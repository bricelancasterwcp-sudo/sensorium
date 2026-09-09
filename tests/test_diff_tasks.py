"""`diff` over asyncio tasks: compared by content, never by interleaving.

The other half of `test_diff`, split at that file's own
`# -- asyncio tasks` banner on 2026-09-08 to bring both halves under the
800-line ceiling. Two runs of the same concurrent program schedule their
tasks in whatever order the loop chose that time, so every expectation here
is about a comparison that must survive a different interleaving -- which is
what separates it from the sequential material the first file covers. The
two recording helpers are the first file's, imported and never copied.
"""
import re

from sensorium import cli, paths
from sensorium.store import db
from sensorium.store.writer import TraceWriter
from tests.helpers import LEGACY_FORMAT, finalize_synthetic, run_cli
from tests.test_diff import _rec, _synthetic


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


def _task_only(run_id, task_hash, name="task-A", file="/tmp/prog.py"):
    """A synthetic trace whose ONLY causal event ran inside a task, so its
    thread stream is empty under the per-task basis. Not reachable through
    the CLI (the target module is always traced), and the honest wording
    for it still has to be pinned by something.

    `file` is a parameter so one qualname can be given two homes across a
    pair, which is what `--ignore-moves` pairs.
    """
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db")
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    w.set_meta("main_thread_ident", 1)
    w.set_meta("fingerprint_basis", "per-task")
    finalize_synthetic(w)
    w.set_meta("threads_started", 0)
    w.add_task(1, name, 1)
    c = w.intern_code(file, "worker", 1)
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


def test_the_all_in_tasks_match_says_modulo_location_when_it_was_lenient(
        tmp_path, monkeypatch, capsys):
    """One leniency, one word for it, on every branch that used it.

    The task streams below are compared through the SAME projection the
    thread streams use, so a verdict reached because a code object was
    paired across a move is `MATCH modulo location` on every other branch
    and read a flat `MATCH` here -- on the one branch where the tasks carry
    the whole verdict, so the leniency was hidden exactly where it decided
    the most.
    """
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    a = _task_only("20260101-000000-mvonla", "a" * 32)
    b = _task_only("20260101-000000-mvonlb", "a" * 32, file="/tmp/moved.py")
    assert cli.main(["diff", "--ignore-moves", a, b]) == 0
    out = capsys.readouterr().out
    assert ("verdict: MATCH modulo location -- no causal event ran outside "
            "a task on either side, so the thread streams held nothing to "
            "compare; the tasks below carry the whole verdict\n") in out, out


def test_the_all_in_tasks_match_stays_flat_when_nothing_was_paired(
        tmp_path, monkeypatch, capsys):
    """The fence on the line above: `--ignore-moves` with nothing to pair
    is not a leniency, and hedging an exact agreement reads as one."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    ids = [_task_only(r, "a" * 32)
           for r in ("20260101-000000-mvsama", "20260101-000000-mvsamb")]
    assert cli.main(["diff", "--ignore-moves", *ids]) == 0
    out = capsys.readouterr().out
    assert "modulo location" not in out, out
    assert "verdict: MATCH -- no causal event ran outside a task" in out, out


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
