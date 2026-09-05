//! A `?` inside a macro invocation's tokens. `syn` hands an invocation an
//! opaque token stream, so there is no `ExprTry` node to wrap: the site is
//! DECLARED (`partial`, reason `macro-arg`) rather than guessed at.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

pub fn printed() -> Result<(), String> {@G(8)
    println!("{}", one()?);
    @R(8)Ok(())@E
}

/// A real `?` beside one in a macro argument: the walk sees this one, and the
/// two facts do not interfere.
pub fn both() -> Result<u8, String> {@G(9)
    println!("{}", one()?);
    let v = @T(10)one()@TE?;
    @R(9)Ok(v)@E
}@U
