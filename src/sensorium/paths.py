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


def is_valid_run_id(run_id: str) -> bool:
    """Whether `run_id` names ONE file inside the trace store, and cannot
    escape it.

    A run id flows straight into `traces_dir() / f"{run_id}.db"`, whose parent
    is created with `parents=True`, so a caller-supplied `--run-id` of `../x`,
    `a/b` or `/tmp/x` would create directories and write a trace outside the
    store. Ids the tool mints itself (`new_run_id`) always pass; this guards the
    one place an id comes from outside. A valid id is a single path component:
    non-empty, not `.`/`..`, and equal to its own basename (no separators).
    """
    return (isinstance(run_id, str) and run_id not in ("", ".", "..")
            and run_id == Path(run_id).name)


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
