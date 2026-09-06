//! The per-thread frame-stack invariant: `frames.parent_id`, `frames.depth`
//! and `frames.thread_id` are derived from EACH thread's OWN open-frame
//! stack, never a process-global view of every thread's frames combined.
//!
//! No other fixture in this suite exercises two threads with their own CALLs
//! interleaved by `seq` while both have open frames at once, so a mutation
//! that flattened the per-thread stacks into one shared view -- taking the
//! last-opened frame ACROSS all threads as "the parent", and its position in
//! that shared view as "the depth" -- would pass every other test in this
//! crate. This fixture is built specifically to fail under that mutation.

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

fn context(out: &Output) -> String {
    format!(
        "status: {:?}\n--- stdout ---\n{}\n--- stderr ---\n{}",
        out.status.code(),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

/// A row read back from `frames`, keyed by which site opened it.
#[derive(Debug, PartialEq, Eq)]
struct FrameRow {
    parent_qualname: Option<String>,
    depth: i64,
    thread_id: i64,
}

fn frame_row_for(conn: &Connection, qualname: &str) -> FrameRow {
    // Join frames -> code_objects (for the frame's own qualname) and, via a
    // self-join on parent_id, the PARENT's qualname -- so the assertion reads
    // by name, not by an id whose value this test does not otherwise care
    // about.
    conn.query_row(
        "SELECT p.qualname, f.depth, f.thread_id \
         FROM frames f \
         JOIN code_objects c ON c.id = f.code_id \
         LEFT JOIN frames pf ON pf.id = f.parent_id \
         LEFT JOIN code_objects p ON p.id = pf.code_id \
         WHERE c.qualname = ?1",
        [qualname],
        |r| {
            Ok(FrameRow {
                parent_qualname: r.get(0)?,
                depth: r.get(1)?,
                thread_id: r.get(2)?,
            })
        },
    )
    .unwrap_or_else(|e| panic!("no frame for qualname {qualname:?}: {e}"))
}

#[test]
fn each_threads_frame_stack_is_its_own_not_a_shared_process_global_view() {
    let f = Fixture::new("frames-per-thread");
    // One unit, three sites: `a` and `b` on thread 2 (nested: b inside a),
    // `x` alone on thread 3.
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            FILE,
            &[
                site(0, "a", 3, "unit"),
                site(1, "b", 6, "unit"),
                site(2, "x", 9, "unit"),
            ],
        )],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        1201,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    // t2: CALL a(seq 0), t3: CALL x(seq 1), t2: CALL b(seq 2, nested in a),
    // t3: RETURN x(seq 3), t2: RETURN b(seq 4), t2: RETURN a(seq 5) -- the
    // interleaving the reviewer's finding names, seq order across threads.
    wire::SpoolBuilder::new(1201, 2, "worker-a")
        .call(0, 1000, 0, 0) // a
        .call(2, 1200, 0, 1) // b, nested in a
        .ret_none(4, 1400, 0, 1) // b returns
        .ret_none(5, 1500, 0, 0) // a returns
        .write(&f.spool_dir);
    wire::SpoolBuilder::new(1201, 3, "worker-b")
        .call(1, 1100, 0, 2) // x
        .ret_none(3, 1300, 0, 2) // x returns
        .write(&f.spool_dir);

    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();

    let a = frame_row_for(&conn, "a");
    assert_eq!(a.parent_qualname, None, "a is a root frame");
    assert_eq!(a.depth, 0);
    assert_eq!(a.thread_id, 2);

    let b = frame_row_for(&conn, "b");
    assert_eq!(
        b.parent_qualname,
        Some("a".to_owned()),
        "b's parent is a, on the SAME thread -- never x, which opened in between by seq"
    );
    assert_eq!(b.depth, 1);
    assert_eq!(b.thread_id, 2);

    let x = frame_row_for(&conn, "x");
    assert_eq!(
        x.parent_qualname, None,
        "x is a root frame on ITS OWN thread, regardless of what was open on thread 2 at the time"
    );
    assert_eq!(x.depth, 0, "x's depth must not count thread 2's open frame");
    assert_eq!(x.thread_id, 3);
}

/// A row read back from `events`.
struct EventRow {
    kind: String,
    frame_id: Option<i64>,
    code_id: Option<i64>,
    line: Option<i64>,
    payload: serde_json::Value,
}

fn event_rows(conn: &Connection) -> Vec<EventRow> {
    let mut stmt = conn
        .prepare("SELECT kind, frame_id, code_id, line, payload FROM events ORDER BY id")
        .unwrap();
    let rows = stmt
        .query_map([], |r| {
            let payload: Option<String> = r.get(4)?;
            Ok(EventRow {
                kind: r.get(0)?,
                frame_id: r.get(1)?,
                code_id: r.get(2)?,
                line: r.get(3)?,
                payload: payload.map_or(serde_json::Value::Null, |p| {
                    serde_json::from_str(&p).unwrap()
                }),
            })
        })
        .unwrap();
    rows.map(Result::unwrap).collect()
}

