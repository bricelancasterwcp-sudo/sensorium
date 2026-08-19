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
