"""Raw E6‴ facts -> `results.json` in the pre-registered shape.

Same rules as `acceptance_schema.assemble` and `acceptance_schema_rung3.
assemble_rung3`: every measurement is `{"value", "n", "lens", "dropped"}`, a
`null` value with a non-empty `dropped` list is the ONLY representation of
not-measured, and `0` is measured-and-zero.

Nothing here decides a verdict, and nothing here counts a false accusation.
§1 of `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` asks
for every printed SWALLOWED line to be adjudicated against the CLONE'S SOURCE
by the acceptance author, under two readings. That is a reading, not a
computation: both arms' false-accusation headlines are `null` with the reason,
and what the schema publishes is every line that had to be adjudicated.

E6-again and E7‴ are §1's E6 and E7″ rows verbatim, so their blocks are the
COMMITTED rung-3 functions (`acceptance_schema_rung3._e6`, `._e7pp`), called
over the same raw keys. A second copy would be a second schema.
"""

from __future__ import annotations

from acceptance_lib import meas
from acceptance_schema_rung3 import _drop, _e6, _e7pp              # noqa: F401

DOC = ("docs/superpowers/acceptance/"
       "2026-09-05-sensorium-rung3-e6ppp.md")

#: The reason both arms' headline values are `null`. One string, used twice,
#: so the two arms cannot drift apart in what they say they did not measure.
BY_HAND = ("adjudicated by hand in §4 of the acceptance document, under both "
           "the amended reading (the gate) and the strictest pre-lock reading "
           "of \"merely observed\"")

#: The GUARDED-ARM count of each arm: the SWALLOWED lines whose `Err` binding
#: is read only by a match GUARD (`Err(e) if e.kind() == io::ErrorKind::
#: NotFound => { }`), which is the one class §1's "read by a `&self`
#: predicate" clause does not settle. Design R15 (`1770515`, committed AFTER
#: the 2026-09-05 run) requires it beside both readings in every acceptance
#: table.
#:
#: These are NOT a new measurement and nothing here derives them. They restate
#: the number §5.2 of the document already published by hand -- rows 3 and 5
#: of §4.1, rows 2 and 7 of §4.2 -- and every cell carries that provenance. A
#: run whose arm printed nothing has nothing to restate and gets `null` with a
#: reason, never this constant.
GUARDED_ARMS = {"raw_e6ppp_a": 2, "raw_e6ppp_w": 2}
GUARDED_PROVENANCE = "hand adjudication, §5.2"


def _arm(raw, key: str, selector: str) -> dict:
    """One E6‴ arm, in §1's shape.

    `swallowed_lines` is the PRIMARY process's count -- §1's `exceptions
    <run>`. `union_swallowed_lines` adds the sweep over every other process
    the same arm recorded; it is what §4 adjudicates, because an arm the
    primary trace never saw is exactly what E6‴-W exists to look at."""
    r = raw.get(key) or {}
    dropped = _drop(raw, key)
    sweep = r.get("sweep") or {}
    n = r.get("swallowed_count")
    union = r.get("union_swallowed_count")
    lens = (f"`cargo sensorium test {selector} --lib` on the clone at e209ed9 "
            f"under the driver of §2, then `sensorium exceptions <run> "
            f"--limit 100000` captured whole on the process with the most "
            f"events, and again on every other process the arm recorded "
            f"(the sweep)")
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
            **meas(GUARDED_ARMS.get(key) if n is not None else None,
                   union if union is not None else n,
                   "SWALLOWED lines whose `Err` binding is read ONLY by a "
                   "match GUARD -- the class §1's \"read by a `&self` "
                   "predicate\" clause does not settle, reported beside both "
                   "readings per design R15. NOT a new measurement: it "
                   "restates the count §5.2 of the document published by "
                   "hand, and under the letter-reading of that clause these "
                   "lines would be FALSE and the endpoint a STOP.",
                   [] if n is not None else
                   ["the arm did not run, so there is no adjudication to "
                    "restate"]),
            "provenance": GUARDED_PROVENANCE},
        "chains_in_scope": meas(r.get("chains_in_scope"), None,
                                "`raised (N):` on the primary process -- Err "
                                "chains the command judged", dropped),
        "processes": meas(r.get("processes"), None,
                          "processes the arm recorded (one per test binary)",
                          dropped),
        "selector": r.get("selector"),
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
    }


