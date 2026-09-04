"""Raw acceptance facts -> `results.json` in the pre-registered shape.

Every measurement is `{"value", "n", "lens", "dropped"}`; a `null` value with
a non-empty `dropped` list is the ONLY representation of not-measured, and
`0` is measured-and-zero. Nothing here decides a verdict -- the endpoint rows
carry the number and the rule's own wording, and §4 of the acceptance
document is written by hand against them.

`assemble(raw, dry_run)` is total: a phase that did not run leaves its cells
`null` with the reason the runner recorded, never a zero.
"""

from __future__ import annotations

from collections import Counter

from acceptance_lib import meas
from acceptance_phases import wall_summary

NOOP_N = 5      # `acceptance_addendum.py`'s sample count for the no-op walls

DRY = "dry run: the plumbing was exercised, no acceptance number was measured"


def _outside(pkg, prefixes) -> int:
    """Files in a build's manifests that the denominator's directories do not
    cover. A ratio whose numerator reaches outside its denominator is not a
    coverage figure -- rung 1's findings §5.14, written into a check."""
    return len([f for f in (pkg.get("sites_by_file") or {})
                if not f.startswith(tuple(prefixes))])


def _drop(raw, key):
    """The reason a phase is missing, or []."""
    v = raw.get(key)
    if v is None:
        return [f"{key} did not run"]
    if isinstance(v, dict) and v.get("dropped"):
        return [v["dropped"]]
    return []


# ------------------------------------------------------------------- E2'


def _e2(raw, dry) -> dict:
    e8 = raw.get("raw_e8") or {}
    ws = raw.get("raw_e2_workspace") or {}
    census = raw.get("raw_census") or {}
    denom_all = census.get("totals", {}).get("eligible")
    denom_reached = census.get("reached_eligible")
    pkg = e8.get("package_manifests") or {}
    wsm = ws.get("manifests") or {}
    scope_lens = (
        "numerator = DISTINCT (file, qualname, firstlineno) over the manifests of "
        "ONE measured build, scoped to that build's own unit set (the `-C metadata=` "
        "values in its `cargo -v` log -- complete because the target directory was "
        "emptied first, so cargo compiled every unit and invoked the wrapper for "
        "each); the manifests directory was cleared before the workspace-wide build "
        "so no earlier tool hash's manifest can enter the count; denominator = "
        "`sensorium-transform`'s own census over the SAME file set")
    num = wsm.get("distinct")
    dropped = [] if num is not None else (
        [ws.get("dropped", "the workspace-wide instrumented --no-run did not run")])
    value = round(num / denom_all, 6) if (num is not None and denom_all) else None
    out = {
        "headline": meas(None if dry else value, denom_all or 0,
                         f"instrumented {num} / {denom_all} eligible fn items, both over "
                         f"crates/*/src + crates/*/tests; {scope_lens}",
                         [DRY] if dry else dropped),
        "workspace_numerator": meas(num, len(wsm.get("units", [])),
                                    "distinct fn items from the workspace-wide "
                                    "instrumented --no-run", dropped),
        "workspace_denominator": meas(denom_all, census.get("files", 0),
                                      "census eligible fn items over crates/*/src + "
                                      "crates/*/tests"),
        "package_numerator": meas(pkg.get("distinct"), len(pkg.get("units", [])),
                                  "distinct fn items from the from-scratch "
                                  "instrumented package build, read before E8(b) "
                                  "touched a source file"),
        "package_denominator": meas(denom_reached, census.get("reached_files", 0),
                                    "census eligible fn items over the files that "
                                    "package build reaches: "
                                    + ", ".join(census.get("reached_prefixes", []))),
        "package_files_outside_denominator": meas(
            _outside(pkg, census.get("reached_prefixes", [])) if pkg else None,
            len(pkg.get("units", [])),
            "files the package build instrumented that are NOT under the "
            "denominator's directories -- anything but 0 means the two sides "
            "of the ratio below are not the same file set"),
        "package_ratio": meas(
            None if dry else (round(pkg["distinct"] / denom_reached, 6)
                              if pkg.get("distinct") is not None and denom_reached
                              else None),
            denom_reached or 0,
            "numerator and denominator over the SAME file set (the package build's)",
            [DRY] if dry else []),
        "units_that_fell_back": meas(
            len(wsm.get("fell_back", [])) if wsm else None,
            len(wsm.get("units", [])),
            "manifests with fell_back true in the workspace-wide build", dropped),
        "fell_back_stderr_lines": meas(
            len(e8.get("fell_back_stderr_lines", [])) if e8 else None, 1,
            "`fell back to the real tree` lines across every E8 build log",
            _drop(raw, "raw_e8")),
        "unreached_files": meas(len(wsm.get("unreached_files", [])) if wsm else None,
                                len(wsm.get("units", [])),
                                "files a unit's module walk could not reach, unioned",
                                dropped),
        "skipped_items": meas(len(wsm.get("skipped", [])) if wsm else None,
                              len(wsm.get("units", [])),
                              "fn items skipped by rule (const/extern/async/macro)",
                              dropped),
        "spawn_sites_rewritten": meas(wsm.get("spawns_wrapped"),
                                      len(wsm.get("units", [])),
                                      "spawn sites replaced with "
                                      "::sensorium_rt::spawn_child -- the RAW SUM over "
                                      "the build's manifests, not a count of distinct "
                                      "sites: two (crate_name, crate_type) pairs "
                                      "declare two manifests each, so their sites are "
                                      "counted twice. The census counts the distinct "
                                      "sites", dropped),
        "spawn_sites_declared_unwrapped": meas(
            len(wsm.get("spawns_declared", [])) if wsm else None,
            len(wsm.get("units", [])),
            "spawn shapes left alone and declared with a reason", dropped),
        "declaring_units": meas(len(wsm.get("declaring_pairs", [])) if wsm else None,
                                len(wsm.get("units", [])),
                                "distinct (crate_name, crate_type) pairs declaring "
                                "a manifest", dropped),
        "out_of_scope_manifests": meas(
            len(wsm.get("out_of_scope_manifests", [])) if wsm else None,
            len(wsm.get("units", [])),
            "manifest files present but NOT in the measured build's unit set", dropped),
        "mirror_identity_checked": meas(
            (ws.get("mirror_identity") or {}).get("checked"),
            len(wsm.get("units", [])),
            "units whose mirror crate root was opened and found to name that "
            "unit's own -C metadata; a check that examined nothing proves "
            "nothing, so the count is reported", dropped),
        "mirror_identity_wrong": meas(
            len((ws.get("mirror_identity") or {}).get("wrong", []))
            if ws.get("mirror_identity") else None,
            len(wsm.get("units", [])),
            "mirrors naming another unit's metadata", dropped),
        "census": census,
        "package_units": pkg.get("units"),
        "workspace_units": wsm.get("units"),
        "fell_back_units": wsm.get("fell_back"),
    }
    return out


