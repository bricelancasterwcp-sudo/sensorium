"""The E4′ phases: the functions that turn 61 parsed answers into H1-H4.

These sit between the parser (tested on real command output in
`test_acceptance_e4p_read.py`) and the schema (tested on pre-built raw
blocks in `test_acceptance_e4p_record.py`), and they are where §1.2's
partition is actually decided. A mutation that swapped H1's granted branch
for its withheld one survived both neighbouring suites; these are the tests
that catch it.

Every fixture here is built to §1.2's OWN prediction -- 57 granted, the four
named withheld with 1/4/4/4 program threads -- so a phase that reported the
partition correctly and a phase that reported it backwards cannot both pass.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4p_phases as phases                             # noqa: E402
import acceptance_e4p_phases2 as phases2                           # noqa: E402
import acceptance_e4p_rows as rows                                 # noqa: E402


#: "the caller passed nothing", told apart from an explicit `None`. A
#: default of `None` here would make "this pair's licence never printed"
#: unspellable in a fixture -- which is one of the cases these tests exist
#: to cover, and the same none-vs-default confusion the record itself is
#: careful about one level up.
_UNSET = object()


def _row(index, name, target, run, *, licence=_UNSET, program=_UNSET,
         harness=1, names_exclusion=True, verdict="MATCH", rc=0,
         pair_n=1, children=(), sides_agree=True, unsubtracted=()):
    """One refocus as `refocus_one` records it, with only the fields the
    phases read. `licence` defaults to §1.2's own answer for this name, so
    a fixture cannot quietly disagree with the prediction it is testing."""
    if licence is _UNSET:
        withheld = name in rows.EXPECTED_WITHHELD
        licence = "WITHHELD" if withheld else "granted"
    if program is _UNSET:
        program = (rows.EXPECTED_WITHHELD.get(name, 0)
                   if licence is not None else None)
    return {
        "index": index, "name": name, "target": target, "original": run,
        "rc": rc, "verdict_word": verdict,
        "verdict_and_exit_agree": rc == phases.VERDICT_EXIT.get(verdict),
        "verdict_exit_expected": phases.VERDICT_EXIT.get(verdict),
        "pair": {"n": pair_n, "qualifying": [f"pair-{index}"],
                 "linked": [f"pair-{index}"], "children": list(children),
                 "unreadable": []},
        "new_run": f"pair-{index}" if pair_n == 1 else None,
        "printed_pair_run": f"pair-{index}" if pair_n == 1 else None,
        "pair_agrees_with_the_printed_id": pair_n == 1,
        "excluded_children_printed": list(children),
        "excluded_children_in_the_store": list(children),
        "licence_partition": {
            "licence": licence, "program_threads": program,
            "harness_threads": harness,
            "names_the_exclusion": names_exclusion,
            "sides_agree": sides_agree,
            "harness_phrase": "libtest's per-test thread, excluded as the "
                              "recorder's own",
            "unsubtracted_labels": list(unsubtracted)},
        "wall_s": 7.0, "timed_out": False,
    }


def _two(overrides=None) -> dict:
    """All 61 of §1.1, answering exactly as §1.2 predicts."""
    overrides = overrides or {}
    refocuses = []
    for index, name, target, run in rows.ROWS:
        refocuses.append(_row(index, name, target, run,
                              **overrides.get(name, {})))
    return {"refocuses": refocuses, "n": 61, "measured": 61,
            "budget_exhausted": [], "killed": [], "pair_refusals": []}


# ------------------------------------------------------------------- H1

def test_the_predicted_partition_reads_as_predicted():
    h = phases.phase_h1(_two())
    assert h["granted_n"] == 57
    assert set(h["withheld"]) == set(rows.EXPECTED_WITHHELD)
    assert h["withheld"] == dict(sorted(rows.EXPECTED_WITHHELD.items()))
    assert h["partition_as_predicted"] is True
    assert h["harness_threads_all_one"] is True
    assert h["hides_the_exclusion"] == []


def test_granted_and_WITHHELD_are_not_interchangeable():
    """The mutation that survived every other suite: a branch that put
    granted pairs in the withheld bucket. 57 and 4 are different numbers and
    the sets are disjoint, so a swap can be seen from either side."""
    h = phases.phase_h1(_two())
    assert h["granted_n"] == 57 and h["withheld_n"] == 4
    assert set(h["granted"]).isdisjoint(h["withheld"])
    assert set(h["granted"]) == set(rows.EXPECTED_GRANTED)
    for name in rows.EXPECTED_WITHHELD:
        assert name not in h["granted"], name


def test_one_granted_pair_too_many_is_NOT_as_predicted():
    """§1.2's gate is the PARTITION, not the count: this run scores 58/3."""
    h = phases.phase_h1(_two({
        "a_pager_can_be_shared_across_threads":
            {"licence": "granted", "program": 0}}))
    assert h["granted_n"] == 58
    assert h["partition_as_predicted"] is False
    assert h["withheld_missing"] == ["a_pager_can_be_shared_across_threads"]


