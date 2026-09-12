# The TypeScript recorder's honesty ledger — §10: Blind spots

The numbered list of [`typescript/HONESTY.md`](HONESTY.md) §10, **moved here
2026-09-10 (S5 rung 2) so that file stays under 800 lines**, on the precedent
[`../rust/HONESTY-BLIND-SPOTS.md`](../rust/HONESTY-BLIND-SPOTS.md) set
2026-09-05. The section's own framing paragraph stays there; **the numbering is
unchanged**, so item *n* here is `typescript/HONESTY.md` §10 item *n* — the
spelling every earlier document, `docs/CARRIED-DEBT.md` and the ledger's own
index already use.

Items **1–9** are rung 1's, from the design's §7; **10–17** were added
2026-09-09 at rung 1's close, from what its acceptance measured. Items
**18–27** are S5 rung 2's, from the throw flow: the shapes the escape rule,
the callback wrapper and the `finally` sink cannot see, plus the one the
disposition rules decline to judge. Items **28–38** are **S5 rung 4's**,
added 2026-09-12 with the focus tier: seven shapes the per-statement record
does not reach, three gaps the tier's readers declare rather than paper over,
and **38**, added at the rung's final review, where the runtime's own frame
lifetime silently drops a row the transform did mint.

**One item rung 4 planned is not here, because it closed before it could be
numbered.** The design's §6.4 named seven items 28–34 and *a falsy `if`
head's assignment* was one of them: `if ((x = f()))` whose test is falsy
wrote `x` and, under §3.2's per-entry rule alone, would have reported it
nowhere. Plan **P1** closed it — a guarded statement's own completion row
carries its head's assignment targets whichever branch ran — and the same
rule is what puts `m = null` on a `while`'s row after the loop. So the list
below has seven rung-4 shapes and the seventh is `enum`/`namespace`/`static
{}` names, not the falsy head; the falsy head is a promise §11 makes and
`E12` H3 measured (row 9 of nine, `m=null`), not a hole.

**Three items are struck and one is narrowed, none deleted.** Rung 2's runtime
records the shapes items **2**, **3** and **11** said it did not, so each is
struck where it stands with the date and the replacement named; item **13** is
narrowed to what is still true of a destructuring clause. A struck item stays
visible because a reader who last met this list under `sensorium-ts 0.1.x`
needs to see which of its holes closed, when, and what is left of them. Item
**22** is neither struck nor narrowed but **rewritten in place**, at this
rung's own final review: what it claimed was never true of the shipped
runtime, and its note says what it used to say.

**Item 27 is narrowed 2026-09-11, S5 rung 3.** The shape it named — an
untraced catcher between two traced frames — is no longer invisible: the
reader now prints a reason, `untraced catcher`, naming which of three
variants it saw. What the item still says is narrower than before but not
struck: naming the footprint is not the same as reading what the untraced
code did with the failure, and that half stays exactly as unread as it
always was.

Each entry names what the trace carries in its place, and what could falsify
the claim that this is the whole of it. A bare `§n` below is a section of
`typescript/HONESTY.md`.

1. **Same-line anonymous twins share a fingerprint key.** Two anonymous
   functions on one line intern to one site, because interning is per site and
   `<anonymous>` carries no ordinal (§7). The trace says exactly what it knows —
   `<anonymous>` at that line — and claims nothing about which of the two ran.
   *Falsifier:* `typescript/test/transform.test.mjs`, `E2′`.
2. ~~**A `.catch(fn)` with a non-empty body is not seen.** Only the empty-callback
   sink records a HANDLED; the `how` enumeration of §4 is the list of shapes
   that produce a record, and this is not on it.~~ — **Closed 2026-09-10, S5
   rung 2** (`sensorium-ts 0.2.0`, §4): every `.catch(<arg>)` and every
   two-argument `.then(<x>, <arg>)` is wrapped and records a HANDLED, whose
   word is `catch_callback`, `catch_callback_escaped`,
   `catch_callback_opaque` or `sink_empty_catch_callback`. **E2″** measured
   **108 of 108** `.catch` sites and **2 of 2** `.then` sites spliced on the
   acceptance lens. What survives of this item is narrower and has entries of
   its own: 23 (an opaque handler is never accused) and 24 (the receiver is
   not typed). *Falsifier:*
   `typescript/probes/src/swallow.probe.test.ts`, `E8″`, `E2″`.
