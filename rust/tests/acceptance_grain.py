#!/usr/bin/env python3
"""The rung-4 entry-slice runner: H1-H6, in the order
`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md` §1
pre-registers them.

WHAT MAKES THIS RUNNER DIFFERENT FROM ITS SIBLINGS
--------------------------------------------------
It measures no program. Every number it needs about the workspace under
measurement was already measured on 2026-09-05 and PUBLISHED: this slice
changes what `exceptions` PRINTS, so its question is whether the new grain
reproduces the record's answers -- and the record is the oracle, read from
the committed `2026-09-05-sensorium-rung3-e6q.results.json` and never
re-measured. What is re-run is the READER, over the trace stores that record
cites, which are kept on disk and are INPUTS here.

Two consequences run through the whole file:

* **the stores are read-only.** No arm is recorded, no cargo command is run
  against the clone, no target is emptied. The preflight counts the traces in
  each store and the cleanup counts them again; the trace `.db` files' total
  bytes are recorded on both sides. The one write this run does cause is the
  CLI's own audit line: every `sensorium` call appends a row to the store's
  `invocations.jsonl` (a SIBLING of `traces/`, invisible to `runs` and
  `find_trace`). That is unavoidable short of `SENSORIUM_NO_INVOCATION_LOG=1`,
  which the record's own protocol did not set either, so the line count is
  recorded before and after and the lens says so rather than claiming a
  purity the run does not have.
* **nothing computed from the oracle stands where a measurement belongs.**
  The oracle is published under its own name in the record; a headline whose
  phase did not run is `null` with a reason. The schema is tested for exactly
  that (`tests/test_acceptance_grain.py`).

THE PREFLIGHT IS THIS SLICE'S, NOT RUNG 3'S
--------------------------------------------
`acceptance_rung3.preflight` asserts a clone at a pinned commit, a census
driver, three E5 arm tips and a read-only source tree, and `acceptance_rung3.
cleanup` checks the clone back out. This slice touches none of them: it runs
no cargo against the clone at all. Re-using that preflight would mean either
refusing on a location this run never opens, or asserting the clone is clean
about a run that could not have dirtied it -- a vacuous assertion, which
rigorous-experiments §1 rates worse than none. So `preflight_grain` below
checks exactly what this run touches, and every other pin rung 3 recorded is
absent from this record rather than copied into it. What IS re-used is the
byte-lock (`acceptance_rung3.byte_lock_check`), the corpus collector
(`acceptance_phases_rung3.phase_e6`, H1) and the sqlite join those phases
read a sink's file with -- all called, never re-implemented.

Every location is an environment variable; no box path appears in this file.
The five are refused TOGETHER when missing, as `acceptance_lib.env_paths`
refuses its own.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_grain.py \
        > <ledger>/acceptance-grain/logs/grain.log 2>&1 &

The last act is `<ledger>/acceptance-grain/grain.DONE` (or `.FAILED`)
carrying `exit=<n>`, so silence is distinguishable from success.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-05-sensorium-rung4-entry-grain"
LEDGER = PLAN
BASE = PLAN / "acceptance-grain"
LOGS = BASE / "logs"

# Every earlier ledger is evidence and is not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_e6ppp import LOADS                                # noqa: E402
# Re-exported so `acceptance_grain.<name>` keeps resolving for every caller
# and every test: this module is the instrument's front door, and the two
# siblings below are where its halves live (the parsers and the record in
# `_read`, the five protocols in `_phases`).
from acceptance_grain_phases import (phase_h1, phase_h2, phase_h3,  # noqa: E402,F401
                                     phase_h4, phase_h6, _ask)
from acceptance_grain_read import (ARMS, BUSIEST_WS_RUN,          # noqa: E402,F401
                                   MULTI, compare_sites, measure_sites,
                                   oracle, oracle_json, parse_header,
                                   parse_shapes, parse_tally, reported,
                                   site_of_event, site_table, sites_of_events,
                                   store_paths, swallowed_shapes, tally_counts,
                                   trace_db, vary_counts)
from acceptance_lib import (LOAD_CEILING, REPO_DISK_FLOOR_GB,      # noqa: E402
                            Refused, dir_bytes, free_gb, loadavg,
                            plain_env, run, sensorium_cli,
                            sha256_file, step)

# Re-asserted AFTER the imports above, and not only before them: importing
# `acceptance_rung3` points `acceptance_lib.LEDGER`/`LOGS` at the rung-3
# slice's workspace, and `acceptance_e6ppp` at the E6‴ document's. Without
# this second assignment every log written outside a `logs_at` block would
# land beside another record (measured on the 2026-09-05 E6‴ run).
lib.LEDGER = LEDGER
lib.LOGS = LOGS
ph.LOGS = LOGS

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-05-sensorium-rung4-entry-grain.md")

#: The commit that committed §1 ALONE, before any number below was read.
#: `None` until that commit exists, and a `None` lock REFUSES rather than
#: measuring against a pre-registration that can still be edited.
BYTE_LOCK = "05c3124"
#: §1 of this document is committed once and never amended, so there is no
#: second sha to carry.
ORIGINAL_LOCK = None

#: The ORACLE: the published E6⁗ record, committed in this repository. Every
#: number this run is compared against comes from here, and this file is
#: opened read-only and never rewritten.
ORACLE = (REPO / "docs" / "superpowers" / "acceptance"
          / "2026-09-05-sensorium-rung3-e6q.results.json")
#: The commit that last touched it, named in §1's lens.
ORACLE_COMMIT = "605db64"

#: The driver H1 records the corpus cases under. This slice changes no crate,
#: so the driver is the one already built and is NOT rebuilt: its sha256 is
#: recorded before and after instead.
DRIVER_VERSION = "0.3.1"

#: H5's kill. A wall over this is a STOP on H5, recorded as a kill -- never
#: raised as an exception that would take the run down with it.
KILL_S = 60.0

#: The five locations, and the `paths` keys they land under.
GRAIN_ENV = {
    "SENSORIUM_E6Q_STORES": "e6q_stores",
    "SENSORIUM_DRIVER": "sensorium_driver",
    "SENSORIUM_CORPUS_TARGET": "corpus_target_env",
    "SENSORIUM_DIR": "sensorium_dir",
    "SENSORIUM_RUST_TARGET": "rust_target",
}


# ------------------------------------------------------------ lock and paths


def check_byte_lock() -> dict:
    """§1, as committed, versus the working tree -- or a refusal to start."""
    if not BYTE_LOCK:
        raise Refused(
            "§1 of the acceptance document is not locked yet: BYTE_LOCK is "
            "None. Commit §1 ALONE, then set BYTE_LOCK to that commit's sha.")
    return rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)


def env_paths_grain() -> dict:
    """Every location this run touches, from the environment, refused
    together when missing -- one launch reports all of them."""
    missing = [k for k in GRAIN_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(
            "unset environment variable(s): " + ", ".join(missing)
            + " -- this run needs the parent of the three kept E6⁗ trace "
              "stores, the 0.3.1 driver H1 records the corpus under, the "
              "corpus target it records into, a FRESH trace directory, and "
              "the Rust workspace's target for H6's `cargo test`")
    return {name: Path(os.environ[key]) for key, name in GRAIN_ENV.items()}


def grain_config(paths) -> dict:
    """This slice's config. Not `rung3_config`: that one calls
    `acceptance.real_config`, which reads the CLONE's crate manifests, and no
    phase here opens the clone."""
    return {
        "corpus_target": paths["corpus_target_env"],
        "e6_workdir": LOGS / "e6-cases",
        "e6_record_timeout": 3600,
        "cli_timeout": 3600,
        "kill_s": KILL_S,
        "pytest_timeout": 3600,
        "cargo_timeout": 7200,
        "limit": 100000,
        "arms": ARMS,
        "oracle_record": str(ORACLE.relative_to(REPO)),
        "oracle_commit": ORACLE_COMMIT,
        "busiest_ws_run": BUSIEST_WS_RUN,
    }


def out(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------- the preflight


def _store_facts(store: Path) -> dict:
    """One kept store, counted. `invocations.jsonl` is a SIBLING of
    `traces/`, appended to by every CLI call (`sensorium.invocations`) and
    invisible to `runs`/`find_trace`. Counting its lines before and after is
    how this record states the one write it does cause instead of claiming a
    read-only-ness it does not have."""
    traces = sorted((store / "traces").glob("*.db")) if store.is_dir() else []
    log = store / "invocations.jsonl"
    return {"store": str(store), "traces": len(traces),
            "trace_bytes": sum(t.stat().st_size for t in traces),
            "runs": [t.stem for t in traces],
            "invocations_jsonl_lines": (
                len(log.read_text().splitlines()) if log.is_file() else 0)}


def _trace_invocation(paths, label: str) -> str | None:
    """The invocation id one store's traces carry, read from a member's own
    `meta` -- the same place `runs` reads it."""
    sp = store_paths(paths, label)
    dbs = sorted((sp["sensorium_dir"] / "traces").glob("*.db"))
    if not dbs:
        return None
    return lib.trace_meta(sp, dbs[0].stem).get("invocation")


def preflight_grain(paths, cfg) -> dict:
    """What THIS run touches, and nothing else (see the module docstring).

    Refuses on: a missing or non-0.3.1 driver; a store whose trace count is
    not the one §1 names; a store whose invocation id is not the one §1
    names; a `SENSORIUM_DIR` that is not fresh; a corpus target that is not
    fresh; the machine's load and the repo disk floor.
    """
    step("rung-4 entry preflight")
    load = loadavg()
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    repo_free = free_gb(REPO)
    if repo_free < REPO_DISK_FLOOR_GB:
        raise Refused(f"{REPO}: {repo_free:.1f} GB free < "
                      f"{REPO_DISK_FLOOR_GB} GB floor")

    driver = Path(paths["sensorium_driver"])
    if not driver.is_file():
        raise Refused(f"no driver at {driver}")
    if not ORACLE.is_file():
        raise Refused(f"the oracle record is missing at {ORACLE}")

    stores, invocations = {}, {}
    for label, spec in ARMS.items():
        facts = _store_facts(paths["e6q_stores"] / label)
        if facts["traces"] != spec["traces"]:
            raise Refused(
                f"kept store {label}: {facts['traces']} trace(s), §1 names "
                f"{spec['traces']} -- this is not the store the record cites")
        if spec["run"] not in facts["runs"]:
            raise Refused(f"kept store {label}: the record's primary process "
                          f"{spec['run']} is not in it")
        stores[label] = facts
        if spec["invocation"]:
            got = _trace_invocation(paths, label)
            if got != spec["invocation"]:
                raise Refused(
                    f"kept store {label}: its traces carry invocation "
                    f"{got!r}, §1 names {spec['invocation']!r}")
            invocations[label] = got

    sdir = paths["sensorium_dir"]
    if sdir.exists() and any(sdir.iterdir()):
        raise Refused(f"SENSORIUM_DIR {sdir} is not empty; H1 needs a NEW "
                      "trace directory, and a stale one could answer a "
                      "question this run asked of another")
    sdir.mkdir(parents=True, exist_ok=True)
    corpus_target = cfg["corpus_target"]
    if corpus_target.exists() and any(corpus_target.iterdir()):
        raise Refused(f"corpus target {corpus_target} is not empty; §1 says "
                      "FRESH, and a warm target would record H1 against "
                      "another slice's artifacts")
    corpus_target.mkdir(parents=True, exist_ok=True)

    pins = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse",
                           "--abbrev-ref", "HEAD"),
        "repo_porcelain": out("git", "-C", str(REPO), "status", "--porcelain"),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "driver_version": DRIVER_VERSION,
        "driver_rebuilt_by_this_run": False,
        "driver_mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                      time.localtime(driver.stat().st_mtime)),
        "oracle_record": cfg["oracle_record"],
        "oracle_commit": cfg["oracle_commit"],
        "oracle_sha256": sha256_file(ORACLE),
        "rustc": out("rustc", "-V"), "cargo": out("cargo", "-V"),
        "python": out(str(REPO / ".venv" / "bin" / "python"), "-V"),
        "sensorium_version": out(
            str(REPO / ".venv" / "bin" / "python"), "-c",
            "import importlib.metadata as m; print(m.version('sensorium'))"),
        "nproc": os.cpu_count(),
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/"
                         "scaling_governor").read_text().strip(),
        "load_1min_at_start": load,
        "repo_disk_free_gb": round(repo_free, 2),
        "stores_root": str(paths["e6q_stores"]),
        "stores_before": stores,
        "store_invocations": invocations,
        "sensorium_dir": str(sdir),
        "corpus_target": str(corpus_target),
        "rust_target": str(paths["rust_target"]),
        "read_only_reading": (
            "the kept stores' `traces/*.db` are INPUTS and are never written; "
            "every CLI call appends one audit row to the store's "
            "`invocations.jsonl`, a sibling of `traces/` that `runs` and "
            "`find_trace` do not read, and the counts before and after are "
            "both recorded"),
    }
    step(f"preflight ok: load={load} driver={pins['driver_sha256'][:12]} "
         f"stores " + ", ".join(f"{k} {v['traces']}"
                                for k, v in stores.items()))
    return pins


def cleanup_grain(paths, cfg, pins) -> dict:
    """What the run left behind. The stores' trace counts and bytes must be
    what they were; the audit-log growth is stated, not hidden."""
    after = {label: _store_facts(paths["e6q_stores"] / label)
             for label in ARMS}
    before = pins.get("stores_before") or {}
    unchanged = all(
        after[k]["traces"] == (before.get(k) or {}).get("traces")
        and after[k]["trace_bytes"] == (before.get(k) or {}).get("trace_bytes")
        for k in ARMS)
    sdir = paths["sensorium_dir"]
    c = {
        "stores_after": after,
        "kept_traces_unchanged": unchanged,
        "invocations_jsonl_lines_added": {
            k: after[k]["invocations_jsonl_lines"]
               - (before.get(k) or {}).get("invocations_jsonl_lines", 0)
            for k in ARMS},
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
        "driver_unchanged": (sha256_file(paths["sensorium_driver"])
                             == pins.get("driver_sha256")),
        "fresh_sensorium_dir_traces": len(
            list((sdir / "traces").glob("*.db"))) if sdir.is_dir() else 0,
        "corpus_target_bytes_after": dir_bytes(cfg["corpus_target"])
        if cfg["corpus_target"].is_dir() else 0,
        "repo_porcelain_after": out("git", "-C", str(REPO), "status",
                                    "--porcelain"),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"cleanup: kept traces unchanged={unchanged}; audit rows added "
         f"{c['invocations_jsonl_lines_added']}; driver unchanged="
         f"{c['driver_unchanged']}")
    return c


# -------------------------------------------------------------------- main


def _partial_json(res: dict) -> str:
    """Whatever of the record CAN be serialised, key by key, with the keys
    that could not NAMED. A run that measured for an hour must lose one value
    to a serialisation defect, not all of them -- and a reader must be able
    to see which one went."""
    kept, lost = {}, []
    for k, v in res.items():
        try:
            json.dumps({k: v}, default=str)
        except (TypeError, ValueError):
            lost.append(k)
        else:
            kept[k] = v
    kept["keys_that_could_not_be_serialised"] = lost
    return json.dumps(kept, indent=2, default=str)


def main(argv) -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("grain.DONE", "grain.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": "rust/tests/acceptance_grain.py",
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = check_byte_lock()
        paths = env_paths_grain()
        cfg = grain_config(paths)
        res["config"] = {k: str(v) if isinstance(v, Path) else v
                         for k, v in cfg.items()}
        orc = oracle(ORACLE)
        # The JSON-SAFE projection: `orc`'s per-arm tables are keyed by
        # (file, line) TUPLES, which `json.dumps` cannot write at all. The
        # tuple-keyed `orc` stays local, where the comparisons need it.
        res["oracle"] = oracle_json(orc)
        step(f"oracle: {cfg['oracle_record']} at {ORACLE_COMMIT} -- sites "
             f"{orc['sites']}, lines {orc['lines']}, tally lines "
             f"{orc['tally_lines']}")
        pins = preflight_grain(paths, cfg)
        res["pins"] = pins

        res["raw_h2"] = phase_h2(paths, cfg, orc)
        res["raw_h3"] = phase_h3(paths, cfg, orc)
        res["raw_h4"] = phase_h4(paths, cfg, orc)
        # H1 last of the reader phases and BEFORE H6: it is the only phase
        # that runs the driver, and H6's `cargo test` is the only thing that
        # could relink it.
        res["raw_e6"] = phase_h1(paths, cfg)
        res["raw_h6"] = phase_h6(paths, cfg)
        res["raw_reported"] = reported(cfg, orc, res["raw_h2"],
                                       res["raw_h3"], res["raw_h4"])
        res["cleanup"] = cleanup_grain(paths, cfg, pins)
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
            res["cleanup_after_failure"] = cleanup_grain(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    raw_path = LEDGER / "results-grain-raw.json"
    try:
        raw_path.write_text(json.dumps(res, indent=2, default=str))
    except (TypeError, ValueError):
        # The last act of an hour-long run, and it must not be able to lose
        # the run. `default=` does not apply to dict KEYS, so one
        # unserialisable key would otherwise raise here -- outside every try
        # -- and leave no raw record, no `results.json` and NO MARKER, which
        # is the one state the marker exists to make impossible.
        import traceback
        trace = traceback.format_exc()
        (LOGS / "raw-json-error.txt").write_text(trace)
        res["raw_json_error"] = trace.strip().splitlines()[-1]
        step("writing the raw record FAILED (logs/raw-json-error.txt); "
             "writing what CAN be serialised instead")
        raw_path.write_text(_partial_json(res))
        rc = rc or 6
    try:
        assemble_only(res)
        render_only()
    except Exception:                                          # noqa: BLE001
        import traceback
        (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
        step("assemble/render FAILED (logs/assemble-error.txt); the raw "
             "record is intact")
        rc = rc or 5
    (BASE / ("grain.DONE" if rc == 0 else "grain.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw facts at "
         f"{LEDGER / 'results-grain-raw.json'}")
    return rc


RESULTS = (REPO / "docs" / "superpowers" / "acceptance"
           / "2026-09-05-sensorium-rung4-entry-grain.results.json")


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no phase and
    reads no new number."""
    from acceptance_grain_schema import assemble_grain              # noqa: PLC0415
    if raw is None:
        raw = json.loads((LEDGER / "results-grain-raw.json").read_text())
    doc = assemble_grain(raw)
    doc["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": "results-grain-raw.json",
        "by": "rust/tests/acceptance_grain.py --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no phase was re-run and no value "
                 "re-measured"),
    }
    RESULTS.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    print(f"assembled {RESULTS} from results-grain-raw.json")
    return 0


def render_only() -> int:
    """§2 and §3, rendered from the assembled record into the ledger. The
    document itself is edited by hand at Task 5; this is the text it pastes,
    produced by committed code rather than by a one-off script."""
    import render_grain                                            # noqa: PLC0415
    doc = json.loads(RESULTS.read_text())
    text = "\n".join(render_grain.environment(doc) + [""]
                     + render_grain.results(doc))
    (BASE / "section-2-3.md").write_text(text + "\n")
    print(f"rendered {BASE / 'section-2-3.md'}")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only() or render_only())
    if "--render" in sys.argv[1:]:
        raise SystemExit(render_only())
    raise SystemExit(main(sys.argv[1:]))
