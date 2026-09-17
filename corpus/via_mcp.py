"""The corpus's questions, asked through a real MCP server.

The corpus has had ONE seam to the tool since it was written --
`run_corpus._cli`, running `python -m sensorium <argv>` -- and every
pre-registered question is checked against what that seam printed. The
MCP server is a SECOND surface answering those same questions, and a
surface no regression suite asks is free to answer differently. So
`--via mcp` routes every question whose command word is a tool through
a server started for that case, handing `run_case` an `Asked` that
duck-types the `CompletedProcess` it already checks; `--compare-cli`
asks the read-only ones both ways and reports any answer the two seams
do not agree on.

WHAT IS AND IS NOT A TOOL (P7). `redact` is a command and deliberately
not a tool -- it rewrites a stored trace (`mcp/tools.py`, `NOT_TOOLS`).
The three corpus questions that call it -- all in `redact_retrofit` --
are asked through the CLI exactly as they always were and NAMED in the
summary. Never skipped: the two questions after them read the store
those three rewrote, so a mode that dropped them would leave two
questions asserting against a trace that was never retrofitted.

THE SERVER'S ENVIRONMENT IS `_cli`'S (P8), not the case's `env:`. A
question's child has never seen `case.env` -- it is merged into the
RECORDING only -- so a server carrying it would answer from an
environment the CLI it is compared against never had:
`redact_retrofit` records under `SENSORIUM_NO_REDACT`, which `info`
reads from the live environment.

`--compare-cli` NEVER RE-RUNS AN EXECUTING TOOL (P26). `refocus` runs
the recorded program again; asking it twice would compare two
EXECUTIONS rather than two seams, and would leave a further trace for
the next question to find (`nondeterministic` asks `runs` right after
its refocus). So the CLI copy is made for the read-only tools alone.

Stdlib and intra-repo imports only, like the rest of `corpus/`.
"""
from __future__ import annotations

import functools
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from corpus.mcp_client import McpClient, McpError
from sensorium.mcp import schema, tools

#: The mode, written by `run_corpus.main` from `--via`/`--compare-cli`.
#: Module state and not a parameter: `run_case(case, workdir)` is called
#: with two positionals by the harness's own tests and by `corpus/_bench`,
#: and a third would be a signature every caller carries for one flag.
VIA = "cli"
COMPARE = False

#: The cap the per-case server is started with -- a megabyte, far above
#: anything a corpus question prints. A capped answer is head, marker
#: and tail (D24) and NOT the CLI's bytes; at this size it cannot be
#: the difference `--compare-cli` reports.
MAX_OUTPUT = "1048576"

#: Where a case's server writes its diagnostics: inside the disposable
#: copy, so it goes when the workdir does.
STDERR_NAME = "mcp-server.stderr"

#: What a difference names when one side simply had no such line.
END = "<end of output>"


@functools.cache
def _table() -> dict:
    """The server's own tool table, built once for the whole run.

    `allow_run=True` because that is how the per-case server is started:
    `refocus` is asked eleven times by the corpus and is a tool only
    under that flag. Cached rather than module-level so importing this
    module cannot fail on a `SchemaError` -- a refusal to boot is the
    server's, not the harness's.
    """
    return tools.table(True)


def is_tool(word: str) -> bool:
    """Whether a question's command word is one of the server's tools."""
    return word in _table()


def executes(word: str) -> bool:
    """Whether answering this tool RUNS the recorded program (P26)."""
    return word in _table() and _table()[word].executes


@dataclass
class Asked:
    """One answer, whichever seam produced it: the three fields
    `run_case` reads off a `CompletedProcess`, plus the seam's name, so
    a checked question cannot be attributed to the wrong one.
    `returncode` is `None` where the server produced no exit at all (a
    timeout, a cancel) and `check_question` then fails it against the
    question's `expect_exit`."""

    stdout: str
    stderr: str
    returncode: int | None
    via: str


