# typescript/ — the sensorium recorder for TypeScript

Record what a TypeScript test suite actually did; ask it the same questions.

`sensorium ts run -- vitest run` wraps one harness invocation, instruments the
files under its root at load time, and writes one sensorium trace per test-file
process — the same SQLite format 4 the Python and Rust recorders write, read by
the same `sensorium` command line. It exists for the same reason those do:
reading logs is reading a diary, and this is watching the execution.

One private npm package, **`sensorium-ts 0.3.0`** — ESM `.mjs` with JSDoc
types, type-checked by `tsc --checkJs`, no build step, Node ≥ 24 (the version
this was measured on; the driver refuses below it before spawning anything).
Fifteen modules and a version:

| Module | What it is |
|---|---|
| `src/transform.mjs` | The rewriter. Pure: source text + path + root in, edited text + a source map + a per-file manifest out. No I/O. Positions come from the consumer's own `typescript`; edits are `magic-string` splices, and **no edit contains a newline**. |
| `src/rt.mjs` | The runtime every instrumented module boots. Imports only `node:` builtins. Tasks on `AsyncLocalStorage`, a frame stack per task, the exception `WeakMap`, the object-identity `WeakMap`, the JSONL spool. |
| `src/dbg.mjs` | The capture formatter: `util.inspect` under fixed options (`depth: 2`, `maxArrayLength: 8`, `maxStringLength: 100`) inside a 200-byte cap, and the `oid`/`type` pair an object or function capture carries. |
| `src/tasks.mjs` | The test-callback wrapping and task naming the transform emits, split out of `transform.mjs` so the focus tier could grow beside it. |
| `src/bindings.mjs` | What a statement WRITES, what a guard BINDS on entry and what a block DECLARES, read off the AST: `writesOf`, `headBindingsOf`, `headDeclaredOf`, `declaredIn`, `isStatementPosition`. Pure, the sibling of `escape.mjs`. |
| `src/probe.mjs` | Where a statement probe goes: which statements mint a row, which guards get a head row, which bodies are wrapped, and the `;` a statement without one needs. |
| `src/focus.mjs` | Whether a `--focus` spec selects a function — the qualname prefix rule on a `.` boundary, the optional file part by path, basename or stem, and the `Closest:` suggestions a refusal prints. |
| `src/resolve.mjs` | The pre-run resolver the driver spawns: it walks the eligible files under the root with the transform's own pass one and prints one JSON line saying what each spec matched, what it did not, and what it matched only among functions this recorder excludes. |
| `src/qualname.mjs` | The file-local JavaScript spelling of a function's name — `Fog.compute`, `outer.inner`, `default`, `<anonymous>` — shared by the transform and the resolver. |
| `src/tally.mjs` | The per-invocation counts the converter reads: files transformed, exclusions by reason, functions focused. |
| `src/vite.mjs` | The Vite plugin (`enforce: 'pre'`) that puts the transform in vitest's path. It reads `SENSORIUM_FOCUS` where it is BUILT, not at module load. |
| `src/setup.mjs` | The vitest setup file: the task-name provider and the per-file/per-test records. Written from a template into `node_modules/.sensorium/` beside the wrapper config, never into your source tree. |
| `src/register.mjs` | What `node --import` runs for `node --test`: it checks the two variables the hook cannot invent and registers `src/hook.mjs`. |
| `src/hook.mjs` | The loader hook itself, on Node's loader thread: it instruments a file under the root and hands it back in **Node's own reported format**, erasing nothing — Node strips the types (`.ts`, `.mts`), and a file Node's strip-only mode refuses fails identically hooked and plain. |
| `src/escape.mjs` | The escape rule, as pure functions over AST nodes: `catchHow(ts, clause)`, `callbackHow(ts, arg)`, `finallyCompletes(ts, block)`. It decides which of the nine `how` words a catch clause, a rejection handler or a `finally` block gets, and it is what `sensorium exceptions` ends up reading. |
| `src/index.mjs` | `VERSION` — stamped into every spool's BOOT record, which is how a trace says `recorder: sensorium-ts 0.3.0`. |

