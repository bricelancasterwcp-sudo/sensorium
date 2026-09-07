#!/usr/bin/env python3
"""The E4 phases, part one: §1's two passes over the 61 tests, and H1-H3.

`acceptance_e4.py` holds the lock, the locations, the preflight and `main`;
this module holds the two protocols and the three endpoints derived directly
from them. H4-H7 are in `acceptance_e4_phases2.py` -- the same seam
`acceptance_e9_cells.py` was split from its schema on: no file in this
repository may pass 800 lines, and the pass protocols and the endpoints they
feed are the natural cut.

Each phase returns RAW FACTS and decides no verdict: `acceptance_e4_schema.
assemble_e4` turns them into the none-versus-zero `results.json`, and §4 and
§5 of the acceptance document are written by hand.

Nothing here is a prediction. §1's numbers -- the 61 names, the
expected-MATCH list of all 61, the three `watch` triples -- enter as
COMPARISON TARGETS under their own names, never as a value a cell falls back
to: a phase that did not run publishes `null` with a reason, and the schema
is tested for exactly that.

THE 2-HOUR BOUND, AND WHY IT IS A FACT PER TEST
------------------------------------------------
§1.4 bounds the whole loop at 2 hours and each invocation at 1800 s. A loop
that ran past its bound would publish 61 numbers of which some were measured
on a machine already over budget; a loop that raised at the bound would lose
every number already read. So the deadline is checked BEFORE each
invocation, and a test the loop did not reach is recorded as
`not_run: the 2-hour loop bound` -- a not-measured with its reason, which is
what the schema then nulls.
"""

from __future__ import annotations

import time
from pathlib import Path

import acceptance_lib as lib
from acceptance_e4_read import (DRIVER_EXIT, HAZARD_TESTS,          # noqa: F401
                                RERUN_BANNER, cargo_finished_seconds,
                                discriminate, licence_counts,
                                pair_candidates, parse_refocus,
                                parse_watch, test_results)
from acceptance_e6ppp import logs_at, mark_load
from acceptance_e9_phases import guarded                            # noqa: F401
from acceptance_e9_read import outcome_counts
from acceptance_lib import REPO, plain_env, run_lines, step

#: The run's log ROOT. `None` here for the reason `acceptance_e9_phases.LOGS`
#: is `None`: this module owns no location, `acceptance_e4` assigns it beside
#: the other pointers, and a phase reached without that assignment fails
#: loudly on `None / "pass1"` instead of writing two hours of evidence
#: somewhere plausible and wrong.
LOGS: Path | None = None

#: §1's exit-status vocabulary for `refocus`, as `src/sensorium/exit.py`
#: fixes it. Read BESIDE the printed verdict word and never derived from it:
#: §1's H3 makes a disagreement between the two a finding.
VERDICT_EXIT = {"MATCH": 0, "DIVERGED": 1, "REFUSED": 3}
PRE_RERUN_REFUSAL_EXIT = 2

NOT_RUN_BOUND = "the 2-hour loop bound was reached before this invocation"

#: What H2's build-failure class does NOT tell apart, stated where the class
#: is published rather than left for a reader to assume.
_BUILD_CAVEAT = (
    "no libtest summary and a non-zero exit -- a focused COMPILE failure "
    "(the pattern the transform could not build, which is §1's finding) OR "
    "a driver/converter failure on the way to one, which is not; the "
    "discriminator is the pass-2 log (driver_exit = {exit}, log = {log})")


# ------------------------------------------------------------------ argv


def pass1_argv(paths, target: str, name: str) -> list[str]:
    """§1's pass-1 argv, verbatim.

        cargo sensorium test -p bloomery-daemon --test <file> -- <name> --exact

    spelled as the built binary invoked the way cargo invokes it (`<driver>
    sensorium …`, E9 §2's practice). The bare `--` separates the driver's own
    flags from cargo's, and `<name> --exact` is libtest's, so exactly one
    test runs. No `--focus` and no `--tier`: §1.4 leaves the coarse tier at
    its default `call`, so an original and its refocused pair differ only by
    the added focus.
    """
    return [str(paths["sensorium_driver"]), "sensorium", "test",
            "-p", "bloomery-daemon", "--test", target,
            "--", name, "--exact"]


