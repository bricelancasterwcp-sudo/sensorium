# Sensorium arc 2b — per-task fingerprints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each asyncio task gets its own causal fingerprint; `refocus` and `diff` compare tasks by content (a multiset of `(name, hash)`), so a different interleaving can no longer manufacture a DIVERGED and a task that really took another path is named.

**Architecture:** The recorder keeps one `Fingerprint` per minted task serial beside the per-thread ones and feeds every CALL/RETURN/RAISE/HANDLED to exactly one of them (the task's when the event has a task serial, else the thread's); at `uninstall` it writes `task_fingerprints` rows. A meta marker `fingerprint_basis = "per-task"` says which definition a trace's thread fingerprints follow (spec D3 forbids a format bump; the meaning narrows, so the marker is what makes the narrowing honest). The reader exposes task fingerprints, task streams and the narrowed thread stream; `diff`/`refocus` add a task comparison beside the thread comparison and REFUSE to compare traces recorded under different bases when tasks are involved.

**Tech Stack:** Python ≥ 3.12 stdlib only (`sys.monitoring`, `sqlite3`, `hashlib.blake2b`); pytest; the corpus harness `corpus/run_corpus.py`.

**Spec:** `docs/superpowers/specs/2026-08-21-sensorium-arc2-inspectable-coroutines-design.md` — §D6 (plan 2b), §D3 (no second format bump), honesty rule 3 (YIELD/RESUME never enter a fingerprint), §"Constraints carried from arc 1" 2–4. Plan 2a shipped on `feat/async-arc2` (PR #3, HEAD `e679b7c`); this plan builds on top of it on branch `feat/async-arc2b`.

## Global Constraints

- Python floor `>=3.12`; every task's tests green on 3.12 / 3.13 / 3.14 (matrix run once, in Task 6, as in plans 1–2a); stdlib-only runtime; the recorder never imports asyncio.
- **No format bump** (spec D3: "`task_fingerprints` … created by the format-3 schema now so 2b is not a second format bump. `fingerprints` (per thread) is unchanged in shape; its *meaning* narrows in 2b"). `TRACE_FORMAT` stays 3. The narrowing is marked by meta `fingerprint_basis`: `"per-task"` written by this recorder; absent (read as `"per-thread"`) on every earlier trace.
- Spec D6, verbatim requirements: each task serial owns a `Fingerprint` over its `CALL/RETURN/RAISE/HANDLED` events (never YIELD/RESUME/LINE); the thread fingerprint covers only events with `task_id IS NULL`; at `uninstall`, `task_fingerprints` rows `(task_id, name, hash, n_events)` are written beside the per-thread rows; `refocus`/`diff` compare thread streams as today plus tasks as a **multiset of `(name, hash)`** — order-independent; DIVERGED names the task stream(s) with no counterpart and, for the first such pair sharing a name, the first differing `(file, qualname, kind)` with a drill-in command on each side; REFUSED when there is nothing to compare; the licence adds `N task stream(s) compared by content; the ordering between tasks is not compared`; `diff` gains `--task NAME`; unnamed tasks (`name IS NULL`) match only unnamed tasks.
- Honesty: the instrument never answers from data it does not have. A trace recorded under the per-thread basis is never read as if its thread fingerprints excluded task events; comparing a per-thread-basis trace with a per-task-basis trace is REFUSED whenever either side recorded a task (their thread streams are defined differently); when neither side has tasks the two definitions coincide and the comparison proceeds.
- Fixture discipline (arc 1/2a): a REAL 0.3.0 recording (`e679b7c`, format 3, per-thread basis, with tasks) is committed in Task 0, recorded under `env -i PATH=/usr/bin:/bin LANG=C.UTF-8 SENSORIUM_DIR=…` so `meta.env` holds only those three keys; fixture tests pin that this reader keeps 0.3.0's wording and claims nothing new about it.
- Tests first; every new behaviour test mutation-checked (`__pycache__` purged, `PYTHONDONTWRITEBYTECODE=1`, file-copy restore — never `git checkout --` while uncommitted work exists); corpus questions registered (YAML written) before their program is run, then bite-checked; output pristine.
- Version `0.4.0`; push/PR deferred to the finishing skill.

## File Structure

- `tests/fixtures/format3_async.py` / `.db` (create, Task 0) — the real 0.3.0 recording; `tests/test_format3_fixture.py` (create) — `old3` pins.
- `src/sensorium/store/reader.py` (modify, Task 1) — `Trace.fingerprint_basis`, `Trace.task_fingerprints()`, `Trace.task_shapes()`, `Trace.task_stream(task_id)`, `causal_stream` narrowed by basis.
- `src/sensorium/store/writer.py` (modify, Task 1) — `TraceWriter.write_task_fingerprint(task_id, hexdigest, count)`.
- `src/sensorium/record/boot.py` (modify, Task 1) — writes meta `fingerprint_basis: "per-task"`.
- `src/sensorium/record/tracer.py` (modify, Task 2) — `_task_fps`, `_fp_for(tid, task)`, the three update sites, `uninstall` writes task rows.
- `src/sensorium/query/diff_cmd.py` (modify, Task 3) — `compare_tasks`, `compare()` gains `tasks`, cross-basis refusal, `--task NAME`, printing.
- `src/sensorium/query/refocus_cmd.py` (modify, Task 4) — `_task_divergence`, `final_verdict`, `tasks:` line, licence fact, blind-spot wording, cross-basis refusal.
- `src/sensorium/query/info_cmd.py` (modify, Task 5) — basis + task-fingerprint lines.
- `corpus/async_refocus/` (create, Task 5) — the interleaving / content / `--task` case; `tests/test_corpus.py` count floor.
- `corpus/_bench/bench.py` (run, Task 6); `README.md`, `pyproject.toml`, spec addendum (Task 6).
- Tests: `tests/test_task_fingerprints.py` (create, Task 2), `tests/test_reader_tasks.py` (create, Task 1), additions to `tests/test_diff.py`, `tests/test_refocus.py`, `tests/refocus_programs.py`, `tests/test_runs_info.py`, `tests/test_format3_fixture.py`.

---

### Task 0: A real 0.3.0 (format 3, per-thread basis) fixture

**Files:**
- Create: `tests/fixtures/format3_async.py`, `tests/fixtures/format3_async.db`, `tests/test_format3_fixture.py`

**Interfaces:**
- Produces: fixture `installed_fixture3` → run id `"old3"` (pattern of `tests/test_format2_fixture.py::_installed`); later tasks add pins to `tests/test_format3_fixture.py`.

- [ ] **Step 1: Write the program**

`tests/fixtures/format3_async.py`:
```python
"""Recorded by sensorium 0.3.0 (trace_format 3) -- BEFORE per-task
fingerprints existed. Its per-thread fingerprint covers every causal event
on the thread, task events included, and its `task_fingerprints` table is
empty. Tests pin that a newer reader says exactly that and claims nothing
more. Do not edit: the .db beside this file is the recording of THIS text.
"""
import asyncio


def step(task, n):
    return f"{task}:{n}"


async def worker(name):
    step(name, 1)
    await asyncio.sleep(0)
    return step(name, 2)


async def amain():
    a = asyncio.create_task(worker("A"), name="task-A")
    b = asyncio.create_task(worker("B"), name="task-B")
    return await asyncio.gather(a, b)


def main():
    print(asyncio.run(amain()))


main()
```

- [ ] **Step 2: Record it with 0.3.0 in a throwaway worktree, scrubbed environment**

```bash
T=/home/brice/.claude/jobs/95b9693a/tmp
git worktree add $T/sensorium-v030 e679b7c
cp tests/fixtures/format3_async.py $T/sensorium-v030/
cd $T/sensorium-v030 && uv venv .venv -p 3.14 -q && uv pip install -q -p .venv/bin/python -e .
env -i PATH=/usr/bin:/bin LANG=C.UTF-8 SENSORIUM_DIR=$T/fixture3-store .venv/bin/sensorium run -- format3_async.py
cp $T/fixture3-store/traces/*.db /home/brice/workspace/sensorium/tests/fixtures/format3_async.db
cd /home/brice/workspace/sensorium && git worktree remove $T/sensorium-v030 --force && rm -rf $T/fixture3-store
git worktree list   # only the main checkout
```

- [ ] **Step 3: Write the pins**

`tests/test_format3_fixture.py`:
```python
"""A trace recorded by sensorium 0.3.0 (format 3, per-thread fingerprint
basis), read by this one. Plan 2b narrows what a thread fingerprint means
and fills `task_fingerprints`; neither may be claimed retroactively."""
import json
import sqlite3
from pathlib import Path

import pytest

from sensorium.store.reader import Trace
from tests.test_format2_fixture import _installed

FIXTURE = Path(__file__).parent / "fixtures" / "format3_async.db"


@pytest.fixture
def installed_fixture3(tmp_path, monkeypatch):
    return _installed(tmp_path, monkeypatch, FIXTURE, "old3")


def test_fixture_is_format_3_with_tasks_and_no_task_fingerprints():
    c = sqlite3.connect(FIXTURE)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    assert fmt == 3
    assert c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 2
    assert c.execute("SELECT COUNT(*) FROM task_fingerprints").fetchone()[0] == 0
    assert c.execute(
        "SELECT 1 FROM meta WHERE key='fingerprint_basis'").fetchone() is None


def test_fixture_carries_no_ambient_environment():
    env = Trace.open(FIXTURE).meta["env"]
    assert sorted(env) == ["LANG", "PATH", "SENSORIUM_DIR"]


def test_fixture_thread_fingerprint_counts_task_events_too():
    """0.3.0's thread fingerprint covered every causal event on the thread,
    the task events included -- the count says so."""
    t = Trace.open(FIXTURE)
    (tid, (h, n)), = t.fingerprints().items()
    causal = [e for e in t.events()
              if e.kind in ("CALL", "RETURN", "RAISE", "HANDLED")]
    assert n == len(causal)
    assert any(e.task_id is not None for e in causal)
```

- [ ] **Step 4: Run, expect PASS (these pin the recording, not new code)**

Run: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_format3_fixture.py -q`
Expected: 3 passed. (If `Event` has no `task_id` attribute, read it from `e.task_id` per `reader.Event` — it does: arc 1 added it.)

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/format3_async.py tests/fixtures/format3_async.db tests/test_format3_fixture.py
git commit -m "test: capture a real 0.3.0 (format-3, per-thread basis) asyncio trace as a fixture"
```

---

### Task 1: Reader, writer and meta — the task-fingerprint surface and the basis marker

**Files:**
- Modify: `src/sensorium/store/reader.py` (`Trace.__init__`, after `fingerprints()` ~line 218, `causal_stream` ~line 258)
- Modify: `src/sensorium/store/writer.py` (after `write_fingerprint` ~line 101)
- Modify: `src/sensorium/record/boot.py` (~line 539, beside `caps`)
- Create: `tests/test_reader_tasks.py`
- Modify: `tests/test_format3_fixture.py`

**Interfaces:**
- Produces: `Trace.fingerprint_basis -> str` (`"per-task"` | `"per-thread"`); `Trace.task_fingerprints() -> dict[int, tuple[str | None, str, int]]` (task_id → (name, hash, n_events)); `Trace.task_shapes() -> Counter[tuple[str | None, str]]`; `Trace.task_stream(task_id) -> list[tuple[str, str, str, int]]` (file, qualname, kind, eid — same tuple as `causal_stream`); `causal_stream(thread_id)` returns only `task_id IS NULL` events when `fingerprint_basis == "per-task"`; `TraceWriter.write_task_fingerprint(task_id, hexdigest, count)`; meta key `fingerprint_basis`.

- [ ] **Step 1: Failing tests**

`tests/test_reader_tasks.py`:
```python
"""The reader's view of task fingerprints and of the fingerprint basis."""
from collections import Counter
from pathlib import Path

from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter

OLD3 = Path(__file__).parent / "fixtures" / "format3_async.db"


def _build(tmp_path, basis):
    """A hand-built trace: main thread runs f, then task 1 (named 'w') runs
    g twice, task 2 (unnamed) runs g once; writer-level, no recorder."""
    w = TraceWriter(tmp_path / "t.db", batch=4)
    if basis is not None:
        w.set_meta("fingerprint_basis", basis)
    f = w.intern_code("/p/prog.py", "f", 1)
    g = w.intern_code("/p/prog.py", "g", 5)
    w.add_task(1, "w", 1)
    w.add_task(2, None, 1)
    w.add_event(0, 1, "CALL", None, f, 1, {"args": {}})
    w.add_event(1, 1, "CALL", None, g, 5, {"args": {}}, task_id=1)
    w.add_event(2, 1, "RETURN", None, g, None, {"value": None}, task_id=1)
    w.add_event(3, 1, "YIELD", None, g, 6, {"awaiting": "Future"}, task_id=1)
    w.add_event(4, 1, "CALL", None, g, 5, {"args": {}}, task_id=2)
    w.add_event(5, 1, "RETURN", None, g, None, {"value": None}, task_id=2)
    w.add_event(6, 1, "RETURN", None, f, None, {"value": None})
    w.write_fingerprint(1, "aa" * 16, 2)
    w.write_task_fingerprint(1, "bb" * 16, 2)
    w.write_task_fingerprint(2, "cc" * 16, 2)
    w.close()
    return Trace.open(tmp_path / "t.db")


def test_basis_defaults_to_per_thread_when_the_marker_is_absent(tmp_path):
    t = _build(tmp_path, None)
    assert t.fingerprint_basis == "per-thread"
    assert Trace.open(OLD3).fingerprint_basis == "per-thread"


def test_basis_reads_the_marker(tmp_path):
    assert _build(tmp_path, "per-task").fingerprint_basis == "per-task"


def test_task_fingerprints_carry_the_name_from_the_tasks_table(tmp_path):
    t = _build(tmp_path, "per-task")
    assert t.task_fingerprints() == {1: ("w", "bb" * 16, 2),
                                     2: (None, "cc" * 16, 2)}
    assert Trace.open(OLD3).task_fingerprints() == {}


def test_task_shapes_is_a_multiset_of_name_and_hash(tmp_path):
    t = _build(tmp_path, "per-task")
    assert t.task_shapes() == Counter({("w", "bb" * 16): 1,
                                       (None, "cc" * 16): 1})


def test_task_stream_is_the_tasks_causal_events_in_order(tmp_path):
    t = _build(tmp_path, "per-task")
    assert [s[:3] for s in t.task_stream(1)] == [
        ("/p/prog.py", "g", "CALL"), ("/p/prog.py", "g", "RETURN")]
    assert [s[3] for s in t.task_stream(1)] == [2, 3]      # event ids
    assert t.task_stream(99) == []


def test_causal_stream_narrows_to_no_task_events_under_the_per_task_basis(
        tmp_path):
    t = _build(tmp_path, "per-task")
    assert [s[:3] for s in t.causal_stream(1)] == [
        ("/p/prog.py", "f", "CALL"), ("/p/prog.py", "f", "RETURN")]


def test_causal_stream_keeps_every_event_under_the_per_thread_basis(tmp_path):
    t = _build(tmp_path, None)
    assert [s[1:3] for s in t.causal_stream(1)] == [
        ("f", "CALL"), ("g", "CALL"), ("g", "RETURN"), ("g", "CALL"),
        ("g", "RETURN"), ("f", "RETURN")]
```

Add to `tests/test_format3_fixture.py`:
```python
def test_old3_thread_stream_still_holds_the_task_events():
    """Under the per-thread basis the thread stream IS every causal event on
    the thread; the narrowing is never applied to a trace that predates it."""
    t = Trace.open(FIXTURE)
    quals = [s[1] for s in t.causal_stream()]
    assert "worker" in quals and "step" in quals
```

- [ ] **Step 2: Run, expect FAIL** — `AttributeError: 'Trace' object has no attribute 'fingerprint_basis'` / `write_task_fingerprint`.

- [ ] **Step 3: Implement**

`src/sensorium/store/writer.py`, after `write_fingerprint`:
```python
    def write_task_fingerprint(self, task_id, hexdigest, count) -> None:
        """One row per minted task serial; the name rides along from the
        `tasks` row so the multiset comparison can read (name, hash) from
        one table. A task whose name could not be read keeps NULL."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO task_fingerprints "
                "(task_id, name, hash, n_events) "
                "SELECT ?, name, ?, ? FROM tasks WHERE id = ?",
                (task_id, hexdigest, count, task_id))
            self._conn.commit()
```

`src/sensorium/store/reader.py` — in `Trace.__init__` after `self._has_tasks = ...`:
```python
        self._has_task_fps = bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='task_fingerprints'").fetchone())
```
after `fingerprints()`:
```python
    @property
    def fingerprint_basis(self) -> str:
        """What a per-thread fingerprint row covers: "per-task" (plan 2b --
        only events outside any asyncio task; tasks have their own rows) or
        "per-thread" (every causal event on the thread; the only definition
        before the marker existed, so absence means exactly that)."""
        return self.meta.get("fingerprint_basis") or "per-thread"

    def task_fingerprints(self) -> dict[int, tuple[str | None, str, int]]:
        if not self._has_task_fps:
            return {}
        return {tid: (name, h, n) for tid, name, h, n in self._c.execute(
            "SELECT task_id, name, hash, n_events FROM task_fingerprints")}

    def task_shapes(self) -> "Counter[tuple[str | None, str]]":
        """The multiset of (name, hash) over every task fingerprint: two
        tasks doing identical work under one name count twice, which is the
        comparison -- the same task shapes ran, the same number of times."""
        return Counter((name, h) for name, h, _n
                       in self.task_fingerprints().values())

    def task_stream(self, task_id: int) -> list[tuple[str, str, str, int]]:
        marks = ",".join("?" * len(CAUSAL_KINDS))
        out = []
        for eid, cid, kind in self._c.execute(
                f"SELECT id, code_id, kind FROM events "
                f"WHERE task_id = ? AND kind IN ({marks}) ORDER BY id",
                (task_id, *CAUSAL_KINDS)):
            c = self.code(cid)
            out.append((c.file, c.qualname, kind, eid))
        return out
```
and `causal_stream`:
```python
    def causal_stream(self, thread_id=None) -> list[tuple[str, str, str, int]]:
        tid = thread_id if thread_id is not None else self.main_thread_id()
        marks = ",".join("?" * len(CAUSAL_KINDS))
        # Under the per-task basis a thread's stream is what its fingerprint
        # covers: the events that ran in no task. Under the per-thread basis
        # (every trace before the marker) it is every causal event, task
        # events included -- the definition those fingerprints were made by.
        narrow = ("AND task_id IS NULL "
                  if self.fingerprint_basis == "per-task" else "")
        out = []
        for eid, cid, kind in self._c.execute(
                f"SELECT id, code_id, kind FROM events "
                f"WHERE thread_id = ? {narrow}AND kind IN ({marks}) ORDER BY id",
                (tid, *CAUSAL_KINDS)):
            c = self.code(cid)
            out.append((c.file, c.qualname, kind, eid))
        return out
```
Add `from collections import Counter` at the top of reader.py.

`src/sensorium/record/boot.py` ~line 539, beside `w.set_meta("caps", capture.CAPS)`:
```python
    # Which definition this recorder's per-thread fingerprints follow (spec
    # D6): events that ran in an asyncio task go to that task's own
    # fingerprint, so the thread's covers only the rest. A trace without
    # this key was recorded before the distinction existed.
    w.set_meta("fingerprint_basis", "per-task")
```

- [ ] **Step 4: Run, expect PASS**

Run: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_reader_tasks.py tests/test_format3_fixture.py -q`
Expected: all pass. Then the full suite: some `refocus`/`diff` tests may still pass (the recorder does not yet write per-task rows, but every freshly recorded trace is now marked `per-task`, so `causal_stream` narrows while the thread fingerprint still covers everything) — that inconsistency is closed by Task 2; if any test turns red here, list it in the report as owned by Task 2 (expected: tests that compare `fingerprints()[tid][1]` to `len(causal_stream())` on an asyncio program, if any).

- [ ] **Step 5: Mutations** — (a) make `fingerprint_basis` return `"per-task"` when the key is absent → `test_basis_defaults…` and `test_causal_stream_keeps_every_event…` fail; (b) drop the `task_id IS NULL` narrowing → `test_causal_stream_narrows…` fails; (c) `write_task_fingerprint` inserts NULL for the name → `test_task_fingerprints_carry_the_name…` fails. Restore by file copy; purge `__pycache__`.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/store/reader.py src/sensorium/store/writer.py src/sensorium/record/boot.py tests/test_reader_tasks.py tests/test_format3_fixture.py
git commit -m "feat(store): task fingerprints, task streams and the fingerprint-basis marker"
```

---

### Task 2: Recorder — one fingerprint per task; the thread fingerprint covers the rest

**Files:**
- Modify: `src/sensorium/record/tracer.py` (`Tracer.__init__` ~434, `_fp` ~507, `_on_start` ~699–716, `_on_return` ~736–745, `_exc_event` ~948–957, `uninstall` ~1120–1124)
- Create: `tests/test_task_fingerprints.py`

**Interfaces:**
- Consumes: `TraceWriter.write_task_fingerprint` (Task 1); `Trace.task_fingerprints()` / `task_shapes()` / `fingerprints()` (Task 1).
- Produces: `task_fingerprints` rows on every recording; thread rows over `task_id IS NULL` events only.

- [ ] **Step 1: Failing tests**

`tests/test_task_fingerprints.py`:
```python
"""Per-task causal fingerprints (spec D6): one per minted task serial over
its CALL/RETURN/RAISE/HANDLED; the thread's fingerprint keeps only the
events that ran in no task; YIELD/RESUME never count (honesty rule 3)."""
from tests.helpers import record_inproc
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


def _causal(trace, pred):
    return [e for e in trace.events() if e.kind in CAUSAL and pred(e)]


def test_each_task_gets_its_own_row_and_the_thread_keeps_only_the_rest(
        tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    fps = t.task_fingerprints()
    assert {name for name, _h, _n in fps.values()} == {"task-A", "task-B"}
    for tid, (name, h, n) in fps.items():
        assert n == len(_causal(t, lambda e: e.task_id == tid))
    # Same code, same sequence -> same hash under two names.
    (ha, hb) = [h for _name, h, _n in fps.values()]
    assert ha == hb
    # The thread row counts exactly the events that ran in no task.
    (tid, (th, tn)), = t.fingerprints().items()
    assert tn == len(_causal(t, lambda e: e.task_id is None))
    assert tn < len(_causal(t, lambda e: True))


def test_task_fingerprint_counts_raise_and_handled_but_never_yield_resume(
        tmp_path):
    t, err = record_inproc(tmp_path, RAISES_IN_TASK)
    assert err is None
    (tid, (name, h, n)), = t.task_fingerprints().items()
    assert name == "w"
    kinds = [e.kind for e in t.events() if e.task_id == tid]
    assert "YIELD" in kinds and "RESUME" in kinds
    assert n == sum(k in CAUSAL for k in kinds)
    assert n >= 4      # CALL worker, CALL boom, RAISE, HANDLED, RETURN ...


def test_an_unnamed_task_gets_a_row_with_a_null_name(tmp_path):
    t, err = record_inproc(tmp_path, UNNAMED_AND_NAMED)
    assert err is None
    names = sorted((name or "") for name, _h, _n in t.task_fingerprints().values())
    assert names == ["", "named"]
    assert t.task_shapes().total() == 2


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
    """A task still parked at uninstall is still a recorded stream."""
    src = TWO_TASKS.replace("return await asyncio.gather(a, b)",
                            "await asyncio.sleep(0)\n    return 'early'")
    t, err = record_inproc(tmp_path, src)
    assert err is None
    assert len(t.task_fingerprints()) == 2
```

- [ ] **Step 2: Run, expect FAIL** — `task_fingerprints()` is `{}`; thread counts equal the full causal count.

- [ ] **Step 3: Implement** in `src/sensorium/record/tracer.py`

In `Tracer.__init__` beside `self._fps`:
```python
        self._fps: dict[int, Fingerprint] = {}
        self._task_fps: dict[int, Fingerprint] = {}   # task serial -> fp
        self._fp_lock = threading.Lock()
```
Replace `_fp` with:
```python
    def _fp(self, tid: int) -> Fingerprint:
        # `tid` is a per-thread SERIAL (see `_TLS.thread_serial`), the same
        # identity events and frames carry, so two short-lived threads that
        # recycle one OS id still key here to distinct fingerprints.
        with self._fp_lock:
            fp = self._fps.get(tid)
            if fp is None:
                fp = self._fps[tid] = Fingerprint()
            return fp

    def _fp_for(self, tid: int, task) -> Fingerprint:
        """The fingerprint this event belongs to: the task's when it ran in
        an asyncio task, else the thread's (spec D6). One event, one
        fingerprint -- the thread's covers exactly the events with
        task_id NULL, which is what makes the two rows comparable
        separately."""
        if task is None:
            return self._fp(tid)
        with self._fp_lock:
            fp = self._task_fps.get(task)
            if fp is None:
                fp = self._task_fps[task] = Fingerprint()
            return fp
```
`_on_start`: `task` is already computed (`task = self._task_serial(tls)`); change the last line of the `try` block:
```python
            self._fp_for(tid, task).update(fp_file, qual, "CALL")
```
`_on_return`: compute the serial once, before `add_event`:
```python
            task = self._task_serial(tls)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "RETURN",
                                        fid, cid, None,
                                        {"value": capture_value(retval)},
                                        task_id=task)
            if fid is not None:
                self.writer.close_frame(fid, eid, "return")
            self._fp_for(tid, task).update(fp_file, qual, "RETURN")
```
`_exc_event`: same shape:
```python
            task = self._task_serial(tls)
            self.writer.add_event(time.monotonic_ns(), tid, kind, fid, cid,
                                  frame.f_lineno,
                                  {"exc": capture_exc(exc, serial)},
                                  task_id=task)
            self._fp_for(tid, task).update(fp_file, qual, kind)
```
`uninstall`, after the per-thread rows:
```python
        with self._fp_lock:
            fps = list(self._fps.items())
            tfps = list(self._task_fps.items())
        for tid, fp in fps:
            self.writer.write_fingerprint(tid, fp.hexdigest(), fp.count)
        for task, fp in tfps:
            self.writer.write_task_fingerprint(task, fp.hexdigest(), fp.count)
```
(`_suspension` must stay untouched: YIELD/RESUME never reach `_fp_for`.)

- [ ] **Step 4: Run, expect PASS** — the new file, then `tests/test_async.py tests/test_refocus.py tests/test_diff.py tests/test_refocus_licence.py tests/test_runs_info.py`, then the full suite. Any test that pinned `fingerprints()[tid][1]` against the whole-thread count of an asyncio program now needs the NULL-task count — update it to the new definition (say which in the report).

- [ ] **Step 5: Mutations** — (a) `_fp_for` ignores `task` → test 1's `tn < len(all)` and the per-task counts fail; (b) `_suspension` calls `_fp_for(...).update(..., "YIELD")` → test 2 fails; (c) `uninstall` skips the task rows → every test fails; (d) `_on_return` passes `None` as task → test 1's per-task `n` fails.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/record/tracer.py tests/test_task_fingerprints.py tests/
git commit -m "feat(record): one causal fingerprint per asyncio task; the thread keeps the rest"
```

---

### Task 3: `diff` — tasks compared by content, `--task NAME`, and the basis guard

**Files:**
- Modify: `src/sensorium/query/diff_cmd.py` (`compare` ~116, `print_comparison` ~250, `add_parser`/`run` ~284–301; new `compare_tasks`, `_basis_reasons`)
- Modify: `tests/test_diff.py`

**Interfaces:**
- Consumes: `Trace.task_shapes()`, `task_fingerprints()`, `task_stream()`, `fingerprint_basis` (Task 1); rows from Task 2.
- Produces: `compare(trace_a, trace_b) -> dict` gains key `"tasks"` = result of `compare_tasks(...)`: `{"verdict": "MATCH" | "DIVERGED" | None, "only_a": [(name, hash, count)], "only_b": [...], "pair": None | {"name", "index", "a_event", "b_event", "a_desc", "b_desc", "a_task", "b_task"}, "n_a": int, "n_b": int}` (`None` verdict = no task on either side); the top-level `verdict` is `DIVERGED` when either the thread stream or the tasks diverge; `_basis_reasons(a, b) -> list[str]` (refusal reasons); `diff --task NAME`.

- [ ] **Step 1: Failing tests** — append to `tests/test_diff.py`:

```python
ASYNC_SHAPE = """
import asyncio, sys

def step(n):
    return n

def other(n):
    return -n

async def worker(name, flip):
    step(1)
    await asyncio.sleep(0)
    if flip and name == "B":
        other(2)
    else:
        step(2)

async def amain(order, flip):
    names = ["A", "B"] if order == "AB" else ["B", "A"]
    tasks = [asyncio.create_task(worker(n, flip), name=f"task-{n}")
             for n in names]
    await asyncio.gather(*tasks)

def main():
    order, flip = sys.argv[1], sys.argv[2] == "flip"
    asyncio.run(amain(order, flip))

main()
"""


def _rec_async(tmp_path, tag, argv):
    d = tmp_path / tag
    d.mkdir()
    (d / "prog.py").write_text(ASYNC_SHAPE)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", "--", "prog.py", *argv], cwd=d, sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def test_diff_matches_two_runs_whose_tasks_interleaved_differently(
        tmp_path, monkeypatch, capsys):
    a = _rec_async(tmp_path, "a", ["AB", "same"])
    b = _rec_async(tmp_path, "b", ["BA", "same"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b]) == 0
    out = capsys.readouterr().out
    assert "verdict: MATCH" in out
    assert "tasks: 2 task stream(s) on each side, compared by content" in out
    assert "all matched" in out
    assert "the ordering between tasks is not compared" in out


