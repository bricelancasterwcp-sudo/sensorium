//! The trace store: `db.SCHEMA` verbatim, one connection per trace, and the
//! narrow set of statements the rest of `convert` needs.
//!
//! Every JSON column (`meta.value`, `events.payload`, `frames.unwind_exc`) is
//! written with `serde_json::to_string`, which is compact by construction --
//! no separator configuration needed to match the Python writer's
//! `separators=(",", ":")`.

use std::path::{Path, PathBuf};

#[cfg(test)]
use rusqlite::OptionalExtension;
use rusqlite::{params, Connection};
use serde::Serialize;

/// Verbatim from `src/sensorium/store/db.py`'s `SCHEMA` string (the four
/// `CREATE INDEX` lines included). `tests::the_schema_matches_the_python_source`
/// re-reads that file at test time and asserts byte-equality with this.
pub const SCHEMA: &str = r#"
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE code_objects (
  id INTEGER PRIMARY KEY,
  file TEXT NOT NULL,
  qualname TEXT NOT NULL,
  firstlineno INTEGER NOT NULL
);
CREATE TABLE frames (
  id INTEGER PRIMARY KEY,
  parent_id INTEGER,
  code_id INTEGER NOT NULL,
  call_event_id INTEGER NOT NULL,
  return_event_id INTEGER,
  depth INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  closed_by TEXT,
  unwind_exc TEXT,
  kind TEXT
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts_ns INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  frame_id INTEGER,
  code_id INTEGER,
  line INTEGER,
  payload TEXT,
  task_id INTEGER
);
CREATE TABLE output (
  id INTEGER PRIMARY KEY,
  after_event_id INTEGER NOT NULL,
  stream TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  name TEXT,
  thread_id INTEGER NOT NULL
);
CREATE TABLE fingerprints (
  thread_id INTEGER PRIMARY KEY,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
CREATE TABLE task_fingerprints (
  task_id INTEGER PRIMARY KEY,
  name TEXT,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
CREATE INDEX idx_events_code ON events(code_id);
CREATE INDEX idx_events_frame ON events(frame_id);
CREATE INDEX idx_events_kind ON events(kind);
CREATE INDEX idx_frames_code ON frames(code_id);
"#;

/// One trace under construction. `create` writes to a `.tmp` path; `finish`
/// closes the connection and renames it into place, so a converter killed
/// mid-write never leaves a half-written file at the name a reader would open.
pub struct TraceWriter {
    conn: Connection,
    tmp_path: PathBuf,
}

impl TraceWriter {
    /// # Errors
    /// Any SQLite failure opening or initialising the file.
    pub fn create(tmp_path: &Path) -> Result<TraceWriter, String> {
        if let Some(dir) = tmp_path.parent() {
            std::fs::create_dir_all(dir)
                .map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
        }
        // A stale `.tmp` from a killed prior run must not resurrect old rows.
        let _ = std::fs::remove_file(tmp_path);
        let conn = Connection::open(tmp_path)
            .map_err(|e| format!("cannot create trace {}: {e}", tmp_path.display()))?;
        conn.pragma_update(None, "journal_mode", "WAL")
            .map_err(|e| format!("PRAGMA journal_mode=WAL: {e}"))?;
        conn.execute_batch(SCHEMA)
            .map_err(|e| format!("cannot write the schema: {e}"))?;
        Ok(TraceWriter {
            conn,
            tmp_path: tmp_path.to_path_buf(),
        })
    }

    /// # Errors
    /// Any SQLite or serialisation failure.
    pub fn set_meta(&self, key: &str, value: &impl Serialize) -> Result<(), String> {
        let json = serde_json::to_string(value).map_err(|e| format!("meta {key}: {e}"))?;
        self.conn
            .execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?1, ?2)",
                params![key, json],
            )
            .map_err(|e| format!("cannot write meta {key}: {e}"))?;
        Ok(())
    }

    /// Interning is the caller's job (`frames::Interner`); this always inserts
    /// a fresh row and returns its id.
    ///
    /// # Errors
    /// Any SQLite failure.
    pub fn insert_code_object(
        &self,
        file: &str,
        qualname: &str,
        firstlineno: u32,
    ) -> Result<i64, String> {
        self.conn
            .execute(
                "INSERT INTO code_objects (file, qualname, firstlineno) VALUES (?1, ?2, ?3)",
                params![file, qualname, firstlineno],
            )
            .map_err(|e| format!("cannot write code_objects: {e}"))?;
        Ok(self.conn.last_insert_rowid())
    }

    /// # Errors
    /// Any SQLite or serialisation failure.
    #[allow(clippy::too_many_arguments)]
    pub fn insert_event(
        &self,
        ts_ns: u64,
        thread_id: u32,
        kind: &str,
        frame_id: Option<i64>,
        code_id: Option<i64>,
        line: Option<u32>,
        payload: Option<&serde_json::Value>,
        task_id: Option<u32>,
    ) -> Result<i64, String> {
        let payload_json = payload
            .map(serde_json::to_string)
            .transpose()
            .map_err(|e| format!("event payload: {e}"))?;
        self.conn
            .execute(
                "INSERT INTO events (ts_ns, thread_id, kind, frame_id, code_id, line, payload, \
                 task_id) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
                params![
                    ts_ns as i64,
                    thread_id,
                    kind,
                    frame_id,
                    code_id,
                    line,
                    payload_json,
                    task_id
                ],
            )
            .map_err(|e| format!("cannot write events: {e}"))?;
        Ok(self.conn.last_insert_rowid())
    }

    /// Opens a frame with `closed_by`/`return_event_id`/`unwind_exc` all NULL;
    /// [`Self::close_frame`] fills them in when (and if) the frame closes.
    ///
    /// # Errors
    /// Any SQLite failure.
    pub fn insert_frame(
        &self,
        parent_id: Option<i64>,
        code_id: i64,
        call_event_id: i64,
        depth: u32,
        thread_id: u32,
    ) -> Result<i64, String> {
        self.conn
            .execute(
                "INSERT INTO frames (parent_id, code_id, call_event_id, return_event_id, depth, \
                 thread_id, closed_by, unwind_exc, kind) VALUES (?1, ?2, ?3, NULL, ?4, ?5, NULL, \
                 NULL, 'function')",
                params![parent_id, code_id, call_event_id, depth, thread_id],
            )
            .map_err(|e| format!("cannot write frames: {e}"))?;
        Ok(self.conn.last_insert_rowid())
    }

    /// # Errors
    /// Any SQLite or serialisation failure.
    pub fn close_frame(
        &self,
        frame_id: i64,
        return_event_id: i64,
        closed_by: &str,
        unwind_exc: Option<&serde_json::Value>,
    ) -> Result<(), String> {
        let unwind_json = unwind_exc
            .map(serde_json::to_string)
            .transpose()
            .map_err(|e| format!("unwind_exc: {e}"))?;
        self.conn
            .execute(
                "UPDATE frames SET return_event_id = ?1, closed_by = ?2, unwind_exc = ?3 WHERE \
                 id = ?4",
                params![return_event_id, closed_by, unwind_json, frame_id],
            )
            .map_err(|e| format!("cannot close frame {frame_id}: {e}"))?;
        Ok(())
    }

    /// `id` is the thread serial, not an autoincrement rowid: the Rust model
    /// has no task identity independent of the thread that ran it.
    ///
    /// # Errors
    /// Any SQLite failure.
    pub fn insert_task(&self, id: u32, name: Option<&str>, thread_id: u32) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT INTO tasks (id, name, thread_id) VALUES (?1, ?2, ?3)",
                params![id, name, thread_id],
            )
            .map_err(|e| format!("cannot write tasks: {e}"))?;
        Ok(())
    }

    /// # Errors
    /// Any SQLite failure.
    pub fn insert_fingerprint(
        &self,
        thread_id: u32,
        hash: &str,
        n_events: u64,
    ) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT INTO fingerprints (thread_id, hash, n_events) VALUES (?1, ?2, ?3)",
                params![thread_id, hash, n_events as i64],
            )
            .map_err(|e| format!("cannot write fingerprints: {e}"))?;
        Ok(())
    }

    /// # Errors
    /// Any SQLite failure.
    pub fn insert_task_fingerprint(
        &self,
        task_id: u32,
        name: Option<&str>,
        hash: &str,
        n_events: u64,
    ) -> Result<(), String> {
        self.conn
            .execute(
                "INSERT INTO task_fingerprints (task_id, name, hash, n_events) VALUES (?1, ?2, \
                 ?3, ?4)",
                params![task_id, name, hash, n_events as i64],
            )
            .map_err(|e| format!("cannot write task_fingerprints: {e}"))?;
        Ok(())
    }

    /// Whether this connection currently has an `INTEGER PRIMARY KEY` row named
    /// `key` in `meta` -- used only by tests, to read a value back without a
    /// second reader implementation.
    #[cfg(test)]
    pub fn meta_json(&self, key: &str) -> Option<String> {
        self.conn
            .query_row("SELECT value FROM meta WHERE key = ?1", params![key], |r| {
                r.get::<_, String>(0)
            })
            .optional()
            .expect("query meta")
    }

    /// Close the connection and rename the `.tmp` file into place.
    ///
    /// # Errors
    /// Any filesystem failure renaming the file.
    pub fn finish(self, dest: &Path) -> Result<(), String> {
        let tmp = self.tmp_path.clone();
        drop(self.conn);
        std::fs::rename(&tmp, dest)
            .map_err(|e| format!("cannot rename {} to {}: {e}", tmp.display(), dest.display()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Reads `src/sensorium/store/db.py` at test time (relative to
    /// `CARGO_MANIFEST_DIR`, which is `rust/cargo-sensorium`), extracts the
    /// `SCHEMA = """…"""` block, and asserts it is byte-identical to
    /// [`SCHEMA`]. A drift between the two is exactly what this test exists to
    /// catch before Task 9's cross-recorder test would.
    #[test]
    fn the_schema_matches_the_python_source() {
        let db_py = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../src/sensorium/store/db.py")
            .canonicalize()
            .expect("db.py must exist at the expected path");
        let text = std::fs::read_to_string(&db_py)
            .unwrap_or_else(|e| panic!("cannot read {}: {e}", db_py.display()));
        let start = text
            .find("SCHEMA = \"\"\"")
            .expect("no SCHEMA = \"\"\" in db.py")
            + "SCHEMA = \"\"\"".len();
        let rest = &text[start..];
        let end = rest
            .find("\"\"\"")
            .expect("no closing \"\"\" for SCHEMA in db.py");
        let python_schema = &rest[..end];
        assert_eq!(
            SCHEMA, python_schema,
            "convert/sqlite.rs's SCHEMA const has drifted from db.py's"
        );
    }

    fn scratch(name: &str) -> std::path::PathBuf {
        let root = std::env::var_os("CARGO_TARGET_DIR")
            .map_or_else(std::env::temp_dir, std::path::PathBuf::from);
        let dir = root.join("convert-sqlite-unit").join(format!(
            "{name}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn create_writes_the_schema_and_finish_renames_into_place() {
        let dir = scratch("create-finish");
        let tmp = dir.join("x.db.tmp");
        let dest = dir.join("x.db");
        let w = TraceWriter::create(&tmp).unwrap();
        w.set_meta("trace_format", &4).unwrap();
        w.finish(&dest).unwrap();
        assert!(dest.is_file());
        assert!(!tmp.exists());
        let conn = Connection::open(&dest).unwrap();
        let v: String = conn
            .query_row(
                "SELECT value FROM meta WHERE key = 'trace_format'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(v, "4");
    }

    #[test]
    fn meta_values_are_compact_json() {
        let dir = scratch("compact-json");
        let w = TraceWriter::create(&dir.join("x.db.tmp")).unwrap();
        w.set_meta("argv", &vec!["a".to_owned(), "b".to_owned()])
            .unwrap();
        assert_eq!(w.meta_json("argv").unwrap(), "[\"a\",\"b\"]");
    }

    #[test]
    fn code_object_rows_and_events_round_trip() {
        let dir = scratch("round-trip");
        let w = TraceWriter::create(&dir.join("x.db.tmp")).unwrap();
        let code = w.insert_code_object("/w/a.rs", "main", 3).unwrap();
        let call = w
            .insert_event(1000, 1, "CALL", None, Some(code), Some(3), None, None)
            .unwrap();
        let frame = w.insert_frame(None, code, call, 0, 1).unwrap();
        let ret = w
            .insert_event(2000, 1, "RETURN", Some(frame), Some(code), None, None, None)
            .unwrap();
        w.close_frame(frame, ret, "return", None).unwrap();
        w.insert_fingerprint(1, "deadbeef", 2).unwrap();
        w.finish(&dir.join("x.db")).unwrap();

        let conn = Connection::open(dir.join("x.db")).unwrap();
        let (closed_by, ret_ev): (String, i64) = conn
            .query_row(
                "SELECT closed_by, return_event_id FROM frames WHERE id = ?1",
                [frame],
                |r| Ok((r.get(0)?, r.get(1)?)),
            )
            .unwrap();
        assert_eq!(closed_by, "return");
        assert_eq!(ret_ev, ret);
        let n_events: i64 = conn
            .query_row("SELECT COUNT(*) FROM events", [], |r| r.get(0))
            .unwrap();
        assert_eq!(n_events, 2);
    }
}
