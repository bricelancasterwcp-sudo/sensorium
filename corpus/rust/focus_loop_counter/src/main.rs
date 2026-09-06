//! A loop, where the per-line record says something the return value alone
//! cannot: `total` is 0, then 1, then 3, and the value 3 is reached on the
//! THIRD iteration and nowhere else.
//!
//! The row shape is design §3.2's loop row: the `for` pattern's binding
//! enters the body once per iteration as a synthetic LINE at the loop's
//! line, the compound assignment writes the name on its left, and the `for`
//! is itself a statement of the body whose own LINE carries nothing.

fn sum() -> i32 {
    let mut total = 0;
    for i in 0..3 {
        total += i;
    }
    total
}

fn main() {
    println!("sum: {}", sum());
}
