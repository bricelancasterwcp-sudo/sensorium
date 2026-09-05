#![deny(warnings)]
#![allow(dead_code)]@W

// A crate root whose inner attributes are real ones. The injected allow shares
// the LAST one's line, so the line count is unchanged and `#![..]` still
// precedes every item. `deny(warnings)` is the SOURCE's own, which makes this
// golden a test of "no new diagnostics" and not only of placement.

pub fn f() -> Result<u8, u8> {@G(7)
    let v = @T(8)g()@TE?;
    @R(7)Ok(v)@E
}

fn g() -> Result<u8, u8> {@G(9)
    @R(9)Ok(1)@E
}@U
