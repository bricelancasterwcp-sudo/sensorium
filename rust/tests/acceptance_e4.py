#!/usr/bin/env python3
"""The E4 runner: the RE-RUN path measured ONCE over the 61 pager tests of
`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md` §1.

WHAT THIS RUNNER DOES
---------------------
Two passes over §1.1's 61 tests, in §1.1's order, against the read-only
bloomery clone at `e209ed9`:

    pass 1  cargo sensorium test -p bloomery-daemon --test <file> -- <name> --exact
    pass 2  sensorium refocus <run> --focus <name>

Pass 1 records the original at the driver's default tier; pass 2 asks the
READER to re-run it one flag deeper and to verify that what came back was the
same execution. Then H1-H7 are asked of the 61 pairs. Every invocation of
either pass carries a 1800 s ceiling and the whole loop a 2-hour one, so a
bound reached is a RECORDED fact rather than an exception that would take the
endpoints already read down with it.

THE RULES THAT RUN THROUGH IT (the E9 family's, unchanged)
-----------------------------------------------------------
* **§1 is the contract, and it is byte-locked.** `check_byte_lock` refuses
  to start unless the locked range is byte-identical to the commit that
  locked it. §1's LENS was amended once (ruling R-H1) after the original
  lock and BEFORE the instrument existed, so BOTH shas are carried -- the
  original `8e7d837` and the amended `413f601` -- and the record states
  `amended_after_the_original_lock` as a fact rather than as a claim in
  prose. No endpoint, method, derivation or table row moved.
* **No endpoint is ever filled from a prediction.** §1's numbers -- the 61
  names, the expected-MATCH list, the three `watch` triples -- are in the
  room, and a headline that borrowed from one could not fail. They enter as
  COMPARISON TARGETS under their own names; a phase that did not run
  publishes `null` with a reason (`acceptance_e4_schema`, tested in
  `tests/test_acceptance_e4_record.py`).
* **An UNVERIFIABLE check is never counted as verified.** H4's verified
  counts and its unverifiable counts are two numbers that are never summed.
* **Every location is an environment variable.** No box path appears in any
  module of this instrument, and the five below are refused TOGETHER when
  missing so one launch reports all of them.

THE LOCATIONS
-------------
    SENSORIUM_DRIVER        the `cargo-sensorium` binary, by absolute path;
                            the runner REBUILDS it from this branch's HEAD
                            into its own target before measuring (§1.4)
    SENSORIUM_BLOOMERY      the read-only clone, pinned at e209ed9
    SENSORIUM_E4_TARGET     a FRESH CARGO_TARGET_DIR for the 61 pairs
    SENSORIUM_DIR           a FRESH trace store for them
    SENSORIUM_RUST_TARGET   this workspace's target, for H7's `cargo test`
    SENSORIUM_CORPUS_TARGET optional; H7's FRESH corpus target. §1.4 requires
                            it to be fresh but names no variable, so when it
                            is unset the runner derives `<E4 target>-corpus`.

`SENSORIUM_CARGO_SENSORIUM` is set by the launcher because the CLI resolves
the driver through it; the phases re-add it for each refocus child, since
`plain_env()` strips every `SENSORIUM_*`.

Launch it detached and read nothing before the marker exists:

    setsid nohup <ledger>/acceptance-e4/launch.sh \\
        > <ledger>/acceptance-e4/logs/e4.log 2>&1 &

The last act is `<ledger>/acceptance-e4/e4.DONE` (or `.FAILED`) carrying
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
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-07-sensorium-rung4-refocus"
LEDGER = PLAN
BASE = PLAN / "acceptance-e4"
LOGS = BASE / "logs"

# Every earlier ledger is evidence and is not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_e4_phases as eph                                 # noqa: E402
import acceptance_e4_phases2 as eph2                               # noqa: E402
import acceptance_e6ppp as e6ppp                                   # noqa: E402
import acceptance_phases as ph                                     # noqa: E402
import acceptance_rung3 as rung3                                   # noqa: E402
from acceptance_e4_phases import (guarded, pass_one,               # noqa: E402
                                  pass_two, phase_h1, phase_h2,
                                  phase_h3)
from acceptance_e4_phases2 import (phase_h4, phase_h5,             # noqa: E402
                                   phase_h6, phase_h7, watch_triples)
from acceptance_e4_read import temp_root                           # noqa: E402
from acceptance_e4_tests import (GATE_N, TARGETS, TESTS,           # noqa: E402
                                 TESTS_SUBDIR)
from acceptance_e6ppp import LOADS, logs_at                        # noqa: E402,F401
from acceptance_lib import (CLONE_PIN, LOAD_CEILING,               # noqa: E402
                            REPO_DISK_FLOOR_GB, TARGET_DISK_FLOOR_GB,
                            Refused, dir_bytes, free_gb, loadavg,
                            plain_env, sha256_file, step)

# Re-asserted AFTER the imports above, and not only before them: importing
# `acceptance_rung3` points `acceptance_lib.LEDGER`/`LOGS` at the rung-3
# slice's workspace and `acceptance_e6ppp` at the E6‴ document's. The phases
# each open `logs_at(LOGS / "<phase>")` in THEIR OWN namespace, and the entry
# slice's first launch died on exactly that name being unset fourteen seconds
# in. `e6ppp.LOGS`/`BASE` move too, because `logs_at` resolves them where it
# is defined.
lib.LEDGER = LEDGER
lib.LOGS = LOGS
ph.LOGS = LOGS
eph.LOGS = LOGS
eph2.LOGS = LOGS
e6ppp.LOGS = LOGS
e6ppp.BASE = BASE

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-07-sensorium-rung4-e4.md")

#: The commit §1 is byte-locked against NOW: the AMENDED lens. A `None` lock
#: REFUSES rather than measuring against a pre-registration that can still be
#: edited.
#:
#: §1 was amended once on 2026-09-07, after the original lock and BEFORE the
#: instrument existed (ruling R-H1), to state the survey's SCOPE, to give
#: §1.2's three-test hazard a DISCRIMINATOR, and to correct the `.collect()`
#: citation lines. No endpoint, no method, no derivation and no table row
#: moved: `tests/test_acceptance_e4.py` asserts row identity between the two
#: commits.
BYTE_LOCK = "413f601"
#: The ORIGINAL lock, committed alone by Task 0 before the instrument
#: existed. Both shas are recorded (`original_lock_sha256`,
#: `amended_after_the_original_lock`) so the amendment is a visible fact of
#: the record rather than a claim in prose.
ORIGINAL_LOCK = "8e7d837"

RUNNER = "rust/tests/acceptance_e4.py"
RAW = LEDGER / "results-e4-raw.json"
RESULTS = (REPO / "docs" / "superpowers" / "acceptance"
           / "2026-09-07-sensorium-rung4-e4.results.json")

#: §1.1's hand enumeration and the seven `--test` targets, in a module of
#: their own (`acceptance_e4_tests.py`): they are the one piece of DATA in
#: this instrument -- a transcription of the byte-locked pre-registration --
#: and `tests/test_acceptance_e4.py` derives the same table from the locked
#: document and asserts it equal, row for row and in order. Re-exported here
#: so every caller's spelling is the runner's.

#: The five locations, and the `paths` keys they land under.
E4_ENV = {
    "SENSORIUM_DRIVER": "sensorium_driver",
    "SENSORIUM_BLOOMERY": "sensorium_bloomery",
    "SENSORIUM_E4_TARGET": "sensorium_e4_target",
    "SENSORIUM_DIR": "sensorium_dir",
    "SENSORIUM_RUST_TARGET": "sensorium_rust_target",
}

#: §1.4's ceilings, verbatim: 1800 s per `cargo sensorium` invocation and
#: 1800 s per `sensorium refocus`, with the whole loop bounded at 2 hours.
#: The reader ceiling is this family's own (a `watch` over one test binary's
#: trace that has not answered in two minutes is a fact worth recording).
CARGO_TIMEOUT = 1800
REFOCUS_TIMEOUT = 1800
READER_TIMEOUT = 120
#: The 2-hour bound, applied to the LOOP: pass 1 and pass 2 together. H7's
#: three commands are not the loop and keep their own ceilings, and the
#: driver build happens before the loop starts. Reached, it is a recorded
#: fact per test (`budget_exhausted`) and a `.FAILED` marker, never a
#: silently shortened pass.
LOOP_BUDGET_S = 7200
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


def env_paths_e4() -> dict:
    """Every location this run touches, from the environment, refused
    together when missing -- one launch reports all of them."""
    missing = [k for k in E4_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(
            "unset environment variable(s): " + ", ".join(missing)
            + " -- this run needs the `cargo-sensorium` binary to rebuild "
              "and measure with, the read-only bloomery clone at "
              f"{CLONE_PIN[:7]}, a FRESH cargo target for the 61 pairs, a "
              "FRESH trace store for them, and this workspace's own target "
              "for H7's `cargo test --workspace`")
    return {name: Path(os.environ[key]) for key, name in E4_ENV.items()}


def e4_config(paths) -> dict:
    """This run's config. The corpus target is derived from the E4 target
    when `SENSORIUM_CORPUS_TARGET` is unset: §1.4 requires H7's corpus target
    to be fresh but names no variable for it, and a location derived from an
    env var is still not a location compiled into this file."""
    corpus = os.environ.get("SENSORIUM_CORPUS_TARGET")
    e4t = paths["sensorium_e4_target"]
    return {
        "corpus_target": (Path(corpus) if corpus
                          else e4t.parent / (e4t.name + "-corpus")),
        "corpus_target_from_env": bool(corpus),
        "tests": [list(t) for t in TESTS],
        "targets": list(TARGETS),
        "gate_n": GATE_N,
        "tests_dir": str(Path(paths["sensorium_bloomery"], *TESTS_SUBDIR)),
        "cargo_timeout": CARGO_TIMEOUT,
        "refocus_timeout": REFOCUS_TIMEOUT,
        "reader_timeout": READER_TIMEOUT,
        "loop_budget_s": LOOP_BUDGET_S,
        "corpus_timeout": CORPUS_TIMEOUT,
        "pytest_timeout": PYTEST_TIMEOUT,
        "cargo_test_timeout": CARGO_TEST_TIMEOUT,
        "clone_pin": CLONE_PIN,
        # §1.4: `TMPDIR` is expected UNSET, which is what makes
        # `std::env::temp_dir()` `/tmp` and W1/W4 derivable at all. It is
        # OBSERVED here, and every literal below is built from it, so a run
        # under a set `TMPDIR` reads the same predictions with the prefix
        # substituted rather than reading the wrong ones silently.
        "tmpdir_observed": os.environ.get("TMPDIR"),
        "temp_root": temp_root(os.environ.get("TMPDIR")),
    }


def build_driver_e4(paths) -> dict:
    """`cargo build [-r] -p cargo-sensorium`, run BY the runner, and the
    record of what it built from (§1.4's `built_from`).

    The profile is read from the binary's own parent directory
    (`<target>/<debug|release>/cargo-sensorium` is cargo's layout), so the
    build lands exactly where `SENSORIUM_DRIVER` points instead of
    refreshing the other profile and reporting `rebuilt: False` about a
    stale binary. A path whose parent is neither is refused rather than
    guessed at. The pre-repair-binary trap of the E6⁗ record is why §1.4
    makes the runner build the driver rather than trust a path.
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
        res = guarded(cmd, REPO / "rust", "built-from.log",
                      plain_env() | {"CARGO_TARGET_DIR": str(target)},
                      CARGO_TIMEOUT, "built-from")
    after = sha256_file(driver)
    rec = {
        "repo_head_at_build": out("git", "-C", str(REPO), "rev-parse", "HEAD"),
        "repo_porcelain_at_build": out("git", "-C", str(REPO), "status",
                                       "--porcelain"),
        "command": " ".join(cmd), "profile": profile,
        "cargo_target_dir": str(target),
        "cargo_rc": res["rc"], "cargo_wall_s": round(res["wall"], 3),
        "timed_out": res["timed_out"], "kill_s": res["kill_s"],
        "driver": str(driver),
        "driver_sha256_before_build": before,
        "driver_sha256_after_build": after,
        "rebuilt": before != after,
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


# ------------------------------------------------------------- the preflight


def _require_fresh(path: Path, what: str) -> None:
    if path.exists() and any(path.iterdir()):
        raise Refused(
            f"{what} {path} is not empty; §1.4 says FRESH, and a warm one "
            "would answer with another run's artifacts")
    path.mkdir(parents=True, exist_ok=True)


def check_the_61_names(paths, cfg) -> dict:
    """§1.1's table, re-derived from the clone's own sources.

    A mismatch is a REFUSAL: the 61 argv lines pass 1 runs come from this
    table, so a table that no longer describes the clone would run 61
    commands about something else and report the result under §1.1's names.
    The derivation is recorded whole, difference by difference, so a refusal
    NAMES the rows rather than reporting a count.
    """
    from acceptance_e4_read import enumerate_tests, table_diff
    derived = enumerate_tests(Path(cfg["tests_dir"]), TARGETS)
    diff = table_diff(derived["rows"], [tuple(t) for t in TESTS])
    rec = {"derived": {k: v for k, v in derived.items() if k != "per_file"},
           "per_file_counts": derived["counts"],
           "ignore_attrs": derived["ignore_attrs"],
           "should_panic_attrs": derived["should_panic_attrs"],
           "unmatched": derived["unmatched"],
           "diff": diff, "expected_total": len(TESTS)}
    if derived["missing_files"]:
        raise Refused("the clone has no such test file(s): "
                      + ", ".join(derived["missing_files"]))
    if not diff["equal"]:
        raise Refused(
            f"the clone's `#[test]` enumeration is not §1.1's table "
            f"({diff['derived_total']} vs {diff['expected_total']}): only in "
            f"the clone {diff['only_in_the_clone']}; only in §1.1 "
            f"{diff['only_in_the_document']}; moved {diff['line_moved']}; "
            f"same order {diff['same_order']}")
    # §1.1's own survey facts, re-measured rather than trusted: an ignored
    # test would not RUN under `--exact` and would have to be pre-registered
    # as EXCLUDED with N dropping by one.
    if derived["ignore_attrs"] or derived["should_panic_attrs"]:
        raise Refused(
            f"§1.1 records 0 `#[ignore]` and 0 `#[should_panic]` over the "
            f"seven files; the clone has {derived['ignore_attrs']} and "
            f"{derived['should_panic_attrs']}, so N is not 61")
    step(f"§1.1 re-derived from the clone: {derived['total']} tests over "
         f"{len(TARGETS)} files, identical to the locked table "
         f"(order too: {diff['same_order']})")
    return rec


def preflight_e4(paths, cfg) -> dict:
    """What THIS run touches, and nothing else.

    Refuses on: the machine's load; either disk floor; a clone that is not at
    §1.4's pin or is not porcelain-clean; a clone whose `#[test]` enumeration
    is not §1.1's; a driver that will not build from HEAD; a `SENSORIUM_DIR`,
    an E4 target or a corpus target that is not fresh.
    """
    step("rung-4 refocus (E4) preflight")
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
    names = check_the_61_names(paths, cfg)

    # The cheap refusals FIRST: a misconfigured launch must not spend a
    # driver build before finding out that its target is not fresh.
    _require_fresh(paths["sensorium_dir"], "SENSORIUM_DIR")
    _require_fresh(paths["sensorium_e4_target"], "SENSORIUM_E4_TARGET")
    _require_fresh(cfg["corpus_target"], "H7's corpus target")

    built = build_driver_e4(paths)
    driver = Path(paths["sensorium_driver"])
    target_free = free_gb(paths["sensorium_e4_target"])
    if target_free < TARGET_DISK_FLOOR_GB:
        raise Refused(f"{paths['sensorium_e4_target']}: {target_free:.1f} GB "
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
        "tests_dir": cfg["tests_dir"],
        "the_61_names": names,
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
        "e4_target": str(paths["sensorium_e4_target"]),
        "rust_target": str(paths["sensorium_rust_target"]),
        "corpus_target": str(cfg["corpus_target"]),
        "corpus_target_from_env": cfg["corpus_target_from_env"],
        "tmpdir_observed": cfg["tmpdir_observed"],
        "temp_root": cfg["temp_root"],
        "tmpdir_reading": (
            "TMPDIR was unset, so `std::env::temp_dir()` is `/tmp` and W1 "
            "and W4 read as §1.3 derives them"
            if cfg["tmpdir_observed"] is None else
            f"TMPDIR was set to {cfg['tmpdir_observed']!r}, so §1.4's "
            f"substituted reading was taken: every predicted literal reads "
            f"against {cfg['temp_root']}/…"),
        "sensorium_tier": (
            "unset -- §1.4 leaves the coarse tier at its default `call` for "
            "every pass-1 recording, so an original and its refocused pair "
            "differ only by the added `--focus`"),
        "invocation_log": (
            "NOT silenced: SENSORIUM_NO_INVOCATION_LOG is unset, so every "
            "reader call this record makes appends a row to the store's "
            "`invocations.jsonl`, and the count is recorded at the end"),
        # Filled after pass 1: §1.4 reads every version token from the
        # TRACE's own meta, never from this file.
        "versions_from_the_first_trace": None,
    }
    step(f"preflight ok: load={load} clone={head[:12]} driver="
         f"{(pins['driver_sha256'] or '?')[:12]} target free "
         f"{target_free:.1f} GB; TMPDIR={cfg['tmpdir_observed']!r}")
    return pins


def cleanup_e4(paths, cfg, pins) -> dict:
    """What the run left behind, and the clone put back on the pin."""
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
    # `None` is "there is nothing there to count", `0` is "counted, and
    # zero". A store the run never created and a store it created and left
    # empty are different facts about the run.
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
        "store_bytes": dir_bytes(sdir) if sdir.is_dir() else None,
        "traces_recorded": (len(list(traces.glob("*.db")))
                            if traces.is_dir() else None),
        "invocations_jsonl_lines": (len(log.read_text().splitlines())
                                    if log.is_file() else None),
        "absent_after_the_run": [
            str(pth) for pth, ok in (
                (sdir, sdir.is_dir()), (traces, traces.is_dir()),
                (log, log.is_file())) if not ok],
        "e4_target_bytes": dir_bytes(paths["sensorium_e4_target"])
        if paths["sensorium_e4_target"].is_dir() else None,
        "corpus_target_bytes": dir_bytes(cfg["corpus_target"])
        if cfg["corpus_target"].is_dir() else None,
        "repo_porcelain_after": out("git", "-C", str(REPO), "status",
                                    "--porcelain"),
        "repo_disk_free_gb_after": round(free_gb(REPO), 2),
        "target_disk_free_gb_after": round(
            free_gb(paths["sensorium_e4_target"]), 2)
        if paths["sensorium_e4_target"].is_dir() else None,
        "finished": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"cleanup: clone HEAD {c['clone_head_after'][:12]}, Cargo.lock moved "
         f"{moved} back-on-the-pin {c['clone_cargo_lock_back_on_the_pin']}; "
         f"{c['traces_recorded']} trace(s), {c['store_bytes']} store bytes; "
         f"driver unchanged {c['driver_unchanged']}")
    return c


# --------------------------------------------------------------------- main


def _partial_json(res: dict) -> str:
    """Whatever of the record CAN be serialised, key by key, with the keys
    that could not NAMED. A run that measured for two hours must lose one
    value to a serialisation defect, not all of them."""
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
    """`cfg` as the record stores it: paths stringified, sets sorted."""
    out_ = {}
    for k, v in cfg.items():
        if isinstance(v, Path):
            out_[k] = str(v)
        elif isinstance(v, (set, frozenset)):
            out_[k] = sorted(v)
        else:
            out_[k] = v
    return out_


def _stops(res: dict) -> list[str]:
    """§1's two STOP classes, each under its own name.

    Kill 1 is a focused BUILD FAILURE (H2's `cargo` non-zero with no libtest
    summary line in the re-run's log); kill 2 is a REFUSED AFTER the rerun
    (H3). A pre-rerun refusal is neither -- it is H1's number, recorded with
    its verbatim sentence -- and collapsing the three would stop the rung on
    a mistyped focus.
    """
    stops = []
    h2 = res.get("raw_h2") or {}
    h3 = res.get("raw_h3") or {}
    if h2.get("build_failures"):
        stops.append("§1 kill 1: focused build failure(s) on "
                     f"{h2['build_failures']} -- no fallback to an "
                     "unfocused build, no retry under a narrower focus, no "
                     "skipped test; the pattern that failed is the finding")
    if h3.get("refused_after_rerun"):
        stops.append("§1 kill 2: REFUSED after the rerun on "
                     f"{h3['refused_after_rerun']} -- the instrument or the "
                     "pairing, not the subject")
    return stops


def main(argv) -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in ("e4.DONE", "e4.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "runner": RUNNER,
                 "document": str(DOC.relative_to(REPO)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = None
    try:
        res["byte_lock"] = check_byte_lock()
        paths = env_paths_e4()
        cfg = e4_config(paths)
        res["config"] = _cfg_json(cfg)
        # §1's triples and its expected-MATCH list, recorded BEFORE any phase
        # runs, so the record publishes what was predicted even for a phase
        # that never ran. They are comparison targets and are never a value a
        # cell can fall back to (`acceptance_e4_schema._predictions`).
        res["predictions"] = {
            "expected_match": [n for _t, _l, n in TESTS],
            "gate_n": GATE_N,
            "hazard_tests": list(eph.HAZARD_TESTS),
            "watch_triples": [{k: t[k] for k in
                               ("id", "of", "at", "expr", "predicted_class",
                                "predicted_exit", "line", "gate")}
                              for t in watch_triples(cfg)],
        }
        pins = preflight_e4(paths, cfg)
        res["pins"] = pins

        one = pass_one(paths, cfg)
        res["raw_pass1"] = one
        pins["versions_from_the_first_trace"] = one.get("versions")
        two = pass_two(paths, cfg, one)
        res["raw_pass2"] = two
        res["raw_h1"] = phase_h1(two)
        res["raw_h2"] = phase_h2(one, two)
        res["raw_h3"] = phase_h3(paths, cfg, one, two)
        res["raw_h4"] = phase_h4(two)
        res["raw_h5"] = phase_h5(paths, cfg, two)
        res["raw_h6"] = phase_h6(paths, one, two)
        # H7 LAST: `cargo test --workspace` shares the driver's target and is
        # the one thing in this run that could relink the binary every other
        # phase measured with.
        res["raw_h7"] = phase_h7(paths, cfg)
        res["cleanup"] = cleanup_e4(paths, cfg, pins)
        stops = _stops(res)
        if stops:
            res["stop"] = "; ".join(stops)
            rc = rc or 7
        exhausted = ((one.get("budget_exhausted") or [])
                     + (two.get("budget_exhausted") or []))
        if exhausted:
            res["bound_reached"] = (
                f"§1.4's 2-hour loop bound was reached; {len(exhausted)} "
                f"invocation(s) were NOT run: {exhausted[:5]}"
                + (" …" if len(exhausted) > 5 else ""))
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
            res["cleanup_after_failure"] = cleanup_e4(paths, cfg, pins)
        except Exception:                                      # noqa: BLE001
            pass
    res["arm_loads"] = list(LOADS)
    res["steps"] = lib.STEPS
    res["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        RAW.write_text(json.dumps(res, indent=2, default=str))
    except (TypeError, ValueError):
        # The last act of a two-hour run, and it must not be able to lose the
        # run: `default=` does not apply to dict KEYS, so one unserialisable
        # key would raise here -- outside every try -- and leave no raw
        # record, no `results.json` and NO MARKER.
        import traceback
        trace = traceback.format_exc()
        (LOGS / "raw-json-error.txt").write_text(trace)
        res["raw_json_error"] = trace.strip().splitlines()[-1]
        step("writing the raw record FAILED (logs/raw-json-error.txt); "
             "writing what CAN be serialised instead")
        RAW.write_text(_partial_json(res))
        rc = rc or 6
    if res.get("refused"):
        # A refusal measured NOTHING. Assembling would write a TRACKED
        # `results.json` (and a rendered §2/§3) full of not-measured cells
        # into `docs/`, where the next reader would take it for a record of a
        # run. The raw record and the marker are the whole evidence.
        step("REFUSED before any measurement: no results.json is assembled "
             "and nothing is rendered; the raw record and the marker are the "
             "evidence")
    else:
        try:
            assemble_only(res)
            render_only()
        except Exception:                                      # noqa: BLE001
            import traceback
            (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
            step("assemble/render FAILED (logs/assemble-error.txt); the raw "
                 "record is intact")
            rc = rc or 5
    why = (res.get("refused") or res.get("stop") or res.get("bound_reached")
           or res.get("error") or "")
    (BASE / ("e4.DONE" if rc == 0 else "e4.FAILED")).write_text(
        f"exit={rc}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n{why}\n")
    step(f"done rc={rc}; raw facts at {RAW}")
    return rc


def assemble_only(raw: dict | None = None) -> int:
    """`--assemble` derives the document's `results.json` from the raw facts
    already on disk, under the committed schema. It re-runs no phase and
    reads no new number."""
    from acceptance_e4_schema import assemble_e4                   # noqa: PLC0415
    if raw is None:
        raw = json.loads(RAW.read_text())
    doc = assemble_e4(raw)
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
    import render_e4                                              # noqa: PLC0415
    doc = json.loads(RESULTS.read_text())
    text = "\n".join(render_e4.environment(doc) + [""]
                     + render_e4.results(doc))
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