class CaseServer:
    """One `sensorium mcp` for one case, over that case's own store.

    Per case and not per run: the store is the case's disposable
    `.sensorium`, `--store` is read once at boot, and a tool call's
    child inherits the SERVER's working directory -- which has to be the
    case's copied directory, the cwd `_cli` gives a question. Started
    after the recording, so it serves a store that exists; a context
    manager around `McpClient`'s, whose kill ladder ends the server and
    all it spawned, by process group.
    """

    def __init__(self, wd, sdir) -> None:
        self.wd, self.sdir = Path(wd), Path(sdir)
        #: P8: `_cli`'s environment exactly, never the case's `env:`.
        self.env = {**os.environ, "SENSORIUM_DIR": str(self.sdir),
                    "PYTHONDONTWRITEBYTECODE": "1"}
        self.argv = [sys.executable, "-m", "sensorium", "mcp", "--allow-run",
                     "--store", str(self.sdir), "--max-output", MAX_OUTPUT]
        self.client = McpClient(self.argv, cwd=self.wd, env=self.env,
                                stderr_path=self.wd / STDERR_NAME)

    def __enter__(self) -> "CaseServer":
        self.client.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        self.client.__exit__(*exc)


def ask(server: CaseServer, cmd: list[str]) -> Asked:
    """One corpus question, through the server.

    The command word names the tool and the rest is its argv, read back
    into a call by the schema the server itself derives (P25) -- never
    a second table of field names kept here.

    A refusal is an exit-2 ANSWER and never an exception: `run_case`
    reports a failed question, where a raise would abandon the case.
    The server's own argument refusal is already an exit-2 result
    (P30); a `Rejection` from `from_argv` is a corpus argv the schema
    cannot parse (none today); an `McpError` is the protocol's own,
    `Unknown tool` among them.
    """
    word, tool = cmd[0], _table().get(cmd[0])
    try:
        # A word with no tool is still SENT: the server owns the answer
        # to "is this a tool", and its refusal is the honest report.
        arguments = ({} if tool is None
                     else schema.from_argv(tool.schema, list(cmd[1:])))
    except schema.Rejection as refused:
        return Asked("", f"error: {refused.message}", 2, "mcp")
    try:
        answer = server.client.call(word, arguments)
    except McpError as err:
        return Asked("", f"error: {err.message}", 2, "mcp")
    return Asked(answer.stdout, answer.stderr, answer.exit, "mcp")


def _first_differing_line(mcp: str, cli: str) -> tuple[str, str]:
    """The first line the two answers disagree on, each side's own.

    Lines and not bytes: a difference reported as two whole answers is
    one nobody reads. Where a side ran out, its half is `END` -- an
    empty string could not be told from a blank line, which is a real
    thing for one of these answers to hold."""
    left, right = mcp.splitlines(), cli.splitlines()
    for i in range(max(len(left), len(right))):
        one = left[i] if i < len(left) else END
        other = right[i] if i < len(right) else END
        if one != other:
            return one, other
    return END, END


def compare(case: str, q: dict, mcp: Asked, cli) -> list[dict]:
    """What the two seams do not agree on, one record per field:
    `stdout` and the exit status, the two facts `check_question` reads.
    Stderr is deliberately not compared -- the server LABELS it (P4),
    and a stdout that lacked its final newline gains one before that
    label: a rendering difference, not an answer's."""
    found = []
    if mcp.stdout != cli.stdout:
        one, other = _first_differing_line(mcp.stdout, cli.stdout)
        found.append({"case": case, "id": q["id"], "field": "stdout",
                      "mcp": one, "cli": other})
    if mcp.returncode != cli.returncode:
        found.append({"case": case, "id": q["id"], "field": "exit",
                      "mcp": mcp.returncode, "cli": cli.returncode})
    return found


def json_keys(results, via: str, compare_cli: bool) -> dict:
    """The keys a `--via mcp` run adds to the JSON report: each only
    where its presence says something -- `via` where a server was asked
    at all, `via_cli` where a question could not be (P7), and
    `mcp_differences` under `--compare-cli`, an EMPTY LIST then because
    "compared, found nothing" is the claim that mode is run for and
    silence cannot be told from a comparison never made."""
    named = cli_questions(results)
    return {**({"via": via} if via == "mcp" else {}),
            **({"via_cli": named} if named else {}),
            **({"mcp_differences": differences(results)}
               if compare_cli else {})}


def cli_questions(results) -> list[str]:
    """`case/id` for every question a `--via mcp` run asked the CLI."""
    return [f"{r.name}/{qid}" for r in results for qid in r.via_cli]


def differences(results) -> list[dict]:
    """Every `compare` record of the run, in the order they were made."""
    return [d for r in results for d in r.differences]
