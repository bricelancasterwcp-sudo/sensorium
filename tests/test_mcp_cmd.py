"""`sensorium mcp`: what it says for itself, and what it refuses.

The subcommand layer only, in process: every case here either prints and
exits or refuses and exits, and none of them reaches `server.serve()` --
a test that started the server would be reading pytest's own stdin.

WHY A REFUSAL IS EXIT 2 AND ONE LINE. The caller is a shell or an MCP
client's launcher, and a launcher shows the user whatever the process
said before it died. A traceback there is unreadable, and a server that
started anyway with a cap of ten bytes would answer every question with
a marker and no answer.

D31: `mcp` is registered beside `ts`, NOT in `cli._QUERY_MODULES`.
`mcp.tools` imports `sensorium.cli` to read `run`'s parser, so a `cmd`
that imported `tools` at module level -- which is what membership of
that list would amount to -- would close an import cycle. The last test
pins the placement; `cmd.run` does its two imports inside the function.
"""
from __future__ import annotations

import pytest

from sensorium import cli
from sensorium.mcp import cmd as mcp_cmd
from sensorium.mcp import tools
from sensorium.mcp.schema import SchemaError

HELP = ("serve the store to a model over the Model Context Protocol on "
        "stdio")
DESCRIPTION = (
    "One JSON-RPC message per line on stdin/stdout; every query command "
    "is a tool, and record and refocus are tools only under --allow-run. "
    "Diagnostics go to stderr.")
EPILOG = "exit: 0 at EOF or SIGTERM, 2 a refusal to start"


def flat(text: str) -> str:
    """`text` with argparse's line wrapping taken back out."""
    return " ".join(text.split())


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    """`cli.main` logs every return, so point the log at a tmp store --
    no test here may append to the developer's own."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))


def test_help_says_what_the_server_is_and_how_it_ends(capsys):
    """P19: the one-liner in `sensorium --help`, and the description and
    the exit convention under `sensorium mcp --help`."""
    with pytest.raises(SystemExit) as top:
        cli.main(["--help"])
    assert top.value.code == 0
    assert HELP in flat(capsys.readouterr().out)
    with pytest.raises(SystemExit) as own:
        cli.main(["mcp", "--help"])
    assert own.value.code == 0
    printed = flat(capsys.readouterr().out)
    assert DESCRIPTION in printed
    assert EPILOG in printed
    assert "--allow-run" in printed
    assert "--max-output" in printed


def test_a_cap_below_the_minimum_is_refused_naming_the_minimum(capsys):
    """A cap under 4 KiB cannot hold a head, a tail and a marker, so the
    answer would be all marker: refused at the door, with the number the
    caller has to beat."""
    assert cli.main(["mcp", "--max-output", "10"]) == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert printed.err.splitlines() == [
        "sensorium mcp: --max-output 10 is below the 4096-byte minimum"]


@pytest.mark.parametrize("flag", ["--timeout", "--run-timeout"])
def test_a_timeout_that_is_not_positive_is_refused(flag, capsys):
    """Zero is not "no timeout" -- it is a call that is killed before it
    starts -- and neither is a negative number anything."""
    assert cli.main(["mcp", flag, "0"]) == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert printed.err.splitlines() == [
        f"sensorium mcp: {flag} 0 is not a positive number of seconds"]


def test_a_schema_error_refuses_to_boot_with_the_message(capsys, monkeypatch):
    """A command whose field lost its `help=` is a tool with a blank in
    it, and `tools.table` raises rather than offer one. The server never
    starts: a client that connected would be offered the blank."""
    def raise_it(allow_run):
        raise SchemaError("grep: field 'kind' has no help; the server "
                          "refuses to boot")

    monkeypatch.setattr(tools, "table", raise_it)
    assert cli.main(["mcp"]) == 2
    printed = capsys.readouterr()
    assert printed.out == ""
    assert printed.err.splitlines() == [
        "sensorium mcp: grep: field 'kind' has no help; the server "
        "refuses to boot"]


def test_mcp_is_not_a_query_module(capsys):
    """D31, pinned: `_QUERY_MODULES` is walked by `cli.main`, by the
    vocabulary scan and by the tool-description gate, and `mcp` is a
    server rather than a question about a trace. It is also the import
    cycle -- see this module's header."""
    assert mcp_cmd not in cli._QUERY_MODULES
    assert all(module.__name__ != "sensorium.mcp.cmd"
               for module in cli._QUERY_MODULES)
