//! Reading a return value without knowing anything about its type.
//!
//! The transformer wraps every exit operand of a value-returning function in
//!
//! ```ignore
//! ::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, SITE, |__r| {
//!     use ::sensorium_rt::probe::*;
//!     ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome())
//! }, <e>)
//! ```
//!
//! and the two method calls resolve by **autoref specialisation** (dtolnay's
//! case study): the specialised impls sit on `&Probe<'_, T>` and the fallbacks
//! on `Probe<'_, T>` by value, every method takes `&self`, and the call site
//! starts one reference deeper than the specialised receiver needs. Method
//! lookup tries `&&Probe<T>` first, which only the specialised impl can be the
//! receiver of; when its bound does not hold it derefs to `&Probe<T>` and the
//! fallback answers. Turn any of those three details around -- `self` by value,
//! impls on `&&Probe`, one fewer `&` at the call site -- and the fallback wins
//! every time (measured 2026-09-02: the specialised trait was reported dead).
//! The `tests` module below pins both arms of both pairs.
//!
//! **The cap.** `Debug` is formatted through a writer that returns `Err` once it
//! has taken 200 bytes. What that bounds, exactly (measured 2026-09-02, and
//! narrower than the plan assumed -- see `rust/HONESTY.md` §2):
//!
//! * **Always**: the bytes captured, the `String` allocated, and the wire
//!   payload. 200 bytes for a three-element `Vec` and for a 10^6-element one.
//! * **When the `Debug` impl propagates the error** -- the `write!(f, ..)?`
//!   idiom nearly every hand-written impl uses -- the formatter stops there, so
//!   the work is O(cap): 10^7 items cost 1.5 us with the cap and 99 ms without.
//! * **Not** for std's collection impls. `Formatter::debug_list`/`debug_map`
//!   short-circuit their WRITES once the writer errors but still walk every
//!   element, so a 10^6-element `Vec<u8>` capture costs ~10 ms either way. The
//!   traversal is the collection's, and this writer cannot shorten it.
//!
//! **The catch.** The whole formatting runs under
//! `catch_unwind`, so a `Debug` impl that panics reads `<unread>` and the
//! program is not unwound -- indistinguishable in the trace from a type with no
//! `Debug` impl at all, which is what `rust/HONESTY.md` §2 says it is.

use std::fmt::{self, Debug, Write as _};
use std::panic::AssertUnwindSafe;

/// The most `Debug` text one return value contributes, in bytes.
pub(crate) const CAP: usize = 200;

/// What was read off a return value. `text: None` means *unread* -- not empty,
/// and never `()`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Capture {
    pub text: Option<String>,
    pub truncated: bool,
}

/// The frame's outcome, as the wire carries it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum Outcome {
    None = 0,
    Ok = 1,
    Err = 2,
    Panic = 3,
}

/// The wrapper the injected closure builds around a borrow of the return value.
pub struct Probe<'a, T: ?Sized>(pub &'a T);

/// The specialised capture: the value has a `Debug` impl.
pub trait DebugCap {
    fn debug_cap(&self) -> Capture;
}

impl<T: Debug + ?Sized> DebugCap for &Probe<'_, T> {
    fn debug_cap(&self) -> Capture {
        capture_debug(self.0)
    }
}

/// The fallback capture: the value has no `Debug` impl, so there is nothing to
/// read and the trace says so.
pub trait NoDebugCap {
    fn debug_cap(&self) -> Capture;
}

impl<T: ?Sized> NoDebugCap for Probe<'_, T> {
    fn debug_cap(&self) -> Capture {
        Capture {
            text: None,
            truncated: false,
        }
    }
}

/// The specialised outcome: the static type at the exit operand is a `Result`.
pub trait ResultOutcome {
    fn outcome(&self) -> Outcome;
}

impl<T, E> ResultOutcome for &Probe<'_, Result<T, E>> {
    fn outcome(&self) -> Outcome {
        match self.0 {
            Ok(_) => Outcome::Ok,
            Err(_) => Outcome::Err,
        }
    }
}

/// The fallback outcome. A value that is not a `Result` crossed the boundary,
/// which is `ok` -- see `rust/HONESTY.md` §1 for what that does and does not
/// claim.
pub trait AnyOutcome {
    fn outcome(&self) -> Outcome;
}

impl<T: ?Sized> AnyOutcome for Probe<'_, T> {
    fn outcome(&self) -> Outcome {
        Outcome::Ok
    }
}

/// A `fmt::Write` that stops the formatter at [`CAP`] bytes by failing.
struct CapWriter {
    out: String,
    overflowed: bool,
}

impl fmt::Write for CapWriter {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        let room = CAP - self.out.len();
        if s.len() <= room {
            self.out.push_str(s);
            return Ok(());
        }
        let mut end = room;
        while end > 0 && !s.is_char_boundary(end) {
            end -= 1;
        }
        self.out.push_str(&s[..end]);
        self.overflowed = true;
        // The error is the point: `Debug::fmt` propagates it and stops.
        Err(fmt::Error)
    }
}

