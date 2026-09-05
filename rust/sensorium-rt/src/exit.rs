//! The exit operand: what a value-returning frame stashes for its own guard, and
//! the RETURN payload that guard writes.
//!
//! The transformer wraps every exit operand -- the tail expression, and each
//! `return <e>` at closure depth 0 -- of a value-returning fn as
//!
//! ```ignore
//! ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, <site>, |__r| {
//!     use ::sensorium_rt::probe::*;
//!     ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
//! }, <e>)
//! ```
//!
//! The probe is a CLOSURE, not a value, and that is the whole reason a `Debug`
//! impl is never invoked at tier `off`. What it returns is a [`Capture`] and an
//! [`Exit`]; the `Exit` carries the frame's outcome and, on an `err`, the static
//! type of the `Result`'s error -- the only place in the runtime that type is
//! knowable, and what lets a converter synthesise the origin RAISE of a chain
//! that left a frame by returning `Err` (design R1).

use std::sync::atomic::Ordering;

use crate::probe::{self, Capture, Exit, Outcome};
use crate::{pack_site, spool, thread, Unit, STATE, STATE_CALL};

pub(crate) const TAG_NO_VALUE: u8 = 0;
pub(crate) const TAG_DEBUG: u8 = 1;
pub(crate) const TAG_UNREAD: u8 = 2;
/// The `type_flags` byte of an `err` RETURN's type block.
pub(crate) const TYPE_FLAG_PRESENT: u8 = 1 << 0;
pub(crate) const TYPE_FLAG_TRUNCATED: u8 = 1 << 1;
/// `u8 tag, u8 truncated`, then -- on an `err` only -- `u8 type_flags,
/// u16 type_len, type`, then the text.
pub(crate) const RETURN_PAYLOAD_MAX: usize = 2 + 3 + probe::TYPE_CAP + probe::CAP;

/// Stash `(site, cap(&v))` for this frame's guard and hand `v` straight back.
///
/// `cap` is called ONLY when the recorder is live on this thread: at tier `off`
/// this function is a move and a compare, and a `Debug` impl that would have
/// been invoked is not invoked.
pub fn ret<T>(unit: &'static Unit, site: u32, cap: impl FnOnce(&T) -> (Capture, Exit), v: T) -> T {
    if STATE.load(Ordering::Acquire) == STATE_CALL {
        stash_return(unit, site, cap, &v);
    }
    v
}

#[inline(never)]
fn stash_return<T>(unit: &'static Unit, site: u32, cap: impl FnOnce(&T) -> (Capture, Exit), v: &T) {
    // The capture runs INSIDE the runtime scope, so a workspace `Debug` impl
    // that calls instrumented code records nothing (spec §3.6).
    let Some(_scope) = thread::try_enter_runtime() else {
        return;
    };
    // No registration here: a unit with no id has no open frame at this site.
    let Some(id) = unit.current_id() else {
        return;
    };
    // With no frame open on this thread there is no guard that could ever take
    // this, so it is not left for one.
    let depth = thread::frame_depth();
    if depth == 0 {
        return;
    }
    let (capture, exit) = cap(v);
    thread::push_stash(thread::Stash {
        site: pack_site(id, site),
        depth,
        capture,
        exit,
    });
}

/// `u8 tag, u8 truncated`, then -- on outcome `err` and only there -- the error
/// type block, then the UTF-8 text.
///
/// Always at least the two bytes on every RETURN, so a reader never has to ask
/// whether a payload is there; and outcomes `none`, `ok` and `panic` are
/// byte-for-byte what wire v2 wrote, so a v3 reader on a v2 spool reads them
/// unchanged (design R1).
pub(crate) fn write_return_payload(
    buf: &mut [u8; RETURN_PAYLOAD_MAX],
    capture: Option<&Capture>,
    exit: Exit,
) -> usize {
    buf[1] = 0;
    let text = match capture {
        None => {
            buf[0] = TAG_NO_VALUE;
            None
        }
        Some(capture) => match capture.text.as_deref() {
            None => {
                buf[0] = TAG_UNREAD;
                None
            }
            Some(text) => {
                buf[0] = TAG_DEBUG;
                // `spool::record` refuses a payload it cannot describe rather
                // than clamping one, so the cut happens here, on a char boundary
                // -- and it is witnessed by the flag, whether the capping writer
                // cut the text or this did.
                let (text, cut_here) = spool::cap_utf8(text, probe::CAP);
                buf[1] = u8::from(capture.truncated || cut_here);
                Some(text)
            }
        },
    };
    let mut at = 2;
    if exit.outcome as u8 == Outcome::Err as u8 {
        at = write_err_type_block(buf, exit.err_type);
    }
    let Some(text) = text else {
        return at;
    };
    buf[at..at + text.len()].copy_from_slice(text.as_bytes());
    at + text.len()
}

