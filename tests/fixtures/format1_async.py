"""Two asyncio tasks, each calling a plain sync helper three times.

This file is the SOURCE of tests/fixtures/format1_async.db, recorded by the
v1 recorder at e384ef4 (trace_format 1). Do not edit it: the .db is a record
of what v1 wrote for exactly this program, and the test that reads it pins
how a format-2 reader describes a format-1 trace.
"""
import asyncio


def step(task, n):
    return f"{task}:{n}"


async def worker(name, delay):
    step(name, 1)
    await asyncio.sleep(delay)
    step(name, 2)
    await asyncio.sleep(delay)
    return step(name, 3)


async def main():
    a = asyncio.create_task(worker("A", 0.01), name="task-A")
    b = asyncio.create_task(worker("B", 0.02), name="task-B")
    return await asyncio.gather(a, b)


if __name__ == "__main__":
    print(asyncio.run(main()))
