# Sensorium S5 rung 2 — throw flow: `exceptions` on a TypeScript trace: design

**Date:** 2026-09-10
**Status:** design, awaiting Brice's read; then writing-plans
**Follows:** `2026-09-09-sensorium-typescript-recorder-design.md` (rung 1;
its §3.3, §4 "Exceptions", D7, D15 and §11 item 2 are this rung's brief) and
`2026-09-10-sensorium-s5-slice2-design.md` (slice 2, merged as 0.9.1 /
`sensorium-ts` 0.1.1)
**Precedent:** `2026-09-04-sensorium-rung3-err-flow-design.md` (the Rust
transfer of `exceptions`: R2's escape rule, R8's ambiguous-by-default, R15's
E6 shape) and its two amendments
**Precedes:** rung 3 (tiers: `--focus`, argument capture, LINE)

---

## 0. Provenance

`sensorium exceptions` answers on Python traces with five dispositions and
on Rust traces with five of its own, and **refuses a TypeScript trace at
exit 3**: *"REFUSED: exceptions on a typescript trace needs the TypeScript
disposition rules (S5 rung 2); the Python rules index exception identity
this trace does not carry; nothing was judged"*. The rows are there — every
`throw` statement writes a RAISE, every `catch` clause a HANDLED, a frame
left by throwing an UNWIND with the thrown value, an unhandled rejection a
meta entry — and `capabilities.err_flow` is `false` because no rule reads
them (rung-1 spec D15; `typescript/HONESTY.md` §4).

**What the wire already settles, and what it does not.** Identity is a
per-object `serial` minted through a `WeakMap` (`typescript/src/dbg.mjs`),
so `catch (e) { throw e }` is one exception with two RAISE rows and a
rethrow across an `await` keeps its serial; a thrown primitive gets a fresh
serial each time and cannot be followed. HANDLED rows come only from real
`catch` clauses and one sink, `.catch(() => {})`, so TypeScript has none of
the implicit-handler noise that makes Python's rule hard (CPython fires
HANDLED on `finally` and on `await` cleanup — `exceptions_cmd.py`'s
docstring). Three shapes produce no record today and would generate false
verdicts under any rule: a `.catch(fn)` with a non-empty body and a
`.then(_, onRejected)` (a rejection they handle would read *propagated,
handler not in traced code*); a `finally { return … }`, which discards an
in-flight throw in JavaScript; and a catch binding that escapes (`return e`,
`expect(e.message)`, `String(e)`), indistinguishable today from a sink.

**The precedent.** Rust's rung 3 met the third of those on its first
acceptance and STOPped: `Err(e) => Ctx { reason: format!("{e}") }` read
SWALLOWED while the rendering reached every caller. Its amended R2 is the
rule this rung transfers: a bound error mentioned only as a **logging**
call's argument is a swallow (the log is where the failure went); mentioned
anywhere else, it **escapes** and the arm reads AMBIGUOUS, never SWALLOWED.
Its E6 shape is the falsifier: zero false SWALLOWED on the corpus (set
equality) and on the lens (every SWALLOWED line hand-adjudicated against the
source). Rust's HONESTY §11 defines the adjudication and is quoted in §7.

**Rulings from the brainstorm (2026-09-10).** Brice ruled the scope: the
**full transfer** — the rules module AND the records the honest verdicts
need (callback handlers, the escape rule, the `finally` sink), rather than
rules over today's records with the gaps declared. Brice approved approach
1 of three (the paragraph below). Design decisions are Claude's under the
2026-09-07 delegation and are listed with their cost in §11.

**Approach, and the two not taken.** (1) **Taken:** Python's rule shape
over serial identity — a HANDLED in a frame that then returned, with no
later RAISE of the same serial, is the swallow candidate — plus Rust's
discipline: ambiguous by default, an escape bucket decided at transform
time, grouped one-block-per-shape output across an invocation. (2) Rust's
chain machine at conversion: the wrong tool, since Rust minted chains
because an `Err` has no wire identity and a TypeScript object does. (3)
Rules over today's records with the gaps declared: cannot meet the
pre-committed falsifier on the lens; ruled out by Brice.

## 1. Goal, scope, non-goals

**Goal.** `sensorium exceptions <run>` and `sensorium exceptions
<invocation>` answer on TypeScript traces with Python's five words —
`swallowed`, `uncaught`, `re-raised`, `propagated`, `ambiguous` — and every
SWALLOWED they print is one the recording establishes.

**In scope.**

- The transform and runtime gain the records the verdicts need (§2): the
  catch-binding escape rule, rejection callbacks of every shape, the
  `finally`-with-completion sink, `capabilities.err_flow: true`.
- A TypeScript rule module (§3) and the invocation mode's language dispatch
  with a TypeScript shape key (§4).
- Converter pass-through, the contract's amendments after a split, four
  vectors (§5).
- The swallow corpus, the probe's new shapes, the ledger's rewrite (§6).
- Pre-registered endpoints, E6-TS and E6-TS′ among them (§7).
- Versions: `sensorium-ts` **0.2.0**, Python **0.10.0** (§10).

**Non-goals, each named so its absence is a choice.**

- Argument capture and LINE (rung 3); refocus (rung 4); the browser runtime
  (rung 5).
- A Python-side grouping of `exceptions` output: still one block per raise
  there, awaiting a definition of a Python verdict's site (`docs/query.md`).
- An event for an unhandled rejection: it stays in meta and the rule reads
  it by serial (R1).
- Following a rethrown primitive: no identity exists; the verdict says so.
- Loggers other than `console.*`: they escape, the safe direction (R3).
- `jest`, still refused by name.

## 2. The records the wire gains

Four changes to `typescript/src/transform.mjs` and `typescript/src/rt.mjs`,
every splice newline-free (the rung-1 invariant, `lines(out) == lines(in)`),
every one writing the existing HANDLED record with a new `how` word. The
wire stays **version 1**: the additions are words in an enumeration and one
capability flag.

### 2.1 Catch bindings are classified at transform time (R2 transferred)

A `catch (e) { … }` clause's `how` is decided from its body:

- **`catch`** — the body never mentions the binding, or mentions it **only
  as an argument of a logging call**: `console.log`, `console.error`,
  `console.warn`, `console.info`, `console.debug`, `console.trace`, at any
  argument position, including inside a template literal or a `String(e)`
  that is itself that argument. Log-and-continue is the archetypal swallow:
  the failure never reached the caller, the log is where it went.
