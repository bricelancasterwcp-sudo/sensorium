"""THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike): raw run -> `results.json`.

Split out of `measure.py` purely to keep both files under the plan's 800-line
ceiling. `assemble(raw, which)` turns the runner's `results-raw.json` into the
pre-registered schema: every measurement is
`{"value", "n", "lens", "dropped"}`, a `null` value with a non-empty `dropped`
list is the ONLY representation of not-measured, and `0` is measured-and-zero.

`which` selects E2's denominator lens (`all`, `src`, `reached`, `workspace`);
the runner defaults to `all`, the plan's file set, and `measure.py --assemble`
re-runs this alone against a saved raw file.
"""

import re

from measure import (E2_CENSUS_LENS, E2_DENOM_ALL, E2_DENOM_REACHED, E2_DENOM_SRC, LOGS,
                     e1_summary, meas)

# ------------------------------------------------ results.json (the schema)

E2_DENOMS = {"all": (E2_DENOM_ALL, "crates/*/src + crates/*/tests (the plan's file set)"),
             "src": (E2_DENOM_SRC, "crates/*/src only"),
             "reached": (E2_DENOM_REACHED,
                         "the file set `cargo test -p bloomery-daemon` reaches"),
             }


def _e1(raw):
    runs = raw["raw_e1"]["runs"]
    arms = {a: e1_summary(runs, a) for a in ("P", "O", "C")}
    lens = ("wall clock of the whole command, dev profile, "
            "`cargo test -p bloomery-daemon` (P) / `cargo sensorium test --tier off|call "
            "-p bloomery-daemon` (O, C), binaries pre-built, default --test-threads, "
            "5 interleaved rounds P,O,C, 10 s between commands; the instrumented arms "
            "include the driver's fixed overhead, reported separately")
    ratio_o = (round(arms["O"]["median"] / arms["P"]["median"], 4)
               if arms["O"]["median"] and arms["P"]["median"] else None)
    ratio_c = (round(arms["C"]["median"] / arms["P"]["median"], 4)
               if arms["C"]["median"] and arms["P"]["median"] else None)
    dropped = arms["P"]["dropped"] + arms["O"]["dropped"] + arms["C"]["dropped"]
    return {
        "headline": meas(ratio_o, min(arms["O"]["n"], arms["P"]["n"]),
                         "median(off)/median(plain); " + lens,
                         dropped if ratio_o is None else []),
        "ratio_call_over_plain": meas(ratio_c, min(arms["C"]["n"], arms["P"]["n"]),
                                      "median(call)/median(plain); " + lens,
                                      dropped if ratio_c is None else []),
        "arms": {a: {"median_s": meas(arms[a]["median"], arms[a]["n"], lens, arms[a]["dropped"]),
                     "min_s": arms[a]["min"], "max_s": arms[a]["max"],
                     "walls_s": arms[a]["walls"]} for a in arms},
        "raw_runs": runs,
        "driver_fixed_overhead_s": meas(
            raw["raw_overhead"]["overhead_s"], 3,
            "median of 3 no-op `--no-run` builds through the release driver minus the "
            "median of 3 straight to cargo, same package, everything Fresh"),
    }


def _e2(raw, which):
    r = raw["raw_e2"]
    wide = raw.get("raw_e2_workspace") or {}
    denom, denom_lens = E2_DENOMS.get(which, E2_DENOMS["all"])
    if which == "workspace":
        num = wide.get("distinct")
        denom, denom_lens = E2_DENOM_ALL, ("crates/*/src + crates/*/tests, numerator from a "
                                           "workspace-wide instrumented --no-run")
        dropped = [] if num is not None else [wide.get("dropped", "workspace build not run")]
    else:
        num = r["distinct_src"] if which == "src" else r["distinct"]
        dropped = []
    value = round(num / denom, 6) if num is not None else None
    lensed = (f"instrumented distinct (file, qualname, firstlineno) / {denom} eligible; "
              f"denominator = {denom_lens}; census: {E2_CENSUS_LENS}")
    out = {
        "headline": meas(value, num if num is not None else 0, lensed, dropped),
        "instrumented_distinct_fn_items": meas(
            r["distinct"], len(r["units"]),
            "distinct (file, qualname, firstlineno) over manifests with fell_back false, "
            "`cargo test -p bloomery-daemon` build"),
        "instrumented_distinct_fn_items_src_only": meas(
            r["distinct_src"], len(r["units"]), "the same, restricted to crates/*/src"),
        "raw_site_total": meas(
            r["raw_site_total"], len(r["units"]),
            "sum of sites across manifests -- larger than the distinct count because a "
            "crate compiled at two feature sets is two units over the same files"),
        "units_that_fell_back": meas(
            len(r["fell_back"]), len(r["units"]),
            "manifests with fell_back true, `-p bloomery-daemon` build"),
        "fell_back_stderr_lines": meas(
            len(raw["raw_e8"]["fell_back_stderr_lines"]), 1,
            "`fell back to the real tree` lines across every build log of the E8 sequence"),
        "unreached_files": meas(
            len(r["unreached_files"]), len(r["units"]),
            "files a unit's module walk could not reach, unioned over manifests"),
        "skipped_items": meas(
            len(r["skipped"]), len(r["units"]),
            "fn items the transformer skipped by rule (const/extern/macro/async)"),
        "denominators": {k: v[0] for k, v in E2_DENOMS.items()},
        "units": r["units"],
        "unreached_file_list": r["unreached_files"],
        "skipped_reasons": _count(r["skipped"], "reason"),
    }
    if wide.get("distinct") is not None:
        out["workspace_wide"] = {
            "instrumented_distinct_fn_items": meas(
                wide["distinct"], len(wide["units"]),
                "distinct fn items from a supplementary workspace-wide instrumented "
                "`--no-run` (declared and disk-guarded before any E2 number was read; "
                "adds no timed arm and moves no threshold)"),
            "over_all": round(wide["distinct"] / E2_DENOM_ALL, 6),
            "units_that_fell_back": len(wide["fell_back"]),
            "unreached_files": len(wide["unreached_files"]),
        }
    elif wide:
        out["workspace_wide"] = {"dropped": wide.get("dropped", "not run")}
    return out


