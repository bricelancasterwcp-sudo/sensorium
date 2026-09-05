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
//! Two more things are measured here rather than argued, both rung 3's:
//!
//! * the crate-root `#![allow(clippy::match_single_binding)]` the transformer
//!   injects actually silences the lint every err wrap provokes -- run through
//!   the real `clippy-driver`, with the attribute REMOVED as the falsifier, and
//!   skipped by name when clippy is not installed;
//! * the E0507 the design gives as the reason not to wrap a place-expression
//!   sink receiver does NOT reproduce for the four written sinks, and does
//!   reproduce for the `&self` predicates design R2 already refuses.
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
const TAG_CLIPPY: &str = "clippy";
const TAG_BORROW: &str = "borrow";

/// The one lint every err wrap provokes, and the only one denied when clippy
/// runs here: this test is about the transformer's own attribute, not about
/// what clippy thinks of a golden's hand-written Rust.
const WRAP_LINT: &str = "clippy::match_single_binding";

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

/// Write an arbitrary source string where rustc (or clippy) can read it.
fn write_source(tag: &str, name: &str, text: &str) -> PathBuf {
    let dir = out_root().join(tag);
    std::fs::create_dir_all(&dir).expect("creating a per-test output directory");
    let path = dir.join(format!("{name}.rs"));
    std::fs::write(&path, text).expect("writing a probe source");
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

// ---------------------------------------------------------------------------
// The crate-root allow (rung 3)
// ---------------------------------------------------------------------------

/// Run `clippy-driver` over one source with EVERY lint allowed except the one
/// the wrap provokes. `None` when clippy is not installed.
fn clippy(tag: &str, name: &str, source: &Path) -> Option<Compiled> {
    let dir = out_root().join(tag).join(name);
    std::fs::create_dir_all(&dir).expect("creating a per-case output directory");
    let mut extern_arg = std::ffi::OsString::from("sensorium_rt=");
    extern_arg.push(runtime_rlib());
    let out = Command::new("clippy-driver")
        .args(["--edition", "2021", "--crate-type", "lib"])
        .arg("--crate-name")
        .arg(format!("c_{name}"))
        .arg(source)
        .arg("--out-dir")
        .arg(&dir)
        .arg("--extern")
        .arg(extern_arg)
        // Allow everything, then deny exactly one: a golden's own hand-written
        // Rust is not what this test is about.
        .args(["-A", "warnings", "-D", WRAP_LINT])
        .output()
        .ok()?;
    Some(Compiled {
        status: out.status.code().unwrap_or(-1),
        stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
        artifact: dir,
    })
}

#[test]
fn the_injected_allow_silences_the_lint_every_wrap_provokes() {
    let mut checked = 0usize;
    for case in CASES {
        if RUN_CASES.contains(case) {
            continue;
        }
        let transformed = expand(&read(case, "out"));
        if !transformed.contains("::sensorium_rt::err_site(") {
            continue;
        }
        let with = write_source(TAG_CLIPPY, case, &transformed);
        let Some(c) = clippy(TAG_CLIPPY, case, &with) else {
            eprintln!(
                "SKIP the_injected_allow_silences_the_lint_every_wrap_provokes: \
                 clippy-driver is not installed; nothing was measured"
            );
            return;
        };
        assert_eq!(
            (c.status, c.stderr.as_str()),
            (0, ""),
            "{case}: the injected allow did not silence {WRAP_LINT}"
        );

        // The falsifier: without the attribute the lint fires, so the check
        // above is measuring something.
        let without = transformed.replace("#![allow(clippy::match_single_binding)]", "");
        assert_ne!(without, transformed, "{case}: no allow to remove");
        let path = write_source(TAG_CLIPPY, &format!("{case}_noallow"), &without);
        let c =
            clippy(TAG_CLIPPY, &format!("{case}_noallow"), &path).expect("clippy ran a moment ago");
        assert!(
            c.stderr.contains("match_single_binding"),
            "{case}: with the allow removed the lint must fire, got:\n{}",
            c.stderr
        );
        checked += 1;
    }
    assert!(
        checked >= 6,
        "only {checked} goldens carry an err wrap: this test is checking nothing"
    );
}

// ---------------------------------------------------------------------------
// The E0507 the design names (rung 3), re-measured
// ---------------------------------------------------------------------------

/// Design R2 declines to wrap a sink whose receiver is a place expression, and
/// the brief gives E0507 as the reason. This is the re-measurement, and it says
/// two things:
///
/// * for the FOUR WRITTEN SINKS the asymmetry does not exist -- all four take
///   `self` by value, so a receiver the wrap cannot move is one the sink could
///   not move either, and every place receiver that compiles plain compiles
///   wrapped;
/// * for the `&self` PREDICATES it is real, which is exactly why design R2
///   refuses to probe `.is_err()`/`.is_ok()`.
///
/// The rule is kept as ruled (it is the conservative direction, and the
/// declined sites are declared), but the justification belongs to the
/// predicates, not to the sinks. Lifting it would raise sink coverage.
#[test]
fn a_place_receiver_is_the_conservative_choice_not_the_e0507_the_brief_names() {
    const PLAIN_SINKS: &str = "\
pub struct S { pub c: Result<u8, u8> }
pub fn field(s: &S) -> u8 { s.c.unwrap_or(0) }
pub fn index(v: &[Result<u8, u8>]) -> u8 { v[0].unwrap_or(0) }
pub fn deref(p: &Result<u8, u8>) -> u8 { (*p).unwrap_or(0) }
pub fn local(r: Result<String, String>) -> Option<String> { r.ok() }
";
    const WRAPPED_SINKS: &str = "\
#![allow(clippy::match_single_binding)]
pub struct S { pub c: Result<u8, u8> }
pub fn field(s: &S) -> u8 { match s.c { __t => { let _ = &__t; __t } }.unwrap_or(0) }
pub fn index(v: &[Result<u8, u8>]) -> u8 { match v[0] { __t => { let _ = &__t; __t } }.unwrap_or(0) }
pub fn deref(p: &Result<u8, u8>) -> u8 { match *p { __t => { let _ = &__t; __t } }.unwrap_or(0) }
pub fn local(r: Result<String, String>) -> Option<String> { match r { __t => { let _ = &__t; __t } }.ok() }
";
    const PLAIN_PREDICATE: &str = "\
pub struct T { pub last: Result<String, String> }
pub fn observed(t: &T) -> bool { t.last.is_err() }
";
    const WRAPPED_PREDICATE: &str = "\
#![allow(clippy::match_single_binding)]
pub struct T { pub last: Result<String, String> }
pub fn observed(t: &T) -> bool { match t.last { __t => { let _ = &__t; __t } }.is_err() }
";
    for (name, source) in [
        ("plain_sinks", PLAIN_SINKS),
        ("wrapped_sinks", WRAPPED_SINKS),
        ("plain_predicate", PLAIN_PREDICATE),
    ] {
        let path = write_source(TAG_BORROW, name, source);
        let c = compile(TAG_BORROW, name, &path, "lib", false);
        assert_eq!(
            (c.status, c.stderr.as_str()),
            (0, ""),
            "{name} must compile clean"
        );
    }
    let path = write_source(TAG_BORROW, "wrapped_predicate", WRAPPED_PREDICATE);
    let c = compile(TAG_BORROW, "wrapped_predicate", &path, "lib", false);
    assert!(
        c.stderr.contains("E0507"),
        "the predicates ARE the E0507 case -- design R2's reason for never \
         probing them -- got:\n{}",
        c.stderr
    );
}