fn capture_debug<T: Debug + ?Sized>(value: &T) -> Capture {
    let formatted = std::panic::catch_unwind(AssertUnwindSafe(|| {
        let mut w = CapWriter {
            out: String::with_capacity(CAP),
            overflowed: false,
        };
        // The `Err` at the cap is expected and is the writer's own; nothing else
        // in `{:?}` can fail.
        let _ = write!(w, "{value:?}");
        (w.out, w.overflowed)
    }));
    match formatted {
        Ok((text, truncated)) => {
            if truncated {
                crate::thread::note_truncated();
            }
            Capture {
                text: Some(text),
                truncated,
            }
        }
        // A workspace `Debug` impl panicked inside the instrument. The program
        // is not unwound and the panic hook stays silent for it; the trace says
        // "not read", and does not say why.
        Err(_) => Capture {
            text: None,
            truncated: false,
        },
    }
}

#[cfg(test)]
// `(&&Probe(x))` is the transformer's call site, character for character. On the
// fallback arms one `&` is redundant and clippy says so -- but dropping it is
// exactly the mistake this module exists to catch, because the specialised impl
// then never wins on the arms where it should.
#[allow(clippy::needless_borrow)]
mod tests {
    use super::*;

    struct NoDbg;

    struct PanicDbg;

    impl Debug for PanicDbg {
        fn fmt(&self, _f: &mut fmt::Formatter<'_>) -> fmt::Result {
            panic!("this Debug impl panics on purpose");
        }
    }

    #[test]
    fn autoref_picks_the_debug_impl_when_there_is_one() {
        let c = (&&Probe(&3u8)).debug_cap();
        assert_eq!(c.text.as_deref(), Some("3"));
        assert!(!c.truncated);
    }

    #[test]
    fn autoref_falls_back_when_there_is_no_debug_impl() {
        let c = (&&Probe(&NoDbg)).debug_cap();
        assert_eq!(c.text, None);
        assert!(!c.truncated);
    }

    #[test]
    fn autoref_picks_the_result_outcome_when_the_type_is_a_result() {
        let ok: Result<u8, String> = Ok(1);
        let err: Result<u8, String> = Err("e".to_owned());
        assert_eq!((&&Probe(&ok)).outcome(), Outcome::Ok);
        assert_eq!((&&Probe(&err)).outcome(), Outcome::Err);
    }

    #[test]
    fn autoref_falls_back_to_ok_for_a_non_result() {
        assert_eq!((&&Probe(&3u8)).outcome(), Outcome::Ok);
        assert_eq!((&&Probe(&NoDbg)).outcome(), Outcome::Ok);
    }

    /// A `Debug` impl that propagates the writer's error, which is what a
    /// hand-written one does. The formatter must stop at the cap, not run to
    /// the end of the value and have its output discarded.
    struct EarlyStop(u32);

    impl Debug for EarlyStop {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            for i in 0..self.0 {
                write!(f, "{i},")?;
            }
            Ok(())
        }
    }

    #[test]
    fn the_cap_stops_a_cooperating_formatter_rather_than_cutting_its_output() {
        let started = std::time::Instant::now();
        let c = (&&Probe(&EarlyStop(10_000_000))).debug_cap();
        let elapsed = started.elapsed();
        assert_eq!(c.text.as_deref().map(str::len), Some(CAP));
        assert!(c.truncated);
        assert!(
            elapsed.as_millis() < 10,
            "10^7 items should cost O(cap) once the writer errors, took {elapsed:?}"
        );
    }

    #[test]
    fn the_cap_bounds_the_bytes_of_a_collection_whose_impl_does_not_stop() {
        // std's `debug_list` walks the whole collection whatever the writer
        // says, so the COST is the vector's -- but the capture is still the cap.
        let c = (&&Probe(&vec![7u8; 100_000])).debug_cap();
        assert_eq!(c.text.as_deref().map(str::len), Some(CAP));
        assert!(c.truncated);
    }

    #[test]
    fn a_value_that_fits_is_not_marked_truncated() {
        let c = (&&Probe(&vec![1u8, 2, 3])).debug_cap();
        assert_eq!(c.text.as_deref(), Some("[1, 2, 3]"));
        assert!(!c.truncated);
    }

    #[test]
    fn the_cap_never_cuts_a_multi_byte_char_in_half() {
        let s = "é".repeat(500);
        let c = (&&Probe(&s)).debug_cap();
        let text = c.text.expect("String has a Debug impl");
        assert!(text.len() <= CAP);
        assert!(text.is_char_boundary(text.len()));
        assert!(c.truncated);
    }

    #[test]
    fn a_panicking_debug_impl_reads_unread_without_unwinding() {
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(|_| {}));
        let c = (&&Probe(&PanicDbg)).debug_cap();
        std::panic::set_hook(previous);
        assert_eq!(c.text, None);
        assert!(!c.truncated);
    }
}
