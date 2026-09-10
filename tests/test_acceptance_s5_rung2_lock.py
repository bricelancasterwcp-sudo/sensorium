"""The byte-lock on S5 rung 2's acceptance record (plan P8).

Two claims this document makes about itself, held by a test rather than by
prose:

* **§1 has not moved since it was committed.** The record is the
  pre-registration; a threshold edited after a number is read turns a gate
  into a description of what happened. `byte_lock_check` compares the
  working tree's `## 1.`--`## 2.` slice against the same slice at the commit
  that first carried it.
* **§1's bodies are verbatim.** §1 says its two blocks are byte-for-byte the
  spec's and the plan's sections. That is checkable against
  `git show <sha>:<source>`, so it is checked here -- a paraphrase, a
  reordered table row or a softened rule would otherwise read as the source
  and never be caught.

This rung has one rule a **human** applies rather than an instrument: E6-TS′'s
adjudication protocol, the definition of a *true* SWALLOWED line. It is the
one thing here that could be widened by a sentence after a transcript is read
and still look like the rule it always was. It is inside the locked range, and
the mutation check below is aimed at that endpoint's gate.

Slice 2's record is locked by `tests/test_acceptance_s5_slice2_lock.py`, the
file this one is modelled on; both reuse `rust/tests/acceptance_rung3.py`'s
`byte_lock_check`, which is the same lock rung 3 ran under.

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
       / "2026-09-10-sensorium-s5-rung2.md")

#: The commit that carried §1 first, and alone. Set at Task 0 Step 2, after
#: the record was committed and before any rung-2 code existed. `None` skips
#: every real-document check BY NAME.
BYTE_LOCK = "779b4ef"

#: §1 of this record is committed once and never amended.
ORIGINAL_LOCK = None

_SPEC = ("docs/superpowers/specs/"
         "2026-09-10-sensorium-s5-rung2-throw-flow-design.md")
_PLAN = "docs/superpowers/plans/2026-09-10-sensorium-s5-rung2-throw-flow.md"
_PLAN_HEAD = ("## Pre-registration (Task 0 commits spec §7's table and its "
              "adjudication protocol verbatim as the record's §1, plus these "
              "pins)")

#: Every verbatim block of §1: (its heading HERE, source commit, source file,
#: its heading THERE). The record carries each source heading as a `###`, so
#: both differ from their record spelling by exactly one `#` -- the one
#: editorial act §1 declares.
SECTIONS = (
    ("### 7. Pre-registered endpoints", "db37351", _SPEC,
     "## 7. Pre-registered endpoints"),
    (f'### Plan section "{_PLAN_HEAD[3:]}" — verbatim', "f0a38e0", _PLAN,
     _PLAN_HEAD),
)


def _require_lock_commits(*shas):
    """The real-document checks read `git show <sha>:<path>`; a shallow
    checkout (CI at depth 1, a `--depth` clone) has no such commit, and
    before Task 0's Step 2 there is no lock sha at all. Skip BY NAME rather
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
    Nothing inside the body is touched."""
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


# -- the lock ---------------------------------------------------------------


def test_the_rung2_byte_lock_passes_on_the_real_document():
    """Catches: §1 edited after the pre-registration commit -- a threshold
    moved, an arm added, a rule softened once a number was in hand."""
    _require_lock_commits(BYTE_LOCK)
    rec = rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_bytes"] > 5000, rec["locked_bytes"]


def test_the_rung2_lock_is_one_sha_and_records_no_amendment():
    """Catches: an amendment reported as an original lock. §1 here is
    committed once; E6‴'s was amended and carries two shas, and a record that
    silently claimed this shape would be describing another document. Also
    pins that §1 references no footnote, so the locked range and §1 are the
    same bytes -- a footnote added later would widen the range silently."""
    _require_lock_commits(BYTE_LOCK)
    assert ORIGINAL_LOCK is None
    rec = rung3.byte_lock_facts(DOC, BYTE_LOCK, ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"]


def test_the_rung2_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """Catches: a lock that computes two shas, reports them unequal and
    proceeds. The mutation is E6-TS′'s gate -- the one number in this
    pre-registration that a human's reading of a transcript decides, and so
    the one most worth widening after the fact."""
    _require_lock_commits(BYTE_LOCK)
    text = DOC.read_text()
    moved = text.replace("gate **0 false SWALLOWED**",
                         "gate **1 false SWALLOWED**", 1)
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
    and end at the `## 2.` line, and contain both of §1's blocks."""
    _require_lock_commits(BYTE_LOCK)
    s1 = rung3.section1(DOC.read_text())
    assert s1.startswith("## 1. Pre-registration")
    assert s1.splitlines()[-1].startswith("## 2. Ambient pins")
    for heading, _, _, _ in SECTIONS:
        assert heading in s1, heading
    assert "| Item | Command | Value |" not in s1  # §2's table is outside it


def test_every_endpoint_of_this_rung_is_inside_the_locked_range():
    """Catches: an endpoint pre-registered in prose but left out of §1, whose
    rule could then be written after its number was read. The nine ids the
    spec's §7 table carries are the nine §3 reports on, and all nine are
    locked here."""
    _require_lock_commits(BYTE_LOCK)
    s1 = rung3.section1(DOC.read_text())
    for endpoint in ("E6-TS", "E6-TS′", "E8″", "E2″", "E3-TS″", "E5″", "E7″",
                     "E1‴", "E10″"):
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
    target is E2″'s ratio -- a gate whose `1.000` is the whole endpoint."""
    _require_lock_commits(BYTE_LOCK)
    here, sha, rel, there = SECTIONS[0]
    mine = body(DOC.read_text(), here)
    tampered = _at(sha, rel).replace("ratio 1.000 after NAMED exclusions",
                                     "ratio 0.500 after NAMED exclusions", 1)
    assert "ratio 0.500" in tampered, "the mutation target moved"
    assert body(tampered, there) != mine


def test_the_adjudication_protocol_is_in_the_verbatim_spec_block():
    """Catches: §1 carrying the endpoint TABLE and leaving the protocol out.
    The table's E6-TS′ rule says "adjudicated by hand" and names no test for
    *true*; the paragraph that defines it is the gate. A §1 with the table
    and without the paragraph would lock a rule with its hardest half
    missing, and every check above would still pass."""
    _require_lock_commits(BYTE_LOCK)
    block = body(DOC.read_text(), SECTIONS[0][0])
    assert "**The adjudication protocol for E6-TS′**" in block
    assert "a line the adjudicator cannot decide from the" in block
    assert "**Stop rules** as slice 2's" in block


def test_a_missing_heading_is_refused_not_silently_empty():
    """Catches: the failure mode above at its root -- `body()` returning `""`
    for a heading that is not there would make every comparison against it
    pass the moment two blocks both went missing."""
    with pytest.raises(Refused):
        body("## 1. Pre-registration\n\nnothing here\n",
             "### 7. Pre-registered endpoints")
