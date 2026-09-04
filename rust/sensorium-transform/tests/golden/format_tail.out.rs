//! A macro call that is not one of the diverging four is an ordinary expression
//! and is wrapped -- including the brace-delimited statement-macro spelling.

macro_rules! pick {
    ($e:expr) => {
        $e
    };
}

pub fn formatted(n: u8) -> String {@G(7)
    @R(7)format!("n = {n}")@E
}

pub fn vector() -> Vec<u8> {@G(8)
    @R(8)vec![1, 2, 3]@E
}

pub fn brace_macro_tail() -> u8 {@G(9)
    @R(9)pick! { 4 }@E
}@U
