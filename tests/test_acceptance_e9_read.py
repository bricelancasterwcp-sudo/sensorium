"""The E9 instrument's READERS, tested against pasted output.

Nothing here runs cargo, the driver or the query CLI, and nothing here opens
a location an environment variable would have to name. Every input is a
string this file spells out or a two-row sqlite database it builds in
`tmp_path` — so a parser that agreed with the tool only on this machine
fails here rather than in a detached run that cannot be repeated.

The shapes are taken from the code that prints them and from the pins that
already gate them: `src/sensorium/query/watch_cmd.verdict`,
`flow_cmd._print_footer`, `fmt.fmt_event`, `info_cmd`, `caps.require`, and
the corpus questions of `corpus/rust/focus_*` and `corpus/rust/stale_cache`.

Each test states the failure it would catch. The mutations run against them
are in the task report.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e9_read as rd                                    # noqa: E402
from acceptance_e9_read import (delta_census, parse_flow,          # noqa: E402
                                parse_watch)

# -- the driver ------------------------------------------------------------

DRIVER_STDERR = """\
focus: missing_stats_is_a_contract_violation_not_a_reply
spool: /somewhere/spools
"""

CARGO_TAIL = """\
running 1 test
test missing_stats_is_a_contract_violation_not_a_reply ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; \
finished in 0.42s

"""


def test_the_drivers_focus_lines_are_read_from_its_own_stderr():
    """H2's resolution evidence. A run whose `focus:` lines were not read
    could only report what was TYPED, which is the thing under test."""
    assert rd.focus_lines(DRIVER_STDERR) == [
        "missing_stats_is_a_contract_violation_not_a_reply"]
    assert rd.focus_lines("nothing here") == []


def test_a_focus_that_matched_two_things_is_two_lines_not_one():
    """`resolved to exactly one qualname` is a COUNT, and a parser that
    returned the first match would make every focus look unique."""
    text = "focus: a::f\nfocus: b::f\n"
    assert rd.focus_lines(text) == ["a::f", "b::f"]


def test_libtests_summary_line_is_parsed_whole():
    """H2's outcome comparison and H6's first reading both live on this one
    line; a regex that dropped `finished in` would silently make H6's first
    reading unmeasurable while H2 still passed."""
    rows = rd.test_results(CARGO_TAIL)
    assert len(rows) == 1
    assert rows[0]["passed"] == 1 and rows[0]["failed"] == 0
    assert rows[0]["ignored"] == 0 and rows[0]["filtered_out"] == 0
    assert rows[0]["libtest_secs"] == 0.42
    assert rows[0]["verdict"] == "ok"


def test_every_target_summary_is_kept_and_the_counts_are_summed():
    """`cargo test` prints one summary per target. A comparison that took the
    first would compare U1's binary against F1's second target."""
    two = CARGO_TAIL + ("test result: FAILED. 3 passed; 1 failed; 2 ignored; "
                        "0 measured; 0 filtered out; finished in 1.5s\n")
    rows = rd.test_results(two)
    assert len(rows) == 2
    out = rd.outcome_counts(rows)
    assert out == {"targets": 2, "passed": 4, "failed": 1, "ignored": 2,
                   "measured": 0, "filtered_out": 0,
                   "verdicts": ["ok", "FAILED"]}


def test_no_summary_at_all_is_None_and_not_a_zero_outcome():
    """A run whose output carried no summary line measured nothing about the
    outcome. `{passed: 0}` would compare EQUAL to another such run and let
    H2 pass on two builds that never ran a test."""
    assert rd.outcome_counts([]) is None


# -- `info` ----------------------------------------------------------------

INFO_UNFOCUSED = """\
cmd: pager_obligation_test    cwd: /w
rust process  env:ab12  exit: 0  events: 812
recorder: sensorium-rt 0.4.0  lang: rust  capabilities: children=no \
err_flow=yes line=no locals=no object_identity=no tasks=no threads=yes
recorded: CALL 406  RETURN 406  RAISE 0  HANDLED 0  YIELD 0  RESUME 0  LINE 0
focus: -    window: -
caps: dbg=yes   truncated values: 0
"""

INFO_FOCUSED = INFO_UNFOCUSED.replace("line=no locals=no",
                                      "line=yes locals=yes") \
    .replace("LINE 0", "LINE 26").replace("focus: -", "focus: fill")


def test_info_yields_the_recorder_the_capabilities_and_the_focus_row():
    """H1 reads `capabilities` from the trace's own meta and prints `info`
    beside it; a parser that lost the row would leave the record with no
    printed evidence for the gate."""
    got = rd.parse_info(INFO_UNFOCUSED)
    assert got["recorder"] == "sensorium-rt 0.4.0"
    assert got["lang"] == "rust"
    assert got["capabilities"]["line"] is False
    assert got["capabilities"]["locals"] is False
    assert got["capabilities"]["err_flow"] is True
    assert got["recorded"]["LINE"] == 0
    assert got["focus"] == [] and got["window"] == "-"


def test_info_reads_a_focused_run_differently_from_an_unfocused_one():
    """The two rows H1 and H2 turn on. A parser that answered the same for
    both would make the whole slice unfalsifiable."""
    got = rd.parse_info(INFO_FOCUSED)
    assert got["capabilities"]["line"] is True
    assert got["capabilities"]["locals"] is True
    assert got["recorded"]["LINE"] == 26
    assert got["focus"] == ["fill"]


# -- `watch` ---------------------------------------------------------------

W_SATISFIED = """\
  HIT   e5 LINE    fill L13  b=2   [local b]
