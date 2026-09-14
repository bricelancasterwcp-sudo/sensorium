"""E16 part B's CELLS, on hand-built inputs.

Three cells decide part B -- H1-values (the token's bytes, as OCCURRENCES,
in the four places §1's amendment names), H5 (the overhead tables before and
after, never gated) and H6-values (`values redacted:` equals the planted
count on every arm). Each is a pure function over rows somebody could type
by hand, and this module is the only place they are exercised against inputs
somebody chose: the measurement runs once, and a decision function first
seen on the day of the run is a decision function nobody has ever watched
refuse.

WHAT IS BEING PREVENTED, CELL BY CELL
-------------------------------------
* **a cell that cannot STOP.** Every cell here has a passing input AND a
  failing one differing in one field, and the failing one names the row it
  failed over.
* **a hole read as a pass.** `None` is what `e16b.py` writes for anything it
  did not measure, and an EMPTY list is what a sweep over a mistyped root
  produces. Both are `dropped`, never PASS -- H1-values' three zero
  readings are all vacuously true over nothing, which is exactly how a
  mistyped path would publish as a clean sweep.
* **a bench regex that reads the wrong line.** `BENCH_ROW` is pinned
  against a line built by `corpus._bench.bench._row` itself, and against the
  four non-row lines `report` prints around it -- a header whose second
  field is `tier`, an `n/a` line for a workload with no focus target, the
  fixed-cost line and the best-of-N line. A regex that matched any of those
  would put a number into §3 that is not a measurement.
* **a probe whose rows are not the pre-registered ones.** §1's amendment
  counts five rows in Python and four in each of Rust and TypeScript, and
  names every one of them. The probe sources are held against that list
  here, statically: a probe edited to drop its `print` or rename `copy`
  would otherwise change what the census means while the number in the
  record stayed 5.
* **a verdict word invented here.** `RULES` is §9's own PASS/STOP column for
  H1, H5 and H6, checked by equality against the record on disk.

The bench tables below are built by `bench._row` rather than typed, so a
change to the printed format reddens here rather than silently ceasing to
parse on the day of the run.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "acceptance_e16"))
sys.path.insert(0, str(REPO / "rust" / "tests"))

from corpus._bench import bench                                   # noqa: E402

import assemble_e16b                                              # noqa: E402
import e16b_cells                                                 # noqa: E402
from e16b_cells import (ARMS, BASELINE, BENCH_REPS,               # noqa: E402
                        BENCH_ROW, DRY_NAME_ROWS, EXPECTED_VALUES,
                        PROBES, RULES, SPOOL_OCCURRENCES, TOKEN_VAR,
                        cell_h1_values, cell_h5, cell_h6_values,
                        parse_bench, part_word)

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-13-sensorium-e16-redaction.md")


# -- H1-values: the token's OCCURRENCES, per file --------------------------
def _rows(*pairs):
    return [{"path": p, "occurrences": n} for p, n in pairs]


#: One healthy reading of each of the four sets: nothing under the store,
#: nothing in a proc header, three occurrences across the Rust spools (the
#: three rows the CONVERTER redacts, which are plaintext until it runs), and
#: nothing in the TypeScript spool.
STORE = _rows(("store-b/traces/r.db", 0), ("store-b/redaction.key", 0),
              ("store-b/spool/i/17-0.jsonl", 0))
HEADERS = _rows(("rust-target/sensorium/spool/i/17.proc.json", 0))
SPOOLS = _rows(("rust-target/sensorium/spool/i/17.1.spool", 3))
TS_SPOOLS = _rows(("store-b/spool/i/17-0.jsonl", 0))


def test_h1_values_passes_on_zero_zero_three_zero():
    out = cell_h1_values(STORE, HEADERS, SPOOLS, TS_SPOOLS)
    assert out["word"] == "PASS"
    assert out["spool_occurrences"] == SPOOL_OCCURRENCES
    # FIVE distinct files, not six readings: the TypeScript spool lives
    # under the store, so `17-0.jsonl` is in two of the four sets.
    assert out["files_examined"] == 5


def test_h1_values_counts_a_file_in_two_readings_once():
    """The TypeScript spool directory is UNDER the store, so every file in
    it is in two of §1's four readings. The dry run printed the same leak
    twice in one verdict and claimed more files examined than the sweep had
    looked at; the cell now answers per FILE and says which readings it
    belongs to."""
    hit = _rows(("store-b/spool/i/17-0.jsonl", 2))
    out = cell_h1_values(STORE[:2] + hit, HEADERS, SPOOLS, hit)
    assert out["word"] == "STOP"
    assert [o["path"] for o in out["offenders"]] == \
        ["store-b/spool/i/17-0.jsonl"]
    assert out["offenders"][0]["sets"] == ["store", "ts_spools"]
    assert out["why"].count("17-0.jsonl") == 1
    # Three store files (one of them the spool's), one header, one spool.
    assert out["files_examined"] == 5


def test_h1_values_stops_and_names_the_store_file_that_held_the_token():
    """The STOP clause is "any non-zero: a missed path. Named, fixed, ...",
    so the path is part of the verdict and not a detail a reader digs for."""
    hit = _rows(("store-b/traces/r.db", 0), ("store-b/invocations.jsonl", 2))
    out = cell_h1_values(hit, HEADERS, SPOOLS, TS_SPOOLS)
    assert out["word"] == "STOP"
    assert "store-b/invocations.jsonl" in out["why"]
    assert [o["path"] for o in out["offenders"]] == \
        ["store-b/invocations.jsonl"]


def test_h1_values_stops_on_a_proc_header_that_held_the_token():
    hit = _rows(("rust-target/sensorium/spool/i/17.proc.json", 1))
    out = cell_h1_values(STORE, hit, SPOOLS, TS_SPOOLS)
    assert out["word"] == "STOP"
    assert "17.proc.json" in out["why"]


def test_h1_values_stops_on_a_typescript_spool_that_held_the_token():
    hit = _rows(("store-b/spool/i/17-0.jsonl", 1))
    out = cell_h1_values(STORE, HEADERS, SPOOLS, hit)
    assert out["word"] == "STOP"
    assert "17-0.jsonl" in out["why"]


@pytest.mark.parametrize("total", [0, 2, 4])
def test_h1_values_stops_when_the_rust_spools_do_not_hold_exactly_three(total):
    """Both directions. FEWER than three would mean the converter is not
    the only thing that redacts those rows -- or that a row never fired at
    all -- and MORE means a fourth place holds it. §1's amendment fixes the
    number at three, so either way is a STOP naming what was counted."""
    out = cell_h1_values(STORE, HEADERS,
                         _rows(("rust-target/sensorium/spool/i/17.1.spool",
                                total)), TS_SPOOLS)
    assert out["word"] == "STOP"
    assert f"{total}" in out["why"] and str(SPOOL_OCCURRENCES) in out["why"]


def test_h1_values_counts_the_rust_spools_together():
    """"together exactly 3" -- the Rust arm writes one spool per thread, and
    a per-file gate would STOP on a run that split the same three rows over
    two files."""
    split = _rows(("rust-target/sensorium/spool/i/17.1.spool", 2),
                  ("rust-target/sensorium/spool/i/17.2.spool", 1))
    assert cell_h1_values(STORE, HEADERS, split, TS_SPOOLS)["word"] == "PASS"


#: Everything the run swept outside the four readings -- including the two
#: Rust spool files §1's amendment does not name.
OTHER = _rows(("rust-target/sensorium/spool/i/17.runner.json", 0),
              ("rust-target/sensorium/spool/i/invocation.json", 0),
              ("ts-project-b/package.json", 0))


def test_a_non_zero_reading_outside_the_four_is_named_but_gates_nothing():
    """The two Rust spool files §1's amendment does not name --
    `<pid>.runner.json` (which carries a recorded environment) and
    `invocation.json` -- were in NO grep set at all: ungated, which is
    right, and never examined, which is not. They are swept now, and a
    non-zero out there is NAMED beside the word rather than left in a
    summary table. The word itself is §1's four readings' and does not
    move."""
    leak = _rows(("rust-target/sensorium/spool/i/17.runner.json", 2))
    out = cell_h1_values(STORE, HEADERS, SPOOLS, TS_SPOOLS, OTHER[1:] + leak)
    assert out["word"] == "PASS"
    assert "17.runner.json (2)" in out["why"]
    assert "not gated" in out["why"]
    assert [row["path"] for row in out["beyond_the_readings"]] == \
        ["rust-target/sensorium/spool/i/17.runner.json"]


def test_a_clean_reading_outside_the_four_says_so_and_counts_itself():
    out = cell_h1_values(STORE, HEADERS, SPOOLS, TS_SPOOLS, OTHER)
    assert out["word"] == "PASS"
    assert "3 further file(s) swept outside the four readings" in out["why"]
    assert "none holding the token" in out["why"]
    assert out["other_examined"] == 3
    assert out["beyond_the_readings"] == []


def test_a_file_outside_the_four_that_could_not_be_read_is_named_too():
    """"Swept and clean" and "swept and unreadable" are not one fact, even
    where nothing is gated."""
    out = cell_h1_values(STORE, HEADERS, SPOOLS, TS_SPOOLS,
                         _rows(("tmp/vitest-x/y.json", None)))
    assert out["word"] == "PASS"
    assert "unreadable: tmp/vitest-x/y.json" in out["why"]


def test_the_wider_sweep_is_optional_and_never_drops_the_cell():
    """It is not one of §1's readings, so a run that handed none still
    decides -- and says nothing about a set it was not given."""
    out = cell_h1_values(STORE, HEADERS, SPOOLS, TS_SPOOLS)
    assert out["word"] == "PASS"
    assert "outside the four readings" not in out["why"]


@pytest.mark.parametrize("which", [0, 1, 2, 3])
def test_h1_values_is_dropped_when_one_of_the_four_sweeps_did_not_run(which):
    sets = [STORE, HEADERS, SPOOLS, TS_SPOOLS]
    sets[which] = None
    assert cell_h1_values(*sets)["word"] == "dropped"


@pytest.mark.parametrize("which", [0, 1, 2, 3])
def test_h1_values_refuses_an_empty_sweep_rather_than_passing_it(which):
    """The failure this cell is most exposed to: three of its four readings
    are "every count 0", which is vacuously true over nothing. A mistyped
    root would otherwise publish as a clean sweep."""
    sets = [STORE, HEADERS, SPOOLS, TS_SPOOLS]
    sets[which] = []
    out = cell_h1_values(*sets)
    assert out["word"] == "dropped", which


def test_h1_values_is_dropped_when_a_count_could_not_be_read():
    unread = _rows(("store-b/traces/r.db", None))
    out = cell_h1_values(unread, HEADERS, SPOOLS, TS_SPOOLS)
    assert out["word"] == "dropped"
    assert "store-b/traces/r.db" in out["why"]


# -- H5: the two bench tables ----------------------------------------------
def _m(baseline_s, recorded_s, events=1000, per=3.5):
    return {"baseline_s": baseline_s, "recorded_s": recorded_s,
            "multiplier": round(recorded_s / baseline_s, 1),
            "events": events, "us_per_event": per}


HEADER = (f"{'workload':<19} {'tier':<8} {'baseline':>9} {'recorded':>9} "
          f"{'x':>7} {'events':>9} {'us/event':>9}")


def _table(rows, reps=BENCH_REPS):
    """A table in the shape `bench.report` prints, built by `bench._row`
    itself -- so a change to the printed format reddens here rather than
    silently failing to parse on the day of the run."""
    out = [HEADER]
    for workload, tier, m in rows:
        if m is None:
            out.append(f"{workload:<19} {'focused':<8} n/a  "
                       "(no focus target registered for this workload)")
        else:
            out.append(bench._row(workload, tier, m))
    out += ["", "recorder fixed cost: 0.030s on a program that does nothing "
            "(0.0100s -> 0.0400s).",
            "  Every row above includes it, so a short program's multiplier "
            "is mostly this.",
            f"best of {reps} timed runs after one untimed warm-up; python "
            "3.13.13."]
    return "\n".join(out) + "\n"


BASE_TABLE = _table([("call_dense", "default", _m(0.0100, 0.2000)),
                     ("call_dense", "focused", _m(0.0100, 0.4000)),
                     ("async_call_dense", "default", _m(0.0200, 0.0400)),
                     ("async_call_dense", "focused", None)])
HEAD_TABLE = _table([("call_dense", "default", _m(0.0100, 0.3000)),
                     ("call_dense", "focused", _m(0.0100, 0.4000)),
                     ("async_call_dense", "default", _m(0.0200, 0.0400)),
                     ("async_call_dense", "focused", None)])


def test_the_bench_row_regex_matches_a_line_bench_itself_built():
    """Pinned against `bench._row`'s own output, field by field: the column
    widths, the four decimals on a time and the one on a multiplier are its
    format string's, not this instrument's guess at it."""
    line = bench._row("work_between_calls", "focused",
                      _m(0.1234, 1.2345, events=123456, per=9.1))
    m = BENCH_ROW.match(line)
    assert m, line
    assert m.group("workload") == "work_between_calls"
    assert m.group("tier") == "focused"
    assert m.group("baseline_s") == "0.1234"
    assert m.group("recorded_s") == "1.2345"
    assert m.group("events") == "123456"
    assert m.group("us_per_event") == "9.1"


def test_the_bench_row_regex_reads_a_row_that_could_not_count_events():
    """`-`, never 0: "no events" and "could not tell" are different facts,
    and `bench._event_count` says so by printing a dash."""
    line = bench._row("await_dense", "default",
                      {"baseline_s": 0.1, "recorded_s": 0.2,
                       "multiplier": 2.0, "events": None,
                       "us_per_event": None})
    parsed = parse_bench(line)
    assert parsed[("await_dense", "default")]["events"] is None
    assert parsed[("await_dense", "default")]["us_per_event"] is None


@pytest.mark.parametrize("line", [
    HEADER,
    "async_call_dense    focused  n/a  (no focus target registered for "
    "this workload)",
    "recorder fixed cost: 0.030s on a program that does nothing "
    "(0.0100s -> 0.0400s).",
    "best of 5 timed runs after one untimed warm-up; python 3.13.13.",
])
def test_the_bench_row_regex_matches_no_line_that_is_not_a_measurement(line):
    """The header's second field is `tier`, the `n/a` line's third is not a
    number, and neither of the two trailing sentences is a row. A regex that
    read any of them would put a number into §3 that nobody measured."""
    assert BENCH_ROW.match(line) is None, line


def test_h5_is_measured_and_carries_both_ratios_and_their_ratio():
    """Never PASS and never STOP: §9 gates nothing here (`n/a`), so the cell
    reports the two tables and the three ratios §1's amendment asks for."""
    out = cell_h5(BASE_TABLE, HEAD_TABLE)
    assert out["word"] == "measured"
    rows = {(r["workload"], r["tier"]): r for r in out["rows"]}
    row = rows[("call_dense", "default")]
    assert row["ratio_baseline"] == pytest.approx(20.0)
    assert row["ratio_head"] == pytest.approx(30.0)
    assert row["ratio_of_ratios"] == pytest.approx(1.5)
    same = rows[("call_dense", "focused")]
    assert same["ratio_of_ratios"] == pytest.approx(1.0)
    assert out["baseline_table"] == BASE_TABLE
    assert out["head_table"] == HEAD_TABLE


