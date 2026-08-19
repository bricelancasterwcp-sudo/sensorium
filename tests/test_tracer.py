import sys
import threading
from pathlib import Path

from sensorium.record.fingerprint import Fingerprint
from sensorium.record.tracer import _RETAIN_MAX, _ExcRefs, FocusSpec, Tracer
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import installed_tracer, record_inproc

ADD = """
def add(a, b):
    return a + b

def main():
    return add(2, 3)
"""

SWALLOW = """
def parse(s):
    return int(s)

def main():
    try:
        parse("x7")
    except ValueError:
        pass
"""

BOOM = """
def boom():
    raise RuntimeError("dead")

def main():
    boom()
"""

STDLIB = """
import json

def main():
    return json.dumps({"a": 1})
"""

GEN = """
def gen():
    yield 1
    yield 2

def main():
    return list(gen())
"""

# A traced function called from a finally block while an exception is still
# propagating. CPython fires EXCEPTION_HANDLED on entry to the finally even
# though there is no except, so "HANDLED means caught" is not enough on its own.
CLEANUP_UNWIND = """
def leaf():
    raise RuntimeError("dead")

def cleanup():
    return 1

def mid():
    try:
        leaf()
    finally:
        cleanup()

def main():
    try:
        mid()
    except RuntimeError:
        pass
"""

# Caught by a handler in traced code, then the same object raised again.
RERAISE_TRACED = """
def raise_it(e):
    raise e

def main():
    e = ValueError("same")
    try:
        try:
            raise_it(e)
        except ValueError:
            raise e
    except ValueError:
        pass
"""

# Caught by a handler in UNTRACED code (compiled with a non-path filename, so
# the tracer classifies it as foreign), then the same object raised again.
RERAISE_UNTRACED = """
NS = {}
exec(compile('''
def catch(fn, e):
    try:
        fn(e)
    except ValueError:
        pass
''', "<untraced-handler>", "exec"), NS)

def raise_it(e):
    raise e

def main():
    e = ValueError("same")
    NS["catch"](raise_it, e)
    try:
        raise_it(e)
    except ValueError:
        pass
"""

# The common real shape: the exception originates in library code, which runs
# RAISE -> EXCEPTION_HANDLED -> RERAISE internally before it ever reaches user
# code. The first traced frame it surfaces in is the origin worth recording.
UNTRACED_ORIGIN = """
import json

def parse(s):
    return json.loads(s)

def main():
    try:
        parse("{bad}")
    except ValueError:
        pass
"""

# A bare `raise` inside a handler: CPython emits RERAISE, not RAISE, so this
# continues the original propagation rather than starting a new origin.
BARE_RERAISE = """
def leaf():
    raise ValueError("v")

def middle():
    try:
        leaf()
    except ValueError:
        raise

def main():
    try:
        middle()
    except ValueError:
        pass
"""

# Never caught, but passes through a finally on the way out.
UNCAUGHT_THROUGH_FINALLY = """
def leaf():
    raise RuntimeError("dead")

def cleanup():
    return 1

def mid():
    try:
        leaf()
    finally:
        cleanup()

def main():
    mid()
"""

THREADED = """
import threading

def work(n):
    return n * 2

def worker():
    for i in range(5):
        work(i)

def main():
    ts = [threading.Thread(target=worker) for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
"""


def test_calls_returns_args_and_frames(tmp_path):
    t, err = record_inproc(tmp_path, ADD)
    assert err is None
    kinds = [e.kind for e in t.events()]
    assert kinds.count("CALL") == 2 and kinds.count("RETURN") == 2
    add_call = next(e for e in t.events(kind="CALL")
                    if t.code(e.code_id).qualname == "add")
    assert add_call.payload["args"]["a"] == {"k": "num", "v": 2}
    assert add_call.frame_id is None                 # CALL: frame links back
    f = t.frame_containing(add_call.id)
    assert f is not None and f.depth == 1 and f.closed_by == "return"
    ret = t.event(f.return_event_id)
    assert ret.payload["value"] == {"k": "num", "v": 5}


def test_raise_and_handled_share_oid(tmp_path):
    t, err = record_inproc(tmp_path, SWALLOW)
    assert err is None
    raises = t.events(kind="RAISE")
    handles = t.events(kind="HANDLED")
    assert len(raises) == 1 and len(handles) == 1
    assert raises[0].payload["exc"]["type"] == "ValueError"
    assert raises[0].payload["exc"]["oid"] == handles[0].payload["exc"]["oid"]


