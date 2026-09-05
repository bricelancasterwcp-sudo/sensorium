//! The fourth side of the line `err_stored`, `logged_arm` and
//! `err_rendered_into_value` draw: an `Err(e) =>` arm that hands a SHARED
//! BORROW of the error to a helper and keeps what the helper built.
//!
//! `logged_arm` borrows the error to print it and drops it -- a swallow.
//! `err_rendered_into_value` renders it with `format!` and returns the
//! rendering. Here the arm does the same thing one function call out:
//! `describe(&e)` takes only a borrow, so the arm still owns the error, but
//! the `(code, body)` it returns is a rendering of the failure and that pair
//! is the value `respond` hands to every caller. Before the 2026-09-05
//! borrow repair the escape test exempted `&e` wherever it appeared and this
//! arm read HANDLED -- a SWALLOWED verdict on a failure the caller received
//! as a 503. On the bloomery clone the shape is `api_v1.rs:396` and `:515`.
//!
//! Seeded bug: the reply says `503 store unavailable: cannot open store.db`
//! and nothing on the terminal says which call produced it; the failure DID
//! reach the caller, inside the reply, which is exactly why the tool must
//! read this arm as ambiguous and not as a swallow.

#[derive(Debug)]
struct Unavailable(String);

#[derive(Debug)]
struct Reply {
    code: u16,
    body: String,
}

/// The store is missing, so this always fails.
fn open(path: &str) -> Result<u32, Unavailable> {
    Err(Unavailable(path.to_owned()))
}

/// Maps a borrowed error to a status and a body: the helper `map_error` on
/// the clone. Its PRODUCT is what leaves the arm.
fn describe(e: &Unavailable) -> (u16, String) {
    (503, format!("store unavailable: cannot open {}", e.0))
}

/// The arm under test: `&e` is a borrow, and the pair the call returns is
/// the reply every caller gets.
fn respond(path: &str) -> Reply {
    match open(path) {
        Ok(n) => Reply { code: 200, body: format!("rows: {n}") },
        Err(e) => {
            let (code, body) = describe(&e);
            Reply { code, body }
        }
    }
}

fn main() {
    let reply = respond("store.db");
    println!("{} {}", reply.code, reply.body);
}
