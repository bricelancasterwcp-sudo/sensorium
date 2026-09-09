# S5 rung 1 — TypeScript recorder v1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first product TypeScript recorder — the `typescript/` Node library, `sensorium ts run`/`sensorium ts ingest`, and the reader's `TYPESCRIPT` column — so that `runs`, `info`, `tree`, `frame`, `grep` and `diff` (with `--ignore-moves`) answer on real VTT-frontend traces with the honesty contract the other two recorders carry, and prove it against the pre-registered endpoints E0′–E11 and the two §10 controls on the spike's lens.

**Architecture:** A Python driver over a Node library (spec D1). The library is written fresh under `typescript/` against the spec, taking the parked spike (`origin/spike/typescript-mechanics`, `spike/typescript/`) as the proven shape for the transform, the runtime and the Vite plugin. The driver recognises the harness, writes a wrapper config and a setup file under the consumer's `node_modules/.sensorium/`, spawns the command as typed, waits, and converts every spool into a format-4 trace through `sensorium.store.writer.TraceWriter` in parallel. The reader gains a third vocabulary column, one choke-point refusal for an unknown `lang`, a lang-keyed `runs` header, `info_typescript.py`, and seven conformance vectors.

**Tech Stack:** Node 24.16 (the measured floor), ESM `.mjs` with JSDoc types checked by `tsc --checkJs`, `magic-string` (the one runtime dependency; `typescript` is the consumer's), vitest 4.1 + jsdom for the probe project and corpus; Python 3.12–3.14 for the driver, converter and reader; sensorium 0.8.7 → **0.9.0**, `sensorium-ts` **0.1.0**.

**Spec:** `docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md` — §2 (architecture), §3 (transformer), §4 (runtime and wire), §5 (contract), §6 (reader), §7 (ledger), §8 (endpoints), §9 (tests), §10 (first use), §12 (D1–D16). **Findings:** `docs/superpowers/spikes/2026-09-08-typescript-mechanics-spike.md` §3–§4 are binding on every task. **Contract:** `docs/TRACE-FORMAT.md`. **Rigor:** `~/.claude/skills/rigorous-experiments/SKILL.md`. **Style:** this plan states interfaces and invariants, and gives verbatim text only where a fresh implementer would guess wrong (wire records, the splice forms, the wrapper files, the run line) — plan-carried code was the dominant defect source in earlier rungs.

## Global Constraints

- **`~/workspace/projects/vtt` is read-only, forever, for this plan.** The lens is the copy at `/mnt/extra/sensorium-s5/vtt/` (root `frontend/`, VTT `0091e97`, vitest 4.1.9, vite 6.4.3, typescript 5.9.3, jsdom 29.1.1); E5-TS's split and the planted change happen on a `cp -a` of it under `/mnt/extra/sensorium-s5/lens-<name>/`, never on the lens itself.
- **The second disk carries every artifact set**: `SENSORIUM_DIR=/mnt/extra/sensorium-s5/store-rung1` for every trace a task records (71 GB free on 2026-09-09); nothing measured writes to `/`. **No box path is ever committed**; env values live in the ledger and the task briefs.
- **The spike is a shape, not a source.** `spike/typescript/` is never cherry-picked; every file under `typescript/` is product: version `0.1.0`, `private: true`, no "throwaway" wording.
- **Pre-registration is committed before any code** (Task 0). After a number is read no threshold moves, no arm is added, no run is re-rolled; an infrastructure kill may be re-run from zero with the reason recorded.
- **Legacy output is byte-identical**: the existing suite (count pinned in Task 0 on 3.12/3.13/3.14, corpus Python + Rust) is the regression fence for every Python task; `PYTHON` and `RUST` strings in `vocab.py` do not change by one character.
- **Dependency policy**: `typescript/` runtime dependency `magic-string` only; `rt.mjs` imports `node:` builtins only; `typescript` is resolved from the consumer's root by `createRequire`; devDependencies `typescript`, `vitest`, `jsdom`, `@types/node`. Python: no new runtime dependency.
- **The transform never inserts a newline** — `lines(out) === lines(in)` asserted on every golden and every probe file.
- No file over 800 lines; functions under 50 lines. Every test mutation-checked before it counts (break the pinned line, watch it fail, restore); Python mutation runs purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`.
- Commits: conventional prefixes; trailer lines per the session's git rules. Branch `feat/s5-rung1-recorder-v1` off `main` once PR #24 has merged (the spec and findings must be on `main` first; if it has not merged, branch off `docs/s5-typescript-design` and say so in the ledger).

---

## Decisions this plan makes (each amends the spec non-silently in Task 11)

| # | Question | Decision | Why | Cost if wrong |
|---|---|---|---|---|
| P1 | Spec §5.1's `pool` key | **Dropped.** `environment` comes from `expect.getState().environment` through the setup file; `vitest` from the driver reading `<root>/node_modules/vitest/package.json`; the pool is already legible from `thread_id_os`/`is_main_thread`. | vitest sets no env var naming the pool. | `info` prints `node v24.16.0 (vitest 4.1.9, jsdom)` — one word fewer. |
| P2 | How a test/describe call is wrapped | **Spread form:** `test(...__srt.task(<title>, fn, <flags>), <rest…>)`, `describe(...__srt.suite(<title>, fn))`. The helper returns `[title, wrapped]`. | The title expression is evaluated once; no newline; options arguments survive. | none known |
| P3 | Where the unknown-`lang` refusal lives (spec §6) | **`db.open_trace`**, keyed on `db.KNOWN_LANGS = ("python", "rust", "typescript")`, raising `TraceFormatError` (exit 2, the newer-format refusal's shape); `vocab.terms()` indexes strictly and never falls back. | One choke point: every command refuses identically, and `grep` cannot answer where `info` refuses. | A recorder for a fourth language must add its column AND its name here — which is the rule. |
| P4 | Records with no frame | A parentless CALL carries `caller: "untraced"`; a RAISE/HANDLED whose `f` is null is counted in meta **`throw_flow_outside_frames`** and written as no event (the contract forbids a code-less causal row; Rust's `err_flow_outside_frames` precedent). | | none |
| P5 | The setup file | `typescript/src/setup.mjs` is a **template**; the driver writes the filled copy to `<root>/node_modules/.sensorium/<invocation>.setup.mjs` beside the wrapper, so its `import 'vitest'` resolves to the CONSUMER's vitest. | A setup file outside the consumer's tree would resolve `vitest` from `typescript/node_modules` and register hooks into the wrong runner instance. | none |
| P6 | Re-ingesting a spool directory | `ingest` writes `<spool>/ingested.json` (`{run_ids}`) and refuses at exit 2 when it exists, naming it. | A second ingest would mint new run ids over the same records. | none |
| P7 | The `run:` line the driver prints | `run: <id>  pid: <pid>  file: <test_file or ->  events: <n>  tasks: <m>` — accepted by `corpus.run_corpus.RUN_LINE` (shape 2, `  pid: ` anchor). | One line per trace, as the Rust converter prints. | none |
| P8 | YIELD payload | `{"awaiting": "Promise"}` for `await`, `{"awaiting": "consumer"}` for `yield`/`yield*`; the wire carries `k: "await"|"yield"`. | The reader prints `awaiting` as a type name. | none |
| P9 | The corpus's vitest root | `corpus/typescript/` is ONE vitest project (shared `package.json`, `package-lock.json`, `vitest.config.ts` with `environment: 'node'`); a case is a subdirectory; `program: vitest`, `harness_args: ["run", "<case>"]`. The runner copies `corpus/typescript/` (minus `node_modules`, `.sensorium`) into the work dir and **symlinks** the real `node_modules` in. | One `npm ci`, not one per case. | Cases share a config; a case needing jsdom uses the per-file `@vitest-environment` pragma. |
| P10 | Locating the Node package from Python | `SENSORIUM_TS_PKG` if set, else `Path(sensorium.__file__).parents[2] / "typescript"` (the editable-install layout); refuse at exit 2 when `<pkg>/node_modules/magic-string` is absent, naming `npm ci --prefix <pkg>`. | The global tool is an editable install of this checkout. | A wheel install has no `typescript/` beside it and must set the variable; the refusal says so. |
| P11 | The `describe` stack | Per container, pushed/popped synchronously around the suite callback; an `async` callback registers after the pop (ledger blind spot). | | provider names unaffected |

## Pre-registration (Task 0 commits spec §8's table and §10's two controls verbatim as `docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §1, plus these pins)

