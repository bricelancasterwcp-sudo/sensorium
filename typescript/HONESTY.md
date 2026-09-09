# The TypeScript recorder's honesty ledger

`sensorium-ts 0.1.0` — v1, the call tier, under vitest and `node --test`.
Read by `sensorium` 0.9.0 and above; a trace names its own writer, because the
runtime stamps the package's `VERSION` into every spool's BOOT record and the
converter spends it on `recorder: "sensorium-ts 0.1.0"` in meta. No edition of
this file is struck yet: this is the first.

Sensorium's founding rule is that **the instrument never answers from data it
does not have**. The Python recorder keeps its half of that rule in the
README's *What the answers claim*, *What a trace file holds* and *What
sensorium sees at all*; the Rust recorder keeps its half in
[`../rust/HONESTY.md`](../rust/HONESTY.md). This is the TypeScript recorder's
half, written to the standard the standing ruling of 2026-08-20 set: a sibling
recorder carries its own ledger and its own refusals, and multi-language
support never softens the core.

**How to read a section.** Each one states a promise, says **what in the trace
says it** — a meta key, a payload field, a transform exclusion count, or a line
`sensorium info` prints — and names **what could falsify it**: a test, a probe,
a corpus case, a vector or an acceptance endpoint, by path or by id. A promise
with no falsifier is not a promise, it is an assertion, and this document does
not carry assertions. The whole list in two columns is the
[index](#the-index-promise--falsifier) at the end.

**Amended 2026-09-09, at rung 1's close** — the first edition to be struck
against a measurement. Nothing below is deleted; each amendment is dated where
it stands and says what it replaced. What moved: §1's cap example (the two
limits compose), §2's `#k` rule (per NAME, ruling R17) and the options-second
shapes (none is refused any more, ruling R8c), §7's exclusions (`.d.ts` and
`node_modules` carry **no** count, ruling R7; `.mts`/`.cts`, ruling R9; a
parse error, ruling R10; the printed `xK` form, ruling R27), §9's cost (E1′,
E10 and **E6′'s STOP**, each with its `n` and lens), and **eight new blind
spots**, 10 through 17. The endpoint ids below now name measured cells: the
record's §3 and §4, and its §5 for what each verdict does not cover.

**Provenance.** This file is written **before the runtime exists**, which is
the point: the code is written to the ledger, not the ledger to the code. Its
facts come from the design
(`../docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md`),
whose §7 fixes these ten sections, and from the mechanics spike that measured
them (`../docs/superpowers/spikes/2026-09-08-typescript-mechanics-spike.md`).
Endpoints `E0′`–`E11` below are the pre-registered acceptance of
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` — §3.1 for
the gated table, §3.2 for the two controls — recorded there before any of this
was built, so none of them can be chosen after its number is read. A falsifier
named here that does not yet exist is a file a later task owes.

## 1. Outcomes

**The promise.** A frame closes exactly one of three ways, and the trace says
which. `return` carries a `dbg` capture of the value the function returned.
`unwind` carries the value that was thrown out of it. A frame still parked when
the recording ends — an `await` on a promise that never settled — closes
neither way and reads **`suspended at end of recording`**, never `(open)` and
never a guessed outcome.

**What in the trace says it.** The RETURN record's value is
`{"k": "dbg", "v": …, "trunc": …}`, `v` produced by `util.inspect` at
`depth: 2`, `maxArrayLength: 8`, `maxStringLength: 100` and capped at 200
bytes with `trunc` set when the cap bit. *(Amended 2026-09-09: the two limits
COMPOSE, and the earlier reading of this sentence — "a 10 kB string comes back
as 200 bytes with `trunc: true`" — is unsatisfiable. `maxStringLength` cuts a
long string inside `inspect`, so the 200-byte cap never sees it; what sets
`trunc` is **a value whose inspection exceeds the cap** — a wide object, a
long array of short strings — not a long string.)* `undefined` is the text `undefined`,
never an absent field: a function that returned nothing is a fact, not a hole.
An inspector that throws — the program's own `inspect` customisation — reads
`{"k": "unread"}`, which says the capture failed rather than showing an empty
string. `capabilities.return_value: true` is the recorder's statement that
these values exist at all.

**What it does not claim.** A captured value is a rendering at a moment, not
the object: nothing here is a handle you can follow, and two renderings being
equal is not two objects being the same one (`object_identity: false`, §7).
`frames.kind` is the contract's own enumeration — `function`, `coroutine`,
`generator`, `async_generator` — and what the reader PRINTS for those is
JavaScript's word, `[async]`, `[generator]`, `[async generator]`, never
Python's `[coroutine]`.

**One promise about outcomes is really a promise about words.** Every answer
about a TypeScript trace is told in this recorder's vocabulary: the unit of
work is a *test*, threads are *worker threads or forked children of the
harness*, and no Python or Rust term (`asyncio`, `python ?`, `cargo`,
`coroutine`, `Rust disposition`, `sensorium run --focus`) appears in any
command's output. A trace written by a recorder this reader has no vocabulary
for is **refused at exit 2 naming the language**, not narrated in Python's
words as a fallback.

**Falsifiers.** `typescript/test/rt.test.mjs` (`dbg caps`),
`typescript/test/transform.test.mjs`, `tests/test_ts_ingest.py`,
`corpus/typescript/pass_vs_fail`, `corpus/typescript/wrong_branch`,
`corpus/typescript/unit_mismatch`, `corpus/typescript/double_call`,
`corpus/typescript/suspended_at_end`,
`typescript/probes/src/never_settles.probe.test.ts`, `E11`(a), `E7′`, and the
vectors `v23-lang-typescript-prose`, `v24-unknown-lang-refused`,
`v26-kind-labels`.

## 2. Tasks

**The promise.** Every test callback the transform wrapped is a task, and it
carries the name vitest itself prints for that test where a provider ran, and
its lexical `describe > title` where none did.

**What in the trace says it.** A call whose callee is `test` or `it`, or a
member chain rooted at one (`test.each(table)(title, fn)`, `it.skip`,
`test.only`, `test.concurrent`, `test.fails`, `test.todo`), has its function
argument wrapped as a task; `describe`/`suite` and their chains push a lexical
title while the collection callback runs, so a test registered inside one knows
its chain at registration time. The name comes from the setup file's provider
(`expect.getState().currentTestName`) — vitest's own full title, `.each` rows
expanded exactly as vitest expands them — and is cross-checked wherever the
transform passed a plain string literal that is not an `.each` template: a
provider name that does not end with that literal is **not used**; the task
falls back to the lexical `describe > title` and the disagreement is counted in
`task_name_conflicts`. `task_name_basis` in meta says which rule named this
trace's tasks; under `node --test`, where no provider runs, that basis is the
lexical one. The k-th activation **in a container to produce a given NAME** —
a `retry`, a `repeats` — is `<name>#k` for k ≥ 2; activations the harness has
already renamed for itself, as `.each` renames its rows, are distinct names and
are not numbered on top of. *(Amended 2026-09-09, ruling R17: this sentence
read "the k-th activation of one registration to produce a given NAME in a
container", which counts **per registration**. Measured under that rule a
five-row `.each` produced `… = 5#2` — the provider had already made the rows
distinct and the counter numbered them again. The counter is per NAME, which is
what a reader of `#2` takes it to mean. The cost is stated where it lands: two
different tests with one identical full name would share a `#k` sequence —
impossible under vitest's unique full names, possible for lexical names under
`node --test`.)* A title expression that is not
a string at runtime leaves the task unnamed, and the reader prints
`(unnamed: title not a string)` for it — a label that says why, not a blank.