3. ~~**`finally` records nothing.** Not a RAISE, not a HANDLED, not a hop. Rung 2
   decides whether it should; until then `capabilities.err_flow: false` says no
   disposition may be read from these rows at all.~~ — **Closed 2026-09-10, S5
   rung 2** (§4): a `finally` block that `return`s, `break`s or `continue`s at
   closure depth 0 discards an in-flight throw and records HANDLED
   `sink_finally_return`. A `finally` with no completion statement still
   records nothing, because it discards nothing. What the sink cannot see is
   items 18 (the frames it never marks) and 22 (the value it never holds).
   *Falsifier:* `typescript/test/transform.test.mjs`,
   `corpus/typescript/finally_return`, `E8″`.
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
11. ~~**A `.catch(function () {})` is not a sink; only the arrow spelling is.**
    §4's empty-callback sink matches an arrow function with an empty block
    body. The same empty body written as a `function` expression records
    nothing at all — not a HANDLED, not a count. Which shapes are sinks is
    rung 2's question, and this is one of the shapes it inherits.~~
    *(Added 2026-09-09; **closed 2026-09-10, S5 rung 2** — rung 2 answered
    the question it inherited: an inline arrow **or** `function` expression
    with an empty body reads `sink_empty_catch_callback`, one rule for two
    spellings.)* *Falsifier:*
    `typescript/probes/src/swallow.probe.test.ts`, `E8″`,
    `typescript/test/escape.test.mjs`.
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
    line and its `how`. *(Added 2026-09-09. **Narrowed 2026-09-10, S5 rung 2:**
    that `how` is now `catch_escaped` — §2.1's rule reads a destructuring
    pattern as an escape, because the transform cannot see what it bound — so
    the clause is in the ESCAPING set and its verdict is AMBIGUOUS, never
    SWALLOWED. The direction is under-claiming: a destructuring clause that
    really does swallow is not accused.)* *Falsifier:*
    `typescript/test/rt.test.mjs`, `typescript/test/transform.test.mjs`,
    `typescript/test/escape.test.mjs`.
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

18. **A `try` that has its own `catch` clause is never marked, so its
    `finally` sink can miss a throw.** §4's mark is set by `raise(f, e)` —
    which only traced code's own `throw` statements reach — and by the
    synthetic marking clause spliced into a **catch-less** `try` whose
    `finally` completes. A `try` that already has a `catch` gets no synthetic
    clause, so a rejection **awaited inside that catch body** (which lands in
    another microtask, where no frame can find its awaiter) followed by a
    completing `finally` records **nothing at all**. `thr` — a callee's frame
    closing by throw — sets no mark either. A synchronous throw inside that
    catch body IS a `raise` and does mark. Declared before the runtime was
    built (plan P1) and never measured away. *(Added 2026-09-10.)*
    *Falsifier:* `typescript/test/rt.test.mjs` (`mark` / `handledFinally`),
    `typescript/probes/src/swallow.probe.test.ts`,
    `corpus/typescript/finally_return`.
19. **The logging family is `console.*` and nothing else.** A project that
    logs through `pino`, `debug`, or its own `logger.error(e)` has its
    log-and-continue read as `catch_escaped`, so the verdict is AMBIGUOUS
    where the shape is in fact the archetypal swallow. That is the safe
    direction — a swallow is under-claimed, never invented — and it is a
    declared limit, not a measured absence: nothing counts how often it
    happens. *(Added 2026-09-10, design R3.)* *Falsifier:*
    `typescript/test/escape.test.mjs`, `E6-TS′`.
20. **A mention inside an intermediate call within a `console` argument still
    reads `catch`.** `console.log(sanitize(e))` is a logged mention, the
    spec's `String(e)` reading applied consistently — so a helper that
    **stores** `e` and returns text is read as a swallow when the value did
    reach something. Ruled at Task 2 and declared then; the lens adjudication
    watched for it and found no such shape among the 30. *(Added 2026-09-10.)*
    *Falsifier:* `typescript/test/escape.test.mjs`, `E6-TS′`.
21. **A closure that captures the binding is an escape wherever it goes, and
    even if it never runs.** `catch (e) { queueMicrotask(() => report(e)) }`
    reads `catch_escaped` and its verdict is AMBIGUOUS. The rule is syntactic
    and does not follow the value; a closure that is built and dropped is
    indistinguishable here from one that ships the error somewhere. Again the
    under-claiming direction. *(Added 2026-09-10.)* *Falsifier:*
    `typescript/test/escape.test.mjs`, `typescript/test/golden/`.
