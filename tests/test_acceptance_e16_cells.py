"""E16 part A's CELLS, on hand-built inputs.

Four cells decide part A -- H1 (the token's bytes nowhere under the work
root), H2 (0600/0700 on everything the recorders made), H3 (the licence
before and after the token changes) and H6 (`redaction.env` holds exactly
one name) -- and each one is a pure function over a list of rows. This
module is the only place they are exercised against inputs somebody chose:
the measurement runs once, and a decision function first seen on the day of
the run is a decision function nobody has ever watched refuse.

WHAT IS BEING PREVENTED, CELL BY CELL
-------------------------------------
* **a cell that cannot STOP.** Each cell here has a passing input AND a
  failing one differing in one field, and the failing one must name the row
  it failed over. A gate that reports "STOP" without the offending path is
  a gate whose finding nobody can act on -- H1's whole STOP clause is "any
  non-zero: a missed path. Named, fixed, ...".
* **a hole read as a pass.** `None` is what `e16a.py` writes for anything it
  did not measure -- a phase that was killed, a file it could not stat, a
  transcript that did not parse. Every cell turns a `None` anywhere in its
  input into `dropped`, never into PASS: a measurement that did not happen
  and a measurement that passed are the two facts this whole apparatus
  exists to keep apart.
* **a verdict word invented here.** `RULES` is the PASS/STOP column of the
  record's §1 §9 table, and `test_the_rule_table_is_the_records_own_words`
  checks it against the record on disk rather than against a second copy
  typed into this file. A rule paraphrased into the instrument is a rule the
  instrument, not the pre-registration, decides.
* **an assembler that publishes a dry run.** The dry run plants a decoy that
  cannot be the token and caps every timer at a minute; its numbers are
  about a different string. `assemble_e16a.refuse_dry_run` is what keeps
  them out of the record, and it is tested here rather than trusted.

The transcripts below are EXCERPTS in the shapes `sensorium refocus` really
prints -- `refocus_world._env_state`'s two env lines and
`refocus_cmd.report`'s two licence lines -- kept to the lines `parse_refocus`
reads. They are hand-built on purpose: what is under test is the decision,
not the box.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "acceptance_e16"))
sys.path.insert(0, str(REPO / "rust" / "tests"))

import assemble_e16a                                              # noqa: E402
import e16a                                                       # noqa: E402
from e16a import (RULES, TOKEN_VAR, cell_h1, cell_h2, cell_h3,    # noqa: E402
                  cell_h6, part_word, read_pair)

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-13-sensorium-e16-redaction.md")


# -- H1: the token's bytes, per file ---------------------------------------
def _files(*rows):
    return [{"path": p, "count": c} for p, c in rows]


def test_h1_passes_when_every_file_examined_counted_zero():
    out = cell_h1(_files(("store-a/traces/r.db", 0),
                         ("store-a/redaction.key", 0),
                         ("rust-target/sensorium/spool/i/1.proc.json", 0)))
    assert out["word"] == "PASS"
    assert out["files_examined"] == 3


def test_h1_stops_and_names_the_file_that_counted_more_than_zero():
    """The STOP clause is "any non-zero: a missed path. Named, ...", so the
    name is part of the verdict and not a detail a reader digs for."""
    out = cell_h1(_files(("store-a/traces/r.db", 0),
                         ("store-a/spool/i/1497008-0.jsonl", 2)))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["store-a/spool/i/1497008-0.jsonl"]
    assert "store-a/spool/i/1497008-0.jsonl" in out["why"]


def test_h1_is_dropped_when_a_count_is_missing():
    """A file the sweep could not read is a hole, and a hole that counted as
    a zero would be a leak reported as a clean sweep."""
    out = cell_h1([{"path": "store-a/traces/r.db", "count": None}])
    assert out["word"] == "dropped"
    assert "store-a/traces/r.db" in out["why"]


def test_h1_is_dropped_when_the_sweep_did_not_run():
    assert cell_h1(None)["word"] == "dropped"


def test_h1_refuses_an_empty_sweep_rather_than_passing_it():
    """Catches the failure this cell is most exposed to: a `grep -r` over a
    path that does not exist returns nothing, and "no file held the token"
    and "no file was examined" are one string apart."""
    assert cell_h1([])["word"] == "dropped"


# -- H2: the modes ---------------------------------------------------------
def _modes(*rows):
    return [{"path": p, "mode": m, "kind": k, "scope": s}
            for p, m, k, s in rows]


def test_h2_passes_when_every_in_scope_file_is_600_and_directory_700():
    out = cell_h2(_modes(("store-a", "700", "dir", "in"),
                         ("store-a/traces/r.db", "600", "file", "in"),
                         ("rust-target", "775", "dir", "out")))
    assert out["word"] == "PASS"
    assert out["out_of_scope"] == 1


def test_h2_stops_on_one_file_at_644_and_names_it():
    out = cell_h2(_modes(("store-a", "700", "dir", "in"),
                         ("store-a/spool/i/invocation.json", "644",
                          "file", "in")))
    assert out["word"] == "STOP"
    assert out["offenders"] == [
        {"path": "store-a/spool/i/invocation.json", "mode": "644",
         "kind": "file", "want": "600"}]
    assert "invocation.json" in out["why"]


def test_h2_stops_on_a_directory_that_is_not_700():
    out = cell_h2(_modes(("store-a/spool", "775", "dir", "in")))
    assert out["word"] == "STOP"
    assert out["offenders"][0]["want"] == "700"


def test_h2_ignores_the_mode_of_anything_marked_out_of_scope():
    """The instrument's own directories and cargo's build tree are listed so
    a reader can see they were looked at, and are not the recorders' to
    answer for. Listed, never gated -- the distinction the cell keeps."""
    out = cell_h2(_modes(("rust-target/debug/aliasing", "775", "file", "out"),
                         ("store-a", "700", "dir", "in")))
    assert out["word"] == "PASS"


def test_h2_is_dropped_when_a_mode_could_not_be_read():
    out = cell_h2(_modes(("store-a/traces/r.db", None, "file", "in")))
    assert out["word"] == "dropped"


def test_h2_is_dropped_when_the_sweep_did_not_run():
    assert cell_h2(None)["word"] == "dropped"
    assert cell_h2([])["word"] == "dropped"


# -- H3: the four refocus pairs --------------------------------------------
GRANTED = """\
refocus-of: 20260101-000000-aaaaaa   cmd: main.py
focus: derive_sandbox   window: -
source: unchanged (1 file(s) compared by content)
env: unchanged (6 variables compared; not compared: OLDPWD, PWD, \
SENSORIUM_DIR, SHLVL, _)
refocus verdict: MATCH -- every recorded thread produced the identical \
CALL/RETURN/RAISE/HANDLED sequence
licence: verified against 20260101-000000-aaaaaa on exactly these points, \
and no others:
  - 6 environment variable(s) compared and unchanged in the environment the \
