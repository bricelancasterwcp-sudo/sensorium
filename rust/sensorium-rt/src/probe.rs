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

/// The most `Debug` text one return value -- or one recorded `Err` -- contributes,
/// in bytes.
pub(crate) const CAP: usize = 200;

/// The most `std::any::type_name` text one recorded `Err` contributes, in bytes
/// (design R1). A generic error type can render far longer than this; the wire's
/// `type truncated` flag is what says so.
pub(crate) const TYPE_CAP: usize = 120;

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

/// What the exit probe read: the frame's outcome and, on an `err`, the static
/// type of the `Result`'s error.
///
/// The type is here rather than in [`Capture`] because it is the *static* type
/// at the exit operand, known to the ladder without formatting anything, and
/// because the converter needs it to synthesise the origin RAISE of a chain that
/// left a frame by returning `Err` (design R1).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Exit {
    pub outcome: Outcome,
    /// `type_name::<E>()`, and only on an `Err`. `None` everywhere else --
    /// including on an `Ok`, where naming `E` would tell a reader about a value
    /// that never crossed the boundary.
    pub err_type: Option<&'static str>,
}

impl Exit {
    /// The answer for anything that is not a `Result::Err`.
    const fn ok() -> Exit {
        Exit {
            outcome: Outcome::Ok,
            err_type: None,
        }
    }
}

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
    fn seen(type_name: &'static str, capture: Capture) -> ErrCapture {
        ErrCapture {
            seen_err: true,
            type_name: Some(type_name),
            text: capture.text,
            truncated: capture.truncated,
        }
    }
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
    fn outcome(&self) -> Exit;
}

impl<T, E> ResultOutcome for &Probe<'_, Result<T, E>> {
    fn outcome(&self) -> Exit {
        match self.0 {
            Ok(_) => Exit::ok(),
            Err(_) => Exit {
                outcome: Outcome::Err,
                err_type: Some(std::any::type_name::<E>()),
            },
        }
    }
}

/// The fallback outcome. A value that is not a `Result` crossed the boundary,
/// which is `ok` -- see `rust/HONESTY.md` §1 for what that does and does not
/// claim.
pub trait AnyOutcome {
    fn outcome(&self) -> Exit;
}

impl<T: ?Sized> AnyOutcome for Probe<'_, T> {
    fn outcome(&self) -> Exit {
        Exit::ok()
    }
}

// ---------------------------------------------------------------------------
// The err-flow ladders
// ---------------------------------------------------------------------------

/// The `?`/sink ladder, level 1 (design R3): a `Result` whose ERROR type has a
/// `Debug` impl. Type and capped text.
///
/// Three levels, not rung 2's two, because the pair above answers about the
/// value as a whole: a `Result<T, E>` where `T` has no `Debug` reads *unread*
/// through `debug_cap`, although `E`'s own `Debug` is perfectly readable. The
/// call site is `(&&&Probe(&__t)).err_cap()` -- one `&` deeper than level 1's
/// receiver needs, so lookup tries level 1, then level 2, then the fallback.
pub trait ErrCapDebug {
    fn err_cap(&self) -> ErrCapture;
}

impl<T, E: Debug> ErrCapDebug for &&Probe<'_, Result<T, E>> {
    fn err_cap(&self) -> ErrCapture {
        match self.0 {
            Ok(_) => ErrCapture::nothing(),
            Err(e) => ErrCapture::seen(std::any::type_name::<E>(), capture_debug(e)),
        }
    }
}

/// Level 2: a `Result` whose error type has no `Debug`. The type is still known
/// statically, so the trace names it and says the message was unread.
pub trait ErrCapTyped {
    fn err_cap(&self) -> ErrCapture;
}

impl<T, E> ErrCapTyped for &Probe<'_, Result<T, E>> {
    fn err_cap(&self) -> ErrCapture {
        match self.0 {
            Ok(_) => ErrCapture::nothing(),
            Err(_) => ErrCapture::seen(
                std::any::type_name::<E>(),
                Capture {
                    text: None,
                    truncated: false,
                },
            ),
        }
    }
}

