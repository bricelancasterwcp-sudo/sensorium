# Async Attribution (arc 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the recorder guessing parentage, stamp asyncio task identity on every event, and make `tree`/`frame`/`info`/`watch` state what the trace can and cannot attribute — without making anything inside an `async def` inspectable yet (that is arc 2).

**Architecture:** The tracer replaces its per-thread "last opened frame is the caller" stack with a per-thread map of live frames keyed by frame address, verified by code identity, and derives every parent from the caller frame's `f_back`. Each event additionally carries the current asyncio task's minted serial (lazily bound, so programs that never import asyncio pay one `sys.modules` probe per event). The trace format goes 1→2 (additive: `events.task_id`, new `tasks` table, new CALL-payload keys); a format-1 trace still opens and is labelled "parentage assumed". Query commands group by task, render unframed coroutine/generator calls as events with their real caller named, and refuse to explain a missing value with a reason the trace contradicts.

**Tech Stack:** Python 3.12–3.14, `sys.monitoring` (PEP 669), sqlite3, pytest, PyYAML (corpus), `uv` for venvs. Stdlib-only runtime — no new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-21-sensorium-async-design.md` — read it first; every task below cites the section it implements.

## Global Constraints

- Python floor stays `>=3.12`; CI matrix is 3.12 / 3.13 / 3.14 and every task's tests must pass on all three (`uv run -p 3.12 …` etc. — see Task 12 for the exact commands).
- Stdlib-only runtime: the recorder must **not** `import asyncio` itself (spec D2: lazy bind via `sys.modules`). A synchronous program's `sys.modules` must be unchanged by recording.
- Per-event overhead budget for the sync path: one `"asyncio" in sys.modules` probe plus two dict ops (spec "Measurements": ~50 ns against ~6 µs/event). No exception may be raised on the common path (`current_task()` raises outside a loop — gate on `_get_running_loop()`).
- Every new test is **mutation-checked**: after it passes, break the code it covers in the named way, confirm the test fails, restore. Steps say exactly which mutation.
- Corpus questions are pre-registered: write `ask`/`truth`/`command`/expectations **before** running the command; if the output disagrees, the tool is wrong until proven otherwise.
- Identity is never `id()` of an object that can die while the key is held, and never a user-supplied name (spec D1 "Why `id()` is sound here", D2).
- Hostile program objects (`__class__`, `__hash__`, `get_name`, `__repr__`) must never crash the recorder — guard with `try/except BaseException`, count, report; never silently swallow (project precedent: `capture.plain_str`, `_exit_status_of`).
- Output format for **synchronous** traces must stay byte-compatible with v1 wherever a test pins it (`tests/test_tree_frame.py`, `tests/test_runs_info.py`); new lines are additive.
- Commit messages: conventional (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), no attribution trailer (repo setting).
- Branch: `feat/async-attribution` (already exists, spec committed on it). Never commit to `main`.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tests/fixtures/format1_async.py` | the two-task program the v1 fixture was recorded from | create |
| `tests/fixtures/format1_async.db` | **real v1 (e384ef4) recording**, trace_format 1 | create (binary, ~50 KB) |
| `src/sensorium/store/db.py` | schema, `TRACE_FORMAT` | 1→2; `events.task_id`; `tasks` table |
| `src/sensorium/store/writer.py` | batched writer | `add_event(..., task_id=None)`, `add_task`, explicit column list |
| `src/sensorium/store/reader.py` | read-side model | `Event.task_id`, `Task`, `tasks()`, `format`, `unframed_calls()`, `call_counts()`, `parentage_basis()` |
| `src/sensorium/record/tracer.py` | recorder | `_TLS.live` replaces `_TLS.stack`; derived parentage; task serials; `unframed_focus()`; `FocusSpec.entries_matching` |
| `src/sensorium/record/boot.py` | `run_target` | focus-unframed warning + meta; `task_errors` meta |
| `src/sensorium/query/tree_cmd.py` | call tree | task groups, unframed children, caller tags, footers |
| `src/sensorium/query/frame_cmd.py` | one activation | three-way `--fn` answer; task in header |
| `src/sensorium/query/info_cmd.py` | summary | unframed count, tasks, call-based hot list, task_errors |
| `src/sensorium/query/watch_cmd.py` | predicate | unframed note; honest NEVER RECORDED reasons |
| `corpus/async_interleaved/` | corpus case 1 | create |
| `corpus/unframed_callers/` | corpus case 2 (generator + sorted key) | create |
| `corpus/async_cancelled/` | corpus case 3 | create |
| `corpus/async_focus/` | corpus case 5 | create |
| `corpus/_bench/bench.py` | overhead | add `async_call_dense` workload |
| `tests/test_async.py` | recorder-level async/derivation tests | create |
| `tests/test_format1_fixture.py` | old-trace honesty | create |
| `tests/test_store_db.py`, `test_writer.py`, `test_reader.py`, `test_tracer.py`, `test_focus.py`, `test_boot_cli.py`, `test_tree_frame.py`, `test_runs_info.py`, `test_watch.py`, `test_corpus.py`, `test_bench.py` | existing suites | extend |
| `README.md`, `pyproject.toml`, spec D1 | docs/version | update |

Setup for every task (once per session):

```bash
cd ~/workspace/sensorium
git checkout feat/async-attribution
[ -d .venv ] || uv venv .venv -p 3.14
uv pip install -p .venv/bin/python -e ".[dev]"
.venv/bin/python -m pytest -q -x 2>&1 | tail -3      # must be green before you start
```

`PY=.venv/bin/python` is assumed in every `Run:` line below.

---

### Task 0: Capture a real format-1 trace before the format changes

**Files:**
- Create: `tests/fixtures/format1_async.py`
- Create: `tests/fixtures/format1_async.db`
- Create: `tests/fixtures/__init__.py` (empty — keeps pytest rootdir imports simple)
- Test: `tests/test_format1_fixture.py`

**Interfaces:**
- Produces: `tests/fixtures/format1_async.db` — a trace whose `meta.trace_format == 1`, recorded by sensorium at `e384ef4` from `format1_async.py`. Tasks 2, 6, 7, 8 read it.

The fixture must be recorded by the **old recorder**, not synthesised — the point is that it is old (spec "Verification" case 4). A git worktree at the v1 merge commit is the only honest source.

- [ ] **Step 1: Write the program the fixture records**

`tests/fixtures/format1_async.py`:

```python
"""Two asyncio tasks, each calling a plain sync helper three times.

This file is the SOURCE of tests/fixtures/format1_async.db, recorded by the
v1 recorder at e384ef4 (trace_format 1). Do not edit it: the .db is a record
of what v1 wrote for exactly this program, and the test that reads it pins
how a format-2 reader describes a format-1 trace.
"""
import asyncio


def step(task, n):
    return f"{task}:{n}"


async def worker(name, delay):
    step(name, 1)
    await asyncio.sleep(delay)
    step(name, 2)
    await asyncio.sleep(delay)
    return step(name, 3)


async def main():
    a = asyncio.create_task(worker("A", 0.01), name="task-A")
    b = asyncio.create_task(worker("B", 0.02), name="task-B")
    return await asyncio.gather(a, b)


if __name__ == "__main__":
    print(asyncio.run(main()))
```

- [ ] **Step 2: Record it with the v1 recorder in a throwaway worktree**

```bash
cd ~/workspace/sensorium
git worktree add /tmp/sensorium-v1-fixture e384ef4
cd /tmp/sensorium-v1-fixture
uv venv .venv -p 3.14 && uv pip install -p .venv/bin/python -e .
mkdir -p /tmp/fixture-store
cp ~/workspace/sensorium/tests/fixtures/format1_async.py ./format1_async.py
SENSORIUM_DIR=/tmp/fixture-store .venv/bin/sensorium run -- format1_async.py
ls /tmp/fixture-store/traces/
```

Expected: `['A:3', 'B:3']`, then `run: <id>` and `trace: /tmp/fixture-store/traces/<id>.db`.

- [ ] **Step 3: Copy it in, verify it is format 1, clean up the worktree**

```bash
cp /tmp/fixture-store/traces/*.db ~/workspace/sensorium/tests/fixtures/format1_async.db
touch ~/workspace/sensorium/tests/fixtures/__init__.py
cd ~/workspace/sensorium
$PY - <<'PY'
import sqlite3, json
c = sqlite3.connect("tests/fixtures/format1_async.db")
print("trace_format:", json.loads(c.execute("SELECT value FROM meta WHERE key='trace_format'").fetchone()[0]))
print("events:", c.execute("SELECT COUNT(*) FROM events").fetchone()[0])
print("cols:", [r[1] for r in c.execute("PRAGMA table_info(events)")])
PY
ls -la tests/fixtures/format1_async.db
git worktree remove /tmp/sensorium-v1-fixture --force
rm -rf /tmp/fixture-store
```

Expected: `trace_format: 1`, `events: 20`, cols without `task_id`, file well under 200 KB.

- [ ] **Step 4: Write the test that pins the fixture is what it claims**

`tests/test_format1_fixture.py`:

```python
"""A trace recorded by the v1 recorder (trace_format 1), read by this one.

The fixture is a real recording, not a synthesised schema -- see
tests/fixtures/format1_async.py. These tests pin what a format-2 reader
CLAIMS about a format-1 trace: it opens, it says nothing about tasks (none
were recorded), and it labels parentage ASSUMED rather than letting v1's
last-opened-frame guess inherit the credibility of derived parentage.
"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from sensorium import cli
from sensorium.store.reader import Trace

FIXTURE = Path(__file__).parent / "fixtures" / "format1_async.db"


def test_fixture_really_is_trace_format_1():
    c = sqlite3.connect(FIXTURE)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    cols = [r[1] for r in c.execute("PRAGMA table_info(events)")]
    assert fmt == 1
    assert "task_id" not in cols


def test_fixture_opens_under_the_current_reader():
    t = Trace.open(FIXTURE)
    assert t.counts()["CALL"] == 10


@pytest.fixture
def installed_fixture(tmp_path, monkeypatch):
    """The fixture placed in a disposable trace store, as run id `old`."""
    store = tmp_path / "sdir" / "traces"
    store.mkdir(parents=True)
    shutil.copy(FIXTURE, store / "old.db")
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return "old"
```

- [ ] **Step 5: Run, commit**

Run: `$PY -m pytest tests/test_format1_fixture.py -v`
Expected: 2 passed.

```bash
git add tests/fixtures/ tests/test_format1_fixture.py
git commit -m "test: capture a real v1 (format-1) async trace as a fixture"
```

---

### Task 1: Trace format 2 — schema and writer

**Files:**
- Modify: `src/sensorium/store/db.py:6` (`TRACE_FORMAT`), `:41-50` (events table), add `tasks` table after `output`
- Modify: `src/sensorium/store/writer.py:40-51` (`add_event`), add `add_task`, `:98-126` (`_flush_locked`)
- Test: `tests/test_store_db.py`, `tests/test_writer.py`

**Interfaces:**
- Produces: `db.TRACE_FORMAT == 2`; `events.task_id INTEGER` (nullable); `tasks(id INTEGER PRIMARY KEY, name TEXT, thread_id INTEGER NOT NULL)`; `TraceWriter.add_event(ts_ns, thread_id, kind, frame_id, code_id, line, payload, task_id=None) -> int`; `TraceWriter.add_task(task_id: int, name: str | None, thread_id: int) -> None`.
- Existing positional `add_event` call sites (5 in tests) keep working because `task_id` is keyword-with-default.

- [ ] **Step 1: Failing tests**

Append to `tests/test_store_db.py`:

```python
def test_format_2_has_task_id_and_tasks_table(tmp_path):
    """Spec D4: events gains a nullable task_id; a tasks table maps serial to
    display name once, not per event; frames is unchanged."""
    conn = db.create_trace(tmp_path / "t.db")
    assert db.get_meta(conn, "trace_format") == 2
    ev_cols = [r[1] for r in conn.execute("PRAGMA table_info(events)")]
    assert ev_cols[-1] == "task_id"
    task_cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)")]
    assert task_cols == ["id", "name", "thread_id"]
    fr_cols = [r[1] for r in conn.execute("PRAGMA table_info(frames)")]
    assert fr_cols == ["id", "parent_id", "code_id", "call_event_id",
                       "return_event_id", "depth", "thread_id", "closed_by",
                       "unwind_exc"]
```

Also change the existing assertion `assert db.get_meta(conn, "trace_format") == 1` in `test_create_trace_has_all_tables` to `== db.TRACE_FORMAT` and add `"tasks"` to its expected table set.

Append to `tests/test_writer.py`:

