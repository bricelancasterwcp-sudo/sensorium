#!/usr/bin/env python3
"""`2026-09-05-sensorium-rung4-entry-grain.results.json` -> §2 and §3.

Run directly:

    .venv/bin/python rust/tests/render_grain.py [results.json]

A module of its own for the reason `render_rung3.py`, `render_e6ppp.py` and
`render_e6q.py` are: no file in this repository may pass 800 lines. Its table
helpers are imported from `render_acceptance`, and H1 is rendered by the
COMMITTED rung-3 renderer over this document's block -- a second table would
be free to disagree with the record that protocol already published.

The renderer's one rule is `render_acceptance`'s: a `null` value prints as
`not measured (<reason>)` and never as a dash, a zero or an empty cell; `0`
is a measured zero.

§4 and §5 are never rendered. They are the verdicts and the gaps, written by
hand against §1's rules and the raw record.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_acceptance import (cell, dropped_of, lens_of, n_of,     # noqa: E402
                               row)

HEAD = ["| Measurement | Value | n | Lens (abridged; the full lens is in "
        "`results.json`) | Dropped |", "|---|---|---|---|---|"]

RULES = {
    "H1": "20 of 20 equal (swallow sets, tallies, every pinned line)",
    "H2": "exactly 5 SWALLOWED groups at the record's five sites; 0 "
          "differences; the tally line byte-identical",
    "H3": "every tally line byte-identical and every swallow count equal — "
          "0 of 288",
    "H4": "the record's per-site tables reproduced — 0 differences; the "
          "summed tallies equal; header counts 144 / 114 / 30",
    "H5": "both answers under 60 s",
    "H6": "the Python suite green and byte-identical expectations; the Rust "
          "workspace green",
}


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def environment(r) -> list[str]:
    env, bl = r["environment"], r.get("byte_lock") or {}
    orc = r.get("oracle") or {}
    name = Path(r["acceptance"]).with_suffix("").name
    out = ["## 2. Environment", "",
           f"Measured {r.get('started')} → {r.get('finished')} by "
           f"`{r.get('runner')}`, launched detached; the raw facts it "
           f"recorded are `results-grain-raw.json` in the gitignored plan "
           f"ledger, with every command's log beside it. §3 below is "
           f"rendered from `{name}.results.json`, which "
           f"`acceptance_grain_schema.assemble_grain` derived from that raw "
           f"file.", "",
           f"**§1 byte-lock.** The runner refuses to start unless the locked "
           f"range is byte-identical to the commit that locked it — and "
           f"refuses outright while no lock sha is set. The range is "
           f"{bl.get('range')} — here §1 references no footnote "
           f"(`footnotes_in_range` = "
           f"{bl.get('footnotes_in_range') or 'none'}), so the extended "
           f"range and `{bl.get('extraction')}` are the same bytes. Checked "
           f"at `{bl.get('commit')}`: {bl.get('locked_bytes')} bytes, sha256 "
           f"`{bl.get('locked_sha256')}` on both sides — identical: "
           f"{_yn(bl.get('identical'))}. §1 was committed ALONE and never "
           f"amended: there is no second sha "
           f"(`original_lock` = {bl.get('original_lock')}).", "",
           f"**The oracle.** `{orc.get('record')}` at `{orc.get('commit')}` "
           f"(sha256 `{orc.get('sha256')}`) — sites {orc.get('sites')}, "
           f"lines {orc.get('lines')}, processes with a tally line "
           f"{orc.get('tally_lines')}, without one "
           f"{orc.get('without_a_tally_line')}. {orc.get('note')}", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("driver (H1 only; NOT rebuilt by this run)",
         f"`{env.get('driver')}` {env.get('driver_version')}, mtime "
         f"{env.get('driver_mtime')}; rebuilt: "
         f"{_yn(env.get('driver_rebuilt_by_this_run'))}"),
        ("driver sha256",
         f"`{env.get('driver_sha256')}` — unchanged across the run: "
         f"{_yn(env.get('driver_unchanged_after'))}"),
        ("kept trace stores (the INPUTS)",
         f"`{env.get('stores_root')}`/{{a,ws,ws0}}; traces before "
         + ", ".join(f"{k} {v.get('traces')}" for k, v in
                     (env.get("stores_before") or {}).items())
         + "; after "
         + ", ".join(f"{k} {v.get('traces')}" for k, v in
                     (env.get("stores_after") or {}).items())
         + f"; `traces/*.db` unchanged: "
           f"{_yn(env.get('kept_traces_unchanged'))}"),
        ("invocation ids the stores carry",
         ", ".join(f"{k} `{v}`" for k, v in
                   (env.get("store_invocations") or {}).items())),
        ("the one write this run causes",
         f"{env.get('read_only_reading')} — rows added: "
         f"{env.get('invocations_jsonl_lines_added')}"),
        ("fresh trace directory (H1's, which stays empty)",
         f"`{env.get('sensorium_dir')}`; traces in it afterwards: "
         f"{env.get('fresh_sensorium_dir_traces')}"),
        ("corpus target (H1) — FRESH for this run",
         f"`{env.get('corpus_target')}`, "
         f"{env.get('corpus_target_bytes_after')} bytes afterwards"),
        ("Rust workspace target (H6's `cargo test`)",
         f"`{env.get('rust_target')}`"),
        ("toolchain", f"{env.get('rustc')} / {env.get('cargo')}"),
        ("reader",
         f"{env.get('python')}, sensorium {env.get('sensorium_version')}"),
        ("machine",
         f"{env.get('nproc')} cpus, governor `{env.get('governor')}`"),
        ("repo porcelain before / after",
         f"{'empty' if not env.get('repo_porcelain') else 'DIRTY'} / "
         f"{'empty' if not env.get('repo_porcelain_after') else 'DIRTY'}"),
        ("1-minute load at the start", f"{env.get('load_1min_at_start')}"),
        ("disk free on the repo's filesystem, before / after",
         f"{env.get('repo_disk_free_gb')} GB / "
         f"{env.get('repo_disk_free_gb_after')} GB"),
    ]
    out += ["| Pin | Value |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in pins]
    loads = env.get("load_at_each_phase") or []
    out += ["", f"**Log locations.** Every command's log is under "
                f"`{env.get('logs_dir')}`, one subdirectory per phase "
                f"(`h2`, `h3-ws`, `h3-ws0`, `h4-ws`, `h4-ws0`, `h1`, `h6`).",
            ""]
    if loads:
        out += ["1-minute load at each phase's start: "
                + ", ".join(f"{a.get('arm')} {a.get('load_1min')}"
                            for a in loads) + "."]
    return out


def _h2(r) -> list[str]:
    e = r["endpoints"]["H2"]
    out = ["### H2 — the grouped view of the A run, at the site grain", ""]
    out += HEAD
    for label, k in (("site-table differences (the gate)", "headline"),
                     ("SWALLOWED groups printed", "groups"),
                     ("chains those groups account for", "chains"),
                     ("the tally line is the record's", "tally_line_equal"),
                     ("sinks the join could not resolve",
                      "unresolved_sinks")):
        out.append(row(label, e.get(k)))
    out += ["",
            f"Command: `{e.get('command')}` on run `{e.get('run')}` (exit "
            f"{e.get('rc')}, {e.get('wall_s')} s, {e.get('stdout_bytes')} "
            f"bytes over {e.get('stdout_lines')} lines).  ",
            f"Printed tally: `{e.get('tally_line')}`; the record's: "
            f"`{e.get('oracle_tally_line')}`.  ",
            f"Vary lines printed, by kind: `{e.get('vary')}`.", ""]
    sites = e.get("measured_sites") or {}
    if sites:
        out += ["The five shapes, as measured:", "",
                "| sink | chains |", "|---|---|"]
        out += [f"| `{k}` | {v} |" for k, v in sites.items()]
    return out


def _h3(r) -> list[str]:
    e = r["endpoints"]["H3"]
    out = ["### H3 — every process of `ws` and `ws0`, one question each", ""]
    out += HEAD
    out.append(row("per-process comparisons that differ (the gate)",
                   e.get("headline")))
    out.append(row("comparisons made", e.get("comparisons")))
    for label, a in (e.get("arms") or {}).items():
        for text, k in (("processes read", "processes"),
                        ("tally lines that are not the record's",
                         "unequal_tally_lines"),
                        ("swallow counts that are not the record's",
                         "unequal_swallow_counts"),
                        ("chains over this arm", "chains_total")):
            out.append(row(f"`{label}`: {text}", a.get(k)))
    out.append("")
    for label, a in (e.get("arms") or {}).items():
        out.append(f"`{label}`: runs only in the store "
                   f"`{a.get('runs_only_in_the_store')}`, only in the record "
                   f"`{a.get('runs_only_in_the_record')}`; total output "
                   f"{a.get('stdout_bytes_total')} bytes over "
                   f"{a.get('stdout_lines_total')} lines; vary lines "
                   f"`{a.get('vary')}`.  ")
    return out


def _h4(r) -> list[str]:
    e = r["endpoints"]["H4"]
    out = ["### H4 — the invocation view against the record's per-site "
           "tables", ""]
    out += HEAD
    out.append(row("site-table differences over both arms (the gate)",
                   e.get("headline")))
    for label, a in (e.get("arms") or {}).items():
        for text, k in (("site-table differences", "site_differences"),
                        ("merged SWALLOWED groups", "groups"),
                        ("chains they account for", "chains"),
                        ("the summed tally is the record's", "tally_equal"),
                        ("the header's counts are the record's",
                         "header_counts_equal"),
                        ("members named INCOMPLETE", "incomplete_members"),
                        ("sinks the join could not resolve",
                         "unresolved_sinks")):
            out.append(row(f"`{label}`: {text}", a.get(k)))
    out.append("")
    for label, a in (e.get("arms") or {}).items():
        h = a.get("header") or {}
        out += [f"`{label}`: `{a.get('command')}` (exit {a.get('rc')}, "
                f"{a.get('wall_s')} s, {a.get('stdout_bytes')} bytes over "
                f"{a.get('stdout_lines')} lines).  ",
                f"`{label}` header: `{h.get('processes')} processes, "
                f"{h.get('with_chains')} with Err chains, "
                f"{h.get('without_chains')} with none`; tally "
                f"`{h.get('tally')}` against the record's summed "
                f"`{a.get('oracle_tally')}`; vary lines `{a.get('vary')}`.  "]
    return out


def _h5(r) -> list[str]:
    e = r["endpoints"]["H5"]
    out = ["### H5 — is the invocation view usable?", ""] + HEAD
    for label, k in (("the slower of the two answers, s", "headline"),
                     ("walls, per arm", "walls_s"),
                     ("arms the 60 s kill fired on", "killed")):
        out.append(row(label, e.get(k)))
    return out


def _h6(r) -> list[str]:
    e = r["endpoints"]["H6"]
    out = ["### H6 — did anything else move?", ""] + HEAD
    for label, k in (("`pytest -q` exit status (the gate)", "headline"),
                     ("the suite's summary line", "pytest_summary"),
                     ("`cargo test --workspace` exit status", "cargo_rc")):
        out.append(row(label, e.get(k)))
    out += ["",
            f"`cargo test` results: `{e.get('cargo_result_lines')}`; the "
            f"driver's sha256 afterwards `{e.get('driver_sha256_after')}`.  ",
            f"Python logs `{e.get('python_log')}`; cargo logs "
            f"`{e.get('cargo_log')}`; the only variables set for the suite: "
            f"`{e.get('python_env')}`.", ""]
    return out


def _h1(r) -> list[str]:
    """H1's table. The CELLS are the committed rung-3 schema's
    (`acceptance_schema_rung3._e6`, called by this document's schema), so no
    number here can disagree with the record that protocol already published;
    only the heading and the column order are local, because this document's
    row is called H1 and names the pins updated BY RULE."""
    e = r["endpoints"]["H1"]
    out = ["### H1 — the corpus, against the pins updated BY RULE", ""]
    out += HEAD + [
        row("printed SWALLOWED lines no registered group claims "
            "(false accusations)", e["headline"]),
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


def _reported(r) -> list[str]:
    rep = r.get("reported") or {}
    b = rep.get("busiest_ws_process") or {}
    v = rep.get("per_process_versus_invocation") or {}
    return [
        "### Reported without a gate", "",
        f"**The busiest `ws` process** (`{b.get('run')}`): "
        f"{b.get('bytes_0_8_1')} bytes under 0.8.1 → {b.get('bytes_0_8_2')} "
        f"bytes over {b.get('lines_0_8_2')} lines under 0.8.2, printed as "
        f"{b.get('groups_0_8_2')} groups accounting for "
        f"{b.get('chains_0_8_2')} chains ({b.get('swallowed_lines_0_8_1')} "
        f"SWALLOWED lines in the record). {b.get('note')}", "",
        f"**{v.get('processes')} per-process answers versus one invocation "
        f"answer**: {v.get('per_process_bytes_total')} bytes over "
        f"{v.get('per_process_lines_total')} lines, against "
        f"{v.get('invocation_bytes')} bytes over "
        f"{v.get('invocation_lines')} lines. {v.get('note')}", "",
        f"**Vary lines that fired, by kind** (an honesty count, not a gate): "
        f"`{rep.get('vary_lines_by_kind')}` — summed over every answer this "
        f"run read: {', '.join(rep.get('vary_counted_over') or []) or 'none'}."
        f" {rep.get('vary_lens', '')}", ""]


def results(r) -> list[str]:
    e = r["endpoints"]
    name = Path(r["acceptance"]).with_suffix("").name
    out = ["## 3. Results", "",
           "Every measurement is `{value, n, lens, dropped}`; a `null` value "
           "with a reason is the ONLY not-measured, and `0` is "
           "measured-and-zero. Rendered by `rust/tests/render_grain.py` from "
           f"`{name}.results.json`. No verdict is decided here — §4 is.", "",
           "| Id | Headline | n | Lens (abridged) | Dropped |",
           "|---|---|---|---|---|"]
    for label in ("H1", "H2", "H3", "H4", "H5", "H6"):
        m = e[label]["headline"]
        out.append(f"| {label} | {cell(m)} (rule: {RULES[label]}) | "
                   f"{n_of(m)} | {lens_of(m)} | {dropped_of(m)} |")
    out += [""] + _h2(r)
    out += [""] + _h3(r)
    out += [""] + _h4(r)
    out += [""] + _h5(r)
    out += [""] + _h6(r)
    out += [""] + _h1(r)
    out += [""] + _reported(r)
    return out


def document(argv) -> int:
    import json                                                    # noqa: PLC0415
    default = (Path(__file__).resolve().parents[2] / "docs" / "superpowers"
               / "acceptance"
               / "2026-09-05-sensorium-rung4-entry-grain.results.json")
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else default
    r = json.loads(path.read_text())
    print("\n".join(environment(r) + [""] + results(r)))
    return 0


if __name__ == "__main__":
    raise SystemExit(document(sys.argv[1:]))