def pass2_argv(name: str, run_id: str) -> list[str]:
    """§1's pass-2 argv: `sensorium refocus <run> --focus <name>`.

    Through this repository's own `.venv` Python (§1.4's lens), which is what
    `acceptance_lib.sensorium_cli` runs; spelled here rather than reused
    because the environment differs -- see `refocus_env`.
    """
    return [str(REPO / ".venv" / "bin" / "python"), "-m", "sensorium",
            "refocus", run_id, "--focus", name]


def record_env(paths) -> dict:
    """The environment every pass-1 recording runs under.

    `plain_env()` strips every `SENSORIUM_*` and `CARGO_TARGET_DIR` from the
    launcher's environment; what a recording needs is put back here and
    NOTHING else. In particular `SENSORIUM_TIER` is not set (§1.4 leaves the
    coarse tier at `call`) and `SENSORIUM_NO_INVOCATION_LOG` is not set (§1.4
    does not silence the audit log), so both facts are properties of this
    function rather than of whoever launched the run.
    """
    return plain_env() | {
        "CARGO_TARGET_DIR": str(paths["sensorium_e4_target"]),
        "SENSORIUM_DIR": str(paths["sensorium_dir"]),
    }


def refocus_env(paths) -> dict:
    """The environment every pass-2 `sensorium refocus` runs under.

    Three variables on top of `plain_env()`, each load-bearing:

    * `SENSORIUM_DIR` -- the store the original is in and the new trace must
      land in; the CLI resolves it to an absolute path before launching the
      child (`refocus_rust.run`).
    * `SENSORIUM_CARGO_SENSORIUM` -- how the CLI finds the driver
      (`refocus_rust.driver()`, the same rule `corpus/run_corpus.py`
      applies). Without it the command refuses with "no cargo-sensorium to
      re-run with", which is a pre-rerun refusal about the LAUNCH rather
      than about the subject.
    * `CARGO_TARGET_DIR` -- the child inherits this process's environment
      (`refocus_rust._launch` passes `{**os.environ, SENSORIUM_DIR}`), so
      this is what puts the re-run's rebuild in the FRESH E4 target beside
      the original's rather than in the clone's own `target/`.
    """
    return plain_env() | {
        "SENSORIUM_DIR": str(paths["sensorium_dir"]),
        "SENSORIUM_CARGO_SENSORIUM": str(paths["sensorium_driver"]),
        "CARGO_TARGET_DIR": str(paths["sensorium_e4_target"]),
    }


def _trace_db(paths, run_id: str) -> Path:
    return paths["sensorium_dir"] / "traces" / f"{run_id}.db"


def has_trace(paths, run_id) -> bool:
    """Is this run's trace actually on disk?

    A killed or failed invocation can still have printed a `run:` line for a
    process the converter never finished writing, and `sqlite3.connect(...,
    mode=ro)` on a missing file RAISES -- which would take the whole run down
    inside a phase instead of leaving a drop in the record.
    """
    return bool(run_id) and _trace_db(paths, run_id).is_file()


# ------------------------------------------------------------------ pass 1


