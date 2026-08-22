"""Recorded program shapes, plus the fixtures that record them.

Shared by `test_exceptions.py`, `test_grep.py` and the two `flow` files.
Each source string is one program *shape* -- the unit the exception
classifier is tested in, because the head of a trace is byte-identical for
behaviours that mean opposite things and only whole-program shapes separate
them. The `flow` shapes at the bottom are here for the same reason: what
`flow --object` may claim turns on whole-program allocation behaviour.
"""
from sensorium import paths
from sensorium.record.tracer import _RETAIN_MAX
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script

# -- program shapes --------------------------------------------------------

# Genuine swallow: `except Exception: pass`. RAISE lands in parse_row's frame
# (int() is C code and untraced), HANDLED lands in load_all's frame, and
# load_all returns normally -- the only shape where closed_by == "return".
SWALLOW = """
ROWS = ["alice,10", "bob,20", "carol,x7", "dan,5", "erin,??"]

def parse_row(row):
    name, amount = row.split(",")
    return name, int(amount)

def load_all(rows):
    out = []
    for row in rows:
        try:
            out.append(parse_row(row))
        except Exception:
            pass
    return out

def main():
    rows = load_all(ROWS)
    print(f"total: {sum(a for _, a in rows)} from {len(rows)} rows")

if __name__ == "__main__":
    main()
"""

CRASH = """
def get(uid):
    return {1: "Alice"}.get(uid)

def main():
    get(1)
    get(7).title()

main()
"""

# Bare `raise` in the handler: RAISE + two HANDLED rows, no later RAISE --
# the trace head a naive classifier reads as SWALLOWED. It is not: the frame
# holding both HANDLED rows is closed_by "unwind" with the same exception.
BARE_RERAISE = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError:
        raise

def main():
    risky()

main()
"""

# Never caught anywhere, merely passes through a bare `finally`. Verified:
# two HANDLED rows and every frame closed_by "unwind". Same trace head again.
FINALLY_PASSTHROUGH = """
def inner():
    raise ValueError("boom")

def middle():
    try:
        inner()
    finally:
        pass

def main():
    middle()

main()
"""

# Caught, then replaced by a different exception.
TRANSLATED = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        raise RuntimeError("wrapped") from e

def main():
    try:
        risky()
    except RuntimeError:
        pass

main()
"""

# Genuinely swallowed, and then the same frame dies of something unrelated.
# Recorded side by side with TRANSLATED the two traces are identical apart
# from line numbers, so the classifier must reach the same verdict for both;
# claiming either "swallowed" or "propagated" here would be a false accusation
# on one of them. (`raise X from e` sets __context__ and the unrelated raise
# does not -- but capture_exc records only type/msg/oid, so the trace has no
# way to tell. Recording __context__ would separate them; that is a recorder
# change, not a query-side one.)
SWALLOW_THEN_UNRELATED = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError:
        pass
    raise RuntimeError("later, unrelated")

def main():
    try:
        risky()
    except RuntimeError:
        pass

main()
"""

# Raised inside untraced library code (json), caught in traced code.
UNTRACED_LIB = """
import json

def parse(text):
    try:
        return json.loads(text)
    except ValueError:
        return None

def main():
    print(parse('{"a": 1}'))
    print(parse('not json'))

main()
"""

# Bare re-raise whose handler lives in code the run does not trace. The trace
# records the raise and the cleanup HANDLED and then simply stops knowing.
RERAISE_CAUGHT_UNTRACED = """
import lib

def risky():
    try:
        raise ValueError("boom")
    except ValueError:
        raise

def main():
    print(lib.guarded(risky))

main()
"""

UNTRACED_LIB_SOURCE = """
def guarded(fn):
    try:
        return fn()
    except ValueError:
        return "caught in untraced library"
"""

# Raised in traced code, caught in untraced code, with no `try` in traced code
# at all: EXCEPTION_HANDLED fires in the library frame and is not recorded, so
# the trace holds a RAISE and no HANDLED whatsoever.
RAISE_CAUGHT_UNTRACED = """
import lib

def risky():
    raise ValueError("boom")

def main():
    print(lib.guarded(risky))

