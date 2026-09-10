"""E3-TS's JSON: what twenty recordings and nineteen `diff`s came to.

Reads the two tab-separated tables `e3.sh` wrote -- one line per recording,
one line per pair -- and turns them into the record's cell. Kept out of the
shell because the counts are the endpoint and a miscounted bucket is the
whole failure this endpoint exists to catch.

`value` is the number of DIVERGED pairs (the rule's first number, whose
PASS is 0); `refused` is the second. Both are `null` only when no pair could
be compared at all.
"""
import os
import sys

from lens import cell, emit

#: `diff`'s exit table, which IS its verdict (sensorium.exit).
MATCH, DIVERGED, BAD_CALL, REFUSED = 0, 1, 2, 3


def rows(path: str) -> list[list[str]]:
    with open(path, encoding="utf-8") as fh:
        return [line.rstrip("\n").split("\t") for line in fh if line.strip()]


def main() -> int:
    runs = rows(os.environ["E3_RUNS"])
    diffs = rows(os.environ["E3_DIFFS"])
    dropped = []

    recorded = [r for r in runs if r[1] != "-"]
    for r in runs:
        if r[1] == "-":
            dropped.append(f"recording {r[0]} left no trace (driver exit {r[2]})")

    buckets = {"match": [], "diverged": [], "refused": [], "bad_call": [],
               "no_trace": []}
    for k, run_id, code, *rest in diffs:
        verdict = rest[0] if rest else ""
        entry = {"k": int(k), "run": run_id, "verdict": verdict}
        if code == "no-trace":
            buckets["no_trace"].append(entry)
            continue
        code = int(code)
        name = {MATCH: "match", DIVERGED: "diverged", BAD_CALL: "bad_call",
                REFUSED: "refused"}.get(code)
        if name is None:
            dropped.append(f"pair {k}: diff exited {code}, which is not in "
                           "the exit table")
            continue
        buckets[name].append(entry)

    compared = sum(len(buckets[b]) for b in ("match", "diverged", "refused",
                                             "bad_call"))
    for entry in buckets["bad_call"]:
        dropped.append(f"pair {entry['k']}: diff exited 2 -- the call was "
                       "wrong, not the recording")
    for entry in buckets["no_trace"]:
        dropped.append(f"pair {entry['k']}: no trace to compare")

    emit(cell(
        None if compared == 0 else len(buckets["diverged"]),
        compared, dropped,
        test_file=os.environ["E3_FILE"],
        recordings=len(runs), recordings_with_a_trace=len(recorded),
        first=os.environ["E3_FIRST"],
        pairs=compared,
        diverged=len(buckets["diverged"]),
        refused=None if compared == 0 else len(buckets["refused"]),
        match=len(buckets["match"]),
        bad_call=len(buckets["bad_call"]),
        verdicts=sorted({e["verdict"] for e in buckets["match"]
                         + buckets["diverged"] + buckets["refused"]}),
        detail=buckets,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
