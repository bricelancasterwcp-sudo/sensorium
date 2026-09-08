#!/usr/bin/env python3
"""E4″'s two phases that are not about the SUBJECT: H7 and H8.

A module of its own for the reason `acceptance_e4p_phases2` is one -- this
project's 800-line ceiling, which `acceptance_e4pp_phases` reached when the
subset guard and the unread-reading branches landed in fix round 1 (H8),
and again when E4″ gaps 3 and 4 landed (H7, 2026-09-08). The seam is what
each phase is ABOUT: H1-H6 read the subject, H7 reads this record's own
instrument and H8 reads this repository, and H8 is besides the only phase
that runs COMMANDS rather than reading rows.

Both moves were pure: `_measured` came here with H7 and is imported back by
`acceptance_e4pp_phases`, so the import runs one way only.
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import acceptance_e4p_phases2 as eph2                              # noqa: E402
import acceptance_e4pp_rows as e4pp                                # noqa: E402
from acceptance_e4p_schema import licence_verified_counts          # noqa: E402
from acceptance_e6ppp import mark_load                             # noqa: E402
from acceptance_lib import REPO, step                              # noqa: E402

LOGS: Path | None = None


def _verdict(ok) -> str:
    """`None` is not a pass -- `acceptance_e4pp_phases._verdict`'s rule,
    spelled here so this module stands alone."""
    return "PASS" if ok is True else "STOP"


def _measured(block: dict) -> list[dict]:
    """Every row of an arm that actually ran. A row the loop bound cut off
    carries `not_run` and has no reading of any kind."""
    return [r for r in (block or {}).get("refocuses") or []
            if "not_run" not in r]


# ---------------------------------------------------------------------- H8

def corpus_case_names(paths) -> dict:
    """The corpus collector's OWN case list, by name.

    `run_corpus.py --json` publishes counts, not names -- E4′ §5's gap 3,
    which left `refocus_child_run_present` null and H6's "the new case
    included" unchecked. §1.4 makes the same reading a GATE here, so the
    names come from `load_cases()`, the very function the run iterates,
    asked in a child of its own. Cheap, and it builds nothing.
    """
    from acceptance_e4p_preflight import out_err
    py = str(REPO / ".venv" / "bin" / "python")
    res = out_err(py, "-c",
                  "import json, sys; sys.path.insert(0, '.'); "
                  "from corpus.run_corpus import load_cases; "
                  "print(json.dumps(sorted(c.name for c in load_cases())))")
    rec = {"command": res["command"], "rc": res["rc"], "names": None,
           "reason": None, "stderr": res["err"] or None}
    if res["rc"] != 0 or not res["out"]:
        rec["reason"] = (res["err"].splitlines()[-1].strip() if res["err"]
                         else f"the listing exited {res['rc']} and printed "
                              "nothing")
        return rec
    try:
        rec["names"] = _json.loads(res["out"].splitlines()[-1])
    except (ValueError, TypeError) as e:
        rec["reason"] = f"the listing did not parse as JSON: {e}"
    return rec


def spawned_presence(listing: dict, case: str) -> dict:
    """Is `case` in the collector's listing -- under EITHER spelling?

    E4″ gap 1. `load_cases()` names each case by its directory relative to
    `corpus/` (`run_corpus.Case(str(qfile.parent.relative_to(root)), …)`),
    so the 43 cargo cases are spelled `rust/<name>` and a bare name is in
    the listing exactly never. The reader asked for the bare name, found it
    absent and published a clean `False` on a case that was collected, ran
    under `--require-driver` and came back equal.

    Two changes, and the second is the one that matters. The whole name and
    the LAST PATH SEGMENT are both matched (a segment, never a substring:
    `rust/<case>_two` is a different case). And a name found under neither
    spelling is `null` WITH the listing's own command and rc as the reason
    -- because "this reader looked the wrong way" and "the case is gone"
    are different facts and a `False` cannot tell them apart, which is the
    named bug class. The gate does not move: `None` is not `True`.
    """
    names = listing.get("names")
    where = f"`{listing.get('command')}` exited {listing.get('rc')}"
    if names is None:
        return {"present": None, "matched": None,
                "reason": (f"the corpus case listing could not be read "
                           f"({listing.get('reason')}); {where}")}
    # One expression rather than two branches: `case` carries no path of its
    # own, so its whole-name test is subsumed by the segment test on every
    # name -- kept in the predicate because it is the reading the fix was
    # ruled in, and stated here because a branch nothing can reach is a
    # defect in an instrument even when it is harmless.
    hits = [n for n in names
            if n == case or str(n).rsplit("/", 1)[-1] == case]
    if hits:
        return {"present": True, "matched": hits[0], "reason": None}
    return {"present": None, "matched": None,
            "reason": (f"`{case}` is among the {len(names)} name(s) the "
                       f"listing printed under neither its whole name nor a "
                       f"last path segment; {where}")}


def phase_h8_nothing_else(paths, cfg) -> dict:
    """H8: did nothing else move? THIS repository, never the clone.

    E4′'s H6 with two differences §1.4 requires. The corpus runs WITH the
    driver (`--require-driver`, so a case nobody could run is a verdict on
    the run rather than a skip inside a green summary), and
    `spawned_test_fn_present` is read from the collector's own case list
    instead of from a JSON that publishes no names.

    Three commands, three return codes, each its own field: a summary line
    is prose and does not decide a gate.
    """
    rec = eph2.phase_h6(paths, cfg)
    listing = corpus_case_names(paths)
    corpus, python, cargo = (rec.get("corpus") or {}, rec.get("python") or {},
                             rec.get("cargo") or {})
    pres = spawned_presence(listing, e4pp.SPAWNED_CASE)
    present = pres["present"]
    skipped = [s for s in ((corpus.get("json") or {}).get("skipped") or [])
               if isinstance(s, dict)]
    out = {
        "corpus_rc": corpus.get("rc"),
        "pytest_rc": python.get("rc"),
        "cargo_rc": cargo.get("rc"),
        "pytest_summary": python.get("summary"),
        "corpus_cases": corpus.get("cases"),
        "corpus_failures": corpus.get("failures"),
        "corpus_errors": corpus.get("errors"),
        "corpus_skipped": skipped,
        "corpus_require_driver": (corpus.get("json") or {}).get(
            "require_driver"),
        "corpus_args": list(cfg.get("corpus_args") or []),
        "spawned_test_fn": e4pp.SPAWNED_CASE,
        "spawned_test_fn_present": present,
        # Which spelling answered, and why nothing did. A `True` that does
        # not say which name it matched is a reading nobody can check.
        "spawned_test_fn_matched": pres["matched"],
        "spawned_test_fn_reason": pres["reason"],
        "spawned_test_fn_skipped": [
            s for s in skipped
            if s.get("case") in (e4pp.SPAWNED_CASE, pres["matched"])],
        "case_listing": listing,
        "cargo_result_lines": cargo.get("result_lines"),
        "logs": {"corpus": corpus.get("log"), "pytest": python.get("log"),
                 "cargo": cargo.get("log")},
        "raw": rec,
        # One reason, from the reader that made it: an unread listing and a
        # name found under neither spelling are both "this went UNREAD",
        # and both carry the command a reader can re-run.
        "dropped": ([] if present is True else [pres["reason"] + ", so "
                    f"whether `{e4pp.SPAWNED_CASE}` is present went UNREAD"]),
        "gate": ("corpus rc 0 with `--require-driver` and the spawned-test "
                 "case present, pytest rc 0, `cargo test --workspace` rc 0"),
    }
    out["as_predicted"] = bool(
        out["corpus_rc"] == 0 and out["pytest_rc"] == 0
        and out["cargo_rc"] == 0 and present is True)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H8: corpus rc {out['corpus_rc']} (args {out['corpus_args']}, "
         f"{e4pp.SPAWNED_CASE} present={present} as "
         f"{pres['matched']!r}); pytest rc "
         f"{out['pytest_rc']}; cargo rc {out['cargo_rc']}; {out['verdict']}")
    return out


# ---------------------------------------------------------------------- H7


def _null_partition_cells(block: dict, arm: str) -> list[dict]:
    """Every pair whose licence PRINTED but whose thread arithmetic did
    not. The three cells H1 reads, and no others: whether the licence's own
    sentence named the exclusion is a fact about the WORDING and is H1's
    second reading, not an instrument failure."""
    out = []
    for r in _measured(block):
        part = r.get("licence_partition") or {}
        if part.get("licence") is None:
            continue
        missing = [c for c in ("program_threads", "harness_threads",
                               "counts_source") if part.get(c) is None]
        if missing:
            out.append({"name": r["name"], "arm": arm, "cells": missing,
                        "reason": part.get("counts_unread_reason")})
    return out


def phase_h7_instrument(raw: dict) -> dict:
    """H7: is the instrument honest? A STOP here is a STOP OF THE
    INSTRUMENT, and the record says so rather than reporting it as a
    finding about the subject.

    Four gates, and each closes one of E4′ §5's own gaps:

    * no partition cell is `None` on a pair whose licence printed (gap 1);
    * every thread count carries the line it came from (gap 1's other
      half);
    * `licence_verified_counts` is non-null (gap 7 -- E4′ named a field
      every reader found null);
    * the version probe is a token, or `null` WITH its reason, and never an
      empty string (gap 2).
    """
    mark_load("H7")
    arms_blocks = (("armA", raw.get("raw_pass2")),
                   ("armB", raw.get("raw_arm_b")),
                   ("armC", raw.get("raw_arm_c")))
    nulls, sources, sourceless = [], {}, []
    for arm, block in arms_blocks:
        if not block:
            continue
        nulls += _null_partition_cells(block, arm)
        for r in _measured(block):
            part = r.get("licence_partition") or {}
            if part.get("licence") is None:
                continue
            sources[f"{arm}/{r['name']}"] = part.get("counts_source")
            if part.get("counts_source") is None:
                sourceless.append(f"{arm}/{r['name']}")
    counts = licence_verified_counts(raw)
    probe = ((raw.get("pins") or {}).get("sensorium_version_metadata_probe")
             or {})
    token, reason = probe.get("token"), probe.get("reason")
    probe_ok = bool(token) or (token is None and bool(reason))
    out = {
        "headline": len(nulls), "null_cells": nulls,
        # The denominator this endpoint's numbers are over: every row of
        # every arm that came back with a licence WORD. Not the 61, and not
        # 69 either -- a row whose licence never printed has no partition to
        # be honest or dishonest about.
        "censused": len(sources),
        "counts_source_by_row": sources,
        "counts_without_a_source_line": sorted(sourceless),
        "counts_carry_their_source_line": bool(sources) and not sourceless,
        "licence_verified_counts": counts,
        "version_probe": {"token": token, "reason": reason,
                          "rc": probe.get("rc"),
                          "command": probe.get("command")},
        "version_probe_ok": probe_ok,
        "dropped_lists": _every_dropped(raw),
        "stop_is_of_the": ("instrument, not of the subject: §1.4's kill 2 "
                           "distinguishes the two in the record"),
        "dropped": [],
        "gate": ("0 null partition cells on a printed licence, every count "
                 "carrying its source line, non-null verified counts, and a "
                 "version probe that is a token or null WITH its reason"),
    }
    out["as_predicted"] = bool(
        not nulls and out["counts_carry_their_source_line"]
        and counts is not None and probe_ok)
    out["verdict"] = _verdict(out["as_predicted"])
    step(f"H7: {len(nulls)} null partition cell(s); source lines carried "
         f"{out['counts_carry_their_source_line']}; verified counts "
         f"{'present' if counts else 'MISSING'}; probe token {token!r} "
         f"reason {reason!r}; {out['verdict']}")
    return out


def _every_dropped(raw: dict) -> dict:
    """Every `dropped` list this run wrote, by phase -- H7's second reading.

    A record whose drops are scattered through eight blocks is one nobody
    reads; collected here, "what this run could not measure" is one list.
    """
    out = {}
    for key, block in sorted((raw or {}).items()):
        if key.startswith("raw_") and isinstance(block, dict):
            reasons = block.get("dropped")
            if reasons:
                out[key] = list(reasons)
    return out


__all__ = ["LOGS", "corpus_case_names", "phase_h7_instrument",
           "phase_h8_nothing_else", "spawned_presence"]