def record_one(paths, cfg, index: int, target: str, name: str) -> dict:
    """One of §1.1's 61 originals, recorded once.

    The wall is taken around the WHOLE `cargo sensorium` invocation -- the
    FIRST is the cold build of the clone's dependency tree, which is why
    §1.4 gives every one of them 1800 s -- and libtest's own reported time is
    parsed out of the summary line beside it.

    §1 requires exactly one runner process per invocation (`--test <file>` is
    single-target, which is what §2.3's `invocation_processes` refusal
    needs). More than one `run:` line is recorded as a `multi_process` FACT
    rather than resolved by picking one: which trace pass 2 then refocused
    would be a guess, and §2.3 refuses that case for the same reason.
    """
    cmd = pass1_argv(paths, target, name)
    res = guarded(cmd, paths["sensorium_bloomery"],
                  f"p1-{index:02d}-{name}.log", record_env(paths),
                  cfg["cargo_timeout"], f"P1/{index}")
    both = "\n".join((res["out"], res["err"]))
    lines = run_lines(res)
    summaries = test_results(both)
    out = {
        "index": index, "target": target, "name": name,
        "command": res["command"], "cwd": str(paths["sensorium_bloomery"]),
        "rc": res["rc"], "wall_s": round(res["wall"], 3),
        "timed_out": res["timed_out"], "kill_s": res["kill_s"],
        "log": res["log"],
        "cargo_exit": lib.cargo_exit_of(res),
        "run_lines": lines,
        "processes": len(lines),
        # §2.3's precondition, measured rather than assumed.
        "multi_process": len(lines) != 1,
        "run": lines[0]["run"] if len(lines) == 1 else None,
        "run_candidates": [ln["run"] for ln in lines] if len(lines) != 1
        else None,
        "test_results": summaries,
        "summary_lines": [s["line"] for s in summaries],
        "outcome": outcome_counts(summaries),
        # `None`, never 0.0, when no summary carried a `finished in`: a zero
        # would read in §3 as "the test took no time at all".
        "libtest_secs": (sum(s["libtest_secs"] for s in summaries)
                         if summaries and all(s["libtest_secs"] is not None
                                              for s in summaries) else None),
        "cargo_finished_s": cargo_finished_seconds(both),
        "trace_bytes": None, "meta": None,
    }
    if has_trace(paths, out["run"]):
        out["trace_bytes"] = lib.trace_bytes(paths, out["run"])
        meta = lib.trace_meta(paths, out["run"])
        out["meta"] = {k: meta.get(k) for k in
                       ("recorder", "driver_version", "lang", "capabilities",
                        "focus", "invocation", "invocation_processes",
                        "workspace_root", "exit_status", "start_ts",
                        "fingerprint_basis", "counts", "truncated_count")}
    step(f"P1 {index}/{len(cfg['tests'])} {name}: rc={out['rc']} "
         f"run={out['run']} outcome={out['outcome']} wall={out['wall_s']}s")
    return out


def pass_one(paths, cfg) -> dict:
    """§1.1's 61 originals, in §1.1's order.

    The deadline is checked before each invocation, never during one: a
    test the loop did not reach is `not_run` with the bound as its reason,
    which the schema publishes as a not-measured rather than as a pass.
    """
    mark_load("pass1")
    # ONE deadline for the WHOLE loop, opened here and carried into pass 2.
    # §1.4 bounds "the whole loop" at 2 hours, not each pass at 2 hours: a
    # per-pass deadline would let the two passes together run for four.
    started = time.monotonic()
    deadline = started + cfg["loop_budget_s"]
    rows, exhausted = [], []
    with logs_at(LOGS / "pass1"):
        for index, (target, _line, name) in enumerate(cfg["tests"], start=1):
            if time.monotonic() >= deadline:
                exhausted.append(f"P1/{name}")
                rows.append({"index": index, "target": target, "name": name,
                             "not_run": NOT_RUN_BOUND})
                continue
            rows.append(record_one(paths, cfg, index, target, name))
    measured = [r for r in rows if "not_run" not in r]
    first = next((r for r in measured if r.get("meta")), None)
    versions = None
    if first:
        # §1.4: every version token this record checks is read from the
        # TRACE's own meta, never hard-coded. Recorded once, from the first
        # trace that carried one, with the run it came from named.
        versions = {"from_run": first["run"],
                    "recorder": (first["meta"] or {}).get("recorder"),
                    "driver_version": (first["meta"] or {}).get(
                        "driver_version"),
                    "fingerprint_basis": (first["meta"] or {}).get(
                        "fingerprint_basis")}
    out = {
        "runs": rows,
        "by_name": {r["name"]: r for r in rows},
        "n": len(rows),
        "measured": len(measured),
        "budget_exhausted": exhausted,
        "killed": [r["name"] for r in measured if r.get("timed_out")],
        "non_zero_exit": [r["name"] for r in measured if r.get("rc") != 0],
        "multi_process": [r["name"] for r in measured
                          if r.get("multi_process")],
        "no_trace": [r["name"] for r in measured
                     if not has_trace(paths, r.get("run"))],
        "versions": versions,
        "walls_s": {r["name"]: r.get("wall_s") for r in rows},
        # Monotonic, and meaningless on their own -- they exist so pass 2
        # can share this loop's one deadline rather than opening a second.
        "loop_started_monotonic": started,
        "loop_deadline_monotonic": deadline,
        "loop_budget_s": cfg["loop_budget_s"],
    }
    step(f"pass 1: {out['measured']}/{out['n']} recorded; killed "
         f"{out['killed']}; non-zero {out['non_zero_exit']}; multi-process "
         f"{out['multi_process']}; no trace {out['no_trace']}")
    return out