def test_diff_names_the_task_that_took_another_path(tmp_path, monkeypatch,
                                                    capsys):
    a = _rec_async(tmp_path, "a", ["AB", "same"])
    b = _rec_async(tmp_path, "b", ["AB", "flip"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b]) == 1
    out = capsys.readouterr().out
    assert "tasks: DIVERGED" in out
    assert "task-B" in out
    assert "only in A:" in out and "only in B:" in out
    assert "first difference inside task-B" in out
    assert "A:      " in out and "step" in out
    assert "B:      " in out and "other" in out
    assert f"drill into A: sensorium tree {a} --around e" in out
    assert f"drill into B: sensorium tree {b} --around e" in out
    # task-A matched and is not listed as differing
    assert "task-A" not in out.split("tasks: DIVERGED", 1)[1].split(
        "first difference", 1)[0]


def test_diff_task_flag_compares_one_named_task(tmp_path, monkeypatch,
                                                capsys):
    a = _rec_async(tmp_path, "a", ["AB", "same"])
    b = _rec_async(tmp_path, "b", ["BA", "flip"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b, "--task", "task-A"]) == 0
    out = capsys.readouterr().out
    assert "compared: task task-A" in out
    assert "verdict: MATCH" in out
    capsys.readouterr()
    assert cli.main(["diff", a, b, "--task", "task-B"]) == 1
    out = capsys.readouterr().out
    assert "verdict: DIVERGED at causal step" in out
    assert "other" in out


