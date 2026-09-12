"""The byte-lock on S5 rung 4's debts-slice acceptance record (plan Task 0,
Step 6).

Five claims this slice makes about itself, held by tests rather than by prose:

* **§1 has not moved since it was written.** The record is the
  pre-registration; a threshold edited after a number is read turns a gate
  into a description of what happened. `byte_lock_check` recomputes the
  sha256 of the working tree's `## 1.`--`## 2.` slice and compares it against
  `BYTE_LOCK` below, which was computed once, before the commit that carried
  §1 -- a commit that changed nothing under `src/`, `typescript/src/` or
  `rust/`, and under `corpus/` only the three case directories §1 itself
  pre-registers as RED.

  Rung 4's lock read its baseline from `git show <lock commit>:<doc>` instead.
  It could: §1 was committed there in its own commit and the sha was filled in
  afterwards. Here §1, the two tables, the three RED cases and this test are
  ONE commit, so a commit-shaped lock could not be verified before the commit
  it names exists. A content sha can be, and is: the check below is run green
  on the working tree first and the commit carries the verified pair. Both
  forms fail on the same mutation -- one byte of §1 -- and both rest on the
  same assumption, that the test and the record are not edited together.

* **§1's bodies are verbatim.** §1 says its four blocks are byte-for-byte the
  design's `### 3.3`, `### 3.4` and `## 8` and the plan's `## Pre-registration
  (…)`. That is checkable against `git show <sha>:<source>`, so it is checked
  here -- a paraphrase, a reordered table row or a softened rule would
  otherwise read as the source and never be caught. The plan block itself
  names all four, which is why all four are carried and all four are checked.

* **The two hand tables have not moved either.** This slice's two rules a
  *human* applies rather than an instrument are the H2′ function-like count
  (six sites under the container rule) and the seal-deferred census (0 / 1 /
  0). E12′ and E13 STOP on a wrong one, which is exactly the pressure that
  would make a row worth quietly correcting once `resolve.mjs` and
  `census_deferred.mjs` have printed. Each table is a separate file, so §1
  locks it by CONTENT: §1's last two lines are their sha256s, and the checks
  below recompute both from the files on disk. A table edited by one byte
  fails here even though §1's own bytes are untouched.

* **The tables are the shapes §1 asks for.** The hand count: five named
  columns in the pre-registered order, six numbered rows, a last line `N =
  <count>` whose count is the number of rows. The census: three tables in the
  order probes / corpus / lens, each `| file | qualname | line |`, each
  followed by an `N = <count>` that equals its row count, and the lens
  table's N is 0. A pinned table of a different shape would pass every check
  above.

Rung 4's record is locked by `tests/test_acceptance_s5_rung4_lock.py`, the
file this one is modelled on; both reuse `rust/tests/acceptance_rung3.py`'s
`section1`, which is the same range rung 3 and rung 4 of this project locked.

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
       / "2026-09-12-sensorium-s5-rung4-debts.md")

#: The two predictions §1 pins by content. Kept as repo-relative strings
#: because that is the spelling §1's last two lines carry, and the lines are
#: compared whole.
HANDCOUNT_REL = ("docs/superpowers/acceptance/"
                 "2026-09-12-sensorium-s5-rung4-debts-h2-handcount.md")
CENSUS_REL = ("docs/superpowers/acceptance/"
              "2026-09-12-sensorium-s5-rung4-debts-census.md")
HANDCOUNT = REPO / HANDCOUNT_REL
CENSUS = REPO / CENSUS_REL

#: The sha256 of §1, computed at Task 0 Step 6 from the finished record and
#: before the commit that carried it. `None` skips every real-document check
#: BY NAME.
BYTE_LOCK = "11d7c023e25c2321213798454f22261c6e02e5a2a1b30d152cc5ccb04505f0ae"

#: §1 of this record is written once and never amended.
ORIGINAL_LOCK = None

_SPEC = ("docs/superpowers/specs/"
         "2026-09-12-sensorium-s5-rung4-debts-design.md")
_PLAN = ("docs/superpowers/plans/"
         "2026-09-12-sensorium-s5-rung4-debts.md")
_SPEC_SHA = "3ecbb65"
_PLAN_SHA = "5c36baa"
_H33 = "### 3.3 The three readings, pre-registered"
_H34 = "### 3.4 H8′ — the live confirmation"
_H8 = "## 8. Acceptance — pre-registered"
_PLAN_HEAD = ("## Pre-registration (Task 0 commits spec §8's table verbatim "
              "as the record's §1, plus this block)")

#: Every verbatim block of §1: (its heading HERE, source commit, source file,
#: its heading THERE). The design's two `###` sections are carried unchanged;
#: the design's `## 8` and the plan's `## Pre-registration` differ from their
#: record spelling by exactly one `#` -- the one editorial act §1 declares.
SECTIONS = (
    (_H33, _SPEC_SHA, _SPEC, _H33),
    (_H34, _SPEC_SHA, _SPEC, _H34),
    (f"### {_H8[3:]}", _SPEC_SHA, _SPEC, _H8),
    (f'### Plan section "{_PLAN_HEAD[3:]}" — verbatim', _PLAN_SHA, _PLAN,
     _PLAN_HEAD),
)

#: The six ids §8's table carries and §3 will report on. Every one is inside
#: the locked range or an endpoint's rule could be written after its number.
ENDPOINTS = ("E12′ H2′/H4′/H5′", "H8′", "E13", "E14", "E6-TS′", "fences")

#: The three ids §3.3's table carries -- the readings E12′ re-registers.
READINGS = ("H2′", "H4′", "H5′")

#: The nine sub-sections the plan block names, as §1 spells their headings.
SUBSECTIONS = (
    (1, "The hashes"),
    (2, "H2′'s hand count"),
    (3, "H4′"),
    (4, "H5′"),
    (5, "E13 — the finally seal"),
    (6, "E14 — the Rust `unbound`"),
    (7, "E6-TS′"),
    (8, "Fences"),
    (9, "H8′ — the live confirmation, run LAST"),
)

#: The pre-registered column order of the hand count (plan ruling A4): five
#: named columns, first and in this order.
HANDCOUNT_HEADER = "| n | qualname | line | kind | how selected |"

#: ...and the census's (plan ruling A5, the controller's P3): three tables of
#: three named columns, in the order probes / corpus / lens.
CENSUS_HEADER = "| file | qualname | line |"

#: The census's three counts, in table order. The lens list is EMPTY, which is
#: E13's third clause and H8′'s eighth; pinned here so the table and §1 cannot
#: drift apart.
CENSUS_COUNTS = [0, 1, 0]

#: The hand count's own gate, as §1.2 publishes it.
HANDCOUNT_N = 6


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def byte_lock_facts(doc_text: str, expected: str) -> dict:
    """The lock's numbers, computed and never enforced.

    Split from [`byte_lock_check`] for the reason rung 3's helper splits its
    own: a reader that wants the shas beside each other should not have to
    take a refusal to get them."""
    s1 = rung3.section1(doc_text)
    return {"doc": DOC.relative_to(REPO).as_posix(),
            "range": "awk '/^## 1/,/^## 2/'",
            "locked_sha256": expected,
            "working_tree_sha256": _sha256_text(s1),
            "working_tree_bytes": len(s1.encode()),
            "identical": _sha256_text(s1) == expected,
            "footnotes_in_range": sorted(
                set(rung3.FOOTNOTE_REF.findall(s1)))}


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
    """§1's last two non-blank lines, which are the two tables' `sha256sum`
    lines -- the hand count first, the census second."""
    s1 = rung3.section1(doc_text).splitlines()
    body_lines = [ln for ln in s1[:-1] if ln.strip()]   # drop the `## 2.` line
    if len(body_lines) < 2:
        raise Refused("§1 is too short to carry two pinned lines")
    return body_lines[-2:]


def _handcount_rows(text: str) -> list[list[str]]:
    """The numbered rows of the hand-count table, each split on its column
    separators.

    Split on UNESCAPED pipes only, for the reason rung 4's lock gives: a
    markdown cell cannot hold a bare `|`, so a cell that needs one escapes it
    and splitting on every `|` would give that row an extra column."""
    return [re.split(r"(?<!\\)\|", ln) for ln in text.splitlines()
            if re.match(r"^\| \d+ \|", ln)]


def _census_tables(text: str) -> list[tuple[int, int]]:
    """Each census table as `(rows, N)`: how many data rows it carries and
    what its own `N =` line claims.

    A table is a `CENSUS_HEADER` line, its separator, zero or more data rows,
    and -- after whatever prose follows -- the next `N = <count>` line. An
    EMPTY table is the point of two of the three, so "no data rows" is a
    shape this must read rather than a table it must fail to find."""
    lines = text.splitlines()
    out = []
    for i, ln in enumerate(lines):
        if ln.strip() != CENSUS_HEADER:
            continue
        rows = 0
        for nxt in lines[i + 2:]:                       # skip the separator
            if nxt.startswith("|"):
                rows += 1
                continue
            m = re.fullmatch(r"N = (\d+)", nxt.strip())
            if m:
                out.append((rows, int(m.group(1))))
                break
            if nxt.strip():
                continue
        else:
            raise Refused(f"the table at line {i + 1} has no `N =` line")
    return out


# -- the lock ---------------------------------------------------------------


def test_the_debts_byte_lock_passes_on_the_real_document():
    """Catches: §1 edited after the pre-registration commit -- a threshold
    moved, an arm added, a rule softened once a number was in hand."""
    _require_lock()
    rec = byte_lock_check(DOC.read_text(), BYTE_LOCK)
    assert rec["identical"] is True
    assert rec["working_tree_bytes"] > 5000, rec["working_tree_bytes"]


def test_the_debts_lock_is_one_sha_and_records_no_amendment():
    """Catches: an amendment reported as an original lock. §1 here is written
    once. Also pins that §1 references no footnote, so the locked range and
    §1 are the same bytes -- a footnote added later would widen the range
    silently."""
    _require_lock()
    assert ORIGINAL_LOCK is None
    rec = byte_lock_facts(DOC.read_text(), BYTE_LOCK)
    assert rec["footnotes_in_range"] == []


def test_the_debts_byte_lock_REFUSES_a_document_that_differs_by_one_byte():
    """Catches: a lock that computes two shas, reports them unequal and
    proceeds. The mutation is E13's gate -- the LINE count of
    `focus_finally_return`, one of the two numbers in this pre-registration
    that a human's reading of source decides, and so one of the two most
    worth widening after the seal has printed."""
    _require_lock()
    text = DOC.read_text()
    moved = text.replace("carrying exactly **3** LINE rows",
                         "carrying exactly **4** LINE rows", 1)
    assert moved != text, "the mutation target is no longer in §1"
    with pytest.raises(Refused) as e:
        byte_lock_check(moved, BYTE_LOCK)
    assert "differs from the byte-lock" in str(e.value)


def test_the_locked_range_is_exactly_section_one():
    """Catches: a lock that slices the wrong range -- §1 plus §2's pins, or
    §1 truncated at its first sub-heading. The slice must start at `## 1.`
    and end at the `## 2.` line, and contain all four verbatim blocks and all
    nine sub-sections."""
    _require_lock()
    s1 = rung3.section1(DOC.read_text())
    assert s1.startswith("## 1. Pre-registration")
    assert s1.splitlines()[-1].startswith("## 2. Ambient pins")
    for heading, _, _, _ in SECTIONS:
        assert heading in s1, heading
    for n, name in SUBSECTIONS:
        assert f"### 1.{n} {name}" in s1, n
    assert "| Item | Command | Value |" not in s1  # §2's tables are outside it


def test_every_endpoint_of_this_slice_is_inside_the_locked_range():
    """Catches: an endpoint pre-registered in prose but left out of §1, whose
    rule could then be written after its number was read. The six ids the
    design's §8 table carries and the three readings §3.3's table carries are
    what §3 will report on, and all nine are locked here."""
    _require_lock()
    s1 = rung3.section1(DOC.read_text())
    for endpoint in ENDPOINTS:
        assert f"| **{endpoint}** |" in s1, endpoint
    for reading in READINGS:
        assert f"| **{reading}** |" in s1, reading


# -- the verbatim claim -----------------------------------------------------


def test_every_block_of_s1_is_its_source_verbatim():
    """Catches: a body paraphrased, reordered, re-worded or silently
    tightened while §1 still says "byte-for-byte". Each block is compared to
    its section at the commit §1 names, not to the working tree's copy of the
    spec -- so an edit to the spec on a later commit cannot make a drifted
    record look faithful."""
    _require_lock()
    _require_source_commits(*{s[1] for s in SECTIONS})
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
    target is H2′'s count -- a gate whose "= **6**" is the whole endpoint."""
    _require_lock()
    _require_source_commits(_SPEC_SHA)
    here, sha, rel, there = SECTIONS[0]
    mine = body(DOC.read_text(), here)
    tampered = _at(sha, rel).replace("`functions_focused` = **6**",
                                     "`functions_focused` = **7**", 1)
    assert "= **7**" in tampered, "the mutation target moved"
    assert body(tampered, there) != mine


