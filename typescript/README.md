# typescript/ — the sensorium recorder for TypeScript

Record what a TypeScript test suite actually did; ask it the same questions.

`sensorium ts run -- vitest run` wraps one harness invocation, instruments the
files under its root at load time, and writes one sensorium trace per test-file
process — the same SQLite format 4 the Python and Rust recorders write, read by
the same `sensorium` command line. It exists for the same reason those do:
reading logs is reading a diary, and this is watching the execution.

One private npm package, **`sensorium-ts 0.1.1`** — ESM `.mjs` with JSDoc
types, type-checked by `tsc --checkJs`, no build step, Node ≥ 24 (the version
this was measured on; the driver refuses below it before spawning anything).
Six modules and a version:

| Module | What it is |
|---|---|
| `src/transform.mjs` | The rewriter. Pure: source text + path + root in, edited text + a source map + a per-file manifest out. No I/O. Positions come from the consumer's own `typescript`; edits are `magic-string` splices, and **no edit contains a newline**. |
| `src/rt.mjs` | The runtime every instrumented module boots. Imports only `node:` builtins. Tasks on `AsyncLocalStorage`, a frame stack per task, the exception `WeakMap`, the JSONL spool. |
| `src/vite.mjs` | The Vite plugin (`enforce: 'pre'`) that puts the transform in vitest's path. |
| `src/setup.mjs` | The vitest setup file: the task-name provider and the per-file/per-test records. Written from a template into `node_modules/.sensorium/` beside the wrapper config, never into your source tree. |
| `src/register.mjs` | What `node --import` runs for `node --test`: it checks the two variables the hook cannot invent and registers `src/hook.mjs`. |
| `src/hook.mjs` | The loader hook itself, on Node's loader thread: it instruments a file under the root and hands it back in **Node's own reported format**, erasing nothing — Node strips the types (`.ts`, `.mts`), and a file Node's strip-only mode refuses fails identically hooked and plain. |
| `src/index.mjs` | `VERSION` — stamped into every spool's BOOT record, which is how a trace says `recorder: sensorium-ts 0.1.1`. |

Beside them, `probes/` is a self-contained vitest project the recorder records
ITSELF with: ten probe files whose expected rows were pinned by the S5 spike
before this code existed, four more under `node --test` — one per extension,
`.ts`, `.mts`, `.mjs`, `.cjs` — with two controls beside them that must fail
the same way hooked and plain, and `probes/check.mjs`,
which reads the spools back and asserts every one of them. Two probes make
`vitest run` red on purpose — an unhandled rejection and a test that never
settles — so the checker's exit status is the gate, not vitest's. The recipe is
`npm run probe` / `npm run probe:nodetest` from `probes/`, three environment
variables and a spool directory outside the repository: `probes/README.md`.

**What v1 records** — tier `call`: calls and returns with a captured return
value, YIELD/RESUME at every `await`, `yield` and `yield*`, RAISE at every
`throw` and HANDLED at every `catch` and empty-callback sink, frames with
outcomes, and **tests as tasks** named the way vitest names them. Files under
the invocation's root only — `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ES modules,
`node_modules` excluded — with no hand annotation and no change to your config
or your dependencies. `meta.lang` is `typescript` even for a suite that is all
`.js`: the tag names the language of the consumer, not of each file.

What it does *not* see, and what says so in the trace, is
[`HONESTY.md`](HONESTY.md) — read that before you trust an answer. The trace
contract all three recorders are written against is
[`../docs/TRACE-FORMAT.md`](../docs/TRACE-FORMAT.md); the design and its rungs
are in
`../docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md`.

## Install

    npm ci --prefix typescript
    npm --prefix typescript run check      # type-check: noEmit + checkJs

Run the check through the package's own script. A bare
`npx tsc -p typescript/tsconfig.json` resolves a different `typescript` from
the repository root and checks the wrong thing.

Reading the traces needs the Python side: **`sensorium` 0.9.0+**, which is
where the `ts` verb, the `TYPESCRIPT` vocabulary, the unknown-language refusal
and the seven conformance vectors live. An older reader opens these traces —
they are format 4 and carry every required key — but narrates them in Python's
words, which is a claim about provenance the trace does not make.

## Record

    sensorium ts run [--tier off|call] -- <your harness command, as you type it>

    sensorium ts run -- vitest run src/fog        # vitest
    sensorium ts run -- npx vitest run            # …however you invoke it
    sensorium ts run -- node --test src/          # node's own runner
    sensorium ts run --tier off -- vitest run     # the control arm

Everything after `--` is yours, unchanged. The driver recognises the harness,
adds what it needs, spawns the command, waits for it, converts the spools, and
**exits with the harness's own status** — a recording of a failing suite is a
recording, not an error.