# -------------------------------------------------------------------- E3


def _e3(raw, dry) -> dict:
    r = raw.get("raw_e3") or {}
    diffs = r.get("diffs") or []
    verdicts = [d.get("verdict") for d in diffs]
    diverged = sum(1 for v in verdicts if v == "DIVERGED")
    refused = sum(1 for v in verdicts if v == "REFUSED")
    unmeasured = sum(1 for v in verdicts if v is None)
    dropped = _drop(raw, "raw_e3") + (
        [f"{unmeasured} of {len(diffs)} pairs produced no verdict"] if unmeasured else [])
    lens = ("`sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE "
            "test binary built once; the binary's sha256 was re-asserted equal before "
            "every run, so no pair spans a rebuild")
    return {
        "headline": meas(None if dry else (diverged + refused if diffs else None),
                         len(diffs),
                         f"DIVERGED + REFUSED verdicts over {len(diffs)} diffs; " + lens,
                         [DRY] if dry else dropped),
        "diverged": meas(diverged if diffs else None, len(diffs), lens, dropped),
        "refused": meas(refused if diffs else None, len(diffs), lens, dropped),
        "matched": meas(sum(1 for v in verdicts if v and v.startswith("MATCH"))
                        if diffs else None, len(diffs), lens, dropped),
        "runs": meas(len([x for x in (r.get("runs") or []) if x.get("run")]),
                     len(r.get("runs") or []),
                     "recorded runs that produced a trace"),
        "binary_sha256": r.get("sha256"),
        "sha256_mismatches": meas(len(r.get("sha256_mismatches", []))
                                  if r.get("runs") else None,
                                  len(r.get("runs") or []),
                                  "runs whose binary sha256 differed from run 1's",
                                  _drop(raw, "raw_e3")),
        "events_per_run": [x.get("events") for x in (r.get("runs") or [])],
        "table": [{"k": d["k"], "a": d.get("a"), "b": d.get("b"),
                   "verdict": d.get("verdict"), "rc": d.get("rc")} for d in diffs],
    }


# -------------------------------------------------------------------- E5


def _e5(raw, dry) -> dict:
    r = raw.get("raw_e5") or {}
    d = r.get("diffs") or {}
    ab = d.get("ab_ignore_moves") or {}
    ac = d.get("ac_ignore_moves") or {}
    conds = {
        "ab_verdict_is_match": (ab.get("verdict") or "").startswith("MATCH"),
        "ab_moved_at_least_one": bool(ab.get("moved")),
        "ab_zero_added": ab.get("added") is False,
        "ab_zero_removed": ab.get("removed") is False,
        "ab_every_task_paired": ab.get("tasks_all_matched") is True,
        "ac_verdict_is_diverged": ac.get("verdict") == "DIVERGED",
    }
    have = bool(ab) and bool(ac)
    failed = [k for k, v in conds.items() if not v]
    lens = ("three arms on three trees (original / split / split + one planted swap of "
            "two consecutive independent call statements), each `cargo sensorium test "
            "<pkg> --lib -- <filter>`; verdicts from `sensorium diff --ignore-moves`")
    return {
        "headline": meas(None if dry else (len(failed) if have else None), len(conds),
                         f"pre-registered E5 conditions not met, of {len(conds)}; " + lens,
                         [DRY] if dry else (_drop(raw, "raw_e5")
                                            or ([] if have else ["a diff did not run"]))),
        "conditions": conds,
        "conditions_failed": failed,
        "ab_verdict": ab.get("verdict"), "ab_verdict_line": ab.get("verdict_line"),
        "ab_moved": meas(ab.get("moved"), 1,
                         "code objects paired across a move by qualname (A/B)"),
        "ac_verdict": ac.get("verdict"), "ac_verdict_line": ac.get("verdict_line"),
        "ab_plain_verdict": (d.get("ab_plain") or {}).get("verdict"),
        "arms": r.get("arms"),
        "diffs": d,
    }


# -------------------------------------------------------------------- E7


