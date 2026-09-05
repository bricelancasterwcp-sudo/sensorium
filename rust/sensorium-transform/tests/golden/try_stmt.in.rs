//! A `?` in statement position and a `?` in a `let`. The wrap goes around the
//! OPERAND; the `?` itself stays outside it, so what the operator does is
//! untouched.

fn one() -> Result<u8, String> {
    Ok(1)
}

pub fn discard() -> Result<(), String> {
    one()?;
    Ok(())
}

pub fn bound() -> Result<u8, String> {
    let v = one()?;
    Ok(v)
}

/// A parenthesised operand: the wrap goes INSIDE the parentheses, because
/// `match (one()) { .. }` is `unused_parens` and this is not.
pub fn parenthesised() -> Result<u8, String> {
    let v = (one())?;
    Ok(v)
}
