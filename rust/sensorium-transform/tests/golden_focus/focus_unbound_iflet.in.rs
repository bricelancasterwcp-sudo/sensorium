//! `if let`: the head pattern's names are bound by the ENTRY row and popped
//! by the statement's own completion row. One name, two rows, and nothing in
//! the `then` block to add -- so this case says the head pattern ALONE
//! reaches the unbind list, which is the branch a mutant drops.

pub fn first_of(v: &[i32]) -> i32 {
    let mut acc = 0;
    if let Some(first) = v.first() {
        acc += first;
    }
    acc
}
