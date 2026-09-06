//! A `loop` a plain `break` leaves COMPLETES: the statement after it runs, and
//! so does the loop's own LINE. `exits::diverges` answers "has this loop a
//! VALUE to wrap", which is a different question (fix round 1, I1). A `loop`
//! nothing breaks out of really does diverge and takes no LINE, and neither
//! does the statement rustc would call unreachable after it.

pub fn wait_then(a: i32) -> i32 {
    let mut n = a;
    loop {
        if n > 0 {
            break;
        }
        n += 1;
    }
    let b = n + 1;
    b
}
