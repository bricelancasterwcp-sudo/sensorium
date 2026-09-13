"""E15's ten cells: §1's rules, read over a synthetic `raw`.

The sibling of `tests/test_acceptance_e15.py` -- which gives the READER text
and asserts what it parsed -- and of `tests/test_acceptance_e15_assemble.py`,
which calls the assembler. The three were one file until it crossed
`tests/test_ceiling.py`'s 800 lines, and the seam is the material's: nothing
here opens a transcript, and nothing there decides a word.

The `raw` is three rows: one MATCH on a deterministic row, one DIVERGED on a
row the survey predicted nondeterministic (a READING), and one DIVERGED on a
deterministic row (a FINDING). Every test states the failure it would catch,
and each one makes §1's rule for that endpoint fail on its own.

`raw_of`, `three_rows` and `SURVEY_3` are imported by the assembler's tests,
so this module is also where that fixture lives.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"
sys.path.insert(0, str(ACCEPT))

import e15_read as rd                                             # noqa: E402
import e15_report as rep                                          # noqa: E402
from test_acceptance_e15 import DIVERGED_TASKS                    # noqa: E402


# -- the cells --------------------------------------------------------------

SURVEY_3 = [
    {"n": 1, "test_file": "src/a.test.ts", "klass": "deterministic",
     "reason": "—", "focus": "a.ts:one", "resolver_matched": 1},
    {"n": 2, "test_file": "src/b.test.ts", "klass": "nondeterministic",
     "reason": "`waitFor` polls on a real timer", "focus": "b.ts:two",
     "resolver_matched": 1},
    {"n": 3, "test_file": "src/c.test.ts", "klass": "deterministic",
     "reason": "—", "focus": "c.ts:three", "resolver_matched": 2},
]

U = 3
HARNESS_EXIT = "0 (waited)"
ENV_OK = ("env: unchanged (110 variables compared; not compared: OLDPWD)  "
          "the recorder's own, also not compared: SENSORIUM_TIER")


def parsed(verdict="MATCH", licence="granted", **over) -> dict:
    """One row's parse, in the shape `parse_refocus` returns."""
    out = {
        "refocus_of": "orig", "driver_cmd": "sensorium ts run …",
        "cwd": "<root>", "focus": ["a.ts:one"], "window": "-",
        "source_line": "source: unchanged (2 file(s) compared by content)",
        "source_status": "unchanged",
        "env_line": ENV_OK, "env_status": "unchanged",
        "exit_line": f"exit: rerun {HARNESS_EXIT}   original {HARNESS_EXIT}",
        "exit_rerun": HARNESS_EXIT, "exit_original": HARNESS_EXIT,
        "exit_equal": True,
        "pair": {"run": "new", "invocation": "inv", "siblings": U - 1},
        "trace": "<store>/traces/new.db",
        "verdict": verdict, "verdict_line": f"refocus verdict: {verdict} …",
        "licence": licence,
        "licence_line": "licence: verified against orig …",
        "licence_points": ["identical call shape across 1 compared "
                           "fingerprint(s), holding 0 causal event(s)",
                           "2 source file(s) unchanged by content"]
        if licence == "granted" else [],
        "withheld_reasons": [] if licence == "granted" else ["1 source "
                                                            "file(s) CHANGED"],
        "unverifiable": list(rd.UNVERIFIABLE), "unverifiable_header": "checks…",
        "refusal": None, "refusal_run": None,
        "refused_after_rerun": None, "lookup_refusal": None,
        "diverged_step": None, "divergent_line": None,
        "harness_duration_s": 24.0,
    }
    out.update(over)
    return out


def row(n: int, klass: str, p: dict, exit_code: int = 0) -> dict:
    survey_row = next(r for r in SURVEY_3 if r["n"] == n)
    return {
        "n": n, "test_file": survey_row["test_file"], "klass": klass,
        "focus": survey_row["focus"], "original": f"orig{n}",
        "command": f"sensorium refocus orig{n} --focus {survey_row['focus']}",
        "transcript": f"transcripts/{n}-x.txt",
        "exit": exit_code, "timed_out": False,
        "wall_s": 60.0, "harness_duration_s": p["harness_duration_s"],
        "wall_minus_harness_s": round(60.0 - (p["harness_duration_s"] or 0), 3),
        "spool_bytes": 400_000_000, "trace_bytes": 1_000_000,
        "parsed": p,
    }


