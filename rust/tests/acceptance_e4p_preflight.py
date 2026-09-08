#!/usr/bin/env python3
"""E4′'s preflight and cleanup: what the run touches, and what it left.

Split out of `acceptance_e4p.py` when that file crossed this project's
800-line ceiling. Everything here runs BEFORE the first number is read or
AFTER the last, which is also the line §1.4's kill rules 4 and 5 are drawn
along: a refusal raised by anything in the preflight is the INFRASTRUCTURE
kill -- the run is archived, the fresh locations emptied, the 61 copies
re-made and it is relaunched from zero -- because nothing has been measured
yet.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4p_read import trace_meta_ro                      # noqa: E402
from acceptance_e4p_store import census_diff, sqlite3_cli, store_census  # noqa: E402,E501
from acceptance_e6ppp import logs_at                                # noqa: E402
from acceptance_lib import (CLONE_PIN, LOAD_CEILING,                # noqa: E402
                            REPO_DISK_FLOOR_GB, TARGET_DISK_FLOOR_GB,
                            REPO, Refused, dir_bytes, free_gb, loadavg,
                            plain_env, sha256_file, step)

#: Set by the runner to its own ledger, as every module of this family is.
LOGS: Path | None = None

#: §1.4's ceiling for the driver build. The loop's own ceilings live in the
#: runner, which is what applies them.
CARGO_TIMEOUT = 1800


def out(*args) -> str:
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True).stdout.strip()


def out_err(*args) -> dict:
    """A child's rc, its stdout AND its stderr.

    `out()` above captures stdout alone, which is E4′ §5's gap 2: a probe
    that raised put its traceback on stderr and an EMPTY STRING in the
    lens, where a reader saw a measured token. Anything whose failure has
    to be readable goes through this instead.
    """
    res = subprocess.run([str(a) for a in args], capture_output=True,
                         text=True)
    return {"command": " ".join(str(a) for a in args),
            "rc": res.returncode,
            "out": (res.stdout or "").strip(),
            "err": (res.stderr or "").strip()}


def _probe(python, code: str, source: str) -> dict:
    """One version token, or `null` WITH the reason it is not there.

    Never `""`. A blank is the one answer a reader cannot tell from a
    measured one, and it is what E4′ published: `{"token": None, "reason":
    "<the interpreter's own last line>"}` is the same fact said honestly.
    A probe that exits 0 and prints nothing is not-measured too -- rc alone
    does not make a token.
    """
    res = out_err(str(python), "-c", code)
    token = res["out"].splitlines()[-1].strip() if res["out"] else ""
    rec = {"source": source, "command": res["command"], "rc": res["rc"],
           "stderr": res["err"] or None, "token": None, "reason": None}
    if res["rc"] == 0 and token:
        rec["token"] = token
        return rec
    rec["reason"] = (
        res["err"].splitlines()[-1].strip() if res["err"]
        else f"the probe exited {res['rc']} and printed nothing")
    return rec


def version_probe(python, dist: str = "sensorium") -> dict:
    """The INSTALLED distribution's version, from `importlib.metadata`."""
    return _probe(python,
                  f"import importlib.metadata as m; print(m.version({dist!r}))",
                  f"importlib.metadata.version({dist!r})")


def attribute_probe(python, module: str = "sensorium") -> dict:
    """The TREE's own token, from the module attribute.

    `sensorium` carries no `__version__`, so this probe fails on this box
    and records the `AttributeError` -- which is the gap-2 fix working, not
    a fault: a probe that cannot answer says so.
    """
    return _probe(python, f"import {module}; print({module}.__version__)",
                  f"{module}.__version__")


def clone_git(paths, *args) -> str:
    return out("git", "-C", str(paths["sensorium_bloomery"]), *args)


def cargo_running() -> dict:
    """Refuse while any `cargo` is on this box, and RECORD the check.

    This run builds the driver, rebuilds 61 units into a fresh target and
    finally runs `cargo test --workspace` in this repository's own. A
    second cargo sharing the machine moves every wall the record reports
    and can hold a lock the build needs -- and §1.4 gates nothing on a
    wall, but it publishes them, and a wall measured beside somebody else's
    build is not the wall it says it is.

    `pgrep -x`: the EXACT process name. Never `-f`, whose pattern is
    matched against the whole command line and would find this runner's own
    argv -- the self-match that has cost this project two sixteen-core
    afternoons one tool along.

    Recorded either way. "No cargo was running" is a lens fact of the run,
    and a check whose passing leaves no trace cannot be audited afterwards.
    """
    res = subprocess.run(["pgrep", "-x", "cargo"], capture_output=True,
                         text=True)
    pids = [x for x in (res.stdout or "").split() if x.strip()]
    rec = {"command": "pgrep -x cargo", "rc": res.returncode,
           "pids": pids, "running": bool(pids)}
    if pids:
        raise Refused(
            f"{len(pids)} `cargo` process(es) are already running on this "
            f"box (pids {', '.join(pids)}): this run builds the driver, "
            "rebuilds 61 units into a fresh target and runs `cargo test "
            "--workspace`, and every wall it publishes would be measured "
            "beside somebody else's build. Wait for them, or kill them by "
            "process group -- never `pkill -f`")
    step(f"no cargo is running ({rec['command']} -> rc {rec['rc']})")
    return rec


def mark_numbers_read(res: dict, raw_path: Path, because: str) -> None:
    """Flip `numbers_read` and FLUSH the raw record, once.

    §1.4's rules 4 and 5 turn on exactly one question -- had any number been
    read when the `.FAILED` was written? -- and the answer decides between
    relaunching from zero (with the 61 copies re-made) and stopping with
    the numbers already read standing. Inferring it afterwards from which
    `raw_*` blocks exist is a judgement; this is a field.

    Flushed AT THIS MOMENT, not at the end: a run that dies between the
    first reading and the marker must still leave a raw record that says a
    number was read, or the rule cannot be applied to it at all.

    Marked at the FIRST reading -- the first refocus that came back with a
    verdict or a licence -- rather than at the first H endpoint. Everything
    after that point is a measurement of one of the 61, and §1.4's kill 6
    ("measured once. No endpoint is re-rolled") forbids relaunching from
    zero over rows that have already been read. The reason is recorded, so
    which reading it was is a fact rather than an assumption.
    """
    if res.get("numbers_read"):
        return
    res["numbers_read"] = True
    res["numbers_read_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    res["numbers_read_because"] = because
    try:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(res, indent=2, default=str))
    except (TypeError, ValueError, OSError):
        # The flush is belt and braces over the marker; a raw record that
        # cannot be written yet is written again at the end, and losing
        # this early copy must not take the run down.
        step("could not flush the raw record at the first number; the flag "
             "is set and will be written with the record at the end")
    step(f"numbers_read = True ({because})")


# ------------------------------------------------------------ lock and paths

def build_driver(paths) -> dict:
    """`cargo build -p cargo-sensorium`, run BY the runner (§1.3).

    The profile is read from the binary's own parent directory, so the build
    lands exactly where `SENSORIUM_DRIVER` points instead of refreshing the
    other profile and reporting `rebuilt: False` about a stale binary. The
    pre-repair-binary trap of the E6⁗ record is why §1.3 makes the runner
    build the driver rather than trust a path.
    """
    driver = Path(paths["sensorium_driver"])
    profile = driver.parent.name
    if profile not in ("debug", "release"):
        raise Refused(
            f"SENSORIUM_DRIVER {driver} is not under a cargo profile "
            f"directory (its parent is {profile!r}), so the runner cannot "
            "rebuild it from HEAD as §1.3 requires")
    from acceptance_e4p_phases import guarded
    target = driver.parents[1]
    before = sha256_file(driver)
    cmd = ["cargo", "build", "-p", "cargo-sensorium"]
    if profile == "release":
        cmd.insert(2, "--release")
    with logs_at(LOGS / "built-from"):
        res = guarded(cmd, REPO / "rust", "built-from.log",
                      plain_env() | {"CARGO_TARGET_DIR": str(target)},
                      CARGO_TIMEOUT, "built-from")
    after = sha256_file(driver)
    rec = {
        "repo_head_at_build": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_porcelain_at_build": out("git", "-C", str(REPO), "status",
                                       "--porcelain"),
        "command": " ".join(cmd), "profile": profile,
        "cargo_target_dir": str(target), "cargo_rc": res["rc"],
        "cargo_wall_s": round(res["wall"], 3), "timed_out": res["timed_out"],
        "driver": str(driver), "driver_sha256_before_build": before,
        "driver_sha256_after_build": after, "rebuilt": before != after,
        "log": res["log"],
    }
    if res["timed_out"]:
        raise Refused(f"`{' '.join(cmd)}` was KILLED at {CARGO_TIMEOUT} s: "
                      "the driver cannot be shown to be this HEAD's")
    if res["rc"] != 0:
        raise Refused(f"`{' '.join(cmd)}` exited {res['rc']}: the driver is "
                      "not this HEAD's")
    if after is None:
        raise Refused(f"the build succeeded but no binary is at {driver}")
    step(f"built_from: HEAD {rec['repo_head_at_build'][:12]} rc 0 in "
         f"{rec['cargo_wall_s']}s; driver {after[:12]} "
         f"rebuilt={rec['rebuilt']}")
    return rec


