"""E17's decision layer, exercised on inputs somebody typed by hand.

`tests/acceptance_e17/e17_cells.py` is pure: every verdict E17 can reach is
a function of rows a test can build, and nothing in it runs a subprocess,
reads the clock or knows where this box keeps its files. That is what lets
every STOP -- including the two "STOP as instrument" readings that exist so
a cell cannot pass by measuring nothing -- be checked here, before the
measurement, which is made ONCE.

WHAT THIS FILE HOLDS AGAINST THE RECORD RATHER THAN AGAINST ITSELF
------------------------------------------------------------------
* `RULES` is §9's own PASS/STOP column, by EQUALITY against the record's §1
  table. A substring check cannot see a clause cut short.
* `CELL_TITLES` is §9's own row names, likewise.
* `MARKER_RE` is DERIVED from `tools.narrowing_fields(tools.table(True)
  ["tree"])` and held against the locked regex §1 spells out, so the code
  and the pre-registration cannot drift apart unnoticed.
* `LOCKED_VIA_CLI` and `LOCKED_CENSUS` are recomputed from `load_cases()`
  and the server's own tool table: a question that stops being a not-a-tool
  question, or a case added to the corpus, reddens here rather than turning
  H1's `via_cli` clause into a comparison nobody could fail.

PRE-REGISTERED MUTANTS FOR THIS MODULE
--------------------------------------
Mutate on a committed tree, run, restore, re-run green:

* `h1` dropping its census clause (`LOCKED_CENSUS` never compared) --
  caught by `test_h1_stops_on_a_census_short_by_one_case`.
* `h1` reading an ABSENT `mcp_differences` as `[]` -- caught by
  `test_h1_stops_as_instrument_when_compare_cli_was_not_honoured`.
* `h5` accepting `pings_sent < MIN_PINGS` -- caught by
  `test_h5_stops_as_instrument_on_too_few_pings`.
* `h5` reading `alive_before is False` as a pass -- caught by
  `test_h5_stops_as_instrument_when_the_group_was_never_alive`.
* `h6` treating a missing `mcp.jsonl` as 0 lines -- caught by
  `test_h6_drops_when_the_audit_file_was_not_read`.
* `part_word` letting a STOP through as DONE -- caught by
  `test_part_word_is_done_with_stop_on_any_stop_among_h1_to_h6`.
* `h3` counting the header line against the 65536-byte bound -- caught by
  `test_h3_does_not_count_the_header_or_the_marker_against_the_bound`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "acceptance_e17"))

import e17_cells                                                  # noqa: E402
from e17_cells import (CELLS, CELL_TITLES, ELEVEN,                # noqa: E402
                       EXPECTED_VERSION, LOCKED_CENSUS,
                       LOCKED_VIA_CLI, LOCKED_VIA_CLI_IDS, MARKER_RE,
                       MIN_PINGS, NINE, RULES, TIMEOUT_HEADER, h1, h2, h3,
                       h4, h5, h6, h7, latency, marker_re, part_word)

from corpus.cases import load_cases                               # noqa: E402
from sensorium.mcp import result, tools                           # noqa: E402

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-16-sensorium-e17-mcp.md")

#: §1 alone. Task 10 writes a verdict table into §2 quoting the very
#: clauses under test here, and a scan of the whole document would then
#: compare the instrument's output against itself.
SECTION_ONE = DOC.read_text().split("## 2. Measured")[0]

#: The row reader §9's table is parsed with -- the regex the plan names.
ROW = re.compile(r"^\| \*\*(H\d) [^|]*\*\* \| .* \| ([^|]*) \| ([^|]*) \|$",
                 re.M)


# -- the constants are the record's and the corpus's, not this file's ------
def test_rules_are_the_specs_own_rows():
    """Catches: §9's PASS/STOP column paraphrased or softened into the
    instrument, where it would decide the measurement while §1 still read
    as the rule. Equality, per cell, per word."""
    rows = {m.group(1): {"PASS": m.group(2).strip(), "STOP": m.group(3).strip()}
            for m in ROW.finditer(SECTION_ONE)}
    assert set(rows) == {"H1", "H2", "H3", "H4", "H5", "H6", "H7"}, rows
    assert set(RULES) == set(rows), set(RULES) ^ set(rows)
    for cell, clauses in RULES.items():
        assert clauses == rows[cell], (cell, clauses, rows[cell])


def test_cell_titles_are_the_specs_own_row_names():
    """Catches: a cell renamed in the instrument, so §2's verdict sentence
    names a row §9 does not have. `latency` is §9's eighth row -- the one
    with `—` in both columns -- and it is titled here too."""
    named = re.findall(r"^\| \*\*([^|*]+)\*\* \|", SECTION_ONE, re.M)
    assert named == list(CELL_TITLES.values()), (named,
                                                 list(CELL_TITLES.values()))


def test_the_cells_tuple_covers_every_rule_and_no_more():
    """Catches: a cell decided but never listed (so `part_word` and the
    verdict table never see it), or listed but never decided. Every §9 row
    has a cell; the one cell without a RULE is `latency`, which §9 gives
    `—` for both words because it is never gated."""
    assert tuple(CELL_TITLES) == CELLS
    assert set(CELLS) - set(RULES) == {"latency"}
    assert set(RULES) - set(CELLS) == set()
    assert re.search(r"^\| \*\*latency\*\* \| .* \| — \| — \|$",
                     SECTION_ONE, re.M)


def test_locked_via_cli_and_census_match_the_corpus():
    """Catches: the locked not-a-tool list or the locked census going stale
    against the corpus they were counted from -- which would turn H1's two
    strictest clauses into comparisons nobody could fail."""
    cases = load_cases()
    table = tools.table(True)
    not_a_tool = [(c.name, q["id"]) for c in cases for q in c.questions
                  if q["command"][0] not in table]
    assert tuple(qid for _, qid in not_a_tool) == LOCKED_VIA_CLI
    assert {case for case, _ in not_a_tool} == {e17_cells.VIA_CLI_CASE}
    assert LOCKED_VIA_CLI_IDS == tuple(f"{case}/{qid}"
                                       for case, qid in not_a_tool)
    assert LOCKED_CENSUS == (len(cases), sum(len(c.questions) for c in cases))


def test_marker_re_matches_the_marker_the_code_builds_for_tree():
    """Catches: §1's locked `narrow with:` list and `tree`'s own narrowing
    fields drifting apart. The regex is DERIVED from the server's table
    here and compared with the module's, then run against a marker the
    capping code actually produced."""
    derived = marker_re(tools.narrowing_fields(tools.table(True)["tree"]))
    assert derived.pattern == MARKER_RE.pattern
    text = _over_limit()
    capped, truncated, _lines, _bytes = result.cap(
        text, e17_cells.CAP_BYTES, tools.narrowing_fields(
            tools.table(True)["tree"]))
    assert truncated
    hits = [ln for ln in capped.split("\n") if MARKER_RE.match(ln)]
    assert len(hits) == 1, hits


def test_the_locked_marker_regex_is_the_records_own():
    """Catches: the derived regex quietly becoming something §1 does not
    say. §1 spells the pattern out; it must be this one, character for
    character."""
    assert f"`{MARKER_RE.pattern}`" in SECTION_ONE


def test_expected_version_is_the_one_section_one_pins():
    assert f"Python **{EXPECTED_VERSION}**" in SECTION_ONE
    assert NINE == tuple(n for n in tools.table(False))
    assert ELEVEN == NINE + ("refocus", "record")
    assert set(ELEVEN) == set(tools.table(True))


# -- helpers for the hand-built inputs -------------------------------------
def _over_limit(header: str = "exit 0: the trace answered affirmatively",
                lines: int = 3000) -> str:
    body = "\n".join(f"line {i:05d} " + "x" * 100 for i in range(lines))
    return header + "\n" + body


def _capped(header: str = "exit 0: the trace answered affirmatively") -> str:
    text, truncated, _l, _b = result.cap(
        _over_limit(header), e17_cells.CAP_BYTES, ("depth", "limit", "around"))
    assert truncated
    return text


def _h1_doc(**over) -> dict:
    doc = {"via": "mcp", "cases": 115, "questions": 253, "failures": [],
           "errors": [], "skipped": [], "via_cli": list(LOCKED_VIA_CLI_IDS),
           "mcp_differences": [], "require_driver": True}
    doc.update(over)
    return doc


def _h5(**over) -> dict:
    args = {"pings_sent": 10, "ping_max": 0.004, "alive_before": True,
            "group_gone_s": 0.3, "response_seen": False,
            "runs_after": {"answered": True, "traces": 1, "incomplete": 1},
            "timeout_header": TIMEOUT_HEADER, "timeout_is_error": True,
            "timeout_exit": None, "timeout_answered_s": 3.2,
            "timeout_group_gone_s": 3.3}
    args.update(over)
    return args


def _h6(**over) -> dict:
    checks = [{"question": e17_cells.PROC_CHECK, "failures": []}]
    checks += [{"question": f"q{i}", "failures": []} for i in range(4)]
    counts = {"questions": 4, "texts": 4, "in_texts": 0, "jsonl_lines": 5,
              "in_jsonl": 0, "stderr_bytes": 812, "in_stderr": 0}
    args = {"checks": checks, "counts": counts,
            "h6b": {"pattern": "<redacted>", "in_jsonl": 0}}
    args.update(over)
    return args


def _h4(**over) -> dict:
    args = {"names_off": list(NINE),
            "err_off": {"code": -32602, "message": "Unknown tool: record"},
            "names_on": list(ELEVEN),
            "record_header": "exit 0: the recorded command's own status",
            "runs_text": "20260916-101010-abcdef  exit:0  events:41  "
                         "cmd: main.py",
            "exceptions_check": []}
    args.update(over)
    return args


# -- H1 ---------------------------------------------------------------------
def test_h1_passes_on_a_clean_locked_report():
    got = h1(_h1_doc())
    assert got["word"] == "PASS", got["read"]
    assert "253" in got["read"] and "115" in got["read"]


def test_h1_drops_when_the_corpus_run_left_no_report():
    """Catches: a cell that reads an absent run as a clean one."""
    got = h1(None)
    assert got["word"] == "dropped"
    assert "no JSON" in got["read"]


def test_h1_stops_and_names_a_single_mcp_cli_difference():
    diff = {"case": "aliasing", "id": "who-shares", "field": "stdout",
            "mcp": "matches: 2", "cli": "matches: 3"}
    got = h1(_h1_doc(mcp_differences=[diff]))
    assert got["word"] == "STOP"
    assert "aliasing/who-shares" in got["read"]
    assert "matches: 3" in got["read"]


def test_h1_stops_as_instrument_when_compare_cli_was_not_honoured():
    """Catches: reading an ABSENT `mcp_differences` as an empty one. The
    key is present-and-empty on a real `--compare-cli` run and absent
    otherwise, so absent means NOTHING was compared."""
    doc = _h1_doc()
    del doc["mcp_differences"]
    got = h1(doc)
    assert got["word"] == "STOP"
    assert "mcp_differences" in got["read"]
    assert "instrument" in got["read"]


def test_h1_stops_on_a_via_cli_list_with_one_extra_id():
    extra = list(LOCKED_VIA_CLI_IDS) + ["typescript/ts-swallow"]
    got = h1(_h1_doc(via_cli=extra))
    assert got["word"] == "STOP"
    assert "typescript/ts-swallow" in got["read"]


def test_h1_stops_on_a_census_short_by_one_case():
    """Catches: the census clause dropped. 114 cases is a corpus one case
    short of the one the endpoint was written against."""
    got = h1(_h1_doc(cases=114))
    assert got["word"] == "STOP"
    assert "114" in got["read"] and "115" in got["read"]


def test_h1_stops_on_a_failure_an_error_or_an_exit_reason():
    assert h1(_h1_doc(failures=["aliasing/who-shares: exit 1 != 0"]))[
        "word"] == "STOP"
    assert h1(_h1_doc(errors=[{"case": "x", "error": "boom"}]))[
        "word"] == "STOP"
    assert h1(_h1_doc(exit_reason="--require-driver was given and 13 "
                      "case(s) could not run"))["word"] == "STOP"
    assert h1(_h1_doc(skipped=[{"case": "rust/panic",
                                "reason": "no cargo-sensorium"}]))[
        "word"] == "STOP"


def test_h1_stops_as_instrument_on_a_report_that_is_not_via_mcp():
    got = h1(_h1_doc(via="cli"))
    assert got["word"] == "STOP" and "instrument" in got["read"]


def test_h1_dry_relaxes_the_census_and_via_cli_clauses_and_says_so():
    """Catches: a rehearsal on a two-case subset reading as a measurement,
    or the relaxation silently widening to the clauses that still bind."""
    subset = _h1_doc(cases=1, questions=2, via_cli=[])
    assert h1(subset)["word"] == "STOP"
    got = h1(subset, dry=True)
    assert got["word"] == "PASS", got["read"]
    assert "DRY" in got["read"] and "via_cli" in got["read"]
    # ...and nothing else is relaxed.
    assert h1(_h1_doc(cases=1, questions=2, via_cli=[],
                      mcp_differences=[{"case": "c", "id": "q",
                                        "field": "exit", "mcp": 1,
                                        "cli": 0}]), dry=True)["word"] == "STOP"


# -- H2 ---------------------------------------------------------------------
def test_h2_passes_on_ten_passed_none_skipped():
    got = h2(0, 10, 0)
    assert got["word"] == "PASS" and "10" in got["read"]


def test_h2_stops_as_instrument_on_any_skip():
    """A skip means the `conformance` extra is missing, so the cell
    measured nothing -- §1's own reading."""
    got = h2(0, 8, 2)
    assert got["word"] == "STOP" and "instrument" in got["read"]


