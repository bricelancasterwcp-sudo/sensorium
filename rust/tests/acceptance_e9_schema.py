"""Raw E9 facts -> `results.json` in the pre-registered shape.

The same rules as every sibling (`acceptance_schema.assemble`,
`acceptance_schema_rung3.assemble_rung3`, `acceptance_grain_schema.
assemble_grain`): every measurement is `{"value", "n", "lens", "dropped"}`, a
`null` value with a non-empty `dropped` list is the ONLY representation of
not-measured, and `0` is measured-and-zero.

TWO RULES THIS SCHEMA ENFORCES BY ITSELF
----------------------------------------
* **A killed arm publishes nulls with the reason.** §1's four recordings and
  every reader command carry a ceiling; a command that hit it leaves partial
  text that parses exactly like a whole answer, so every cell whose number is
  only true of a COMPLETE answer becomes `null` with the kill as its reason
  (the rule `acceptance_grain_schema` added on the entry slice's review, and
  the reason this file names its killed cells in constants rather than
  inline).
* **No cell is ever filled from a prediction.** §1's numbers -- N = 26,
  §1.1's per-line table, the three `watch` triples' classes and exits, the
  two sightings -- are published under `predictions`, beside the
  measurements and never inside one. A schema that fell back to §1 when a
  phase did not run would report the pre-registration as its own result, and
  no endpoint could fail.
"""

from __future__ import annotations

from acceptance_lib import meas
from acceptance_schema_rung3 import _drop                          # noqa: F401

DOC = "docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md"

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
                {s["id"]: s["whole_trace_count"] for s in rows}, len(rows),
                "SECOND reading (reported, not gated): every printed "
                "sighting row per literal, gated set included", dropped),
        }
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
                "pytest_rc": _null(NOT_RUN, "`pytest -q` exit status"),
                "cargo_rc": _null(NOT_RUN, "`cargo test --workspace` exit "
                                           "status")}
    c, py, cargo = (r.get("corpus") or {}), (r.get("python") or {}), \
        (r.get("cargo") or {})
    c_drop = dropped + _reader_drop(c, "run_corpus")
    failures = c.get("failures")
    return {
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
        "corpus_skipped": c.get("skipped"),
        "corpus_cases": c.get("cases"),
        "corpus_questions": c.get("questions"),
        "cargo_result_lines": cargo.get("result_lines"),
        "walls_s": {"corpus": c.get("wall_s"), "python": py.get("wall_s"),
                    "cargo": cargo.get("wall_s")},
        "logs": {"corpus": c.get("log"), "python": py.get("log"),
                 "cargo": cargo.get("log")},
        "driver_sha256_after": r.get("driver_sha256_after"),
    }


# ------------------------------------------------------------- predictions


def _predictions(raw) -> dict:
    """§1's pre-committed numbers, published under their OWN name.

    They are here so a reader can check the arithmetic without opening the
    document, and they are here ONLY here: no measurement cell above falls
    back to one, which is what `tests/test_acceptance_e9.py` pins.
    """
    cfg = raw.get("config") or {}
    # RECORDED BY THE RUNNER before any phase ran, so §1's triples and
    # sightings are published even when the phase that would have used them
    # never ran -- a `predictions` block that came out of `raw_h4` would be
    # EMPTY on exactly the run whose reader a reviewer most wants to check.
    pre = raw.get("predictions") or {}
    h4 = raw.get("raw_h4") or {}
    h5 = raw.get("raw_h5") or {}
    return {
        "note": ("§1's pre-registration, recorded beside the measurements "
                 "and never inside one; a headline that borrowed from here "
                 "could not fail"),
        "focus_values": {"A": cfg.get("focus_a"), "B": cfg.get("focus_b")},
        "N": cfg.get("gate_n"),
        "accounted_N": cfg.get("accounted_n"),
        "expected_by_line": cfg.get("expected_by_line"),
        "watch_triples": pre.get("watch_triples") or [
            {k: t.get(k) for k in ("id", "run", "at", "expr",
                                   "predicted_class", "predicted_exit",
                                   "line")}
            for t in (h4.get("triples") or [])],
        "flow_sightings": pre.get("flow_sightings") or [
            {k: s.get(k) for k in ("id", "literal", "binding", "line")}
            for s in (h5.get("sightings") or [])],
        "temp_root": cfg.get("temp_root"),
        "tmpdir_observed": cfg.get("tmpdir_observed"),
    }


def _reported(raw) -> dict:
    """§1.4's ungated block, as the run recorded it."""
    h3 = raw.get("raw_h3") or {}
    h5 = raw.get("raw_h5") or {}
    h6 = raw.get("raw_h6") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    pins = raw.get("pins") or {}
    runs = _records(raw)
    return {
        "walls_s": h6.get("walls_s"),
        "libtest_s": h6.get("libtest_s"),
        "pairs": h6.get("pairs"),
        "line_histogram": h3.get("by_line"),
        "line_histogram_via_code_id": h3.get("by_line_via_code_id"),
        "line_rows_per_run": {n: (r.get("meta") or {}).get("counts")
                              for n, r in runs.items()},
        "trace_bytes": h6.get("trace_bytes"),
        "whole_trace_sightings": {s.get("id"): s.get("whole_trace_rows")
                                  for s in (h5.get("sightings") or [])},
        "gated_sightings": {s.get("id"): s.get("gated_rows")
                            for s in (h5.get("sightings") or [])},
        "driver": pins.get("driver"),
        "driver_sha256": pins.get("driver_sha256"),
        "driver_sha256_after": cl.get("driver_sha256_after"),
        "driver_built_from": pins.get("built_from"),
        "tmpdir_observed": pins.get("tmpdir_observed"),
        "tmpdir_reading": pins.get("tmpdir_reading"),
        "sensorium_tier": pins.get("sensorium_tier"),
        "invocation_log": pins.get("invocation_log"),
        "invocations_jsonl_lines": cl.get("invocations_jsonl_lines"),
        "store_bytes": cl.get("store_bytes"),
        "traces_recorded": cl.get("traces_recorded"),
        "e9_target_bytes": cl.get("e9_target_bytes"),
        "corpus_target_bytes": cl.get("corpus_target_bytes"),
        "disk_free_gb": {
            "repo_before": pins.get("repo_disk_free_gb"),
            "repo_after": cl.get("repo_disk_free_gb_after"),
            "target_before": pins.get("target_disk_free_gb"),
            "target_after": cl.get("target_disk_free_gb_after")},
        "load_at_each_phase": raw.get("arm_loads"),
    }


