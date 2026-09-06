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

/// An unlabelled `break` leaves the INNERMOST loop only, so the OUTER one here
/// never completes: no LINE for it, and nothing may follow it. A break walk that
/// ignored the nesting depth would put a probe after a statement of type `!`,
/// and `oracle.rs` fails that under `-D warnings` -- which is what makes this
/// case a compile proof and not an opinion (fix round 2, F1).
pub fn spins() {
    loop {
        loop {
            break;
        }
    };
}

/// A LABELLED `break` leaves the outer loop from inside the inner one, so the
/// outer loop DOES complete: it takes its LINE, and the statement after it runs.
pub fn labelled(mut n: i32) -> i32 {
    'o: loop {
        loop {
            n += 1;
            break 'o;
        }
    }
    let b = n;
    b
}