def test_h2_stops_on_a_non_zero_exit_or_too_few_passed():
    assert h2(1, 9, 0)["word"] == "STOP"
    assert h2(0, 8, 0)["word"] == "STOP"


def test_h2_drops_when_pytest_was_never_parsed():
    assert h2(None, None, None)["word"] == "dropped"


# -- H3 ---------------------------------------------------------------------
def test_h3_passes_on_a_capped_answer():
    got = h3(_capped(), 28_507_987, {"truncated": True, "bytes": 65999})
    assert got["word"] == "PASS", got["read"]
    assert "65536" in got["read"]


def test_h3_does_not_count_the_header_or_the_marker_against_the_bound():
    """Catches: the header line or the cap's own marker counted against
    65536. The header here is long enough that counting it WOULD breach
    the bound -- a 200-byte one would not, and a test that used one could
    not tell the two readings apart -- and the answer must still pass."""
    long_header = "exit 0: " + "the trace answered affirmatively " * 20
    assert len(long_header.encode()) > 41
    got = h3(_capped(long_header), 28_507_987, {"truncated": True})
    assert got["word"] == "PASS", got["read"]
    assert got["detail"]["bytes"] <= e17_cells.CAP_BYTES
    counted = got["detail"]["bytes"] + len(long_header.encode()) + 1
    assert counted > e17_cells.CAP_BYTES, counted


