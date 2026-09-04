//! Performance sanity for the trace writer: one transaction per trace under
//! WAL + `synchronous=NORMAL`, instead of one fsync'd commit per row.
//!
//! Not a benchmark, and -- disclosed here, not just in the task report --
//! **not a regression fence either: a FLOOR**. The acceptance run measured
//! 1118.9s for one bloomery invocation (119 processes, 134,394 events)
//! against the Python converter's 22.7s for the same invocation, ~49x,
//! entirely attributable to one committed (fsync'd) transaction per INSERT
//! (`wchan: jbd2_log_wait_commit`, 2.59 GB written for 32 MB of traces, the
//! device at 98.8%). At THIS fixture's size, on a fast/idle disk, that
//! difference does not reproduce: mutation-testing this fix by removing
//! `BEGIN`/`COMMIT` entirely (back to one commit per row) measured 2.546s
//! here for the same 100,000 records -- still under the 5s bound below, so
//! this test would NOT have caught that regression. The pathological
//! `jbd2_log_wait_commit` wait is a property of the device (busier, or
//! nearer full) and of scale (119 separate files, not one), neither of
//! which a single small fixture on a fast disk reproduces. What actually
//! discriminates the fix is the real acceptance-spool conversion --
//! 1118.9s -> 0.903s for the identical 119-process invocation -- cited in
//! the acceptance document's addendum. This test's job is narrower: stay
//! fast on any box (a floor under 5s), and catch the fix losing or
//! duplicating rows, which it does check for below.
//!
//! Row counts and meta are checked against what the fixture itself built --
//! the transaction wrapping changes WHEN bytes hit disk, never WHAT gets
//! written, and this is the test that would notice if it ever did.

mod common;

use std::path::PathBuf;
use std::process::{Command, Output};
use std::time::Instant;

use common::wire::{self, site};
use common::Scratch;
use rusqlite::Connection;

const FILE: &str = "crates/demo/src/lib.rs";

fn context(out: &Output) -> String {
    format!(
        "status: {:?}\n--- stdout ---\n{}\n--- stderr ---\n{}",
        out.status.code(),
        String::from_utf8_lossy(&out.stdout),
        String::from_utf8_lossy(&out.stderr)
    )
}

fn get_meta(conn: &Connection, key: &str) -> serde_json::Value {
    let raw: String = conn
        .query_row("SELECT value FROM meta WHERE key = ?1", [key], |r| r.get(0))
        .unwrap_or_else(|e| panic!("no meta key {key}: {e}"));
    serde_json::from_str(&raw).unwrap()
}

#[test]
fn a_hundred_thousand_record_spool_converts_in_seconds_not_minutes() {
    let scratch = Scratch::in_build_dir("convert-perf-100k");
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
    wire::write_manifest(
        &manifests_dir,
        "meta1",
        "demo",
        &[(FILE, &[site(0, "hot_fn", 3, "unit")])],
        &[(FILE, "deadbeef")],
        false,
        None,
        &[],
    );
    wire::write_proc_header(
        &spool_dir,
        9001,
        1,
        "/w/target/deps/demo",
        &[(0, "meta1")],
        None,
    );

    // 50,000 CALL/RETURN pairs on one thread, one site, back to back: a
    // 100,000-record spool, matching the shape the reviewer measured 2.6s
    // against before this fix.
    const PAIRS: u64 = 50_000;
    let mut b = wire::SpoolBuilder::new(9001, 1, "main");
    let mut seq = 0u64;
    let mut ts = 1000u64;
    for _ in 0..PAIRS {
        b = b.call(seq, ts, 0, 0);
        seq += 1;
        ts += 10;
        b = b.ret_none(seq, ts, 0, 0);
        seq += 1;
        ts += 10;
    }
    b = b.thread_end(seq, ts);
    b.write(&spool_dir);

    let start = Instant::now();
    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["convert", &spool_dir.to_string_lossy()])
        .env("SENSORIUM_DIR", &sensorium_dir)
        .output()
        .expect("run cargo-sensorium convert");
    let elapsed = start.elapsed();

    assert_eq!(out.status.code(), Some(0), "{}", context(&out));
    // Printed unconditionally (not just on failure): the report wants the
    // number, not just the pass/fail.
    eprintln!(
        "convert_perf: 100,000 records converted in {:.3}s (debug build)",
        elapsed.as_secs_f64()
    );
    assert!(
        elapsed.as_secs_f64() < 5.0,
        "converting 100,000 records took {:.2}s in a debug build; one \
         transaction per trace should keep this to a couple of seconds at \
         most: {}",
        elapsed.as_secs_f64(),
        context(&out)
    );

    let traces_dir = sensorium_dir.join("traces");
    let dbs: Vec<PathBuf> = std::fs::read_dir(&traces_dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
        .collect();
    assert_eq!(dbs.len(), 1, "{dbs:?}");
    let conn = Connection::open(&dbs[0]).unwrap();

    let events: i64 = conn
        .query_row("SELECT COUNT(*) FROM events", [], |r| r.get(0))
        .unwrap();
    assert_eq!(events, 2 * PAIRS as i64, "one CALL and one RETURN per pair");

    let frames: i64 = conn
        .query_row("SELECT COUNT(*) FROM frames", [], |r| r.get(0))
        .unwrap();
    assert_eq!(frames, PAIRS as i64, "one frame per CALL");

    let open_frames: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM frames WHERE closed_by IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(open_frames, 0, "every frame closed by its RETURN");

    let bad_closed_by: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM frames WHERE closed_by != 'return'",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(bad_closed_by, 0);

    let code_objects: i64 = conn
        .query_row("SELECT COUNT(*) FROM code_objects", [], |r| r.get(0))
        .unwrap();
    assert_eq!(
        code_objects, 1,
        "one site, interned once across 50,000 calls"
    );

    let fingerprints: i64 = conn
        .query_row("SELECT COUNT(*) FROM fingerprints", [], |r| r.get(0))
        .unwrap();
    assert_eq!(fingerprints, 1, "the one main-thread row");

    let (fp_n_events,): (i64,) = conn
        .query_row(
            "SELECT n_events FROM fingerprints WHERE thread_id = 1",
            [],
            |r| Ok((r.get(0)?,)),
        )
        .unwrap();
    assert_eq!(fp_n_events, 2 * PAIRS as i64);

    // Meta: trace_format/incomplete are exactly the two writes this fix's
    // ordering rule (COMMIT is one call, at the very end, after `incomplete
    // = false`) must not disturb.
    assert_eq!(get_meta(&conn, "trace_format"), 4);
    assert_eq!(get_meta(&conn, "incomplete"), false);
    assert_eq!(get_meta(&conn, "seq_gaps"), 0);
    assert_eq!(get_meta(&conn, "records_dropped"), serde_json::json!({}));
}
