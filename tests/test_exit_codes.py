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


# -- the matrix ------------------------------------------------------------
# (site-table row, trace shape, argv, expected status, text that must show)
# "$RUN" is replaced by the builder's run id.
MATRIX = [
    ("runs: at least one trace listed",
     _recorded, ["runs"], ANSWERED, "$RUN"),
    ("runs: no traces recorded",
     _empty_store, ["runs"], NEGATIVE, "no traces recorded"),
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
    # Not a site-table row: the third arm of the same `if not all_raises`
    # block, where an escaping exception was reported by the header and
    # nothing was listed under it. It answered before this commit and
    # answers after it -- pinned so the split above cannot swallow it.
    ("exceptions: uncaught reported, no RAISE row of its own",
     _uncaught_only, ["exceptions", "$RUN"], ANSWERED, "uncaught: "),
    ("exceptions: REFUSED on a trace another recorder wrote",
     _rust, ["exceptions", "$RUN"],
     UNSETTLED, "REFUSED: exceptions on a rust trace"),
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
