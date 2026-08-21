"""A trace recorded by the v1 recorder (trace_format 1), read by this one.

The fixture is a real recording, not a synthesised schema -- see
tests/fixtures/format1_async.py. These tests pin what a format-2 reader
CLAIMS about a format-1 trace: it opens, it says nothing about tasks (none
were recorded), and it labels parentage ASSUMED rather than letting v1's
last-opened-frame guess inherit the credibility of derived parentage.
"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from sensorium import cli
from sensorium.store.reader import Trace

FIXTURE = Path(__file__).parent / "fixtures" / "format1_async.db"


def test_fixture_really_is_trace_format_1():
    c = sqlite3.connect(FIXTURE)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    cols = [r[1] for r in c.execute("PRAGMA table_info(events)")]
    assert fmt == 1
    assert "task_id" not in cols


def test_fixture_opens_under_the_current_reader():
    t = Trace.open(FIXTURE)
    assert t.counts()["CALL"] == 10


def test_fixture_carries_no_ambient_environment():
    """A trace stores the whole process environment (README: 'What a trace
    file holds'). A fixture committed to git must therefore be recorded under
    `env -i` with exactly these three variables -- pinned EXACTLY so that a
    re-recording in a live shell (tokens, sockets, home paths) fails here
    rather than landing in history."""
    env = Trace.open(FIXTURE).meta["env"]
    assert sorted(env) == ["LANG", "PATH", "SENSORIUM_DIR"]


@pytest.fixture
def installed_fixture(tmp_path, monkeypatch):
    """The fixture placed in a disposable trace store, as run id `old`."""
    store = tmp_path / "sdir" / "traces"
    store.mkdir(parents=True)
    shutil.copy(FIXTURE, store / "old.db")
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return "old"


def test_format1_trace_reports_no_tasks_and_assumed_parentage():
    t = Trace.open(FIXTURE)
    assert t.format == 1
    assert t.tasks() == []                      # no table: not "zero tasks"
    assert t.parentage_basis() == "assumed"
    assert all(e.task_id is None for e in t.events())
    worker = next(c for c in t.codes() if c.qualname == "worker")
    assert len(t.unframed_calls(code_id=worker.id)) == 2   # join works on v1
    assert t.call_counts()[worker.id] == 2              # CALLs only, not RETURNs
