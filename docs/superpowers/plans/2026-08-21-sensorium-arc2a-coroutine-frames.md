# Arc 2a — Coroutine Frames, Suspension States, Inspection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every traced code object — functions, generators, coroutines, async generators — a frame, record suspension and resumption as events, derive each frame's end state honestly (returned / raised / cancelled / abandoned / suspended at end of recording / open), and make `--focus`, `watch`, `tree`, `frame`, `exceptions` work inside `async def`; trace format 3.

**Architecture:** The recorder's `tls.live` map (keyed by `id(frame)`, verified by code identity — measured stable across suspension) simply stops excluding generator-like code; `PY_YIELD`/`PY_RESUME`/`PY_THROW` become `YIELD`/`RESUME` events on the same frame; `--window` becomes an ancestry flag on the live entry (exact under concurrency) instead of a per-thread counter. The reader derives frame state from `closed_by`, `unwind_exc` and the frame's last suspension event; `tree`/`frame`/`exceptions`/`watch`/`info` consume that. Formats 1 and 2 keep rendering exactly as arc 1 left them (a real 0.2.0 fixture proves it).

**Tech Stack:** Python 3.12–3.14, `sys.monitoring` (`PY_YIELD`, `PY_RESUME`, `PY_THROW` exist since 3.12), sqlite3, pytest, PyYAML (corpus), `uv`. Stdlib-only runtime.

**Spec:** `docs/superpowers/specs/2026-08-21-sensorium-arc2-inspectable-coroutines-design.md` (plan 2a implements §D1–D5, §D7 and the verification section; §D6 is plan 2b). The arc-1 spec `docs/superpowers/specs/2026-08-21-sensorium-async-design.md` is the baseline it amends.

## Global Constraints

- Python floor `>=3.12`; every task's tests green on 3.12 / 3.13 / 3.14 (`uv venv /tmp/svX -p X` as in arc 1); stdlib-only runtime; the recorder never imports asyncio.
- **Measured facts the code may rely on** (spec "Measurements"): frame identity is stable across suspension; a dropped suspended generator fires `PY_THROW(GeneratorExit)` + `PY_UNWIND`; a cancelled task fires `PY_THROW(CancelledError)` + `PY_UNWIND`; LINE fires inside coroutines with readable locals; `PY_YIELD` receives the yielded value, `PY_THROW` the exception; `STOP_ITERATION` is not subscribed.
- Frame state is **derived by the reader** (`Trace.frame_state`) — never stored by the recorder; "cancelled"/"abandoned" require the thrown exception's **serial** to equal the unwind's serial (spec D2).
- `YIELD`/`RESUME` are never passed to `Fingerprint.update`; the awaited object is recorded as a **type name only** via `plain_str`, never `repr` (spec honesty rules 3).
- Hostile-program discipline unchanged: program code runs only inside `in_hook`; every new read of a program object is guarded.
- Formats ≤ 2 keep arc 1's wording everywhere (honesty rule 4); a real 0.2.0 fixture (`tests/fixtures/format2_async.db`, recorded under `env -i`, `meta.env` keys exactly `['LANG','PATH','SENSORIUM_DIR']`) pins it.
- Every new test is mutation-checked with `__pycache__` purged (`find . -name __pycache__ -not -path './.venv/*' -exec rm -rf {} +`) and `PYTHONDONTWRITEBYTECODE=1`; the report records each mutation's failing and restored output.
- Corpus questions are registered (YAML written) before their program is run; Ruling 2 (format pre-flight on an unrelated recording) stands.
- Conventional commits, no attribution trailer; branch `feat/async-arc2` (exists, spec committed at 6896301); never on `main`; push/PR deferred to the finishing skill.
- Output for traces with no generators/coroutines stays byte-compatible with 0.2.0 where tests pin it (`tests/test_tree_frame.py` sync tests, `tests/test_runs_info.py`, `tests/test_watch*.py`).

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `tests/fixtures/format2_async.py` / `.db` | REAL 0.2.0 recording (format 2) of a coroutine+generator program, recorded with `--focus` on the coroutine | create |
| `tests/test_format2_fixture.py` | old-trace honesty (arc-1 wording survives on format 2) | create |
| `src/sensorium/store/db.py` | `TRACE_FORMAT` 2→3; `frames.kind`; `task_fingerprints` table | modify |
| `src/sensorium/store/writer.py` | `open_frame(..., kind)`; frames INSERT gains `kind` | modify |
| `src/sensorium/store/reader.py` | `Frame.kind`, `FrameState`, `Trace.frame_state`, `_FRAME_COLS` by format | modify |
| `src/sensorium/query/fmt.py` | `fmt_event` renders `YIELD`/`RESUME` | modify |
| `src/sensorium/record/tracer.py` | `in_window` ancestry flag; frames for every kind; `_on_yield/_on_resume/_on_throw`; `suspended` slot; retire `frameless`, `window_depths`, `_focus_hits`/`unframed_focus` | modify (4 tasks) |
| `src/sensorium/record/boot.py` | retire the focus-unframed warning + `focus_unframed` meta | modify |
| `src/sensorium/query/tree_cmd.py` | kind marker, state tails, caller-tag wording by format | modify |
| `src/sensorium/query/frame_cmd.py` | header kind+state, suspension rows in the timeline | modify |
| `src/sensorium/query/exceptions_cmd.py` | lift the under-claim; thrown-in rule; format ≤2 arm kept | modify |
| `src/sensorium/query/info_cmd.py` | `recorded:` gains YIELD/RESUME; unframed line wording on format 3 | modify |
| `src/sensorium/query/watch_cmd.py` | no code change expected (sites are frames); tests re-pointed | tests |
| `corpus/generator_swallow`, `async_cancelled`, `async_focus`, `async_interleaved`, `unframed_callers` | re-registered | modify |
| `corpus/abandoned_generator`, `corpus/suspended_handler`, `corpus/window_across_suspension`, `corpus/async_handler` | new cases | create |
| `corpus/_bench/bench.py` | `await_dense` workload | modify |
| `README.md`, `pyproject.toml` (0.3.0), spec status | docs | modify |
| tests: `test_store_db`, `test_writer`, `test_reader`, `test_fmt`, `test_tracer`, `test_async`, `test_focus`, `test_boot_cli`, `test_tree_frame`, `test_exceptions`, `test_watch`, `test_runs_info`, `test_corpus`, `test_bench` | extend / re-point | modify |

Setup for every task:

```bash
cd ~/workspace/sensorium && git checkout feat/async-arc2
[ -d .venv ] || uv venv .venv -p 3.14
uv pip install -p .venv/bin/python -e ".[dev]"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -x 2>&1 | tail -2     # 623 passed expected at the start
```

`PY=.venv/bin/python` is assumed below.

---

### Task 0: Record a real format-2 fixture before the format changes

**Files:**
- Create: `tests/fixtures/format2_async.py`, `tests/fixtures/format2_async.db`
- Create: `tests/test_format2_fixture.py`

**Interfaces:**
- Produces: a trace with `meta.trace_format == 2`, recorded by 0.2.0 (`main` @ d59cafc) WITH `--focus format2_async:worker`, whose program has two tasks (one cancelled), a generator helper, and a coroutine awaited by a coroutine — so it holds unframed CALL events with `unframed`, `parent_frame`, `caller_code`, and the arc-1 `NOTHING WAS CHECKED` shape for `watch`. `installed_fixture2` pytest fixture (copies it to a disposable store as run id `old2`).

- [ ] **Step 1: Write the program**

`tests/fixtures/format2_async.py`:

```python
"""Source of tests/fixtures/format2_async.db, recorded by sensorium 0.2.0
(main @ d59cafc, trace_format 2) with `--focus format2_async:worker`. Do not
edit: the .db is what 0.2.0 wrote for exactly this program, and the tests
pin how a format-3 reader describes a format-2 trace (arc-1 wording).

Shapes it holds: two tasks (one cancelled at an await), a generator helper
consumed by a sync function, a coroutine awaited by a coroutine.
"""
import asyncio


def step(task, n):
    return f"{task}:{n}"


def parse(s):
    return int(s)


def rows(items):
    for it in items:
        yield parse(it)


async def inner(name):
    return step(name, 0)


async def worker(name, delay):
    await inner(name)
    step(name, 1)
    await asyncio.sleep(delay)
    return step(name, 2)


async def main():
    total = sum(rows(["1", "2"]))
    a = asyncio.create_task(worker("A", 0), name="task-A")
    b = asyncio.create_task(worker("B", 10), name="task-B")
    await a
    b.cancel()
    try:
        await b
    except asyncio.CancelledError:
        pass
    return total


if __name__ == "__main__":
    print(asyncio.run(main()))
```

- [ ] **Step 2: Record it with 0.2.0 in a throwaway worktree under a scrubbed environment**

```bash
cd ~/workspace/sensorium
git worktree add /tmp/sensorium-v020 d59cafc
cd /tmp/sensorium-v020 && uv venv .venv -p 3.14 -q && uv pip install -q -p .venv/bin/python -e .
cp ~/workspace/sensorium/tests/fixtures/format2_async.py ./format2_async.py
mkdir -p /tmp/fixture2-store
env -i PATH=/usr/bin:/bin LANG=C.UTF-8 SENSORIUM_DIR=/tmp/fixture2-store .venv/bin/sensorium run --focus format2_async:worker -- format2_async.py
```

Expected stdout: `3`, then `run:`/`trace:` lines, then the 0.2.0 stderr warning `sensorium: --focus format2_async:worker matched only coroutine/generator code …`.

- [ ] **Step 3: Copy in, verify, clean up**

```bash
cp /tmp/fixture2-store/traces/*.db ~/workspace/sensorium/tests/fixtures/format2_async.db
cd ~/workspace/sensorium && $PY - <<'PY'
import sqlite3, json
c = sqlite3.connect("tests/fixtures/format2_async.db")
g = lambda k: json.loads(c.execute("SELECT value FROM meta WHERE key=?", (k,)).fetchone()[0])
print("format", g("trace_format"), "| env", sorted(g("env")), "| focus_unframed", g("focus_unframed"))
print("frames cols", [r[1] for r in c.execute("PRAGMA table_info(frames)")])
print("kinds", dict(c.execute("SELECT kind, COUNT(*) FROM events GROUP BY kind")))
PY
git worktree remove /tmp/sensorium-v020 --force && rm -rf /tmp/fixture2-store
```

Expected: `format 2 | env ['LANG', 'PATH', 'SENSORIUM_DIR'] | focus_unframed ['format2_async:worker']`; frames cols without `kind`; kinds include CALL/RETURN/RAISE/HANDLED and **no** LINE (0.2.0 could not focus a coroutine).

- [ ] **Step 4: Write the test file**

`tests/test_format2_fixture.py`:

```python
"""A trace recorded by sensorium 0.2.0 (trace_format 2), read by this one.

Arc 2 gives coroutines and generators frames. A format-2 trace has none for
them -- it holds unframed CALL events -- and a format-3 reader must keep
saying exactly what 0.2.0 said about it: unframed lines in `tree`,
"recorded but not framed" in `frame`, the `ambiguous ... no frame recorded`
arm in `exceptions`, and `watch`'s "opens no frame in this version" reason.
No state, no disposition, no site may be claimed retroactively.
"""
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from sensorium import cli
from sensorium.store.reader import Trace

FIXTURE = Path(__file__).parent / "fixtures" / "format2_async.db"


def test_fixture_really_is_trace_format_2_with_no_frame_kind():
    c = sqlite3.connect(FIXTURE)
    fmt = json.loads(c.execute(
        "SELECT value FROM meta WHERE key='trace_format'").fetchone()[0])
    assert fmt == 2
    assert "kind" not in [r[1] for r in c.execute("PRAGMA table_info(frames)")]
    kinds = {r[0] for r in c.execute("SELECT DISTINCT kind FROM events")}
    assert "YIELD" not in kinds and "RESUME" not in kinds


def test_fixture_carries_no_ambient_environment():
    env = Trace.open(FIXTURE).meta["env"]
    assert sorted(env) == ["LANG", "PATH", "SENSORIUM_DIR"]


def test_fixture_holds_the_arc1_unframed_shapes():
    t = Trace.open(FIXTURE)
    worker = next(c for c in t.codes() if c.qualname == "worker")
    rows = next(c for c in t.codes() if c.qualname == "rows")
    assert len(t.unframed_calls(code_id=worker.id)) == 2
    assert t.unframed_calls(code_id=rows.id)[0].payload["unframed"] == "generator"
    assert t.frames(code_id=worker.id) == []
    assert t.meta["focus_unframed"] == ["format2_async:worker"]


@pytest.fixture
def installed_fixture2(tmp_path, monkeypatch):
    store = tmp_path / "sdir" / "traces"
    store.mkdir(parents=True)
    shutil.copy(FIXTURE, store / "old2.db")
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return "old2"
```

- [ ] **Step 5: Run, commit**

Run: `PYTHONDONTWRITEBYTECODE=1 $PY -m pytest tests/test_format2_fixture.py -v` → 3 passed.

```bash
git add tests/fixtures/format2_async.py tests/fixtures/format2_async.db tests/test_format2_fixture.py
git commit -m "test: capture a real 0.2.0 (format-2) coroutine trace as a fixture"
```

---

### Task 1: Format 3 — schema, writer, reader `frame_state`, `fmt_event`

**Files:**
- Modify: `src/sensorium/store/db.py` (`TRACE_FORMAT`, frames table, new table), `src/sensorium/store/writer.py` (`open_frame`, frames INSERT), `src/sensorium/store/reader.py` (`Frame`, `_FRAME_COLS_V2/V3`, `_frame`, `__init__` column detection, `FrameState`, `frame_state`), `src/sensorium/query/fmt.py` (`fmt_event`)
- Test: `tests/test_store_db.py`, `tests/test_writer.py`, `tests/test_reader.py`, `tests/test_fmt.py`, `tests/test_format2_fixture.py`, `tests/test_format1_fixture.py`

