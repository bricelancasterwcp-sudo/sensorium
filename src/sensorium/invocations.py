"""The invocation log: one JSON line per `cli.main` return.

`cli.main` calls `record` once per invocation, after dispatch, with the
argv it was given and the exit status (and, for the three exception
classes it catches, the exception's class name) it is about to return.
The log exists to answer "was sensorium called, and how did it end" --
the census a future on-demand flag would otherwise be arguing from thin
air (finding §4) -- not to reconstruct the process, so a line carries
exactly `utc`, `argv`, `exit`, `error`: never the environment, never the
working directory.

Default on. Opt out for one process with `SENSORIUM_NO_INVOCATION_LOG=1`.
The log lives at `paths.trace_root() / "invocations.jsonl"`, a *sibling*
of `traces/` -- `runs` and `find_trace` only glob `traces/*.db`, so this
file is invisible to every trace lookup, by construction rather than by
filtering.

`record` never raises: a location it cannot write to (its directory
missing and uncreatable, e.g. a regular file sitting where a directory
belongs) prints one line to stderr and returns, exactly like a dropped
log line from any other best-effort logger -- a command's exit status is
never the invocation log's business.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sensorium import paths

_DISABLE_VAR = "SENSORIUM_NO_INVOCATION_LOG"


def path() -> Path:
    return paths.trace_root() / "invocations.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def record(argv: list[str], exit_status: int, error: str | None) -> None:
    """Append one JSON line to `path()`. Never raises."""
    if os.environ.get(_DISABLE_VAR):
        return
    line = {"utc": _utc_now(), "argv": list(argv), "exit": exit_status,
            "error": error}
    try:
        p = path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
    except OSError as e:
        print(f"sensorium: invocation log unwritable: {e}", file=sys.stderr)