def raw_of(rows, **over) -> dict:
    out = {
        "preflight": {"dry_run": False, "driver_version": "0.14.0",
                      "lens": "a lens", "node": "v24.16.0",
                      "vitest": "4.1.9"},
        "originals": {"U": U, "harness_exit": HARNESS_EXIT,
                      "invocation": "inv0", "exit": 0, "wall_s": 40.0,
                      "harness_duration_s": 24.0,
                      "spool_bytes": 400_000_000, "trace_bytes": 3_000_000},
        "loop": {"rows": rows, "n": len(rows)},
        "controls": {
            "B": {"ran": True, "exit": 1, "row": 2,
                  "test_file": "src/b.test.ts",
                  "restored": True, "sha_equal": True,
                  "parsed": parsed(verdict="DIVERGED", licence="WITHHELD",
                                   source_line="source: 1 file(s) CHANGED "
                                               "since the original run: "
                                               "src/b.test.ts",
                                   source_status="CHANGED",
                                   withheld_reasons=[
                                       "1 source file(s) CHANGED since the "
                                       "original run: src/b.test.ts"])},
            "C": {"ran": True, "exit": 2, "row": 3,
                  "traces_before": 4, "traces_after": 4,
                  "parsed": rd.parse_refocus(
                      "error: cannot refocus orig3: --window is not available "
                      "for a TypeScript trace (the recorder has no "
                      "per-activation gate); nothing was re-run\n")},
        },
        "fences": {"checks": [
            {"name": "corpus", "command": "corpus/run_corpus.py", "exit": 0,
             "wall_s": 100.0},
            {"name": "pytest", "command": "pytest -q", "exit": 0,
             "wall_s": 200.0}],
            "needle": {"searched": 3, "hits": []},
            "e_fences": {"E-legacy": {"value": 2, "n": 2,
                                      "diff_stat_lines": []},
                         "E-branch": {"value": 1, "n": 1}}},
        "reads": {"reads": [
            {"label": "Row 1", "row": 1, "kind": "watch",
             "command": "watch new1 --at one --expr 'x == 1'",
             "predicted_class": "SATISFIED", "predicted_exit": 0,
             "exit": 0, "parsed": {"verdict": "SATISFIED"}},
            {"label": "Row 3", "row": 3, "kind": "flow",
             "command": "flow new3 --value 0.4",
             "predicted_class": "NOT FOUND", "predicted_exit": 1,
             "exit": 1, "parsed": {"verdict": "NOT FOUND"}}]},
    }
    out.update(over)
    return out


def three_rows() -> list[dict]:
    """One MATCH on a deterministic row, one DIVERGED on the row the survey
    predicted nondeterministic (a READING), one DIVERGED on a deterministic
    row (a FINDING)."""
    return [
        row(1, "deterministic", parsed()),
        row(2, "nondeterministic",
            parsed(verdict="DIVERGED", licence="WITHHELD",
                   diverged_step=4,
                   divergent_line="tasks: DIVERGED -- … at causal step 4: …"),
            exit_code=1),
        row(3, "deterministic",
            parsed(verdict="DIVERGED", licence="WITHHELD",
                   diverged_step=7,
                   divergent_line="tasks: DIVERGED -- … at causal step 7: …"),
            exit_code=1),
    ]


def cells_of(rows=None, **over) -> dict:
    return rep.cells(raw_of(three_rows() if rows is None else rows, **over),
                     SURVEY_3)


def test_cells_publishes_all_ten_endpoints_in_the_records_shape():
    """Catches: a cell that is not a cell. Every endpoint is `{value, n,
    dropped, holds, evidence}` -- `lens.stamp` adds the label at assembly
    time -- so a block missing a key would be stamped and published as a
    measurement nobody could read as one."""
    got = cells_of()
    assert list(got) == [f"H{n}" for n in range(1, 11)]
    for name, c in got.items():
        assert set(c) >= {"value", "n", "dropped", "holds", "evidence"}, name
        assert "lens" not in c, name          # the assembler stamps it
        assert c["evidence"]["word"] in ("PASS", "STOP", "finding",
                                         "reported"), name


