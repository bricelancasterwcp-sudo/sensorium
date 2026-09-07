"""Raw E4 facts -> `results.json` in the pre-registered shape.

The same rules as every sibling (`acceptance_schema.assemble`,
`acceptance_schema_rung3.assemble_rung3`, `acceptance_e9_schema.assemble_e9`):
every measurement is `{"value", "n", "lens", "dropped"}`, a `null` value with
a non-empty `dropped` list is the ONLY representation of not-measured, and
`0` is measured-and-zero.

The SEVEN ENDPOINT BLOCKS and the rules that govern them -- a count over a
loop that did not finish is a not-measured, a killed invocation publishes
nulls with the kill as the reason, and no cell is ever filled from a
prediction -- live in `acceptance_e4_cells.py`, which this file re-exports
whole so no caller's spelling changed. What is left here is the assembly: the
environment, the 61 pairs, §1's predictions and §1.4's ungated block, put
beside those seven.
"""

from __future__ import annotations

from acceptance_e4_cells import (MEASUREMENT_CELLS, NEEDS,          # noqa: F401
                                 NOT_RUN, SURVIVES_A_KILL, _apply_drops,
                                 _drop, _h1, _h2, _h3, _h4, _h5, _h6, _h7,
                                 _incomplete_drops, _killed_drops, _null,
                                 _null_cells, _reader_drop,
                                 measurement_keys)

DOC = "docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md"


# ------------------------------------------------------------- predictions


def _predictions(raw) -> dict:
    """§1's pre-committed numbers, published under their OWN name.

    They are here so a reader can check the arithmetic without opening the
    document, and they are here ONLY here: no measurement cell falls back to
    one, which is what `tests/test_acceptance_e4_record.py` pins.
    """
    cfg = raw.get("config") or {}
    # RECORDED BY THE RUNNER before any phase ran, so §1's list and triples
    # are published even when the phase that would have used them never ran.
    pre = raw.get("predictions") or {}
    h5 = raw.get("raw_h5") or {}
    return {
        "note": ("§1's pre-registration, recorded beside the measurements "
                 "and never inside one; a headline that borrowed from here "
                 "could not fail"),
        "expected_match": pre.get("expected_match"),
        "expected_match_n": len(pre.get("expected_match") or []),
        "gate_n": pre.get("gate_n") or cfg.get("gate_n"),
        "hazard_tests": pre.get("hazard_tests"),
        "the_61_tests": cfg.get("tests"),
        "targets": cfg.get("targets"),
        "watch_triples": pre.get("watch_triples") or [
            {k: t.get(k) for k in ("id", "of", "at", "expr",
                                   "predicted_class", "predicted_exit",
                                   "line", "gate")}
            for t in (h5.get("triples") or [])],
        "temp_root": cfg.get("temp_root"),
        "tmpdir_observed": cfg.get("tmpdir_observed"),
        "argv_forms": {
            "pass1": ("cargo sensorium test -p bloomery-daemon --test <file> "
                      "-- <name> --exact"),
            "pass2": "sensorium refocus <run> --focus <name>"},
    }


