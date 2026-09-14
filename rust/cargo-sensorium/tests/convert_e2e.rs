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

    check_modes(&stderr, &dbs);
    check_redaction(&dbs, &sensorium_dir);
}

/// Nothing this invocation created is readable by another account on the box.
///
/// Every file named here holds either the recorded process's whole
/// environment (`<pid>.proc.json`, and the trace's `env` meta), its captured
/// return values (`.spool`), or its full argv (`<pid>.runner.json`) -- the
/// three places a secret typed on a command line or exported in a shell ends
/// up. They were 0644 in a 0755 directory until this slice, so a recording
/// made on a shared box handed them to everyone with an account.
///
/// End to end and not per unit: each mode is set at a different `open` or
/// `DirBuilder` in a different module, and only a real recording says all of
/// them fired on the same run.
fn check_modes(stderr: &str, dbs: &[std::path::PathBuf]) {
    use std::os::unix::fs::PermissionsExt;

    let spool = stderr
        .lines()
        .find_map(|l| l.strip_prefix("spool: "))
        .map(Path::new)
        .expect("the driver prints its spool directory");
    let mode = |p: &Path| {
        std::fs::metadata(p)
            .unwrap_or_else(|e| panic!("cannot stat {}: {e}", p.display()))
            .permissions()
            .mode()
            & 0o7777
    };

    // The spool directory and the `sensorium/spool` it was created under --
    // both this driver's own `DirBuilder`, which applies the mode to every
    // level it creates.
    assert_eq!(mode(spool), 0o700, "{}", spool.display());
    let parent = spool.parent().expect("<...>/sensorium/spool");
    assert_eq!(mode(parent), 0o700, "{}", parent.display());

    let mut seen = 0;
    for entry in std::fs::read_dir(spool).expect("read the spool directory") {
        let path = entry.unwrap().path();
        let name = path.file_name().unwrap().to_string_lossy().into_owned();
        if name.ends_with(".spool")
            || name.ends_with(".proc.json")
            || name.ends_with(".runner.json")
            // The DRIVER's own record of what it was about to spawn, and the
            // one file in this directory that held nothing out of the
            // recorded process -- so it was the one written with plain
            // `std::fs::write` and the one E16 part A found at 0664 (H2, the
            // tenth path). It holds the user's argv, their workspace root and
            // their target directory, which is not nothing.
            || name == "invocation.json"
        {
            assert_eq!(mode(&path), 0o600, "{name}");
            seen += 1;
        }
    }
    // A recording writes at least a header, a spool, a runner record and the
    // driver's own record; a loop over an empty directory would assert
    // nothing at all.
    assert!(seen >= 4, "only {seen} spool files in {}", spool.display());

    for db in dbs {
        assert_eq!(mode(db), 0o600, "{}", db.display());
    }

    // The store's `traces/` directory, which the CONVERTER creates (ruling
    // R26). It was the one directory in the store this driver still made with
    // the process umask, so a 0600 trace sat in a 0755 directory whose listing
    // named every run on the box.
    let traces = dbs
        .first()
        .and_then(|db| db.parent())
        .expect("a trace lives in the store's traces directory");
    assert_eq!(mode(traces), 0o700, "{}", traces.display());
}

/// The driver minted the store's key, handed it to the runtime, and the
/// converter carried what the runtime wrote into the trace.
///
/// Four modules and one hop through cargo's environment, which only a real
/// invocation exercises: `redaction_key` creates the file, `launch` puts its
/// hex in `SENSORIUM_REDACT_KEY`, `sensorium-rt` parses it and writes the
/// header's `redaction`/`env_redaction`, and `convert::redaction` carries
/// them into meta. `key_id` is what ties the two ends together -- a trace
/// whose digests were taken under some other key would still say
/// `keyed: true`.
fn check_redaction(dbs: &[std::path::PathBuf], sensorium_dir: &Path) {
    let material = std::fs::read(sensorium_dir.join("redaction.key"))
        .expect("the driver mints the store's key");
    assert_eq!(material.len(), 32);
    let expected = sensorium_rt::redact::Key::from_bytes(&material)
        .key_id()
        .expect("a 32-byte key has an id");

    for db in dbs {
        let conn = Connection::open(db).unwrap();
        let ctx = format!("trace {}", db.display());
        let r = meta(&conn, "redaction");
        assert_eq!(r["rule"], "v1", "{ctx}: {r}");
        assert_eq!(r["mode"], "on", "{ctx}: {r}");
        assert_eq!(r["keyed"], true, "{ctx}: {r}");
        assert_eq!(r["key_id"], expected.as_str(), "{ctx}: {r}");
        // The RECORDER applied it, not the converter: this runtime writes the
        // rule itself, and a `converter` here would mean the header arrived
        // without one -- plaintext on disk between the two.
        assert_eq!(r["by"], "recorder", "{ctx}: {r}");
        assert!(r["env"].is_object(), "{ctx}: {r}");
        // The key variable is DELETED from the recorded environment, never
        // redacted: a digest of the key under the key is a pointless row.
        let env = meta(&conn, "env");
        assert!(
            env.get("SENSORIUM_REDACT_KEY").is_none(),
            "{ctx}: the key variable reached the trace"
        );
        assert!(
            env.as_object().is_some_and(|e| !e.is_empty()),
            "{ctx}: an empty environment would pass every check above"
        );
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
