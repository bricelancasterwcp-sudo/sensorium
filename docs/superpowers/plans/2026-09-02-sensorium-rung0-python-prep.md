# Rung 0 — Python-core prep for the Rust recorder: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship everything the Rust recorder needs from the Python side before a line of Rust exists: a reader that survives Rust-sized traces, a move-aware `diff`, trace format 4 with a required-meta choke point and declared capabilities, command gating on capabilities, and the trace-format contract with conformance vectors — and re-verify today's bloomery Python-trio split with the new instrument as the acceptance test.

**Architecture:** Every change is in the existing Python package. The reader gets two query rewrites (no schema change). `diff` gains a query-time rename detector in a new small module. The format bump is a required-key set enforced once in `db.open_trace`, plus three meta keys the Python recorder now writes (`recorder`, `lang`, `capabilities`), plus reader properties that every "predates" sentence and every capability-dependent command reads. The contract is a Markdown document plus JSON vectors that a builder turns into traces and runs through the real CLI.

**Tech Stack:** Python 3.12+ stdlib only at runtime (sqlite3, hashlib, json); pytest + pyyaml in dev. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` — sections 5, 6, 8 (E5), 9 (vectors), 10 (rung-0 acceptance), 11 (rung 0), 13.

## Global Constraints

- Runtime stays stdlib-only; `requires-python = ">=3.12"`; CI matrix 3.12/3.13/3.14 must stay green (`python -m pytest -q` and `python corpus/run_corpus.py`).
- No file over 800 lines. `diff_cmd.py` is 736 lines: the move detector goes in a NEW module `src/sensorium/query/moves.py`, and `diff_cmd.py` gains at most ~40 lines.
- Existing CLI output for Python traces must not change except where a task says so; every existing test keeps passing (745 collected at start).
- The honesty contract: no command prints a value it did not read; absence of a record is never printed as zero; a refusal names what was missing.
- Commit per task, conventional commits, message body states the measured fact where one exists. Attribution trailers per the session's git rules.
- Work on a branch `feat/rung0-python-prep` from `main` (`c2ab81a`), with the spec committed first (Task 0).

---

### Task 0: Branch and commit the spec

**Files:**
- Commit: `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` (already written, untracked)
- Commit: `docs/superpowers/plans/2026-09-02-sensorium-rung0-python-prep.md` (this file)

- [ ] **Step 1: Create the branch and commit the two documents**

```bash
cd ~/workspace/sensorium
git checkout -b feat/rung0-python-prep main
git add docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md \
        docs/superpowers/plans/2026-09-02-sensorium-rung0-python-prep.md
git commit -m "docs: Rust recorder design (reworked) and the rung-0 plan"
```

- [ ] **Step 2: Confirm the suite baseline**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: `745 passed` (skips allowed on 3.12/3.13 legs; this box's venv is 3.14).

---

### Task 1: Reader — `unframed_calls` in O(n), frame children from a parent map

**Files:**
- Modify: `src/sensorium/store/reader.py:86-101` (`__init__`), `:158-166` (`children`, `roots`), `:201-214` (`unframed_calls`)
- Test: `tests/test_reader.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `Trace.unframed_calls(code_id=None) -> list[Event]`, `Trace.children(fid) -> list[Frame]`, `Trace.roots() -> list[Frame]` — same signatures and same rows as today; a private `Trace._child_ids: dict[int | None, list[int]] | None` cache.

Measured on this box (2026-09-01): `sensorium info` on a 93k-event / 44k-frame trace took 54.4 s; the `unframed_calls` SQL alone took 53.9 s (`EXPLAIN` = `SEARCH e USING INDEX idx_events_kind` + `SCAN f LEFT-JOIN`, one full `frames` scan per CALL row). The same query as a `NOT IN` subquery took 0.011 s and returned identical rows. `children()` is `SCAN frames` per call.

- [ ] **Step 1: Write the failing tests (oracle = the old SQL, run directly)**

Append to `tests/test_reader.py`:

```python
import sqlite3
from pathlib import Path

from sensorium.store.reader import Trace

GEN_FIXTURE = Path(__file__).parent / "fixtures" / "format2_gen.db"


def _old_unframed_ids(path, code_id=None):
    """The LEFT JOIN this rewrite replaces, kept here as the oracle."""
    c = sqlite3.connect(path)
    q = ("SELECT e.id FROM events e LEFT JOIN frames f ON f.call_event_id = e.id "
         "WHERE e.kind = 'CALL' AND f.id IS NULL AND e.code_id IS NOT NULL")
    params = ()
    if code_id is not None:
        q += " AND e.code_id = ?"
        params = (code_id,)
    return [r[0] for r in c.execute(q + " ORDER BY e.id", params)]


def test_unframed_calls_returns_exactly_what_the_join_returned():
    t = Trace.open(GEN_FIXTURE)
    got = [e.id for e in t.unframed_calls()]
    assert got == _old_unframed_ids(GEN_FIXTURE)
    assert got, "the format-2 generator fixture must contain unframed calls"
    cid = t.event(got[0]).code_id
    assert ([e.id for e in t.unframed_calls(code_id=cid)]
            == _old_unframed_ids(GEN_FIXTURE, cid))


def test_unframed_calls_query_does_not_scan_frames_per_event():
    """The plan is the fact: a per-CALL scan of `frames` is quadratic and was
    measured at 54 s on a 93k-event trace."""
    t = Trace.open(GEN_FIXTURE)
    plan = " ".join(r[3] for r in t._c.execute(
        "EXPLAIN QUERY PLAN " + t._unframed_sql()))
    assert "LEFT-JOIN" not in plan


def test_children_and_roots_match_a_direct_query():
    t = Trace.open(GEN_FIXTURE)
    c = sqlite3.connect(GEN_FIXTURE)
    roots = [r[0] for r in c.execute(
        "SELECT id FROM frames WHERE parent_id IS NULL ORDER BY id")]
    assert [f.id for f in t.roots()] == roots
    for fid in roots[:3]:
        kids = [r[0] for r in c.execute(
            "SELECT id FROM frames WHERE parent_id = ? ORDER BY id", (fid,))]
        assert [f.id for f in t.children(fid)] == kids
    assert t.children(10**9) == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_reader.py -q -k "unframed or children" 2>&1 | tail -5`
Expected: `test_unframed_calls_query_does_not_scan_frames_per_event` FAILS with `AttributeError: 'Trace' object has no attribute '_unframed_sql'`; the other two pass or fail on the same attribute — either way the plan test is RED.

- [ ] **Step 3: Implement**

In `reader.py`, add to `__init__` after `self._code_cache = None`:

```python
        self._child_ids: dict[int | None, list[int]] | None = None
```

Replace `children` and `roots` (lines 158-166):

```python
    def _parent_map(self) -> dict[int | None, list[int]]:
        """parent_id -> [frame ids], built once per Trace from one ordered
        pass over (id, parent_id). `children()` was a full `frames` scan per
        call (no index on parent_id), so a tree walk was O(frames^2)."""
        if self._child_ids is None:
            m: dict[int | None, list[int]] = {}
            for fid, pid in self._c.execute(
                    "SELECT id, parent_id FROM frames ORDER BY id"):
                m.setdefault(pid, []).append(fid)
            self._child_ids = m
        return self._child_ids

    def children(self, fid: int) -> list[Frame]:
        return [self.frame(i) for i in self._parent_map().get(fid, [])]

    def roots(self) -> list[Frame]:
        return [self.frame(i) for i in self._parent_map().get(None, [])]
```

Replace `unframed_calls` (lines 201-214):

```python
    def _unframed_sql(self, code_id: int | None = None) -> str:
        # NOT IN over frames.call_event_id (NOT NULL by schema, so NOT IN is
        # exact), not a LEFT JOIN: the join had no index to use and scanned
        # `frames` once per CALL row -- 53.9 s on a 93k-event trace, 0.011 s
        # this way, row-identical (measured 2026-09-01).
        q = (f"SELECT {self._ecols} FROM events WHERE kind = 'CALL' "
             "AND code_id IS NOT NULL "
             "AND id NOT IN (SELECT call_event_id FROM frames)")
        if code_id is not None:
            q += " AND code_id = ?"
        return q + " ORDER BY id"

    def unframed_calls(self, code_id: int | None = None) -> list[Event]:
        """CALL events no frame was opened for (generators, coroutines).

        Decided by the frames table, deliberately not the `unframed`
        payload key: the key is format 2, the table answers for every format,
        and 'recorded but not framed' must be the same fact on both."""
        params: tuple = () if code_id is None else (code_id,)
        return [_event(r) for r in self._c.execute(self._unframed_sql(code_id),
                                                   params)]
```

- [ ] **Step 4: Run the tests and the whole suite**

Run: `.venv/bin/python -m pytest tests/test_reader.py -q 2>&1 | tail -3 && .venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: all pass, `748 passed`.

- [ ] **Step 5: Measure on the real trace and record the number in the commit**

Run: `time .venv/bin/sensorium info 20260901-210520-7f8854 > /dev/null`
Expected: under 1 s (was 54 s). Record the real number in the commit body.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/store/reader.py tests/test_reader.py
git commit -m "perf(reader): unframed calls in one pass, children from a parent map

info on a 93k-event/44k-frame trace: 54.4 s -> <measured> s. The LEFT JOIN
on frames.call_event_id had no index and scanned frames once per CALL row
(EXPLAIN: SCAN f LEFT-JOIN); NOT IN over the same column is exact
(call_event_id is NOT NULL) and returns identical rows. children()/roots()
were SCAN frames per call; they now read one (id, parent_id) pass."
```

---

### Task 2: `diff --ignore-moves` — a move-aware comparison, with the E5 mutation test

**Files:**
- Create: `src/sensorium/query/moves.py`
- Modify: `src/sensorium/query/diff_cmd.py:157-166` (`_shapes`), `:286-303` (`compare_tasks`), `:306-376` (`compare`), `:416-469` (`compare_task_streams`), `:580-607` (`_print_thread_match`), `:665-683` (`print_comparison`), `:711-736` (`add_parser`, `run`)
- Test: `tests/test_moves.py` (new), `tests/test_diff_moves.py` (new)

