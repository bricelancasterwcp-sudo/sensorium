//! Seeded bug: `survey` holds TWO different failures at once -- a probe that
//! could not reach its host, and a count that would not parse -- and folds
//! both into a plausible zero.
//!
//! It is also the shape this recorder must refuse to over-claim on. There is
//! no error identity on the wire: a chain is followed by its type and its
//! `Debug` text, so a frame's window holding two DIFFERENT errors cannot be
//! split into "this one was absorbed and that one was not". Both must read
//! ambiguous, and neither may be reported as a swallow.

fn probe(host: &str) -> Result<u32, String> {
    Err(format!("probe {host} unreachable"))
}

fn survey(host: &str, raw: &str) -> u32 {
    // The first error: ours, born in an instrumented frame.
    let probed = probe(host);
    // The second: a different one, entering the same window through an
    // `Err(..)` arm that builds a new error out of it.
    let counted = match raw.parse::<u32>() {
        Ok(v) => Ok(v),
        Err(e) => Err(format!("bad count {e}")),
    };
    // BUG: two distinct failures, one indistinguishable zero.
    match (probed, counted) {
        (Ok(a), Ok(b)) => a + b,
        _ => 0,
    }
}

fn main() {
    println!("survey: {}", survey("db-3", "many"));
}