**Tests the transform did not wrap are counted, not hidden.** The setup file
records one SEEN per test the harness registered; `tests_seen` is that count,
and `info` prints `tests: N as tasks, M seen by the harness`. A shortfall is
named by the shape that caused it, and is a shortfall the trace states rather
than a silence.

**What it does not claim.** Hooks (`beforeEach`, `afterAll`, …) are not tasks:
their frames run in no task, on the container's root stack, and are compared as
the thread stream in order, which is what they are. And a `.concurrent` task's
provider name is *uncheckable*: vitest's `expect` state is global and shared
across concurrent tests, so a `.concurrent.each` name that is wrong cannot be
caught by the cross-check that catches every other kind (blind spot 5) — the
count that would have caught it is `task_name_conflicts`, and this ledger says
where it cannot reach.

**The options-second form is wrapped, not refused** *(added 2026-09-09,
ruling R8c)*. vitest's documented `test(name, options, fn)` and
`describe(name, options, fn)` are spliced **positionally**, with the callback
wrapped at its own argument position and the flags appended last — so an
options object holding a function, a multi-line options object, an `await`ed or
`yield`ed title expression, and an expression-bodied callback all come out
CORRECT and all are tasks. An earlier rule relocated the callback chunk and
refused those four shapes rather than move text it could not move safely;
relocation carries a chunk's intro and outro text with it, so the relocation
was withdrawn and **no shape of a test call is refused by the transform
today**. What is still not covered is stated below as a blind spot, never as a
refusal.

**Falsifiers.** `E9`, `typescript/probes/src/each.probe.test.ts`,
`typescript/probes/src/concurrent.probe.test.ts`,
`typescript/probes/src/describe_chain.probe.test.ts`,
`corpus/typescript/each_naming`, `typescript/test/rt.test.mjs`
(`task isolation`), `tests/test_ts_ingest.py`.

## 3. Attribution

**The promise.** Every continuation of a task's work lands in that task. A
microtask, a timer callback, a jsdom timer, an emitter callback fired from a
timer — each resolves to the task that started the chain, not to whatever
happened to be running when the event loop got there.

**What in the trace says it.** `__srt.task(title, fn)` runs the callback inside
`als.run(task, …)` — one `AsyncLocalStorage` store per activation — so the
task is a property of the async context and not of the call stack.
`fingerprint_basis: "per-task"` in meta says the trace was built that way. Each
task owns its own frame stack; a frame running in no task uses the container's
root stack; CALL records the parent as the frame beneath it on the stack it
pushed onto. At `await`, `yield` and `yield*` the frame is popped and a YIELD
recorded, and pushed again at RESUME, which is what keeps a fan-out's siblings
from nesting under one another. YIELD says what is being waited on:
`awaiting: "Promise"` for an `await`, `awaiting: "consumer"` for a `yield`.

