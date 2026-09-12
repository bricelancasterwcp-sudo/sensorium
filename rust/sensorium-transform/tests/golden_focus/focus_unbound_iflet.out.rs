//! `if let`: the head pattern's names are bound by the ENTRY row and popped
//! by the statement's own completion row. One name, two rows, and nothing in
//! the `then` block to add -- so this case says the head pattern ALONE
//! reaches the unbind list, which is the branch a mutant drops.
@W
pub fn first_of(v: &[i32]) -> i32 {@G(7)@N(8,v)
    let mut acc = 0;@N(9,acc)
    if let Some(first) = v.first() {@N(10,first)
        acc += first;@N(11,acc)
    }@B(12;first)
    @R(7)acc@E
}@U
