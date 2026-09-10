"""E10's JSON: the ingest walls and their median.

`value` is the median wall in seconds. `n` is how many repetitions produced
a wall at all -- a repetition that exited non-zero converted nothing and is
named in `dropped` rather than averaged in.
"""
import os
import statistics
import sys

from lens import cell, emit


def main() -> int:
    env = os.environ
    walls, dropped, rows = [], [], []
    with open(env["E10_WALLS"], encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            k, wall, status, traces = line.rstrip("\n").split("\t")
            row = {"rep": int(k), "wall": round(float(wall), 4),
                   "exit": int(status), "traces": int(traces)}
            rows.append(row)
            if row["exit"] == 0:
                walls.append(row["wall"])
            else:
                dropped.append(f"repetition {k}: ingest exited {status}")
    emit(cell(
        round(statistics.median(walls), 4) if walls else None,
        len(walls), dropped,
        label=env["E10_LABEL"],
        spools=int(env["E10_SPOOLS"]), spool_bytes=int(env["E10_BYTES"]),
        walls=[r["wall"] for r in rows], reps=rows,
        min=min(walls) if walls else None, max=max(walls) if walls else None,
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
