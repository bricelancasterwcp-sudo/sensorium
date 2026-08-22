"""A trace recorded by sensorium 0.3.0 (format 3, per-thread fingerprint
basis), read by this one. Plan 2b narrows what a thread fingerprint means
and fills `task_fingerprints`; neither may be claimed retroactively."""
import json
import sqlite3
from pathlib import Path

import pytest

from sensorium.store.reader import Trace
from tests.test_format2_fixture import _installed

FIXTURE = Path(__file__).parent / "fixtures" / "format3_async.db"


@pytest.fixture
def installed_fixture3(tmp_path, monkeypatch):
    return _installed(tmp_path, monkeypatch, FIXTURE, "old3")


def test_fixture_is_format_3_with_tasks_and_no_task_fingerprints():
    c = sqlite3.connect(FIXTURE)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    assert fmt == 3
    # asyncio.run(amain()) wraps amain itself in an implicit task (named
    # "Task-1" by asyncio) in addition to the two explicit task-A/task-B --
    # every task current_task() ever returns for a traced event gets a row,
    # the wrapper included. Same shape as tests/fixtures/format2_async.db.
    assert c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 3
    assert c.execute("SELECT COUNT(*) FROM task_fingerprints").fetchone()[0] == 0
    assert c.execute(
        "SELECT 1 FROM meta WHERE key='fingerprint_basis'").fetchone() is None


def test_fixture_carries_no_ambient_environment():
    env = Trace.open(FIXTURE).meta["env"]
    assert sorted(env) == ["LANG", "PATH", "SENSORIUM_DIR"]


def test_fixture_thread_fingerprint_counts_task_events_too():
    """0.3.0's thread fingerprint covered every causal event on the thread,
    the task events included -- the count says so."""
    t = Trace.open(FIXTURE)
    (tid, (h, n)), = t.fingerprints().items()
    causal = [e for e in t.events()
              if e.kind in ("CALL", "RETURN", "RAISE", "HANDLED")]
    assert n == len(causal)
    assert any(e.task_id is not None for e in causal)


def test_old3_thread_stream_still_holds_the_task_events():
    """Under the per-thread basis the thread stream IS every causal event on
    the thread; the narrowing is never applied to a trace that predates it."""
    t = Trace.open(FIXTURE)
    quals = [s[1] for s in t.causal_stream()]
    assert "worker" in quals and "step" in quals


def test_refocus_refuses_old3_before_re_running_it():
    """Read-only: the refusal is a property of the trace, so it can be asked
    for without touching the world. 0.3.0's single thread fingerprint covers
    the task events too, so there is no thread stream here of the kind this
    version compares and no task fingerprints to compare beside it -- and
    the answer must arrive BEFORE the rerun, which has side effects."""
    from sensorium.query import refocus_cmd

    t = Trace.open(FIXTURE)
    problem = refocus_cmd._refusal(t.meta, t)
    assert problem == (
        "original was recorded under the per-thread fingerprint basis and "
        "ran 3 asyncio task(s); this version compares tasks by content and "
        "defines thread streams without them, so no verdict against it "
        "would compare like with like -- re-record it with this version")