**Interfaces:**
- Produces (`moves.py`):
  - `@dataclass(frozen=True) class Moves: mapping: dict[tuple[str, str], tuple[str, str]]; moved: list[tuple[str, str, str]]; added: list[tuple[str, str]]; removed: list[tuple[str, str]]; unpaired: list[str]; one_sided_modules: list[tuple[str, str]]` — the last is `("A"|"B", file)` for every file whose `<module>` code object exists on one side only.
  - `def detect_moves(trace_a, trace_b) -> Moves` — pairs A-only `(file, qualname)` with B-only `(file, qualname)` by qualname when the pairing is unique on both sides; `<module>` code objects are never paired (they are file identity, not a function) and go to `one_sided_modules` when one-sided.
  - `def project(stream, moves) -> list[tuple]` — drops steps whose `(file, "<module>")` is in `one_sided_modules`, then rewrites the remaining `(file, qualname, kind, eid)` steps through `moves.mapping`. Takes the `Moves` object (not a bare dict); `_shapes` passes it for A and a `Moves` with an empty mapping but the same `one_sided_modules` for B — build that with `dataclasses.replace(moves, mapping={})`.
  - `def hash_stream(stream) -> str` — blake2b over `(file, qualname, kind)` via `record.fingerprint.Fingerprint`.
  - `def print_moves(moves) -> None` and `def short(key) -> str` live HERE, not in `diff_cmd.py` (controller ruling: `diff_cmd.py` is 736 lines and Task 4 adds to it; keep it under 800). `diff_cmd` imports and calls `print_moves`.
- Produces (`diff_cmd.py`): `compare(trace_a, trace_b, moves=None)`, `compare_tasks(trace_a, trace_b, moves=None)`, `compare_task_streams(trace_a, trace_b, name, moves=None)`; the result dict gains `"moves": Moves | None`. CLI flag `--ignore-moves`.

Semantics (spec §6, tightened): a qualname that is A-only under two or more files, or B-only under two or more files, is NOT paired; it stays in `removed`/`added` and is listed under `unpaired`, so a divergence inside it is reported as DIVERGED — never "MATCH with an undetectable region". Task streams are re-hashed at query time on BOTH sides (A projected, B as recorded) because stored task hashes use a root-relative file and a query-time hash must be computed one way for both sides.

**Module frames of one-sided files (controller ruling, pre-flight):** a split creates new files, and each new file's `<module>` code object runs once at import (the Python-trio split added exactly five such CALLs). Those steps exist on one side only by construction, so under `--ignore-moves` the CALL/RETURN steps whose code object is `<module>` of a file present on ONE side only are dropped from both compared streams before comparison, and the verdict says so: `module frames not compared: N (files only in B: lib_helper.py; only in A: -)`. Only the `<module>` code object's own steps are dropped — anything that module-level code CALLS stays in the stream, so import-time side effects still diverge. A `<module>` of a file present on both sides is compared as before. `Moves` gains `one_sided_modules: list[tuple[str, str]]` (`("A"|"B", file)`), `project()` drops those steps, and `_shapes` with a mapping drops them from task streams the same way. The `<module>` qualname is exactly the string `"<module>"`.

- [ ] **Step 1: Write the failing unit tests for the detector**

`tests/test_moves.py`:

```python
"""Rename detection for `diff --ignore-moves`: pair a function that left one
file with the same-named function that appeared in another, and only when
that pairing is the only one possible."""
from sensorium.query.moves import Moves, detect_moves, hash_stream, project
from sensorium.store.writer import TraceWriter


class _T:
    """Just enough of Trace for detect_moves: `codes()`."""
    def __init__(self, keys):
        from sensorium.store.reader import Code
        self._codes = [Code(i + 1, f, q, 1) for i, (f, q) in enumerate(keys)]

    def codes(self):
        return list(self._codes)


def test_unique_move_is_paired_and_named():
    a = _T([("/w/main.py", "main"), ("/w/a.py", "helper")])
    b = _T([("/w/main.py", "main"), ("/w/b.py", "helper")])
    m = detect_moves(a, b)
    assert m.mapping == {("/w/a.py", "helper"): ("/w/b.py", "helper")}
    assert m.moved == [("helper", "/w/a.py", "/w/b.py")]
    assert m.added == [] and m.removed == [] and m.unpaired == []


def test_unchanged_code_is_not_in_the_mapping():
    a = _T([("/w/main.py", "main")])
    m = detect_moves(a, a)
    assert m == Moves({}, [], [], [], [], [])


def test_ambiguous_name_is_left_unpaired_on_both_sides():
    a = _T([("/w/a.py", "helper"), ("/w/c.py", "helper")])
    b = _T([("/w/b.py", "helper"), ("/w/d.py", "helper")])
    m = detect_moves(a, b)
    assert m.mapping == {}
    assert m.unpaired == ["helper"]
    assert m.removed == [("/w/a.py", "helper"), ("/w/c.py", "helper")]
    assert m.added == [("/w/b.py", "helper"), ("/w/d.py", "helper")]


def test_added_and_removed_are_reported_not_paired():
    a = _T([("/w/a.py", "old")])
    b = _T([("/w/a.py", "new")])
    m = detect_moves(a, b)
    assert m.mapping == {}
    assert m.removed == [("/w/a.py", "old")] and m.added == [("/w/a.py", "new")]


def test_project_rewrites_only_mapped_steps_and_keeps_kind_and_event_id():
    m = Moves({("/w/a.py", "helper"): ("/w/b.py", "helper")}, [], [], [], [], [])
    stream = [("/w/main.py", "main", "CALL", 1), ("/w/a.py", "helper", "CALL", 2),
              ("/w/a.py", "helper", "RETURN", 3)]
    assert project(stream, m) == [
        ("/w/main.py", "main", "CALL", 1), ("/w/b.py", "helper", "CALL", 2),
        ("/w/b.py", "helper", "RETURN", 3)]


def test_project_drops_a_one_sided_module_frame_and_keeps_two_sided_ones():
    m = Moves({}, [], [], [], [], [("B", "/w/new.py")])
    stream = [("/w/main.py", "<module>", "CALL", 1), ("/w/new.py", "<module>", "CALL", 2),
              ("/w/new.py", "helper", "CALL", 3), ("/w/new.py", "<module>", "RETURN", 4)]
    assert project(stream, m) == [("/w/main.py", "<module>", "CALL", 1),
                                  ("/w/new.py", "helper", "CALL", 3)]


def test_detect_moves_never_pairs_module_code_and_lists_one_sided_files():
    a = _T([("/w/main.py", "<module>"), ("/w/old.py", "<module>")])
    b = _T([("/w/main.py", "<module>"), ("/w/new.py", "<module>")])
    m = detect_moves(a, b)
    assert m.mapping == {} and m.added == [] and m.removed == [] and m.unpaired == []
    assert m.one_sided_modules == [("A", "/w/old.py"), ("B", "/w/new.py")]


def test_hash_stream_is_blake2b_over_file_qualname_kind():
    import hashlib
    h = hashlib.blake2b(digest_size=16)
    h.update(b"/w/a.py\x1fhelper\x1fCALL\n")
    assert hash_stream([("/w/a.py", "helper", "CALL", 7)]) == h.hexdigest()
    assert hash_stream([]) == hashlib.blake2b(digest_size=16).hexdigest()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_moves.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'sensorium.query.moves'`.

- [ ] **Step 3: Write `moves.py`**

```python
"""Query-time rename detection for `diff --ignore-moves`.

A behaviour-preserving refactor that moves a function to another file
changes the `file` of every one of its events, and the causal stream is
compared on (file, qualname, kind), so the plain verdict is DIVERGED at the
first moved CALL (observed 2026-09-01 on bloomery's Python-trio split: the
verification fell back to comparing `info` counts by eye).

This module pairs code objects that LEFT one file on side A with the
same-named code objects that APPEARED in another file on side B -- and
only when that pairing is the only one possible. A qualname that is A-only
under two files, or B-only under two files, is not paired: it is listed as
unpaired and its events keep their recorded keys, so any divergence inside
it is still a divergence. Nothing here changes what is stored; the stored
fingerprints are untouched and `diff` without the flag reads them as before.
"""
from collections import defaultdict
from dataclasses import dataclass

from sensorium.record.fingerprint import Fingerprint

Key = tuple[str, str]           # (file, qualname)


@dataclass(frozen=True)
class Moves:
    mapping: dict[Key, Key]                  # A key -> B key, unique pairs only
    moved: list[tuple[str, str, str]]        # (qualname, file_a, file_b)
    added: list[Key]                         # B-only, not paired
    removed: list[Key]                       # A-only, not paired
    unpaired: list[str]                      # qualnames refused for ambiguity


def detect_moves(trace_a, trace_b) -> Moves:
    ka = {(c.file, c.qualname) for c in trace_a.codes()}
    kb = {(c.file, c.qualname) for c in trace_b.codes()}
    only_a, only_b = ka - kb, kb - ka
    by_q_a: dict[str, list[str]] = defaultdict(list)
    by_q_b: dict[str, list[str]] = defaultdict(list)
    for f, q in only_a:
        by_q_a[q].append(f)
    for f, q in only_b:
        by_q_b[q].append(f)
    mapping: dict[Key, Key] = {}
    moved, unpaired = [], []
    for q in sorted(by_q_a):
        if q not in by_q_b:
            continue
        fa, fb = by_q_a[q], by_q_b[q]
        if len(fa) == 1 and len(fb) == 1:
            mapping[(fa[0], q)] = (fb[0], q)
            moved.append((q, fa[0], fb[0]))
        else:
            unpaired.append(q)
    paired_b = set(mapping.values())
    removed = sorted(k for k in only_a if k not in mapping)
    added = sorted(k for k in only_b if k not in paired_b)
    return Moves(mapping, moved, added, removed, unpaired)


def project(stream, mapping: dict[Key, Key]) -> list[tuple]:
    """Rewrite each (file, qualname, kind, eid) step through `mapping`;
    unmapped steps pass through unchanged."""
    if not mapping:
        return list(stream)
    out = []
    for file, qual, kind, eid in stream:
        file, qual = mapping.get((file, qual), (file, qual))
        out.append((file, qual, kind, eid))
    return out


def hash_stream(stream) -> str:
    """The same rolling hash the recorder uses, over a query-time stream.
    Both sides of a `--ignore-moves` comparison are hashed here, never one
    side here and the other from the stored row: the recorder hashes a
    root-relative file, this hashes what `code_objects` holds."""
    fp = Fingerprint()
    for file, qual, kind, _eid in stream:
        fp.update(file, qual, kind)
    return fp.hexdigest()
```

