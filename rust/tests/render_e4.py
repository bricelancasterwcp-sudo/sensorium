#!/usr/bin/env python3
"""`2026-09-07-sensorium-rung4-e4.results.json` -> §2 and §3.

Run directly:

    .venv/bin/python rust/tests/render_e4.py [results.json]

A module of its own for the reason `render_e9.py` is one: no file in this
repository may pass 800 lines, and the table helpers are
`render_acceptance`'s so a `null` cannot render as a dash in one record and
as `not measured` in another.

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
    "H1": "0 of 61 pre-rerun refusals; 61 of 61 invocations reached the "
          "driver",
    "H2": "61 of 61 re-runs complete; a focused BUILD failure is a STOP",
    "H3": "61 of 61 MATCH (the gate); an unexpected DIVERGED is a finding, "
          "a REFUSED after the rerun is a STOP",
    "H4": "REPORTED, no gate: source and environment verified 61 of 61; "
          "output and children UNVERIFIABLE 61 of 61, never summed with the "
          "verified counts",
    "H5": "all three triples as predicted on their own gates -- W1 and W4 on "
          "both readings, W3 on the exit",
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
    ver = env.get("versions_from_the_first_trace") or {}
    out = [
        "## 2. Environment", "",
        f"Measured {r.get('started')} → {r.get('finished')} by "
        f"`{r.get('runner')}`, launched detached; the raw facts it recorded "
        f"are `results-e4-raw.json` in the gitignored plan ledger, with "
        f"every command's log beside it. §3 below is rendered from "
        f"`{name}.results.json`, which `acceptance_e4_schema.assemble_e4` "
        f"derived from that raw file.", "",
        f"**§1 byte-lock.** The runner refuses to start unless the locked "
        f"range is byte-identical to the commit that locked it — and refuses "
        f"outright while no lock sha is set. The range is {bl.get('range')} "
        f"(`footnotes_in_range` = {bl.get('footnotes_in_range') or 'none'}). "
        f"Checked at `{bl.get('commit')}`: {bl.get('locked_bytes')} bytes, "
        f"sha256 `{bl.get('locked_sha256')}` on both sides — identical: "
        f"{_yn(bl.get('identical'))}.", "",
        f"**Both locks.** §1 was committed ALONE at the ORIGINAL lock "
        f"`{bl.get('original_lock')}` ({bl.get('original_lock_bytes')} "
        f"bytes, sha256 `{bl.get('original_lock_sha256')}`), and was then "
        f"amended once — after that lock and before the instrument existed "
        f"(ruling R-H1) — to state the survey's scope, to give §1.2's "
        f"three-test hazard a DISCRIMINATOR, and to correct the "
        f"`.collect()` citation lines. Amended: "
        f"{_yn(bl.get('amended_after_the_original_lock'))}"
        + (f" (+{bl.get('amendment_bytes')} bytes)"
           if bl.get("amendment_bytes") else "")
        + ". Both shas are recorded here, and no endpoint, method, "
          "derivation or table row moved: every `|` row of the locked range "
          "is byte-identical at the two commits "
          "(`tests/test_acceptance_e4.py`).", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("the clone under measurement (READ-ONLY input)",
         f"`{env.get('clone')}` at `{env.get('clone_head')}`; §1.4's pin "
         f"`{env.get('clone_pin')}`; porcelain before / after "
         f"{_empty(env.get('clone_porcelain'))} / "
         f"{_empty(env.get('clone_porcelain_after'))}; HEAD after "
         f"`{env.get('clone_head_after')}`"),
        ("the seven test files",
         f"`{env.get('tests_dir')}` — §1.1's 61 names re-derived from them "
         f"in the preflight and compared row for row"),
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
        ("version tokens — READ FROM THE TRACE, never from the instrument",
         f"recorder `{ver.get('recorder')}`, driver "
         f"`{ver.get('driver_version')}`, fingerprint basis "
         f"`{ver.get('fingerprint_basis')}` (from run "
         f"`{ver.get('from_run')}`); reader sensorium "
         f"{env.get('sensorium_version')}"),
        ("trace store — FRESH and empty at the start",
         f"`{env.get('sensorium_dir')}`"),
        ("cargo target for the 61 pairs — FRESH",
         f"`{env.get('e4_target')}`"),
        ("H7's corpus target — FRESH",
         f"`{env.get('corpus_target')}` (named by "
         f"`SENSORIUM_CORPUS_TARGET`: "
         f"{_yn(env.get('corpus_target_from_env'))})"),
        ("Rust workspace target (H7's `cargo test --workspace`)",
         f"`{env.get('rust_target')}`"),
        ("ceilings",
         f"{(env.get('timeouts') or {}).get('cargo_timeout')} s per `cargo "
         f"sensorium`, "
         f"{(env.get('timeouts') or {}).get('refocus_timeout')} s per "
         f"`sensorium refocus`, "
         f"{(env.get('timeouts') or {}).get('loop_budget_s')} s for the "
         f"whole loop"),
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
                f"(`built-from`, `pass1`, `pass2`, `h5`, `h7`), one file per "
                f"invocation.", ""]
    loads = env.get("load_at_each_phase") or []
    if loads:
        out += ["1-minute load at each phase's start: "
                + ", ".join(f"{a.get('arm')} {a.get('load_1min')}"
                            for a in loads) + ".", ""]
    return out


# ------------------------------------------------------------------ §3


def _table(title, endpoint, rows) -> list[str]:
    out = [title, ""] + HEAD
    for label, key in rows:
        out.append(row(label, (endpoint or {}).get(key)))
    return out


def _h1(r) -> list[str]:
    e = r["endpoints"]["H1"]
    out = _table("### H1 — does every original refocus without a pre-rerun "
                 "refusal?", e, (
                     ("pre-rerun refusals (the gate: 0)", "headline"),
                     ("invocations that reached the driver (2nd reading)",
                      "reached_the_driver"),
                     ("exit-2 answers carrying no §2.3 sentence",
                      "exit_2_without_a_sentence"),
                 ))
    out += ["", f"Rule: {RULES['H1']}.", ""]
    refusals = e.get("refusals") or []
    if refusals:
        out += ["| test | run | exit | sentence |", "|---|---|---|---|"]
        out += [f"| `{x.get('name')}` | `{x.get('run')}` | {x.get('exit')} | "
                f"{x.get('sentence')} |" for x in refusals]
        out.append("")
    return out


def _h2(r) -> list[str]:
    e = r["endpoints"]["H2"]
    out = _table("### H2 — does every re-run complete?", e, (
        ("re-runs that completed (the gate: 61)", "headline"),
        ("focused BUILD failures (§1's kill 1 — a STOP)", "build_failures"),
        ("re-runs whose libtest counts equal the original's (2nd reading)",
         "outcomes_equal"),
        ("pairs where a summary line could not be read",
         "outcomes_unreadable"),
    ))
    out += ["", f"Rule: {RULES['H2']}.  ",
            f"Failed: {e.get('failed_tests') or 'none'}.  ",
            f"Unequal: {e.get('unequal_tests') or 'none'}.", ""]
    caveat = e.get("build_failure_caveat")
    if caveat:
        out += [f"**What the class does not tell apart.** {caveat}", ""]
    return out


def _h3(r) -> list[str]:
    e = r["endpoints"]["H3"]
    out = _table("### H3 — MATCH on the expected list?", e, (
        ("MATCH verdicts (THE GATE: 61 of 61)", "headline"),
        ("DIVERGED verdicts", "diverged"),
        ("… reading as §1.2's named hazard (§1.4's discriminator)",
         "named_hazard"),
        ("… reading as H3's finding", "findings"),
        ("REFUSED after the rerun (§1's kill 2 — a STOP)",
         "refused_after_rerun"),
        ("verdict word and exit disagreeing (2nd reading)",
         "readings_disagree"),
    ))
    out += ["", f"Rule: {RULES['H3']}.  ",
            f"DIVERGED: {e.get('diverged_tests') or 'none'}.", ""]
    events = e.get("divergent_events") or {}
    for name, rows in events.items():
        out += [f"Divergent event(s) for `{name}`:", "", "```"]
        out += [x.get("text", "") for x in rows]
        out += ["```", ""]
    return out


def _h4(r) -> list[str]:
    e = r["endpoints"]["H4"]
    out = _table("### H4 — what does the licence say? (reported, no gate)",
                 e, (
                     ("SOURCE verified", "headline"),
                     ("ENVIRONMENT verified", "env_verified"),
                     ("EXIT verified", "exit_verified"),
                     ("OUTPUT — unverifiable (never counted as verified)",
                      "output_unverifiable"),
                     ("CHILDREN — unverifiable (never counted as verified)",
                      "children_unverifiable"),
                     ("licences granted", "licences_granted"),
                     ("licence lines claiming an unverifiable check (gate: 0)",
                      "claims_an_unverifiable_check"),
                 ))
    out += ["", f"Rule: {RULES['H4']}.  ", f"{e.get('reading')}.  ",
            f"Withheld: {e.get('withheld')}; no licence line: "
            f"{e.get('no_licence_line') or 'none'}.", ""]
    return out


def _h5(r) -> list[str]:
    e = r["endpoints"]["H5"]
    out = _table("### H5 — does the loop close?", e, (
        ("triples as predicted ON THEIR OWN GATE", "headline"),
        ("verdict classes as predicted (1st reading)", "class_as_predicted"),
        ("exit statuses as predicted (2nd reading)", "exit_as_predicted"),
        ("triples where class and exit disagree", "readings_disagree"),
    ))
    out += ["", f"Rule: {RULES['H5']}.", ""]
    triples = e.get("triples") or []
    if triples:
        out += ["| # | NEW trace of | `--at` | gate | predicted | class | "
                "exit | sites / evaluated / hits / not-captured / errors |",
                "|---|---|---|---|---|---|---|---|"]
        for t in triples:
            if "dropped" in t:
                out.append(f"| {t.get('id')} | `{t.get('of')}` | "
                           f"`{t.get('at')}` | {t.get('gate')} | "
                           f"{t.get('predicted_class')} / "
                           f"{t.get('predicted_exit')} | not measured "
                           f"({t.get('dropped')}) | | |")
                continue
            out.append(
                f"| {t.get('id')} | `{t.get('of')}` | `{t.get('at')}` | "
                f"{t.get('gate')} | {t.get('predicted_class')} / "
                f"{t.get('predicted_exit')} | {t.get('verdict_class')} | "
                f"{t.get('rc')} | {t.get('sites')} / {t.get('evaluated')} / "
                f"{t.get('hits')} / {t.get('not_captured')} / "
                f"{t.get('errors')} |")
        out.append("")
    return out


def _h6(r) -> list[str]:
    e = r["endpoints"]["H6"]
    out = _table("### H6 — what does it cost? (reported, no gate)", e, (
        ("the FIRST focus's wall, s (1st reading)", "headline"),
        ("later focuses' mean wall, s", "later_focus_mean_s"),
        ("the slowest later focus, s", "later_focus_max_s"),
        ("entries under `<target>/sensorium/shim/*`", "shim_entries"),
        ("bytes under `<target>/sensorium/shim/*`", "shim_bytes"),
    ))
    out += ["", f"Rule: {RULES['H6']}.  ",
            f"Pass 1 total: {e.get('pass1_total_s')} s; pass 2 total: "
            f"{e.get('refocus_total_s')} s.  ",
            f"Shim census: `{(e.get('shim_census') or {}).get('dir')}`.", ""]
    return out


def _h7(r) -> list[str]:
    e = r["endpoints"]["H7"]
    out = _table("### H7 — did nothing else move?", e, (
        ("corpus questions whose answer is not the expectation", "headline"),
        ("the collector's exit status (2nd reading)", "corpus_rc"),
        ("harness errors", "corpus_errors"),
        ("cases the collector SKIPPED (gate: 0)", "corpus_skipped"),
        ("`pytest -q` exit status", "pytest_rc"),
        ("the suite's summary line", "pytest_summary"),
        ("`cargo test --workspace` exit status", "cargo_rc"),
    ))
    out += ["", f"Rule: {RULES['H7']}.  ",
            f"Corpus: {e.get('corpus_cases')} case(s), "
            f"{e.get('corpus_questions')} question(s); failures "
            f"{e.get('corpus_failures') or 'none'}; skipped "
            f"{e.get('corpus_skipped_cases') or 'none'}.", ""]
    return out


def pairs(r) -> list[str]:
    """The 61 rows: one per §1.1 name, whether or not it ran."""
    rows = (r.get("pairs") or {}).get("rows") or []
    if not rows:
        return []
    out = ["### The 61 pairs", "",
           "| # | test | original | new | verdict | exit | licence | class |",
           "|---|---|---|---|---|---|---|---|"]
    for p in rows:
        if p.get("pass1_not_run") or p.get("pass2_not_run"):
            why = p.get("pass2_not_run") or p.get("pass1_not_run")
            out.append(f"| {p.get('index')} | `{p.get('name')}` | "
                       f"`{p.get('original') or '—'}` | not run | not "
                       f"measured ({why}) | | | |")
            continue
        out.append(
            f"| {p.get('index')} | `{p.get('name')}` | "
            f"`{p.get('original')}` | `{p.get('new_run') or '—'}` | "
            f"{p.get('verdict_word') or 'none printed'} | "
            f"{p.get('pass2_rc')} | {p.get('licence') or '—'} | "
            f"{p.get('diverged_class') or '—'} |")
    out.append("")
    return out


def ungated(r) -> list[str]:
    """§1.4's reported-without-a-gate block."""
    rep = r.get("reported") or {}
    walls = rep.get("walls") or {}
    census = rep.get("shim_census") or {}
    totals = rep.get("pass_totals") or {}
    out = ["### Reported without a gate — §1.4", "",
           "| what | value |", "|---|---|",
           f"| the first focus | {walls.get('first_focus')} |",
           f"| later focuses, min / mean / max s | "
           f"{walls.get('later_focus_min_s')} / "
           f"{walls.get('later_focus_mean_s')} / "
           f"{walls.get('later_focus_max_s')} |",
           f"| pass 1 total / pass 2 total, s | "
           f"{walls.get('pass1_total_s')} / {walls.get('refocus_total_s')} |",
           f"| cargo's own build time reported for | "
           f"{len(walls.get('cargo_build_reported_for') or [])} re-run(s) |",
           f"| shim census | {census.get('entries')} entries, "
           f"{census.get('bytes')} bytes under `{census.get('dir')}` |",
           f"| invocation-log rows at the end | "
           f"{rep.get('invocations_jsonl_lines')} |",
           f"| store bytes / traces recorded | {rep.get('store_bytes')} / "
           f"{rep.get('traces_recorded')} |",
           f"| E4 target bytes / corpus target bytes | "
           f"{rep.get('e4_target_bytes')} / "
           f"{rep.get('corpus_target_bytes')} |",
           f"| pass 1 measured / n | {totals.get('pass1_measured')} / "
           f"{totals.get('pass1_n')} |",
           f"| pass 2 measured / n | {totals.get('pass2_measured')} / "
           f"{totals.get('pass2_n')} |",
           f"| invocations killed at the ceiling | pass 1 "
           f"{totals.get('pass1_killed')}, pass 2 "
           f"{totals.get('pass2_killed')} |",
           f"| invocations never run (the 2-hour bound) | pass 1 "
           f"{totals.get('pass1_budget_exhausted')}, pass 2 "
           f"{totals.get('pass2_budget_exhausted')} |",
           f"| originals with more than one process | "
           f"{totals.get('pass1_multi_process')} |",
           f"| pair-rule refusals | {totals.get('pass2_pair_refusals')} |",
           ""]
    disc = rep.get("discriminator") or {}
    if disc:
        out += ["§1.4's discriminator, where it was applied:", "",
                "| test | worker-task events A / B | MAIN fingerprint equal "
                "| task count A / B | class |", "|---|---|---|---|---|"]
        for name, d in disc.items():
            if not d:
                continue
            out.append(
                f"| `{name}` | {d.get('task_events_total_original')} / "
                f"{d.get('task_events_total_new')} | "
                f"{_yn(d.get('main_fingerprint_matches'))} | "
                f"{d.get('task_count_original')} / {d.get('task_count_new')} "
                f"| {d.get('class')} |")
        out.append("")
    return out


def results(r) -> list[str]:
    out = ["## 3. Results", "", "The gate of each row, and both readings "
           "where §1 pre-committed two. A `null` is not-measured with its "
           "reason; `0` is a measured zero.", ""]
    for fn in (_h1, _h2, _h3, _h4, _h5, _h6, _h7, pairs, ungated):
        out += fn(r) + [""]
    stop = r.get("stop")
    if stop:
        out += [f"**STOP.** {stop}", ""]
    bound = r.get("bound_reached")
    if bound:
        out += [f"**BOUND REACHED.** {bound}", ""]
    return out


def main(argv) -> int:
    path = Path(argv[0]) if argv else (
        Path(__file__).resolve().parents[2] / "docs" / "superpowers"
        / "acceptance" / "2026-09-07-sensorium-rung4-e4.results.json")
    doc = json.loads(Path(path).read_text())
    print("\n".join(environment(doc) + [""] + results(doc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
