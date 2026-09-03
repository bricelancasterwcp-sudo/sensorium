//! Meta-key content this recorder's own honesty promises name, over
//! hand-built fixtures: `uninstrumented` (a fallen-back unit still reaches
//! the trace, `rust/HONESTY.md` §8 item 7) and `panics_outside_frames` (a
//! PANIC record with no open frame is counted, not silently dropped, §1).

mod common;

use std::path::PathBuf;
use std::process::{Command, Output};

use common::wire::{self, site};
use common::Scratch;
use rusqlite::Connection;

const FILE: &str = "crates/demo/src/lib.rs";

#[allow(dead_code)]
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

    fn convert(&self) -> Output {
        Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
            .args(["convert", &self.spool_dir.to_string_lossy()])
            .env("SENSORIUM_DIR", &self.sensorium_dir)
            .output()
            .expect("run cargo-sensorium convert")
    }

    fn only_trace(&self) -> Connection {
        let dir = self.sensorium_dir.join("traces");
        let found: Vec<PathBuf> = std::fs::read_dir(&dir)
            .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", dir.display()))
            .map(|e| e.unwrap().path())
            .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
            .collect();
        assert_eq!(found.len(), 1, "{found:?}");
        Connection::open(&found[0]).unwrap()
    }
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

#[test]
fn a_fallen_back_unit_reaches_uninstrumented_even_though_this_process_never_registered_it() {
    let f = Fixture::new("uninstrumented-meta");
    // The unit this pid actually registered and ran.
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    // A SIBLING unit that fell back -- no process ever registers it, since a
    // fallen-back unit links no runtime at all, but the trace must still say
    // it happened.
    wire::write_manifest(
        &f.manifests_dir,
        "meta2",
        "helper",
        &[],
        &[],
        true,
        Some("rustc: E0999 something"),
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        1101,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1101, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();
    let uninstrumented = meta(&conn, "uninstrumented");
    let arr = uninstrumented.as_array().unwrap();
    assert_eq!(arr.len(), 1, "{uninstrumented}");
    assert_eq!(arr[0]["unit"], "meta2");
    assert_eq!(arr[0]["crate_name"], "helper");
    assert_eq!(arr[0]["reason"], "rustc: E0999 something");
}

#[test]
fn a_panic_record_with_no_open_frame_is_counted_and_never_written_as_an_event() {
    let f = Fixture::new("panics-outside-frames");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "main", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        1102,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // A CALL and its RETURN close the only frame this thread ever opens, and
    // THEN a PANIC record fires with nothing open on the stack -- e.g. code
    // that runs after the last traced call returns.
    wire::SpoolBuilder::new(1102, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .panic_record(2, 2500, &format!("{FILE}:9:1"), "orphaned panic")
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();
    assert_eq!(meta(&conn, "panics_outside_frames"), 1);
    assert_eq!(meta(&conn, "panics_unrecorded"), 0);
    // The stray PANIC never became a RAISE event: a causal event must carry
    // a code_id, and there was no frame to attach one from.
    let raises: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM events WHERE kind = 'RAISE'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(raises, 0);
    let total_events: i64 = conn
        .query_row("SELECT COUNT(*) FROM events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(total_events, 2, "only the CALL and the RETURN");
}
