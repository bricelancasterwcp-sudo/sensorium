"""`mcp.jsonl`: one line per call, one per rejection, one per cancel.

The audit file is the census a future policy argument has to stand on
(§6.3), so what these tests pin is the SHAPE of a line -- which keys,
under which conditions, in which order -- rather than that something was
written. Key order is checked against the raw text, not the parsed dict:
`json.loads` sorts nothing, but a reader grepping the file reads bytes,
and a line whose keys moved is a line whose `grep -o '"reason":"[^"]*"'`
census stops matching.

The file is a sibling of `invocations.jsonl` and shares its two rules,
which is why they are tested here again rather than assumed: the store
root is created `0700`, the file `0600`, and a location that cannot be
written to prints one line and returns -- an audit that raised would
turn a logging failure into a failed tool call.

PRE-REGISTERED MUTATIONS (task 4, step 6), each with the test that
catches it:

* `scrub` applies the content rule to top-level strings only (no
  recursion into lists or dicts) ->
  `test_arguments_pass_the_content_rule`. `refocus --focus` and
  `record --focus` are arrays, and a secret typed into one would reach
  the file verbatim.
* the audit file is opened `0o644` instead of `0o600` ->
  `test_record_call_writes_one_line_with_the_fields_and_0600`. The file
  names every call and its (redacted) arguments; world-readable is the
  wrong default for it, exactly as for the invocation log.
* `record_rejection` scrubs nothing (the content rule on `arguments`
  only) -> `test_rejection_lines_by_reason`'s last case. A field NAME is
  model-typed text too, and a secret misspelt into one would survive in
  the file precisely because the call carrying it was refused.
"""
import json
import os
import stat

from sensorium import invocations
from sensorium.mcp import audit
from sensorium.mcp.child import Outcome

#: Long enough for the content rule's `sk-` row, which needs 20+ chars of
#: `[A-Za-z0-9_-]` after the prefix before it will fire at all.
SECRET = "sk-" + "A" * 33


def _store(tmp_path, monkeypatch):
    """A store root that does not exist yet: `record_*` is the hand that
    creates it, which is the half of the mode rule nothing else covers."""
    root = tmp_path / "sdir"
    monkeypatch.setenv("SENSORIUM_DIR", str(root))
    monkeypatch.delenv("SENSORIUM_NO_INVOCATION_LOG", raising=False)
    return root


def _lines(root):
    return [json.loads(ln) for ln in (root / "mcp.jsonl").read_text()
            .splitlines() if ln]


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def _o(status, cause=None, ms=84, **kw):
    return Outcome(exit=status, stdout="", stderr="", cause=cause, ms=ms, **kw)


# -- the call line (D27) ---------------------------------------------------
def test_record_call_writes_one_line_with_the_fields_and_0600(tmp_path,
                                                              monkeypatch):
    root = _store(tmp_path, monkeypatch)
    timed_out = "timed out after 600 s (server flag --timeout / --run-timeout)"

    audit.record_call("grep", {"run": "last", "pattern": "x"},
                      _o(1), 4120, False)
    audit.record_call("record", {"command": ["p.py"]},
                      _o(None, timed_out, ms=600_012, timed_out=True),
                      0, False)
    audit.record_call("record", {"command": ["p.py"]},
                      _o(None, "cancelled", ms=3001, cancelled=True),
                      0, True)

    assert audit.path() == root / "mcp.jsonl"
    assert _mode(root) == 0o700
    assert _mode(root / "mcp.jsonl") == 0o600
    called, timeout, cancelled = _lines(root)

    assert list(called) == ["utc", "tool", "arguments", "exit", "bytes",
                            "truncated", "ms"]
    assert called["tool"] == "grep"
    assert called["arguments"] == {"run": "last", "pattern": "x"}
    assert (called["exit"], called["bytes"], called["truncated"],
            called["ms"]) == (1, 4120, False, 84)
    assert called["utc"].endswith("Z")

    # no exit: `timeout` says which way it ended, `cause` says why.
    assert list(timeout) == ["utc", "tool", "arguments", "exit", "bytes",
                             "truncated", "ms", "timeout", "cause"]
    assert timeout["exit"] is None
    assert timeout["timeout"] is True
    assert timeout["cause"] == timed_out
    assert timeout["ms"] == 600_012

    # ...but a cancel's cause is the word "cancelled", which the
    # `cancelled` line already says: no `cause`, and no `timeout`.
    assert list(cancelled) == ["utc", "tool", "arguments", "exit", "bytes",
                               "truncated", "ms"]
    assert cancelled["truncated"] is True


