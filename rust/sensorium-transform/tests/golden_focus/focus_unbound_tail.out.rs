//! R5, both halves.
//!
//! `plain`'s block has no `let` and no head pattern, so its row is
//! `line(...)` byte for byte as it was before this slice: the fragment
//! changes only where there is something to name, and every golden without a
//! block is untouched because of it.
//!
//! `tailing`'s `match` is the function's TAIL and takes no completion row at
//! all, so its arm's `n` is never unbound. A tail is not a statement (design
//! §3.3), and there is no row for the rule to reach -- which is a gap stated
//! rather than a row invented: the frame's RETURN is what says the whole
//! scope ended.
@W
pub fn plain(v: &[i32]) -> usize {@G(7)@N(8,v)
    let mut acc = v.len();@N(9,acc)
    {
        acc += 1;@N(10,acc)
    }@N(11)
    @R(7)acc@E
}

pub fn tailing(v: &[i32]) -> usize {@G(12)@N(13,v)
    @R(12)match v.first() {
        Some(n) => { @N(14,n) *n as usize },
        None => 0,
    }@E
}@U
