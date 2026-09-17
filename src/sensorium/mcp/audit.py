"""`mcp.jsonl`: what was asked of this server, and how it ended.

One JSON line per `tools/call`, per rejection and per cancel, in
`<store root>/mcp.jsonl` -- a sibling of `invocations.jsonl`, invisible
to every trace lookup for its reason: `runs` and `find_trace` glob
`traces/*.db`, and this file is not under `traces/`.

WHAT IT IS FOR. The census a future policy argument has to stand on
(§6.3) -- which tools a model reaches for, how often a call is refused
and why, how much output it takes to answer. So a rejection line carries
`reason` and `fields` as DATA (P16): one prose message cannot be
counted, and a census parsing English stops matching the first time the
wording improves.

WHAT IT IS NOT. Never the environment, never `cwd`, never the result
text. `bytes` says how much was shown and `truncated` whether that was
all of it; what was shown in full is the trace, which the tenant already
holds. Arguments pass the content rule first (D28): a model that types a
secret into `grep`'s pattern leaves the marker here, not the value. The
invocation log the child writes does NOT apply the rule to its argv --
an asymmetry older than this file, carried as debt, not fixed in passing.

ONE KNOB (D29). `SENSORIUM_NO_INVOCATION_LOG` disables this file too,
read through `invocations._log_disabled` rather than re-implemented: the
user has one word for "log nothing about my calls" and two readings of
it would eventually disagree. The server says so once on stderr at boot.
And nothing here raises: an unwritable location prints one line and
returns, exactly as `invocations.record` does -- a tool call's answer is
never the audit file's business.

This module records. `result.py` renders; the two never import each
other, and the server is what calls both.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sensorium import invocations, paths, redact_content
from sensorium.mcp.child import Outcome


def path() -> Path:
    return paths.trace_root() / "mcp.jsonl"


def disabled() -> bool:
    """The invocation log's knob, not a second one of our own (D29)."""
    return invocations._log_disabled()


def scrub(value):
    """`value` with the content rule applied to every string in it.

    All the way down, not the top level only: `focus`, `include` and
    `exclude` are arrays, and a secret typed into one of them would
    otherwise reach the file verbatim. Tuples come back as lists, which
    is what JSON has; anything that is not a string, a sequence or a
    mapping passes through untouched.
    """
    if isinstance(value, str):
        return redact_content.content(value)[0]
    if isinstance(value, (list, tuple)):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items()}
    return value


def _write(line: dict) -> None:
    """Append one line. Never raises; writes nothing when disabled."""
    if disabled():
        return
    try:
        p = path()
        # 0700 on the root and 0600 on the file: `invocations.record`'s
        # two-half rule, for its reason -- this file names every call and
        # its arguments, and `p.open("a")` would create it 0666-under-the-
        # umask. An EXISTING directory or file keeps its own mode.
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, separators=(",", ":"),
                               ensure_ascii=False) + "\n")
    except (OSError, RuntimeError) as e:
        # OSError: the usual "can't write there". RuntimeError: `path()`
        # -> `trace_root()` -> `Path.home()` raises THAT, not OSError,
        # when no home can be determined and SENSORIUM_DIR is unset.
        print(f"sensorium mcp: audit: {e}", file=sys.stderr)


def record_call(tool: str, arguments: dict, o: Outcome, nbytes: int,
                truncated: bool) -> None:
    """One answered call. `bytes` is the length of the FINAL text."""
    line = {"utc": invocations._utc_now(), "tool": tool,
            "arguments": scrub(arguments), "exit": o.exit,
            "bytes": nbytes, "truncated": truncated, "ms": o.ms}
    if o.timed_out:
        line["timeout"] = True
    if o.exit is None and not o.cancelled:
        # Why there was no status -- the timeout's sentence or the spawn
        # error. A cancel needs none: `record_cancel` says so in a field.
        line["cause"] = o.cause
    _write(line)


def record_rejection(tool: str | None, code: int, reason: str, message: str,
                     fields: tuple[str, ...] = ()) -> None:
    """A call that was refused (P16). `tool` is None for a malformed
    request that named none; `fields` is written only when there are
    fields to name, an empty list reading to a census as "some field was
    named", which is not what happened.

    Tool name, field names and message are model-typed text like any
    argument, so they pass the content rule too: a secret misspelt into a
    field name must not survive here because the call was REFUSED.
    """
    rejected: dict = {"code": code, "reason": reason}
    if fields:
        rejected["fields"] = scrub(list(fields))
    rejected["message"] = scrub(message)
    _write({"utc": invocations._utc_now(), "tool": scrub(tool),
            "rejected": rejected})


def record_cancel(tool: str, arguments: dict, queued: bool,
                  ms: int | None) -> None:
    """A call the client cancelled. `queued` says whether it had started:
    a cancel that landed while the request was still in the queue never
    spawned anything, and `ms` is None for it."""
    _write({"utc": invocations._utc_now(), "tool": tool,
            "arguments": scrub(arguments), "cancelled": True,
            "queued": queued, "ms": ms})
