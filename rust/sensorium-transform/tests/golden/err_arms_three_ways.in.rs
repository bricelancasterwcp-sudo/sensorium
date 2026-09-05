//! `Err(..) =>` arms are classified syntactically at closure depth 0 (design
//! R2): PROPAGATE writes a RAISE at the arm's entry, PANIC writes NOTHING --
//! a probe there would move the `panic!`'s own column, which E7 measures --
//! and HANDLED writes the swallow candidate.

fn one() -> Result<u8, String> {
    Ok(1)
}

/// PROPAGATE: the arm's tail is `Err(..)`, so the error leaves this frame.
pub fn propagates() -> Result<u8, String> {
    match one() {
        Ok(v) => Ok(v),
        Err(e) => Err(e),
    }
}

/// PROPAGATE by a `?` at depth 0, with an UNBOUND pattern: no type and no
/// text to read, so the record says only that an error was seen here.
pub fn propagates_by_try() -> Result<u8, String> {
    match one() {
        Ok(v) => Ok(v),
        Err(_) => Ok(one()? + 1),
    }
}

/// PANIC: one of the four diverging macros at depth 0. No probe at all, so
/// the `panic!`'s own column is exactly where it was.
pub fn panics() -> u8 {
    match one() {
        Ok(v) => v,
        Err(e) => panic!("no: {e}"),
    }
}

/// HANDLED: the bound name is used only as a format argument and as a shared
/// borrow, which is what design R2 calls a provable non-escape.
pub fn handles() -> u8 {
    match one() {
        Ok(v) => v,
        Err(e) => {
            println!("{e}");
            note(&e);
            0
        }
    }
}

fn note(_e: &String) {}

/// An `assert!` is NOT one of the four diverging macros (the ruling of
/// 2026-09-04): this arm is HANDLED and the assert may well pass.
pub fn asserted(flag: bool) -> u8 {
    match one() {
        Ok(v) => v,
        Err(..) => {
            assert!(flag, "an assert is not a panic");
            0
        }
    }
}
