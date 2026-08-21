"""Seeded bug: two tasks write the same key of a shared store, so the
second writer silently overwrites the first. The output looks fine -- a value
is there -- it is just the wrong task's. The order is made deterministic with
an Event, so the final value is always B's.

The only framed code inside the tasks is the sync helper `update`; the
coroutine bodies are unframed. v1 parented every `update` to `<module>` and
recorded no task at all, so the question "which task made the final write?"
had no answer in the trace.
"""
import asyncio

STORE = {}


def update(key, value):
    STORE[key] = value
    return STORE[key]


async def writer(name, wait_for, signal):
    update("result", f"{name}:1")
    if wait_for is not None:
        await wait_for.wait()
    else:
        await asyncio.sleep(0)
    update("result", f"{name}:2")            # BUG: same key as the other task
    if signal is not None:
        signal.set()


async def main():
    a_done = asyncio.Event()
    a = asyncio.create_task(writer("A", None, a_done), name="task-A")
    b = asyncio.create_task(writer("B", a_done, None), name="task-B")
    await asyncio.gather(a, b)
    print(f"result: {STORE['result']}")


if __name__ == "__main__":
    asyncio.run(main())
