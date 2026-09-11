# The TypeScript recorder's honesty ledger

`sensorium-ts 0.2.0` — v1, the call tier, under vitest and `node --test`.
Read by `sensorium` 0.9.0 and above, and by **0.10.0** and above for the
throw-flow verdicts of §4; a trace names its own writer, because the runtime
stamps the package's `VERSION` into every spool's BOOT record and the
converter spends it on `recorder: "sensorium-ts 0.2.0"` in meta. No edition of
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

**Amended 2026-09-10, at rung 2's close** — the second edition struck against
a measurement. Nothing below is deleted; each amendment is dated where it
stands and says what it replaced. What moved: **§4 is rewritten whole** (the
throw flow is judged now, not merely recorded — nine `how` words, the escape
rule with its bare-rethrow exclusion, the rejection-callback words, the
`finally` sink, `capabilities.err_flow: true`), §7's capability list follows
it, §9 gains *Measured, rung 2*, blind spots **2**, **3** and **11** are
**struck** where they stand because this runtime records the shapes they named,
**13** is narrowed, **ten new blind spots 18–27** are added, and the numbered
list moves to [`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md) so this file
stays under 800 lines. Endpoint ids `E6-TS`–`E10″` name measured cells of
`../docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` — its §3 and
§4 for the numbers, its §5 for the four gaps they do not cover.

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
never a guessed outcome. A generator its CONSUMER closed early — a `break` out
of a `for…of`, a `return` from inside one, an explicit `.return()` — closes as a
**`return` whose value is `<unread>`**: the body was resumed with a completion
it did not choose and produced no value, and `.return(v)`'s value belongs to the
consumer and never reaches the body. *(Amended 2026-09-09, ruling R40: the
generator wrapper had no `finally`, so neither its `ret` nor its `catch` ran on
that path and the frame stayed open — a generator somebody deliberately closed
read `suspended at end of recording`, which is a loss claim about a
non-loss.)*

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

**Falsifiers.** `typescript/test/rt.test.mjs` (`dbg caps`, `a generator its
consumer closed early closes as a return it never read`, `a generator that runs
to its own end still closes with its own value`),
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
unlikely under vitest's unique full names, and reachable when one worker runs
several files (a `threads` pool): two files sharing a full title in one
container yield `name` and `name#2`; possible for lexical names under
`node --test`.)* *(Amended 2026-09-10, ruling R46: the clause above read
"impossible under vitest's unique full names" — over-strong once `#k` counts
per CONTAINER (ruling R39) rather than per process: `tests/test_ts_live.py`'s
`test_files` case is exactly a `threads`-pool worker running several files in
one container, where two of them sharing a full title still collide.)* A
title expression that is not
a string at runtime leaves the task unnamed, and the reader prints
`(unnamed: title not a string)` for it — a label that says why, not a blank.

**Tests the transform did not wrap are counted, not hidden.** The setup file
records one SEEN per test the harness registered; `tests_seen` is that count,
and `info` prints `tests: N as tasks, M seen by the harness`. A shortfall is
named by the shape that caused it, and is a shortfall the trace states rather
than a silence. **Where nobody counted, there is no count.** The setup file is
vitest's, and `node --test` runs none: such a trace carries NO `tests_seen`
key and `info` prints `tests: N as tasks` alone. *(Amended 2026-09-09, ruling
R38: the key was written unconditionally from a counter initialised at zero,
so every `node --test` trace read `tests: 2 as tasks, 0 seen by the harness` —
a zero nobody measured, inviting exactly the subtraction the clause exists to
make possible. A vitest container that registered no test still counts, and
its zero is written: there the setup file ran.)*

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

