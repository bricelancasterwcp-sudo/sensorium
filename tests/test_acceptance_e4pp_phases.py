"""E4″'s phases H2-H6, on synthetic answers built to §1's own expectation.

Every fixture here answers exactly as §1.2 and §1.4 predict -- 57 granted,
the four withheld with 1/4/4/4, MATCH 61, pair 1 of 1, `RUSTDOCFLAGS`
stripped on every pair and in no changed list, one differing session key --
so a phase that read the partition backwards and a phase that read it
correctly cannot both pass. The `overrides` argument is how each test
breaks exactly one of those and asks what the phase says.

Split at the H7 seam on 2026-09-08: H7, §1.5's two tool hashes and H8 are
`test_acceptance_e4pp_phases2`, which imports these fixtures rather than
copying them -- the same `phases`/`phases2` split the instrument itself
carries. This file was 932 lines before the split, over a ceiling that the
suite checked for the instrument's modules and not for its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4p_rows as rows                                 # noqa: E402
import acceptance_e4pp_arms as arms                                # noqa: E402
import acceptance_e4pp_phases as ph                                # noqa: E402
import acceptance_e4pp_rows as e4pp                                # noqa: E402

SESSION_PIN = ["CLAUDE_CODE_SESSION_ID"]
INJECTED = "TMUX"
_UNSET = object()


def _row(index, name, target, run, *, licence=_UNSET, program=_UNSET,
         verdict="MATCH", rc=0, pair_n=1, children=(), stripped=_UNSET,
         changed=(), changed_truncated=False, session=_UNSET,
         session_truncated=False, counts_source="licence-clause",
         arm=None, orig_rt="d9ce385a08c66466", rerun_rt="83d9294b8135c157",
         orig_frags=1, rerun_frags=1, cargo=(3.3,)):
    """One refocus as `refocus_one` records it under E4″, with only the
    fields the phases read."""
    if licence is _UNSET:
        licence = ("WITHHELD" if name in rows.EXPECTED_WITHHELD
                   else "granted")
    if program is _UNSET:
        program = (rows.EXPECTED_WITHHELD.get(name, 0)
                   if licence is not None else None)
    if stripped is _UNSET:
        stripped = ["RUSTDOCFLAGS"]
    if session is _UNSET:
        session = list(SESSION_PIN)
    return {
        "index": index, "name": name, "target": target, "original": run,
        "arm": arm, "rc": rc, "verdict_word": verdict,
        "verdict_and_exit_agree": rc == ph.eph.VERDICT_EXIT.get(verdict),
        "pair": {"n": pair_n, "qualifying": [f"pair-{index}"],
                 "linked": [f"pair-{index}"], "children": list(children),
                 "unreadable": []},
        "new_run": f"pair-{index}" if pair_n == 1 else None,
        "printed_pair_run": f"pair-{index}" if pair_n == 1 else None,
        "pair_agrees_with_the_printed_id": pair_n == 1,
        "excluded_children_printed": list(children),
        "excluded_children_in_the_store": list(children),
        "env_status": "CHANGED" if changed else "unchanged",
        "env_unchanged_outside_session": bool(session) and not changed,
        "env_stripped_keys": list(stripped),
        "env_relocated_keys": list(e4pp.EXPECTED_RELOCATED),
        "env_changed_keys": list(changed), "env_changed_n": len(changed),
        "env_changed_keys_truncated": changed_truncated,
        "env_session_keys": (None if session is None else list(session)),
        "env_session_n": (None if session is None else len(session)),
        "env_session_keys_truncated": session_truncated,
        "env_line": "env: unchanged outside session set 1 (...)",
        "licence_facts": ["... unchanged outside session set 1 ..."],
        "licence_caveats": [],
        "licence_partition": {
            "licence": licence, "program_threads": program,
            "harness_threads": 1, "names_the_exclusion": True,
            "sides_agree": True, "unsubtracted_labels": [],
            "counts_source": counts_source},
        "licence": {"source_verified": True, "env_verified": True,
                    "exit_verified": True, "output_unverifiable": True,
                    "children_unverifiable": True},
        "original_rt_hash": {"value": orig_rt, "fragments": orig_frags,
                             "occurrences": 2, "reason": None},
        "rerun_rt_hash": {"value": rerun_rt, "fragments": rerun_frags,
                          "occurrences": 2, "reason": None},
        "wall_s": 7.0, "cargo_finished_s": list(cargo),
        "timed_out": False,
    }


def _two(overrides=None) -> dict:
    overrides = overrides or {}
    refocuses = [_row(i, n, t, r, **overrides.get(n, {}))
                 for i, n, t, r in rows.ROWS]
    return {"refocuses": refocuses, "n": 61, "measured": 61,
            "budget_exhausted": [], "killed": [], "pair_refusals": []}


def _arm(key, value, overrides=None, arm="armB") -> dict:
    overrides = overrides or {}
    four = arms.arm_rows(rows.ROWS)
    answers = []
    for r in four:
        kw = dict(overrides.get(r["name"], {}))
        kw.setdefault("arm", arm)
        answers.append(_row(*r["row"], **kw))
    return {"arm": arm, "key": key, "value": value, "n": len(answers),
            "refocuses": answers, "by_name": {a["name"]: a for a in answers},
            "rows": [r["name"] for r in four], "killed": [],
            "expected_licence": {r["name"]: r["expected_licence"]
                                 for r in four}}


# ------------------------------------------------------------------- H2

def test_the_predicted_fragment_reading_passes():
    h = ph.phase_h2_fragment(_two())
    assert h["rustdocflags_in_changed"] == 0
    assert h["strip_clause_named"] == 61
    assert h["relocated_set"] == list(e4pp.EXPECTED_RELOCATED)
    assert h["as_predicted"] is True
    assert h["verdict"] == "PASS"


def test_RUSTDOCFLAGS_in_ONE_changed_list_is_a_STOP():
    """H2's gate: the fragment is gone from the compare, or the strip did
    not fire and E4′'s confound is still there."""
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {
            "changed": ["RUSTDOCFLAGS"]}}))
    assert h["rustdocflags_in_changed"] == 1
    assert h["changed_by_pair"]["unknown_model_mutating_verbs_is_false"] == [
        "RUSTDOCFLAGS"]
    assert h["as_predicted"] is False
    assert h["verdict"] == "STOP"


def test_ONE_pair_whose_strip_clause_is_silent_is_a_STOP():
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {"stripped": []}}))
    assert h["strip_clause_named"] == 60
    assert h["strip_clause_missing"] == ["unknown_model_mutating_verbs_is_false"]
    assert h["verdict"] == "STOP"


def test_a_DIFFERENT_relocated_set_on_one_pair_nulls_the_cell_and_STOPs():
    """The set is a name list, not a count: a run that relocated four
    DIFFERENT keys would score 61/61 on a count and be a different finding
    entirely."""
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {}}))
    h2 = ph.phase_h2_fragment(_two())
    assert h["relocated_set"] == h2["relocated_set"]
    two = _two()
    two["refocuses"][1]["env_relocated_keys"] = ["CARGO_TARGET_DIR"]
    h3 = ph.phase_h2_fragment(two)
    assert h3["relocated_set"] is None
    assert len(h3["relocated_sets_seen"]) == 2
    assert h3["relocated_set_matches"] == 60
    assert h3["verdict"] == "STOP"


def test_a_TRUNCATED_changed_list_cannot_answer_the_membership_question():
    """§1.4's kill 7. The printed changed list stops at eight names, so on
    a longer one `RUSTDOCFLAGS`'s absence from the NAMES is not its absence
    from the list -- the pair goes unread with its reason rather than
    counting as a clean one."""
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {
            "changed": [f"K{i}" for i in range(9)],
            "changed_truncated": True}}))
    assert h["changed_lists_bounded"] == [
        "unknown_model_mutating_verbs_is_false"]
    assert h["rustdocflags_in_changed"] is None
    assert h["verdict"] == "STOP"


def test_the_two_rt_hashes_are_reported_per_pair_and_their_DIFFERENCE_named():
    """§1.5's proof that the two builds are not the same build -- and H2's
    second reading, that a pair whose hashes were EQUAL never tested its
    own strip."""
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {
            "rerun_rt": "d9ce385a08c66466"}}))
    assert h["hashes_differ"] == 60
    assert h["hashes_equal_so_the_strip_was_untested"] == [
        "unknown_model_mutating_verbs_is_false"]
    # Reported, never gated: the gate is the three cells above.
    assert h["verdict"] == "PASS"


def test_the_FRAGMENT_COUNT_per_side_is_published_and_not_only_read():
    """E4″ gap 4. §1.4's H2 row pre-commits TWO second readings -- the rt
    hash each side carries, and "the count of fragments removed per key per
    side". The first was a cell; the second was read into the raw on both
    sides and published on neither, so a reader after a pre-committed
    reading had to open a gitignored ledger."""
    h = ph.phase_h2_fragment(_two())
    assert h["fragments_per_side"] == {"original": 1, "rerun": 1}
    assert h["fragments_reason"] is None
    assert h["fragments_readable"] == 61
    # ...and per pair, beside the two hashes it belongs to.
    pair = h["rt_hashes_by_pair"]["unknown_model_mutating_verbs_is_false"]
    assert pair["original_fragments"] == 1 and pair["rerun_fragments"] == 1
    assert pair["original_occurrences"] == 2
    # ...and the number is COUNTED, not this record's own 1: a run whose
    # sides carried two and three fragments publishes two and three.
    other = ph.phase_h2_fragment(
        _two({n: {"orig_frags": 2, "rerun_frags": 3} for n in rows.NAMES}))
    assert other["fragments_per_side"] == {"original": 2, "rerun": 3}


def test_pairs_that_DISAGREE_on_the_fragment_count_publish_no_single_one():
    """`session_k`'s rule: one number per side only where every readable
    pair carried the same one. Two folded into one would report a subject
    that never existed -- and the reason names the counts seen."""
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {"orig_frags": 2}}))
    assert h["fragments_per_side"] is None
    assert "did not agree" in h["fragments_reason"]
    assert "original: 1, 2" in h["fragments_reason"]
    assert h["fragments_seen"] == {"original": [1, 2], "rerun": [1]}
    # Reported, never gated: H2's gate is its three membership cells.
    assert h["verdict"] == "PASS"


# ------------------------------------------------------------------- H3

def test_the_predicted_verdict_and_pair_reading_passes():
    h = ph.phase_h3_verdict_pair(_two())
    assert h["headline"] == 61
    assert h["pairs_of_one"] == 61
    assert h["word_and_exit_disagree"] == []
    assert h["excluded_children"] == 0
    assert h["verdict"] == "PASS"


@pytest.mark.parametrize("verdict, rc", [("DIVERGED", 1), ("REFUSED", 3)])
def test_a_single_non_MATCH_is_a_STOP_with_its_run_ids(verdict, rc):
    h = ph.phase_h3_verdict_pair(_two({
        "unknown_model_mutating_verbs_is_false": {"verdict": verdict,
                                                  "rc": rc}}))
    assert h["headline"] == 60
    assert h["non_match"][0]["verdict"] == verdict
    assert h["non_match"][0]["original"]
    assert h["verdict"] == "STOP"


def test_a_pair_count_other_than_one_is_a_STOP():
    """Task 3's finding 1 made mechanical: three arms refocus one original
    into one store, and a pair found by `refocus_of` alone would read 3."""
    h = ph.phase_h3_verdict_pair(_two({
        "unknown_model_mutating_verbs_is_false": {"pair_n": 3}}))
    assert h["pairs_of_one"] == 60
    # NAMED, with its run ids: "the pair count is 60" and "which pair" are
    # two different findings, and the second is the one Task 8 writes down.
    assert [x["name"] for x in h["not_one"]] == [
        "unknown_model_mutating_verbs_is_false"]
    assert h["not_one"][0]["n"] == 3
    assert h["verdict"] == "STOP"


def test_a_clean_run_names_NO_pair_as_wrong():
    """The other half: `not_one` empty on a run where every pair is one,
    so a reading that filled it with the GOOD pairs cannot pass."""
    h = ph.phase_h3_verdict_pair(_two())
    assert h["not_one"] == []
    assert h["verdict"] == "PASS"


def test_the_word_and_the_exit_are_compared_and_NEVER_derived():
    two = _two()
    two["refocuses"][1]["verdict_and_exit_agree"] = False
    two["refocuses"][1]["rc"] = 1
    h = ph.phase_h3_verdict_pair(two)
    assert len(h["word_and_exit_disagree"]) == 1
    # A finding, reported -- and the gate is still the headline and the
    # pairs, which this run met.
    assert h["headline"] == 61
    assert h["verdict"] == "PASS"


# ------------------------------------------------------------------- H4

def test_the_printed_session_set_matching_the_PIN_passes():
    h = ph.phase_h4_session(_two(), SESSION_PIN)
    assert h["session_names"] == SESSION_PIN
    assert h["session_k"] == 1
    assert h["session_names_match"] == 61
    assert h["withholding_cites_a_session_key"] == []
    assert h["verdict"] == "PASS"


def test_a_printed_set_that_disagrees_with_the_PIN_is_a_STOP():
    """H4 compares against the set recorded at PREFLIGHT, never against a
    set read out of the same lines it is checking."""
    h = ph.phase_h4_session(_two({
        "unknown_model_mutating_verbs_is_false": {
            "session": ["SSH_TTY"]}}), SESSION_PIN)
    assert h["session_names"] is None
    assert h["session_names_match"] == 60
    assert h["verdict"] == "STOP"


def test_a_K_that_disagrees_with_the_PINs_SIZE_is_a_STOP():
    h = ph.phase_h4_session(_two({
        "unknown_model_mutating_verbs_is_false": {
            "session": ["CLAUDE_CODE_SESSION_ID", "TMUX"]}}), SESSION_PIN)
    assert h["session_k_match"] == 60
    assert h["verdict"] == "STOP"


def test_a_WITHHOLDING_that_cites_a_SESSION_key_is_a_STOP():
    """The whole of R4: a session key never withholds. One that appears in
    a withheld pair's changed list is the exemption having failed."""
    h = ph.phase_h4_session(_two({
        "a_pager_can_be_shared_across_threads": {
            "changed": ["CLAUDE_CODE_SESSION_ID"]}}), SESSION_PIN)
    assert h["withholding_cites_a_session_key"] == [
        {"name": "a_pager_can_be_shared_across_threads",
         "keys": ["CLAUDE_CODE_SESSION_ID"]}]
    assert h["verdict"] == "STOP"


def test_K_ABOVE_EIGHT_nulls_the_names_and_decides_on_K_alone():
    """§1.4's kill 7, pre-committed: the by-name half goes null WITH its
    reason, the gate is decided on K alone, and the record says plainly
    that the bounded reading is not the full one."""
    pin = [f"K{i}" for i in range(11)]
    h = ph.phase_h4_session(_two({
        n: {"session": [f"K{i}" for i in range(8)],
            "session_truncated": True}
        for _i, n, _t, _r in rows.ROWS}), pin)
    assert h["session_names"] is None
    assert h["decided_on_k_alone"] is True
    assert "cap" in " ".join(h["dropped"]).lower()
    assert h["session_k_match"] == 0        # K is 8 on the line, 11 on the pin
    assert h["verdict"] == "STOP"


def test_a_bounded_reading_whose_K_agrees_PASSES_on_K_alone():
    """§1.4's kill 7, the other half: with the names unread, the gate is
    decided on K ALONE -- so a K that DOES equal the pin's size passes,
    with the by-name half published as unread rather than as agreeing."""
    pin = [f"K{i}" for i in range(9)]
    h = ph.phase_h4_session(_two({
        n: {"session": [f"K{i}" for i in range(9)], "session_truncated": True}
        for _i, n, _t, _r in rows.ROWS}), pin)
    # The COUNT is authoritative: the fixture's `env_session_n` is the
    # length of the printed list, so this asks the phase to read K from the
    # count field and not from the names.
    assert set(h["session_k_by_name"].values()) == {9}
    assert h["session_k_match"] == 61
    assert h["session_names"] is None
    assert h["decided_on_k_alone"] is True
    assert h["as_predicted"] is True
    assert h["verdict"] == "PASS"


def test_the_second_reading_carries_a_GRANTED_pairs_line_and_fact():
    h = ph.phase_h4_session(_two(), SESSION_PIN)
    assert "unchanged outside session set 1" in h["line_on_a_granted_pair"]
    assert h["pairs_with_an_empty_session_set"] == 0


# ------------------------------------------------------------------- H5