def test_h5_keeps_a_row_only_one_table_carried_without_a_ratio():
    """A workload in one table and not the other is a real reading -- the
    two trees are different commits -- and inventing a ratio for it would be
    a number about a comparison that was never made."""
    short = _table([("call_dense", "default", _m(0.0100, 0.2000))])
    out = cell_h5(short, HEAD_TABLE)
    rows = {(r["workload"], r["tier"]): r for r in out["rows"]}
    missing = rows[("async_call_dense", "default")]
    assert missing["ratio_baseline"] is None
    assert missing["ratio_of_ratios"] is None
    assert "async_call_dense" in out["why"]


@pytest.mark.parametrize("bad", ["", "nothing here\nno table at all\n", None])
def test_h5_is_dropped_when_a_table_did_not_parse(bad):
    assert cell_h5(bad, HEAD_TABLE)["word"] == "dropped"
    assert cell_h5(BASE_TABLE, bad)["word"] == "dropped"


def test_h5_names_which_of_the_two_tables_was_missing():
    assert BASELINE in cell_h5(None, HEAD_TABLE)["why"]
    assert "HEAD" in cell_h5(BASE_TABLE, None)["why"]


def test_h5_does_not_divide_by_a_baseline_of_zero():
    """`{:>9.4f}` rounds a fast enough baseline to `0.0000`. A ratio taken
    against it is not a large number, it is no number at all."""
    out = cell_h5(_table([("call_dense", "default",
                           {"baseline_s": 0.0, "recorded_s": 0.2,
                            "multiplier": 0.0, "events": 10,
                            "us_per_event": 1.0})]), HEAD_TABLE)
    assert out["word"] == "measured"
    assert out["rows"][0]["ratio_baseline"] is None


