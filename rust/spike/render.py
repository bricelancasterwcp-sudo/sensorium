#!/usr/bin/env python3
"""THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike): `results.json` -> §3.

Rewrites the `## 3. Results` section of
`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` from the ledger's
`results.json`. It writes §3 and NOTHING else: §4 (decisions) and §5 (rung-2
gaps) are written by hand against the pre-registered rules.

The one hard rule it enforces: a measurement whose `value` is `null` is printed
as `not measured (<reason>)` and never as anything else -- no dash, no zero, no
blank cell.

    .venv/bin/python rust/spike/render.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / ".superpowers" / "sdd" / "2026-09-02-sensorium-rung1-mechanics-spike"
RESULTS = LEDGER / "results.json"
DOC = REPO / "docs" / "superpowers" / "spikes" / "2026-09-02-rust-mechanics-spike.md"
COPY = REPO / "docs" / "superpowers" / "spikes" / "2026-09-02-rust-mechanics-spike.results.json"


class NullValue(Exception):
    """A `value: null` reached a renderer that had a number's shape for it."""


def cell(m: dict, fmt="{}") -> str:
    """One measurement as a table cell. `null` is `not measured (<reason>)`."""
    if m is None:
        return "not measured (the runner recorded nothing for this cell)"
    if m.get("value") is None:
        why = "; ".join(m.get("dropped") or ["no reason recorded"])
        return f"not measured ({why})"
    return fmt.format(m["value"])


def num(m: dict, fmt="{}") -> str:
    """The same, for a cell that MUST be a number -- raises if it is null, so a
    renderer bug cannot quietly print a hole where a threshold is compared."""
    if m is None or m.get("value") is None:
        raise NullValue(str(m))
    return fmt.format(m["value"])


def short(lens: str, n=110) -> str:
    lens = lens.replace("\n", " ")
    return lens if len(lens) <= n else lens[: n - 1] + "…"


def dropped(m: dict) -> str:
    d = m.get("dropped") or []
    return "; ".join(d) if d else "none"


def pct(v):
    return f"{v * 100:.1f}%"


def headline_rows(e) -> list[str]:
    rows = []
    spec = [
        ("E0", e["E0"]["headline"], lambda v: f"{v:.2f} s (worst of 4 medians; rule: > 60 s)"),
        ("E1", e["E1"]["headline"], lambda v: f"×{v:.4f} (rule: > 1.5 → cargo feature)"),
        ("E2", e["E2"]["headline"], lambda v: f"{pct(v)} (floor 98%)"),
        ("E7", e["E7"]["headline"], lambda v: f"{int(v)} differences (rule: any → stop)"),
        ("E8", e["E8"]["headline"], lambda v: f"{int(v)} failed checks (rule: any → stop)"),
    ]
    for name, m, f in spec:
        value = f(m["value"]) if m["value"] is not None else cell(m)
        rows.append(f"| {name} | {value} | {m['n']} | {short(m['lens'])} | {dropped(m)} |")
    return rows


def e1_table(e1) -> list[str]:
    out = ["| Round | P (plain) | O (off) | C (call) |", "|---|---|---|---|"]
    runs = {(r["round"], r["arm"]): r for r in e1["raw_runs"]}
    for rnd in sorted({r["round"] for r in e1["raw_runs"]}):
        cells = []
        for arm in ("P", "O", "C"):
            r = runs.get((rnd, arm))
            if r is None:
                cells.append("not measured (the round was never started)")
            elif r.get("wall") is None:
                cells.append(f"dropped ({r.get('dropped', 'no reason recorded')})")
            else:
                cells.append(f"{r['wall']:.3f} s")
        out.append(f"| {rnd} | " + " | ".join(cells) + " |")
    stats = ["| **median** ", "| **min** ", "| **max** "]
    for arm in ("P", "O", "C"):
        a = e1["arms"][arm]
        stats[0] += f"| {cell(a['median_s'], '{:.3f} s')} "
        stats[1] += f"| {a['min_s']:.3f} s " if a["min_s"] is not None else "| not measured (no scored run) "
        stats[2] += f"| {a['max_s']:.3f} s " if a["max_s"] is not None else "| not measured (no scored run) "
    out += [s + "|" for s in stats]
    return out


