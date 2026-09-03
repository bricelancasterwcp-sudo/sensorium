#!/usr/bin/env python3
"""`results.json` -> §3 of the rung-2 acceptance document.

The renderer's one rule: a `null` value is printed as
`not measured (<reason>)` and never as anything else -- not as a dash, not as
a zero, not as an empty cell. `0` is a measured zero and prints as `0`.

    .venv/bin/python rust/tests/render_acceptance.py [results.json] > section3.md

§4 is not rendered. It is written by hand against the pre-registered rules.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT = (REPO / ".superpowers" / "sdd"
           / "2026-09-02-sensorium-rung2-recorder-v1" / "acceptance" / "results.json")
LENS_CAP = 110


def cell(m, fmt=str) -> str:
    """One measurement as a table cell. `null` is not-measured, with why."""
    if m is None:
        return "not measured (absent from results.json)"
    if m.get("value") is None:
        why = "; ".join(m.get("dropped") or []) or "no reason recorded"
        return f"not measured ({why})"
    return fmt(m["value"])


def pct(v) -> str:
    return f"{v * 100:.1f}%"


def n_of(m) -> str:
    return "not measured" if m is None else str(m.get("n"))


def lens_of(m) -> str:
    if m is None:
        return "not measured"
    lens = m.get("lens", "")
    return (lens[:LENS_CAP] + "…") if len(lens) > LENS_CAP else lens


def dropped_of(m) -> str:
    if m is None:
        return "not measured"
    d = m.get("dropped") or []
    return "; ".join(d) if d else "none"


def row(label, m, fmt=str) -> str:
    return f"| {label} | {cell(m, fmt)} | {n_of(m)} | {lens_of(m)} | {dropped_of(m)} |"


def headline(r) -> list[str]:
    e = r["endpoints"]
    rules = {
        "E2′": "floor 98% of eligible fn items; any fell-back unit stops the rung",
        "E3": "DIVERGED 0/19 and REFUSED 0/19",
        "E5": "A/B MATCH modulo location with ≥1 moved, 0 added, 0 removed, every "
              "task paired; A/C DIVERGED",
        "E7": "any difference stops the rung",
        "E8": "any failed check stops the rung",
    }
    fmts = {"E2′": pct, "E3": str, "E5": str, "E7": str, "E8": str}
    keys = {"E2′": "E2prime", "E3": "E3", "E5": "E5", "E7": "E7", "E8": "E8"}
    out = ["| Id | Value | n | Lens (abridged; the full lens is in "
           "`results.json`) | Dropped |", "|---|---|---|---|---|"]
    for label, key in keys.items():
        m = e[key]["headline"]
        out.append(f"| {label} | {cell(m, fmts[label])} (rule: {rules[label]}) | "
                   f"{n_of(m)} | {lens_of(m)} | {dropped_of(m)} |")
    return out


def e2_section(r) -> list[str]:
    e = r["endpoints"]["E2prime"]
    c = e.get("census") or {}
    t = c.get("totals") or {}
    out = ["### E2′ — transformer coverage of the measured workspace", "",
           "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|"]
    for label, key in (
            ("instrumented fn items, workspace-wide build", "workspace_numerator"),
            ("eligible fn items, same file set", "workspace_denominator"),
            ("instrumented fn items, package build", "package_numerator"),
            ("eligible fn items, the files that build reaches", "package_denominator"),
            ("package files outside the denominator's directories",
             "package_files_outside_denominator"),
            ("units that fell back to the real tree", "units_that_fell_back"),
            ("`fell back to the real tree` stderr lines", "fell_back_stderr_lines"),
            ("files a module walk could not reach", "unreached_files"),
            ("fn items skipped by rule", "skipped_items"),
            ("spawn sites rewritten", "spawn_sites_rewritten"),
            ("spawn sites declared, not rewritten", "spawn_sites_declared_unwrapped"),
            ("declaring units (crate_name, crate_type)", "declaring_units"),
            ("manifests outside the measured build's unit set", "out_of_scope_manifests"),
            ("units whose mirror was opened and checked", "mirror_identity_checked"),
            ("mirrors naming another unit's metadata", "mirror_identity_wrong")):
        out.append(row(label, e.get(key)))
    out += ["", "Denominators, both from `sensorium-transform`'s own `census` — the "
            "parser that did the instrumenting — over the same tree:", "",
            "| Denominator (eligible fn items) | Numerator over the SAME files | Reading |",
            "|---|---|---|"]
    wn, wd = e["workspace_numerator"], e["workspace_denominator"]
    pn, pd = e["package_numerator"], e["package_denominator"]
    if wn["value"] is not None and wd["value"]:
        out.append(f"| the whole workspace ({wd['value']}) | {wn['value']} | "
                   f"{pct(wn['value'] / wd['value'])} ← §4's reading |")
    if pn["value"] is not None and pd["value"]:
        out.append(f"| the files a package build reaches ({pd['value']}) | "
                   f"{pn['value']} | {pct(pn['value'] / pd['value'])} |")
    if c:
        out += ["", f"Census: {c.get('files')} files walked, {c.get('parsed')} parsed; "
                f"{t.get('fn_items')} `fn` items with a body, {t.get('const_fns')} "
                f"`const fn`, {t.get('extern_fns')} `extern` fn, {t.get('async_fns')} "
                f"`async fn` → {t.get('eligible')} eligible."]
    return out


def e3_section(r) -> list[str]:
    e = r["endpoints"]["E3"]
    out = ["### E3 — does the comparator report a false DIVERGED?", "",
           f"Test binary sha256 `{e.get('binary_sha256')}`, asserted equal before "
           "every recorded run.", "",
           "| K | run 1 | run K | verdict | CLI exit |", "|---|---|---|---|---|"]
    for d in e.get("table", []):
        verdict = d.get("verdict") or "not measured (no verdict line)"
        out.append(f"| {d['k']} | `{d.get('a')}` | `{d.get('b')}` | {verdict} | "
                   f"{d.get('rc')} |")
    out += ["", "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|"]
    for label, key in (("DIVERGED verdicts", "diverged"),
                       ("REFUSED verdicts", "refused"),
                       ("MATCH verdicts", "matched"),
                       ("runs that produced a trace", "runs"),
                       ("runs whose binary sha256 moved", "sha256_mismatches")):
        out.append(row(label, e.get(key)))
    return out


def e5_section(r) -> list[str]:
    e = r["endpoints"]["E5"]
    arms = e.get("arms") or {}
    out = ["### E5 — does `diff --ignore-moves` verify a source-file split?", "",
           "| Arm | Tree | run | events | threads | tests run |",
           "|---|---|---|---|---|---|"]
    for k in ("A", "B", "C"):
        a = arms.get(k) or {}
        out.append(f"| {k} | `{a.get('ref')}` | `{a.get('run')}` | {a.get('events')} | "
                   f"{a.get('threads')} | {len(a.get('tests') or [])} |")
    out += ["", "| Pre-registered condition | Met |", "|---|---|"]
    for k, v in (e.get("conditions") or {}).items():
        out.append(f"| `{k}` | {'yes' if v else 'NO'} |")
    out.append("")
    out.append(row("E5 conditions not met", e.get("headline")))
    for label, key in (("A/B `--ignore-moves`", "ab_ignore_moves"),
                       ("A/C `--ignore-moves`", "ac_ignore_moves"),
                       ("A/B plain `diff` (reported)", "ab_plain"),
                       ("A/C, one task (drill-down)", "ac_task")):
        d = (e.get("diffs") or {}).get(key)
        if not d:
            continue
        out += ["", f"**{label}** — `sensorium {' '.join(d['argv'])}`, verbatim:", "",
                "```", d.get("stdout", "").rstrip(), "```"]
    return out


def e7_section(r) -> list[str]:
    e = r["endpoints"]["E7"]
    out = ["### E7 — line numbers, paths and backtraces", "",
           "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|"]
    for label, key in (("(a) E7 checks passed on the probe", "a_checks_ok"),
                       ("(a) E7 checks failed on the probe", "a_checks_failed"),
                       ("(a) mechanics.sh checks passed", "a_script_ok"),
                       ("(a) mechanics.sh checks failed", "a_script_failed"),
                       ("(b) differences, plain vs call", "b_differences"),
                       ("(b) panic locations on the plain side", "b_panic_locations"),
                       ("(b) spool files the instrumented arm wrote",
                        "b_spool_files_under_call")):
        out.append(row(label, e.get(key)))
    if e.get("a_driver_unchanged") is not None:
        out += ["", f"The driver's sha256 was unchanged across mechanics.sh: "
                f"{e['a_driver_unchanged']}."]
    if e.get("b_section_differences"):
        out += ["", "(b) differing lines, verbatim:", "", "```",
                "\n".join(e["b_section_differences"]), "```"]
    return out


def e8_section(r) -> list[str]:
    e = r["endpoints"]["E8"]
    out = ["### E8 — cargo freshness, and contamination of a plain build", "",
           "| Check | Result | Compiled | Fresh |", "|---|---|---|---|"]
    for name, c in (e.get("checks") or {}).items():
        if name == "c_sentinel":
            out.append(f"| (c) sentinel: the plain binary writes no spool, the "
                       f"instrumented one does | {'PASS' if c.get('pass') else 'FAIL'} | "
                       f"plain wrote {c.get('plain')} spool files | instrumented wrote "
                       f"{c.get('instrumented')} |")
            continue
        out.append(f"| `{name}` | {'PASS' if c.get('pass') else 'FAIL'} | "
                   f"`{c.get('compiled')}` | `{c.get('fresh')}` |")
    out += ["", f"The expected `Fresh` set is `{e.get('expected_fresh_set')}` — "
            "asserted, not merely 'compiled nothing', because a build that dies "
            "before its first `Compiling` line also compiles nothing.", "",
            "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|",
            row("baseline build wall (s)", e.get("baseline_build_wall_s")),
            row("instrumented build wall (s)", e.get("instrumented_build_wall_s"))]
    return out


def reported_section(r) -> list[str]:
    rep = r["reported"]
    out = ["### Reported without a gate", "",
           "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|"]
    for label, key in (
            ("wall, plain median (s)", "wall_plain_median_s"),
            ("wall, call median (s)", "wall_call_median_s"),
            ("wall ratio call/plain", "wall_ratio_call_over_plain"),
            ("processes in one whole invocation", "invocation_processes"),
            ("events in one whole invocation", "invocation_events"),
            ("trace bytes", "invocation_trace_bytes"),
            ("spool bytes", "invocation_spool_bytes"),
            ("bytes per event (trace)", "bytes_per_event_trace"),
            ("bytes per event (spool)", "bytes_per_event_spool"),
            ("events per second of suite wall", "events_per_second_of_suite_wall"),
            ("conversion wall (s)", "conversion_wall_s"),
            ("child runs named by a parent", "child_runs_total"),
            ("live threads at process exit", "live_threads"),
            ("live threads with a torn last record",
             "live_threads_with_torn_last_record"),
            ("seq gaps", "seq_gaps"),
            ("records dropped", "records_dropped"),
            ("truncated captures", "truncated_count"),
            ("panics unrecorded", "panics_unrecorded"),
            ("manifests unscoped", "manifests_unscoped"),
            ("driver fixed cost (s)", "driver_fixed_cost_s"),
            ("runtime rlib build (s)", "runtime_rlib_build_s"),
            ("mean wall of one recorded --lib run (s)", "e3_run_wall_s")):
        out.append(row(label, rep.get(key)))
    basis = rep.get("exit_status_basis")
    if basis:
        out += ["", "`exit_status_basis` across the invocation: "
                + ", ".join(f"{k} × {v}" for k, v in basis.items()) + "."]
    arms = rep.get("wall_arms") or {}
    if arms.get("P", {}).get("walls"):
        out += ["", "| Round | P (plain) | C (call) |", "|---|---|---|"]
        p, c = arms["P"]["walls"], arms["C"]["walls"]
        for i in range(max(len(p), len(c))):
            out.append(f"| {i + 1} | {p[i] if i < len(p) else '—'} s | "
                       f"{c[i] if i < len(c) else '—'} s |")
        out.append(f"| **median** | {arms['P']['median']} s | {arms['C']['median']} s |")
        out.append(f"| **min** | {arms['P']['min']} s | {arms['C']['min']} s |")
        out.append(f"| **max** | {arms['P']['max']} s | {arms['C']['max']} s |")
    return out


def main(argv) -> int:
    path = Path(argv[0]) if argv else DEFAULT
    r = json.loads(path.read_text())
    lines = ["## 3. Results", ""]
    if r.get("dry_run"):
        lines += ["**DRY RUN — no acceptance number was measured.** Every endpoint "
                  "cell below reads `not measured (dry run …)`; what this proves is "
                  "that every step runs and every artifact is written.", ""]
    lines += [f"Measured on the §2 pins. Runner: `rust/tests/acceptance.py` "
              f"(raw logs and `results-raw.json` in the gitignored ledger). "
              f"Started {r.get('started')}, finished {r.get('finished')}. "
              "Every cell below is a number with its `n` and its lens, or "
              "`not measured (<reason>)`.", ""]
    lines += headline(r) + [""]
    for section in (e2_section, e3_section, e5_section, e7_section, e8_section,
                    reported_section):
        lines += section(r) + [""]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
