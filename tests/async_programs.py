"""The coroutine and generator program shapes, kept apart from the rest.

Split out of `programs.py` when it reached the 800-line ceiling, along the
seam the material has: every shape here is closed by something *delivered*
into a suspended frame -- a cancel thrown at the next await, a GeneratorExit
thrown at a yield, a parked generator that is never resumed -- which is the
one class of shape `programs.py`'s sync sources cannot express.
"""
# Swallowed inside a coroutine, which is LATER killed by a CancelledError
# thrown in at its next suspension point. The frame unwinds -- but with
# something delivered after the handler ran, which says nothing about the
# ValueError the handler kept.
CORO_SWALLOW_THEN_CANCELLED = """
import asyncio
GATE = None

async def worker():
    try:
        int("x")
    except ValueError:
        pass                      # swallowed inside the coroutine
    await GATE.wait()             # then the task is cancelled here

async def amain():
    global GATE
    GATE = asyncio.Event()
    t = asyncio.create_task(worker())
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass

asyncio.run(amain())
"""

# The cancel is caught inside the coroutine and let straight back out. The
# frame IS unwound by an exception thrown into it -- but by THIS one, so the
# thrown-in rule must stay silent: nothing in `worker` swallowed it.
CORO_RERAISES_ITS_CANCEL = """
import asyncio
GATE = None

async def worker():
    try:
        await GATE.wait()
    except asyncio.CancelledError:
        raise                     # caught, and let straight back out

async def amain():
    global GATE
    GATE = asyncio.Event()
    t = asyncio.create_task(worker())
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass

asyncio.run(amain())
"""

# Caught inside a coroutine and STASHED -- handed out of the frame by
# reference, exactly as `except E as e: return e` does -- and the frame is
# then cancelled. The handler frame did not return normally AND the exception
# is raised again later: both facts have to survive into the verdict.
CORO_STASH_THEN_CANCELLED = """
import asyncio
GATE = None
STASH = []

async def worker():
    try:
        int("x")
    except ValueError as e:
        STASH.append(e)           # kept, not swallowed: handed out of here
    await GATE.wait()             # then the task is cancelled here

async def amain():
    global GATE
    GATE = asyncio.Event()
    t = asyncio.create_task(worker())
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
    raise STASH[0]                # the stashed exception, raised again

asyncio.run(amain())
"""

# Swallowed inside a generator that is then DROPPED while parked: CPython
# throws GeneratorExit into it at the yield. A death delivered after the
# handler ran, like a cancel -- and named in its own words.
GEN_SWALLOW_THEN_DROPPED = """
def gen():
    try:
        int("x")
    except ValueError:
        yield -1                  # swallowed, then dropped while parked here
    yield 0

def main():
    g = gen()
    next(g)
    del g                         # GeneratorExit thrown in at the yield

main()
"""

# Swallowed inside a generator that is then thrown INTO by its driver. Same
# shape as a cancel, but the exception is an ordinary one, so the tail has to
# name it rather than claim the frame itself was "thrown".
GEN_SWALLOW_THEN_THROWN = """
def gen():
    try:
        int("x")
    except ValueError:
        yield -1                  # swallowed, then KeyError thrown in here
    yield 0

def main():
    g = gen()
    next(g)
    g.throw(KeyError("k"))        # not caught: the run ends here

main()
"""

# Swallowed inside a generator that is then parked forever: the frame is still
# suspended when recording stops, so nothing says what it would have done with
# the exception. The honest answer stays "ambiguous".
GEN_SWALLOW_THEN_PARKED = """
KEEP = []

def gen():
    try:
        int("x")
    except ValueError:
        yield -1                  # swallowed, then parked here for good
    yield 0

def main():
    g = gen()
    next(g)
    KEEP.append(g)

main()
"""
