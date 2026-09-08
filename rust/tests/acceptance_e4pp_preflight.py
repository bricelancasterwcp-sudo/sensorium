#!/usr/bin/env python3
"""E4″'s launch guard, and the two pins every session reading is compared
against.

E4′'s `env_parity` refuses on ANY key that differs between this process's
environment and the 61 recorded ones. A-§3 exempts session set 1 from
WITHHOLDING, and §1.3 carries that exemption into the guard -- but not into
a silence:

1. **Every key OUTSIDE session set 1 must match.** A difference there is a
   refusal to launch, before any number, because it is an uncontrolled
   instrument variable and not a property of the subject. The launcher
   satisfies it by EXPORTING the three keys the scan of the 61 found, never
   by exempting them.
2. **Every key INSIDE the set that differs is recorded BY NAME**, before
   any refocus runs, into `pins.session_keys_differing`. H4 and H6 compare
   the printed lines against THAT recorded set -- never against a set read
   out of the same lines they are checking, which would make the check
   circular.
3. **A different differing-set on the day is REPORTED, not a STOP.** The
   launch shell is the instrument's, not the subject's; which session
   variables this box's shell happens to carry is a fact about the
   launcher. What would be a STOP is a difference outside the set (rule 1)
   or a printed line that disagrees with the recorded set (H4).

Arm C's key is chosen HERE too, and before the driver build: §1.3 makes no
eligible key a refusal to launch, and the cheap moment to discover that is
the cheap one.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4p_preflight as pre                             # noqa: E402
import acceptance_e4pp_arms as arms                                # noqa: E402
from acceptance_e4p_preflight import (EXCLUDED_ENV,                # noqa: E402
                                      UNCOMPARED_ENV)
from acceptance_e4p_read import trace_meta_ro                      # noqa: E402
from acceptance_lib import Refused, step                           # noqa: E402
from sensorium.query.refocus_env import is_session_key             # noqa: E402

#: §1.3's rule 3, measured 2026-09-08 (names only) against kept original
#: `20260907-111144-33d30c` from that session's shell: 73 keys equal, 0
#: added, 3 missing (the previous launcher's own pins, which this launcher
#: exports too) and exactly ONE changed.
#:
#: A COMPARISON TARGET and never a gate. It is published beside what the
#: guard actually found, so a reader sees the expectation and the reading
#: without either standing in for the other.
EXPECTED_SESSION_DIFFERS = ("CLAUDE_CODE_SESSION_ID",)

REPORTED_NEVER_A_STOP = (
    "which session variables this box's shell carries on the day is a fact "
    "about the LAUNCHER, not about the subject: §1.3's rule 3 makes a "
    "differing set other than the expected one REPORTED, never a STOP. What "
    "would be a STOP is a difference OUTSIDE the set (rule 1, which refuses "
    "to launch) or a printed line that disagrees with this recorded set "
    "(H4)")


def session_parity(kept: Path, rows, environ=None) -> dict:
    """E4′'s `env_parity` with session set 1 allowed -- and NAMED.

    Same walk, same exclusions, same one-refusal-names-everything rule. The
    single difference is the partition at the end: a differing key that
    `is_session_key` accepts goes on `session_differs` and the launch
    proceeds; every other one is a refusal.

    A key is a difference whether its VALUE moved, it is missing from this
    process, or this process added it. The licence compares a SET, and a
    subset check would pass a shell carrying a variable E4's did not.
    """
    environ = dict(os.environ if environ is None else environ)
    mine = {k: v for k, v in environ.items()
            if not EXCLUDED_ENV.match(k) and k not in UNCOMPARED_ENV}
    differing, session, unreadable, compared = {}, {}, [], set(mine)
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
            where = session if is_session_key(key) else differing
            where.setdefault(key, {"how": how, "originals": []})
            where[key]["originals"].append(run)
    rec = {
        "guard": "session_parity",
        "checked": len(rows) - len(unreadable),
        "originals": len(rows),
        "differing": sorted(differing), "detail": differing,
        "session_differs": sorted(session), "session_detail": session,
        "session_differs_n": len(session),
        "expected_session_differs": sorted(EXPECTED_SESSION_DIFFERS),
        "session_set_as_expected": (sorted(session)
                                    == sorted(EXPECTED_SESSION_DIFFERS)),
        "reported_never_a_stop": REPORTED_NEVER_A_STOP,
        "unreadable": unreadable,
        "compared_keys": sorted(compared),
        "excluded_pattern": EXCLUDED_ENV.pattern,
        "uncompared": sorted(UNCOMPARED_ENV),
        "session_rule": ("`refocus_env.is_session_key`: session set 1's "
                         "fourteen exact names, or the `CLAUDE_CODE_` "
                         "prefix"),
    }
    if unreadable or differing:
        named = "; ".join(
            f"{k} ({d['how']}; {len(d['originals'])} original(s), e.g. "
            f"{', '.join(d['originals'][:3])})"
            for k, d in sorted(differing.items()))
        raise Refused(
            "this process's environment is NOT the one the originals were "
            f"recorded under, OUTSIDE session set 1. {len(differing)} "
            f"key(s) differ: {named}"
            + (f". Originals that could not be read: {unreadable}"
               if unreadable else "")
            + ". §1.3's rule 1: a difference outside the set is an "
              "uncontrolled instrument variable, not a subject property, so "
              "this is a refusal to launch before any number. Pin them in "
              "the launcher (it already exports PYTHONDONTWRITEBYTECODE, "
              "SSL_CERT_DIR and SSL_CERT_FILE) and relaunch -- nothing has "
              "been copied and no number has been read, so this is the "
              "infrastructure kill")
    step(f"session parity: {rec['checked']} original(s) over "
         f"{len(rec['compared_keys'])} compared key(s); none differ outside "
         f"session set 1; {rec['session_differs_n']} session key(s) differ "
         f"{rec['session_differs']} (expected "
         f"{rec['expected_session_differs']}, as expected="
         f"{rec['session_set_as_expected']})")
    return rec


def arm_original_env(kept: Path, rows) -> dict:
    """The recorded environments of the arm rows, MERGED.

    §1.3 says arm C's key must be absent from "the original's recorded
    environment"; arm C runs FOUR originals, so the union of the four is
    what "the original's" means for a key that has to be absent from every
    one of the four invocations. The strict reading, and the only one that
    holds for all four.

    A union nobody could read is a refusal, not an empty dict: an empty
    union makes EVERY candidate look absent, and arm C would then inject a
    key the original already carried -- which tests nothing and looks like
    a pass.
    """
    merged, read, unreadable = {}, [], []
    for _index, _name, _target, run in rows:
        db = Path(kept) / "traces" / f"{run}.db"
        recorded = trace_meta_ro(db).get("env") if db.is_file() else None
        if not isinstance(recorded, dict):
            unreadable.append(run)
            continue
        merged.update(recorded)
        read.append(run)
    if not read:
        raise Refused(
            f"none of the arm rows' originals could be read out of the kept "
            f"store ({unreadable}): arm C's key must be absent from the "
            "original's recorded environment, and an environment nobody "
            "read makes every candidate look absent")
    return {"env": merged, "read": read, "unreadable": unreadable,
            "keys": len(merged), "store": str(kept)}


def preflight_e4pp(paths, cfg) -> dict:
    """E4′'s preflight with E4″'s guard, plus the two session pins.

    The ORDER is the point. Arm C's key is chosen before `pre.preflight`
    runs, because a launch with no eligible key must refuse before it
    spends a driver build -- and everything it reads (four traces and this
    process's environment) is cheap.
    """
    step("rung-4 footprint (E4″) preflight")
    kept = paths["sensorium_e4_store"]
    if not (kept / "traces").is_dir():
        raise Refused(f"the kept E4 store {kept} has no `traces/` directory: "
                      "§1.3 copies the 61 originals out of it and this run "
                      "cannot start without them")
    rows = arms.arm_rows(cfg["rows"])
    originals = arm_original_env(kept, [r["row"] for r in rows])
    choice = arms.session_key_choice(originals["env"], dict(os.environ))
    if choice["key"] is None:
        raise Refused(
            "arm C has no key to inject: " + choice["reason"]
            + f". The names walked were {choice['candidates']}, over "
            f"{originals['keys']} recorded key(s) from "
            f"{len(originals['read'])} original(s) and this process's own "
            "environment. §1.3's rule 3 of the kills: a refusal to launch "
            "is not a measurement")
    step(f"arm C's key: {choice['key']} (skipped "
         f"{[s['name'] for s in choice['skipped']]})")

    pins = pre.preflight(paths, cfg, parity=session_parity)
    parity = pins["env_parity"]
    pins.update({
        "session_parity": parity,
        # H4 and H6 read THESE, and never a set derived from the lines they
        # are checking. Recorded before any refocus ran.
        "session_keys_differing": parity["session_differs"],
        "session_keys_differing_n": parity["session_differs_n"],
        "session_set_as_expected": parity["session_set_as_expected"],
        "expected_session_keys_differing": parity["expected_session_differs"],
        "injected_session_key": choice["key"],
        "injected_session_key_choice": choice,
        "injected_session_key_value": cfg["injected_value"],
        "arm_b_key": arms.ARM_B_KEY,
        "arm_rows": [r["name"] for r in rows],
        "arm_rows_n": len(rows),
        "arm_originals_env": {k: v for k, v in originals.items()
                              if k != "env"},
        "session_pins_recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    return pins


__all__ = ["EXPECTED_SESSION_DIFFERS", "REPORTED_NEVER_A_STOP",
           "arm_original_env", "preflight_e4pp", "session_parity"]
