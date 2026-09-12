# Changelog

## 0.12.0 — 2026-09-12

**TypeScript records per statement, when it is asked to.** S5 rung 4 gives
`sensorium ts run` a focus tier. `--focus <spec>` is resolved against the
consumer's own AST with the consumer's own TypeScript **before anything is
spawned** — a spec that names nothing is refused at exit **2** with the
closest eligible qualnames, and a spec that names only functions this
recorder never instruments is refused with the reason and its count — and the
transform then splices a probe after every statement of the functions it
selected. One **LINE** row per completed statement, its `deltas` the bindings
that statement wrote and nothing else; a guarded body's head names as a
synthetic first row at each entry; the block-scoped names a block-like
statement declared listed `unbound` on that statement's own row; and the CALL
of a focused function carrying its `args` where an unfocused one still reads
`<unread: locals>`. Python **0.12.0** (the driver's `--focus` and its
resolver, the converter's `_on_line`, the inspect dialect, the `--at`
spellings, `flow --object` on a serial, the predicate constants);
**`sensorium-ts 0.3.0`**, bumped at the rung's second task before any of it
was measured. The Rust crates do not move. `TRACE_FORMAT` stays **4** and the
wire stays **v1** — a 0.2.x spool converts under 0.12.0 unchanged, and a
converter that predates the LINE record refuses one by name.

- **Identity is a serial now, not an address.** `dbg()` mints `oid` (a
  `WeakMap` serial, once per object, never reused) and `type` on every object
  or function it captures — a RETURN value at the call tier, an argument and a
  statement's delta under a focus — so `sensorium-ts 0.3.0` declares
  `capabilities.object_identity: **true**` unconditionally and `flow --object`
  is **exact**: no gap analysis, a `flow of object #64 (Array)` header and
  `continuity: exact (serial identity)`. `corpus/typescript/object_refused`
  became `corpus/typescript/object_identity`, a refusal turned into an answer.
- **One `dbg` kind, two dialects.** A TypeScript capture is `util.inspect`
  text and a Rust one is `Debug` text; `watch --expr` reads and `flow --value`
  writes each through its trace's own dialect, never through the other's.
  Every spelling was **generated**, not guessed: 41 measured rows in
  `typescript/test/fixtures/inspect-table.json`, four of which would have been
  wrong by hand — `5.0` prints `5` (JavaScript has one number type, the
  opposite of Rust's `2.0`), `-0` keeps its sign, `\v` prints `\x0B`, and a
  `${` in the text rules the backtick quote out. `null`, `undefined`, `true`
  and `false` are predicate constants in every language.
- **`--at` and `--focus` are one spelling.** The file half of a site may be
  the dotted module, the stem, the basename or the root-relative path, in
  every language, so every `--focus` spelling is an `--at` spelling; one
  fixture (`typescript/test/fixtures/site-spellings.json`) holds the JavaScript
  matcher and the Python one to the same ten rows. `info` prints
  `focus matched: <n> — …` beside the specs as they were typed, with
  `(<n> function(s) focused by the transform)` where the transform's own count
  differs — on a focused Rust trace too, because the line is gated on a meta
  key and never on a language.
- Ten new corpus cases — `focus_let_chain`, `focus_loop_counter`,
  `focus_block_scope`, `focus_destructure`, `focus_args`, `focus_async`,
  `focus_catch_binding`, `focus_place_write`, `focus_container`,
  `flow_value_inspect` — the only ten recorded under a focus, plus
  `object_identity`, bring `corpus/typescript/` to **42** and the whole corpus
  to **105 cases, 220 questions**. A vitest case declares its focus with the
  Python recorder's own key, `record: {focus: [...]}`. Five new vectors,
  `v35`–`v39`: the predicate constants, a TypeScript LINE and its args, the
  serial `flow --object`, the inspect dialect's two directions agreeing, and
  the site spellings as CLI questions.

**The rung ships `DONE-WITH-STOP`** — eight endpoints, each read once, three
of them STOPped (record
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md` §3–§5,
measured on 830 files of a real frontend). **H3 is the one the rung exists
for and it PASSed on the first reading**: the first `parseDiceGroups('1d20')`
activation carries **9** LINE rows, their lines **69, 70, 71, 72, 73, 74, 76,
75, 72**, every delta name and the one `unbound` list row for row against a
hand count written — and sha256-locked — before `bindings.mjs`, `probe.mjs`,
the runtime's `line` or the converter's `_on_line` existed. Empty diff. **H1**
4/4: an unfocused arm declares `line: false` / `locals: false`, writes zero
LINE rows, and `watch` refuses it at exit **3** in a sentence naming the
recorder the TRACE carries. **H6** 4/4: two sightings of one array across two
functions, one serial, `continuity: exact`, both `Array`. **H8** 6/6: 105
corpus cases and 220 questions equal, `pytest -q` 4090 passed / 33 skipped,
`cargo test --workspace` 773 passed, `npm --prefix typescript test` 521
passed, the probes' 146 checks green, and 0 of nine leak needles over 13
transcripts. **H7**, reported and gating nothing: ×**2.3816** on the median
wall of one 26-test file (0.7955 s → 1.8946 s, n=3 each, interleaved) for 295
extra LINE rows and the same call tier, plus **1.132 s** of resolution over
830 files, once per invocation.

**The three STOPs, and what each one is about.** **H2** is the
pre-registration's own under-derivation: three typed specs resolved to **six**
sites where §1 pre-committed three, because `focus.mjs`'s documented prefix
rule selects the function-likes nested inside a container — a `reduce` arrow
and two default-parameter arrows. The behaviour is the design's; the number
was a count of the functions a reader names, not of the ones a spec selects,
and `resolve.mjs` is where anyone finds that out before a run. Beside it,
`focus_matched` **5** against `functions_focused` **6**: two anonymous arrows
share one `<file>:<qualname>`, so a qualname is not an identity for an
anonymous function-like. **H4** and **H5** are the INSTRUMENT's, not the
recorder's: H4's cell tested "no HIT at line 72" where the pre-registration
predicted "no HIT at the `while`-COMPLETION row", and line 72 also carries a
head row; H5's row parser could not see a CALL sighting its own transcript
prints, because a printed CALL row's name carries its argument list and no
line at all. Both were found after their numbers were read, so both are
findings and the numbers stand — the next slice re-registers H2, H4 and H5
under fixed instruments, the way rung 1's E6′ became E6″. The lesson is about
the dry run: a rehearsal that does not exercise every SHAPE an endpoint can
meet verifies plumbing, not reading.

`docs/TRACE-FORMAT.md`, `docs/trace-format/TYPESCRIPT-KEYS.md`,
`typescript/HONESTY.md` (a new §11, *Under a focus*), `HONESTY-BLIND-SPOTS.md`
(items **28–37**), `docs/query.md` and both READMEs are amended to this state;
the design's §15 carries all fourteen plan decisions and every controller
ruling that amended a section, with what shipped and the cost if wrong,
including the two that changed the spec's own rules — **R23** (a `do…while` gets no head row, so §3.2's
guard list is narrowed) and **R29** (§2.2's `Closest:` clause gains the case
where only `<anonymous>` qualnames are eligible). `docs/CARRIED-DEBT.md` closes
five rung-3 debts and opens this rung's.

## 0.11.0 — 2026-09-11

**The catch-all gets a name.** S5 rung 3 closes rung 2's Gap 4: the
seventeen blocks reading *"no rule of this recorder reaches a verdict
here"* now read a reason, `untraced catcher`, in three variants — `its
caller f<n> returned; not followed`, `later unwound with <exc>: a
translation by untraced code, or a later failure, indistinguishable`, and
`had not closed at the end of the recording; not followed` — each
predicted by a human from source before this code existed. Rule 4's
absorbing conjunct is now window-scoped, not trace-global, so a logged
rethrow to the harness reads `PROPAGATED` where rung 2 read this same
catch-all (`corpus/typescript/logged_rethrow_to_harness`); a second tally
line prints only when non-empty — `ambiguous by reason: escaped 21,
untraced catcher 32` on the kept lens. Python **0.11.0** (the reason, the
window scope, the site-bearing TypeScript key — the verdict's own words
under a mask `\b[ef]\d+\b` that exempts nothing, closing Gap 1's borrowed
Rust float-type exclusion; the origin site enters only where the verdict
names none of its own); **`sensorium-ts` stays 0.2.0**, no runtime,
transform or wire change. `TRACE_FORMAT` stays **4**, wire **v1**; nothing
is recorded this rung — one re-read of the kept rung-2 invocation, hashed
before and after, against a pre-registration byte-locked first
(`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3.md` §1).

Four new corpus cases and the `translated` re-pin bring
`corpus/typescript/` to **32**; one new probe marker,
`callback_bare_rethrow` (`.catch((e) => { throw e })` → `catch_callback`),
closes a rung-2 debt with no probe pin; every acceptance script resolves
`<repo root>/.venv/bin/sensorium` and refuses outside it, only `lens.py`
stamps the `lens` label, and the E7 checker prints its matching rule.

**All eight endpoints ran once, none fired its rule's failure word — the
rung ships DONE** (record §3, §5): **E6-TS‴** 0 false names over 20
blocks, 17 of 17 rows named, `unnamed` 0; **E6-TS′-fence** 0 differences
over 29 gated lines; **E-places** 28 of 28 SWALLOWED blocks; **E6-TS** 21
of 21 corpus cases; **E8‴** 33 of 33 markers; **E7‴** 0 over 9 needles;
**E-legacy**/**E-branch** intact. Left open, none a stop: a block can cover
origins from two rows sharing one parent frame; `[×3 …]` was unprintable,
its arithmetic conserved instead (`[×132 over 11 processes …]`,
130+1+1); and `tests/test_exceptions_python*.py` matched no file, the
fence holding on intent regardless. `HONESTY.md` §4 and blind spot 27 are
amended; `docs/query.md` gains the reason line; `CARRIED-DEBT.md` closes
Gap 1, Gap 4, the neighbour and the probe-marker debt, dated to this
record, and gains new debts.

## 0.10.0 — 2026-09-10

**`exceptions` answers on a TypeScript trace.** S5 rung 2 gives the throw-flow
rows rung 1 recorded a rule to be read by: the same five dispositions
`exceptions` has always printed — `swallowed`, `uncaught`, `re-raised`,
`propagated`, `ambiguous` — computed over JavaScript's own shapes, per trace
and across a whole `sensorium ts run` invocation. Python **0.10.0** (a third
rules module, the per-member invocation dispatch, four vectors, seventeen new
corpus cases); **`sensorium-ts 0.2.0`** (the escape rule, the rejection-callback
wrapper, the `finally` sink, `capabilities.err_flow: true`). The Rust crates do
not move. `TRACE_FORMAT` stays **4** and the wire stays **v1**: the BOOT record
gains `capabilities`, HANDLED gains `how`, and nothing else changes shape —
every Python and Rust `exceptions` output, every existing vector and every
Python and Rust corpus case is byte-identical, which is what the suites that
did not move are the evidence for.

Everything below is measured on one lens — the tabletop VTT frontend at
`0091e97`, **372 test files, 4,278 tests**, under vitest 4.1.9, vite 6.4.3,
jsdom 29.1.1, node v24.16.0, 16 cores — against a pre-registration byte-locked
before any of this code existed
(`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` §1). **Every
one of the nine endpoints ran, once, and not one fired its rule's failure
word.** No row reads PASS and neither does the rung, because no rule of this
pre-registration supplies that word: six name only a failure word, three name
none at all. **The rung ships DONE** — the DONE-WITH-STOP branch §1 spells out
is the one not taken.

- **The recorder classifies a catch binding where the syntax is, and says so
  in `how`** (`sensorium-ts 0.2.0`, spec §2.1–§2.5). A clause's word is decided
  at transform time from its own AST: **`catch`** when the body never mentions
  the binding or mentions it only as an argument of a `console.*` call
  (log-and-continue is the archetypal swallow), **`catch_escaped`** when it
  appears anywhere else, **`sink_empty_catch`** for an empty block. Rejection
  handlers get the same rule applied to their parameter —
  **`catch_callback`**, **`catch_callback_escaped`**,
  **`sink_empty_catch_callback`** (now for the `function` spelling too, closing
  blind spot 11), and **`catch_callback_opaque`** for a handler defined
  somewhere else, whose parameter's fate is not this splice's to say. A
  `finally` block that `return`s, `break`s or `continue`s discards an in-flight
  throw and records **`sink_finally_return`**, read from a one-slot mark per
  frame that carries the real serial (blind spot 3 closes). Nine `how` words in
  all, and the enumeration is the declaration: a shape outside it produced no
  record, and `typescript/HONESTY.md` §4 lists what still produces none.
- **A bare rethrow is a traced exit, not an escape** (`68015dd`, `43e1fbd`,
  spec §2.1's dated amendment). `throw e;` whose operand is the binding itself
  leaves the way it arrived and carries the same serial, so it does not count
  towards `catch_escaped`: `catch (e) { console.error(e); throw e }` reads
  `catch`, while `catch (e) { list.push(e); throw e }` and
  `catch (e) { throw new Wrapped(e) }` stay `catch_escaped`. The exclusion
  holds at closure depth 0 only, and applies to rejection callbacks by the same
  rule. It was found and fixed **before any endpoint was measured**: the
  literal reading barred every `throw e` hop from SWALLOWED and made §1's
  locked `rethrow_hop` count unreachable by construction (record §2.3).
- **The capability is the gate, and an old trace still refuses.**
  `capabilities.err_flow` is **true** on a 0.2.0 recording and the converter
  passes the BOOT record's own capabilities through untouched. A trace a 0.1.x
  runtime wrote declares `false` and is refused at exit **3** by the capability
  sentence — naming the recorder and saying nothing was checked — because what
  it lacks is a record and not a rule. Re-recording is the fix; the cost was
  pre-committed at rung 1, not discovered here. Vector
  `v32-err-flow-typescript-capability-refusal` pins that sentence, and the old
  language refusal is gone: `TYPESCRIPT.exceptions_refusal` is now `None`.
- **SWALLOWED is claimed only where the recording establishes it.** A HANDLED
  whose `how` is in the absorbing set, in a frame that later closed by
  `return`, with no later raise of the serial and **no** escaping handler for
  it anywhere. Everything else is `ambiguous` with its reason printed —
  an escaped or opaque handler, a handler frame still suspended, a primitive
  rethrow, a frame that unwound with a different serial. Nothing reaches
  SWALLOWED by falling through, and an UNWIND is never itself a verdict.
- **`sensorium exceptions <invocation-id>` answers for a whole TypeScript run**
  (spec §4). Every member trace is opened, dispatched on its own `lang`, and
  merged on a shape key the language module supplies, so one clause swallowing
  in 40 processes prints once with `[×N over N processes]` beside it. The
  grouper Rust has used since 0.8.2 is now generalised over a per-language
  renderer, and every Rust caller and test is byte-unchanged.
- **A swallow corpus that runs itself.** `corpus/typescript/` grows from
  thirteen cases to **28** — one shape per case, each with an `exceptions`
  question pinning the verdict line and the tally, and a `why_logs_fail` naming
  all three channels. `exceptions_refused` is renamed **`silent_swallow`**: the
  refusal it recorded is one no recorder produces any more, and it is a vector
  now.
- **What the endpoints read** (record §3). **E6-TS** — the corpus's verdicts,
  **17 of 17** equal to the locked table. **E6-TS′** — the gate that decides
  the shipping word: **0 false SWALLOWED of 30** hand-adjudicated shapes on a
  consumer's own suite, every line's adjudication written into
  `-e6tsp-adjudication.md` under a protocol fixed before any of them was read;
  the tally over that run is `swallowed 261, ambiguous 53` across 314 raises in
  53 of 372 processes. **E2″** — **287 spliced of 287** eligible sites
  (177 catch clauses, 108 `.catch`, 2 `.then`, 0 completing `finally`) over 741
  files, ratio **1.0000**, zero named exclusions needed. **E8″** — **32 of 32**
  probe markers. **E3-TS″** — **0/19** false DIVERGED over twenty recordings of
  one file. **E5″** — both harnesses green. **E7″** — **0** occurrences of nine
  Python/Rust leak needles over both transcripts. **E1‴** — `off/plain`
  **1.0608** and `call/plain` **1.1266** (n=5 per arm, interleaved, every load
  reading under 4.0), against rung 1's 1.0587 / 1.1324. **E10″** — the fresh
  372-spool set converts in **16.0715 s** (n=5), beside slice 2's 16.3859 s.
- **Four gaps, none of them an endpoint's rule** (record §5). **Gap 1** — the
  shape key's id mask carries Rust's float-type exclusion (`f32` and its
  siblings are Rust type names) onto TypeScript FRAME ids, so the lens's 30
  SWALLOWED shapes are **28 distinct places**; no verdict and no tally moves.
  **Gap 2** — `arms.sh`, `e3.sh` and `e7.sh` hard-coded the global `sensorium`,
  which is an editable install of `main`: three reused instruments were
  measuring the wrong binary, fixed before any of the three ran here. **Gap 3**
  — E7″'s needle list cannot be applied as written, because `Err` as a
  case-insensitive substring is matched by every `Error('…')` an answer prints;
  the three identifier needles are matched word-bounded and case-sensitively,
  fixed before the count was taken. **Gap 4** — on real code the modal
  AMBIGUOUS reason is the classifier's catch-all (**17** of 30 ambiguous
  shapes), and the shape behind it is an untraced catcher sitting *inside* a
  traced frame. The rules decline instead of guessing, which is what keeps the
  gate at 0.
- **Documents.** `typescript/HONESTY.md` §4 is rewritten against the shipped
  runtime and its blind-spot list restruck, with the list split to
  `typescript/HONESTY-BLIND-SPOTS.md`; `docs/query.md` gains the TypeScript
  paragraph under `exceptions`; `docs/CARRIED-DEBT.md` gains the rung's section
  after cutting rung 1's to [`docs/CARRIED-DEBT-ARCHIVE-6.md`](docs/CARRIED-DEBT-ARCHIVE-6.md),
  drafted and measured first the way the ledger's own lesson asks; this rung's
  design gains a §14 naming every place its own text moved and why.

## 0.9.1 — 2026-09-10

**The converter's ladder, the plain band re-measured, and `node --test` made
honest.** No new verb and no new key: S5 slice 2 answers the two questions
rung 1 shipped open — E6′'s STOPped timing clause and E10's design input —
and fixes the four things the `node --test` path was getting wrong. Python
**0.9.1** (the converter's write path and its spool reader, the no-spool
refusal); **`sensorium-ts 0.1.1`** (the loader hook). The Rust crates do not
move. `TRACE_FORMAT` stays **4**: no trace key, vector or vocabulary string
changed, and a 372-pair equivalence gate is the evidence rather than the
claim.

Everything below is measured on one lens — the tabletop VTT frontend at
`0091e97`, **372 test files, 4,278 tests**, under vitest 4.1.9, vite 6.4.3,
jsdom 29.1.1, node v24.16.0, 16 cores — against a pre-registration byte-locked
before any of this code existed
(`docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md` §1).
**Every cell this slice pre-registered was measured**: the four gated clauses
whose rule supplies a PASS word — E10′-suite, E10′-file, E10′-eq and E6″ —
read **PASS**, and the H-probes clause, whose rule carries only a STOP,
**held with no STOP**.

- **E6″ — PASS on all five clauses; E6′'s STOP is answered** (`ecdc631`,
  record §3.11 and §4.3). A new pre-registration, not a second look: the
  instrument now carries the load guard E6′ lacked, the band is **derived**
  from the before arm rather than chosen, the comparison is **medians over
  n=5** on each side, and the manifest is verified *after* the after arm. One
  guarded session on the lens — five plain runs, one call-tier recording, five
  plain runs — read the manifest **748 OK / 0 FAILED** before and after, every
  one of the ten plain runs at `372 passed (372)` / `4278 passed (4278)` with
  nothing dropped, **0** `__srt` markers over the 2 cache directories that
  exist, `node_modules/.sensorium` **absent**, and the after arm's median
  **22.1136 s** inside the band **[21.9834, 22.3652]** the before arm's own
  median (**22.1743**) and range (**0.1909**) define. The after arm is 0.0607 s
  *faster* than the before arm. What that closes is bounded and the record says
  so: one session, one lens, one recorder.
- **E10′ — PASS on all three gated clauses: the converter stays Python**
  (record §3.6–§3.9, §4.1). Rung 1 measured full-suite `ingest` at 45.5293 s
  against a 22.5925 s plain wall and made it a design input. Two levers
  answered it, each a commit of its own with its cells measured before the
  next was written:
  - **`TraceWriter(durable=False)`** — one transaction per trace and
    `PRAGMA synchronous=NORMAL` under the WAL `create_trace` already sets,
    committed once in `close()` instead of once per 512-event batch. The
    Python recorder keeps the durable default; one argument, one meaning.
  - **A streaming spool reader** — `spool.read` opens the file, reads BOOT
    from line 1 and **yields** every later record, where it had materialised
    the whole spool. `exit` and `torn_tail` are filled by the walk, and
    `TraceWriter.discard()` (rollback, then close) is what `Builder.abort()`
    calls so an aborted build checkpoints nothing.

  Measured end to end on the pinned 372-spool, 414,450,522-byte copy: the full
  suite falls **45.7378 s → 16.3859 s** (n=5 guarded, **2.7913×**, **6.2066 s
  below** the 22.5925 s bound) and the one file a debugging loop actually pays
  for falls **0.3624 s → 0.1648 s** (n=5, **2.1990×**, against a 0.4002 s
  bound whose failure was the one thing allowed to STOP the ladder). The
  heaviest worker's peak resident falls **2,269,696 kB → 290,948 kB** on the
  same suite cell — **7.8010×** — which was the streaming reader's own
  pre-registered quantity. **A2** (largest-first dispatch) and **A4** (the
  per-record Python cost) were **not built**: the spec conditioned them on the
  first two levers leaving the suite above the bound, and they did not. **Arm
  B**, a Node or Rust converter, is not raised.
- **And the trace did not move** (record §3.9, §5.A). The pinned set was
  converted twice — once by 0.9.0's converter, once by this one — and all
  **372** pairs read **MATCH** under `sensorium diff`, 0 DIVERGED, 0 REFUSED,
  every diff run by one reader over both traces in one store. `diff` compares
  causal structure and not recorded values, which the record states as the
  ceiling on that PASS — so a second, ungated check was pre-registered *after*
  the gate was read and could not move it: every row of `events`, `frames`,
  `code_objects`, `tasks`, `fingerprints`, `task_fingerprints` and `output`
  compared column for column across all 372 pairs. **372 / 372 identical**;
  the only `meta` key that differs on any pair is the minted `run_id`.
- **The loader hook returns Node's own format and erases nothing**
  (`05e5338`, `sensorium-ts 0.1.1`). It had classified by extension and forced
  `format: 'module'`, which meant an eligible `.mts` was instrumented and then
  never type-stripped — Node threw a `SyntaxError` on the file's first
  annotation — and a `.tsx`/`.jsx` was reported as an exclusion it is not.
  The hook now asks `nextLoad` and takes the answer: **Node strips**, the
  recorder splices, and neither pretends to do the other's job. `.tsx`/`.jsx`
  are outside Node's own scope under `node --test` and are not counted as
  exclusions. Four probe files (`.ts`, `.mts`, `.mjs`, `.cjs`) and two
  controls now run under `node --test` in CI: **25 checks, 0 failures**, and
  both controls fail *identically* plain and hooked
  (`ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`, `ERR_UNKNOWN_FILE_EXTENSION`). The
  controls are what makes this a check rather than a hope — measured against
  the pre-fix hook, `enum.ts` loaded under the recorder and failed plain.
- **A no-spool run whose transform excluded everything says so** (`5af2def`).
  `ingest` on a spool directory with no spools said "nothing was recorded, or
  the recorder wrote somewhere else" even when the tallies beside it recorded
  exactly why — every file CommonJS, or a parse error. It now names them by
  reason with counts (`commonjs x2, parse-error x1`) and appends the
  ES-modules-only clause only when `commonjs` is among them. R27's precedent:
  one bare reason loses the split as soon as there are two.
- **Six of the ten per-cell predictions this ladder pre-registered did not
  hold as written, and all three gated clauses pass** (record §4.2). Arm 0's
  0b missed by more than three times (154.3012 s against a predicted 40–50 s);
  all three of the first lever's predictions were falsified, including
  "0e unchanged" — the one-file spool turned out to be commit-*dominated* at
  2.2004× — and the streaming reader's wall prediction ("within noise") was
  falsified **in the fast direction** on both large cells by about 1.25 s
  each. Its RSS prediction is the one that held, with room. The numbers are
  the pre-registered cells'; no threshold moved and nothing was re-rolled.
- **Documents.** `typescript/HONESTY.md` §7 and §9 carry the dated amendments
  and this slice's measured costs; `docs/CARRIED-DEBT.md` gains the slice's
  section; this slice's design gains a `§12` table naming every place its own
  text moved and why. `CHANGELOG.md` cut `0.8.4` and `0.8.3` to
  [`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md) before this entry was
  written, drafted and measured first the way the ledger's own lesson asks.

## 0.9.0 — 2026-09-09

**A third recorder.** `sensorium ts run -- vitest run` records a TypeScript or
JavaScript test suite the way `cargo sensorium test` records a Rust workspace:
one trace per test-file process, trace format **4**, read by the same
`sensorium` command line. Python **0.9.0** — a new verb, a third vocabulary, a
refusal for a fourth, seven conformance vectors and thirteen corpus cases;
**`sensorium-ts 0.1.0`**, one private npm package with `magic-string` as its
only runtime dependency. The Rust crates do not move. `TRACE_FORMAT` stays
**4**: every TypeScript-only key is optional, and no required key changed.

**The rung ships DONE-WITH-STOP**, on a pre-registration byte-locked before
any of this code existed
(`docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` §1). Ten of
the twelve gated endpoints and both §10 controls **PASS**; **E6′ is a STOP**
on its plain-band clause and **E10 is REPORTED** on the design-input branch of
its own rule. One lens under every number: a tabletop VTT frontend at
`0091e97` — **372 test files, 4,278 tests** — under vitest 4.1.9, vite 6.4.3,
jsdom 29.1.1, node v24.16.0, 16 cores.

- **The transform** (`typescript/src/transform.mjs`): the consumer's own
  TypeScript for positions, `magic-string` for edits, and **no edit contains a
  newline**, so every output line is the input's line. Functions get an entry
  guard and an outcome; `await`/`yield`/`yield*` pop the frame and record
  YIELD/RESUME; `throw` records a RAISE and every `catch` a HANDLED; test and
  `describe` callbacks become tasks. Measured coverage: **5,378 instrumented
  of 5,378 eligible** over 367 files, ratio **1.0000**, no unnamed exclusion
  (n = 5,378 sites). Sites keep their lines and columns: **20/20** shapes on
  their exact line, and a planted failing assertion's `FAIL` header and
  `…:44:13` identical plain against driven — on the narrower reading the
  record's §5 gap 8 states, since the driven report also carries two frames
  inside the recorder's own runtime.
  Rulings that changed the design here: **R8/R8b** made the test-wrap rule
  **file-scoped** (a local `describe(label, formula, value)` helper in
  ordinary source was being rewritten; a type-only `vitest` import does not
  make a test file); **R8a/R8c** withdrew a chunk MOVE and splice the
  options-second form **positionally**, so the four shapes it used to refuse
  now come out correct; **R10/R10a** leave a file whose parse produced
  diagnostics **untouched** and counted, and fail loud rather than splice
  blind; **R12** put a `;` after a bare `return`/`yield` (ASI would otherwise
  call the returned `undefined`); **R9** added `.mts`/`.cts`; **R11** names
  `module.exports = fn` `default`; **R7/R7a** made `node_modules` and `.d.ts`
  out of scope with **no** count, and gave the plugin `classify()` to tally
  CommonJS with it.
- **The runtime** (`typescript/src/rt.mjs`, `node:` builtins only): tasks on
  `AsyncLocalStorage` so a continuation lands in the task that started it, a
  frame stack per task, an exception `WeakMap` so a rethrow is one exception
  with two RAISE rows, `util.inspect` return values capped at 200 bytes, and a
  JSONL spool per container. **R13** writes an EXIT record on SIGTERM/SIGINT/
  SIGHUP before re-raising, so a signalled worker's recording is COMPLETE;
  **R14/R14a** cap every consumer-derived string with the contract's own
  `trunc` keys and leave paths uncapped; **R17** counts `#k` per NAME, not per
  registration, so a five-row `.each` is five names and not `… = 5#2`;
  **R16** declares `rt.mjs` external to vite's module runner so one Node
  module instance serves the setup file and the instrumented modules — and is
  named in the ledger as insurance, because at vitest 4.1.9 the
  one-BOOT-per-spool probe reads the same with it and without it.
- **The driver and converter** (`sensorium ts run`, `sensorium ts ingest`):
  Python, so the reader needs no Node. The wrapper config and the setup file
  live under `<root>/node_modules/.sensorium/` for the run and are removed in
  a `finally`; `setupFiles` are appended, never replaced; the command after
  `--` is spawned as typed and the driver exits with the harness's own status.
  Package scripts and jest are refused by name at exit 2; so are Node below
  24, an uninstalled package, an unwritable `node_modules`, a spool directory
  already ingested (`ingested.json`, **P6**) and one no driver wrote.
  **R21** keeps the container's own EXIT as `exit_self_reported` while
  `exit_status` stays `null`/`unwitnessed` — a self-observation is not a
  borrowed status. **R26** records the command AS TYPED (`harness_command`),
  because `node-test --test` is a command nobody typed. **R24**: `--tier off`
  records nothing by design and returns the harness's status, not an exit 2
  over an empty spool directory.
- **The reader, in this recorder's words.** A `TYPESCRIPT` column in
  `vocab.py`; the unit of work is a *test*; `terms()` indexes strictly and
  `db.open_trace` **refuses an unknown `lang` at exit 2** naming the language
  and the recorder (**P3** — one choke point, so every command refuses
  identically). `info_typescript.py` beside `info_rust.py`; `runs` gates its
  TypeScript header and `file:` member on `meta.lang`, never on a key's
  presence, and prints exclusions per reason with counts (**R27**). Two
  reader bugs this recorder was the first to be able to produce are fixed for
  everyone: a NULL `line` now renders **no** `L…` segment instead of `LNone`
  in `tree`'s state tail, in `frame`'s timeline and in `fmt.fmt_event`
  (**R28/R28a**). Measured: **0** occurrences of eight Python/Rust leak
  needles across a 2,241-line transcript of ten commands (n = 8 needles).
- **Seven conformance vectors, `v23`–`v29`**, through the real CLI as every
  vector is: the TypeScript prose, the unknown-`lang` refusal, `exc.kind`
  throw against rejection, the kind labels (`[async]`, not `[coroutine]`), an
  unhandled rejection in meta, `harness_exit` waited, and the `runs` file
  header. **Thirteen corpus cases** under `corpus/typescript/` — six ports,
  three refusals and four TypeScript-only (`each_naming`,
  `unhandled_rejection_in_info`, `suspended_at_end`,
  `timer_callback_parentless`) — one shared vitest project (**P9**), run
  through the real driver, with `--require-driver` turning a skipped case into
  exit 1. **R31** holds every TypeScript case's `why_logs_fail` to naming all
  three channels, the way the Rust cases are held.
- **CI**: a `typescript` job — Node 24, `npm ci --prefix typescript`,
  `npm --prefix typescript run check` (**R4**: the bare `npx tsc -p …` form
  resolves a decoy `typescript` from the repository root, measured rc=1
  against rc=0), the golden and runtime tests under `node --test`, the probe
  project through the driver, the Python vectors and converter tests, and the
  corpus with `--require-driver`. The probe and corpus projects pin
  `vitest@4.1.9` and `vite@6.4.3` exactly (**R18**), so CI runs on the lens
  the acceptance was measured on.
- **What it cost, with `n` and lens.** Recording: `off/plain` **1.0587**,
  `call/plain` **1.1324** (n=5 per arm, interleaved, 0 dropped, conversion
  excluded) — inside the pre-registered 1.10 bound, so the transform stays
  uncached and the source-sha cache stays a later slice. Conversion:
  full-suite `ingest` **45.5293 s** (n=3) against the same run's plain wall of
  **22.5925 s**, ×2.02; one file's spool **0.3638 s** (n=3). Reading: `info`
  **0.5401 s** and `diff` **0.6867 s** (n=3 each) on a 333,832,192-byte trace.
  Verification: **0/19** false DIVERGED over twenty recordings of one file; a
  split control reading `MATCH modulo location` with exactly its two moved
  code objects; and a **value-preserving** planted swap reading DIVERGED at
  causal step 16 — invisible to the consumer's own 56/56 suite, visible only
  to the recording.
- **The STOP, stated as a STOP** (**R32**). E6′ asks whether a plain run
  afterwards is contaminated, in four clauses. The three that ask about
  contamination directly hold exactly — sources identical by sha256 manifest
  (**748 OK, 0 FAILED**), **0** `__srt` markers in any cache directory, the
  wrapper directory absent. The fourth is a timing clause and it did not: the
  plain-after wall **22.8678 s** against the plain arm's own min–max band
  **[22.3136, 22.7221]**, 0.1457 s (0.65%) above it. The number stands as
  measured — nothing re-rolled, no band moved, no verdict renamed — and the
  two instrument gaps it rests on are recorded rather than argued away
  (`e6.sh` took its one timed reading with no load guard, and a five-run
  min–max is a range, not a tolerance). It is re-measured next slice under a
  **new** pre-registration, **E6″**, whose band is derived from the plain
  arm's own spread and whose manifest check runs after its own run.
- **The REPORTED, taken as design input** (**R33**). Converting a whole
  372-file suite costs twice the suite's own wall, so a Node converter on
  `node:sqlite`, or a binary wire, is the next slice's pre-registered design
  question — the second branch E10's rule named, not a STOP. The one-file
  number is reported beside it, because 0.36 s is what a debugging loop
  actually pays.
- **A finding about the consumer, which the pre-registration committed to
  reading as one**: **8 of 372** test files (2.2%) record differently across
  two runs of the same suite. The comparator refused nothing and mis-called
  nothing; the eight are named in the record's §3.4.
- **Documentation.** `typescript/HONESTY.md` — written before the runtime
  existed and now struck against the measurement, with eight new blind spots
  (10–17) and E6′'s STOP in its cost section. `typescript/README.md` is the
  full reference; this repository's README gains a compact `## TypeScript`
  section beside `## Rust`. The TypeScript-only meta keys live in
  `docs/trace-format/TYPESCRIPT-KEYS.md` (**R25**: `docs/TRACE-FORMAT.md` was
  at 752 lines when the ruling was made, and gained only what R25 allowed —
  the `lang` value, the `exc.kind`/`how` enumerations, the `runs` header
  sentence, the vocabulary column and a pointer — which took it to **799** in
  Task 7; the doc pass then edited it no further, under **R35**). The design's
  own deltas — one row per plan decision and per ruling that moved a
  sentence — are §14 of
  `docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md`.
  This file's `0.8.2`, `0.8.1` and `0.8.0` entries — three of them — moved to
  [`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md) **before** this entry was
  written (**R35**), a pure move, wording and dates unchanged.

**What none of this licenses.** No endpoint here says a TypeScript trace
answered a debugging question nobody planted, and none was measured on a
second consumer. Arguments are unread (`locals: false`), there are no LINE
events (`line: false`), and the `exceptions` disposition rules do not exist
yet (`err_flow: false`) — so a 0.1.0 trace stays refused by `exceptions` after
rung 2 lands, and re-recording is what changes that. Each of those is declared
in the trace and refused by name, never silently missing.

## 0.8.7 — 2026-09-08

**The queue, buttoned up.** No new capability: this slice pays the carried
debt four ledgers had accumulated — 116 open bullets at `f14d2f6` — and ships
the ledgers to prove it. Brice funded three of the four buckets: **A**, 54
mechanical rows whose fix was already written (47 taken whole, 3 in part, 4
declined with reasons); **B**, the 800-line ceiling; **D**, 5 rows closable
only by a dated note. **C**, 43 design-level or ruled-not-funded rows, is
untouched and is the next conversation. Python **0.8.7**; **`sensorium-rt
0.4.1`**, its first move since `0.4.0`, because the leaf crate now owns the
one `sha256`; **`sensorium-transform 0.4.4`** and **`cargo-sensorium 0.5.3`**,
which take it from there. `TRACE_FORMAT` stays **4**: nothing here writes a
new key into a trace.

- **One `sha256`, in the crate with zero dependencies** (row #13, ruling R3,
  `a0580d3`). The same ~300-line from-scratch implementation stood in all
  three crates, kept in sync by the same NIST vectors. `sensorium-rt` — the
  only crate the other two can both depend on — owns it as `pub mod sha256`
  and the copies are deleted. **The one observable consequence is a token.**
  `sensorium-rt`'s `RT_VERSION` is a literal by necessity (the bare `rustc`
  line that builds the runtime has no cargo environment, so `env!` will not
  compile) and a unit test holds it to the manifest, so the rt bump changes
  what every Rust trace declares: `recorder: sensorium-rt 0.4.1`. Three corpus
  expectations, one E9 cross-check and the living docs moved with it, each
  re-pinned **by value** — the sentence names the recorder, so loosening it
  would have deleted the check. Nothing the runtime records changed: no wire
  kind, no record shape, no capability. The sha256 vectors the consolidation
  dropped came back at `bde3a66`.
- **Seventeen files split — thirteen before anything edited them, four
  after, which is what R9 asks for** (rulings R2/R9).
  Thirteen the design's seam map named — `tests/programs.py` (`b05046b`),
  `test_tree_frame.py` (`718a013`), `test_boot_cli.py` (`5ef40e5`),
  `test_exceptions.py` (`71d18b8`), `test_diff.py` (`d3823b4`),
  `test_tracer.py` (`4267251`), `test_refocus.py` (`f24745c`),
  `test_acceptance_e6q.py` (#58, `1bd523d`), `rust/tests/acceptance_schema.py`
  (`91242c2`), `rust/cargo-sensorium/tests/convert.rs` (#56, `4b98c3f`),
  `convert/chains/tests.rs` (`9bd2647`), `src/sensorium/record/tracer.py`
  1193 → 672 + two modules (`e87996e`), `src/sensorium/query/refocus_world.py`
  (#55, `f350b9c`) — and four more that this slice's own edits took past 780,
  split at their banners under R9 (`bb6b2c4` and the fix commits). Every one a
  pure move, proved by `--color-moved=zebra` and equal collection counts, with
  seven falsified pointers repointed at `b6e2125`.
- **A repo-wide ceiling gate** (ruling R1, `e531200`, widened in the final
  fix wave). `tests/test_ceiling.py` holds every tracked `*.py`, `*.rs`,
  `*.sh` and `*.md` under 800 lines and exempts the three record directories
  under
  `docs/superpowers/` **by name** — dated history, some byte-locked, amended
  by appended notes and never restructured. Both mutations were measured: the
  limit lowered to 700 names 37 files; a fourth exemption fails the test that
  pins the list. The ruling closes two ledger rows without code — the parent
  spec at 1458 (#59) and the repair acceptance record at 795 (#60) — because
  neither is owed a split. The wave widened the markdown half from three
  named patterns to `*.md` whole, which closes the class rather than the
  three files it happened to be missing: `CHANGELOG.md`, `ORIGIN.md` and
  `corpus/rust/README.md` join the enumeration, and this file's own pre-0.8
  entries move to `CHANGELOG-ARCHIVE.md` first — a pure move, off 798 lines
  and two from a ceiling nothing was checking. `docs/CARRIED-DEBT.md`'s
  near-ceiling list carries the measured number.
- **The E4″ instrument's five gaps, with the measurement closed** (rows #1–#5,
  ruling R5, `962cacd`, findings lines `8c4dde1`, renderer `b0c3720`): H8's
  presence reader matches the listing's last path segment as well as the whole
  name and records `null` with the listing command and its rc; the STOP's
  label is derived from what missed, with both sides printed when they
  disagree; `driver_version` is read from the copied original too; H2's
  fragment counts are published per side and per pair; and `walls_s` carries
  `driver_build`, `dry` and a per-arm cargo summary. No published number is
  re-derived and no `results.json` is re-assembled — every fix changes what
  the NEXT run publishes and is pinned by a unit test on synthetic records.
  **Both schema tokens moved with the shapes their assemblers publish:
  `e4pp/2` and `e9/2`**, raw and assembly together, so a fresh run's two
  tokens agree and only a genuine re-derivation of a closed record differs;
  `e4/1` is untouched.
- **The instruments' own honesty**: `ENV_RECORDER_OWN` anchored on its clause
  rather than the line's end (#8, `04d0243`); the E4″ runner's seven minors
  (#9, `862ffa0`); the E4′ lock test diffing the whole pre-amendment range
  (#12, `32aab32`, measured discriminating on a single moved byte);
  `line_rows_per_run` reading the census that counted it (#17, `3e1dac9`); one
  manifest reader for rung 2 and rung 3, its workaround deleted (#22,
  `05148e8`); the e6q runner's falsified expectation swept (#25),
  `render_grain`'s three literals derived (#32) and the grain box-path scan
  walking the directory (#33) — all three at `a3b29b7`, the last two measured
  discriminating; five runner-side review minors (#26, `ae58c54`); the fifth
  override named (#35, `eba4db1`); and the grain reader's `RAISED_INV` regex
  BUILT from the line the tool prints (`aefb7ca`).
- **Eight printed sentences, each through the corpus gate WITH the driver**
  (ruling R6): the session clause reaching the withheld pair's own record and
  `is_relocation_note` → `is_env_rule_note` (#6/#7, `fc72550`); `focus: -` for
  an absent key against `focus: none` for a recorded empty one (#14,
  `36a6f5f`); the printed `HONESTY.md` citation (#18), the born-outside claim
  qualified (#28), the invocation header's noun — `N swallowed shape(s)`,
  which is what N counts (#30) — and the panics line's unit (#31), at
  `edc2bce` with `6490a14`; a typed lookup failure — `cli.py:91` stamps
  `type(e).__name__`, so the invocation log's `error` value for a prefix
  miss now reads `NoSuchTrace` where it read `TraceLookupError`, the class
  actually raised, and no reader keys on it — a language-free `diff --task`
  help line, the `or "?"` fixture and "modulo location" on the
  all-in-tasks branch (#27/#36/#37/#51, `0d685ad`); and a MATCH that says it
  is not a statement about the schedule (#20, `13475a2` with `245dee4`).
- **The corpus and the driver seam**: one driver resolution under
  `src/sensorium/`, the `run:` line keyed and pinned, and `corpus/rust/abort`
  cleaning its core file (#19/#21/#43/#45, `a9a5ed1`); the spawned-test-fn
  case recording deterministically and pinning its marked ROOT (#10,
  `7d9dc9c`). 63 cases, 141 questions, none skipped.
- **The crate-side rows**: `expr_attrs`' loud fallthrough for a `syn` variant
  it does not enumerate (#16, `bb0bb29`, with the known-surviving mutant
  documented at `30fcb39`); five private intra-doc links, so
  `RUSTDOCFLAGS="-D warnings" cargo doc` passes (#24, `059ac7b`);
  malformed-metadata fixtures (#38, `d836a77`); a `mint()` test that reddens
  and one run-id mix for both minters (#39/#42, `74d5fbb`); the panic path
  pinned by wire number and the orphan panic's serial (#40/#41, `852a0f5`);
  the WARN that counts test binaries apart from doctest processes (#46,
  `9c82fde`); `convert_perf` named for the bound it asserts (#47, `6abcc27`);
  goldens for fns nested in const, static and trait-const initialisers
  (#50/#52, `d17eb20`); the refused crate root on the wrapper-binary path
  (#53, `017a4a1`); self-removing scratch directories (#54, `1530f68`); and
  the tid-mask justification written into the suite (#44 nit 2, `91f737d`).
- **The ledgers themselves** (`b498caa`). Every row struck where it was
  raised, across this file's live volume and three archives, with the rung-3
  inbox — a spec — taking appended dated lines instead of strikes. Five **D**
  rows closed by dated note (#62–#66, ruling R8), including the measured cost
  of #66: re-rendering the two committed grain `results.json` today differs
  from their published §2 in exactly three lines, two of which remove a
  falsehood the records struck by hand in prose. Seven **X** rows struck for
  work that shipped in earlier slices and was never marked (#67–#73). Two
  blind spots declared — `rust/HONESTY-BLIND-SPOTS.md` items **30** (design
  R16 (v), the ledger half of #28) and **31** (a spawn in an expression
  position the container visitors skip, #49's A half). The stale
  `rust/target/release/cargo-sensorium` deleted from the root disk (#15,
  ruling R7). The rung-4-entry grain design's §5 example, which still spelled
  a continuation note ruling R-G7 had replaced, corrected beside itself with a
  dated amendment (#34). Slice 3's section moved to a third archive volume,
  measured before the ceiling was met rather than after.
- **What was declined, and why** (all in `docs/CARRIED-DEBT.md`'s new
  section): the six converter functions of 88–274 lines are **C, not A**
  (ruling R4 — behaviour-risk work with no failing test behind it); and of
  #26, #35 and #44 the parts that stand are named individually. Rows #11,
  #23 and #29 were declined for wanting one task holding two file scopes at
  once, and the final fix wave — one task, both scopes — took all three:
  the re-export idiom's file counts dropped everywhere they were spelled,
  three `chain.terminal` conformance vectors (`v20`–`v22`, for `panicked`,
  `left_thread` and `handled_then_failed`), and the §11 sweep finished.
  The **C** list — the inventory's 43, plus **C117**, which the final fix
  wave's review added rather than ruled on — is restated in one line each so
  it can be read without opening four volumes.

**Earlier entries** — `0.8.6` and `0.8.5`, and `0.8.4`, `0.8.3`, `0.8.2`,
`0.8.1`, `0.8.0`, `0.7.0` and `0.6.0` before them — are in
[`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md): `0.7.0`/`0.6.0` moved there
2026-09-08, `0.8.2`/`0.8.1`/`0.8.0` 2026-09-09, `0.8.4`/`0.8.3` 2026-09-10 and
`0.8.6`/`0.8.5` 2026-09-11, every time so this file stays under the repo-wide
800-line ceiling `tests/test_ceiling.py` holds it to. A count of moved entries
in this sentence goes stale at the next cut, which is why it names them rather
than counting them. Pure moves: same wording, same order, same dates.