*(Rewritten whole 2026-09-10, at rung 2's close. Rung 1's §4 promised these
rows were "recorded and **not judged**" and that `exceptions` refused a
TypeScript trace by name; both were true of `sensorium-ts 0.1.x` and are false
of this runtime, so the section is replaced rather than annotated — the promise
itself changed. The old text stands in this file's git history and in
`CHANGELOG.md`'s 0.9.0 entry; its last paragraph is the part still in force.)*

**Amended 2026-09-11, at rung 3's close.** Rule 5's catch-all — *"no rule
of this recorder reaches a verdict here"* — now names the footprint first,
in three variants, still AMBIGUOUS and claiming nothing about what the
untraced code did with the failure (blind spot 27, narrowed). Rule 4's
absorbing conjunct now reads within the unit's own window, not
trace-globally, and a second tally line prints beside the first when a
reason count is non-zero. Measured **0 false names of 20** printed blocks
against the seventeen-row hand read, `E6-TS‴`.

**The promise.** RAISE marks a `throw` **statement** and nothing else. HANDLED
marks a `catch` clause, a rejection handler, and the two sinks that have no
clause of their own. Every such record says which shape it came from, in
`how` — and `how` is now **read**: `sensorium exceptions` computes a
disposition from it, so a verdict is only ever as good as the word the
transform wrote. That word is decided from syntax the transform can see, and
every shape it cannot see is a numbered blind spot rather than a guess.

**Nine words, and the enumeration is the declaration.** `how` ∈ `throw`,
`catch`, `catch_escaped`, `sink_empty_catch`, `catch_callback`,
`catch_callback_escaped`, `catch_callback_opaque`,
`sink_empty_catch_callback`, `sink_finally_return`. A shape outside that list
produced **no record**, which is the only thing an absent row ever means here.

**The escape rule, decided at transform time.** A `catch (e) { … }` clause's
word comes from its own AST, at closure depth 0:

- **`catch`** — the body never mentions the binding, or mentions it only as an
  argument of a `console.{log,error,warn,info,debug,trace}` call, at any
  argument position, including inside a template literal or a `String(e)` that
  is itself that argument. Log-and-continue is the archetypal swallow: the
  failure never reached the caller, and the log is where it went.
- **`catch_escaped`** — the binding appears anywhere else: `return e`,
  `throw new Wrapped(e)`, `expect(e.message)`, `err = e`, `list.push(e)`, an
  argument to any non-logging call, a closure that captures it. The error, or
  a rendering of it, left the handler; the rule does **not** follow where, and
  says so by declining to call it a swallow.
- **`sink_empty_catch`** — an empty block.
- A clause with no binding reads `catch` (nothing can escape); a
  **destructuring** binding reads `catch_escaped`, because the transform
  cannot see what it bound (blind spot 13).
- **A bare rethrow is a traced EXIT, not a mention.** `throw e;` or
  `throw (e);` whose operand after any parentheses is the binding ITSELF does
  not count towards `catch_escaped`: the value leaves the way it arrived, and
  the RAISE that throw writes carries the same serial, which the rules read as
  a hop. So `catch (e) { throw e }` and
  `catch (e) { console.error(e); throw e }` read `catch`, while
  `catch (e) { list.push(e); throw e }`, `catch (e) { throw e.cause }` and
  `catch (e) { throw wrap(e) }` stay `catch_escaped`. The exclusion holds at
  closure depth 0 only. *(Amended into the design at Task 6 and shipped here,
  **before any endpoint was measured**: the literal rule barred every
  `throw e` hop from SWALLOWED — record §2.3.)*

**Rejection handlers get the same rule applied to their parameter.**
`p.catch(<arg>)` and `p.then(<x>, <arg>)` are wrapped as
`__srt.catchCb(__sf, <line>, <how>, (<arg>))`, which records HANDLED
`{kind: "rejection"}` and then calls the original with the same `this` and the
same argument and returns its result — a wrapper that must not change what the
handler does. An inline arrow or `function` with an **empty** body is
`sink_empty_catch_callback` (both spellings now, which is what closes blind
spot 11); one with a parameter is `catch_callback` or
`catch_callback_escaped` by the rule above, with the same bare-rethrow
exclusion; anything else — an identifier, a member reference, a call returning
a function — is **`catch_callback_opaque`**, because whether a handler defined
elsewhere swallows is not this splice's to say. `p.catch()` with no argument,
`.then(x)` with one, and `.finally(fn)` are not touched.

**A `finally` that completes is a sink.** A `finally` block containing a
`return`, `break` or `continue` at closure depth 0 discards an in-flight
throw and records HANDLED `sink_finally_return` — but **only when a throw is
in flight**, read from a one-slot mark per frame holding the exception now
travelling through it. `raise(f, e)` sets `f`'s mark; a catch-**less** `try`
whose `finally` completes gains a synthetic marking clause,
`catch(__sfe){__srt.mark(__sf,__sfe);throw __sfe}`, so a library's throw and
an awaited rejection mark it too; `handled` clears it. The sink's `exc` is the
marked throw's own, **complete** — `kind`, `type`, `msg` and `serial` exactly
as the RAISE (or the synthetic marking clause) wrote them, nothing `unread`:
the mark holds the whole `exc` object, not just its serial (R2), and the serial
is what pairs the sink with its RAISE. A `finally` with no completion statement
records nothing: it discards nothing.

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

**What is judged, and on whose word.** `capabilities.err_flow` is **true** in
this version: the runtime's statement that its records carry what the
`exceptions` rules need. SWALLOWED is claimed only where the recording
establishes it — a HANDLED whose `how` is in the **absorbing** set (`catch`,
`sink_empty_catch`, `catch_callback`, `sink_empty_catch_callback`,
`sink_finally_return`), in a frame that later closed by `return`, with no later
raise of that serial, and **no** HANDLED for it anywhere in the **escaping**
set (`catch_escaped`, `catch_callback_escaped`, `catch_callback_opaque`).
Everything else is `ambiguous` with its reason printed. Nothing reaches
SWALLOWED by falling through, and an UNWIND is never itself a verdict: it is
the evidence the `propagated` rule reads. Measured on somebody else's suite,
**0 false SWALLOWED of 30** hand-adjudicated shapes (`E6-TS′`), under an
adjudication protocol byte-locked before any of those lines was read.

**What still produces nothing**, each carried by a numbered blind spot: a
`finally` with no completion statement; `.finally(fn)`; a `Promise.reject(v)`,
which is not a `throw` — its handler's HANDLED has no RAISE and reads *born
outside a throw statement*; a throw inside a promise executor with no open
frame; a throw in untraced code — `JSON.parse`, a dependency — whose HANDLED
reads *born outside traced code*; and an assertion failure born in vitest's own
`expect`, which throws inside untraced code and writes no RAISE at all, so
`exceptions` cannot see it and `info`'s exit line is where it shows (blind spot
26).

