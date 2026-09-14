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
from e16a import (ARMS, PREDICTIONS, RULES, TOKEN_VAR,          # noqa: E402
                  cell_h1, cell_h2, cell_h3, cell_h6, gated_roots,
                  part_word, read_pair)

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


#: The run label every H2 case below is written against. One place, because
#: `gated_roots` derives the store's name from it and a test that spelled
#: the store by hand would stop tracking that.
LABEL = "a"


def _roots(*names, ok=True, why=""):
    """One status per gated tree. The default is every tree read; a test
    that wants a short sweep names fewer, or flips `ok`."""
    return [{"root": r, "ok": ok, "why": why}
            for r in (names or gated_roots(LABEL))]


def test_h2_passes_when_every_in_scope_file_is_600_and_directory_700():
    out = cell_h2(_modes(("store-a", "700", "dir", "in"),
                         ("store-a/traces/r.db", "600", "file", "in"),
                         ("rust-target", "775", "dir", "out")),
                  _roots(), LABEL)
    assert out["word"] == "PASS"
    assert out["out_of_scope"] == 1


def test_h2_stops_on_one_file_at_644_and_names_it():
    out = cell_h2(_modes(("store-a", "700", "dir", "in"),
                         ("store-a/spool/i/invocation.json", "644",
                          "file", "in")), _roots(), LABEL)
    assert out["word"] == "STOP"
    assert out["offenders"] == [
        {"path": "store-a/spool/i/invocation.json", "mode": "644",
         "kind": "file", "want": "600"}]
    assert "invocation.json" in out["why"]


def test_h2_stops_on_a_directory_that_is_not_700():
    out = cell_h2(_modes(("store-a/spool", "775", "dir", "in")),
                  _roots(), LABEL)
    assert out["word"] == "STOP"
    assert out["offenders"][0]["want"] == "700"


def test_h2_ignores_the_mode_of_anything_marked_out_of_scope():
    """The instrument's own directories and cargo's build tree are listed so
    a reader can see they were looked at, and are not the recorders' to
    answer for. Listed, never gated -- the distinction the cell keeps."""
    out = cell_h2(_modes(("rust-target/debug/aliasing", "775", "file", "out"),
                         ("store-a", "700", "dir", "in")), _roots(), LABEL)
    assert out["word"] == "PASS"


def test_h2_is_dropped_when_a_mode_could_not_be_read():
    out = cell_h2(_modes(("store-a/traces/r.db", None, "file", "in")),
                  _roots(), LABEL)
    assert out["word"] == "dropped"


def test_h2_is_dropped_when_the_sweep_did_not_run():
    assert cell_h2(None, _roots(), LABEL)["word"] == "dropped"
    assert cell_h2([], _roots(), LABEL)["word"] == "dropped"
    assert cell_h2(_modes(("store-a", "700", "dir", "in")),
                   None, LABEL)["word"] == "dropped"


def test_h2_is_dropped_when_a_gated_root_was_never_swept():
    """Finding 1, H2's third of it. `find` over a root that is not there
    prints nothing and exits non-zero, and the cell used to be handed an
    empty list it could not tell from a complete one -- so a run whose Rust
    arm never recorded would sweep the store, find every mode right, and
    PASS while claiming both trees. The root's own status is what the cell
    drops on, and the reason names the root."""
    out = cell_h2(_modes(("store-a", "700", "dir", "in")),
                  _roots("store-a"), LABEL)
    assert out["word"] == "dropped"
    assert "rust-target/sensorium/spool" in out["why"]


def test_h2_is_dropped_when_find_could_not_read_a_gated_root():
    out = cell_h2(_modes(("store-a", "700", "dir", "in")),
                  _roots(ok=False, why="no such directory"), LABEL)
    assert out["word"] == "dropped"
    assert "no such directory" in out["why"]


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
    """Exactly the pairs named, however few -- for the short-input case."""
    return [read_pair(name, predicted, text, in_recorded_env=True)
            for name, predicted, text in rows]


#: A transcript that reads the way each prediction says it will.
AS_PREDICTED = {"granted": GRANTED, "WITHHELD": WITHHELD}


def _all_pairs(text=None, in_env=None):
    """All four pre-registered pairs, each reading as predicted unless
    `text` or `in_env` names one and changes it.

    Every H3 case that expects a VERDICT has to build the whole set now:
    the cell drops on a short one, which is the hole this round closed, and
    a STOP case built from a single wrong pair would be testing the drop
    rather than the STOP.
    """
    text, in_env = text or {}, in_env or {}
    return [read_pair(name, predicted,
                      text.get(name, AS_PREDICTED[predicted]),
                      in_recorded_env=in_env.get(name, True))
            for name, predicted in PREDICTIONS]


