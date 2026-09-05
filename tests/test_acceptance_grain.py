"""The rung-4 entry-slice acceptance TOOLING, tested without the box.

Nothing here runs cargo or pytest, opens a kept trace store, reads anything
under `/mnt`, or needs an environment variable to be set by whoever launched
pytest. Every trace this module reads it built itself in `tmp_path`; the one
real file it opens is the COMMITTED E6⁗ `results.json`, which is the oracle
and lives in this repository.

What it tests is the places this run could report a wrong number while every
command it ran succeeded:

* the §1 byte-lock -- a lock that compared the wrong slice, that passed on a
  changed §1, or that fell through while `BYTE_LOCK` is still `None`, lets an
  endpoint move after a number is read;
* the SHAPE PARSER -- H2, H3 and H4 all count chains out of a bracket, and a
  parser that read a missing bracket as 0, or `[in <run>]` as anything but
  one chain in a named process, would move every count it feeds;
* the ORACLE -- the published record is read, never re-measured, and a
  process that printed NO tally line is `None` there, not a zero: summing it
  as `swallowed 0` would invent 30 measurements per arm;
* the SITE COMPARISON -- `compare_sites` is the whole of H2 and H4, and one
  that ignored a count difference would pass a view that found the right 91
  sites with the wrong 782 lines;
* the sqlite join -- the verdict names a qualname and a line, the record
  names a FILE, and only the trace's own `events` -> `code_objects` join
  bridges them;
* none-versus-zero -- a phase that did not run is `null` with a reason, and
  no headline may ever be filled from the oracle, which is the one number in
  the room that is already known.

Every test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_grain as runner                                  # noqa: E402
import acceptance_grain_phases as phases                           # noqa: E402
import acceptance_grain_read as read                               # noqa: E402
import acceptance_lib as lib                                       # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
import render_grain                                                # noqa: E402
from acceptance_grain_schema import assemble_grain                 # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

# Importing this runner re-points the SHARED log pointers at THIS document's
# workspace (its job). `tests/test_acceptance_e6q.py` and `..._e6ppp.py`
# assert the same invariant for THEIR runners and all of them are imported at
# COLLECTION time, so whichever pytest collected last would own the pointer
# and a sibling assertion would fail on collection order alone. Restoring
# E6‴'s pointers here makes every suite order-independent and costs nothing:
# each phase runs inside a `logs_at` block.
lib.LOGS, lib.LEDGER, ph.LOGS = e6ppp.LOGS, e6ppp.LEDGER, e6ppp.LOGS


# -- the byte-lock on the new document -------------------------------------


def _require_lock_commits(*shas):
    """The real-document lock tests read `git show <sha>:<doc>`; a shallow
    checkout has no such commit, and before this task's last step there is no
    lock sha at all. Skip BY NAME rather than pass on a missing commit -- a
    skipped lock check must never look like a passed one."""
    import subprocess
    for sha in shas:
        if not sha:
            pytest.skip("§1 is not locked yet (BYTE_LOCK is None) -- the "
                        "byte-lock test is skipped BY NAME, not passed")
        ok = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                            cwd=REPO, capture_output=True).returncode == 0
        if not ok:
            pytest.skip(f"lock commit {sha} is not in this checkout "
                        "(shallow clone) -- the byte-lock test is skipped "
                        "BY NAME, not passed")


def test_the_grain_byte_lock_passes_on_the_real_document():
    """The same comparison the runner refuses on, run in the suite so a stray
    edit to §1 is caught before a run is launched rather than by a refusal
    with a store already read."""
    _require_lock_commits(runner.BYTE_LOCK)
    rec = rung3.byte_lock_check(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["identical"] is True


def test_the_grain_lock_is_one_sha_and_records_no_amendment():
    """§1 of this document is committed once and never amended. A record that
    silently reported an amendment would be describing another document."""
    _require_lock_commits(runner.BYTE_LOCK)
    assert runner.ORIGINAL_LOCK is None
    rec = rung3.byte_lock_facts(runner.DOC, runner.BYTE_LOCK,
                                runner.ORIGINAL_LOCK)
    assert rec["amended_after_the_original_lock"] is False
    assert rec["original_lock_sha256"] is None
    # No footnote is referenced by this §1, so the extended range and §1 are
    # the same bytes -- asserted, because a footnote added later would
    # silently widen the locked range.
    assert rec["footnotes_in_range"] == []
    assert rec["locked_sha256"] == rec["section1_sha256"]


def test_the_grain_byte_lock_REFUSES_a_document_that_differs_by_one_byte(
        tmp_path):
    """The refusal path itself. A check that computes two shas, reports them
    unequal and proceeds is not a lock."""
    if not runner.DOC.is_file():
        pytest.skip("the acceptance document does not exist yet (§1 is "
                    "committed ALONE by a later step) -- skipped BY NAME, "
                    "not passed")
    text = runner.DOC.read_text()
    moved = text.replace("**20 of 20 equal**", "**19 of 20 equal**", 1)
    assert moved != text, "the §1 phrase this test moves is gone"
    doc = tmp_path / "moved.md"
    doc.write_text(moved)
    with pytest.raises(Refused):
        rung3.byte_lock_check(doc, "aaaaaaa", None, lambda rel, commit: text)


def test_the_runner_REFUSES_to_measure_while_section_1_is_unlocked(
        monkeypatch):
    """The state this file is committed in: the tooling exists and §1 does
    not. A `None` lock that fell through to "no commit to compare with" would
    measure against a pre-registration that could still be edited."""
    monkeypatch.setattr(runner, "BYTE_LOCK", None)
    with pytest.raises(Refused) as e:
        runner.check_byte_lock()
    assert "not locked" in str(e.value)


# -- the shape parser ------------------------------------------------------

#: One hand-written answer carrying all four bracket forms the shipped
#: renderers can print (`exceptions_group.bracket`, `exceptions_invocation.
#: bracket`). The two modes never appear in one real answer; they do here
#: because what is under test is the PARSER, and a parser that needed to be
#: told which mode it was reading would need a caller that always knew.
FOUR_FORMS = """\
raised (15):
  e340 HANDLED tests::fresh_dir handled io::Error('NotFound') L156
    SWALLOWED -- absorbed by sink_let_underscore at e340 (tests::fresh_dir L156) in f171, which returned ok
      born outside this thread's instrumented frames; absorbed at sink_let_underscore
  e4 RAISE attempt raised Refused(1) L14
    ambiguous -- an Err(..) arm at e6 (retry L27) bound it to a name and let the name escape  [×4: e1, e2, e3, e4]
      messages: 2 distinct (first shown)
  e1204 HANDLED Server::serve handled io::Error('WouldBlock') L236
    SWALLOWED -- absorbed by arm_handled at e1204 (Server::serve L236) in f88, which returned ok  [×9 over 3 processes: first e7 in r1, +8]
      routes: 4 distinct (first shown)
  e2 HANDLED usable_window handled io::Error('X') L192
    SWALLOWED -- absorbed by sink_unwrap_or at e2 (usable_window L192) in f1, which returned ok  [in r2]
