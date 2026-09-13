//! An `else if` chain, and ruling P13 (2026-09-12, which withdrew P7's earlier
//! clause). An `else if` is the outer `if`'s `else_branch` EXPRESSION, not a
//! statement standing in a block, so it never gets a completion row of its
//! own -- and the outer `if` statement's row is therefore the ONLY row that
//! can say the chain's names ended.
//!
//! So the rule walks the chain: every link's condition bindings and every
//! link's direct `let`s, plus the final `else` block's, in source order and
//! each once. Under the withdrawn reading the row said `p` alone and `q`, `r`
//! and `s` were bound by rows that nothing ever balanced.

pub fn chained(c: bool, o: Option<i32>) -> i32 {
    let mut acc = 0;
    if c {
        let p = 1;
        acc += p;
    } else if let Some(q) = o {
        let r = q;
        acc += r;
    } else {
        let s = 0;
        acc += s;
    }
    acc
}
