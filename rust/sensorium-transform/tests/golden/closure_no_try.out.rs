//! A closure with no `?` is left exactly as it was: no frame, no guard, no
//! site. This is the fence for design R5's "closures without `?` stay
//! unframed" -- framing one would cost a CALL/RETURN pair per call for
//! nothing at all.
@W
pub fn mapped(v: &[u8]) -> Vec<u8> {@G(7)
    @R(7)v.iter().map(|n| n + 1).collect()@E
}

pub fn nested() -> u8 {@G(8)
    let outer = || {
        let inner = || 1u8;
        inner() + 1
    };
    @R(8)outer()@E
}@U
