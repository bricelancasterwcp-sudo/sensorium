"""The tracer's exception serials, the identity table behind them, and
what `uninstall` does to both.

The other half of `test_tracer`, split at that file's own
`# -- exception serials` banner on 2026-09-08 to bring both halves under the
800-line ceiling. The first file pins the DECISIONS the recorder takes --
which frames it watches, what kind each is, the fingerprints and thread ids
it mints; this one pins the LABELS it puts on exceptions once a decision is
made, and the bounded tables that carry them. Three program sources are the
first file's, imported and never copied.
"""
import sys
import threading
from pathlib import Path

from sensorium.record.fingerprint import Fingerprint
from sensorium.record.tracer import (_CONTROL_RETAIN_MAX, _RETAIN_MAX,
                                     _ExcRefs, FocusSpec, Tracer)
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import installed_tracer, load_module, record_inproc
from tests.test_tracer import ADD, SEQ_THREADS, UNCAUGHT_THROUGH_FINALLY


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


def test_the_control_flow_table_is_small_and_shares_the_serial_counter():
    """Control-flow throws are serialled apart from real exceptions -- and
    from the SAME counter.

    Two tables counting independently would eventually hand a GeneratorExit
    and a real exception the same number on one thread, and a serial is what
    `frame_state` and `exceptions` compare. The side table is also small on
    purpose: its serials never leave the frame they were minted for.
    """
    real = _ExcRefs()
    control = _ExcRefs(cap=_CONTROL_RETAIN_MAX, source=real)
    seen = []
    for i in range(_CONTROL_RETAIN_MAX * 2):
        seen.append(control.identify(GeneratorExit()))
        seen.append(real.identify(ValueError(f"real {i}")))
    assert len(set(seen)) == len(seen), "one thread issued a serial twice"
    assert len(control.serials) <= _CONTROL_RETAIN_MAX
    assert _CONTROL_RETAIN_MAX < _RETAIN_MAX


def test_dropped_generators_do_not_evict_a_retained_exception(tmp_path):
    """The recorder-side half of the P10 shape: throwing control flow into
    traced frames far past the small table's bound leaves the real table's
    contents untouched."""
    src = """
def gen():
    yield 1
    yield 2

def main():
    for _ in range(%d):
        for v in gen():
            break
""" % (_CONTROL_RETAIN_MAX * 4)
    tmp_path.mkdir(parents=True, exist_ok=True)
    prog = tmp_path / "prog.py"
    prog.write_text(src)
    mod = load_module(prog)              # imported BEFORE install, as always
    with installed_tracer(tmp_path) as tracer:
        kept = ValueError("kept")
        serial = tracer._tls.exc.identify(kept)
        mod.main()
        assert len(tracer._tls.cf_exc.serials) <= _CONTROL_RETAIN_MAX
        assert tracer._tls.exc.serial_of(kept) == serial


CONTROL_AND_REAL_EXCEPTIONS = """
def gen():
    yield 1
    yield 2

def main():
    for i in range(3):
        for v in gen():
            break                  # drops the generator: GeneratorExit in
        try:
            raise ValueError(f"real {i}")
        except ValueError:
            pass
"""


def test_control_flow_serials_never_collide_with_real_ones(tmp_path):
    """The two tables of one thread mint from ONE counter, so no serial is
    ever issued twice there. A serial is what `frame_state` and `exceptions`
    compare; two counters running independently would eventually let a
    GeneratorExit's number match a real exception's and make a frame's unwind
    look like rows that belong to another object entirely."""
    t, err = record_inproc(tmp_path, CONTROL_AND_REAL_EXCEPTIONS)
    assert err is None
    real = {e.payload["exc"]["serial"]
            for e in t.events(kind=("RAISE", "HANDLED"))}
    control = {e.payload["thrown"]["serial"] for e in t.events(kind="RESUME")
               if (e.payload or {}).get("thrown")}
    assert len(real) == 3 and len(control) == 3      # both shapes really ran
    assert not real & control


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


def test_sequential_threads_do_not_merge_under_a_recycled_id(tmp_path):
    """Four workers that each finish before the next starts reuse ONE OS thread
    id, but they are four distinct threads and must record four distinct
    fingerprints -- not one merged under the recycled id. Recorded thread
    identity is a per-thread serial the recorder mints, never
    `threading.get_ident()`, whose reuse would silently undercount the threads a
    run had (and mislead `diff`/`refocus`, which compare a fingerprint multiset)."""
    t, err = record_inproc(tmp_path, SEQ_THREADS)
    assert err is None
    tids = {e.thread_id for e in t.events()}
    assert len(tids) == 5                       # main + 4 workers, each distinct
    assert len(t.fingerprints()) == 5
    # small minted serials, not the large recycled OS ids get_ident() returns
    # (they need not be contiguous: a thread may touch the recorder without
    # recording, consuming a serial)
    assert max(tids) < 1000