**And the cost rung 1 pre-committed is still paid.** A trace a **0.1.x**
runtime wrote declares `err_flow: false`, and `exceptions` refuses it at exit
**3** — by the **capability** sentence now, naming the recorder, rather than by
the language sentence rung 1 shipped — because what such a trace lacks is a
record and not a rule. Re-recording is the fix, and it was pre-committed, not
discovered. Vector `v32-err-flow-typescript-capability-refusal` is that
sentence's pin.

**Falsifiers.** `E6-TS`, `E6-TS′`, `E8″`, `E2″`, `E7″`, `E6-TS‴`,
`E6-TS′-fence`, `E-places`;
`typescript/test/{escape,rt.throw,rt,transform}.test.mjs` and
`typescript/test/golden/`; `typescript/probes/src/{swallow,escape}.probe.test.ts`;
`tests/test_exceptions_typescript{,_ambiguous}.py` and
`tests/test_exceptions_invocation_typescript.py`; the thirty-two throw-flow
cases under `corpus/typescript/`; and vectors `v25`, `v27`, `v30`–`v34`.

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
appear in **no** count. *(Amended 2026-09-09, ruling R37: the CommonJS clause
above was true of vitest runs alone. The `node --test` loader hook classified
by EXTENSION and then forced Node's default load to `format: 'module'`, so a
`.js` in a package with no `"type"` field was spliced as ESM rather than
excluded, and no `node --test` trace carried a count at all. Node decides the
format now — the hook asks it and takes the answer — and the counts are shared
with the plugin. Their GRAIN differs and each is the honest one: vitest
transforms once for the whole invocation, so its count is every container's;
`node --test` runs one child process per test file, so the count on such a
trace is that container's own transform, which is the only one it had.)* Counting files the plugin never looks at would be a
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

***Under `node --test`, Node decides the format AND Node does the stripping***
*(added 2026-09-10, S5 slice 2, `sensorium-ts 0.1.1`).* R37 made the hook ask
Node for the format; the hook still **erased** types itself, from a `STRIP`
list keyed on extension, which is why an eligible `.mts` was instrumented and
then met Node with its annotations intact. Both halves are gone. The hook
returns Node's **own reported format** unchanged — `module-typescript` for an
ESM `.ts` or `.mts` on node ≥ 23.6 — splices its instrumentation into the text
and hands the file back; **Node strips**, the recorder does not, and the
recorder erases nothing. What a consumer can check rather than take on trust:
a construct Node's strip-only mode rejects (an `enum`, say) fails
**identically** plain and hooked, same error code both sides — measured, as
`ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` on both, by a control that discriminates
(against the pre-fix hook the same file **loaded** under the recorder and
failed plain). `.tsx` and `.jsx` are **outside Node's own scope** under
`node --test`: Node's loader throws `ERR_UNKNOWN_FILE_EXTENSION` before this
hook is consulted, on the hooked side and the plain side alike. That is not an
exclusion this recorder makes, so it is **not counted** as one — the same rule
the paragraph above states for `node_modules` and `.d.ts`. Under vitest
nothing here changes: the eligibility list is what it was and `.tsx`/`.jsx` are
transformed.

***A run that recorded nothing says why, when the tallies know*** *(added
2026-09-10, ruling R45).* `ingest` over a spool directory holding no spool said
"nothing was recorded, or the recorder wrote somewhere else" even where the
per-child tallies beside it recorded exactly why — every eligible file
CommonJS, or a parse error. Where **every** tally reads `files_transformed: 0`
and the exclusions are non-empty, the refusal now **names them by reason with
counts** (`commonjs x2, parse-error x1`) and appends the ES-modules-only clause
only when `commonjs` is among them; R27's precedent, one bare reason losing the
split as soon as there are two. A partial suite — anything transformed at all —
keeps the old sentence, because a real recording failure is not an exclusion
and the converter does not guess which it met.

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
spot 4). `refocus: false`, refused at exit 2. **`err_flow: true`** (§4)
*(amended 2026-09-10, rung 2: it read `false` here, which was this list's one
statement about a capability the runtime now has; a 0.1.x recording still
declares `false` and is still refused, by the capability sentence)*.