Beside them, `probes/` is a self-contained vitest project the recorder records
ITSELF with: twelve probe files whose expected rows were pinned before this
code existed — `focus.probe.test.ts` is rung 4's, eleven exported functions,
one per rule of the focus tier — four more under `node --test`, one per
extension (`.ts`, `.mts`, `.mjs`, `.cjs`), with two controls beside them that
must fail the same way hooked and plain, and `probes/check.mjs`, which reads
the spools back and asserts every one of them. `checkFocus` has **two
branches** and skips neither: keyed on the BOOT record's own declaration, a
`line: true` spool is held to every focus marker, the CALL's args and the row
count, and a `line: false` one is held to zero LINE records in that file's
container and no args on any of its CALLs. A checker that quietly skipped
would be a hole, so the mode itself is reported (`focus:mode focused` /
`focus:mode unfocused`). Two probes make
`vitest run` red on purpose — an unhandled rejection and a test that never
settles — so the checker's exit status is the gate, not vitest's. The recipe is
`npm run probe` / `npm run probe:nodetest` from `probes/`, three environment
variables and a spool directory outside the repository: `probes/README.md`.

**What it records** — tier `call`: calls and returns with a captured return
value, YIELD/RESUME at every `await`, `yield` and `yield*`, RAISE at every
`throw` and HANDLED at every `catch` and empty-callback sink, frames with
outcomes, an object serial (`oid`) and constructor name on every object or
function capture, and **tests as tasks** named the way vitest names them.
**Under `--focus`, one LINE row per completed statement** of each function a
spec selected, with the bindings that statement wrote, plus the focused
function's arguments on its CALL. Files under the invocation's root only —
`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` ES modules, `node_modules` excluded —
with no hand annotation and no change to your config or your dependencies.
`meta.lang` is `typescript` even for a suite that is all `.js`: the tag names
the language of the consumer, not of each file.

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
where the `ts` verb, the `TYPESCRIPT` vocabulary and the unknown-language
refusal live; **0.10.0+** for the `exceptions` verdicts, and **0.12.0+** for
the focus tier — the LINE rows, the `util.inspect` dialect and the serial
`flow --object`. An older reader opens these traces — they are format 4 and
carry every required key — but narrates them in Python's words, which is a
claim about provenance the trace does not make.

## Record

    sensorium ts run [--tier off|call] [--focus <spec>]… -- <your harness command, as you type it>

    sensorium ts run -- vitest run src/fog            # vitest
    sensorium ts run -- npx vitest run                # …however you invoke it
    sensorium ts run -- node --test src/              # node's own runner
    sensorium ts run --tier off -- vitest run         # the control arm
    sensorium ts run --focus fog.ts:compute -- npx vitest run src/fog   # per-statement

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

### `--focus <spec>` — the per-statement tier

Repeatable, parsed where `--tier` is (before the `--`, so a harness's own
`--focus` after it is never stolen). A spec is `<qualname>` or
`<file>:<qualname>`:

* **The qualname is what `tree` prints** — `compute`, `Fog.compute`,
  `outer.inner`, `default` — and a value naming a **container selects
  everything under it on a `.` boundary**. `--focus Fog` selects `Fog.compute`
  and `Fog.render`; `--focus refresh` selects `refresh` AND the arrows nested
  in it (`refresh.<anonymous>`), which is the only way to name an anonymous
  function. **This is the trap worth knowing before you run**: three typed
  names on a real file resolved to six sites on the rung-4 lens, because two
  of them held default-parameter arrows. `resolve.mjs` is what says so, and it
  says so before the harness starts.
* **The file part narrows and is optional** — the root-relative path
  (`src/lib/fog.ts`), the basename (`fog.ts`) or the stem (`fog`). Qualnames
  are file-local, so a bare `--focus load` selects every `load` under the
  root and `meta.focus_matched` lists each. No globs, no regexes, no line
  numbers.
* **A bad spec refuses at exit 2, before a spool directory exists.**
  `error: --focus <spec> matches no function under <root>; nothing was run.
  Closest: a, b, c` — and a spec whose only matches are functions this
  recorder excludes (an overload signature, a `declare`, a hoisted factory)
  refuses with the exclusion named and counted instead.
