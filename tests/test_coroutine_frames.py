"""Arc 2: generators and coroutines have frames. Recorded in-process."""
from sensorium.store.reader import FrameState
from tests.helpers import record_inproc, record_script, run_cli
from tests.test_async import TWO_TASKS, GEN_HELPER, _by_qual


def test_coroutines_get_frames_and_their_sync_callees_become_children(tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    worker, step = _by_qual(t, "worker"), _by_qual(t, "step")
    wf = t.frames(code_id=worker.id)
    assert [f.kind for f in wf] == ["coroutine", "coroutine"]
    assert t.unframed_calls() == []
    for f in t.frames(code_id=step.id):
        assert f.parent_id in {w.id for w in wf}
        assert f.depth == 1
        assert "caller_code" not in (t.event(f.call_event_id).payload or {})


def test_generators_get_frames_and_parse_is_their_child(tmp_path):
    t, err = record_inproc(tmp_path, GEN_HELPER)
    assert err is None
    rows_c, parse_c, main_c = (_by_qual(t, q) for q in ("rows", "parse", "main"))
    rows_f, = t.frames(code_id=rows_c.id)
    main_f, = t.frames(code_id=main_c.id)
    assert rows_f.kind == "generator" and rows_f.parent_id == main_f.id
    assert all(f.parent_id == rows_f.id for f in t.frames(code_id=parse_c.id))


RAISE_IN_CORO = """
import asyncio

async def worker():
    try:
        raise ValueError("inside")
    except ValueError:
        return 1

def main():
    return asyncio.run(worker())
"""


def test_raise_and_handled_inside_a_coroutine_carry_its_frame(tmp_path):
    t, err = record_inproc(tmp_path, RAISE_IN_CORO)
    assert err is None
    wf, = t.frames(code_id=_by_qual(t, "worker").id)
    kinds = {(e.kind, e.frame_id) for e in t.events(kind=("RAISE", "HANDLED"))}
    assert kinds == {("RAISE", wf.id), ("HANDLED", wf.id)}
    assert wf.closed_by == "return"


def test_focus_on_a_coroutine_records_its_lines(tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS, focus=["prog:worker"])
    assert err is None
    wf = {f.id for f in t.frames(code_id=_by_qual(t, "worker").id)}
    lines = [e for e in t.events(kind="LINE")]
    assert lines and {e.frame_id for e in lines} <= wf


EARLY_BREAK = """
def gen():
    yield 1
    yield 2

def main():
    for x in gen():
        break
    return x
"""


def test_generator_closed_early_unwinds_with_generator_exit(tmp_path):
    t, err = record_inproc(tmp_path, EARLY_BREAK)
    assert err is None
    g, = t.frames(code_id=_by_qual(t, "gen").id)
    assert g.kind == "generator" and g.closed_by == "unwind"
    assert g.unwind_exc["type"] == "GeneratorExit"
    # Control-flow exceptions are never RAISE rows; the unwind is the only record.
    assert t.events(kind="RAISE") == []


ASYNC_GEN = """
import asyncio

async def agen():
    yield 1
    yield 2

async def amain():
    out = []
    async for v in agen():
        out.append(v)
    return out

def main():
    return asyncio.run(amain())
"""


def test_async_generators_get_frames_of_kind_async_generator(tmp_path):
    t, err = record_inproc(tmp_path, ASYNC_GEN)
    assert err is None
    a, = t.frames(code_id=_by_qual(t, "agen").id)
    assert a.kind == "async_generator"
    assert a.closed_by == "return"


SUSPEND_LOCALS = """
import asyncio

async def worker():
    before = 1
    await asyncio.sleep(0)
    after = before + 1
    return after

def main():
    return asyncio.run(worker())
"""


def test_line_deltas_survive_a_suspension(tmp_path):
    t, err = record_inproc(tmp_path, SUSPEND_LOCALS, focus=["prog:worker"])
    assert err is None
    deltas = [e.payload.get("deltas", {}) for e in t.events(kind="LINE")]
    assert any(d.get("before", {}).get("v") == 1 for d in deltas)
    # `after` is bound on the line following the await: its delta must be
    # recorded against the PRE-suspension locals (prev_locals survived in
    # tls.live), i.e. `before` is NOT re-reported as a delta there.
    post = [d for d in deltas if "after" in d]
    assert post and post[0]["after"]["v"] == 2 and "before" not in post[0]


CANCEL = """
import asyncio
GATE = None

def step(n):
    return n

async def worker():
    step(1)
    await GATE.wait()
    return step(2)

async def amain():
    global GATE
    GATE = asyncio.Event()
    a = asyncio.create_task(worker(), name="task-A")
    b = asyncio.create_task(worker(), name="task-B")
    await asyncio.sleep(0)
    b.cancel()
    GATE.set()
    await a
    try:
        await b
    except asyncio.CancelledError:
        pass

def main():
    asyncio.run(amain())
"""


def test_suspension_is_recorded_and_a_cancelled_task_is_derived_as_cancelled(tmp_path):
    t, err = record_inproc(tmp_path, CANCEL)
    assert err is None
    states = {}
    for f in t.frames(code_id=_by_qual(t, "worker").id):
        s = t.frame_state(f)
        states[t.task(t.event(f.call_event_id).task_id).name] = s
    assert states["task-A"].state == "returned"
    b = states["task-B"]
    assert b.state == "cancelled" and b.exc["type"] == "CancelledError"
    assert b.line == 10                                 # `await GATE.wait()`
    ys = t.events(kind="YIELD")
    assert ys and all(e.frame_id is not None and e.task_id is not None
                      for e in ys)
    rs = t.events(kind="RESUME")
    thrown = [e for e in rs if (e.payload or {}).get("thrown")]
    assert len(thrown) == 1 and thrown[0].payload["thrown"]["type"] == "CancelledError"


def test_awaiting_is_the_bare_type_name_not_a_repr(tmp_path):
    """`awaiting` names the TYPE being awaited, never `repr(value)`.

    A repr is the program's own `__repr__` output -- unbounded, run from a
    hook, and different on every run (`<Future pending cb=[...] at 0x...>`),
    which would make the column useless for grouping and for diffing runs.
    """
    t, err = record_inproc(tmp_path, CANCEL)
    assert err is None
    ys = t.events(kind="YIELD")
    assert ys
    wf = {f.id for f in t.frames(code_id=_by_qual(t, "worker").id)}
    assert {e.payload["awaiting"] for e in ys if e.frame_id in wf} == {"Future"}
    # Every one of them, worker or not: a bare type name, never a repr.
    for e in ys:
        a = e.payload["awaiting"]
        assert a.isidentifier(), a


ABANDON = """
KEEP = []

def gen():
    x = 1
    yield x
    yield 2

def main():
    g = gen()
    next(g)
    del g            # dropped while suspended -> GeneratorExit thrown in
    h = gen()
    next(h)
    KEEP.append(h)   # still suspended when recording stops
"""


def test_dropped_generator_is_abandoned_and_a_parked_one_is_suspended_at_end(tmp_path):
    t, err = record_inproc(tmp_path, ABANDON)
    assert err is None
    f1, f2 = t.frames(code_id=_by_qual(t, "gen").id)
    s1, s2 = t.frame_state(f1), t.frame_state(f2)
    assert s1.state == "abandoned" and s1.exc["type"] == "GeneratorExit" and s1.line == 6
    assert s2 == FrameState("suspended", 6, None)
    assert f2.closed_by is None


def test_a_generator_left_by_a_break_derives_as_abandoned(tmp_path):
    """The `for/break` case of the same fact: the loop drops the generator,
    CPython closes it, and the frame is abandoned AT THE YIELD it was parked
    on -- keyed on the thrown GeneratorExit's serial, not on "unwound with
    no RAISE row" (a control-flow exception never gets a RAISE)."""
    t, err = record_inproc(tmp_path, EARLY_BREAK)
    assert err is None
    g, = t.frames(code_id=_by_qual(t, "gen").id)
    s = t.frame_state(g)
    assert s.state == "abandoned" and s.exc["type"] == "GeneratorExit"
    assert s.line == 3                                  # `yield 1`


def test_yield_and_resume_never_touch_the_fingerprint(tmp_path):
    t, err = record_inproc(tmp_path, CANCEL)
    assert err is None
    # The fingerprint is over CALL/RETURN/RAISE/HANDLED only, so YIELD and
    # RESUME counts must not appear in n_events. Since plan 2b every causal
    # event belongs to exactly ONE row -- its task's if it ran in a task,
    # else its thread's -- so the two tables TOGETHER are what must total
    # the causal count; the thread's row alone covers only what ran outside
    # any task (which for this program is nearly nothing).
    n_causal = sum(1 for e in t.events()
                   if e.kind in ("CALL", "RETURN", "RAISE", "HANDLED"))
    assert t.events(kind=("YIELD", "RESUME"))        # there ARE such rows
    n_thread = sum(n for _h, n in t.fingerprints().values())
    n_task = sum(n for _name, _h, n in t.task_fingerprints().values())
    assert n_thread + n_task == n_causal
    assert n_task                                    # tasks did the work...
    assert n_thread < n_causal                       # ...so the thread's is a part


LOUD_THROW = """
def leaf():
    return "boom"

class Loud(Exception):
    def __str__(self):
        return leaf()

def gen():
    yield 1
    yield 2

def main():
    g = gen()
    next(g)
    try:
        g.throw(Loud())
    except Loud:
        pass
"""


def test_building_a_thrown_payload_never_records_the_programs_own_code(tmp_path):
    """`capture_exc` calls the exception's `__str__`, which is the observed
    program: `Loud.__str__` calls `leaf()`. The message proves `leaf` ran, and
    the trace must hold no sign of it -- a phantom CALL/RETURN pair the
    program never made, a live entry, a fingerprint update from hook time.

    Measured on CPython 3.14.4: the interpreter delivers NO monitoring event
    to a tool while that tool's own callback is running, so this holds even
    when the payload is built before `in_hook` is set (that mutation
    survives -- recorded, not hidden). The assertion guards the ordering
    rather than proving it load-bearing today: the recorder must not rest on
    an interpreter behaviour nothing pins, and building the payload inside
    the region also stops `__str__` running at all when no row is written.
    """
    t, err = record_inproc(tmp_path, LOUD_THROW)
    assert err is None
    # `leaf` ran (the message proves it) but was never RECORDED -- not even
    # interned, since interning happens only on the path that writes a row.
    assert "leaf" not in {c.qualname for c in t.codes()}
    assert t.events(code_id=None, kind="CALL")       # other calls were recorded
    r, = [e for e in t.events(kind="RESUME") if (e.payload or {}).get("thrown")]
    assert r.payload["thrown"]["type"] == "Loud"
    assert r.payload["thrown"]["msg"] == "boom"
    # And the serial minted for the throw is still the one the unwind carries.
    g, = t.frames(code_id=_by_qual(t, "gen").id)
    assert t.frame_state(g) == FrameState("thrown", 10, g.unwind_exc)  # `yield 1`


# A generator first stepped on one thread and finished on another. This is
# the Starlette `iterate_in_threadpool` / FastAPI `StreamingResponse(sync_gen)`
# shape: the first `next()` happens where the object was made, the rest are
# submitted to a worker pool. The recorder's live map is per-thread, so
# without the parked-frame hand-off every lookup after the first step misses:
# no RESUME rows, a RETURN with frame_id NULL, and a frame that reads
# `~ suspended at end of recording` although it exhausted normally.
CROSS_THREAD_GEN = """
from concurrent.futures import ThreadPoolExecutor


def rows():
    n = 0
    while n < 3:
        yield n
        n += 1
    return "done"


def step(g):
    try:
        return next(g)
    except StopIteration as e:
        return e.value


def main():
    g = rows()
    out = [step(g)]                    # first step, on the main thread
    with ThreadPoolExecutor(max_workers=2) as ex:
        while len(out) < 4:            # the rest, on worker threads
            out.append(ex.submit(step, g).result())
    return out


if __name__ == "__main__":
    main()
"""


def test_a_generator_finished_on_another_thread_keeps_its_frame(tmp_path):
    """Four steps: one on the main thread, three on pool workers. The frame
    belongs to the generator, not to a thread, so it must close by `return`
    with every suspension recorded -- three YIELDs and three RESUMEs -- and
    the RETURN row must carry the frame."""
    t, err = record_inproc(tmp_path, CROSS_THREAD_GEN)
    assert err is None
    f, = t.frames(code_id=_by_qual(t, "rows").id)
    assert f.kind == "generator" and f.closed_by == "return"
    assert t.frame_state(f) == FrameState("returned", None, None)
    ys = [e for e in t.events(kind="YIELD") if e.frame_id == f.id]
    rs = [e for e in t.events(kind="RESUME") if e.frame_id == f.id]
    assert len(ys) == 3 and len(rs) == 3
    ret, = [e for e in t.events(kind="RETURN")
            if t.code(e.code_id).qualname == "rows"]
    assert ret.frame_id == f.id and ret.payload["value"]["v"] == "done"


def test_cross_thread_resume_rows_carry_the_thread_that_resumed(tmp_path):
    """The frames row keeps the thread that OPENED the frame; the events a
    suspended frame produces after another thread picks it up carry that
    thread. Both are true of the same frame, and neither is guessed."""
    t, err = record_inproc(tmp_path, CROSS_THREAD_GEN)
    assert err is None
    f, = t.frames(code_id=_by_qual(t, "rows").id)
    assert f.thread_id == t.main_thread_id()
    rs = [e for e in t.events(kind="RESUME") if e.frame_id == f.id]
    assert rs and any(e.thread_id != f.thread_id for e in rs)


def test_tree_reports_the_cross_thread_generator_as_returned(tmp_path):
    """The sentence a user reads. Before the hand-off this frame rendered
    `~ suspended at L8 at end of recording` -- a false statement about a
    generator that exhausted and returned -- because its RETURN landed on a
    thread whose live map had never held it."""
    run_id, _trace, r = record_script(tmp_path, CROSS_THREAD_GEN)
    assert run_id, r.stderr
    out = run_cli(["tree", run_id], cwd=tmp_path,
                  sensorium_dir=tmp_path / "sdir").stdout
    rows_line, = [ln for ln in out.splitlines() if "rows()" in ln]
    assert "[generator]" in rows_line and "-> 'done'" in rows_line
    assert "~ suspended" not in out
