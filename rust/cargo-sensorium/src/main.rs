//! `cargo-sensorium` — the sensorium Rust recorder's driver.
//!
//! One binary, three lives, decided by [`args::role`] from the contracts cargo
//! itself defines:
//!
//! * **Driver** — `cargo sensorium test|run [--tier off|call] [cargo args]`.
//!   Compiles the runtime, installs a content-hashed shim, mints an invocation
//!   id and a spool directory, and runs cargo with the argv unchanged.
//! * **Wrapper** — what cargo invokes per workspace unit through
//!   `RUSTC_WORKSPACE_WRAPPER`. Walks the unit's module tree, splices the
//!   guards, materialises the unit's mirror, writes the manifest, and runs the
//!   real rustc from inside the mirror.
//! * **Runner** — what cargo invokes for every test binary (and, on cargo 1.96,
//!   every doctest process) through `CARGO_TARGET_<HOST>_RUNNER`. Spawns,
//!   waits, and records the exit status nothing inside the process can see.
//!
//! What this recorder does not see, and how each limit declares itself, is
//! `rust/HONESTY.md`.

mod args;
mod driver;
mod fallback;
mod mirror;
mod modtree;
mod rt_build;
mod rt_src;
mod runner;
mod sha256;
mod wrapper;

fn main() {
    let argv: Vec<String> = std::env::args().collect();
    let code = match args::role(&argv) {
        args::Role::Wrapper { rustc, args } => wrapper::run(&rustc, &args),
        args::Role::Runner(args) => runner::run(&args),
        args::Role::Driver(rest) => driver::run(&rest),
        args::Role::Help => {
            eprintln!("{}", driver::USAGE);
            eprintln!(
                "(also runs as cargo's RUSTC_WORKSPACE_WRAPPER, which passes rustc as argv[1], \
                 and as its target runner behind --runner)"
            );
            2
        }
    };
    std::process::exit(code);
}
