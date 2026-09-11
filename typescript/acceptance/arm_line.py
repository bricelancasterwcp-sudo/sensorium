"""One line of `arms.jsonl`: everything `arms.sh` knows about one run.

Called by `arms.sh` with the run's facts in the environment, because a shell
that assembles JSON by hand gets a path with a quote in it wrong exactly
once. Reads the run's log for the two suite lines, vitest's `Duration` line
and its transform seconds, and -- for a driver arm -- measures the spool the
run left behind (bytes, lines, files), which is the ungated wire-cost pair
the record reports.

Prints one compact JSON object and nothing else.
"""
import json
import os
import re
import sys
from pathlib import Path

#: Vitest prints `Duration  22.30s (transform 10.26s, …)` on a big suite and
#: `Duration  307ms (transform 103ms, …)` on a small one. Both spellings, and
#: the units carried, because a dry run on the probe project read `123m` out
#: of a splitter that assumed seconds -- and crashed rather than lie, which is
#: how it was found.
TRANSFORM = re.compile(r"transform\s+([\d.]+)(ms|s)\b")


def spool_size(spool: str) -> dict:
    """Bytes, lines and file count over one invocation's `.jsonl` spools."""
    if not spool:
        return {}
    root = Path(spool)
    if not root.is_dir():
        return {}
    files = sorted(root.glob("*.jsonl"))
    total = lines = 0
    for path in files:
        data = path.read_bytes()
        total += len(data)
        lines += data.count(b"\n")
    return {"spool_files": len(files), "spool_bytes": total,
            "spool_lines": lines}


def main() -> int:
    env = os.environ
    log = Path(env["LOG"])
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    duration = next((ln.strip() for ln in text.splitlines()
                     if ln.lstrip().startswith("Duration")), None)
    transform = None
    m = TRANSFORM.search(duration or "")
    if m:
        transform = float(m.group(1)) / (1000.0 if m.group(2) == "ms" else 1.0)
    files_ok = env["WANT_FILES"] in text
    tests_ok = env["WANT_TESTS"] in text
    status = int(env["STATUS"])
    row = {
        "arm": env["ARM"],
        "batch": int(env["BATCH"]),
        "run": int(env["IDX"]),
        "wall": round(float(env["END"]) - float(env["START"]), 4),
        "harness_wall": (None if not env["HARNESS_WALL"]
                         else round(float(env["HARNESS_WALL"]), 4)),
        "load_1min": float(env["LOAD"]),
        "exit": status,
        "suite_files_ok": files_ok,
        "suite_tests_ok": tests_ok,
        "ok": files_ok and tests_ok and status == 0,
        "duration_line": duration,
        "transform_s": None if transform is None else round(transform, 4),
        "invocation": env["INV"] or None,
        "log": log.name,
    }
    row.update(spool_size(env["SPOOL"]))
    if not row["ok"]:
        row["why_not_ok"] = (
            [] + ([] if files_ok else ["Test Files line is not 372 passed (372)"])
            + ([] if tests_ok else ["Tests line is not 4278 passed (4278)"])
            + ([] if status == 0 else [f"exit status {status}"]))
    json.dump(row, sys.stdout, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
