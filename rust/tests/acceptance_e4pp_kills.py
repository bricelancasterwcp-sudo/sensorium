#!/usr/bin/env python3
"""What E4″'s run EXITS as, and why: §1.4's kill rules and §1.3's dry check.

Split out of `acceptance_e4pp.py` at its `# ---- main` banner on 2026-09-08,
when the debts slice's own fixes took that file to 827 of an 800-line
ceiling. A pure move: this is the block that decides what a run MEANS --
which gated endpoint missed and on which side (§1.4's kill 2), whether a
`.FAILED` is a STOP or infrastructure (rules 4 and 5), and whether a dry run
checked the instrument at all (§1.3) -- and `acceptance_e4pp` imports every
name back, so the runner's own namespace is unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from acceptance_e4pp_rows import REFOCUS_TIMEOUT                   # noqa: E402


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


#: Exit 9's shapes, by name. All three are "relaunch from zero" and none is
#: a finding about the subject; a marker that carried only the number left
#: which one to a reader's memory, and the record carried it nowhere at all.
INFRASTRUCTURE_SHAPES = {
    "dry_did_not_check": ("a DRY run that did not check the instrument "
                          "(§1.3: the launch does not happen)"),
    "before_a_number": ("a `.FAILED` before any number had been read "
                        "(§1.4's rule 4: archive, empty the fresh "
                        "locations, re-make the 61 copies)"),
    "killed_in_a_dry_run": ("an invocation KILLED inside a DRY run, which "
                            "measures nothing about the subject: rule 5's "
                            "'the numbers already read stand' has no "
                            "numbers to stand, so the launch simply does "
                            "not happen"),
}


def infrastructure_shape(res: dict) -> str | None:
    """WHICH of exit 9's shapes a run is, or `None` when it is not one.

    Read by the marker and stamped into the record, so the distinction is a
    field rather than a sentence a reader has to parse back out of prose.
    """
    if res.get("dry_run_did_not_check_the_instrument"):
        return "dry_did_not_check"
    if not res.get("kill_is_infrastructure"):
        return None
    return "killed_in_a_dry_run" if res.get("dry_run") else "before_a_number"


def _infrastructure(res: dict) -> bool:
    """§1.4's rule 4 rather than its rule 5: a `.FAILED` BEFORE any number
    had been read. The run is archived and relaunched from zero, which is
    not the same event as a STOP and must not carry a STOP's exit code."""
    if res.get("dry_run"):
        # And a DRY run is never rule 5 either. It measures nothing about
        # the subject, so there are no numbers for "the numbers already
        # read stand" to be about -- §1.3's own words are that a dry run
        # that does not check the instrument is infrastructure and never a
        # STOP. A dry whose row was killed after a reading was exiting 7,
        # which told the controller a finding had been made.
        return True
    if res.get("numbers_read"):
        return False
    for key in ("raw_pass2", "raw_arm_b", "raw_arm_c"):
        block = res.get(key) or {}
        if (block.get("killed") or block.get("budget_exhausted")):
            return True
    return False


__all__ = ["GATED", "INFRASTRUCTURE_SHAPES", "_infrastructure",
           "_stops", "dry_check", "infrastructure_shape",
           "stop_side", "stop_sides"]
