//! Parameters (design §3.2's parameters row, amendments A2 and A6): a receiver
//! is spelled `self`, a destructured pattern contributes every name it binds,
//! and a function with NO parameters still mints its LINE with an empty list.
//! `self.n += ..` is a place write and writes no delta.

pub struct Counter {
    n: i32,
}

impl Counter {
    pub fn bump(&mut self, (lo, hi): (i32, i32)) -> i32 {
        self.n += lo + hi;
        self.n
    }

    pub fn zero() -> i32 {
        0
    }
}