**What it does not claim.** A continuation that runs when its task's stack is
empty — a timer callback, a promise reaction whose scheduler already returned —
opens a **parentless** frame at depth 0 in its task, and its CALL payload says
`caller: "untraced"`. That is the truthful answer: Node's timer machinery
called it, and Node's timer machinery is not instrumented. Which frame
**scheduled** it is a different relationship and this recorder does not record
it; there is no `scheduled_by` key to read, and depth 0 inside the right task
is the whole of what is claimed.

**Falsifiers.** `E3-TS`, `typescript/probes/src/async.probe.test.ts`,
`typescript/probes/src/timer_parentless.probe.test.ts`,
`corpus/typescript/async_interleaved`,
`corpus/typescript/timer_callback_parentless`, `typescript/test/rt.test.mjs`
(`task isolation`, `stack pops at yield`).

## 4. Throw flow

**The promise.** RAISE marks a `throw` **statement** and nothing else. HANDLED
marks a `catch` clause and the one sink shape that has no clause. Every such
record says which shape it came from, in `how`.

**What in the trace says it.** `throw X` becomes
`throw __srt.raise(__sf, (X), <line>)`; a `catch` clause gains a
`__srt.handled(…)` first statement (a clause with no binding is given one); a
`.catch(() => {})` whose callback body is empty is wrapped so the callback
records a HANDLED. `how` is one of `throw`, `catch`, `sink_empty_catch`,
`sink_empty_catch_callback` — the enumeration is the declaration, and a shape
outside it produced no record. Every `exc` object is
`{kind, type, msg, serial}` with `kind` ∈ `throw`, `rejection`; `kind` is
written on **every** one, because the contract reads a kindless `exc` as
Python's.

**Identity, and where it ends.** `serial` is minted once per thrown **object**
through a `WeakMap`, so `catch (e) { throw e }` is one exception with two RAISE
rows — a hop, not two exceptions and not a sink. A thrown **primitive** (a
string, a number) has no identity to hang a `WeakMap` on and gets a fresh
serial each time, so a rethrown primitive cannot be followed across the
rethrow. That is stated here rather than papered over by merging on text.

**Records with nowhere to go are counted, not dropped.** A RAISE or HANDLED
that fires with no open frame — a default-parameter expression that throws
before its frame opens, a throw at module scope — is written as **no event**
and counted in meta `throw_flow_outside_frames`. A causal event with no
`code_id` is refused by the contract, and inventing a code object would put a
site in the program that has none. The same rule sends an unhandled rejection
to meta: `process.on('unhandledRejection')` fills
`unhandled_rejections: [{type, msg, serial}]`, **never** `events`. `info`
prints that count when it is non-zero, and prints a zero on a complete trace
too — the listener always ran, so zero there is a measured zero.

**What it does not claim, and the refusal that says so.** These rows are
recorded and **not judged**. `capabilities.err_flow: false` in 0.1.0, although
RAISE and HANDLED rows exist, because the key is the runtime's statement that
its records carry what the `exceptions` rules need — and no TypeScript
disposition rules exist yet (rung 2 writes them). So `exceptions` **refuses**
on these traces at exit 3, naming the language and saying nothing was judged.
The cost is real and pre-committed: a trace this 0.1.0 runtime wrote stays
refused after rung 2 lands, then by the capability sentence, and re-recording
is what changes it. Two further shapes record nothing at all: a `.catch(fn)`
with a non-empty body (blind spot 2), and `finally` (blind spot 3). A
`Promise.reject(v)` is not a `throw` statement and raises nothing here.

**Falsifiers.** `E8′`, `typescript/probes/src/swallow.probe.test.ts`,
`typescript/test/rt.test.mjs` (`serial survives rethrow`),
`typescript/test/transform.test.mjs`, `tests/test_ts_ingest.py`,
`corpus/typescript/unhandled_rejection_in_info`,
`corpus/typescript/exceptions_refused`, and the vectors
`v25-exc-kind-throw-rejection`, `v27-unhandled-rejection-in-meta`.

## 5. Loss

**The promise.** A container that was killed says so, and never says how much
it lost.

**What in the trace says it.** Records are buffered and flushed after every
task, every 100 ms, on `exit` and `beforeExit`, and on `SIGTERM`, `SIGINT` and
`SIGHUP`; the EXIT record is the last line of a whole spool. A container killed
by `SIGKILL` — vitest's teardown timeout is the ordinary way this happens —
loses at most the unflushed tail and its EXIT. The converter marks that trace
`incomplete: true`, `info` prints the INCOMPLETE banner above everything else,
and `diff` refuses it at exit 3 rather than comparing half a recording against
a whole one.

**What it does not claim.** No `records_dropped` count is ever written by this
recorder. A process that was killed did not get to count what it was about to
write, and a number the runtime cannot know is a number this recorder does not
put in a trace. The flag is the honest artifact; the tail is unknowable and is
declared unknowable.

**Falsifiers.** `E11`(b), `typescript/test/rt.spool.test.mjs` (`flush on exit`),
`tests/test_ts_ingest.py`.

## 6. Exit

**The promise.** Two exit facts exist and each is written where it was
witnessed. Neither is ever written wearing the other's name.