rerun executed under; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _
"""

WITHHELD = """\
refocus-of: 20260101-000000-aaaaaa   cmd: main.py
focus: derive_sandbox   window: -
source: unchanged (1 file(s) compared by content)
env: CHANGED since the original run -- 1 variable(s) differ: \
SENSORIUM_E16_TOKEN   (names only)
refocus verdict: MATCH -- every recorded thread produced the identical \
CALL/RETURN/RAISE/HANDLED sequence
licence: WITHHELD -- this MATCH is about call shape, and these checks say \
it is not a statement about the run as a whole:
  - 1 environment variable(s) differ between the two runs \
(SENSORIUM_E16_TOKEN)
"""

#: The Rust shape, and the one this measurement had to be able to tell
#: apart from `GRANTED`: `refocus_rust._is_recorder_key` matches every
#: `SENSORIUM_`-prefixed name, so the pre-registered variable is named on
#: the line as NOT compared while the licence is still granted.
GRANTED_BUT_UNCOMPARED = GRANTED.replace(
    "SENSORIUM_DIR, SHLVL, _)",
    "SENSORIUM_DIR, SHLVL, _)  the recorder's own, also not compared: "
    "RUSTC_WORKSPACE_WRAPPER, SENSORIUM_E16_TOKEN, SENSORIUM_FOCUS")


def _pairs(*rows):
    return [read_pair(name, predicted, text, in_recorded_env=True)
            for name, predicted, text in rows]


def test_h3_passes_when_all_four_pairs_read_as_predicted():
    out = cell_h3(_pairs(("python-unchanged", "granted", GRANTED),
                         ("rust-unchanged", "granted", GRANTED),
                         ("python-changed", "WITHHELD", WITHHELD),
                         ("rust-changed", "WITHHELD", WITHHELD)))
    assert out["word"] == "PASS"
    assert len(out["pairs"]) == 4


def test_h3_stops_when_a_changed_pair_still_grants_the_licence():
    """The discriminating case, and the direction that matters: a rotated
    secret that earns a full licence is what H3 exists to refuse."""
    out = cell_h3(_pairs(("python-unchanged", "granted", GRANTED),
                         ("rust-changed", "WITHHELD", GRANTED)))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["rust-changed"]
    assert "rust-changed" in out["why"]


def test_h3_stops_when_an_unchanged_pair_withholds():
    out = cell_h3(_pairs(("python-unchanged", "granted", WITHHELD)))
    assert out["word"] == "STOP"


def test_h3_stops_when_a_granted_pair_names_the_token_as_not_compared():
    """`GRANTED_BUT_UNCOMPARED` grants the licence and reads `unchanged`, so
    a cell keyed on the licence alone would call it PASS. §1 predicts the
    variable is AMONG THE COMPARED; a line that names it on an exclusion
    list is the other way, and the pair is a STOP."""
    out = cell_h3(_pairs(("rust-unchanged", "granted",
                          GRANTED_BUT_UNCOMPARED)))
    assert out["word"] == "STOP"
    assert out["pairs"][0]["licence"] == "granted"
    assert out["pairs"][0]["token_on_env_line"] is True


def test_read_pair_needs_the_name_in_the_recorded_environment():
    """The positive half of "among the compared". The env line names only
    what was EXCLUDED, so absence from the line is half the claim; the other
    half is that the trace recorded the variable at all (H6's reading). A
    pair whose original trace never held it compared nothing."""
    row = read_pair("python-unchanged", "granted", GRANTED,
                    in_recorded_env=False)
    assert row["ok"] is False
    assert cell_h3([row])["word"] == "STOP"


def test_h3_is_dropped_when_a_transcript_did_not_parse():
    row = read_pair("python-unchanged", "granted", "the driver crashed",
                    in_recorded_env=True)
    assert row["licence"] is None
    assert cell_h3([row])["word"] == "dropped"


def test_h3_is_dropped_when_no_pair_ran():
    assert cell_h3(None)["word"] == "dropped"
    assert cell_h3([])["word"] == "dropped"


def test_read_pair_keeps_the_three_lines_the_record_quotes():
    """The record's §2 quotes the verdict, licence and env lines and nothing
    else -- a whole transcript in a document is a transcript nobody reads,
    and the token's own value must never be near one."""
    row = read_pair("python-changed", "WITHHELD", WITHHELD,
                    in_recorded_env=True)
    assert row["verdict_line"].startswith("refocus verdict: MATCH")
    assert row["licence_line"].startswith("licence: WITHHELD")
    assert row["env_line"].startswith("env: CHANGED")
    assert row["ok"] is True


# -- H6: exactly one redacted name per trace -------------------------------
def _traces(*rows):
    return [{"run": r, "names": n, "vars": v} for r, n, v in rows]


def test_h6_passes_when_every_trace_redacted_exactly_the_token():
    out = cell_h6(_traces(("a", [TOKEN_VAR], 7), ("b", [TOKEN_VAR], 44),
                          ("c", [TOKEN_VAR], 49)))
    assert out["word"] == "PASS"
    assert out["traces"] == 3


def test_h6_stops_on_a_trace_that_redacted_a_second_name():
    out = cell_h6(_traces(("a", [TOKEN_VAR], 7),
                          ("b", [TOKEN_VAR, "AWS_SECRET_ACCESS_KEY"], 44)))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["b"]


def test_h6_stops_on_a_trace_that_redacted_nothing():
    """The under-firing direction. A rule that fired on nothing would leave
    the token in plaintext and read as "no secrets here"."""
    out = cell_h6(_traces(("a", [], 7)))
    assert out["word"] == "STOP"


def test_h6_is_dropped_when_a_traces_names_could_not_be_read():
    assert cell_h6(_traces(("a", None, 7)))["word"] == "dropped"


def test_h6_is_dropped_when_no_trace_was_read():
    assert cell_h6(None)["word"] == "dropped"
    assert cell_h6([])["word"] == "dropped"


# -- the part's own word ---------------------------------------------------
def test_the_part_is_DONE_only_when_every_measured_cell_passed():
    assert part_word({"H1": {"word": "PASS"}, "H2": {"word": "PASS"},
                      "H3": {"word": "PASS"}, "H6": {"word": "PASS"}}) \
        == "DONE"


def test_one_stop_makes_the_part_DONE_WITH_STOP():
    assert part_word({"H1": {"word": "PASS"}, "H2": {"word": "STOP"},
                      "H3": {"word": "PASS"}, "H6": {"word": "PASS"}}) \
        == "DONE-WITH-STOP"


def test_a_dropped_cell_also_costs_the_part_its_plain_DONE():
    """A part whose cell could not be read is not a part that passed. The
    word says so rather than a footnote saying so."""
    assert part_word({"H1": {"word": "dropped"}}) == "DONE-WITH-STOP"


# -- the rule table is the record's, not this instrument's -----------------
def test_the_rule_table_is_the_records_own_words():
    """Catches: §9's PASS/STOP column paraphrased into the instrument, where
    a softened endpoint would decide the measurement while §1 still read as
    the rule. Every cell's two clauses are checked as substrings of the
    record's own row for that cell.

    Read from §1 ALONE. §2's verdict table carries a row per cell too, and
    it quotes the very clause under test -- so a scan of the whole document
    would end up comparing the instrument's output against itself, which is
    a check that passes because it stopped checking."""
    text = DOC.read_text().split("## 2. Part A")[0]
    rows = {m.group(1): m.group(0)
            for m in re.finditer(r"^\| (H\d) \|.*$", text, re.M)}
    assert set(RULES) <= set(rows), (set(RULES) - set(rows))
    for cell, clauses in RULES.items():
        for word, clause in clauses.items():
            assert clause in rows[cell], (cell, word, clause)


def test_every_cell_the_part_measures_has_a_rule_and_a_dropped_reason():
    """The four measured cells and the four deferred ones, with nothing
    falling between: a cell in neither list is one nobody decided about."""
    assert set(RULES) == {"H1", "H2", "H3", "H6"}
    assert dict(e16a.DROPPED) == {"H1-values": "part B", "H4": "part C",
                                  "H5": "part B", "H6-values": "part B"}


# -- the assembler's one refusal -------------------------------------------
def test_the_assembler_refuses_a_dry_run_record():
    """The dry run plants a decoy that cannot be the token and caps every
    timer at a minute. Its cells are about a different string, and rendering
    them into §2 would publish a number about a different subject under §1's
    endpoints."""
    with pytest.raises(assemble_e16a.Refused):
        assemble_e16a.refuse_dry_run({"dry_run": True})
    assert assemble_e16a.refuse_dry_run({"dry_run": False}) is None


def test_the_assembler_refuses_a_record_that_does_not_say_which_it_was():
    """Absent is not false. A raw record with no `dry_run` key came from an
    instrument that did not stamp it, and assuming the safe answer is how a
    dry run gets published once the stamp is ever dropped."""
    with pytest.raises(assemble_e16a.Refused):
        assemble_e16a.refuse_dry_run({})


def test_the_scrub_replaces_the_longest_root_first():
    """Catches: a transcript committed with a box path in it, or -- worse --
    half of one, when the work root sits under a root the scrub also
    replaces and the shorter needle runs first. The labels are what §2's pin
    table defines; a committed artifact says those and nothing else."""
    lens = {"work_root": "/box/w/e16", "repo": "/box/w/repo"}
    pairs = assemble_e16a.scrub_pairs(lens)
    assert [n for n, _ in pairs] == sorted((n for n, _ in pairs),
                                           key=lambda n: -len(n))
    out = assemble_e16a.scrub("cwd: /box/w/e16/py-case and /box/w/repo/x",
                              pairs)
    assert out == "cwd: $E16_DIR/py-case and $REPO/x"


def test_offenders_names_the_line_that_still_holds_a_box_path():
    assert assemble_e16a.offenders("clean\n") == []
    assert assemble_e16a.offenders("trace: /mnt/x/y\n") == ["trace: /mnt/x/y"]
    assert assemble_e16a.offenders("| root | `E16_DIR=/mnt/x` |") == []
