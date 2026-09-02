"""Read-side access to trace files."""
import json
from collections import Counter
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
    task_id: int | None = None   # None when no asyncio task is current
                                 # (before/after the loop, AND inside loop
                                 # callbacks), or format 1


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
    kind: str = "function"      # formats <= 2 recorded no kind: framed code there is a function


@dataclass(frozen=True)
class FrameState:
    """How a frame ended, DERIVED from evidence (spec D2): returned | raised |
    cancelled | abandoned | thrown | suspended | open. `line` is the parked
    line for suspended/cancelled/abandoned/thrown; `exc` the unwind cause."""
    state: str
    line: int | None
    exc: dict | None


_FRAME_COLS_V2 = ("id, parent_id, code_id, call_event_id, return_event_id, "
                  "depth, thread_id, closed_by, unwind_exc")
_FRAME_COLS_V3 = _FRAME_COLS_V2 + ", kind"
_EVENT_COLS_V1 = "id, ts_ns, thread_id, kind, frame_id, code_id, line, payload"
_EVENT_COLS_V2 = _EVENT_COLS_V1 + ", task_id"


def _loads(s):
    return None if s is None else json.loads(s)


def _frame(row) -> Frame:
    return Frame(*row[:8], _loads(row[8]), *row[9:])


def _event(row) -> Event:
    # 8 columns on a format-1 trace, 9 on format 2; task_id defaults to None.
    return Event(*row[:7], _loads(row[7]), *row[8:])


