#!/usr/bin/env python3
"""E4′'s six endpoints as measurement cells, with the drop rules applied once.

Every cell is `{value, n, lens, dropped}`. A `null` value plus a reason in
`dropped` is the ONLY not-measured; `0` is measured-and-zero; no cell is
ever filled from §1's predictions, which enter the record under their own
names as comparison targets.

Two rules turn a measured number back into a not-measured one, and both are
applied HERE rather than in six copies:

* the loop did not reach every test (the 1 h 15 min bound), so a count over
  "the 61" is a count over fewer;
* an invocation was KILLED at its 1800 s ceiling, so its output is partial.

No cell of this record survives either. E4 could keep one -- its H1 counted
PRE-RERUN refusals, which an invocation long enough to be killed had already
passed -- but every number here is over what came back from a completed
refocus, and a smaller loop makes each of them a smaller answer.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4p_rows import (EXPECTED_GRANTED, EXPECTED_MATCH,  # noqa: E402
                                 EXPECTED_PAIRS_OF_ONE,
                                 EXPECTED_SHIM_KEYS, GATE_N)
from acceptance_lib import meas                                    # noqa: E402

#: Every endpoint's measurement cells, listed so `measurement_keys` can be
#: CHECKED against what the schema publishes: a cell added to a block and
#: forgotten here would escape the drop rules entirely and publish a number
#: from a loop that never finished.
MEASUREMENT_CELLS = {
    "H1": ("headline", "withheld", "hides_the_exclusion",
           "reasons_that_never_subtracted", "harness_threads_all_one"),
    "H2": ("headline", "non_match", "word_and_exit_disagree"),
    "H3": ("headline", "excluded_children", "readings_disagree"),
    "H4": ("headline", "entries", "distinct_inodes", "bytes_once_per_inode",
           "linked_to_the_driver"),
    "H5": ("headline", "raw_schema_version", "assembled_schema_version",
           "renderers_print_their_field"),
    "H6": ("headline", "corpus_rc", "corpus_cases", "pytest_summary",
           "cargo_rc"),
}

#: Which raw blocks each endpoint's numbers are only true of. H5 is about
#: this record's own two files and H6 about this repository, so neither
#: depends on the loop.
NEEDS = {"H1": ("raw_pass2",), "H2": ("raw_pass2",), "H3": ("raw_pass2",),
         "H4": ("raw_pass2",), "H5": (), "H6": ()}

#: The one sentence every "this phase did not run" reason is built from.
NOT_RUN = "the phase did not run, so there is nothing to compare"


def measurement_keys(block: dict) -> set:
    """Every key of one endpoint whose value IS a measurement -- derived
    from the block rather than declared, so `MEASUREMENT_CELLS` can be
    checked against what the schema actually publishes."""
    return {k for k, v in block.items()
            if isinstance(v, dict)
            and {"value", "n", "lens", "dropped"} <= set(v)}


def killed_cell(reason: str) -> dict:
    """A cell for something that was KILLED, shaped so it cannot be read as
    a measurement.

    Not `0`, not `""`, not an empty list: each of those is a value a reader
    -- or a later sum -- takes for a measured one. A dict with `killed` and
    a reason has no numeric reading at all, which is the point.
    """
    return {"killed": True, "reason": reason}


def _null(reason: str, lens: str, n=None) -> dict:
    return meas(None, n, lens, [reason])


def _null_cells(block: dict, names, reasons: list) -> dict:
    """Turn the named cells into not-measured, keeping their lens and `n`
    and carrying every reason. A cell that is not a measurement is left
    alone; one already `null` keeps the reason it has."""
    if not reasons:
        return block
    for name in names:
        cell = block.get(name)
        if not isinstance(cell, dict) or "lens" not in cell:
            continue
        if cell.get("value") is None:
            cell["dropped"] = list(dict.fromkeys(
                list(cell["dropped"]) + reasons))
            continue
        nulled = _null(reasons[0], cell["lens"], cell["n"])
        nulled["dropped"] = list(dict.fromkeys(
            nulled["dropped"] + list(cell["dropped"]) + reasons[1:]))
        block[name] = nulled
    return block


def _drops(raw, endpoint: str) -> list[str]:
    """Every reason a count over "the 61" may not be trusted, named."""
    out = []
    for key in NEEDS.get(endpoint, ()):
        block = raw.get(key)
        if not block:
            out.append(f"{key} is absent from the record")
            continue
        missing = block.get("budget_exhausted") or []
        if missing:
            out.append(f"{key}: {len(missing)} invocation(s) were never run "
                       f"-- §1.4's 1 h 15 min loop bound was reached "
                       f"({missing[:3]}{' …' if len(missing) > 3 else ''})")
        n, measured = block.get("n"), block.get("measured")
        if (n is not None and measured is not None and measured != n
                and not missing):
            out.append(f"{key}: {measured} of {n} invocation(s) ran")
        killed = block.get("killed") or []
        if killed:
            out.append(f"{key}: invocation(s) {killed[:3]}"
                       f"{' …' if len(killed) > 3 else ''} were KILLED at "
                       "the 1800 s ceiling; their output is partial")
    return out


def _apply_drops(block: dict, endpoint: str, raw) -> dict:
    return _null_cells(block, MEASUREMENT_CELLS.get(endpoint, ()),
                       _drops(raw, endpoint))


def _absent(endpoint: str, lens: str, names) -> dict:
    """Every cell of an endpoint whose phase never ran."""
    return {name: _null(NOT_RUN, lens) for name in names}


# ------------------------------------------------------------------- H1

H1_LENS = ("the licence word `sensorium refocus` printed beside each of the "
           "61 pairs, and the thread counts inside its sentence "
           "(`refocus_world._verified_facts` / `_licence_caveats` under R1)")


def _h1(raw) -> dict:
    h = raw.get("raw_h1")
    if not h:
        return _absent("H1", H1_LENS, MEASUREMENT_CELLS["H1"])
    n = h.get("n")
    block = {
        "headline": meas(h.get("granted_n"), n, H1_LENS, []),
        "withheld": meas(h.get("withheld"), n,
                         H1_LENS + "; the program's own thread count per "
                         "WITHHELD pair", []),
        "hides_the_exclusion": meas(h.get("hides_the_exclusion"), n,
                                    "granted pairs whose thread line does "
                                    "NOT name the excluded harness thread "
                                    "(H1's second reading; a finding even "
                                    "when the word is the predicted one)",
                                    []),
        "reasons_that_never_subtracted": meas(
            h.get("reasons_that_never_subtracted"), n,
            "WITHHELD pairs whose reason names the RAW thread count -- the "
            "rule did not fire even though the word is right (§1.2)", []),
        "harness_threads_all_one": meas(h.get("harness_threads_all_one"), n,
                                        "every pair reports exactly 1 "
                                        "harness thread (§1.2)", []),
        "granted": h.get("granted"),
        "expected_granted_n": len(EXPECTED_GRANTED),
        "withheld_set_as_predicted": h.get("withheld_set_as_predicted"),
        "withheld_only_here": h.get("withheld_only_here"),
        "withheld_missing": h.get("withheld_missing"),
        "withheld_count_mismatches": h.get("withheld_count_mismatches"),
        "sides_disagree": h.get("sides_disagree"),
        "harness_phrases": h.get("harness_phrases"),
        "unread": h.get("unread"),
        "gate": ("granted = 57 AND the WITHHELD set is exactly §1.2's four, "
                 "by name, with their program-thread counts"),
        "as_predicted": h.get("partition_as_predicted"),
    }
    return _apply_drops(block, "H1", raw)


# ------------------------------------------------------------------- H2

H2_LENS = ("the verdict word `refocus` printed on each of the 61 pairs, "
           "read APART from the process exit it returned")


def _h2(raw) -> dict:
    h = raw.get("raw_h2")
    if not h:
        return _absent("H2", H2_LENS, MEASUREMENT_CELLS["H2"])
    n = h.get("n")
    block = {
        "headline": meas(h.get("match_n"), n, H2_LENS, []),
        "non_match": meas(h.get("non_match"), n,
                          H2_LENS + "; every pair whose verdict was not "
                          "MATCH, with its run ids", []),
        "word_and_exit_disagree": meas(
            h.get("word_and_exit_disagree"), n,
            "pairs where the printed word and the exit (MATCH 0 / DIVERGED "
            "1 / REFUSED 3) disagree -- a finding, never resolved in favour "
            "of either", []),
        "verdicts": h.get("verdicts"),
        "unread": h.get("unread"),
        "expected_match": EXPECTED_MATCH,
        "gate": "MATCH 61 of 61",
        "as_predicted": h.get("match_as_predicted"),
    }
    return _apply_drops(block, "H2", raw)


# ------------------------------------------------------------------- H3

H3_LENS = ("the store's own answer to §1.4's pair rule -- exactly one trace "
           "whose `refocus_of` is the original and whose recording started "
           "after the launch, with R2's child runs excluded -- read from "
           "the trace files, never from the CLI's printed id")


def _h3(raw) -> dict:
    h = raw.get("raw_h3")
    if not h:
        return _absent("H3", H3_LENS, MEASUREMENT_CELLS["H3"])
    n = h.get("n")
    block = {
        "headline": meas(h.get("pairs_of_one"), n, H3_LENS, []),
        "excluded_children": meas(
            h.get("excluded_children_n"), n,
            "pairs whose R2 exclusion list is NON-empty, read from the "
            "printed clause and from the store (H3's second reading: the "
            "list is expected empty on all 61)", []),
        "readings_disagree": meas(h.get("readings_disagree"), n,
                                  "pairs where the store and the printed "
                                  "line disagree about the pair or its "
                                  "excluded children", []),
        "pair_counts": h.get("pair_counts"),
        "not_one": h.get("not_one"),
        "expected_pairs_of_one": EXPECTED_PAIRS_OF_ONE,
        "gate": "61 of 61 pairs of exactly one",
        "as_predicted": h.get("pairs_as_predicted"),
    }
    return _apply_drops(block, "H3", raw)


# ------------------------------------------------------------------- H4

H4_LENS = ("`<CARGO_TARGET_DIR>/sensorium/shim/*/cargo-sensorium`, measured "
           "ONCE at the end: entries, distinct inodes, and bytes counted "
           "once per inode -- three numbers, never summed into each other")


def _h4(raw) -> dict:
    h = raw.get("raw_h4")
    if not h:
        return _absent("H4", H4_LENS, MEASUREMENT_CELLS["H4"])
    n = h.get("keys")
    block = {
        "headline": meas(h.get("keys"), n, H4_LENS, []),
        "entries": meas(h.get("entries"), n, H4_LENS, []),
        "distinct_inodes": meas(h.get("distinct_inodes"), n, H4_LENS, []),
        "bytes_once_per_inode": meas(h.get("bytes_once_per_inode"), n,
                                     H4_LENS + "; NEVER the sum of the "
                                     "per-entry sizes", []),
        "linked_to_the_driver": meas(h.get("linked_to_the_driver"), n,
                                     "shim keys whose `st_ino` equals the "
                                     "driver's", []),
        "not_linked": h.get("not_linked"),
        "same_device": h.get("same_device"),
        "driver_inode": h.get("driver_inode"),
        # A term of the gate, not a note beside it: a key directory holding
        # no `cargo-sensorium` has no `st_ino`, so "for EVERY key" is not
        # met however many of the rest linked.
        "entries_cover_every_key": h.get("entries_cover_every_key"),
        "keys_without_a_binary": h.get("keys_without_a_binary"),
        "expected_keys": EXPECTED_SHIM_KEYS,
        "finding": h.get("finding"),
        "gate": ("61 focused keys, EVERY one holding a `cargo-sensorium` "
                 "that shares the driver's inode where the filesystem "
                 "allows a link"),
        "as_predicted": h.get("as_predicted"),
    }
    return _apply_drops(block, "H4", raw)


# ------------------------------------------------------------------- H5

H5_LENS = ("this record's own two files: the raw record the runner wrote "
           "and the assembled record `assemble_e4p` derived from it")


def _h5(raw) -> dict:
    h = raw.get("raw_h5")
    if not h:
        return _absent("H5", H5_LENS, MEASUREMENT_CELLS["H5"])
    block = {
        "headline": meas(h.get("as_predicted"), 2, H5_LENS, []),
        "raw_schema_version": meas(h.get("raw_schema_version"), 1, H5_LENS,
                                   []),
        "assembled_schema_version": meas(h.get("assembled_schema_version"),
                                         1, H5_LENS, []),
        "renderers_print_their_field": meas(
            h.get("renderers_print_their_field"), len(h.get("dry_assemble")
                                                      or {}),
            "a DRY assemble -- nothing written -- of the E9 and E4 records, "
            "asking each renderer to print its own `schema_version`", []),
        "dry_assemble": h.get("dry_assemble"),
        "committed_records_predate_the_field": h.get(
            "committed_records_predate_the_field"),
        "gate": "the raw and the assembled record both carry `e4p/1`",
        "as_predicted": h.get("as_predicted"),
    }
    return _apply_drops(block, "H5", raw)


# ------------------------------------------------------------------- H6

H6_LENS = ("this repository, never the clone: the corpus collector over "
           "every case, the whole Python suite, and `cargo test "
           "--workspace`, each with its own log")


def _h6(raw) -> dict:
    h = raw.get("raw_h6")
    if not h:
        return _absent("H6", H6_LENS, MEASUREMENT_CELLS["H6"])
    corpus, python, cargo = (h.get("corpus") or {}, h.get("python") or {},
                             h.get("cargo") or {})
    block = {
        "headline": meas(h.get("all_green"), 3, H6_LENS, []),
        "corpus_rc": meas(corpus.get("rc"), 1, H6_LENS, []),
        "corpus_cases": meas(corpus.get("cases"), 1, H6_LENS, []),
        "pytest_summary": meas(python.get("summary"), 1, H6_LENS, []),
        "cargo_rc": meas(cargo.get("rc"), 1, H6_LENS, []),
        "corpus_failures": corpus.get("failures"),
        "corpus_errors": corpus.get("errors"),
        "corpus_skipped": corpus.get("skipped"),
        "refocus_child_run_present": corpus.get("refocus_child_run_present"),
        "pytest_rc": python.get("rc"),
        "cargo_result_lines": cargo.get("result_lines"),
        "gate": ("every corpus case equal, the Python suite green, `cargo "
                 "test --workspace` green"),
        "as_predicted": h.get("all_green"),
    }
    return _apply_drops(block, "H6", raw)


ENDPOINTS = {"H1": _h1, "H2": _h2, "H3": _h3, "H4": _h4, "H5": _h5,
             "H6": _h6}

__all__ = ["ENDPOINTS", "GATE_N", "MEASUREMENT_CELLS", "NEEDS", "NOT_RUN",
           "killed_cell", "measurement_keys"]
