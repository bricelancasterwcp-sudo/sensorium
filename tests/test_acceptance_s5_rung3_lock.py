"""The byte-lock on S5 rung 3's acceptance record (plan Task 0, Step 4).

Three claims this rung makes about itself, held by tests rather than by prose:

* **§1 has not moved since it was committed.** The record is the
  pre-registration; a threshold edited after a number is read turns a gate
  into a description of what happened. `byte_lock_check` compares the
  working tree's `## 1.`--`## 2.` slice against the commit that first carried
  it.
* **§1's bodies are verbatim.** §1 says its two blocks are byte-for-byte the
  design's `## 5` and the plan's `## Pre-registration (…)`. That is checkable
  against `git show <sha>:<source>`, so it is checked here -- a paraphrase, a
  reordered table row or a softened rule would otherwise read as the source
  and never be caught.
* **The hand-read table has not moved either.** Rung 3's one rule a *human*
  applies rather than an instrument is the hand read: seventeen predictions
  about what the untraced catcher is and which frame went on, written before
  any rung-3 code existed. E6-TS‴ STOPs on a wrong row, which is exactly the
  pressure that would make a row worth quietly correcting once the reader has
  printed. The table is a separate file, so §1 locks it by CONTENT: §1's last
  line is its sha256, and the check below recomputes that sha from the file
  on disk. A table edited by one byte fails here even though §1's own bytes
  are untouched.

Rung 2's record is locked by `tests/test_acceptance_s5_rung2_lock.py`, the
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
       / "2026-09-10-sensorium-s5-rung3.md")

#: The prediction §1 pins by content. Kept as a repo-relative string because
#: that is the spelling §1's last line carries, and the line is compared whole.
HANDREAD_REL = ("docs/superpowers/acceptance/"
                "2026-09-10-sensorium-s5-rung3-handread.md")
HANDREAD = REPO / HANDREAD_REL

#: The commit that carried §1 first, and alone. Set at Task 0 Step 4, after
#: the record was committed and before any rung-3 code existed. `None` skips
#: every real-document check BY NAME.
BYTE_LOCK = "61816a5"

#: §1 of this record is committed once and never amended.
ORIGINAL_LOCK = None

_SPEC = ("docs/superpowers/specs/"
         "2026-09-10-sensorium-s5-rung3-naming-ambiguity-design.md")
_PLAN = ("docs/superpowers/plans/"
         "2026-09-10-sensorium-s5-rung3-naming-ambiguity.md")
_PLAN_HEAD = ("## Pre-registration (Task 0 commits spec §5 verbatim as the "
              "record's §1, plus this block)")

#: Every verbatim block of §1: (its heading HERE, source commit, source file,
#: its heading THERE). The record carries each source heading as a `###`, so
#: both differ from their record spelling by exactly one `#` -- the one
#: editorial act §1 declares.
SECTIONS = (
    ("### 5. Pre-registered endpoints", "51978b1", _SPEC,
     "## 5. Pre-registered endpoints"),
    (f'### Plan section "{_PLAN_HEAD[3:]}" — verbatim', "11a02a4", _PLAN,
     _PLAN_HEAD),
)

#: The eight ids §5's table carries and §3 will report on. Every one is inside
#: the locked range or an endpoint's rule could be written after its number.
ENDPOINTS = ("E6-TS‴", "E6-TS′-fence", "E-places", "E6-TS", "E8‴", "E7‴",
             "E-legacy", "E-branch")


def _require_lock_commits(*shas):
    """The real-document checks read `git show <sha>:<path>`; a shallow
    checkout (CI at depth 1, a `--depth` clone) has no such commit, and
    before Task 0's Step 4 there is no lock sha at all. Skip BY NAME rather
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


def _pinned_handread_line(doc_text: str) -> str:
    """§1's last non-blank line, which is the hand read's `sha256sum` line."""
    s1 = rung3.section1(doc_text).splitlines()
    body_lines = [ln for ln in s1[:-1] if ln.strip()]   # drop the `## 2.` line
    if not body_lines:
        raise Refused("§1 is empty; there is no pinned line to read")
    return body_lines[-1]


# -- the lock ---------------------------------------------------------------


def test_the_rung3_byte_lock_passes_on_the_real_document():
    """Catches: §1 edited after the pre-registration commit -- a threshold
    moved, an arm added, a rule softened once a number was in hand."""
    _require_lock_commits(BYTE_LOCK)
    rec = rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)
    assert rec["identical"] is True
    assert rec["locked_bytes"] > 5000, rec["locked_bytes"]


def test_the_rung3_lock_is_one_sha_and_records_no_amendment():
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


def test_the_rung3_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """Catches: a lock that computes two shas, reports them unequal and
    proceeds. The mutation is E6-TS‴'s gate -- the one number in this
    pre-registration that a human's reading of source decides, and so the one
    most worth widening after the fact."""
    _require_lock_commits(BYTE_LOCK)
    text = DOC.read_text()
    moved = text.replace("**0 false names**", "**1 false name**", 1)
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
    and end at the `## 2.` line, and contain all three of §1's blocks."""
    _require_lock_commits(BYTE_LOCK)
    s1 = rung3.section1(DOC.read_text())
    assert s1.startswith("## 1. Pre-registration")
    assert s1.splitlines()[-1].startswith("## 2. Ambient pins")
    for heading, _, _, _ in SECTIONS:
        assert heading in s1, heading
    assert "### The hand read this pre-registration locks" in s1
    assert "| Item | Command | Value |" not in s1  # §2's tables are outside it


