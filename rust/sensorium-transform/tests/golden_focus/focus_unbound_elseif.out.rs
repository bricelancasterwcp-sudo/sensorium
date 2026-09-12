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
@W
pub fn chained(c: bool, o: Option<i32>) -> i32 {@G(7)@N(8,c,o)
    let mut acc = 0;@N(9,acc)
    if c {
        let p = 1;@N(10,p)
        acc += p;@N(11,acc)
    } else if let Some(q) = o {@N(12,q)
        let r = q;@N(13,r)
        acc += r;@N(14,acc)
    } else {
        let s = 0;@N(15,s)
        acc += s;@N(16,acc)
    }@B(17;p,q,r,s)
    @R(7)acc@E
}@U
