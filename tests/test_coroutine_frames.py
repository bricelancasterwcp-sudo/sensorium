"""Arc 2: generators and coroutines have frames. Recorded in-process."""
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
