//! Operands the transformer leaves alone because they diverge. Wrapping one
//! makes the `ret` call itself unreachable, which rustc reports.

pub fn not_yet() -> u8 {
    todo!()
}

pub fn never_here() -> u8 {
    unreachable!("never")
}

pub fn no_impl() -> u8 {
    unimplemented!()
}

pub fn boom() -> u8 {
    panic!("boom")
}

pub fn leave(code: i32) -> u8 {
    std::process::exit(code)
}

pub fn stop_now() -> u8 {
    std::process::abort()
}

pub fn tail_return(c: bool) -> u8 {
    if c {
        return 1;
    }
    return 2
}