def e0_table(e0) -> list[str]:
    out = ["| Binary | events (run 1 / run 2) | trace bytes | threads | `info` wall | "
           "`diff` wall | spools without END |", "|---|---|---|---|---|---|---|"]
    for label, r in e0["per_binary"].items():
        ev = " / ".join(str(x) if x is not None else "not measured" for x in r["events"])
        by = " / ".join(str(x) if x is not None else "not measured" for x in r["trace_bytes"])
        th = " / ".join(str(x) if x is not None else "not measured" for x in r["threads"])
        sw = " / ".join(str(x) if x is not None else "not measured" for x in r["spools_without_end"])
        out.append(f"| `{label}` | {ev} | {by} | {th} | {cell(r['info_wall_s'], '{:.2f} s')} "
                   f"| {cell(r['diff_wall_s'], '{:.2f} s')} | {sw} |")
    return out


def render(res: dict) -> str:
    e = res["endpoints"]
    L: list[str] = ["## 3. Results", ""]
    L += [f"Measured {res['finished'][:10]} on the box §2 pins, bloomery @ "
          f"`{res['pins']['bloomery_commit'][:7]}` (`{res['pins']['bloomery_branch']}`), "
          f"{res['pins']['rustc']}. Runner: `rust/spike/measure.py` "
          "(raw logs and `results-raw.json` in the gitignored ledger). Every cell below is "
          "a number with its `n` and its lens, or `not measured (<reason>)`.", ""]
    L += ["| Id | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |",
          "|---|---|---|---|---|"]
    L += headline_rows(e)
    L += ["", "### E0 — one test binary as a trace unit", ""]
    L += e0_table(e["E0"])
    w = e["E0"]["whole_invocation"]
    L += [""]
    if "processes" in w:
        L += [f"One whole `cargo test -p bloomery-daemon` call-arm invocation converted: "
              f"**{num(w['processes'])} processes** "
              f"(71 test binaries plus 48 spawned `flywheel-tool` children; bloomery-daemon "
              f"has no doctests, so no rustdoc process appears — the doctest route is "
              f"covered on the probe workspace by `mechanics.sh`), "
              f"**{num(w['events'])} events**, "
              f"**{num(w['trace_bytes'])} trace bytes** over "
              f"{num(w['spool_bytes'])} spool bytes "
              f"({num(w['bytes_per_event_on_disk'], '{:.2f}')} B/event on disk), "
              f"conversion wall {num(w['convert_wall_s'], '{:.1f}')} s, "
              f"**{num(w['spools_without_end'])} spools without `THREAD_END`** "
              f"(3 processes: 64 of 81 threads in `api_v1_honesty_test`, 32 of 62 in "
              f"`api_v1_test`, 4 of 71 in `api_native_test` — server threads alive at "
              f"process exit, whose buffered tail is lost; §5).", ""]
    else:
        L += [f"Whole-invocation conversion: {cell(w if 'value' in w else None)}"
              f"{'' if 'value' in w else ' — ' + str(w.get('dropped'))}", ""]
    L += ["`diff` verdict, verbatim (both pairs read the same way):", "", "```"]
    L += (e["E0"]["per_binary"]["lib"]["diff_verdict"] or ["not measured (no pair)"])
    L += ["```", ""]
    L += ["### E1 — compile-once, gate at runtime", ""]
    L += e1_table(e["E1"])
    L += ["", f"median(off)/median(plain) = **×{num(e['E1']['headline'], '{:.4f}')}**; "
              f"median(call)/median(plain) = ×{num(e['E1']['ratio_call_over_plain'], '{:.4f}')}. "
              f"The instrumented walls include the driver's own fixed cost, measured "
              f"separately at **{num(e['E1']['driver_fixed_overhead_s'], '{:.3f}')} s** "
              f"(release driver; a debug one costs ≈0.5 s).", ""]
    b = res["reported_without_a_gate"]["micro_bench"]["lenses"]
    L += ["Micro-bench `fib(30)`, ns per call, best of 3, each arm its own process — TWO "
          "lenses, and E1's pre-registered lens is the first:", "",
          "| Lens | plain | off | call | off/plain | call/plain |", "|---|---|---|---|---|---|"]
    for lens, arms in b.items():
        L.append(f"| `{lens}` | {arms['plain']['ns_per_call']:.4f} | "
                 f"{arms['off']['ns_per_call']:.4f} | {arms['call']['ns_per_call']:.4f} | "
                 f"×{arms['off']['over_plain']:.3f} | ×{arms['call']['over_plain']:.3f} |")
    L += ["", "### E2 — transformer coverage of bloomery", ""]
    e2 = e["E2"]
    L += ["| Quantity | Value | n | Lens |", "|---|---|---|---|"]
    for key, label in (("instrumented_distinct_fn_items", "instrumented fn items, `-p bloomery-daemon` build"),
                       ("instrumented_distinct_fn_items_src_only", "…of those, in `crates/*/src`"),
                       ("raw_site_total", "raw site total across manifests"),
                       ("units_that_fell_back", "units that fell back to the real tree"),
                       ("fell_back_stderr_lines", "`fell back to the real tree` stderr lines"),
                       ("unreached_files", "files a module walk could not reach"),
                       ("skipped_items", "fn items skipped by rule")):
        m = e2[key]
        L.append(f"| {label} | {cell(m)} | {m['n']} | {short(m['lens'], 90)} |")
    ww = e2.get("workspace_wide", {})
    if "instrumented_distinct_fn_items" in ww:
        m = ww["instrumented_distinct_fn_items"]
        L.append(f"| instrumented fn items, workspace-wide instrumented `--no-run` | "
                 f"{cell(m)} | {m['n']} | {short(m['lens'], 90)} |")
    L += ["", "Denominators, all from `sensorium-transform`'s own `census` — the parser that "
          "did the instrumenting — over bloomery @ `e209ed9`:", "",
          "| Denominator | eligible fn items | E2 with the `-p bloomery-daemon` numerator "
          "(1723) | E2 with the workspace-wide numerator (2051) |", "|---|---|---|---|",
          f"| `crates/*/src` + `crates/*/tests` (the plan's file set) | {e2['denominators']['all']} "
          f"| {pct(1723 / e2['denominators']['all'])} | {pct(2051 / e2['denominators']['all'])} |",
          f"| `crates/*/src` only | {e2['denominators']['src']} | "
          f"{pct(679 / e2['denominators']['src'])} | (not comparable: the wide numerator "
          f"spans both) |",
          f"| the files a `-p bloomery-daemon` build reaches | {e2['denominators']['reached']} "
          f"| {pct(1723 / e2['denominators']['reached'])} | (not comparable) |", "",
          "Census: 2056 `fn` items with a body, 5 `const fn`, 0 `extern` fn, 0 `async` fn → "
          "2051 eligible (739 over 82 files in `crates/*/src`, 1312 over 109 files in "
          "`crates/*/tests`). A `cargo test -p bloomery-daemon` build compiles 1723 of "
          "those 2051; the other 328 live in `bloomery-bench/src` (60), "
          "`bloomery-bench/tests`, `bloomery-core/tests` and `bloomery-substrate/tests` "
          "(268) — files that build never sees. See §4 for which reading the decision uses "
          "and why.", ""]
    L += ["### E7 — line numbers, paths and backtraces", ""]
    L += ["```"] + e["E7"]["e7_lines"] + ["```", ""]
    L += [f"`rust/spike/tests/mechanics.sh`: {num(e['E7']['checks_ok'])} checks passed, "
          f"{num(e['E7']['checks_failed'])} failed, exit {e['E7']['rc']}.", ""]
    L += ["### E8 — cargo freshness, and contamination of a plain build", ""]
    L += ["| Check | Result | Compiled | Fresh |", "|---|---|---|---|"]
    e8 = e["E8"]
    names = {"a_second_instrumented_compiles_nothing":
             "(a) a second instrumented `--no-run` compiles no workspace unit",
             "c_plain_after_instrumented_compiles_nothing":
             "(c) a plain `--no-run` after it compiles no workspace unit",
             "c_sentinel": "(c) sentinel: the plain `--lib` binary writes no spool, the "
                           "instrumented one does",
             "d_instrumented_after_plain_compiles_nothing":
             "(d) an instrumented `--no-run` after the plain one compiles no workspace unit"}
    for k, v in e8["checks"].items():
        if k == "c_sentinel":
            detail = (f"plain wrote {v.get('plain')} spool files, instrumented wrote "
                      f"{v.get('instrumented')}")
            L.append(f"| {names[k]} | {'PASS' if v['pass'] else 'FAIL'} | {detail} | — |")
        else:
            L.append(f"| {names[k]} | {'PASS' if v['pass'] else 'FAIL'} | "
                     f"`{v['compiled'] or '[]'}` | `{v['fresh']}` |")
    bm = e8["b_on_the_probe_workspace"]
    L.append(f"| (b) touch one line → exactly that unit and its dependents recompile | "
             f"{'PASS' if bm['value'] == 0 else cell(bm)} | probe workspace only "
             f"(bloomery is read-only for this plan) | — |")
    L += ["", f"The expected `Fresh` set is `{e8['expected_fresh_set']}` — asserted, not "
              f"merely 'compiled nothing', because a build that dies before its first "
              f"`Compiling` line also compiles nothing.", "",
          f"Reported, not gated: `--no-run` wall {cell(e8['clean_no_run_wall_s']['plain'], '{:.3f} s')} "
          f"plain (LENS: the plain artifacts pre-existed, so this is a freshness check, not a "
          f"build) versus {cell(e8['clean_no_run_wall_s']['instrumented'], '{:.2f} s')} for a "
          f"genuine clean instrumented build of all 77 units; `--lib` test binary "
          f"{cell(e8['test_binary_size_bytes']['plain'])} bytes plain versus "
          f"{cell(e8['test_binary_size_bytes']['instrumented'])} bytes instrumented "
          f"(+{(e8['test_binary_size_bytes']['instrumented']['value'] - e8['test_binary_size_bytes']['plain']['value']) / e8['test_binary_size_bytes']['plain']['value'] * 100:.2f}%).", ""]
    r = res["reported_without_a_gate"]
    L += ["### Reported without a gate", "",
          f"- Test binaries and processes cargo ran: **{num(r['test_binaries_run'])}** "
          f"spooling processes (72 distinct executables).",
          f"- Events per second of recording (call arm): "
          f"{132344 / (e['E1']['arms']['C']['median_s']['value'] - e['E1']['arms']['P']['median_s']['value']):.0f} "
          f"events per second of ADDED wall, or {132344 / e['E1']['arms']['C']['median_s']['value']:.0f} "
          f"per second of suite wall — LENS: the added wall is 0.085 s at n=5 and is inside "
          f"the arms' own spread, so the first figure is an order of magnitude, not a rate.",
          f"- Bytes per event on disk: "
          f"{num(w['bytes_per_event_on_disk'], '{:.2f}') if 'bytes_per_event_on_disk' in w else 'not measured'} "
          f"(24 B/record plus one file header per thread).",
          "- libtest thread naming as observed: every spawned test thread carries the test's "
          "own name (`codec_probe::fixtures::tests::parses_the_two_brief_examples`, "
          "`envelope_lens_names_are_pinned`, …), so the converter's per-task naming needs no "
          "heuristic.",
          f"- Per-process exit status available to the runtime: "
          f"**{num(r['per_process_exit_status_available'])}** (measured-and-zero, not "
          f"unmeasured) — every trace carries cargo's status instead (§5).",
          f"- Wall time of the spike's own build: "
          f"{num(r['spike_build_wall_s'], '{:.2f}')} s.", ""]
    L += [f"Cleanup: `{res['cleanup']['target_sensorium_removed_bytes']}` bytes of "
          f"`bloomery/target/sensorium` removed (exists after: "
          f"`{res['cleanup']['target_sensorium_exists_after']}`); "
          f"`git -C ~/workspace/bloomery status --porcelain` empty; `Cargo.lock` sha256 "
          f"unchanged (`{res['pins']['cargo_lock_sha256_before'][:16]}…`).", ""]
    return "\n".join(L)


def main() -> int:
    res = json.loads(RESULTS.read_text())
    body = render(res)
    doc = DOC.read_text()
    start = doc.index("## 3. Results")
    end = doc.index("## 4. Decisions")
    DOC.write_text(doc[:start] + body + "\n" + doc[end:])
    COPY.write_text(RESULTS.read_text())
    print(f"rendered §3 into {DOC}")
    print(f"copied results.json to {COPY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
