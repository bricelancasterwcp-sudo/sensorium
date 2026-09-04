"""Every subcommand's `--help` teaches the exit-status convention (X10).

`argparse` handles `--help` itself: it prints and calls `parser.exit()`,
which raises `SystemExit` straight out of `cli.main` before dispatch (see
`cli.py`'s own docstring on that). So each case here calls `cli.main` with
just `[cmd, "--help"]` -- no trace, no `SENSORIUM_DIR`, nothing to build --
catches the `SystemExit(0)`, and asserts the epilog landed in stdout.

Query commands share one epilog; `run`'s is the one carve-out (its exit
status is the target's, not the convention's). A parser missing its
`epilog=` prints no such line at all, so dropping any one of them (the
prescribed mutation) turns its case red with an empty-string "not found"
failure -- there is no way to satisfy this file by accident.
"""
import pytest

from sensorium import cli

QUERY_EPILOG = "exit: 0 yes, 1 no, 2 fix the call, 3 change the recording"
RUN_EPILOG = "exit: the target's own status"

CASES = [
    ("run", RUN_EPILOG),
    ("runs", QUERY_EPILOG),
    ("info", QUERY_EPILOG),
    ("tree", QUERY_EPILOG),
    ("frame", QUERY_EPILOG),
    ("grep", QUERY_EPILOG),
    ("exceptions", QUERY_EPILOG),
    ("flow", QUERY_EPILOG),
    ("watch", QUERY_EPILOG),
    ("diff", QUERY_EPILOG),
    ("refocus", QUERY_EPILOG),
]


@pytest.mark.parametrize("cmd,epilog", CASES, ids=[c[0] for c in CASES])
def test_help_states_the_exit_convention(cmd, epilog, capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main([cmd, "--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert epilog in out, out
