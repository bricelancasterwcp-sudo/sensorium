"""H7: what does the focus tier cost? Reported, never gated.

    .venv/bin/python typescript/acceptance/e12_cost.py <arms.jsonl> <out dir>

§1's H7 is "F against U, the test file's wall, n=3 each, interleaved, medians,
under the slice-2 load guard; the resolver's wall beside it; **reported, not
gated**". So this file computes medians and says how many walls each came from
-- and issues no verdict, because the pre-registration issues none.

A run that did not finish, or whose suite lines the driver never printed, is
DROPPED and named rather than averaged in: `n` is how many walls the median
was taken over and `dropped` says which runs are missing and why. An arm with
no usable wall gets a `null` median, never a zero -- an unmeasured cost is not
a cost of nothing.

The resolver's wall is `e12.sh`'s own timing of `node resolve.mjs`, because
Task 5 left `Resolution.wall` unpersisted; it is one number from one run and
is reported as such, with no median and no band.
"""
import json
import os
import statistics
import sys
from pathlib import Path

from lens import cell, emit, usage

#: The two arms, spelled as `e12.sh` writes them into `arms.jsonl`.
ARMS = ("U", "F")


def usable(rows: list[dict], arm: str) -> tuple[list[float], list[str]]:
    """One arm's walls, and why any run of it was dropped."""
    walls, dropped = [], []
    for row in sorted((r for r in rows if r["arm"] == arm),
                      key=lambda r: r["run"]):
        why = []
        if row["exit"] != 0:
            why.append(f"exit {row['exit']}")
        if row["test_files_line"] is None or row["tests_line"] is None:
            why.append("the harness printed no `Test Files`/`Tests` line")
        if row.get("run_id") is None:
            why.append("no single container recorded the subject file "
                       f"(run ids: {row.get('run_ids')})")
        if why:
            dropped.append(f"{arm}{row['run']}: " + "; ".join(why))
            continue
        walls.append(row["wall"])
    return walls, dropped


def arm(rows: list[dict], name: str) -> dict:
    walls, dropped = usable(rows, name)
    return {"runs": sum(1 for r in rows if r["arm"] == name),
            "walls": walls, "dropped": dropped,
            "median": round(statistics.median(walls), 4) if walls else None,
            "min": min(walls) if walls else None,
            "max": max(walls) if walls else None,
            "loads": [r["load_1min"] for r in rows if r["arm"] == name]}


def main(argv) -> int:
    if len(argv) != 3:
        usage("usage: e12_cost.py <arms.jsonl> <out dir>")
    arms_path, out = Path(argv[1]), Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(ln) for ln in
            arms_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    stats = {name: arm(rows, name) for name in ARMS}
    session = json.loads((arms_path.parent / "e12.json").read_text(
        encoding="utf-8")) if (arms_path.parent / "e12.json").is_file() else {}
    resolver = (session.get("resolver") or {})

    dropped = [d for s in stats.values() for d in s["dropped"]]
    ratio = None
    if stats["U"]["median"] and stats["F"]["median"]:
        ratio = round(stats["F"]["median"] / stats["U"]["median"], 4)
    else:
        dropped.append("no F/U ratio: one of the two medians was not measured")
    # `value` is the F median -- the number H7 exists to report -- and `n` is
    # how many walls it was taken over. Neither is a threshold.
    payload = cell(
        stats["F"]["median"], len(stats["F"]["walls"]), dropped,
        rule="reported, not gated",
        unfocused=stats["U"], focused=stats["F"],
        focused_over_unfocused=ratio,
        resolver={"wall": resolver.get("wall"), "exit": resolver.get("exit"),
                  "files_scanned": resolver.get("files_scanned"),
                  "note": "one timed run of `node resolve.mjs` in `e12.sh`; "
                          "`Resolution.wall` is not persisted (Task 5)"},
        recorder=os.environ.get("E12_RECORDER"),
        recorder_rev=os.environ.get("E12_REV"))
    (out / "e12-h7.json").write_text(json.dumps(payload, indent=2) + "\n",
                                     encoding="utf-8")
    emit(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
