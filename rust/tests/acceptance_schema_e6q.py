"""Raw E6⁗ facts -> `results.json` in the pre-registered shape.

Same rules as `acceptance_schema.assemble`, `acceptance_schema_rung3.
assemble_rung3` and `acceptance_schema_e6ppp.assemble_e6ppp`: every
measurement is `{"value", "n", "lens", "dropped"}`, a `null` value with a
non-empty `dropped` list is the ONLY representation of not-measured, and `0`
is measured-and-zero.

Nothing here decides a verdict, and nothing here counts a false accusation.
§1 of `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md` asks for
every printed SWALLOWED line to be adjudicated against the CLONE'S SOURCE by
the acceptance author. That is a reading, not a computation: all three arms'
false-accusation headlines are `null` with the reason, and what the schema
publishes is every line that had to be adjudicated.

The control arm carries one extra pair of cells, and the difference between
them is the point: `lines_at_flipped_sites` is COMPUTED (how many of the
control's SWALLOWED lines land at a site the flip diff lists) and
`discriminating` is `null` (whether any of them is a FALSE accusation is
§4's reading). A control whose verdict was derived from the count would be a
control that could not fail -- the failure design B5 exists to prevent.

E6-again′, E7⁗ and E0‴ are §1's rows verbatim, so their blocks are the
COMMITTED rung-3 functions (`acceptance_schema_rung3._e6`, `._e7pp`,
`._e0pp`), called over this document's raw keys. A second copy would be a
second schema.
"""

from __future__ import annotations

from acceptance_lib import meas
from acceptance_schema_e6ppp import (BY_HAND, GUARDED_ARMS,         # noqa: F401
                                     GUARDED_PROVENANCE, _drop,
                                     _sweep_added)
from acceptance_schema_rung3 import _e0pp, _e6, _e7pp               # noqa: F401

DOC = ("docs/superpowers/acceptance/"
       "2026-09-05-sensorium-rung3-e6q.md")

#: The three arms of §1, named in the words the lens uses. The runner holds
#: the same three as argument lists and cannot be imported here (it imports
#: this module), so `tests/test_acceptance_e6q.py` asserts the two agree.
ARMS = {
    "E6qA": {"key": "raw_arm_a", "label": "E6⁗-A",
             "selector": "-p bloomery-daemon", "tail": "--lib",
             "driver": "head"},
    "E6qWS": {"key": "raw_arm_ws", "label": "E6⁗-WS",
              "selector": "--workspace", "tail": "", "driver": "head"},
    "E6qWS0": {"key": "raw_arm_ws0", "label": "E6⁗-WS0",
               "selector": "--workspace", "tail": "", "driver": "base"},
}

DRIVERS = {
    "head": "the HEAD driver of §2, built `--release` by the runner",
    "base": ("the BASE driver of §2, built `--release` from the pre-repair "
             "`d1b1b57`, into its OWN from-scratch target and its OWN trace "
             "store"),
}

#: The reason the control's verdict is null. Design B5: the control licenses
#: the claim only if a HAND reading finds a false accusation at a flip-set
#: arm; a count of lines is what that reading works from, never the reading.
BY_HAND_CONTROL = ("decided by the hand adjudication of §4: ≥ 1 FALSE "
                   "accusation at a flip-set arm")

#: The guarded-arm count of each arm (design B4/R15). It RESTATES §5 of THIS
#: document, which the measurement task writes; until then there is no
#: adjudication to restate and every cell is `null` with that reason. E6‴'s
#: `GUARDED_ARMS` is imported but deliberately not used: another document's
#: hand count is not this one's.
#: Filled 2026-09-05 from the measurement's own hand adjudication (§4.2-§4.4,
#: restated in §5.3): the SWALLOWED lines whose `Err` binding is read ONLY by a
#: match guard. E6⁗-A's 2 are `memory/store.rs:96`; the WS arms' 374 are that
#: site (41) plus `http.rs:236` (303), `drift.rs:694` (14), `:291` (8), `:457`
#: (4) and `task/exec.rs:380` (4). Not a new measurement -- the same count the
#: record publishes by hand, in the cell where a reader compares the readings.
GUARDED_ARMS_E6Q: dict = {"raw_arm_a": 2, "raw_arm_ws": 374,
                          "raw_arm_ws0": 374}