def _e7(raw, dry) -> dict:
    a = raw.get("raw_e7a") or {}
    b = raw.get("raw_e7b") or {}
    e7_ok = [c for c in a.get("ok", []) if c.startswith("e7")]
    e7_fail = [c for c in a.get("fail", []) if c.startswith("e7")]
    total = None
    if a and b:
        total = len(e7_fail) + b.get("differences", 0)
    lens = ("(a) `rust/tests/mechanics.sh` on the probe workspace: panic locations, "
            "file!()/line!() values and backtrace frames, plain vs off vs call, "
            "durations and rustc's (<tid>) masked; (b) the measured workspace's own "
            "`--lib -- --test-threads=1` output, plain vs call, same masking")
    return {
        "headline": meas(None if dry else total, len(e7_ok) + len(e7_fail) + 1,
                         f"E7(a) failed checks + E7(b) masked differences; {lens}",
                         [DRY] if dry else (_drop(raw, "raw_e7a") + _drop(raw, "raw_e7b"))),
        "a_checks_ok": meas(len(e7_ok) if a else None, len(e7_ok) + len(e7_fail),
                            "E7 checks that passed in mechanics.sh",
                            _drop(raw, "raw_e7a")),
        "a_checks_failed": meas(len(e7_fail) if a else None, len(e7_ok) + len(e7_fail),
                                "E7 checks that failed in mechanics.sh",
                                _drop(raw, "raw_e7a")),
        "a_script_ok": meas(len(a.get("ok", [])) if a else None, 1,
                            "every check mechanics.sh passed (E7 and E8 on the probe, "
                            "and the rest of rust/HONESTY.md's falsifiable half)",
                            _drop(raw, "raw_e7a")),
        "a_script_failed": meas(len(a.get("fail", [])) if a else None, 1,
                                "every check mechanics.sh failed",
                                _drop(raw, "raw_e7a")),
        "a_driver_unchanged": a.get("driver_unchanged"),
        "b_differences": meas(b.get("differences") if b else None,
                              b.get("section_lines", 0),
                              "differences in the masked libtest section, the "
                              "`test result:` line, or a panic location, plain vs call",
                              _drop(raw, "raw_e7b")),
        "b_panic_locations": meas(len(b.get("panic_locations_plain", [])) if b else None,
                                  2, "`panicked at <file>:<line>:<col>` locations on the "
                                  "plain side -- 0 would make the location comparison "
                                  "vacuous, so the count is reported",
                                  _drop(raw, "raw_e7b")),
        "b_spool_files_under_call": meas(
            (b.get("arms", {}).get("call") or {}).get("spool_files") if b else None, 1,
            "spool files the instrumented arm wrote -- 0 would mean E7(b) compared a "
            "tool that did nothing", _drop(raw, "raw_e7b")),
        "b_section_differences": b.get("section_differences"),
        "a_e7_lines": a.get("e7_lines"),
    }


# -------------------------------------------------------------------- E8


def _e8(raw, dry) -> dict:
    r = raw.get("raw_e8") or {}
    checks = r.get("checks") or {}
    failed = [k for k, v in checks.items() if not v.get("pass")]
    lens = ("on the measured workspace with its target directory emptied first, "
            "counting Compiling/Fresh from `cargo -v` AND asserting the expected "
            "Fresh set -- a build that dies before its first Compiling line also "
            "compiles nothing")
    return {
        "headline": meas(None if dry else (len(failed) if checks else None), len(checks),
                         f"failed checks of {len(checks)}; " + lens,
                         [DRY] if dry else _drop(raw, "raw_e8")),
        "failed_checks": failed,
        "checks": checks,
        "expected_fresh_set": r.get("expected_fresh_set"),
        "baseline_build_wall_s": meas(
            (r.get("builds", {}).get("plain1") or {}).get("wall"), 1,
            "wall of the plain `--no-run` on an EMPTIED target directory: a "
            "genuinely clean build of this package's whole build graph, third-party "
            "dependencies included, sources and target on different filesystems"),
        "instrumented_build_wall_s": meas(
            (r.get("builds", {}).get("instr1") or {}).get("wall"), 1,
            "wall of the first instrumented `--no-run` on the same emptied target"),
        "builds": r.get("builds"),
    }


# ------------------------------------------------- reported without a gate