**What in the trace says it.** The driver spawns the harness and waits for the
harness — not for the harness's workers. So every container carries
`exit_status: null` with `exit_status_basis: "unwitnessed"`: this recorder did
not start that process and did not reap it, and a status it did not observe is
not a status it reports. What the driver **did** observe is written on every
trace of the invocation as `harness_exit {status, signal, basis: "waited"}`,
and both `runs`' header and `info` print it with that basis attached
(`invocation <id>: vitest run src/fog  exit:1 (waited)`).

**What groups them.** `meta.invocation` is the invocation every member belongs
to; `meta.test_file` is the root-relative path of the one test file a container
ran, which is what `runs` prints per member in place of an argv. A container
that ran several files (a reused worker) carries `test_files` and `runs` prints
`files: N`; a container that ran none — a `globalSetup` in the main process,
any `node --test` process — carries neither key and is listed by its argv. The
absence of `test_file` is therefore a statement, not a gap.

**Falsifiers.** `E0′`, `tests/test_ts_ingest.py`,
`corpus/typescript/pass_vs_fail`, and the vectors
`v28-harness-exit-waited`, `v29-runs-file-header`.

## 7. Scope

**The promise.** What is inside this recorder's scope is stated; what is
outside it is counted or declared, and never silently absent.

**Eligibility, and every exclusion by name.** Eligible files are `.ts`,
`.mts`, `.tsx`, `.js`, `.jsx` and `.mjs` ES modules under the invocation's
root. A CommonJS file — `.cjs`, `.cts`, or a `.js` that Node loads
as CommonJS under `node --test` — is excluded and counted, because the
runtime's header is an `import`. A file whose own TypeScript parse produces
diagnostics is left **untouched** and counted as `parse-error` with its first
three messages, rather than spliced blind against a best-effort AST; the
consumer's own bundler then reports the consumer's own syntax error on the
file as written.

***Out of scope is not the same as excluded, and only one of the two is
counted*** *(amended 2026-09-09, ruling R7; this paragraph previously listed
`node_modules` and `.d.ts` among the exclusions).* Anything under
`node_modules` and every `.d.ts` declaration file are **outside the transform's
scope**: the transform returns null for them and writes no manifest, so they
appear in **no** count. Counting files the plugin never looks at would be a
claim about the tree, not about the run. The counted exclusions are the
in-scope ones below — a file the transform saw and declined. Nothing inside a `vi.mock`, `vi.doMock`,
`vi.hoisted` or `vi.unmock` factory is instrumented (vitest hoists those above
every import, our header included) and that count is named. Overload
signatures and `declare`d or `abstract` members have no body to wrap. `eval`
and `new Function` bodies are never touched at all. `meta.files_transformed`
and `meta.transform_excluded {reason: count}` carry these totals and `info`
prints them **by reason with each reason's own count** — `files: 725
transformed; excluded: 344 (vitest-hoisted-factory x344)` — so coverage is a
number in the trace, not a hope. *(The printed form was amended 2026-09-09,
ruling R27: it read `excluded: 3 (vitest-hoisted factory)`, a total beside one
bare reason, which loses the split as soon as there are two. The example above
is a measured line from a call-arm trace of the acceptance lens.)*

**How a site inside the scope is named.** `code_objects.file` is absolute (the
contract's rule) while the fingerprint hashes the **root-relative** path, which
is what lets `diff --ignore-moves` pair a function across a file split.
`firstlineno` is the TypeScript line of the function's first token.
`qualname` is the file-local path in JavaScript's own spelling — `compute`,
`Fog.compute`, `Fog.constructor`, `outer.inner`, `ns.fn`, `default` for an
`export default`, and `<anonymous>` for a function with no name and no binding.
`<anonymous>` carries **no ordinal** on purpose: an ordinal would move every
later anonymous function's key when one is inserted above it, which is the
move-fragility `--ignore-moves` exists to absorb. The cost is blind spot 1.

**Declared absent, and refused rather than guessed.** The capabilities block is
the recorder's own list of what it does not produce, and every command reads it
the same way. Arguments are unread: `locals: false`, and every CALL carries
`unread: ["locals"]`, so `tree` prints `name() <unread: locals>` — a stated
absence, not an empty argument list. `line: false`, so `watch` and `flow`
refuse at exit 3 naming the capability and the recorder. `object_identity:
false`, so `flow --object` refuses. `output: false` — vitest owns the capture,
and this recorder does not claim the program's stdout — and `stdin: false`
beside it, which is the same statement about the other end of the pipe
*(added 2026-09-09: the list omitted it, which made the list look complete and
was not false about any key)*. `threads: false` and `children: false` (blind
spot 4). `refocus: false`, refused at exit 2. `err_flow: false` (§4).

**The footprint on the consumer's tree.** One directory is written:
`<root>/node_modules/.sensorium/`, holding the wrapper vitest config and the
setup file the driver writes from a template. No source file is touched, no
dependency is added, and the consumer's own config is merged rather than
replaced — `setupFiles` are **appended** to the user's, never swapped for
ours. The directory is removed in a `finally`, so it exists only for the run.
A read-only `node_modules` is a refusal at exit 2 naming the directory, never
a write somewhere else in the source tree.

**Falsifiers.** `E2′`, `E3-TS`, `E5′`, `E6′`, `E7′`,
`typescript/test/transform.test.mjs`, `tests/test_ts_ingest.py`,
`corpus/typescript/nondeterministic`, `corpus/typescript/watch_refused`,
`corpus/typescript/object_refused`, and the E5-TS split control of the
acceptance record's §3.2.

## 8. Preserved by construction, tested

**The promise.** Recording changes what runs, and changes nothing you read.

**Lines, by construction.** No edit the transform makes contains a newline, so
every line of the output is the same line of the input and `firstlineno` is the
line a human sees in the source. This is not a check that passed once; it is a
property of the edit set, asserted on every golden as `lines(out) == lines(in)`
and measured end to end as 20 shapes landing on 20 exact lines.

**Columns, by the map.** The transform returns a `hires` source map to vitest,
so a failing assertion's column is the original's. The endpoint that pins it
compares a planted failing assertion's report instrumented against plain and
requires the report to be byte-identical, which is the reader's experience and
not a proxy for it.

**The next plain run is a plain run.** Sources are byte-identical after a
recording by sha256 manifest, no marker appears in any cache directory, the
wrapper directory is gone, and the suite's own pass counts sit inside the plain
band. The instrumentation lives in memory between the plugin and the harness,
never in a file the consumer keeps.

**The harness stays the runner.** The driver spawns the command as typed and
never re-implements a harness's CLI. `npm test`, `pnpm test` and `yarn test`
are refused at exit 2 naming the direct form — a package script cannot take the
two flags the wrapper appends, and guessing what the script runs is a guess.
jest is refused by name.

**Falsifiers.** `E4′`, `E5′`, `E6′`,
`typescript/probes/src/sites.probe.test.ts`, `typescript/test/transform.test.mjs`.

## 9. Cost

**The promise.** Cost is a reported fact with its `n` and its lens beside it,
and it gates nothing.

The tier is a runtime gate and the transform runs every time, so the whole cost
of `--tier off` is the transform — which makes `off` a real control arm rather
than a different program. The endpoints report walls at n=5 per arm,
interleaved, conversion excluded, and report conversion separately. Where an
endpoint carries a bound, crossing it buys **work**, not a verdict: a transform
cache keyed on source sha becomes rung-1 work if `off/plain` goes above 1.10,
and a conversion wall above the plain suite's own wall is a design input
naming a Node converter or a binary wire. Neither outcome is a NO-GO, and
neither number is allowed to decide whether the recorder is honest.

**Measured, rung 1** *(added 2026-09-09; every number from
`../docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §3, on one
lens: the VTT frontend at `0091e97` — 372 test files, 4,278 tests — under
vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores)*:

- **Recording**: `off/plain` **1.0587** and `call/plain` **1.1324**, n=5 per
  arm, interleaved, 0 runs dropped, conversion excluded — inside E1′'s 1.10
  bound, so the transform stays uncached and the source-sha cache stays a later
  slice. Beside them, ungated: **99.61 B/line** and **162,629.8 lines/s** under
  the product runtime (medians over the 5 call runs), and vitest's own
  `transform` seconds **10.24 / 21.64 / 21.43** for plain / off / call.
- **Conversion**: full-suite `ingest` over 372 spools and 414,450,522 bytes,
  **45.5293 s** median (n=3) against the same run's plain wall of **22.5925 s**
  — ×2.02, **above** E10's bound. E10's own rule made that a **design input and
  not a STOP**, and the input is taken: a Node converter on `node:sqlite`, or a
  binary wire, is the next slice's question. One file's spool converts in
  **0.3638 s** (n=3), which is what a debugging loop actually pays, and it is
  reported here beside the suite number so the design question is asked about
  the right workload.
- **Reading**: `info` **0.5401 s** and `diff` **0.6867 s** (n=3 each) on the
  lens's largest trace, 333,832,192 bytes.
- **And one cost that is a STOP.** E6′ asks whether a plain run afterwards is
  contaminated, in four clauses. Three ask about contamination directly and all
  three hold — the sources are identical by sha256 manifest (**748 OK, 0
  FAILED**), **0** `__srt` markers appear in any cache directory, and
  `node_modules/.sensorium` is **absent**. The fourth is a timing clause, and
  it **STOPped**: the plain-after wall **22.8678 s** against the plain arm's
  own min–max band **[22.3136, 22.7221]**, 0.1457 s (0.65%) above it. The
  number stands as measured — nothing was re-rolled and no band was moved —
  and what the STOP is understood to rest on is written down rather than
  argued away: the instrument that took it ran with no load guard though its
  clause is a timing clause, and a five-run min–max is a range and not a
  tolerance (record §5, gaps 5 and 6). It is re-measured next slice under a
  NEW pre-registration, **E6″**. This ledger states it as a STOP because that
  is what the pre-registration's own words make it, and a rung that ships with
  one is a rung that ships with one.

**Falsifiers.** `E1′`, `E10`, `E6′`.

## 10. Blind spots

Numbered so a later document can cite "blind spot 3" and mean this one. Each
names what the trace carries in its place, and what could falsify the claim
that this is the whole of it.