def test_diff_task_flag_refuses_an_unknown_or_ambiguous_name(
        tmp_path, monkeypatch, capsys):
    a = _rec_async(tmp_path, "a", ["AB", "same"])
    b = _rec_async(tmp_path, "b", ["AB", "same"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", a, b, "--task", "nope"]) == 2
    out = capsys.readouterr().out
    assert "REFUSED" in out and "no task named 'nope'" in out
    assert "task-A, task-B" in out


def test_diff_unnamed_tasks_match_only_unnamed_tasks(tmp_path, monkeypatch):
    from collections import Counter
    from sensorium.query.diff_cmd import _shape_difference
    a = Counter({(None, "h1"): 1, ("w", "h1"): 1})
    b = Counter({("w", "h1"): 2})
    only_a, only_b = _shape_difference(a, b)
    assert only_a == [(None, "h1", 1)] and only_b == [("w", "h1", 1)]


def test_diff_refuses_to_compare_across_fingerprint_bases_when_tasks_ran(
        tmp_path, monkeypatch, capsys):
    from tests.test_format2_fixture import _installed
    from tests.test_format3_fixture import FIXTURE as OLD3
    old3 = _installed(tmp_path, monkeypatch, OLD3, "old3")
    new = _rec_async(tmp_path, "n", ["AB", "same"])
    assert cli.main(["diff", old3, new]) == 2
    out = capsys.readouterr().out
    assert "verdict: REFUSED" in out
    assert ("recorded under different fingerprint bases "
            "(A: per-thread, B: per-task)") in out
    assert "re-record" in out


def test_diff_compares_across_bases_when_neither_side_ran_a_task(
        tmp_path, monkeypatch, capsys):
    """No task anywhere: both definitions coincide, so nothing is refused."""
    a = _rec(tmp_path, "a", ["100"])
    sdir = tmp_path / "sdir"
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    import sqlite3
    c = sqlite3.connect(sdir / "traces" / f"{a}.db")
    c.execute("DELETE FROM meta WHERE key='fingerprint_basis'")
    c.commit(); c.close()
    b = _rec(tmp_path, "b", ["100"])
    assert cli.main(["diff", a, b]) == 0
    assert "REFUSED" not in capsys.readouterr().out
```
(`_rec` and `BRANCH` already exist at the top of `tests/test_diff.py`; `re`, `run_cli`, `cli` are imported there.)

- [ ] **Step 2: Run, expect FAIL** — `tasks:` lines absent; `--task` unknown argument; `_shape_difference` missing.

- [ ] **Step 3: Implement** in `src/sensorium/query/diff_cmd.py`

New helpers (after `_desc`):
```python
def _shape_difference(a, b):
    """(only_a, only_b): the (name, hash, count) entries one multiset has
    and the other lacks. Unnamed tasks carry name None and therefore only
    ever match unnamed tasks -- a name is content here, not a label."""
    def rows(c):
        return sorted(((n, h, k) for (n, h), k in c.items()),
                      key=lambda r: (r[0] is None, r[0] or "", r[1]))
    return rows(a - b), rows(b - a)


def _basis_reasons(trace_a: Trace, trace_b: Trace) -> list[str]:
    """Two traces recorded under different fingerprint bases define their
    thread streams differently; if either ran a task the comparison would
    put task events on one side only. No task anywhere: the definitions
    coincide and nothing is refused."""
    ba, bb = trace_a.fingerprint_basis, trace_b.fingerprint_basis
    if ba == bb or not (trace_a.tasks() or trace_b.tasks()):
        return []
    return [f"the two traces were recorded under different fingerprint "
            f"bases (A: {ba}, B: {bb}): one thread stream includes the "
            "events that ran inside asyncio tasks and the other does not, "
            "so they are not the same kind of stream. Re-record the older "
            "side with this version to compare them"]


def _first_pair_sharing_a_name(trace_a, trace_b, only_a, only_b):
    """For the first name present on both 'only' lists, the two task
    streams and their first differing step -- None when no name is shared
    (then every unmatched stream is simply listed)."""
    names_b = {n for n, _h, _k in only_b if n is not None}
    for name, ha, _k in only_a:
        if name is None or name not in names_b:
            continue
        hb = next(h for n, h, _c in only_b if n == name)
        ta = next(t for t, (n, h, _c) in trace_a.task_fingerprints().items()
                  if n == name and h == ha)
        tb = next(t for t, (n, h, _c) in trace_b.task_fingerprints().items()
                  if n == name and h == hb)
        sa, sb = trace_a.task_stream(ta), trace_b.task_stream(tb)
        i = first_divergence(sa, sb)
        if i is None:          # same stream, different serial numbering: no
            continue           # real difference to show; keep looking
        a_step = sa[i] if i < len(sa) else None
        b_step = sb[i] if i < len(sb) else None
        return {"name": name, "index": i, "a_task": ta, "b_task": tb,
                "a_event": a_step[3] if a_step else None,
                "b_event": b_step[3] if b_step else None,
                "a_desc": _desc(a_step) if a_step else "(stream ended)",
                "b_desc": _desc(b_step) if b_step else "(stream ended)"}
    return None


def compare_tasks(trace_a: Trace, trace_b: Trace) -> dict:
    """Tasks compared as a multiset of (name, hash): order-independent, so
    a different interleaving cannot manufacture a DIVERGED, and two tasks
    sharing a name are matched by content. verdict None = no task on
    either side (nothing to say)."""
    a, b = trace_a.task_shapes(), trace_b.task_shapes()
    n_a, n_b = a.total(), b.total()
    if not n_a and not n_b:
        return {"verdict": None, "only_a": [], "only_b": [], "pair": None,
                "n_a": 0, "n_b": 0}
    only_a, only_b = _shape_difference(a, b)
    if not only_a and not only_b:
        return {"verdict": "MATCH", "only_a": [], "only_b": [], "pair": None,
                "n_a": n_a, "n_b": n_b}
    return {"verdict": "DIVERGED", "only_a": only_a, "only_b": only_b,
            "pair": _first_pair_sharing_a_name(trace_a, trace_b,
                                               only_a, only_b),
            "n_a": n_a, "n_b": n_b}
```
In `compare()`: add the basis guard to the refusal reasons and the nothing-to-compare rule:
```python
    reasons = (_unsafe_reasons(trace_a, "A") + _unsafe_reasons(trace_b, "B")
               + _basis_reasons(trace_a, trace_b))
    if reasons:
        return _refused(reasons)
    sa = trace_a.causal_stream()
    sb = trace_b.causal_stream()
    tasks = compare_tasks(trace_a, trace_b)
    if not sa and not sb and tasks["verdict"] is None:
        return _refused([... the existing sentence ...])
```
Every returned dict gains `"tasks": tasks`; the MATCH/DIVERGED decision: thread divergence as today; if the thread stream matches but `tasks["verdict"] == "DIVERGED"`, return `verdict: "DIVERGED"` with `index: None` and the `a_event`/… keys `None` (the task section carries the detail). `_refused` also sets `"tasks": None`.

`print_comparison` — after the thread verdict block (MATCH or DIVERGED) print the task section:
```python
def _print_tasks(res, name_a, name_b) -> None:
    t = res.get("tasks")
    if not t or t["verdict"] is None:
        return
    if t["verdict"] == "MATCH":
        print(f"tasks: {t['n_a']} task stream(s) on each side, compared by "
              "content as (name, hash): all matched; the ordering between "
              "tasks is not compared")
        return
    def fmt(rows):
        return ", ".join(f"{n if n is not None else '(unnamed)'} "
                         f"{h[:12]}{'' if k == 1 else f' x{k}'}"
                         for n, h, k in rows) or "-"
    print(f"tasks: DIVERGED -- {t['n_a']} task stream(s) on A, {t['n_b']} "
          f"on B; only in A: {fmt(t['only_a'])}; only in B: "
          f"{fmt(t['only_b'])}; the ordering between tasks is not compared")
    p = t["pair"]
    if p:
        print(f"first difference inside {p['name']} (A task t{p['a_task']}, "
              f"B task t{p['b_task']}) at causal step {p['index']}:")
        print(f"  A:      {p['a_desc']}")
        print(f"  B:      {p['b_desc']}")
        if p["a_event"]:
            print(f"drill into A: sensorium tree {name_a} "
                  f"--around e{p['a_event']}")
        if p["b_event"]:
            print(f"drill into B: sensorium tree {name_b} "
                  f"--around e{p['b_event']}")
```
The thread verdict line when the thread stream matched but tasks diverged: print `verdict: MATCH on the thread stream; DIVERGED on the tasks (below)` — keep `verdict: MATCH -- identical causal streams …` for the all-match case exactly as today, and print `verdict: DIVERGED` only in the thread-diverged case (unchanged text). `run()` exit: 1 when `res["verdict"] == "DIVERGED"` (either source).

`--task NAME`:
```python
    p.add_argument("--task", default=None, metavar="NAME",
                   help="compare one asyncio task's stream by name instead "
                        "of the thread streams")
```
In `run()`: if `args.task`: resolve the task on each side — exactly one task fingerprint row with that name per side, else `REFUSED` exit 2 printing `no task named 'NAME' on A (A has: task-A, task-B)` or `NAME names 2 tasks on A; a name must pick exactly one`. Then compare `ta.task_stream(ia)` vs `tb.task_stream(ib)` with `first_divergence`, print `A {name_a}: compared: task NAME (t{ia})` / same for B, and the same MATCH/DIVERGED/drill-in lines as the thread comparison (reuse `print_comparison`'s step printing by building a `res` dict with `a_stream`/`b_stream`). Implement as `compare_task_streams(trace_a, trace_b, name) -> dict` (same keys as `compare()`, plus `"a_task"`, `"b_task"`, `"reasons"`) and a `print_task_comparison(...)`.

- [ ] **Step 4: Run, expect PASS** (new tests + all of `tests/test_diff.py`).
- [ ] **Step 5: Mutations** — (a) `_shape_difference` treats None as matching any name → unnamed test fails; (b) `compare_tasks` returns MATCH whenever `n_a == n_b` → the flip test fails; (c) drop `_basis_reasons` → the cross-basis test fails; (d) `--task` ignores ambiguity → the refusal test fails.
- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/diff_cmd.py tests/test_diff.py
git commit -m "feat(diff): compare asyncio tasks by content; --task NAME; refuse mixed fingerprint bases"
```

---

### Task 4: `refocus` — the task verdict, the licence line, the blind spot, the basis guard

**Files:**
- Modify: `src/sensorium/query/refocus_cmd.py` (`_BLIND_SPOTS` ~175–200, `_thread_divergence`/`final_verdict` ~423–450, `_verified_facts` ~590, the `threads:` print ~685–700, `_refusal`/run path for the basis guard)
- Modify: `tests/refocus_programs.py`, `tests/test_refocus.py`, `tests/test_refocus_licence.py`, `tests/test_format3_fixture.py`

**Interfaces:**
- Consumes: `compare()`'s `tasks` key (Task 3), `_shape_difference`, `Trace.task_shapes()`.
- Produces: `final_verdict(orig, new, res) -> (verdict, threads, tasks_desc)` — a third element: the task-divergence description or None; printed `tasks:` line; licence fact `N task stream(s) compared by content`.

- [ ] **Step 1: Failing tests**

`tests/refocus_programs.py` — add shapes (the counter file flips the SECOND run, exactly like `COUNTER`):
```python
# Two named tasks whose START ORDER flips between the original and the
# rerun (a counter file decides), while each task does identical work.
# Refocus must say MATCH: tasks are compared by content, never by the order
# they interleaved in.
ASYNC_ORDER_FLIP = """
import asyncio
from pathlib import Path
COUNTER = Path("run_count.txt")

def step(n):
    return n

async def worker(name):
    step(1)
    await asyncio.sleep(0)
    step(2)

async def amain(order):
    names = ["A", "B"] if order else ["B", "A"]
    await asyncio.gather(*[asyncio.create_task(worker(n), name=f"task-{n}")
                           for n in names])

def main():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    asyncio.run(amain(n % 2 == 0))

if __name__ == "__main__":
    main()
"""

# Same, but task-B takes another branch on the rerun: DIVERGED, naming
# task-B and the first differing step.
ASYNC_CONTENT_FLIP = ASYNC_ORDER_FLIP.replace(
    "async def worker(name):\n    step(1)\n    await asyncio.sleep(0)\n    step(2)",
    "def other(n):\n    return -n\n\nasync def worker(name):\n    step(1)\n"
    "    await asyncio.sleep(0)\n    if name == 'B' and not FIRST[0]:\n"
    "        other(2)\n    else:\n        step(2)").replace(
    "COUNTER = Path(\"run_count.txt\")",
    "COUNTER = Path(\"run_count.txt\")\nFIRST = [True]").replace(
    "    asyncio.run(amain(n % 2 == 0))",
    "    FIRST[0] = n % 2 == 0\n    asyncio.run(amain(True))")

# The rerun spawns a third worker: DIVERGED with a stream only on the rerun.
ASYNC_COUNT_FLIP = ASYNC_ORDER_FLIP.replace(
    "    names = [\"A\", \"B\"] if order else [\"B\", \"A\"]",
    "    names = [\"A\", \"B\"] if order else [\"A\", \"B\", \"C\"]")
```
`tests/test_refocus.py`:
```python
def test_refocus_matches_when_only_the_task_interleaving_changed(tmp_path):
    run_id, sdir = rec(tmp_path, ASYNC_ORDER_FLIP)
    r = refocus(sdir, run_id, "--focus", "prog:worker")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert ("tasks: 2 task stream(s) compared by content, all matching; "
            "the ordering between tasks is not compared") in r.stdout
    assert "2 task stream(s) compared by content" in r.stdout   # licence


def test_refocus_diverges_when_one_task_took_another_path(tmp_path):
    run_id, sdir = rec(tmp_path, ASYNC_CONTENT_FLIP)
    r = refocus(sdir, run_id, "--focus", "prog:worker")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "refocus verdict: DIVERGED" in r.stdout
    assert "tasks: DIVERGED" in r.stdout and "task-B" in r.stdout
    assert "first difference inside task-B" in r.stdout
    assert "drill into A: sensorium tree" in r.stdout
    assert "a task took a different path" in r.stdout


def test_refocus_diverges_when_the_rerun_ran_a_task_the_original_did_not(
        tmp_path):
    run_id, sdir = rec(tmp_path, ASYNC_COUNT_FLIP)
    r = refocus(sdir, run_id, "--focus", "prog:worker")
    assert r.returncode == 1
    assert "tasks: DIVERGED" in r.stdout and "only in B: task-C" in r.stdout


def test_refocus_refuses_a_per_thread_basis_original_that_ran_tasks(
        tmp_path, monkeypatch):
    from tests.test_format2_fixture import _installed
    from tests.test_format3_fixture import FIXTURE as OLD3
    import shutil
    sdir = tmp_path / "sdir"
    _installed(tmp_path, monkeypatch, OLD3, "old3")
    # The original's program must resolve for the rerun to be attempted.
    cwd = Trace.open(sdir / "traces" / "old3.db").meta["cwd"]
    ...
```
(The `old3` refusal must happen BEFORE any rerun: put it in `_refusal(meta, trace)`: when `trace.fingerprint_basis == "per-thread"` and `trace.tasks()` is non-empty → reason `"original was recorded under the per-thread fingerprint basis and ran N asyncio task(s); this version compares tasks by content and defines thread streams without them, so no verdict against it would compare like with like -- re-record it with this version"`. Test it with a synthetic trace instead of `old3` (whose cwd no longer exists): build via `synthetic(sdir, run_id, argv=("prog.py",))` plus `w.add_task(1, "t", 1)` and no `fingerprint_basis` meta, write a trivial `prog.py` in `sdir.parent`, and assert `refocus` exits 2 with `REFUSED` and the sentence above; keep a second, read-only pin in `tests/test_format3_fixture.py`: `refocus_cmd._refusal(trace.meta, trace)` on `old3` returns that sentence.)

`tests/test_refocus_licence.py`:
```python
def test_blind_spots_name_task_ordering(tmp_path):
    run_id, sdir = rec(tmp_path, LOOP)
    r = refocus(sdir, run_id, "--focus", "prog:helper")
    assert ("the order threads ran in relative to one another, and the "
            "order asyncio tasks interleaved in: recorded, never compared"
            ) in r.stdout
```

- [ ] **Step 2: Run, expect FAIL.**

- [ ] **Step 3: Implement**

`_BLIND_SPOTS` — replace the ordering line with:
```python
    "  - argument and return values, per-line state, timing, the order "
    "threads ran in relative to one another, and the order asyncio tasks "
    "interleaved in: recorded, never compared",
```
`_refusal(meta)` → `_refusal(meta, trace=None)`; append before `return None`:
```python
    if (trace is not None and trace.fingerprint_basis == "per-thread"
            and trace.tasks()):
        n = len(trace.tasks())
        return (f"original was recorded under the per-thread fingerprint "
                f"basis and ran {n} asyncio task(s); this version compares "
                "tasks by content and defines thread streams without them, "
                "so no verdict against it would compare like with like -- "
                "re-record it with this version")
```
(update the one call site to pass the opened trace).

Task divergence beside the thread one:
```python
def _task_divergence(orig: Trace, new: Trace, res: dict) -> str | None:
    t = res.get("tasks")
    if not t or t["verdict"] != "DIVERGED":
        return None
    def fmt(rows):
        return ", ".join((n if n is not None else "(unnamed)")
                         + ("" if k == 1 else f" x{k}") for n, _h, k in rows
                         ) or "-"
    s = (f"{t['n_a']} task stream(s) originally, {t['n_b']} on the rerun; "
         f"only in A: {fmt(t['only_a'])}; only in B: {fmt(t['only_b'])}")
    p = t["pair"]
    if p:
        s += (f"; first difference inside {p['name']} at causal step "
              f"{p['index']}: A {p['a_desc']} / B {p['b_desc']}")
    return s


def final_verdict(orig, new, res) -> tuple[str, str | None, str | None]:
    if res["verdict"] == "REFUSED":
        return res["verdict"], None, None
    threads = _thread_divergence(orig, new)
    tasks = _task_divergence(orig, new, res)
    if res["verdict"] == "DIVERGED" and res.get("index") is not None:
        return "DIVERGED", None, tasks     # the compared thread itself parted
    return ("DIVERGED" if (threads or tasks) else "MATCH"), threads, tasks
```
`assess()` stores `"tasks": tasks`; the printing: after the `threads:` line print
```python
    t = res.get("tasks") or {}
    if tasks_desc:
        print(f"tasks: DIVERGED -- {tasks_desc}")
        p = t.get("pair")
        if p and p["a_event"]:
            print(f"drill into A: sensorium tree {orig_name} --around e{p['a_event']}")
        if p and p["b_event"]:
            print(f"drill into B: sensorium tree {new_name} --around e{p['b_event']}")
    elif t.get("verdict") == "MATCH":
        print(f"tasks: {t['n_b']} task stream(s) compared by content, all "
              "matching; the ordering between tasks is not compared")
```
The DIVERGED `why` sentence gains a third arm: `"a task took a different path"` when only tasks diverged (threads None, res index None). `_verified_facts` inserts, after the first fact, `f"{n} task stream(s) compared by content"` when `n = len(new.task_fingerprints())` is > 0 (and the licence line `verified against … on exactly these points` prints it); `_licence_caveats` unchanged (task ordering is a blind spot, not a caveat — it is structural, like thread interleaving is already listed there). The `runs`/`info` stamping is unchanged (verdict + licence only).

- [ ] **Step 4: Run, expect PASS** — the new tests, then `tests/test_refocus*.py tests/test_runs_info.py`, then the full suite.
- [ ] **Step 5: Mutations** — (a) `final_verdict` ignores `tasks` → content-flip test fails; (b) `_task_divergence` always None → same; (c) drop the `_refusal` basis arm → the per-thread-basis refusal test fails; (d) revert the blind-spot wording → the licence test fails.
- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/refocus_cmd.py tests/refocus_programs.py tests/test_refocus.py tests/test_refocus_licence.py tests/test_format3_fixture.py
git commit -m "feat(refocus): a task that took another path is DIVERGED by content, not by interleaving; basis guard; licence and blind-spot lines"
```

---

### Task 5: `info` lines + corpus case `async_refocus`

**Files:**
- Modify: `src/sensorium/query/info_cmd.py` (~line 97–131), `tests/test_runs_info.py`, `tests/test_format3_fixture.py`
- Create: `corpus/async_refocus/main.py`, `corpus/async_refocus/questions.yaml`
- Modify: `tests/test_corpus.py` (count floor → `>= 20`)

**Interfaces:**
- Consumes: `Trace.fingerprint_basis`, `task_fingerprints()` (Task 1); `diff`/`refocus` output (Tasks 3–4).

- [ ] **Step 1: Failing tests**

`tests/test_runs_info.py`:
```python
def test_info_states_the_fingerprint_basis_and_the_task_rows(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, TWO_TASKS)      # use the file's own recorder helper
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert ("fingerprints: per-task basis -- each thread row covers the "
            "events that ran in no asyncio task; 2 task fingerprint(s) "
            "beside it") in out
```
`tests/test_format3_fixture.py`:
```python
def test_info_on_old3_says_its_thread_fingerprint_covers_task_events(
        installed_fixture3, capsys):
    assert cli.main(["info", installed_fixture3]) == 0
    out = capsys.readouterr().out
    assert ("fingerprints: per-thread basis -- each thread row covers every "
            "causal event on the thread, task events included; no task "
            "fingerprints were recorded (recorded before they existed)") in out
    assert "per-task basis" not in out
```
(import `cli` in that file.)

- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** in `info_cmd.py`, right after the per-thread fingerprint lines (~line 99):
```python
    if t.fingerprint_basis == "per-task":
        print("fingerprints: per-task basis -- each thread row covers the "
              "events that ran in no asyncio task; "
              f"{len(t.task_fingerprints())} task fingerprint(s) beside it")
    else:
        print("fingerprints: per-thread basis -- each thread row covers "
              "every causal event on the thread, task events included; no "
              "task fingerprints were recorded (recorded before they "
              "existed)")
```
- [ ] **Step 4: Run, expect PASS.** Mutation: swap the two arms → both tests fail.

- [ ] **Step 5: Corpus case — REGISTER FIRST**

`corpus/async_refocus/main.py`:
```python
"""Two asyncio tasks whose interleaving depends on state OUTSIDE the
process (a counter file, as in `nondeterministic`): the original run
starts task-A first, the rerun starts task-B first, and each task does the
same work either way. With --branch, the rerun ALSO sends task-B down
another path.

Ground truth: `refocus` says MATCH on the plain program -- tasks are
compared by content, the order they interleaved in is not compared and
says so -- and DIVERGED naming task-B on the branching program. A tool
that compared the thread's event order would call the plain program
DIVERGED: that is the false alarm plan 2b removes.

The pins name no line numbers, but the task names and function names are
part of the fixture.
"""
import asyncio
import sys
from pathlib import Path

COUNTER = Path("run_count.txt")


def step(n):
    return n


def other(n):
    return -n


async def worker(name, branch):
    step(1)
    await asyncio.sleep(0)
    if branch and name == "B":
        other(2)
    else:
        step(2)


async def amain(flip, branch):
    names = ["B", "A"] if flip else ["A", "B"]
    await asyncio.gather(*[
        asyncio.create_task(worker(n, branch), name=f"task-{n}")
        for n in names])


def main():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    # Harness order (corpus/run_corpus.py::run_case): run 1 (n=0), run 2
    # with --branch (n=1), then the questions: refocus of run 1 (n=2),
    # refocus of run 2 (n=3). The start order flips between a recording and
    # its rerun (n//2 parity); the branch fires only on the rerun of the
    # --branch recording (n >= 3). So question 1 differs by interleaving
    # alone, question 2 by task-B's content as well.
    flip = (n // 2) % 2 == 1
    branch = "--branch" in sys.argv and n >= 3
    asyncio.run(amain(flip, branch))
    print("done")


main()
```
`corpus/async_refocus/questions.yaml` (write BEFORE running; record the mtime):
```yaml
program: main.py
record: {focus: ["main:worker"]}
questions:
  - id: is-the-rerun-the-same-execution-when-only-the-interleaving-moved
    ask: >
      The rerun started the two tasks in the other order. Was it still the
      same execution, so the deeper capture describes the run I recorded?
    truth: >
      Yes. Each task's own CALL/RETURN/RAISE/HANDLED stream is identical to
      the original's, and the thread's stream outside any task is identical
      too; only the order the tasks interleaved in moved, and that order is
      recorded but never compared -- the verdict says so. MATCH, exit 0,
      with the task streams named as compared by content.
    why_logs_fail: >
      Two log files from these runs differ in line order and nothing else,
      and a diff of them screams. Deciding that the difference is ONLY the
      interleaving needs each task's events separated out and compared as
      its own sequence, which a flat log has no notion of.
    command: ["refocus", "$RUN", "--focus", "main:step"]
    expect_exit: 0
    expect_contains:
      - "refocus verdict: MATCH"
      - "tasks: 2 task stream(s) compared by content, all matching; the ordering between tasks is not compared"
      - "2 task stream(s) compared by content"
    expect_absent: ["refocus verdict: DIVERGED", "tasks: DIVERGED"]
  - id: which-task-took-another-path
    depends_on: is-the-rerun-the-same-execution-when-only-the-interleaving-moved
    ask: >
      Re-recorded with --branch, the rerun's task-B called other() instead
      of step(2). Which task diverged, and where?
    truth: >
      task-B; task-A's stream is identical. The verdict is DIVERGED, the
      tasks line names task-B as the stream with no counterpart, and the
      first difference inside task-B is step vs other with a drill-in
      command for each side.
    why_logs_fail: >
      A log shows other() was called somewhere in the second run; saying
      WHICH task's stream it belongs to, and that the other task was
      unaffected, needs every event attributed to its task and each task
      compared as its own sequence -- prints carry no task identity.
    command: ["refocus", "$RUN2", "--focus", "main:step"]
    expect_exit: 1
    expect_contains:
      - "refocus verdict: DIVERGED"
      - "tasks: DIVERGED"
      - "first difference inside task-B"
      - "drill into A: sensorium tree"
    expect_line:
      - ["first difference inside task-B", "step", "other"]
    expect_absent: ["refocus verdict: MATCH"]
second_run: {argv: ["--branch"]}
```
(Harness facts, verified: `run_case` records run 1, then run 2 (`second_run.argv`), THEN runs the questions in order; substitutions are `$RUN` / `$RUN2`; the top-level key is `second_run`. The counter parity in `main()` above is worked out for exactly that order — confirm it by reading the two `refocus` outputs during the bite-check and record the four `runs` rows in the report. If the interleaving-only rerun does not produce a different task start order, the MATCH is still true but the case proves less: fix the program, not the pin.)
Run `python -m corpus.run_corpus --only async_refocus`; bite-check each expectation (flip it → fails); then the whole corpus; `tests/test_corpus.py` floor → 20.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/info_cmd.py tests/test_runs_info.py tests/test_format3_fixture.py corpus/async_refocus tests/test_corpus.py
git commit -m "feat(info): state the fingerprint basis; corpus: async_refocus (interleaving is not divergence, a task that branched is)"
```

---

### Task 6: Bench, README, spec addendum, version 0.4.0, matrix

**Files:** `corpus/_bench/bench.py` (run only), `README.md`, `pyproject.toml`, the spec (status line + D6 addendum), `tests/test_corpus.py` if the README quotes counts.

- [ ] **Step 1: Bench** — `python -m corpus.run_corpus --bench` on this branch and on `e679b7c` (worktree under the job tmp dir, removed after): the per-task dict lookup is one more `dict.get` per causal event; report `call_dense` / `async_call_dense` / `await_dense` before/after; if any moves by > 0.2 µs/event say so in the README Overhead section.
- [ ] **Step 2: README** —
  - `### refocus` table, MATCH row: `every thread that left a fingerprint in both runs produced the **identical sequence of (file, qualname, kind) for CALL/RETURN/RAISE/HANDLED** outside any asyncio task, every asyncio task's own stream has a counterpart of the same name and content on the other side (a multiset — the order tasks interleaved in is never compared), and there was at least one such event to compare`; add one sentence under the table: "`diff --task NAME` diffs one task's stream by name; unnamed tasks match only unnamed tasks. Traces recorded before 0.4.0 define a thread stream to include task events (`info` says `per-thread basis`); comparing one of those with a 0.4.0 trace is REFUSED whenever either ran a task."
  - `## What a trace file holds`: add `- one causal fingerprint per thread (events outside any task) and per asyncio task`.
  - `## Not yet`: remove the plan-2b sentence.
  - `## Corpus`: twenty programs / N questions (measure) + the `async_refocus` sentence.
  - Overhead: the numbers from Step 1.
  - Version mentions that describe the current version → `0.4.0`.
- [ ] **Step 3: Spec** — status line → `Status: plans 2a and 2b implemented (2a on feat/async-arc2 / PR #3; 2b on feat/async-arc2b)`; append under D6: "*Addendum (plan 2b):* the narrowing of the thread fingerprint is marked by meta `fingerprint_basis = "per-task"`; traces without the marker are read under the per-thread definition; `refocus`/`diff` refuse to compare across bases when either side recorded a task and compare normally when neither did; `causal_stream` narrows to `task_id IS NULL` under the per-task basis."
- [ ] **Step 4: `pyproject.toml` version 0.4.0.**
- [ ] **Step 5: Matrix** — `uv venv <jobtmp>/sv312 -p 3.12` (exists; `uv pip install -p … -e .` to refresh), same for 3.13; full pytest + corpus on 3.12/3.13/3.14; record the result lines.
- [ ] **Step 6: Commit** — `docs: per-task fingerprints (arc 2b) -- README, version 0.4.0`.

---

## Self-review

**Spec coverage:** D6 recorder (per-task `Fingerprint`, thread fp over NULL-task events, rows at uninstall) → Task 2; D6 comparison multiset / DIVERGED naming + first differing step + drill-ins / REFUSED when nothing to compare / licence line / `--task NAME` / unnamed-match-unnamed → Tasks 3–4; honesty rule 3 (YIELD/RESUME never fingerprinted) → Task 2 test; D3 "no second format bump; meaning narrows" → the basis marker (Task 1) with its reader and refusal rules (Tasks 3–4); fixture discipline → Task 0; `info` → Task 5; verification norms (corpus pre-registration, matrix, bench, README cost) → Tasks 5–6. Out of D6: nothing left.

**Placeholder scan:** Task 3's `--task` printing and Task 5's corpus parity are described by contract with the decision rule spelled out (the implementer must read `run_corpus.py`'s second-run order and record it); everything else carries code and exact strings.

**Type consistency:** `Trace.task_fingerprints() -> dict[int, tuple[str|None, str, int]]` used by Tasks 2–5; `task_shapes()` Counter of `(name, hash)` used by `compare_tasks`; `_shape_difference` returns lists of `(name, hash, count)`; `compare()['tasks']` keys `verdict/only_a/only_b/pair/n_a/n_b` used by both printers; `final_verdict` returns a 3-tuple (update its two callers: `assess` and the print path); `_refusal(meta, trace=None)`.
