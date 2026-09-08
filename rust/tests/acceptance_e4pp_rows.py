#!/usr/bin/env python3
"""E4″'s pre-registered numbers, in one place and never retyped twice.

§1.1's subject and §1.2's partition are E4′'s, unchanged and in E4′'s
order, so they are IMPORTED from `acceptance_e4p_rows` rather than copied:
one transcription of the locked table, checked against the document by
`tests/test_acceptance_e4p.py`, and `acceptance_e4pp_lock.ROWS_SHA256`
locking the sibling file that was generated from it.

What is new here is §1.4's own comparison targets -- the relocated set, the
stripped key, the corpus case H8 names -- and each is a COMPARISON TARGET
under its own name. No endpoint falls back to one; a headline that borrowed
from a prediction could not fail.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4p_rows import (EXPECTED_EXCLUDED_CHILDREN,       # noqa: E402,F401
                                 EXPECTED_GRANTED,
                                 EXPECTED_HARNESS_THREADS,
                                 EXPECTED_MATCH, EXPECTED_PAIRS_OF_ONE,
                                 EXPECTED_WITHHELD, GATE_N, NAMES, ROWS,
                                 RUNS, TARGETS)

#: H2's gate, third cell: E4′'s MEASURED relocated set, on 61/61 pairs. Read
#: off E4′'s published `reported.env_relocation.relocated_keys_seen` before
#: §1 was locked, and written into §1.4 as the expectation -- so it is a
#: prior measurement entering as a comparison target, never as a fallback.
#:
#: §1.3 gives every re-run a FRESH `CARGO_TARGET_DIR`, so these four are the
#: variables cargo derives from the root: the root itself, one path per
#: binary target, and the loader path whose first entry is under it.
EXPECTED_RELOCATED = ("CARGO_BIN_EXE_bloomery-daemon",
                      "CARGO_BIN_EXE_flywheel-tool",
                      "CARGO_TARGET_DIR", "LD_LIBRARY_PATH")

#: H2's other two cells. The strip names ONE key -- the recorder writes its
#: fragment into `RUSTDOCFLAGS` and nowhere else -- and that key must appear
#: in no pair's CHANGED list, which is what "gone from the compare" means.
STRIP_KEY = "RUSTDOCFLAGS"
EXPECTED_STRIP_CLAUSE_NAMED = GATE_N
EXPECTED_RUSTDOCFLAGS_IN_CHANGED = 0

#: The printed name lists are capped at eight (`refocus_world._capped`), so
#: a set larger than this makes the COUNT authoritative and the names short
#: -- §1.4's kill 7, pre-committed for H4 and applied wherever a capped list
#: is read.
NAME_CAP = 8

#: Arms B and C: four rows each (§1.3), the first three expected granted and
#: the pager test expected WITHHELD for its one program thread.
ARM_N = 4

#: H8's named case: the corpus case R3 was written against -- a test that
#: spawns a thread onto another `#[test]` fn, whose marked ROOT frame is not
#: proof the recorder started that thread. §1.4 gates on its presence.
SPAWNED_CASE = "refocus_spawned_test_fn"

#: H8's corpus flag. `--require-driver` turns a skipped case into a verdict
#: on the RUN: this record BUILDS a driver so those cases run, and a green
#: summary over cases nobody recorded would say nothing.
CORPUS_ARGS = ("--require-driver",)

__all__ = ["ARM_N", "CORPUS_ARGS", "EXPECTED_EXCLUDED_CHILDREN",
           "EXPECTED_GRANTED", "EXPECTED_HARNESS_THREADS", "EXPECTED_MATCH",
           "EXPECTED_PAIRS_OF_ONE", "EXPECTED_RELOCATED",
           "EXPECTED_RUSTDOCFLAGS_IN_CHANGED",
           "EXPECTED_STRIP_CLAUSE_NAMED", "EXPECTED_WITHHELD", "GATE_N",
           "NAMES", "NAME_CAP", "ROWS", "RUNS", "SPAWNED_CASE", "STRIP_KEY",
           "TARGETS"]
