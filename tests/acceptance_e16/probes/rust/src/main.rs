//! E16 part B's Rust probe -- not a seeded bug and not a corpus case: the
//! four places §1's amendment counts, and nothing else.
//!
//! `handle` is the focused function (`cargo sensorium --focus handle run`).
//! `token` fires rule v1's NAME rule and is taken by the recorder before
//! the spool is written; `copy` and `headers` fire no name at all, so the
//! only thing that can reach them is the CONTENT rule the converter runs --
//! which is why the token is minted as `sk-e16-` plus 33 characters, inside
//! the `sk-` pattern. `main` prints the LENGTH, never the value.

#[derive(Debug)]
struct Headers {
    authorization: String,
}

fn secret() -> String {
    std::env::var("SENSORIUM_E16_TOKEN").unwrap_or_default()
}

fn handle(token: String) -> usize {
    let copy = token.clone();
    let headers = Headers {
        authorization: copy,
    };
    headers.authorization.len()
}

fn main() {
    println!("{}", handle(secret()));
}
