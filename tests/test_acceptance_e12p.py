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

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ACCEPT = REPO / "typescript" / "acceptance"
sys.path.insert(0, str(ACCEPT))

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
