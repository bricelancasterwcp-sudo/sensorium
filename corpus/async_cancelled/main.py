"""Seeded bug: a task is cancelled while suspended and its second step never
runs; the program prints a total that silently omits it.

Nothing the helper receives says which task it is running in -- `step` is
handed only the number to append, and both tasks append the same 1 -- so
"whose second step ran" is a fact about the execution that only the trace
holds. The cancelled task's coroutine is unframed, so arc 1 records its CALL,
its first step and the RAISE that ended it, and -- honestly -- no RETURN, no
frame, no closed_by.

This case also pins what arc 1 does NOT claim about an abandoned task, so
that arc 2 (coroutine frames with an ABANDONED state) has a failing case to
turn into a working one.
"""
import asyncio

TOTAL = []


def step(n):
    TOTAL.append(n)
    return n


async def worker(delay):
    step(1)
    await asyncio.sleep(delay)
    return step(2)


async def main():
    a = asyncio.create_task(worker(0), name="task-A")
    b = asyncio.create_task(worker(10), name="task-B")
    await a
    b.cancel()                       # BUG: B never gets to its second step
    try:
        await b
    except asyncio.CancelledError:
        pass
    print(f"total: {sum(TOTAL)}")


if __name__ == "__main__":
    asyncio.run(main())