**One config shape is refused by name.** A `test.projects` or
`test.workspace` config makes vitest resolve a config PER PROJECT, and this
wrapper merges onto one: the plugin never reaches the projects' pipelines, so
the suite runs and nothing is recorded. The wrapper config refuses it at load
time — `vitest projects/workspaces are not supported by sensorium-ts 0.2.0` —
and leaves that sentence in the spool directory (`wrapper-refusal.json`) for
the driver to print at exit 2. *(Added 2026-09-09, ruling R41: measured, such
a run came back as the CONVERTER's sentence, "nothing was recorded, or the
recorder wrote somewhere else" — the right exit status, naming neither the
cause nor the fix.)*

**The footprint on the consumer's tree.** One directory is written:
`<root>/node_modules/.sensorium/`, holding the wrapper vitest config and the
setup file the driver writes from a template. No source file is touched, no
dependency is added, and the consumer's own config is merged rather than
replaced — `setupFiles` are **appended** to the user's, never swapped for
ours. The directory is removed in a `finally`, so it exists only for the run.
A read-only `node_modules` is a refusal at exit 2 naming the directory, never
a write somewhere else in the source tree.

**Falsifiers.** `E2′`, `E3-TS`, `E5′`, `E6′`, `E6″`, `E7′`, `H-probes`
(`typescript/probes/nodetest/`, four extensions and two controls),
`typescript/test/transform.test.mjs`, `typescript/test/hook.test.mjs`
(`R37: a CommonJS file under the root is loaded as Node loads it, and
counted`), `tests/test_ts_driver.py`, `tests/test_ts_ingest.py`,
`tests/test_ts_ingest_refusals.py`,
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
  NEW pre-registration, **E6″**. **The rung therefore ships DONE-WITH-STOP**,
  which is the phrase the record, the spec, the CHANGELOG and both READMEs use
  for it, so a reader meets one name for one fact. This ledger states it as a
  STOP because that is what the pre-registration's own words make it, and a
  rung that ships with one is a rung that ships with one.


