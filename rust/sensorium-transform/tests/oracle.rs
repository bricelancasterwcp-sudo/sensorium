//! The oracle: every golden's OUTPUT is handed to the real rustc.
//!
//! A golden pair proves the splicer put the bytes where the test said. It does
//! not prove the result is legal Rust, that it borrows, or that it is warning
//! free -- and "no new diagnostics" is a promise `rust/HONESTY.md` §9 makes.
//! This test is what falsifies it: each `.out.rs` is compiled with
//! `-D warnings` against a runtime rlib THIS TEST builds from
//! `../sensorium-rt/src/lib.rs`, and both the exit status and an EMPTY stderr
//! are required. A warning is a failure here, because under a workspace's own
//! `#![deny(warnings)]` a warning is a build error and the whole unit falls
//! back.
//!
//! Two of the goldens are compiled as BINARIES and run, transformed and
//! untransformed, with their stdout compared:
//!
//! * `run_drop_order` -- a `Drop`-logging local held across a wrapped tail and
//!   a wrapped `return`, so "temporary lifetimes and drop order unchanged at
//!   every wrapped site" is measured rather than argued.
//! * `run_mutex_guard` -- a `MutexGuard` held across a wrapped tail, read by a
//!   `try_lock` from another thread before and after, so the lock's hold time
//!   is measured too.
//!
//! Nothing is written outside `$CARGO_TARGET_DIR` (or the system temp directory
//! when that is unset). No path is hard-coded.

mod common;

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::OnceLock;
use std::time::{Duration, Instant};

use common::{expand, read, CASES, RUN_CASES};

/// A probe that has not finished in this long is hung, not slow. Killed by pid
/// and reaped, so a failing run never leaves a process behind.
const RUN_TIMEOUT: Duration = Duration::from_secs(60);

/// One output subtree per test, so parallel tests never share a path.
const TAG_COMPILE: &str = "compile";
const TAG_PLAIN: &str = "plain";
const TAG_RUN: &str = "run";

fn out_root() -> &'static Path {
    static ROOT: OnceLock<PathBuf> = OnceLock::new();
    ROOT.get_or_init(|| {
        let base = match std::env::var_os("CARGO_TARGET_DIR") {
            Some(d) if !d.is_empty() => PathBuf::from(d),
            _ => std::env::temp_dir(),
        };
        let dir = base.join("sensorium-transform-oracle");
        std::fs::create_dir_all(&dir).expect("creating the oracle's output directory");
        dir
    })
    .as_path()
}

/// The runtime rlib, built once per test binary with the bare `rustc` line the
/// driver uses (plan decision D1). If this ever needs a `-L dependency` the
/// runtime has grown a dependency it is not allowed to have.
fn runtime_rlib() -> &'static Path {
    static RLIB: OnceLock<PathBuf> = OnceLock::new();
    RLIB.get_or_init(|| {
        let src = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../sensorium-rt/src/lib.rs");
        let rlib = out_root().join("libsensorium_rt.rlib");
        let out = Command::new("rustc")
            .args([
                "--crate-type",
                "rlib",
                "--edition",
                "2021",
                "-C",
                "opt-level=3",
                "--crate-name",
                "sensorium_rt",
            ])
            .arg(&src)
            .arg("-o")
            .arg(&rlib)
            .output()
            .expect("running rustc for the runtime");
        assert!(
            out.status.success(),
            "building the runtime rlib failed:\n{}",
            String::from_utf8_lossy(&out.stderr)
        );
        rlib
    })
    .as_path()
}

/// Write one golden's transformed output where rustc can read it.
///
/// `tag` is the calling test's name. Tests run in parallel, and two of them
/// compile the same goldens: without a tag they would race on one output path
/// and one would read a half-written file or link a half-written object.
fn write_transformed(tag: &str, case: &str) -> PathBuf {
    let dir = out_root().join(tag);
    std::fs::create_dir_all(&dir).expect("creating a per-test output directory");
    let path = dir.join(format!("{case}.out.rs"));
    std::fs::write(&path, expand(&read(case, "out"))).expect("writing the transformed golden");
    path
}

struct Compiled {
    status: i32,
    stderr: String,
    artifact: PathBuf,
}