def _sweep_added(sweep: dict, dropped: list) -> dict:
    """What the sweep ADDED -- or `null` with its reason when there was no
    sweep to add anything.

    An arm that recorded ONE process sweeps none, and a `0` there is a 0 OF 0.
    Under this schema's own rule a measured zero says "the sweep read other
    processes and found no SWALLOWED line in them", which is a stronger claim
    than an arm with nothing to sweep can make: the renderer would print `0`
    beside E6‴-W's real `0` over 2 swept processes and the two would read
    alike. Recorded 2026-09-05 by the whole-branch review, after the run: no
    verdict ever read this cell, and no measured number moves (§5.10 of the
    document).
    """
    lens = ("SWALLOWED lines the sweep added, of the processes swept; "
            "reported without a gate")
    swept = sweep.get("processes_swept")
    if not swept:
        return meas(None, swept, lens,
                    [*dropped, "the arm recorded a single process, so the "
                               "sweep read none and there was nothing to add: "
                               "a 0 here would be a 0 of 0"])
    return meas(sweep.get("swallowed_count"), swept, lens, dropped)


def _dispositions(raw) -> dict:
    """The per-disposition tallies of both arms, side by side.

    §1 reports them without a gate so the widening's cost in volume is
    visible. The primary process's tally line is the one `exceptions` printed;
    the sweep's tallies are summed beside it, and the sum is labelled a sum."""
    out = {}
    for key, label in (("raw_e6ppp_a", "E6‴-A"), ("raw_e6ppp_w", "E6‴-W")):
        r = raw.get(key) or {}
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
        out[label] = {
            "primary_tally_line": r.get("tally_line"),
            "primary_tally": r.get("tally"),
            "all_processes_tally": totals,
            "processes": r.get("processes"),
            "sweep_tally_lines": [s.get("tally_line")
                                  for s in sweep.get("swept") or []],
        }
    return out


def _blast(raw) -> dict:
    """The blast radius: static, and executed by each arm.

    An arm the run never reaches is not evidence either way, so the record
    carries both halves and names which is which."""
    st = raw.get("raw_blast_static") or {}
    ev = raw.get("raw_executed_vs_static") or {}
    cfg = raw.get("config") or {}
    lens = ("`kind: \"arm\"` rows of the from-scratch `--workspace --no-run` "
            "build's own manifests, scoped to that build's `-C metadata=` "
            "set, intersected with the Task-8 reviewer's static list as "
            "t10-context.md writes it; EXECUTED means the arm's traces carry "
            "a HANDLED event at that (file, line) -- an arm probe fires only "
            "when its arm is taken")
    out = {
        "static_entries_total": meas(st.get("static_entries_total"), None,
                                     "entries in the reviewer's list", []),
        "static_entries_located": meas(
            st.get("static_entries_located"), None,
            "entries carrying a line, so intersectable", []),
        "static_entries_unlocated": meas(
            st.get("static_entries_unlocated"), None,
            "entries named only by file pattern (`codec_fixtures_*`), which "
            "no (file, line) key can match", []),
        "resolved_to_an_arm_site": meas(st.get("resolved_count"),
                                        st.get("static_entries_located"),
                                        lens, []),
        "reading_arm_ambiguous_now": meas(
            st.get("in_blast_radius_now_count"), st.get("resolved_count"),
            "of the resolved entries, those the build's manifests now "
            "classify `arm_ambiguous` -- the class the R2 amendment moves "
            "them to; " + lens, []),
        "unmatched": st.get("unmatched"),
        "ambiguous_suffixes": st.get("ambiguous"),
        "resolved": st.get("resolved"),
        "frozen_census": cfg.get("frozen_census"),
    }
    for arm, label in (("a", "E6‴-A"), ("w", "E6‴-W")):
        e = ev.get(arm) or {}
        out[f"executed_{arm}"] = meas(
            e.get("executed"), e.get("static"),
            f"{label}: located static blast-radius arms this arm EXECUTED, "
            f"of the located static arms; " + lens, [])
        out[f"executed_arm_sites_all_{arm}"] = meas(
            e.get("executed_arm_sites_all"), None,
            f"{label}: distinct arm sites that fired at all (the whole tree, "
            f"not only the blast radius)", [])
        out[f"not_executed_{arm}"] = [
            {"file": r["file"], "line": r["line"]}
            for r in (e.get("not_executed_rows") or [])]
        out[f"executed_rows_{arm}"] = e.get("executed_rows")
        out[f"trace_paths_not_under_the_clone_root_{arm}"] = e.get(
            "trace_paths_not_under_the_clone_root")
    return out


def _prep(raw) -> dict:
    """The from-scratch build that opens the run. PREP, reported, never gated."""
    r = raw.get("raw_prep") or {}
    b = r.get("build") or {}
    arms = r.get("arms") or {}
    return {
        "rc": b.get("rc"), "wall_s": b.get("wall"),
        "compiled": b.get("compiled"), "fresh": b.get("fresh"),
        "cargo_exit": b.get("cargo_exit"),
        "units": len(b.get("metadata_units") or []),
        "target_emptied_bytes": r.get("target_emptied_bytes"),
        "log": (r.get("build") or {}).get("log"),
        "arm_sites_distinct": meas(arms.get("distinct"), None,
                                   "distinct (file, line) `kind: \"arm\"` "
                                   "manifest rows of this build", []),
        "arm_sites_raw": arms.get("raw"),
        "arm_sites_by_how": arms.get("by_how"),
        "dropped": r.get("dropped"),
    }


def assemble_e6ppp(raw: dict) -> dict:
    """Raw E6‴ facts -> the acceptance document's `results.json`."""
    pins = raw.get("pins") or {}
    cl = raw.get("cleanup") or raw.get("cleanup_after_failure") or {}
    prep = raw.get("raw_prep") or {}
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
            "target_warm_at_start": pins.get("target_warm_at_start"),
            "target_emptied_by_prep_bytes": prep.get("target_emptied_bytes"),
            "corpus_target": pins.get("corpus_target"),
            "corpus_target_bytes_before":
                pins.get("corpus_target_bytes_before"),
            "probe_target": pins.get("probe_target"),
            "sensorium_dir": pins.get("sensorium_dir"),
            "sensorium_dir_per_arm": {
                "E6‴-A": (raw.get("raw_e6ppp_a") or {}).get("sensorium_dir"),
                "E6‴-W": (raw.get("raw_e6ppp_w") or {}).get("sensorium_dir"),
            },
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
                "dropped": [
                    "not recorded: this run's driver was built by the "
                    "operator before launch and evidenced by its sha256 and "
                    "mtime (§2, §5.8). `built_from` is recorded by the runner "
                    "itself from this commit onward"]},
            "logs_dir": raw.get("logs"),
            "prep_build_log": ((raw.get("raw_prep") or {}).get("build")
                               or {}).get("log"),
            "load_1min_at_start": pins.get("load_1min_at_start"),
            "load_at_each_arm": raw.get("arm_loads"),
            "target_disk_free_gb": pins.get("target_disk_free_gb"),
            "target_disk_free_gb_after": cl.get("target_disk_free_gb_after"),
            "repo_disk_free_gb": pins.get("repo_disk_free_gb"),
            "frozen_census": (raw.get("config") or {}).get("frozen_census"),
        },
        "endpoints": {
            "E6pppA": _arm(raw, "raw_e6ppp_a", "-p bloomery-daemon"),
            "E6pppW": _arm(raw, "raw_e6ppp_w", "--workspace"),
            "E6again": _e6(raw),
            "E7ppp": _e7pp(raw),
        },
        "reported": {
            "dispositions": _dispositions(raw),
            "blast_radius": _blast(raw),
            "prep_build": _prep(raw),
        },
        "cleanup": raw.get("cleanup") or raw.get("cleanup_after_failure"),
        "steps": raw.get("steps"),
        "refused": raw.get("refused"), "error": raw.get("error"),
        "started": raw.get("started"), "finished": raw.get("finished"),
    }