**Interfaces:**
- Produces:
  - `db.TRACE_FORMAT == 3`; `frames.kind TEXT` (last column); `task_fingerprints(task_id INTEGER PRIMARY KEY, name TEXT, hash TEXT NOT NULL, n_events INTEGER NOT NULL)`.
  - `TraceWriter.open_frame(parent_id, code_id, call_event_id, depth, thread_id, kind="function") -> int`.
  - `Frame.kind: str = "function"` (last dataclass field; formats ≤ 2 read as `function`).
  - `@dataclass(frozen=True) class FrameState: state: str; line: int | None; exc: dict | None` with `state ∈ {"returned","raised","cancelled","abandoned","thrown","suspended","open"}`.
  - `Trace.frame_state(frame) -> FrameState`; `Trace.suspensions(fid) -> list[Event]` (the frame's `YIELD`/`RESUME` rows in order).
  - `fmt_event` renders `e12 YIELD   worker L29 awaiting Future`, `e14 RESUME  worker L29`, `e15 RESUME  worker L29 thrown CancelledError('')`.

- [ ] **Step 1: Failing tests**

Append to `tests/test_store_db.py`:

```python
def test_format_3_adds_frame_kind_and_task_fingerprints(tmp_path):
    conn = db.create_trace(tmp_path / "t.db")
    assert db.get_meta(conn, "trace_format") == 3
    fcols = [r[1] for r in conn.execute("PRAGMA table_info(frames)")]
    assert fcols[-1] == "kind"
    tcols = [r[1] for r in conn.execute("PRAGMA table_info(task_fingerprints)")]
    assert tcols == ["task_id", "name", "hash", "n_events"]
```

(Also change `test_create_trace_has_all_tables`'s expected table set to include `"task_fingerprints"`.)

Append to `tests/test_writer.py`:

```python
def test_open_frame_records_the_kind_and_defaults_to_function(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=100)
    cid = w.intern_code("/x/prog.py", "gen", 1)
    e1 = w.add_event(0, 1, "CALL", None, cid, 1, {"args": {}})
    f1 = w.open_frame(None, cid, e1, 0, 1)
    f2 = w.open_frame(None, cid, e1, 0, 1, kind="coroutine")
    w.close()
    c = sqlite3.connect(p)
    assert c.execute("SELECT id, kind FROM frames ORDER BY id").fetchall() == [
        (f1, "function"), (f2, "coroutine")]
```

Append to `tests/test_reader.py`:

```python
def _frame_with(tmp_path, closed_by, unwind_exc, tail_events, kind="coroutine"):
    """One frame of `kind`, closed as given, with `tail_events` =
    [(kind, line, payload), ...] appended in order after its CALL."""
    w = TraceWriter(tmp_path / "t.db", batch=100)
    c = w.intern_code("/x/p.py", "worker", 1)
    e1 = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f1 = w.open_frame(None, c, e1, 0, 1, kind=kind)
    for k, line, payload in tail_events:
        w.add_event(1, 1, k, f1, c, line, payload)
    if closed_by is not None:
        w.close_frame(f1, None, closed_by, unwind_exc)
    w.close()
    t = Trace.open(tmp_path / "t.db")
    return t, t.frame(f1)


CANCEL = {"type": "CancelledError", "msg": "", "oid": 1, "serial": 7}
GENEXIT = {"type": "GeneratorExit", "msg": "", "oid": 2, "serial": 8}
VALERR = {"type": "ValueError", "msg": "x", "oid": 3, "serial": 9}


def test_frame_kind_reads_function_on_old_traces_and_the_column_on_new(tmp_path):
    t, f = _frame_with(tmp_path, "return", None, [])
    assert f.kind == "coroutine"
    assert Trace.open(Path(__file__).parent / "fixtures" / "format2_async.db"
                      ).frames()[0].kind == "function"


def test_frame_state_derives_each_state_from_evidence(tmp_path):
    t, f = _frame_with(tmp_path / "a", "return", None,
                       [("YIELD", 29, {"awaiting": "Future"}), ("RESUME", 29, None)])
    assert t.frame_state(f).state == "returned"
    t, f = _frame_with(tmp_path / "b", "unwind", VALERR,
                       [("YIELD", 29, {"awaiting": "Future"}), ("RESUME", 29, None)])
    assert t.frame_state(f) == FrameState("raised", None, VALERR)
    t, f = _frame_with(tmp_path / "c", "unwind", CANCEL,
                       [("YIELD", 29, {"awaiting": "Future"}),
                        ("RESUME", 29, {"thrown": CANCEL})])
    assert t.frame_state(f) == FrameState("cancelled", 29, CANCEL)
    t, f = _frame_with(tmp_path / "d", "unwind", GENEXIT,
                       [("YIELD", 23, {"awaiting": "NoneType"}),
                        ("RESUME", 23, {"thrown": GENEXIT})], kind="generator")
    assert t.frame_state(f) == FrameState("abandoned", 23, GENEXIT)
    t, f = _frame_with(tmp_path / "e", "unwind", VALERR,
                       [("YIELD", 23, {"awaiting": "NoneType"}),
                        ("RESUME", 23, {"thrown": VALERR})], kind="generator")
    assert t.frame_state(f) == FrameState("thrown", 23, VALERR)
    t, f = _frame_with(tmp_path / "f", None, None,
                       [("YIELD", 29, {"awaiting": "Future"})])
    assert t.frame_state(f) == FrameState("suspended", 29, None)
    t, f = _frame_with(tmp_path / "g", None, None, [])
    assert t.frame_state(f) == FrameState("open", None, None)


def test_frame_state_cancelled_requires_the_serials_to_match(tmp_path):
    """A CancelledError thrown in and a DIFFERENT CancelledError raised
    inside are two objects; only the serial says which one unwound the
    frame. A type match alone would over-claim."""
    other = dict(CANCEL, serial=99)
    t, f = _frame_with(tmp_path, "unwind", other,
                       [("YIELD", 29, {"awaiting": "Future"}),
                        ("RESUME", 29, {"thrown": CANCEL})])
    assert t.frame_state(f).state == "raised"
```

Add `from sensorium.store.reader import FrameState` and `from pathlib import Path` to that file's imports if absent.

Append to `tests/test_fmt.py` (it has a `_FakeEvent(payload)` helper; extend it so `kind`/`line` can be set, or add a sibling):

```python
def test_fmt_event_renders_yield_and_resume():
    class E:
        def __init__(self, kind, line, payload, eid=12):
            self.id, self.kind, self.line, self.payload, self.code_id = eid, kind, line, payload, 1
    class T:
        def code(self, cid):
            class C: qualname = "worker"
            return C()
    t = T()
    assert fmt_event(t, E("YIELD", 29, {"awaiting": "Future"})) == \
        "e12 YIELD   worker L29 awaiting Future"
    assert fmt_event(t, E("RESUME", 29, None, 14)) == "e14 RESUME  worker L29"
    assert fmt_event(t, E("RESUME", 29, {"thrown": {"type": "CancelledError",
                                                   "msg": "", "oid": 1}}, 15)) == \
        "e15 RESUME  worker L29 thrown CancelledError('')"
```

- [ ] **Step 2: Run to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 $PY -m pytest tests/test_store_db.py tests/test_writer.py tests/test_reader.py tests/test_fmt.py -q`
Expected: FAIL — format 2, no `kind` column/kwarg, `FrameState` missing, `fmt_event` renders `e12 YIELD   worker`.

- [ ] **Step 3: Implement**

`db.py`: `TRACE_FORMAT = 3`; in `SCHEMA` append `kind TEXT` as the last `frames` column; add after `tasks`:

```sql
CREATE TABLE task_fingerprints (
  task_id INTEGER PRIMARY KEY,
  name TEXT,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
```

Extend the `TraceFormatError` docstring: `Format 3 (inspectable coroutines) added frames.kind, the YIELD/RESUME event kinds, and task_fingerprints; a format-2 trace opens and renders with arc 1's wording.`

`writer.py`:

```python
    def open_frame(self, parent_id, code_id, call_event_id, depth,
                   thread_id, kind: str = "function") -> int:
        with self._lock:
            fid = self._next_frame
            self._next_frame += 1
            self._frames.append(
                (fid, parent_id, code_id, call_event_id, depth, thread_id, kind))
            return fid
```

and the INSERT: `"INSERT INTO frames (id, parent_id, code_id, call_event_id, depth, thread_id, kind) VALUES (?, ?, ?, ?, ?, ?, ?)"`.

`reader.py`:

```python
@dataclass(frozen=True)
class Frame:
    id: int
    parent_id: int | None
    code_id: int
    call_event_id: int
    return_event_id: int | None
    depth: int
    thread_id: int
    closed_by: str | None
    unwind_exc: dict | None
    kind: str = "function"      # formats <= 2 recorded no kind: framed code there is a function


@dataclass(frozen=True)
class FrameState:
    """How a frame ended, DERIVED from evidence (spec D2): returned | raised |
    cancelled | abandoned | thrown | suspended | open. `line` is the parked
    line for suspended/cancelled/abandoned/thrown; `exc` the unwind cause."""
    state: str
    line: int | None
    exc: dict | None


_FRAME_COLS_V2 = ("id, parent_id, code_id, call_event_id, return_event_id, "
                  "depth, thread_id, closed_by, unwind_exc")
_FRAME_COLS_V3 = _FRAME_COLS_V2 + ", kind"


def _frame(row) -> Frame:
    return Frame(*row[:8], _loads(row[8]), *row[9:])
```

In `Trace.__init__` after the events-column probe: `fcols = {r[1] for r in conn.execute("PRAGMA table_info(frames)")}; self._fcols = _FRAME_COLS_V3 if "kind" in fcols else _FRAME_COLS_V2`; replace every `{_FRAME_COLS}` f-string (`frames`, `frame`, `children`, `roots`, `frame_containing`) with `{self._fcols}`. Add:

```python
    def suspensions(self, fid: int) -> list[Event]:
        return self.events(kind=("YIELD", "RESUME"), frame_id=fid)

    def frame_state(self, f: Frame) -> FrameState:
        """Spec D2. Evidence only: closed_by, unwind_exc, and the frame's last
        YIELD/RESUME row. 'cancelled'/'abandoned'/'thrown' need the serial of
        the exception thrown in at the last RESUME to equal the unwind's --
        a type match alone could be a different exception raised inside."""
        last = self._c.execute(
            "SELECT kind, line, payload FROM events WHERE frame_id = ? "
            "AND kind IN ('YIELD', 'RESUME') ORDER BY id DESC LIMIT 1",
            (f.id,)).fetchone()
        lkind, lline, lpayload = (None, None, None) if last is None else (
            last[0], last[1], _loads(last[2]))
        if f.closed_by == "return":
            return FrameState("returned", None, None)
        if f.closed_by == "unwind":
            thrown = (lpayload or {}).get("thrown") if lkind == "RESUME" else None
            ts = thrown.get("serial") if thrown else None
            us = (f.unwind_exc or {}).get("serial")
            if thrown is not None and ts is not None and ts == us:
                t = thrown.get("type")
                state = ("cancelled" if t == "CancelledError"
                         else "abandoned" if t == "GeneratorExit" else "thrown")
                return FrameState(state, lline, f.unwind_exc)
            return FrameState("raised", None, f.unwind_exc)
        if lkind == "YIELD":
            return FrameState("suspended", lline, None)
        return FrameState("open", None, None)
```

`fmt.py` `fmt_event`: add before the `else`:

```python
    elif e.kind == "YIELD":
        body = f"{q} L{e.line} awaiting {p.get('awaiting', '?')}"
    elif e.kind == "RESUME":
        thrown = p.get("thrown")
        body = (f"{q} L{e.line} thrown {fmt_exc(thrown)}" if thrown
                else f"{q} L{e.line}")
```

- [ ] **Step 4: Run** — the four files, then `tests/test_format1_fixture.py tests/test_format2_fixture.py`, then the full suite `-x`, then `PYTHONDONTWRITEBYTECODE=1 $PY corpus/run_corpus.py` → 15/27/0 (the recorder still opens frames only for functions; `kind` defaults).

- [ ] **Step 5: Mutation checks** — (a) `frame_state`: replace `ts == us` with `True` → `test_frame_state_cancelled_requires_the_serials_to_match` fails; (b) swap the `cancelled`/`abandoned` type strings → `test_frame_state_derives_each_state_from_evidence` fails; (c) `fmt_event`: drop the `awaiting` tail → fmt test fails. Restore each.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/store/db.py src/sensorium/store/writer.py src/sensorium/store/reader.py src/sensorium/query/fmt.py tests/test_store_db.py tests/test_writer.py tests/test_reader.py tests/test_fmt.py
git commit -m "feat(store): trace format 3 -- frames.kind, task_fingerprints, derived FrameState, YIELD/RESUME rendering"
```

---

### Task 2: `--window` as an ancestry flag (retire `window_depths`)

**Files:**
- Modify: `src/sensorium/record/tracer.py` — `_TLS.__init__` (drop `window_depths`), `_on_start` (compute `in_window`, live entry gains slot 5), `_on_return`/`_on_unwind` (drop the decrement blocks), `_on_line` (consult `entry[5]`)
- Test: `tests/test_focus.py`

**Interfaces:**
- Produces: live entry layout `[fid, code, cid, prev_locals, depth, in_window]`; `Tracer._in_window(parent_entry, win_key) -> bool` = `win_key is not None or (parent_entry is not None and parent_entry[5])`.
- Existing window tests (`test_window_limits_line_capture_to_dynamic_extent`, `..._module_qualified_target`, `..._reentry_...`) must pass unchanged. `test_abandoned_generator_does_not_wedge_window_open` is REWRITTEN: its `tracer._tls.window_depths` assertion goes (the structure no longer exists); the behavioural half stays and gains the reason "a frame is in the window iff an ancestor is the window target — no counter can wedge".

- [ ] **Step 1: Failing tests**

Replace `test_abandoned_generator_does_not_wedge_window_open` in `tests/test_focus.py` with:

```python
def test_window_is_ancestry_so_an_abandoned_generator_cannot_wedge_it(tmp_path):
    """Membership in the window is derived from the frame's ANCESTRY, not
    from a per-thread counter: a generator abandoned mid-iteration has no
    descendants, so nothing later is "inside" it, counter or no counter."""
    t, err, tracer = record_inproc_full(
        tmp_path / "windowed", ABANDONED_GEN,
        focus=["prog:watched"], window="numbers")
    assert err is None
    assert not hasattr(tracer._tls, "window_depths")
    assert t.events(kind="LINE") == []      # watched() ran outside the window
    ctl, _ = record_inproc(tmp_path / "control", ABANDONED_GEN,
                           focus=["prog:watched"])
    quals = [ctl.code(e.code_id).qualname for e in ctl.events(kind="LINE")]
    assert quals and set(quals) == {"watched"}


TWO_TASK_WINDOW = """
import asyncio

def helper(tag):
    x = tag
    return x

async def windowed():
    helper("in")
    await asyncio.sleep(0)       # suspends; the other task runs meanwhile
    helper("in-again")

async def other():
    await asyncio.sleep(0)
    helper("out")

def main():
    async def amain():
        await asyncio.gather(windowed(), other())
    asyncio.run(amain())
"""


def test_window_on_a_coroutine_excludes_another_tasks_helper_during_suspension(tmp_path):
    """While `windowed` is parked, `other` calls helper("out") on the same
    thread. A per-thread counter would count that as inside the window; the
    ancestry flag does not, and helper("in-again") after the resume IS in."""
    t, err = record_inproc(tmp_path, TWO_TASK_WINDOW,
                           focus=["prog:helper"], window="windowed")
    assert err is None
    tags = [e.payload["deltas"]["x"]["v"] for e in t.events(kind="LINE")
            if "x" in e.payload["deltas"]]
    assert sorted(tags) == ["in", "in-again"]
```

(The second test will not pass until Task 3 gives `windowed` a frame; write it now, mark it `@pytest.mark.xfail(strict=True, reason="coroutine frames arrive in Task 3")`, and REMOVE the xfail in Task 3 — that is the contract between the two tasks.)

- [ ] **Step 2: Run to verify** — `tests/test_focus.py -q`: the rewritten abandoned test FAILS on `not hasattr(...window_depths)`; the xfail test xfails.

- [ ] **Step 3: Implement**

`_TLS.__init__`: delete `self.window_depths`. `_on_start`: replace the `window_depths` increment block with nothing, and build the entry as

```python
                in_window = bool(win_key is not None
                                 or (parent is not None and parent[5]))
                tls.live[id(frame)] = [fid, code, cid, {}, depth, in_window]
```

(`parent[5]` exists because every entry now has six slots.) `_on_return`/`_on_unwind`: delete the `window_depths` decrement blocks. `_on_line`: replace

```python
        if self.window and not any(tls.window_depths.values()):
            return None
        frame = sys._getframe(1)
        entry = tls.live.get(id(frame))
        if entry is None or entry[1] is not code:
            return None
```
with
```python
        frame = sys._getframe(1)
        entry = tls.live.get(id(frame))
        if entry is None or entry[1] is not code:
            return None           # no open frame for this activation
        if self.window and not entry[5]:
            # Outside the window: no ancestor of THIS activation is the
            # window target. Not DISABLE -- another activation of the same
            # code may be inside it later.
            return None
```

Update the `_TLS.live` comment to document slot 5 and the arc-1 test `test_parent_of_rejects_a_live_entry…` entries (they construct 5-slot lists — extend them to 6 slots `[7, code, 1, {}, 0, False]`).

- [ ] **Step 4: Run** — `tests/test_focus.py tests/test_async.py tests/test_tracer.py`, full suite, corpus.

- [ ] **Step 5: Mutation** — in `_on_start` set `in_window = win_key is not None` (drop ancestry): `test_window_limits_line_capture_to_dynamic_extent` fails (inner's frames are not the window target). Restore.

- [ ] **Step 6: Commit** — `git commit -m "refactor(record): --window is an ancestry flag on the live entry, not a per-thread counter"`.

---

### Task 3: Frames for every kind of code

**Files:**
- Modify: `src/sensorium/record/tracer.py` — `_classify` (return `kind` not `frameless`), `_frame_kind(code)`, `_on_start` (always `open_frame(..., kind)`; drop `unframed`/`parent_frame` payload keys), `_exc_event` and `_on_line` (drop kind exclusions), `_GENLIKE` comment, module docstring lines 30–36
- Modify: `tests/test_async.py` (three flipped tests rewritten), `tests/test_tracer.py::test_generators_recorded_frameless` → `test_generators_get_frames_of_kind_generator`, `tests/test_focus.py` (remove the xfail from Task 2's test)
- Test: new `tests/test_coroutine_frames.py`

**Interfaces:**
- Produces: `_classify` returns `(traced, rel, qual, focused, kind, win_key)` with `kind ∈ {"function","generator","coroutine","async_generator"}`; every traced call opens a frame with that kind; `tls.live` entries for coroutine/generator frames; `_exc_event` gives RAISE/HANDLED inside coroutines a `frame_id`; `_on_line` records LINE inside focused coroutines.
- Note: the `unframed` and `parent_frame` payload keys are no longer written; `caller_code`/`caller` still are.

- [ ] **Step 1: Failing tests**

`tests/test_coroutine_frames.py`:

```python
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
```

Rewrite in `tests/test_async.py`: `test_sync_helper_inside_a_coroutine_is_not_parented_to_the_module` → assert `f.parent_id` is a `worker` frame and NO `caller_code` (keep the name, rewrite the docstring: "arc 1 named the caller; arc 2 has a frame for it"); DELETE `test_coroutine_calls_are_recorded_unframed_with_their_kind` (its subject no longer exists; the format-2 fixture test covers the old shape); `test_generator_helper_names_the_generator_and_key_fn_finds_main` → `parse` frames' `parent_id == rows frame`, `rank` unchanged, and remove the `unframed_calls` assertions. `tests/test_tracer.py::test_generators_recorded_frameless` → rename `test_generators_get_frames_of_kind_generator` asserting `t.frames(code_id=gen_code.id)[0].kind == "generator"`.

- [ ] **Step 2: Run to verify** — the new file fails (no coroutine frames; `unframed_calls()` non-empty); the rewritten tests fail likewise.

- [ ] **Step 3: Implement**

In `tracer.py`, replace `_unframed_kind` with

```python
def _frame_kind(code) -> str:
    """Which kind of frame this code opens (frames.kind): every traced code
    object opens one -- arc 2 -- so this is a label, not a gate."""
    flags = code.co_flags
    if flags & _CO_ASYNC_GENERATOR:
        return "async_generator"
    if flags & _CO_COROUTINE:
        return "coroutine"
    if flags & _CO_GENERATOR:
        return "generator"
    return "function"
```

`_classify`: `kind = _frame_kind(code)`; drop the `_focus_hits` block (Task 5 removes the attribute; leave `self._focus_hits` assignment in `__init__` until then — or remove both here and adjust `unframed_focus` to return `[]`; choose removing both here and make `unframed_focus()` return `[]` with a docstring "retired in arc 2; removed in Task 5"); return `(True, rel, code.co_qualname, focused, kind, win_key)`; `untraced = (False, None, None, False, "function", None)`. Every caller that unpacked `frameless` now unpacks `kind` (`_on_start`, `_on_return`, `_on_unwind`, `_exc_event`, `_on_line`) — rename the variable; in `_on_start` delete the `if frameless:` payload block and the `if not frameless:` guard so the frame is ALWAYS opened: `fid = self.writer.open_frame(pfid, cid, eid, depth, tid, kind)`; in `_on_line` change `if not traced or not focused or frameless:` to `if not traced or not focused:`. Module docstring lines 30–36: replace with "Every traced code object opens a frame, generators and coroutines included (arc 2); a suspendable frame stays in `live` across its suspensions and leaves through PY_RETURN/PY_UNWIND like any other — the dropped-while-suspended case arrives as PY_THROW(GeneratorExit) + PY_UNWIND." Keep `_GENLIKE` for `_frame_kind` only.

Remove the `xfail` marker from `test_window_on_a_coroutine_excludes_another_tasks_helper_during_suspension`.

- [ ] **Step 4: Run** — `tests/test_coroutine_frames.py tests/test_async.py tests/test_tracer.py tests/test_focus.py`; then the full suite: EXPECT failures in `tests/test_tree_frame.py`, `tests/test_runs_info.py`, `tests/test_watch.py`, `tests/test_exceptions.py::test_exceptions_refuses_to_classify_a_frameless_handler`, `tests/test_boot_cli.py` (focus warning) and the corpus (`generator_swallow`, `async_*`, `unframed_callers`) — these are the query-side and corpus flips Tasks 5–11 own. Record the exact list in your report; do NOT "fix" them here. The suite is red between Task 3 and Task 11 by design; each task's own files must be green.

- [ ] **Step 5: Mutation** — make `_frame_kind` return `"function"` always: the kind assertions fail. Restore.

- [ ] **Step 6: Commit** — `git commit -m "feat(record): every traced code object opens a frame, generators and coroutines included"`.

---

### Task 4: `YIELD` / `RESUME` events and the `suspended` slot

**Files:**
- Modify: `src/sensorium/record/tracer.py` — `install`/`uninstall` subscriptions, new `_on_yield`, `_on_resume`, `_on_throw`, live entry slot 6 `suspended`
- Test: `tests/test_coroutine_frames.py`

**Interfaces:**
- Produces: events `YIELD` (`line`, payload `{"awaiting": <type name>}`), `RESUME` (`line`, payload `None` or `{"thrown": capture_exc(exc, serial)}`), both with `frame_id`, thread and task; entry slot 6 `suspended: bool`; states derivable by `Trace.frame_state` end to end: cancelled, abandoned, suspended-at-end, returned.

- [ ] **Step 1: Failing tests** (append to `tests/test_coroutine_frames.py`)

```python
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
    assert b.line == 9                                  # `await GATE.wait()`
    ys = t.events(kind="YIELD")
    assert {e.payload["awaiting"] for e in ys} == {"Future"} or ys
    assert all(e.frame_id is not None and e.task_id is not None for e in ys)
    rs = t.events(kind="RESUME")
    thrown = [e for e in rs if (e.payload or {}).get("thrown")]
    assert len(thrown) == 1 and thrown[0].payload["thrown"]["type"] == "CancelledError"


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


def test_yield_and_resume_never_touch_the_fingerprint(tmp_path):
    from tests.helpers import record_inproc_full
    t1, _, tr1 = record_inproc_full(tmp_path / "a", CANCEL)
    # Same program; the fingerprint is over CALL/RETURN/RAISE/HANDLED only,
    # so YIELD/RESUME counts do not appear in n_events.
    n_causal = sum(1 for e in t1.events() if e.kind in ("CALL", "RETURN", "RAISE", "HANDLED"))
    assert sum(n for _h, n in t1.fingerprints().values()) == n_causal
```

Add `from sensorium.store.reader import FrameState` to the file's imports.

- [ ] **Step 2: Run to verify** — FAIL: no YIELD events; states come back `open`/`raised`.

- [ ] **Step 3: Implement**

`_TLS`-independent: live entry becomes `[fid, code, cid, prev_locals, depth, in_window, suspended]` — in `_on_start` append `False`. Add the three callbacks after `_on_unwind`:

```python
    def _suspension(self, code, kind, payload):
        """Shared body of the YIELD/RESUME callbacks: the frame is the
        triggering frame, found in `live` by identity like every event."""
        tls = self._tls
        if tls.in_hook:
            return None
        traced, _fp, _qual, _focused, _kind, _win = self._decide(code)
        if not traced:
            return M.DISABLE
        tls.in_hook = True
        try:
            frame = sys._getframe(2)          # one deeper: _on_yield -> here
            entry = tls.live.get(id(frame))
            if entry is None or entry[1] is not code:
                return None
            entry[6] = (kind == "YIELD")
            self.writer.add_event(time.monotonic_ns(), tls.thread_serial, kind,
                                  entry[0], entry[2], frame.f_lineno, payload,
                                  task_id=self._task_serial(tls))
        finally:
            tls.in_hook = False
        return None

    def _on_yield(self, code, offset, value):
        try:
            awaiting = plain_str(type(value).__name__)
        except BaseException:                   # a metaclass __name__ is program code
            awaiting = "?"
        return self._suspension(code, "YIELD", {"awaiting": awaiting})

    def _on_resume(self, code, offset):
        return self._suspension(code, "RESUME", None)

    def _on_throw(self, code, offset, exc):
        # The exception is now in flight in that frame; identify it so the
        # RESUME row, the RAISE the interpreter fires next, and the UNWIND
        # all carry one serial -- that equality is what lets the reader say
        # "cancelled", not the type alone.
        tls = self._tls
        serial = None if tls.in_hook else tls.exc.identify(exc)
        return self._suspension(code, "RESUME", {"thrown": capture_exc(exc, serial)})
```

(`sys._getframe(2)` because `_suspension` sits one call deeper than the registered callback — verify with the cancel test that `YIELD` rows carry the worker frame's id; if `_getframe(2)` is wrong on your interpreter the test tells you, and `_getframe(1)` inside each callback passed down is the alternative.)

`install`: register `E.PY_YIELD → self._on_yield`, `E.PY_RESUME → self._on_resume`, `E.PY_THROW → self._on_throw`; add the three to `events`. `uninstall`: add them to the unregister tuple. Do NOT add them to `Fingerprint.update` anywhere.

- [ ] **Step 4: Run** — `tests/test_coroutine_frames.py tests/test_async.py tests/test_tracer.py tests/test_focus.py tests/test_reader.py`.

- [ ] **Step 5: Mutations** — (a) in `_on_throw` pass `serial=None` → the cancel test's `state == "cancelled"` fails (reader sees no serial match → "raised"); (b) skip `entry[6] = ...` → no test fails (slot unused until uninstall; note it); (c) add `self._fp(tid).update(...)` to `_suspension` → the fingerprint test fails. Restore.

- [ ] **Step 6: Commit** — `git commit -m "feat(record): record YIELD/RESUME (and thrown-in RESUME) on suspendable frames"`.

---

### Task 5: Retire the focus-unframed warning; `--focus` on coroutines records lines

**Files:**
- Modify: `src/sensorium/record/tracer.py` (`_focus_hits`, `unframed_focus` removed), `src/sensorium/record/boot.py` (`_finalize_meta` loses `focus_unframed`; the warning loop goes)
- Test: `tests/test_focus.py` (replace the two `unframed_focus` tests), `tests/test_boot_cli.py` (replace the two warning tests)

- [ ] **Step 1: Tests** — in `tests/test_focus.py` replace `test_focus_that_matched_only_coroutine_code_is_reported` and `test_focus_entry_that_matched_framed_and_unframed_code_is_not_reported` with:

```python
def test_focus_on_a_coroutine_records_its_lines_with_locals(tmp_path):
    t, err = record_inproc(tmp_path, ASYNC_FOCUS, focus=["prog:worker"])
    assert err is None
    lines = t.events(kind="LINE")
    assert lines and {t.code(e.code_id).qualname for e in lines} == {"worker"}
    assert not hasattr(record_inproc_full(tmp_path / "b", ASYNC_FOCUS)[2], "unframed_focus")
```

In `tests/test_boot_cli.py` replace the two warning tests with:

```python
def test_run_with_focus_on_a_coroutine_records_lines_and_stamps_no_warning(tmp_path):
    run_id, trace, r = record_script(tmp_path, ASYNC_FOCUS_SCRIPT,
                                     extra=["--focus", "prog:worker"])
    assert run_id, r.stderr
    assert "matched only coroutine" not in r.stderr
    from sensorium.store.reader import Trace
    t = Trace.open(trace)
    assert "focus_unframed" not in t.meta
    assert t.counts().get("LINE", 0) > 0
```

- [ ] **Step 2–4:** remove `self._focus_hits`, `unframed_focus` and the `_classify` hits block from the tracer; in `boot.py` remove the `focus_unframed` parameter, its `set_meta_final`, the `unframed = tracer.unframed_focus()` line and the stderr loop; update `test_late_write_guard_classifies_every_public_writer_method` only if it lists the meta key (it does not). Run `tests/test_focus.py tests/test_boot_cli.py tests/test_async.py`. Commit `refactor(record): retire the focus-unframed warning -- coroutines can be focused now`.

---

### Task 6: `tree` — kinds, state tails, caller-tag wording

**Files:**
- Modify: `src/sensorium/query/tree_cmd.py` (`frame_line`, `_caller_of`, module docstring, footers unchanged)
- Test: `tests/test_tree_frame.py`, `tests/test_format2_fixture.py`

**Interfaces:**
- Produces: `frame_line` renders `fN eM qual(args)  [coroutine]` + tail; tails per spec D4 from `trace.frame_state(frame)`: ` -> value` / ` !! Exc` / ` ~ cancelled (CancelledError thrown in at L29)` / ` ~ abandoned (dropped while suspended at L6)` / ` ~ unwound by ValueError thrown in at L6` / ` ~ suspended at L29 at end of recording` / ` (open)`; kind marker only for non-`function` kinds; `_caller_of` wording: `(unframed)` when `trace.format < 3`, `(no frame: started before recording)` otherwise.

- [ ] **Step 1: Tests** — rewrite the flipped tests in `tests/test_tree_frame.py`:
  - `test_tree_groups_by_task_and_names_the_real_caller` → `test_tree_groups_by_task_with_coroutine_frames`: in section `task t2: task-A`, a line `worker(name='A')  [coroutine] -> 'A:2'` exists and the `step(` lines are indented two more spaces than it; no `<- worker` anywhere; no `[coroutine, unframed]`.
  - `test_tree_unframed_count_matches_the_trace` → assert the unframed footer is ABSENT on a format-3 trace (`"unframed call(s) in this trace" not in out`).
  - `test_tree_renders_a_generator_call_under_the_frame_that_called_it` → `rows(` line shows `[generator] -> None`? No — `rows` is a generator consumed by `list()`: it returns `None` at exhaustion → tail `-> None`; `parse(` lines indented under it; no tags.
  - `test_tree_around_an_unframed_event_says_so` → `--around` on a `YIELD` event resolves to its frame (record `ASYNC_SRC`, find a YIELD event, `tree --around eN` exit 0 and prints the `worker(` line).
  - `test_tree_depth_withholds_an_unframed_call_and_counts_it`, `test_tree_limit_pins_the_page…` → keep the `--limit`/`--depth` mechanics but assert on frames (the unframed counts are 0 on format 3): `--limit 1` prints exactly one frame line and the note names `--limit 1`.
  - `test_tree_names_the_unframed_caller_of_an_unframed_call` → `test_tree_nests_an_awaited_coroutine_under_its_awaiter`: `inner(` line is indented under `amain(` and both carry `[coroutine]`.
  - ADD `test_tree_state_tails_name_cancelled_abandoned_and_suspended` using `CANCEL` and `ABANDON` from `tests/test_coroutine_frames.py` through `_rec`: asserts `~ cancelled (CancelledError thrown in at L` in task-B's section, `~ abandoned (dropped while suspended at L6)` and `~ suspended at L6 at end of recording` for the two `gen` frames.
  - In `tests/test_format2_fixture.py` ADD `test_tree_on_a_format2_trace_keeps_the_unframed_wording(installed_fixture2, capsys)`: `[coroutine, unframed]` present, `<- worker (unframed)` present, no `~ ` tails, no `[coroutine]` marker without `, unframed`.

- [ ] **Step 2–5:** implement `frame_line`:

```python
def _state_tail(trace, frame) -> str:
    s = trace.frame_state(frame)
    if s.state == "returned":
        ret = trace.event(frame.return_event_id) if frame.return_event_id else None
        return f" -> {fmt_value((ret.payload or {}).get('value'))}" if ret else " -> ?"
    if s.state == "raised":
        return f" !! {fmt_exc(frame.unwind_exc)}" if frame.unwind_exc else " !! unwound"
    if s.state == "cancelled":
        return f"  ~ cancelled ({s.exc['type']} thrown in at L{s.line})"
    if s.state == "abandoned":
        return f"  ~ abandoned (dropped while suspended at L{s.line})"
    if s.state == "thrown":
        return f"  ~ unwound by {s.exc['type']} thrown in at L{s.line}"
    if s.state == "suspended":
        return f"  ~ suspended at L{s.line} at end of recording"
    return " (open)"


def frame_line(trace, frame) -> str:
    code = trace.code(frame.code_id)
    call = trace.event(frame.call_event_id)
    args = fmt_args((call.payload or {}).get("args", {})) if call else ""
    kind = f"  [{frame.kind}]" if frame.kind != "function" else ""
    return (f"f{frame.id} e{frame.call_event_id} {code.qualname}({args}){kind}"
            f"{_state_tail(trace, frame)}" + _caller_tag(trace, frame))
```

and `_caller_of`: `why = "unframed" if trace.format < 3 else "no frame: started before recording"` → `f"  <- {qualname} ({why})"`. Update the module docstring. Run `tests/test_tree_frame.py tests/test_format1_fixture.py tests/test_format2_fixture.py`; mutations: drop the kind marker → marker test fails; return `(open)` for every state → the state-tails test fails. Commit `feat(tree): coroutine/generator frames with kind markers and derived state tails`.

---

### Task 7: `frame` — header kind+state, suspension rows in the timeline

**Files:** `src/sensorium/query/frame_cmd.py`; tests in `tests/test_tree_frame.py`, `tests/test_format2_fixture.py`.

- [ ] Tests: `frame RUN --fn worker --nth 2` on `CANCEL` (via `_rec`) → header contains `[coroutine]` and `state: cancelled at L9`, timeline contains `~ YIELD L9 awaiting Future` and `~ RESUME L9 thrown CancelledError`; on a sync frame the header is unchanged (`closed: return` stays). Format-2 fixture: `frame --fn worker` still says `recorded as 2 call(s) but not framed (coroutine)`.
- [ ] Implement: after `end = …`, `state = trace.frame_state(f)`; header: `... depth {f.depth}  closed: {f.closed_by or 'open'}` + (f"  state: {state.state}" + (f" at L{state.line}" if state.line else "")) when `f.kind != "function"` or `state.state not in ("returned","raised","open")`; kind marker `[{f.kind}]` after the qualname when not function. Timeline: `lines = [e for e in trace.frame_events(f.id) if e.kind in ("LINE","YIELD","RESUME")]` rendered by `fmt_event` with a `~ ` prefix for YIELD/RESUME; keep the "not captured" message when no LINE rows but print suspension rows regardless (`timeline (suspensions only):`). Commit `feat(frame): show kind, derived state and suspension points`.

---

### Task 8: `exceptions` — lift the under-claim; thrown-in rule

**Files:** `src/sensorium/query/exceptions_cmd.py` (docstring lines 85–91, `_unreadable_frame`, `classify` rule 2, `_swallowed` text), `tests/test_exceptions.py`, `tests/programs.py` (new shapes), `tests/test_format2_fixture.py`.

- [ ] **Tests:** `test_exceptions_refuses_to_classify_a_frameless_handler` → `test_exceptions_classifies_a_generator_handler_now_that_it_has_a_frame`: `GENERATOR_HANDLES` → `SWALLOWED` ×1 (the `int("x")` ValueError), `"no frame recorded" not in out`. New shapes in `tests/programs.py`:

```python
CORO_SWALLOW_THEN_CANCELLED = """
import asyncio
GATE = None

async def worker():
    try:
        int("x")
    except ValueError:
        pass                      # swallowed inside the coroutine
    await GATE.wait()             # then the task is cancelled here

async def amain():
    global GATE
    GATE = asyncio.Event()
    t = asyncio.create_task(worker())
    await asyncio.sleep(0)
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass

asyncio.run(amain())
"""

GEN_SWALLOW_THEN_PARKED = """
KEEP = []

def gen():
    try:
        int("x")
    except ValueError:
        yield -1                  # swallowed, then parked here for good
    yield 0

def main():
    g = gen()
    next(g)
    KEEP.append(g)

main()
"""
```

tests: `CORO_SWALLOW_THEN_CANCELLED` → a line `SWALLOWED at e` … `(frame later cancelled at L` and `dispositions: swallowed 1`, `CancelledError` RAISE classified separately (propagated/ambiguous — assert only the swallow line); `GEN_SWALLOW_THEN_PARKED` → `ambiguous` with `never closed` (the existing arm; the new under-claim pin). Format-2 fixture: `exceptions old2` still prints `no frame recorded` for the fixture's cancelled worker? (the fixture has no handler inside a coroutine — assert only that the command exits 0 and prints no `~`/state claims).
- [ ] **Implement:** in `classify` rule 2, replace `if frame is not None and frame.closed_by == "return":` with `if frame is not None and (frame.closed_by == "return" or _closed_by_thrown_in_other(trace, frame, key)):` where

```python
def _closed_by_thrown_in_other(trace, frame, key) -> bool:
    """Spec D4 rule: a frame unwound by an exception THROWN IN at a later
    RESUME (cancelled/abandoned/thrown) did not let THIS exception out --
    the handler kept it; the frame then died of something delivered after
    a YIELD. True only when that thrown exception is not this one."""
    s = trace.frame_state(frame)
    if s.state not in ("cancelled", "abandoned", "thrown") or s.exc is None:
        return False
    return exc_key(s.exc, frame.thread_id) != key
```

and `_swallowed` appends ` (frame later {state} at L{line})` when the frame's state is one of those three. `_unreadable_frame`'s `frame is None` arm: text → `"recorded by a sensorium before coroutine frames existed (format <= 2); no closed_by to read"`. Update the module docstring and README bullet later (Task 12). Update `tests/test_corpus.py::test_the_classifiers_under_claim_is_registered_somewhere` to point at the NEW corpus case `suspended_handler` (Task 11) — do it in Task 11. Commit `feat(exceptions): classify handlers inside coroutine/generator frames; thrown-in unwinds do not make an earlier handler ambiguous`.

---

### Task 9: `watch`, `info` — tests re-pointed, `info` wording

**Files:** `src/sensorium/query/info_cmd.py`; `tests/test_watch.py`, `tests/test_runs_info.py`, `tests/test_format2_fixture.py`.

- [ ] `watch`: no production change expected (`_unframed` is a join → empty on format 3). Tests: `test_watch_names_unframed_code_as_the_reason_not_a_misspelling` → `test_watch_evaluates_inside_a_focused_coroutine`: `ASYNC_WATCH` recorded with `--focus prog:worker`, `watch --at prog:worker --expr "name == 'A'"` → `HIT` present, `NOTHING WAS CHECKED` absent, `sites:` ≥ 1; `test_watch_counts_the_unframed_matches_when_only_some_are_frameless` → `ASYNC_MIXED` with `--focus prog` → worker contributes sites now: assert `"coroutine/generator code" not in out` and a normal verdict; keep `test_guidance_for_unframed_code_never_offers_a_refocus` (branch still exists for old traces). Format-2 fixture: `watch old2 --at format2_async:worker --expr "name == 'A'"` → `NOTHING WAS CHECKED` + `opens no frame in this version` (the fixture was recorded with that focus).
- [ ] `info`: `recorded:` tuple → `("CALL","RETURN","RAISE","HANDLED","YIELD","RESUME","LINE")`; the unframed line: `if t.format >= 3: print("unframed calls: 0 (all calls framed in format 3)")` else the existing line. Tests: `test_info_counts_unframed_calls_and_lists_tasks` → asserts `unframed calls: 0 (all calls framed in format 3)` and `YIELD` appears in the `recorded:` line; the fixture test asserts the old wording on `old2`. Commit `feat(info,watch): coroutine sites and counts on format-3 traces; arc-1 wording kept for older ones`.

---

### Task 10: Corpus — re-register five cases, add four

**Files:** the five existing case dirs; new `corpus/abandoned_generator/`, `corpus/suspended_handler/`, `corpus/window_across_suspension/`, `corpus/async_handler/`; `tests/test_corpus.py` (count ≥ 19; the under-claim pin moves to `suspended_handler`).

Discipline: rewrite each `questions.yaml` BEFORE running the case; record timestamps; bite-check each changed question. Rulings: Ruling 2 (format pre-flight) stands.

- [ ] **generator_swallow**: `truth` → the frame exists and `closed_by` is `return` for each handler → `dispositions: swallowed 2`; `expect_contains: ["dispositions: swallowed 2"]`; `expect_line: [["SWALLOWED at e", "parse_all"], ...×2 via expect_count {"SWALLOWED": 2}]`; `expect_absent: ["no frame recorded", "ambiguous"]`; docstring in `main.py` rewritten: "until 0.3.0 this was the honest under-claim; frames made it decidable".
- [ ] **async_cancelled**: `did-b-finish` keeps its counts, adds `expect_line [["worker()", "[coroutine]", "~ cancelled (CancelledError thrown in at L29)"]]` (the line number is the file's `await GATE.wait()` — re-verify; the tree tail names it); `whose-second-step-was-it` → `depth 1` (step is now a child of worker's frame) and the truth text updated; `where-was-b-when-cancelled` → command `frame $RUN --fn worker --nth 2` with `expect_line [["state: cancelled at L29"]]` plus keep the `exceptions` RAISE pin as a second question.
- [ ] **async_focus**: → `watch` now HITs: `expect_contains ["HIT"]`, `expect_absent ["NOTHING WAS CHECKED", "opens no frame"]`; ask/truth rewritten ("the coroutine is framed and focused; the predicate held at N sites").
- [ ] **async_interleaved**: `update` frames are children of `writer` frames: `expect_line [["writer(wait_for=", "[coroutine]"], ["update(key='last_seen', value=2)"]]`, `expect_count {"[coroutine]": 3}`, drop the `<- writer` pins; `the-winning-frame-names-its-task` → `depth 1`.
- [ ] **unframed_callers**: rename the case dir to `generator_callers` (git mv), `rows(` line `[generator]`, `parse(` lines children (indent), `expect_absent ["<- rows"]`, `rank` unchanged.
- [ ] **New `abandoned_generator`**: a generator dropped mid-iteration (planted bug: a consumer `break`s early and the cleanup in the generator's `finally` never ran … no — keep it pure: `tree` shows `~ abandoned (dropped while suspended at L<n>)`); question: "did the generator finish, and if not where was it when it was dropped?"
- [ ] **New `suspended_handler`** (the under-claim pin): `GEN_SWALLOW_THEN_PARKED` shape; `exceptions` → `dispositions: ambiguous 1`, `never closed`; `tree` → `~ suspended at L<n> at end of recording`. `tests/test_corpus.py::test_the_classifiers_under_claim_is_registered_somewhere` → asserts this case pins `"dispositions: ambiguous 1"` and `expect_absent` contains `"SWALLOWED"`.
- [ ] **New `window_across_suspension`**: `TWO_TASK_WINDOW` shape, `record: {focus: ["main:helper"], window: "windowed"}`, `watch --at main:helper --expr "x == 'out'"` → `NOT SATISFIED`/no hit for `"out"` and sites only from the windowed task (pin `sites: 2`); the `why_logs_fail`: a print in helper fires three times and cannot say which ran during the other task's suspension.
- [ ] **New `async_handler`** (field target): a FastAPI-shaped program — `async def handle(req): items = parse(req); await asyncio.sleep(0); return summarise(items)` driven by a tiny `serve()` that creates one task per request; planted bug in `summarise`; `record: {focus: ["main:handle"]}`; questions: `watch --at main:handle --expr "len(items) > 2"` HIT/verdict; `tree` shows `handle(` `[coroutine]` per task with `parse`/`summarise` children.
- [ ] Run each `--only`, then the whole corpus (19 cases), bite-checks, `tests/test_corpus.py`; commit `test(corpus): re-register five cases for coroutine frames; add abandoned, suspended-handler, window, handler cases`.

---

### Task 11: Bench `await_dense` + README + version 0.3.0 + matrix

**Files:** `corpus/_bench/bench.py`, `README.md`, `pyproject.toml`, spec status line.

- [ ] `bench.py`: add

```python
AWAIT_DENSE = '''
import asyncio

async def spin(n):
    for _ in range(n):
        await asyncio.sleep(0)

asyncio.run(spin(20000))
'''
```
registered `"await_dense": (AWAIT_DENSE, "prog:spin")` (focusable now — LINE inside the coroutine); docstring "WHY FOUR WORKLOADS": the fourth measures YIELD+RESUME per suspension. Run `--bench` on this branch and on 0.2.0 (worktree at d59cafc; the 0.2.0 table lacks the row); record both in the report.
- [ ] README: the "On an asyncio program…" paragraph → coroutine frames, states, `--focus`/`watch` inside `async def`; `### tree` second paragraph → "(a caller that started before recording)"; `### exceptions` bullet → "Generators and coroutines have frames (0.3.0); a handler inside one is classified by the same rules; a frame later unwound by a thrown-in CancelledError/GeneratorExit does not make an earlier handler ambiguous (it says `frame later cancelled at Ln`). A generator still suspended when recording stopped is `ambiguous … never closed`."; "What sensorium sees" bullet 167 → states list; `## Not yet` → drop the inside-async item, add "refocus/diff compare tasks by content (plan 2b)"; Overhead: add the `await_dense` row + one sentence with the measured per-event cost vs the 114 ns floor; Corpus: 19 cases / N questions + the new honesty cases; version `0.3.0`; spec status line → `Status: plan 2a implemented on feat/async-arc2; plan 2b pending`.
- [ ] Matrix 3.12/3.13/3.14 tests + corpus (as in arc 1 Task 12); commit `docs: inspectable coroutines (arc 2a) -- README, version 0.3.0`.

---

## Self-review

**Spec coverage:** D1 (frames for all, YIELD/RESUME/THROW events, `in_window`, retirements) → Tasks 2–5; D2 (derived states) → Task 1 (`frame_state`) + Task 4 (end-to-end) + Task 6 (rendering); D3 (format 3, fixture) → Tasks 0–1; D4 (`tree`, `frame`, `exceptions`, `watch`, `info`, `grep` via `fmt_event`) → Tasks 1, 6, 7, 8, 9; D5 (`--window` across suspension) → Task 2 + corpus `window_across_suspension`; D7 verification (re-registrations, new cases, bench, matrix) → Tasks 10–11; honesty rules 1–6 → Task 6 tails (1, 2), Task 4 fingerprint test (3), fixture tests (4), Task 8 text (5), Task 11 README (6). D6 (2b) deliberately absent — its table exists from Task 1.

**Placeholder scan:** none; Tasks 5–9 and 11 are specified by deltas + code where the surface is small, with the exact strings the tests pin. Task 10's new programs are sketched by shape where the brief's pre-registration rule requires the implementer to author the YAML before running — the facts to pin are named.

**Type consistency:** `Frame.kind: str = "function"`; `FrameState(state, line, exc)`; `Trace.frame_state(frame)`; `Trace.suspensions(fid)`; live entry `[fid, code, cid, prev_locals, depth, in_window, suspended]` (Tasks 2→4); `_classify` 6-tuple with `kind`; `TraceWriter.open_frame(..., kind="function")`; `fmt_event` YIELD/RESUME forms used by Task 7's timeline.
