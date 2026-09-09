"""Raw E9 facts -> `results.json` in the pre-registered shape.

The same rules as every sibling (`acceptance_schema.assemble`,
`acceptance_schema_rung3.assemble_rung3`, `acceptance_grain_schema.
assemble_grain`): every measurement is `{"value", "n", "lens", "dropped"}`, a
`null` value with a non-empty `dropped` list is the ONLY representation of
not-measured, and `0` is measured-and-zero.

The SEVEN ENDPOINT BLOCKS and the two rules that govern them -- a killed arm
publishes nulls with the reason, and no cell is ever filled from a prediction
-- live in `acceptance_e9_cells.py`, which this file re-exports whole so no
caller's spelling changed. What is left here is the assembly: the environment,
the recordings, §1's predictions and §1.4's ungated block, put beside those
seven.
"""

from __future__ import annotations

from acceptance_e9_cells import (MEASUREMENT_CELLS, NEEDS,         # noqa: F401
                                 NOT_RUN, SURVIVES_A_DROPPED_RECORDING,
                                 _apply_record_drops, _drop, _h1, _h2, _h3,
                                 _h4, _h5, _h6, _h7, _null, _null_cells,
                                 _reader_drop, _record_drops, _records,
                                 measurement_keys)

DOC = "docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md"

#: R4 (design 2026-09-07 §5): the schema THIS assembler writes.
#: The raw record's own token is COPIED into `schema_version` and
#: this one is stamped beside it, so a record re-derived under a
#: later schema is distinguishable from one derived under its own.
#:
#: **`e9/1` -> `e9/2` (2026-09-08, the debts slice):**
#: `reported.line_rows_per_run` changed SHAPE, from one value per run to
#: `{value, source, reason}` per run, and its source from `meta.counts`
#: (a key no format-4 trace carries, so it published four nulls) to the
#: census's `line_events`. `acceptance_e9.SCHEMA_VERSION` moves with it.
SCHEMA_VERSION = "e9/2"


# ------------------------------------------------------------- predictions


def _predictions(raw) -> dict:
    """§1's pre-committed numbers, published under their OWN name.

    They are here so a reader can check the arithmetic without opening the
    document, and they are here ONLY here: no measurement cell above falls
    back to one, which is what `tests/test_acceptance_e9.py` pins.
    """
    cfg = raw.get("config") or {}
    # RECORDED BY THE RUNNER before any phase ran, so §1's triples and
    # sightings are published even when the phase that would have used them
    # never ran -- a `predictions` block that came out of `raw_h4` would be
    # EMPTY on exactly the run whose reader a reviewer most wants to check.
    pre = raw.get("predictions") or {}
    h4 = raw.get("raw_h4") or {}
    h5 = raw.get("raw_h5") or {}
    return {
        "note": ("§1's pre-registration, recorded beside the measurements "
                 "and never inside one; a headline that borrowed from here "
                 "could not fail"),
        "focus_values": {"A": cfg.get("focus_a"), "B": cfg.get("focus_b")},
        "N": cfg.get("gate_n"),
        "accounted_N": cfg.get("accounted_n"),
        "expected_by_line": cfg.get("expected_by_line"),
        "watch_triples": pre.get("watch_triples") or [
            {k: t.get(k) for k in ("id", "run", "at", "expr",
                                   "predicted_class", "predicted_exit",
                                   "line")}
            for t in (h4.get("triples") or [])],
        "flow_sightings": pre.get("flow_sightings") or [
            {k: s.get(k) for k in ("id", "literal", "binding", "line")}
            for s in (h5.get("sightings") or [])],
        "temp_root": cfg.get("temp_root"),
        "tmpdir_observed": cfg.get("tmpdir_observed"),
    }