- **E3-TS's file, named now:** `src/__tests__/useMeshVoice.test.tsx` (39 `await`s, 3 timer sites, 21 tests on the lens). Twenty `sensorium ts run -- npx vitest run src/__tests__/useMeshVoice.test.tsx`, `diff` each against the first.
- **E9's sample:** the first 20 task names of the trace for `src/components/inventory/InventoryTab.test.tsx`, against `fullName`s from one plain `npx vitest run --reporter=json --outputFile=<store>/e9.json` of the same file.
- **E10's lens:** `sensorium ts ingest` over the full-suite spool set of E0′'s run, n=3, median; and over E3-TS's first spool.
- **E11(b)'s kill:** `kill -9` of the forked child running `InventoryTab.test.tsx` during a full-suite run, found by `pgrep -f '^[^ ]*node .*forks'` anchored (never `pkill -f` unanchored: it self-matches).
- **Reported without a gate:** as spec §8's list.

## File structure

```
typescript/
├── package.json                  sensorium-ts 0.1.0, private, type module, engines node>=24, exports ./rt ./transform ./vite ./register
├── package-lock.json             committed; `npm ci` is the install
├── tsconfig.json                 allowJs + checkJs + strict, noEmit, types node
├── README.md                     install (npm ci), record (sensorium ts run …), what rung 1 does and does not see
├── HONESTY.md                    the TypeScript honesty ledger (spec §7) — written in Task 1, before the runtime
├── src/{transform.mjs, rt.mjs, vite.mjs, register.mjs, setup.mjs (template), dbg.mjs, qualname.mjs}
├── test/{transform.test.mjs, rt.test.mjs, golden/*.ts → *.expected.ts}     node --test
├── probes/                       a vitest project: package.json, vitest.config.ts (imports ../src/vite.mjs directly), files per spec §9
└── acceptance/{census.mjs, check_e3.py, sites.py, e6.sh, arms.sh, assemble.py}   the §8 instruments, committed
src/sensorium/ts/{__init__.py, cli.py, driver.py, harness.py, wrapper.py, pkg.py, spool.py, ingest.py}
src/sensorium/query/{vocab.py (TYPESCRIPT, kind_labels), info_typescript.py, runs_cmd.py, exceptions_cmd.py, tree_cmd.py, frame_cmd.py}
src/sensorium/store/db.py         KNOWN_LANGS + the refusal
tests/{test_ts_harness.py, test_ts_wrapper.py, test_ts_ingest.py, test_ts_live.py, test_vocab.py, test_ts_refusal.py}
tests/fixtures/ts-spools/<case>/{invocation.json, harness.json, <pid>-0.jsonl, questions.json}
docs/trace-format/vectors/v23..v29.json; docs/trace-format/VECTORS.md
corpus/typescript/{package.json, package-lock.json, vitest.config.ts, README.md, <case>/{*.test.ts, questions.yaml}}
docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md   §1 pre-registration, §2 pins, §3 results, §4 decisions, §5 gaps
```