GUARDED_PROVENANCE_E6Q = "hand adjudication, §4.4 of this document"


def _frozen(raw) -> dict:
    """§1's frozen census -- the FIVE numbers §1 carries -- from wherever the
    run recorded it. Never re-derived: a denominator computed at run time is
    not a frozen one."""
    return (raw.get("frozen_census")
            or (raw.get("config") or {}).get("frozen_census") or {})


def _ledger_census(raw) -> dict:
    """Census numbers the T0/T1 runs read that §1 does NOT freeze. Published
    beside the frozen five, never under their label."""
    return (raw.get("ledger_census")
            or (raw.get("config") or {}).get("ledger_census") or {})


def _arm(raw, spec: dict) -> dict:
    """One E6⁗ arm, in §1's shape.

    `swallowed_lines` is the PRIMARY process's count -- §1's `exceptions
    <run>`. `union_swallowed_lines` adds the sweep over every other process
    the same arm recorded; it is what §4 adjudicates, because on a
    `--workspace` arm the integration-test and doctest processes the primary
    trace never saw are exactly what the arm exists to look at."""
    key = spec["key"]
    r = raw.get(key) or {}
    dropped = _drop(raw, key)
    sweep = r.get("sweep") or {}
    n = r.get("swallowed_count")
    union = r.get("union_swallowed_count")
    cmdline = " ".join(x for x in ("cargo sensorium test", spec["selector"],
                                   spec["tail"]) if x)
    lens = (f"`{cmdline}` on the clone at e209ed9 under "
            f"{DRIVERS[spec['driver']]}, from a target its prep build "
            f"emptied, then `sensorium exceptions <run> --limit 100000` "
            f"captured whole on the process with the most events, and again "
            f"on every other process the arm recorded (the sweep)")
    return {
        "headline": meas(
            None, union if union is not None else n,
            "FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks "
            "for every printed SWALLOWED line to be adjudicated against the "
            "clone's SOURCE, which is a reading, not a computation. The "
            "counts and the adjudication table are §4 of the document; what "
            "is here is every line that had to be adjudicated. " + lens,
            [BY_HAND]),
        "swallowed_lines": meas(n, r.get("chains_in_scope"),
                                "printed SWALLOWED lines on the PRIMARY "
                                "process, of the chains in scope; " + lens,
                                dropped),
        "union_swallowed_lines": meas(
            union, r.get("processes"),
            "printed SWALLOWED lines over EVERY process this arm recorded "
            "(primary + sweep), of the processes recorded; " + lens, dropped),
        "sweep_swallowed_lines": _sweep_added(sweep, dropped),
        "unparsed_swallowed_lines": meas(
            (None if n is None else
             r.get("unparsed_swallowed", 0)
             + sum(1 for p in (sweep.get("swallowed_parsed") or [])
                   if p.get("unparsed"))),
            union,
            "SWALLOWED lines the collector could not parse into "
            "(how, event, qualname, line) -- anything but 0 means a row of "
            "the adjudication table was assembled by hand", dropped),
        "guarded_arms": {
            **meas(GUARDED_ARMS_E6Q.get(key) if n is not None else None,
                   union if union is not None else n,
                   "SWALLOWED lines whose `Err` binding is read ONLY by a "
                   "match GUARD -- the class §1's reading of \"merely "
                   "observed\" does not settle, reported beside both "
                   "readings per design B4/R15. NOT a new measurement: it "
                   "restates the count §4.4 of this document publishes by "
                   "hand, which §5.3 repeats.",
                   ["the arm did not run, so there is no adjudication to "
                    "restate"] if n is None else []),
            "provenance": GUARDED_PROVENANCE_E6Q},
        "chains_in_scope": meas(r.get("chains_in_scope"), None,
                                "`raised (N):` on the primary process -- Err "
                                "chains the command judged", dropped),
        "processes": meas(r.get("processes"), None,
                          "processes the arm recorded (one per test binary, "
                          "including integration-test and doctest binaries "
                          "on a `--workspace` arm)", dropped),
        "selector": r.get("selector"), "tail": r.get("tail"),
        "command": cmdline,
        "driver_role": spec["driver"],
        "driver": r.get("driver"), "driver_sha256": r.get("driver_sha256"),
        "driver_identity": r.get("driver_identity"),
        "target": r.get("target"),
        "tally": r.get("tally"), "tally_line": r.get("tally_line"),
        "partial_line": r.get("partial_line"),
        "panics_line": r.get("panics_line"),
        "more_note": r.get("more_note"),
        "run": r.get("run"), "events": r.get("events"),
        "rc": r.get("rc"), "exceptions_rc": r.get("exceptions_rc"),
        "wall_s": r.get("wall"), "exceptions_wall_s": r.get("exceptions_wall"),
        "per_process": r.get("per_process"),
        "swallowed": r.get("swallowed_parsed"),
        "swallowed_sweep": sweep.get("swallowed_parsed"),
        "sweep_processes": sweep.get("swept"),
        "trace": r.get("counts"),
        "sensorium_dir": r.get("sensorium_dir"),
        "dropped": r.get("dropped"),
    }


