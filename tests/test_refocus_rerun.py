"""`refocus` the re-run itself: whether it may happen, where it happens,
and the one line it prints per finding.

The other half of `test_refocus`, split at that file's own `# -- refusals`
banner on 2026-09-08 to bring both halves under the 800-line ceiling. The
first file covers the VERDICT -- MATCH, DIVERGED, tasks compared by content,
what the verdict may be added to; this one covers everything about the RERUN:
the originals it refuses to re-run at all, the store and working directory the
rerun happens in, and how one finding renders as exactly one line. The
recording fixtures are `tests/refocus_programs.py`'s, as in the first file.
"""
import os

import pytest

from sensorium import cli
from tests.refocus_programs import (ASYNC_CONTENT_FLIP, ASYNC_ORDER_FLIP,
                                    EXIT_FROM_FILE, LIB_TASKS, LOOP,
                                    READS_STDIN, SLEEPER, TASKS_ON_RERUN_ONLY,
                                    WORKER_ON_SECOND_RUN, dbs, new_run, rec,
                                    record_killed, refocus, set_meta,
                                    synthetic, trace)


# -- refusals ---------------------------------------------------------------

def test_refocus_refuses_a_stdin_consuming_original(tmp_path):
    run_id, sdir = rec(tmp_path, READS_STDIN, stdin_text="hello\n")
    assert trace(sdir, run_id).meta["stdin_consumed"] is True
    before = dbs(sdir)

    r = refocus(sdir, run_id, "--focus", "prog:main")
    assert r.returncode == 2
    assert "stdin" in r.stderr and "non-refocusable" in r.stderr
    assert "no rerun was attempted" in r.stderr
    assert dbs(sdir) == before, "a refusal must not re-run the program"


def test_refocus_refuses_an_incomplete_original(tmp_path):
    """An incomplete trace never got its finalize pass, so it never recorded
    whether the run consumed stdin: the stdin gate would read the missing
    key as False and wave through exactly the run it exists to stop."""
    sdir = record_killed(tmp_path, SLEEPER)
    [db_name] = dbs(sdir)
    m = trace(sdir, db_name[:-3]).meta
    assert m["incomplete"] is True
    assert "stdin_consumed" not in m
    assert m["argv"] == ["prog.py"]           # boot-time meta did survive

    r = refocus(sdir, db_name[:-3], "--focus", "prog:spin")
    assert r.returncode == 2
    assert "INCOMPLETE" in r.stderr
    assert "stdin" in r.stderr
    assert dbs(sdir) == [db_name]


