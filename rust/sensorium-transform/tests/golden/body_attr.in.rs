pub fn with_inner_stmt_attr() {
    #[allow(unused_mut)]
    let mut x = 1;
    let _ = x;
}

pub fn with_doc_on_first_item() {
    /// A documented nested item.
    struct Nested;
    let _ = Nested;
}
