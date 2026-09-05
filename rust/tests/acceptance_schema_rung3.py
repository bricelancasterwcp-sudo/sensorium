"""Raw rung-3 acceptance facts -> `results.json` in the pre-registered shape.

Same rules as `acceptance_schema.assemble`: every measurement is
`{"value", "n", "lens", "dropped"}`, a `null` value with a non-empty `dropped`
list is the ONLY representation of not-measured, and `0` is measured-and-zero.

Nothing here decides a verdict. §4 of
`docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md` is
written by hand against §1's rules, and E6''s adjudication -- which no program
can do, because it is a reading of the clone's SOURCE -- is carried as a
`null` with the reason, never as a number this file invented.
"""

from __future__ import annotations

import time

from acceptance_lib import meas
from acceptance_phases import wall_summary
from acceptance_schema import _e3, _e5                             # noqa: F401

DOC = ("docs/superpowers/acceptance/"
       "2026-09-04-sensorium-rung3-acceptance.md")


def _drop(raw, key):
    v = raw.get(key)
    if v is None:
        return [f"{key} did not run"]
    if isinstance(v, dict) and v.get("dropped"):
        d = v["dropped"]
        return d if isinstance(d, list) else [d]
    return []


# --------------------------------------------------------------------- E6


def _e6(raw) -> dict:
    r = raw.get("raw_e6") or {}
    cases = r.get("cases") or []
    dropped = _drop(raw, "raw_e6") + [
        f"{c['case']}: {c['dropped']}" for c in cases if c.get("dropped")]
    qs = [(c["case"], q) for c in cases for q in c.get("questions", [])]
    extra = sum(len(q["extra_swallowed_lines"]) for _, q in qs)
    missing = sum(len(q["missing_swallow_groups"]) for _, q in qs)
    tally_bad = [f"{c}/{q['id']}" for c, q in qs if not q["tally_equal"]]
    empty_bad = [f"{c}/{q['id']}" for c, q in qs
                 if not q["swallow_set_nonempty_ok"]]
    set_bad = [f"{c}/{q['id']}" for c, q in qs if not q["swallow_set_equal"]]
    corpus_bad = [f"{c}/{q['id']}: {'; '.join(q['corpus_check_failures'])}"
                  for c, q in qs if q.get("corpus_check_failures")]
    lens = ("every `corpus/rust/*` case with an `exceptions` question, copied "
            "to a disposable workdir and recorded ONCE under the rung-3 "
            "driver; the printed SWALLOWED lines matched against the case's "
            "registered `expect_line` groups by a PERFECT bipartite matching "
            "(so two groups cannot both claim one line while a second line "
            "goes unclaimed) with the count pinned by "
            "`expect_count[\"SWALLOWED\"]`, and the printed `dispositions:` "
            "line compared WHOLE against the case's single "
            "`expect_contains` tally")
    return {
        "headline": meas(extra if qs else None, len(qs),
                         "printed SWALLOWED lines no registered group claims "
                         "-- §1's false accusations; " + lens, dropped),
        "extra_swallowed_lines": meas(extra if qs else None, len(qs), lens,
                                      dropped),
        "missing_swallow_groups": meas(missing if qs else None, len(qs),
                                       "registered SWALLOWED groups with no "
                                       "printed line; " + lens, dropped),
        "cases_with_an_unequal_swallow_set": meas(
            len(set_bad) if qs else None, len(qs),
            "questions whose printed swallow set is not EQUAL to the "
            "registered one (count, and a perfect matching both ways)",
            dropped),
        "cases_with_an_unequal_tally": meas(
            len(tally_bad) if qs else None, len(qs),
            "questions whose printed `dispositions:` line differs from the "
            "registered whole line (or which printed one where the case "
            "registered none)", dropped),
        "swallow_cases_with_an_empty_set": meas(
            len(empty_bad) if qs else None, len(qs),
            "questions registering a non-empty swallow set that printed no "
            "SWALLOWED line", dropped),
        "corpus_reading_failures": meas(
            len(corpus_bad) if qs else None, len(qs),
            "the CORPUS's own reading of the same output "
            "(`run_corpus.check_question`: substring, not equality) -- "
            "reported beside §1's stricter one, never gated", dropped),
        "unequal_swallow_sets": set_bad,
        "unequal_tallies": tally_bad,
        "empty_swallow_sets": empty_bad,
        "corpus_failures": corpus_bad,
        "cases": [{"case": c["case"], "run_ids": c.get("run_ids"),
                   "record_rc": c.get("record_rc"),
                   "dropped": c.get("dropped"),
                   "questions": [{
                       "id": q["id"],
                       "printed": q["printed_swallowed_count"],
                       "expected": q["expected_swallowed"],
                       "equal": q["swallow_set_equal"],
                       "printed_tally": q["printed_tally"],
                       "pinned_tally": q["tally_pinned"],
                       "tally_equal": q["tally_equal"],
                       "extra": q["extra_swallowed_lines"],
                       "missing": q["missing_swallow_groups"],
                       "rc": q["rc"], "expect_exit": q["expect_exit"],
                       "swallowed_lines": q["printed_swallowed"],
                   } for q in c.get("questions", [])]}
                  for c in cases],
    }


