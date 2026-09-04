//! The panic shapes: caught by an instrumented frame, uncaught out of `main`,
//! a non-string payload, and a message past the hook's cap.

// ---------------------------------------------------------------------------
// Panics
// ---------------------------------------------------------------------------

/// An instrumented frame that CATCHES an instrumented frame's panic. The outer
/// returns a `u8` rather than the `Result` `catch_unwind` handed it: an `Err` at
/// the exit operand would close the outer frame `err`, and what this arm pins is
/// that catching a panic leaves the catching frame `ok`.
fn caught_outer() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 17);
    let caught = std::panic::catch_unwind(panicking_inner).is_err();
    sret!(17, u8::from(caught))
}

#[rustfmt::skip]
fn panicking_inner() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 16);
    println!("panic_site {}:{}", file!(), line!()); panic!("caught boom");
}

pub(crate) fn panic_caught_scenario() {
    println!("caught {}", caught_outer());
}

#[rustfmt::skip]
fn panics_uncaught() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 18);
    println!("panic_site {}:{}", file!(), line!()); panic!("uncaught boom");
}

/// Unwinds out of `main`: the thread-local destructor still runs, so the spool
/// still ends with `THREAD_END`, and the process still exits 101.
pub(crate) fn panic_uncaught_scenario() {
    std::hint::black_box(panics_uncaught());
}

/// A payload that is neither `&str` nor `String`.
#[rustfmt::skip]
fn panics_with_a_number() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 19);
    println!("panic_site {}:{}", file!(), line!()); std::panic::panic_any(7u32);
}

pub(crate) fn panic_non_string_scenario() {
    let r = std::panic::catch_unwind(panics_with_a_number);
    assert!(r.is_err(), "the scenario must actually unwind");
    println!("unwound 1");
}

/// A message far past the hook's cap, in three-byte characters so a cut that
/// did not step back to a char boundary would not be UTF-8.
fn panics_at_length() -> u8 {
    let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, 26);
    let msg = "\u{20ac}".repeat(2000);
    println!("msg_bytes {}", msg.len());
    panic!("{msg}");
}

pub(crate) fn panic_long_scenario() {
    let r = std::panic::catch_unwind(panics_at_length);
    assert!(r.is_err(), "the scenario must actually unwind");
    println!("unwound 1");
}