def transform_version() -> dict:
    """`sensorium-transform`'s version, and WHERE it was read.

    §1.4 requires every version token inside a sentence this record checks
    to be read from the trace's own meta. The transform's version is not in
    the trace and not in the driver's `--version`, so it is taken from
    `rust/Cargo.lock` and LABELLED with that source. Presenting it beside
    the driver's token as though both were observed from the run is exactly
    the mixing §1.4 forbids.
    """
    lock = REPO / "rust" / "Cargo.lock"
    value, name = None, "sensorium-transform"
    if lock.is_file():
        block = None
        for line in lock.read_text().splitlines():
            if line.strip() == "[[package]]":
                block = {}
            elif block is not None and line.startswith("name = "):
                block["name"] = line.split("=", 1)[1].strip().strip('"')
            elif block is not None and line.startswith("version = "):
                block["version"] = line.split("=", 1)[1].strip().strip('"')
                if block.get("name") == name:
                    value = block["version"]
                    break
    return {"value": value, "source": "Cargo.lock",
            "path": str(lock.relative_to(REPO)),
            "note": ("NOT observed from the run: the transform's version is "
                     "not carried in the trace or by the driver binary, so "
                     "it is read from the lockfile and labelled as such")}


# ------------------------------------------------------------- the preflight

#: Keys the parity guard does NOT compare, and why each is out.
#:
#: `^(CARGO|RUST|SENSORIUM|LD_)` differ BY DESIGN and are judged one check
#: along, not here: §1.4 gives the re-run a FRESH `CARGO_TARGET_DIR`, so
#: every variable cargo derives from the root moves with it (`CARGO_*`,
#: `RUSTDOCFLAGS`, `LD_LIBRARY_PATH`), the recorder mints `SENSORIUM_*` and
#: `RUSTC_WORKSPACE_WRAPPER` per invocation, and `refocus_env` is what
#: decides whether the movement is a relocation or a change. A guard that
#: compared them would refuse every launch it exists to protect.
EXCLUDED_ENV = re.compile(r"^(CARGO|RUST|SENSORIUM|LD_)")

#: The shell's own bookkeeping, `refocus_world._UNCOMPARED_ENV`'s names and
#: its reasons: `PWD` names the calling shell and `os.chdir` does not update
#: it, `_` is bash's last argument, and neither says anything about the
#: world the program ran in.
UNCOMPARED_ENV = frozenset({"_", "OLDPWD", "PWD", "SHLVL"})


