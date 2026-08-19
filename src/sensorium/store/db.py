"""Trace file creation, opening, and run-metadata access."""
import json
import sqlite3
from pathlib import Path

TRACE_FORMAT = 1

SCHEMA = """
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
  unwind_exc TEXT
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts_ns INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  frame_id INTEGER,
  code_id INTEGER,
  line INTEGER,
  payload TEXT
);
CREATE TABLE output (
  id INTEGER PRIMARY KEY,
  after_event_id INTEGER NOT NULL,
  stream TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE fingerprints (
  thread_id INTEGER PRIMARY KEY,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
CREATE INDEX idx_events_code ON events(code_id);
CREATE INDEX idx_events_frame ON events(frame_id);
CREATE INDEX idx_events_kind ON events(kind);
CREATE INDEX idx_frames_code ON frames(code_id);
"""


def create_trace(path: Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # The tracer flushes on whichever thread fills the batch, so the write
    # connection outlives its creating thread. TraceWriter serialises every
    # access under its own lock, which is the invariant check_same_thread
    # approximates. (open_trace stays checked: the read path is single-threaded.)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    set_meta(conn, "trace_format", TRACE_FORMAT)
    conn.commit()
    return conn


def open_trace(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no trace at {path}")
    return sqlite3.connect(path)


def set_meta(conn: sqlite3.Connection, key: str, value) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, json.dumps(value, separators=(",", ":"))),
    )


def get_meta(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return default if row is None else json.loads(row[0])


def all_meta(conn: sqlite3.Connection) -> dict:
    return {k: json.loads(v)
            for k, v in conn.execute("SELECT key, value FROM meta")}
