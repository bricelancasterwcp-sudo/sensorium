#!/usr/bin/env python3
"""The E6‴ runner: E6‴-A, E6‴-W, E6-again and E7‴, in the order
`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` §1
pre-registered.

A SIBLING of `acceptance_rung3.py`, not a fork of it. Everything §1 calls
"verbatim" is the committed rung-3 function, CALLED: `acceptance_phases_rung3.
phase_e6prime` is both E6‴ arms (the A arm is `-p bloomery-daemon --lib`, the
W arm is the same function with `--workspace` in the package selector, which
is the only difference §1 states between them), `phase_e6` is E6-again and
`phase_e7pp` is E7‴. `acceptance_rung3`'s byte-lock, preflight and cleanup are
imported and re-used with this document's own lock. A second copy of a
protocol is a second protocol, so nothing here re-implements one.

What is NEW, and reported WITHOUT a gate:

* **the per-arm log and trace directories** -- each arm records into its own
  `SENSORIUM_DIR` subdirectory and writes its own logs, so the two arms'
  evidence cannot overwrite each other;
* **the sweep**: `phase_e6prime` runs `exceptions` on the process with the
  most events, which is THE process for `-p bloomery-daemon --lib` and one of
  several for `--workspace --lib`. Every OTHER recorded process of an arm is
  swept with the same command afterwards and its SWALLOWED lines carried
  beside the primary's. The gate is adjudicated over the UNION -- strictly
  more lines than §1's `exceptions <run>` asks for, which can only make a
  "0 false accusations" endpoint harder to pass, never easier;
* **the blast radius's identity**: the census binary prints no arm columns, so
  the arm sites come from the from-scratch build's own manifests (`kind:
  "arm"` rows, with the `how` each writes) intersected with the Task-8
  reviewer's static list, and the EXECUTED half comes from the arms' traces
  (a HANDLED event whose payload `how` starts `arm_`). An arm the run never
  reaches is not evidence either way, and the record says which number is
  which.

The from-scratch `--workspace --no-run` build that opens the run is PREP, not
an endpoint: it empties the target so that every unit is compiled by THIS
driver (a fingerprint-fresh unit is never handed to the wrapper, so a warm
target could otherwise run test binaries an older transformer emitted) and so
that the manifest set is complete. It leaves the target warm for both measured
arms, which is the lens §1 states.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_e6ppp.py \
        > <ledger>/acceptance-e6ppp/logs/e6ppp.log 2>&1 &

The last act is `<ledger>/acceptance-e6ppp/e6ppp.DONE` (or `.FAILED`) carrying
`exit=<n>`, so silence is distinguishable from success.
"""

from __future__ import annotations

import contextlib
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-04-sensorium-rung3-err-flow"
LEDGER = PLAN
BASE = PLAN / "acceptance-e6ppp"
LOGS = BASE / "logs"

# The rung-2, E5' and rung-3 ledgers are evidence and are not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_phases as ph                                     # noqa: E402
import acceptance_phases_rung3 as r3                               # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_lib import (Refused, driver_cmd, free_gb,          # noqa: E402
                            loadavg, manifests_dir, rmtree,
                            sensorium_cli, step)

ph.LOGS = LOGS

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-05-sensorium-rung3-e6ppp.md")

#: The commit §1 is byte-locked against NOW: the amendment that recorded the
#: census after the literal scan, committed alone and before any E6‴ number
#: was read.
BYTE_LOCK = "254765b"
#: The ORIGINAL lock, committed alone by Task 10 with the transformer change
#: already in but no measurement taken. Both shas are recorded, so the
#: amendment is a visible fact of the record rather than a claim in prose.
ORIGINAL_LOCK = "33396b0"

#: §1's frozen census, in the words it froze it: the numbers Task 10 measured
#: on the clone across the repair, repeated here as the pins the record cites
#: rather than re-derives. Nothing gates on them.
FROZEN_CENSUS = {"arms_escaped_before": 90, "arms_escaped_after": 121,
                 "arms_handled_before": 96, "arms_handled_after": 65,
                 "arms_moved": 31, "arm_sites": 225, "source": "§1"}

