//! Ordinary value tails. Each is wrapped exactly once, and the operand is a
//! call ARGUMENT, so every coercion a tail position performs still performs.

pub fn literal() -> u8 {@G(7)
    @R(7)7@E
}

pub fn call(a: u8) -> u8 {@G(8)
    @R(8)literal() + a@E
}

pub fn chain(v: &[u8]) -> usize {@G(9)
    @R(9)v.iter().filter(|b| **b > 0).count()@E
}

pub fn deref_coercion(s: &String) -> &str {@G(10)
    @R(10)s@E
}

pub fn boxed() -> Box<dyn std::fmt::Debug> {@G(11)
    @R(11)Box::new(1u8)@E
}

pub fn generic<T: Clone>(t: &T) -> T {@G(12)
    @R(12)t.clone()@E
}

pub fn optional() -> Option<u8> {@G(13)
    @R(13)Some(1)@E
}@U