verdict: SATISFIED at 2 of the 2 site(s) the predicate could be evaluated at
  but 3 of 5 recorded site(s) could NOT be evaluated, so these are not \
necessarily every time it held
"""

W_NOTHING = """\
verdict: NOTHING WAS CHECKED -- the predicate could not be evaluated at any \
of the 5 recorded site(s)
  'hits: 0' here means 'could not evaluate', NOT 'the invariant held'
"""

W_NOT_SATISFIED = """\
verdict: not satisfied at any of the 7 recorded site(s), every one of which \
was evaluated
  that is a fact about what was RECORDED, not a claim that the invariant held\
: only recorded sites were checked
"""

W_REFUSED = ("REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 "
             "declares it does not produce (capabilities.line: false); "
             "nothing was checked\n")


def test_the_three_verdict_classes_are_told_apart():
    """H4's first reading. `watch` returns 0 / 1 / 3 for these three, and a
    parser that could not separate them would make the class agree with the
    exit by construction — which is exactly the disagreement §1 says must be
    reportable."""
    assert rd.parse_watch(W_SATISFIED)["verdict_class"] == "SATISFIED"
    assert rd.parse_watch(W_NOTHING)["verdict_class"] == "NOTHING WAS CHECKED"
    assert rd.parse_watch(W_NOT_SATISFIED)["verdict_class"] == "not satisfied"
    assert rd.parse_watch(W_REFUSED)["verdict_class"] == "REFUSED"


def test_the_counts_beside_each_verdict_are_read():
    """The numbers §1.2's derivations name. W2's prediction rests on `no site
    evaluated`, and a parser that did not read `evaluated` could not tell
    that branch from a zero-hit one."""
    s = rd.parse_watch(W_SATISFIED)
    assert s["hits"] == 2 and s["evaluated"] == 2
    assert s["hit_rows"] == ["HIT   e5 LINE    fill L13  b=2   [local b]"]
    n = rd.parse_watch(W_NOTHING)
    assert n["evaluated"] == 0 and n["sites"] == 5
    ns = rd.parse_watch(W_NOT_SATISFIED)
    assert ns["hits"] == 0 and ns["sites"] == 7


def test_two_verdict_sentences_leave_the_class_null_rather_than_the_first():
    """A text carrying two verdicts is a defect in the command, and taking
    the first would hide it behind a class that looks read."""
    both = W_SATISFIED + W_NOTHING
    got = rd.parse_watch(both)
    assert got["verdict_class"] is None
    assert sorted(got["classes"]) == ["NOTHING WAS CHECKED", "SATISFIED"]


def test_the_refusal_sentence_takes_its_version_token_from_the_trace():
    """§1's H1 second reading. The version in the pinned sentence is
    `trace.recorder`, which §2 records from the trace itself; a runner that
    spelled `0.4.0` into the gate would be checking the design's PLAN for the
    version and would pass a run that shipped another recorder."""
    assert rd.refusal_sentence("sensorium-rt 0.4.0") == W_REFUSED.strip()
    moved = rd.refusal_sentence("sensorium-rt 0.5.1")
    assert "sensorium-rt 0.5.1" in moved
    assert moved != W_REFUSED.strip()
    # and the sentence around the token is unchanged
    assert moved.replace("0.5.1", "0.4.0") == W_REFUSED.strip()


def test_the_refusal_sentence_is_the_one_the_corpus_already_pins():
    """The same bytes `corpus/rust/focus_unfocused_refuses` expects. Two
    spellings of one sentence would let E9 pass while the corpus failed.

    The token here is the CURRENT `sensorium-rt` -- `spool.RT_VERSION` -- and
    moves with it: the corpus pins what today's runtime declares, so a stale
    token here would pass against nothing. That is the opposite of the test
    above, which pins the SHAPE around the token and must not name a version.
    """
    pin = (REPO / "corpus" / "rust" / "focus_unfocused_refuses"
           / "questions.yaml")
    text = pin.read_text()
    assert rd.refusal_sentence("sensorium-rt 0.4.1") in text


# -- `flow` ----------------------------------------------------------------

FLOW = """\
  e10 LINE    sum L13  total=3   [local total]
  e12 RETURN  sum -> 3   [return]
  e4 LINE    fresh_dir L66  p="/tmp/x"   [local p]
