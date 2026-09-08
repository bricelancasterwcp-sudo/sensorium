#!/usr/bin/env python3
"""The E4″ runner: PASS 2 ONLY, measured ONCE over E4's 61 kept originals
under a DIFFERENT driver build, plus two four-pair control arms.

`docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md` §1.

WHAT THIS RUNNER DOES
---------------------
Nothing is re-recorded. Pass 1 already happened -- it is E4's -- so its 61
originals are COPIED out of the kept store by §1.3's statement and the only
invocation this record makes against the subject is

    sensorium refocus <run> --focus <name>

for each of §1.1's 61 rows (arm A), then for four of them again with
`E4PP_INPUT=1` added (arm B), then for the same four with the session key
the preflight chose (arm C). Because pass 1 is not re-run, the originals'
bytes are E4's exactly, and any difference this record reads is
attributable to the reader and the driver, never to a fresh recording.

Then H1-H8: the partition (H1), the recorder's fragment (H2), the verdict
and the pair (H3), the session set (H4), the two controls (H5, H6), the
instrument itself (H7) and what did not move (H8).

WHY E4″ EXISTS
--------------
E4′ measured this partition once and STOPPED on H1 with `granted` = 0: the
licence's environment clause read the driver's own `RUSTDOCFLAGS` fragment
as a change the world had made, so all 61 pairs were withheld for a reason
with nothing to do with the rule under test. The rt hash that fragment
carries is a digest of the driver binary and the `sensorium-rt` sources, so
the originals (recorded by 0.5.0) and the re-runs (by the 0.5.2 this
preflight builds) carry DIFFERENT hashes -- the one condition under which
the confound is visible, and one a dry run under a single build cannot
create.

THE RULES THAT RUN THROUGH IT
-----------------------------
* **§1 is the contract, and it is byte-locked** -- by RANGE for §1 and by
  DIGEST for the 61-row sibling. `acceptance_e4pp_lock` holds both and the
  runner refuses to start on either mismatch, or while no lock is set.
* **No endpoint is ever filled from a prediction.** §1.2's and §1.4's
  numbers enter as COMPARISON TARGETS under their own names
  (`acceptance_e4pp_schema._predictions`).
* **The kept store is READ-ONLY**, opened `mode=ro`, copied from by `VACUUM
  INTO`, and censused before and after by size and `st_mtime_ns`.
* **None is not zero.** An unread field is `null` with its reason in
  `dropped`; a KILLED cell is `{killed, reason}` and has no numeric
  reading.
* **Every pair is found by ITS OWN invocation's launch timestamp**, in
  `refocus_one`, immediately after that invocation. Arms B and C refocus
  four of arm A's originals into the SAME store, so a closing sweep by
  `refocus_of` alone would read a pair count of 3 on four rows and STOP H3
  for an instrument's reason.
* **A kill is a fact, not an exception.** Every child runs in its own
  process GROUP and a bound reached kills the group, verifies with `ps -p`
  and records what it did. `pkill -f` is never used.

THE LOCATIONS
-------------
    SENSORIUM_DRIVER          the `cargo-sensorium` binary, by absolute
                              path; the runner REBUILDS it from this
                              branch's HEAD before measuring (§1.3)
    SENSORIUM_E4_STORE        the KEPT E4 store -- READ-ONLY input, the
                              source of the 61 copies
    SENSORIUM_BLOOMERY        the read-only clone, pinned at e209ed9
    SENSORIUM_E4PP_TARGET     a FRESH CARGO_TARGET_DIR for the rebuilds
    SENSORIUM_DIR             a FRESH trace store for the copies
    SENSORIUM_RUST_TARGET     this workspace's target, for H8's `cargo test`
    SENSORIUM_CARGO_SENSORIUM how the CLI resolves the driver; the phases
                              re-add it per child, since `plain_env()`
                              strips every `SENSORIUM_*`

plus the three pins the guard needs (`PYTHONDONTWRITEBYTECODE`,
`SSL_CERT_DIR`, `SSL_CERT_FILE`) and `unset TMPDIR`. Launch it detached and
read nothing before the marker exists:

    setsid nohup <ledger>/acceptance-e4pp/launch.sh \\
        > <ledger>/acceptance-e4pp/logs/e4pp.log 2>&1 &

The last act is `<ledger>/acceptance-e4pp/e4pp.DONE` (or `.FAILED`)
carrying `exit=<n>`, so silence is distinguishable from success.

A DRY RUN IS NOT THE MEASUREMENT
--------------------------------
`--dry` replaces §1.1's table with §1.3's two pairs -- one expected
granted, and `a_pager_can_be_shared_across_threads` -- and moves EVERY
fresh location to its own `-dry` sibling: the store, the cargo target, the
raw record, the markers and the assembled record all carry the suffix,
`dry_run: true` is stamped through, and the document's tracked
`results.json` is never written. H8 does not run in a dry: it asks whether
THIS repository still answers as it did, which a two-row table says nothing
about.

`--dry-arms` (which implies `--dry`) additionally rehearses arms B and C
over the same two rows, into the same `-dry` siblings. §1.3's dry is a
MINIMUM, not a ceiling: the four control invocations are otherwise
unrehearsed until an hour into the real run, and a dry that rehearses them
must also show that each arm produced a PAIR for each of its rows. Both
readings feed `dry_check`, and a dry that fails either exits 9 --
INFRASTRUCTURE, never a STOP, because a dry run measures nothing.

A DRY RUN IS NEVER JUDGED BY THE SUBJECT'S GATES. A two-row table cannot
meet §1.2's "granted 57", and an rc that said so would report a STOP where
no measurement was made at all -- and the marker is exactly what the
controller reads before deciding whether the launch happens.

The launcher passes no argv by default, so the measurement cannot take
either path by accident.

THE EXIT CODES, AND THE TWO THINGS 9 MEANS
------------------------------------------
    0  clean
    3  REFUSED before any measurement (nothing assembled, nothing rendered)
    4  an unhandled error
    5  assemble/render failed; the raw record is intact
    6  the raw record would not serialise; a partial one was written
    7  a STOP -- §1.4's rule 5: the numbers already read STAND
    8  the loop bound was reached
    9  INFRASTRUCTURE -- **relaunch from zero**, in both its shapes:
       a `.FAILED` before any number had been read (§1.4's rule 4: archive
       the run, empty the fresh locations, re-make the 61 copies), or a DRY
       run that did not check the instrument (§1.3: the launch does not
       happen). Neither is a finding about the subject and neither is a
       STOP; the marker says which of the two it was.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_lib as lib                                       # noqa: E402

REPO = lib.REPO
PLAN = REPO / ".superpowers" / "sdd" / "2026-09-08-sensorium-rung4-footprint"
LEDGER = PLAN
BASE = PLAN / "acceptance-e4pp"
LOGS = BASE / "logs"

# Every earlier ledger is evidence and is not written to again.
lib.LEDGER = LEDGER
lib.LOGS = LOGS

import acceptance_e4p_phases as eph                                # noqa: E402
import acceptance_e4p_phases2 as eph2                              # noqa: E402
import acceptance_e4p_preflight as pre                             # noqa: E402
import acceptance_e4pp_arms as arms                                # noqa: E402
import acceptance_e4pp_phases as ph                                # noqa: E402
import acceptance_e4pp_phases2 as ph2                              # noqa: E402
import acceptance_e4pp_preflight as e4pre                          # noqa: E402
import acceptance_e6ppp as e6ppp                                   # noqa: E402
from acceptance_e4p_phases import pass_two                         # noqa: E402
from acceptance_e4p_preflight import cleanup, mark_numbers_read    # noqa: E402
from acceptance_e4p_store import (copy_originals, store_census)    # noqa: E402
from acceptance_e4pp_lock import (BYTE_LOCK, DOC, RESULTS,         # noqa: E402,F401
                                  ROWS_DOC, ROWS_SHA256,
                                  check_byte_lock, check_rows_digest)
from acceptance_e4pp_rows import (CORPUS_ARGS, GATE_N,            # noqa: E402
                                  LOOP_BUDGET_S, REFOCUS_TIMEOUT, ROWS,
                                  TARGETS, bound_sentence)
from acceptance_e4pp_schema import SCHEMA_VERSION, assemble_e4pp   # noqa: E402
from acceptance_e6ppp import LOADS                                 # noqa: E402
from acceptance_lib import Refused, step                           # noqa: E402

# Re-asserted AFTER the imports above, and not only before them: importing
# `acceptance_rung3` (through the lock) points `acceptance_lib.LEDGER`/
# `LOGS` at the rung-3 slice's workspace and `acceptance_e6ppp` at the E6‴
# document's. The phases each open `logs_at(LOGS / "<phase>")` in THEIR OWN
# namespace, and E4′'s first launch died on exactly that name being unset
# fourteen seconds in.
lib.LEDGER = LEDGER
lib.LOGS = LOGS
eph.LOGS = LOGS
eph2.LOGS = LOGS
pre.LOGS = LOGS
ph.LOGS = LOGS
ph2.LOGS = LOGS
arms.LOGS = LOGS
e4pre.LOGS = LOGS
e6ppp.LOGS = LOGS
e6ppp.BASE = BASE

RUNNER = "rust/tests/acceptance_e4pp.py"
RAW = LEDGER / "results-e4pp-raw.json"

#: The six locations, and the `paths` keys they land under.
#:
#: `SENSORIUM_E4PP_TARGET` lands under `sensorium_e4p_target` deliberately:
#: `refocus_env`, `shim_census` and E4′'s preflight all read that KEY, and
#: this record re-uses those functions unchanged. The variable moved; the
#: key did not, and a record that renamed the key would fork three shared
#: functions to say the same thing.
E4PP_ENV = {
    "SENSORIUM_DRIVER": "sensorium_driver",
    "SENSORIUM_E4_STORE": "sensorium_e4_store",
    "SENSORIUM_BLOOMERY": "sensorium_bloomery",
    "SENSORIUM_E4PP_TARGET": "sensorium_e4p_target",
    "SENSORIUM_DIR": "sensorium_dir",
    "SENSORIUM_RUST_TARGET": "sensorium_rust_target",
}

#: The locations a DRY run moves to a sibling of its own. The kept store,
#: the clone and the driver are INPUTS and are the same on both paths.
DRY_SIBLINGS = ("sensorium_dir", "sensorium_e4p_target")

#: §1.4's ceilings. `REFOCUS_TIMEOUT` and `LOOP_BUDGET_S` are imported from
#: `acceptance_e4pp_rows` with §1.4's other pre-registered numbers, because
#: `bound_sentence` derives the words a cut-off row carries from the ceiling
#: itself. H8's three commands are not the loop and keep their own; the
#: driver build happens before the loop starts.
CORPUS_TIMEOUT = 7200
PYTEST_TIMEOUT = 3600
CARGO_TEST_TIMEOUT = 7200


# ------------------------------------------------------------ lock and paths

def env_paths_e4pp(dry: bool = False) -> dict:
    """Every location this run touches, from the environment, refused
    TOGETHER when missing -- one launch reports all of them."""
    missing = [k for k in E4PP_ENV if not os.environ.get(k)]
    if missing:
        raise Refused(
            "unset environment variable(s): " + ", ".join(missing)
            + " -- this run needs the `cargo-sensorium` binary to rebuild "
              "and measure with, the KEPT E4 store to copy the 61 originals "
              "out of, the read-only bloomery clone at §1.3's pin, a FRESH "
              "cargo target for the rebuilds, a FRESH trace store for the "
              "copies, and this workspace's own target for H8's `cargo test "
              "--workspace`")
    paths = {name: Path(os.environ[key]) for key, name in E4PP_ENV.items()}
    if dry:
        # §1.3's `-dry` siblings, DERIVED rather than exported: a dry run
        # that shared the measurement's store would leave two of its traces
        # where the loop's freshness check counts them.
        for key in DRY_SIBLINGS:
            paths[key] = paths[key].with_name(paths[key].name + "-dry")
    return paths


def dry_rows() -> list:
    """§1.3's two dry pairs, from §1.1's own table.

    "One expected granted, and `a_pager_can_be_shared_across_threads`" --
    both real rows with real run ids, because the dry run's job is to show
    the strip clause fire on an original whose rt hash differs from the
    re-run's, and a stub row would show nothing.
    """
    granted = next(r for r in ROWS
                   if r[1] not in __import__(
                       "acceptance_e4pp_rows").EXPECTED_WITHHELD)
    pager = next(r for r in ROWS if r[1] == arms.PAGER_ROW)
    return [list(granted), list(pager)]


def e4pp_config(paths, rows=None) -> dict:
    """This run's config.

    The corpus target is derived from the run target: §1.3 requires H8's
    corpus target to be fresh and names a path for it but no variable, and
    a location derived from an env var is still not a location compiled
    into this file.
    """
    corpus = os.environ.get("SENSORIUM_CORPUS_TARGET")
    target = paths["sensorium_e4p_target"]
    rows = [list(r) for r in (rows if rows is not None else ROWS)]
    return {
        "corpus_target": (Path(corpus) if corpus
                          else target.parent / (target.name + "-corpus")),
        "corpus_target_from_env": bool(corpus),
        "corpus_args": list(CORPUS_ARGS),
        "rows": rows,
        "targets": list(TARGETS),
        "gate_n": len(rows),
        "gate_n_locked": GATE_N,
        "refocus_timeout": REFOCUS_TIMEOUT,
        "loop_budget_s": LOOP_BUDGET_S,
        "corpus_timeout": CORPUS_TIMEOUT,
        "pytest_timeout": PYTEST_TIMEOUT,
        "cargo_test_timeout": CARGO_TEST_TIMEOUT,
        "clone_pin": lib.CLONE_PIN,
        # The labels the shared E4′ preflight prints, so a refusal a human
        # reads names the variable THIS launch actually sets.
        "preflight_label": "rung-4 footprint (E4″)",
        "target_env_name": "SENSORIUM_E4PP_TARGET",
        "corpus_label": "H8",
        # Arm C's value: the launch stamp, so the injected key carries
        # something no shell would have set and the record can say what it
        # was.
        "injected_value": time.strftime("e4pp-%Y%m%dT%H%M%S%z"),
        # The sentence a row cut off by the loop bound carries, DERIVED
        # from this record's own ceiling. Without it `pass_two` and
        # `run_arm` write E4′'s constant -- "the 1 h 15 min loop bound" --
        # into a record whose bound is 1 h 30 min.
        "not_run_bound": bound_sentence(LOOP_BUDGET_S),
        "tmpdir_observed": os.environ.get("TMPDIR"),
        "tempfile_gettempdir": tempfile.gettempdir(),
    }


# --------------------------------------------------------------------- main

#: Which raw block each gated endpoint lives in, and how a miss is named.
#: §1.4's kill 2 by its words: H2-H6 and H8 are STOPs of the SUBJECT; H7 is
#: a STOP of the INSTRUMENT and the record says so rather than reporting it
#: as a finding about the subject.
GATED = (("H2", "raw_h2", "subject"), ("H3", "raw_h3", "subject"),
         ("H4", "raw_h4", "subject"), ("H5", "raw_h5", "subject"),
         ("H6", "raw_h6", "subject"), ("H7", "raw_h7", "instrument"),
         ("H8", "raw_h8", "subject"))


def stop_side(number: str, block: dict, declared: str) -> dict:
    """Which side a STOP is of, DERIVED from what missed.

    E4″ gap 2: `stop` and the `.FAILED` marker both ended "This is a STOP of
    the subject" because the label hung off the endpoint id rather than off
    the cell that missed -- and on the real run H8's own miss was a READER's
    (three green return codes, a case that ran and came back equal), so the
    marker's words pointed at the wrong side.

    The rule, in one line: a phase that recorded a reason it could not READ
    something (its `dropped` list, which is where every such reason goes,
    and which is what takes `as_predicted` to `None`) missed because this
    INSTRUMENT could not read it; a phase whose reading was whole and simply
    did not match its gate missed on the side that endpoint measures. §1.4's
    kill 2 asks the record to keep the two apart, and where they disagree
    BOTH are printed -- neither is dropped for the other.
    """
    unread = [r for r in (block.get("dropped") or []) if r]
    derived = "instrument" if unread else declared
    return {"endpoint": number, "declared": declared, "derived": derived,
            "agree": derived == declared, "unread": unread,
            "blocked": block.get("as_predicted") is None}


def stop_sides(res: dict) -> list[dict]:
    """`stop_side` for every gated endpoint that STOPped, in GATED's order.
    Published beside `stop` so a reader gets the derivation and not only the
    sentence built from it."""
    return [stop_side(number, res.get(key) or {}, whose)
            for number, key, whose in GATED
            if (res.get(key) or {}).get("verdict") == "STOP"]


def _stop_sentence(side: dict) -> str:
    """The words `stop_side`'s answer earns."""
    if side["agree"]:
        return ("This is a STOP of the INSTRUMENT, not of the subject"
                if side["derived"] == "instrument"
                else "This is a STOP of the subject")
    return (f"The endpoint is gated on the {side['declared']}, and what "
            f"missed is the {side['derived'].upper()}'s reading: "
            f"{'; '.join(side['unread'])}. Both are named because they "
            f"disagree, and neither stands in for the other")


