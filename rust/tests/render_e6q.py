#!/usr/bin/env python3
"""`2026-09-05-sensorium-rung3-e6q.results.json` -> §2 and §3.

Run directly (this commit does not touch `render_acceptance.py`, whose
`--doc` dispatch the earlier documents go through):

    .venv/bin/python rust/tests/render_e6q.py [results.json]

A module of its own for the reason `render_rung3.py` and `render_e6ppp.py`
are: neither file may pass the repo's 800-line ceiling. Its table helpers are
imported from `render_acceptance`, and E6-again′, E7⁗ and E0‴ are rendered by
the COMMITTED rung-3 renderer over this document's blocks -- a second table
would be free to disagree with the record that protocol already published.

The renderer's one rule is `render_acceptance`'s: a `null` value prints as
`not measured (<reason>)` and never as a dash, a zero or an empty cell; `0`
is a measured zero.

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

ARM_TITLES = {
    "E6qA": "E6⁗-A — the clone's `-p bloomery-daemon --lib` suite, HEAD driver",
    "E6qWS": "E6⁗-WS — the clone's `--workspace` suite (no `--lib`), HEAD "
             "driver",
    "E6qWS0": "E6⁗-WS0 — the same `--workspace` suite under the PRE-repair "
              "driver (the control)",
}


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def environment(r) -> list[str]:
    env, bl = r["environment"], r.get("byte_lock") or {}
    base = env.get("base_driver") or {}
    name = Path(r["acceptance"]).with_suffix("").name
    out = ["## 2. Environment", "",
           f"Measured {r.get('started')} → {r.get('finished')} by "
           f"`{r.get('runner')}`, launched detached; the raw facts it "
           f"recorded are `results-e6q-raw.json` in the gitignored plan "
           f"ledger, with every command's log beside it. §3 below is rendered "
           f"from `{name}.results.json`, which "
           f"`acceptance_schema_e6q.assemble_e6q` derived from that raw "
           f"file.", "",
           f"**§1 byte-lock.** The runner refuses to start unless the locked "
           f"range is byte-identical to the commit that locked it — and "
           f"refuses outright while no lock sha is set. The range is "
           f"{bl.get('range')} — here §1 references no footnote "
           f"(`footnotes_in_range` = "
           f"{bl.get('footnotes_in_range') or 'none'}), so the extended range "
           f"and `{bl.get('extraction')}` are the same bytes. Checked at "
           f"`{bl.get('commit')}`: {bl.get('locked_bytes')} bytes, sha256 "
           f"`{bl.get('locked_sha256')}` on both sides — identical: "
           f"{_yn(bl.get('identical'))}. §1 was committed ALONE and never "
           f"amended: there is no second sha "
           f"(`original_lock` = {bl.get('original_lock')}).", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("HEAD driver (E6⁗-A, E6⁗-WS)",
         f"`{env.get('driver')}`, mtime {env.get('driver_mtime')}"),
        ("HEAD driver sha256",
         f"`{env.get('driver_sha256')}` — unchanged across the run: "
         f"{_yn(env.get('driver_unchanged_after'))}"),
        ("BASE driver (E6⁗-WS0, the control)",
         f"`{base.get('driver')}` (sha256 `{base.get('driver_sha256')}`, "
         f"mtime {base.get('driver_mtime')}), built from worktree "
         f"`{base.get('worktree')}` at `{base.get('head')}` — expected "
         f"`{base.get('expected_commit')}`: {_yn(base.get('head_matches'))}, "
         f"clean: {_yn(base.get('clean'))}. "
         f"{base.get('version_read') or ''}"),
        ("driver each arm ran",
         ", ".join(f"{k} `{v}`"
                   for k, v in (env.get("driver_per_arm") or {}).items())),
        ("driver version each arm's own trace carries",
         ", ".join(f"{k} {v}" for k, v in
                   (env.get("driver_version_per_arm") or {}).items())),
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
        ("targets, each emptied from scratch by its OWN prep build",
         ", ".join(f"{k} `{v}`"
                   for k, v in (env.get("target_per_arm") or {}).items())),
        ("corpus target (E6-again′) — FRESH for this run",
         f"`{env.get('corpus_target')}`, "
         f"{env.get('corpus_target_bytes_before')} bytes at the start"),
        ("probe target (E7⁗)", f"`{env.get('probe_target')}`"),
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
        ("HEAD driver `built_from` (recorded by the runner)",
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
        ("§1's frozen census (Tasks 0 and 1, before the lock) — the five "
         "numbers §1 carries",
         ", ".join(f"{k} {v}" for k, v in
                   (env.get("frozen_census") or {}).items())),
        ("census numbers from the T0/T1 ledger that §1 does NOT freeze",
         ", ".join(f"{k} {v}" for k, v in
                   (env.get("ledger_census") or {}).items())),
    ]
    out += ["| Pin | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in pins]
    out += ["", f"**Log locations.** Every command's log is under "
                f"`{env.get('logs_dir')}`, one subdirectory per phase "
                f"(`built-from`, `prep-head`, `prep-base`, `arm-a`, `arm-ws`, "
                f"`arm-ws0`, `e6-again`, `e7q`, `e0ppp`). Each prep build "
                f"opens its own `logs_at` block inside itself, so its "
                f"`cargo -v` log lands under that prep's directory and the "
                f"two cannot overwrite each other: "
                f"`{env.get('prep_head_log')}` and "
                f"`{env.get('prep_base_log')}`.", ""]
    loads = env.get("load_at_each_arm") or []
    out += ["1-minute load at each phase's start: "
            + ", ".join(f"{a.get('arm')} {a.get('load_1min')}"
                        for a in loads) + "."]
    return out


def _arm(r, key) -> list[str]:
    e = r["endpoints"][key]
    out = [f"### {ARM_TITLES[key]}", ""] + HEAD
    rows = [("SWALLOWED lines on the primary process "
             "(each adjudicated in §4)", "swallowed_lines"),
            ("SWALLOWED lines over EVERY process (primary + sweep)",
             "union_swallowed_lines"),
            ("SWALLOWED lines the sweep added", "sweep_swallowed_lines"),
            ("SWALLOWED lines the collector could not parse",
             "unparsed_swallowed_lines"),
            ("guarded arms (B4/R15; restates §5, not a new measurement)",
             "guarded_arms"),
            ("Err chains judged on the primary (`raised (N):`)",
             "chains_in_scope"),
            ("processes recorded", "processes")]
    if key == "E6qWS0":
        rows += [("SWALLOWED lines at a flipped site (computed evidence)",
                  "lines_at_flipped_sites"),
                 ("of this arm's lines, sinks not resolved",
                  "lines_at_flipped_sites_unresolved"),
                 ("DISCRIMINATING (≥ 1 false accusation at a flipped arm)",
                  "discriminating")]
    rows.append(("false accusations", "headline"))
    for label, k in rows:
        out.append(row(label, e.get(k)))
    out += ["",
            f"Command: `{e.get('command')}`  ",
            f"Driver: `{e.get('driver')}` (role {e.get('driver_role')}, "
            f"sha256 `{e.get('driver_sha256')}`); the trace's own "
            f"`driver_version`: "
            f"{(e.get('driver_identity') or {}).get('driver_versions')}  ",
            f"Target: `{e.get('target')}`; trace store "
            f"`{e.get('sensorium_dir')}`  ",
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


def _flip(r) -> list[str]:
    e = r["endpoints"]["Eflip"]
    out = ["### E-flip — which arms the repair moved, exactly", ""] + HEAD
    for label, k in (("changed rows whose transition is NOT "
                      "`arm_handled → arm_ambiguous`", "headline"),
                     ("changed rows", "changed_count"),
                     ("every transition is `arm_handled → arm_ambiguous`",
                      "only_handled_to_ambiguous"),
                     ("both rows §1 names flipped", "named_all_flipped"),
                     ("changed rows == §1's frozen census delta",
                      "changed_equals_delta"),
                     ("arm sites only the BASE build declared",
                      "only_before_count"),
                     ("arm sites only the HEAD build declared",
                      "only_after_count")):
        out.append(row(label, e.get(k)))
    out += ["",
            f"Transitions: `{e.get('transitions')}`; frozen delta "
            f"{e.get('frozen_delta')} from `{e.get('frozen_census')}` (§1's "
            f"five). Beside them, not frozen in §1: "
            f"`{e.get('ledger_census')}`.  ",
            f"Arm sites declared: BASE {e.get('sites_before')}, HEAD "
            f"{e.get('sites_after')}.  ",
            f"Rows declared with more than one `how` (excluded from the "
            f"transitions): `{e.get('multi_how')}`.", "",
            "The rows §1 names:", "",
            "| Row | before | after | flipped |", "|---|---|---|---|"]
    for name, v in (e.get("named") or {}).items():
        out.append(f"| `{name}` | `{v.get('before')}` | `{v.get('after')}` | "
                   f"{_yn(v.get('flipped'))} |")
    changed = e.get("changed") or []
    if not changed:
        return out + ["", "No manifest row changed between the two builds."]
    out += ["", "Every changed row:", "",
            "| # | file | line | qualname | before | after |",
            "|---|---|---|---|---|---|"]
    for i, c in enumerate(changed, 1):
        out.append(f"| {i} | `{c.get('file')}` | {c.get('line')} | "
                   f"`{c.get('qualname')}` | `{c.get('before')}` | "
                   f"`{c.get('after')}` |")
    return out


def _e6again(r) -> list[str]:
    """E6-again′ is §1's E6 row verbatim, so its table is the COMMITTED
    rung-3 renderer, called over a shim whose `E6` key is this document's
    `E6again` block. Only the heading differs."""
    from render_rung3 import _e6 as rung3_e6                       # noqa: PLC0415
    out = rung3_e6({"endpoints": {"E6": r["endpoints"]["E6again"]}})
    out[0] = ("### E6-again′ — the Rust corpus, every `exceptions` question "
              "(20)")
    return out


def _e0ppp(r) -> list[str]:
    from render_rung3 import _e0pp as rung3_e0pp                   # noqa: PLC0415
    out = rung3_e0pp({"endpoints": {"E0pp": r["endpoints"]["E0ppp"]}})
    out[0] = "### E0‴ — the reader on the widest trace yet"
    return out


def _e7q(r) -> list[str]:
    e = r["endpoints"]["E7q"]
    out = ["### E7⁗ — panic locations under the wraps", ""] + HEAD
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
            f"`mechanics.sh`: exit {e.get('mechanics_rc')}, "
            f"{e.get('mechanics_ok')} ok, {len(e.get('mechanics_fail') or [])} "
            f"FAIL, {len(e.get('mechanics_skip') or [])} skip; driver sha "
            f"unchanged across it: {_yn(e.get('driver_unchanged'))}."]
    return out


def _reported(r) -> list[str]:
    rep = r.get("reported") or {}
    disp = rep.get("dispositions") or {}
    ex = rep.get("executed_flipped_arms") or {}
    out = ["### Reported without a gate", "",
           "**Per-disposition tallies, all three arms side by side.**", "",
           "| Arm | processes | primary `dispositions:` line | all processes "
           "summed |", "|---|---|---|---|"]
    for label, d in disp.items():
        out.append(f"| {label} | {d.get('processes')} | "
                   f"`{d.get('primary_tally_line')}` | "
                   f"{d.get('all_processes_tally')} |")
    out += ["", "**Of the flip set, which arms each arm EXECUTED** — an arm "
                "the run never reaches is not evidence either way.", ""] + HEAD
    for label, e in ex.items():
        out.append(row(f"EXECUTED by {label}", e.get("executed")))
    for label, e in ex.items():
        rows = e.get("executed_rows") or []
        out += ["", f"{label} executed, named one by one: "
                    + (", ".join(f"`{x.get('file')}:{x.get('line')}` "
                                 f"({x.get('events')} events)"
                                 for x in rows) if rows else "none") + ".  ",
                f"{label} did not reach: "
                + (", ".join(f"`{x.get('file')}:{x.get('line')}`"
                             for x in (e.get("not_executed_rows") or []))
                   or "none") + "."]
    out += ["", "**The two prep builds** (from-scratch `--workspace "
                "--no-run`, each emptying its own target so every unit was "
                "compiled by that build's driver and the manifest set is "
                "complete):", "",
            "| Prep | driver | target | exit | wall (s) | units | emptied "
            "(bytes) | arm rows | by `how` |",
            "|---|---|---|---|---|---|---|---|---|"]
    for key in ("prep_head", "prep_base"):
        p = rep.get(key) or {}
        out.append(f"| {key} | `{p.get('driver')}` | `{p.get('target')}` | "
                   f"{p.get('rc')} | {p.get('wall_s')} | {p.get('units')} | "
                   f"{p.get('target_emptied_bytes')} | "
                   f"{(p.get('arm_sites_distinct') or {}).get('value')} | "
                   f"{p.get('arm_sites_by_how')} |")
    for label, key in (("E6⁗-WS", "flip_lines_ws"),
                       ("E6⁗-WS0", "flip_lines_ws0")):
        fl = rep.get(key) or {}
        out += ["", f"{label}: {fl.get('count')} SWALLOWED line(s) at a "
                    f"flipped site, of {fl.get('read')} read "
                    f"({fl.get('unresolved')} unresolved, "
                    f"{fl.get('not_under_the_clone_root')} outside the clone "
                    f"root)."]
    return out


def results(r) -> list[str]:
    e = r["endpoints"]
    rules = {
        "E6⁗-A": "0 false accusations on the clone's `-p bloomery-daemon "
                 "--lib` suite",
        "E6⁗-WS": "0 false accusations over the union of every process of "
                  "the clone's `--workspace` suite",
        "E6⁗-WS0": "≥ 1 false accusation at a flipped arm — NOT a merge "
                   "gate; a 0 makes E6⁗-WS NOT DISCRIMINATING",
        "E-flip": "both named rows go `arm_handled` → `arm_ambiguous`; no "
                  "other transition; changed rows == the frozen delta",
        "E6-again′": "printed SWALLOWED lines == the registered set for every "
                     "case; any extra = a false accusation = STOP",
        "E7⁗": "0 failures, 0 differences",
        "E0‴": "both reads under 60 s",
    }
    keys = {"E6⁗-A": "E6qA", "E6⁗-WS": "E6qWS", "E6⁗-WS0": "E6qWS0",
            "E-flip": "Eflip", "E6-again′": "E6again", "E7⁗": "E7q",
            "E0‴": "E0ppp"}
    name = Path(r["acceptance"]).with_suffix("").name
    out = ["## 3. Results", "",
           "Every measurement is `{value, n, lens, dropped}`; a `null` value "
           "with a reason is the ONLY not-measured, and `0` is "
           "measured-and-zero. Rendered by `rust/tests/render_e6q.py` from "
           f"`{name}.results.json`. No verdict is decided here — §4 is.", "",
           "| Id | Headline | n | Lens (abridged) | Dropped |",
           "|---|---|---|---|---|"]
    for label, key in keys.items():
        m = e[key]["headline"]
        out.append(f"| {label} | {cell(m)} (rule: {rules[label]}) | "
                   f"{n_of(m)} | {lens_of(m)} | {dropped_of(m)} |")
    for key in ("E6qA", "E6qWS", "E6qWS0"):
        out += [""] + _arm(r, key)
    out += [""] + _flip(r)
    out += [""] + _e6again(r)
    out += [""] + _e7q(r)
    out += [""] + _e0ppp(r)
    out += [""] + _reported(r)
    return out


def document(argv) -> int:
    import json                                                    # noqa: PLC0415
    default = (Path(__file__).resolve().parents[2] / "docs" / "superpowers"
               / "acceptance"
               / "2026-09-05-sensorium-rung3-e6q.results.json")
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else default
    r = json.loads(path.read_text())
    print("\n".join(environment(r) + [""] + results(r)))
    return 0


if __name__ == "__main__":
    raise SystemExit(document(sys.argv[1:]))
