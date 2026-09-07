"""The E9 endpoints, cell by cell: H1-H7 in the pre-registered shape.

A module of its own because `acceptance_e9_schema.py` reached 782 lines and
no file in this repository may pass 800. The seam is the one the schema
already had: this file builds the SEVEN ENDPOINT BLOCKS and owns the rules
that decide when a cell is not-measured; `acceptance_e9_schema.assemble_e9`
puts them beside the environment, the predictions and the ungated block. Every
name here is re-exported from the schema, so no caller's spelling changed.

TWO RULES THIS FILE ENFORCES BY ITSELF
--------------------------------------
* **A killed arm publishes nulls with the reason.** §1's four recordings and
  every reader command carry a ceiling; a command that hit it leaves partial
  text that parses exactly like a whole answer, so every cell whose number is
  only true of a COMPLETE answer becomes `null` with the kill as its reason
  (the rule `acceptance_grain_schema` added on the entry slice's review).
  `MEASUREMENT_CELLS` is the list that rule walks, and
  `tests/test_acceptance_e9_record.py` checks it against the assembled
  record's own keys so a cell cannot escape it by being forgotten.
* **No cell is ever filled from a prediction.** §1's numbers -- N = 26,
  §1.1's per-line table, the three `watch` triples' classes and exits, the
  two sightings -- are published under `predictions`, beside the
  measurements and never inside one. A block that fell back to §1 when a
  phase did not run would report the pre-registration as its own result, and
  no endpoint could fail.
"""

from __future__ import annotations

from acceptance_lib import meas
from acceptance_schema_rung3 import _drop                          # noqa: F401

#: completeness test and the schema cannot list different sets.
MEASUREMENT_CELLS = {
    "H1": ("headline", "capabilities_line", "capabilities_locals",
           "watch_exit", "watch_verdict_class", "refusal_sentence_equal"),
    "H2": ("headline", "outcomes_equal", "line_qualname_sets",
           "exit_status_equal", "focused_build_failures"),
    "H3": ("headline", "equals_the_gate", "line_differences", "activations",
           "joins_agree", "in_the_accounted_range"),
    "H4": ("headline", "class_as_predicted", "exit_as_predicted",
           "readings_disagree"),
    "H5": ("headline", "unpredicted_gated_sightings",
           "whole_trace_sightings"),
    "H6": ("headline", "libtest_s", "invocation_s"),
    "H7": ("headline", "corpus_rc", "corpus_errors", "corpus_skipped",
           "pytest_rc", "pytest_summary", "cargo_rc"),
}


def measurement_keys(block: dict) -> set:
    """Every key of one endpoint whose value IS a measurement.

    Derived from the assembled block rather than declared, so
    `MEASUREMENT_CELLS` can be CHECKED against what the schema actually
    publishes. A cell that was added to a block and forgotten in the list
    would escape `_apply_record_drops` entirely and publish a number from a
    killed recording -- which is exactly what happened to H3's
    `in_the_accounted_range` on the first round.
    """
    return {k for k, v in block.items()
            if isinstance(v, dict)
            and {"value", "n", "lens", "dropped"} <= set(v)}


#: The one sentence every "this phase did not run" reason is built from, so
#: the cells cannot drift apart in what they say they did not measure.
NOT_RUN = "the phase did not run, so there is nothing to compare"

#: The recordings each endpoint's numbers are only true of. A recording that
#: was killed, exited non-zero or left no trace makes every cell of that
#: endpoint not-measured -- the rule the entry slice's review added, applied
#: here to the RECORDINGS rather than to a reader's answer: a killed `cargo
#: sensorium` leaves partial text that parses exactly like a whole one.
NEEDS = {"H1": ("U1",), "H2": ("U1", "F1", "U2", "F2"), "H3": ("F1",),
         "H4": ("F1", "F2"), "H5": ("F1",), "H6": ("U1", "F1", "U2", "F2")}

#: The cells of each endpoint that SURVIVE a dropped recording, because what
#: they report happened before the recording could fail. H2's resolution is
#: the only such reading: the driver prints its `focus:` lines and refuses a
#: focus that names nothing BEFORE cargo is invoked (design §2.2), so a
#: focused build that then failed still resolved -- and the count of focused
#: runs that did not complete is exactly the fact a drop reports. Every other
#: cell of every other endpoint is derived from a trace.
SURVIVES_A_DROPPED_RECORDING = {"H2": ("headline", "focused_build_failures")}


