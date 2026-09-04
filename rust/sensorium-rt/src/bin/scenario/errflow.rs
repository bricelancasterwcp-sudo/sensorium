//! Err-flow sites: the shapes the transformer wraps at a `?`, a sink, and an
//! `Err(..)` arm, written by hand in exactly the form it injects (design R3, R4).
//!
//! Sites live in the 500 band. Every arm here uses one of the three verbatim
//! forms in `scenario.rs` (`serr!`, `serr_value!`, `serr_unbound!`), so the text
//! the transformer will emit is a text that compiles and behaves today.
//!
//! `failing`/`succeeding` are deliberately NOT instrumented: they stand in for
//! dependency code, the case where an `Err` is born outside anything the
//! recorder can see.

use std::io;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Dependency code that fails. No guard: the `Err` is born outside.
fn failing() -> Result<u8, String> {
    Err("boom".to_owned())
}

/// Dependency code that does not fail.
fn succeeding() -> Result<u8, String> {
    Ok(3)
}

/// An error type with NO `Debug` impl, so the ladder's second level answers:
/// the type is named, the message is unread.
pub(crate) struct NoDbgErr;

fn failing_nodebug() -> Result<u8, NoDbgErr> {
    Err(NoDbgErr)
}

/// A type whose NAME alone is longer than the 120-byte type cap, so the wire's
/// `type truncated` flag has something to witness that does not depend on how
/// any particular compiler spells a std path.
#[derive(Debug)]
pub(crate) struct AnErrorTypeWhoseNameIsDeliberatelyLongerThanTheOneHundredAndTwentyByteTypeCapSoTruncationHasSomethingToWitness(
    // Read by the derived `Debug`, which is the only reader this type needs.
    #[allow(dead_code)] pub String,
);

// ---------------------------------------------------------------------------
// `?`
// ---------------------------------------------------------------------------

/// The injected `?`-operand form written out longhand, once, so the `serr!`
/// macro is provably the same text.
fn try_verbatim(inner: Result<u8, String>) -> Result<u8, String> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 500);
    let v = match inner {
        __t => {
            ::sensorium_rt::err_site(
                &crate::__SENSORIUM_UNIT,
                501,
                ::sensorium_rt::HOW_TRY,
                || {
                    use ::sensorium_rt::probe::*;
                    (&&&Probe(&__t)).err_cap()
                },
            );
            __t
        }
    }?;
    sret!(500, Ok(v))
}

/// A `?` whose operand is `Err`: one RAISE at site 501, and the frame closes
/// `none` because the `?` bypassed its tail.
pub(crate) fn try_err() {
    let r = try_verbatim(failing());
    println!("returned {r:?}");
}

/// The same site with an `Ok` operand: no record at all, and the frame closes
/// `ok`.
pub(crate) fn try_ok() {
    let r = try_verbatim(succeeding());
    println!("returned {r:?}");
}

fn none_source() -> Option<u8> {
    None
}

/// A `?` on an `Option`. `None` is not an error in this model (design §6), so
/// the ladder's fallback answers and nothing is written.
fn try_option_inner() -> Option<u8> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 502);
    let v = serr!(503, ::sensorium_rt::HOW_TRY, none_source())?;
    sret!(502, Some(v))
}

pub(crate) fn try_option() {
    let r = try_option_inner();
    println!("returned {r:?}");
}

// ---------------------------------------------------------------------------
// Sinks
// ---------------------------------------------------------------------------

/// `.ok()` on an `Err` receiver: HANDLED, and the frame still closes `ok`.
fn sink_ok_frame(source: Result<u8, String>) -> Option<u8> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 510);
    let v = serr!(511, ::sensorium_rt::HOW_SINK_OK, source).ok();
    sret!(510, v)
}

pub(crate) fn sink_ok_err() {
    println!("sank {:?}", sink_ok_frame(failing()));
}

pub(crate) fn sink_ok_ok() {
    println!("sank {:?}", sink_ok_frame(succeeding()));
}

/// `let _ = <value expression>`: the value is dropped at the end of the
/// statement exactly as it was before the wrap.
pub(crate) fn let_underscore_err() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 512);
    let _ = serr!(513, ::sensorium_rt::HOW_SINK_LET_UNDERSCORE, failing());
    let v = serr!(514, ::sensorium_rt::HOW_SINK_UNWRAP_OR, failing()).unwrap_or(0);
    println!("unwrapped {v}");
}

// ---------------------------------------------------------------------------
// `Err(..)` arms
// ---------------------------------------------------------------------------