def _reported(raw, dry) -> dict:
    w = raw.get("raw_walls") or {}
    runs = w.get("runs") or []
    p, c = wall_summary(runs, "P"), wall_summary(runs, "C")
    whole = raw.get("raw_whole") or {}
    costs = raw.get("raw_costs") or {}
    e3 = raw.get("raw_e3") or {}
    wall_lens = (
        "wall clock of `cargo test <pkg> --lib` (P) versus `cargo sensorium test "
        "<pkg> --lib` (C), binaries pre-built, dev profile, default --test-threads, "
        "rounds interleaved with the order alternating P,C then C,P, 10 s cool-down "
        "between arms, 1-minute load recorded at each arm's start and an arm DROPPED "
        "(never re-rolled) above 4.0. The call arm carries tier call: CALL and RETURN "
        "with the captured return value, so it also carries the return-value capture "
        "cost -- plan decision D10 states that cost is LINEAR in the length of a "
        "returned std collection, so this ratio is a property of what this suite "
        "returns, not a constant")
    ratio = (round(c["median"] / p["median"], 4)
             if c["median"] and p["median"] else None)
    ev = whole.get("events")
    tb = whole.get("trace_bytes")
    return {
        "wall_plain_median_s": meas(p["median"], p["n"], wall_lens, p["dropped"]),
        "wall_call_median_s": meas(c["median"], c["n"], wall_lens, c["dropped"]),
        "wall_ratio_call_over_plain": meas(
            None if dry else ratio, min(p["n"], c["n"]),
            "median(call)/median(plain); " + wall_lens,
            [DRY] if dry else (p["dropped"] + c["dropped"] if ratio is None else [])),
        "wall_arms": {"P": p, "C": c}, "wall_runs": runs,
        "invocation_processes": meas(whole.get("processes"), 1,
                                     "traces converted from one `cargo sensorium test "
                                     "-p <pkg>` invocation: every test binary plus "
                                     "every instrumented child it spawned"),
        "invocation_events": meas(ev, whole.get("processes", 0),
                                  "CALL/RETURN/PANIC records converted"),
        "invocation_trace_bytes": meas(tb, whole.get("processes", 0),
                                       "sum of the format-4 .db files"),
        "invocation_spool_bytes": meas(whole.get("spool_bytes"),
                                       whole.get("processes", 0),
                                       "sum of the on-disk spool files"),
        "bytes_per_event_trace": meas(round(tb / ev, 3) if ev else None,
                                      ev or 0, "trace bytes / events"),
        "bytes_per_event_spool": meas(
            round(whole.get("spool_bytes", 0) / ev, 3) if ev else None, ev or 0,
            "spool bytes / events (24 B per record plus one header per thread)"),
        "events_per_second_of_suite_wall": meas(
            round(ev / whole["wall"], 1) if ev and whole.get("wall") else None,
            whole.get("processes", 0),
            "events / the whole invocation's wall, conversion included -- an "
            "order of magnitude for the suite, not a recorder throughput number"),
        "conversion_wall_s": meas(
            whole.get("conversion_wall"), whole.get("processes", 0),
            "`cargo-sensorium convert <spool>` over the SAME spool the invocation "
            "just converted in-process, so the number is a second, warm-cache pass "
            "over the whole invocation -- the shape rung 1 reported as 22.7 s"),
        "exit_status_basis": whole.get("exit_status_basis"),
        "exit_status_basis_histogram": meas(
            ", ".join(f"{k} x {v}" for k, v in
                      (whole.get("exit_status_basis") or {}).items()) or None,
            whole.get("processes", 0),
            "the basis each process's `exit_status` was written on, one per trace: "
            "`waited` = the target runner spawned that process and waited for it, so "
            "the status is witnessed; `unwitnessed` = nothing this recorder ran saw "
            "the process end (a child the runner never spawned), so the field is "
            "declared rather than borrowed from cargo",
            [] if whole.get("exit_status_basis") else ["the whole invocation did not run"]),
        "child_runs_total": meas(whole.get("child_runs_total"),
                                 whole.get("processes", 0),
                                 "child run ids named by a parent trace"),
        "live_threads": meas(whole.get("live_thread_count"),
                             whole.get("processes", 0),
                             "threads with no THREAD_END record at process exit, "
                             "summed over every trace of the invocation"),
        "live_threads_with_torn_last_record": meas(
            len(whole.get("spools_with_torn_last_record", []))
            if whole.get("spool_files") else None,
            whole.get("spool_files", 0),
            "spool files whose last record runs past the end of the file: the "
            "MAP_SHARED claim, read from the spool bytes rather than from the "
            "converter that wrote them"),
        "seq_gaps": meas(whole.get("seq_gaps"), whole.get("processes", 0),
                         "seq gaps summed over the invocation's traces"),
        "records_dropped": meas(whole.get("records_dropped"),
                                whole.get("processes", 0),
                                "records the runtime dropped, summed"),
        "truncated_count": meas(whole.get("truncated_count"),
                                whole.get("processes", 0),
                                "captured values truncated at the repr cap, summed"),
        "panics_unrecorded": meas(whole.get("panics_unrecorded"),
                                  whole.get("processes", 0),
                                  "panics the runtime saw but could not attribute"),
        "manifests_unscoped": meas(whole.get("manifests_unscoped"),
                                   whole.get("processes", 0),
                                   "manifests with no workspace_root -- 0 is the "
                                   "expected reading on a from-scratch target"),
        "driver_fixed_cost_s": meas(
            costs.get("driver_overhead_s"), 3,
            "median of 3 no-op `--no-run` builds through the release driver minus "
            "the median of 3 straight to cargo, same package, everything Fresh"),
        "runtime_rlib_build_s": meas(
            costs.get("rt_build_s"), 1,
            "one `--no-run` with <target>/sensorium/rt removed, minus the warm "
            "no-op driver median above: the runtime's own rustc build"),
        "e3_run_wall_s": meas(
            (lambda ws: round(sum(ws) / len(ws), 3) if ws else None)(
                [x["wall"] for x in (e3.get("runs") or []) if x.get("wall")]),
            len([x for x in (e3.get("runs") or []) if x.get("wall")]),
            "mean wall of one recorded `--lib` invocation during E3 (build Fresh, "
            "conversion included)"),
        "invocation_warn_lines": whole.get("warn_lines"),
    }


# ------------------------------------------------ the addendum (re-measured)


