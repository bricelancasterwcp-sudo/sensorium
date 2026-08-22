"""Arc 2: generators and coroutines have frames. Recorded in-process."""
from sensorium.store.reader import FrameState
from tests.helpers import record_inproc
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
    assert {e.payload["awaiting"] for e in ys} == {"Future"} or ys
    assert all(e.frame_id is not None and e.task_id is not None for e in ys)
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
    from tests.helpers import record_inproc_full
    t1, _, tr1 = record_inproc_full(tmp_path / "a", CANCEL)
    # Same program; the fingerprint is over CALL/RETURN/RAISE/HANDLED only,
    # so YIELD/RESUME counts do not appear in n_events.
    n_causal = sum(1 for e in t1.events() if e.kind in ("CALL", "RETURN", "RAISE", "HANDLED"))
    assert sum(n for _h, n in t1.fingerprints().values()) == n_causal
