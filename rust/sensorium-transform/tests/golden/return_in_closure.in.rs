//! Closure frames are rung 3. A closure gets no guard, and a `return` inside one
//! leaves the CLOSURE, not this function, so it is never wrapped as an exit.

pub fn with_closure(v: &[u8]) -> usize {
    let pick = |b: &u8| -> bool {
        if *b == 0 {
            return false;
        }
        true
    };
    v.iter().filter(|b| pick(b)).count()
}

pub fn with_async_block() -> u8 {
    let _fut = async {
        if false {
            return 1u8;
        }
        2u8
    };
    3
}
