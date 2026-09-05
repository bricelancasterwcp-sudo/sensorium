#!/usr/bin/env python3
"""The rung-4 entry phases: H2, H3, H4/H5, H1 and H6.

A module of its own for the reason `acceptance_phases_rung3.py` is one:
`acceptance_grain.py` crossed the repository's 800-line ceiling once fix
round 1 added the guarded raw-json write and the INCOMPLETE reporting, and
the seam this splits on is the same one the rung-2 instrument uses --
`acceptance.py` holds the lock, the locations, the preflight and `main`, and
`acceptance_phases.py` holds the protocols. Nothing moved changed: these are
the same five phases, in the same order, calling the same committed
functions.

Each phase returns RAW FACTS and decides no verdict:
`acceptance_grain_schema.assemble_grain` turns them into the none-versus-zero
`results.json`, and §4 of the acceptance document is written by hand.

`acceptance_grain` re-exports every name here, so `acceptance_grain.phase_h2`
and the rest keep resolving for callers and tests.
"""

from __future__ import annotations

import subprocess
import time
from collections import Counter
from pathlib import Path

import acceptance_lib as lib
import acceptance_phases_rung3 as r3
from acceptance_e6ppp import logs_at, mark_load
from acceptance_grain_read import (ARMS, MULTI, compare_sites, measure_sites,
                                   parse_header, parse_tally, site_table,
                                   store_paths, swallowed_shapes, vary_counts)
from acceptance_lib import (REPO, plain_env, run, sensorium_cli,   # noqa: F401
                            sha256_file, step)

#: The run's log ROOT -- the directory each phase opens its own `logs_at`
#: subdirectory under. DECLARED here so the name exists in the namespace the
#: phases resolve it in, and `None` here because this module owns no
#: location: `acceptance_grain` assigns it beside `acceptance_lib.LOGS` and
#: `acceptance_phases.LOGS`, from the same `BASE / "logs"` every other
#: pointer comes from. A phase reached without that assignment fails loudly
#: on `None / "h2"` instead of writing a run's evidence somewhere plausible
#: and wrong -- which is the failure a default copied from `lib.LOGS` would
#: have hidden, since `lib.LOGS` happens to hold this run's root at the
#: moment this module is imported and would stop doing so on any import
#: reorder.
#:
#: It is NOT what `logs_at` rebinds. `logs_at` moves `lib.LOGS`/`ph.LOGS` --
#: the pointers `acceptance_lib.run` resolves at call time -- and restores
#: them; this one stays the root for the whole run, which is why every
#: `logs_at(LOGS / "<phase>")` below names a sibling directory rather than
#: nesting inside the previous phase's.
LOGS: Path | None = None

# ------------------------------------------------------------- H2, H3, H4


def _ask(paths, label: str, ref: str, cfg, tag: str, kill=None) -> dict:
    """One `exceptions <ref> --limit <big>` against one kept store.

    `kill` arms H5's ceiling. A kill is a fact of the record -- H5's STOP --
    and never an exception that takes the run down with it, so the wall and
    whatever the process had printed are captured and returned.
    """
    sp = store_paths(paths, label)
    args = ["exceptions", ref, "--limit", str(cfg["limit"])]
    timeout = kill if kill else cfg["cli_timeout"]
    t0 = time.monotonic()
    try:
        res = sensorium_cli(sp, args, tag, timeout=timeout)
        res["timed_out"] = False
    except subprocess.TimeoutExpired as e:
        # The kill's OWN evidence. `acceptance_lib.run` writes its log after
        # the call returns, so a killed command leaves none; the partial
        # output `subprocess.run` attaches to the exception is written here
        # instead, because "what it had printed when the ceiling fired" is
        # the whole of what an H5 STOP has to show for itself.
        wall = time.monotonic() - t0
        raw = e.output or ("" if isinstance(e.output, str) else b"")
        text = raw if isinstance(raw, str) else raw.decode("utf-8", "replace")
        log = lib.LOGS / f"cli-{tag}.KILLED.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"$ sensorium {' '.join(args)}\n"
                       f"--- KILLED at {timeout} s (wall {wall:.3f}) ---\n"
                       f"--- partial stdout ---\n{text}\n")
        res = {"rc": None, "out": text, "err": "", "wall": wall,
               "log": str(log), "timed_out": True}
        step(f"{tag}: KILLED at {timeout} s -- H5 STOP "
             f"({len(text)} byte(s) printed before the kill)")
    res["command"] = "sensorium " + " ".join(args)
    res["stdout_bytes"] = len(res["out"])
    res["stdout_lines"] = len(res["out"].splitlines())
    return res


