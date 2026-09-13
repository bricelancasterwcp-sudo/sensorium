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

pub fn plain(v: &[i32]) -> usize {
    let mut acc = v.len();
    {
        acc += 1;
    }
    acc
}

pub fn tailing(v: &[i32]) -> usize {
    match v.first() {
        Some(n) => *n as usize,
        None => 0,
    }
}
