"""E4″'s eight phases, on synthetic answers built to §1's own expectation.

Every fixture here answers exactly as §1.2 and §1.4 predict -- 57 granted,
the four withheld with 1/4/4/4, MATCH 61, pair 1 of 1, `RUSTDOCFLAGS`
stripped on every pair and in no changed list, one differing session key --
so a phase that read the partition backwards and a phase that read it
correctly cannot both pass. The `overrides` argument is how each test
breaks exactly one of those and asks what the phase says.
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
         arm=None, orig_rt="d9ce385a08c66466", rerun_rt="83d9294b8135c157"):
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
        "original_rt_hash": {"value": orig_rt, "fragments": 1,
                             "reason": None},
        "rerun_rt_hash": {"value": rerun_rt, "fragments": 1, "reason": None},
        "wall_s": 7.0, "timed_out": False,
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


# ------------------------------------------------------------------- H7

def _raw(two=None, arm_b=None, arm_c=None, probe=None) -> dict:
    return {
        "raw_pass2": two if two is not None else _two(),
        "raw_arm_b": arm_b, "raw_arm_c": arm_c,
        "pins": {"sensorium_version_metadata_probe":
                 probe if probe is not None
                 else {"token": "0.8.5", "reason": None, "rc": 0}},
    }


def test_an_honest_instrument_reads_zero_and_PASSES():
    h = ph.phase_h7_instrument(_raw())
    assert h["headline"] == 0
    assert h["counts_carry_their_source_line"] is True
    assert h["licence_verified_counts"]["n"] == 61
    assert h["version_probe"]["token"] == "0.8.5"
    assert h["verdict"] == "PASS"


def test_a_partition_cell_that_is_None_on_a_PRINTED_licence_is_a_STOP():
    """H7 is a STOP of the INSTRUMENT, told apart in the record from a STOP
    of the subject."""
    h = ph.phase_h7_instrument(_raw(_two({
        "unknown_model_mutating_verbs_is_false": {"program": None}})))
    assert h["headline"] == 1
    assert h["null_cells"][0]["name"] == "unknown_model_mutating_verbs_is_false"
    assert h["verdict"] == "STOP"
    assert "instrument" in h["stop_is_of_the"]


def test_a_count_with_NO_source_line_fails_the_instrument():
    h = ph.phase_h7_instrument(_raw(_two({
        "unknown_model_mutating_verbs_is_false": {"counts_source": None}})))
    assert h["counts_carry_their_source_line"] is False
    assert h["verdict"] == "STOP"


def test_a_version_probe_that_is_an_EMPTY_STRING_fails_the_instrument():
    """E4′ §5's gap 2, as a gate: a token or `null` with its reason, never
    a blank that reads as measured."""
    h = ph.phase_h7_instrument(_raw(probe={"token": "", "reason": None,
                                           "rc": 0}))
    assert h["version_probe_ok"] is False
    assert h["verdict"] == "STOP"


def test_a_probe_that_is_NULL_WITH_a_reason_is_honest_and_PASSES():
    h = ph.phase_h7_instrument(_raw(probe={
        "token": None, "reason": "No package metadata was found", "rc": 1}))
    assert h["version_probe_ok"] is True
    assert h["verdict"] == "PASS"


def test_licence_verified_counts_that_could_NOT_be_built_fail_the_gate():
    """§1.4: `H7.licence_verified_counts` is non-null. E4′ published null
    there for a whole run, which is the gap this gate exists to close."""
    two = _two()
    for r in two["refocuses"]:
        r.pop("licence")
    h = ph.phase_h7_instrument(_raw(two))
    assert h["licence_verified_counts"] is None
    assert h["verdict"] == "STOP"


def test_the_arms_rows_are_counted_too_and_never_only_arm_A():
    """A `None` partition cell on a control arm is the same instrument
    failure as one on the subject."""
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    bad = _arm(arms.ARM_B_KEY, "1", {names[0]: {"program": None}})
    h = ph.phase_h7_instrument(_raw(arm_b=bad))
    assert h["headline"] == 1
    assert h["null_cells"][0]["arm"] == "armB"


# ------------------------------------------------- §1.5's two tool hashes

def _trace(dirpath, run, flags):
    import json as _j
    import sqlite3
    dirpath.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(dirpath / f"{run}.db")
    try:
        con.execute("create table meta (key text primary key, value text)")
        con.execute("insert into meta values ('run_id', ?)",
                    (_j.dumps(run),))
        con.execute("insert into meta values ('env', ?)",
                    (_j.dumps({"RUSTDOCFLAGS": flags} if flags else {}),))
        con.commit()
    finally:
        con.close()


def _flags(root, rt):
    d = f"{root}/sensorium/rt/{rt}/unwind"
    return (f"--extern sensorium_rt={d}/libsensorium_rt.rlib "
            f"-L dependency={d}")


def test_the_two_rt_hashes_are_read_from_the_TWO_TRACES(tmp_path):
    """The printed line names keys and never values, so the hash is read
    from each side's recorded environment: the original's from the copy in
    the fresh store, the re-run's from the trace this invocation made."""
    traces = tmp_path / "traces"
    _trace(traces, "orig-1", _flags("/t/a", "d9ce385a08c66466"))
    _trace(traces, "pair-1", _flags("/t/b", "83d9294b8135c157"))
    block = {"refocuses": [{"name": "n", "original": "orig-1",
                            "new_run": "pair-1"}]}
    ph.read_rt_hashes({"sensorium_dir": tmp_path}, block)
    r = block["refocuses"][0]
    assert r["original_rt_hash"]["value"] == "d9ce385a08c66466"
    assert r["rerun_rt_hash"]["value"] == "83d9294b8135c157"
    assert r["rt_hashes_differ"] is True


