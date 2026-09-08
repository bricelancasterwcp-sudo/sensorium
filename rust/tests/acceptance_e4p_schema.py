#!/usr/bin/env python3
"""Raw E4′ facts -> the acceptance document's `results.json`.

The assembler decides nothing the runner did not measure. Its jobs are three:
carry the raw record's own `schema_version` and stamp its own beside it
(R4); apply the drop rules once per endpoint (`acceptance_e4p_cells`); and
publish §1's predictions under their OWN names, as comparison targets that no
cell can fall back to.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4p_cells import ENDPOINTS                        # noqa: E402
from acceptance_e4p_cells import killed_cell                      # noqa: E402
from acceptance_e4p_rows import (EXPECTED_EXCLUDED_CHILDREN,      # noqa: E402
                                 EXPECTED_GRANTED,
                                 EXPECTED_HARNESS_THREADS,
                                 EXPECTED_MATCH, EXPECTED_PAIRS_OF_ONE,
                                 EXPECTED_SHIM_KEYS, EXPECTED_WITHHELD,
                                 GATE_N)

DOC = "docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md"

#: R4: the schema THIS assembler writes. The raw record's own token is
#: COPIED into `schema_version`; this one is stamped beside it, so a record
#: re-derived under a later schema is distinguishable from one derived under
#: its own.
SCHEMA_VERSION = "e4p/1"


def _predictions(raw) -> dict:
    """§1.2's numbers, published under their own names.

    They are in the room and a headline that borrowed from one could not
    fail, so they are never a value a cell falls back to. What they are for
    is the comparison beside each endpoint: `granted 57` next to the granted
    count actually read.
    """
    return {
        "source": "§1.1 and §1.2 of the byte-locked pre-registration",
        "gate_n": GATE_N,
        "granted": len(EXPECTED_GRANTED),
        "withheld": dict(sorted(EXPECTED_WITHHELD.items())),
        "harness_threads_per_pair": EXPECTED_HARNESS_THREADS,
        "match": EXPECTED_MATCH,
        "pairs_of_one": EXPECTED_PAIRS_OF_ONE,
        "excluded_children": EXPECTED_EXCLUDED_CHILDREN,
        "shim_keys": EXPECTED_SHIM_KEYS,
        "recorded_before_any_phase_ran": bool(raw.get("predictions")),
    }


def _pairs(raw) -> dict:
    """The 61 rows, one per original, whatever happened to each.

    A row that was KILLED at its ceiling, or never reached because the loop
    bound arrived, is STRUCTURAL: `{"killed": true, "reason": …}` in the
    place a number would be. Not `0`, not `""`, not an empty list -- each of
    those is a value a reader or a later sum takes for a measured one.
    """
    two = raw.get("raw_pass2") or {}
    rows = []
    for r in two.get("refocuses") or []:
        row = {"index": r.get("index"), "name": r.get("name"),
               "target": r.get("target"), "original": r.get("original")}
        if r.get("not_run"):
            row["measured"] = killed_cell(r["not_run"])
            rows.append(row)
            continue
        if r.get("timed_out"):
            row["measured"] = killed_cell(
                f"the invocation was KILLED at its {r.get('kill_s')} s "
                f"ceiling; its output is partial (kill: {r.get('kill')})")
        part = r.get("licence_partition") or {}
        row.update({
            "pair": r.get("new_run"),
            "pair_count": (r.get("pair") or {}).get("n"),
            "excluded_children": r.get("excluded_children_in_the_store"),
            "verdict": r.get("verdict_word"),
            "exit": r.get("rc"),
            "verdict_and_exit_agree": r.get("verdict_and_exit_agree"),
            "licence": part.get("licence"),
            "program_threads": part.get("program_threads"),
            "harness_threads": part.get("harness_threads"),
            "names_the_exclusion": part.get("names_the_exclusion"),
            "sides_agree": part.get("sides_agree"),
            "licence_line": r.get("licence_line"),
            "licence_facts": r.get("licence_facts"),
            "licence_caveats": r.get("licence_caveats"),
            "threads_line": r.get("threads_line"),
            "unverifiable": r.get("unverifiable"),
            "licence_counts": r.get("licence"),
            # Task 5b's two readings of the env line, kept apart. §1.4 gives
            # the re-run a FRESH target, so the keys cargo derives from the
            # root differ on EVERY pair; the relocated list is what the rule
            # explained, and `env_changed_for_other_keys` is whether the
            # clause fired for anything it did not.
            "env_status": r.get("env_status"),
            "env_relocated_keys": r.get("env_relocated_keys"),
            "env_changed_keys": r.get("env_changed_keys"),
            "env_changed_for_other_keys": r.get("env_changed_for_other_keys"),
            "env_line": r.get("env_line"),
            "driver_version_from_the_trace": r.get(
                "driver_version_from_the_trace"),
            "wall_s": r.get("wall_s"),
            "cargo_finished_s": r.get("cargo_finished_s"),
            "trace_bytes": r.get("new_trace_bytes"),
            "log": r.get("log"),
        })
        rows.append(row)
    return {"n": len(rows), "rows": rows}


def _env_reading(two: dict) -> dict:
    """Task 5b's clause over the whole run, reported and never gated.

    Two numbers that must not be added: how many pairs had a key the
    target-root rule EXPLAINED, and how many had a key it did not. The
    second is the one that still withholds a licence, and the expectation
    written into 5b is that it is zero here -- but it is published as
    measured either way, with the pairs named.
    """
    rows = [r for r in (two.get("refocuses") or []) if "not_run" not in r]
    relocated = {r["name"]: r.get("env_relocated_keys") for r in rows
                 if r.get("env_relocated_keys")}
    other = {r["name"]: r.get("env_changed_keys") for r in rows
             if r.get("env_changed_for_other_keys")}
    unread = [r["name"] for r in rows if r.get("env_line") is None]
    keys = sorted({k for v in relocated.values() for k in (v or [])})
    return {
        "pairs_with_a_relocated_target": len(relocated),
        "relocated_keys_seen": keys,
        "relocated_by_pair": relocated,
        "pairs_changed_for_another_key": len(other),
        "changed_keys_by_pair": other,
        "pairs_whose_env_line_was_not_read": unread,
        "note": ("a re-run from another target directory is a normal use of "
                 "the tool (design 2026-09-07, `refocus_env`); a key that "
                 "moved for any OTHER reason is a change and still "
                 "withholds"),
    }


def licence_verified_counts(raw) -> dict | None:
    """§1.2's four verified/unverifiable counts, COUNTED FROM THE ROWS.

    E4′ §5's gap 7: this block used to read a TOP-LEVEL
    `licence_verified_counts` the runner never writes, so the record named
    a field every reader found `null` while the data sat one level down,
    per row, under `raw_pass2.refocuses[*].licence` (`licence_counts`'s
    output).

    Counted, never SUMMED. `source` and `env` are checks that ran; `output`
    and `children` are UNVERIFIABLE by construction on a Rust pair; §1.4
    binds this record to reporting them in kind, so there is no
    `verified_total` key here and there never will be.

    `None` -- not five zeroes -- when no row carries a reading. A loop that
    read nothing has no counts, and `0` there is a check that ran and found
    nothing, which is a different claim.
    """
    two = raw.get("raw_pass2") or {}
    rows = [r.get("licence") for r in (two.get("refocuses") or [])
            if "not_run" not in r and isinstance(r.get("licence"), dict)]
    if not rows:
        return None
    return {
        "source_verified": sum(1 for c in rows if c.get("source_verified")),
        "env_verified": sum(1 for c in rows if c.get("env_verified")),
        "exit_verified": sum(1 for c in rows if c.get("exit_verified")),
        "output_unverifiable": sum(1 for c in rows
                                   if c.get("output_unverifiable")),
        "children_unverifiable": sum(1 for c in rows
                                     if c.get("children_unverifiable")),
        "n": len(rows),
        "note": ("counted over the rows that came back with a licence "
                 "reading; source and environment are checks that RAN, "
                 "output and children are UNVERIFIABLE by construction on a "
                 "Rust pair, and the two kinds are never summed"),
    }


def _reported(raw) -> dict:
    """§1.4's "reported without a gate" list, whole."""
    two = raw.get("raw_pass2") or {}
    h1, h4 = raw.get("raw_h1") or {}, raw.get("raw_h4") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    pins = raw.get("pins") or {}
    walls = [r.get("wall_s") for r in (two.get("refocuses") or [])
             if r.get("wall_s") is not None]
    return {
        "licence_wording": {
            "harness_phrases": h1.get("harness_phrases"),
            "harness_threads_by_name": h1.get("harness_threads_by_name"),
            "hides_the_exclusion": h1.get("hides_the_exclusion"),
            "reasons_that_never_subtracted": h1.get(
                "reasons_that_never_subtracted"),
            "sides_disagree": h1.get("sides_disagree"),
        },
        "shim_census": {
            "entries": h4.get("entries"),
            "distinct_inodes": h4.get("distinct_inodes"),
            "bytes_once_per_inode": h4.get("bytes_once_per_inode"),
            "note": ("the three numbers are printed separately; the byte "
                     "total is never the sum of the per-entry sizes"),
        },
        "walls_s": {
            "first_focus": walls[0] if walls else None,
            "later_focus": walls[1:] if len(walls) > 1 else [],
            "later_focus_mean": (round(sum(walls[1:]) / len(walls[1:]), 3)
                                 if len(walls) > 1 else None),
            "later_focus_max": max(walls[1:]) if len(walls) > 1 else None,
            "note": "nothing is gated on a wall",
        },
        "cargo_build_s": {r.get("name"): r.get("cargo_finished_s")
                          for r in (two.get("refocuses") or [])
                          if r.get("cargo_finished_s")},
        "env_relocation": _env_reading(two),
        "licence_verified_counts": licence_verified_counts(raw),
        "store": {
            "copies": (raw.get("store") or {}).get("copied"),
            "bytes_copied": (raw.get("store") or {}).get("bytes_copied"),
            "engine": (raw.get("store") or {}).get("engines"),
            "sqlite_version": (raw.get("store") or {}).get("sqlite_version"),
            "fresh_listing_n": (raw.get("store") or {}).get(
                "fresh_listing_n"),
            "fresh_holds_only_the_copies": (raw.get("store") or {}).get(
                "fresh_holds_only_the_copies"),
            "refocused_trace_bytes": {
                r.get("name"): r.get("new_trace_bytes")
                for r in (two.get("refocuses") or [])
                if r.get("new_trace_bytes")},
            "store_bytes_after": cl.get("store_bytes_after"),
        },
        "kept_store_unchanged": {
            "before": (raw.get("kept_census_before") or {}).get("n"),
            "after": cl.get("kept_census_after_n"),
            "differences": cl.get("kept_census_differences"),
            "identical": cl.get("kept_store_unchanged"),
        },
        "invocation_log_rows": cl.get("invocations_jsonl_lines"),
        "disk_free_gb": {
            "repo_before": pins.get("repo_disk_free_gb"),
            "repo_after": cl.get("repo_disk_free_gb_after"),
            "target_before": pins.get("target_disk_free_gb"),
            "target_after": cl.get("target_disk_free_gb_after")},
        "load_at_each_phase": raw.get("arm_loads"),
    }


