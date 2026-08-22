"""What `--window` means once a coroutine can be suspended in the middle of
it: membership is ANCESTRY, not "everything that ran on this thread while
the window was open".

`windowed` and `other` both call the same `helper`, on the same thread, in
the same event loop, and they interleave: helper("out") runs BETWEEN
helper("in") and helper("in-again"), while `windowed` is parked at its
await. A window implemented as a per-thread depth counter would capture that
middle call as if it were inside `windowed`; a window derived from the
caller chain does not -- and it still captures helper("in-again"), which
runs after `windowed` resumes and is genuinely inside it.

So the same flag has to say no to one call and yes to the one after it,
where the three calls are adjacent in wall-clock order and identical in
every way a print could show. No planted bug: the fact under test is which
of three interleaved calls the instrument claims to have looked at.

DO NOT REFLOW OR REORDER THIS FILE. The line numbers are pinned by the
questions (`helper L23`), and so is the event order: `other` must call
`helper` BEFORE its own await, or "out" runs after `windowed` has already
returned and the case silently stops testing anything -- the two watch
questions would still pass, counting the same sites, while the interleaving
they describe no longer happened. The third question pins the recorded
order by event id so that this cannot go unnoticed.
"""
import asyncio


def helper(tag):
    x = tag
    return x


async def windowed():
    helper("in")
    await asyncio.sleep(0)      # `other` runs while this one is parked
    helper("in-again")


async def other():
    helper("out")               # runs while `windowed` is suspended
    await asyncio.sleep(0)


async def main():
    await asyncio.gather(windowed(), other())


if __name__ == "__main__":
    asyncio.run(main())