def test_exc_events_carry_traced_program_line_numbers(tmp_path):
    # Regression: the exception callbacks must report the line in the *traced*
    # program, not a line inside the tracer's own callback plumbing.
    t, err = record_inproc(tmp_path, SWALLOW)
    n_lines = len(SWALLOW.splitlines())
    raise_ev = t.events(kind="RAISE")[0]
    assert raise_ev.line == 3                    # "    return int(s)"
    for e in t.events():
        assert e.line is None or 1 <= e.line <= n_lines


def test_uncaught_closes_frames_by_unwind(tmp_path):
    t, err = record_inproc(tmp_path, BOOM)
    assert type(err).__name__ == "RuntimeError"
    boom_code = next(c for c in t.codes() if c.qualname == "boom")
    f = t.frames(code_id=boom_code.id)[0]
    assert f.closed_by == "unwind"
    assert f.unwind_exc["type"] == "RuntimeError"


def test_stdlib_not_traced(tmp_path):
    t, err = record_inproc(tmp_path, STDLIB)
    files = {t.code(e.code_id).file for e in t.events() if e.code_id}
    assert all(str(tmp_path) in f for f in files)


def test_generators_recorded_frameless(tmp_path):
    t, err = record_inproc(tmp_path, GEN)
    assert err is None
    gen_calls = [e for e in t.events(kind="CALL")
                 if t.code(e.code_id).qualname == "gen"]
    assert len(gen_calls) == 1
    gen_code = next(c for c in t.codes() if c.qualname == "gen")
    assert t.frames(code_id=gen_code.id) == []


def test_cleanup_during_unwind_records_one_origin_raise(tmp_path):
    # Traced code running in a finally block must not disarm the RAISE
    # de-dupe: the exception is still in flight, so there is exactly one
    # origin. Two RAISE rows here would read to `sensorium exceptions` as
    # "handled, then raised again later".
    t, err = record_inproc(tmp_path, CLEANUP_UNWIND)
    assert err is None
    called = {t.code(e.code_id).qualname for e in t.events(kind="CALL")}
    assert "cleanup" in called          # traced code really ran mid-propagation
    raises = t.events(kind="RAISE")
    assert len(raises) == 1
    assert t.code(raises[0].code_id).qualname == "leaf"


def test_reraise_after_traced_handler_records_two_origins(tmp_path):
    t, err = record_inproc(tmp_path, RERAISE_TRACED)
    assert err is None
    raises = t.events(kind="RAISE")
    assert len(raises) == 2
    oids = {r.payload["exc"]["oid"] for r in raises}
    assert len(oids) == 1               # genuinely the same exception object


def test_reraise_after_untraced_handler_records_two_origins(tmp_path):
    # Mirror case: the handler frame is foreign code, so the tracer only ever
    # sees HANDLED for a code object it does not record. It must still notice
    # that the exception stopped propagating.
    t, err = record_inproc(tmp_path, RERAISE_UNTRACED)
    assert err is None
    raises = t.events(kind="RAISE")
    assert len(raises) == 2
    assert {t.code(r.code_id).qualname for r in raises} == {"raise_it"}
    oids = {r.payload["exc"]["oid"] for r in raises}
    assert len(oids) == 1


def test_untraced_origin_records_raise_at_first_traced_frame(tmp_path):
    # Regression: library code runs its own RAISE/HANDLED/RERAISE cycle before
    # the exception reaches user code. That must not leave the exception
    # already "in flight" and swallow the RAISE row, or every library-raised
    # exception lands a HANDLED with no matching RAISE.
    t, err = record_inproc(tmp_path, UNTRACED_ORIGIN)
    assert err is None
    raises = t.events(kind="RAISE")
    assert len(raises) == 1
    assert t.code(raises[0].code_id).qualname == "parse"   # first traced frame
    handles = t.events(kind="HANDLED")
    assert len(handles) == 1
    assert raises[0].payload["exc"]["oid"] == handles[0].payload["exc"]["oid"]


def test_bare_reraise_in_handler_stays_one_origin(tmp_path):
    # A bare `raise` re-raises the same object as part of the same propagation
    # (CPython emits RERAISE for it, and v1 has no RERAISE event kind), so it
    # is not a second origin. Task 11's classifier depends on this.
    t, err = record_inproc(tmp_path, BARE_RERAISE)
    assert err is None
    raises = t.events(kind="RAISE")
    assert len(raises) == 1
    assert t.code(raises[0].code_id).qualname == "leaf"
    handles = t.events(kind="HANDLED")
    assert [t.code(h.code_id).qualname for h in handles] == [
        "middle", "middle", "main"]
    oid = raises[0].payload["exc"]["oid"]
    assert all(h.payload["exc"]["oid"] == oid for h in handles)


def test_uncaught_through_finally_records_one_origin_and_unwinds(tmp_path):
    # Nothing catches this, yet HANDLED rows still appear: CPython compiles
    # `finally` as an implicit handler. A HANDLED row therefore does NOT imply
    # the exception was caught -- the frame's closed_by does.
    t, err = record_inproc(tmp_path, UNCAUGHT_THROUGH_FINALLY)
    assert type(err).__name__ == "RuntimeError"
    raises = t.events(kind="RAISE")
    assert len(raises) == 1
    assert t.code(raises[0].code_id).qualname == "leaf"
    handles = t.events(kind="HANDLED")
    assert [t.code(h.code_id).qualname for h in handles] == ["mid", "mid"]
    # every frame the exception crossed is closed by unwind, including the one
    # that ran the finally; cleanup() itself returned normally
    closed = {t.code(f.code_id).qualname: f.closed_by for f in t.frames()}
    assert closed == {"leaf": "unwind", "mid": "unwind", "main": "unwind",
                      "cleanup": "return"}


def test_threads_recorded_with_distinct_ids_and_fingerprints(tmp_path):
    t, err = record_inproc(tmp_path, THREADED)
    assert err is None
    work_code = next(c for c in t.codes() if c.qualname == "work")
    work_events = t.events(code_id=work_code.id)
    worker_tids = {e.thread_id for e in work_events}
    assert len(worker_tids) == 3                   # all three threads recorded
    assert t.main_thread_id() not in worker_tids
    assert len(work_events) == 3 * 5 * 2           # CALL+RETURN per call

    fps = t.fingerprints()
    assert len(fps) == 4                           # 3 workers + main thread
    worker_fps = [fps[tid] for tid in worker_tids]
    # each worker ran an identical sequence: CALL worker, 5x(CALL/RETURN work),
    # RETURN worker -> same count and same causal hash, proving the per-thread
    # fingerprint state really is isolated and not shared.
    assert [n for _, n in worker_fps] == [12, 12, 12]
    assert len({h for h, _ in worker_fps}) == 1

    # per-thread frame stacks: every thread roots its own tree at depth 0
    for tid in worker_tids:
        depths = sorted({f.depth for f in t.frames() if f.thread_id == tid})
        assert depths == [0, 1]
    assert [f.id for f in t.frames() if f.closed_by is None] == []


def test_fingerprint_deterministic_across_runs(tmp_path):
    t1, _ = record_inproc(tmp_path / "a", ADD)
    t2, _ = record_inproc(tmp_path / "b", ADD)
    h1 = next(iter(t1.fingerprints().values()))
    h2 = next(iter(t2.fingerprints().values()))
    assert h1[0] != "" and h1 == h2


# -- exception serials (Task 11, fix round 3) ------------------------------
# `oid` (`id(exc)`) is not an identity: CPython recycles addresses, measurably
# so in a plain retry loop. Every RAISE/HANDLED payload therefore carries a
# `serial`, minted by the exception state machine while it holds a strong
# reference to the object. These tests pin the machine's labelling; the
# decisions it takes are pinned by the tests above, which are untouched.

SERIAL_LOOP = """
def main():
    for i in range(3):
        try:
            raise ValueError("fail")
        except ValueError as e:
            pass
"""

SERIAL_RERAISE = """
def main():
    try:
        try:
            raise ValueError("boom")
        except ValueError as e:
            raise e
    except ValueError:
        pass
"""


def _exc_serials(trace, kind="RAISE"):
    return [e.payload["exc"].get("serial") for e in trace.events(kind=kind)]


def test_distinct_exceptions_get_distinct_serials(tmp_path):
    """Three separate ValueError('fail') objects, identical in type, message
    and (absent the recorder's own retention) address."""
    trace, err = record_inproc(tmp_path, SERIAL_LOOP)
    serials = _exc_serials(trace)
    assert len(serials) == 3
    assert None not in serials
    assert len(set(serials)) == 3


def test_reraised_exception_keeps_its_serial(tmp_path):
    """`raise e` re-raises the same object, so it keeps its identity."""
    trace, err = record_inproc(tmp_path, SERIAL_RERAISE)
    serials = _exc_serials(trace)
    assert len(serials) == 2
    assert serials[0] == serials[1]
    # and the HANDLED rows agree with the RAISE rows
    assert set(_exc_serials(trace, "HANDLED")) == {serials[0]}


def test_serials_increase_and_never_repeat_within_a_thread(tmp_path):
    trace, err = record_inproc(tmp_path, SERIAL_LOOP)
    serials = _exc_serials(trace)
    assert serials == sorted(serials)
    assert all(isinstance(s, int) and s > 0 for s in serials)


def test_serial_never_reaches_the_fingerprint(tmp_path):
    """Fingerprints hash only (file, qualname, kind). If a serial ever leaked
    into one, two runs of the same program would stop matching and every
    refocus verdict would be worthless."""
    t1, _ = record_inproc(tmp_path / "a", SERIAL_LOOP)
    t2, _ = record_inproc(tmp_path / "b", SERIAL_LOOP)
    h1 = next(iter(t1.fingerprints().values()))
    h2 = next(iter(t2.fingerprints().values()))
    assert h1[0] != "" and h1 == h2
    assert _exc_serials(t1)                      # serials really were recorded


def test_unwound_frames_and_uncaught_carry_the_serial(tmp_path):
    trace, err = record_inproc(tmp_path, UNCAUGHT_THROUGH_FINALLY)
    raised = _exc_serials(trace)
    assert raised and None not in raised
    unwound = [f.unwind_exc.get("serial") for f in trace.frames()
               if f.unwind_exc]
    assert unwound and set(unwound) == {raised[0]}


# -- the identity table (Task 11, fix round 4) -----------------------------
# Round 3 kept identity in slots: one "current serial" and one last-handled
# exception. Slots cannot hold "several exceptions are alive and any of them
# may come back", so an unrelated exception in between evicted a stored one
# (two serials for one object) and an exception raised inside cleanup stamped
# its serial on the exception still in flight (one serial for two objects).
# Identity now lives in a per-thread, bounded table keyed by the object.

SERIAL_STASH_NOISE = """
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
    try:
        raise saved
    except ValueError:
        pass
"""

SERIAL_CLEANUP_RAISES = """
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
"""


def test_a_stored_exception_keeps_its_serial_across_another_exception(tmp_path):
    trace, err = record_inproc(tmp_path, SERIAL_STASH_NOISE)
    assert err is None
    by_type: dict = {}
    for e in trace.events(kind="RAISE"):
        by_type.setdefault(e.payload["exc"]["type"], []).append(
            e.payload["exc"]["serial"])
    assert len(by_type["ValueError"]) == 2
    assert len(set(by_type["ValueError"])) == 1     # one object, one serial
    assert not set(by_type["ValueError"]) & set(by_type["RuntimeError"])


def test_a_raise_during_cleanup_does_not_steal_the_in_flight_serial(tmp_path):
    trace, err = record_inproc(tmp_path, SERIAL_CLEANUP_RAISES)
    assert err is None
    seen: dict = {}
    for e in trace.events(kind="RAISE") + trace.events(kind="HANDLED"):
        seen.setdefault(e.payload["exc"]["type"], set()).add(
            e.payload["exc"]["serial"])
    # the interloper really did run while the outer exception was in flight
    assert set(seen) == {"ValueError", "KeyError"}
    assert len(seen["ValueError"]) == 1
    assert len(seen["KeyError"]) == 1
    assert not seen["ValueError"] & seen["KeyError"]
    # and the frame the outer exception left names that same identity
    unwound = [f.unwind_exc for f in trace.frames() if f.unwind_exc]
    assert unwound and all(u["serial"] in seen["ValueError"] for u in unwound)


def test_retention_is_bounded(tmp_path):
    """Every retained exception pins its traceback, frames and locals, so the
    table has to be bounded even though bounding it is what costs the recorder
    the link to an old stash."""
    with installed_tracer(tmp_path) as tracer:
        for i in range(_RETAIN_MAX * 2):
            try:
                raise ValueError(f"churn {i}")
            except ValueError:
                pass
        refs = tracer._tls.exc
        held, minted = len(refs.serials), refs.minted
    assert minted >= _RETAIN_MAX * 2, "the bound was never approached"
    assert held <= _RETAIN_MAX


def test_retention_never_forgets_the_exception_in_flight():
    """The bound drops the oldest entry -- except the exception this thread is
    propagating, which is the one whose identity a verdict is most likely to
    turn on. (An exception paused inside a `finally` is not that: its
    EXCEPTION_HANDLED already cleared `last_exc`, which is why the query side
    still has to hedge a link it cannot make.)"""
    refs = _ExcRefs()
    in_flight = ValueError("in flight")
    refs.last_exc = in_flight
    serial = refs.identify(in_flight)
    for i in range(_RETAIN_MAX * 2):
        refs.identify(ValueError(f"other {i}"))
    assert len(refs.serials) <= _RETAIN_MAX
    assert refs.serial_of(in_flight) == serial