sightings: 3 event(s), 3 capture(s)
scope: 9 capture(s) searched across 9 event(s) in CALL args, RETURN values \
and LINE deltas
"""


def test_flow_totals_and_rows_are_read():
    """H5 gates on the sightings restricted to A's LINE deltas and REPORTS
    the whole-trace set beside them; both need the rows, not just the total."""
    got = rd.parse_flow(FLOW)
    assert got["sighting_events"] == 3 and got["sighting_captures"] == 3
    assert got["scope_captures"] == 9 and got["scope_events"] == 9
    assert [r["event"] for r in got["rows"]] == [10, 12, 4]
    assert got["rows"][0]["kind"] == "LINE"
    assert got["rows"][0]["qualname"] == "sum"
    assert got["rows"][0]["line"] == 13
    assert got["rows"][0]["labels"] == ["local total"]
    assert got["rows"][1]["kind"] == "RETURN"
    assert got["rows"][1]["qualname"] == "sum"
    assert got["rows"][1]["line"] is None


def test_the_gated_set_is_one_qualnames_LINE_deltas_and_nothing_else():
    """§1.3's gate. The unfocused helpers are still instrumented at the call
    tier and their RETURN values carry the same texts, so a gate that
    counted every sighting would pass on a recording that focused nothing."""
    rows = rd.parse_flow(FLOW)["rows"]
    gated = rd.line_deltas_of(rows, "sum")
    assert [r["event"] for r in gated] == [10]
    assert rd.line_deltas_of(rows, "fresh_dir") == [
        r for r in rows if r["event"] == 4]
    assert rd.line_deltas_of(rows, "nobody") == []


def test_a_line_that_is_not_an_event_row_parses_to_None():
    """The footer lines run through the same walk; a parser that took them
    for rows would inflate every sighting count by two."""
    assert rd.parse_event_row("sightings: 3 event(s), 3 capture(s)") is None
    assert rd.parse_event_row("") is None


# -- the temp root ---------------------------------------------------------


def test_the_temp_root_follows_the_observed_TMPDIR():
    """§1.4: `TMPDIR` unset is what makes `std::env::temp_dir()` `/tmp` and
    W1/W3/S1/S2 derivable at all. A runner that hard-coded `/tmp` would read
    four predictions against the wrong prefix and report them as MISSES."""
    assert rd.temp_root(None) == "/tmp"
    assert rd.temp_root("") == "/tmp"
    assert rd.temp_root("/scratch/tmp") == "/scratch/tmp"
    assert rd.temp_root("/scratch/tmp/") == "/scratch/tmp"


# -- the trace joins -------------------------------------------------------


def _trace(tmp_path, rows, codes, frames) -> Path:
    """A two-table trace: enough of the real schema for the joins H1 and H3
    make, built here so no store on the box is opened."""
    db = tmp_path / "t.db"
    con = sqlite3.connect(db)
    con.executescript(
        "create table code_objects (id integer primary key, file text, "
        "qualname text, firstlineno integer);"
        "create table frames (id integer primary key, code_id integer);"
        "create table events (id integer primary key, kind text, "
        "frame_id integer, code_id integer, line integer);")
    con.executemany("insert into code_objects values (?,?,?,?)", codes)
    con.executemany("insert into frames values (?,?)", frames)
    con.executemany("insert into events values (?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return db


def test_the_whole_trace_LINE_count_is_H1s_gate(tmp_path):
    """H1's `select count(*) from events where kind = 'LINE'`. A count
    restricted to one qualname would read 0 on a trace that carried LINE
    rows for another function — the exact leak H1 exists to exclude."""
    db = _trace(tmp_path,
                [(1, "CALL", 1, 1, 10), (2, "LINE", 1, 1, 11),
                 (3, "LINE", 2, 2, 30)],
                [(1, "f", "a", 10), (2, "f", "b", 29)],
                [(1, 1), (2, 2)])
    assert rd.line_rows_total(db) == 2


def test_the_distinct_LINE_qualnames_are_H2s_second_reading(tmp_path):
    """`the set of distinct qualnames carrying LINE rows is exactly the
    focus value`. A set that folded two qualnames into one would let a focus
    that leaked into a helper read as exact."""
    db = _trace(tmp_path,
                [(1, "LINE", 1, 1, 11), (2, "LINE", 1, 1, 12),
                 (3, "LINE", 2, 2, 30), (4, "CALL", 2, 2, 29)],
                [(1, "f", "a", 10), (2, "f", "b", 29)],
                [(1, 1), (2, 2)])
    assert rd.line_qualnames(db) == {"a": 2, "b": 1}


def test_the_histogram_counts_one_activation_by_line(tmp_path):
    """H3's N and its per-line table. A histogram keyed by anything but the
    source line could not produce the diff §1.1 exists to make readable."""
    db = _trace(tmp_path,
                [(1, "CALL", 1, 1, 10), (2, "LINE", 1, 1, 11),
                 (3, "LINE", 1, 1, 12), (4, "LINE", 1, 1, 12),
                 (5, "RETURN", 1, 1, 13)],
                [(1, "f", "a", 10)], [(1, 1)])
    h = rd.line_histogram(db, "a")
    assert h["activations"] == 1 and h["frame_ids"] == [1]
    assert h["by_line"] == {11: 1, 12: 2}
    assert h["total"] == 3
    assert h["joins_agree"] is True


def test_the_frame_join_and_the_code_join_are_both_recorded(tmp_path):
    """A LINE row attributed to a frame that is not its code object's is a
    finding about the recorder, not a number to choose between — so the two
    joins are recorded separately and their disagreement is a field."""
    db = _trace(tmp_path,
                [(1, "LINE", 1, 1, 11), (2, "LINE", 99, 1, 12)],
                [(1, "f", "a", 10)], [(1, 1)])
    h = rd.line_histogram(db, "a")
    assert h["by_line"] == {11: 1}
    assert h["by_line_via_code_id"] == {11: 1, 12: 1}
    assert h["joins_agree"] is False


def test_two_activations_are_counted_as_two(tmp_path):
    """§1 derives N from ONE activation; anything but 1 changes what N
    means, so the count must not be a boolean in disguise."""
    db = _trace(tmp_path,
                [(1, "LINE", 1, 1, 11), (2, "LINE", 2, 1, 11)],
                [(1, "f", "a", 10)], [(1, 1), (2, 1)])
    h = rd.line_histogram(db, "a")
    assert h["activations"] == 2
    assert h["by_line"] == {11: 2}


# -- the diff --------------------------------------------------------------

EXPECTED = {ln: 1 for ln in (250, 251, 252)}


def test_a_missing_line_is_NAMED_and_not_only_counted():
    """§1.1's whole point: a measured 25 must say WHICH line did not mint a
    row, because that is what decides between readings B and C."""
    d = rd.histogram_diff({250: 1, 252: 1}, EXPECTED)
    assert d["missing_lines"] == [251]
    assert d["unexpected_lines"] == []
    assert d["differences"] == 1
    assert d["measured_total"] == 2 and d["expected_total"] == 3


def test_an_extra_line_and_a_count_difference_are_separate_facts():
    """Reading C is an extra ROW at a line that already has one; a diff that
    folded `extra line` and `count differs` together could not tell C from a
    row minted at a line §1.1 did not count at all."""
    d = rd.histogram_diff({250: 2, 251: 1, 252: 1, 259: 1}, EXPECTED)
    assert d["unexpected_lines"] == [259]
    assert d["count_diffs"] == [{"line": 250, "measured": 2, "expected": 1}]
    assert d["missing_lines"] == []
    assert d["differences"] == 2


def test_an_identical_histogram_has_zero_differences():
    """The passing case, asserted so a diff that always reported a
    difference could not masquerade as a strict check."""
    assert rd.histogram_diff(dict(EXPECTED), EXPECTED)["differences"] == 0


def test_a_histogram_read_back_from_json_has_int_keys_again():
    """The record round-trips through JSON, which stringifies every key. A
    diff over string keys would report all 26 lines missing AND all 26
    unexpected — a 52-difference answer about an identical histogram."""
    assert rd.int_keys({"250": 1, "251": 2}) == {250: 1, 251: 2}
    assert rd.histogram_diff(rd.int_keys({"250": 1, "251": 1, "252": 1}),
                             EXPECTED)["differences"] == 0


# -- fix round 1: §1.4's ungated counts -------------------------------------

#: The real shapes, captured from a recording of `corpus/rust/focus_let_chain`
#: under the driver at HEAD (2026-09-06) and pasted here so this suite never
#: needs one again.
W_REAL = """\
watch 'b == 2' at fill in 20260906-182425-1549cb
  a site is one RECORDED event in a matching frame: a CALL (its arguments)