def test_H1_counts_pre_rerun_refusals_and_holds_at_zero():
    """Catches: an H1 that counts something else. §1 gates it at `0 of 31`
    refusals, and a pre-rerun refusal is the one class the loop can produce
    without re-running anything."""
    got = cells_of()["H1"]
    assert got["value"] == 0 and got["n"] == 3
    assert got["holds"] is True and got["evidence"]["word"] == "PASS"
    refused = three_rows()
    refused[1]["parsed"]["refusal"] = "run orig2 records no harness command"
    refused[1]["exit"] = 2
    bad = rep.cells(raw_of(refused), SURVEY_3)["H1"]
    assert bad["value"] == 1 and bad["holds"] is False
    assert bad["evidence"]["word"] == "STOP"
    assert "src/b.test.ts" in json.dumps(bad["evidence"]["refusals"])


def test_H2_names_the_row_whose_harness_exit_differs_and_calls_it_a_finding():
    """Catches: an H2 that STOPs. §1 is explicit -- a harness that ended
    differently is a FINDING carrying the exit, not a STOP -- and the row has
    to be named or the finding is a count."""
    ok = cells_of()["H2"]
    assert ok["value"] == 3 and ok["n"] == 3 and ok["holds"] is True
    rows = three_rows()
    rows[2]["parsed"]["exit_rerun"] = "1 (waited)"
    got = rep.cells(raw_of(rows), SURVEY_3)["H2"]
    assert got["value"] == 2 and got["n"] == 3 and got["holds"] is False
    assert got["evidence"]["word"] == "finding"
    finding = got["evidence"]["findings"][0]
    assert finding["n"] == 3 and finding["exit_rerun"] == "1 (waited)"
    assert finding["expected"] == HARNESS_EXIT


def test_H3_STOPs_on_a_refusal_after_the_rerun_on_the_lookup():
    """Catches: an H3 that folds a pairing refusal into H4's verdict count.
    §1 makes a REFUSED after the re-run on the LOOKUP a STOP -- the
    instrument or the pairing, not the subject."""
    ok = cells_of()["H3"]
    assert ok["value"] == 3 and ok["holds"] is True
    rows = three_rows()
    rows[0]["parsed"].update(
        verdict="REFUSED", licence=None,
        refused_after_rerun="the re-run produced 3 trace(s) linked to orig1 "
                            "and none ran test file src/a.test.ts",
        lookup_refusal=True)
    rows[0]["exit"] = 3
    got = rep.cells(raw_of(rows), SURVEY_3)["H3"]
    assert got["value"] == 2 and got["holds"] is False
    assert got["evidence"]["word"] == "STOP"
    assert got["evidence"]["lookup_refusals"][0]["n"] == 1


def test_H3_reads_the_linked_count_off_the_sibling_count():
    """Catches: an H3 that checks only the candidate. §1 asks two things --
    exactly one candidate AND a linked count equal to `U` -- and the linked
    count is `siblings + 1`, the pair being one of them."""
    rows = three_rows()
    rows[1]["parsed"]["pair"]["siblings"] = 0
    got = rep.cells(raw_of(rows), SURVEY_3)["H3"]
    assert got["holds"] is False
    assert got["evidence"]["linked_equal_to_U"] == 2
    assert got["evidence"]["linked_findings"][0]["linked"] == 1
    assert got["evidence"]["linked_findings"][0]["U"] == U


def test_H4_calls_an_unexpected_DIVERGED_a_finding_naming_the_row_and_step():
    """Catches: an H4 that reads an unexpected DIVERGED as a reading. §1
    separates them by the survey's CLASS: on a deterministic row a DIVERGED
    is a finding recorded with the divergent event; on a nondeterministic one
    the verdict is a reading and gates nothing."""
    got = cells_of()["H4"]
    assert got["value"] == 1 and got["n"] == 2      # two deterministic rows
    assert got["holds"] is False
    assert got["evidence"]["word"] == "finding"
    findings = got["evidence"]["findings"]
    assert [f["n"] for f in findings] == [3]
    assert "at causal step 7:" in findings[0]["divergent_line"]
    readings = got["evidence"]["readings"]
    assert [r["n"] for r in readings] == [2]
    assert readings[0]["verdict"] == "DIVERGED"
    assert readings[0]["klass"] == "nondeterministic"


