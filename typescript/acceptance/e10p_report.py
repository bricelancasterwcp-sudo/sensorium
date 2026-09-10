"""E10's JSON, guarded: the ingest walls, their median, and what they cost.

`value` is the median wall in seconds over the repetitions that CONVERTED --
a repetition that exited non-zero, or that reported a trace count other than
the copy's `.jsonl` count, converted something other than the workload and is
named in `dropped` rather than averaged in. `n` is how many were kept, so
`n` under the requested count is visible in the cell itself.

`walls` is every repetition's wall in order, dropped ones included, because a
dropped repetition's wall is evidence about the box and hiding it would leave
the record unable to say what happened. `value`, `min` and `max` are over the
kept ones only; `reps` carries each repetition whole, with the 1-minute load
the guard read before it and the peak RSS of its heaviest worker.

`converter_bin` and `converter_rev` come from the environment and are written
verbatim. Arm 0 measures the global tool while this file sits in a worktree
whose HEAD is a different commit, so a rev derived from the working directory
would label main's converter with the branch's -- the ladder's rungs are only
comparable if each says which converter it ran.
"""
import os
import statistics
import sys

from lens import cell, emit

#: One repetition's TSV line, as `e10p.sh` writes it.
FIELDS = ("rep", "wall", "exit", "traces", "load_1min", "maxrss_kb")


def _row(line: str) -> dict:
    k, wall, status, traces, load, maxrss = line.rstrip("\n").split("\t")
    return {"rep": int(k), "wall": round(float(wall), 4), "exit": int(status),
            "traces": int(traces), "load_1min": float(load),
            "maxrss_kb": int(maxrss)}


def _why_dropped(row: dict, spools: int) -> str | None:
    """The reason this repetition is not a measurement, or None."""
    if row["exit"] != 0:
        return f"repetition {row['rep']}: ingest exited {row['exit']}"
    if row["traces"] != spools:
        return (f"repetition {row['rep']}: converted {row['traces']} traces, "
                f"the copy holds {spools} spools")
    return None


def main() -> int:
    env = os.environ
    spools = int(env["E10P_SPOOLS"])
    rows, kept, dropped = [], [], []
    with open(env["E10P_WALLS"], encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = _row(line)
            rows.append(row)
            reason = _why_dropped(row, spools)
            if reason is None:
                kept.append(row)
            else:
                dropped.append(reason)
    walls = [r["wall"] for r in kept]
    emit(cell(
        round(statistics.median(walls), 4) if walls else None,
        len(kept), dropped,
        label=env["E10P_LABEL"], jobs=int(env["E10P_JOBS"]),
        spools=spools, spool_bytes=int(env["E10P_BYTES"]),
        walls=[r["wall"] for r in rows], reps=rows,
        min=min(walls) if walls else None, max=max(walls) if walls else None,
        loads=[r["load_1min"] for r in rows],
        maxrss_kb=max((r["maxrss_kb"] for r in kept), default=None),
        converter_bin=env["E10P_BIN"], converter_rev=env["E10P_REV"],
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
