//! A closure that contains a `?` gets its own frame (design R5): a guard at
//! its body's entry, its exits probed the way a fn's are, and a qualname of
//! `<enclosing item>::{{closure}}#k`. The `?` inside then belongs to the
//! CLOSURE's site rather than to the fn around it.
@W
fn one() -> Result<u8, String> {@G(7)
    @R(7)Ok(1)@E
}

/// A block-bodied closure: the guard goes after its `{`, exactly as a fn's
/// does, and its tail is wrapped.
pub fn block_body() -> Result<u8, String> {@G(8)
    let f = |n: u8| -> Result<u8, String> {@K(9)
        let v = @T(10)one()@TE?;
        @R(9)Ok(v + n)@E
    };
    @R(8)f(1)@E
}

/// An EXPRESSION-bodied closure: the body becomes `{ guard; <expr> }`. A
/// closure with a declared return type must have a block body, so this one
/// takes its type from the call it is handed to.
pub fn expression_body() -> Result<u8, String> {@G(11)
    @R(11)one().and_then(|n| { @K(12) @R(12)Ok(@T(13)one()@TE? + n)@E })@E
}

/// Two `?`-bearing closures in one item are numbered in source order, and a
/// closure with no `?` between them takes no number at all.
pub fn two_of_them() -> Result<u8, String> {@G(14)
    let a = |n: u8| -> Result<u8, String> {@K(15) @R(15)Ok(@T(16)one()@TE? + n)@E };
    let plain = |n: u8| n + 1;
    let b = |n: u8| -> Result<u8, String> {@K(17) @R(17)Ok(@T(18)one()@TE? + plain(n))@E };
    @R(14)a(1).and_then(b)@E
}

/// An expression-bodied closure with a `return` of its own: the `return`
/// operand is wrapped exactly as a fn's is, and the tail wrap goes around the
/// whole expression.
pub fn returning(c: bool) -> Result<u8, String> {@G(19)
    let f = |n: u8| { @K(20) @R(20)if c { return @R(20)Ok(0)@E } else { Ok(@T(21)one()@TE? + n) }@E };
    @R(19)f(3)@E
}@U
