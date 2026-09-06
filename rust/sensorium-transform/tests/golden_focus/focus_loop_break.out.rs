//! A `loop` a plain `break` leaves COMPLETES: the statement after it runs, and
//! so does the loop's own LINE. `exits::diverges` answers "has this loop a
//! VALUE to wrap", which is a different question (fix round 1, I1). A `loop`
//! nothing breaks out of really does diverge and takes no LINE, and neither
//! does the statement rustc would call unreachable after it.
@W
pub fn wait_then(a: i32) -> i32 {@G(7)@N(8,a)
    let mut n = a;@N(9,n)
    loop {
        if n > 0 {
            break;
        }@N(10)
        n += 1;@N(11,n)
    }@N(12)
    let b = n + 1;@N(13,b)
    @R(7)b@E
}@U
