# Sensorium v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build sensorium v1 — a Python execution-trace recorder (PEP 669) plus a deterministic query CLI that answers debugging questions from what actually happened, proven against a seeded-bug corpus.

**Architecture:** A recorder boots the target program in-process under `sys.monitoring` hooks and streams structured events into a per-run SQLite file. A read-only CLI answers questions from that file in dense stable text. `refocus` re-runs a recorded command with deeper capture and verifies via causal fingerprints that it witnessed the same execution.

**Tech Stack:** Python 3.12+ (developed on 3.14), stdlib only at runtime (`sys.monitoring`, `sqlite3`, `argparse`, `ast`, `runpy`). Dev: pytest, pyyaml (corpus specs), uv for env management.

**Spec:** `docs/superpowers/specs/2026-08-18-sensorium-design.md` — read it before starting. Every honesty rule in it (marked truncation, counted not-captured sites, labeled divergence, listed unwitnessed subprocesses) is a requirement, not decoration.

## Global Constraints

- Python `>= 3.12` required at runtime; the CLI refuses to run on older interpreters with a clear message.
- Runtime dependencies: **standard library only**. `pytest`/`pyyaml` are dev-only extras.
- Trace files live in `$SENSORIUM_DIR/traces/*.db` (default `~/.sensorium/traces/`). All tests and the corpus set `SENSORIUM_DIR` to a temp dir — never write to the real store from tests.
- Event ordering ground truth is the monotonic event id; wall-clock ns is carried but never used for ordering.
- Fingerprints hash only `(file, qualname, kind)` for kinds CALL/RETURN/RAISE/HANDLED. LINE events and captured values are **never** fingerprinted (capture depth must not alter the fingerprint).
- Every truncated capture is marked (`"trunc": true`) and counted; every "I don't have that" is reported, never silently skipped.
- No model, no network, no interactivity in any command. Output is plain ASCII text; `--json` is out of scope for v1 tasks below except where noted (YAGNI — add when a consumer needs it).
- Control-flow exceptions (`StopIteration`, `StopAsyncIteration`, `GeneratorExit`) are excluded from RAISE/HANDLED recording.
- Generator/coroutine/async-generator code objects are recorded as events but never opened as frames in v1 (async attribution is out of scope per spec).
- Conventional commits (`feat:`, `test:`, `docs:`, `chore:`). No attribution trailers.
- Files stay under 800 lines; functions focused and small.
- Repo root for all commands below: `~/workspace/sensorium`. Test runner: `.venv/bin/pytest`.

## File Structure

```
sensorium/
├── pyproject.toml                  # package metadata, console script, dev extras
├── .gitignore
├── README.md                       # Task 17
├── src/sensorium/
│   ├── __init__.py
│   ├── __main__.py                 # python -m sensorium
│   ├── paths.py                    # trace dir, run ids, run-ref resolution
│   ├── cli.py                      # argparse wiring; grows one import per query task
│   ├── store/
│   │   ├── __init__.py
│   │   ├── db.py                   # schema DDL, create/open, meta key-value access
│   │   ├── writer.py               # TraceWriter: batched, thread-safe, WAL
│   │   └── reader.py               # Trace + Code/Event/Frame dataclasses
│   ├── record/
│   │   ├── __init__.py
│   │   ├── capture.py              # structured value capture, caps, marked truncation
│   │   ├── fingerprint.py          # per-thread causal rolling hash
│   │   ├── tracer.py               # sys.monitoring hooks, FocusSpec, tiers, window
│   │   └── boot.py                 # target resolution, in-process exec, run metadata
│   └── query/
│       ├── __init__.py
│       ├── fmt.py                  # fmt_value/fmt_args/fmt_event/fmt_exc, windows
│       ├── expr.py                 # restricted predicate evaluator (ast-based)
│       ├── runs_cmd.py  info_cmd.py  tree_cmd.py  frame_cmd.py
│       ├── grep_cmd.py  exceptions_cmd.py  flow_cmd.py  watch_cmd.py
│       ├── diff_cmd.py  refocus_cmd.py
├── corpus/
│   ├── run_corpus.py               # record + answer + verify + overhead report
│   ├── _bench/bench.py             # overhead micro-benchmark (self-timing)
│   └── <program>/{main.py, questions.yaml}   # 10 seeded-bug programs
├── tests/
│   ├── helpers.py                  # load_module, record_inproc, run_cli, record_script
│   └── test_*.py                   # one file per task area
└── docs/superpowers/{specs,plans}/
```

Import layering (no cycles): `paths` and `store/db` at the bottom; `record/*` depends on `store/writer`; `query/*` depends on `store/reader` + `fmt`/`expr`; `cli` on top. `refocus_cmd` reuses `diff_cmd.first_divergence` and `record/boot.git_info`.

---

### Task 1: Scaffold, trace schema, and paths

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/sensorium/__init__.py`, `src/sensorium/store/__init__.py`, `src/sensorium/record/__init__.py`, `src/sensorium/query/__init__.py`, `src/sensorium/store/db.py`, `src/sensorium/paths.py`
- Test: `tests/test_store_db.py`, `tests/test_paths.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `db.create_trace(path) -> sqlite3.Connection`, `db.open_trace(path)`, `db.set_meta(conn, key, value)`, `db.get_meta(conn, key, default=None)`, `db.all_meta(conn) -> dict` (values JSON-encoded in a `meta` key/value table); tables `meta`, `code_objects(id,file,qualname,firstlineno)`, `frames(id,parent_id,code_id,call_event_id,return_event_id,depth,thread_id,closed_by,unwind_exc)`, `events(id,ts_ns,thread_id,kind,frame_id,code_id,line,payload)`, `output(id,after_event_id,stream,data)`, `fingerprints(thread_id,hash,n_events)`. `paths.trace_root()`, `paths.traces_dir()`, `paths.new_run_id() -> str`, `paths.find_trace(ref: str) -> Path`, `paths.TraceLookupError`.

- [ ] **Step 1: Create environment and package skeleton**

```bash
cd ~/workspace/sensorium
python3 --version   # must be >= 3.12 (box has 3.14.4)
mkdir -p src/sensorium/{store,record,query} tests corpus
touch src/sensorium/__init__.py src/sensorium/store/__init__.py \
      src/sensorium/record/__init__.py src/sensorium/query/__init__.py
```

Write `pyproject.toml`:

```toml
[project]
name = "sensorium"
version = "0.1.0"
description = "Execution-trace recorder and LLM-native query CLI for Python programs"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8", "pyyaml>=6", "pytest-cov>=5"]

[project.scripts]
sensorium = "sensorium.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sensorium"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Write `.gitignore`:

```
.venv/
__pycache__/
*.egg-info/
.pytest_cache/
.coverage
```

Then:

```bash
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"
```

- [ ] **Step 2: Write failing tests for db and paths**

`tests/test_store_db.py`:

```python
import sqlite3

from sensorium.store import db


def test_create_trace_has_all_tables(tmp_path):
    conn = db.create_trace(tmp_path / "t.db")
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"meta", "code_objects", "frames", "events", "output",
            "fingerprints"} <= names
    assert db.get_meta(conn, "trace_format") == 1


def test_meta_roundtrip_preserves_types(tmp_path):
    conn = db.create_trace(tmp_path / "t.db")
    db.set_meta(conn, "argv", ["prog.py", "--x"])
    db.set_meta(conn, "incomplete", True)
    db.set_meta(conn, "exit_status", 3)
    conn.commit()
    assert db.get_meta(conn, "argv") == ["prog.py", "--x"]
    assert db.get_meta(conn, "incomplete") is True
    assert db.all_meta(conn)["exit_status"] == 3
    assert db.get_meta(conn, "missing", "d") == "d"


def test_open_trace_missing_file_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        db.open_trace(tmp_path / "nope.db")
```

`tests/test_paths.py`:

```python
import pytest

from sensorium import paths
from sensorium.store import db


def _mk(tmp_path, monkeypatch, names):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    for n in names:
        db.create_trace(paths.traces_dir() / f"{n}.db").close()


def test_find_by_unique_prefix(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch, ["20260818-1200-aaa111", "20260818-1300-bbb222"])
    assert paths.find_trace("20260818-13").name == "20260818-1300-bbb222.db"


def test_ambiguous_prefix_names_candidates(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch, ["20260818-1200-aaa111", "20260818-1300-bbb222"])
    with pytest.raises(paths.TraceLookupError, match="ambiguous"):
        paths.find_trace("20260818")


def test_last_picks_newest(tmp_path, monkeypatch):
    import os, time
    _mk(tmp_path, monkeypatch, ["a-run", "b-run"])
    t = time.time()
    os.utime(paths.traces_dir() / "a-run.db", (t + 60, t + 60))
    assert paths.find_trace("last").name == "a-run.db"


def test_no_traces_is_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    with pytest.raises(paths.TraceLookupError, match="no traces"):
        paths.find_trace("last")


def test_run_ids_unique():
    assert paths.new_run_id() != paths.new_run_id()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_store_db.py tests/test_paths.py -v`
Expected: FAIL — `ModuleNotFoundError` / `AttributeError` (modules don't exist yet).

- [ ] **Step 4: Implement `src/sensorium/store/db.py`**

```python
"""Trace file creation, opening, and run-metadata access."""
import json
import sqlite3
from pathlib import Path

TRACE_FORMAT = 1

SCHEMA = """
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE code_objects (
  id INTEGER PRIMARY KEY,
  file TEXT NOT NULL,
  qualname TEXT NOT NULL,
  firstlineno INTEGER NOT NULL
);
CREATE TABLE frames (
  id INTEGER PRIMARY KEY,
  parent_id INTEGER,
  code_id INTEGER NOT NULL,
  call_event_id INTEGER NOT NULL,
  return_event_id INTEGER,
  depth INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  closed_by TEXT,
  unwind_exc TEXT
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts_ns INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  frame_id INTEGER,
  code_id INTEGER,
  line INTEGER,
  payload TEXT
);
CREATE TABLE output (
  id INTEGER PRIMARY KEY,
  after_event_id INTEGER NOT NULL,
  stream TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE fingerprints (
  thread_id INTEGER PRIMARY KEY,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
CREATE INDEX idx_events_code ON events(code_id);
CREATE INDEX idx_events_frame ON events(frame_id);
CREATE INDEX idx_events_kind ON events(kind);
CREATE INDEX idx_frames_code ON frames(code_id);
"""


def create_trace(path: Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    set_meta(conn, "trace_format", TRACE_FORMAT)
    conn.commit()
    return conn


def open_trace(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no trace at {path}")
    return sqlite3.connect(path)


def set_meta(conn: sqlite3.Connection, key: str, value) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, json.dumps(value, separators=(",", ":"))),
    )


def get_meta(conn: sqlite3.Connection, key: str, default=None):
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return default if row is None else json.loads(row[0])


def all_meta(conn: sqlite3.Connection) -> dict:
    return {k: json.loads(v)
            for k, v in conn.execute("SELECT key, value FROM meta")}
```

- [ ] **Step 5: Implement `src/sensorium/paths.py`**

```python
"""Trace directory location, run ids, and run-reference resolution."""
import os
import time
import uuid
from pathlib import Path


class TraceLookupError(Exception):
    pass


def trace_root() -> Path:
    return Path(os.environ.get("SENSORIUM_DIR") or Path.home() / ".sensorium")


def traces_dir() -> Path:
    d = trace_root() / "traces"
    d.mkdir(parents=True, exist_ok=True)
    return d


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]


def find_trace(ref: str) -> Path:
    files = sorted(traces_dir().glob("*.db"))
    if not files:
        raise TraceLookupError("no traces recorded yet")
    if ref == "last":
        return max(files, key=lambda p: p.stat().st_mtime)
    hits = [p for p in files if p.stem.startswith(ref)]
    if not hits:
        raise TraceLookupError(f"no trace matches {ref!r}")
    if len(hits) > 1:
        names = ", ".join(p.stem for p in hits)
        raise TraceLookupError(f"{ref!r} is ambiguous: {names}")
    return hits[0]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_store_db.py tests/test_paths.py -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml .gitignore src tests
git commit -m "feat: project scaffold, trace schema, and run-path resolution"
```

---

### Task 2: Structured value capture

**Files:**
- Create: `src/sensorium/record/capture.py`
- Test: `tests/test_capture.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `CAPS = {"str": 200, "repr": 200, "sample": 8, "depth": 3}`; `capture_stats = {"truncated": 0}` (module-level counter, reset per process); `capture_value(obj, depth=0) -> dict` returning one of `{"k":"none"}`, `{"k":"bool","v":b}`, `{"k":"num","v":n}`, `{"k":"str","v":s[,"trunc":true]}`, `{"k":"seq","type":t,"len":n,"oid":i,"sample":[...][,"trunc":true]}`, `{"k":"map","type":t,"len":n,"oid":i,"sample":[[k,v],...][,"trunc":true]}`, `{"k":"obj","type":t,"oid":i,"repr":r[,"trunc":true]}`; `capture_exc(exc) -> {"type","msg","oid"}`. `oid` on seq/map/obj enables same-object provenance (`flow --object`).

- [ ] **Step 1: Write failing tests**

`tests/test_capture.py`:

```python
from sensorium.record.capture import CAPS, capture_exc, capture_stats, capture_value


def test_primitives_stored_natively():
    assert capture_value(42) == {"k": "num", "v": 42}
    assert capture_value(2.5) == {"k": "num", "v": 2.5}
    assert capture_value(True) == {"k": "bool", "v": True}
    assert capture_value(None) == {"k": "none"}
    assert capture_value("hi") == {"k": "str", "v": "hi"}


def test_long_string_truncated_and_marked():
    before = capture_stats["truncated"]
    v = capture_value("x" * 500)
    assert v["trunc"] is True and len(v["v"]) == CAPS["str"]
    assert capture_stats["truncated"] == before + 1


def test_large_list_keeps_len_and_capped_sample():
    v = capture_value(list(range(1000)))
    assert v["k"] == "seq" and v["len"] == 1000 and v["trunc"] is True
    assert len(v["sample"]) == CAPS["sample"]
    assert v["sample"][0] == {"k": "num", "v": 0}
    assert isinstance(v["oid"], int)


def test_dict_sample_pairs():
    v = capture_value({"a": 1, "b": 2})
    assert v["k"] == "map" and v["len"] == 2 and "trunc" not in v
    assert v["sample"][0] == [{"k": "str", "v": "a"}, {"k": "num", "v": 1}]


def test_object_has_oid_and_capped_repr():
    class Grid:
        def __repr__(self):
            return "<Grid " + "y" * 500 + ">"
    g = Grid()
    v = capture_value(g)
    assert v["k"] == "obj" and v["type"] == "Grid" and v["oid"] == id(g)
    assert len(v["repr"]) == CAPS["repr"] and v["trunc"] is True


def test_hostile_repr_is_guarded():
    class Bomb:
        def __repr__(self):
            raise RuntimeError("boom")
    v = capture_value(Bomb())
    assert v["k"] == "obj" and "repr-raised" in v["repr"] and v["trunc"] is True


def test_recursive_structure_stops_at_depth_cap():
    l: list = []
    l.append(l)
    v = capture_value(l)          # must not RecursionError
    assert v["k"] == "seq"


def test_capture_exc():
    e = ValueError("bad amount")
    assert capture_exc(e) == {"type": "ValueError", "msg": "bad amount",
                              "oid": id(e)}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_capture.py -v` — Expected: FAIL (module missing).

- [ ] **Step 3: Implement `src/sensorium/record/capture.py`**

```python
"""Structured value capture with hard caps and marked truncation.

Captures may be smaller than the real value; they are never silently so:
anything cut carries "trunc": true and bumps capture_stats["truncated"].
"""
from itertools import islice

CAPS = {"str": 200, "repr": 200, "sample": 8, "depth": 3}

capture_stats = {"truncated": 0}


def _trunc_str(s: str, cap: int) -> tuple[str, bool]:
    if len(s) <= cap:
        return s, False
    capture_stats["truncated"] += 1
    return s[:cap], True


def capture_value(obj, depth: int = 0) -> dict:
    if obj is None:
        return {"k": "none"}
    if isinstance(obj, bool):
        return {"k": "bool", "v": obj}
    if isinstance(obj, (int, float)):
        return {"k": "num", "v": obj}
    if isinstance(obj, str):
        s, t = _trunc_str(obj, CAPS["str"])
        out = {"k": "str", "v": s}
        if t:
            out["trunc"] = True
        return out
    if isinstance(obj, (list, tuple, set, frozenset)):
        return _capture_sized(obj, depth, "seq",
                              lambda o, d: [capture_value(x, d)
                                            for x in islice(iter(o), CAPS["sample"])])
    if isinstance(obj, dict):
        return _capture_sized(obj, depth, "map",
                              lambda o, d: [[capture_value(k, d), capture_value(v, d)]
                                            for k, v in islice(o.items(), CAPS["sample"])])
    return _capture_obj(obj)


def _capture_sized(obj, depth, kind, sampler) -> dict:
    out = {"k": kind, "type": type(obj).__name__, "len": len(obj), "oid": id(obj)}
    if depth >= CAPS["depth"]:
        out["trunc"] = True
        capture_stats["truncated"] += 1
        return out
    out["sample"] = sampler(obj, depth + 1)
    if len(obj) > CAPS["sample"]:
        out["trunc"] = True
        capture_stats["truncated"] += 1
    return out


def _capture_obj(obj) -> dict:
    out = {"k": "obj", "type": type(obj).__name__, "oid": id(obj)}
    try:
        r = repr(obj)
    except BaseException:
        r = f"<{type(obj).__name__} repr-raised>"
        out["trunc"] = True
        capture_stats["truncated"] += 1
    s, t = _trunc_str(r, CAPS["repr"])
    out["repr"] = s
    if t:
        out["trunc"] = True
    return out


def capture_exc(exc: BaseException) -> dict:
    msg, _ = _trunc_str(str(exc), CAPS["str"])
    return {"type": type(exc).__name__, "msg": msg, "oid": id(exc)}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_capture.py -v` — Expected: all PASS. Note the depth-cap test: recursion is bounded because `_capture_sized` stops sampling at `CAPS["depth"]`.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/record/capture.py tests/test_capture.py
git commit -m "feat: structured value capture with caps and marked truncation"
```

---

### Task 3: Causal fingerprints

**Files:**
- Create: `src/sensorium/record/fingerprint.py`
- Test: `tests/test_fingerprint.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `CAUSAL_KINDS = ("CALL", "RETURN", "RAISE", "HANDLED")`; `class Fingerprint` with `update(file: str, qualname: str, kind: str) -> None`, `hexdigest() -> str`, attribute `count: int`. The tracer (Task 6) calls `update` only for `CAUSAL_KINDS`; the reader (Task 5) exposes stored fingerprints; refocus (Task 15) compares them.