- [ ] **Step 4: Run the unit tests**

Run: `.venv/bin/python -m pytest tests/test_moves.py -q 2>&1 | tail -3`
Expected: 8 passed.

- [ ] **Step 5: Write the failing end-to-end tests (the E5 mutation test lives here)**

`tests/test_diff_moves.py`:

```python
"""`diff --ignore-moves`: a function moved to another file is paired by
name; a planted behavioural change under the same move is still DIVERGED
(spec E5 -- if the planted change read MATCH the verifier would be void)."""
import re

from sensorium import cli
from tests.helpers import run_cli

MAIN = """
from lib import helper, other

def main():
    helper(1)
    other(2)

if __name__ == "__main__":
    main()
"""
MAIN_SWAPPED = MAIN.replace("    helper(1)\n    other(2)", "    other(2)\n    helper(1)")
LIB_TOGETHER = "def helper(x):\n    return x + 1\n\ndef other(y):\n    return y * 2\n"
LIB_SPLIT = "from lib_helper import helper\n\ndef other(y):\n    return y * 2\n"
LIB_HELPER = "def helper(x):\n    return x + 1\n"


def _record(workdir, sdir, files):
    """Write `files` into ONE directory and record `main.py` there. Every
    version is recorded in the same directory on purpose: `file` is
    absolute, and a different directory would make every module's
    `<module>` and every function a "move" at once. Stale bytecode is
    ruled out explicitly (same directory, rewritten sources)."""
    import os
    for stale in workdir.glob("*.py"):
        stale.unlink()
    for fname, text in files:
        (workdir / fname).write_text(text)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "sensorium", "run", "--", "main.py"],
                       cwd=workdir, env={**env, "SENSORIUM_DIR": str(sdir)},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def _three(tmp_path, monkeypatch):
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_TOGETHER)])
    moved = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_SPLIT),
                              ("lib_helper.py", LIB_HELPER)])
    swapped = _record(w, sdir, [("main.py", MAIN_SWAPPED), ("lib.py", LIB_SPLIT),
                                ("lib_helper.py", LIB_HELPER)])
    return before, moved, swapped


def _collect(capsys, args):
    rc = cli.main(args)
    return rc, capsys.readouterr().out


def test_plain_diff_calls_a_pure_move_diverged(tmp_path, monkeypatch, capsys):
    before, moved, _ = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", before, moved])
    assert rc == 1 and "verdict: DIVERGED" in out


def test_ignore_moves_pairs_the_move_and_says_so(tmp_path, monkeypatch, capsys):
    before, moved, _ = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, moved])
    assert rc == 0, out
    assert "verdict: MATCH modulo location" in out
    assert re.search(r"moved: helper\s+lib\.py -> lib_helper\.py", out)
    assert "key: (file, qualname, kind), with 1 code object(s) paired" in out
    assert "module frames not compared: 1 (files only in B: lib_helper.py" in out
    assert "values, timing, and LINE events were not compared" in out


def test_ignore_moves_still_catches_a_planted_swap(tmp_path, monkeypatch, capsys):
    """E5: the same move plus two call sites swapped must read DIVERGED and
    name the step; a MATCH here would mean the comparison compares nothing."""
    before, _, swapped = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, swapped])
    assert rc == 1, out
    assert "verdict: DIVERGED at causal step" in out
    assert "A:      " in out and "B:      " in out
    assert "moved: helper" in out          # the pairing is still reported


def test_ignore_moves_lists_added_and_removed_code(tmp_path, monkeypatch, capsys):
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_TOGETHER)])
    renamed = _record(w, sdir, [("main.py", MAIN.replace("other", "third")),
                                ("lib.py", LIB_TOGETHER.replace("other", "third"))])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, renamed])
    assert rc == 1
    assert "removed (only in A): lib.py:other" in out
    assert "added (only in B): lib.py:third" in out


def test_import_time_side_effects_in_a_new_module_still_diverge(tmp_path, monkeypatch, capsys):
    """Only the new module's own <module> steps are dropped; a call it makes
    at import time is a step A never took."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_TOGETHER)])
    noisy = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_SPLIT),
                              ("lib_helper.py", LIB_HELPER + "\nhelper(0)\n")])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, noisy])
    assert rc == 1 and "verdict: DIVERGED at causal step" in out
```

(`tests/test_diff_moves.py` imports `re`, `subprocess`, `sys`, and `from sensorium import cli`; `run_cli` is not used.)

- [ ] **Step 6: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_diff_moves.py -q 2>&1 | tail -3`
Expected: `error: unrecognized arguments: --ignore-moves` (argparse exits) or an AttributeError; RED either way.

- [ ] **Step 7: Wire `diff_cmd.py`**

Add the import near the top (after `from sensorium.store.reader import Trace`):

```python
from dataclasses import replace as _replace

from sensorium.query.moves import (Moves, detect_moves, hash_stream, print_moves,
                                   project)
```

Replace `_shapes` (lines 157-166):

```python
def _shapes(trace: Trace, moves: Moves | None = None) -> Counter:
    """`Trace.task_shapes()` with asyncio's default `Task-N` names read as
    no name. With `moves` (a Moves object, its mapping empty for the B side)
    the shapes are RE-HASHED from each task's stream, projected through it
    -- `--ignore-moves` must hash both sides one way, and the stored rows
    were hashed over a root-relative file. The reader owns the multiset;
    this owns the comparison policy."""
    out: Counter = Counter()
    if moves is None:
        for (name, h), k in trace.task_shapes().items():
            out[(None if _unnamed(name) else name, h)] += k
        return out
    for tid, (name, _h, _n) in trace.task_fingerprints().items():
        h = hash_stream(project(trace.task_stream(tid), moves))
        out[(None if _unnamed(name) else name, h)] += 1
    return out
```

In `compare_tasks` change the signature and first line:

```python
def compare_tasks(trace_a: Trace, trace_b: Trace, moves: Moves | None = None) -> dict:
    ...
    mb = _replace(moves, mapping={}) if moves is not None else None
    a, b = _shapes(trace_a, moves), _shapes(trace_b, mb)   # Ruling 4 normalisation
```

In `compare` change the signature to `compare(trace_a, trace_b, moves: Moves | None = None)`, and:

```python
    sa = project(trace_a.causal_stream(), moves) if moves else trace_a.causal_stream()
    sb = (project(trace_b.causal_stream(), _replace(moves, mapping={})) if moves
          else trace_b.causal_stream())
    tasks = compare_tasks(trace_a, trace_b, moves)
```

and add `"moves": moves` to every returned dict in `compare` (the two non-refused returns; `_refused` gains `"moves": None`).

In `compare_task_streams` add `moves: Moves | None = None` and project `sa`:

```python
    sa, sb = trace_a.task_stream(ia), trace_b.task_stream(ib)
    if moves:
        sa = project(sa, moves)
        sb = project(sb, _replace(moves, mapping={}))
```

Add the printing helpers to `moves.py` (end of file):

```python
MOVE_LIST_CAP = 12


def short(key) -> str:
    file, qual = key
    return f"{file.rsplit('/', 1)[-1]}:{qual}"


def print_moves(moves: Moves) -> None:
    """What was paired, what was not, and why -- printed on every verdict
    under --ignore-moves, so a MATCH never hides how it was reached."""
    for qual, fa, fb in moves.moved[:MOVE_LIST_CAP]:
        print(f"  moved: {qual}  {fa.rsplit('/', 1)[-1]} -> {fb.rsplit('/', 1)[-1]}")
    if len(moves.moved) > MOVE_LIST_CAP:
        print(f"  ... +{len(moves.moved) - MOVE_LIST_CAP} more moved")
    if moves.removed:
        print("  removed (only in A): " + ", ".join(short(k) for k in moves.removed[:MOVE_LIST_CAP]))
    if moves.added:
        print("  added (only in B): " + ", ".join(short(k) for k in moves.added[:MOVE_LIST_CAP]))
    if moves.unpaired:
        print("  unpaired (same name in several files on one side, not paired; "
              "a divergence inside them is reported as one): "
              + ", ".join(moves.unpaired))
    if moves.one_sided_modules:
        only_a = [f.rsplit('/', 1)[-1] for s, f in moves.one_sided_modules if s == "A"]
        only_b = [f.rsplit('/', 1)[-1] for s, f in moves.one_sided_modules if s == "B"]
        print(f"  module frames not compared: {len(moves.one_sided_modules)} "
              f"(files only in B: {', '.join(only_b) or '-'}; only in A: "
              f"{', '.join(only_a) or '-'}) -- a new file's own import-time "
              "frame exists on one side by construction; what it called is still compared")
```

`detect_moves` skips `<module>` when building `by_q_a`/`by_q_b` and instead collects `one_sided_modules = sorted([("A", f) for f, q in only_a if q == "<module>"] + [("B", f) for f, q in only_b if q == "<module>"])`; those keys are excluded from `removed`/`added`. `project(stream, moves)` first drops any step with `qual == "<module>"` whose `(file)` is in `{f for _s, f in moves.one_sided_modules}`, then applies `moves.mapping`. Update `test_moves.py` accordingly: `project` takes a `Moves`; add a test that a one-sided `<module>` step is dropped and a two-sided one kept; `Moves(...)` constructor calls gain the sixth field.

In `_print_thread_match`, change the final MATCH print so a move-aware verdict says so:

```python
    exact = (trace_a.main_thread_basis() == "recorded"
             and trace_b.main_thread_basis() == "recorded")
    where = "the main thread" if exact else "the thread named above"
    if res.get("moves"):
        nm = len(res["moves"].moved)
        print(f"verdict: MATCH modulo location -- identical causal streams "
              f"({n} events) once {nm} moved code object(s) are paired by "
              f"qualname on {where}; values, timing, and LINE events were "
              "not compared")
        return
    print(f"verdict: MATCH -- identical causal streams ({n} events): "
          ...unchanged...)
```

In `print_comparison`, after the two `_thread_header` prints and before the notes:

```python
    if res.get("moves"):
        mv = res["moves"]
        print(f"key: (file, qualname, kind), with {len(mv.moved)} code "
              "object(s) paired across a move by (qualname, kind) -- see "
              "moves below")
```

and at the end of `print_comparison` (after the tasks section):

```python
    if res.get("moves"):
        print("moves:")
        print_moves(res["moves"])
