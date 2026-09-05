//! A closure that contains a `?` gets its own frame (design R5): a guard at
//! its body's entry, its exits probed the way a fn's are, and a qualname of
//! `<enclosing item>::{{closure}}#k`. The `?` inside then belongs to the
//! CLOSURE's site rather than to the fn around it.

fn one() -> Result<u8, String> {
    Ok(1)
}

/// A block-bodied closure: the guard goes after its `{`, exactly as a fn's
/// does, and its tail is wrapped.
pub fn block_body() -> Result<u8, String> {
    let f = |n: u8| -> Result<u8, String> {
        let v = one()?;
        Ok(v + n)
    };
    f(1)
}

/// An EXPRESSION-bodied closure: the body becomes `{ guard; <expr> }`. A
/// closure with a declared return type must have a block body, so this one
/// takes its type from the call it is handed to.
pub fn expression_body() -> Result<u8, String> {
    one().and_then(|n| Ok(one()? + n))
}

/// Two `?`-bearing closures in one item are numbered in source order, and a
/// closure with no `?` between them takes no number at all.
pub fn two_of_them() -> Result<u8, String> {
    let a = |n: u8| -> Result<u8, String> { Ok(one()? + n) };
    let plain = |n: u8| n + 1;
    let b = |n: u8| -> Result<u8, String> { Ok(one()? + plain(n)) };
    a(1).and_then(b)
}

/// An expression-bodied closure with a `return` of its own: the `return`
/// operand is wrapped exactly as a fn's is, and the tail wrap goes around the
/// whole expression.
pub fn returning(c: bool) -> Result<u8, String> {
    let f = |n: u8| if c { return Ok(0) } else { Ok(one()? + n) };
    f(3)
}
