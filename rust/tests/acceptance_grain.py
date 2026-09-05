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
from collections import Counter
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
import acceptance_phases_rung3 as r3                               # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_e6ppp import logs_at, mark_load                    # noqa: E402
from acceptance_grain_read import (ARMS, BUSIEST_WS_RUN,          # noqa: E402,F401
                                   MULTI, compare_sites, measure_sites,
                                   oracle, parse_header, parse_shapes,
                                   parse_tally, reported, site_of_event,
                                   sites_of_events, swallowed_shapes,
                                   tally_counts, trace_db, vary_counts)
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


def store_paths(paths, label: str) -> dict:
    """A `paths` dict pointing at ONE kept store.

    `sensorium_cli` and `acceptance_phases_rung3._sink_files` both resolve a
    store through `paths["sensorium_dir"]`, so this is the whole of what an
    arm needs. It is deliberately NOT `paths["sensorium_dir"]` itself: that
    one is the fresh directory H1's preflight requires to be empty, and an
    arm reading it would find no traces at all."""
    return dict(paths) | {"sensorium_dir": paths["e6q_stores"] / label}


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


# ------------------------------------------------------------- H2, H3, H4


def _ask(paths, label: str, ref: str, cfg, tag: str, kill=None) -> dict:
    """One `exceptions <ref> --limit <big>` against one kept store.

    `kill` arms H5's ceiling. A kill is a fact of the record -- H5's STOP --
    and never an exception that takes the run down with it, so the wall and
    whatever the process had printed are captured and returned.
    """
    sp = store_paths(paths, label)
    args = ["exceptions", ref, "--limit", str(cfg["limit"])]
    timeout = kill if kill else cfg["cli_timeout"]
    t0 = time.monotonic()
    try:
        res = sensorium_cli(sp, args, tag, timeout=timeout)
        res["timed_out"] = False
    except subprocess.TimeoutExpired as e:
        wall = time.monotonic() - t0
        text = e.output if isinstance(e.output, str) else (e.output or b""
                                                           ).decode("replace",
                                                                    )
        res = {"rc": None, "out": text or "", "err": "", "wall": wall,
               "log": None, "timed_out": True}
        step(f"{tag}: KILLED at {timeout} s -- H5 STOP")
    res["command"] = "sensorium " + " ".join(args)
    res["stdout_bytes"] = len(res["out"])
    res["stdout_lines"] = len(res["out"].splitlines())
    return res


def phase_h2(paths, cfg, orc) -> dict:
    """H2: the grouped view of the A run, at the site grain."""
    mark_load("H2")
    spec = ARMS["a"]
    with logs_at(LOGS / "h2"):
        res = _ask(paths, "a", spec["run"], cfg, "h2-a")
        m = measure_sites(store_paths(paths, "a"), res["out"],
                          spec["run"])
    header = parse_header(res["out"])
    cmp_ = compare_sites(m["sites"], orc["a"])
    out_ = {
        "arm": "a", "run": spec["run"], "rc": res["rc"],
        "wall": round(res["wall"], 3), "log": res["log"],
        "command": res["command"], "stdout": res["out"],
        "stdout_bytes": res["stdout_bytes"],
        "stdout_lines": res["stdout_lines"],
        "groups": m["groups"], "chains": m["chains"],
        "measured_sites": {f"{f}:{ln}": n for (f, ln), n in
                           sorted(m["sites"].items(), key=str)},
        "unresolved_sinks": m["unresolved_count"],
        "unresolved": m["unresolved"],
        "compare": {**cmp_,
                    "missing": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                 "expected": d["expected"]}
                                for d in cmp_["missing"]],
                    "extra": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                               "measured": d["measured"]}
                              for d in cmp_["extra"]],
                    "count_diffs": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                     "measured": d["measured"],
                                     "expected": d["expected"]}
                                    for d in cmp_["count_diffs"]]},
        "tally_line": header["tally_line"],
        "oracle_tally_line": (orc["per_process"]["a"] or {}).get(spec["run"]),
        "vary": vary_counts(res["out"]),
        "header": header,
    }
    out_["tally_line_equal"] = (out_["tally_line"]
                                == out_["oracle_tally_line"])
    step(f"H2: {out_['groups']} SWALLOWED group(s), {out_['chains']} chain(s); "
         f"site differences {cmp_['differences']}; tally equal "
         f"{out_['tally_line_equal']}")
    return out_


def phase_h3(paths, cfg, orc) -> dict:
    """H3: every process of `ws` and `ws0`, one `exceptions <run>` each.

    Compared per process against the record's own tally line and swallow
    count. A process whose record tally line is `None` printed `no exceptions
    recorded`, and the check is for THAT SHAPE, not for a zero.
    """
    mark_load("H3")
    arms: dict = {}
    for label in MULTI:
        sp = store_paths(paths, label)
        runs = sorted(p.stem for p in
                      (sp["sensorium_dir"] / "traces").glob("*.db"))
        expect = orc["per_process"][label]
        counts = orc["swallowed_count"][label]
        rows, bad_tally, bad_count = [], [], []
        with logs_at(LOGS / f"h3-{label}"):
            for run_id in runs:
                res = _ask(paths, label, run_id, cfg, f"h3-{label}-{run_id}")
                shapes = swallowed_shapes(res["out"])
                chains = sum(s["n"] for s in shapes)
                tally_line = parse_tally(res["out"])
                want = expect.get(run_id)
                if want is None:
                    ok_tally = (tally_line is None
                                and "no exceptions recorded" in res["out"])
                else:
                    ok_tally = tally_line == want
                ok_count = chains == counts.get(run_id)
                row = {"run": run_id, "rc": res["rc"],
                       "wall": round(res["wall"], 3),
                       "stdout_bytes": res["stdout_bytes"],
                       "stdout_lines": res["stdout_lines"],
                       "groups": len(shapes), "chains": chains,
                       "tally_line": tally_line, "oracle_tally_line": want,
                       "oracle_swallowed_count": counts.get(run_id),
                       "tally_equal": ok_tally, "count_equal": ok_count,
                       "vary": vary_counts(res["out"]),
                       "log": res["log"]}
                if run_id == cfg["busiest_ws_run"]:
                    row["stdout"] = res["out"]
                rows.append(row)
                if not ok_tally:
                    bad_tally.append(run_id)
                if not ok_count:
                    bad_count.append(run_id)
        arms[label] = {
            "processes": len(rows), "rows": rows,
            "runs_only_in_the_store": sorted(set(runs) - set(expect)),
            "runs_only_in_the_record": sorted(set(expect) - set(runs)),
            "unequal_tally_lines": bad_tally,
            "unequal_swallow_counts": bad_count,
            "stdout_bytes_total": sum(r["stdout_bytes"] for r in rows),
            "stdout_lines_total": sum(r["stdout_lines"] for r in rows),
            "groups_total": sum(r["groups"] for r in rows),
            "chains_total": sum(r["chains"] for r in rows),
            "vary": dict(sum((Counter(r["vary"]) for r in rows), Counter())),
        }
        step(f"H3 {label}: {len(rows)} process(es); unequal tally lines "
             f"{len(bad_tally)}; unequal swallow counts {len(bad_count)}")
    total = sum(a["processes"] for a in arms.values())
    return {"arms": arms, "comparisons": total,
            "unequal": sum(len(a["unequal_tally_lines"])
                           + len(a["unequal_swallow_counts"])
                           for a in arms.values())}


def phase_h4(paths, cfg, orc) -> dict:
    """H4 and H5: one invocation question per multi-process arm, wall-timed
    under an armed kill."""
    mark_load("H4")
    arms: dict = {}
    for label in MULTI:
        spec = ARMS[label]
        with logs_at(LOGS / f"h4-{label}"):
            res = _ask(paths, label, spec["invocation"], cfg,
                       f"h4-{label}", kill=cfg["kill_s"])
            m = measure_sites(store_paths(paths, label),
                              res["out"], spec["run"])
        header = parse_header(res["out"])
        cmp_ = compare_sites(m["sites"], orc[label])
        arms[label] = {
            "arm": label, "invocation": spec["invocation"],
            "rc": res["rc"], "wall": round(res["wall"], 3),
            "timed_out": res["timed_out"], "kill_s": cfg["kill_s"],
            "log": res["log"], "command": res["command"],
            "stdout_bytes": res["stdout_bytes"],
            "stdout_lines": res["stdout_lines"],
            "groups": m["groups"], "chains": m["chains"],
            "unresolved_sinks": m["unresolved_count"],
            "unresolved": m["unresolved"],
            "processes_named": len(m["runs_named"]),
            "compare": {"equal": cmp_["equal"],
                        "differences": cmp_["differences"],
                        "measured_sites": cmp_["measured_sites"],
                        "expected_sites": cmp_["expected_sites"],
                        "measured_lines": cmp_["measured_lines"],
                        "expected_lines": cmp_["expected_lines"],
                        "missing": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                     "expected": d["expected"]}
                                    for d in cmp_["missing"]],
                        "extra": [{"site": f"{d['site'][0]}:{d['site'][1]}",
                                   "measured": d["measured"]}
                                  for d in cmp_["extra"]],
                        "count_diffs": [
                            {"site": f"{d['site'][0]}:{d['site'][1]}",
                             "measured": d["measured"],
                             "expected": d["expected"]}
                            for d in cmp_["count_diffs"]]},
            "header": header,
            "oracle_tally": orc["tallies"][label],
            "tally_equal": header["tally"] == orc["tallies"][label],
            "header_counts_equal": (
                header["processes"] == orc["processes"][label]
                and header["with_chains"] == orc["tally_lines"][label]
                and header["without_chains"]
                == orc["without_a_tally_line"][label]),
            "incomplete_members": header["incomplete"],
            "vary": vary_counts(res["out"]),
        }
        step(f"H4 {label}: {m['groups']} group(s) over "
             f"{arms[label]['processes_named']} named process(es) in "
             f"{arms[label]['wall']} s; site differences {cmp_['differences']}; "
             f"tally equal {arms[label]['tally_equal']}; header counts equal "
             f"{arms[label]['header_counts_equal']}")
    return {"arms": arms,
            "walls": {k: v["wall"] for k, v in arms.items()},
            "killed": [k for k, v in arms.items() if v["timed_out"]]}


# ----------------------------------------------------------------- H1 and H6


def phase_h1(paths, cfg) -> dict:
    """H1: the COMMITTED corpus collector (`acceptance_phases_rung3.phase_e6`)
    over every `corpus/rust/*` case with an `exceptions` question.

    `phase_e6` gives each case its OWN `<workdir>/.sensorium`, so the fresh
    `SENSORIUM_DIR` the preflight required stays empty -- which the cleanup
    re-checks, because a corpus recording landing in it would mean a case
    read another case's trace.
    """
    mark_load("H1")
    with logs_at(LOGS / "h1"):
        step("H1: the Rust corpus cases with an `exceptions` question, "
             "against the pins §1 names as updated BY RULE")
        return r3.phase_e6(paths, cfg)


def phase_h6(paths, cfg) -> dict:
    """H6: the whole Python suite, and the Rust workspace tests.

    Both, because §1's H6 names both. The Python suite runs under
    `plain_env()` plus `SENSORIUM_CARGO_SENSORIUM` -- the one variable the
    suite reads to decide whether it can drive a real driver -- so no store
    of this run can answer a test's question, and the module that is skipped
    without it is RUN. `cargo test --workspace` runs in `rust/` against the
    workspace target it was built in; no crate changed in this slice, so it
    compiles nothing, and the driver's sha256 is checked afterwards rather
    than assumed. H6 runs LAST, so even a relink could not reach H1.
    """
    mark_load("H6")
    env = plain_env() | {
        "PYTHONDONTWRITEBYTECODE": "1",
        "SENSORIUM_CARGO_SENSORIUM": str(paths["sensorium_driver"])}
    with logs_at(LOGS / "h6"):
        step("H6(python): the whole suite")
        py = run([str(REPO / ".venv" / "bin" / "python"), "-m", "pytest",
                  "-q"], REPO, "h6-pytest.log", env,
                 timeout=cfg["pytest_timeout"])
        step("H6(rust): cargo test --workspace")
        cargo_env = plain_env() | {
            "CARGO_TARGET_DIR": str(paths["rust_target"]),
            "PYTHONDONTWRITEBYTECODE": "1"}
        cargo = run(["cargo", "test", "--workspace"], REPO / "rust",
                    "h6-cargo.log", cargo_env, timeout=cfg["cargo_timeout"])
    tail = [ln for ln in (py["out"] + py["err"]).splitlines() if ln.strip()]
    summary = next((ln for ln in reversed(tail)
                    if " passed" in ln or " failed" in ln or " error" in ln),
                   None)
    results = [ln for ln in (cargo["out"] + cargo["err"]).splitlines()
               if ln.startswith("test result:")]
    return {
        "python": {"rc": py["rc"], "wall": round(py["wall"], 3),
                   "summary": summary, "log": py["log"],
                   "env": sorted(k for k in env if k.startswith("SENSORIUM_")
                                 or k == "PYTHONDONTWRITEBYTECODE")},
        "cargo": {"rc": cargo["rc"], "wall": round(cargo["wall"], 3),
                  "result_lines": results, "log": cargo["log"],
                  "target": str(paths["rust_target"])},
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
    }


# -------------------------------------------------------------------- main


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
        res["oracle"] = orc
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
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-grain-raw.json").write_text(
        json.dumps(res, indent=2, default=str))
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