def _recordings(raw) -> dict:
    """The four runs as the record publishes them: what was asked, what came
    back, and no verdict."""
    keep = ("name", "command", "cwd", "focus_flags", "test_target", "rc",
            "wall_s", "timed_out", "kill_s", "log", "focus_lines",
            "focus_refusal", "cargo_exit", "run", "run_pick_rule",
            "run_candidates", "outcome", "libtest_secs", "trace_bytes")
    return {n: {k: r.get(k) for k in keep}
            | {"test_result_lines": [s["line"] for s in
                                     (r.get("test_results") or [])]}
            for n, r in _records(raw).items()}


# --------------------------------------------------------------- assemble


def assemble_e9(raw: dict) -> dict:
    """Raw E9 facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero"),
        # DERIVED, not asserted: the document this run was byte-locked
        # against, taken from the raw record's own `byte_lock.doc`. The
        # module constant is only the last resort for a raw record with no
        # byte-lock at all (a run refused before the check), where there is
        # nothing to derive from -- R-G15.
        "acceptance": ((raw.get("byte_lock") or {}).get("doc")
                       or raw.get("document") or DOC),
        "runner": raw.get("runner"),
        "byte_lock": raw.get("byte_lock"),
        "pins": pins,
        "environment": {
            "repo_commit": pins.get("repo_commit"),
            "repo_branch": pins.get("repo_branch"),
            "repo_porcelain": pins.get("repo_porcelain"),
            "repo_porcelain_after": cl.get("repo_porcelain_after"),
            "clone": pins.get("clone"),
            "clone_head": pins.get("clone_head"),
            "clone_pin": pins.get("clone_pin"),
            "clone_head_after": cl.get("clone_head_after"),
            "clone_porcelain": pins.get("clone_porcelain"),
            "clone_porcelain_after": cl.get("clone_porcelain_after"),
            "clone_cargo_lock_sha256": pins.get("clone_cargo_lock_sha256"),
            "clone_cargo_lock_sha256_after": cl.get(
                "clone_cargo_lock_sha256_after"),
            "clone_cargo_lock_moved": cl.get("clone_cargo_lock_moved"),
            "clone_cargo_lock_back_on_the_pin": cl.get(
                "clone_cargo_lock_back_on_the_pin"),
            "clone_read_only_reading": pins.get("clone_read_only_reading"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_sha256_after": cl.get("driver_sha256_after"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "driver_profile": pins.get("driver_profile"),
            "driver_mtime": pins.get("driver_mtime"),
            "driver_rebuilt_by_this_run": pins.get(
                "driver_rebuilt_by_this_run"),
            "built_from": pins.get("built_from"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "e9_target": pins.get("e9_target"),
            "rust_target": pins.get("rust_target"),
            "corpus_target": pins.get("corpus_target"),
            "corpus_target_from_env": pins.get("corpus_target_from_env"),
            "tmpdir_observed": pins.get("tmpdir_observed"),
            "tmpdir_reading": pins.get("tmpdir_reading"),
            "temp_root": pins.get("temp_root"),
            "sensorium_tier": pins.get("sensorium_tier"),
            "invocation_log": pins.get("invocation_log"),
            "invocations_jsonl_lines": cl.get("invocations_jsonl_lines"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_phase": raw.get("arm_loads"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "repo_disk_free_gb_after": cl.get("repo_disk_free_gb_after"),
            "target_disk_free_gb": pins.get("target_disk_free_gb"),
            "target_disk_free_gb_after": cl.get("target_disk_free_gb_after"),
            "logs_dir": raw.get("logs"),
        },
        "recordings": _recordings(raw),
        "endpoints": {
            "H1": _h1(raw), "H2": _h2(raw), "H3": _h3(raw), "H4": _h4(raw),
            "H5": _h5(raw), "H6": _h6(raw), "H7": _h7(raw),
        },
        "predictions": _predictions(raw),
        "reported": _reported(raw),
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "stop": raw.get("stop"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }


#: Every endpoint the schema publishes, and every cell inside it whose value
#: is a `{value, n, lens, dropped}` measurement. Named once so the
#: completeness test and the schema cannot list different sets.
MEASUREMENT_CELLS = {
    "H1": ("headline", "capabilities_line", "capabilities_locals",
           "watch_exit", "watch_verdict_class", "refusal_sentence_equal"),
    "H2": ("headline", "outcomes_equal", "line_qualname_sets",
           "exit_status_equal", "focused_build_failures"),
    "H3": ("headline", "equals_the_gate", "line_differences", "activations",
           "joins_agree"),
    "H4": ("headline", "class_as_predicted", "exit_as_predicted",
           "readings_disagree"),
    "H5": ("headline", "unpredicted_gated_sightings",
           "whole_trace_sightings"),
    "H6": ("headline", "libtest_s", "invocation_s"),
    "H7": ("headline", "corpus_rc", "pytest_rc", "cargo_rc"),
}
