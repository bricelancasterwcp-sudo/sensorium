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


@pytest.fixture
def installed_fixture2(tmp_path, monkeypatch):
    store = tmp_path / "sdir" / "traces"
    store.mkdir(parents=True)
    shutil.copy(FIXTURE, store / "old2.db")
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return "old2"


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