# -------------------------------------------------------------------- E6'


def _e6prime(raw) -> dict:
    r = raw.get("raw_e6prime") or {}
    dropped = _drop(raw, "raw_e6prime")
    n = r.get("swallowed_count")
    counts = r.get("counts") or {}
    lens = ("`cargo sensorium test -p bloomery-daemon --lib` on the clone at "
            "e209ed9 under the driver of §2, then `sensorium exceptions <run> "
            "--limit 100000` captured whole (the limit is above the chain "
            "count, so nothing was paged away)")
    return {
        "headline": meas(
            None, n,
            "FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks "
            "for every printed SWALLOWED line to be adjudicated against the "
            "clone's SOURCE, which is a reading, not a computation. The "
            "count and the adjudication table are §4 of the document; what "
            "is here is every line that had to be adjudicated. " + lens,
            ["adjudicated by hand in §4 of the acceptance document, under "
             "both the amended and the strictest pre-lock readings of "
             "\"merely observed\""]),
        "swallowed_lines": meas(n, r.get("chains_in_scope"),
                                "printed SWALLOWED lines, of the chains in "
                                "scope; " + lens, dropped),
        "unparsed_swallowed_lines": meas(
            r.get("unparsed_swallowed"), n,
            "SWALLOWED lines the collector could not parse into "
            "(how, event, qualname, line) -- anything but 0 means the "
            "adjudication table below was assembled by hand for that row",
            dropped),
        "chains_in_scope": meas(r.get("chains_in_scope"), None,
                                "`raised (N):` -- Err chains the command "
                                "judged", dropped),
        "tally": r.get("tally"), "tally_line": r.get("tally_line"),
        "partial_line": r.get("partial_line"),
        "panics_line": r.get("panics_line"),
        "more_note": r.get("more_note"),
        "run": r.get("run"), "events": r.get("events"),
        "rc": r.get("rc"), "exceptions_rc": r.get("exceptions_rc"),
        "wall_s": r.get("wall"), "exceptions_wall_s": r.get("exceptions_wall"),
        "swallowed": r.get("swallowed_parsed"),
        "trace": counts,
    }


# -------------------------------------------------------------------- E2''