def _null_cells(block: dict, names, reasons: list) -> dict:
    """Turn the named cells of `block` into not-measured, keeping their lens
    and their `n` and carrying every reason.

    A cell that is not a measurement (a raw sub-table, a command string) is
    left alone, and one that is already `null` keeps the reason it has.
    """
    if not reasons:
        return block
    for name in names:
        cell = block.get(name)
        if not isinstance(cell, dict) or "lens" not in cell:
            continue
        if cell.get("value") is None:
            cell["dropped"] = list(dict.fromkeys(
                list(cell["dropped"]) + reasons))
            continue
        nulled = _null(reasons[0], cell["lens"], cell["n"])
        nulled["dropped"] = list(dict.fromkeys(
            nulled["dropped"] + list(cell["dropped"]) + reasons[1:]))
        block[name] = nulled
    return block


def _apply_record_drops(block: dict, endpoint: str, reasons: list) -> dict:
    """Null every cell of `block` whose number is only true of a COMPLETE
    recording, with the recording's own reason attached.

    Called after each `_h*` builds its cells, so one rule covers every
    endpoint instead of seven copies that could drift.
    """
    keep = SURVIVES_A_DROPPED_RECORDING.get(endpoint, ())
    names = [n for n in MEASUREMENT_CELLS.get(endpoint, ()) if n not in keep]
    return _null_cells(block, names, reasons)


def _null(reason: str, lens: str, n=None) -> dict:
    return meas(None, n, lens, [reason])


def _records(raw) -> dict:
    return ((raw.get("raw_records") or {}).get("runs") or {})


def _record_drops(raw, endpoint: str) -> list[str]:
    """Why this endpoint's numbers may not be trusted, named per recording.

    A run that timed out, exited non-zero or produced no trace makes every
    number derived from it not-measured; a run that is simply absent from
    the record does too, and says so differently.
    """
    runs = _records(raw)
    out = []
    for name in NEEDS.get(endpoint, ()):
        r = runs.get(name)
        if r is None:
            out.append(f"{name} is absent from the record")
            continue
        if r.get("timed_out"):
            out.append(f"{name} was KILLED at {r.get('kill_s')} s; its "
                       "output is partial")
        elif r.get("rc") not in (0,):
            out.append(f"{name} exited {r.get('rc')}")
        elif not r.get("run"):
            out.append(f"{name} produced no trace")
    return out


def _reader_drop(block: dict | None, name: str) -> list[str]:
    """A reader command that hit its ceiling, as a reason."""
    if not block:
        return []
    if block.get("timed_out"):
        return [f"`{name}` was KILLED at {block.get('kill_s')} s; its output "
                "is partial"]
    return []

# ------------------------------------------------------------------- H1


H1_LENS = ("U1 -- `cargo sensorium test -p bloomery-daemon --test "
           "pager_obligation_test` on the clone at e209ed9 -- then `info "
           "<run>`, a `select count(*) from events where kind = 'LINE'` over "
           "the WHOLE trace, and `watch <run> --at "
           "missing_stats_is_a_contract_violation_not_a_reply --expr events "
           "== 0`")