* The driver passes the specs to the plugin and the runtime in one
  `SENSORIUM_FOCUS` variable, unit-separated. An inherited value is **cleared**
  on an unfocused run, so a stale export cannot focus a run whose own record
  says it focused nothing.

`info` then prints what was typed and what it selected —
`focus matched: 2 — src/fog.ts:Fog.compute, src/fog.ts:Fog.render`, with
`(N function(s) focused by the transform)` appended when the transform's own
count differs, which it does when two anonymous function-likes share one
qualname. What a focused row holds, rule by rule, is
[`../docs/trace-format/TYPESCRIPT-KEYS.md`](../docs/trace-format/TYPESCRIPT-KEYS.md)
§ *Under a focus*; what it does not is
[`HONESTY.md`](HONESTY.md) §11 and blind spots 28–37.

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
    sensorium exceptions last                       # which throws went nowhere
    sensorium exceptions <invocation-id>            # …across the whole suite at once
    sensorium flow last --object loadSettings:return   # is that the same object?

…and, on a run recorded with a `--focus`:

    sensorium watch last --at fog.ts:compute --expr 'visible > 100'
    sensorium flow last --value 20                  # where did that number go
    sensorium frame last --fn compute               # …its timeline, one row per statement

On a TypeScript trace, `runs` groups a whole invocation under one header with
the harness command and the exit somebody waited for, and prints each member's
test file. `info` adds the harness, the container, the interpreter line
(`node v24.16.0 (vitest 4.1.9, jsdom)`), tests as tasks against tests the
harness registered, what the transform covered and what it excluded by reason,
any unhandled rejections, and — on a focused run — the specs as typed beside
what they matched. `tree` groups by test, because here a task is a test.

`exceptions` classifies every `throw` and every orphan handler as one of five
dispositions — `swallowed`, `uncaught`, `re-raised`, `propagated`,
`ambiguous` — and prints the tally. **SWALLOWED is claimed only where the
recording establishes it**: a handler whose `how` is in the absorbing set
(`catch`, `sink_empty_catch`, `catch_callback`, `sink_empty_catch_callback`,
`sink_finally_return`), in a frame that later returned, with no later raise of
that serial and **no** escaping handler for it anywhere. Which word a `catch`
clause or a rejection handler gets is decided at transform time from its own
syntax: a body that only `console.*`-logs the binding is a swallow, a body that
does anything else with it has let the error escape, and a bare `throw e` is a
hop and not an escape. Everything short of proof is `ambiguous` with its reason
printed, and nothing reaches SWALLOWED by falling through — including, since
S5 rung 3, an **untraced catcher**: no HANDLED anywhere in the unit's own
window and the raise's frame unwound into a traced parent a vitest
`toThrow`, an error boundary or a library's own `try` caught without a
trace of its own. Rule 4's own absorbing conjunct is window-scoped, so a
handler in an EARLIER window no longer keeps a later rethrow out of
`propagated`, and a second line, `ambiguous by reason: escaped N, untraced
catcher N`, prints beside the tally whenever a reason count is non-zero.
Twenty-one of `corpus/typescript/`'s **42** cases carry an `exceptions`
verdict, one shape each.
Given an **invocation id**, one answer covers every worker: identical
verdicts merge into one block with `[×N over M processes]` beside it. What
the rules cannot see is [`HONESTY.md`](HONESTY.md) §4 and its blind spots
18–27.

## What refuses, and why

No command answers from a capability the recorder declared it does not have,
and each refusal names the capability and the recorder rather than returning an
empty result. Changing the answer means changing the recording, which is what
these exit statuses mean.

