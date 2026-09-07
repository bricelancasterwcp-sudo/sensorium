//! The second test binary. It shares no code with `a.rs` on purpose: this
//! crate has no lib target, so there are no doctests and no unit-test
//! binary, and `cargo test` builds exactly these two.

fn halve(n: u32) -> u32 {
    n / 2
}

#[test]
fn b_halves() {
    assert_eq!(halve(4), 2);
}
