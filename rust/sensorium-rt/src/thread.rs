//! Per-thread state: serial, reentrancy depth, the truncation counter, the
//! spool, and the slot a wrapped exit operand stashes its value in.
//!
//! Every one of these is a `thread_local!`, so nothing here is shared and
//! nothing here locks. The spool's destructor is what writes `THREAD_END`; a
//! thread that never ends never runs it, which is exactly the distinction
//! `rust/HONESTY.md` §4 draws between a finished thread and a live one.

use std::cell::{Cell, RefCell};
use std::path::Path;
use std::sync::atomic::{AtomicU32, Ordering};

use crate::ffi;
use crate::probe::{Capture, Outcome};
use crate::spool::Spool;

/// Serials are minted from 2 upward. Serial 1 is RESERVED for the main thread
/// (the thread whose `gettid() == getpid()`) whether or not it ever emits, so a
/// spawned thread that emits first still gets 2.
static NEXT_SERIAL: AtomicU32 = AtomicU32::new(2);

/// The most exit-operand captures that can be pending on one thread at once.
///
/// An entry is pushed when a frame evaluates its exit operand and taken by that
/// frame's guard a moment later, so the only way they stack up is a chain of
/// `Drop`s that call instrumented code between the two. 64 is far past anything
/// a real one reaches; a 65th push is refused and that frame closes `none`
/// (`rust/HONESTY.md` §1).
pub(crate) const MAX_PENDING_STASHES: usize = 64;

/// What a wrapped exit operand left behind for the guard of its own frame.
///
/// Keyed by `(site, depth)`, not by site alone: a `Drop` that calls the SAME
/// instrumented function one level down produces two live entries with the same
/// site, and the frame depth is what keeps each one's value its own.
pub(crate) struct Stash {
    pub(crate) site: u32,
    pub(crate) depth: u32,
    pub(crate) capture: Capture,
    pub(crate) outcome: Outcome,
}

thread_local! {
    /// Non-zero while the runtime itself is running. `enter` and `ret` are inert
    /// while it is set, so a workspace `Debug` impl the instrument invokes
    /// records nothing (spec §3.6; Python's `in_hook`).
    static DEPTH: Cell<u32> = const { Cell::new(0) };
    /// 0 until this thread mints one.
    static SERIAL: Cell<u32> = const { Cell::new(0) };
    /// Captures cut short on this thread, mirrored into the spool header.
    static TRUNCATED: Cell<u64> = const { Cell::new(0) };
    /// Opened on the thread's first event; its destructor writes `THREAD_END`.
    static SPOOL: RefCell<Option<Spool>> = const { RefCell::new(None) };
    /// Pending exit-operand captures, innermost last. Bounded by
    /// [`MAX_PENDING_STASHES`].
    static STASH: RefCell<Vec<Stash>> = const { RefCell::new(Vec::new()) };
    /// How many frames this thread has open. A guard's own depth is minted here
    /// when its CALL is recorded and is stable for the guard's whole life,
    /// because guards are `let`-bound locals and drop in reverse order.
    static FRAME_DEPTH: Cell<u32> = const { Cell::new(0) };
}

/// This thread's serial, minting it on first use.
fn serial() -> u32 {
    SERIAL
        .try_with(|c| {
            let existing = c.get();
            if existing != 0 {
                return existing;
            }
            let minted = if ffi::is_main_thread() {
                1
            } else {
                NEXT_SERIAL.fetch_add(1, Ordering::Relaxed)
            };
            c.set(minted);
            minted
        })
        .unwrap_or(0)
}

/// Held while the runtime runs. Its `Drop` clears the depth even if the body
/// panics, so a fault inside the instrument cannot wedge the thread silently.
pub(crate) struct RuntimeScope(());

impl Drop for RuntimeScope {
    fn drop(&mut self) {
        let _ = DEPTH.try_with(|d| d.set(d.get().saturating_sub(1)));
    }
}

/// `Some` only when the runtime was not already running on this thread.
pub(crate) fn try_enter_runtime() -> Option<RuntimeScope> {
    DEPTH
        .try_with(|d| {
            if d.get() != 0 {
                return None;
            }
            d.set(1);
            Some(RuntimeScope(()))
        })
        .ok()
        .flatten()
}

/// Mark the runtime as running whatever the depth already is. Closing a frame
/// is never conditional -- a guard that recorded its CALL records its RETURN --
/// so the RETURN path takes this rather than `try_enter_runtime`.
pub(crate) fn enter_runtime() -> RuntimeScope {
    let _ = DEPTH.try_with(|d| d.set(d.get() + 1));
    RuntimeScope(())
}