class Trace:
    def __init__(self, conn, path: Path) -> None:
        self._c = conn
        self.path = path
        self._code_cache: dict[int, Code] | None = None
        self._child_ids: dict[int | None, list[int]] | None = None
        cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
        # Decided from the table, not from meta: the column is the fact.
        self._ecols = _EVENT_COLS_V2 if "task_id" in cols else _EVENT_COLS_V1
        fcols = {r[1] for r in conn.execute("PRAGMA table_info(frames)")}
        self._fcols = _FRAME_COLS_V3 if "kind" in fcols else _FRAME_COLS_V2
        self._has_tasks = bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone())
        self._has_task_fps = bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='task_fingerprints'").fetchone())

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
        q = f"SELECT {self._fcols} FROM frames"
        params: tuple = ()
        if code_id is not None:
            q += " WHERE code_id = ?"
            params = (code_id,)
        return [_frame(r) for r in self._c.execute(q + " ORDER BY id", params)]

    def frame(self, fid: int) -> Frame | None:
        row = self._c.execute(
            f"SELECT {self._fcols} FROM frames WHERE id = ?", (fid,)).fetchone()
        return None if row is None else _frame(row)

    def _parent_map(self) -> dict[int | None, list[int]]:
        """parent_id -> [frame ids], built once per Trace from one ordered
        pass over (id, parent_id). `children()` was a full `frames` scan per
        call (no index on parent_id), so a tree walk was O(frames^2)."""
        if self._child_ids is None:
            m: dict[int | None, list[int]] = {}
            for fid, pid in self._c.execute(
                    "SELECT id, parent_id FROM frames ORDER BY id"):
                m.setdefault(pid, []).append(fid)
            self._child_ids = m
        return self._child_ids

    def children(self, fid: int) -> list[Frame]:
        return [self.frame(i) for i in self._parent_map().get(fid, [])]

    def roots(self) -> list[Frame]:
        return [self.frame(i) for i in self._parent_map().get(None, [])]

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

    def _unframed_sql(self, code_id: int | None = None) -> str:
        # NOT IN over frames.call_event_id (NOT NULL by schema, so NOT IN is
        # exact), not a LEFT JOIN: the join had no index to use and scanned
        # `frames` once per CALL row -- 53.9 s on a 93k-event trace, 0.011 s
        # this way, row-identical (measured 2026-09-01).
        q = (f"SELECT {self._ecols} FROM events WHERE kind = 'CALL' "
             "AND code_id IS NOT NULL "
             "AND id NOT IN (SELECT call_event_id FROM frames)")
        if code_id is not None:
            q += " AND code_id = ?"
        return q + " ORDER BY id"

    def unframed_calls(self, code_id: int | None = None) -> list[Event]:
        """CALL events no frame was opened for (generators, coroutines).

        Decided by the frames table, deliberately not the `unframed`
        payload key: the key is format 2, the table answers for every format,
        and 'recorded but not framed' must be the same fact on both."""
        params: tuple = () if code_id is None else (code_id,)
        return [_event(r) for r in self._c.execute(self._unframed_sql(code_id),
                                                   params)]

    def call_counts(self) -> dict[int, int]:
        """code_id -> CALL events. Counts activations, framed or not."""
        return dict(self._c.execute(
            "SELECT code_id, COUNT(*) FROM events WHERE kind = 'CALL' "
            "AND code_id IS NOT NULL GROUP BY code_id"))

    def fingerprints(self) -> dict[int, tuple[str, int]]:
        return {tid: (h, n) for tid, h, n in self._c.execute(
            "SELECT thread_id, hash, n_events FROM fingerprints")}

    @property
    def fingerprint_basis(self) -> str:
        """What a per-thread fingerprint row covers: "per-task" (plan 2b --
        only events outside any asyncio task; tasks have their own rows) or
        "per-thread" (every causal event on the thread; the only definition
        before the marker existed, so absence means exactly that)."""
        return self.meta.get("fingerprint_basis") or "per-thread"

    @property
    def lang(self) -> str:
        """`meta["lang"]`; a trace without it predates the declaration and
        was written by the Python recorder (nothing else existed)."""
        return self.meta.get("lang") or "python"

    @property
    def recorder(self) -> str:
        r = self.meta.get("recorder")
        return r or f"sensorium <=0.4.0 (format {self.format}, undeclared)"

    @property
    def capabilities(self) -> dict:
        """What the recorder declared it produces. A Python trace with no
        declaration is read as full: that recorder had every capability and,
        before format 4, no way to say so (a hand-built or still-recording
        format-4 Python trace is the same case -- the open-time refusal
        guarantees a FINALIZED format-4 trace always carries the key). A
        non-Python trace with no declaration declares nothing.

        A declaration that is PRESENT but not a dict -- a list, a string, a
        null -- declared nothing usable, whatever the language: reading it
        as full would turn a recorder's malformed claim into ten
        capabilities it never asserted, and `dict()` on it would raise.
        Absence and unusability are different facts and only absence on a
        Python trace means "predates the declaration"."""
        caps = self.meta.get("capabilities")
        if isinstance(caps, dict):
            return dict(caps)
        if "capabilities" in self.meta:
            return {}                      # present but not a usable dict
        if self.lang == "python":
            # Local: `boot` pulls runpy/subprocess/tracer, and every
            # other importer in the tree defers it for the same reason.
            from sensorium.record.boot import CAPABILITIES
            return dict(CAPABILITIES)
        return {}

    def declares(self, cap: str) -> bool | None:
        """True/False = the recorder declared `cap`; None = nothing was
        declared and the trace is the Python recorder's (undeclared = full,
        the only recorder that existed). A trace whose dict omits a
        capability declared it False; a non-Python trace with no dict, and
        ANY trace whose `capabilities` is present but not a dict, declares
        everything False -- only a missing key can mean "predates"."""
        if "capabilities" not in self.meta:
            return None if self.lang == "python" else False
        return bool(self.capabilities.get(cap, False))

    def dropped_writes(self) -> int:
        """Trace writes known lost: the Python recorder's `late_writes`
        (a lower bound), or a Rust recorder's per-thread `records_dropped`
        summed over the threads that reported a number."""
        m = self.meta
        if "late_writes" in m:
            return int(m["late_writes"] or 0)
        rd = m.get("records_dropped")
        if isinstance(rd, dict):
            return sum(int(v) for v in rd.values() if v is not None)
        return 0

    def task_fingerprints(self) -> dict[int, tuple[str | None, str, int]]:
        if not self._has_task_fps:
            return {}
        return {tid: (name, h, n) for tid, name, h, n in self._c.execute(
            "SELECT task_id, name, hash, n_events FROM task_fingerprints")}

    def task_shapes(self) -> "Counter[tuple[str | None, str]]":
        """The multiset of (name, hash) over every task fingerprint: two
        tasks doing identical work under one name count twice, which is the
        comparison -- the same task shapes ran, the same number of times."""
        return Counter((name, h) for name, h, _n
                       in self.task_fingerprints().values())

    def task_stream(self, task_id: int) -> list[tuple[str, str, str, int]]:
        marks = ",".join("?" * len(CAUSAL_KINDS))
        out = []
        for eid, cid, kind in self._c.execute(
                f"SELECT id, code_id, kind FROM events "
                f"WHERE task_id = ? AND kind IN ({marks}) ORDER BY id",
                (task_id, *CAUSAL_KINDS)):
            c = self.code(cid)
            out.append((c.file, c.qualname, kind, eid))
        return out

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
        # Under the per-task basis a thread's stream is what its fingerprint
        # covers: the events that ran in no task. Under the per-thread basis
        # (every trace before the marker) it is every causal event, task
        # events included -- the definition those fingerprints were made by.
        narrow = ("AND task_id IS NULL "
                  if self.fingerprint_basis == "per-task" else "")
        out = []
        for eid, cid, kind in self._c.execute(
                f"SELECT id, code_id, kind FROM events "
                f"WHERE thread_id = ? {narrow}AND kind IN ({marks}) ORDER BY id",
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
            f"SELECT {self._fcols} FROM frames WHERE call_event_id = ?",
            (eid,)).fetchone()
        return None if row is None else _frame(row)

    def suspensions(self, fid: int) -> list[Event]:
        return self.events(kind=("YIELD", "RESUME"), frame_id=fid)

    def frame_state(self, f: Frame) -> FrameState:
        """Spec D2. Evidence only: closed_by, unwind_exc, and the frame's last
        YIELD/RESUME row. 'cancelled'/'abandoned'/'thrown' need the serial of
        the exception thrown in at the last RESUME to equal the unwind's --
        a type match alone could be a different exception raised inside."""
        last = self._c.execute(
            "SELECT kind, line, payload FROM events WHERE frame_id = ? "
            "AND kind IN ('YIELD', 'RESUME') ORDER BY id DESC LIMIT 1",
            (f.id,)).fetchone()
        lkind, lline, lpayload = (None, None, None) if last is None else (
            last[0], last[1], _loads(last[2]))
        if f.closed_by == "return":
            return FrameState("returned", None, None)
        if f.closed_by == "unwind":
            thrown = (lpayload or {}).get("thrown") if lkind == "RESUME" else None
            ts = thrown.get("serial") if thrown else None
            us = (f.unwind_exc or {}).get("serial")
            if thrown is not None and ts is not None and ts == us:
                t = thrown.get("type")
                state = ("cancelled" if t == "CancelledError"
                         else "abandoned" if t == "GeneratorExit" else "thrown")
                return FrameState(state, lline, f.unwind_exc)
            return FrameState("raised", None, f.unwind_exc)
        if lkind == "YIELD":
            return FrameState("suspended", lline, None)
        return FrameState("open", None, None)