dispositions: swallowed 14, ambiguous 8
"""


def test_parse_shapes_reads_every_bracket_form_as_a_chain_count():
    """H2, H3 and H4 all add these numbers up. `[×4: …]` is four chains,
    `[×9 over 3 processes: …]` is nine, and both bracketless forms are
    ONE -- a group of one in single-run mode, and a shape seen once in an
    invocation answer, which still names its process (ruling R-G9)."""
    shapes = runner.parse_shapes(FOUR_FORMS)
    assert [s["n"] for s in shapes] == [1, 4, 9, 1]
    assert [s["tag"] for s in shapes] == ["SWALLOWED", "ambiguous",
                                          "SWALLOWED", "SWALLOWED"]
    assert [s["first_origin"] for s in shapes] == [None, 1, 7, None]
    assert [s["run"] for s in shapes] == [None, None, "r1", "r2"]
    assert [s["processes"] for s in shapes] == [None, None, 3, 1]


def test_a_block_with_no_bracket_is_one_chain_and_never_zero():
    """MUTANT: a parser that reads "no bracket" as 0 would drop every group
    of one -- five of E6⁗-A's fourteen lines and most of the 782 -- and
    still print a total, so the miss would look like a real number."""
    shapes = runner.parse_shapes(FOUR_FORMS)
    bare = shapes[0]
    assert bare["n"] == 1
    assert bare["bracket"] is None
    assert sum(s["n"] for s in runner.swallowed_shapes(FOUR_FORMS)) == 11


def test_the_in_run_bracket_is_one_chain_in_a_named_process():
    """MUTANT: `[in r2]` read as 0, or as `×2` because it is a bracket,
    moves H4's per-site counts. It is exactly one chain, and the run it names
    is the trace H4 must resolve its site in."""
    shapes = runner.parse_shapes(FOUR_FORMS)
    once = shapes[3]
    assert once["n"] == 1
    assert once["run"] == "r2"
    assert once["processes"] == 1
    assert once["bracket"] == "  [in r2]"


def test_parse_shapes_reads_the_site_the_verdict_names():
    """The event id in the verdict is the SINK for a swallow -- the id the
    E6⁗ record's own collector resolved to a file. The bracket's ids are
    ORIGINS. A parser that returned one field for both would resolve origins
    against a sink-keyed table and find nothing."""
    shapes = runner.parse_shapes(FOUR_FORMS)
    assert [s["event"] for s in shapes] == [340, 6, 1204, 2]
    assert [s["qualname"] for s in shapes] == [
        "tests::fresh_dir", "retry", "Server::serve", "usable_window"]
    assert [s["site_line"] for s in shapes] == [156, 27, 236, 192]


def test_parse_shapes_attributes_each_vary_line_to_its_own_block():
    """The ungated honesty count of §1: how many groups flagged a difference
    the key did not look at. A vary line counted against the wrong block
    would say the tool flagged a shape it did not."""
    shapes = runner.parse_shapes(FOUR_FORMS)
    assert shapes[1]["vary"] == ["messages: 2 distinct (first shown)"]
    assert shapes[2]["vary"] == ["routes: 4 distinct (first shown)"]
    assert shapes[0]["vary"] == [] and shapes[3]["vary"] == []
    assert runner.vary_counts(FOUR_FORMS) == {"messages": 1, "routes": 1}


def test_parse_shapes_reads_no_shape_out_of_a_header_or_a_tally():
    """`raised (…)`, `dispositions: …` and the paging note are not blocks. A
    parser that took the tally line for a verdict would count a shape per
    answer and add it to every arm."""
    shapes = runner.parse_shapes(
        "raised (0):\ndispositions: swallowed 3\n"
        "... 2 more; continue with: sensorium exceptions r1 --limit 5\n")
    assert shapes == []


# -- the header parser -----------------------------------------------------

INVOCATION = """\
invocation 20260905-091115-9e8e5a: cargo test --workspace -- 3 processes, 2 with Err chains, 1 with none
INCOMPLETE: r3 never finalized -- its Err chains after the cut are not below
raised (10 chains over 2 processes, 2 swallowing sites):
  e2 HANDLED usable_window handled io::Error('X') L192
    SWALLOWED -- absorbed by sink_unwrap_or at e2 (usable_window L192) in f1, which returned ok  [in r2]
