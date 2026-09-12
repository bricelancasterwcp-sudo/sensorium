//! A `for` pattern, the same rule read on a loop: `item` enters once per
//! iteration at the entry row, and the loop statement's own row pops it. The
//! body binds nothing, so the list is the head pattern's and no more.
//!
//! `focus_loop` is this shape's twin WITHOUT the unbind rule -- it predates
//! this slice, and its `@N(12)` became a `@B(12;i)` the day the rule landed.
@W
pub fn total(v: &[i32]) -> i32 {@G(7)@N(8,v)
    let mut acc = 0;@N(9,acc)
    for item in v {@N(10,item)
        acc += item;@N(11,acc)
    }@B(12;item)
    @R(7)acc@E
}@U
