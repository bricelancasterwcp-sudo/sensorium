//! The `--refocus-of` gate, through the REAL binary: the two refusals design
//! 2026-09-07 §2.1 (amendment B2) fixes, and the promise each one ends with.
//!
//! `refocus_of.rs` has unit tests for `check`, but the crate has no library
//! target, so the only way to reach the gate from outside `src/` is the
//! binary — which is also the honest subject: what these tests pin is the
//! exit code and the sentence a person meets, and that nothing was built to
//! produce either. The gate is the FIRST statement of the driver's `go()`,
//! before the workspace is even located, so a scratch crate that could have
//! been built is what makes "nothing was built." a measurable claim rather
//! than a restatement of the code.
//!
//! Two shapes are pinned here and nowhere else in this suite:
//!   * `.` — the one member of the shape list (`is_run_id`'s `value != "."`)
//!     that is neither empty, nor a `..`, nor a separator. Without it the
//!     clause could be deleted and every other test would still pass.
//!   * the store-miss sentence names the store ROOT, never its `traces`
//!     subdirectory: the root is what a person set in `SENSORIUM_DIR` and
//!     therefore what the refusal has to name back to them.

mod common;

use std::process::Command;

use common::Scratch;

const RUN: &str = "20260101-000000-abcdef";

/// A scratch crate, a scratch store, and the driver run against them.
/// Returns (exit code, stderr, whether a target directory was created).
fn refuse(name: &str, refocus_of: &str) -> (Option<i32>, String, bool) {
    let s = Scratch::in_build_dir(name);
    // `[workspace]` so the scratch crate is its own root wherever it lands,
    // exactly as `driver_smoke.rs` does it.
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"gated\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", "pub fn value() -> u8 {\n    5\n}\n");
    let target = s.p("target");
    let store = s.p("sensorium-dir");

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["sensorium", "test", "--refocus-of", refocus_of])
        .current_dir(s.p("ws"))
        .env("CARGO_TARGET_DIR", &target)
        .env("SENSORIUM_DIR", &store)
        // Whatever ran THIS test must not leak into the run under test.
        .env_remove("RUSTC_WORKSPACE_WRAPPER")
        .env_remove("RUSTC_WRAPPER")
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .output()
        .expect("run the driver");

    let stderr = String::from_utf8_lossy(&out.stderr).into_owned();
    (out.status.code(), stderr, target.exists())
}

#[test]
fn a_dot_is_not_a_run_id_and_nothing_is_built() {
    let (code, stderr, built) = refuse("refocus-of-dot", ".");
    assert_eq!(
        stderr.trim_end(),
        "REFUSED: --refocus-of . is not a run id; nothing was built.",
        "stderr was: {stderr}"
    );
    assert_eq!(code, Some(2), "stderr was: {stderr}");
    // The other half of the sentence, checked rather than trusted: the gate
    // runs before the runtime, the shim, the spool and cargo, so not even a
    // target directory exists afterwards.
    assert!(!built, "a build directory was created by a refused call");
}

#[test]
fn the_store_miss_refusal_names_the_store_root_not_its_traces_directory() {
    let (code, stderr, built) = refuse("refocus-of-missing", RUN);
    let line = stderr.trim_end();
    assert!(
        line.starts_with(&format!("REFUSED: --refocus-of {RUN} names no trace in ")),
        "stderr was: {stderr}"
    );
    assert!(
        line.ends_with("; nothing was built."),
        "stderr was: {stderr}"
    );
    // The named path is the store ROOT: it ends in the directory
    // `SENSORIUM_DIR` was set to, and does not reach down into `traces`.
    assert!(
        line.contains("sensorium-dir;") && !line.contains("traces"),
        "stderr was: {stderr}"
    );
    assert_eq!(code, Some(2), "stderr was: {stderr}");
    assert!(!built, "a build directory was created by a refused call");
}
