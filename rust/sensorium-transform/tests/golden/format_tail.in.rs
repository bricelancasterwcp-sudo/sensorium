//! A macro call that is not one of the diverging four is an ordinary expression
//! and is wrapped -- including the brace-delimited statement-macro spelling.

macro_rules! pick {
    ($e:expr) => {
        $e
    };
}

pub fn formatted(n: u8) -> String {
    format!("n = {n}")
}

pub fn vector() -> Vec<u8> {
    vec![1, 2, 3]
}

pub fn brace_macro_tail() -> u8 {
    pick! { 4 }
}