/// The three-plus-`type_len` bytes an `err` RETURN carries between its flags and
/// its text. Always written on an `err`, even with no type to name, so the
/// block's own presence never has to be inferred from the payload's length.
fn write_err_type_block(buf: &mut [u8; RETURN_PAYLOAD_MAX], err_type: Option<&str>) -> usize {
    let (flags, text) = match err_type {
        None => (0u8, ""),
        Some(t) => {
            let (text, cut) = spool::cap_utf8(t, probe::TYPE_CAP);
            let mut flags = TYPE_FLAG_PRESENT;
            if cut {
                flags |= TYPE_FLAG_TRUNCATED;
            }
            (flags, text)
        }
    };
    buf[2] = flags;
    buf[3..5].copy_from_slice(&(text.len() as u16).to_le_bytes());
    buf[5..5 + text.len()].copy_from_slice(text.as_bytes());
    5 + text.len()
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The tags are wire-format numbers, so they are written out here as
    /// numbers. Asserting against the constants would move with them and pin
    /// nothing -- which is exactly what these three tests did until a mutation
    /// run walked through them untouched.
    #[test]
    fn the_payload_tags_and_type_flags_are_the_numbers_the_wire_format_names() {
        assert_eq!(TAG_NO_VALUE, 0);
        assert_eq!(TAG_DEBUG, 1);
        assert_eq!(TAG_UNREAD, 2);
        assert_eq!(TYPE_FLAG_PRESENT, 1);
        assert_eq!(TYPE_FLAG_TRUNCATED, 2);
    }

    /// The exit an outcome that is not `err` produces.
    fn plain(outcome: Outcome) -> Exit {
        Exit {
            outcome,
            err_type: None,
        }
    }

    #[test]
    fn a_return_with_no_capture_is_two_bytes() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        assert_eq!(
            write_return_payload(&mut buf, None, plain(Outcome::None)),
            2
        );
        assert_eq!(&buf[..2], &[0, 0]);
    }

    #[test]
    fn an_unread_value_is_two_bytes_with_tag_two() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: None,
            truncated: false,
        };
        assert_eq!(
            write_return_payload(&mut buf, Some(&c), plain(Outcome::Ok)),
            2
        );
        assert_eq!(&buf[..2], &[2, 0]);
    }

    #[test]
    fn a_read_value_carries_its_text_and_its_flag() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: Some("Ok(3)".to_owned()),
            truncated: true,
        };
        let n = write_return_payload(&mut buf, Some(&c), plain(Outcome::Ok));
        assert_eq!(n, 7);
        assert_eq!(buf[0], 1);
        assert_eq!(buf[1], 1);
        assert_eq!(&buf[2..n], b"Ok(3)");
    }

    #[test]
    fn an_over_long_capture_is_clipped_on_a_char_boundary_and_flagged() {
        // `truncated: false` on purpose: the cut happens HERE, and the flag has
        // to be set by the writer that cut, not inherited from the capture.
        let text = "é".repeat(500);
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: Some(text),
            truncated: false,
        };
        let n = write_return_payload(&mut buf, Some(&c), plain(Outcome::Ok));
        assert!(n <= RETURN_PAYLOAD_MAX, "{n} bytes");
        assert_eq!(n, 2 + probe::CAP, "'é' is two bytes and the cap is even");
        assert_eq!(
            buf[1], 1,
            "a payload cut here is a payload marked truncated"
        );
        assert_eq!(
            std::str::from_utf8(&buf[2..n]),
            Ok("é".repeat(probe::CAP / 2).as_str())
        );
    }

    #[test]
    fn an_empty_debug_rendering_is_a_read_value_not_an_unread_one() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let c = Capture {
            text: Some(String::new()),
            truncated: false,
        };
        assert_eq!(
            write_return_payload(&mut buf, Some(&c), plain(Outcome::Ok)),
            2
        );
        assert_eq!(&buf[..2], &[1, 0], "tag 1 with no text, never tag 2");
    }
    // -----------------------------------------------------------------------
    // The typed `err` RETURN (design R1)
    // -----------------------------------------------------------------------

    /// The three claims below are the ones no integration test can reach; the
    /// rest of the type block's shape is pinned byte-for-byte in
    /// `tests/outcomes.rs` and `tests/err_flow.rs`, off a real spool.
    fn err_exit(err_type: Option<&'static str>) -> Exit {
        Exit {
            outcome: Outcome::Err,
            err_type,
        }
    }

    /// An `err` whose type the probe could not name still writes the block, so a
    /// reader never has to infer its presence from the payload's length.
    #[test]
    fn an_err_with_no_named_type_still_writes_an_empty_type_block() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let n = write_return_payload(&mut buf, None, err_exit(None));
        assert_eq!(n, 5);
        assert_eq!(&buf[..5], &[0, 0, 0, 0, 0]);
    }

    #[test]
    fn a_long_error_type_is_cut_on_a_char_boundary_and_flagged() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let ty: &'static str = Box::leak("é".repeat(200).into_boxed_str());
        let n = write_return_payload(&mut buf, None, err_exit(Some(ty)));
        assert_eq!(buf[2], 3, "type present (bit0) and truncated (bit1)");
        let len = u16::from_le_bytes([buf[3], buf[4]]) as usize;
        assert_eq!(len, probe::TYPE_CAP, "'é' is two bytes and the cap is even");
        assert_eq!(
            std::str::from_utf8(&buf[5..5 + len]),
            Ok("é".repeat(probe::TYPE_CAP / 2).as_str())
        );
        assert_eq!(n, 5 + probe::TYPE_CAP);
    }

    /// The widest RETURN an `err` can produce still fits the buffer, and the
    /// buffer still fits the wire's `u16` length field.
    #[test]
    fn the_widest_err_return_fits_the_buffer() {
        let mut buf = [0u8; RETURN_PAYLOAD_MAX];
        let ty: &'static str = Box::leak("t".repeat(1000).into_boxed_str());
        let c = Capture {
            text: Some("m".repeat(1000)),
            truncated: false,
        };
        let n = write_return_payload(&mut buf, Some(&c), err_exit(Some(ty)));
        assert_eq!(n, RETURN_PAYLOAD_MAX);
        assert_eq!(n, 2 + 3 + 120 + 200);
        assert!(n <= u16::MAX as usize);
    }
}