main()
"""

# `raise e` (by name, not bare) fires RAISE, not RERAISE, so the same object
# gets a second RAISE row -- the one shape where "raised again" is provable.
EXPLICIT_RERAISE = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        raise e

def main():
    try:
        risky()
    except ValueError:
        pass

main()
"""

# Same, but nothing catches the second raise: two RAISE rows share one
# identity and the header must name the one that actually escaped.
EXPLICIT_RERAISE_ESCAPES = """
def risky():
    try:
        raise ValueError("boom")
    except ValueError as e:
        raise e

def main():
    risky()

main()
"""

# `except E as e: return e` -- an ordinary idiom. The handler frame closes
# "return", which is the swallow signal, and yet the exception is stored,
# re-raised by the caller, and kills the process. Fix round 1: this was
# reported as "SWALLOWED ... never re-raised" two lines under a header that
# said the same exception was uncaught -- the tool contradicting itself.
STASH_AND_RERAISE = """
def stash():
    try:
        raise ValueError("x")
    except ValueError as e:
        return e

def main():
    raise stash()

main()
"""

# Fix round 2. A plain retry loop, and the shape that disproved the premise
# both earlier rounds leaned on -- that address reuse "needs a synthetic
# trace". It does not. `except ValueError as e: pass` drops the binding at
# the end of each handler, so the object is freed before the next iteration
# allocates, and CPython hands the new one the *same address*. Measured: all
# three ValueError('fail') objects here share one oid. Because the handler
# frame unwinds (main dies of the RuntimeError), rule 2 cannot fire and the
# classifier reached rule 3, which asserted "then raised again at eN" twice
# -- one exception reported as re-raised when there were three separate ones.
RETRY_LOOP_REUSED_ADDRESS = """
def main():
    for i in range(3):
        try:
            raise ValueError("fail")
        except ValueError as e:
            pass
    raise RuntimeError("gave up")

main()
"""

# The same collision pressure with a *genuine* re-raise at the end: the last
# attempt's exception is stored and re-raised from a different statement, so
# this one must stay confident. Measured: the three attempt() exceptions get
# distinct addresses here (the `last = e` binding keeps each alive across the
# next allocation), and e12 really is the same object as e10.
RETRY_THEN_RAISE_LAST = """
def attempt(i):
    raise ValueError("fail")

def main():
    last = None
    for i in range(3):
        try:
            attempt(i)
            break
        except ValueError as e:
            last = e
    raise last

main()
"""

# Fix round 3. The shape that disproved round 2's soundness argument: the
# handler lives in UNTRACED code, so it ends the exception's flight and frees
# the object while leaving no HANDLED row at all -- `tracer._exc_event` clears
# `last_exc` before it checks whether the code is traced. A fresh exception
# then takes the freed address. Two provably distinct objects, one address,
# zero HANDLED rows, which the classifier read as "it never stopped
# propagating, so its address cannot have been reused". Both clauses false.
UNTRACED_HANDLER_REUSED_ADDRESS = """
import lib

def boom():
    raise ValueError("dup")

def main():
    lib.guarded(boom)
    raise ValueError("dup")

main()
"""

SWALLOWING_LIB_SOURCE = """
def guarded(fn):
    try:
        fn()
    except ValueError:
        pass
"""

# Fix round 4. STASH_AND_RERAISE with one ordinary complication: an unrelated
# exception is raised and handled *between* the stash and the re-raise. Round
# 3 remembered the last-handled exception in a single slot, so the RuntimeError
# evicted the stored ValueError and the re-raise minted a second serial for one
# object -- printing "SWALLOWED ... never re-raised" two lines under a header
# saying that same exception left the program. Nothing here is exotic; the
# noise is what any program does between stashing an error and raising it.
STASH_NOISE_RERAISE = """
def stash():
    try:
        raise ValueError("x")
    except ValueError as e:
        return e

def noise():
    try:
        raise RuntimeError("unrelated")
    except RuntimeError:
        pass

def main():
    saved = stash()
    noise()
    raise saved

main()
"""