def test_h3_stops_as_instrument_when_the_cli_answer_fits_under_the_cap():
    """Catches: a cap cell that "passes" on a trace small enough that the
    cap never fired -- the cell would have measured nothing."""
    got = h3(_capped(), 4096, {"truncated": True})
    assert got["word"] == "STOP" and "instrument" in got["read"]


def test_h3_stops_when_no_marker_line_is_there():
    text = "exit 0: the trace answered affirmatively\nshort body\n"
    got = h3(text, 28_507_987, {"truncated": True})
    assert got["word"] == "STOP" and "marker" in got["read"]


def test_h3_stops_on_a_header_that_is_not_exit_zero():
    got = h3(_capped("no answer: cancelled"), 28_507_987,
             {"truncated": True})
    assert got["word"] == "STOP" and "header" in got["read"]


def test_h3_stops_when_the_audit_line_does_not_say_truncated():
    got = h3(_capped(), 28_507_987, {"truncated": False})
    assert got["word"] == "STOP" and "truncated" in got["read"]


def test_h3_stops_when_the_head_is_empty():
    """A marker with nothing before it is a cap that kept no head."""
    text = ("exit 0: the trace answered affirmatively\n"
            "[... 9,000 lines (900,000 bytes) omitted; narrow with: "
            "depth, limit, around ...]\ntail line\n")
    got = h3(text, 28_507_987, {"truncated": True})
    assert got["word"] == "STOP" and "head" in got["read"]


