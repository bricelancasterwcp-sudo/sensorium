#!/usr/bin/env python3
"""The E9 runner: the focus tier measured ONCE against the bloomery clone, in
the order `docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md` §1
pre-registers.

WHAT THIS RUNNER DOES
---------------------
It records §1's four runs -- U1, F1, U2, F2 -- against the read-only clone at
`e209ed9`, then asks H1-H7 of them. Unlike its immediate sibling
(`acceptance_grain.py`, which re-read kept stores), this one BUILDS: U1 is a
cold build of the clone's dependency tree and F1 rebuilds the matched crate
under a focus, so every cargo invocation carries an hour-long ceiling and a
timeout is recorded as a fact rather than raised.

THREE RULES RUN THROUGH IT
--------------------------
* **§1 is the contract, and it is byte-locked.** `check_byte_lock` refuses to
  start unless the locked range is byte-identical to the commit that locked
  it. §1 was committed ALONE and never amended, so there is one sha and
  `ORIGINAL_LOCK` is `None`; the record carries `amended_after_the_original_
  lock: False` as a fact rather than as a claim in prose.
* **No endpoint is ever filled from a prediction.** §1's numbers -- N = 26,
  §1.1's per-line table, the three `watch` triples, the two sightings -- are
  in the room, and a headline that borrowed from one could not fail. They
  enter as COMPARISON TARGETS under their own names; a phase that did not run
  publishes `null` with a reason (`acceptance_e9_schema`, tested in
  `tests/test_acceptance_e9.py`).
* **Every location is an environment variable.** No box path appears in any
  module of this instrument, and the five below are refused TOGETHER when
  missing so one launch reports all of them.

THE LOCATIONS
-------------
    SENSORIUM_DRIVER        the `cargo-sensorium` binary, by absolute path;
                            the runner REBUILDS it from this branch's HEAD
                            into its own target before measuring (§1.4)
    SENSORIUM_BLOOMERY      the read-only clone, pinned at e209ed9
    SENSORIUM_E9_TARGET     a FRESH CARGO_TARGET_DIR for the four runs
    SENSORIUM_DIR           a FRESH trace store for the four runs
    SENSORIUM_RUST_TARGET   this workspace's target, for H7's `cargo test`
    SENSORIUM_CORPUS_TARGET optional; H7's FRESH corpus target. §1.4 requires
                            it to be fresh but names no variable, so when it
                            is unset the runner derives `<E9 target>-corpus`
                            -- still an env-var-derived location, never a
                            path compiled into this file.

Launch it detached and read nothing before the marker exists:

    setsid nohup .venv/bin/python rust/tests/acceptance_e9.py \
        > <ledger>/acceptance-e9/logs/e9.log 2>&1 &

The last act is `<ledger>/acceptance-e9/e9.DONE` (or `.FAILED`) carrying
`exit=<n>`, so silence is distinguishable from success.
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
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-06-sensorium-rung4-focus-tier"
LEDGER = PLAN
BASE = PLAN / "acceptance-e9"
LOGS = BASE / "logs"

# Every earlier ledger is evidence and is not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_e9_phases as eph                                 # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_e6ppp import LOADS, logs_at                        # noqa: E402,F401
from acceptance_e9_phases import (FOCUS_A, FOCUS_B, PAIRS,         # noqa: E402,F401
                                  RUNS, argv_of, flow_sightings,
                                  guarded, phase_h1, phase_h2, phase_h3,
                                  phase_h4, phase_h5, phase_h6, phase_h7,
                                  phase_records, pick_run, record,
                                  record_env, watch_triples)
from acceptance_e9_read import temp_root                           # noqa: E402
from acceptance_lib import (CLONE_PIN, LOAD_CEILING,               # noqa: E402
                            REPO_DISK_FLOOR_GB, TARGET_DISK_FLOOR_GB,
                            Refused, dir_bytes, free_gb, loadavg,
                            plain_env, run, sha256_file, step)

# Re-asserted AFTER the imports above, and not only before them: importing
# `acceptance_rung3` points `acceptance_lib.LEDGER`/`LOGS` at the rung-3
# slice's workspace and `acceptance_e6ppp` at the E6‴ document's. `eph.LOGS`
# is the third pointer -- the phases each open `logs_at(LOGS / "<phase>")` in
# THEIR OWN namespace, and the entry slice's first launch died on exactly
# that name being unset fourteen seconds in. `e6ppp.LOGS`/`BASE` move too,
# because `build_driver` and `logs_at` resolve them where they are defined.
lib.LEDGER = LEDGER
lib.LOGS = LOGS
ph.LOGS = LOGS
eph.LOGS = LOGS
e6ppp.LOGS = LOGS
e6ppp.BASE = BASE

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-06-sensorium-rung4-e9.md")

#: The commit that committed §1 ALONE, before any number below was read. A
#: `None` lock REFUSES rather than measuring against a pre-registration that
#: can still be edited.
BYTE_LOCK = "a4264b5"
#: §1 of this document is committed once and never amended, so there is no
#: second sha to carry -- `byte_lock_facts` records
#: `amended_after_the_original_lock: False` and `original_lock_sha256: None`.
ORIGINAL_LOCK = None

RUNNER = "rust/tests/acceptance_e9.py"
RAW = LEDGER / "results-e9-raw.json"
RESULTS = (REPO / "docs" / "superpowers" / "acceptance"
           / "2026-09-06-sensorium-rung4-e9.results.json")

#: §1.1's hand count, line by line, as a COMPARISON TARGET published under
#: its own name. Every one of these 26 source lines mints exactly one LINE
#: row under design §3.1/§3.2; the diff against the measured histogram is
#: what lets a miss name lines instead of reporting a number.
EXPECTED_BY_LINE = {ln: 1 for ln in (
    250, 251, 252, 253, 254, 255, 257, 259, 263, 264, 265, 266, 267, 268,
    274, 275, 276, 277, 278, 282, 283, 286, 287, 292, 293, 300)}

#: §1.1's gate, and the three readings it accounts for. A count outside the
#: accounted set is §1's kill 4: a STOP, with the diff of lines.
GATE_N = 26
ACCOUNTED_N = frozenset({25, 26, 27})

#: The five locations, and the `paths` keys they land under.
E9_ENV = {
    "SENSORIUM_DRIVER": "sensorium_driver",
    "SENSORIUM_BLOOMERY": "sensorium_bloomery",
    "SENSORIUM_E9_TARGET": "sensorium_e9_target",
    "SENSORIUM_DIR": "sensorium_dir",
    "SENSORIUM_RUST_TARGET": "sensorium_rust_target",
}

#: Ceilings. Each cargo invocation of §1's four runs gets an hour: U1 is a
#: COLD build of the clone's whole dependency tree and F1 rebuilds the
#: matched crate under a focus. A reader command gets two minutes -- a query
#: over a single test binary's trace that has not answered in two minutes is
#: a fact worth recording, not a slow machine.
CARGO_TIMEOUT = 3600
READER_TIMEOUT = 120
CORPUS_TIMEOUT = 7200
PYTEST_TIMEOUT = 3600
CARGO_TEST_TIMEOUT = 7200


def out(*args) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def clone_git(paths, *args) -> str:
    return out("git", "-C", str(paths["sensorium_bloomery"]), *args)


# ------------------------------------------------------------ lock and paths


def check_byte_lock() -> dict:
    """§1, as committed, versus the working tree -- or a refusal to start."""
    if not BYTE_LOCK:
        raise Refused(
            "§1 of the acceptance document is not locked yet: BYTE_LOCK is "
            "None. Commit §1 ALONE, then set BYTE_LOCK to that commit's sha.")
    return rung3.byte_lock_check(DOC, BYTE_LOCK, ORIGINAL_LOCK)


def env_paths_e9() -> dict:
    """Every location this run touches, from the environment, refused
    together when missing -- one launch reports all of them."""
    missing = [k for k in E9_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(
            "unset environment variable(s): " + ", ".join(missing)
            + " -- this run needs the `cargo-sensorium` binary to rebuild "
              "and measure with, the read-only bloomery clone at "
              f"{CLONE_PIN[:7]}, a FRESH cargo target for the four runs, a "
              "FRESH trace store for them, and this workspace's own target "
              "for H7's `cargo test --workspace`")
    return {name: Path(os.environ[key]) for key, name in E9_ENV.items()}


def e9_config(paths) -> dict:
    """This run's config. The corpus target is derived from the E9 target
    when `SENSORIUM_CORPUS_TARGET` is unset: §1.4 requires H7's corpus target
    to be fresh but names no variable for it, and a location derived from an
    env var is still not a location compiled into this file."""
    corpus = os.environ.get("SENSORIUM_CORPUS_TARGET")
    e9t = paths["sensorium_e9_target"]
    return {
        "corpus_target": (Path(corpus) if corpus
                          else e9t.parent / (e9t.name + "-corpus")),
        "corpus_target_from_env": bool(corpus),
        "cargo_timeout": CARGO_TIMEOUT,
        "reader_timeout": READER_TIMEOUT,
        "corpus_timeout": CORPUS_TIMEOUT,
        "pytest_timeout": PYTEST_TIMEOUT,
        "cargo_test_timeout": CARGO_TEST_TIMEOUT,
        "expected_by_line": dict(EXPECTED_BY_LINE),
        "gate_n": GATE_N,
        "accounted_n": ACCOUNTED_N,
        "focus_a": FOCUS_A, "focus_b": FOCUS_B,
        "clone_pin": CLONE_PIN,
        # §1.4: `TMPDIR` is expected UNSET, which is what makes
        # `std::env::temp_dir()` `/tmp` and W1/W3/S1/S2 derivable at all. It
        # is OBSERVED here, and every literal below is built from it, so a
        # run under a set `TMPDIR` reads the same predictions with the prefix
        # substituted rather than reading the wrong ones silently.
        "tmpdir_observed": os.environ.get("TMPDIR"),
        "temp_root": temp_root(os.environ.get("TMPDIR")),
    }


def build_driver_e9(paths) -> dict:
    """`cargo build [-r] -p cargo-sensorium`, run BY the runner, and the
    record of what it built from (§1.4's `built_from`).

    `acceptance_e6ppp.build_driver` builds `--release` unconditionally, and
    this run's driver may be either profile: the profile is read from the
    binary's own parent directory (`<target>/<debug|release>/cargo-sensorium`
    is cargo's layout), so the build lands exactly where `SENSORIUM_DRIVER`
    points instead of refreshing the other profile and reporting `rebuilt:
    False` about a stale binary. A path whose parent is neither is refused
    rather than guessed at.
    """
    driver = Path(paths["sensorium_driver"])
    profile = driver.parent.name
    if profile not in ("debug", "release"):
        raise Refused(
            f"SENSORIUM_DRIVER {driver} is not under a cargo profile "
            f"directory (its parent is {profile!r}, not `debug` or "
            "`release`), so the runner cannot rebuild it from HEAD as §1.4 "
            "requires")
    target = driver.parents[1]
    before = sha256_file(driver)
    cmd = ["cargo", "build", "-p", "cargo-sensorium"]
    if profile == "release":
        cmd.insert(2, "--release")
    with logs_at(LOGS / "built-from"):
        res = run(cmd, REPO / "rust", "built-from.log",
                  plain_env() | {"CARGO_TARGET_DIR": str(target)},
                  timeout=CARGO_TIMEOUT)
    after = sha256_file(driver)
    rec = {
        "repo_head_at_build": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_porcelain_at_build": out("git", "-C", str(REPO), "status",
                                       "--porcelain"),
        "command": " ".join(cmd), "profile": profile,
        "cargo_target_dir": str(target),
        "cargo_rc": res["rc"], "cargo_wall_s": round(res["wall"], 3),
        "driver": str(driver),
        "driver_sha256_before_build": before,
        "driver_sha256_after_build": after,
        "rebuilt": before != after,
        "log": res["log"],
    }
    if res["rc"] != 0:
        raise Refused(f"`{' '.join(cmd)}` exited {res['rc']}: the driver is "
                      "not this HEAD's")
    if after is None:
        raise Refused(f"the build succeeded but no binary is at {driver}")
    step(f"built_from: HEAD {rec['repo_head_at_build'][:12]} rc 0 in "
         f"{rec['cargo_wall_s']}s; driver {after[:12]} "
         f"rebuilt={rec['rebuilt']}")
    return rec


# ------------------------------------------------------------- the preflight


def _require_fresh(path: Path, what: str) -> None:
    if path.exists() and any(path.iterdir()):
        raise Refused(
            f"{what} {path} is not empty; §1.4 says FRESH, and a warm one "
            "would answer with another run's artifacts")
    path.mkdir(parents=True, exist_ok=True)


def preflight_e9(paths, cfg) -> dict:
    """What THIS run touches, and nothing else.

    Refuses on: the machine's load; either disk floor; a clone that is not
    at §1.4's pin or is not porcelain-clean; a driver that will not build
    from HEAD; a `SENSORIUM_DIR`, an E9 target or a corpus target that is
    not fresh.
    """
    step("rung-4 focus-tier (E9) preflight")
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
    lockfile = clone / "Cargo.lock"
    lock_sha = sha256_file(lockfile)

    # The cheap refusals FIRST: a misconfigured launch must not spend a
    # driver build before finding out that its target is not fresh.
    _require_fresh(paths["sensorium_dir"], "SENSORIUM_DIR")
    _require_fresh(paths["sensorium_e9_target"], "SENSORIUM_E9_TARGET")
    _require_fresh(cfg["corpus_target"], "H7's corpus target")

    built = build_driver_e9(paths)
    driver = Path(paths["sensorium_driver"])
    target_free = free_gb(paths["sensorium_e9_target"])
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{paths['sensorium_e9_target']}: {target_free:.1f} GB "
                      f"free < {TARGET_DISK_FLOOR_GB} GB floor")

    pins = {
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "repo_commit": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_branch": out("git", "-C", str(REPO), "rev-parse",
                           "--abbrev-ref", "HEAD"),
        "repo_porcelain": out("git", "-C", str(REPO), "status", "--porcelain"),
        "clone": str(clone), "clone_head": head, "clone_pin": CLONE_PIN,
        "clone_porcelain": porcelain,
        "clone_cargo_lock_sha256": lock_sha,
        "clone_read_only_reading": (
            "the clone is an INPUT: nothing writes into it but cargo's own "
            "`Cargo.lock` refresh, whose sha256 is recorded before and after "
            "and which the cleanup restores to the pin"),
        "driver": str(driver), "driver_sha256": sha256_file(driver),
        "driver_rebuilt_by_this_run": built["rebuilt"],
        "driver_profile": built["profile"],
        "driver_mtime": time.strftime("%Y-%m-%dT%H:%M:%S%z",
                                      time.localtime(driver.stat().st_mtime)),
        "built_from": built,
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
        "target_disk_free_gb": round(target_free, 2),
        "sensorium_dir": str(paths["sensorium_dir"]),
        "e9_target": str(paths["sensorium_e9_target"]),
        "rust_target": str(paths["sensorium_rust_target"]),
        "corpus_target": str(cfg["corpus_target"]),
        "corpus_target_from_env": cfg["corpus_target_from_env"],
        "tmpdir_observed": cfg["tmpdir_observed"],
        "temp_root": cfg["temp_root"],
        "tmpdir_reading": (
            "TMPDIR was unset, so `std::env::temp_dir()` is `/tmp` and "
            "W1/W3/S1/S2 read as §1.2 and §1.3 derive them"
            if cfg["tmpdir_observed"] is None else
            f"TMPDIR was set to {cfg['tmpdir_observed']!r}, so §1.4's "
            f"substituted reading was taken: every predicted literal reads "
            f"against {cfg['temp_root']}/…"),
        "sensorium_tier": (
            "unset -- §1.4 leaves the coarse tier at its default `call` for "
            "all four runs, so U1/U2 and F1/F2 differ only by `--focus`"),
        "invocation_log": (
            "NOT silenced: SENSORIUM_NO_INVOCATION_LOG is unset, so every "
            "reader call this record makes appends a row to the store's "
            "`invocations.jsonl`, and the count is recorded at the end"),
    }
    step(f"preflight ok: load={load} clone={head[:12]} driver="
         f"{(pins['driver_sha256'] or '?')[:12]} target free "
         f"{target_free:.1f} GB; TMPDIR={cfg['tmpdir_observed']!r}")
    return pins


def cleanup_e9(paths, cfg, pins) -> dict:
    """What the run left behind, and the clone put back on the pin."""
    clone = paths["sensorium_bloomery"]
    lockfile = clone / "Cargo.lock"
    after_sha = sha256_file(lockfile)
    moved = after_sha != pins.get("clone_cargo_lock_sha256")
    restored = None
    if moved:
        # §1.4: the clone is read-only and `Cargo.lock` is restored to the
        # pin. Cargo refreshes it during a build; the restore is recorded
        # rather than assumed, so the next run starts from the pin.
        out("git", "-C", str(clone), "checkout", "--", "Cargo.lock")
        restored = sha256_file(lockfile)
    sdir = paths["sensorium_dir"]
    log = sdir / "invocations.jsonl"
    c = {
        "clone_head_after": clone_git(paths, "rev-parse", "HEAD"),
        "clone_porcelain_after": clone_git(paths, "status", "--porcelain"),
        "clone_cargo_lock_sha256_after": after_sha,
        "clone_cargo_lock_moved": moved,
        "clone_cargo_lock_sha256_restored": restored,
        "clone_cargo_lock_back_on_the_pin": (
            (restored if moved else after_sha)
            == pins.get("clone_cargo_lock_sha256")),
        "driver_sha256_after": sha256_file(paths["sensorium_driver"]),
        "driver_unchanged": (sha256_file(paths["sensorium_driver"])
                             == pins.get("driver_sha256")),
        "store_bytes": dir_bytes(sdir) if sdir.is_dir() else 0,
        "traces_recorded": len(list((sdir / "traces").glob("*.db")))
        if (sdir / "traces").is_dir() else 0,
        "invocations_jsonl_lines": (len(log.read_text().splitlines())
                                    if log.is_file() else 0),
        "e9_target_bytes": dir_bytes(paths["sensorium_e9_target"])
        if paths["sensorium_e9_target"].is_dir() else 0,
        "corpus_target_bytes": dir_bytes(cfg["corpus_target"])
        if cfg["corpus_target"].is_dir() else 0,
        "repo_porcelain_after": out("git", "-C", str(REPO), "status",
                                    "--porcelain"),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "target_disk_free_gb_after": round(
            free_gb(paths["sensorium_e9_target"]), 2)
        if paths["sensorium_e9_target"].is_dir() else None,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"cleanup: clone HEAD {c['clone_head_after'][:12]}, Cargo.lock moved "
         f"{moved} back-on-the-pin {c['clone_cargo_lock_back_on_the_pin']}; "
         f"{c['traces_recorded']} trace(s), {c['store_bytes']} store bytes; "
         f"driver unchanged {c['driver_unchanged']}")
    return c


# -------------------------------------------------------------------- main


def _partial_json(res: dict) -> str:
    """Whatever of the record CAN be serialised, key by key, with the keys
    that could not NAMED. A run that measured for an hour must lose one value
    to a serialisation defect, not all of them."""
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


def _cfg_json(cfg: dict) -> dict:
    """`cfg` as the record stores it: paths stringified, the accounted set a
    sorted list (a `frozenset` is not JSON), the line table's keys strings."""
    out_ = {}
    for k, v in cfg.items():
        if isinstance(v, Path):
            out_[k] = str(v)
        elif isinstance(v, (set, frozenset)):
            out_[k] = sorted(v)
        elif k == "expected_by_line":
            out_[k] = {str(a): b for a, b in sorted(v.items())}
        else:
            out_[k] = v
    return out_


def main(argv) -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("e9.DONE", "e9.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": RUNNER,
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = check_byte_lock()
        paths = env_paths_e9()
        cfg = e9_config(paths)
        res["config"] = _cfg_json(cfg)
        # §1's triples and sightings, recorded BEFORE any phase runs, so the
        # record publishes what was predicted even for a phase that never
        # ran. They are comparison targets and are never a value a cell can
        # fall back to (`acceptance_e9_schema._predictions`).
        res["predictions"] = {
            "watch_triples": [{k: t[k] for k in
                               ("id", "run", "at", "expr", "predicted_class",
                                "predicted_exit", "line")}
                              for t in watch_triples(cfg)],
            "flow_sightings": [{k: s[k] for k in
                                ("id", "literal", "binding", "line")}
                               for s in flow_sightings(cfg)],
        }
        pins = preflight_e9(paths, cfg)
        res["pins"] = pins

        records = phase_records(paths, cfg)
        res["raw_records"] = records
        res["raw_h1"] = phase_h1(paths, cfg, records)
        res["raw_h2"] = phase_h2(paths, cfg, records)
        res["raw_h3"] = phase_h3(paths, cfg, records)
        res["raw_h4"] = phase_h4(paths, cfg, records)
        res["raw_h5"] = phase_h5(paths, cfg, records)
        res["raw_h6"] = phase_h6(records)
        # H7 LAST: `cargo test --workspace` shares the driver's target and is
        # the one thing in this run that could relink the binary every other
        # phase measured with.
        res["raw_h7"] = phase_h7(paths, cfg)
        res["cleanup"] = cleanup_e9(paths, cfg, pins)
        # §1's kill 1: a compile failure of a FOCUSED unit is a STOP, and the
        # marker says so. Every number already read stays in the record.
        if records["focused_build_failed"]:
            res["stop"] = ("§1 kill 1: focused run(s) "
                           f"{records['focused_build_failed']} did not "
                           "complete; no fallback and no retry was made")
            rc = rc or 7
        if (res["raw_h3"] or {}).get("stop"):
            res["stop"] = ("§1 kill 4: H3's N = "
                           f"{res['raw_h3'].get('N')} is outside "
                           f"{sorted(ACCOUNTED_N)}; the diff of lines is in "
                           "`raw_h3.diff`")
            rc = rc or 7
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
            res["cleanup_after_failure"] = cleanup_e9(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        RAW.write_text(json.dumps(res, indent=2, default=str))
    except (TypeError, ValueError):
        # The last act of an hour-long run, and it must not be able to lose
        # the run: `default=` does not apply to dict KEYS, so one
        # unserialisable key would raise here -- outside every try -- and
        # leave no raw record, no `results.json` and NO MARKER.
        import traceback
        trace = traceback.format_exc()
        (LOGS / "raw-json-error.txt").write_text(trace)
        res["raw_json_error"] = trace.strip().splitlines()[-1]
        step("writing the raw record FAILED (logs/raw-json-error.txt); "
             "writing what CAN be serialised instead")
        RAW.write_text(_partial_json(res))
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
    (BASE / ("e9.DONE" if rc == 0 else "e9.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{res.get('refused') or res.get('stop') or res.get('error') or ''}\n")
    step(f"done rc={rc}; raw facts at {RAW}")
    return rc


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no phase and
    reads no new number."""
    from acceptance_e9_schema import assemble_e9                   # noqa: PLC0415
    if raw is None:
        raw = json.loads(RAW.read_text())
    doc = assemble_e9(raw)
    doc["assembled"] = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "from": RAW.name,
        "by": f"{RUNNER} --assemble",
        "note": ("derived from the raw facts the run recorded, which nothing "
                 "since has touched; no phase was re-run and no value "
                 "re-measured"),
    }
    RESULTS.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    print(f"assembled {RESULTS} from {RAW.name}")
    return 0


def render_only() -> int:
    """§2 and §3, rendered from the assembled record into the ledger. The
    document itself is edited by hand at Task 8; this is the text it pastes,
    produced by committed code rather than by a one-off script."""
    import render_e9                                              # noqa: PLC0415
    doc = json.loads(RESULTS.read_text())
    text = "\n".join(render_e9.environment(doc) + [""]
                     + render_e9.results(doc))
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "section-2-3.md").write_text(text + "\n")
    print(f"rendered {BASE / 'section-2-3.md'}")
    return 0


if __name__ == "__main__":
    if "--assemble" in sys.argv[1:]:
        raise SystemExit(assemble_only() or render_only())
    if "--render" in sys.argv[1:]:
        raise SystemExit(render_only())
    raise SystemExit(main(sys.argv[1:]))
