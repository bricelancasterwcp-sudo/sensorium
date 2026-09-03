//! What the runtime does when it is not recording: nothing, anywhere.
//!
//! "Writes no file" is not falsifiable by watching one named directory -- a
//! recorder that fell back to a default path would leave that directory
//! untouched and still write a spool. Every arm here therefore runs the subject
//! in a sandbox whose cwd, `TMPDIR` and `HOME` are all a fresh empty tree, and
//! asserts that tree is still empty afterwards.

mod common;

use common::{Spec, TempDir, KIND_CALL};

#[test]
fn no_spool_variable_records_nothing_anywhere() {
    let sandbox = TempDir::created("inert-unset-sandbox");
    let run = Spec::new("main-only").sandbox(sandbox.path()).run();
    sandbox.assert_untouched("SENSORIUM_SPOOL unset");
    assert_eq!(run.stderr, "", "an unconfigured recorder says nothing");
}

#[test]
fn an_empty_spool_variable_records_nothing_anywhere() {
    let sandbox = TempDir::created("inert-empty-sandbox");
    let run = Spec::new("main-only")
        .sandbox(sandbox.path())
        .env("SENSORIUM_SPOOL", "")
        .run();
    sandbox.assert_untouched("SENSORIUM_SPOOL empty");
    assert_eq!(run.stderr, "");
}

#[test]
fn tier_off_creates_no_spool_directory() {
    let sandbox = TempDir::created("inert-off-sandbox");
    let dir = TempDir::reserved("inert-off");
    let run = Spec::new("main-only")
        .sandbox(sandbox.path())
        .spool(dir.path())
        .tier("off")
        .run();
    assert!(
        !dir.exists(),
        "tier off must not even create {}",
        dir.path().display()
    );
    sandbox.assert_untouched("SENSORIUM_TIER=off");
    assert_eq!(run.stderr, "", "tier off is a request, not an error");
}

#[test]
fn an_empty_tier_means_call() {
    let dir = TempDir::reserved("inert-empty-tier");
    Spec::new("main-only").spool(dir.path()).tier("").run();
    assert_eq!(
        dir.spools().len(),
        1,
        "an empty SENSORIUM_TIER is the default tier"
    );
}

#[test]
fn an_unknown_tier_prints_one_line_and_records_nothing() {
    let sandbox = TempDir::created("inert-badtier-sandbox");
    let dir = TempDir::reserved("inert-badtier");
    let run = Spec::new("main-only")
        .sandbox(sandbox.path())
        .spool(dir.path())
        .tier("trace")
        .run();
    assert!(
        !dir.exists(),
        "a refused tier must not create {}",
        dir.path().display()
    );
    sandbox.assert_untouched("SENSORIUM_TIER=trace");
    let lines: Vec<&str> = run.stderr.lines().collect();
    assert_eq!(
        lines.len(),
        1,
        "exactly one line, not a line per call: {lines:?}"
    );
    assert!(
        lines[0].contains("trace"),
        "the line names the value it refused: {:?}",
        lines[0]
    );
    assert!(
        lines[0].starts_with("sensorium-rt:"),
        "the line names its source: {:?}",
        lines[0]
    );
}

#[test]
fn an_enter_reached_from_inside_the_runtime_is_inert() {
    let dir = TempDir::reserved("inert-reentrant");
    Spec::new("reentrant").spool(dir.path()).run();
    let s = dir.spool(1);
    let sites: Vec<u32> = s
        .of_kind(KIND_CALL)
        .iter()
        .map(|r| r.site_index())
        .collect();
    assert_eq!(
        sites,
        vec![91],
        "site 90 ran inside the runtime and must not be recorded; site 91 must be"
    );
}
