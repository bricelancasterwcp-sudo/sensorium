"""Derived parentage and task identity, recorded in-process.

Every program here is shaped so that v1's `tls.stack[-1]` guess gives a
DIFFERENT answer from the caller frame -- coroutines resumed by the loop,
a generator calling a helper, a key function called back from C. The
assertions are on what the trace says the parent IS, not on the rendering.
"""
from tests.helpers import record_inproc

TWO_TASKS = """
import asyncio

def step(task, n):
    return f"{task}:{n}"

async def worker(name):
    step(name, 1)
    await asyncio.sleep(0)
    step(name, 2)
    return step(name, 3)

async def amain():
    a = asyncio.create_task(worker("A"), name="task-A")
    b = asyncio.create_task(worker("B"), name="task-B")
    return await asyncio.gather(a, b)

def main():
    return asyncio.run(amain())
"""

GEN_HELPER = """
def parse(s):
    return int(s)

def rows(items):
    for it in items:
        yield parse(it)

def rank(s):
    return len(s)

def main():
    list(rows(["1", "22"]))
    sorted(["bb", "a"], key=rank)
"""


def _by_qual(t, qual):
    return next(c for c in t.codes() if c.qualname == qual)


def test_sync_helper_inside_a_coroutine_is_not_parented_to_the_module(tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    step = _by_qual(t, "step")
    worker = _by_qual(t, "worker")
    frames = t.frames(code_id=step.id)
    assert len(frames) == 6
    # v1 parented every one of these to main's frame. The caller is worker,
    # which is frameless, so the honest parent is NULL and the caller is NAMED.
    assert all(f.parent_id is None for f in frames)
    assert all(f.depth == 0 for f in frames)
    for f in frames:
        call = t.event(f.call_event_id)
        assert call.payload["caller_code"] == worker.id
        assert "caller" not in call.payload


def test_coroutine_calls_are_recorded_unframed_with_their_kind(tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    worker = _by_qual(t, "worker")
    calls = t.unframed_calls(code_id=worker.id)
    assert len(calls) == 2
    assert {c.payload["unframed"] for c in calls} == {"coroutine"}
    # Entered by the event loop, which is untraced: say so, invent nothing.
    assert all(c.payload.get("caller") == "untraced" for c in calls)
    assert all("parent_frame" not in c.payload for c in calls)


def test_generator_helper_names_the_generator_and_key_fn_finds_main(tmp_path):
    """Parentage is about the caller frame, not about asyncio: a generator
    body calling `parse` is unframed-but-traced (caller_code), and a key
    function called back from C-level sorted() has `main` as its real caller
    -- which is also what v1 said, by the accident of stack discipline."""
    t, err = record_inproc(tmp_path, GEN_HELPER)
    assert err is None
    rows_c, parse_c, rank_c, main_c = (_by_qual(t, q) for q in
                                        ("rows", "parse", "rank", "main"))
    main_frame, = t.frames(code_id=main_c.id)
    for f in t.frames(code_id=parse_c.id):
        assert f.parent_id is None
        assert t.event(f.call_event_id).payload["caller_code"] == rows_c.id
    for f in t.frames(code_id=rank_c.id):
        assert f.parent_id == main_frame.id
        assert f.depth == main_frame.depth + 1
    gen_call, = t.unframed_calls(code_id=rows_c.id)
    assert gen_call.payload["unframed"] == "generator"
    assert gen_call.payload["parent_frame"] == main_frame.id


def test_parent_of_rejects_a_live_entry_whose_code_is_not_the_callers(tmp_path):
    """The `code is` check is the guard arc 2 will lean on when suspendable
    frames enter `live` and an address CAN be recycled under a stale entry.
    Pinned now, in isolation, so it cannot be 'simplified' away."""
    from types import SimpleNamespace
    from sensorium.record.tracer import Tracer
    tls = SimpleNamespace(live={})
    caller = SimpleNamespace(f_code=object())
    tls.live[id(caller)] = [7, object(), 1, {}, 0]          # same id, other code
    assert Tracer._parent_of(None, tls, caller) is None
    tls.live[id(caller)] = [7, caller.f_code, 1, {}, 0]
    assert Tracer._parent_of(None, tls, caller)[0] == 7
    assert Tracer._parent_of(None, tls, None) is None
