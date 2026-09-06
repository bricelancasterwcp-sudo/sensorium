#!/usr/bin/env python3
"""`2026-09-06-sensorium-rung4-e9.results.json` -> §2 and §3.

Run directly:

    .venv/bin/python rust/tests/render_e9.py [results.json]

A module of its own for the reason `render_grain.py` is one: no file in this
repository may pass 800 lines, and the table helpers are `render_acceptance`'s
so a `null` cannot render as a dash in one record and as `not measured` in
another.

The renderer's one rule is `render_acceptance`'s: a `null` value prints as
`not measured (<reason>)` and never as a dash, a zero or an empty cell; `0`
is a measured zero.

§4 and §5 are never rendered. They are the verdicts and the gaps, written by
hand at Task 8 against §1's rules and the raw record.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_acceptance import cell, row              # noqa: E402

HEAD = ["| Measurement | Value | n | Lens (abridged; the full lens is in "
        "`results.json`) | Dropped |", "|---|---|---|---|---|"]

#: What §1 pre-registered, per endpoint, printed beside the numbers so a
#: reader sees the gate without opening the document. These are the RULES,
#: not values: nothing here is ever substituted for a measurement.
RULES = {
    "H1": "`capabilities.line` and `capabilities.locals` both false; LINE "
          "rows 0; the pinned refusal at exit 3",
    "H2": "both values resolve to exactly one qualname; F1's counts equal "
          "U1's and F2's equal U2's; a focused compile failure is a STOP",
    "H3": "N = 26 (the gate); 25 or 27 is a MISS §1.1 accounts for; anything "
          "else is a STOP",
    "H4": "all three triples as predicted, on both readings",
    "H5": "both sightings found among A's LINE deltas, and no unpredicted "
          "one there",
    "H6": "reported, not gated",
    "H7": "every corpus case equal; the Python suite green; the Rust "
          "workspace green",
}


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def _empty(v) -> str:
    return "empty" if not v else "DIRTY"


def environment(r) -> list[str]:
    env, bl = r["environment"], r.get("byte_lock") or {}
    name = Path(r["acceptance"]).with_suffix("").name
    bf = env.get("built_from") or {}
    out = [
        "## 2. Environment", "",
        f"Measured {r.get('started')} → {r.get('finished')} by "
        f"`{r.get('runner')}`, launched detached; the raw facts it recorded "
        f"are `results-e9-raw.json` in the gitignored plan ledger, with "
        f"every command's log beside it. §3 below is rendered from "
        f"`{name}.results.json`, which `acceptance_e9_schema.assemble_e9` "
        f"derived from that raw file.", "",
        f"**§1 byte-lock.** The runner refuses to start unless the locked "
        f"range is byte-identical to the commit that locked it — and refuses "
        f"outright while no lock sha is set. The range is {bl.get('range')} "
        f"— here §1 references no footnote (`footnotes_in_range` = "
        f"{bl.get('footnotes_in_range') or 'none'}), so the extended range "
        f"and `{bl.get('extraction')}` are the same bytes. Checked at "
        f"`{bl.get('commit')}`: {bl.get('locked_bytes')} bytes, sha256 "
        f"`{bl.get('locked_sha256')}` on both sides — identical: "
        f"{_yn(bl.get('identical'))}. §1 was committed ALONE and never "
        f"amended: there is no second sha (`original_lock` = "
        f"{bl.get('original_lock')}, amended: "
        f"{_yn(bl.get('amended_after_the_original_lock'))}).", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("the clone under measurement (READ-ONLY input)",
         f"`{env.get('clone')}` at `{env.get('clone_head')}`; §1.4's pin "
         f"`{env.get('clone_pin')}`; porcelain before / after "
         f"{_empty(env.get('clone_porcelain'))} / "
         f"{_empty(env.get('clone_porcelain_after'))}; HEAD after "
         f"`{env.get('clone_head_after')}`"),
        ("the clone's `Cargo.lock`",
         f"sha256 `{env.get('clone_cargo_lock_sha256')}` before, "
         f"`{env.get('clone_cargo_lock_sha256_after')}` after (moved: "
         f"{_yn(env.get('clone_cargo_lock_moved'))}); restored to the pin: "
         f"{_yn(env.get('clone_cargo_lock_back_on_the_pin'))}"),
        ("driver — BUILT by the runner from HEAD",
         f"`{env.get('driver')}` ({env.get('driver_profile')} profile), "
         f"`{bf.get('command')}` exit {bf.get('cargo_rc')} in "
         f"{bf.get('cargo_wall_s')} s from HEAD "
         f"`{bf.get('repo_head_at_build')}`; rebuilt: "
         f"{_yn(env.get('driver_rebuilt_by_this_run'))}"),
        ("driver sha256",
         f"`{env.get('driver_sha256')}` before, "
         f"`{env.get('driver_sha256_after')}` after — unchanged: "
         f"{_yn(env.get('driver_unchanged_after'))}"),
        ("trace store — FRESH and empty at the start",
         f"`{env.get('sensorium_dir')}`"),
        ("cargo target for the four runs — FRESH",
         f"`{env.get('e9_target')}`"),
        ("H7's corpus target — FRESH",
         f"`{env.get('corpus_target')}` (named by "
         f"`SENSORIUM_CORPUS_TARGET`: "
         f"{_yn(env.get('corpus_target_from_env'))})"),
        ("Rust workspace target (H7's `cargo test --workspace`)",
         f"`{env.get('rust_target')}`"),
        ("`TMPDIR` as observed",
         f"{env.get('tmpdir_observed')!r} — {env.get('tmpdir_reading')}"),
        ("`SENSORIUM_TIER`", f"{env.get('sensorium_tier')}"),
        ("the invocation audit log",
         f"{env.get('invocation_log')} — rows in the store afterwards: "
         f"{env.get('invocations_jsonl_lines')}"),
        ("toolchain", f"{env.get('rustc')} / {env.get('cargo')}"),
        ("reader",
         f"{env.get('python')}, sensorium {env.get('sensorium_version')}"),
        ("machine",
         f"{env.get('nproc')} cpus, governor `{env.get('governor')}`"),
        ("repo porcelain before / after",
         f"{_empty(env.get('repo_porcelain'))} / "
         f"{_empty(env.get('repo_porcelain_after'))}"),
        ("1-minute load at the start", f"{env.get('load_1min_at_start')}"),
        ("disk free, repo filesystem, before / after",
         f"{env.get('repo_disk_free_gb')} GB / "
         f"{env.get('repo_disk_free_gb_after')} GB"),
        ("disk free, target filesystem, before / after",
         f"{env.get('target_disk_free_gb')} GB / "
         f"{env.get('target_disk_free_gb_after')} GB"),
    ]
    out += ["| Pin | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in pins]
    out += ["", f"**Log locations.** Every command's log is under "
                f"`{env.get('logs_dir')}`, one subdirectory per phase "
                f"(`built-from`, `record-u1`, `record-f1`, `record-u2`, "
                f"`record-f2`, `h1`, `h4`, `h5`, `h7`).", ""]
    loads = env.get("load_at_each_phase") or []
    if loads:
        out += ["1-minute load at each phase's start: "
                + ", ".join(f"{a.get('arm')} {a.get('load_1min')}"
                            for a in loads) + ".", ""]
    out += _recordings(r)
    return out


def _recordings(r) -> list[str]:
    recs = r.get("recordings") or {}
    if not recs:
        return []
    out = ["**The four runs.**", "",
           "| run | command | exit | trace | libtest | wall | focus resolved |",
           "|---|---|---|---|---|---|---|"]
    for name in ("U1", "F1", "U2", "F2"):
        d = recs.get(name)
        if not d:
            out.append(f"| {name} | not recorded | | | | | |")
            continue
        out.append(
            f"| {name} | `{d.get('command')}` | {d.get('rc')} | "
            f"`{d.get('run')}` ({d.get('trace_bytes')} bytes) | "
            f"{d.get('libtest_secs')} s | {d.get('wall_s')} s | "
            f"{d.get('focus_lines') or '—'} |")
    out.append("")
    return out


# ------------------------------------------------------------------ §3


def _table(title, endpoint, rows) -> list[str]:
    out = [title, ""] + HEAD
    for label, key in rows:
        out.append(row(label, (endpoint or {}).get(key)))
    return out


def _h1(r) -> list[str]:
    e = r["endpoints"]["H1"]
    out = _table("### H1 — does an unfocused run stay unfocused?", e, (
        ("LINE rows over the whole U1 trace (the gate: 0)", "headline"),
        ("meta `capabilities.line`", "capabilities_line"),
        ("meta `capabilities.locals`", "capabilities_locals"),
        ("the class `watch` printed", "watch_verdict_class"),
        ("the exit `watch` returned", "watch_exit"),
        ("the refusal sentence, with §2's recorded token (2nd reading)",
         "refusal_sentence_equal"),
    ))
    out += ["", f"Rule: {RULES['H1']}.  ",
            f"Recorder as the trace declares it: `{e.get('recorder')}`.  ",
            f"Expected sentence: `{e.get('expected_refusal')}`.  ",
            f"Printed sentence: `{e.get('printed_refusal')}`.  ",
            f"Command: `{e.get('watch_command')}`; the count is "
            f"`{e.get('line_rows_query')}`.", ""]
    return out


def _h2(r) -> list[str]:
    e = r["endpoints"]["H2"]
    out = _table("### H2 — does a focus resolve and build?", e, (
        ("focus values resolving to exactly one qualname (the gate)",
         "headline"),
        ("pairs whose libtest counts are equal (1st reading)",
         "outcomes_equal"),
        ("focused traces whose LINE qualname set is exactly the value "
         "(2nd reading)", "line_qualname_sets"),
        ("pairs whose process exit status is equal (2nd reading)",
         "exit_status_equal"),
        ("focused runs that did not complete (§1's kill 1)",
         "focused_build_failures"),
    ))
    out += ["", f"Rule: {RULES['H2']}.", ""]
    res = e.get("resolution") or {}
    if res:
        out += ["| run | `--focus` value | the driver's `focus:` lines |",
                "|---|---|---|"]
        out += [f"| {k} | `{v.get('value')}` | {v.get('focus_lines')} |"
                for k, v in res.items()]
        out.append("")
    pairs = e.get("pairs") or {}
    if pairs:
        out += ["| pair | focused summary | unfocused summary |",
                "|---|---|---|"]
        for k, p in pairs.items():
            out.append(f"| {k} | {p.get('focused_summary_lines')} | "
                       f"{p.get('unfocused_summary_lines')} |")
        out.append("")
    return out


def _h3(r) -> list[str]:
    e = r["endpoints"]["H3"]
    out = _table("### H3 — one LINE per completed statement?", e, (
        ("N — the LINE rows of A's activation (the gate: 26)", "headline"),
        ("N equals the gate", "equals_the_gate"),
        ("lines differing from §1.1's table (2nd reading)",
         "line_differences"),
        ("activations of the focus value", "activations"),
        ("the frame join and the code join agree", "joins_agree"),
        ("N is inside {25, 26, 27}", "in_the_accounted_range"),
    ))
    out += ["", f"Rule: {RULES['H3']}.", ""]
    diff = e.get("diff") or {}
    if diff:
        out += [f"Missing lines: `{diff.get('missing_lines')}`; unexpected: "
                f"`{diff.get('unexpected_lines')}`; count differences: "
                f"`{diff.get('count_diffs')}`.", ""]
    hist = e.get("measured_by_line") or {}
    if hist:
        out += ["| source line | LINE rows |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in
                sorted(hist.items(), key=lambda kv: int(kv[0]))]
        out.append("")
    return out


def _h4(r) -> list[str]:
    e = r["endpoints"]["H4"]
    out = _table("### H4 — does `watch` answer?", e, (
        ("triples as predicted on BOTH readings (the gate)", "headline"),
        ("verdict classes as predicted (1st reading)", "class_as_predicted"),
        ("exit statuses as predicted (2nd reading)", "exit_as_predicted"),
        ("triples where the two readings disagree", "readings_disagree"),
    ))
    out += ["", f"Rule: {RULES['H4']}.", "",
            "| # | run | `--expr` | predicted | class | exit |",
            "|---|---|---|---|---|---|"]
    for t in e.get("triples") or []:
        out.append(
            f"| {t.get('id')} | {t.get('run')} | `{t.get('expr')}` | "
            f"{t.get('predicted_class')} / {t.get('predicted_exit')} | "
            f"{t.get('verdict_class')} | {t.get('rc')} |")
    out.append("")
    return out


def _h5(r) -> list[str]:
    e = r["endpoints"]["H5"]
    out = _table("### H5 — does `flow --value` see it?", e, (
        ("sightings found at the predicted line (the gate)", "headline"),
        ("unpredicted sightings among A's LINE deltas",
         "unpredicted_gated_sightings"),
        ("every printed sighting row, per literal (2nd reading)",
         "whole_trace_sightings"),
    ))
    out += ["", f"Rule: {RULES['H5']}.", "",
            "| # | literal | sighting events | gated to A's LINE deltas | "
            "at the predicted line |", "|---|---|---|---|---|"]
    for s in e.get("sightings") or []:
        out.append(f"| {s.get('id')} | `{s.get('literal')}` | "
                   f"{s.get('sighting_events')} | {s.get('gated_count')} | "
                   f"{_yn(s.get('found_at_predicted_line'))} |")
    out.append("")
    return out


def _h6(r) -> list[str]:
    e = r["endpoints"]["H6"]
    out = _table("### H6 — what does it cost?", e, (
        ("the slowest invocation wall, s", "headline"),
        ("libtest's own reported time, s (1st reading)", "libtest_s"),
        ("the whole invocation's wall, s (2nd reading)", "invocation_s"),
    ))
    out += ["", f"Rule: {RULES['H6']}.", "",
            "| pair | libtest focused / unfocused | invocation focused / "
            "unfocused |", "|---|---|---|"]
    for k, p in (e.get("pairs") or {}).items():
        out.append(f"| {k} | {p.get('focused_libtest_s')} s / "
                   f"{p.get('unfocused_libtest_s')} s | "
                   f"{p.get('focused_invocation_s')} s / "
                   f"{p.get('unfocused_invocation_s')} s |")
    out.append("")
    return out


def _h7(r) -> list[str]:
    e = r["endpoints"]["H7"]
    out = _table("### H7 — did nothing else move?", e, (
        ("corpus questions whose answer is not the registered one (the gate)",
         "headline"),
        ("the collector's exit status (2nd reading)", "corpus_rc"),
        ("`pytest -q` exit status", "pytest_rc"),
        ("`cargo test --workspace` exit status", "cargo_rc"),
    ))
    out += ["", f"Rule: {RULES['H7']}.  ",
            f"Corpus: {e.get('corpus_cases')} cases, "
            f"{e.get('corpus_questions')} questions, failures "
            f"`{e.get('corpus_failures')}`, skipped "
            f"`{e.get('corpus_skipped')}`.  ",
            f"Python: `{cell(e.get('pytest_summary'))}`.  ",
            f"Rust: `{e.get('cargo_result_lines')}`.", ""]
    return out


def results(r) -> list[str]:
    out = ["## 3. Results", "", "The gate of each row, and both readings "
           "where §1 pre-committed two. A `null` is not-measured with its "
           "reason; `0` is a measured zero.", ""]
    for fn in (_h1, _h2, _h3, _h4, _h5, _h6, _h7):
        out += fn(r) + [""]
    stop = r.get("stop")
    if stop:
        out += [f"**STOP.** {stop}", ""]
    return out


def main(argv) -> int:
    path = Path(argv[0]) if argv else (
        Path(__file__).resolve().parents[2] / "docs" / "superpowers"
        / "acceptance" / "2026-09-06-sensorium-rung4-e9.results.json")
    doc = json.loads(Path(path).read_text())
    print("\n".join(environment(doc) + [""] + results(doc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