def env_parity(kept: Path, rows, environ=None) -> dict:
    """Refuse unless THIS process's environment is the one the 61 originals
    were recorded under.

    The licence compares the environment the original executed under with
    the one the re-run did, and both are the recording process's own. Task
    5b taught that check to read a relocated target root as the same world,
    which covers the difference §1.4 introduces ON PURPOSE. It does not
    cover a difference between the shell E4 was launched from and the shell
    this run is launched from -- and a scan of the 61 found three:
    `PYTHONDONTWRITEBYTECODE`, `SSL_CERT_DIR`, `SSL_CERT_FILE`.

    The launcher pins all three. This is what makes the pinning MECHANICAL
    rather than a line on a checklist, and it runs before a single copy is
    made and long before a number is read -- so a refusal here is §1.4's
    INFRASTRUCTURE kill by its words, and costs nothing but the launch.

    A key is a difference whether its VALUE moved, it is missing from this
    process, or this process added it: the licence compares a SET, and a
    subset check would pass a shell carrying a variable E4's did not.

    EVERY offending key and the originals that carry it are named in ONE
    refusal. A refusal that named the first would cost one detached launch
    per key to discover the rest.
    """
    environ = dict(os.environ if environ is None else environ)
    mine = {k: v for k, v in environ.items()
            if not EXCLUDED_ENV.match(k) and k not in UNCOMPARED_ENV}
    differing, unreadable, compared = {}, [], set(mine)
    for _index, _name, _target, run in rows:
        db = Path(kept) / "traces" / f"{run}.db"
        if not db.is_file():
            unreadable.append(f"{run}: not in the kept store ({db})")
            continue
        recorded = trace_meta_ro(db).get("env")
        if not isinstance(recorded, dict):
            unreadable.append(f"{run}: no recorded environment to compare "
                              "against")
            continue
        theirs = {k: v for k, v in recorded.items()
                  if not EXCLUDED_ENV.match(k) and k not in UNCOMPARED_ENV}
        compared |= set(theirs)
        for key in sorted(set(mine) | set(theirs)):
            if mine.get(key) == theirs.get(key):
                continue
            how = ("this process ADDED it" if key not in theirs else
                   "this process is MISSING it" if key not in mine else
                   "the value differs")
            differing.setdefault(key, {"how": how, "originals": []})
            differing[key]["originals"].append(run)
    rec = {"checked": len(rows) - len(unreadable),
           "originals": len(rows),
           "differing": sorted(differing),
           "detail": differing,
           "unreadable": unreadable,
           "compared_keys": sorted(compared),
           "excluded_pattern": EXCLUDED_ENV.pattern,
           "uncompared": sorted(UNCOMPARED_ENV)}
    if unreadable or differing:
        named = "; ".join(
            f"{k} ({d['how']}; {len(d['originals'])} original(s), e.g. "
            f"{', '.join(d['originals'][:3])})"
            for k, d in sorted(differing.items()))
        raise Refused(
            "this process's environment is NOT the one the originals were "
            f"recorded under. {len(differing)} key(s) differ: {named}"
            + (f". Originals that could not be read: {unreadable}"
               if unreadable else "")
            + ". The licence compares the recording environments, so every "
              "one of these would be reported as a change the world made "
              "on all 61 pairs. Pin them in the launcher (it already "
              "exports PYTHONDONTWRITEBYTECODE, SSL_CERT_DIR and "
              "SSL_CERT_FILE) and relaunch -- nothing has been copied and "
              "no number has been read, so this is the infrastructure kill")
    step(f"env parity: {rec['checked']} original(s) checked over "
         f"{len(rec['compared_keys'])} compared key(s); none differ")
    return rec


def _require_fresh(path: Path, what: str) -> None:
    if path.exists() and any(path.iterdir()):
        raise Refused(f"{what} {path} is not FRESH: it already holds "
                      f"{len(list(path.iterdir()))} entr(ies). §1.4 requires "
                      "it empty at the start, and a re-used location makes "
                      "H4's census and §1.3's listing count meaningless")


