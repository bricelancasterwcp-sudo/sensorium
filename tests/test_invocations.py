"""The invocation log: one JSON line per `cli.main` return."""
import json

from sensorium import cli, invocations
from tests.helpers import record_script
from tests.programs import CRASH, record


def _lines(path):
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln]


def _reset_log():
    """`record()` boots its fixture trace via a real `sensorium run`
    subprocess, which is itself one `main()` return and gets logged --
    correctly, but that line belongs to setup, not to the invariant a test
    is pinning. Clear it so a test's own assertions start from zero."""
    p = invocations.path()
    if p.exists():
        p.unlink()


# -- invariant 1: every main() return appends exactly one line whose exit
# equals the value returned, on both the query path and the run path,
# including the three caught exception classes ---------------------------
def test_records_a_zero_a_one_a_two_and_a_caught_exception(
        tmp_path, monkeypatch):
    run_id = record(tmp_path, monkeypatch, CRASH)
    _reset_log()

    assert cli.main(["info", run_id]) == 0                    # 0: describes
    assert cli.main(["tree", run_id, "--root", "f999999"]) == 1  # 1: no such
    assert cli.main(["grep", run_id, "x", "--limit", "0"]) == 2  # 2: bad call
    assert cli.main(["info", "no-such-run"]) == 2              # TraceLookupError

    lines = _lines(invocations.path())
    assert len(lines) == 4
    assert [ln["exit"] for ln in lines] == [0, 1, 2, 2]
    assert [ln["error"] for ln in lines] == [
        None, None, None, "TraceLookupError"]
    assert lines[0]["argv"] == ["info", run_id]
    assert lines[3]["argv"] == ["info", "no-such-run"]


def test_run_subcommand_logs_the_targets_exit_status(tmp_path):
    """The `run` subcommand's exit status is the TARGET's -- it is also a
    `main()` return, and gets logged like any other."""
    run_id, _trace, r = record_script(tmp_path, "import sys\nsys.exit(3)\n")
    assert run_id, r.stderr
    lines = _lines(tmp_path / "sdir" / "invocations.jsonl")
    assert len(lines) == 1
    assert lines[0]["exit"] == 3
    assert lines[0]["error"] is None
    assert lines[0]["argv"][0] == "run"


# -- invariant 2: argv only -- exactly the four keys, no env, no cwd -----
def test_line_has_exactly_the_four_keys(tmp_path, monkeypatch):
    run_id = record(tmp_path, monkeypatch, CRASH)
    _reset_log()
    cli.main(["info", run_id])
    lines = _lines(invocations.path())
    assert len(lines) == 1
    assert set(lines[0].keys()) == {"utc", "argv", "exit", "error"}


# -- invariant 3: SENSORIUM_NO_INVOCATION_LOG=1 -> no file, no output ----
def test_opt_out_env_var_writes_nothing(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CRASH)
    _reset_log()
    monkeypatch.setenv("SENSORIUM_NO_INVOCATION_LOG", "1")
    assert cli.main(["info", run_id]) == 0
    capsys.readouterr()                      # drop the command's own output
    assert not invocations.path().exists()


# -- invariant 4: an unwritable log location prints one stderr line and
# never changes the exit status ------------------------------------------
def test_unwritable_log_prints_one_stderr_line_and_exit_is_unchanged(
        tmp_path, monkeypatch, capsys):
    # A regular file where the trace-root directory should be: mkdir(parent)
    # cannot create a child under it. The version guard is the one main()
    # return that never touches the trace store on its own, so it isolates
    # the invocation log's own write failure cleanly.
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    monkeypatch.setattr(cli.sys, "version_info", (3, 11, 9, "final", 0))

    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "writable"))
    baseline_exit = cli.main(["runs"])
    capsys.readouterr()

    monkeypatch.setenv("SENSORIUM_DIR", str(blocker / "sub"))
    exit_status = cli.main(["runs"])

    assert exit_status == baseline_exit        # unwritable log, same exit
    err_lines = [ln for ln in capsys.readouterr().err.splitlines() if ln]
    unwritable = [ln for ln in err_lines
                 if ln.startswith("sensorium: invocation log unwritable:")]
    assert len(unwritable) == 1
    assert not (blocker / "sub").exists()      # the write never landed


# -- invariant 5: `runs` never lists the log; it globs traces/*.db only --
def test_runs_output_is_unchanged_by_the_log_existing(tmp_path, monkeypatch,
                                                       capsys):
    run_id = record(tmp_path, monkeypatch, CRASH)
    cli.main(["runs"])
    before = capsys.readouterr().out
    assert invocations.path().exists()         # the log now has >= 1 line

    cli.main(["runs"])
    after = capsys.readouterr().out

    assert before == after
    assert "invocations" not in after
    assert run_id in after