def test_a_DIFFERENT_four_withheld_is_caught_even_at_57_slash_4():
    """The reading a count alone cannot make. This run withholds four tests
    and grants 57 -- and it is a different finding entirely."""
    h = phases.phase_h1(_two({
        "a_pager_can_be_shared_across_threads":
            {"licence": "granted", "program": 0},
        "unload_credits_the_weights_back":
            {"licence": "WITHHELD", "program": 1}}))
    assert h["granted_n"] == 57 and h["withheld_n"] == 4
    assert h["partition_as_predicted"] is False
    assert h["withheld_only_here"] == ["unload_credits_the_weights_back"]
    assert h["withheld_missing"] == ["a_pager_can_be_shared_across_threads"]


def test_a_reason_naming_the_RAW_count_is_a_count_mismatch():
    """§1.2: a WITHHELD whose reason says 5 instead of 4 never subtracted,
    "and is H1's STOP, because it means the rule did not fire even though
    the word happens to be right"."""
    h = phases.phase_h1(_two({
        "the_refusal_advises_a_window_that_actually_places":
            {"program": 5, "unsubtracted": ["the original"]}}))
    assert h["partition_as_predicted"] is False
    assert h["withheld_count_mismatches"] == [
        {"name": "the_refusal_advises_a_window_that_actually_places",
         "expected": 4, "measured": 5}]
    assert h["reasons_that_never_subtracted"] == [
        "the_refusal_advises_a_window_that_actually_places"]


def test_a_granted_line_that_hides_the_exclusion_is_a_REPORTED_finding():
    """H1's second reading, and it must not touch the gate: the word is the
    predicted one, so the partition still reads as predicted, and the
    finding is published beside it."""
    h = phases.phase_h1(_two({
        "unload_credits_the_weights_back": {"names_exclusion": False}}))
    assert h["partition_as_predicted"] is True
    assert h["hides_the_exclusion"] == ["unload_credits_the_weights_back"]


def test_a_pair_whose_licence_never_printed_is_UNREAD_not_granted():
    h = phases.phase_h1(_two({
        "unload_credits_the_weights_back":
            {"licence": None, "program": None, "harness": None}}))
    assert h["unread"] == ["unload_credits_the_weights_back"]
    assert h["granted_n"] == 56
    assert h["partition_as_predicted"] is False


def test_a_harness_count_other_than_one_is_reported():
    h = phases.phase_h1(_two({
        "unload_credits_the_weights_back": {"harness": 2}}))
    assert h["harness_threads_all_one"] is False
    assert h["harness_threads_by_name"]["unload_credits_the_weights_back"] == 2


def test_two_sides_that_disagree_are_named():
    h = phases.phase_h1(_two({
        "unload_credits_the_weights_back": {"sides_agree": False}}))
    assert h["sides_disagree"] == ["unload_credits_the_weights_back"]


# ------------------------------------------------------------------- H2

def test_61_MATCHes_read_as_predicted():
    h = phases.phase_h2(_two())
    assert h["match_n"] == 61
    assert h["match_as_predicted"] is True
    assert h["non_match"] == [] and h["word_and_exit_disagree"] == []


@pytest.mark.parametrize("verdict, rc", [("DIVERGED", 1), ("REFUSED", 3)])
def test_a_single_non_MATCH_is_caught_and_NAMED(verdict, rc):
    h = phases.phase_h2(_two({
        "unload_credits_the_weights_back": {"verdict": verdict, "rc": rc}}))
    assert h["match_n"] == 60
    assert h["match_as_predicted"] is False
    assert h["non_match"][0]["name"] == "unload_credits_the_weights_back"
    assert h["non_match"][0]["verdict"] == verdict