def test_H4_STOPs_on_a_comparator_REFUSED_and_not_on_a_lookup_one():
    """Catches: an H4 that treats every REFUSED alike. §1 gives the lookup
    refusal to H3 and the comparator's to H4, and the two have different
    words at different endpoints."""
    rows = three_rows()
    rows[0]["parsed"].update(verdict="REFUSED", licence=None,
                             refused_after_rerun="it could NOT be verified",
                             lookup_refusal=False)
    rows[0]["exit"] = 3
    got = rep.cells(raw_of(rows), SURVEY_3)["H4"]
    assert got["holds"] is False and got["evidence"]["word"] == "STOP"
    assert got["evidence"]["comparator_refusals"][0]["n"] == 1


def test_H4_holds_when_every_deterministic_row_matched():
    """Catches: an H4 whose gate can never pass -- the population is the
    DETERMINISTIC rows, and a nondeterministic DIVERGED must not count
    against it."""
    rows = three_rows()
    rows[2] = row(3, "deterministic", parsed())
    got = rep.cells(raw_of(rows), SURVEY_3)["H4"]
    assert got["value"] == 2 and got["n"] == 2 and got["holds"] is True
    assert got["evidence"]["word"] == "PASS"


def test_H5_sums_the_licence_and_gates_the_claim_count_at_zero():
    """Catches: an H5 that sums an unverifiable check into a verified total.
    Its own clause is gated at 0 licence lines claiming one, which is the R7
    bug class -- a check that could not run, reported as one that passed."""
    got = cells_of()["H5"]
    sums = got["evidence"]["sums"]
    assert sums["source_verified"] == 3 and sums["env_verified"] == 3
    assert sums["recorder_set_named"] == 3
    assert sums["unverifiable_output"] == 3
    assert sums["unverifiable_children"] == 3
    assert sums["unverifiable_threads"] == 3
    assert sums["harness_exit_equal"] == 3
    assert sums["claims_an_unverifiable_check"] == 0
    assert sums["granted_on_expected_granted"] == "1 of 1"
    assert got["evidence"]["word"] == "PASS" and got["holds"] is True

    rows = three_rows()
    rows[0]["parsed"]["licence_points"].append(
        "no thread started besides the main one, and none left running")
    bad = rep.cells(raw_of(rows), SURVEY_3)["H5"]
    assert bad["evidence"]["sums"]["claims_an_unverifiable_check"] == 1
    assert bad["holds"] is False and bad["evidence"]["word"] == "STOP"
    assert "thread" in json.dumps(bad["evidence"]["claims"])


def test_H5_counts_harness_set_one_only_where_the_line_names_it():
    """Catches: a clause that fires on every row. §1 asks for harness set 1's
    count WHERE IT DIFFERS -- a row whose env line never names the set is not
    a row missing the count."""
    rows = three_rows()
    rows[0]["parsed"]["env_line"] = (
        "env: unchanged outside harness set 1 (109 variables compared; not "
        "compared: OLDPWD; 2 harness variable(s) differ: VITEST_POOL_ID, "
        "VITEST_WORKER_ID)  the recorder's own, also not compared: "
        "SENSORIUM_TIER")
    got = rep.cells(raw_of(rows), SURVEY_3)["H5"]
    assert got["evidence"]["sums"]["harness_set_named"] == 1
    assert got["evidence"]["sums"]["harness_set_counted"] == 1
    assert got["holds"] is True

    rows[0]["parsed"]["env_line"] = (
        "env: unchanged outside harness set 1 (109 variables compared)  "
        "the recorder's own, also not compared: SENSORIUM_TIER")
    bad = rep.cells(raw_of(rows), SURVEY_3)["H5"]
    assert bad["evidence"]["sums"]["harness_set_counted"] == 0
    assert bad["holds"] is False


def test_H6_compares_both_halves_of_each_prediction():
    """Catches: an H6 that compares the verdict class and ignores the exit,
    which §1 names as two halves of one prediction."""
    got = cells_of()["H6"]
    assert got["value"] == 2 and got["n"] == 2 and got["holds"] is True
    raw = raw_of(three_rows())
    raw["reads"]["reads"][1]["exit"] = 0
    bad = rep.cells(raw, SURVEY_3)["H6"]
    assert bad["value"] == 1 and bad["holds"] is False
    assert bad["evidence"]["word"] == "STOP"
    assert bad["evidence"]["findings"][0]["exit"] == 0
    assert bad["evidence"]["findings"][0]["predicted_exit"] == 1


