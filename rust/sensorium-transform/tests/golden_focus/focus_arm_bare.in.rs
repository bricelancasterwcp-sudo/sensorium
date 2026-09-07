//! Amendment A1: an arm whose body is a bare EXPRESSION is spliced as
//! `{ <arm-entry probe> <expr> }`, so the entry LINE has somewhere to stand and
//! the arm still evaluates to exactly what it did. The exit wrap goes around the
//! whole `match`, so the two never share a byte.

pub fn pick(o: Option<i32>) -> i32 {
    match o {
        Some(n) => n * 2,
        None => 0,
    }
}
