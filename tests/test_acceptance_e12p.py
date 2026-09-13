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

This file is the PARSER half. Its sibling
`tests/test_acceptance_s5debts_reports.py` holds everything that reads an
artefact somebody else produced -- H8′'s eight clause readers, the census
comparer, E13, E14 and the assembler -- and the two were one file until it
crossed `tests/test_ceiling.py`'s 800 lines.

Nothing here measures anything. The endpoints are read once, by Task 11, with
the instruments this file tests.
"""

from __future__ import annotations

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
