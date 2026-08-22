import sys

import pytest

from sensorium import cli, paths
from sensorium.record import boot
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script
from tests.programs import synthetic
from tests.refocus_programs import (ASYNC_CONTENT_FLIP, COUNTER, new_run, rec,
                                    refocus)
from tests.test_async import TWO_TASKS

# TWO_TASKS defines main() and no entry point; `record_script` runs the file.
TWO_TASKS_PROG = TWO_TASKS + '\nif __name__ == "__main__":\n    main()\n'

SRC = """
def work(n):
    try:
        [1, 2][n]
    except IndexError:
        pass
    return n * "x" * 300

def main():
    for i in range(3):
        work(5)

if __name__ == "__main__":
    main()
"""


def _record(tmp_path, monkeypatch, extra=(), src=SRC):
    run_id, trace, r = record_script(tmp_path, src, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_runs_lists_recorded_trace(tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["runs"]) == 0
    out = capsys.readouterr().out
    assert run_id in out and "exit:0" in out and "prog.py" in out


def test_info_reports_shape_and_honesty(tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "exit: 0" in out
    assert "CALL" in out and "HANDLED" in out
    assert "truncated values:" in out          # 300-char strings force it
    assert "fingerprint" in out
    assert "work" in out                       # hot functions list
    assert "INCOMPLETE" not in out


def test_info_prefix_and_last_resolution(tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", "last"]) == 0
    assert run_id in capsys.readouterr().out


def test_unknown_run_is_exit_2(tmp_path, monkeypatch, capsys):
    _record(tmp_path, monkeypatch)
    assert cli.main(["info", "zzz-nope"]) == 2
    assert "no trace matches" in capsys.readouterr().err


# -- contract: meta["env"] holds the entire process environment. `info` must
# never print it wholesale -- only env_hash, never a raw env var.
def test_info_never_prints_the_raw_environment(tmp_path, monkeypatch, capsys):
    marker = "SENSORIUM_CANARY_VALUE_DO_NOT_PRINT"
    monkeypatch.setenv("SENSORIUM_CANARY", marker)
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert marker not in out
    assert "SENSORIUM_CANARY" not in out


# -- contract: a run whose install() failed has NO exit_status/uncaught keys
# at all -- info must gate on `incomplete` and print it prominently, not
# blow up on the missing keys and not bury the flag at the bottom.
def test_info_on_incomplete_trace_is_prominent_and_survives_missing_keys(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "prog.py").write_text("print('hi')\n")
    tool = sys.monitoring.PROFILER_ID
    sys.monitoring.use_tool_id(tool, "another-profiler")
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            boot.run_target(["prog.py"])
    finally:
        sys.monitoring.free_tool_id(tool)
    dbs = list(paths.traces_dir().glob("*.db"))
    assert len(dbs) == 1
    run_id = dbs[0].stem

    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert "INCOMPLETE" in lines[1]      # second line: unmissable, not buried
    assert "exit: ?" in out              # no exit_status key -- gated, no crash


# -- contract: late_writes is a lower bound, and must never be presented as
# an exact count; it must only show up when non-zero.
def test_info_surfaces_late_writes_as_a_lower_bound(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdef"
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    w.set_meta("cwd", str(tmp_path))
    w.set_meta("python", "3.12.0")
    w.set_meta("exit_status", 0)
    w.set_meta("incomplete", False)
    w.set_meta("late_writes", 3)
    w.set_meta("caps", {})
    w.close()

    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    line = next(l for l in out.splitlines() if "late writes" in l)
    assert line.startswith("late writes dropped: >=3")
    assert "3 more" not in line          # not phrased as an exact/complete count


def test_info_says_nothing_about_late_writes_when_zero(
        tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "late writes" not in out.lower()


# -- contract: a run whose recording died is labelled wherever it is listed,
# not only where it is inspected. `runs` is the ledger a reader scans before
# picking a trace, so an INCOMPLETE run that looks ordinary there gets
# queried as if its stream were whole.
def test_runs_labels_an_incomplete_trace_in_the_listing(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdef"
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    w.set_meta("cwd", str(tmp_path))
    w.set_meta("python", "3.12.0")
    w.set_meta("incomplete", True)
    w.set_meta("caps", {})
    w.close()

    assert cli.main(["runs"]) == 0
    line = next(l for l in capsys.readouterr().out.splitlines()
                if run_id in l)
    assert "INCOMPLETE" in line


def test_runs_says_the_store_is_empty_instead_of_printing_nothing(
        tmp_path, monkeypatch, capsys):
    """Silence would read as "the command did nothing", which is the one
    thing it did not do."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "empty-sdir"))
    assert cli.main(["runs"]) == 0
    assert capsys.readouterr().out.strip() == "no traces recorded"


# -- contract: a subprocess is OBSERVED, never witnessed. `info` must name it
# so a reader knows a piece of the execution happened outside the trace.
def test_info_names_a_subprocess_it_could_not_witness(
        tmp_path, monkeypatch, capsys):
    src = ("import subprocess, sys\n"
           "def main():\n"
           "    subprocess.run([sys.executable, '-c', 'pass'], check=True)\n"
           "if __name__ == '__main__':\n"
           "    main()\n")
    run_id, _trace, r = record_script(tmp_path, src)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))

    assert cli.main(["info", run_id]) == 0
    line = next((l for l in capsys.readouterr().out.splitlines()
                 if l.startswith("unwitnessed subprocess:")), None)
    assert line is not None, "the child process was not reported at all"
    assert "-c" in line and "pass" in line       # the command, not just a count


# -- contract: `children` is not the only thing the recorder notices being
# started. A multiprocessing 'spawn' child is visible ONLY as a spawn
# syscall, and threads only as `threads_started` -- and `refocus` withholds
# its licence on exactly those keys, so `info` reading only `children` made
# two commands answer one question differently.
SPAWNER = """
import os
import sys
import threading

def worker():
    return 1

def main():
    ts = [threading.Thread(target=worker) for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    pid = os.posix_spawn(sys.executable, [sys.executable, "-c", "pass"],
                         os.environ)
    os.waitpid(pid, 0)

if __name__ == "__main__":
    main()
"""


def _one(out: str, prefix: str) -> str:
    hits = [l for l in out.splitlines() if l.startswith(prefix)]
    assert len(hits) == 1, f"{prefix!r} matched {len(hits)} lines in:\n{out}"
    return hits[0]


def test_info_counts_threads_and_spawns_that_no_child_list_can_name(
        tmp_path, monkeypatch, capsys):
    run_id, _trace, r = record_script(tmp_path, SPAWNER)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))

    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    # `os.posix_spawn` is deliberately absent from the named-child table, so
    # this run has an EMPTY children list: without the two lines below the
    # trace's own record of it would be silence.
    assert "unwitnessed subprocess:" not in out
    assert _one(out, "threads started:").startswith("threads started: 3 ")
    assert _one(out, "spawn syscalls:").startswith("spawn syscalls: 1 ")


def test_info_says_nothing_about_threads_or_spawns_when_there_were_none(
        tmp_path, monkeypatch, capsys):
    """A printed `spawn syscalls: 0` would be read as proof no child ran,
    which is the one thing it does not prove -- same rule as late_writes."""
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "threads started:" not in out and "spawn syscalls:" not in out
    assert "audit hook errors:" not in out
    assert "not recorded in this trace:" not in out


def test_info_flags_a_trace_that_predates_the_bookkeeping(
        tmp_path, monkeypatch, capsys):
    """Absence of the record is not a record of absence: a trace with no
    `spawn_syscalls` key must not read like a run that spawned nothing."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdef"
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    for k, v in (("run_id", run_id), ("argv", ["prog.py"]),
                 ("cwd", str(tmp_path)), ("python", "3.12.0"),
                 ("exit_status", 0), ("incomplete", False), ("caps", {})):
        w.set_meta(k, v)
    w.close()

    assert cli.main(["info", run_id]) == 0
    line = _one(capsys.readouterr().out, "not recorded in this trace:")
    for key in ("children", "threads_started", "spawn_syscalls",
                "audit_errors"):
        assert key in line
    assert "not a record of absence" in line


def test_info_reports_an_audit_hook_that_malfunctioned(
        tmp_path, monkeypatch, capsys):
    """A non-zero count means the two records above it are incomplete, and a
    short child list must not be read as 'nothing was started'."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdee"
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    for k, v in (("run_id", run_id), ("argv", ["prog.py"]),
                 ("cwd", str(tmp_path)), ("python", "3.12.0"),
                 ("exit_status", 0), ("incomplete", False), ("caps", {}),
                 ("children", []), ("threads_started", 0),
                 ("spawn_syscalls", 0), ("audit_errors", 2)):
        w.set_meta(k, v)
    w.close()

    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert _one(out, "audit hook errors:").startswith("audit hook errors: 2 ")
    assert "not recorded in this trace:" not in out   # every key IS recorded


def test_info_reports_the_exception_that_left_the_program(
        tmp_path, monkeypatch, capsys):
    src = ("def boom():\n"
           "    raise ValueError('escaped-from-main')\n"
           "def main():\n"
           "    boom()\n"
           "if __name__ == '__main__':\n"
           "    main()\n")
    run_id, _trace, r = record_script(tmp_path, src)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))

    assert cli.main(["info", run_id]) == 0
    line = next((l for l in capsys.readouterr().out.splitlines()
                 if l.startswith("uncaught:")), None)
    assert line is not None, "the escaping exception was not reported"
    assert "ValueError" in line and "escaped-from-main" in line


ASYNC_SRC = """
import asyncio

def step(n):
    return n

async def worker():
    step(1)
    await asyncio.sleep(0)
    return step(2)

async def amain():
    await asyncio.gather(asyncio.create_task(worker(), name="w1"),
                         asyncio.create_task(worker(), name="w2"))

if __name__ == "__main__":
    asyncio.run(amain())
"""


def test_info_counts_unframed_calls_and_lists_tasks(tmp_path, monkeypatch,
                                                     capsys):
    """On a format-3 trace, arc 2 opened a frame for every one of these
    coroutines -- amain and both worker activations included -- so the
    unframed count is zero and says why, and the counted-event line now
    carries YIELD/RESUME alongside the arc-1 kinds."""
    run_id, trace, r = record_script(tmp_path, ASYNC_SRC)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "unframed calls: 0 (all calls framed in format 3)" in out
    assert ("recorded: CALL 8  RETURN 8  RAISE 0  HANDLED 0  YIELD 3  "
            "RESUME 3  LINE 0") in out
    assert "tasks: 3 (" in out and "w1" in out and "w2" in out
    assert "2x prog.py:worker" in out                      # calls, not frames
    assert "task identity errors" not in out


def test_info_counts_unframed_calls_on_a_format_3_trace_too(
        tmp_path, monkeypatch, capsys):
    """The count is a JOIN, on every format. Arc 2 frames every traced code
    object, so the zero is expected -- but printing it from the FORMAT alone
    means `info` states as fact something it never looked at, and a trace
    that somehow held an unframed CALL would be described by its version
    number instead of by its contents. Synthetic, because the recorder this
    version ships cannot produce the row."""
    w = synthetic(tmp_path, monkeypatch)
    c_main = w.intern_code("/tmp/prog.py", "main", 1)
    c_rows = w.intern_code("/tmp/prog.py", "rows", 5)
    e_main = w.add_event(0, 1, "CALL", None, c_main, 1, {"args": {}})
    f_main = w.open_frame(None, c_main, e_main, 0, 1, "function")
    w.add_event(0, 1, "CALL", None, c_rows, 5,
                {"args": {}, "unframed": "generator"})
    e_ret = w.add_event(0, 1, "RETURN", f_main, c_main, None, {"value": None})
    w.close_frame(f_main, e_ret, "return")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["info", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "unframed calls: 1 (generator 1)" in out
    assert "all calls framed in format 3" not in out


def test_info_says_a_task_name_was_unreadable_not_that_it_was_unnamed(
        tmp_path, monkeypatch, capsys):
    """NULL in `tasks.name` means `get_name()` RAISED: the identity was
    minted, the name could not be read. "(unnamed)" would claim the task had
    no name -- a different fact, and one asyncio cannot produce, since every
    task gets a default name. `tree` already says this; `info` is the other
    place the name is printed, and the two must not disagree."""
    from tests.test_async import HOSTILE_TASK
    src = HOSTILE_TASK + '\nif __name__ == "__main__":\n    main()\n'
    run_id, trace, r = record_script(tmp_path, src)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "(name unreadable)" in out
    assert "(unnamed)" not in out


def test_info_on_a_sync_trace_says_zero_unframed_and_no_loop(tmp_path,
                                                             monkeypatch,
                                                             capsys):
    """Pinned to the exact format-3 line, not a substring of it: a bare
    "unframed calls: 0" would keep passing whether or not the reason
    ("all calls framed in format 3") is actually there."""
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "unframed calls: 0 (all calls framed in format 3)" in out
    assert "tasks: none (no event ran inside an asyncio task)" in out


# -- contract: what a fingerprint row COVERS changed under plan 2b, and a
# reader cannot tell which definition a hash was made under by looking at it.
# `info` is where a trace describes itself, so it states the basis -- and the
# thread rows say what they counted, since under the per-task basis they no
# longer count the events that ran inside a task.
def test_info_states_the_fingerprint_basis_and_the_task_rows(
        tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch, src=TWO_TASKS_PROG)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    # asyncio.run's own wrapper task has a row beside task-A and task-B
    assert ("fingerprints: per-task basis -- each thread row covers the "
            "events that ran in no asyncio task; 3 task fingerprint(s) "
            "beside it") in out
    line = _one(out, "fingerprint thread ")
    assert line.endswith(" causal events outside any asyncio task)"), line
    assert "per-thread basis" not in out


# -- Ruling 7: a rerun whose thread streams all matched and whose TASKS
# parted has no `refocus_diverge_index` to print -- so before this line
# `info` showed a bare `verdict: DIVERGED` with nothing about what diverged,
# which is the "the terminal has scrolled away" failure the stamp exists for.
def test_info_replays_a_task_only_divergence_stamped_by_refocus(tmp_path,
                                                                monkeypatch,
                                                                capsys):
    run_id, sdir = rec(tmp_path, ASYNC_CONTENT_FLIP)
    r = refocus(sdir, run_id, "--focus", "prog:worker")
    assert r.returncode == 1, r.stdout + r.stderr
    new_id = new_run(r.stdout)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))

    assert cli.main(["info", new_id]) == 0
    out = capsys.readouterr().out
    assert "verdict: DIVERGED" in out
    line = _one(out, "  diverged on tasks:")
    assert "task-B" in line
    # the threads all matched: saying they diverged would send the reader to
    # the wrong stream
    assert "diverged on threads:" not in out


def test_info_names_where_the_compared_thread_parted(tmp_path, monkeypatch,
                                                     capsys):
    """The commonest divergence there is -- the compared thread took another
    branch -- and `refocus` has been stamping its position and both sides all
    along while `info` read none of them: a bare `verdict: DIVERGED` once the
    terminal has scrolled away. The task line above is an ADDITION to this
    one, not a replacement: a rerun with no tasks must not grow a task line.
    """
    run_id, sdir = rec(tmp_path, COUNTER)
    r = refocus(sdir, run_id, "--focus", "prog:bump")
    assert r.returncode == 1, r.stdout + r.stderr
    new_id = new_run(r.stdout)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))

    assert cli.main(["info", new_id]) == 0
    out = capsys.readouterr().out
    line = _one(out, "  diverged at causal step ")
    assert "first" in line and "again" in line     # A's side and B's side
    assert "diverged on tasks:" not in out
