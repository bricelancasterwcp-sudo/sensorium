"""Read-side access to trace files."""
import json
from dataclasses import dataclass
from pathlib import Path

from sensorium.record.fingerprint import CAUSAL_KINDS
from sensorium.store import db


@dataclass(frozen=True)
class Code:
    id: int
    file: str
    qualname: str
    firstlineno: int


@dataclass(frozen=True)
class Event:
    id: int
    ts_ns: int
    thread_id: int
    kind: str
    frame_id: int | None
    code_id: int | None
    line: int | None
    payload: dict | None
    task_id: int | None = None   # None outside a running loop, or format 1


@dataclass(frozen=True)
class Task:
    id: int
    name: str | None         # None when the name could not be read
    thread_id: int


@dataclass(frozen=True)
class Frame:
    id: int
    parent_id: int | None
    code_id: int
    call_event_id: int
    return_event_id: int | None
    depth: int
    thread_id: int
    closed_by: str | None
    unwind_exc: dict | None


_FRAME_COLS = ("id, parent_id, code_id, call_event_id, return_event_id, "
               "depth, thread_id, closed_by, unwind_exc")
_EVENT_COLS_V1 = "id, ts_ns, thread_id, kind, frame_id, code_id, line, payload"
_EVENT_COLS_V2 = _EVENT_COLS_V1 + ", task_id"


def _loads(s):
    return None if s is None else json.loads(s)


def _frame(row) -> Frame:
    return Frame(*row[:8], _loads(row[8]))


def _event(row) -> Event:
    # 8 columns on a format-1 trace, 9 on format 2; task_id defaults to None.
    return Event(*row[:7], _loads(row[7]), *row[8:])


