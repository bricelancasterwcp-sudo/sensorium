"""`Part.phase` -- what happens to a phase that raises.

The E16 instrument's cells are tested on hand-built rows
(`tests/test_acceptance_e16_cells.py`); this module tests the one piece of
the RUNNER whose behaviour is a decision rather than plumbing, and the piece
this instrument got wrong.

WHAT WENT WRONG, AND WHY IT IS PINNED HERE
------------------------------------------
`phase()` records a phase's own failure instead of raising it, on purpose: a
recording that fell over should drop the cell that needed it, not kill the
run with three other cells unread. Ruling R37 then added `build-driver` as
the first phase -- rebuild the release driver, refuse if the build fails --
and its dry run watched the new phase raise `KeyError: 'build'`, `phase()`
swallow the exception into a note, and the run go on to record WITH THE
UNREBUILT BINARY and report `DONE`. A rebuild that is not a refusal is not a
rebuild, and the failure R37 exists to prevent is exactly the one it would
have let through.

The fix was `critical=True` on the two phases that are PRECONDITIONS rather
than measurements. Two lines in one file, held by nothing: `critical=`
appeared at two call sites and no test constructed a `Part`. So this module
pins three things --

* a critical phase that raises ENDS the run, and its failure is still
  recorded (a refusal whose phase table forgot the phase would leave a
  reader unable to see which precondition failed);
* a non-critical phase that raises does NOT, and records the note;
* `main` marks EXACTLY the phases `CRITICAL_PHASES` names, read out of the
  module's own syntax tree rather than by running it -- so dropping
  `critical=True` from either call reddens here.

`Part.__init__` touches no filesystem -- it builds paths and nothing else --
so a `Part` can be constructed for these tests without a store, a driver or
a work root that exists.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "acceptance_e16"))

import e16a                                                       # noqa: E402
from e16a import CRITICAL_PHASES, Part, Refused                   # noqa: E402


@pytest.fixture
def part(tmp_path):
    """A `Part` over paths that need not exist: nothing below runs a phase
    that touches one."""
    return Part(tmp_path / "work", tmp_path / "out", str(tmp_path / "node"),
                str(tmp_path / "release"), dry=True, label="t")


def _raiser():
    raise KeyError("build")


# -- a precondition that fails ends the run --------------------------------
def test_a_critical_phase_that_raises_refuses(part):
    with pytest.raises(Refused) as caught:
        part.phase("build-driver", _raiser, critical=True)
    assert "build-driver is a precondition and it failed" in str(caught.value)
    assert "KeyError: 'build'" in str(caught.value)


def test_a_critical_phase_that_fails_is_still_in_the_phase_table(part):
    """A refusal whose phase table forgot the phase leaves a reader unable
    to see WHICH precondition failed, or how long it took to fail."""
    with pytest.raises(Refused):
        part.phase("build-driver", _raiser, critical=True)
    assert len(part.phases) == 1
    row = part.phases[0]
    assert row["name"] == "build-driver"
    assert row["error"] == "KeyError: 'build'"
    assert isinstance(row["seconds"], float)


def test_a_critical_phase_that_succeeds_returns_its_value(part):
    assert part.phase("build-driver", lambda: {"built": True},
                      critical=True) == {"built": True}
    assert part.phases[0]["error"] is None


# -- a measurement that fails drops its cell, and only its cell ------------
def test_a_non_critical_phase_that_raises_returns_none_and_notes_it(part):
    """The behaviour `critical` inverts, and it has to keep working: a
    recording that fell over drops the cell that needed it rather than
    killing the run with three other cells unread."""
    assert part.phase("record-rust", _raiser) is None
    assert part.phases[0]["error"] == "KeyError: 'build'"
    assert part.phases[0]["name"] == "record-rust"


def test_the_run_continues_after_a_non_critical_failure(part):
    part.phase("record-rust", _raiser)
    assert part.phase("modes", lambda: ["a row"]) == ["a row"]
    assert [row["name"] for row in part.phases] == ["record-rust", "modes"]
    assert [row["error"] for row in part.phases] == ["KeyError: 'build'", None]


def test_a_refusal_from_inside_a_phase_is_never_swallowed(part):
    """`Refused` is the instrument's own "do not continue", and a phase that
    raises one means it -- critical or not."""
    def refuse():
        raise Refused("the store already exists")

    with pytest.raises(Refused):
        part.phase("preflight", refuse)


# -- exactly these phases are preconditions --------------------------------
def _phase_calls() -> dict[str, bool]:
    """Every `part.phase("<name>", ...)` in `main`, and whether it passes
    `critical=True`.

    Read from the module's SYNTAX TREE, not from its text and not by running
    it: a regex over source cannot tell a call from a comment, and running
    `main` would need a box. The mutation this catches is one keyword
    deleted from one line."""
    tree = ast.parse((REPO / "tests" / "acceptance_e16" / "e16a.py")
                     .read_text())
    main = next(node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name == "main")
    calls = {}
    for node in ast.walk(main):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "phase"):
            continue
        name = node.args[0]
        assert isinstance(name, ast.Constant), ast.dump(name)
        calls[name.value] = any(
            kw.arg == "critical" and getattr(kw.value, "value", None) is True
            for kw in node.keywords)
    return calls


def test_main_marks_exactly_the_critical_phases_as_critical():
    """Catches the one-keyword mutation directly: drop `critical=True` from
    the `build-driver` call and this fails, which is what the R37 dry run
    had to catch by running the whole instrument."""
    calls = _phase_calls()
    assert set(CRITICAL_PHASES) <= set(calls), (set(CRITICAL_PHASES)
                                                - set(calls))
    marked = {name for name, critical in calls.items() if critical}
    assert marked == set(CRITICAL_PHASES), marked


def test_every_phase_main_runs_is_accounted_for():
    """The other direction: a phase added to `main` is either a measurement
    or a precondition, and `CRITICAL_PHASES` is where that is written down.
    A new precondition marked at the call site but not listed here would
    pass the test above only by widening `marked`, which it cannot."""
    calls = _phase_calls()
    assert len(calls) >= 11, sorted(calls)
    assert "build-driver" in calls and "grep" in calls
    assert e16a.CRITICAL_PHASES == ("build-driver", "preflight")