/// Level 3, the fallback: the operand is not a `Result` at all -- an `Option`, a
/// plain value, a generic `T`. Nothing is an error here and nothing is written.
pub trait ErrCapNone {
    fn err_cap(&self) -> ErrCapture;
}

impl<T: ?Sized> ErrCapNone for Probe<'_, T> {
    fn err_cap(&self) -> ErrCapture {
        ErrCapture::nothing()
    }
}

/// The arm ladder, level 1 (design R4): an `Err(e) =>` arm is handed the bound
/// `E` itself, not a `Result`, so R3's ladder cannot apply. Two levels, and the
/// type is known on both -- an arm that matched `Err` HAS an error, which is why
/// `seen_err` is true whatever the `Debug` situation.
pub trait ErrCapValueDebug {
    fn err_cap_value(&self) -> ErrCapture;
}

impl<E: Debug + ?Sized> ErrCapValueDebug for &Probe<'_, E> {
    fn err_cap_value(&self) -> ErrCapture {
        ErrCapture::seen(std::any::type_name::<E>(), capture_debug(self.0))
    }
}

/// The arm ladder's fallback: the bound error has no `Debug` impl.
pub trait ErrCapValueNone {
    fn err_cap_value(&self) -> ErrCapture;
}

impl<E: ?Sized> ErrCapValueNone for Probe<'_, E> {
    fn err_cap_value(&self) -> ErrCapture {
        ErrCapture::seen(
            std::any::type_name::<E>(),
            Capture {
                text: None,
                truncated: false,
            },
        )
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
        assert_eq!((&&Probe(&ok)).outcome().outcome, Outcome::Ok);
        assert_eq!((&&Probe(&err)).outcome().outcome, Outcome::Err);
    }

    #[test]
    fn autoref_falls_back_to_ok_for_a_non_result() {
        assert_eq!((&&Probe(&3u8)).outcome().outcome, Outcome::Ok);
        assert_eq!((&&Probe(&NoDbg)).outcome().outcome, Outcome::Ok);
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
    // -----------------------------------------------------------------------
    // The err-flow ladders (R3, R4)
    // -----------------------------------------------------------------------

    /// The critic's four arms, in one test each. A two-level ladder on the
    /// whole `Result` reads arm three as unread; three levels is what separates
    /// "no `Debug` on `E`" from "no `Debug` on `T`".
    #[test]
    fn the_ladder_reads_type_and_text_when_the_error_type_has_debug() {
        let e: Result<u8, String> = Err("boom".to_owned());
        let c = (&&&Probe(&e)).err_cap();
        assert!(c.seen_err);
        assert!(
            c.type_name
                .expect("a Result knows its E")
                .ends_with("String"),
            "{:?}",
            c.type_name
        );
        assert_eq!(c.text.as_deref(), Some(r#""boom""#));
        assert!(!c.truncated);
    }

    #[test]
    fn the_ladder_reads_the_type_only_when_the_error_type_has_no_debug() {
        let e: Result<u8, NoDbg> = Err(NoDbg);
        let c = (&&&Probe(&e)).err_cap();
        assert!(c.seen_err);
        assert!(
            c.type_name
                .expect("a Result knows its E")
                .ends_with("NoDbg"),
            "{:?}",
            c.type_name
        );
        assert_eq!(c.text, None, "no Debug on E is an unread message");
        assert!(!c.truncated);
    }

    /// The arm rung 2's two-level trick gets wrong: the OK type has no `Debug`,
    /// the error type does, and the error's text is readable.
    #[test]
    fn the_ladder_reads_a_debug_error_even_when_the_ok_type_has_none() {
        let e: Result<NoDbg, std::io::Error> = Err(std::io::Error::other("nope"));
        let c = (&&&Probe(&e)).err_cap();
        assert!(c.seen_err);
        assert!(
            c.type_name
                .expect("a Result knows its E")
                .ends_with("Error"),
            "{:?}",
            c.type_name
        );
        assert!(
            c.text.as_deref().unwrap_or_default().contains("nope"),
            "{:?}",
            c.text
        );
    }

    #[test]
    fn the_ladder_reads_nothing_at_all_from_a_non_result() {
        let o: Option<u8> = None;
        let c = (&&&Probe(&o)).err_cap();
        assert!(!c.seen_err, "an Option is not an error in this model");
        assert_eq!(c.type_name, None);
        assert_eq!(c.text, None);
        let c = (&&&Probe(&3u8)).err_cap();
        assert!(!c.seen_err);
    }

    #[test]
    fn the_ladder_reads_nothing_from_an_ok() {
        let ok: Result<u8, String> = Ok(1);
        let c = (&&&Probe(&ok)).err_cap();
        assert!(!c.seen_err, "an Ok is not an Err");
        assert_eq!(c.type_name, None);
        assert_eq!(c.text, None);
        let ok: Result<u8, NoDbg> = Ok(1);
        assert!(!(&&&Probe(&ok)).err_cap().seen_err);
    }

    #[test]
    fn the_ladders_message_is_capped_and_says_it_cut() {
        let e: Result<u8, String> = Err("x".repeat(1000));
        let c = (&&&Probe(&e)).err_cap();
        assert_eq!(c.text.as_deref().map(str::len), Some(CAP));
        assert!(c.truncated);
    }

    #[test]
    fn a_panicking_debug_on_the_error_reads_unread_without_unwinding() {
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(|_| {}));
        let e: Result<u8, PanicDbg> = Err(PanicDbg);
        let c = (&&&Probe(&e)).err_cap();
        std::panic::set_hook(previous);
        assert!(
            c.seen_err,
            "the Err was seen even though its Debug panicked"
        );
        assert!(
            c.type_name.is_some(),
            "the type is known without formatting"
        );
        assert_eq!(c.text, None);
        assert!(!c.truncated);
    }

    /// The arm ladder (R4): two levels, on the bound `E` rather than a
    /// `Result`, and the type is known on both arms.
    #[test]
    fn the_arm_ladder_reads_the_bound_error_with_debug() {
        let e = "boom".to_owned();
        let c = (&&Probe(&e)).err_cap_value();
        assert!(c.seen_err);
        assert!(c.type_name.expect("E is named").ends_with("String"));
        assert_eq!(c.text.as_deref(), Some(r#""boom""#));
    }

    #[test]
    fn the_arm_ladder_reads_the_type_only_when_the_bound_error_has_no_debug() {
        let c = (&&Probe(&NoDbg)).err_cap_value();
        assert!(c.seen_err);
        assert!(c.type_name.expect("E is named").ends_with("NoDbg"));
        assert_eq!(c.text, None);
    }

    /// Match ergonomics bind by reference; the converter strips the leading `&`
    /// (R4), so the runtime is free to record the reference type it was handed.
    #[test]
    fn the_arm_ladder_answers_for_a_by_reference_binding() {
        let e = "boom".to_owned();
        let by_ref: &String = &e;
        let c = (&&Probe(&by_ref)).err_cap_value();
        assert!(c.seen_err);
        assert!(c.type_name.expect("E is named").contains("String"));
        assert_eq!(c.text.as_deref(), Some(r#""boom""#));
    }

    /// The exit probe now carries `E`'s type on an `Err`, and nothing on
    /// anything else: that is what lets a RETURN carry the type the reader needs
    /// to synthesise the origin RAISE.
    #[test]
    fn the_exit_probe_names_the_error_type_only_on_an_err() {
        let ok: Result<u8, String> = Ok(1);
        let err: Result<u8, String> = Err("e".to_owned());
        assert_eq!((&&Probe(&ok)).outcome().err_type, None);
        assert!((&&Probe(&err))
            .outcome()
            .err_type
            .expect("an Err knows its E")
            .ends_with("String"));
        assert_eq!((&&Probe(&3u8)).outcome().err_type, None);
    }
}
