"""Source of tests/fixtures/format2_async.db, recorded by sensorium 0.2.0
(main @ d59cafc, trace_format 2) with `--focus format2_async:worker`. Do not
edit: the .db is what 0.2.0 wrote for exactly this program, and the tests
pin how a format-3 reader describes a format-2 trace (arc-1 wording).

Shapes it holds: two tasks (one cancelled at an await), a generator helper
consumed by a sync function, a coroutine awaited by a coroutine.
"""
import asyncio


def step(task, n):
    return f"{task}:{n}"


def parse(s):
    return int(s)


def rows(items):
    for it in items:
        yield parse(it)


async def inner(name):
    return step(name, 0)


async def worker(name, delay):
    await inner(name)
    step(name, 1)
    await asyncio.sleep(delay)
    return step(name, 2)


async def main():
    total = sum(rows(["1", "2"]))
    a = asyncio.create_task(worker("A", 0), name="task-A")
    b = asyncio.create_task(worker("B", 10), name="task-B")
    await a
    b.cancel()
    try:
        await b
    except asyncio.CancelledError:
        pass
    return total


if __name__ == "__main__":
    print(asyncio.run(main()))
