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


def test_tree_on_a_format1_trace_labels_parentage_assumed(installed_fixture,
                                                           capsys):
    assert cli.main(["tree", installed_fixture]) == 0
    out = capsys.readouterr().out
    assert "parentage: ASSUMED" in out and "format-1" in out
    # v1 parented every step to <module>; the tree must not PRESENT that as
    # derived, and must still show the unframed worker calls it never showed.
    assert out.count("worker(") == 2
    assert "[generator/coroutine, unframed]" in out      # kind unknown in v1
    assert "task t" not in out                             # no tasks recorded


def test_tree_subtree_views_of_a_format1_trace_keep_the_assumed_caveat(
        installed_fixture, capsys):
    """A subtree view drops the inter-task ordering line -- that line
    describes nothing the reader can see there -- but never the basis
    caveat: v1's parentage is a guess whichever slice you look at, and a
    view that omits the caveat hands that guess over as derived fact."""
    assert cli.main(["tree", installed_fixture, "--root", "f1"]) == 0
    out = capsys.readouterr().out
    assert "parentage: ASSUMED" in out
    assert "order between tasks" not in out
    # e4 is step's CALL event: a real event of this fixture, and the
    # call_event_id path through frame_containing.
    assert cli.main(["tree", installed_fixture, "--around", "e4"]) == 0
    out = capsys.readouterr().out
    assert "parentage: ASSUMED" in out
    assert "order between tasks" not in out


def test_frame_on_a_format1_trace_says_unframed_and_assumed(installed_fixture,
                                                             capsys):
    assert cli.main(["frame", installed_fixture, "--fn", "worker"]) == 1
    out = capsys.readouterr().out
    assert "recorded as 2 call(s) but not framed (generator/coroutine)" in out
    assert cli.main(["frame", installed_fixture, "--fn", "step"]) == 0
    out = capsys.readouterr().out
    assert "parentage: assumed (format-1 trace)" in out
    assert "task t" not in out.splitlines()[0]