# -- H6-values: the census, per arm ----------------------------------------
def _census(**by_arm):
    return [{"arm": arm, "run": f"2026-{i}", "values": values,
             "names": names}
            for i, (arm, (values, names)) in enumerate(by_arm.items())]


def _exact():
    return _census(**{arm: (EXPECTED_VALUES[arm], [TOKEN_VAR])
                      for arm in ARMS})


def test_h6_values_passes_when_every_arm_counted_its_planted_rows():
    out = cell_h6_values(_exact())
    assert out["word"] == "PASS"
    assert out["traces"] == 3


def test_h6_values_stops_when_one_arm_counted_a_different_number():
    """Both directions are a STOP -- fewer is an under-firing rule and more
    an over-firing one -- which is why the check is equality and not a lower
    bound."""
    rows = _exact()
    rows[0]["values"] = EXPECTED_VALUES[rows[0]["arm"]] - 1
    out = cell_h6_values(rows)
    assert out["word"] == "STOP"
    assert rows[0]["arm"] in out["why"]
    assert str(EXPECTED_VALUES[rows[0]["arm"]]) in out["why"]


def test_h6_values_stops_when_a_name_other_than_the_token_was_redacted():
    """`redaction.env` on every probe trace is exactly `{TOKEN_VAR}`: a
    second name means a variable this instrument's allowlist let through,
    and the census would then be about that variable too."""
    rows = _exact()
    rows[1]["names"] = [TOKEN_VAR, "AWS_SECRET_ACCESS_KEY"]
    out = cell_h6_values(rows)
    assert out["word"] == "STOP"
    assert "AWS_SECRET_ACCESS_KEY" in out["why"]