22. **The `finally` sink sees only what the mark holds.** `sink_finally_return`
    names the sink, the line and the serial, and its `exc` is the marked
    throw's **own, complete** one — `kind`, `type`, `msg` and `serial`, nothing
    `unread` — so what the sink cannot know is not the *value* but the *throw*:
    a throw nothing marked reaches a completing `finally` invisibly. Those are
    P1's own two shapes and they are argued at item **18** — a `try` with its
    own `catch` clause gains no synthetic marking clause, and `thr` (a callee's
    frame closing by throw) sets no mark. *(Added 2026-09-10. **Corrected
    2026-09-10, at the rung's final review:** this item first said the sink
    "records no value" and wrote `unread: ["type","msg"]`, which was the
    design's pre-R2 wording and never the shipped runtime's — ruling R2 made
    the mark hold the whole `exc(e, 'throw')` object. Rewritten in place,
    keeping its number, per this file's own rule.)* *Falsifier:*
    `typescript/test/rt.throw.test.mjs` (`a marked frame whose finally
    completes`), `docs/trace-format/TYPESCRIPT-KEYS.md`,
    `corpus/typescript/finally_return`.
23. **An opaque rejection handler is never accused.** `.catch(handler)` — an
    identifier, a member reference, a call returning a function — reads
    `catch_callback_opaque`, which is in the ESCAPING set, so its verdict is
    AMBIGUOUS however plainly the handler swallows. If `handler` is itself
    instrumented it has its own frame, and a rethrow from it carries the
    serial and reads as a hop; a plain return from it is **not** evidence of a
    swallow, because its parameter's fate was never analysed. *(Added
    2026-09-10, design R4.)* *Falsifier:*
    `corpus/typescript/callback_opaque`, `typescript/test/escape.test.mjs`.
24. **`.catch` and `.then` are wrapped on ANY receiver, because the transform
    cannot type one.** A non-promise API with a `.catch(fn)` method has its
    callback wrapped too; if that callback runs, an orphan HANDLED with no
    RAISE is written, and such a record can read *SWALLOWED, born outside a
    throw statement*. Declared at Task 2 and made an explicit watch item of
    the E6-TS′ adjudication, where a SWALLOWED at a `.catch` whose receiver is
    not a promise counts as FALSE: the lens sweep found **none** among its 30
    shapes. Evidence about one suite, not a proof about the shape. *(Added
    2026-09-10.)* *Falsifier:* `E6-TS′`, `typescript/test/golden/`.
25. **A `Promise.reject(v)` raises nothing, and neither does a dependency.**
    `Promise.reject(v)` is not a `throw` statement, so its handler's HANDLED
    has no RAISE and reads *born outside a throw statement*; a throw inside
    untraced code — `JSON.parse`, any dependency — reads *born outside traced
    code*. An unhandled rejection is `meta.unhandled_rejections`, never an
    event, because a causal event with no `code_id` would put a site in the
    program that has none. The verdicts say which of the two it is rather
    than inventing an origin. *(Added 2026-09-10.)* *Falsifier:*
    `corpus/typescript/callback_sink`, `corpus/typescript/dependency_throw`,
    `corpus/typescript/unhandled_rejection_in_info`,
    `docs/trace-format/vectors/v27-unhandled-rejection-in-meta.json`.