def _count(items, key):
    out = {}
    for it in items:
        out[it.get(key, "?")] = out.get(it.get(key, "?"), 0) + 1
    return out


def _e0(raw):
    r = raw["raw_e0"]
    whole = r.get("whole_invocation")
    pairs = r.get("pairs", {})
    worst, worst_n = None, 0
    rows = {}
    for label, p in pairs.items():
        info, diff = p.get("info"), p.get("diff")
        rows[label] = {
            "info_wall_s": meas(info["median"] if info else None, info["n"] if info else 0,
                                "/usr/bin/time -f %e around `sensorium info <run>`, median of 3 "
                                "CONSECUTIVE runs on the same trace file -- runs 2 and 3 read a "
                                "warm page cache, so this is a warm-read median, not a "
                                "cold-start one",
                                [] if info else ["the pair was not converted"]),
            "diff_wall_s": meas(diff["median"] if diff else None, diff["n"] if diff else 0,
                                "/usr/bin/time -f %e around `sensorium diff <a> <b>`, "
                                "identical pair (two tier-call runs of the same binary), "
                                "median of 3 CONSECUTIVE runs on the same two trace files -- "
                                "runs 2 and 3 read a warm page cache, so this is a warm-read "
                                "median, not a cold-start one",
                                [] if diff else ["the pair was not converted"]),
            "diff_verdict": (diff["stdout_last"].strip().splitlines()[:6] if diff else None),
            "events": [pk["events"] if pk else None for pk in p.get("picked", [])],
            "trace_bytes": [pk["bytes"] if pk else None for pk in p.get("picked", [])],
            "threads": [pk["threads"] if pk else None for pk in p.get("picked", [])],
            "spools_without_end": [pk["spools_without_end"] if pk else None
                                   for pk in p.get("picked", [])],
            "processes_converted": [len(rr["convert"]["procs"]) if rr.get("convert") else None
                                    for rr in p["runs"]],
            "thread_names": p.get("thread_names"),
        }
        for m in (rows[label]["info_wall_s"], rows[label]["diff_wall_s"]):
            if m["value"] is not None and (worst is None or m["value"] > worst):
                worst, worst_n = m["value"], m["n"]
    e0 = {
        "headline": meas(worst, worst_n,
                         "the LARGEST of the four medians (info and diff on --lib and on "
                         "--test config_test); the rule is `> 60 s on --lib or on "
                         "config_test` -> STOP and re-plan the trace unit",
                         [] if worst is not None else ["no pair was converted"]),
        "per_binary": rows,
    }
    if whole:
        ev = whole["events"]
        e0["whole_invocation"] = {
            "processes": meas(len(whole["procs"]), 1,
                              "one trace per pid from the last E1 call-arm spool, doctest "
                              "processes included"),
            "events": meas(ev, len(whole["procs"]), "CALL+RETURN records converted"),
            "trace_bytes": meas(whole["bytes"], len(whole["procs"]),
                                "sum of the format-4 .db files"),
            "spool_bytes": meas(whole["spool_bytes"], len(whole["procs"]),
                                "sum of the on-disk spool files (24 B/record + headers)"),
            "spools_without_end": meas(whole["spools_without_end"], len(whole["procs"]),
                                       "spools with no THREAD_END: a thread alive at process "
                                       "exit loses its buffered tail (rung-2 gap)"),
            "convert_wall_s": meas(whole["wall"], 1,
                                   "`convert.py` over the whole invocation, one process"),
            "bytes_per_event_on_disk": meas(
                round(whole["spool_bytes"] / ev, 3) if ev else None, ev,
                "spool bytes / events"),
            "per_process": whole["procs"],
        }
    else:
        e0["whole_invocation"] = {"dropped": raw["raw_e0"].get(
            "whole_invocation_dropped", "the last call-arm spool was not available")}
    return e0