**Measured, slice 2** *(added 2026-09-10; every number from
`../docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md` §3 and §4,
on the same lens)*:

- **Conversion, the ladder.** Rung 1's design input was taken and answered on
  the pinned 372-spool, 414,450,522-byte copy of one recording, every cell
  guarded and each lever measured before the next was written. **Arm 0** (the
  0.9.0 converter): full suite at 16 jobs **45.7378 s**, the one file
  **0.3624 s**, the heaviest worker's peak resident **2,273,872 kB** on the
  big-spool cell. **A1** — one transaction per trace, `synchronous=NORMAL`:
  **17.7740 s** and **0.1647 s**, RSS unmoved at **2,273,996 kB** (it is not
  the quantity this lever touches). **A3** — the streaming spool reader:
  **16.5088 s** and **0.1628 s**, and peak resident **280,408 kB** on that
  same cell, **8.1096×** below A1's. **A2** (largest-first dispatch) and **A4** (the per-record Python
  cost) were **not built**: the spec conditioned them on the first two levers
  leaving the suite above the bound, and they did not; a lever that cannot
  move a verdict is not free.
- **Conversion, the verdicts.** **E10′-suite PASS** — **16.3859 s** median,
  n=5, against the pinned **22.5925 s** wall: **the converter stays Python**
  and Arm B is not raised. **E10′-file PASS** — **0.1648 s** median, n=5,
  against **0.4002 s**, which was the one clause on this ladder allowed to
  **STOP** it; it did not fire. **E10′-eq PASS** — the set converted twice,
  **372 MATCH / 0 DIVERGED / 0 REFUSED**, the only `meta` key differing on any
  pair being the minted `run_id`. Beside it, reported and never gated,
  **E10′-eq-content**: every row of all seven tables compared column for
  column, **372 / 372 identical**.
- **One cost this slice does not have a number for.** The non-durable writer
  holds a whole trace's WAL until `close()`: measured once at `--jobs 1`, a
  **335,895,392-byte** `-wal` beside a **333,832,192-byte** database, so
  transient disk is ≈ **2×** per in-flight trace and, at the default job
  count, the sum over the workers building at that moment. Nothing came near
  the disk on any cell here (63 GB free), so no verdict rests on it — but this
  box has run at ~3 GB free, and the peak at 16 jobs is unmeasured. It is in
  `docs/CARRIED-DEBT.md`.