def _addendum(raw, reported) -> dict | None:
    """The reported-without-a-gate items, re-measured after the converter fix.

    Nothing here touches a gated endpoint: `endpoints` and `reported` are the
    numbers the acceptance run measured, and this block sits BESIDE them. Every
    row carries the 46074ef value it is compared against, and a row that has no
    46074ef counterpart says so in `dropped` rather than inventing one."""
    a = raw.get("raw_addendum")
    if not a or a.get("refused") or a.get("error"):
        return None
    pins = a.get("pins") or {}
    cw = a.get("conversion_whole") or {}
    lt = a.get("lib_trace") or {}
    lc = (lt.get("conversion") or {})
    costs = a.get("costs") or {}
    runs = (a.get("walls") or {}).get("runs") or []
    p, c = wall_summary(runs, "P"), wall_summary(runs, "C")
    ratio = (round(c["median"] / p["median"], 4)
             if c["median"] and p["median"] else None)
    warm = ("the SAME acceptance target directory, WARM (it holds the acceptance "
            "run's artifacts; only the driver changed), clone at e209ed9, traces "
            "to a NEW SENSORIUM_DIR so the run's own remain untouched")
    wall_lens = (
        "wall clock of `cargo test -p bloomery-daemon --lib` (P) versus "
        "`cargo sensorium test -p bloomery-daemon --lib` (C), binaries pre-built, "
        "5 rounds interleaved with the order alternating P,C then C,P, 10 s "
        "cool-down, the 1-minute load read at each arm's start and an arm DROPPED "
        "above 4.0 -- the run's own protocol, re-run; " + warm)
    new = "no 46074ef counterpart: this row is new to the addendum"

    def before(key):
        return reported.get(key)

    rows = [
        {"item": "conversion wall, whole invocation (s)",
         "before": before("conversion_wall_s"),
         "after": meas(cw.get("median"), cw.get("n", 0),
                       "`cargo-sensorium convert <spool>` over the SAME spool "
                       "directory the acceptance run recorded and had already "
                       "converted in-process -- a second pass, exactly as the "
                       "46074ef cell was; 119 processes converted each pass; "
                       + warm,
                       cw.get("dropped", []))},
        {"item": "wall, plain median (s)", "before": before("wall_plain_median_s"),
         "after": meas(p["median"], p["n"], wall_lens, p["dropped"])},
        {"item": "wall, call median (s)", "before": before("wall_call_median_s"),
         "after": meas(c["median"], c["n"], wall_lens, c["dropped"])},
        {"item": "wall ratio call/plain",
         "before": before("wall_ratio_call_over_plain"),
         "after": meas(ratio, min(p["n"], c["n"]),
                       "median(call)/median(plain); " + wall_lens,
                       p["dropped"] + c["dropped"] if ratio is None else [])},
        {"item": "conversion wall, one `--lib` trace (s)",
         "before": meas(None, 0, "not a 46074ef row", [new]),
         "after": meas(lc.get("median"), lc.get("n", 0),
                       "`cargo-sensorium convert` over the spool of ONE recorded "
                       "`--lib` invocation (1390 events, 1 process), a second pass "
                       "over an already-converted spool -- subtract it from the "
                       "call median above to see what the command spends outside "
                       "conversion; " + warm,
                       lc.get("dropped", []))},
        {"item": "one recorded `--lib` invocation wall (s)",
         "before": meas(None, 0, "not a 46074ef row", [
             new + "; the nearest 46074ef figure is E3's mean over 20 recorded "
             "runs (12.38 s), a different estimand"]),
         "after": meas(lt.get("invocation_wall"), 1,
                       "one `cargo sensorium test -p bloomery-daemon --lib`, "
                       "build Fresh, conversion included, whose spool the row "
                       "above converts; " + warm)},
        {"item": "driver fixed cost (s)", "before": before("driver_fixed_cost_s"),
         "after": meas(costs.get("driver_overhead_s"), NOOP_N,
                       "median of 5 no-op `--tier off --no-run` invocations through "
                       "the driver minus the median of 5 straight to cargo, same "
                       "package, everything Fresh -- the 46074ef estimand at n=5 "
                       "instead of n=3; the first sample of each arm (3.514 s and "
                       "2.875 s) is a cold-cache outlier the median excludes and "
                       "the raw file keeps; " + warm)},
        {"item": "driver no-op invocation wall (s)",
         "before": meas(None, 0, "not a 46074ef row", [new]),
         "after": meas(costs.get("instrumented_median"), NOOP_N,
                       "the absolute wall of one no-op `--tier off --no-run` "
                       "invocation, median of 5, nothing to subtract; " + warm)},
        {"item": "runtime rlib build (s)", "before": before("runtime_rlib_build_s"),
         "after": meas(costs.get("rt_build_s"), 1,
                       "one `--no-run` with `<target>/sensorium/rt` removed "
                       f"({costs.get('rt_removed_bytes')} bytes), minus the warm "
                       "no-op median above; n=1, as at 46074ef; " + warm)},
    ]
    return {
        "measured_with": {
            "commit": pins.get("repo_commit"),
            "driver_sha256": pins.get("driver_sha256"),
            "started": pins.get("started"), "finished": a.get("finished"),
            "clone_head": pins.get("clone_head"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "whole_spool": pins.get("whole_spool"),
            "why": ("the converter's one-transaction-per-trace fix "
                    "(`synchronous=NORMAL` under WAL) landed after the acceptance "
                    "run, so the reported-without-a-gate items -- and only those -- "
                    "were read again"),
        },
        "rows": rows,
        "walls": {"P": p, "C": c, "runs": runs},
        "cleanup": a.get("cleanup"),
    }


def assemble(raw: dict, dry_run: bool = False) -> dict:
    reported = _reported(raw, dry_run)
    addendum = _addendum(raw, reported)
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null value "
                   "plus a dropped reason is the ONLY not-measured; 0 is "
                   "measured-and-zero"),
        "acceptance": ("docs/superpowers/acceptance/"
                       "2026-09-02-sensorium-rung2-acceptance.md"),
        "dry_run": dry_run,
        "pins": raw.get("pins"),
        "endpoints": {"E2prime": _e2(raw, dry_run), "E3": _e3(raw, dry_run),
                      "E5": _e5(raw, dry_run), "E7": _e7(raw, dry_run),
                      "E8": _e8(raw, dry_run)},
        "reported": reported,
        "addendum": addendum,
        "cleanup": raw.get("cleanup"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"),
        "error": raw.get("error"),
        "started": raw.get("started"),
        "finished": raw.get("finished"),
    }


