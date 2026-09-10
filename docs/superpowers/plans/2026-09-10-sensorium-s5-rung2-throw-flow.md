# S5 rung 2 — throw flow: `exceptions` on a TypeScript trace: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sensorium exceptions <run>` and `sensorium exceptions <invocation>` answer on TypeScript traces with Python's five words, every SWALLOWED they print established by the recording, measured by zero false SWALLOWED on a seventeen-case corpus and on the VTT lens — shipping `sensorium-ts` **0.2.0** and Python **0.10.0** with trace format 4 untouched.

**Architecture:** The transform classifies catch bindings, rejection callbacks and completing `finally` blocks at splice time and writes the verdict-bearing `how` word on the existing HANDLED record; the runtime wraps callbacks and keeps a per-frame in-flight mark; the converter passes the recorder's `err_flow: true` through. A new reader module, `exceptions_typescript.py`, applies Python's rule shape over the serial identity the wire already carries with Rust's ambiguous-by-default discipline; `exceptions_group` is generalised over a per-language renderer so the invocation mode dispatches per member. Nothing is judged at conversion; nothing is minted the wire does not carry.

**Tech Stack:** Node v24.16.0 (ESM `.mjs`, JSDoc, `tsc --checkJs`, the consumer's TypeScript for parsing, `magic-string`); Python 3.12–3.14; vitest 4.1.9 / vite 6.4.3 on the lens and in the corpus project; sqlite3. No new dependency on either side.

**Spec:** `docs/superpowers/specs/2026-09-10-sensorium-s5-rung2-throw-flow-design.md` — §2 (the records), §3 (the rules), §4 (the invocation mode), §5 (converter, contract, vectors), §6 (corpus, probes, ledger), §7 (endpoints + the adjudication protocol), §8–§10, §11 (R1–R14). **Precedent:** `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (R2, R8, R15) and `rust/HONESTY-ERR-FLOW.md` §11. **Rigor:** `~/.claude/skills/rigorous-experiments/SKILL.md`. **Style:** as the rung-1 and slice-2 plans — interfaces and invariants, verbatim text only where a fresh implementer would guess wrong (the splice forms, the runtime signatures, the classifier's rules, the refusal and verdict sentences, the instruments' shapes).

## Global Constraints

- **The lens is read-only except by the Task 7 instruments.** `/mnt/extra/sensorium-s5/vtt/frontend` (VTT `0091e97`, vitest 4.1.9, vite 6.4.3, typescript 5.9.3, jsdom 29.1.1) is touched only by the guarded acceptance runs; `~/workspace/projects/vtt` is never read. Nothing measured writes to `/`.
- **Store:** `SENSORIUM_DIR=/mnt/extra/sensorium-s5/store-rung2ts` for every trace this rung records or converts; results JSON under `<store>/results/`; the committed results file is redacted by its assembler and refused if a box path survives. **No box path is ever committed.**
- **Pre-registration is committed before any code** (Task 0), byte-locked: after a number is read no threshold moves, no arm is added, no run is re-rolled. An infrastructure kill re-runs from zero with the reason recorded. **The E6-TS′ adjudication protocol is fixed in §1 before any SWALLOWED line is read** and every line's adjudication is written into the record.
- **Legacy output is byte-identical:** the Python and Rust `exceptions` outputs, every existing vector, the corpus's Python and Rust cases, `PYTHON`/`RUST` vocabulary strings — pinned by their own suites, which are the regression fence. The rung-1 TypeScript corpus questions that pin **event ids** (`corpus/typescript/suspended_at_end`, the renamed `silent_swallow`) are re-pinned with the reason stated per question (spec §5.1, Rust R12's precedent) — that is the ONE sanctioned change to existing expectations.
- **Every splice is newline-free:** `lines(out) === lines(in)` asserted on every golden and every probe file (rung 1's invariant).
- **Wire stays version 1.** The BOOT record gains `capabilities`; HANDLED gains `how` words; nothing else on the wire changes shape. `TRACE_FORMAT` stays 4.
- **Dependency policy:** `typescript/` runtime dependency `magic-string` only; `rt.mjs` imports `node:` builtins only; Python adds nothing.
- **Verdict words come from the rule** (spec §3.3): no PASS on an endpoint whose rule names none; a prediction that does not hold is written as such.
- **Ceilings** (`tests/test_ceiling.py`, 800; records/plans/specs exempt): `transform.mjs` is at 708 — the escape rule goes in a **new** `typescript/src/escape.mjs`; `rt.mjs` 637; `exceptions_cmd.py` 757 gains only its dispatch; `exceptions_invocation.py` 355, `exceptions_group.py` 361; `typescript/HONESTY.md` 757 — split §10 into `typescript/HONESTY-BLIND-SPOTS.md` if the rewrite would cross (measured at Task 8); `docs/TRACE-FORMAT.md` 799 — the split in Task 0 precedes every edit; `docs/CARRIED-DEBT.md` 774 — cut the oldest section to `docs/CARRIED-DEBT-ARCHIVE-6.md` before appending; `README.md` 782 — at most one sentence; `CHANGELOG.md` 637 — no cut needed; `tests/test_ts_ingest_meta.py` 777 — new ingest tests go in a new file.
- **Tests:** TDD per task; every new Python test mutation-checked under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged, mutant runs under `setsid` and killed by process group on timeout; every new Node test run with `npm --prefix typescript test`; `npm --prefix typescript run check` (never `npx tsc -p` from the root, R4). Functions under 50 lines.
- **Load guard** before every timed or recorded arm on the lens: 1-minute load under 4.0, up to 90 tries 20 s apart, the reading written beside every wall (`arms.sh`'s `wait_for_load`).
- **Commits:** conventional prefixes; the session's trailer lines. Branch `feat/s5-rung2` off `main` at `db37351`, worktree `/mnt/extra/sensorium-rung2/s5-rung2`, venv `.venv` 3.13 (`uv venv .venv --python 3.13 && uv pip install -p .venv/bin/python -e ".[dev]"`, plus `.venv312`/`.venv314` for the matrix), `npm ci --prefix typescript && npm ci --prefix typescript/probes && npm ci --prefix corpus/typescript`. SDD ledger `<worktree>/.superpowers/sdd/2026-09-10-sensorium-s5-rung2-throw-flow/progress.md`, archived to `/mnt/extra/sensorium-rung2/sdd-archive/` before the worktree goes.
- **Gotchas carried:** `pkill -f`/`pgrep -f` self-match — anchor `^[^ ]*node ` or find pids from spool names; `setsid nohup x &` changes the pid; `controls.mjs`-style helper scripts must scrub `SENSORIUM_MANIFEST_DIR`/`SENSORIUM_SPOOL` (a probe run was polluted once); the global `sensorium` tool is never reinstalled from the worktree (E1‴/E10″ compare against recorded numbers, not against main's binary).

---

## Decisions this plan makes (each amends the spec non-silently in Task 8)

| # | Question | Decision | Why | Cost if wrong |
|---|---|---|---|---|
| P1 | How a `finally` sink learns a throw is in flight (spec §2.3 said `raise`/`thr` set a mark) | **A catch-less `try` whose `finally` completes gains a synthetic marking clause**: `catch(__sfe){__srt.mark(__sf,__sfe);throw __sfe}` spliced before its `finally`; `raise(f, e)` and the synthetic clause set `f.mark`; `handled` clears it; `handledFinally` records when set. `thr` sets nothing. | A `Frame` holds no parent reference and an awaited rejection lands in another microtask, so an unwinding callee cannot find its awaiter; the synthetic clause sees library throws and awaited rejections alike and carries the real serial | a `try` with its own `catch` whose body's **awaited** callee rejects and whose `finally` returns records nothing — a declared blind spot; a synchronous throw inside that catch body is a `raise` and marks |
| P2 | Where the escape rule lives | `typescript/src/escape.mjs`, exporting `catchHow(ts, clause)`, `callbackHow(ts, arg)`, `finallyCompletes(ts, block)` — pure functions over AST nodes, unit-tested directly | `transform.mjs` is at 708 lines | one more module in `exports` is not needed (internal) |
| P3 | `emptyCatch` | **Replaced** by `catchCb(f, line, how, fn)`; the transform emits `catchCb` for every rejection handler; `emptyCatch` deleted (a 0.1.x transform output never reaches a 0.2.0 runtime — the driver pins the package) | one wrapper, one signature | none |
| P4 | The `.then` shape | Only a two-argument `.then(x, arg)` wraps its second argument; `.then(fn)` and `.catch()` untouched; `.finally(fn)` untouched | spec §2.2 | none |
| P5 | Generalising the grouper | `exceptions_group.group_units(trace, units, idx, classify, render)` where `render` is a module-level `Renderer` dataclass `{at, hops_line, site, site_text, site_file, tag_order}` supplied by each language module; `group_chains` stays as a thin wrapper passing the Rust renderer, so every Rust caller and test is byte-unchanged | one grouper, two renderers | none |
| P6 | The TypeScript "unit" the grouper sees | a `Raise` object `{origin: event, handled: [events], last_raise: event}` per RAISE serial (and one per orphan HANDLED serial), built by the index; `origin` is what `_at`/bracket ids print | the grouper reads `.origin` today | none |
| P7 | The vocabulary column | `TYPESCRIPT.exceptions_refusal` becomes `None` (dispatched before `_language_refusal`, as `RUST`'s) and v23's sentence about `exceptions` refusing at exit 3 is re-pinned to the capability sentence on a 0.1.x-shaped trace (v32) | the old sentence names a rung that has shipped | none |
| P8 | The record and results file names | `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` (+ `.results.json`, `-e6tsp-adjudication.md`, `-e7-exceptions.txt`); lock test `tests/test_acceptance_s5_rung2_lock.py` (the slice-2 lock test's pattern, `rung3.byte_lock_check`); assembler `typescript/acceptance/assemble_rung2.py` | one record per slice, as before | none |
| P9 | The adjudication table | one row per SWALLOWED shape: `shape id · site (file:line) · how · the source lines quoted · verdict TRUE/FALSE · reason under §7's definition`; written to `-e6tsp-adjudication.md`, its counts copied into §3 | the per-line record is what lets Brice re-read the gate | none |
| P10 | The census instrument for E2″ | `typescript/acceptance/census_catch.mjs <root>`: walks the lens `src` with the consumer's TypeScript, counts catch clauses / rejection-callback call sites / completing `finally` blocks the walker sees, and the `how` records the transform would write, by kind; ratio = spliced / seen after NAMED exclusions | rung 1's `census.mjs` shape | none |
| P11 | Corpus rename | `corpus/typescript/exceptions_refused/` → `silent_swallow/` (`git mv`; same `config.ts`; new questions); the refusal becomes v32 | spec R14 | none |
| P12 | Where the new ingest test goes | `tests/test_ts_ingest_caps.py` (the BOOT-capabilities pass-through) — `test_ts_ingest_meta.py` is at 777 | ceiling | none |
| P14 | When `sensorium-ts` becomes 0.2.0 | At Task 1, with the runtime whose declaration changed; Python's 0.10.0 waits for Task 8 | Task 6's corpus questions pin the recorder string `info` prints, which is the BOOT's `VERSION` — written before Task 8 | one version-bearing commit earlier in the branch |
| P13 | Task order: runtime before transform | The runtime's `catchCb`/`mark`/`handledFinally` land first (Task 1) so no Node test ever executes a transformed call the runtime lacks; the probes are written with the runtime and go green with the transform | `hook.test.mjs` and `vite.test.mjs` run transformed code against the real `rt.mjs` | none |

## Pre-registration (Task 0 commits spec §7's table and its adjudication protocol verbatim as the record's §1, plus these pins)

- **The lens:** `/mnt/extra/sensorium-s5/vtt/frontend`, VTT `0091e97`, manifest `/mnt/extra/sensorium-s5/manifest-rung1-before.txt` (748 entries) verified before and after every arm that touches it.
- **E3-TS″'s file, named now:** `src/__tests__/useMeshVoice.test.tsx` (rung 1's), twenty recordings, `diff` each against the first.
- **E6-TS′'s run:** ONE guarded `sensorium ts run -- npx vitest run` on the lens at tier `call` through THIS rung's recorder; then `sensorium exceptions <invocation>` with `--limit 10000`; the transcript committed beside the record; every SWALLOWED shape adjudicated under §7's protocol; the ambiguous-escaped count, the per-disposition tally and the number of shapes whose adjudication needed a second reading reported.
- **E7″'s needles**, each a literal: `oid`, `chain`, `Err`, `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own`, over the E6-TS′ transcript and over one single-trace `exceptions` transcript.
- **E8″'s shapes:** every `// SWALLOW` / `// ESCAPE` marker in `swallow.probe.test.ts` and `escape.probe.test.ts`, one check per marker.
- **E1‴ / E10″:** `arms.sh` ×5 batches interleaved; `e10p.sh` over the E6-TS′ run's spool set at jobs 16 n=5 and over its `useMeshVoice` spool n=5; reported beside 1.0587 / 1.1324 and 16.3859 s / 0.1648 s.
- **E6-TS's pre-registered set, per corpus case** (spec §6.1's verdict column, fixed here before any case exists): SWALLOWED lines — `silent_swallow` 1 (the `catch` in `loadConfig`), `logged_catch` 1, `callback_sink` 1, `callback_handled` 1, `await_rejection_caught` 1, `finally_return` 1, `dependency_throw` 1, `rethrow_hop` 1 (the rethrow's block); every other case 0. The exact line text is pinned by each case's `questions.yaml` (Task 6) before the collector runs (Task 7); a case whose count differs from this table STOPs, whatever its text.
- **Reported without a gate:** the count of HANDLED records per `how` on the lens run; the share of catch clauses reading `catch_escaped`.

## File structure

```
typescript/src/escape.mjs                     catchHow / callbackHow / finallyCompletes   [create, T2]
typescript/src/transform.mjs                  spliceCatch(how), spliceRejectionCallback, spliceFinally  [modify, T2]
typescript/src/rt.mjs                         catchCb, mark, handledFinally, Frame.mark, BOOT capabilities  [modify, T1]
typescript/src/index.mjs, package.json        0.2.0                                        [modify, T8]
typescript/test/escape.test.mjs               the rule table                              [create, T2]
typescript/test/golden/*.ts (+ .expected.ts)  one per how word / rule branch              [create, T2]
typescript/test/rt.test.mjs                   catchCb / mark / handledFinally / BOOT      [modify, T1]
typescript/probes/src/swallow.probe.test.ts, escape.probe.test.ts, check.mjs, README.md   [modify/create, T1 written, T2 green]
src/sensorium/ts/build.py                     capabilities from BOOT                      [modify, T3]
tests/test_ts_ingest_caps.py                                                              [create, T3]
docs/trace-format/vectors/v30..v32.json, VECTORS.md                                       [create/modify, T4]; v33 [T5]
docs/TRACE-FORMAT.md, docs/trace-format/TYPESCRIPT-KEYS.md   split (T0), amendment (T3)   [modify]
src/sensorium/query/exceptions_typescript.py  the rules                                   [create, T4]
src/sensorium/query/exceptions_cmd.py         dispatch                                    [modify, T4]
src/sensorium/query/vocab.py                  TYPESCRIPT.exceptions_refusal = None        [modify, T4]
tests/ts_traces.py, tests/test_exceptions_typescript.py (+ _ambiguous.py)                 [create, T4]
src/sensorium/query/exceptions_group.py       Renderer, group_units                       [modify, T5]
src/sensorium/query/exceptions_invocation.py  per-member dispatch                         [modify, T5]
tests/test_exceptions_invocation.py           the TypeScript half                         [modify, T5]
corpus/typescript/<17 cases>/, docs/corpus.md                                             [create/modify, T6]
typescript/acceptance/{census_catch.mjs, e6ts.py, e6tsp.sh, e6tsp_report.py, assemble_rung2.py}  [create, T0/T7]
docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md (+ results, adjudication, transcript)  [T0; filled T7]
tests/test_acceptance_s5_rung2_lock.py                                                    [create, T0]
typescript/HONESTY.md (+ HONESTY-BLIND-SPOTS.md if split), typescript/README.md, README.md, docs/query.md, CHANGELOG.md, docs/CARRIED-DEBT.md (+ ARCHIVE-6), pyproject.toml, wrapper.py:57, the 0.1.1 test/corpus strings  [T8]
```

---

### Task 0: Branch, pre-registration, the contract split, the census instrument, the lock

**Files:**
- Create: the record (P8) — §1 = spec §7's table + the adjudication protocol + the pins above, verbatim by `sed -n` and diffed against `git show db37351:<spec>`; §2 ambient pins; §3 every endpoint `not measured (rung 2 pending)`; §4/§5 headings.
- Create: `tests/test_acceptance_s5_rung2_lock.py` (P8).
- Modify: `docs/TRACE-FORMAT.md` — the `### TypeScript throw flow: exc.kind and how` subsection (lines 613–634 at `db37351`) moves **byte-for-byte** to `docs/trace-format/TYPESCRIPT-KEYS.md` as a new `## Throw flow` section before `## What is deliberately absent`, and a one-line pointer stays in its place (R25's precedent). No other word changes in this task.
- Create: `typescript/acceptance/census_catch.mjs` (P10).

**Invariants:**
- The pre-registration commit precedes every other commit on the branch; the lock test skips BY NAME on `BYTE_LOCK = None`; a second test holds each §1 body to the spec at `db37351`.
- §2 records with commands: node/npm/lens versions, nproc, governor, `free -g`, `df -h` both mounts, loadavg, `git rev-parse HEAD`, `importlib.metadata.version('sensorium')` (0.9.1), the manifest verified (748 OK), suite baselines (pytest ×3 interpreters, npm 167, `check` rc 0, corpus `--only-dir typescript --require-driver` 13/35/0 and `--only-dir .` 20/39/0, live 10, `tests/test_exceptions_*.py` counts).
- The TRACE-FORMAT move is a pure move: `git show db37351:docs/TRACE-FORMAT.md | sed -n '613,634p'` equals the new section's body; TRACE-FORMAT ends under 790.
- `census_catch.mjs <root>` prints `{files, catch_clauses, callback_sites, then_sites, finally_completing, spliced: {how: n}, excluded: {reason: n}, ratio}` and refuses on a `failed` list.

- [ ] **Step 1:** worktree, venvs, npm installs, `mkdir -p /mnt/extra/sensorium-s5/store-rung2ts`; preflight (8 GB free on `/mnt/extra`, 3 GB on `/`, load under 4.0); the manifest verified.
- [ ] **Step 2:** the record; commit ALONE: `docs(s5): pre-register rung 2 (E6-TS, E6-TS′ + protocol, E8″, E2″, E3-TS″, E5″, E7″) before any code`; set `BYTE_LOCK`; the lock test; commit.
- [ ] **Step 3:** the TRACE-FORMAT split; commit: `docs(contract): the TypeScript throw-flow section moves to TYPESCRIPT-KEYS.md, unchanged (R13)`.
- [ ] **Step 4:** `census_catch.mjs` + a probe-project dry run; commit: `test(acceptance): census_catch.mjs — catch sites the transform sees and splices`.

---

### Task 1: The runtime — `catchCb`, the mark, `handledFinally`, the capability; the probes

**Files:**
- Modify: `typescript/src/rt.mjs`, `typescript/test/rt.test.mjs`, `typescript/probes/src/swallow.probe.test.ts`, `typescript/probes/check.mjs`, `typescript/probes/README.md`.

**Interfaces (verbatim):**
```js
/** @typedef {{id: number, task: Task|null, open: boolean, mark: number|null}} Frame */
export function catchCb(f, line, how, fn) {
  if (!on) return fn;
  return /** @this {unknown} */ function sensoriumCatchCb(/** @type {unknown} */ reason) {
    record(f, reason, line, how, 'rejection');
    return fn.call(this, reason);
  };
}
export function mark(f, e) { if (on && f && f.open) f.mark = serialOf(e); }
export function handledFinally(f, line) {
  if (!on || !f || !f.open || f.mark === null) return;
  emitTs({ e: 'HANDLED', f: f.id, t: taskOf(f), x: { kind: 'throw', serial: f.mark, unread: ['type', 'msg'] }, l: line, how: 'sink_finally_return' });
  f.mark = null;
}
```
`raise(f, e, line)` sets `f.mark = serialOf(e)` when `f` is open (after emitting); `handled(f, …)` sets `f.mark = null`; `call()` initialises `mark: null`; `serialOf` is exported from `dbg.mjs` (it is module-private today). `emptyCatch` is deleted. BOOT gains `capabilities: { err_flow: true }` after `tier`. **This task also bumps `sensorium-ts` to 0.2.0** (P14): `typescript/package.json` + `package-lock.json` root entries, `src/index.mjs` `VERSION`, `typescript/test/rt.test.mjs:63`, `src/sensorium/ts/wrapper.py:57`, `tests/test_ts_live.py:200`, `tests/test_ts_wrapper.py:84`, and the four corpus questions naming `sensorium-ts 0.1.1` (`corpus/typescript/{watch_refused,pass_vs_fail,object_refused}/questions.yaml`, five lines) — NOT the fixtures' `0.1.0`. The `exc` object with `unread` is the contract's own spelling (TRACE-FORMAT §5: `unread: ["msg"]` inside `exc`), extended to `type`; `fmt_exc` already renders an unread `msg` on a kind-bearing exc — Task 4 checks `type` renders too.

**Tests (`rt.test.mjs`):** `catchCb` records HANDLED `{kind: 'rejection', how}` with the reason's serial and returns the original's result with `this` preserved; `catchCb` at tier `off` returns `fn` itself; `mark`+`handledFinally` write one `sink_finally_return` carrying the marked serial and clear the mark; `handledFinally` with no mark writes nothing; `raise` marks and `handled` clears (a `finally` after a caught throw records nothing); BOOT carries `capabilities.err_flow: true`; `VERSION` held to `package.json` at 0.2.0.

**Probes (they run only once Task 2's transform emits the new records; written here, asserted at Task 2's end):** `swallow.probe.test.ts` gains shapes 6–12 with markers (`logged catch`, `escaped catch`, `callback function empty`, `callback arrow logged`, `callback escaped`, `callback opaque`, `finally return`); `check.mjs`: `SWALLOW_EXC` rows for each, and a new `checkEscape(k, s)` reading `// ESCAPE` markers from `escape.probe.test.ts` and asserting the HANDLED `how` at the marked line; `VITEST_PROBES` gains the file; the README table gains both.

- [ ] **Step 1:** the rt tests (RED); the runtime; GREEN; `npm test`, `run check`.
- [ ] **Step 2:** probes + checker written (the new checks fail until Task 2 lands the transform — state that in the report; the existing probe run stays green).
- [ ] **Step 3:** commits: `feat(rt): catchCb, the in-flight mark and the finally sink; the recorder declares err_flow`; `test(probes): the escape and swallow shapes, one marker each`.

---

### Task 2: The transform — the escape rule, rejection callbacks, the `finally` sink

**Files:**
- Create: `typescript/src/escape.mjs`, `typescript/test/escape.test.mjs`, goldens.
- Modify: `typescript/src/transform.mjs` (`spliceCatch`, replace `spliceEmptyCatchCallback` with `spliceRejectionCallback`, add `spliceFinally`, the visitor), `typescript/test/transform.test.mjs` (golden count floor), `typescript/probes/src/escape.probe.test.ts` (create).

**Interfaces (verbatim where the splice would be guessed wrong):**

- `escape.mjs`:
  ```js
  export const LOGGING = new Set(['log', 'error', 'warn', 'info', 'debug', 'trace']);
  /** @returns {'catch'|'catch_escaped'|'sink_empty_catch'} */
  export function catchHow(ts, clause) { … }
  /** @returns {'sink_empty_catch_callback'|'catch_callback'|'catch_callback_escaped'|'catch_callback_opaque'} */
  export function callbackHow(ts, arg) { … }
  /** @returns {boolean} the block contains return/break/continue at closure depth 0 */
  export function finallyCompletes(ts, block) { … }
  ```
  `catchHow`: empty block → `sink_empty_catch`; no binding → `catch`; a destructuring binding → `catch_escaped`; otherwise walk the block: a mention of the binding's name is **logged** iff its nearest enclosing `CallExpression` — with no function boundary in between — has callee `console.<LOGGING member>` and the mention lies inside that call's arguments (a template literal, a `String(e)`, a property access `e.message` inside those arguments all count as logged); any other mention (including any inside a nested function body, and a shorthand property `{ e }`) escapes; a `throw` statement's operand mentioning `e` escapes (the RAISE carries the identity; the escape marks the clause). Shadowing is not resolved: any identifier with the binding's text counts.
  `callbackHow`: not an arrow/function expression → `catch_callback_opaque`; body an empty block → `sink_empty_catch_callback`; no parameter → `catch_callback`; a single identifier parameter → `catchHow`'s walk over the body with that name (`catch_callback` / `catch_callback_escaped`); a destructuring parameter → `catch_callback_escaped`; an expression body (`(e) => log(e)`) is walked as a one-expression block.
- `transform.mjs`:
  - `spliceCatch` calls `catchHow` for `how` (the empty-block check moves into it).
  - `spliceRejectionCallback(ctx, node)`: callee `.catch` with exactly one argument, or `.then` with exactly two; the target argument `arg`; `line = lineOf(sf, callee.name.getStart(sf))`; splice `s.appendLeft(arg.getStart(sf), `__srt.catchCb(${frameVar(ctx, node)},${line},"${how}",(`)` and `s.prependRight(arg.end, '))')`. Returns true when spliced. Replaces `spliceEmptyCatchCallback` in the visitor.
  - `spliceFinally(ctx, node)` for a `TryStatement` whose `finallyBlock` satisfies `finallyCompletes`: if `node.catchClause` is undefined, insert **before the `finally` keyword** `catch(__sfe){__srt.mark(${frameVar},__sfe);throw __sfe}` (one `appendLeft` at the `finally` keyword's start); then insert as the finally block's first statement `__srt.handledFinally(${frameVar},${line});` where `line = lineOf(sf, finally keyword)`. A `try` outside any recorded frame (`frameVar` null) is left alone.
  - Visitor: `else if (ts.isTryStatement(node)) spliceFinally(ctx, node);` before the catch-clause arm; `ts.forEachChild` still descends.
- Goldens (`typescript/test/golden/`, `.ts` + `.expected.ts`): `catch-logged`, `catch-escaped-return`, `catch-escaped-expect`, `catch-escaped-closure`, `catch-no-binding`, `catch-destructuring`, `callback-arrow-logged`, `callback-arrow-escaped`, `callback-function-empty`, `callback-opaque`, `then-onrejected`, `finally-return`, `finally-plain`, `finally-with-catch`. The golden floor in `transform.test.mjs` rises from 13 to 27.
- `escape.test.mjs`: one test per row of the rule table above (mention positions: bare argument, template literal, `String(e)`, `e.message` inside `console.*`; outside: `return`, assignment, push, non-console call, nested function, shorthand property, throw operand; the destructuring and no-binding branches; `callbackHow`'s five outcomes; `finallyCompletes` on return/break/continue/none/nested-function-return).
- `escape.probe.test.ts`: one clause or callback per branch with a `// ESCAPE <id> <how>` marker naming the expected `how`; Task 1 wrote the checker's `checkEscape`; this task makes every probe check pass.

**Invariants:** `lines(out) === lines(in)` on every golden; `npm --prefix typescript run check` clean; a mutation dropping `'error'` from `LOGGING` flips `catch-logged`.

- [ ] **Step 1:** `escape.test.mjs` + the goldens' inputs and expected outputs (RED: module missing).
- [ ] **Step 2:** `escape.mjs`; the transform changes; GREEN; `npm test` + `run check`; the probe file; `SENSORIUM_PROBE_DIRECT=1 npm run probe` from `typescript/probes` with a scratch spool/manifest dir → `ok` (every Task-1 check now passes).
- [ ] **Step 3:** commits: `feat(transform): the catch-binding escape rule (R2 transferred) in escape.mjs`; `feat(transform): rejection callbacks of every shape and a completing finally are recorded`.

---

### Task 3: The converter and the contract's amendment

**Files:**
- Modify: `src/sensorium/ts/build.py` (`_meta`: `capabilities = {**CAPABILITIES, **(boot.get("capabilities") or {})}`; nothing else), `docs/trace-format/TYPESCRIPT-KEYS.md` (the moved section amended: the nine `how` words, the `unread: ["type","msg"]` exc, the capability, "judged by the TypeScript rules from `sensorium-ts` 0.2.0"), `docs/TRACE-FORMAT.md` capabilities row for `err_flow` (one line: "Rust and TypeScript; the Python column never declares it"), `docs/trace-format/VECTORS.md`.
- Create: `tests/test_ts_ingest_caps.py` (P12): a spool whose BOOT carries `capabilities: {err_flow: true}` converts to `meta.capabilities.err_flow == True` with every other key the constant's; a spool without the map converts to the constant (the ten fixtures — `test_the_declaration_is_this_recorders_own` keeps passing unchanged); a BOOT `capabilities` that is not a dict is a `SpoolError` naming the file.
- The vectors are NOT this task's: `tests/test_vectors.py` runs every vector, so v30–v32 land with the rules (Task 4) and v33 with the invocation mode (Task 5), in v25's layout with `recorder: "sensorium-ts 0.2.0"` (v32: `0.1.1`, `err_flow: false`).

**Invariants:** `TRACE-FORMAT.md` stays under 800; the ten fixture traces still declare `err_flow: false`; the full suite green at this task's end.

- [ ] **Step 1:** the caps test (RED); `build.py`; GREEN; full suite.
- [ ] **Step 2:** the contract amendment.
- [ ] **Step 3:** commits: `feat(ingest): the recorder's own capabilities ride the BOOT record`; `docs(contract): the TypeScript throw-flow words and the capability`.

---

### Task 4: The rules module

**Files:**
- Create: `src/sensorium/query/exceptions_typescript.py`, `tests/ts_traces.py` (synthetic TypeScript traces: `ts_trace(tmp_path, monkeypatch, codes, frames, events, **meta)` over `tests.helpers.finalize_synthetic` with `TS_META`/`TS_CAPABILITIES`, `ts_exc(type_, msg, serial, kind="throw", unread=None)`, `raise_ev`, `handled_ev`, `frame(..., unwind_exc=)`, `task(id, name)`), `tests/test_exceptions_typescript.py`, `tests/test_exceptions_typescript_ambiguous.py`.
- Modify: `src/sensorium/query/exceptions_cmd.py` (`run`: `if trace.lang == "typescript": from sensorium.query import exceptions_typescript; return exceptions_typescript.run(trace, args, after)` beside the Rust arm), `src/sensorium/query/vocab.py` (`TYPESCRIPT.exceptions_refusal=None`, the comment updated), `tests/test_vocab.py`/`tests/test_vectors.py` expectations that pinned the old refusal (v23 re-pinned to the capability sentence).

**Interfaces:**
- `TAG_ORDER = ("swallowed", "uncaught", "re-raised", "propagated", "ambiguous")`.
- `ABSORBING = {"catch", "sink_empty_catch", "catch_callback", "sink_empty_catch_callback", "sink_finally_return"}`; `ESCAPING = {"catch_escaped", "catch_callback_escaped", "catch_callback_opaque"}`.
- `class Raise` (P6): `origin` (a RAISE event, or the orphan HANDLED), `serial`, `raises` (every RAISE with the serial, id order), `handled` (every HANDLED with the serial), `orphan: bool`, `primitive: bool` (the origin's exc `type` is a primitive typeof — `string`, `number`, `boolean`, `undefined`, `symbol`, `bigint` — or `object` with `msg` `null`).
- `class Index(trace)`: `units: list[Raise]` in origin order; `frame_of(e)`; `task_root(frame)` → the frame with `parent_id None` walking up; `rejections: dict[serial → entry]` from `meta.unhandled_rejections`; `incomplete`. Primitive pairing (spec §3.1): a primitive RAISE's `handled` is the next HANDLED in the same frame with equal `type` and `msg` and no RAISE between; a primitive rethrow (a second primitive RAISE with equal text in a window) makes the unit `primitive_rethrown`.
- `classify(trace, unit, idx) -> Disposition`, spec §3.3's five rules in order, verbatim wording:
  1. `uncaught`: `UNCAUGHT -- unhandled rejection; raised at <at>` / `UNCAUGHT -- unhandled rejection; born outside traced code (a reject() or a library)`.
  2. `re-raised`: `RE-RAISED -- raised again at e<id> (<at>) → <last raise's tag>` with detail `hops: <at> → <at> → …`; the later raises are their own units and get their own blocks.
  3. `swallowed`: `SWALLOWED -- caught by <how> at e<id> (<at>) in f<id>, which returned`; detail `born outside traced code, at <at>` / `born outside a throw statement (a reject())` for an orphan; `site` = the HANDLED's `(file, line, qualname)`.
  4. `propagated`: `PROPAGATED -- to the harness: test "<name>" failed` / `PROPAGATED -- handler not in traced code`; `site` None.
  5. `ambiguous`, each with its reason: `AMBIGUOUS -- caught at e<id> (<how>), and the error or a rendering of it left the handler; not followed` (site = the handler's); `… -- the handler's frame f<id> is still suspended at the end of the recording`; `… -- handler's frame f<id> later unwound with <X>: a translation or a later failure, indistinguishable`; `… -- a primitive has no identity across a rethrow`; `… -- this recording never finalized (INCOMPLETE)`; and the fall-through `… -- no rule of this recorder reaches a verdict here`.
- `run(trace, args, after)`: `caps.require(trace, "err_flow", "exceptions")` first (→ `REFUSED: …`, exit 3); the header (`INCOMPLETE` line as Python's; `unhandled rejections: N` when non-zero); `no exceptions recorded` → `caps.none_status`; `raised (N):`; one block per unit printed the way `exceptions_cmd.run` prints Python's (head line, verdict, detail, hops) — Task 5 switches this to `group_units` with `RENDER = Renderer(at=_at, hops_line=_hops_line, site=_site, site_text=site_text, site_file=site_file, tag_order=TAG_ORDER)`, so nothing here imports `exceptions_group` yet; the tally in `TAG_ORDER`; paging as the Rust module's.

**Tests** (one per rule and per reason, each named for the behaviour): a catch sink in a returning frame → SWALLOWED; a logged catch (`how: catch`) → SWALLOWED; an escaped catch → AMBIGUOUS never SWALLOWED even when the frame returned; an absorbing HANDLED plus an escaping HANDLED for one serial → AMBIGUOUS; a rethrow → two blocks, origin RE-RAISED with hops, rethrow judged on its own; an orphan sink → SWALLOWED born outside; a task-root unwind → PROPAGATED to the harness naming the test; a parentless-frame unwind → handler not in traced code; a serial in `unhandled_rejections` → UNCAUGHT; a handler frame suspended → AMBIGUOUS; a handler frame unwound with another serial → AMBIGUOUS; a primitive rethrow → AMBIGUOUS; a `sink_finally_return` HANDLED with the marked serial → SWALLOWED; an incomplete trace → the INCOMPLETE line and `no RAISE events recorded` at exit 3 when empty; the capability gate on a 0.1.x-shaped trace → the capability sentence, exit 3; the tally order; `--after`/`--limit`; no Python/Rust word in any sentence (a needle test over every verdict string in the module).

**Mutation checks:** drop `sink_finally_return` from `ABSORBING` → the finally test fails; drop the ESCAPING conjunction → the two-handler test fails; swap rule order 3/4 → the harness test fails.

- [ ] **Step 1:** `ts_traces.py`; the tests (RED).
- [ ] **Step 2:** the module; the dispatch; the vocab change and re-pins; the vectors `v30-exceptions-typescript-swallowed`, `v31-exceptions-typescript-escaped-ambiguous`, `v32-err-flow-typescript-capability-refusal` + their `VECTORS.md` rows; GREEN; full suite.
- [ ] **Step 3:** commits: `feat(exceptions): the TypeScript disposition rules — Python's five words over serial identity`; `test(exceptions): every rule and every ambiguous reason on synthetic TypeScript traces`.

---

### Task 5: The invocation mode and the grouper

**Files:**
- Modify: `src/sensorium/query/exceptions_group.py` (P5: `Renderer`, `group_units`, `group_chains` wrapper; `print_shape`/`bracket`/`vary_lines` take the renderer from the shape's `render` field), `src/sensorium/query/exceptions_invocation.py` (`_member_refusal`: language in `("rust", "typescript")` else the sentence; `_index_for(trace)` / `_classify_for` / `_render_for` / `_tag_order_for` by lang; `_header` prints `with Err chains` for Rust and `with throws` for TypeScript, `raised (N raises over M processes, K swallowed shapes):` for TypeScript; the panic line only for Rust; the tally in the members' language's order — a mixed-language invocation is impossible and refused by name), `tests/test_exceptions_invocation.py` (a TypeScript half: two members, one swallowed shape merged with `[×2 over 2 processes: …]`, an INCOMPLETE member named first, an `err_flow: false` member refusing the whole answer, `--after` refused), `tests/test_exceptions_typescript.py` (the per-trace grouping: a loop raising one error fifty times prints one block with `[×50: …]` and a tally of 50); the vector `v33-exceptions-typescript-invocation-shape` (two copies, `copies: 2`, sharing `invocation`) + its `VECTORS.md` row.

**Invariants:** every existing Rust invocation/group test byte-unchanged; the Rust and TypeScript shape keys can never collide (`lang` is not in the key because a member set is one language).

- [ ] **Step 1:** tests (RED); the grouper generalisation; the invocation dispatch; GREEN; the whole `test_exceptions_*` set + `test_vectors`.
- [ ] **Step 2:** commit: `feat(exceptions): the invocation mode dispatches per member language; one grouper, two renderers`.

---

### Task 6: The swallow corpus

**Files:**
- `git mv corpus/typescript/exceptions_refused corpus/typescript/silent_swallow`; new questions (`what-happened-to-the-parse-error` → `SWALLOWED -- caught by catch at … (loadConfig L…) in f…, which returned`, tally `swallowed 1`, exit 0; the `info` question's `err_flow=yes` and `recorder: sensorium-ts 0.2.0`; the `tree` question unchanged modulo event ids).
- Create the sixteen other cases of spec §6.1's table, each `<case>/<case>.test.ts` (+ a source module where the shape needs one) and `questions.yaml` with `program: vitest`, `harness_args: ["run", "<case>"]`, an `exceptions` question with `expect_line` pinning the verdict line and the `dispositions:` line, `why_logs_fail` naming `console.log`, `DEBUG` and `stack trace` (the guard in `tests/test_corpus.py`). `test_failed` is a red suite by design: its `record` expects exit 1 (the `pass_vs_fail` precedent). `suspended_handler` uses the `never_settles` shape inside a `try/catch`.
- Modify: `corpus/typescript/suspended_at_end/questions.yaml` and `silent_swallow/questions.yaml` event-id re-pins with the reason per question; `docs/corpus.md`'s TypeScript roll-call (seventeen new paragraphs — measure the file; it is at 87 lines).

**Invariants:** `python corpus/run_corpus.py --only-dir typescript --require-driver` → 29 cases, every question green; each case's SWALLOWED set is what §6.1 pins; `E6-TS`'s collector (Task 7) reads these same questions.

- [ ] **Step 1:** the cases; the questions; the corpus run; the roll-call.
- [ ] **Step 2:** commit: `test(corpus): the TypeScript swallow corpus — seventeen shapes, one verdict each`.

---

### Task 7: Acceptance — every endpoint, the adjudication

**Files:**
- Create: `typescript/acceptance/e6ts.py` (the corpus collector: runs every TypeScript case's `exceptions` question through `run_corpus`'s machinery, compares the printed SWALLOWED lines per case to the pre-registered set as EQUALITY, the tallies whole; JSON cell `{value: cases equal, n: cases, lens, dropped, per_case}`), `typescript/acceptance/e6tsp.sh <lens> <store> <out>` (manifest before; guard; one call-tier full-suite run through the worktree's `.venv/bin/sensorium`; `exceptions <invocation> --limit 10000` transcript to `<out>/e6tsp-exceptions.txt`; manifest after; markers; wrapper), `typescript/acceptance/e6tsp_report.py` (parses the transcript: shapes by disposition, the SWALLOWED shapes as rows `{shape, site, how, ids}` for the adjudication table, the escaped-ambiguous count, the tally; JSON cell with `value: null` until the adjudication file is filled and then `value: false accusations`), `typescript/acceptance/assemble_rung2.py` (P8; the same redaction refusal as `assemble_slice2.py`).
- Reuse unchanged: `census_catch.mjs` (E2″), `e3.sh` (E3-TS″), `e7.sh` with the needle list from §1 (E7″), `arms.sh` (E1‴), `e10p.sh` (E10″), `check.mjs` via `npm run probe` (E8″; the JSON captured to `results/e8pp.json` with its revs, the slice-2 lesson).
- Modify: the record §2 (pins re-taken), §3 (every cell), §4 (verdicts with the rules quoted), §5 (gaps); the adjudication file `…-e6tsp-adjudication.md` (P9).

**Order (the timed and lens-touching arms last):** E8″ (probes, no lens) → E2″ (census, reads the lens, writes nothing) → E6-TS (corpus) → E3-TS″ (20 recordings) → E5″ (the full suite once under the driver: the E6-TS′ run doubles as it) → E6-TS′ (the invocation `exceptions`, then the adjudication, every line, before any number is written into §3) → E7″ (the transcripts) → E1‴ (five interleaved batches) → E10″ (over the E6-TS′ spool set) → manifest after everything.

**The adjudication:** every SWALLOWED shape row is read against the VTT source at its site; §7's protocol decides TRUE/FALSE; the count of FALSE is the gate; a row the adjudicator cannot decide from the source is FALSE; the table is committed whole. If FALSE > 0: STOP, the rung ships DONE-WITH-STOP, no re-roll, the amendment slice is named in §4.

- [ ] **Step 1:** the four new instruments; dry runs on `typescript/probes` / the corpus; commit: `test(acceptance): the rung-2 instruments — corpus equality, the lens sweep, the adjudication table, the assembler`.
- [ ] **Step 2:** the endpoints in order; the adjudication; §3/§4/§5; the results file; commit: `test(acceptance): S5 rung 2 measured — <verdicts>`.

---

### Task 8: Documents, versions, the ledger

**Files:**
- `typescript/HONESTY.md` §4 rewritten by dated amendment (the promise, the nine words, the escape rule, the absorbing/escaping sets, what still records nothing), blind spots 2/3/11/13 struck or amended, new blind spots (P1's, R3's, closures, the `finally` sink's unread value, opaque handlers, `Promise.reject` origins), §9 "Measured, rung 2" (E1‴/E10″ numbers, the tally on the lens, the escaped share); split §10 to `HONESTY-BLIND-SPOTS.md` if over 800.
- `typescript/README.md` (the hook/plugin rows; `exceptions` answers), `README.md` (`sensorium-ts 0.1.1` → `0.2.0`, one token; the TypeScript paragraph's "`exceptions` refuse at exit 3" clause → "answer"), `docs/query.md` (a TypeScript paragraph under `exceptions`: the five words, the escape rule, the `[×N]` grouping, the invocation mode; the "refuses" sentence in v23's description updated).
- `CHANGELOG.md` `## 0.10.0 — <date>` (637 + ~90 lines, no cut); `pyproject.toml` 0.10.0 (the `sensorium-ts` 0.2.0 sites were Task 1's, P14); NOT the fixtures' `0.1.0` (`tests/test_ts_ingest_meta.py:31`).
- `docs/CARRIED-DEBT.md`: measure; cut the oldest section to `docs/CARRIED-DEBT-ARCHIVE-6.md` with the dated note; append the rung-2 section (settled: blind spots 2/3/11/13, the refusal, D15; deferred with rulings from the SDD ledger's `Ruling:` lines and every deferred minor; process lessons); strike rung 1's "`exceptions` disposition rules are rung 2" row and the R46 residual list's throw-flow items.
- The rung-1 spec's §11 item 2 gains a dated line pointing at the record; this spec's §12 = "what changed against this design" (P1–P12, the measured numbers, the predictions that did not hold).
- Reinstall the three worktree venvs so `importlib.metadata` reads 0.10.0; `tests/test_release_tokens.py` green.

- [ ] **Step 1:** `pyproject.toml` 0.10.0 + reinstall + `test_release_tokens`; commit `chore(release): sensorium 0.10.0`.
- [ ] **Step 2:** HONESTY, READMEs, query.md, CHANGELOG, the ledger, the spec pointers; every suite once more on 3.12/3.13/3.14 + npm + corpus + live; commit `docs: HONESTY, READMEs, query.md, CHANGELOG and the ledger for rung 2`.

---

### Task 9: Final review, one fix wave, the PR

- [ ] **Step 1:** superpowers:requesting-code-review over the whole branch (fable); Critical/Important fixed in ONE wave; minors ledgered with rulings.
- [ ] **Step 2:** the lock test, every suite, the corpus, the live suite on the tip; `git push -u origin feat/s5-rung2`; `gh pr create` with the verdicts as measured; CI green; merge is Brice's.
- [ ] **Step 3:** archive the SDD ledger; after the merge: worktree removed, branch deleted local+remote, origin sync verified, the global tool reinstalled from the main checkout.

---

## Self-review against the spec

- **§2.1–§2.5** → Task 2 (escape rule, callbacks, `finally`), Task 1 (runtime + capability), §2.5's "still nothing" list → HONESTY in Task 8. **§3** → Task 4 (identity §3.1, index §3.2, classifier §3.3 rule by rule, printing §3.4, exits §3.5). **§4** → Task 5 (dispatch §4.1, shape key §4.2 via P5/P6, header §4.3). **§5** → Task 3 (pass-through §5.1, contract §5.2 after Task 0's split, vectors §5.3). **§6** → Task 6 (corpus §6.1), Tasks 1–2 (probes §6.2), Task 8 (ledger §6.3). **§7** → Task 0 (locked) + Task 7 (measured), the adjudication protocol carried verbatim. **§8** testing → each task's tests and mutation checks. **§9** order → Tasks 0–9. **§10** → Task 8 and the Global Constraints' ceilings. **§11/§12** → Task 8's ledger and the PR body.
- **Placeholders:** none — every splice, signature, sentence and instrument shape is written.
- **Type consistency:** `catchCb(f, line, how, fn)` (T2 emits, T1 defines); `mark(f, e)` / `handledFinally(f, line)` (T2 emits, T1 defines); `escape.mjs`'s three exports (T2 both sides); `Raise`/`Index`/`classify` (T4 defines, T5 consumes); `Renderer`/`group_units`/`RENDER` (T5 defines and wires into T4's `run`); `capabilities` from BOOT (T1 writes, T3 reads); the record/results names (P8) in Tasks 0 and 7.
