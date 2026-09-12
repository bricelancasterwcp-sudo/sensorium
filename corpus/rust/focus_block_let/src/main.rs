//! A focused function whose blocks BIND and then unbind: a plain block that
//! shadows an outer `let`, an `if let`, a `for` pattern, and a `match` arm
//! with a guard and a body `let`. Each statement's completion row is where
//! the recorder says the names it introduced went out of scope -- the row
//! Rust did not write before this slice (design §5.1), which left `x` alive
//! in the fold at every later site and let `watch` answer about a dead name.
//!
//! The shadow is the costly half and is pinned on purpose (design §5.5, R4):
//! the block pops `x`, so after it `x` is reported NOT IN SCOPE even though
//! Rust's outer `x` is alive and the tail adds it. Absence, never a stale
//! value.

fn shape(v: &[i32]) -> i32 {
    let x = 1;
    let mut acc = 0;
    {
        let x = 2;
        acc += x;
    }
    if let Some(first) = v.first() {
        acc += first;
    }
    for item in v {
        acc += item;
    }
    match v.len() {
        n if n > 1 => {
            let big = n as i32;
            acc += big;
        }
        _ => {}
    }
    acc + x
}

fn main() {
    println!("{}", shape(&[3, 4]));
}