def dry_check(res: dict) -> dict:
    """What §1.3 requires a DRY run to SHOW, and nothing else.

    "It must show the strip clause firing on an original whose rt hash
    differs from the re-run's -- a dry run under one build is not a dry run
    of this instrument, which is precisely E4′'s lesson. A dry run that does
    not show it has not checked the instrument: the launch does not happen,
    and that is infrastructure, not a STOP."

    So a dry run is NOT judged by the subject's gates. A two-row table
    cannot meet §1.2's "granted 57" and an rc that said so would report a
    STOP where there is no measurement at all -- and the marker is what the
    controller reads before deciding whether the launch happens.
    """
    rows = [r for r in (res.get("raw_pass2") or {}).get("refocuses") or []
            if "not_run" not in r]
    showed = [r["name"] for r in rows
              if "RUSTDOCFLAGS" in (r.get("env_stripped_keys") or [])
              and r.get("rt_hashes_differ") is True]
    silent = [{"name": r["name"],
               "stripped": r.get("env_stripped_keys"),
               "original_rt": (r.get("original_rt_hash") or {}).get("value"),
               "rerun_rt": (r.get("rerun_rt_hash") or {}).get("value")}
              for r in rows if r["name"] not in showed]
    rec = {"rows": len(rows), "showed_the_strip_on_differing_hashes": showed,
           "did_not_show_it": silent, "strip_ok": bool(showed),
           "arms_rehearsed": bool(res.get("dry_arms"))}
    # §1.3's dry is a MINIMUM, not a ceiling (controller, fix round 1). With
    # `--dry-arms` the two dry rows are re-run under both controls, and the
    # dry then also has to show that each arm produced a PAIR for each of
    # its rows -- the one thing four unrehearsed invocations could get wrong
    # an hour into the real run.
    arms_rec = {}
    if rec["arms_rehearsed"]:
        for key, label in (("raw_arm_b", "B"), ("raw_arm_c", "C")):
            block = res.get(key) or {}
            answers = [r for r in (block.get("refocuses") or [])
                       if "not_run" not in r]
            without = [r["name"] for r in answers
                       if not r.get("new_run") or r.get("timed_out")]
            arms_rec[label] = {
                "rows": block.get("n"), "measured": len(answers),
                "never_run": block.get("budget_exhausted") or [],
                "rows_without_a_pair": without,
                "ok": bool(answers) and not without
                and not (block.get("budget_exhausted") or [])
                and len(answers) == block.get("n")}
        rec["arms"] = arms_rec
        rec["arms_ok"] = all(a["ok"] for a in arms_rec.values())
    else:
        rec["arms"] = None
        rec["arms_ok"] = None
    rec["ok"] = bool(rec["strip_ok"]) and rec["arms_ok"] is not False
    strip = (
        f"{len(showed)} of {len(rows)} dry pair(s) showed the strip clause "
        "fire on an original whose rt hash differs from the re-run's"
        if showed else
        "NO dry pair showed the strip clause fire on an original whose rt "
        "hash differs from the re-run's")
    arms_said = (
        "" if not rec["arms_rehearsed"] else
        "; both control arms produced a pair for every row"
        if rec["arms_ok"] else
        "; a control arm did NOT produce a pair for every row "
        + str({k: v["rows_without_a_pair"] or v["never_run"]
               for k, v in arms_rec.items() if not v["ok"]}))
    rec["reading"] = strip + arms_said + ("" if rec["ok"] else (
        ". §1.3: a dry run that does not show it has not checked the "
        "instrument -- the launch does not happen, and that is "
        "INFRASTRUCTURE, not a STOP"))
    return rec