---

### Task 0: Branch, pre-registration, preflight, the package skeleton

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` — §1 (spec §8 table + §10 controls + the pins above, verbatim), §2 ambient pins (filled), §3 results (every cell `not measured (rung 1 pending)`), §4, §5 empty.
- Create: `typescript/package.json`, `typescript/tsconfig.json`, `typescript/.gitignore` (`node_modules/`), run `npm install magic-string@^0.30 && npm install -D typescript@^5.9 vitest@^4.1 jsdom@^29 @types/node@^24` and commit the lock.

**Invariants:**
- The pre-registration commit precedes every other commit on the branch.
- §2 records: `node --version` (`v24.16.0`), `npm --version`, the lens's vitest/vite/typescript/jsdom versions from `frontend/node_modules/*/package.json`, the lens's sha256 manifest of `frontend/src` + `vite.config.ts` + `package.json` (748 entries expected — the spike's E6 set; store it at `/mnt/extra/sensorium-s5/manifest-rung1-before.txt`), a plain `npx vitest run` on the lens at `372 passed (372)` / `4278 passed (4278)` with its wall, `nproc`/governor, `df -h` of `/` and `/mnt/extra`, `NODE_OPTIONS`/`VITEST`/`CI` unset, the Python suite's pass count on 3.12/3.13/3.14, `sensorium --version`, and `git rev-parse HEAD` of this repo.
- Preflight refuses under 8 GB free on `/mnt/extra` or 3 GB on `/`, or a 1-minute load above 4.0.
- `npm ci` in `typescript/` reproduces `node_modules` from the lock; `npx tsc -p typescript/tsconfig.json` passes on an empty `src/`.

- [ ] **Step 1:** branch; `mkdir -p /mnt/extra/sensorium-s5/store-rung1`; preflight; the manifest; the plain baseline; write §1 and §2.
- [ ] **Step 2:** the package skeleton; `npm ci`; `npx tsc -p typescript/tsconfig.json`.
- [ ] **Step 3:** Commit: `docs(s5): pre-register rung 1 (E0'–E11, the §10 controls) before any recorder code exists; the sensorium-ts skeleton`.

---

### Task 1: `typescript/HONESTY.md`, `typescript/README.md`

**Files:**
- Create: `typescript/HONESTY.md` (spec §7's ten sections, each row naming its falsifier by the path a later task must use), `typescript/README.md`.

**Interfaces:** the falsifier names are fixed here and later tasks must create them: `typescript/test/rt.test.mjs` (`task isolation`, `stack pops at yield`, `serial survives rethrow`, `dbg caps`, `flush on exit`), `typescript/test/transform.test.mjs` (goldens), `typescript/probes/{async,sites,swallow,each,concurrent,never_settles,describe_chain,timer_parentless}.probe.test.ts`, `tests/test_ts_ingest.py`, vectors `v23`–`v29`, corpus cases `corpus/typescript/{double_call,pass_vs_fail,wrong_branch,nondeterministic,unit_mismatch,async_interleaved,object_refused,watch_refused,exceptions_refused,each_naming,unhandled_rejection_in_info,suspended_at_end,timer_callback_parentless}`, and endpoints E0′–E11.

**Invariants:** every promise names a falsifier; every "cannot see" is also a meta key, an `info` line or a transform exclusion count — the ledger claims nothing the trace does not carry. README: `npm ci --prefix typescript`, `sensorium ts run [--tier off|call] -- vitest run …`, where traces go, the not-yet list (`exceptions`, `watch`, `flow`, `refocus` refuse on these traces in 0.1.0; args unread).

- [ ] Write both; commit: `docs(typescript): the honesty ledger before the runtime`.

---

### Task 2: `typescript/src/transform.mjs` — the rewriter, goldens

**Files:**
- Create: `src/transform.mjs`, `src/qualname.mjs`, `test/transform.test.mjs`, `test/golden/<rule>.ts` + `.expected.ts` for every rule below.

**Interfaces:**
- `transformSource(code: string, filePath: string, opts: {root: string, ts: typeof import('typescript'), rtPath: string}) → {code, map, manifest} | null` — null for a path outside `root`, under any `node_modules`, a `.d.ts`, or an extension outside `.ts .tsx .js .jsx .mjs` (`.cjs` counted in the manifest as `excluded.commonjs` and returned null).
- `manifest = {file: <abs>, rel: <root-relative>, sha256, instrumented: [{qualname, line, kind}], excluded: {<reason>: count}}` with `kind ∈ function|coroutine|generator|async_generator` and reasons `vitest-hoisted-factory`, `overload-signature`, `ambient`, `abstract`, `commonjs`.
- Header prepended: `import * as __srt from "<rtPath>";const __sfile=__srt.file(<rel>,<abs>,<codes>,<sha>);` where `codes = [[qualname, line, kind]…]`.
- The splice forms (verbatim, the one place to copy):
  - block body: after `{` → `const __sf=__srt.call(__sfile,<idx>);try{`; before the closing `}` → `;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}`
  - expression body: `{const __sf=__srt.call(__sfile,<idx>);try{return __srt.ret(__sf,(` … `))}catch(__se){__srt.thr(__sf,__se);throw __se}}`
  - `return <e>` → `return __srt.ret(__sf,(<e>))`; bare `return` → `return __srt.ret(__sf,undefined)`
  - `await <e>` → `__srt.r(__sf,await __srt.y(__sf,(<e>),0))`; `yield <e>` / `yield* <e>` → `__srt.r(__sf,yield __srt.y(__sf,(<e>),1))` / `__srt.r(__sf,yield* __srt.y(__sf,(<e>),1))`
  - `throw <e>` → `throw __srt.raise(__sf,(<e>),<line>)`; a `catch (e) {` gains `__srt.handled(__sf,e,<line>,<how>);` as its first statement; `catch {` becomes `catch(__sce){__srt.handled(__sf,__sce,<line>,<how>);` — `how` is `"sink_empty_catch"` for an empty block, `"catch"` otherwise; `.catch(() => {})` (arrow, empty block) → `.catch(__srt.emptyCatch(__sf,<line>,() => {}))`
  - `test|it[.chain…](<title>, fn, …)` → `(...__srt.task((<title>),fn,<flags>), …)` with `flags = (literal ? 1 : 0) | (each ? 2 : 0)`; `describe|suite[.chain…](<title>, fn)` → `(...__srt.suite((<title>),fn))`; `__sf` outside any instrumented function is spelled `null`.
- Closing insertions at one offset are spliced innermost first (`prependRight`); nothing inside a `vi.mock|vi.doMock|vi.hoisted|vi.unmock` factory is instrumented.

**Invariants:** every golden is byte-exact; `lines(out) === lines(in)` on every golden; the census over the lens's `frontend/src` (Task 10's `census.mjs`, runnable now) reports 0 files thrown on and every exclusion named; a property test parses the output of every golden with the consumer's `ts.createSourceFile` and finds no syntax diagnostics.

- [ ] Goldens first (one per bullet above, plus TSX, class field arrow, getter+setter, `namespace`, IIFE, nested fn, `map` callback, `export default`, constructor with `super()`, `test.each`, `it.concurrent`, `describe.each`, `vi.mock` factory, overload set, CommonJS); then the rewriter to green; `npm test` and `npx tsc` green; commit: `feat(typescript): the transform — functions, suspension, throw flow, tests as tasks, goldens`.

---

### Task 3: `typescript/src/rt.mjs` — tasks, stacks, values, spools

**Files:**
- Create: `src/rt.mjs`, `src/dbg.mjs`, `test/rt.test.mjs`.

**Interfaces** (every export a no-op returning its pass-through value when the tier is not `call`):
- `file(rel, abs, codes, sha) → fileId`; `task(title, fn, flags) → [title, wrapped]`; `suite(title, fn) → [title, wrapped]`; `call(fileId, idx) → frame|null`; `ret(f, v) → v`; `thr(f, e)`; `y(f, x, kind) → x`; `r(f, v) → v`; `raise(f, e, line) → e`; `handled(f, e, line, how)`; `emptyCatch(f, line, fn) → fn'`; `nameProvider(fn)`; `fileStart(path, environment)`; `seen(name)`; `flush()`.
- Env: `SENSORIUM_TIER` (`off`|`call`), `SENSORIUM_SPOOL` (dir), `SENSORIUM_INVOCATION`. Spool `<SENSORIUM_SPOOL>/<pid>-<threadId>.jsonl`.
- Wire records (verbatim keys, wire `1`): `BOOT {e, wire:1, pid, ppid, threadId, isMainThread, argv, cwd, env, envHash, node, tier, invocation, startTs, ts}` · `FILE {e, id, rel, abs, codes, sha}` · `TASK {e, id, name, basis: "vitest"|"title", conflict: bool}` · `CALL {e, f, p, file, c, t, ts}` · `RETURN {e, f, t, v, ts}` · `UNWIND {e, f, t, x, ts}` · `YIELD {e, f, t, k: "await"|"yield", ts}` · `RESUME {e, f, t, ts}` · `RAISE {e, f, t, x, l, how, ts}` · `HANDLED {e, f, t, x, l, how, ts}` · `UNHANDLED {e, x, ts}` · `FILE_START {e, path, environment}` · `SEEN {e, name}` · `EXIT {e, code, endTs, ts}`. `x = {kind: "throw"|"rejection", type, msg, serial}`; `v = {k: "dbg", v, trunc} | {k: "unread"}`; `envHash` = sha256 over sorted `k=v` lines, hex, first 16.
- Task naming (spec §4, D4): `wrapped` runs `fn` inside `als.run(task)`; name = provider name when a provider is registered and returns a string, cross-checked when `flags & 1 && !(flags & 2)` (`endsWith(title)`; a miss → lexical name, `conflict: true`); lexical = `[...suiteStack, title].join(' > ')`; the k-th activation of one registration appends `#k` for k ≥ 2.
- Frames: per-task stack; `call` pushes with `p` = the top or null; `ret`/`thr` pop by identity; `y` pops, `r` pushes.
- `dbg(v)`: `util.inspect(v, {depth: 2, maxArrayLength: 8, maxStringLength: 100, breakLength: Infinity, compact: true})`, capped at 200 bytes with `trunc`; a throwing inspect → `{k: "unread"}`; `undefined` → the text `undefined`.
- Flush: after every task settles, every 100 ms (unref'd), on `exit`, `beforeExit`, `SIGTERM`/`SIGINT`/`SIGHUP` (then re-raise the default), and `unhandledRejection` writes UNHANDLED then flushes.

**Invariants** (each a test in `rt.test.mjs`, each mutation-checked): two consecutive tasks leak zero rows (the E3 negative control in miniature); after `y` the stack top is the parent, after `r` it is the frame again; a rethrown object keeps its serial and a rethrown string does not; `dbg` of a 10 kB string is 200 bytes with `trunc: true`; a `SIGTERM`ed child's spool ends with EXIT; a task whose provider name does not end with its literal title is recorded `conflict: true` under the lexical name; `off` writes no file at all.

- [ ] Tests first; runtime to green; commit: `feat(typescript): the runtime — AsyncLocalStorage tasks, per-task stacks, dbg values, JSONL spools`.

---

### Task 4: `vite.mjs`, `register.mjs`, the setup template, the probe project

**Files:**
- Create: `src/vite.mjs`, `src/register.mjs`, `src/setup.mjs` (template with `__PKG__` placeholder), `probes/{package.json, package-lock.json, vitest.config.ts, src/…}`, the eight probe files named in Task 1.

**Interfaces:**
- `sensorium({root, pkgDir, rtPath}) → VitePlugin` with `enforce: 'pre'`; resolves `typescript` by `createRequire(join(root, 'package.json'))` and `magic-string` by `createRequire(join(pkgDir, 'package.json'))`; `transform(code, id)` strips `?query`, calls `transformSource`, returns `{code, map}` or null; writes the manifest to `$SENSORIUM_MANIFEST_DIR/<rel with / → __>.json` when that variable is set.
- `register.mjs`: `node --import <pkg>/src/register.mjs --test …`; reads `SENSORIUM_TS_ROOT`, `SENSORIUM_TS_PKG`; the hook transforms `.ts/.tsx` under the root and type-strips with the root's `typescript` (`transpileModule`, ESNext/ES2022/react-jsx), as the spike did; `.js/.mjs` under the root are transformed without stripping.
- The setup template (verbatim; the driver substitutes `__PKG__`):
  ```js
  import { beforeEach, expect } from 'vitest';
  import * as rt from '__PKG__/src/rt.mjs';
  rt.nameProvider(() => expect.getState().currentTestName ?? null);
  rt.fileStart(expect.getState().testPath ?? null, expect.getState().environment ?? null);
  beforeEach(() => { rt.seen(expect.getState().currentTestName ?? null); });
  ```
- The probe project's own `vitest.config.ts` imports `../src/vite.mjs` directly and lists `probes/setup.mjs` — the template's text with `'../src/rt.mjs'` in place of `__PKG__/src/rt.mjs` (a test in `transform.test.mjs` asserts the two files differ only on that line) — so the probes run WITHOUT the driver: `SENSORIUM_TIER=call SENSORIUM_SPOOL=<dir> npx vitest run` from `typescript/probes/`.

**Invariants** (a `probes/check.mjs` reads the spools and asserts): the E3 rows of spec §1.1 of the findings in `node` and `jsdom` files; 20/20 sites on their `// SITE` lines; the five swallow shapes; `each.probe` produces 3 tasks named `adds 1 + 2`-style by the provider with `conflict: false`; `describe_chain.probe` names `outer > inner > leaf`; `never_settles.probe`'s frame ends on a YIELD with no RETURN; `timer_parentless.probe`'s timer callback CALL has `p: null` inside its task; `concurrent.probe` records a conflict count that the checker prints (not gated: the documented hazard); `node --test` on the async probe produces its rows through `register.mjs`.

- [ ] Plugin, hook, template, probes, checker; `npm ci` in `probes/`; commit: `feat(typescript): the Vite plugin, the node --test hook, the setup template, and the probe project`.

---

### Task 5: `sensorium ts ingest` — spools to traces

**Files:**
- Create: `src/sensorium/ts/{__init__.py, spool.py, ingest.py}`, `tests/test_ts_ingest.py`, `tests/fixtures/ts-spools/<case>/…` for cases `async-chain` (recorded from the probe project in Task 4 and committed), `unhandled-rejection`, `killed-mid-file` (a spool cut before EXIT), `each-names`, `outside-frame-throw`, `no-boot` (refused by name).

**Interfaces:**
- `spool.read(path) → Spool` (records in order; `boot` required else `SpoolError` naming the file; `exit` optional).
- `ingest.convert(spool_path, invocation: dict, harness: dict|None, store_dir) → Summary{run_id, pid, test_file, events, tasks, incomplete}`; `ingest.ingest_dir(spool_dir, store_dir, jobs=os.cpu_count()) → list[Summary]` (a `multiprocessing.Pool` over spool files in name order; writes `ingested.json`; refuses when it exists — P6).
- Trace construction through `TraceWriter`: `intern_code(abs, qualname, line)`; `open_frame(parent_db, code_id, call_eid, depth, 1, kind)`; CALL payload `{"args": {}, "unread": ["locals"]}` plus `"caller": "untraced"` when `p` is null; RETURN `{"value": v, "outcome": "ok"}` and `close_frame(return)`; UNWIND → `close_frame(None, "unwind", exc)`; YIELD per P8; RAISE/HANDLED `{"exc": x, "how": how}` with `line`, `frame_id`/`code_id` from `f` (closed frames included), or counted in `throw_flow_outside_frames` when `f` is null; UNHANDLED → `unhandled_rejections`; TASK → `add_task(id, name, 1)`; fingerprints per task and one thread row over `(rel, qualname, kind)` for the four causal kinds (`Fingerprint`, root-relative file = `rel`); `truncated_count` = `trunc: true` values.
- Meta: the required set (`run_id` minted `time.strftime('%Y%m%d-%H%M%S', localtime(startTs)) + '-' + 6 hex`; `argv`, `cwd`, `env`, `env_hash` from BOOT; `start_ts`/`end_ts` from BOOT/EXIT, `end_ts` = last `ts` when EXIT is absent; `exit_status: None`, `exit_status_basis: "unwitnessed"`; `main_thread_ident: 1`; `fingerprint_basis: "per-task"`; `source_hashes {abs: sha}`; `recorder: "sensorium-ts 0.1.0"` (from the package.json the driver recorded in `invocation.json`); `lang: "typescript"`; `capabilities` = spec §5.2; `caps: {"dbg": 200, "depth": 2, "sample": 8, "str": 100}`), the TypeScript-only keys of spec §5.1 minus `pool` plus `throw_flow_outside_frames`, `harness_exit` when `harness.json` exists; `incomplete` true first, `False` after finalize only when EXIT was present.

**Invariants** (tests): every complete fixture opens with `db.missing_required == []`; `killed-mid-file` opens `incomplete: true` and `diff` against `async-chain` exits 3; `unhandled-rejection` has the entry in meta and zero events with a NULL `code_id`; `outside-frame-throw` counts 1 and writes no event; `each-names` has three `tasks` rows named as the provider named them; the async fixture's `tree` shows S1's frames nested `a → b → c` and the two `p` frames as siblings under `fanout`; `no-boot` raises `SpoolError` naming the file; re-ingest refuses at exit 2 naming `ingested.json`; the `run:` line matches `RUN_LINE` (P7).

- [ ] Fixtures and tests first; converter to green on 3.12/3.13/3.14; commit: `feat(ts): sensorium ts ingest — JSONL spools to format-4 traces through TraceWriter, in parallel`.

---

### Task 6: `sensorium ts run` — harness recognition, the wrapper, the driver

**Files:**
- Create: `src/sensorium/ts/{cli.py, harness.py, wrapper.py, pkg.py, driver.py}`, `tests/test_ts_harness.py`, `tests/test_ts_wrapper.py`, `tests/test_ts_live.py` (gated by `SENSORIUM_TS_LIVE=1` and skipped BY NAME otherwise).
- Modify: `src/sensorium/cli.py` — register `ts` (`from sensorium.ts import cli as ts_cli; ts_cli.add_parser(sub)`), help `record a TypeScript/JavaScript program under vitest or node --test`.

**Interfaces:**
- `harness.recognise(cmd: list[str], cwd: Path) → Plan | Refusal`; `Plan{kind: "vitest"|"node-test", argv, root, user_config: Path|None}`; `Refusal{message}` for `npm|pnpm|yarn test|run …` ("run the harness directly: sensorium ts run -- vitest run …"), for `jest` ("jest is not supported: not measured, and the consumer does not run it"), and for anything else (naming `vitest` and `node --test`). vitest is recognised through `vitest`, `npx vitest`, `pnpm vitest`, `pnpm exec vitest`, `yarn vitest`, any path ending `/vitest`; `--root X`, `-r X`, `--root=X`, `--config X`, `-c X`, `--config=X` are consumed; the default config search is `vitest.config.{ts,mts,cts,js,mjs,cjs}` then `vite.config.{…}` in the root.
- `wrapper.write(root, invocation, pkg_dir, user_config) → (config_path, setup_path)` under `<root>/node_modules/.sensorium/`; `wrapper.remove(paths)`. The config text (verbatim):
  ```ts
  // written by sensorium ts run for invocation <inv>; removed when it exits
  import { mergeConfig } from 'vitest/config';
  import sensorium from '<pkg>/src/vite.mjs';
  import base from '<user config abs>';            // line absent when none
  const user = base;                                // `{}` when none
  const resolved = typeof user === 'function' ? await user({ command: 'serve', mode: 'test' }) : user;
  export default mergeConfig(resolved, {
    root: '<root>',
    plugins: [sensorium({ root: '<root>', pkgDir: '<pkg>', rtPath: '<pkg>/src/rt.mjs' })],
    test: { setupFiles: ['<root>/node_modules/.sensorium/<inv>.setup.mjs'] },
  });
  ```
  A read-only `node_modules` → `Refusal` naming the directory (D9).
- `pkg.locate() → Path` (P10); `pkg.node_version() → (major, minor, patch)`; below 24 → refusal.
- `driver.run(args) → int`: order = node check → package check → recognise → mint invocation (`paths.new_run_id()`), spool dir `paths.trace_root()/spool/<inv>/`, `invocation.json` `{invocation, harness, harness_args, root, cwd, argv, env_hash, start_ts, wrapper, vitest, node, driver_version, recorder}` → write wrapper (vitest) or prepend `--import` (node-test) → env `SENSORIUM_SPOOL, SENSORIUM_TIER, SENSORIUM_TS_ROOT, SENSORIUM_TS_PKG, SENSORIUM_INVOCATION` → spawn with inherited stdio, wait → `harness.json` `{status, signal, wall_start_ts, wall_end_ts, basis: "waited"}` → `finally` remove the wrapper files → `ingest_dir` → print one `run:` line per trace (P7) and `invocation: <inv>  traces: <n>  harness exit: <status> (waited)` → return the harness's status (`128 + signal` on a signal).
- `sensorium ts ingest <spool-dir>`: `ingest_dir` alone, same lines.

**Invariants:** the recognition table above, each row a test; the wrapper text byte-exact against a golden with and without a user config; `--config`/`--root` consumed and re-issued exactly once; live (gated): `sensorium ts run -- npx vitest run` in `typescript/probes/` produces one trace per probe file, `runs` groups them under `invocation <id>: npx vitest run  exit:0 (waited)`, `info` on the async probe's trace prints `node v24.16.0 (vitest 4.1.9, node)` and `tests: 6 as tasks, 6 seen by the harness`, and `node_modules/.sensorium/` is gone afterwards; `sensorium ts run -- npm test` exits 2 with the direct form named; `sensorium ts run -- jest` exits 2.

- [ ] Recognition and wrapper tests first, then the driver; the live test on this box; commit: `feat(ts): sensorium ts run — harness recognition, the wrapper under node_modules/.sensorium, spawn, wait, ingest`.

---

### Task 7: The reader on TypeScript traces — vocabulary, refusal, `runs`, `info`, vectors, contract

**Files:**
- Modify: `src/sensorium/query/vocab.py` (`TYPESCRIPT`, `Terms.kind_labels`, `Terms.exceptions_refusal: str | None`, strict `terms()`), `src/sensorium/store/db.py` (`KNOWN_LANGS`, the refusal in `open_trace`), `src/sensorium/query/tree_cmd.py:149` and `frame_cmd.py:137` (`terms(trace).kind_labels.get(kind, kind)`), `runs_cmd.py` (`_header` reads `harness`/`harness_args` + `harness_exit`; `_row` prints `file: <test_file>` or `files: N` when present), `exceptions_cmd.py` (`_language_refusal` returns `terms(trace).exceptions_refusal`; the Rust arm unchanged), `info_cmd.py` (`typescript_lines(t, m)` after the interpreter line, gated on `t.lang == "typescript"` exactly as `rust_lines` is), `docs/TRACE-FORMAT.md` (§4 a TypeScript-only table, §5 `exc.kind` and `how` values, §6 the `file:` member, the vocabulary row), `docs/trace-format/VECTORS.md` (rows `v23`–`v29`), `tests/test_vocab.py` (a `TYPESCRIPT_VECTORS` scan with `FORBIDDEN_TS = FORBIDDEN + ("cargo", "Rust disposition", "toolchain:")`, `test_typescript_terms_name_what_a_typescript_trace_has`, the unknown-lang test).
- Create: `src/sensorium/query/info_typescript.py`, `docs/trace-format/vectors/v23-lang-typescript-prose.json` … `v29-runs-file-header.json`, `tests/test_ts_refusal.py` (a hand-built `lang: "cobol"` trace through `finalize_synthetic`: `Trace.open` raises `TraceFormatError` with the sentence, and `info`, `grep`, `tree` and `diff` through the real CLI all exit 2 with it — one choke point, four commands).

**Interfaces:**
- `TYPESCRIPT` fields as spec §6; `kind_labels = {"coroutine": "async", "async_generator": "async generator"}` (PYTHON and RUST: `{}`); `exceptions_refusal` = `"REFUSED: exceptions on a typescript trace needs the TypeScript disposition rules (S5 rung 2); the Python rules index exception identity this trace does not carry; nothing was judged"` (PYTHON: None; RUST: None — dispatched before the refusal).
- `db.open_trace`: after the format checks, `lang = get_meta(conn, "lang")`; `lang is not None and lang not in KNOWN_LANGS` → `TraceFormatError(f"{path} was written by {recorder} for lang {lang!r}, which this sensorium ({version}) has no vocabulary for ({', '.join(KNOWN_LANGS)}); upgrade sensorium to read it")`.
- `info_typescript.typescript_lines(trace, m)`: `harness: vitest run src/fog  exit: 1 (waited)`, `container: pid 4242  thread 0 (main)  file: src/fog/compute.test.ts`, `tests: 11 as tasks, 11 seen by the harness` (+ `; 2 registered through a shape the transform did not wrap` when they differ; + `; task names: vitest|title|mixed` + `, 1 conflict`), `files: 41 transformed; excluded: 3 (vitest-hoisted-factory)`, `unhandled rejections: N` (when non-zero, or zero on a complete trace), `throw flow outside frames: N` (when non-zero) — every line gated on its key.

**Invariants:** `v23` asks `info`, `tree`, `frame`, `runs`, `diff` and `exceptions` on a hand-built TypeScript trace and asserts the words `node v24`, `test`, `[async]`, `file:`, `exit:1 (waited)`, the refusal sentence at exit 3, and the ABSENCE of `asyncio`, `cargo`, `python ?`, `coroutine`, `Python's own`, `Rust disposition`; `v24` builds a `lang: "cobol"` trace and asserts `info` exits 2 with `no vocabulary for (python, rust, typescript)`; `v25`–`v29` as spec §5.3; the whole legacy suite green; `test_vocab.py`'s Rust scan unchanged and the TypeScript scan green over every `lang: typescript` vector and the six commands.

- [ ] Vectors first (they fail), then the reader; commit: `feat(query): the TYPESCRIPT vocabulary, the unknown-lang refusal, a lang-keyed runs header, info_typescript, vectors v23–v29`.

---

### Task 8: The TypeScript corpus and `run_corpus.py --program vitest`

**Files:**
- Create: `corpus/typescript/{package.json, package-lock.json, vitest.config.ts, README.md}` and the thirteen cases named in Task 1, each `<case>/<case>.test.ts` (+ a source file where the case needs one) and `questions.yaml`.
- Modify: `corpus/run_corpus.py` — `VITEST = "vitest"`, `TS_DIR = "typescript"`, `harness_args` in `ALLOWED_TOP_KEYS` and `Case`, `_question_files` adds `typescript/*/questions.yaml`, `_record_vitest(wd, sdir, harness_args)` (copy `corpus/typescript/` minus `node_modules`/`.sensorium`, symlink `node_modules`, run `python -m sensorium ts run -- npx vitest run <case>` with `SENSORIUM_DIR=sdir`), skip reason `NO_TS = "no corpus/typescript/node_modules (npm ci) or node < 24"`, `--require-driver` unchanged (any skip already fails it), and a new `--only-dir <name>` that runs one corpus directory (`rust`, `typescript`, or `.` for the Python cases) so a CI job can gate one recorder's cases with `--require-driver` while another recorder's driver is absent.

**Invariants:** every question pre-registers `why_logs_fail` naming which of `console.log`, `DEBUG=*`, a stack trace fails; every case's planted truth is stated; the count line reads `13 cases` for the TypeScript directory; the refusal cases pin the exact sentences (`flow --object` → `object_identity: false` at exit 3; `watch` → `line: false` at exit 3; `exceptions` → the TypeScript sentence at exit 3); `async_interleaved` pins two `.concurrent` tests' rows each under their own task; `each_naming` pins three tasks named by expanded titles; `unhandled_rejection_in_info` pins `unhandled rejections: 1`; `suspended_at_end` pins `~ suspended at L<n> at end of recording`; `timer_callback_parentless` pins a depth-0 frame inside the task with the tree's untraced-caller tag.

- [ ] Cases with truths first; the runner; green with `--require-driver`; commit: `feat(corpus): the TypeScript corpus — six ports, three refusals, four TypeScript-only cases`.

---

### Task 9: CI — the `typescript` job

**Files:**
- Modify: `.github/workflows/ci.yml` — a `typescript` job: `actions/setup-node@v4` with `node-version: 24`, `npm ci` in `typescript/`, `typescript/probes/` and `corpus/typescript/`, `npx tsc -p typescript/tsconfig.json`, `npm test --prefix typescript`, the probe checker through the driver (`SENSORIUM_TS_LIVE=1 python -m pytest -q tests/test_ts_live.py`), `python -m pytest -q tests/test_ts_ingest.py tests/test_ts_refusal.py tests/test_vectors.py tests/test_vocab.py`, `python corpus/run_corpus.py --require-driver` with `SENSORIUM_CARGO_SENSORIUM` unset **and** the Rust cases excluded by `--only-dir typescript` (add that flag: run one corpus directory) so the flag gates the TypeScript cases alone. `actions/cache@v4` on `~/.npm` keyed by the three lock files.

**Invariants:** the Python matrix jobs are unchanged and skip the TypeScript cases BY NAME; the job fails when the driver or `node_modules` is missing (the gate on the gate).

- [ ] Commit: `ci: the typescript job — tsc, node:test, the probes through the driver, the vectors, the corpus with --require-driver`.

---

### Task 10: The acceptance run — E0′–E11 and the §10 controls on the lens

**Files:**
- Create: `typescript/acceptance/{census.mjs, check_e3.py, sites.py, e6.sh, arms.sh, assemble.py, e5ts_split.sh, planted_change.sh}` — re-authored from the spike's instruments (shape, not source), each printing JSON with `{value, n, lens, dropped}` per measurement.
- Modify: the acceptance record §2 (pins re-taken), §3 (results), §4 (decisions), §5 (gaps).

**Invariants:** every endpoint computed by an instrument, never by hand; the arms interleaved plain/off/call ×5 with the load guard; `arms.sh` detached with `setsid nohup`, pid file + `.DONE` marker, killed by pgid on timeout; E6′ from the Task-0 manifest; E9's 20-name comparison against `e9.json`; E10 n=3; E11 both halves; E5-TS on `lens-split` (two functions of one VTT module moved to a new file), the planted change on `lens-swap` (two call sites swapped); every number written into §3 with its rule quoted, verdicts into §4 as the rules say (STOP stands where it fires; no re-roll).

- [ ] Instruments; dry run on `typescript/probes/`; the run; the record; commit: `test(acceptance): S5 rung 1 measured — E0'–E11 and the §10 controls on the VTT lens`.