def phase_h2(paths, cfg, orc) -> dict:
    """H2: the grouped view of the A run, at the site grain."""
    mark_load("H2")
    spec = ARMS["a"]
    with logs_at(LOGS / "h2"):
        res = _ask(paths, "a", spec["run"], cfg, "h2-a")
        m = measure_sites(store_paths(paths, "a"), res["out"],
                          spec["run"])
    header = parse_header(res["out"])
    cmp_ = compare_sites(m["sites"], orc["a"])
    out_ = {
        "arm": "a", "run": spec["run"], "rc": res["rc"],
        "wall": round(res["wall"], 3), "log": res["log"],
        "command": res["command"], "stdout": res["out"],
        "stdout_bytes": res["stdout_bytes"],
        "stdout_lines": res["stdout_lines"],
        "groups": m["groups"], "chains": m["chains"],
        "measured_sites": {f"{f}:{ln}": n for (f, ln), n in
                           sorted(m["sites"].items(), key=str)},
        "unresolved_sinks": m["unresolved_count"],
        "unresolved": m["unresolved"],
        "compare": {**cmp_,
                    "missing": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                 "expected": d["expected"]}
                                for d in cmp_["missing"]],
                    "extra": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                               "measured": d["measured"]}
                              for d in cmp_["extra"]],
                    "count_diffs": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                     "measured": d["measured"],
                                     "expected": d["expected"]}
                                    for d in cmp_["count_diffs"]]},
        "tally_line": header["tally_line"],
        "oracle_tally_line": (orc["per_process"]["a"] or {}).get(spec["run"]),
        "vary": vary_counts(res["out"]),
        "incomplete_banner": header["incomplete_banner"],
        "header": header,
    }
    out_["tally_line_equal"] = (out_["tally_line"]
                                == out_["oracle_tally_line"])
    step(f"H2: {out_['groups']} SWALLOWED group(s), {out_['chains']} chain(s); "
         f"site differences {cmp_['differences']}; tally equal "
         f"{out_['tally_line_equal']}")
    return out_


