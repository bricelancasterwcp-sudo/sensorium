#!/usr/bin/env python3
"""`2026-09-07-sensorium-rung4-e4p.results.json` -> §2 and §3.

Run directly:

    .venv/bin/python rust/tests/render_e4p.py [results.json]

The table helpers are `render_acceptance`'s, so a `null` cannot render as a
dash in one record and as `not measured` in another. The renderer's one rule
is that helper's: a `null` value prints as `not measured (<reason>)` and
never as a dash, a zero or an empty cell; `0` is a measured zero; a KILLED
cell prints as killed with its reason, because it has no numeric reading.

§4 and §5 are never rendered. They are the verdicts and the gaps, written by
hand at Task 6 against §1's rules and the raw record -- along with the
erratum for §1's three kill cross-references.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_acceptance import row, schema_sentence            # noqa: E402

HEAD = ["| Measurement | Value | n | Lens (abridged; the full lens is in "
        "`results.json`) | Dropped |", "|---|---|---|---|---|"]

#: What §1 pre-registered per endpoint, printed beside the numbers so a
#: reader sees the gate without opening the document. These are the RULES,
#: not values: nothing here is ever substituted for a measurement.
RULES = {
    "H1": ("granted = 57 AND the WITHHELD set is exactly §1.2's four, by "
           "name, with their program-thread counts (1, 4, 4, 4); any other "
           "partition is a STOP"),
    "H2": "MATCH 61 of 61; any non-MATCH is a STOP",
    "H3": "61 of 61 pairs of exactly one; a count other than 1 is a STOP",
    "H4": ("61 focused keys, every one sharing the driver's inode where the "
           "filesystem allows a link; a copy where a link was possible is a "
           "FINDING, not a STOP"),
    "H5": ("the raw record and the assembled record both carry `e4p/1`; the "
           "E9 and E4 renderers print their own fields on a DRY assemble"),
    "H6": ("every corpus case equal (the new `refocus_child_run` included); "
           "the Python suite green; `cargo test --workspace` green"),
}


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def _empty(v) -> str:
    return "empty" if not v else "DIRTY"


def environment(r) -> list[str]:
    env, bl = r.get("environment") or {}, r.get("byte_lock") or {}
    name = Path(r["acceptance"]).with_suffix("").name
    bf = env.get("built_from") or {}
    tv = env.get("transform_version") or {}
    out = [
        "## 2. Environment", "",
        f"Measured {r.get('started')} → {r.get('finished')} by "
        f"`{r.get('runner')}`, launched detached; the raw facts it recorded "
        f"are `results-e4p-raw.json` in the gitignored plan ledger, with "
        f"every command's log beside it. §3 below is rendered from "
        f"`{name}.results.json`, which `acceptance_e4p_schema.assemble_e4p` "
        f"derived from that raw file.", "",
        schema_sentence(r), "",
        f"**§1 byte-lock.** The runner refuses to start unless the locked "
        f"range is byte-identical to the commit that locked it — and refuses "
        f"outright while no lock sha is set. The range is {bl.get('range')} "
        f"(`footnotes_in_range` = {bl.get('footnotes_in_range') or 'none'}, "
        f"so the extended range and `{bl.get('extraction')}` are the same "
        f"bytes). Checked at `{bl.get('commit')}`: {bl.get('locked_bytes')} "
        f"bytes, sha256 `{bl.get('locked_sha256')}` on both sides — "
        f"identical: {_yn(bl.get('identical'))}. §1 was committed ALONE and "
        f"has never been amended (amended: "
        f"{_yn(bl.get('amended_after_the_original_lock'))}).", ""]
    if r.get("dry_run"):
        out += ["**THIS IS A DRY RUN.** The row table was replaced from a "
                "file and no number below is the measurement.", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`)"),
        ("the clone under measurement (READ-ONLY input)",
         f"`{env.get('clone')}` at `{env.get('clone_head')}`; §1.4's pin "
         f"`{env.get('clone_pin')}`; porcelain before / after "
         f"{_empty(env.get('clone_porcelain'))} / "
         f"{_empty(env.get('clone_porcelain_after'))}"),
        ("the clone's `Cargo.lock`",
         f"sha256 `{env.get('clone_cargo_lock_sha256')}` before, "
         f"`{env.get('clone_cargo_lock_sha256_after')}` after (moved: "
         f"{_yn(env.get('clone_cargo_lock_moved'))}; back on the pin: "
         f"{_yn(env.get('clone_cargo_lock_back_on_the_pin'))})"),
        ("the KEPT E4 store (READ-ONLY input)",
         f"`{env.get('kept_store')}`, {env.get('kept_store_files')} `.db` "
         f"file(s). {env.get('kept_store_read_only_reading')}. Unchanged "
         f"across the whole run: {_yn(env.get('kept_store_unchanged'))}"
         + (f" — differences: {env.get('kept_census_differences')}"
            if env.get("kept_census_differences") else "")),
        ("the copy",
         f"§1.3's statement, executed by "
         f"{env.get('copy_engine') or 'not recorded'} (SQLite "
         f"{env.get('sqlite_version')}; `sqlite3` CLI on PATH: "
         f"{env.get('sqlite3_cli') or 'none'})"),
        ("the driver",
         f"`{env.get('driver')}` sha256 `{env.get('driver_sha256')}`, built "
         f"by this run from HEAD `{bf.get('repo_head_at_build')}` "
         f"(rebuilt: {_yn(env.get('driver_rebuilt_by_this_run'))}); "
         f"unchanged after: {_yn(env.get('driver_unchanged_after'))}"),
        ("the driver's version token",
         f"`{env.get('driver_version_from_the_trace')}` — read from the "
         f"TRACE's own `meta.driver_version`, never from the instrument"),
        ("`sensorium-transform`'s version",
         f"`{tv.get('value')}` — source `{tv.get('source')}` "
         f"(`{tv.get('path')}`). {tv.get('note')}"),
        ("the fresh trace store",
         f"`{env.get('sensorium_dir')}`; invocation log "
         f"{env.get('invocations_jsonl_lines')} row(s)"),
        ("the fresh cargo target",
         f"`{env.get('e4p_target')}`; H6's corpus target "
         f"`{env.get('corpus_target')}` (from an env var: "
         f"{_yn(env.get('corpus_target_from_env'))})"),
        ("`TMPDIR`",
         f"{env.get('tmpdir_observed')!r}; `tempfile.gettempdir()` resolved "
         f"to `{env.get('tempfile_gettempdir')}`. "
         f"{env.get('tmpdir_reading')}"),
        ("`SENSORIUM_TIER`", str(env.get("sensorium_tier"))),
        ("the invocation audit log", str(env.get("invocation_log"))),
        ("toolchain",
         f"{env.get('rustc')}; {env.get('cargo')}; {env.get('python')}; "
         f"sensorium `{env.get('sensorium_version')}` in the tree, "
         f"`{env.get('sensorium_version_metadata')}` in the installed "
         f"distribution metadata"),
        ("machine",
         f"{env.get('nproc')} CPU(s), governor `{env.get('governor')}`, "
         f"1-minute load {env.get('load_1min_at_start')} at the start"),
        ("disk",
         f"repo {env.get('repo_disk_free_gb')} → "
         f"{env.get('repo_disk_free_gb_after')} GB free; artifact disk "
         f"{env.get('target_disk_free_gb')} → "
         f"{env.get('target_disk_free_gb_after')} GB free"),
        ("ceilings", str(env.get("timeouts"))),
        ("logs", str(env.get("logs_dir"))),
    ]
    out += ["| what | value |", "|---|---|"]
    out += [f"| {label} | {value} |" for label, value in pins]
    out.append("")
    loads = env.get("load_at_each_phase") or []
    if loads:
        out += ["**Load at each phase's start.** "
                + "; ".join(f"{a.get('arm')} {a.get('load_1min')}"
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
    out = _table("### H1 — does the harness rule change the licence word as "
                 "predicted?", e, (
                     ("licences GRANTED (the gate: 57)", "headline"),
                     ("the WITHHELD pairs and their program-thread counts",
                      "withheld"),
                     ("granted lines that HIDE the exclusion (2nd reading)",
                      "hides_the_exclusion"),
                     ("WITHHELD reasons that never subtracted (2nd reading)",
                      "reasons_that_never_subtracted"),
                     ("every pair reports exactly 1 harness thread",
                      "harness_threads_all_one"),
                 ))
    out += ["", f"Rule: {RULES['H1']}.", "",
            f"Predicted WITHHELD: `{e.get('expected_granted_n')}` granted, "
            f"and {e.get('gate')}. Measured set as predicted: "
            f"{_yn(e.get('withheld_set_as_predicted'))}; withheld only here: "
            f"{e.get('withheld_only_here') or 'none'}; withheld missing: "
            f"{e.get('withheld_missing') or 'none'}; count mismatches: "
            f"{e.get('withheld_count_mismatches') or 'none'}.", "",
            f"The harness phrase(s) actually printed: "
            f"{e.get('harness_phrases') or 'none'}. Pairs whose two sides "
            f"disagree on the count: {e.get('sides_disagree') or 'none'}. "
            f"Pairs whose licence could not be read: "
            f"{e.get('unread') or 'none'}.", ""]
    return out


def _h2(r) -> list[str]:
    e = r["endpoints"]["H2"]
    out = _table("### H2 — is the verdict untouched?", e, (
        ("MATCH verdicts (the gate: 61)", "headline"),
        ("pairs whose verdict was not MATCH", "non_match"),
        ("word/exit disagreements (2nd reading)", "word_and_exit_disagree"),
    ))
    out += ["", f"Rule: {RULES['H2']}.", "",
            "The printed word and the process exit are read APART and never "
            "derived from each other: a disagreement between them is a "
            "finding reported as one, never resolved in favour of either.",
            ""]
    return out


def _h3(r) -> list[str]:
    e = r["endpoints"]["H3"]
    out = _table("### H3 — is the pair found?", e, (
        ("pairs of exactly one (the gate: 61)", "headline"),
        ("pairs with a NON-empty R2 exclusion list (2nd reading)",
         "excluded_children"),
        ("store/printed reading disagreements", "readings_disagree"),
    ))
    out += ["", f"Rule: {RULES['H3']}.", "",
            "The pair is read from the STORE — `refocus_of`, the launch "
            "timestamp, and R2's child filter re-applied from the same pid / "
            "ppid facts — and the id the CLI printed is a CROSS-CHECK beside "
            "it, never the source.", ""]
    if e.get("not_one"):
        out += ["| test | pairs | qualifying | linked |", "|---|---|---|---|"]
        out += [f"| `{x.get('name')}` | {x.get('n')} | "
                f"{x.get('qualifying')} | {x.get('linked')} |"
                for x in e["not_one"]]
        out.append("")
    return out


def _h4(r) -> list[str]:
    e = r["endpoints"]["H4"]
    out = _table("### H4 — does the shim link?", e, (
        ("focused keys under the census path (the gate: 61)", "headline"),
        ("entries (2nd reading)", "entries"),
        ("distinct inodes (2nd reading)", "distinct_inodes"),
        ("bytes, counted ONCE PER INODE (2nd reading)",
         "bytes_once_per_inode"),
        ("keys sharing the driver's inode", "linked_to_the_driver"),
    ))
    out += ["", f"Rule: {RULES['H4']}.", "",
            f"The three numbers above are printed separately and the byte "
            f"total is never the sum of the per-entry sizes. Driver inode "
            f"`{e.get('driver_inode')}`; shim and driver on one filesystem: "
            f"{_yn(e.get('same_device'))}; keys not linked: "
            f"{e.get('not_linked') or 'none'}. Every key holds a "
            f"`cargo-sensorium`: {_yn(e.get('entries_cover_every_key'))}"
            + (f" — keys holding none: {e.get('keys_without_a_binary')}"
               if e.get("keys_without_a_binary") else "") + ".", ""]
    if e.get("finding"):
        out += [f"**Finding (not a STOP).** {e['finding']}", ""]
    return out


def _h5(r) -> list[str]:
    e = r["endpoints"]["H5"]
    out = _table("### H5 — is `schema_version` present?", e, (
        ("both records carry `e4p/1` (the gate)", "headline"),
        ("the raw record's token", "raw_schema_version"),
        ("the assembled record's token", "assembled_schema_version"),
        ("the E9 and E4 renderers print their own field (2nd reading)",
         "renderers_print_their_field"),
    ))
    out += ["", f"Rule: {RULES['H5']}.", ""]
    dry = e.get("dry_assemble") or {}
    if dry:
        out += ["| record | assembler stamps | renderer's sentence | "
                "committed file carries the field |",
                "|---|---|---|---|"]
        for name, d in sorted(dry.items()):
            out.append(f"| {name} | `{d.get('assembler_stamps')}` | "
                       f"{d.get('sentence') or 'none printed'} | "
                       f"{_yn(d.get('committed_carries_it'))} |")
        out += ["", "The E9 and E4 `results.json` are **not re-derived** and "
                "are not expected to carry the field (design §5's "
                "R-F15/R-G15 precedent: a derivation is STATED, never "
                "rewritten). That they predate it is recorded here, not "
                "repaired.", ""]
    return out


def _h6(r) -> list[str]:
    e = r["endpoints"]["H6"]
    out = _table("### H6 — did nothing else move?", e, (
        ("all three green (the gate)", "headline"),
        ("corpus exit", "corpus_rc"),
        ("corpus cases", "corpus_cases"),
        ("the Python suite's summary", "pytest_summary"),
        ("`cargo test --workspace` exit", "cargo_rc"),
    ))
    out += ["", f"Rule: {RULES['H6']}.", "",
            f"Corpus failures: {e.get('corpus_failures') or 'none'}; errors: "
            f"{e.get('corpus_errors') or 'none'}; skipped: "
            f"{e.get('corpus_skipped') or 'none'}. R2's new "
            f"`refocus_child_run` case present: "
            f"{_yn(e.get('refocus_child_run_present'))}. Rust result lines: "
            f"{e.get('cargo_result_lines') or 'none'}.", ""]
    return out


def pairs(r) -> list[str]:
    """The 61 rows: one per §1.1 name, whether or not it ran."""
    rows = (r.get("pairs") or {}).get("rows") or []
    if not rows:
        return []
    out = ["### The 61 pairs", "",
           "| # | test | original | pair | verdict | exit | licence | "
           "program threads | harness | names the exclusion | env | "
           "relocated keys |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in rows:
        killed = p.get("measured")
        if isinstance(killed, dict) and killed.get("killed"):
            out.append(f"| {p.get('index')} | `{p.get('name')}` | "
                       f"`{p.get('original') or '—'}` | KILLED | "
                       f"{killed.get('reason')} | | | | | | | |")
            continue
        out.append(
            f"| {p.get('index')} | `{p.get('name')}` | "
            f"`{p.get('original')}` | `{p.get('pair') or '—'}` | "
            f"{p.get('verdict') or 'none printed'} | {p.get('exit')} | "
            f"{p.get('licence') or 'none printed'} | "
            f"{p.get('program_threads')} | {p.get('harness_threads')} | "
            f"{_yn(p.get('names_the_exclusion'))} | "
            f"{p.get('env_status') or 'not read'} | "
            f"{', '.join(p.get('env_relocated_keys') or []) or '—'} |")
    out.append("")
    return out


def ungated(r) -> list[str]:
    """§1.4's reported-without-a-gate block."""
    rep = r.get("reported") or {}
    walls = rep.get("walls_s") or {}
    census = rep.get("shim_census") or {}
    store = rep.get("store") or {}
    kept = rep.get("kept_store_unchanged") or {}
    out = ["### Reported without a gate", "",
           f"**Walls.** First focus {walls.get('first_focus')} s; the later "
           f"ones mean {walls.get('later_focus_mean')} s, max "
           f"{walls.get('later_focus_max')} s. {walls.get('note')}.", "",
           f"**The shim census.** {census.get('entries')} entr(ies), "
           f"{census.get('distinct_inodes')} distinct inode(s), "
           f"{census.get('bytes_once_per_inode')} byte(s). "
           f"{census.get('note')}.", "",
           f"**The copy.** {store.get('copies')} original(s), "
           f"{store.get('bytes_copied')} byte(s), by "
           f"{store.get('engine')} (SQLite {store.get('sqlite_version')}); "
           f"the fresh store held {store.get('fresh_listing_n')} file(s) "
           f"when the loop opened and only the copies: "
           f"{_yn(store.get('fresh_holds_only_the_copies'))}.", "",
           f"**The kept store.** {kept.get('before')} file(s) censused "
           f"before, {kept.get('after')} after; identical: "
           f"{_yn(kept.get('identical'))}"
           + (f"; differences: {kept.get('differences')}"
              if kept.get("differences") else "") + ".", "",
           f"**The invocation log.** {rep.get('invocation_log_rows')} row(s) "
           f"— this record's own; the 61 copied originals carry none from "
           f"E4.", ""]
    env = rep.get("env_relocation") or {}
    out += [f"**The target directory, relocated.** §1.4 gives the re-run a "
            f"FRESH `CARGO_TARGET_DIR`, so the variables cargo derives from "
            f"the root differ on every pair. "
            f"{env.get('pairs_with_a_relocated_target')} pair(s) had a key "
            f"the target-root rule explained "
            f"({', '.join(env.get('relocated_keys_seen') or []) or 'none'}); "
            f"{env.get('pairs_changed_for_another_key')} pair(s) had a key "
            f"it did NOT — those are changes and still withhold. Pairs whose "
            f"`env:` line was not read: "
            f"{env.get('pairs_whose_env_line_was_not_read') or 'none'}. "
            f"{env.get('note')}.", ""]
    lic = rep.get("licence_wording") or {}
    out += [f"**H1's second reading, whole.** Harness phrase(s): "
            f"{lic.get('harness_phrases') or 'none'}. Granted lines hiding "
            f"the exclusion: {lic.get('hides_the_exclusion') or 'none'}. "
            f"WITHHELD reasons that never subtracted: "
            f"{lic.get('reasons_that_never_subtracted') or 'none'}. Pairs "
            f"whose two sides disagree: {lic.get('sides_disagree') or 'none'}"
            f".", ""]
    return out


def results(r) -> list[str]:
    out = ["## 3. Results", "", "The gate of each row, and both readings "
           "where §1 pre-committed two. A `null` is not-measured with its "
           "reason; `0` is a measured zero; a KILLED cell has no numeric "
           "reading at all.", ""]
    for fn in (_h1, _h2, _h3, _h4, _h5, _h6, pairs, ungated):
        out += fn(r) + [""]
    if r.get("stop"):
        out += [f"**STOP.** {r['stop']}", ""]
    if r.get("bound_reached"):
        out += [f"**BOUND REACHED.** {r['bound_reached']}", ""]
    if r.get("refused"):
        out += [f"**REFUSED.** {r['refused']}", ""]
    return out


def main(argv) -> int:
    path = Path(argv[0]) if argv else (
        Path(__file__).resolve().parents[2] / "docs" / "superpowers"
        / "acceptance" / "2026-09-07-sensorium-rung4-e4p.results.json")
    doc = json.loads(Path(path).read_text())
    print("\n".join(environment(doc) + [""] + results(doc)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


__all__ = ["HEAD", "RULES", "environment", "main", "pairs", "results",
           "ungated"]