---

### Task 11: Land it — README, CHANGELOG, versions, spec amendments, ledger, PR

**Files:**
- Modify: `README.md` (a `## TypeScript` section beside `## Rust`, the same shape: install, record, what it answers, what refuses, cost beside Python's and Rust's; the `--help` description of the top-level parser moves from "Record a Python program's execution" to "Record a program's execution (Python, Rust, TypeScript)"), `CHANGELOG.md` (a `0.9.0` entry in the file's style), `pyproject.toml` (`0.9.0`), the spec (§13-style deltas: P1–P11 and every measured number that moved a sentence, dated in place, nothing deleted), `docs/CARRIED-DEBT.md` (an S5 rung-1 section: settled → deferred with rulings → lessons; args capture, `exceptions` rules, `scheduled_by`, transform cache, the `.concurrent` naming hazard, jest), `typescript/HONESTY.md` (row references to the acceptance record's §4 cells).

**Invariants:** `sensorium --version` prints 0.9.0; the README's TypeScript numbers quote §3 of the acceptance record with n and lens; every deferral in CARRIED-DEBT names its ruling; the PR body carries the §4 verdicts; `git status --porcelain` of the lens copy's manifest set is unchanged (E6′ already proved it).

- [ ] Docs, versions, PR against `main`; origin sync verified after the push; commit: `chore(release): sensorium 0.9.0 — the TypeScript recorder, rung 1`.