def test_uninstall_drops_retained_exceptions_on_every_live_thread(tmp_path):
    """`uninstall` must release what it holds on threads that are still
    running, not only on the thread that calls it: a worker parked after a
    handler would otherwise keep its last exception -- and that exception's
    frames and locals -- alive for the rest of the process."""
    box, caught, release = [], threading.Event(), threading.Event()

    def worker():
        try:
            raise ValueError("stashed by a live thread")
        except ValueError as e:
            box.append(e)
        caught.set()
        release.wait(10)

    t = threading.Thread(target=worker)
    try:
        with installed_tracer(tmp_path) as tracer:
            t.start()
            assert caught.wait(10)
            exc = box[0]
            other = [r for r in tracer._live_exc_refs()
                     if any(held[0] is exc for held in r.serials.values())]
            assert other, "the worker's exception was never retained"
            assert other[0] is not tracer._tls.exc, "needs a non-main thread"
            before = sys.getrefcount(exc)
        # uninstall has now run, from the main thread
        assert sys.getrefcount(exc) == before - 1
        assert all(not r.serials for r in tracer._live_exc_refs())
    finally:
        release.set()
        t.join(10)


def test_uninstall_disables_events_before_it_clears_any_table(
        tmp_path, monkeypatch):
    """Ordering, not tidiness. Clearing another thread's retention table
    while that thread's callbacks are still live races the eviction loop's
    unguarded `next(iter(...))`: a worker between the `len()` check and the
    `next()` raises StopIteration from inside a monitoring callback, which
    kills the traced thread. The recorder killing what it observes is the
    same class of failure as an unguarded `__repr__`."""
    from sensorium.record import tracer as tr

    events_when_cleared = []
    real = tr.Tracer._live_exc_refs

    def spy(self):
        events_when_cleared.append(sys.monitoring.get_events(tr.TOOL))
        return real(self)

    monkeypatch.setattr(tr.Tracer, "_live_exc_refs", spy)
    with installed_tracer(tmp_path):
        assert sys.monitoring.get_events(tr.TOOL) != 0   # precondition
    assert events_when_cleared == [0]


def test_the_recorders_own_code_is_never_traced(tmp_path, monkeypatch):
    """The one guard the ordinary tests cannot reach.

    `_SENSORIUM_DIR` only bites when the recorder's own source sits UNDER the
    run's root -- which happens for real (`sensorium run -- pytest` inside
    this repo) and never in a test, because every test records a program in a
    temporary directory the installed package is nowhere near. Pointing the
    constant at the recorded program's own directory is the smallest way to
    put the two in the relationship the guard exists for: if it stops
    excluding, the recorder records itself and the trace fills with frames
    the program never had.
    """
    from sensorium.record import tracer

    monkeypatch.setattr(tracer, "_SENSORIUM_DIR", str(tmp_path))
    t, err = record_inproc(tmp_path, ADD)

    assert err is None
    assert t.events() == []          # every frame was the recorder's, by fiat


def test_uninstall_survives_a_fingerprint_inserted_while_it_writes(tmp_path):
    """A callback still in flight when events are turned off can insert a NEW
    per-thread fingerprint as `uninstall` writes the fingerprints out. Iterating
    the live `_fps` dict would raise `RuntimeError: dictionary changed size
    during iteration` from inside `uninstall`, which runs in `run_target`'s
    `finally` BEFORE the db is closed -- so the raise would leak the connection,
    leave the trace `incomplete`, and never restore the interpreter's streams.
    `uninstall` must read a snapshot under `_fp_lock`, as every other access to
    `_fps` already does."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    writer = TraceWriter(tmp_path / "trace.db", batch=8)
    tracer = Tracer(writer, root=tmp_path, focus=FocusSpec([]))
    tracer.install()

    def fp():
        f = Fingerprint()
        f.update("a.py", "worker", "CALL")
        return f

    tracer._fps[1001] = fp()          # as if two threads had each run one call
    tracer._fps[1002] = fp()

    # the first fingerprint write inserts a third entry, exactly as a still-live
    # worker's first traced call would while uninstall is mid-loop
    inserted = []
    real = writer.write_fingerprint

    def racing(tid, h, n):
        if not inserted:
            inserted.append(tid)
            tracer._fps[1003] = fp()
        return real(tid, h, n)

    writer.write_fingerprint = racing

    tracer.uninstall()                # must not raise
    writer.close()

    written = set(Trace.open(tmp_path / "trace.db").fingerprints())
    assert {1001, 1002} <= written    # the threads present at the snapshot land