| Command | Exit | Why |
|---|---|---|
| `exceptions` on a trace a **0.1.x** runtime wrote | 3 | That recorder declared `capabilities.err_flow: false` and its HANDLED rows carry no `how` word for the rules to read. The refusal names the capability and the recorder; what such a trace lacks is a record, not a rule, so **re-recording** is the fix. A 0.2.0 or later recording is answered, not refused. |
| `watch`, `flow --value`, `frame`'s timeline, on a run that named **no `--focus`** | 3 | `capabilities.line: false` and `locals: false` — the tier is decided at transform time, so an unfocused run produces no LINE event and no argument to check. The refusal names the recorder the TRACE carries, not the one installed, and re-recording under `--focus` is the fix. On a focused run all three answer. |
| `flow --object` on a trace a **0.2.x** runtime wrote | 3 | `capabilities.object_identity: false` — that recorder carried no identity, so a question about *that* object cannot be answered from its traces. A **0.3.0** recording declares `true` unconditionally, focused or not, and is answered exactly. |
| `refocus` | 2 | `capabilities.refocus: false` — nothing was re-run, and the reader's next move is a different command. |

Arguments are **unread on an unfocused run**: `capabilities.locals: false`,
every CALL carries `unread: ["locals"]`, and `tree` prints
`compute() <unread: locals>`. That is a stated absence, not an empty argument
list — and in a focused recording the same tree prints
`total(items=[ 1, 2 ], member=true)` for a focused callee beside
`helper() <unread: locals>` for one no spec reached.

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