def test_arguments_pass_the_content_rule(tmp_path, monkeypatch):
    """D28, all the way down: a secret in a string, in a list and in a
    nested dict all leave the marker, and nothing that is not a string is
    touched."""
    root = _store(tmp_path, monkeypatch)

    audit.record_call("grep",
                      {"pattern": SECRET,
                       "focus": ["x", SECRET],
                       "nested": {"expr": f"token={SECRET}"},
                       "limit": 5, "misses": True, "none": None},
                      _o(0), 10, False)

    raw = (root / "mcp.jsonl").read_text()
    assert SECRET not in raw
    assert "<redacted>" in raw
    args = _lines(root)[0]["arguments"]
    assert args["pattern"] == "<redacted>"
    assert args["focus"] == ["x", "<redacted>"]
    assert args["nested"] == {"expr": "token=<redacted>"}
    assert args["limit"] == 5 and args["misses"] is True
    assert args["none"] is None
    # the pure function, directly: a tuple comes back as a list, because
    # that is what JSON has.
    assert audit.scrub(("x", SECRET)) == ["x", "<redacted>"]
    assert audit.scrub(7) == 7


# -- the rejection lines (P16) ---------------------------------------------
def test_rejection_lines_by_reason(tmp_path, monkeypatch):
    """Four shapes. `fields` is present exactly when there are fields to
    name -- the census counts `reason` and `fields`, and an empty list
    would count as a named field."""
    root = _store(tmp_path, monkeypatch)

    audit.record_rejection("nosuch", -32602, "unknown_tool",
                           "Unknown tool: nosuch")
    audit.record_rejection("grep", -32602, "unknown_fields",
                           "unknown field 'regex' for grep; fields: run",
                           ("regex",))
    audit.record_rejection("grep", -32602, "bad_fields",
                           "bad value for 'pattern' on grep: expected string",
                           ("pattern",))
    audit.record_rejection("grep", -32602, "missing_fields",
                           "missing required field(s) for grep: pattern",
                           ("pattern",))

    raw = (root / "mcp.jsonl").read_text().splitlines()
    unknown_tool, unknown, bad, missing = _lines(root)

    for line in (unknown_tool, unknown, bad, missing):
        assert list(line) == ["utc", "tool", "rejected"]
    assert list(unknown_tool["rejected"]) == ["code", "reason", "message"]
    assert unknown_tool["tool"] == "nosuch"
    assert unknown_tool["rejected"]["code"] == -32602
    assert unknown_tool["rejected"]["reason"] == "unknown_tool"
    assert unknown_tool["rejected"]["message"] == "Unknown tool: nosuch"

    for line, reason, fields in ((unknown, "unknown_fields", ["regex"]),
                                 (bad, "bad_fields", ["pattern"]),
                                 (missing, "missing_fields", ["pattern"])):
        assert list(line["rejected"]) == ["code", "reason", "fields",
                                          "message"]
        assert line["rejected"]["reason"] == reason
        assert line["rejected"]["fields"] == fields

    # key order as a reader greps it, not as `json.loads` hands it back
    assert ('"rejected":{"code":-32602,"reason":"unknown_fields",'
            '"fields":["regex"],"message":') in raw[1]

    # a malformed call that named no tool still gets its line
    audit.record_rejection(None, -32602, "unknown_tool", "no name")
    assert _lines(root)[-1]["tool"] is None

    # ...and a rejection is scrubbed WHOLE: the field name a model
    # misspelt is model-typed text, and `to_argv` quotes it back into the
    # message, so a secret typed there reaches both places.
    audit.record_rejection("grep", -32602, "unknown_fields",
                           f"unknown field '{SECRET}' for grep; fields: run",
                           (SECRET,))
    last = _lines(root)[-1]
    assert last["rejected"]["fields"] == ["<redacted>"]
    assert last["rejected"]["message"] == ("unknown field '<redacted>' for "
                                           "grep; fields: run")
    assert SECRET not in (root / "mcp.jsonl").read_text()


