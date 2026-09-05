"""Raw rung-4 entry facts -> `results.json` in the pre-registered shape.

Same rules as `acceptance_schema.assemble`, `acceptance_schema_rung3.
assemble_rung3` and `acceptance_schema_e6q.assemble_e6q`: every measurement
is `{"value", "n", "lens", "dropped"}`, a `null` value with a non-empty
`dropped` list is the ONLY representation of not-measured, and `0` is
measured-and-zero.

ONE RULE THIS SCHEMA HAS THAT ITS SIBLINGS DO NOT
--------------------------------------------------
The ORACLE is already in the room. Every number H2, H3 and H4 are compared
against was measured on 2026-09-05 and published, and this run reads it. So
the rule the tests pin hardest is: **no headline is ever filled from the
oracle.** A phase that did not run reaches the document as `null` with its
reason, and the oracle is published beside it under its own name
(`results["oracle"]`), never inside a measurement cell. A schema that fell
back to the record when a measurement was missing would report the record as
its own result, and H2/H4 could not fail.

H1 is §1's E6 row verbatim, so its block is the COMMITTED rung-3 function
(`acceptance_schema_rung3._e6`) called over the same raw key. A second copy
would be a second schema.
"""

from __future__ import annotations

from acceptance_grain_read import with_every_vary_kind
from acceptance_lib import meas
from acceptance_schema_rung3 import _drop, _e6                     # noqa: F401

DOC = ("docs/superpowers/acceptance/"
       "2026-09-05-sensorium-rung4-entry-grain.md")

#: The one sentence every "this phase did not run" reason is built from, so
#: six cells cannot drift apart in what they say they did not measure.
NOT_RUN = "the phase did not run, so there is nothing to compare"

#: Named once and used by every cell that mentions where the expected number
#: came from, so no cell can quietly claim the oracle was re-measured.
ORACLE_LENS = ("compared against the PUBLISHED E6⁗ record "
               "(`docs/superpowers/acceptance/"
               "2026-09-05-sensorium-rung3-e6q.results.json`), read and "
               "never re-measured")


def _null(reason: str, lens: str, n=None) -> dict:
    return meas(None, n, lens, [reason])


# ------------------------------------------------------------------- H2


def _h2(raw) -> dict:
    r = raw.get("raw_h2")
    lens = (f"`sensorium exceptions <the A run> --limit 100000` on the kept "
            f"`a` store; each SWALLOWED group's chain count booked at the "
            f"SINK its verdict names, resolved through the trace's own "
            f"`events` -> `code_objects` join; {ORACLE_LENS}")
    if not r:
        return {
            "headline": _null(NOT_RUN, "site-table differences; " + lens),
            "groups": _null(NOT_RUN, "SWALLOWED groups printed"),
            "chains": _null(NOT_RUN, "chains those groups account for"),
            "tally_line_equal": _null(NOT_RUN, "the printed `dispositions:` "
                                               "line vs the record's"),
            "unresolved_sinks": _null(NOT_RUN, "sinks the join could not "
                                               "resolve"),
        }
    c = r.get("compare") or {}
    dropped = _drop(raw, "raw_h2")
    return {
        "headline": meas(c.get("differences"), c.get("expected_sites"),
                         "site-table differences (missing + extra + count "
                         "diffs), of the record's sites; " + lens, dropped),
        "groups": meas(r.get("groups"), r.get("chains"),
                       "SWALLOWED groups printed, of the chains they account "
                       "for -- §1 predicts 5 groups over 14 chains", dropped),
        "chains": meas(r.get("chains"), c.get("expected_lines"),
                       "chains the groups account for, of the record's "
                       "SWALLOWED lines; " + lens, dropped),
        "tally_line_equal": meas(r.get("tally_line_equal"), None,
                                 "the printed `dispositions:` line is "
                                 "byte-identical to the record's for this "
                                 "process", dropped),
        "unresolved_sinks": meas(r.get("unresolved_sinks"), r.get("groups"),
                                 "SWALLOWED groups whose sink event the "
                                 "trace does not hold -- anything but 0 is a "
                                 "hole in the comparison, not a difference",
                                 dropped),
        "compare": c, "measured_sites": r.get("measured_sites"),
        "tally_line": r.get("tally_line"),
        "oracle_tally_line": r.get("oracle_tally_line"),
        "run": r.get("run"), "rc": r.get("rc"), "wall_s": r.get("wall"),
        "command": r.get("command"), "log": r.get("log"),
        "stdout_bytes": r.get("stdout_bytes"),
        "stdout_lines": r.get("stdout_lines"),
        "vary": r.get("vary"), "header": r.get("header"),
    }