def _h1(raw) -> dict:
    r = raw.get("raw_h1")
    dropped = _drop(raw, "raw_h1") + _record_drops(raw, "H1")
    if not r or r.get("dropped"):
        why = (r or {}).get("dropped") or NOT_RUN
        return {
            "headline": _null(why, "LINE rows over the whole U1 trace; "
                              + H1_LENS),
            "capabilities_line": _null(why, "meta `capabilities.line`"),
            "capabilities_locals": _null(why, "meta `capabilities.locals`"),
            "watch_exit": _null(why, "the exit status `watch` returned"),
            "watch_verdict_class": _null(why, "the class `watch` printed"),
            "refusal_sentence_equal": _null(
                why, "the pinned refusal with §2's recorded recorder token "
                     "substituted"),
        }
    w = r.get("watch") or {}
    watch_killed = _reader_drop(w, "watch")
    block = {
        "headline": meas(r.get("line_rows"), None,
                         "LINE rows over the whole U1 trace -- the gate is "
                         "0; " + H1_LENS, dropped),
        "capabilities_line": meas(
            r.get("capabilities_line"), None,
            "the trace's own meta `capabilities.line`, read from the "
            "converted trace and not from the printed row", dropped),
        "capabilities_locals": meas(
            r.get("capabilities_locals"), None,
            "the trace's own meta `capabilities.locals`", dropped),
        "watch_exit": meas(r.get("watch_exit"), None,
                           "the exit status `watch` returned -- 3 is "
                           "UNSETTLED, `record again with what it lacks`",
                           dropped),
        "watch_verdict_class": meas(
            w.get("verdict_class"), len(w.get("classes") or []),
            "the class `watch` printed, of the verdict sentences found "
            "(more than one is itself a defect and leaves the class null)",
            dropped),
        "refusal_sentence_equal": meas(
            r.get("refusal_equal"), None,
            "SECOND reading: the pinned refusal sentence with the version "
            "token taken from the trace's own `recorder` meta value -- §1 "
            "reads that token from §2, never from the design's plan",
            dropped),
        "recorder": r.get("recorder"),
        "expected_refusal": r.get("expected_refusal"),
        "printed_refusal": w.get("refusal_line"),
        "info": {k: v for k, v in (r.get("info") or {}).items()
                 if k != "stdout"},
        "info_stdout": (r.get("info") or {}).get("stdout"),
        "watch_stdout": w.get("stdout"),
        "watch_command": w.get("command"),
        "line_rows_query": r.get("line_rows_query"),
        "run": r.get("run"),
    }
    # A `watch` cut off at its ceiling printed part of an answer: the class
    # parsed out of it is not the class the command would have printed, and
    # the exit status it never returned is `None`. The LINE count above is a
    # sqlite read and is untouched by it.
    _null_cells(block, ("watch_exit", "watch_verdict_class",
                        "refusal_sentence_equal"), watch_killed)
    return _apply_record_drops(block, "H1", _record_drops(raw, "H1"))


# ------------------------------------------------------------------- H2


H2_LENS = ("the driver's own `focus:` lines, printed on stderr BEFORE cargo "
           "was invoked, and each focused run's libtest summary against its "
           "unfocused partner's (F1/U1 and F2/U2)")


def _h2(raw) -> dict:
    r = raw.get("raw_h2")
    dropped = _drop(raw, "raw_h2") + _record_drops(raw, "H2")
    if not r:
        return {
            "headline": _null(NOT_RUN, "focus values resolving to exactly "
                                       "one qualname; " + H2_LENS, 2),
            "outcomes_equal": _null(NOT_RUN, "pairs whose libtest counts are "
                                             "equal", 2),
            "line_qualname_sets": _null(NOT_RUN, "focused traces whose LINE "
                                                 "qualname set is exactly "
                                                 "the focus value", 2),
            "exit_status_equal": _null(NOT_RUN, "pairs whose process exit "
                                                "status is equal", 2),
            "focused_build_failures": _null(NOT_RUN, "focused runs that did "
                                                     "not complete", 2),
        }
    res = r.get("resolution") or {}
    qn = r.get("line_qualnames") or {}
    pairs = r.get("pairs") or {}
    measurable_qn = {k: v for k, v in qn.items() if "dropped" not in v}
    block = {
        "headline": meas(
            sum(1 for v in res.values() if v["resolved_to_exactly_one"]),
            len(res),
            "FIRST reading: `--focus` values that resolved to exactly one "
            "qualname, of the values given; " + H2_LENS, dropped),
        "outcomes_equal": meas(
            sum(1 for p in pairs.values() if p["outcome_equal"]), len(pairs),
            "FIRST reading of `equal outcome`: pairs whose summed libtest "
            "pass/fail/ignored/measured/filtered counts are equal, of the "
            "pairs", dropped),
        "line_qualname_sets": meas(
            (sum(1 for v in measurable_qn.values()
                 if v["is_exactly_the_focus_value"])
             if measurable_qn else None),
            len(qn),
            "SECOND reading of `resolved to that one`: focused traces whose "
            "set of distinct qualnames carrying LINE rows is exactly the "
            "focus value, of the focused runs",
            dropped + [f"{k}: {v['dropped']}" for k, v in qn.items()
                       if "dropped" in v]),
        "exit_status_equal": meas(
            sum(1 for p in pairs.values() if p["exit_status_equal"]),
            len(pairs),
            "SECOND reading of `equal outcome`: pairs whose `cargo "
            "sensorium` process exit status is equal, of the pairs",
            dropped),
        "focused_build_failures": meas(
            len((raw.get("raw_records") or {}).get("focused_build_failed")
                or r.get("focused_build_failed") or []), 2,
            "focused runs that did not complete -- §1's kill 1 makes any a "
            "STOP: no unfocused fallback, no narrower focus, no retry",
            dropped),
        "resolution": res, "pairs": pairs, "line_qualnames": qn,
        "failed_runs": r.get("focused_build_failed"),
    }
    # The resolution half of H2 happened BEFORE cargo was invoked (design
    # §2.2), so it survives a build that then failed; the outcome halves do
    # not -- comparing a killed run's counts to a whole one's is comparing
    # nothing. `SURVIVES_A_DROPPED_RECORDING` names which is which.
    return _apply_record_drops(block, "H2", dropped)


