"""One-command smoke for the agent path: record, query, MCP.

After install, this file is the proof the Python recorder, the query CLI
and `sensorium mcp --allow-run` still form one path:

    python -m pytest tests/test_agent_smoke.py -q

It records the in-repo program `docs/agent.md` teaches
(`corpus/silent_swallow/main.py`), asks `exceptions`, and asks the same
question through a real MCP server started with `--store`. The store is
always a tmp directory -- this file never writes `~/.sensorium`. Dropping
`--store` (MCP) or `sensorium_dir` (CLI) fails the trace-file assertion,
not the query text.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from corpus.mcp_client import McpClient
from sensorium.mcp import tools
from tests.helpers import run_cli

REPO = Path(__file__).resolve().parents[1]
PROGRAM = "corpus/silent_swallow/main.py"
SWALLOWED = "dispositions: swallowed 2"
ELEVEN = list(tools.table(True))
RUN_LINE = re.compile(r"^run: (\S+)$", re.M)


def _trace(store: Path, text: str) -> Path:
    """The sqlite file `sensorium run` named, which must sit in `store`."""
    match = RUN_LINE.search(text)
    assert match, text
    trace = store / "traces" / f"{match.group(1)}.db"
    assert trace.is_file(), trace
    return trace


def test_cli_records_silent_swallow_and_exceptions_names_the_two_swallows(
        tmp_path):
    """Install → record → query, the CLI half."""
    store = tmp_path / "sdir"
    recorded = run_cli(["run", "--", PROGRAM], cwd=REPO, sensorium_dir=store)
    assert recorded.returncode == 0, recorded.stderr
    _trace(store, recorded.stdout)
    asked = run_cli(["exceptions", "last"], cwd=REPO, sensorium_dir=store)
    assert asked.returncode == 0, asked.stderr
    assert SWALLOWED in asked.stdout
    assert "load_all" in asked.stdout


def test_mcp_records_the_same_program_and_answers_the_same_exceptions(
        tmp_path):
    """The MCP half: `--allow-run --store`, eleven tools, record, query.

    `SENSORIUM_DIR` is stripped from the child environment so the flag,
    not an inherited store, is what the recording lands in (the same
    proof `test_every_call_lands_in_invocations_jsonl_...` uses).
    """
    store = tmp_path / "sdir"
    store.mkdir()
    env = {k: v for k, v in os.environ.items() if k != "SENSORIUM_DIR"}
    argv = [sys.executable, "-m", "sensorium", "mcp",
            "--allow-run", "--store", str(store)]
    with McpClient(argv, cwd=REPO, env=env,
                   stderr_path=tmp_path / "mcp.stderr") as client:
        assert [t["name"] for t in client.list_tools()] == ELEVEN
        made = client.call("record", {"command": [PROGRAM], "cwd": str(REPO)})
        asked = client.call("exceptions", {})
    assert made.exit == 0, made.text
    _trace(store, made.stdout)
    assert asked.exit == 0, asked.text
    assert SWALLOWED in asked.stdout
    assert "load_all" in asked.stdout
    assert client.bad_lines == []
