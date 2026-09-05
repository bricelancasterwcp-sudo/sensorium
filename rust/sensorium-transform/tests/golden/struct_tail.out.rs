//! A struct literal is an expression, and it is still one as a call argument.
@W
pub struct Counter {
    pub n: u32,
}

impl Counter {
    pub fn new() -> Self {@G(7)
        @R(7)Self { n: 0 }@E
    }
}

impl Default for Counter {
    fn default() -> Counter {@G(8)
        @R(8)Counter { n: 9 }@E
    }
}@U
