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
import acceptance_e4p_preflight as pre                            # noqa: E402
from acceptance_e4p_phases import (guarded, pass_two, phase_h1,    # noqa: E402,F401
                                   phase_h2, phase_h3)
from acceptance_e4p_preflight import (_require_fresh, build_driver,  # noqa: E402,F401
                                      cargo_running, cleanup, clone_git,
                                      mark_numbers_read, out, preflight,
                                      transform_version)
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
pre.LOGS = LOGS
e6ppp.LOGS = LOGS
e6ppp.BASE = BASE

DOC = (REPO / "docs" / "superpowers" / "acceptance"
       / "2026-09-07-sensorium-rung4-e4p.md")

#: The commit §1 is byte-locked against NOW: the AMENDED §1. A `None` lock
#: REFUSES rather than measuring against a pre-registration that can still
#: be edited, and this one refuses on anything but amendment A1's bytes.
#:
#: §1 was amended ONCE, on 2026-09-07, after the original lock and BEFORE
#: any E4′ number was read: §1.5 (amendment A1) records what the preflight
#: found -- that §1.3's FRESH `CARGO_TARGET_DIR` makes the licence's env
#: clause fire on all 61 pairs for a reason unrelated to R1 -- the ruling
#: that a re-run from another target directory is a normal use of the tool,
#: and the three launch-environment variables the launcher pins. The
#: expectation, the H-table and the kills did not move.
BYTE_LOCK = "d5efaab"
#: The ORIGINAL lock: §1 as Task 0 committed it ALONE, before
#: `harness_threads` existed in `refocus_world.py`, before `find_pair`
#: excluded a child, before `install_shim` hard-linked, before any results
#: file carried `schema_version`, and before this file existed.
#:
#: Carried BESIDE the current lock, never replaced by it. The record
#: publishes both shas and `amended_after_the_original_lock`, so the
#: amendment is a checkable fact of the record rather than a claim in
#: prose -- a runner that dropped the original would make a post-lock edit
#: indistinguishable from no edit at all.
ORIGINAL_LOCK = "2991c3b"

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


# --------------------------------------------------------------------- main


def _stops(res: dict) -> list[str]:
    """§1.4's kill rules 1-3 and 5, by their WORDS.

    Every one of these is read AFTER a number: the partition, the verdict,
    the pair and the instrument's own `schema_version` are all measured
    before they can fail, so each is a STOP -- the numbers already read
    stand -- and never a relaunch.
    """
    stops = []
    # The KILL first, in the words of the rule that applies. A row killed at
    # its 1800 s ceiling leaves its licence unread, which takes H1's
    # partition to False -- and the first line Task 6 reads must not
    # attribute a kill-4/5 event to kill 1. §1.4's rules 4 and 5 are told
    # apart by `numbers_read` and by nothing else.
    two = res.get("raw_pass2") or {}
    killed, missing = two.get("killed") or [], two.get("budget_exhausted") or []
    if killed or missing:
        what = []
        if killed:
            what.append(f"{len(killed)} invocation(s) were KILLED at the "
                        f"1800 s ceiling ({killed[:3]})")
        if missing:
            what.append(f"{len(missing)} invocation(s) were never run -- the "
                        f"1 h 15 min loop bound was reached ({missing[:3]})")
        if res.get("numbers_read"):
            stops.append(
                "; ".join(what) + ". A `.FAILED` marker AFTER a number had "
                "already been read is a STOP and the numbers already read "
                "stand (§1.4's rule 5, by its words). Every endpoint "
                "boolean below is over fewer than the 61, and the assembled "
                "record nulls each of them with this reason")
        else:
            stops.append(
                "; ".join(what) + ". A `.FAILED` marker BEFORE any number "
                "had been read is infrastructure (§1.4's rule 4, by its "
                "words): the run is archived, the fresh locations are "
                "emptied, the 61 copies are re-made from the kept store by "
                "§1.3's statement, and it is relaunched from zero")
    h1 = res.get("raw_h1") or {}
    if h1 and h1.get("partition_as_predicted") is False:
        stops.append(
            f"H1 (kill 1): the partition is not §1.2's -- granted "
            f"{h1.get('granted_n')} of {h1.get('n')} "
            f"expected {h1.get('expected_granted_n')}; withheld only here "
            f"{h1.get('withheld_only_here')}; withheld missing "
            f"{h1.get('withheld_missing')}; count mismatches "
            f"{h1.get('withheld_count_mismatches')}")
    # `is False` and not falsiness: `None` is "not measured over the 61"
    # (the loop stopped short, and the clause above already said so), which
    # is not a STOP about the subject.
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

        res["raw_pass2"] = two = pass_two(
            paths, cfg,
            on_first_number=lambda why: mark_numbers_read(res, raw_path, why))
        first = next((r.get("driver_version_from_the_trace")
                      for r in two["refocuses"]
                      if r.get("driver_version_from_the_trace")), None)
        pins["driver_version_from_the_trace"] = first
        # Belt and braces over the loop hook: by the time an H endpoint is
        # computed a number has certainly been read, and a loop that
        # produced no readable answer at all still marks the record here
        # rather than leaving rules 4 and 5 to a judgement.
        mark_numbers_read(res, raw_path, "the first H endpoint was computed")
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
    """`--render` PRINTS §2 and §3 from the assembled record, to stdout —
    which under the launcher is the run's log.

    It rewrites nothing: §4 and §5 are the verdicts and the gaps, written by
    hand at Task 6 against §1's rules and the raw record. Never run for a
    dry assembly."""
    import render_e4p
    return render_e4p.main([str(RESULTS)])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