# ------------------------------------------------------------------ pass 2


def refocus_one(paths, cfg, rec: dict) -> dict:
    """One `sensorium refocus <run> --focus <name>`, and what came back.

    stderr is captured to this item's own log: `refocus_rust._launch` does
    not capture the driver child's stderr, so cargo's build output arrives
    on THIS process's stderr. §2.3's "streams through" is a promise to the
    person waiting at a terminal; a runner is not a terminal, and the
    evidence has to land in a file either way.

    The pair is found in the STORE, by `refocus_of` plus the launch
    timestamp (§1.4's pair rule), and the id the CLI printed is recorded
    beside it as a CROSS-CHECK -- never as the source. Zero or more than one
    qualifying trace is a REFUSED by count.
    """
    name, run_id = rec["name"], rec.get("run")
    index = rec["index"]
    if not run_id:
        return {"index": index, "name": name, "target": rec["target"],
                "original": None,
                "not_run": ("the original left no single run id, so there is "
                            "nothing to refocus")}
    cmd = pass2_argv(name, run_id)
    launched_at = time.time()
    res = guarded(cmd, REPO, f"p2-{index:02d}-{name}.log", refocus_env(paths),
                  cfg["refocus_timeout"], f"P2/{index}")
    both = "\n".join((res["out"], res["err"]))
    parsed = parse_refocus(both)
    pair = pair_candidates(paths["sensorium_dir"] / "traces", run_id,
                           launched_at)
    summaries = test_results(both)
    m = DRIVER_EXIT.search(both)
    out = {
        "index": index, "name": name, "target": rec["target"],
        "original": run_id, "command": res["command"], "cwd": str(REPO),
        "rc": res["rc"], "wall_s": round(res["wall"], 3),
        "timed_out": res["timed_out"], "kill_s": res["kill_s"],
        "log": res["log"],
        "launched_at": launched_at,
        # H1: the child was launched iff the CLI printed the banner it prints
        # immediately before `subprocess.run`.
        "child_launched": RERUN_BANNER in both,
        "driver_exit": int(m.group("rc")) if m else None,
        # H2: a re-run COMPLETED iff libtest printed a summary line.
        "test_results": summaries,
        "summary_lines": [s["line"] for s in summaries],
        "outcome": outcome_counts(summaries),
        "libtest_secs": (sum(s["libtest_secs"] for s in summaries)
                         if summaries and all(s["libtest_secs"] is not None
                                              for s in summaries) else None),
        "cargo_finished_s": cargo_finished_seconds(both),
        "pair": pair,
        "new_run": pair["qualifying"][0] if pair["n"] == 1 else None,
        "pair_refusal": (None if pair["n"] == 1 else
                         (f"the store holds {pair['n']} trace(s) whose "
                          f"`refocus_of` is {run_id} and whose recording "
                          f"started after the launch ({pair['qualifying']}); "
                          f"§1.4's pair rule needs exactly one")),
        "printed_new_run": parsed["new_run"],
        "pair_agrees_with_the_printed_id": (
            pair["n"] == 1 and parsed["new_run"] == pair["qualifying"][0]),
        "stdout": res["out"], "stderr": res["err"],
        # The parse, whole -- MINUS the two keys this record spells
        # differently. `new_run` is the STORE's answer (§1.4's pair rule),
        # never the printed one, which is carried beside it as a
        # cross-check; and `licence` here is the COUNTS, of which the
        # printed word is one field. Letting the spread win either would
        # silently replace a measured fact with a printed one.
        **{k: v for k, v in parsed.items()
           if k not in ("new_run", "licence")},
        "parsed_new_run": parsed["new_run"],
        "licence": licence_counts(parsed),
    }
    out["verdict_exit_expected"] = VERDICT_EXIT.get(out["verdict_word"])
    out["verdict_and_exit_agree"] = (
        None if out["verdict_word"] is None or out["rc"] is None
        else out["rc"] == VERDICT_EXIT[out["verdict_word"]])
    if has_trace(paths, out["new_run"]):
        out["new_trace_bytes"] = lib.trace_bytes(paths, out["new_run"])
        meta = lib.trace_meta(paths, out["new_run"])
        out["new_meta"] = {k: meta.get(k) for k in
                           ("recorder", "driver_version", "capabilities",
                            "focus", "refocus_of", "refocus_verdict",
                            "refocus_licence", "refocus_licence_reasons",
                            "refocus_licence_unverifiable", "counts",
                            "exit_status")}
    else:
        out["new_trace_bytes"], out["new_meta"] = None, None
    step(f"P2 {index}/{len(cfg['tests'])} {name}: exit={out['rc']} "
         f"verdict={out['verdict_word']} licence={parsed['licence']} "
         f"pair={pair['n']} wall={out['wall_s']}s")
    return out