dispositions: swallowed 10, ambiguous 3
"""


def test_parse_header_reads_the_invocation_counts():
    """H4's gate is `144 / 114 / 30`. A header read loosely -- or not at all
    -- would leave that endpoint decided by the site table alone."""
    h = runner.parse_header(INVOCATION)
    assert h["invocation"] == "20260905-091115-9e8e5a"
    assert h["cargo"] == "test --workspace"
    assert (h["processes"], h["with_chains"], h["without_chains"]) == (3, 2, 1)
    assert h["chains"] == 10 and h["swallowing_sites"] == 2
    assert h["tally_line"] == "dispositions: swallowed 10, ambiguous 3"
    assert h["tally"] == {"swallowed": 10, "ambiguous": 3}


def test_parse_header_names_every_incomplete_member():
    """§1's H4 gate includes `INCOMPLETE members 0`. An incomplete member is
    a gap in the whole answer, so it is counted by name, never by absence."""
    h = runner.parse_header(INVOCATION)
    assert h["incomplete"] == ["r3"]


def test_a_single_run_answer_has_no_invocation_header():
    """H3 reads 288 single-run answers with the same function. A parser that
    invented an invocation line for them would report 288 invocations."""
    h = runner.parse_header(FOUR_FORMS)
    assert h["invocation"] is None
    assert h["processes"] is None
    assert h["chains"] == 15
    assert h["tally"] == {"swallowed": 14, "ambiguous": 8}


def test_an_answer_with_no_chains_is_recorded_as_such_not_as_zero_chains():
    """The 30 + 30 processes that print `no exceptions recorded`. The oracle
    holds `None` for their tally line, and the measurement must say the same
    shape rather than `swallowed 0`."""
    h = runner.parse_header("no exceptions recorded\n")
    assert h["empty"] is True and h["tally_line"] is None
    assert h["chains"] is None
    inv = runner.parse_header("invocation i1: cargo test -- 2 processes, 0 "
                              "with Err chains, 2 with none\n"
                              "no exceptions recorded across 2 processes\n")
    assert inv["empty"] is True and inv["with_chains"] == 0


# -- the oracle ------------------------------------------------------------


def _fake_record(tmp_path) -> Path:
    """A tiny `results.json` in the published record's shape: one primary
    process with its own SWALLOWED lines, two swept processes, one of which
    printed no tally line at all."""
    def sw(file, line, run=None):
        row = {"line": "SWALLOWED -- …", "event": 1,
               "sink": {"file": file, "line": line}}
        if run:
            row["run"] = run
        return row
    doc = {"endpoints": {
        "E6qA": {"run": "p0", "tally_line": "dispositions: swallowed 2",
                 "swallowed": [sw("a.rs", 10), sw("a.rs", 10)],
                 "swallowed_sweep": [], "sweep_processes": []},
        "E6qWS": {"run": "p1", "tally_line": "dispositions: swallowed 1",
                  "swallowed": [sw("x.rs", 5)],
                  "swallowed_sweep": [sw("x.rs", 5, "p2"),
                                      sw("y.rs", 7, "p2")],
                  "sweep_processes": [
                      {"run": "p2", "swallowed_count": 2, "stdout_bytes": 40,
                       "tally_line": "dispositions: swallowed 2, ambiguous 1"},
                      {"run": "p3", "swallowed_count": 0, "stdout_bytes": 12,
                       "tally_line": None}]},
        "E6qWS0": {"run": "q1", "tally_line": None, "swallowed": [],
                   "swallowed_sweep": [], "sweep_processes": []}}}
    p = tmp_path / "fake.results.json"
    p.write_text(json.dumps(doc))
    return p


def test_oracle_reads_the_primary_and_the_sweep_into_one_site_table(tmp_path):
    """The record splits the primary process's SWALLOWED lines from the
    sweep's. An oracle that read only one half would compare H4's 782 lines
    against 1."""
    orc = runner.oracle(_fake_record(tmp_path))
    assert orc["a"] == Counter({("a.rs", 10): 2})
    assert orc["ws"] == Counter({("x.rs", 5): 2, ("y.rs", 7): 1})
    assert orc["lines"]["ws"] == 3 and orc["sites"]["ws"] == 2


def test_oracle_keeps_a_process_that_printed_no_tally_line_as_None(tmp_path):
    """MUTANT: a process with no tally line recorded as `swallowed 0`, or
    dropped from the map entirely. The record's `None` means "this process
    printed `no exceptions recorded`" -- 30 processes per arm -- and H3
    checks for that SHAPE, not for a zero."""
    orc = runner.oracle(_fake_record(tmp_path))
    assert orc["per_process"]["ws"] == {
        "p1": "dispositions: swallowed 1",
        "p2": "dispositions: swallowed 2, ambiguous 1",
        "p3": None}
    assert orc["tally_lines"]["ws"] == 2
    assert orc["without_a_tally_line"]["ws"] == 1


def test_oracle_sums_only_the_tally_lines_that_were_printed(tmp_path):
    """MUTANT: summing a `None` as zero. `swallowed` would appear in the sum
    of an arm where no process ever printed it, and the summed tally is
    exactly what H4's gate compares."""
    orc = runner.oracle(_fake_record(tmp_path))
    assert orc["tallies"]["ws"] == {"swallowed": 3, "ambiguous": 1}
    assert orc["tallies"]["ws0"] == {}
    assert orc["tally_lines"]["ws0"] == 0
    assert orc["swallowed_count"]["ws"] == {"p1": 1, "p2": 2, "p3": 0}


