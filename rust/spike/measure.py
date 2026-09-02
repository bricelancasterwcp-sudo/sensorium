#!/usr/bin/env python3
"""THROWAWAY SPIKE CODE (rung-1 Rust mechanics spike): the measurement runner.

Runs the pre-registered protocol of
`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` §1 against
`/home/brice/workspace/bloomery` (READ-ONLY: only `target/` is written) and the
probe workspace, and writes `results.json` in the pre-registered
none-versus-zero schema plus every raw log beside it.

It never writes §4: the decisions are written by hand against the rules.

Launch detached (E1 alone is 15 bloomery test-suite runs):

    setsid nohup .venv/bin/python rust/spike/measure.py > <log> 2>&1 &

It writes `<ledger>/logs/measure.DONE` (with the exit status inside) as its last
act, so silence is distinguishable from success.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------- paths

REPO = Path(__file__).resolve().parents[2]
SPIKE = REPO / "rust" / "spike"
BLOOMERY = Path("/home/brice/workspace/bloomery")
TARGET = BLOOMERY / "target"
LEDGER = REPO / ".superpowers" / "sdd" / "2026-09-02-sensorium-rung1-mechanics-spike"
LOGS = LEDGER / "logs"
DRIVER = SPIKE / "target" / "release" / "cargo-sensorium"
VENV_PY = REPO / ".venv" / "bin" / "python"
SENSORIUM = REPO / ".venv" / "bin" / "sensorium"
SENSORIUM_DIR = LOGS / "sensorium-dir"

# ----------------------------------------------------------------- constants

BLOOMERY_PIN = "e209ed9b00f7eef647fb31d0b0895a5ad3b90807"
LOAD_CEILING = 4.0          # plan §Global Constraints: refuse an arm above this
DISK_FLOOR_GB = 8.0         # plan Task 0: refuse to start under this
DISK_ABORT_GB = 2.0         # brief: abort an E1 round under this
E1_ROUNDS = 5
E1_SLEEP_S = 10
WS_PKGS = ("bloomery-core", "bloomery-substrate", "bloomery-daemon", "bloomery-bench")

# E2 denominators, all from `sensorium-transform`'s own `census` (the parser
# that instrumented), recorded in the preflight before any endpoint was read:
E2_DENOM_ALL = 2051         # crates/*/src + crates/*/tests   (the plan's file set)
E2_DENOM_SRC = 739          # crates/*/src only               (the §1 derivation's shape)
E2_DENOM_REACHED = 1723     # the files a `-p bloomery-daemon` build can reach
E2_CENSUS_LENS = (
    "sensorium-transform::census over bloomery @ e209ed9; 2056 fn items, "
    "5 const fn, 0 extern fn, 0 async fn -> 2051 eligible "
    "(739 in crates/*/src over 82 files, 1312 in crates/*/tests over 109 files); "
    "1723 eligible over the file set `cargo test -p bloomery-daemon` reaches "
    "(core/src + substrate/src + daemon/src + daemon/tests); "
    "328 eligible in files it never compiles (bench/src 60, bench/tests + "
    "core/tests + substrate/tests 268)"
)

STEPS: list[str] = []       # progress breadcrumbs, printed and kept


def meas(value, n, lens, dropped=None):
    """The pre-registered measurement shape. `None` + a reason is the ONLY
    representation of not-measured; `0` is measured-and-zero."""
    return {"value": value, "n": n, "lens": lens, "dropped": list(dropped or [])}


def step(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    STEPS.append(line)
    print(line, flush=True)


class Refused(Exception):
    """A preflight or invariant the runner refuses to proceed past."""


# ------------------------------------------------------------------ plumbing


def loadavg() -> float:
    return float(Path("/proc/loadavg").read_text().split()[0])


def free_gb(path: Path = BLOOMERY) -> float:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def plain_env() -> dict:
    """The environment for an UNINSTRUMENTED arm: no wrapper env at all."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("SENSORIUM_")
           and k not in ("RUSTC_WORKSPACE_WRAPPER", "RUSTDOCFLAGS", "CARGO_TARGET_DIR")}
    return env


