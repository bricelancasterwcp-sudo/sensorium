# typescript/ — the sensorium recorder for TypeScript

Record what a TypeScript test suite actually did; ask it the same questions.

`sensorium ts run -- vitest run` wraps one harness invocation, instruments the
files under its root at load time, and writes one sensorium trace per test-file
process — the same SQLite format 4 the Python and Rust recorders write, read by
the same `sensorium` command line. It exists for the same reason those do:
reading logs is reading a diary, and this is watching the execution.

One private npm package, **`sensorium-ts 0.1.0`** — ESM `.mjs` with JSDoc
types, type-checked by `tsc --checkJs`, no build step, Node ≥ 24 (the version
this was measured on; the driver refuses below it before spawning anything).
Five modules and a version:

| Module | What it is |
|---|---|
| `src/transform.mjs` | The rewriter. Pure: source text + path + root in, edited text + a source map + a per-file manifest out. No I/O. Positions come from the consumer's own `typescript`; edits are `magic-string` splices, and **no edit contains a newline**. |
| `src/rt.mjs` | The runtime every instrumented module boots. Imports only `node:` builtins. Tasks on `AsyncLocalStorage`, a frame stack per task, the exception `WeakMap`, the JSONL spool. |
| `src/vite.mjs` | The Vite plugin (`enforce: 'pre'`) that puts the transform in vitest's path. |
| `src/setup.mjs` | The vitest setup file: the task-name provider and the per-file/per-test records. Written from a template into `node_modules/.sensorium/` beside the wrapper config, never into your source tree. |
| `src/register.mjs` | The `node --test` loader hook, which type-strips with the consumer's own TypeScript. |
| `src/index.mjs` | `VERSION` — stamped into every spool's BOOT record, which is how a trace says `recorder: sensorium-ts 0.1.0`. |

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
`finally`. For `node --test` it prepends an `--import`. `npm test`, `pnpm test`
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

## Not yet

Argument capture and per-line state under a `--focus` (rung 3); the
`exceptions` disposition rules that make an empty `catch` a sink and a rethrow
a hop (rung 2, at which point these 0.1.0 traces stay refused and re-recording
is the fix); `refocus` (rung 4); the browser, which needs a runtime without a
filesystem (rung 5); jest; a transform cache. `finally`, a `.catch` with a
non-empty body, and which frame *scheduled* a continuation are recorded by
nothing here — see [`HONESTY.md`](HONESTY.md) §4, §3 and the numbered blind
spots.

## Cost

Reported, never gated. The tier is a runtime gate and the transform runs every
time, so the whole cost of `--tier off` is the transform. The numbers, with
their `n` and the suite they were measured on, are in
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md`; where a
reading crosses a pre-registered bound it buys work — a transform cache, a
converter elsewhere — and never a verdict about whether the recorder is
honest.
