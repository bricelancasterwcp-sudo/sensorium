"""Batched, thread-safe writer for trace files. Buffers rows in memory and
flushes in one transaction per batch; on an unclean death, everything
already flushed is a valid partial trace."""
import json
import threading
from pathlib import Path

from sensorium.store import db


class TraceWriter:
    def __init__(self, path: Path, batch: int = 512) -> None:
        self.path = Path(path)
        self._conn = db.create_trace(self.path)
        self._lock = threading.Lock()
        self._batch = batch
        self._events: list[tuple] = []
        self._frames: list[tuple] = []
        self._closes: list[tuple] = []
        self._outputs: list[tuple] = []
        self._tasks: list[tuple] = []
        self._codes: dict[tuple, int] = {}
        self._new_codes: list[tuple] = []
        self._next_event = 1
        self._next_frame = 1

    @property
    def last_event_id(self) -> int:
        return self._next_event - 1

    def intern_code(self, file: str, qualname: str, firstlineno: int) -> int:
        key = (file, qualname, firstlineno)
        with self._lock:
            cid = self._codes.get(key)
            if cid is None:
                cid = len(self._codes) + 1
                self._codes[key] = cid
                self._new_codes.append((cid, file, qualname, firstlineno))
            return cid

    def add_event(self, ts_ns, thread_id, kind, frame_id, code_id, line,
                  payload: dict | None, task_id: int | None = None) -> int:
        p = (None if payload is None
             else json.dumps(payload, separators=(",", ":"), default=repr))
        with self._lock:
            eid = self._next_event
            self._next_event += 1
            self._events.append(
                (eid, ts_ns, thread_id, kind, frame_id, code_id, line, p,
                 task_id))
            if len(self._events) >= self._batch:
                self._flush_locked()
            return eid

    def add_task(self, task_id: int, name: str | None, thread_id: int) -> None:
        """One row per asyncio task, written when its serial is minted."""
        with self._lock:
            self._tasks.append((task_id, name, thread_id))

    def open_frame(self, parent_id, code_id, call_event_id, depth,
                   thread_id, kind: str = "function") -> int:
        with self._lock:
            fid = self._next_frame
            self._next_frame += 1
            self._frames.append(
                (fid, parent_id, code_id, call_event_id, depth, thread_id, kind))
            return fid

    def close_frame(self, frame_id, return_event_id=None, closed_by="return",
                    unwind_exc: dict | None = None) -> None:
        exc = (None if unwind_exc is None
               else json.dumps(unwind_exc, separators=(",", ":")))
        with self._lock:
            self._closes.append((return_event_id, closed_by, exc, frame_id))

    def add_output(self, after_event_id, stream, data) -> None:
        with self._lock:
            self._outputs.append((after_event_id, stream, data))

    def interned_files(self) -> list[str]:
        """Distinct source files this trace has interned code from.

        Read from the in-memory intern table rather than the database
        because callers need it during finalize, while codes may still be
        sitting unflushed in `_new_codes`.
        """
        with self._lock:
            return sorted({file for file, _qual, _line in self._codes})

    def set_meta(self, key, value) -> None:
        with self._lock:
            db.set_meta(self._conn, key, value)
            self._conn.commit()

    def write_fingerprint(self, thread_id, hexdigest, count) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO fingerprints "
                "(thread_id, hash, n_events) VALUES (?, ?, ?)",
                (thread_id, hexdigest, count))
            self._conn.commit()

    def write_task_fingerprints(self, rows) -> None:
        """Every task's row -- `(task_id, hexdigest, count)` -- in ONE
        transaction.

        One row per minted task serial; the name rides along from the
        `tasks` row so the multiset comparison can read (name, hash) from
        one table. A task whose name could not be read keeps NULL.

        The buffer is flushed FIRST because that `tasks` row may still be
        sitting in it: `INSERT ... SELECT` over a table that does not yet
        hold the row inserts nothing at all, silently, and the caller (the
        tracer's uninstall pass) has no way to tell. Under the CLI's
        batch=512 that is the ordinary case for any async program short
        enough not to have flushed on its own -- which is to say, most of
        them: every task fingerprint was dropped and `diff` saw a run with
        no tasks in it.

        The flush does not commit, because it does not need to: a
        connection sees its own uncommitted writes, so the SELECT below
        reads the `tasks` rows this flush just inserted. What that buys is
        the whole pass being one transaction -- one fsync for the run
        rather than two per task. This is written from `uninstall`, after
        the recorded program has already finished, so per-row commits
        charged their cost to a process that looked done. Measured on this
        box (ext4, 1,000 rows, best of five, three interleaved series):
        1.3-3.2 ms per task the old way, 4.6-5.4 us per task this way. End
        to end, recording a 2,000-task program went from 2.18 s to 0.35 s
        of wall clock.
        """
        rows = list(rows)
        if not rows:
            return
        with self._lock:
            self._flush_locked(commit=False)
            self._conn.executemany(
                "INSERT OR REPLACE INTO task_fingerprints "
                "(task_id, name, hash, n_events) "
                "SELECT ?, name, ?, ? FROM tasks WHERE id = ?",
                [(task_id, hexdigest, count, task_id)
                 for task_id, hexdigest, count in rows])
            self._conn.commit()

    def write_task_fingerprint(self, task_id, hexdigest, count) -> None:
        """One task's row. Kept as its own entry point -- callers with a
        single task read better for it -- and routed through the bulk path
        so there is one implementation of what a row means."""
        self.write_task_fingerprints([(task_id, hexdigest, count)])

    def _flush_locked(self, commit: bool = True) -> None:
        c = self._conn
        if self._new_codes:
            c.executemany("INSERT INTO code_objects VALUES (?, ?, ?, ?)",
                          self._new_codes)
            self._new_codes.clear()
        if self._frames:
            c.executemany(
                "INSERT INTO frames (id, parent_id, code_id, call_event_id, "
                "depth, thread_id, kind) VALUES (?, ?, ?, ?, ?, ?, ?)",
                self._frames)
            self._frames.clear()
        if self._events:
            c.executemany(
                "INSERT INTO events (id, ts_ns, thread_id, kind, frame_id, "
                "code_id, line, payload, task_id) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)", self._events)
            self._events.clear()
        if self._tasks:
            c.executemany(
                "INSERT INTO tasks (id, name, thread_id) VALUES (?, ?, ?)",
                self._tasks)
            self._tasks.clear()
        if self._closes:
            c.executemany(
                "UPDATE frames SET return_event_id = ?, closed_by = ?, "
                "unwind_exc = ? WHERE id = ?", self._closes)
            self._closes.clear()
        if self._outputs:
            c.executemany(
                "INSERT INTO output (after_event_id, stream, data) "
                "VALUES (?, ?, ?)", self._outputs)
            self._outputs.clear()
        # `commit=False` is for a caller that has more to write in the SAME
        # transaction (see `write_task_fingerprints`); every other caller
        # takes the default, because an unflushed batch left uncommitted is
        # a batch an unclean death loses.
        if commit:
            c.commit()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def close(self) -> None:
        with self._lock:
            self._flush_locked()
            self._conn.close()
