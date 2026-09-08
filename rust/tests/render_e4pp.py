#!/usr/bin/env python3
"""`2026-09-08-sensorium-rung4-e4pp.results.json` -> §2 and §3.

Run directly:

    .venv/bin/python rust/tests/render_e4pp.py [results.json]

The table helpers are `render_acceptance`'s, so a `null` cannot render as a
dash in one record and as `not measured` in another: a `null` value prints
as `not measured (<reason>)`, `0` is a measured zero, and a KILLED cell
prints as killed with its reason because it has no numeric reading.

§4 and §5 are never rendered. They are the verdicts and the gaps, written
by hand against §1's rules and the raw record.

**Written COMPACT on purpose.** §0 and §1 are 441 lines of this project's
800-line file ceiling, so §2 and §3 together must leave room for §4 and §5
as well. The per-pair tables live in `results.json`; what is rendered here
is one row per endpoint plus the sentences a reader needs to check a gate
without opening the JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from render_acceptance import row, schema_sentence                 # noqa: E402

HEAD = ["| Measurement | Value | n | Lens (abridged; the full lens is in "
        "`results.json`) | Dropped |", "|---|---|---|---|---|"]

#: What §1.4 pre-registered per endpoint, printed beside the numbers so a
#: reader sees the gate without opening the document. These are the RULES,
#: not values: nothing here is ever substituted for a measurement.
RULES = {
    "H1": ("granted = 57 AND the WITHHELD set is exactly §1.2's four, by "
           "name, with 1/4/4/4; any other partition is a STOP"),
    "H2": ("`RUSTDOCFLAGS` in 0 of 61 changed lists, the strip clause "
           "naming it on 61 of 61, and E4′'s four relocated keys on 61 of "
           "61"),
    "H3": "MATCH 61 of 61 and 61 pairs of exactly one",
    "H4": ("the printed session set equals `pins.session_keys_differing` by "
           "name and by size on 61 of 61, and no withholding cites a key of "
           "session set 1"),
    "H5": ("arm B WITHHELD 4 of 4, each env caveat naming `E4PP_INPUT`; any "
           "granted line is a STOP"),
    "H6": ("arm C's licence word equals arm A's on 4 of 4, and the session "
           "set is the pin ∪ the injected key with K exactly one greater"),
    "H7": ("0 null partition cells on a printed licence, every count "
           "carrying its source line, non-null verified counts, and a "
           "version probe that is a token or null WITH its reason — a miss "
           "is a STOP of the INSTRUMENT"),
    "H8": ("corpus rc 0 with `--require-driver` and `refocus_spawned_test_"
           "fn` present, pytest rc 0, `cargo test --workspace` rc 0"),
}

QUESTION = {
    "H1": "does the harness rule change the licence word as predicted?",
    "H2": "is the recorder's fragment gone from the compare?",
    "H3": "is the verdict untouched and the pair still found?",
    "H4": "do session differences stay outside the vote?",
    "H5": "does the licence still bite outside the set?",
    "H6": "is the session count exact, and the word unmoved?",
    "H7": "is the instrument honest?",
    "H8": "did nothing else move?",
}

#: The cells rendered per endpoint, in order, with the label each gets.
CELLS = {
    "H1": (("licences GRANTED (the gate: 57)", "headline"),
           ("the WITHHELD pairs and their program-thread counts", "withheld"),
           ("granted lines that HIDE the exclusion (2nd reading)",
            "hides_the_exclusion"),
           ("WITHHELD reasons that never subtracted (2nd reading)",
            "reasons_that_never_subtracted"),
           ("every pair reports exactly 1 harness thread",
            "harness_threads_all_one")),
    "H2": (("pairs whose CHANGED list names `RUSTDOCFLAGS` (the gate: 0)",
            "rustdocflags_in_changed"),
           ("pairs whose strip clause NAMES it (the gate: 61)",
            "strip_clause_named"),
           ("the relocated key set (the gate: E4′'s four)", "relocated_set"),
           ("pairs whose two rt hashes DIFFER (2nd reading)",
            "hashes_differ")),
    "H3": (("MATCH verdicts (the gate: 61)", "headline"),
           ("pairs of exactly one (the gate: 61)", "pairs_of_one"),
           ("word/exit disagreements (2nd reading)",
            "word_and_exit_disagree"),
           ("pairs with a NON-empty R2 exclusion list (2nd reading)",
            "excluded_children")),
    "H4": (("the printed session set (the gate: the preflight's pin)",
            "session_names"),
           ("K (the gate: the pin's size)", "session_k"),
           ("withholdings citing a session key (the gate: none)",
            "withholding_cites_a_session_key")),
    "H5": (("arm B WITHHELD (the gate: 4)", "headline"),
           ("caveats naming the key (the gate: 4)",
            "env_caveat_names_the_key"),
           ("the pager row's thread reason survived (2nd reading)",
            "thread_reason_kept")),
    "H6": (("arm C's word equals arm A's (the gate: 4)", "headline"),
           ("the printed session set (the gate: the pin ∪ the key)",
            "session_names"),
           ("K (the gate: one greater)", "session_k"),
           ("the injected key (2nd reading; DERIVED from the pin)",
            "injected_key")),
    "H7": (("partition cells NULL on a printed licence (the gate: 0)",
            "headline"),
           ("every count carries its source line", "counts_carry_their_"
            "source_line"),
           ("the verified/unverifiable counts (non-null)",
            "licence_verified_counts"),
           ("the version probe", "version_probe")),
    "H8": (("corpus exit", "corpus_rc"),
           ("`refocus_spawned_test_fn` present", "spawned_test_fn_present"),
           ("Python suite exit", "pytest_rc"),
           ("`cargo test --workspace` exit", "cargo_rc"),
           ("the Python suite's summary (reported)", "pytest_summary")),
}


def _yn(v) -> str:
    return "not recorded" if v is None else ("yes" if v else "no")


def _empty(v) -> str:
    return "empty" if not v else "DIRTY"


def environment(r) -> list[str]:
    env, bl = r.get("environment") or {}, r.get("byte_lock") or {}
    rows_lock = r.get("rows_digest") or {}
    bf = env.get("built_from") or {}
    probe = env.get("sensorium_version_metadata_probe") or {}
    parity = env.get("session_parity") or {}
    out = [
        "## 2. Environment", "",
        f"Measured {r.get('started')} → {r.get('finished')} by "
        f"`{r.get('runner')}`, launched detached; the raw facts are "
        f"`results-e4pp-raw.json` in the gitignored plan ledger, with every "
        f"command's log beside it. §3 is rendered from this document's "
        f"`results.json`, which `acceptance_e4pp_schema.assemble_e4pp` "
        f"derived from that raw file.", "",
        schema_sentence(r), "",
        f"**§1 byte-lock.** The runner refuses to start unless the locked "
        f"range is byte-identical to the commit that locked it. Range "
        f"{bl.get('range')}, checked at `{bl.get('commit')}`: "
        f"{bl.get('locked_bytes')} bytes, sha256 `{bl.get('locked_sha256')}` "
        f"— identical: {_yn(bl.get('identical'))}. The 61-row subject "
        f"sibling is locked by DIGEST: `{rows_lock.get('sha256')}` — "
        f"identical: {_yn(rows_lock.get('identical'))}. §1 has never been "
        f"amended (amended: "
        f"{_yn(bl.get('amended_after_the_original_lock'))}).", ""]
    if r.get("dry_run"):
        out += ["**THIS IS A DRY RUN.** The row table was replaced and no "
                "number below is the measurement.", ""]
    pins = [
        ("repo HEAD at the run",
         f"`{env.get('repo_commit')}` (branch `{env.get('repo_branch')}`); "
         f"porcelain before / after {_empty(env.get('repo_porcelain'))} / "
         f"{_empty(env.get('repo_porcelain_after'))}"),
        ("the clone under measurement (READ-ONLY input)",
         f"`{env.get('clone')}` at `{env.get('clone_head')}`; §1.3's pin "
         f"`{env.get('clone_pin')}`; `Cargo.lock` back on the pin: "
         f"{_yn(env.get('clone_cargo_lock_back_on_the_pin'))}"),
        ("the KEPT E4 store (READ-ONLY input)",
         f"`{env.get('kept_store')}`, {env.get('kept_store_files')} `.db` "
         f"file(s); unchanged across the whole run: "
         f"{_yn(env.get('kept_store_unchanged'))}"
         + (f" — differences: {env.get('kept_census_differences')}"
            if env.get("kept_census_differences") else "")),
        ("the copy",
         f"§1.3's `VACUUM INTO`, executed by "
         f"{env.get('copy_engine') or 'not recorded'} (SQLite "
         f"{env.get('sqlite_version')}; `sqlite3` CLI on PATH: "
         f"{env.get('sqlite3_cli') or 'none'})"),
        ("the driver",
         f"`{env.get('driver')}` sha256 `{env.get('driver_sha256')}`, built "
         f"by this run from HEAD `{bf.get('repo_head_at_build')}` (rebuilt: "
         f"{_yn(env.get('driver_rebuilt_by_this_run'))}); unchanged after: "
         f"{_yn(env.get('driver_unchanged_after'))}"),
        ("the driver's version token",
         f"`{env.get('driver_version_from_the_trace')}` — read from the "
         f"TRACE's own `meta.driver_version`, never from the instrument"),
        ("the launch guard",
         f"`{parity.get('guard')}`: {parity.get('checked')} original(s) over "
         f"{len(parity.get('compared_keys') or [])} compared key(s); "
         f"differing OUTSIDE session set 1: "
         f"{parity.get('differing') or 'none'} (a difference there is a "
         f"refusal to launch). Session keys differing: "
         f"{env.get('session_keys_differing')} — expected "
         f"{parity.get('expected_session_differs')}, as expected: "
         f"{_yn(parity.get('session_set_as_expected'))}. A different set is "
         f"REPORTED, never a STOP"),
        ("the arms",
         f"B injects `{env.get('arm_b_key')}`; C injects "
         f"`{env.get('injected_session_key')}`, chosen at preflight as the "
         f"first of session set 1's fourteen exact names absent from both "
         f"sides. Rows: {env.get('arm_rows')}"),
        ("the fresh trace store",
         f"`{env.get('sensorium_dir')}`; invocation log "
         f"{env.get('invocations_jsonl_lines')} row(s)"),
        ("the fresh cargo target",
         f"`{env.get('e4pp_target')}`; H8's corpus target "
         f"`{env.get('corpus_target')}` (from an env var: "
         f"{_yn(env.get('corpus_target_from_env'))})"),
        ("`TMPDIR`",
         f"{env.get('tmpdir_observed')!r}; `tempfile.gettempdir()` resolved "
         f"to `{env.get('tempfile_gettempdir')}`"),
        ("no other `cargo` was running",
         f"`{(env.get('cargo_running_check') or {}).get('command')}` → rc "
         f"{(env.get('cargo_running_check') or {}).get('rc')}, pids "
         f"{(env.get('cargo_running_check') or {}).get('pids')}"),
        ("`SENSORIUM_TIER`", str(env.get("sensorium_tier"))),
        ("the invocation audit log", str(env.get("invocation_log"))),
        ("toolchain",
         f"{env.get('rustc')}; {env.get('cargo')}; {env.get('python')}; "
         f"sensorium `{env.get('sensorium_version_metadata')}` in the "
         f"installed distribution metadata"
         + (f" (the probe `{probe.get('command')}` recorded null: "
            f"{probe.get('reason')})" if probe.get("reason") else "")),
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

def _endpoint(r, name) -> list[str]:
    e = (r.get("endpoints") or {}).get(name) or {}
    out = [f"### {name} — {QUESTION[name]}", ""] + list(HEAD)
    for label, key in CELLS[name]:
        out.append(row(label, e.get(key)))
    out += ["", f"Rule: {RULES[name]}. Verdict: **{e.get('verdict')}**"
            f" (as predicted: {_yn(e.get('as_predicted'))}).", ""]
    out += _notes(name, e)
    return out


def _notes(name, e) -> list[str]:
    """One sentence per endpoint carrying what its table cannot."""
    if name == "H1":
        return [f"Withheld only here: {e.get('withheld_only_here') or 'none'}"
                f"; withheld missing: {e.get('withheld_missing') or 'none'}; "
                f"count mismatches: "
                f"{e.get('withheld_count_mismatches') or 'none'}. Harness "
                f"phrase(s): {e.get('harness_phrases') or 'none'}. Pairs "
                f"whose licence could not be read: "
                f"{e.get('unread') or 'none'}.", ""]
    if name == "H2":
        return [f"Expected relocated set: "
                f"{e.get('expected_relocated_set')}; sets seen: "
                f"{e.get('relocated_sets_seen')}; pairs matching: "
                f"{e.get('relocated_set_matches')}. Pairs naming "
                f"`RUSTDOCFLAGS` as changed: "
                f"{e.get('rustdocflags_in_changed_pairs') or 'none'}; pairs "
                f"whose strip clause was silent: "
                f"{e.get('strip_clause_missing') or 'none'}. **Pairs whose "
                f"two rt hashes were EQUAL — a strip that pair could not "
                f"have tested:** "
                + str(e.get("hashes_equal_so_the_strip_was_untested")
                      or "none") + ".", ""]
    if name == "H3":
        return [f"Non-MATCH: {e.get('non_match') or 'none'}. Pair counts "
                f"other than 1: {e.get('not_one') or 'none'}. The pair is "
                f"read from the STORE, by THAT invocation's launch "
                f"timestamp, and the printed id is a cross-check beside it.",
                ""]
    if name == "H4":
        return [f"The pin (recorded at preflight, before any refocus): "
                f"{e.get('pin')} (n {e.get('pin_n')}); names matching on "
                f"{e.get('session_names_match')} pair(s), K on "
                f"{e.get('session_k_match')}. Decided on K alone: "
                f"{_yn(e.get('decided_on_k_alone'))}. Pairs with an EMPTY "
                f"session set: {e.get('pairs_with_an_empty_session_set')}.",
                "",
                f"The line on a granted pair: "
                f"`{e.get('line_on_a_granted_pair')}`.", ""]
    if name == "H5":
        return [f"Key: `{e.get('key')}`. Granted lines (any is a STOP): "
                f"{e.get('granted') or 'none'}; WITHHELD without the key "
                f"named: {e.get('env_caveat_missing_the_key') or 'none'}. "
                f"Arm B's verdicts (REPORTED, never a gate): "
                f"{e.get('verdicts')}.", ""]
    if name == "H6":
        choice = e.get("injected_key_choice") or {}
        return [f"Expected set: {e.get('expected_session_names')} (K "
                f"{e.get('expected_k')}); names matching on "
                f"{e.get('session_names_match')} pair(s), K on "
                f"{e.get('session_k_match')}. Words that MOVED: "
                f"{e.get('word_moved') or 'none'}. The choice skipped "
                + str([s.get("name") for s in choice.get("skipped") or []]
                      or "none")
                + f" — {choice.get('rule')}.", ""]
    if name == "H7":
        return [f"Null partition cells: {e.get('null_cells') or 'none'}; "
                f"counts with no source line: "
                f"{e.get('counts_without_a_source_line') or 'none'}. Probe "
                f"reason: {e.get('version_probe_reason') or 'none'}. Every "
                f"`dropped` list this run wrote: "
                f"{e.get('dropped_lists') or 'none'}. A miss here is a STOP "
                f"of the {e.get('stop_is_of_the')}.", ""]
    return [f"Corpus: {e.get('corpus_cases')} case(s), args "
            f"{e.get('corpus_args')}, require_driver "
            f"{_yn(e.get('corpus_require_driver'))}; failures "
            f"{e.get('corpus_failures') or 'none'}; errors "
            f"{e.get('corpus_errors') or 'none'}; skipped "
            f"{e.get('corpus_skipped') or 'none'}. Rust result lines: "
            f"{e.get('cargo_result_lines') or 'none'}.", ""]


def ungated(r) -> list[str]:
    """§1.5's reported-without-a-gate block, compact."""
    rep = r.get("reported") or {}
    rt, walls = rep.get("rt_hashes") or {}, rep.get("walls_s") or {}
    sess, store = rep.get("session_set") or {}, rep.get("store") or {}
    kept = rep.get("kept_store_unchanged") or {}
    counts = rep.get("licence_verified_counts") or {}
    out = ["### Reported without a gate", "",
           f"**The two tool hashes.** {rt.get('pairs_whose_hashes_differ')} "
           f"pair(s) carried DIFFERENT rt hashes on their two sides; "
           f"{len(rt.get('pairs_whose_hashes_were_equal') or [])} carried "
           f"equal ones. {rt.get('note')}.", "",
           f"**K and its names.** Pin {sess.get('pin')} (n "
           f"{sess.get('pin_n')}), expected {sess.get('expected')}, as "
           f"expected: {_yn(sess.get('as_expected'))}; injected "
           f"`{sess.get('injected')}`. {sess.get('note')}.", "",
           f"**Wall per arm.** " + "; ".join(
               f"{a}: first {(walls.get(a) or {}).get('first_focus')} s, "
               f"later mean {(walls.get(a) or {}).get('later_focus_mean')} s "
               f"over {(walls.get(a) or {}).get('n')}"
               for a in ("A", "B", "C")) + f". {walls.get('note')}.", "",
           f"**The four verified/unverifiable counts, in kind and never "
           f"summed.** source {counts.get('source_verified')}, environment "
           f"{counts.get('env_verified')}, exit "
           f"{counts.get('exit_verified')} verified; output "
           f"{counts.get('output_unverifiable')}, children "
           f"{counts.get('children_unverifiable')} UNVERIFIABLE by "
           f"construction, over n {counts.get('n')}.", "",
           f"**The store.** {store.get('copies')} original(s) copied, "
           f"{store.get('bytes_copied')} byte(s), by {store.get('engine')}; "
           f"the fresh store held {store.get('fresh_listing_n')} file(s) "
           f"when the loop opened and only the copies: "
           f"{_yn(store.get('fresh_holds_only_the_copies'))}; "
           f"{store.get('traces_in_the_fresh_store')} trace(s) at the end. "
           f"The KEPT store: {kept.get('before')} file(s) before, "
           f"{kept.get('after')} after; identical: "
           f"{_yn(kept.get('identical'))}. The invocation log: "
           f"{rep.get('invocation_log_rows')} row(s) — this record's own.",
           ""]
    arm_b = rep.get("arm_b_verdicts") or {}
    out += [f"**Arm B's verdicts.** {arm_b.get('verdicts')}. "
            f"{arm_b.get('note')}.", ""]
    return out


def results(r) -> list[str]:
    out = ["## 3. Results", "", "The gate of each row, and both readings "
           "where §1 pre-committed two. A `null` is not-measured with its "
           "reason; `0` is a measured zero; a KILLED cell has no numeric "
           "reading at all. The per-pair tables are in `results.json`.", ""]
    for name in ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"):
        out += _endpoint(r, name)
    out += ungated(r)
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
        / "acceptance" / "2026-09-08-sensorium-rung4-e4pp.results.json")
    doc = json.loads(Path(path).read_text())
    print("\n".join(environment(doc) + [""] + results(doc)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


__all__ = ["CELLS", "HEAD", "QUESTION", "RULES", "environment", "main",
           "results", "ungated"]