def test_two_EQUAL_hashes_are_recorded_as_equal_and_not_hidden(tmp_path):
    traces = tmp_path / "traces"
    _trace(traces, "orig-1", _flags("/t/a", "d9ce385a08c66466"))
    _trace(traces, "pair-1", _flags("/t/b", "d9ce385a08c66466"))
    block = {"refocuses": [{"name": "n", "original": "orig-1",
                            "new_run": "pair-1"}]}
    ph.read_rt_hashes({"sensorium_dir": tmp_path}, block)
    assert block["refocuses"][0]["rt_hashes_differ"] is False


def test_a_pair_with_NO_re_run_trace_reads_null_WITH_its_reason(tmp_path):
    """None-vs-false: a hash nobody read is not a hash that matched."""
    _trace(tmp_path / "traces", "orig-1", _flags("/t/a", "aaaaaaaaaaaaaaaa"))
    block = {"refocuses": [{"name": "n", "original": "orig-1",
                            "new_run": None}]}
    ph.read_rt_hashes({"sensorium_dir": tmp_path}, block)
    r = block["refocuses"][0]
    assert r["rerun_rt_hash"]["value"] is None
    assert r["rerun_rt_hash"]["reason"]
    assert r["rt_hashes_differ"] is None


def test_a_row_that_never_RAN_is_left_alone(tmp_path):
    block = {"refocuses": [{"name": "n", "not_run": "the bound was reached"}]}
    ph.read_rt_hashes({"sensorium_dir": tmp_path}, block)
    assert "original_rt_hash" not in block["refocuses"][0]


# ------------------------------------------------------------------- H8

def _h6_rec(corpus_rc=0, pytest_rc=0, cargo_rc=0, skipped=()):
    return {
        "corpus": {"rc": corpus_rc, "cases": 33, "failures": [],
                   "errors": [], "log": "c.log",
                   "json": {"cases": 33, "require_driver": True,
                            "skipped": list(skipped)}},
        "python": {"rc": pytest_rc, "summary": "2146 passed", "log": "p.log"},
        "cargo": {"rc": cargo_rc, "result_lines": ["test result: ok"],
                  "log": "r.log"},
        "all_green": corpus_rc == 0 and pytest_rc == 0 and cargo_rc == 0,
    }