def pass_two(paths, cfg, one: dict) -> dict:
    """Pass 2 over every original of pass 1, in §1.1's order."""
    mark_load("pass2")
    # Pass 1's deadline, not a fresh one: the bound is on the LOOP. A pass 2
    # that opened its own would double §1.4's 2 hours in silence. A record
    # without one (a hand-built `one`) falls back to a fresh budget, and
    # says so by carrying the value it used.
    deadline = one.get("loop_deadline_monotonic")
    if deadline is None:
        deadline = time.monotonic() + cfg["loop_budget_s"]
    rows, exhausted = [], []
    with logs_at(LOGS / "pass2"):
        for rec in one["runs"]:
            if "not_run" in rec:
                rows.append({"index": rec["index"], "name": rec["name"],
                             "target": rec["target"], "original": None,
                             "not_run": ("pass 1 did not run this test: "
                                         + rec["not_run"])})
                continue
            if time.monotonic() >= deadline:
                exhausted.append(f"P2/{rec['name']}")
                rows.append({"index": rec["index"], "name": rec["name"],
                             "target": rec["target"],
                             "original": rec.get("run"),
                             "not_run": NOT_RUN_BOUND})
                continue
            rows.append(refocus_one(paths, cfg, rec))
    measured = [r for r in rows if "not_run" not in r]
    out = {
        "refocuses": rows,
        "by_name": {r["name"]: r for r in rows},
        "n": len(rows), "measured": len(measured),
        "budget_exhausted": exhausted,
        "killed": [r["name"] for r in measured if r.get("timed_out")],
        "pair_refusals": [r["name"] for r in measured
                          if r.get("pair_refusal")],
        "walls_s": {r["name"]: r.get("wall_s") for r in rows},
        "loop_deadline_monotonic": deadline,
        "loop_deadline_inherited_from_pass1": (
            one.get("loop_deadline_monotonic") is not None),
    }
    step(f"pass 2: {out['measured']}/{out['n']} refocused; killed "
         f"{out['killed']}; pair refusals {out['pair_refusals']}")
    return out


def _measured(two: dict) -> list[dict]:
    return [r for r in two["refocuses"] if "not_run" not in r]


# --------------------------------------------------------------------- H1


def phase_h1(two: dict) -> dict:
    """H1: does every original refocus without a PRE-RERUN refusal?

    First reading (the gate): pre-rerun refusals, expected 0. One is an
    exit 2 carrying a design §2.3 sentence -- `error: cannot refocus <run>:
    …; nothing was re-run` -- and each is recorded with its verbatim
    sentence and its run.

    Second reading, on the count that can move independently: invocations
    that REACHED the driver, read from the banner the CLI prints immediately
    before it launches the child. A pre-rerun refusal short-circuits before
    that banner, so the two readings are separate observations of one answer
    rather than one derived from the other.
    """
    mark_load("H1")
    rows = _measured(two)
    refusals = [{"name": r["name"], "run": r["original"], "exit": r["rc"],
                 "sentence": r["pre_rerun_refusal"]}
                for r in rows if r.get("pre_rerun_refusal")]
    # An exit 2 with NO §2.3 sentence is neither reading's number and is
    # named on its own: it is the CLI refusing the CALL (a bad flag, an
    # unreadable trace), not the design's pre-rerun gate.
    unexplained = [r["name"] for r in rows
                   if r.get("rc") == PRE_RERUN_REFUSAL_EXIT
                   and not r.get("pre_rerun_refusal")]
    launched = [r["name"] for r in rows if r.get("child_launched")]
    out = {
        "n": len(rows),
        "pre_rerun_refusals": refusals,
        "pre_rerun_refusal_count": len(refusals),
        "exit_2_without_a_sentence": unexplained,
        "reached_the_driver": len(launched),
        "did_not_reach_the_driver": [r["name"] for r in rows
                                     if not r.get("child_launched")],
        "killed": two["killed"],
    }
    step(f"H1: {out['pre_rerun_refusal_count']} pre-rerun refusal(s) of "
         f"{out['n']}; {out['reached_the_driver']} reached the driver")
    return out


