"""The overhead benchmark asserts that the INSTRUMENT works, never that the
machine is fast.

A threshold on a multiplier is a hardware-dependent assertion, which is a
flaky test whose failure mode is a red suite on a busy laptop; the honest
home for the number is the printed table with the machine named beside it.
So what is pinned here is: the measurement is taken the way it says it is
(best of N, warm-up discarded), it never writes to the user's own trace
store, it reports "could not tell" as `-` rather than as zero, and `--bench`
reports without gating.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from corpus import run_corpus
from corpus._bench import bench

# Ten events: CALL/RETURN for <module>, for main, and for three calls to `a`.
TINY = '''
def a():
    return 1

def main():
    for _ in range(3):
        a()

if __name__ == "__main__":
    main()
'''

# Six: CALL/RETURN for <module>, for main, and for the one call to `a`.
TINIER = '''
def a():
    return 1

def main():
    a()

if __name__ == "__main__":
    main()
'''


def test_measure_reports_a_real_multiplier():
    m = bench.measure(TINY, reps=1)
    assert m["baseline_s"] > 0 and m["recorded_s"] > 0
    assert m["multiplier"] >= 1.0


def test_measure_counts_the_events_the_recorded_run_actually_wrote():
    """The multiplier is uninterpretable without the event count beside it:
    overhead is per event, so a number with no denominator generalises to
    nothing. Ten is this program's exact count, so a `_event_count` that
    counted frames, or returned a constant, fails here."""
    assert bench.measure(TINY, reps=1)["events"] == 10


def test_measure_never_writes_to_the_users_own_trace_store(monkeypatch):
    seen = []
    real = subprocess.run

    def spy(cmd, **kw):
        seen.append(kw["env"]["SENSORIUM_DIR"])
        return real(cmd, **kw)

    monkeypatch.setattr(bench.subprocess, "run", spy)
    bench.measure(TINY, reps=1)

    assert seen, "measure ran no subprocess at all"
    home_store = Path.home() / ".sensorium"
    for sdir in seen:
        assert not Path(sdir).is_relative_to(home_store), sdir
        # The store went away with the temporary directory it lived in, which
        # is what makes a benchmark run leave nothing behind.
        assert not Path(sdir).exists(), sdir


def _fake_clock(monkeypatch, ticks):
    it = iter(ticks)
    monkeypatch.setattr(bench, "time",
                        SimpleNamespace(perf_counter=lambda: next(it)))


def test_best_takes_the_minimum_of_the_timed_runs(monkeypatch):
    _fake_clock(monkeypatch, [0.0, 5.0, 0.0, 2.0, 0.0, 9.0, 0.0, 7.0])
    monkeypatch.setattr(bench.subprocess, "run",
                        lambda cmd, **kw: SimpleNamespace(stdout=""))
    best, _ = bench._best(["x"], ".", {}, reps=3)
    assert best == 2.0


def test_best_discards_the_warm_up_run(monkeypatch):
    """The warm-up pays for bytecode compilation and a cold page cache. If it
    were timed, it would be the maximum -- and with `min` that is invisible
    unless the warm-up is also the FASTEST run, which is what this pins."""
    _fake_clock(monkeypatch, [0.0, 0.5, 0.0, 4.0, 0.0, 6.0])
    calls = []
    monkeypatch.setattr(
        bench.subprocess, "run",
        lambda cmd, **kw: calls.append(cmd) or SimpleNamespace(stdout=""))
    best, _ = bench._best(["x"], ".", {}, reps=2)
    assert best == 4.0, "the untimed warm-up leaked into the measurement"
    assert len(calls) == 3, "expected one warm-up plus two timed runs"


def test_best_reports_the_output_of_a_run_it_timed(monkeypatch):
    """The trace counted afterwards must be one the timings describe."""
    outs = iter(["warm-up", "timed-1", "timed-2"])
    _fake_clock(monkeypatch, [0.0, 1.0, 0.0, 2.0, 0.0, 3.0])
    monkeypatch.setattr(bench.subprocess, "run",
                        lambda cmd, **kw: SimpleNamespace(stdout=next(outs)))
    _, out = bench._best(["x"], ".", {}, reps=2)
    assert out == "timed-2"


def test_event_count_says_it_could_not_tell_instead_of_zero():
    """`-` and `0` are different facts, and reporting the second as the first
    would put a fabricated denominator under every us/event figure."""
    assert bench._event_count("run: 20260819-000000-aaaaaa\n") is None


def test_a_measurement_with_no_trace_reports_no_per_event_cost(monkeypatch):
    monkeypatch.setattr(bench, "_event_count", lambda out: None)
    m = bench.measure(TINY, reps=1)
    assert m["events"] is None and m["us_per_event"] is None
    assert bench._row("w", "default", m).split()[-2:] == ["-", "-"]


def test_per_event_cost_is_the_added_time_over_the_events_that_caused_it(
        monkeypatch):
    """us/event is the figure a reader is invited to carry to their own
    program, so it must be the MARGINAL cost -- the time recording added,
    over the events recorded -- and not the whole recorded runtime, which
    would fold the program's own work into the recorder's bill."""
    times = iter([(2.0, ""), (5.0, "trace: x")])
    monkeypatch.setattr(bench, "_best", lambda *a, **kw: next(times))
    monkeypatch.setattr(bench, "_event_count", lambda out: 1000)

    m = bench.measure(TINY, reps=1)

    assert m["multiplier"] == 2.5
    assert m["us_per_event"] == 3000.0        # (5.0 - 2.0) / 1000, in us


def _rows_for(printed: str, workload: str) -> dict:
    return {ln.split()[1]: ln for ln in printed.splitlines()
            if ln.startswith(workload + " ")}


def test_report_prints_a_row_per_tier_of_every_workload(monkeypatch, capsys):
    """Two workloads, because one cannot tell a per-workload table from a
    table that reports the last one it measured -- and the whole reason there
    are two is that a single multiplier generalises to nothing."""
    monkeypatch.setattr(bench, "WORKLOADS",
                        {"tiny": (TINY, "prog:a"), "tinier": (TINIER, None)})
    out = bench.report(reps=1)
    printed = capsys.readouterr().out

    for workload in ("tiny", "tinier"):
        assert set(_rows_for(printed, workload)) == {"default", "focused"}
    for tier, line in _rows_for(printed, "tiny").items():
        m = out["tiny"][tier]
        # The row must carry THIS tier's own numbers, not a neighbour's.
        assert f"{m['multiplier']:.1f}" in line and str(m["events"]) in line
    assert out["tiny"]["default"]["events"] == 10
    assert out["tinier"]["default"]["events"] == 6


def test_report_refuses_to_report_a_focused_tier_it_could_not_focus(
        monkeypatch, capsys):
    """`tinier`'s registered focus is None -- there is nothing frameable to
    focus. Measuring `focus=None` a second time and printing it as the
    "focused" tier reports a run that was never focused: the row differs
    from `default` only by timing noise, and a reader reads that difference
    as the cost of focusing. So the tier says n/a and is not measured."""
    monkeypatch.setattr(bench, "WORKLOADS", {"tinier": (TINIER, None)})
    measured = []
    real = bench.measure
    monkeypatch.setattr(bench, "measure",
                        lambda *a, **kw: measured.append(kw.get("focus"))
                        or real(*a, **kw))

    out = bench.report(reps=1)

    row = _rows_for(capsys.readouterr().out, "tinier")["focused"]
    assert "n/a" in row and "(no frameable target to focus)" in row
    assert out["tinier"]["focused"] is None
    # DO_NOTHING's fixed-cost run, and the workload's default tier. A third
    # measurement is the un-focused re-run this test exists to forbid.
    assert measured == [None, None], measured


def test_report_states_the_fixed_cost_the_table_cannot_separate(
        monkeypatch, capsys):
    """Every row includes interpreter startup and recorder boot, so a short
    program's multiplier is mostly fixed cost. Printing it separately is what
    lets a reader subtract it instead of over-reading the ratio."""
    monkeypatch.setattr(bench, "WORKLOADS", {"tiny": (TINY, "prog:a")})
    out = bench.report(reps=1)
    line = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("recorder fixed cost:")]

    assert len(line) == 1, "the fixed cost is not reported"
    fixed = out["fixed_cost"]
    assert f"{fixed['recorded_s'] - fixed['baseline_s']:.3f}s" in line[0]
    assert fixed["recorded_s"] > fixed["baseline_s"]


def test_the_documented_command_reaches_the_bench(tmp_path):
    """`python corpus/run_corpus.py --bench` is what the README tells people
    to type, and running the harness as a SCRIPT puts `corpus/` on sys.path
    instead of the repo root -- so `from corpus._bench import bench` raised
    ModuleNotFoundError while every in-process test passed, because pytest
    puts the root there itself. The bench is stubbed so this test pays for
    the import path and not for a real benchmark.
    """
    pkg = tmp_path / "corpus"
    (pkg / "_bench").mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "_bench" / "__init__.py").write_text("")
    (pkg / "_bench" / "bench.py").write_text(
        "def report(*a, **kw):\n    print('stub table')\n")
    shutil.copy(Path(run_corpus.__file__), pkg / "run_corpus.py")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}

    r = subprocess.run([sys.executable, str(pkg / "run_corpus.py"), "--bench"],
                       capture_output=True, text=True, cwd=tmp_path, env=env)

    assert r.returncode == 0, r.stderr
    assert "stub table" in r.stdout, r.stderr


def test_bench_reports_without_running_the_corpus(monkeypatch, capsys):
    """`--bench` is a report, not a gate: it exits 0 whatever the numbers,
    and it does not smuggle in a corpus run whose failures could change the
    exit status underneath it."""
    monkeypatch.setattr(bench, "report",
                        lambda: print("call_dense default 9999.0"))
    monkeypatch.setattr(run_corpus, "run_case", _refuse)

    assert run_corpus.main(["--bench"]) == 0
    assert "9999.0" in capsys.readouterr().out


def _refuse(*a, **kw):
    raise AssertionError("--bench must not run corpus cases")
