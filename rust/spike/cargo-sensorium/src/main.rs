//! `cargo-sensorium` -- THROWAWAY SPIKE CODE for the rung-1 Rust mechanics
//! spike (`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`).
//! Evidence, not product: never merged to main, never `cargo install`ed.
//!
//! One binary, two lives:
//!
//! * **Driver** -- `cargo sensorium test [args]`. Builds the runtime rlib,
//!   installs a content-hashed shim, mints an invocation id and a spool
//!   directory, and runs `cargo test` with the argv unchanged.
//! * **Wrapper** -- what cargo invokes per workspace unit via
//!   `RUSTC_WORKSPACE_WRAPPER`. Walks the unit's module tree, splices entry
//!   guards, materialises the workspace mirror, writes the manifest, and runs
//!   the real rustc from inside the mirror with two linkage flags appended.
//!
//! [`args::role`] decides which, from cargo's own contract.

mod args;
mod driver;
mod mirror;
mod modtree;
mod rt_build;
mod sha256;
mod wrapper;

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let code = match args::role(&argv) {
        args::Role::Wrapper => wrapper::run(&argv),
        args::Role::Driver(rest) => driver::run(&rest),
        args::Role::Help => {
            eprintln!("usage: cargo sensorium test [--tier off|call] [cargo test args]");
            eprintln!("(also runs as RUSTC_WORKSPACE_WRAPPER; cargo passes rustc as argv[1])");
            2
        }
    };
    std::process::exit(code);
}