def _control(raw, block: dict) -> dict:
    """The control arm's two extra cells: the COMPUTED evidence, and the
    verdict that is not computed."""
    lines = ((raw.get("raw_flip_lines") or {}).get("ws0") or {})
    dropped = _drop(raw, "raw_arm_ws0")
    have = bool(lines)
    block["lines_at_flipped_sites"] = meas(
        lines.get("count") if have else None, lines.get("flip_sites"),
        "COMPUTED EVIDENCE for §4: SWALLOWED lines of this arm whose sink "
        "resolves to a (file, line) the E-flip diff lists, of the flipped "
        "sites. It is the set of lines the hand adjudication must READ; it "
        "is never the verdict, and a line at a flipped site is not yet a "
        "false accusation.",
        dropped if have else
        [*dropped, "the flip-set line count was not recorded"])
    block["lines_at_flipped_sites_unresolved"] = meas(
        lines.get("unresolved") if have else None, lines.get("read"),
        "SWALLOWED lines of this arm whose sink could not be resolved to a "
        "(file, line) under the clone root -- anything but 0 means the "
        "evidence above is over a subset", dropped if have else ["not "
        "recorded"])
    block["discriminating"] = meas(
        None, lines.get("count"),
        "Whether the control REACHED the shape the repair is for. Design B5: "
        "if the pre-repair driver prints ≥ 1 FALSE accusation at an arm "
        "E-flip lists and the repaired driver prints none there, the record "
        "may say the repair removed a false accusation the arm reached; a 0 "
        "makes E6⁗-WS NOT DISCRIMINATING and the record says so. Not a merge "
        "gate either way.",
        [BY_HAND_CONTROL])
    block["flip_lines"] = lines.get("lines")
    return block


