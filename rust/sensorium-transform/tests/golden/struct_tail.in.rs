//! A struct literal is an expression, and it is still one as a call argument.

pub struct Counter {
    pub n: u32,
}

impl Counter {
    pub fn new() -> Self {
        Self { n: 0 }
    }
}

impl Default for Counter {
    fn default() -> Counter {
        Counter { n: 9 }
    }
}
