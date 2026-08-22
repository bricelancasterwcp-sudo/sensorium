"""Per-task causal fingerprints (spec D6): one per minted task serial over
its CALL/RETURN/RAISE/HANDLED; the thread's fingerprint keeps only the
events that ran in no task; YIELD/RESUME never count (honesty rule 3)."""
import re

from sensorium.record.fingerprint import Fingerprint
from sensorium.store.reader import Trace
from tests.helpers import record_inproc, record_script
from tests.test_async import TWO_TASKS

CAUSAL = ("CALL", "RETURN", "RAISE", "HANDLED")

RAISES_IN_TASK = """
import asyncio

def boom():
    raise ValueError("x")

async def worker():
    try:
        boom()
    except ValueError:
        pass
    await asyncio.sleep(0)

async def amain():
    await asyncio.create_task(worker(), name="w")

def main():
    asyncio.run(amain())
"""

UNNAMED_AND_NAMED = """
import asyncio

def step():
    return 1

async def worker():
    step()
    await asyncio.sleep(0)

async def amain():
    class Mute(asyncio.Task):
        def get_name(self):
            raise RuntimeError("no name for you")
    loop = asyncio.get_running_loop()
    a = Mute(worker(), loop=loop)
    b = asyncio.create_task(worker(), name="named")
    await asyncio.gather(a, b)

def main():
    asyncio.run(amain())
"""

TASK_ON_A_WORKER_THREAD = """
import asyncio, threading

def step():
    return 1

async def worker():
    step()
    await asyncio.sleep(0)

def run_loop():
    asyncio.run(worker())

def main():
    t = threading.Thread(target=run_loop)
    t.start(); t.join()
    step()
"""


ALL_WORK_INSIDE_A_TASK = """
import asyncio, threading

def step(n):
    return n

async def worker():
    step(1)
    await asyncio.sleep(0)
    return step(2)

def main():
    # The thread's ENTRY is stdlib (`asyncio.run`), so every traced thing
    # this thread does happens inside the wrapper task -- it never runs a
    # causal event with task_id NULL.
    t = threading.Thread(target=asyncio.run, args=(worker(),))
    t.start(); t.join()
"""

NEVER_FINISHES = """
import asyncio

def step(name, n):
    return f"{name}:{n}"

async def worker(name):
    step(name, 1)
    await asyncio.Event().wait()      # never set: this task never finishes
    return step(name, 2)

async def amain():
    a = asyncio.create_task(worker("A"), name="task-A")
    b = asyncio.create_task(worker("B"), name="task-B")
    await asyncio.sleep(0)
    return "early"

def main():
    asyncio.run(amain())
"""


def _causal(trace, pred):
    return [e for e in trace.events() if e.kind in CAUSAL and pred(e)]


