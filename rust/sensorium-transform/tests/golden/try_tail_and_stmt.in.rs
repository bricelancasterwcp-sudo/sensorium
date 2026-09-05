//! The exit wrap and the err wrap on one operand. The `?` wrap opens INSIDE the
//! exit wrap and closes before it, which is the whole of the splice ordering
//! rule between the two kinds; nested `?` close innermost-first.

fn one() -> Result<u8, String> {
    Ok(1)
}

fn twice() -> Result<Result<u8, String>, String> {
    Ok(Ok(2))
}

/// A `?` nested in the tail's own call argument.
pub fn wrapped_tail() -> Result<u8, String> {
    Ok(one()?)
}

/// A tail that IS the `?`: both wraps open on the same byte.
pub fn try_is_the_tail() -> Result<u8, String> {
    twice()?
}

/// Two `?` on one operand: both open on the same byte, and the inner one
/// closes first.
pub fn nested_try() -> Result<u8, String> {
    let v = twice()??;
    Ok(v)
}
