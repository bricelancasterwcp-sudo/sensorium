//! Per-thread state: serial, reentrancy depth, the truncation counter, the
//! spool, the slot a wrapped exit operand stashes its value in -- and the
//! err-flow sites, which are the one recording path with no per-frame state of
//! their own and so sit beside the `emit` they write straight through.
//!
//! Every one of the first group is a `thread_local!`, so nothing there is shared
//! and nothing there locks. The spool's destructor is what writes `THREAD_END`;
//! a thread that never ends never runs it, which is exactly the distinction
//! `rust/HONESTY.md` §4 draws between a finished thread and a live one.
//!
//! (The err-flow half would be a module of its own. It is not one because the
//! driver embeds the runtime's sources file by file --
//! `cargo-sensorium/src/rt_src.rs::FILES`, plan decision D1 -- so a new
//! `sensorium-rt` module is a two-crate change, and this one is not.)

use std::cell::{Cell, RefCell};
use std::path::Path;
use std::sync::atomic::{AtomicU32, Ordering};

use crate::ffi;
use crate::probe::{self, Capture, ErrCapture, Exit};
use crate::spool::{self, Spool, KIND_HANDLED, KIND_RAISE, SITE_INDEX_MASK};
use crate::Unit;

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
    /// The outcome AND, on an `err`, the static type of the error -- the exit
    /// probe is the only place that type is knowable (design R1).
    pub(crate) exit: Exit,
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

// ---------------------------------------------------------------------------
// The `how` byte (design R2)
// ---------------------------------------------------------------------------

/// `?` on a `Result` whose operand was `Err`. RAISE: the `Err` left the frame.
/// (A `?` on an `Option` writes nothing -- `None` is not an error in this model.)
pub const HOW_TRY: u8 = 1;
/// `.ok()` on an `Err` receiver. HANDLED: the `Err` was absorbed.
pub const HOW_SINK_OK: u8 = 2;
/// `.unwrap_or(..)`, `.unwrap_or_else(..)` or `.unwrap_or_default()` on an `Err`
/// receiver. HANDLED.
pub const HOW_SINK_UNWRAP_OR: u8 = 3;
/// `let _ = <value expression>` whose value was `Err`. HANDLED.
pub const HOW_SINK_LET_UNDERSCORE: u8 = 4;
/// An `Err(..) =>` arm whose body propagates (`?`, `return Err(..)`, or a tail
/// `Err(..)`). RAISE.
pub const HOW_ARM_PROPAGATE: u8 = 5;
/// An `Err(..) =>` arm that handles the error and does not let it out. HANDLED.
pub const HOW_ARM_HANDLED: u8 = 6;
/// An `Err(e) =>` arm that binds the error and lets the name escape -- stored,
/// returned inside something else, moved into a closure. HANDLED-class, and
/// never a SWALLOWED candidate: the converter reads it as AMBIGUOUS.
pub const HOW_ARM_AMBIGUOUS: u8 = 7;
/// A frame closing `err`, synthesised BY THE CONVERTER in front of the RETURN
/// so a chain has an origin record. It is never written to a spool, and is
/// declared here only so the eight numbers have one home.
pub const HOW_EXIT: u8 = 8;

/// Which record kind a `how` writes.
///
/// The split is the whole of what the runtime decides about err flow: a `how`
/// that lets the `Err` OUT of the frame is a RAISE, and every other is a
/// HANDLED. `HOW_EXIT` never reaches a spool, so it is not in the table.
pub(crate) fn kind_for_how(how: u8) -> u8 {
    match how {
        HOW_TRY | HOW_ARM_PROPAGATE => KIND_RAISE,
        _ => KIND_HANDLED,
    }
}

// ---------------------------------------------------------------------------
// The payload
// ---------------------------------------------------------------------------

const FLAG_MSG_PRESENT: u8 = 1 << 0;
const FLAG_MSG_TRUNCATED: u8 = 1 << 1;
const FLAG_TYPE_TRUNCATED: u8 = 1 << 2;
const FLAG_TYPE_PRESENT: u8 = 1 << 3;

/// `u8 flags, u16 type_len, type, msg` -- the biggest either cap allows.
pub(crate) const ERR_PAYLOAD_MAX: usize = 3 + probe::TYPE_CAP + probe::CAP;