def test_h3_drops_on_a_missing_input():
    assert h3(None, 1, {})["word"] == "dropped"
    assert h3("x\ny", None, {})["word"] == "dropped"
    assert h3("x\ny", 1, None)["word"] == "dropped"


# -- H4 ---------------------------------------------------------------------
def test_h4_passes_on_the_gate_holding_both_ways():
    got = h4(**_h4())
    assert got["word"] == "PASS", got["read"]


def test_h4_stops_on_each_clause_in_turn():
    assert h4(**_h4(names_off=list(ELEVEN)))["word"] == "STOP"
    assert h4(**_h4(err_off={"code": -32602,
                             "message": "Unknown tool: nope"}))[
        "word"] == "STOP"
    assert h4(**_h4(err_off={"code": -32602, "message":
                             "Unknown tool: record"},
                    names_on=list(NINE)))["word"] == "STOP"
    assert h4(**_h4(record_header="exit 1: the recorded command failed"))[
        "word"] == "STOP"
    assert h4(**_h4(runs_text="no traces"))["word"] == "STOP"
    assert h4(**_h4(runs_text="20260916-101010-abcdef  exit:0\n"
                              "20260916-101011-abcdee  exit:0"))[
        "word"] == "STOP"
    named = h4(**_h4(exceptions_check=["missing 'dispositions: swallowed 2'"]))
    assert named["word"] == "STOP"
    assert "swallowed 2" in named["read"]