def _e2pp(raw) -> dict:
    r = raw.get("raw_e2pp") or {}
    cfg = raw.get("config") or {}
    census = raw.get("raw_census") or {}
    tr = r.get("try") or {}
    m = r.get("manifests") or {}
    ctry = raw.get("raw_census_try") or {}
    denom = cfg.get("try_syn")
    num = tr.get("try_rows_distinct")
    dropped = _drop(raw, "raw_e2pp")
    ratio = (round(num / denom, 6) if (num is not None and denom) else None)
    lens = (f"numerator = DISTINCT (file, line) over `kind: \"try\"` manifest "
            f"rows from ONE from-scratch workspace `--no-run` build (the "
            f"target directory was emptied first, so cargo compiled every "
            f"unit and the `-C metadata=` scope in its own `cargo -v` log is "
            f"complete); denominator = §1's FROZEN try_syn = {denom}, counted "
            f"by Task 0 over the clone at e209ed9 BEFORE the byte-lock")
    return {
        "headline": meas(ratio, denom or 0,
                         f"instrumented {num} / {denom} syn-visible `?`; "
                         + lens, dropped),
        "numerator": meas(num, len(m.get("units", [])),
                          "distinct `kind: \"try\"` manifest rows", dropped),
        "numerator_raw": meas(tr.get("try_rows_raw"),
                              len(m.get("units", [])),
                              "the RAW sum of `try` rows over the build's "
                              "manifests: two (crate_name, crate_type) pairs "
                              "declare two manifests for one unit, so this "
                              "double-counts a source `?`", dropped),
        "denominator": meas(denom, census.get("files"),
                            "§1's frozen `try_syn` over the clone", []),
        "units_that_fell_back": meas(
            len(m.get("fell_back", [])) if m else None,
            len(m.get("units", [])),
            "manifests with `fell_back: true` in the from-scratch workspace "
            "build", dropped),
        "fell_back_stderr_lines": meas(
            len(r.get("fell_back_stderr_lines") or []) if r else None, 1,
            "`fell back to the real tree` lines in the build's own log",
            dropped),
        "partial_rows": meas(tr.get("partial_rows"),
                             len(m.get("units", [])),
                             f"distinct `partial` rows; §1 reports these "
                             f"against try_macro_tokens = "
                             f"{cfg.get('try_macro_tokens')} per file",
                             dropped),
        "partial_by_file": tr.get("partial_by_file"),
        "partial_reasons": tr.get("partial_reasons"),
        "partial_detail": tr.get("partial_detail"),
        "try_rows_by_file": tr.get("try_rows_by_file"),
        "site_kinds_raw": tr.get("site_kinds_raw"),
        "unreached_files": meas(len(m.get("unreached_files", [])) if m else None,
                                len(m.get("units", [])),
                                "files a unit's module walk could not reach, "
                                "unioned", dropped),
        "build": r.get("build"),
        "census_rerun_try_syn": meas(
            ctry.get("try_syn"), ctry.get("files"),
            "the census binary re-run over the clone at run time. REPORTED, "
            "not the denominator: §1 froze try_syn before the byte-lock and "
            "the ratio above is taken over that number", []),
        "census_rerun_try_macro_tokens": meas(
            ctry.get("try_macro_tokens"), ctry.get("files"),
            "the same re-run's macro-argument `?` tokens", []),
        "census_rerun_agrees_with_the_frozen_denominator":
            ctry.get("agrees_with_the_frozen_denominator"),
        "census_rerun": {"files": ctry.get("files"),
                         "parsed": ctry.get("parsed"),
                         "try_by_file": ctry.get("try_by_file"),
                         "macro_by_file": ctry.get("macro_by_file")},
        "census_rung2_columns": {"files": census.get("files"),
                                 "parsed": census.get("parsed"),
                                 "totals": census.get("totals")},
    }


# -------------------------------------------------------------------- E7''


def _e7pp(raw) -> dict:
    r = raw.get("raw_e7pp") or {}
    op = r.get("operand") or {}
    e7_ok = [c for c in r.get("ok", []) if c.startswith("e7")
             and not c.startswith("e7_operand")]
    e7_fail = [c for c in r.get("fail", []) if c.startswith("e7")
               and not c.startswith("e7_operand")]
    op_fail = [c for c in r.get("fail", []) if c.startswith("e7_operand")]
    loc = op.get("locations") or {}
    have = bool(loc.get("plain")) and bool(loc.get("call"))
    return {
        "headline": meas(len(e7_fail) if r else None,
                         len(e7_ok) + len(e7_fail),
                         "FAILED E7 checks on the probe's EXISTING panics "
                         "(lines and columns), of the E7 checks that ran; "
                         "`rust/tests/mechanics.sh`",
                         _drop(raw, "raw_e7pp")),
        "existing_checks_passed": meas(len(e7_ok), len(e7_ok) + len(e7_fail),
                                       "E7 checks that passed", []),
        "existing_check_failures": e7_fail,
        "operand_column_shift": meas(
            op.get("column_shift_call") if have else None, 1,
            f"instrumented column minus plain column for the panic literal "
            f"inside a `?` operand, tier `call`; §1 predicted "
            f"{op.get('predicted_shift')} (the wrap prefix `match `)",
            op.get("dropped") or []),
        "operand_column_shift_off": meas(
            op.get("column_shift_off") if have else None, 1,
            "the same, tier `off`: the wrapped bytes are identical, only the "
            "runtime's answer differs", op.get("dropped") or []),
        "operand_line_identical": meas(
            (1 if op.get("line_identical") else 0) if have else None, 1,
            "1 when the panic's LINE is the same in both arms",
            op.get("dropped") or []),
        "operand_locations": loc,
        "operand_predicted_shift": op.get("predicted_shift"),
        "operand_check_failures": op_fail,
        "operand_checks": op.get("checks"),
        "mechanics_rc": r.get("rc"),
        "mechanics_ok": len(r.get("ok", [])),
        "mechanics_fail": r.get("fail"),
        "mechanics_skip": r.get("skip"),
        "driver_unchanged": r.get("driver_unchanged"),
    }


