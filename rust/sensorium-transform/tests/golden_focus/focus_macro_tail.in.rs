//! A brace-delimited MACRO in TAIL position -- `fn f() -> i32 { m! { 1 } }`,
//! the shape of every `quote!`- or `html!`-terminated function, and so of
//! proc-macro and markup crates. `syn` reads that tail as a `Stmt::Macro`
//! whose `semi_token` is `None`, which is a different node from the
//! `Stmt::Expr(_, None)` every other tail is -- and a tail is not a statement
//! whichever node spells it (design §3.3, `sensorium-transform` 0.4.1).
//!
//! Four functions, because the guard has four distinguishable effects.
//! `wrapped` and `spoken` are the two halves of the shape it repairs, and they
//! failed differently: in the VALUE fn the exits walk had already claimed the
//! same tail as its operand, so the LINE landed after the RETURN wrap's closing
//! paren and rustc rejected the file -- `found `::``, a PARSE error, so the
//! whole unit fell back and said so. In the UNIT fn there is no wrap to collide
//! with, so the extra LINE compiled and quietly recorded a completed statement
//! for what is the function's value. The first was loud, the second was not.
//!
//! `declared` is the NEGATIVE case, and it is what says the guard is narrow: a
//! brace macro that is NOT a tail keeps its probe, spliced after the closing
//! brace exactly as before, carrying no deltas because a macro's expansion is
//! not inspected. Without this function, widening the arm to `None` for every
//! brace macro would leave the suite green.
//!
//! `looped` is a brace-macro tail of a NESTED block -- a loop body's, which no
//! exits walk claims, because only a FN body's tail is an operand. It takes no
//! probe either, and for the plainer of the guard's two reasons: a tail is not
//! a statement. That is the same answer `Stmt::Expr(_, None)` already gives a
//! nested block's tail, so the guard makes the two node kinds agree rather than
//! inventing a rule for one of them.

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

macro_rules! decl {
    ($n:ident) => {
        let $n = 1;
    };
}

pub fn wrapped() -> i32 {
    pick! { 1 }
}

pub fn spoken(a: i32) {
    shout! { a }
}

pub fn declared() -> i32 {
    decl! { a }
    a + 1
}

pub fn looped() {
    for x in 0..2 {
        shout! { x }
    }
}