- **And the STOP is answered.** E6′'s plain-band clause STOPped at rung 1.
  **E6″ — PASS**, on all five clauses of a NEW pre-registration: manifest
  **748 OK / 0 FAILED** before and after, all ten plain runs at
  `372 passed (372)` / `4278 passed (4278)` with **nothing dropped**, **0**
  `__srt` markers over the 2 cache directories that exist, the wrapper
  **absent**, and the after arm's median **22.1136 s** inside the band
  **[21.9834, 22.3652]** the before arm's own median (**22.1743**) and range
  (**0.1909**) define — 0.0607 s **faster**, not slower. The instrument E6′
  lacked is what makes this readable: a load guard on every timed run with its
  reading in the artifact, a band derived from the arm rather than chosen, and
  medians over n=5 on each side. What it closes is one session, one lens, one
  recorder, and the record's §5 says what it does not settle — the band's
  width is a property of the session, and "under 4.0" is not "idle".

**Measured, rung 2** *(added 2026-09-10; every number from
`../docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` §3, on the
same lens, with a load guard on every timed run and its reading beside every
wall — the highest 1-minute load any arm ran under was **3.91**)*:

- **Recording, again.** `off/plain` **1.0608** and `call/plain` **1.1266**,
  n=5 per arm, interleaved, 15 of 15 runs green, conversion excluded (`E1‴`).
  Rung 1 read **1.0587** and **1.1324** on the same lens with a recorder that
  did not yet splice a `catch` word, a callback wrapper or a `finally` sink,
  so the throw flow's whole cost is inside the difference between those two
  pairs — which is to say inside the noise this instrument can resolve. It
  gates nothing either way, and the transform stays uncached.
- **Conversion, again.** The rung's own 372-spool set (**414,599,103 B**)
  converts in **16.0715 s** at 16 jobs (n=5), and its `useMeshVoice` spool
  (**611,325 B**) in **0.1642 s** (n=5) — beside slice 2's **16.3859 s** and
  **0.1648 s** on the pinned set (`E10″`). No gate; the converter stays
  Python.
- **What the recorder wrote about throws, over 372 member traces.** HANDLED
  records by `how`: `catch` **36**, `catch_callback` **182**,
  `catch_escaped` **22**, `sink_empty_catch` **37**,
  `sink_empty_catch_callback` **8** — **285** in all, from **287** spliced
  sites of **287** eligible (`E2″`, ratio **1.0000**, zero named exclusions).
  The escape rule's own verdict distribution over that lens: **22 of 177**
  catch clauses read `catch_escaped` — **0.1243** — with `catch` **87** and
  `sink_empty_catch` **68** beside it. Reported, gated by nothing.
- **And what the rules made of it.** Over the same run, `swallowed` **261**
  and `ambiguous` **53** across **314** raises in **53** of 372 processes;
  **30** SWALLOWED shapes printed, every one hand-adjudicated, **0** of them
  false (`E6-TS′`). Fifteen of the thirty needed a second reading, and
  **13** of the 30 AMBIGUOUS shapes read the escaped-handler reason. What
  those numbers do NOT establish is a false-negative rate: the gate asks
  whether an accusation is true, and a swallow this recorder never saw makes
  no shape to adjudicate.

**Falsifiers.** `E1′`, `E10`, `E10′`, `E6′`, `E6″`, `E1‴`, `E10″`, `E2″`,
`E6-TS′`.

## 10. Blind spots

Numbered so a later document can cite "blind spot 3" and mean this one. Each
names what the trace carries in its place, and what could falsify the claim
that this is the whole of it.