def run(cmd, cwd, log_name, env=None, timeout=3600):
    """Run `cmd`, tee its combined output to `LOGS/<log_name>`, return a dict."""
    log = LOGS / log_name
    t0 = time.monotonic()
    p = subprocess.run(cmd, cwd=str(cwd), env=env or plain_env(),
                       capture_output=True, text=True, timeout=timeout)
    wall = time.monotonic() - t0
    log.write_text(
        f"$ {' '.join(str(c) for c in cmd)}\n(cwd={cwd})\n"
        f"--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}\n"
        f"--- rc={p.returncode} wall={wall:.3f} ---\n")
    return {"rc": p.returncode, "out": p.stdout, "err": p.stderr,
            "wall": wall, "log": str(log)}


def driver_cmd(*args, tier=None):
    cmd = [str(DRIVER), "sensorium", "test"]
    if tier:
        cmd += ["--tier", tier]
    return cmd + list(args)


def spool_of(res) -> str | None:
    m = re.findall(r"^spool: (.+)$", res["err"], re.M)
    return m[-1] if m else None


def cargo_exit_of(res):
    m = re.findall(r"^cargo exit: (-?\d+)$", res["err"], re.M)
    return int(m[-1]) if m else None


def unit_sets(res) -> tuple[list[str], list[str]]:
    """Workspace packages cargo said it Compiled / found Fresh, from `-v`."""
    both = res["out"] + res["err"]
    pat = r"^\s*(Compiling|Fresh) (%s) " % "|".join(WS_PKGS)
    comp, fresh = set(), set()
    for verb, pkg in re.findall(pat, both, re.M):
        (comp if verb == "Compiling" else fresh).add(pkg)
    return sorted(comp), sorted(fresh)


def test_exe(package_args, instrumented: bool, target_name: str) -> str | None:
    """The path of one test executable, by target name, from cargo's JSON."""
    if instrumented:
        cmd = driver_cmd(*package_args, "--no-run", "--message-format=json", tier="off")
        env = plain_env()
    else:
        cmd = ["cargo", "test", *package_args, "--no-run", "--message-format=json"]
        env = plain_env()
    res = run(cmd, BLOOMERY, f"exe-{'instr' if instrumented else 'plain'}-{target_name}.log", env)
    found = None
    for line in res["out"].splitlines():
        try:
            v = json.loads(line)
        except Exception:
            continue
        if v.get("reason") != "compiler-artifact":
            continue
        if v.get("target", {}).get("name") != target_name:
            continue
        if not v.get("profile", {}).get("test"):
            continue
        if v.get("executable"):
            found = v["executable"]
    return found


def thread_names(spool_dir: str, pid: int) -> list[str]:
    """The thread names libtest gave the threads that emitted, read from the
    spool file headers: b"SNSR" u8 version u32 serial u16 name_len name."""
    import struct
    names = []
    for f in sorted(Path(spool_dir).glob(f"{pid}.*.spool")):
        b = f.read_bytes()
        if len(b) < 11 or b[:4] != b"SNSR":
            continue
        n = struct.unpack_from("<H", b, 9)[0]
        names.append({"serial": struct.unpack_from("<I", b, 5)[0],
                      "name": b[11:11 + n].decode("utf-8", "replace")})
    return sorted(names, key=lambda d: d["serial"])


def dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


# ------------------------------------------------------------------ preflight


