#!/usr/bin/env python3
"""`2026-09-05-sensorium-rung3-e6ppp.results.json` -> §2 and §3.

Reached through `render_acceptance.py --doc e6ppp`; a module of its own for
the reason `render_rung3.py` is one -- neither file may pass the repo's
800-line ceiling. The renderer's one rule is that file's: a `null` value
prints as `not measured (<reason>)` and never as a dash, a zero or an empty
cell; `0` is a measured zero.

§4 and §5 are never rendered. They are the verdicts and the gaps, written by
hand against §1's rules and the raw record -- and the adjudication of every
SWALLOWED line against the clone's source is a reading no renderer can do.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_acceptance import (cell, dropped_of, lens_of, n_of,       # noqa: E402
                               row)

HEAD = ["| Measurement | Value | n | Lens (abridged; the full lens is in "
        "`results.json`) | Dropped |", "|---|---|---|---|---|"]


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def environment(r) -> list[str]:
    env, bl = r["environment"], r.get("byte_lock") or {}
    name = Path(r["acceptance"]).with_suffix("").name
    out = ["## 2. Environment", "",
           f"Measured {r.get('started')} → {r.get('finished')} by "
           f"`{r.get('runner')}`, launched detached; the raw facts it "
           f"recorded are `results-e6ppp-raw.json` in the gitignored plan "
           f"ledger, with every command's log beside it. §3 below is rendered "
           f"from `{name}.results.json`, which "
           f"`acceptance_schema_e6ppp.assemble_e6ppp` derived from that raw "
           f"file.", "",
           f"**§1 byte-lock.** The runner refuses to start unless the locked "
           f"range is byte-identical to the commit that locked it. The range "
           f"is {bl.get('range')} — here §1 references no footnote "
           f"(`footnotes_in_range` = "
           f"{bl.get('footnotes_in_range') or 'none'}), so the extended range "
           f"and `{bl.get('extraction')}` are the same bytes. Checked at "
           f"`{bl.get('commit')}`: {bl.get('locked_bytes')} bytes, sha256 "
           f"`{bl.get('locked_sha256')}` on both sides — identical: "
           f"{_yn(bl.get('identical'))}. The ORIGINAL lock is "
           f"`{bl.get('original_lock')}` (sha256 "
           f"`{bl.get('original_lock_sha256')}`, "
           f"{bl.get('original_lock_bytes')} bytes); §1 was amended after it: "
           f"{_yn(bl.get('amended_after_the_original_lock'))} "
           f"({bl.get('amendment_bytes')} bytes added — the dated "
           f"pre-measurement note inside \"Reported without a gate\").", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("driver",
         f"`{env.get('driver')}`, mtime {env.get('driver_mtime')}"),
        ("driver sha256",
         f"`{env.get('driver_sha256')}` — unchanged across the run: "
         f"{_yn(env.get('driver_unchanged_after'))}"),
        ("census driver",
         f"`{env.get('census_driver')}` (sha256 "
         f"`{env.get('census_driver_sha256')}`)"),
        ("toolchain", f"{env.get('rustc')} / {env.get('cargo')}"),
        ("reader",
         f"{env.get('python')}, sensorium {env.get('sensorium_version')}"),
        ("machine",
         f"{env.get('nproc')} cpus, governor `{env.get('governor')}`"),
        ("clone (the workspace under measurement)",
         f"`{env.get('clone')}` at `{env.get('clone_head')}`"),
        ("clone porcelain before / after",
         f"{'empty' if not env.get('clone_porcelain_before') else 'DIRTY'} / "
         f"{'empty' if not env.get('clone_porcelain_after') else 'DIRTY'}; "
         f"restored to the pin: {_yn(env.get('clone_restored'))}; "
         f"`Cargo.lock` unchanged: "
         f"{_yn(env.get('cargo_lock_unchanged'))}"),
        ("target (**emptied by the prep build**, which then left it warm for "
         "both measured arms)",
         f"`{env.get('target_dir')}` — "
         f"{env.get('target_emptied_by_prep_bytes')} bytes removed"),
        ("corpus target (E6-again) — FRESH for this run",
         f"`{env.get('corpus_target')}`, "
         f"{env.get('corpus_target_bytes_before')} bytes at the start"),
        ("probe target (E7‴)", f"`{env.get('probe_target')}`"),
        ("trace store (new and empty at the start)",
         f"`{env.get('sensorium_dir')}`; per arm "
         + ", ".join(f"{k} `{v}`" for k, v in
                     (env.get("sensorium_dir_per_arm") or {}).items())),
        ("`~/workspace/bloomery` (READ-ONLY)",
         f"`{env.get('source_bloomery')}` at "
         f"`{env.get('source_bloomery_head_before')}` → "
         f"`{env.get('source_bloomery_head_after')}`; porcelain "
         f"{'empty' if not env.get('source_bloomery_porcelain_before') else 'DIRTY'}"
         f" → "
         f"{'empty' if not env.get('source_bloomery_porcelain_after') else 'DIRTY'}"
         f"; unchanged: {_yn(env.get('source_bloomery_unchanged'))}"),
        ("driver `built_from` (recorded by the runner)",
         (f"HEAD `{(env.get('built_from') or {}).get('repo_head_at_build')}`, "
          f"`cargo build --release` exit "
          f"{(env.get('built_from') or {}).get('cargo_rc')}, rebuilt: "
          f"{_yn((env.get('built_from') or {}).get('rebuilt'))}")
         if not (env.get("built_from") or {}).get("dropped") else
         "not measured (" + "; ".join((env.get("built_from") or {})
                                      .get("dropped") or []) + ")"),
        ("1-minute load at the start", f"{env.get('load_1min_at_start')}"),
        ("disk free on the target's filesystem, before / after",
         f"{env.get('target_disk_free_gb')} GB / "
         f"{env.get('target_disk_free_gb_after')} GB"),
        ("§1's frozen census (Task 10, before the lock)",
         ", ".join(f"{k} {v}" for k, v in
                   (env.get("frozen_census") or {}).items())),
    ]
    out += ["| Pin | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in pins]
    out += log_locations(r)
    loads = env.get("load_at_each_arm") or []
    out += ["", "1-minute load at each arm's start: "
            + ", ".join(f"{a.get('arm')} {a.get('load_1min')}"
                        for a in loads) + "."]
    return out


def log_locations(r) -> list[str]:
    """Where this run's logs actually landed.

    Derived, never asserted: the prep build's log path is compared with the
    document's own logs directory, both read from the record. A log outside
    that directory is stated with the date the run finished, because the
    reader's next move is to go and find it."""
    env = r["environment"]
    logs, prep = env.get("logs_dir"), env.get("prep_build_log")
    out = ["", f"**Log locations.** Every command's log is under `{logs}`, "
                "one subdirectory per phase (`built-from`, `prep`, `arm-a`, "
                "`arm-w`, `e6-again`, `e7ppp`)."]
    if prep and logs and not str(prep).startswith(str(logs)):
        date = (r.get("finished") or "")[:10]
        out[-1] += (
            f" **One exception, recorded {date}, after the run:** the prep "
            f"build's own log went to `{prep}` — the rung-3 slice's log "
            f"directory, not this document's. `acceptance_rung3`'s module "
            f"body re-points `acceptance_lib.LOGS` when it is imported, and "
            f"the prep phase ran outside a `logs_at` block, so it inherited "
            f"that pointer. Nothing was clobbered (the rung-3 run writes no "
            f"file of that name) and no measured number depends on it; the "
            f"runner now re-asserts the pointer after the import AND wraps "
            f"the phase, so a later run logs beside its own document.")
    return out + [""]


