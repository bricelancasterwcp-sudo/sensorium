//! R4 and design §5.5, the costly half: a block that SHADOWS an outer name
//! pops that name. After this block the recording says `x` is NOT IN SCOPE,
//! even though Rust's outer `x` is alive and the tail reads it -- absence,
//! never a stale value, because a probe of the outer `x` at block exit would
//! read a name the statement did not write.
//!
//! The transform's whole part in that is this one row. What the fold does
//! with it is the converter's, and `corpus/rust/focus_block_let` measures
//! the pair end to end.

pub fn shadowed() -> i32 {
    let x = 1;
    {
        let x = 2;
        println!("{x}");
    }
    x
}