fn compile(tag: &str, case: &str, source: &Path, crate_type: &str, link_runtime: bool) -> Compiled {
    let dir = out_root().join(tag).join(format!("{case}-{crate_type}"));
    std::fs::create_dir_all(&dir).expect("creating a per-case output directory");
    let mut cmd = Command::new("rustc");
    cmd.args([
        "--edition",
        "2021",
        "-D",
        "warnings",
        "--crate-type",
        crate_type,
    ])
    .arg("--crate-name")
    .arg(format!("g_{case}"))
    .arg(source)
    .arg("--out-dir")
    .arg(&dir);
    if link_runtime {
        let mut extern_arg = std::ffi::OsString::from("sensorium_rt=");
        extern_arg.push(runtime_rlib());
        cmd.arg("--extern").arg(extern_arg);
    }
    let out = cmd.output().expect("running rustc");
    Compiled {
        status: out.status.code().unwrap_or(-1),
        stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
        artifact: dir.join(format!("g_{case}")),
    }
}

/// Run a built probe, killing it by pid if it hangs rather than hanging the
/// suite. Returns `(stdout, stderr)`.
fn run_probe(bin: &Path) -> (String, String) {
    let mut child = Command::new(bin)
        // The recorder must be inert: this measures the SHAPE of the code, and
        // a spool would add writes the untransformed build cannot make.
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap_or_else(|e| panic!("spawning {}: {e}", bin.display()));
    let pid = child.id();
    let started = Instant::now();
    loop {
        match child.try_wait().expect("waiting on the probe") {
            Some(_) => break,
            None if started.elapsed() > RUN_TIMEOUT => {
                child.kill().expect("killing a hung probe");
                child.wait().expect("reaping a hung probe");
                panic!(
                    "{} did not finish in {RUN_TIMEOUT:?} (pid {pid} killed and reaped)",
                    bin.display()
                );
            }
            None => std::thread::yield_now(),
        }
    }
    let out = child.wait_with_output().expect("collecting probe output");
    assert!(
        out.status.success(),
        "{} exited {:?}",
        bin.display(),
        out.status.code()
    );
    (
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

#[test]
fn every_golden_output_compiles_with_zero_diagnostics() {
    let mut failures = Vec::new();
    for case in CASES {
        let crate_type = if RUN_CASES.contains(case) {
            "bin"
        } else {
            "lib"
        };
        let source = write_transformed(TAG_COMPILE, case);
        let c = compile(TAG_COMPILE, case, &source, crate_type, true);
        println!(
            "{case:<24} {crate_type:<3} exit {:<3} stderr {} bytes",
            c.status,
            c.stderr.len()
        );
        if c.status != 0 || !c.stderr.is_empty() {
            failures.push(format!("--- {case} (exit {}) ---\n{}", c.status, c.stderr));
        }
    }
    assert!(
        failures.is_empty(),
        "rustc reported {} diagnostic(s) on transformed output:\n{}",
        failures.len(),
        failures.join("\n")
    );
}

#[test]
fn the_untransformed_goldens_are_warning_free_to_begin_with() {
    // Without this the oracle proves nothing: a golden INPUT that already warns
    // would make "no NEW diagnostics" unmeasurable.
    let mut failures = Vec::new();
    for case in CASES {
        let crate_type = if RUN_CASES.contains(case) {
            "bin"
        } else {
            "lib"
        };
        let source = common::golden_path(case, "in");
        let c = compile(TAG_PLAIN, &format!("{case}_in"), &source, crate_type, false);
        if c.status != 0 || !c.stderr.is_empty() {
            failures.push(format!("--- {case} (exit {}) ---\n{}", c.status, c.stderr));
        }
    }
    assert!(
        failures.is_empty(),
        "a golden INPUT is not warning free:\n{}",
        failures.join("\n")
    );
}

#[test]
fn the_run_probes_behave_identically_transformed_and_not() {
    for case in RUN_CASES {
        let transformed = write_transformed(TAG_RUN, case);
        let built = compile(TAG_RUN, case, &transformed, "bin", true);
        assert_eq!(
            (built.status, built.stderr.as_str()),
            (0, ""),
            "{case}: transformed probe did not compile cleanly"
        );
        let plain = compile(
            TAG_RUN,
            &format!("{case}_in"),
            &common::golden_path(case, "in"),
            "bin",
            false,
        );
        assert_eq!(
            (plain.status, plain.stderr.as_str()),
            (0, ""),
            "{case}: untransformed probe did not compile cleanly"
        );

        let (plain_out, plain_err) = run_probe(&plain.artifact);
        let (built_out, built_err) = run_probe(&built.artifact);
        println!("--- {case} (untransformed) ---\n{plain_out}");
        println!("--- {case} (transformed) ---\n{built_out}");
        assert_eq!(
            plain_out, built_out,
            "{case}: the transform changed what the program printed"
        );
        assert_eq!(plain_err, built_err, "{case}: stderr differs");
        assert!(
            !plain_out.is_empty(),
            "{case}: a probe that prints nothing compares nothing"
        );
    }
}
