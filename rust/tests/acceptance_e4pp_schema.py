#!/usr/bin/env python3
"""Raw E4″ facts -> the acceptance document's `results.json`.

The assembler decides nothing the runner did not measure. Its jobs are
three: carry the raw record's own `schema_version` and stamp its own beside
it (R4); apply the drop rules once per endpoint
(`acceptance_e4pp_cells`); and publish §1's predictions under their OWN
names, as comparison targets that no cell can fall back to.

E4′'s `results.json` is NEVER re-assembled by this module. That record is
closed; `schema_version` is what tells a record derived under its own
schema from one re-derived later, and the derivation is stated rather than
rewritten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4pp_rows as e4pp                                # noqa: E402
from acceptance_e4p_cells import killed_cell                       # noqa: E402
from acceptance_e4p_schema import licence_verified_counts          # noqa: E402
from acceptance_e4pp_cells import ENDPOINTS                        # noqa: E402

DOC = "docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md"

#: R4: the schema THIS assembler writes. The raw record's own token is
#: COPIED into `schema_version`; this one is stamped beside it, so a record
#: re-derived under a later schema is distinguishable from one derived
#: under its own.
SCHEMA_VERSION = "e4pp/1"


def _predictions(raw) -> dict:
    """§1.2's and §1.4's numbers, published under their own names.

    They are in the room and a headline that borrowed from one could not
    fail, so they are never a value a cell falls back to. What they are for
    is the comparison beside each endpoint.
    """
    return {
        "source": "§1.1, §1.2 and §1.4 of the byte-locked pre-registration",
        "gate_n": e4pp.GATE_N,
        "granted": len(e4pp.EXPECTED_GRANTED),
        "withheld": dict(sorted(e4pp.EXPECTED_WITHHELD.items())),
        "harness_threads_per_pair": e4pp.EXPECTED_HARNESS_THREADS,
        "match": e4pp.EXPECTED_MATCH,
        "pairs_of_one": e4pp.EXPECTED_PAIRS_OF_ONE,
        "excluded_children": e4pp.EXPECTED_EXCLUDED_CHILDREN,
        "relocated_set": list(e4pp.EXPECTED_RELOCATED),
        "strip_key": e4pp.STRIP_KEY,
        "strip_clause_named": e4pp.EXPECTED_STRIP_CLAUSE_NAMED,
        "rustdocflags_in_changed": e4pp.EXPECTED_RUSTDOCFLAGS_IN_CHANGED,
        "arm_n": e4pp.ARM_N,
        "spawned_case": e4pp.SPAWNED_CASE,
        "recorded_before_any_phase_ran": bool(raw.get("predictions")),
    }


def _pair_row(r: dict) -> dict:
    """One refocus, whatever happened to it.

    A row KILLED at its ceiling, or never reached, is STRUCTURAL:
    `{"killed": true, "reason": …}` where a number would be. Not `0`, not
    `""`, not an empty list -- each of those is a value a reader or a later
    sum takes for a measured one.
    """
    row = {"index": r.get("index"), "name": r.get("name"),
           "arm": r.get("arm") or "A", "original": r.get("original")}
    if r.get("not_run"):
        row["measured"] = killed_cell(r["not_run"])
        return row
    if r.get("timed_out"):
        row["measured"] = killed_cell(
            f"the invocation was KILLED at its {r.get('kill_s')} s ceiling; "
            f"its output is partial (kill: {r.get('kill')})")
    part = r.get("licence_partition") or {}
    row.update({
        "pair": r.get("new_run"),
        "pair_count": (r.get("pair") or {}).get("n"),
        "verdict": r.get("verdict_word"), "exit": r.get("rc"),
        "verdict_and_exit_agree": r.get("verdict_and_exit_agree"),
        "licence": part.get("licence"),
        "program_threads": part.get("program_threads"),
        "harness_threads": part.get("harness_threads"),
        "counts_source": part.get("counts_source"),
        "counts_unread_reason": part.get("counts_unread_reason"),
        "names_the_exclusion": part.get("names_the_exclusion"),
        "env_status": r.get("env_status"),
        "env_stripped_keys": r.get("env_stripped_keys"),
        "env_relocated_keys": r.get("env_relocated_keys"),
        "env_changed_keys": r.get("env_changed_keys"),
        "env_session_keys": r.get("env_session_keys"),
        "env_session_n": r.get("env_session_n"),
        "env_session_keys_truncated": r.get("env_session_keys_truncated"),
        "env_line": r.get("env_line"),
        "extra_env": r.get("extra_env"),
        "original_rt_hash": (r.get("original_rt_hash") or {}).get("value"),
        "rerun_rt_hash": (r.get("rerun_rt_hash") or {}).get("value"),
        "driver_version_from_the_trace": r.get(
            "driver_version_from_the_trace"),
        # The copied ORIGINAL's own token, beside the re-run's and beside
        # the rt-hash pair (E4″ gap 3): `null` WITH its reason, never a
        # blank that reads as "the two agree".
        "driver_version_from_the_original": (
            r.get("original_driver_version") or {}).get("value"),
        "driver_version_from_the_original_reason": (
            r.get("original_driver_version") or {}).get("reason"),
        "wall_s": r.get("wall_s"), "trace_bytes": r.get("new_trace_bytes"),
        "log": r.get("log"),
    })
    return row


def _pairs(raw) -> dict:
    """Every row of every arm, one table, each carrying its arm."""
    rows = []
    for key in ("raw_pass2", "raw_arm_b", "raw_arm_c"):
        for r in (raw.get(key) or {}).get("refocuses") or []:
            rows.append(_pair_row(r))
    return {"n": len(rows), "rows": rows,
            "by_arm": {a: sum(1 for r in rows if r["arm"] == a)
                       for a in sorted({r["arm"] for r in rows})}}


#: The three arms, in §1.5's order, and the raw block each one wrote.
ARMS = (("raw_pass2", "A"), ("raw_arm_b", "B"), ("raw_arm_c", "C"))


def _summary(walls: list) -> dict:
    """One arm's walls, the FIRST focus apart from the later ones -- the
    first pays for a cold build and averaging it in hides both numbers."""
    return {"first_focus": walls[0] if walls else None,
            "later_focus_mean": (round(sum(walls[1:]) / len(walls[1:]), 3)
                                 if len(walls) > 1 else None),
            "later_focus_max": max(walls[1:]) if len(walls) > 1 else None,
            "n": len(walls)}


def _arm_walls(raw) -> dict:
    """§1.5's wall per arm, the first focus distinguished from the later
    ones. Reported; nothing here is gated on a wall."""
    return {label: _summary([r.get("wall_s")
                             for r in (raw.get(key) or {}).get("refocuses")
                             or [] if r.get("wall_s") is not None])
            for key, label in ARMS}


def _cargo_walls(raw) -> dict:
    """Cargo's OWN time inside each focus, per arm.

    §1.5 asks for the arm walls "with cargo's own build time inside each",
    and this run recorded it per row -- `cargo_finished_s`, a LIST, because
    one `sensorium refocus` can drive more than one cargo invocation -- and
    never gathered it anywhere (E4″ gap 5). Summed per row, then summarised
    like the arm walls. Rows that printed no `Finished in` line are counted
    apart rather than entering the mean as zeros.
    """
    out = {}
    for key, label in ARMS:
        rows = [r for r in (raw.get(key) or {}).get("refocuses") or []
                if "not_run" not in r]
        per_row = [round(sum(v), 3) for r in rows
                   if (v := r.get("cargo_finished_s"))]
        out[label] = dict(_summary(per_row),
                          rows_without_a_cargo_time=len(rows) - len(per_row))
    return out


def _driver_build_wall(raw) -> dict:
    """The driver build's own wall, apart from every focus (§1.5).

    Recorded by the preflight as `pins.built_from.cargo_wall_s` and never
    carried into `reported` (E4″ gap 5). `rebuilt` beside it, because 0.025
    s means something different when nothing was rebuilt.
    """
    built = (raw.get("pins") or {}).get("built_from") or {}
    return {"value": built.get("cargo_wall_s"),
            "rebuilt": built.get("rebuilt"),
            "reason": (None if built.get("cargo_wall_s") is not None
                       else "the preflight recorded no driver build wall")}


def _dry_walls(raw) -> dict:
    """The DRY run's walls, from the record the dry launch wrote.

    §1.5's fourth wall. A dry run measures nothing about the subject, so
    its walls are not among this run's rows: they stayed in their own
    archived results and never reached the real run's `reported` (E4″ gap
    5). `null` WITH the path this reader looked at where there is no dry
    record beside this one -- a wall nobody read is not a wall of zero.
    """
    if raw.get("dry_run"):
        return {"value": None, "path": None,
                "reason": ("this record IS the dry run, and its own walls "
                           "are `walls_s.A`/`B`/`C` beside this field")}
    path = raw.get("dry_raw")
    if not path:
        return {"value": None, "path": None,
                "reason": "this record names no dry run's raw file"}
    try:
        dry = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        return {"value": None, "path": path,
                "reason": f"the dry run's raw record could not be read: {e}"}
    return {"path": path, "started": dry.get("started"), "reason": None,
            "arms": _arm_walls(dry), "cargo_s": _cargo_walls(dry)}


def _walls(raw) -> dict:
    """The four walls §1.5 names, in one field.

    The bullet pre-commits "wall per arm (A, B, C and the dry run), the
    first focus distinguished from the later ones with cargo's own build
    time inside each, and the driver build's wall separately". Three of the
    four were here and the rest were recorded elsewhere in the raw or in
    another record's -- E4″ gap 5, closed by gathering, never by measuring
    anything new.
    """
    out = _arm_walls(raw)
    out["cargo_s"] = _cargo_walls(raw)
    out["driver_build"] = _driver_build_wall(raw)
    out["dry"] = _dry_walls(raw)
    out["note"] = ("nothing is gated on a wall. §1.5 names four -- the "
                   "three arms and the dry run -- with cargo's own time "
                   "inside each focus and the driver build's wall apart")
    return out


def _reported(raw) -> dict:
    """§1.5's "reported without a gate" list, whole."""
    h2 = raw.get("raw_h2") or {}
    h5 = raw.get("raw_h5") or {}
    h7 = raw.get("raw_h7") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    pins = raw.get("pins") or {}
    store = raw.get("store") or {}
    return {
        "rt_hashes": {
            "by_pair": h2.get("rt_hashes_by_pair"),
            "pairs_whose_hashes_differ": h2.get("hashes_differ"),
            "pairs_whose_hashes_were_equal": h2.get(
                "hashes_equal_so_the_strip_was_untested"),
            "pairs_whose_hashes_were_unread": h2.get("hashes_unread"),
            "pairs_whose_hashes_were_readable": h2.get("hashes_readable"),
            # §1.4's OTHER pre-committed second reading for H2 (E4″ gap 4).
            # `by_pair[*]` carries the per-side counts themselves; these are
            # the summary, `null` WITH its reason where the pairs disagree.
            "fragments_per_side": h2.get("fragments_per_side"),
            "fragments_per_side_reason": h2.get("fragments_reason"),
            "fragments_per_side_seen": h2.get("fragments_seen"),
            "pairs_whose_fragments_were_readable": h2.get(
                "fragments_readable"),
            "note": ("their DIFFERENCE is the proof the two builds are not "
                     "the same build -- the one condition E4′ could not "
                     "create; a pair whose two hashes were EQUAL is a pair "
                     "whose strip was never tested, and a pair whose hash "
                     "could not be READ is on neither list -- counted as "
                     "'not differing' an unreadable run and a single-build "
                     "run would print the same number"),
        },
        "driver_version": {
            "from_the_trace": pins.get("driver_version_from_the_trace"),
            "from_the_original_trace": pins.get(
                "driver_version_from_the_original"),
            "built": (pins.get("built_from") or {}).get("driver"),
            "sha256": pins.get("driver_sha256"),
            "note": ("read from each trace's own `meta.driver_version` -- "
                     "the RE-RUN's and, since E4″ gap 3, the copied "
                     "ORIGINAL's, so the pair is two readings and not one "
                     "-- and from the built driver's recorded version, "
                     "never from the tokens §1.3 expects. `meta.recorder` "
                     "is the RUNTIME's version and is a different key; §1.5 "
                     "names it, and this is the key the reader takes"),
        },
        "session_set": {
            "pin": pins.get("session_keys_differing"),
            "pin_n": pins.get("session_keys_differing_n"),
            "expected": pins.get("expected_session_keys_differing"),
            "as_expected": pins.get("session_set_as_expected"),
            "injected": pins.get("injected_session_key"),
            "injected_choice": pins.get("injected_session_key_choice"),
            "k_by_pair_arm_a": (raw.get("raw_h4") or {}).get(
                "session_k_by_name"),
            "k_by_pair_arm_c": (raw.get("raw_h6") or {}).get(
                "session_k_by_name"),
            "note": ("a differing set other than the expected one is "
                     "REPORTED, never a STOP: the launch shell is the "
                     "instrument's, not the subject's (§1.3's rule 3)"),
        },
        "walls_s": _walls(raw),
        "arm_b_verdicts": {
            "verdicts": h5.get("verdicts"),
            "note": ("a variable the program actually READ would change the "
                     "re-run's behaviour, so arm B's verdicts may not all "
                     "be MATCH. That is a FINDING, not a gate"),
        },
        "licence_verified_counts": licence_verified_counts(raw),
        "dropped_lists": h7.get("dropped_lists"),
        "store": {
            "copies": store.get("copied"),
            "bytes_copied": store.get("bytes_copied"),
            "engine": store.get("engines"),
            "sqlite_version": store.get("sqlite_version"),
            "fresh_listing_n": store.get("fresh_listing_n"),
            "fresh_holds_only_the_copies": store.get(
                "fresh_holds_only_the_copies"),
            "store_bytes_after": cl.get("store_bytes_after"),
            "traces_in_the_fresh_store": cl.get("traces_in_the_fresh_store"),
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


def _environment(raw) -> dict:
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    store = raw.get("store") or {}
    return {
        "repo_commit": pins.get("repo_commit"),
        "repo_branch": pins.get("repo_branch"),
        "repo_porcelain": pins.get("repo_porcelain"),
        "repo_porcelain_after": cl.get("repo_porcelain_after"),
        "clone": pins.get("clone"), "clone_head": pins.get("clone_head"),
        "clone_pin": pins.get("clone_pin"),
        "clone_head_after": cl.get("clone_head_after"),
        "clone_porcelain": pins.get("clone_porcelain"),
        "clone_porcelain_after": cl.get("clone_porcelain_after"),
        "clone_cargo_lock_sha256": pins.get("clone_cargo_lock_sha256"),
        "clone_cargo_lock_back_on_the_pin": cl.get(
            "clone_cargo_lock_back_on_the_pin"),
        "kept_store": pins.get("kept_store"),
        "kept_store_read_only_reading": pins.get(
            "kept_store_read_only_reading"),
        "kept_store_files": (raw.get("kept_census_before") or {}).get("n"),
        "kept_store_unchanged": cl.get("kept_store_unchanged"),
        "kept_census_differences": cl.get("kept_census_differences"),
        "driver": pins.get("driver"), "driver_sha256": pins.get(
            "driver_sha256"),
        "driver_sha256_after": cl.get("driver_sha256_after"),
        "driver_unchanged_after": cl.get("driver_unchanged"),
        "driver_rebuilt_by_this_run": pins.get("driver_rebuilt_by_this_run"),
        "built_from": pins.get("built_from"),
        "driver_version_from_the_trace": pins.get(
            "driver_version_from_the_trace"),
        "transform_version": pins.get("transform_version"),
        "python": pins.get("python"),
        "sensorium_version": pins.get("sensorium_version"),
        "sensorium_version_probe": pins.get("sensorium_version_probe"),
        "sensorium_version_metadata": pins.get("sensorium_version_metadata"),
        "sensorium_version_metadata_probe": pins.get(
            "sensorium_version_metadata_probe"),
        "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
        "nproc": pins.get("nproc"), "governor": pins.get("governor"),
        "sensorium_dir": pins.get("sensorium_dir"),
        "e4pp_target": pins.get("e4p_target"),
        "rust_target": pins.get("rust_target"),
        "corpus_target": pins.get("corpus_target"),
        "corpus_target_from_env": pins.get("corpus_target_from_env"),
        "cargo_running_check": pins.get("cargo_running_check"),
        "session_parity": pins.get("session_parity"),
        "session_keys_differing": pins.get("session_keys_differing"),
        "injected_session_key": pins.get("injected_session_key"),
        "arm_b_key": pins.get("arm_b_key"),
        "arm_rows": pins.get("arm_rows"),
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
                     ("refocus_timeout", "loop_budget_s", "corpus_timeout",
                      "pytest_timeout", "cargo_test_timeout")},
        "logs_dir": raw.get("logs"),
    }


def assemble_e4pp(raw: dict) -> dict:
    """Raw E4″ facts -> the acceptance document's `results.json`."""
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero; a KILLED cell is {killed, reason} "
                   "and has no numeric reading at all"),
        "schema_version": raw.get("schema_version"),
        "assembled": {"schema_version": SCHEMA_VERSION},
        "acceptance": ((raw.get("byte_lock") or {}).get("doc")
                       or raw.get("document") or DOC),
        "runner": raw.get("runner"),
        "dry_run": raw.get("dry_run", False),
        # What a DRY run rehearsed, and what it showed. Carried so a reader
        # of a `-dry` record can see that it is one, and which of §1.3's
        # two readings it actually made.
        "dry_arms": raw.get("dry_arms", False),
        "dry_check": raw.get("dry_check"),
        "numbers_read": bool(raw.get("numbers_read")),
        "numbers_read_at": raw.get("numbers_read_at"),
        "numbers_read_because": raw.get("numbers_read_because"),
        "byte_lock": raw.get("byte_lock"),
        "rows_digest": raw.get("rows_digest"),
        "pins": raw.get("pins") or {},
        "environment": _environment(raw),
        "store": raw.get("store") or {},
        "pairs": _pairs(raw),
        "endpoints": {name: fn(raw) for name, fn in ENDPOINTS.items()},
        "predictions": _predictions(raw),
        "reported": _reported(raw),
        "cleanup": cl or None,
        "steps": raw.get("steps"),
        "stop": raw.get("stop"),
        # Which side each gated miss was on, DERIVED from what
        # missed rather than from the endpoint id (E4″ gap 2).
        "stop_sides": raw.get("stop_sides"),
        "bound_reached": raw.get("bound_reached"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }


__all__ = ["DOC", "SCHEMA_VERSION", "assemble_e4pp"]