- [ ] **Step 1: Write failing tests**

`tests/test_fingerprint.py`:

```python
from sensorium.record.fingerprint import CAUSAL_KINDS, Fingerprint


def _fp(seq):
    f = Fingerprint()
    for item in seq:
        f.update(*item)
    return f


def test_same_sequence_same_digest():
    seq = [("/a.py", "f", "CALL"), ("/a.py", "f", "RETURN")]
    assert _fp(seq).hexdigest() == _fp(seq).hexdigest()
    assert _fp(seq).count == 2


def test_order_matters():
    a = [("/a.py", "f", "CALL"), ("/a.py", "g", "CALL")]
    assert _fp(a).hexdigest() != _fp(list(reversed(a))).hexdigest()


def test_kind_matters():
    assert (_fp([("/a.py", "f", "CALL")]).hexdigest()
            != _fp([("/a.py", "f", "RETURN")]).hexdigest())


def test_no_separator_collision():
    # ("ab","c") must not hash equal to ("a","bc")
    assert (_fp([("ab", "c", "CALL")]).hexdigest()
            != _fp([("a", "bc", "CALL")]).hexdigest())


def test_line_not_a_causal_kind():
    assert "LINE" not in CAUSAL_KINDS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_fingerprint.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/record/fingerprint.py`**

```python
"""Per-thread causal fingerprints: a rolling hash over the (code, kind)
sequence. Values, timing, and LINE events are deliberately excluded so
capture depth can never alter the fingerprint (spec section 4)."""
import hashlib

CAUSAL_KINDS = ("CALL", "RETURN", "RAISE", "HANDLED")


class Fingerprint:
    def __init__(self) -> None:
        self._h = hashlib.blake2b(digest_size=16)
        self.count = 0

    def update(self, file: str, qualname: str, kind: str) -> None:
        self._h.update(f"{file}\x1f{qualname}\x1f{kind}\n".encode())
        self.count += 1

    def hexdigest(self) -> str:
        return self._h.hexdigest()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_fingerprint.py -v` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/record/fingerprint.py tests/test_fingerprint.py
git commit -m "feat: per-thread causal fingerprints"
```

---

### Task 4: TraceWriter — batched, thread-safe writes

**Files:**
- Create: `src/sensorium/store/writer.py`
- Test: `tests/test_writer.py`

**Interfaces:**
- Consumes: `store.db.create_trace`, `db.set_meta`.
- Produces: `class TraceWriter(path, batch=512)` with: property `last_event_id: int`; `intern_code(file, qualname, firstlineno) -> int`; `add_event(ts_ns, thread_id, kind, frame_id, code_id, line, payload: dict | None) -> int` (auto-flushes every `batch` events); `open_frame(parent_id, code_id, call_event_id, depth, thread_id) -> int`; `close_frame(frame_id, return_event_id=None, closed_by="return", unwind_exc=None)`; `add_output(after_event_id, stream, data)`; `set_meta(key, value)` (immediate commit); `write_fingerprint(thread_id, hexdigest, count)`; `flush()`; `close()`; attribute `path`. All methods are safe to call from any thread. Event ids start at 1 and are monotonic across threads.

- [ ] **Step 1: Write failing tests**

`tests/test_writer.py`:

```python
import sqlite3

from sensorium.store.writer import TraceWriter


def test_roundtrip_events_frames_output(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=100)
    cid = w.intern_code("/x/prog.py", "add", 1)
    assert w.intern_code("/x/prog.py", "add", 1) == cid  # interned once
    e1 = w.add_event(10, 7, "CALL", None, cid, 1, {"args": {}})
    fid = w.open_frame(None, cid, e1, 0, 7)
    e2 = w.add_event(20, 7, "RETURN", fid, cid, None,
                     {"value": {"k": "num", "v": 5}})
    w.close_frame(fid, e2, "return")
    w.add_output(e2, "stdout", "hello\n")
    w.write_fingerprint(7, "abc123", 2)
    w.close()

    c = sqlite3.connect(p)
    assert c.execute("SELECT COUNT(*) FROM code_objects").fetchone()[0] == 1
    ev = c.execute("SELECT id, kind, frame_id FROM events ORDER BY id").fetchall()
    assert ev == [(e1, "CALL", None), (e2, "RETURN", fid)]
    fr = c.execute(
        "SELECT return_event_id, closed_by FROM frames WHERE id=?", (fid,)
    ).fetchone()
    assert fr == (e2, "return")
    assert c.execute("SELECT data FROM output").fetchone()[0] == "hello\n"
    assert c.execute("SELECT hash FROM fingerprints").fetchone()[0] == "abc123"


def test_event_ids_monotonic_and_last_event_id(tmp_path):
    w = TraceWriter(tmp_path / "t.db")
    cid = w.intern_code("/x.py", "f", 1)
    ids = [w.add_event(i, 1, "CALL", None, cid, 1, None) for i in range(5)]
    assert ids == [1, 2, 3, 4, 5] and w.last_event_id == 5
    w.close()


def test_partial_trace_valid_without_close(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=2)          # tiny batch forces auto-flush
    cid = w.intern_code("/x.py", "f", 1)
    for i in range(5):
        w.add_event(i, 1, "CALL", None, cid, 1, None)
    # no close(): simulate a killed process; flushed batches must be readable
    c = sqlite3.connect(p)
    n = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert n >= 4                        # two full batches guaranteed flushed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_writer.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/store/writer.py`**

```python
"""Batched, thread-safe writer for trace files. Buffers rows in memory and
flushes in one transaction per batch; on an unclean death, everything
already flushed is a valid partial trace."""
import json
import threading
from pathlib import Path

from sensorium.store import db


class TraceWriter:
    def __init__(self, path: Path, batch: int = 512) -> None:
        self.path = Path(path)
        self._conn = db.create_trace(self.path)
        self._lock = threading.Lock()
        self._batch = batch
        self._events: list[tuple] = []
        self._frames: list[tuple] = []
        self._closes: list[tuple] = []
        self._outputs: list[tuple] = []
        self._codes: dict[tuple, int] = {}
        self._new_codes: list[tuple] = []
        self._next_event = 1
        self._next_frame = 1

    @property
    def last_event_id(self) -> int:
        return self._next_event - 1

    def intern_code(self, file: str, qualname: str, firstlineno: int) -> int:
        key = (file, qualname, firstlineno)
        with self._lock:
            cid = self._codes.get(key)
            if cid is None:
                cid = len(self._codes) + 1
                self._codes[key] = cid
                self._new_codes.append((cid, file, qualname, firstlineno))
            return cid

    def add_event(self, ts_ns, thread_id, kind, frame_id, code_id, line,
                  payload: dict | None) -> int:
        p = (None if payload is None
             else json.dumps(payload, separators=(",", ":"), default=repr))
        with self._lock:
            eid = self._next_event
            self._next_event += 1
            self._events.append(
                (eid, ts_ns, thread_id, kind, frame_id, code_id, line, p))
            if len(self._events) >= self._batch:
                self._flush_locked()
            return eid

    def open_frame(self, parent_id, code_id, call_event_id, depth,
                   thread_id) -> int:
        with self._lock:
            fid = self._next_frame
            self._next_frame += 1
            self._frames.append(
                (fid, parent_id, code_id, call_event_id, depth, thread_id))
            return fid

    def close_frame(self, frame_id, return_event_id=None, closed_by="return",
                    unwind_exc: dict | None = None) -> None:
        exc = (None if unwind_exc is None
               else json.dumps(unwind_exc, separators=(",", ":")))
        with self._lock:
            self._closes.append((return_event_id, closed_by, exc, frame_id))

    def add_output(self, after_event_id, stream, data) -> None:
        with self._lock:
            self._outputs.append((after_event_id, stream, data))

    def set_meta(self, key, value) -> None:
        with self._lock:
            db.set_meta(self._conn, key, value)
            self._conn.commit()

    def write_fingerprint(self, thread_id, hexdigest, count) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO fingerprints "
                "(thread_id, hash, n_events) VALUES (?, ?, ?)",
                (thread_id, hexdigest, count))
            self._conn.commit()

    def _flush_locked(self) -> None:
        c = self._conn
        if self._new_codes:
            c.executemany("INSERT INTO code_objects VALUES (?, ?, ?, ?)",
                          self._new_codes)
            self._new_codes.clear()
        if self._frames:
            c.executemany(
                "INSERT INTO frames (id, parent_id, code_id, call_event_id, "
                "depth, thread_id) VALUES (?, ?, ?, ?, ?, ?)", self._frames)
            self._frames.clear()
        if self._events:
            c.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          self._events)
            self._events.clear()
        if self._closes:
            c.executemany(
                "UPDATE frames SET return_event_id = ?, closed_by = ?, "
                "unwind_exc = ? WHERE id = ?", self._closes)
            self._closes.clear()
        if self._outputs:
            c.executemany(
                "INSERT INTO output (after_event_id, stream, data) "
                "VALUES (?, ?, ?)", self._outputs)
            self._outputs.clear()
        c.commit()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def close(self) -> None:
        with self._lock:
            self._flush_locked()
            self._conn.close()
```

Flush order inside a batch is codes → frames → events → closes → outputs, so a close-update never races the insert of the frame it targets.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_writer.py -v` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/store/writer.py tests/test_writer.py
git commit -m "feat: batched thread-safe trace writer with crash-valid partial traces"
```

---

### Task 5: Trace reader

**Files:**
- Create: `src/sensorium/store/reader.py`
- Test: `tests/test_reader.py`

**Interfaces:**
- Consumes: `store.db.open_trace`, `db.all_meta`; fixture traces built with `TraceWriter`.
- Produces: frozen dataclasses `Code(id, file, qualname, firstlineno)`, `Event(id, ts_ns, thread_id, kind, frame_id, code_id, line, payload)` (payload decoded to dict or None), `Frame(id, parent_id, code_id, call_event_id, return_event_id, depth, thread_id, closed_by, unwind_exc)`; `class Trace` with `Trace.open(path) -> Trace`, property `meta: dict`, `codes() -> list[Code]`, `code(code_id) -> Code`, `events(kind=None, code_id=None, frame_id=None, after=0, limit=None) -> list[Event]` (kind may be a str or tuple), `event(eid) -> Event | None`, `frames(code_id=None) -> list[Frame]`, `frame(fid) -> Frame | None`, `children(fid) -> list[Frame]`, `roots() -> list[Frame]`, `frame_events(fid) -> list[Event]`, `counts() -> dict[str, int]`, `fingerprints() -> dict[int, tuple[str, int]]`, `output_chunks() -> list[tuple[int, str, str]]`, `main_thread_id() -> int | None` (thread of event 1), `causal_stream(thread_id=None) -> list[tuple[str, str, str, int]]` ((file, qualname, kind, event_id) for CAUSAL_KINDS on the main thread by default), `frame_containing(eid) -> Frame | None` (falls back to `frames.call_event_id` because CALL events carry `frame_id=NULL`).

- [ ] **Step 1: Write failing tests**

`tests/test_reader.py` — build a small trace with `TraceWriter`, read it back:

```python
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter


def _fixture(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p)
    main = w.intern_code("/x/prog.py", "main", 1)
    add = w.intern_code("/x/prog.py", "add", 5)
    e1 = w.add_event(10, 7, "CALL", None, main, 1, {"args": {}})
    f1 = w.open_frame(None, main, e1, 0, 7)
    e2 = w.add_event(20, 7, "CALL", None, add, 5,
                     {"args": {"a": {"k": "num", "v": 2}}})
    f2 = w.open_frame(f1, add, e2, 1, 7)
    e3 = w.add_event(30, 7, "RETURN", f2, add, None,
                     {"value": {"k": "num", "v": 5}})
    w.close_frame(f2, e3, "return")
    e4 = w.add_event(40, 7, "RETURN", f1, main, None,
                     {"value": {"k": "none"}})
    w.close_frame(f1, e4, "return")
    w.set_meta("run_id", "r1")
    w.write_fingerprint(7, "aa", 4)
    w.close()
    return Trace.open(p), (e1, f1, e2, f2, e3, e4)


def test_meta_codes_events(tmp_path):
    t, (e1, f1, e2, f2, e3, e4) = _fixture(tmp_path)
    assert t.meta["run_id"] == "r1"
    assert {c.qualname for c in t.codes()} == {"main", "add"}
    assert [e.kind for e in t.events()] == ["CALL", "CALL", "RETURN", "RETURN"]
    assert t.event(e3).payload == {"value": {"k": "num", "v": 5}}
    assert len(t.events(kind="CALL")) == 2
    assert len(t.events(kind=("CALL", "RETURN"), after=e2)) == 2
    assert len(t.events(limit=3)) == 3


def test_frames_tree_navigation(tmp_path):
    t, (e1, f1, e2, f2, e3, e4) = _fixture(tmp_path)
    assert [f.id for f in t.roots()] == [f1]
    assert [f.id for f in t.children(f1)] == [f2]
    assert t.frame(f2).return_event_id == e3
    assert t.frame(f2).closed_by == "return"
    add_code = next(c for c in t.codes() if c.qualname == "add")
    assert [f.id for f in t.frames(code_id=add_code.id)] == [f2]
    assert [e.id for e in t.frame_events(f2)] == [e3]


def test_frame_containing_falls_back_to_call_event(tmp_path):
    t, (e1, f1, e2, f2, e3, e4) = _fixture(tmp_path)
    assert t.frame_containing(e2).id == f2   # CALL event: via call_event_id
    assert t.frame_containing(e3).id == f2   # RETURN event: via frame_id


def test_causal_stream_and_counts(tmp_path):
    t, ids = _fixture(tmp_path)
    assert t.main_thread_id() == 7
    stream = t.causal_stream()
    assert [(q, k) for _, q, k, _ in stream] == [
        ("main", "CALL"), ("add", "CALL"), ("add", "RETURN"),
        ("main", "RETURN")]
    assert t.counts() == {"CALL": 2, "RETURN": 2}
    assert t.fingerprints() == {7: ("aa", 4)}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_reader.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/store/reader.py`**

```python
"""Read-side access to trace files."""
import json
from dataclasses import dataclass
from pathlib import Path

from sensorium.record.fingerprint import CAUSAL_KINDS
from sensorium.store import db


@dataclass(frozen=True)
class Code:
    id: int
    file: str
    qualname: str
    firstlineno: int


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


_FRAME_COLS = ("id, parent_id, code_id, call_event_id, return_event_id, "
               "depth, thread_id, closed_by, unwind_exc")
_EVENT_COLS = "id, ts_ns, thread_id, kind, frame_id, code_id, line, payload"


def _loads(s):
    return None if s is None else json.loads(s)


def _frame(row) -> Frame:
    return Frame(*row[:8], _loads(row[8]))


def _event(row) -> Event:
    return Event(*row[:7], _loads(row[7]))


class Trace:
    def __init__(self, conn, path: Path) -> None:
        self._c = conn
        self.path = path
        self._code_cache: dict[int, Code] | None = None

    @classmethod
    def open(cls, path: Path) -> "Trace":
        return cls(db.open_trace(path), Path(path))

    @property
    def meta(self) -> dict:
        return db.all_meta(self._c)

    def codes(self) -> list[Code]:
        if self._code_cache is None:
            self._code_cache = {r[0]: Code(*r) for r in self._c.execute(
                "SELECT id, file, qualname, firstlineno FROM code_objects")}
        return list(self._code_cache.values())

    def code(self, code_id: int) -> Code:
        self.codes()
        return self._code_cache[code_id]

    def events(self, kind=None, code_id=None, frame_id=None, after=0,
               limit=None) -> list[Event]:
        q = f"SELECT {_EVENT_COLS} FROM events WHERE id > ?"
        params: list = [after]
        if kind is not None:
            kinds = (kind,) if isinstance(kind, str) else tuple(kind)
            q += f" AND kind IN ({','.join('?' * len(kinds))})"
            params += list(kinds)
        if code_id is not None:
            q += " AND code_id = ?"
            params.append(code_id)
        if frame_id is not None:
            q += " AND frame_id = ?"
            params.append(frame_id)
        q += " ORDER BY id"
        if limit is not None:
            q += " LIMIT ?"
            params.append(limit)
        return [_event(r) for r in self._c.execute(q, params)]

    def event(self, eid: int) -> Event | None:
        row = self._c.execute(
            f"SELECT {_EVENT_COLS} FROM events WHERE id = ?", (eid,)).fetchone()
        return None if row is None else _event(row)

    def frames(self, code_id=None) -> list[Frame]:
        q = f"SELECT {_FRAME_COLS} FROM frames"
        params: tuple = ()
        if code_id is not None:
            q += " WHERE code_id = ?"
            params = (code_id,)
        return [_frame(r) for r in self._c.execute(q + " ORDER BY id", params)]

    def frame(self, fid: int) -> Frame | None:
        row = self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE id = ?", (fid,)).fetchone()
        return None if row is None else _frame(row)

    def children(self, fid: int) -> list[Frame]:
        return [_frame(r) for r in self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE parent_id = ? "
            "ORDER BY id", (fid,))]

    def roots(self) -> list[Frame]:
        return [_frame(r) for r in self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE parent_id IS NULL "
            "ORDER BY id")]

    def frame_events(self, fid: int) -> list[Event]:
        return self.events(frame_id=fid)

    def counts(self) -> dict[str, int]:
        return dict(self._c.execute(
            "SELECT kind, COUNT(*) FROM events GROUP BY kind"))

    def fingerprints(self) -> dict[int, tuple[str, int]]:
        return {tid: (h, n) for tid, h, n in self._c.execute(
            "SELECT thread_id, hash, n_events FROM fingerprints")}

    def output_chunks(self) -> list[tuple[int, str, str]]:
        return list(self._c.execute(
            "SELECT after_event_id, stream, data FROM output ORDER BY id"))

    def main_thread_id(self) -> int | None:
        row = self._c.execute(
            "SELECT thread_id FROM events ORDER BY id LIMIT 1").fetchone()
        return None if row is None else row[0]

    def causal_stream(self, thread_id=None) -> list[tuple[str, str, str, int]]:
        tid = thread_id if thread_id is not None else self.main_thread_id()
        marks = ",".join("?" * len(CAUSAL_KINDS))
        out = []
        for eid, cid, kind in self._c.execute(
                f"SELECT id, code_id, kind FROM events "
                f"WHERE thread_id = ? AND kind IN ({marks}) ORDER BY id",
                (tid, *CAUSAL_KINDS)):
            c = self.code(cid)
            out.append((c.file, c.qualname, kind, eid))
        return out

    def frame_containing(self, eid: int) -> Frame | None:
        ev = self.event(eid)
        if ev is None:
            return None
        if ev.frame_id is not None:
            return self.frame(ev.frame_id)
        row = self._c.execute(
            f"SELECT {_FRAME_COLS} FROM frames WHERE call_event_id = ?",
            (eid,)).fetchone()
        return None if row is None else _frame(row)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_reader.py -v` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/store/reader.py tests/test_reader.py