`refocus`; the browser, which needs a runtime without a filesystem; jest; a
transform cache. Which frame *scheduled* a continuation is recorded by nothing
here. Argument capture and per-line state under a `--focus` **arrived in rung
4** and are above; the `exceptions` disposition rules arrived in **rung 2** —
the empty `catch` is a sink, the rethrow is a hop, the completing `finally` is
a sink and every rejection handler is recorded — and traces written by **0.1.0
and 0.1.1 alike stay refused**, because both declare `err_flow: false` and
re-recording is the fix. What none of it can see, it says: a `try` with its own
`catch` clause is never marked for the `finally` sink, a logger that is not
`console.*` reads as an escape, an assertion failure born in vitest's `expect`
writes no RAISE at all, and a focused row reports no place write, no `this`
and no `switch` discriminant — [`HONESTY.md`](HONESTY.md) §3, §4, §11 and
[`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md).

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

## What rung 2 measured, and the four gaps it found

Nine endpoints, pre-registered and byte-locked before this rung's code existed
(`../docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` §1), on the
same lens. **The rung ships DONE**: every endpoint ran once and not one fired
its rule's failure word. No row reads PASS and neither does the rung, because
six of the nine rules name only a failure word and three name none at all —
what a clean reading can say is that the word did not fire.

| | Measured | n |
|---|---|---|
| False accusation on somebody else's suite | **0 false SWALLOWED** of **30** hand-adjudicated shapes; tally `swallowed 261, ambiguous 53` over 314 raises in 53 of 372 processes — **no STOP** | 30 shapes |
| The corpus's verdicts | **17 of 17** cases equal to the locked table, 8 SWALLOWED lines — **no STOP** | 17 cases |
| Every catch site instrumented | **287 spliced of 287** eligible (177 catch clauses, 108 `.catch`, 2 `.then`, 0 completing `finally`) over 741 files, ratio **1.0000**, 0 exclusions needed — **no STOP** | 287 sites |
| The probes' shapes | **32 of 32** `// SWALLOW` / `// ESCAPE` markers seen — **no STOP** | 32 markers |
| False DIVERGED | **0/19** DIVERGED, **0/19** REFUSED over twenty recordings of one file — **no STOP** | 19 pairs |
| The reader's words | **0** occurrences of nine Python/Rust leak needles over both transcripts — both clauses met | 9 needles |
| Cost of recording | `off/plain` **1.0608**, `call/plain` **1.1266**, every load reading under 4.0 — **REPORTED, no gate** | 5 per arm |
| Cost of conversion | the fresh 372-spool set **16.0715 s**; its one big spool **0.1642 s** — **REPORTED, no gate** | 5 each |

Beside them, ungated: the escape rule's own distribution over that lens —
**22 of 177** catch clauses read `catch_escaped` (**0.1243**), with `catch`
**87** and `sink_empty_catch` **68** — and **285** HANDLED records across the
suite.

**Four gaps, and none of them is an endpoint's rule** (record §5). The shape
key's id mask carries Rust's float-type exclusion onto TypeScript frame ids, so
those 30 SWALLOWED shapes are **28 distinct places**. Three reused instruments
were measuring the **global** `sensorium` — an install of `main` — and were
fixed before any of them ran here. E7″'s needle list could not be applied as
written, because `Err` as a case-insensitive substring is matched by every
`Error('…')` an answer prints. And on real code the modal AMBIGUOUS reason is
the classifier's catch-all — **17** of the 30 ambiguous shapes — whose shape is
an untraced catcher sitting *inside* a traced frame. The rules declining rather
than guessing there is exactly what keeps the false-SWALLOWED count at 0.

## What rung 4 measured, and its three STOPs

Eight endpoints, pre-registered and byte-locked before this rung's code
existed
(`../docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md` §1),
on the same lens — this time on **830 files** of it, one 26-test file as the
subject, three of its pure functions as the focus. **The rung ships
DONE-WITH-STOP.**

| | Measured | word |
|---|---|---|
| H3 · one LINE per completed statement | **9 of 9** rows on the first `parseDiceGroups('1d20')` activation — lines 69, 70, 71, 72, 73, 74, 76, 75, 72; every delta name and the one `unbound` list equal to a hand count sha256-locked before `bindings.mjs`, `probe.mjs`, the runtime's `line` or the converter's `_on_line` existed; empty diff | **PASS** |
| H1 · an unfocused run stays unfocused | `line: false`, `locals: false`, **0** LINE rows, and `watch` refusing at exit 3 in a sentence whose version token IS the trace's own `recorder` | **PASS** |
| H6 · identity is exact | one array at `diceQueue.ts:138` (empty) and `diceQueue.ts:202` (one die), **one serial**, `continuity: exact (serial identity)`, both `Array` | **PASS** |
| H8 · nothing else moved | 105 corpus cases / 220 questions / 0 failures; `pytest -q` 4090 passed; cargo 773 passed; node 521 passed; the probes' 146 checks; **0** of nine leak needles over 13 transcripts | **PASS** |
| H7 · what it cost | focused/unfocused median wall ×**2.3816** (0.7955 s → 1.8946 s, n=3 each, interleaved) for **295** extra LINE rows on the same call tier, plus **1.132 s** of resolution over 830 files, once per invocation | reported |
| H2 · does a focus resolve and run? | the suite half held exactly (F's counts = U's, both exit 0) — but three typed specs resolved to **six** sites where the pre-registration committed three | **STOP** |
| H4 · does `watch` answer? | all three verdicts and all three exits as predicted; the cell read one clause too strongly (*no HIT at line 72* where the prediction was *no HIT at the `while`-completion row*, and line 72 carries a head row too) | **STOP** |
| H5 · does `flow --value` see it? | S1 found with 9 sightings; S2 is in the trace and in the committed transcript, and the cell's row parser could not see it — a printed CALL row's name carries its argument list and no line | **STOP** |

**None of the three STOPs is the recorder's.** H2 is the pre-registration's
own under-derivation: `focus.mjs`'s prefix rule selects the function-likes
nested inside a container, which is documented and deliberate, and the number
three was a count of the names a reader types. Beside it, `focus matched: 5`
against `functions focused: 6` — two anonymous arrows share one qualname, so a
qualname is not an identity for an anonymous function-like. H4 and H5 are
readings of `e12_report.py`, found AFTER their numbers, which under this
record's own rule makes them findings and not fixes: nothing was re-run and no
threshold moved. The next slice re-registers all three under fixed
instruments, on rung 1's E6′→E6″ precedent. **The lesson is about the dry
run**: the rehearsal on `probes/` exercised a LINE sighting and a loop whose
extra clause happened to hold, so neither parser defect had a chance to show.

## Cost

Reported, never gated. The tier is a runtime gate and the transform runs every
time, so the whole cost of `--tier off` is the transform. Every number, with
its `n` and the suite it was measured on, is in
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §3, and the
summary is the table above. Where a reading crosses a pre-registered bound it
buys **work** — a transform cache, a converter elsewhere — and never a verdict
about whether the recorder is honest.