The list itself — items **1–17** from rung 1, **18–27** that rung 2 adds for
the throw flow — is [`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md), **moved
there 2026-09-10 so this file stays under 800 lines**, on Rust's precedent
([`../rust/HONESTY-BLIND-SPOTS.md`](../rust/HONESTY-BLIND-SPOTS.md), 2026-09-05).
**The numbering there is unchanged**, so "blind spot 13" still names what it
always named, one file away. Items **2**, **3** and **11** are **struck** there
rather than deleted — this runtime records the shapes they said it did not —
and **13** is narrowed; a struck item stays visible, because a reader who last
met this list under `sensorium-ts 0.1.x` needs to see which of its holes closed
and when.

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
| 4 | RAISE marks `throw` statements only; HANDLED marks `catch` clauses, rejection handlers and the two clause-less sinks; the nine `how` words are the enumeration of shapes that record at all | `E8″`, `E2″`, `typescript/probes/src/swallow.probe.test.ts`, `typescript/test/transform.test.mjs`, `docs/trace-format/vectors/v25-exc-kind-throw-rejection.json` |
| 4 | A catch binding's word is decided from its own AST — logged-only is `catch`, any other mention is `catch_escaped`, a bare rethrow is a traced exit and not a mention — and the same rule reads a rejection handler's parameter | `typescript/test/escape.test.mjs`, `typescript/test/golden/`, `typescript/probes/src/escape.probe.test.ts`, `E8″` |
| 4 | A `finally` that completes records `sink_finally_return` only under an in-flight mark, and its `exc` is the marked throw's own, complete — `kind`, `type`, `msg`, `serial`, nothing `unread` | `typescript/test/rt.throw.test.mjs` (`mark`, `handledFinally`), `typescript/test/rt.test.mjs`, `corpus/typescript/finally_return`, `E8″` |
| 4 | A rethrown OBJECT keeps its serial (one exception, two RAISE rows, a hop); a rethrown primitive gets a fresh one and cannot be followed | `typescript/test/rt.test.mjs` (`serial survives rethrow`), `docs/trace-format/vectors/v25-exc-kind-throw-rejection.json` |
| 4 | A RAISE or HANDLED with no open frame is written as no event and counted in `throw_flow_outside_frames` | `typescript/probes/src/swallow.probe.test.ts`, `tests/test_ts_ingest.py` |
| 4 | Unhandled rejections are meta, never events, and `info` prints a zero on a complete trace because the listener always ran | `docs/trace-format/vectors/v27-unhandled-rejection-in-meta.json`, `corpus/typescript/unhandled_rejection_in_info`, `tests/test_ts_ingest.py` |
| 4 | These rows are judged: `err_flow: true`, and `exceptions` answers in this recorder's five dispositions — SWALLOWED only on an absorbing `how` in a frame that returned, with no escaping handler for the serial anywhere, and 0 false of 30 adjudicated on somebody else's suite | `E6-TS`, `E6-TS′`, `tests/test_exceptions_typescript.py`, the seventeen throw-flow cases under `corpus/typescript/`, `docs/trace-format/vectors/v30-exceptions-typescript-swallowed.json` |
| 4 | A trace a 0.1.x runtime wrote declares `err_flow: false` and is still refused at exit 3, by the capability sentence naming the recorder | `docs/trace-format/vectors/v32-err-flow-typescript-capability-refusal.json`, `tests/test_exceptions_invocation_typescript.py` |
| 4 | Rule 5's catch-all names an untraced catcher (three variants) before it prints unnamed; rule 4's absorbing conjunct is window-scoped, not trace-global; a second `ambiguous by reason:` line prints when non-empty | `E6-TS‴`, `E6-TS′-fence`, `corpus/typescript/{untraced_catcher,untraced_catcher_rejection,untraced_catcher_later_failure,logged_rethrow_to_harness}`, `docs/trace-format/vectors/v34-exceptions-typescript-untraced-catcher.json` |
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
| 9 | Cost is reported again at rung 2 with the throw flow spliced in: `off/plain` 1.0608, `call/plain` 1.1266, conversion 16.0715 s — and none of the three gates anything | `E1‴`, `E10″` |
| 10 | The blind-spot list — now [`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md) — is the whole of what this recorder cannot see, each item carried by a meta key, an `info` line or a stated absence | each item's own falsifier, 1 through 27 *(10–17 added 2026-09-09; 18–27 added 2026-09-10, when 2/3/11 were struck and 13 narrowed)* |
