"""Trace directory location, run ids, and run-reference resolution."""
import os
import time
import uuid
from pathlib import Path


class TraceLookupError(Exception):
    pass


def trace_root() -> Path:
    return Path(os.environ.get("SENSORIUM_DIR") or Path.home() / ".sensorium")


def traces_dir() -> Path:
    d = trace_root() / "traces"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def find_trace(ref: str) -> Path:
    files = sorted(traces_dir().glob("*.db"))
    if not files:
        raise TraceLookupError("no traces recorded yet")
    if ref == "last":
        return max(files, key=lambda p: p.stat().st_mtime)
    hits = [p for p in files if p.stem.startswith(ref)]
    if not hits:
        raise TraceLookupError(f"no trace matches {ref!r}")
    if len(hits) > 1:
        names = ", ".join(p.stem for p in hits)
        raise TraceLookupError(f"{ref!r} is ambiguous: {names}")
    return hits[0]
