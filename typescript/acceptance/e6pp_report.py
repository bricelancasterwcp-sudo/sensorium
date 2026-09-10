"""E6″'s JSON: the five clauses, the band, and the two arms that made it.

E6′ asked the same question with one plain run against a band five OTHER runs
had produced, and STOPped on a wall 0.65% outside it. E6″ re-asks it with a
band the session derives from its OWN before arm -- that arm's median plus or
minus that arm's range -- and with the after arm's MEDIAN over five guarded
runs, not one wall, as the number the clause tests.

`value` is how many of the five clauses held, out of five. A single number
cannot carry five claims, so every clause is beside it with the evidence it
was read from: the manifest check before and after, both arms whole, the
marker grep with the directories it searched, the wrapper listing, and the
call run that is the contamination source.

The timing clause has three words, not two. Fewer than four usable walls in
either arm means the band or the median was never measured, and an unmeasured
clause is `STOP by instrument` -- neither a pass nor a finding about the
recorder.
"""
import json
import os
import statistics
import sys
from pathlib import Path

from assemble import arm_stats
from lens import cell, emit

#: The suite the lens is pinned at, as `arms.sh` and `e6.sh` spell it. A run
#: that does not read both lines ran a different suite and is dropped.
WANT_FILES = " Test Files  372 passed (372)"
WANT_TESTS = "      Tests  4278 passed (4278)"

#: Spec 2.2: "Fewer than four usable walls in either arm ... makes the timing
#: clause a STOP by instrument". Five are run; four is the floor at which a
#: median and a range are still a measurement of the arm.
MIN_USABLE = 4

#: The five clauses of spec 2.2's table, in its order.
CLAUSE_NAMES = ("manifest_identical", "suite_is_the_suite", "zero_markers",
                "wrapper_gone", "plain_band")


def band_of(walls: list[float]) -> list[float] | None:
    """The before arm's own median, plus or minus the before arm's own range.

    No multiplier and no chosen width: `range = max - min` over the walls the
    arm actually produced, taken over the USABLE walls only -- a dropped run
    at 60 s would otherwise open a band nothing could fall outside.
    """
    if not walls:
        return None
    spread = max(walls) - min(walls)
    mid = statistics.median(walls)
    return [round(mid - spread, 4), round(mid + spread, 4)]


def timing(before: dict, after: dict) -> dict:
    """The timing clause, from the two arms' stats as `arm_stats` returns them."""
    band = band_of(before["walls"])
    usable = {"before": len(before["walls"]), "after": len(after["walls"])}
    short = [name for name, n in usable.items() if n < MIN_USABLE]
    if band is None or short:
        return {"band": band, "in_band": None, "usable": usable,
                "clause": "STOP by instrument",
                "why": [f"the {name} arm has {usable[name]} usable walls, "
                        f"fewer than the {MIN_USABLE} the rule requires"
                        for name in short]}
    in_band = band[0] <= after["median"] <= band[1]
    return {"band": band, "in_band": in_band, "usable": usable,
            "clause": "held" if in_band else "STOP", "why": []}


def clauses(contamination: dict, timing_clause: str) -> dict:
    """The five clause booleans and how many of them held.

    The band contributes `True` only when it was measured AND held: a
    `STOP by instrument` leaves it `None`, which counts as not held without
    claiming the recorder failed it.
    """
    verdicts = {name: bool(contamination[name]) for name in CLAUSE_NAMES[:-1]}
    verdicts["plain_band"] = (True if timing_clause == "held"
                              else False if timing_clause == "STOP" else None)
    return {"value": sum(1 for v in verdicts.values() if v is True),
            "n": len(CLAUSE_NAMES), "clauses": verdicts}


def manifest_reading(path: str) -> dict:
    """One `sha256sum -c` run, read back: OK lines, FAILED lines, exit."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    failed = [ln for ln in text.splitlines() if "FAILED" in ln]
    return {"ok": sum(1 for ln in text.splitlines() if ln.endswith(": OK")),
            "failed": failed, "lines": len(text.splitlines())}


def _markers(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return {"searched": [ln[len("searched: "):] for ln in text.splitlines()
                         if ln.startswith("searched: ")],
            "hits": [ln[len("hit: "):] for ln in text.splitlines()
                     if ln.startswith("hit: ")]}


def _rows(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def _call_run(call: dict | None) -> dict:
    """The contamination source's two walls, reported ungated (spec 3.6)."""
    if call is None:
        return {}
    return {"harness_wall": call["harness_wall"], "driver_wall": call["wall"],
            "invocation": call["invocation"], "ok": call["ok"],
            "exit": call["exit"], "duration_line": call["duration_line"],
            "spool_files": call.get("spool_files"),
            "spool_bytes": call.get("spool_bytes"),
            "spool_lines": call.get("spool_lines")}


def main() -> int:
    env = os.environ
    rows = _rows(env["E6PP_JSONL"])
    before = arm_stats(rows, "before", "wall")
    after = arm_stats(rows, "after", "wall")
    call = next((r for r in rows if r["arm"] == "call"), None)
    marks = _markers(env["E6PP_MARKERS"])
    check_before = manifest_reading(env["E6PP_MANIFEST_BEFORE"])
    check_after = manifest_reading(env["E6PP_MANIFEST_AFTER"])
    want_ok = int(env["E6PP_MANIFEST_LINES"])
    after_exit = int(env["E6PP_MANIFEST_AFTER_STATUS"])
    band = timing(before, after)

    identical = (after_exit == 0 and not check_after["failed"]
                 and check_after["ok"] == want_ok)
    # The clause is over the PLAIN runs -- the call run is the contamination
    # source, not one of the runs the suite clause is asked about.
    plain = [r for r in rows if r["arm"] in ("before", "after")]
    suite = bool(plain) and all(r["ok"] for r in plain)
    held = clauses({"manifest_identical": identical, "suite_is_the_suite": suite,
                    "zero_markers": not marks["hits"] and bool(marks["searched"]),
                    "wrapper_gone": env["E6PP_WRAPPER"] == "absent"},
                   band["clause"])

    dropped = before["dropped"] + after["dropped"] + band["why"]
    if not marks["searched"]:
        dropped.append("no vite/vitest cache directory existed to search -- "
                       "0 markers here is 0 files searched, not 0 found")
    emit(cell(
        held["value"], held["n"], dropped,
        clauses=held["clauses"], timing_clause=band["clause"],
        band=band["band"], in_band=band["in_band"], usable=band["usable"],
        n_per_arm=int(env["E6PP_N"]),
        manifest_before={**check_before, "exit": int(env["E6PP_MANIFEST_BEFORE_STATUS"]),
                         "want_ok": want_ok, "sha256": env["E6PP_MANIFEST_SHA"]},
        manifest_after={**check_after, "exit": after_exit, "want_ok": want_ok,
                        "identical": identical},
        before=before, after=after, call_run=_call_run(call),
        runs=rows, markers=marks, wrapper_dir=env["E6PP_WRAPPER"],
        wrapper_listing=env.get("E6PP_WRAPPER_LISTING", ""),
        recorder_bin=env["E6PP_BIN"], recorder_rev=env["E6PP_REV"],
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