1. **Same-line anonymous twins share a fingerprint key.** Two anonymous
   functions on one line intern to one site, because interning is per site and
   `<anonymous>` carries no ordinal (§7). The trace says exactly what it knows —
   `<anonymous>` at that line — and claims nothing about which of the two ran.
   *Falsifier:* `typescript/test/transform.test.mjs`, `E2′`.
2. **A `.catch(fn)` with a non-empty body is not seen.** Only the empty-callback
   sink records a HANDLED; the `how` enumeration of §4 is the list of shapes
   that produce a record, and this is not on it. *Falsifier:*
   `typescript/probes/src/swallow.probe.test.ts`, `E8′`.
3. **`finally` records nothing.** Not a RAISE, not a HANDLED, not a hop. Rung 2
   decides whether it should; until then `capabilities.err_flow: false` says no
   disposition may be read from these rows at all. *Falsifier:*
   `typescript/test/transform.test.mjs`, `corpus/typescript/exceptions_refused`.
4. **A worker thread or child process the program itself spawns is its own
   unlinked container.** It records if it imports an instrumented module, and
   nothing joins it to the frame that spawned it. `threads: false` and
   `children: false` say so, and `info`'s container line (`pid`, `ppid`,
   `thread_id_os`, `is_main_thread`) is all the identity there is.
   *Falsifier:* `tests/test_ts_ingest.py`, `E0′`.
5. **`.concurrent` tests may be misnamed, and the miss is countable but not
   catchable.** vitest's `expect` state is global, so the provider name for one
   concurrent test can belong to another; the literal cross-check catches this
   everywhere except a `.concurrent.each`, whose title is a template. The
   carriers are `task_name_basis` and `task_name_conflicts`. *Falsifier:*
   `typescript/probes/src/concurrent.probe.test.ts`,
   `corpus/typescript/async_interleaved`, `E9`.
6. **A default-parameter expression that throws throws before its frame
   opens.** There is no frame to attach the RAISE to, so no event is written
   and the record is counted in `throw_flow_outside_frames`. *Falsifier:*
   `typescript/probes/src/swallow.probe.test.ts`,
   `typescript/test/transform.test.mjs`.
7. **Top-level module code runs unframed.** Module scope is not a function, so
   nothing wraps it; `files_transformed` counts the file, and a throw from
   module scope lands in `throw_flow_outside_frames` like any other record with
   no open frame. *Falsifier:* `typescript/test/transform.test.mjs`, `E2′`.
8. **A generator driven by `yield*` runs its inner frames parentless.** The
   delegating frame has parked, so the inner frames open at depth 0 with
   `caller: "untraced"` — the same marker §3 gives a timer callback, and the
   same limit. *Falsifier:* `typescript/probes/src/async.probe.test.ts`,
   `typescript/test/rt.test.mjs` (`stack pops at yield`).
9. **An `async` `describe` callback registers its tests after the lexical chain
   has popped.** Where a provider ran, the names are vitest's and are
   unaffected; where none ran (`node --test`), those tasks lose their chain and
   `task_name_basis` says the names are lexical. *Falsifier:*
   `typescript/probes/src/describe_chain.probe.test.ts`,
   `corpus/typescript/each_naming`, `E9`.

10. **`for await (…)` and top-level `await` mint no YIELD/RESUME.** The
    suspension rewrite is applied to `await` expressions inside an
    instrumented function body; a `for await` loop's implicit await and a
    module's top-level `await` are neither, so a frame parked there is not
    recorded as parked. Measured absence, not inference: **0** occurrences of
    either shape in the acceptance lens, so the endpoint that would have
    caught it had nothing to catch. *(Added 2026-09-09.)*
    *Falsifier:* `typescript/test/transform.test.mjs`, `E2′`.
11. **A `.catch(function () {})` is not a sink; only the arrow spelling is.**
    §4's empty-callback sink matches an arrow function with an empty block
    body. The same empty body written as a `function` expression records
    nothing at all — not a HANDLED, not a count. Which shapes are sinks is
    rung 2's question, and this is one of the shapes it inherits.
    *(Added 2026-09-09.)* *Falsifier:*
    `typescript/probes/src/swallow.probe.test.ts`, `E8′`.
12. **A class static block is neither instrumented nor counted.** `static { … }`
    is not a function, so nothing wraps it — and unlike every other in-scope
    thing the transform declines, it produces no `excluded` entry either, so it
    is invisible in the coverage number rather than named in it. It should be
    counted as `static-block`; that it is not is this ledger's, not the
    trace's. *(Added 2026-09-09.)* *Falsifier:*
    `typescript/test/transform.test.mjs`.
13. **A destructuring `catch ({ code })` records the exception type as
    `undefined`.** The HANDLED splice hands the runtime the clause's own
    binding; a destructuring pattern binds no name to the caught value itself,
    so the transform passes the literal `undefined` rather than reconstruct an
    object it does not have, and the record reads `type: "undefined"`. That is
    what the recorder knows about the value, and it is not the claim that the
    program caught `undefined`. The clause still records a HANDLED with its
    line and its `how`. *(Added 2026-09-09.)* *Falsifier:*
    `typescript/test/rt.test.mjs`, `typescript/test/transform.test.mjs`.