/// True while this thread is inside the instrument. The panic hook reads it to
/// stay silent for a panic the instrument itself provoked.
pub(crate) fn in_runtime() -> bool {
    DEPTH.try_with(|d| d.get() != 0).unwrap_or(false)
}

/// Open a frame: mint and return its depth. Called only once a CALL has actually
/// been recorded, so an inert guard never consumes a depth.
pub(crate) fn open_frame() -> u32 {
    FRAME_DEPTH
        .try_with(|c| {
            let depth = c.get() + 1;
            c.set(depth);
            depth
        })
        .unwrap_or(0)
}

/// Close the frame that was opened at `depth`. Restores the counter rather than
/// decrementing it, so an odd drop order cannot leave it drifting upward.
pub(crate) fn close_frame(depth: u32) {
    let _ = FRAME_DEPTH.try_with(|c| c.set(depth.saturating_sub(1)));
}

/// The depth of the innermost frame open on this thread; 0 when none is.
pub(crate) fn frame_depth() -> u32 {
    FRAME_DEPTH.try_with(Cell::get).unwrap_or(0)
}

/// Leave a capture for the guard of the frame `(site, depth)`. Refused, and the
/// capture dropped, once [`MAX_PENDING_STASHES`] are already pending.
pub(crate) fn push_stash(stash: Stash) {
    let _ = STASH.try_with(|cell| {
        if let Ok(mut stack) = cell.try_borrow_mut() {
            if stack.len() < MAX_PENDING_STASHES {
                stack.push(stash);
            }
        }
    });
}

/// Take the top entry, but ONLY if it is this frame's own.
///
/// A guard drops after every frame it opened has finished, so its own entry --
/// if it left one -- is necessarily on top. Anything else on top belongs to
/// somebody, and taking it would report one frame's value as another's; the
/// stack is left exactly as it was and this frame closes knowing nothing.
pub(crate) fn pop_stash_if(site: u32, depth: u32) -> Option<Stash> {
    STASH
        .try_with(|cell| {
            let mut stack = cell.try_borrow_mut().ok()?;
            match stack.last() {
                Some(top) if top.site == site && top.depth == depth => stack.pop(),
                _ => None,
            }
        })
        .ok()
        .flatten()
}

/// Count one capture that hit the cap, and mirror the count into the header.
pub(crate) fn note_truncated() {
    let n = TRUNCATED.try_with(|c| {
        c.set(c.get() + 1);
        c.get()
    });
    let Ok(n) = n else {
        return;
    };
    let _ = SPOOL.try_with(|cell| {
        if let Ok(mut slot) = cell.try_borrow_mut() {
            if let Some(spool) = slot.as_mut() {
                spool.set_truncated(n);
            }
        }
    });
}

/// Append one record to a spool this thread ALREADY has, opening nothing.
///
/// The panic hook's writer, and the reason it cannot panic: opening a spool can
/// fail, and reporting that failure prints -- which, on a thread that is already
/// panicking, would be a second panic and an abort. A thread that never recorded
/// an event has no frame for a PANIC record to close, so this is not a record
/// lost so much as one there was nothing to attach.
pub(crate) fn emit_if_open(site: u32, kind: u8, outcome: u8, payload: &[u8]) -> bool {
    SPOOL
        .try_with(|cell| {
            let Ok(mut slot) = cell.try_borrow_mut() else {
                return false;
            };
            let Some(spool) = slot.as_mut() else {
                return false;
            };
            spool.record(ffi::now_ns(), site, kind, outcome, payload)
        })
        .unwrap_or(false)
}

/// Append one record to this thread's spool, opening it on first use. Returns
/// false if nothing was written.
pub(crate) fn emit(dir: &Path, site: u32, kind: u8, outcome: u8, payload: &[u8]) -> bool {
    SPOOL
        .try_with(|cell| {
            let Ok(mut slot) = cell.try_borrow_mut() else {
                return false;
            };
            if slot.is_none() {
                let serial = serial();
                let name = crate::tasks::header_name();
                let truncated = TRUNCATED.try_with(|c| c.get()).unwrap_or(0);
                match Spool::open(dir, std::process::id(), serial, &name, truncated) {
                    Ok(s) => *slot = Some(s),
                    Err(e) => {
                        crate::fail_process("opening a spool file", &e);
                        return false;
                    }
                }
            }
            let Some(spool) = slot.as_mut() else {
                return false;
            };
            spool.record(ffi::now_ns(), site, kind, outcome, payload)
        })
        .unwrap_or(false)
}
