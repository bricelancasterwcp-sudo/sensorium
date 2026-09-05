//! The third side of the line `err_stored` and `logged_arm` draw: an
//! `Err(e) =>` arm that RENDERS the error into the value it returns.
//!
//! `logged_arm` borrows the error to print it and drops it -- the failure
//! reached stderr and nowhere else, which is a swallow. `err_stored` moves it
//! into a Vec. Here the arm does neither: `format!` hands it back a String,
//! and that String is the arm's own value, so a rendering of the failure
//! travels to every caller in the returned struct. Nothing was dropped, and
//! the tool must not say it was.
//!
//! This is the shape endpoint E6' STOPped on, reduced to one crate: on the
//! bloomery clone it is `build_memory` at `memory.rs:131`, whose arm returns
//! `MemoryContext { disabled_reason: Some(format!("...{e}")), store: None }`.
//!
//! Seeded bug: `settings` comes back with `retries: 0` -- the disabled
//! default -- and the reason why is sitting in `disabled_reason`, printed
//! only under a `--why` flag nobody passes. The failure DID reach the caller,
//! which is exactly why the tool must read this arm as ambiguous and not as a
//! swallow; whether anything ever acts on it is not on the wire.

use std::fmt;

#[derive(Debug)]
struct Unreadable(String);

impl fmt::Display for Unreadable {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "cannot read {}", self.0)
    }
}

#[derive(Debug)]
struct Settings {
    retries: u32,
    disabled_reason: Option<String>,
}

/// The store is missing, so this always fails.
fn load(path: &str) -> Result<Settings, Unreadable> {
    Err(Unreadable(path.to_owned()))
}

/// The arm under test: its value IS this function's value, and it carries a
/// rendering of the error out with it.
fn build(path: &str) -> Settings {
    match load(path) {
        Ok(s) => s,
        Err(e) => Settings {
            retries: 0,
            disabled_reason: Some(format!("settings unreadable: {e}")),
        },
    }
}

fn main() {
    let settings = build("settings.toml");
    println!("retries: {}", settings.retries);
    // BUG: the rendered failure travels back in the struct and the default
    // run never shows it. Nobody passes `--why`.
    if std::env::args().any(|a| a == "--why") {
        if let Some(reason) = &settings.disabled_reason {
            println!("reason: {reason}");
        }
    }
}