def test_H7_reads_control_B_as_one_of_one():
    """Catches: an H7 that accepts a WITHHELD licence without the source
    reason. §1 predicts `source: CHANGED` NAMING THE FILE and a WITHHELD
    licence carrying that reason, whatever the verdict."""
    got = cells_of()["H7"]
    assert got["value"] == 1 and got["n"] == 1 and got["holds"] is True
    claims = got["evidence"]["claims"]
    assert claims["`source: CHANGED` names the edited file"] is True
    assert claims["`licence: WITHHELD`"] is True
    assert claims["a withheld reason names the source change"] is True
    assert got["evidence"]["lens_restored"] is True

    raw = raw_of(three_rows())
    raw["controls"]["B"]["parsed"]["licence"] = "granted"
    bad = rep.cells(raw, SURVEY_3)["H7"]
    assert bad["value"] == 0 and bad["holds"] is False


def test_H8_reads_control_C_as_exit_two_the_sentence_and_an_unmoved_store():
    """Catches: an H8 that checks the exit and not the store. "Nothing was
    re-run" is a claim about the world, and the trace count before and after
    is what tests it."""
    got = cells_of()["H8"]
    assert got["value"] == 1 and got["n"] == 1 and got["holds"] is True
    assert got["evidence"]["claims"]["the trace count is unchanged"] is True
    raw = raw_of(three_rows())
    raw["controls"]["C"]["traces_after"] = 5
    bad = rep.cells(raw, SURVEY_3)["H8"]
    assert bad["value"] == 0 and bad["holds"] is False
    assert bad["evidence"]["word"] == "STOP"


def test_H9_is_reported_and_never_gates():
    """Catches: a cost cell with a gate. §1 says reported, no gate -- and the
    three walls are named as what they are, the last of them `wall minus
    harness` and never "the conversion"."""
    got = cells_of()["H9"]
    assert got["holds"] is None and got["evidence"]["word"] == "reported"
    per = got["evidence"]["per_refocus"]
    assert len(per) == 3
    assert per[0]["wall_s"] == 60.0
    assert per[0]["harness_duration_s"] == 24.0
    assert per[0]["wall_minus_harness_s"] == 36.0
    totals = got["evidence"]["totals"]
    assert totals["wall_s"] == 180.0
    assert totals["spool_bytes"] == 1_200_000_000
    assert "conversion" not in json.dumps(got["evidence"]).lower()


def test_H10_holds_only_when_every_fence_exits_zero_and_names_no_path():
    """Catches: an H10 that reports the suites and forgets the fence's own
    report. §1 requires `e_fences.py`'s report to list NO fenced path: this
    slice touches none."""
    got = cells_of()["H10"]
    assert got["holds"] is True and got["evidence"]["word"] == "PASS"
    raw = raw_of(three_rows())
    raw["fences"]["e_fences"]["E-legacy"]["diff_stat_lines"] = [
        " rust/src/lib.rs | 2 +-"]
    bad = rep.cells(raw, SURVEY_3)["H10"]
    assert bad["holds"] is False and bad["evidence"]["word"] == "STOP"
    raw2 = raw_of(three_rows())
    raw2["fences"]["checks"][1]["exit"] = 1
    worse = rep.cells(raw2, SURVEY_3)["H10"]
    assert worse["holds"] is False
    assert worse["evidence"]["findings"][0]["name"] == "pytest"


def test_a_phase_that_did_not_run_is_null_and_named_never_zero():
    """Catches: the record's none-versus-zero rule broken. A cell whose phase
    never ran must carry `value: null` with a reason, not a `0` that reads as
    measured-and-zero."""
    raw = raw_of(three_rows())
    raw["loop"] = None
    raw["fences"] = None
    got = rep.cells(raw, SURVEY_3)
    for name in ("H1", "H2", "H3", "H4", "H5", "H9"):
        assert got[name]["value"] is None, name
        assert got[name]["dropped"], name
        assert got[name]["holds"] is None, name
    assert got["H10"]["value"] is None and got["H10"]["dropped"]


# -- what a DIVERGED verdict does to the licence ----------------------------


