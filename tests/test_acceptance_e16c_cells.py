"""E16 part C's CELL, on hand-built inputs.

One cell decides part C: H4, §9's row about the retrofit, read over a copy
of this box's own store. It is a pure function over rows somebody could type
by hand, and this module is the only place it is exercised against inputs
somebody chose -- the measurement runs once, on a copy of a store that took
a year to fill, and a decision function first seen on the day of the run is
a decision function nobody has ever watched refuse.

WHAT IS BEING PREVENTED
-----------------------
* **a cell that cannot STOP.** Each of H4's four clauses has a passing input
  AND a failing one differing in one field, and the failing one names the
  trace or the file it failed over.
* **a hole read as a pass.** `None` is what `e16c.py` writes for a phase
  that did not run, and an EMPTY list is what a copy of nothing or a grep
  over a mistyped root produces. Both are `dropped`, never PASS -- three of
  H4's four clauses are "every one of these is so", which is vacuously true
  over nothing.
* **a line the instrument cannot read.** `LINE`, `CLEAN` and `SUMMARY` are
  pinned against strings `redact_cmd.line_for` and `redact_cmd.summary`
  BUILD, not against strings typed here: an instrument that silently stops
  matching reports a green run over an unmeasured claim, and the day it
  stops matching is the day the command's wording changes.
* **the eight-name cap read as an absence.** `_capped` prints eight names
  and counts the rest; a line that hit the cap without showing the token
  cannot say whether the rule fired on it, and is a HOLE rather than a
  failure.
* **a verdict word invented here.** `RULES` is §9's own PASS/STOP column for
  H4, checked by equality against the record on disk.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "acceptance_e16"))

import e16c_cells                                                 # noqa: E402
from e16c_cells import (CLEAN, DRY_TIMERS, EXPECTED_TRACES,       # noqa: E402
                        EXPECTED_VERSION, LINE, RULES, SUMMARY,
                        TIMERS, TOKEN_VAR, h4, parse_lines,
                        part_word)
from sensorium.query.redact_cmd import line_for, summary          # noqa: E402
from sensorium.redact_store import Plan                           # noqa: E402

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-13-sensorium-e16-redaction.md")

STEMS = ["20260101-000001-aaaaaa", "20260102-000002-bbbbbb",
         "20260103-000003-cccccc"]


# -- the inputs, as one phase each leaves them -----------------------------
def _dry(*, names=(TOKEN_VAR, "SSH_AUTH_SOCK"), values=2, over=STEMS):
    return {stem: {"names": list(names), "values": values, "note": None,
                   "capped": None} for stem in over}


def _after(*paths, count=0):
    return [{"path": p, "count": count}
            for p in (paths or ("store-c/traces/one.db",
                                "store-c/redaction.key"))]


def _infos(*, over=STEMS, exit=0, by="retrofit"):
    return [{"run": stem, "exit": exit, "by": by} for stem in over]


def _pass():
    return h4(list(STEMS), _dry(), _after(), _infos(), True)


# -- H4 PASSes when all four clauses do ------------------------------------
def test_all_four_clauses_pass_is_the_cells_only_pass():
    out = _pass()
    assert out["word"] == "PASS"
    assert out["read"] == ("3 traces, every one named in the dry run; "
                           "0 occurrences in 2 files after; "
                           "3/3 info exit 0, by retrofit; stdouts identical")
    assert [c["word"] for c in out["clauses"]] == ["PASS"] * 4
    assert [c["clause"] for c in out["clauses"]] == [1, 2, 3, 4]


def test_a_trace_whose_dry_run_line_does_not_name_the_token_stops_clause_one():
    rows = _dry()
    rows[STEMS[1]]["names"] = ["SSH_AUTH_SOCK"]
    out = h4(list(STEMS), rows, _after(), _infos(), True)
    assert out["word"] == "STOP"
    assert out["read"].startswith("clause 1: 1 trace(s) without the name "
                                  "in the dry run: ")
    assert STEMS[1] in out["read"]
    assert out["clauses"][0]["word"] == "STOP"
    # The other three still read: a STOP names the first failing clause and
    # the table beside it says whether the rest held.
    assert [c["word"] for c in out["clauses"][1:]] == ["PASS"] * 3


def test_a_trace_the_dry_run_printed_no_line_for_is_named_as_such():
    out = h4(list(STEMS), _dry(over=STEMS[:2]), _after(), _infos(), True)
    assert out["word"] == "STOP"
    assert f"{STEMS[2]} (no line)" in out["read"]


def test_a_refused_trace_carries_the_commands_own_sentence_into_the_stop():
    rows = _dry(over=STEMS[:2])
    rows[STEMS[2]] = {"names": [], "values": None, "capped": None,
                      "note": "REFUSED: env_hash does not reproduce under "
                              "the rust formula"}
    out = h4(list(STEMS), rows, _after(), _infos(), True)
    assert out["word"] == "STOP"
    assert "env_hash does not reproduce" in out["read"]


def test_a_dry_run_line_for_a_trace_the_copy_does_not_hold_stops():
    """The clause is a set EQUALITY (P13): a line naming a trace that is not
    in the copy means the instrument and the command were looking at two
    different stores."""
    rows = _dry(over=STEMS + ["20260104-000004-dddddd"])
    out = h4(list(STEMS), rows, _after(), _infos(), True)
    assert out["word"] == "STOP"
    assert "name a trace the copy does not hold" in out["read"]
    assert "20260104-000004-dddddd" in out["read"]


def test_a_file_still_holding_the_value_stops_clause_two():
    rows = _after() + [{"path": "store-c/traces/two.db", "count": 2}]
    out = h4(list(STEMS), _dry(), rows, _infos(), True)
    assert out["word"] == "STOP"
    assert out["read"] == ("clause 2: 1 file(s) still hold the value: "
                           "store-c/traces/two.db (2)")


def test_an_info_that_did_not_exit_zero_stops_clause_three():
    rows = _infos()
    rows[2] = {"run": STEMS[2], "exit": 1, "by": None}
    out = h4(list(STEMS), _dry(), _after(), rows, True)
    assert out["word"] == "STOP"
    assert out["read"] == f"clause 3: run {STEMS[2]}: info exit 1"


def test_a_trace_that_opens_but_says_another_hand_stops_clause_three():
    """Exit 0 alone is not the clause: a trace stamped `recorder` after a
    pass that was meant to rewrite it is a file the retrofit never reached."""
    rows = _infos()
    rows[0] = {"run": STEMS[0], "exit": 0, "by": "recorder"}
    out = h4(list(STEMS), _dry(), _after(), rows, True)
    assert out["word"] == "STOP"
    assert out["read"] == (f"clause 3: run {STEMS[0]}: by recorder, "
                           "not retrofit")


def test_a_trace_with_no_info_reading_at_all_stops_clause_three():
    out = h4(list(STEMS), _dry(), _after(), _infos(over=STEMS[:2]), True)
    assert out["word"] == "STOP"
    assert out["read"] == f"clause 3: run {STEMS[2]}: no info reading"


def test_two_stdouts_that_differ_stop_clause_four():
    out = h4(list(STEMS), _dry(), _after(), _infos(), False)
    assert out["word"] == "STOP"
    assert out["read"] == "clause 4: dry-run stdout != real"


def test_the_stop_names_the_first_failing_clause():
    """Two clauses failing is still one sentence, and it is the earlier
    clause's: a reader fixes the first thing that went wrong."""
    out = h4(list(STEMS), _dry(over=STEMS[:1]),
             _after() + [{"path": "store-c/x.db", "count": 9}],
             _infos(), False)
    assert out["word"] == "STOP"
    assert out["read"].startswith("clause 1:")
    assert [c["word"] for c in out["clauses"]] == ["STOP", "STOP",
                                                   "PASS", "STOP"]


