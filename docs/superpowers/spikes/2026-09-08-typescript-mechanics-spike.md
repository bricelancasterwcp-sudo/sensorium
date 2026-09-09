# TypeScript mechanics spike — findings (throwaway code, pre-registered)

**Status: PRE-REGISTERED, not yet run.** Sections 1 and 2 are locked by
the commit that adds this file; sections 3 and 4 are filled by the run and
never edit the two above them (errata are appended, dated, below the
table they correct — the Rust spike's rule, kept).

**Program:** S5 of the sensor-suite program (plan
`~/.claude/plans/if-you-were-to-lexical-clover.md`, S5 section as rewritten
2026-09-08 when C/C++ was dropped). **Consumer ruling (Brice, 2026-09-08,
by approving this pre-registration as presented):** the VTT frontend,
Node first — under vitest and jsdom that IS the Node substrate; the browser
proper is the second rung. **Branch:** `spike/typescript-mechanics`; the
code under `spike/typescript/` is throwaway and is not merged. **Precedent:**
`2026-09-02-rust-mechanics-spike.md`, whose shape this follows on purpose
so the two records read side by side.

## 1. Pre-registration

**Question.** Can a compile-time source transform plus a small runtime
record a TypeScript program under vitest into sensorium's trace format
(format 4, `lang: "typescript"`) with the honesty the Rust recorder has —
and what is the trace unit, what is the async model, and what does it
cost?

**Lens for every endpoint.** The VTT frontend at commit
`0091e97d695d3c71748a465301e00d159fea4e6c` (branch `feat/pixi-v12-fog` in
the live repo, which is NOT touched: another session owns it and it has
one untracked file), rsync'd without `.git` to
`/mnt/extra/sensorium-s5/vtt/` together with the root `node_modules`, the
root `package.json`/`package-lock.json`, `docs/superpowers/specs/` and
`backend/app/systems/pf2e/data/` (three suites read data from those two
repo-root paths and fail without them — §2). `vitest run` as the repo
configures it (`environment: 'jsdom'`, `globals: true`,
`setupFiles: ['./src/test-setup.ts']`, default pool), Node 24.16.0,
vitest 4.1.9, vite 6.4.3, typescript 5.9.3, this box (16 threads,
`powersave`). Trace store `SENSORIUM_DIR=/mnt/extra/sensorium-s5/store`.
Nothing runs against the root disk.

| Id | Question | Measurement | Decision rule | Derivation of the threshold |
|---|---|---|---|---|
| E0 | What is one execution container under `vitest run`, and can a test file's events be told apart? | The spike runtime records, at every module boot, `(pid, ppid, worker_threads.threadId, isMainThread)` and the first test file it sees; run a 1-file invocation and the full 372-file invocation; count distinct `(pid, threadId)` containers, files per container, and whether each container's spool is separate. | Trace unit = the smallest container whose events spool apart. (a) container = child process → one trace per worker PROCESS, test files as tasks; (b) container = worker thread in one process → one trace per process, threads witnessed, files as tasks; (c) files cannot be told apart inside a container → per-file identity is NO-GO and the unit is the invocation. Which of (a)/(b)/(c) holds is the finding; only (c) is a NO-GO. | Rust E0: one test binary is the unit and libtest tests are tasks; a vitest worker is the analogue if and only if its events can be spooled apart from its siblings'. |
| E1 | Does the transform cost little enough to run on every invocation, and what does the call tier cost? | Wall clock of `vitest run` (full suite, green at 372/4278), n=5 per arm, arms: **plain** (no plugin), **off** (transform applied, probes compiled in, emission gated off at runtime), **call** (CALL/RETURN/YIELD/RESUME/RAISE/HANDLED emitted to the spool). Median and spread per arm; vitest's own `Duration` breakdown (transform/setup/import/tests/environment) recorded per arm. | **off ≤ 1.10 × plain** (medians) → the transform can run on every invocation and the tier is a runtime gate, as in Rust. Above it, the finding is "the transform must be cached or the tier compiled", a design input, not a NO-GO. **call** is reported beside Python's 2.7× and Rust's ×2.16 with no gate. An arm whose suite is not 372/4278 is infrastructure-invalid: `value: null`, `dropped` names the arm. | 1.10 is Rust E1's off-arm bound, reused unchanged. Sanity check against noise: three plain walls before any code exist read 22.31 / 22.17 / 22.22 s (§2), a spread of 0.14 s = 0.6%; the 10% bound sits ≈15× outside it. |
| E2 | Does the transform cover the frontend? | A census over `frontend/src/**/*.{ts,tsx}` minus `*.test.*`, `*.d.ts`, `test-setup.ts`: **eligible** = every FunctionDeclaration, FunctionExpression, ArrowFunction, MethodDeclaration, Constructor, GetAccessor, SetAccessor, including `async` and generator forms and JSX-returning components; **instrumented** = sites the transform wrapped, read from the transform's own per-file manifest. Ratio, plus a table of every excluded node kind with its count and reason. | **≥ 95%**, AND every excluded kind named with a written reason, AND no excluded kind above 1% of eligible without a reason that a rung-1 design can act on. | Chosen, marked for sanity: Rust reached 99.3% by rule (5 `const fn` of 756). JavaScript has more function shapes (object-literal accessors, class-field arrows, IIFEs, `new Function`), so 5% is reserved for NAMED exclusions; the 1%-per-kind clause keeps the floor from hiding one large class behind the aggregate (§2 of `rigorous-experiments`: aggregates hide compensating drifts). |
| E3 | **The rung-0 question: async attribution.** After an `await`, a timer, a `Promise.all` fan-out and an emitter callback, is every row attributed to the task that started it, and is the causal order right? | The probe file in §1.1 (four scenarios and one negative control), run under vitest in BOTH `node` and `jsdom` environments (the per-file `@vitest-environment` pragma; two copies of the file). Compare the recorded `(kind, qualname, task)` rows in order against the expected table in §1.1, per scenario. | **100% of expected rows present, in the expected order, with the expected task, in both environments; and the negative control shows ZERO rows of T2 attributed to T1.** Anything less means a continuation escaped its task; the async model is then wrong and rung 1 cannot start on it. | Attribution is binary per row and the probe is small enough to enumerate, so the only honest threshold is all of them. The negative control is the shape check §1 of `rigorous-experiments` asks for: four passing scenarios could still license a model that attributes EVERYTHING to the first task. |
| E4 | Do sites survive transpilation and bundling? | The site probe in §1.3: 20 CALL sites whose TypeScript line numbers are written down here; compare each recorded `line` with the source line; run twice and compare recorded `file` paths. Plus one deliberately failing assertion in an instrumented run: the line vitest reports must equal the TS line it reports in the plain run (source-map chain intact). | **≥ 19 of 20 sites on the exact TS line** (one off-by-one is reported, not hidden — Rust E7 was binary and this leaves room to record a systematic shift); paths repo-relative (`frontend/src/…`) and byte-identical across the two runs; the failing assertion's reported line unchanged. | 20 sites, one allowed miss, so a single boundary case (a multi-line arrow, a decorator) can be seen without failing the endpoint; a shift of 2+ is a pattern and fails. |
| E5 | Which harnesses work? | The §1.1 probe under (i) vitest via a Vite plugin (the consumer's harness) and (ii) `node --test` via a `module.register` loader hook. Pass = the probe's tests pass AND its expected rows are produced. | (i) is a gate: **vitest must pass**, or the consumer cannot be recorded and the spike is NO-GO on mechanics. (ii) is reported. jest is not measured: VTT does not use it, and a harness the consumer does not run is not this spike's question. | The consumer decides the gate (plan §S5: "needs a consumer before rung 0"). |
| E6 | Is a plain run contaminated afterwards? | Before any instrumented run: `sha256sum` manifest of every file under `frontend/src`, `frontend/vite.config.ts`, `frontend/package.json`, and a listing of `frontend/node_modules/.vite*` / `.vitest*` cache dirs. After ALL instrumented runs: the same manifest; then one plain `vitest run` (372/4278 expected, wall inside the plain band of E1); then a grep of every cache dir for the runtime's marker identifier. | **Manifest identical, plain counts identical, marker absent from every cache** → GO. Any difference → NO-GO until fixed and re-measured from zero (Rust E8). | Rust E8: a plain build must never carry the instrumented one. Same rule, same binary outcome. |
| E7 | What does today's reader do with a `lang: "typescript"` trace? | Convert the §1.1 probe's spool into a format-4 SQLite trace with `lang: "typescript"`, `recorder: "sensorium-ts 0.0.0-spike"` and a truthful `capabilities` declaration; run `sensorium info`, `tree`, `frame`, `grep`, `exceptions`, `watch`, `flow`, `refocus` against it and record every line verbatim, with exit statuses. | **Reported, not gated.** The finding is which sentences narrate in Python's words (`vocab.terms()` falls back to `PYTHON` for a `lang` neither table knows — `src/sensorium/query/vocab.py:31`), which commands refuse, and which answer correctly; it decides whether rung 1 must add a `TYPESCRIPT` vocabulary and a refusal for unknown `lang`. | A design input. Gating it would gate the spike on the reader, which is not the spike's subject. |
| E8 | Which swallow shapes does the transform plus runtime see? | The probe in §1.2: five shapes, each with its expected `(kind, site)` rows. Count shapes fully seen. | **Reported, 0–5 of 5; scopes rung 2.** A shape not seen is written into the TypeScript HONESTY ledger's first draft as a blind spot, never silently. | Rust rung 3 shipped err-flow after the spike; the same order. |

**Reported without a gate:** events per second of recording and bytes
per event on disk (call arm); the number of worker containers vitest used
and their kind; jsdom-vs-node differences in E3 beyond the pass/fail;
transform output size ÷ input size over the census set; the wall of the
converter; what `bun test` does with the loader hook (one run, curiosity
only — bun 1.3.14 is on the box, not in the consumer's toolchain).

**Stop rules.** A 1-minute load above 4.0 before a timed arm → wait, do
not measure. A timed arm with fewer than 5 completed runs reports
`value: null` with the reason in `dropped`. Any arm whose suite is not
372/4278 is infrastructure, never a number. No endpoint is re-run after
its number is read; an externally killed run with no number read may be
rerun from zero.

**Decisions this spike settles**, written into §4 and carried into the
S5 design spec: (1) the trace unit under vitest (E0); (2) runtime gate
versus compiled tier (E1); (3) GO / NO-GO on mechanics (E2, E4, E5-vitest,
E6); (4) the async model rung 1 builds on (E3); (5) what the reader must
learn in rung 1 (E7); (6) the scope of the err-flow rung (E8).

**`results.json` schema (none-versus-zero):** every measurement is
`{"value": <number|null>, "n": <int>, "lens": <string>, "dropped": [<reason>…]}`;
a `null` value with a non-empty `dropped` list is the only way to say
"not measured", and `0` is only ever a measured zero.

### 1.1 The E3 async probe and its expected rows

One file, `spike/typescript/probes/async.probe.test.ts`, copied once with
`// @vitest-environment node` and once with `// @vitest-environment jsdom`.
Each vitest `test()` callback boundary opens a **task** (the runtime's
AsyncLocalStorage store, named by the test title) — the analogue of
libtest's per-test thread and asyncio's task. Rows below are
`(kind, qualname)`; every row's task is the scenario's own unless stated.
`YIELD` is emitted immediately before an `await` parks the frame; `RESUME`
immediately after it continues. Rows the probe file's own harness code
would add (the `test()` callback itself) are not listed and not counted.

**S1 — an await chain** (`a` awaits `b`, `b` awaits `c`, `c` awaits
`Promise.resolve()` and returns `2`, `b` returns `c + 1`, `a` returns
`b + 1`):

```
CALL a · CALL b · CALL c · YIELD c · YIELD b · YIELD a ·
RESUME c · RETURN c=2 · RESUME b · RETURN b=3 · RESUME a · RETURN a=4
```

**S2 — a fan-out** (`fanout` awaits `Promise.all([p(1), p(2)])`; `p(n)`
awaits a 1 ms timer and returns `n * 10`):

```
CALL fanout · CALL p · YIELD p · CALL p · YIELD p · YIELD fanout ·
RESUME p · RETURN p=10 · RESUME p · RETURN p=20 · RESUME fanout · RETURN fanout=[10,20]
```
(the two `RESUME p` rows may come in either order — timers of equal delay
are not ordered by the spec; the rule is "both present, each after its own
YIELD, both before `RESUME fanout`").

**S3 — a timer continuation** (`viaTimer` returns a promise resolved from a
`setTimeout(() => resolve(work()), 0)` callback; `work` returns `7`):

```
CALL viaTimer · YIELD viaTimer · CALL work · RETURN work=7 · RESUME viaTimer · RETURN viaTimer=7
```
`CALL work` MUST carry S3's task although it runs from the timer queue —
this is the row that fails if AsyncLocalStorage does not propagate through
timers in the environment under test.

**S4 — an emitter callback** (`viaEmitter` subscribes `handler` to an
`EventEmitter`, emits once synchronously, then emits once from a
`setTimeout(…, 0)` and awaits a promise the second call resolves; `handler`
returns `undefined`):

```
CALL viaEmitter · CALL handler · RETURN handler · YIELD viaEmitter ·
CALL handler · RETURN handler · RESUME viaEmitter · RETURN viaEmitter=2
```

**Negative control — task separation.** Two consecutive tests `T1` and
`T2`, each running S1. Expected: every S1 row of the second test carries
`T2`; **zero** rows carry `T1` after `RETURN a` of the first test. A
runtime that keys tasks by "the first store ever created" fails here
while passing S1–S4.

### 1.2 The E8 swallow probe and its expected rows

`spike/typescript/probes/swallow.probe.test.ts`, node environment. The
runtime's interposition points at rung 0 are: every `throw` statement
(rewritten to record a RAISE at its site), every `catch` clause (a HANDLED
recorded at the top of the clause, empty clauses included), a
`process.on('unhandledRejection')` listener, and a name-based rewrite of
`.catch(<arrow with an empty body>)`. What each shape is EXPECTED to
produce if the mechanism works; a shape that produces less is a blind
spot to record, not a failure of the spike:

| # | Shape | Expected rows |
|---|---|---|
| 1 | `try { throw new Error("e1") } catch {}` | `RAISE Error("e1")` at the throw line; `HANDLED` at the catch line (empty clause) |
| 2 | `Promise.reject(new Error("e2")).catch(() => {})` | `HANDLED` at the `.catch` site, marked `sink: empty_catch_callback`; no RAISE (the rejection is not a `throw` statement) |
| 3 | `void Promise.reject(new Error("e3"))` (never handled) | a `RAISE` recorded by the `unhandledRejection` listener at process exit, with `loc` absent and `basis: "unhandledRejection"` |
| 4 | `throw "not-an-error"` caught by `catch (e)` | `RAISE` with `type: "string"`, `msg: "not-an-error"`; `HANDLED` at the catch |
| 5 | `catch (e) { throw e }` | `HANDLED` at the catch, then a second `RAISE` at the rethrow line, same `serial` |

### 1.3 The E4 site probe

`spike/typescript/probes/sites.probe.test.ts`: 20 named functions, one per
distinct syntactic shape (declaration, expression, arrow on one line,
arrow spanning lines, method, static method, constructor, getter, setter,
async declaration, async arrow, generator, async generator, default
export, arrow as class field, IIFE, nested inner function, callback
literal passed to `map`, a JSX-returning component in a `.tsx` sibling,
and a function inside a `namespace`), each called once from one test. The
TS line of each function's first token is written into the probe file as a
comment on the line above it and into the census as the expected value;
the spike compares recorded `code_objects.firstlineno` against it.

## 2. Ambient pins (preflight, recorded 2026-09-08 before any code exists)

| Item | Command | Value |
|---|---|---|
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| bun (curiosity only) | `bun --version` | `1.3.14` |
| vitest | `frontend/node_modules/vitest/package.json` | `4.1.9` |
| vite | same | `6.4.3` |
| typescript | same | `5.9.3` (the frontend's own; the transform uses THIS copy) |
| jsdom | same | `29.1.1` |
| react / pixi.js | same | `18.3.1` / `8.19.0` |
| VTT commit | `git -C ~/workspace/projects/vtt rev-parse HEAD` | `0091e97d695d3c71748a465301e00d159fea4e6c` |
| VTT branch / status | `git branch --show-current` / `git status --porcelain` | `feat/pixi-v12-fog` / one untracked file (`skills-lock.json`) — the live tree is never touched |
| copy | `rsync -a --exclude .git …` | `/mnt/extra/sensorium-s5/vtt/` — 725 MB with both `node_modules` |
| vitest config | `frontend/vite.config.ts` | `environment: 'jsdom'`, `globals: true`, `setupFiles: ['./src/test-setup.ts']`, no `pool` key (default), plugins `react()`, `tailwindcss()`, `suppressWebGPUForPixi()` |
| test census | `find … -name '*.test.ts*'` | 372 test files run by vitest (473 `*.test.*`/`*.spec.*` files exist repo-wide, some outside the frontend) |
| source size | TS/TSX lines outside tests | ~119k lines repo-wide |
| nproc / governor | `nproc` / `scaling_governor` | `16` / `powersave` |
| 1-minute load at pin time | `/proc/loadavg` | `0.25` |
| free disk | `df -h /mnt/extra` / `df -h /` | `72G` / `5.6G` (nothing writes to `/`) |
| env | `NODE_OPTIONS`, `VITEST`, `CI` | all unset |
| plain baseline, incomplete copy (history only) | `npx vitest run`, before the two data dirs were added | wall `22.31 s`, `22.17 s`; `369 passed, 3 failed (372)` files, `4051` tests — the 3 suites read `docs/superpowers/specs/*.json` and `backend/app/systems/pf2e/data/classes.json` from the repo root, absent from the first copy |
| **plain baseline, the lens** | `npx vitest run` after the data dirs were added | **wall `22.22 s`**, vitest `Duration 21.92s (transform 10.38s, setup 12.04s, import 32.67s, tests 77.72s, environment 162.49s)`, **`372 passed (372)` files, `4278 passed (4278)` tests**, exit 0 — n=1 here; E1's plain arm re-measures it at n=5 |
| sensorium | `sensorium --version` / `git -C ~/workspace/sensorium rev-parse --short HEAD` | `0.8.7` / `281b7fb` (main), branch `spike/typescript-mechanics` |

**Lens note on the baseline.** The first two walls were taken on a copy
missing two repo-root data directories; they are cited only to show the
plain wall's spread (0.14 s) and are not the E1 reference. The E1 plain
arm is the green copy.

## 3. Results

Run 2026-09-08 evening, this box, from `spike/typescript/` on branch
`spike/typescript-mechanics`. Numbers are in
`2026-09-08-typescript-mechanics-spike.results.json` (assembled by
`spike/typescript/assemble.py` from the artifacts under
`/mnt/extra/sensorium-s5/`); the reader transcript for E7 is
`2026-09-08-typescript-mechanics-spike.e7-reader.txt`. The instrument is a
TypeScript-AST-positioned, magic-string-edited source transform (no edit
inserts a newline), a runtime keyed on `AsyncLocalStorage`, one JSONL spool
per `(pid, threadId)`, and a converter writing format-4 SQLite through
`sensorium.store.db`. Two transform defects were found and fixed BEFORE any
E1 number was read and AFTER E3/E4/E8 had been read once on the probes
(their probe numbers were re-read on a fresh recording, `probes-3`, and did
not change): (1) two closing insertions at one offset nested in the wrong
order (`return () => x` → esbuild "Expected ;"), fixed by `prependRight`;
(2) functions inside `vi.mock`/`vi.hoisted` factories were instrumented,
which vitest's hoisting forbids — now an excluded kind. The first full-suite
instrumented run (`full-call-1`, 88 real files failed on those two defects)
is history, not a number; the E0 numbers are from `full-call-2` (372/4278
green).

### E2 — coverage of the frontend: **1.000, PASS**

Census set 368 files (`frontend/src` minus tests, `.d.ts`, `test-setup.ts`);
the transform threw on **0** files; **5,403 of 5,403** function-like nodes
instrumented (FunctionDeclaration 1,069 · ArrowFunction 4,268 ·
MethodDeclaration 59 · Constructor 4 · GetAccessor 2 · FunctionExpression 1);
excluded kinds in the census set: **none** (no overloads, abstract or
ambient bodies exist there — the `vi.mock` exclusion applies only inside test
files, outside the census). Output/input size 1.242. Not counted, by
construction: `new Function`/`eval` bodies. The ratio is the transform's own
count over its own eligibility rule, so what it proves is that the transform
PARSES and EDITS every source file in the consumer; whether the instrumented
code RUNS is E0/E1's 372/4278.

### E3 — async attribution: **100%, PASS in node, jsdom, and node:test**

Every expected row of S1–S4 present, in order, with the expected task,
under the vitest `node` environment, the vitest `jsdom` environment, and the
`node --test` harness through the loader hook (three independent recordings,
`probes-3` ×2 and `nodetest-2`). Negative control: **0** rows of T1 after
T1's `RETURN a`; T2's 12 rows all carry T2. The rows that decide it: S3's
`CALL work` from a `setTimeout` callback and S4's second `CALL handler` from
a timer-driven `emit` both carry their scenario's task — `AsyncLocalStorage`
propagates through Node timers and through jsdom's timers alike.

Two clarifications the checker applies, written here because §1.1 did not
spell them out (recorded honestly: both were implemented in `check.py`
before its first run, and one checker defect — comparing a RETURN's value
where §1.1 named none — was found on the first read of S4 and fixed WITHOUT
re-recording; the spool it re-read is the same file): rows of functions not
named in §1.1's tables are ignored (`sleep`, promise executors, timer
callbacks); a qualname matches on its last `.` segment (`viaEmitter.handler`
is `handler`); RETURN values compare with whitespace removed (`[ 10, 20 ]`
is `[10,20]`).

One shape the tables did not ask about, visible in `tree`: a timer callback
runs with NO open frame on its task's stack (its scheduler had yielded), so
its frame is parentless at depth 0 inside the task. Task attribution is
right; causal parentage across a timer is a rung-1 design question, not a
rung-0 failure.

### E4 — sites: **20 of 20, PASS**

All twenty shapes' `firstlineno` equal the TypeScript source line
(declaration, expression, one-line and multi-line arrow, constructor,
method, static, getter, setter, class-field arrow, async declaration and
arrow, generator, async generator, IIFE, nested inner, `map` callback,
default export, `namespace` member, and the TSX component in the sibling
file). Paths are `frontend/sensorium-probes/…`, identical across the two
probe recordings. The failing-assertion line check was not run separately:
E1's `call` arm reports every failing line vitest prints (none — the suite
is green), so the map-chain claim rests on the 20 sites and on vitest's own
`FAIL` reports in the defect runs, which pointed at the TS line and column
of the ORIGINAL file (e.g. `ArtPicker.tsx:62:141`) — the source map the
plugin returns is honoured.

### E5 — harnesses: **vitest PASS (gate), node --test PASS**

vitest: five probe files pass under the Vite plugin (`enforce: 'pre'`), and
the full suite is green under it. `node --test`: a `module.register` loader
hook transforms then type-strips with the frontend's own TypeScript; the
E3 probe's node:test variant passes and its E3 rows check. jest: not
measured (VTT does not use it). Note for rung 1: the repo's
`setupFiles` assumes jsdom, so a probe declaring `@vitest-environment node`
needs the setup file dropped — that is the consumer's config, not the
recorder's.

### E7 — today's reader on `lang: "typescript"`: reported

`tree`, `frame`, `grep`, `runs` and the structural half of `info` answer
correctly from the trace (tasks named by test title, returns as `dbg` text,
`<unread: locals>` on every call, YIELD/RESUME shown as suspensions).
The vocabulary leaks, verbatim in the transcript: `info` prints
**`python ?`** for the interpreter line and **"asyncio task"** in both
fingerprint sentences; `frame` advises **`refocus with --focus
async.probe.test.ts:viaEmitter`** (Python's spelling); `runs` labels the
invocation **`invocation probes-2: cargo`** — a non-Python invocation is
assumed to be Rust; `refocus` refuses on `capabilities.refocus: false`
(right) and then suggests **`sensorium run --focus`** (Python's recorder).
`exceptions` refuses at exit 3 with **"needs the Rust disposition rules
(rung 3)"** — the refusal is correct (no TypeScript rules exist), the
sentence names the wrong language. `watch`/`flow` refuse on
`capabilities.line: false` correctly. Rung 1 therefore needs: a
`TYPESCRIPT` vocabulary table, an explicit refusal (not a fallback to
Python's words) for a `lang` the reader does not know, a language-keyed
`runs` header, and TypeScript disposition rules before `exceptions` can
answer.

### E8 — swallow shapes: **5 of 5 seen**

| # | Shape | Seen as |
|---|---|---|
| 1 | empty `catch {}` | `RAISE Error("e1")` at the throw line; `HANDLED` at the catch with `sink: "empty_catch"` |
| 2 | `.catch(() => {})` | `HANDLED` with `sink: "empty_catch_callback"`, no RAISE (no `throw` statement ran) |
| 3 | unhandled rejection | `RAISE` with `basis: "unhandledRejection"` from the process listener — and vitest 4 did NOT mark the file failed |
| 4 | `throw "not-an-error"` | `RAISE` `type: "string"`; `HANDLED` at the catch |
| 5 | `catch (e) { throw e }` | two `RAISE` rows with ONE serial (WeakMap identity), two `HANDLED` |

What rung 2 still has to decide is which of these are sinks in the
`exceptions` sense (2 and the empty clause of 1 clearly; a rethrow is a hop,
not a sink) and what an unhandled rejection's "frame" is (none: it was
recorded outside every task and frame).

### E0, E1, E6 — see below, filled when the arms finished.

## 4. Decisions

*(unrun)*