# -------------------------------------------------------------------- E0''


def _e0pp(raw) -> dict:
    r = raw.get("raw_e0pp") or {}
    arms = r.get("arms") or {}
    dropped = _drop(raw, "raw_e0pp")
    walls = [a.get("wall") for a in arms.values() if a.get("wall") is not None]
    over = [k for k, a in arms.items() if not a.get("under_ceiling")]
    lens = (f"`sensorium info <run>` and `sensorium diff <run> <run>` on the "
            f"E6' trace, wall-timed, with E0's "
            f"{r.get('kill_s')} s kill ARMED (a command that hits it is "
            f"killed, never waited out)")
    def arm(name):
        a = arms.get(name) or {}
        return meas(a.get("wall"), 1, lens,
                    [a["dropped"]] if a.get("dropped") else dropped)

    return {
        "headline": meas(len(over) if arms else None, len(arms),
                         "arms at or over the 60 s ceiling; " + lens, dropped),
        "info_wall_s": arm("info"),
        "diff_wall_s": arm("diff"),
        "max_wall_s": meas(max(walls) if walls else None, len(arms), lens,
                           dropped),
        "diff_verdict_line": (arms.get("diff") or {}).get("verdict_line"),
        "arms": arms,
    }


# ------------------------------------------- reported without a gate


def _reported(raw) -> dict:
    r6 = raw.get("raw_e6prime") or {}
    counts = r6.get("counts") or {}
    walls = (raw.get("raw_walls") or {}).get("runs") or []
    plain = wall_summary(walls, "P")
    call = wall_summary(walls, "C")
    overhead = (round(call["median"] - plain["median"], 3)
                if plain["median"] and call["median"] else None)
    lens = ("`cargo test -p bloomery-daemon --lib` versus `cargo sensorium "
            "test -p bloomery-daemon --lib`, 5 rounds, order alternating "
            "P,C then C,P, 10 s cool-down, the 1-minute load read at each "
            "arm's start and an arm DROPPED (never re-rolled) above 4.0 -- "
            "the rung-2 addendum's protocol and lens")
    return {
        "E1pp_plain_median_s": meas(plain["median"], plain["n"], lens,
                                    plain["dropped"]),
        "E1pp_call_median_s": meas(call["median"], call["n"], lens,
                                   call["dropped"]),
        "E1pp_overhead_s": meas(overhead, min(plain["n"], call["n"]),
                                "call median minus plain median; " + lens,
                                plain["dropped"] + call["dropped"]),
        "E1pp_walls": {"plain": plain, "call": call, "runs": walls},
        "raise_events": meas(counts.get("raise"), counts.get("events"),
                             "RAISE events on the E6' trace", []),
        "handled_events": meas(counts.get("handled"), counts.get("events"),
                               "HANDLED events on the E6' trace", []),
        "bytes_per_record": meas(counts.get("bytes_per_record"),
                                 counts.get("events"),
                                 "the E6' trace's size in bytes divided by "
                                 "its event count", []),
        "trace_bytes": meas(counts.get("trace_bytes"), 1,
                            "the E6' trace file's size", []),
        "meta_sites_bytes": meas(counts.get("meta_sites_bytes"), 1,
                                 "JSON bytes of `meta.sites` on the E6' "
                                 "trace (the Task-4 watch item)", []),
        "partial_rows_on_the_trace": meas(counts.get("partial_rows"), 1,
                                          "`meta.partial` rows on the E6' "
                                          "trace", []),
        "closure_frames": meas(counts.get("closure_frames"),
                               sum((counts.get("frame_kinds") or {}).values())
                               or None,
                               "frames whose kind is `closure`, of every "
                               "frame on the E6' trace", []),
        "site_kinds": counts.get("site_kinds"),
        "event_kinds": counts.get("event_kinds"),
        "frame_kinds": counts.get("frame_kinds"),
        "dispositions_on_the_clone": r6.get("tally"),
    }