# -- a hole is never a pass ------------------------------------------------
@pytest.mark.parametrize("missing,phase", [
    (0, "copy"), (1, "dry-run"), (2, "grep-after"), (3, "info"),
    (4, "compare")])
def test_a_phase_that_did_not_run_drops_the_cell(missing, phase):
    args = [list(STEMS), _dry(), _after(), _infos(), True]
    args[missing] = None
    out = h4(*args)
    assert out == {"word": "dropped", "read": f"{phase} did not run",
                   "clauses": []}


@pytest.mark.parametrize("empty,why", [
    (0, "the copy held no `*.db` file at all"),
    (2, "the sweep after the real run examined no file"),
    (3, "no trace was opened after the real run")])
def test_an_empty_input_is_dropped_and_never_vacuously_passed(empty, why):
    args = [list(STEMS), _dry(), _after(), _infos(), True]
    args[empty] = [] if empty else []
    out = h4(*args)
    assert out["word"] == "dropped"
    assert out["read"] == why


def test_an_empty_dry_run_parse_is_a_stop_and_not_a_drop():
    """A run that printed no line at all is not a hole in the instrument --
    the stdout was read, and it named nothing. That is clause 1 failing over
    every trace in the copy."""
    out = h4(list(STEMS), {}, _after(), _infos(), True)
    assert out["word"] == "STOP"
    assert out["read"].startswith("clause 1: 3 trace(s) without the name")


def test_a_file_whose_count_could_not_be_read_drops_rather_than_passes():
    rows = _after() + [{"path": "store-c/traces/odd.db", "count": None}]
    out = h4(list(STEMS), _dry(), rows, _infos(), True)
    assert out["word"] == "dropped"
    assert out["read"] == ("clause 2: 1 file(s) the sweep could not count: "
                           "store-c/traces/odd.db")
    # The clause table still says which clause held the hole.
    assert [c["word"] for c in out["clauses"]] == ["PASS", "dropped",
                                                   "PASS", "PASS"]


def test_a_capped_name_list_without_the_token_is_a_hole_not_a_failure():
    """`_capped` shows eight names and counts the rest. A line that hit the
    cap and does not show the token cannot say whether the rule fired on it:
    reading that as "the token was not redacted" would publish a STOP about
    a line nobody could read."""
    rows = _dry()
    rows[STEMS[0]] = {"names": ["A", "B"], "values": 4, "note": None,
                      "capped": 3}
    out = h4(list(STEMS), rows, _after(), _infos(), True)
    assert out["word"] == "dropped"
    assert "eight-name cap" in out["read"]
    assert f"{STEMS[0]} (+3 names not shown)" in out["read"]


def test_a_capped_line_that_does_show_the_token_reads_normally():
    rows = _dry()
    rows[STEMS[0]] = {"names": [TOKEN_VAR, "B"], "values": 4, "note": None,
                      "capped": 3}
    assert h4(list(STEMS), rows, _after(), _infos(), True)["word"] == "PASS"


# -- parsing the command's own lines ---------------------------------------
def test_parse_lines_reads_the_three_forms_of_one_stdout():
    stdout = (f"run {STEMS[0]}: env 2 redacted ({TOKEN_VAR}, SSH_AUTH_SOCK)"
              "; values 7; mode 644 -> 600\n"
              f"run {STEMS[1]}: nothing to redact; mode 600\n"
              f"run {STEMS[2]}: env 1 redacted ({TOKEN_VAR}); values 0; "
              "mode 600\n"
              "redacted 2 of 3 traces (1 already clean, 0 skipped, "
              "0 refused); spools under target/ and the TypeScript spool "
              "dirs are not reached\n")
    rows = parse_lines(stdout)
    assert set(rows) == set(STEMS)
    assert rows[STEMS[0]] == {"names": [TOKEN_VAR, "SSH_AUTH_SOCK"],
                              "values": 7, "note": None, "capped": None}
    assert rows[STEMS[1]] == {"names": [], "values": 0, "note": None,
                              "capped": None}
    assert rows[STEMS[2]]["names"] == [TOKEN_VAR]
    assert rows[STEMS[2]]["values"] == 0


def test_parse_lines_keeps_a_skipped_or_refused_sentence_and_counts_nothing():
    stdout = (f"run {STEMS[0]}: in flight (incomplete), skipped\n"
              f"run {STEMS[1]}: REFUSED: another redact is rewriting it\n")
    rows = parse_lines(stdout)
    assert rows[STEMS[0]]["values"] is None
    assert rows[STEMS[0]]["note"] == "in flight (incomplete), skipped"
    assert rows[STEMS[1]]["note"] == ("REFUSED: another redact is rewriting "
                                      "it")
    assert rows[STEMS[1]]["names"] == []


def test_parse_lines_reads_the_cap_as_a_cap():
    stdout = (f"run {STEMS[0]}: env 11 redacted (A, B, C, D, E, F, G, H, "
              "+3 more); values 1; mode 644 -> 600\n")
    row = parse_lines(stdout)[STEMS[0]]
    assert row["capped"] == 3
    assert row["names"] == ["A", "B", "C", "D", "E", "F", "G", "H"]


def test_parse_lines_passes_none_through():
    assert parse_lines(None) is None


# -- the regexes are the COMMAND's lines, not lines typed here -------------
def _plan(**kw):
    kw.setdefault("path", Path("/x/20260101-000001-aaaaaa.db"))
    kw.setdefault("run", STEMS[0])
    kw.setdefault("lang", "python")
    return Plan(**kw)