def phase_h3(paths, cfg, orc) -> dict:
    """H3: every process of `ws` and `ws0`, one `exceptions <run>` each.

    Compared per process against the record's own tally line and swallow
    count. A process whose record tally line is `None` printed `no exceptions
    recorded`, and the check is for THAT SHAPE, not for a zero.
    """
    mark_load("H3")
    arms: dict = {}
    for label in MULTI:
        sp = store_paths(paths, label)
        runs = sorted(p.stem for p in
                      (sp["sensorium_dir"] / "traces").glob("*.db"))
        expect = orc["per_process"][label]
        counts = orc["swallowed_count"][label]
        rows, bad_tally, bad_count = [], [], []
        with logs_at(LOGS / f"h3-{label}"):
            for run_id in runs:
                res = _ask(paths, label, run_id, cfg, f"h3-{label}-{run_id}")
                shapes = swallowed_shapes(res["out"])
                chains = sum(s["n"] for s in shapes)
                tally_line = parse_tally(res["out"])
                want = expect.get(run_id)
                header = parse_header(res["out"])
                if want is None:
                    # The record holds `None` because this process printed
                    # the empty-answer shape. An empty answer on a recording
                    # that never finalized reports where the RECORDING
                    # ended, not what the program did (`caps.none_status`),
                    # so the banner makes this a reported GAP, not a pass.
                    ok_tally = (tally_line is None
                                and "no exceptions recorded" in res["out"]
                                and not header["incomplete_banner"])
                else:
                    ok_tally = tally_line == want
                ok_count = chains == counts.get(run_id)
                row = {"run": run_id, "rc": res["rc"],
                       "wall": round(res["wall"], 3),
                       "stdout_bytes": res["stdout_bytes"],
                       "stdout_lines": res["stdout_lines"],
                       "groups": len(shapes), "chains": chains,
                       "tally_line": tally_line, "oracle_tally_line": want,
                       "oracle_swallowed_count": counts.get(run_id),
                       "tally_equal": ok_tally, "count_equal": ok_count,
                       "vary": vary_counts(res["out"]),
                       "incomplete_banner": header["incomplete_banner"],
                       "log": res["log"]}
                if run_id == cfg["busiest_ws_run"]:
                    row["stdout"] = res["out"]
                rows.append(row)
                if not ok_tally:
                    bad_tally.append(run_id)
                if not ok_count:
                    bad_count.append(run_id)
        arms[label] = {
            "processes": len(rows), "rows": rows,
            "runs_only_in_the_store": sorted(set(runs) - set(expect)),
            "runs_only_in_the_record": sorted(set(expect) - set(runs)),
            "unequal_tally_lines": bad_tally,
            "unequal_swallow_counts": bad_count,
            "incomplete_processes": [r["run"] for r in rows
                                     if r["incomplete_banner"]],
            "stdout_bytes_total": sum(r["stdout_bytes"] for r in rows),
            "stdout_lines_total": sum(r["stdout_lines"] for r in rows),
            "groups_total": sum(r["groups"] for r in rows),
            "chains_total": sum(r["chains"] for r in rows),
            "vary": dict(sum((Counter(r["vary"]) for r in rows), Counter())),
        }
        step(f"H3 {label}: {len(rows)} process(es); unequal tally lines "
             f"{len(bad_tally)}; unequal swallow counts {len(bad_count)}")
    total = sum(a["processes"] for a in arms.values())
    return {"arms": arms, "comparisons": total,
            "unequal": sum(len(a["unequal_tally_lines"])
                           + len(a["unequal_swallow_counts"])
                           for a in arms.values())}


def phase_h4(paths, cfg, orc) -> dict:
    """H4 and H5: one invocation question per multi-process arm, wall-timed
    under an armed kill."""
    mark_load("H4")
    arms: dict = {}
    for label in MULTI:
        spec = ARMS[label]
        with logs_at(LOGS / f"h4-{label}"):
            res = _ask(paths, label, spec["invocation"], cfg,
                       f"h4-{label}", kill=cfg["kill_s"])
            m = measure_sites(store_paths(paths, label),
                              res["out"], spec["run"])
        header = parse_header(res["out"])
        cmp_ = compare_sites(m["sites"], orc[label])
        arms[label] = {
            "arm": label, "invocation": spec["invocation"],
            "rc": res["rc"], "wall": round(res["wall"], 3),
            "timed_out": res["timed_out"], "kill_s": cfg["kill_s"],
            "log": res["log"], "command": res["command"],
            "stdout_bytes": res["stdout_bytes"],
            "stdout_lines": res["stdout_lines"],
            "groups": m["groups"], "chains": m["chains"],
            "unresolved_sinks": m["unresolved_count"],
            "unresolved": m["unresolved"],
            "measured_sites": site_table(m["sites"]),
            "processes_named": len(m["runs_named"]),
            "compare": {"equal": cmp_["equal"],
                        "differences": cmp_["differences"],
                        "measured_sites": cmp_["measured_sites"],
                        "expected_sites": cmp_["expected_sites"],
                        "measured_lines": cmp_["measured_lines"],
                        "expected_lines": cmp_["expected_lines"],
                        "missing": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                     "expected": d["expected"]}
                                    for d in cmp_["missing"]],
                        "extra": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                   "measured": d["measured"]}
                                  for d in cmp_["extra"]],
                        "count_diffs": [
                            {"site": f"{d['site'][0]}:{d['site'][1]}",
                             "measured": d["measured"],
                             "expected": d["expected"]}
                            for d in cmp_["count_diffs"]]},
            "header": header,
            "oracle_tally": orc["tallies"][label],
            "tally_equal": header["tally"] == orc["tallies"][label],
            "header_counts_equal": (
                header["processes"] == orc["processes"][label]
                and header["with_chains"] == orc["tally_lines"][label]
                and header["without_chains"]
                == orc["without_a_tally_line"][label]),
            "incomplete_members": header["incomplete"],
            "vary": vary_counts(res["out"]),
        }
        step(f"H4 {label}: {m['groups']} group(s) over "
             f"{arms[label]['processes_named']} named process(es) in "
             f"{arms[label]['wall']} s; site differences {cmp_['differences']}; "
             f"tally equal {arms[label]['tally_equal']}; header counts equal "
             f"{arms[label]['header_counts_equal']}")
    return {"arms": arms,
            "walls": {k: v["wall"] for k, v in arms.items()},
            "killed": [k for k, v in arms.items() if v["timed_out"]]}


