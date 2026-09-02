"""Trace file creation, opening, and run-metadata access."""
import json
import sqlite3
from pathlib import Path

TRACE_FORMAT = 4

# Keys a finalized format-4 trace MUST carry (spec §5.1). Every reader
# defaults these when absent; on a trace that claims `incomplete = False`
# that default would print as a measured zero, so absence is refused here,
# once, instead of guarded at every `.get(key, 0)`.
REQUIRED_META = ("run_id", "argv", "cwd", "env_hash", "start_ts", "end_ts",
                 "exit_status", "main_thread_ident", "fingerprint_basis",
                 "truncated_count", "source_hashes",
                 "recorder", "lang", "capabilities")
# Witness keys, required only when the recorder declares the capability
# that produces them. A capability declared False means "not witnessed",
# which every reader prints as such -- never as zero, never as "predates".
WITNESS_KEYS = {"threads": ("threads_started", "live_threads"),
                "children": ("children", "spawn_syscalls", "audit_errors"),
                "stdin": ("stdin_consumed",)}


class TraceFormatError(Exception):
    """A trace this sensorium must not read: written by a NEWER sensorium,
    or a format-4 trace that claims to be finalized without the keys the
    format requires.

    `trace_format` is stamped at creation; a higher value means the file's
    layout may differ from what these queries assume. A trace with no
    `trace_format` at all predates the key and is read as format 1. Format
    2 (async attribution) added events.task_id, the tasks table and
    CALL-payload keys. Format 3 (inspectable coroutines) added frames.kind,
    the YIELD/RESUME event kinds, and task_fingerprints. Format 4 (the
    trace-format contract, docs/TRACE-FORMAT.md) adds no column: it makes
    `recorder`, `lang` and `capabilities` required meta, and requires the
    finalize keys above on any trace that says `incomplete = False`, so a
    second recorder can never render an absent record as a zero.
    """

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


def missing_required(conn: sqlite3.Connection) -> list[str]:
    """Required keys absent from a trace that claims to be finalized, in
    a stable order; [] when nothing is missing or the claim is not made.

    A `capabilities` that is present but not a dict counts as absent. This
    is a validation boundary for a recorder nobody here wrote: a list, a
    string or a null is not a declaration this reader can act on, and
    reporting it by name is the whole point of the mechanism. Reading it
    anyway would raise AttributeError out of `open_trace`, which the CLI
    does not catch, or -- for null -- pass silently and be rendered
    downstream as the full Python capability set.
    """
    if get_meta(conn, "incomplete") is not False:
        return []
    present = {k for (k,) in conn.execute("SELECT key FROM meta")}
    missing = [k for k in REQUIRED_META if k not in present]
    caps = get_meta(conn, "capabilities")
    if not isinstance(caps, dict):
        if "capabilities" not in missing:
            missing.append("capabilities")
        caps = {}
    for cap, keys in WITNESS_KEYS.items():
        if caps.get(cap):
            missing += [k for k in keys if k not in present]
    return missing


def open_trace(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no trace at {path}")
    conn = sqlite3.connect(path)
    fmt = get_meta(conn, "trace_format")
    if fmt is not None and fmt > TRACE_FORMAT:
        conn.close()
        raise TraceFormatError(
            f"{path} is trace format {fmt}, newer than this sensorium reads "
            f"(up to {TRACE_FORMAT}); upgrade sensorium to open it")
    if fmt is not None and fmt >= 4:
        missing = missing_required(conn)
        if missing:
            who = get_meta(conn, "recorder")
            if not isinstance(who, str) or not who:
                who = "an unnamed recorder"     # absent, null, or not a name
            conn.close()
            raise TraceFormatError(
                f"{path} claims to be finalized (incomplete = false) but "
                f"lacks required meta {', '.join(missing)} -- written by "
                f"{who}; format 4 refuses rather than read those as zero")
    return conn


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
