#!/usr/bin/env python3
"""The E9 phases: the four recordings of §1, and H1-H7 over them.

`acceptance_e9.py` holds the lock, the locations, the preflight and `main`;
this module holds the protocols, on the seam every runner in this family
splits on (`acceptance_phases.py`, `acceptance_phases_rung3.py`,
`acceptance_grain_phases.py`).

Each phase returns RAW FACTS and decides no verdict: `acceptance_e9_schema.
assemble_e9` turns them into the none-versus-zero `results.json`, and §4 and
§5 of the acceptance document are written by hand.

Nothing here is a prediction. §1's numbers (N = 26, the three `watch`
triples, the two sightings) enter as COMPARISON TARGETS under their own
names, never as a value a cell falls back to: a phase that did not run
publishes `null` with a reason, and the schema is tested for exactly that.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import acceptance_lib as lib
from acceptance_e6ppp import logs_at, mark_load
from acceptance_e9_read import (delta_census, focus_lines,        # noqa: F401
                                histogram_diff,
                                line_deltas_of, line_histogram,
                                line_qualnames, line_rows_total,
                                outcome_counts, parse_flow, parse_info,
                                parse_watch, refusal_sentence, temp_root,
                                test_results)
from acceptance_lib import (REPO, plain_env, run, run_lines,        # noqa: F401
                            sensorium_cli, sha256_file, step)

#: The run's log ROOT. `None` here for the reason `acceptance_grain_phases.
#: LOGS` is `None`: this module owns no location, `acceptance_e9` assigns it
#: beside the other pointers, and a phase reached without that assignment
#: fails loudly on `None / "h1"` instead of writing an hour of evidence
#: somewhere plausible and wrong.
LOGS: Path | None = None

# ------------------------------------------------------- §1's four runs

#: The two focus values, exactly as §1's table spells them (`--focus` takes
#: the bare file-local qualname; neither name is nested in a `mod`).
FOCUS_A = "missing_stats_is_a_contract_violation_not_a_reply"
FOCUS_B = "pager_with_model"

#: §1's four runs, in §1's order. `focus` is the driver's own flags, placed
#: BEFORE the cargo subcommand exactly as §1's command column spells them;
#: `tail` is cargo's argv. The package is `-p bloomery-daemon` in all four.
RUNS = {
    "U1": {"focus": [], "test": "pager_obligation_test"},
    "F1": {"focus": ["--focus", FOCUS_A], "test": "pager_obligation_test"},
    "U2": {"focus": [], "test": "pager_codec_gate_test"},
    "F2": {"focus": ["--focus", FOCUS_B], "test": "pager_codec_gate_test"},
}

#: The pairs H2's "equal outcome" reading compares, and H6's two walls.
PAIRS = (("F1", "U1"), ("F2", "U2"))


def argv_of(paths, name: str) -> list[str]:
    """`cargo sensorium [--focus <v>] test -p bloomery-daemon --test <t>`.

    Spelled from `RUNS` so the record's command column and the command
    actually run cannot drift: the driver is invoked as cargo invokes it
    (`<driver> sensorium …`), which is what `acceptance_lib.driver_cmd`
    does for the unfocused case and what this generalises for `--focus`.
    """
    spec = RUNS[name]
    return [str(paths["sensorium_driver"]), "sensorium", *spec["focus"],
            "test", "-p", "bloomery-daemon", "--test", spec["test"]]


def record_env(paths) -> dict:
    """The environment every recording runs under.

    `plain_env()` strips every `SENSORIUM_*` and `CARGO_TARGET_DIR` from the
    launcher's environment; what a recording needs is put back here and
    NOTHING else. In particular `SENSORIUM_TIER` is not set (§1.4 leaves the
    coarse tier at its default `call`) and `SENSORIUM_NO_INVOCATION_LOG` is
    not set (§1.4 does not silence the audit log), so both facts are
    properties of this function rather than of whoever launched the run.
    """
    return plain_env() | {
        "CARGO_TARGET_DIR": str(paths["sensorium_e9_target"]),
        "SENSORIUM_DIR": str(paths["sensorium_dir"]),
    }


def guarded(cmd, cwd, log_name, env, timeout, tag) -> dict:
    """`acceptance_lib.run` with the timeout recorded as a FACT.

    A `TimeoutExpired` that escaped would take every later phase down with
    it and lose the endpoints already measured; §1's kill criteria make a
    timed-out arm a recorded not-measured, not a crash. `acceptance_lib.run`
    writes its log after the call returns, so a killed command leaves none
    and the partial output is written here instead -- the same shape
    `acceptance_grain_phases._ask` uses.
    """
    t0 = time.monotonic()
    try:
        res = run(cmd, cwd, log_name, env, timeout=timeout)
        res["timed_out"] = False
    except subprocess.TimeoutExpired as e:
        wall = time.monotonic() - t0
        parts = []
        for stream in (e.output, getattr(e, "stderr", None)):
            if stream is None:
                continue
            parts.append(stream if isinstance(stream, str)
                         else stream.decode("utf-8", "replace"))
        text = "\n".join(parts)
        log = (lib.LOGS or Path(".")) / f"{log_name}.KILLED.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"$ {' '.join(str(c) for c in cmd)}\n(cwd={cwd})\n"
                       f"--- KILLED at {timeout} s (wall {wall:.3f}) ---\n"
                       f"--- partial output ---\n{text}\n")
        res = {"rc": None, "out": text, "err": "", "wall": wall,
               "log": str(log), "timed_out": True}
        step(f"{tag}: KILLED at {timeout} s ({len(text)} byte(s) printed)")
    res["command"] = " ".join(str(c) for c in cmd)
    res["kill_s"] = timeout
    return res


def pick_run(lines: list[dict], test_target: str) -> dict:
    """Which `run:` line is the TEST BINARY's, and by which rule.

    `cargo test --test <t>` can leave more than one converted process behind
    (a build script, a proc-macro helper), and every number below is about
    the test binary. The rule is stated and recorded rather than assumed:
    the process whose `exe` basename starts with the target name, and -- if
    no `exe` says so -- the process with the most events, which is named as
    a FALLBACK in the record so a reader knows which rule fired.
    """
    named = [ln for ln in lines
             if Path(ln["exe"]).name.startswith(test_target)]
    if len(named) == 1:
        return {"run": named[0]["run"], "rule": "exe basename matches the "
                                                "--test target", "row": named[0]}
    if named:
        best = max(named, key=lambda ln: ln["events"])
        return {"run": best["run"], "rule": "several exe names match the "
                                            "--test target; the busiest",
                "row": best, "candidates": [ln["run"] for ln in named]}
    if lines:
        best = max(lines, key=lambda ln: ln["events"])
        return {"run": best["run"], "rule": "FALLBACK: no exe basename "
                                            "matches the --test target; the "
                                            "busiest process", "row": best,
                "candidates": [ln["run"] for ln in lines]}
    return {"run": None, "rule": "no `run:` line was printed", "row": None}


def record(paths, cfg, name: str) -> dict:
    """One of §1's four runs, recorded once.

    The wall is taken around the WHOLE `cargo sensorium` invocation (H6's
    second reading, which includes the focused rebuild); libtest's own
    reported time is parsed out of the summary line (H6's first reading).
    """
    spec = RUNS[name]
    cmd = argv_of(paths, name)
    with logs_at(LOGS / f"record-{name.lower()}"):
        step(f"{name}: {' '.join(cmd[1:])}")
        res = guarded(cmd, paths["sensorium_bloomery"], f"{name.lower()}.log",
                      record_env(paths), cfg["cargo_timeout"], name)
    both = "\n".join((res["out"], res["err"]))
    summaries = test_results(both)
    lines = run_lines(res)
    picked = pick_run(lines, spec["test"])
    out = {
        "name": name, "command": res["command"], "cwd": str(
            paths["sensorium_bloomery"]),
        "focus_flags": spec["focus"], "test_target": spec["test"],
        "rc": res["rc"], "wall_s": round(res["wall"], 3),
        "timed_out": res["timed_out"], "kill_s": res["kill_s"],
        "log": res["log"],
        # H2's resolution evidence, read from stderr BEFORE cargo ran.
        "focus_lines": focus_lines(res["err"]),
        "focus_refusal": next((ln for ln in res["err"].splitlines()
                               if ln.startswith("REFUSED: --focus")), None),
        "cargo_exit": lib.cargo_exit_of(res),
        "run_lines": lines, "run": picked["run"], "run_pick_rule": picked["rule"],
        "run_candidates": picked.get("candidates"),
        "test_results": summaries,
        "outcome": outcome_counts(summaries),
        # H6, first reading: libtest's own time, summed over the targets --
        # and `None`, never 0.0, when no summary carried a `finished in`. A
        # zero would compare EQUAL to a run that reported nothing and would
        # read in §3 as "the focused binary took no time at all".
        "libtest_secs": (sum(s["libtest_secs"] for s in summaries)
                         if summaries and all(s["libtest_secs"] is not None
                                              for s in summaries) else None),
        "trace_bytes": None, "census": None, "truncated_count": None,
    }
    out.update(_outcome_class(out, summaries, res))
    if out["run"] and _trace_db(paths, out["run"]).is_file():
        out["trace_bytes"] = lib.trace_bytes(paths, out["run"])
        out["meta"] = lib.trace_meta(paths, out["run"])
        # §1.4's ungated honesty counts, per run.
        out["census"] = delta_census(_trace_db(paths, out["run"]))
        out["truncated_count"] = (out["meta"] or {}).get("truncated_count")
    step(f"{name}: rc={out['rc']} run={out['run']} focus={out['focus_lines']} "
         f"outcome={out['outcome']} wall={out['wall_s']}s")
    return out


#: What a non-zero `cargo sensorium` exit MEANS, which §1's kill 1 turns on.
#: Kill 1 is "a compile failure of a focused unit", and only one of these
#: three is that.
COMPILE_FAILURE = "compile_failure"
TEST_FAILURE = "test_failure"
REFUSAL = "refusal"
COMPLETED = "completed"
KILLED = "killed"


def _outcome_class(out: dict, summaries: list, res: dict) -> dict:
    """Which of §1's cases this run's exit status is.

    §1's kill 1 is a COMPILE FAILURE of a focused unit -- the pattern the
    transform could not build. It is not a libtest failure (the unit built,
    ran and reported; H2's equality is what decides that) and it is not the
    driver's own `--focus` refusal (exit 2, printed before cargo is invoked
    at all: infrastructure if it happens before any number is read, and a
    STOP-worthy finding after). Collapsing the three would label a failing
    assertion in the clone's own test suite "a compile failure of a focused
    unit" and stop the rung on it.

    The discriminator is libtest's own summary line: a unit that printed one
    was compiled and run.
    """
    if out["timed_out"]:
        return {"outcome_class": KILLED,
                "outcome_class_why": f"killed at {out['kill_s']} s"}
    if out["rc"] == 0:
        return {"outcome_class": COMPLETED, "outcome_class_why": "exit 0"}
    if out["focus_refusal"] or out["rc"] == 2:
        return {"outcome_class": REFUSAL,
                "outcome_class_why": (out["focus_refusal"]
                                      or f"exit {out['rc']} before cargo ran")}
    if summaries:
        failed = sum(s["failed"] for s in summaries)
        return {"outcome_class": TEST_FAILURE,
                "outcome_class_why": (f"exit {out['rc']} with "
                                      f"{len(summaries)} libtest summary "
                                      f"line(s), {failed} test(s) failed: "
                                      "the unit compiled and ran")}
    return {"outcome_class": COMPILE_FAILURE,
            "outcome_class_why": (f"exit {out['rc']} and NO libtest summary "
                                  "line: the unit never ran")}


def phase_records(paths, cfg) -> dict:
    """§1's four runs, in §1's order.

    §1's kill criterion 1 is a COMPILE FAILURE of a focused unit, and only
    that: `focused_compile_failures` carries it, `main` writes `e9.FAILED`,
    and no unfocused fallback is attempted and no narrower focus is retried,
    so the pattern that failed is what the record holds. A focused run that
    compiled and reported a libtest FAILURE is not kill 1 -- H2's equality
    reading decides that one -- and a `--focus` refusal is a third case
    again. All three are recorded under their own names.
    """
    mark_load("records")
    runs = {}
    for name in RUNS:
        runs[name] = record(paths, cfg, name)
    by = lambda cls: [n for n in ("F1", "F2")                     # noqa: E731
                      if runs[n]["outcome_class"] == cls]
    compile_failures, refusals = by(COMPILE_FAILURE), by(REFUSAL)
    test_failures, killed_focus = by(TEST_FAILURE), by(KILLED)
    incomplete = compile_failures + refusals + test_failures + killed_focus
    if compile_failures:
        step(f"STOP (§1 kill 1): focused run(s) {compile_failures} did not "
             f"COMPILE; no unfocused fallback and no narrower focus is tried")
    for label, names in (("REFUSED by the driver", refusals),
                         ("libtest FAILURE (not kill 1; H2 decides)",
                          test_failures),
                         ("KILLED at the ceiling", killed_focus)):
        if names:
            step(f"focused run(s) {names}: {label}")
    return {"runs": runs,
            "focused_compile_failures": compile_failures,
            "focused_refusals": refusals,
            "focused_test_failures": test_failures,
            "focused_killed": killed_focus,
            # Every focused run that did not come back at exit 0, whatever
            # the reason -- the set H2's `focused_build_failures` counts and
            # the set the schema drops numbers for.
            "focused_build_failed": incomplete,
            "outcome_classes": {n: r["outcome_class"] for n, r in runs.items()},
            "killed": [n for n, r in runs.items() if r["timed_out"]]}


def _trace_db(paths, run_id: str) -> Path:
    return paths["sensorium_dir"] / "traces" / f"{run_id}.db"


def has_trace(paths, rec: dict) -> bool:
    """Is this recording's trace actually on disk?

    A KILLED `cargo sensorium` can still have printed a `run:` line for a
    process the converter never finished writing, and `sqlite3.connect(...,
    mode=ro)` on a missing file RAISES -- which would take the whole run down
    inside a phase instead of leaving a drop in the record. Every phase that
    opens a trace asks this first.
    """
    return bool(rec.get("run")) and _trace_db(paths, rec["run"]).is_file()


def _read(paths, args, tag, cfg) -> dict:
    """One query-CLI call, timeout recorded as a fact rather than raised."""
    t0 = time.monotonic()
    try:
        res = sensorium_cli(paths, args, tag, timeout=cfg["reader_timeout"])
        res["timed_out"] = False
    except subprocess.TimeoutExpired as e:
        wall = time.monotonic() - t0
        raw = e.output or ""
        text = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
        log = (lib.LOGS or Path(".")) / f"cli-{tag}.KILLED.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"$ sensorium {' '.join(str(a) for a in args)}\n"
                       f"--- KILLED at {cfg['reader_timeout']} s "
                       f"(wall {wall:.3f}) ---\n{text}\n")
        res = {"rc": None, "out": text, "err": "", "wall": wall,
               "log": str(log), "timed_out": True}
        step(f"{tag}: KILLED at {cfg['reader_timeout']} s")
    res["command"] = "sensorium " + " ".join(str(a) for a in args)
    res["kill_s"] = cfg["reader_timeout"]
    return res


# --------------------------------------------------------------------- H1


def phase_h1(paths, cfg, records) -> dict:
    """H1: does an unfocused run stay unfocused?

    Three readings of one run (U1), all recorded: the trace's own `meta`
    capabilities, a `count(*)` of LINE rows over the whole trace, and a
    `watch` that must come back as the capability REFUSAL at exit 3.

    The refusal's version token is not spelled here. §1 reads it from
    `trace.recorder` -- §2's own recorded value -- and `refusal_sentence`
    substitutes it, so a runner that hard-coded `0.4.0` would be gating on
    the design's plan rather than on the trace's claim.
    """
    mark_load("H1")
    u1 = records["runs"]["U1"]
    run_id = u1["run"]
    if not has_trace(paths, u1):
        return {"dropped": f"U1 left no trace on disk (exit {u1['rc']}, run "
                           f"{run_id!r})", "run": run_id}
    db = _trace_db(paths, run_id)
    meta = u1.get("meta") or {}
    caps = meta.get("capabilities") or {}
    recorder = meta.get("recorder")
    with logs_at(LOGS / "h1"):
        info = _read(paths, ["info", run_id], "h1-info", cfg)
        watch_args = ["watch", run_id, "--at", FOCUS_A,
                      "--expr", "events == 0"]
        w = _read(paths, watch_args, "h1-watch", cfg)
    parsed_info = parse_info(info["out"])
    parsed_watch = parse_watch("\n".join((w["out"], w["err"])))
    expected = (refusal_sentence(recorder) if recorder else None)
    # A sqlite read over the converted trace: it does not depend on the
    # `watch` above, and a count that went missing because a READER hit its
    # ceiling would report a gap H1 does not have.
    rows = line_rows_total(db)
    out = {
        "run": run_id, "trace_db": str(db),
        "meta_capabilities": caps,
        "capabilities_line": caps.get("line"),
        "capabilities_locals": caps.get("locals"),
        "recorder": recorder,
        "info": {"rc": info["rc"], "command": info["command"],
                 "log": info["log"], "stdout": info["out"],
                 "timed_out": info["timed_out"], **parsed_info},
        "line_rows": rows,
        "line_rows_query": "select count(*) from events where kind = 'LINE'",
        "watch": {"rc": w["rc"], "command": w["command"], "log": w["log"],
                  "stdout": "\n".join((w["out"], w["err"])),
                  "timed_out": w["timed_out"],
                  **parsed_watch},
        "expected_refusal": expected,
        "refusal_token_source": ("the trace's own `recorder` meta value, "
                                 "substituted into the pinned sentence"),
    }
    out["refusal_equal"] = (expected is not None
                            and parsed_watch["refusal_line"] == expected)
    out["watch_exit"] = w["rc"]
    step(f"H1: caps line={out['capabilities_line']} locals="
         f"{out['capabilities_locals']}; LINE rows {rows}; watch exit "
         f"{w['rc']}; refusal equal {out['refusal_equal']}")
    return out


# --------------------------------------------------------------------- H2


def phase_h2(paths, cfg, records) -> dict:
    """H2: does a focus resolve and build?

    First reading: each `--focus` value resolved to exactly one qualname
    (the driver's `focus:` lines, read before cargo was invoked), and each
    focused run's libtest counts equal its unfocused partner's. Second
    reading: the set of distinct qualnames carrying LINE rows in the focused
    trace, and each run's process exit status beside the counts.
    """
    mark_load("H2")
    runs = records["runs"]
    values = {"F1": FOCUS_A, "F2": FOCUS_B}
    resolution, qualnames = {}, {}
    for name, value in values.items():
        r = runs[name]
        resolution[name] = {
            "value": value, "focus_lines": r["focus_lines"],
            "matched": len(r["focus_lines"]),
            "resolved_to_exactly_one": (r["focus_lines"] == [value]),
            "refusal": r["focus_refusal"],
        }
        if has_trace(paths, r) and not r["timed_out"]:
            hist = line_qualnames(_trace_db(paths, r["run"]))
            qualnames[name] = {
                "qualnames_with_line_rows": hist,
                "set": sorted(hist),
                "is_exactly_the_focus_value": sorted(hist) == [value],
            }
        else:
            qualnames[name] = {"dropped": f"{name} left no trace on disk"}
    pairs = {}
    for focused, unfocused in PAIRS:
        f, u = runs[focused], runs[unfocused]
        pairs[f"{focused}/{unfocused}"] = {
            "focused": focused, "unfocused": unfocused,
            "focused_outcome": f["outcome"], "unfocused_outcome": u["outcome"],
            # `None`, not `False`, when either run printed no summary at
            # all: "these two are not equal" is a claim about two outcomes,
            # and an unparsed one is not an outcome.
            "outcome_equal": (None if f["outcome"] is None
                              or u["outcome"] is None
                              else f["outcome"] == u["outcome"]),
            "focused_rc": f["rc"], "unfocused_rc": u["rc"],
            "exit_status_equal": f["rc"] == u["rc"],
            "focused_summary_lines": [s["line"] for s in f["test_results"]],
            "unfocused_summary_lines": [s["line"] for s in u["test_results"]],
        }
    out = {
        "resolution": resolution, "line_qualnames": qualnames, "pairs": pairs,
        "all_resolved_to_one": all(v["resolved_to_exactly_one"]
                                   for v in resolution.values()),
        "all_outcomes_equal": all(p["outcome_equal"] for p in pairs.values()),
        "focused_build_failed": records["focused_build_failed"],
    }
    step(f"H2: resolved-to-one {out['all_resolved_to_one']}; outcomes equal "
         f"{out['all_outcomes_equal']}; focused failures "
         f"{out['focused_build_failed']}")
    return out


# --------------------------------------------------------------------- H3


def phase_h3(paths, cfg, records) -> dict:
    """H3: one LINE per completed statement?

    The LINE rows of the single activation of focus value A in F1, as a
    per-line histogram, diffed against §1.1's hand count so a difference
    NAMES lines rather than reporting a number. `expected_by_line` is
    published under its own name; no cell is ever filled from it.
    """
    mark_load("H3")
    f1 = records["runs"]["F1"]
    if not has_trace(paths, f1) or f1["timed_out"]:
        return {"dropped": f"F1 left no usable trace (exit {f1['rc']}, "
                           f"killed {f1['timed_out']})", "run": f1["run"]}
    hist = line_histogram(_trace_db(paths, f1["run"]), FOCUS_A)
    expected = dict(cfg["expected_by_line"])
    diff = histogram_diff(hist["by_line"], expected)
    n = hist["total"]
    out = {
        "run": f1["run"], **hist,
        "expected_by_line": {str(k): v for k, v in sorted(expected.items())},
        "expected_total": sum(expected.values()),
        "diff": diff,
        "N": n,
        "gate_N": cfg["gate_n"],
        "equals_gate": n == cfg["gate_n"],
        "in_accounted_range": n in cfg["accounted_n"],
        "accounted_range": sorted(cfg["accounted_n"]),
        # §1's kill 4: any count outside {25, 26, 27} is a STOP.
        "stop": n not in cfg["accounted_n"],
    }
    step(f"H3: N={n} (gate {cfg['gate_n']}); activations "
         f"{hist['activations']}; line differences {diff['differences']}; "
         f"joins agree {hist['joins_agree']}")
    return out


# --------------------------------------------------------------------- H4


def watch_triples(cfg) -> list[dict]:
    """§1.2's W1-W3, with the temp-directory prefix substituted once.

    The predicted verdict class and exit are carried BESIDE each triple as
    comparison targets, never as values a cell can fall back to.
    """
    root = cfg["temp_root"]
    return [
        {"id": "W1", "run": "F1", "at": FOCUS_A,
         "expr": f'dir == "{root}/bloomery-pager-contract"',
         "predicted_class": "SATISFIED", "predicted_exit": 0, "line": 251},
        {"id": "W2", "run": "F1", "at": FOCUS_A, "expr": "len(events) == 0",
         "predicted_class": "NOTHING WAS CHECKED", "predicted_exit": 3,
         "line": 282},
        {"id": "W3", "run": "F2", "at": FOCUS_B,
         "expr": f'dir == "{root}/bloomery-pager-contract"',
         "predicted_class": "not satisfied", "predicted_exit": 1, "line": 22},
    ]


def phase_h4(paths, cfg, records) -> dict:
    """H4: does `watch` answer? The three triples of §1.2, each on its run.

    Both readings are recorded separately -- the verdict class the command
    printed and the exit status it returned -- and their agreement is a
    field, not a resolution: §1 makes a disagreement between them a finding
    about `Verdict`/`STATUS`, so neither is derived from the other.
    """
    mark_load("H4")
    rows = []
    with logs_at(LOGS / "h4"):
        for t in watch_triples(cfg):
            src = records["runs"][t["run"]]
            if not has_trace(paths, src) or src["timed_out"]:
                rows.append({**t, "dropped": f"{t['run']} left no usable "
                                             "trace"})
                continue
            args = ["watch", src["run"], "--at", t["at"], "--expr", t["expr"]]
            res = _read(paths, args, f"h4-{t['id'].lower()}", cfg)
            p = parse_watch("\n".join((res["out"], res["err"])))
            row = {**t, "run_id": src["run"], "command": res["command"],
                   "rc": res["rc"], "timed_out": res["timed_out"],
                   "log": res["log"], "stdout": "\n".join((res["out"], res["err"])),
                   "wall_s": round(res["wall"], 3), **p}
            row["class_as_predicted"] = (p["verdict_class"]
                                         == t["predicted_class"])
            row["exit_as_predicted"] = res["rc"] == t["predicted_exit"]
            row["readings_agree"] = (row["class_as_predicted"]
                                     == row["exit_as_predicted"])
            rows.append(row)
            step(f"H4 {t['id']}: class {p['verdict_class']!r} (predicted "
                 f"{t['predicted_class']!r}), exit {res['rc']} (predicted "
                 f"{t['predicted_exit']}); sites {p['sites']} hits "
                 f"{p['hits']} not-captured {p['not_captured']}")
    measured = [r for r in rows if "dropped" not in r]
    return {
        "triples": rows,
        "measured": len(measured),
        "as_predicted": sum(1 for r in measured
                            if r["class_as_predicted"] and r["exit_as_predicted"]),
        "class_disagreements": [r["id"] for r in measured
                                if not r["readings_agree"]],
        "killed": [r["id"] for r in measured if r["timed_out"]],
    }


# --------------------------------------------------------------------- H5


def flow_sightings(cfg) -> list[dict]:
    """§1.3's S1 and S2, with the temp-directory prefix substituted once."""
    root = cfg["temp_root"]
    return [
        {"id": "S1", "literal": f"{root}/bloomery-pager-contract",
         "binding": "dir", "line": 251},
        {"id": "S2", "literal": f"{root}/bloomery-pager-contract2/j.jsonl",
         "binding": "jpath2", "line": 264},
    ]


def phase_h5(paths, cfg, records) -> dict:
    """H5: does `flow --value` see it? Both sightings, on F1.

    First reading (the gate): sightings restricted to focus value A's LINE
    deltas. Second reading (reported, not gated): every sighting of the
    literal anywhere in the trace -- the unfocused `common::pager` helpers
    are still instrumented at the call tier and their RETURN values carry
    the same texts.
    """
    mark_load("H5")
    f1 = records["runs"]["F1"]
    rows = []
    if not has_trace(paths, f1) or f1["timed_out"]:
        return {"dropped": f"F1 left no usable trace (exit {f1['rc']}, "
                           f"killed {f1['timed_out']})", "sightings": []}
    with logs_at(LOGS / "h5"):
        for s in flow_sightings(cfg):
            # `--limit 1000`. §1.3 spells the command without one and
            # `flow`'s default is 50: every H5 number is read off the
            # PRINTED rows, so the gate over a default page would be a
            # smaller number about a smaller question. The deviation is
            # stated here and in the cell's lens rather than left implicit.
            args = ["flow", f1["run"], "--value", s["literal"],
                    "--limit", str(cfg["flow_limit"])]
            res = _read(paths, args, f"h5-{s['id'].lower()}", cfg)
            p = parse_flow("\n".join((res["out"], res["err"])))
            gated = line_deltas_of(p["rows"], FOCUS_A)
            at_line = [r for r in gated if r["line"] == s["line"]]
            rows.append({
                **s, "run_id": f1["run"], "command": res["command"],
                "rc": res["rc"], "timed_out": res["timed_out"],
                "log": res["log"], "wall_s": round(res["wall"], 3),
                "stdout": "\n".join((res["out"], res["err"])),
                "sighting_events": p["sighting_events"],
                "sighting_captures": p["sighting_captures"],
                "scope_captures": p["scope_captures"],
                "scope_events": p["scope_events"],
                "sightings_line": p["sightings_line"],
                "scope_line": p["scope_line"],
                "page_truncated": p["page_truncated"],
                "rows_printed": p["rows_printed"],
                "showing": p["showing"],
                "flow_limit": cfg["flow_limit"],
                # The GATE: A's LINE deltas only.
                "gated_rows": [r["text"] for r in gated],
                "gated_count": len(gated),
                "found_at_predicted_line": bool(at_line),
                "unpredicted_gated_rows": [r["text"] for r in gated
                                           if r["line"] != s["line"]],
                # REPORTED beside it: every printed sighting row.
                "whole_trace_rows": [r["text"] for r in p["rows"]],
                "whole_trace_count": len(p["rows"]),
            })
            step(f"H5 {s['id']}: {p['sighting_events']} sighting event(s); "
                 f"gated to A's LINE deltas {len(gated)}; at line "
                 f"{s['line']} {bool(at_line)}")
    return {
        "sightings": rows,
        "page_truncated": [r["id"] for r in rows if r["page_truncated"]],
        "both_found": all(r["found_at_predicted_line"] for r in rows),
        "unpredicted": sum(len(r["unpredicted_gated_rows"]) for r in rows),
        "killed": [r["id"] for r in rows if r["timed_out"]],
    }


# --------------------------------------------------------------------- H6


def phase_h6(records) -> dict:
    """H6: what does it cost? Reported, not gated, under both readings.

    Reading one is libtest's own reported time, parsed out of the summary
    line; reading two is the wall of the whole `cargo sensorium` invocation,
    which includes the focused rebuild. Both are already recorded by
    `record`; this collects them into the pairs §1 compares.
    """
    mark_load("H6")
    runs = records["runs"]
    pairs = {}
    for focused, unfocused in PAIRS:
        f, u = runs[focused], runs[unfocused]
        pairs[f"{focused}/{unfocused}"] = {
            "focused_libtest_s": f["libtest_secs"],
            "unfocused_libtest_s": u["libtest_secs"],
            "focused_invocation_s": f["wall_s"],
            "unfocused_invocation_s": u["wall_s"],
            "libtest_delta_s": (None if f["libtest_secs"] is None
                                or u["libtest_secs"] is None
                                else round(f["libtest_secs"]
                                           - u["libtest_secs"], 3)),
            "invocation_delta_s": (None if f["wall_s"] is None
                                   or u["wall_s"] is None
                                   else round(f["wall_s"] - u["wall_s"], 3)),
        }
    return {
        "pairs": pairs,
        "walls_s": {n: r["wall_s"] for n, r in runs.items()},
        "libtest_s": {n: r["libtest_secs"] for n, r in runs.items()},
        "trace_bytes": {n: r["trace_bytes"] for n, r in runs.items()},
    }


# --------------------------------------------------------------------- H7


def phase_h7(paths, cfg) -> dict:
    """H7: did nothing else move? THIS repository, not the clone.

    Three commands, each with its own generous ceiling and its own log:
    the corpus collector over EVERY case (`corpus/run_corpus.py --json`,
    which is the committed collector -- `acceptance_phases_rung3.phase_e6`
    selects only the cases with an `exceptions` question and would silently
    skip the six new focus cases §1 names), the whole Python suite, and
    `cargo test --workspace` under the workspace target.

    The corpus runs under a FRESH target of its own (§1.4) and under
    `SENSORIUM_CARGO_SENSORIUM`, the one variable `run_corpus` reads to find
    a driver; the Python suite runs under `plain_env()` plus that same
    variable, so the module that is skipped without a built driver RUNS and
    no store of this run can answer a test's question. H7 runs LAST because
    `cargo test --workspace` shares the driver's target and could relink it.
    """
    mark_load("H7")
    driver = str(paths["sensorium_driver"])
    py = str(REPO / ".venv" / "bin" / "python")
    with logs_at(LOGS / "h7"):
        step("H7(corpus): the collector over every case")
        corpus_env = plain_env() | {
            "PYTHONDONTWRITEBYTECODE": "1",
            "SENSORIUM_CARGO_SENSORIUM": driver,
            "CARGO_TARGET_DIR": str(cfg["corpus_target"])}
        corpus = guarded([py, "corpus/run_corpus.py", "--json"], REPO,
                         "h7-corpus.log", corpus_env, cfg["corpus_timeout"],
                         "h7-corpus")
        step("H7(python): the whole suite")
        py_env = plain_env() | {"PYTHONDONTWRITEBYTECODE": "1",
                                "SENSORIUM_CARGO_SENSORIUM": driver}
        suite = guarded([py, "-m", "pytest", "-q"], REPO, "h7-pytest.log",
                        py_env, cfg["pytest_timeout"], "h7-pytest")
        step("H7(rust): cargo test --workspace")
        cargo_env = plain_env() | {
            "PYTHONDONTWRITEBYTECODE": "1",
            "CARGO_TARGET_DIR": str(paths["sensorium_rust_target"])}
        cargo = guarded(["cargo", "test", "--workspace"], REPO / "rust",
                        "h7-cargo.log", cargo_env, cfg["cargo_test_timeout"],
                        "h7-cargo")
    import json as _json
    parsed = None
    try:
        parsed = _json.loads(corpus["out"])
    except (ValueError, TypeError):
        parsed = None
    tail = [ln for ln in "\n".join(
            (suite["out"], suite["err"])).splitlines()
            if ln.strip()]
    summary = next((ln for ln in reversed(tail)
                    if " passed" in ln or " failed" in ln or " error" in ln),
                   None)
    results = [ln for ln in "\n".join(
            (cargo["out"], cargo["err"])).splitlines()
               if ln.startswith("test result:")]
    out = {
        "corpus": {"rc": corpus["rc"], "wall_s": round(corpus["wall"], 3),
                   "log": corpus["log"], "timed_out": corpus["timed_out"],
                   "command": corpus["command"],
                   "target": str(cfg["corpus_target"]),
                   "json": parsed,
                   "cases": (parsed or {}).get("cases"),
                   "questions": (parsed or {}).get("questions"),
                   "failures": (parsed or {}).get("failures"),
                   "errors": (parsed or {}).get("errors"),
                   "skipped": (parsed or {}).get("skipped")},
        "python": {"rc": suite["rc"], "wall_s": round(suite["wall"], 3),
                   "summary": summary, "log": suite["log"],
                   "timed_out": suite["timed_out"],
                   "command": suite["command"]},
        "cargo": {"rc": cargo["rc"], "wall_s": round(cargo["wall"], 3),
                  "result_lines": results, "log": cargo["log"],
                  "timed_out": cargo["timed_out"],
                  "command": cargo["command"],
                  "target": str(paths["sensorium_rust_target"])},
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
    }
    step(f"H7: corpus rc {corpus['rc']} ({out['corpus']['cases']} cases, "
         f"{len(out['corpus']['failures'] or [])} failures); pytest rc "
         f"{suite['rc']}; cargo rc {cargo['rc']}")
    return out


__all__ = ["COMPILE_FAILURE", "COMPLETED", "KILLED", "REFUSAL",
           "TEST_FAILURE", "_outcome_class",
           "FOCUS_A", "FOCUS_B", "RUNS", "PAIRS", "argv_of", "record_env",
           "guarded", "has_trace", "pick_run", "record", "phase_records",
           "phase_h1",
           "phase_h2", "phase_h3", "phase_h4", "phase_h5", "phase_h6",
           "phase_h7", "watch_triples", "flow_sightings", "temp_root"]
