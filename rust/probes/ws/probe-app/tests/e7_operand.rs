//! E7''(rung 3): one panic literal INSIDE a `?` operand.
//!
//! `tests/e7.rs` pins that an instrumented build moves no panic location for a
//! panic that is not inside a wrapped operand. Rung 3 still wraps the operand
//! of every `?` in `match <operand> { __t => .. }`, and `match ` is six bytes
//! spliced at the operand's first byte, so this panic's column moves in the
//! bytes rustc compiles. The runtime maps it back: the reported column equals
//! the plain build's. The line does not move: the wrap never inserts a newline.
//!
//! This file is a SEPARATE test target on purpose. Putting the panic in
//! `tests/e7.rs` would make the unchanged E7 checks (byte-identical output for
//! panics whose columns were not shifted) fail by construction if the map ever
//! stopped applying.
//!
//! The test is `#[should_panic]` so the probe suite stays green in every arm;
//! the panic HOOK still prints `panicked at <file>:<line>:<col>` to
//! `--nocapture` stderr, which is the text `mechanics.sh` reads.

/// Takes a thunk so the panic's call site is a literal INSIDE the operand of
/// the `?` below, rather than inside this fn.
fn compute(f: impl Fn() -> u32) -> Result<u32, String> {
    Ok(f())
}

/// The measured line is the `let v = ...?;` one. Everything the transformer
/// splices on it is the operand wrap and nothing else: the fn's entry guard
/// goes after this fn's opening brace (the signature's line), and the exit
/// wrap goes around the tail expression (its own line), so `match ` is the
/// only insertion before the `panic!` token.
fn run_operand() -> Result<u32, String> {
    let v = compute(|| panic!("operand probe panic"))?;
    Ok(v)
}

#[test]
#[should_panic(expected = "operand probe panic")]
fn panics_inside_a_try_operand() {
    println!("e7-operand: about to panic at {}:{}", file!(), line!());
    let _ = run_operand();
}