def test_a_missing_heading_is_refused_not_silently_empty():
    """Catches: the failure mode above at its root -- `body()` returning `""`
    for a heading that is not there would make every comparison against it
    pass the moment two blocks both went missing."""
    with pytest.raises(Refused):
        body("## 1. Pre-registration\n\nnothing here\n", _H8)


# -- the two hand tables, pinned by content ---------------------------------


def test_s1_ends_with_both_tables_sha256s_and_the_files_still_match():
    """Catches: either prediction edited after the instrument printed. §1's
    bytes would not move -- the tables are different files -- so the byte
    lock above cannot see it. The pins are §1's last two lines, in
    `sha256sum` format, the hand count first and the census second, and this
    recomputes both from the files on disk."""
    _require_lock()
    first, second = _pinned_lines(DOC.read_text())
    assert first == f"{_sha256(HANDCOUNT)}  {HANDCOUNT_REL}", first
    assert second == f"{_sha256(CENSUS)}  {CENSUS_REL}", second


def test_the_hand_count_pin_REFUSES_a_table_that_differs_by_one_byte(tmp_path):
    """Catches: a pin that is written down and never recomputed. One byte --
    a sixth row dropped once `resolve.mjs` turned out to print five -- must
    fail the comparison above."""
    _require_lock()
    pinned = _pinned_lines(DOC.read_text())[0].split("  ")[0]
    moved = tmp_path / HANDCOUNT.name
    moved.write_bytes(HANDCOUNT.read_text()
                      .replace("| 6 | `buildDiceQueueEntry.<anonymous>` | 198",
                               "| 6 | `buildDiceQueueEntry.<anonymous>` | 199",
                               1).encode())
    assert moved.read_bytes() != HANDCOUNT.read_bytes(), "mutation target moved"
    assert _sha256(moved) != pinned


