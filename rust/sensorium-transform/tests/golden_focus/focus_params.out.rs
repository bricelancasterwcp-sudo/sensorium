//! Parameters (design §3.2's parameters row, amendments A2 and A6): a receiver
//! is spelled `self`, a destructured pattern contributes every name it binds,
//! and a function with NO parameters still mints its LINE with an empty list.
//! `self.n += ..` is a place write and writes no delta.
@W
pub struct Counter {
    n: i32,
}

impl Counter {
    pub fn bump(&mut self, (lo, hi): (i32, i32)) -> i32 {@G(7)@N(8,self,lo,hi)
        self.n += lo + hi;@N(9)
        @R(7)self.n@E
    }

    pub fn zero() -> i32 {@G(10)@N(11)
        @R(10)0@E
    }
}@U
