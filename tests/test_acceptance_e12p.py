"""E12′'s instrument, tested on literal rows and on the committed transcripts.

`typescript/acceptance/e12_report.py` read rung 4's transcripts with four
defects, each named in the rung-4 record's §4.4/§4.5, and three of rung 4's
eight endpoints STOPped on them rather than on the recorder. `e12p_report.py`
is the parser without them. This file is what says so, in two halves:

* **the shapes** -- five literal rows, one per defect plus one control, so
  each fix has a test that fails when that one line of the regex moves. The
  mutations run against them are in the task report.
* **the committed data** -- the thirteen transcripts of 2026-09-11, which are
  in the repository and whose sha256 list is the new record's §1.1. The
  numbers asserted here are the ones §1 of
  `docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md`
  pre-registers, and every one of them is a STOP of rung 4's instrument
  turned into a PASS **of this instrument**, never a re-measurement of the
  recorder:

  | assertion | the rung-4 STOP it answers |
  |---|---|
  | S2 read off `08-…` as a CALL row, `e10`, `parseDiceGroups` | §4.5 (1): a CALL row's qualname is not the token after the kind, so `S2 found` read false on a row that IS the sighting |
  | `call_line_of(conn, 10) == 68` | §4.5 (2): a printed CALL carries no `L<line>`, so even a fixed name would not have matched §1.3's `diceQueue.ts:68` |
  | `elsewhere_not_gated` five rows | §4.5's third gap: a `RETURN` arrow takes ONE space, so the cell listed one row where the transcripts print five |
  | W2: 0 HITs on a row whose `unbound` names `count`, 2 at line 72 | §4.4: a `line` alone cannot tell a `while`'s head row from its completion row; the payload can |

  W1, W3, S1 and the resolver's six sites are the controls: they held in rung
  4 and must still hold here, or the new parser has traded one defect for
  another.

Nothing here measures anything. The endpoints are read once, by Task 11, with
the instruments this file tests.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"
sys.path.insert(0, str(ACCEPT))

import e12p_pre as e12pre                                         # noqa: E402
import e12p_report as e12p                                        # noqa: E402

#: The committed transcripts of rung 4's thirteen reads. They are in the
#: repository, so these tests need no box and no environment.
REAL = (REPO / "docs" / "superpowers" / "acceptance"
        / "2026-09-11-sensorium-s5-rung4-focus-reads")

#: The rung-4 record, whose §4.2 quotes `node resolve.mjs`'s six sites.
RUNG4 = (REPO / "docs" / "superpowers" / "acceptance"
         / "2026-09-11-sensorium-s5-rung4-focus.md")

#: The sha-pinned seal-deferred census, E13's first clause's prediction.
CENSUS = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-12-sensorium-s5-rung4-debts-census.md")


def read(name: str) -> str:
    return (REAL / name).read_text(encoding="utf-8")


def only(rows: list[dict], kind: str) -> list[dict]:
    return [r for r in rows if r["kind"] == kind]


# -- the five shapes -------------------------------------------------------


def test_rows_of2_reads_a_call_rows_name_before_its_parenthesis():
    """Catches: the rung-4 defect §4.5 (1) coming back -- `\\S+` takes
    `parseDiceGroups(formula='1d20')` whole as the qualname, and the
    population test `qualname in {the three focused}` then fails on the row
    that IS the sighting."""
    line = "  e10 CALL    parseDiceGroups(formula='1d20')   [arg formula]"

    (row,) = e12p.rows_of2(line)

    assert row["kind"] == "CALL"
    assert row["qualname"] == "parseDiceGroups"
    assert row["args"] == "(formula='1d20')"
    assert row["line"] is None
    assert row["labels"] == ["arg formula"]
    assert row["eid"] == 10


def test_rows_of2_reads_a_return_whose_arrow_follows_one_space():
    """Catches: the rung-4 defect §4.5's third gap -- `\\s\\s->` requires two
    spaces before the arrow and `flow` prints one, so four of the five
    ungated RETURN rows were invisible to `elsewhere_not_gated`."""
    line = "  e288 RETURN  buildForcedNotation.<anonymous> -> 20   [return]"

    (row,) = e12p.rows_of2(line)

    assert row["kind"] == "RETURN"
    assert row["qualname"] == "buildForcedNotation.<anonymous>"
    assert row["ret"] == "20"
    assert row["labels"] == ["return"]


def test_rows_of2_reads_a_head_row_hit_as_carrying_no_unbound():
    """Catches: the rung-4 defect §4.4 -- W2's two HITs at line 72 are HEAD
    rows, and a reader that classes by `line` alone calls them the
    completion row §1.2 predicts no hit on."""
    line = ("  HIT   e32 LINE    parseDiceGroups L72  "
            "m=[ '2d6', … ]   state: count=1")

    (row,) = e12p.rows_of2(line)

    assert row["hit"] is True
    assert row["line"] == 72
    assert row["unbound"] == []


def test_rows_of2_reads_a_completion_rows_unbound_names():
    """Catches: an `unbound` parse that never fires -- the completion row's
    only distinguishing mark. Without it W2's clause cannot be read off the
    payload at all and the instrument is back to reading line numbers."""
    line = ("  HIT   e40 LINE    parseDiceGroups L72  "
            "m=null unbound:count,sides   state: …")

    (row,) = e12p.rows_of2(line)

    assert row["unbound"] == ["count", "sides"]
    assert row["line"] == 72


def test_rows_of2_still_reads_a_plain_line_row_with_its_label():
    """The control: the shape `rows_of` already read must read identically,
    or the new parser has bought the four fixes with a regression."""
    line = "  e16 LINE    parseDiceGroups L74  sides=20   [local sides]"

    (row,) = e12p.rows_of2(line)

    assert row["kind"] == "LINE"
    assert row["qualname"] == "parseDiceGroups"
    assert row["line"] == 74
    assert row["args"] is None
    assert row["ret"] is None
    assert row["unbound"] == []
    assert row["labels"] == ["local sides"]
    assert row["rest"] == "sides=20   [local sides]"


# -- the committed transcripts ---------------------------------------------

#: The three names the rung-4 specs focus, as `e12_report.preregistration()`
#: reads them out of the rung-4 record's §1. Spelled from the record here too
#: rather than typed, so the population this file gates on is §1's.
FOCUSED = {"parseDiceGroups", "forcedDiceFromSource", "buildDiceQueueEntry"}


def test_h5p_reads_S2_off_the_committed_transcript():
    """Rung 4 read `S2 found: false` off this very file. The row is there:
    one CALL, `parseDiceGroups`, event `e10` -- §1.4's pre-registered
    reading, and the STOP §4.5 (1) explains."""
    rows = e12p.rows_of2(read("08-flow-F1-value-1d20.txt"))

    calls = only(rows, "CALL")
    assert len(calls) == 1, [r["text"] for r in calls]
    assert calls[0]["qualname"] == "parseDiceGroups"
    assert calls[0]["eid"] == 10
    assert calls[0]["args"] == "(formula='1d20')"
    assert calls[0]["labels"] == ["arg formula"]
    assert len(only(rows, "RETURN")) == 4


def test_h5p_elsewhere_is_five_across_the_two_flow_transcripts():
    """§1.4: `elsewhere_not_gated` = 5, one row from `--value 20` and four
    RETURN rows from `--value "'1d20'"`. Rung 4's cell listed ONE, because
    four of the five have a one-space arrow (§4.5's third gap)."""
    twenty = e12p.rows_of2(read("07-flow-F1-value-20.txt"))
    one_d20 = e12p.rows_of2(read("08-flow-F1-value-1d20.txt"))

    pop20, out20 = e12p.split_population(twenty, FOCUSED)
    pop1d20, out1d20 = e12p.split_population(one_d20, FOCUSED)

    assert len(out20) == 1, [r["text"] for r in out20]
    assert len(out1d20) == 4, [r["text"] for r in out1d20]
    assert len(out20) + len(out1d20) == 5
    # S1's nine sightings of `sides` at :74, the control that already held.
    assert len(pop20) == 9
    assert {(n, r["line"]) for r in pop20 for n in r["names"]} == {("sides", 74)}
    assert len(pop1d20) == 1


def test_h4p_W2_has_no_hit_on_a_completion_row_and_two_head_rows_at_72():
    """§1.3's W2, and the rung-4 STOP §4.4 explains: 52 HITs, NONE on a row
    whose `unbound` names `count` (the `while`'s completion rows), and the
    two at line 72 are HEAD rows carrying no `unbound` at all. Rung 4's cell
    tested "no HIT at line 72", which is strictly stronger and read a miss.

    The total is `watch`'s own tally line, never a count of printed rows:
    this transcript prints 20 of 52 and says `... 32 more`."""
    text = read("05-watch-F1-at-parseDiceGroups-expr-count-1.txt")

    tally = e12p.tally_of(text)
    hits = [r for r in e12p.rows_of2(text) if r["hit"]]

    assert tally["hits"] == 52
    assert tally["evaluated"] == 77
    assert [r["text"] for r in hits if "count" in r["unbound"]] == []
    at72 = [r for r in hits if r["line"] == 72]
    assert len(at72) == 2, [r["text"] for r in at72]
    assert all(r["unbound"] == [] for r in at72)
    assert all("m=[" in r["rest"] for r in at72)
    # ANTI-VACUITY. "Zero rows whose `unbound` names `count`" is a real zero
    # only while the parse that would have found one is alive: an `unbound`
    # that never fires reads the same zero off any transcript at all. W2's
    # own printed hits carry no completion row, so the control is the same
    # run's `frame` transcript, where the completion row is right there.
    completions = [r for r in e12p.rows_of2(
        read("12-frame-F1-fn-parseDiceGroups.txt")) if r["unbound"]]
    assert [(r["line"], r["unbound"]) for r in completions] == [
        (72, ["count", "sides"])]


def test_h4p_W3_fifteen_completion_rows():
    """§1.3's W3, the control: 15 HITs, all at line 72, every one a
    completion row carrying `m=null` and `unbound:count,sides`. All fifteen
    are printed, so the tally and the rows agree here."""
    text = read("06-watch-F1-at-parseDiceGroups-expr-m-null.txt")

    tally = e12p.tally_of(text)
    hits = [r for r in e12p.rows_of2(text) if r["hit"]]

    assert tally["hits"] == 15
    assert len(hits) == 15
    assert {r["line"] for r in hits} == {72}
    assert all(r["unbound"] == ["count", "sides"] for r in hits)
    assert all("m=null" in r["rest"] for r in hits)


def test_h4p_W1_thirty_one():
    """§1.3's W1, the other control: 31 HITs of 64 evaluable sites."""
    text = read("04-watch-F1-at-parseDiceGroups-expr-sides-20.txt")

    tally = e12p.tally_of(text)

    assert tally["hits"] == 31
    assert tally["evaluated"] == 64
    assert tally["sites"] == 165


def test_h2p_resolver_output_in_the_record_names_six():
    """§1.2's gate: `node resolve.mjs` named SIX sites, and exactly two of
    them share one qualname -- which is why `focus_matched` is 5 and
    `functions_focused` 6. Read out of the rung-4 record's §4.2 fenced
    block, the committed copy of the resolver's answer."""
    sites = e12p.resolver_sites_in_record(RUNG4.read_text(encoding="utf-8"))

    assert len(sites) == 6, sites
    names = [s.split(":", 1)[1] for s in sites]
    assert len(set(names)) == 5, names
    assert [n for n in set(names) if names.count(n) == 2] == [
        "buildDiceQueueEntry.<anonymous>"]


# -- the trace, and the hash preflight -------------------------------------


def store() -> Path:
    """The rung-4 store copy, named by the operator.

    A committed file of this slice carries no box path (the record's §2
    rule), so the copy's location is `E12P_STORE`'s. Skipping BY NAME rather
    than passing silently is the rule: a skip that reads as a pass is a green
    suite that checked nothing.
    """
    where = os.environ.get("E12P_STORE")
    if not where:
        pytest.skip("E12P_STORE unset: the rung-4 store copy is not on this box")
    return Path(where)


def test_call_line_of_reads_the_code_objects_line_for_S2():
    """§1.4's S2 line is `diceQueue.ts:68`, the code object's own -- and a
    printed CALL row carries no `L<line>` at all (§4.5 (2)). The run id is
    read off the committed `info F1` transcript rather than typed."""
    f1 = e12p.run_id_of(read("02-info-F1.txt"))
    assert f1, "the committed `info F1` transcript names no run id"

    conn = e12p.db(store(), f1)
    try:
        assert e12p.call_line_of(conn, 10) == 68
        # The CODE OBJECT's line, not the event's. On a CALL those two happen
        # to be equal in this trace, so S2 alone cannot tell a correct reader
        # from one that took `events.line`; `e11` is a LINE event AT line 69
        # whose code object is still `parseDiceGroups` at 68, and it can.
        assert e12p.call_line_of(conn, 11) == 68
        assert e12p.call_line_of(conn, 10 ** 9) is None
    finally:
        conn.close()


def test_the_preflight_refuses_a_transcript_that_moved(tmp_path):
    """Catches: a reading taken off data §1.1 does not describe. §1.1's own
    words: a mismatch is exit 4 and no number."""
    for path in sorted(REAL.glob("*.txt")):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    listed = e12pre.hash_list()["transcripts"]
    assert e12pre.verify_transcripts(tmp_path, listed)["ok"]

    (tmp_path / "07-flow-F1-value-20.txt").write_text("moved\n", encoding="utf-8")
    got = e12pre.verify_transcripts(tmp_path, listed)

    assert got["ok"] is False
    assert any("07-flow-F1-value-20.txt" in why for why in got["why"]), got["why"]


def test_the_preflight_refuses_a_fourteenth_transcript(tmp_path):
    """Catches: a transcript in the directory that §1.1 does not list -- data
    the record does not describe, sitting beside data it does."""
    for path in sorted(REAL.glob("*.txt")):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    (tmp_path / "14-extra.txt").write_text("$ sensorium info X\n", encoding="utf-8")

    got = e12pre.verify_transcripts(tmp_path, e12pre.hash_list()["transcripts"])

    assert got["ok"] is False
    assert got["extra"] == ["14-extra.txt"]


def test_every_predicted_number_is_read_from_the_record(tmp_path, monkeypatch):
    """Catches: ruling P1 broken -- a number typed into the instrument is a
    second pre-registration nobody locked. Move §1.2's gate in a COPY of the
    record and the instrument must read the moved number, not the old one."""
    copy = tmp_path / "record.md"
    copy.write_text(e12pre.RECORD.read_text(encoding="utf-8")
                    .replace("N = 6.**", "N = 7.**"), encoding="utf-8")
    monkeypatch.setattr(e12pre, "RECORD", copy)

    got = e12pre.predictions()

    assert got["functions_focused"] == 7
    assert got["record"] == "record.md"          # the copy, named, not a path


# -- H8′'s readers, and the census comparer --------------------------------

import e12p_h8 as h8                                              # noqa: E402


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

import e13_report                                                 # noqa: E402
import e14_report                                                 # noqa: E402

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


def test_e13_names_a_file_the_operator_did_not_write(tmp_path):
    """Catches: a missing input read as a passing clause. `dropped` names it
    and the cell is partial, never a silent zero."""
    got = e13_report.build(tmp_path)

    assert len(got["dropped"]) == 4
    assert got["value"] == 0


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
