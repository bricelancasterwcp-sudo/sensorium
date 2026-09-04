//! Operands the transformer leaves alone because they diverge. Wrapping one
//! makes the `ret` call itself unreachable, which rustc reports.

pub fn not_yet() -> u8 {@G(7)
    todo!()
}

pub fn never_here() -> u8 {@G(8)
    unreachable!("never")
}

pub fn no_impl() -> u8 {@G(9)
    unimplemented!()
}

pub fn boom() -> u8 {@G(10)
    panic!("boom")
}

pub fn leave(code: i32) -> u8 {@G(11)
    std::process::exit(code)
}

pub fn stop_now() -> u8 {@G(12)
    std::process::abort()
}

pub fn tail_return(c: bool) -> u8 {@G(13)
    if c {
        return @R(13)1@E;
    }
    return @R(13)2@E
}@U