# ------------------------------------------------------------------- H3


def _h3(raw) -> dict:
    r = raw.get("raw_h3")
    lens = (f"`sensorium exceptions <run> --limit 100000` on EVERY trace of "
            f"the kept `ws` and `ws0` stores (144 + 144); per process the "
            f"printed `dispositions:` line against the record's, and the sum "
            f"of the SWALLOWED groups' chain counts against the record's "
            f"`swallowed_count`; a process the record holds `None` for "
            f"printed `no exceptions recorded` and is checked for THAT "
            f"shape, never for a zero; {ORACLE_LENS}")
    if not r:
        return {"headline": _null(NOT_RUN, "processes that differ; " + lens),
                "comparisons": _null(NOT_RUN, "per-process comparisons made"),
                "arms": {a: {"unequal_tally_lines": _null(NOT_RUN, lens),
                             "unequal_swallow_counts": _null(NOT_RUN, lens)}
                         for a in ("ws", "ws0")}}
    dropped = _drop(raw, "raw_h3")
    arms = r.get("arms") or {}
    out = {
        "headline": meas(r.get("unequal"), r.get("comparisons"),
                         "per-process comparisons that differ (a tally line "
                         "or a swallow count), of the comparisons made; "
                         + lens, dropped),
        "comparisons": meas(r.get("comparisons"), None,
                            "processes read, over both arms", dropped),
        "arms": {},
    }
    for label, a in arms.items():
        out["arms"][label] = {
            "processes": meas(a.get("processes"), None,
                              f"traces read in the kept `{label}` store",
                              dropped),
            "unequal_tally_lines": meas(
                len(a.get("unequal_tally_lines") or []), a.get("processes"),
                "processes whose printed `dispositions:` line is not the "
                "record's (or which did not print the empty-answer shape "
                "where the record has none); " + lens, dropped),
            "unequal_swallow_counts": meas(
                len(a.get("unequal_swallow_counts") or []),
                a.get("processes"),
                "processes where the SWALLOWED groups' chains do not sum to "
                "the record's `swallowed_count`; " + lens, dropped),
            "chains_total": meas(a.get("chains_total"), a.get("groups_total"),
                                 "chains over this arm, of the groups they "
                                 "were printed as", dropped),
            "unequal_tally_line_runs": a.get("unequal_tally_lines"),
            "unequal_swallow_count_runs": a.get("unequal_swallow_counts"),
            "runs_only_in_the_store": a.get("runs_only_in_the_store"),
            "runs_only_in_the_record": a.get("runs_only_in_the_record"),
            "stdout_bytes_total": a.get("stdout_bytes_total"),
            "stdout_lines_total": a.get("stdout_lines_total"),
            "vary": a.get("vary"),
            "rows": [{k: v for k, v in row.items() if k != "stdout"}
                     for row in a.get("rows") or []],
        }
    return out


# ------------------------------------------------------------------- H4


