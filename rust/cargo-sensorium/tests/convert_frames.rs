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