/// An arm that binds an error with a `Debug` impl: type and message.
pub(crate) fn arm_value_debug() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 520);
    match failing() {
        Ok(v) => println!("ok {v}"),
        Err(e) => {
            serr_value!(521, ::sensorium_rt::HOW_ARM_HANDLED, e);
            println!("handled {e}");
        }
    }
}

/// An arm that binds an error with no `Debug` impl: type only.
pub(crate) fn arm_value_nodebug() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 522);
    match failing_nodebug() {
        Ok(v) => println!("ok {v}"),
        Err(e) => {
            serr_value!(523, ::sensorium_rt::HOW_ARM_AMBIGUOUS, e);
            println!("handled a NoDbgErr");
        }
    }
}

/// `Err(_)` binds nothing, so the record carries neither a type nor a message.
pub(crate) fn arm_unbound() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 524);
    match failing() {
        Ok(v) => println!("ok {v}"),
        Err(_) => {
            serr_unbound!(525, ::sensorium_rt::HOW_ARM_PROPAGATE);
            println!("propagating");
        }
    }
}

// ---------------------------------------------------------------------------
// The ladder's second level, and both caps, over the wire
// ---------------------------------------------------------------------------

/// A `?` whose error type has no `Debug`: RAISE with a type and no message.
fn err_nodebug_inner() -> Result<u8, NoDbgErr> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 530);
    let v = serr!(531, ::sensorium_rt::HOW_TRY, failing_nodebug())?;
    sret!(530, Ok(v))
}

pub(crate) fn err_nodebug() {
    let r = err_nodebug_inner();
    println!("returned {}", r.is_ok());
}

/// Both caps at once: a type name longer than 120 bytes and a `Debug` rendering
/// longer than 200.
pub(crate) fn err_big() {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 540);
    let source: Result<u8, AnErrorTypeWhoseNameIsDeliberatelyLongerThanTheOneHundredAndTwentyByteTypeCapSoTruncationHasSomethingToWitness> =
        Err(AnErrorTypeWhoseNameIsDeliberatelyLongerThanTheOneHundredAndTwentyByteTypeCapSoTruncationHasSomethingToWitness("é".repeat(500)));
    let _ = serr!(541, ::sensorium_rt::HOW_SINK_LET_UNDERSCORE, source);
    println!("big done");
}

// ---------------------------------------------------------------------------
// The typed `err` RETURN
// ---------------------------------------------------------------------------

fn typed_err() -> Result<u8, io::Error> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 550);
    sret!(550, Err(io::Error::other("nope")))
}

fn typed_ok() -> Result<u8, io::Error> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 551);
    sret!(551, Ok(9))
}

/// An `err` whose value has no readable `Debug`: the RETURN's tag says unread
/// and the type block is there all the same.
fn typed_err_unread() -> Result<u8, NoDbgErr> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 552);
    sret!(552, Err(NoDbgErr))
}

pub(crate) fn typed_err_return() {
    println!("err {}", typed_err().is_err());
    println!("ok {}", typed_ok().is_ok());
    println!("unread {}", typed_err_unread().is_err());
}

// ---------------------------------------------------------------------------
// The capture closure is lazy
// ---------------------------------------------------------------------------

/// How many times [`CountingDbg`]'s `Debug` impl was entered in this process.
/// Printed at the end of the `errflow-lazy` arm, so a test can see whether the
/// capture ran without needing a spool to exist at all.
static DEBUG_CALLS: AtomicUsize = AtomicUsize::new(0);

/// A `Debug` impl that counts its own invocations and then panics.
///
/// The panic is the second half of the claim: at tier `call` it is caught by
/// `capture_debug` and the record reads unread, and at tier `off` it must never
/// be reached at all -- so a run that prints `debug_calls 0` proves the closure
/// was not called, and one that survives at tier `call` proves the catch still
/// holds for err sites.
struct CountingDbg;

impl std::fmt::Debug for CountingDbg {
    fn fmt(&self, _f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        DEBUG_CALLS.fetch_add(1, Ordering::Relaxed);
        panic!("this Debug impl panics on purpose");
    }
}

/// One `?` on an `Err(CountingDbg)`. Run at tier `off` the capture closure must
/// not be entered; run at tier `call` it is entered exactly once and its panic
/// is caught.
fn lazy_inner() -> Result<u8, CountingDbg> {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 560);
    let v = serr!(561, ::sensorium_rt::HOW_TRY, Err(CountingDbg))?;
    sret!(560, Ok(v))
}

pub(crate) fn errflow_lazy() {
    let previous = std::panic::take_hook();
    std::panic::set_hook(Box::new(|_| {}));
    let r = lazy_inner();
    std::panic::set_hook(previous);
    println!("returned {}", r.is_err());
    println!("debug_calls {}", DEBUG_CALLS.load(Ordering::Relaxed));
}
