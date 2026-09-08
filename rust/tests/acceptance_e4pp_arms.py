#!/usr/bin/env python3
"""E4″'s two control arms: the rows they run, the key each injects, and how
arm C's key is CHOSEN rather than picked.

    B -- the control that must still bite.  Four rows re-run with
         `E4PP_INPUT=1` added: a key on no list, standing in for something
         the program could have read. Expected WITHHELD 4/4. If a key
         OUTSIDE session set 1 no longer withholds, the licence stopped
         meaning anything and this slice's own exemption is what did it.

    C -- the control that must not bite.  The SAME four rows re-run with
         the first of session set 1's fourteen exact names, in the
         document's printed order, that is absent from BOTH the original's
         recorded environment and the runner's own, set to the launch
         stamp. Expected: the licence word equals arm A's on 4/4, and the
         printed session set is the preflight's ∪ the chosen key, with K
         exactly one greater.

THREE RULES THIS MODULE IS THE PLACE FOR
----------------------------------------
* **The four rows are chosen by FIELD, never by index.** §1.3 names them
  as "rows 1-3 of §1.1, all three expected granted" plus the pager test:
  read from §1.2's partition, so a table whose first row were withheld
  would not quietly be run as a granted control.
* **Arm C's key is a preflight FACT.** Which session variables this box's
  shell exports is not knowable before the day, so the key is chosen and
  recorded once, at preflight, into `pins.injected_session_key`, and every
  later reading DERIVES from that pin rather than choosing again.
* **There is no fallback.** No eligible key is `None`, which the preflight
  turns into a refusal to launch. It never falls back to a key that is
  already present -- setting one again tests nothing -- and never reaches
  outside the set for one.

AND THE ORDERING FINDING THE ARMS EXIST INSIDE
----------------------------------------------
Arms B and C re-refocus FOUR OF ARM A's OWN run ids into the same fresh
store, so after all three arms up to three traces name each of those four
originals in `refocus_of`. `refocus_one` resolves that by pairing on the
launch timestamp of the invocation it just made, immediately after making
it -- and `run_arm` calls it once per row for exactly that reason. A
closing sweep that paired by `refocus_of` alone would read a pair count of
3 on four rows and STOP H3 for an instrument's reason.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4p_phases as eph                                # noqa: E402
from acceptance_e4p_rows import EXPECTED_WITHHELD                  # noqa: E402
from acceptance_e6ppp import logs_at, mark_load                    # noqa: E402
from acceptance_lib import step                                    # noqa: E402
from sensorium.query.refocus_env import SESSION_ORDER              # noqa: E402

#: Set by the runner to its own ledger, as every module of this family is.
LOGS: Path | None = None

#: Arm B's key: a name no code in the clone reads and no list of this tool
#: carries. §1.5 reports arm B's verdicts as a finding rather than a gate
#: for that reason -- a variable the program actually READ would change the
#: re-run's behaviour, and `E4PP_INPUT` is chosen so that it cannot.
ARM_B_KEY = "E4PP_INPUT"

#: Arm C's candidates: session set 1's FOURTEEN EXACT NAMES, in the order
#: §1.3 prints, taken from the source that defines the set so the arm and
#: the rule cannot drift apart. The `CLAUDE_CODE_` prefix is deliberately
#: NOT here: a prefix names no key, so "the first key absent from both
#: sides" would not be decidable over it, and a `CLAUDE_CODE_*` name
#: invented by this runner is one this box's agent session may create or
#: destroy underneath the measurement.
SESSION_CANDIDATES: tuple[str, ...] = SESSION_ORDER

#: The fourth row of both arms, by NAME: §1.2's one-program-thread test, so
#: a control's env caveat is read beside a thread reason that must survive
#: it (H5's second reading).
PAGER_ROW = "a_pager_can_be_shared_across_threads"

#: How many GRANTED rows the arms take from the head of the table.
GRANTED_ROWS = 3


# ------------------------------------------------------------- the rows

def arm_rows(rows, withheld=None) -> list[dict]:
    """§1.3's four rows, from the row table and §1.2's partition.

    `withheld` is `EXPECTED_WITHHELD` and is a parameter only so a test can
    show the selection follows the PARTITION rather than the table order:
    the first three rows whose expected licence is granted, in the table's
    order, and then the pager row by name.

    A table that does not hold four -- the dry run's does not -- yields
    what it holds. `--dry-arms` rehearses both arms over exactly those
    rows, so this is a real path and not a corner: inventing a row to reach
    four would be worse than an arm that honestly says `n: 2`.
    """
    withheld = EXPECTED_WITHHELD if withheld is None else withheld
    out, granted = [], 0
    for row in rows:
        _index, name, _target, _run = row
        if name in withheld or granted >= GRANTED_ROWS:
            continue
        granted += 1
        out.append(_arm_row(row, withheld))
    pager = next((r for r in rows if r[1] == PAGER_ROW), None)
    if pager is not None:
        out.append(_arm_row(pager, withheld))
    return out


def _arm_row(row, withheld) -> dict:
    index, name, target, run = row
    return {"index": index, "name": name, "target": target, "original": run,
            "row": row,
            "expected_licence": ("WITHHELD" if name in withheld
                                 else "granted"),
            "expected_program_threads": withheld.get(name, 0)}


# ------------------------------------------------------- arm C's key

def session_key_choice(original_env: dict, environ: dict) -> dict:
    """The whole walk, not just its answer.

    §1.4's H6 second reading asks for the key chosen AND the names the
    choice skipped over, "so the rule is checkable rather than asserted" --
    which means the skipped names carry WHICH side already held them.
    """
    original_env = dict(original_env or {})
    environ = dict(environ or {})
    skipped = []
    for name in SESSION_CANDIDATES:
        present = ([] + (["the original"] if name in original_env else [])
                   + (["the runner"] if name in environ else []))
        if not present:
            return {"key": name, "skipped": skipped,
                    "candidates": list(SESSION_CANDIDATES),
                    "rule": ("the FIRST of session set 1's fourteen exact "
                             "names, in the order §1.3 prints, absent from "
                             "BOTH the original's recorded environment and "
                             "the runner's own"),
                    "reason": None}
        skipped.append({"name": name, "present_on": present})
    return {"key": None, "skipped": skipped,
            "candidates": list(SESSION_CANDIDATES),
            "rule": ("the FIRST of session set 1's fourteen exact names "
                     "absent from BOTH sides"),
            "reason": ("every one of session set 1's fourteen exact names is "
                       "already present on one side or the other, so arm C "
                       "has no key to inject. §1.3: the preflight REFUSES to "
                       "launch and says so -- it never falls back to a key "
                       "that is already present, and never reaches outside "
                       "the set for one")}


def choose_session_key(original_env: dict, environ: dict) -> str | None:
    """§1.3's rule, as one name -- or `None`, which is a refusal upstream."""
    return session_key_choice(original_env, environ)["key"]