26. **An assertion failure born in `expect` writes no RAISE row at all.**
    vitest's `expect` throws inside vitest's own untraced code, so
    `exceptions` never sees it: the `propagated (to the harness)` verdict is
    reachable only from a `throw` in traced code. The failure is not lost —
    `info`'s exit line and the task's own outcome carry it — but the command
    a reader would reach for first cannot answer about it. This is why
    `corpus/typescript/test_failed` is a `throw` statement and not a failing
    `expect` (spec §6.1's dated amendment). *(Added 2026-09-10.)*
    *Falsifier:* `corpus/typescript/test_failed`,
    `corpus/typescript/pass_vs_fail`.
27. **An untraced catcher sitting INSIDE a traced frame is invisible, and
    everything it catches reads AMBIGUOUS.** A React error boundary, a vitest
    `toThrow`, a `try` in a dependency between two traced frames: the raise's
    frame unwinds, its **parent** frame returns, and no HANDLED for that
    serial exists anywhere. Rule 1 declines (not an unhandled rejection),
    rule 2 declines (no later raise), rule 3 declines (no absorbing handler),
    and rule 4 declines because the last unwind closes neither a task root nor
    a frame whose parent is untraced — so rule 5's catch-all is the verdict.
    Measured on the lens: **17 of the 30 AMBIGUOUS shapes** read that reason,
    which makes this the modal ambiguous shape on real code (record §5,
    gap 4). The rules declining rather than guessing is exactly what keeps the
    false-SWALLOWED count at **0**; naming the shape is what a later rung
    needs before it can decide whether it is judgeable at all. *(Added
    2026-09-10. **Narrowed 2026-09-11, S5 rung 3:** the reader now NAMES
    this footprint under a new reason, `untraced catcher`, in three
    variants — the parent returned, the parent later unwound with its own
    error (a translation or a later failure, indistinguishable), or the
    parent never closed — still AMBIGUOUS. What is narrowed is the shape's
    invisibility, not its depth: the rule says WHICH shape this is and
    still claims nothing about what the untraced code did with the
    failure, which stays exactly as unread as it always was. Measured
    **0 false names of 20** printed blocks against the seventeen-row hand
    read, all seventeen predicted before this code existed.)* *Falsifier:*
    `E6-TS′`, `E6-TS‴`, `corpus/typescript/{translated,untraced_catcher,
    untraced_catcher_rejection,untraced_catcher_later_failure}`.

28. **A place write is a row with no delta.** `a.b = e`, `a[i] = e`,
    `a.b++` and `delete a.b` write through an object the statement did not
    bind, and `writesOf` reports identifier targets only — so the LINE row
    exists, at the right line, with empty `deltas`. The row is the honest
    artifact: the statement ran and this recorder cannot say what it
    changed. Reading it would mean a snapshot-and-diff of every reachable
    object at every statement, which is a different instrument at a
    different price (design D3). `flow --value` therefore sights nothing for
    a value that only ever lived in a property. *(Added 2026-09-12.)*
    *Falsifier:* `corpus/typescript/focus_place_write` (the present row and
    the absent value, pinned from both sides),
    `typescript/probes/src/focus.probe.test.ts` (`placeWrite`),
    `typescript/test/bindings.test.mjs`.
29. **`this` is not read, under a focus or otherwise.** A method's rows
    carry what it wrote to its own bindings and nothing about the receiver:
    `this` is not a parameter, so it is not in a CALL's `args`, and it is
    not an identifier target, so it is not in any row's `deltas`. A method
    whose whole effect is on `this` records rows with empty deltas. Capturing
    it as a pseudo-argument is a later slice's decision if demand shows
    (design §14). *(Added 2026-09-12.)* *Falsifier:*
    `typescript/test/bindings.test.mjs`, `typescript/test/golden/`.
30. **A conditional assignment's row does not say whether the write
    happened.** `x ||= f()`, `x &&= f()` and `x ??= f()` may not assign at
    all, and `writesOf` names `x` regardless; the row reports the binding's
    value AFTER the statement either way. So a row showing `x` unchanged is
    two different facts wearing one shape — the operator short-circuited, or
    it assigned the same value. What is claimed is the value at the end of
    the statement, which is what every later site reads, and that much is
    exact. *(Added 2026-09-12.)* *Falsifier:*
    `typescript/test/bindings.test.mjs`, `typescript/test/golden/`.
31. **A `switch` discriminant's assignment is reported nowhere.**
    `switch ((k = key(o))) { … }` writes `k`, and a `switch` has no body to
    enter, so it mints no head row (design §3.2, §3.9) — `headBindingsOf`
    returns nothing for it and the statement's own completion row carries
    the discriminant's targets only through plan P1's rule for guards, which
    a `switch` is not. The declared shape is rare and the alternative — a
    seventh guard form with a synthetic row per case clause — was not worth
    the grain. *(Added 2026-09-12.)* *Falsifier:*
    `typescript/test/bindings.test.mjs`.
32. **Object identities are top-level captures only.** `oid` is minted for
    the value a capture IS, not for the values inside its rendering: an
    array of three objects has one serial, and the three have none, so
    `flow --object` cannot follow an element out of the container it was
    printed in. Python's `_walk` over samples finds nested identities and
    this recorder does not, because `util.inspect` hands back TEXT and there
    is nothing behind it to walk. What the trace holds instead is the
    container's own serial and the rendering at each sighting — which is how
    a mutation shows (the same `#64` printed `[]` at one site and
    `[ { sides: 20, value: 17 } ]` at the next). *(Added 2026-09-12.)*
    *Falsifier:* `corpus/typescript/object_identity`, `E12` H6,
    `docs/trace-format/vectors/v37-flow-object-serial.json`.
33. **A nested function outside the focus prefix is call-level only.** A
    spec selects a qualname and everything under it on a `.` boundary, so
    `--focus outer` reaches `outer.inner` and `--focus inner` reaches
    nothing (the prefix runs one way). A callback defined inside a focused
    function but reached by no spec — a handler passed to a dependency, an
    arrow in a file the spec's file part excluded — records its CALL and its
    RETURN and no statements, and `writesOf` never attributes its writes to
    the enclosing statement either. The count of what a spec DID select is
    `meta.focus_matched` and `resolve.mjs` answers it before the run.
    *(Added 2026-09-12.)* *Falsifier:* `corpus/typescript/focus_container`,
    `typescript/test/focus.test.mjs`, `typescript/test/resolve.test.mjs`.
34. **`enum` and `namespace` binding names, and a class `static {}` block,
    are reported by neither `writesOf` nor `declaredIn`.** An
    `EnumDeclaration` and a `ModuleDeclaration` execute where they stand and
    each binds a name, so each keeps its row — but the row's `deltas` are
    **empty**, and the name is not listed `unbound` when its block ends
    either. A class `static {}` block is a member body that runs at
    definition time and is not walked at all, so what it writes to the
    class's own statics reaches no row. Each is a row that exists and
    under-reports rather than a row that is missing. *(Added 2026-09-12.)*
    *Falsifier:* `typescript/test/golden/` (`focus-type-only` pins the
    `enum`'s empty row), `typescript/test/bindings.test.mjs`.
35. **`undefined` and a BigInt are readable at `flow --value` and not
    writable.** `read_inspect` resolves the text `undefined` to the
    `UNDEFINED` sentinel and `123n` to a BigInt, so `watch --expr 'x ==
    undefined'` answers; `inspect_text` returns `None` for either target, so
    `flow --value undefined` and `flow --value 123n` sight nothing rather
    than sighting approximately. The asymmetry is deliberate — reading wider
    than writing is `rust_debug`'s rule too — but it means one of the two
    commands can answer about a value the other cannot search for.
    *(Added 2026-09-12.)* *Falsifier:* `tests/test_js_inspect.py`,
    `corpus/typescript/flow_value_inspect`.
36. **`info`'s `truncated values:` count does not include an
    inspect-dialect string cut.** A string past inspect's own 100-character
    cap is cut by the FORMATTER, long before the 200-byte wire cap looks at
    the rendering, so the capture's `trunc` flag is `false` and the counter
    that reads it does not see the cut. The evidence is in the text instead
    — the `… N more characters` tail outside the closing quote, which
    `read_inspect` reads as TRUNCATED and `inspect_text` refuses to spell —
    so `watch` reports such a site as *recorded truncated* while `info`'s
    total says none was. A reader trusting the count alone under-counts what
    was clipped. *(Added 2026-09-12.)* *Falsifier:*
    `corpus/typescript/flow_value_inspect` (the 150-character value),
    `tests/test_js_inspect.py`.
37. **A new TypeScript corpus case cannot ask an `exceptions` question.**
    `typescript/acceptance/e6ts.py` carries a locked `PRE_REGISTERED` table
    — the rung-2 verdicts, hand-adjudicated before that code existed — and
    the E6-TS fence reads every `exceptions` question in
    `corpus/typescript/` against it, so a case added later that asks one
    would be an unpredicted row in a closed pre-registration. Rung 4's
    `focus_catch_binding` pins its HANDLED with `grep` instead. This is a
    property of the fence, not of the recorder: the verdicts a new case
    would get are computed by the same rules as every other case's. **Closing
    it** means the next rung that touches E6-TS either re-registers the table
    or scopes the fence to the cases it was written over. *(Added
    2026-09-12.)* *Falsifier:* `corpus/typescript/focus_catch_binding`,
    `typescript/acceptance/e6ts.py`.
38. **A statement in a `finally` reached by the `try`'s `return` mints no
    row.** `spliceReturn` renders `return x` as `return __srt.ret(__sf,(x))`,
    and `ret` sets the frame's `open` to false before the program's own
    `finally` runs; `line` drops every row that arrives on a closed frame. So
    in `try { return x } finally { cleanup = true }` under a focus the trace
    carries the RETURN and **nothing at all** for the finally's statements —
    the row is not present-and-empty, it is absent, and no `info` line counts
    it. The gap is **asymmetric**: the same `finally` reached by a `throw` IS
    recorded in full, because `thr` has not run yet when it executes. The
    runtime change that would close it — seal the frame AFTER the finally,
    which also moves the RETURN row past those statements — is a next-slice
    design item in [`../docs/CARRIED-DEBT.md`](../docs/CARRIED-DEBT.md), so
    the falsifier named below pins the ABSENCE and a later fix must change it
    deliberately. *(Added 2026-09-12, R42.)* *Falsifier:*
    `typescript/test/rt.focus.test.mjs` (*a statement in a finally after the
    return mints no row*).