For vitest it writes one wrapper config and the setup file under
`<root>/node_modules/.sensorium/`, merged with your own config and appending
to your `setupFiles` rather than replacing them, and removes the directory in a
`finally`. If the root has no `node_modules` at all — a hoisted monorepo
package, whose dependencies resolve from a parent — the driver **creates** it,
and removes it again on the way out when it is still empty, which it is only
when the driver is what made it. Resolution is unaffected: an empty directory
is walked past. A directory that still holds anything is left alone, so a
second concurrent invocation of the same project keeps its own two files. For `node --test` it prepends an `--import`. `npm test`, `pnpm test`
and `yarn test` are refused at exit 2 naming the direct form: a package script
cannot carry the flags the wrapper needs, and guessing what the script runs is
a guess. jest is refused by name.

`--tier off` compiles exactly the same edits and emits nothing, so switching
tiers rebuilds nothing and `off` is a real control arm rather than a different
program.

If the driver dies between the harness's exit and the conversion, nothing is
lost — conversion is deterministic and re-runnable over the spool directory:

    sensorium ts ingest <spool-dir>

## Where traces go

`$SENSORIUM_DIR/traces/`, default `~/.sensorium/traces` — the same place the
Python and Rust recorders write, so one `sensorium runs` lists all three. One
invocation of a 372-file suite makes 372 traces, grouped under one
`invocation` header with each member named by its test file.

A trace holds the recorded process's environment, command line, source digests
and captured return values in plaintext; so does the spool directory the
recording itself writes. Treat both the way you would treat a core dump, and
do not upload either as a build artifact.

## Ask

    sensorium runs                                  # what have I recorded
    sensorium info last                             # what am I looking at
    sensorium tree last --depth 3                   # what actually ran
    sensorium frame last --fn compute               # one activation, in full
    sensorium grep last compute --kind RETURN       # every event that mentions it
    sensorium diff RUN_A RUN_B                      # where two runs part
    sensorium diff --ignore-moves RUN_A RUN_B       # …across a refactor that moved code

On a TypeScript trace, `runs` groups a whole invocation under one header with
the harness command and the exit somebody waited for, and prints each member's
test file. `info` adds the harness, the container, the interpreter line
(`node v24.16.0 (vitest 4.1.9, jsdom)`), tests as tasks against tests the
harness registered, what the transform covered and what it excluded by reason,
and any unhandled rejections. `tree` groups by test, because here a task is a
test.

## What refuses, and why

No command answers from a capability the recorder declared it does not have,
and each refusal names the capability and the recorder rather than returning an
empty result. Changing the answer means changing the recording, which is what
these exit statuses mean.

| Command | Exit | Why |
|---|---|---|
| `exceptions` | 3 | The RAISE and HANDLED rows exist, but the TypeScript disposition rules do not (rung 2). `capabilities.err_flow: false`, and the refusal says nothing was judged. |
| `watch`, `flow` | 3 | `capabilities.line: false` — this recorder produces no LINE events, so there is no per-line state to check. |
| `flow --object` | 3 | `capabilities.object_identity: false` — object identity is not carried, so a question about *that* object cannot be answered from this trace. |
| `refocus` | 2 | `capabilities.refocus: false` — nothing was re-run, and the reader's next move is a different command. |

Arguments are **unread** in 0.1.0: `capabilities.locals: false`, every CALL
carries `unread: ["locals"]`, and `tree` prints `compute() <unread: locals>`.
That is a stated absence, not an empty argument list.

The **driver** refuses before it mints anything, and each refusal names the
thing to do instead:

| What | Exit | Why |
|---|---|---|
| `npm test`, `pnpm test`, `yarn test` | 2 | A package script cannot carry the two flags the wrapper appends, and guessing what the script runs is a guess. The refusal names the direct form. |
| `jest …` | 2 | *"jest is not supported: not measured, and the consumer does not run it."* By name, not by silence. |
| anything else after `--` | 2 | The command names no harness this recorder wires; the refusal names both forms it does. |
| `node` below 24 | 2 | Checked before a spool directory exists, so a refused run leaves nothing behind. |
| `typescript/node_modules` not installed | 2 | Names `npm ci --prefix <pkg>`. Set `SENSORIUM_TS_PKG` if the package is not beside the Python one. |
| your project has no `typescript` in `node_modules` | 2 | The transform parses with **your** compiler, not this package's, so the root must have one; resolved the way Node resolves it, parents included. Names `npm install --save-dev typescript`. |
| a `node_modules` that cannot be written | 2 | The wrapper has to live under `node_modules` for `vitest/config` to resolve from your tree, so this is a refusal rather than a write somewhere else in your source. |
| a vitest `test.projects` / `test.workspace` config | 2 | vitest resolves a config per project and the wrapper merges onto one, so the plugin never reaches those pipelines and the suite would run unrecorded. Refused at config load, by name. |
| a harness binary that is not there | 2 | `recognise` reads the command you typed and does not resolve it -- which `vitest` runs is your choice. A name that is not a program is refused by name, and the invocation it would have recorded is taken back. |
| `ts ingest` over a directory already ingested | 2 | `ingested.json` names the run ids the first pass minted; a second pass would mint new ones over the same records. |
| `ts ingest` over a directory no driver wrote | 2 | A spool set with no `invocation.json` cannot say what produced it. |
| a trace whose `lang` this reader has no vocabulary for | 2 | The recording is fine and the reader is old — the refusal says which and names the upgrade. |

