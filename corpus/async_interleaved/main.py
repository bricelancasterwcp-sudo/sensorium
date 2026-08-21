"""Seeded bug: two tasks write the same key of a shared store, so the second
writer silently overwrites the first. The output looks fine -- a value is
there -- it is just the wrong task's. An Event makes the order deterministic,
so the value that survives is always the one B wrote.

The values carry no identity. Both tasks write 1 and then 2, so the surviving
2 says nothing about who wrote it and neither does a print of every write:
the helper is handed a number, never a name. The only framed code inside the
tasks is the sync helper `update`; the coroutine bodies are unframed. v1
parented every `update` to `<module>` and recorded no task at all, so the
question "which task made the final write?" had no answer in the trace.
"""
import asyncio

STORE = {}


def update(key, value):
    STORE[key] = value
    return STORE[key]


async def writer(wait_for, signal):
    update("last_seen", 1)
    if wait_for is not None:
        await wait_for.wait()
    else:
        await asyncio.sleep(0)
    update("last_seen", 2)            # BUG: both tasks write the same key
    if signal is not None:
        signal.set()


async def main():
    a_done = asyncio.Event()
    a = asyncio.create_task(writer(None, a_done), name="task-A")
    b = asyncio.create_task(writer(a_done, None), name="task-B")
    await asyncio.gather(a, b)
    print(f"last_seen: {STORE['last_seen']}")


if __name__ == "__main__":
    asyncio.run(main())