def test_the_census_pin_REFUSES_a_table_that_differs_by_one_byte(tmp_path):
    """Catches: the same, on the census -- the list whose EMPTY lens table is
    E13's third clause and H8′'s eighth. A lens row added after the detector
    ran would be the correction worth catching."""
    _require_lock()
    pinned = _pinned_lines(DOC.read_text())[1].split("  ")[0]
    moved = tmp_path / CENSUS.name
    moved.write_bytes(CENSUS.read_text().replace("| `settle` | 7 |",
                                                 "| `settle` | 8 |", 1)
                      .encode())
    assert moved.read_bytes() != CENSUS.read_bytes(), "mutation target moved"
    assert _sha256(moved) != pinned


def test_the_hand_count_is_the_shape_the_pre_registration_describes():
    """Catches: a table that is pinned but is not the table §1 asks for -- a
    row dropped, a column reordered, or the `N =` line left off. Ruling A4
    fixes the five named columns and their order and that the last line is
    `N = <count>`; the rows are numbered from 1; and the count on that last
    line is the number of rows, so a seventh row could not arrive without
    moving N."""
    _require_lock()
    text = HANDCOUNT.read_text()
    assert HANDCOUNT_HEADER in text, "the column order is not the pre-registered one"
    rows = _handcount_rows(text)
    assert len(rows) == HANDCOUNT_N, len(rows)
    assert [r[1].strip() for r in rows] == [str(n) for n in
                                            range(1, HANDCOUNT_N + 1)]
    for r in rows:
        assert len(r) == 7, r[:70]          # five columns -> seven pipe fields
        assert re.fullmatch(r"\d+", r[3].strip()), r[3]
    last = text.splitlines()[-1]
    assert re.fullmatch(r"N = \d+", last), last
    assert int(last.split("=")[1]) == len(rows) == HANDCOUNT_N, last