def test_h6_values_stops_when_the_rule_named_nothing_at_all():
    rows = _exact()
    rows[2]["names"] = []
    assert cell_h6_values(rows)["word"] == "STOP"


def test_h6_values_is_dropped_when_an_arm_is_missing():
    """The census is a claim about all three recorders, so a reading missing
    for one drops the cell rather than letting the other two answer for
    it."""
    rows = [r for r in _exact() if r["arm"] != "rust"]
    out = cell_h6_values(rows)
    assert out["word"] == "dropped"
    assert "rust" in out["why"]


def test_h6_values_is_dropped_when_two_traces_carry_one_arm():
    """The planted count is a per-TRACE claim. Two traces for one arm means
    the recording was split, and neither 4 nor 8 would be the number §1
    predicted."""
    rows = _exact() + [{"arm": "python", "run": "2026-9", "values": 5,
                        "names": [TOKEN_VAR]}]
    out = cell_h6_values(rows)
    assert out["word"] == "dropped"
    assert "python" in out["why"]


@pytest.mark.parametrize("field", ["values", "names"])
def test_h6_values_is_dropped_when_a_reading_could_not_be_parsed(field):
    """A recording made before the count existed carries no `values` key,
    and `_parse_info` leaves `None` rather than a zero nobody measured."""
    rows = _exact()
    rows[0][field] = None
    out = cell_h6_values(rows)
    assert out["word"] == "dropped"
    assert rows[0]["run"] in out["why"]


