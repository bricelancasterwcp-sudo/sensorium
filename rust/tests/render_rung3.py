#!/usr/bin/env python3
"""`2026-09-04-sensorium-rung3-acceptance.results.json` -> §2 and §3.

Reached through `render_acceptance.py --doc rung3`; a module of its own so
neither file passes the repo's 800-line ceiling. The renderer's one rule is
that file's: a `null` value prints as `not measured (<reason>)` and never as a
dash, a zero or an empty cell; `0` is a measured zero.

§4 and §5 are never rendered. They are the verdicts and the gaps, written by
hand against §1's rules and the raw record -- and E6''s adjudication of every
SWALLOWED line against the clone's source is a reading no renderer can do.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_acceptance import (cell, dropped_of, lens_of, n_of,        # noqa: E402
                               pct, row)

HEAD = ["| Measurement | Value | n | Lens (abridged; the full lens is in "
        "`results.json`) | Dropped |", "|---|---|---|---|---|"]


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def environment(r) -> list[str]:
    env, bl = r["environment"], r.get("byte_lock") or {}
    out = ["## 2. Environment", "",
           f"Measured {r.get('started')} → {r.get('finished')} by "
           f"`{r.get('runner')}`, launched detached; the raw facts it recorded "
           f"are `results-rung3-raw.json` in the gitignored plan ledger, with "
           f"every command's log beside it. §3 below is rendered from "
           f"`{Path(r['acceptance']).with_suffix('').name}.results.json`, "
           f"which `acceptance_schema_rung3.assemble_rung3` derived from that "
           f"raw file.", ""]
    out += [
        f"**§1 byte-lock.** The runner refuses to start unless §1 is "
        f"byte-identical to the commit that locked it. Checked at "
        f"`{bl.get('commit')}` with `{bl.get('extraction')}`: "
        f"{bl.get('locked_bytes')} bytes, sha256 "
        f"`{bl.get('locked_sha256')}` on both sides — identical: "
        f"{_yn(bl.get('identical'))}. The ORIGINAL lock is "
        f"`{bl.get('original_lock')}` (sha256 "
        f"`{bl.get('original_lock_sha256')}`, "
        f"{bl.get('original_lock_bytes')} bytes); §1 was amended after it: "
        f"{_yn(bl.get('amended_after_the_original_lock'))} "
        f"({bl.get('amendment_bytes')} bytes added — the dated E6′ footnote).",
        ""]
    rows = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("driver", f"`{env.get('driver')}`, mtime {env.get('driver_mtime')}"),
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
        ("E5″ arm tips", ", ".join(f"{k} `{v}`" for k, v in
                                   (env.get("arm_tips") or {}).items())),
        ("clone porcelain before / after",
         f"{env.get('clone_porcelain_before') or 'empty'} / "
         f"{env.get('clone_porcelain_after') or 'empty'}; restored to the pin: "
         f"{_yn(env.get('clone_restored'))}; `Cargo.lock` unchanged: "
         f"{_yn(env.get('cargo_lock_unchanged'))}"),
        ("target (warm at the start; **emptied by E2″** for the from-scratch "
         "build, which then left it warm for every later arm)",
         f"`{env.get('target_dir')}` — "
         f"{env.get('target_emptied_by_e2pp_bytes')} bytes removed"),
        ("corpus target (E6)", f"`{env.get('corpus_target')}`"),
        ("probe target (E7″)", f"`{env.get('probe_target')}`"),
        ("trace store (new and empty at the start)",
         f"`{env.get('sensorium_dir')}`"),
        ("`~/workspace/bloomery` (READ-ONLY)",
         f"`{env.get('source_bloomery')}` at "
         f"`{env.get('source_bloomery_head_before')}` → "
         f"`{env.get('source_bloomery_head_after')}`; porcelain "
         f"{env.get('source_bloomery_porcelain_before') or 'empty'} → "
         f"{env.get('source_bloomery_porcelain_after') or 'empty'}; "
         f"unchanged: {_yn(env.get('source_bloomery_unchanged'))}"),
        ("1-minute load at the start",
         f"{env.get('load_1min_at_start')} (ceiling 4.0)"),
        ("disk free on the target's filesystem, before / after",
         f"{env.get('target_disk_free_gb')} GB / "
         f"{env.get('target_disk_free_gb_after')} GB"),
        ("E2″'s frozen denominator",
         f"try_syn = {(env.get('frozen_denominator') or {}).get('try_syn')}, "
         f"try_macro_tokens = "
         f"{(env.get('frozen_denominator') or {}).get('try_macro_tokens')} "
         f"({(env.get('frozen_denominator') or {}).get('source')})"),
    ]
    out += ["| Pin | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    loads = env.get("load_at_each_arm") or []
    if loads:
        out += ["", "1-minute load at each checked-out arm's start: "
                + ", ".join(f"`{l['ref']}` {l['load_1min']}" for l in loads)
                + "."]
    return out


def _e6(r) -> list[str]:
    e = r["endpoints"]["E6"]
    out = ["### E6 — the Rust corpus, every `exceptions` question", ""]
    out += HEAD + [
        row("printed SWALLOWED lines no group claims (false accusations)",
            e["headline"]),
        row("registered SWALLOWED groups with no printed line",
            e["missing_swallow_groups"]),
        row("questions whose swallow SET is not equal",
            e["cases_with_an_unequal_swallow_set"]),
        row("questions whose `dispositions:` tally is not equal",
            e["cases_with_an_unequal_tally"]),
        row("swallow cases that printed an empty set",
            e["swallow_cases_with_an_empty_set"]),
        row("the corpus's own (substring) reading's failures",
            e["corpus_reading_failures"]),
    ]
    out += ["", "| Case | Question | SWALLOWED printed / registered | Set "
            "equal | Printed tally | Registered tally | Tally equal |",
            "|---|---|---|---|---|---|---|"]
    for c in e.get("cases", []):
        if c.get("dropped"):
            out.append(f"| `{c['case']}` | — | not measured "
                       f"({c['dropped']}) | — | — | — | — |")
        for q in c.get("questions", []):
            out.append(
                f"| `{c['case']}` | `{q['id']}` | {q['printed']} / "
                f"{q['expected']} | {_yn(q['equal'])} | "
                f"`{q['printed_tally'] or '(none printed)'}` | "
                f"`{q['pinned_tally'] or '(none registered)'}` | "
                f"{_yn(q['tally_equal'])} |")
    return out


def _e6prime(r) -> list[str]:
    e = r["endpoints"]["E6prime"]
    t = e.get("trace") or {}
    out = ["### E6′ — the bloomery clone's `--lib` suite", ""]
    out += HEAD + [
        row("SWALLOWED lines printed (each adjudicated in §4)",
            e["swallowed_lines"]),
        row("SWALLOWED lines the collector could not parse",
            e["unparsed_swallowed_lines"]),
        row("Err chains judged (`raised (N):`)", e["chains_in_scope"]),
        row("false accusations", e["headline"]),
    ]
    out += ["",
            f"Tally line: `{e.get('tally_line')}`  ",
            f"Header `partial:` line: `{e.get('partial_line')}`  ",
            f"Header `panics:` line: `{e.get('panics_line')}`  ",
            f"Paging note (`... N more`): `{e.get('more_note')}`  ",
            f"Run `{e.get('run')}`, {e.get('events')} events, recorded in "
            f"{e.get('wall_s')} s; `exceptions` answered in "
            f"{e.get('exceptions_wall_s')} s (exit {e.get('exceptions_rc')}).",
            ""]
    rows = e.get("swallowed") or []
    if rows:
        out += ["Every SWALLOWED line, with the sink the trace names for it "
                "(the adjudication itself is §4):", "",
                "| # | how | sink | line |", "|---|---|---|---|"]
        for i, s in enumerate(rows, 1):
            sink = s.get("sink") or {}
            where = (f"`{sink.get('file')}:{sink.get('line')}`"
                     if sink.get("file") else "not resolved")
            out.append(f"| {i} | `{s.get('how')}` | {where} "
                       f"(`{s.get('qualname')}` L{s.get('site_line')}) | "
                       f"`{s.get('line')}` |")
    return out


def _e2pp(r) -> list[str]:
    e = r["endpoints"]["E2pp"]
    out = ["### E2″ — the transformer's reach over the clone's `?` sites", ""]
    out += HEAD + [
        row("instrumented `?` sites / syn-visible `?` sites", e["headline"],
            pct),
        row("numerator — distinct `kind: \"try\"` manifest rows",
            e["numerator"]),
        row("numerator — the raw sum over the build's manifests",
            e["numerator_raw"]),
        row("denominator — §1's frozen `try_syn`", e["denominator"]),
        row("units that fell back", e["units_that_fell_back"]),
        row("`fell back to the real tree` lines in the build log",
            e["fell_back_stderr_lines"]),
        row("`partial` rows (distinct)", e["partial_rows"]),
        row("files a module walk could not reach", e["unreached_files"]),
        row("census re-run at run time: `try_syn`", e["census_rerun_try_syn"]),
        row("census re-run at run time: `try_macro_tokens`",
            e["census_rerun_try_macro_tokens"]),
    ]
    out += ["",
            f"The re-run census agrees with the frozen denominator: "
            f"{_yn(e.get('census_rerun_agrees_with_the_frozen_denominator'))}."]
    pf = e.get("partial_by_file") or {}
    if pf:
        out += ["", "`partial` rows per file: "
                + ", ".join(f"`{k}` {v}" for k, v in sorted(pf.items()))
                + f"; reasons: {e.get('partial_reasons')}."]
    return out


def _e7pp(r) -> list[str]:
    e = r["endpoints"]["E7pp"]
    loc = e.get("operand_locations") or {}
    out = ["### E7″ — panic locations under the new wraps", ""]
    out += HEAD + [
        row("FAILED E7 checks on the probe's existing panics", e["headline"]),
        row("E7 checks that passed", e["existing_checks_passed"]),
        row("new operand panic: column shift, tier `call`",
            e["operand_column_shift"]),
        row("new operand panic: column shift, tier `off`",
            e["operand_column_shift_off"]),
        row("new operand panic: line identical (1 = yes)",
            e["operand_line_identical"]),
    ]
    out += ["", f"Predicted shift: **+{e.get('operand_predicted_shift')}** "
            f"(the wrap prefix `match `). Measured locations:", "",
            "| Arm | file:line:col |", "|---|---|"]
    for k in ("plain", "off", "call"):
        v = loc.get(k)
        out.append(f"| {k} | " + (f"`{v['file']}:{v['line']}:{v['col']}`"
                                  if v else "not measured") + " |")
    out += ["", f"`mechanics.sh` exit {e.get('mechanics_rc')}, "
            f"{e.get('mechanics_ok')} checks ok; failures: "
            f"{e.get('mechanics_fail') or 'none'}; skipped: "
            f"{e.get('mechanics_skip') or 'none'}; driver sha256 unchanged "
            f"across it: {_yn(e.get('driver_unchanged'))}."]
    return out


def _e3pp(r) -> list[str]:
    e = r["endpoints"]["E3pp"]
    out = ["### E3″ — determinism with RAISE/HANDLED in the fingerprint", ""]
    out += HEAD + [
        row("DIVERGED + REFUSED verdicts", e["headline"]),
        row("DIVERGED", e["diverged"]), row("REFUSED", e["refused"]),
        row("MATCH", e["matched"]),
        row("runs that produced a trace", e["runs"]),
        row("runs whose binary sha256 differed from run 1's",
            e["sha256_mismatches"]),
    ]
    return out


def _e5pp(r) -> list[str]:
    e = r["endpoints"]["E5pp"]
    out = ["### E5″ — `diff --ignore-moves` still verifies the split", ""]
    out += HEAD + [row("pre-registered conditions not met", e["headline"]),
                   row("code objects paired across a move (A/B)",
                       e["ab_moved"])]
    out += ["", f"A/B verdict: **{e.get('ab_verdict')}** — "
            f"`{e.get('ab_verdict_line')}`  ",
            f"A/C verdict: **{e.get('ac_verdict')}** — "
            f"`{e.get('ac_verdict_line')}`  ",
            f"Conditions: `{e.get('conditions')}`; not met: "
            f"`{e.get('conditions_failed')}`."]
    return out


def _e0pp(r) -> list[str]:
    e = r["endpoints"]["E0pp"]
    out = ["### E0″ — the reader at the new event volume", ""]
    out += HEAD + [
        row("arms at or over the 60 s ceiling", e["headline"]),
        row("`info <run>` wall (s)", e["info_wall_s"]),
        row("`diff <run> <run>` wall (s)", e["diff_wall_s"]),
        row("the larger of the two (s)", e["max_wall_s"]),
    ]
    out += ["", f"`diff` verdict line: `{e.get('diff_verdict_line')}`."]
    return out


def _reported(r) -> list[str]:
    rep = r["reported"]
    out = ["### Reported without a gate", ""]
    out += HEAD + [
        row("E1″ plain median (s)", rep["E1pp_plain_median_s"]),
        row("E1″ call median (s)", rep["E1pp_call_median_s"]),
        row("E1″ overhead, call − plain (s)", rep["E1pp_overhead_s"]),
        row("RAISE events on the E6′ trace", rep["raise_events"]),
        row("HANDLED events on the E6′ trace", rep["handled_events"]),
        row("bytes per record", rep["bytes_per_record"]),
        row("trace bytes", rep["trace_bytes"]),
        row("`meta.sites` JSON bytes", rep["meta_sites_bytes"]),
        row("`meta.partial` rows on the trace",
            rep["partial_rows_on_the_trace"]),
        row("closure frames", rep["closure_frames"]),
    ]
    out += ["", f"Per-disposition tally on the clone: "
            f"`{rep.get('dispositions_on_the_clone')}`.  ",
            f"Site kinds on the trace: `{rep.get('site_kinds')}`.  ",
            f"Event kinds: `{rep.get('event_kinds')}`.  ",
            f"Frame kinds: `{rep.get('frame_kinds')}`.",
            "", "E1″ walls, every round (a dropped arm is never re-rolled):",
            "", "| Round | Arm | Order | Load | Wall (s) | Dropped |",
            "|---|---|---|---|---|---|"]
    for run in (rep.get("E1pp_walls") or {}).get("runs") or []:
        out.append(f"| {run.get('round')} | {run.get('arm')} | "
                   f"{run.get('order')} | {run.get('load_1min')} | "
                   f"{run.get('wall') if run.get('wall') is not None else '—'} "
                   f"| {run.get('dropped') or 'none'} |")
    return out


def results(r) -> list[str]:
    e = r["endpoints"]
    rules = {
        "E6": ("printed SWALLOWED lines == the registered set for every case; "
               "any extra = a false accusation = STOP"),
        "E6′": "0 false accusations on the bloomery clone",
        "E2″": "numerator / try_syn ≥ 95.0%; 0 units fell back",
        "E7″": "existing checks: 0 differences; new check: line identical, "
               "column = original + 6",
        "E3″": "DIVERGED 0/19, REFUSED 0/19",
        "E5″": "A/B MATCH class with every task paired; A/C DIVERGED",
        "E0″": "both under 60 s",
    }
    keys = {"E6": "E6", "E6′": "E6prime", "E2″": "E2pp", "E7″": "E7pp",
            "E3″": "E3pp", "E5″": "E5pp", "E0″": "E0pp"}
    fmts = {"E2″": pct}
    out = ["## 3. Results", "",
           "Every measurement is `{value, n, lens, dropped}`; a `null` value "
           "with a reason is the ONLY not-measured, and `0` is "
           "measured-and-zero. Rendered by "
           "`rust/tests/render_acceptance.py --doc rung3` from "
           f"`{Path(r['acceptance']).name}`'s `results.json`. No verdict is "
           "decided here — §4 is.", "",
           "| Id | Headline | n | Lens (abridged) | Dropped |",
           "|---|---|---|---|---|"]
    for label, key in keys.items():
        m = e[key]["headline"]
        out.append(f"| {label} | {cell(m, fmts.get(label, str))} "
                   f"(rule: {rules[label]}) | {n_of(m)} | {lens_of(m)} | "
                   f"{dropped_of(m)} |")
    for part in (_e6, _e6prime, _e2pp, _e7pp, _e3pp, _e5pp, _e0pp, _reported):
        out += [""] + part(r)
    return out


def document(argv) -> int:
    import json                                                    # noqa: PLC0415
    default = (Path(__file__).resolve().parents[2] / "docs" / "superpowers"
               / "acceptance"
               / "2026-09-04-sensorium-rung3-acceptance.results.json")
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else default
    r = json.loads(path.read_text())
    print("\n".join(environment(r) + [""] + results(r)))
    return 0


if __name__ == "__main__":
    raise SystemExit(document(sys.argv[1:]))
