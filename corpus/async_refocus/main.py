"""Two asyncio tasks whose interleaving depends on state OUTSIDE the
process (a counter file, as in `nondeterministic`): the original run
starts task-A first, the rerun starts task-B first, and each task does the
same work either way. With --branch, the rerun ALSO sends task-B down
another path.

Ground truth: `refocus` says MATCH on the plain program -- tasks are
compared by content, the order they interleaved in is not compared and
says so -- and DIVERGED naming task-B on the branching program. A tool
that compared the thread's event order would call the plain program
DIVERGED: that is the false alarm plan 2b removes.

The pins name no line numbers, but the task names and function names are
part of the fixture.
"""
import asyncio
import sys
from pathlib import Path

COUNTER = Path("run_count.txt")


def step(n):
    return n


def other(n):
    return -n


async def worker(name, branch):
    step(1)
    await asyncio.sleep(0)
    if branch and name == "B":
        other(2)
    else:
        step(2)


async def amain(flip, branch):
    names = ["B", "A"] if flip else ["A", "B"]
    await asyncio.gather(*[
        asyncio.create_task(worker(n, branch), name=f"task-{n}")
        for n in names])


def main():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    # Harness order (corpus/run_corpus.py::run_case): run 1 (n=0), run 2
    # with --branch (n=1), then the questions: refocus of run 1 (n=2),
    # refocus of run 2 (n=3). The start order flips between a recording and
    # its rerun (n//2 parity); the branch fires only on the rerun of the
    # --branch recording (n >= 3). So question 1 differs by interleaving
    # alone, question 2 by task-B's content as well.
    flip = (n // 2) % 2 == 1
    branch = "--branch" in sys.argv and n >= 3
    asyncio.run(amain(flip, branch))
    print("done")


main()
