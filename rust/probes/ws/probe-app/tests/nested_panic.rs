//! Two frames deep, and one frame that catches.
//!
//! `panics_two_frames_deep` panics inside `panic_inner`, which was called by
//! `panic_outer`, which was called here: both of those frames must close
//! `unwind` with an `unwind_exc` of type `panic`.
//! `a_caught_panic_returns_normally` catches the same panic, so its own frame
//! closes `return` with an `ok` outcome — the pair is what says the converter
//! tells a caught panic from an escaping one.

#[test]
#[should_panic(expected = "probe nested panic: deep")]
fn panics_two_frames_deep() {
    let _unreachable = probe_app::panic_outer("deep");
}

#[test]
fn a_caught_panic_returns_normally() {
    assert_eq!(probe_app::catch_inner_panic("caught"), 7);
}
