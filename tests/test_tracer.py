from tests.helpers import record_inproc

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