def test_the_word_and_the_exit_are_compared_and_never_derived():
    """§1's second reading: a disagreement between them is a finding
    reported as one, never resolved in favour of either. So a MATCH that
    exited 1 is BOTH a match by word and a disagreement."""
    h = phases.phase_h2(_two({
        "unload_credits_the_weights_back": {"verdict": "MATCH", "rc": 1}}))
    assert h["match_n"] == 61
    assert h["word_and_exit_disagree"] == [
        {"name": "unload_credits_the_weights_back", "word": "MATCH",
         "exit": 1, "expected_exit": 0}]


# ------------------------------------------------------------------- H3

def test_61_pairs_of_one_read_as_predicted():
    h = phases.phase_h3(_two())
    assert h["pairs_of_one"] == 61
    assert h["pairs_as_predicted"] is True
    assert h["excluded_list_empty_on_all"] is True


@pytest.mark.parametrize("n", [0, 2])
def test_a_pair_count_other_than_one_is_caught(n):
    h = phases.phase_h3(_two({
        "unload_credits_the_weights_back": {"pair_n": n}}))
    assert h["pairs_of_one"] == 60
    assert h["pairs_as_predicted"] is False
    assert h["not_one"][0]["n"] == n


def test_a_NON_empty_child_exclusion_list_is_a_reported_finding():
    """H3's second reading. §1.1's greps found `Command::new` 0 hits, so the
    list is expected empty on all 61 -- and a non-empty one does NOT move
    the gate, which is about the pair count."""
    h = phases.phase_h3(_two({
        "unload_credits_the_weights_back": {"children": ["c-1"]}}))
    assert h["pairs_as_predicted"] is True
    assert h["excluded_children_n"] == 1
    assert h["excluded_list_empty_on_all"] is False
    assert h["excluded_children"]["unload_credits_the_weights_back"] == {
        "printed": ["c-1"], "store": ["c-1"]}


def test_the_store_and_the_printed_line_disagreeing_is_a_finding():
    two = _two()
    row = two["by_name"] = {r["name"]: r for r in two["refocuses"]}
    row["unload_credits_the_weights_back"]["excluded_children_printed"] = []
    row["unload_credits_the_weights_back"][
        "excluded_children_in_the_store"] = ["c-1"]
    h = phases.phase_h3(two)
    assert h["readings_disagree"]
    assert h["readings_disagree"][0]["printed"] == []


# ------------------------------------------------------------------- H4

def _census(monkeypatch, **kw):
    base = {"dir": "/x", "exists": True, "keys": 61, "entries": 61,
            "distinct_inodes": 1, "bytes_once_per_inode": 40_000_000,
            "driver_inode": 7, "driver_dev": 66, "linked_to_the_driver": 61,
            "not_linked": [], "same_device": True, "devices": [66],
            "names": [], "keys_without_a_binary": [],
            "entries_cover_every_key": True}
    base.update(kw)
    monkeypatch.setattr(phases2, "shim_census", lambda *_a, **_k: base)
    return {"sensorium_e4p_target": Path("/x"),
            "sensorium_driver": Path("/d")}


def test_61_linked_keys_read_as_predicted(monkeypatch):
    paths = _census(monkeypatch)
    h = phases2.phase_h4(paths, _two())
    assert h["keys"] == 61 and h["all_linked"] is True
    assert h["keys_as_predicted"] is True
    assert h["finding"] is None


def test_a_copy_where_a_link_was_POSSIBLE_is_a_finding_and_not_a_stop(
        monkeypatch):
    paths = _census(monkeypatch, linked_to_the_driver=59,
                    not_linked=["k1", "k2"], same_device=True)
    h = phases2.phase_h4(paths, _two())
    assert h["all_linked"] is False
    assert "without a boundary forcing it" in h["finding"]


def test_a_copy_ACROSS_a_filesystem_boundary_disables_the_finding_branch(
        monkeypatch):
    """§1.2: "if `st_dev` differs at measurement time, §2 records it and
    H4's finding branch does not apply"."""
    paths = _census(monkeypatch, linked_to_the_driver=0,
                    not_linked=["k1"], same_device=False, devices=[66, 99])
    h = phases2.phase_h4(paths, _two())
    assert h["all_linked"] is False
    assert "forced" in h["finding"]
    assert "without a boundary" not in h["finding"]


