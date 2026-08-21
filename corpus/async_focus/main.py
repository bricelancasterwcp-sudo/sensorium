"""Honesty rule 2: a --focus on a coroutine is accepted, captures no line,
and `watch` must explain why with the real reason -- the code opens no
frame in this version -- not with "misspelled" or "frames this run did not
record". `name` is right there in the CALL payload.
"""
import asyncio


async def worker(name):
    visible = len(name)
    await asyncio.sleep(0)
    return visible


if __name__ == "__main__":
    print(asyncio.run(worker("A")))