def _pairs(raw) -> dict:
    """The 61 pairs, as the record publishes them: what was asked of each,
    what came back, and no verdict.

    One row per §1.1 name, whether or not it ran: a test the loop never
    reached is a row carrying `not_run` and nothing else, which is what
    stops the table from being a list of the tests that happened to work.
    """
    one = raw.get("raw_pass1") or {}
    two = raw.get("raw_pass2") or {}
    p2 = {r["name"]: r for r in (two.get("refocuses") or [])}
    h2 = {p["name"]: p for p in ((raw.get("raw_h2") or {}).get("per_test")
                                 or [])}
    h3 = {p["name"]: p for p in ((raw.get("raw_h3") or {}).get("per_test")
                                 or [])}
    h4 = {p["name"]: p for p in ((raw.get("raw_h4") or {}).get("per_test")
                                 or [])}
    rows = []
    for r in (one.get("runs") or []):
        name = r["name"]
        b = p2.get(name) or {}
        cls = (h3.get(name) or {}).get("classification") or {}
        rows.append({
            "index": r.get("index"), "target": r.get("target"), "name": name,
            "pass1_not_run": r.get("not_run"),
            "pass1_command": r.get("command"),
            "pass1_rc": r.get("rc"), "pass1_wall_s": r.get("wall_s"),
            "pass1_timed_out": r.get("timed_out"),
            "pass1_summary_lines": r.get("summary_lines"),
            "pass1_libtest_s": r.get("libtest_secs"),
            "pass1_processes": r.get("processes"),
            "pass1_log": r.get("log"),
            "original": r.get("run"),
            "original_trace_bytes": r.get("trace_bytes"),
            "pass2_not_run": b.get("not_run"),
            "pass2_command": b.get("command"),
            "pass2_rc": b.get("rc"), "pass2_wall_s": b.get("wall_s"),
            "pass2_timed_out": b.get("timed_out"),
            "pass2_log": b.get("log"),
            "driver_cmd": b.get("driver_cmd"),
            "child_launched": b.get("child_launched"),
            "new_run": b.get("new_run"),
            "new_trace_bytes": b.get("new_trace_bytes"),
            "pair_n": (b.get("pair") or {}).get("n"),
            "pair_refusal": b.get("pair_refusal"),
            "pair_agrees_with_the_printed_id": b.get(
                "pair_agrees_with_the_printed_id"),
            "verdict_word": b.get("verdict_word"),
            "verdict_and_exit_agree": b.get("verdict_and_exit_agree"),
            "stamped_verdict": (h3.get(name) or {}).get("stamped_verdict"),
            "licence": (h4.get(name) or {}).get("licence"),
            "source_status": (h4.get(name) or {}).get("source_status"),
            "env_status": (h4.get(name) or {}).get("env_status"),
            "unverifiable": (h4.get(name) or {}).get("unverifiable"),
            "completed": (h2.get(name) or {}).get("completed"),
            "build_failure": (h2.get(name) or {}).get("build_failure"),
            "outcome_equal": (h2.get(name) or {}).get("outcome_equal"),
            "diverged_class": cls.get("class"),
            "diverged_reading": cls.get("reading"),
            "pre_rerun_refusal": b.get("pre_rerun_refusal"),
        })
    return {"rows": rows, "n": len(rows)}


