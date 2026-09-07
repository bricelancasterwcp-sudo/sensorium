//! Pattern bindings: an `if let` whose binding enters its block, and a
//! `match` in the function's tail position whose arm binding does the same.
//!
//! Three rules meet here. An arm or `if let` that binds an identifier mints
//! an entry LINE at its own line (design §3.2); one that binds nothing --
//! `None` is a path pattern, not a binding -- mints none (amendment A3); and
//! a `match` in tail position is not a statement, so it takes no LINE of its
//! own while the `if let` in statement position does.

fn pick(o: Option<i32>) -> i32 {
    if let Some(k) = o {
        println!("saw {k}");
    }
    match o {
        Some(n) => {
            let d = n * 2;
            d
        }
        None => 0,
    }
}

fn main() {
    println!("picked: {}", pick(Some(21)));
}