def _binaries(raw):
    """Cargo's own `Running` lines for the kept call-arm invocation, against the
    executables that actually produced a spool.

    The pre-registered item is "number of test binaries cargo ran", which is NOT
    the number of processes that spooled and NOT the number of distinct
    executables in the trace set: a binary with no tests never enters an
    instrumented fn, and a spawned child is a process cargo never ran.
    Derived from the raw artifacts (the invocation's own log), not re-measured."""
    kept = raw["raw_e1"].get("kept_spool")
    rec = next((r for r in raw["raw_e1"]["runs"] if r.get("spool") == kept), None)
    if rec is None:
        return None
    log = LOGS / f"e1-r{rec['round']}-{rec['arm']}.log"
    if not log.is_file():
        return None
    text = log.read_text()
    ran = {}
    # `Running <target> (<exe>)`, where <target> is `tests/x.rs` for an
    # integration test but `unittests src/lib.rs` for a lib/bin unit-test
    # binary -- two tokens, which a `\S+` here silently dropped (3 of 72).
    for m in re.finditer(r"^\s+Running (.+) \((\S+)\)$", text, re.M):
        ran[m.group(2).rsplit("/", 1)[-1]] = m.group(1)
    doctests = len(re.findall(r"^\s+Doc-tests ", text, re.M))
    whole = (raw["raw_e0"].get("whole_invocation") or {}).get("procs") or []
    spooled = {p["exe"] for p in whole}
    silent = sorted(set(ran) - spooled)
    children = sorted(spooled - set(ran))
    return {"ran": ran, "doctests": doctests, "spooled": spooled,
            "silent": silent, "children": children, "processes": len(whole)}


def _e7(raw):
    r = raw["raw_e7"]
    e7ok = [k for k in r["ok"] if k.startswith("e7")]
    e7bad = [k for k in r["fail"] if k.startswith("e7")]
    return {
        "headline": meas(len(e7bad), len(e7ok) + len(e7bad),
                         "differences in `panicked at <file>:<line>:<col>`, in a "
                         "`file!()`/`line!()` value, or in a backtrace frame's "
                         "<file>:<line>, plain vs off and plain vs call, on the PROBE "
                         "workspace (bloomery is read-only for this plan): "
                         "rust/spike/tests/mechanics.sh, --test-threads=1 --nocapture, "
                         "durations and the OS tid masked"),
        "checks_ok": meas(len(r["ok"]), len(r["ok"]) + len(r["fail"]),
                          "mechanics.sh checks that passed"),
        "checks_failed": meas(len(r["fail"]), len(r["ok"]) + len(r["fail"]),
                              "mechanics.sh checks that failed"),
        "rc": r["rc"],
        "e7_lines": r["e7_lines"],
        "all_checks": r["ok"],
    }


def _e8(raw):
    r = raw["raw_e8"]
    ck = r["checks"]
    failed = [k for k, v in ck.items() if not v["pass"]]
    lens = ("on BLOOMERY, `-p bloomery-daemon`, counting Compiling/Fresh of the workspace "
            "packages from `cargo ... -v`; check (b) is PROBE-ONLY because the bloomery "
            "tree is read-only for this plan")
    probe_b = [k for k in raw["raw_e7"]["ok"] if k.startswith("e8b")]
    return {
        "headline": meas(len(failed), len(ck), "failed checks of E8(a), (c)+sentinel, (d); "
                         + lens, []),
        "checks": ck,
        "b_on_the_probe_workspace": meas(
            0 if probe_b else None, 1,
            "E8(b) `touch one source line -> exactly that unit and its dependents "
            "recompile`, run on the PROBE workspace only (mechanics.sh: "
            "e8b_edited_unit_and_dependents_recompile)",
            [] if probe_b else ["mechanics.sh did not report the e8b check"]),
        "builds": r["builds"],
        "expected_fresh_set": r["expected_fresh_set"],
        "clean_no_run_wall_s": {
            "plain": meas(r["builds"]["plain1"]["wall"], 1,
                          "wall of `cargo test -p bloomery-daemon --no-run -v` -- LENS: the "
                          "plain artifacts pre-existed, so this is a no-op freshness check, "
                          "not a build"),
            "instrumented": meas(r["builds"]["instr1"]["wall"], 1,
                                 "wall of `cargo sensorium test -p bloomery-daemon --no-run "
                                 "-v` -- a genuine clean build of the instrumented artifact "
                                 "set (mirror + transform + rustc for every workspace unit)"),
        },
        "test_binary_size_bytes": {
            "plain": meas(ck["c_sentinel"].get("plain_exe_bytes"), 1,
                          "the plain --lib test binary"),
            "instrumented": meas(ck["c_sentinel"].get("instrumented_exe_bytes"), 1,
                                 "the instrumented --lib test binary"),
        },
    }