git commit -m "feat: trace reader with frame/event/causal-stream navigation"
```

---

### Task 6: Tracer — default tier (CALL/RETURN/RAISE/HANDLED)

**Files:**
- Create: `src/sensorium/record/tracer.py`, `tests/helpers.py`
- Test: `tests/test_tracer.py`

**Interfaces:**
- Consumes: `TraceWriter`, `capture_value`/`capture_exc`, `Fingerprint`, `Trace` (in tests).
- Produces: `module_name_for(file: str, root: Path) -> str | None`; `class FocusSpec(entries: list[str])` with `matches(module, qualname) -> bool` and truthiness; `class Tracer(writer, root, focus, include=(), exclude=(), window=None)` with `install()` / `uninstall()`. Behavior contract: CALL events carry `frame_id=NULL` and `payload={"args": {...}}`; frames link via `call_event_id`. RETURN carries `payload={"value": ...}`. RAISE/HANDLED carry `payload={"exc": {...}}` and skip control-flow exceptions. Uncaught propagation closes frames with `closed_by="unwind"` + `unwind_exc`. Generator/coroutine code objects (`co_flags & 0x2a0`) get CALL/RETURN events but no frames. Fingerprints written per thread at `uninstall()`. Helpers produce: `helpers.load_module(path)`, `helpers.record_inproc(tmp_path, source, focus=(), window=None, entry="main") -> (Trace, exc | None)`.

- [ ] **Step 1: Write `tests/helpers.py` (in-process recording harness)**

```python
"""Test helpers: in-process recording against real sys.monitoring."""
import importlib.util
import sys
from pathlib import Path

from sensorium.record.tracer import FocusSpec, Tracer
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter


def load_module(path: Path):
    name = f"{path.stem}_{abs(hash(str(path))) % 10**6}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def record_inproc(tmp_path, source, focus=(), window=None, entry="main"):
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)   # tests pass tmp_path / "a"
    prog = tmp_path / "prog.py"
    prog.write_text(source)
    mod = load_module(prog)          # import BEFORE install: defs not traced
    writer = TraceWriter(tmp_path / "trace.db", batch=8)
    tracer = Tracer(writer, root=tmp_path, focus=FocusSpec(list(focus)),
                    window=window)
    err = None
    tracer.install()
    try:
        getattr(mod, entry)()
    except Exception as e:
        err = e
    finally:
        tracer.uninstall()
        writer.close()
    return Trace.open(tmp_path / "trace.db"), err
```

- [ ] **Step 2: Write failing tests**

`tests/test_tracer.py`:

```python
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


def test_fingerprint_deterministic_across_runs(tmp_path):
    t1, _ = record_inproc(tmp_path / "a", ADD)
    t2, _ = record_inproc(tmp_path / "b", ADD)
    h1 = next(iter(t1.fingerprints().values()))
    h2 = next(iter(t2.fingerprints().values()))
    assert h1[0] != "" and h1 == h2
```

Note: `record_inproc` writes both runs' `prog.py` under different roots but the
same *relative* file name; the fingerprint hashes `co_filename`, which differs
by tmp dir. Fix the determinism test by hashing relative paths: the Tracer must
fingerprint `file` as the path **relative to root** when under root (this also
makes refocus robust to store relocation). This is the contract — implement it
that way, don't weaken the test.

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_tracer.py -v` — Expected: FAIL (no tracer module).

- [ ] **Step 4: Implement `src/sensorium/record/tracer.py`**

```python
"""sys.monitoring-based recorder.

Default tier: CALL/RETURN/RAISE/HANDLED for user code (files under root,
excluding stdlib/site-packages/sensorium itself). Focus tier (Task 7) adds
LINE events with local deltas. Re-entrancy: recorder frames are never traced
and capture runs behind a thread-local in_hook flag.
"""
import sys
import threading
import time
from fnmatch import fnmatch
from pathlib import Path

from sensorium.record.capture import capture_exc, capture_value
from sensorium.record.fingerprint import Fingerprint

M = sys.monitoring
TOOL = M.PROFILER_ID
_SENSORIUM_DIR = str(Path(__file__).resolve().parent.parent)
_GENLIKE = 0x20 | 0x80 | 0x200        # CO_GENERATOR|CO_COROUTINE|CO_ASYNC_GEN
_CONTROL_FLOW_EXC = ("StopIteration", "StopAsyncIteration", "GeneratorExit")


def module_name_for(file: str, root: Path) -> str | None:
    try:
        rel = Path(file).resolve().relative_to(root)
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


class FocusSpec:
    def __init__(self, entries: list[str]) -> None:
        self._entries = []
        for e in entries:
            mod, _, qual = e.partition(":")
            self._entries.append((mod, qual or None))

    def __bool__(self) -> bool:
        return bool(self._entries)

    def matches(self, module: str | None, qualname: str) -> bool:
        if module is None:
            return False
        for mod, qual in self._entries:
            if module != mod:
                continue
            if qual is None or qualname == qual or qualname.startswith(qual + "."):
                return True
        return False


class _TLS(threading.local):
    def __init__(self) -> None:
        self.stack: list = []          # [frame_id, code, code_id, locals_snapshot]
        self.in_hook = False
        self.window_depth = 0


class Tracer:
    def __init__(self, writer, root: Path, focus: FocusSpec,
                 include=(), exclude=(), window: str | None = None) -> None:
        self.writer = writer
        self.root = Path(root).resolve()
        self.focus = focus
        self.include = tuple(include)
        self.exclude = tuple(exclude)
        self.window = window
        # id(code) -> (traced, fp_file, qualname, focused, frameless)
        self._decisions: dict[int, tuple] = {}
        self._fps: dict[int, Fingerprint] = {}
        self._fp_lock = threading.Lock()
        self._tls = _TLS()

    # -- classification ----------------------------------------------------
    def _decide(self, code):
        d = self._decisions.get(id(code))
        if d is None:
            d = self._classify(code)
            self._decisions[id(code)] = d
        return d

    def _classify(self, code):
        file = code.co_filename
        untraced = (False, None, None, False, False)
        if not file.startswith("/") or file.startswith(_SENSORIUM_DIR):
            return untraced
        p = str(Path(file).resolve())
        rootp = str(self.root)
        if not p.startswith(rootp + "/"):
            return untraced
        if ("/site-packages/" in p or "/.venv/" in p
                or p.startswith(sys.prefix) or p.startswith(sys.base_prefix)):
            return untraced
        rel = p[len(rootp) + 1:]
        if self.include and not any(fnmatch(rel, g) for g in self.include):
            return untraced
        if any(fnmatch(rel, g) for g in self.exclude):
            return untraced
        module = module_name_for(p, self.root)
        focused = self.focus.matches(module, code.co_qualname)
        frameless = bool(code.co_flags & _GENLIKE)
        return (True, rel, code.co_qualname, focused, frameless)

    def _fp(self, tid: int) -> Fingerprint:
        with self._fp_lock:
            fp = self._fps.get(tid)
            if fp is None:
                fp = self._fps[tid] = Fingerprint()
            return fp

    # -- callbacks ---------------------------------------------------------
    def _on_start(self, code, offset):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced:
            return M.DISABLE
        tls.in_hook = True
        try:
            frame = sys._getframe(1)
            names = code.co_varnames[:code.co_argcount + code.co_kwonlyargcount]
            loc = frame.f_locals
            args = {n: capture_value(loc[n]) for n in names if n in loc}
            tid = threading.get_ident()
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "CALL",
                                        None, cid, code.co_firstlineno,
                                        {"args": args})
            if not frameless:
                parent = tls.stack[-1][0] if tls.stack else None
                fid = self.writer.open_frame(parent, cid, eid,
                                             len(tls.stack), tid)
                tls.stack.append([fid, code, cid, {}])
            self._fp(tid).update(fp_file, qual, "CALL")
            if self.window and qual == self.window:
                tls.window_depth += 1
        finally:
            tls.in_hook = False
        return None

    def _on_return(self, code, offset, retval):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced:
            return M.DISABLE
        tls.in_hook = True
        try:
            tid = threading.get_ident()
            fid = None
            if not frameless and tls.stack and tls.stack[-1][1] is code:
                fid = tls.stack.pop()[0]
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            eid = self.writer.add_event(time.monotonic_ns(), tid, "RETURN",
                                        fid, cid, None,
                                        {"value": capture_value(retval)})
            if fid is not None:
                self.writer.close_frame(fid, eid, "return")
            self._fp(tid).update(fp_file, qual, "RETURN")
            if self.window and qual == self.window and tls.window_depth:
                tls.window_depth -= 1
        finally:
            tls.in_hook = False
        return None

    def _on_unwind(self, code, offset, exc):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced:
            return None                      # exception events can't DISABLE
        tls.in_hook = True
        try:
            if not frameless and tls.stack and tls.stack[-1][1] is code:
                fid = tls.stack.pop()[0]
                self.writer.close_frame(fid, None, "unwind", capture_exc(exc))
            if self.window and qual == self.window and tls.window_depth:
                tls.window_depth -= 1
        finally:
            tls.in_hook = False
        return None

    def _on_raise(self, code, offset, exc):
        return self._exc_event(code, exc, "RAISE")

    def _on_handled(self, code, offset, exc):
        return self._exc_event(code, exc, "HANDLED")

    def _exc_event(self, code, exc, kind):
        tls = self._tls
        if tls.in_hook:
            return None
        traced, fp_file, qual, focused, frameless = self._decide(code)
        if not traced or type(exc).__name__ in _CONTROL_FLOW_EXC:
            return None
        tls.in_hook = True
        try:
            tid = threading.get_ident()
            frame = sys._getframe(1)
            fid = tls.stack[-1][0] if (not frameless and tls.stack
                                       and tls.stack[-1][1] is code) else None
            cid = self.writer.intern_code(code.co_filename, qual,
                                          code.co_firstlineno)
            self.writer.add_event(time.monotonic_ns(), tid, kind, fid, cid,
                                  frame.f_lineno, {"exc": capture_exc(exc)})
            self._fp(tid).update(fp_file, qual, kind)
        finally:
            tls.in_hook = False
        return None

    def _on_line(self, code, line):      # focus tier: implemented in Task 7
        return M.DISABLE

    # -- lifecycle ---------------------------------------------------------
    def install(self) -> None:
        E = M.events
        try:
            M.use_tool_id(TOOL, "sensorium")
        except ValueError as e:
            owner = M.get_tool(TOOL)
            raise RuntimeError(
                f"cannot install monitoring: tool id {TOOL} is already in use"
                f" by {owner!r} ({e}). Another profiler or debugger is "
                "active; stop it and re-run.") from None
        M.register_callback(TOOL, E.PY_START, self._on_start)
        M.register_callback(TOOL, E.PY_RETURN, self._on_return)
        M.register_callback(TOOL, E.PY_UNWIND, self._on_unwind)
        M.register_callback(TOOL, E.RAISE, self._on_raise)
        M.register_callback(TOOL, E.EXCEPTION_HANDLED, self._on_handled)
        M.register_callback(TOOL, E.LINE, self._on_line)
        events = (E.PY_START | E.PY_RETURN | E.PY_UNWIND
                  | E.RAISE | E.EXCEPTION_HANDLED)
        if self.focus:
            events |= E.LINE
        M.set_events(TOOL, events)
        M.restart_events()

    def uninstall(self) -> None:
        E = M.events
        M.set_events(TOOL, 0)
        for ev in (E.PY_START, E.PY_RETURN, E.PY_UNWIND, E.RAISE,
                   E.EXCEPTION_HANDLED, E.LINE):
            M.register_callback(TOOL, ev, None)
        M.free_tool_id(TOOL)
        for tid, fp in self._fps.items():
            self.writer.write_fingerprint(tid, fp.hexdigest(), fp.count)
```

Notes for the implementer:
- `sys._getframe(1)` inside a monitoring callback is the frame that triggered
  the event; this is the standard PEP 669 debugger technique.
- `TOOL = M.PROFILER_ID` (2). Coverage.py claims `COVERAGE_ID` (0), so
  `pytest --cov` and sensorium coexist. A second profiler does not — hence
  the loud `RuntimeError` in `install()`, which `boot.run_target` lets
  propagate so the run dies with a diagnosis rather than a thin trace.
- `M.DISABLE` from PY_START/PY_RETURN/LINE permanently mutes that code
  location (until `restart_events`), which is what makes unfocused code
  near-free. Exception events cannot be disabled — those callbacks fast-path
  on the cached decision instead.
- The fingerprint uses the **root-relative** path (`fp_file`), per the
  contract in Step 2's note.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_tracer.py -v` — Expected: all PASS.
Also rerun the whole suite (`.venv/bin/pytest`) to confirm nothing regressed.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/record/tracer.py tests/helpers.py tests/test_tracer.py
git commit -m "feat: sys.monitoring tracer default tier with frames and fingerprints"
```

---

### Task 7: Focus tier — LINE events with local deltas, and `--window`

**Files:**
- Modify: `src/sensorium/record/tracer.py` (replace the `_on_line` stub)
- Test: `tests/test_focus.py`

**Interfaces:**
- Consumes: everything Task 6 built.
- Produces: LINE events for focused code only: `kind="LINE"`, `frame_id` set, `line` = line about to execute, `payload={"deltas": {name: capture}}` containing **only changed** locals (state produced by the preceding execution). No LINE event is emitted when nothing changed. With `window=QUALNAME`, LINE events are only recorded while dynamically inside an activation of that qualname. Fingerprints are identical with and without focus.

- [ ] **Step 1: Write failing tests**

`tests/test_focus.py`:

```python
from tests.helpers import record_inproc

LOOP = """
def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    return accumulate([5, 10, 20])
"""

NESTED = """
def inner(x):
    y = x * 2
    return y

def outer(x):
    a = inner(x)
    b = inner(a)
    return b

def main():
    return outer(3)
"""


def _deltas(trace):
    out = []
    for e in trace.events(kind="LINE"):
        out.append({n: v for n, v in e.payload["deltas"].items()})
    return out


def test_focused_function_yields_local_deltas(tmp_path):
    t, err = record_inproc(tmp_path, LOOP, focus=["prog:accumulate"])
    assert err is None
    seen = _deltas(t)
    assert {"total": {"k": "num", "v": 0}} in seen
    totals = [d["total"]["v"] for d in seen if "total" in d]
    assert totals == [0, 5, 15, 35]


def test_line_events_only_deltas_and_have_frames(tmp_path):
    t, _ = record_inproc(tmp_path, LOOP, focus=["prog:accumulate"])
    for e in t.events(kind="LINE"):
        assert e.frame_id is not None and e.payload["deltas"]
        assert t.code(e.code_id).qualname == "accumulate"


def test_unfocused_run_has_no_line_events(tmp_path):
    t, _ = record_inproc(tmp_path, LOOP)
    assert t.events(kind="LINE") == []


def test_focus_does_not_change_fingerprint(tmp_path):
    t1, _ = record_inproc(tmp_path / "a", LOOP)
    t2, _ = record_inproc(tmp_path / "b", LOOP, focus=["prog:accumulate"])
    assert (next(iter(t1.fingerprints().values()))
            == next(iter(t2.fingerprints().values())))


def test_window_limits_line_capture_to_dynamic_extent(tmp_path):
    # focus on inner, but window on outer: both inner activations are inside
    # outer, so both captured
    t_in, _ = record_inproc(tmp_path / "a", NESTED,
                            focus=["prog:inner"], window="outer")
    assert len(t_in.events(kind="LINE")) > 0
    # window on a function that never runs: no LINE events at all
    t_out, _ = record_inproc(tmp_path / "b", NESTED,
                             focus=["prog:inner"], window="never_runs")
    assert t_out.events(kind="LINE") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_focus.py -v` — Expected: the delta tests FAIL (stub DISABLEs everything).

- [ ] **Step 3: Replace `_on_line` in `src/sensorium/record/tracer.py`**

```python
    def _on_line(self, code, line):
        tls = self._tls
        if tls.in_hook:
            return None
        d = self._decide(code)
        traced, _, _, focused, frameless = d
        if not traced or not focused or frameless:
            return M.DISABLE          # never see this location again
        if self.window and tls.window_depth == 0:
            return None               # outside window; can't DISABLE (may re-enter)
        tls.in_hook = True
        try:
            if not tls.stack or tls.stack[-1][1] is not code:
                return None
            entry = tls.stack[-1]
            frame = sys._getframe(1)
            prev = entry[3]
            deltas = {}
            cur = {}
            for name, val in frame.f_locals.items():
                cap = capture_value(val)
                cur[name] = cap
                if prev.get(name) != cap:
                    deltas[name] = cap
            entry[3] = cur
            if deltas:
                tid = threading.get_ident()
                self.writer.add_event(time.monotonic_ns(), tid, "LINE",
                                      entry[0], entry[2], line,
                                      {"deltas": deltas})
        finally:
            tls.in_hook = False
        return None
```

The LINE event fires *before* the line runs, so its deltas describe the state
produced by the preceding line — the stored `line` is the line about to
execute. This is intentional and documented in the module docstring; queries
present it as a state timeline.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_focus.py tests/test_tracer.py -v` — Expected: all PASS (tracer tests must not regress).

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/record/tracer.py tests/test_focus.py
git commit -m "feat: focus tier LINE capture with local deltas and window gating"
```

---

### Task 8: Boot, run metadata, and the `run` CLI command

**Files:**
- Create: `src/sensorium/record/boot.py`, `src/sensorium/cli.py`, `src/sensorium/__main__.py`
- Modify: `tests/helpers.py` (add subprocess helpers)
- Test: `tests/test_boot_cli.py`

**Interfaces:**
- Consumes: `Tracer`, `FocusSpec`, `TraceWriter`, `paths`, `capture`.
- Produces: `boot.TargetError`; `boot.resolve_target(argv) -> Callable[[], None]` (`.py` path → `runpy.run_path` with script dir prepended to `sys.path`, `-m mod` → `runpy.run_module` with cwd prepended, console script → entry-point load; sets `sys.argv` to match `python`'s behavior); `boot.git_info(cwd) -> {"git_sha": str | None, "git_dirty_hash": str | None}`; `boot.run_target(argv, *, focus=(), include=(), exclude=(), window=None, run_id=None, refocus_of=None) -> (run_id, exit_status)`. `cli.main(argv=None) -> int` with subcommand `run` printing `run: <id>` and `trace: <path>` and returning the target's exit status. Meta keys written (exact names — later tasks read them): `run_id, argv, cwd, env, env_hash, python, git_sha, git_dirty_hash, focus, include, exclude, window, caps, start_ts, end_ts, exit_status, uncaught, stdin_consumed, children, truncated_count, incomplete, refocus_of` (last only when set). stdout/stderr are tee'd into the `output` table keyed by `last_event_id`; `subprocess.Popen` audit events land in `children`.

- [ ] **Step 1: Add subprocess helpers to `tests/helpers.py`**

Append:

```python
import os
import re
import subprocess