def test_oracle_on_the_PUBLISHED_record_reproduces_the_ledgers_numbers():
    """The oracle is the committed E6⁗ record and nothing else. These are the
    numbers Task 0 extracted into the ledger before this design was written;
    an oracle that read the record differently would move every gate."""
    orc = runner.oracle(runner.ORACLE)
    assert orc["sites"] == {"a": 5, "ws": 91, "ws0": 98}
    assert orc["lines"] == {"a": 14, "ws": 782, "ws0": 812}
    assert orc["tally_lines"] == {"a": 1, "ws": 114, "ws0": 114}
    assert orc["processes"] == {"a": 1, "ws": 144, "ws0": 144}
    assert orc["tallies"]["a"] == {"swallowed": 14, "ambiguous": 8}
    assert orc["tallies"]["ws"] == {"swallowed": 782, "ambiguous": 330,
                                    "panicked": 2}
    assert orc["tallies"]["ws0"] == {"swallowed": 812, "ambiguous": 300,
                                     "panicked": 2}
    assert orc["runs"]["a"] == "20260905-091115-5da3dc"


def test_the_0_8_1_bytes_of_the_busiest_ws_process_come_from_the_record():
    """§1 reports the busiest process's output before and after. The BEFORE
    is the record's, never re-measured: 0.8.1 is not installed here."""
    orc = runner.oracle(runner.ORACLE)
    assert orc["stdout_bytes"]["ws"][runner.BUSIEST_WS_RUN] == 20166
    assert orc["swallowed_count"]["ws"][runner.BUSIEST_WS_RUN] == 54