# ------------------------------------------------------------ the arm

def arm_env(base: dict, key: str, value: str) -> dict:
    """`base` plus one key, as a NEW dict.

    The base is the guard's own environment and is read again by the other
    arm; a mutation here would leave arm C running under arm B's key as
    well, and the record would have no way to say so.
    """
    return dict(base) | {key: value}


def run_arm(paths, cfg, rows, key, value, tag, deadline=None) -> dict:
    """One control arm: the same four rows, one key added, one row at a
    time -- each paired by ITS OWN invocation's launch timestamp.

    Not a batch. `refocus_one` finds the pair immediately after the
    invocation that produced it, which is the only thing that keeps H3's
    "pair 1 of 1" true once three arms have refocused one original into one
    store.

    `deadline` is `pass_two`'s OWN monotonic deadline, passed through by the
    runner. §1.4 bounds "the whole loop" at 1 h 30 min and these eight
    invocations are part of it: an arm that ran past the bound would be
    measuring outside every ceiling this record pre-registered. A row past
    the deadline is `not_run` with the same sentence `pass_two` writes, and
    it lands on `budget_exhausted`, which is what the phases' subset guard
    and §1.4's rules 4 and 5 both read.
    """
    mark_load(tag)
    answers, exhausted = [], []
    with logs_at((LOGS or Path(".")) / tag):
        for row in rows:
            if deadline is not None and time.monotonic() >= deadline:
                exhausted.append(row["name"])
                answers.append({"index": row["index"], "name": row["name"],
                                "target": row["target"], "arm": tag,
                                "original": row["original"],
                                "not_run": cfg.get("not_run_bound",
                                                   eph.NOT_RUN_BOUND)})
                continue
            answers.append(eph.refocus_one(paths, cfg, row["row"],
                                           extra_env={key: value},
                                           label=tag))
    measured = [a for a in answers if "not_run" not in a]
    out = {
        "arm": tag, "key": key, "value": value,
        "n": len(answers), "measured": len(measured), "refocuses": answers,
        "budget_exhausted": exhausted,
        "by_name": {a["name"]: a for a in answers},
        "rows": [r["name"] for r in rows],
        "expected_licence": {r["name"]: r["expected_licence"] for r in rows},
        "killed": [a["name"] for a in measured if a.get("timed_out")],
        "walls_s": {a["name"]: a.get("wall_s") for a in answers},
        "loop_deadline_monotonic": deadline,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    step(f"arm {tag}: {out['measured']}/{out['n']} row(s) with "
         f"{key}={value!r}; killed {out['killed']}; never run "
         f"{exhausted}; licences "
         f"{[(a.get('licence_partition') or {}).get('licence') for a in measured]}")
    return out


__all__ = ["ARM_B_KEY", "GRANTED_ROWS", "LOGS", "PAGER_ROW",
           "SESSION_CANDIDATES", "arm_env", "arm_rows", "choose_session_key",
           "run_arm", "session_key_choice"]