def run_cli(args, cwd, sensorium_dir, stdin_text=None):
    env = dict(os.environ, SENSORIUM_DIR=str(sensorium_dir))
    return subprocess.run(
        [sys.executable, "-m", "sensorium", *args],
        cwd=cwd, env=env, capture_output=True, text=True, input=stdin_text)


def record_script(tmp_path, source, extra=(), name="prog.py", argv=(),
                  stdin_text=None):
    (tmp_path / name).write_text(source)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", *extra, "--", name, *argv], cwd=tmp_path,
                sensorium_dir=sdir, stdin_text=stdin_text)
    m = re.search(r"^run: (\S+)$", r.stdout, re.M)
    run_id = m.group(1) if m else None
    trace = sdir / "traces" / f"{run_id}.db" if run_id else None
    return run_id, trace, r
```

- [ ] **Step 2: Write failing tests**

`tests/test_boot_cli.py`:

```python
from sensorium.store.reader import Trace
from tests.helpers import record_script, run_cli

HELLO = """
def greet(name):
    print(f"hello {name}")
    return name

def main():
    greet("world")

if __name__ == "__main__":
    main()
"""

EXITS = """
import sys
sys.exit(3)
"""

SPAWNS = """
import subprocess, sys
subprocess.run([sys.executable, "-c", "pass"])
print("spawned")
"""

READS_STDIN = """
line = input()
print("got", line)
"""


def test_records_and_propagates_exit_zero(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO)
    assert r.returncode == 0 and run_id is not None
    assert f"trace: {trace}" in r.stdout
    t = Trace.open(trace)
    assert t.meta["exit_status"] == 0
    assert t.meta["incomplete"] is False
    assert t.meta["argv"] == ["prog.py"]
    quals = {t.code(e.code_id).qualname for e in t.events(kind="CALL")}
    assert {"main", "greet"} <= quals


def test_stdout_passthrough_and_captured(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO)
    assert "hello world" in r.stdout          # passed through to real stdout
    t = Trace.open(trace)
    data = "".join(d for _, s, d in t.output_chunks() if s == "stdout")
    assert "hello world" in data              # and interleaved in the trace


def test_sys_exit_code_propagated(tmp_path):
    run_id, trace, r = record_script(tmp_path, EXITS)
    assert r.returncode == 3
    assert Trace.open(trace).meta["exit_status"] == 3


def test_uncaught_exception_recorded_and_exit_1(tmp_path):
    src = "def main():\n    raise ValueError('bad')\nmain()\n"
    run_id, trace, r = record_script(tmp_path, src)
    assert r.returncode == 1
    m = Trace.open(trace).meta
    assert m["uncaught"]["type"] == "ValueError"


def test_child_processes_listed_not_witnessed(tmp_path):
    run_id, trace, r = record_script(tmp_path, SPAWNS)
    assert len(Trace.open(trace).meta["children"]) == 1


def test_stdin_consumption_flagged(tmp_path):
    run_id, trace, r = record_script(tmp_path, READS_STDIN, stdin_text="x\n")
    assert Trace.open(trace).meta["stdin_consumed"] is True
    run_id2, trace2, _ = record_script(tmp_path / "b", HELLO)
    assert Trace.open(trace2).meta["stdin_consumed"] is False


def test_unresolvable_target_is_clear_error(tmp_path):
    r = run_cli(["run", "--", "no-such-cmd-xyz"], cwd=tmp_path,
                sensorium_dir=tmp_path / "s")
    assert r.returncode == 2 and "cannot resolve" in r.stderr
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_boot_cli.py -v` — Expected: FAIL (`No module named sensorium.__main__`).

- [ ] **Step 4: Implement `src/sensorium/record/boot.py`**

```python
"""Resolve and execute a target program in-process under recording."""
import hashlib
import importlib.metadata
import io
import json
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path

from sensorium import paths
from sensorium.record import capture
from sensorium.record.tracer import FocusSpec, Tracer
from sensorium.store.writer import TraceWriter


class TargetError(Exception):
    pass


def resolve_target(argv: list[str]):
    if not argv:
        raise TargetError("no target command given")
    cmd = argv[0]
    if cmd == "-m":
        if len(argv) < 2:
            raise TargetError("-m requires a module name")
        mod, rest = argv[1], argv[2:]

        def run_module():
            sys.path.insert(0, os.getcwd())
            sys.argv = [mod, *rest]
            runpy.run_module(mod, run_name="__main__", alter_sys=True)
        return run_module
    if cmd.endswith(".py"):
        p = Path(cmd).resolve()
        if not p.exists():
            raise TargetError(f"cannot resolve target: no such file: {cmd}")

        def run_file():
            sys.path.insert(0, str(p.parent))
            sys.argv = [str(p), *argv[1:]]
            runpy.run_path(str(p), run_name="__main__")
        return run_file
    eps = importlib.metadata.entry_points(group="console_scripts", name=cmd)
    for ep in eps:
        fn = ep.load()

        def run_script():
            sys.argv = list(argv)
            fn()
        return run_script
    raise TargetError(
        f"cannot resolve target {cmd!r}: not a .py file, -m module, "
        "or installed console script")


class _Tee(io.TextIOBase):
    def __init__(self, orig, name, writer):
        self._orig = orig
        self._name = name
        self._writer = writer

    def write(self, s):
        n = self._orig.write(s)
        if s:
            self._writer.add_output(self._writer.last_event_id, self._name, s)
        return n

    def flush(self):
        self._orig.flush()


class _StdinProxy:
    def __init__(self, orig):
        self._orig = orig
        self.consumed = False

    def _marking(self, fn):
        def inner(*a, **k):
            self.consumed = True
            return fn(*a, **k)
        return inner

    def __getattr__(self, name):
        attr = getattr(self._orig, name)
        if name in ("read", "readline", "readlines"):
            return self._marking(attr)
        return attr

    def __iter__(self):
        self.consumed = True
        return iter(self._orig)


def git_info(cwd: Path) -> dict:
    def _git(*args):
        r = subprocess.run(["git", *args], cwd=cwd,
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    sha = _git("rev-parse", "HEAD")
    if sha is None:
        return {"git_sha": None, "git_dirty_hash": None}
    status = _git("status", "--porcelain") or ""
    return {"git_sha": sha,
            "git_dirty_hash": hashlib.sha256(status.encode()).hexdigest()[:16]}


def run_target(argv, *, focus=(), include=(), exclude=(), window=None,
               run_id=None, refocus_of=None):
    run_id = run_id or paths.new_run_id()
    target = resolve_target(argv)        # resolve before hooks: never traced
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db")
    env = dict(os.environ)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", list(argv))
    w.set_meta("cwd", str(Path.cwd()))
    w.set_meta("env", env)
    w.set_meta("env_hash", hashlib.sha256(
        json.dumps(env, sort_keys=True).encode()).hexdigest()[:16])
    w.set_meta("python", sys.version.split()[0])
    for k, v in git_info(Path.cwd()).items():
        w.set_meta(k, v)
    w.set_meta("focus", list(focus))
    w.set_meta("include", list(include))
    w.set_meta("exclude", list(exclude))
    w.set_meta("window", window)
    w.set_meta("caps", capture.CAPS)
    w.set_meta("start_ts", time.time())
    w.set_meta("incomplete", True)
    if refocus_of:
        w.set_meta("refocus_of", refocus_of)

    children: list[list[str]] = []

    def _audit(event, args_tuple):
        if event == "subprocess.Popen":
            try:
                children.append([str(a) for a in (args_tuple[1] or [])][:8])
            except Exception:
                pass
    sys.addaudithook(_audit)

    prev = (sys.stdin, sys.stdout, sys.stderr)
    stdin_proxy = _StdinProxy(sys.stdin)
    tracer = Tracer(w, root=Path.cwd(), focus=FocusSpec(list(focus)),
                    include=include, exclude=exclude, window=window)
    exit_status = 0
    uncaught = None
    sys.stdin = stdin_proxy
    sys.stdout = _Tee(prev[1], "stdout", w)
    sys.stderr = _Tee(prev[2], "stderr", w)
    tracer.install()
    try:
        target()
    except SystemExit as e:
        code = e.code
        exit_status = code if isinstance(code, int) else (0 if code is None
                                                          else 1)
    except BaseException as e:
        exit_status = 1
        uncaught = capture.capture_exc(e)
    finally:
        tracer.uninstall()
        sys.stdin, sys.stdout, sys.stderr = prev
        w.set_meta("uncaught", uncaught)
        w.set_meta("stdin_consumed", stdin_proxy.consumed)
        w.set_meta("children", children)
        w.set_meta("truncated_count", capture.capture_stats["truncated"])
        w.set_meta("exit_status", exit_status)
        w.set_meta("end_ts", time.time())
        w.set_meta("incomplete", False)
        w.close()
    return run_id, exit_status
```

- [ ] **Step 5: Implement `src/sensorium/cli.py` and `src/sensorium/__main__.py`**

`src/sensorium/cli.py` (query subcommands register here in later tasks — the
loop over `_QUERY_MODULES` is the single growth point):

```python
"""sensorium command-line interface."""
import argparse
import sys

from sensorium import paths

_QUERY_MODULES: list = []      # query tasks append their modules here


def _add_run_parser(sub):
    p = sub.add_parser("run", help="record one execution")
    p.add_argument("--focus", action="append", default=[],
                   help="pkg.module or pkg.module:qualname; repeatable")
    p.add_argument("--include", action="append", default=[])
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--window", default=None)
    p.add_argument("--run-id", default=None, help=argparse.SUPPRESS)
    p.add_argument("--refocus-of", default=None, help=argparse.SUPPRESS)
    p.add_argument("target", nargs=argparse.REMAINDER)
    p.set_defaults(func=_run)


def _run(args) -> int:
    from sensorium.record import boot
    target = list(args.target)
    if target and target[0] == "--":
        target = target[1:]
    if not target:
        print("usage: sensorium run [options] -- <command> [args...]",
              file=sys.stderr)
        return 2
    try:
        run_id, exit_status = boot.run_target(
            target, focus=args.focus, include=args.include,
            exclude=args.exclude, window=args.window,
            run_id=args.run_id, refocus_of=args.refocus_of)
    except boot.TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"run: {run_id}")
    print(f"trace: {paths.traces_dir() / (run_id + '.db')}")
    return exit_status