14. **The untraced caller is on the wire and no reader prints it.** §3's
    `caller: "untraced"` is in the CALL payload, and the reader renders
    nothing for it — the Python core's own caller renderer has only ever
    printed a caller it has a code object for, and `caller: "untraced"` is on
    the Python wire too. So a parentless continuation reads as depth 0 inside
    the right task, with no tag saying why. Rendering one is a reader feature
    for **all three** languages, carried in `docs/CARRIED-DEBT.md` (ruling
    R29). *(Added 2026-09-09.)* *Falsifier:*
    `corpus/typescript/timer_callback_parentless`,
    `typescript/probes/src/timer_parentless.probe.test.ts`.
15. **Two declarations in this recorder are stated and unfalsifiable as
    shipped.** (a) `rt.mjs` is declared external to vite's module runner in
    every config the recorder writes, so the setup file and the instrumented
    modules resolve one Node module instance; at vitest **4.1.9** the probe
    that would catch a second instance — exactly one BOOT line per spool —
    reads the same with the declaration and without it, so the declaration is
    **insurance whose effect was not observed on this version**, and it is
    named here rather than presented as a measured guarantee. (b)
    `meta.test_files` — the key a container that ran more than one file
    carries — is written by the converter and was exercised by **no run**: the
    acceptance measured **0** traces carrying it, and a `--pool=threads` probe
    produced none either. The reader's `files: N` line is therefore code no
    recording has printed. *(Added 2026-09-09.)* *Falsifier:*
    `typescript/probes/check.mjs` (the one-BOOT assertion),
    `tests/test_ts_ingest.py`, `E0′`.
16. **One reader fallback is unreachable today and would print a raw wire
    word if it were reached.** `tree`'s unframed-kind line falls back to the
    contract's own `generator`/`coroutine` spelling where it has no label for a
    kind — Python's words, in this recorder's output. Every call in a
    TypeScript trace is framed, so nothing has ever reached it; it is named
    because an unreachable branch that would print the wrong vocabulary is
    still a place this ledger's central promise could break. *(Added
    2026-09-09.)* *Falsifier:* `E7′`, `tests/test_vocab.py`.
17. **A `.concurrent` name that is wrong is counted where it can be, and E9
    measured zero.** Blind spot 5 says the cross-check cannot reach a
    `.concurrent.each`. What rung 1 adds is the measurement: over the full
    suite, `task_name_conflicts` is **0** and tasks equal `tests_seen` at
    **4,278**, so nothing the check CAN see disagreed — which is evidence
    about the shapes it covers and none at all about the one it does not.
    *(Added 2026-09-09.)* *Falsifier:* `E9`,
    `typescript/probes/src/concurrent.probe.test.ts`.

## The index: promise → falsifier

A promise with no falsifier is not a promise. Every row names a test, a probe,
a corpus case, a vector or an acceptance endpoint.