---

## Self-review against the spec

- §2.1 driver → Task 6; §2.2 wiring → Tasks 4 and 6; §2.3 run model → Tasks 5–6 (`test_file`, `harness_exit`, `invocation.json`); §2.4 site identity → Task 2 (`qualname.mjs`) and Task 5 (root-relative fingerprint); §3.1–3.4 → Task 2 (goldens per rule) and Task 3 (naming); §4 → Task 3 (wire) and Task 5 (conversion); §5.1 keys → Task 5 (minus `pool`, P1); §5.2 capabilities → Task 5; §5.3 vectors → Task 7; §6 → Task 7; §7 → Task 1; §8 and §10 → Task 0 (pre-registration) and Task 10 (measurement); §9 → Tasks 2–8 by name; §11 versions → Task 11; D9's read-only refusal → Task 6; D10 jest → Task 6; D15 `err_flow: false` → Task 5.
- No placeholder: every task names its files, its interfaces and the test that pins each invariant; the verbatim blocks are the four wire-format surfaces (splices, records, the setup template, the wrapper config) and nothing else.
- Type consistency: `transformSource` returns `{code, map, manifest}` (Tasks 2, 4); `task(title, fn, flags) → [title, wrapped]` (Tasks 2, 3); `y(f, x, kind)` with `0|1` in the splice and `k: "await"|"yield"` on the wire (Tasks 2, 3, 5); `ingest_dir` returns `Summary` rows the driver prints (Tasks 5, 6); `typescript_lines(trace, m)` mirrors `rust_lines` (Task 7).
