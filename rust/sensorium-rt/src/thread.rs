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

/// What a wrapped exit operand left behind for the guard of its own frame.
pub(crate) struct Stash {
    pub(crate) site: u32,
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
    /// At most one pending exit-operand capture.
    static STASH: RefCell<Option<Stash>> = const { RefCell::new(None) };
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

/// Leave a capture for the guard of the frame at `site`.
pub(crate) fn stash_ret(site: u32, capture: Capture, outcome: Outcome) {
    let _ = STASH.try_with(|cell| {
        if let Ok(mut slot) = cell.try_borrow_mut() {
            *slot = Some(Stash {
                site,
                capture,
                outcome,
            });
        }
    });
}

/// Take whatever is in the slot, leaving it empty. A stash that does not belong
/// to the taking frame is discarded by the caller rather than carried on, so a
/// `return` inside an unwrapped nested construct cannot poison an outer frame.
pub(crate) fn take_stash() -> Option<Stash> {
    STASH
        .try_with(|cell| cell.try_borrow_mut().ok().and_then(|mut slot| slot.take()))
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
                let name = std::thread::current().name().unwrap_or("").to_owned();
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
            spool.record(
                crate::next_seq(),
                ffi::now_ns(),
                site,
                kind,
                outcome,
                payload,
            )
        })
        .unwrap_or(false)
}
