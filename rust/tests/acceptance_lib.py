"""Plumbing for the rung-2 acceptance run: paths, process running, and the
readers every phase shares.

No box path appears here. Every location is an environment variable, named
once in `env_paths()`, and a run that does not set one refuses in the
preflight rather than measuring something else:

    SENSORIUM_BLOOMERY_CLONE   the workspace under measurement (the CLONE;
                               never `~/workspace/bloomery`)
    SENSORIUM_ACCEPTANCE_TARGET  its CARGO_TARGET_DIR
    SENSORIUM_DIR              where converted traces land
    SENSORIUM_DRIVER           the release `cargo-sensorium`, by absolute path
    SENSORIUM_CENSUS_DRIVER    a binary that prints one JSON census row per
                               `.rs` file under `<root>/crates/*/{src,tests}`
    SENSORIUM_PROBE_TARGET     the probe workspace's target (E7(a))
    SENSORIUM_SOURCE_BLOOMERY  optional: the read-only source tree, asserted
                               unchanged before and after

The measurement shape is the pre-registered one: every number is
`{"value", "n", "lens", "dropped"}`, a `null` value with a non-empty
`dropped` list is the ONLY representation of not-measured, and `0` is
measured-and-zero.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import struct
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = (REPO / ".superpowers" / "sdd"
          / "2026-09-02-sensorium-rung2-recorder-v1" / "acceptance")
LOGS = LEDGER / "logs"

CLONE_PIN = "e209ed9b00f7eef647fb31d0b0895a5ad3b90807"
LOAD_CEILING = 4.0          # an arm is DROPPED above this, never re-rolled
TARGET_DISK_FLOOR_GB = 8.0  # the artifact disk
REPO_DISK_FLOOR_GB = 3.0    # the root disk
E3_RUNS = 20
WALL_ROUNDS = 5
COOLDOWN_S = 10

STEPS: list[str] = []


class Refused(Exception):
    """A preflight or invariant the runner refuses to proceed past."""


def meas(value, n, lens, dropped=None) -> dict:
    """The pre-registered measurement shape."""
    return {"value": value, "n": n, "lens": lens, "dropped": list(dropped or [])}


def step(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    STEPS.append(line)
    print(line, flush=True)


# ------------------------------------------------------------------- paths


def env_paths(dry_run: bool) -> dict:
    """Every location this run touches, from the environment. Missing
    variables are collected and refused together, so one launch reports all
    of them rather than one per attempt."""
    wanted = ["SENSORIUM_BLOOMERY_CLONE", "SENSORIUM_ACCEPTANCE_TARGET",
              "SENSORIUM_DIR", "SENSORIUM_DRIVER", "SENSORIUM_CENSUS_DRIVER",
              "SENSORIUM_PROBE_TARGET"]
    missing = [k for k in wanted if not os.environ.get(k)]
    if missing:
        raise Refused("unset environment variable(s): " + ", ".join(missing))
    p = {k.lower(): Path(os.environ[k]) for k in wanted}
    src = os.environ.get("SENSORIUM_SOURCE_BLOOMERY")
    p["source_bloomery"] = Path(src) if src else None
    p["dry_run"] = dry_run
    return p


def free_gb(path: Path) -> float:
    st = os.statvfs(path)
    return st.f_bavail * st.f_frsize / 1e9


def loadavg() -> float:
    return float(Path("/proc/loadavg").read_text().split()[0])


def sha256_file(path) -> str | None:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


# ---------------------------------------------------------------- processes


def plain_env() -> dict:
    """The environment for an UNINSTRUMENTED arm: no recorder variable at
    all, and no inherited target directory to surprise a build."""
    return {k: v for k, v in os.environ.items()
            if not k.startswith("SENSORIUM_")
            and k not in ("RUSTC_WORKSPACE_WRAPPER", "RUSTDOCFLAGS",
                          "CARGO_TARGET_DIR")}


def target_env(paths: dict, extra: dict | None = None) -> dict:
    env = plain_env()
    env["CARGO_TARGET_DIR"] = str(paths["sensorium_acceptance_target"])
    env["SENSORIUM_DIR"] = str(paths["sensorium_dir"])
    env.update(extra or {})
    return env


def run(cmd, cwd, log_name, env=None, timeout=7200) -> dict:
    """Run `cmd`, tee its combined output to `LOGS/<log_name>`, return a dict.
    The log is the evidence; nothing here summarises it away."""
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / log_name
    t0 = time.monotonic()
    p = subprocess.run([str(c) for c in cmd], cwd=str(cwd),
                       env=plain_env() if env is None else env,
                       capture_output=True, text=True, timeout=timeout)
    wall = time.monotonic() - t0
    log.write_text(
        f"$ {' '.join(str(c) for c in cmd)}\n(cwd={cwd})\n"
        f"--- stdout ---\n{p.stdout}\n--- stderr ---\n{p.stderr}\n"
        f"--- rc={p.returncode} wall={wall:.3f} ---\n")
    return {"rc": p.returncode, "out": p.stdout, "err": p.stderr,
            "wall": wall, "log": str(log)}


def driver_cmd(paths: dict, *args, tier=None) -> list:
    cmd = [str(paths["sensorium_driver"]), "sensorium", "test"]
    if tier:
        cmd += ["--tier", tier]
    return cmd + list(args)


def git(paths: dict, *args) -> str:
    return subprocess.run(["git", "-C", str(paths["sensorium_bloomery_clone"]),
                           *args], capture_output=True, text=True).stdout


def spool_of(res) -> str | None:
    m = re.findall(r"^spool: (.+)$", res["err"], re.M)
    return m[-1] if m else None


def cargo_exit_of(res):
    m = re.findall(r"^cargo exit: (-?\d+)$", res["err"], re.M)
    return int(m[-1]) if m else None


RUN_LINE = re.compile(r"^run: (\S+)\s+pid: (\d+)\s+exe: (\S*)\s+events: (\d+)\s+"
                      r"threads: (\d+)\s+exit: (\S+)")


def run_lines(res) -> list[dict]:
    """Every `run:` line the converter printed, in order."""
    out = []
    for line in res["out"].splitlines():
        m = RUN_LINE.match(line)
        if m:
            out.append({"run": m.group(1), "pid": int(m.group(2)),
                        "exe": m.group(3), "events": int(m.group(4)),
                        "threads": int(m.group(5)), "exit": m.group(6)})
    return out


def unit_sets(res, packages) -> tuple[list[str], list[str]]:
    """Workspace packages cargo said it Compiled / found Fresh, from `-v`."""
    both = res["out"] + res["err"]
    pat = r"^\s*(Compiling|Fresh) (%s) " % "|".join(re.escape(p) for p in packages)
    comp, fresh = set(), set()
    for verb, pkg in re.findall(pat, both, re.M):
        (comp if verb == "Compiling" else fresh).add(pkg)
    return sorted(comp), sorted(fresh)


def metadata_set(res) -> list[str]:
    """The `-C metadata=` values of every rustc invocation in a `cargo -v`
    log: this build's OWN unit set. Complete only on a from-scratch target —
    cargo does not invoke the wrapper for a fingerprint-fresh unit — which is
    why every measured build here runs against an emptied target."""
    both = res["out"] + res["err"]
    return sorted(set(re.findall(r"-C metadata=([0-9a-zA-Z_]+)", both)))


def workspace_packages(root: Path) -> list[str]:
    """Every package name in the workspace, read from the crate manifests."""
    names = []
    for toml in sorted(root.glob("crates/*/Cargo.toml")):
        m = re.search(r'^name\s*=\s*"([^"]+)"', toml.read_text(), re.M)
        if m:
            names.append(m.group(1))
    if not names:
        for toml in sorted(root.glob("*/Cargo.toml")):
            m = re.search(r'^name\s*=\s*"([^"]+)"', toml.read_text(), re.M)
            if m:
                names.append(m.group(1))
    return sorted(names)


# ---------------------------------------------------------------- manifests


def manifests_dir(paths: dict) -> Path:
    return paths["sensorium_acceptance_target"] / "sensorium" / "manifests"


def read_manifests(paths: dict, scope: list[str] | None) -> dict:
    """Every manifest of ONE build, scoped to that build's own unit set.

    `scope` is the `-C metadata=` values from the build's `cargo -v` log; a
    manifest whose filename is not in it belongs to another build (a
    different tool hash leaves its manifests behind) and is counted as
    `out_of_scope` rather than folded into the numerator."""
    d = manifests_dir(paths)
    sites, sites_by_file, raw = set(), {}, 0
    units, fell, unreached, skipped = [], [], set(), []
    spawns_wrapped, spawns_declared = 0, []
    out_of_scope, declaring = [], set()
    hashed_files = 0
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        metadata = p.stem
        if scope is not None and metadata not in scope:
            out_of_scope.append(metadata)
            continue
        m = json.loads(p.read_text())
        units.append({"unit": m["unit"], "crate_name": m["crate_name"],
                      "crate_type": m["crate_type"], "fell_back": m["fell_back"],
                      "fallback_reason": m.get("fallback_reason"),
                      "files": len(m["files"]),
                      "sites": sum(len(v) for v in m["files"].values()),
                      "unreached_files": m.get("unreached_files", []),
                      "workspace_root": m.get("workspace_root", ""),
                      "source_hashes": len(m.get("source_hashes", {})),
                      "skipped": len(m.get("skipped", []))})
        declaring.add((m["crate_name"], m["crate_type"]))
        unreached |= set(m.get("unreached_files", []))
        skipped += m.get("skipped", [])
        hashed_files += len(m.get("source_hashes", {}))
        for s in m.get("spawns", []):
            if s.get("wrapped"):
                spawns_wrapped += 1
            else:
                spawns_declared.append(s)
        if m["fell_back"]:
            fell.append({"unit": m["unit"], "reason": m.get("fallback_reason")})
            continue
        for rel, entries in m["files"].items():
            raw += len(entries)
            for e in entries:
                sites.add((rel, e["qualname"], e["firstlineno"]))
                sites_by_file.setdefault(rel, set()).add(
                    (e["qualname"], e["firstlineno"]))
    return {"distinct": len(sites),
            "sites_by_file": {k: len(v) for k, v in sites_by_file.items()},
            "raw_site_total": raw, "units": units, "fell_back": fell,
            "unreached_files": sorted(unreached), "skipped": skipped,
            "spawns_wrapped": spawns_wrapped, "spawns_declared": spawns_declared,
            "out_of_scope_manifests": sorted(out_of_scope),
            "declaring_pairs": sorted(declaring),
            "source_hashed_files": hashed_files}


def mirror_identity(paths: dict, units: list[dict]) -> dict:
    """Every unit's mirror crate root must name that unit's own metadata.
    Counts what it checked and reports the count: a check that examined
    nothing proves nothing (`checked > 0`)."""
    mirror = paths["sensorium_acceptance_target"] / "sensorium" / "mirror"
    checked, wrong, no_mirror = 0, [], []
    for u in units:
        d = mirror / u["unit"]
        if not d.is_dir():
            no_mirror.append(u["unit"])
            continue
        found = False
        for f in d.rglob("*.rs"):
            try:
                text = f.read_text(errors="replace")
            except OSError:
                continue
            # The DEFINITION, not a reference: every instrumented file names
            # `crate::__SENSORIUM_UNIT` in its guards, and only the crate root
            # declares the static. Matching the reference would flag every
            # ordinary file as "wrong" (measured in the dry run).
            if "static __SENSORIUM_UNIT" not in text:
                continue
            found = True
            if f'Unit::new("{u["unit"]}")' not in text:
                wrong.append(f'{u["unit"]}: {f.name}')
        if found:
            checked += 1
        else:
            no_mirror.append(u["unit"] + " (no crate root static)")
    return {"checked": checked, "wrong": wrong, "without_mirror": no_mirror,
            "units": len(units)}


# ------------------------------------------------------------------- spools


HEADER_FIXED = 28
RECORD_FIXED = 24
KIND_UNWRITTEN = 0
KIND_THREAD_END = 255


def parse_spool(path: Path) -> dict:
    """The spool wire format, read the way the converter reads it, so the
    MAP_SHARED claim can be checked from outside the converter: a thread that
    was still running at process exit must still leave a COMPLETE last
    record, not a torn one."""
    b = path.read_bytes()
    if len(b) < HEADER_FIXED or b[:4] != b"SNSR":
        return {"file": path.name, "parsed": False, "why": "short or bad magic"}
    name_len = struct.unpack_from("<H", b, 6)[0]
    serial = struct.unpack_from("<I", b, 8)[0]
    dropped = struct.unpack_from("<Q", b, 12)[0]
    truncated = struct.unpack_from("<Q", b, 20)[0]
    head = HEADER_FIXED + name_len
    name = b[HEADER_FIXED:head].decode("utf-8", "replace")
    i, records, ended, torn = head, 0, False, False
    while i + RECORD_FIXED <= len(b):
        kind = b[i + 20]
        payload_len = struct.unpack_from("<H", b, i + 22)[0]
        if kind == KIND_UNWRITTEN:
            break
        if i + RECORD_FIXED + payload_len > len(b):
            torn = True
            break
        records += 1
        if kind == KIND_THREAD_END:
            ended = True
        i += RECORD_FIXED + payload_len
    return {"file": path.name, "parsed": True, "serial": serial, "name": name,
            "records_dropped": dropped, "truncated": truncated,
            "records": records, "thread_end": ended, "torn_last_record": torn}


# ------------------------------------------------------------------- traces


def trace_meta(paths: dict, run_id: str) -> dict:
    """One trace's whole meta table, JSON-decoded."""
    db = paths["sensorium_dir"] / "traces" / f"{run_id}.db"
    if not db.is_file():
        return {}
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = dict(con.execute("select key, value from meta"))
    finally:
        con.close()
    out = {}
    for k, v in rows.items():
        try:
            out[k] = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            out[k] = v
    return out


def trace_bytes(paths: dict, run_id: str) -> int:
    db = paths["sensorium_dir"] / "traces" / f"{run_id}.db"
    return db.stat().st_size if db.is_file() else 0


def sensorium_cli(paths: dict, args, label: str, timeout=3600) -> dict:
    """The Python reader, from the repo's own venv."""
    env = plain_env() | {"SENSORIUM_DIR": str(paths["sensorium_dir"])}
    return run([str(REPO / ".venv" / "bin" / "python"), "-m", "sensorium", *args],
               REPO, f"cli-{label}.log", env, timeout)


def rmtree(p: Path) -> int:
    """Remove `p`, returning the bytes it held (0 when it did not exist)."""
    if not p.exists():
        return 0
    n = dir_bytes(p) if p.is_dir() else p.stat().st_size
    shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink()
    return n