def _reported(raw) -> dict:
    """§1.4's ungated block, as the run recorded it."""
    h3 = raw.get("raw_h3") or {}
    h4 = raw.get("raw_h4") or {}
    h5 = raw.get("raw_h5") or {}
    h6 = raw.get("raw_h6") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    pins = raw.get("pins") or {}
    one = raw.get("raw_pass1") or {}
    two = raw.get("raw_pass2") or {}
    return {
        "walls": {
            "first_focus": h6.get("first_focus"),
            "later_focus_walls_s": h6.get("later_focus_walls_s"),
            "later_focus_mean_s": h6.get("later_focus_mean_s"),
            "later_focus_min_s": h6.get("later_focus_min_s"),
            "later_focus_max_s": h6.get("later_focus_max_s"),
            "refocus_total_s": h6.get("refocus_total_s"),
            "pass1_total_s": h6.get("pass1_total_s"),
            "cargo_build_s": h6.get("cargo_build_s"),
            "cargo_build_reported_for": h6.get("cargo_build_reported_for"),
            "libtest_s": h6.get("libtest_s"),
            "pass1_libtest_s": h6.get("pass1_libtest_s"),
            "note": ("REPORTED without a gate: the first focus pays for the "
                     "rt build, the later ones for a fresh shim and the "
                     "matched units"),
        },
        "shim_census": h6.get("shim_census"),
        "trace_bytes": h6.get("trace_bytes"),
        "watch_bucket_counts": {
            t.get("id"): {k: t.get(k) for k in
                          ("sites", "evaluated", "hits", "not_captured",
                           "errors")}
            for t in (h5.get("triples") or []) if "dropped" not in t},
        "watch_reported_classes": h5.get("reported_classes"),
        "licence_per_test": h4.get("per_test"),
        "divergent_events": {p["name"]: p.get("step_rows")
                             for p in (h3.get("per_test") or [])
                             if p.get("step_rows")},
        "discriminator": {p["name"]: p.get("classification")
                          for p in (h3.get("per_test") or [])
                          if p.get("classification")},
        "driver": pins.get("driver"),
        "driver_sha256": pins.get("driver_sha256"),
        "driver_sha256_after": cl.get("driver_sha256_after"),
        "driver_built_from": pins.get("built_from"),
        "versions_from_the_first_trace": pins.get(
            "versions_from_the_first_trace"),
        "the_61_names_re_derived": pins.get("the_61_names"),
        "tmpdir_observed": pins.get("tmpdir_observed"),
        "tmpdir_reading": pins.get("tmpdir_reading"),
        "sensorium_tier": pins.get("sensorium_tier"),
        "invocation_log": pins.get("invocation_log"),
        "invocations_jsonl_lines": cl.get("invocations_jsonl_lines"),
        "store_bytes": cl.get("store_bytes"),
        "traces_recorded": cl.get("traces_recorded"),
        "e4_target_bytes": cl.get("e4_target_bytes"),
        "corpus_target_bytes": cl.get("corpus_target_bytes"),
        "pass_totals": {
            "pass1_measured": one.get("measured"), "pass1_n": one.get("n"),
            "pass2_measured": two.get("measured"), "pass2_n": two.get("n"),
            "pass1_budget_exhausted": one.get("budget_exhausted"),
            "pass2_budget_exhausted": two.get("budget_exhausted"),
            "pass1_killed": one.get("killed"), "pass2_killed": two.get(
                "killed"),
            "pass1_multi_process": one.get("multi_process"),
            "pass2_pair_refusals": two.get("pair_refusals")},
        "disk_free_gb": {
            "repo_before": pins.get("repo_disk_free_gb"),
            "repo_after": cl.get("repo_disk_free_gb_after"),
            "target_before": pins.get("target_disk_free_gb"),
            "target_after": cl.get("target_disk_free_gb_after")},
        "load_at_each_phase": raw.get("arm_loads"),
    }


# --------------------------------------------------------------- assemble


def assemble_e4(raw: dict) -> dict:
    """Raw E4 facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero"),
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
            "tests_dir": pins.get("tests_dir"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_sha256_after": cl.get("driver_sha256_after"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "driver_profile": pins.get("driver_profile"),
            "driver_mtime": pins.get("driver_mtime"),
            "driver_rebuilt_by_this_run": pins.get(
                "driver_rebuilt_by_this_run"),
            "built_from": pins.get("built_from"),
            "versions_from_the_first_trace": pins.get(
                "versions_from_the_first_trace"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "e4_target": pins.get("e4_target"),
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
            "timeouts": {k: (raw.get("config") or {}).get(k) for k in
                         ("cargo_timeout", "refocus_timeout",
                          "reader_timeout", "loop_budget_s",
                          "corpus_timeout", "pytest_timeout",
                          "cargo_test_timeout")},
            "logs_dir": raw.get("logs"),
        },
        "pairs": _pairs(raw),
        "endpoints": {
            "H1": _h1(raw), "H2": _h2(raw), "H3": _h3(raw), "H4": _h4(raw),
            "H5": _h5(raw), "H6": _h6(raw), "H7": _h7(raw),
        },
        "predictions": _predictions(raw),
        "reported": _reported(raw),
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "stop": raw.get("stop"),
        "bound_reached": raw.get("bound_reached"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }
