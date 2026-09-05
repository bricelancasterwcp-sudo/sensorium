//! Struct literals in a wrap's `match` scrutinee. rustc forbids one in EVERY
//! exterior position, not just the leftmost, so the fence is a POST-CONDITION:
//! the wrap is built and handed back to `syn`, and a site whose wrap does not
//! re-parse is DECLARED (`partial`, reason `struct-literal`) rather than
//! emitted. Each of these four is "struct literals are not allowed here" when
//! wrapped (measured on rustc 1.96, 2026-09-04); none of them is wrapped here.

pub struct C {
    pub v: u8,
}

impl C {
    pub fn go(self) -> Result<u8, u8> {
        Ok(self.v)
    }
}

/// The leftmost position, which the fast path answers without a parse.
pub fn leftmost() -> Result<u8, u8> {
    let v = C { v: 1 }.go()?;
    let _ = C { v: 2 }.go();
    Ok(v)
}

/// The three the fast path cannot see: a binary operand, a range end, and a
/// closure body. All reachable through `let _ = <value expression>`.
pub fn exterior() {
    let _ = 1 + C { v: 1 }.v;
    let _ = 1..C { v: 2 }.v;
    let _ = || C { v: 3 };
}

/// The fence: parentheses protect the literal -- rustc's own suggestion -- and
/// then the site is ordinary and IS wrapped.
pub fn protected() -> Result<u8, u8> {
    let v = (C { v: 1 }).go()?;
    Ok(v)
}
