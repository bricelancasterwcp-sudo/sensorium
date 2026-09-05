//! Closure frames are rung 3. A closure gets no guard, and a `return` inside one
//! leaves the CLOSURE, not this function, so it is never wrapped as an exit.
@W
pub fn with_closure(v: &[u8]) -> usize {@G(7)
    let pick = |b: &u8| -> bool {
        if *b == 0 {
            return false;
        }
        true
    };
    @R(7)v.iter().filter(|b| pick(b)).count()@E
}

pub fn with_async_block() -> u8 {@G(8)
    let _fut = async {
        if false {
            return 1u8;
        }
        2u8
    };
    @R(8)3@E
}@U
