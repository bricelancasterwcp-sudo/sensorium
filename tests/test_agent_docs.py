"""The agent path is a short page, not a hunt through the honesty doctrine.

An agent arriving at the repo has to install, record one run, query it,
and serve the same store over MCP. That recipe lives in `docs/agent.md`
as numbered steps, at most ten, and the README points there. The page
is pinned against the commands it teaches rather than proofread: a
reworded install line or a vanished smoke test fails here.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENT = REPO / "docs" / "agent.md"
README = REPO / "README.md"
MCP = REPO / "docs" / "mcp.md"

#: A step is a markdown ordered-list item at column 0.
STEP = re.compile(r"^(\d+)\. ", re.M)

INSTALL = 'uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"'
SMOKE = "tests/test_agent_smoke.py"
PROGRAM = "corpus/silent_swallow/main.py"
MCP_CMD = "sensorium mcp --allow-run"
STDIO_ARGS = '["mcp", "--allow-run"]'
STORE_FLAG = "--store"
STORE_ENV = "SENSORIUM_DIR"


def _steps(text: str) -> list[int]:
    return [int(n) for n in STEP.findall(text)]


def test_agent_page_exists_and_is_at_most_ten_steps():
    """The done criterion: install → record → query → MCP in ≤10 steps."""
    assert AGENT.is_file(), AGENT
    text = AGENT.read_text()
    numbers = _steps(text)
    assert numbers, f"{AGENT} has no numbered steps"
    assert numbers == list(range(1, len(numbers) + 1)), numbers
    assert len(numbers) <= 10, f"{len(numbers)} steps is more than ten"


def test_agent_page_teaches_the_install_the_program_mcp_and_the_smoke():
    """The four things an agent has to type, present as themselves."""
    text = AGENT.read_text()
    assert INSTALL in text
    assert PROGRAM in text
    assert MCP_CMD in text
    assert SMOKE in text
    assert STDIO_ARGS in text
    assert STORE_FLAG in text
    assert STORE_ENV in text


def test_readme_points_at_the_agent_page():
    """A reader of the README does not have to guess the page exists."""
    text = README.read_text()
    assert "## For agents" in text
    assert "docs/agent.md" in text


def test_mcp_docs_name_the_stdio_shape_not_only_claude():
    """`claude mcp add` is one client's launcher; the wire is stdio."""
    text = MCP.read_text()
    assert STDIO_ARGS in text
    assert '"command": "<venv>/bin/sensorium"' in text
