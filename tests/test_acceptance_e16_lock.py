"""The byte-lock on E16's acceptance record (plan `2026-09-13-sensorium-
redaction-a.md`, Task 0; the part B amendment, plan `2026-09-14-sensorium-
redaction-b.md`, Task 0; the part C amendment, plan `2026-09-15-sensorium-
redaction-c.md`, Task 0).

Two claims this document makes about itself, held by a test rather than by
prose:

* **§1's four bodies are verbatim.** §1 says block (a) is spec §9's `## 9.
  E16, pre-registered` section, byte-for-byte, and block (b) is plan A's
  `## Pre-registration (…)` block, byte-for-byte. Blocks (c) and (d), added
  the days part B and part C were planned, are plan B's and plan C's own
  `## Pre-registration (…)` blocks under dated `###` headings --
  pre-registration written down BESIDE the locked text rather than over it,
  so that what an earlier part was measured against is still readable
  exactly as it was. All four are checkable against the source files, so
  all four are checked here -- a paraphrase, a reordered row or a softened
  endpoint would otherwise read as the source and never be caught.

  Unlike `tests/test_acceptance_e15_lock.py`, the source read is the WORKING
  TREE and only the working tree -- no `git show <commit>:<path>` fallback.
  `docs/superpowers/specs/2026-09-13-sensorium-secrets-redaction-design.md`
  and all three `docs/superpowers/plans/…-sensorium-redaction-{a,b,c}.md`
  are committed on THIS branch, and CI does not fetch the docs branch those
  files were first drafted on -- a `git show` primary read would skip by
  name on every CI run, which is a check that never checks anything. The
  bodies end differently in their sources, and are read differently here:
  the spec's `## 9.` section runs to the next heading (`## 10.`); each
  plan's `## Pre-registration (…)` block runs to the `---` that terminates
  it, which is §1's own stated rule for that source.

* **§2, §3 and §4 open the shape §1 promises.** The first non-blank line
  after `## 2. Part A` -- and after `## 3. Part B`, and after `## 4. Part
  C` -- is either the literal `Not yet measured.` (that part's unmeasured
  state) or a heading beginning `### measured` (its measured one) -- never
  a bare claim typed in between the two.

There is no separate content-hash lock on the record's own §1 bytes: the
verbatim check against the (static, already-committed) source files IS the
lock -- an edit to either the record's blocks or the source they must equal
is caught by the same comparison, which is what the mutation test below
demonstrates.
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
       / "2026-09-13-sensorium-e16-redaction.md")

_SPEC = (REPO / "docs" / "superpowers" / "specs"
         / "2026-09-13-sensorium-secrets-redaction-design.md")
_PLAN = (REPO / "docs" / "superpowers" / "plans"
         / "2026-09-13-sensorium-redaction-a.md")
_PLAN_B = (REPO / "docs" / "superpowers" / "plans"
           / "2026-09-14-sensorium-redaction-b.md")
_PLAN_C = (REPO / "docs" / "superpowers" / "plans"
           / "2026-09-15-sensorium-redaction-c.md")

_SPEC_HEAD = "## 9. E16, pre-registered"
_PLAN_HEAD = ("## Pre-registration (Task 0 commits spec §9 verbatim as the "
              "record's §1, plus this block)")
_PLAN_B_HEAD = ("## Pre-registration (Task 0 appends this block verbatim to "
                "the record's §1 as a dated amendment; the lock test holds "
                "it there)")
_PLAN_C_HEAD = ("## Pre-registration (Task 0 appends this block verbatim to "
                "the record's §1 as a dated amendment; the lock test holds "
                "it there)")
_AMENDMENT = ("### 2026-09-14 — Part B's pre-registration (amendment, beside "
              "the locked text above)")
_AMENDMENT_C = ("### 2026-09-15 — Part C's pre-registration (amendment, "
                "beside the locked text above)")

#: The four headings §1 carries the sources under, and the reader that ends
#: each body ON EACH SIDE. In the record every block butts against the next
#: `###`/`##` heading, so the record side always reads `body_to_heading`;
#: the spec's source section does too (it ends at `## 10.`), but a plan's
#: source block ends at the `---` that follows it in the plan file, not at
#: a heading -- the plans separate sections with a rule, and §1 states this
#: reading as the one that applies to those sources.
SECTIONS = (
    ("### 9. E16, pre-registered", "body_to_heading",
     _SPEC, _SPEC_HEAD, "body_to_heading"),
    ("### The plan's pre-registration block", "body_to_heading",
     _PLAN, _PLAN_HEAD, "body_to_rule"),
    (_AMENDMENT, "body_to_heading", _PLAN_B, _PLAN_B_HEAD, "body_to_rule"),
    (_AMENDMENT_C, "body_to_heading", _PLAN_C, _PLAN_C_HEAD, "body_to_rule"),
)


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


def test_section_one_carries_the_specs_e16_section_verbatim():
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
    still reads to the next heading, since `## 2. Part A` follows the block
    directly with no rule of its own."""
    here, here_reader, source, there, there_reader = SECTIONS[1]
    mine = _READERS[here_reader](DOC.read_text(), here)
    theirs = _READERS[there_reader](source.read_text(), there)
    assert mine == theirs, (
        f"{there} vs record's {here}: "
        f"{len(mine.encode())} B in the record, "
        f"{len(theirs.encode())} B in the source")


