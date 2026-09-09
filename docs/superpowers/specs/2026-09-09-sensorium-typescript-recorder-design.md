# Sensorium TypeScript recorder — S5 design

Date: 2026-09-09. Status: DRAFT for Brice's review. Program: S5 of the
sensor-suite program (`~/.claude/plans/if-you-were-to-lexical-clover.md`, S5
as rewritten 2026-09-08 when C/C++ was dropped). Design authority: Claude,
under the 2026-09-04 delegation ("you have design authority"); every design
decision below is Claude's, recorded with its cost if wrong (§12). What is
Brice's is scope, money, merges and anything destructive (§13).

Precedent, followed on purpose so the two records read side by side:
`2026-09-01-sensorium-rust-recorder-design.md` (the Rust recorder) and the
rung ladder it set. Evidence this design rests on:
`docs/superpowers/spikes/2026-09-08-typescript-mechanics-spike.md` — the
pre-registered mechanics spike, nine endpoints, every gate PASS, its §4
decisions carried here by number.

## 0. Provenance

Three rulings stand and are not re-argued:

- **Standing ruling (2026-08-20)**: multi-language support never compromises
  the Python core; the trace schema is a frozen contract (`docs/TRACE-FORMAT.md`,
  format 4); sibling recorders carry their own honesty ledger and their own
  `exceptions` rules; no "80% works" polyglot mode.
- **Brice, 2026-09-08**: S5 is a TypeScript sibling, not C/C++; the consumer
  is the VTT frontend, Node first, the browser second.
- **The spike's decisions (findings §4, all measured on the VTT frontend at
  commit `0091e97`, 372 test files, 4,278 tests, vitest 4.1.9, Node 24.16):**
  1. the trace unit under vitest is the test-file process (E0: 372 files,
     372 pids, one file per container);
  2. the async model is `AsyncLocalStorage` per task with `YIELD`/`RESUME`
     at every `await`, the frame stack per task and popped at `YIELD` (E3:
     100% of expected rows under node, jsdom and node:test, negative control
     0 leaked rows);
  3. GO on mechanics (E2 5,403/5,403 function-like nodes; E4 20/20 sites on
     the exact TypeScript line; E5 vitest green through a Vite plugin; E6
     byte-identical sources, no marker in any cache);
  4. the tier is a runtime gate and the transform runs every time (E1
     off/plain 1.058 ≤ 1.10; call/plain 1.131 on a 4-million-event suite);
  5. the reader needs a `TYPESCRIPT` vocabulary, a refusal for an unknown
     `lang`, a language-keyed `runs` header, and its own `exceptions` rules
     (E7, verbatim leaks: `python ?`, "asyncio task", `cargo`, "needs the
     Rust disposition rules");
  6. rung 2's err-flow scope is the five shapes E8 saw, plus the one shape
     Python and Rust do not have — an unhandled rejection, recorded outside
     every frame and task;
  7. not measured, so not claimed: jest, the browser, `--focus`/LINE,
     `refocus`, per-closure overhead, `eval`/`new Function`, generators.

What this document adds is everything the spike left open by name: the
product's shape (§2), the transformer's rules (§3), the runtime and wire
(§4), the contract additions (§5), the reader's changes (§6), the ledger
(§7), rung 1's pre-registered acceptance (§8), the tests (§9), the first use
(§10), the rungs (§11), and the decisions with their costs (§12).

## 1. Goal, scope, non-goals

**Goal.** An agent debugging the VTT frontend records one `vitest run`
invocation and asks sensorium's existing questions of it — `runs`, `info`,
`tree`, `frame`, `grep`, `diff`, and (rung 2) `exceptions` — with the honesty
contract the other two recorders carry: every answer is a function of the
trace, and the instrument never answers from data it does not have.

**In scope for rung 1.**

- TypeScript and JavaScript ES modules under the invocation's root (`.ts`,
  `.tsx`, `.js`, `.jsx`, `.mjs`), `node_modules` excluded; no hand
  annotation, no change to the consumer's config or dependencies. A
  CommonJS file (`.cjs`, or a `.js` Node loads as CommonJS under
  `node --test`) is excluded and counted: the runtime header is an `import`.
- Event kinds CALL, RETURN (with a captured value), YIELD/RESUME at `await`
  and `yield`, RAISE at `throw`, HANDLED at `catch`, frames with outcomes,
  tasks = tests.
- Harnesses: vitest (the consumer's; the gate) and `node --test` (measured;
  shipped). jest refused by name.
- `diff` on per-file traces, `diff --ignore-moves` across a file split.
- A TypeScript corpus, `typescript/HONESTY.md`, conformance vectors, a CI job.

**Out of scope for rung 1**, each declared as a capability or a ledger item:
argument capture (`locals: false`; rung 3 with the focus tier), LINE
(`line: false`), object identity (`flow --object` refuses), program output
(`output: false`; vitest owns the capture), threads and children (a worker
thread or a child process the program spawns records as its own container
with no link; `threads: false`, `children: false`), `refocus`
(`refocus: false`; rung 4), the browser substrate (rung 5, own spec), the
`exceptions` rules (rung 2, own design; the records ship now), a transform
cache (later; E1 says it is not needed to ship).

## 2. Architecture

Two artifacts: a Node **library** and the existing Python package, which
gains the **driver**, the **converter** and the reader changes of §6. There
is no Node command line (D1).

| Artifact | Kind | Job |
|---|---|---|
| `typescript/` — npm package `sensorium-ts`, private, ESM `.mjs` with JSDoc types, no build step, Node ≥ 24 (D2) | Node library | `src/transform.mjs` (TypeScript AST positions, `magic-string` edits, newline-free); `src/rt.mjs` (tasks, frame stacks, spools — imports only `node:` builtins); `src/vite.mjs` (the plugin, `enforce: 'pre'`); `src/setup.mjs` (the vitest setup file: task-name provider and test counter); `src/register.mjs` (the `node --test` loader hook). |
| `src/sensorium/ts/` | Python | `sensorium ts run` (the driver), `sensorium ts ingest` (the converter), the spool reader. |
| `src/sensorium/query/` | Python | The `TYPESCRIPT` vocabulary column, `info_typescript.py`, the unknown-`lang` refusal, the lang-keyed `runs` header. |