def test_the_byte_total_is_never_the_sum_of_the_per_entry_sizes(monkeypatch):
    """The measurement error this endpoint is about: 61 hard links to one
    40 MB binary hold 40 MB, not 2.4 GB."""
    paths = _census(monkeypatch)
    h = phases2.phase_h4(paths, _two())
    assert h["bytes_once_per_inode"] == 40_000_000
    assert h["distinct_inodes"] == 1
    assert h["bytes_once_per_inode"] != h["entries"] * 40_000_000


def test_a_key_that_holds_NO_binary_is_not_as_predicted_and_is_NAMED(
        monkeypatch):
    """The review's blocking finding. 61 key directories of which one holds
    no `cargo-sensorium` reads keys=61, entries=60, linked=60 — and a gate
    that compared `linked` to `entries` would call that "every key linked".
    §1's H4 says "61 focused keys, and FOR EVERY KEY the st_ino ... equals
    the driver's"; a key with no binary has no st_ino, so the gate is not
    met and the instrument must say so, naming the key."""
    paths = _census(monkeypatch, keys=61, entries=60,
                    linked_to_the_driver=60,
                    keys_without_a_binary=["k60"],
                    entries_cover_every_key=False)
    h = phases2.phase_h4(paths, _two())
    assert h["all_linked"] is False
    assert h["entries_cover_every_key"] is False
    assert h["keys_without_a_binary"] == ["k60"]
    assert h["as_predicted"] is False
    assert "k60" in (h["finding"] or "")


def test_the_denominator_is_the_KEYS_and_never_the_entries(monkeypatch):
    """Stated as a unit, so the mutation that swaps them back is caught by
    a test that names the rule rather than by a coincidence of numbers."""
    paths = _census(monkeypatch, keys=61, entries=60,
                    linked_to_the_driver=60,
                    keys_without_a_binary=["k60"],
                    entries_cover_every_key=False)
    h = phases2.phase_h4(paths, _two())
    assert h["linked_to_the_driver"] == h["entries"]      # the trap
    assert h["linked_to_the_driver"] != h["keys"]         # the truth
    assert h["all_linked"] is False


# --------------------------- H2/H3 over a SUBSET are never `as_predicted`

def _short(n=51):
    """A loop that stopped short: `n` rows measured, the rest never run."""
    two = _two()
    two["refocuses"] = two["refocuses"][:n]
    two["n"], two["measured"] = 61, n
    two["budget_exhausted"] = [r[1] for r in rows.ROWS[n:]]
    return two


def test_H2_over_a_SHORT_loop_is_None_and_never_true():
    """`match_n == len(measured)` compares a count to its own denominator,
    so a loop that stopped at 51 could write `match_as_predicted: true`
    beside `n: 51`. §1's gate is MATCH 61 of 61; over fewer rows there is
    no answer, and `None` plus a named reason is the only honest one --
    Task 6 reads this RAW file to write §4."""
    h = phases.phase_h2(_short())
    assert h["match_as_predicted"] is None
    assert h["dropped"], "a null must carry its reason"
    assert any("61" in d for d in h["dropped"])
    assert h["match_n"] == 51          # the count itself is still measured


def test_H3_over_a_SHORT_loop_is_None_and_never_true():
    h = phases.phase_h3(_short())
    assert h["pairs_as_predicted"] is None
    assert h["dropped"]
    assert h["pairs_of_one"] == 51


def test_a_KILLED_invocation_also_takes_the_boolean_to_None():
    two = _two()
    two["killed"] = ["a_pager_can_be_shared_across_threads"]
    assert phases.phase_h2(two)["match_as_predicted"] is None
    assert phases.phase_h3(two)["pairs_as_predicted"] is None


def test_a_WHOLE_loop_still_answers_true_with_an_empty_dropped():
    h2, h3 = phases.phase_h2(_two()), phases.phase_h3(_two())
    assert h2["match_as_predicted"] is True and h2["dropped"] == []
    assert h3["pairs_as_predicted"] is True and h3["dropped"] == []


def test_a_WHOLE_loop_that_really_DIVERGED_is_False_and_not_None():
    """`None` is "not measured"; `False` is "measured, and not as
    predicted". A rule that returned None for both would hide a divergence
    behind a bound that was never reached."""
    h = phases.phase_h2(_two({
        "unload_credits_the_weights_back": {"verdict": "DIVERGED",
                                            "rc": 1}}))
    assert h["match_as_predicted"] is False
    assert h["dropped"] == []
