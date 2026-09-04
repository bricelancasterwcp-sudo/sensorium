//! E7(a)'s two probes: line numbers, paths and backtrace frames must be
//! byte-identical between a plain build and an instrumented one.
//!
//! Both tests are `#[should_panic]` so the probe workspace's suite is green in
//! every arm; the panic HOOK still prints `panicked at <file>:<line>:<col>`
//! (and, under `RUST_BACKTRACE=1`, the backtrace) to `--nocapture` stderr,
//! which is the text E7 diffs.

/// A known message, panicked at a known place.
#[test]
#[should_panic(expected = "known probe panic")]
fn panics_with_a_known_message() {
    println!("e7: about to panic at {}:{}", file!(), line!());
    panic!("known probe panic");
}

/// An assert whose message embeds `file!()` and `line!()`.
#[test]
#[should_panic(expected = "probe assert at")]
fn assert_message_embeds_file_and_line() {
    let here = format!("probe assert at {}:{}", file!(), line!());
    println!("e7: file!() = {}, line!() = {}", file!(), line!());
    // Parsed, not folded: a constant assertion is folded away by the compiler
    // and would move the location E7 is measuring.
    let two: u32 = "2".parse().expect("a literal 2 parses");
    assert!(two == 3, "{here}");
}
