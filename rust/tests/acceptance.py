#!/usr/bin/env python3
"""The rung-2 acceptance runner: E2', E3, E5, E7 and E8 against a real
workspace, in the order `docs/superpowers/acceptance/
2026-09-02-sensorium-rung2-acceptance.md` §1 pre-registered.

It writes `results.json` in the pre-registered none-versus-zero schema, every
raw log beside it, and `results-raw.json` with the facts each cell came from.
It never writes §4: the decisions are written by hand against the rules.

Nothing here names a machine. Every location is an environment variable
(`acceptance_lib.env_paths`), and a missing one refuses in the preflight.

Launch it detached -- the real run is half an hour of builds and 20 recorded
runs -- and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance.py > <log> 2>&1 &

The last act is `<ledger>/logs/acceptance.DONE` (or `.FAILED`), so silence is
distinguishable from success. `--dry-run` runs the same code against the probe
workspace with the counts turned down and every endpoint cell marked
`not measured (dry run)`: it proves the artifacts, not the numbers.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_lib import (CLONE_PIN, E3_RUNS, LEDGER, LOGS, LOAD_CEILING,  # noqa: E402
                            REPO, REPO_DISK_FLOOR_GB, STEPS,
                            TARGET_DISK_FLOOR_GB, Refused, dir_bytes,
                            env_paths, free_gb, git, loadavg, rmtree,
                            sha256_file, step, workspace_packages)
import acceptance_phases as ph                                     # noqa: E402
from acceptance_schema import assemble                             # noqa: E402


def out(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


# ------------------------------------------------------------------ configs


def real_config(paths) -> dict:
    root = paths["sensorium_bloomery_clone"]
    return {
        "packages": workspace_packages(root),
        "pkg": ["-p", "bloomery-daemon"],
        "workspace_sel": ["--workspace"],
        "lib_target": "bloomery_daemon",
        "touch_file": "crates/bloomery-core/src/lib.rs",
        # bloomery-daemon depends on bloomery-core; bloomery-substrate does
        # not (its Cargo.toml has no bloomery-core dependency), so a touch of
        # core must recompile exactly these two and leave substrate Fresh.
        "touch_expect_compiled": ["bloomery-core", "bloomery-daemon"],
        "reached_prefixes": ("crates/bloomery-core/src/",
                             "crates/bloomery-substrate/src/",
                             "crates/bloomery-daemon/src/",
                             "crates/bloomery-daemon/tests/"),
        "e5_arms": [("A", CLONE_PIN), ("B", "e5-split"), ("C", "e5-planted")],
        "e5_filter": "task::registry",
        "e5_task": "task::registry::tests::spawn_task_runs_in_background_"
                   "and_get_reflects_completion",
        "e8_branch": "e8-touch",
        "arm_a": CLONE_PIN,
        "git": True,
        "e3_runs": E3_RUNS,
        "wall_rounds": 5,
    }


def dry_config(paths) -> dict:
    """The same protocol against the probe workspace, counts turned down.
    The probe is not a git repository of its own, so the E5 arms are the same
    tree three times and E8(b) restores by bytes: what this proves is that
    every step runs and every artifact is written, not any number."""
    root = paths["sensorium_bloomery_clone"]
    return {
        "packages": workspace_packages(root),
        "pkg": ["-p", "probe-app"],
        "workspace_sel": ["--workspace"],
        "lib_target": "probe_app",
        "touch_file": "probe-core/src/lib.rs",
        "touch_expect_compiled": ["probe-app", "probe-core"],
        "reached_prefixes": ("probe-app/src/", "probe-core/src/",
                             "probe-app/tests/"),
        "e5_arms": [("A", "HEAD"), ("B", "HEAD"), ("C", "HEAD")],
        "e5_filter": "tally",
        "e5_task": None,
        "e8_branch": None,
        "arm_a": "HEAD",
        "git": False,
        "e3_runs": 3,
        "wall_rounds": 1,
    }


# ---------------------------------------------------------------- preflight


def preflight(paths, cfg, dry) -> dict:
    step("preflight")
    clone = paths["sensorium_bloomery_clone"]
    target = paths["sensorium_acceptance_target"]
    target.mkdir(parents=True, exist_ok=True)
    load = loadavg()
    target_free = free_gb(target)
    repo_free = free_gb(REPO)
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{target}: {target_free:.1f} GB free < "
                      f"{TARGET_DISK_FLOOR_GB} GB floor")
    if repo_free < REPO_DISK_FLOOR_GB:
        raise Refused(f"{REPO}: {repo_free:.1f} GB free < {REPO_DISK_FLOOR_GB} GB floor")
    driver = paths["sensorium_driver"]
    if not Path(driver).is_file():
        raise Refused(f"no driver at {driver}")
    if not Path(paths["sensorium_census_driver"]).is_file():
        raise Refused(f"no census driver at {paths['sensorium_census_driver']}")
    version = out(str(REPO / ".venv" / "bin" / "python"), "-c",
                  "import importlib.metadata as m; print(m.version('sensorium'))")
    head = porcelain = branch = None
    if cfg["git"]:
        head = git(paths, "rev-parse", "HEAD").strip()
        porcelain = git(paths, "status", "--porcelain")
        branch = git(paths, "branch", "--show-current").strip()
        if head != CLONE_PIN:
            raise Refused(f"the clone is at {head}, pinned at {CLONE_PIN}")
        if porcelain.strip():
            raise Refused(f"the clone is not clean:\n{porcelain}")
    src = paths["source_bloomery"]
    src_head = src_porcelain = None
    if src:
        src_head = out("git", "-C", str(src), "rev-parse", "HEAD")
        src_porcelain = out("git", "-C", str(src), "status", "--porcelain")

    removed = 0
    for child in sorted(target.iterdir()):
        removed += rmtree(child)
    emptied_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    step(f"preflight: emptied the target directory ({removed} bytes) at {emptied_at}")

    pins = {
        "dry_run": dry,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "rustc": out("rustc", "-V"), "cargo": out("cargo", "-V"),
        "toolchains": out("rustup", "toolchain", "list"),
        "nproc": os.cpu_count(),
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/"
                         "scaling_governor").read_text().strip(),
        "RUSTFLAGS": os.environ.get("RUSTFLAGS", ""),
        "CARGO_INCREMENTAL": os.environ.get("CARGO_INCREMENTAL", ""),
        "RUSTC_WRAPPER": os.environ.get("RUSTC_WRAPPER", ""),
        "RUSTDOCFLAGS": os.environ.get("RUSTDOCFLAGS", ""),
        "load_1min_at_start": load,
        "target_disk_free_gb": round(target_free, 2),
        "repo_disk_free_gb": round(repo_free, 2),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "census_driver": str(paths["sensorium_census_driver"]),
        "census_driver_sha256": sha256_file(paths["sensorium_census_driver"]),
        "sensorium_version": version,
        "python": out(str(REPO / ".venv" / "bin" / "python"), "-V"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"),
        "repo_porcelain": out("git", "-C", str(REPO), "status", "--porcelain"),
        "clone": str(clone), "clone_head": head, "clone_branch": branch,
        "clone_porcelain_before": porcelain,
        "clone_cargo_lock_sha256_before": sha256_file(clone / "Cargo.lock"),
        "source_bloomery": str(src) if src else None,
        "source_bloomery_head_before": src_head,
        "source_bloomery_porcelain_before": src_porcelain,
        "target_dir": str(target), "target_emptied_bytes": removed,
        "target_emptied_at": emptied_at,
        "sensorium_dir": str(paths["sensorium_dir"]),
        "packages": cfg["packages"],
    }
    step(f"preflight ok: load={load} target_free={target_free:.1f}GB "
         f"repo_free={repo_free:.1f}GB sensorium={version}")
    return pins


def cleanup(paths, cfg, pins) -> dict:
    step("cleanup")
    clone = paths["sensorium_bloomery_clone"]
    if cfg["git"]:
        git(paths, "checkout", "-q", "--detach", cfg["arm_a"])
    src = paths["source_bloomery"]
    for p in LOGS.glob("sentinel-spool-*"):
        rmtree(p)
    return {
        "clone_head_after": git(paths, "rev-parse", "HEAD").strip() if cfg["git"] else None,
        "clone_porcelain_after": git(paths, "status", "--porcelain") if cfg["git"] else None,
        "clone_branches": git(paths, "branch").strip() if cfg["git"] else None,
        "clone_cargo_lock_sha256_after": sha256_file(clone / "Cargo.lock"),
        "cargo_lock_unchanged": (sha256_file(clone / "Cargo.lock")
                                 == pins["clone_cargo_lock_sha256_before"]),
        "source_bloomery_head_after": out("git", "-C", str(src), "rev-parse", "HEAD")
        if src else None,
        "source_bloomery_porcelain_after": out("git", "-C", str(src), "status",
                                               "--porcelain") if src else None,
        "source_bloomery_unchanged": (
            out("git", "-C", str(src), "rev-parse", "HEAD") == pins["source_bloomery_head_before"]
            and out("git", "-C", str(src), "status", "--porcelain")
            == pins["source_bloomery_porcelain_before"]) if src else None,
        "repo_porcelain_after": out("git", "-C", str(REPO), "status", "--porcelain"),
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
        "driver_unchanged": sha256_file(paths["sensorium_driver"]) == pins["driver_sha256"],
        "target_bytes": dir_bytes(paths["sensorium_acceptance_target"]),
        "sensorium_dir_bytes": dir_bytes(paths["sensorium_dir"])
        if paths["sensorium_dir"].is_dir() else 0,
        "target_disk_free_gb_after": round(free_gb(paths["sensorium_acceptance_target"]), 2),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


# --------------------------------------------------------------------- main


def main(argv) -> int:
    dry = "--dry-run" in argv
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("acceptance.DONE", "acceptance.FAILED"):
        (LOGS / marker).unlink(missing_ok=True)
    results: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "dry_run": dry}
    rc = 0
    paths, cfg = None, None
    try:
        paths = env_paths(dry)
        cfg = dry_config(paths) if dry else real_config(paths)
        results["config"] = {k: v for k, v in cfg.items()}
        pins = preflight(paths, cfg, dry)
        results["pins"] = pins

        results["raw_e8"] = ph.phase_e8(paths, cfg)
        results["raw_census"] = ph.phase_census(paths, cfg)
        results["raw_e2_workspace"] = ph.phase_e2_workspace(paths, cfg)
        results["raw_e3"] = ph.phase_e3(paths, cfg)
        results["raw_walls"] = ph.phase_walls(paths, cfg)
        results["raw_e7b"] = ph.phase_e7b(paths, cfg)
        results["raw_e7a"] = ph.phase_e7a(paths)
        results["raw_e5"] = ph.phase_e5(paths, cfg)
        results["raw_whole"] = ph.phase_whole(paths, cfg)
        results["raw_costs"] = ph.phase_costs(paths, cfg)
        results["cleanup"] = cleanup(paths, cfg, pins)
    except Refused as e:
        step(f"REFUSED: {e}")
        results["refused"] = str(e)
        rc = 3
    except Exception:                                          # noqa: BLE001
        import traceback
        step("ERROR: " + traceback.format_exc().strip().splitlines()[-1])
        results["error"] = traceback.format_exc()
        rc = 4
    if paths and cfg and results.get("cleanup") is None:
        try:
            results["cleanup_after_failure"] = cleanup(
                paths, cfg, results.get("pins") or {})
        except Exception:                                      # noqa: BLE001
            pass
    results["steps"] = STEPS
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-raw.json").write_text(json.dumps(results, indent=2, default=str))
    try:
        (LEDGER / "results.json").write_text(
            json.dumps(assemble(results, dry), indent=2, default=str))
    except Exception:                                          # noqa: BLE001
        import traceback
        (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
        step("assemble FAILED (logs/assemble-error.txt); results-raw.json is intact")
        rc = rc or 5
    marker = "acceptance.DONE" if rc == 0 else "acceptance.FAILED"
    (LOGS / marker).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{results.get('refused') or results.get('error') or ''}\n")
    step(f"done rc={rc}; results at {LEDGER / 'results.json'}")
    return rc


if __name__ == "__main__":
    # `--assemble` re-derives `results.json` from the raw facts already on
    # disk. It re-runs no arm and reads no new number: it exists so a lens can
    # be corrected, or the schema re-checked, without touching a measurement.
    if "--assemble" in sys.argv[1:]:
        _raw = json.loads((LEDGER / "results-raw.json").read_text())
        _out = assemble(_raw, _raw.get("dry_run", False))
        # Stamped, so a reader of `results.json` can never mistake a
        # re-assembly for the run: the values come from `results-raw.json`,
        # which the run wrote and nothing since has touched.
        _out["assembled"] = {
            "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "from": "results-raw.json",
            "by": "rust/tests/acceptance.py --assemble",
            "note": ("re-derived from the raw facts the run recorded, under the "
                     "committed schema; no arm was re-run and no value was "
                     "re-measured -- only lens text can differ from the "
                     "assembly the run itself wrote"),
        }
        (LEDGER / "results.json").write_text(json.dumps(_out, indent=2, default=str))
        print(f"assembled {LEDGER / 'results.json'} from results-raw.json")
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