```

In `add_parser`:

```python
    p.add_argument("--ignore-moves", action="store_true",
                   help="pair a function that left one file with the same-"
                        "named function that appeared in another, then "
                        "compare; the pairing is printed with the verdict")
```

In `run`:

```python
    moves = detect_moves(ta, tb) if args.ignore_moves else None
    if args.task:
        res = compare_task_streams(ta, tb, args.task, moves)
        ...
    else:
        res = compare(ta, tb, moves)
        ...
```

`print_task_comparison` prints `moves:` + `print_moves` at its end too when `res.get("moves")`.

- [ ] **Step 8: Run the new tests and the suite**

Run: `.venv/bin/python -m pytest tests/test_diff_moves.py tests/test_moves.py tests/test_diff.py -q 2>&1 | tail -3 && .venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: all pass; existing `diff` output unchanged (test_diff green).

- [ ] **Step 9: Check the file ceiling**

Run: `wc -l src/sensorium/query/diff_cmd.py src/sensorium/query/moves.py`
Expected: both under 800.

- [ ] **Step 10: Commit**

```bash
git add src/sensorium/query/moves.py src/sensorium/query/diff_cmd.py tests/test_moves.py tests/test_diff_moves.py
git commit -m "feat(diff): --ignore-moves pairs a moved function by name and says so

A pure module move changes the file of every moved event, so the plain
verdict is DIVERGED at the first moved CALL (bloomery's Python-trio split,
2026-09-01, was verified by eye on info counts because of it). The pairing
is query-time only, unique-by-qualname only, printed with every verdict,
and a planted call-site swap under the same move still reads DIVERGED."
```

---

### Task 3: Trace format 4 — required meta at the choke point, recorder/lang/capabilities

**Files:**
- Modify: `src/sensorium/store/db.py:6-23` (constant + docstring), `:103-114` (`open_trace`)
- Modify: `src/sensorium/store/reader.py` (new properties after `fingerprint_basis`, line ~233)
- Modify: `src/sensorium/record/boot.py:535-563` (`_write_run_meta`)
- Modify: `tests/helpers.py` (new `FINAL_META`, `finalize_synthetic`)
- Modify (mechanical, each listed): `tests/refocus_programs.py:467`, `tests/test_exception_identity.py:233,281,315`, `tests/test_exceptions.py:481,508,567,614,660,687,771,798,828,850`, `tests/test_runs_info.py:122,265,286,373`, `tests/test_boot_cli.py:497,528`, `tests/test_diff.py` (`_synthetic` if it sets `incomplete` False — it does not today)
- Test: `tests/test_store_db.py` (append), `tests/test_format4.py` (new)

**Interfaces:**
- Produces (`db.py`): `TRACE_FORMAT = 4`; `REQUIRED_META: tuple[str, ...]`; `WITNESS_KEYS: dict[str, tuple[str, ...]]`; `def missing_required(conn) -> list[str]`; `open_trace` raises `TraceFormatError` naming recorder and keys when `trace_format >= 4`, `incomplete` is exactly `False`, and any required key is absent.
- Produces (`reader.py`): `Trace.lang -> str`, `Trace.recorder -> str`, `Trace.capabilities -> dict[str, bool]`, `Trace.declares(cap: str) -> bool | None` (`None` = format < 4, nothing declared), `Trace.dropped_writes() -> int`.
- Produces (`boot.py`): `CAPABILITIES: dict[str, bool]` (all True), `_recorder_id() -> str` (`"sensorium <version>"`), three new meta keys written at boot: `recorder`, `lang`, `capabilities`.
- Produces (`tests/helpers.py`): `FINAL_META: dict`, `def finalize_synthetic(w, **overrides) -> None` — fills every required key that is absent with a neutral default and sets `incomplete` False.

Required set (spec §5.1, the refused-on-absence subset — `env`, `caps`, `focus`, `include`, `exclude`, `window`, `python`, `late_writes` are written by the Python recorder and read with defaults, not refused):

```python
REQUIRED_META = ("run_id", "argv", "cwd", "env_hash", "start_ts", "end_ts",
                 "exit_status", "main_thread_ident", "fingerprint_basis",
                 "truncated_count", "source_hashes",
                 "recorder", "lang", "capabilities")
WITNESS_KEYS = {"threads": ("threads_started", "live_threads"),
                "children": ("children", "spawn_syscalls", "audit_errors"),
                "stdin": ("stdin_consumed",)}
```

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_store_db.py`:

```python
def _format4_finalized(path, **meta):
    conn = db.create_trace(path)
    base = {"run_id": "r", "argv": ["p.py"], "cwd": "/w", "env_hash": "0" * 16,
            "start_ts": 1.0, "end_ts": 2.0, "exit_status": 0,
            "main_thread_ident": 1, "fingerprint_basis": "per-task",
            "truncated_count": 0, "source_hashes": {}, "recorder": "x 1.0",
            "lang": "rust", "capabilities": {"threads": False, "children": False,
                                             "stdin": False},
            "incomplete": False}
    base.update(meta)
    for k, v in base.items():
        db.set_meta(conn, k, v)
    conn.commit()
    conn.close()


def test_format_is_4():
    assert db.TRACE_FORMAT == 4


def test_open_refuses_a_finalized_format4_trace_missing_a_required_key(tmp_path):
    """The choke point: a recorder that says it finalized and left out a
    key the readers default to zero must be refused, naming the key."""
    p = tmp_path / "t.db"
    _format4_finalized(p)
    db.open_trace(p).close()                       # complete: opens
    conn = db.create_trace(tmp_path / "u.db")
    conn.close()
    _format4_finalized(tmp_path / "u.db")
    c = db.open_trace(tmp_path / "u.db")
    c.execute("DELETE FROM meta WHERE key = 'truncated_count'")
    c.commit()
    c.close()
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(tmp_path / "u.db")
    assert "truncated_count" in str(e.value) and "x 1.0" in str(e.value)


def test_open_requires_witness_keys_only_for_declared_capabilities(tmp_path):
    p = tmp_path / "t.db"
    _format4_finalized(p, capabilities={"threads": True, "children": False,
                                        "stdin": False})
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(p)
    assert "threads_started" in str(e.value)
    q = tmp_path / "u.db"
    _format4_finalized(q, capabilities={"threads": True, "children": False,
                                        "stdin": False},
                       threads_started=0, live_threads=[])
    db.open_trace(q).close()


def test_open_does_not_refuse_an_unfinished_or_hand_built_trace(tmp_path):
    """`incomplete` True, or absent (a trace still being written, or a test
    fixture that never claimed to have finalized), opens as before."""
    p = tmp_path / "t.db"
    _format4_finalized(p, incomplete=True)
    c = db.open_trace(p)
    c.execute("DELETE FROM meta WHERE key = 'exit_status'")
    c.commit()
    c.close()
    db.open_trace(p).close()
    q = tmp_path / "bare.db"
    db.create_trace(q).close()
    db.open_trace(q).close()
```

`tests/test_format4.py`:

```python
"""Format 4: the Python recorder declares itself, and the reader reads the
declaration instead of inferring age from absent keys."""
from sensorium.record import boot
from sensorium.store.reader import Trace
from tests.helpers import finalize_synthetic, record_script
from tests.programs import synthetic

PROG = "def main():\n    return 1\n\nif __name__ == '__main__':\n    main()\n"


def test_recorder_writes_recorder_lang_and_full_capabilities(tmp_path):
    run_id, trace, r = record_script(tmp_path, PROG)
    assert run_id, r.stderr
    m = Trace.open(trace).meta
    assert m["lang"] == "python"
    assert m["recorder"].startswith("sensorium ")
    assert m["capabilities"] == boot.CAPABILITIES
    assert all(m["capabilities"].values())
    assert m["trace_format"] == 4
    t = Trace.open(trace)
    assert t.lang == "python" and t.declares("threads") is True
    assert t.dropped_writes() == 0


def test_format3_fixture_reads_as_python_full_but_declares_nothing():
    from pathlib import Path
    t = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    assert t.lang == "python"
    assert t.recorder.startswith("sensorium <=0.4.0")
    assert t.capabilities == boot.CAPABILITIES
    assert t.declares("threads") is None


def test_declares_false_reads_as_false(tmp_path, monkeypatch):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"threads": False, "children": False,
                                     "stdin": False})
    w.close()
    from sensorium import paths
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    assert t.lang == "rust" and t.declares("threads") is False
    assert t.declares("line") is False        # absent from the dict = not declared


def test_dropped_writes_reads_rust_records_dropped(tmp_path, monkeypatch):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={}, records_dropped={"1": 0, "2": 3, "3": None})
    w.close()
    from sensorium import paths
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    assert t.dropped_writes() == 3
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_store_db.py tests/test_format4.py -q 2>&1 | tail -3`
Expected: `test_format_is_4` fails (`3 == 4`), the rest fail on missing names.

- [ ] **Step 3: `db.py`**

Replace lines 6-23 with:

```python
TRACE_FORMAT = 4

# Keys a finalized format-4 trace MUST carry (spec §5.1). Every reader
# defaults these when absent; on a trace that claims `incomplete = False`
# that default would print as a measured zero, so absence is refused here,
# once, instead of guarded at every `.get(key, 0)`.
REQUIRED_META = ("run_id", "argv", "cwd", "env_hash", "start_ts", "end_ts",
                 "exit_status", "main_thread_ident", "fingerprint_basis",
                 "truncated_count", "source_hashes",
                 "recorder", "lang", "capabilities")
# Witness keys, required only when the recorder declares the capability
# that produces them. A capability declared False means "not witnessed",
# which every reader prints as such -- never as zero, never as "predates".
WITNESS_KEYS = {"threads": ("threads_started", "live_threads"),
                "children": ("children", "spawn_syscalls", "audit_errors"),
                "stdin": ("stdin_consumed",)}


class TraceFormatError(Exception):
    """A trace this sensorium must not read: written by a NEWER sensorium,
    or a format-4 trace that claims to be finalized without the keys the
    format requires.

    `trace_format` is stamped at creation; a higher value means the file's
    layout may differ from what these queries assume. A trace with no
    `trace_format` at all predates the key and is read as format 1. Format
    2 (async attribution) added events.task_id, the tasks table and
    CALL-payload keys. Format 3 (inspectable coroutines) added frames.kind,
    the YIELD/RESUME event kinds, and task_fingerprints. Format 4 (the
    trace-format contract, docs/TRACE-FORMAT.md) adds no column: it makes
    `recorder`, `lang` and `capabilities` required meta, and requires the
    finalize keys above on any trace that says `incomplete = False`, so a
    second recorder can never render an absent record as a zero.
    """