def _h4_arm(a: dict | None, label: str, dropped: list) -> dict:
    lens = (f"`sensorium exceptions <the {label} invocation id> --limit "
            f"100000`; each merged SWALLOWED group's chain count booked at "
            f"the sink its verdict names, resolved in the trace the bracket "
            f"NAMES; {ORACLE_LENS}")
    if not a:
        return {
            "site_differences": _null(NOT_RUN, "site-table differences; "
                                      + lens),
            "groups": _null(NOT_RUN, "merged SWALLOWED groups printed"),
            "chains": _null(NOT_RUN, "chains those groups account for"),
            "tally_equal": _null(NOT_RUN, "the summed `dispositions:` line "
                                          "vs the record's summed tally"),
            "header_counts_equal": _null(NOT_RUN, "the header's N / k / m"),
            "incomplete_members": _null(NOT_RUN, "members never finalized"),
            "unresolved_sinks": _null(NOT_RUN, "sinks the join could not "
                                               "resolve"),
        }
    c = a.get("compare") or {}
    return {
        "site_differences": meas(c.get("differences"), c.get("expected_sites"),
                                 "missing + extra + count diffs against the "
                                 "record's per-site table, of its sites; "
                                 + lens, dropped),
        "groups": meas(a.get("groups"), c.get("expected_sites"),
                       "merged SWALLOWED groups printed, of the record's "
                       "sites; " + lens, dropped),
        "chains": meas(a.get("chains"), c.get("expected_lines"),
                       "chains the groups account for, of the record's "
                       "SWALLOWED lines; " + lens, dropped),
        "tally_equal": meas(a.get("tally_equal"), None,
                            "the printed `dispositions:` counts equal the "
                            "record's SUM over its per-process tally lines; "
                            + lens, dropped),
        "header_counts_equal": meas(
            a.get("header_counts_equal"), a.get("header", {}).get("processes"),
            "the header's `N processes, k with Err chains, m with none` "
            "against the record's process count, its processes WITH a tally "
            "line, and those without; " + lens, dropped),
        "incomplete_members": meas(
            len(a.get("incomplete_members") or []),
            a.get("header", {}).get("processes"),
            "members the answer named INCOMPLETE, of the members", dropped),
        "unresolved_sinks": meas(a.get("unresolved_sinks"), a.get("groups"),
                                 "groups whose sink event the named trace "
                                 "does not hold -- a hole, not a difference",
                                 dropped),
        "compare": c, "header": a.get("header"),
        "measured_sites": a.get("measured_sites"),
        "oracle_tally": a.get("oracle_tally"),
        "invocation": a.get("invocation"), "command": a.get("command"),
        "rc": a.get("rc"), "wall_s": a.get("wall"), "log": a.get("log"),
        "stdout_bytes": a.get("stdout_bytes"),
        "stdout_lines": a.get("stdout_lines"),
        "processes_named": a.get("processes_named"),
        "vary": a.get("vary"),
    }


def _h4(raw) -> dict:
    r = raw.get("raw_h4")
    arms = (r or {}).get("arms") or {}
    dropped = _drop(raw, "raw_h4")
    blocks = {label: _h4_arm(arms.get(label), label, dropped)
              for label in ("ws", "ws0")}
    diffs = [b["site_differences"]["value"] for b in blocks.values()]
    measured = [d for d in diffs if d is not None]
    lens = ("site-table differences summed over both invocation answers; "
            + ORACLE_LENS)
    headline = (meas(sum(measured), len(blocks), lens, dropped)
                if len(measured) == len(blocks)
                else _null(NOT_RUN if not r else
                           "one or both arms did not produce a comparison",
                           lens, len(blocks)))
    return {"headline": headline, "arms": blocks}


# ------------------------------------------------------------------- H5


def _h5(raw) -> dict:
    r = raw.get("raw_h4")
    lens = ("wall of H4's two `exceptions <invocation-id>` commands, 60 s "
            "kill ARMED; a kill is recorded as a kill, never raised")
    if not r:
        return {"headline": _null(NOT_RUN, "slowest invocation answer, s",
                                  2),
                "walls_s": _null(NOT_RUN, lens, 2),
                "killed": _null(NOT_RUN, "arms the kill fired on", 2)}
    dropped = _drop(raw, "raw_h4")
    walls = r.get("walls") or {}
    killed = r.get("killed") or []
    return {
        "headline": meas(max(walls.values()) if walls else None, len(walls),
                         "the SLOWEST of the two answers, seconds, of the "
                         "arms timed; " + lens, dropped),
        "walls_s": meas(walls, len(walls), lens, dropped),
        "killed": meas(len(killed), len(walls),
                       "arms the 60 s kill fired on -- any is a STOP on H5",
                       dropped),
        "killed_arms": killed,
    }


# ------------------------------------------------------------------- H6