def test_refocus_refuses_when_the_target_no_longer_resolves(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    (tmp_path / "prog.py").unlink()
    before = dbs(sdir)

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 2
    assert "cannot resolve target" in r.stderr
    assert dbs(sdir) == before


def test_refocus_refuses_when_the_original_cwd_is_gone(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    gone = tmp_path / "deleted-since"
    set_meta(sdir / "traces" / f"{run_id}.db", cwd=str(gone))
    before = dbs(sdir)

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 2
    assert "no longer exists" in r.stderr and str(gone) in r.stderr
    assert dbs(sdir) == before


@pytest.mark.parametrize("kwargs, expected", [
    ({"argv": None, "cwd": "/tmp"}, "records no command to re-run"),
    ({"cwd": None}, "records no working directory to re-run from"),
])
def test_refocus_refuses_a_trace_with_nothing_to_re_run(tmp_path, kwargs,
                                                        expected):
    """Corrupt or hand-built metadata is a refusal, never a traceback: an
    agent parsing this output is worse served by a stack trace than a
    human is."""
    sdir = tmp_path / "sdir"
    synthetic(sdir, "20260101-000000-broken", **kwargs)

    r = refocus(sdir, "20260101-000000-broken", "--focus", "prog:main")
    assert r.returncode == 2
    assert expected in r.stderr
    assert "Traceback" not in r.stderr


def test_refocus_refuses_a_per_thread_basis_original_that_ran_tasks(tmp_path):
    """A trace recorded before task fingerprints existed defines its thread
    stream to INCLUDE the events that ran inside asyncio tasks; this version
    defines it to exclude them and compares the tasks separately. A verdict
    across that seam would not compare like with like -- and the refusal has
    to come BEFORE the rerun, because re-running has side effects and
    nothing about the answer could be salvaged afterwards. Everything else
    about this original is fine: its command resolves and its directory is
    still there, so the basis is the only thing stopping it."""
    sdir = tmp_path / "sdir"
    (tmp_path / "prog.py").write_text(LOOP)
    synthetic(sdir, "20260101-000000-old", cwd=tmp_path, tasks=[(1, "t", 1)])
    before = dbs(sdir)

    r = refocus(sdir, "20260101-000000-old", "--focus", "prog:accumulate")
    assert r.returncode == 2, r.stdout + r.stderr
    assert ("original was recorded under the per-thread fingerprint basis "
            "and ran 1 asyncio task(s); this version compares tasks by "
            "content and defines thread streams without them, so no verdict "
            "against it would compare like with like -- re-record it with "
            "this version") in r.stderr
    assert "no rerun was attempted" in r.stderr
    assert dbs(sdir) == before, "a refusal must not re-run the program"


def test_refocus_requires_a_focus(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id)
    assert r.returncode == 2
    assert "--focus" in r.stderr


def test_refocus_rejects_an_unknown_run_reference(tmp_path):
    rec(tmp_path, LOOP)
    r = refocus(tmp_path / "sdir", "no-such-run", "--focus", "prog:main")
    assert r.returncode == 2
    assert "error:" in r.stderr and "no trace matches" in r.stderr


# -- the process the rerun happens in ---------------------------------------

def test_refocus_keeps_the_rerun_in_the_same_trace_store(tmp_path):
    """A relative SENSORIUM_DIR must not follow the chdir into the original
    cwd and strand the new trace in a store nobody will look in."""
    run_id, sdir = rec(tmp_path, LOOP)
    runner = tmp_path / "runner"
    runner.mkdir()

    r = refocus(sdir, run_id, "--focus", "prog:accumulate",
                cwd=runner, sensorium_dir="../sdir")
    assert r.returncode == 0, r.stdout + r.stderr
    new_id = new_run(r.stdout)
    assert (sdir / "traces" / f"{new_id}.db").exists()
    assert not (tmp_path.parent / "sdir").exists()


def test_refocus_restores_the_working_directory(tmp_path, monkeypatch,
                                                capsys):
    """`refocus` chdirs into the original run's cwd; an in-process caller
    must get its own directory back afterwards."""
    run_id, sdir = rec(tmp_path, LOOP)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = os.getcwd()
    monkeypatch.chdir(before)         # restore even if the assert below trips

    assert cli.main(["refocus", run_id, "--focus", "prog:accumulate"]) == 0
    assert os.getcwd() == before
    assert "refocus verdict: MATCH" in capsys.readouterr().out


def test_refocus_reports_a_differing_exit_status(tmp_path):
    """The exit code of `refocus` is the VERDICT, never the program's own."""
    run_id, sdir = rec(tmp_path, EXIT_FROM_FILE)
    r = refocus(sdir, run_id, "--focus", "prog:attempt")
    assert "refocus verdict: MATCH" in r.stdout, r.stdout + r.stderr
    assert r.returncode == 0
    assert "exit: rerun 1   original 0" in r.stdout


def test_refocus_counts_uncompared_threads_from_the_side_that_had_them(
        tmp_path):
    """The two sides can be asymmetric: this worker starts only on the
    rerun. Counting the uncompared threads from the SMALLER side would
    report none at all, so the reader would never learn that a thread ran
    which nothing compared."""
    run_id, sdir = rec(tmp_path, WORKER_ON_SECOND_RUN)
    assert trace(sdir, run_id).meta["threads_started"] == 0   # none yet

    r = refocus(sdir, run_id, "--focus", "prog:maybe_worker")
    assert r.returncode == 0, r.stdout + r.stderr
    new = trace(sdir, new_run(r.stdout))
    assert new.meta["threads_started"] == 1        # the rerun started one
    assert len(new.fingerprints()) == 1            # and it left no fingerprint

    assert "1 further thread(s) ran no traced code" in r.stdout
    assert "were NOT compared" in r.stdout
    assert "licence: WITHHELD" in r.stdout


# -- one finding, one line -------------------------------------------------

def _task_lines(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("tasks:")]


def test_refocus_prints_exactly_one_tasks_line_on_a_match(tmp_path):
    """`diff.print_comparison` prints a `tasks:` line and so does `refocus`.
    Two lines saying different amounts about one finding read as two
    findings, so `refocus` asks `print_comparison` not to print its own."""
    run_id, sdir = rec(tmp_path, ASYNC_ORDER_FLIP)
    r = refocus(sdir, run_id, "--focus", "prog:worker")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _task_lines(r.stdout) == [
        "tasks: 3 task stream(s) compared by content, all matching; the "
        "ordering between tasks is not compared"]


def test_refocus_prints_exactly_one_tasks_line_and_keeps_the_drill_ins(
        tmp_path):
    """The DIVERGED half. The surviving line is the one `refocus` stamps into
    the trace, so the terminal and `sensorium info` say the same words -- and
    the drill-in commands travel with it rather than being lost with diff's
    section."""
    run_id, sdir = rec(tmp_path, ASYNC_CONTENT_FLIP)
    r = refocus(sdir, run_id, "--focus", "prog:worker")
    assert r.returncode == 1, r.stdout + r.stderr
    lines = _task_lines(r.stdout)
    assert len(lines) == 1, lines
    assert lines[0].startswith("tasks: DIVERGED -- ")
    assert "first difference inside task-B" in lines[0]
    new_id = new_run(r.stdout)
    assert lines[0] == ("tasks: DIVERGED -- "
                        + trace(sdir, new_id).meta["refocus_diverge_tasks"])
    drills = [ln for ln in r.stdout.splitlines() if ln.startswith("drill into")]
    assert len(drills) == 2, r.stdout
    assert drills[0].startswith(f"drill into A: sensorium tree {run_id} "
                                "--around e")
    assert drills[1].startswith(f"drill into B: sensorium tree {new_id} "
                                "--around e")


def test_refocus_says_which_side_ran_the_task_when_the_other_ran_none(
        tmp_path):
    """The wording "a task took a different path" presumes both sides ran
    one. Here the original ran no task at all, so there is no path to have
    differed -- and which side is missing is the whole finding."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "taskslib.py").write_text(LIB_TASKS)
    run_id, sdir = rec(tmp_path, TASKS_ON_RERUN_ONLY,
                       extra=["--exclude", "prog.py"])
    assert trace(sdir, run_id).tasks() == []              # precondition

    r = refocus(sdir, run_id, "--focus", "taskslib:worker")
    assert r.returncode == 1, r.stdout + r.stderr
    assert ("refocus verdict: DIVERGED -- the rerun ran a task stream the "
            "original did not.") in r.stdout
    assert "a task took a different path" not in r.stdout
    # The threads did NOT part: the finding is entirely about the tasks.
    assert "threads: DIVERGED" not in r.stdout
    assert ("threads: 1 recorded fingerprint(s) compared (events outside "
            "any asyncio task), all matching") in r.stdout
    lines = _task_lines(r.stdout)
    assert len(lines) == 1, lines
    # Counts and names pinned; the hashes are content and are not.
    assert lines[0].startswith(
        "tasks: DIVERGED -- 0 task stream(s) originally, 3 on the rerun; "
        "only in A: -; only in B: task-A "), lines[0]
    assert "task-B" in lines[0] and "(unnamed)" in lines[0]