```

Replace `open_trace`:

```python
def missing_required(conn: sqlite3.Connection) -> list[str]:
    """Required keys absent from a trace that claims to be finalized, in
    a stable order; [] when nothing is missing or the claim is not made."""
    if get_meta(conn, "incomplete") is not False:
        return []
    present = {k for (k,) in conn.execute("SELECT key FROM meta")}
    missing = [k for k in REQUIRED_META if k not in present]
    caps = get_meta(conn, "capabilities") or {}
    for cap, keys in WITNESS_KEYS.items():
        if caps.get(cap):
            missing += [k for k in keys if k not in present]
    return missing


def open_trace(path: Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"no trace at {path}")
    conn = sqlite3.connect(path)
    fmt = get_meta(conn, "trace_format")
    if fmt is not None and fmt > TRACE_FORMAT:
        conn.close()
        raise TraceFormatError(
            f"{path} is trace format {fmt}, newer than this sensorium reads "
            f"(up to {TRACE_FORMAT}); upgrade sensorium to open it")
    if fmt is not None and fmt >= 4:
        missing = missing_required(conn)
        if missing:
            who = get_meta(conn, "recorder", "an unnamed recorder")
            conn.close()
            raise TraceFormatError(
                f"{path} claims to be finalized (incomplete = false) but "
                f"lacks required meta {', '.join(missing)} -- written by "
                f"{who}; format 4 refuses rather than read those as zero")
    return conn
```

- [ ] **Step 4: `reader.py` properties (after `fingerprint_basis`)**

```python
    @property
    def lang(self) -> str:
        """`meta["lang"]`; a trace without it predates the declaration and
        was written by the Python recorder (nothing else existed)."""
        return self.meta.get("lang") or "python"

    @property
    def recorder(self) -> str:
        r = self.meta.get("recorder")
        return r or f"sensorium <=0.4.0 (format {self.format}, undeclared)"

    @property
    def capabilities(self) -> dict:
        """What the recorder declared it produces. A Python trace with no
        declaration is read as full: that recorder had every capability and,
        before format 4, no way to say so (a hand-built or still-recording
        format-4 Python trace is the same case -- the open-time refusal
        guarantees a FINALIZED format-4 trace always carries the key). A
        non-Python trace with no declaration declares nothing."""
        caps = self.meta.get("capabilities")
        if caps is None:
            if self.lang == "python":
                from sensorium.record.boot import CAPABILITIES
                return dict(CAPABILITIES)
            return {}
        return dict(caps)

    def declares(self, cap: str) -> bool | None:
        """True/False = the recorder declared `cap`; None = nothing was
        declared and the trace is the Python recorder's (undeclared = full,
        the only recorder that existed). A trace whose dict omits a
        capability declared it False; a non-Python trace with no dict
        declares everything False."""
        if "capabilities" not in self.meta:
            return None if self.lang == "python" else False
        return bool(self.capabilities.get(cap, False))

    def dropped_writes(self) -> int:
        """Trace writes known lost: the Python recorder's `late_writes`
        (a lower bound), or a Rust recorder's per-thread `records_dropped`
        summed over the threads that reported a number."""
        m = self.meta
        if "late_writes" in m:
            return int(m["late_writes"] or 0)
        rd = m.get("records_dropped")
        if isinstance(rd, dict):
            return sum(int(v) for v in rd.values() if v is not None)
        return 0
```

Move the `from sensorium.record.boot import CAPABILITIES` to module top if it does not create an import cycle (`boot` imports `reader`? check with `grep -n "reader" src/sensorium/record/boot.py`; if it does, keep the local import).

- [ ] **Step 5: `boot.py`**

Near the top (after the imports):

```python
# What this recorder produces, declared into every trace (spec §5.2). Every
# query command reads the declaration of the trace it was given; a
# recorder that cannot produce something says so here, and the command
# refuses instead of rendering an empty result as a finding.
CAPABILITIES = {"line": True, "locals": True, "return_value": True,
                "tasks": True, "threads": True, "children": True,
                "stdin": True, "output": True, "object_identity": True,
                "refocus": True}


def _recorder_id() -> str:
    try:
        return f"sensorium {importlib.metadata.version('sensorium')}"
    except importlib.metadata.PackageNotFoundError:
        return "sensorium (uninstalled source tree)"
```

In `_write_run_meta`, after `w.set_meta("python", ...)`:

```python
    w.set_meta("recorder", _recorder_id())
    w.set_meta("lang", "python")
    w.set_meta("capabilities", dict(CAPABILITIES))
```

- [ ] **Step 6: `tests/helpers.py` — the finalize helper, then convert the listed sites**

Append to `tests/helpers.py`:

```python
from sensorium.store import db as _db

# Neutral values for every key a finalized format-4 trace must carry. A
# hand-built trace that sets `incomplete` False claims it finalized, and
# format 4 refuses that claim without these keys (db.REQUIRED_META).
FINAL_META = {
    "run_id": "synthetic", "argv": ["prog.py"], "cwd": "/tmp",
    "env_hash": "0" * 16, "start_ts": 0.0, "end_ts": 0.0, "exit_status": 0,
    "main_thread_ident": 1, "fingerprint_basis": "per-task",
    "truncated_count": 0, "source_hashes": {},
    "recorder": "sensorium (synthetic test trace)", "lang": "python",
    "capabilities": {"line": True, "locals": True, "return_value": True,
                     "tasks": True, "threads": True, "children": True,
                     "stdin": True, "output": True, "object_identity": True,
                     "refocus": True},
    "threads_started": 0, "live_threads": [], "children": [],
    "spawn_syscalls": 0, "audit_errors": 0, "stdin_consumed": False,
}


_WITNESS = {"threads": ("threads_started", "live_threads"),
            "children": ("children", "spawn_syscalls", "audit_errors"),
            "stdin": ("stdin_consumed",)}


def finalize_synthetic(w, **overrides) -> None:
    """Mark a hand-built trace finalized the way the recorder does: every
    required key present (existing values kept, `overrides` win), then
    `incomplete` False. Use in place of `w.set_meta("incomplete", False)`.

    Witness keys are written only for the capabilities the final dict
    declares TRUE -- a trace that declares `threads: false` must be able to
    have no `threads_started` at all, which is what the readers then print
    as a declaration. Pass a witness key explicitly to force it."""
    present = {k for (k,) in w._conn.execute("SELECT key FROM meta")}
    final = {**FINAL_META, **overrides}
    caps = final["capabilities"]
    skip = {k for cap, keys in _WITNESS.items() if not caps.get(cap)
            for k in keys if k not in overrides}
    for k, v in final.items():
        if k in skip:
            continue
        if k in overrides or k not in present:
            w.set_meta(k, v)
    w.set_meta("incomplete", False)
```

Then at each listed site replace the line `w.set_meta("incomplete", False)` with `finalize_synthetic(w)` (add `from tests.helpers import finalize_synthetic` to each file). For the two tuple-style sites in `tests/test_runs_info.py:265` and `:286`, append `finalize_synthetic(w)` after the loop and delete the `("incomplete", False)` tuple; for `test_info_flags_a_trace_that_predates_the_bookkeeping` (line ~257) the point of the test is ABSENT bookkeeping, so call `finalize_synthetic(w, capabilities={"line": True})` — `threads`/`children` are then declared false and no witness key is written — and keep its existing assertions (the wording Task 4 introduces keeps "not recorded in this trace:", each key name, and "not a record of absence"); update the docstring to say a format-4 trace states absence as a declaration. For `tests/test_boot_cli.py:497` (the `_LateWriteGuard`), write the keys through the guard before the `incomplete` line:

```python
    for k, v in FINAL_META.items():
        g.set_meta_final(k, v)
    g.set_meta_final("incomplete", False)
```

and for `:528` (`g.set_meta("incomplete", False)` after close — a late write that is absorbed) leave it as is: it never reaches the file.

`tests/refocus_programs.py:467` sets several witness keys itself; replace only the `incomplete` line with `finalize_synthetic(w)` placed AFTER its other `set_meta` calls so its own values are kept (the helper never overwrites a present key).

- [ ] **Step 7: Run the whole suite; fix every `TraceFormatError` by converting the site it names**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -15`
Expected: green after the listed sites are converted. A failure that names a required key in `TraceFormatError` is a site this list missed; convert it the same way. Do not weaken the refusal.

- [ ] **Step 8: Record a fresh format-3 fixture assertion still holds**

Run: `.venv/bin/python -m pytest tests/test_format3_fixture.py tests/test_format2_fixture.py tests/test_format1_fixture.py -q 2>&1 | tail -2`
Expected: pass (old fixtures open; they never claim format 4).

- [ ] **Step 9: Commit**

```bash
git add src/sensorium/store/db.py src/sensorium/store/reader.py src/sensorium/record/boot.py tests/
git commit -m "feat(format): trace format 4 -- required meta at open, recorder/lang/capabilities

A finalized trace (incomplete = false) that lacks a key the readers default
to zero is refused at open, naming the recorder and the keys; witness keys
are required only for capabilities the recorder declared. The Python
recorder now writes recorder, lang and a full capabilities dict; the reader
exposes lang/recorder/capabilities/declares()/dropped_writes(). Hand-built
test traces that claim to be finalized now say so through
tests.helpers.finalize_synthetic."
```

---

### Task 4: Declared absence is not age — the four "predates" sites, `info`'s recorder line, `refocus`'s output blind spot

**Files:**
- Create: `src/sensorium/query/caps.py`
- Modify: `src/sensorium/query/diff_cmd.py:522-554` (`_thread_notes`), `:112-133` (`_unsafe_reasons` → `dropped_writes()`)
- Modify: `src/sensorium/query/refocus_world.py:226-233` and `:267-272` (`_licence_caveats`), plus a new output caveat in the same function
- Modify: `src/sensorium/query/info_cmd.py:62-68` (`unwitnessed_lines`), `:88-91` (recorder line), `:178-182` (`late_writes` → `dropped_writes`)
- Test: `tests/test_caps.py` (new), `tests/test_runs_info.py` (one assertion), `tests/test_refocus_licence.py` (append)

