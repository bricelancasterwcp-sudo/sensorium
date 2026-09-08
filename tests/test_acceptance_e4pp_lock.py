"""The E4″ byte-lock, checked in the suite rather than by a refusal at launch.

§1 of `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md` was
committed ALONE, before any of this slice's source existed. Two things are
locked and they are locked differently: §1 itself by RANGE (the
`awk '/^## 1/,/^## 2/'` bytes at the lock commit) and its 61-row subject
table by DIGEST (a sha256 printed inside §1 and carried by the lock module).
Both are checked here, so a stray edit is caught before a driver is built and
a store is copied — not after.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUST_TESTS = REPO / "rust" / "tests"
sys.path.insert(0, str(RUST_TESTS))

import acceptance_e4pp_lock as lock                                # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

#: The locked range's sha256 at `BYTE_LOCK`. Pinned as a literal, E4′'s
#: practice: without it `locked == working` passes just as happily after a
#: silent re-lock, which is the one failure a byte lock exists to make loud.
DOC_SHA = "5717507e8e0f4beb82a449df6312ac1427a276596fb1ee71e1cf106c7d547759"


def _require_lock_commit(sha):
    """A shallow checkout has no such commit. Skip BY NAME rather than pass
    on a missing one -- a skipped lock check must never look like a passed
    one."""
    if not sha:
        pytest.skip("§1 is not locked yet (BYTE_LOCK is falsy) — skipped BY "
                    "NAME, not passed")
    ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                        cwd=REPO, capture_output=True).returncode == 0
    if not ok:
        pytest.skip(f"lock commit {sha} is not in this checkout — skipped BY "
                    "NAME, not passed")


# -- (1) the range lock ----------------------------------------------------

def test_the_byte_lock_passes_on_the_real_document():
    """The comparison the runner refuses on, run against the working tree.

    `original` is None: §1 has NOT been amended, and passing None rather than
    a second sha is what says so -- E4′ carried two shas because its §1 grew
    an amendment before its numbers were read, and a record that has not been
    amended must not imply that it was."""
    _require_lock_commit(lock.BYTE_LOCK)
    rec = rung3.byte_lock_facts(lock.DOC, lock.BYTE_LOCK, None)
    assert rec["identical"] is True
    assert rec["locked_sha256"] == rec["working_tree_sha256"]
    assert rec["locked_sha256"] == DOC_SHA
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    assert rec["footnotes_in_range"] == []


def test_the_lock_module_carries_a_lock_and_the_paths_the_runner_reads():
    """The interface Task 7's runner imports. A falsy `BYTE_LOCK` is the one
    state that must refuse rather than measure."""
    assert lock.BYTE_LOCK
    assert lock.ORIGINAL_LOCK is None
    for p in (lock.DOC, lock.ROWS_DOC):
        assert p.is_file(), p
    assert lock.RESULTS.name.endswith(".results.json")
    for p in (lock.DOC, lock.ROWS_DOC, lock.RESULTS):
        assert p.is_relative_to(REPO)


def test_an_unset_lock_REFUSES_rather_than_measuring(monkeypatch):
    """A pre-registration that can still be edited is not one."""
    monkeypatch.setattr(lock, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        lock.check_byte_lock()
    assert "not locked yet" in str(e.value)


# -- (2) the digest lock ---------------------------------------------------

def test_section_1_prints_the_rows_digest_and_the_rows_file_hashes_to_it():
    """§1.1 names its subject by digest because the subject is a separate
    file: the range lock cannot see a byte that moves outside §1, so the
    sha256 printed IN §1 is what carries the rows table into the lock.

    Both halves are asserted -- the printed value and the file on disk --
    because a module constant that agreed with neither would pass a test
    that only compared it to one of them."""
    _require_lock_commit(lock.BYTE_LOCK)
    s1 = rung3.section1(lock.DOC.read_text())
    assert lock.ROWS_SHA256 in s1, "§1 does not print ROWS_SHA256"
    on_disk = hashlib.sha256(lock.ROWS_DOC.read_bytes()).hexdigest()
    assert on_disk == lock.ROWS_SHA256
    assert lock.check_rows_digest()["identical"] is True


def test_the_rows_digest_check_REFUSES_a_rows_file_that_moved(tmp_path):
    """The check has to be able to fail, or the assertion above is an
    assertion about nothing."""
    moved = tmp_path / lock.ROWS_DOC.name
    moved.write_text(lock.ROWS_DOC.read_text().replace(
        "57 granted", "58 granted", 1))
    with pytest.raises(Refused) as e:
        lock.check_rows_digest(moved)
    assert "differs from the digest" in str(e.value)


def test_the_rows_file_carries_the_61_subject_rows_and_the_partition():
    """What the digest is a digest OF. A file that hashed correctly but held
    something else would satisfy every other test here."""
    rows = [ln for ln in lock.ROWS_DOC.read_text().splitlines()
            if ln.startswith("| ") and not ln.startswith("| # |")
            and not ln.startswith("|---")]
    assert len(rows) == 61
    assert sum(1 for ln in rows if ln.endswith("| granted |")) == 57
    assert sum(1 for ln in rows if "WITHHELD" in ln) == 4
    assert "| WITHHELD (1 program thread) |" in "\n".join(rows)
    assert sum(1 for ln in rows
               if ln.endswith("| WITHHELD (4 program threads) |")) == 3


# -- (3) the lock can fail -------------------------------------------------

def test_the_byte_lock_REFUSES_a_document_that_differs_by_one_byte(tmp_path):
    """One digit inside §1.2's expectation, changed in a copy: the lock must
    refuse. A lock that only ever passes is a claim, not a check."""
    _require_lock_commit(lock.BYTE_LOCK)
    doc = tmp_path / lock.DOC.name
    doc.write_text(lock.DOC.read_text().replace("Granted 57", "Granted 58", 1))
    assert doc.read_text() != lock.DOC.read_text(), "the edit changed nothing"
    with pytest.raises(Refused) as e:
        rung3.byte_lock_check(doc, lock.BYTE_LOCK, None,
                              read_committed=lambda _p, _c:
                              lock.DOC.read_text())
    assert "differs from the byte-lock" in str(e.value)


# -- (4) what §1 must contain ----------------------------------------------

def test_the_locked_range_ENDS_at_the_stubbed_section_2_heading():
    """The range has to be closed, or writing the record breaks the lock.

    `section1()` reproduces `awk '/^## 1/,/^## 2/'` and stops AT the `## 2`
    line. §1's first draft had no such line, so the range ran to EOF and
    would have grown by every byte Task 8 appended -- the lock refusing the
    very run it exists to authorise. The stubs close it: §2..§5 are headings
    now, the range ends on `## 2. Environment`, and filling the bodies in
    BELOW those headings cannot move a byte inside it.

    The proof grows the document at the §2 heading rather than at the stub
    text: Task 8 replaced the four `*(written by Task 8)*` stubs with the
    measured record, so a proof phrased against that literal would go silently
    no-op the moment the run it authorises is written up. The heading itself is
    the last line of the range and outlives the stub."""
    text = lock.DOC.read_text()
    s1 = rung3.section1(text)
    assert s1.splitlines()[-1] == "## 2. Environment"
    for h in ("## 2. Environment", "## 3. Results", "## 4. Verdicts",
              "## 5. Gaps"):
        assert h in text, f"{h} heading is missing"
    # The proof, not the claim: appending a §2 body leaves the range alone.
    grown = text.replace("## 2. Environment\n",
                         "## 2. Environment\n\n"
                         + "Measured 2026-09-09. " * 40 + "\n", 1)
    assert grown != text
    assert rung3.section1(grown) == s1


def test_section_1_carries_all_eight_endpoints_and_the_reported_row():
    """H1..H8 plus the ungated `reported` row, inside the LOCKED range --
    an endpoint that lived outside §1 would not be pre-registered at all."""
    s1 = rung3.section1(lock.DOC.read_text())
    for i in range(1, 9):
        assert f"| H{i} |" in s1, f"H{i} is not a row of §1's table"
    assert "| reported |" in s1
    assert "| H9 |" not in s1


def test_section_1_pre_commits_both_readings_and_the_kill_sentences():
    """The house rule the table exists to keep: every endpoint names a PASS
    and a STOP before any number exists, and the kills are numbered in §1
    rather than decided when one is needed."""
    s1 = rung3.section1(lock.DOC.read_text())
    assert s1.count("**PASS**") >= 8
    assert s1.count("**STOP**") >= 6
    assert "Second reading" in s1
    assert "**Kill criteria.**" in s1
    for n in range(1, 8):
        assert f"\n{n}. **" in s1, f"kill {n} is missing"
    # Kills 1 and 2 together must name every gated endpoint: H1 in kill 1,
    # H2..H6 and H8 in kill 2, H7 as the instrument STOP.
    assert "A miss on H2, H3, H4, H5, H6 or H8 is a STOP" in s1
    assert "A miss on H7 is a STOP" in s1
    assert "these eight cover every gated endpoint" in s1
    # Kill 6's clause, matched on the one line it wraps onto: the document is
    # locked, so the test moves to the text and never the other way round.
    assert "`src/`, crate, corpus or instrument change is made after the" in s1
    assert "Measured once, and nothing moves afterwards" in s1