def test_h3_passes_when_all_four_pairs_read_as_predicted():
    out = cell_h3(_all_pairs())
    assert out["word"] == "PASS"
    assert len(out["pairs"]) == 4


def test_h3_stops_when_a_changed_pair_still_grants_the_licence():
    """The discriminating case, and the direction that matters: a rotated
    secret that earns a full licence is what H3 exists to refuse."""
    out = cell_h3(_all_pairs({"rust-changed": GRANTED}))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["rust-changed"]
    assert "rust-changed" in out["why"]


def test_h3_stops_when_an_unchanged_pair_withholds():
    out = cell_h3(_all_pairs({"python-unchanged": WITHHELD}))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["python-unchanged"]


def test_h3_stops_when_a_granted_pair_names_the_token_as_not_compared():
    """`GRANTED_BUT_UNCOMPARED` grants the licence and reads `unchanged`, so
    a cell keyed on the licence alone would call it PASS. §1 predicts the
    variable is AMONG THE COMPARED; a line that names it on an exclusion
    list is the other way, and the pair is a STOP."""
    out = cell_h3(_all_pairs({"rust-unchanged": GRANTED_BUT_UNCOMPARED}))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["rust-unchanged"]
    row = next(p for p in out["pairs"] if p["name"] == "rust-unchanged")
    assert row["licence"] == "granted"
    assert row["token_on_env_line"] is True


def test_read_pair_needs_the_name_in_the_recorded_environment():
    """The positive half of "among the compared". The env line names only
    what was EXCLUDED, so absence from the line is half the claim; the other
    half is that the trace recorded the variable at all (H6's reading). A
    pair whose original trace never held it compared nothing."""
    row = read_pair("python-unchanged", "granted", GRANTED,
                    in_recorded_env=False)
    assert row["ok"] is False
    out = cell_h3(_all_pairs(in_env={"python-unchanged": False}))
    assert out["word"] == "STOP"


def test_h3_is_dropped_when_a_transcript_did_not_parse():
    row = read_pair("python-unchanged", "granted", "the driver crashed",
                    in_recorded_env=True)
    assert row["licence"] is None
    out = cell_h3(_all_pairs({"python-unchanged": "the driver crashed"}))
    assert out["word"] == "dropped"
    assert "python-unchanged" in out["why"]


def test_h3_is_dropped_when_a_pre_registered_pair_is_missing():
    """Finding 1, H3's third of it -- and the cell's own docstring already
    said it: "three pairs out of four is not both". It said so while
    PASSING on any non-empty list, so one refocus that never ran would have
    read as a cell that passed."""
    out = cell_h3(_pairs(("python-unchanged", "granted", GRANTED)))
    assert out["word"] == "dropped"
    assert "1 of 4" in out["why"]
    for name, _predicted in PREDICTIONS[1:]:
        assert name in out["why"]


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
def _traces(*rows, arms=ARMS):
    """One row per arm by default -- what a complete reading looks like.
    A test that wants a short one passes fewer `arms`."""
    return [{"run": r, "arm": a, "names": n, "vars": v}
            for (r, n, v), a in zip(rows, arms)]


def test_h6_passes_when_every_trace_redacted_exactly_the_token():
    out = cell_h6(_traces(("a", [TOKEN_VAR], 7), ("b", [TOKEN_VAR], 44),
                          ("c", [TOKEN_VAR], 49)))
    assert out["word"] == "PASS"
    assert out["traces"] == 3


def test_h6_stops_on_a_trace_that_redacted_a_second_name():
    out = cell_h6(_traces(("a", [TOKEN_VAR], 7),
                          ("b", [TOKEN_VAR, "AWS_SECRET_ACCESS_KEY"], 44),
                          ("c", [TOKEN_VAR], 50)))
    assert out["word"] == "STOP"
    assert out["offenders"] == ["b"]


def test_h6_stops_on_a_trace_that_redacted_nothing():
    """The under-firing direction. A rule that fired on nothing would leave
    the token in plaintext and read as "no secrets here"."""
    out = cell_h6(_traces(("a", [], 7), ("b", [TOKEN_VAR], 44),
                          ("c", [TOKEN_VAR], 50)))
    assert out["word"] == "STOP"


def test_h6_is_dropped_when_a_traces_names_could_not_be_read():
    assert cell_h6(_traces(("a", None, 7), ("b", [TOKEN_VAR], 44),
                           ("c", [TOKEN_VAR], 50)))["word"] == "dropped"


