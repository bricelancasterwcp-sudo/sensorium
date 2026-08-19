"""Measure recording overhead: baseline vs default-depth vs focused.

This REPORTS, it never gates. Overhead is a tracked fact about a machine and
a workload, not a pass/fail property of the tool, so `--bench` always exits 0
and no threshold is asserted anywhere. A hardware-dependent threshold in a
test is a flaky test, and the honest home for the number is a printed table
with the machine named beside it.

WHAT IS TIMED
-------------
Whole-command wall clock: `python prog.py` against
`python -m sensorium run [--focus ...] -- prog.py`. That includes interpreter
startup, the recorder's own import and boot, and the final flush of the trace
to SQLite. It is what a user actually waits for, which is why it is the
headline -- but it means a short program's multiplier is mostly fixed cost.
So the fixed cost is measured separately, on a program that does nothing, and
printed beside the table: subtract it to reason about the marginal cost.

BEST OF N, NOT THE MEAN
-----------------------
Every measurement takes the MINIMUM of `reps` timed runs after one untimed
warm-up. The quantity being measured is a floor -- the work the machine must
do -- and background noise can only ever add to it, so the mean of a noisy
sample is a worse estimate of that floor than its minimum. The warm-up is
untimed because the first run of a fresh file pays for bytecode compilation
and a cold page cache, and it pays that in the baseline and the recorded run
alike but at different points in the total.

WHY TWO WORKLOADS
-----------------
The multiplier is not a property of sensorium. It is a property of how often
the traced program CALLS things, because the recorder's cost is per event and
a program's own cost is not. `call_dense` (naive recursive fib) is close to
the worst case that exists: every microsecond of its baseline is function
calls, so almost every microsecond gains a CALL and a RETURN event.
`work_between_calls` does real work inside a modest number of calls, which is
what ordinary code looks like. Reporting only one of them would be reporting
a number that generalises to nothing; the per-event cost printed in the last
column is the figure that travels, since a reader can multiply it by their
own event count.
"""
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Recursion whose entire cost is calls. The upper bound of the overhead range.
CALL_DENSE = '''
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

def main():
    total = 0
    for i in range(22):
        total += fib(i)
    print("total:", total)

if __name__ == "__main__":
    main()
'''

# Real work inside each call. Closer to what ordinary code costs.
WORK_BETWEEN_CALLS = '''
def transform(row):
    total = 0
    for ch in row:
        total += ord(ch) * 3
    return total % 97

def main():
    row = "row-payload-" * 40
    acc = 0
    for i in range(12000):
        acc += transform(row + str(i))
    print("acc:", acc)

if __name__ == "__main__":
    main()
'''

DO_NOTHING = 'if __name__ == "__main__":\n    pass\n'

# The focus target is chosen per workload and the choice is part of the
# measurement: `--focus` costs one LINE event per executed line of the named
# code, so focusing a hot inner loop and focusing a driver are different
# questions. `call_dense` focuses the hot recursive function -- the worst
# case. `work_between_calls` focuses the outer driver, which is what asking
# "show me the state in the function I am debugging" usually looks like.
WORKLOADS = {
    "call_dense": (CALL_DENSE, "prog:fib"),
    "work_between_calls": (WORK_BETWEEN_CALLS, "prog:main"),
}


def _best(cmd, cwd, env, reps) -> tuple[float, str]:
    """Minimum wall clock over `reps` timed runs, after one untimed warm-up."""
    best, out = None, ""
    for i in range(reps + 1):
        t0 = time.perf_counter()
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True,
                           check=True, text=True)
        dt = time.perf_counter() - t0
        out = r.stdout
        if i == 0:                # the warm-up: keep its output, not its time
            continue
        best = dt if best is None else min(best, dt)
    return best, out


def _event_count(stdout: str) -> int | None:
    """Events in the trace the recorded run just wrote, or None.

    None means the run printed no trace path -- reported as `-`, never as 0,
    because "no events" and "could not tell" are different facts.
    """
    m = re.search(r"^trace: (\S+)$", stdout, re.M)
    if m is None:
        return None
    from sensorium.store import db
    conn = db.open_trace(Path(m.group(1)))
    try:
        return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()


def measure(program: str = CALL_DENSE, focus: str | None = None,
            reps: int = 3) -> dict:
    """Time `program` un-recorded and recorded, in a disposable directory.

    SENSORIUM_DIR points inside that directory, so a benchmark run never
    writes to the user's own trace store.
    """
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "prog.py").write_text(program)
        env = {**os.environ, "SENSORIUM_DIR": str(wd / ".sensorium")}
        base, _ = _best([sys.executable, "prog.py"], wd, env, reps)
        rec = ["run"]
        if focus:
            rec += ["--focus", focus]
        rec += ["--", "prog.py"]
        recorded, out = _best([sys.executable, "-m", "sensorium", *rec],
                              wd, env, reps)
        events = _event_count(out)
    per_event = ((recorded - base) * 1e6 / events
                 if events else None)
    return {"baseline_s": round(base, 4), "recorded_s": round(recorded, 4),
            "multiplier": round(recorded / base, 1), "events": events,
            "us_per_event": None if per_event is None else round(per_event, 1)}


def _row(workload: str, tier: str, m: dict) -> str:
    events = "-" if m["events"] is None else str(m["events"])
    per = "-" if m["us_per_event"] is None else f"{m['us_per_event']:.1f}"
    return (f"{workload:<19} {tier:<8} {m['baseline_s']:>9.4f} "
            f"{m['recorded_s']:>9.4f} {m['multiplier']:>7.1f} "
            f"{events:>9} {per:>9}")


def report(reps: int = 3) -> dict:
    """Print the overhead table. Always returns; never raises on a number."""
    fixed = measure(DO_NOTHING, reps=reps)
    results = {}
    print(f"{'workload':<19} {'tier':<8} {'baseline':>9} {'recorded':>9} "
          f"{'x':>7} {'events':>9} {'us/event':>9}")
    for name, (source, focus) in WORKLOADS.items():
        tiers = {"default": measure(source, reps=reps),
                 "focused": measure(source, focus=focus, reps=reps)}
        for tier, m in tiers.items():
            print(_row(name, tier, m))
        results[name] = tiers
    overhead = fixed["recorded_s"] - fixed["baseline_s"]
    print(f"\nrecorder fixed cost: {overhead:.3f}s on a program that does "
          f"nothing ({fixed['baseline_s']:.4f}s -> {fixed['recorded_s']:.4f}s)."
          "\n  Every row above includes it, so a short program's multiplier is"
          " mostly this.")
    print(f"best of {reps} timed runs after one untimed warm-up; python "
          f"{sys.version.split()[0]}."
          "\n  Measurements of THIS machine and these workloads, not a promise"
          " about yours: the"
          "\n  multiplier tracks how call-dense the program is, and us/event"
          " is the figure that travels.")
    results["fixed_cost"] = fixed
    return results


if __name__ == "__main__":
    report()