```python
def test_add_event_task_id_defaults_to_null_and_round_trips(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=100)
    cid = w.intern_code("/x/prog.py", "f", 1)
    e1 = w.add_event(10, 7, "CALL", None, cid, 1, {"args": {}})
    e2 = w.add_event(11, 7, "CALL", None, cid, 1, {"args": {}}, task_id=3)
    w.add_task(3, "task-A", 7)
    w.add_task(4, None, 7)                  # a task whose name was unreadable
    w.close()
    c = sqlite3.connect(p)
    rows = c.execute("SELECT id, task_id FROM events ORDER BY id").fetchall()
    assert rows == [(e1, None), (e2, 3)]
    tasks = c.execute("SELECT id, name, thread_id FROM tasks ORDER BY id").fetchall()
    assert tasks == [(3, "task-A", 7), (4, None, 7)]
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY -m pytest tests/test_store_db.py tests/test_writer.py -q`
Expected: FAIL — `trace_format == 1`, no `tasks` table, `add_event() got an unexpected keyword argument 'task_id'`.

- [ ] **Step 3: Implement**

`src/sensorium/store/db.py`:

```python
TRACE_FORMAT = 2
```

In `SCHEMA`, change the events table and add `tasks` after `output`:

```sql
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts_ns INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  frame_id INTEGER,
  code_id INTEGER,
  line INTEGER,
  payload TEXT,
  task_id INTEGER
);
CREATE TABLE output (
  id INTEGER PRIMARY KEY,
  after_event_id INTEGER NOT NULL,
  stream TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  name TEXT,
  thread_id INTEGER NOT NULL
);
```

Extend the `TraceFormatError` docstring's last sentence with: `Format 2 (async attribution) added events.task_id, the tasks table and CALL-payload keys; a format-1 trace opens and its parentage is reported as assumed -- see reader.Trace.parentage_basis.`

`src/sensorium/store/writer.py` — `__init__` gains `self._tasks: list[tuple] = []`; replace `add_event` and add `add_task`; replace the events insert in `_flush_locked`:

```python
    def add_event(self, ts_ns, thread_id, kind, frame_id, code_id, line,
                  payload: dict | None, task_id: int | None = None) -> int:
        p = (None if payload is None
             else json.dumps(payload, separators=(",", ":"), default=repr))
        with self._lock:
            eid = self._next_event
            self._next_event += 1
            self._events.append(
                (eid, ts_ns, thread_id, kind, frame_id, code_id, line, p,
                 task_id))
            if len(self._events) >= self._batch:
                self._flush_locked()
            return eid

    def add_task(self, task_id: int, name: str | None, thread_id: int) -> None:
        """One row per asyncio task, written when its serial is minted."""
        with self._lock:
            self._tasks.append((task_id, name, thread_id))
```

In `_flush_locked`, replace the events `executemany` and add tasks before `output`:

```python
        if self._events:
            c.executemany(
                "INSERT INTO events (id, ts_ns, thread_id, kind, frame_id, "
                "code_id, line, payload, task_id) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?)", self._events)
            self._events.clear()
        if self._tasks:
            c.executemany(
                "INSERT INTO tasks (id, name, thread_id) VALUES (?, ?, ?)",
                self._tasks)
            self._tasks.clear()
```

- [ ] **Step 4: Run the two files, then the whole suite**

Run: `$PY -m pytest tests/test_store_db.py tests/test_writer.py -q` → all pass.
Run: `$PY -m pytest -q -x` → all pass (the reader still selects 8 named columns, so nothing downstream notices yet).

- [ ] **Step 5: Mutation check** — in `add_event`, change `task_id))` to `None))` (drop the value); `test_add_event_task_id_defaults_to_null_and_round_trips` must fail on `(e2, None)`. Restore.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/store/db.py src/sensorium/store/writer.py tests/test_store_db.py tests/test_writer.py
git commit -m "feat(store): trace format 2 -- events.task_id and a tasks table"
```

---

### Task 2: Reader — tasks, format, unframed calls, call counts

**Files:**
- Modify: `src/sensorium/store/reader.py:19-28` (`Event`), add `Task`, `:61-70` (`Trace.__init__`, `_EVENT_COLS` selection), add methods
- Test: `tests/test_reader.py`, `tests/test_format1_fixture.py`

**Interfaces:**
- Produces:
  - `Event.task_id: int | None = None` (last field; positional 8-arg construction still valid)
  - `@dataclass(frozen=True) class Task: id: int; name: str | None; thread_id: int`
  - `Trace.format -> int` — `meta["trace_format"]`, 1 if absent
  - `Trace.tasks() -> list[Task]` — `[]` on a trace with no `tasks` table
  - `Trace.task(task_id) -> Task | None`
  - `Trace.unframed_calls(code_id: int | None = None) -> list[Event]` — CALL events with no frame whose `call_event_id` is that event; **works on format 1 too** (it is a join, not a payload key)
  - `Trace.call_counts() -> dict[int, int]` — code_id → number of CALL events
  - `Trace.parentage_basis() -> str` — `"derived"` if `format >= 2` else `"assumed"`
- Consumes: Task 1 schema.

- [ ] **Step 1: Failing tests**

Append to `tests/test_reader.py` (it already imports `TraceWriter`, `Trace`; add `from pathlib import Path` if missing):

```python
def _two_task_trace(tmp_path):
    """Hand-built: one framed call, two unframed calls (one per task)."""
    w = TraceWriter(tmp_path / "t.db", batch=100)
    c_main = w.intern_code("/x/p.py", "main", 1)
    c_gen = w.intern_code("/x/p.py", "gen", 5)
    e1 = w.add_event(0, 1, "CALL", None, c_main, 1, {"args": {}})
    f1 = w.open_frame(None, c_main, e1, 0, 1)
    w.add_event(1, 1, "CALL", None, c_gen, 5,
                {"args": {}, "unframed": "generator", "parent_frame": f1},
                task_id=1)
    w.add_event(2, 1, "CALL", None, c_gen, 5,
                {"args": {}, "unframed": "generator"}, task_id=2)
    w.add_task(1, "Task-1", 1)
    w.add_task(2, None, 1)
    w.close()
    return Trace.open(tmp_path / "t.db"), c_main, c_gen, f1


def test_reader_exposes_format_tasks_and_task_ids(tmp_path):
    t, c_main, c_gen, _ = _two_task_trace(tmp_path)
    assert t.format == 2
    assert t.parentage_basis() == "derived"
    assert [(k.id, k.name, k.thread_id) for k in t.tasks()] == [
        (1, "Task-1", 1), (2, None, 1)]
    assert t.task(2).name is None and t.task(9) is None
    evs = t.events(kind="CALL")
    assert [e.task_id for e in evs] == [None, 1, 2]


def test_unframed_calls_is_a_join_not_a_payload_key(tmp_path):
    """Spec D3: 'recorded but not framed' must be decidable from the frames
    table alone, so a v1 trace (no `unframed` key) gets the same answer."""
    t, c_main, c_gen, f1 = _two_task_trace(tmp_path)
    unf = t.unframed_calls()
    assert [e.code_id for e in unf] == [c_gen, c_gen]
    assert t.unframed_calls(code_id=c_main) == []
    assert t.call_counts() == {c_main: 1, c_gen: 2}
```

Append to `tests/test_format1_fixture.py`:

```python
def test_format1_trace_reports_no_tasks_and_assumed_parentage():
    t = Trace.open(FIXTURE)
    assert t.format == 1
    assert t.tasks() == []                      # no table: not "zero tasks"
    assert t.parentage_basis() == "assumed"
    assert all(e.task_id is None for e in t.events())
    worker = next(c for c in t.codes() if c.qualname == "worker")
    assert len(t.unframed_calls(code_id=worker.id)) == 2   # join works on v1
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY -m pytest tests/test_reader.py tests/test_format1_fixture.py -q`
Expected: FAIL — `Trace` has no attribute `format`/`tasks`/`unframed_calls`.

- [ ] **Step 3: Implement**

`src/sensorium/store/reader.py` — extend `Event`, add `Task`, make column selection format-aware:

```python
@dataclass(frozen=True)
class Event:
    id: int
    ts_ns: int
    thread_id: int
    kind: str
    frame_id: int | None
    code_id: int | None
    line: int | None
    payload: dict | None
    task_id: int | None = None   # None outside a running loop, or format 1


@dataclass(frozen=True)
class Task:
    id: int
    name: str | None         # None when the name could not be read
    thread_id: int
```

Replace `_EVENT_COLS` / `_event` with two variants and a selector:

```python
_EVENT_COLS_V1 = "id, ts_ns, thread_id, kind, frame_id, code_id, line, payload"
_EVENT_COLS_V2 = _EVENT_COLS_V1 + ", task_id"


def _event(row) -> Event:
    # 8 columns on a format-1 trace, 9 on format 2; task_id defaults to None.
    return Event(*row[:7], _loads(row[7]), *row[8:])
```

In `Trace.__init__` after `self._code_cache = None`:

```python
        cols = {r[1] for r in conn.execute("PRAGMA table_info(events)")}
        # Decided from the table, not from meta: the column is the fact.
        self._ecols = _EVENT_COLS_V2 if "task_id" in cols else _EVENT_COLS_V1
        self._has_tasks = bool(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone())
```

Replace every `{_EVENT_COLS}` f-string in `events`, `event` with `{self._ecols}` (three sites: `events`, `event`; `frame_containing` uses `_FRAME_COLS` only). Add methods after `counts`:

```python
    @property
    def format(self) -> int:
        """`meta["trace_format"]`; a trace without the key predates it (1)."""
        return db.get_meta(self._c, "trace_format", 1)

    def parentage_basis(self) -> str:
        """"derived" (format 2+: parent = the caller frame, verified by code
        identity) or "assumed" (format 1: parent = the last frame opened on
        the thread, which is a guess that async resumption, generators and
        C-level callbacks all break). Query output labels the latter."""
        return "derived" if self.format >= 2 else "assumed"

    def tasks(self) -> list[Task]:
        if not self._has_tasks:
            return []
        return [Task(*r) for r in self._c.execute(
            "SELECT id, name, thread_id FROM tasks ORDER BY id")]

    def task(self, task_id: int) -> Task | None:
        if not self._has_tasks:
            return None
        row = self._c.execute(
            "SELECT id, name, thread_id FROM tasks WHERE id = ?",
            (task_id,)).fetchone()
        return None if row is None else Task(*row)

    def unframed_calls(self, code_id: int | None = None) -> list[Event]:
        """CALL events no frame was opened for (generators, coroutines).

        A join on frames.call_event_id, deliberately not the `unframed`
        payload key: the key is format 2, the join answers for every format,
        and 'recorded but not framed' must be the same fact on both."""
        q = (f"SELECT {', '.join('e.' + c.strip() for c in self._ecols.split(','))} "
             "FROM events e LEFT JOIN frames f ON f.call_event_id = e.id "
             "WHERE e.kind = 'CALL' AND f.id IS NULL AND e.code_id IS NOT NULL")
        params: tuple = ()
        if code_id is not None:
            q += " AND e.code_id = ?"
            params = (code_id,)
        return [_event(r) for r in self._c.execute(q + " ORDER BY e.id", params)]

    def call_counts(self) -> dict[int, int]:
        """code_id -> CALL events. Counts activations, framed or not."""
        return dict(self._c.execute(
            "SELECT code_id, COUNT(*) FROM events WHERE kind = 'CALL' "
            "AND code_id IS NOT NULL GROUP BY code_id"))
```

- [ ] **Step 4: Run**

Run: `$PY -m pytest tests/test_reader.py tests/test_format1_fixture.py -q` → pass.
Run: `$PY -m pytest -q -x` → all pass.

- [ ] **Step 5: Mutation checks** — (a) in `unframed_calls` change `f.id IS NULL` to `f.id IS NOT NULL`: both unframed tests fail. (b) In `parentage_basis` return `"derived"` unconditionally: the fixture test fails. Restore both.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/store/reader.py tests/test_reader.py tests/test_format1_fixture.py
git commit -m "feat(reader): tasks, trace format, unframed calls and call counts"
```

---

### Task 3: Derived parentage in the recorder

**Files:**
- Modify: `src/sensorium/record/tracer.py` — `_TLS` (`:280-289`), `_on_start` (`:378-421`), `_on_return` (`:422-448`), `_on_unwind` (`:450-469`), `_exc_event` fid lookup (`:548-549`), `_on_line` entry lookup (`:577-579`), module docstring line 30-32
- Modify: `docs/superpowers/specs/2026-08-21-sensorium-async-design.md` D1 last paragraph (one sentence)
- Create: `tests/test_async.py`
- Test: `tests/test_tracer.py` (existing must stay green)

**Interfaces:**
- Produces (recorder-internal, used by Task 4/5):
  - `_TLS.live: dict[int, list]` — `id(frame) -> [frame_id, code, code_id, prev_locals, depth]`; **replaces** `_TLS.stack` entirely
  - `Tracer._parent_of(tls, caller) -> list | None` — the live entry for `caller` if present **and** `entry[1] is caller.f_code`, else `None`
  - `Tracer._note_caller(payload, caller)` — writes `payload["caller_code"] = <interned id>` when the caller's code is traced, `payload["caller"] = "untraced"` otherwise, nothing when `caller is None`
  - `_unframed_kind(code) -> str` — `"generator" | "coroutine" | "async_generator"`
  - CALL payload keys (spec D1/D4): `caller_code`, `caller`, `unframed`, `parent_frame`
  - `frames.parent_id` = derived parent or NULL; `frames.depth` = parent.depth+1 or 0