def assemble_e4p(raw: dict) -> dict:
    """Raw E4′ facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    store = raw.get("store") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero; a KILLED cell is {killed, reason} "
                   "and has no numeric reading at all"),
        # COPIED from the raw record, never asserted (R4).
        "schema_version": raw.get("schema_version"),
        "assembled": {"schema_version": SCHEMA_VERSION},
        # DERIVED from the raw record's own byte-lock, with the module
        # constant only as the last resort for a run refused before the
        # check -- where there is nothing to derive from (R-G15).
        "acceptance": ((raw.get("byte_lock") or {}).get("doc")
                       or raw.get("document") or DOC),
        "runner": raw.get("runner"),
        "dry_run": raw.get("dry_run", False),
        # §1.4's rules 4 and 5 turn on this and on nothing else: a `.FAILED`
        # BEFORE any number is infrastructure (relaunch from zero, the
        # copies re-made), AFTER one is a STOP and the numbers already read
        # stand. Carried as a FIELD so the distinction is mechanical rather
        # than a judgement a reader makes from which `raw_*` blocks exist.
        "numbers_read": bool(raw.get("numbers_read")),
        "numbers_read_at": raw.get("numbers_read_at"),
        "numbers_read_because": raw.get("numbers_read_because"),
        "byte_lock": raw.get("byte_lock"),
        "pins": pins,
        "environment": {
            "repo_commit": pins.get("repo_commit"),
            "repo_branch": pins.get("repo_branch"),
            "repo_porcelain": pins.get("repo_porcelain"),
            "repo_porcelain_after": cl.get("repo_porcelain_after"),
            "clone": pins.get("clone"),
            "clone_head": pins.get("clone_head"),
            "clone_pin": pins.get("clone_pin"),
            "clone_head_after": cl.get("clone_head_after"),
            "clone_porcelain": pins.get("clone_porcelain"),
            "clone_porcelain_after": cl.get("clone_porcelain_after"),
            "clone_cargo_lock_sha256": pins.get("clone_cargo_lock_sha256"),
            "clone_cargo_lock_sha256_after": cl.get(
                "clone_cargo_lock_sha256_after"),
            "clone_cargo_lock_moved": cl.get("clone_cargo_lock_moved"),
            "clone_cargo_lock_back_on_the_pin": cl.get(
                "clone_cargo_lock_back_on_the_pin"),
            "kept_store": pins.get("kept_store"),
            "kept_store_read_only_reading": pins.get(
                "kept_store_read_only_reading"),
            "kept_store_files": (raw.get("kept_census_before") or {}).get("n"),
            "kept_store_unchanged": cl.get("kept_store_unchanged"),
            "kept_census_differences": cl.get("kept_census_differences"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_sha256_after": cl.get("driver_sha256_after"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "driver_rebuilt_by_this_run": pins.get(
                "driver_rebuilt_by_this_run"),
            "built_from": pins.get("built_from"),
            # §1.4's version rule: read from the TRACE, never hard-coded.
            "driver_version_from_the_trace": pins.get(
                "driver_version_from_the_trace"),
            "transform_version": pins.get("transform_version"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "sensorium_version_metadata": pins.get(
                "sensorium_version_metadata"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "e4p_target": pins.get("e4p_target"),
            "rust_target": pins.get("rust_target"),
            "corpus_target": pins.get("corpus_target"),
            # Recorded in `pins`, READ by §2, and until now absent from
            # here — so the lens section printed "not recorded" for a fact
            # the run had recorded. E9 and E4 both carry it; carried rather
            # than dropped, because the renderer uses it.
            "corpus_target_from_env": pins.get("corpus_target_from_env"),
            # The two preflight guards, whose passing is itself a lens fact:
            # a check that leaves no trace when it passes cannot be audited.
            "cargo_running_check": pins.get("cargo_running_check"),
            "env_parity": pins.get("env_parity"),
            "tmpdir_observed": pins.get("tmpdir_observed"),
            "tempfile_gettempdir": pins.get("tempfile_gettempdir"),
            "tmpdir_reading": pins.get("tmpdir_reading"),
            "sensorium_tier": pins.get("sensorium_tier"),
            "invocation_log": pins.get("invocation_log"),
            "invocations_jsonl_lines": cl.get("invocations_jsonl_lines"),
            "sqlite3_cli": store.get("sqlite3_cli"),
            "sqlite_version": store.get("sqlite_version"),
            "copy_engine": store.get("engines"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_phase": raw.get("arm_loads"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "repo_disk_free_gb_after": cl.get("repo_disk_free_gb_after"),
            "target_disk_free_gb": pins.get("target_disk_free_gb"),
            "target_disk_free_gb_after": cl.get("target_disk_free_gb_after"),
            "timeouts": {k: (raw.get("config") or {}).get(k) for k in
                         ("refocus_timeout", "loop_budget_s",
                          "corpus_timeout", "pytest_timeout",
                          "cargo_test_timeout")},
            "logs_dir": raw.get("logs"),
        },
        "store": store,
        "pairs": _pairs(raw),
        "endpoints": {name: fn(raw) for name, fn in ENDPOINTS.items()},
        "predictions": _predictions(raw),
        "reported": _reported(raw),
        "cleanup": cl or None,
        "steps": raw.get("steps"),
        "stop": raw.get("stop"),
        "bound_reached": raw.get("bound_reached"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }


__all__ = ["DOC", "SCHEMA_VERSION", "assemble_e4p",
           "licence_verified_counts"]