def test_the_hand_count_and_section_one_agree_on_the_shared_qualname():
    """Catches: the table and §1.2 drifting apart. H2′'s second reading is
    that `focus_matched` is 5 because exactly two of the six sites share one
    qualname; if the table listed six distinct ones, a correct resolver would
    fail a reading the table said otherwise about."""
    _require_lock()
    rows = _handcount_rows(HANDCOUNT.read_text())
    names = [r[2].strip() for r in rows]
    assert len(set(names)) == 5, names
    shared = [n for n in set(names) if names.count(n) == 2]
    assert shared == ["`buildDiceQueueEntry.<anonymous>`"], shared
    s1 = " ".join(rung3.section1(DOC.read_text()).split())
    assert "`meta.focus_matched` = 5" in s1
    assert "`buildDiceQueueEntry.<anonymous>`" in s1


def test_the_census_is_the_shape_the_pre_registration_describes():
    """Catches: a census pinned but not the census §1 asks for -- a root
    dropped, the three tables reordered, or an `N =` that does not count its
    own rows. The lens table's N is 0 and is the clause E13 and H8′ both
    rest on."""
    _require_lock()
    tables = _census_tables(CENSUS.read_text())
    assert len(tables) == 3, tables
    assert [n for _, n in tables] == CENSUS_COUNTS, tables
    for rows, n in tables:
        assert rows == n, (rows, n)
    assert tables[2][1] == 0, "the lens list must be EMPTY"
    s1 = " ".join(rung3.section1(DOC.read_text()).split())
    assert "The predicted counts are **0**, **1** and **0**" in s1