# ------------------------------------------------------------------- H3


H3_LENS = ("F1's trace: the LINE rows of the activations of focus value A, "
           "joined `events` (kind LINE) -> `frames` -> `code_objects` on the "
           "qualname, as a per-line histogram; the same rows counted through "
           "the event's own `code_id` are recorded beside them and must "
           "agree")


def _h3(raw) -> dict:
    r = raw.get("raw_h3")
    dropped = _drop(raw, "raw_h3") + _record_drops(raw, "H3")
    if not r or r.get("dropped"):
        why = (r or {}).get("dropped") or NOT_RUN
        return {
            "headline": _null(why, "N, the LINE rows of the single "
                              "activation; " + H3_LENS, 26),
            "equals_the_gate": _null(why, "N == 26"),
            "line_differences": _null(why, "lines that differ from §1.1's "
                                           "hand count"),
            "activations": _null(why, "activations of the focus value"),
            "joins_agree": _null(why, "the frame join and the code join "
                                      "count the same rows"),
            "in_the_accounted_range": _null(
                why, "N is inside {25, 26, 27}; outside it is §1's kill 4"),
        }
    diff = r.get("diff") or {}
    block = {
        "headline": meas(r.get("N"), r.get("expected_total"),
                         "N: the LINE rows of focus value A's activation, of "
                         "§1.1's hand count; the gate is 26, 25 and 27 are "
                         "the two readings §1.1 accounts for, anything else "
                         "is a STOP; " + H3_LENS, dropped),
        "equals_the_gate": meas(r.get("equals_gate"), r.get("gate_N"),
                                "N equals §1.1's reading A, the gate",
                                dropped),
        "line_differences": meas(
            diff.get("differences"), r.get("expected_total"),
            "SECOND reading: missing + unexpected + count-differing lines "
            "against §1.1's per-line table, of its 26 rows -- this is what "
            "lets a miss NAME lines rather than report a number", dropped),
        "activations": meas(r.get("activations"), None,
                            "frames whose code object is focus value A -- §1 "
                            "derives N from ONE activation, so anything but "
                            "1 changes what N means", dropped),
        "joins_agree": meas(r.get("joins_agree"), None,
                            "the frame join and the code-object join count "
                            "the same rows; a disagreement is a finding "
                            "about attribution, not a number to choose",
                            dropped),
        "in_the_accounted_range": meas(
            r.get("in_accounted_range"), len(r.get("accounted_range") or []),
            "N is inside {25, 26, 27}; outside it is §1's kill 4, a STOP",
            dropped),
        "measured_by_line": r.get("by_line"),
        "measured_by_line_via_code_id": r.get("by_line_via_code_id"),
        "diff": diff,
        "run": r.get("run"), "frame_ids": r.get("frame_ids"),
    }
    return _apply_record_drops(block, "H3", dropped)


# ------------------------------------------------------------------- H4


H4_LENS = ("§1.2's three triples, each `watch <run> --at <qualname> --expr "
           "<expr>` on the run named there; the verdict CLASS the command "
           "printed and the EXIT status it returned are read separately, and "
           "a disagreement between them is a finding about `Verdict`/"
           "`STATUS` rather than a reading resolved in favour of either")


