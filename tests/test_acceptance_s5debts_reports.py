"""This slice's OTHER instruments: H8′'s readers, the census comparer, E13,
E14 and the assembler.

The parser half -- `rows_of2`, the committed transcripts, `call_line_of` and
§1.1's hash preflight -- is `tests/test_acceptance_e12p.py`, and this file is
its sibling rather than its continuation: the two were one file until it
crossed `tests/test_ceiling.py`'s 800 lines. What lives here is everything
that reads an ARTEFACT somebody else produced -- `e12p.sh`'s out directory,
`census_deferred.mjs`'s JSON, the corpus runner's exits, one instrument's
cell -- as opposed to a transcript rung 4 already committed.

Two house rules are what most of these tests are about:

* **unmeasured is null and named.** A clause whose input was never written is
  OMITTED from `claims`, so `n` counts only what was read and `dropped` names
  the file. A clause computed over a missing file would score False and be
  COUNTED, and the cell would then say both "not measured" and "did not hold"
  about one clause.
* **a refusal is tested by calling the thing that refuses.** The assembler's
  provenance check, its box-path refusal and its exit statuses live in
  `assemble_s5debts.main`, so the tests call `main`.

Every test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"
sys.path.insert(0, str(ACCEPT))

import e12p_h8 as h8                                              # noqa: E402
import e12p_pre as e12pre                                         # noqa: E402
import e12p_report as e12p                                        # noqa: E402
import e13_report                                                 # noqa: E402
import e14_report                                                 # noqa: E402
import assemble_s5debts as assembler                              # noqa: E402

#: The committed transcripts of rung 4's thirteen reads, and the two records
#: this slice's instruments read. Spelled here too, so each test file stands
#: on its own rather than importing its sibling's constants.
REAL = (REPO / "docs" / "superpowers" / "acceptance"
        / "2026-09-11-sensorium-s5-rung4-focus-reads")
RUNG4 = (REPO / "docs" / "superpowers" / "acceptance"
         / "2026-09-11-sensorium-s5-rung4-focus.md")
CENSUS = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-12-sensorium-s5-rung4-debts-census.md")


def read(name: str) -> str:
    return (REAL / name).read_text(encoding="utf-8")


def store() -> Path:
    """The rung-4 store copy, named by the operator.

    A committed file of this slice carries no box path (the record's §2 rule),
    so the copy's location is `E12P_STORE`'s. Skipping BY NAME rather than
    passing silently is the rule: a skip that reads as a pass is a green suite
    that checked nothing.
    """
    where = os.environ.get("E12P_STORE")
    if not where:
        pytest.skip("E12P_STORE unset: the rung-4 store copy is not on this box")
    return Path(where)


# -- H8′'s readers, and the census comparer --------------------------------


def test_delta_names_reads_one_delta_off_a_bracketed_inspect_text():
    """Catches: a `split(", ")` delta reader. The `while` head row binds ONE
    name and prints five commas inside the match array; a naive split reads
    six deltas off it and clause 4's comparison then fails on a row that is
    exactly what the hand count predicted."""
    (row,) = e12p.rows_of2(
        "  e14 LINE    parseDiceGroups L72  "
        "m=[ '1d20', '1', '20', index: 0, input: '1d20', groups: undefined ]")

    assert h8.delta_names(row) == ["m"]


def test_delta_names_reads_two_deltas_and_drops_unbound_and_labels():
    """The other direction: a row that really does bind two names, and a row
    whose tail is `unbound:` or `flow`'s `[local x]` label -- neither of
    which is a delta."""
    (two,) = e12p.rows_of2(
        "  e378 LINE    buildDiceQueueEntry L202  "
        "dice=[ { sides: 20, value: 17 } ], skippedCount=0")
    (dropped,) = e12p.rows_of2(
        "  e19 LINE    parseDiceGroups L72  m=null  unbound:count,sides")
    (labelled,) = e12p.rows_of2(
        "  e16 LINE    parseDiceGroups L74  sides=20   [local sides]")

    assert h8.delta_names(two) == ["dice", "skippedCount"]
    assert h8.delta_names(dropped) == ["m"] and dropped["unbound"] == [
        "count", "sides"]
    assert h8.delta_names(labelled) == ["sides"]


def test_clause_four_holds_on_rung_fours_own_frame_transcript():
    """The control for H8′'s hardest clause: the nine rows of the COMMITTED
    frame transcript already are the hand count's nine rows, cell for cell.
    A reader that could not read them would make Task 11's live run fail for
    the instrument's reasons rather than the recorder's."""
    got = h8.nine_rows(read("12-frame-F1-fn-parseDiceGroups.txt"))

    assert got["holds"] is True, got["differences"]
    assert got["n"] == got["read"] == 9
    assert [r["read"]["line"] for r in got["rows"]] == [
        69, 70, 71, 72, 73, 74, 76, 75, 72]


def test_clause_four_names_the_row_that_moved(tmp_path):
    """Catches: a comparison that passes on a changed row. One line number
    moved in a COPY of the transcript must be named, with both readings."""
    text = read("12-frame-F1-fn-parseDiceGroups.txt").replace(
        "parseDiceGroups L74  sides=20", "parseDiceGroups L75  sides=20", 1)

    got = h8.nine_rows(text)

    assert got["holds"] is False
    assert [d["row"] for d in got["differences"]] == [6]
    assert got["differences"][0]["expected"]["line"] == 74
    assert got["differences"][0]["read"]["line"] == 75


def _census_json(tmp_path: Path, corpus_rows: list) -> Path:
    path = tmp_path / "census.json"
    path.write_text(json.dumps({"roots": [
        {"root": "typescript/probes", "deferred": [], "files_scanned": 21},
        {"root": "corpus/typescript", "deferred": corpus_rows,
         "files_scanned": 84},
        {"root": "the lens", "deferred": [], "files_scanned": 1},
    ]}), encoding="utf-8")
    return path


def test_census_matches_agrees_with_the_pinned_hand_table(tmp_path):
    """The positive control: a JSON printing exactly the sha-pinned census's
    three lists -- 0, 1 and 0 -- matches, table by table."""
    got = h8.census_matches(CENSUS, _census_json(tmp_path, [
        {"rel": "corpus/typescript/focus_finally_return/finally.ts",
         "qualname": "settle", "line": 7}]))

    assert got["holds"] is True, (got["missing"], got["extra"])
    assert got["missing"] == [] and got["extra"] == []
    assert [t["hand_rows"] for t in got["per_table"].values()] == [0, 1, 0]
    assert [t["declared_n"] for t in got["per_table"].values()] == [0, 1, 0]


def test_census_matches_names_a_root_that_disagrees(tmp_path):
    """Catches: a comparer that passes on a disagreeing pair. The detector
    misses `settle` and invents a function in the LENS list -- the list §1.5
    and H8′'s eighth clause both rest on being EMPTY."""
    got = h8.census_matches(CENSUS, _census_json(tmp_path, []))

    assert got["holds"] is False
    assert [m["triple"] for m in got["missing"]] == [
        ["corpus/typescript/focus_finally_return/finally.ts", "settle", 7]]
    assert got["extra"] == []

    invented = json.loads(_census_json(tmp_path, []).read_text(encoding="utf-8"))
    invented["roots"][2]["deferred"] = [
        {"rel": "src/lib/diceQueue.ts", "qualname": "parseDiceGroups", "line": 68}]
    (tmp_path / "census.json").write_text(json.dumps(invented), encoding="utf-8")

    worse = h8.census_matches(CENSUS, tmp_path / "census.json")

    assert worse["holds"] is False
    assert [e["triple"] for e in worse["extra"]] == [
        ["src/lib/diceQueue.ts", "parseDiceGroups", 68]]


def test_every_clause_of_section_one_nine_has_a_reader():
    """Catches: a clause added to §1.9 that nothing reads. `clauses()`
    refuses by name in that case; this is the same question asked in
    source, so the count cannot drift silently."""
    rows = h8.clause_rows()

    assert [r["n"] for r in rows] == list(range(1, 9)), rows
    assert all(r["clause"].strip() for r in rows)


# -- E13 and E14, on fixture inputs ----------------------------------------


#: The one function the sha-pinned census names, and the file it lives in.
SETTLE = ("corpus/typescript/focus_finally_return/finally.ts", "settle", 7)


def _e13_fixture(tmp_path: Path, **over) -> Path:
    (tmp_path / "census.json").write_text(json.dumps({"roots": [
        {"root": "typescript/probes", "deferred": [], "files_scanned": 21},
        {"root": "corpus/typescript", "files_scanned": 84, "deferred": [
            {"rel": SETTLE[0], "qualname": SETTLE[1], "line": SETTLE[2]}]},
        {"root": "the lens", "deferred": [], "files_scanned": 1},
    ]}), encoding="utf-8")
    (tmp_path / "transform-diff.json").write_text(json.dumps({
        "files_compared": 84, "changed": 1,
        "files": over.get("files", [
            {"file": "focus_finally_return/finally.ts", "changed": True,
             "functions": ["settle"], "diff": "@@ …"},
            {"file": "finally_return/ledger.ts", "changed": False,
             "functions": [], "diff": ""}])}), encoding="utf-8")
    (tmp_path / "corpus.json").write_text(json.dumps({
        "command": "corpus/run_corpus.py --require-driver", "exit": 0,
        "cases": {"focus_finally_return": {"language": "typescript",
                                           "exit": over.get("case_exit", 0)}}}),
        encoding="utf-8")
    (tmp_path / "honesty-cost.diff").write_text(over.get("cost", ""),
                                                encoding="utf-8")
    return tmp_path


def test_e13_holds_when_the_census_the_diff_and_the_case_agree(tmp_path):
    """The positive control, and the one that shows clause 2 tolerates the
    two spellings: the census writes a repository-relative path and
    `transform_diff.mjs` writes one relative to the root it was handed."""
    got = e13_report.build(_e13_fixture(tmp_path))

    assert got["dropped"] == []
    assert got["value"] == got["n"] == 4, got["claims"]
    assert got["transform_diff"]["changed"] == {SETTLE[0]: ["settle"]}


def test_e13_stops_on_a_wrapper_the_census_never_named(tmp_path):
    """Catches: the seal firing on a function the hand census did not name --
    "and no other byte" is the half of clause 2 that discriminates."""
    got = e13_report.build(_e13_fixture(tmp_path, files=[
        {"file": "focus_finally_return/finally.ts", "changed": True,
         "functions": ["settle"], "diff": "@@ …"},
        {"file": "finally_return/ledger.ts", "changed": True,
         "functions": ["commit"], "diff": "@@ …"}]))

    assert got["value"] == 3
    assert got["claims"][
        "the transform diff changes exactly the census's files and wrappers"] \
        is False
    assert "finally_return/ledger.ts" in got["transform_diff"]["changed"]


def test_e13_stops_on_a_moved_honesty_cost_and_a_red_case(tmp_path):
    """Catches: clauses 3 and 4 read as absent rather than as false."""
    got = e13_report.build(_e13_fixture(tmp_path, case_exit=1,
                                        cost=" typescript/HONESTY-COST.md | 2 +-\n"))

    assert got["value"] == 2
    assert got["claims"]["`focus_finally_return` is green"] is False
    assert got["claims"][
        "`HONESTY-COST.md`'s cited numbers are untouched"] is False


def test_e13_over_an_empty_directory_measured_nothing(tmp_path):
    """Catches: an unwritten input scored as a FAILED clause. A clause
    computed over a file nobody wrote comes out False and would be counted,
    so one cell would say both "not measured" (in `dropped`) and "did not
    hold" (in `value`/`n`) about the same clause. The record's schema has one
    representation of not measured -- a null value with a reason -- so an
    absent input's clause is OMITTED from `claims` and `n` counts only what
    was read. Nothing was read here, so nothing was measured."""
    got = e13_report.build(tmp_path)

    assert got["value"] is None
    assert got["n"] == 0
    assert got["claims"] == {}
    assert sorted(got["dropped"]) == sorted(
        f"{name} was not written into the results directory" for name in
        ("census.json", "corpus.json", "honesty-cost.diff",
         "transform-diff.json"))


def test_e13_counts_only_the_clauses_whose_inputs_were_written(tmp_path):
    """The partial case, which is the one the schema exists for: two inputs
    written and two not. `n` is 2, the two that were read are scored, and
    `dropped` names the two that were not -- never a 2-of-4 that reads as
    two failures."""
    full = _e13_fixture(tmp_path)
    (full / "transform-diff.json").unlink()
    (full / "honesty-cost.diff").unlink()

    got = e13_report.build(full)

    assert got["n"] == 2 and got["value"] == 2
    assert set(got["claims"]) == {
        "`census_deferred.mjs` prints the three pinned lists exactly",
        "`focus_finally_return` is green"}
    assert sorted(got["dropped"]) == sorted(
        f"{name} was not written into the results directory" for name in
        ("honesty-cost.diff", "transform-diff.json"))


def _e14_fixture(tmp_path: Path, **over) -> Path:
    cases = {"focus_block_let": {"language": "rust",
                                 "exit": over.get("case_exit", 0)},
             "refocus_env": {"language": "rust",
                             "exit": over.get("refocus_exit", 0)},
             "block_free": {"language": "rust", "exit": over.get("other", 0)},
             "focus_finally_return": {"language": "typescript", "exit": 0}}
    (tmp_path / "corpus.json").write_text(json.dumps(
        {"command": "corpus/run_corpus.py --require-driver", "exit": 0,
         "cases": cases}), encoding="utf-8")
    (tmp_path / "vectors.json").write_text(json.dumps(
        {"command": "pytest -k v40", "exit": over.get("vectors", 0)}),
        encoding="utf-8")
    (tmp_path / "refusals.json").write_text(json.dumps(
        {"command": "cargo test -p cargo-sensorium spool::",
         "exit": over.get("refusals", 0)}), encoding="utf-8")
    return tmp_path


def test_e14_holds_when_the_new_case_is_green_and_nothing_else_moved(tmp_path):
    """The positive control. The TypeScript case in the fixture must not be
    counted among "every other Rust case": the clause is about Rust."""
    got = e14_report.build(_e14_fixture(tmp_path))

    assert got["dropped"] == []
    assert got["value"] == got["n"] == 5, got["claims"]
    assert got["rust_cases"] == ["block_free", "focus_block_let", "refocus_env"]
    assert got["other_rust_cases"] == 2


def test_e14_names_the_rust_case_that_moved(tmp_path):
    """Catches: "every other Rust case equal" reported as a bare false. The
    case that moved is named, and a `refocus_*` one is named twice because
    §1.6 asks about it twice."""
    got = e14_report.build(_e14_fixture(tmp_path, other=1, refocus_exit=1))

    assert got["value"] == 3
    assert got["rust_cases_that_moved"] == ["block_free", "refocus_env"]
    assert got["refocus_cases_that_moved"] == ["refocus_env"]


def test_e14_counts_only_the_clauses_whose_inputs_were_written(tmp_path):
    """The partial case, and the one that shows a single input can carry
    several clauses: `corpus.json` alone feeds THREE of §1.6's five, so a
    directory holding only it measures three and names the other two."""
    full = _e14_fixture(tmp_path)
    (full / "vectors.json").unlink()
    (full / "refusals.json").unlink()

    got = e14_report.build(full)

    assert got["n"] == 3 and got["value"] == 3
    assert list(got["claims"]) == [
        "`focus_block_let` is green",
        "every other Rust corpus case is equal",
        "every `refocus_*` case is equal"]
    assert sorted(got["dropped"]) == sorted(
        f"{name} was not written into the results directory"
        for name in ("refusals.json", "vectors.json"))


def test_e14_over_an_empty_directory_measured_nothing(tmp_path):
    """The same house rule as E13's: nothing read, nothing measured, and a
    null value rather than a zero that reads as five failed clauses."""
    got = e14_report.build(tmp_path)

    assert got["value"] is None and got["n"] == 0 and got["claims"] == {}
    assert len(got["dropped"]) == 3


def test_e14_does_not_pass_on_an_empty_corpus(tmp_path):
    """Catches: the vacuous green -- a corpus that lost every Rust case has
    nothing that moved, which is not the same as nothing having moved."""
    (tmp_path / "corpus.json").write_text(json.dumps(
        {"command": "x", "exit": 0, "cases": {}}), encoding="utf-8")
    (tmp_path / "vectors.json").write_text('{"command": "x", "exit": 0}',
                                           encoding="utf-8")
    (tmp_path / "refusals.json").write_text('{"command": "x", "exit": 0}',
                                            encoding="utf-8")

    got = e14_report.build(tmp_path)

    assert got["claims"]["every other Rust corpus case is equal"] is False
    assert got["claims"]["every `refocus_*` case is equal"] is False


# -- the assembler ----------------------------------------------------------


def _fake_cell(value, n, **detail) -> dict:
    return {"value": value, "n": n, "dropped": [], **detail}


def _results(tmp_path: Path, *, drop: str | None = None) -> Path:
    """A results directory holding one JSON per instrument of this slice."""
    files = {
        "e12p-reads.json": {"cells": {
            "H2p": _fake_cell(5, 5), "H4p": _fake_cell(3, 3),
            "H5p": _fake_cell(7, 7)},
            "run_id": "20260912-015130-42f691",
            "reads": {"info F1": "02-info-F1.txt"},
            "record": "docs/…/2026-09-12-sensorium-s5-rung4-debts.md",
            "record_sha256": "0" * 64, "questions_sha256": "1" * 64},
        "e12p-h8.json": _fake_cell(8, 8),
        "e13.json": _fake_cell(4, 4, census={"holds": True},
                               transform_diff={"changed": {}}),
        "e14.json": _fake_cell(5, 5),
        "e6tsp.json": _fake_cell(12, 12),
        "e-legacy.json": _fake_cell(1, 1),
        "e-branch.json": _fake_cell(1, 1),
        "suites.json": {"pytest": {"command": "pytest -q", "exit": 0}},
    }
    for name, body in files.items():
        if name == drop:
            continue
        (tmp_path / name).write_text(json.dumps(body), encoding="utf-8")
    return tmp_path


def test_the_assembly_carries_the_records_schema(tmp_path):
    """Catches: a results file missing one of the four sections a reader of
    this record needs -- the gated cells in §3's row order, what is reported
    beside them, what was verified, and who recorded it."""
    payload, _ = assembler.build(_results(tmp_path))
    payload["verification"] = {}
    payload["recorded_by"] = {}

    assert set(payload) >= {"gated", "reported", "verification", "recorded_by"}
    assert list(payload["gated"]) == assembler.ORDER
    assert set(payload["reported"]) == {
        "fences", "suites", "census", "transform_diff", "the_three_readings"}
    assert payload["reported"]["census"] == {"holds": True}


def test_the_assembly_refuses_a_missing_cell_by_name(tmp_path):
    """Catches: a cell nobody measured reported as an omission or a zero.
    `e14.json` absent must become a null value with a reason NAMING the file,
    which is the record's only representation of 'not measured'."""
    payload, _ = assembler.build(_results(tmp_path, drop="e14.json"))

    e14 = payload["gated"]["E14"]
    assert e14["value"] is None and e14["n"] == 0
    assert len(e14["dropped"]) == 1
    assert "e14.json" in e14["dropped"][0]
    assert payload["gated"]["E13"]["value"] == 4          # the others stand


def _consistent(tmp_path: Path, **over) -> Path:
    """A results directory whose reads record verifies: §1.1's bytes, and
    both locked §1s' sha256. Everything the assembler CHECKS is real here;
    only the cells are fixtures."""
    results = _results(tmp_path)
    (results / "e12p-reads.json").write_text(json.dumps({
        "cells": {"H2p": _fake_cell(5, 5), "H4p": _fake_cell(3, 3),
                  "H5p": _fake_cell(7, 7)},
        "run_id": "20260912-015130-42f691",
        "reads": {"info F1": "02-info-F1.txt"},
        "record": "docs/…/2026-09-12-sensorium-s5-rung4-debts.md",
        "record_sha256": over.get("record_sha256", hashlib.sha256(
            e12pre.RECORD.read_bytes()).hexdigest()),
        "questions_from": "docs/…/2026-09-11-sensorium-s5-rung4-focus.md",
        "questions_sha256": hashlib.sha256(RUNG4.read_bytes()).hexdigest(),
        "reads_dir": str(REAL), "store": str(store()),
    }), encoding="utf-8")
    return results


def _assemble(results: Path, out: Path) -> int:
    return assembler.main(["assemble_s5debts.py", str(results), str(out),
                           "task-2 rehearsal", "0" * 40,
                           f"{store()}=<store>", f"{REPO}=<repo>"])


def test_assembling_a_consistent_results_directory_writes_the_file(tmp_path):
    """The positive control for `main` itself, not for `build`: with §1.1's
    bytes verifying and both locked §1s matching, the assembler exits 0 and
    writes the results file, and all three verifications read OK."""
    out = tmp_path / "results.json"

    code = _assemble(_consistent(tmp_path), out)

    assert code == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert {k: v["ok"] for k, v in written["verification"].items()} == {
        "hashed_set": True, "reads_read_this_record": True,
        "questions_read_rung_fours_record": True}
    assert list(written["gated"]) == assembler.ORDER


def test_assembling_reads_taken_against_another_record_fails_by_name(
        tmp_path, capsys):
    """Catches: a dry run's numbers assembled into this slice's results file.
    `e12p_report.py` records which §1 it read and its sha256; `main` compares
    it against the tree's own and exits 1 naming the check.

    The file IS still written, and the test pins that deliberately: it is
    `assemble_rung4.py`'s documented behaviour, inherited here on purpose --
    "a reader diagnosing a failed verification needs the cells it failed
    over" -- and what makes it safe is that the written file PUBLISHES the
    failure in its own `verification` block rather than hiding it. Both halves
    are asserted, so a future decision to suppress the write would surface
    here as a deliberate change rather than a silent one."""
    out = tmp_path / "results.json"

    code = _assemble(_consistent(tmp_path, record_sha256="0" * 64), out)

    err = capsys.readouterr().err
    assert code == 1
    assert "reads_read_this_record: FAILED" in err
    assert "0" * 64 in err
    assert "hashed_set: OK" in err                 # the ONLY failure is this
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["verification"]["reads_read_this_record"]["ok"] is False


def test_assembling_a_cell_carrying_a_box_path_refuses_and_writes_nothing(
        tmp_path, capsys):
    """Catches: a box path reaching a COMMITTED results file. `pytest`'s own
    `tmp_path` sits under one of `assemble.FORBIDDEN`'s prefixes, so a cell
    carrying it is exactly the offender the refusal exists for -- and this
    test needs no box-path literal of its own to make one."""
    results = _consistent(tmp_path)
    (results / "e13.json").write_text(json.dumps(
        _fake_cell(4, 4, where=str(tmp_path))), encoding="utf-8")
    out = tmp_path / "results.json"

    code = _assemble(results, out)

    err = capsys.readouterr().err
    assert code == 2
    assert "a box path survived redaction" in err
    assert "$.gated.E13.where" in err
    assert str(tmp_path) in err
    assert not out.exists(), "a refused assembly must write no results file"


def test_the_assembly_says_the_reads_named_no_directory(tmp_path):
    """Catches: `verify_hashes` passing on a reads file that does not say
    which bytes it read -- a verification with nothing to verify."""
    got = assembler.verify_hashes({"run_id": "x"})

    assert got["ok"] is False
    assert "e12p-reads.json" in got["why"][0]
