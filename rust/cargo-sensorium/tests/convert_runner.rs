//! Invocation-level metadata over hand-built spool bytes: the exit status a
//! runner record witnesses (`exit_status`, `exit_signal`,
//! `exit_status_basis`) and the `child_runs` a parent names when a child of
//! the same invocation spooled beside it. Split from `convert.rs` at its
//! runner banner (the file was over the 800-line ceiling); these are the
//! only tests here that read the binary's own stdout rather than the DB,
//! which is why `OutputExt` lives with them.
//!
//! The fixture helpers below are this binary's own copies, as
//! `convert_meta.rs`/`convert_frames.rs`/`convert_errors.rs` each carry
//! theirs -- an integration test target is its own crate, and
//! `tests/common/` holds the wire writers, not the assertions' scaffolding.

mod common;

use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use common::wire::{self, site};
use common::Scratch;
use rusqlite::Connection;

const FILE: &str = "crates/demo/src/lib.rs";
const QUALNAME: &str = "main";

/// A scratch tree with a real `target` (so a manifests directory can live on
/// disk), one invocation's spool directory under it, and an isolated
/// `SENSORIUM_DIR` this test's traces land in.
#[allow(dead_code)] // `scratch` is held only for its Drop cleanup; `target` documents the layout.
struct Fixture {
    scratch: Scratch,
    target: PathBuf,
    spool_dir: PathBuf,
    manifests_dir: PathBuf,
    sensorium_dir: PathBuf,
}

impl Fixture {
    fn new(name: &str) -> Fixture {
        let scratch = Scratch::in_build_dir(name);
        let target = scratch.p("target");
        let spool_dir = target.join("sensorium/spool/20260903-000000-000000");
        let manifests_dir = target.join("sensorium/manifests");
        let sensorium_dir = scratch.p("sensorium-dir");
        std::fs::create_dir_all(&spool_dir).unwrap();
        std::fs::create_dir_all(&manifests_dir).unwrap();
        wire::write_invocation(
            &spool_dir,
            "20260903-000000-000000",
            "/w",
            &target.to_string_lossy(),
        );
        Fixture {
            scratch,
            target,
            spool_dir,
            manifests_dir,
            sensorium_dir,
        }
    }

    /// The single-site manifest every non-error fixture below builds on:
    /// `crates/demo/src/lib.rs :: main`, the exact strings the blake2b pins
    /// are computed over.
    fn one_site_manifest(&self, metadata: &str, ret: &'static str) {
        wire::write_manifest(
            &self.manifests_dir,
            metadata,
            "demo",
            &[(FILE, &[site(0, QUALNAME, 3, ret)])],
            &[(FILE, "deadbeef")],
            false,
            None,
            &[],
        );
    }

    fn convert(&self) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["convert", &self.spool_dir.to_string_lossy()])
            .env("SENSORIUM_DIR", &self.sensorium_dir)
            .output()
            .expect("run cargo-sensorium convert")
    }

    fn traces(&self) -> Vec<PathBuf> {
        let dir = self.sensorium_dir.join("traces");
        let mut found: Vec<PathBuf> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", dir.display()))
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
            .collect();
        found.sort();
        found
    }
}

fn open(db: &Path) -> Connection {
    Connection::open(db).unwrap_or_else(|e| panic!("cannot open {}: {e}", db.display()))
}

fn meta(conn: &Connection, key: &str) -> serde_json::Value {
    let raw: String = conn
        .query_row("SELECT value FROM meta WHERE key = ?1", [key], |r| r.get(0))
        .unwrap_or_else(|e| panic!("no meta key {key}: {e}"));
    serde_json::from_str(&raw).unwrap()
}

fn context(out: &Output) -> String {
    format!(
        "status: {:?}\n--- stdout ---\n{}\n--- stderr ---\n{}",
        out.status.code(),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

// ---------------------------------------------------------------------------
// Runner: present, absent, signalled
// ---------------------------------------------------------------------------

#[test]
fn a_present_runner_record_yields_exit_status_and_basis_waited() {
    let f = Fixture::new("runner-present");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        601,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(601, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    wire::write_runner_record(&f.spool_dir, 601, Some(0), None);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(meta(&conn, "exit_status"), 0);
    assert_eq!(meta(&conn, "exit_status_basis"), "waited");
    assert!(out.stdout_str().contains("exit: 0"));
}

#[test]
fn no_runner_record_yields_null_exit_status_and_basis_unwitnessed() {
    let f = Fixture::new("runner-absent");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        602,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(602, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(meta(&conn, "exit_status"), serde_json::Value::Null);
    assert_eq!(meta(&conn, "exit_status_basis"), "unwitnessed");
    assert!(out.stdout_str().contains("exit: unwitnessed"));
}

#[test]
fn a_signalled_runner_record_yields_null_exit_status_and_the_signal_number() {
    let f = Fixture::new("runner-signalled");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        603,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(603, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    wire::write_runner_record(&f.spool_dir, 603, None, Some(9));
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(meta(&conn, "exit_status"), serde_json::Value::Null);
    assert_eq!(meta(&conn, "exit_signal"), 9);
    assert_eq!(meta(&conn, "exit_status_basis"), "waited");
    // The `run:` line's third exit form: witnessed but no exit code, because
    // a signal killed it -- never "unwitnessed", which would say nobody saw
    // it happen.
    assert!(
        out.stdout_str().contains("exit: signal 9"),
        "{}",
        context(&out)
    );
    assert!(
        !out.stdout_str().contains("exit: unwitnessed"),
        "a signalled process was witnessed, just not with a code: {}",
        context(&out)
    );
}

// ---------------------------------------------------------------------------
// Parent + child by ppid: child_runs
// ---------------------------------------------------------------------------

#[test]
fn a_child_of_the_same_invocation_is_named_in_the_parents_child_runs() {
    let f = Fixture::new("child-runs");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        701,
        0,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::write_proc_header(
        &f.spool_dir,
        702,
        701,
        "/w/target/deps/demo-child",
        &[(0, "meta1")],
        None,
    );
    for pid in [701u32, 702] {
        wire::SpoolBuilder::new(pid, 1, "main")
            .call(0, 1000, 0, 0)
            .ret_none(1, 2000, 0, 0)
            .write(&f.spool_dir);
    }
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let traces = f.traces();
    assert_eq!(traces.len(), 2);
    // Find the parent's trace by pid meta, not by array position: run ids
    // are minted, not ordered by pid.
    let parent = traces
        .iter()
        .map(|p| open(p))
        .find(|c| meta(c, "pid") == 701)
        .expect("parent trace");
    let child_runs = meta(&parent, "child_runs");
    let arr = child_runs.as_array().unwrap();
    assert_eq!(arr.len(), 1, "{child_runs}");
    assert_eq!(arr[0]["pid"], 702);
    assert_eq!(arr[0]["exe"], "/w/target/deps/demo-child");
    assert!(!arr[0]["run_id"].as_str().unwrap().is_empty());
}

trait OutputExt {
    fn stdout_str(&self) -> String;
}

impl OutputExt for Output {
    fn stdout_str(&self) -> String {
        String::from_utf8_lossy(&self.stdout).into_owned()
    }
}