def test_h6_values_is_dropped_when_nothing_was_read():
    assert cell_h6_values(None)["word"] == "dropped"
    assert cell_h6_values([])["word"] == "dropped"


# -- the part's own word ---------------------------------------------------
def _cells(h1="PASS", h6="PASS", h5="measured"):
    return {"H1-values": {"word": h1}, "H5": {"word": h5},
            "H6-values": {"word": h6}}


def test_the_part_is_DONE_when_both_gated_cells_passed():
    """H5 is `measured` and never gates: §9's own PASS/STOP column for it is
    `n/a`, and a part word that waited for a PASS there would never be
    DONE."""
    assert part_word(_cells()) == "DONE"


@pytest.mark.parametrize("word", ["STOP", "dropped"])
def test_one_stop_or_one_dropped_cell_costs_the_part_its_plain_DONE(word):
    assert part_word(_cells(h1=word)) == "DONE-WITH-STOP"
    assert part_word(_cells(h6=word)) == "DONE-WITH-STOP"


def test_a_missing_cell_is_not_a_passed_one():
    """A cell nobody measured cannot be read out of an absent key as a
    pass: `.get` on a dict that never got the row has to be the STOP side."""
    assert part_word({"H5": {"word": "measured"}}) == "DONE-WITH-STOP"
    assert part_word({}) == "DONE-WITH-STOP"