/// Write the RAISE/HANDLED payload and return its length.
///
/// Absent and empty are different, and the flags are what separate them: a type
/// of `""` with `bit3` set is a type that rendered empty, and no `bit3` is a
/// type the ladder could not name at all. The same for `bit0` and the message.
pub(crate) fn write_err_payload(
    buf: &mut [u8; ERR_PAYLOAD_MAX],
    type_name: Option<&str>,
    msg: Option<&str>,
    msg_truncated: bool,
) -> usize {
    let mut flags = 0u8;
    // `spool::record` refuses a payload it cannot describe rather than clamping
    // one, so both cuts happen HERE, on char boundaries, each witnessed by its
    // own flag bit.
    let type_text = match type_name {
        Some(t) => {
            flags |= FLAG_TYPE_PRESENT;
            let (text, cut) = spool::cap_utf8(t, probe::TYPE_CAP);
            if cut {
                flags |= FLAG_TYPE_TRUNCATED;
            }
            text
        }
        None => "",
    };
    let msg_text = match msg {
        Some(m) => {
            flags |= FLAG_MSG_PRESENT;
            let (text, cut) = spool::cap_utf8(m, probe::CAP);
            if cut || msg_truncated {
                flags |= FLAG_MSG_TRUNCATED;
            }
            text
        }
        None => "",
    };
    buf[0] = flags;
    buf[1..3].copy_from_slice(&(type_text.len() as u16).to_le_bytes());
    let mut at = 3;
    buf[at..at + type_text.len()].copy_from_slice(type_text.as_bytes());
    at += type_text.len();
    buf[at..at + msg_text.len()].copy_from_slice(msg_text.as_bytes());
    at + msg_text.len()
}

// ---------------------------------------------------------------------------
// The entry points
// ---------------------------------------------------------------------------

/// A `?` or a sink receiver. Writes a record **only** when the ladder saw a
/// `Result::Err`: an `Ok`, an `Option` and a non-`Result` all write nothing.
#[inline]
pub fn err_site(unit: &'static Unit, site: u32, how: u8, cap: ErrCapture) {
    if !cap.seen_err {
        return;
    }
    record(
        unit,
        site,
        how,
        cap.type_name,
        cap.text.as_deref(),
        cap.truncated,
    );
}

/// An `Err(e) =>` arm, handed the bound error itself. The arm ladder always saw
/// an error -- that is what matching `Err` means -- so this always writes; what
/// varies is whether the message could be read.
#[inline]
pub fn err_site_value(unit: &'static Unit, site: u32, how: u8, cap: ErrCapture) {
    if !cap.seen_err {
        return;
    }
    record(
        unit,
        site,
        how,
        cap.type_name,
        cap.text.as_deref(),
        cap.truncated,
    );
}

/// An `Err(_)`, `Err(..)` or `Err(E::Variant)` arm: there is no binding, so
/// there is no type and no text to read. The record says an error was seen at
/// this site and nothing more; the converter fills the type in from the chain it
/// continues, or says it is unread (design R4).
#[inline]
pub fn err_site_unbound(unit: &'static Unit, site: u32, how: u8) {
    record(unit, site, how, None, None, false);
}

