//! A brace-delimited MACRO in TAIL position -- `fn f() -> i32 { m! { 1 } }`,
//! the shape of every `quote!`- or `html!`-terminated function, and so of
//! proc-macro and markup crates. `syn` reads that tail as a `Stmt::Macro`
//! whose `semi_token` is `None`, which is a different node from the
//! `Stmt::Expr(_, None)` every other tail is -- and a tail is not a statement
//! whichever node spells it (design §3.3, `sensorium-transform` 0.4.1).
//!
//! Both shapes are here because they failed differently before the guard. In
//! the VALUE fn the exits walk had already claimed the same tail as its
//! operand, so the LINE landed after the RETURN wrap's closing paren and rustc
//! rejected the file -- `found `::``, a PARSE error, so the whole unit fell
//! back and said so. In the UNIT fn there is no wrap to collide with, so the
//! extra LINE compiled and quietly recorded a completed statement for what is
//! the function's value. The first was loud, the second was not; the guard is
//! the same one line for both.
@W
macro_rules! pick {
    ($n:expr) => {
        $n
    };
}

macro_rules! shout {
    ($n:ident) => {
        println!("{}", $n)
    };
}

pub fn wrapped() -> i32 {@G(7)@N(8)
    @R(7)pick! { 1 }@E
}

pub fn spoken(a: i32) {@G(9)@N(10,a)
    shout! { a }
}@U