def _arm(r, key, title) -> list[str]:
    e = r["endpoints"][key]
    out = [f"### {title}", ""] + HEAD
    for label, k in (("SWALLOWED lines on the primary process "
                      "(each adjudicated in §4)", "swallowed_lines"),
                     ("SWALLOWED lines over EVERY process (primary + sweep)",
                      "union_swallowed_lines"),
                     ("SWALLOWED lines the sweep added", "sweep_swallowed_lines"),
                     ("SWALLOWED lines the collector could not parse",
                      "unparsed_swallowed_lines"),
                     ("guarded arms (R15; restates §5.2, not a new "
                      "measurement)", "guarded_arms"),
                     ("Err chains judged on the primary (`raised (N):`)",
                      "chains_in_scope"),
                     ("processes recorded", "processes"),
                     ("false accusations", "headline")):
        out.append(row(label, e.get(k)))
    out += ["",
            f"Selector: `{' '.join(e.get('selector') or [])} --lib`  ",
            f"Primary tally line: `{e.get('tally_line')}`  ",
            f"Header `partial:` line: `{e.get('partial_line')}`  ",
            f"Header `panics:` line: `{e.get('panics_line')}`  ",
            f"Paging note (`... N more`): `{e.get('more_note')}`  ",
            f"Primary run `{e.get('run')}`, {e.get('events')} events, "
            f"recorded in {e.get('wall_s')} s; `exceptions` answered in "
            f"{e.get('exceptions_wall_s')} s (exit "
            f"{e.get('exceptions_rc')}).", ""]
    lines = list(e.get("swallowed") or []) + list(e.get("swallowed_sweep") or [])
    if not lines:
        out += ["No SWALLOWED line was printed by any process of this arm.", ""]
        return out
    out += ["Every SWALLOWED line, with the sink the trace names for it "
            "(the adjudication itself is §4):", "",
            "| # | how | sink | line |", "|---|---|---|---|"]
    for i, p in enumerate(lines, 1):
        s = p.get("sink") or {}
        where = (f"`{s.get('file')}:{s.get('line')}` "
                 f"(`{s.get('qualname')}` L{s.get('line')})"
                 if s else "not resolved")
        out.append(f"| {i} | `{p.get('how')}` | {where} | "
                   f"`{p.get('line')}` |")
    return out


