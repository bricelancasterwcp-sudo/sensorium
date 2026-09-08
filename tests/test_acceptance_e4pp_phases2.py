"""E4″'s phases H7 and H8, and §1.5's two tool hashes.

The other half of `test_acceptance_e4pp_phases`, split at the H7 seam on
2026-09-08 to bring both halves under the 800-line ceiling, mirroring the
instrument's own `acceptance_e4pp_phases` / `acceptance_e4pp_phases2` split.
The fixtures are the first file's -- imported, never copied, so one change to
what §1 predicts still lands in one place.
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

sys.path.insert(0, str(REPO / "tests"))
from test_acceptance_e4pp_phases import (INJECTED, SESSION_PIN,    # noqa: E402
                                         _UNSET, _arm, _arm_c, _two)


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

def _trace(dirpath, run, flags, driver=None):
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
        if driver is not None:
            con.execute("insert into meta values ('driver_version', ?)",
                        (_j.dumps(driver),))
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


def test_the_ORIGINALS_driver_version_is_read_TOO(tmp_path):
    """E4″ gap 3. The instrument opened the copied original for its `env`
    and never for its `meta.driver_version`, so §1.5's "`driver_version` on
    both sides" had one cell -- and the originals' own token appeared
    nowhere in the record. Read beside the rt-hash pair, from the same
    `meta` the hash comes out of."""
    traces = tmp_path / "traces"
    _trace(traces, "orig-1", _flags("/t/a", "d9ce385a08c66466"),
           driver="cargo-sensorium 0.5.0")
    _trace(traces, "pair-1", _flags("/t/b", "83d9294b8135c157"),
           driver="cargo-sensorium 0.5.2")
    block = {"refocuses": [{"name": "n", "original": "orig-1",
                            "new_run": "pair-1"}]}
    ph.read_rt_hashes({"sensorium_dir": tmp_path}, block)
    got = block["refocuses"][0]["original_driver_version"]
    assert got["value"] == "cargo-sensorium 0.5.0"
    assert got["reason"] is None


def test_an_ORIGINAL_with_no_token_is_null_WITH_its_reason(tmp_path):
    """None-vs-blank, and the two ways it goes missing told apart: a trace
    this reader could not open is not a trace that records no token, and
    neither of them is "the two sides agree"."""
    traces = tmp_path / "traces"
    _trace(traces, "orig-1", _flags("/t/a", "d9ce385a08c66466"))
    block = {"refocuses": [{"name": "n", "original": "orig-1",
                            "new_run": None},
                           {"name": "m", "original": "gone", "new_run": None}]}
    ph.read_rt_hashes({"sensorium_dir": tmp_path}, block)
    recorded, missing = (r["original_driver_version"]
                         for r in block["refocuses"])
    assert recorded["value"] is None
    assert "records no `meta.driver_version`" in recorded["reason"]
    assert missing["value"] is None
    assert "could not be read" in missing["reason"]


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
    listing = {"command": "python -c 'from corpus.run_corpus import "
                          "load_cases; ...'", "rc": 0,
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
    and no names, so the presence is read from its own `load_cases()`.

    E4″ gap 1: the miss is `null` WITH the listing's command and rc, never a
    clean `False` -- a reader cannot tell "this reader looked the wrong way"
    from "the case is gone", and only the second is about the repository.
    The gate is unmoved: `None` is not `True`."""
    h = _h8(monkeypatch, names=["refocus_child_run"])
    assert h["spawned_test_fn_present"] is None
    assert h["spawned_test_fn_matched"] is None
    why = h["spawned_test_fn_reason"]
    assert "under neither" in why and "load_cases" in why
    assert "exited 0" in why
    assert any(why in d and "UNREAD" in d for d in h["dropped"])
    assert h["verdict"] == "STOP"


def test_the_case_under_its_PREFIXED_spelling_is_present(monkeypatch):
    """E4″ gap 1, the half that made the false negative: `load_cases()`
    names each case by its directory relative to `corpus/`, so the 43 cargo
    cases are spelled `rust/<name>` and the bare name is in the list of 63
    exactly never. The real run read `False` on a case that was collected,
    ran under `--require-driver` and came back equal."""
    h = _h8(monkeypatch, names=["rust/abort", f"rust/{e4pp.SPAWNED_CASE}"])
    assert h["spawned_test_fn_present"] is True
    assert h["spawned_test_fn_matched"] == f"rust/{e4pp.SPAWNED_CASE}"
    assert h["spawned_test_fn_reason"] is None
    assert h["dropped"] == []
    assert h["verdict"] == "PASS"


