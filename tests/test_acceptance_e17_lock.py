"""The byte-lock on E17's acceptance record (plan `2026-09-16-sensorium-mcp-
stdio.md`, Task 0).

Two claims this document makes about itself, held by a test rather than by
prose:

* **§1's two bodies are verbatim.** §1 says block (a) is the MCP stdio
  spec's `## 9. E17, pre-registered` section, byte-for-byte, and block (b)
  is the plan's `## Pre-registration (…)` block, byte-for-byte. Both are
  checkable against the source files, so both are checked here -- a
  paraphrase, a reordered row or a softened endpoint would otherwise read
  as the source and never be caught.

  As in `tests/test_acceptance_e16_lock.py`, the source read is the WORKING
  TREE and only the working tree -- no `git show <commit>:<path>` fallback.
  `docs/superpowers/specs/2026-09-16-sensorium-mcp-stdio-design.md` and
  `docs/superpowers/plans/2026-09-16-sensorium-mcp-stdio.md` are committed
  on THIS branch, and CI does not fetch the docs branch the spec was first
  drafted on -- a `git show` primary read would skip by name on every CI
  run, which is a check that never checks anything. The bodies end
  differently in their sources, and are read differently here: the spec's
  `## 9.` section runs to the next heading (`## 10.`); the plan's
  `## Pre-registration (…)` block runs to the `---` that terminates it,
  which is §1's own stated rule for that source.

* **§2 opens the shape §1 promises.** The first non-blank line after
  `## 2. Measured` is either the literal `Not yet measured.` (its
  unmeasured state) or a heading beginning `### measured` (its measured
  one) -- never a bare claim typed in between the two, and never a number
  written down before the instrument that is supposed to produce it exists.

There is no separate content-hash lock on the record's own §1 bytes: the
verbatim check against the (static, already-committed) source files IS the
lock -- an edit to either the record's blocks or the source they must equal
is caught by the same comparison, which is what the mutation test below
demonstrates.

Pre-registered mutants for this module (mutate on a committed tree, run,
restore, re-run green): `_after` returning `[]` instead of raising
`Refused` for an absent heading (caught by
`test_a_missing_heading_is_refused_not_silently_empty` and by the mutation
test); `body_to_rule` breaking on a heading rather than on `---` (caught by
`test_section_one_carries_the_plans_preregistration_verbatim`, since the
plan's block is followed by `---` and then a `###` heading, so the rule
read and the heading read differ); the `!=` in the mutation test flipped to
`==`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

from acceptance_lib import Refused                                 # noqa: E402

#: The document this module locks.
DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-16-sensorium-e17-mcp.md")

_SPEC = (REPO / "docs" / "superpowers" / "specs"
         / "2026-09-16-sensorium-mcp-stdio-design.md")
_PLAN = (REPO / "docs" / "superpowers" / "plans"
         / "2026-09-16-sensorium-mcp-stdio.md")

_SPEC_HEAD = "## 9. E17, pre-registered"
_PLAN_HEAD = ("## Pre-registration (Task 0 appends this block verbatim to "
              "the record's §1 as a dated amendment; the lock test holds "
              "it there)")

#: The record's title, and the two headings §1 carries the sources under
#: with the reader that ends each body ON EACH SIDE. In the record both
#: blocks butt against the next `###`/`##` heading, so the record side
#: always reads `body_to_heading`; the spec's source section does too (it
#: ends at `## 10.`), but the plan's source block ends at the `---` that
#: follows it in the plan file, not at a heading -- the plan separates
#: sections with a rule, and §1 states this reading as the one that applies
#: to that source.
TITLE = "# E17 — sensorium as an MCP server, measured\n"

SECTIONS = (
    ("### 9. E17, pre-registered", "body_to_heading",
     _SPEC, _SPEC_HEAD, "body_to_heading"),
    ("### The plan's pre-registration block", "body_to_heading",
     _PLAN, _PLAN_HEAD, "body_to_rule"),
)

#: The one-byte mutation target: the corpus census H1's PASS is read
#: against, which lives in the plan's block and nowhere else in the record.
#: `65536` -- the cap figure the brief first reached for -- occurs in BOTH
#: locked bodies, so a mutation there would not say which block was
#: compared.
_NEEDLE = "**115 cases / 253 questions**"
_MUTANT = "**116 cases / 253 questions**"


def _after(text: str, heading: str) -> list[str]:
    """The lines following `heading`, or a refusal if it is not there.

    A heading lookup that silently returned `[]` would make every comparison
    against its body pass the moment two blocks both went missing."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip("\n") == heading:
            return lines[i + 1:]
    raise Refused(f"no heading {heading!r} in this document")


def body_to_heading(text: str, heading: str) -> str:
    """One section's body, read to the next heading of any level -- how the
    spec's `## 9.` ends in its source, and how §1 says it was read."""
    out = []
    for line in _after(text, heading):
        if re.match(r"^#{1,6} ", line):
            break
        out.append(line)
    return "".join(out).strip("\n")