def main(argv=None) -> int:
    if sys.version_info < (3, 12):
        print("sensorium requires Python 3.12+ (sys.monitoring); running "
              f"under {sys.version.split()[0]}", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(
        prog="sensorium",
        description="Record a Python program's execution; "
                    "query what actually happened.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_run_parser(sub)
    for mod in _QUERY_MODULES:
        mod.add_parser(sub)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except paths.TraceLookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
```

`src/sensorium/__main__.py`:

```python
from sensorium.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_boot_cli.py -v` — Expected: all PASS.
Full suite: `.venv/bin/pytest` — Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/sensorium/record/boot.py src/sensorium/cli.py \
        src/sensorium/__main__.py tests/helpers.py tests/test_boot_cli.py
git commit -m "feat: boot target in-process under recording; sensorium run CLI"
```

---

### Task 9: Formatting helpers, `runs`, and `info`

**Files:**
- Create: `src/sensorium/query/fmt.py`, `src/sensorium/query/runs_cmd.py`, `src/sensorium/query/info_cmd.py`
- Modify: `src/sensorium/cli.py` (register the two modules)
- Test: `tests/test_fmt.py`, `tests/test_runs_info.py`

**Interfaces:**
- Consumes: `Trace`, `paths.find_trace`.
- Produces: `fmt.fmt_value(v: dict | None) -> str` (e.g. `1800`, `'abc'`, `None`, `list[1000]=[0, 1, ...]`, `dict[5]={'a': 1, ...}`, `Grid#140233…`; truncated strings get a `~` suffix); `fmt.fmt_args(args: dict, limit=4) -> str`; `fmt.fmt_exc(e) -> str` (`ValueError('bad amount')`); `fmt.fmt_event(trace, e) -> str` — one dense line: `e12 CALL    shipping_cost(weight_kg=1800)` / `e14 RETURN  item_weight -> 1800` / `e77 RAISE   parse_row raise ValueError('...') L8` / `e81 LINE    accumulate L4  total=15`; `fmt.more_note(total, shown, hint) -> str | None`; `fmt.parse_eref("e12") -> 12`, `fmt.parse_fref("f5") -> 5`. Query command modules each expose `add_parser(sub)` and `run(args) -> int`. Every query command resolves its `run` argument through `paths.find_trace` (accepting a full id, unique prefix, or `last`).
- CLI registration pattern used by this and every later query task, in `cli.py`:

```python
from sensorium.query import runs_cmd, info_cmd     # extend this import
_QUERY_MODULES = [runs_cmd, info_cmd]              # extend this list
```

- [ ] **Step 1: Write failing tests**

`tests/test_fmt.py`:

```python
from sensorium.query import fmt


def test_fmt_scalars():
    assert fmt.fmt_value({"k": "num", "v": 1800}) == "1800"
    assert fmt.fmt_value({"k": "str", "v": "hi"}) == "'hi'"
    assert fmt.fmt_value({"k": "str", "v": "xx", "trunc": True}) == "'xx'~"
    assert fmt.fmt_value({"k": "none"}) == "None"
    assert fmt.fmt_value({"k": "bool", "v": True}) == "True"
    assert fmt.fmt_value(None) == "?"


def test_fmt_containers_and_objects():
    v = {"k": "seq", "type": "list", "len": 3, "oid": 1,
         "sample": [{"k": "num", "v": 1}, {"k": "num", "v": 2},
                    {"k": "num", "v": 3}]}
    assert fmt.fmt_value(v) == "list[3]=[1, 2, 3]"
    v["trunc"] = True
    assert fmt.fmt_value(v).endswith(", ...]")
    o = {"k": "obj", "type": "Grid", "oid": 99, "repr": "<Grid>"}
    assert fmt.fmt_value(o) == "Grid#99"


def test_fmt_args_caps_at_limit():
    args = {f"a{i}": {"k": "num", "v": i} for i in range(6)}
    s = fmt.fmt_args(args)
    assert s.count("=") == 4 and s.endswith(", ...")


def test_parse_refs():
    assert fmt.parse_eref("e12") == 12 and fmt.parse_eref("12") == 12
    assert fmt.parse_fref("f5") == 5


def test_more_note():
    assert fmt.more_note(10, 10, "x") is None
    assert "7 more" in fmt.more_note(10, 3, "sensorium tree R --after e9")
```

`tests/test_runs_info.py` (records via subprocess, queries in-process for
coverage):

```python
from sensorium import cli
from tests.helpers import record_script

SRC = """
def work(n):
    try:
        [1, 2][n]
    except IndexError:
        pass
    return n * "x" * 300

def main():
    for i in range(3):
        work(5)

if __name__ == "__main__":
    main()
"""


def _record(tmp_path, monkeypatch, extra=()):
    run_id, trace, r = record_script(tmp_path, SRC, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_runs_lists_recorded_trace(tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["runs"]) == 0
    out = capsys.readouterr().out
    assert run_id in out and "exit:0" in out and "prog.py" in out


def test_info_reports_shape_and_honesty(tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert "exit: 0" in out
    assert "CALL" in out and "HANDLED" in out
    assert "truncated values:" in out          # 300-char strings force it
    assert "fingerprint" in out
    assert "work" in out                       # hot functions list
    assert "INCOMPLETE" not in out


def test_info_prefix_and_last_resolution(tmp_path, monkeypatch, capsys):
    run_id = _record(tmp_path, monkeypatch)
    assert cli.main(["info", "last"]) == 0
    assert run_id in capsys.readouterr().out


def test_unknown_run_is_exit_2(tmp_path, monkeypatch, capsys):
    _record(tmp_path, monkeypatch)
    assert cli.main(["info", "zzz-nope"]) == 2
    assert "no trace matches" in capsys.readouterr().err
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_fmt.py tests/test_runs_info.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/query/fmt.py`**

```python
"""Shared plain-text formatting: dense, stable, one fact per line."""


def fmt_value(v: dict | None) -> str:
    if v is None:
        return "?"
    k = v.get("k")
    if k == "none":
        return "None"
    if k in ("num", "bool"):
        return repr(v["v"])
    if k == "str":
        return repr(v["v"]) + ("~" if v.get("trunc") else "")
    if k == "seq":
        inner = ", ".join(fmt_value(x) for x in v.get("sample", []))
        more = ", ..." if v.get("trunc") else ""
        return f"{v['type']}[{v['len']}]=[{inner}{more}]"
    if k == "map":
        pairs = ", ".join(f"{fmt_value(a)}: {fmt_value(b)}"
                          for a, b in v.get("sample", []))
        more = ", ..." if v.get("trunc") else ""
        return f"{v['type']}[{v['len']}]={{{pairs}{more}}}"
    if k == "obj":
        return f"{v['type']}#{v['oid']}"
    return "?"


def fmt_args(args: dict, limit: int = 4) -> str:
    parts = [f"{n}={fmt_value(v)}" for n, v in list(args.items())[:limit]]
    if len(args) > limit:
        parts.append("...")
    return ", ".join(parts)


def fmt_exc(e: dict) -> str:
    return f"{e['type']}({e['msg']!r})"


def fmt_event(trace, e) -> str:
    code = trace.code(e.code_id) if e.code_id else None
    q = code.qualname if code else "?"
    p = e.payload or {}
    if e.kind == "CALL":
        body = f"{q}({fmt_args(p.get('args', {}))})"
    elif e.kind == "RETURN":
        body = f"{q} -> {fmt_value(p.get('value'))}"
    elif e.kind in ("RAISE", "HANDLED"):
        body = f"{q} {e.kind.lower()} {fmt_exc(p['exc'])} L{e.line}"
    elif e.kind == "LINE":
        deltas = ", ".join(f"{n}={fmt_value(v)}"
                           for n, v in p.get("deltas", {}).items())
        body = f"{q} L{e.line}  {deltas}"
    else:
        body = q
    return f"e{e.id} {e.kind:<7} {body}"


def more_note(total: int, shown: int, hint: str) -> str | None:
    if shown >= total:
        return None
    return f"... {total - shown} more; continue with: {hint}"


def parse_eref(s: str) -> int:
    return int(s.lstrip("ef"))


def parse_fref(s: str) -> int:
    return int(s.lstrip("ef"))
```

- [ ] **Step 4: Implement `runs_cmd.py` and `info_cmd.py`; register in `cli.py`**

`src/sensorium/query/runs_cmd.py`:

```python
"""List recorded traces, newest-last."""
from sensorium import paths
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("runs", help="list recorded traces")
    p.set_defaults(func=run)


def run(args) -> int:
    files = sorted(paths.traces_dir().glob("*.db"), key=lambda p: p.name)
    if not files:
        print("no traces recorded")
        return 0
    for f in files:
        t = Trace.open(f)
        m = t.meta
        flags = []
        if m.get("incomplete"):
            flags.append("INCOMPLETE")
        if m.get("refocus_of"):
            flags.append(f"refocus-of:{m['refocus_of']}")
        suffix = f"  [{','.join(flags)}]" if flags else ""
        print(f"{f.stem}  exit:{m.get('exit_status', '?')}  "
              f"events:{sum(t.counts().values())}  "
              f"cmd: {' '.join(m.get('argv', []))}{suffix}")
    return 0
```

`src/sensorium/query/info_cmd.py`:

```python
"""Summarize one trace: shape, exceptions, caps, honesty flags."""
from sensorium import paths
from sensorium.query.fmt import fmt_exc
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("info", help="summarize one trace")
    p.add_argument("run")
    p.set_defaults(func=run)


def run(args) -> int:
    t = Trace.open(paths.find_trace(args.run))
    m = t.meta
    counts = t.counts()
    dur = ""
    if m.get("end_ts") and m.get("start_ts"):
        dur = f"  duration: {m['end_ts'] - m['start_ts']:.2f}s"
    print(f"run {m.get('run_id', t.path.stem)}  trace: {t.path}")
    print(f"cmd: {' '.join(m.get('argv', []))}    cwd: {m.get('cwd', '?')}")
    print(f"python {m.get('python', '?')}  exit: {m.get('exit_status', '?')}"
          f"  events: {sum(counts.values())}{dur}")
    print("recorded: " + "  ".join(f"{k} {counts.get(k, 0)}" for k in
                                   ("CALL", "RETURN", "RAISE", "HANDLED",
                                    "LINE")))
    focus = m.get("focus") or []
    print(f"focus: {', '.join(focus) if focus else '-'}    "
          f"window: {m.get('window') or '-'}")
    caps = m.get("caps", {})
    print("caps: " + " ".join(f"{k}={v}" for k, v in caps.items())
          + f"   truncated values: {m.get('truncated_count', 0)}")
    for tid, (h, n) in sorted(t.fingerprints().items()):
        tag = " (main)" if tid == t.main_thread_id() else ""
        print(f"fingerprint thread {tid}{tag}: {h} ({n} causal events)")
    if m.get("uncaught"):
        print(f"uncaught: {fmt_exc(m['uncaught'])}")
    for child in m.get("children") or []:
        print(f"unwitnessed subprocess: {child}")
    if m.get("incomplete"):
        print(f"INCOMPLETE: trace ended at e{sum(counts.values())} "
              "without finalize (process died mid-record)")
    if m.get("refocus_of"):
        print(f"refocus-of: {m['refocus_of']}  "
              f"verdict: {m.get('refocus_verdict', 'UNVERIFIED')}")
    hot = sorted(((c, len(t.frames(code_id=c.id))) for c in t.codes()),
                 key=lambda x: -x[1])[:8]
    if hot:
        print("hot functions:")
        for code, n in hot:
            if n:
                print(f"  {n}x {code.file.rsplit('/', 1)[-1]}:{code.qualname}")
    return 0
```

In `src/sensorium/cli.py`, replace the `_QUERY_MODULES` line:

```python
from sensorium.query import info_cmd, runs_cmd

_QUERY_MODULES = [runs_cmd, info_cmd]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_fmt.py tests/test_runs_info.py -v` — Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query tests/test_fmt.py tests/test_runs_info.py \
        src/sensorium/cli.py
git commit -m "feat: fmt helpers plus runs and info commands"
```

---

### Task 10: `tree` and `frame`

**Files:**
- Create: `src/sensorium/query/tree_cmd.py`, `src/sensorium/query/frame_cmd.py`
- Modify: `src/sensorium/cli.py` (extend `_QUERY_MODULES` with `tree_cmd, frame_cmd`)
- Test: `tests/test_tree_frame.py`

**Interfaces:**
- Consumes: `Trace`, `fmt`, `paths.find_trace`.
- Produces: `tree RUN [--root fN | --around eN] [--depth N] [--limit N]` — indented one-line-per-frame rendering; `tree_cmd.frame_line(trace, frame) -> str` (reused by `frame_cmd`): `f5 e12 silver_discount(total=100.0) -> 95.0`, unwound frames tagged `!! ValueError('...')`, open frames `(open)`. `frame RUN [fN] [--fn QUALNAME] [--nth N]` — full args, LINE timeline (or an honest "not captured … refocus with --focus" note), return/unwind, children.

- [ ] **Step 1: Write failing tests**

`tests/test_tree_frame.py`:

```python
from sensorium import cli
from tests.helpers import record_script

SRC = """
def gold(total):
    return total * 0.80

def silver(total):
    return total * 0.95

def price(points, total):
    if points > 1000:
        return gold(total)
    return silver(total)

def main():
    for pts in (500, 1000, 1500):
        price(pts, 100.0)

if __name__ == "__main__":
    main()
"""

LOOP = """
def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    accumulate([5, 10])

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, monkeypatch, src=SRC, extra=()):
    run_id, trace, r = record_script(tmp_path, src, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_tree_shows_hierarchy_args_returns(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("silver(") == 2 and out.count("gold(") == 1
    assert "-> 95.0" in out
    # children indented under price
    price_line = next(ln for ln in out.splitlines() if "price(points=1000" in ln)
    child_line = out.splitlines()[out.splitlines().index(price_line) + 1]
    assert child_line.startswith(price_line[:len(price_line)
                                            - len(price_line.lstrip())] + "  ")


def test_tree_around_event(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    cli.main(["tree", run_id])
    first = capsys.readouterr().out
    silver_line = next(ln for ln in first.splitlines() if "silver(" in ln)
    eid = silver_line.split()[1]            # "e<id>" token of frame_line
    assert cli.main(["tree", run_id, "--around", eid]) == 0
    out = capsys.readouterr().out
    assert "silver(" in out and "main(" in out    # ancestors shown


def test_frame_by_fn_with_timeline(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=LOOP,
                  extra=("--focus", "prog:accumulate"))
    assert cli.main(["frame", run_id, "--fn", "accumulate"]) == 0
    out = capsys.readouterr().out
    assert "args: ops=list[2]=[5, 10]" in out
    assert "timeline:" in out and "total=15" in out
    assert "return: 15" in out


def test_frame_without_focus_says_refocus(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=LOOP)
    cli.main(["frame", run_id, "--fn", "accumulate"])
    out = capsys.readouterr().out
    assert "not captured" in out and "refocus" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_tree_frame.py -v` — Expected: FAIL (unknown subcommand).

- [ ] **Step 3: Implement `src/sensorium/query/tree_cmd.py`**

```python
"""Call-tree slices: what actually ran, in what order."""
from sensorium import paths
from sensorium.query.fmt import (fmt_args, fmt_exc, fmt_value, parse_eref,
                                 parse_fref)
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("tree", help="call-tree slice")
    p.add_argument("run")
    p.add_argument("--root", default=None, help="frame ref (f12)")
    p.add_argument("--around", default=None, help="event ref (e40)")
    p.add_argument("--depth", type=int, default=4)
    p.add_argument("--limit", type=int, default=200)
    p.set_defaults(func=run)


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
    return f"f{frame.id} e{frame.call_event_id} {code.qualname}({args}){tail}"


def render_tree(trace, roots, depth_limit, max_lines):
    lines: list[str] = []
    cut = [0]

    def walk(frame, depth):
        if len(lines) >= max_lines or depth > depth_limit:
            cut[0] += 1
            return
        lines.append("  " * depth + frame_line(trace, frame))
        for ch in trace.children(frame.id):
            walk(ch, depth + 1)

    for r in roots:
        walk(r, 0)
    return lines, cut[0]


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    if args.around:
        f = trace.frame_containing(parse_eref(args.around))
        if f is None:
            print(f"no frame contains {args.around}")
            return 1
        chain = [f]
        while chain[-1].parent_id is not None:
            chain.append(trace.frame(chain[-1].parent_id))
        ancestors = list(reversed(chain[1:]))
        for depth, fr in enumerate(ancestors):
            print("  " * depth + frame_line(trace, fr))
        lines, cut = render_tree(trace, [f], args.depth, args.limit)
        for ln in lines:
            print("  " * len(ancestors) + ln)
    else:
        roots = ([trace.frame(parse_fref(args.root))] if args.root
                 else trace.roots())
        lines, cut = render_tree(trace, [r for r in roots if r], args.depth,
                                 args.limit)
        for ln in lines:
            print(ln)
        if cut:
            print(f"... {cut} subtree(s) beyond --depth {args.depth} or "
                  f"--limit {args.limit}; narrow with --root fN")
    return 0
```

- [ ] **Step 4: Implement `src/sensorium/query/frame_cmd.py`**

```python
"""One activation completely: args, local timeline, return, children."""
from sensorium import paths
from sensorium.query.fmt import fmt_args, fmt_exc, fmt_value, parse_fref
from sensorium.query.tree_cmd import frame_line
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("frame", help="one activation in full")
    p.add_argument("run")
    p.add_argument("frame", nargs="?", default=None, help="frame ref (f12)")
    p.add_argument("--fn", default=None, help="qualname of the function")
    p.add_argument("--nth", type=int, default=1, help="which activation (1-based)")
    p.set_defaults(func=run)


def _resolve(trace, args):
    if args.frame:
        return trace.frame(parse_fref(args.frame))
    if args.fn:
        matches = [f for f in trace.frames()
                   if trace.code(f.code_id).qualname == args.fn]
        if len(matches) >= args.nth:
            return matches[args.nth - 1]
    return None


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    f = _resolve(trace, args)
    if f is None:
        print("no such frame; give f<id> or --fn QUALNAME [--nth N]")
        return 1
    code = trace.code(f.code_id)
    end = f"e{f.return_event_id}" if f.return_event_id is not None else "?"
    print(f"f{f.id} {code.file.rsplit('/', 1)[-1]}:{code.qualname}  "
          f"[e{f.call_event_id}..{end}]  thread {f.thread_id}  "
          f"depth {f.depth}  closed: {f.closed_by or 'open'}")
    call = trace.event(f.call_event_id)
    args_p = (call.payload or {}).get("args", {}) if call else {}
    print("args: " + (fmt_args(args_p, limit=99) or "(none)"))
    lines = [e for e in trace.frame_events(f.id) if e.kind == "LINE"]
    if lines:
        print("timeline:")
        for e in lines:
            deltas = ", ".join(f"{n}={fmt_value(v)}"
                               for n, v in e.payload["deltas"].items())
            print(f"  e{e.id} L{e.line}  {deltas}")
    else:
        mod = code.file.rsplit("/", 1)[-1].removesuffix(".py")
        print("timeline: not captured (locals need line-level focus; "
              f"refocus with --focus {mod}:{code.qualname})")
    if f.closed_by == "unwind":
        print("unwound: " + (fmt_exc(f.unwind_exc) if f.unwind_exc else "?"))
    elif f.return_event_id is not None:
        ret = trace.event(f.return_event_id)
        print(f"return: {fmt_value((ret.payload or {}).get('value'))}")
    kids = trace.children(f.id)
    if kids:
        print(f"children ({len(kids)}):")
        for ch in kids:
            print("  " + frame_line(trace, ch))
    else:
        print("children: (none)")
    return 0
```

In `cli.py` extend:

```python
from sensorium.query import frame_cmd, info_cmd, runs_cmd, tree_cmd

_QUERY_MODULES = [runs_cmd, info_cmd, tree_cmd, frame_cmd]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_tree_frame.py -v` — Expected: all PASS.
Note: the frame test asserts `timeline: (no local changes captured)` never
appears in the unfocused case — the message must be the refocus hint, keyed
on whether LINE events exist for the frame, per Step 4's implementation.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/tree_cmd.py src/sensorium/query/frame_cmd.py \
        src/sensorium/cli.py tests/test_tree_frame.py
git commit -m "feat: tree and frame commands"
```

---

### Task 11: `grep` and `exceptions`

**Files:**
- Create: `src/sensorium/query/grep_cmd.py`, `src/sensorium/query/exceptions_cmd.py`
- Modify: `src/sensorium/cli.py` (extend `_QUERY_MODULES` with `grep_cmd, exceptions_cmd`)
- Test: `tests/test_grep_exceptions.py`

**Interfaces:**
- Consumes: `Trace`, `fmt.fmt_event`, `fmt.more_note`, `paths.find_trace`.
- Produces: `grep RUN PATTERN [--kind K] [--fn SUBSTR] [--after eN] [--limit N]` — substring match against the *rendered* `fmt_event` line (so it matches both names and formatted values), ends with `matches: N` and a continuation hint when clipped. `exceptions RUN` — uncaught (from meta), then every RAISE with its disposition: `SWALLOWED at eN <qualname> LNN (handled, never re-raised)` / `handled at eN, raised again later` / `unwound (never handled in traced code)`. Heuristic documented in the module docstring: RERAISE is not monitored, so re-raise detection is oid-based on later RAISE events.

- [ ] **Step 1: Write failing tests**

`tests/test_grep_exceptions.py`:

```python
from sensorium import cli
from tests.helpers import record_script

SWALLOW = """
ROWS = ["alice,10", "bob,20", "carol,x7", "dan,5", "erin,??"]

def parse_row(row):
    name, amount = row.split(",")
    return name, int(amount)

def load_all(rows):
    out = []
    for row in rows:
        try:
            out.append(parse_row(row))
        except Exception:
            pass
    return out

def main():
    rows = load_all(ROWS)
    print(f"total: {sum(a for _, a in rows)} from {len(rows)} rows")

if __name__ == "__main__":
    main()
"""

CRASH = """
def get(uid):
    return {1: "Alice"}.get(uid)

def main():
    get(1)
    get(7).title()

main()
"""


def _rec(tmp_path, monkeypatch, src):
    run_id, trace, r = record_script(tmp_path, src)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_grep_by_value_content(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["grep", run_id, "carol"]) == 0
    out = capsys.readouterr().out
    assert "parse_row" in out and "matches:" in out


def test_grep_kind_and_fn_filters(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CRASH)
    assert cli.main(["grep", run_id, "get", "--kind", "RETURN",
                     "--fn", "get"]) == 0
    out = capsys.readouterr().out
    assert "get -> None" in out and "get -> 'Alice'" in out


def test_grep_limit_offers_continuation(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    cli.main(["grep", run_id, "parse_row", "--limit", "1"])
    out = capsys.readouterr().out
    assert "more; continue with:" in out and "--after e" in out


def test_exceptions_flags_swallowed(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 2          # carol,x7 and erin,??
    assert "ValueError" in out and "load_all" in out


def test_exceptions_reports_uncaught(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, CRASH)
    cli.main(["exceptions", run_id])
    out = capsys.readouterr().out
    assert "uncaught: AttributeError" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_grep_exceptions.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/query/grep_cmd.py`**

```python
"""Search events by qualname or captured-value content."""
from sensorium import paths
from sensorium.query.fmt import fmt_event, more_note, parse_eref
from sensorium.store.reader import Trace

KINDS = ("CALL", "RETURN", "RAISE", "HANDLED", "LINE")


def add_parser(sub) -> None:
    p = sub.add_parser("grep", help="search events by name or value")
    p.add_argument("run")
    p.add_argument("pattern")
    p.add_argument("--kind", default=None, choices=KINDS)
    p.add_argument("--fn", default=None, help="qualname substring filter")
    p.add_argument("--after", default=None, help="event ref to resume from")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=run)


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    after = parse_eref(args.after) if args.after else 0
    shown = total = last = 0
    for e in trace.events(kind=args.kind, after=after):
        if e.code_id is None:
            continue
        if args.fn and args.fn not in trace.code(e.code_id).qualname:
            continue
        line = fmt_event(trace, e)
        if args.pattern not in line:
            continue
        total += 1
        if shown < args.limit:
            print(line)
            shown += 1
            last = e.id
    print(f"matches: {total}")
    note = more_note(total, shown,
                     f"sensorium grep {args.run} {args.pattern} "
                     f"--after e{last}")
    if note:
        print(note)
    return 0
```

- [ ] **Step 4: Implement `src/sensorium/query/exceptions_cmd.py`**

```python
"""Every raise and its disposition; silently swallowed is a first-class flag.

Heuristic (documented, v1): re-raise via bare `raise` fires RERAISE, which is
not monitored — so disposition is oid-based: a RAISE whose oid has a later
HANDLED and no later RAISE is SWALLOWED. Control-flow exceptions
(StopIteration etc.) were excluded at record time.
"""
from sensorium import paths
from sensorium.query.fmt import fmt_event, fmt_exc
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("exceptions", help="raises, handles, swallows")
    p.add_argument("run")
    p.set_defaults(func=run)


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    m = trace.meta
    if m.get("uncaught"):
        print(f"uncaught: {fmt_exc(m['uncaught'])} "
              f"(exit {m.get('exit_status')})")
    raises = trace.events(kind="RAISE")
    handles = trace.events(kind="HANDLED")
    if not raises and not m.get("uncaught"):
        print("no exceptions recorded")
        return 0
    h_by_oid: dict[int, list] = {}
    for h in handles:
        h_by_oid.setdefault(h.payload["exc"]["oid"], []).append(h)
    r_by_oid: dict[int, list] = {}
    for r in raises:
        r_by_oid.setdefault(r.payload["exc"]["oid"], []).append(r)
    print(f"raised ({len(raises)}):")
    for r in raises:
        oid = r.payload["exc"]["oid"]
        print("  " + fmt_event(trace, r))
        handled = next((h for h in h_by_oid.get(oid, []) if h.id > r.id),
                       None)
        later = [x for x in r_by_oid[oid] if x.id > r.id]
        if handled and not later:
            hq = trace.code(handled.code_id).qualname
            print(f"    SWALLOWED at e{handled.id} {hq} L{handled.line} "
                  "(handled, never re-raised)")
        elif handled:
            print(f"    handled at e{handled.id}, raised again later")
        else:
            print("    unwound (never handled in traced code)")
    return 0
```

In `cli.py` extend the import/list with `grep_cmd, exceptions_cmd`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_grep_exceptions.py -v` — Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/grep_cmd.py src/sensorium/query/exceptions_cmd.py \
        src/sensorium/cli.py tests/test_grep_exceptions.py
git commit -m "feat: grep and exceptions commands with swallowed-exception detection"
```

---

### Task 12: `flow`

**Files:**
- Create: `src/sensorium/query/flow_cmd.py`
- Modify: `src/sensorium/cli.py` (extend `_QUERY_MODULES` with `flow_cmd`)
- Test: `tests/test_flow.py`

**Interfaces:**
- Consumes: `Trace`, `fmt.fmt_event`, `paths.find_trace`.
- Produces: `flow RUN (--value LITERAL | --object SPEC) [--limit N]`. `--value` parses int/float/`None`/string and matches captured primitives (including inside container samples). `--object` takes `e<id>:<name>` or `<qualname>:<name>` (first CALL of that qualname), resolves the capture's `oid`, and matches identity across obj/seq/map captures. Each sighting prints the `fmt_event` line plus a `[role]` tag (`arg items[1].val`, `return`, `local total`). Output headers state the honesty caveat (equality/identity lineage, not true dataflow). Exposes `find_in_value(v, target, path="") -> list[str]` and `parse_literal(s)` for tests.

- [ ] **Step 1: Write failing tests**

`tests/test_flow.py`:

```python
from sensorium import cli
from tests.helpers import record_script

GRAMS = """
def shipping_cost(weight_kg):
    return 4.0 + 2.5 * weight_kg

def item_weight(item):
    return item["grams"]

def order_total(items):
    goods = sum(i["price"] for i in items)
    ship = sum(shipping_cost(item_weight(i)) for i in items)
    return round(goods + ship, 2)

def main():
    items = [{"name": "mug", "price": 12.0, "grams": 400},
             {"name": "kettle", "price": 49.0, "grams": 1800}]
    print("total:", order_total(items))

if __name__ == "__main__":
    main()
"""

ALIAS = """
def make_default():
    return {"retries": 3, "timeout": 30}

def derive_sandbox(cfg):
    sandbox = cfg
    sandbox["timeout"] = 1
    return sandbox

def main():
    prod = make_default()
    sand = derive_sandbox(prod)
    print("prod timeout:", prod["timeout"])

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, monkeypatch, src):
    run_id, trace, r = record_script(tmp_path, src)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_flow_value_traces_a_number_through_calls(tmp_path, monkeypatch,
                                                  capsys):
    run_id = _rec(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--value", "1800"]) == 0
    out = capsys.readouterr().out
    assert "item_weight -> 1800" in out
    assert "shipping_cost(weight_kg=1800)" in out
    assert "sightings:" in out and "not true dataflow" in out


def test_flow_object_shows_aliasing(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, ALIAS)
    assert cli.main(["flow", run_id, "--object", "derive_sandbox:cfg"]) == 0
    out = capsys.readouterr().out
    assert "make_default ->" in out          # same oid seen at creation...
    assert "derive_sandbox(cfg=" in out      # ...and entering the mutator
    assert "flow of object #" in out


def test_flow_object_on_primitive_is_clear_error(tmp_path, monkeypatch,
                                                 capsys):
    run_id = _rec(tmp_path, monkeypatch, GRAMS)
    assert cli.main(["flow", run_id, "--object", "shipping_cost:weight_kg"]) == 1
    assert "use --value" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_flow.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/query/flow_cmd.py`**

```python
"""Value provenance: every sighting of a value or object across the trace.

Honesty: repr/identity-based lineage over CAPTURED values (primitive
equality; oid identity for containers/objects) — not true dataflow analysis.
The output header says so.
"""
from sensorium import paths
from sensorium.query.fmt import fmt_event, fmt_value
from sensorium.store.reader import Trace


class _Oid:
    def __init__(self, oid: int) -> None:
        self.oid = oid


def parse_literal(s: str):
    if s == "None":
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def find_in_value(v: dict, target, path: str = "") -> list[str]:
    hits: list[str] = []
    k = v.get("k")
    if isinstance(target, _Oid):
        if k in ("obj", "seq", "map") and v.get("oid") == target.oid:
            hits.append(path)
    elif k == "num" and not isinstance(target, (str, bool)) \
            and target is not None and v["v"] == target:
        hits.append(path)
    elif k == "str" and isinstance(target, str) and v["v"] == target:
        hits.append(path)
    elif k == "none" and target is None:
        hits.append(path)
    if k == "seq":
        for i, x in enumerate(v.get("sample", [])):
            hits += find_in_value(x, target, f"{path}[{i}]")
    elif k == "map":
        for kk, vv in v.get("sample", []):
            hits += find_in_value(kk, target, f"{path}.key")
            hits += find_in_value(vv, target, f"{path}.val")
    return hits


def _roles(e):
    p = e.payload or {}
    if e.kind == "CALL":
        return [(f"arg {n}", v) for n, v in p.get("args", {}).items()]
    if e.kind == "RETURN" and p.get("value") is not None:
        return [("return", p["value"])]
    if e.kind == "LINE":
        return [(f"local {n}", v) for n, v in p.get("deltas", {}).items()]
    return []


def sightings(trace, target):
    out = []
    for e in trace.events():
        for role, v in _roles(e):
            for hit in find_in_value(v, target):
                out.append((e, role + hit))
    return out


def resolve_object(trace, spec: str):
    ref, sep, name = spec.rpartition(":")
    if not sep or not ref:
        return None, "object spec must be e<id>:<name> or <qualname>:<name>"
    if ref.startswith("e") and ref[1:].isdigit():
        ev = trace.event(int(ref[1:]))
    else:
        ev = next((e for e in trace.events(kind="CALL")
                   if trace.code(e.code_id).qualname == ref), None)
    if ev is None:
        return None, f"no event found for {ref!r}"
    p = ev.payload or {}
    v = (p.get("args", {}).get(name) or p.get("deltas", {}).get(name)
         or (p.get("value") if name == "return" else None))
    if v is None:
        return None, f"{name!r} not captured at e{ev.id}"
    if v.get("k") not in ("obj", "seq", "map"):
        return None, (f"{name!r} at e{ev.id} is a primitive "
                      f"({fmt_value(v)}); use --value")
    return _Oid(v["oid"]), None


def add_parser(sub) -> None:
    p = sub.add_parser("flow", help="provenance of a value or object")
    p.add_argument("run")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--value", default=None)
    g.add_argument("--object", default=None)
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=run)


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    if args.object:
        target, err = resolve_object(trace, args.object)
        if err:
            print(f"error: {err}")
            return 1
        print(f"flow of object #{target.oid} "
              "(identity-based lineage, not true dataflow)")
    else:
        target = parse_literal(args.value)
        print(f"flow of {args.value} "
              "(captured-value equality, not true dataflow)")
    found = sightings(trace, target)
    for e, role in found[: args.limit]:
        print(f"  {fmt_event(trace, e)}   [{role}]")
    print(f"sightings: {len(found)}")
    if len(found) > args.limit:
        print(f"... {len(found) - args.limit} more (raise --limit)")
    return 0
```

In `cli.py` extend the import/list with `flow_cmd`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_flow.py -v` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/query/flow_cmd.py src/sensorium/cli.py tests/test_flow.py
git commit -m "feat: flow command for value and object provenance"
```

---

### Task 13: Restricted expressions and `watch`

**Files:**
- Create: `src/sensorium/query/expr.py`, `src/sensorium/query/watch_cmd.py`
- Modify: `src/sensorium/cli.py` (extend `_QUERY_MODULES` with `watch_cmd`)
- Test: `tests/test_expr.py`, `tests/test_watch.py`

**Interfaces:**
- Consumes: `Trace`, `fmt.fmt_event`, `paths.find_trace`.
- Produces: `expr.ExprError`, `expr.NotCaptured`, `expr.NOT_CAPTURED` sentinel, `expr._Sized(n)`, `expr.resolve(captured_dict) -> value | _Sized | NOT_CAPTURED`, `expr.compile_expr(src) -> Expr` with `Expr.eval(env) -> bool`, `Expr.margin(env) -> float | None` (abs distance for a single numeric ordering comparison), `Expr.names: set[str]`. Allowed syntax: names, int/float/str/bool/None constants, single comparisons (`< <= > >= == !=`), `and`/`or`/`not`, unary minus, `+ - * / %`, and `len(name)`. Everything else raises `ExprError` at compile time. `watch RUN --at SPEC --expr EXPR [--limit N]` evaluates at each matching frame's CALL (args) and each LINE (accumulated locals), printing `sites evaluated / hits / not-captured` and, when there are no hits, up to 5 near-misses sorted by margin.

- [ ] **Step 1: Write failing tests**

`tests/test_expr.py`:

```python
import pytest

from sensorium.query.expr import (ExprError, NotCaptured, _Sized,
                                  compile_expr, resolve, NOT_CAPTURED)


def test_comparison_and_boolean_ops():
    e = compile_expr("used > 100 and not done")
    assert e.eval({"used": 150, "done": False}) is True
    assert e.eval({"used": 50, "done": False}) is False
    assert e.names == {"used", "done"}


def test_len_on_sized_and_str():
    e = compile_expr("len(buf) >= 3")
    assert e.eval({"buf": _Sized(5)}) is True
    assert e.eval({"buf": "ab"}) is False


def test_arithmetic():
    assert compile_expr("a + b * 2 == 7").eval({"a": 1, "b": 3}) is True


def test_missing_name_raises_not_captured():
    with pytest.raises(NotCaptured):
        compile_expr("x > 1").eval({})


def test_bare_container_name_is_not_captured():
    with pytest.raises(NotCaptured):
        compile_expr("buf == 3").eval({"buf": _Sized(3)})


@pytest.mark.parametrize("bad", [
    "__import__('os')", "x.attr > 1", "x[0] > 1", "f(x)", "x if y else z",
    "lambda: 1", "x < y < z",
])
def test_disallowed_syntax_rejected_at_compile(bad):
    with pytest.raises(ExprError):
        compile_expr(bad)


def test_margin_for_numeric_ordering():
    e = compile_expr("used > 100")
    assert e.margin({"used": 99}) == 1
    assert compile_expr("a == b").margin({"a": 1, "b": 2}) is None


def test_resolve_mapping():
    assert resolve({"k": "num", "v": 3}) == 3
    assert resolve({"k": "none"}) is None
    assert isinstance(resolve({"k": "seq", "type": "list", "len": 4,
                               "oid": 1}), _Sized)
    assert resolve({"k": "obj", "type": "X", "oid": 1,
                    "repr": "<X>"}) is NOT_CAPTURED
```

`tests/test_watch.py`:

```python
from sensorium import cli
from tests.helpers import record_script

BUFFER = """
def fill(buf, chunk):
    buf.extend(chunk)
    used = len(buf)
    return used

def drain(buf, n):
    del buf[:n]

def main():
    buf = []
    for size, dn in [(40, 0), (30, 10), (25, 20), (34, 30), (0, 69)]:
        fill(buf, [0] * size)
        drain(buf, dn)

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, monkeypatch, extra=()):
    run_id, trace, r = record_script(tmp_path, BUFFER, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_watch_near_miss_when_no_hits(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "used > 100"]) == 0
    out = capsys.readouterr().out
    assert "hits: 0" in out
    assert "near-misses" in out and "margin 1:" in out and "used=99" in out


def test_watch_hits_reported_with_env(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, extra=("--focus", "prog:fill"))
    cli.main(["watch", run_id, "--at", "prog:fill", "--expr", "used > 90"])
    out = capsys.readouterr().out
    assert "HIT" in out and "used=99" in out


def test_watch_counts_not_captured_sites(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)          # no focus: no locals
    cli.main(["watch", run_id, "--at", "prog:fill", "--expr", "used > 100"])
    out = capsys.readouterr().out
    assert "not-captured: 5" in out               # 5 CALL sites lack `used`
    assert "refocus" in out


def test_watch_bad_expr_is_exit_2(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["watch", run_id, "--at", "prog:fill",
                     "--expr", "__import__('os')"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_expr.py tests/test_watch.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/query/expr.py`**

```python
"""Restricted predicate evaluator over captured values. No arbitrary Python,
no live objects: names resolve to captured primitives, containers expose only
len(), anything else is NotCaptured — counted by callers, never skipped
silently."""
import ast
import operator


class ExprError(Exception):
    pass


class NotCaptured(Exception):
    pass


NOT_CAPTURED = object()


class _Sized:
    def __init__(self, n: int) -> None:
        self.n = n


_CMP = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
        ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}
_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod}


def resolve(v: dict):
    k = v.get("k")
    if k in ("num", "str", "bool"):
        return v["v"]
    if k == "none":
        return None
    if k in ("seq", "map"):
        return _Sized(v["len"])
    return NOT_CAPTURED


def _validate(node) -> None:
    if isinstance(node, ast.Expression):
        _validate(node.body)
    elif isinstance(node, ast.Constant):
        ok = isinstance(node.value, (int, float, str, bool)) or node.value is None
        if not ok:
            raise ExprError(f"unsupported constant {node.value!r}")
    elif isinstance(node, ast.Name):
        pass
    elif isinstance(node, ast.Call):
        if not (isinstance(node.func, ast.Name) and node.func.id == "len"
                and len(node.args) == 1 and not node.keywords
                and isinstance(node.args[0], ast.Name)):
            raise ExprError("only len(name) calls are allowed")
    elif isinstance(node, ast.Compare):
        if len(node.ops) != 1 or type(node.ops[0]) not in _CMP:
            raise ExprError("only single comparisons (< <= > >= == !=)")
        _validate(node.left)
        _validate(node.comparators[0])
    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            _validate(v)
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op,
                                                      (ast.Not, ast.USub)):
        _validate(node.operand)
    elif isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        _validate(node.left)
        _validate(node.right)
    else:
        raise ExprError(f"unsupported syntax: {type(node).__name__}")


class Expr:
    def __init__(self, tree: ast.Expression, names: set[str]) -> None:
        self._tree = tree
        self.names = names

    def eval(self, env: dict) -> bool:
        return bool(self._eval(self._tree.body, env))

    def _eval(self, node, env):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            val = env.get(node.id, NOT_CAPTURED)
            if val is NOT_CAPTURED or isinstance(val, _Sized):
                raise NotCaptured(node.id)
            return val
        if isinstance(node, ast.Call):            # validated: len(name)
            val = env.get(node.args[0].id, NOT_CAPTURED)
            if isinstance(val, _Sized):
                return val.n
            if isinstance(val, str):
                return len(val)
            raise NotCaptured(node.args[0].id)
        if isinstance(node, ast.Compare):
            return _CMP[type(node.ops[0])](
                self._eval(node.left, env),
                self._eval(node.comparators[0], env))
        if isinstance(node, ast.BoolOp):
            vals = [self._eval(v, env) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.UnaryOp):
            v = self._eval(node.operand, env)
            return (not v) if isinstance(node.op, ast.Not) else -v
        return _BIN[type(node.op)](self._eval(node.left, env),
                                   self._eval(node.right, env))

    def margin(self, env) -> float | None:
        node = self._tree.body
        if not (isinstance(node, ast.Compare)
                and type(node.ops[0]) in (ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
            return None
        try:
            lhs = self._eval(node.left, env)
            rhs = self._eval(node.comparators[0], env)
        except NotCaptured:
            return None
        if (isinstance(lhs, (int, float)) and isinstance(rhs, (int, float))
                and not isinstance(lhs, bool) and not isinstance(rhs, bool)):
            return abs(lhs - rhs)
        return None


def compile_expr(src: str) -> Expr:
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise ExprError(f"bad expression: {e}") from None
    _validate(tree)
    names = {n.id for n in ast.walk(tree)
             if isinstance(n, ast.Name) and n.id != "len"}
    return Expr(tree, names)
```

- [ ] **Step 4: Implement `src/sensorium/query/watch_cmd.py`**

```python
"""Predicate over captured state at every matching site; near-misses for
numeric boundaries. Sites that lack the needed capture are counted and
reported — never silently skipped."""
from pathlib import Path

from sensorium import paths
from sensorium.query.expr import (NOT_CAPTURED, ExprError, NotCaptured,
                                  _Sized, compile_expr, resolve)
from sensorium.query.fmt import fmt_event
from sensorium.store.reader import Trace


def add_parser(sub) -> None:
    p = sub.add_parser("watch", help="predicate over captured state")
    p.add_argument("run")
    p.add_argument("--at", required=True, help="module:qualname or qualname")
    p.add_argument("--expr", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=run)


def site_matches(code, at: str) -> bool:
    mod, _, qual = at.partition(":")
    stem = Path(code.file).stem
    if qual:
        return code.qualname == qual and (stem == mod or f"/{mod}" in code.file)
    return code.qualname == at or stem == at


def evaluate(trace, at: str, expr):
    hits, near = [], []
    evaluated = not_captured = 0
    match_codes = {c.id for c in trace.codes() if site_matches(c, at)}
    for f in trace.frames():
        if f.code_id not in match_codes:
            continue
        call = trace.event(f.call_event_id)
        env: dict = {}
        if call:
            for n, v in (call.payload or {}).get("args", {}).items():
                env[n] = resolve(v)
        sites = [(call, dict(env))] if call else []
        for e in trace.frame_events(f.id):
            if e.kind != "LINE":
                continue
            for n, v in e.payload.get("deltas", {}).items():
                env[n] = resolve(v)
            sites.append((e, dict(env)))
        for e, env2 in sites:
            evaluated += 1
            try:
                if expr.eval(env2):
                    hits.append((e, env2))
                else:
                    m = expr.margin(env2)
                    if m is not None:
                        near.append((m, e, env2))
            except NotCaptured:
                not_captured += 1
    near.sort(key=lambda t: (t[0], t[1].id))
    return hits, near, evaluated, not_captured


def _env_line(expr, env) -> str:
    parts = []
    for n in sorted(expr.names):
        v = env.get(n, NOT_CAPTURED)
        if v is NOT_CAPTURED:
            parts.append(f"{n}=?")
        elif isinstance(v, _Sized):
            parts.append(f"len({n})={v.n}")
        else:
            parts.append(f"{n}={v!r}")
    return "  ".join(parts)


def run(args) -> int:
    trace = Trace.open(paths.find_trace(args.run))
    try:
        expr = compile_expr(args.expr)
    except ExprError as e:
        print(f"error: {e}")
        return 2
    hits, near, evaluated, not_captured = evaluate(trace, args.at, expr)
    print(f"watch {args.expr!r} at {args.at}")
    tail = "  (refocus to capture more)" if not_captured else ""
    print(f"sites evaluated: {evaluated}   hits: {len(hits)}   "
          f"not-captured: {not_captured}{tail}")
    if evaluated == 0:
        print(f"no frames matched {args.at!r}; check the qualname "
              "(sensorium info shows hot functions)")
    for e, env in hits[: args.limit]:
        print(f"  HIT  {fmt_event(trace, e)}   {_env_line(expr, env)}")
    if not hits and near:
        print("near-misses (closest approaches):")
        for m, e, env in near[:5]:
            print(f"  margin {m:g}: {fmt_event(trace, e)}   "
                  f"{_env_line(expr, env)}")
    return 0
```

In `cli.py` extend the import/list with `watch_cmd`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_expr.py tests/test_watch.py -v` — Expected: all PASS.
(In `test_watch_near_miss…`: `fill` runs 5 times and `used` — the length right
after each fill — takes the values 40, 70, 85, 99, 69. The buffer's high-water
mark is 99, so `used > 100` never fires and the closest approach is margin 1 at
`used=99`. Without `--focus`, `used` is a local that was never captured, which
is why the third test sees `not-captured: 5` — one CALL site per activation.)

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/expr.py src/sensorium/query/watch_cmd.py \
        src/sensorium/cli.py tests/test_expr.py tests/test_watch.py
git commit -m "feat: restricted expression evaluator and watch command"
```

---

### Task 14: `diff`

**Files:**
- Create: `src/sensorium/query/diff_cmd.py`
- Modify: `src/sensorium/cli.py` (extend `_QUERY_MODULES` with `diff_cmd`)
- Test: `tests/test_diff.py`

**Interfaces:**
- Consumes: `Trace.causal_stream`, `Trace.fingerprints`, `fmt`, `paths.find_trace`.
- Produces: `diff_cmd.first_divergence(stream_a, stream_b) -> int | None` (index of the first differing element, `None` if one is a prefix of the other and lengths match, else the shorter length). `diff_cmd.compare(trace_a, trace_b) -> dict` with keys `verdict` (`"MATCH"` / `"DIVERGED"`), `index`, `a_event`, `b_event`, `a_desc`, `b_desc`. **This function is what `refocus` (Task 15) reuses — do not duplicate the comparison logic there.** CLI: `diff RUN1 RUN2 [--context N]` prints per-thread fingerprint comparison, then for a divergence the last N common causal steps followed by the two sides' next steps, then the surrounding `tree --around` hint for each side.

- [ ] **Step 1: Write failing tests**

`tests/test_diff.py`:

```python
from sensorium import cli
from sensorium.query.diff_cmd import first_divergence
from sensorium.store.reader import Trace
from tests.helpers import record_script

BRANCH = """
import sys

def gold(total):
    return total * 0.80

def silver(total):
    return total * 0.95

def price(points, total):
    if points > 1000:
        return gold(total)
    return silver(total)

def main():
    price(int(sys.argv[1]), 100.0)

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, name, argv):
    (tmp_path / "prog.py").write_text(BRANCH)
    from tests.helpers import run_cli
    import re
    sdir = tmp_path / "sdir"
    r = run_cli(["run", "--", "prog.py", *argv], cwd=tmp_path,
                sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def test_first_divergence_pure_function():
    a = [("p.py", "main", "CALL", 1), ("p.py", "gold", "CALL", 2)]
    b = [("p.py", "main", "CALL", 1), ("p.py", "silver", "CALL", 2)]
    assert first_divergence(a, b) == 1
    assert first_divergence(a, a) is None
    assert first_divergence(a, a[:1]) == 1


def test_identical_runs_match(tmp_path, monkeypatch, capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2]) == 0
    out = capsys.readouterr().out
    assert "MATCH" in out and "identical" in out