def _h6(raw) -> dict:
    r = raw.get("raw_h6")
    lens = ("the whole Python suite from the repo root under `plain_env()` "
            "plus `SENSORIUM_CARGO_SENSORIUM` (so the module that is skipped "
            "without a built driver RUNS), and `cargo test --workspace` in "
            "`rust/` -- the crates are unchanged by this slice, so it "
            "compiles nothing")
    if not r:
        return {"headline": _null(NOT_RUN, "pytest exit status; " + lens),
                "pytest_summary": _null(NOT_RUN, "the suite's summary line"),
                "cargo_rc": _null(NOT_RUN, "`cargo test --workspace` exit "
                                           "status")}
    dropped = _drop(raw, "raw_h6")
    py = r.get("python") or {}
    cargo = r.get("cargo") or {}
    return {
        "headline": meas(py.get("rc"), None,
                         "`pytest -q` exit status -- 0 is green; " + lens,
                         dropped),
        "pytest_summary": meas(py.get("summary"), None,
                               "the suite's own summary line, recorded whole",
                               dropped),
        "pytest_wall_s": meas(py.get("wall"), None, "seconds", dropped),
        "cargo_rc": meas(cargo.get("rc"), len(cargo.get("result_lines") or []),
                         "`cargo test --workspace` exit status, of its "
                         "`test result:` lines", dropped),
        "cargo_result_lines": cargo.get("result_lines"),
        "cargo_wall_s": cargo.get("wall"),
        "python_log": py.get("log"), "cargo_log": cargo.get("log"),
        "python_env": py.get("env"),
        "driver_sha256_after": r.get("driver_sha256_after"),
    }


# --------------------------------------------------------------- assemble


def _reported(raw: dict) -> dict | None:
    """§1's ungated block, as the run recorded it -- with every vary spelling
    zero-filled.

    The raw record is never rewritten, so a run whose `reported` predates
    `with_every_vary_kind` (2026-09-05, fix round 1) still assembles with
    `details: 0` present. Nothing else here is derived: no count is changed,
    and a kind that fired keeps the number the run measured.
    """
    rep = raw.get("raw_reported")
    if not rep:
        return rep
    return dict(rep) | {
        "vary_lines_by_kind": with_every_vary_kind(rep.get("vary_lines_by_kind"))}


def assemble_grain(raw: dict) -> dict:
    """Raw rung-4 entry facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    orc = raw.get("oracle") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero"),
        "acceptance": DOC,
        "runner": raw.get("runner"),
        "byte_lock": raw.get("byte_lock"),
        "pins": pins,
        # The oracle, published under its OWN name and never inside a
        # measurement. Every "expected" number in every cell above came from
        # here; a reader can check the arithmetic without opening the record.
        "oracle": {
            "record": (raw.get("config") or {}).get("oracle_record"),
            "commit": (raw.get("config") or {}).get("oracle_commit"),
            "sha256": pins.get("oracle_sha256"),
            "sites": orc.get("sites"), "lines": orc.get("lines"),
            "tallies": orc.get("tallies"),
            "tally_lines": orc.get("tally_lines"),
            "without_a_tally_line": orc.get("without_a_tally_line"),
            "processes": orc.get("processes"), "runs": orc.get("runs"),
            "note": ("read from the committed record; nothing here was "
                     "measured by this run, and no endpoint above is filled "
                     "from it"),
        },
        "environment": {
            "repo_commit": pins.get("repo_commit"),
            "repo_branch": pins.get("repo_branch"),
            "repo_porcelain": pins.get("repo_porcelain"),
            "repo_porcelain_after": cl.get("repo_porcelain_after"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_version": pins.get("driver_version"),
            "driver_mtime": pins.get("driver_mtime"),
            "driver_rebuilt_by_this_run": pins.get(
                "driver_rebuilt_by_this_run"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "stores_root": pins.get("stores_root"),
            "stores_before": pins.get("stores_before"),
            "stores_after": cl.get("stores_after"),
            "store_invocations": pins.get("store_invocations"),
            "kept_traces_unchanged": cl.get("kept_traces_unchanged"),
            "invocations_jsonl_lines_added": cl.get(
                "invocations_jsonl_lines_added"),
            "read_only_reading": pins.get("read_only_reading"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "fresh_sensorium_dir_traces": cl.get(
                "fresh_sensorium_dir_traces"),
            "corpus_target": pins.get("corpus_target"),
            "corpus_target_bytes_after": cl.get("corpus_target_bytes_after"),
            "rust_target": pins.get("rust_target"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_phase": raw.get("arm_loads"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "repo_disk_free_gb_after": cl.get("repo_disk_free_gb_after"),
            "logs_dir": raw.get("logs"),
        },
        "endpoints": {
            "H1": _e6(raw),
            "H2": _h2(raw), "H3": _h3(raw), "H4": _h4(raw),
            "H5": _h5(raw), "H6": _h6(raw),
        },
        "reported": _reported(raw),
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }
