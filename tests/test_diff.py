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
from sensorium.store import db
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import LEGACY_FORMAT, finalize_synthetic, run_cli
from tests.programs import THREADED_SWALLOWS, record
from tests.refocus_programs import JOINED_UNTRACED_WORKER

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
    # both sides are real, freshly-recorded traces -- basis is "recorded"
    # on both, so the verdict is entitled to say "the main thread" plainly
    verdict_line = next(ln for ln in out.splitlines()
                        if ln.startswith("verdict:"))
    assert "the main thread" in verdict_line
    assert "the thread named above" not in verdict_line


def test_diff_header_handles_a_trace_with_zero_events(tmp_path, monkeypatch,
                                                       capsys):
    """No events at all -- main_thread_id() is None, and the header must
    say so plainly rather than crash trying to look up a basis label for a
    thread that was never identified."""
    good = _rec(tmp_path, "a", ["500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    w = TraceWriter(paths.traces_dir() / "20260101-000000-empty.db")
    w.set_meta("run_id", "20260101-000000-empty")
    w.set_meta("argv", ["prog.py", "500"])
    w.close()

    assert cli.main(["diff", good, "20260101-000000-empty"]) == 1
    out = capsys.readouterr().out
    assert "compared: - (no events)" in out
    assert "DIVERGED" in out


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
    assert "only the thread named above was compared" in out
    # this trace was recorded after main_thread_ident landed, so the thread
    # actually compared must be identified as a recorded fact, not a guess
    assert "recorded main thread" in out
    assert "INFERRED" not in out
    # both sides are multi-threaded here; each side's own note must fire
    # independently, not just whichever one happens to be checked first
    assert "A recorded" in out and "B recorded" in out


def test_diff_match_does_not_assert_main_thread_when_inferred(
        tmp_path, monkeypatch, capsys):
    """Both sides are legacy-shaped (no meta["main_thread_ident"], as a
    trace recorded before that key existed would be) and each one's
    inferred thread happens to log a worker CALL first -- so the thread
    diff actually compares is a GUESS, not a recorded fact. The verdict
    line must say so: MATCH is still the right verdict (the two guessed
    streams are identical), but it must not claim "the main thread" when
    neither side's identification of that thread is anything more than an
    inference that names the wrong thread by construction here."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))

    def _legacy(run_id):
        w = TraceWriter(paths.traces_dir() / f"{run_id}.db")
        w.set_meta("run_id", run_id)
        w.set_meta("argv", ["prog.py"])
        c = w.intern_code("/tmp/prog.py", "worker_fn", 1)
        m = w.intern_code("/tmp/prog.py", "main", 5)
        w.add_event(0, 999, "CALL", None, c, 1, {"args": {}})   # worker: id 1
        w.add_event(0, 7, "CALL", None, m, 5, {"args": {}})     # main: id 2
        w.close()

    _legacy("20260101-000000-legacya")
    _legacy("20260101-000000-legacyb")
    ta = Trace.open(paths.find_trace("20260101-000000-legacya"))
    assert ta.main_thread_basis() == "inferred"    # precondition
    assert ta.main_thread_id() == 999              # names the worker, not main

    assert cli.main(["diff", "20260101-000000-legacya",
                     "20260101-000000-legacyb"]) == 0
    out = capsys.readouterr().out
    verdict_line = next(ln for ln in out.splitlines()
                        if ln.startswith("verdict:"))
    assert "MATCH" in verdict_line
    assert "the thread named above" in verdict_line
    assert "the main thread" not in verdict_line
    assert out.count("INFERRED main thread") == 2   # both header lines
    assert "A's compared thread is INFERRED" in out
    assert "B's compared thread is INFERRED" in out


def _rec_worker(tmp_path, payload):
    (tmp_path / "prog.py").write_text(JOINED_UNTRACED_WORKER)
    (tmp_path / "payload.txt").write_text(payload)
    r = run_cli(["run", "--", "prog.py"], cwd=tmp_path,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def test_diff_notes_a_worker_thread_that_left_no_fingerprint(
        tmp_path, monkeypatch, capsys):
    """The thread counting fingerprints cannot see. This worker's body is
    entirely stdlib, so it produces no fingerprint row, and it is joined
    before the run ends, so it is gone from `live_threads` too -- while it
    copies a differently-sized file in each run. `diff` printed `threads 1`,
    a clean MATCH and NO note on the very pair of traces `refocus` refuses
    to license, citing "started 1 thread(s) besides the main one"."""
    r1 = _rec_worker(tmp_path, "1234")
    r2 = _rec_worker(tmp_path, "1234567890" * 2)
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    ta = Trace.open(paths.find_trace(r1))
    assert len(ta.fingerprints()) == 1        # invisible to the old count...
    assert ta.meta["threads_started"] == 1    # ...and visible only to this one

    assert cli.main(["diff", r1, r2]) == 0    # the causal streams do match
    out = capsys.readouterr().out
    note = next(l for l in out.splitlines() if l.startswith("note: A recorded"))
    assert "1 started through Python's own threading/_thread" in note
    assert "1 left a fingerprint" in note
    assert "not a MATCH on the whole run" in note


def test_diff_notes_a_thread_the_creation_count_could_never_have_seen(
        tmp_path, monkeypatch, capsys):
    """The other half of the condition. A thread started outside Python's
    own `_thread` -- a C extension calling `pthread_create` -- is counted by
    nobody, but if it runs traced Python it still leaves a fingerprint. A
    `threads_started` of 0 must not silence that row."""
    def build(run_id):
        w = _synthetic(tmp_path, monkeypatch, run_id)
        w.set_meta("threads_started", 0)
        w.add_event(0, 555, "CALL", None, 1, 1, {"args": {}})
        w.write_fingerprint(1, "aaaaaaaaaaaa", 1)
        w.write_fingerprint(555, "bbbbbbbbbbbb", 1)
        w.close()

    build("20260101-000000-ctypea")
    build("20260101-000000-ctypeb")
    assert cli.main(["diff", "20260101-000000-ctypea",
                     "20260101-000000-ctypeb"]) == 0
    note = next(l for l in capsys.readouterr().out.splitlines()
                if l.startswith("note: A recorded"))
    assert "0 started through Python's own threading/_thread" in note
    assert "2 left a fingerprint" in note


def test_diff_says_it_cannot_count_threads_on_a_trace_that_predates_the_count(
        tmp_path, monkeypatch, capsys):
    """A trace with no `threads_started` key must not read as a run that
    started no threads -- the same rule `refocus` applies to the same key."""
    _synthetic(tmp_path, monkeypatch, "20260101-000000-olda").close()
    _synthetic(tmp_path, monkeypatch, "20260101-000000-oldb").close()
    assert cli.main(["diff", "20260101-000000-olda",
                     "20260101-000000-oldb"]) == 0
    out = capsys.readouterr().out
    for label in ("A", "B"):
        note = next(l for l in out.splitlines()
                    if l.startswith(f"note: {label} predates"))
        assert "absence of the record is not a record of absence" in note


def test_diff_names_a_declared_but_incomplete_recording_in_the_note(
        tmp_path, monkeypatch, capsys):
    """Today's Python recorder writes `capabilities` (all True) at run
    start (`boot.install()`) and `threads_started` only at the finalize
    pass -- a still-incomplete recording declares `threads` True with the
    key still absent, and that must never read as "predates" (it does not
    predate the declaration; it just has not finished). The comparison must
    still be REFUSED: `incomplete` is true regardless of what the note
    says."""
    from sensorium.record.boot import CAPABILITIES
    run_id = "20260101-000000-inflight"
    w = _synthetic(tmp_path, monkeypatch, run_id)
    w.set_meta("capabilities", dict(CAPABILITIES))
    w.set_meta("recorder", "sensorium 9.9.9")
    w.set_meta("incomplete", True)
    w.close()
    assert cli.main(["diff", run_id, run_id]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out
    note = next(l for l in out.splitlines()
                if l.startswith("note: A's recorder"))
    assert ("declares threads witnessed, but this trace carries no thread "
            "record") in note
    assert "the recording did not finish, or the record was removed" in note
    assert "absence of the record is not a record of absence" in note
    assert "predates" not in note


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

    assert cli.main(["diff", good, "20260101-000000-incmpl"]) == 3
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

    assert cli.main(["diff", "20260101-000000-incmpl", good]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out and "INCOMPLETE" in out


def test_diff_refuses_a_trace_with_dropped_late_writes(
        tmp_path, monkeypatch, capsys):
    """late_writes > 0 means events are missing even though the run
    finalized cleanly -- it must be refused exactly like an incomplete
    trace, not silently trusted because incomplete is False."""
    good = _rec(tmp_path, "a", ["500"])
    w = _synthetic(tmp_path, monkeypatch, "20260101-000000-latewr")
    finalize_synthetic(w)
    w.set_meta("exit_status", 0)
    w.set_meta("late_writes", 3)
    w.close()

    assert cli.main(["diff", good, "20260101-000000-latewr"]) == 3
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


# -- asyncio tasks: compared by content, never by interleaving -------------

ASYNC_SHAPE = """
import asyncio, sys

def step(n):
    return n

def other(n):
    return -n

async def worker(name, flip):
    step(1)
    await asyncio.sleep(0)
    if flip and name == "B":
        other(2)
    else:
        step(2)

async def amain(order, flip):
    names = ["A", "B"] if order == "AB" else ["B", "A"]
    tasks = [asyncio.create_task(worker(n, flip), name=f"task-{n}")
             for n in names]
    await asyncio.gather(*tasks)

def main():
    order, flip = sys.argv[1], sys.argv[2] == "flip"
    asyncio.run(amain(order, flip))

main()
"""

# The same program with the names dropped: asyncio then names every task
# `Task-<N>` from a process-global counter, i.e. by creation order.
UNNAMED_SHAPE = ASYNC_SHAPE.replace('name=f"task-{n}"', "name=None")

DUP_TASK_NAMES = """
import asyncio

def step(n):
    return n

async def worker():
    step(1)

async def amain():
    await asyncio.gather(asyncio.create_task(worker(), name="dup"),
                         asyncio.create_task(worker(), name="dup"))

asyncio.run(amain())
"""


def _rec_prog(tmp_path, src, argv=()):
    """Record one run of `src`, from `tmp_path` itself -- like `_rec`, and
    deliberately not from a per-run subdirectory: a causal stream is
    (file, qualname, kind), so two runs of the same program recorded from
    different directories diverge at step 0 on the absolute path alone."""
    (tmp_path / "prog.py").write_text(src)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", "--", "prog.py", *argv], cwd=tmp_path,
                sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def _rec_async(tmp_path, argv):
    return _rec_prog(tmp_path, ASYNC_SHAPE, argv)


def test_diff_matches_two_runs_whose_tasks_interleaved_differently(
        tmp_path, monkeypatch, capsys):
    a = _rec_async(tmp_path, ["AB", "same"])
    b = _rec_async(tmp_path, ["BA", "same"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b]) == 0
    out = capsys.readouterr().out
    assert "verdict: MATCH" in out
    assert "tasks: 3 task stream(s) on each side, compared by content" in out
    assert "all matched" in out
    assert "the ordering between tasks is not compared" in out


def test_diff_names_the_task_that_took_another_path(tmp_path, monkeypatch,
                                                    capsys):
    a = _rec_async(tmp_path, ["AB", "same"])
    b = _rec_async(tmp_path, ["AB", "flip"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b]) == 1
    out = capsys.readouterr().out
    assert ("verdict: MATCH on the thread stream (4 events); DIVERGED on "
            "the tasks (below)") in out
    assert "tasks: DIVERGED" in out
    assert "task-B" in out
    assert "only in A:" in out and "only in B:" in out
    assert "first difference inside task-B" in out
    assert "A:      " in out and "step" in out
    assert "B:      " in out and "other" in out
    assert f"drill into A: sensorium tree {a} --around e" in out
    assert f"drill into B: sensorium tree {b} --around e" in out
    # task-A matched and is not listed as differing
    assert "task-A" not in out.split("tasks: DIVERGED", 1)[1].split(
        "first difference", 1)[0]


def test_diff_task_flag_compares_one_named_task(tmp_path, monkeypatch,
                                                capsys):
    a = _rec_async(tmp_path, ["AB", "same"])
    b = _rec_async(tmp_path, ["BA", "flip"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b, "--task", "task-A"]) == 0
    out = capsys.readouterr().out
    assert "compared: task task-A" in out
    assert "verdict: MATCH" in out
    capsys.readouterr()
    assert cli.main(["diff", a, b, "--task", "task-B"]) == 1
    out = capsys.readouterr().out
    assert "verdict: DIVERGED at causal step" in out
    assert "other" in out


def test_diff_task_flag_refuses_an_unknown_name(tmp_path, monkeypatch,
                                                capsys):
    a = _rec_async(tmp_path, ["AB", "same"])
    b = _rec_async(tmp_path, ["AB", "same"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b, "--task", "nope"]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out and "no task named 'nope'" in out
    assert "task-A, task-B" in out


def test_diff_task_flag_refuses_a_name_that_picks_two_tasks(
        tmp_path, monkeypatch, capsys):
    """A name that two tasks share picks neither: comparing "the" dup task
    would silently pick one of them by creation order -- the very thing the
    task comparison exists not to do."""
    a = _rec_prog(tmp_path, DUP_TASK_NAMES)
    b = _rec_prog(tmp_path, DUP_TASK_NAMES)
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b, "--task", "dup"]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert "'dup' names 2 tasks on A" in out
    assert "exactly one" in out


def test_diff_unnamed_tasks_match_only_unnamed_tasks(tmp_path, monkeypatch):
    from collections import Counter
    from sensorium.query.diff_cmd import _shape_difference
    a = Counter({(None, "h1"): 1, ("w", "h1"): 1})
    b = Counter({("w", "h1"): 2})
    only_a, only_b = _shape_difference(a, b)
    assert only_a == [(None, "h1", 1)] and only_b == [("w", "h1", 1)]


def test_diff_default_task_names_are_compared_as_unnamed(
        tmp_path, monkeypatch, capsys):
    """`Task-2` is not a name: asyncio hands it out from a process-global
    counter, so it says when the task was created and nothing else. Two runs
    that created the same tasks in the other order must still MATCH, and
    `--task Task-2` must refuse rather than compare creation slots.

    Both runs flip, so the two workers do DIFFERENT work from each other:
    A's `Task-2` did what B's `Task-3` did and vice versa. Reading the
    number as a name makes this pair DIVERGED on nothing but creation
    order -- which is the whole of Ruling 4."""
    a = _rec_prog(tmp_path, UNNAMED_SHAPE, ["AB", "flip"])
    b = _rec_prog(tmp_path, UNNAMED_SHAPE, ["BA", "flip"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b]) == 0
    out = capsys.readouterr().out
    assert "verdict: MATCH" in out
    assert "all matched" in out
    assert cli.main(["diff", a, b, "--task", "Task-2"]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert ("'Task-2' is asyncio's default name and encodes creation order, "
            "not identity") in out
    assert "asyncio.create_task(..., name=...)" in out


def test_diff_pairs_unnamed_tasks_by_creation_order_and_says_so(
        tmp_path, monkeypatch, capsys):
    """With no name shared between the unmatched streams there is nothing to
    match on, so the drill-in pairs the first unmatched unnamed stream on
    each side -- and labels that pairing a guide, not a match."""
    a = _rec_prog(tmp_path, UNNAMED_SHAPE, ["AB", "same"])
    b = _rec_prog(tmp_path, UNNAMED_SHAPE, ["AB", "flip"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b]) == 1
    out = capsys.readouterr().out
    assert "tasks: DIVERGED" in out
    assert "(unnamed)" in out
    assert "first difference inside (unnamed)" in out
    assert "(paired by creation order -- a guide, not a match)" in out
    assert "other" in out


def test_diff_refuses_to_compare_across_fingerprint_bases_when_tasks_ran(
        tmp_path, monkeypatch, capsys):
    from tests.test_format2_fixture import _installed
    from tests.test_format3_fixture import FIXTURE as OLD3
    old3 = _installed(tmp_path, monkeypatch, OLD3, "old3")
    new = _rec_async(tmp_path, ["AB", "same"])
    assert cli.main(["diff", old3, new]) == 3
    out = capsys.readouterr().out
    assert "verdict: REFUSED" in out
    assert ("recorded under different fingerprint bases "
            "(A: per-thread, B: per-task): the per-thread side's thread "
            "stream includes its task events, which this version compares "
            "separately") in out
    assert "re-record" in out


def test_diff_by_name_on_a_per_thread_trace_names_the_missing_table(
        tmp_path, monkeypatch, capsys):
    """`--task NAME` against a 0.3.0 trace. That trace is not short of task
    STREAMS -- its events carry task ids and it ran three tasks; what it
    lacks is the `task_fingerprints` table this version resolves a name
    through. "It has no task stream to compare by name" described the
    recording as emptier than it is."""
    from tests.test_format2_fixture import _installed
    from tests.test_format3_fixture import FIXTURE as OLD3
    old3 = _installed(tmp_path, monkeypatch, OLD3, "old3")
    assert cli.main(["diff", old3, old3, "--task", "task-A"]) == 3
    out = capsys.readouterr().out
    assert "verdict: REFUSED" in out
    for label in ("A", "B"):
        assert (f"{label} recorded 3 asyncio task(s) and no "
                "task_fingerprints rows: this version resolves task names "
                "through task_fingerprints, which the recording's version "
                "did not write -- re-record it to compare by name") in out
    assert "has no task stream" not in out


def test_diff_compares_across_bases_when_neither_side_ran_a_task(
        tmp_path, monkeypatch, capsys):
    """No task anywhere: both definitions coincide, so nothing is refused."""
    a = _rec(tmp_path, "a", ["100"])
    sdir = tmp_path / "sdir"
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    import sqlite3
    c = sqlite3.connect(sdir / "traces" / f"{a}.db")
    c.execute("DELETE FROM meta WHERE key='fingerprint_basis'")
    # format 4 requires the key on a finalized trace, so a fixture that
    # removes it has to claim the older format it is imitating.
    db.set_meta(c, "trace_format", LEGACY_FORMAT)
    c.commit(); c.close()
    b = _rec(tmp_path, "b", ["100"])
    assert cli.main(["diff", a, b]) == 0
    assert "REFUSED" not in capsys.readouterr().out


def _task_only(run_id, task_hash, name="task-A"):
    """A synthetic trace whose ONLY causal event ran inside a task, so its
    thread stream is empty under the per-task basis. Not reachable through
    the CLI (the target module is always traced), and the honest wording
    for it still has to be pinned by something."""
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db")
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    w.set_meta("main_thread_ident", 1)
    w.set_meta("fingerprint_basis", "per-task")
    finalize_synthetic(w)
    w.set_meta("threads_started", 0)
    w.add_task(1, name, 1)
    c = w.intern_code("/tmp/prog.py", "worker", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}}, task_id=1)
    w.write_task_fingerprint(1, task_hash, 1)
    w.close()
    return run_id


def test_diff_does_not_call_an_empty_thread_stream_identical(
        tmp_path, monkeypatch, capsys):
    """`compare()` refuses two empty thread streams only when no task ran
    either -- with tasks there IS something to compare, which makes an empty
    thread stream reachable for the first time. The thread line must not
    report "identical causal streams" over zero events: that is the verdict
    about nothing this command refuses everywhere else."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    ids = [_task_only(r, "a" * 32)
           for r in ("20260101-000000-tonlya", "20260101-000000-tonlyb")]
    assert cli.main(["diff", *ids]) == 0
    out = capsys.readouterr().out
    assert "identical causal streams" not in out
    assert "no causal event ran outside a task on either side" in out
    assert "tasks: 1 task stream(s) on each side" in out


def test_diff_does_not_claim_a_match_on_an_empty_thread_stream_either(
        tmp_path, monkeypatch, capsys):
    """The tasks-DIVERGED branch prints the thread verdict too, and it must
    be as honest as the MATCH one: "MATCH on the thread stream (0 events)"
    claims agreement about a stream that held nothing."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    a = _task_only("20260101-000000-tonlyc", "a" * 32)
    b = _task_only("20260101-000000-tonlyd", "b" * 32)
    assert cli.main(["diff", a, b]) == 1
    out = capsys.readouterr().out
    assert "MATCH on the thread stream (0 events)" not in out
    assert ("verdict: the thread stream held no causal events on either "
            "side; DIVERGED on the tasks (below)") in out
    assert "tasks: DIVERGED" in out


def test_diff_refuses_a_per_task_trace_whose_task_fingerprints_are_missing(
        tmp_path, monkeypatch, capsys):
    """A trace that ran tasks under the per-task basis but recorded no task
    fingerprint rows is not a trace with no tasks: its thread stream was
    NARROWED to exclude the task events (the basis marker is meta, and
    `causal_stream()` reads it), so comparing it reports a confident MATCH
    about the module scaffolding of a run whose work all happened inside
    tasks. Traces in exactly this state exist on disk -- the writer wrote
    zero task fingerprint rows for every CLI recording until this arc."""
    a = _rec_async(tmp_path, ["AB", "same"])
    b = _rec_async(tmp_path, ["AB", "same"])
    sdir = tmp_path / "sdir"
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    import sqlite3
    c = sqlite3.connect(sdir / "traces" / f"{a}.db")
    c.execute("DELETE FROM task_fingerprints")
    c.commit(); c.close()

    assert cli.main(["diff", a, b]) == 3
    out = capsys.readouterr().out
    assert "verdict: REFUSED" in out
    assert "verdict: MATCH" not in out
    assert ("A ran 3 asyncio task(s) but recorded no task fingerprints") in out
    assert "re-record it with this version" in out

    assert cli.main(["diff", a, b, "--task", "task-A"]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out
    assert ("A ran 3 asyncio task(s) but recorded no task fingerprints") in out
    # ...and not the misleading "no task named 'task-A' on A (A has: -)".
    assert "no task named" not in out


def test_diff_default_name_pattern_ignores_a_trailing_newline():
    """`^Task-\\d+$` also matches "Task-1\\n" -- `$` matches before a final
    newline. A task actually named that has a name of its own, and dropping
    it would erase content the comparison is supposed to compare."""
    from sensorium.query.diff_cmd import _unnamed
    assert _unnamed(None) and _unnamed("Task-1") and _unnamed("Task-12")
    assert not _unnamed("Task-1\n")
    assert not _unnamed("task-1") and not _unnamed("Task-") and \
        not _unnamed("xTask-1")


def test_diff_refuses_a_trace_whose_record_sequence_has_holes(
        tmp_path, monkeypatch, capsys):
    """A Rust trace declares its losses as `seq_gaps` (a minted record no
    spool holds) and `records_dropped` (a write the runtime knew it lost).
    Neither is `late_writes`, and a `diff` that read only the key it knew
    would issue a verdict over a hole the trace itself declares."""
    good = _rec(tmp_path, "a", ["500"])
    w = _synthetic(tmp_path, monkeypatch, "20260101-000000-seqgap")
    finalize_synthetic(w)
    w.set_meta("exit_status", 0)
    w.set_meta("records_dropped", {})
    w.set_meta("seq_gaps", 2)
    w.close()

    assert cli.main(["diff", good, "20260101-000000-seqgap"]) == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out and "dropped >=2 trace write(s)" in out
    assert "verdict: MATCH" not in out and "verdict: DIVERGED" not in out
