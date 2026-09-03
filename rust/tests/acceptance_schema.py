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

from acceptance_lib import meas
from acceptance_phases import wall_summary

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
                                      "the build's manifests, so a crate compiled at "
                                      "two feature sets contributes its sites twice; "
                                      "the distinct count is the census's", dropped),
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


def assemble(raw: dict, dry_run: bool = False) -> dict:
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
        "reported": _reported(raw, dry_run),
        "cleanup": raw.get("cleanup"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"),
        "error": raw.get("error"),
        "started": raw.get("started"),
        "finished": raw.get("finished"),
    }