sites: 5   evaluated: 2   hits: 2   not-captured: 3   errors: 0
verdict: SATISFIED at 2 of the 2 site(s) the predicate could be evaluated at
  but 3 of 5 recorded site(s) could NOT be evaluated, so these are not \
necessarily every time it held
  HIT   e5 LINE    fill L13  b=2   state: b=2
  HIT   e6 LINE    fill L14  s="2"   state: b=2
not captured at 3 of 5 site(s) -- the predicate could not be checked there:
  b: not in scope at this site   [3 site(s)]
"""

F_REAL = """\
flow of 2 (int) in 20260906-182425-1549cb
  captured-value equality, not true dataflow analysis: the trace records \
values, not the edges between them
  e5 LINE    fill L13  b=2   [local b]
sightings: 1 event(s), 1 capture(s)
scope: 5 capture(s) searched across 5 event(s) in CALL args, RETURN values \
and LINE local deltas
"""


def test_watchs_counts_line_gives_every_bucket():
    """§1.4 reports W1's and W3's hit AND not-captured counts. The verdict
    sentence carries two of the five buckets and the HIT rows below it are a
    PAGE (`--limit`, default 20), so the counts line is the only complete
    source — a record that counted the printed HIT rows would under-report
    every watch with more than twenty hits."""
    w = parse_watch(W_REAL)
    assert (w["sites"], w["evaluated"], w["hits"], w["not_captured"],
            w["errors"]) == (5, 2, 2, 3, 0)
    assert w["counts_line"] == ("sites: 5   evaluated: 2   hits: 2   "
                               "not-captured: 3   errors: 0")
    assert w["verdict_class"] == "SATISFIED"
    assert len(w["hit_rows"]) == 2


def test_the_counts_line_OVERRIDES_the_verdict_sentences_numbers():
    """Where both exist they must agree, and where they do not the command's
    own tally is the record's. A parser that let the verdict sentence win
    would publish `sites` from a sentence that never carries `not-captured`
    or `errors` at all."""
    text = W_REAL.replace("sites: 5   evaluated: 2   hits: 2",
                          "sites: 9   evaluated: 4   hits: 3")
    w = parse_watch(text)
    assert w["sites"] == 9 and w["evaluated"] == 4 and w["hits"] == 3
    # with no counts line the verdict sentence still answers
    no_counts = "\n".join(ln for ln in W_REAL.splitlines()
                          if not ln.startswith("sites: "))
    w = parse_watch(no_counts)
    assert w["counts_line"] is None
    assert w["hits"] == 2 and w["evaluated"] == 2


def test_a_whole_flow_page_is_not_truncated():
    """The real output, unpaged. A guard that fired on a complete answer
    would null H5's gate on every run."""
    f = parse_flow(F_REAL)
    assert f["sighting_events"] == 1 and f["rows_printed"] == 1
    assert f["page_truncated"] is False and f["showing"] is None
    assert f["scope_captures"] == 5 and f["scope_events"] == 5