def test_the_LAST_SEGMENT_is_matched_and_never_a_substring(monkeypatch):
    """A last-path-segment match, not a `in`-the-string one: a case called
    `rust/refocus_spawned_test_fn_two` ends with the name as a substring and
    is a different case."""
    h = _h8(monkeypatch, names=[f"rust/{e4pp.SPAWNED_CASE}_two",
                                f"deep/nest/{e4pp.SPAWNED_CASE}x"])
    assert h["spawned_test_fn_present"] is None


def test_a_listing_that_could_NOT_be_read_is_null_WITH_its_reason(
        monkeypatch):
    """None-vs-false: "the collector printed nothing" and "the case is
    missing" are different facts, and only the second is about the
    repository. Both now carry the listing's own command and rc, which is
    what lets a reader re-run the question."""
    h = _h8(monkeypatch, names=None, reason="ImportError: no corpus")
    assert h["spawned_test_fn_present"] is None
    assert h["dropped"] and "UNREAD" in h["dropped"][0]
    assert "ImportError: no corpus" in h["spawned_test_fn_reason"]
    assert "exited 0" in h["spawned_test_fn_reason"]
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


# ================== fix round 2 ==================================

def test_an_UNREAD_env_line_is_not_read_as_a_CLEAN_changed_list():
    """Item 2. `r.get("env_changed_keys") or []` read a pair with no `env:`
    line at all as "RUSTDOCFLAGS is not in the changed list" -- the PASS
    direction, from a line nobody read. Same treatment H4 and H6 got: the
    pair contributes to neither count and blocks the gate."""
    two = _two()
    two["refocuses"][1]["env_changed_keys"] = None
    two["refocuses"][1]["env_stripped_keys"] = None
    two["refocuses"][1]["env_relocated_keys"] = None
    two["refocuses"][1]["env_line"] = None
    h = ph.phase_h2_fragment(two)
    assert h["env_line_unread"] == ["unknown_model_mutating_verbs_is_false"]
    assert h["rustdocflags_in_changed"] == 0        # over the 60 that read
    assert h["strip_clause_named"] == 60
    assert h["strip_clause_missing"] == []          # unread is not missing
    assert h["env_lines_readable"] == 60
    assert h["as_predicted"] is None
    assert h["verdict"] == "STOP"
    assert any("no `env:` line" in d for d in h["dropped"])


def test_an_unread_env_line_does_not_poison_the_RELOCATED_set():
    """It contributes no set either: `[]` in the distinct sets would null a
    cell every readable pair agreed on."""
    two = _two()
    for key in ("env_changed_keys", "env_stripped_keys",
                "env_relocated_keys", "env_line"):
        two["refocuses"][1][key] = None
    h = ph.phase_h2_fragment(two)
    assert h["relocated_set"] == list(e4pp.EXPECTED_RELOCATED)
    assert h["relocated_set_matches"] == 60


def test_every_env_line_read_leaves_the_unread_list_EMPTY():
    h = ph.phase_h2_fragment(_two())
    assert h["env_line_unread"] == []
    assert h["env_lines_readable"] == 61
    assert h["as_predicted"] is True


# ------- item 1: the arms' bound sentence is E4″'s own -------------------

def test_the_bound_sentence_is_DERIVED_from_the_budget_it_names():
    """The arms' `not_run` rows carried E4′'s "1 h 15 min", which is not
    this record's bound. Derived from `LOOP_BUDGET_S` so the sentence and
    the ceiling cannot drift apart."""
    assert "1 h 30 min" in e4pp.bound_sentence(e4pp.LOOP_BUDGET_S)
    # ...and the derivation reproduces E4′'s own sentence for E4′'s own
    # budget, which is the check that it is a derivation and not a retype.
    assert e4pp.bound_sentence(4500) == ph.eph.NOT_RUN_BOUND
    assert "45 min" in e4pp.bound_sentence(2700)
    # CARRIED-DEBT minor 1: a WHOLE number of hours dropped the "0 min" and
    # read `1 h` where every other bound reads `1 h 15 min` -- one grammar
    # above the hour, so a reader parsing the sentence has one rule.
    assert "1 h 00 min" in e4pp.bound_sentence(3600)
    assert "2 h 00 min" in e4pp.bound_sentence(7200)
