//! THROWAWAY SPIKE CODE. Being inert: no file, no directory, no allocation.

mod common;

use std::process::Command;

use common::TempDir;

/// `SENSORIUM_TIER=off` writes no file, even with a spool directory named --
/// and none anywhere else either.
#[test]
fn tier_off_writes_no_file() {
    let dir = TempDir::reserved();
    let (sandbox, run) = common::run_sandboxed("main-only", &[], Some(dir.path()), Some("off"));
    assert!(
        !dir.exists(),
        "SENSORIUM_TIER=off must not even create the spool directory {}",
        dir.path().display()
    );
    sandbox.assert_untouched("SENSORIUM_TIER=off");
    assert!(
        run.stderr.is_empty(),
        "an off run says nothing on stderr: {}",
        run.stderr
    );
}

/// An unset `SENSORIUM_SPOOL` writes no file and creates no directory --
/// including no default one of the runtime's own choosing.
#[test]
fn an_unset_spool_variable_creates_nothing() {
    let dir = TempDir::reserved();
    let (sandbox, run) = common::run_sandboxed("main-only", &[], None, None);
    assert!(
        !dir.exists(),
        "nothing may be created when SENSORIUM_SPOOL is unset"
    );
    sandbox.assert_untouched("unset SENSORIUM_SPOOL");
    assert!(run.stderr.is_empty(), "stderr: {}", run.stderr);
}

/// An empty `SENSORIUM_SPOOL` is treated as unset -- not as the working
/// directory, which is where an empty path would otherwise resolve.
#[test]
fn an_empty_spool_variable_is_inert() {
    let (sandbox, run) = common::run_sandboxed(
        "main-only",
        &[],
        Some(std::path::Path::new("")),
        None,
    );
    sandbox.assert_untouched("empty SENSORIUM_SPOOL");
    assert!(run.stderr.is_empty(), "stderr: {}", run.stderr);
}

/// `SENSORIUM_TIER=call` records, and an absent `SENSORIUM_TIER` means `call`:
/// the two runs are indistinguishable in what they write. This is the control
/// that stops the two tests above from passing for the wrong reason.
#[test]
fn tier_call_and_an_absent_tier_both_record() {
    for tier in [None, Some("call"), Some("")] {
        let dir = TempDir::reserved();
        common::run("main-only", &[], Some(dir.path()), tier);
        assert!(
            dir.exists(),
            "tier {tier:?} must record, but no spool directory was created"
        );
        assert_eq!(
            dir.spool(1).records.len(),
            3,
            "tier {tier:?} must record CALL, RETURN, THREAD_END"
        );
    }
}

/// An unrecognised tier records nothing and says why, exactly once.
#[test]
fn an_unknown_tier_is_refused_with_one_line() {
    let dir = TempDir::reserved();
    let run = common::run("two-threads", &[], Some(dir.path()), Some("full"));
    assert!(
        !dir.exists(),
        "an unknown tier must not record: {}",
        dir.path().display()
    );
    let lines: Vec<&str> = run.stderr.lines().filter(|l| !l.is_empty()).collect();
    assert_eq!(
        lines.len(),
        1,
        "exactly one stderr line, got {lines:?}"
    );
    assert!(
        lines[0].contains("SENSORIUM_TIER") && lines[0].contains("full"),
        "the line must name the variable and the value: {}",
        lines[0]
    );
}

/// The inert `enter` path allocates nothing. Measured by a counting global
/// allocator in a subject process, not asserted by inspection.
#[test]
fn the_inert_enter_path_allocates_nothing() {
    let out = Command::new(env!("CARGO_BIN_EXE_alloc_probe"))
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .output()
        .expect("running alloc_probe");
    let stdout = String::from_utf8_lossy(&out.stdout).trim().to_owned();
    assert!(
        out.status.success(),
        "alloc_probe failed: {:?} {}",
        out.status,
        String::from_utf8_lossy(&out.stderr)
    );
    assert_eq!(
        stdout, "0",
        "1000 inert enter/drop pairs allocated {stdout} times; the inert path must \
         allocate nothing beyond the guard value itself"
    );
}