# -- the site comparison ---------------------------------------------------


def test_compare_sites_is_not_equal_when_a_count_differs():
    """MUTANT: a comparison that checks the site SET and not the counts. H4
    would pass a view that found the record's 91 sites and put 500 lines
    under them -- the exact failure grouping could introduce."""
    got = runner.compare_sites(Counter({("a.rs", 1): 3}),
                               Counter({("a.rs", 1): 4}))
    assert got["equal"] is False
    assert got["count_diffs"] == [{"site": ("a.rs", 1), "measured": 3,
                                   "expected": 4}]
    assert got["missing"] == [] and got["extra"] == []


def test_compare_sites_reports_missing_and_extra_sites_apart():
    """A site the record has and the view does not is a MISS; the other way
    round is a false accusation. They are different failures and are never
    added together."""
    got = runner.compare_sites(Counter({("a.rs", 1): 1, ("b.rs", 2): 1}),
                               Counter({("a.rs", 1): 1, ("c.rs", 3): 1}))
    assert got["equal"] is False
    assert got["extra"] == [{"site": ("b.rs", 2), "measured": 1}]
    assert got["missing"] == [{"site": ("c.rs", 3), "expected": 1}]


def test_compare_sites_is_equal_only_on_an_identical_multiset():
    c = Counter({("a.rs", 1): 3, ("b.rs", 2): 1})
    got = runner.compare_sites(Counter(c), Counter(c))
    assert got["equal"] is True
    assert got["differences"] == 0
    assert got["measured_lines"] == 4 and got["expected_lines"] == 4


# -- the sqlite join -------------------------------------------------------


def _trace(tmp_path, run_id="r1", rows=((1, 156, 10), (2, 606, 20))):
    """A trace with just the two tables the join reads."""
    d = tmp_path / "traces"
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / f"{run_id}.db")
    con.execute("create table code_objects (id integer primary key, "
                "file text, qualname text)")
    con.execute("create table events (id integer primary key, line integer, "
                "code_id integer)")
    con.execute("insert into code_objects values (10, '/w/memory.rs', 'f')")
    con.execute("insert into code_objects values (20, '/w/exec.rs', 'g')")
    for eid, line, code in rows:
        con.execute("insert into events values (?,?,?)", (eid, line, code))
    con.commit()
    con.close()
    return d / f"{run_id}.db"


def test_site_of_event_joins_the_event_to_its_file(tmp_path):
    """The verdict names `tests::fresh_dir L156`; the record names
    `/w/memory.rs:156`. Only this join bridges them, and without it H2 and H4
    compare a qualname against a path and find 91 missing sites."""
    db = _trace(tmp_path)
    assert runner.site_of_event(db, 1) == ("/w/memory.rs", 156)
    assert runner.site_of_event(db, 2) == ("/w/exec.rs", 606)


def test_an_event_the_trace_does_not_hold_is_not_a_site(tmp_path):
    """An unresolved sink is a HOLE in the evidence, reported as such. A
    `(None, None)` folded into the multiset would be a 92nd site."""
    db = _trace(tmp_path)
    assert runner.site_of_event(db, 999) == (None, None)


def test_sites_of_events_reads_every_id_in_one_pass(tmp_path):
    """782 lines over 144 traces: one query per trace, the two-line join of
    `acceptance_phases_rung3._sink_files`."""
    db = _trace(tmp_path)
    got = runner.sites_of_events(db, [1, 2, 999])
    assert got == {1: ("/w/memory.rs", 156), 2: ("/w/exec.rs", 606)}


# -- none versus zero, in the schema ---------------------------------------


def _raw(**over) -> dict:
    raw = {"runner": "rust/tests/acceptance_grain.py",
           "oracle": runner.oracle(runner.ORACLE)}
    raw.update(over)
    return raw


def test_a_phase_that_did_not_run_is_null_with_a_reason():
    """The schema's one rule. A phase absent from the raw record must reach
    the document as `not measured (<why>)`, never as a dash or a zero."""
    doc = assemble_grain(_raw())
    for key in ("H1", "H2", "H3", "H4", "H5", "H6"):
        m = doc["endpoints"][key]["headline"]
        assert m["value"] is None, key
        assert m["dropped"], key


