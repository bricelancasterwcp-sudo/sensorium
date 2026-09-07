//! The straight-line case: three statements, each writing exactly one
//! binding, and a tail expression that is not a statement.
//!
//! What it pins is the shape of a focused frame at its simplest -- a
//! parameters LINE with empty deltas (design amendment A2: a function with
//! no parameters still mints the row that says it was entered), then one
//! LINE per completed statement (design §3.1), and no LINE for the tail
//! `s`, whose value is the RETURN's. Four rows, and a `watch` that settles
//! `b == 2` at the statement that wrote `b` rather than at the function.

fn fill() -> String {
    let a = 1;
    let b = a + 1;
    let s = format!("{b}");
    s
}

fn main() {
    println!("filled: {}", fill());
}
