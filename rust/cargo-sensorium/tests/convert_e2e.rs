//! End to end: run the driver smoke crate (as `tests/driver_smoke.rs` does),
//! and open every trace it produced with `rusqlite`, asserting the shape a
//! real invocation must have -- not a hand-built one.

mod common;

use std::path::Path;
use std::process::Command;

use common::Scratch;
use rusqlite::Connection;

const LIB: &str = r#"//! A crate small enough to read and big enough to record.

pub fn add(a: u8, b: u8) -> u8 {
    a + b
}

pub fn double(x: u8) -> u8 {
    add(x, x)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn doubling_three_is_six() {
        assert_eq!(double(3), 6);
    }
}
"#;

#[test]
fn a_real_invocation_converts_to_traces_a_reader_can_open() {
    let s = Scratch::in_build_dir("convert-e2e");
    s.write(
        "ws/Cargo.toml",
        "[workspace]\n\n[package]\nname = \"e2esmoke\"\nversion = \"0.0.0\"\nedition = \"2021\"\n",
    );
    s.write("ws/src/lib.rs", LIB);
    let target = s.p("target");
    let sensorium_dir = s.p("sensorium-dir");

    let out = Command::new(env!("CARGO_BIN_EXE_cargo-sensorium"))
        .args(["sensorium", "test"])
        .current_dir(s.p("ws"))
        .env("CARGO_TARGET_DIR", &target)
        .env("SENSORIUM_DIR", &sensorium_dir)
        .env_remove("RUSTC_WORKSPACE_WRAPPER")
        .env_remove("RUSTC_WRAPPER")
        .env_remove("RUSTFLAGS")
        .env_remove("RUSTDOCFLAGS")
        .env_remove("CARGO_ENCODED_RUSTFLAGS")
        .env_remove("SENSORIUM_SPOOL")
        .env_remove("SENSORIUM_TIER")
        .env_remove("SENSORIUM_INNER_RUNNER")
        .output()
        .expect("run the driver");

    let stdout = String::from_utf8_lossy(&out.stdout).into_owned();
    let stderr = String::from_utf8_lossy(&out.stderr).into_owned();
    let context = format!("--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}");
    assert_eq!(out.status.code(), Some(0), "{context}");
    assert!(stdout.contains("test result: ok"), "{context}");

    // The converter's own output: at least one `run:` line, on stdout, before
    // the driver's `spool:`/`cargo exit:` lines on stderr.
    let run_lines: Vec<&str> = stdout.lines().filter(|l| l.starts_with("run: ")).collect();
    assert!(
        !run_lines.is_empty(),
        "no `run:` line in stdout:\n{context}"
    );
    for line in &run_lines {
        assert!(line.contains("pid:"), "{line}");
        assert!(line.contains("exe:"), "{line}");
        assert!(line.contains("events:"), "{line}");
        assert!(line.contains("threads:"), "{line}");
        assert!(line.contains("exit:"), "{line}");
    }
    assert!(stderr.contains("spool:"), "{context}");
    assert!(stderr.contains("cargo exit: 0"), "{context}");
    assert!(
        !stderr.contains("cargo-sensorium: "),
        "a conversion error leaked:\n{context}"
    );

    let traces_dir = sensorium_dir.join("traces");
    let dbs: Vec<_> = std::fs::read_dir(&traces_dir)
        .unwrap_or_else(|e| panic!("no traces dir at {}: {e}", traces_dir.display()))
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().and_then(|e| e.to_str()) == Some("db"))
        .collect();
    assert_eq!(
        dbs.len(),
        run_lines.len(),
        "one `.db` per `run:` line: {dbs:?}"
    );
    assert!(!dbs.is_empty());

    for db in &dbs {
        check_trace(db);
    }
}

fn check_trace(db: &Path) {
    let conn = Connection::open(db).unwrap_or_else(|e| panic!("cannot open {}: {e}", db.display()));
    let ctx = format!("trace {}", db.display());

    assert_eq!(meta(&conn, "trace_format"), 4, "{ctx}");
    assert_eq!(meta(&conn, "incomplete"), false, "{ctx}");

    // `db.REQUIRED_META`, verbatim.
    for key in [
        "run_id",
        "argv",
        "cwd",
        "env_hash",
        "start_ts",
        "end_ts",
        "exit_status",
        "main_thread_ident",
        "fingerprint_basis",
        "truncated_count",
        "source_hashes",
        "recorder",
        "lang",
        "capabilities",
    ] {
        assert!(
            has_meta(&conn, key),
            "{ctx}: missing required meta key {key}"
        );
    }
    assert_eq!(meta(&conn, "lang"), "rust", "{ctx}");
    assert!(
        meta(&conn, "recorder")
            .as_str()
            .unwrap()
            .starts_with("sensorium-rt "),
        "{ctx}"
    );

    let calls: i64 = conn
        .query_row("SELECT COUNT(*) FROM events WHERE kind = 'CALL'", [], |r| {
            r.get(0)
        })
        .unwrap();
    let frames: i64 = conn
        .query_row("SELECT COUNT(*) FROM frames", [], |r| r.get(0))
        .unwrap();
    assert_eq!(frames, calls, "{ctx}: one frame per CALL");
    assert!(
        calls > 0,
        "{ctx}: a two-function crate under test must record calls"
    );

    // Every frame closed: the test binary ran to completion, so nothing
    // should still be open.
    let open_frames: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM frames WHERE closed_by IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(open_frames, 0, "{ctx}: an open frame after a clean exit");

    // Every CALL and RETURN carries a code_id and a task_id consistent with
    // the main-thread convention.
    let uncoded: i64 = conn
        .query_row(
            "SELECT COUNT(*) FROM events WHERE kind IN ('CALL','RETURN','RAISE') AND code_id IS NULL",
            [],
            |r| r.get(0),
        )
        .unwrap();
    assert_eq!(uncoded, 0, "{ctx}: a causal event with no code_id");
}

fn meta(conn: &Connection, key: &str) -> serde_json::Value {
    let raw: String = conn
        .query_row("SELECT value FROM meta WHERE key = ?1", [key], |r| r.get(0))
        .unwrap_or_else(|e| panic!("no meta key {key}: {e}"));
    serde_json::from_str(&raw).unwrap()
}

fn has_meta(conn: &Connection, key: &str) -> bool {
    conn.query_row("SELECT 1 FROM meta WHERE key = ?1", [key], |r| {
        r.get::<_, i64>(0)
    })
    .is_ok()
}
