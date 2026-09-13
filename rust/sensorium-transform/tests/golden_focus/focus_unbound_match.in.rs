//! A `match` in statement position, and the SOURCE ORDER rule: the arm
//! pattern's `n` comes before the arm body's `let big`, because that is the
//! order the two are written in. Design §5.2's bullets list the inner `let`s
//! first; its lead clause says "in source order, each name once", and that is
//! what governs (ruling P7). `corpus/rust/focus_block_let` pins the same
//! pair, `unbound:n,big`, through the recorder.
//!
//! The second arm binds nothing and contributes nothing -- the same silence
//! amendment A3 gives it at entry.

pub fn sized(v: &[i32]) -> i32 {
    let mut acc = 0;
    match v.len() {
        n if n > 1 => {
            let big = n as i32;
            acc += big;
        }
        _ => {}
    }
    acc
}