# --------------------------------------------------------------------- H2


def phase_h2(one: dict, two: dict) -> dict:
    """H2: does every re-run COMPLETE?

    First reading (the gate, and §1's kill 1): a focused BUILD FAILURE is a
    re-run whose child was launched and whose output carries NO libtest
    `test result:` line -- the unit never ran. It is a STOP: no fallback to
    an unfocused build, no retry under a narrower focus, no skipped test.

    The class is what §1 names; what the class cannot tell apart is stated
    beside it rather than left for a reader to assume. "No libtest summary
    and a non-zero exit" is a focused COMPILE failure -- the pattern the
    transform could not build, which is the finding §1 means -- OR a driver
    or converter failure on the way to one, which is not. The discriminator
    between those two is the pass-2 log, and `build_failure_caveat` says so
    with the child's own exit beside it.

    Second reading: each re-run's libtest summary counts against the
    original's. `None`, not `False`, when either side printed no summary at
    all -- "these two are not equal" is a claim about two outcomes, and an
    unparsed one is not an outcome.
    """
    mark_load("H2")
    rows = _measured(two)
    originals = one["by_name"]
    per_test, failures, unequal = [], [], []
    for r in rows:
        orig = originals.get(r["name"]) or {}
        completed = bool(r.get("summary_lines"))
        launched = bool(r.get("child_launched"))
        build_failure = launched and not completed and not r.get("timed_out")
        equal = (None if orig.get("outcome") is None or r.get("outcome") is None
                 else orig["outcome"] == r["outcome"])
        per_test.append({
            "name": r["name"], "target": r["target"],
            "child_launched": launched, "completed": completed,
            "build_failure": build_failure,
            "driver_exit": r.get("driver_exit"),
            "refocus_exit": r.get("rc"),
            "timed_out": r.get("timed_out"),
            "original_outcome": orig.get("outcome"),
            "rerun_outcome": r.get("outcome"),
            "outcome_equal": equal,
            "original_summary_lines": orig.get("summary_lines"),
            "rerun_summary_lines": r.get("summary_lines"),
            "log": r.get("log"),
        })
        if build_failure:
            failures.append(r["name"])
            per_test[-1]["build_failure_caveat"] = _BUILD_CAVEAT.format(
                exit=r.get("driver_exit"), log=r.get("log"))
        if equal is False:
            unequal.append(r["name"])
    out = {
        "n": len(rows),
        "per_test": per_test,
        "completed": sum(1 for p in per_test if p["completed"]),
        "build_failures": failures,
        "build_failure_caveat": (
            _BUILD_CAVEAT.format(
                exit={p["name"]: p.get("driver_exit") for p in per_test
                      if p["build_failure"]},
                log={p["name"]: p.get("log") for p in per_test
                     if p["build_failure"]})
            if failures else None),
        "outcomes_equal": sum(1 for p in per_test if p["outcome_equal"]),
        "outcomes_unequal": unequal,
        "outcomes_unreadable": [p["name"] for p in per_test
                                if p["outcome_equal"] is None],
        "killed": two["killed"],
    }
    if failures:
        step(f"STOP (§1 kill 1): focused build failure(s) on {failures}; no "
             "fallback and no retry was made")
    step(f"H2: {out['completed']}/{out['n']} re-runs completed; outcomes "
         f"equal {out['outcomes_equal']}; unequal {unequal}")
    return out


# --------------------------------------------------------------------- H3


def _classify(paths, r: dict) -> dict:
    """One DIVERGED, classified under §1.4's amendment (2).

    The discriminator is applied ONLY to the three tests §1.2 pre-registers
    as the scheduler hazard; every other DIVERGED is the finding H3 means,
    with no prior explanation available to it. A pair whose two traces are
    not both on disk cannot be discriminated at all, and says so rather than
    defaulting to either class.
    """
    name = r["name"]
    if name not in HAZARD_TESTS:
        return {"class": "finding",
                "reading": ("§1.2 pre-registers no explanation for a "
                            "DIVERGED on this test, so it is the finding H3 "
                            "means"),
                "is_a_pre_registered_hazard_test": False}
    orig_db, new_db = (_trace_db(paths, r.get("original")),
                       _trace_db(paths, r.get("new_run")))
    if not (orig_db.is_file() and new_db.is_file()):
        return {"class": None,
                "reading": ("the discriminator needs BOTH traces' "
                            "fingerprint tables and one is not on disk"),
                "is_a_pre_registered_hazard_test": True,
                "dropped": f"missing trace: {orig_db.name} / {new_db.name}"}
    return discriminate(orig_db, new_db, name)