# ------------------------------------------------------------------- E5'


E5PRIME_DOC = ("docs/superpowers/acceptance/"
               "2026-09-03-sensorium-rung3-entry-e5prime.md")

# The reading of the A/B verdict line, ruled BEFORE the run (ledger, Task 3;
# `t5-context.md` §4) and repeated here so `results.json` carries it: on a
# trace whose causal events all live in tasks, the literal `MATCH modulo
# location` string prints only on the thread-stream branch, which is empty
# here. §1's label denotes the class the committed rung-2 schema `_e5`
# already encodes -- verdict token startswith MATCH, moved >= 1, 0 added,
# 0 removed, every task paired -- and that is how the condition is judged.
AB_READING = (
    "§1's label `MATCH modulo location` denotes the committed rung-2 `_e5` "
    "condition class (verdict token startswith MATCH; >= 1 moved; 0 added; "
    "0 removed; every task paired), because on a trace whose causal events "
    "all live in tasks the literal string prints only on the thread-stream "
    "branch. Ruled in the ledger before the run, not after the number.")


def _e5prime_env(raw: dict) -> dict:
    """§2's facts: what was measured, with what, on what."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or {}
    arms = (raw.get("raw_e5") or {}).get("arms") or {}
    return {
        "byte_lock": raw.get("byte_lock"),
        "driver": pins.get("driver"), "driver_sha256": pins.get("driver_sha256"),
        "driver_mtime": pins.get("driver_mtime"),
        "driver_unchanged_after": cl.get("driver_unchanged"),
        "repo_commit": pins.get("repo_commit"), "repo_branch": pins.get("repo_branch"),
        "repo_porcelain": pins.get("repo_porcelain"),
        "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
        "python": pins.get("python"),
        "sensorium_version": pins.get("sensorium_version"),
        "nproc": pins.get("nproc"), "governor": pins.get("governor"),
        "clone": pins.get("clone"), "clone_head": pins.get("clone_head"),
        "arm_tips": pins.get("arm_tips"),
        "arm_heads": {k: v.get("head") for k, v in arms.items()},
        "clone_porcelain_before": pins.get("clone_porcelain_before"),
        "clone_porcelain_after": cl.get("clone_porcelain_after"),
        "clone_restored": cl.get("clone_restored"),
        "cargo_lock_unchanged": cl.get("cargo_lock_unchanged"),
        "target_dir": pins.get("target_dir"), "target_warm": pins.get("target_warm"),
        "manifests_cleared_before_arm_a": len(
            pins.get("manifests_cleared_before_arm_a") or []),
        "manifests_cleared_bytes": pins.get("manifests_cleared_bytes"),
        "sensorium_dir": pins.get("sensorium_dir"),
        "source_bloomery": pins.get("source_bloomery"),
        "source_bloomery_head_before": pins.get("source_bloomery_head_before"),
        "source_bloomery_head_after": cl.get("source_bloomery_head_after"),
        "source_bloomery_porcelain_before":
            pins.get("source_bloomery_porcelain_before"),
        "source_bloomery_porcelain_after": cl.get("source_bloomery_porcelain_after"),
        "source_bloomery_unchanged": cl.get("source_bloomery_unchanged"),
        "load_1min_at_start": pins.get("load_1min_at_start"),
        "load_at_each_arm": raw.get("arm_checkout_loads"),
        "target_disk_free_gb": pins.get("target_disk_free_gb"),
        "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
        "unused_env": pins.get("unused_env"),
    }


def _e5prime_main(raw: dict) -> dict:
    """E5': the six committed rung-2 `_e5` conditions plus §1's `all ten task
    streams` clause, read on the A/B `--ignore-moves` diff."""
    base = _e5(raw, False)
    d = (raw.get("raw_e5") or {}).get("diffs") or {}
    ab, ac = d.get("ab_ignore_moves") or {}, d.get("ac_ignore_moves") or {}
    conds = dict(base["conditions"])
    conds["ab_all_ten_task_streams_paired"] = (
        ab.get("tasks_all_matched") is True and ab.get("tasks_each_side") == 10)
    failed = [k for k, v in conds.items() if not v]
    have = bool(ab) and bool(ac)
    lens = ("three arms on three trees of the clone (A = e209ed9, B = e5-split, "
            "C = e5-planted), each `cargo sensorium test -p bloomery-daemon --lib "
            "-- task::registry` under the driver of §2 on the warm rung-2 target; "
            "verdicts from `sensorium diff --ignore-moves`. " + AB_READING)
    return {
        "headline": meas(len(failed) if have else None, len(conds),
                         f"pre-registered E5' conditions not met, of "
                         f"{len(conds)}; " + lens,
                         _drop(raw, "raw_e5")
                         or ([] if have else ["a diff did not run"])),
        "conditions": conds, "conditions_failed": failed,
        "ab_reading": AB_READING,
        "ab_verdict": ab.get("verdict"), "ab_verdict_line": ab.get("verdict_line"),
        "ac_verdict": ac.get("verdict"), "ac_verdict_line": ac.get("verdict_line"),
        "ab_plain_verdict": (d.get("ab_plain") or {}).get("verdict"),
        "ab_plain_verdict_line": (d.get("ab_plain") or {}).get("verdict_line"),
        "ac_task_verdict": (d.get("ac_task") or {}).get("verdict"),
        "ac_task_verdict_line": (d.get("ac_task") or {}).get("verdict_line"),
        "ab_moved": meas(ab.get("moved"), 1,
                         "code objects paired across a move by qualname (A/B "
                         "`--ignore-moves`, from the `key:` line)"),
        "ab_tasks_each_side": meas(
            ab.get("tasks_each_side"), ab.get("tasks_each_side"),
            "task streams on each side of the A/B `--ignore-moves` diff, "
            "compared by content as (name, hash) -- the tool's own `tasks:` line"),
        "arms": base.get("arms"), "diffs": base.get("diffs"),
    }


def _e5prime_names(raw: dict) -> dict:
    """E5'-names: the predicted string on both sides, and A's multiset of
    `(name, hash)` equal to B's.

    Two numbers, because §1's sentence has two conjuncts and they read
    differently. The hash read here is the STORED `task_fingerprints.hash`,
    which TRACE-FORMAT §7 defines as a blake2b over `(file, qualname, kind)`
    per causal event -- so a file move changes it by construction, and
    `diff --ignore-moves` re-hashes both sides at query time rather than
    trusting it. Both readings are carried; neither is silently chosen."""
    n = raw.get("names") or {}
    e = raw.get("names_endpoint") or {}
    d = (raw.get("raw_e5") or {}).get("diffs") or {}
    ab = d.get("ab_ignore_moves") or {}
    dropped = e.get("dropped") or []
    a, b = n.get("A") or {}, n.get("B") or {}
    total = (a.get("spawn_count") or 0) + (b.get("spawn_count") or 0)
    bad = len(e.get("not_as_predicted") or [])
    pairs_differing = None
    if e.get("a_multiset") is not None and e.get("b_multiset") is not None:
        # A true multiset difference over the WHOLE (name, hash) pair: how many
        # of A's pairs have no equal pair left in B. Reported post-run as a
        # positional zip over two hash-sorted lists, which is not a pairing --
        # A [(x,h1),(x,h2)] against B [(x,h2),(x,h3)] would have read 2, not 1.
        # The value on this record is unchanged (4 of 4); only the definition is.
        ma = Counter(tuple(x) for x in e["a_multiset"])
        mb = Counter(tuple(x) for x in e["b_multiset"])
        pairs_differing = sum((ma - mb).values())
    name_lens = ("every task name containing `spawn@` on arms A and B, read from "
                 "each arm's own trace with `select task_id, name, hash, n_events "
                 "from task_fingerprints order by task_id` against "
                 "`$SENSORIUM_DIR/traces/<run>.db` opened read-only (the CLI has "
                 "no `tasks` command); compared to "
                 "`task::registry::tests::<test> :: spawn@TaskRegistry::"
                 "spawn_task#1`")
    hash_lens = ("the STORED `task_fingerprints.hash` of the same four children, "
                 "A against B as a multiset of (name, hash). TRACE-FORMAT §7: the "
                 "stored hash is a blake2b over `file\\x1fqualname\\x1fkind` per "
                 "causal event, so a file move changes it by construction; "
                 "`diff --ignore-moves` re-hashes both sides at query time "
                 "instead of reading this column; counted as the multiset "
                 "difference A - B over whole (name, hash) pairs, i.e. A-pairs "
                 "with no equal pair left in B, not a positional zip")
    conjuncts = {
        "every_spawn_name_is_the_predicted_string": (
            None if dropped else bad == 0 and total > 0),
        "stored_name_hash_multiset_a_equals_b": (
            None if dropped else e.get("multiset_equal") is True),
    }
    missed = ([k for k, v in conjuncts.items() if v is False]
              if not dropped else [])
    return {
        "predicted_shape": e.get("predicted_shape"),
        "conjuncts": conjuncts, "conjuncts_missed": missed,
        "headline": meas(len(missed) if not dropped else None, len(conjuncts),
                         "§1 E5'-names conjuncts missed, of 2 — (a) every "
                         "spawn@ name is the predicted string, (b) the multiset "
                         "of (name, hash) pairs on A equals B's. Each conjunct's "
                         "own number is in the table below; the hash conjunct is "
                         "read on the STORED column, which is the source §1's "
                         "Method names", dropped),
        "names_not_as_predicted": meas(bad if not dropped else None, total,
                                       "spawned-child task names that are NOT the "
                                       "predicted string, of the four on A plus "
                                       "the four on B; " + name_lens, dropped),
        "names_as_predicted": meas((total - bad) if not dropped else None, total,
                                   "spawned-child task names equal to the "
                                   "predicted string; " + name_lens, dropped),
        "spawn_tasks_a": meas(a.get("spawn_count"), a.get("task_count"),
                              "task streams on arm A whose name contains "
                              "`spawn@`, of every task stream in that trace"),
        "spawn_tasks_b": meas(b.get("spawn_count"), b.get("task_count"),
                              "task streams on arm B whose name contains "
                              "`spawn@`, of every task stream in that trace"),
        "stored_hash_pairs_differing": meas(
            pairs_differing, len(e.get("a_multiset") or []),
            "of the four (name, hash) pairs, those whose HASH component differs "
            "between A and B; " + hash_lens,
            dropped),
        "stored_multiset_equal": e.get("multiset_equal"),
        "a_multiset": e.get("a_multiset"), "b_multiset": e.get("b_multiset"),
        "not_as_predicted": e.get("not_as_predicted"),
        "differ_tasks_line": ab.get("verdict_line") and next(
            (l for l in (ab.get("stdout") or "").splitlines()
             if l.startswith("tasks: ")), None),
        "differ_all_matched": ab.get("tasks_all_matched"),
        "names": {k: {"run": (n.get(k) or {}).get("run"),
                      "query": (n.get(k) or {}).get("query"),
                      "task_count": (n.get(k) or {}).get("task_count"),
                      "spawn_tasks": (n.get(k) or {}).get("spawn_tasks")}
                  for k in ("A", "B", "C")},
    }


def _e5prime_coverage(raw: dict) -> dict:
    """E5'-coverage: units that fell back to the real tree, across the arms."""
    cov = raw.get("coverage_endpoint") or {}
    am = raw.get("arm_manifests") or {}
    per_arm = cov.get("per_arm_fell_back") or {}
    n = sum((v.get("units_seen") or 0) for v in am.values())
    written = sum((v.get("units_written_during_this_arm") or 0) for v in am.values())
    lens = (f"`fell_back: true` over the manifests each arm's build left in "
            f"`<target>/sensorium/manifests/`, snapshotted the moment that arm's "
            f"build returned; the directory was cleared before arm A, so no "
            f"rung-2 manifest can enter the count. n counts unit-manifests read "
            f"across the three arms ({written} of them written by the arm that "
            f"read them; the rest were units cargo found fresh and did not "
            f"recompile, so no new manifest was written for them)")
    return {
        "headline": meas(cov.get("units_fell_back"), n, lens,
                         cov.get("dropped") or []),
        "units_fell_back": meas(cov.get("units_fell_back"), n, lens,
                                cov.get("dropped") or []),
        "per_arm_fell_back": per_arm,
        "units_seen_per_arm": cov.get("units_seen"),
        "unit_manifests_written_by_their_own_arm": written,
        "unreached_reasons": cov.get("unreached_reasons"),
        "spawn_sites_wrapped_per_arm": {
            k: (v.get("read_manifests_summary") or {}).get("spawns_wrapped")
            for k, v in am.items()},
        "spawn_sites_declared_unwrapped_per_arm": {
            k: len((v.get("read_manifests_summary") or {}).get("spawns_declared")
                   or []) for k, v in am.items()},
        "unreached_files_per_arm": {
            k: (v.get("read_manifests_summary") or {}).get("unreached_files")
            for k, v in am.items()},
        "units": {k: [{"crate_name": u["crate_name"],
                       "crate_type": u["crate_type"],
                       "fell_back": u["fell_back"],
                       "fallback_reason": u["fallback_reason"],
                       "files": u["files"], "sites": u["sites"],
                       "spawns": len(u["spawns"]),
                       "written_during_this_arm": u["written_during_this_arm"]}
                      for u in (v.get("units") or [])]
                  for k, v in am.items()},
    }


