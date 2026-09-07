//! The bare-expression arm body: amendment A1's shape, and the row it does
//! NOT mint.
//!
//! `pick`'s taken arm has no block -- its body is the expression `n * 2`.
//! Amendment A1 wraps such a body `{ <arm-entry probe>; <expr> }`, so the
//! arm-entry LINE exists for it exactly as it does for a block arm, while
//! the expression becomes the wrapper's TAIL and takes no statement LINE of
//! its own. Two rows for the whole activation, derived before it was
//! recorded: the parameters LINE (A2) and the arm entry (A3, since `Some(n)`
//! binds). E9 measured this shape on a real workspace and settled it in
//! favour of that reading (record §5.1), then recorded that nothing pinned
//! it (§5.5 item 2). This is the pin.

fn pick(o: Option<i32>) -> i32 {
    match o {
        Some(n) => n * 2,
        None => 0,
    }
}

fn main() {
    println!("picked: {}", pick(Some(21)));
}
