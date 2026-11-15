"""End to end `sensorium c run` on the sample programs.

`stats` with no extra argv returns. `stats bob` crashes in `name_len`.
`diff` of the pair diverges, and `tree` on the crash names `name_len`
and `SIGSEGV`. `threads` shows both workers before the NULL deref.
`assert_div` aborts. `longjmp_test` exits 0, `test_two` returns 42, and
the jump is not a RAISE.
"""
import shutil

import pytest

from tests.c_helpers import SAMPLES, build_and_run, calls, returns, run_c

if shutil.which("gcc") is None:
    pytest.skip("gcc is not on PATH", allow_module_level=True)


@pytest.fixture(scope="module")
def stats_pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("stats")
    sdir = root / "sdir"
    good = build_and_run(root / "good", SAMPLES / "stats.c", sdir, binary="stats")
    crash = build_and_run(root / "bad", SAMPLES / "stats.c", sdir,
                           argv=("bob",), binary="stats")
    return good, crash


def test_stats_good_and_crash_diverge(stats_pair):
    good, crash = stats_pair
    assert good.proc.returncode == 0, good.proc.stdout + good.proc.stderr
    assert crash.proc.returncode != 0, crash.proc.stdout
    assert good.trace.path != crash.trace.path
    proc = run_c(
        ["diff", good.trace.path.stem, crash.trace.path.stem],
        crash.work, crash.sdir)
    text = proc.stdout + proc.stderr
    assert "DIVERGED" in text, text


def test_tree_on_the_stats_crash_shows_name_len_and_sigsegv(stats_pair):
    _good, crash = stats_pair
    proc = run_c(["tree", crash.trace.path.stem], crash.work, crash.sdir)
    text = proc.stdout
    assert "name_len" in text, text + proc.stderr
    assert "SIGSEGV" in text, text


def test_threads_show_both_workers_then_the_crash(tmp_path_factory):
    root = tmp_path_factory.mktemp("threads")
    rec = build_and_run(root / "work", SAMPLES / "threads.c", root / "sdir",
                        link=("-pthread",), binary="threads")
    assert rec.proc.returncode != 0, rec.proc.stdout
    worker_calls = calls(rec.trace, "worker_fn")
    assert len(worker_calls) >= 2, [e.payload for e in worker_calls]
    tids = {e.thread_id for e in worker_calls}
    assert len(tids) >= 2, tids
    raises = rec.trace.events("RAISE")
    assert raises, "no RAISE after the joins"
    blob = str([e.payload for e in raises])
    assert "SIGSEGV" in blob, blob
    main_tid = rec.trace.meta.get("main_thread_ident")
    assert raises[-1].thread_id == main_tid, (raises[-1].thread_id, main_tid)
    proc = run_c(["tree", rec.trace.path.stem], rec.work, rec.sdir)
    assert proc.stdout.count("worker_fn") >= 2, proc.stdout
    assert "SIGSEGV" in proc.stdout, proc.stdout


def test_assert_sample_aborts(tmp_path_factory):
    root = tmp_path_factory.mktemp("assert")
    rec = build_and_run(root / "work", SAMPLES / "assert_div.c", root / "sdir",
                        binary="assert_div")
    assert rec.proc.returncode != 0, rec.proc.stdout
    raises = rec.trace.events("RAISE")
    blob = str([e.payload for e in raises])
    assert raises, "assert produced no RAISE"
    assert "SIGABRT" in blob or "divisor must be nonzero" in blob, blob


def test_longjmp_runs_the_second_test_and_exits_0(tmp_path_factory):
    """Trampoline repair: test_one jumps, test_two still returns 42, no RAISE."""
    root = tmp_path_factory.mktemp("jump")
    rec = build_and_run(root / "work", SAMPLES / "longjmp_test.c", root / "sdir",
                        binary="longjmp_test")
    assert rec.proc.returncode == 0, rec.proc.stdout + rec.proc.stderr
    assert calls(rec.trace, "test_one"), "test_one was not called"
    vals = [(e.payload or {}).get("value") for e in returns(rec.trace, "test_two")]
    assert vals, "test_two did not return"
    nums = [v.get("v") for v in vals if isinstance(v, dict) and v.get("k") == "num"]
    assert 42 in nums, vals
    assert rec.trace.events("RAISE") == [], rec.trace.events("RAISE")
