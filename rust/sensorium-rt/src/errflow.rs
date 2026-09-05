//! Err-flow sites: the RAISE and HANDLED records a `?`, a sink or an `Err(..)`
//! arm writes when the value it saw was actually an `Err`.
//!
//! The runtime stays dumb here on purpose (design R7, placement B): it records
//! *sites*, never dispositions. Whether an `Err` was swallowed, propagated,
//! panicked on or is simply ambiguous is computed at conversion from the
//! per-thread order of these records, so every rule change is a converter
//! change and none of them is a wire change.
//!
//! The transformer injects, in place (design R3), one of:
//!
//! ```ignore
//! // a `?` or a sink receiver, on the operand `__t`
//! match <operand> { __t => {
//!     ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, SITE, HOW, || {
//!         use ::sensorium_rt::probe::*;
//!         (&&&Probe(&__t)).err_cap()
//!     });
//!     __t
//! } }
//!
//! // an `Err(e) =>` arm, on the BOUND error
//! ::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, SITE, HOW, || {
//!     use ::sensorium_rt::probe::*;
//!     (&&Probe(&e)).err_cap_value()
//! });
//!
//! // an `Err(_)`/`Err(..)` arm, which binds nothing
//! ::sensorium_rt::err_site_unbound(&crate::__SENSORIUM_UNIT, SITE, HOW);
//! ```
//!
//! **The capture is a closure.** It is called only once this process is known to
//! be recording, so at tier `off` a `Debug` impl at an err site is not invoked,
//! nothing is formatted and nothing is allocated -- exactly the promise `ret`
//! keeps for the exit operand, and pinned by the `errflow-lazy` scenario.
//!
//! **No frame is required.** A site whose enclosing frame never opened (its
//! CALL was refused, or the closure ran on a thread of its own) still records
//! what it saw. The runtime does not decide what a converter can use.

use std::sync::atomic::Ordering;

use crate::probe::{self, Capture};
use crate::spool::{self, KIND_HANDLED, KIND_RAISE, SITE_INDEX_MASK};
use crate::{thread, Unit};

/// What an err-flow site read off the value it was handed.
///
/// `seen_err` is the only field that decides whether a record is written at all:
/// an `Ok`, an `Option`, and a non-`Result` all answer `false`, and
/// [`crate::err_site`] writes nothing for them. `type_name: None` means the
/// ladder could not name the error type; `text: None` means it could not read
/// one -- *unread*, never empty.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErrCapture {
    pub seen_err: bool,
    pub type_name: Option<&'static str>,
    pub text: Option<String>,
    pub truncated: bool,
}

impl ErrCapture {
    /// Nothing was seen: no record, nothing to say.
    pub(crate) const fn nothing() -> ErrCapture {
        ErrCapture {
            seen_err: false,
            type_name: None,
            text: None,
            truncated: false,
        }
    }