def _bench(raw):
    """Parse the micro-bench's `result` lines. The lens is TWO tokens
    (`caller=dev(opt0) rt=opt3`), which is why this is re-parsed here from the
    stored lines rather than trusted from the runner's first pass."""
    out = {}
    for ln in raw["raw_bench"]["lines"]:
        m = re.match(r"result (caller=\S+ rt=\S+) arm=(\S+) metric=(\S+) value=([\d.]+)", ln)
        if m:
            out.setdefault(m.group(1), {}).setdefault(m.group(2), {})[m.group(3)] = float(m.group(4))
    return out


def assemble(raw: dict, which: str) -> dict:
    bench = _bench(raw) or raw["raw_bench"]["results"]
    b = _binaries(raw)
    out = {
        "schema": raw["schema"],
        "spike": raw["spike"],
        "pins": raw["pins"],
        "e2_headline_denominator": which,
        "endpoints": {"E0": _e0(raw), "E1": _e1(raw), "E2": _e2(raw, which),
                      "E7": _e7(raw), "E8": _e8(raw)},
        "reported_without_a_gate": {
            "micro_bench": {"lenses": bench, "lines": raw["raw_bench"]["lines"]},
            "test_binaries_run": meas(
                len(b["ran"]) if b else None, 1,
                "test binaries cargo RAN in one `cargo test -p bloomery-daemon` call-arm "
                "invocation, counted from cargo's own `Running <target> (<exe>)` lines in "
                "that invocation's log; a `Doc-tests` line is counted separately below",
                [] if b else ["the kept call-arm invocation's log was not available"]),
            "doctest_targets_run": meas(
                b["doctests"] if b else None, 1,
                "`Doc-tests` lines in the same log; bloomery-daemon has 0 doctests, so this "
                "target ran 0 tests and produced no process",
                [] if b else ["the kept call-arm invocation's log was not available"]),
            "test_binaries_that_spooled": meas(
                len(b["ran"]) - len(b["silent"]) if b else None, 1,
                "of the binaries cargo ran, those that produced at least one spool file. "
                "The difference is named in `test_binaries_that_did_not_spool`",
                [] if b else ["the kept call-arm invocation's log was not available"]),
            "test_binaries_that_did_not_spool": {
                "value": len(b["silent"]) if b else None, "n": 1,
                "lens": "a binary that runs 0 tests never enters an instrumented fn and so "
                        "never opens a spool -- not a recorder failure",
                "dropped": [] if b else ["the kept call-arm invocation's log was not available"],
                "names": b["silent"] if b else None,
                "targets": [b["ran"][x] for x in b["silent"]] if b else None},
            "spooling_processes": meas(
                b["processes"] if b else None, 1,
                "PROCESSES that spooled in the same invocation: the binaries that spooled "
                "plus every instrumented child they spawned "
                "(here 48 `flywheel-tool` children); this is the number E0 converted",
                [] if b else ["the whole-invocation conversion was not available"]),
            "spawned_child_executables": {
                "value": len(b["children"]) if b else None, "n": 1,
                "lens": "distinct executables that spooled but appear in no `Running` line",
                "dropped": [] if b else ["the kept call-arm invocation's log was not available"],
                "names": b["children"] if b else None},
            "per_process_exit_status_available": meas(
                0, 1, "a DESIGN FACT read off the wire format and the runtime, not a "
                      "measurement: the record stream carries no exit code and a Drop-based "
                      "runtime is bypassed by `std::process::exit`, so the converter writes "
                      "cargo's status for every process (exit_status_basis = cargo). §1 "
                      "pre-registered this as `expected: NOT available to the runtime`; the "
                      "0 records that expectation holding, and no instrument was run for it"),
            "spike_build_wall_s": meas(
                4.24, 1, "`cargo clean --release && cargo build --release` in rust/spike "
                         "(4 workspace units recompiled; third-party deps stayed warm). "
                         "PROVENANCE: transcribed by hand from the preflight transcript in "
                         "task-5-report.md §1 -- this one was run before the runner existed "
                         "and has NO log in logs/; reported, not gated"),
        },
        "cleanup": raw.get("cleanup"),
        "steps": raw.get("steps"),
        "finished": raw.get("finished"),
    }
    if "refused" in raw:
        out["refused"] = raw["refused"]
    if "error" in raw:
        out["error"] = raw["error"]
    return out