| § | Promise | What could falsify it |
|---|---|---|
| 1 | A frame closes `return` with a `dbg` capture or `unwind` with the thrown value; `undefined` is the text `undefined` and an inspector that throws reads `{"k": "unread"}` | `typescript/test/rt.test.mjs` (`dbg caps`), `tests/test_ts_ingest.py`, `corpus/typescript/pass_vs_fail`, `corpus/typescript/wrong_branch`, `corpus/typescript/unit_mismatch` |
| 1 | Every activation is its own frame row, so two calls of one function are two frames and not one | `corpus/typescript/double_call`, `typescript/test/transform.test.mjs` |
| 1 | A frame parked at end of recording reads `suspended at end of recording`, on a trace that is otherwise complete | `corpus/typescript/suspended_at_end`, `typescript/probes/src/never_settles.probe.test.ts`, `E11`(a) |
| 1 | Answers are told in this recorder's words: `[async]`/`[generator]`/`[async generator]` for the frame kinds, no Python or Rust term anywhere, and an unknown `lang` refused at exit 2 rather than read as Python | `docs/trace-format/vectors/v26-kind-labels.json`, `docs/trace-format/vectors/v23-lang-typescript-prose.json`, `docs/trace-format/vectors/v24-unknown-lang-refused.json`, `E7′` |
| 2 | Every wrapped test callback is a task named by vitest's own full title where a provider ran and lexically otherwise, `#k` on the k-th activation to repeat a name, with `task_name_basis` naming the rule | `E9`, `typescript/probes/src/each.probe.test.ts`, `corpus/typescript/each_naming`, `typescript/test/rt.test.mjs` (`task isolation`) |
| 2 | A provider name that contradicts a literal title is not used and is counted in `task_name_conflicts` | `typescript/probes/src/concurrent.probe.test.ts`, `E9`, `tests/test_ts_ingest.py` |
| 2 | Tests the transform did not wrap are counted (`tests_seen` against tasks) and named by shape, never silently missing | `E9`, `typescript/probes/src/each.probe.test.ts`, `tests/test_ts_ingest.py` |
| 2 | Hooks are not tasks; their frames run on the container's root stack | `typescript/probes/src/describe_chain.probe.test.ts`, `corpus/typescript/each_naming` |
| 3 | Every continuation lands in the task that started it, across microtasks, timers, jsdom timers and emitter callbacks | `E3-TS`, `typescript/probes/src/async.probe.test.ts`, `corpus/typescript/async_interleaved`, `typescript/test/rt.test.mjs` (`task isolation`) |
| 3 | The frame pops at YIELD and pushes at RESUME, so a fan-out's siblings do not nest; YIELD says `awaiting: "Promise"` for `await` and `awaiting: "consumer"` for `yield` | `typescript/test/rt.test.mjs` (`stack pops at yield`), `typescript/test/transform.test.mjs`, `typescript/probes/src/async.probe.test.ts` |
| 3 | A continuation entered with an empty stack is parentless at depth 0 with `caller: "untraced"`, and the scheduling frame is not recorded | `typescript/probes/src/timer_parentless.probe.test.ts`, `corpus/typescript/timer_callback_parentless`, `tests/test_ts_ingest.py` |
| 4 | RAISE marks `throw` statements only; HANDLED marks `catch` clauses and the empty-callback sink; `how` is the enumeration of shapes that record at all | `E8′`, `typescript/probes/src/swallow.probe.test.ts`, `typescript/test/transform.test.mjs`, `docs/trace-format/vectors/v25-exc-kind-throw-rejection.json` |
| 4 | A rethrown OBJECT keeps its serial (one exception, two RAISE rows, a hop); a rethrown primitive gets a fresh one and cannot be followed | `typescript/test/rt.test.mjs` (`serial survives rethrow`), `docs/trace-format/vectors/v25-exc-kind-throw-rejection.json` |
| 4 | A RAISE or HANDLED with no open frame is written as no event and counted in `throw_flow_outside_frames` | `typescript/probes/src/swallow.probe.test.ts`, `tests/test_ts_ingest.py` |
| 4 | Unhandled rejections are meta, never events, and `info` prints a zero on a complete trace because the listener always ran | `docs/trace-format/vectors/v27-unhandled-rejection-in-meta.json`, `corpus/typescript/unhandled_rejection_in_info`, `tests/test_ts_ingest.py` |
| 4 | These rows are recorded and not judged: `err_flow: false`, and `exceptions` refuses at exit 3 naming the language and saying nothing was judged | `corpus/typescript/exceptions_refused`, `E7′` |
| 5 | Records are flushed after every task, every 100 ms and on every terminal signal, and EXIT is the spool's last line | `typescript/test/rt.spool.test.mjs` (`flush on exit`), `E11`(b) |
| 5 | A SIGKILLed container is `incomplete: true` with the INCOMPLETE banner and a `diff` refusal, and no `records_dropped` is ever written | `E11`(b), `tests/test_ts_ingest.py` |
| 6 | Every container's own exit is `null` / `unwitnessed`, and the harness's exit is `waited` on every member of the invocation, each printed with its basis | `docs/trace-format/vectors/v28-harness-exit-waited.json`, `tests/test_ts_ingest.py`, `corpus/typescript/pass_vs_fail` |
| 6 | `meta.invocation` groups the traces and `meta.test_file` names each; a container that ran none carries neither key and is listed by its argv | `docs/trace-format/vectors/v29-runs-file-header.json`, `E0′` |
| 7 | Eligible files under the root are instrumented and every exclusion is named and counted in `transform_excluded`, with `files_transformed` beside it | `E2′`, `typescript/test/transform.test.mjs`, `tests/test_ts_ingest.py` |
| 7 | Sites keep JavaScript's own spelling, `file` absolute and the fingerprint root-relative, so `diff` pairs across a file split and a re-record of one file never reads DIVERGED | `E3-TS`, the E5-TS split control (acceptance §3.2), `corpus/typescript/nondeterministic` |
| 7 | What the recorder does not produce is declared, and every command refuses on the declaration instead of answering: `locals`, `line`, `object_identity`, `output`, `threads`, `children`, `refocus` | `corpus/typescript/watch_refused`, `corpus/typescript/object_refused`, `E7′`, `tests/test_ts_ingest.py` |
| 7 | The consumer's tree is touched at exactly one path, `<root>/node_modules/.sensorium/`, and only for the run's duration; `setupFiles` are appended, never replaced | `E6′`, `E5′` (the suite green under the driver is what a REPLACED `setupFiles` would break; E6′ alone cannot see it) |
| 8 | No edit contains a newline, so every output line is the input's and 20 shapes land on 20 exact lines | `E4′`, `typescript/test/transform.test.mjs` |
| 8 | The source map is `hires`, so a planted failing assertion's report is byte-identical instrumented against plain | `E4′`, `typescript/probes/src/sites.probe.test.ts` |
| 8 | A plain run afterwards is uncontaminated: sources identical by manifest, no marker in any cache, the wrapper directory gone | `E6′` |
| 8 | Both harnesses run their own way; a package script and jest are refused at exit 2 rather than guessed at | `E5′` |
| 9 | Cost is reported with its `n` and lens and gates nothing; a bound crossed buys work, never a verdict | `E1′`, `E10` |
| 9 | Cost is a STOP where a pre-registered clause did not hold: E6′'s plain-band clause, stated as a STOP and not re-rolled | `E6′`, the acceptance record §4 and §5 gaps 5–6 |
| 10 | The blind-spot list above is the whole of what this recorder cannot see, each item carried by a meta key, an `info` line or a stated absence | each item's own falsifier, 1 through 17 *(10–17 added 2026-09-09)* |
