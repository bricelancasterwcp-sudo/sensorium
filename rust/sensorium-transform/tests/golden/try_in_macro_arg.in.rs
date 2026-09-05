//! A `?` inside a macro invocation's tokens. `syn` hands an invocation an
//! opaque token stream, so there is no `ExprTry` node to wrap: the site is
//! DECLARED (`partial`, reason `macro-arg`) rather than guessed at.

fn one() -> Result<u8, String> {
    Ok(1)
}

pub fn printed() -> Result<(), String> {
    println!("{}", one()?);
    Ok(())
}

/// A real `?` beside one in a macro argument: the walk sees this one, and the
/// two facts do not interfere.
pub fn both() -> Result<u8, String> {
    println!("{}", one()?);
    let v = one()?;
    Ok(v)
}