def test_H4s_headline_is_never_filled_from_the_oracle():
    """MUTANT: the schema falling back to the oracle when the measurement is
    absent. The oracle already holds 91 sites and 782 lines; a headline that
    quietly took them would report the record as its own measurement and H4
    could not fail."""
    doc = assemble_grain(_raw())
    h4 = doc["endpoints"]["H4"]
    assert h4["headline"]["value"] is None
    assert "not measured" not in str(h4["headline"]["value"])
    for arm in ("ws", "ws0"):
        assert h4["arms"][arm]["site_differences"]["value"] is None
        assert h4["arms"][arm]["site_differences"]["dropped"]
    # ...while the oracle it was NOT allowed to borrow from is published
    # beside it, under its own name.
    assert doc["oracle"]["sites"] == {"a": 5, "ws": 91, "ws0": 98}


def test_a_measured_zero_is_a_measured_zero():
    """The other half of the rule: 0 differences is the PASS, and it must not
    read as not-measured."""
    doc = assemble_grain(_raw(raw_h2={
        "run": "r1", "rc": 0, "wall": 1.0, "groups": 5, "chains": 14,
        "compare": {"equal": True, "differences": 0, "missing": [],
                    "extra": [], "count_diffs": [], "measured_lines": 14,
                    "expected_lines": 14},
        "tally_line": "dispositions: swallowed 14, ambiguous 8",
        "tally_line_equal": True, "unresolved_sinks": 0}))
    m = doc["endpoints"]["H2"]["headline"]
    assert m["value"] == 0 and m["dropped"] == []


# -- the renderer ----------------------------------------------------------


def test_the_renderer_prints_not_measured_with_the_reason():
    """A null that rendered as a dash, an empty cell or a 0 would publish a
    phase that did not run as one that found nothing."""
    doc = assemble_grain(_raw())
    text = "\n".join(render_grain.results(doc))
    assert "not measured (" in text
    assert "| — |" not in text


def test_the_renderer_prints_a_measured_zero_as_zero():
    doc = assemble_grain(_raw(raw_h2={
        "run": "r1", "rc": 0, "wall": 1.0, "groups": 5, "chains": 14,
        "compare": {"equal": True, "differences": 0, "missing": [],
                    "extra": [], "count_diffs": [], "measured_lines": 14,
                    "expected_lines": 14},
        "tally_line": "dispositions: swallowed 14, ambiguous 8",
        "tally_line_equal": True, "unresolved_sinks": 0}))
    line = [ln for ln in render_grain.results(doc) if ln.startswith("| H2 |")]
    assert line and "| 0 (rule:" in line[0], line


# -- the locations this run touches ----------------------------------------


def test_the_four_locations_are_refused_TOGETHER_when_unset(monkeypatch):
    """One launch reports every missing variable, not one per attempt. A run
    launched with the stores set and the corpus target not would refuse only
    after H2, H3 and H4 had already read the stores."""
    for k in runner.GRAIN_ENV:
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(Refused) as e:
        runner.env_paths_grain()
    for k in runner.GRAIN_ENV:
        assert k in str(e.value)


def test_each_arm_reads_its_own_kept_store_and_H1_records_into_neither(
        tmp_path):
    """The kept stores are the INPUTS. An arm pointed at the wrong one would
    compare `ws0`'s traces against `ws`'s table; a corpus recording landing
    in one would change the evidence the record cites."""
    p = {"e6q_stores": tmp_path / "e6q", "sensorium_dir": tmp_path / "fresh"}
    dirs = {label: runner.store_paths(p, label)["sensorium_dir"]
            for label in ("a", "ws", "ws0")}
    assert len(set(dirs.values())) == 3
    for label, d in dirs.items():
        assert d == p["e6q_stores"] / label
        assert d != p["sensorium_dir"]