def phase_h3(paths, cfg, one: dict, two: dict) -> dict:
    """H3: MATCH on the expected list?

    The gate is §1.2's expected-MATCH list, which is ALL 61. Each verdict is
    read twice and the two are never derived from each other: the WORD
    `refocus` printed, and the EXIT it returned (MATCH 0 / DIVERGED 1 /
    REFUSED 3). A disagreement between them is itself a finding and is
    reported as one.

    A DIVERGED on one of §1.2's three server tests goes through §1.4's
    discriminator; every other DIVERGED is the finding. A REFUSED AFTER the
    rerun is §1's kill 2, a STOP.
    """
    mark_load("H3")
    rows = _measured(two)
    per_test, diverged, refused, disagreements = [], [], [], []
    for r in rows:
        word = r.get("verdict_word")
        row = {"name": r["name"], "target": r["target"],
               "original": r.get("original"), "new_run": r.get("new_run"),
               "verdict_word": word, "exit": r.get("rc"),
               "expected_exit_for_the_word": r.get("verdict_exit_expected"),
               "readings_agree": r.get("verdict_and_exit_agree"),
               "verdict_line": r.get("verdict_line"),
               "diff_verdict_line": r.get("diff_verdict_line"),
               "threads_line": r.get("threads_line"),
               "tasks_line": r.get("tasks_line"),
               "pair_refusal": r.get("pair_refusal"),
               "stamped_verdict": (r.get("new_meta") or {}).get(
                   "refocus_verdict"),
               "classification": None,
               "diverged_step": r.get("diverged_step"),
               "step_rows": r.get("step_rows"),
               "refused_after_rerun": r.get("refused_after_rerun")}
        if word == "DIVERGED":
            row["classification"] = _classify(paths, r)
            diverged.append(r["name"])
        if word == "REFUSED" or r.get("refused_after_rerun"):
            refused.append(r["name"])
        if row["readings_agree"] is False:
            disagreements.append(r["name"])
        per_test.append(row)
    hazard = [p["name"] for p in per_test
              if (p["classification"] or {}).get("class") == "hazard"]
    findings = [p["name"] for p in per_test
                if (p["classification"] or {}).get("class") == "finding"]
    unclassified = [p["name"] for p in per_test
                    if p["classification"] is not None
                    and (p["classification"] or {}).get("class") is None]
    out = {
        "n": len(rows),
        "gate_n": cfg["gate_n"],
        "per_test": per_test,
        "match": sum(1 for p in per_test if p["verdict_word"] == "MATCH"),
        "diverged": diverged,
        "diverged_named_hazard": hazard,
        "diverged_findings": findings,
        "diverged_unclassified": unclassified,
        "refused_after_rerun": refused,
        "verdict_words": {p["name"]: p["verdict_word"] for p in per_test},
        "exits": {p["name"]: p["exit"] for p in per_test},
        "readings_disagree": disagreements,
        "no_verdict_word": [p["name"] for p in per_test
                            if p["verdict_word"] is None],
        "killed": two["killed"],
    }
    if refused:
        step(f"STOP (§1 kill 2): REFUSED after the rerun on {refused}")
    step(f"H3: {out['match']}/{out['n']} MATCH (gate {cfg['gate_n']}); "
         f"diverged {diverged} (hazard {hazard}, findings {findings}); "
         f"word/exit disagreements {disagreements}")
    return out


__all__ = ["LOGS", "NOT_RUN_BOUND", "PRE_RERUN_REFUSAL_EXIT", "VERDICT_EXIT",
           "HAZARD_TESTS", "guarded", "has_trace", "pass1_argv", "pass2_argv",
           "pass_one", "pass_two", "phase_h1", "phase_h2", "phase_h3",
           "record_env", "record_one", "refocus_env", "refocus_one",
           "_trace_db", "_measured", "_classify"]