def test_every_endpoint_of_this_rung_is_inside_the_locked_range():
    """Catches: an endpoint pre-registered in prose but left out of §1, whose
    rule could then be written after its number was read. The eight ids the
    design's §5 table carries are the eight §3 will report on, and all eight
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
    target is E-places' count -- a gate whose `28` is the whole endpoint."""
    _require_lock_commits(BYTE_LOCK)
    here, sha, rel, there = SECTIONS[0]
    mine = body(DOC.read_text(), here)
    tampered = _at(sha, rel).replace("exactly **28**", "exactly **29**", 1)
    assert "exactly **29**" in tampered, "the mutation target moved"
    assert body(tampered, there) != mine


def test_the_hand_read_paragraph_is_in_the_verbatim_spec_block():
    """Catches: §1 carrying the endpoint TABLE and leaving the hand read's
    definition out. E6-TS‴'s rule says "compared to the hand-read table's row
    for that origin" and names no test for what a row must contain; the
    paragraph that defines it -- what is opened, what is predicted, and that
    an undecidable shape is predicted `unnamed` -- is half the gate. A §1 with
    the table and without the paragraph would lock a rule with its hardest
    half missing, and every check above would still pass."""
    _require_lock_commits(BYTE_LOCK)
    block = body(DOC.read_text(), SECTIONS[0][0])
    assert "**The hand-read table (T0).**" in block
    # Needles stay inside one source line: §5 hard-wraps, so a phrase that
    # spans a wrap would fail on a document that carries the paragraph.
    assert "cannot decide is predicted `unnamed`" in block
    assert "**Stop rules** as rung 2's" in block


def test_a_missing_heading_is_refused_not_silently_empty():
    """Catches: the failure mode above at its root -- `body()` returning `""`
    for a heading that is not there would make every comparison against it
    pass the moment two blocks both went missing."""
    with pytest.raises(Refused):
        body("## 1. Pre-registration\n\nnothing here\n",
             "### 5. Pre-registered endpoints")


# -- the hand read, pinned by content ---------------------------------------


def test_s1_ends_with_the_hand_reads_sha256_and_the_file_still_matches():
    """Catches: the prediction edited after the reader printed. §1's bytes
    would not move -- the table is a different file -- so the byte-lock above
    cannot see it. The pin is §1's last line, in `sha256sum` format, and this
    recomputes it from the file on disk."""
    _require_lock_commits(BYTE_LOCK)
    line = _pinned_handread_line(DOC.read_text())
    assert line == f"{_sha256(HANDREAD)}  {HANDREAD_REL}", line


def test_the_hand_read_pin_REFUSES_a_table_that_differs_by_one_byte(tmp_path):
    """Catches: a pin that is written down and never recomputed. One byte --
    a predicted parent renamed to whatever the reader turned out to print --
    must fail the comparison above."""
    _require_lock_commits(BYTE_LOCK)
    pinned = _pinned_handread_line(DOC.read_text()).split("  ")[0]
    moved = tmp_path / HANDREAD.name
    moved.write_bytes(HANDREAD.read_text()
                      .replace("`useCompendiumQuery.queryFn`",
                               "`useCompendiumQuery.queryFns`", 1)
                      .encode())
    assert moved.read_bytes() != HANDREAD.read_bytes(), "mutation target moved"
    assert _sha256(moved) != pinned


def test_the_hand_read_is_the_shape_the_pre_registration_describes():
    """Catches: a table that is pinned but is not the table §1 asks for -- a
    row dropped, a column reordered, or the predicted-`unnamed` count left
    off. The plan's block fixes seventeen rows, the column order, and that
    the last line is the predicted count; all three are checked against the
    file, so a pin cannot certify a differently-shaped prediction."""
    _require_lock_commits(BYTE_LOCK)
    text = HANDREAD.read_text()
    header = ("| # | origin as printed | raise site | traced callers to the "
              "test | untraced catcher the source shows | predicted variant "
              "| predicted parent qualname | reading |")
    assert header in text, "the column order is not the pre-registered one"
    rows = [ln for ln in text.splitlines() if re.match(r"^\| \d+ \|", ln)]
    assert len(rows) == 17, len(rows)
    assert [r.split("|")[1].strip() for r in rows] == [
        str(n) for n in range(1, 18)]
    for r in rows:
        assert len(r.split("|")) == 10, r[:70]
        variant = r.split("|")[6].strip().strip("`")
        assert variant in ("returned", "had not closed", "later unwound",
                           "unnamed"), variant
        assert r.split("|")[8].strip() in ("first reading", "second reading")
    last = text.splitlines()[-1]
    assert re.fullmatch(r"predicted unnamed after rung 3: \d+", last), last


def test_the_hand_reads_origins_are_the_transcripts_catch_all_lines():
    """Catches: a row invented, dropped or re-keyed. Every row's `origin as
    printed` must be, byte for byte, the RAISE line above one of the
    transcript's seventeen `no rule of this recorder` lines, in transcript
    order -- otherwise the table predicts about shapes the lens never
    printed, and E6-TS‴ would compare the reader against a fiction."""
    _require_lock_commits(BYTE_LOCK)
    transcript = (REPO / "docs" / "superpowers" / "acceptance"
                  / "2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt")
    lines = transcript.read_text().splitlines()
    want = [lines[i - 1].lstrip() for i, ln in enumerate(lines)
            if "no rule of this recorder" in ln]
    assert len(want) == 17, len(want)
    rows = [ln for ln in HANDREAD.read_text().splitlines()
            if re.match(r"^\| \d+ \|", ln)]
    got = [r.split("|")[2].strip().strip("`") for r in rows]
    assert got == want