#[inline(never)]
fn record(
    unit: &'static Unit,
    site: u32,
    how: u8,
    type_name: Option<&str>,
    msg: Option<&str>,
    msg_truncated: bool,
) {
    if crate::STATE.load(Ordering::Acquire) != crate::STATE_CALL {
        return;
    }
    // Reentrancy: a site reached from inside the instrument records nothing,
    // the same rule `enter` and `ret` keep (spec §3.6).
    let Some(_scope) = try_enter_runtime() else {
        return;
    };
    let Some(dir) = crate::ensure_dir() else {
        return;
    };
    let Some(id) = crate::unit_id(unit, dir) else {
        return;
    };
    debug_assert!(
        site <= SITE_INDEX_MASK,
        "site index {site} does not fit the wire format's 24 bits and would alias"
    );
    let mut buf = [0u8; ERR_PAYLOAD_MAX];
    let len = write_err_payload(&mut buf, type_name, msg, msg_truncated);
    emit(
        dir,
        crate::pack_site(id, site),
        kind_for_how(how),
        how,
        &buf[..len],
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The `how` numbers are wire-format numbers, so they are written out here
    /// as numbers. Asserting against the constants would move with them and pin
    /// nothing.
    #[test]
    fn the_how_bytes_are_the_numbers_the_wire_format_names() {
        assert_eq!(HOW_TRY, 1);
        assert_eq!(HOW_SINK_OK, 2);
        assert_eq!(HOW_SINK_UNWRAP_OR, 3);
        assert_eq!(HOW_SINK_LET_UNDERSCORE, 4);
        assert_eq!(HOW_ARM_PROPAGATE, 5);
        assert_eq!(HOW_ARM_HANDLED, 6);
        assert_eq!(HOW_ARM_AMBIGUOUS, 7);
        assert_eq!(HOW_EXIT, 8);
    }

    /// RAISE is the two hows that let the `Err` out of the frame, and HANDLED is
    /// every other. Spelled out one `how` at a time rather than as a range, so a
    /// row moving between the two kinds is a failing assertion.
    #[test]
    fn only_the_propagating_hows_write_a_raise() {
        assert_eq!(kind_for_how(HOW_TRY), 4);
        assert_eq!(kind_for_how(HOW_ARM_PROPAGATE), 4);
        assert_eq!(kind_for_how(HOW_SINK_OK), 5);
        assert_eq!(kind_for_how(HOW_SINK_UNWRAP_OR), 5);
        assert_eq!(kind_for_how(HOW_SINK_LET_UNDERSCORE), 5);
        assert_eq!(kind_for_how(HOW_ARM_HANDLED), 5);
        assert_eq!(kind_for_how(HOW_ARM_AMBIGUOUS), 5);
    }

    #[test]
    fn a_type_and_a_message_are_both_present_and_flagged() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let n = write_err_payload(&mut buf, Some("std::io::Error"), Some(r#""x""#), false);
        assert_eq!(buf[0], 0b1001, "msg present (bit0) and type present (bit3)");
        assert_eq!(u16::from_le_bytes([buf[1], buf[2]]), 14);
        assert_eq!(&buf[3..17], b"std::io::Error");
        assert_eq!(&buf[17..n], br#""x""#);
        assert_eq!(n, 3 + 14 + 3);
    }

    #[test]
    fn an_unbound_arm_writes_three_bytes_and_no_flags() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let n = write_err_payload(&mut buf, None, None, false);
        assert_eq!(n, 3);
        assert_eq!(&buf[..3], &[0, 0, 0]);
    }

    #[test]
    fn a_type_with_no_readable_message_sets_only_the_type_bit() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let n = write_err_payload(&mut buf, Some("E"), None, false);
        assert_eq!(buf[0], 0b1000);
        assert_eq!(u16::from_le_bytes([buf[1], buf[2]]), 1);
        assert_eq!(n, 4);
    }

    /// An empty rendering is a rendering: bit0 is set and the length is zero.
    /// The alternative -- dropping the bit -- would report a `Debug` impl that
    /// wrote nothing as one that could not be read.
    #[test]
    fn an_empty_message_is_present_not_absent() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let n = write_err_payload(&mut buf, None, Some(""), false);
        assert_eq!(buf[0], 0b0001);
        assert_eq!(n, 3);
    }

    #[test]
    fn a_long_type_is_cut_on_a_char_boundary_and_flagged() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let ty = "é".repeat(200);
        let n = write_err_payload(&mut buf, Some(&ty), None, false);
        assert_eq!(buf[0], 0b1100, "type present (bit3) and truncated (bit2)");
        let len = u16::from_le_bytes([buf[1], buf[2]]) as usize;
        assert_eq!(len, probe::TYPE_CAP, "'é' is two bytes and the cap is even");
        assert_eq!(
            std::str::from_utf8(&buf[3..3 + len]),
            Ok("é".repeat(probe::TYPE_CAP / 2).as_str())
        );
        assert_eq!(n, 3 + probe::TYPE_CAP);
    }

    #[test]
    fn a_long_message_is_cut_on_a_char_boundary_and_flagged() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let msg = "é".repeat(500);
        let n = write_err_payload(&mut buf, None, Some(&msg), false);
        assert_eq!(buf[0], 0b0011, "msg present (bit0) and truncated (bit1)");
        assert_eq!(n, 3 + probe::CAP);
        assert_eq!(
            std::str::from_utf8(&buf[3..n]),
            Ok("é".repeat(probe::CAP / 2).as_str())
        );
    }

    /// A capture the ladder's own writer already cut arrives short, so nothing
    /// is cut here -- and the flag has to come from the caller, not from this
    /// function's own scissors.
    #[test]
    fn a_message_the_ladder_already_cut_is_still_flagged_truncated() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let n = write_err_payload(&mut buf, None, Some("short"), true);
        assert_eq!(buf[0], 0b0011);
        assert_eq!(n, 3 + 5);
    }

    /// The two caps together are the widest payload an err site can produce, and
    /// it fits the wire's `u16` length with room to spare.
    #[test]
    fn the_widest_payload_fits_the_buffer_and_the_length_field() {
        let mut buf = [0u8; ERR_PAYLOAD_MAX];
        let n = write_err_payload(
            &mut buf,
            Some(&"t".repeat(1000)),
            Some(&"m".repeat(1000)),
            false,
        );
        assert_eq!(n, ERR_PAYLOAD_MAX);
        assert_eq!(n, 3 + 120 + 200);
        assert!(n <= u16::MAX as usize);
        assert_eq!(buf[0], 0b1111, "both present, both truncated");
    }
}
