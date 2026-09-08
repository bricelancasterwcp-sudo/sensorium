"""E4″'s two control arms: which rows they run, which key each injects, and
how arm C's key is CHOSEN rather than picked.

§1.3 names both arms and their four rows so neither is a choice made at run
time, and it makes arm C's key a preflight FACT -- the first of session set
1's fourteen exact names absent from BOTH the original's recorded
environment and the runner's own -- because which keys this box's shell
exports is not knowable before the day. A key that is already present
would test nothing, and there is no fallback to one.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4p_rows as rows                                 # noqa: E402
import acceptance_e4pp_arms as arms                                # noqa: E402
from sensorium.query.refocus_env import SESSION_ORDER              # noqa: E402

#: §1.3's printed order, retyped ONCE here from the byte-locked document so
#: a change to `SESSION_ORDER` that the pre-registration did not authorise
#: fails the suite instead of silently moving arm C's choice.
DOC_ORDER = ("DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID", "TERM_SESSION_ID",
             "WINDOWID", "TMUX", "TMUX_PANE", "SSH_AGENT_PID",
             "SSH_AUTH_SOCK", "SSH_CLIENT", "SSH_CONNECTION", "SSH_TTY",
             "INVOCATION_ID", "JOURNAL_STREAM", "SYSTEMD_EXEC_PID")


def test_arm_Cs_candidate_list_is_the_documents_fourteen_EXACT_names():
    """§1.3: the fourteen names, in that order, and nothing else. The
    `CLAUDE_CODE_` prefix is NEVER a candidate -- a prefix names no key, so
    "the first key absent from both sides" would not be decidable over it,
    and a `CLAUDE_CODE_*` name invented here is one this box's agent
    session may create or destroy underneath the measurement."""
    assert arms.SESSION_CANDIDATES == DOC_ORDER
    assert arms.SESSION_CANDIDATES == SESSION_ORDER
    assert not any(n.startswith("CLAUDE_CODE_")
                   for n in arms.SESSION_CANDIDATES)


# ------------------------------------------------------------ the rows

def test_the_four_rows_are_chosen_BY_FIELD_and_never_by_index():
    """§1.3's four: rows 1-3 of §1.1, all three expected granted, and the
    one pager test expected WITHHELD for its single program thread -- so a
    control's env caveat is read beside a thread reason that must survive
    it."""
    four = arms.arm_rows(rows.ROWS)
    assert [r["name"] for r in four] == [
        "unmeasured_model_is_fail_closed_read_only_and_status_shows_null",
        "unknown_model_mutating_verbs_is_false",
        "stored_keep_gate_enables_mutating_verbs_and_populates_status",
        "a_pager_can_be_shared_across_threads"]
    assert [r["expected_licence"] for r in four] == [
        "granted", "granted", "granted", "WITHHELD"]
    assert four[3]["expected_program_threads"] == 1
    assert all(r["expected_program_threads"] == 0 for r in four[:3])


def test_the_selection_follows_the_PARTITION_not_the_table_order():
    """By FIELD: if §1.2's partition withheld row 1, the first three
    GRANTED rows would be 2, 3 and 4 -- and a selection that sliced the
    first three would have run a withheld row as a granted control."""
    doctored = dict(rows.EXPECTED_WITHHELD)
    doctored[rows.ROWS[0][1]] = 2
    four = arms.arm_rows(rows.ROWS, withheld=doctored)
    assert [r["name"] for r in four[:3]] == [n for _i, n, _t, _r in
                                             rows.ROWS[1:4]]


def test_the_pager_row_is_found_by_NAME_and_is_the_fourth():
    four = arms.arm_rows(rows.ROWS)
    assert four[-1]["name"] == arms.PAGER_ROW
    assert four[-1]["row"] == next(r for r in rows.ROWS
                                   if r[1] == arms.PAGER_ROW)


def test_a_table_that_does_not_hold_the_four_returns_what_it_holds():
    """A DRY table is two rows. `arm_rows` returns what is there and the
    runner reports `n`; it does not invent a row, and it does not raise --
    the arms simply do not run in a dry."""
    two = [r for r in rows.ROWS
           if r[1] in (rows.ROWS[0][1], arms.PAGER_ROW)]
    assert [r["name"] for r in arms.arm_rows(two)] == [
        rows.ROWS[0][1], arms.PAGER_ROW]


# --------------------------------------------------- arm C's chosen key

def test_the_FIRST_name_absent_from_BOTH_sides_is_chosen():
    original = {"DBUS_SESSION_BUS_ADDRESS": "unix:/x", "PATH": "/usr/bin"}
    mine = {"XDG_SESSION_ID": "3", "TERM_SESSION_ID": "w0t0p0"}
    assert arms.choose_session_key(original, mine) == "WINDOWID"


def test_a_name_present_on_EITHER_side_is_skipped():
    """Absent from BOTH. A key already on one side would be a key the
    compare has seen, and setting it again tests nothing."""
    assert arms.choose_session_key({"DBUS_SESSION_BUS_ADDRESS": "x"},
                                   {}) == "XDG_SESSION_ID"
    assert arms.choose_session_key(
        {}, {"DBUS_SESSION_BUS_ADDRESS": "x"}) == "XDG_SESSION_ID"


def test_the_choice_walks_the_DOCUMENTS_order_and_records_what_it_skipped():
    """§1.4's H6 second reading: which key was chosen AND the names the
    choice skipped over, so the rule is checkable rather than asserted."""
    original = {"DBUS_SESSION_BUS_ADDRESS": "x"}
    mine = {"XDG_SESSION_ID": "3"}
    choice = arms.session_key_choice(original, mine)
    assert choice["key"] == "TERM_SESSION_ID"
    assert [s["name"] for s in choice["skipped"]] == [
        "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID"]
    assert choice["skipped"][0]["present_on"] == ["the original"]
    assert choice["skipped"][1]["present_on"] == ["the runner"]
    assert choice["candidates"] == list(DOC_ORDER)


def test_NO_eligible_key_is_None_and_says_so_rather_than_falling_back():
    """§1.3: "If no key of the list is absent from both sides, the
    preflight REFUSES to launch and says so: it never falls back to a key
    that is already present, and never reaches outside the set for one."""
    both = {n: "set" for n in DOC_ORDER}
    assert arms.choose_session_key(both, {}) is None
    choice = arms.session_key_choice(both, {})
    assert choice["key"] is None
    assert len(choice["skipped"]) == len(DOC_ORDER)
    assert "never falls back" in choice["reason"]


def test_the_choice_never_reaches_for_a_CLAUDE_CODE_name():
    """Even when every one of the fourteen is taken."""
    both = {n: "set" for n in DOC_ORDER}
    assert arms.choose_session_key(both, {"CLAUDE_CODE_SESSION_ID": "s"}) \
        is None


# ------------------------------------------------------ the arm's env

def test_arm_env_returns_a_NEW_dict_and_never_mutates_the_base():
    base = {"PATH": "/usr/bin"}
    got = arms.arm_env(base, arms.ARM_B_KEY, "1")
    assert got == {"PATH": "/usr/bin", "E4PP_INPUT": "1"}
    assert base == {"PATH": "/usr/bin"}
    assert got is not base


def test_arm_B_injects_the_key_on_no_list():
    """§1.3: a key on no list, standing in for something the program could
    have read. If it no longer withholds, the licence stopped meaning
    anything -- which is H5's STOP."""
    from sensorium.query.refocus_env import is_session_key
    assert arms.ARM_B_KEY == "E4PP_INPUT"
    assert not is_session_key(arms.ARM_B_KEY)


