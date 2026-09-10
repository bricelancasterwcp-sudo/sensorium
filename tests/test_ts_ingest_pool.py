"""How the converter runs its work: the pool, and what it does when a
worker dies.

Split out of `tests/test_ts_ingest_meta.py` at the 800-line ceiling, along
the seam that was already there: that module is about what the converter
WRITES -- the meta keys, the refusals, this command's own surfaces -- and
these three tests are about the machinery that runs it. The fixtures and
the driving machinery stay `tests/ts_spools.py`, shared by all three.
"""
import json
import multiprocessing

import pytest

from tests.helpers import run_cli
from tests.ts_spools import FIXTURES, copy_tree, ingest_case, only_trace


def test_the_pool_and_the_single_process_answer_the_same(tmp_path):
    """`--jobs 1` runs in this process; anything more runs a pool. Two paths
    to one answer, held on a directory with more than one spool so the pool
    is really taken -- and one of those spools is refused, which is the part
    worth checking across a process boundary: a refusal must come back as a
    VALUE the parent can print, not as an exception that kills the pool."""
    _s1, sdir1, one = ingest_case("no-boot", tmp_path / "one", jobs=1)
    _s2, sdir2, many = ingest_case("no-boot", tmp_path / "many", jobs=4)
    assert one.returncode == many.returncode == 2
    assert _refusals(one.stdout) == _refusals(many.stdout)
    a = only_trace(sdir1)
    b = only_trace(sdir2)
    assert a.task_fingerprints() == b.task_fingerprints()
    assert a.fingerprints() == b.fingerprints()
    assert a.meta["truncated_count"] == b.meta["truncated_count"]


def _refusals(stdout: str) -> list[str]:
    """The refusal lines, with the spool's absolute path -- which differs
    between two ingests of two copies -- taken back out."""
    return [ln.split(": ", 2)[-1].rsplit("/", 1)[-1]
            for ln in stdout.splitlines() if ln.startswith("refused: ")]


def test_a_worker_killed_by_a_signal_refuses_and_does_not_hang(tmp_path):
    """R42. A worker that dies of a signal never puts a result on the
    queue, and `Pool.imap` waits for one: the driver hung forever on a
    converter the OOM killer took, with no output and nothing to interrupt
    but the process itself. `ProcessPoolExecutor` raises
    `BrokenProcessPool` instead, which the existing `except Exception`
    turns into the marker plus a named refusal.

    Bounded by `SIGALRM` and not by patience: a regression here HANGS, and
    a hanging test is a suite that never reports rather than one that
    fails.
    """
    import signal as signal_mod
    from tests.ts_spools import kill_this_worker

    spool = tmp_path / "spool"
    copy_tree(FIXTURES / "each-names", spool)
    # Two containers, so `_map` uses the pool: one spool means one job, and
    # one job runs in this process -- which would kill the test runner.
    only = next(spool.glob("*.jsonl"))
    (spool / "439935-0.jsonl").write_bytes(only.read_bytes())
    assert len(list(spool.glob("*.jsonl"))) == 2

    from sensorium.ts import ingest
    monkeypatched = ingest._worker
    ingest._worker = kill_this_worker

    def _too_slow(_sig, _frame):
        raise AssertionError("ingest_dir did not return within 60s: a dead "
                             "worker is hanging the converter again")

    previous = signal_mod.signal(signal_mod.SIGALRM, _too_slow)
    signal_mod.alarm(60)
    try:
        with pytest.raises(ingest.IngestError) as e:
            ingest.ingest_dir(spool, tmp_path / "sdir", jobs=2)
    finally:
        signal_mod.alarm(0)
        signal_mod.signal(signal_mod.SIGALRM, previous)
        ingest._worker = monkeypatched

    assert "BrokenProcessPool" in str(e.value)
    # P6's marker is written anyway, and says what stopped the run: a
    # re-ingest must not mint a second run id for anything that converted.
    marker = json.loads((spool / "ingested.json").read_text())
    assert "BrokenProcessPool" in marker["error"]


def test_the_pool_is_spawned_not_forked():
    """A forked worker inherits the parent's threads, its sqlite handles and
    its signal dispositions; `spawn` is the only context this converter is
    written against."""
    from sensorium.ts import ingest
    assert ingest.CONTEXT == "spawn"
    assert multiprocessing.get_context(ingest.CONTEXT) is not None