def _flip(raw) -> dict:
    """E-flip: which arms the repair moved, exactly.

    The gate is a conjunction, so the headline is the one number that must be
    zero -- changed rows whose transition is NOT `arm_handled ->
    arm_ambiguous` -- and the two named rows and the frozen delta are their
    own cells beside it."""
    f = raw.get("raw_flip") or {}
    frozen = _frozen(raw)
    dropped = _drop(raw, "raw_flip")
    changed = f.get("changed_count")
    tr = f.get("transitions")
    other = (None if tr is None
             else sum(v for k, v in tr.items() if k != "arm_handled->arm_ambiguous"))
    before = frozen.get("arms_handled_before")
    after = frozen.get("arms_handled_after")
    delta = None if before is None or after is None else before - after
    lens = ("`kind: \"arm\"` manifest rows of two from-scratch `--workspace "
            "--no-run` builds -- the BASE driver into the control target, the "
            "HEAD driver into the acceptance target -- keyed (file, line), "
            "with the `how` each build writes")
    return {
        "headline": meas(
            other, changed,
            "changed manifest rows whose transition is NOT `arm_handled -> "
            "arm_ambiguous`, of the changed rows; §1's gate is 0. " + lens,
            dropped if tr is not None else
            [*dropped, "the flip diff recorded no transition table"]),
        "changed_count": meas(changed, f.get("sites_after"),
                              "manifest rows whose `how` differs between the "
                              "two builds, of the arm sites the AFTER build "
                              "declared; " + lens, dropped),
        "only_handled_to_ambiguous": meas(
            f.get("only_handled_to_ambiguous"), changed,
            "true only when there is at least one transition and every one "
            "of them is `arm_handled -> arm_ambiguous`; an empty diff is not "
            "a pass. " + lens, dropped),
        "named_all_flipped": meas(
            f.get("named_all_flipped"), len(f.get("named") or {}),
            "true when EVERY row §1 names by hand (`api_v1.rs:396` and "
            "`:515`) read `arm_handled` before and `arm_ambiguous` after; a "
            "row missing from either build is reported, never assumed "
            "flipped. " + lens, dropped),
        "changed_equals_delta": meas(
            None if changed is None or delta is None else changed == delta,
            changed,
            f"changed rows == §1's FROZEN census delta "
            f"(arms_handled_before {before} − arms_handled_after {after} = "
            f"{delta}), cited from §1 and never re-derived; " + lens,
            dropped if delta is not None else
            [*dropped, "§1's frozen handled counts were not recorded"]),
        "only_before_count": meas(
            f.get("only_before_count"), f.get("sites_before"),
            "arm sites the BASE build declared and the HEAD build did not -- "
            "evidence about the builds, not about the rule; " + lens,
            dropped),
        "only_after_count": meas(
            f.get("only_after_count"), f.get("sites_after"),
            "arm sites the HEAD build declared and the BASE build did not; "
            + lens, dropped),
        "frozen_delta": delta,
        "frozen_census": frozen,
        "ledger_census": _ledger_census(raw),
        "named": f.get("named"),
        "transitions": tr,
        "changed": f.get("changed"),
        "only_before": f.get("only_before"),
        "only_after": f.get("only_after"),
        "multi_how": f.get("multi_how"),
        "sites_before": f.get("sites_before"),
        "sites_after": f.get("sites_after"),
    }


#: The rung-3 lens names the trace E0″ read. This run passes the E6⁗-WS arm's
#: process with the most events, so the string is rewritten -- and ONLY the
#: string: the numbers, the shape and the 60 s gate are the committed
#: function's, because a second copy would be a second protocol.
E0_LENS_WAS = "E6' trace"
E0_LENS_IS = "E6⁗-WS process with the most events"


def _e0ppp(raw) -> dict:
    """E0‴: `acceptance_schema_rung3._e0pp` over this document's raw key,
    with the lens saying which trace was actually read."""
    block = _e0pp({"raw_e0pp": raw.get("raw_e0ppp")})
    for cell in block.values():
        if isinstance(cell, dict) and isinstance(cell.get("lens"), str):
            cell["lens"] = cell["lens"].replace(E0_LENS_WAS, E0_LENS_IS)
    return block


def _dispositions(raw) -> dict:
    """The per-disposition tallies of all three arms, side by side, reported
    without a gate so the widening's cost in volume is visible."""
    out = {}
    for spec in ARMS.values():
        r = raw.get(spec["key"]) or {}
        sweep = r.get("sweep") or {}
        totals = dict(r.get("tally") or {})
        for s in sweep.get("swept") or []:
            line = s.get("tally_line") or ""
            if not line.startswith("dispositions: "):
                continue
            for part in line[len("dispositions: "):].split(", "):
                bits = part.rsplit(" ", 1)
                if len(bits) == 2 and bits[1].isdigit():
                    totals[bits[0]] = totals.get(bits[0], 0) + int(bits[1])
        out[spec["label"]] = {
            "primary_tally_line": r.get("tally_line"),
            "primary_tally": r.get("tally"),
            "all_processes_tally": totals,
            "processes": r.get("processes"),
            "sweep_tally_lines": [s.get("tally_line")
                                  for s in sweep.get("swept") or []],
        }
    return out