`--tier off` is not a refusal: it records nothing by design, reports
`traces: 0`, and returns the harness's own status.

## Not yet

Argument capture and per-line state under a `--focus` (rung 3); the
`exceptions` disposition rules that make an empty `catch` a sink and a rethrow
a hop (rung 2, at which point these 0.1.0 traces stay refused and re-recording
is the fix); `refocus` (rung 4); the browser, which needs a runtime without a
filesystem (rung 5); jest; a transform cache. `finally`, a `.catch` with a
non-empty body, and which frame *scheduled* a continuation are recorded by
nothing here — see [`HONESTY.md`](HONESTY.md) §4, §3 and the numbered blind
spots.

## What rung 1 measured, and what it did not settle

Twelve endpoints and two controls, **pre-registered before this code existed**
and byte-locked in
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §1. **The
rung ships DONE-WITH-STOP.** Ten of the twelve gated endpoints PASS, both
controls PASS, **one is a STOP** and **one is REPORTED**.

**One lens under every number below**, and it is somebody else's code: a
tabletop VTT frontend at commit `0091e97` — **372 test files, 4,278 tests** —
under vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, on 16 cores.

| | Measured | n |
|---|---|---|
| Trace unit | **372** containers, one `test_file` each, 372 distinct names — **PASS** | 372 traces |
| Cost of recording | `off/plain` **1.0587**, `call/plain` **1.1324** — **PASS**, inside the 1.10 bound, so the transform stays uncached | 5 per arm |
| Coverage | **5,378 instrumented of 5,378 eligible**, ratio **1.0000**, no unnamed exclusion — **PASS** | 5,378 sites |
| False DIVERGED | **0/19** DIVERGED, **0/19** REFUSED over twenty recordings of one file — **PASS** | 19 pairs |
| Sites keep their lines | **20/20** on the exact line; a planted failure's `FAIL` header and `file:44:13` identical plain against driven — **PASS** | 20 shapes |
| Both harnesses | 372/4278 green under the driver; `node --test` 6 pass 0 fail — **PASS** | 2 harnesses |
| Tests are tasks | tasks **4,278** = `tests_seen` **4,278**, conflicts **0** — **PASS** | 372 traces |
| The reader's words | **0** occurrences of eight Python/Rust leak needles over ten commands — **PASS** | 8 needles |
| Loss model | suspended-at-end 2/2; SIGKILLed worker `incomplete` with a `diff` refusal 3/3 — **PASS** | both halves |
| Verification | the split control reads `MATCH modulo location`; a **value-preserving** planted swap reads DIVERGED at causal step 16, invisible to the suite's own 56/56 — **PASS** | 2 controls |
| Contamination | manifest **748 OK / 0 FAILED**, **0** markers, wrapper directory gone — and the plain-after wall **22.8678 s** against the plain band **[22.3136, 22.7221]** — **STOP on that one clause** | 4 clauses |
| Cost of conversion | full-suite `ingest` **45.5293 s** against a plain wall of **22.5925 s** (×2.02); one file **0.3638 s** — **REPORTED**, design input | 3 repetitions |

**The STOP is a STOP.** E6′'s rule is a flat conjunction of four clauses and
defines no lesser word. Three of the four ask about contamination directly and
all three hold exactly; the fourth is a timing clause and it did not. Nothing
was re-rolled, no band was moved and no verdict was renamed. What it rests on
is written down instead: the instrument that took that one wall ran without the
load guard every other timed arm had, and a five-run min–max is a range and not
a tolerance. It is re-measured next slice under a **new** pre-registration,
E6″ — a new commitment, not a second look at this one.

**The REPORTED is design input, which is what its rule said it would be.**
Converting a whole 372-file suite costs twice the suite's own wall, so a Node
converter on `node:sqlite` or a binary wire is the next slice's question. One
file — what a debugging loop actually pays — converts in **0.36 s**.

Two things none of the fourteen license: none of them says a TypeScript trace
answered a debugging question nobody planted, and none of them was measured on
a second consumer.

## Cost

Reported, never gated. The tier is a runtime gate and the transform runs every
time, so the whole cost of `--tier off` is the transform. Every number, with
its `n` and the suite it was measured on, is in
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §3, and the
summary is the table above. Where a reading crosses a pre-registered bound it
buys **work** — a transform cache, a converter elsewhere — and never a verdict
about whether the recorder is honest.
