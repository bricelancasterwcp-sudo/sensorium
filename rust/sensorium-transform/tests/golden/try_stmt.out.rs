//! A `?` in statement position and a `?` in a `let`. The wrap goes around the
//! OPERAND; the `?` itself stays outside it, so what the operator does is
//! untouched.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

pub fn discard() -> Result<(), String> {@G(8)
    @T(9)one()@TE?;
    @R(8)Ok(())@E
}

pub fn bound() -> Result<u8, String> {@G(10)
    let v = @T(11)one()@TE?;
    @R(10)Ok(v)@E
}

/// A parenthesised operand: the wrap goes INSIDE the parentheses, because
/// `match (one()) { .. }` is `unused_parens` and this is not.
pub fn parenthesised() -> Result<u8, String> {@G(12)
    let v = (@T(13)one()@TE)?;
    @R(12)Ok(v)@E
}@U
