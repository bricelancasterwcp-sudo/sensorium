//! `return <e>` at closure depth 0, wherever the block nesting puts it.

pub fn in_if(c: bool) -> u8 {
    if c {
        return 1;
    }
    2
}

pub fn in_match(c: u8) -> u8 {
    match c {
        0 => return 10,
        _ => {}
    }
    20
}

pub fn in_loop(v: &[u8]) -> u8 {
    for b in v {
        if *b > 0 {
            return *b;
        }
    }
    0
}

pub fn in_nested_block() -> u8 {
    {
        let n = 1;
        if n == 1 {
            return n;
        }
    }
    0
}