def test_divergent_runs_pinpoint_branch(tmp_path, monkeypatch, capsys):
    r1 = _rec(tmp_path, "a", ["500"])
    r2 = _rec(tmp_path, "b", ["1500"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["diff", r1, r2]) == 1
    out = capsys.readouterr().out
    assert "DIVERGED" in out
    assert "silver" in out and "gold" in out
    assert "tree" in out            # drill-down hint on both sides
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_diff.py -v` — Expected: FAIL.

- [ ] **Step 3: Implement `src/sensorium/query/diff_cmd.py`**

```python
"""Compare two runs' causal streams and pinpoint the first divergence.

Causal stream = (file, qualname, kind) per CAUSAL_KINDS event on the main
thread. Values and timing are excluded by construction (see fingerprint.py),
so a MATCH means the same execution path, not merely a similar one.
"""
from sensorium import paths
from sensorium.query.fmt import fmt_event
from sensorium.store.reader import Trace


def first_divergence(a: list, b: list) -> int | None:
    for i, (x, y) in enumerate(zip(a, b)):
        if x[:3] != y[:3]:
            return i
    if len(a) != len(b):
        return min(len(a), len(b))
    return None


def _desc(step) -> str:
    file, qual, kind, eid = step
    return f"e{eid} {kind:<7} {qual}  ({file})"


def compare(trace_a: Trace, trace_b: Trace) -> dict:
    sa = trace_a.causal_stream()
    sb = trace_b.causal_stream()
    i = first_divergence(sa, sb)
    if i is None:
        return {"verdict": "MATCH", "index": None, "a_event": None,
                "b_event": None, "a_desc": None, "b_desc": None,
                "a_stream": sa, "b_stream": sb}
    a_step = sa[i] if i < len(sa) else None
    b_step = sb[i] if i < len(sb) else None
    return {
        "verdict": "DIVERGED",
        "index": i,
        "a_event": a_step[3] if a_step else None,
        "b_event": b_step[3] if b_step else None,
        "a_desc": _desc(a_step) if a_step else "(stream ended)",
        "b_desc": _desc(b_step) if b_step else "(stream ended)",
        "a_stream": sa, "b_stream": sb,
    }


def print_comparison(trace_a, trace_b, res, name_a, name_b, context=3) -> None:
    fa, fb = trace_a.fingerprints(), trace_b.fingerprints()
    print(f"A {name_a}: threads {len(fa)}  "
          f"main fp {list(fa.values())[0][0] if fa else '-'}")
    print(f"B {name_b}: threads {len(fb)}  "
          f"main fp {list(fb.values())[0][0] if fb else '-'}")
    if res["verdict"] == "MATCH":
        n = len(res["a_stream"])
        print(f"verdict: MATCH — identical causal streams ({n} events)")
        return
    i = res["index"]
    print(f"verdict: DIVERGED at causal step {i}")
    for step in res["a_stream"][max(0, i - context):i]:
        print(f"  common  {_desc(step)}")
    print(f"  A:      {res['a_desc']}")
    print(f"  B:      {res['b_desc']}")
    if res["a_event"]:
        print(f"drill into A: sensorium tree {name_a} "
              f"--around e{res['a_event']}")
    if res["b_event"]:
        print(f"drill into B: sensorium tree {name_b} "
              f"--around e{res['b_event']}")


def add_parser(sub) -> None:
    p = sub.add_parser("diff", help="first divergence between two runs")
    p.add_argument("run_a")
    p.add_argument("run_b")
    p.add_argument("--context", type=int, default=3)
    p.set_defaults(func=run)


def run(args) -> int:
    pa, pb = paths.find_trace(args.run_a), paths.find_trace(args.run_b)
    ta, tb = Trace.open(pa), Trace.open(pb)
    if ta.meta.get("argv") != tb.meta.get("argv"):
        print(f"note: different commands — A: {' '.join(ta.meta.get('argv', []))}"
              f"   B: {' '.join(tb.meta.get('argv', []))}")
    res = compare(ta, tb)
    print_comparison(ta, tb, res, pa.stem, pb.stem, args.context)
    return 0 if res["verdict"] == "MATCH" else 1
```

In `cli.py` extend the import/list with `diff_cmd`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_diff.py -v` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/query/diff_cmd.py src/sensorium/cli.py tests/test_diff.py
git commit -m "feat: diff command pinpointing first causal divergence"
```

---

### Task 15: `refocus`

**Files:**
- Create: `src/sensorium/query/refocus_cmd.py`
- Modify: `src/sensorium/cli.py` (extend `_QUERY_MODULES` with `refocus_cmd`)
- Test: `tests/test_refocus.py`

**Interfaces:**
- Consumes: `boot.run_target`, `boot.git_info`, `diff_cmd.compare`, `Trace`, `paths`.
- Produces: `refocus RUN --focus SPEC [--focus SPEC]... [--window QUALNAME]`. Preconditions (refuse with exit 2): original `stdin_consumed` is true; original `incomplete` is true; target no longer resolvable. Warning (proceed): `git_dirty_hash` differs from the original. Re-runs from the original `cwd`, with `refocus_of` set. After the rerun, compares causal streams via `diff_cmd.compare` and writes to the **new** trace: `refocus_verdict` = `"MATCH"` or `"DIVERGED"`, plus `refocus_diverge_index`/`refocus_diverge_a`/`refocus_diverge_b` on divergence. Exit 0 on MATCH, 1 on DIVERGED (the trace is still written and queryable). `info` (Task 9) already prints `refocus-of` + verdict.

- [ ] **Step 1: Write failing tests**

`tests/test_refocus.py`:

```python
import re

from sensorium import cli
from sensorium.store.reader import Trace
from tests.helpers import record_script, run_cli

LOOP = """
def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    print("sum:", accumulate([5, 10, 20]))

if __name__ == "__main__":
    main()
"""

RANDOM = """
import random

def pick():
    return random.random() < 0.5

def left():
    return "L"

def right():
    return "R"

def main():
    print(left() if pick() else right())

if __name__ == "__main__":
    main()
"""

READS_STDIN = """
def main():
    line = input()
    print("got", line)

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, src, stdin_text=None):
    run_id, trace, r = record_script(tmp_path, src, stdin_text=stdin_text)
    assert run_id, r.stderr
    return run_id, tmp_path / "sdir"


def _refocus(tmp_path, sdir, run_id, extra):
    return run_cli(["refocus", run_id, *extra], cwd=tmp_path,
                   sensorium_dir=sdir)


def test_refocus_match_captures_deeper_state(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    r = _refocus(tmp_path, sdir, run_id, ["--focus", "prog:accumulate"])
    assert r.returncode == 0, r.stderr + r.stdout
    assert "MATCH" in r.stdout and "verified same execution" in r.stdout
    new_id = re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)
    t = Trace.open(sdir / "traces" / f"{new_id}.db")
    assert t.meta["refocus_of"] == run_id
    assert t.meta["refocus_verdict"] == "MATCH"
    assert len(t.events(kind="LINE")) > 0          # deeper capture landed


def test_refocus_reports_divergence_for_nondeterministic(tmp_path):
    run_id, sdir = _rec(tmp_path, RANDOM)
    # rerun until the coin lands differently; 12 attempts makes a false
    # "always MATCH" essentially impossible (p < 1/4096)
    verdicts = set()
    for _ in range(12):
        r = _refocus(tmp_path, sdir, run_id, ["--focus", "prog:pick"])
        verdicts.add("DIVERGED" if r.returncode == 1 else "MATCH")
        if "DIVERGED" in verdicts:
            assert "DIVERGED" in r.stdout
            new_id = re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)
            t = Trace.open(sdir / "traces" / f"{new_id}.db")
            assert t.meta["refocus_verdict"] == "DIVERGED"
            assert t.meta["refocus_diverge_index"] is not None
            return
    raise AssertionError(f"never observed divergence; verdicts={verdicts}")


def test_refocus_refuses_when_stdin_consumed(tmp_path):
    run_id, sdir = _rec(tmp_path, READS_STDIN, stdin_text="hello\n")
    r = _refocus(tmp_path, sdir, run_id, ["--focus", "prog:main"])
    assert r.returncode == 2
    assert "stdin" in r.stderr and "non-refocusable" in r.stderr


def test_refocus_warns_on_changed_source(tmp_path):
    run_id, sdir = _rec(tmp_path, LOOP)
    (tmp_path / "prog.py").write_text(LOOP.replace("[5, 10, 20]", "[1, 2]"))
    r = _refocus(tmp_path, sdir, run_id, ["--focus", "prog:accumulate"])
    # source changed → the rerun is a different execution; must not claim MATCH
    assert r.returncode == 1 and "DIVERGED" in r.stdout
```

Note on the last test: the loop body count changes (3 iterations → 2), so the
causal stream length differs and `compare` reports DIVERGED. If the source
edit had preserved the causal stream exactly, MATCH would be the honest
verdict — the fingerprint speaks to execution path, not file bytes, and the
`git_dirty_hash` warning covers the rest.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_refocus.py -v` — Expected: FAIL (unknown subcommand).

- [ ] **Step 3: Implement `src/sensorium/query/refocus_cmd.py`**

```python
"""Re-run a recorded command with deeper capture, then verify — via causal
fingerprints — that the rerun was the same execution.

MATCH: the new trace answers questions about the original mystery.
DIVERGED: a different execution; still queryable, permanently labeled.
Nondeterminism is not replayed (spec section 4) — DIVERGED is the honest
answer for a nondeterministic program.
"""
import os
import sys

from sensorium import paths
from sensorium.query.diff_cmd import compare, print_comparison
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter   # noqa: F401  (schema parity)
from sensorium.store import db


def add_parser(sub) -> None:
    p = sub.add_parser("refocus", help="re-run with deeper capture, verified")
    p.add_argument("run")
    p.add_argument("--focus", action="append", default=[], required=True)
    p.add_argument("--window", default=None)
    p.set_defaults(func=run)


def _preflight(meta) -> str | None:
    if meta.get("stdin_consumed"):
        return ("original run consumed stdin — marked non-refocusable "
                "(a rerun could not be the same execution)")
    if meta.get("incomplete"):
        return ("original trace is INCOMPLETE — its causal stream is "
                "truncated, so a rerun cannot be verified against it")
    return None


def run(args) -> int:
    from sensorium.record import boot

    orig_path = paths.find_trace(args.run)
    orig = Trace.open(orig_path)
    meta = orig.meta
    problem = _preflight(meta)
    if problem:
        print(f"error: {problem}", file=sys.stderr)
        return 2

    cwd = meta.get("cwd")
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)
    now = boot.git_info(os.getcwd())
    if (meta.get("git_dirty_hash") and now["git_dirty_hash"]
            and meta["git_dirty_hash"] != now["git_dirty_hash"]):
        print("warning: working tree changed since the original run; "
              "the rerun may not reproduce it")

    argv = meta.get("argv") or []
    try:
        new_id, exit_status = boot.run_target(
            argv, focus=args.focus, include=meta.get("include") or (),
            exclude=meta.get("exclude") or (), window=args.window,
            refocus_of=meta.get("run_id", orig_path.stem))
    except boot.TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    new_path = paths.traces_dir() / f"{new_id}.db"
    new = Trace.open(new_path)
    res = compare(orig, new)

    conn = db.open_trace(new_path)
    db.set_meta(conn, "refocus_verdict", res["verdict"])
    if res["verdict"] == "DIVERGED":
        db.set_meta(conn, "refocus_diverge_index", res["index"])
        db.set_meta(conn, "refocus_diverge_a", res["a_desc"])
        db.set_meta(conn, "refocus_diverge_b", res["b_desc"])
    conn.commit()
    conn.close()

    print(f"run: {new_id}")
    print(f"trace: {new_path}")
    print(f"refocus-of: {orig_path.stem}   focus: {', '.join(args.focus)}"
          + (f"   window: {args.window}" if args.window else ""))
    print_comparison(orig, new, res, orig_path.stem, new_path.stem)
    if res["verdict"] == "MATCH":
        print("verified same execution — answers from this trace are answers "
              "about the original run")
        return 0
    print("DIVERGED — this trace is a DIFFERENT execution than "
          f"{orig_path.stem}; it is still queryable, and every info header "
          "will say so")
    return 1
```

In `cli.py` extend the import/list with `refocus_cmd`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_refocus.py -v` — Expected: all PASS.
Full suite: `.venv/bin/pytest` — Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add src/sensorium/query/refocus_cmd.py src/sensorium/cli.py \
        tests/test_refocus.py
git commit -m "feat: refocus with fingerprint-verified MATCH/DIVERGED verdicts"
```

---

### Task 16: Seeded-bug corpus and harness

**Files:**
- Create: `corpus/run_corpus.py`, and for each of the ten programs `corpus/<name>/main.py` + `corpus/<name>/questions.yaml`
- Test: `tests/test_corpus.py`

**Interfaces:**
- Consumes: the whole CLI.
- Produces: `run_corpus.load_cases(root) -> list[Case]`, `run_corpus.run_case(case, workdir) -> CaseResult`, `run_corpus.main(argv) -> int` (exit 0 iff every question's assertions hold). `questions.yaml` schema, validated by the harness (unknown keys are an error, not ignored):

```yaml
program: main.py            # required
argv: []                    # optional args to the program
record: {focus: [], window: null}   # optional recording options
second_run: {argv: ["1500"]}        # optional; its id substitutes as $RUN2
questions:
  - id: short-slug                       # required, unique in file
    ask: plain-language question          # required
    truth: the known ground-truth answer  # required (documentation)
    why_logs_fail: why print/logging cannot answer this   # required
    command: ["grep", "$RUN", "carol"]    # required; $RUN → run id,
                                          #   $RUN2 → second_run's id
    expect_contains: ["parse_row"]        # required (list, all must appear)
    expect_absent: []                     # optional
    expect_exit: 0                        # optional, default 0
```

`second_run` exists so `diff` — which is meaningless against a single trace —
gets real corpus coverage: the same program is recorded twice with different
argv, and the question diffs them.

- [ ] **Step 1: Write the harness `corpus/run_corpus.py`**

```python
"""Record each corpus program, run its pre-registered questions, and verify
the answers against known ground truth.

This is the tool's regression suite: every question was registered BEFORE the
query layer was finished, and the ground truth is known because the bug was
planted deliberately.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
ALLOWED_Q_KEYS = {"id", "ask", "truth", "why_logs_fail", "command",
                  "expect_contains", "expect_absent", "expect_exit"}
ALLOWED_TOP_KEYS = {"program", "argv", "record", "second_run", "questions"}


@dataclass
class Case:
    name: str
    dir: Path
    program: str
    argv: list = field(default_factory=list)
    record: dict = field(default_factory=dict)
    second_run: dict | None = None
    questions: list = field(default_factory=list)


@dataclass
class CaseResult:
    name: str
    failures: list = field(default_factory=list)
    passed: int = 0


def load_cases(root: Path = ROOT) -> list[Case]:
    cases = []
    for qfile in sorted(root.glob("*/questions.yaml")):
        spec = yaml.safe_load(qfile.read_text())
        extra = set(spec) - ALLOWED_TOP_KEYS
        if extra:
            raise ValueError(f"{qfile}: unknown keys {sorted(extra)}")
        for q in spec["questions"]:
            bad = set(q) - ALLOWED_Q_KEYS
            if bad:
                raise ValueError(f"{qfile}:{q.get('id')}: unknown {sorted(bad)}")
            for required in ("id", "ask", "truth", "why_logs_fail",
                             "command", "expect_contains"):
                if required not in q:
                    raise ValueError(f"{qfile}: question missing {required!r}")
        cases.append(Case(qfile.parent.name, qfile.parent, spec["program"],
                          spec.get("argv", []), spec.get("record") or {},
                          spec.get("second_run"), spec["questions"]))
    return cases


def _cli(args, cwd, sdir, capture=True):
    return subprocess.run([sys.executable, "-m", "sensorium", *args],
                          cwd=cwd, capture_output=capture, text=True,
                          env={**os.environ, "SENSORIUM_DIR": str(sdir)})


def _record(case: Case, wd: Path, sdir: Path, argv) -> tuple[str | None, str]:
    rec = ["run"]
    for f in case.record.get("focus") or []:
        rec += ["--focus", f]
    if case.record.get("window"):
        rec += ["--window", case.record["window"]]
    rec += ["--", case.program, *[str(a) for a in argv]]
    r = _cli(rec, wd, sdir)
    m = re.search(r"^run: (\S+)$", r.stdout, re.M)
    return (m.group(1) if m else None), r.stderr


def run_case(case: Case, workdir: Path) -> CaseResult:
    res = CaseResult(case.name)
    wd = workdir / case.name
    shutil.copytree(case.dir, wd)
    sdir = wd / ".sensorium"
    run_id, err = _record(case, wd, sdir, case.argv)
    if run_id is None:
        res.failures.append(f"{case.name}: recording failed: {err[:400]}")
        return res
    run_id2 = None
    if case.second_run is not None:
        run_id2, err2 = _record(case, wd, sdir,
                                case.second_run.get("argv", []))
        if run_id2 is None:
            res.failures.append(
                f"{case.name}: second recording failed: {err2[:400]}")
            return res
    subs = {"$RUN": run_id, "$RUN2": run_id2}
    for q in case.questions:
        if "$RUN2" in q["command"] and run_id2 is None:
            res.failures.append(
                f"{case.name}/{q['id']}: uses $RUN2 but no second_run declared")
            continue
        cmd = [subs.get(a, str(a)) for a in q["command"]]
        out = _cli(cmd, wd, sdir)
        text = out.stdout + out.stderr
        expect_exit = q.get("expect_exit", 0)
        if out.returncode != expect_exit:
            res.failures.append(
                f"{case.name}/{q['id']}: exit {out.returncode} != {expect_exit}")
        for needle in q["expect_contains"]:
            if needle not in text:
                res.failures.append(
                    f"{case.name}/{q['id']}: missing {needle!r}\n"
                    f"    ask: {q['ask']}\n    got: {text[:400]}")
        for needle in q.get("expect_absent", []):
            if needle in text:
                res.failures.append(
                    f"{case.name}/{q['id']}: unexpected {needle!r}")
        res.passed += 1
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="run the sensorium corpus")
    ap.add_argument("--only", default=None, help="run one case by name")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    cases = [c for c in load_cases()
             if args.only is None or c.name == args.only]
    if not cases:
        print("no cases found", file=sys.stderr)
        return 2
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            results.append(run_case(case, Path(tmp)))
    failures = [f for r in results for f in r.failures]
    if args.json:
        print(json.dumps({"cases": len(results),
                          "questions": sum(r.passed for r in results),
                          "failures": failures}, indent=2))
    else:
        for r in results:
            mark = "FAIL" if r.failures else "ok"
            print(f"{mark:>4}  {r.name}  ({r.passed} questions)")
        for f in failures:
            print("  " + f)
        print(f"\n{len(results)} cases, "
              f"{sum(r.passed for r in results)} questions, "
              f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Write the ten corpus programs and their questions**

Each directory gets `main.py` (the seeded bug) and `questions.yaml`. Two are
written out in full below; the remaining eight follow the identical shape —
**write them all**, using the source already exercised in the task tests where
noted, so the corpus and the unit tests reinforce each other.

`corpus/silent_swallow/main.py` (source: `SWALLOW` from Task 11):

```python
"""Seeded bug: the except clause swallows bad rows, so the total is wrong
and nothing in the output says rows were dropped."""
ROWS = ["alice,10", "bob,20", "carol,x7", "dan,5", "erin,??"]


def parse_row(row):
    name, amount = row.split(",")
    return name, int(amount)


def load_all(rows):
    out = []
    for row in rows:
        try:
            out.append(parse_row(row))
        except Exception:
            pass
    return out


def main():
    rows = load_all(ROWS)
    print(f"total: {sum(a for _, a in rows)} from {len(rows)} rows")


if __name__ == "__main__":
    main()
```

`corpus/silent_swallow/questions.yaml`:

```yaml
program: main.py
questions:
  - id: what-was-dropped
    ask: The total is lower than expected. Which rows never made it in, and why?
    truth: >
      Two rows raised ValueError inside parse_row ("carol,x7" and "erin,??")
      and were swallowed by the bare `except Exception: pass` in load_all.
    why_logs_fail: >
      The except clause has no logging at all. Nothing is printed for the
      dropped rows, so stdout shows only a plausible-looking smaller total.
    command: ["exceptions", "$RUN"]
    expect_contains: ["SWALLOWED", "ValueError", "load_all"]
  - id: which-inputs
    ask: Which input values produced the failures?
    truth: parse_row was called with "carol,x7" and "erin,??".
    why_logs_fail: The inputs are never printed; only the aggregate total is.
    command: ["grep", "$RUN", "carol", "--kind", "CALL"]
    expect_contains: ["parse_row"]
```

`corpus/unit_mismatch/main.py` (source: `GRAMS` from Task 12):

```python
"""Seeded bug: item_weight returns grams, but shipping_cost expects kilograms,
so shipping is ~1000x too large. Only the final total is printed."""


def shipping_cost(weight_kg):
    return 4.0 + 2.5 * weight_kg


def item_weight(item):
    return item["grams"]          # BUG: grams, not kg


def order_total(items):
    goods = sum(i["price"] for i in items)
    ship = sum(shipping_cost(item_weight(i)) for i in items)
    return round(goods + ship, 2)


def main():
    items = [{"name": "mug", "price": 12.0, "grams": 400},
             {"name": "kettle", "price": 49.0, "grams": 1800}]
    print("total:", order_total(items))


if __name__ == "__main__":
    main()
```

`corpus/unit_mismatch/questions.yaml`:

```yaml
program: main.py
questions:
  - id: where-did-1800-go
    ask: Where does the value 1800 travel, and what consumes it?
    truth: >
      item_weight returns 1800 (grams) and it enters shipping_cost as
      weight_kg — the unit mismatch is visible at that call boundary.
    why_logs_fail: >
      Only the final total is printed. No intermediate weight or shipping
      figure is logged anywhere, so the 1000x error is invisible.
    command: ["flow", "$RUN", "--value", "1800"]
    expect_contains: ["item_weight -> 1800", "shipping_cost(weight_kg=1800)"]
  - id: what-did-shipping-return
    ask: What did shipping_cost actually return for each item?
    truth: 1004.0 for the mug (400 g) and 4504.0 for the kettle (1800 g).
    why_logs_fail: Return values are never printed; only their rounded sum is.
    command: ["grep", "$RUN", "shipping_cost", "--kind", "RETURN"]
    expect_contains: ["4504.0", "1004.0"]
```

Remaining eight, same structure:

| Directory | Seeded bug | Source | Registered command(s) | Key `expect_contains` |
|---|---|---|---|---|
| `aliasing` | `derive_sandbox` mutates the dict it was handed, so the prod config's timeout changes | `ALIAS` (Task 12) | `flow $RUN --object derive_sandbox:cfg` | `make_default ->`, `derive_sandbox(cfg=` |
| `near_miss` | Buffer high-water mark reaches 99 but the alert fires at >100, so it never triggers | `BUFFER` (Task 13), record with `focus: [main:fill]` | `watch $RUN --at main:fill --expr 'used > 100'` | `hits: 0`, `near-misses`, `used=99` |
| `wrong_branch` | Loyalty tier boundary uses `>` where the spec says `>=`, so exactly-1000-point orders get the wrong discount | `SRC` (Task 10) | `tree $RUN` | `silver(`, `gold(` |
| `pass_vs_fail` | Boundary bug: `points > 1000` should be `>=`, so an exactly-1000-point order silently takes the silver path | `BRANCH` (Task 14) with `argv: ["1000"]` and `second_run: {argv: ["1001"]}` | `diff $RUN $RUN2` with `expect_exit: 1` | `DIVERGED`, `silver`, `gold` |
| `none_propagation` | A lookup miss returns `None`, which flows two calls deep before `.title()` raises `AttributeError` | `CRASH` (Task 11) | `exceptions $RUN`, `flow $RUN --value None` | `uncaught: AttributeError`, `get -> None` |
| `double_call` | A retry wrapper calls the charge function twice on a slow path, double-charging | new: `charge(order)` invoked from both `submit` and its retry branch | `tree $RUN`, `grep $RUN charge --kind CALL` | two `charge(` lines, `matches: 2` |
| `stale_cache` | A memo dict keyed on a mutable field returns a stale value after the field changes | new: `cache[key]` populated before mutation | `flow $RUN --object build_key:record` | `cache`, the pre-mutation value |
| `nondeterministic` | Run-to-run varying branch; **the registered ground truth is that refocus reports DIVERGED** — see the note below for why it is not `random` | see note | `refocus $RUN --focus main:pick` with `expect_exit: 1` | `DIVERGED`, `DIFFERENT execution` |

**Note on `nondeterministic`.** A `random.random()` coin flip (Task 15's
`RANDOM`) is the honest illustration but a *flaky corpus case*: a refocus has
roughly even odds of landing on MATCH, and a suite that fails half the time
teaches nobody anything. Use a program whose branch is nondeterministic
**deterministically**: it reads and increments a counter in a sidecar file, so
the first recording takes the left branch and the refocus takes the right one.
The verdict is guaranteed DIVERGED, and the reason is exactly the real one —
sensorium does not replay state outside the process, so the rerun genuinely
was a different execution. Say this in the case's `truth` field so the next
reader does not "fix" it back into a coin flip:

```python
"""Seeded property: this program's branch depends on state outside the
process (a counter file), so no rerun reproduces the previous execution.
Ground truth: refocus must report DIVERGED, never MATCH."""
from pathlib import Path

COUNTER = Path("run_count.txt")


def pick():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    return n % 2 == 0


def left():
    return "L"


def right():
    return "R"


def main():
    print(left() if pick() else right())


if __name__ == "__main__":
    main()
```

The corpus harness copies each case into a fresh temp dir per run, so the
counter starts clean every time the suite runs.

- [ ] **Step 3: Write the corpus test wrapper**

`tests/test_corpus.py`:

```python
import pytest

yaml = pytest.importorskip("yaml")

from corpus import run_corpus       # noqa: E402


def test_all_cases_load_and_validate():
    cases = run_corpus.load_cases()
    assert len(cases) >= 10
    ids = [(c.name, q["id"]) for c in cases for q in c.questions]
    assert len(ids) == len(set(ids))


def test_corpus_passes():
    assert run_corpus.main([]) == 0
```

Add `corpus/__init__.py` (empty) so the import works, and ensure
`pyproject.toml`'s `[tool.pytest.ini_options]` has `pythonpath = ["."]`.

- [ ] **Step 4: Run the corpus and the wrapper**

Run: `.venv/bin/python corpus/run_corpus.py` — Expected: `10 cases, N questions, 0 failures`.
Run: `.venv/bin/pytest tests/test_corpus.py -v` — Expected: PASS.

Any question that fails here is either a real gap in the query layer (fix the
tool) or a mis-registered expectation (fix the yaml **only** if the ground
truth was wrong — never loosen an expectation to make a weak answer pass).

- [ ] **Step 5: Commit**

```bash
git add corpus tests/test_corpus.py pyproject.toml
git commit -m "test: seeded-bug corpus with pre-registered questions and harness"
```

---

### Task 17: Overhead benchmark, coverage gate, and README

**Files:**
- Create: `corpus/_bench/bench.py`, `README.md`
- Modify: `corpus/run_corpus.py` (add `--bench`)
- Test: `tests/test_bench.py`

**Interfaces:**
- Consumes: the CLI, `time.perf_counter`.
- Produces: `bench.measure(program, focus=None, reps=3) -> dict` with `baseline_s`, `recorded_s`, `multiplier`; `run_corpus.main(["--bench"])` prints a table of default-depth and focused multipliers and always exits 0 (it reports, it does not gate — overhead is a tracked fact, not a pass/fail).

- [ ] **Step 1: Write the benchmark program and harness**

`corpus/_bench/bench.py`:

```python
"""Measure recording overhead: baseline vs default-depth vs focused."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKLOAD = '''
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

def main():
    total = 0
    for i in range(18):
        total += fib(i)
    print("total:", total)

if __name__ == "__main__":
    main()
'''


def _time(cmd, cwd, env, reps):
    best = None
    for _ in range(reps):
        t0 = time.perf_counter()
        subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, check=True)
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best


def measure(focus=None, reps=3) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        (wd / "prog.py").write_text(WORKLOAD)
        env = {**os.environ, "SENSORIUM_DIR": str(wd / ".sensorium")}
        base = _time([sys.executable, "prog.py"], wd, env, reps)
        rec = ["run"]
        if focus:
            rec += ["--focus", focus]
        rec += ["--", "prog.py"]
        recorded = _time([sys.executable, "-m", "sensorium", *rec], wd, env,
                         reps)
    return {"baseline_s": round(base, 3), "recorded_s": round(recorded, 3),
            "multiplier": round(recorded / base, 1)}


def report() -> dict:
    default = measure()
    focused = measure(focus="prog:fib")
    print(f"{'tier':<10} {'baseline':>9} {'recorded':>9} {'x':>6}")
    for name, m in (("default", default), ("focused", focused)):
        print(f"{name:<10} {m['baseline_s']:>9} {m['recorded_s']:>9} "
              f"{m['multiplier']:>6}")
    return {"default": default, "focused": focused}


if __name__ == "__main__":
    report()
```

In `corpus/run_corpus.py`, add to `main`'s parser and dispatch:

```python
    ap.add_argument("--bench", action="store_true",
                    help="report recording overhead and exit")
```

and immediately after `args = ap.parse_args(argv)`:

```python
    if args.bench:
        from corpus._bench import bench
        bench.report()
        return 0
```

Add `corpus/_bench/__init__.py` (empty).

- [ ] **Step 2: Write the benchmark test**

`tests/test_bench.py`:

```python
from corpus._bench import bench


def test_measure_reports_a_real_multiplier():
    m = bench.measure(reps=1)
    assert m["baseline_s"] > 0 and m["recorded_s"] > 0
    assert m["multiplier"] >= 1.0
```

The test asserts the instrument works, not a specific speed — a hardware-
dependent threshold would be a flaky test, and the honest home for the number
is the reported table.

- [ ] **Step 3: Run tests and the benchmark**

Run: `.venv/bin/pytest tests/test_bench.py -v` — Expected: PASS.
Run: `.venv/bin/python corpus/run_corpus.py --bench` — Expected: a two-row
table. Record the observed multipliers in the README (Step 4) as measured
numbers with the machine noted, not as promises.

- [ ] **Step 4: Write `README.md`**

```markdown
# sensorium

Record what a Python program actually did; ask it questions afterward.

Sensorium wraps one run of a program with PEP 669 (`sys.monitoring`)
instrumentation, streams every call, return, and exception — with captured
argument and return values — into a SQLite trace, and answers debugging
questions from that trace in dense plain text. It exists because reading logs
is reading a diary; this is watching the execution.

## Install

    uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"

Requires Python 3.12+ (it refuses to run otherwise). No runtime dependencies.

## Use

    sensorium run -- pytest tests/test_fog.py     # record
    sensorium info last                           # what am I looking at
    sensorium exceptions last                     # what blew up, what got swallowed
    sensorium tree last --depth 3                 # what actually ran
    sensorium flow last --value 1800              # where did that number come from
    sensorium watch last --at fog:compute --expr 'visible > 100'
    sensorium refocus last --focus fog:compute    # re-run deeper, verified

Recording captures calls/returns/raises for code under the working directory.
`--focus module:qualname` adds line-level capture with local-variable deltas
for the named code.

## The honesty rules

- Truncated captures are marked (`~`) and counted; `info` reports the total.
- `watch` reports how many sites lacked the value it needed instead of
  skipping them.
- `flow` labels itself: equality/identity lineage over captured values, not
  true dataflow analysis.
- `refocus` re-runs the command and compares causal fingerprints. MATCH means
  verified same execution. DIVERGED means a different execution, and the
  trace says so permanently. Nondeterminism is not replayed — DIVERGED is the
  correct answer for a nondeterministic program.
- Subprocesses are listed as observed-but-unwitnessed, never silently ignored.

## Corpus

    python corpus/run_corpus.py            # verify against seeded bugs
    python corpus/run_corpus.py --bench    # report recording overhead

Ten small programs with deliberately planted bugs and pre-registered
questions, each recording why plain logging cannot answer it. This is the
regression suite.

## Not in v1

Async task attribution, subprocess following, attach-to-live-server flight
recording, native (rr) substrates, MCP wrapper. See
`docs/superpowers/specs/2026-08-18-sensorium-design.md`.
```

Fill the measured overhead numbers into the README's Use section as a short
"measured on this machine" line beneath the commands.

- [ ] **Step 5: Verify the whole suite and coverage**

Run: `.venv/bin/pytest --cov=sensorium --cov-report=term-missing`
Expected: all tests PASS, coverage ≥ 80%. If a module is below that, add
tests for its uncovered branches — do not lower the target.
Run: `.venv/bin/python corpus/run_corpus.py` — Expected: 0 failures.

- [ ] **Step 6: Commit**

```bash
git add corpus/_bench README.md corpus/run_corpus.py tests/test_bench.py
git commit -m "feat: overhead benchmark and README"
```

---

## Success criteria (from the spec)

1. Every corpus question is answered correctly by its registered invocation,
   including the honesty cases (DIVERGED reported; truncation and
   not-captured counts present where registered).
2. Overhead multipliers are measured and reported by `--bench`: default depth
   in the low single digits, focused depth bounded and stated.
3. A cold agent session, given only a corpus program's failing behavior and
   the CLI, collapses the mystery using sensorium queries alone — no added
   print statements. (Verify by hand on `unit_mismatch` and `aliasing` after
   Task 17.)