def test_h4_stops_when_record_was_a_tool_without_the_flag():
    """The gate's whole point: `record` must be `-32602 Unknown tool` with
    the flag off."""
    got = h4(**_h4(err_off=None))
    assert got["word"] == "STOP"


def test_h4_drops_on_a_missing_input():
    args = _h4()
    args["names_on"] = None
    assert h4(**args)["word"] == "dropped"


# -- H5 ---------------------------------------------------------------------
def test_h5_passes_when_every_clause_holds():
    got = h5(**_h5())
    assert got["word"] == "PASS", got["read"]
    assert "10 ping" in got["read"]


def test_h5_stops_as_instrument_on_too_few_pings():
    """Catches: `MIN_PINGS` dropped. Three pings over five seconds is a
    client that was not polling, so "every ping answered under a second"
    is a claim about almost nothing."""
    got = h5(**_h5(pings_sent=3))
    assert got["word"] == "STOP"
    assert "instrument" in got["read"] and str(MIN_PINGS) in got["read"]


def test_h5_stops_as_instrument_when_the_group_was_never_alive():
    """Catches: a cancel cell passing by ABSENCE -- a record that never
    spawned has no group to kill, and `killpg` would raise on the first
    look."""
    got = h5(**_h5(alive_before=False))
    assert got["word"] == "STOP" and "instrument" in got["read"]


def test_h5_stops_on_each_clause_in_turn():
    assert h5(**_h5(ping_max=1.4))["word"] == "STOP"
    assert h5(**_h5(group_gone_s=2.6))["word"] == "STOP"
    assert h5(**_h5(group_gone_s=None))["word"] == "STOP"
    assert h5(**_h5(response_seen=True))["word"] == "STOP"
    assert h5(**_h5(runs_after={"answered": True, "traces": 1,
                                "incomplete": 0}))["word"] == "STOP"
    assert h5(**_h5(runs_after={"answered": False, "traces": None,
                                "incomplete": None}))["word"] == "STOP"
    assert h5(**_h5(timeout_is_error=False))["word"] == "STOP"
    assert h5(**_h5(timeout_exit=0))["word"] == "STOP"
    assert h5(**_h5(timeout_answered_s=7.5))["word"] == "STOP"
    assert h5(**_h5(timeout_group_gone_s=6.0))["word"] == "STOP"
    assert h5(**_h5(timeout_header="no answer: cancelled"))["word"] == "STOP"


def test_h5_names_the_headers_exit_and_not_the_wire_field(request):
    """R18: what the cell reads is `CallResult.exit`, parsed out of the
    `no answer: timed out after 3 s (…)` header. The clause says that."""
    got = h5(**_h5(timeout_exit=0))
    assert "the header's exit (`CallResult.exit`) is 0" in got["read"]
    assert "structuredContent" not in got["read"]