# ------------------------------------------------------------------ assemble


def _byte_lock_extended() -> dict | None:
    """The EXTENDED locked range, re-derived at assembly time.

    The 2026-09-05 run locked `awk '/^## 1/,/^## 2/'`, which covers §1's
    footnote MARKER and not the footnote's body -- the sentence the whole E6'
    adjudication turns on. The Task-8 review closed that hole by widening the
    range to §1 plus the definition of every footnote §1 references.

    It is computed HERE rather than taken from the raw record because the raw
    record is the run's own and is never rewritten: this block is stamped
    `verified_at` and says plainly that it was derived after the run. It reads
    only committed text and the document, so it is deterministic; a mismatch
    is reported, never raised, so a failed run still assembles."""
    try:
        import acceptance_rung3 as runner                          # noqa: PLC0415
        rec = runner.byte_lock_facts()
    except Exception as e:                                         # noqa: BLE001
        return {"dropped": f"the extended range could not be derived: {e}"}
    return {
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "derived": ("after the run, by `acceptance_rung3.byte_lock_facts` "
                    "over committed text; the run's own §1-only lock is in "
                    "`byte_lock` above and is unchanged"),
        "range": rec["range"], "footnotes_in_range": rec["footnotes_in_range"],
        "commit": rec["commit"], "sha256": rec["locked_sha256"],
        "bytes": rec["locked_bytes"],
        "original_lock": rec["original_lock"],
        "original_lock_sha256": rec["original_lock_sha256"],
        "original_lock_bytes": rec["original_lock_bytes"],
        "amendment_bytes": rec["amendment_bytes"],
        "working_tree_sha256": rec["working_tree_sha256"],
        "identical": rec["identical"],
        "dropped": None,
    }


def assemble_rung3(raw: dict) -> dict:
    """Raw rung-3 facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero"),
        "acceptance": DOC,
        "runner": raw.get("runner"),
        "byte_lock": raw.get("byte_lock"),
        "byte_lock_extended": _byte_lock_extended(),
        "pins": pins,
        "environment": {
            "repo_commit": pins.get("repo_commit"),
            "repo_branch": pins.get("repo_branch"),
            "repo_porcelain": pins.get("repo_porcelain"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_mtime": pins.get("driver_mtime"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "census_driver": pins.get("census_driver"),
            "census_driver_sha256": pins.get("census_driver_sha256"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "clone": pins.get("clone"), "clone_head": pins.get("clone_head"),
            "arm_tips": pins.get("arm_tips"),
            "clone_porcelain_before": pins.get("clone_porcelain_before"),
            "clone_porcelain_after": cl.get("clone_porcelain_after"),
            "clone_restored": cl.get("clone_restored"),
            "cargo_lock_unchanged": cl.get("cargo_lock_unchanged"),
            "target_dir": pins.get("target_dir"),
            "target_warm_at_start": pins.get("target_warm_at_start"),
            "target_emptied_by_e2pp_bytes":
                (raw.get("raw_e2pp") or {}).get("target_emptied_bytes"),
            "corpus_target": pins.get("corpus_target"),
            "probe_target": pins.get("probe_target"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "source_bloomery": pins.get("source_bloomery"),
            "source_bloomery_head_before":
                pins.get("source_bloomery_head_before"),
            "source_bloomery_head_after": cl.get("source_bloomery_head_after"),
            "source_bloomery_porcelain_before":
                pins.get("source_bloomery_porcelain_before"),
            "source_bloomery_porcelain_after":
                cl.get("source_bloomery_porcelain_after"),
            "source_bloomery_unchanged": cl.get("source_bloomery_unchanged"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_arm": raw.get("arm_checkout_loads"),
            "target_disk_free_gb": pins.get("target_disk_free_gb"),
            "target_disk_free_gb_after": cl.get("target_disk_free_gb_after"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "frozen_denominator": pins.get("frozen_denominator"),
        },
        "endpoints": {
            "E6": _e6(raw),
            "E6prime": _e6prime(raw),
            "E2pp": _e2pp(raw),
            "E7pp": _e7pp(raw),
            "E3pp": _e3(raw, False),
            "E5pp": _e5(raw, False),
            "E0pp": _e0pp(raw),
        },
        "reported": _reported(raw),
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }
