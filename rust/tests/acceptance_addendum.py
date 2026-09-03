#!/usr/bin/env python3
"""The rung-2 acceptance ADDENDUM runner: the reported-without-a-gate items,
re-measured after the converter's one-transaction fix.

It re-measures nothing that a §1 endpoint rests on. The five gated verdicts and
every §3 cell they stand on were measured at commit 46074ef and stay exactly as
they were; this runner produces a second, dated column beside them, and
`acceptance_schema.assemble` renders both.

What it measures, and the four lenses:

  (a) the whole-invocation conversion wall -- `cargo-sensorium convert` over
      the SAME spool directory the acceptance run recorded, a SECOND pass over
      an already-converted spool, n=3, median;
  (b) the `--lib` plain-vs-call walls -- the same protocol as the run itself
      (5 rounds, order alternating P,C then C,P, 10 s cool-down, the 1-minute
      load read at each arm's start and an arm DROPPED, never re-rolled, above
      4.0), through `acceptance_phases.phase_walls`;
  (c) the conversion wall of ONE `--lib` trace alone, so a reader can subtract
      it from (b)'s in-command number rather than be told what is left;
  (d) the driver's fixed cost (a no-op `--tier off --no-run` invocation, n=5,
      reported both absolutely and as the difference of medians the run
      reported) and the runtime rlib's build wall from a cleared rt directory.

Every location is an environment variable, as in the run: the six
`acceptance_lib.env_paths` reads, plus `SENSORIUM_WHOLE_SPOOL` naming the spool
directory (a) converts. `SENSORIUM_DIR` must name a NEW traces directory -- the
acceptance run's own is evidence and is not written to again.

    setsid nohup .venv/bin/python rust/tests/acceptance_addendum.py > <log> 2>&1 &
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_lib import (LEDGER, LOGS, LOAD_CEILING, REPO,                # noqa: E402
                            REPO_DISK_FLOOR_GB, STEPS, TARGET_DISK_FLOOR_GB,
                            Refused, dir_bytes, driver_cmd, env_paths,
                            free_gb, git, loadavg, rmtree, run, run_lines,
                            sha256_file, spool_of, step, target_env)
import acceptance_phases as ph                                              # noqa: E402
from acceptance import real_config                                          # noqa: E402

CONVERT_N = 3
NOOP_N = 5


def out(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def convert_n(paths, spool: Path, n: int, label: str) -> dict:
    """`cargo-sensorium convert <spool>`, n times, walls and medians."""
    walls, procs, rcs = [], [], []
    for i in range(n):
        res = run([str(paths["sensorium_driver"]), "convert", str(spool)],
                  paths["sensorium_bloomery_clone"], f"add-convert-{label}-{i}.log",
                  target_env(paths))
        walls.append(round(res["wall"], 3))
        procs.append(len(run_lines(res)))
        rcs.append(res["rc"])
        step(f"convert[{label}] {i + 1}/{n}: {walls[-1]}s rc={res['rc']} "
             f"processes={procs[-1]}")
    ok = [w for w, rc in zip(walls, rcs) if rc == 0]
    return {"spool": str(spool), "walls": walls, "rcs": rcs,
            "processes": procs, "spool_bytes": dir_bytes(spool),
            "spool_files": len([q for q in spool.rglob("*") if q.is_file()]),
            "median": round(statistics.median(ok), 3) if ok else None,
            "n": len(ok),
            "dropped": [] if len(ok) == n else
            [f"{n - len(ok)} of {n} passes exited non-zero"]}


def phase_lib_trace(paths, cfg) -> dict:
    """One recorded `--lib` invocation whose spool is KEPT, then converted
    again n times: (b)'s in-command number minus this is what the command
    spends outside conversion."""
    res = run(driver_cmd(paths, *cfg["pkg"], "--lib"),
              paths["sensorium_bloomery_clone"], "add-lib-run.log", target_env(paths))
    lines = run_lines(res)
    sp = spool_of(res)
    step(f"lib trace: wall={res['wall']:.3f}s processes={len(lines)} "
         f"events={sum(l['events'] for l in lines)}")
    conv = convert_n(paths, Path(sp), CONVERT_N, "lib") if sp else None
    return {"invocation_wall": round(res["wall"], 3), "rc": res["rc"],
            "processes": len(lines),
            "events": sum(l["events"] for l in lines),
            "conversion": conv}


def phase_costs(paths, cfg) -> dict:
    """The driver's fixed cost and the runtime rlib's build wall."""
    step("costs: no-op invocations, both ways")
    instr, plain = [], []
    for i in range(NOOP_N):
        instr.append(round(run(driver_cmd(paths, *cfg["pkg"], "--no-run", tier="off"),
                               paths["sensorium_bloomery_clone"],
                               f"add-cost-instr-{i}.log", target_env(paths))["wall"], 3))
        plain.append(round(run(["cargo", "test", *cfg["pkg"], "--no-run"],
                               paths["sensorium_bloomery_clone"],
                               f"add-cost-plain-{i}.log", target_env(paths))["wall"], 3))
    warm = statistics.median(instr)
    rt = paths["sensorium_acceptance_target"] / "sensorium" / "rt"
    removed = rmtree(rt)
    cold = run(driver_cmd(paths, *cfg["pkg"], "--no-run", tier="off"),
               paths["sensorium_bloomery_clone"], "add-cost-rt-cold.log",
               target_env(paths))
    step(f"costs: no-op {warm}s, overhead {round(warm - statistics.median(plain), 3)}s, "
         f"rt rebuild {round(cold['wall'] - warm, 3)}s")
    return {"instrumented_walls": instr, "plain_walls": plain,
            "instrumented_median": round(warm, 3),
            "plain_median": round(statistics.median(plain), 3),
            "driver_overhead_s": round(warm - statistics.median(plain), 3),
            "rt_removed_bytes": removed, "rt_cold_wall": round(cold["wall"], 3),
            "rt_build_s": round(cold["wall"] - warm, 3), "rt_rc": cold["rc"]}


def preflight(paths, cfg, spool: Path) -> dict:
    step("addendum preflight")
    load, tfree, rfree = loadavg(), free_gb(paths["sensorium_acceptance_target"]), free_gb(REPO)
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    if tfree < TARGET_DISK_FLOOR_GB:
        raise Refused(f"target disk {tfree:.1f} GB < {TARGET_DISK_FLOOR_GB}")
    if rfree < REPO_DISK_FLOOR_GB:
        raise Refused(f"repo disk {rfree:.1f} GB < {REPO_DISK_FLOOR_GB}")
    if not spool.is_dir():
        raise Refused(f"no spool directory at {spool}")
    if paths["sensorium_dir"].name == "acceptance":
        raise Refused("SENSORIUM_DIR must be a NEW directory; the acceptance "
                      "run's own traces are evidence and are not written to again")
    head = git(paths, "rev-parse", "HEAD").strip()
    porcelain = git(paths, "status", "--porcelain")
    if porcelain.strip():
        raise Refused(f"the clone is not clean:\n{porcelain}")
    pins = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"),
        "driver": str(paths["sensorium_driver"]),
        "driver_sha256": sha256_file(paths["sensorium_driver"]),
        "clone_head": head, "clone_porcelain_before": porcelain,
        "load_1min_at_start": load,
        "target_disk_free_gb": round(tfree, 2), "repo_disk_free_gb": round(rfree, 2),
        "rustc": out("rustc", "-V"), "cargo": out("cargo", "-V"),
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/"
                         "scaling_governor").read_text().strip(),
        "nproc": os.cpu_count(),
        "sensorium_dir": str(paths["sensorium_dir"]),
        "whole_spool": str(spool),
        "target_dir": str(paths["sensorium_acceptance_target"]),
        "target_warm": True,
    }
    step(f"addendum preflight ok: load={load} target_free={tfree:.1f}GB "
         f"driver={pins['driver_sha256'][:12]}")
    return pins


def main(argv) -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    for m in ("addendum.DONE", "addendum.FAILED"):
        (LOGS / m).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    rc = 0
    try:
        paths = env_paths(False)
        cfg = real_config(paths)
        spool_env = os.environ.get("SENSORIUM_WHOLE_SPOOL")
        if not spool_env:
            raise Refused("SENSORIUM_WHOLE_SPOOL is unset: name the spool "
                          "directory the acceptance run recorded")
        spool = Path(spool_env)
        res["pins"] = preflight(paths, cfg, spool)

        res["conversion_whole"] = convert_n(paths, spool, CONVERT_N, "whole")

        step("walls: pre-building both arms under the new driver")
        run(["cargo", "test", *cfg["pkg"], "--lib", "--no-run"],
            paths["sensorium_bloomery_clone"], "add-prebuild-plain.log",
            target_env(paths))
        run(driver_cmd(paths, *cfg["pkg"], "--lib", "--no-run"),
            paths["sensorium_bloomery_clone"], "add-prebuild-call.log",
            target_env(paths))
        res["walls"] = ph.phase_walls(paths, cfg)
        res["lib_trace"] = phase_lib_trace(paths, cfg)
        res["costs"] = phase_costs(paths, cfg)
        res["cleanup"] = {
            "clone_head_after": git(paths, "rev-parse", "HEAD").strip(),
            "clone_porcelain_after": git(paths, "status", "--porcelain"),
            "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
            "target_disk_free_gb_after": round(
                free_gb(paths["sensorium_acceptance_target"]), 2),
            "addendum_traces_bytes": dir_bytes(paths["sensorium_dir"])
            if paths["sensorium_dir"].is_dir() else 0,
            "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
    except Refused as e:
        step(f"REFUSED: {e}")
        res["refused"] = str(e)
        rc = 3
    except Exception:                                              # noqa: BLE001
        import traceback
        step("ERROR: " + traceback.format_exc().strip().splitlines()[-1])
        res["error"] = traceback.format_exc()
        rc = 4
    res["steps"] = STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-addendum-raw.json").write_text(
        json.dumps(res, indent=2, default=str))
    (LOGS / ("addendum.DONE" if rc == 0 else "addendum.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw addendum facts at {LEDGER / 'results-addendum-raw.json'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
