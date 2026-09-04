"""The exit-status convention as one matrix: site table -> named constant.

The plan's site table (X2) is the contract; this file is that table for the
five listing commands, one parametrised case per row whose code no existing
test already pinned. `sensorium.exit`'s names are used on both sides -- a
case that spelled the number would still pass if the constant moved, which
is the one thing the convention must not allow.

Rows already pinned at the code the table requires are left where they are
and are NOT repeated here: `grep` matches >= 1 / `--limit < 1`
(`tests/test_grep.py`), `tree` frames printed / `no such frame` / `--limit`
/ `--depth` (`tests/test_tree_frame.py`), `frame` printed / its three
negative messages (`tests/test_tree_frame.py`,
`tests/test_format{1,2}_fixture.py`), `exceptions` dispositions listed /
`--limit < 1` (`tests/test_exceptions.py`), and `grep matches: 0`
(`tests/test_grep.py`, moved 0 -> 1 by this commit).

`watch` and `flow` are the exception to that, and deliberately: both now
decide their status STRUCTURALLY -- `watch` from the verdict class its
`verdict()` returns, `flow` from the status `resolve_object` carries
alongside its message -- so each mapping has arms that only differ from one
another. A file that pinned the arms one at a time, in the command's own
test module, cannot show that the arms disagree; the rows below are the
whole mapping in one place, so collapsing either one to a single code fails
here. The per-command modules keep their own richer pins (the verdict's
exact wording, the message text), and those moved with this commit too:
`tests/test_watch_verdict.py`, `tests/test_watch.py`,
`tests/test_format2_fixture.py`, `tests/test_flow.py`,
`tests/test_flow_identity.py`.
"""
import pytest

from sensorium import cli
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from tests.helpers import finalize_synthetic
from tests.programs import CLEAN, exc_payload, record, synthetic

SYNTH_RUN = "20260101-000000-abcdef"


# -- trace shapes ----------------------------------------------------------
# Each builder leaves SENSORIUM_DIR pointing at a disposable store and
# returns the run id the case's argv should name (None when the case is
# about a store that holds nothing).
def _empty_store(tmp_path, monkeypatch):
    """A store with no traces at all."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return None


def _recorded(tmp_path, monkeypatch):
    """A real recording of a program that raises nothing: `add` runs once."""
    return record(tmp_path, monkeypatch, CLEAN)


def _bare(tmp_path, monkeypatch):
    """A trace with meta and nothing else -- no events, no frames."""
    w = synthetic(tmp_path, monkeypatch)
    w.close()
    return SYNTH_RUN


def _incomplete(tmp_path, monkeypatch):
    """A recording that never finalized: silence is not evidence of none."""
    w = synthetic(tmp_path, monkeypatch)
    w.set_meta("incomplete", True)
    w.close()
    return SYNTH_RUN


def _uncaught_only(tmp_path, monkeypatch):
    """An exception escaped, but no RAISE row carries its identity -- it
    fired where nothing was traced. The header reports it all the same."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, exit_status=1,
                       uncaught=exc_payload("ValueError", "boom", 1, serial=1))
    w.close()
    return SYNTH_RUN


def _rust(tmp_path, monkeypatch):
    """A finalized trace another recorder wrote, in another language."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.rs", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0")
    w.close()
    return SYNTH_RUN


def _undeclared(tmp_path, monkeypatch):
    """A recorder that declares it produces neither LINE events nor object
    identity -- the two capabilities `watch` and `flow` are gated on."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.rs", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"line": False,
                                     "object_identity": False})
    w.close()
    return SYNTH_RUN