def _h8(monkeypatch, rec=None, names=_UNSET, reason=None):
    """H8 lives in `acceptance_e4pp_phases2` (the 800-line split), so the
    stubs go on the module it resolves its own names in."""
    import acceptance_e4pp_phases2 as ph2
    monkeypatch.setattr(ph2.eph2, "phase_h6",
                        lambda paths, cfg: rec or _h6_rec())
    listing = {"command": "…", "rc": 0,
               "names": (["refocus_child_run", e4pp.SPAWNED_CASE]
                         if names is _UNSET else names),
               "reason": reason}
    monkeypatch.setattr(ph2, "corpus_case_names", lambda paths: listing)
    return ph.phase_h8_nothing_else({}, {"corpus_args": ["--require-driver"]})


def test_three_green_commands_and_the_named_case_present_passes(monkeypatch):
    h = _h8(monkeypatch)
    assert (h["corpus_rc"], h["pytest_rc"], h["cargo_rc"]) == (0, 0, 0)
    assert h["spawned_test_fn_present"] is True
    assert h["corpus_args"] == ["--require-driver"]
    assert h["verdict"] == "PASS"


@pytest.mark.parametrize("which", ["corpus_rc", "pytest_rc", "cargo_rc"])
def test_ANY_red_command_is_a_STOP_with_its_OWN_return_code(monkeypatch,
                                                            which):
    """§1.4's kill 2: three commands, three return codes, each its own
    field -- a summary line is prose and does not decide a gate."""
    h = _h8(monkeypatch, _h6_rec(**{which.replace("_rc", "") + "_rc": 1}))
    assert h[which] == 1
    assert h["verdict"] == "STOP"


def test_the_named_case_MISSING_from_the_collector_is_a_STOP(monkeypatch):
    """E4′ §5's gap 3, as a gate: the collector's `--json` publishes counts
    and no names, so the presence is read from its own `load_cases()`."""
    h = _h8(monkeypatch, names=["refocus_child_run"])
    assert h["spawned_test_fn_present"] is False
    assert h["verdict"] == "STOP"


def test_a_listing_that_could_NOT_be_read_is_null_WITH_its_reason(
        monkeypatch):
    """None-vs-false: "the collector printed nothing" and "the case is
    missing" are different facts, and only the second is about the
    repository."""
    h = _h8(monkeypatch, names=None, reason="ImportError: no corpus")
    assert h["spawned_test_fn_present"] is None
    assert h["dropped"] and "UNREAD" in h["dropped"][0]
    assert h["verdict"] == "STOP"


# ================== fix round 1 ==================================

# ------- Important 1: the gates count against the LOCKED 61 and 4 --------

def _short(block, *, n=59, measured=None, killed=(), exhausted=()):
    """An arm whose loop did not reach every row, in the four shapes it
    comes in. E4′ guarded exactly this and none of E4″'s new phases did:
    "a `true` sitting beside `n: 51` in the raw file is a sentence waiting
    to be misread"."""
    block = dict(block)
    block["n"] = n
    block["measured"] = n if measured is None else measured
    block["killed"] = list(killed)
    block["budget_exhausted"] = list(exhausted)
    return block


@pytest.mark.parametrize("phase, args", [
    ("phase_h2_fragment", ()),
    ("phase_h3_verdict_pair", ()),
    ("phase_h4_session", (SESSION_PIN,)),
])
def test_a_SHORT_arm_A_loop_is_None_and_never_a_PASS(phase, args):
    """§1.4's gates are over §1.1's 61, not over however many rows came
    back. A loop that stopped at 59 measured nothing about "61 of 61"."""
    two = _short(_two())
    h = getattr(ph, phase)(two, *args)
    assert h["as_predicted"] is None, h["as_predicted"]
    assert h["verdict"] == "STOP"
    assert any("61" in d for d in h["dropped"]), h["dropped"]


@pytest.mark.parametrize("phase, args", [
    ("phase_h2_fragment", ()),
    ("phase_h3_verdict_pair", ()),
    ("phase_h4_session", (SESSION_PIN,)),
])
def test_a_KILLED_row_takes_arm_A_to_None_too(phase, args):
    two = _short(_two(), n=61, killed=["a_pager_can_be_shared_across_threads"])
    h = getattr(ph, phase)(two, *args)
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"
    assert any("KILLED" in d for d in h["dropped"])


@pytest.mark.parametrize("phase, args", [
    ("phase_h2_fragment", ()),
    ("phase_h3_verdict_pair", ()),
    ("phase_h4_session", (SESSION_PIN,)),
])
def test_a_bound_REACHED_takes_arm_A_to_None_too(phase, args):
    two = _short(_two(), n=61, measured=60, exhausted=["a_row"])
    h = getattr(ph, phase)(two, *args)
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"
    assert any("never run" in d for d in h["dropped"])


def test_a_WHOLE_arm_A_loop_still_answers_True_with_an_empty_dropped():
    for phase, args in (("phase_h2_fragment", ()),
                        ("phase_h3_verdict_pair", ()),
                        ("phase_h4_session", (SESSION_PIN,))):
        h = getattr(ph, phase)(_two(), *args)
        assert h["as_predicted"] is True, phase
        assert h["dropped"] == [], phase


def _arm_full(key, value, over=None, arm="armB"):
    a = _arm(key, value, over, arm=arm)
    a["measured"] = a["n"]
    a["budget_exhausted"] = []
    return a


def test_a_SHORT_arm_B_is_None_and_never_a_PASS():
    """The arms' denominator is §1.3's FOUR, not however many ran."""
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    arm = _arm_full(arms.ARM_B_KEY, "1", over)
    arm["refocuses"] = arm["refocuses"][:3]
    arm["n"] = arm["measured"] = 3
    h = ph.phase_h5_input(arm)
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"
    assert any("4" in d for d in h["dropped"])


def test_a_KILLED_arm_B_row_is_None_and_never_a_PASS():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    arm = _arm_full(arms.ARM_B_KEY, "1", over)
    arm["killed"] = [names[0]]
    h = ph.phase_h5_input(arm)
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"


def test_a_SHORT_arm_C_is_None_and_never_a_PASS():
    arm = _arm_c()
    arm["refocuses"] = arm["refocuses"][:3]
    arm["n"] = arm["measured"] = 3
    arm["killed"], arm["budget_exhausted"] = [], []
    h = ph.phase_h6_session_key(_two(), arm, SESSION_PIN, INJECTED)
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"


def test_a_SHORT_arm_A_also_takes_H6_to_None():
    """H6 compares arm C's word against ARM A's for the same row, so a
    short arm A is a short comparison."""
    arm = _arm_c()
    arm["measured"], arm["killed"], arm["budget_exhausted"] = arm["n"], [], []
    h = ph.phase_h6_session_key(_short(_two()), arm, SESSION_PIN, INJECTED)
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"


def test_H1_over_a_SHORT_loop_is_None_and_never_a_PASS():
    """The same guard on the partition: a loop that killed two WITHHELD
    rows could still count 57 granted and read as §1.2's partition."""
    h = ph.phase_h1(_short(_two()))
    assert h["partition_as_predicted"] is None
    assert h["dropped"]


def test_H1_over_a_WHOLE_loop_is_unchanged():
    h = ph.phase_h1(_two())
    assert h["partition_as_predicted"] is True
    assert h["dropped"] == []
    assert h["granted_n"] == 57


# ------- Important 2: an UNREADABLE hash is neither differ nor equal -----

def test_a_pair_whose_hash_could_not_be_READ_is_counted_as_neither():
    """`hashes_differ` read 0 whether no pair differed or no pair was
    readable. Three numbers now, and the denominator is the readable
    ones."""
    h = ph.phase_h2_fragment(_two({
        "unknown_model_mutating_verbs_is_false": {"rerun_rt": None}}))
    assert h["hashes_differ"] == 60
    assert h["hashes_equal_so_the_strip_was_untested"] == []
    assert h["hashes_unread"] == ["unknown_model_mutating_verbs_is_false"]
    assert h["hashes_readable"] == 60
    assert any("could not be read" in d for d in h["dropped"])


