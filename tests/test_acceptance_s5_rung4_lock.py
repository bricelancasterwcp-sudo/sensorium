"""The byte-lock on S5 rung 4's acceptance record (plan Task 0, Step 3).

Four claims this rung makes about itself, held by tests rather than by prose:

* **§1 has not moved since it was committed.** The record is the
  pre-registration; a threshold edited after a number is read turns a gate
  into a description of what happened. `byte_lock_check` compares the
  working tree's `## 1.`--`## 2.` slice against the commit that first carried
  it -- a commit that changed nothing under `src/`, `typescript/src/`,
  `rust/` or `corpus/`.
* **§1's bodies are verbatim.** §1 says its two blocks are byte-for-byte the
  design's `## 8` and the plan's `## Pre-registration (…)`. That is checkable
  against `git show <sha>:<source>`, so it is checked here -- a paraphrase, a
  reordered table row or a softened rule would otherwise read as the source
  and never be caught.
* **The hand count has not moved either.** Rung 4's one rule a *human*
  applies rather than an instrument is the hand count: nine LINE rows
  derived from the lens source before `bindings.mjs`, `probe.mjs`, the
  runtime's `line` or the converter's `_on_line` existed. H3 STOPs on a
  wrong count, which is exactly the pressure that would make a row worth
  quietly correcting once the transform has run. The table is a separate
  file, so §1 locks it by CONTENT: §1's last line is its sha256, and the
  check below recomputes that sha from the file on disk. A table edited by
  one byte fails here even though §1's own bytes are untouched.
* **The hand count is the shape §1 asks for, and §1 agrees with it.** Five
  named columns in the pre-registered order, nine numbered rows, a last line
  `N = <count>` whose count is the number of rows -- and the `line` column,
  read in order, equal to the list §1.1 publishes as H3's second reading. A
  pinned table of a different shape, or a §1 whose ordered line list drifted
  from the table it pins, would pass every check above.

Rung 3's record is locked by `tests/test_acceptance_s5_rung3_lock.py`, the
file this one is modelled on; both reuse `rust/tests/acceptance_rung3.py`'s
`byte_lock_check`, which is the same lock rung 3 of the Rust track ran under.

`BYTE_LOCK = None`, or a lock commit missing from a shallow clone, SKIPS BY
NAME. A skipped lock check must never look like a passed one.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402

# `acceptance_rung3`'s module body re-points `acceptance_lib.LOGS`,
# `acceptance_lib.LEDGER` and `acceptance_phases.LOGS` at ITS workspace, and
# `tests/test_acceptance_e6ppp.py` asserts those same pointers for its own
# runner. Every such module is imported at COLLECTION time, so whichever file
# pytest collected last would own the pointer. Restoring what was there
# before this import makes the suites order-independent and costs nothing:
# nothing here writes a log.
_PTRS = (lib.LOGS, lib.LEDGER, ph.LOGS)
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402
lib.LOGS, lib.LEDGER, ph.LOGS = _PTRS

#: The document this module locks.
DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-11-sensorium-s5-rung4-focus.md")

#: The prediction §1 pins by content. Kept as a repo-relative string because
#: that is the spelling §1's last line carries, and the line is compared whole.
HANDCOUNT_REL = ("docs/superpowers/acceptance/"
                 "2026-09-11-sensorium-s5-rung4-handcount.md")
HANDCOUNT = REPO / HANDCOUNT_REL

#: The commit that carried §1 first, and alone. Set at Task 0 Step 3, after
#: the record was committed and before any rung-4 code existed. `None` skips
#: every real-document check BY NAME.
BYTE_LOCK = "a60917f"

#: §1 of this record is committed once and never amended.
ORIGINAL_LOCK = None

_SPEC = ("docs/superpowers/specs/"
         "2026-09-11-sensorium-s5-rung4-focus-tier-design.md")
_PLAN = ("docs/superpowers/plans/"
         "2026-09-11-sensorium-s5-rung4-focus-tier.md")
_SPEC_HEAD = "## 8. Acceptance — E12, pre-registered (section 7, approved)"
_PLAN_HEAD = ("## Pre-registration (Task 0 commits spec §8's table verbatim "
              "as the record's §1, plus this block)")

#: Every verbatim block of §1: (its heading HERE, source commit, source file,
#: its heading THERE). The record carries each source heading as a `###`, so
#: both differ from their record spelling by exactly one `#` -- the one
#: editorial act §1 declares.
SECTIONS = (
    (f"### {_SPEC_HEAD[3:]}", "aea6b47", _SPEC, _SPEC_HEAD),
    (f'### Plan section "{_PLAN_HEAD[3:]}" — verbatim', "c70b2cf", _PLAN,
     _PLAN_HEAD),
)

#: The eight ids §8's table carries and §3 will report on. Every one is inside
#: the locked range or an endpoint's rule could be written after its number.
ENDPOINTS = ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8")

#: The pre-registered column order of the hand count (plan Task 0, the
#: controller's ruling): five named columns, first and in this order.
HANDCOUNT_HEADER = "| row | line | statement | deltas | unbound |"

#: H3's second reading, as §1.1 publishes it: the rows' `line` values in
#: execution order. Pinned here so the table and §1 cannot drift apart.
LINES_IN_ORDER = [69, 70, 71, 72, 73, 74, 76, 75, 72]

#: R6: §1.5 lists THIRTEEN read commands, verbatim with their arguments, in
#: this order. `U1`/`F1` stand for the run ids, substituted at measurement.
READ_COMMANDS = (
    "info U1",
    "info F1",
    "watch U1 --at parseDiceGroups --expr groups == 0",
    "watch F1 --at parseDiceGroups --expr sides == 20",
    "watch F1 --at parseDiceGroups --expr count == 1",
    "watch F1 --at parseDiceGroups --expr m == null",
    "flow F1 --value 20",
    "flow F1 --value \"'1d20'\"",
    "flow F1 --object e<id>:dice",
    "grep F1 dice --kind LINE",
    "grep F1 parseDiceGroups --kind CALL",
    "frame F1 --fn parseDiceGroups",
    "tree F1",
)


def _require_lock_commits(*shas):
    """The real-document checks read `git show <sha>:<path>`; a shallow
    checkout (CI at depth 1, a `--depth` clone) has no such commit, and
    before Task 0's Step 3 there is no lock sha at all. Skip BY NAME rather
    than pass on a missing commit."""
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) -- this "
                        "check is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) -- this check is skipped BY NAME, "
                        "not passed")


def _at(commit: str, rel: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{rel}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise Refused(f"cannot read {rel} at {commit}")
    return r.stdout


def body(text: str, heading: str) -> str:
    """One section's body: the lines after `heading` up to the next heading
    of any level, with leading and trailing blank lines dropped.

    Blank lines are dropped at the ends because a body that ends a file has
    no trailing blank while the same body followed by another heading does.
    Nothing inside the body is touched -- including the horizontal rule that
    terminates the plan's section, which §1 carries for exactly this reason:
    the rule is inside the body this function extracts, so leaving it out of
    the record would make the record differ from its source."""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.rstrip("\n") == heading:
            break
    else:
        raise Refused(f"no heading {heading!r} in this document")
    out = []
    for line in lines[i + 1:]:
        if re.match(r"^#{1,6} ", line):
            break
        out.append(line)
    return "".join(out).strip("\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _pinned_handcount_line(doc_text: str) -> str:
    """§1's last non-blank line, which is the hand count's `sha256sum` line."""
    s1 = rung3.section1(doc_text).splitlines()
    body_lines = [ln for ln in s1[:-1] if ln.strip()]   # drop the `## 2.` line
    if not body_lines:
        raise Refused("§1 is empty; there is no pinned line to read")
    return body_lines[-1]


def _handcount_rows(text: str) -> list[list[str]]:
    """The numbered rows of the hand-count table, each split on its column
    separators.

    Split on UNESCAPED pipes only: row 3's statement is
    `let m: RegExpExecArray | null;`, whose one pipe a markdown table cell
    cannot hold bare, so the table escapes it `\\|`. Splitting on every `|`
    would give that row an extra column and make a correct table fail the
    shape check below."""
    return [re.split(r"(?<!\\)\|", ln) for ln in text.splitlines()
            if re.match(r"^\| \d+ \|", ln)]


# -- the lock ---------------------------------------------------------------


def test_the_rung4_byte_lock_passes_on_the_real_document():
    """Catches: §1 edited after the pre-registration commit -- a threshold
    moved, an arm added, a rule softened once a number was in hand."""
    _require_lock_commits(BYTE_LOCK)
    rec = rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_bytes"] > 5000, rec["locked_bytes"]


def test_the_rung4_lock_is_one_sha_and_records_no_amendment():
    """Catches: an amendment reported as an original lock. §1 here is
    committed once. Also pins that §1 references no footnote, so the locked
    range and §1 are the same bytes -- a footnote added later would widen the
    range silently."""
    _require_lock_commits(BYTE_LOCK)
    assert ORIGINAL_LOCK is None
    rec = rung3.byte_lock_facts(DOC, BYTE_LOCK, ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"]


def test_the_rung4_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """Catches: a lock that computes two shas, reports them unequal and
    proceeds. The mutation is H3's gate -- the one number in this
    pre-registration that a human's reading of source decides, and so the one
    most worth widening after the transform has printed."""
    _require_lock_commits(BYTE_LOCK)
    text = DOC.read_text()
    moved = text.replace("**N = 9**", "**N = 8**", 1)
    assert moved != text, "the mutation target is no longer in §1"
    doc = tmp_path / DOC.name
    doc.write_text(moved)
    with pytest.raises(Refused) as e:
        rung3.byte_lock_check(doc, BYTE_LOCK, ORIGINAL_LOCK,
                              read_committed=lambda rel, c: text)
    assert "differs from the byte-lock" in str(e.value)


def test_the_locked_range_is_exactly_section_one():
    """Catches: a lock that slices the wrong range -- §1 plus §2's pins, or
    §1 truncated at its first sub-heading. The slice must start at `## 1.`
    and end at the `## 2.` line, and contain both verbatim blocks and all
    five sub-sections."""
    _require_lock_commits(BYTE_LOCK)
    s1 = rung3.section1(DOC.read_text())
    assert s1.startswith("## 1. Pre-registration")
    assert s1.splitlines()[-1].startswith("## 2. Ambient pins")
    for heading, _, _, _ in SECTIONS:
        assert heading in s1, heading
    for n, name in ((1, "The hand count for H3"),
                    (2, "Three `watch` triples for H4"),
                    (3, "Two `flow --value` sightings for H5"),
                    (4, "The identity for H6"),
                    (5, "The read commands")):
        assert f"### 1.{n} {name}" in s1, n
    assert "| Item | Command | Value |" not in s1  # §2's tables are outside it


def test_every_endpoint_of_this_rung_is_inside_the_locked_range():
    """Catches: an endpoint pre-registered in prose but left out of §1, whose
    rule could then be written after its number was read. The eight ids the
    design's §8 table carries are the eight §3 will report on, and all eight
    are locked here."""
    _require_lock_commits(BYTE_LOCK)
    s1 = rung3.section1(DOC.read_text())
    for endpoint in ENDPOINTS:
        assert f"| {endpoint} |" in s1, endpoint


# -- the verbatim claim -----------------------------------------------------


def test_every_block_of_s1_is_its_source_verbatim():
    """Catches: a body paraphrased, reordered, re-worded or silently
    tightened while §1 still says "byte-for-byte". Each block is compared to
    its section at the commit §1 names, not to the working tree's copy of the
    spec -- so an edit to the spec on a later commit cannot make a drifted
    record look faithful."""
    _require_lock_commits(BYTE_LOCK, *{s[1] for s in SECTIONS})
    doc = DOC.read_text()
    mismatched = []
    for here, sha, rel, there in SECTIONS:
        mine, theirs = body(doc, here), body(_at(sha, rel), there)
        if mine != theirs:
            mismatched.append(
                f"{there} @ {sha}: record "
                f"{hashlib.sha256(mine.encode()).hexdigest()[:12]} "
                f"({len(mine.encode())} B) vs source "
                f"{hashlib.sha256(theirs.encode()).hexdigest()[:12]} "
                f"({len(theirs.encode())} B)")
    assert not mismatched, "\n".join(mismatched)


def test_the_verbatim_check_REFUSES_a_body_that_differs_by_one_byte():
    """Catches: a verbatim check that compares a body to itself, or that
    compares nothing because a heading lookup silently returned empty. The
    same comparison, on a source with one character changed, must fail. The
    target is H6's count -- a gate whose "exactly two sightings" is the whole
    endpoint."""
    _require_lock_commits(BYTE_LOCK)
    here, sha, rel, there = SECTIONS[0]
    mine = body(DOC.read_text(), here)
    tampered = _at(sha, rel).replace("exactly two sightings",
                                     "exactly three sightings", 1)
    assert "exactly three sightings" in tampered, "the mutation target moved"
    assert body(tampered, there) != mine


def test_the_lens_and_subject_paragraph_is_in_the_verbatim_spec_block():
    """Catches: §1 carrying the endpoint TABLE and leaving the paragraph that
    names what is measured out. H3's rule says "the FIRST activation of
    `parseDiceGroups` in F" and names no test for which file, which function
    or which two runs; the paragraph that fixes the lens, the store, the
    subject and the two runs is half the gate. A §1 with the table and
    without it would lock a rule with its hardest half missing, and every
    check above would still pass."""
    _require_lock_commits(BYTE_LOCK)
    block = body(DOC.read_text(), SECTIONS[0][0])
    # Needles stay inside one source line: §8 hard-wraps, so a phrase that
    # spans a wrap would fail on a document that carries the paragraph.
    assert "**§1 is committed alone and byte-locked**" in block
    assert "read-only for the whole run" in block
    assert "and three pure functions of `src/lib/diceQueue.ts`" in block
    assert "**Lens sentence.**" in block


def test_a_missing_heading_is_refused_not_silently_empty():
    """Catches: the failure mode above at its root -- `body()` returning `""`
    for a heading that is not there would make every comparison against it
    pass the moment two blocks both went missing."""
    with pytest.raises(Refused):
        body("## 1. Pre-registration\n\nnothing here\n", _SPEC_HEAD)


# -- the hand count, pinned by content --------------------------------------


def test_s1_ends_with_the_hand_counts_sha256_and_the_file_still_matches():
    """Catches: the prediction edited after the transform printed. §1's bytes
    would not move -- the table is a different file -- so the byte-lock above
    cannot see it. The pin is §1's last line, in `sha256sum` format, and this
    recomputes it from the file on disk."""
    _require_lock_commits(BYTE_LOCK)
    line = _pinned_handcount_line(DOC.read_text())
    assert line == f"{_sha256(HANDCOUNT)}  {HANDCOUNT_REL}", line


def test_the_hand_count_pin_REFUSES_a_table_that_differs_by_one_byte(tmp_path):
    """Catches: a pin that is written down and never recomputed. One byte --
    an `unbound` list trimmed to whatever the transform turned out to write --
    must fail the comparison above."""
    _require_lock_commits(BYTE_LOCK)
    pinned = _pinned_handcount_line(DOC.read_text()).split("  ")[0]
    moved = tmp_path / HANDCOUNT.name
    moved.write_bytes(HANDCOUNT.read_text()
                      .replace("| m | count, sides |", "| m | count |", 1)
                      .encode())
    assert moved.read_bytes() != HANDCOUNT.read_bytes(), "mutation target moved"
    assert _sha256(moved) != pinned


def test_the_hand_count_is_the_shape_the_pre_registration_describes():
    """Catches: a table that is pinned but is not the table §1 asks for -- a
    row dropped, a column reordered, or the `N =` line left off. The
    controller's ruling fixes the five named columns and their order and that
    the last line is `N = <count>`; the rows are numbered from 1; and the
    count on that last line is the number of rows, so a tenth row could not
    arrive without moving N."""
    _require_lock_commits(BYTE_LOCK)
    text = HANDCOUNT.read_text()
    assert HANDCOUNT_HEADER in text, "the column order is not the pre-registered one"
    rows = _handcount_rows(text)
    assert len(rows) == 9, len(rows)
    assert [r[1].strip() for r in rows] == [str(n) for n in range(1, 10)]
    for r in rows:
        assert len(r) == 8, r[:70]          # six columns -> eight pipe fields
        for cell in (r[4], r[5]):           # deltas, unbound
            assert cell.strip() == "-" or re.fullmatch(
                r"[A-Za-z_$][A-Za-z0-9_$]*(, [A-Za-z_$][A-Za-z0-9_$]*)*",
                cell.strip()), cell
    last = text.splitlines()[-1]
    assert re.fullmatch(r"N = \d+", last), last
    assert int(last.split("=")[1]) == len(rows), last


def test_the_hand_counts_lines_are_the_list_section_one_publishes():
    """Catches: §1.1's ordered line list and the table it pins drifting
    apart. H3's second reading is that list; if it were copied wrong, a
    correct transform would fail the reading while the table said otherwise.
    The list is also the claim that a block-like statement's row carries its
    FIRST line -- 75 before 72 at the end, not 77 and 78 -- so a table that
    quietly moved to closing-brace lines fails here."""
    _require_lock_commits(BYTE_LOCK)
    rows = _handcount_rows(HANDCOUNT.read_text())
    assert [int(r[2].strip()) for r in rows] == LINES_IN_ORDER
    # §1 hard-wraps, so the published list spans a line break; compare
    # against §1 with its whitespace collapsed rather than pin the wrap.
    s1 = " ".join(rung3.section1(DOC.read_text()).split())
    published = "**" + ", ".join(str(n) for n in LINES_IN_ORDER) + "**"
    assert published in s1, published


def test_section_1_5_lists_the_thirteen_read_commands_verbatim():
    """Catches: a read added, dropped or re-spelled after the fact. The
    journal's pre-registered delta is one line per command in §1.5's list, so
    the list IS the expected delta; a fourteenth read slipped in later would
    make the assembler's check pass against a moved target. The plan block
    §1 carries says "twelve", counting only the three F1 `watch` triples;
    §1.5 says thirteen and is the one the journal is checked against."""
    _require_lock_commits(BYTE_LOCK)
    s1 = rung3.section1(DOC.read_text())
    fence = re.search(r"```\n(info U1\n.*?)```", s1, re.S)
    assert fence, "§1.5's fenced command list is missing"
    assert fence.group(1).splitlines() == list(READ_COMMANDS)
    assert len(READ_COMMANDS) == 13
    assert "**The journal's expected delta is the length of this list: " \
           "thirteen lines**" in s1
