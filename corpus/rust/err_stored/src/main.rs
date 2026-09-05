//! The shape a swallow detector must NOT accuse: a retry loop whose
//! `Err(e) =>` arm binds the error and keeps it. Pushing `e` onto a list is
//! not dropping it -- the program is holding the failures for a report --
//! and this recording cannot tell a list that gets reported from one that
//! does not.
//!
//! Seeded bug: here the list really is never reported. The tool still must
//! not say so, because the two programs record identically and only one of
//! them is wrong.

#[derive(Debug)]
struct Refused(u32);

fn attempt(n: u32) -> Result<u32, Refused> {
    Err(Refused(n))
}

fn retry(times: u32) -> u32 {
    let mut errors: Vec<Refused> = Vec::new();
    let mut got = 0;
    for n in 1..=times {
        match attempt(n) {
            Ok(v) => {
                got = v;
                break;
            }
            Err(e) => errors.push(e),
        }
    }
    // BUG: `errors` goes out of scope here and nobody ever reads it.
    got
}

fn main() {
    println!("charged: {}", retry(2));
}
