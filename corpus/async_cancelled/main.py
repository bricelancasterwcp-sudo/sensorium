"""Seeded bug: a task is cancelled while suspended and its second step never
runs; the program prints a total that silently omits it. The cancelled task's
coroutine is unframed, so arc 1 records its CALL and its first step, and --
honestly -- no RETURN, no frame, no closed_by.

This case also pins what arc 1 does NOT claim about an abandoned task, so
that arc 2 (coroutine frames with an ABANDONED state) has a failing case to
turn into a working one.
"""
import asyncio

TOTAL = []


def step(name, n):
    TOTAL.append(n)
    return n


async def worker(name, delay):
    step(name, 1)
    await asyncio.sleep(delay)
    return step(name, 2)


async def main():
    a = asyncio.create_task(worker("A", 0), name="task-A")
    b = asyncio.create_task(worker("B", 10), name="task-B")
    await a
    b.cancel()                       # BUG: B never gets to its second step
    try:
        await b
    except asyncio.CancelledError:
        pass
    print(f"total: {sum(TOTAL)}")


if __name__ == "__main__":
    asyncio.run(main())