def _e6again(r) -> list[str]:
    """E6-again is §1's E6 row verbatim, so its table is the COMMITTED rung-3
    renderer, called over a shim whose `E6` key is this document's `E6again`
    block. Only the heading differs, and it is rewritten rather than
    re-typed."""
    from render_rung3 import _e6 as rung3_e6                       # noqa: PLC0415
    out = rung3_e6({"endpoints": {"E6": r["endpoints"]["E6again"]}})
    out[0] = "### E6-again — the Rust corpus, every `exceptions` question"
    return out


def _e7ppp(r) -> list[str]:
    e = r["endpoints"]["E7ppp"]
    loc = e.get("operand_locations") or {}
    out = ["### E7‴ — panic locations under the wraps", ""] + HEAD
    for label, k in (("failed E7 checks on the probe's existing panics",
                      "headline"),
                     ("E7 checks that passed", "existing_checks_passed"),
                     ("`?`-operand panic: column shift, tier `call`",
                      "operand_column_shift"),
                     ("the same, tier `off`", "operand_column_shift_off"),
                     ("`?`-operand panic: line identical (1 = yes)",
                      "operand_line_identical")):
        out.append(row(label, e.get(k)))
    out += ["",
            f"Locations: plain `{(loc.get('plain') or {}).get('file')}:"
            f"{(loc.get('plain') or {}).get('line')}:"
            f"{(loc.get('plain') or {}).get('col')}`, tier `off` "
            f"`{(loc.get('off') or {}).get('line')}:"
            f"{(loc.get('off') or {}).get('col')}`, tier `call` "
            f"`{(loc.get('call') or {}).get('line')}:"
            f"{(loc.get('call') or {}).get('col')}`; §1 predicted a shift of "
            f"{e.get('operand_predicted_shift')}.  ",
            f"`mechanics.sh`: exit {e.get('mechanics_rc')}, "
            f"{e.get('mechanics_ok')} ok, {len(e.get('mechanics_fail') or [])} "
            f"FAIL, {len(e.get('mechanics_skip') or [])} skip; driver sha "
            f"unchanged across it: {_yn(e.get('driver_unchanged'))}."]
    return out