class Trace:
    def __init__(self, conn, path: Path) -> None:
        self._c = conn
        self.path = path
        self._code_cache: dict[int, Code] | None = None
        cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
        # Decided from the table, not from meta: the column is the fact.
        self._ecols = _EVENT_COLS_V2 if "task_id" in cols else _EVENT_COLS_V1
        self._has_tasks = bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone())

    @classmethod
    def open(cls, path: Path) -> "Trace":
        return cls(db.open_trace(path), Path(path))

    @property
    def meta(self) -> dict:
        return db.all_meta(self._c)

    def codes(self) -> list[Code]:
        if self._code_cache is None:
            self._code_cache = {r[0]: Code(*r) for r in self._c.execute(
                "SELECT id, file, qualname, firstlineno FROM code_objects")}
        return list(self._code_cache.values())

    def code(self, code_id: int) -> Code:
        self.codes()
        return self._code_cache[code_id]

    def events(self, kind=None, code_id=None, frame_id=None, after=0,
               limit=None) -> list[Event]:
        q = f"SELECT {self._ecols} FROM events WHERE id > ?"
        params: list = [after]
        if kind is not None:
            kinds = (kind,) if isinstance(kind, str) else tuple(kind)
            q += f" AND kind IN ({','.join('?' * len(kinds))})"
            params += list(kinds)
        if code_id is not None:
            q += " AND code_id = ?"
            params.append(code_id)
        if frame_id is not None:
            q += " AND frame_id = ?"
            params.append(frame_id)
        q += " ORDER BY id"
        if limit is not None:
            q += " LIMIT ?"
            params.append(limit)
        return [_event(r) for r in self._c.execute(q, params)]

    def event(self, eid: int) -> Event | None:
        row = self._c.execute(
            f"SELECT {self._ecols} FROM events WHERE id = ?", (eid,)).fetchone()
        return None if row is None else _event(row)

    def frames(self, code_id=None) -> list[Frame]:
        q = f"SELECT {_FRAME_COLS} FROM frames"
        params: tuple = ()
        if code_id is not None:
            q += " WHERE code_id = ?"
            params = (code_id,)
        return [_frame(r) for r in self._c.execute(q + " ORDER BY id", params)]

    def frame(self, fid: int) -> Frame | None:
        row = self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE id = ?", (fid,)).fetchone()
        return None if row is None else _frame(row)

    def children(self, fid: int) -> list[Frame]:
        return [_frame(r) for r in self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE parent_id = ? "
            "ORDER BY id", (fid,))]

    def roots(self) -> list[Frame]:
        return [_frame(r) for r in self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE parent_id IS NULL "
            "ORDER BY id")]

    def frame_events(self, fid: int) -> list[Event]:
        return self.events(frame_id=fid)

    def counts(self) -> dict[str, int]:
        return dict(self._c.execute(
            "SELECT kind, COUNT(*) FROM events GROUP BY kind"))

    @property
    def format(self) -> int:
        """`meta["trace_format"]`; a trace without the key predates it (1)."""
        return db.get_meta(self._c, "trace_format", 1)

    def parentage_basis(self) -> str:
        """"derived" (format 2+: parent = the caller frame, verified by code
        identity) or "assumed" (format 1: parent = the last frame opened on
        the thread, which is a guess that async resumption, generators and
        C-level callbacks all break). Query output labels the latter."""
        return "derived" if self.format >= 2 else "assumed"

    def tasks(self) -> list[Task]:
        if not self._has_tasks:
            return []
        return [Task(*r) for r in self._c.execute(
            "SELECT id, name, thread_id FROM tasks ORDER BY id")]

    def task(self, task_id: int) -> Task | None:
        if not self._has_tasks:
            return None
        row = self._c.execute(
            "SELECT id, name, thread_id FROM tasks WHERE id = ?",
            (task_id,)).fetchone()
        return None if row is None else Task(*row)

    def unframed_calls(self, code_id: int | None = None) -> list[Event]:
        """CALL events no frame was opened for (generators, coroutines).

        A join on frames.call_event_id, deliberately not the `unframed`
        payload key: the key is format 2, the join answers for every format,
        and 'recorded but not framed' must be the same fact on both."""
        q = (f"SELECT {', '.join('e.' + c.strip() for c in self._ecols.split(','))} "
             "FROM events e LEFT JOIN frames f ON f.call_event_id = e.id "
             "WHERE e.kind = 'CALL' AND f.id IS NULL AND e.code_id IS NOT NULL")
        params: tuple = ()
        if code_id is not None:
            q += " AND e.code_id = ?"
            params = (code_id,)
        return [_event(r) for r in self._c.execute(q + " ORDER BY e.id", params)]

    def call_counts(self) -> dict[int, int]:
        """code_id -> CALL events. Counts activations, framed or not."""
        return dict(self._c.execute(
            "SELECT code_id, COUNT(*) FROM events WHERE kind = 'CALL' "
            "AND code_id IS NOT NULL GROUP BY code_id"))

    def fingerprints(self) -> dict[int, tuple[str, int]]:
        return {tid: (h, n) for tid, h, n in self._c.execute(
            "SELECT thread_id, hash, n_events FROM fingerprints")}

    def output_chunks(self) -> list[tuple[int, str, str]]:
        return list(self._c.execute(
            "SELECT after_event_id, stream, data FROM output ORDER BY id"))

    def main_thread_id(self) -> int | None:
        """The thread `run_target` was invoked from -- for the ordinary
        `sensorium run` CLI entry point, the process's actual main thread.

        Prefers `meta["main_thread_ident"]`, recorded once at boot time
        independent of event ordering. Falls back to "the thread of
        whichever event happened to get id 1" only for traces that predate
        that key: under `--focus`/`--window` filtering, or ordinary
        scheduling jitter in a program that starts a worker early, a
        worker thread's first *recorded* event can land before the main
        thread's own first traced event, which makes that heuristic
        silently name the wrong thread on exactly the traces where it
        matters most. Callers that need to know which case they got --
        e.g. before asserting "the main thread" rather than a caveated
        guess -- must call `main_thread_basis()` too.
        """
        recorded = db.get_meta(self._c, "main_thread_ident")
        if recorded is not None:
            return recorded
        row = self._c.execute(
            "SELECT thread_id FROM events ORDER BY id LIMIT 1").fetchone()
        return None if row is None else row[0]

    def main_thread_basis(self) -> str | None:
        """How `main_thread_id()` got its answer: `"recorded"` (from
        `meta["main_thread_ident"]`, exact), `"inferred"` (the event-id-1
        fallback, a guess), or `None` (no events and no recorded key, i.e.
        `main_thread_id()` itself returned `None`)."""
        if db.get_meta(self._c, "main_thread_ident") is not None:
            return "recorded"
        return "inferred" if self.main_thread_id() is not None else None

    def causal_stream(self, thread_id=None) -> list[tuple[str, str, str, int]]:
        tid = thread_id if thread_id is not None else self.main_thread_id()
        marks = ",".join("?" * len(CAUSAL_KINDS))
        out = []
        for eid, cid, kind in self._c.execute(
                f"SELECT id, code_id, kind FROM events "
                f"WHERE thread_id = ? AND kind IN ({marks}) ORDER BY id",
                (tid, *CAUSAL_KINDS)):
            c = self.code(cid)
            out.append((c.file, c.qualname, kind, eid))
        return out

    def frame_containing(self, eid: int) -> Frame | None:
        ev = self.event(eid)
        if ev is None:
            return None
        if ev.frame_id is not None:
            return self.frame(ev.frame_id)
        row = self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE call_event_id = ?",
            (eid,)).fetchone()
        return None if row is None else _frame(row)
