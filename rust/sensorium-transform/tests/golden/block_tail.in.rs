//! A bare `{ e }` tail is descended INTO, not wrapped whole.
//!
//! `#![allow(unused_braces)]` is the SOURCE's own, not the transformer's excuse:
//! `fn f() -> u8 { { 1 } }` already warns "unnecessary braces around block
//! return value" untransformed, so this shape cannot occur in a warning-clean
//! workspace at all (measured on rustc 1.96, 2026-09-02). The allow is present
//! in both builds, so it silences nothing the transform contributes -- and
//! because it covers "around function argument" too, it is `tests/golden.rs`'s
//! byte-exact diff, not the oracle, that pins the wrap to the INSIDE of the
//! braces here.
#![allow(unused_braces)]

pub fn bare_block() -> u8 {
    { 1 }
}

pub fn nested_bare_blocks() -> u8 {
    {{ 2 }}
}

pub fn a_block_with_statements_is_wrapped_whole() -> u8 {
    {
        let n = 3;
        n
    }
}

pub fn a_labelled_block_is_wrapped_whole() -> u8 {
    'value: {
        if true {
            break 'value 4;
        }
        5
    }
}

pub fn a_labelled_bare_block_is_wrapped_whole(c: bool) -> u8 {
    'value: {
        if c { break 'value 6 } else { 7 }
    }
}