def _h4(raw) -> dict:
    r = raw.get("raw_h4")
    dropped = _drop(raw, "raw_h4") + _record_drops(raw, "H4")
    if not r:
        return {
            "headline": _null(NOT_RUN, "triples as predicted on BOTH "
                              "readings; " + H4_LENS, 3),
            "class_as_predicted": _null(NOT_RUN, "verdict classes as "
                                                 "predicted", 3),
            "exit_as_predicted": _null(NOT_RUN, "exit statuses as "
                                                "predicted", 3),
            "readings_disagree": _null(NOT_RUN, "triples where the class and "
                                                "the exit disagree", 3),
        }
    rows = r.get("triples") or []
    measured = [t for t in rows if "dropped" not in t]
    killed = [t["id"] for t in measured if t.get("timed_out")]
    dropped = dropped + [f"{t['id']}: {t['dropped']}" for t in rows
                         if "dropped" in t]
    if killed:
        dropped = dropped + [f"{i} was KILLED; its answer is partial"
                             for i in killed]
    n = len(rows)
    if not measured or killed:
        why = ("every triple was dropped" if not measured
               else f"triple(s) {killed} hit the reader ceiling")
        block = {k: _null(why, H4_LENS, n) for k in
                 ("headline", "class_as_predicted", "exit_as_predicted",
                  "readings_disagree")}
        for cell in block.values():
            cell["dropped"] += dropped
    else:
        block = {
            "headline": meas(r.get("as_predicted"), n,
                             "triples whose verdict class AND exit status "
                             "are both as §1.2 predicts, of the three; "
                             + H4_LENS, dropped),
            "class_as_predicted": meas(
                sum(1 for t in measured if t["class_as_predicted"]), n,
                "FIRST reading: verdict classes as predicted "
                "(SATISFIED / NOTHING WAS CHECKED / not satisfied)", dropped),
            "exit_as_predicted": meas(
                sum(1 for t in measured if t["exit_as_predicted"]), n,
                "SECOND reading: exit statuses as predicted (0 / 3 / 1)",
                dropped),
            "readings_disagree": meas(
                len(r.get("class_disagreements") or []), n,
                "triples where the class and the exit do not agree -- itself "
                "a finding about `Verdict`/`STATUS`", dropped),
        }
    block["triples"] = [{k: v for k, v in t.items() if k != "stdout"}
                        for t in rows]
    block["stdout"] = {t["id"]: t.get("stdout") for t in rows
                       if t.get("stdout")}
    block["disagreeing"] = r.get("class_disagreements")
    # §1.4 reports W1's and W3's hit AND not-captured counts without a gate.
    # They come from `watch`'s own counts line, which is the only complete
    # source: the verdict sentence carries two of the five buckets and the
    # HIT rows below it are a page.
    block["bucket_counts"] = {
        t.get("id"): {k: t.get(k) for k in
                      ("sites", "evaluated", "hits", "not_captured",
                       "errors", "counts_line")}
        for t in (r.get("triples") or []) if "dropped" not in t}
    return _apply_record_drops(block, "H4", _record_drops(raw, "H4"))


# ------------------------------------------------------------------- H5


H5_LENS = ("§1.3's two `flow <F1 run> --value <literal>` sightings; the GATE "
           "is the sighting set restricted to focus value A's LINE deltas, "
           "and every sighting anywhere in the trace is reported beside it "
           "-- the unfocused `common::pager` helpers are still instrumented "
           "at the call tier and their RETURN values carry the same texts")