# The mirror shape, also fix round 4: nothing is stored, but an exception is
# raised AND handled inside a `finally` while another is still in flight. With
# a single "current serial" slot the inner KeyError's serial was stamped onto
# the outer ValueError's later rows -- one object under two identities and two
# objects under one. The classifier then read the outer ValueError's own unwind
# as a different exception and printed "f3 then unwound with ValueError('outer')"
# about ValueError('outer'), missing the swallow in main entirely.
CLEANUP_RAISES_ITS_OWN = """
def cleanup():
    try:
        raise KeyError("inner")
    except KeyError:
        pass

def mid():
    try:
        raise ValueError("outer")
    finally:
        cleanup()

def main():
    try:
        mid()
    except ValueError:
        pass

main()
"""

# The retention bound, crossed on purpose. The recorder remembers at most
# _RETAIN_MAX exceptions per thread, so a stash separated from its re-raise by
# more than that many other exceptions comes back with a FRESH serial: the link
# is genuinely gone, and no recorder change can conjure it back. This is the
# shape that proves the query side refuses to call such a raise swallowed --
# the recorder fix alone only moves the boundary, it does not remove it.
#
# Each noise exception gets its own class so that no two of them can share a
# (type, address) pair; that keeps the disposition tally exact instead of
# depending on which addresses CPython happens to recycle.
STASH_PAST_RETENTION = f"""
def stash():
    try:
        raise ValueError("kept")
    except ValueError as e:
        return e

def churn(n):
    for i in range(n):
        cls = type(f"Noise{{i}}", (Exception,), {{}})
        try:
            raise cls("noise")
        except Exception:
            pass

def main():
    saved = stash()
    churn({_RETAIN_MAX + 6})
    raise saved

main()
"""

# The same bound crossed from the other side: nothing is stored, but the
# cleanup an exception passes through on its way out raises and handles more
# exceptions than the recorder retains, so the exception in flight is forgotten
# mid-flight and the frame it finally leaves carries a fresh serial for it.
# Read as "the frame unwound with some other exception", that would deny that
# this exception left the frame -- about the very exception being named.
IN_FLIGHT_PAST_RETENTION = f"""
def cleanup(n):
    for i in range(n):
        cls = type(f"Noise{{i}}", (Exception,), {{}})
        try:
            raise cls("noise")
        except Exception:
            pass

def mid():
    try:
        raise ValueError("outer")
    finally:
        cleanup({_RETAIN_MAX + 6})

def main():
    try:
        mid()
    except ValueError:
        pass

main()
"""

RETENTION_NOISE_COUNT = _RETAIN_MAX + 6

# Serials are minted per thread, so two worker threads both start at 1. If the
# classifier keyed on the serial alone it would fuse two unrelated exceptions
# from different threads into one identity.
THREADED_SWALLOWS = """
import threading

def work(tag):
    try:
        raise ValueError("thread fail")
    except ValueError:
        pass

def main():
    ts = [threading.Thread(target=work, args=(i,)) for i in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print("done")

main()
"""

# Three raises of an identically-typed, identically-messaged exception. Each
# must pair with its own handler, not with a neighbour's.
LOOP_SAME_MESSAGE = """
def boom(i):
    raise ValueError("same message")

def main():
    for i in range(3):
        try:
            boom(i)
        except ValueError:
            pass
    print("done")

main()
"""

# A handler inside a generator. Until frames covered generators there was no
# `closed_by` to read here and the verdict was withheld; the generator body is
# framed now, so this swallow is decidable like any other.
GENERATOR_HANDLES = """
def gen(items):
    for it in items:
        try:
            yield int(it)
        except ValueError:
            yield -1

def main():
    print(list(gen(["1", "x", "3"])))

main()
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

CLEAN = """
def add(a, b):
    return a + b

def main():
    print(add(1, 2))

main()
"""

# Re-raised through an inner frame, then genuinely caught by an OUTER traced
# frame -- which afterwards dies of an unrelated exception. The inner frame
# unwinds carrying the ValueError (a re-raise), but the exception did NOT
# leave traced code: `caller` caught it. Its true fate is what the OUTERMOST
# handler did, `caller`'s frame later unwinding with an unrelated KeyError, so
# the honest verdict is the same "handled here, frame died of something else"
# ambiguity as TRANSLATED -- never "propagated (handler not in traced code)",
# which is contradicted by the HANDLED row in `caller`.
RERAISE_CAUGHT_THEN_FRAME_DIES = """
def reraiser():
    try:
        raise ValueError("inner")
    except ValueError:
        raise

def caller():
    try:
        reraiser()
    except ValueError:
        pass
    return {}["missing"]

