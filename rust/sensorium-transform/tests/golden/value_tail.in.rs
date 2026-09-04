//! Ordinary value tails. Each is wrapped exactly once, and the operand is a
//! call ARGUMENT, so every coercion a tail position performs still performs.

pub fn literal() -> u8 {
    7
}

pub fn call(a: u8) -> u8 {
    literal() + a
}

pub fn chain(v: &[u8]) -> usize {
    v.iter().filter(|b| **b > 0).count()
}

pub fn deref_coercion(s: &String) -> &str {
    s
}

pub fn boxed() -> Box<dyn std::fmt::Debug> {
    Box::new(1u8)
}

pub fn generic<T: Clone>(t: &T) -> T {
    t.clone()
}

pub fn optional() -> Option<u8> {
    Some(1)
}