#: The Task-8 reviewer's STATIC blast-radius list, as t10-context.md writes
#: it: a file SUFFIX and a line. Written as the reviewer wrote it, not
#: pre-resolved to a path -- the list is the input to this check and resolving
#: it by hand first would hide a resolution that went wrong.
STATIC_BLAST: list[tuple[str, int]] = [
    ("drift.rs", 300), ("drift.rs", 458), ("drift.rs", 700),
    ("drift.rs", 714), ("drift.rs", 869),
    ("swap.rs", 194),
    ("exec.rs", 181), ("exec.rs", 191), ("exec.rs", 365), ("exec.rs", 387),
    ("exec.rs", 402), ("exec.rs", 548), ("exec.rs", 560),
    ("exec_run.rs", 241),
    ("swap/job.rs", 189), ("swap/job.rs", 250), ("swap/job.rs", 266),
    ("swap/job.rs", 282), ("swap/job.rs", 386),
    ("registry.rs", 293), ("registry.rs", 615), ("registry.rs", 643),
    ("registry.rs", 773),
    ("drift/watch.rs", 210), ("drift/watch.rs", 381), ("drift/watch.rs", 441),
    ("flywheel_tool.rs", 383),
    ("llama.rs", 406),
    ("memory.rs", 131),
]
#: The two entries of the same list that carry NO line: "two `codec_fixtures_*`
#: tests". They cannot be intersected with a (file, line) key, and are counted
#: as UNLOCATED rather than quietly dropped or quietly matched.
STATIC_BLAST_UNLOCATED = ["codec_fixtures_* (two arms, no line given)"] * 2

#: The `how` an arm writes once the R2 amendment routes it out of `arm_handled`.
ESCAPED_ARM_HOW = "arm_ambiguous"

#: The 1-minute load at each arm's start, which §1's lens names. The rung-3
#: runner reads it off `git checkout`; this run checks nothing out, so each
#: phase records its own.
LOADS: list = []


def mark_load(label: str) -> None:
    LOADS.append({"arm": label, "load_1min": loadavg(),
                  "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})


@contextlib.contextmanager
def logs_at(path: Path):
    """Point every shared runner at `path` for the duration.

    `acceptance_lib.run` resolves `LOGS` in its own module namespace at call
    time, so re-binding it here moves every log a phase writes -- which is how
    two runs of ONE protocol keep two sets of evidence instead of one
    overwriting the other."""
    old_lib, old_ph = lib.LOGS, ph.LOGS
    path.mkdir(parents=True, exist_ok=True)
    lib.LOGS = ph.LOGS = path
    try:
        yield path
    finally:
        lib.LOGS, ph.LOGS = old_lib, old_ph


def arm_paths(paths: dict, label: str) -> dict:
    """`paths` with `SENSORIUM_DIR` moved to this arm's own subdirectory."""
    p = dict(paths)
    p["sensorium_dir"] = paths["sensorium_dir"] / label
    p["sensorium_dir"].mkdir(parents=True, exist_ok=True)
    return p


def e6ppp_config(paths) -> dict:
    cfg = dict(rung3.rung3_config(paths))
    cfg.update({
        "e6_workdir": LOGS / "e6-cases",
        "arm_a": {"label": "a", "selector": cfg["pkg"]},
        "arm_w": {"label": "w", "selector": ["--workspace"]},
        "frozen_census": FROZEN_CENSUS,
    })
    return cfg


# ------------------------------------------------------- prep: the manifests


def phase_prep_build(paths, cfg) -> dict:
    """The from-scratch `--workspace --no-run` build. PREP, never an endpoint.

    Two jobs, both stated in §2 of the document: it guarantees every unit the
    measured arms then run was compiled by THIS driver, and it leaves a
    COMPLETE manifest set -- cargo does not invoke the wrapper for a
    fingerprint-fresh unit, so only a build that compiles every unit writes
    one manifest per unit."""
    mark_load("prep (--workspace --no-run, from scratch)")
    target = paths["sensorium_acceptance_target"]
    removed = sum(rmtree(child) for child in sorted(target.iterdir()))
    step(f"prep: emptied the target ({removed} bytes)")
    res, b = ph._build(paths, cfg, [*cfg["workspace_sel"], "--no-run"],
                       "prep-workspace.log", True,
                       timeout=cfg.get("e2pp_timeout", 14400))
    out = {"build": b, "target_emptied_bytes": removed,
           "emptied_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "target_free_gb_after": round(free_gb(target), 2)}
    if res["rc"] != 0:
        out["dropped"] = f"the from-scratch workspace build exited {res['rc']}"
        step(f"prep: DROPPED -- build exited {res['rc']}")
        return out
    out["arms"] = arm_rows(paths, b["metadata_units"])
    step(f"prep: {out['arms']['distinct']} distinct arm site(s) over "
         f"{len(b['metadata_units'])} unit(s); how "
         f"{out['arms']['by_how']}")
    return out


def arm_rows(paths, scope: list[str] | None) -> dict:
    """Every `kind: "arm"` manifest row of ONE build, with the `how` it writes.

    `acceptance_phases_rung3.read_manifests_rung3` keeps only
    `(file, qualname, line, kind)` and drops `how`, which is the field this
    check is about; and `_try_rows` counts kinds without keeping identities.
    So this is a third reader over the same files, and it keeps what those two
    discard rather than changing either."""
    d = manifests_dir(paths)
    rows: dict[tuple[str, int], dict] = {}
    raw, units = 0, 0
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        if scope is not None and p.stem not in scope:
            continue
        m = json.loads(p.read_text())
        units += 1
        if m["fell_back"]:
            continue
        for rel, entries in m["files"].items():
            for e in entries:
                if e.get("kind") != "arm":
                    continue
                raw += 1
                line = e.get("line", e.get("firstlineno"))
                key = (rel, line)
                row = rows.setdefault(key, {"file": rel, "line": line,
                                            "qualname": e.get("qualname"),
                                            "hows": [], "units": 0})
                row["units"] += 1
                if e.get("how") not in row["hows"]:
                    row["hows"].append(e.get("how"))
    by_how: dict = {}
    for r in rows.values():
        for h in r["hows"]:
            by_how[h] = by_how.get(h, 0) + 1
    return {"distinct": len(rows), "raw": raw, "units_in_scope": units,
            "by_how": by_how,
            "rows": [rows[k] for k in sorted(rows, key=lambda k: (k[0], k[1]))]}


def resolve_static(arms: dict, static=STATIC_BLAST) -> dict:
    """The reviewer's `(file suffix, line)` list, resolved against the arm
    rows the build actually declared.

    A suffix that matches more than one manifest file carrying an arm at that
    line is reported AMBIGUOUS, never silently resolved: `drift.rs`,
    `swap.rs` and `memory.rs` each name two files in this workspace."""
    rows = arms.get("rows") or []
    resolved, unmatched, ambiguous = [], [], []
    for suffix, line in static:
        hits = [r for r in rows
                if (r["file"] == suffix or r["file"].endswith("/" + suffix))
                and r["line"] == line]
        if not hits:
            unmatched.append({"suffix": suffix, "line": line})
            continue
        if len(hits) > 1:
            ambiguous.append({"suffix": suffix, "line": line,
                              "files": [h["file"] for h in hits]})
        resolved.append({"suffix": suffix, "line": line,
                         "file": hits[0]["file"], "hows": hits[0]["hows"],
                         "qualname": hits[0]["qualname"],
                         "ambiguous": len(hits) > 1})
    escaped = [r for r in resolved if ESCAPED_ARM_HOW in r["hows"]]
    return {
        "static_entries_located": len(static),
        "static_entries_unlocated": len(STATIC_BLAST_UNLOCATED),
        "static_entries_total": len(static) + len(STATIC_BLAST_UNLOCATED),
        "unlocated": list(STATIC_BLAST_UNLOCATED),
        "resolved": resolved, "resolved_count": len(resolved),
        "unmatched": unmatched, "ambiguous": ambiguous,
        "in_blast_radius_now": [
            {"file": r["file"], "line": r["line"], "qualname": r["qualname"]}
            for r in escaped],
        "in_blast_radius_now_count": len(escaped),
    }


# ------------------------------------------------------- executed arm sites


def executed_arms(paths, run_ids: list[str]) -> dict:
    """Every arm site that FIRED in one arm's traces.

    An arm probe writes a HANDLED event only when its arm is taken, so an
    event at an arm site is the run's own evidence that the arm executed.
    Read from the trace's `events` -> `code_objects` join, read-only, with the
    `how` taken from the event's own payload."""
    seen: dict[tuple[str, int], dict] = {}
    per_run, missing = {}, []
    for run_id in run_ids:
        db = paths["sensorium_dir"] / "traces" / f"{run_id}.db"
        if not db.is_file():
            missing.append(run_id)
            continue
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute(
                "select e.line, c.file, c.qualname, e.payload from events e "
                "left join code_objects c on c.id = e.code_id "
                "where e.kind = 'HANDLED'").fetchall()
        finally:
            con.close()
        n = 0
        for line, file, qualname, payload in rows:
            try:
                how = (json.loads(payload) or {}).get("how")
            except (TypeError, ValueError):
                how = None
            if not (how or "").startswith("arm_"):
                continue
            n += 1
            key = (file or "?", line)
            row = seen.setdefault(key, {"file": file, "line": line,
                                        "qualname": qualname, "hows": [],
                                        "events": 0, "runs": []})
            row["events"] += 1
            if how not in row["hows"]:
                row["hows"].append(how)
            if run_id not in row["runs"]:
                row["runs"].append(run_id)
        per_run[run_id] = n
    return {"runs": run_ids, "arm_events_per_run": per_run,
            "traces_missing": missing,
            "distinct_sites": len(seen),
            "sites": [seen[k] for k in sorted(seen, key=lambda k: (k[0] or "",
                                                                  k[1] or 0))]}


def executed_vs_static(resolved: dict, executed: dict, clone_root: str) -> dict:
    """The number §1 asks for: of the located static blast-radius arms, how
    many this arm EXECUTED, against how many exist statically.

    Trace files are absolute; manifest files are workspace-relative. The join
    is on the workspace-relative path, with the clone's root stripped from the
    trace side and the stripping REPORTED, so a path shape that stopped
    matching shows up as a zero with an explanation rather than as a finding."""
    root = clone_root.rstrip("/") + "/"
    ex: dict[tuple[str, int], dict] = {}
    unstripped = 0
    for s in executed.get("sites") or []:
        f = s["file"] or ""
        if f.startswith(root):
            f = f[len(root):]
        else:
            unstripped += 1
        ex[(f, s["line"])] = s
    hits, misses = [], []
    for r in resolved.get("resolved") or []:
        key = (r["file"], r["line"])
        (hits if key in ex else misses).append(
            {**r, "executed_hows": (ex.get(key) or {}).get("hows"),
             "events": (ex.get(key) or {}).get("events")})
    return {
        "executed": len(hits), "static": resolved.get("resolved_count"),
        "static_total_including_unlocated":
            resolved.get("static_entries_total"),
        "executed_rows": hits, "not_executed_rows": misses,
        "executed_arm_sites_all": executed.get("distinct_sites"),
        "trace_paths_not_under_the_clone_root": unstripped,
        "clone_root": clone_root,
    }


# ----------------------------------------------------------------- the arms


def sweep_other_runs(paths, cfg, primary: str | None, per_process: list,
                     label: str) -> dict:
    """`exceptions` on every process of this arm that is NOT the primary.

    Reported beside the primary, never instead of it: §1's protocol names one
    `<run>` and `phase_e6prime` picks it (the process with the most events),
    which for `-p bloomery-daemon --lib` is the only process there is. A
    `--workspace --lib` arm records one process per lib test binary, and an
    arm the primary trace never saw is exactly what E6‴-W exists to look at,
    so the union is what §4 adjudicates."""
    others = [r for r in per_process if r["run"] != primary]
    out = {"primary": primary, "swept": [], "swallowed_lines": [],
           "swallowed_parsed": [], "processes_swept": len(others)}
    for r in others:
        cli = sensorium_cli(paths,
                            ["exceptions", r["run"], "--limit", "100000"],
                            f"{label}-sweep-{r['run']}",
                            timeout=cfg.get("cli_timeout", 3600))
        printed = [ln.strip() for ln in cli["out"].splitlines()
                   if r3.SWALLOWED in ln]
        tallies = [ln for ln in cli["out"].splitlines()
                   if ln.startswith(r3.TALLY)]
        parsed = []
        for ln in printed:
            m = r3.SWALLOW_LINE.search(ln)
            parsed.append({"run": r["run"], "line": ln,
                           "how": m.group("how") if m else None,
                           "event": int(m.group("event")) if m else None,
                           "qualname": m.group("qualname") if m else None,
                           "site_line": int(m.group("line")) if m else None,
                           "frame": m.group("frame") if m else None,
                           "unparsed": m is None})
        sinks = r3._sink_files(paths, r["run"],
                               [p["event"] for p in parsed
                                if p["event"] is not None])
        for p in parsed:
            p["sink"] = sinks.get(p["event"])
        out["swept"].append({"run": r["run"], "events": r["events"],
                             "rc": cli["rc"], "log": cli["log"],
                             "swallowed_count": len(printed),
                             "tally_line": tallies[0] if tallies else None,
                             "stdout_bytes": len(cli["out"])})
        out["swallowed_lines"] += printed
        out["swallowed_parsed"] += parsed
    out["swallowed_count"] = len(out["swallowed_lines"])
    step(f"{label}: swept {len(others)} other process(es); "
         f"{out['swallowed_count']} further SWALLOWED line(s)")
    return out


def phase_arm(paths, cfg, spec: dict) -> dict:
    """One E6‴ arm: §1's protocol (the committed `phase_e6prime`), then the
    sweep, then the arm's executed arm sites."""
    label = spec["label"]
    mark_load(f"E6‴-{label.upper()}")
    ap = arm_paths(paths, label)
    acfg = dict(cfg) | {"pkg": list(spec["selector"])}
    step(f"E6‴-{label.upper()}: "
         f"{' '.join(str(c) for c in driver_cmd(ap, *acfg['pkg'], '--lib'))}")
    with logs_at(LOGS / f"arm-{label}"):
        out = r3.phase_e6prime(ap, acfg)
        out["selector"] = list(spec["selector"])
        out["sensorium_dir"] = str(ap["sensorium_dir"])
        if out.get("dropped"):
            return out
        out["sweep"] = sweep_other_runs(
            ap, acfg, out.get("run"), out.get("per_process") or [], label)
    runs = [r["run"] for r in (out.get("per_process") or [])]
    out["executed_arms"] = executed_arms(ap, runs)
    out["union_swallowed_count"] = (out["swallowed_count"]
                                    + out["sweep"]["swallowed_count"])
    step(f"E6‴-{label.upper()}: primary {out['swallowed_count']} + sweep "
         f"{out['sweep']['swallowed_count']} = {out['union_swallowed_count']} "
         f"SWALLOWED line(s) over {out['processes']} process(es)")
    return out


# -------------------------------------------------------------------- main


def main(argv) -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("e6ppp.DONE", "e6ppp.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": "rust/tests/acceptance_e6ppp.py",
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)
        paths = lib.env_paths(False)
        cfg = e6ppp_config(paths)
        res["config"] = {k: str(v) if isinstance(v, Path) else v
                         for k, v in cfg.items()}
        pins = rung3.preflight(paths, cfg)
        res["pins"] = pins

        step("prep: from-scratch --workspace --no-run (empties the target)")
        res["raw_prep"] = phase_prep_build(paths, cfg)
        res["raw_blast_static"] = resolve_static(
            (res["raw_prep"] or {}).get("arms") or {})
        step(f"blast radius: {res['raw_blast_static']['resolved_count']} of "
             f"{res['raw_blast_static']['static_entries_total']} static "
             f"entries resolved; "
             f"{res['raw_blast_static']['in_blast_radius_now_count']} read "
             f"{ESCAPED_ARM_HOW} now")

        step("E6‴-A: the clone's -p bloomery-daemon --lib suite")
        res["raw_e6ppp_a"] = phase_arm(paths, cfg, cfg["arm_a"])

        step("E6‴-W: the clone's --workspace --lib suite")
        res["raw_e6ppp_w"] = phase_arm(paths, cfg, cfg["arm_w"])

        clone = str(paths["sensorium_bloomery_clone"])
        res["raw_executed_vs_static"] = {
            arm: executed_vs_static(
                res["raw_blast_static"],
                (res.get(f"raw_e6ppp_{arm}") or {}).get("executed_arms") or {},
                clone)
            for arm in ("a", "w")}
        step("executed-vs-static: A "
             f"{res['raw_executed_vs_static']['a']['executed']}/"
             f"{res['raw_executed_vs_static']['a']['static']}, W "
             f"{res['raw_executed_vs_static']['w']['executed']}/"
             f"{res['raw_executed_vs_static']['w']['static']}")

        with logs_at(LOGS / "e6-again"):
            mark_load("E6-again")
            step("E6-again: the Rust corpus cases with an `exceptions` question")
            res["raw_e6"] = r3.phase_e6(paths, cfg)

        with logs_at(LOGS / "e7ppp"):
            mark_load("E7‴")
            step("E7‴: mechanics.sh, lines and columns")
            res["raw_e7pp"] = r3.phase_e7pp(paths, cfg)

        res["arm_loads"] = list(LOADS)
        res["cleanup"] = rung3.cleanup(paths, cfg, pins)
    except Refused as e:
        step(f"REFUSED: {e}")
        res["refused"] = str(e)
        rc = 3
    except Exception:                                          # noqa: BLE001
        import traceback
        step("ERROR: " + traceback.format_exc().strip().splitlines()[-1])
        res["error"] = traceback.format_exc()
        rc = 4
    if paths and cfg and res.get("cleanup") is None and pins is not None:
        try:
            res["cleanup_after_failure"] = rung3.cleanup(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-e6ppp-raw.json").write_text(
        json.dumps(res, indent=2, default=str))
    try:
        assemble_only(res)
    except Exception:                                          # noqa: BLE001
        import traceback
        (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
        step("assemble FAILED (logs/assemble-error.txt); the raw record is intact")
        rc = rc or 5
    (BASE / ("e6ppp.DONE" if rc == 0 else "e6ppp.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw E6‴ facts at "
         f"{LEDGER / 'results-e6ppp-raw.json'}")
    return rc


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no arm and reads
    no new number."""
    from acceptance_schema_e6ppp import assemble_e6ppp               # noqa: PLC0415
    if raw is None:
        raw = json.loads((LEDGER / "results-e6ppp-raw.json").read_text())
    doc = assemble_e6ppp(raw)
    doc["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": "results-e6ppp-raw.json",
        "by": "rust/tests/acceptance_e6ppp.py --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no arm was re-run and no value "
                 "re-measured"),
    }
    dest = (REPO / "docs" / "superpowers" / "acceptance"
            / "2026-09-05-sensorium-rung3-e6ppp.results.json")
    dest.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    print(f"assembled {dest} from results-e6ppp-raw.json")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only())
    raise SystemExit(main(sys.argv[1:]))