def test_arm_C_injects_a_key_that_IS_on_the_session_list():
    from sensorium.query.refocus_env import is_session_key
    assert all(is_session_key(n) for n in arms.SESSION_CANDIDATES)


# ------------------------------------------------------------ run_arm

def test_run_arm_pairs_each_row_with_ITS_OWN_invocation(monkeypatch):
    """Task 3's finding 1. Arms B and C re-refocus four of arm A's run ids
    into the SAME fresh store, so after all three arms there are up to
    three traces whose `refocus_of` is one of those originals. The pair
    rule resolves it only if each pair is found with THAT invocation's
    launch timestamp, immediately after it -- a closing sweep by
    `refocus_of` alone would read a pair count of 3 on four rows and STOP
    H3 for an instrument reason."""
    seen = []

    def fake_refocus_one(paths, cfg, row, extra_env=None, label=None):
        seen.append({"row": row, "extra_env": extra_env, "label": label})
        return {"index": row[0], "name": row[1], "original": row[3],
                "verdict_word": "MATCH", "wall_s": 1.0, "timed_out": False,
                "pair": {"n": 1}, "licence_partition": {"licence": "granted"}}

    monkeypatch.setattr(arms.eph, "refocus_one", fake_refocus_one)
    four = arms.arm_rows(rows.ROWS)
    rec = arms.run_arm({"sensorium_dir": Path("/nowhere")},
                       {"refocus_timeout": 1800, "gate_n": 61},
                       four, "TMUX", "stamp", "armC")
    assert rec["n"] == 4
    assert [s["extra_env"] for s in seen] == [{"TMUX": "stamp"}] * 4
    assert [s["label"] for s in seen] == ["armC"] * 4
    assert rec["key"] == "TMUX" and rec["value"] == "stamp"
    assert list(rec["by_name"]) == [r["name"] for r in four]