def test_h5_stops_when_the_timeout_arm_never_answered():
    """A header the instrument wrote because nothing came back is a STOP,
    not a hole: the arm ran and the server did not answer."""
    got = h5(**_h5(timeout_header=e17_cells.NO_TIMEOUT_RESULT,
                   timeout_answered_s=None))
    assert got["word"] == "STOP"


def test_h5_drops_when_the_cancel_arm_did_not_run():
    assert h5(**_h5(pings_sent=None))["word"] == "dropped"
    assert h5(**_h5(alive_before=None))["word"] == "dropped"
    assert h5(**_h5(timeout_header=None))["word"] == "dropped"


# -- H6 ---------------------------------------------------------------------
def test_h6_passes_on_zero_occurrences_in_the_three_places():
    got = h6(**_h6())
    assert got["word"] == "PASS", got["read"]
    assert "0 occurrence" in got["read"]


def test_h6_stops_on_any_occurrence_in_any_of_the_three_places():
    for key in ("in_texts", "in_jsonl", "in_stderr"):
        counts = dict(_h6()["counts"])
        counts[key] = 1
        got = h6(**_h6(counts=counts))
        assert got["word"] == "STOP", key
        assert key in got["read"] or "occurrence" in got["read"]


def test_h6_stops_as_instrument_on_a_failed_expectation_naming_it():
    """The case's own `expect_absent` rows are what prove the token was at
    the four value sites and was withheld; a failed one means the cell was
    never in a position to count anything."""
    checks = [{"question": "info-counts-the-values-the-rule-took",
               "failures": ["missing 'values redacted: 4'"]},
              {"question": "frame-renders-the-marker-not-the-token",
               "failures": []}]
    got = h6(**_h6(checks=checks))
    assert got["word"] == "STOP"
    assert "instrument" in got["read"]
    assert "info-counts-the-values-the-rule-took" in got["read"]


def test_h6_drops_when_a_count_over_the_result_texts_was_never_taken():
    """Catches: `texts` and `questions` left out of the `unread` guard. An
    absent pair made the first clause `None == None` -- a PASS over two
    holes -- and degraded the audit-lines clause to `jsonl_lines >= 0`,
    which nothing can fail.

    Pre-registered mutant: drop the two new `unread` entries -- caught
    here.
    """
    for key, said in (("texts", "the result texts"),
                      ("questions", "the case's question count")):
        counts = dict(_h6()["counts"])
        counts[key] = None
        got = h6(**_h6(counts=counts))
        assert got["word"] == "dropped", (key, got)
        assert said in got["read"], (key, got["read"])
    # ...and both absent together is still a drop, never `None == None`.
    counts = dict(_h6()["counts"])
    counts["texts"] = counts["questions"] = None
    assert h6(**_h6(counts=counts))["word"] == "dropped"


def test_h6_counts_the_proc_row_apart_from_the_cases_questions():
    """The `/proc` precondition rides in `checks` so a failure reaches the
    STOP-AS-INSTRUMENT sentence, but it is not one of `secret_in_env`'s
    questions: `checks_run` must read 4, not 5."""
    got = h6(**_h6())
    assert got["detail"]["checks_run"] == got["detail"]["counts"]["questions"]
    assert got["detail"]["proc_check"] == "PASS"
    # A run whose `checks` never carried the row says so, rather than
    # reporting a precondition that was never looked at as one that held.
    bare = [c for c in _h6()["checks"]
            if c["question"] != e17_cells.PROC_CHECK]
    assert h6(**_h6(checks=bare))["detail"]["proc_check"] is None


def test_h6_stops_as_instrument_when_the_server_did_not_hold_the_token():
    """The `/proc` row failing is a finding about the MEASUREMENT: a server
    without the token in its environment measured no secrecy."""
    checks = [{"question": e17_cells.PROC_CHECK,
               "failures": ["the entry is not in the server's environ"]}]
    checks += [{"question": f"q{i}", "failures": []} for i in range(4)]
    got = h6(**_h6(checks=checks))
    assert got["word"] == "STOP"
    assert "instrument" in got["read"]
    assert e17_cells.PROC_CHECK in got["read"]