def test_a_killed_answer_is_recorded_as_a_kill_and_not_raised(
        tmp_path, monkeypatch):
    """H5's ceiling. A `TimeoutExpired` that escaped would take H1 and H6
    down with it and lose four measured endpoints to one slow answer, so the
    kill is a FACT of the record: the wall, whatever the command had printed
    before it fired, and a log of its own — `acceptance_lib.run` writes its
    log only after the call returns, so a killed command otherwise leaves no
    evidence at all."""
    import subprocess

    def killed(*a, **k):
        # BYTES, which is what `subprocess.run(text=True)` attaches on some
        # platforms -- and the branch that decodes them is the one that
        # carried the `LookupError` this test was written for.
        raise subprocess.TimeoutExpired(["sensorium"], 60,
                                        output=b"partial\n")

    # Patched on the PHASES module, not on the front door: `acceptance_grain`
    # re-exports `_ask` by NAME, and `_ask` resolves `sensorium_cli` in the
    # namespace it was defined in. Patching the re-export would leave the
    # real command in place -- the same lesson as E6‴ §2's `logs_at`.
    monkeypatch.setattr(phases, "sensorium_cli", killed)
    monkeypatch.setattr(lib, "LOGS", tmp_path / "logs")
    p = {"e6q_stores": tmp_path / "e6q", "sensorium_dir": tmp_path / "fresh"}
    res = runner._ask(p, "ws", "inv", {"limit": 10, "cli_timeout": 99},
                      "h4-ws", kill=60)
    assert res["timed_out"] is True
    assert res["rc"] is None
    assert res["out"] == "partial\n"
    assert res["stdout_bytes"] == 8
    assert Path(res["log"]).is_file()
    assert "KILLED at 60 s" in Path(res["log"]).read_text()


def test_no_module_of_this_instrument_names_a_box_path():
    """Every location is an environment variable. A path compiled into the
    runner would make the record unreproducible and the file wrong on any
    other machine."""
    for name in ("acceptance_grain.py", "acceptance_grain_read.py",
                 "acceptance_grain_phases.py", "acceptance_grain_schema.py",
                 "render_grain.py"):
        text = (REPO / "rust" / "tests" / name).read_text()
        assert "/mnt/" not in text, name
        assert "/home/" not in text, name

# -- fix round 1: the record must survive being written --------------------


def test_the_whole_raw_record_and_the_assembled_document_serialise():
    """The round trip the runner's LAST act depends on.

    `oracle()`'s per-arm tables are keyed by `(file, line)` TUPLES, and
    `json.dumps` cannot write a tuple KEY at all -- `default=` applies to
    values only, so nothing rescues it. Storing them raw made the raw-json
    write raise `TypeError` after an hour of measurement, losing the record,
    the `results.json` AND both markers. `oracle_json` is what the runner
    stores, and this asserts the whole shape goes out and comes back."""
    raw = {"runner": "rust/tests/acceptance_grain.py",
           "oracle": runner.oracle_json(runner.oracle(runner.ORACLE)),
           "config": {"oracle_record": "x", "oracle_commit": "y"},
           "pins": {}, "cleanup": {}}
    text = json.dumps(raw, indent=2, default=str)
    assert json.loads(text)["oracle"]["ws"], "the ws site table is empty"
    doc = assemble_grain(raw)
    back = json.loads(json.dumps(doc, indent=2, default=str))
    assert back["oracle"]["sites"] == {"a": 5, "ws": 91, "ws0": 98}


def test_the_oracles_site_tables_are_stringified_and_keep_every_count():
    """`"<file>:<line>"`, and the same multiset. A projection that lost a
    site or merged two would move H2's and H4's expected tables."""
    orc = runner.oracle(runner.ORACLE)
    js = runner.oracle_json(orc)
    for arm in ("a", "ws", "ws0"):
        assert all(isinstance(k, str) for k in js[arm]), arm
        assert len(js[arm]) == len(orc[arm]), arm
        assert sum(js[arm].values()) == sum(orc[arm].values()), arm
    assert js["ws"][
        "/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-core/src/"
        "geometry.rs:192"] > 0


def test_a_record_with_one_unwritable_value_still_writes_the_rest():
    """The fallback the guarded write uses. A run that measured for an hour
    must lose the one value a serialisation defect touched, not all of them,
    and a reader must be told which key went."""
    text = runner._partial_json({"started": "t", "bad": {("a", 1): 2},
                                 "steps": ["one"]})
    got = json.loads(text)
    assert got["started"] == "t" and got["steps"] == ["one"]
    assert got["keys_that_could_not_be_serialised"] == ["bad"]
    assert "bad" not in got


# -- fix round 1: the ungated vary count is over EVERY answer ---------------


def _vary_fixture():
    h2 = {"vary": {"origins": 1}}
    h3 = {"arms": {"ws": {"vary": {"messages": 2}, "rows": [],
                          "stdout_bytes_total": 9, "stdout_lines_total": 3,
                          "processes": 144},
                   "ws0": {"vary": {"routes": 4}, "rows": []}}}
    h4 = {"arms": {"ws": {"vary": {"details": 8}, "stdout_bytes": 5,
                          "stdout_lines": 2},
                   "ws0": {"vary": {"origins": 16}}}}
    return h2, h3, h4