def test_arm_B_withheld_on_all_four_with_the_key_named_passes():
    arm = _arm(arms.ARM_B_KEY, "1", {
        n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
        for n in arms.arm_rows(rows.ROWS) and
        [r["name"] for r in arms.arm_rows(rows.ROWS)]})
    h = ph.phase_h5_input(arm)
    assert h["headline"] == 4
    assert h["env_caveat_names_the_key"] == 4
    assert h["verdict"] == "PASS"


def test_ONE_granted_line_in_arm_B_is_a_STOP():
    """§1.4: any granted line in arm B is a STOP -- the exemption ate the
    rule."""
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    over[names[0]] = {"licence": "granted", "changed": []}
    h = ph.phase_h5_input(_arm(arms.ARM_B_KEY, "1", over))
    assert h["headline"] == 3
    assert h["granted"] == [names[0]]
    assert h["verdict"] == "STOP"


def test_a_WITHHELD_whose_caveat_does_NOT_name_the_key_is_a_STOP():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    over[names[1]] = {"licence": "WITHHELD", "changed": ["SOMETHING_ELSE"]}
    h = ph.phase_h5_input(_arm(arms.ARM_B_KEY, "1", over))
    assert h["headline"] == 4
    assert h["env_caveat_names_the_key"] == 3
    assert h["verdict"] == "STOP"


def test_the_thread_reason_SURVIVING_the_env_caveat_is_the_second_reading():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    h = ph.phase_h5_input(_arm(arms.ARM_B_KEY, "1", over))
    assert h["thread_reason_kept"] is True
    over[arms.PAGER_ROW] = {"licence": "WITHHELD",
                            "changed": [arms.ARM_B_KEY], "program": 0}
    h2 = ph.phase_h5_input(_arm(arms.ARM_B_KEY, "1", over))
    assert h2["thread_reason_kept"] is False
    # A finding, not a gate: the gate is the headline and the caveat.
    assert h2["verdict"] == "PASS"


# ------------------------------------------------------------------- H6

def _arm_c(overrides=None):
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"session": SESSION_PIN + [INJECTED], "arm": "armC"}
            for n in names}
    for n, kw in (overrides or {}).items():
        over[n] = dict(over[n], **kw)
    return _arm(INJECTED, "stamp", over, arm="armC")


def test_arm_C_matching_arm_As_word_with_K_one_greater_passes():
    h = ph.phase_h6_session_key(_two(), _arm_c(), SESSION_PIN, INJECTED)
    assert h["headline"] == 4
    assert h["session_names"] == sorted(SESSION_PIN + [INJECTED])
    assert h["session_k"] == 2
    assert h["injected_key"] == INJECTED
    assert h["verdict"] == "PASS"


def test_a_licence_word_that_MOVED_under_arm_C_is_a_STOP():
    """The control that must not bite: a session key that withheld is the
    exemption having failed the other way."""
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    h = ph.phase_h6_session_key(
        _two(), _arm_c({names[0]: {"licence": "WITHHELD"}}),
        SESSION_PIN, INJECTED)
    assert h["headline"] == 3
    assert h["word_moved"][0]["name"] == names[0]
    assert h["verdict"] == "STOP"


def test_a_session_set_that_is_NOT_the_pin_plus_the_key_is_a_STOP():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    h = ph.phase_h6_session_key(
        _two(), _arm_c({names[0]: {"session": SESSION_PIN}}),
        SESSION_PIN, INJECTED)
    assert h["session_names"] is None
    assert h["session_names_match"] == 3
    assert h["verdict"] == "STOP"


def test_the_injected_key_is_DERIVED_from_the_pin_and_never_re_chosen():
    """Task 3's finding 3: the gate reads the pin and the second reading
    reports the cell, so they cannot differ."""
    h = ph.phase_h6_session_key(_two(), _arm_c(), SESSION_PIN, "SSH_TTY")
    assert h["injected_key"] == "SSH_TTY"
    # The lines say TMUX and the pin says SSH_TTY. The set the pairs
    # printed was MEASURED and is published; the disagreement is carried by
    # the match count and by the verdict, never by a null.
    assert h["session_names"] == sorted(SESSION_PIN + [INJECTED])
    assert h["session_names_match"] == 0
    assert h["verdict"] == "STOP"
