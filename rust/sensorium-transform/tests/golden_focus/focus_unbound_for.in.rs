//! A `for` pattern, the same rule read on a loop: `item` enters once per
//! iteration at the entry row, and the loop statement's own row pops it. The
//! body binds nothing, so the list is the head pattern's and no more.
//!
//! `focus_loop` is this shape's twin WITHOUT the unbind rule -- it predates
//! this slice; its plain LINE row became an unbinding one when this landed.

pub fn total(v: &[i32]) -> i32 {
    let mut acc = 0;
    for item in v {
        acc += item;
    }
    acc
}