def _stops(res: dict) -> list[str]:
    """§1.4's kill rules, by their WORDS.

    A DRY run is judged by `dry_check` alone: it measures nothing, so no
    subject gate applies to it and none is evaluated here.
    """
    stops = []
    # The KILL first, in the words of the rule that applies: a row killed
    # at its ceiling leaves its licence unread, which takes H1's partition
    # to False, and the first line Task 8 reads must not attribute a kill
    # 4/5 event to kill 1. Rules 4 and 5 are told apart by `numbers_read`
    # and by nothing else.
    killed, missing = [], []
    for key in ("raw_pass2", "raw_arm_b", "raw_arm_c"):
        block = res.get(key) or {}
        killed += [f"{key}:{n}" for n in (block.get("killed") or [])]
        missing += [f"{key}:{n}" for n in (block.get("budget_exhausted")
                                           or [])]
    if killed or missing:
        what = []
        if killed:
            what.append(f"{len(killed)} invocation(s) were KILLED at the "
                        f"{REFOCUS_TIMEOUT} s ceiling ({killed[:3]})")
        if missing:
            what.append(f"{len(missing)} invocation(s) were never run -- the "
                        f"1 h 30 min loop bound was reached ({missing[:3]})")
        if res.get("numbers_read"):
            stops.append(
                "; ".join(what) + ". A `.FAILED` marker AFTER a number had "
                "already been read is a STOP and the numbers already read "
                "stand (§1.4's rule 5, by its words). Every endpoint "
                "boolean below is over fewer than its arm's rows, and the "
                "assembled record nulls each of them with this reason")
        else:
            stops.append(
                "; ".join(what) + ". A `.FAILED` marker BEFORE any number "
                "had been read is infrastructure (§1.4's rule 4, by its "
                "words): the run is archived, the fresh locations are "
                "emptied, the 61 copies are re-made from the kept store by "
                "§1.3's statement, and it is relaunched from zero")
    if res.get("dry_run"):
        return stops
    h1 = res.get("raw_h1") or {}
    if h1 and h1.get("partition_as_predicted") is False:
        stops.append(
            f"H1 (kill 1): the partition is not §1.2's -- granted "
            f"{h1.get('granted_n')} of {h1.get('n')} expected "
            f"{h1.get('expected_granted_n')}; withheld only here "
            f"{h1.get('withheld_only_here')}; withheld missing "
            f"{h1.get('withheld_missing')}; count mismatches "
            f"{h1.get('withheld_count_mismatches')}. The partition observed "
            "is the finding")
    for number, key, whose in GATED:
        block = res.get(key) or {}
        if not block or block.get("verdict") != "STOP":
            continue
        stops.append(
            f"{number} (kill 2): a miss with its number. Gate: "
            f"{block.get('gate')}. "
            + _stop_sentence(stop_side(number, block, whose)))
    cl = res.get("cleanup") or res.get("cleanup_after_failure") or {}
    if cl.get("kept_store_unchanged") is False:
        stops.append(
            "§1.3: the KEPT store changed during the run -- "
            f"{cl.get('kept_census_differences')}. A single changed mtime "
            "is a STOP")
    return stops