**Interfaces:**
- Produces (`caps.py`):
  - `def witness_gap(trace, cap: str, keys: str) -> str` — the sentence fragment for absent bookkeeping: `"predates <keys> bookkeeping, so … absence of the record is not a record of absence"` when `trace.declares(cap) is None`; `"<recorder> declares <cap> not witnessed, so …"` when it is `False`.
  - `def require(trace, cap: str, command: str) -> str | None` — `None` when the trace declares `cap` (or predates declarations and is Python); otherwise a refusal sentence: `"<command> needs <cap>, which recorder <recorder> declares it does not produce (capabilities.<cap>: false); nothing was checked"`.

- [ ] **Step 1: Write the failing tests**

`tests/test_caps.py`:

```python
"""Capability declarations, read one way by every command."""
from sensorium import paths
from sensorium.query.caps import require, witness_gap
from sensorium.store.reader import Trace
from tests.helpers import finalize_synthetic
from tests.programs import synthetic

CAPS_NONE = {"line": False, "locals": False, "threads": False, "children": False,
             "stdin": False, "output": False, "object_identity": False}


def _rust(tmp_path, monkeypatch, **caps):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={**CAPS_NONE, **caps})
    w.close()
    return Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")


def test_require_passes_a_declared_capability_and_a_pre_format4_python_trace(
        tmp_path, monkeypatch):
    t = _rust(tmp_path, monkeypatch, line=True)
    assert require(t, "line", "flow") is None
    from pathlib import Path
    old = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    assert require(old, "object_identity", "flow --object") is None


def test_require_refuses_an_undeclared_capability_naming_the_recorder(
        tmp_path, monkeypatch):
    t = _rust(tmp_path, monkeypatch)
    msg = require(t, "line", "flow")
    assert msg and "sensorium-rt 0.0" in msg and "capabilities.line: false" in msg
    assert "nothing was checked" in msg


def test_witness_gap_distinguishes_predates_from_declared(tmp_path, monkeypatch):
    t = _rust(tmp_path, monkeypatch)
    declared = witness_gap(t, "threads", "thread")
    assert "declares threads not witnessed" in declared and "predates" not in declared
    from pathlib import Path
    old = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    assert "predates" in witness_gap(old, "threads", "thread")
```

Append to `tests/test_runs_info.py` (replacing the assertion in `test_info_flags_a_trace_that_predates_the_bookkeeping` per Task 3, and adding):

```python
def test_info_prints_the_recorder_and_its_declarations(tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"line": False, "threads": False,
                                     "children": False, "stdin": False})
    w.close()
    assert cli.main(["info", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "recorder: sensorium-rt 0.0  lang: rust" in out
    assert "declares threads not witnessed" in out
    assert "predates" not in out
```

Append to `tests/test_refocus_licence.py`:

```python
def test_licence_names_an_undeclared_output_capability_as_a_blind_spot(
        tmp_path, monkeypatch):
    from sensorium.query.refocus_world import _licence_caveats
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"output": False, "threads": True},
                       threads_started=0, live_threads=[])
    w.write_fingerprint(1, "aa" * 16, 1)
    w.close()
    from sensorium import paths
    from sensorium.store.reader import Trace
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    caveats = _licence_caveats(t, t)
    assert any("output was not recorded" in c and "cross-check did not run" in c
               for c in caveats)
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_caps.py tests/test_runs_info.py tests/test_refocus_licence.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: sensorium.query.caps` and the two new info/licence tests fail.

- [ ] **Step 3: `caps.py`**

```python
"""Capability declarations (spec §5.2), read one way by every command.

A format-4 trace says what its recorder produces. Before format 4 nothing
was declared and only the Python recorder existed, so an absent key meant
"older": the sentence for it says "predates". On a format-4 trace an absent
record is a declaration, and the sentence says so -- never "older", never a
zero.
"""


def witness_gap(trace, cap: str, keys: str) -> str:
    """Why a record is absent, in the words the trace itself supports."""
    if trace.declares(cap) is None:
        return (f"predates the recorder's {keys} bookkeeping, so absence of "
                "the record is not a record of absence")
    return (f"recorder {trace.recorder} declares {cap} not witnessed "
            f"(capabilities.{cap}: false), so there is no {keys} record to "
            "read; absence of the record is not a record of absence")


def require(trace, cap: str, command: str) -> str | None:
    """A refusal sentence when `trace` does not produce `cap`, else None.
    The instrument never answers from data it does not have: this is that
    rule applied to a whole command instead of one value."""
    declared = trace.declares(cap)
    if declared is None or declared:
        return None
    return (f"{command} needs {cap}, which recorder {trace.recorder} "
            f"declares it does not produce (capabilities.{cap}: false); "
            "nothing was checked")
```

- [ ] **Step 4: Apply at the four sites**

`diff_cmd._thread_notes`: replace the `"threads_started" not in meta` branch body with

```python
        return [f"{label} {witness_gap(trace, 'threads', 'thread')} -- {fps} "
                "left a fingerprint, and only the thread named above was compared"]
```

(import `witness_gap` from `sensorium.query.caps`). `diff_cmd._unsafe_reasons`: `late = trace.dropped_writes()` instead of `m.get("late_writes", 0)`; wording keeps "late_writes is a LOWER BOUND".

`refocus_world._licence_caveats`: the two `predates` branches become

```python
        if "threads_started" not in meta or "live_threads" not in meta:
            out.append(f"{label} {witness_gap(trace, 'threads', 'thread')}")
            continue
```

and

```python
        if "spawn_syscalls" not in meta:
            out.append(f"{label} {witness_gap(trace, 'children', 'spawn-syscall')}")
```

and add, before `diff = _output_difference(orig, new)`:

```python
    for label, trace in (("the original", orig), ("the rerun", new)):
        if trace.declares("output") is False:
            out.append(
                f"the program's output was not recorded on {label} (recorder "
                f"{trace.recorder} declares output: false), so the "
                "observer-effect cross-check did not run")
```

and skip `_output_difference` entirely when either side declares output False (two empty tables would otherwise pass).

`info_cmd.unwitnessed_lines`: the `missing` branch becomes

```python
    if missing and not m.get("incomplete"):
        out.append("not recorded in this trace: " + ", ".join(missing) + " -- "
                   + witness_gap(trace, "children" if "children" in missing
                                 else "threads", "that"))
```

which needs `trace` passed in: change the signature to `unwitnessed_lines(trace, m)` and its one call site in `run`. `info.run`: after the `python …` line print

```python
    print(f"recorder: {t.recorder}  lang: {t.lang}  capabilities: "
          + (" ".join(f"{k}={'yes' if v else 'no'}" for k, v in sorted(t.capabilities.items()))
             or "(none declared)"))
```

and replace the `late_writes` read with `t.dropped_writes()`.

- [ ] **Step 5: Run the tests and the suite**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -3`
Expected: green. If an existing test asserted the exact old "predates" sentence on a format-3 fixture, the new sentence for `declares() is None` keeps the word "predates" and "absence of the record is not a record of absence"; adjust only if the test pinned other words.

- [ ] **Step 6: Commit**

```bash
git add src/sensorium/query/caps.py src/sensorium/query/diff_cmd.py src/sensorium/query/refocus_world.py src/sensorium/query/info_cmd.py tests/
git commit -m "feat(query): declared absence is a declaration, not age

diff, refocus and info said 'predates the bookkeeping' for any absent
witness key. On a format-4 trace an absent record is what the recorder
declared (capabilities.<cap>: false) and is printed as such; refocus adds
the output cross-check as a blind spot when either side declares output
false instead of passing two empty tables; info prints the recorder line."
```

---

### Task 5: Capability gating in `flow` and `watch`

**Files:**
- Modify: `src/sensorium/query/flow_cmd.py:737-745` (`run`, after `Trace.open`)
- Modify: `src/sensorium/query/watch_cmd.py:488-505` (`run`, after `Trace.open`)
- Test: `tests/test_flow.py` (append), `tests/test_watch.py` (append)

**Interfaces:**
- Consumes: `caps.require(trace, cap, command)` from Task 4.
- Behaviour: `flow` refuses (exit 2, prints the sentence) when the trace declares `line` False; `flow --object` additionally when `object_identity` is False; `watch` refuses when `line` False. Python traces are unaffected (all declared or predating).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_flow.py`:

```python
def test_flow_refuses_a_trace_that_declares_no_line_events(tmp_path, monkeypatch, capsys):
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"line": False, "object_identity": False})
    w.close()
    assert cli.main(["flow", "20260101-000000-abcdef", "--value", "1"]) == 2
    out = capsys.readouterr().out
    assert "flow needs line" in out and "sensorium-rt 0.0" in out
    assert cli.main(["flow", "20260101-000000-abcdef", "--object", "0x1:int"]) == 2
    assert "flow --object needs object_identity" in capsys.readouterr().out
```

(if `tests/test_flow.py` does not already import `cli`, add `from sensorium import cli`.)

Append to `tests/test_watch.py`:

```python
def test_watch_refuses_a_trace_that_declares_no_line_events(tmp_path, monkeypatch, capsys):
    from sensorium import cli
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"line": False})
    w.close()
    assert cli.main(["watch", "20260101-000000-abcdef", "--at", "main",
                     "--expr", "x > 1"]) == 2
    assert "watch needs line" in capsys.readouterr().out
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_flow.py tests/test_watch.py -q -k "declares" 2>&1 | tail -3`
Expected: both fail (exit 0 or 1, no refusal text).

- [ ] **Step 3: Implement**

`flow_cmd.run`, right after `trace = Trace.open(...)`:

```python
    refusal = (require(trace, "line", "flow")
               or (require(trace, "object_identity", "flow --object")
                   if args.object is not None else None))
    if refusal:
        print(f"REFUSED: {refusal}")
        return 2
```

`watch_cmd.run`, right after `trace = Trace.open(...)`:

```python
    refusal = require(trace, "line", "watch")
    if refusal:
        print(f"REFUSED: {refusal}")
        return 2
```

(import `require` from `sensorium.query.caps` in both.)

- [ ] **Step 4: Run and commit**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: green.

```bash
git add src/sensorium/query/flow_cmd.py src/sensorium/query/watch_cmd.py tests/test_flow.py tests/test_watch.py
git commit -m "feat(query): flow and watch refuse a trace whose recorder declares no LINE events"
```

---

