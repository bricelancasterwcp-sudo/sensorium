//! The exit wrap and the err wrap on one operand. The `?` wrap opens INSIDE the
//! exit wrap and closes before it, which is the whole of the splice ordering
//! rule between the two kinds; nested `?` close innermost-first.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

fn twice() -> Result<Result<u8, String>, String> {@G(8)
    @R(8)Ok(Ok(2))@E
}

/// A `?` nested in the tail's own call argument.
pub fn wrapped_tail() -> Result<u8, String> {@G(9)
    @R(9)Ok(@T(10)one()@TE?)@E
}

/// A tail that IS the `?`: both wraps open on the same byte.
pub fn try_is_the_tail() -> Result<u8, String> {@G(11)
    @R(11)@T(12)twice()@TE?@E
}

/// Two `?` on one operand: both open on the same byte, and the inner one
/// closes first.
pub fn nested_try() -> Result<u8, String> {@G(13)
    let v = @T(14)@T(15)twice()@TE?@TE?;
    @R(13)Ok(v)@E
}@U
