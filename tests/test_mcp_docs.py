"""`docs/mcp.md` says what the server says, or the suite says so.

A document describing a surface drifts the moment the surface moves, and
the drift is silent: nobody diffs a page against a parser. Three things
on that page are not prose but COPIES of strings the code owns -- the
tool table's names and description sentences, the four exit meanings a
result's header line is made of, and the three forms a refused call
comes back in -- so each is checked against its source here rather than
proofread.

The table is the one that would rot fastest. `Tool.description` is
`help=` plus `description=` off the command's own parser (D3), so a
reworded `add_parser` changes eleven sentences in `tools/list` and none
in the doc; `present` is `Tool.executes`, so a tool that moved behind
`--allow-run` -- or out from behind it -- would leave the page claiming
the old policy. Parsing the markdown and comparing cell by cell is what
makes the page a derived artefact with a gate on it.

PRE-REGISTERED MUTANTS (run on the committed tree, both on
`test_the_docs_table_names_every_tool_and_its_description`):

* change one word of one description cell -- `search events by name or
  value.` -> `search events by name or price.` -- the test fails naming
  that row's description.
* swap two rows of the table -- `tree` and `frame` -- the test fails on
  the name order.

`present` and the tool name are compared with their markdown backticks
stripped, because the house style sets a flag and a command in code
font; the description is compared EXACTLY, backticks and all, since the
sentence itself contains them.
"""
from __future__ import annotations

from pathlib import Path

from sensorium import exit as ex
from sensorium.mcp import schema, tools

DOC = Path(__file__).resolve().parents[1] / "docs" / "mcp.md"

#: The header row that marks the table this file is about. Written out
#: rather than "the first table": the page has prose tables too.
HEADER = "| tool | present | description |"


def _cells(line: str) -> list[str]:
    """One markdown row's cells, without the leading/trailing pipes."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _rows() -> list[list[str]]:
    """The tool table's data rows, in the order the page prints them."""
    lines = DOC.read_text().splitlines()
    assert HEADER in lines, f"{DOC} has no `{HEADER}` table"
    start = lines.index(HEADER)
    rows = []
    for line in lines[start + 2:]:          # +2: skip the `|---|` rule
        if not line.startswith("|"):
            break
        rows.append(_cells(line))
    assert rows, "the tool table has no rows"
    return rows


def test_the_docs_table_names_every_tool_and_its_description():
    """Every tool, in `tools/list` order, with its policy and its
    sentence -- the three things a client is shown."""
    table = tools.table(True)
    rows = _rows()
    assert [c[0].strip("`") for c in rows] == list(table), (
        "the table's tool names, in order, are not `tools.table(True)`'s")
    for name, present, description in rows:
        tool = table[name.strip("`")]
        expected = "--allow-run" if tool.executes else "always"
        assert present.strip("`") == expected, (
            f"{tool.name}: the table says {present!r}, "
            f"`Tool.executes` says {expected!r}")
        assert description == tool.description, (
            f"{tool.name}: the table's description is not the tool's")


def test_the_docs_quote_the_four_meanings():
    """The header line is `exit.MEANING`'s words (P3), so the page that
    teaches a model to branch on it must carry those words and not a
    paraphrase of them."""
    text = DOC.read_text()
    for status, sentence in ex.MEANING.items():
        assert sentence in text, f"exit {status}: {sentence!r} is not on the page"


def test_the_docs_name_the_three_rejection_forms():
    """The three messages `schema.validate` raises, generated here the
    way a call would earn them rather than retyped, so a reworded
    refusal fails this test instead of quietly outdating the page."""
    text = DOC.read_text()
    grep = tools.table(True)["grep"]
    calls = ({"run": "last", "pattern": "x", "depth": 2},
             {"run": "last", "pattern": "x", "limit": "3"},
             {"run": "last"})
    seen = []
    for arguments in calls:
        try:
            schema.validate(grep.schema, arguments)
        except schema.Rejection as rejected:
            seen.append((rejected.reason, rejected.message))
        else:                                    # pragma: no cover - guard
            raise AssertionError(f"{arguments} was not refused")
    assert [reason for reason, _ in seen] == ["unknown_fields", "bad_fields",
                                              "missing_fields"]
    for reason, message in seen:
        assert message in text, f"{reason}: {message!r} is not on the page"