def _executed_flipped(raw) -> dict:
    """Of the flip set, which arms each arm EXECUTED. An arm the run never
    reaches is not evidence either way, and the record names which is
    which."""
    ev = raw.get("raw_executed_flipped") or {}
    out = {}
    for spec in ARMS.values():
        label = spec["key"].removeprefix("raw_arm_")
        e = ev.get(label) or {}
        # A null ALWAYS carries its reason: without one the renderer prints
        # `not measured (no reason recorded)`, which is this module's own rule
        # broken at the cell that says which arms the run reached.
        dropped = [*_drop(raw, spec["key"])] if not e else []
        if not e and not dropped:
            dropped = ["the flip set was not joined against this arm's "
                       "traces on this run"]
        out[spec["label"]] = {
            "executed": meas(e.get("executed"), e.get("static"),
                             f"{spec['label']}: flipped arm sites this arm "
                             f"EXECUTED (a HANDLED event whose `how` starts "
                             f"`arm_` at that site), of the flipped sites",
                             dropped),
            "executed_rows": [{"file": r.get("file"), "line": r.get("line"),
                               "qualname": r.get("qualname"),
                               "events": r.get("events")}
                              for r in e.get("executed_rows") or []],
            "not_executed_rows": [{"file": r.get("file"),
                                   "line": r.get("line")}
                                  for r in e.get("not_executed_rows") or []],
            "arm_sites_that_fired_at_all": e.get("executed_arm_sites_all"),
            "trace_paths_not_under_the_clone_root":
                e.get("trace_paths_not_under_the_clone_root"),
        }
    return out


def _prep(raw, key: str) -> dict:
    """One from-scratch build that opens the run. PREP, reported, never
    gated."""
    r = raw.get(key) or {}
    b = r.get("build") or {}
    arms = r.get("arms") or {}
    # As above: a prep that did not run, or that dropped, must say so rather
    # than render as `not measured (no reason recorded)`.
    dropped = _drop(raw, key)
    if not arms and not dropped:
        dropped = ["this prep build recorded no `kind: \"arm\"` manifest rows"]
    return {
        "label": r.get("label"), "driver": r.get("driver"),
        "driver_sha256": r.get("driver_sha256"), "target": r.get("target"),
        "rc": b.get("rc"), "wall_s": b.get("wall"),
        "compiled": b.get("compiled"), "fresh": b.get("fresh"),
        "cargo_exit": b.get("cargo_exit"),
        "units": len(b.get("metadata_units") or []),
        "target_emptied_bytes": r.get("target_emptied_bytes"),
        "log": b.get("log"),
        "arm_sites_distinct": meas(arms.get("distinct"), None,
                                   "distinct (file, line) `kind: \"arm\"` "
                                   "manifest rows of this build",
                                   dropped if arms.get("distinct") is None
                                   else []),
        "arm_sites_raw": arms.get("raw"),
        "arm_sites_by_how": arms.get("by_how"),
        "dropped": r.get("dropped"),
    }


