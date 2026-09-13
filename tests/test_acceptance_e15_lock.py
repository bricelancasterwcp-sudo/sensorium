"""The byte-lock on E15's acceptance record (plan Task 0, Step 5).

Six claims this slice makes about itself, held by tests rather than by prose:

* **§1 has not moved since it was written.** The record is the
  pre-registration; a threshold edited after a number is read turns a gate
  into a description of what happened. `byte_lock_check` recomputes the
  sha256 of the working tree's `## 1.`--`## 2.` slice and compares it against
  `BYTE_LOCK` below, which was computed once, before the commit that carried
  §1 -- a commit that changed nothing under `src/`, `typescript/src/` or
  `rust/`, and under `corpus/` only the three case directories §1 itself
  pre-registers as RED.

  A content sha rather than `git show <lock commit>:<doc>`, for the reason
  `tests/test_acceptance_s5_debts_lock.py` gives: §1, the survey table, the
  three RED cases and this file are ONE commit, so a commit-shaped lock could
  not be verified before the commit it names exists. A content sha can be,
  and is: the check below was run green on the working tree first and the
  commit carries the verified pair. Both forms fail on the same mutation --
  one byte of §1 -- and both rest on the same assumption, that the test and
  the record are not edited together.

* **§1 was amended once, and BOTH end-shas are carried.** Controller ruling
  P16 found two clauses of the H1--H10 table to be pre-registration errors
  BEFORE any endpoint ran: H7 asks for a `licence: WITHHELD` line that
  `refocus_report.py` prints only on a MATCH -- a DIVERGED prints the world
  block and no licence at all -- and H8's locked command omits the `--focus`
  that `refocus_cmd.py` makes `required=True`, so argparse refuses the call
  before design §2.3's refusal 1 can run. Neither clause is edited: each is
  measured and reported as written and STOPs where its literal fails, which
  is a finding about the pre-registration. A dated paragraph inside §1
  pre-registers the corrected clauses H7′ and H8′ beside them, with both
  readings of each. `ORIGINAL_LOCK` is §1's sha as the pre-registration
  commit carried it, before the amendment, and `BYTE_LOCK` its sha after;
  the check below recomputes the ORIGINAL out of `ORIGINAL_COMMIT` rather
  than trusting the constant -- so "amended, from exactly that text" is a
  fact git holds. The amendment ADDED a paragraph and moved no table row and
  no bullet of the pre-registration, which is its own test.

* **§1's two bodies are verbatim.** §1 says its two blocks are byte-for-byte
  the design's `## 5. E15, pre-registered` and the plan's `## Pre-registration
  (…)`. That is checkable against `git show <sha>:<source>`, so it is checked
  here -- a paraphrase, a reordered table row or a softened endpoint would
  otherwise read as the source and never be caught. The two bodies end
  differently in their sources and so are read differently here: the design's
  section runs to the next heading, the plan's to the horizontal rule that
  terminates it, which is §1's own stated rule.

* **The survey table has not moved either.** The 31 rows of the selection --
  a class, a focus spec and a resolver count per file -- are the one part of
  this pre-registration a human's reading of source decides rather than an
  instrument, and therefore the one worth quietly correcting once the loop
  has printed 31 verdicts. It is a separate file, so §1 locks it by CONTENT:
  §1's second-to-last line is its sha256, and the check below recomputes it
  from the file on disk. A table edited by one byte fails here even though
  §1's own bytes are untouched.

* **The survey is the shape §1 asks for.** Six named columns in the
  pre-registered order, rows numbered from 1, and a last line `N = <count>`
  whose count is the number of rows. A pinned table of a different shape
  would pass every check above.

* **Every endpoint is inside the locked range.** H1--H10 are what §3 will
  report on; an endpoint pre-registered in prose outside §1 could have its
  rule written after its number was read.

`BYTE_LOCK = None`, or a source commit missing from a shallow clone, SKIPS BY
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
# other suites assert those same pointers for their own runners. Every such
# module is imported at COLLECTION time, so whichever file pytest collected
# last would own the pointer. Restoring what was there before this import
# makes the suites order-independent and costs nothing: nothing here writes a
# log.
_PTRS = (lib.LOGS, lib.LEDGER, ph.LOGS)
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402
lib.LOGS, lib.LEDGER, ph.LOGS = _PTRS

#: The document this module locks.
DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-13-sensorium-e15-refocus-typescript.md")

#: The prediction §1 pins by content. Kept as a repo-relative string because
#: that is the spelling §1's own line carries, and the line is compared whole.
SURVEY_REL = ("docs/superpowers/acceptance/"
              "2026-09-13-sensorium-e15-refocus-typescript-survey.md")
SURVEY = REPO / SURVEY_REL

#: The sha256 of §1 as it now stands: the ORIGINAL lock plus the one dated
#: amendment (ruling P16's H7′/H8′ pre-registration, added before any
#: endpoint ran). `None` skips every real-document check BY NAME.
BYTE_LOCK = "044b9231dc1aea0cff14d3722ced37f2dc70c20e4c51875c2647414c67ba4b1d"

#: The sha256 of §1 as the pre-registration commit carried it, before the
#: amendment. Both shas travel together so the amendment is a visible fact of
#: the record rather than a claim in its prose.
ORIGINAL_LOCK = "40298b4f7eac78f066a2bcd54716ad028d5bfd05c862fe676fdc3207ce876fa8"

#: The commit that carried §1 first and alone: the pre-registration.
#: `ORIGINAL_LOCK` is RECOMPUTED from this commit's copy of the document, so
#: the "before" text is git's and not a constant's.
ORIGINAL_COMMIT = "74d574c"

#: The dated sub-heading the amendment added, INSIDE §1 and before the survey
#: pin. Named here so "one paragraph was added" is a check and not a reading
#: of the diff.
AMENDMENT_HEADING = "### Amended 2026-09-13 (ruling P16, before any endpoint ran)"

#: The sha256 of the survey file, which is also §1's second-to-last line.
SURVEY_LOCK = "10433230d34dfd96f7aeede1c637dbb217da1764bc98d00f50474b909ae5d46b"

#: The two source commits. Branch commits, not merge commits: this project
#: merges with a merge commit, so a branch commit stays reachable from `main`
#: afterwards -- the debts slice's precedent.
SPEC_COMMIT = "a8aa533"
PLAN_COMMIT = "4d8f3d9"

_SPEC = ("docs/superpowers/specs/"
         "2026-09-13-sensorium-s5-refocus-typescript-design.md")
_PLAN = ("docs/superpowers/plans/"
         "2026-09-13-sensorium-s5-refocus-typescript.md")
_SPEC_HEAD = "## 5. E15, pre-registered"
_PLAN_HEAD = ("## Pre-registration (Task 0 commits spec §5 verbatim as the "
              "record's §1, plus this block)")

#: The ten ids §5's table carries and §3 will report on. Every one is inside
#: the locked range or an endpoint's rule could be written after its number.
ENDPOINTS = tuple(f"H{n}" for n in range(1, 11))

#: The pre-registered column order of the survey (plan ruling A7): six named
#: columns, first and in this order.
SURVEY_HEADER = "| n | test file | class | reason | focus spec | resolver matched |"

#: The survey's own gate, as §1 publishes it through the plan block.
SURVEY_N = 31


def _require_lock():
    """`BYTE_LOCK = None` is the state between writing this file and
    computing the sha. Skip BY NAME rather than pass on a missing lock."""
    if not BYTE_LOCK:
        pytest.skip("§1 is not locked yet (BYTE_LOCK is None) -- this check "
                    "is skipped BY NAME, not passed")


def _require_source_commits(*shas):
    """The verbatim checks read `git show <sha>:<path>`; a shallow checkout
    (CI at depth 1, a `--depth` clone) has no such commit. Skip BY NAME
    rather than pass on a missing commit."""
    for sha in shas:
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"source commit {sha} is not in this checkout "
                        "(shallow clone) -- this check is skipped BY NAME, "
                        "not passed")


def _at(commit: str, rel: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{rel}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise Refused(f"cannot read {rel} at {commit}")
    return r.stdout


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
    design's `## 5.` ends in its source, and how §1 says it was read."""
    out = []
    for line in _after(text, heading):
        if re.match(r"^#{1,6} ", line):
            break
        out.append(line)
    return "".join(out).strip("\n")


def body_to_rule(text: str, heading: str) -> str:
    """One section's body, read to the horizontal rule that terminates it --
    how the plan's `## Pre-registration (…)` ends in its source.

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


#: Every verbatim block of §1: (its heading HERE, source commit, source file,
#: its heading THERE, the reader that ends the body THERE).
SECTIONS = (
    (f"### {_SPEC_HEAD[3:]}", SPEC_COMMIT, _SPEC, _SPEC_HEAD, body_to_heading),
    ("### Pre-registration (plan)", PLAN_COMMIT, _PLAN, _PLAN_HEAD,
     body_to_rule),
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def byte_lock_facts(doc_text: str, expected: str,
                    original: str | None = None,
                    original_text: str | None = None) -> dict:
    """The lock's numbers, computed and never enforced.

    Split from [`byte_lock_check`] for the reason the debts lock splits its
    own: a reader who wants the two shas beside each other should not have to
    take a refusal to get them.

    `original_text` is the document as the ORIGINAL lock commit carried it.
    When it is given, `original_lock_sha256` is RECOMPUTED from it rather than
    echoed from `original`, and `original_lock_declared_matches` says whether
    the constant agrees -- which is the difference between "the record says it
    was amended" and "git shows it was amended, from exactly that text".
    """
    s1 = rung3.section1(doc_text)
    s1_orig = (rung3.section1(original_text) if original_text is not None
               else None)
    orig_sha = _sha256_text(s1_orig) if s1_orig is not None else original
    return {"doc": DOC.relative_to(REPO).as_posix(),
            "range": "awk '/^## 1/,/^## 2/'",
            "locked_sha256": expected,
            "working_tree_sha256": _sha256_text(s1),
            "section1_sha256": _sha256_text(s1),
            "working_tree_bytes": len(s1.encode()),
            "locked_bytes": len(s1.encode()),
            "identical": _sha256_text(s1) == expected,
            "original_lock": ORIGINAL_COMMIT if original else None,
            "original_lock_sha256": orig_sha,
            "original_lock_declared_matches": (orig_sha == original
                                               if original else None),
            "original_lock_bytes": (len(s1_orig.encode())
                                    if s1_orig is not None else None),
            "amended_after_the_original_lock": bool(orig_sha
                                                    and orig_sha != expected),
            "amendment_bytes": (len(s1.encode()) - len(s1_orig.encode())
                                if s1_orig is not None else None),
            "footnotes_in_range": sorted(set(rung3.FOOTNOTE_REF.findall(s1)))}


def byte_lock_check(doc_text: str, expected: str) -> dict:
    """§1 of the record, as the pre-registration fixed it, versus the working
    tree. The endpoint is decided before the instrument exists; this is the
    check that it did not move afterwards."""
    rec = byte_lock_facts(doc_text, expected)
    if not rec["identical"]:
        raise Refused(
            f"the locked range of {rec['doc']} differs from the byte-lock: "
            f"{rec['locked_sha256'][:12]} vs "
            f"{rec['working_tree_sha256'][:12]} (range: {rec['range']})")
    return rec


def _pinned_lines(doc_text: str) -> list[str]:
    """§1's last two non-blank lines: the survey's sha256 first, the plan
    commit second."""
    s1 = rung3.section1(doc_text).splitlines()
    body_lines = [ln for ln in s1[:-1] if ln.strip()]   # drop the `## 2.` line
    if len(body_lines) < 2:
        raise Refused("§1 is too short to carry two pinned lines")
    return body_lines[-2:]


def _survey_rows(text: str) -> list[list[str]]:
    """The numbered rows of the survey, each split on its column separators,
    read from the header line to the `N =` line and from nowhere else.

    Split on UNESCAPED pipes only, for the reason rung 4's lock gives: a
    markdown cell cannot hold a bare `|`, so a cell that needs one escapes it
    and splitting on every `|` would give that row an extra column."""
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == SURVEY_HEADER:
            break
    else:
        raise Refused("the survey carries no header in the pinned order")
    rows = []
    for ln in lines[i + 2:]:                            # skip the separator
        if re.fullmatch(r"N = \d+", ln.strip()):
            return rows
        if re.match(r"^\| \d+ \|", ln):
            rows.append(re.split(r"(?<!\\)\|", ln))
    raise Refused("the survey table has no `N =` line after it")


# -- the lock ---------------------------------------------------------------


def test_section_one_has_not_moved():
    """Catches: §1 edited after the pre-registration commit -- an endpoint
    moved, an arm added, a rule softened once a number was in hand.

    Also pins that §1 references no footnote, so the locked range and §1 are
    the same bytes: a footnote added later would widen the range silently."""
    _require_lock()
    rec = byte_lock_check(DOC.read_text(), BYTE_LOCK)
    assert rec["identical"] is True
    assert rec["working_tree_bytes"] > 5000, rec["working_tree_bytes"]
    assert rec["footnotes_in_range"] == []


def test_the_record_carries_both_shas_and_the_amendment_flag():
    """Catches: an amendment reported as an original lock, or an amendment
    that quietly REPLACED §1 instead of adding to it.

    §1 was amended on 2026-09-13, before any endpoint ran (controller ruling
    P16): H7 asks for a `licence: WITHHELD` line that
    `src/sensorium/query/refocus_report.py` prints only on a MATCH, and H8's
    locked command omits the `--focus` that
    `src/sensorium/query/refocus_cmd.py:186` makes `required=True`. Both
    clauses stand and are measured as written; H7′ and H8′ are pre-registered
    beside them in a dated paragraph. The record must say so with two shas
    and a flag -- a record that reported no amendment would be describing
    another document.

    The ORIGINAL is read from `ORIGINAL_COMMIT`, not from the constant, so
    "amended from exactly that text" is git's fact and not this file's claim.
    That the amendment REMOVED nothing is checked by
    `test_the_amendment_added_a_paragraph_and_moved_no_row` below, not here:
    `locked_bytes == original_lock_bytes + amendment_bytes` is the definition
    of `amendment_bytes` restated -- arithmetic, not a check.
    """
    _require_lock()
    _require_source_commits(ORIGINAL_COMMIT)
    assert BYTE_LOCK != ORIGINAL_LOCK
    rec = byte_lock_facts(DOC.read_text(), BYTE_LOCK, ORIGINAL_LOCK,
                          _at(ORIGINAL_COMMIT, DOC.relative_to(REPO).as_posix()))
    assert rec["amended_after_the_original_lock"] is True
    assert rec["original_lock_sha256"] == ORIGINAL_LOCK
    assert rec["original_lock_declared_matches"] is True
    assert rec["locked_sha256"] == rec["section1_sha256"] == BYTE_LOCK
    assert rec["amendment_bytes"] > 0


def test_the_amendment_added_a_paragraph_and_moved_no_row():
    """The rule the amendment lives by: a pre-registration error found before
    a number is read is pre-registered AGAIN, beside the clause it corrects,
    and the clause it corrects does not move. Every table row of §1 at the
    original lock is a row of §1 now, byte-identical and in the same order;
    so is every bullet of the plan block; every line of the original §1
    survives, in order; and the dated heading appears exactly once, in
    today's §1 and not in the original's.

    An "amendment" that rewrote H7's `licence: WITHHELD` clause or H8's
    locked command -- the two rows this slice now expects to STOP on -- would
    fail here even though both shas moved together.
    """
    _require_lock()
    _require_source_commits(ORIGINAL_COMMIT)
    rel = DOC.relative_to(REPO).as_posix()
    before_s1 = rung3.section1(_at(ORIGINAL_COMMIT, rel))
    after_s1 = rung3.section1(DOC.read_text())
    before, after = before_s1.splitlines(), after_s1.splitlines()

    rows = lambda lines: [ln for ln in lines if ln.startswith("|")]
    bullets = lambda lines: [ln for ln in lines if ln.startswith("- ")]
    assert rows(before) == rows(after), "a table row of §1 moved"
    assert bullets(before) == bullets(after), "a bullet of §1 moved"
    assert len(rows(after)) >= len(ENDPOINTS)          # the H1--H10 table

    # Additions only: every line of the original §1 survives, IN ORDER.
    i = 0
    for ln in before:
        while i < len(after) and after[i] != ln:
            i += 1
        assert i < len(after), f"§1 lost a line, or moved it: {ln!r}"
        i += 1
    assert len(after) > len(before)

    assert AMENDMENT_HEADING not in before_s1
    assert after_s1.count(AMENDMENT_HEADING) == 1
    assert after_s1.count("Amended 2026-09-13") == 1


def test_the_byte_lock_REFUSES_a_document_that_differs_by_one_byte():
    """Catches: a lock that computes two shas, reports them unequal and
    proceeds. The mutation is H2's gate -- `31 of 31` harness exits equal --
    one of the numbers most worth widening once 31 re-runs have printed."""
    _require_lock()
    text = DOC.read_text()
    moved = text.replace("**31 of 31** harness exits equal",
                         "**30 of 31** harness exits equal", 1)
    assert moved != text, "the mutation target is no longer in §1"
    with pytest.raises(Refused) as e:
        byte_lock_check(moved, BYTE_LOCK)
    assert "differs from the byte-lock" in str(e.value)


def test_the_locked_range_is_exactly_section_one():
    """Catches: a lock that slices the wrong range -- §1 plus §2's pins, or
    §1 truncated at its first sub-heading. The slice must start at `## 1.`,
    end at the `## 2.` line, and contain both verbatim blocks."""
    _require_lock()
    s1 = rung3.section1(DOC.read_text())
    assert s1.startswith("## 1. Pre-registration")
    assert s1.splitlines()[-1].startswith("## 2. Environment")
    for heading, _, _, _, _ in SECTIONS:
        assert heading in s1, heading


def test_every_endpoint_of_this_slice_is_inside_the_locked_range():
    """Catches: an endpoint pre-registered in prose but left out of §1, whose
    rule could then be written after its number was read. H1--H10 are what §3
    will report on, and all ten are locked here."""
    _require_lock()
    s1 = rung3.section1(DOC.read_text())
    for endpoint in ENDPOINTS:
        assert f"| {endpoint} |" in s1, endpoint


# -- the verbatim claim -----------------------------------------------------


def test_section_one_carries_the_specs_section_five_verbatim():
    """Catches: the design's `## 5.` paraphrased, reordered or silently
    tightened while §1 still says "byte-for-byte". It is compared against the
    section at the commit §1 names, not against the working tree's copy of
    the design -- so a later edit to the design cannot make a drifted record
    look faithful."""
    _require_lock()
    _require_source_commits(SPEC_COMMIT)
    here, sha, rel, there, reader = SECTIONS[0]
    mine = body_to_heading(DOC.read_text(), here)
    theirs = reader(_at(sha, rel), there)
    assert mine == theirs, (
        f"{there} @ {sha}: record {_sha256_text(mine)[:12]} "
        f"({len(mine.encode())} B) vs source {_sha256_text(theirs)[:12]} "
        f"({len(theirs.encode())} B)")


def test_section_one_carries_the_plans_preregistration_verbatim():
    """The same for the plan's block, read to the `---` that terminates it in
    the plan file rather than to the next heading -- §1's own stated rule,
    and the one that decides whether the rule is part of the body."""
    _require_lock()
    _require_source_commits(PLAN_COMMIT)
    here, sha, rel, there, reader = SECTIONS[1]
    mine = body_to_heading(DOC.read_text(), here)
    theirs = reader(_at(sha, rel), there)
    assert mine == theirs, (
        f"{there} @ {sha}: record {_sha256_text(mine)[:12]} "
        f"({len(mine.encode())} B) vs source {_sha256_text(theirs)[:12]} "
        f"({len(theirs.encode())} B)")


def test_the_verbatim_check_REFUSES_a_body_that_differs_by_one_byte():
    """Catches: a verbatim check that compares a body to itself, or that
    compares nothing because a heading lookup silently returned empty. The
    same comparison, on a source with one character changed, must fail. The
    target is the selection's own size -- `**31** of 372`, the number every
    later count is read against."""
    _require_lock()
    _require_source_commits(SPEC_COMMIT)
    here, sha, rel, there, reader = SECTIONS[0]
    mine = body_to_heading(DOC.read_text(), here)
    tampered = _at(sha, rel).replace("**31** of 372", "**30** of 372", 1)
    assert "**30** of 372" in tampered, "the mutation target moved"
    assert reader(tampered, there) != mine


def test_a_missing_heading_is_refused_not_silently_empty():
    """Catches: the failure mode above at its root -- a reader returning `""`
    for a heading that is not there would make every comparison against it
    pass the moment two blocks both went missing."""
    for reader in (body_to_heading, body_to_rule):
        with pytest.raises(Refused):
            reader("## 1. Pre-registration\n\nnothing here\n", _SPEC_HEAD)


# -- the survey, pinned by content ------------------------------------------


def test_the_survey_table_has_not_moved():
    """Catches: a class, a focus spec or a resolver count edited after the
    loop printed its verdicts. §1's bytes would not move -- the survey is a
    different file -- so the byte lock above cannot see it. The pin is §1's
    second-to-last line, in `sha256sum` format, and this recomputes it from
    the file on disk; the last line is the plan commit the block came from."""
    _require_lock()
    first, second = _pinned_lines(DOC.read_text())
    assert first == f"survey: {_sha256(SURVEY)}", first
    assert first == f"survey: {SURVEY_LOCK}", first
    assert second == f"plan-commit: {PLAN_COMMIT}", second


def test_the_survey_pin_REFUSES_a_table_that_differs_by_one_byte(tmp_path):
    """Catches: a pin that is written down and never recomputed. One byte --
    a resolver count corrected once `resolve.mjs` had printed a different
    one -- must fail the comparison above."""
    _require_lock()
    moved = tmp_path / SURVEY.name
    moved.write_bytes(SURVEY.read_text()
                      .replace("`mergeSheetSnapshot.ts:isDeepEqual` | 3 |",
                               "`mergeSheetSnapshot.ts:isDeepEqual` | 4 |", 1)
                      .encode())
    assert moved.read_bytes() != SURVEY.read_bytes(), "mutation target moved"
    assert _sha256(moved) != SURVEY_LOCK


def test_the_survey_has_thirty_one_rows_and_says_so():
    """Catches: a table that is pinned but is not the table §1 asks for -- a
    row dropped, a column reordered, or the `N =` line left off. Plan ruling
    A7 fixes the six named columns and their order and that the last line is
    `N = <count>`; the rows are numbered from 1; and the count on that last
    line is the number of rows, so a thirty-second row could not arrive
    without moving N."""
    _require_lock()
    text = SURVEY.read_text()
    assert SURVEY_HEADER in text, "the column order is not the pre-registered one"
    rows = _survey_rows(text)
    assert len(rows) == SURVEY_N, len(rows)
    assert [r[1].strip() for r in rows] == [str(n) for n in
                                            range(1, SURVEY_N + 1)]
    for r in rows:
        assert len(r) == 8, r[:80]          # six columns -> eight pipe fields
        assert r[3].strip() in {"deterministic", "nondeterministic",
                                "unsurveyed"}, r[3]
        assert re.fullmatch(r"\d+", r[6].strip()), r[6]
        assert int(r[6].strip()) >= 1, r     # a zero would refuse at E15
    last = text.splitlines()[-1]
    assert re.fullmatch(r"N = \d+", last), last
    assert int(last.split("=")[1]) == len(rows) == SURVEY_N, last