def test_a_TRUNCATED_flow_page_is_noticed_both_ways():
    """`flow`'s default `--limit` is 50 and the footer says `(showing K)`
    when the page is smaller than the set. Every H5 number is read off the
    printed rows, so an unnoticed truncation is a silent under-count of the
    gate — and the footer is not the only tell: a total that the printed rows
    do not reach says the same thing."""
    footer = F_REAL.replace("sightings: 1 event(s), 1 capture(s)",
                            "sightings: 90 event(s), 90 capture(s) "
                            "(showing 50)")
    f = parse_flow(footer)
    assert f["page_truncated"] is True and f["showing"] == 50
    assert f["sighting_events"] == 90 and f["rows_printed"] == 1
    # no `(showing)` at all, but the rows do not reach the total
    counted = F_REAL.replace("sightings: 1 event(s), 1 capture(s)",
                             "sightings: 4 event(s), 4 capture(s)")
    assert parse_flow(counted)["page_truncated"] is True


def _trace_with_payloads(tmp_path, rows) -> Path:
    db = tmp_path / "c.db"
    con = sqlite3.connect(db)
    con.executescript(
        "create table code_objects (id integer primary key, file text, "
        "qualname text, firstlineno integer);"
        "create table events (id integer primary key, kind text, "
        "frame_id integer, code_id integer, line integer, payload text);")
    con.execute("insert into code_objects values (1,'f','fill',10)")
    con.executemany("insert into events values (?,?,1,1,?,?)", rows)
    con.commit()
    con.close()
    return db