def assemble_e6q(raw: dict) -> dict:
    """Raw E6⁗ facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    bd = raw.get("raw_base_driver") or {}
    return {
        "schema": ("every measurement is {value, n, lens, dropped}; a null "
                   "value plus a dropped reason is the ONLY not-measured; 0 "
                   "is measured-and-zero"),
        "acceptance": DOC,
        "runner": raw.get("runner"),
        "byte_lock": raw.get("byte_lock"),
        "pins": pins,
        "environment": {
            "repo_commit": pins.get("repo_commit"),
            "repo_branch": pins.get("repo_branch"),
            "repo_porcelain": pins.get("repo_porcelain"),
            "driver": pins.get("driver"),
            "driver_sha256": pins.get("driver_sha256"),
            "driver_mtime": pins.get("driver_mtime"),
            "driver_unchanged_after": cl.get("driver_unchanged"),
            "base_driver": {
                "driver": bd.get("driver"),
                "driver_sha256": bd.get("driver_sha256"),
                "driver_mtime": bd.get("driver_mtime"),
                "worktree": bd.get("worktree"),
                "expected_commit": bd.get("expected_commit"),
                "head": bd.get("head"),
                "head_matches": bd.get("head_matches"),
                "clean": bd.get("clean"),
                "control_target": bd.get("control_target"),
                "version_read": bd.get("version_read"),
            } if bd else {"dropped": ["the base driver was not verified: the "
                                      "run refused before that step"]},
            "census_driver": pins.get("census_driver"),
            "census_driver_sha256": pins.get("census_driver_sha256"),
            "rustc": pins.get("rustc"), "cargo": pins.get("cargo"),
            "python": pins.get("python"),
            "sensorium_version": pins.get("sensorium_version"),
            "nproc": pins.get("nproc"), "governor": pins.get("governor"),
            "clone": pins.get("clone"), "clone_head": pins.get("clone_head"),
            "clone_porcelain_before": pins.get("clone_porcelain_before"),
            "clone_porcelain_after": cl.get("clone_porcelain_after"),
            "clone_restored": cl.get("clone_restored"),
            "cargo_lock_unchanged": cl.get("cargo_lock_unchanged"),
            "target_dir": pins.get("target_dir"),
            "control_target_dir": bd.get("control_target"),
            "corpus_target": pins.get("corpus_target"),
            "corpus_target_bytes_before":
                pins.get("corpus_target_bytes_before"),
            "probe_target": pins.get("probe_target"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "sensorium_dir_per_arm": {
                spec["label"]: (raw.get(spec["key"]) or {}).get(
                    "sensorium_dir") for spec in ARMS.values()},
            "driver_per_arm": {
                spec["label"]: (raw.get(spec["key"]) or {}).get("driver")
                for spec in ARMS.values()},
            "driver_version_per_arm": {
                spec["label"]: ((raw.get(spec["key"]) or {}).get(
                    "driver_identity") or {}).get("driver_versions")
                for spec in ARMS.values()},
            "target_per_arm": {
                spec["label"]: (raw.get(spec["key"]) or {}).get("target")
                for spec in ARMS.values()},
            "source_bloomery": pins.get("source_bloomery"),
            "source_bloomery_head_before":
                pins.get("source_bloomery_head_before"),
            "source_bloomery_head_after": cl.get("source_bloomery_head_after"),
            "source_bloomery_porcelain_before":
                pins.get("source_bloomery_porcelain_before"),
            "source_bloomery_porcelain_after":
                cl.get("source_bloomery_porcelain_after"),
            "source_bloomery_unchanged": cl.get("source_bloomery_unchanged"),
            "built_from": raw.get("raw_built_from") or {
                "dropped": ["not recorded: the runner did not build the HEAD "
                            "driver on this run"]},
            "logs_dir": raw.get("logs"),
            "prep_head_log": ((raw.get("raw_prep_head") or {}).get("build")
                              or {}).get("log"),
            "prep_base_log": ((raw.get("raw_prep_base") or {}).get("build")
                              or {}).get("log"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_arm": raw.get("arm_loads"),
            "target_disk_free_gb": pins.get("target_disk_free_gb"),
            "target_disk_free_gb_after": cl.get("target_disk_free_gb_after"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "frozen_census": _frozen(raw),
            "ledger_census": _ledger_census(raw),
        },
        "endpoints": {
            "E6qA": _arm(raw, ARMS["E6qA"]),
            "E6qWS": _arm(raw, ARMS["E6qWS"]),
            "E6qWS0": _control(raw, _arm(raw, ARMS["E6qWS0"])),
            "Eflip": _flip(raw),
            "E6again": _e6(raw),
            "E7q": _e7pp(raw),
            "E0ppp": _e0ppp(raw),
        },
        "reported": {
            "dispositions": _dispositions(raw),
            "executed_flipped_arms": _executed_flipped(raw),
            "flip_lines_ws": (raw.get("raw_flip_lines") or {}).get("ws"),
            "flip_lines_ws0": (raw.get("raw_flip_lines") or {}).get("ws0"),
            "prep_head": _prep(raw, "raw_prep_head"),
            "prep_base": _prep(raw, "raw_prep_base"),
        },
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }
