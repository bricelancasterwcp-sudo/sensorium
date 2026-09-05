//! A closure with no `?` is left exactly as it was: no frame, no guard, no
//! site. This is the fence for design R5's "closures without `?` stay
//! unframed" -- framing one would cost a CALL/RETURN pair per call for
//! nothing at all.

pub fn mapped(v: &[u8]) -> Vec<u8> {
    v.iter().map(|n| n + 1).collect()
}

pub fn nested() -> u8 {
    let outer = || {
        let inner = || 1u8;
        inner() + 1
    };
    outer()
}
