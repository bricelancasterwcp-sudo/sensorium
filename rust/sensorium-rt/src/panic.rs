//! The panic hook: one PANIC record per panic, then the hook that was already
//! installed, so the program's own output is unchanged.
//!
//! **What is on the wire.** `u16 loc_len`, the location as
//! `"<file>:<line>:<col>"` exactly as [`std::panic::Location`] gave it, then the
//! message -- `payload().downcast_ref::<&str>()` or `::<String>()`, and
//! `"<non-string payload>"` when it is neither. The record's `kind` is 3 and its
//! `outcome` byte is 0: outcome is a RETURN's field, and the frame this panic
//! unwinds carries `panic` on its own RETURN a moment later.
//!
//! **The serial is not on the wire.** A panic's serial is per thread, and the
//! converter mints it: PANIC records on one thread are numbered in the order
//! they appear in that thread's spool, and the most recent one is attached to
//! every frame that then closes `panic`. Writing a serial here would be a
//! second source of truth for a number the reader can already count.
//!
//! **Silence inside the instrument.** While the runtime is running on this
//! thread (`thread::in_runtime()`) the hook records nothing *and does not
//! chain*: a workspace `Debug` impl that panics while the recorder is
//! formatting it is caught by `probe`, the program is not unwound, and printing
//! `thread 'x' panicked` for it would be the instrument talking in the
//! program's voice. `rust/HONESTY.md` §2 is what the trace says instead:
//! `<unread>`, with no reason given.
//!
//! **This code cannot panic, by construction.** A panic raised inside a panic
//! hook, while the thread is already panicking, aborts the process -- no
//! `catch_unwind` can intercept it, because the panic count is already 1 and
//! std aborts before unwinding. So the writer here allocates nothing (a
//! `PAYLOAD_MAX`-byte stack buffer and two `cap_utf8` slices), opens nothing (it
//! appends only to a spool this thread already has, so there is no file to
//! create and no error to report), indexes nothing it has not just bounded, and
//! calls nothing that can fail: the record lands in a mapping that already
//! exists, or the thread counts a drop. The one thing it does not do is record a
//! panic on a thread that never recorded an event -- such a thread has no frame
//! for the panic to close, and buying that record would cost the guarantee
//! above.
//!
//! **Truncation.** `loc` is capped at [`LOC_CAP`] and the message at
//! [`MSG_CAP`], both on a char boundary, so `2 + loc + msg` always fits the wire
//! format's `u16` payload length -- `spool::record` refuses an over-long payload
//! rather than clamping one. A PANIC record carries **no truncated byte of its
//! own**; the witness is the thread header's `truncated` counter, which
//! [`thread::note_truncated`] bumps whenever this writer cuts.

use std::fmt::{self, Write as _};
use std::panic::PanicHookInfo;
use std::sync::Once;

use crate::spool::{cap_utf8, KIND_PANIC, OUTCOME_NONE};
use crate::thread;

/// The most bytes of panic message one PANIC record carries. A `Debug`-style
/// bound, in the same spirit as `probe::CAP`: an `assert_eq!` over two large
/// collections renders a message that can run to megabytes, and a trace is not
/// the place to keep it.
const MSG_CAP: usize = 4096;

/// The most bytes of `"<file>:<line>:<col>"` one PANIC record carries. Paths in
/// `Location` are as the compiler saw them, so this is generous rather than
/// tight.
const LOC_CAP: usize = 512;

/// Whole payload: the `u16` length, the location, the message.
const PAYLOAD_MAX: usize = 2 + LOC_CAP + MSG_CAP;

/// What the record says when the payload is neither `&str` nor `String`.
const NON_STRING: &str = "<non-string payload>";

/// A PANIC is not at an instrumented site: the panic's own location is in the
/// payload, and its frame is the one whose RETURN follows. The site word is the
/// same not-a-site a `THREAD_END` record carries, and a reader keys on `kind`.
const NO_SITE: u32 = 0;

static INSTALLED: Once = Once::new();

/// Install the hook once per process, on the first `enter` that records.
///
/// Not from `init()`: `std::panic::set_hook` **panics** when it is called from a
/// panicking thread, and a first `enter` reached from a `Drop` running during an
/// unwind would turn that into a double panic and abort the process. Skipping
/// leaves `INSTALLED` uncompleted, so the next `enter` on a thread that is not
/// panicking installs it.
#[inline]
pub(crate) fn install() {
    if INSTALLED.is_completed() {
        return;
    }
    install_cold();
}

#[cold]
fn install_cold() {
    if std::thread::panicking() {
        return;
    }
    INSTALLED.call_once(|| {
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |info| {
            // Silence, both halves of it: no record, and no chaining either.
            if thread::in_runtime() {
                return;
            }
            record(info);
            // Every byte the program would have printed, printed by whoever was
            // going to print it. This is endpoint E7, and it is the reason the
            // hook chains instead of replacing.
            previous(info);
        }));
    });
}

fn record(info: &PanicHookInfo<'_>) {
    let mut buf = [0u8; PAYLOAD_MAX];
    let len = write_payload(&mut buf, info);
    thread::emit_if_open(NO_SITE, KIND_PANIC, OUTCOME_NONE, &buf[..len]);
}