def test_each_task_gets_its_own_row_and_the_thread_keeps_only_the_rest(
        tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    fps = t.task_fingerprints()
    # asyncio.run's own wrapper task (running amain) is a task like any
    # other: it has a row too. Its name is the default asyncio mints from a
    # PROCESS-GLOBAL counter, so the number depends on whatever ran earlier
    # in this interpreter -- the shape is the claim, not "Task-1".
    names = {name for name, _h, _n in fps.values()}
    assert len(fps) == 3
    assert {"task-A", "task-B"} < names
    wrapper, = names - {"task-A", "task-B"}
    assert re.fullmatch(r"Task-\d+", wrapper)
    for tid, (name, h, n) in fps.items():
        assert n == len(_causal(t, lambda e: e.task_id == tid))
    # Same code, same sequence -> same hash under two names.
    ha, hb = [h for name, h, _n in fps.values() if name in ("task-A", "task-B")]
    assert ha == hb
    # The thread row counts exactly the events that ran in no task.
    (tid, (th, tn)), = t.fingerprints().items()
    assert tn == len(_causal(t, lambda e: e.task_id is None))
    assert tn < len(_causal(t, lambda e: True))


def test_task_fingerprint_counts_raise_and_handled_but_never_yield_resume(
        tmp_path):
    t, err = record_inproc(tmp_path, RAISES_IN_TASK)
    assert err is None
    # Selected by name: `asyncio.run`'s wrapper task has a row of its own,
    # so this trace holds two, and the one under test is the named worker.
    tid, (name, h, n) = next((k, v) for k, v in t.task_fingerprints().items()
                             if v[0] == "w")
    kinds = [e.kind for e in t.events() if e.task_id == tid]
    assert "YIELD" in kinds and "RESUME" in kinds
    assert n == sum(k in CAUSAL for k in kinds)
    assert n >= 4      # CALL worker, CALL boom, RAISE, HANDLED, RETURN ...


def test_an_unnamed_task_gets_a_row_with_a_null_name(tmp_path):
    t, err = record_inproc(tmp_path, UNNAMED_AND_NAMED)
    assert err is None
    names = sorted((name or "") for name, _h, _n in t.task_fingerprints().values())
    assert len(names) == 3
    assert names[0] == "" and names[2] == "named"    # "" = the unnamed one
    assert re.fullmatch(r"Task-\d+", names[1])       # the wrapper; see above
    assert t.task_shapes().total() == 3


def test_a_task_on_a_worker_thread_is_fingerprinted_by_serial_not_thread(
        tmp_path):
    t, err = record_inproc(tmp_path, TASK_ON_A_WORKER_THREAD)
    assert err is None
    (tid, (name, h, n)), = t.task_fingerprints().items()
    assert n == len(_causal(t, lambda e: e.task_id == tid))
    # Two thread rows (main + the loop thread); the loop thread's row holds
    # only what ran there outside the task: run_loop's CALL/RETURN etc.
    fps = t.fingerprints()
    assert len(fps) == 2
    for thread, (_h, count) in fps.items():
        assert count == len(_causal(
            t, lambda e, th=thread: e.thread_id == th and e.task_id is None))


def test_rows_are_written_even_when_the_task_never_finished(tmp_path):
    """A task that never ran to completion is still a recorded stream.

    `amain` returns while both workers are parked on an Event that is never
    set, so `asyncio.run` cancels them on the way out: neither worker ever
    reaches its `return`. The rows must be written anyway -- what a task DID
    is evidence whether or not it got to finish."""
    t, err = record_inproc(tmp_path, NEVER_FINISHES)
    assert err is None
    # The premise, pinned: the workers really did not finish.
    worker = next(c for c in t.codes() if c.qualname == "worker")
    frames = t.frames(code_id=worker.id)
    assert len(frames) == 2
    assert [e for e in t.events(kind="RETURN") if e.code_id == worker.id] == []
    for f in frames:
        assert f.return_event_id is None and f.closed_by == "unwind"
        assert t.frame_state(f).state == "cancelled"
    # ...and each still has its own fingerprint row, wrapper task included.
    assert len(t.task_fingerprints()) == 3
    for tid, (_name, _h, n) in t.task_fingerprints().items():
        assert n == len(_causal(t, lambda e: e.task_id == tid))


def test_a_recorded_run_declares_the_per_task_basis_and_narrows_the_stream(
        tmp_path):
    """Through the real CLI, because `boot` is what writes the marker
    (`record_inproc` installs a Tracer directly and writes no run meta).
    The marker is not decoration: `causal_stream()` reads it to decide what
    a thread's stream covers, so a trace recorded by THIS recorder -- whose
    thread fingerprint excludes task events -- must say "per-task" or every
    reader will compare a narrowed row against a whole-thread stream."""
    src = TWO_TASKS + '\nif __name__ == "__main__":\n    main()\n'
    run_id, path, r = record_script(tmp_path, src)
    assert run_id, r.stderr
    assert r.returncode == 0, r.stderr
    t = Trace.open(path)
    assert t.fingerprint_basis == "per-task"
    stream = t.causal_stream()
    ids = {eid for _f, _q, _k, eid in stream}
    assert ids and all(t.event(eid).task_id is None for eid in ids)
    # ...and the narrowing is real: the thread ran task events too.
    assert len(ids) < len(_causal(t, lambda e: True))
    # The stream is exactly what the thread's fingerprint counted.
    (_tid, (_h, n)), = t.fingerprints().items()
    assert n == len(ids)


def test_a_thread_whose_every_event_ran_in_a_task_still_gets_its_own_row(
        tmp_path):
    """Ruling 5. A thread row is created by running a causal event, not by
    running one OUTSIDE a task -- otherwise a loop thread entered through
    stdlib (`Thread(target=asyncio.run, ...)`) produces no row at all, and
    every reader that counts rows to count threads mis-reports it. `refocus`
    would say "1 further thread(s) ran no traced code, left no fingerprint"
    about a thread that ran six traced causal events, which is false."""
    t, err = record_inproc(tmp_path, ALL_WORK_INSIDE_A_TASK)
    assert err is None
    loop_tid, = {e.thread_id for e in t.events() if e.task_id is not None}
    fps = t.fingerprints()
    assert len(fps) == 2                       # the main thread AND this one
    assert loop_tid in fps
    # Zero, and the empty digest: this thread ran traced code, all of it
    # inside asyncio tasks. That is a different fact from "ran nothing".
    assert fps[loop_tid] == (Fingerprint().hexdigest(), 0)
    # The six events are not lost -- they are on the task's row.
    (_name, _h, n), = t.task_fingerprints().values()
    assert n == 6 == len(_causal(t, lambda e: e.thread_id == loop_tid))