DIVERGED_WORLD = DIVERGED_TASKS.replace(
    "checks that could not run on this pair",
    "differences in the world between the two runs, any of which may be why:\n"
    "  - 1 source file(s) CHANGED between the two runs (b.test.ts), so the "
    "rerun executed different code than the recording did\n"
    "checks that could not run on this pair", 1)


def test_parse_refocus_reads_the_world_caveats_a_DIVERGED_prints():
    """Catches: a reader that looks for the source finding under a licence a
    DIVERGED never prints. `report` prints no `licence:` line at all on a
    divergence -- the licence belongs to a MATCH -- and the world findings go
    under `differences in the world between the two runs`. H7's control B is
    predicted to DIVERGE, so where the reason lands is exactly what has to be
    readable."""
    got = rd.parse_refocus(DIVERGED_WORLD)
    assert got["verdict"] == "DIVERGED"
    assert got["licence"] is None and got["withheld_reasons"] == []
    assert len(got["world_caveats"]) == 1
    assert got["world_caveats"][0].startswith("1 source file(s) CHANGED")
    # …and the unverifiable block below it is still its own list.
    assert got["unverifiable"] == list(rd.UNVERIFIABLE)


def test_H7_publishes_the_world_caveats_beside_the_claims_it_does_not_read():
    """Catches: an H7 that quietly accepts a world caveat as the withheld
    reason §1 asks for. §1's words are `licence: WITHHELD` WITH that reason;
    a caveat printed somewhere else is evidence for §3 and never the claim."""
    raw = raw_of(three_rows())
    raw["controls"]["B"]["parsed"] = rd.parse_refocus(DIVERGED_WORLD)
    raw["controls"]["B"]["test_file"] = "src/b.test.ts"
    got = rep.cells(raw, SURVEY_3)["H7"]
    assert got["holds"] is False and got["value"] == 0
    assert got["evidence"]["claims"]["`licence: WITHHELD`"] is False
    assert got["evidence"]["licence_is_absent_on_a_diverged_verdict"] is True
    assert got["evidence"]["world_caveats"][0].startswith("1 source file(s)")


def test_H8_carries_the_form_section_one_literally_spells(tmp_path):
    """Catches: an instrument that silently ran a different command than §1
    wrote. `--focus` is required by `sensorium refocus`, so §1's shorthand is
    refused by argparse before design §2.3's refusal 1 can run; the literal
    form is run too and its answer is published beside the endpoint's."""
    raw = raw_of(three_rows())
    raw["controls"]["C"]["as_written"] = {
        "command": "sensorium refocus orig3 --window 1", "exit": 2,
        "stderr": "sensorium refocus: error: the following arguments are "
                  "required: --focus",
        "parsed": rd.parse_refocus("usage: sensorium refocus …\n")}
    got = rep.cells(raw, SURVEY_3)["H8"]
    assert got["holds"] is True
    assert got["evidence"]["as_written"]["exit"] == 2
    assert "required" in got["evidence"]["as_written"]["stderr"]
    assert "`--focus` is required" in got["evidence"]["focus_added_because"]


def test_a_row_that_refused_before_the_rerun_is_dropped_by_name_not_scored():
    """Catches: one fact reported as four failures. A pre-rerun refusal ran no
    suite, so that row has no harness exit, no candidate, no verdict and no
    licence -- H1 counts it and gates at 0, and H2-H5 drop it BY NAME rather
    than scoring it as a re-run that ended differently, a pair that was not
    found and a verdict that was not MATCH."""
    rows = three_rows()
    rows[1]["parsed"] = parsed(verdict=None, licence=None,
                               refusal="it ran 2 test files in one container",
                               exit_rerun=None, exit_original=None,
                               exit_equal=None)
    rows[1]["exit"] = 2
    got = rep.cells(raw_of(rows), SURVEY_3)
    assert got["H1"]["value"] == 1 and got["H1"]["holds"] is False
    for name in ("H2", "H3", "H4", "H5"):
        assert got[name]["dropped"], name
        assert "refused before the re-run" in got[name]["dropped"][0], name
        assert "src/b.test.ts" in got[name]["dropped"][0], name
    # …and the two rows that DID run are still read: H2 scores 2 of 2.
    assert got["H2"]["value"] == 2 and got["H2"]["n"] == 2
    assert got["H2"]["holds"] is True
