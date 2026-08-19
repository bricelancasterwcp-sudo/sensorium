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
_EVENT_COLS = "id, ts_ns, thread_id, kind, frame_id, code_id, line, payload"


def _loads(s):
    return None if s is None else json.loads(s)


def _frame(row) -> Frame:
    return Frame(*row[:8], _loads(row[8]))


def _event(row) -> Event:
    return Event(*row[:7], _loads(row[7]))


class Trace:
    def __init__(self, conn, path: Path) -> None:
        self._c = conn
        self.path = path
        self._code_cache: dict[int, Code] | None = None

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
        q = f"SELECT {_EVENT_COLS} FROM events WHERE id > ?"
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
            f"SELECT {_EVENT_COLS} FROM events WHERE id = ?", (eid,)).fetchone()
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

    def fingerprints(self) -> dict[int, tuple[str, int]]:
        return {tid: (h, n) for tid, h, n in self._c.execute(
            "SELECT thread_id, hash, n_events FROM fingerprints")}

    def output_chunks(self) -> list[tuple[int, str, str]]:
        return list(self._c.execute(
            "SELECT after_event_id, stream, data FROM output ORDER BY id"))

    def main_thread_id(self) -> int | None:
        row = self._c.execute(
            "SELECT thread_id FROM events ORDER BY id LIMIT 1").fetchone()
        return None if row is None else row[0]

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
