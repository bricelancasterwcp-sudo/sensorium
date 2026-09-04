#!/usr/bin/env python3
"""`results.json` -> the rendered sections of an acceptance document.

The renderer's one rule: a `null` value is printed as
`not measured (<reason>)` and never as anything else -- not as a dash, not as
a zero, not as an empty cell. `0` is a measured zero and prints as `0`.

    # rung-2 acceptance, §3 (the original mode, unchanged)
    .venv/bin/python rust/tests/render_acceptance.py [results.json] > section3.md

    # rung-3 entry, E5': §2 and §3
    .venv/bin/python rust/tests/render_acceptance.py --doc e5prime [results.json]

§4 is never rendered, and neither is E5''s §5. They are written by hand
against the pre-registered rules and the raw record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT = (REPO / ".superpowers" / "sdd"
           / "2026-09-02-sensorium-rung2-recorder-v1" / "acceptance" / "results.json")
LENS_CAP = 110


def _upper_first(text: str) -> str:
    """`text` with its first character upper-cased and the REST UNTOUCHED.

    `str.capitalize()` lower-cases everything after the first character, so a
    note naming `results-raw.json` or an endpoint like `E5` comes back mangled.
    """
    return text[:1].upper() + text[1:]


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
            ("exit_status_basis across the invocation",
             "exit_status_basis_histogram"),
            ("driver fixed cost (s)", "driver_fixed_cost_s"),
            ("runtime rlib build (s)", "runtime_rlib_build_s"),
            ("mean wall of one recorded --lib run (s)", "e3_run_wall_s")):
        out.append(row(label, rep.get(key)))

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


def addendum_section(r) -> list[str]:
    """The dated before/after block. Rendered last inside §3 and never mixed
    into a table above it: the 46074ef columns are the measurement, the second
    column is a later reading of the reported items only."""
    a = r.get("addendum")
    if not a:
        return []
    m = a["measured_with"]
    short = (m.get("commit") or "")[:7]
    date = (m.get("started") or "")[:10]
    out = [f"### 3.1 Addendum — reported items re-measured after the converter fix "
           f"(commit `{short}`, {date})", "",
           f"**Nothing gated is re-measured here.** The five verdicts of §4 and every "
           f"§3 cell they rest on are the numbers the acceptance run recorded at "
           f"`46074ef`, and they stand. What changed since: {m.get('why')}. "
           f"Measured with the release driver built from "
           f"`{m.get('commit')}`, sha256 `{m.get('driver_sha256')}`, "
           f"{m.get('started')} → {m.get('finished')}, clone at "
           f"`{(m.get('clone_head') or '')[:12]}`, 1-minute load "
           f"{m.get('load_1min_at_start')} at the start.", "",
           "| Item | at `46074ef` | at " + f"`{short}`" + " | n | Lens of the re-measurement |",
           "|---|---|---|---|---|"]
    for row in a["rows"]:
        b, af = row.get("before"), row["after"]
        out.append(f"| {row['item']} | {cell(b)} | {cell(af)} | {n_of(af)} | "
                   f"{lens_of(af)} |")
    w = a.get("walls") or {}
    if w.get("P", {}).get("walls"):
        out += ["", "| Round | P (plain) | C (call) | load at P | load at C |",
                "|---|---|---|---|---|"]
        runs = w.get("runs") or []
        for rnd in sorted({x["round"] for x in runs}):
            pr = next((x for x in runs if x["round"] == rnd and x["arm"] == "P"), {})
            cr = next((x for x in runs if x["round"] == rnd and x["arm"] == "C"), {})
            out.append(f"| {rnd} | {pr.get('wall')} s | {cr.get('wall')} s | "
                       f"{pr.get('load_1min')} | {cr.get('load_1min')} |")
        out.append(f"| **median** | {w['P']['median']} s | {w['C']['median']} s | — | — |")
        out.append(f"| **min** | {w['P']['min']} s | {w['C']['min']} s | — | — |")
        out.append(f"| **max** | {w['P']['max']} s | {w['C']['max']} s | — | — |")
    return out


def rung2_document(argv) -> int:
    """§3 of the rung-2 acceptance document — the original mode."""
    path = Path(argv[0]) if argv else DEFAULT
    r = json.loads(path.read_text())
    lines = ["## 3. Results", ""]
    if r.get("dry_run"):
        lines += ["**DRY RUN — no acceptance number was measured.** Every endpoint "
                  "cell below reads `not measured (dry run …)`; what this proves is "
                  "that every step runs and every artifact is written.", ""]
    a = r.get("assembled")
    if a:
        lines += [f"**Provenance of this section.** It is rendered by "
                  f"`rust/tests/render_acceptance.py` from "
                  f"`results.json`, which was assembled at {a['at']} by "
                  f"`{a['by']}` from `{a['from']}` — the raw facts the run itself "
                  f"recorded — under the committed schema. {_upper_first(a['note'])}. "
                  f"The committed `…acceptance.results.json` is that assembly, byte "
                  f"for byte.", ""]
    lines += [f"Measured on the §2 pins. Runner: `rust/tests/acceptance.py` "
              f"(raw logs and `results-raw.json` in the gitignored ledger). "
              f"Started {r.get('started')}, finished {r.get('finished')}. "
              "Every cell below is a number with its `n` and its lens, or "
              "`not measured (<reason>)`.", ""]
    lines += headline(r) + [""]
    for section in (e2_section, e3_section, e5_section, e7_section, e8_section,
                    reported_section, addendum_section):
        rendered = section(r)
        if rendered:
            lines += rendered + [""]
    print("\n".join(lines))
    return 0


# --------------------------------------------------------------- E5' (rung 3)

E5PRIME_DEFAULT = (REPO / "docs" / "superpowers" / "acceptance"
                   / "2026-09-03-sensorium-rung3-entry-e5prime.results.json")


def _yn(v) -> str:
    return "not measured" if v is None else ("yes" if v else "NO")


def e5prime_environment(r) -> list[str]:
    """§2 of the E5' document: what was measured, with what, on what."""
    e = r["environment"]
    bl = r.get("byte_lock") or {}
    loads = e.get("load_at_each_arm") or []
    out = ["## 2. Environment", "",
           f"Measured {r.get('started')} → {r.get('finished')} by "
           f"`{r.get('runner')}`, launched detached; the raw facts it recorded "
           f"are `results-e5prime-raw.json` in the gitignored plan ledger, with "
           f"every command's log beside it. §3 below is rendered from "
           f"`{Path(r['acceptance']).name.replace('.md', '.results.json')}`, "
           f"which `acceptance_schema.assemble_e5prime` derived from that raw "
           f"file.", "",
           f"**§1 byte-lock.** The runner refuses to start unless §1 is "
           f"byte-identical to the commit that locked it. Checked at "
           f"`{bl.get('commit')}` with `{bl.get('extraction')}`: "
           f"{bl.get('locked_bytes')} bytes, sha256 "
           f"`{bl.get('locked_sha256')}` on both sides — "
           f"identical: {_yn(bl.get('identical'))}.", "",
           "| Pin | Value |", "|---|---|",
           f"| driver commit | `{e.get('repo_commit')}` "
           f"(branch `{e.get('repo_branch')}`) |",
           f"| driver | `{e.get('driver')}`, built `--release` from that commit "
           f"at {e.get('driver_mtime')} |",
           f"| driver sha256 | `{e.get('driver_sha256')}` — unchanged across the "
           f"run: {_yn(e.get('driver_unchanged_after'))} |",
           f"| toolchain | {e.get('rustc')} / {e.get('cargo')} |",
           f"| reader | {e.get('python')}, sensorium {e.get('sensorium_version')} |",
           f"| machine | {e.get('nproc')} cpus, governor `{e.get('governor')}` |",
           f"| clone (the workspace under measurement) | `{e.get('clone')}` at "
           f"`{e.get('clone_head')}` |",
           f"| arm A | `{(e.get('arm_tips') or {}).get('A')}` |",
           f"| arm B (`e5-split`) | `{(e.get('arm_tips') or {}).get('B')}` |",
           f"| arm C (`e5-planted`) | `{(e.get('arm_tips') or {}).get('C')}` |",
           f"| clone porcelain before / after | "
           f"{'empty' if not (e.get('clone_porcelain_before') or '').strip() else 'NOT EMPTY'}"
           f" / "
           f"{'empty' if not (e.get('clone_porcelain_after') or '').strip() else 'NOT EMPTY'}"
           f"; restored to arm A detached: {_yn(e.get('clone_restored'))}; "
           f"`Cargo.lock` unchanged: {_yn(e.get('cargo_lock_unchanged'))} |",
           f"| target (lens: **WARM** — the rung-2 acceptance target, only the "
           f"driver changed) | `{e.get('target_dir')}` |",
           f"| manifests cleared before arm A | "
           f"{e.get('manifests_cleared_before_arm_a')} stale manifests "
           f"({e.get('manifests_cleared_bytes')} bytes), so every `fell_back` "
           f"counted in §3 belongs to this invocation |",
           f"| traces | `{e.get('sensorium_dir')}` — new and empty at the "
           f"preflight, refused otherwise |",
           f"| 1-minute load at the start | {e.get('load_1min_at_start')} |",
           f"| free disk at the start | {e.get('target_disk_free_gb')} GB "
           f"(target) / {e.get('repo_disk_free_gb')} GB (repo) |"]
    if loads:
        out += ["", "The 1-minute load read at each arm's own first act (the "
                "`git checkout` that puts the arm's tree in place):", "",
                "| Arm ref | At | 1-minute load |", "|---|---|---|"]
        for x in loads:
            out.append(f"| `{x['ref']}` | {x['at']} | {x['load_1min']} |")
    out += ["", f"**`{e.get('source_bloomery')}` was never checked out.** Its "
            f"HEAD and porcelain were read before and after: "
            f"`{(e.get('source_bloomery_head_before') or '')[:12]}` / "
            f"{'empty' if not (e.get('source_bloomery_porcelain_before') or '').strip() else 'NOT EMPTY'}"
            f" before, "
            f"`{(e.get('source_bloomery_head_after') or '')[:12]}` / "
            f"{'empty' if not (e.get('source_bloomery_porcelain_after') or '').strip() else 'NOT EMPTY'}"
            f" after — unchanged: {_yn(e.get('source_bloomery_unchanged'))}."]
    u = e.get("unused_env") or {}
    if u:
        out += ["", f"Two environment variables the shared preflight requires "
                f"belong to phases this runner does not call and were not read: "
                f"`SENSORIUM_CENSUS_DRIVER`, `SENSORIUM_PROBE_TARGET`."]
    return out