def test_the_census_counts_unread_and_truncated_LINE_deltas(tmp_path):
    """§1.4's honesty count, over the payload shapes a real converted trace
    carries (`convert/frames.rs`): `{"deltas": {name: {"k","v","trunc"}}}`,
    with `{"k": "unread"}` for a value the probe could not read at all."""
    db = _trace_with_payloads(tmp_path, [
        (1, "LINE", 11, '{"deltas":{}}'),
        (2, "LINE", 12, '{"deltas":{"a":{"k":"dbg","trunc":false,"v":"1"}}}'),
        (3, "LINE", 13, '{"deltas":{"journal":{"k":"unread"},'
                        '"p":{"k":"dbg","trunc":true,"v":"Pager { .."}}}'),
        (4, "RETURN", None, '{"outcome":"ok","value":{"k":"dbg","v":"()"}}'),
    ])
    c = delta_census(db)
    assert c["line_events"] == 3 and c["line_deltas"] == 3
    assert c["line_deltas_unread"] == 1
    assert c["line_deltas_truncated"] == 1
    assert c["unread_delta_names"] == {"journal": 1}
    assert c["truncated_delta_names"] == {"p": 1}
    assert c["all_captures"] == 4          # 3 deltas + 1 RETURN value
    assert c["bit0_ever_set"] is False


def test_bit0_is_read_from_a_LINE_payload_and_NEVER_from_a_CALL(tmp_path):
    """The trap this count would otherwise fall into.

    `flags.bit0` means a delta did not fit and every later one was dropped
    (`sensorium-rt/src/line.rs`), and the converter spells it as
    `"unread": ["locals"]` on the LINE payload (`frames.rs:367`). But EVERY
    Rust CALL row carries `{"args": {}, "unread": ["locals"]}` as well —
    Rust CALL rows have no args at all (`frames.rs:162`) — so a census that
    looked for the key anywhere would report a dropped delta on every single
    activation and §1.4's honesty count would be a constant."""
    db = _trace_with_payloads(tmp_path, [
        (1, "CALL", 10, '{"args":{},"unread":["locals"]}'),
        (2, "LINE", 11, '{"deltas":{"a":{"k":"dbg","trunc":false,"v":"1"}}}'),
    ])
    c = delta_census(db)
    assert c["bit0_ever_set"] is False
    assert c["line_rows_with_dropped_locals"] == 0
    other = tmp_path / "x"
    other.mkdir()
    db2 = _trace_with_payloads(other, [
        (1, "CALL", 10, '{"args":{},"unread":["locals"]}'),
        (2, "LINE", 11, '{"deltas":{},"unread":["locals"]}'),
    ])
    c2 = delta_census(db2)
    assert c2["bit0_ever_set"] is True
    assert c2["line_rows_with_dropped_locals"] == 1


def test_an_unparseable_payload_is_skipped_and_not_a_crash(tmp_path):
    """The census walks every payload in the trace. One row the converter
    wrote in a shape this reader does not know must not take an hour-long
    run's last phase down."""
    db = _trace_with_payloads(tmp_path, [
        (1, "LINE", 11, "not json at all"),
        (2, "LINE", 12, "[1, 2, 3]"),
        (3, "LINE", 13, '{"deltas":{"a":{"k":"unread"}}}'),
    ])
    c = delta_census(db)
    assert c["line_events"] == 1 and c["line_deltas_unread"] == 1
