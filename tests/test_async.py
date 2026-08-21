"""Derived parentage and task identity, recorded in-process.

Every program here is shaped so that v1's `tls.stack[-1]` guess gives a
DIFFERENT answer from the caller frame -- coroutines resumed by the loop,
a generator calling a helper, a key function called back from C. The
assertions are on what the trace says the parent IS, not on the rendering.
"""
from tests.helpers import record_inproc, record_script

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


def test_events_inside_tasks_carry_distinct_minted_serials(tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    tasks = {k.id: k for k in t.tasks()}
    names = sorted(k.name for k in tasks.values())
    # amain's task + the two named ones. asyncio mints default names from a
    # PROCESS-global counter, so the number in "Task-N" depends on how many
    # unnamed tasks this pytest session already made -- pinned by shape.
    assert len(names) == 3 and names[1:] == ["task-A", "task-B"]
    assert names[0].startswith("Task-")
    step = _by_qual(t, "step")
    by_task = {}
    for f in t.frames(code_id=step.id):
        call = t.event(f.call_event_id)
        by_task.setdefault(tasks[call.task_id].name, []).append(
            call.payload["args"]["task"]["v"])
    assert by_task == {"task-A": ["A", "A", "A"], "task-B": ["B", "B", "B"]}
    # main() itself ran before asyncio.run started a loop.
    main_call = t.event(t.frames(code_id=_by_qual(t, "main").id)[0].call_event_id)
    assert main_call.task_id is None
    # RETURN events are stamped too, not only CALLs.
    rets = [e for e in t.events(kind="RETURN") if e.code_id == step.id]
    assert all(e.task_id is not None for e in rets)


def test_serials_are_minted_not_names_so_duplicate_names_do_not_merge(tmp_path):
    src = TWO_TASKS.replace('name="task-B"', 'name="task-A"')
    t, err = record_inproc(tmp_path, src)
    assert err is None
    same = [k for k in t.tasks() if k.name == "task-A"]
    assert len(same) == 2 and same[0].id != same[1].id


SYNC_NO_ASYNCIO = """
import sys

def leaf():
    return 1

def main():
    leaf()
    return "asyncio" in sys.modules

if __name__ == "__main__":
    print("asyncio imported:", main())
"""


def test_recorder_does_not_import_asyncio_into_a_sync_program(tmp_path):
    """Spec D2: the recorder binds asyncio from sys.modules only once the
    PROGRAM has imported it. Checked in a subprocess so the test process's
    own imports cannot leak in."""
    run_id, trace, r = record_script(tmp_path, SYNC_NO_ASYNCIO)
    assert run_id, r.stderr
    assert "asyncio imported: False" in r.stdout


HOSTILE_TASK = """
import asyncio

class Evil(asyncio.Task):
    def get_name(self):
        raise RuntimeError("no name for you")

def leaf():
    return 1

async def inner():
    return leaf()

async def amain():
    loop = asyncio.get_running_loop()
    return await Evil(inner(), loop=loop)

def main():
    return asyncio.run(amain())
"""


def test_a_task_whose_get_name_raises_is_recorded_unnamed_not_crashed(tmp_path):
    t, err = record_inproc(tmp_path, HOSTILE_TASK)
    assert err is None                                   # the program finished
    leaf = _by_qual(t, "leaf")
    call = t.event(t.frames(code_id=leaf.id)[0].call_event_id)
    assert call.task_id is not None
    assert t.task(call.task_id).name is None             # unreadable -> None