### Task 6: `docs/TRACE-FORMAT.md` and the conformance vectors

**Files:**
- Create: `docs/TRACE-FORMAT.md`
- Create: `docs/trace-format/vectors/v01-missing-required-key.json`, `v02-declared-not-witnessed.json`, `v03-two-thread-order.json`, `v04-main-thread-silent-tasks-carry.json`, `v05-closed-by-unwind-panic.json`, `v06-frames-kind-function.json`
- Create: `tests/vectors.py` (builder), `tests/test_vectors.py` (runner)

**Interfaces:**
- Produces (`tests/vectors.py`): `def build(vector: dict, sdir: Path, run_id: str) -> Path` — writes a trace from the vector's `meta`/`codes`/`frames`/`events`/`tasks` sections via `TraceWriter`; `"fingerprints": "compute"` computes per-thread (task_id NULL events) and per-task fingerprints with `record.fingerprint.Fingerprint` over `(file, qualname, kind)`.
- Vector JSON shape:

```json
{"id": "v03-two-thread-order",
 "asserts": "events.id is causal order across threads: two threads' events alternate",
 "meta": {"trace_format": 4, "incomplete": false, "run_id": "$RUN", "...": "..."},
 "codes": [["/w/a.py", "main", 1], ["/w/a.py", "worker", 9]],
 "frames": [{"parent": null, "code": 1, "call": 1, "return": 6, "depth": 0, "thread": 1, "closed_by": "return", "kind": "function"}],
 "events": [{"thread": 1, "kind": "CALL", "frame": 1, "code": 1, "line": 1, "payload": {"args": {}}, "task": null}],
 "tasks": [[1, "t::alpha", 2]],
 "fingerprints": "compute",
 "copies": 1,
 "questions": [{"id": "order", "command": ["tree", "$RUN"], "expect_line": [["f1", "main"]], "expect_exit": 0}]}
```

  Frame and event ids are their 1-based positions; `$RUN` (and `$RUN2` when `copies` is 2) are substituted in `meta` values and commands. `questions` use the corpus keys and are checked by `corpus.run_corpus.check_question` over stdout+stderr.

- [ ] **Step 1: Write the runner and the builder (test-first: the runner fails until vectors exist)**

`tests/vectors.py`:

```python
"""Build a trace from a conformance vector (docs/trace-format/vectors)."""
import json
from pathlib import Path

from sensorium.record.fingerprint import Fingerprint
from sensorium.store.writer import TraceWriter

VECTORS = Path(__file__).resolve().parent.parent / "docs" / "trace-format" / "vectors"


def load_all() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(VECTORS.glob("v*.json"))]


def _subst(v, run_ids):
    if isinstance(v, str):
        for i, rid in enumerate(run_ids):
            v = v.replace("$RUN2" if i else "$RUN", rid)
        return v
    if isinstance(v, list):
        return [_subst(x, run_ids) for x in v]
    if isinstance(v, dict):
        return {k: _subst(x, run_ids) for k, x in v.items()}
    return v


def build(vector: dict, sdir: Path, run_ids: list[str]) -> Path:
    path = Path(sdir) / "traces" / f"{run_ids[0]}.db"
    w = TraceWriter(path, batch=1)
    codes = [w.intern_code(f, q, ln) for f, q, ln in vector.get("codes", [])]
    fids = []
    for fr in vector.get("frames", []):
        fids.append(w.open_frame(fr["parent"], codes[fr["code"] - 1], fr["call"],
                                 fr["depth"], fr["thread"], fr.get("kind", "function")))
    for ev in vector.get("events", []):
        w.add_event(ev.get("ts", 0), ev["thread"], ev["kind"],
                    fids[ev["frame"] - 1] if ev.get("frame") else None,
                    codes[ev["code"] - 1] if ev.get("code") else None,
                    ev.get("line"), ev.get("payload"), ev.get("task"))
    for fr, fid in zip(vector.get("frames", []), fids):
        if fr.get("return") is not None or fr.get("closed_by"):
            w.close_frame(fid, fr.get("return"), fr.get("closed_by", "return"),
                          fr.get("unwind_exc"))
    for tid, name, thread in vector.get("tasks", []):
        w.add_task(tid, name, thread)
    if vector.get("fingerprints") == "compute":
        _compute_fingerprints(w, vector, codes)
    meta = _subst(vector.get("meta", {}), run_ids)
    for k, v in meta.items():
        if k == "incomplete":
            continue                      # written last, like the recorder
        w.set_meta(k, v)
    if "incomplete" in meta:
        w.set_meta("incomplete", meta["incomplete"])
    w.close()
    return path


def _compute_fingerprints(w, vector, codes) -> None:
    per_thread: dict[int, Fingerprint] = {}
    per_task: dict[int, Fingerprint] = {}
    for ev in vector.get("events", []):
        if ev["kind"] not in ("CALL", "RETURN", "RAISE", "HANDLED"):
            continue
        f, q, _ = vector["codes"][ev["code"] - 1]
        target = (per_task.setdefault(ev["task"], Fingerprint()) if ev.get("task")
                  else per_thread.setdefault(ev["thread"], Fingerprint()))
        target.update(f, q, ev["kind"])
    for thread in {ev["thread"] for ev in vector.get("events", [])}:
        fp = per_thread.get(thread, Fingerprint())
        w.write_fingerprint(thread, fp.hexdigest(), fp.count)
    w.write_task_fingerprints([(tid, fp.hexdigest(), fp.count)
                               for tid, fp in per_task.items()])
```

`tests/test_vectors.py`:

```python
"""Every vector under docs/trace-format/vectors builds, and every question
it asks of the CLI comes back as the contract says."""
import shutil

import pytest

from corpus.run_corpus import check_question
from tests.helpers import run_cli
from tests.vectors import build, load_all

VECTORS = load_all()


@pytest.mark.parametrize("vector", VECTORS, ids=[v["id"] for v in VECTORS])
def test_vector(vector, tmp_path):
    sdir = tmp_path / "sdir"
    run_ids = ["20260101-000000-aaaaaa", "20260101-000001-bbbbbb"][:vector.get("copies", 1)]
    path = build(vector, sdir, run_ids)
    if len(run_ids) == 2:
        shutil.copy(path, path.with_name(f"{run_ids[1]}.db"))
    assert vector["questions"], f"{vector['id']} asserts nothing"
    for q in vector["questions"]:
        cmd = [_sub(a, run_ids) for a in q["command"]]
        r = run_cli(cmd, cwd=tmp_path, sensorium_dir=sdir)
        bad = check_question(q, r.stdout + r.stderr, r.returncode)
        assert not bad, f"{vector['id']}/{q['id']}: {bad}\n{r.stdout}{r.stderr}"


def _sub(a, run_ids):
    for i, rid in enumerate(run_ids):
        a = a.replace("$RUN2" if i else "$RUN", rid)
    return a


def test_every_vector_has_an_id_a_claim_and_at_least_one_question():
    assert VECTORS, "no vectors found"
    for v in VECTORS:
        assert v["id"] and v["asserts"] and v["questions"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_vectors.py -q 2>&1 | tail -3`
Expected: `no vectors found` (the directory does not exist yet).

- [ ] **Step 3: Write the six vectors**

Shared meta block (`FINAL` below) for every vector unless a vector overrides a key:

```json
"meta": {"trace_format": 4, "run_id": "$RUN", "argv": ["prog"], "cwd": "/w",
         "env_hash": "0000000000000000", "start_ts": 0.0, "end_ts": 1.0,
         "exit_status": 0, "main_thread_ident": 1, "fingerprint_basis": "per-task",
         "truncated_count": 0, "source_hashes": {}, "recorder": "vector 1.0",
         "lang": "rust", "capabilities": {"threads": false, "children": false, "stdin": false, "line": false},
         "incomplete": false}
```

`v01-missing-required-key.json` — `meta` = FINAL without `truncated_count`; no codes/events; one question: `["info", "$RUN"]`, `expect_exit: 2`, `expect_contains: ["lacks required meta truncated_count", "vector 1.0"]`.

`v02-declared-not-witnessed.json` — FINAL; one CALL/RETURN pair on thread 1 in one frame; `fingerprints: "compute"`; questions: `["info", "$RUN"]` expect_exit 0, `expect_contains: ["recorder: vector 1.0  lang: rust", "declares threads not witnessed"]`, `expect_absent: ["predates", "threads started: 0"]`.

`v03-two-thread-order.json` — FINAL with `capabilities.threads: true`, `threads_started: 1`, `live_threads: []`; codes `main` and `worker`; two frames (thread 1 root at event 1, thread 2 root at event 2); events: CALL main (t1), CALL worker (t2), RETURN worker (t2), RETURN main (t1) — ids 1..4 by position, so the two threads' events alternate; `fingerprints: "compute"`; question: `["tree", "$RUN"]` expect_exit 0, `expect_line: [["f1", "main"], ["f2", "worker"]]` and `expect_count: {"f1 e1": 1, "f2 e2": 1}`.

`v04-main-thread-silent-tasks-carry.json` — FINAL with `copies: 2`; codes `t_alpha`, `t_beta`; two frames on threads 2 and 3, `tasks: [[1, "t::alpha", 2], [2, "t::beta", 3]]`; events CALL/RETURN for each with `"task": 1` / `"task": 2`; main thread 1 has NO events; `fingerprints: "compute"` (thread 1 gets a zero-count row: it must exist — add `"threads_with_rows": [1, 2, 3]` support in `_compute_fingerprints` by iterating `vector.get("threads_with_rows")` when present, else the event threads); question: `["diff", "$RUN", "$RUN2"]` expect_exit 0, `expect_contains: ["the tasks below carry the whole verdict", "2 task stream(s) on each side"]`.

`v05-closed-by-unwind-panic.json` — FINAL; one frame `closed_by: "unwind"`, `unwind_exc: {"type": "panic", "msg": "boom", "serial": 1, "oid": 1}`; events CALL then RAISE (payload `{"exc": {"type": "panic", "msg": "boom", "serial": 1, "oid": 1}}`); question: `["frame", "$RUN", "--fn", "main"]` expect_exit 0, `expect_contains: ["state: raised", "panic"]`, `expect_absent: ["state: open", "[None]"]`. (Confirm the exact `frame` invocation against `frame_cmd.add_parser` when writing the vector; adjust the flag, not the expectation.)

