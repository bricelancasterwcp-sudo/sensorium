"""`diff`: first causal divergence between two runs.

Built from real recorded traces (record the same program with different
argv to produce a genuine divergence), plus synthetic traces for the shapes
no real recording can be coaxed into on demand: an incomplete recording and
one with dropped late writes. Both are the single most important behaviour
of this command -- refusing a verdict rather than reporting a false
DIVERGED against a truncated stream.
"""
import re

from sensorium import cli, paths
from sensorium.query.diff_cmd import compare, first_divergence
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import run_cli
from tests.programs import THREADED_SWALLOWS, record

BRANCH = """
import sys

def gold(total):
    return total * 0.80

def silver(total):
    return total * 0.95

def price(points, total):
    if points > 1000:
        return gold(total)
    return silver(total)

def main():
    price(int(sys.argv[1]), 100.0)

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, name, argv):
    (tmp_path / "prog.py").write_text(BRANCH)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", "--", "prog.py", *argv], cwd=tmp_path,
                sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def _synthetic(tmp_path, monkeypatch, run_id, argv=("prog.py", "500")):
    """A minimal hand-built trace, for shapes no real recording produces on
    demand: incomplete runs and runs with dropped late writes."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db")
    w.set_meta("run_id", run_id)
    w.set_meta("argv", list(argv))
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    return w


# -- first_divergence: the pure comparison primitive ------------------------

def test_first_divergence_pure_function():
    a = [("p.py", "main", "CALL", 1), ("p.py", "gold", "CALL", 2)]
    b = [("p.py", "main", "CALL", 1), ("p.py", "silver", "CALL", 2)]
    assert first_divergence(a, b) == 1
    assert first_divergence(a, a) is None
    assert first_divergence(a, a[:1]) == 1


def test_first_divergence_ignores_a_trailing_event_id():
    """The 4th tuple slot is an event id and must never gate equality --
    two runs with identical shape but different absolute event numbering
    (e.g. more LINE events recorded in one) must still compare equal."""
    a = [("p.py", "main", "CALL", 1), ("p.py", "gold", "CALL", 9)]
    b = [("p.py", "main", "CALL", 5), ("p.py", "gold", "CALL", 40)]
    assert first_divergence(a, b) is None


def test_first_divergence_shorter_stream_reports_its_length():
    a = [("p.py", "main", "CALL", 1), ("p.py", "gold", "CALL", 2)]
    b = [("p.py", "main", "CALL", 1)]
    assert first_divergence(a, b) == 1
    assert first_divergence(b, a) == 1


# -- diff: real recordings ---------------------------------------------------

def test_identical_runs_match(tmp_path, monkeypatch, capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2]) == 0
    out = capsys.readouterr().out
    assert "MATCH" in out and "identical" in out
    # a MATCH must say what it does NOT claim, not just what it does
    assert "values" in out and "timing" in out and "LINE" in out
    assert "note:" not in out                # same argv: no spurious note


