//! Struct literals in a wrap's `match` scrutinee. rustc forbids one in EVERY
//! exterior position, not just the leftmost, so the fence is a POST-CONDITION:
//! the wrap is built and handed back to `syn`, and a site whose wrap does not
//! re-parse is DECLARED (`partial`, reason `struct-literal`) rather than
//! emitted. Each of these four is "struct literals are not allowed here" when
//! wrapped (measured on rustc 1.96, 2026-09-04); none of them is wrapped here.
@W
pub struct C {
    pub v: u8,
}

impl C {
    pub fn go(self) -> Result<u8, u8> {@G(7)
        @R(7)Ok(self.v)@E
    }
}

/// The leftmost position, which the fast path answers without a parse.
pub fn leftmost() -> Result<u8, u8> {@G(8)
    let v = C { v: 1 }.go()?;
    let _ = C { v: 2 }.go();
    @R(8)Ok(v)@E
}

/// The three the fast path cannot see: a binary operand, a range end, and a
/// closure body. All reachable through `let _ = <value expression>`.
pub fn exterior() {@G(9)
    let _ = 1 + C { v: 1 }.v;
    let _ = 1..C { v: 2 }.v;
    let _ = || C { v: 3 };
}

/// The fence: parentheses protect the literal -- rustc's own suggestion -- and
/// then the site is ordinary and IS wrapped.
pub fn protected() -> Result<u8, u8> {@G(10)
    let v = @T(11)(C { v: 1 }).go()@TE?;
    @R(10)Ok(v)@E
}@U