def main():
    caller()

main()
"""

# A user class that merely SHARES the name `StopIteration` with the builtin --
# it is not the interpreter's iterator-protocol exception, it is an ordinary
# error raised in ordinary code and caught. A name-based control-flow filter
# drops it entirely (no RAISE, no HANDLED, no serial) and `exceptions` then
# says "no exceptions recorded"; a type-based filter records and classifies it.
SHADOWED_CONTROL_FLOW_NAME = """
class StopIteration(Exception):
    pass

def scan(items):
    for x in items:
        if x < 0:
            raise StopIteration("negative found")
    return sum(items)

def main():
    try:
        scan([1, 2, -3, 4])
    except StopIteration:
        print("caught my StopIteration")

main()
"""


def record(tmp_path, monkeypatch, src, extra=(), files=()):
    for name, text in files:
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    run_id, _trace, r = record_script(tmp_path, src, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def synthetic(tmp_path, monkeypatch, run_id="20260101-000000-abcdef"):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    return w


def exc_payload(type_, msg, oid, serial=None):
    """A recorded exception payload. Omit `serial` to build a LEGACY trace --
    one recorded before the tracer minted exact identities."""
    out = {"type": type_, "msg": msg, "oid": oid}
    if serial is not None:
        out["serial"] = serial
    return out


# -- flow shapes -----------------------------------------------------------
# Shared by `test_flow.py` (equality) and `test_flow_identity.py` (identity).
GRAMS = """
def shipping_cost(weight_kg):
    return 4.0 + 2.5 * weight_kg

def item_weight(item):
    return item["grams"]

def order_total(items):
    goods = sum(i["price"] for i in items)
    ship = sum(shipping_cost(item_weight(i)) for i in items)
    return round(goods + ship, 2)

def main():
    items = [{"name": "mug", "price": 12.0, "grams": 400},
             {"name": "kettle", "price": 49.0, "grams": 1800}]
    print("total:", order_total(items))

if __name__ == "__main__":
    main()
"""

ALIAS = """
def make_default():
    return {"retries": 3, "timeout": 30}

def derive_sandbox(cfg):
    sandbox = cfg
    sandbox["timeout"] = 1
    return sandbox

def main():
    prod = make_default()
    sand = derive_sandbox(prod)
    print("prod timeout:", prod["timeout"])

if __name__ == "__main__":
    main()
"""

def open_trace(run_id) -> Trace:
    return Trace.open(paths.find_trace(run_id))


def flow_rows(out: str) -> list[str]:
    """The sighting lines: `  e<id> KIND ...   [role]`."""
    return [ln.strip() for ln in out.splitlines()
            if ln.startswith("  e") and ln.rstrip().endswith("]")]


def obj_captures(trace) -> list[tuple[int, int, str]]:
    """(event id, oid, type) for every top-level `obj` capture recorded.

    Deliberately re-derived here from the payloads rather than through
    flow_cmd, so the fixture's address collisions are established
    independently of the code under test.
    """
    out = []
    for e in trace.events():
        p = e.payload or {}
        vals = list(p.get("args", {}).values()) + list(
            p.get("deltas", {}).values())
        if p.get("value") is not None:
            vals.append(p["value"])
        for v in vals:
            if v.get("k") == "obj":
                out.append((e.id, v["oid"], v["type"]))
    return out


def interleaved_address(trace, a: str, b: str):
    """The address that hosted an `a`, then a `b`, then an `a` again.

    Returns (address, [(event id, type), ...] at it). Three objects minimum,
    one address: the shape that makes `oid` alone a false identity.
    """
    by_oid: dict[int, list] = {}
    for eid, oid, typ in obj_captures(trace):
        by_oid.setdefault(oid, []).append((eid, typ))
    for oid, seq in by_oid.items():
        types = [t for _e, t in seq]
        if a not in types or b not in types:
            continue
        rest = types[types.index(a):]
        if b in rest and a in rest[rest.index(b):]:
            return oid, seq
    raise AssertionError(
        f"this test needs one address hosting {a}, then {b}, then {a} again; "
        f"CPython allocated {by_oid}")


def flow_shown_ids(out: str) -> set[int]:
    """The event ids actually listed as sightings."""
    return {int(r.split()[0][1:]) for r in flow_rows(out)}
