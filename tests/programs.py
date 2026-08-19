"""Recorded program shapes, plus the fixtures that record them.

Shared by `test_exceptions.py` and `test_grep.py`. Each source string is
one program *shape* -- the unit the exception classifier is tested in,
because the head of a trace is byte-identical for behaviours that mean
opposite things and only whole-program shapes separate them.
"""
from sensorium import paths
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

# Generators are frameless by design (no frame is opened), so RAISE and
# HANDLED both carry frame_id NULL and there is no closed_by to read.
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

CLEAN = """
def add(a, b):
    return a + b

def main():
    print(add(1, 2))

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


def exc_payload(type_, msg, oid):
    return {"type": type_, "msg": msg, "oid": oid}


