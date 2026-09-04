#!/usr/bin/env python3
"""The rung-3-entry E5' runner: E5 re-measured under the new spawned-task
naming rule (`<parent> :: spawn@<qualname>#<k>`).

It measures the three endpoints `docs/superpowers/acceptance/
2026-09-03-sensorium-rung3-entry-e5prime.md` §1 pre-registered, and nothing
else. §1 is BYTE-LOCKED at its own commit: this runner refuses to start if the
working tree's §1 differs from that commit's, so the endpoint cannot move
after a number is read.

It re-uses the rung-2 instrument rather than restating it: `acceptance_lib`
for paths, processes and manifests, `acceptance_phases.phase_e5` for the three
arms and the four diffs, and `acceptance.real_config` for the arm refs and the
test filter. What is NEW here is only what E5 did not measure:

  * the four spawned children's task NAMES on arms A and B, read from each
    arm's trace with
        select task_id, name, hash, n_events from task_fingerprints order by task_id
    against `$SENSORIUM_DIR/traces/<run>.db` opened read-only (the `sensorium`
    CLI has no `tasks` command; this is the same table `diff` compares by
    `(name, hash)`), and
  * the units that FELL BACK to the real tree across the three arms, from the
    manifests each arm's build wrote. The manifests directory is cleared
    before arm A (rung-2 practice) so no rung-2 manifest can enter the count,
    and each arm's build is snapshotted the moment it returns -- arms B and C
    recompile the same unit, so a manifest read only at the end would be arm
    C's alone.

The rung-2 ledger is READ-ONLY for this slice: `LEDGER` and `LOGS` are
re-pointed at this plan's own workspace before anything runs.

Every location is an environment variable, as in the run (`acceptance_lib.
env_paths`); a missing one refuses in the preflight. Two of the six --
`SENSORIUM_CENSUS_DRIVER` and `SENSORIUM_PROBE_TARGET` -- belong to phases
this runner does not call; they are recorded in the pins as unused.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_e5prime.py \
        > <ledger>/acceptance/logs/e5prime.log 2>&1 &

The last act is `<ledger>/acceptance/logs/e5prime.DONE` (or `.FAILED`)
carrying `exit=<n>`, so silence is distinguishable from success.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = (REPO / ".superpowers" / "sdd"
        / "2026-09-03-sensorium-rung3-entry-spawn-names")
LEDGER = PLAN
LOGS = PLAN / "acceptance" / "logs"

# The rung-2 ledger is evidence and is not written to again. Re-point the
# shared plumbing BEFORE importing the phases, so every log this run writes --
# including the ones `run()` and `sensorium_cli()` tee -- lands in this plan's
# own workspace.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_phases as ph                                     # noqa: E402
from acceptance import real_config                                 # noqa: E402
from acceptance_lib import (CLONE_PIN, LOAD_CEILING, REPO_DISK_FLOOR_GB,  # noqa: E402
                            STEPS, TARGET_DISK_FLOOR_GB, Refused, dir_bytes,
                            env_paths, free_gb, git, loadavg, manifests_dir,
                            read_manifests, run_lines, sha256_file, step)

ph.LOGS = LOGS

DOC = REPO / "docs" / "superpowers" / "acceptance" / \
    "2026-09-03-sensorium-rung3-entry-e5prime.md"
BYTE_LOCK = "10f2c59"
SOURCE_BLOOMERY = Path("/home/brice/workspace/bloomery")   # read-only; see pins

# §1's tips, as the pre-registration names them.
ARM_TIPS = {"A": CLONE_PIN, "B": "e8c79be", "C": "fea50b1"}

# §1's E5'-names prediction: one literal spawn site, inside
# `impl TaskRegistry { pub fn spawn_task(..) }`, on both branches.
PREDICTED = re.compile(
    r"^task::registry::tests::(?P<test>[A-Za-z0-9_]+)"
    r" :: spawn@TaskRegistry::spawn_task#1$")
PREDICTED_SHAPE = "task::registry::tests::<test> :: spawn@TaskRegistry::spawn_task#1"

TASK_QUERY = ("select task_id, name, hash, n_events from task_fingerprints "
              "order by task_id")

# Filled by the `run` hook: the manifests each arm's build left behind.
ARM_MANIFESTS: dict = {}


def out(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------- the byte-lock


def byte_lock_check() -> dict:
    """§1 of the acceptance document, as committed, versus the working tree.

    The endpoint is decided before the instrument exists; this is the check
    that it did not move afterwards. `awk '/^## 1/,/^## 2/'` is the same
    extraction the brief names."""
    rel = DOC.relative_to(REPO).as_posix()
    committed = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{BYTE_LOCK}:{rel}"],
        capture_output=True, text=True)
    if committed.returncode != 0:
        raise Refused(f"cannot read {rel} at {BYTE_LOCK}: "
                      f"{committed.stderr.strip()}")

    def section1(text: str) -> str:
        keep, buf = False, []
        for line in text.splitlines(keepends=True):
            if line.startswith("## 1"):
                keep = True
            if keep:
                buf.append(line)
            if keep and line.startswith("## 2"):
                break
        return "".join(buf)

    locked = section1(committed.stdout)
    now = section1(DOC.read_text())
    import hashlib
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()          # noqa: E731
    rec = {"commit": BYTE_LOCK, "doc": rel,
           "locked_sha256": h(locked), "working_tree_sha256": h(now),
           "locked_bytes": len(locked.encode()),
           "working_tree_bytes": len(now.encode()),
           "identical": locked == now,
           "extraction": "awk '/^## 1/,/^## 2/'"}
    if not rec["identical"]:
        raise Refused(
            f"§1 of {rel} differs from the byte-lock at {BYTE_LOCK}: "
            f"{rec['locked_sha256'][:12]} vs {rec['working_tree_sha256'][:12]}")
    step(f"byte-lock ok: §1 == {BYTE_LOCK}:{rel} "
         f"(sha256 {rec['locked_sha256'][:12]}, {rec['locked_bytes']} bytes)")
    return rec


# ---------------------------------------------------------------- preflight


def preflight(paths, cfg) -> dict:
    step("E5' preflight")
    clone = paths["sensorium_bloomery_clone"]
    target = paths["sensorium_acceptance_target"]
    load = loadavg()
    target_free = free_gb(target)
    repo_free = free_gb(REPO)
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{target}: {target_free:.1f} GB free < "
                      f"{TARGET_DISK_FLOOR_GB} GB floor")
    if repo_free < REPO_DISK_FLOOR_GB:
        raise Refused(f"{REPO}: {repo_free:.1f} GB free < "
                      f"{REPO_DISK_FLOOR_GB} GB floor")
    driver = Path(paths["sensorium_driver"])
    if not driver.is_file():
        raise Refused(f"no driver at {driver}")

    head = git(paths, "rev-parse", "HEAD").strip()
    porcelain = git(paths, "status", "--porcelain")
    if head != CLONE_PIN:
        raise Refused(f"the clone is at {head}, pinned at {CLONE_PIN}")
    if porcelain.strip():
        raise Refused(f"the clone is not clean:\n{porcelain}")
    tips = {}
    for label, ref in cfg["e5_arms"]:
        tip = out("git", "-C", str(clone), "rev-parse", ref)
        if not tip:
            raise Refused(f"arm {label}: the clone cannot resolve {ref!r}")
        if not tip.startswith(ARM_TIPS[label]):
            raise Refused(f"arm {label} ({ref}) is at {tip}, §1 names "
                          f"{ARM_TIPS[label]}")
        tips[label] = tip

    sdir = paths["sensorium_dir"]
    if sdir.exists() and any(sdir.iterdir()):
        raise Refused(f"SENSORIUM_DIR {sdir} is not empty; this run needs a "
                      "NEW traces directory")
    sdir.mkdir(parents=True, exist_ok=True)

    src_head = out("git", "-C", str(SOURCE_BLOOMERY), "rev-parse", "HEAD")
    src_porcelain = out("git", "-C", str(SOURCE_BLOOMERY), "status", "--porcelain")

    # The manifests directory is cleared before arm A, so every `fell_back`
    # counted below belongs to THIS invocation. The rest of the warm target is
    # left alone -- the lens says warm, and emptying it would be a different
    # measurement.
    md = manifests_dir(paths)
    stale = sorted(p.name for p in md.glob("*.json")) if md.is_dir() else []
    stale_bytes = sum((md / n).stat().st_size for n in stale)
    for n in stale:
        (md / n).unlink()
    step(f"preflight: cleared {len(stale)} stale manifest(s) "
         f"({stale_bytes} bytes) from {md}")

    pins = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse",
                           "--abbrev-ref", "HEAD"),
        "repo_porcelain": out("git", "-C", str(REPO), "status", "--porcelain"),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "driver_mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                      time.localtime(driver.stat().st_mtime)),
        "rustc": out("rustc", "-V"), "cargo": out("cargo", "-V"),
        "toolchains": out("rustup", "toolchain", "list"),
        "python": out(str(REPO / ".venv" / "bin" / "python"), "-V"),
        "sensorium_version": out(
            str(REPO / ".venv" / "bin" / "python"), "-c",
            "import importlib.metadata as m; print(m.version('sensorium'))"),
        "nproc": os.cpu_count(),
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/"
                         "scaling_governor").read_text().strip(),
        "RUSTFLAGS": os.environ.get("RUSTFLAGS", ""),
        "CARGO_INCREMENTAL": os.environ.get("CARGO_INCREMENTAL", ""),
        "RUSTC_WRAPPER": os.environ.get("RUSTC_WRAPPER", ""),
        "load_1min_at_start": load,
        "target_disk_free_gb": round(target_free, 2),
        "repo_disk_free_gb": round(repo_free, 2),
        "clone": str(clone), "clone_head": head,
        "clone_porcelain_before": porcelain,
        "clone_branches_before": git(paths, "branch", "-v").strip(),
        "arm_tips": tips,
        "clone_cargo_lock_sha256_before": sha256_file(clone / "Cargo.lock"),
        "source_bloomery": str(SOURCE_BLOOMERY),
        "source_bloomery_head_before": src_head,
        "source_bloomery_porcelain_before": src_porcelain,
        "target_dir": str(target), "target_warm": True,
        "target_bytes_before": dir_bytes(target),
        "manifests_cleared_before_arm_a": stale,
        "manifests_cleared_bytes": stale_bytes,
        "sensorium_dir": str(sdir),
        "packages": cfg["packages"],
        "unused_env": {
            "SENSORIUM_CENSUS_DRIVER": str(paths["sensorium_census_driver"]),
            "SENSORIUM_PROBE_TARGET": str(paths["sensorium_probe_target"]),
            "why": "required by acceptance_lib.env_paths for phases this "
                   "runner does not call (census, E7(a)); neither is read here",
        },
    }
    step(f"preflight ok: load={load} target_free={target_free:.1f}GB "
         f"driver={pins['driver_sha256'][:12]} arms={tips}")
    return pins


# ------------------------------------------------- per-arm manifests + runs


def _snapshot_manifests(paths, label: str, t0: float) -> None:
    """Every manifest present the moment arm `label`'s build returned.

    Arms B and C recompile the same unit under the same `-C metadata=`, so the
    file is OVERWRITTEN: a manifest read once at the end would be arm C's
    alone. `written_during_this_arm` is the mtime attribution -- a manifest
    older than the build's start was left by an earlier arm of THIS run (the
    directory was cleared before arm A), which is a fact about cargo's
    freshness, not a fell-back unit going unseen."""
    d = manifests_dir(paths)
    keep = LOGS / f"manifests-{label}"
    shutil.rmtree(keep, ignore_errors=True)
    keep.mkdir(parents=True, exist_ok=True)
    units = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        m = json.loads(p.read_text())
        shutil.copy2(p, keep / p.name)
        units.append({
            "metadata": p.stem, "unit": m["unit"],
            "crate_name": m["crate_name"], "crate_type": m["crate_type"],
            "fell_back": m["fell_back"],
            "fallback_reason": m.get("fallback_reason"),
            "unreached_files": m.get("unreached_files", []),
            "unreached_reasons": m.get("unreached_reasons", {}),
            "files": len(m["files"]),
            "sites": sum(len(v) for v in m["files"].values()),
            "spawns": m.get("spawns", []),
            "mtime": p.stat().st_mtime,
            "written_during_this_arm": p.stat().st_mtime >= t0,
        })
    summary = read_manifests(paths, None)
    fell = [u for u in units if u["fell_back"]]
    ARM_MANIFESTS[label] = {
        "kept_at": str(keep), "units": units,
        "units_seen": len(units),
        "units_written_during_this_arm":
            len([u for u in units if u["written_during_this_arm"]]),
        "fell_back": fell, "fell_back_count": len(fell),
        "unreached_reasons": {u["unit"]: u["unreached_reasons"]
                              for u in units if u["unreached_reasons"]},
        "unreached_files": sorted({f for u in units
                                   for f in u["unreached_files"]}),
        "read_manifests_summary": {
            "distinct": summary["distinct"],
            "raw_site_total": summary["raw_site_total"],
            "units": len(summary["units"]),
            "fell_back": summary["fell_back"],
            "spawns_wrapped": summary["spawns_wrapped"],
            "spawns_declared": summary["spawns_declared"],
            "unreached_files": summary["unreached_files"],
            "skipped": len(summary["skipped"]),
        },
    }
    step(f"E5' arm {label} manifests: units={len(units)} "
         f"(written by this arm: "
         f"{ARM_MANIFESTS[label]['units_written_during_this_arm']}) "
         f"fell_back={len(fell)} "
         f"spawns_wrapped={summary['spawns_wrapped']}")


ARM_RUNLINES: dict = {}
BUILD_LOG = re.compile(r"^e5-([ABC])-build\.log$")
RUN_LOG = re.compile(r"^e5-([ABC])-run\.log$")


def install_hook(paths):
    """`phase_e5` runs UNCHANGED; the only addition is a wrapper around the
    `run` it calls, which snapshots the manifests the instant an arm's build
    returns and keeps every `run:` line of an arm's recorded invocation."""
    original = ph.run

    def hooked(cmd, cwd, log_name, env=None, timeout=7200):
        t0 = time.time()
        res = original(cmd, cwd, log_name, env, timeout)
        b = BUILD_LOG.match(str(log_name))
        if b:
            _snapshot_manifests(paths, b.group(1), t0)
        r = RUN_LOG.match(str(log_name))
        if r:
            ARM_RUNLINES[r.group(1)] = {
                "run_lines": run_lines(res), "rc": res["rc"],
                "wall": round(res["wall"], 3),
            }
        return res

    ph.run = hooked
    return original


ARM_LOAD: dict = {}


def install_load_hook(paths):
    """The 1-minute load at each arm's start, which the lens names. `phase_e5`
    checks out the arm's ref first, so the `git checkout` is the arm's own
    first act."""
    original = ph.git

    def hooked(p, *args):
        if args and args[0] == "checkout":
            ref = args[-1]
            ARM_LOAD.setdefault("checkouts", []).append(
                {"ref": ref, "load_1min": loadavg(),
                 "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
        return original(p, *args)

    ph.git = hooked
    return original


# --------------------------------------------------------------------- names


def task_names(paths, run_id: str | None) -> dict:
    """Every task fingerprint of one trace, and the `spawn@` names among them.

    Read from the trace's own `task_fingerprints` table -- the table
    `sensorium diff` compares by `(name, hash)` -- with
    `TASK_QUERY` against a read-only connection. The `sensorium` CLI has no
    `tasks` command; this is the reader."""
    if not run_id:
        return {"run": None, "dropped": "the arm recorded no trace",
                "query": TASK_QUERY, "tasks": None, "spawn_tasks": None}
    db = paths["sensorium_dir"] / "traces" / f"{run_id}.db"
    if not db.is_file():
        return {"run": run_id, "dropped": f"no trace file at {db}",
                "query": TASK_QUERY, "tasks": None, "spawn_tasks": None}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = [{"task_id": t, "name": n, "hash": h, "n_events": e}
                for t, n, h, e in con.execute(TASK_QUERY)]
    finally:
        con.close()
    spawn = [r for r in rows if "spawn@" in (r["name"] or "")]
    matched = [r for r in spawn if PREDICTED.match(r["name"])]
    return {"run": run_id, "db": str(db), "query": TASK_QUERY,
            "tasks": rows, "task_count": len(rows),
            "spawn_tasks": spawn, "spawn_count": len(spawn),
            "as_predicted": [r["name"] for r in matched],
            "not_as_predicted": [r["name"] for r in spawn
                                 if not PREDICTED.match(r["name"])],
            "all_as_predicted": bool(spawn) and len(matched) == len(spawn),
            "dropped": None}


def names_endpoint(names: dict) -> dict:
    """E5'-names: the predicted string on both sides, and A's multiset of
    `(name, hash)` equal to B's."""
    a, b = names.get("A") or {}, names.get("B") or {}
    dropped = [f"arm {k}: {v['dropped']}" for k, v in (("A", a), ("B", b))
               if v.get("dropped")]
    if dropped:
        return {"value": None, "dropped": dropped, "multiset_equal": None,
                "a_multiset": None, "b_multiset": None}
    ma = sorted((r["name"], r["hash"]) for r in a["spawn_tasks"])
    mb = sorted((r["name"], r["hash"]) for r in b["spawn_tasks"])
    bad = a["not_as_predicted"] + b["not_as_predicted"]
    return {
        "predicted_shape": PREDICTED_SHAPE,
        "a_spawn_count": len(ma), "b_spawn_count": len(mb),
        "a_multiset": ma, "b_multiset": mb,
        "multiset_equal": ma == mb,
        "all_as_predicted": a["all_as_predicted"] and b["all_as_predicted"],
        "not_as_predicted": bad,
        "value": len(bad) + (0 if ma == mb else 1),
        "dropped": [],
    }


# ----------------------------------------------------------------- cleanup


def cleanup(paths, pins) -> dict:
    clone = paths["sensorium_bloomery_clone"]
    git(paths, "checkout", "-q", "--detach", CLONE_PIN)
    head = git(paths, "rev-parse", "HEAD").strip()
    porcelain = git(paths, "status", "--porcelain")
    src_head = out("git", "-C", str(SOURCE_BLOOMERY), "rev-parse", "HEAD")
    src_porcelain = out("git", "-C", str(SOURCE_BLOOMERY), "status", "--porcelain")
    c = {
        "clone_head_after": head,
        "clone_restored": head == CLONE_PIN,
        "clone_porcelain_after": porcelain,
        "clone_clean_after": not porcelain.strip(),
        "clone_branches_after": git(paths, "branch", "-v").strip(),
        "clone_cargo_lock_sha256_after": sha256_file(clone / "Cargo.lock"),
        "cargo_lock_unchanged": (sha256_file(clone / "Cargo.lock")
                                 == pins.get("clone_cargo_lock_sha256_before")),
        "source_bloomery_head_after": src_head,
        "source_bloomery_porcelain_after": src_porcelain,
        "source_bloomery_unchanged": (
            src_head == pins.get("source_bloomery_head_before")
            and src_porcelain == pins.get("source_bloomery_porcelain_before")),
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
        "driver_unchanged": (sha256_file(paths["sensorium_driver"])
                             == pins.get("driver_sha256")),
        "repo_porcelain_after": out("git", "-C", str(REPO), "status", "--porcelain"),
        "target_bytes_after": dir_bytes(paths["sensorium_acceptance_target"]),
        "sensorium_dir_bytes": dir_bytes(paths["sensorium_dir"])
        if paths["sensorium_dir"].is_dir() else 0,
        "target_disk_free_gb_after": round(
            free_gb(paths["sensorium_acceptance_target"]), 2),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"cleanup: clone at {head[:12]} restored={c['clone_restored']} "
         f"clean={c['clone_clean_after']} "
         f"source_unchanged={c['source_bloomery_unchanged']}")
    return c


# -------------------------------------------------------------------- main


def main(argv) -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("e5prime.DONE", "e5prime.FAILED"):
        (LOGS / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": "rust/tests/acceptance_e5prime.py",
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = pins = None
    try:
        res["byte_lock"] = byte_lock_check()
        paths = env_paths(False)
        cfg = real_config(paths)
        res["config"] = dict(cfg)
        pins = preflight(paths, cfg)
        res["pins"] = pins

        install_hook(paths)
        install_load_hook(paths)
        step("E5': three arms, four diffs (phase_e5, unchanged)")
        raw_e5 = ph.phase_e5(paths, cfg)
        res["raw_e5"] = raw_e5
        res["arm_manifests"] = ARM_MANIFESTS
        res["arm_run_lines"] = ARM_RUNLINES
        res["arm_checkout_loads"] = ARM_LOAD.get("checkouts", [])

        arms = raw_e5.get("arms") or {}
        names = {k: task_names(paths, (arms.get(k) or {}).get("run"))
                 for k in ("A", "B", "C")}
        res["names"] = names
        res["names_endpoint"] = names_endpoint(names)
        for k in ("A", "B", "C"):
            n = names[k]
            step(f"E5' names arm {k}: tasks={n.get('task_count')} "
                 f"spawn@={n.get('spawn_count')} "
                 f"as_predicted={n.get('all_as_predicted')}")

        fell = {k: v["fell_back_count"] for k, v in ARM_MANIFESTS.items()}
        res["coverage_endpoint"] = {
            "per_arm_fell_back": fell,
            "units_fell_back": sum(fell.values()) if fell else None,
            "units_seen": {k: v["units_seen"] for k, v in ARM_MANIFESTS.items()},
            "unreached_reasons": {k: v["unreached_reasons"]
                                  for k, v in ARM_MANIFESTS.items()
                                  if v["unreached_reasons"]},
            "dropped": [] if len(ARM_MANIFESTS) == 3 else
            [f"only {len(ARM_MANIFESTS)} of 3 arms left a manifest snapshot"],
        }
        step(f"E5' coverage: fell_back per arm {fell}")

        res["cleanup"] = cleanup(paths, pins)
    except Refused as e:
        step(f"REFUSED: {e}")
        res["refused"] = str(e)
        rc = 3
    except Exception:                                          # noqa: BLE001
        import traceback
        step("ERROR: " + traceback.format_exc().strip().splitlines()[-1])
        res["error"] = traceback.format_exc()
        rc = 4
    if paths and res.get("cleanup") is None and pins is not None:
        try:
            res["cleanup_after_failure"] = cleanup(paths, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["steps"] = STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-e5prime-raw.json").write_text(
        json.dumps(res, indent=2, default=str))
    (LOGS / ("e5prime.DONE" if rc == 0 else "e5prime.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw E5' facts at "
         f"{LEDGER / 'results-e5prime-raw.json'}")
    return rc


def assemble_only() -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no arm and reads
    no new number: it exists so the assembly is reproducible from committed
    code rather than from a one-off script (the rung-2 precedent,
    `acceptance.py --assemble`)."""
    from acceptance_schema import assemble_e5prime                 # noqa: PLC0415
    raw = json.loads((LEDGER / "results-e5prime-raw.json").read_text())
    out = assemble_e5prime(raw)
    out["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": "results-e5prime-raw.json",
        "by": "rust/tests/acceptance_e5prime.py --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no arm was re-run and no value re-measured"),
    }
    dest = REPO / "docs" / "superpowers" / "acceptance" / \
        "2026-09-03-sensorium-rung3-entry-e5prime.results.json"
    dest.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"assembled {dest} from results-e5prime-raw.json")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only())
    raise SystemExit(main(sys.argv[1:]))