def _h5(raw) -> dict:
    r = raw.get("raw_h5")
    dropped = _drop(raw, "raw_h5") + _record_drops(raw, "H5")
    if not r or r.get("dropped"):
        why = (r or {}).get("dropped") or NOT_RUN
        return {
            "headline": _null(why, "sightings found at the predicted line; "
                              + H5_LENS, 2),
            "unpredicted_gated_sightings": _null(
                why, "sightings among A's LINE deltas at any other line"),
            "whole_trace_sightings": _null(
                why, "SECOND reading: every printed sighting row"),
        }
    rows = r.get("sightings") or []
    killed = [s["id"] for s in rows if s.get("timed_out")]
    if killed:
        dropped = dropped + [f"{i} was KILLED; its answer is partial"
                             for i in killed]
        block = {k: _null(f"sighting(s) {killed} hit the reader ceiling",
                          H5_LENS, len(rows))
                 for k in ("headline", "unpredicted_gated_sightings",
                           "whole_trace_sightings")}
        for cell in block.values():
            cell["dropped"] += dropped
    else:
        block = {
            "headline": meas(
                sum(1 for s in rows if s["found_at_predicted_line"]),
                len(rows),
                "FIRST reading (the gate): sightings found among focus value "
                "A's LINE deltas at the line §1.3 derives, of the two; "
                + H5_LENS, dropped),
            "unpredicted_gated_sightings": meas(
                sum(len(s["unpredicted_gated_rows"]) for s in rows),
                len(rows),
                "sightings of the literal among A's LINE deltas at any OTHER "
                "line -- the gate is 0, and `--value` is equality, never a "
                "prefix test", dropped),
            "whole_trace_sightings": meas(
                {s["id"]: s["sighting_events"] for s in rows}, len(rows),
                "SECOND reading (reported, not gated): every sighting of the "
                "literal ANYWHERE in the trace, per literal, gated set "
                "included -- `flow`'s own `sightings:` count, which it "
                "computes over its whole scope and not over the printed "
                "page (`flow_cmd._print_footer`)", dropped),
        }
    # §1.3's command has no `--limit` and `flow`'s default page is 50. The
    # runner asks for 1000, and if the footer STILL says the page is smaller
    # than the sighting set then every number below was read off part of an
    # answer: the gate is not-measured, with the truncation as its reason.
    truncated = [s["id"] for s in rows if s.get("page_truncated")]
    if truncated:
        # `whole_trace_sightings` is in the list even though its number comes
        # from `flow`'s whole-scope count rather than from the page: on a
        # truncated answer the two readings were computed over different
        # things, and publishing one of them beside a nulled gate would let a
        # reader take the pair for a comparison.
        _null_cells(block, ("headline", "unpredicted_gated_sightings",
                            "whole_trace_sightings"),
                    [f"the printed page of sighting(s) {truncated} was "
                     "SMALLER than the sighting set; every gated count comes "
                     "from the printed rows"])
    block["page_truncated"] = truncated
    block["sightings"] = [{k: v for k, v in s.items() if k != "stdout"}
                          for s in rows]
    block["stdout"] = {s["id"]: s.get("stdout") for s in rows
                       if s.get("stdout")}
    return _apply_record_drops(block, "H5", _record_drops(raw, "H5"))


# ------------------------------------------------------------------- H6


H6_LENS = ("F1 against U1 and F2 against U2, under both readings: libtest's "
           "own reported time (`finished in <n>s`, summed over the run's "
           "targets) and the wall of the whole `cargo sensorium` invocation "
           "including the focused rebuild")


def _h6(raw) -> dict:
    r = raw.get("raw_h6")
    dropped = _drop(raw, "raw_h6") + _record_drops(raw, "H6")
    if not r:
        return {"headline": _null(NOT_RUN, "the slowest invocation, s; "
                                  + H6_LENS, 4),
                "libtest_s": _null(NOT_RUN, "libtest's own reported time, s",
                                   4),
                "invocation_s": _null(NOT_RUN, "invocation walls, s", 4)}
    walls = {k: v for k, v in (r.get("walls_s") or {}).items()
             if v is not None}
    libtest = r.get("libtest_s") or {}
    if walls:
        headline = meas(max(walls.values()), len(walls),
                        "REPORTED, NOT GATED: the slowest of the four "
                        "invocation walls, seconds, of the runs timed; "
                        + H6_LENS, dropped)
    else:
        # `max` of nothing is not a slowest run. `null` with an empty
        # `dropped` is the one shape this schema forbids.
        headline = _null("H6 ran but timed no invocation, so there is no "
                         "slowest wall", H6_LENS, 0)
        headline["dropped"] += dropped
    block = {
        "headline": headline,
        "libtest_s": meas(libtest, len(libtest),
                          "FIRST reading: libtest's own reported time per "
                          "run, seconds (null for a run whose summary line "
                          "carried none)", dropped),
        "invocation_s": meas(r.get("walls_s"), len(r.get("walls_s") or {}),
                             "SECOND reading: the wall of each whole `cargo "
                             "sensorium` invocation, seconds", dropped),
        "pairs": r.get("pairs"),
        "trace_bytes": r.get("trace_bytes"),
    }
    return _apply_record_drops(block, "H6", dropped)


# ------------------------------------------------------------------- H7


H7_LENS = ("THIS repository, not the clone: `corpus/run_corpus.py --json` "
           "over EVERY case (the six new Rust focus cases included) under a "
           "FRESH corpus target and `SENSORIUM_CARGO_SENSORIUM`; the whole "
           "Python suite under `plain_env()` plus that same variable, so the "
           "module skipped without a built driver RUNS; and `cargo test "
           "--workspace` in `rust/` under the workspace target")


