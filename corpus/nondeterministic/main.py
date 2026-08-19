"""Seeded property, not a bug: this program's branch depends on state OUTSIDE
the process -- a counter file it reads and increments -- so no rerun ever
reproduces the previous execution.

Ground truth: `sensorium refocus` must report DIVERGED, never MATCH. That is
the CORRECT answer, not a flaw in this case: sensorium does not replay state
outside the process, so the rerun genuinely was a different execution.

Do NOT "fix" this back into a `random.random()` coin flip. A coin flip is the
honest illustration and a flaky corpus case: the refocus would land on MATCH
roughly half the time, and a suite that fails half the time teaches nobody
anything. Here the verdict is guaranteed while the REASON stays exactly the
real one. The harness copies each case into a fresh temp dir per run, so the
counter starts clean every time the suite runs.
"""
from pathlib import Path

COUNTER = Path("run_count.txt")


def pick():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    return n % 2 == 0


def left():
    return "L"


def right():
    return "R"


def main():
    print(left() if pick() else right())


if __name__ == "__main__":
    main()