def e5prime_results(r) -> list[str]:
    """§3 of the E5' document: one row per §1 condition, with n and lens."""
    m, nm, cov = (r["endpoints"]["E5prime"], r["endpoints"]["E5prime_names"],
                  r["endpoints"]["E5prime_coverage"])
    rep = r.get("reported") or {}
    arms = m.get("arms") or {}
    out = ["## 3. Results", "",
           f"Rendered by `rust/tests/render_acceptance.py --doc e5prime` from "
           f"`{Path(r['acceptance']).name.replace('.md', '.results.json')}`. "
           f"Every cell is a number with its `n` and its lens, or "
           f"`not measured (<reason>)`; `0` is a measured zero.", "",
           "| Id | Value | n | Lens (abridged; the full lens is in the "
           "`results.json`) | Dropped |", "|---|---|---|---|---|"]
    for label, e, rule in (
            ("E5′", m["headline"],
             "A/B MATCH-class with ≥1 moved, 0 added, 0 removed, all ten task "
             "streams paired; A/C DIVERGED inside the swapped fn"),
            ("E5′-names", nm["headline"],
             "BOTH conjuncts — every spawn@ name exactly the predicted string "
             "on A and on B, AND A's multiset of (name, hash) equal to B's"),
            ("E5′-coverage", cov["headline"], "0 units fell back")):
        out.append(f"| {label} | {cell(e)} (rule: {rule}) | {n_of(e)} | "
                   f"{lens_of(e)} | {dropped_of(e)} |")

    out += ["", "### The three arms", "",
            "| Arm | Tree | run | events | threads | tests | run wall (s) |",
            "|---|---|---|---|---|---|---|"]
    for k in ("A", "B", "C"):
        a = arms.get(k) or {}
        out.append(f"| {k} | `{a.get('head')}` | `{a.get('run')}` | "
                   f"{a.get('events')} | {a.get('threads')} | "
                   f"{len(a.get('tests') or [])} | {a.get('wall')} |")
    out += ["", "The wall is reported without a gate: nothing pre-registered "
            "rests on it."]

    out += ["", "### E5′ — does `diff --ignore-moves` verify the split now?", "",
            "| Pre-registered condition | Met |", "|---|---|"]
    for k, v in (m.get("conditions") or {}).items():
        out.append(f"| `{k}` | {_yn(v)} |")
    out += ["", "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|",
            row("E5′ conditions not met", m.get("headline")),
            row("code objects paired across a move (A/B)", m.get("ab_moved")),
            row("task streams on each side (A/B)", m.get("ab_tasks_each_side")),
            "", f"**How the A/B verdict line is read.** {m.get('ab_reading')}"]

    out += ["", "### E5′-names — the four children's names, and their hashes", "",
            "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|",
            row("§1 conjuncts missed, of 2", nm.get("headline")),
            row("spawn@ names equal to the predicted string",
                nm.get("names_as_predicted")),
            row("spawn@ names NOT the predicted string",
                nm.get("names_not_as_predicted")),
            row("spawn@ task streams on arm A", nm.get("spawn_tasks_a")),
            row("spawn@ task streams on arm B", nm.get("spawn_tasks_b")),
            row("(name, hash) pairs whose STORED hash differs, A vs B",
                nm.get("stored_hash_pairs_differing")),
            "",
            "| §1 conjunct | Met |", "|---|---|"] + [
                f"| `{k}` | {_yn(v)} |"
                for k, v in (nm.get("conjuncts") or {}).items()] + [
            "",
            f"Predicted string: `{nm.get('predicted_shape')}`. The stored "
            f"multiset of (name, hash) pairs on A equals B's: "
            f"{_yn(nm.get('stored_multiset_equal'))}. What the differ itself "
            f"says about the same pairs, verbatim from the A/B "
            f"`--ignore-moves` run:", "",
            "```", str(nm.get("differ_tasks_line")), "```", "",
            "The four `spawn@` streams on each side, verbatim, with the stored "
            "`task_fingerprints.hash`:", "",
            "| Side | Task name | Stored hash |", "|---|---|---|"]
    for side, key in (("A", "a_multiset"), ("B", "b_multiset")):
        for name, h in (nm.get(key) or []):
            out.append(f"| {side} | `{name}` | `{h}` |")

    out += ["", "### E5′-coverage — did the transformer instrument every unit?",
            "", "| Quantity | Value | n | Lens | Dropped |", "|---|---|---|---|---|",
            row("units that fell back to the real tree", cov.get("units_fell_back")),
            "", "| Arm | unit manifests read | written by this arm | fell back | "
            "spawn sites wrapped | spawn sites declared, not wrapped | unreached "
            "files |", "|---|---|---|---|---|---|---|"]
    for k in ("A", "B", "C"):
        out.append(
            f"| {k} | {(cov.get('units_seen_per_arm') or {}).get(k)} | "
            f"{len([u for u in (cov.get('units') or {}).get(k, []) if u['written_during_this_arm']])} | "
            f"{(cov.get('per_arm_fell_back') or {}).get(k)} | "
            f"{(cov.get('spawn_sites_wrapped_per_arm') or {}).get(k)} | "
            f"{(cov.get('spawn_sites_declared_unwrapped_per_arm') or {}).get(k)} | "
            f"{len((cov.get('unreached_files_per_arm') or {}).get(k) or [])} |")
    out += ["", "| Arm | crate | type | fell back | files | sites | spawn sites | "
            "compiled by this arm |", "|---|---|---|---|---|---|---|---|"]
    for k in ("A", "B", "C"):
        for u in (cov.get("units") or {}).get(k, []):
            out.append(f"| {k} | `{u['crate_name']}` | {u['crate_type']} | "
                       f"{'**YES**' if u['fell_back'] else 'no'} | {u['files']} | "
                       f"{u['sites']} | {u['spawns']} | "
                       f"{'yes' if u['written_during_this_arm'] else 'no'} |")
    rr = cov.get("unreached_reasons") or {}
    out += ["", f"`unreached_reasons` (the manifest key a refusal on real code "
            f"would show up in) was empty on every unit of every arm: "
            f"{'no reason recorded on any unit' if not rr else rr}."]

    out += ["", "### The four diffs, verbatim", ""]
    for label, key in (("A/B `--ignore-moves` — the endpoint", "ab_ignore_moves"),
                       ("A/C `--ignore-moves` — the negative control",
                        "ac_ignore_moves"),
                       ("A/B plain `diff` (reported without a gate)", "ab_plain"),
                       ("A/C, one task (reported without a gate)", "ac_task")):
        d = (m.get("diffs") or {}).get(key)
        if not d:
            continue
        out += [f"**{label}** — `sensorium {' '.join(d['argv'])}`, exit "
                f"{d.get('rc')}:", "", "```", d.get("stdout", "").rstrip(),
                "```", ""]
    return out


def e5prime_document(argv) -> int:
    """§2 and §3 of the rung-3-entry E5' document, from its own results.json.

    §4 and §5 are not rendered. They are written by hand against §1's rules
    and against the raw record."""
    path = Path(argv[0]) if argv else E5PRIME_DEFAULT
    r = json.loads(path.read_text())
    lines = e5prime_environment(r) + [""] + e5prime_results(r)
    print("\n".join(lines))
    return 0


def main(argv) -> int:
    """`--doc e5prime` renders the rung-3-entry E5' document; with no `--doc`
    the original rung-2 §3 is printed, unchanged.

        .venv/bin/python rust/tests/render_acceptance.py [results.json]
        .venv/bin/python rust/tests/render_acceptance.py --doc e5prime [results.json]
    """
    argv = list(argv)
    doc = "rung2"
    if "--doc" in argv:
        i = argv.index("--doc")
        doc = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    if doc == "e5prime":
        return e5prime_document(argv)
    if doc != "rung2":
        print(f"unknown --doc {doc!r}: expected `rung2` or `e5prime`",
              file=sys.stderr)
        return 2
    return rung2_document(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