def test_the_vary_count_sums_every_answer_this_run_read():
    """MUTANT: an arm left out of the sum. The first draft counted H2, both
    H3 arms and H4's `ws` -- `ws0`'s invocation answer, one of the two the
    slice exists to produce, was silently outside the total, and a partial
    sum published as a total is a wrong number, not a missing one."""
    h2, h3, h4 = _vary_fixture()
    rep = runner.reported({"busiest_ws_run": runner.BUSIEST_WS_RUN},
                          runner.oracle(runner.ORACLE), h2, h3, h4)
    assert rep["vary_lines_by_kind"] == {"origins": 17, "messages": 2,
                                         "routes": 4, "details": 8}
    assert rep["vary_counted_over"] == ["H2", "H3/ws", "H3/ws0", "H4/ws",
                                        "H4/ws0"]
    # the cell names the set it summed, so a reader can see what is in it
    for name in rep["vary_counted_over"]:
        assert name in rep["vary_lens"]


# -- fix round 1: no fallback run in invocation mode ------------------------

UNBRACKETED_INVOCATION = """\
invocation i1: cargo test --workspace -- 2 processes, 2 with Err chains, 0 with none
raised (2 chains over 2 processes, 2 swallowing sites):
  e1 HANDLED f handled io::Error('x') L156
    SWALLOWED -- absorbed by sink_ok at e1 (f L156) in f1, which returned ok
  e2 HANDLED g handled io::Error('y') L606
    SWALLOWED -- absorbed by sink_ok at e2 (g L606) in f2, which returned ok  [in r1]
dispositions: swallowed 2
"""


def test_an_invocation_block_that_names_no_process_is_unresolved(tmp_path):
    """MUTANT: falling back to the primary run. In invocation mode EVERY
    block carries a bracket naming its process (R-G9), so a block without one
    is a bracket the parser could not read -- and looking its sink id up in
    the FIRST member's trace returns a REAL but WRONG `(file, line)`. A wrong
    site is worse than a missing one: nothing downstream can tell it from a
    measurement. Here e1 EXISTS in `r1` at `/w/memory.rs:156`, so the
    fallback would have booked exactly that."""
    _trace(tmp_path, "r1")
    store = {"sensorium_dir": tmp_path}
    m = runner.measure_sites(store, UNBRACKETED_INVOCATION, "r1")
    assert m["unresolved_count"] == 1, m
    assert m["unresolved"][0]["event"] == 1
    assert m["unresolved"][0]["run"] is None
    assert m["unresolved"][0]["why"]
    assert dict(m["sites"]) == {("/w/exec.rs", 606): 1}, m
    assert ("/w/memory.rs", 156) not in m["sites"], "the fallback fired"


def test_a_single_run_answer_still_uses_the_run_it_was_asked_about(tmp_path):
    """The other half: single-run mode has exactly one trace, the ref the
    reader typed, and a bare block there is a group of one -- so the default
    run is right and must still be used."""
    _trace(tmp_path, "r1")
    single = ("raised (1):\n"
              "  e1 HANDLED f handled io::Error('x') L156\n"
              "    SWALLOWED -- absorbed by sink_ok at e1 (f L156) in f1, "
              "which returned ok\n"
              "dispositions: swallowed 1\n")
    m = runner.measure_sites({"sensorium_dir": tmp_path}, single, "r1")
    assert m["unresolved_count"] == 0, m
    assert dict(m["sites"]) == {("/w/memory.rs", 156): 1}, m


# -- fix round 1: both INCOMPLETE spellings --------------------------------


def test_the_single_run_incomplete_banner_is_reported(tmp_path):
    """`caps.print_incomplete`'s banner names no process, because the ref the
    reader typed IS the process, and the member regex does not match it
    (checked 2026-09-05). H2 and H3 could not report a truncated recording at
    all until this was read: an empty answer on a run that never finalized
    reports where the RECORDING ended, not what the program did."""
    banner = ("INCOMPLETE: this recording never finalized, so it may stop "
              "mid-run\n  its Err chains after the cut are not below\n"
              "no exceptions recorded\n")
    h = runner.parse_header(banner)
    assert h["incomplete_banner"] is True
    # ...and it is NOT mistaken for a named member of an invocation
    assert h["incomplete"] == []
    assert h["empty"] is True


def test_a_named_member_is_not_mistaken_for_the_banner():
    h = runner.parse_header(INVOCATION)
    assert h["incomplete"] == ["r3"]
    assert h["incomplete_banner"] is False