def test_section_one_carries_part_bs_preregistration_verbatim():
    """The same for part B's block, added as a DATED amendment beside the
    two locked bodies rather than folded into them: what part A was measured
    against has to stay readable exactly as it was on the day it was
    measured, and a second part's endpoints have to be written down before
    that part is run. Read to the `---` in plan B, like plan A's."""
    here, here_reader, source, there, there_reader = SECTIONS[2]
    mine = _READERS[here_reader](DOC.read_text(), here)
    theirs = _READERS[there_reader](source.read_text(), there)
    assert mine == theirs, (
        f"{there} vs record's {here}: "
        f"{len(mine.encode())} B in the record, "
        f"{len(theirs.encode())} B in the source")


def test_section_one_carries_part_cs_preregistration_verbatim():
    """The same for part C's block, the second dated amendment: parts A and
    B stay readable exactly as they were measured, and part C's endpoints
    are written down before part C is run. Read to the `---` in plan C.

    Part C's block is now the LAST in §1, so it is the one whose
    `body_to_heading` read ends at `## 2. Part A`; part B's now ends at
    this heading, which is a heading too and so reads the same."""
    here, here_reader, source, there, there_reader = SECTIONS[3]
    mine = _READERS[here_reader](DOC.read_text(), here)
    theirs = _READERS[there_reader](source.read_text(), there)
    assert mine == theirs, (
        f"{there} vs record's {here}: "
        f"{len(mine.encode())} B in the record, "
        f"{len(theirs.encode())} B in the source")


def test_the_verbatim_check_REFUSES_a_body_that_differs_by_one_byte():
    """Catches: a verbatim check that compares a body to itself, or that
    compares nothing because a heading lookup silently returned empty. The
    same comparison, on a record with one character changed inside block
    (a), must fail. The mutation target is E16's token-length fact -- one of
    the numbers H1's measurement is read against."""
    here, here_reader, source, there, there_reader = SECTIONS[0]
    text = DOC.read_text()
    tampered = text.replace("(40 in all)", "(41 in all)", 1)
    assert tampered != text, "the mutation target is no longer in the record"
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


def test_the_record_carries_both_headings_inside_section_one():
    """Catches: a block moved out of `## 1.` -- into `## 2.`, or above the
    record's title -- where it would still read as "in the record" but no
    longer as "locked". Every heading in `SECTIONS`, both amendments
    included, which is also what holds them in `SECTIONS` order in §1: an
    unlisted block between two of them would end the earlier one's
    `body_to_heading` read early and fail the verbatim check above."""
    text = DOC.read_text()
    one_at = text.index("## 1. Pre-registration (locked)")
    two_at = text.index("## 2. Part A")
    assert 0 <= one_at < two_at
    for heading, _, _, _, _ in SECTIONS:
        at = text.index(heading)
        assert one_at < at < two_at, heading


# -- what §2 and §3 must look like ---------------------------------------


def test_part_a_begins_not_yet_measured_or_a_measured_heading():
    """Catches: a bare claim -- a number, a verdict -- typed into §2 outside
    either of the two shapes §1 promises. This task's state is the literal
    sentence; a later task's is a `### measured` heading; nothing else."""
    text = DOC.read_text()
    lines = text.splitlines()
    idx = lines.index("## 2. Part A")
    first = next(ln for ln in lines[idx + 1:] if ln.strip())
    assert (first == "Not yet measured."
            or first.startswith("### measured")), first


def test_part_b_begins_not_yet_measured_or_a_measured_heading():
    """The same gate on §3, opened the day part B was pre-registered and
    long before it is run: a section that exists but holds no measurement
    is the one place a number could be typed in ahead of the instrument
    that is supposed to produce it."""
    text = DOC.read_text()
    lines = text.splitlines()
    idx = lines.index("## 3. Part B")
    first = next(ln for ln in lines[idx + 1:] if ln.strip())
    assert (first == "Not yet measured."
            or first.startswith("### measured")), first


def test_part_c_begins_not_yet_measured_or_a_measured_heading():
    """The same gate on §4, opened the day part C was pre-registered and
    before the retrofit is run on a copy of this box's own store."""
    text = DOC.read_text()
    lines = text.splitlines()
    idx = lines.index("## 4. Part C")
    first = next(ln for ln in lines[idx + 1:] if ln.strip())
    assert (first == "Not yet measured."
            or first.startswith("### measured")), first


def test_the_record_opens_with_its_title_and_no_box_path():
    """Catches: a retitled record, or a box-specific absolute path leaking
    into a document meant to travel with the repo -- outside the one
    sanctioned work-root pin each of blocks (b), (c) and (d) carries
    (`E16_DIR=` for parts A and B, `E16C_DIR=` for part C), which stay
    verbatim because §1 says those blocks are verbatim."""
    text = DOC.read_text()
    assert text.startswith("# E16 — secrets redaction, measured\n")
    stray = [ln for ln in text.splitlines()
             if ("/mnt/" in ln or "/home/" in ln)
             and not any(pin in ln for pin in ("E16_DIR=", "E16C_DIR="))]
    assert stray == [], stray
