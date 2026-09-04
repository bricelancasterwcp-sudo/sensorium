"""A trace recorded by sensorium 0.2.0 (trace_format 2), read by this one.

Arc 2 gives coroutines and generators frames. A format-2 trace has none for
them -- it holds unframed CALL events -- and a format-3 reader must keep
saying exactly what 0.2.0 said about it: unframed lines in `tree`,
"recorded but not framed" in `frame`, the `ambiguous ... no frame recorded`
arm in `exceptions`, and `watch`'s "opens no frame in this version" reason.
No state, no disposition, no site may be claimed retroactively.
"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from sensorium.exit import NEGATIVE, UNSETTLED
from sensorium import cli
from sensorium.store.reader import Trace

FIXTURE = Path(__file__).parent / "fixtures" / "format2_async.db"


def test_fixture_really_is_trace_format_2_with_no_frame_kind():
    c = sqlite3.connect(FIXTURE)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    assert fmt == 2
    assert "kind" not in [r[1] for r in c.execute("PRAGMA table_info(frames)")]
    kinds = {r[0] for r in c.execute("SELECT DISTINCT kind FROM events")}
    assert "YIELD" not in kinds and "RESUME" not in kinds
    # No task_fingerprints table either: the reader must answer "no task
    # fingerprints", not raise, on a file recorded before they existed.
    assert Trace.open(FIXTURE).task_fingerprints() == {}


def test_fixture_carries_no_ambient_environment():
    env = Trace.open(FIXTURE).meta["env"]
    assert sorted(env) == ["LANG", "PATH", "SENSORIUM_DIR"]


def test_fixture_holds_the_arc1_unframed_shapes():
    t = Trace.open(FIXTURE)
    worker = next(c for c in t.codes() if c.qualname == "worker")
    rows = next(c for c in t.codes() if c.qualname == "rows")
    assert len(t.unframed_calls(code_id=worker.id)) == 2
    assert t.unframed_calls(code_id=rows.id)[0].payload["unframed"] == "generator"
    assert t.frames(code_id=worker.id) == []
    assert t.meta["focus_unframed"] == ["format2_async:worker"]


def _installed(tmp_path, monkeypatch, fixture: Path, run_id: str) -> str:
    """One recorded fixture, copied into a private store the CLI can find."""
    store = tmp_path / "sdir" / "traces"
    store.mkdir(parents=True, exist_ok=True)
    shutil.copy(fixture, store / f"{run_id}.db")
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


@pytest.fixture
def installed_fixture2(tmp_path, monkeypatch):
    return _installed(tmp_path, monkeypatch, FIXTURE, "old2")


def test_tree_on_a_format2_trace_keeps_the_unframed_wording(
        installed_fixture2, capsys):
    """0.2.0 opened no frame for a coroutine or generator, and this trace is
    what that recorder wrote. A format-3 reader must keep saying so: the
    unframed lines, the `<- caller (unframed)` tags and the footer are the
    honest account of THIS trace. Rendering the arc-2 vocabulary over it --
    a bare `[coroutine]` marker, a `~ suspended` tail, the "started before
    recording" wording -- would claim frames and states that were never
    recorded, from a file that cannot support either claim."""
    assert cli.main(["tree", installed_fixture2]) == 0
    out = capsys.readouterr().out
    assert "[coroutine, unframed]" in out
    assert "[generator, unframed]" in out
    assert "<- worker (unframed)" in out
    assert "6 unframed call(s) in this trace" in out
    # No derived state: the trace has no YIELD/RESUME rows to derive from.
    assert "~ " not in out
    assert "no frame: started before recording" not in out
    # ...and no bare kind marker: every kind here is qualified as unframed.
    for ln in out.splitlines():
        assert "[coroutine]" not in ln and "[generator]" not in ln
    # The frames this trace DOES have are plain functions, and a plain
    # function is marked by nothing at all -- on this trace and on any
    # other. `[function]` on every ordinary call would be noise on every
    # line, and here it would also be new vocabulary over an old file.
    assert "[function]" not in out


def test_frame_on_a_format2_trace_shows_no_kind_or_state_for_step(
        installed_fixture2, capsys):
    """`worker` still has no frame on this trace -- `frame` must keep
    refusing with the arc-1 "not framed" wording, unchanged by Task 7.
    `step` DOES have a frame (plain functions were always framed), but it
    is a format-2 frame: its `kind` column does not exist, so it defaults
    to "function", and `frame_state` derives "returned" for it -- both
    fall into the arm Task 7's header contract excludes. Rendering a bare
    `[coroutine]` or a `state:` segment here would claim a disposition this
    trace holds no YIELD/RESUME evidence for."""
    assert cli.main(["frame", installed_fixture2, "--fn", "worker"]) == 1
    out = capsys.readouterr().out
    assert "recorded as 2 call(s) but not framed (coroutine)" in out

    assert cli.main(["frame", installed_fixture2, "--fn", "step"]) == 0
    out = capsys.readouterr().out
    assert "state:" not in out
    # No kind marker: the qualname is followed directly by the event-range
    # bracket, with nothing inserted between them.
    assert "step  [e" in out.splitlines()[0]


def test_exceptions_on_a_format2_trace_claims_no_frame_and_no_state(
        installed_fixture2, capsys):
    """The fixture's CancelledError was handled inside a coroutine that this
    recorder never framed, so there is still no closed_by to read: the
    `no frame recorded` arm survives, and its reason names the format rather
    than claiming -- falsely, of a format-3 trace -- that coroutines open no
    frames. No derived state may leak onto an old trace either: this file has
    no YIELD/RESUME rows, so nothing here was ever cancelled, abandoned or
    suspended as far as it can say."""
    assert cli.main(["exceptions", installed_fixture2]) == 0
    out = capsys.readouterr().out
    assert "no frame recorded" in out
    assert ("recorded by a sensorium before coroutine frames existed "
            "(format <= 2); no closed_by to read") in out
    assert "dispositions: ambiguous 1" in out
    for claim in ("~ ", "frame later", "cancelled at L", "abandoned",
                  "suspended"):
        assert claim not in out, claim


def test_tree_around_an_unframed_call_of_a_format2_trace_still_says_so(
        installed_fixture2, capsys):
    """`--around` on a CALL that opened no frame cannot show a subtree: there
    is none. On THIS trace that is the truthful answer and the message has to
    keep naming the reason (and where to look instead) rather than falling
    back to the generic "no frame contains it", which reads as a bad event
    reference. Arc 2 removed the shape from new recordings, not from this
    file."""
    ev = Trace.open(FIXTURE).unframed_calls()[0]
    assert cli.main(["tree", installed_fixture2, "--around", f"e{ev.id}"]) == 1
    out = capsys.readouterr().out
    assert f"e{ev.id} is an unframed CALL of" in out
    assert "sensorium grep" in out
    # ...and not the generic fallback, which names the REF and nothing else.
    assert f"no frame contains e{ev.id}" not in out


def test_watch_on_a_format2_trace_keeps_the_unframed_wording(
        installed_fixture2, capsys):
    """The fixture was recorded with `--focus format2_async:worker`, and in
    0.2.0 a coroutine focus opened no frame -- `worker` has CALL events and
    no frame on this file, same as every other command in this module.
    `watch`'s sites come from frames, so there are none here, and Task 9's
    format-3 branch (a coroutine focus DOES contribute sites now) must not
    retroactively claim any on a trace that never recorded them."""
    assert cli.main(["watch", installed_fixture2, "--at",
                     "format2_async:worker", "--expr",
                     "name == 'A'"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "NOTHING WAS CHECKED" in out
    assert "opens no frame in this version" in out
    assert "NEVER RECORDED" in out


def test_info_on_a_format2_trace_keeps_the_unframed_wording(
        installed_fixture2, capsys):
    """Task 9 makes `info` print "unframed calls: 0 (all calls framed in
    format 3)" -- but only for a format-3 trace. This fixture is format 2
    and DOES hold unframed calls (6 of them, per
    `test_fixture_holds_the_arc1_unframed_shapes`), so the arc-1 line with
    its kind breakdown must survive unchanged. The `recorded:` line grows
    YIELD/RESUME columns regardless of format -- this file has none of
    either kind, and 0 is the honest count, not a claim they were framed."""
    assert cli.main(["info", installed_fixture2]) == 0
    out = capsys.readouterr().out
    assert "unframed calls: 6 (coroutine 5, generator 1)" in out
    assert "all calls framed in format 3" not in out
    assert ("recorded: CALL 14  RETURN 13  RAISE 1  HANDLED 4  YIELD 0  "
            "RESUME 0  LINE 0") in out


# -- a second 0.2.0 trace: a sync framed function calling a generator ------
# `format2_async.db` holds a generator too, but tangled with two tasks and a
# cancellation, so the plain shape -- framed caller, unframed generator, and
# a helper frame left parentless under it -- is only ever read through the
# async case. This fixture isolates it, so the old-trace branches that exist
# for exactly that shape are covered end to end rather than by inference.
FIXTURE_GEN = Path(__file__).parent / "fixtures" / "format2_gen.db"


def test_generator_fixture_is_format_2_and_carries_no_ambient_environment():
    c = sqlite3.connect(FIXTURE_GEN)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    assert fmt == 2
    assert sorted(Trace.open(FIXTURE_GEN).meta["env"]) == [
        "LANG", "PATH", "SENSORIUM_DIR"]


@pytest.fixture
def installed_fixture2gen(tmp_path, monkeypatch):
    return _installed(tmp_path, monkeypatch, FIXTURE_GEN, "old2g")


def test_tree_on_a_format2_generator_trace_keeps_the_unframed_shapes(
        installed_fixture2gen, capsys):
    """`main` was framed, `rows` was not, and `clean` -- called from inside
    the generator body -- had no frame to be a child of. 0.2.0 recorded the
    generator's CALL as an unframed event and tagged each `clean` frame with
    the caller it could not be hung under. A format-3 reader must render
    both of those unchanged: a bare `[generator]` marker here would claim a
    frame this file does not contain, and dropping the `<- rows (unframed)`
    tag would silently re-parent three frames to nothing."""
    assert cli.main(["tree", installed_fixture2gen]) == 0
    out = capsys.readouterr().out
    assert "[generator, unframed]" in out
    assert "<- rows (unframed)" in out
    assert out.count("<- rows (unframed)") == 3
    assert "unframed call(s) in this trace" in out
    # No arc-2 vocabulary over an old file: no derived state, and no bare
    # kind marker on any line.
    assert "~ " not in out
    for ln in out.splitlines():
        assert "[generator]" not in ln and "[function]" not in ln


def test_frame_on_a_format2_generator_trace_refuses_with_arc1_wording(
        installed_fixture2gen, capsys):
    """The generator ran once and has no frame on this trace. `frame` must
    keep saying exactly that -- recorded, not framed, and which kind -- and
    must not invent a frame for it now that generators have one."""
    assert cli.main(["frame", installed_fixture2gen, "--fn", "rows"]) == 1
    out = capsys.readouterr().out
    assert "recorded as 1 call(s) but not framed (generator)" in out
    assert "state:" not in out


def test_exceptions_on_a_format2_generator_trace_claims_no_state(
        installed_fixture2gen, capsys):
    """Nothing was raised in this program, so `exceptions` has nothing to
    classify -- and a clean old trace is the easiest place for a derived
    state to leak in as a stray tail. The file holds no YIELD/RESUME rows,
    so nothing here was ever cancelled, abandoned or suspended as far as it
    can say, and the command still exits 0."""
    assert cli.main(["exceptions", installed_fixture2gen]) == NEGATIVE
    out = capsys.readouterr().out
    assert "no exceptions recorded" in out
    for claim in ("~ ", "frame later", "cancelled", "abandoned", "suspended",
                  "never closed", "state:"):
        assert claim not in out, claim