def _reported(raw) -> dict:
    """§1.4's ungated block, as the run recorded it."""
    h3 = raw.get("raw_h3") or {}
    h5 = raw.get("raw_h5") or {}
    h6 = raw.get("raw_h6") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    pins = raw.get("pins") or {}
    runs = _records(raw)
    h4 = raw.get("raw_h4") or {}
    # §1.4's ungated honesty counts, per run: the deltas that came back
    # `{"k": "unread"}`, the deltas that came back truncated, and whether
    # `flags.bit0` (a dropped delta, `unread: ["locals"]` on a LINE payload)
    # was ever set. `meta.truncated_count` is the recorder's own whole-trace
    # figure and sits beside the walked one, because they count different
    # things and are only comparable if both are stated.
    #
    # `unread` on a CALL payload is NOT bit0: every Rust CALL row carries
    # `{"args": {}, "unread": ["locals"]}` because Rust CALL rows have no
    # args at all, so counting it there would report a dropped delta on every
    # activation (`convert/frames.rs:162` vs `:367`).
    census = {n: r.get("census") for n, r in runs.items()}
    return {
        "unread_and_truncated_captures": {
            "per_run": census,
            "recorder_truncated_count": {n: r.get("truncated_count")
                                         for n, r in runs.items()},
            "bit0_ever_set": {n: (c or {}).get("bit0_ever_set")
                              for n, c in census.items()},
            "note": ("§1.4's honesty count, reported without a gate; "
                     "`journal`, `images`, `p`, `p2` and `fake` are expected "
                     "among the unread"),
        },
        "watch_bucket_counts": (raw.get("raw_h4") or {}) and {
            t.get("id"): {k: t.get(k) for k in
                          ("sites", "evaluated", "hits", "not_captured",
                           "errors")}
            for t in (h4.get("triples") or []) if "dropped" not in t},
        "flow_pages": {s.get("id"): {"limit": s.get("flow_limit"),
                                     "rows_printed": s.get("rows_printed"),
                                     "showing": s.get("showing"),
                                     "page_truncated": s.get("page_truncated")}
                       for s in (h5.get("sightings") or [])},
        "walls_s": h6.get("walls_s"),
        "libtest_s": h6.get("libtest_s"),
        "pairs": h6.get("pairs"),
        "line_histogram": h3.get("by_line"),
        "line_histogram_via_code_id": h3.get("by_line_via_code_id"),
        # §1.4's "the LINE-row totals of F1 and F2", at the name §1.4 uses.
        # It read `meta.counts` -- a key no format-4 trace carries (there is
        # `truncated_count`, and the `recorded: CALL … LINE …` line `info`
        # prints is computed by the reader) -- so it published four nulls a
        # reader could not tell from four runs with no LINE rows. The number
        # was in the record all along under another name: the census walks
        # each run's events and counts them. Read from there, with the
        # source named on the cell and `null` WITH its reason for a run that
        # was never censused.
        "line_rows_per_run": {
            n: {"value": (c or {}).get("line_events"),
                "source": "census.line_events",
                "reason": (None if c else "this run was not censused, so "
                                          "its LINE rows were never counted")}
            for n, c in census.items()},
        "trace_bytes": h6.get("trace_bytes"),
        "whole_trace_sightings": {s.get("id"): s.get("whole_trace_rows")
                                  for s in (h5.get("sightings") or [])},
        "gated_sightings": {s.get("id"): s.get("gated_rows")
                            for s in (h5.get("sightings") or [])},
        "driver": pins.get("driver"),
        "driver_sha256": pins.get("driver_sha256"),
        "driver_sha256_after": cl.get("driver_sha256_after"),
        "driver_built_from": pins.get("built_from"),
        "tmpdir_observed": pins.get("tmpdir_observed"),
        "tmpdir_reading": pins.get("tmpdir_reading"),
        "sensorium_tier": pins.get("sensorium_tier"),
        "invocation_log": pins.get("invocation_log"),
        "invocations_jsonl_lines": cl.get("invocations_jsonl_lines"),
        "store_bytes": cl.get("store_bytes"),
        "traces_recorded": cl.get("traces_recorded"),
        "e9_target_bytes": cl.get("e9_target_bytes"),
        "corpus_target_bytes": cl.get("corpus_target_bytes"),
        "disk_free_gb": {
            "repo_before": pins.get("repo_disk_free_gb"),
            "repo_after": cl.get("repo_disk_free_gb_after"),
            "target_before": pins.get("target_disk_free_gb"),
            "target_after": cl.get("target_disk_free_gb_after")},
        "load_at_each_phase": raw.get("arm_loads"),
    }


