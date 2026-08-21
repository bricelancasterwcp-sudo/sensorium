"""Seeded bug: main cancels task-B before opening the gate both workers are
parked at, so B's second step never runs and the total is 4, not 6. Both
workers are IDENTICAL (no arguments): which one was cancelled is decided in
main, by which handle main chose -- nothing inside a worker or a step can
tell them apart, and main already knows it cancelled b, so that is not the
question. What the trace holds and a print cannot: which task the one
surviving second step belongs to, and WHERE task-B was suspended when the
cancellation reached it.

The cancellation question pins a LINE NUMBER, so this file's line layout is
part of the fixture: do not reflow anything above `await GATE.wait()`
without re-checking the pin in questions.yaml.
"""
import asyncio

TOTAL = []
# created inside main so the program is a plain script; the pinned L29 below
# depends on this file's line layout -- do not reflow above the await
GATE = None


def step(n):
    TOTAL.append(n)
    return n


async def worker():
    step(1)
    await GATE.wait()
    return step(2)


async def main():
    global GATE
    GATE = asyncio.Event()
    a = asyncio.create_task(worker(), name="task-A")
    b = asyncio.create_task(worker(), name="task-B")
    await asyncio.sleep(0)          # both run step(1) and park at the gate
    b.cancel()                      # BUG: cancelled before the gate opens
    GATE.set()
    await a
    try:
        await b
    except asyncio.CancelledError:
        pass
    print(f"total: {sum(TOTAL)}")


if __name__ == "__main__":
    asyncio.run(main())