def test_ALL_hashes_unread_is_not_the_same_answer_as_none_differing():
    h = ph.phase_h2_fragment(_two({
        n: {"orig_rt": None, "rerun_rt": None}
        for _i, n, _t, _r in rows.ROWS}))
    assert h["hashes_differ"] == 0
    assert h["hashes_readable"] == 0
    assert len(h["hashes_unread"]) == 61


def test_every_hash_readable_leaves_the_unread_list_EMPTY():
    h = ph.phase_h2_fragment(_two())
    assert h["hashes_unread"] == []
    assert h["hashes_readable"] == 61
    assert h["dropped"] == []


# ------- Important 4: H6 publishes a set it MEASURED ---------------------

def test_H6_publishes_a_measured_set_that_merely_DISAGREES_with_the_pin():
    """§1.3: a `null` with a reason is the only not-measured. A set every
    pair printed WAS measured; that it is not the expected one is what
    `session_names_match` and the verdict are for."""
    h = ph.phase_h6_session_key(_two(), _arm_c(), SESSION_PIN, "SSH_TTY")
    assert h["session_names"] == sorted(SESSION_PIN + [INJECTED])
    assert h["session_names_match"] == 0
    assert h["expected_session_names"] == sorted(SESSION_PIN + ["SSH_TTY"])
    assert h["verdict"] == "STOP"


def test_H6_nulls_the_set_only_when_the_pairs_DISAGREE_among_themselves():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    h = ph.phase_h6_session_key(
        _two(), _arm_c({names[0]: {"session": SESSION_PIN}}),
        SESSION_PIN, INJECTED)
    assert h["session_names"] is None
    assert any("did not agree" in d for d in h["dropped"])
    assert h["verdict"] == "STOP"


# ------- minor (a): H5's by-name half is bounded too ---------------------

def test_a_TRUNCATED_arm_B_changed_list_cannot_answer_the_key_question():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    over[names[1]] = {"licence": "WITHHELD",
                      "changed": [f"K{i}" for i in range(9)],
                      "changed_truncated": True}
    h = ph.phase_h5_input(_arm_full(arms.ARM_B_KEY, "1", over))
    assert h["env_caveat_names_the_key"] is None
    assert h["changed_lists_bounded"] == [names[1]]
    assert h["verdict"] == "STOP"


# ------- minor (b): an unread pager row is None, not False --------------

def test_thread_reason_kept_is_None_when_the_pager_rows_licence_was_UNREAD():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    over = {n: {"licence": "WITHHELD", "changed": [arms.ARM_B_KEY]}
            for n in names}
    over[arms.PAGER_ROW] = {"licence": None, "program": None}
    h = ph.phase_h5_input(_arm_full(arms.ARM_B_KEY, "1", over))
    assert h["thread_reason_kept"] is None
    assert h["thread_reason_reason"]


# ------- minor (c): an UNREAD session list is not an empty one ----------

def test_an_UNREAD_session_list_is_not_read_as_an_empty_set():
    """`None` turned into `[]` matched an empty pin and counted as a
    match. A line nobody read matches nothing."""
    h = ph.phase_h4_session(_two({
        "unknown_model_mutating_verbs_is_false": {"session": None}}), [])
    assert h["session_names_unread"] == [
        "unknown_model_mutating_verbs_is_false"]
    assert h["session_names_match"] == 0
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"


def test_an_UNREAD_session_list_in_arm_C_is_caught_the_same_way():
    names = [r["name"] for r in arms.arm_rows(rows.ROWS)]
    h = ph.phase_h6_session_key(
        _two(), _arm_c({names[0]: {"session": None}}), SESSION_PIN, INJECTED)
    assert h["session_names_unread"] == [names[0]]
    assert h["verdict"] == "STOP"
