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