def test_run_arm_records_a_KILLED_row_rather_than_dropping_it(monkeypatch):
    """A killed invocation is a fact of the arm, not a shorter arm."""
    def fake(paths, cfg, row, extra_env=None, label=None):
        return {"index": row[0], "name": row[1], "timed_out": True,
                "wall_s": 1800.0, "verdict_word": None,
                "licence_partition": {"licence": None}}

    monkeypatch.setattr(arms.eph, "refocus_one", fake)
    rec = arms.run_arm({}, {}, arms.arm_rows(rows.ROWS), "K", "v", "armB")
    assert rec["killed"] == [r["name"] for r in arms.arm_rows(rows.ROWS)]
    assert rec["n"] == 4


# ============ fix round 1: minor (d) — the arms share the loop's bound ====

def test_an_arm_row_past_the_DEADLINE_is_NOT_RUN_and_named(monkeypatch):
    """§1.4 bounds the whole LOOP at 1 h 30 min, and arms B and C are part
    of it: a run that spent the budget on arm A must not then run four more
    invocations outside every bound this record pre-registered."""
    import time as _t
    seen = []

    def fake(paths, cfg, row, extra_env=None, label=None):
        seen.append(row[1])
        return {"index": row[0], "name": row[1], "verdict_word": "MATCH",
                "wall_s": 1.0, "timed_out": False, "pair": {"n": 1},
                "licence_partition": {"licence": "granted"}}

    monkeypatch.setattr(arms.eph, "refocus_one", fake)
    rec = arms.run_arm({}, {}, arms.arm_rows(rows.ROWS), "K", "v", "armB",
                       deadline=_t.monotonic() - 1)
    assert seen == []
    assert len(rec["budget_exhausted"]) == 4
    assert rec["measured"] == 0
    assert rec["n"] == 4                       # the ROWS, not the runs
    assert all("not_run" in r for r in rec["refocuses"])


def test_NO_deadline_runs_every_row_exactly_as_before(monkeypatch):
    monkeypatch.setattr(arms.eph, "refocus_one",
                        lambda paths, cfg, row, extra_env=None, label=None: {
                            "index": row[0], "name": row[1],
                            "timed_out": False, "wall_s": 1.0})
    rec = arms.run_arm({}, {}, arms.arm_rows(rows.ROWS), "K", "v", "armB")
    assert rec["budget_exhausted"] == []
    assert rec["measured"] == rec["n"] == 4