- **`catch_escaped`** — the binding appears anywhere else: `return e`, `throw
  new Wrapped(e)`, `expect(e.message)`, `err = e`, `list.push(e)`, a
  template literal or `String(e)` whose value is used, an argument to any
  non-logging call, a closure that captures it. The failure, or a rendering
  of it, reached something; the rule does not follow where.
- **`sink_empty_catch`** — an empty block, as today.
- A clause with no binding reads `catch` (nothing can escape); a
  **destructuring** binding reads `catch_escaped` (the runtime cannot see
  what it bound; blind spot 13 becomes a declared escape).
- A **bare rethrow** — `throw e;`, or `throw (e);`, whose operand after any
  parentheses is the binding ITSELF — is a traced EXIT and not a mention: it
  does not count towards `catch_escaped`, and the clause's `how` is decided by
  whatever else its body does with the binding. So `catch (e) { throw e }` and
  `catch (e) { console.error(e); throw e }` read `catch`, while
  `catch (e) { list.push(e); throw e }`, `catch (e) { throw new Wrapped(e) }`,
  `catch (e) { throw e.cause }` and `catch (e) { throw wrap(e) }` stay
  `catch_escaped`. The exclusion holds at closure depth 0 only: a `throw e`
  inside a nested function within the body is an escape by the closure rule,
  because the closure keeps the binding. The value reaches nothing — it leaves
  the way it arrived — and the RAISE the throw writes carries the same serial,
  which is what the rule module reads (a rethrow with the same serial is a hop,
  §3.3 rule 2). The exclusion applies to §2.2's rejection callbacks as well —
  one rule, two syntaxes — since §2.2 defines a callback's word as this rule
  applied to its parameter and a rethrow from a handler carries the serial the
  same way: `.catch((e) => { throw e })` reads `catch_callback`, while
  `.catch((e) => { seen.push(e); throw e })` and
  `.catch((e) => { throw wrap(e) })` stay `catch_callback_escaped`, a
  non-inline handler stays `catch_callback_opaque` and an empty body stays
  `sink_empty_catch_callback`. *(Amended 2026-09-10 at Task 6: the original text and
  `escape.mjs` counted a bare rethrow as an escape, which made rule 3's
  escaping conjunct bar every `throw e` hop from SWALLOWED and contradicted
  §3.3, §6.1's `rethrow_hop` row and R4; ruled at execution.)*

The analysis is syntactic, over the clause's own AST, closure depth 0 and
below (a mention inside a nested function body escapes: the closure keeps
`e`). It is Rust's `escape.rs` transferred with JavaScript's logging family
in place of the macro list.

### 2.2 Rejection callbacks are recorded, whatever their shape

`p.catch(<arg>)` and `p.then(<x>, <arg>)` wrap `<arg>` the way
`spliceEmptyCatchCallback` wraps an empty arrow today:
`__srt.catchCb(__sf, <line>, <how>, (<arg>))` returns a function that records
HANDLED `{kind: "rejection"}` with the reason it was given, then calls the
original with the same `this` and argument and returns its result — a
wrapper that must not change what the handler does. `<how>` is decided at
transform time from the argument's shape:

- an inline arrow or `function` expression with an **empty** body →
  `sink_empty_catch_callback` (today's word, now for the `function` spelling
  too — blind spot 11 closes);
- an inline arrow or `function` with a parameter → **`catch_callback`** or
  **`catch_callback_escaped`** by §2.1's rule applied to the parameter over
  the callback's body; a parameterless non-empty body → `catch_callback`;
- **anything else** — an identifier, a member reference, a call returning a
  function — → **`catch_callback_opaque`**: the handler is a function
  defined elsewhere, and whether it swallows is not this splice's to say.
  (A named handler that is itself instrumented has its own frame; a
  rethrow from it carries the serial and reads as a hop; a return from it
  is not evidence of a swallow, because its parameter's fate was not
  analysed.)

`p.catch()` with no argument and `.then(x)` with one are not touched.
`.finally(fn)` is not a handler and records nothing.

### 2.3 A `finally` that completes is a sink

A `finally` block containing a `return`, `break` or `continue` at closure
depth 0 discards an in-flight throw. It gains `__srt.handledFinally(__sf,
<line>)` as its first statement, which records HANDLED `how:
sink_finally_return` **only when a throw is in flight**, read from a
one-slot **mark per frame** holding the serial of the exception now
travelling through that frame: `raise(f, e)` sets `f`'s mark to `e`'s
serial; `thr(f, e)` (the callee's frame closing by throw) sets the mark of
`f`'s **parent** frame, where the exception is now in flight; `handled(f, …)`
clears `f`'s mark. `handledFinally(f)` writes the record when `f`'s mark is
set — `exc` is `{kind: "throw", serial: <the mark's>, unread: ["type",
"msg"]}`, since the block has no binding and the runtime holds no reference
to the value — and then clears it. The serial keeps identity intact, so the
rule module pairs the sink with its RAISE like any other HANDLED. A throw
that traced code never raised — a library's, a `reject()`'s — sets no mark,
so a `finally` that discards one records nothing: a declared blind spot. A
`finally` with no completion statement records nothing, as today.

### 2.4 The capability

The BOOT record's `capabilities` gains `err_flow: true`; the converter
passes it through untouched (`_meta`'s `capabilities` is `dict(CAPABILITIES)`
today; it becomes the BOOT's). A spool whose BOOT lacks the key reads
`false`, so a 0.1.x spool converted by this converter still refuses at exit
3 — with the **capability** sentence now, `caps.require`'s: what it lacks is
a record.

### 2.5 The enumeration, and what still produces nothing

`how` ∈ `throw`, `catch`, `catch_escaped`, `sink_empty_catch`,
`catch_callback`, `catch_callback_escaped`, `catch_callback_opaque`,
`sink_empty_catch_callback`, `sink_finally_return`. The enumeration is the
declaration: a shape outside it produced no record. Still unrecorded, each
named in HONESTY: a `finally` without a completion statement; `.finally(fn)`;
a `Promise.reject(v)` (not a `throw`: its handler's HANDLED has no RAISE, and
reads *born outside a throw statement*); a throw inside a promise executor
with no open frame (counted in `throw_flow_outside_frames`); a throw in
untraced code (`JSON.parse`, a library) — its HANDLED has no RAISE and reads
*born outside traced code*.

## 3. The rules module

`src/sensorium/query/exceptions_typescript.py`, dispatched on `trace.lang ==
"typescript"` in `exceptions_cmd.run` **before** any Python rule touches the
trace (the Rust dispatch's shape), gated by `caps.require(trace, "err_flow",
"exceptions")` so a 0.1.x trace refuses at exit 3 with the capability
sentence. It shares `exceptions_cmd.Disposition`, the header, the tally
order (`TAG_ORDER = ("swallowed", "uncaught", "re-raised", "propagated",
"ambiguous")`, Python's), `--after`/`--limit` paging, `fmt_event` and
`fmt_exc`. It computes dispositions and nothing else: identity is the
recorder's serial, read and never recomputed.

### 3.1 Identity

Every RAISE, HANDLED and frame UNWIND (`unwind_exc`) carries `exc.serial`.
A **window** runs from one RAISE to the next RAISE of the same serial, so a
loop that rethrows one object pairs each raise with its own handler. A
primitive throw carries a fresh serial on every record, the HANDLED's
included, so its rows never share one: within **one frame**, a primitive
RAISE pairs with the next HANDLED in that frame carrying equal `type` and
`msg` and no serial-matched RAISE between them; any other pairing of
primitives — across frames, or after a rethrow — is `ambiguous (a primitive
has no identity across a rethrow)`. Two objects are never merged on text.

### 3.2 The index

Per trace: RAISE events by serial; HANDLED events by serial and by frame;
frames' `closed_by` / `unwind_exc` / `frame_state`; the task each frame
belongs to and each task's **root frame** (the frame in the task with no
parent, `caller: "untraced"`); meta `unhandled_rejections` by serial; meta
`incomplete`. A HANDLED whose serial no RAISE minted opens its own entry
(born outside a throw statement, or outside traced code).

### 3.3 The classifier, in order, for every RAISE and every orphan HANDLED

1. **uncaught** — the serial is in `unhandled_rejections` and no later RAISE
   carries it. Detail: `unhandled rejection; raised at <site>`, or `unhandled
   rejection; born outside traced code (a reject() or a library)` for an
   orphan.
2. **re-raised** — a later RAISE with the same serial exists. The origin's
   line lists every hop (`e3 raise L12 → e9 raise L30 → …`) and points at
   the last raise's verdict, `re-raised → <that word>`; **every RAISE keeps
   its own block and its own tally entry**, as Python's output does (the
   rethrow's block carries its own verdict by rules 1, 3–5), so tallies
   count RAISE events and stay comparable line for line.
3. **swallowed** — a HANDLED with `how` in the **absorbing set** — `catch`,
   `sink_empty_catch`, `catch_callback`, `sink_empty_catch_callback`,
   `sink_finally_return` — sits in a frame that later closed by `return`,
   no later RAISE of the serial exists, and **no** HANDLED for the serial
   anywhere is in the escaping set (`catch_escaped`,
   `catch_callback_escaped`, `catch_callback_opaque`). Python's thrown-in
   clause does not transfer: this wire's RESUME carries no `thrown` key, so
   a handler frame that later unwound for any reason is rule 5's, never
   this one's. Detail: `SWALLOWED -- caught by <how> at e<id> (<qualname>
   L<line>) in f<id>, which returned`, plus `born outside traced code` /
   `born outside a throw statement` for an orphan.
4. **propagated** — no HANDLED in the absorbing set, and the serial's last
   UNWIND closes the task's **root frame**, or a frame whose parent is
   untraced. Detail: `to the harness: test "<task name>" failed` for a task
   root, else `handler not in traced code`. As coded
   (`src/sensorium/query/exceptions_typescript.py`, `_propagated` and
   `_still_open_absorber`) this rule declines in two further places, both
   narrowings of the sentence above: **(a)** whenever **any** HANDLED for the
   serial is in the **escaping** set — rule 5 then answers it with the escaped
   reason, and since rule 4 runs first the conjunct has to sit here for rule 5
   to be reached at all; and **(b)** when an **absorbing** HANDLED sits in a
   frame that has **not yet returned** — an absorbing handler whose frame DID
   return is rule 3's or, for a rethrown serial, an earlier window's and no
   evidence about this one, while a parked `.catch(async …)` frame unwinding
   beneath a live handler is not evidence the harness saw the failure (the
   Task-4 review fix, `7c2ead1`). *(Amended 2026-09-10 at the final review:
   the rule as coded and as MEASURED — the record's E6-TS′ tally was produced
   under it; the coded reading is the safe direction, it never accuses; a
   handler that escaped and then rethrew out of the test root reads AMBIGUOUS
   where PROPAGATED would be truer — carried in CARRIED-DEBT.)*
5. **ambiguous** — everything else, each with its reason printed: an escaped
   or opaque handler (`caught at e<id> (<how>), and the error or a rendering
   of it left the handler; not followed`); a handler frame still suspended
   at the end of the recording; a handler frame that later unwound with a
   different serial (`a translation or a later failure, indistinguishable`);
   a primitive rethrow; an orphan HANDLED with an escaping `how`; a recording
   that never finalized (`INCOMPLETE`, the cut named). Nothing reaches
   SWALLOWED by falling through.

A HANDLED in the absorbing set whose frame **never closed** is ambiguous,
not swallowed. An UNWIND is never itself a verdict: it is the evidence rule
4 reads.

### 3.4 What is printed

The per-raise block is Python's shape (`e<id> RAISE <qualname> raise
<Type>('<msg>') L<n>` then the verdict line), the header is this recorder's
(`raised (N):`, then `INCOMPLETE` when it applies), and the tally line is
`dispositions: swallowed n, uncaught n, re-raised n, propagated n, ambiguous
n`. Grouping (§4.2) applies to the per-trace output too. No Python or Rust
word appears: no `oid`, `chain`, `Err`, `asyncio`, `coroutine`, `Rust
disposition`; E7″ holds it.

### 3.5 Exit codes

As `exceptions` today: dispositions listed → **0**; `no exceptions recorded`
on a finalized trace → **1**; `no RAISE events recorded (see INCOMPLETE
above)` → **3**; the capability refusal → **3**; a bad `--limit`/`--after`
→ **2**.

## 4. The invocation mode

### 4.1 Dispatch

`exceptions_invocation.run` opens every member trace and dispatches each on
its `lang`: Rust members through `exceptions_rust`, TypeScript members
through this module; a Python member is impossible (only the two drivers
write `meta.invocation`) and stays refused by name. A member whose recorder
declares `err_flow: false` refuses the whole answer, naming it, as today; a
member that never finalized is named above any verdict; `--after` stays
refused at exit 2 in this mode.

### 4.2 The shape key

Two verdicts are one **shape** when they share the disposition, the **site
the verdict is about**, and the verdict text with event and frame ids
masked. The site, per disposition: the sink's `file:line` (the HANDLED's)
for `swallowed`; the escaped or opaque handler's site for that kind of
`ambiguous`; the origin RAISE's site for `uncaught`, `re-raised`,
`propagated` and every other `ambiguous`. `exceptions_group`'s `Shape`,
`group_chains` and `print_shape` are generalised over a `site(disposition)`
callable each language module supplies; the printed bracket, the
`origins/messages/details/routes: N distinct (first shown)` flags and the
`--limit`-counts-shapes rule carry over verbatim.

### 4.3 The header

`invocation <id>: <harness_command as typed> -- 372 processes, 41 with
throws, 331 with none`, then `raised (N raises over M processes, K swallowed
shapes):` — the noun corrected on 2026-09-08 for Rust, adopted here from the
start.

## 5. Converter, contract, vectors

### 5.1 Converter

`src/sensorium/ts/build.py`: the BOOT record gains a `capabilities` map
(today it carries none) and `_meta`'s `capabilities` becomes that map
merged over today's constant when present, else the constant alone; the new
`how` words need no converter change (the payload is `{"exc", "how"}` as
before); a `sink_finally_return` record with `serial: null` is written as it
arrives. `throw_flow_outside_frames` unchanged. **RAISE and HANDLED are
causal kinds**, so every new HANDLED row moves fingerprints and event ids:
E3-TS″ re-measures the comparator (§7), and the existing TypeScript corpus
questions that pin event ids are re-pinned with the reason stated per
question (Rust R12's precedent).

### 5.2 The contract

`docs/TRACE-FORMAT.md` is at 799 of 800 lines and two of its sentences
become false (§5's *TypeScript throw flow* enumeration and "the rows are not
judged"; §4's capabilities row calling `err_flow` Rust-only). **The split
comes first** (R25's precedent): the *TypeScript throw flow* subsection
moves to `docs/trace-format/TYPESCRIPT-KEYS.md` under a one-line pointer,
and is amended there with the nine words, the `serial: null` case, and the
capability. The `err_flow` row reads "Rust and TypeScript; the Python
column never declares it". `docs/query.md`'s `exceptions` section gains the
TypeScript paragraph and its own five-word sentence.

### 5.3 Vectors

`v30-exceptions-typescript-swallowed` (a `catch` sink in a returning frame →
SWALLOWED, exit 0); `v31-exceptions-typescript-escaped-ambiguous` (a
`catch_escaped` → AMBIGUOUS with its reason, never SWALLOWED);
`v32-err-flow-typescript-capability-refusal` (a 0.1.x-shaped trace,
`err_flow: false`, refuses at exit 3 with the capability sentence — the
refusal `corpus/typescript/exceptions_refused` pinned moves here, since no
new recording can produce it); `v33-exceptions-typescript-invocation-shape`
(two members, one swallowed shape `[×2 over 2 processes: …]`).

## 6. Corpus, probes, ledger

### 6.1 The swallow corpus

Under `corpus/typescript/` (one vitest project, P9's layout), one shape per
case, each with an `exceptions` question whose `expect_line` pins the
verdict line and the tally, and a `why_logs_fail` naming all three channels:

| Case | Shape | Verdict pinned |
|---|---|---|
| `silent_swallow` | the existing `exceptions_refused` source: `parse` throws inside `loadConfig`'s empty `catch` | SWALLOWED at the sink; tally `swallowed 1` |
| `logged_catch` | `catch (e) { console.error(e) }` | SWALLOWED, detail names the logging catch |
| `escaped_catch` | `catch (e) { return String(e) }` | AMBIGUOUS (escaped), never SWALLOWED |
| `asserted_catch` | `catch (e) { expect((e as Error).message).toBe(…) }` — the lens's dominant shape | AMBIGUOUS (escaped) |
| `rethrow_hop` | `catch (e) { throw e }` caught by an outer empty catch | two RAISE blocks: the origin `re-raised → swallowed` with its hop, the rethrow SWALLOWED; tally `re-raised 1, swallowed 1` |
| `translated` | `catch (e) { throw new Wrapped(e) }` | origin AMBIGUOUS (translation), the wrapper's own raise judged on its own |
| `callback_sink` | `await Promise.reject(new Error()).catch(() => {})` | SWALLOWED, born outside a throw statement |
| `callback_handled` | `.catch((e) => { console.warn(e) })` | SWALLOWED |
| `callback_escaped` | `.catch((e) => { seen.push(e) })` | AMBIGUOUS |
| `callback_opaque` | `.catch(handler)` | AMBIGUOUS (opaque) |
| `await_rejection_caught` | `try { await f() } catch {}` with the throw inside `f` | SWALLOWED, one serial across the await, hop shown |
| `test_failed` | an `expect` that fails | PROPAGATED to the harness, test named |
| `unhandled_rejection` | the existing `unhandled_rejection_in_info` gains the question | UNCAUGHT (unhandled rejection) |
| `primitive_rethrow` | `catch (e) { throw e }` on a thrown string | AMBIGUOUS (primitive) |
| `finally_return` | `try { throw … } finally { return x }` | SWALLOWED via `sink_finally_return` |
| `dependency_throw` | `JSON.parse('{')` inside an empty catch | SWALLOWED, born outside traced code |
| `suspended_handler` | a handler in an async frame parked at the end | AMBIGUOUS (frame still suspended) |

*Amended 2026-09-10 at Task 6 — four rows read differently in the measured
output, none moving a count: `silent_swallow` prints `caught by catch` (the
clause returns; it is not `sink_empty_catch`); `translated`'s origin prints the
escaped reason, not a translation reason (§3.3 rule 5 reaches the translation
reason only when no escaping handler exists, and this shape's clause binds
`e`); `await_rejection_caught` prints no hops line (one RAISE, so there is no
hop); `test_failed` is a `throw` statement, not a failing `expect` — a failing
`expect` throws inside vitest's untraced code and writes no RAISE row, so
`exceptions` can only reach `to the harness` from a throw in traced code (an
assertion failure born in `expect` shows in `info`'s exit line, not in
`exceptions`; HONESTY records this at Task 8).*

`exceptions_refused` is renamed to `silent_swallow` (same source; the old
question becomes v32). `tests/test_corpus.py`'s three-channel guard applies
to every new case.

### 6.2 Probes

`typescript/probes/src/swallow.probe.test.ts` gains the new shapes with
`// SWALLOW <shape> <kind> <how>` markers (logged catch, escaped catch,
callback handled/escaped/opaque, finally return, the `function`-spelled
empty callback); `check.mjs`'s `SWALLOW_EXC` table grows with them; E8″
counts them per shape. A new `escape.probe.test.ts` holds one clause per
escape-rule branch (each mention position of §2.1) with the expected `how`
in its marker, so the rule's table is pinned by a running probe and not only
by goldens.

### 6.3 The ledger

`typescript/HONESTY.md` §4 is rewritten by dated amendment: the promise
becomes *every RAISE and HANDLED is judged, and SWALLOWED is claimed only
where the recording establishes it*; the enumeration, the escape rule, the
absorbing and escaping sets, and what still produces nothing (§2.5). Blind
spots 2 (`.catch(fn)` non-empty), 3 (`finally`, narrowed to "without a
completion statement"), 11 (the `function` spelling) and 13 (destructuring,
now a declared escape) are struck or amended. New blind spots: a logger
other than `console.*` escapes (safe); a binding captured by a closure
escapes (safe); a `finally` sink cannot name what it discarded; a rethrown
primitive; a handler defined elsewhere is opaque; a `Promise.reject` has no
origin site. `typescript/README.md` and `README.md` say `exceptions` answers.

## 7. Pre-registered endpoints

Written into the acceptance record's §1 at T0 and byte-locked before the
transform changes. **Lens:** the VTT frontend copy at `0091e97`
(`/mnt/extra/sensorium-s5/vtt/frontend`), vitest 4.1.9, node v24.16.0; store
`/mnt/extra/sensorium-s5/store-rung2ts`; every timed arm behind the load
guard (1-minute load under 4.0, the reading written beside every wall).

| Id | Question | Measurement | Rule |
|---|---|---|---|
| E6-TS | Are the corpus's verdicts the pre-registered ones? | `exceptions` on every TypeScript corpus case with an `exceptions` question | the printed SWALLOWED lines `==` the pre-registered set per case (equality, not subset); every swallow case's set non-empty; the `dispositions:` tally compared whole; any difference → STOP |
| E6-TS′ | Does the recorder accuse falsely on somebody else's suite? | `exceptions <invocation>` over ONE fresh guarded call-tier full-suite run on the lens; every printed SWALLOWED shape adjudicated by hand against the VTT source | gate **0 false SWALLOWED**; a false one → STOP (the rung ships DONE-WITH-STOP with an amendment slice, Rust's precedent). Reported beside it: the per-disposition tally, the count of escaped-ambiguous shapes, the count of shapes whose adjudication needed a second reading |
| E8″ | Are the shapes' records seen? | the swallow and escape probes through `check.mjs` | every marker's record present per shape; a missing one → STOP |
| E2″ | Is every catch site instrumented? | a census over the lens's `src`: `catch` clauses + `.catch`/`.then(_, fn)` call sites found by the transform's own AST walk vs. those it spliced | ratio 1.000 after NAMED exclusions; one unnamed miss → STOP |
| E3-TS″ | Does the comparator still not cry wolf? | `src/__tests__/useMeshVoice.test.tsx` recorded 20 times, `diff` against the first (fingerprints moved) | DIVERGED 0/19, REFUSED 0/19; any → STOP |
| E5″ | Do both harnesses run? | the full suite under the driver; the probes under `node --test` | 372/4278 green; `node --test` green with its rows; a red vitest is NO-GO |
| E7″ | Does the reader speak this recorder's words? | the `exceptions` transcript on a lens trace and on the invocation, grepped | 0 occurrences of `oid`, `chain`, `Err`, `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`; plus v30–v33 green |
| E1‴ | What does the product cost now? | walls n=5 per arm, interleaved plain/off/call, guarded, conversion excluded | reported beside rung 1's off/plain 1.0587 and call/plain 1.1324; no gate |
| E10″ | What does conversion cost now? | `e10p.sh` over the fresh run's spool set at jobs 16, n=5, and over one file | reported beside slice 2's 16.3859 s and 0.1648 s; no gate |

**The adjudication protocol for E6-TS′**, transferred from Rust's
HONESTY-ERR-FLOW §11 and R15 and fixed here before any line is read: a
SWALLOWED line is **true** when the catch (or callback, or `finally`)
discarded the failure and the caller went on as if the call had succeeded —
an empty clause, a clause that only logs, a `finally` that returned; it is
**false** when the failure or a rendering of it reached the caller by any
route the rule did not see — returned, stored, asserted on, rendered into a
value, re-thrown as another object, or read by a handler the rule called
opaque and that in fact propagated. Every line is read against the source
at the site the verdict names; the count of lines and the adjudication of
each are in the record, and a line the adjudicator cannot decide from the
source counts as false.

**Stop rules** as slice 2's: a run whose suite is not 372/4278 is dropped
and named; no endpoint is re-run after its number is read; an
infrastructure kill re-runs from zero with the reason recorded.

## 8. Testing story

- **Transform goldens** (`typescript/test/golden/`): one per `how` word and
  per escape-rule branch, each asserting `lines(out) == lines(in)`; a golden
  for `.then(_, fn)`, for the `function`-spelled empty callback, for a
  destructuring catch, for a `finally` with and without a completion.
- **Runtime** (`typescript/test/rt.test.mjs`): `catchCb` calls the original
  with `this` and the reason and returns its result; `handledFinally`
  records only with a mark set; the capability in BOOT.
- **The rules on synthetic traces** (`tests/test_exceptions_typescript.py`,
  the `tests.helpers.finalize_synthetic` pattern the Python and Rust rules
  use): one test per classifier rule and per ambiguous reason, the
  absorbing/escaping-set conjunction (a swallowing HANDLED plus an escaped
  one → ambiguous), the orphan HANDLED, the primitive, the task-root
  propagation, the unhandled rejection, the incomplete trace; the tally
  order; paging; the capability gate on a 0.1.x-shaped trace.
- **The invocation mode** (`tests/test_exceptions_invocation.py` gains a
  TypeScript half): dispatch by member language, the TypeScript shape key,
  the flags for members differing off-key.
- **Mutation checks** on the escape analysis (drop the logging family →
  `logged_catch` flips), on rule 3's conjunction, on the shape key; Python
  mutants under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged.
- **Unchanged and re-run:** the whole Python suite, `npm --prefix typescript
  test`, `run check`, the corpus (`--only-dir typescript --require-driver`,
  `--only-dir .`), the live suite; the Python and Rust `exceptions` outputs
  byte-identical (their tests are the fence).

## 9. Order of work

Subagent-driven in a worktree under `/mnt/extra/sensorium-rung2/`; a plan
carries §3.3, §4.2, §6.1's table and §7 **verbatim**.

0. Pre-registration byte-locked (§7 + the adjudication protocol + pins); the
   E2″ census instrument; the TRACE-FORMAT split (§5.2).
1. Transform: §2.1–§2.3 with goldens; `escape.probe.test.ts`.
2. Runtime: `catchCb`, `handledFinally`, the capability; the swallow probe's
   new shapes; `check.mjs`.
3. Converter pass-through; vectors v30–v33; the corpus questions re-pinned
   for moved event ids.
4. The rules module on synthetic traces.
5. The invocation dispatch and the TypeScript shape key.
6. The corpus (§6.1).
7. Acceptance: E8″, E2″, E3-TS″, E5″, E7″, E6-TS, then E6-TS′ with its
   adjudication, E1‴ and E10″.
8. HONESTY, READMEs, `docs/query.md`, CHANGELOG, the ledger, versions.
9. Final review, one fix wave, PR.

## 10. Versions and ceilings

- `sensorium-ts` **0.2.0** (wire 1; the recorder's declaration changes);
  Python **0.10.0**; `TRACE_FORMAT` stays **4** (every addition optional).
- Ceilings: `docs/TRACE-FORMAT.md` split before any edit (§5.2);
  `exceptions_cmd.py` (757) gains its dispatch lines only; `README.md`
  (782) takes at most one sentence; `docs/CARRIED-DEBT.md` (722) is measured
  before its section — a cut of its oldest section to volume 6 is expected;
  `typescript/HONESTY.md` (757) may need a split of §10's blind spots into
  `typescript/HONESTY-BLIND-SPOTS.md` (Rust's precedent), decided by the
  measured count at task 8.

## 11. Decisions, with what each costs if wrong

| # | Decision | Cost if wrong |
|---|---|---|
| R1 | Unhandled rejections stay in meta; the rule reads them by serial, no event minted | an orphan rejection prints no site, and says so |
| R2 | The catch-binding escape rule is decided at transform time and written as `how` (Rust R2 amended, transferred) | a misclassified clause errs toward AMBIGUOUS; E6-TS′ measures the rate |
| R3 | The logging family is `console.{log,error,warn,info,debug,trace}` only | a project using a logger library reads its log-and-continue as AMBIGUOUS — the safe direction, declared |
| R4 | `.catch(<arg>)` / `.then(_, <arg>)` wrap any argument; non-inline arguments are `catch_callback_opaque` | a named handler that swallows is never accused; its rethrow still reads as a hop |
| R5 | `finally` with a completion statement is a sink recorded only under an in-flight mark | a `finally` that returns on the normal path writes nothing; a mark left by a HANDLED-then-`finally` sequence is cleared by the HANDLED |
| R6 | `uncaught` is reserved for an unhandled rejection; a failing test is `propagated (to the harness)` | a reader used to Python's word for a crash reads the detail |
| R7 | Python's five words and Python's rule shape, not Rust's | a TypeScript reader gets `re-raised` where Rust says `propagated`; the words are the command's original ones |
| R8 | Ambiguous by default; a swallowing HANDLED coexisting with an escaping one for the same serial is ambiguous | fewer SWALLOWED lines; none false by this route |
| R9 | The invocation mode dispatches per member language; the shape key is supplied by the language module | a Rust shape and a TypeScript shape never merge (different `lang`) |
| R10 | The per-trace TypeScript output groups by shape from the start | a reader of one trace sees `[×N]` brackets, as Rust readers do |
| R11 | Primitives are never merged on text | a rethrown string is always ambiguous |
| R12 | The E6-TS′ adjudication is Claude's under the delegation, with the protocol fixed in §7 before any line is read | a wrong adjudication is a wrong gate; the per-line record lets Brice re-read it |
| R13 | TRACE-FORMAT's TypeScript throw-flow section moves to TYPESCRIPT-KEYS.md before it is amended | one more pointer in the contract |
| R14 | The old refusal becomes a vector on a synthetic trace; `exceptions_refused` becomes `silent_swallow` | the corpus no longer records a refusal no recorder can produce |

## 12. Rulings from Brice

Scope, merges and money only.

1. **Ruled 2026-09-10:** full transfer (§0); approach 1 (§0).
2. **Owed:** merge of this design PR, then of the rung.
3. **Owed:** disk for one fresh full-suite recording under
   `/mnt/extra/sensorium-s5/store-rung2ts` (≈ 1 GB) and the E1‴ arms (their
   spools are deleted after each wall is read, as rung 1 did).

*The plan's Task 8 calls this section the home of the execution deltas. In this
document's layout §12 is Brice's rulings and §13 is the pre-registration
pointer, so the deltas are **§14** below — "What changed against this design,
and why", slice 2's own §12 by another number. (Added 2026-09-10.)*

## 13. The pre-registration, in one table

§7's table and its adjudication protocol are carried verbatim into the
record's §1 at T0 and byte-locked there; this section is the pointer, so
the plan and the record cite one source.

## 14. What changed against this design, and why (rung 2, 2026-09-10)

*Added 2026-09-10, at the rung's close — the "execution deltas" §12 promises
and the plan's Task 8 asks for. Nothing above is deleted; where a sentence of
this document was narrowed, replaced or falsified, this section is the index
to it. **§7 is byte-locked** and carried verbatim into the record's §1 — no row
below touches it, and none could: every number in it was fixed before any of
this code existed (`tests/test_acceptance_s5_rung2_lock.py`). Two amendments
already stand where they belong rather than here: **§2.1**'s bare-rethrow
paragraph and **§6.1**'s four-row note under its table, both dated at Task 6.*

**P-rows** are the fourteen decisions the plan made before any code existed
(its *"Decisions this plan makes"* table,
`../plans/2026-09-10-sensorium-s5-rung2-throw-flow.md`), each of which that
table promised would amend this spec non-silently; this is where that is paid.
**R-rows** are controller rulings made while shipping, in the order they were
made (the SDD ledger's `Ruling:` lines) — with one exception, **R15**, which
is the whole-branch final review's own amendment and is dated as such both
here and in §3.3.

| # | What this document said, or left open | What rung 2 shipped, and why |
|---|---|---|
| P1 | §2.3: a `finally` sink learns a throw is in flight because `raise` and `thr` set a mark | A catch-**less** `try` whose `finally` completes gains a synthetic marking clause `catch(__sfe){__srt.mark(__sf,__sfe);throw __sfe}`; `raise(f, e)` and that clause set `f.mark`, `handled` clears it, and **`thr` sets nothing** — a `Frame` holds no parent reference and an awaited rejection lands in another microtask, so an unwinding callee cannot find its awaiter, while the synthetic clause sees a library throw and an awaited rejection alike and carries the real serial. A `try` with its own `catch` is therefore never marked: blind spot 18. |
| P2 | Where the escape rule lives was open | `typescript/src/escape.mjs`, exporting `catchHow`, `callbackHow` and `finallyCompletes` as pure functions over AST nodes, unit-tested directly — `transform.mjs` was at 708 of 800 lines and the rule is the largest new thing this rung writes. |
| P3 | `emptyCatch` records the empty-callback sink | **Replaced** by `catchCb(f, line, how, fn)`, emitted for every rejection handler; `emptyCatch` is deleted, because a 0.1.x transform output never reaches a 0.2.0 runtime (the driver pins the package) and one wrapper with one signature is the whole of §2.2. |
| P4 | §2.2 wraps `p.then(<x>, <arg>)` | Only a **two-argument** `.then` wraps its second argument; `.then(fn)`, `.catch()` with no argument and `.finally(fn)` are untouched, as §2.2 says. |
| P5 | §4.2 generalises `exceptions_group` over a `site(disposition)` callable | `group_units(trace, units, idx, classify, render)` with a module-level `Renderer` dataclass `{at, hops_line, site, site_text, site_file, tag_order}` supplied per language; `group_chains` stays as a thin wrapper passing the Rust renderer, which is what keeps every Rust caller and every Rust test byte-unchanged. |
| P6 | §3.2's "unit" the grouper sees was left to the module | A `Raise` object `{origin, handled, last_raise}` per RAISE serial, and one per orphan HANDLED serial, built by the index; `origin` is what `_at` and the bracket ids print, because the grouper reads `.origin` already. |
| P7 | §2.4 and R14: the old language refusal retires | `TYPESCRIPT.exceptions_refusal` becomes `None` — dispatched before `_language_refusal`, as `RUST` is — and v23's sentence about `exceptions` refusing at exit 3 is re-pinned to the **capability** sentence on a 0.1.x-shaped trace (the new v32). The old sentence named a rung that has now shipped. |
| P8 | §7's record was unnamed | `../acceptance/2026-09-10-sensorium-s5-rung2.md`, with `.results.json`, `-e6tsp-adjudication.md` and `-e7-exceptions.txt` beside it; lock test `tests/test_acceptance_s5_rung2_lock.py` on the slice-2 pattern; assembler `typescript/acceptance/assemble_rung2.py`. |
| P9 | §7's adjudication protocol fixes the reading, not the record | One row per SWALLOWED shape — `shape id · site · how · the source lines quoted · TRUE/FALSE · reason under §7` — written to `-e6tsp-adjudication.md` with its counts copied into the record's §3, because the per-line record is what lets the gate be re-read by somebody else. |
| P10 | §7's E2″ needed an instrument | `typescript/acceptance/census_catch.mjs <root>`, on rung 1's `census.mjs` shape: it walks the lens with the consumer's own TypeScript, counts what a walker sees, and takes its numerator from the transform's own output. |
| P11 | R14: the corpus's refusal case is renamed | `corpus/typescript/exceptions_refused/` → `silent_swallow/` by `git mv`, same `config.ts`, new questions; the refusal it recorded becomes vector v32, since no recorder produces it any more. |
| P12 | Where the BOOT-capabilities ingest test goes was open | `tests/test_ts_ingest_caps.py` — `tests/test_ts_ingest_meta.py` was at 777 of 800 lines. |
| P13 | §9's order of work | The runtime's `catchCb`/`mark`/`handledFinally` land **before** the transform, so no Node test ever executes a transformed call the runtime lacks; the probes are written with the runtime and go green with the transform. |
| P14 | §10: `sensorium-ts` 0.2.0 and Python 0.10.0 | `sensorium-ts` becomes **0.2.0 at Task 1**, with the runtime whose declaration changed, because Task 6's corpus questions pin the recorder string `info` prints — which is the BOOT's `VERSION`, written before Task 8. Python's **0.10.0** waits for Task 8, with the CHANGELOG entry the release-token gate binds to it. |
| R1 | §2.3's literal reading of a completing `finally` | `finallyCompletes` counts a `return` at closure depth 0, and a `break`/`continue` only when no loop or switch **inside** the `finally` encloses it — a break that stays inside the finally discards nothing — and the census imports the predicate from `escape.mjs` so E2″'s two halves share one rule. |
| R2 | §2.3 stores "the serial of the exception now travelling" | The mark stores the whole `exc(e, 'throw')` object rather than the serial, so `raise` and the synthetic clause both hold the value and `handledFinally` writes a complete `exc` — the contract requires `type` on every `exc`. |
| R3 | §6.2's probes and the checker's new checks were Task 1's | They move wholly to Task 2: new checker checks would have turned `tests/test_ts_live.py`'s checker test red between the two tasks, so Task 1 ships runtime, tests and the version bump only. |
| R4 | §7 left E2″'s numerator to the instrument | It comes from the transform's **own output**: `census_catch.mjs` runs `transformSource` over each eligible file and counts `__srt.handled(` / `__srt.catchCb(` / `__srt.handledFinally(` in the result by `how` word. No manifest key is added; the goldens hold the text's shape. |
| R5 | §2.2 wraps `.catch(<arg>)` "the way `spliceEmptyCatchCallback` does" | The wrap happens on **any receiver**, because the transform cannot type the expression. A non-promise API whose `.catch` calls its callback writes an orphan HANDLED and could reach *SWALLOWED, born outside a throw statement* — a declared blind spot and an explicit E6-TS′ watch item, where such a line counts FALSE. |
| R6 | §2.1's `String(e)` reading | A mention inside an intermediate call within a `console` argument — `console.log(sanitize(e))` — reads `catch` (logged), the same reading applied consistently; a helper that stores `e` and returns text is therefore read as a swallow, and is declared. |
| R7 | §6.1: `exceptions_refused` is renamed at Task 6 | Task **4** rewrites that case's `exceptions` question to the verdict it now gets, because the corpus re-records with the 0.2.0 recorder and would go red between Tasks 4 and 6; Task 6 does the rename. |
| R8 | §2.1 listed only `throw new Wrapped(e)` as an escape | **A bare rethrow — `throw e;` whose operand after any parentheses is the binding itself — is a traced EXIT and not a mention**, so it does not count towards `catch_escaped` and the clause's word is decided by its other mentions. §3.3 rule 2, §6.1's `rethrow_hop` row and R4 all assumed this, while `escape.mjs` counted every `throw` operand: under that reading rule 3's escaping conjunct barred **every** `throw e` hop from SWALLOWED and §7's locked `rethrow_hop` count was unreachable by construction. An instrument defect fixed **before any endpoint was measured**; §2.1 carries the dated amendment. |
| R9 | §6.1: `translated`'s wrapper raise | It reads **AMBIGUOUS**, not PROPAGATED: the wrapper is thrown from a traced arrow that vitest's untraced `toThrow` called from **inside** a traced test frame, and the rules cannot see an untraced catcher between two traced frames. AMBIGUOUS is the honest word and §7's pre-registered SWALLOWED count (0) is unaffected. |
| R10 | §2.2 defines a callback's word as §2.1's rule applied to its parameter | So `callbackHow` carries the **same** bare-rethrow exclusion: `.catch((e) => { throw e })` reads `catch_callback`, while `.catch((e) => { seen.push(e); throw e })` stays `catch_callback_escaped`. Two readings of one rule would make the lens adjudication depend on which syntax a swallow used. |
| R11 | §6.1's `rethrow_hop` shape column says "an outer empty catch" | The outer sink is a **returning** `catch { return 'defaults' }`, whose word is `catch`: §7's table counts SWALLOWED verdicts, both words are in the absorbing set, and a returning clause is the realistic seeded-bug shape. §6.1's shape column is descriptive. |
| R12 | §6.1's verdict column for four cases | Those four rows get **one dated amendment note under the table**, not row rewrites — §6.1 is descriptive and outside the §7 lock, and the counts are unmoved: `silent_swallow` prints `caught by catch`, `translated`'s origin prints the escaped reason, `await_rejection_caught` prints no hops line, and `test_failed` is a `throw` statement because a failing `expect` throws inside vitest's untraced code and writes no RAISE row at all. |
| R13 | §7's only named shipping branch is DONE-WITH-STOP | The rung's word is **DONE**. Every word in the record comes from a rule; §7 names no PASS anywhere, and rung 1 shipped DONE-WITH-STOP under the same convention, so the branch not taken reads DONE. |
| R14 | §7 left the results file's provenance to the assembler | The assembler writes `recorder_basis` on every cell, `own` on the two that record themselves (E6-TS′, E8″), and the record's provenance sentence stays: a re-assembly of saved cells is not a re-measurement, and a JSON that names its basis per cell is what slice 2's misattribution lesson asked for. |
| R15 | §3.3 rule 4's one conjunct, "no HANDLED in the absorbing set" | Two narrowings, written into §3.3 rule 4 in place and dated: the rule also declines on an **escaping** HANDLED anywhere for the serial (rule 5 owns that reason, and rule 4 runs first), and its absorbing conjunct is read as "no absorbing HANDLED whose frame has **not yet returned**" (`_still_open_absorber`, the Task-4 review fix `7c2ead1`, which is what keeps rule 3's 3/4 mutation live). Both narrow the verdict, never widen it — no shape gains PROPAGATED that the sentence denied it — and E6-TS′'s 30 shapes were adjudicated under the coded reading. What it costs is in `docs/CARRIED-DEBT.md`: an escaped handler that then rethrows out of the test root reads AMBIGUOUS where PROPAGATED would be truer. |

**What the endpoints read, against what this document expected.** §7's table
held: **E6-TS 17 of 17**, **E6-TS′ 0 false SWALLOWED of 30**, **E8″ 32 of 32**,
**E2″ 287 of 287 (ratio 1.0000)**, **E3-TS″ 0/19**, **E5″ 2 of 2**, **E7″ 0 of
nine needles**; ungated, **E1‴ 1.0608 / 1.1266** and **E10″ 16.0715 s /
0.1642 s**. Not one endpoint fired its rule's failure word. This document made
no per-cell predictions of the kind slice 2's §3.3 did, so there is no
prediction table here; what it did assume and got wrong is R8 above — a rule
whose literal reading made one of §7's own locked counts unreachable — and the
four instrument corrections the record's §2.3 dates, each made before the
endpoint it touches had been measured.

**Four findings this design did not anticipate** are the record's §5 gaps
1–4 — the shape key's Rust-shaped id mask splitting one place into three on a
TypeScript trace, three reused instruments measuring the global binary, E7″'s
needle list being unapplicable as written, and rule 5's catch-all being the
modal ambiguous reason on real code with an unnamed shape behind it. All four
are carried in `docs/CARRIED-DEBT.md`'s rung-2 section with what closing each
would take, and the fourth is `typescript/HONESTY-BLIND-SPOTS.md` item 27.

*(2026-09-11: S5 rung 3 closed Gaps 1 and 4 and the Gap-4 neighbour — the
shape key now holds the verdict's own words under a mask that exempts
nothing, and rule 5's catch-all names an untraced catcher before falling
back to `unnamed`. See
`../acceptance/2026-09-10-sensorium-s5-rung3.md` §3 and §5.)*