`v06-frames-kind-function.json` — FINAL; one frame with `kind: "function"` explicitly; question `["tree", "$RUN"]` expect_exit 0, `expect_absent: ["[None]", "[function]"]`, `expect_line: [["f1", "main"]]`.

- [ ] **Step 4: Run the vectors; fix the vector (or the builder), never the CLI, unless the CLI is wrong**

Run: `.venv/bin/python -m pytest tests/test_vectors.py -q 2>&1 | tail -8`
Expected: 7 passed. A failing vector is either a vector-authoring error (fix the JSON) or a contract violation in the CLI (that is a finding: record it in the commit and fix the CLI in this task only if the fix is under ten lines; otherwise open it as a follow-up in the ledger).

- [ ] **Step 5: Write `docs/TRACE-FORMAT.md`**

Sections, each short and exact (this is the contract a Rust converter is written against):

1. **Purpose and versioning** — `trace_format` history 1→4 (copy the `TraceFormatError` docstring facts); format 4 = required-meta contract, no column change; readers refuse newer formats.
2. **Storage** — one SQLite file per run under `$SENSORIUM_DIR/traces/<run-id>.db`; run-id shape `YYYYMMDD-HHMMSS-xxxxxx`; WAL at write, plain read; `0644` warning as in README.
3. **Tables** — the `SCHEMA` from `db.py` verbatim, then per column: meaning, NULL semantics (`frames.parent_id` NULL = root; `events.task_id` NULL = no unit of work; `frames.kind` never NULL on format ≥ 3 — write `function`; `frames.closed_by ∈ {return, unwind}` or NULL = open).
4. **Meta** — `REQUIRED_META` and `WITNESS_KEYS` from `db.py` with one line each; the refusal rule (`incomplete = false` + missing key → refuse); the Python-only keys (`python`, `late_writes`, `caps`, `focus`, `include`, `exclude`, `window`, `env`, `git_*`) and the Rust-only keys planned (`invocation`, `pid`, `ppid`, `exe`, `toolchain`, `cargo_args`, `profile`, `instrumented_units`, `uninstrumented`, `skipped`, `partial`, `records_dropped`); `capabilities` key list `{line, locals, return_value, tasks, threads, children, stdin, output, object_identity, refocus}` and what each command needs.
5. **Enumerations** — event kinds; payload keys per kind (`CALL: args`, `RETURN: value`, `RAISE/HANDLED: exc{type,msg,serial,oid?}`, `LINE: deltas`, `YIELD: awaiting`, `RESUME: thrown`), noting `oid` is Python-only and `type`+`msg` are required by the renderer; `closed_by`; `unwind_exc` shape; the panic mapping.
6. **Identity and order** — `events.id` is causal order across threads within one process; `ts_ns` monotonic; thread serials per process with main = 1; `main_thread_ident` written explicitly; `fingerprint_basis` explicit; task rows for every unit of work (asyncio task; Rust: test or spawned thread) with `task_fingerprints`; how `diff` compares (thread stream stepwise, tasks as a `(name, hash)` multiset, `Task-N` read as unnamed).
7. **Fingerprints** — blake2b-16 over `f"{file}\x1f{qualname}\x1f{kind}\n"` per causal event; the Python recorder hashes a root-relative `file`; `diff --ignore-moves` re-hashes both sides at query time over `code_objects.file`.
8. **Conformance vectors** — the JSON shape (copy the Interfaces block above), how to run them (`python -m pytest tests/test_vectors.py`), and the rule that every vector states what it asserts and asks at least one question.

- [ ] **Step 6: Commit**

```bash
git add docs/TRACE-FORMAT.md docs/trace-format/ tests/vectors.py tests/test_vectors.py
git commit -m "docs(format): TRACE-FORMAT.md, the contract a second recorder is written against, with six conformance vectors"
```

---

### Task 7: README, version 0.5.0, acceptance on the Python-trio pair, matrix

**Files:**
- Modify: `pyproject.toml:3` (`version = "0.5.0"`)
- Modify: `README.md:111-116` (add a `### diff — shape, not location` subsection before `### refocus`), `:269-287` (`info` line for recorder/capabilities), `:288-314` (format 4 sentence + pointer to `docs/TRACE-FORMAT.md`), `:335` (Overhead: the reader fix numbers, reported not gated)
- Ledger: `.superpowers/sdd/2026-09-02-rung0/progress.md` (gitignored; acceptance outputs pasted verbatim)

- [ ] **Step 1: Bump the version and reinstall the editable tool so `recorder` reads 0.5.0**

```bash
sed -i 's/^version = "0.4.0"/version = "0.5.0"/' pyproject.toml
.venv/bin/pip install -e . -q
uv tool install --reinstall --python 3.13 -e /home/brice/workspace/sensorium
.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"
```

Expected: `0.5.0`.

- [ ] **Step 2: README edits**

`### diff — shape, not location` (new, before `### refocus`):

> `diff` compares two runs' causal streams on `(file, qualname, kind)`; a MATCH is the same shape of execution, not the same values. A function moved to another file changes `file` on every one of its events, so a pure move reads DIVERGED at the first moved CALL. `diff --ignore-moves` pairs a function that left one file with the same-named function that appeared in another — only when that pairing is unique on both sides — and prints the pairing with the verdict as `moved: helper  a.py -> b.py`. A name present under two files on one side is left unpaired and any divergence inside it is still reported. A planted call-site swap under the same move reads DIVERGED (tests/test_diff_moves.py).

`info` section: one sentence that `info` prints `recorder`, `lang` and the declared capabilities, and that an absent witness record on a format-4 trace is printed as the recorder's declaration, never as a zero or as "predates".

"What a trace file holds": add "The file layout is trace format 4; `docs/TRACE-FORMAT.md` is the contract, with conformance vectors under `docs/trace-format/vectors/`."

"Overhead": add the reader line — `info` on a 93k-event trace 54.4 s → the Task-1 measured number; reported, not gated.

- [ ] **Step 3: Acceptance — the Python-trio pair with the new instrument (spec §10, rung 0)**

```bash
time .venv/bin/sensorium info 20260901-210520-7f8854 | head -3
.venv/bin/sensorium diff 20260901-210300-edca03 20260901-210520-7f8854 | head -12
.venv/bin/sensorium diff --ignore-moves 20260901-210300-edca03 20260901-210520-7f8854
```

Expected: `info` under 1 s; plain `diff` = `verdict: DIVERGED at causal step 426` (as recorded 2026-09-01); `--ignore-moves` = `verdict: MATCH modulo location …` with the `moved:` list naming the functions the e209ed9 file table relocated (`_ledger_row`, `_infer_completed`, `_memory_stamp`, `_task_step_done`, `_write_jsonl` among them: `test_recompute.py -> _recompute_fixtures.py`) and `added (only in B):` naming the five new `<module>` code objects. Paste all three outputs verbatim into the ledger. If `--ignore-moves` reads DIVERGED, that is a finding about the split or about the detector: drill with the printed `sensorium tree … --around` commands and record which before touching code. Note: those two traces are format 1 (recorded by the stale 0.1.0 tool); the comparison is per-thread basis on both sides, which `diff` accepts.

- [ ] **Step 4: Matrix**

```bash
for v in 3.12 3.13 3.14; do
  uv venv /tmp/claude-1000/-home-brice/rung0-$v -p $v -q && \
  uv pip install -p /tmp/claude-1000/-home-brice/rung0-$v/bin/python -q -e ".[dev]" && \
  /tmp/claude-1000/-home-brice/rung0-$v/bin/python -m pytest -q 2>&1 | tail -1 && \
  /tmp/claude-1000/-home-brice/rung0-$v/bin/python corpus/run_corpus.py 2>&1 | tail -1
done
```

Expected: green on all three, corpus `20 cases / 39 questions / 0 failures` (numbers as at 0.4.0).

- [ ] **Step 5: Commit, push, open the PR**

```bash
git add pyproject.toml README.md
git commit -m "chore: 0.5.0 -- format 4, diff --ignore-moves, reader fix, TRACE-FORMAT.md (rung 0 of the Rust recorder arc)"
git push -u origin feat/rung0-python-prep
gh pr create --title "Rung 0: Python-core prep for the Rust recorder (format 4, diff --ignore-moves, reader fix, TRACE-FORMAT.md)" --body-file - <<'EOF'
Implements docs/superpowers/plans/2026-09-02-sensorium-rung0-python-prep.md
(spec: docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md §11 rung 0).

- reader: `info` on a 93k-event trace 54.4 s -> <measured>; children()/roots() from a parent map
- diff --ignore-moves: unique-by-qualname pairing, printed with every verdict; planted swap still DIVERGED
- trace format 4: required meta refused at open when a trace claims finalized; recorder/lang/capabilities
- declared absence printed as a declaration (diff/refocus/info); flow/watch refuse undeclared LINE
- docs/TRACE-FORMAT.md + 6 conformance vectors run through the real CLI
- acceptance: the bloomery Python-trio pair reads MATCH modulo location (output in the PR description below)

<paste the three acceptance outputs>
EOF
```

Then verify origin is in sync (`git fetch && git status -sb`) and that CI is green on all three legs before reporting done.

---

## Self-review

**Spec coverage (rung 0 items in §11):** reader fix → Task 1; `diff --ignore-moves` + E5 → Task 2; format-4 meta contract with the one-choke-point refusal → Task 3; declared-not-witnessed wording, `refocus` output blind spot → Task 4; capability gating → Task 5; `TRACE-FORMAT.md` + vectors → Task 6; version 0.5.0 + §10 acceptance → Task 7. Deferred to rung 2 with the spec amended to say so: the per-language vocabulary table (no Rust trace exists to render; the terms are the recorder's to define).

**Placeholder scan:** none. Two places name a measured value to be filled at execution (`<measured>` in commit bodies) — these are numbers the executor reads off the box, not design gaps.

**Type consistency:** `Moves` fields (`mapping`, `moved`, `added`, `removed`, `unpaired`) match between Task 2's module, its tests and the printer; `compare*(…, moves=None)` and the result key `"moves"` are used identically in `run` and `print_comparison`; `declares()` returns `bool | None` and both `caps.py` functions branch on `None` first; `finalize_synthetic(w, **overrides)` is the one helper every converted test site calls; `REQUIRED_META`/`WITNESS_KEYS` names are spelled the same in `db.py`, the tests and `TRACE-FORMAT.md`.