```
sensorium ts run [--tier off|call] -- vitest run src/fog
  │
  ├─ mints an INVOCATION id; writes $SENSORIUM_DIR/spool/<invocation>/invocation.json
  │  exports SENSORIUM_SPOOL, SENSORIUM_TIER, SENSORIUM_TS_ROOT, SENSORIUM_INVOCATION
  ├─ recognises the harness from the command (§2.2): vitest → writes
  │  <root>/node_modules/.sensorium/<invocation>.config.mts (user config + plugin +
  │  setup file), appends `--config <it> --root <root>`; node --test → prepends
  │  `--import <typescript>/src/register.mjs`
  ├─ spawns the command as typed, waits, records the harness's exit (waited)
  │    └─ every worker that imports an instrumented module boots rt.mjs and spools
  │       to <spool>/<pid>-<threadId>.jsonl; each vitest fork = one test file (E0)
  ├─ removes the wrapper config; runs `sensorium ts ingest <spool>` (parallel over
  │  spools): one trace per container → $SENSORIUM_DIR/traces/<run-id>.db,
  │  meta.invocation groups them, meta.test_file names each
  └─ exits with the harness's own status (`run` never applies the 0/1/2/3 table to itself)
```

### 2.1 The driver is Python (D1)

Recording a Rust program needed a Rust binary because cargo needs a wrapper
binary. Recording a Node program needs nothing of the kind: a Vite plugin
and a loader hook are files, and everything else the driver does — mint an
invocation, set environment, spawn, wait, convert, log the invocation —
already exists in the Python package for `sensorium run`. So the driver is a
`ts` namespace on the one command line an agent already uses, the converter
reuses `sensorium.store.db` (the schema's only home), and `refocus` (rung 4)
re-invokes the same command the way it re-invokes `cargo sensorium`. The
Node package stays a library that a later Node bin could wrap without
changing.

`sensorium ts run` takes the harness command **after `--`, as the user
types it** (`vitest run …`, `npx vitest run …`, `node --test src/`): the
Python recorder's own shape (`sensorium run -- pytest …`), not a new one.
The one flag before `--` is `--tier off|call` (default `call`; `off`
transforms and emits nothing — the control arm). There is no `--run-id`: an
invocation mints one run id per container, and a name for one of 372 would
name nothing. Everything after `--` is the harness's, unchanged, plus the
two flags §2.2 appends. The driver checks `node --version` before spawning
and refuses below 24 at exit 2 (the measured floor, D2).

### 2.2 Harness wiring (D9, D10)

**vitest** (recognised by a token `vitest`, `npx vitest`, `pnpm vitest`,
`pnpm exec vitest`, or a path ending in `/vitest`). The driver resolves the
root (`--root`/`-r` in the command, else the cwd) and the user's config
(`--config`/`-c` in the command, else vitest's own search order:
`vitest.config.*`, then `vite.config.*`, in the root), and writes a wrapper:

```ts
// <root>/node_modules/.sensorium/<invocation>.config.mts
import { mergeConfig } from 'vitest/config';
import base from '<abs user config>';                 // omitted when none exists
import sensorium from '<abs typescript>/src/vite.mjs';
export default mergeConfig(base, { root: '<root>', plugins: [sensorium()],
  test: { setupFiles: ['<abs typescript>/src/setup.mjs'] } });
```

A user config exported as a function is called with vitest's own
`ConfigEnv` before the merge. The wrapper lives under `node_modules/` so
that bare imports (`vitest/config`) resolve from the consumer's tree; it is
never a source file, it is gitignored by every project, and it is removed
in a `finally`. The user's
`--config`/`--root` are consumed and re-issued as `--config <wrapper>
--root <root>`. `setupFiles` are **appended** to the user's, never replaced
(the spike's note: the consumer's setup assumes jsdom, and that is the
consumer's business). `npm test`, `pnpm test` and `yarn test` are refused at
exit 2 naming the direct form: a package script cannot take the appended
flags, and guessing what the script runs is a guess.

**node --test** (recognised by a token `node` with `--test` among its
arguments): the driver prepends `--import <typescript>/src/register.mjs`.
The hook transforms files under the root and type-strips with the
consumer's own TypeScript (`ts.transpileModule`), exactly as measured.

**Anything else** is refused at exit 2 naming the two harnesses. jest is
named in the refusal as unsupported (the spike did not measure it and the
consumer does not run it).

### 2.3 The run model (D3, D8)

- **The harness stays the runner.** The driver spawns the command the user
  typed; it never re-implements a harness's CLI.
- **One trace per container.** A container is `(pid, threadId)`: under
  vitest's default `forks` pool that is one forked child per test file
  (E0), under a `threads` pool it is one worker thread, and under `node
  --test` it is the process. Each container spools to its own file, so
  per-container identity holds by construction, and `diff`, `incomplete`,
  `main_thread_ident` and `exit_status` stay the per-process concepts every
  reader already has.
- **`meta.invocation` groups the traces**, `meta.test_file` names each:
  the setup file runs at the start of every test file and records a
  `FILE_START {path}` with `expect.getState().testPath`, root-relative.
  Exactly one such record makes `test_file`; a container that ran several
  (a reused worker) carries `test_files` instead and `runs` prints `files: N`;
  a container that ran none — a `globalSetup` in the main process, or any
  `node --test` process — is listed by its argv. `runs` prints one group per
  invocation with `file: src/fog/compute.test.ts` per member (§6).
- **Exit status is per container and unwitnessed.** The driver waits for
  the harness, not for its workers, so every container carries
  `exit_status: null`, `exit_status_basis: "unwitnessed"` — never the
  harness's number wearing a worker's name (the Rust D4 rule). What the
  driver DID witness is written where it was witnessed: `harness_exit:
  {status, signal, basis: "waited"}` on every trace of the invocation, and
  `runs`' header prints it (`vitest run src/fog  exit:1 (waited)`) — a
  claim the Rust header does not make only because cargo's traces do not
  carry one.
- **The invocation's own record** (`invocation.json`, then `harness.json`)
  lives beside the spools: harness, args, root, cwd, the driver's env hash,
  the wrapper path, walls, the exit. `ingest` is deterministic and
  re-runnable over a spool directory, so a driver killed between the
  harness's exit and the conversion leaves nothing that cannot be finished.

### 2.4 Site identity (D14)

`code_objects.file` is **absolute** (the contract's `co_filename` rule);
the fingerprint hashes the **root-relative** path, as the Python recorder
does (TRACE-FORMAT §7), so `diff --ignore-moves` pairs across a file split
exactly as it does for Python and Rust. `firstlineno` is the TypeScript line
of the function's first token, preserved because no edit inserts a newline
(E4 20/20).

`qualname` is the **file-local** path in the shape JavaScript's own tools
print, and nothing Python-only is borrowed:

| Shape | qualname |
|---|---|
| declaration, method, constructor | `compute`, `Fog.compute`, `Fog.constructor` |
| accessor | `Fog.radius` for both the getter and the setter — two rows, told apart by `firstlineno` |
| function assigned to a binding, property, class field, or `module.exports.x` | the binding's name (`onClick`, `Store.reset`) |
| `export default function`/arrow | `default` |
| nested function | `outer.inner` (no `<locals>`: that is Python's ceremony, and Node's stack traces print the bare name) |
| inside a `namespace`/`module` block | `ns.fn` |
| a function with no name and no binding (a `.map(x => …)` callback, an IIFE) | `<anonymous>` — Node's own word — with **no ordinal**: an ordinal would move every later anonymous function's key when one is inserted above it, which is exactly the move-fragility `--ignore-moves` exists to absorb. Rows stay distinct (interning is per site, TRACE-FORMAT §3); two anonymous functions on ONE line share a fingerprint key and are a declared blind spot (§7), the Rust "cfg-gated twins" precedent |

## 3. The transformer

Pure: source text + file path + root → edited text + source map + a
per-file manifest (`{file, sha256, instrumented: [{qualname, line, kind}],
excluded: {reason: count}}`). No I/O. Positions come from the TypeScript AST
(`createSourceFile`, the consumer's own `typescript`, resolved from the
root's `package.json` — E4 rests on the consumer's compiler parsing the
consumer's code); edits are `magic-string` splices; **no edit contains a
newline**, so every output line is the input's. The source map is returned
to vitest (a `hires` map) so a failing assertion's column is the original's
too.

### 3.1 Functions (measured E2, E4)

Every function-like node with a body — `FunctionDeclaration`,
`FunctionExpression`, `ArrowFunction`, `MethodDeclaration`, `Constructor`,
`GetAccessor`, `SetAccessor`, `async` and generator forms, TSX components —
is wrapped:

```
{ const __sf = __srt.call(__sfile, <idx>); try { <body> ; __srt.ret(__sf, undefined) }
  catch (__se) { __srt.thr(__sf, __se); throw __se } }
```

An expression-bodied arrow becomes a block returning `__srt.ret(__sf, (<expr>))`;
every `return <expr>` becomes `return __srt.ret(__sf, (<expr>))`. Two rules
the spike bought with defects: two closing insertions at one offset are
spliced **innermost first** (`prependRight`), and nothing inside a
`vi.mock`/`vi.doMock`/`vi.hoisted`/`vi.unmock` factory is instrumented
(vitest hoists those above every import, our header included) — the count
of such functions is a named exclusion. Excluded by rule, each counted under
its reason: overload signatures, `declare`d and `abstract` members (no
body). Not touched, declared in the ledger: `eval` and `new Function` bodies.

`frames.kind` is `function`, or `coroutine` for an `async` function,
`generator` for `function*`, `async_generator` for `async function*` — the
contract's enumeration, unchanged; what the reader PRINTS for them is the
vocabulary's (§6: `[async]`, `[generator]`, `[async generator]`).

### 3.2 Suspension (measured E3 for `await`; `yield` added, D5)

`await X` → `__srt.r(__sf, await __srt.y(__sf, (X)))`: a YIELD record before
the frame parks, a RESUME after it continues. `yield X` and `yield* X`
inside a generator take the same form (the value flows through `y` and `r`
untouched). The runtime pops the frame at `y` and pushes it at `r`, which is
what keeps a fan-out's siblings from nesting under each other (E3 S2) and
what makes a frame whose promise never settles read `suspended at end of
recording` rather than `(open)`.

### 3.3 Throw flow records (measured E8; the rules are rung 2's)

`throw X` → `throw __srt.raise(__sf, (X), <line>)`; a `catch` clause gains
`__srt.handled(__sf, <e>, <line>[, how])` as its first statement (a clause
with no binding is given one); a `.catch(() => {})` whose callback body is
empty is wrapped so the callback records a HANDLED. `how` is `catch`,
`sink_empty_catch` (an empty clause) or `sink_empty_catch_callback` — the
word `how` and the `sink_` prefix are the Rust wire's, reused. A rethrow
carries the SAME serial (identity is a `WeakMap` on the thrown object, §4),
so `catch (e) { throw e }` is one exception with two RAISE rows, a hop and
not a sink. `finally` records nothing (rung 2 decides whether it should).

### 3.4 Tests as tasks (measured E0/E3; the naming is D4)

A call whose callee is `test` or `it` — or a member chain rooted at one
(`test.each(table)(title, fn)`, `it.skip`, `test.only`, `test.concurrent`,
`test.fails`, `test.todo`) — has its **function argument** wrapped:
`__srt.task(<title expr>, fn)`. `describe`/`suite` calls (and their chains)
are wrapped the same way with `__srt.describe(<title expr>, fn)`, which
pushes the title while the collection callback runs, so a task registered
inside it knows its lexical chain at registration time. The title is passed
as the **expression**, evaluated: a template or a variable is a string at
runtime, and `<unnamed: title not a string>` only when it is not. The spike
wrapped literal callees only and left 120 of 4,278 tests outside any task
(all `.each`); this closes that by rule, and E9 (§8) measures it.

Hooks (`beforeEach`, `afterAll`, …) are not tasks: their frames run in no
task and are compared as the thread stream, in order, which is what they are.

## 4. The runtime (`rt.mjs`) and the wire

- **Tier gate.** `SENSORIUM_TIER=off` compiles the same edits and emits
  nothing (E1: the whole cost of `off` is the transform, 1.058); `call`
  records everything in this document. The tier is read once at boot.
- **Tasks.** `__srt.task(title, fn)` returns a wrapper that runs `fn` inside
  `als.run(task, …)` — one `AsyncLocalStorage` store per activation — and
  every continuation (microtask, timer, jsdom timer, emitter callback fired
  from a timer) lands in that task (E3, three environments, negative control
  0 leaked rows). Each task owns a frame stack; frames running in no task
  use the container's root stack.
- **Task names (D4).** The vitest setup file registers a name provider:
  `__srt.nameProvider(() => expect.getState().currentTestName)`. A task
  takes the provider's name — vitest's own full title, `describe > test`,
  `.each` rows expanded exactly as vitest prints them — and cross-checks it
  where the transform passed a plain string literal that is not a `.each`
  template: a provider name that does not end with that literal falls back
  to the lexical `describe > title` and is counted in `task_name_conflicts`
  (the documented hazard: the global `expect` state is shared across
  `.concurrent` tests; a `.concurrent.each` misnaming is therefore
  uncheckable, and the ledger says so). Without a provider
  (`node --test`) the lexical name is the name. The k-th activation of one
  registration in a container (a `retry`, a `repeats`) is `<name>#k` for
  k ≥ 2. `task_name_basis` in meta says which rule named this trace's tasks.
- **Frames.** `call` pushes on the current stack and records the parent as
  the frame beneath it; `ret`/`thr` pop. A continuation that runs when its
  task's stack is empty — a timer callback, a promise reaction whose
  scheduler has yielded — opens a **parentless** frame at depth 0 in its
  task with `caller: "untraced"` in the CALL payload: the truthful answer
  (Node's timer machinery called it), and the same answer the Python recorder
  gives a coroutine entered by the event loop (async design 2026-08-21: "main
  created the task, the loop entered it"). Which frame SCHEDULED it is a
  different relationship, not recorded in rung 1 (§12 D5's cost).
- **Values.** RETURN carries `{"k": "dbg", "v": util.inspect(v, {depth: 2,
  maxArrayLength: 8, maxStringLength: 100, breakLength: Infinity}), "trunc"}`
  capped at 200 bytes; a formatter that throws reads `{"k": "unread"}`;
  `undefined` is the text `undefined`, never absent. Arguments are not read:
  every CALL carries `unread: ["locals"]` (rung 3 adds an args tier under
  `--focus`, D12).
- **Exceptions.** `fmtExc(e)` → `{kind, type, msg, serial}`: `type` is the
  constructor name or `typeof` for a primitive, `msg` is `e.message` or
  `String(e)`, `serial` is minted once per object through a `WeakMap` (a
  rethrown object keeps it; a primitive gets a fresh serial every time — a
  rethrown string cannot be followed, ledger item). `kind` is `throw` for a
  thrown value and `rejection` for a value that arrived as a promise
  rejection (the `.catch` sink, the process listener). Every `exc` object
  this recorder writes carries `kind`, because the contract reads a kindless
  `exc` as Python's (TRACE-FORMAT §5).
- **Unhandled rejections (D7).** `process.on('unhandledRejection')` writes
  an `UNHANDLED` record — `{exc}`, no frame, no task. The converter puts it
  in meta `unhandled_rejections: [{type, msg, serial}]`, **never** into
  `events`: a causal event with no `code_id` is refused by the contract
  (`causal_stream` looks the code up unconditionally), and a synthetic code
  object would put a site in the program that has none. Where the reason
  object was thrown by traced code its serial matches the RAISE that threw
  it, and rung 2 reads that as `uncaught (unhandled rejection)`; a serial no
  event carries was born outside traced code or by a `reject()` call, and is
  reported as exactly that.
- **Spools and loss.** One JSONL file per container, `<pid>-<threadId>.jsonl`,
  wire version 1 in the BOOT record; ~98 bytes per line, ~174k lines/s
  (E0). Records are buffered and flushed after every task, every 100 ms, on
  `exit`, `beforeExit`, `SIGTERM`/`SIGINT`/`SIGHUP`, and the EXIT record is
  the last line. A container killed by `SIGKILL` (vitest's teardown timeout)
  loses at most the unflushed tail and its EXIT: the converter marks it
  `incomplete: true`, `info` prints the INCOMPLETE banner, `diff` refuses —
  and no `records_dropped` is written, because the runtime cannot know the
  count. E11 (§8) pins both behaviours.
- **Records:** BOOT `{wire, pid, ppid, threadId, isMainThread, argv, cwd,
  env, envHash, node, tier, startTs}` · FILE `{id, path, sha256, codes:
  [[qualname, line, kind]…]}` · TASK `{id, name, basis}` · CALL `{f, p,
  file, c, t}` · RETURN `{f, t, v}` · UNWIND `{f, t, x}` · YIELD/RESUME
  `{f, t}` · RAISE `{f, t, x, l, how}` · HANDLED `{f, t, x, l, how}` ·
  UNHANDLED `{x}` · FILE_START `{path}` and SEEN `{name}` (the setup file's
  per-file and per-test records; `tests_seen` is the SEEN count) ·
  EXIT `{code, endTs}`. `env_hash` is sha256 over sorted `k=v` lines, the
  Rust recorder's recipe — comparable within this language only.

## 5. The contract: `docs/TRACE-FORMAT.md`, format 4

No column changes; `TRACE_FORMAT` stays 4. What this recorder adds is a
third `lang`, new values for existing keys, and TypeScript-only meta keys.

### 5.1 Meta

Required set: unchanged and all written. `recorder: "sensorium-ts 0.1.0"`;
`lang: "typescript"` (`.js` files under the root are instrumented too; the
tag names the consumer's language, and the README says so);
`main_thread_ident: 1`; `fingerprint_basis: "per-task"`; `source_hashes`
keyed by absolute path (sha256 of the ORIGINAL source, from the transform's
manifest); `exit_status: null` with `exit_status_basis: "unwitnessed"`
(§2.3). Shared optional keys written: `env`, `caps`.

**TypeScript-only keys**, printed only where present (the Rust rule):

| Key | Meaning, and what reads it |
|---|---|
| `invocation`, `harness` (`"vitest"` / `"node-test"`), `harness_args` | The command the traces came out of. `runs`: `invocation <id>: vitest run src/fog`. |
| `harness_exit` `{status, signal, basis: "waited"}` | The driver waited for the harness. `runs`' header and `info` print it with its basis; a member's own exit stays `unwitnessed`. |
| `pid`, `ppid`, `thread_id_os`, `is_main_thread` | The container. |
| `test_file` / `test_files` | Root-relative path of the one test file this container ran (`runs`: `file: <it>` in place of the argv), or the list when a container ran several (`runs`: `files: N`). Both absent on a container that ran none. |
| `node`, `vitest`, `pool`, `environment` | `info`'s interpreter line is `node v24.16.0 (vitest 4.1.9, forks, jsdom)`. |
| `tests_seen`, `task_name_basis`, `task_name_conflicts` | Tests the setup file counted against tasks the transform opened; `info`: `tests: 11 as tasks, 11 seen by the harness` and, when they differ, the shortfall named as tests registered through a shape the transform did not wrap. |
| `unhandled_rejections` | `[{type, msg, serial}]`; `info` prints the count when non-zero or when the trace is complete (the listener always runs, so a zero on a complete trace is a measured zero). |
| `files_transformed`, `transform_excluded` `{reason: count}` | Coverage as the transform saw it; `info`: `files: 41 transformed; excluded: 3 (vitest-hoisted factory)`. |
| `wire`, `driver_version` | Identity of what wrote the spool and what converted it. |

### 5.2 Capabilities (rung 1)

```
line: false, locals: false, return_value: true, tasks: true, threads: false,
children: false, stdin: false, output: false, object_identity: false,
refocus: false, err_flow: false
```

`err_flow: false` although RAISE/HANDLED rows exist: the key is the
runtime's statement that its records carry what the `exceptions` rules
need, and no TypeScript rules exist yet — the Rust rung-2 precedent (panics
as RAISE under `err_flow` absent). Rung 2 flips it with the rules, and a
rung-1 trace is then refused by `exceptions` at exit 3 with the capability
sentence, naming the recorder.

### 5.3 Enumerations and vectors

- `lang`: `python`, `rust`, **`typescript`**. `vocab.terms()` **refuses** a
  fourth (§6); vector `v23-lang-typescript-prose` pins the absence of every
  Python and Rust word from every command's output on a TypeScript trace,
  and `v24-unknown-lang-refused` pins the refusal.
- `exc.kind`: `err`, `panic`, **`throw`**, **`rejection`**. Vector
  `v25-exc-kind-throw-rejection`.
- `payload.how` on RAISE/HANDLED: `throw`, `catch`, `sink_empty_catch`,
  `sink_empty_catch_callback` (rung 2 adds what it needs). Same vector.
- `frames.kind` printed labels per language: vector `v26-kind-labels`
  (`[async]` on a `coroutine` frame of a TypeScript trace; `[coroutine]`
  unchanged on Python's).
- `unhandled_rejections` in meta, never in `events`: `v27-unhandled-rejection-in-meta`.
- `exit_status` null + `harness_exit` waited, both printed: `v28-harness-exit-waited`.
- `test_file` in `runs`: `v29-runs-file-header`.

## 6. Query-layer changes

- **A `TYPESCRIPT` column in `vocab.py`** (D13). Every field filled in the
  recorder's own words: unit of work `test`/`tests`, article `a`,
  `stream_scope` "tests", `harness_thread` None (vitest runs each test on the
  container's own thread), `unnamed_task` "(unnamed: title not a string)",
  `thread_origin` "as worker threads or forked children of the harness (not
  witnessed: each is its own trace)", `default_name_note` None, `no_rerun_note`
  "no rerun was attempted; this recorder records one tier and has no deeper
  capture to re-run for (S5 rung 3)", `timeline_hint` "this recorder produces
  no LINE events (capabilities.line: false); per-line capture is S5 rung 3",
  `interp_key`/`interp_fmt` `node` / `node {}`, and the four language-naming
  blind-spot lines rewritten for "TypeScript and JavaScript files under the
  invocation's root that the transform edited" / "any container the program
  spawned itself" / "node_modules, Node's own modules, vitest, and every
  file the transform excluded" / "capturing values runs the program's own
  `inspect` customisations". One new field on `Terms`, **`kind_labels`**
  (`{coroutine: "async", async_generator: "async generator"}`; identity for
  Python and Rust), read by `tree_cmd.frame_line` and `frame_cmd` where
  they print `[{kind}]`.
- **`terms()` refuses an unknown `lang`** instead of falling back to
  `PYTHON`: `error: <run> was written by <recorder> for lang "<x>", which
  this sensorium (0.9.0) has no vocabulary for (python, rust, typescript);
  upgrade sensorium to read it`, exit 2 — the newer-format refusal's shape,
  because the recording is fine and the reader is what is old. The Python
  default for a trace with NO `lang` key is unchanged (it predates the key).
- **`runs`.** The header reads `harness` + `harness_args` when present
  (`invocation <id>: vitest run src/fog  exit:1 (waited)`), and keeps
  `cargo` + `cargo_args` for a trace that carries those; a member with
  `test_file` prints `file: <path>` where a Rust member prints `cmd:`.
- **`info`.** `info_typescript.py` beside `info_rust.py`: the harness line,
  the container, `tests:`/tasks, transform coverage, unhandled rejections,
  the declaration block — every line gated on its key, never on the
  language.
- **`exceptions`.** `_language_refusal` becomes lang-keyed through the
  vocabulary: the TypeScript sentence is `REFUSED: exceptions on a
  typescript trace needs the TypeScript disposition rules (S5 rung 2); the
  Python rules index exception identity this trace does not carry; nothing
  was judged` at exit 3. The Rust arm is already dispatched; the sentence
  for a FOURTH language names the language it was asked about, never Rust.
- **`tree`/`frame`/`grep`/`diff`** answer unchanged (E7: the structural
  commands already do). `watch`/`flow`/`refocus` refuse on the declared
  capabilities, unchanged.

## 7. The TypeScript honesty ledger: `typescript/HONESTY.md`

Written before the runtime, one section per promise, each row naming what
could falsify it (a test, a corpus case, a vector, an endpoint), in the
Rust ledger's two-column shape (`rust/HONESTY-INDEX.md`):

1. Outcomes: a frame closes `return` with a `dbg` value or `unwind` with
   the thrown value; a frame parked at end of recording reads `suspended`.
2. Tasks: every test callback the transform wrapped is a task named by
   vitest's own full title where a provider ran, the lexical title
   otherwise, `#k` on repeats; the basis is in meta; conflicts are counted.
   Hooks are not tasks. Tests the transform did not wrap are counted
   (`tests_seen` − tasks) and named by shape.
3. Attribution: every continuation lands in the task that started it
   (E3, negative control); a continuation entered with an empty stack is
   parentless, and the scheduling frame is NOT recorded.
4. Throw flow: RAISE at `throw` statements only (a `reject()` is not a
   throw and records nothing until rung 2), HANDLED at `catch` clauses and
   the empty-callback sink; a rethrown OBJECT keeps its serial, a rethrown
   primitive does not; an unhandled rejection is meta, not an event.
5. Loss: a SIGKILLed container is `incomplete` with an unknowable tail;
   nothing is ever written as `records_dropped`.
6. Exit: `unwitnessed` for every container, `harness_exit` for the
   invocation, never one wearing the other's name.
7. Scope: files under the root the transform edited; `node_modules`,
   `.d.ts`, `eval`/`new Function` bodies and vitest-hoisted factories are
   outside it, and the excluded count is in meta.
8. Preserved by construction, tested: line numbers, source-map columns,
   the plain run's sources and caches, the consumer's config.
9. Cost is a reported fact, never a gate.
10. Blind spots, numbered: same-line anonymous twins share a fingerprint
    key; a `.catch(fn)` with a non-empty body is not seen; `finally`
    records nothing; a worker thread or child process the program spawns
    is its own unlinked container; `.concurrent` tests may misname through
    the global `expect` state (counted); default-parameter throws happen
    before the frame opens; top-level module code runs unframed; a
    generator driven by `yield*` runs its inner frames parentless; an
    `async` describe callback registers its tests after the lexical chain
    has popped (provider names are unaffected; lexical ones lose the chain).

## 8. Pre-registered endpoints for rung 1 (product acceptance)

Written here before the product exists; the plan carries them verbatim and
the acceptance record quotes each rule beside its number. **Lens:** the
spike's — the VTT frontend copy at `0091e97` under
`/mnt/extra/sensorium-s5/vtt/`, vitest 4.1.9, Node 24.16, this box, store
under `/mnt/extra`, nothing on the root disk. **Control arm:** the spike's
instrument on the same lens (its numbers below are that arm). Stop rules as
the spike's: 1-minute load above 4.0 → wait; an arm with fewer than 5 runs
or a suite not at 372/4278 → `value: null`, named in `dropped`; no endpoint
re-run after its number is read.

| Id | Question | Measurement | Rule | Derivation |
|---|---|---|---|---|
| E0′ | Is the trace unit still the test file under the product? | containers, files per container, full suite at tier `call` | 372 containers, one file each; any container with two files or any file with none → STOP | E0's measured shape, now a claim |
| E1′ | What does the product cost? | walls n=5 per arm, interleaved plain/off/call, conversion excluded | off/plain ≤ 1.10 → the transform stays uncached; above → a cache keyed on source sha becomes rung-1 work, not a NO-GO; call/plain reported beside the spike's 1.131 | E1's bound, reused; the product adds a setup file, a name provider and the `yield` rewrite, none of which the spike had |
| E2′ | Does the transform still cover the consumer? | instrumented / eligible over the census set, per node kind, with every exclusion named | after removing NAMED kinds the ratio is 1.000 (5,403 of 5,403 was measured); one unnamed miss → STOP | a measured 100% may not regress silently |
| E3-TS | False DIVERGED? | one pre-named VTT test file recorded 20 times; `diff` each against the first | DIVERGED 0/19 and REFUSED 0/19; any → the comparator or the recorder is wrong, STOP | the Rust E3 rule, per-task basis |
| E4′ | Do sites keep their lines and columns? | the 20-shape probe under the product transform; one planted failing assertion's line and column as vitest reports it, instrumented against plain | 20/20 on the exact line; the report byte-identical; a miss is a regression of a measured 20/20 → STOP | E4, tightened from 19/20 because the number is now known |
| E5′ | Do both harnesses run? | the full suite under `sensorium ts run -- vitest run` (gate); the E3 probe under `-- node --test` | 372/4278 green and `node --test` green with its rows; a red vitest is NO-GO | E5 |
| E6′ | Is a plain run contaminated? | sha256 manifest before/after, plain counts after, marker grep of every cache dir, listing of `node_modules/.sensorium` after | manifest identical, 372/4278 inside the plain band, 0 markers, the wrapper directory gone | E6, plus the wrapper's removal |
| E7′ | Does the reader speak this recorder's words? | every command run on a product trace; transcript grepped for `asyncio`, `python ?`, `cargo`, `coroutine`, `Python's own`, `threading/_thread`, `Rust disposition`, `sensorium run --focus` | 0 occurrences; plus `v23`/`v24` green | E7's leak list, now a gate |
| E8′ | Are the five swallow shapes still seen? | the swallow probe | 5/5, reported per shape; rung 2 gates the rules | E8 |
| E9 | Are tests tasks, and named as vitest names them? | `tests_seen`, tasks, `task_name_conflicts` over the full suite; a sample of 20 task names against `vitest --reporter=json` full names | tasks = tests_seen (4,278) and conflicts = 0 → PASS; a shortfall is named by shape and STOPs above 1% | the spike's gap was 120/4,278 = 2.8%, all one shape, closed by rule in §3.4 |
| E10 | What does conversion cost? | `ingest` wall over the full-suite spool set (parallel), and over one file | reported; full-suite ingest ≤ the plain wall (22.08 s) → the converter stays in Python; above → design input: a Node converter on `node:sqlite` or a binary wire | Rust's converter did 132k events in 1.2 s; 4.1M events is ×31, so the bound is the suite's own wall, not Rust's number |
| E11 | Is the loss model honest? | (a) a probe test whose promise never settles under vitest's timeout; (b) a worker SIGKILLed mid-file | (a) the frame reads `suspended at end of recording` and the trace is complete; (b) `incomplete: true`, INCOMPLETE banner, `diff` refuses at exit 3; anything else → STOP | §4's loss model, both halves |

**Reported without a gate:** bytes per line and lines per second under the
product runtime; vitest's `transform` seconds per arm; output/input size;
`info` and `diff` latency on the largest file trace; the count of DIVERGED
pairs when two full-suite runs are `diff`ed file by file (a non-zero names
a nondeterministic test, which is a finding about the consumer).

## 9. Testing story

- **Transform goldens** (`typescript/test/golden/*.ts` → `*.expected.ts`):
  byte-exact, one per rule in §3, `lines(out) == lines(in)` asserted on
  every golden; a property test that the output parses.
- **Runtime tests** (`node:test`): task isolation across `als.run`, the
  stack pop/push at `y`/`r`, `WeakMap` serial reuse on rethrow, `dbg` caps
  and the throwing formatter, flush on every terminal path, the
  `unhandledRejection` record.
- **Probe project** (`typescript/probes/`: a tiny vitest project with jsdom
  and node files, the E3/E4/E8 probes from the spike, a `.each` file, a
  `.concurrent` file, a never-settling test, a `describe` chain): run
  through the real driver in CI.
- **Converter tests** (Python): spool → trace through `db.create_trace`;
  `missing_required` empty on every complete spool; a truncated spool →
  `incomplete`; `unhandled_rejections` lands in meta and never in `events`;
  fingerprint basis per task; `harness_exit` written on every member.
- **Vectors** `v23`–`v29` (§5.3) through the real CLI, as every vector is.
- **Corpus** `corpus/typescript/<case>/` with a shared `package.json`
  (vitest, typescript) and `program: vitest` + `harness_args` in
  `questions.yaml`, run by `run_corpus.py` through the driver; ports that
  need no `exceptions`: `double_call`, `pass_vs_fail`, `wrong_branch`,
  `nondeterministic`, `unit_mismatch`, `async_interleaved` (two
  `.concurrent` tests, attribution); refusal cases: `flow --object`,
  `watch`, `exceptions`; TypeScript-only: `each_naming`,
  `unhandled_rejection_in_info`, `suspended_at_end`, `timer_callback_parentless`.
  `--require-ts` makes a missing driver a failure in the job that has one.
- **CI**: a `typescript` job — Node 24, `npm ci` in `typescript/` and
  `corpus/typescript/`, `tsc --noEmit --checkJs`, the runtime and golden
  tests, the probe project through the driver, the Python vectors and
  converter tests, the corpus with `--require-ts`. The Python matrix gains
  nothing that needs Node (the TypeScript cases skip BY NAME there, as the
  Rust ones do).

## 10. First use

Two invocations of the consumer's own suite, then the question the tool
exists for:

```
sensorium ts run -- vitest run                 # A
sensorium ts run -- vitest run                 # B
sensorium runs                                 # two groups, 372 files each
sensorium diff <A:src/fog/compute.test.ts> <B:same>   # MATCH, per file
sensorium tree <A:one file> --depth 3          # tests as task groups
sensorium frame <run> --fn compute             # one activation, return value
```

Expected: every same-file pair MATCH (E3-TS at invocation scale, reported),
`tree` grouping by test, `info` naming the harness and the file. Then two
controls on a throwaway copy of the lens, both gated (the Rust E5 shape):

- **E5-TS, the split.** Two functions of one VTT module moved to a new
  file, nothing else changed; record the test file that exercises them.
  Plain `diff` reads DIVERGED at the first moved function (the fingerprint
  hashes the file); `diff --ignore-moves` reads `MATCH modulo location` with
  exactly those two code objects in `moved:` and every task paired by name.
  Anything else → STOP: the verifier cannot see through a move.
- **The planted change.** Two call sites swapped in one VTT function →
  `diff` DIVERGED naming the step. A MATCH voids the verifier and STOPs.

## 11. Order of work (rungs)

0. **Mechanics spike** — DONE 2026-09-08, every gate PASS (findings §4; code
   parked on `spike/typescript-mechanics`, never merged).
1. **Recorder v1** — this document. Plan: writing-plans next. Versions:
   `sensorium-ts 0.1.0`, Python **0.9.0** (a new verb, a third vocabulary,
   the refusal, seven vectors). Acceptance: §8, §10.
2. **Throw flow** — `exceptions` on a TypeScript trace: Python's five
   dispositions on JavaScript shapes (an empty catch and an empty callback
   are sinks, a rethrow is a hop, an unhandled rejection is `uncaught` with
   its basis, `finally` and `.then(_, onRejected)` decided), `err_flow:
   true`, the swallow corpus. Own design doc; the falsifier is zero false
   SWALLOWED on the corpus and on the lens (the Rust E6 shape).
3. **Tiers** — `--focus <qualname>`: argument capture and one LINE per
   completed statement with the bindings it wrote (the Rust focus design,
   transferred), `watch`/`flow`; measured cost per tier. Own design doc.
4. **Refocus** — `sensorium ts run --refocus-of <run>`, the licence over
   `source_hashes`, env and `harness_exit`; the multi-container refusal.
5. **Browser** — the runtime without a filesystem, a collector, tasks that
   are not tests. Own spec; nothing here assumes it.
6. **Later** — a transform cache keyed on source sha (E1 says not needed to
   ship); paging in `runs`; batch `diff` across an invocation; a Node bin
   wrapping the driver for a Python-less consumer.

## 12. Decisions, with what each costs if wrong

| # | Decision | Cost if wrong |
|---|---|---|
| D1 | The driver and converter are Python (`sensorium ts run`/`ingest`); Node is a library | a Python-less consumer needs a Node bin later — the library is written so one can wrap it without changing it |
| D2 | One private npm package, ESM `.mjs` + JSDoc, `tsc --checkJs`, no build, Node ≥ 24 (the measured version) | an older-Node consumer is refused by the driver before anything is spawned, naming the floor; widening it is a measured slice |
| D3 | Trace unit = container `(pid, threadId)`; `test_file` names it | a `threads` pool shares a pid across traces; every reader is per-trace so nothing merges wrongly |
| D4 | Tasks named by vitest's own `currentTestName` through a setup-file provider, cross-checked against the lexical title, conflicts counted; lexical names under `node --test` | if `expect.getState()` is unavailable or wrong, the fallback names every task lexically and `task_name_basis` says so; nothing is misnamed silently |
| D5 | A continuation entered with an empty stack is parentless with `caller: "untraced"`; the scheduling frame is not recorded | `tree` shows timer callbacks at depth 0 inside their task (the spike's `tree` already does, and it read fine); a `scheduled_by` key is additive when a rung wants it |
| D6 | JSONL wire v1; the converter in Python, parallel over spools; E10 bounds it | E10 above the plain wall moves the converter to Node or the wire to binary — a design input pre-committed in §8 |
| D7 | Unhandled rejections are meta, never events; `exc.kind ∈ {throw, rejection}`; `how` reuses the Rust word | rung 2 wants an event for them → it mints one with a real code id from the matching RAISE's serial, which meta preserves |
| D8 | `exit_status` unwitnessed per container; `harness_exit` waited on the invocation and printed | none of substance: both facts are written where they were witnessed |
| D9 | The vitest wrapper config lives under `<root>/node_modules/.sensorium/`, appends to `setupFiles`, is removed after the run | a read-only `node_modules` → the driver refuses at exit 2 naming the directory rather than writing into the source tree |
| D10 | `node --test` shipped via `--import`; jest refused by name | a consumer on jest is a future slice with its own spike; nothing here pretends otherwise |
| D11 | Scope = files under the root minus `node_modules`/`.d.ts`/hoisted factories; no `--include/--exclude` in rung 1 | a monorepo consumer whose sources sit above the root needs `--root`, which vitest already has |
| D12 | Arguments unread in rung 1 (`locals: false`); an args tier arrives with `--focus` in rung 3, measured | `tree` prints `name() <unread: locals>` for a rung, exactly as Rust does today |
| D13 | A `TYPESCRIPT` vocabulary column; `terms()` refuses a fourth `lang` at exit 2 | a fourth recorder cannot be read by this reader until it brings its column — which is the rule, not a cost |
| D14 | Qualnames in JavaScript's own spelling (`Fog.compute`, `outer.inner`, `<anonymous>` without an ordinal); `file` absolute, fingerprint root-relative | same-line anonymous twins share a key (declared); a `--focus` selector spelling is rung 3's |
| D15 | `err_flow: false` in rung 1 although RAISE/HANDLED rows exist | rung-1 traces are refused by `exceptions` forever (re-recording costs 25 s); the alternative is a false declaration |
| D16 | The spike's findings document lands on `main` with this spec (the Rust precedent: PR #9 carried findings + amendments; the code stays parked) | none |

## 13. Rulings requested from Brice

Scope, merges and money only; the design is decided above.

1. **The lens** stays the VTT copy at `0091e97` on `/mnt/extra/sensorium-s5/`
   (725 MB) through rung 1's acceptance. *Recommend: keep it; deleting it is
   destructive and re-copying costs a live-tree read.*
2. **This docs PR** — the spec plus the spike's four findings files — merges
   to `main`, and rung 1 proceeds to a plan (writing-plans) on that basis.
   *Recommend: yes, the Rust precedent (PR #9).*
3. **Scope of rung 1** is §1 as written — vitest and `node --test`, no
   argument capture, no `exceptions` rules. Narrowing or widening it is a
   scope call. *Recommend: as written; each deferral is declared in the
   trace, not hidden.*
