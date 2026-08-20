import sys

import pytest

from sensorium import cli, paths
from sensorium.record import boot
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script

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


def _record(tmp_path, monkeypatch, extra=()):
    run_id, trace, r = record_script(tmp_path, SRC, extra=extra)
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