def assemble_e5prime(raw: dict) -> dict:
    """Raw E5' facts -> the E5' document's `results.json`.

    Same shape and same rules as `assemble`: every measurement is
    {value, n, lens, dropped}, a null value with a reason is the ONLY
    not-measured, and 0 is measured-and-zero. Nothing here decides a verdict;
    §4 of the E5' document is written by hand against §1's rules."""
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null value "
                   "plus a dropped reason is the ONLY not-measured; 0 is "
                   "measured-and-zero"),
        "acceptance": E5PRIME_DOC,
        "runner": raw.get("runner"),
        "byte_lock": raw.get("byte_lock"),
        "pins": raw.get("pins"),
        "environment": _e5prime_env(raw),
        "endpoints": {"E5prime": _e5prime_main(raw),
                      "E5prime_names": _e5prime_names(raw),
                      "E5prime_coverage": _e5prime_coverage(raw)},
        "reported": {
            "arm_walls_s": {k: (v or {}).get("wall")
                            for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                         or {}).items()},
            "arm_events": {k: (v or {}).get("events")
                           for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                        or {}).items()},
            "arm_threads": {k: (v or {}).get("threads")
                            for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                         or {}).items()},
            "arm_tests": {k: len((v or {}).get("tests") or [])
                          for k, v in ((raw.get("raw_e5") or {}).get("arms")
                                       or {}).items()},
            "arm_run_lines": raw.get("arm_run_lines"),
            "ab_plain_verdict": ((raw.get("raw_e5") or {}).get("diffs")
                                 or {}).get("ab_plain", {}).get("verdict"),
            "ac_task_verdict": ((raw.get("raw_e5") or {}).get("diffs")
                                or {}).get("ac_task", {}).get("verdict"),
        },
        "cleanup": raw.get("cleanup"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"),
        "error": raw.get("error"),
        "started": raw.get("started"),
        "finished": raw.get("finished"),
    }