def _infrastructure(res: dict) -> bool:
    """§1.4's rule 4 rather than its rule 5: a `.FAILED` BEFORE any number
    had been read. The run is archived and relaunched from zero, which is
    not the same event as a STOP and must not carry a STOP's exit code."""
    if res.get("numbers_read"):
        return False
    for key in ("raw_pass2", "raw_arm_b", "raw_arm_c"):
        block = res.get(key) or {}
        if (block.get("killed") or block.get("budget_exhausted")):
            return True
    return False


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
    # `--dry-arms` IMPLIES `--dry`: there is no arms-only mode, and a flag
    # that silently did nothing without its partner is a flag that will be
    # passed alone one day.
    dry = "--dry" in argv or "--dry-arms" in argv
    dry_arms = dry and "--dry-arms" in argv
    suffix = "-dry" if dry else ""
    raw_path = (RAW.with_name(RAW.stem + suffix + RAW.suffix) if dry
                else RAW)
    BASE.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    for marker in (f"e4pp{suffix}.DONE", f"e4pp{suffix}.FAILED"):
        (BASE / marker).unlink(missing_ok=True)
    res: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                 "schema_version": SCHEMA_VERSION,
                 "runner": RUNNER, "dry_run": dry, "dry_arms": dry_arms,
                 "document": str(DOC.relative_to(REPO)),
                 # Where the DRY run's own raw record is, so §1.5's fourth
                 # wall can be gathered from it instead of staying in an
                 # archive nobody opens (E4″ gap 5). Named whether or not
                 # the file exists: the assembler says which it found.
                 "dry_raw": str(RAW.with_name(RAW.stem + "-dry"
                                              + RAW.suffix)),
                 "ledger": str(LEDGER), "logs": str(LOGS)}
    rc = 0
    paths = cfg = pins = kept_before = None
    try:
        res["byte_lock"] = check_byte_lock()
        res["rows_digest"] = check_rows_digest()
        paths = env_paths_e4pp(dry=dry)
        cfg = e4pp_config(paths, dry_rows() if dry else None)
        res["config"] = {k: (str(v) if isinstance(v, Path) else v)
                         for k, v in cfg.items()}
        if dry:
            step(f"DRY RUN: {len(cfg['rows'])} row(s); every location is a "
                 "`-dry` sibling, no tracked results.json is written, and "
                 "neither arm nor H8 runs")
        res["predictions"] = {"source": "§1.1, §1.2 and §1.4",
                              "gate_n": GATE_N}
        pins = e4pre.preflight_e4pp(paths, cfg)
        res["pins"] = pins
        kept_before = store_census(paths["sensorium_e4_store"])
        res["kept_census_before"] = kept_before
        res["store"] = copy_originals(paths["sensorium_e4_store"],
                                      paths["sensorium_dir"], cfg["rows"])

        res["raw_pass2"] = two = pass_two(
            paths, cfg,
            on_first_number=lambda why: mark_numbers_read(res, raw_path, why))
        ph.read_rt_hashes(paths, two)
        first = next((r.get("driver_version_from_the_trace")
                      for r in two["refocuses"]
                      if r.get("driver_version_from_the_trace")), None)
        pins["driver_version_from_the_trace"] = first
        # E4″ gap 3: the copied ORIGINAL's own token, beside the re-run's,
        # so §1.5's "on both sides" has two cells and not one. The DISTINCT
        # values, never a first: originals written by more than one driver
        # would be the finding, and a first would hide it.
        pins["driver_version_from_the_original"] = sorted(
            {v for r in two["refocuses"]
             if (v := (r.get("original_driver_version") or {}).get("value"))})
        # Belt and braces over the loop hook -- but ONLY where a row
        # really came back with a reading. E4′ marked here
        # unconditionally, which makes §1.4's rule 4 unreachable: a loop
        # that produced no readable answer at all would still be recorded
        # as having read a number, and the relaunch-from-zero the rule
        # authorises would never be offered.
        if any(r.get("verdict_word") or r.get("licence_word")
               for r in two["refocuses"] if "not_run" not in r):
            mark_numbers_read(res, raw_path,
                              "a row of arm A came back with a reading")

        if not dry or dry_arms:
            rows = arms.arm_rows(cfg["rows"])
            # ONE deadline across all three arms: §1.4 bounds "the whole
            # loop", and `pass_two` already opened it.
            deadline = two.get("loop_deadline_monotonic")
            res["raw_arm_b"] = arm_b = arms.run_arm(
                paths, cfg, rows, arms.ARM_B_KEY, "1", "armB",
                deadline=deadline)
            ph.read_rt_hashes(paths, arm_b)
            res["raw_arm_c"] = arm_c = arms.run_arm(
                paths, cfg, rows, pins["injected_session_key"],
                cfg["injected_value"], "armC", deadline=deadline)
            ph.read_rt_hashes(paths, arm_c)
            if dry_arms:
                step(f"DRY RUN: both arms REHEARSED over "
                     f"{len(rows)} row(s) into the `-dry` siblings")
        else:
            step("DRY RUN: arms B and C are NOT run -- §1.3's dry run is two "
                 "pairs, and its job is to show the strip clause fire. Pass "
                 "`--dry-arms` to rehearse them over the same two rows")
            arm_b = arm_c = None

        session = pins["session_keys_differing"]
        res["raw_h1"] = ph.phase_h1(two)
        res["raw_h2"] = ph.phase_h2_fragment(two)
        res["raw_h3"] = ph.phase_h3_verdict_pair(two)
        res["raw_h4"] = ph.phase_h4_session(two, session)
        if arm_b is not None:
            res["raw_h5"] = ph.phase_h5_input(arm_b)
            res["raw_h6"] = ph.phase_h6_session_key(
                two, arm_c, session, pins["injected_session_key"])
        # H8 before H7 and LAST of the commands: `cargo test --workspace`
        # shares the driver's target and is the one thing here that could
        # relink the binary every other phase measured with. A DRY run does
        # not run it -- H8 asks whether THIS repository still answers as it
        # did, which a two-row table says nothing about, and its three
        # commands cost more than the rest of a dry run put together.
        if dry:
            step("DRY RUN: H8 is NOT run; its cells publish null with a "
                 "reason, which is the artifact this dry run checks")
        else:
            res["raw_h8"] = ph.phase_h8_nothing_else(paths, cfg)
        # H7 reads every OTHER phase's `dropped` list as its second
        # reading, so it is computed after them -- including H8's, whose
        # commands cannot raise (a bound reached is a recorded fact, never
        # an exception) and so cannot take this phase down with them.
        res["raw_h7"] = ph.phase_h7_instrument(res)
        res["cleanup"] = cleanup(paths, cfg, pins, kept_before)
        if dry:
            res["dry_check"] = check = dry_check(res)
            step("DRY RUN: " + check["reading"])
            if not check["ok"]:
                res["dry_run_did_not_check_the_instrument"] = check["reading"]
                rc = rc or 9
        stops = _stops(res)
        if stops:
            # §1.4's rules 4 and 5 part company on `numbers_read`, and so
            # do the exit codes: 9 is the INFRASTRUCTURE kill (archive,
            # empty the fresh locations, re-make the 61 copies, relaunch
            # from zero) and 7 is a STOP (the numbers already read stand).
            # One code for both made a relaunch and a finding read the same
            # to whatever is watching the marker.
            res["stop"] = "; ".join(stops)
            # The derivation beside the sentence built from it, so a reader
            # gets which side each gated miss was on without parsing prose.
            res["stop_sides"] = stop_sides(res)
            res["kill_is_infrastructure"] = _infrastructure(res)
            rc = rc or (9 if res["kill_is_infrastructure"] else 7)
        exhausted = [n for key in ("raw_pass2", "raw_arm_b", "raw_arm_c")
                     for n in ((res.get(key) or {}).get("budget_exhausted")
                               or [])]
        if exhausted:
            res["bound_reached"] = (
                f"§1.4's 1 h 30 min loop bound was reached; "
                f"{len(exhausted)} invocation(s) were NOT run: "
                f"{exhausted[:5]}"
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
            assemble_only(res, dry=dry)
            if not dry:
                render_only()
        except Exception:                                      # noqa: BLE001
            import traceback
            (LOGS / "assemble-error.txt").write_text(traceback.format_exc())
            step("assemble/render FAILED (logs/assemble-error.txt); the raw "
                 "record is intact")
            rc = rc or 5
    why = (res.get("refused") or res.get("stop") or res.get("bound_reached")
           or res.get("dry_run_did_not_check_the_instrument")
           or res.get("error") or "")
    marker = f"e4pp{suffix}." + ("DONE" if rc == 0 else "FAILED")
    # What the code MEANS, beside the code. 9 has two shapes and both are
    # "relaunch from zero"; 7 is the one where the numbers stand. A marker
    # that carried only the number left that to a reader's memory.
    meaning = {
        0: "clean", 3: "REFUSED before any measurement",
        4: "an unhandled error", 5: "assemble/render failed",
        6: "the raw record would not serialise",
        7: "a STOP -- §1.4's rule 5: the numbers already read STAND",
        8: "§1.4's loop bound was reached",
        9: ("INFRASTRUCTURE -- RELAUNCH FROM ZERO: "
            + ("a DRY run that did not check the instrument (§1.3: the "
               "launch does not happen)" if res.get(
                   "dry_run_did_not_check_the_instrument")
               else "a `.FAILED` before any number had been read (§1.4's "
                    "rule 4: archive, empty the fresh locations, re-make "
                    "the 61 copies)")),
    }.get(rc, "unnamed")
    (BASE / marker).write_text(
        f"exit={rc}\n{meaning}\n{time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n"
        f"{why}\n")
    step(f"done rc={rc}; raw facts at {raw_path}")
    return rc


def assemble_only(raw: dict | None = None, dry: bool = False) -> int:
    """`--assemble` derives the document's `results.json` from the raw
    facts. A DRY assembly writes a `-dry` sibling in the ledger and never
    the tracked file."""
    path = RAW.with_name(RAW.stem + "-dry" + RAW.suffix) if dry else RAW
    if raw is None:
        raw = json.loads(path.read_text())
    record = assemble_e4pp(raw)
    dest = (LEDGER / "results-e4pp-dry.results.json" if dry else RESULTS)
    dest.write_text(json.dumps(record, indent=2, default=str))
    step(f"assembled -> {dest}")
    return 0


def render_only() -> int:
    """`--render` PRINTS §2 and §3 from the assembled record, to stdout --
    which under the launcher is the run's log.

    It rewrites nothing: §4 and §5 are the verdicts and the gaps, written
    by hand at Task 8 against §1's rules and the raw record. Never run for
    a dry assembly."""
    import render_e4pp
    return render_e4pp.main([str(RESULTS)])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