def preflight(paths, cfg) -> dict:
    """What THIS run touches, and nothing else.

    Refuses on: the machine's load; either disk floor; a clone that is not
    at §1.4's pin or is not porcelain-clean; a kept store that is not there
    or does not hold every one of §1.1's originals; a driver that will not
    build from HEAD; a `SENSORIUM_DIR`, an E4′ target or a corpus target
    that is not fresh. Every one of these is BEFORE any number is read, so
    each is the INFRASTRUCTURE kill (§1.4's rule 4) rather than a STOP.
    """
    step("rung-4 debts (E4′) preflight")
    load = loadavg()
    if load > LOAD_CEILING:
        raise Refused(f"1-minute load {load} > {LOAD_CEILING}")
    repo_free = free_gb(REPO)
    if repo_free < REPO_DISK_FLOOR_GB:
        raise Refused(f"{REPO}: {repo_free:.1f} GB free < "
                      f"{REPO_DISK_FLOOR_GB} GB floor")

    clone = paths["sensorium_bloomery"]
    if not (clone / ".git").exists():
        raise Refused(f"no git clone at {clone}")
    head = clone_git(paths, "rev-parse", "HEAD")
    if head != CLONE_PIN:
        raise Refused(f"the clone is at {head}, not §1.4's pin {CLONE_PIN}")
    porcelain = clone_git(paths, "status", "--porcelain")
    if porcelain:
        raise Refused(f"the clone at {clone} is not clean:\n{porcelain}")
    lock_sha = sha256_file(clone / "Cargo.lock")

    kept = paths["sensorium_e4_store"]
    if not (kept / "traces").is_dir():
        raise Refused(f"the kept E4 store {kept} has no `traces/` directory: "
                      "§1.3 copies the 61 originals out of it and this run "
                      "cannot start without them")

    # The cheap refusals FIRST: a misconfigured launch must not spend a
    # driver build before finding out that its target is not fresh.
    cargo_check = cargo_running()
    parity = env_parity(kept, cfg["rows"])
    _require_fresh(paths["sensorium_dir"], "SENSORIUM_DIR")
    _require_fresh(paths["sensorium_e4p_target"], "SENSORIUM_E4P_TARGET")
    _require_fresh(cfg["corpus_target"], "H6's corpus target")

    built = build_driver(paths)
    driver = Path(paths["sensorium_driver"])
    target_free = free_gb(paths["sensorium_e4p_target"].parent)
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{paths['sensorium_e4p_target']}: {target_free:.1f} "
                      f"GB free < {TARGET_DISK_FLOOR_GB} GB floor")

    py = REPO / ".venv" / "bin" / "python"
    attr_probe, meta_probe = attribute_probe(py), version_probe(py)
    pins = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse",
                           "--abbrev-ref", "HEAD"),
        "repo_porcelain": out("git", "-C", str(REPO), "status", "--porcelain"),
        "clone": str(clone), "clone_head": head, "clone_pin": CLONE_PIN,
        "clone_porcelain": porcelain, "clone_cargo_lock_sha256": lock_sha,
        "clone_read_only_reading": (
            "the clone is an INPUT: nothing writes into it but cargo's own "
            "`Cargo.lock` refresh, whose sha256 is recorded before and after "
            "and which the cleanup restores to the pin"),
        "kept_store": str(kept),
        "kept_store_read_only_reading": (
            "the kept E4 store is opened `mode=ro` and copied from by §1.3's "
            "`VACUUM INTO`; no refocus points at it and nothing writes into "
            "it. Every `.db`'s size and `st_mtime_ns` is censused before and "
            "after the whole run and the two lists are compared file by file"),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "driver_rebuilt_by_this_run": built["rebuilt"],
        "driver_profile": built["profile"], "built_from": built,
        "transform_version": transform_version(),
        "rustc": out("rustc", "-V"), "cargo": out("cargo", "-V"),
        "python": out(str(REPO / ".venv" / "bin" / "python"), "-V"),
        # E4′ §5's gap 2: both tokens go through a probe that captures
        # stderr, so a probe that could not answer records `null` with its
        # reason instead of the empty string a reader takes for a measured
        # one. The bare fields keep their shape for the renderer; the two
        # `*_probe` dicts carry the rc, the command and the reason.
        "sensorium_version": attr_probe["token"],
        "sensorium_version_probe": attr_probe,
        "sensorium_version_metadata": meta_probe["token"],
        "sensorium_version_metadata_probe": meta_probe,
        "nproc": os.cpu_count(),
        "governor": _governor(),
        "load_1min_at_start": load,
        "repo_disk_free_gb": round(repo_free, 2),
        "target_disk_free_gb": round(target_free, 2),
        "sensorium_dir": str(paths["sensorium_dir"]),
        "e4p_target": str(paths["sensorium_e4p_target"]),
        "rust_target": str(paths["sensorium_rust_target"]),
        "corpus_target": str(cfg["corpus_target"]),
        "corpus_target_from_env": cfg["corpus_target_from_env"],
        "tmpdir_observed": cfg["tmpdir_observed"],
        "tempfile_gettempdir": cfg["tempfile_gettempdir"],
        "tmpdir_reading": (
            "TMPDIR was unset, so `tempfile.gettempdir()` resolved to "
            f"{cfg['tempfile_gettempdir']}. No endpoint in this record is "
            "derived from a temporary path -- there is no `watch` triple "
            "here -- so TMPDIR binds nothing; it is recorded because it is "
            "part of the environment the licence compares"
            if cfg["tmpdir_observed"] is None else
            f"TMPDIR was SET to {cfg['tmpdir_observed']!r} at measurement "
            "time. No prediction in this record moves on it: no endpoint is "
            "derived from a temporary path"),
        "sensorium_tier": (
            "NOT set by this record: each refocus replays the tier recorded "
            "on its own original, and E4's pass 1 ran with SENSORIUM_TIER "
            "unset, so the driver's default `call` applies again"),
        "invocation_log": (
            "NOT silenced: SENSORIUM_NO_INVOCATION_LOG is unset, so every "
            "reader invocation this record makes is logged into the FRESH "
            "store, and the row count is recorded at the end. The 61 copied "
            "originals carry no such rows from E4, so the count is this "
            "record's own"),
        "sqlite3_cli": sqlite3_cli(),
        "cargo_running_check": cargo_check,
        "env_parity": parity,
        # Filled from the first refocused trace: §1.4 reads every version
        # token from the TRACE's own meta, never from this file.
        "driver_version_from_the_trace": None,
    }
    step(f"preflight ok: load={load} clone={head[:12]} driver="
         f"{(pins['driver_sha256'] or '?')[:12]} target free "
         f"{target_free:.1f} GB; TMPDIR={cfg['tmpdir_observed']!r} "
         f"(gettempdir {cfg['tempfile_gettempdir']})")
    return pins


def _governor() -> str | None:
    path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
    return path.read_text().strip() if path.is_file() else None


def cleanup(paths, cfg, pins, kept_before) -> dict:
    """What the run left behind, the clone put back on the pin, and §1.3's
    proof that the kept store was not written."""
    clone = paths["sensorium_bloomery"]
    lockfile = clone / "Cargo.lock"
    after_sha = sha256_file(lockfile)
    moved = after_sha != pins.get("clone_cargo_lock_sha256")
    restored = None
    if moved:
        out("git", "-C", str(clone), "checkout", "--", "Cargo.lock")
        restored = sha256_file(lockfile)
    sdir = paths["sensorium_dir"]
    log = sdir / "invocations.jsonl"
    traces = sdir / "traces"
    kept_after = store_census(paths["sensorium_e4_store"])
    differences = census_diff(kept_before or {}, kept_after)
    c = {
        "clone_head_after": clone_git(paths, "rev-parse", "HEAD"),
        "clone_porcelain_after": clone_git(paths, "status", "--porcelain"),
        "clone_cargo_lock_sha256_after": after_sha,
        "clone_cargo_lock_moved": moved,
        "clone_cargo_lock_sha256_restored": restored,
        "clone_cargo_lock_back_on_the_pin": (
            (restored if moved else after_sha)
            == pins.get("clone_cargo_lock_sha256")),
        "kept_census_after": kept_after,
        "kept_census_after_n": kept_after.get("n"),
        "kept_census_differences": differences,
        "kept_store_unchanged": not differences,
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
        "driver_unchanged": (sha256_file(paths["sensorium_driver"])
                             == pins.get("driver_sha256")),
        # `None` is "there is nothing there to count", `0` is "counted, and
        # zero": a store the run never created and one it created and left
        # empty are different facts.
        "store_bytes_after": dir_bytes(sdir) if sdir.is_dir() else None,
        "traces_in_the_fresh_store": (len(list(traces.glob("*.db")))
                                      if traces.is_dir() else None),
        "invocations_jsonl_lines": (len(log.read_text().splitlines())
                                    if log.is_file() else None),
        "e4p_target_bytes": (dir_bytes(paths["sensorium_e4p_target"])
                             if paths["sensorium_e4p_target"].is_dir()
                             else None),
        "corpus_target_bytes": (dir_bytes(cfg["corpus_target"])
                                if cfg["corpus_target"].is_dir() else None),
        "repo_porcelain_after": out("git", "-C", str(REPO), "status",
                                    "--porcelain"),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "target_disk_free_gb_after": round(
            free_gb(paths["sensorium_e4p_target"].parent), 2),
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"cleanup: clone HEAD {c['clone_head_after'][:12]}, Cargo.lock moved "
         f"{moved} back-on-the-pin {c['clone_cargo_lock_back_on_the_pin']}; "
         f"kept store unchanged {c['kept_store_unchanged']} "
         f"({len(differences)} difference(s)); "
         f"{c['traces_in_the_fresh_store']} trace(s) in the fresh store")
    return c


__all__ = ["EXCLUDED_ENV", "UNCOMPARED_ENV", "LOGS", "CARGO_TIMEOUT",
           "attribute_probe", "build_driver", "cargo_running", "env_parity",
           "cleanup", "clone_git", "mark_numbers_read", "out", "out_err",
           "preflight", "transform_version", "version_probe"]
