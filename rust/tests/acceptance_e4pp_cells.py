#!/usr/bin/env python3
"""E4″'s eight endpoints as measurement cells, with the drop rules applied
once.

Every cell is `{value, n, lens, dropped}`. A `null` value plus a reason in
`dropped` is the ONLY not-measured; `0` is measured-and-zero; no cell is
ever filled from §1's predictions, which enter the record under their own
names as comparison targets.

Two rules turn a measured number back into a not-measured one, and both are
applied HERE rather than in eight copies: the loop or an arm did not reach
every row (the 1 h 30 min bound), or an invocation was KILLED at its 1800 s
ceiling. `NEEDS` says which raw block each endpoint's numbers are only true
of -- H7 is about this record's own instrument and H8 about this
repository, so neither depends on a loop.

The cell NAMES are §1.4's, verbatim. A gate the document names by path and
this module does not write is a defect, and `tests/test_acceptance_e4pp_
record.py` checks every one of them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4pp_rows as e4pp                                # noqa: E402
from acceptance_e4p_cells import killed_cell, measurement_keys     # noqa: E402,F401
from acceptance_lib import meas                                    # noqa: E402

#: Every endpoint's measurement cells -- §1.4's own field names.
MEASUREMENT_CELLS = {
    "H1": ("headline", "withheld", "hides_the_exclusion",
           "reasons_that_never_subtracted", "harness_threads_all_one"),
    "H2": ("rustdocflags_in_changed", "strip_clause_named",
           "relocated_set", "hashes_differ", "hashes_unread"),
    "H3": ("headline", "pairs_of_one", "word_and_exit_disagree",
           "excluded_children"),
    "H4": ("session_names", "session_k",
           "withholding_cites_a_session_key"),
    "H5": ("headline", "env_caveat_names_the_key", "thread_reason_kept"),
    "H6": ("headline", "session_names", "session_k", "injected_key"),
    "H7": ("headline", "counts_carry_their_source_line",
           "licence_verified_counts", "version_probe"),
    "H8": ("corpus_rc", "spawned_test_fn_present", "pytest_rc", "cargo_rc",
           "pytest_summary"),
}

#: Which raw blocks each endpoint's numbers are only true of.
NEEDS = {"H1": ("raw_pass2",), "H2": ("raw_pass2",), "H3": ("raw_pass2",),
         "H4": ("raw_pass2",), "H5": ("raw_arm_b",),
         "H6": ("raw_pass2", "raw_arm_c"), "H7": (), "H8": ()}

NOT_RUN = "the phase did not run, so there is nothing to compare"


def _null(reason: str, lens: str, n=None) -> dict:
    return meas(None, n, lens, [reason])


def _null_cells(block: dict, names, reasons: list) -> dict:
    """Turn the named cells into not-measured, keeping their lens and `n`
    and carrying every reason."""
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
    """Every reason a count over an arm's rows may not be trusted, named."""
    out = []
    for key in NEEDS.get(endpoint, ()):
        block = raw.get(key)
        if not block:
            out.append(f"{key} is absent from the record")
            continue
        missing = block.get("budget_exhausted") or []
        if missing:
            out.append(f"{key}: {len(missing)} invocation(s) were never run "
                       f"-- §1.4's 1 h 30 min loop bound was reached "
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


def _apply(block: dict, endpoint: str, raw) -> dict:
    return _null_cells(block, MEASUREMENT_CELLS.get(endpoint, ()),
                       _drops(raw, endpoint))


def _absent(endpoint: str, lens: str) -> dict:
    return {name: _null(NOT_RUN, lens)
            for name in MEASUREMENT_CELLS[endpoint]}


def _dropped(h) -> list:
    return list(h.get("dropped") or [])


# ------------------------------------------------------------------- H1

H1_LENS = ("the licence word `sensorium refocus` printed beside each of the "
           "61 arm-A pairs, and the thread counts inside its sentence "
           "(`refocus_world._verified_facts` / `_licence_caveats` under R1) "
           "or, where that sentence is silent, on the `threads:` line -- "
           "each count carrying the line it came from")


def _h1(raw) -> dict:
    h = raw.get("raw_h1")
    if not h:
        return _absent("H1", H1_LENS)
    n = h.get("n")
    block = {
        "headline": meas(h.get("granted_n"), n, H1_LENS, []),
        "withheld": meas(h.get("withheld"), n, H1_LENS + "; the program's "
                         "own thread count per WITHHELD pair", []),
        "hides_the_exclusion": meas(
            h.get("hides_the_exclusion"), n,
            "granted pairs whose thread line does NOT name the excluded "
            "harness thread (a finding even when the word is predicted)",
            []),
        "reasons_that_never_subtracted": meas(
            h.get("reasons_that_never_subtracted"), n,
            "WITHHELD pairs whose reason names the RAW thread count -- the "
            "rule did not fire even though the word is right (§1.2)", []),
        "harness_threads_all_one": meas(
            h.get("harness_threads_all_one"), n,
            "every pair reports exactly 1 harness thread (§1.2)", []),
        "granted": h.get("granted"),
        "expected_granted_n": len(e4pp.EXPECTED_GRANTED),
        "withheld_set_as_predicted": h.get("withheld_set_as_predicted"),
        "withheld_only_here": h.get("withheld_only_here"),
        "withheld_missing": h.get("withheld_missing"),
        "withheld_count_mismatches": h.get("withheld_count_mismatches"),
        "counts_source_by_name": h.get("counts_source_by_name"),
        "sides_disagree": h.get("sides_disagree"),
        "harness_phrases": h.get("harness_phrases"),
        "unread": h.get("unread"),
        "gate": ("granted = 57 AND the WITHHELD set is exactly §1.2's four, "
                 "by name, with their program-thread counts (1, 4, 4, 4)"),
        "as_predicted": h.get("partition_as_predicted"),
        "verdict": h.get("verdict") or (
            "PASS" if h.get("partition_as_predicted") else "STOP"),
    }
    return _apply(block, "H1", raw)


# ------------------------------------------------------------------- H2

H2_LENS = ("the `env:` line each of the 61 arm-A pairs printed: R1's strip "
           "clause, the CHANGED name list, and Task 5b's relocated clause, "
           "read apart from one another")


def _h2(raw) -> dict:
    h = raw.get("raw_h2")
    if not h:
        return _absent("H2", H2_LENS)
    n = h.get("n")
    block = {
        "rustdocflags_in_changed": meas(
            h.get("rustdocflags_in_changed"), n,
            H2_LENS + f"; pairs whose CHANGED list names `{e4pp.STRIP_KEY}`",
            _dropped(h) if h.get("rustdocflags_in_changed") is None else []),
        "strip_clause_named": meas(
            h.get("strip_clause_named"), n,
            H2_LENS + f"; pairs whose strip clause names `{e4pp.STRIP_KEY}`",
            []),
        "relocated_set": meas(
            h.get("relocated_set"), n,
            H2_LENS + "; the relocated key set, published only where every "
            "pair printed the same one",
            [] if h.get("relocated_set") is not None else _dropped(h)),
        "hashes_differ": meas(
            h.get("hashes_differ"), h.get("hashes_readable"),
            "§1.5: the rt hash the recorder's fragment carries on each "
            "side, read from each trace's own recorded `RUSTDOCFLAGS`; "
            "pairs whose two hashes DIFFER, over the pairs whose two "
            "hashes could be READ -- a pair unread is on neither this list "
            "nor the equal one",
            ([f"{len(h.get('hashes_unread') or [])} pair(s) hash could not "
              f"be read on one side or both "
              f"({(h.get('hashes_unread') or [])[:3]})"]
             if h.get("hashes_unread") else [])),
        "hashes_unread": meas(
            h.get("hashes_unread"), n,
            "§1.5: pairs whose rt hash could not be read on one side or "
            "both. Published BESIDE `hashes_differ` and the equal list, "
            "because counted as 'not differing' an unreadable run and a "
            "single-build run would print the same number", []),
        "rustdocflags_in_changed_pairs": h.get(
            "rustdocflags_in_changed_pairs"),
        "strip_clause_missing": h.get("strip_clause_missing"),
        "relocated_sets_seen": h.get("relocated_sets_seen"),
        "relocated_set_matches": h.get("relocated_set_matches"),
        "expected_relocated_set": h.get("expected_relocated_set"),
        "changed_lists_bounded": h.get("changed_lists_bounded"),
        "hashes_equal_so_the_strip_was_untested": h.get(
            "hashes_equal_so_the_strip_was_untested"),
        "hashes_readable": h.get("hashes_readable"),
        "rt_hashes_by_pair": h.get("rt_hashes_by_pair"),
        "gate": h.get("gate"),
        "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H2", raw)


# ------------------------------------------------------------------- H3

H3_LENS = ("the verdict word `refocus` printed on each of the 61 arm-A "
           "pairs, read APART from the process exit; and the STORE's own "
           "answer to §1.4's pair rule -- exactly one trace whose "
           "`refocus_of` is the original and whose recording started after "
           "THAT invocation's launch, with R2's child runs excluded")


def _h3(raw) -> dict:
    h = raw.get("raw_h3")
    if not h:
        return _absent("H3", H3_LENS)
    n = h.get("n")
    block = {
        "headline": meas(h.get("headline"), n, H3_LENS, []),
        "pairs_of_one": meas(h.get("pairs_of_one"), n, H3_LENS, []),
        "word_and_exit_disagree": meas(
            h.get("word_and_exit_disagree"), n,
            "pairs where the printed word and the exit (MATCH 0 / DIVERGED "
            "1 / REFUSED 3) disagree -- a finding, never resolved in favour "
            "of either", []),
        "excluded_children": meas(
            h.get("excluded_children"), n,
            "pairs whose R2 exclusion list is NON-empty (expected empty on "
            "all 61)", []),
        "verdicts": h.get("verdicts"), "non_match": h.get("non_match"),
        "not_one": h.get("not_one"), "unread": h.get("unread"),
        "pair_counts": h.get("pair_counts"),
        "excluded_children_by_pair": h.get("excluded_children_by_pair"),
        "expected_match": e4pp.EXPECTED_MATCH,
        "expected_pairs_of_one": e4pp.EXPECTED_PAIRS_OF_ONE,
        "gate": h.get("gate"), "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H3", raw)


# ------------------------------------------------------------------- H4

H4_LENS = ("the session clause each arm-A pair printed on its `env:` line "
           "(A-§3's `unchanged outside session set 1 (…)`), compared "
           "against `pins.session_keys_differing` -- the set recorded at "
           "PREFLIGHT, before any refocus ran, and never a set read out of "
           "the lines this endpoint is checking")


def _h4(raw) -> dict:
    h = raw.get("raw_h4")
    if not h:
        return _absent("H4", H4_LENS)
    n = h.get("n")
    lens = H4_LENS + ("; BOUNDED: " + _capped_note(h)
                      if h.get("decided_on_k_alone") else "")
    block = {
        "session_names": meas(
            h.get("session_names"), n, lens,
            [] if h.get("session_names") is not None else _dropped(h)),
        "session_k": meas(
            h.get("session_k"), n, lens,
            [] if h.get("session_k") is not None else _k_reason(h)),
        "withholding_cites_a_session_key": meas(
            h.get("withholding_cites_a_session_key"), n,
            "WITHHELD pairs whose CHANGED list names a key of session set 1 "
            "-- the whole of R4 is that such a key never withholds", []),
        "session_names_match": h.get("session_names_match"),
        "session_k_match": h.get("session_k_match"),
        "session_names_unread": h.get("session_names_unread"),
        "session_names_seen": h.get("session_names_seen"),
        "session_names_by_name": h.get("session_names_by_name"),
        "session_k_by_name": h.get("session_k_by_name"),
        "pin": h.get("pin"), "pin_n": h.get("pin_n"),
        "decided_on_k_alone": h.get("decided_on_k_alone"),
        "names_bounded": h.get("names_bounded"),
        "line_on_a_granted_pair": h.get("line_on_a_granted_pair"),
        "fact_on_a_granted_pair": h.get("fact_on_a_granted_pair"),
        "pairs_with_an_empty_session_set": h.get(
            "pairs_with_an_empty_session_set"),
        "gate": h.get("gate"), "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H4", raw)


def _k_reason(h) -> list:
    """Why a single K could not be published -- never an empty `dropped`.

    A `null` with no reason is the one shape §1.3 forbids: it reads as a
    cell nobody thought about. K is a single number only where the pairs
    that could be READ all printed the same one, so the two ways it goes
    missing are named apart.
    """
    reasons = _dropped(h)
    ks = sorted({k for k in (h.get("session_k_by_name") or {}).values()
                 if k is not None})
    if not ks:
        reasons.append("no pair printed a session count this reader could "
                       "read, so there is no K to publish")
    elif len(ks) > 1:
        reasons.append(f"the pairs did not agree on K ({ks}); a single "
                       "value is published only where every readable pair "
                       "printed the same one, and the per-pair counts are "
                       "under `session_k_by_name`")
    return reasons or ["K was not measured and the phase gave no reason -- "
                       "reported as the instrument's own gap"]


def _capped_note(h) -> str:
    return ("the printed session list was at its 8-name cap, so the by-name "
            "half of this reading went UNREAD and the gate is decided on K "
            "alone (§1.4's kill 7, pre-committed). The bounded reading is "
            "not reported as the full one")


# ------------------------------------------------------------------- H5

H5_LENS = ("arm B: the same four rows re-run with one key on no list added "
           "to the launch environment, read from each pair's printed "
           "licence and `env:` line")


def _h5(raw) -> dict:
    h = raw.get("raw_h5")
    if not h:
        return _absent("H5", H5_LENS)
    n = h.get("n")
    block = {
        "headline": meas(h.get("headline"), n,
                         H5_LENS + "; pairs whose licence was WITHHELD", []),
        "env_caveat_names_the_key": meas(
            h.get("env_caveat_names_the_key"), n,
            H5_LENS + f"; WITHHELD pairs whose env caveat names "
            f"`{h.get('key')}`",
            [] if h.get("env_caveat_names_the_key") is not None
            else _dropped(h)),
        "thread_reason_kept": meas(
            h.get("thread_reason_kept"), 1,
            "the pager row's one-program-thread reason, read beside the env "
            "caveat: a control that SILENCED the thread reason is a finding",
            [h["thread_reason_reason"]] if h.get("thread_reason_reason")
            else []),
        "key": h.get("key"),
        "thread_reason_reason": h.get("thread_reason_reason"),
        "changed_lists_bounded": h.get("changed_lists_bounded"),
        "withheld": h.get("withheld"), "granted": h.get("granted"),
        "env_caveat_missing_the_key": h.get("env_caveat_missing_the_key"),
        "verdicts": h.get("verdicts"), "unread": h.get("unread"),
        "gate": h.get("gate"), "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H5", raw)


# ------------------------------------------------------------------- H6

H6_LENS = ("arm C: the same four rows re-run with the FIRST of session set "
           "1's fourteen exact names absent from both sides, set to the "
           "launch stamp. The word is compared against ARM A's word for "
           "the same row, and the session set against "
           "`pins.session_keys_differing` ∪ {`pins.injected_session_key`}")


def _h6(raw) -> dict:
    h = raw.get("raw_h6")
    if not h:
        return _absent("H6", H6_LENS)
    n = h.get("n")
    block = {
        "headline": meas(h.get("headline"), n,
                         H6_LENS + "; pairs whose licence word equals arm "
                         "A's for the same row", []),
        # MEASURED even when it disagrees with the pin ∪ the key: a set
        # every pair printed WAS measured, and `session_names_match` is
        # what carries the miss (§1.3 -- a null with a reason is the only
        # not-measured).
        "session_names": meas(
            h.get("session_names"), n, H6_LENS,
            [] if h.get("session_names") is not None else _dropped(h)),
        "session_k": meas(
            h.get("session_k"), n, H6_LENS,
            [] if h.get("session_k") is not None else _k_reason(h)),
        "injected_key": meas(
            h.get("injected_key"), 1,
            "`pins.injected_session_key` -- chosen and recorded at PREFLIGHT "
            "and DERIVED here, never chosen a second time", []),
        "word_moved": h.get("word_moved"),
        "session_names_match": h.get("session_names_match"),
        "session_k_match": h.get("session_k_match"),
        "session_names_unread": h.get("session_names_unread"),
        "session_names_by_name": h.get("session_names_by_name"),
        "expected_session_names": h.get("expected_session_names"),
        "expected_k": h.get("expected_k"), "pin": h.get("pin"),
        "injected_key_choice": (raw.get("pins") or {}).get(
            "injected_session_key_choice"),
        "gate": h.get("gate"), "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H6", raw)


# ------------------------------------------------------------------- H7

H7_LENS = ("this record's OWN instrument, over every pair of every arm: "
           "the partition cells beside the licence word that printed, the "
           "source line each thread count came from, the verified counts "
           "built from the rows, and the version probe's own output")


def _h7(raw) -> dict:
    h = raw.get("raw_h7")
    if not h:
        return _absent("H7", H7_LENS)
    probe = h.get("version_probe") or {}
    # The denominator: rows of EVERY arm that came back with a licence
    # word. A row whose licence never printed has no partition for this
    # endpoint to be honest or dishonest about.
    n = h.get("censused")
    counts = h.get("licence_verified_counts") or {}
    block = {
        "headline": meas(h.get("headline"), n, H7_LENS + "; pairs whose "
                         "licence PRINTED and whose thread arithmetic did "
                         "not", []),
        "counts_carry_their_source_line": meas(
            h.get("counts_carry_their_source_line"), n,
            H7_LENS + "; every thread count says whether it came from the "
            "licence clause or the `threads:` line", []),
        "licence_verified_counts": meas(
            h.get("licence_verified_counts"), counts.get("n"),
            "the four verified/unverifiable counts, COUNTED over "
            "`raw_pass2.refocuses[*].licence` and never summed", []),
        "version_probe": meas(
            probe.get("token"), 1,
            f"`{probe.get('command')}` -- a token, or null WITH its reason, "
            "never an empty string",
            [probe["reason"]] if probe.get("reason") else []),
        "version_probe_ok": h.get("version_probe_ok"),
        "version_probe_reason": probe.get("reason"),
        "null_cells": h.get("null_cells"),
        "counts_without_a_source_line": h.get(
            "counts_without_a_source_line"),
        "dropped_lists": h.get("dropped_lists"),
        "stop_is_of_the": h.get("stop_is_of_the"),
        "gate": h.get("gate"), "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H7", raw)


# ------------------------------------------------------------------- H8

H8_LENS = ("this repository, never the clone: the corpus collector over "
           "every case WITH the driver (`--require-driver`), the whole "
           "Python suite, and `cargo test --workspace`, each with its own "
           "log and its own return code")


def _h8(raw) -> dict:
    h = raw.get("raw_h8")
    if not h:
        return _absent("H8", H8_LENS)
    block = {
        "corpus_rc": meas(h.get("corpus_rc"), 1, H8_LENS, []),
        "spawned_test_fn_present": meas(
            h.get("spawned_test_fn_present"), 1,
            f"the corpus collector's own `load_cases()` listing, asked "
            f"whether it names `{e4pp.SPAWNED_CASE}`",
            _dropped(h)),
        "pytest_rc": meas(h.get("pytest_rc"), 1, H8_LENS, []),
        "cargo_rc": meas(h.get("cargo_rc"), 1, H8_LENS, []),
        "pytest_summary": meas(h.get("pytest_summary"), 1,
                               H8_LENS + "; prose, reported and never a "
                               "gate", []),
        "corpus_cases": h.get("corpus_cases"),
        "corpus_failures": h.get("corpus_failures"),
        "corpus_errors": h.get("corpus_errors"),
        "corpus_skipped": h.get("corpus_skipped"),
        "corpus_require_driver": h.get("corpus_require_driver"),
        "corpus_args": h.get("corpus_args"),
        "spawned_test_fn": h.get("spawned_test_fn"),
        "spawned_test_fn_skipped": h.get("spawned_test_fn_skipped"),
        "cargo_result_lines": h.get("cargo_result_lines"),
        "logs": h.get("logs"),
        "gate": h.get("gate"), "as_predicted": h.get("as_predicted"),
        "verdict": h.get("verdict"),
    }
    return _apply(block, "H8", raw)


ENDPOINTS = {"H1": _h1, "H2": _h2, "H3": _h3, "H4": _h4, "H5": _h5,
             "H6": _h6, "H7": _h7, "H8": _h8}

__all__ = ["ENDPOINTS", "MEASUREMENT_CELLS", "NEEDS", "NOT_RUN",
           "killed_cell", "measurement_keys"]
