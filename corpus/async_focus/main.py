"""A --focus on a coroutine, and what it now buys.

Until 0.3.0 this case was the honesty-rule-2 fixture: the focus was
accepted, captured no line, and `watch` had to explain the silence with the
real reason -- coroutines opened no frame -- instead of blaming a
misspelling. The frame exists now, so the focus does what a focus on any
other function does: `name` and `visible` are recorded at the sites inside
the coroutine, and the predicate is actually evaluated there.

What the case still guards is the same thing from the other side. A
`watch` that comes back NOTHING WAS CHECKED here would be reporting a
capture gap that is gone; a `watch` that reports HITs it did not evaluate
would be worse. The pins name both the site count and the lines, so this
file's layout is part of the fixture.
"""
import asyncio


async def worker(name):
    visible = len(name)
    await asyncio.sleep(0)
    return visible


if __name__ == "__main__":
    print(asyncio.run(worker("A")))
