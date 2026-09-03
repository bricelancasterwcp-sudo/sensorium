//! Fixture-driven tests of `cargo-sensorium convert <spool dir>`, over
//! HAND-BUILT bytes (`tests/common/wire.rs`) -- never the output of running
//! the runtime. Each fixture is a spool directory this test writes from the
//! wire format v2 block, converted through the real binary and read back
//! with `rusqlite` directly against the produced `.db` file.
//!
//! The blake2b pins and the schema-equality check live as internal unit
//! tests next to what they pin (`src/convert/fingerprint.rs`,
//! `src/convert/sqlite.rs`) and are not repeated here.

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

fn count(conn: &Connection, sql: &str) -> i64 {
    conn.query_row(sql, [], |r| r.get(0)).unwrap()
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
// The identical pair: equal stored fingerprints
// ---------------------------------------------------------------------------

#[test]
fn identical_processes_convert_to_traces_with_equal_stored_fingerprints() {
    let f = Fixture::new("identical-pair");
    f.one_site_manifest("meta1", "unit");
    for pid in [101u32, 102] {
        wire::write_proc_header(
            &f.spool_dir,
            pid,
            1,
            "/w/target/deps/demo",
            &[(0, "meta1")],
            None,
        );
        wire::SpoolBuilder::new(pid, 1, "main")
            .call(0, 1000, 0, 0)
            .ret_none(1, 2000, 0, 0)
            .thread_end(2, 2500)
            .write(&f.spool_dir);
    }
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let traces = f.traces();
    assert_eq!(traces.len(), 2, "{traces:?}");
    let (c1, c2) = (open(&traces[0]), open(&traces[1]));
    let (h1,): (String,) = c1
        .query_row(
            "SELECT hash FROM fingerprints WHERE thread_id = 1",
            [],
            |r| Ok((r.get(0)?,)),
        )
        .unwrap();
    let (h2,): (String,) = c2
        .query_row(
            "SELECT hash FROM fingerprints WHERE thread_id = 1",
            [],
            |r| Ok((r.get(0)?,)),
        )
        .unwrap();
    assert_eq!(h1, h2);
    // The main-thread row is present even though it is present for BOTH:
    // the pin this asserts is on equality, not merely on existence.
    assert_eq!(
        count(&c1, "SELECT n_events FROM fingerprints WHERE thread_id = 1"),
        2
    );
}

// ---------------------------------------------------------------------------
// Main thread: events.task_id is NULL, and main is never a task
// ---------------------------------------------------------------------------

#[test]
fn a_main_threads_own_causal_events_carry_a_null_task_id() {
    let f = Fixture::new("main-task-id-null");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        1001,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(1001, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .thread_end(2, 2500)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let null_task_events: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM events WHERE thread_id = 1 AND task_id IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(null_task_events, 2, "both the CALL and the RETURN");
    let non_null_on_main: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM events WHERE thread_id = 1 AND task_id IS NOT NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(non_null_on_main, 0);
    // Main is never a task: no `tasks` row for serial 1.
    let main_task_rows: i64 = conn
        .query_row("SELECT COUNT(*) FROM tasks WHERE id = 1", [], |r| r.get(0))
        .unwrap();
    assert_eq!(main_task_rows, 0);
}

// ---------------------------------------------------------------------------
// Torn tail / missing seq: seq_gaps
// ---------------------------------------------------------------------------

#[test]
fn a_torn_tail_yields_n_events_and_zero_seq_gaps() {
    let f = Fixture::new("torn-tail");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        201,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // CALL, RETURN, then a kind-0 tail: the mapped-but-unwritten remainder of
    // a chunk, not corruption.
    wire::SpoolBuilder::new(201, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .zero_tail(64)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(count(&conn, "SELECT COUNT(*) FROM events"), 2);
    assert_eq!(meta(&conn, "seq_gaps"), 0);
    // No THREAD_END was ever written after the tail: this thread is live.
    assert_eq!(meta(&conn, "live_threads"), serde_json::json!(["main"]));
    assert_eq!(meta(&conn, "incomplete"), false);
}

#[test]
fn a_missing_seq_is_counted_as_one_gap() {
    let f = Fixture::new("missing-seq");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        202,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // seq 0 (CALL), seq 1 MISSING, seq 2 (RETURN).
    wire::SpoolBuilder::new(202, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(2, 3000, 0, 0)
        .thread_end(3, 3500)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(meta(&conn, "seq_gaps"), 1);
}

// ---------------------------------------------------------------------------
// Live thread: named in live_threads, incomplete stays false
// ---------------------------------------------------------------------------

#[test]
fn a_thread_with_no_thread_end_is_named_in_live_threads() {
    let f = Fixture::new("live-thread");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        301,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(301, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        // No THREAD_END.
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(meta(&conn, "live_threads"), serde_json::json!(["main"]));
    assert_eq!(meta(&conn, "incomplete"), false);
}

// ---------------------------------------------------------------------------
// Panic: RAISE + unwind, and the unrecorded case
// ---------------------------------------------------------------------------

#[test]
fn a_panic_yields_a_raise_and_an_unwind_with_the_pending_records_fields() {
    let f = Fixture::new("panic");
    f.one_site_manifest("meta1", "value");
    wire::write_proc_header(
        &f.spool_dir,
        401,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(401, 1, "main")
        .call(0, 1000, 0, 0)
        .panic_record(1, 1500, &format!("{FILE}:3:5"), "boom")
        .ret_panic(2, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let (kind, line, payload): (String, Option<i64>, String) = conn
        .query_row(
            "SELECT kind, line, payload FROM events WHERE kind = 'RAISE'",
            [],
            |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
        )
        .unwrap();
    assert_eq!(kind, "RAISE");
    assert_eq!(line, Some(3), "the panic's own file matches the frame's");
    let p: serde_json::Value = serde_json::from_str(&payload).unwrap();
    assert_eq!(p["exc"]["type"], "panic");
    assert_eq!(p["exc"]["msg"], "boom");
    assert_eq!(p["exc"]["serial"], 1);
    let (closed_by, unwind_exc): (String, String) = conn
        .query_row(
            "SELECT closed_by, unwind_exc FROM frames LIMIT 1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(closed_by, "unwind");
    let u: serde_json::Value = serde_json::from_str(&unwind_exc).unwrap();
    assert_eq!(u["type"], "panic");
    assert_eq!(u["msg"], "boom");
    assert_eq!(u["serial"], 1);
    assert_eq!(meta(&conn, "panics_unrecorded"), 0);
}

#[test]
fn a_pending_panic_record_is_shared_by_every_frame_it_unwinds_through() {
    // outer calls inner; inner panics; BOTH frames close `panic` off the same
    // single PANIC record -- `rust/HONESTY.md` §1: "the pending unwind for
    // that thread until a non-panic RETURN", not "until the first frame
    // reads it".
    let f = Fixture::new("panic-multi-frame");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            FILE,
            &[site(0, "outer", 3, "value"), site(1, "inner", 6, "value")],
        )],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        403,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(403, 1, "main")
        .call(0, 1000, 0, 0) // outer
        .call(1, 1100, 0, 1) // inner
        .panic_record(2, 1500, &format!("{FILE}:6:1"), "boom")
        .ret_panic(3, 2000, 0, 1) // inner unwinds
        .ret_panic(4, 2100, 0, 0) // outer unwinds
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let mut stmt = conn
        .prepare("SELECT unwind_exc FROM frames ORDER BY depth")
        .unwrap();
    let rows: Vec<String> = stmt
        .query_map([], |r| r.get::<_, String>(0))
        .unwrap()
        .map(Result::unwrap)
        .collect();
    assert_eq!(rows.len(), 2, "{rows:?}");
    for raw in &rows {
        let u: serde_json::Value = serde_json::from_str(raw).unwrap();
        assert_eq!(u["type"], "panic");
        assert_eq!(u["msg"], "boom");
        assert_eq!(
            u["serial"], 1,
            "both frames share the one PANIC record's serial"
        );
    }
    assert_eq!(meta(&conn, "panics_unrecorded"), 0);
}

#[test]
fn a_frame_that_unwinds_with_no_pending_panic_record_gets_the_ruled_message() {
    let f = Fixture::new("panic-unrecorded");
    f.one_site_manifest("meta1", "value");
    wire::write_proc_header(
        &f.spool_dir,
        402,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // No PANIC record at all -- the hook was replaced, or the case
    // `rust/HONESTY.md` §1 names.
    wire::SpoolBuilder::new(402, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_panic(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let unwind_exc: String = conn
        .query_row("SELECT unwind_exc FROM frames LIMIT 1", [], |r| r.get(0))
        .unwrap();
    let u: serde_json::Value = serde_json::from_str(&unwind_exc).unwrap();
    assert_eq!(u["type"], "panic");
    assert_eq!(
        u["msg"],
        "<panic message not recorded: no PANIC record preceded this unwind>"
    );
    assert_eq!(u["serial"], 0);
    assert_eq!(meta(&conn, "panics_unrecorded"), 1);
}

// ---------------------------------------------------------------------------
// Unit fn and value-fn bypass
// ---------------------------------------------------------------------------

#[test]
fn a_unit_fn_with_wire_outcome_none_reads_ok_with_value_unit() {
    let f = Fixture::new("unit-fn");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        501,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(501, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let payload: String = conn
        .query_row(
            "SELECT payload FROM events WHERE kind = 'RETURN'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let p: serde_json::Value = serde_json::from_str(&payload).unwrap();
    assert_eq!(p["outcome"], "ok");
    assert_eq!(p["value"], serde_json::json!({"k": "dbg", "v": "()"}));
}

#[test]
fn a_value_fn_bypassed_by_a_question_mark_reads_none_with_no_value_key() {
    let f = Fixture::new("value-bypass");
    f.one_site_manifest("meta1", "value");
    wire::write_proc_header(
        &f.spool_dir,
        502,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(502, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let payload: String = conn
        .query_row(
            "SELECT payload FROM events WHERE kind = 'RETURN'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    let p: serde_json::Value = serde_json::from_str(&payload).unwrap();
    assert_eq!(p["outcome"], "none");
    assert!(p.get("value").is_none(), "{p}");
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

// ---------------------------------------------------------------------------
// Refused unit and unreached files
// ---------------------------------------------------------------------------

#[test]
fn a_refused_unit_reaches_units_refused_in_the_trace() {
    let f = Fixture::new("refused-unit");
    f.one_site_manifest("meta1", "unit");
    wire::write_proc_header(
        &f.spool_dir,
        801,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        Some("meta255"),
    );
    wire::SpoolBuilder::new(801, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(
        meta(&conn, "units_refused"),
        serde_json::json!({"refused": true, "at": "meta255"})
    );
}

#[test]
fn unreached_files_from_a_registered_units_manifest_reach_the_trace() {
    let f = Fixture::new("unreached-files");
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, QUALNAME, 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &["crates/demo/src/ghost.rs"],
    );
    wire::write_proc_header(
        &f.spool_dir,
        802,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(802, 1, "main")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    assert_eq!(
        meta(&conn, "unreached_files"),
        serde_json::json!(["crates/demo/src/ghost.rs"])
    );
}

// ---------------------------------------------------------------------------
// Zero-count fingerprint row: the main thread, even with nothing on it
// ---------------------------------------------------------------------------

#[test]
fn the_main_thread_gets_a_zero_count_fingerprint_row_when_it_ran_nothing_itself() {
    let f = Fixture::new("zero-count-main");
    f.one_site_manifest("meta1", "unit");
    // Everything causal happens on a non-main thread (serial 2); main's own
    // spool never opens at all (no CALL/RETURN on it), so this pins the case
    // where the row must still exist with hash of the empty input.
    wire::write_proc_header(
        &f.spool_dir,
        901,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    wire::SpoolBuilder::new(901, 2, "worker")
        .call(0, 1000, 0, 0)
        .ret_none(1, 2000, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = open(&f.traces()[0]);
    let (hash, n): (String, i64) = conn
        .query_row(
            "SELECT hash, n_events FROM fingerprints WHERE thread_id = 1",
            [],
            |r| Ok((r.get(0)?, r.get(1)?)),
        )
        .unwrap();
    assert_eq!(n, 0);
    assert_eq!(
        hash, "cae66941d9efbd404e4d88758ea67670",
        "the empty blake2b pin"
    );
    // The worker DID become a task with its own non-zero fingerprint.
    let task_n: i64 = conn
        .query_row(
            "SELECT n_events FROM task_fingerprints WHERE task_id = 2",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(task_n, 2);
    assert_eq!(
        meta(&conn, "threads_started"),
        serde_json::json!(1),
        "one non-main spool (the worker)"
    );
}

trait OutputExt {
    fn stdout_str(&self) -> String;
}

impl OutputExt for Output {
    fn stdout_str(&self) -> String {
        String::from_utf8_lossy(&self.stdout).into_owned()
    }
}
