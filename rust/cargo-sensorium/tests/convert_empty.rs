//! An invocation that recorded no process at all is not an error: `cargo
//! sensorium test --help`, a cargo failure before anything compiled, or a
//! `target/sensorium` wiped between builds while cargo stayed
//! fingerprint-fresh. `convert_dir` must return an empty [`Report`] rather
//! than demanding a manifests directory nothing ever had a reason to write.

mod common;

use std::process::{Command, Output};

use common::Scratch;

fn context(out: &Output) -> String {
    format!(
        "status: {:?}\n--- stdout ---\n{}\n--- stderr ---\n{}",
        out.status.code(),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

/// A spool directory with only `invocation.json` -- no `.proc.json`, no
/// `sensorium/manifests` directory at all -- the shape the driver leaves
/// behind for an invocation where cargo never invoked the wrapper or the
/// runner (`--help`, or a failure before any unit compiled).
#[test]
fn a_spool_dir_with_no_proc_headers_and_no_manifests_dir_converts_cleanly() {
    let s = Scratch::in_build_dir("convert-empty-fixture");
    let target = s.p("target");
    let spool_dir = target.join("sensorium/spool/20260903-000000-000000");
    std::fs::create_dir_all(&spool_dir).unwrap();
    // Deliberately no `sensorium/manifests` directory: nothing ever compiled,
    // so nothing ever wrote one.
    common::wire::write_invocation(
        &spool_dir,
        "20260903-000000-000000",
        "/w",
        &target.to_string_lossy(),
    );
    let sensorium_dir = s.p("sensorium-dir");

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["convert", &spool_dir.to_string_lossy()])
        .env("SENSORIUM_DIR", &sensorium_dir)
        .output()
        .expect("run cargo-sensorium convert");

    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    assert!(
        String::from_utf8_lossy(&out.stderr).is_empty(),
        "no error line for nothing to convert: {}",
        context(&out)
    );
    assert!(
        String::from_utf8_lossy(&out.stdout).is_empty(),
        "no `run:` line either -- nothing was converted: {}",
        context(&out)
    );
    // No traces directory needs to exist; if `runid::traces_dir` happened to
    // create an empty one that is fine, but nothing was written into it.
    let traces_dir = sensorium_dir.join("traces");
    if traces_dir.is_dir() {
        let entries: Vec<_> = std::fs::read_dir(&traces_dir).unwrap().collect();
        assert!(entries.is_empty(), "{entries:?}");
    }
}

/// The real repro: `cargo sensorium test --help` builds nothing and runs
/// nothing, through the actual driver, not a hand-built fixture.
#[test]
fn cargo_sensorium_test_help_does_not_turn_a_green_run_into_exit_2() {
    let s = Scratch::in_build_dir("convert-empty-e2e");
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"emptyrun\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", "pub fn one() -> u8 { 1 }\n");
    let target = s.p("target");
    let sensorium_dir = s.p("sensorium-dir");

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        // No `--` separator: this is cargo's OWN `--help`, so cargo prints its
        // usage and exits without ever invoking the wrapper or the runner --
        // the exact repro from the review (`cargo-sensorium sensorium test
        // --help` in a fresh target dir).
        .args(["sensorium", "test", "--help"])
        .current_dir(s.p("ws"))
        .env("CARGO_TARGET_DIR", &target)
        .env("SENSORIUM_DIR", &sensorium_dir)
        .env_remove("RUSTC_WORKSPACE_WRAPPER")
        .env_remove("RUSTC_WRAPPER")
        .env_remove("RUSTFLAGS")
        .env_remove("RUSTDOCFLAGS")
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .env_remove("SENSORIUM_INNER_RUNNER")
        .output()
        .expect("run the driver");

    let ctx = context(&out);
    assert_eq!(out.status.code(), Some(0), "{ctx}");
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        !stderr.contains("cargo-sensorium: "),
        "a conversion error leaked on a --help run: {ctx}"
    );
    assert!(stderr.contains("cargo exit: 0"), "{ctx}");
}