def _reported(r) -> list[str]:
    rep = r.get("reported") or {}
    disp, blast = rep.get("dispositions") or {}, rep.get("blast_radius") or {}
    prep = rep.get("prep_build") or {}
    out = ["### Reported without a gate", "",
           "**Per-disposition tallies, both arms side by side.**", "",
           "| Arm | processes | primary `dispositions:` line | all processes "
           "summed |", "|---|---|---|---|"]
    for label, d in disp.items():
        out.append(f"| {label} | {d.get('processes')} | "
                   f"`{d.get('primary_tally_line')}` | "
                   f"{d.get('all_processes_tally')} |")
    out += ["", "**The blast radius: static, and executed.**", ""] + HEAD
    for label, k in (("entries in the reviewer's static list",
                      "static_entries_total"),
                     ("of them, carrying a line (intersectable)",
                      "static_entries_located"),
                     ("of them, named only by file pattern",
                      "static_entries_unlocated"),
                     ("located entries that resolve to an arm site",
                      "resolved_to_an_arm_site"),
                     ("of those, reading `arm_ambiguous` now",
                      "reading_arm_ambiguous_now"),
                     ("EXECUTED by E6‴-A", "executed_a"),
                     ("EXECUTED by E6‴-W", "executed_w"),
                     ("arm sites that fired at all, E6‴-A",
                      "executed_arm_sites_all_a"),
                     ("arm sites that fired at all, E6‴-W",
                      "executed_arm_sites_all_w")):
        out.append(row(label, blast.get(k)))
    out += ["",
            f"Unresolved static entries: {blast.get('unmatched')}.  ",
            f"Suffixes matching more than one file with an arm at that line: "
            f"{blast.get('ambiguous_suffixes')}.  ",
            f"§1's frozen census (cited, not re-derived): "
            f"{blast.get('frozen_census')}.", "",
            "**The prep build** (from-scratch `--workspace --no-run`, which "
            "emptied the target so every unit was compiled by this driver and "
            "the manifest set is complete):", ""] + HEAD
    out.append(row("distinct `kind: \"arm\"` manifest rows",
                   prep.get("arm_sites_distinct")))
    out += ["",
            f"exit {prep.get('rc')} in {prep.get('wall_s')} s over "
            f"{prep.get('units')} unit(s); arm rows by `how`: "
            f"{prep.get('arm_sites_by_how')}; raw rows "
            f"{prep.get('arm_sites_raw')}."]
    return out


def results(r) -> list[str]:
    e = r["endpoints"]
    rules = {
        "E6‴-A": "0 false accusations on the clone's `-p bloomery-daemon "
                 "--lib` suite",
        "E6‴-W": "0 false accusations on the clone's `--workspace --lib` "
                 "suite",
        "E6-again": "printed SWALLOWED lines == the registered set for every "
                    "case; any extra = a false accusation = STOP",
        "E7‴": "existing checks: 0 differences; new check: line identical, "
               "column = original + 6",
    }
    keys = {"E6‴-A": "E6pppA", "E6‴-W": "E6pppW", "E6-again": "E6again",
            "E7‴": "E7ppp"}
    name = Path(r["acceptance"]).with_suffix("").name
    out = ["## 3. Results", "",
           "Every measurement is `{value, n, lens, dropped}`; a `null` value "
           "with a reason is the ONLY not-measured, and `0` is "
           "measured-and-zero. Rendered by "
           "`rust/tests/render_acceptance.py --doc e6ppp` from "
           f"`{name}.results.json`. No verdict is decided here — §4 is.", "",
           "| Id | Headline | n | Lens (abridged) | Dropped |",
           "|---|---|---|---|---|"]
    for label, key in keys.items():
        m = e[key]["headline"]
        out.append(f"| {label} | {cell(m)} (rule: {rules[label]}) | "
                   f"{n_of(m)} | {lens_of(m)} | {dropped_of(m)} |")
    out += [""] + _arm(r, "E6pppA",
                       "E6‴-A — the clone's `-p bloomery-daemon --lib` suite")
    out += [""] + _arm(r, "E6pppW",
                       "E6‴-W — the clone's `--workspace --lib` suite")
    out += [""] + _e6again(r)
    out += [""] + _e7ppp(r)
    out += [""] + _reported(r)
    return out


def document(argv) -> int:
    import json                                                    # noqa: PLC0415
    default = (Path(__file__).resolve().parents[2] / "docs" / "superpowers"
               / "acceptance"
               / "2026-09-05-sensorium-rung3-e6ppp.results.json")
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else default
    r = json.loads(path.read_text())
    print("\n".join(environment(r) + [""] + results(r)))
    return 0


if __name__ == "__main__":
    raise SystemExit(document(sys.argv[1:]))