# -- the rule table is the record's, not this instrument's -----------------
def test_the_rule_table_is_the_records_own_words():
    """Catches: §9's PASS/STOP column paraphrased into the instrument, where
    a softened endpoint would decide the measurement while §1 still read as
    the rule. Checked by EQUALITY against the record's own cell, and read
    from §1 ALONE -- §2's and §3's verdict tables quote the very clause
    under test, so a scan of the whole document would compare the
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


def test_every_cell_this_part_measures_has_a_rule_and_a_dropped_reason():
    """The three measured cells and the five deferred ones, with nothing
    falling between: a cell in neither list is one nobody decided about."""
    assert set(RULES) == {"H1", "H5", "H6"}
    assert dict(e16b_cells.DROPPED) == {
        "H1-env": "part A", "H2": "part A", "H3": "part A",
        "H4": "part C", "H6-env": "part A"}
    assert set(e16b_cells.CELL_TITLES) == set(e16b_cells.RULE_OF)
    assert set(e16b_cells.RULE_OF.values()) == set(RULES)


# -- what §1's amendment fixed --------------------------------------------
def test_the_planted_counts_are_the_pre_registrations():
    assert EXPECTED_VALUES == {"python": 5, "typescript": 4, "rust": 4}
    assert SPOOL_OCCURRENCES == 3
    assert BENCH_REPS == 5
    assert BASELINE == "7dd25d2"
    assert e16b_cells.EXPECTED == {"sensorium": "0.16.0",
                                   "sensorium-rt": "0.7.0",
                                   "cargo-sensorium": "0.8.0",
                                   "sensorium-ts": "0.6.0"}


def test_the_dry_runs_predicted_rows_are_the_name_rows_alone():
    """The decoy is `dry-` plus four characters, which no content pattern
    matches, so a dry run fires the NAME rows and nothing else. The table is
    stated so the dry run can say "as predicted" -- and it REPORTS, never
    gates: a dry run's census is about a different string."""
    assert DRY_NAME_ROWS == {"python": 4, "typescript": 2, "rust": 2}
    for arm in ARMS:
        assert DRY_NAME_ROWS[arm] < EXPECTED_VALUES[arm], arm


def test_the_kill_rules_are_the_ones_the_amendment_fixed():
    assert e16b_cells.TIMERS["build"] == 1800
    assert e16b_cells.TIMERS["baseline"] == 600
    assert e16b_cells.TIMERS["record"] == 600
    assert e16b_cells.TIMERS["bench"] == 1200
    assert e16b_cells.TIMERS["part"] == 60 * 60
    assert e16b_cells.DRY_TIMERS["record"] == 60
    assert e16b_cells.DRY_TIMERS["bench"] == 300


# -- the probes carry the rows §1 counted ----------------------------------
def _probe(arm: str) -> str:
    return "\n".join((REPO / "tests" / "acceptance_e16" / "probes" / arm / p)
                     .read_text() for p in PROBES[arm])


def test_every_probe_reads_the_token_out_of_the_pre_registered_variable():
    for arm in ARMS:
        assert TOKEN_VAR in _probe(arm), arm


@pytest.mark.parametrize("arm,fragments", [
    # Python 5: secret's RETURN, the `token` local, the `authorization`
    # map value, `send`'s CALL argument, and the `print` chunk by content.
    ("python", ("def secret(", "def handle(", "token = secret()",
                '"authorization": token', "send(token)", "print(token)")),
    # Rust 4: the `token` parameter delta, `copy`, the `Headers` Debug text,
    # secret's RETURN. `copy` and `headers` fire NO name -- they are the two
    # rows the content rule has to reach.
    ("rust", ("fn secret(", "fn handle(token: String)", "let copy = ",
              "struct Headers", "authorization", "#[derive(Debug)]")),
    # TypeScript 4: the CALL argument, `copy`, the `headers` inspect text,
    # secret's RETURN.
    ("typescript", ("function secret(", "function handle(token: string)",
                    "const copy = token", "authorization: copy",
                    "handle(secret())")),
])
def test_each_probe_carries_every_row_the_pre_registration_counted(
        arm, fragments):
    """A probe edited to drop a row -- the `print`, the `copy` binding --
    would change what the census means while the number in §1 stayed 5 or
    4. The sources are held against the amendment's own list of rows."""
    source = _probe(arm)
    for fragment in fragments:
        assert fragment in source, (arm, fragment)


def test_no_probe_carries_a_name_the_content_rule_was_meant_to_reach():
    """`copy` and `headers` are deliberately names rule v1 does NOT fire on
    (the corpus case uses `api_key` and `auth_headers`, which do). Renaming
    either back would move a row from the content rule to the name rule and
    leave the count unchanged -- a silent loss of the only two rows part B
    adds over part A."""
    from sensorium import redact

    knobs = redact.Knobs.from_environ({})
    for name in ("copy", "headers"):
        assert not redact.fires(name, knobs), name
    for name in ("token", "secret", "authorization"):
        assert redact.fires(name, knobs), name


# -- the assembler ---------------------------------------------------------
def test_the_assembler_refuses_a_dry_run_record():
    """The dry run plants a decoy that cannot match the content rule and
    caps its timers; its cells are about a different string."""
    with pytest.raises(assemble_e16b.Refused):
        assemble_e16b.refuse_dry_run({"dry_run": True})
    with pytest.raises(assemble_e16b.Refused):
        assemble_e16b.refuse_dry_run({})
    assert assemble_e16b.refuse_dry_run({"dry_run": False}) is None


def test_the_amendments_block_states_the_text_the_command_and_the_why():
    """R11: a pre-registration error is recorded BESIDE the locked text,
    never edited into it. The entry has to carry §1's own clause, the
    command that was actually run, and why they differ -- otherwise a reader
    cannot tell an amendment from a changed mind."""
    out = "\n".join(assemble_e16b.amendments(
        {"amendments": list(e16b_cells.AMENDMENTS)}))
    assert "--focus handle" in out
    assert "--focus main:handle" in out
    assert "module" in out


def test_the_amendments_block_is_empty_when_the_run_carried_none():
    assert assemble_e16b.amendments({}) == []
    assert assemble_e16b.amendments({"amendments": []}) == []


def test_the_instrument_carries_the_amendments_it_measured_under():
    """The list is DATA in the raw record, not prose in the assembler: what
    §3 says was amended is what the run was actually made under."""
    assert len(e16b_cells.AMENDMENTS) >= 2
    joined = "\n".join(e16b_cells.AMENDMENTS)
    assert "main:handle" in joined
    assert "secret_in_env" in joined


def test_writing_into_the_record_refuses_a_second_unmeasured_section(
        tmp_path):
    """`--write` replaces the ONE remaining `Not yet measured.`, and §3's is
    the only one left. Two would mean the assembler could not tell which
    part it was writing into."""
    doc = tmp_path / "rec.md"
    doc.write_text("## 2. Part A\n\nNot yet measured.\n\n## 3. Part B\n\n"
                   "Not yet measured.\n")
    with pytest.raises(assemble_e16b.Refused):
        assemble_e16b.write_into(doc, "### measured 2026-01-01\n")
    doc.write_text("## 3. Part B\n\nNot yet measured.\n")
    assemble_e16b.write_into(doc, "### measured 2026-01-01\n")
    assert "Not yet measured." not in doc.read_text()
    with pytest.raises(assemble_e16b.Refused):
        assemble_e16b.write_into(doc, "### measured 2026-01-02\n")


def test_offenders_still_refuses_a_box_path_and_a_token_shaped_line():
    """Imported from part A's assembler rather than re-implemented: one
    rule, one place, and the record's own no-box-path test is what it
    mirrors."""
    assert assemble_e16b.offenders("| root | `E16_DIR=/mnt/x` |") == []
    assert assemble_e16b.offenders("trace: /mnt/x/y") == ["trace: /mnt/x/y"]
    planted = "SENSORIUM_E16_TOKEN=sk-e16-" + "A1b2C3d4E5f6G7h8" * 2
    assert assemble_e16b.offenders(planted) == [planted]