# ----------------------------------------------------------------- H1 and H6


def phase_h1(paths, cfg) -> dict:
    """H1: the COMMITTED corpus collector (`acceptance_phases_rung3.phase_e6`)
    over every `corpus/rust/*` case with an `exceptions` question.

    `phase_e6` gives each case its OWN `<workdir>/.sensorium`, so the fresh
    `SENSORIUM_DIR` the preflight required stays empty -- which the cleanup
    re-checks, because a corpus recording landing in it would mean a case
    read another case's trace.
    """
    mark_load("H1")
    with logs_at(LOGS / "h1"):
        step("H1: the Rust corpus cases with an `exceptions` question, "
             "against the pins §1 names as updated BY RULE")
        return r3.phase_e6(paths, cfg)


def phase_h6(paths, cfg) -> dict:
    """H6: the whole Python suite, and the Rust workspace tests.

    Both, because §1's H6 names both. The Python suite runs under
    `plain_env()` plus `SENSORIUM_CARGO_SENSORIUM` -- the one variable the
    suite reads to decide whether it can drive a real driver -- so no store
    of this run can answer a test's question, and the module that is skipped
    without it is RUN. `cargo test --workspace` runs in `rust/` against the
    workspace target it was built in; no crate changed in this slice, so it
    compiles nothing, and the driver's sha256 is checked afterwards rather
    than assumed. H6 runs LAST, so even a relink could not reach H1.
    """
    mark_load("H6")
    env = plain_env() | {
        "PYTHONDONTWRITEBYTECODE": "1",
        "SENSORIUM_CARGO_SENSORIUM": str(paths["sensorium_driver"])}
    with logs_at(LOGS / "h6"):
        step("H6(python): the whole suite")
        py = run([str(REPO / ".venv" / "bin" / "python"), "-m", "pytest",
                  "-q"], REPO, "h6-pytest.log", env,
                 timeout=cfg["pytest_timeout"])
        step("H6(rust): cargo test --workspace")
        cargo_env = plain_env() | {
            "CARGO_TARGET_DIR": str(paths["rust_target"]),
            "PYTHONDONTWRITEBYTECODE": "1"}
        cargo = run(["cargo", "test", "--workspace"], REPO / "rust",
                    "h6-cargo.log", cargo_env, timeout=cfg["cargo_timeout"])
    tail = [ln for ln in (py["out"] + py["err"]).splitlines() if ln.strip()]
    summary = next((ln for ln in reversed(tail)
                    if " passed" in ln or " failed" in ln or " error" in ln),
                   None)
    results = [ln for ln in (cargo["out"] + cargo["err"]).splitlines()
               if ln.startswith("test result:")]
    return {
        "python": {"rc": py["rc"], "wall": round(py["wall"], 3),
                   "summary": summary, "log": py["log"],
                   "env": sorted(k for k in env if k.startswith("SENSORIUM_")
                                 or k == "PYTHONDONTWRITEBYTECODE")},
        "cargo": {"rc": cargo["rc"], "wall": round(cargo["wall"], 3),
                  "result_lines": results, "log": cargo["log"],
                  "target": str(paths["rust_target"])},
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
    }