def test_the_line_regex_matches_what_line_for_builds():
    text = line_for(_plan(env_names=(TOKEN_VAR, "SSH_AUTH_SOCK"), values=7,
                          mode_before=0o644, meta={"env": {}}))
    m = LINE.match(text)
    assert m, text
    assert m.group("id") == STEMS[0]
    assert m.group("names") == f"{TOKEN_VAR}, SSH_AUTH_SOCK"
    assert m.group("v") == "7"
    assert m.group("mode") == "644 -> 600"


def test_the_clean_regex_matches_what_line_for_builds_for_an_untouched_trace():
    text = line_for(_plan())
    assert text == f"run {STEMS[0]}: nothing to redact; mode 600"
    assert CLEAN.match(text)
    assert not LINE.match(text)


@pytest.mark.parametrize("kw", [{"refused": "another key"},
                                {"skipped": "in flight (incomplete)"}])
def test_neither_pinned_regex_matches_a_refusal_or_a_skip(kw):
    text = line_for(_plan(**kw))
    assert not LINE.match(text) and not CLEAN.match(text)
    assert parse_lines(text + "\n")[STEMS[0]]["values"] is None


def test_the_summary_regex_matches_what_summary_builds():
    for swept, dir_mode in ((0, None), (2, (0o755, 0o700))):
        text = summary([_plan(), _plan(run=STEMS[1], meta={"env": {}})],
                       swept, dir_mode)
        assert SUMMARY.match(text), text
    assert not SUMMARY.match(f"run {STEMS[0]}: nothing to redact; mode 600")


# -- the rule table is the record's, not this instrument's -----------------
def test_the_rules_are_the_records_own():
    """Catches: §9's PASS/STOP column paraphrased into the instrument, where
    a softened endpoint would decide the measurement while §1 still read as
    the rule. Checked by EQUALITY against the record's own cell, and read
    from §1 ALONE -- §2's, §3's and §4's verdict tables quote the very
    clause under test, so a scan of the whole document would compare the
    instrument's output against itself."""
    text = DOC.read_text().split("## 2. Part A")[0]
    rows = {}
    for m in re.finditer(r"^\| (H\d) \|.*$", text, re.M):
        fields = m.group(0).split("|")
        assert len(fields) == 6, (m.group(1), len(fields))
        rows[m.group(1)] = {"PASS": fields[3].strip(),
                            "STOP": fields[4].strip()}
    assert set(RULES) <= set(rows), (set(RULES) - set(rows))
    for cell, clauses in RULES.items():
        for word, clause in clauses.items():
            assert clause == rows[cell][word], (cell, word, clause,
                                                rows[cell][word])


def test_dropped_names_every_other_cell_and_its_part():
    """The one measured cell and the seven deferred ones, with nothing
    falling between: a cell in neither list is one nobody decided about."""
    assert set(RULES) == {"H4"}
    assert dict(e16c_cells.DROPPED) == {
        "H1-env": "part A", "H1-values": "part B", "H2": "part A",
        "H3": "part A", "H5": "part B", "H6-env": "part A",
        "H6-values": "part B"}
    assert set(e16c_cells.CELL_TITLES) == set(RULES)


def test_the_token_variable_is_the_one_section_nine_names():
    assert TOKEN_VAR == "CLAUDE_CODE_MESSAGING_TOKEN"
    assert TOKEN_VAR in DOC.read_text().split("## 2. Part A")[0]


def test_the_pins_and_kill_rules_are_the_pre_registrations():
    assert EXPECTED_TRACES == 273
    assert EXPECTED_VERSION == "0.17.0"
    assert TIMERS == {"copy": 600, "redact": 900, "info": 900, "grep": 300,
                      "part": 2700}
    assert DRY_TIMERS == {name: seconds // 10
                          for name, seconds in TIMERS.items()}


# -- the part's own word ---------------------------------------------------
@pytest.mark.parametrize("word,expected", [("PASS", "DONE"),
                                           ("STOP", "DONE-WITH-STOP"),
                                           ("dropped", "DONE-WITH-STOP")])
def test_the_parts_word_is_h4s(word, expected):
    assert part_word({"H4": {"word": word}}) == expected


def test_a_missing_cell_is_not_a_passed_one():
    assert part_word({}) == "DONE-WITH-STOP"