def test_divergent_runs_pinpoint_branch(tmp_path, monkeypatch, capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["1500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2]) == 1
    out = capsys.readouterr().out
    assert "DIVERGED" in out
    assert "silver" in out and "gold" in out
    assert "tree" in out            # drill-down hint on both sides
    assert f"tree {r1} --around e" in out
    assert f"tree {r2} --around e" in out
    # different argv (500 vs 1500) must be surfaced, not silently compared
    assert "different commands" in out


def test_diff_context_controls_how_much_common_history_is_shown(
        tmp_path, monkeypatch, capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["1500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2, "--context", "0"]) == 1
    out = capsys.readouterr().out
    assert "common" not in out
    assert "silver" in out and "gold" in out


def test_diff_exit_code_zero_on_match_one_on_diverged(tmp_path, monkeypatch):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["500"])
    r3 = _rec(tmp_path, "c", ["1500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2]) == 0
    assert cli.main(["diff", r1, r3]) == 1


def test_diff_rejects_a_malformed_run_ref_cleanly(tmp_path, monkeypatch,
                                                   capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, "no-such-run"]) == 2
    err = capsys.readouterr().err
    assert "error:" in err


def test_diff_notes_multiple_threads(tmp_path, monkeypatch, capsys):
    """Main-thread MATCH must not be read as a whole-run MATCH when other
    threads exist -- the note is the difference between the two claims."""
    r1 = record(tmp_path, monkeypatch, THREADED_SWALLOWS)
    r2 = record(tmp_path, monkeypatch, THREADED_SWALLOWS)
    assert cli.main(["diff", r1, r2]) == 0
    out = capsys.readouterr().out
    assert "MATCH" in out
    fa = Trace.open(paths.find_trace(r1)).fingerprints()
    assert len(fa) > 1, "fixture must actually record more than one thread"
    assert "threads" in out
    assert "only the main thread was compared" in out
    # both sides are multi-threaded here; each side's own note must fire
    # independently, not just whichever one happens to be checked first
    assert "A recorded" in out and "B recorded" in out


def test_diff_thread_note_is_per_side_not_shared(tmp_path, monkeypatch,
                                                  capsys):
    """One multi-threaded side and one single-threaded side: only the
    multi-threaded side's note may appear, and it must name the right
    letter -- a note keyed to the wrong side would misdirect a reader
    straight at the trace that is NOT the one with extra threads."""
    threaded = record(tmp_path, monkeypatch, THREADED_SWALLOWS)
    plain = _rec(tmp_path, "b", ["500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))

    cli.main(["diff", threaded, plain])
    out = capsys.readouterr().out
    assert "A recorded" in out
    assert "B recorded" not in out

    cli.main(["diff", plain, threaded])
    out = capsys.readouterr().out
    assert "B recorded" in out
    assert "A recorded" not in out


def test_diff_negative_context_does_not_crash(tmp_path, monkeypatch, capsys):
    """A negative --context must not turn into a reversed or wrapped slice;
    it degrades to showing no common history, not garbage."""
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["1500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2, "--context", "-5"]) == 1
    out = capsys.readouterr().out
    assert "common" not in out
    assert "silver" in out and "gold" in out


def test_compare_reports_which_side_ran_out_when_lengths_differ(
        tmp_path, monkeypatch):
    """`i == len(shorter_stream)` is the boundary the index-bounds guard
    exists for: the shorter side must render as "(stream ended)" with no
    event to drill into, not raise IndexError and not be silently treated
    as still having a step at that position."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    wa = TraceWriter(paths.traces_dir() / "20260101-000000-shorta.db")
    wa.set_meta("run_id", "20260101-000000-shorta")
    wa.set_meta("argv", ["prog.py"])
    ca = wa.intern_code("/tmp/prog.py", "main", 1)
    wa.add_event(0, 1, "CALL", None, ca, 1, {"args": {}})
    wa.close()

    wb = TraceWriter(paths.traces_dir() / "20260101-000000-shortb.db")
    wb.set_meta("run_id", "20260101-000000-shortb")
    wb.set_meta("argv", ["prog.py"])
    cb = wb.intern_code("/tmp/prog.py", "main", 1)
    wb.add_event(0, 1, "CALL", None, cb, 1, {"args": {}})
    cb2 = wb.intern_code("/tmp/prog.py", "helper", 3)
    wb.add_event(0, 1, "CALL", None, cb2, 2, {"args": {}})
    wb.close()

    ta = Trace.open(paths.find_trace("20260101-000000-shorta"))
    tb = Trace.open(paths.find_trace("20260101-000000-shortb"))
    res = compare(ta, tb)
    assert res["verdict"] == "DIVERGED"
    assert res["index"] == 1
    assert res["a_event"] is None
    assert res["a_desc"] == "(stream ended)"
    assert res["b_event"] is not None
    assert "helper" in res["b_desc"]

    reverse = compare(tb, ta)
    assert reverse["verdict"] == "DIVERGED"
    assert reverse["index"] == 1
    assert reverse["b_event"] is None
    assert reverse["b_desc"] == "(stream ended)"
    assert reverse["a_event"] is not None


# -- diff: the refusal contract ----------------------------------------------

def test_diff_refuses_an_incomplete_trace(tmp_path, monkeypatch, capsys):
    """The single most important behaviour: a truncated stream must never
    be reported as DIVERGED (or MATCH) -- only refused, loudly."""
    good = _rec(tmp_path, "a", ["500"])
    w = _synthetic(tmp_path, monkeypatch, "20260101-000000-incmpl")
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["diff", good, "20260101-000000-incmpl"]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "INCOMPLETE" in out
    assert "verdict: MATCH" not in out
    assert "verdict: DIVERGED" not in out


def test_diff_refuses_when_either_side_is_incomplete_regardless_of_order(
        tmp_path, monkeypatch, capsys):
    good = _rec(tmp_path, "a", ["500"])
    w = _synthetic(tmp_path, monkeypatch, "20260101-000000-incmpl")
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["diff", "20260101-000000-incmpl", good]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and "INCOMPLETE" in out


def test_diff_refuses_a_trace_with_dropped_late_writes(
        tmp_path, monkeypatch, capsys):
    """late_writes > 0 means events are missing even though the run
    finalized cleanly -- it must be refused exactly like an incomplete
    trace, not silently trusted because incomplete is False."""
    good = _rec(tmp_path, "a", ["500"])
    w = _synthetic(tmp_path, monkeypatch, "20260101-000000-latewr")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("late_writes", 3)
    w.close()

    assert cli.main(["diff", good, "20260101-000000-latewr"]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "late_writes" in out or "late write" in out
    assert "verdict: MATCH" not in out
    assert "verdict: DIVERGED" not in out


def test_diff_says_nothing_about_late_writes_when_zero(
        tmp_path, monkeypatch, capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2]) == 0
    out = capsys.readouterr().out
    assert "late_writes" not in out and "late write" not in out


def test_compare_returns_refused_without_touching_causal_stream(
        tmp_path, monkeypatch):
    """`compare()` is the seam Task 15's refocus reuses -- it must refuse
    before ever calling `causal_stream()` on an unsafe trace, not merely
    hedge the printed text around a computed (and possibly bogus) result."""
    good = _rec(tmp_path, "a", ["500"])
    w = _synthetic(tmp_path, monkeypatch, "20260101-000000-incmpl2")
    w.set_meta("incomplete", True)
    w.close()

    ta = Trace.open(paths.find_trace(good))
    tb = Trace.open(paths.find_trace("20260101-000000-incmpl2"))
    res = compare(ta, tb)
    assert res["verdict"] == "REFUSED"
    assert res["a_stream"] is None and res["b_stream"] is None
    assert res["index"] is None
    assert any("INCOMPLETE" in r for r in res["reasons"])
