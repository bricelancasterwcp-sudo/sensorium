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
}

/// An unlabelled `break` leaves the INNERMOST loop only, so the OUTER one here
/// never completes: no LINE for it, and nothing may follow it. A break walk that
/// ignored the nesting depth would put a probe after a statement of type `!`,
/// and `oracle.rs` fails that under `-D warnings` -- which is what makes this
/// case a compile proof and not an opinion (fix round 2, F1).
pub fn spins() {@G(14)@N(15)
    loop {
        loop {
            break;
        }
    };
}

/// A LABELLED `break` leaves the outer loop from inside the inner one, so the
/// outer loop DOES complete: it takes its LINE, and the statement after it runs.
pub fn labelled(mut n: i32) -> i32 {@G(16)@N(17,n)
    'o: loop {
        loop {
            n += 1;@N(18,n)
            break 'o;
        }
    }@N(19)
    let b = n;@N(20,b)
    @R(16)b@E
}@U