def preflight() -> dict:
    step("preflight")
    load = loadavg()
    disk = free_gb()
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    if disk < DISK_FLOOR_GB:
        raise Refused(f"free disk {disk:.1f} GB < {DISK_FLOOR_GB} GB floor")
    head = subprocess.run(["git", "-C", str(BLOOMERY), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    if head != BLOOMERY_PIN:
        raise Refused(f"bloomery is at {head}, pinned at {BLOOMERY_PIN}")
    porcelain = subprocess.run(["git", "-C", str(BLOOMERY), "status", "--porcelain"],
                               capture_output=True, text=True).stdout
    if porcelain.strip():
        raise Refused(f"bloomery is not clean:\n{porcelain}")
    branch = subprocess.run(["git", "-C", str(BLOOMERY), "branch", "--show-current"],
                            capture_output=True, text=True).stdout.strip()
    lock = subprocess.run(["sha256sum", str(BLOOMERY / "Cargo.lock")],
                          capture_output=True, text=True).stdout.split()[0]
    if not DRIVER.is_file():
        raise Refused(f"no release driver at {DRIVER} (cargo build --release)")
    pins = {
        "rustc": subprocess.run(["rustc", "-V"], capture_output=True, text=True).stdout.strip(),
        "cargo": subprocess.run(["cargo", "-V"], capture_output=True, text=True).stdout.strip(),
        "bloomery_commit": head,
        "bloomery_branch": branch,
        "bloomery_status_porcelain": porcelain,
        "cargo_lock_sha256_before": lock,
        "nproc": os.cpu_count(),
        "governor": Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read_text().strip(),
        "RUSTFLAGS": os.environ.get("RUSTFLAGS", ""),
        "CARGO_INCREMENTAL": os.environ.get("CARGO_INCREMENTAL", ""),
        "RUSTC_WRAPPER": os.environ.get("RUSTC_WRAPPER", ""),
        "load_1min_at_start": load,
        "free_gb_at_start": round(disk, 2),
        "driver": str(DRIVER),
        "driver_sha256": subprocess.run(["sha256sum", str(DRIVER)],
                                        capture_output=True, text=True).stdout.split()[0],
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"preflight ok: load={load} disk={disk:.1f}GB bloomery={head[:7]} clean")
    return pins


# ------------------------------------------------------------------- E8 + E2


def phase_e8() -> dict:
    """The E8 sequence on bloomery, `-p bloomery-daemon`, in the pinned order."""
    step("E8: plain --no-run (records the plain artifact set)")
    pkg = ["-p", "bloomery-daemon"]
    out: dict = {"checks": {}, "builds": {}}

    p1 = run(["cargo", "test", *pkg, "--no-run", "-v"], BLOOMERY, "e8-plain1.log")
    out["builds"]["plain1"] = {"rc": p1["rc"], "wall": round(p1["wall"], 3),
                               "compiled": unit_sets(p1)[0], "fresh": unit_sets(p1)[1],
                               "log": p1["log"]}
    if p1["rc"] != 0:
        raise Refused(f"plain --no-run failed: {p1['err'][-2000:]}")
    expected_fresh = sorted(set(unit_sets(p1)[0]) | set(unit_sets(p1)[1]))
    out["expected_fresh_set"] = expected_fresh
    step(f"E8: plain #1 wall={p1['wall']:.2f}s compiled={unit_sets(p1)[0]} fresh={unit_sets(p1)[1]}")

    step("E8: instrumented --no-run #1 (the instrumented artifact set)")
    i1 = run(driver_cmd(*pkg, "--no-run", "-v"), BLOOMERY, "e8-instr1.log", timeout=7200)
    out["builds"]["instr1"] = {"rc": i1["rc"], "wall": round(i1["wall"], 3),
                               "compiled": unit_sets(i1)[0], "fresh": unit_sets(i1)[1],
                               "cargo_exit": cargo_exit_of(i1), "log": i1["log"]}
    if i1["rc"] != 0:
        raise Refused(f"instrumented --no-run failed: {i1['err'][-3000:]}")
    step(f"E8: instr #1 wall={i1['wall']:.2f}s compiled={unit_sets(i1)[0]}")

    # (a) a second instrumented --no-run compiles no workspace unit
    i2 = run(driver_cmd(*pkg, "--no-run", "-v"), BLOOMERY, "e8-instr2.log")
    c, f = unit_sets(i2)
    out["builds"]["instr2"] = {"rc": i2["rc"], "wall": round(i2["wall"], 3),
                               "compiled": c, "fresh": f, "log": i2["log"]}
    out["checks"]["a_second_instrumented_compiles_nothing"] = {
        "pass": i2["rc"] == 0 and c == [] and f == expected_fresh,
        "rc": i2["rc"], "compiled": c, "fresh": f, "expected_fresh": expected_fresh}
    step(f"E8(a): compiled={c} fresh={f} -> {out['checks']['a_second_instrumented_compiles_nothing']['pass']}")

    # (c) a plain --no-run after an instrumented build compiles no workspace unit
    p2 = run(["cargo", "test", *pkg, "--no-run", "-v"], BLOOMERY, "e8-plain2.log")
    c, f = unit_sets(p2)
    out["builds"]["plain2"] = {"rc": p2["rc"], "wall": round(p2["wall"], 3),
                               "compiled": c, "fresh": f, "log": p2["log"]}
    out["checks"]["c_plain_after_instrumented_compiles_nothing"] = {
        "pass": p2["rc"] == 0 and c == [] and f == expected_fresh,
        "rc": p2["rc"], "compiled": c, "fresh": f, "expected_fresh": expected_fresh}
    step(f"E8(c): compiled={c} fresh={f} -> {out['checks']['c_plain_after_instrumented_compiles_nothing']['pass']}")

    # (c) sentinel: the plain --lib binary must write no spool; the instrumented one must
    step("E8(c) sentinel: run both --lib binaries with SENSORIUM_SPOOL set")
    plain_exe = test_exe(pkg + ["--lib"], False, "bloomery_daemon")
    instr_exe = test_exe(pkg + ["--lib"], True, "bloomery_daemon")
    sent = {"plain_exe": plain_exe, "instrumented_exe": instr_exe}
    if not plain_exe or not instr_exe or plain_exe == instr_exe:
        sent["pass"] = False
        sent["why"] = "could not locate two distinct --lib test binaries"
    else:
        counts = {}
        for name, exe in (("plain", plain_exe), ("instrumented", instr_exe)):
            sp = LOGS / f"sentinel-spool-{name}"
            shutil.rmtree(sp, ignore_errors=True)
            sp.mkdir(parents=True)
            env = plain_env() | {"SENSORIUM_SPOOL": str(sp), "SENSORIUM_TIER": "call"}
            r = run([exe], BLOOMERY, f"e8-sentinel-{name}.log", env)
            counts[name] = len([q for q in sp.rglob("*") if q.is_file()])
            counts[name + "_rc"] = r["rc"]
            if name == "instrumented":
                sent["instrumented_spool_bytes"] = dir_bytes(sp)
            shutil.rmtree(sp, ignore_errors=True)
        sent.update(counts)
        sent["plain_exe_bytes"] = os.path.getsize(plain_exe)
        sent["instrumented_exe_bytes"] = os.path.getsize(instr_exe)
        sent["pass"] = counts["plain"] == 0 and counts["instrumented"] > 0
    out["checks"]["c_sentinel"] = sent
    step(f"E8(c) sentinel: {sent}")

    # (d) an instrumented --no-run after the plain one compiles no workspace unit
    i3 = run(driver_cmd(*pkg, "--no-run", "-v"), BLOOMERY, "e8-instr3.log")
    c, f = unit_sets(i3)
    out["builds"]["instr3"] = {"rc": i3["rc"], "wall": round(i3["wall"], 3),
                               "compiled": c, "fresh": f, "log": i3["log"]}
    out["checks"]["d_instrumented_after_plain_compiles_nothing"] = {
        "pass": i3["rc"] == 0 and c == [] and f == expected_fresh,
        "rc": i3["rc"], "compiled": c, "fresh": f, "expected_fresh": expected_fresh}
    step(f"E8(d): compiled={c} fresh={f} -> {out['checks']['d_instrumented_after_plain_compiles_nothing']['pass']}")

    # Fallbacks: the manifest flag AND the wrapper's stderr line, both.
    logs = [out["builds"][k]["log"] for k in out["builds"]]
    fell_lines = []
    for lg in logs:
        fell_lines += [ln for ln in Path(lg).read_text().splitlines()
                       if "fell back to the real tree" in ln]
    out["fell_back_stderr_lines"] = fell_lines
    return out


def read_manifests(paths) -> dict:
    """Distinct instrumented fn items across manifests with fell_back false."""
    sites, sites_src, raw, units, fell, unreached, skipped = set(), set(), 0, [], [], set(), []
    for p in sorted(paths):
        m = json.loads(Path(p).read_text())
        units.append({"unit": m["unit"], "crate_name": m["crate_name"],
                      "crate_type": m["crate_type"], "fell_back": m["fell_back"],
                      "files": len(m["files"]),
                      "sites": sum(len(v) for v in m["files"].values()),
                      "unreached_files": m.get("unreached_files", []),
                      "skipped": len(m.get("skipped", []))})
        unreached |= set(m.get("unreached_files", []))
        skipped += m.get("skipped", [])
        if m["fell_back"]:
            fell.append(m["unit"])
            continue
        for rel, entries in m["files"].items():
            raw += len(entries)
            for e in entries:
                key = (rel, e["qualname"], e["firstlineno"])
                sites.add(key)
                if "/src/" in rel or rel.endswith("/src"):
                    sites_src.add(key)
    return {"distinct": len(sites), "distinct_src": len(sites_src), "raw_site_total": raw,
            "units": units, "fell_back": fell, "unreached_files": sorted(unreached),
            "skipped": skipped}


def phase_e2(manifest_paths, label: str) -> dict:
    m = read_manifests(manifest_paths)
    step(f"E2[{label}]: distinct={m['distinct']} raw={m['raw_site_total']} "
         f"units={len(m['units'])} fell_back={len(m['fell_back'])} "
         f"unreached={len(m['unreached_files'])}")
    return m


# ------------------------------------------------------------------------ E1


def driver_fixed_overhead() -> dict:
    """The driver's own fixed cost: a no-op `--no-run` through it, against the
    same no-op straight to cargo. Three samples each, medians reported."""
    step("E1: driver fixed overhead (3 no-op builds each way)")
    pkg = ["-p", "bloomery-daemon", "--no-run"]
    plain, instr = [], []
    for i in range(3):
        plain.append(run(["cargo", "test", *pkg], BLOOMERY, f"overhead-plain-{i}.log")["wall"])
        instr.append(run(driver_cmd(*pkg, tier="off"), BLOOMERY, f"overhead-instr-{i}.log")["wall"])
    return {"plain_walls": [round(w, 3) for w in plain],
            "instrumented_walls": [round(w, 3) for w in instr],
            "plain_median": round(statistics.median(plain), 3),
            "instrumented_median": round(statistics.median(instr), 3),
            "overhead_s": round(statistics.median(instr) - statistics.median(plain), 3)}


def phase_e1() -> dict:
    arms = {"P": {"cmd": lambda: ["cargo", "test", "-p", "bloomery-daemon"], "tier": None},
            "O": {"cmd": lambda: driver_cmd("-p", "bloomery-daemon", tier="off"), "tier": "off"},
            "C": {"cmd": lambda: driver_cmd("-p", "bloomery-daemon", tier="call"), "tier": "call"}}
    runs: list[dict] = []
    kept_spool = None
    first = True
    for rnd in range(1, E1_ROUNDS + 1):
        for arm in ("P", "O", "C"):
            if not first:
                time.sleep(E1_SLEEP_S)
            first = False
            load, disk = loadavg(), free_gb()
            rec = {"round": rnd, "arm": arm, "load_1min": load, "free_gb": round(disk, 2)}
            if load > LOAD_CEILING:
                rec.update({"wall": None, "dropped": f"1-min load {load} > {LOAD_CEILING} at arm start"})
                runs.append(rec)
                step(f"E1 r{rnd} {arm}: DROPPED (load {load})")
                continue
            if disk < DISK_ABORT_GB:
                rec.update({"wall": None, "dropped": f"free disk {disk:.2f} GB < {DISK_ABORT_GB} GB"})
                runs.append(rec)
                step(f"E1 r{rnd} {arm}: DROPPED (disk {disk:.2f} GB)")
                continue
            res = run(arms[arm]["cmd"](), BLOOMERY, f"e1-r{rnd}-{arm}.log", timeout=7200)
            rec["rc"] = res["rc"]
            rec["cargo_exit"] = cargo_exit_of(res) if arm != "P" else res["rc"]
            sp = spool_of(res)
            if sp:
                rec["spool"] = sp
                rec["spool_bytes"] = dir_bytes(Path(sp))
                rec["spool_files"] = len([q for q in Path(sp).rglob("*") if q.is_file()])
            if res["rc"] != 0:
                rec.update({"wall": None,
                            "dropped": f"cargo exit {res['rc']} (infrastructure, not scored)"})
                step(f"E1 r{rnd} {arm}: DROPPED (rc={res['rc']})")
            else:
                rec["wall"] = round(res["wall"], 3)
                step(f"E1 r{rnd} {arm}: {res['wall']:.3f}s")
            # keep only the LAST call-arm spool; record and delete the rest
            if arm == "C" and sp:
                if kept_spool:
                    shutil.rmtree(kept_spool, ignore_errors=True)
                kept_spool = sp
            elif sp:
                shutil.rmtree(sp, ignore_errors=True)
            runs.append(rec)
    return {"runs": runs, "kept_spool": kept_spool}


def e1_summary(runs, arm) -> dict:
    walls = [r["wall"] for r in runs if r["arm"] == arm and r.get("wall") is not None]
    dropped = [f"round {r['round']}: {r['dropped']}" for r in runs
               if r["arm"] == arm and r.get("dropped")]
    if not walls:
        return {"median": None, "min": None, "max": None, "n": 0, "walls": [], "dropped": dropped}
    return {"median": round(statistics.median(walls), 3), "min": min(walls), "max": max(walls),
            "n": len(walls), "walls": walls, "dropped": dropped}


# ------------------------------------------------------------------------ E0


def convert(spool: str, label: str, cargo_exit: int, cargo_args: list) -> dict:
    env = plain_env() | {"SENSORIUM_DIR": str(SENSORIUM_DIR)}
    cmd = [str(VENV_PY), str(SPIKE / "convert.py"), spool, "--target", str(TARGET),
           "--cargo-exit", str(cargo_exit), "--argv", *cargo_args]
    t0 = time.monotonic()
    res = run(cmd, REPO, f"convert-{label}.log", env, timeout=7200)
    wall = time.monotonic() - t0
    procs = []
    for line in res["out"].splitlines():
        m = re.match(r"run: (\S+)\s+pid: (\d+)\s+exe: (\S*)\s+events: (\d+)\s+"
                     r"threads: (\d+)\s+spools_without_end: (\d+)", line)
        if m:
            rid = m.group(1)
            db = SENSORIUM_DIR / "traces" / f"{rid}.db"
            procs.append({"run": rid, "pid": int(m.group(2)), "exe": m.group(3),
                          "events": int(m.group(4)), "threads": int(m.group(5)),
                          "spools_without_end": int(m.group(6)),
                          "bytes": db.stat().st_size if db.exists() else None})
    return {"rc": res["rc"], "wall": round(wall, 3), "procs": procs,
            "stderr_tail": res["err"][-2000:], "log": res["log"],
            "spool_bytes": dir_bytes(Path(spool)),
            "events": sum(p["events"] for p in procs),
            "bytes": sum(p["bytes"] or 0 for p in procs),
            "spools_without_end": sum(p["spools_without_end"] for p in procs)}


def timed_cli(args, label: str, n=3) -> dict:
    """`/usr/bin/time -f %e` around a real `sensorium` command, n times."""
    env = plain_env() | {"SENSORIUM_DIR": str(SENSORIUM_DIR)}
    walls, outs = [], []
    for i in range(n):
        res = run(["/usr/bin/time", "-f", "%e", str(SENSORIUM), *args], REPO,
                  f"cli-{label}-{i}.log", env, timeout=3600)
        tail = res["err"].strip().splitlines()
        try:
            walls.append(float(tail[-1]))
        except (ValueError, IndexError):
            walls.append(None)
        outs.append(res["out"])
    good = [w for w in walls if w is not None]
    return {"walls": walls, "median": round(statistics.median(good), 3) if good else None,
            "n": len(good), "rc": res["rc"], "stdout_last": outs[-1]}


def phase_e0(kept_spool, e1_runs) -> dict:
    out: dict = {}
    disk = free_gb()
    if kept_spool and Path(kept_spool).is_dir() and disk < 4.0:
        out["whole_invocation"] = None
        out["whole_invocation_dropped"] = f"free disk {disk:.2f} GB < 4.0 GB guard"
        step(f"E0: whole-invocation conversion SKIPPED, disk {disk:.2f} GB")
        kept_spool = None
    if kept_spool and Path(kept_spool).is_dir():
        exit_code = next((r.get("cargo_exit", 0) for r in reversed(e1_runs)
                          if r["arm"] == "C" and r.get("spool") == kept_spool), 0)
        step("E0: converting the last E1 call-arm spool (whole invocation)")
        out["whole_invocation"] = convert(kept_spool, "e1-call-last", exit_code or 0,
                                          ["test", "-p", "bloomery-daemon"])
        w = out["whole_invocation"]
        step(f"E0: {len(w['procs'])} processes, {w['events']} events, "
             f"{w['bytes']} trace bytes, {w['spools_without_end']} spools_without_end")
    else:
        out["whole_invocation"] = None

    pairs = {}
    for label, extra in (("lib", ["--lib"]), ("config_test", ["--test", "config_test"])):
        runs = []
        for i in (1, 2):
            step(f"E0: tier-call run {i} of --{label}")
            res = run(driver_cmd("-p", "bloomery-daemon", *extra, tier="call"),
                      BLOOMERY, f"e0-{label}-run{i}.log", timeout=7200)
            sp = spool_of(res)
            ce = cargo_exit_of(res)
            conv = convert(sp, f"{label}-{i}", ce if ce is not None else res["rc"],
                           ["test", "-p", "bloomery-daemon", *extra]) if sp else None
            runs.append({"rc": res["rc"], "cargo_exit": ce, "wall": round(res["wall"], 3),
                         "spool": sp, "convert": conv})
        pairs[label] = {"runs": runs}
        # the trace of the test binary itself: the process with the most events
        picks = []
        for r in runs:
            if not r["convert"] or not r["convert"]["procs"]:
                picks.append(None)
                continue
            picks.append(max(r["convert"]["procs"], key=lambda p: p["events"]))
        pairs[label]["picked"] = picks
        if picks[0] and runs[0]["spool"]:
            pairs[label]["thread_names"] = thread_names(runs[0]["spool"], picks[0]["pid"])
        if all(picks):
            a, b = picks[0]["run"], picks[1]["run"]
            step(f"E0: timing `sensorium info` and `diff` on {label} ({a}, {b})")
            pairs[label]["info"] = timed_cli(["info", a], f"info-{label}")
            pairs[label]["diff"] = timed_cli(["diff", a, b], f"diff-{label}")
            step(f"E0: {label} info median={pairs[label]['info']['median']}s "
                 f"diff median={pairs[label]['diff']['median']}s")
    out["pairs"] = pairs
    return out


# ------------------------------------------------------------- E7 and bench


def phase_e7() -> dict:
    step("E7: mechanics.sh on the probe workspace")
    res = run(["bash", str(SPIKE / "tests" / "mechanics.sh")], REPO, "e7-mechanics.log",
              timeout=3600)
    body = res["out"] + res["err"]
    ok = re.findall(r"^ok: (\S+)$", body, re.M)
    bad = re.findall(r"^FAIL: (.+)$", body, re.M)
    # The contiguous E7 REGION, not just the lines that name E7: the masked
    # plain-vs-instrumented output between them is the evidence, and a filter
    # that keeps only the headline lines throws it away.
    lines = body.splitlines()
    marks = [i for i, ln in enumerate(lines)
             if ln.startswith(("ok: e7", "FAIL: e7")) or "[E7]" in ln]
    e7_lines = lines[marks[0]:marks[-1] + 1] if marks else []
    step(f"E7: {len(ok)} ok, {len(bad)} FAIL, rc={res['rc']}")
    return {"rc": res["rc"], "ok": ok, "fail": bad, "e7_lines": e7_lines, "log": res["log"]}


def phase_bench() -> dict:
    step("micro-bench: building both caller profiles")
    run(["cargo", "build"], SPIKE, "bench-build-dev.log")
    run(["cargo", "build", "--release"], SPIKE, "bench-build-release.log")
    step("micro-bench: running")
    res = run(["cargo", "run", "--release", "--bin", "microbench"], SPIKE, "bench-run.log",
              timeout=7200)
    lines = [ln for ln in (res["out"] + res["err"]).splitlines()
             if ln.startswith(("run ", "result ", "bench ", "#"))]
    results = {}
    for ln in lines:
        m = re.match(r"result caller=(\S+) arm=(\S+) metric=(\S+) value=([\d.]+)", ln)
        if m:
            results.setdefault(m.group(1), {}).setdefault(m.group(2), {})[m.group(3)] = float(m.group(4))
    step(f"micro-bench: {len(results)} lenses")
    return {"rc": res["rc"], "lines": lines, "results": results, "log": res["log"]}


# ----------------------------------------------------------------- cleanup


def cleanup(pins) -> dict:
    step("cleanup")
    sens = TARGET / "sensorium"
    bytes_before = dir_bytes(sens) if sens.is_dir() else 0
    shutil.rmtree(sens, ignore_errors=True)
    porcelain = subprocess.run(["git", "-C", str(BLOOMERY), "status", "--porcelain"],
                               capture_output=True, text=True).stdout
    lock = subprocess.run(["sha256sum", str(BLOOMERY / "Cargo.lock")],
                          capture_output=True, text=True).stdout.split()[0]
    for p in LOGS.glob("sentinel-spool-*"):
        shutil.rmtree(p, ignore_errors=True)
    return {"target_sensorium_removed_bytes": bytes_before,
            "target_sensorium_exists_after": sens.exists(),
            "bloomery_status_porcelain_after": porcelain,
            "cargo_lock_sha256_after": lock,
            "cargo_lock_unchanged": lock == pins["cargo_lock_sha256_before"],
            "free_gb_after": round(free_gb(), 2),
            "sensorium_dir_bytes": dir_bytes(SENSORIUM_DIR) if SENSORIUM_DIR.is_dir() else 0}




# --------------------------------------------------------------------- main


def assemble(raw: dict, which: str) -> dict:
    """Delegated to `results_schema` (kept separate for the 800-line ceiling)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import results_schema
    return results_schema.assemble(raw, which)


def main() -> int:
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "measure.DONE").unlink(missing_ok=True)
    SENSORIUM_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"schema": "every measurement is {value, n, lens, dropped}; "
                               "value null + a dropped reason is the ONLY not-measured; "
                               "0 is measured-and-zero",
                     "spike": "docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md"}
    rc = 0
    try:
        pins = preflight()
        results["pins"] = pins

        e8 = phase_e8()
        results["raw_e8"] = e8
        manifests_daemon = sorted((TARGET / "sensorium" / "manifests").glob("*.json"))
        results["raw_e2"] = phase_e2(manifests_daemon, "daemon build")

        results["raw_overhead"] = driver_fixed_overhead()

        e1 = phase_e1()
        results["raw_e1"] = e1

        results["raw_e0"] = phase_e0(e1["kept_spool"], e1["runs"])

        results["raw_e7"] = phase_e7()
        results["raw_bench"] = phase_bench()

        # Supplementary E2 lens: a workspace-wide instrumented --no-run, so the
        # numerator can be read against the pre-registered whole-workspace
        # denominator on comparable terms. Declared and disk-guarded BEFORE any
        # E2 number was read; it adds no timed arm and moves no threshold.
        disk = free_gb()
        if disk < 4.0:
            results["raw_e2_workspace"] = {"dropped": f"free disk {disk:.2f} GB < 4.0 GB guard"}
            step(f"E2(workspace): SKIPPED, disk {disk:.2f} GB")
        else:
            step("E2(workspace): instrumented `--workspace --no-run`")
            before = set(str(p) for p in (TARGET / "sensorium" / "manifests").glob("*.json"))
            w = run(driver_cmd("--workspace", "--no-run", "-v"), BLOOMERY,
                    "e2-workspace.log", timeout=7200)
            allm = sorted((TARGET / "sensorium" / "manifests").glob("*.json"))
            results["raw_e2_workspace"] = {
                "rc": w["rc"], "wall": round(w["wall"], 3), "log": w["log"],
                "new_manifests": len(allm) - len(before),
                "compiled": unit_sets(w)[0], "fresh": unit_sets(w)[1],
                **(phase_e2(allm, "workspace build") if w["rc"] == 0 else
                   {"dropped": f"cargo exit {w['rc']}"})}

        results["cleanup"] = cleanup(pins)
    except Refused as e:
        step(f"REFUSED: {e}")
        results["refused"] = str(e)
        rc = 3
    except Exception as e:                                  # noqa: BLE001
        import traceback
        step(f"ERROR: {e}")
        results["error"] = traceback.format_exc()
        rc = 4
    results["steps"] = STEPS
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (LEDGER / "results-raw.json").write_text(json.dumps(results, indent=2, sort_keys=False))
    if rc == 0:
        try:
            which = os.environ.get("SENSORIUM_E2_DENOM", "all")
            (LEDGER / "results.json").write_text(
                json.dumps(assemble(results, which), indent=2, sort_keys=False))
        except Exception:                                   # noqa: BLE001
            import traceback
            (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
            step("assemble FAILED (see logs/assemble-error.txt); results-raw.json is intact")
    (LOGS / "measure.DONE").write_text(f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n")
    step(f"done rc={rc}; raw results at {LEDGER / 'results-raw.json'}")
    return rc


if __name__ == "__main__":
    if "--assemble" in sys.argv:
        _raw = json.loads((LEDGER / "results-raw.json").read_text())
        _which = os.environ.get("SENSORIUM_E2_DENOM", "all")
        (LEDGER / "results.json").write_text(
            json.dumps(assemble(_raw, _which), indent=2, sort_keys=False))
        print(f"assembled {LEDGER / 'results.json'} (E2 denominator: {_which})")
        raise SystemExit(0)
    raise SystemExit(main())