Deviation from spec D1 text ("tls.stack is retained"): every consumer of the stack (parent, depth, close, exception fid, LINE entry) moves to `live`, so keeping the stack would leave a second structure with no reader. Step 8 edits the spec sentence.

- [ ] **Step 1: Failing tests**

`tests/test_async.py`:

```python
"""Derived parentage and task identity, recorded in-process.

Every program here is shaped so that v1's `tls.stack[-1]` guess gives a
DIFFERENT answer from the caller frame -- coroutines resumed by the loop,
a generator calling a helper, a key function called back from C. The
assertions are on what the trace says the parent IS, not on the rendering.
"""
import sys

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
```

Add to `tests/test_tracer.py` (depth/close path through `live`, sync program — the depth/parent half must hold before AND after; the `live == {}` half is new). Add `record_inproc_full` to the file's `from tests.helpers import …` line.

```python
def test_frames_close_by_frame_identity_and_leave_no_live_entry(tmp_path):
    """Recursion: every activation of `f` must close its OWN frame, which a
    code-identity stack-top check cannot tell apart; the live map can. And
    once main has returned, the map must be EMPTY -- a stale entry is an
    address that can be recycled under a live key, the one thing the
    spec's id()-soundness argument forbids."""
    src = """
def f(n):
    return n if n == 0 else f(n - 1)

def main():
    return f(3)
"""
    t, err, tracer = record_inproc_full(tmp_path, src)
    assert err is None
    f_code = next(c for c in t.codes() if c.qualname == "f")
    frames = t.frames(code_id=f_code.id)
    assert [fr.depth for fr in frames] == [1, 2, 3, 4]
    assert all(fr.closed_by == "return" for fr in frames)
    assert [fr.parent_id for fr in frames][1:] == [fr.id for fr in frames][:-1]
    assert len(t.frames()) == 5                      # main + four f
    assert all(fr.return_event_id is not None for fr in t.frames())
    assert tracer._tls.live == {}
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY -m pytest tests/test_async.py tests/test_tracer.py::test_frames_close_by_frame_identity_and_leave_no_live_entry -q`
Expected: `test_sync_helper_inside_a_coroutine…` FAILS (parent_id is main's frame, no `caller_code`); `…unframed_with_their_kind` FAILS (no `unframed` key); `…rejects_a_live_entry` FAILS (`_parent_of` missing); the recursion test FAILS on `tracer._tls.live` (no such attribute yet) — its depth/parent assertions already hold.

- [ ] **Step 3: Implement — `_TLS` and helpers**

In `tracer.py`, add after `_is_control_flow`:

```python
_CO_GENERATOR, _CO_COROUTINE, _CO_ASYNC_GENERATOR = 0x20, 0x80, 0x200


def _unframed_kind(code) -> str:
    """Why this code opens no frame: which of the generator-like flags it has.
    Recorded on the CALL payload so the query side can say 'coroutine', not
    the vaguer 'coroutine or generator' it must say for a format-1 trace."""
    flags = code.co_flags
    if flags & _CO_ASYNC_GENERATOR:
        return "async_generator"
    if flags & _CO_COROUTINE:
        return "coroutine"
    return "generator"
```

Replace `_TLS.__init__`'s `self.stack` line:

```python
        # id(frame) -> [frame_id, code, code_id, prev_locals, depth] for every
        # OPEN frame this recorder opened on this thread. Replaces the stack
        # that v1 used: "the last frame I opened is the caller" is stack
        # discipline, which a coroutine resumed by the event loop, a generator
        # resumed by its consumer, and a callback from C all break. `id()` is
        # sound as a key here ONLY because every entry is a regular function
        # frame, which always leaves through PY_RETURN or PY_UNWIND -- both
        # subscribed -- so the entry is removed before the address can die. A
        # suspendable frame must not enter this map without a terminal
        # ABANDONED state (arc 2). `_parent_of` re-checks code identity anyway.
        self.live: dict[int, list] = {}
```

Update the module docstring lines 30-32 to:

```
A LINE event's `frame_id` is always set. Generators and coroutines are
frameless (no frame is opened for them), so LINE stays permanently disabled for
their code even when focused -- there would be no frame to attach to. Their
CALL is still recorded, with `unframed` naming the kind and either
`parent_frame` (the caller's open frame) or `caller_code` / `caller` saying who
called it. A framed call whose caller has no open frame gets `parent_id NULL`
and the same `caller_code` / `caller` keys: the parent is never guessed.
```

- [ ] **Step 4: Implement — `_on_start`**

Replace the body of `_on_start` from `tid = tls.thread_serial` to the end of the `try:` block:

```python
            tid = tls.thread_serial
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            caller = frame.f_back
            parent = self._parent_of(tls, caller)
            if parent is None:
                self._note_caller(payload, caller)
            if frameless:
                payload["unframed"] = _unframed_kind(code)
                if parent is not None:
                    payload["parent_frame"] = parent[0]
            eid = self.writer.add_event(time.monotonic_ns(), tid, "CALL",
                                        None, cid, code.co_firstlineno,
                                        payload)
            if not frameless:
                pfid = parent[0] if parent is not None else None
                depth = parent[4] + 1 if parent is not None else 0
                fid = self.writer.open_frame(pfid, cid, eid, depth, tid)
                tls.live[id(frame)] = [fid, code, cid, {}, depth]
            self._fp(tid).update(fp_file, qual, "CALL")
            # Frameless code is excluded on purpose: an abandoned generator
            # never reaches PY_RETURN/PY_UNWIND, so counting its PY_START would
            # leak depth and wedge the window open for the rest of the run.
            # The gate must open and close on the same set of events.
            if not frameless and win_key is not None:
                tls.window_depths[win_key] = tls.window_depths.get(win_key, 0) + 1
```

Add the two helpers right after `_fp`:

```python
    def _parent_of(self, tls, caller):
        """The live entry for `caller`, or None -- and None is an answer.

        A hit requires the address to be live AND the code to match: the
        map cannot hold a stale entry in arc 1 (see `_TLS.live`), but the
        check is what makes that a property of this method rather than of
        the current set of callers."""
        if caller is None:
            return None
        entry = tls.live.get(id(caller))
        if entry is None or entry[1] is not caller.f_code:
            return None
        return entry

    def _note_caller(self, payload, caller) -> None:
        """When there is no parent frame, record WHO called instead of
        guessing: the caller's interned code if it is traced (a frameless
        generator/coroutine, or code that started before recording did), or
        the literal "untraced" (the event loop, a C callback's Python caller
        in a library, sensorium's own boot). No caller at all writes nothing,
        which is distinct from both."""
        if caller is None:
            return
        ccode = caller.f_code
        traced, _rel, cqual, _f, _fl, _w = self._decide(ccode)
        if traced:
            payload["caller_code"] = self.writer.intern_code(
                ccode.co_filename, cqual, ccode.co_firstlineno)
        else:
            payload["caller"] = "untraced"
```

- [ ] **Step 5: Implement — close, exception and LINE paths through `live`**

`_on_return` — replace

```python
            fid = None
            if not frameless and tls.stack and tls.stack[-1][1] is code:
                fid = tls.stack.pop()[0]
```
with
```python
            frame = sys._getframe(1)
            entry = tls.live.get(id(frame))
            fid = None
            if entry is not None and entry[1] is code:
                del tls.live[id(frame)]
                fid = entry[0]
```

`_on_unwind` — replace

```python
            if not frameless and tls.stack and tls.stack[-1][1] is code:
                fid = tls.stack.pop()[0]
                self.writer.close_frame(
                    fid, None, "unwind",
                    capture_exc(exc, self.serial_of(exc)))
```
with
```python
            frame = sys._getframe(1)
            entry = tls.live.get(id(frame))
            if entry is not None and entry[1] is code:
                del tls.live[id(frame)]
                self.writer.close_frame(
                    entry[0], None, "unwind",
                    capture_exc(exc, self.serial_of(exc)))
```

`_exc_event` — replace

```python
            fid = tls.stack[-1][0] if (not frameless and tls.stack
                                       and tls.stack[-1][1] is code) else None
```
with
```python
            entry = tls.live.get(id(frame))
            fid = entry[0] if (entry is not None and entry[1] is code) else None
```

`_on_line` — replace

```python
        if not tls.stack or tls.stack[-1][1] is not code:
            return None           # no open frame for this activation
        entry = tls.stack[-1]
        frame = sys._getframe(1)
```
with
```python
        frame = sys._getframe(1)
        entry = tls.live.get(id(frame))
        if entry is None or entry[1] is not code:
            return None           # no open frame for this activation
```

Grep to be sure nothing references the old field: `grep -n "tls.stack\|\.stack\b" src/sensorium/record/tracer.py` → no hits. (`tests/helpers.py` mentions `tracer._tls.window_depth` in a docstring only.)

- [ ] **Step 6: Run**

Run: `$PY -m pytest tests/test_async.py tests/test_tracer.py -q` → pass.
Run: `$PY -m pytest -q -x` → all pass. `$PY corpus/run_corpus.py` → `0 failures`.

- [ ] **Step 7: Mutation checks**
  - In `_on_start`, change `caller = frame.f_back` to `caller = None`: `test_sync_helper_inside_a_coroutine…` fails (no `caller_code`) and `…key_fn_finds_main` fails. Restore.
  - In `_parent_of`, delete `or entry[1] is not caller.f_code`: `test_parent_of_rejects_a_live_entry…` fails. Restore.
  - In `_on_return`, change `del tls.live[id(frame)]` to `pass`: `test_frames_close_by_frame_identity_and_leave_no_live_entry` fails on `tracer._tls.live == {}`. Restore.
  - In `_on_return`, change `entry[1] is code` to `True`: nothing fails (in arc 1 the live entry at a returning frame's address is always that frame's) — expected; the guard is for arc 2 and is pinned in isolation by `_parent_of`'s test.

- [ ] **Step 8: Spec edit (the one deviation)**

In the spec D1 subsection "A property gained on the close path", replace the sentence `` `tls.stack` is retained — LINE events and locals capture still need the current activation — but it stops being the authority on parentage and on frame lifetime. `` with: `` `tls.stack` is removed: LINE capture, exception-site frames and frame close all look the activation up in `tls.live` by frame address, so there is one authority, not two that must agree. ``

- [ ] **Step 9: Commit**

```bash
git add src/sensorium/record/tracer.py tests/test_async.py tests/test_tracer.py docs/superpowers/specs/2026-08-21-sensorium-async-design.md
git commit -m "feat(record): derive parentage from the caller frame; name the caller when there is no parent"
```

---

### Task 4: Task identity in the recorder

**Files:**
- Modify: `src/sensorium/record/tracer.py` — `Tracer.__init__`, `_TLS.__init__`, every `add_event` call (`_on_start`, `_on_return`, `_exc_event`, two in `_on_line`), `uninstall`
- Modify: `src/sensorium/record/boot.py:543-577` (`_finalize_meta`) and the `_finalize_meta(...)` call in `run_target`
- Test: `tests/test_async.py`, `tests/test_boot_cli.py`

**Interfaces:**
- Produces:
  - `Tracer._task_serial(tls) -> int | None` — called inside every `in_hook` region; `None` outside a running loop, when no task is current, or on any failure
  - `Tracer._bind_asyncio() -> tuple | None` — lazily binds `(asyncio.events._get_running_loop, asyncio.current_task)` from `sys.modules`; never imports
  - `Tracer.task_errors -> int` — count of lookups that raised (hostile task objects); stamped as `meta["task_errors"]`
  - `_TLS.task_cache: tuple | None` — `(task, serial)` of the last task seen on this thread (identity check by `is`)
  - every event row carries `task_id`; `tasks` rows carry the name via `capture.plain_str(task.get_name())` or `None`
- Consumes: Task 1 `add_event(task_id=)`, `add_task`.

- [ ] **Step 1: Failing tests**

Append to `tests/test_async.py`:

```python
def test_events_inside_tasks_carry_distinct_minted_serials(tmp_path):
    t, err = record_inproc(tmp_path, TWO_TASKS)
    assert err is None
    tasks = {k.id: k for k in t.tasks()}
    names = sorted(k.name for k in tasks.values())
    assert names == ["Task-1", "task-A", "task-B"]      # amain's task + two
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
```

Append to `tests/test_boot_cli.py` (it imports `record_script`; check the top of the file and add the import if absent):

```python
def test_task_errors_meta_is_stamped_as_zero_on_a_clean_run(tmp_path):
    run_id, trace, r = record_script(tmp_path, "def main():\n    pass\nmain()\n")
    assert run_id, r.stderr
    from sensorium.store.reader import Trace
    assert Trace.open(trace).meta["task_errors"] == 0
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY -m pytest tests/test_async.py tests/test_boot_cli.py -q`
Expected: the four new async tests FAIL (`tasks()` empty / `task_id` None), the meta test FAILS with KeyError `task_errors`; `…does_not_import_asyncio` already passes (keep it — it guards the implementation you are about to write).

- [ ] **Step 3: Implement — `Tracer` state and `_task_serial`**

`Tracer.__init__`, after `self._serial_lock`/`_next_serial` lines:

```python
        # asyncio task identity: a minted serial per task object, weakly held
        # so finished tasks do not accumulate. Bound lazily from sys.modules
        # (never imported here) so a program that never uses asyncio pays one
        # dict probe per event and sees its sys.modules untouched.
        self._asyncio: tuple | None = None
        self._task_serials: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self._task_lock = threading.Lock()
        self._next_task = 0
        self.task_errors = 0       # lookups a hostile task object broke
```

`_TLS.__init__`: add `self.task_cache: tuple | None = None   # (task, serial) last seen on this thread`.

Add methods after `_note_caller`:

```python
    def _bind_asyncio(self):
        """(`_get_running_loop`, `current_task`) from the asyncio the PROGRAM
        imported, or None if it is not (fully) there yet. Both are C
        functions (`_asyncio`) on 3.12-3.14; `_get_running_loop` returns
        None outside a loop instead of raising, which is why it is the gate."""
        mod = sys.modules.get("asyncio")
        events = getattr(mod, "events", None)
        get_loop = getattr(events, "_get_running_loop", None)
        cur_task = getattr(mod, "current_task", None)
        if get_loop is None or cur_task is None:
            return None
        self._asyncio = (get_loop, cur_task)
        return self._asyncio

    def _count_task_error(self) -> None:
        with self._task_lock:
            self.task_errors += 1

    def _task_serial(self, tls):
        """The minted serial of the asyncio task running on this thread right
        now, or None: no asyncio, no running loop, no current task, or a task
        object that broke the lookup (counted in `task_errors`, never raised
        into the program). Must be called inside an `in_hook` region: a Task
        subclass's `get_name` is program code."""
        if "asyncio" not in sys.modules:
            return None
        fns = self._asyncio or self._bind_asyncio()
        if fns is None:
            return None
        get_loop, cur_task = fns
        try:
            if get_loop() is None:
                return None
            task = cur_task()
        except BaseException:
            self._count_task_error()
            return None
        if task is None:
            return None
        cache = tls.task_cache
        if cache is not None and cache[0] is task:
            return cache[1]
        try:
            with self._task_lock:
                serial = self._task_serials.get(task)
                minted = serial is None
                if minted:
                    self._next_task += 1
                    serial = self._next_task
                    self._task_serials[task] = serial
        except BaseException:          # hostile __hash__/__eq__ on a subclass
            self._count_task_error()
            return None
        if minted:
            try:
                name = plain_str(task.get_name())
            except BaseException:
                name = None
            self.writer.add_task(serial, name, tls.thread_serial)
        tls.task_cache = (task, serial)
        return serial
```

- [ ] **Step 4: Implement — stamp every event**

In `_on_start`, after `tid = tls.thread_serial`: `task = self._task_serial(tls)`; pass `task_id=task` to `add_event`. Same in `_on_return` (`task_id=self._task_serial(tls)`), in `_exc_event` (inside the `try`, before `add_event`), and both `add_event` calls in `_on_line`. In `uninstall`, after `refs.clear()` loop: `self._tls.task_cache = None`.

- [ ] **Step 5: Implement — meta**

`boot._finalize_meta` gains a keyword `task_errors` and writes `w.set_meta_final("task_errors", task_errors)`; `run_target` passes `task_errors=tracer.task_errors`.

- [ ] **Step 6: Run**

Run: `$PY -m pytest tests/test_async.py tests/test_boot_cli.py -q` → pass.
Run: `$PY -m pytest -q -x` and `$PY corpus/run_corpus.py` → green.

- [ ] **Step 7: Mutation checks**
  - In `_task_serial`, change `serial = self._next_task` to `serial = 1` (every task shares one serial): `test_events_inside_tasks_carry_distinct_minted_serials` fails (`by_task` merges) and `test_serials_are_minted_not_names…` fails (`same[0].id == same[1].id`). Restore.
  - Delete `tls.task_cache = (task, serial)`: nothing fails — the cache is an optimisation over the locked lookup; say so in the commit body.
  - Replace the `if "asyncio" not in sys.modules: return None` gate with `import asyncio` at the top of the module: `test_recorder_does_not_import_asyncio…` fails. Restore.
  - In `HOSTILE_TASK` handling, remove the `try/except` around `task.get_name()`: `test_a_task_whose_get_name_raises…` fails (the program dies inside a monitoring callback). Restore.

- [ ] **Step 8: Commit**

```bash
git add src/sensorium/record/tracer.py src/sensorium/record/boot.py tests/test_async.py tests/test_boot_cli.py
git commit -m "feat(record): stamp every event with a minted asyncio task serial"
```

---

### Task 5: `--focus` on coroutine-only code warns at record time

**Files:**
- Modify: `src/sensorium/record/tracer.py` — `FocusSpec` (`:173-190`), `Tracer.__init__`, `_decide`, add `unframed_focus()`
- Modify: `src/sensorium/record/boot.py` — `run_target` finally block, `_finalize_meta`
- Test: `tests/test_focus.py`, `tests/test_boot_cli.py`

**Interfaces:**
- Produces: `FocusSpec.entries_matching(module, qualname) -> list[str]` (the entry strings as given, e.g. `"main:worker"`); `Tracer.unframed_focus() -> list[str]` — focus entries that matched ≥1 code object and **only** frameless ones; `meta["focus_unframed"]: list[str]`; stderr line from `sensorium run`.
- Spec: honesty rule 2, corpus case 5.

- [ ] **Step 1: Failing tests**

Append to `tests/test_focus.py` (check its imports: it uses `record_inproc`/`record_inproc_full`; add `from sensorium.record.tracer import FocusSpec` if missing):

```python
def test_focusspec_reports_which_entries_matched():
    fs = FocusSpec(["main:worker", "main", "other:x"])
    assert fs.entries_matching("main", "worker") == ["main:worker", "main"]
    assert fs.entries_matching("main", "step") == ["main"]
    assert fs.entries_matching("other", "y") == []


ASYNC_FOCUS = """
import asyncio

def step(n):
    return n

async def worker():
    step(1)
    await asyncio.sleep(0)
    return step(2)

def main():
    return asyncio.run(worker())
"""


def test_focus_that_matched_only_coroutine_code_is_reported(tmp_path):
    from tests.helpers import record_inproc_full
    t, err, tracer = record_inproc_full(tmp_path, ASYNC_FOCUS,
                                        focus=["prog:worker", "prog:step"])
    assert err is None
    assert tracer.unframed_focus() == ["prog:worker"]      # step is framed
    assert t.counts().get("LINE", 0) > 0                   # step's lines


def test_focus_entry_that_matched_framed_and_unframed_code_is_not_reported(
        tmp_path):
    """A module-wide entry matched worker (frameless) AND step (framed): it
    did capture lines, so it is not "only coroutine code" and must not warn."""
    from tests.helpers import record_inproc_full
    t, err, tracer = record_inproc_full(tmp_path, ASYNC_FOCUS, focus=["prog"])
    assert err is None
    assert tracer.unframed_focus() == []
    assert t.counts().get("LINE", 0) > 0
```

Append to `tests/test_boot_cli.py`:

```python
ASYNC_FOCUS_SCRIPT = """
import asyncio

async def worker():
    await asyncio.sleep(0)
    return 1

def main():
    return asyncio.run(worker())

if __name__ == "__main__":
    main()
"""


def test_run_warns_when_focus_matched_only_coroutine_code(tmp_path):
    run_id, trace, r = record_script(tmp_path, ASYNC_FOCUS_SCRIPT,
                                     extra=["--focus", "prog:worker"])
    assert run_id, r.stderr
    assert "--focus prog:worker matched only coroutine/generator code" in r.stderr
    assert "opens no frame in this version" in r.stderr
    from sensorium.store.reader import Trace
    assert Trace.open(trace).meta["focus_unframed"] == ["prog:worker"]


def test_run_does_not_warn_when_focus_matched_framed_code(tmp_path):
    run_id, trace, r = record_script(
        tmp_path, "def f():\n    return 1\n\ndef main():\n    f()\nmain()\n",
        extra=["--focus", "prog:f"])
    assert run_id, r.stderr
    assert "matched only coroutine" not in r.stderr
    from sensorium.store.reader import Trace
    assert Trace.open(trace).meta["focus_unframed"] == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY -m pytest tests/test_focus.py tests/test_boot_cli.py -q` → the four new tests FAIL (`entries_matching`/`unframed_focus` missing, no stderr line, KeyError).

- [ ] **Step 3: Implement**

`FocusSpec` — keep the original strings and add the method:

```python
class FocusSpec:
    def __init__(self, entries: list[str]) -> None:
        self._entries = []
        for e in entries:
            mod, _, qual = e.partition(":")
            self._entries.append((e, mod, qual or None))

    def __bool__(self) -> bool:
        return bool(self._entries)

    def _hit(self, mod, qual, module, qualname) -> bool:
        if module != mod:
            return False
        return qual is None or qualname == qual or qualname.startswith(qual + ".")

    def matches(self, module: str | None, qualname: str) -> bool:
        if module is None:
            return False
        return any(self._hit(m, q, module, qualname) for _e, m, q in self._entries)

    def entries_matching(self, module: str | None, qualname: str) -> list[str]:
        """Every entry, as the user wrote it, that this code satisfies."""
        if module is None:
            return []
        return [e for e, m, q in self._entries if self._hit(m, q, module, qualname)]
```

`Tracer.__init__`: `self._focus_hits: dict[str, set] = {}   # entry -> {frameless flags of matched codes}`. In `_decide`, where `focused = self.focus.matches(module, code.co_qualname)` is computed, add right after `frameless = ...`:

```python
        if focused:
            for entry in self.focus.entries_matching(module, code.co_qualname):
                self._focus_hits.setdefault(entry, set()).add(frameless)
```

(`_decide` is cached per code object, so this runs once per code, not per event.) Add:

```python
    def unframed_focus(self) -> list[str]:
        """Focus entries that matched code, all of it frameless -- so no LINE
        was ever possible for them. Reported at the end of the run because
        the recorder learns a code object's kind only when it first starts."""
        return [e for e, flags in self._focus_hits.items() if flags == {True}]
```

`boot.run_target` — in the `finally`, after `gaps = _recording_gaps(...)` printing, add:

```python
            for entry in tracer.unframed_focus():
                print(f"sensorium: --focus {entry} matched only coroutine/"
                      "generator code, which opens no frame in this version; "
                      "no line-level capture was recorded for it, and `watch` "
                      "against it will report NOTHING WAS CHECKED.",
                      file=sys.stderr)
```

`_finalize_meta` gains `focus_unframed` → `w.set_meta_final("focus_unframed", focus_unframed)`; `run_target` passes `focus_unframed=tracer.unframed_focus()`.

- [ ] **Step 4: Run**

Run: `$PY -m pytest tests/test_focus.py tests/test_boot_cli.py -q` → pass; full suite + corpus green.

- [ ] **Step 5: Mutation check** — in `unframed_focus` change `flags == {True}` to `True in flags`: `test_focus_entry_that_matched_framed_and_unframed_code_is_not_reported` fails (`["prog"]` is reported). Restore. Then in `boot.run_target` delete the warning loop: `test_run_warns_when_focus_matched_only_coroutine_code` fails. Restore.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/record/tracer.py src/sensorium/record/boot.py tests/test_focus.py tests/test_boot_cli.py
git commit -m "feat(record): say at record time when --focus matched only unframed code"
```

---

### Task 6: `tree` — task groups, unframed calls, real callers, footers

**Files:**
- Modify: `src/sensorium/query/tree_cmd.py` (whole file; keep `add_parser`, `frame_line` signature, `render_tree`'s `(lines, cut_frames)` contract, `_truncation_note`)
- Test: `tests/test_tree_frame.py`, `tests/test_format1_fixture.py`

**Interfaces:**
- Produces (used by Task 7's `frame` children listing): `frame_line(trace, frame) -> str` (now with a `  <- QUAL (unframed)` tag when `parent_id is None` and the CALL payload has `caller_code`); `unframed_kind(ev) -> str`; `unframed_line(trace, ev) -> str`; `index_unframed(trace) -> (by_parent_frame: dict[int, list[Event]], parentless: list[Event])`; `render_tree(trace, roots, depth_limit, max_lines, unframed_by_parent=None) -> (lines, cut_frames, cut_unframed)`; `_truncation_note(run_ref, depth, limit, cut_frames, cut_unframed=()) -> str | None`; `task_label(trace, task_id) -> str`.
- Spec D3 `tree`, honesty rules 1, 3, 4.

Output contract (sync trace with no unframed calls and no tasks: **identical to v1**). Otherwise:

```
outside any event loop
  f1 e1 <module>() -> None
task t1: Task-1
  e2 main()  [coroutine, unframed]
task t2: task-A
  e3 worker(name='A', delay=0.01)  [coroutine, unframed]
    f2 e4 step(task='A', n=1) -> 'A:1'  <- worker (unframed)
    f4 e9 step(task='A', n=2) -> 'A:2'  <- worker (unframed)
    f6 e13 step(task='A', n=3) -> 'A:3'  <- worker (unframed)
task t3: task-B
  ...
order between tasks is wall-clock (event ids), not causal; within one task it is causal
4 unframed call(s) shown as events: coroutine/generator code opens no frame in this version (no tree, frame, focus or watch inside them)
```

Rules: items are grouped by the task of their CALL event; **group headers print only when the trace has tasks** (a sync trace has one unlabelled group, so its output is v1's); a group's items are its root frames and its parentless unframed calls, in event order; a root frame whose CALL payload carries `caller_code` is indented one level deeper than a plain root and tagged; an unframed call with `parent_frame` renders as a child of that frame (merged with framed children by event id); `--limit` is one budget across the whole output, as in v1, and unframed lines it withholds are counted in the truncation note; `--root`/`--around` subtree rendering includes unframed children; format-1 adds the `parentage: ASSUMED -- …` footer; a trace with tasks or unframed calls prints the "order between tasks" / "N unframed call(s)" footers that apply.

- [ ] **Step 1: Failing tests**

Append to `tests/test_tree_frame.py`:

```python
ASYNC_SRC = """
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

if __name__ == "__main__":
    asyncio.run(amain())
"""

GEN_SRC = """
def parse(s):
    return int(s)

def rows(items):
    for it in items:
        yield parse(it)

def main():
    return list(rows(["1", "2"]))

if __name__ == "__main__":
    main()
"""


def _section(out: str, header: str) -> list[str]:
    """Lines under `header` up to the next unindented line."""
    lines = out.splitlines()
    i = lines.index(header)
    body = []
    for ln in lines[i + 1:]:
        if ln and not ln.startswith(" "):
            break
        body.append(ln)
    return body


def test_tree_groups_by_task_and_names_the_real_caller(tmp_path, monkeypatch,
                                                        capsys):
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    a = "\n".join(_section(out, "task t2: task-A"))
    b = "\n".join(_section(out, "task t3: task-B"))
    assert "worker(name='A')  [coroutine, unframed]" in a
    assert a.count("<- worker (unframed)") == 2 and "task='B'" not in a
    assert b.count("<- worker (unframed)") == 2 and "task='A'" not in b
    # <module> ran before the loop existed: not placed in any task.
    assert "<module>()" in "\n".join(_section(out, "outside any event loop"))
    assert "order between tasks is wall-clock" in out


def test_tree_unframed_count_matches_the_trace(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    from sensorium import paths
    from sensorium.store.reader import Trace
    n = len(Trace.open(paths.find_trace(run_id)).unframed_calls())
    assert cli.main(["tree", run_id]) == 0
    assert f"{n} unframed call(s) shown as events" in capsys.readouterr().out


def test_tree_renders_a_generator_call_under_the_frame_that_called_it(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=GEN_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    main_ln = next(ln for ln in lines if "main()" in ln)
    gen_ln = next(ln for ln in lines if "rows(" in ln)
    assert "[generator, unframed]" in gen_ln
    indent = len(main_ln) - len(main_ln.lstrip())
    assert gen_ln.startswith(" " * (indent + 2) + "e")      # child of main
    parse_lns = [ln for ln in lines if "parse(" in ln]
    assert len(parse_lns) == 2
    assert all("<- rows (unframed)" in ln for ln in parse_lns)
    assert "outside any event loop" not in out                # no tasks: no groups
    assert "unframed call(s) shown as events" in out


def test_tree_around_an_unframed_event_says_so(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=GEN_SRC)
    from sensorium import paths
    from sensorium.store.reader import Trace
    ev, = Trace.open(paths.find_trace(run_id)).unframed_calls()
    assert cli.main(["tree", run_id, "--around", f"e{ev.id}"]) == 1
    out = capsys.readouterr().out
    assert f"e{ev.id} is an unframed CALL of rows (generator)" in out
    assert f"sensorium grep {run_id} rows" in out
```

Append to `tests/test_format1_fixture.py`:

```python
def test_tree_on_a_format1_trace_labels_parentage_assumed(installed_fixture,
                                                           capsys):
    assert cli.main(["tree", installed_fixture]) == 0
    out = capsys.readouterr().out
    assert "parentage: ASSUMED" in out and "format-1" in out
    # v1 parented every step to <module>; the tree must not PRESENT that as
    # derived, and must still show the unframed worker calls it never showed.
    assert out.count("worker(") == 2
    assert "[generator/coroutine, unframed]" in out      # kind unknown in v1
    assert "task t" not in out                             # no tasks recorded
```

- [ ] **Step 2: Run to verify they fail**

Run: `$PY -m pytest tests/test_tree_frame.py tests/test_format1_fixture.py -q`
Expected: new tests FAIL (no headers, no tags, `--around` says "no frame contains"); the pre-existing tree tests PASS.

- [ ] **Step 3: Implement**

Rewrite `src/sensorium/query/tree_cmd.py` (module docstring + `add_parser` unchanged):

```python
"""Call-tree slices: what actually ran, in what order -- and who called it.

Parentage is DERIVED on format-2 traces (the caller frame, verified by code
identity) and ASSUMED on format-1 ones (v1's last-opened-frame guess); the
footer says which. Coroutines and generators open no frame and are shown as
events in their true position: under the frame that called them when that
frame was open, otherwise at the top of their task group. A framed call whose
caller has no frame is tagged with the caller's name and never re-parented.
"""
from sensorium import paths
from sensorium.query.fmt import (fmt_args, fmt_exc, fmt_value, parse_eref,
                                 parse_fref)
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    ...unchanged...


def task_label(trace, task_id) -> str:
    if task_id is None:
        return "outside any event loop"
    t = trace.task(task_id)
    name = t.name if (t is not None and t.name is not None) else "(unnamed)"
    return f"task t{task_id}: {name}"


def _caller_tag(trace, frame) -> str:
    """`<- QUAL (unframed)` when the frame's caller is traced code that has
    no frame (a generator or coroutine body). Nothing for a true root or an
    untraced caller -- and nothing on a format-1 trace, which has no record."""
    if frame.parent_id is not None:
        return ""
    call = trace.event(frame.call_event_id)
    cc = (call.payload or {}).get("caller_code") if call else None
    if cc is None:
        return ""
    return f"  <- {trace.code(cc).qualname} (unframed)"


def frame_line(trace, frame) -> str:
    code = trace.code(frame.code_id)
    call = trace.event(frame.call_event_id)
    args = fmt_args((call.payload or {}).get("args", {})) if call else ""
    if frame.closed_by == "unwind":
        tail = (f" !! {fmt_exc(frame.unwind_exc)}" if frame.unwind_exc
                else " !! unwound")
    elif frame.return_event_id is not None:
        ret = trace.event(frame.return_event_id)
        tail = f" -> {fmt_value((ret.payload or {}).get('value'))}"
    else:
        tail = " (open)"
    return (f"f{frame.id} e{frame.call_event_id} {code.qualname}({args}){tail}"
            + _caller_tag(trace, frame))


def unframed_kind(ev) -> str:
    # Format-1 traces recorded no kind; "generator/coroutine" is all v1 knew.
    return (ev.payload or {}).get("unframed", "generator/coroutine")


def unframed_line(trace, ev) -> str:
    code = trace.code(ev.code_id)
    args = fmt_args((ev.payload or {}).get("args", {}))
    return f"e{ev.id} {code.qualname}({args})  [{unframed_kind(ev)}, unframed]"


def index_unframed(trace):
    """(by_parent_frame, parentless): every unframed call, split by whether
    its caller's frame was open. Computed once per command."""
    by_parent: dict[int, list] = {}
    parentless = []
    for ev in trace.unframed_calls():
        pf = (ev.payload or {}).get("parent_frame")
        if pf is None:
            parentless.append(ev)
        else:
            by_parent.setdefault(pf, []).append(ev)
    return by_parent, parentless


def render_tree(trace, roots, depth_limit, max_lines, unframed_by_parent=None):
    """Return (lines, cut_frames, cut_unframed): `cut_frames` is the actual
    Frame objects withheld because they crossed --depth or --limit, in
    encounter order -- never just a count. A caller that only reports the
    count and drops the frames themselves cannot point a reader at what was
    hidden. `cut_unframed` is the unframed-call events --limit withheld; they
    have no subtree, so they never cross --depth.

    Unframed calls whose caller is a frame in this subtree render as that
    frame's children, merged with the framed children by event id."""
    ubp = unframed_by_parent if unframed_by_parent is not None else {}
    lines: list[str] = []
    cut_frames: list = []
    cut_unframed: list = []

    def walk(frame, depth):
        if len(lines) >= max_lines or depth > depth_limit:
            cut_frames.append(frame)
            return
        lines.append("  " * depth + frame_line(trace, frame))
        kids = ([("f", ch.call_event_id, ch) for ch in trace.children(frame.id)]
                + [("u", ev.id, ev) for ev in ubp.get(frame.id, [])])
        kids.sort(key=lambda k: k[1])
        for kind, _eid, obj in kids:
            if kind == "f":
                walk(obj, depth + 1)
            elif len(lines) < max_lines:
                lines.append("  " * (depth + 1) + unframed_line(trace, obj))
            else:
                cut_unframed.append(obj)

    for r in roots:
        walk(r, 0)
    return lines, cut_frames, cut_unframed


def _truncation_note(run_ref, depth, limit, cut_frames,
                     cut_unframed=()) -> str | None:
    """Every branch that can withhold subtrees must report it -- silence
    here is indistinguishable from "that's the whole tree", which is
    exactly the unsupported claim this project forbids. The hint is a
    fully-instantiated, copy-pasteable command (a real frame id, the run
    ref actually in hand), not a template like "fN"."""
    parts = []
    if cut_frames:
        parts.append(f"{len(cut_frames)} subtree(s) beyond --depth {depth} or "
                     f"--limit {limit}; continue with: "
                     f"sensorium tree {run_ref} --root f{cut_frames[0].id}")
    if cut_unframed:
        parts.append(f"{len(cut_unframed)} unframed call(s) withheld by "
                     f"--limit {limit}; see them with: sensorium grep "
                     f"{run_ref} CALL")
    return ("... " + "; ".join(parts)) if parts else None


def _grouped(trace, roots, parentless):
    """Group roots and parentless unframed calls by task, in event order.
    Returns [(task_id, [(event_id, kind, obj)])] with None first."""
    groups: dict = {}
    for f in roots:
        call = trace.event(f.call_event_id)
        tid = call.task_id if call else None
        groups.setdefault(tid, []).append((f.call_event_id, "f", f))
    for ev in parentless:
        groups.setdefault(ev.task_id, []).append((ev.id, "u", ev))
    order = sorted(groups, key=lambda t: (t is not None, t or 0))
    return [(t, sorted(groups[t], key=lambda i: i[0])) for t in order]


def _has_caller_code(trace, frame) -> bool:
    call = trace.event(frame.call_event_id)
    return bool(call and (call.payload or {}).get("caller_code") is not None)


def _footers(trace, n_unframed: int) -> list[str]:
    out = []
    if trace.tasks():
        out.append("order between tasks is wall-clock (event ids), not causal; "
                   "within one task it is causal")
    if n_unframed:
        out.append(f"{n_unframed} unframed call(s) shown as events: "
                   "coroutine/generator code opens no frame in this version "
                   "(no tree, frame, focus or watch inside them)")
    if trace.parentage_basis() == "assumed":
        out.append("parentage: ASSUMED -- recorded by a format-1 sensorium, "
                   "whose parent was the last frame opened on the thread, not "
                   "the caller; async, generators and C callbacks break that. "
                   "Re-record to derive it.")
    return out


def run(args) -> int:
    if args.limit < 1:
        print(f"--limit must be >= 1 (got {args.limit}); "
              "there is no useful zero-row page")
        return 2
    if args.depth < 0:
        print(f"--depth must be >= 0 (got {args.depth}); "
              "depth 0 shows the root frames alone")
        return 2
    trace = Trace.open(paths.find_trace(args.run))
    by_parent, parentless = index_unframed(trace)
    n_unframed = sum(len(v) for v in by_parent.values()) + len(parentless)
    if args.around:
        eid = parse_eref(args.around)
        f = trace.frame_containing(eid)
        if f is None:
            ev = trace.event(eid)
            # frame_containing is None for a CALL event only when no frame
            # was opened for it: that is what "unframed" means.
            if ev is not None and ev.kind == "CALL" and ev.code_id is not None:
                q = trace.code(ev.code_id).qualname
                print(f"e{eid} is an unframed CALL of {q} ({unframed_kind(ev)}); "
                      f"no frame contains it. Its events: sensorium grep "
                      f"{args.run} {q}")
            else:
                print(f"no frame contains {args.around}")
            return 1
        chain = [f]
        while chain[-1].parent_id is not None:
            chain.append(trace.frame(chain[-1].parent_id))
        ancestors = list(reversed(chain[1:]))
        for depth, fr in enumerate(ancestors):
            print("  " * depth + frame_line(trace, fr))
        lines, cut_frames, cut_u = render_tree(trace, [f], args.depth,
                                               args.limit, by_parent)
        for ln in lines:
            print("  " * len(ancestors) + ln)
        note = _truncation_note(args.run, args.depth, args.limit, cut_frames,
                                cut_u)
        if note:
            print(note)
        for ln in _footers(trace, 0):
            print(ln)
        return 0
    if args.root:
        root = trace.frame(parse_fref(args.root))
        if root is None:
            print(f"no such frame: {args.root} does not exist")
            return 1
        lines, cut_frames, cut_u = render_tree(trace, [root], args.depth,
                                               args.limit, by_parent)
        for ln in lines:
            print(ln)
        note = _truncation_note(args.run, args.depth, args.limit, cut_frames,
                                cut_u)
        if note:
            print(note)
        for ln in _footers(trace, 0):
            print(ln)
        return 0
    # One path for every trace. A synchronous trace has no tasks, so it is
    # one unlabelled group whose roots render at indent 0 in event order --
    # byte-identical to v1 -- and --limit is one budget across the whole
    # output, as it was.
    show_headers = bool(trace.tasks())
    cut_frames_all: list = []
    cut_unframed_all: list = []
    printed = 0
    for tid, items in _grouped(trace, trace.roots(), parentless):
        if show_headers:
            print(task_label(trace, tid))
        for _eid, kind, obj in items:
            budget = args.limit - printed
            if kind == "u":
                if budget <= 0:
                    cut_unframed_all.append(obj)
                    continue
                print(("  " if show_headers else "") + unframed_line(trace, obj))
                printed += 1
                continue
            if budget <= 0:
                cut_frames_all.append(obj)
                continue
            base = (1 if show_headers else 0) + (1 if _has_caller_code(trace, obj) else 0)
            lines, cut, cut_u = render_tree(trace, [obj], args.depth, budget,
                                            by_parent)
            cut_frames_all += cut
            cut_unframed_all += cut_u
            for ln in lines:
                print("  " * base + ln)
            printed += len(lines)
    note = _truncation_note(args.run, args.depth, args.limit, cut_frames_all,
                            cut_unframed_all)
    if note:
        print(note)
    elif printed == 0:
        print("no frames recorded")
    for ln in _footers(trace, n_unframed):
        print(ln)
    return 0
```

- [ ] **Step 4: Run**

Run: `$PY -m pytest tests/test_tree_frame.py tests/test_format1_fixture.py -q` → pass. Full suite + corpus green. Then eyeball: `$PY -m sensorium run -- tests/fixtures/format1_async.py && $PY -m sensorium tree last` — matches the output contract above.

- [ ] **Step 5: Mutation checks**
  - In `_caller_tag` return `""` always: `…names_the_real_caller` and the generator test fail.
  - In `_grouped`, drop the `parentless` loop: the unframed count test still passes (count is computed separately) — so in `test_tree_groups_by_task…` the `worker(name='A')  [coroutine, unframed]` assertion fails. Good.
  - In `_footers`, drop the ASSUMED line: fixture test fails. Restore all.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/tree_cmd.py tests/test_tree_frame.py tests/test_format1_fixture.py
git commit -m "feat(tree): group by task, show unframed calls, name real callers, label assumed parentage"
```

---

### Task 7: `frame` — three answers for `--fn`, task in the header

**Files:**
- Modify: `src/sensorium/query/frame_cmd.py:18-41` (`_resolve`), `:44-84` (`run`)
- Test: `tests/test_tree_frame.py`, `tests/test_format1_fixture.py`

**Interfaces:**
- Produces: `_resolve(trace, args) -> (frame | None, error | None)`; error text for the unframed case: `'{fn}' was recorded as {N} call(s) but not framed ({kind}): no frame, locals or children to show; its events: sensorium grep {run} {fn}`; header gains `  task t{id} ({name})` when the CALL event has a task; format-1 header line `parentage: assumed (format-1 trace)`.
- Consumes: Task 2 `unframed_calls`, `task`; Task 6 `unframed_kind`, `frame_line`.

- [ ] **Step 1: Failing tests**

Append to `tests/test_tree_frame.py`:

```python
def test_frame_fn_distinguishes_unframed_from_never_recorded(tmp_path,
                                                              monkeypatch,
                                                              capsys):
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["frame", run_id, "--fn", "worker"]) == 1
    out = capsys.readouterr().out
    assert "'worker' was recorded as 2 call(s) but not framed (coroutine)" in out
    assert f"sensorium grep {run_id} worker" in out
    assert "no recorded activations" not in out
    assert cli.main(["frame", run_id, "--fn", "nope"]) == 1
    assert "no recorded activations of 'nope'" in capsys.readouterr().out


def test_frame_header_names_the_task(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["frame", run_id, "--fn", "step", "--nth", "1"]) == 0
    head = capsys.readouterr().out.splitlines()[0]
    assert "task t2 (task-A)" in head and "depth 0" in head
```

Append to `tests/test_format1_fixture.py`:

```python
def test_frame_on_a_format1_trace_says_unframed_and_assumed(installed_fixture,
                                                             capsys):
    assert cli.main(["frame", installed_fixture, "--fn", "worker"]) == 1
    out = capsys.readouterr().out
    assert "recorded as 2 call(s) but not framed (generator/coroutine)" in out
    assert cli.main(["frame", installed_fixture, "--fn", "step"]) == 0
    out = capsys.readouterr().out
    assert "parentage: assumed (format-1 trace)" in out
    assert "task t" not in out.splitlines()[0]
```

- [ ] **Step 2: Run to verify they fail** — `$PY -m pytest tests/test_tree_frame.py tests/test_format1_fixture.py -q`: the three new FAIL.

- [ ] **Step 3: Implement**

In `frame_cmd.py`, import `unframed_kind` alongside `frame_line`, and replace the `--fn` branch of `_resolve`:

```python
    if args.fn:
        matches = [f for f in trace.frames()
                   if trace.code(f.code_id).qualname == args.fn]
        if not matches:
            codes = [c for c in trace.codes() if c.qualname == args.fn]
            calls = [e for c in codes for e in trace.unframed_calls(code_id=c.id)]
            if calls:
                # Recorded, not framed: the activations are in the trace,
                # as CALL events -- denying them contradicts `grep` on the
                # same trace, which is what v1 did.
                return None, (
                    f"{args.fn!r} was recorded as {len(calls)} call(s) but "
                    f"not framed ({unframed_kind(calls[0])}): no frame, locals "
                    "or children to show; its events: sensorium grep "
                    f"{args.run} {args.fn}")
            return None, ("no such frame: no recorded activations of "
                          f"{args.fn!r}")
```

In `run`, build the header with the task:

```python
    call = trace.event(f.call_event_id)
    task = ""
    if call is not None and call.task_id is not None:
        t = trace.task(call.task_id)
        name = t.name if (t is not None and t.name is not None) else "unnamed"
        task = f"  task t{call.task_id} ({name})"
    print(f"f{f.id} {code.file.rsplit('/', 1)[-1]}:{code.qualname}  "
          f"[e{f.call_event_id}..{end}]  thread {f.thread_id}{task}  "
          f"depth {f.depth}  closed: {f.closed_by or 'open'}")
    if trace.parentage_basis() == "assumed":
        print("parentage: assumed (format-1 trace) -- depth and the parent "
              "chain are v1's last-opened-frame guess")
```

(Move the existing `call = trace.event(f.call_event_id)` line up so it is not fetched twice.)

- [ ] **Step 4: Run** — the two files, then full suite + corpus: green.

- [ ] **Step 5: Mutation check** — in `_resolve` replace `if calls:` with `if False:`: the unframed tests fail. Restore.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/frame_cmd.py tests/test_tree_frame.py tests/test_format1_fixture.py
git commit -m "fix(frame): say 'recorded but not framed' instead of denying the activation"
```

---

### Task 8: `info` — unframed count, tasks, call-based hot list

**Files:**
- Modify: `src/sensorium/query/info_cmd.py:74-148` (`run`)
- Test: `tests/test_runs_info.py`, `tests/test_format1_fixture.py`

**Interfaces:**
- Produces lines: `unframed calls: N (coroutine 2, generator 1)` (always printed; `unframed calls: 0` on a sync trace); `tasks: N (t1 Task-1, t2 task-A, …)` on format 2 with tasks, `tasks: none (no running event loop was seen)` on format 2 without, `tasks: not recorded (format-1 trace; parentage assumed)` on format 1; `task identity errors: N -- …` only when non-zero; `hot functions:` now counts CALL events (`trace.call_counts()`), so `worker`/`main` appear.

- [ ] **Step 1: Failing tests**

Append to `tests/test_runs_info.py`:

```python
ASYNC_SRC = """
import asyncio

def step(n):
    return n

async def worker():
    step(1)
    await asyncio.sleep(0)
    return step(2)

async def amain():
    await asyncio.gather(asyncio.create_task(worker(), name="w1"),
                         asyncio.create_task(worker(), name="w2"))

if __name__ == "__main__":
    asyncio.run(amain())
"""


def test_info_counts_unframed_calls_and_lists_tasks(tmp_path, monkeypatch,
                                                     capsys):
    run_id, trace, r = record_script(tmp_path, ASYNC_SRC)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "unframed calls: 3 (coroutine 3)" in out        # amain + 2 worker
    assert "tasks: 3 (" in out and "w1" in out and "w2" in out
    assert "2x prog.py:worker" in out                      # calls, not frames
    assert "task identity errors" not in out


def test_info_on_a_sync_trace_says_zero_unframed_and_no_loop(tmp_path,
                                                             monkeypatch,
                                                             capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "unframed calls: 0" in out
    assert "tasks: none (no running event loop was seen)" in out
```

Append to `tests/test_format1_fixture.py`:

```python
def test_info_on_a_format1_trace_says_tasks_not_recorded(installed_fixture,
                                                          capsys):
    assert cli.main(["info", installed_fixture]) == 0
    out = capsys.readouterr().out
    assert "tasks: not recorded (format-1 trace; parentage assumed)" in out
    assert "unframed calls: 3 (generator/coroutine 3)" in out
    assert "2x format1_async.py:worker" in out
```

- [ ] **Step 2: Run to verify they fail** — the three FAIL.

- [ ] **Step 3: Implement**

In `info_cmd.run`, after the `print("recorded: " …)` line:

```python
    unframed = t.unframed_calls()
    kinds: dict[str, int] = {}
    for ev in unframed:
        k = (ev.payload or {}).get("unframed", "generator/coroutine")
        kinds[k] = kinds.get(k, 0) + 1
    detail = ", ".join(f"{k} {n}" for k, n in sorted(kinds.items()))
    print(f"unframed calls: {len(unframed)}" + (f" ({detail})" if detail else ""))
    if t.format < 2:
        print("tasks: not recorded (format-1 trace; parentage assumed)")
    elif t.tasks():
        names = ", ".join(f"t{k.id} {k.name if k.name is not None else '(unnamed)'}"
                          for k in t.tasks())
        print(f"tasks: {len(t.tasks())} ({names})")
    else:
        print("tasks: none (no running event loop was seen)")
    task_errors = m.get("task_errors", 0)
    if task_errors:
        print(f"task identity errors: {task_errors} -- a task object broke the "
              "lookup (hostile get_name/__hash__); those events carry no task")
```

Replace the hot-functions block:

```python
    counts_by_code = t.call_counts()
    hot = sorted(((c, counts_by_code.get(c.id, 0)) for c in t.codes()),
                 key=lambda x: -x[1])[:8]
```

(keep the printing loop as is).

- [ ] **Step 4: Run** — the three files, full suite, corpus: green.

- [ ] **Step 5: Mutation check** — revert `call_counts` to `len(t.frames(code_id=c.id))`: `2x prog.py:worker` assertion fails. Restore.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/info_cmd.py tests/test_runs_info.py tests/test_format1_fixture.py
git commit -m "feat(info): count unframed calls, list tasks, count calls not frames"
```

---

### Task 9: `watch` — the real reason, not a misspelling

**Files:**
- Modify: `src/sensorium/query/watch_cmd.py:274-300` (`print_never_recorded`), `:444-502` (`run`), add `unframed_note`
- Test: `tests/test_watch.py`

**Interfaces:**
- Produces: `unframed_note(trace, codes) -> list[str]`; `print_never_recorded(ghosts, all_unframed: bool = False)`. When every `--at`-matched code is unframed, the NEVER RECORDED block names the real reason and does not offer a refocus.
- Spec honesty rule 2, corpus case 5.

- [ ] **Step 1: Failing test**

Append to `tests/test_watch.py` (uses `record_script` + `cli.main`; match the file's existing helper pattern — it has `_rec`-style helpers; if not, inline `record_script` + `monkeypatch.setenv("SENSORIUM_DIR", …)` as in test_runs_info):

```python
ASYNC_WATCH = """
import asyncio

async def worker(name):
    await asyncio.sleep(0)
    return name

def main():
    return asyncio.run(worker("A"))

if __name__ == "__main__":
    main()
"""


def test_watch_names_unframed_code_as_the_reason_not_a_misspelling(
        tmp_path, monkeypatch, capsys):
    run_id, trace, r = record_script(tmp_path, ASYNC_WATCH,
                                     extra=["--focus", "prog:worker"])
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["watch", run_id, "--at", "prog:worker",
                     "--expr", "name == 'A'"]) == 0
    out = capsys.readouterr().out
    assert "NOTHING WAS CHECKED" in out
    assert "opens no frame in this version" in out
    assert "watch sites are frames" in out
    assert "misspelled" not in out
    assert "refocus and re-run" not in out       # re-recording cannot help
```

- [ ] **Step 2: Run to verify it fails** — FAIL on `"misspelled" not in out`.

- [ ] **Step 3: Implement**

Add after `refocus_cmd`:

```python
def unframed_note(trace, codes) -> list[str]:
    """Which of the `--at` matches are coroutine/generator code -- recorded
    as calls, never framed, so they contribute NO site. Returned as
    (lines, all_unframed) would be two things; callers get the lines and
    test `all_unframed_codes` separately."""
    unf = [c for c in codes
           if trace.unframed_calls(code_id=c.id) and not trace.frames(code_id=c.id)]
    if not unf:
        return []
    names = ", ".join(c.qualname for c in unf)
    if len(unf) == len(codes):
        return [f"--at matched only coroutine/generator code ({names}), which "
                "opens no frame in this version: watch sites are frames, so "
                "there are no sites here at all, and refocusing cannot change "
                "that"]
    return [f"{len(unf)} of the {len(codes)} matched code object(s) ({names}) "
            "are coroutine/generator code: recorded as calls, never framed, "
            "and contributed no site"]


def all_unframed_codes(trace, codes) -> bool:
    return bool(codes) and all(
        trace.unframed_calls(code_id=c.id) and not trace.frames(code_id=c.id)
        for c in codes)
```

Change `print_never_recorded`:

```python
def print_never_recorded(ghosts: list[str], all_unframed: bool = False) -> None:
    ...docstring unchanged...
    if not ghosts:
        return
    names = ", ".join(repr(g) for g in ghosts)
    print(f"NEVER RECORDED: {names} -- named by the predicate, captured at NO "
          "site in these frames")
    print("  every result below was decided WITHOUT it: nothing in this trace "
          "witnesses that name")
    if all_unframed:
        print("  there are no frames here at all: --at matched only "
              "coroutine/generator code, which opens no frame in this version "
              "(see the line above the verdict)")
    else:
        print("  either it is misspelled, or it lives in frames this run did "
              "not record")
```

In `run`, replace the existing `print_never_recorded(ghosts)` call (just below the optional `--after` line) with:

```python
    for line in unframed_note(trace, codes):
        print(line)
    all_unf = all_unframed_codes(trace, codes)
    # Above the verdict on purpose: the verdict cannot be read without it.
    print_never_recorded(ghosts, all_unf)
```

and change the later call to `print_unavailable(trace, out, sites, ever, codes, n, all_unf)`.

Signatures, exactly: `def print_unavailable(trace, out: Outcome, sites, ever, codes, n_sites: int, all_unframed: bool = False) -> None` passes `all_unframed` as the last positional argument of `_guidance(reason, name, name in ever, has_line, trace, codes, all_unframed)`; `def _guidance(reason: str, name: str, ever: bool, has_line: bool, trace, codes, all_unframed: bool = False) -> list[str]` whose `not has_line` branch becomes:

```python
    if not has_line:
        if all_unframed:
            return ["no site exists for these code objects: coroutine/"
                    "generator code opens no frame in this version"]
        return ["no local of these frames was recorded at all -- line capture "
                "is opt-in at record time",
                "refocus and re-run: " + refocus_cmd(trace, codes)]
```

- [ ] **Step 4: Run** — `tests/test_watch.py tests/test_watch_verdict.py`, full suite, corpus: green.

- [ ] **Step 5: Mutation check** — in `run`, call `print_never_recorded(ghosts)` without `all_unf`: the test fails on `"misspelled" not in out`. Restore.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/watch_cmd.py tests/test_watch.py
git commit -m "fix(watch): name unframed code as the reason, never a misspelling"
```

---

### Task 10: Corpus cases — pre-registered questions

**Files:**
- Create: `corpus/async_interleaved/main.py`, `corpus/async_interleaved/questions.yaml`
- Create: `corpus/unframed_callers/main.py`, `corpus/unframed_callers/questions.yaml`
- Create: `corpus/async_cancelled/main.py`, `corpus/async_cancelled/questions.yaml`
- Create: `corpus/async_focus/main.py`, `corpus/async_focus/questions.yaml`
- Modify: `tests/test_corpus.py:71` (`assert len(cases) >= 11` → `>= 15`)

Write every `questions.yaml` **before** running a single command against its program. Then run `$PY corpus/run_corpus.py --only <case>`; a failure means either the tool is wrong (fix the tool) or the expectation is genuinely mis-registered (fix it and say so in the commit body — never loosen to make it pass).

- [ ] **Step 1: `async_interleaved`**

`corpus/async_interleaved/main.py`:

```python
"""Seeded bug: two tasks write the same key of a shared store, so the
second writer silently overwrites the first. The output looks fine -- a value
is there -- it is just the wrong task's. The order is made deterministic with
an Event, so the final value is always B's.

The only framed code inside the tasks is the sync helper `update`; the
coroutine bodies are unframed. v1 parented every `update` to `<module>` and
recorded no task at all, so the question "which task made the final write?"
had no answer in the trace.
"""
import asyncio

STORE = {}


def update(key, value):
    STORE[key] = value
    return STORE[key]


async def writer(name, wait_for, signal):
    update("result", f"{name}:1")
    if wait_for is not None:
        await wait_for.wait()
    else:
        await asyncio.sleep(0)
    update("result", f"{name}:2")            # BUG: same key as the other task
    if signal is not None:
        signal.set()


async def main():
    a_done = asyncio.Event()
    a = asyncio.create_task(writer("A", None, a_done), name="task-A")
    b = asyncio.create_task(writer("B", a_done, None), name="task-B")
    await asyncio.gather(a, b)
    print(f"result: {STORE['result']}")


if __name__ == "__main__":
    asyncio.run(main())
```

`corpus/async_interleaved/questions.yaml`:

```yaml
program: main.py
questions:
  - id: which-task-wrote-last
    ask: >
      The final value is "B:2" and I expected "A:2". Which task made the
      write that won, and did task A's second write happen at all?
    truth: >
      Both tasks wrote "result"; the order was A:1, B:1, A:2, B:2, and the
      last write was update(key='result', value='B:2') in task-B. Task A's
      second write happened (A:2) and was overwritten. The four `update`
      activations are real frames whose caller is the coroutine `writer`,
      which has no frame: they belong to a task group and are tagged with
      the caller's name, never re-parented to <module>.
    why_logs_fail: >
      A print inside update shows four writes and their values, in order,
      but not which task each came from: the helper has no idea what task
      it is running in, and adding that means threading the task name
      through every call or calling asyncio.current_task() inside the
      helper -- the instrumentation nobody writes until they already
      suspect the interleaving, which is the thing being asked.
    command: ["tree", "$RUN"]
    expect_contains:
      - "task t2: task-A"
      - "task t3: task-B"
      - "order between tasks is wall-clock"
    expect_line:
      - ["update(key='result', value='B:2')", "<- writer (unframed)"]
      - ["update(key='result', value='A:2')", "<- writer (unframed)"]
      - ["writer(name='B'", "[coroutine, unframed]"]
    expect_count: {"<- writer (unframed)": 4}
  - id: the-winning-frame-names-its-task
    ask: Which task does the fourth (last) update activation belong to?
    truth: >
      The fourth update frame -- the B:2 write -- ran in task t3 (task-B),
      at depth 0 because its caller opened no frame.
    why_logs_fail: >
      There is no log line that records the asyncio task an ordinary
      function ran in; the task is a property of the execution, not of the
      code, and a print shows only what the code was told to print.
    command: ["frame", "$RUN", "--fn", "update", "--nth", "4"]
    expect_line:
      - ["f", "update", "task t3 (task-B)", "depth 0"]
      - ["args:", "value='B:2'"]
```

- [ ] **Step 2: `unframed_callers`**

`corpus/unframed_callers/main.py`:

```python
"""Two parentage shapes that have nothing to do with asyncio.

A generator body calling a helper: v1 parented the helper to the CONSUMER's
frame (the last one opened on the thread), which is not who called it. And a
key function called back from C-level sorted(): its real caller is the frame
that called sorted, which v1 also said -- by the accident of stack discipline
holding for C callbacks. Both are pinned so the fix is seen to be about the
caller frame, not about coroutines.

Seeded bug: the key function ranks by the wrong field, so the longest name
sorts first instead of the highest score.
"""


def parse(s):
    return int(s)


def rows(items):
    for it in items:
        yield parse(it)


def rank(rec):
    return len(rec[0])          # BUG: should be rec[1]


def main():
    total = sum(rows(["10", "20", "30"]))
    best = sorted([("al", 9), ("bea", 3)], key=rank, reverse=True)[0]
    print(f"total: {total}  best: {best[0]}")


if __name__ == "__main__":
    main()
```

`corpus/unframed_callers/questions.yaml`:

```yaml
program: main.py
questions:
  - id: who-called-parse
    ask: >
      parse ran three times. Who called it -- main, which consumed the
      generator, or the generator body?
    truth: >
      The generator `rows` called parse every time; rows is frameless, so
      each parse frame has no parent and is tagged "<- rows (unframed)".
      The rows() call itself appears as an unframed event under main's
      frame, which is the frame that was open when it was called.
    why_logs_fail: >
      A print in parse proves it ran and what it got, not whose line called
      it; the fact being asked is the shape of the call, and a log entry is
      written by the callee with no view of its caller unless it prints the
      whole stack, which is the thing you do only once you suspect the
      generator.
    command: ["tree", "$RUN"]
    expect_line:
      - ["rows(", "[generator, unframed]"]
      - ["parse(s='10')", "<- rows (unframed)"]
    expect_count: {"<- rows (unframed)": 3}
    expect_absent: ["task t"]
  - id: key-fn-is-a-child-of-main
    ask: >
      rank was called from inside sorted(), which is C. Does the trace
      parent it to main, and what did it return for each record?
    truth: >
      rank's two frames are children of main's frame (the frame that called
      sorted), returning 2 for ("al", 9) and 3 for ("bea", 3) -- the bug is
      that it ranked by name length, which is why "bea" won.
    why_logs_fail: >
      A print inside rank shows the two return values; it cannot show that
      the calls were made from main's sorted() line rather than from
      anywhere else, because the C frame between them leaves no Python
      line to print.
    command: ["tree", "$RUN"]
    expect_line:
      - ["rank(rec=('al', 9))", "-> 2"]
      - ["rank(rec=('bea', 3))", "-> 3"]
    expect_absent: ["<- main"]
```

(`expect_absent: ["<- main"]` pins that rank is a real child, not a tagged orphan.)

- [ ] **Step 3: `async_cancelled`**

`corpus/async_cancelled/main.py`:

```python
"""Seeded bug: a task is cancelled while suspended and its second step never
runs; the program prints a total that silently omits it. The cancelled task's
coroutine is unframed, so arc 1 records its CALL and its first step, and --
honestly -- no RETURN, no frame, no closed_by.

This case also pins what arc 1 does NOT claim about an abandoned task, so
that arc 2 (coroutine frames with an ABANDONED state) has a failing case to
turn into a working one.
"""
import asyncio

TOTAL = []


def step(name, n):
    TOTAL.append(n)
    return n


async def worker(name, delay):
    step(name, 1)
    await asyncio.sleep(delay)
    return step(name, 2)


async def main():
    a = asyncio.create_task(worker("A", 0), name="task-A")
    b = asyncio.create_task(worker("B", 10), name="task-B")
    await a
    b.cancel()                       # BUG: B never gets to its second step
    try:
        await b
    except asyncio.CancelledError:
        pass
    print(f"total: {sum(TOTAL)}")


if __name__ == "__main__":
    asyncio.run(main())
```

`corpus/async_cancelled/questions.yaml`:

```yaml
program: main.py
questions:
  - id: did-b-finish
    ask: The total is 4, not 6. Did task B's second step ever run?
    truth: >
      No. task-B's group holds the unframed worker call and exactly one
      step (n=1); task-A's holds two. worker returned once (task A) --
      the second worker call has no RETURN, because the task was cancelled
      while suspended, and the trace says nothing more than that about it:
      no frame, no closed_by, no "abandoned" label (that is arc 2).
    why_logs_fail: >
      A print at the end of worker would fire once and you would read the
      total and the single line and still not know whether the second
      task was never started, was started and cancelled, or raised --
      absence of a log line is not a record of what happened instead.
    command: ["tree", "$RUN"]
    expect_line:
      - ["task t3: task-B"]
      - ["worker(name='B'", "[coroutine, unframed]"]
      - ["step(name='A', n=2)", "<- worker (unframed)"]
    expect_count: {"step(name='B'": 1, "step(name='A'": 2}
  - id: one-return-for-two-calls
    ask: How many times did worker return?
    truth: Once -- the A task; B's second activation never returned.
    why_logs_fail: >
      A return-value print shows one line; a reader cannot tell one line
      from "the other task returned before the print was added" without
      the call count beside it, which the trace has and the log does not.
    command: ["grep", "$RUN", "worker"]
    expect_line:
      - ["CALL", "worker(name='A'"]
      - ["CALL", "worker(name='B'"]
      - ["RETURN", "worker -> 2"]
    expect_count: {"RETURN": 1}
```

- [ ] **Step 4: `async_focus`**

`corpus/async_focus/main.py`:

```python
"""Honesty rule 2: a --focus on a coroutine is accepted, captures no line,
and `watch` must explain why with the real reason -- the code opens no
frame in this version -- not with "misspelled" or "frames this run did not
record". `name` is right there in the CALL payload.
"""
import asyncio


async def worker(name):
    visible = len(name)
    await asyncio.sleep(0)
    return visible


if __name__ == "__main__":
    print(asyncio.run(worker("A")))
```

`corpus/async_focus/questions.yaml`:

```yaml
program: main.py
record:
  focus: ["main:worker"]
questions:
  - id: watch-says-why
    ask: >
      I focused worker and asked whether name == 'A' held. Nothing was
      checked -- why, and will refocusing help?
    truth: >
      worker is a coroutine: it opens no frame in this version, so there
      are no sites at all, and refocusing cannot change that. The verdict
      is NOTHING WAS CHECKED, and the reason given must be that one -- not
      a misspelling (name IS a recorded argument of worker) and not "frames
      this run did not record" (worker's calls were recorded).
    why_logs_fail: >
      This is a question about the instrument, not the program: whether a
      silence means the invariant held, the check could not run, or the
      check could never run here. A log line can be present or absent; it
      cannot say which of those its absence is.
    command: ["watch", "$RUN", "--at", "main:worker", "--expr", "name == 'A'"]
    expect_contains:
      - "NOTHING WAS CHECKED"
      - "opens no frame in this version"
      - "sites: 0"
    expect_absent:
      - "misspelled"
      - "refocus and re-run"
```

- [ ] **Step 5: Bump the count in `tests/test_corpus.py`** — `assert len(cases) >= 11` → `>= 15`.

- [ ] **Step 6: Run each case, then everything**

```bash
for c in async_interleaved unframed_callers async_cancelled async_focus; do
  $PY corpus/run_corpus.py --only $c || break
done
$PY corpus/run_corpus.py
$PY -m pytest -q -x
```

Expected: every case `0 failures`. If a case fails, read the `got:` excerpt: decide **which** of (tool, expectation) is wrong, fix that, and record the decision in the commit body.

- [ ] **Step 7: Commit**

```bash
git add corpus/async_interleaved corpus/unframed_callers corpus/async_cancelled corpus/async_focus tests/test_corpus.py
git commit -m "test(corpus): pre-registered async attribution cases (interleaved, unframed callers, cancelled, focus)"
```

---

### Task 11: Bench — measure the async path, report it

**Files:**
- Modify: `corpus/_bench/bench.py` (`WORKLOADS`)
- Test: `tests/test_bench.py` (existing tests monkeypatch `WORKLOADS`; nothing to add unless the structure changes)

- [ ] **Step 1: Add the workload**

Open `corpus/_bench/bench.py`, find `WORKLOADS = {` and add a third entry whose source is:

```python
ASYNC_CALL_DENSE = '''
import asyncio

def leaf(n):
    return n

async def work():
    for i in range(20000):
        leaf(i)

asyncio.run(work())
'''
```

registered as `"async_call_dense": (ASYNC_CALL_DENSE, None)`, with a comment: `# every event inside a running loop: measures the task-identity path (sys.modules probe + _get_running_loop + current_task + serial lookup) on top of derived parentage.` Also add the paragraph to the module docstring's "WHY TWO WORKLOADS" section, renaming it "WHY THREE WORKLOADS": the third one exists because the async path costs more per event than the sync path, and reporting only sync rows would under-state it.

- [ ] **Step 2: Run the bench and keep the numbers**

Measure v1 from a throwaway worktree (never by checking old files into the working tree), then arc 1 from the branch:

```bash
$PY -m pytest tests/test_bench.py -q
git worktree add /tmp/sensorium-v1-bench e384ef4
(cd /tmp/sensorium-v1-bench && uv venv .venv -p 3.14 -q && uv pip install -q -p .venv/bin/python -e ".[dev]" && .venv/bin/python corpus/run_corpus.py --bench) | tee /tmp/bench-v1.txt
$PY corpus/run_corpus.py --bench | tee /tmp/bench-arc1.txt
git worktree remove /tmp/sensorium-v1-bench --force
```

Record both tables in the PR description (Task 12). Expected: `call_dense default` within ~5% of v1 (sync path adds ~50–100 ns to ~6 µs); `async_call_dense` new row, higher per-event cost (task path), reported not gated. If the sync multiplier moved by more than ~10%, that is a finding: re-measure twice (best-of-N already), then look at `_on_start` for an accidental per-event cost before shipping.

- [ ] **Step 3: Commit**

```bash
git add corpus/_bench/bench.py
git commit -m "chore(bench): add an async call-dense workload so the task-identity path is measured"
```

---

### Task 12: Docs, version, matrix run, PR

**Files:**
- Modify: `README.md` (`Use` block after line 83; new `### tree` subsection under "What the answers claim"; "What a trace file holds" list; "Not in v1" → "Not yet"; Overhead section)
- Modify: `pyproject.toml` (`version = "0.2.0"`)
- Modify: spec status line

- [ ] **Step 1: README edits**

1. After the `Use` code block (the paragraph beginning "Per-line state is opt-in…"), add a paragraph:

   > On an asyncio program `tree` groups by task, shows each coroutine call as an unframed event in its true position, and tags a framed call whose caller opened no frame with that caller's name (`<- worker (unframed)`) instead of re-parenting it. Nothing inside an `async def` is inspectable yet — no `--focus`, `watch` or LINE there — and `run` says so at record time if a `--focus` matched only such code.

2. New subsection before `### \`exceptions\``:

   ```
   ### `tree` — derived parentage, and what a task group claims

   A parent link is the **caller frame**, verified by code identity, never
   "the last frame opened on this thread" — coroutines resumed by the event
   loop, generators resumed by their consumer and callbacks from C all break
   that assumption, and v1 made it. When the caller has no frame (a
   generator or coroutine body) the link is `NULL` and the caller is *named*;
   when the caller is untraced (the event loop, a library) the frame is a
   root. A trace recorded by a format-1 sensorium is labelled
   `parentage: ASSUMED` because its links were the guess.

   Grouping by task is a statement about causality *within* a task (one
   task is sequential) and says nothing about order *between* tasks beyond
   wall-clock event ids; the footer says so. Task identity is a serial
   minted per task object, not the task's name — two tasks named alike do
   not merge — and is `NULL` for everything that ran outside a running loop.
   ```

3. "What a trace file holds" — add a bullet: `- which asyncio task each event ran in, and the tasks' names;`

4. Replace `## Not in v1` section with:

   ```
   ## Not yet

   Line-level capture, `--focus`, `watch` and frames **inside** `async def`
   (coroutines are recorded as unframed calls with task identity, and their
   sync callees are attributed — but the coroutine's own body is not
   inspectable; arc 2). Subprocess following, attach-to-live-server flight
   recording, native (rr) substrates, MCP wrapper. See
   `docs/superpowers/specs/2026-08-21-sensorium-async-design.md`.
   ```

5. Overhead section — add the `async_call_dense` row from `/tmp/bench-arc1.txt` to the table and one sentence: the task-identity path costs more per event than the sync path; the sync path's change from v1 is the number beside it.

- [ ] **Step 2: Version + spec status**

`pyproject.toml`: `version = "0.2.0"`. Spec first line under the title: `Status: implemented on feat/async-attribution (arc 1); arc 2 pending its own spec`.

- [ ] **Step 3: Full matrix + corpus, all three interpreters**

```bash
cd ~/workspace/sensorium
for v in 3.12 3.13 3.14; do
  uv venv /tmp/sv$v -p $v -q && uv pip install -q -p /tmp/sv$v/bin/python -e ".[dev]"
  echo "== $v tests ==";  /tmp/sv$v/bin/python -m pytest -q 2>&1 | tail -2
  echo "== $v corpus ==";  /tmp/sv$v/bin/python corpus/run_corpus.py 2>&1 | tail -2
done
```

Expected: green on all three (3.12 keeps its 6 alloc-precondition skips). If 3.12/3.13 differ on any async test, that is a version fact to record in the test (skip with reason) **only if** the tool's claim stays true on that version — otherwise fix the tool.

- [ ] **Step 4: Commit and push, open PR**

```bash
git add README.md pyproject.toml docs/superpowers/specs/2026-08-21-sensorium-async-design.md
git commit -m "docs: async attribution (arc 1) -- README, version 0.2.0"
git push -u origin feat/async-attribution
gh pr create --title "Async attribution (arc 1): derived parentage, task identity, honest tree/frame/info/watch" --body-file - <<'EOF'
Implements docs/superpowers/specs/2026-08-21-sensorium-async-design.md (arc 1).

- recorder derives every parent from the caller frame (verified by code identity); no more "last opened frame is the caller"
- every event stamped with a minted asyncio task serial; recorder never imports asyncio itself
- trace format 2 (events.task_id, tasks table, CALL payload keys); format-1 traces open and are labelled "parentage assumed"
- tree groups by task, shows unframed coroutine/generator calls, names real callers; frame stops denying recorded activations; info counts unframed calls + lists tasks; watch names the real reason
- 4 new pre-registered corpus cases; real v1 fixture trace for the old-format honesty tests

Bench (this box):
<paste /tmp/bench-v1.txt and /tmp/bench-arc1.txt>

Matrix: 3.12 / 3.13 / 3.14 tests + corpus green locally; CI will confirm.
EOF
git fetch origin && git status -sb | head -1      # verify in sync
```

- [ ] **Step 5: Optional follow-up outside the repo** — `~/.claude/skills/debugging-with-sensorium/SKILL.md`: add one rule: "on asyncio code read `tree`'s task groups; a `<- NAME (unframed)` tag means the caller is a coroutine/generator body and is not inspectable yet (no `--focus`/`watch` there)."

---

## Self-review

**Spec coverage**

| Spec section | Task |
|---|---|
| The problem (3 defects) | 3 (parentage), 7 (`frame` denial), 8 (`info` disclosure) |
| Root cause: stack discipline | 3 (`_TLS.live`, `_parent_of`) |
| Measurements → no `import asyncio`, gate on `_get_running_loop` | 4 |
| D1 derived parentage, `caller_code`, miss = NULL + depth 0, `id()` soundness, close by identity | 3 |
| D2 task identity: minted serial, WeakKeyDictionary, names not identity, NULL outside loop | 4 |
| D3 `tree` | 6 |
| D3 `frame` | 7 |
| D3 `info` | 8 |
| D4 format bump, `events.task_id`, `tasks`, `caller_code` payload, format-1 labelled assumed | 1, 2, 6, 7, 8 |
| Honesty rule 1 (inter-task order wall-clock) | 6 footer |
| Honesty rule 2 (`watch`/`--focus` on coroutines, record-time warning) | 5, 9, corpus `async_focus` |
| Honesty rule 3 (never backfill a parent) | 3, 6 |
| Honesty rule 4 (format-1 assumed) | 2, 6, 7, 8, fixture tests |
| Honesty rule 5 (`refocus` licence unchanged) | no code change; `causal_stream` untouched — verified by the existing refocus suite staying green in every task |
| Verification: corpus cases 1–3, 5 | 10 |
| Verification: case 4 (format-1 trace) | 0 + fixture tests in 2, 6, 7, 8 (a pytest fixture, not a corpus case — the corpus harness *records*, and the point of this case is a recording it cannot make) |
| Verification: `--bench` in situ | 11 |
| Verification: matrix 3.12/3.13/3.14 | 12 |
| Arc-2 constraints (ABANDONED, per-task fingerprints, serial is the key) | 3 comment on `_TLS.live`; no fingerprint change; `task_id` column is the key arc 2 will use |

**Placeholder scan** — no TBD/TODO; every code step carries the code; the unframed-count expectation in Task 6 is pinned against the trace (`test_tree_unframed_count_matches_the_trace`) rather than a guessed literal. One deliberate "nothing fails" mutation is recorded in Tasks 3 and 4 with the reason, so a future reader does not re-discover it.

**Type consistency** — `Trace.unframed_calls(code_id=None) -> list[Event]`, `Trace.task(id) -> Task|None`, `Trace.tasks()`, `Trace.format`, `Trace.parentage_basis()`, `Trace.call_counts()` are used with those exact names in Tasks 6–9; `TraceWriter.add_event(..., task_id=)` / `add_task(task_id, name, thread_id)` in Tasks 2 and 4; `Tracer._parent_of(tls, caller)` is called unbound as `Tracer._parent_of(None, tls, caller)` in the isolation test (it uses no `self`); `unframed_kind(ev)`/`frame_line`/`unframed_line` are imported from `tree_cmd` by `frame_cmd`; `FocusSpec.entries_matching` / `Tracer.unframed_focus()` in Task 5 and `boot`.