def test_h6_drops_when_the_audit_file_was_not_read():
    """Catches: a missing `mcp.jsonl` counted as 0 lines and 0
    occurrences -- a hole reported as the cleanest possible pass."""
    counts = dict(_h6()["counts"])
    counts["jsonl_lines"] = counts["in_jsonl"] = None
    got = h6(**_h6(counts=counts))
    assert got["word"] == "dropped"
    assert "mcp.jsonl" in got["read"]


def test_h6_stops_on_too_few_audit_lines_or_result_texts():
    counts = dict(_h6()["counts"])
    counts["jsonl_lines"] = 3
    assert h6(**_h6(counts=counts))["word"] == "STOP"
    counts = dict(_h6()["counts"])
    counts["texts"] = 3
    assert h6(**_h6(counts=counts))["word"] == "STOP"


def test_h6_stops_when_the_stderr_transcript_is_empty():
    counts = dict(_h6()["counts"])
    counts["stderr_bytes"] = 0
    assert h6(**_h6(counts=counts))["word"] == "STOP"


def test_h6b_stops_when_the_audit_kept_the_pattern():
    got = h6(**_h6(h6b={"pattern": "sk-e17-plainly-here", "in_jsonl": 1}))
    assert got["word"] == "STOP"
    assert "H6b" in got["read"]


def test_h6_drops_on_a_missing_input():
    assert h6(**_h6(checks=None))["word"] == "dropped"
    assert h6(**_h6(counts=None))["word"] == "dropped"
    assert h6(**_h6(h6b=None))["word"] == "dropped"


# -- H7 and latency ---------------------------------------------------------
def _h7(**over) -> dict:
    doc = {"tools_used": ["record", "exceptions", "frame", "runs"],
           "sensorium_tool_calls": 11,
           "recorded_command": ["main.py"], "named_frame": True,
           "model": "claude-opus-5", "claude_version": "2.1.258",
           "handshake": "handshake discover 2026-07-28"}
    doc.update(over)
    return doc


def test_h7_is_reported_either_way_and_names_what_was_read():
    got = h7(_h7())
    assert got["word"] == "reported"
    assert "4 sensorium tool" in got["read"]
    assert "11 sensorium call(s)" in got["read"]
    assert got["detail"]["sensorium_tool_calls"] == 11
    assert "main.py" in got["read"]
    assert "load_all" in got["read"]
    assert "handshake discover 2026-07-28" in got["read"]
    assert "2.1.258" in got["read"]


def test_h7_is_still_reported_when_the_model_did_something_else():
    got = h7(_h7(tools_used=["runs"], named_frame=False))
    assert got["word"] == "reported"
    assert "fewer than 3" in got["read"]
    assert "is NOT" in got["read"]


def test_h7_says_so_when_the_call_count_was_not_recorded():
    """`sensorium_tool_calls` is R17's addition to `h7.json`. Absent is
    said out loud -- never a zero, and never silence that reads as one."""
    doc = _h7()
    del doc["sensorium_tool_calls"]
    got = h7(doc)
    assert got["word"] == "reported"
    assert "a call count that was not recorded" in got["read"]
    assert got["detail"]["sensorium_tool_calls"] is None


def test_h7_drops_with_the_controllers_reason_when_the_file_is_absent():
    got = h7(None)
    assert got["word"] == "dropped"
    assert got["read"] == "H7 not run by the controller"


def test_latency_is_measured_and_reports_the_ratio():
    got = latency(3812.0, 3720.0, 41.2)
    assert got["word"] == "measured"
    assert "3812" in got["read"] and "1.02" in got["read"]
    assert "41.2" in got["read"]


def test_latency_drops_when_a_median_was_never_taken():
    assert latency(None, 3720.0, 41.2)["word"] == "dropped"
    assert latency(3812.0, None, 41.2)["word"] == "dropped"
    assert latency(3812.0, 3720.0, None)["word"] == "dropped"


# -- the part's own word ----------------------------------------------------
def _cells(**over) -> dict:
    cells = {c: {"word": "PASS", "read": "", "detail": {}}
             for c in ("H1", "H2", "H3", "H4", "H5", "H6")}
    cells["H7"] = {"word": "reported", "read": "", "detail": {}}
    cells["latency"] = {"word": "measured", "read": "", "detail": {}}
    for name, word in over.items():
        cells[name] = {"word": word, "read": "", "detail": {}}
    return cells


