"""Which activations of one run are stored, and which are only counted.

The first ``max_calls`` activations of each function are recorded in full.
Further activations of that function, and every activation once the trace
has hit its event or byte cap, are counted and not stored. A failure still
materializes the raising frame, so the exception stays in the trace.

``report`` is ``None`` unless at least one call was dropped. Callers write
that dict as trace meta only then, so a run that stayed inside the cap is
unchanged.
"""
from __future__ import annotations

import threading
from collections import deque

_FAILURE_WINDOW = 8


class Budget:
    """The cap decision for one ``Tracer``. ``writer`` supplies the counters."""

    def __init__(self, limits, writer) -> None:
        self.limits = limits
        self.writer = writer
        self._lock = threading.Lock()
        # code id -> [elided, file, qualname, firstlineno, kept, reason]
        self._hot: dict[int, list] = {}
        self._kept: dict[int, int] = {}
        self._hits: list[str] = []
        self._hitset: set[str] = set()
        self.failures_kept = 0
        self._recent: deque = deque(maxlen=_FAILURE_WINDOW)

    def slot(self, code_id: int):
        """The hot-function row, or ``None`` when this code is still stored."""
        return self._hot.get(code_id)

    def bump(self, slot) -> None:
        """One more elided activation of a function that is already hot."""
        with self._lock:
            self._drop(slot, slot[1], slot[2], slot[3])

    def should_elide(self, code_id: int, file: str, qual: str,
                     lineno: int) -> bool:
        """True when this activation must not be stored."""
        with self._lock:
            slot = self._hot.get(code_id)
            if slot is not None:
                self._drop(slot, file, qual, lineno)
                return True
            kept = self._kept.get(code_id, 0)
            events = self.writer.last_event_id
            nbytes = self.writer.bytes_estimate
            reasons = []
            if self.limits.max_calls and kept >= self.limits.max_calls:
                reasons.append("max_calls")
            if self.limits.max_events and events >= self.limits.max_events:
                reasons.append("max_events")
            if self.limits.max_bytes and nbytes >= self.limits.max_bytes:
                reasons.append("max_bytes")
            if not reasons:
                return False
            for reason in reasons:
                self._mark(reason)
            self._hot[code_id] = [1, file, qual, lineno, kept, reasons[0]]
            self._recent.append((file, qual, lineno))
            return True

    def note_kept(self, code_id: int, file: str, qual: str, lineno: int) -> None:
        """A call that was stored. Arms the fast path once the quota is full."""
        with self._lock:
            n = self._kept.get(code_id, 0) + 1
            self._kept[code_id] = n
            if (self.limits.max_calls and n >= self.limits.max_calls
                    and code_id not in self._hot):
                self._hot[code_id] = [0, file, qual, lineno, n, "max_calls"]

    def note_failure(self, code_id: int) -> bool:
        """A failure frame kept after it had been counted as elided.

        Returns True when the count moved, so the caller writes the skeleton
        once. A second walk of the same frame finds the count already spent.
        """
        with self._lock:
            slot = self._hot.get(code_id)
            if slot is None or slot[0] <= 0:
                return False
            slot[0] -= 1
            slot[4] += 1
            self.failures_kept += 1
            return True

    def report(self) -> dict | None:
        with self._lock:
            elided = sum(slot[0] for slot in self._hot.values())
            if elided <= 0:
                return None
            elisions = [
                {"file": slot[1], "qualname": slot[2], "firstlineno": slot[3],
                 "elided": slot[0], "kept": slot[4]}
                for slot in self._hot.values() if slot[0] > 0
            ]
            limits = {
                "max_events": self.limits.max_events,
                "max_bytes": self.limits.max_bytes,
                "max_calls": self.limits.max_calls,
                "hit": list(self._hits),
                "events_recorded": self.writer.last_event_id,
                "calls_elided": elided,
            }
            if self.failures_kept:
                limits["failures_kept"] = self.failures_kept
            out = {
                "trace_truncated": True,
                "trace_limits": limits,
                "elisions": elisions,
            }
            if self.failures_kept and self._recent:
                out["failure_context"] = [
                    {"file": file, "qualname": qual, "firstlineno": line}
                    for file, qual, line in self._recent
                ]
            return out

    def _drop(self, slot, file: str, qual: str, lineno: int) -> None:
        slot[0] += 1
        if slot[0] == 1:
            self._mark(slot[5])
        self._recent.append((file, qual, lineno))

    def _mark(self, name: str) -> None:
        if name not in self._hitset:
            self._hitset.add(name)
            self._hits.append(name)