def test_the_versions_block_is_dropped_when_the_phase_left_nothing():
    """A `versions` phase that failed leaves `None`, and a renderer that
    raises on it hands the operator a traceback where §3 should carry a
    named hole. Dropped, in words, like every other unread reading."""
    rendered = assemble_e16b.versions_table(
        {"driver_build": {"built": True, "binary": "$DRIVER_DIR/x",
                          "mtime": 1789000000.0, "size": 1, "seconds": 0.1},
         "versions": None})
    assert len(rendered) == 1
    assert rendered[0].startswith("**Versions: dropped")


def test_the_h1_values_table_names_every_file_and_its_occurrences():
    rendered = "\n".join(assemble_e16b.h1_values_table(
        {"h1_values": {"store": STORE, "headers": HEADERS,
                       "spools": SPOOLS, "ts_spools": TS_SPOOLS,
                       "other": []}}))
    assert "store-b/redaction.key" in rendered
    assert "17.1.spool" in rendered
    assert "| 3 |" in rendered


def test_the_h6_values_table_names_the_count_and_the_expectation_per_arm():
    rendered = "\n".join(assemble_e16b.h6_values_table(
        {"h6_values": _exact()}))
    for arm in ARMS:
        assert arm in rendered
    assert str(EXPECTED_VALUES["python"]) in rendered


def test_the_h5_caption_states_the_reps_the_run_actually_used():
    """The dry run caught this: the caption was built from `BENCH_REPS` and
    said `reps=5` directly above evidence reading `best of 1 timed runs`. It
    is read off the run now, and a run whose two trees somehow differed says
    both numbers rather than picking one."""
    raw = {"cells": {"H5": cell_h5(BASE_TABLE, HEAD_TABLE)},
           "bench": {"baseline": {"reps": 1}, "head": {"reps": 1}}}
    assert "reps=1" in "\n".join(assemble_e16b.h5_tables(raw))
    raw["bench"]["head"]["reps"] = 5
    assert "reps=1 and 5" in "\n".join(assemble_e16b.h5_tables(raw))


def test_the_other_table_marks_a_non_zero_row_and_names_the_file():
    """A number a reader has to notice for themselves in a summary row is a
    number that gets missed. Marked in the row, named under the table."""
    leak = _rows(("rust-target/sensorium/spool/i/17.runner.json", 2))
    rendered = "\n".join(assemble_e16b.h1_values_table(
        {"h1_values": {"store": STORE, "headers": HEADERS,
                       "spools": SPOOLS, "ts_spools": TS_SPOOLS,
                       "other": OTHER[2:] + leak}}))
    assert "not gated, but non-zero" in rendered
    assert "`rust-target/sensorium/spool/i/17.runner.json` (2)" in rendered
    # The caption names both ungated Rust spool file types by name.
    assert "`<pid>.runner.json`" in rendered
    assert "`invocation.json`" in rendered


def test_the_h1_values_table_prints_a_file_in_two_readings_once():
    """The other half of the dry run's duplicate: the table listed the
    TypeScript spool's files twice, once under each reading they belong
    to."""
    rendered = assemble_e16b.h1_values_table(
        {"h1_values": {"store": STORE, "headers": HEADERS,
                       "spools": SPOOLS, "ts_spools": TS_SPOOLS,
                       "other": []}})
    rows = [ln for ln in rendered if "17-0.jsonl" in ln]
    assert len(rows) == 1, rows
    assert "every file under the store + TypeScript spool" in rows[0]


def test_the_h5_tables_carry_both_readings_verbatim():
    """§1's amendment asks for both tables verbatim -- a bench table is a
    measurement of a machine and a summary of it is a different claim."""
    rendered = "\n".join(assemble_e16b.h5_tables(
        {"cells": {"H5": cell_h5(BASE_TABLE, HEAD_TABLE)}}))
    assert BASE_TABLE.strip() in rendered
    assert HEAD_TABLE.strip() in rendered
    assert "1.5" in rendered
