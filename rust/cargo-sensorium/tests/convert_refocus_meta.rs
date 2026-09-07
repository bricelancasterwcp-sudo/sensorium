//! The three invocation-scoped meta keys `cargo-sensorium 0.5.0` writes
//! (design 2026-09-07 §2.2), through the REAL binary over hand-built spools:
//! `workspace_root`, `refocus_of` and `invocation_processes`.
//!
//! All three come from facts only the INVOCATION holds -- the workspace cargo
//! ran in, the flag the driver was given, the number of test binaries the run
//! produced -- so every one of them is asserted on every trace the invocation
//! wrote, not just on the first. `refocus` reads them to decide whether one
//! trace is the whole answer and where to re-run from, and it reads them from
//! whichever trace it was handed.
//!
//! A file of its own rather than more of `convert_meta.rs`: that file is at
//! 758 lines and this crate's ceiling is 800.

mod common;

use std::path::PathBuf;
use std::process::{Command, Output};

use common::spooldir::{context, meta, open};
use common::wire::{self, site};
use common::Scratch;
use rusqlite::Connection;

const FILE: &str = "crates/demo/src/lib.rs";
const WS: &str = "/w";
const ORIGINAL: &str = "20260101-000000-aaaaaa";

/// A spool directory with N recorded test binaries, each one a pid with a
/// proc header, a spool and a runner record -- which is what makes the
/// invocation's process count something other than 1.
struct Fixture {
    #[allow(dead_code)] // held for its Drop cleanup
    scratch: Scratch,
    spool_dir: PathBuf,
    sensorium_dir: PathBuf,
}

impl Fixture {
    fn new(name: &str, pids: &[u32]) -> Fixture {
        let scratch = Scratch::in_build_dir(name);
        let target = scratch.p("target");
        let spool_dir = target.join("sensorium/spool/20260907-000000-000000");
        let manifests_dir = target.join("sensorium/manifests");
        let sensorium_dir = scratch.p("sensorium-dir");
        std::fs::create_dir_all(&spool_dir).unwrap();
        std::fs::create_dir_all(&manifests_dir).unwrap();
        wire::write_invocation(
            &spool_dir,
            "20260907-000000-000000",
            WS,
            &target.to_string_lossy(),
        );
        wire::write_manifest(
            &manifests_dir,
            "meta1",
            "demo",
            &[(FILE, &[site(0, "compute", 10, "value")])],
            &[(FILE, "deadbeef")],
            false,
            None,
            &[],
        );
        for &pid in pids {
            wire::write_proc_header(
                &spool_dir,
                pid,
                1,
                &format!("/w/target/debug/deps/demo-{pid}"),
                &[(0, "meta1")],
                None,
            );
            wire::SpoolBuilder::new(pid, 1, "main")
                .call(0, 1000, 0, 0)
                .ret_none(1, 2000, 0, 0)
                .write(&spool_dir);
            wire::write_runner_record(&spool_dir, pid, Some(0), None);
        }
        Fixture {
            scratch,
            spool_dir,
            sensorium_dir,
        }
    }

    fn refocus_of(&self, run_id: &str) {
        wire::set_invocation_refocus_of(&self.spool_dir, run_id);
    }

    fn convert(&self) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["convert", &self.spool_dir.to_string_lossy()])
            .env("SENSORIUM_DIR", &self.sensorium_dir)
            .output()
            .expect("run cargo-sensorium convert")
    }

    /// Every trace this invocation wrote, in run-id order.
    fn traces(&self) -> Vec<Connection> {
        let out = self.convert();
        assert!(out.status.success(), "{}", context(&out));
        let dir = self.sensorium_dir.join("traces");
        let mut found: Vec<PathBuf> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", dir.display()))
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
            .collect();
        found.sort();
        assert!(!found.is_empty(), "no trace was written");
        found.iter().map(|p| open(p)).collect()
    }
}

/// Whether the key is in the trace at all -- `meta()` panics on a missing
/// key, and "absent" is the assertion here.
fn has_meta(conn: &Connection, key: &str) -> bool {
    conn.query_row("SELECT 1 FROM meta WHERE key = ?1", [key], |_| Ok(()))
        .is_ok()
}

#[test]
fn the_refocus_of_the_invocation_was_given_reaches_every_process() {
    let f = Fixture::new("refocus-of-two-pids", &[7001, 7002]);
    f.refocus_of(ORIGINAL);
    let traces = f.traces();
    assert_eq!(traces.len(), 2, "two test binaries, two traces");
    for conn in &traces {
        assert_eq!(meta(conn, "refocus_of"), ORIGINAL);
    }
}

/// Absent, not null. `refocus`'s pair lookup asks the store which traces
/// carry `refocus_of`; a null written on every ordinary run would answer it
/// with every trace ever recorded.
#[test]
fn an_ordinary_run_carries_no_refocus_of_key_at_all() {
    let f = Fixture::new("refocus-of-absent", &[7101]);
    let conn = &f.traces()[0];
    assert!(
        !has_meta(conn, "refocus_of"),
        "an ordinary run must write no refocus_of key, not a null one"
    );
}

#[test]
fn invocation_processes_is_the_number_of_test_binaries_this_invocation_ran() {
    let one = Fixture::new("invocation-processes-1", &[7201]);
    assert_eq!(meta(&one.traces()[0], "invocation_processes"), 1);

    let two = Fixture::new("invocation-processes-2", &[7301, 7302]);
    let traces = two.traces();
    assert_eq!(traces.len(), 2);
    // On BOTH traces: `refocus` refuses a re-run of one binary out of
    // several, and it is handed one trace, not the pair.
    for conn in &traces {
        assert_eq!(meta(conn, "invocation_processes"), 2);
    }
}

#[test]
fn the_workspace_root_is_the_one_the_invocation_recorded() {
    let f = Fixture::new("workspace-root", &[7401]);
    assert_eq!(meta(&f.traces()[0], "workspace_root"), WS);
}

/// Unconditional (design §2.2): the recorder CAN be re-invoked. Whether one
/// trace can be refocused is a refusal, not a capability.
#[test]
fn capabilities_refocus_is_true_for_every_trace_this_driver_converts() {
    let f = Fixture::new("capabilities-refocus", &[7501]);
    assert_eq!(meta(&f.traces()[0], "capabilities")["refocus"], true);
}