fn line_fixture(name: &str, pid: u32) -> Fixture {
    let f = Fixture::new(name);
    wire::write_manifest(
        &f.manifests_dir,
        "meta1",
        "demo",
        &[(
            FILE,
            &[site(0, "fill", 3, "unit"), wire::line_site(1, "fill", 5)],
        )],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &f.spool_dir,
        pid,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );
    f
}

/// Design §3.5: a LINE record becomes an `events` row on the frame that is
/// OPEN -- the CALL's -- carrying the fn's code object, the STATEMENT's line
/// (not the fn's), and the deltas in the capture shape a RETURN value already
/// uses. It pushes and pops nothing, and it is not a fingerprint event.
#[test]
fn a_line_record_becomes_a_row_on_the_open_frame_with_the_statements_own_line() {
    let f = line_fixture("frames-line-row", 1301);
    wire::SpoolBuilder::new(1301, 1, "main")
        .call(0, 1000, 0, 0)
        .line(
            1,
            1100,
            0,
            1,
            false,
            &[
                ("x", wire::LineDelta::Dbg("5", false)),
                ("buf", wire::LineDelta::Unread),
            ],
        )
        .ret_none(2, 1200, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();

    let rows = event_rows(&conn);
    let kinds: Vec<&str> = rows.iter().map(|r| r.kind.as_str()).collect();
    assert_eq!(
        kinds,
        ["CALL", "LINE", "RETURN"],
        "three rows, in seq order"
    );

    let frame_id: i64 = conn
        .query_row("SELECT id FROM frames", [], |r| r.get(0))
        .expect("exactly one frame");
    let code_id: i64 = conn
        .query_row(
            "SELECT id FROM code_objects WHERE qualname = 'fill'",
            [],
            |r| r.get(0),
        )
        .expect("the fn's code object");
    let frames: i64 = conn
        .query_row("SELECT COUNT(*) FROM frames", [], |r| r.get(0))
        .unwrap();
    assert_eq!(frames, 1, "a LINE pushes and pops nothing");

    let line = &rows[1];
    assert_eq!(
        line.frame_id,
        Some(frame_id),
        "the LINE row sits on the CALL's frame"
    );
    assert_eq!(
        line.code_id,
        Some(code_id),
        "and carries the fn's code object"
    );
    assert_eq!(line.line, Some(5), "the statement's line, not the fn's 3");
    assert_eq!(
        line.payload,
        serde_json::json!({
            "deltas": {"x": {"k": "dbg", "v": "5", "trunc": false},
                       "buf": {"k": "unread"}}
        }),
        "no `unread` key when nothing was dropped"
    );

    let n_events: i64 = conn
        .query_row(
            "SELECT n_events FROM fingerprints WHERE thread_id = 1",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(
        n_events, 2,
        "the fingerprint still counts CALL and RETURN only"
    );
}

/// `flags.bit0` is the runtime saying the record is SHORT, and the row must
/// say so in the one key a reader already knows: `unread: ["locals"]`.
#[test]
fn a_line_record_whose_deltas_were_dropped_says_unread_locals() {
    let f = line_fixture("frames-line-dropped", 1302);
    wire::SpoolBuilder::new(1302, 1, "main")
        .call(0, 1000, 0, 0)
        .line(
            1,
            1100,
            0,
            1,
            true,
            &[("x", wire::LineDelta::Dbg("5", false))],
        )
        .ret_none(2, 1200, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();
    let rows = event_rows(&conn);
    assert_eq!(
        rows[1].payload,
        serde_json::json!({
            "deltas": {"x": {"k": "dbg", "v": "5", "trunc": false}},
            "unread": ["locals"]
        })
    );
}

/// A statement that wrote nothing is still a row: the empty `deltas` object
/// says the line RAN, which is the whole point of a LINE with no bindings.
#[test]
fn a_line_record_with_no_deltas_is_still_a_row_that_says_the_line_ran() {
    let f = line_fixture("frames-line-empty", 1303);
    wire::SpoolBuilder::new(1303, 1, "main")
        .call(0, 1000, 0, 0)
        .line(1, 1100, 0, 1, false, &[])
        .ret_none(2, 1200, 0, 0)
        .write(&f.spool_dir);
    let out = f.convert();
    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    let conn = f.only_trace();
    let rows = event_rows(&conn);
    assert_eq!(rows[1].kind, "LINE");
    assert_eq!(rows[1].payload, serde_json::json!({"deltas": {}}));
}