# -- the matrix ------------------------------------------------------------
# (site-table row, trace shape, argv, expected status, text that must show)
# "$RUN" is replaced by the builder's run id.
MATRIX = [
    ("runs: at least one trace listed",
     _recorded, ["runs"], ANSWERED, "$RUN"),
    ("runs: no traces recorded",
     _empty_store, ["runs"], NEGATIVE, "no traces recorded"),
    # `matches: 0` is NEGATIVE (pinned in tests/test_grep.py), but zero
    # matches for --kind LINE on a run that recorded no LINE event at all
    # is a gap in the recording, not the trace saying "no".
    ("grep: --kind LINE with no LINE capture",
     _recorded, ["grep", "$RUN", "a", "--kind", "LINE"],
     UNSETTLED, "line-level capture needs --focus"),
    ("tree: no frames recorded",
     _bare, ["tree", "$RUN"], NEGATIVE, "no frames recorded"),
    ("frame: --nth N is out of range",
     _recorded, ["frame", "$RUN", "--fn", "add", "--nth", "9"],
     BAD_CALL, "--nth 9 is out of range"),
    ("frame: no ref given at all",
     _recorded, ["frame", "$RUN"],
     BAD_CALL, "no such frame; give f<id> or --fn QUALNAME [--nth N]"),
    ("exceptions: no exceptions recorded",
     _recorded, ["exceptions", "$RUN"], NEGATIVE, "no exceptions recorded"),
    ("exceptions: no RAISE events recorded (see INCOMPLETE above)",
     _incomplete, ["exceptions", "$RUN"],
     UNSETTLED, "no RAISE events recorded (see INCOMPLETE above)"),
    # The third arm of the same `if not all_raises` block: an exception
    # escaped and the header said so, but no RAISE row carries its
    # identity. WHICH exception it was is the question, and only a
    # recording that captured the raise can settle it.
    ("exceptions: uncaught reported, no RAISE row of its own",
     _uncaught_only, ["exceptions", "$RUN"], UNSETTLED, "uncaught: "),
    ("exceptions: REFUSED on a trace another recorder wrote",
     _rust, ["exceptions", "$RUN"],
     UNSETTLED, "REFUSED: exceptions on a rust trace"),
    # -- watch: the three verdict classes are three different answers ------
    # `add(1, 2)` is recorded with its arguments and no LINE event, so one
    # CALL site carries `a`, and `ghost` is bound nowhere: the same command
    # over the same trace reaches all three arms by the predicate alone.
    ("watch: SATISFIED",
     _recorded, ["watch", "$RUN", "--at", "add", "--expr", "a > 0"],
     ANSWERED, "verdict: SATISFIED"),
    ("watch: not satisfied",
     _recorded, ["watch", "$RUN", "--at", "add", "--expr", "a > 100"],
     NEGATIVE, "verdict: not satisfied"),
    ("watch: verdict NOTHING WAS CHECKED",
     _recorded, ["watch", "$RUN", "--at", "add", "--expr", "ghost > 1"],
     UNSETTLED, "verdict: NOTHING WAS CHECKED"),
    ("watch: no recorded code matches --at",
     _recorded, ["watch", "$RUN", "--at", "nosuch", "--expr", "a > 0"],
     NEGATIVE, "no recorded code matches --at"),
    ("watch: REFUSED: watch needs line",
     _undeclared, ["watch", "$RUN", "--at", "main", "--expr", "1 == 1"],
     UNSETTLED, "REFUSED: watch needs line"),
    # -- flow -------------------------------------------------------------
    ("flow: sightings printed",
     _recorded, ["flow", "$RUN", "--value", "1"], ANSWERED, "sightings: 1"),
    ("flow: zero sightings",
     _recorded, ["flow", "$RUN", "--value", "999999"],
     NEGATIVE, "sightings: 0"),
    ("flow: REFUSED: flow needs line",
     _undeclared, ["flow", "$RUN", "--value", "1"],
     UNSETTLED, "REFUSED: flow needs line"),
    ("flow: REFUSED: flow --object needs object_identity",
     _undeclared, ["flow", "$RUN", "--object", "main:x"],
     UNSETTLED, "REFUSED: flow --object needs object_identity"),
    # The `resolve_object` split (X6): a reference the trace does not hold
    # is the trace saying "no"; a spec that cannot name anything, or a name
    # whose value has no identity to follow, is the call being wrong.
    ("flow: no event eN",
     _recorded, ["flow", "$RUN", "--object", "e99999:a"],
     NEGATIVE, "no event e99999 in this trace"),
    ("flow: no CALL of X was recorded",
     _recorded, ["flow", "$RUN", "--object", "nosuchfn:a"],
     NEGATIVE, "no CALL of 'nosuchfn' was recorded"),
    ("flow: X is not captured at eN",
     _recorded, ["flow", "$RUN", "--object", "add:nope"],
     NEGATIVE, "'nope' is not captured at e"),
    ("flow: malformed --object spec",
     _recorded, ["flow", "$RUN", "--object", "cfg"],
     BAD_CALL, "object spec must be e<id>:<name> or <qualname>:<name>"),
    ("flow: primitive has no identity to follow",
     _recorded, ["flow", "$RUN", "--object", "add:a"],
     BAD_CALL, "has no identity to follow; use --value"),
]


@pytest.mark.parametrize("row,build,argv,expected,needle",
                         MATRIX, ids=[c[0] for c in MATRIX])
def test_exit_status_matches_the_site_table(
        row, build, argv, expected, needle, tmp_path, monkeypatch, capsys):
    run_id = build(tmp_path, monkeypatch)
    argv = [run_id if a == "$RUN" else a for a in argv]
    status = cli.main(argv)
    out = capsys.readouterr().out
    want = run_id if needle == "$RUN" else needle
    assert want in out, out
    assert status == expected, f"{row}: {status} != {expected}\n{out}"
