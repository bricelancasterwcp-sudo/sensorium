//! A brace-delimited MACRO in tail position. `syn` reads `pick! { 1 }` as a
//! `Stmt::Macro` whose `semi_token` is `None`, and `lines.rs`'s
//! `statement_end` gives that shape the byte after its closing brace without
//! asking whether it is the block's tail -- so a LINE probe is minted after a
//! macro that IS the function's return value.
//!
//! MEASURED: the tail gets BOTH treatments -- the RETURN wrap closes around
//! `pick! { 1 }` and the LINE probe is then spliced after the closing paren,
//! giving `..., pick! { 1 })::sensorium_rt::line(..)`, which rustc rejects with
//! `expected one of `.`, `;`, `?`, `}`, or an operator, found `::``. It is a
//! PARSE error, so the whole unit falls back to the real tree loudly
//! (`fallback::announce`) rather than losing a row quietly.
//!
//! The shape is `quote!`/`html!`-shaped tails, which is what proc-macro and
//! markup crates are made of. `rust/HONESTY-BLIND-SPOTS.md` item 3 states it;
//! this file is what measures it.

macro_rules! pick {
    ($n:expr) => {
        $n
    };
}

pub fn wrapped() -> i32 {
    pick! { 1 }
}