def _recordings(raw) -> dict:
    """The four runs as the record publishes them: what was asked, what came
    back, and no verdict."""
    keep = ("name", "command", "cwd", "focus_flags", "test_target", "rc",
            "wall_s", "timed_out", "kill_s", "log", "focus_lines",
            "focus_refusal", "cargo_exit", "run", "run_pick_rule",
            "run_candidates", "outcome", "libtest_secs", "trace_bytes")
    keep = keep + ("outcome_class", "outcome_class_why", "truncated_count")
    return {n: {k: r.get(k) for k in keep}
            | {"test_result_lines": [s["line"] for s in
                                     (r.get("test_results") or [])]}
            for n, r in _records(raw).items()}


# --------------------------------------------------------------- assemble


def assemble_e9(raw: dict) -> dict:
    """Raw E9 facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero"),
        # COPIED from the raw record, never asserted: this is the schema the
        # MEASUREMENT was written under. `None` for a raw that predates the
        # field is the honest answer -- borrowing the assembler's token here
        # would date every old record forward.
        "schema_version": raw.get("schema_version"),
        "assembled": {"schema_version": SCHEMA_VERSION},
        # DERIVED, not asserted: the document this run was byte-locked
        # against, taken from the raw record's own `byte_lock.doc`. The
        # module constant is only the last resort for a raw record with no
        # byte-lock at all (a run refused before the check), where there is
        # nothing to derive from -- R-G15.
        "acceptance": ((raw.get("byte_lock") or {}).get("doc")
                       or raw.get("document") or DOC),
        "runner": raw.get("runner"),
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
            "clone_read_only_reading": pins.get("clone_read_only_reading"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_sha256_after": cl.get("driver_sha256_after"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "driver_profile": pins.get("driver_profile"),
            "driver_mtime": pins.get("driver_mtime"),
            "driver_rebuilt_by_this_run": pins.get(
                "driver_rebuilt_by_this_run"),
            "built_from": pins.get("built_from"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "e9_target": pins.get("e9_target"),
            "rust_target": pins.get("rust_target"),
            "corpus_target": pins.get("corpus_target"),
            "corpus_target_from_env": pins.get("corpus_target_from_env"),
            "tmpdir_observed": pins.get("tmpdir_observed"),
            "tmpdir_reading": pins.get("tmpdir_reading"),
            "temp_root": pins.get("temp_root"),
            "sensorium_tier": pins.get("sensorium_tier"),
            "invocation_log": pins.get("invocation_log"),
            "invocations_jsonl_lines": cl.get("invocations_jsonl_lines"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_phase": raw.get("arm_loads"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "repo_disk_free_gb_after": cl.get("repo_disk_free_gb_after"),
            "target_disk_free_gb": pins.get("target_disk_free_gb"),
            "target_disk_free_gb_after": cl.get("target_disk_free_gb_after"),
            "logs_dir": raw.get("logs"),
        },
        "recordings": _recordings(raw),
        "endpoints": {
            "H1": _h1(raw), "H2": _h2(raw), "H3": _h3(raw), "H4": _h4(raw),
            "H5": _h5(raw), "H6": _h6(raw), "H7": _h7(raw),
        },
        "predictions": _predictions(raw),
        "reported": _reported(raw),
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "stop": raw.get("stop"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }
