# CARRIED-DEBT

Appended at every merge: *what this slice settled* → *deferred, with
rulings* → *process lessons*. Resolved items are struck through, never
deleted.

Started 2026-09-05, at rung 3's close. Earlier slices carried their debt in
the rung-3 inbox
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3) and in the
gitignored plan ledgers; nothing there is restated here, and that document
stays the record for rungs 0–2.

**The earlier sections moved 2026-09-06** — rung 3, the borrow repair and the
rung-4 entry slice are
[`docs/CARRIED-DEBT-ARCHIVE.md`](CARRIED-DEBT-ARCHIVE.md), wording, order and
strikes unchanged, so a deferred item there is still open unless it is struck.
The split was named in this file before it was taken (the focus tier's own
"files near the ceiling" bullet, below) rather than discovered at 800; ~~the
rule above governs both files, and the next slice appends here~~ — **corrected
2026-09-08**: **three** files, not two. The paragraph below superseded this
sentence when volume 2 was cut and left it standing, which is how a reader
arriving at this line alone would have counted the archive wrong; the rule at
the top governs every volume, and the next slice appends to *this* file.

**Rung 4's slices 1 and 2 moved 2026-09-08** — the focus tier and the refocus
slice are [`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md),
wording, order and strikes unchanged, so a deferred item there is still open
unless it is struck. Volume 1 was itself at 594 lines when this file next
needed room, so the archive is **numbered volumes, each under 800 lines**, and
~~the rule at the top now governs three files rather than the two named
above~~ — **corrected 2026-09-08**: **four** files, the paragraph below having
superseded this sentence when volume 3 was cut, exactly as this paragraph
superseded the one above it. A count of volumes stated in a paragraph goes
stale every time a volume is cut; the rule at the top governs every volume,
whatever their number.
This file keeps the newest sections, and the next slice's section is appended
here.

**Rung 4's slice 3 moved 2026-09-08** — the rung-4 debts slice is
[`docs/CARRIED-DEBT-ARCHIVE-3.md`](CARRIED-DEBT-ARCHIVE-3.md), wording, order
and strikes unchanged (the queue slice's own strikes inside it included), so a
deferred item there is still open unless it is struck. ~~The rule at the top now
governs **four** files.~~ — a count in a paragraph, which the paragraph below
made stale exactly as this file's header has twice recorded happening; the rule
at the top governs every volume, whatever their number. The move was measured
before it was made: this slice's section would have taken the live file to 790
lines, and the ledger's own rule is to cut the oldest section rather than
discover the ceiling.

**Rung 4's slice 4 moved 2026-09-09** — the recorder's-footprint slice is
[`docs/CARRIED-DEBT-ARCHIVE-4.md`](CARRIED-DEBT-ARCHIVE-4.md), wording, order
and strikes unchanged, so a deferred item there is still open unless it is
struck. Measured before it was made, the way the rule asks: the S5 rung-1
section below was drafted at **270** lines against a live file of **676**, and
the oldest section was cut rather than the ceiling discovered. This file keeps
the newest sections, and the next slice's section is appended here.

**The queue-buttoned-up slice moved 2026-09-10** — that section is
[`docs/CARRIED-DEBT-ARCHIVE-5.md`](CARRIED-DEBT-ARCHIVE-5.md), wording, order
and strikes unchanged, so a deferred item there is still open unless it is
struck. Measured before it was made, the way the rule asks: this commit's
four residual rows (ruling R46) were drafted at **34** lines against a live
file of **785**, which would have taken it to **819**, over the ceiling, so
the oldest section was cut rather than the ceiling discovered. This file
keeps the newest section, and the next slice's section is appended here.

**The S5 rung-1 section moved 2026-09-10** — the TypeScript recorder's slice is
[`docs/CARRIED-DEBT-ARCHIVE-6.md`](CARRIED-DEBT-ARCHIVE-6.md), wording, order
and strikes unchanged but for the two rows rung 2 closed, which are struck
where they stand and say so. Measured before it was made, the way the rule
asks: the rung-2 section below was drafted at **228** lines against a live file
of **774**, which would have taken it to **1,002**, so the oldest section was
cut rather than the ceiling discovered. This file keeps the newest sections,
and the next slice's section is appended here.

**The S5 slice-2 section moved 2026-09-11** — the E6″ exception and the E10′
converter ladder are
[`docs/CARRIED-DEBT-ARCHIVE-7.md`](CARRIED-DEBT-ARCHIVE-7.md), wording, order
and strikes unchanged, so a deferred item there is still open unless it is
struck. Measured before it was made, the way the rule asks: rung 3's final
review added four debt rows drafted at **40** lines against a live file of
**799**, which would have taken it to **839**, over the ceiling, so the oldest
section was cut rather than the ceiling discovered. This file keeps the newest
sections, and the next slice's section is appended here.

## 2026-09-10 — S5 rung 2, the throw flow (Python 0.10.0 / sensorium-ts 0.2.0)

The rung that makes rung 1's RAISE and HANDLED rows answerable: an escape rule
at transform time, nine `how` words, a rejection-callback wrapper, a `finally`
sink, and a TypeScript rules module `exceptions` dispatches to per member.
Fourteen plan decisions (P1–P14) and fourteen controller rulings, every one of
them in the spec's §14. **The rung ships DONE** — nine endpoints, each run
once, and no rule's failure word fired; the gate that decides the word,
`E6-TS′`, read **0 false SWALLOWED of 30** hand-adjudicated shapes on a
consumer's own suite. No row reads PASS and neither does the rung: six of the
nine rules name only a failure word and three name none at all.

### Settled

- ~~**The `exceptions` disposition rules** are rung 2 (D15)~~ — **closed
  2026-09-10 by this rung.** The rules exist (`exceptions_typescript`), the
  runtime declares `capabilities.err_flow: true`, and a 0.2.0 recording is
  answered rather than refused. The half of that row that was never a debt
  stands: a trace **0.1.0 or 0.1.1** wrote still refuses, now through the
  capability sentence, because what it lacks is a record. Re-recording is the
  fix, and it was pre-committed at rung 1 rather than discovered here. The row
  itself is in [`docs/CARRIED-DEBT-ARCHIVE-6.md`](CARRIED-DEBT-ARCHIVE-6.md),
  struck where it stands.
- ~~**A `.catch(fn)` with a non-empty body is not seen** (blind spot 2)~~,
  ~~**`finally` records nothing** (blind spot 3)~~ and ~~**a
  `.catch(function () {})` is not a sink** (blind spot 11)~~ — **all three
  closed 2026-09-10.** Every `.catch(<arg>)` and two-argument
  `.then(<x>, <arg>)` is wrapped and records a HANDLED with one of four words;
  a `finally` that `return`s, `break`s or `continue`s under an in-flight mark
  records `sink_finally_return`; both empty-callback spellings read
  `sink_empty_catch_callback`. Struck in
  [`typescript/HONESTY-BLIND-SPOTS.md`](../typescript/HONESTY-BLIND-SPOTS.md),
  never deleted, each naming what replaced it.
- **A destructuring `catch ({ code })` (blind spot 13) is narrowed, not
  closed.** It still records `type: "undefined"`, and it now also reads
  `catch_escaped` — the transform cannot see what the pattern bound — so its
  verdict is AMBIGUOUS and never SWALLOWED. The under-claiming direction.
- ~~**Two version tokens this slice left standing**: `docs/TRACE-FORMAT.md`'s
  `capabilities.err_flow` sentence and
  `corpus/typescript/exceptions_refused/questions.yaml:12`, both naming
  `sensorium-ts 0.1.0`~~ — **both closed 2026-09-10.** The contract's sentence
  was rewritten at Task 3 when `err_flow` became a key two recorders declare
  (it now names `sensorium-ts ≥ 0.2.0`), and the corpus case was renamed to
  `silent_swallow` at Task 6 with its questions rewritten to the verdict it
  now gets. Neither was carried further; the row is struck here rather than
  in the slice-2 section it belongs to, because that section was still live
  when the strike was written (it is volume 7 from 2026-09-11) and a strike is
  where the reader meets the row.
- **The invocation refusal named one of the two languages it answers for.**
  `_member_refusal` said `exceptions` across an invocation "is defined for Rust
  traces" — true when written, false since Task 4. It now names Rust **and**
  TypeScript and says the member's language is not ruled. Its byte-pin is a
  **fenced Rust test**, and the sentence and the pin moved in one commit. That
  is one of **two** sanctioned edits to a fenced Rust test in this rung, both
  re-pins of the retired TypeScript refusal and neither moving a Rust answer:
  `64e1b05` (this sentence and its pin, `tests/test_exceptions_invocation.py`)
  and `55b3fd7` (P7's re-pin of the retired lang-keyed refusal to the capability
  sentence in `tests/test_exceptions_rust_gate.py`, on a `lang: typescript`
  fixture, named in the Task-4 dispatch). Each commit body says so.
- **The grouper is one module with two renderers.** `exceptions_group` was
  Rust-only prose; it now takes a per-language `Renderer` and a `site()`
  callable, `group_chains` staying as a thin wrapper. Every Rust caller and
  every Rust test is byte-unchanged, which is the evidence rather than the
  claim.

### The four gaps this rung's measurement found (record §5)

Findings, not stops: none is an endpoint's rule and none moves a number.

- ~~**Gap 1 — the shape key's id mask carries Rust's float-type exclusion onto
  TypeScript traces, so 30 shapes are 28 places.** `exceptions_group.MASK` is
  `\b(?!f(?:16|32|64|128)\b)([ef])\d+\b`: `f32` and its siblings are Rust type
  names a panic message can carry (ruling R-G8), and on a TypeScript trace they
  are ordinary FRAME ids. Measured on the lens: S1, S11 and S17 are the same
  clause at `src/hooks/useAiAssist.ts:56`, printed as three blocks because
  their sinks sat in frames 174, 128 and 32. Nothing else moves — tallies count
  units, not shapes, and the adjudication reached the same word for all three.
  **Closing it** means keying on the classifier's own components — disposition,
  site, the verdict's parts — instead of on masked prose, which the grouper's
  own docstring already names as the better answer and as CARRIED-DEBT. This
  is the first measurement of that debt on a TypeScript lens. *Cost if wrong:*
  a reader counts places from a shape count and is over by two in thirty.~~ —
  **closed 2026-09-11 by S5 rung 3**: the TypeScript key now holds the
  verdict's own words under a mask that exempts nothing (record §2.3 entries
  3–4); E-places read **28 of 28** SWALLOWED blocks, the `useAiAssist.ts` L56
  sink printing once (record §3 row 7, §4.4). See the rung-3 section below.
- ~~**Gap 2 — three reused instruments were measuring the wrong binary, and it
  took this rung to notice.** `arms.sh`, `e3.sh` and `e7.sh` hard-coded the
  global `sensorium`, which is an editable install of `main`; a rung that ships
  a new recorder would have reported main's numbers under its own name. Fixed
  before any of the three ran here (record §2.3), default unchanged so the
  earlier readings stay reproducible. **Closing it** means a shared rule that
  every acceptance instrument takes its binary from the branch under test, and
  a check that says which binary a cell used. *Cost if wrong:* a future slice
  reuses a fourth instrument with the same hard-coding.~~ — **closed
  2026-09-10 at this rung's own Task 4**: every acceptance script invoking
  `sensorium` resolves `<repo root>/.venv/bin/sensorium` and refuses outside
  it, checked by `tests/test_acceptance_scripts.py` (E-branch, record §3
  row 4).
- ~~**Gap 3 — E7″'s needle list cannot be applied as written.** §1's list
  includes `Err`, `oid` and `chain`, and the inherited instrument matched
  needles as case-insensitive substrings: under that reading `Err` is matched
  by every `Error('…')` an answer prints, so the endpoint would STOP on any
  transcript naming an exception type and could not be passed by a correct
  recorder. The reading was fixed before the count was taken (record §2.3);
  slice 2 hit the same edge on `python ?` and this is the **second** time.
  **Closing it** means pre-registering a needle's MATCHING RULE beside the
  needle. *Cost if wrong:* a third slice writes a list of literals whose rule
  is discovered when the instrument runs.~~ — **closed 2026-09-10 at this
  rung's own Task 4**: the needle checker prints its own matching rule
  (whole-word for `oid`/`chain`/`Err`, substring for the rest) into the
  transcript header it reads (spec §4.3; E7‴ read **0** occurrences over 9
  needles, record §3 row 8).
- ~~**Gap 4 — on real code the modal AMBIGUOUS reason is the rules' last one,
  and the shape behind it has no name.** Of the 30 AMBIGUOUS shapes, **17**
  read *"no rule of this recorder reaches a verdict here"* (§3.3 rule 5's
  catch-all) and 13 read the escaped-handler reason. One of the 17 was opened
  and diagnosed rather than guessed at: a RAISE whose frame closed by unwind,
  whose traced PARENT frame closed by **return**, and for whose serial there is
  no HANDLED anywhere. What caught it is untraced code sitting INSIDE a traced
  frame — a React error boundary, a vitest `toThrow` — which is the same blind
  spot §6.1's Task-6 amendment records for `translated` and `test_failed`, and
  is now `typescript/HONESTY-BLIND-SPOTS.md` item 27. **The rules decline
  instead of guessing, which is what keeps the gate at 0.** **Closing it**
  means either a record that marks an untraced catcher — which this runtime
  cannot see — or a rule that reads the parent's return as evidence, which is
  exactly how a false SWALLOWED would be minted. Naming it is what a later
  rung needs before it decides. *Cost if wrong:* nothing measured; more than
  half of a real lens's ambiguity stays unnamed.~~ — **closed 2026-09-11 by
  S5 rung 3**: the rules now name the shape, `untraced catcher`, in three
  variants, still AMBIGUOUS — **0 false names of 20** printed blocks against
  the seventeen-row hand read, all seventeen predicted before this code
  existed (record §3 row 5, §4.2). `HONESTY-BLIND-SPOTS.md` item 27 is
  narrowed, not struck: naming the shape is not the same as reading what the
  untraced code did with the failure. See the rung-3 section below.
- ~~**A Gap-4 NEIGHBOUR with a different cause** (the final review's probe, not
  one of the 30): `catch (e) { console.error(e); throw e }` whose rethrow
  unwinds the test root also prints rule 5's catch-all — but here there IS an
  absorbing HANDLED for the serial, in an **earlier** window, and §3.3 rule 4's
  absorbing conjunct is trace-global rather than scoped to the unit's own
  window. Same bucket, different diagnosis. **Closing it** is a rung-3 look at
  window-scoping that conjunct, with a corpus case (`logged_rethrow_to_harness`)
  pinning whichever reading is chosen. *Cost if wrong:* nothing measured; one
  more unnamed shape inside Gap 4's 17.~~ — **closed 2026-09-11 by S5 rung
  3**: rule 4's absorbing conjunct now reads within the unit's own window
  only, so `logged_rethrow_to_harness` reads `PROPAGATED -- to the harness`
  rather than the catch-all; the escaping conjuncts of rules 3 and 4 stay
  trace-global (record §4.5's corpus reading; spec R2). See the rung-3
  section below.

### Deferred by ruling

Each was ruled at execution, is in the spec's §14, and leaves something a
later rung may want.

- **A `try` with its own `catch` clause is never marked** (P1, HONESTY blind
  spot 18). Only a catch-**less** `try` whose `finally` completes gains the
  synthetic marking clause, so a rejection **awaited inside** that catch body
  followed by a completing `finally` records nothing. `thr` sets no mark
  either — the plan narrowed spec §2.3, which had it mark the parent frame.
  Declared before the runtime was built and never measured away. *Cost if
  wrong:* a real swallow in that shape is invisible, in the under-claiming
  direction.
- **`.catch` and `.then` are wrapped on ANY receiver** (T2 ruling, blind spot
  24): the transform cannot type the expression, so a non-promise API's
  `.catch(fn)` is wrapped too and its callback can write an orphan HANDLED that
  reads *SWALLOWED, born outside a throw statement*. Made an explicit E6-TS′
  adjudication watch item — such a line counts FALSE — and the lens sweep found
  none among 30. *Cost if wrong:* the one route to a false SWALLOWED this rung
  could name, measured at zero on one suite.
- **A mention inside an intermediate call within a `console` argument reads
  `catch`** (T2 ruling, blind spot 20): `console.log(sanitize(e))` is logged,
  the `String(e)` reading applied consistently, so a helper that STORES `e` and
  returns text is read as a swallow. Watched in the adjudication; no such shape
  appeared. *Cost if wrong:* as above, and in the over-claiming direction.
- **The logging family is `console.*` only** (R3, blind spot 19). A project
  logging through `pino`, `debug` or its own `logger.error(e)` reads
  `catch_escaped` and gets AMBIGUOUS where the shape is the archetypal swallow.
  Nothing counts how often that happens. *Cost if wrong:* on a consumer with a
  logger library, the command under-reports and says nothing about it.
- **An opaque handler is never accused** (R4, blind spot 23) and **a closure
  that captures the binding is an escape even if it never runs** (blind spot
  21). Both are the syntactic rule declining to follow a value, both
  under-claim, and both are declared rather than measured.
- **`finallyCompletes` counts `return` at closure depth 0, and `break`/
  `continue` only when no loop or switch INSIDE the `finally` encloses them**
  (T0 ruling): a break that stays inside the finally discards nothing. The
  census imports the predicate from `escape.mjs` so E2″'s two halves share one
  rule. *Cost if wrong:* a spec §2.3 refinement; nothing measured moved.
- **The `translated` case's wrapper raise reads AMBIGUOUS, not PROPAGATED**
  (T6 ruling): the wrapper is thrown from a traced arrow that vitest's
  untraced `toThrow` called from inside a traced test frame, and the rules
  cannot see an untraced catcher between two traced frames. AMBIGUOUS is the
  honest word and the pre-registered SWALLOWED count (0) is unaffected. Gap 4
  is the same shape, measured at scale.
- **An assertion failure born in `expect` writes no RAISE row** (T6 ruling,
  blind spot 26): a failing `expect` throws inside vitest's untraced code, so
  `exceptions` cannot see it and `propagated (to the harness)` is reachable
  only from a `throw` in traced code. `info`'s exit line is where such a
  failure shows. This is why `corpus/typescript/test_failed` is a `throw`.
- **The in-flight mark stores the whole `exc` object, not the serial** (T1
  ruling, spec §14 R2), so `handledFinally` writes the marked throw's OWN
  complete `exc` — `kind`, `type`, `msg`, `serial` — and nothing `unread`.
  *Cost if wrong:* one object per marked frame instead of a number.
- **E2″'s numerator comes from the transform's OWN OUTPUT** (T2 ruling):
  `census_catch.mjs` runs `transformSource` over each eligible file and counts
  the markers by `how` word; no manifest key was added. *Cost if wrong:* a
  census that reads text the transform wrote rather than a manifest it
  declared — the goldens hold the text's shape.
- **The assembler stamps `recorder_basis` on every cell** (T7 ruling), `own`
  on the two that record themselves. A re-assembly of saved cells is not a
  re-measurement, which is what slice 2's misattribution lesson asked for.
- **§3.3 rule 4 declines on two conjuncts the sentence did not state**
  (spec §14 R15, written into §3.3 in place at the final review): an escaping
  HANDLED anywhere for the serial routes to rule 5, and an absorbing HANDLED
  blocks rule 4 only while its frame has not returned. Both narrow the verdict
  and the 30 adjudicated shapes were read under the coded rule, so no measured
  number depends on the difference. What it leaves: **a handler that escaped
  and then rethrew out of the test root reads AMBIGUOUS where PROPAGATED would
  be truer.** **Closing it** is a rung-3 rule change with a corpus case
  (`escaped_rethrow_to_harness`), not a fix inside this rung. *Cost if wrong:*
  a propagation the recorder could name is reported as unknown; nothing is
  accused that should not be.
- ~~**The callback-side bare-rethrow exclusion has no probe marker** (43e1fbd;
  the final review's Minor 5). `escape.probe.test.ts` pins `bare_rethrow catch`
  for the clause syntax; the callback form — `.catch((e) => { throw e })` reads
  `catch_callback`, R10 — is pinned by `typescript/test/escape.test.mjs` and
  the contract only. **E8″ was measured at 32 of 32 markers after 43e1fbd, so
  adding a marker now is a post-measurement instrument change**: it goes in the
  next slice, with the endpoint re-read. *Cost if wrong:* one shipped rule with
  a unit pin and no probe pin, on a lens the probes do not cover.~~ — **closed
  2026-09-11 by S5 rung 3**: `escape.probe.test.ts` gains
  `callback_bare_rethrow`, expecting `catch_callback`; E8‴ read **33 of 33**
  markers (19 `// SWALLOW` + 14 `// ESCAPE`), 96 checks, 0 failures (record
  §3 row 3, §4.6).

### Deferred minors, per task

Each is a review's `M`, deferred with its cost; the full text is in the SDD
ledger (`.superpowers/sdd/2026-09-10-sensorium-s5-rung2-throw-flow/progress.md`,
each task's "Minors deferred" line), archived with the worktree.

- **T0:** the record's report line counts went stale post-amendment (M2/M3);
  §1's preamble calls its wrapped plan-block heading "the only editorial act"
  (M6).
- **T2:** `console.log({ e })` — a shorthand inside a console argument — reads
  logged and is untested either way (M2); the climb-through inverts the
  module header's "errs toward escaped" promise (M3 — **closed 2026-09-10 at
  the final review**: `escape.mjs`'s header now names `isLogged` as the one
  deliberate exception, agreeing with blind spot 20); `checkEscape`'s `got`
  map is keyed by line and collapses two HANDLEDs on one line (M5);
  `spliceFinally` returns silently when it finds no keyword (M6).
- **T4:** `_unresolved`'s primitive trigger is trace-global, so two unrelated
  `throw "boom"` swallows in two tests both read ambiguous "across a rethrow"
  — safe, but the reason is mis-named (M2); `left_frame` keeps one outermost
  unwind per serial (M3); raise×handled pairing is quadratic (M4);
  `exceptions_cmd._language_refusal`'s docstring drifted (M1).
- **T5:** `_ambient` branches on `LANGUAGES["rust"]` identity outside the
  table (M1); `Renderer`'s fields are typed `object` and built positionally
  (M2); the grouper's nouns are still Rust's (`Shape.chains`, `Merged.n`) (M4).
- **T7:** the record's `### 3.x` headings shadow the spec's own numbering, as
  slice 2's did; every ambiguous citation is qualified in place.

### Process lessons

- **An instrument defect found before the number is a fix; found after, it is
  a re-roll.** Four of this rung's corrections were made before the endpoint
  they touch had been measured — the bare-rethrow amendment, E2″'s numerator,
  the `SENSORIUM_BIN` hook and E7″'s matching rule — and each is written into
  the record's §2.3 with the date and the reason. The one that arrived after a
  number would have been a different thing entirely, and none did.
- **A pre-registration can encode a shape that its own rule then makes
  unreachable.** §1 locked `rethrow_hop` at one SWALLOWED line while
  `escape.mjs` counted every `throw` operand as an escape, which barred every
  `throw e` hop from SWALLOWED by construction. The lock is what surfaced it:
  a count that cannot be reached is a louder signal than a count that is
  merely wrong. The fix was a rule change with a dated spec amendment, taken
  before any endpoint ran.
- **Check what a needle matches before pre-registering it as a literal.**
  Gap 3, and the second time in two slices. A list of literals is not a rule
  until its matching is written down beside it.
- **A verdict word must come from a rule.** The measurement commit's own
  subject said the rung ships PASS; no rule of this pre-registration supplies
  that word, and the record now says DONE with the correction dated in place
  and the old subject left as history. Slice 2 made the same correction to its
  rows; this rung had to make it to its own shipping word.
- **Draft, measure, then cut.** This section was drafted at its full length
  against a live file of **774**, which is why rung 1's section was cut to
  volume 6 before a line of it was appended.

## 2026-09-11 — S5 rung 3, naming the ambiguity (Python 0.11.0 / sensorium-ts 0.2.0)

The rung that names rung 2's own Gap 4: the seventeen blocks reading *"no
rule of this recorder reaches a verdict here"* now read a reason,
`untraced catcher`, predicted by a human from source before any of this
code existed. Twelve plan decisions (P1–P12) and thirteen controller
rulings, every one of them in the spec's §12. **The rung ships DONE** —
eight endpoints, each run once, no rule's failure word fired; the gate
that decides the word, `E6-TS‴`, read **0 false names of 20** printed
blocks against the seventeen-row hand read. Nothing was recorded this
rung — one re-read of the kept rung-2 invocation, hashed byte-for-byte
before and after.

### Settled — rung 2's own debts, closed here

Struck where they stand, above, with a dated pointer; restated in full
here because a reader who reaches this section first should not have to
scroll up to find what closed.

- **Gap 1** (the shape key's id mask) — closed: the TypeScript key holds
  the verdict's own words under a mask (`\b[ef]\d+\b`) that exempts
  nothing; the origin site enters only where the verdict names none of its
  own. `E-places` read **28 of 28** SWALLOWED blocks (record §3 row 7,
  §4.4).
- **Gap 2** (three instruments measuring the global binary) and **Gap 3**
  (E7″'s needle list unapplicable as written) — both closed at this
  rung's own Task 4, before Task 5 read a number: every acceptance script
  resolves `<repo root>/.venv/bin/sensorium`; the needle checker prints
  its matching rule into the transcript header (spec §4.3; record §3
  rows 4, 8).
- **Gap 4** (the modal AMBIGUOUS reason had no name) — closed: `untraced
  catcher`, in three variants, still AMBIGUOUS. **0 false names of 20**
  printed blocks; 17 of 17 hand-read rows named; `unnamed` after 0
  (record §3 row 5, §4.2). `HONESTY-BLIND-SPOTS.md` item 27 is
  **narrowed**, not struck — naming the shape is not the same as reading
  what the untraced code did with the failure, which stays unread.
- **The Gap-4 neighbour** (rule 4's absorbing conjunct read trace-global)
  — closed: it now reads within the unit's own window; a logged rethrow
  to the harness reads `PROPAGATED`
  (`corpus/typescript/logged_rethrow_to_harness`, record §4.5).
- **The callback-side bare-rethrow probe marker** — closed:
  `callback_bare_rethrow` added to `escape.probe.test.ts`; **E8‴** read
  **33 of 33** markers (record §3 row 3, §4.6).

### New debts this rung's measurement found

- **`Shape.site`'s `key[1]` fallback is a fence, not a guarantee.**
  `exceptions_group.Shape.__post_init__` still reads `self.key[1]` when no
  `site` is handed in — true of Rust's key and of every hand-built `Shape`
  a test constructs, but no longer true in general once a key's second
  component can be something other than a place. **Closing it** means
  making `site` a required argument once the Rust grouping fence lifts
  and every hand-built test passes it explicitly. *Cost if wrong:* a
  future renderer whose key puts something other than a place at index 1
  gets a wrong `site` silently.
- **The store's own command journal, `invocations.jsonl`, sits outside
  the hashed trace set.** The T5 re-read appended exactly one line to
  it — the read's own receipt, ruled NOT the forbidden write (record
  §4.1) — but §2.1's hash list covers only `traces/*.db` and the spool's
  `*.jsonl`, so a `sha256sum -c` returning all-OK says nothing about the
  journal either way. **Closing it** means the next rung either hashes
  `invocations.jsonl` too, with a pre-registered expected delta of one
  line per pre-registered command, or names it out of scope in the same
  sentence that names the hashed set. *Cost if wrong:* a read that
  silently also wrote a trace would pass this rung's own gate.
- **A fenced pre-registration pattern that matches no file.**
  `tests/test_exceptions_python*.py` (spec §7, §1's E-legacy clause)
  matches no file in this tree — the Python reader's own tests are
  `tests/test_exceptions.py` and `tests/test_exceptions_synthetic.py`.
  `e_fences.py` reports the miss in the cell's `dropped` rather than
  folding it into the gate (record §2.3, §4.7). **Closing it** means the
  next rung's pre-registration names the real files before it is locked.
  *Cost if wrong:* none measured; a fence reading intact for a pattern
  matching nothing is a fence over an empty set.
- **The hand read's uniform prediction leaves two of three variants
  unmeasured on the lens.** All seventeen rows predicted the `returned`
  variant; the `had not closed at the end of the recording` and `later
  unwound with <exc>` variants are pinned by
  `tests/test_exceptions_typescript_reasons.py` and the corpus case
  `untraced_catcher_later_failure` only, never by a hand-adjudicated row
  on somebody else's code. *Cost if wrong:* nothing measured; a future
  lens is the only way to learn whether either variant is common there.
- **`tests/test_acceptance_scripts.py` is 315 lines**, comfortably under
  the 800-line ceiling today, but it is the file every future E-branch
  instrument change grows. Watched, not acted on.
- **Spec §4.3's prose and the shipped instrument disagree on which
  needles are whole-word.** §4.3 reads "whole-word for `Err` and `Rust
  disposition`"; the shipped rule and the locked transcript header are
  `oid`/`chain`/`Err` whole-word, `Rust disposition` substring (record
  §4.6). §4.3 gains a dated parenthesis saying the locked block and the
  instrument bind, not the earlier prose. *Cost if wrong:* a reader of
  §4.3 alone expects a stricter match than the tool makes.
- **The T0 hand read's row 1 calls the untraced catcher "a library
  `try`"** where it is a `.catch` chain on the promise TanStack Query's
  retryer returned. The locked table keeps the words it locked; the
  record's §3 states the correction in place rather than editing the
  table. *Cost if wrong:* none — the prediction the row supports
  (`useCompendiumQuery.queryFn`, `returned`) is the one the reader
  printed.
- **`Index.left_frame` is per-serial and outermost, so a window-2 rethrow
  that stayed inside traced code reads a window-1 root.** The frame the
  reason's sentence names is the outermost frame the SERIAL left, across
  every window that serial has; where a rethrow unwound no further than
  the frame its own predecessor left, `f<child>` is window 1's id rather
  than the rethrow's. This is rung-2 behaviour, untouched here, and the
  PARENT — and so the name the reason prints — is unaffected. Raised at
  T1's review and carried to T5's dispatch; no block on the lens showed
  the shape, so it is recorded rather than measured. *Cost if wrong:* a
  reader following `f<child>` out of a rethrow's block lands on a frame id
  from the wrong window.
- **Task 4's `lens.stamp()` wiring into the three legacy assemblers is
  verified by the slice-2 tooling test only.** `assemble.py`,
  `assemble_rung2.py` and `assemble_slice2.py` gained the call at T4; the
  Global Constraints freeze their results, so not one was re-run against a
  store this rung and the evidence is
  `tests/test_acceptance_s5_slice2_tooling.py` (16/16 green) plus one
  standalone interactive check — new code on old, frozen paths. *Cost if wrong:* a future re-run of an old
  assembler fails or mis-stamps, and this rung's measurement would not
  have caught it.
- **`typescript/acceptance/e7_report.py` rewrites the transcript it is
  handed, in place** — it prepends the needle-rule header to the same file
  (`e7_report.py:123-124`), so a second run over one transcript prepends a
  second header, and rung 2's `e7.sh`, which reuses this reporter,
  inherits the write. **Ruled NOT fixed this rung:** an instrument defect
  found after its number is a finding, not a fix, and the transcript's
  sha256 is pinned in the record (§4.1). **Closing it** means guarding on
  a header already present, or writing the header to a sibling file.
  *Cost if wrong:* nothing measured — nobody ran it twice this rung; a
  later re-run mangles the transcript it exists to preserve.
- **`CHANGELOG.md` sits at exactly 800 lines**, the ceiling
  `tests/test_ceiling.py` enforces, so the next release entry cannot be
  written until its oldest section is cut. The mechanism is this repo's
  own and is NOT this file's numbered volumes:
  [`CHANGELOG-ARCHIVE.md`](../CHANGELOG-ARCHIVE.md), one archive file, the
  oldest entries moved into it as a pure move in a commit that lands
  BEFORE the release entry is appended — the way `0.8.2`, `0.8.1` and
  `0.8.0` moved at rung 1. Cut before append. *Cost if wrong:* the release
  commit fails `test_ceiling.py`, and the entry gets trimmed to fit
  instead of the file being cut.

### Process lessons

- **A hand read predicts words, not a technique.** Row 1's "a library
  `try`" named the wrong syntax and still supported the right prediction,
  because the reason the reader prints does not depend on which untraced
  construct did the catching. A locked table is locked on its
  predictions; a wording slip in its own prose is a correction, not a
  re-open.
- **A pre-registered bracket string can describe a shape the printer
  cannot produce.** `[×3 …]` was read as a shape prediction (printed
  once, with a `×N` bracket) rather than a literal, and the arithmetic
  (130+1+1 = 132) is what the reading was checked against instead. The
  next rung's pre-registration pins brackets by their arithmetic, not by
  a quoted example.