def test_h6_is_dropped_when_an_arm_is_missing():
    """Finding 1, H6's third of it. The census is a claim about all three
    recorders; two traces that both passed is not that claim, and the cell
    used to report it as one."""
    out = cell_h6(_traces(("a", [TOKEN_VAR], 7), ("b", [TOKEN_VAR], 44)))
    assert out["word"] == "dropped"
    assert "typescript" in out["why"]


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
    the rule. Every cell's two clauses are checked by EQUALITY against the
    record's own cell for that row -- not as substrings, which is how H1's
    STOP clause shipped cut short at "…with a fresh token", losing the
    sentence that says a fix is followed by a re-measurement from zero. A
    substring check cannot see a truncation; this one can.

    Read from §1 ALONE. §2's verdict table carries a row per cell too, and
    it quotes the very clause under test -- so a scan of the whole document
    would end up comparing the instrument's output against itself, which is
    a check that passes because it stopped checking."""
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


def test_offenders_refuses_a_line_shaped_like_the_token():
    """This module's docstring claimed `offenders` re-checked the token
    before the check existed. A planted value -- the token's real shape,
    `sk-e16-` plus its alphabet -- has to be refused, or every claim about
    a committed artifact rests on the scrub having been remembered."""
    planted = "env: SENSORIUM_E16_TOKEN=sk-e16-" + "A1b2C3d4E5f6G7h8" * 2
    assert assemble_e16a.offenders(planted) == [planted]
    # ...and the record's own prose about the token's shape is not a hit:
    # a backtick where a token has its body.
    assert assemble_e16a.offenders(
        "The token was `sk-e16-` plus 33 characters") == []
    assert assemble_e16a.offenders("scrubbed to <token>") == []


# -- finding 2: §2 has to carry a dry-run reading --------------------------
def test_the_dry_run_block_renders_what_the_instrument_carried():
    out = assemble_e16a.dry_run_block(
        {"dry_run_findings": ["the versions phase moved ahead of grep",
                              "836 -> 842 files swept"]})
    assert "#### The dry run" in out
    assert "- 836 -> 842 files swept" in out


def test_the_dry_run_block_is_empty_when_the_instrument_carried_nothing():
    """Empty, not a sentence claiming there was no dry run: run 1 was
    measured before the field existed and carries a paragraph written by
    hand instead, which says so. A generated "no dry run" line would
    contradict the record it was appended to."""
    assert assemble_e16a.dry_run_block({}) == []
    assert assemble_e16a.dry_run_block({"dry_run_findings": []}) == []


# -- R37: the driver the run recorded with ---------------------------------
GOOD_BUILD = {"built": True, "seconds": 2.2, "binary": "…/cargo-sensorium",
              "cargo_target": "…", "mtime": 1789000000.0, "size": 7219088,
              "finished_line": "Finished `release` profile in 2.16s"}


def test_a_stamped_driver_build_reads_as_measured():
    out = e16a.read_driver_build(GOOD_BUILD)
    assert out["word"] == "measured"
    assert out["build"] is GOOD_BUILD


def test_the_versions_are_dropped_when_no_driver_build_was_stamped():
    """The failure this stamp exists for: run 1's H2 STOP was fixed in the
    tree, and a dry run against the unrebuilt binary still read the STOP. No
    version string in the block can tell a current driver from a stale one
    -- they come from the source tree or from a trace the stale binary
    wrote -- so an unstamped run drops the whole block rather than letting
    them read as a statement about the binary."""
    assert e16a.read_driver_build(None)["word"] == "dropped"
    assert e16a.read_driver_build({})["word"] == "dropped"
    rendered = assemble_e16a.versions_table({"versions": {}})
    assert len(rendered) == 1 and rendered[0].startswith("**Versions: dropped")
    assert "stale binary" in rendered[0]


def test_a_driver_build_missing_a_field_is_dropped_not_half_read():
    for field in ("built", "binary", "mtime", "size"):
        short = {k: v for k, v in GOOD_BUILD.items() if k != field}
        out = e16a.read_driver_build(short)
        assert out["word"] == "dropped", field
        assert field in out["why"], field


def test_a_driver_build_that_did_not_succeed_is_dropped():
    out = e16a.read_driver_build({**GOOD_BUILD, "built": False})
    assert out["word"] == "dropped"


def test_the_versions_table_names_the_binary_it_was_built_into():
    rendered = assemble_e16a.versions_table(
        {"driver_build": GOOD_BUILD,
         "versions": {"sensorium": "0.15.0", "recorder": {}, "tools": {},
                      "driver_version": {}}})
    assert rendered[0].startswith("**Driver built by the run (R37):**")
    assert "7219088 bytes" in rendered[0]
    assert "Finished `release` profile in 2.16s" in rendered[0]


# -- a re-measurement, beside the run before it ----------------------------
def _cells(**words):
    return {"cells": {c: {"word": w, "why": f"{c} why."}
                      for c, w in words.items()}}


def test_the_first_pass_line_names_the_run_that_first_passed():
    """§9's H1 clause asks the record to say which run is the first PASS
    after a fix; R30 extends that to H2 and H3. The earlier run's words are
    read out of its own results file, so this cannot claim a cell STOPped
    when the record beside it says otherwise."""
    now = _cells(H1="PASS", H2="PASS", H3="PASS", H6="PASS")
    was = _cells(H1="PASS", H2="STOP", H3="STOP", H6="PASS")
    out = "\n".join(assemble_e16a.first_pass_block(now, was))
    assert "H2 — this run is the first PASS" in out
    assert "H3 — this run is the first PASS" in out
    assert "passed in run 1 and reads **PASS** here" in out
    assert assemble_e16a.FIX_COMMITS["H2"] in out


def test_a_cell_that_stops_twice_is_told_it_has_no_first_pass_yet():
    now = _cells(H1="PASS", H2="STOP", H3="PASS", H6="PASS")
    was = _cells(H1="PASS", H2="STOP", H3="STOP", H6="PASS")
    out = "\n".join(assemble_e16a.first_pass_block(now, was))
    assert "H2 — still STOP, no first PASS yet" in out
    assert "H3 — this run is the first PASS" in out


def test_there_is_no_first_pass_block_for_a_first_run():
    assert assemble_e16a.first_pass_block(_cells(H1="PASS"), None) == []


def test_appending_refuses_a_record_that_was_never_measured(tmp_path):
    doc = tmp_path / "rec.md"
    doc.write_text("## 2. Part A\n\nNot yet measured.\n")
    with pytest.raises(assemble_e16a.Refused):
        assemble_e16a.append_into(doc, "### measured 2026-01-01 — run 2\n")


def test_appending_the_same_section_twice_is_refused(tmp_path):
    """An assembler run twice would otherwise leave two copies of one
    measurement in a document whose whole claim is that each was made
    once."""
    doc = tmp_path / "rec.md"
    doc.write_text("## 2. Part A\n\n### measured 2026-01-01\n\nrun 1.\n")
    section = "### measured 2026-01-02 — run 2\n\nrun 2.\n"
    assemble_e16a.append_into(doc, section)
    body = doc.read_text()
    assert body.index("### measured 2026-01-01") < body.index("run 2.")
    with pytest.raises(assemble_e16a.Refused):
        assemble_e16a.append_into(doc, section)


# -- the run label, at the value a re-measurement actually used ------------
def test_the_gated_roots_follow_the_run_label():
    """Run 2 measured into `store-a2`, and a cell whose expected roots still
    named `store-a` would have dropped H2 on a store that was swept. Pinned
    at `a2` and not only at the default, because the default is the one
    value that cannot catch a label that is ignored."""
    assert gated_roots("a2") == ("store-a2", "rust-target/sensorium/spool")
    assert gated_roots("a") == ("store-a", "rust-target/sensorium/spool")


def test_one_runs_gated_roots_never_name_another_runs_store():
    """The failure mode is silent in both directions: a first run gating on
    a second run's store would drop, and a second run gating on the first's
    would gate on files it did not make."""
    assert "store-a2" not in gated_roots("a")
    assert "store-a" not in gated_roots("a2")


def test_the_named_file_prefixes_follow_the_run_label():
    """H1's table lists the store's files one by one and summarises the
    rest. Keyed on the first run's store name, a re-measurement's own
    artifacts -- the rows §1 asks for BY NAME -- would have been counted
    into a single summary line."""
    assert assemble_e16a.named_prefixes({"label": "a2"}) == (
        "store-a2/", "rust-target/sensorium/spool/")
    assert assemble_e16a.named_prefixes({"label": "a"})[0] == "store-a/"
    # A raw record written before the label existed is run 1's.
    assert assemble_e16a.named_prefixes({})[0] == "store-a/"


def test_the_dry_run_sentence_prints_the_timers_that_were_used():
    """It said "every timer at 60 s" while the driver build's was 1800 --
    deliberately, because a cold `cargo build --release` says nothing about
    the instrument's plumbing. A record that rounds its own instrument's
    settings into a tidier sentence is one whose numbers a reader cannot
    use, so the phrase is built from the table."""
    phrase = assemble_e16a.dry_timer_phrase()
    assert "60 s" in phrase
    assert f"{e16a.DRY_TIMERS['build']} s for the driver build" in phrase
    assert "every timer at 60 s" not in phrase
    block = assemble_e16a.dry_run_block({"dry_run_findings": ["a finding"]})
    assert phrase in block[3]