/// `u16 loc_len, loc, msg` into `buf`, returning how much of it was used.
fn write_payload(buf: &mut [u8; PAYLOAD_MAX], info: &PanicHookInfo<'_>) -> usize {
    let mut loc = [0u8; LOC_CAP];
    let (loc_len, loc_cut) = write_location(&mut loc, info.location());
    let (msg, msg_cut) = cap_utf8(message(info), MSG_CAP);
    if loc_cut || msg_cut {
        // The header's counter is this record's only witness.
        thread::note_truncated();
    }
    buf[0..2].copy_from_slice(&(loc_len as u16).to_le_bytes());
    buf[2..2 + loc_len].copy_from_slice(&loc[..loc_len]);
    let end = 2 + loc_len + msg.len();
    buf[2 + loc_len..end].copy_from_slice(msg.as_bytes());
    end
}

/// The message, borrowed straight out of the payload. Nothing is formatted and
/// nothing is allocated: the two shapes std produces are `&'static str` (a
/// literal `panic!`) and `String` (a formatted one), and anything else is a
/// payload this hook cannot read rather than one it renders some other way.
fn message<'a>(info: &'a PanicHookInfo<'_>) -> &'a str {
    let payload = info.payload();
    if let Some(s) = payload.downcast_ref::<&'static str>() {
        return s;
    }
    if let Some(s) = payload.downcast_ref::<String>() {
        return s.as_str();
    }
    NON_STRING
}

/// `"<file>:<line>:<col>"` into a fixed buffer. `None` -- which std does not
/// currently produce -- writes an empty location rather than inventing one.
fn write_location(buf: &mut [u8; LOC_CAP], at: Option<&std::panic::Location<'_>>) -> (usize, bool) {
    let Some(at) = at else {
        return (0, false);
    };
    let mut w = Fixed {
        buf,
        len: 0,
        cut: false,
    };
    // The `Err` at the cap is `Fixed`'s own and is expected; nothing else in
    // this format can fail.
    let _ = write!(w, "{}:{}:{}", at.file(), at.line(), at.column());
    (w.len, w.cut)
}

/// A `fmt::Write` over a fixed buffer that stops the formatter at the cap by
/// failing, like `probe::CapWriter` -- and, like it, cuts on a char boundary so
/// what lands on the wire is UTF-8.
struct Fixed<'a> {
    buf: &'a mut [u8; LOC_CAP],
    len: usize,
    cut: bool,
}

impl fmt::Write for Fixed<'_> {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        let (s, cut) = cap_utf8(s, self.buf.len() - self.len);
        self.buf[self.len..self.len + s.len()].copy_from_slice(s.as_bytes());
        self.len += s.len();
        self.cut |= cut;
        if cut {
            return Err(fmt::Error);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_payload_bound_fits_the_wire_formats_length_field() {
        // `spool::record` refuses a payload it cannot describe rather than
        // clamping one, so this is the caller's half of that contract.
        assert!(PAYLOAD_MAX <= u16::MAX as usize, "{PAYLOAD_MAX} bytes");
    }

    #[test]
    fn a_location_is_file_line_and_column() {
        let mut buf = [0u8; LOC_CAP];
        let mut w = Fixed {
            buf: &mut buf,
            len: 0,
            cut: false,
        };
        let (file, line, col) = ("src/x.rs", 12u32, 5u32);
        write!(w, "{file}:{line}:{col}").expect("fits");
        let (len, cut) = (w.len, w.cut);
        assert!(!cut);
        assert_eq!(std::str::from_utf8(&buf[..len]), Ok("src/x.rs:12:5"));
    }

    /// The cap is per BUFFER, not per write. A writer that measured its room
    /// against the whole buffer each time would copy past the end of it the
    /// first time a location arrived in more than one piece -- which every
    /// location does, because `"{}:{}:{}"` is five writes.
    #[test]
    fn a_location_that_overflows_across_writes_stops_at_the_cap() {
        let mut buf = [0u8; LOC_CAP];
        let mut w = Fixed {
            buf: &mut buf,
            len: 0,
            cut: false,
        };
        let file = "a".repeat(LOC_CAP - 4);
        let _ = write!(w, "{file}:{}:{}", 123456, 78);
        let (len, cut) = (w.len, w.cut);
        assert!(cut, "1200 bytes of format do not fit {LOC_CAP}");
        assert_eq!(len, LOC_CAP, "filled to the cap, and not one byte past it");
    }

    #[test]
    fn an_over_long_location_is_cut_on_a_char_boundary_and_says_it_cut() {
        let mut buf = [0u8; LOC_CAP];
        let mut w = Fixed {
            buf: &mut buf,
            len: 0,
            cut: false,
        };
        // Three bytes each: the cap is not a multiple of three, so a cut that
        // did not step back would land inside a char.
        let file = "\u{20ac}".repeat(400);
        let _ = write!(w, "{file}:1:1");
        let (len, cut) = (w.len, w.cut);
        assert!(cut, "512 bytes cannot hold 1200");
        assert_eq!(len, 510, "3 does not divide 512; the cut steps back");
        assert!(std::str::from_utf8(&buf[..len]).is_ok());
    }
}