    /// An `Err` was seen and its type is known; the text may not be.
    pub(crate) fn seen(type_name: &'static str, capture: Capture) -> ErrCapture {
        ErrCapture {
            seen_err: true,
            type_name: Some(type_name),
            text: capture.text,
            truncated: capture.truncated,
        }
    }
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
/// A frame closing `err`, synthesised BY THE CONVERTER in front of the RETURN so
/// a chain has an origin record.
///
/// **Converter-only, and deliberately not re-exported from the crate root beside
/// the writable seven**: no runtime path can write it, [`debug_check_how`]
/// refuses it, and instrumented code has no business naming it. It is declared
/// here so the eight numbers of the wire's `how` vocabulary have one home, and
/// the assertion below is what keeps that home honest -- the writable range must
/// end exactly where the converter-only how begins.
pub(crate) const HOW_EXIT: u8 = 8;

const _: () = assert!(
    HOW_ARM_AMBIGUOUS + 1 == HOW_EXIT,
    "the writable hows must run 1..=7 with the converter-only `exit` at 8"
);

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

/// **Why there are two entry points with all but the same body.** They are two
/// CONTRACTS, not two implementations, and the transformer picks between them by
/// what it has in hand at the site -- which is also what `how` records. [`err_site`]
/// is handed a whole `Result` whose `Err`-ness is a runtime question, so its
/// ladder answers `seen_err: false` for an `Ok`, an `Option` and a non-`Result`
/// and NOTHING is written. [`err_site_value`] is handed the error an
/// `Err(e) =>` arm already destructured, so its ladder always answers
/// `seen_err: true` and a record always follows. Merging them would put one
/// name on two claims: "an error was seen here if there was one" and "an error
/// was seen here". The shared `seen_err` check is what makes the merged body
/// look identical; the guarantee behind it is not.
///
/// A `?` or a sink receiver. Writes a record **only** when the ladder saw a
/// `Result::Err`.
///
/// `cap` is a CLOSURE and is called only when this process is recording, so at
/// tier `off` no `Debug` impl is invoked, nothing is formatted and nothing is
/// allocated -- the same promise [`crate::ret`] keeps for the exit operand.
#[inline]
pub fn err_site(unit: &'static Unit, site: u32, how: u8, cap: impl FnOnce() -> ErrCapture) {
    debug_check_how(how);
    if !recording_now() {
        return;
    }
    write_capture(unit, site, how, cap());
}

/// An `Err(e) =>` arm, handed the bound error itself (see [`err_site`] for why
/// this is a second entry point rather than the same one). The arm ladder always
/// saw an error -- that is what matching `Err` means -- so this always writes;
/// what varies is whether the message could be read.
///
/// `cap` is a closure for the same reason it is one on [`err_site`].
#[inline]
pub fn err_site_value(unit: &'static Unit, site: u32, how: u8, cap: impl FnOnce() -> ErrCapture) {
    debug_check_how(how);
    if !recording_now() {
        return;
    }
    write_capture(unit, site, how, cap());
}

/// An `Err(_)`, `Err(..)` or `Err(E::Variant)` arm: there is no binding, so
/// there is no type and no text to read -- and so no capture to defer, which is
/// why this one takes no closure. The record says an error was seen at this site
/// and nothing more; the converter fills the type in from the chain it
/// continues, or says it is unread (design R4).
#[inline]
pub fn err_site_unbound(unit: &'static Unit, site: u32, how: u8) {
    debug_check_how(how);
    if !recording_now() {
        return;
    }
    record(unit, site, how, None, None, false);
}

/// One `Acquire` load. The gate that makes the capture closures lazy: at tier
/// `off`, and in a process that never configured a spool, an err site is this
/// load and a return.
#[inline]
fn recording_now() -> bool {
    crate::STATE.load(Ordering::Acquire) == crate::STATE_CALL
}

/// The `how` a caller passes must be one this module can write.
///
/// A `debug_assert`, stated the way `Spool::record` states its payload-length
/// contract: a wrong `how` is a transformer defect, and a release build must not
/// pay for checking it. It is checked BEFORE [`recording_now`] on purpose --
/// the contract is on the caller, not on the recording path, so a test does not
/// have to arrange a live recorder to falsify it.
#[inline]
fn debug_check_how(how: u8) {
    debug_assert!(
        (HOW_TRY..=HOW_ARM_AMBIGUOUS).contains(&how),
        "how {how} is not a writable how"
    );
}

#[inline(never)]
fn write_capture(unit: &'static Unit, site: u32, how: u8, cap: ErrCapture) {
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

/// Build the payload and hand it to this thread's spool.
///
/// Every err-flow entry point funnels through here, so the record's shape --
/// kind from the `how`, the site word, the capped type and message -- has one
/// home and one set of falsifiers.
#[inline(never)]
fn record(
    unit: &'static Unit,
    site: u32,
    how: u8,
    type_name: Option<&str>,
    msg: Option<&str>,
    msg_truncated: bool,
) {
    // Reentrancy: a site reached from inside the instrument records nothing,
    // the same rule `enter` and `ret` keep (spec §3.6).
    let Some(_scope) = thread::try_enter_runtime() else {
        return;
    };
    // Re-reads STATE, so a recorder that went inert between the entry point's
    // gate and here still writes nothing.
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
    thread::emit(
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

    /// The `how` guard is a caller contract, so it fires whether or not this
    /// process is recording -- which is the only reason it can be falsified in a
    /// unit test at all.
    #[test]
    #[should_panic(expected = "how 8 is not a writable how")]
    fn the_converter_only_how_is_refused_by_the_writer() {
        // Constant per profile, and deliberately asserted: this test is only
        // meaningful where `debug_assert!` is live.
        #[allow(clippy::assertions_on_constants)]
        {
            assert!(
                cfg!(debug_assertions),
                "this test pins a debug_assert and needs a debug build"
            );
        }
        static UNIT: Unit = Unit::new("errflow-how-guard");
        err_site(&UNIT, 0, HOW_EXIT, ErrCapture::nothing);
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
