//! `return <e>` at closure depth 0, wherever the block nesting puts it.

pub fn in_if(c: bool) -> u8 {@G(7)
    if c {
        return @R(7)1@E;
    }
    @R(7)2@E
}

pub fn in_match(c: u8) -> u8 {@G(8)
    match c {
        0 => return @R(8)10@E,
        _ => {}
    }
    @R(8)20@E
}

pub fn in_loop(v: &[u8]) -> u8 {@G(9)
    for b in v {
        if *b > 0 {
            return @R(9)*b@E;
        }
    }
    @R(9)0@E
}

pub fn in_nested_block() -> u8 {@G(10)
    {
        let n = 1;
        if n == 1 {
            return @R(10)n@E;
        }
    }
    @R(10)0@E
}@U
