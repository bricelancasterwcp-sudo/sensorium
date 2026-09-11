# S5 rung 3 — naming the ambiguity: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sensorium exceptions` on a TypeScript trace names the untraced-catcher footprint under AMBIGUOUS, reads a logged rethrow to the harness as PROPAGATED, keys shapes on the classifier's components, and is measured by re-reading the kept rung-2 lens invocation against a hand-read table locked before any code.

**Architecture:** Reader-side only. `exceptions_typescript.py` gains one reason before rule 5's catch-all, a window-scoped absorbing conjunct in rule 4, and a reason table; `Disposition` gains a `reason` field; the grouper's `Renderer` gains a `key` callable so the TypeScript key is a component tuple while Rust's stays the masked prose; the invocation mode sums the reason tally. Four corpus cases and one probe marker pin the shapes; the acceptance scripts resolve the branch's binary and stamp the lens label in one place. Nothing on the wire, in the runtime or in the transform changes.

**Tech Stack:** Python 3.13 (`src/sensorium/query/`), pytest; the existing TypeScript probes (vitest 4) and corpus; bash acceptance scripts; the kept store `store-rung2ts`.

**Spec:** `docs/superpowers/specs/2026-09-10-sensorium-s5-rung3-naming-ambiguity-design.md` (main `51978b1`, PR #31). The spec is the authority; this plan is its argument. Section numbers below (§2.1, §5 …) are the spec's.

## Global Constraints

- **Nothing is recorded.** The lens measurement is the rung-2 invocation `20260910-150809-cbc8de` in `SENSORIUM_DIR=/mnt/extra/sensorium-s5/store-rung2ts` (372 traces under `traces/`, the spool under `spool/<invocation>/`). The store is read, never written: no `sensorium ts run`, no `ingest`, no `record` against it; the T5 instrument opens it read-only and refuses if the T0 hash list does not match. `/mnt/extra/sensorium-s5/vtt/frontend` (the lens copy) is read by the T0 hand read and by nobody else; `~/workspace/projects/vtt` is never read.
- **No box path in a committed file.** The store and the lens are named by label (`LENS.txt`, `<store>`); the hash list carries paths relative to the store root; the assembler redacts with `PATH=LABEL` pairs as rung 2's did. `grep -rn "/mnt/\|/home/"` over every committed file must hit only the record's §2 pin table, which sanctions it in its own sentence.
- **Pre-registration is committed before any code** (Task 0) and byte-locked by `tests/test_acceptance_s5_rung3_lock.py`: after a number is read no threshold moves, no arm is added, nothing is re-read. The hand-read table is part of the lock. An instrument defect found before a number is read is fixed and written into the record's §2.3 with its commit; found after, it is a finding.
- **Verdict words come from the rule** (spec §5): endpoint rows are `no STOP` / `STOP` (E-legacy and E-branch: `intact` / `STOP` as their rule reads), the rung's word is `DONE` or `DONE-WITH-STOP`; never PASS.
- **Legacy output is byte-identical:** the Python and Rust `exceptions` outputs, every existing vector except where a rung-3 reason line moves (named per vector in the commit), the Python and Rust corpus cases, `exceptions_rust.py`, `exceptions.py`, `rust/`, `tests/test_exceptions_rust*.py`, `tests/test_exceptions_invocation.py`, `tests/test_exceptions_python*.py` — zero diff. `Shape.key` for a Rust unit is the same tuple as today (Task 2 pins it). The rung-2 E6-TS SWALLOWED table is unchanged.
- **Wire stays 1, trace format 4, `typescript/src/` untouched**, sensorium-ts stays `0.2.0`; Python becomes `0.11.0` at Task 6 (`tests/test_release_tokens.py` binds pyproject to the CHANGELOG's newest header, so the CHANGELOG entry lands in the bump commit).
- **Ceilings** (`tests/test_ceiling.py`, 800; `docs/superpowers/{acceptance,plans,specs}/` exempt): `exceptions_typescript.py` is 613 — the reason and the reason table stay inside it unless it crosses 780, then `exceptions_typescript_reasons.py`; `exceptions_group.py` gains one field and one argument; `typescript/HONESTY.md` 788 — §4's amendment is net-neutral, new prose goes to `HONESTY-BLIND-SPOTS.md` (279); `CHANGELOG.md` 756, no cut; `docs/CARRIED-DEBT.md` 657, append, cut the oldest section to `docs/CARRIED-DEBT-ARCHIVE-7.md` only if the append crosses 800; `README.md` 790, at most one sentence; new test files rather than growth past 780 in `tests/test_exceptions_typescript.py` (its size is checked at T1).
- **Tests:** TDD per task; every new Python predicate mutation-checked under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged, mutant runs under `setsid` and killed by process group on timeout, the failing tests named in the task report. Never `npx tsc -p` from the root: `npm --prefix typescript run check`. The global `sensorium` tool is never reinstalled from this worktree; the branch's binary is `.venv/bin/sensorium`.
- **Commits:** conventional prefixes; the session's trailer lines. Branch `feat/s5-rung3` off `main` at `51978b1`, worktree `/mnt/extra/sensorium-rung2/s5-rung3`, venv `.venv` 3.13 (editable), `node_modules` installed in `typescript/`, `typescript/probes/`, `corpus/typescript/`.
- **Gotchas carried:** `pkill -f`/`pgrep -f` self-match; helper scripts scrub `SENSORIUM_MANIFEST_DIR` and `SENSORIUM_SPOOL`; the corpus runner's `expect_line` is a substring match, so a collector compares whole printed lines itself; `test_ceiling.py` enumerates `git ls-files`, so suite counts move when files become tracked.

---

## File Structure

| file | responsibility |
|---|---|
| `src/sensorium/query/exceptions_cmd.py` | `Disposition` gains `reason: str \| None = None` (shared dataclass; Rust and Python never set it) |
| `src/sensorium/query/exceptions_typescript.py` | `REASON_ORDER`; `_untraced_catcher`; every ambiguous `Disposition` carries `reason`; `_still_open_absorber` reads the unit's window; `run` prints the reason line |
| `src/sensorium/query/exceptions_group.py` | `Renderer.key`; `group_units` returns `(shapes, tally, reasons)`; `group_chains` returns two |
| `src/sensorium/query/exceptions_invocation.py` | `_merge` sums `reasons`; the reason line printed once after the summed tally |
| `tests/test_exceptions_typescript_reasons.py` (new) | the reason, its variants, the reason table walk, the reason line |
| `tests/test_exceptions_typescript_window.py` (new) | the window-scoped conjunct |
| `tests/test_exceptions_typescript_grouping.py` (new) | the component key; the Rust key fence |
| `docs/trace-format/vectors/v34-exceptions-typescript-untraced-catcher.json` + `VECTORS.md` row | the reason line and the reason tally on one trace |
| `corpus/typescript/{untraced_catcher,untraced_catcher_rejection,untraced_catcher_later_failure,logged_rethrow_to_harness}/` | the four shapes; `translated/questions.yaml` re-pinned; `corpus/typescript/README.md`, `docs/corpus.md` rows |
| `typescript/probes/src/escape.probe.test.ts`, `typescript/probes/check.mjs` | the `callback_bare_rethrow` marker; `escape:count` 14 |
| `typescript/acceptance/bin.sh` (new, sourced), `lens.py` | the binary resolution rule; `sensorium_bin()`; the label stamped only here |
| `typescript/acceptance/e6tsppp.py` (new), `assemble_rung3.py` (new), `e7_report.py` | the re-read instrument; the assembler; `LISTS["rung3"]` + the rule in the transcript header |
| `tests/test_acceptance_scripts.py` (new) | E-branch: no bare `sensorium`, no `lens` writer outside `lens.py`/assemblers |
| `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3.md` (+ `.results.json`, `-handread.md`, `-tracehashes.txt`, `-exceptions.txt`) | the record |
| `tests/test_acceptance_s5_rung3_lock.py` (new) | the byte lock |

## Decisions this plan makes

| # | decision | why |
|---|---|---|
| P1 | `Disposition.reason` is a new optional field on the shared dataclass, defaulting to `None` | Rust and Python construct `Disposition` positionally with three or four fields; a defaulted trailing field changes none of them |
| P2 | The reason key follows the SENTENCE printed: an orphan escaping HANDLED prints the escaped sentence, so its key is `escaped`; `orphan` is the key of an orphan that reaches the catch-all | a reader who tallies `escaped 13` must find thirteen escaped sentences above it |
| P3 | The untraced-catcher site is `(parent code file, parent code firstlineno, parent qualname)` — the parent code object.s own identity; the verdict prints qualname and file basename only | a CALL event.s line is the callee.s definition line, not a place in the parent, so the parent.s own first line is the one line that names the parent; the sentence names the frame, not a line, because the catcher.s own line is not on the wire |
| P4 | `_untraced_catcher` runs first inside `_ambiguous` after the escaped check, guarded by `not unit.handled` | the open/translated checks read handlers in the window and the guard makes them moot |
| P5 | `group_units` returns a third value; `group_chains` slices it off | every Rust caller keeps its two-tuple; the invocation mode is the only consumer of three |
| P6 | `Renderer.key` takes `(trace, unit, d, site, hops)`; `RUST.key` reproduces today's tuple verbatim including `mask(d.verdict)` | the Rust fence is a tuple-equality test, not prose |
| P7 | The reason line is printed by `run` and by the invocation printer, not by the grouper | the grouper prints blocks; tallies are the callers' |
| P8 | The T0 hash list is `sha256` over `traces/*.db` and `spool/<invocation>/*.jsonl`, paths relative to the store root | the invocation's members are those 372 files; the spool is what an ingest would re-read |
| P9 | `bin.sh` is sourced by every `.sh`; Python scripts call `lens.sensorium_bin()`; both refuse with the resolved path when `realpath` is outside the repo root | one rule, two spellings, one refusal sentence |
| P10 | `e6tsppp.py` compares the re-read to the rung-2 transcript line by line on `SWALLOWED --`, `RE-RAISED --`, `PROPAGATED --`, `UNCAUGHT --`, `dispositions:` after stripping the `[in <run>]`/`[×N …]` brackets is NOT done — brackets included, ids included | the store is the same store; anything that moves is a finding |
| P11 | The four corpus cases' `expect_line` pin the reason line and both tally lines whole; the collector still compares whole lines itself | rung 2's M4 |
| P12 | Task 5 reads E-legacy, E6-TS, E8‴, E-branch before the single re-read | a fence that fails after the re-read would taint a number already read |

## Pre-registration (Task 0 commits spec §5 verbatim as the record's §1, plus this block)

- **The lens:** the rung-2 invocation `20260910-150809-cbc8de`, read by label from `LENS.txt`; its trace set is the 372 `traces/*.db` plus the spool `.jsonl` files, each `sha256` listed in `…-s5-rung3-tracehashes.txt` at T0; a re-read whose list differs is dropped and named.
- **The hand-read table** (`…-s5-rung3-handread.md`, T0, before any rung-3 code): one row per catch-all block in `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt` (17 rows): origin as printed; lens `file:line` of the raise; every traced caller up to the test, by qualname; the untraced catcher the source shows; predicted reason variant (`returned` / `had not closed` / `later unwound`) or `unnamed`; predicted parent qualname; the reading's difficulty (`first reading` / `second reading`). Its last line is the predicted `unnamed` count after rung 3.
- **E6-TS‴ gate:** 0 false names; a printed untraced-catcher line whose parent qualname is not the row's, or printed for a row predicted `unnamed`, is false. A row predicted named that the reader leaves unnamed is a miss, reported with its count, not a STOP.
- **E6-TS′-fence:** every `SWALLOWED --`, `RE-RAISED --`, `PROPAGATED --`, `UNCAUGHT --` and `dispositions:` line of the re-read byte-identical (brackets and ids included) to the rung-2 transcript above, else STOP.
- **E-places:** SWALLOWED shapes exactly 28; the merged block is `useAiAssist.ts:56`'s (rung-2 adjudication rows S1, S11, S17) printed once with `[×3 …]`; every other rung-2 SWALLOWED block unchanged, else STOP.
- **E6-TS per-case SWALLOWED set:** rung 2's locked table unchanged (`silent_swallow` 1, `logged_catch` 1, `callback_sink` 1, `callback_handled` 1, `await_rejection_caught` 1, `finally_return` 1, `dependency_throw` 1, `rethrow_hop` 1, every other rung-2 case 0) and the four new cases 0 each; `translated`'s wrapper block reads the untraced-catcher reason (`returned` variant, parent the test function).
- **E8‴:** `escape.probe.test.ts` carries 14 `// ESCAPE` markers (13 + `callback_bare_rethrow catch_callback`), `swallow.probe.test.ts` 19 `// SWALLOW` markers, `check.mjs` `escape:count` expects 14; 96 checks, 0 failed.
- **E7‴ needles and rule:** `NEEDLES_RUNG2` reused as `rung3` — `oid`, `chain`, `Err` whole-word and case-sensitive; `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own` substring and case-insensitive — printed in the transcript header; 0 hits over the re-read transcript; vectors v30–v34 green.
- **E-legacy:** the fenced files above show zero diff against `51978b1`; their tests green; `Shape.key` for the Rust fixture in `tests/test_exceptions_typescript_grouping.py` equals the pre-change tuple.
- **E-branch:** `tests/test_acceptance_scripts.py` green.
- **Versions:** Python 0.11.0, sensorium-ts 0.2.0, wire 1, trace format 4.

---

### Task 0: The record, the hand read, the hash list, the lock

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3.md`, `…-s5-rung3-handread.md`, `…-s5-rung3-tracehashes.txt`, `tests/test_acceptance_s5_rung3_lock.py`
- Read only: the lens copy; the store (hashing); `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt`

**Interfaces:** Produces the record whose §1 T5 fills against, `HANDREAD` rows T5's instrument parses (a markdown table with the columns above, in that order), and the hash list T5's instrument verifies (`<sha256>  <relative path>` per line, `sha256sum -c` format).

- [ ] **Step 1: The hash list.** From the store root: `(cd "$SENSORIUM_DIR" && sha256sum traces/*.db spool/20260910-150809-cbc8de/*.jsonl)` → `…-s5-rung3-tracehashes.txt`; 372 + N lines; no absolute path in the file.
- [ ] **Step 2: The hand read.** For each of the 17 catch-all blocks in the rung-2 transcript, open the lens source at the raise site (`grep -rn` the message text under `<lens>/src`), walk the traced callers to the test, name the untraced catcher, predict the variant and parent qualname. Write the table; the last line `predicted unnamed after rung 3: <n>`. The two brainstorm spot-checks (`src/lib/sheets/formula.test.ts:37`, `src/components/PanelErrorBoundary.test.tsx`) are rows like any other.
- [ ] **Step 3: The record.** §1 = spec §5 verbatim (heading carried as `###`) + this plan's Pre-registration block verbatim, sources named with their commits (`51978b1` for the spec; this plan's commit). §2 pins: the hash list's line count and its own sha256; the E8‴ marker counts read with `grep -c '^\s*// ESCAPE '` / `'^\s*// SWALLOW '` (the format-comment lines excluded — state the command); the script census (`grep -ln sensorium typescript/acceptance/*.sh *.py` and how each resolves it: five `.sh` via `SENSORIUM_BIN:-sensorium`, four `.py` via a bare `["sensorium", …]`); the rung-2 E6-TS table; `wc -l` of every ceiling-relevant file. §3 `## 3. Results`, §4 `## 4. Decisions`, §5 `## 5. What the rung ships` as stubs reading `not measured (rung 3 pending)`. Commit: `docs(acceptance): S5 rung 3 record — pre-registration, hand read, trace hashes`.
- [ ] **Step 4: The lock test**, modelled on `tests/test_acceptance_s5_rung2_lock.py`: `BYTE_LOCK` = the sha of Step 3's commit; the locked range `## 1.`–`## 2.`; verbatim checks of spec §5 (`git show 51978b1:<spec>`) and of this plan's block; every endpoint name inside the range; the hand-read file's sha256 pinned in §1's last line and checked; a one-byte mutation refused. Run: `.venv/bin/python -m pytest -q tests/test_acceptance_s5_rung3_lock.py` → green. Commit: `test(acceptance): byte-lock the rung-3 pre-registration`.

### Task 1: The rules — the named reason, the window, the reason table

**Files:**
- Modify: `src/sensorium/query/exceptions_cmd.py:180-194` (`Disposition`), `src/sensorium/query/exceptions_typescript.py` (`_still_open_absorber`, `_ambiguous`, `run`, new `REASON_ORDER`, `_untraced_catcher`)
- Create: `tests/test_exceptions_typescript_reasons.py`, `tests/test_exceptions_typescript_window.py`, `docs/trace-format/vectors/v34-exceptions-typescript-untraced-catcher.json`; a row in `docs/trace-format/VECTORS.md`

**Interfaces:**
- Consumes: `Raise` (`origin`, `serial`, `handled`, `escaping`, `absorbing`, `orphan`), `Index.left_frame(serial)`, `Index.rejections`, `trace.frame(id)` (`parent_id`, `closed_by`, `unwind_exc`, `code_id`, `call_event_id`), `trace.code(id)` (`file`, `qualname`), `trace.code(id).firstlineno`, `fmt_exc`.
- Produces: `Disposition.reason` on every ambiguous disposition; `REASON_ORDER`; `run` printing `ambiguous by reason: …`.

- [ ] **Step 1: Failing tests.** In `tests/test_exceptions_typescript_reasons.py` (helpers from `tests/ts_traces.py`; `FILE`, `cli`, `ANSWERED`, `out` as the sibling file imports them):

```python
def test_a_throw_caught_by_untraced_code_inside_a_traced_frame_is_named(
        tmp_path, monkeypatch, capsys):
    """`expect(() => parse('x')).toThrow()`: parse unwinds, the arrow unwinds,
    the test frame returns, no handler row anywhere."""
    exc = ts_exc("FormulaError", "Unknown function 'sqrt'", 9)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "formula > rejects sqrt", 30],
               [FILE, "<anonymous>", 37], [FILE, "parse", 80]],
        frames=[frame(1, 1, 6),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc),
                frame(3, 3, parent=2, depth=2, unwind_exc=exc)],
        events=[call(1000, 1, 30, task=1), call(2000, 2, 37, task=1),
                call(3000, 3, 80, task=1),
                raise_ev(4000, 3, 3, 86, exc, task=1),
                ret(6000, 1, 1, task=1)],
        tasks=[task(1, "formula > rejects sqrt")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside "
            "formula > rejects sqrt (config.ts): f2 unwound, its caller f1 "
            "returned; not followed") in o, o
    assert "dispositions: ambiguous 1" in o, o
    assert "ambiguous by reason: untraced catcher 1" in o, o
    assert "no rule of this recorder" not in o, o
```

  Add, in the same file: the `had not closed` variant (parent frame with no `ret` and `closed_by=None` → `frame(1, 1)` without a return event); the `later unwound` variant (parent `unwind_exc` a different serial → `later unwound with Error('later')`); a rejection-kind exc (`kind="rejection"`) reads the same sentence; a handler row in the window (an absorbing HANDLED in frame 2) keeps the reason OUT (`not unit.handled` guard) and prints the existing suspended/translated sentence instead; an unhandled rejection (`meta.unhandled_rejections`) stays UNCAUGHT; a single-frame unwind under a returning parent is named with `f<child>` = the raising frame; `test_every_reason_the_module_prints_has_a_key`: walk every `Disposition("ambiguous", …)` the module can return by driving each branch with a hand-built trace, assert `d.reason in REASON_ORDER`, and assert the module's source has no `Disposition(\n        "ambiguous"` without a `reason=` (a regex over `inspect.getsource`); the reason line is absent when `ambiguous` is 0; keys print in `REASON_ORDER` order with zeros omitted (a trace with one escaped and one untraced-catcher unit prints `escaped 1, untraced catcher 1`).

  In `tests/test_exceptions_typescript_window.py`:

```python
def test_a_logged_rethrow_out_of_the_test_root_propagates(
        tmp_path, monkeypatch, capsys):
    """`catch (e) { console.error(e); throw e }` in the test body: the
    absorbing handler's frame was closed by the rethrow itself, which is
    the rethrow's predecessor and not an unfinished handler."""
    exc = ts_exc("Error", "disk offline", 4)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "boot > falls back", 5], [FILE, "load", 20]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                raise_ev(3000, 2, 2, 22, exc, task=1),
                handled_ev(4000, 1, 1, 9, exc, "catch", task=1),
                raise_ev(5000, 1, 1, 10, exc, task=1)],
        tasks=[task(1, "boot > falls back")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "RE-RAISED -- raised again at e5 (boot > falls back L10) → propagated" in o, o
    assert 'PROPAGATED -- to the harness: test "boot > falls back" failed' in o, o
    assert "dispositions: re-raised 1, propagated 1" in o, o
```

  And: the suspended `.catch(async …)` handler in the unit's own window still declines rule 4 (copy the shape from `tests/test_exceptions_typescript_ambiguous.py`'s existing test and assert its sentence is unchanged); an earlier-window absorbing handler whose frame RETURNED and a later rethrow from another frame of the same serial (an escaped-then-rethrown object) still reads the escaped reason, never PROPAGATED.

- [ ] **Step 2: Run, see them fail.** `.venv/bin/python -m pytest -q tests/test_exceptions_typescript_reasons.py tests/test_exceptions_typescript_window.py` → every new test fails on the missing sentence / `REASON_ORDER` import.
- [ ] **Step 3: Implement.** `exceptions_cmd.py`: add `reason: str | None = None` after `site` with a two-line comment (P1). `exceptions_typescript.py`:

```python
#: Every reason an AMBIGUOUS line can carry, in printing order (design
#: §2.3). `unnamed` is rule 5's catch-all and the number rung 3 is
#: measured on; a reason without a key here is a test failure.
REASON_ORDER = ("escaped", "untraced catcher", "suspended", "translated",
                "primitive", "orphan", "incomplete", "unnamed")


def _untraced_catcher(trace, unit, idx) -> Disposition | None:
    """§2.1: no handler row in this window, the outermost frame the serial
    left has a traced parent, and that parent is not the raise's own frame.
    Names the footprint; claims nothing about what the untraced code did."""
    if unit.handled or unit.escaping or unit.serial in idx.rejections:
        return None
    f = idx.left_frame(unit.serial)
    if f is None or f.parent_id is None or f.parent_id == unit.origin.frame_id:
        return None
    p = trace.frame(f.parent_id)
    if p is None:
        return None
    code = trace.code(p.code_id)
    where = f"{code.qualname} ({Path(code.file).name})"
    if p.closed_by == "return":
        fate = f"its caller f{p.id} returned; not followed"
    elif p.closed_by == "unwind":
        fate = (f"its caller f{p.id} later unwound with "
                f"{fmt_exc(p.unwind_exc)}: a translation by untraced code, "
                "or a later failure, indistinguishable")
    else:
        fate = (f"its caller f{p.id} had not closed at the end of the "
                "recording; not followed")
    site = (code.file, code.firstlineno, code.qualname)     # P3
    return Disposition(
        "ambiguous",
        f"AMBIGUOUS -- caught by untraced code inside {where}: f{f.id} "
        f"unwound, {fate}",
        site=site, reason="untraced catcher")
```

  `_ambiguous`: after the `unit.escaping` branch, `d = _untraced_catcher(trace, unit, idx); if d is not None: return d`; then the existing branches, each `Disposition` gaining `reason=` (`suspended` for both open-frame tails, `translated`, `incomplete`, `unnamed` for the catch-all; `orphan` when `unit.orphan` reaches the catch-all; `primitive` where the primitive sentence is built — find every `Disposition("ambiguous"` in the module and tag it). `_still_open_absorber`: iterate `[h for h in unit.handled if _how(h) in ABSORBING]` instead of `unit.absorbing`; rewrite its docstring to §2.2 (the window, the predecessor). `run`: after the `dispositions:` print:

```python
    if reasons:
        print("ambiguous by reason: " + ", ".join(
            f"{r} {reasons[r]}" for r in REASON_ORDER if reasons.get(r)))
```

  where `shapes, tally, reasons = group_units(...)` (Task 2 lands the third value; until then, in THIS task, compute `reasons` in `run` from `classify` over `scope` — and Task 2 replaces it with the grouper's value; note it in the report).
- [ ] **Step 4: Run.** The two new files green; `tests/test_exceptions_typescript.py tests/test_exceptions_typescript_ambiguous.py tests/test_exceptions_invocation_typescript.py tests/test_vectors.py` green — any vector whose reason line moved (the `translated`-like shape has none among v30–v33; expect zero) is re-pinned with the reason named in the commit.
- [ ] **Step 5: v34.** Copy v30's JSON shape: three codes (the test, the arrow, `parse`), three frames as the first test above, the RAISE, the test's RETURN; two questions: the reason line + `ambiguous by reason: untraced catcher 1` + `expect_absent` of the eight needles and `no rule of this recorder`; and `tree $RUN` still renders. `VECTORS.md` row after v33; prose count thirty-four. `tests/test_vectors.py` green.
- [ ] **Step 6: Mutants.** Flip `p.closed_by == "return"` to `!=`; drop the `not unit.handled` guard; use `unit.absorbing` again in `_still_open_absorber`. Each under `PYTHONDONTWRITEBYTECODE=1` after `find . -name __pycache__ -exec rm -r {} +`, `setsid`, killed by pgid on timeout; name the failing tests. `wc -l` of the module (< 780 or split per the constraint).
- [ ] **Step 7: Commit.** `feat(exceptions): name the untraced catcher, scope rule 4 to the window, tally ambiguity by reason`.

### Task 2: The component key

**Files:**
- Modify: `src/sensorium/query/exceptions_group.py` (`Renderer`, `RUST`, `TYPESCRIPT`, `group_units`, `group_chains`), `src/sensorium/query/exceptions_invocation.py` (`_merge`, the print after the summed tally), `src/sensorium/query/exceptions_typescript.py:run` (take `reasons` from the grouper)
- Create: `tests/test_exceptions_typescript_grouping.py`

**Interfaces:**
- Produces: `Renderer.key(trace, unit, d, site, hops) -> tuple`; `group_units(...) -> (shapes, tally, reasons)`; `group_chains(...) -> (shapes, tally)`; the invocation printing `ambiguous by reason:` once.

- [ ] **Step 1: Failing tests.** `tests/test_exceptions_typescript_grouping.py`: (a) three TypeScript units swallowed at one `(file, 56, "useAiAssist")` site in frames 32, 128 and 174 (the ids that defeated the mask) → ONE block with `[×3`; (b) two units with identical masked prose but different sites → two blocks; (c) two untraced-catcher units under one parent → one block keyed on the parent; (d) the Rust fence: build a Rust `Disposition` and unit via `exceptions_rust`'s own helpers (import the sibling `tests/test_exceptions_rust_grouping.py`'s fixture) and assert `RUST.key(trace, unit, d, site, hops) == (d.tag, site, mask(d.verdict), hops if d.site is None else None)`; (e) `group_chains` returns exactly two values; (f) an invocation of two TypeScript members prints `ambiguous by reason:` once with summed counts (add to `tests/test_exceptions_invocation_typescript.py` only if it stays under 780; else here).
- [ ] **Step 2: Fail.** Run the file → `Renderer` has no `key`.
- [ ] **Step 3: Implement.**

```python
    key: object                 # (trace, unit, d, site, hops) -> the group key


def _rust_key(trace, unit, d, site, hops):
    """Today's tuple, verbatim: the mask stays Rust's (design R3)."""
    return (d.tag, site, mask(d.verdict), hops if d.site is None else None)


def _typescript_key(trace, unit, d, site, hops):
    """The classifier's own parts (design §3.1): no prose, no mask."""
    return (d.tag, d.reason, site, exceptions_typescript._site(trace, unit.origin))
```

  `RUST = Renderer(..., exceptions_rust.TAG_ORDER, _rust_key)`, `TYPESCRIPT = Renderer(..., _typescript_key)`; in `group_units` replace the literal `key = (...)` with `key = render.key(trace, unit, d, site_of(trace, unit, d, render), hops)` and add `reasons: dict[str, int]` counting `d.reason` for `d.tag == "ambiguous"`; return three; `group_chains` returns `shapes, tally`. `exceptions_typescript.run` takes `reasons` from the grouper (drop Task 1's interim). `_merge`: sum `member_reasons` into a dict returned as a third value; the printer emits the line after `dispositions:` when non-empty. `Shape.key`'s comment updated.
- [ ] **Step 4: Run.** The new file, `tests/test_exceptions_rust_grouping.py`, `tests/test_exceptions_invocation.py`, `tests/test_exceptions_invocation_typescript.py`, `tests/test_vectors.py`, `tests/test_exceptions_typescript*.py` green; `git diff --stat -- tests/test_exceptions_rust_grouping.py tests/test_exceptions_invocation.py src/sensorium/query/exceptions_rust.py` empty.
- [ ] **Step 5: Mutant.** Swap `_typescript_key` to include `mask(d.verdict)` → test (a) fails; make `RUST.key` drop `mask` → test (d) fails. Name them.
- [ ] **Step 6: Commit.** `feat(exceptions): the TypeScript shape key is the classifier's components; Rust keeps its mask`.

### Task 3: The corpus, the re-pin, the probe marker

**Files:**
- Create: `corpus/typescript/untraced_catcher/{formula.ts,untraced_catcher.test.ts,questions.yaml}`, `untraced_catcher_rejection/…`, `untraced_catcher_later_failure/…`, `logged_rethrow_to_harness/…`
- Modify: `corpus/typescript/translated/questions.yaml`, `corpus/typescript/README.md` (four rows + the exit-1 note), `docs/corpus.md` (the roll-call), `typescript/probes/src/escape.probe.test.ts`, `typescript/probes/check.mjs:355`, `typescript/probes/README.md`

**Interfaces:** Consumes Task 1's sentences verbatim. Produces the pins T5's E6-TS reads.

- [ ] **Step 1: The cases.** Sources in the corpus style (a `// BUG:` or `// NOT A BUG:` marker where the rung-2 cases have one):
  - `untraced_catcher`: `formula.ts` exports `class FormulaError extends Error` and `parse(src)` that throws `FormulaError("Unknown function 'sqrt'")` for `sqrt`; the test `expect(() => parse('sqrt(4)')).toThrow(FormulaError)`. Green suite.
  - `untraced_catcher_rejection`: `fetchThing()` is `async` and throws `Error('offline')`; `await expect(fetchThing()).rejects.toThrow('offline')`. Green.
  - `untraced_catcher_later_failure`: the `toThrow` line, then `throw new Error('the assertion after was wrong')` at the test root. Red suite; no `record:` key (refused on vitest cases).
  - `logged_rethrow_to_harness`: `try { load() } catch (e) { console.error(e); throw e }` in the test body; `load` throws. Red.
- [ ] **Step 2: Record and pin.** `.venv/bin/python corpus/run_corpus.py --only-dir typescript --require-driver --only <case>` (read the runner's flags; else the whole dir) — read the printed output; check each word against the pre-registration; pin `expect_line` groups for the RAISE line, the verdict line, `dispositions:` and `ambiguous by reason:` whole; `expect_absent: ["SWALLOWED", "no rule of this recorder"]` on the three untraced-catcher cases; `why_logs_fail` naming the three channels. Re-pin `translated`'s wrapper block to the untraced-catcher sentence and add the reason line; rewrite its `truth` so it argues the named reason.
- [ ] **Step 3: The probe.** In `escape.probe.test.ts` add, in the file's style:

```ts
export async function callbackBareRethrow(): Promise<string> {
  try {
    // ESCAPE callback_bare_rethrow catch_callback
    await Promise.reject(new Error('cb')).catch((e) => { throw e; });
  } catch {
    return 'rethrown';
  }
  return 'unreachable';
}
```

  and a test that calls it; `check.mjs:355` → `=== 14`; the probes README's count. `npm --prefix typescript/probes run probe` (the dry run; the measurement is T5's) → `escape:count` 14, 0 failed.
- [ ] **Step 4: Docs rows.** `corpus/typescript/README.md`: four rows (`exceptions` column), the red-suite note names the two new red cases; `docs/corpus.md`: the roll-call paragraph gains the four with their shapes and the nine/seven arithmetic updated (nine accuse nothing + four = thirteen; say it).
- [ ] **Step 5: Verify.** `--only-dir typescript --require-driver` → 32 cases, every question green; `--only-dir .` unchanged for Python/Rust; `tests/test_corpus.py tests/test_ceiling.py` green.
- [ ] **Step 6: Commit.** `test(corpus): four rung-3 shapes, the translated re-pin, the callback bare-rethrow probe`.

### Task 4: Instruments from the branch

**Files:**
- Create: `typescript/acceptance/bin.sh`, `tests/test_acceptance_scripts.py`
- Modify: `typescript/acceptance/{e10p.sh,e3.sh,arms.sh,e6pp.sh,e6tsp.sh,e7.sh}` (source `bin.sh`), `{e11_report.py,reported.py,firstuse.py}` (`lens.sensorium_bin()`), `lens.py` (`sensorium_bin`, the label stamped only here), every script that writes a `"lens"` key of its own (`grep -n '"lens"' typescript/acceptance/*.py | grep -v lens.py | grep -v assemble`), `e7_report.py` (`LISTS["rung3"]`, the rule printed)

- [ ] **Step 1: Failing test.** `tests/test_acceptance_scripts.py`: (a) no `.sh` under `typescript/acceptance/` contains `SENSORIUM_BIN:-sensorium` or a bare `sensorium ` command outside a comment, and every one that invokes it sources `bin.sh`; (b) no `.py` there passes `"sensorium"` as `argv[0]` except through `lens.sensorium_bin()`; (c) `"lens":` literal appears only in `lens.py` and `assemble*.py`; (d) `bin.sh` refuses when `REPO_ROOT/.venv/bin/sensorium` is absent (run it in a tmp copy with a fake root) and when `realpath` escapes the root (symlink out); (e) `lens.sensorium_bin()` returns a path under the repo root.
- [ ] **Step 2: Fail**, then implement:

```bash
# typescript/acceptance/bin.sh -- sourced. The branch's binary or nothing.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SENSORIUM_BIN="$REPO_ROOT/.venv/bin/sensorium"
if [ ! -x "$SENSORIUM_BIN" ] || [[ "$(realpath "$SENSORIUM_BIN")" != "$REPO_ROOT"/* ]]; then
  echo "refused: sensorium resolves to '$SENSORIUM_BIN', not the branch's .venv under $REPO_ROOT" >&2
  exit 3
fi
```

  `lens.py`: `def sensorium_bin() -> str` with the same rule and refusal sentence (raise `SystemExit(3)`); the three Python scripts call it. Delete every per-instrument `"lens"` write named by the grep; the assemblers stamp `LENS` on every cell. `e7_report.py`: `LISTS["rung3"] = NEEDLES_RUNG2`; the transcript header prints one line per needle `needle <name>: <whole-word|substring>, <case-sensitive|insensitive>`.
- [ ] **Step 3: Run.** The new test green; `bash -n` on every `.sh`; a dry run of `e7.sh` against a corpus trace with `E7_NEEDLES=rung3` shows the header.
- [ ] **Step 4: Commit.** `test(acceptance): instruments resolve the branch's binary; the assembler alone stamps the lens label; the needle rule is printed`.

### Task 5: Measurement — fences first, one re-read

**Files:**
- Create: `typescript/acceptance/e6tsppp.py` (the re-read + comparisons + cells), `typescript/acceptance/assemble_rung3.py`, `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3-exceptions.txt` (the re-read transcript, redacted), `…-s5-rung3.results.json`
- Modify: the record §2.3 (any pre-number fix), §3, §4, §5

**Interfaces:** Consumes the hash list, the hand-read table, the rung-2 transcript, `sensorium_bin()`, `LENS`. Produces cells `{value, n, lens, dropped, recorder, recorder_rev, recorder_basis}` per endpoint.

- [ ] **Step 1: The instrument**, dry-run on the corpus store before touching the kept store: `e6tsppp.py <store> <invocation> <rung2 transcript> <handread.md> <hashes.txt> <out dir>`: (1) `sha256sum -c` the hash list from the store root, refuse on any mismatch; (2) run `[sensorium_bin(), "exceptions", inv, "--limit", "10000"]` with `SENSORIUM_DIR=<store>`, env scrubbed of `SENSORIUM_MANIFEST_DIR`/`SENSORIUM_SPOOL`; save the transcript; (3) E6-TS′-fence: extract the five line kinds from both transcripts in order, diff, count differences; (4) E-places: count `SWALLOWED --` blocks and the `[×3` bracket at the `useAiAssist` block; (5) E6-TS‴: for each `caught by untraced code inside <q> (…)` line, find the block's origin line, look the origin up in the hand-read table, compare parent qualname and predicted variant; count true / false / missed (rows predicted named but printed unnamed) / unnamed-after; (6) write cells + a JSON of every comparison row. Every comparison row is written BEFORE any verdict word.
- [ ] **Step 2: Fences, in order** (each written into §3 as it is read): E-legacy (`git diff 51978b1..HEAD --stat` over the fenced paths → empty; the fenced tests green; the grouping fence test green); E6-TS (corpus run, the collector comparing whole `dispositions:` lines per case against the locked table — reuse rung 2's `e6ts.py`, extended to read the reason line); E8‴ (`npm run probe`, JSON captured with revs); E-branch (the test). Any STOP here stops the rung before the re-read.
- [ ] **Step 3: The re-read** — once. E6-TS‴, E6-TS′-fence, E-places, E7‴ (`e7_report.py` with `E7_NEEDLES=rung3` over the new transcript; vectors v30–v34). Words per the rule.
- [ ] **Step 4: Record.** §3 one row per endpoint with the cell and the word; §4 the decisions (every false/missed/unnamed row quoted; the merged `useAiAssist` block quoted; the fence diff, empty or not); §5 the shipping word and the gaps found. `assemble_rung3.py` redacts and stamps; every cell carries provenance (`sensorium 0.10.0` at HEAD — the bump is Task 6's; say so in the cell's `recorder`). No box path.
- [ ] **Step 5: Commit** `test(acceptance): S5 rung 3 measured — <words>`; lock test, ceiling, full suite green.

### Task 6: Docs and versions

**Files:**
- Modify: `pyproject.toml` (0.11.0), `CHANGELOG.md` (`## 0.11.0`), `typescript/HONESTY.md` §4 + index row, `typescript/HONESTY-BLIND-SPOTS.md` item 27, `docs/query.md` (the TypeScript paragraph: the reason line, the named catcher), `README.md` (≤ 1 sentence), `typescript/README.md`, `docs/CARRIED-DEBT.md` (rung-3 section: Gap 1–4 and the neighbour closed with dated lines pointing at the record; the callback probe marker closed; new debts from the record's §5), the spec's §12
- Venv reinstalls named by `tests/test_release_tokens.py`'s docstring

- [ ] **Step 1:** `chore(release): sensorium 0.11.0` — pyproject + the CHANGELOG entry (the reason, the window, the key, the corpus, the record's headline numbers quoted from §3, the probe marker, the instruments) + reinstalls; `tests/test_release_tokens.py` green.
- [ ] **Step 2:** the docs; the spec's §12 lists every ledger `Ruling:` and every plan decision that changed; `grep -rn "no rule of this recorder" README.md typescript docs/query.md docs/corpus.md` — every hit describes the catch-all as the remainder, not as the modal reason. Suites once more on 3.12/3.13/3.14, npm, corpus, live. Commit `docs: HONESTY, query.md, CARRIED-DEBT and the ledger for rung 3`.

### Task 7: Final review, fix wave, PR

- [ ] Final whole-branch review on the most capable model over `51978b1..HEAD`; one fix wave; one scoped re-review; push; PR against `main` with the record's numbers and every ruling; CI; merge is Brice's; then archive the ledger to `/mnt/extra/sensorium-rung2/sdd-archive/`, remove the worktree, delete the branch, verify sync, reinstall the global tool.

---

## Self-review

- **Spec coverage.** §2.1 → T1 Step 3; §2.2 → T1 (`_still_open_absorber`); §2.3 → T1 Step 3 + T2 (`reasons`); §2.4 → E6-TS′-fence; §3.1–3.3 → T2 + E-places; §4.1 → T3 Steps 1–2; §4.2 → T3 Step 3; §4.3 → T4; §5 → T0 + T5; §6 → the test files per task; §7 → the task order; §8 → T6 + the constraints; §9 R1–R10 → P1–P12 and the tasks; §10 → recorded; §11 → T0; §12 → T6.
- **Placeholders.** None: every test and code step carries its content.
- **Type consistency.** `Renderer.key(trace, unit, d, site, hops)` in T2 matches `group_units`'s call; `group_units` returns three everywhere after T2 and T1's interim is removed by T2; `Disposition.reason` (T1) is what `_typescript_key` (T2) and the corpus pins (T3) read; `sensorium_bin()` (T4) is what `e6tsppp.py` (T5) calls; `REASON_ORDER` keys are the words the corpus and v34 pin.
