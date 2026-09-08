#!/usr/bin/env python3
"""The E4″ pre-registration's locks, and the paths its record lives at.

§1 of `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md` was
committed ALONE, before any of this slice's source existed -- before
`strip_recorder_fragment` was in `refocus_env.py`, before `SESSION_EXACT`
existed, before `harness_threads` had read a `spawn@` name, before the E4″
runner existed, and while `cargo-sensorium` was still 0.5.1. This module is
what the runner imports to prove that: it holds the commit §1 is locked
against, the digest its subject table is locked by, and nothing else.

**Two locks, because the pre-registration is two files.** §1 is locked by
RANGE -- `awk '/^## 1/,/^## 2/' | sha256sum`, the shared check in
`acceptance_rung3.byte_lock_facts`. Its 61-row subject table lives in a
SIBLING file, outside that range, so it is locked by DIGEST instead: the
sha256 is printed inside §1 (and therefore inside the range lock) and
repeated here, and both must agree with the file on disk. A range lock alone
would leave the subject editable; a digest alone would leave it unattested.

No location is written into this file. `REPO` is derived from `__file__` and
every path below hangs off it, so this module says nothing about which box
it is running on -- the record's own §2 is where that belongs.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

REPO = lib.REPO
ACCEPTANCE = REPO / "docs" / "superpowers" / "acceptance"

#: The record: §0 and §1 at the lock commit; §2 onward appended after the
#: measurement, outside the locked range.
DOC = ACCEPTANCE / "2026-09-08-sensorium-rung4-e4pp.md"
#: §1.1's subject -- the 61 kept originals with the licence each is expected
#: to get, generated from `acceptance_e4p_rows.ROWS` and never retyped.
ROWS_DOC = ACCEPTANCE / "2026-09-08-sensorium-rung4-e4pp-rows.md"
#: Where the assembled record is written. Named here so the runner and the
#: renderer cannot disagree about it.
RESULTS = ACCEPTANCE / "2026-09-08-sensorium-rung4-e4pp.results.json"

#: The commit that added §1, ALONE, with the rows sibling and nothing else.
#: The runner refuses to start unless the working tree's §1 is byte-identical
#: to this commit's; a falsy value refuses outright, because a
#: pre-registration that can still be edited is not one.
BYTE_LOCK = "b9abcbd"

#: `None`, and deliberately so. E4′ carried a second sha because its §1 grew
#: an amendment (A1) after the original lock and before any number was read;
#: E4″'s §1 has NOT been amended, and `None` is how this module says that
#: rather than implying an amendment by repeating one sha twice. If §1 is
#: ever amended before the measurement, this becomes the ORIGINAL commit and
#: `BYTE_LOCK` the amended one -- both travel together from then on, as E4′'s
#: do, and the record publishes `amended_after_the_original_lock`.
ORIGINAL_LOCK = None

#: sha256 of `ROWS_DOC` as committed at `BYTE_LOCK`, and as printed in §1.1.
#: A byte that moves in the rows file after the lock is a DIFFERENT SUBJECT,
#: not a correction, and this digest is what makes that a refusal rather than
#: a silent substitution.
ROWS_SHA256 = "e3bd5313231ce2d65c190b4e2ac11355033920a3e1a8a2a17e4a15cf17d50aa8"


def check_byte_lock() -> dict:
    """§1, as committed, versus the working tree -- or a refusal to start."""
    if not BYTE_LOCK:
        raise Refused(
            "§1 of the acceptance document is not locked yet: BYTE_LOCK is "
            "falsy. Commit §1 ALONE, then set BYTE_LOCK to that commit's sha.")
    return rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)


def check_rows_digest(rows_doc: Path | None = None) -> dict:
    """The subject table, by digest -- or a refusal to start.

    Returned rather than merely asserted, so the record can publish the
    digest it actually read beside the one it expected."""
    if not ROWS_SHA256:
        raise Refused(
            "the subject table is not locked yet: ROWS_SHA256 is falsy. "
            "Print the sha256 in §1.1 and set it here.")
    doc = ROWS_DOC if rows_doc is None else rows_doc
    on_disk = hashlib.sha256(doc.read_bytes()).hexdigest()
    rel = (doc.relative_to(REPO).as_posix() if doc.is_relative_to(REPO)
           else doc.as_posix())
    rec = {"doc": rel, "expected_sha256": ROWS_SHA256,
           "sha256": on_disk, "bytes": doc.stat().st_size,
           "identical": on_disk == ROWS_SHA256}
    if not rec["identical"]:
        raise Refused(
            f"the subject table {rel} differs from the digest §1.1 printed: "
            f"{on_disk[:12]} vs {ROWS_SHA256[:12]}")
    return rec


__all__ = ["DOC", "ROWS_DOC", "RESULTS", "BYTE_LOCK", "ORIGINAL_LOCK",
           "ROWS_SHA256", "check_byte_lock", "check_rows_digest"]