# -- the cancel line -------------------------------------------------------
def test_cancel_line(tmp_path, monkeypatch):
    root = _store(tmp_path, monkeypatch)

    audit.record_cancel("record", {"command": ["p.py"], "focus": [SECRET]},
                        False, 3001)
    audit.record_cancel("refocus", {"run": "last"}, True, None)

    ran, queued = _lines(root)
    assert list(ran) == ["utc", "tool", "arguments", "cancelled", "queued",
                         "ms"]
    assert ran["tool"] == "record"
    assert ran["arguments"] == {"command": ["p.py"], "focus": ["<redacted>"]}
    assert (ran["cancelled"], ran["queued"], ran["ms"]) == (True, False, 3001)
    assert (queued["queued"], queued["ms"]) == (True, None)


# -- the knob (D29) --------------------------------------------------------
def test_the_invocation_log_knob_disables_it(tmp_path, monkeypatch):
    """One word for "log nothing about my calls", and it means this file
    too -- the same knob, read through `invocations`, never a second
    variable that could drift from it."""
    root = _store(tmp_path, monkeypatch)
    monkeypatch.setenv("SENSORIUM_NO_INVOCATION_LOG", "1")

    assert audit.disabled() is True
    assert invocations._log_disabled() is True
    audit.record_call("grep", {}, _o(0), 10, False)
    audit.record_rejection("grep", -32602, "unknown_tool", "x")
    audit.record_cancel("grep", {}, False, 1)
    assert not (root / "mcp.jsonl").exists()

    # "0" is not "disabled": the log stays on, as the variable documents.
    monkeypatch.setenv("SENSORIUM_NO_INVOCATION_LOG", "0")
    assert audit.disabled() is False
    audit.record_call("grep", {}, _o(0), 10, False)
    assert len(_lines(root)) == 1


# -- never raises ----------------------------------------------------------
def test_a_write_failure_never_raises(tmp_path, monkeypatch, capsys):
    """A regular file where the store root belongs: `mkdir` cannot make a
    directory under it. One stderr line per dropped record, and the call
    returns None like any other best-effort logger."""
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    monkeypatch.setenv("SENSORIUM_DIR", str(blocker / "sub"))
    monkeypatch.delenv("SENSORIUM_NO_INVOCATION_LOG", raising=False)

    assert audit.record_call("grep", {}, _o(0), 10, False) is None
    assert audit.record_rejection("grep", -32602, "unknown_tool", "x") is None
    assert audit.record_cancel("grep", {}, False, 1) is None

    err = [ln for ln in capsys.readouterr().err.splitlines() if ln]
    assert len(err) == 3
    assert all(ln.startswith("sensorium mcp: audit: ") for ln in err)
    assert not (blocker / "sub").exists()


def test_a_lone_surrogate_in_a_line_never_raises(tmp_path, monkeypatch,
                                                 capsys):
    """I1. `_write` said "Never raises" and did: a lone surrogate in a
    field name, a tool name or an argument cannot be encoded onto the
    UTF-8 file, and `UnicodeEncodeError` -- a `ValueError`, not an
    `OSError` -- walked out of the audit and into the server's `_work`,
    which then answered `-32603` for an id that already had its result.
    One stderr line each, no exception, and the file stays a file."""
    root = _store(tmp_path, monkeypatch)
    audit.record_call("grep", {"pattern": "fine"}, _o(0), 10, False)

    assert audit.record_rejection("grep", -32602, "unknown_fields",
                                  "unknown field '\ud800bad' for grep",
                                  ("\ud800bad",)) is None
    assert audit.record_call("grep", {"pattern": "\ud800"}, _o(0), 10,
                             False) is None
    assert audit.record_cancel("grep", {"pattern": "\ud800"}, False,
                               1) is None

    err = [ln for ln in capsys.readouterr().err.splitlines() if ln]
    assert len(err) == 3, err
    assert all(ln.startswith("sensorium mcp: audit: ") for ln in err)
    # The census loses those three lines and says so on stderr; the one
    # written before them is intact, which is what a half-written line
    # would have destroyed.
    assert [ln["tool"] for ln in _lines(root)] == ["grep"]