def _h7(raw) -> dict:
    r = raw.get("raw_h7")
    dropped = _drop(raw, "raw_h7")
    if not r:
        return {"headline": _null(NOT_RUN, "corpus failures; " + H7_LENS),
                "corpus_rc": _null(NOT_RUN, "the collector's exit status"),
                "corpus_errors": _null(NOT_RUN, "cases that crashed the "
                                                "collector"),
                "corpus_skipped": _null(NOT_RUN, "cases the collector "
                                                 "SKIPPED"),
                "pytest_rc": _null(NOT_RUN, "`pytest -q` exit status"),
                "pytest_summary": _null(NOT_RUN, "the suite's summary line"),
                "cargo_rc": _null(NOT_RUN, "`cargo test --workspace` exit "
                                           "status")}
    c, py, cargo = (r.get("corpus") or {}), (r.get("python") or {}), \
        (r.get("cargo") or {})
    c_drop = dropped + _reader_drop(c, "run_corpus")
    failures = c.get("failures")
    out = {
        "headline": meas(
            (len(failures) if failures is not None else None),
            c.get("questions"),
            "FIRST reading: corpus questions whose printed answer is not the "
            "case's registered expectation, of the questions asked; "
            + H7_LENS,
            c_drop + ([] if failures is not None
                      else ["the collector printed no JSON to read failures "
                            "from"])),
        "corpus_rc": meas(c.get("rc"), c.get("cases"),
                          "SECOND reading: the collector's exit status, of "
                          "the cases it ran -- 0 is every case equal",
                          c_drop),
        "corpus_errors": meas(
            (len(c.get("errors") or []) if c.get("json") is not None
             else None), c.get("cases"),
            "harness errors -- a case that crashed the collector answered "
            "nothing and is not a pass",
            c_drop + ([] if c.get("json") is not None
                      else ["the collector printed no JSON"])),
        "corpus_skipped": meas(
            (len(c.get("skipped") or []) if c.get("json") is not None
             else None), c.get("cases"),
            "cases the collector SKIPPED, of the cases -- `run_corpus` skips "
            "a cargo case when it can find no driver and still exits 0, so a "
            "green H7 over a skipped corpus is not `every case equal`; the "
            "gate is 0",
            c_drop + ([] if c.get("json") is not None
                      else ["the collector printed no JSON"])),
        "pytest_rc": meas(py.get("rc"), None,
                          "`pytest -q` exit status -- 0 is green",
                          dropped + _reader_drop(py, "pytest")),
        "pytest_summary": meas(py.get("summary"), None,
                               "the suite's own summary line, recorded whole",
                               dropped + _reader_drop(py, "pytest")),
        "cargo_rc": meas(cargo.get("rc"),
                         len(cargo.get("result_lines") or []),
                         "`cargo test --workspace` exit status, of its `test "
                         "result:` lines",
                         dropped + _reader_drop(cargo, "cargo test")),
        "corpus_failures": failures,
        # The SKIPPED rows themselves, under a name of their own: the
        # measurement cell above is `corpus_skipped`, and a second key of
        # that name in this literal silently replaced it (caught by the
        # completeness test on the first attempt).
        "corpus_skipped_cases": c.get("skipped"),
        "corpus_cases": c.get("cases"),
        "corpus_questions": c.get("questions"),
        "cargo_result_lines": cargo.get("result_lines"),
        "walls_s": {"corpus": c.get("wall_s"), "python": py.get("wall_s"),
                    "cargo": cargo.get("wall_s")},
        "logs": {"corpus": c.get("log"), "python": py.get("log"),
                 "cargo": cargo.get("log")},
        "driver_sha256_after": r.get("driver_sha256_after"),
    }
    # The same rule as everywhere else, applied to H7's three commands: a
    # collector, a suite or a `cargo test` cut off at its ceiling printed
    # part of an answer, and the exit status it never returned is `None`.
    # Only the cells that command answers are nulled.
    for names, block_, label in (
            (("headline", "corpus_rc", "corpus_errors", "corpus_skipped"),
             c, "run_corpus"),
            (("pytest_rc", "pytest_summary"), py, "pytest"),
            (("cargo_rc",), cargo, "cargo test")):
        _null_cells(out, names, _reader_drop(block_, label))
    return out
