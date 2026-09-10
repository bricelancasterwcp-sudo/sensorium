"""The JSON for either §10 control, read off the `diff` transcripts.

    python3 control_report.py split|planted     (facts in the environment)

The split's claims, all four of which must hold:

    plain `diff` DIVERGED (exit 1)
    `--ignore-moves` MATCH modulo location (exit 0)
    `moved:` lists exactly the two functions that were moved
    the task section says every task matched

The planted change's two claims: plain `diff` DIVERGED (exit 1), and the
report names the causal step it diverged at. A MATCH is the failure this
control exists to catch, so a MATCH is reported as such and never smoothed
into "no difference found".

`value` is the number of the control's own claims that held.
"""
import json
import os
import re
import sys
from pathlib import Path

from lens import cell, emit

DIVERGED, MATCH = 1, 0
#: `moves.print_moves`: `  moved: <qualname>  <file a> -> <file b>`
MOVED = re.compile(r"^\s*moved: (\S+)\s+(\S+) -> (\S+)\s*$")

#: WHERE THE STEP IS NAMED, AND WHY THIS IS NOT THE VERDICT LINE.
#: When two runs part inside a task rather than on the thread stream, the
#: verdict line says `DIVERGED on the tasks (below)` and the step number is
#: printed by the TASK section: `first difference inside <task> (A task tN,
#: B task tM) at causal step K:`, with the two steps under it. This
#: instrument first looked for `causal step` in the verdict line alone and
#: so read "the step was not named" off a report that named it on the next
#: line but one -- the defect is recorded in the acceptance record's §5,
#: because it was found after the planted change had printed a number.
STEP = re.compile(r"at causal step (\d+)")


def read(key: str) -> str:
    return Path(os.environ[key]).read_text(encoding="utf-8", errors="replace")


def runs() -> list[dict]:
    out = []
    for line in read("E5TS_RUNS").splitlines():
        if not line.strip():
            continue
        label, status, run_id = line.split("\t")
        out.append({"stage": label, "driver_exit": int(status),
                    "run": run_id or None})
    return out


def verdict_line(text: str) -> str | None:
    return next((ln.strip() for ln in text.splitlines()
                 if ln.startswith("verdict:")), None)


def split() -> dict:
    plain = read("E5TS_PLAIN")
    lenient = read("E5TS_MOVES")
    plain_code = int(os.environ["E5TS_PLAIN_CODE"])
    moves_code = int(os.environ["E5TS_MOVES_CODE"])
    want = sorted(os.environ["E5TS_NAMES"].split(","))
    moved = [MOVED.match(ln).groups() for ln in lenient.splitlines()
             if MOVED.match(ln)]
    extras = [ln.strip() for ln in lenient.splitlines()
              if ln.lstrip().startswith(("removed (only in A):",
                                         "added (only in B):",
                                         "unpaired ("))]
    tasks_line = next((ln.strip() for ln in lenient.splitlines()
                       if ln.startswith("tasks:")), None)
    claims = {
        "plain_diff_diverged": plain_code == DIVERGED,
        "ignore_moves_match_modulo_location":
            moves_code == MATCH
            and "MATCH modulo location" in (verdict_line(lenient) or ""),
        "moved_is_exactly_the_two": sorted(m[0] for m in moved) == want
                                    and not extras,
        "every_task_paired": bool(tasks_line and "all matched" in tasks_line),
    }
    return cell(sum(1 for v in claims.values() if v), len(claims),
                control="E5-TS, the split",
                test_file=os.environ["E5TS_FILE"],
                edit=json.loads(read("E5TS_EDIT")),
                runs=runs(), claims=claims,
                plain={"exit": plain_code, "verdict": verdict_line(plain)},
                ignore_moves={"exit": moves_code,
                              "verdict": verdict_line(lenient),
                              "moved": [{"qualname": q, "from": a, "to": b}
                                        for q, a, b in moved],
                              "other_move_lines": extras,
                              "tasks": tasks_line})


def planted() -> dict:
    plain = read("E5TS_PLAIN")
    plain_code = int(os.environ["E5TS_PLAIN_CODE"])
    line = verdict_line(plain)
    step_line = next((ln.strip() for ln in plain.splitlines()
                      if STEP.search(ln)), None)
    step_no = STEP.search(step_line).group(1) if step_line else None
    claims = {"plain_diff_diverged": plain_code == DIVERGED,
              "report_names_the_step": step_line is not None}
    return cell(sum(1 for v in claims.values() if v), len(claims),
                control="the planted change",
                test_file=os.environ["E5TS_FILE"],
                edit=json.loads(read("E5TS_EDIT")),
                runs=runs(), claims=claims,
                plain={"exit": plain_code, "verdict": line,
                       "step_line": step_line, "causal_step": step_no,
                       "first_difference": [
                           ln.strip() for ln in plain.splitlines()
                           if ln.strip().startswith(("A:", "B:"))][:2]})


def main(argv) -> int:
    if len(argv) != 2 or argv[1] not in ("split", "planted"):
        sys.stderr.write("usage: control_report.py split|planted\n")
        return 2
    emit(split() if argv[1] == "split" else planted())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
