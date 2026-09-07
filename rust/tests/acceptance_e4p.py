#!/usr/bin/env python3
"""The E4′ runner: PASS 2 ONLY, measured ONCE over E4's 61 kept originals
under the repaired harness rule.

`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md` §1.

WHAT THIS RUNNER DOES
---------------------
Nothing is re-recorded. Pass 1 already happened -- it is E4's -- so its 61
originals are COPIED out of the kept store by §1.3's statement and the only
invocation this record makes against the subject is

    sensorium refocus <run> --focus <name>

for each of §1.1's 61 rows, in §1.1's order, against a FRESH store and a
FRESH `CARGO_TARGET_DIR`. Because pass 1 is not re-run, the originals' bytes
are E4's exactly, and any difference this record reads is attributable to
the reader and the driver, never to a fresh recording.

Then H1-H6 are asked of the 61 pairs: the licence partition (H1), the
verdict (H2), the pair (H3), the shim census (H4), `schema_version` (H5),
and what did not move (H6).

THE RULES THAT RUN THROUGH IT
-----------------------------
* **§1 is the contract, and it is byte-locked.** `check_byte_lock` refuses
  to start unless the locked range is byte-identical to the commit that
  locked it, and refuses outright while no lock sha is set. §1 was committed
  ALONE, before `harness_threads` existed, and has never been amended.
* **No endpoint is ever filled from a prediction.** §1.2's numbers -- 57
  granted, the four names, MATCH 61, pair 1 of 1 -- enter as COMPARISON
  TARGETS under their own names (`acceptance_e4p_schema._predictions`). A
  headline that borrowed from one could not fail.
* **The kept store is READ-ONLY.** It is opened `mode=ro`, copied from by
  `VACUUM INTO`, and its every `.db`'s size and `st_mtime_ns` are censused
  before and after the whole run. A single difference is reported.
* **None is not zero.** An unread field is `null` with its reason in
  `dropped`; a KILLED cell is `{killed, reason}` and has no numeric reading.
* **Every location is an environment variable.** No box path appears in any
  module of this instrument, and the seven below are refused TOGETHER when
  missing so one launch reports all of them.
* **A kill is a fact, not an exception.** Every child runs in its own
  process GROUP and a bound reached kills the group, verifies with `ps -p`
  and records what it did. `pkill -f` is never used.

THE KILL CROSS-REFERENCES IN THE LOCKED §1
------------------------------------------
Three of §1's citations name the wrong index and this runner implements the
WORDS of each sentence, never the number beside it (§2 files the erratum):

* H5's "a STOP of the instrument ... under kill 4" -- the WORDS say STOP,
  which is rule 5.
* §1.3's "a single changed mtime is a STOP under kill 4" -- likewise a STOP.
* §1.3's "a mismatch is a refusal to start (before any number, so kill 3)"
  -- the WORDS say a refusal before any number, which is rule 4,
  INFRASTRUCTURE: relaunch from zero with the copies re-made.

THE LOCATIONS
-------------
    SENSORIUM_DRIVER          the `cargo-sensorium` binary, by absolute
                              path; the runner REBUILDS it from this
                              branch's HEAD before measuring (§1.3)
    SENSORIUM_E4_STORE        the KEPT E4 store -- READ-ONLY input, the
                              source of the 61 copies
    SENSORIUM_BLOOMERY        the read-only clone, pinned at e209ed9
    SENSORIUM_E4P_TARGET      a FRESH CARGO_TARGET_DIR for the 61 rebuilds
    SENSORIUM_DIR             a FRESH trace store for the 61 copies
    SENSORIUM_RUST_TARGET     this workspace's target, for H6's `cargo test`
    SENSORIUM_CARGO_SENSORIUM how the CLI resolves the driver; the phases
                              re-add it per child, since `plain_env()`
                              strips every `SENSORIUM_*`

Launch it detached and read nothing before the marker exists:

    setsid nohup <ledger>/acceptance-e4p/launch.sh \\
        > <ledger>/acceptance-e4p/logs/e4p.log 2>&1 &

The last act is `<ledger>/acceptance-e4p/e4p.DONE` (or `.FAILED`) carrying
`exit=<n>`, so silence is distinguishable from success.

A DRY RUN IS NOT THE MEASUREMENT
--------------------------------
`--dry-rows <file.json>` replaces §1.1's table with a small one and makes
every artifact a `-dry` sibling: the raw record, the markers and the
assembled record all carry the suffix, `dry_run: true` is stamped through
the record, and the document's tracked `results.json` is never written. The
launcher passes no argv, so the measurement cannot take this path by
accident.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-07-sensorium-rung4-debts"
LEDGER = PLAN
BASE = PLAN / "acceptance-e4p"
LOGS = BASE / "logs"

# Every earlier ledger is evidence and is not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_e4p_phases as eph                                # noqa: E402
import acceptance_e4p_phases2 as eph2                              # noqa: E402
import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_e4p_phases import (guarded, pass_two, phase_h1,    # noqa: E402
                                   phase_h2, phase_h3)
from acceptance_e4p_phases2 import phase_h4, phase_h5, phase_h6    # noqa: E402
from acceptance_e4p_rows import GATE_N, ROWS, TARGETS              # noqa: E402
from acceptance_e4p_schema import SCHEMA_VERSION, assemble_e4p     # noqa: E402
from acceptance_e4p_store import (census_diff, copy_originals,     # noqa: E402
                                  sqlite3_cli, store_census)
from acceptance_e6ppp import LOADS, logs_at                        # noqa: E402,F401
from acceptance_lib import (CLONE_PIN, LOAD_CEILING,               # noqa: E402
                            REPO_DISK_FLOOR_GB, TARGET_DISK_FLOOR_GB,
                            Refused, dir_bytes, free_gb, loadavg,
                            plain_env, sha256_file, step)

# Re-asserted AFTER the imports above, and not only before them: importing
# `acceptance_rung3` points `acceptance_lib.LEDGER`/`LOGS` at the rung-3
# slice's workspace and `acceptance_e6ppp` at the E6‴ document's. The phases
# each open `logs_at(LOGS / "<phase>")` in THEIR OWN namespace, and the entry
# slice's first launch died on exactly that name being unset fourteen
# seconds in.
lib.LEDGER = LEDGER
lib.LOGS = LOGS
eph.LOGS = LOGS
eph2.LOGS = LOGS
e6ppp.LOGS = LOGS
e6ppp.BASE = BASE

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-07-sensorium-rung4-e4p.md")

#: The commit §1 is byte-locked against. A `None` lock REFUSES rather than
#: measuring against a pre-registration that can still be edited. §1 was
#: committed ALONE by Task 0 -- before `harness_threads` existed in
#: `refocus_world.py`, before `find_pair` excluded a child, before
#: `install_shim` hard-linked, before any results file carried
#: `schema_version`, and before this file existed -- and has NEVER been
#: amended, so the original lock and the current one are one sha.
BYTE_LOCK = "2991c3b"
ORIGINAL_LOCK = BYTE_LOCK

RUNNER = "rust/tests/acceptance_e4p.py"
RAW = LEDGER / "results-e4p-raw.json"
RESULTS = (REPO / "docs" / "superpowers" / "acceptance"
           / "2026-09-07-sensorium-rung4-e4p.results.json")

#: The seven locations, and the `paths` keys they land under.
E4P_ENV = {
    "SENSORIUM_DRIVER": "sensorium_driver",
    "SENSORIUM_E4_STORE": "sensorium_e4_store",
    "SENSORIUM_BLOOMERY": "sensorium_bloomery",
    "SENSORIUM_E4P_TARGET": "sensorium_e4p_target",
    "SENSORIUM_DIR": "sensorium_dir",
    "SENSORIUM_RUST_TARGET": "sensorium_rust_target",
}

#: §1.4's ceilings, verbatim: 1800 s per `sensorium refocus`, and the whole
#: LOOP bounded at 1 h 15 min. H6's three commands are not the loop and keep
#: their own; the driver build happens before the loop starts.
REFOCUS_TIMEOUT = 1800
LOOP_BUDGET_S = 4500
CARGO_TIMEOUT = 1800
CORPUS_TIMEOUT = 7200
PYTEST_TIMEOUT = 3600
CARGO_TEST_TIMEOUT = 7200


def out(*args) -> str:
    return subprocess.run([str(a) for a in args], capture_output=True,
                          text=True).stdout.strip()


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


def env_paths_e4p() -> dict:
    """Every location this run touches, from the environment, refused
    TOGETHER when missing -- one launch reports all of them."""
    missing = [k for k in E4P_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(
            "unset environment variable(s): " + ", ".join(missing)
            + " -- this run needs the `cargo-sensorium` binary to rebuild "
              "and measure with, the KEPT E4 store to copy the 61 originals "
              f"out of, the read-only bloomery clone at {CLONE_PIN[:7]}, a "
              "FRESH cargo target for the 61 rebuilds, a FRESH trace store "
              "for the copies, and this workspace's own target for H6's "
              "`cargo test --workspace`")
    return {name: Path(os.environ[key]) for key, name in E4P_ENV.items()}


def e4p_config(paths, rows=None) -> dict:
    """This run's config.

    The corpus target is derived from the E4′ target: §1.4 requires H6's
    corpus target to be fresh and names a path for it but no variable, and a
    location derived from an env var is still not a location compiled into
    this file.
    """
    corpus = os.environ.get("SENSORIUM_CORPUS_TARGET")
    target = paths["sensorium_e4p_target"]
    rows = [list(r) for r in (rows if rows is not None else ROWS)]
    return {
        "corpus_target": (Path(corpus) if corpus
                          else target.parent / (target.name + "-corpus")),
        "corpus_target_from_env": bool(corpus),
        "rows": rows,
        "targets": list(TARGETS),
        "gate_n": len(rows),
        "gate_n_locked": GATE_N,
        "refocus_timeout": REFOCUS_TIMEOUT,
        "loop_budget_s": LOOP_BUDGET_S,
        "corpus_timeout": CORPUS_TIMEOUT,
        "pytest_timeout": PYTEST_TIMEOUT,
        "cargo_test_timeout": CARGO_TEST_TIMEOUT,
        "clone_pin": CLONE_PIN,
        # §1.4: TMPDIR is OBSERVED, and binds nothing here -- there is no
        # `watch` triple in this record. `tempfile.gettempdir()` is recorded
        # beside it because that is the value this process actually resolved,
        # which an unset variable alone does not say.
        "tmpdir_observed": os.environ.get("TMPDIR"),
        "tempfile_gettempdir": tempfile.gettempdir(),
    }


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
    _require_fresh(paths["sensorium_dir"], "SENSORIUM_DIR")
    _require_fresh(paths["sensorium_e4p_target"], "SENSORIUM_E4P_TARGET")
    _require_fresh(cfg["corpus_target"], "H6's corpus target")

    built = build_driver(paths)
    driver = Path(paths["sensorium_driver"])
    target_free = free_gb(paths["sensorium_e4p_target"].parent)
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{paths['sensorium_e4p_target']}: {target_free:.1f} "
                      f"GB free < {TARGET_DISK_FLOOR_GB} GB floor")

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
        "sensorium_version": out(
            str(REPO / ".venv" / "bin" / "python"), "-c",
            "import sensorium; print(sensorium.__version__)"),
        "sensorium_version_metadata": out(
            str(REPO / ".venv" / "bin" / "python"), "-c",
            "import importlib.metadata as m; print(m.version('sensorium'))"),
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


# --------------------------------------------------------------------- main

def _stops(res: dict) -> list[str]:
    """§1.4's kill rules 1-3 and 5, by their WORDS.

    Every one of these is read AFTER a number: the partition, the verdict,
    the pair and the instrument's own `schema_version` are all measured
    before they can fail, so each is a STOP -- the numbers already read
    stand -- and never a relaunch.
    """
    stops = []
    h1 = res.get("raw_h1") or {}
    if h1 and h1.get("partition_as_predicted") is False:
        stops.append(
            f"H1 (kill 1): the partition is not §1.2's -- granted "
            f"{h1.get('granted_n')} of {len(h1.get('granted') or []) or '?'} "
            f"expected {h1.get('expected_granted_n')}; withheld only here "
            f"{h1.get('withheld_only_here')}; withheld missing "
            f"{h1.get('withheld_missing')}; count mismatches "
            f"{h1.get('withheld_count_mismatches')}")
    h2 = res.get("raw_h2") or {}
    if h2 and h2.get("match_as_predicted") is False:
        stops.append(f"H2 (kill 2): {len(h2.get('non_match') or [])} pair(s) "
                     f"did not MATCH: {h2.get('non_match')}")
    h3 = res.get("raw_h3") or {}
    if h3 and h3.get("pairs_as_predicted") is False:
        stops.append(f"H3 (kill 3): {len(h3.get('not_one') or [])} pair "
                     f"count(s) were not 1: {h3.get('not_one')}")
    h5 = res.get("raw_h5") or {}
    if h5 and h5.get("as_predicted") is False:
        stops.append(
            "H5 (a STOP of the instrument, not of the subject -- the locked "
            "§1's 'kill 4' beside this sentence is a cross-reference "
            "erratum; the WORDS say STOP, which is rule 5): "
            f"raw={h5.get('raw_schema_version')} "
            f"assembled={h5.get('assembled_schema_version')}, expected "
            "e4p/1")
    cl = res.get("cleanup") or res.get("cleanup_after_failure") or {}
    if cl.get("kept_store_unchanged") is False:
        stops.append(
            "§1.3 (a STOP; the locked text's 'kill 4' here is the same "
            "cross-reference erratum): the KEPT store changed during the "
            f"run -- {cl.get('kept_census_differences')}")
    h6 = res.get("raw_h6") or {}
    if h6 and h6.get("all_green") is False:
        stops.append(
            f"H6: corpus rc {(h6.get('corpus') or {}).get('rc')}, pytest rc "
            f"{(h6.get('python') or {}).get('rc')}, cargo rc "
            f"{(h6.get('cargo') or {}).get('rc')}")
    return stops


def _partial_json(res: dict) -> str:
    """What CAN be serialised, when the whole record cannot."""
    safe = {}
    for key, value in res.items():
        try:
            json.dumps({key: value}, default=str)
            safe[key] = value
        except (TypeError, ValueError):
            safe[key] = f"<unserialisable {type(value).__name__}>"
    return json.dumps(safe, indent=2, default=str)


def main(argv) -> int:
    dry = None
    if "--dry-rows" in argv:
        dry = Path(argv[argv.index("--dry-rows") + 1])
    suffix = "-dry" if dry else ""
    raw_path = (RAW.with_name(RAW.stem + suffix + RAW.suffix) if dry
                else RAW)
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in (f"e4p{suffix}.DONE", f"e4p{suffix}.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "schema_version": SCHEMA_VERSION,
                 "runner": RUNNER, "dry_run": bool(dry),
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = kept_before = None
    try:
        res["byte_lock"] = check_byte_lock()
        paths = env_paths_e4p()
        rows = json.loads(dry.read_text()) if dry else None
        cfg = e4p_config(paths, rows)
        res["config"] = {k: (str(v) if isinstance(v, Path) else v)
                         for k, v in cfg.items()}
        if dry:
            step(f"DRY RUN: {len(cfg['rows'])} row(s) from {dry}; no tracked "
                 "results.json is written and every artifact is a `-dry` "
                 "sibling")
        # §1.2's numbers, recorded BEFORE any phase runs, so the record
        # publishes what was predicted even for a phase that never ran.
        res["predictions"] = {"source": "§1.1 and §1.2", "gate_n": GATE_N}
        pins = preflight(paths, cfg)
        res["pins"] = pins
        # §1.3's proof, opened BEFORE the first copy reads the kept store.
        kept_before = store_census(paths["sensorium_e4_store"])
        res["kept_census_before"] = kept_before
        res["store"] = copy_originals(paths["sensorium_e4_store"],
                                      paths["sensorium_dir"], cfg["rows"])

        two = pass_two(paths, cfg)
        res["raw_pass2"] = two
        first = next((r.get("driver_version_from_the_trace")
                      for r in two["refocuses"]
                      if r.get("driver_version_from_the_trace")), None)
        pins["driver_version_from_the_trace"] = first
        res["raw_h1"] = phase_h1(two)
        res["raw_h2"] = phase_h2(two)
        res["raw_h3"] = phase_h3(two)
        res["raw_h4"] = phase_h4(paths, two)
        # H5 reads back what was ACTUALLY stamped, from this record's own
        # objects -- never re-asserted from a constant.
        res["raw_h5"] = phase_h5(res.get("schema_version"),
                                 (assemble_e4p(res).get("assembled") or {}
                                  ).get("schema_version")
                                 if res.get("schema_version") else None)
        # H6 LAST: `cargo test --workspace` shares the driver's target and
        # is the one thing here that could relink the binary every other
        # phase measured with.
        #
        # A DRY run does not run it. H6 asks whether THIS repository still
        # answers as it did, which a shortened row table says nothing about
        # -- and its three commands cost more than the rest of a dry run put
        # together. Left absent rather than faked: the H6 cells then publish
        # `null` with "the phase did not run", which is the shape a dry run
        # exists to check.
        if dry:
            step("DRY RUN: H6 is NOT run; its cells publish null with a "
                 "reason, which is the artifact this dry run checks")
        else:
            res["raw_h6"] = phase_h6(paths, cfg)
        res["cleanup"] = cleanup(paths, cfg, pins, kept_before)
        stops = _stops(res)
        if stops:
            res["stop"] = "; ".join(stops)
            rc = rc or 7
        if two.get("budget_exhausted"):
            res["bound_reached"] = (
                f"§1.4's 1 h 15 min loop bound was reached; "
                f"{len(two['budget_exhausted'])} invocation(s) were NOT run: "
                f"{two['budget_exhausted'][:5]}"
                + (" …" if len(two["budget_exhausted"]) > 5 else ""))
            rc = rc or 8
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
            res["cleanup_after_failure"] = cleanup(paths, cfg, pins,
                                                   kept_before)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        raw_path.write_text(json.dumps(res, indent=2, default=str))
    except (TypeError, ValueError):
        # The last act of a long run, and it must not be able to lose the
        # run: `default=` does not apply to dict KEYS, so one unserialisable
        # key would raise here -- outside every try -- and leave no raw
        # record, no `results.json` and NO MARKER.
        import traceback
        trace = traceback.format_exc()
        (LOGS / "raw-json-error.txt").write_text(trace)
        res["raw_json_error"] = trace.strip().splitlines()[-1]
        step("writing the raw record FAILED (logs/raw-json-error.txt); "
             "writing what CAN be serialised instead")
        raw_path.write_text(_partial_json(res))
        rc = rc or 6
    if res.get("refused"):
        # A refusal measured NOTHING. Assembling would write a TRACKED
        # `results.json` full of not-measured cells into `docs/`, where the
        # next reader would take it for a record of a run.
        step("REFUSED before any measurement: no results.json is assembled "
             "and nothing is rendered; the raw record and the marker are the "
             "evidence")
    else:
        try:
            assemble_only(res, dry=bool(dry))
            if not dry:
                render_only()
        except Exception:                                      # noqa: BLE001
            import traceback
            (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
            step("assemble/render FAILED (logs/assemble-error.txt); the raw "
                 "record is intact")
            rc = rc or 5
    why = (res.get("refused") or res.get("stop") or res.get("bound_reached")
           or res.get("error") or "")
    marker = f"e4p{suffix}." + ("DONE" if rc == 0 else "FAILED")
    (BASE / marker).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n{why}\n")
    step(f"done rc={rc}; raw facts at {raw_path}")
    return rc


def assemble_only(raw: dict | None = None, dry: bool = False) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts.

    A DRY assembly writes a `-dry` sibling in the ledger and never the
    tracked file: a dry run's numbers must not be able to land where a
    reader would take them for the measurement.
    """
    path = RAW.with_name(RAW.stem + "-dry" + RAW.suffix) if dry else RAW
    if raw is None:
        raw = json.loads(path.read_text())
    record = assemble_e4p(raw)
    dest = (LEDGER / "results-e4p-dry.results.json" if dry else RESULTS)
    dest.write_text(json.dumps(record, indent=2, default=str))
    step(f"assembled -> {dest}")
    return 0


def render_only() -> int:
    """`--render` rewrites §2-§5 of the acceptance document from the
    assembled record. Never run for a dry assembly."""
    import render_e4p
    return render_e4p.main([str(RESULTS)])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