def body_to_rule(text: str, heading: str) -> str:
    """One section's body, read to the horizontal rule that terminates it --
    how the plan's `## Pre-registration (…)` block ends in its source.

    The plan separates its sections with `---` rather than by butting one
    heading against the next, so a to-the-next-heading read would carry that
    rule into the record. §1 states this reading, and it is the reading
    checked here."""
    out = []
    for line in _after(text, heading):
        if line.rstrip("\n") == "---":
            break
        out.append(line)
    return "".join(out).strip("\n")


_READERS = {"body_to_heading": body_to_heading, "body_to_rule": body_to_rule}


# -- the verbatim claim -------------------------------------------------


def test_section_one_carries_the_specs_e17_section_verbatim():
    """Catches: the spec's `## 9.` paraphrased, reordered or silently
    tightened while §1 still says "byte-for-byte". Read from the working
    tree, not a pinned commit -- see the module docstring for why."""
    here, here_reader, source, there, there_reader = SECTIONS[0]
    mine = _READERS[here_reader](DOC.read_text(), here)
    theirs = _READERS[there_reader](source.read_text(), there)
    assert mine == theirs, (
        f"{there} vs record's {here}: "
        f"{len(mine.encode())} B in the record, "
        f"{len(theirs.encode())} B in the source")


def test_section_one_carries_the_plans_preregistration_verbatim():
    """The same for the plan's block, read to the `---` that terminates it
    in the plan file rather than to the next heading -- the record itself
    still reads to the next heading, since `## 2. Measured` follows the
    block directly with no rule of its own."""
    here, here_reader, source, there, there_reader = SECTIONS[1]
    mine = _READERS[here_reader](DOC.read_text(), here)
    theirs = _READERS[there_reader](source.read_text(), there)
    assert mine == theirs, (
        f"{there} vs record's {here}: "
        f"{len(mine.encode())} B in the record, "
        f"{len(theirs.encode())} B in the source")


def test_the_verbatim_check_refuses_a_body_that_differs_by_one_byte(tmp_path):
    """Catches: a verbatim check that compares a body to itself, or that
    compares nothing because a heading lookup silently returned empty. The
    same comparison, on a COPY of the record with one character changed
    inside block (b), must fail. The mutation target is E17's locked corpus
    census -- one of the numbers H1's PASS is read against."""
    here, here_reader, source, there, there_reader = SECTIONS[1]
    text = DOC.read_text()
    assert text.count(_NEEDLE) == 1, "the mutation target moved"
    copy = tmp_path / DOC.name
    copy.write_text(text.replace(_NEEDLE, _MUTANT, 1))
    tampered = copy.read_text()
    assert tampered != text
    theirs = _READERS[there_reader](source.read_text(), there)
    assert _READERS[here_reader](tampered, here) != theirs


def test_a_missing_heading_is_refused_not_silently_empty():
    """Catches: the failure mode above at its root -- a reader returning `""`
    for a heading that is not there would make every comparison against it
    pass the moment two blocks both went missing."""
    for reader in (body_to_heading, body_to_rule):
        with pytest.raises(Refused):
            reader("## 1. Pre-registration (locked)\n\nnothing here\n",
                   _SPEC_HEAD)


# -- what §2 must look like ----------------------------------------------


def test_section_two_begins_not_yet_measured_or_a_measured_heading():
    """Catches: a bare claim -- a number, a verdict -- typed into §2 outside
    either of the two shapes §1 promises. This task's state is the literal
    sentence; Task 10's is a `### measured` heading; nothing else."""
    lines = DOC.read_text().splitlines()
    idx = lines.index("## 2. Measured")
    first = next(ln for ln in lines[idx + 1:] if ln.strip())
    assert (first == "Not yet measured."
            or first.startswith("### measured")), first


def test_the_record_opens_with_its_title_and_no_box_path():
    """Catches: a retitled record, or a box-specific absolute path leaking
    into a document meant to travel with the repo -- outside the one
    sanctioned work-root pin each locked block carries (`E17_DIR=`), which
    stays verbatim because §1 says those blocks are verbatim."""
    text = DOC.read_text()
    assert text.startswith(TITLE)
    stray = [ln for ln in text.splitlines()
             if ("/mnt/" in ln or "/home/" in ln) and "E17_DIR=" not in ln]
    assert stray == [], stray


def test_both_headings_sit_inside_section_one():
    """Catches: a block moved out of `## 1.` -- into `## 2.`, or above the
    record's title -- where it would still read as "in the record" but no
    longer as "locked". Both headings in `SECTIONS`, which is also what
    holds them in `SECTIONS` order in §1: an unlisted block between the two
    would end the earlier one's `body_to_heading` read early and fail the
    verbatim check above."""
    text = DOC.read_text()
    one_at = text.index("## 1. Pre-registration (locked)")
    two_at = text.index("## 2. Measured")
    assert 0 <= one_at < two_at
    for heading, _, _, _, _ in SECTIONS:
        at = text.index(heading)
        assert one_at < at < two_at, heading