def test_part_word_is_done_when_h1_to_h6_all_pass():
    assert part_word(_cells()) == "DONE"


def test_part_word_is_done_with_stop_on_any_stop_among_h1_to_h6():
    """Catches: a STOP let through as DONE -- the one verdict this
    instrument must never be able to publish."""
    for cell in ("H1", "H2", "H3", "H4", "H5", "H6"):
        assert part_word(_cells(**{cell: "STOP"})) == "DONE-WITH-STOP", cell


def test_part_word_is_incomplete_on_a_drop_with_no_stop():
    assert part_word(_cells(H4="dropped")) == "INCOMPLETE"
    # A STOP outranks a drop: a measured failure is a finding, a hole is
    # not, and the part word has to carry the finding.
    assert part_word(_cells(H4="dropped", H5="STOP")) == "DONE-WITH-STOP"


def test_part_word_is_incomplete_when_a_gating_cell_was_never_written():
    assert part_word({}) == "INCOMPLETE"


def test_h7_and_latency_never_gate_the_part_word():
    assert part_word(_cells(H7="dropped")) == "DONE"
    assert part_word(_cells(latency="dropped")) == "DONE"
    assert part_word(_cells(H7="STOP")) == "DONE"


def test_every_cell_returns_the_same_three_keys():
    """Catches: a cell that answers in a shape the assembler cannot
    render -- every one of them is read by the same table builder."""
    every = (h1(_h1_doc()), h1(None), h2(0, 10, 0),
             h3(_capped(), 28_507_987, {"truncated": True}),
             h4(**_h4()), h5(**_h5()), h6(**_h6()), h7(_h7()), h7(None),
             latency(1.0, 1.0, 1.0))
    for got in every:
        assert set(got) == {"word", "read", "detail"}, got
        assert isinstance(got["read"], str) and got["read"]
        assert got["word"] in ("PASS", "STOP", "dropped", "reported",
                               "measured")


@pytest.mark.parametrize("word", ["PASS", "STOP"])
def test_every_rule_names_both_words(word):
    for cell, clauses in RULES.items():
        assert clauses[word].strip(), (cell, word)


# -- the one reader that lives in the instrument, not in the cells ---------
def test_pytest_counts_reads_the_skip_the_summary_line_carries():
    """Catches the defect the first rehearsal could not: a summary parser
    matching a FRAGMENT reads `14 passed, 1 skipped in 0.03s` as `14
    passed` alone, the skip count comes back absent, and H2's
    STOP-AS-INSTRUMENT on a skipped conformance run can never fire -- a
    green cell over an oracle that did not run. Nothing skipped during the
    rehearsal, so only a test can hold this.

    Pre-registered mutant: `SUMMARY` narrowed back to a fragment that ends
    at `passed|failed|error` -- caught here.
    """
    import e17                                              # noqa: PLC0415

    assert e17.pytest_counts("10 passed in 2.31s") == {"passed": 10,
                                                       "skipped": 0}
    assert e17.pytest_counts("14 passed, 1 skipped in 0.03s") == {
        "passed": 14, "skipped": 1}
    assert e17.pytest_counts("2 failed, 12 passed in 1s") == {"passed": 12,
                                                              "skipped": 0}
    # A skip REASON that reads like a summary must not be taken for one:
    # the LAST matching line is the summary, and it is the one read.
    assert e17.pytest_counts("SKIPPED [1] x.py:9: 3 skipped elsewhere\n"
                             "9 passed, 1 skipped in 2s") == {"passed": 9,
                                                              "skipped": 1}
    # ...and no summary at all is two `None`s, never two zeros.
    assert e17.pytest_counts("no tests ran in 0.01s") == {"passed": None,
                                                          "skipped": None}
    assert h2(0, **e17.pytest_counts("14 passed, 1 skipped in 0.03s"))[
        "word"] == "STOP"
    assert h2(5, **e17.pytest_counts("no tests ran in 0.01s"))[
        "word"] == "dropped"
