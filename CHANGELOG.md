# Changelog

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

## 0.8.6 — 2026-09-08

Rung 4, slice 4: **the recorder's footprint** — the three places this recorder
still showed up inside its own licence, removed, and the small debts slice 3
named with their fixes, paid. Python **0.8.6**; **`cargo-sensorium 0.5.2`**,
**`sensorium-transform 0.4.3`** for three pure splits (the goldens pin the
output byte for byte), **`sensorium-rt 0.4.0`** unchanged (neither the wire nor
the runtime moved). The driver's number carries no behaviour change, and that
is the point: E4″ identifies the driver that recorded a run by
`driver_version`, the token a trace carries, so a rebuilt tree needs a number
of its own. `TRACE_FORMAT` stays **4**: nothing here writes a new key into a
trace.

- **The recorder's own compiler flags are not a change the world made**
  (ruling R1). E4′ withheld the licence on all 61 pairs for one key:
  `RUSTDOCFLAGS` carries the driver's own `--extern sensorium_rt=…` and
  `-L dependency=…`, two tokens naming one directory under
  `<target>/sensorium/rt/<16 hex>/<unwind|abort>/`, whose hash moves with
  every driver build. `strip_recorder_fragment` removes
  every occurrence from BOTH sides before the compare; the remainder is
  compared exactly as it always was, and the backreference is the rule — two
  tokens that do not name one directory are not a shape this recorder writes
  and are left for the world's compare. A variable this tool compared less of
  is never silent: `; the recorder's own fragment stripped before comparing:
  RUSTDOCFLAGS` rides on the line and in the fact. Python traces cannot carry
  the fragment and their lines are byte for byte what they were.
- **Session set 1** (ruling R4, amended by A-§3 before any code). A re-run
  launched from another shell met a licence it could not earn: the handles a
  shell, terminal or agent session hands a process differ, and none of them is
  input to what a program computes. Fourteen exact names and one prefix,
  **positive and versioned**, are now named and never withhold —
  `env: unchanged outside session set 1 (<N> variables compared; …; <K>
  session variable(s) differ: <names>)` — while every other differing key
  withholds exactly as before. Not a *bearing* set: a list of the variables
  that "bear" on a program is a guess dressed as a rule, and the suite already
  held its falsifier in a test that records under `REFOCUS_TEST_LIMIT` and
  re-runs without it.
- **The harness rule anchors on the FIRST root, and never on a spawned
  thread** (ruling R3, `rust/HONESTY-BLIND-SPOTS.md` item 28). `#[test] fn` is
  an ordinary fn to rustc, so `thread::spawn(|| a_test_fn())` put a marked
  root on a thread the PROGRAM started, that thread was subtracted as the
  recorder's own, and the licence was granted over a thread nothing had
  compared — the direction that claims more. A spawn-named task
  (`spawn@<qualname>#<k>`) is now never the harness's whatever its root's
  mark, only the first root counts, and an `async` test fn carries no mark so
  its thread stays counted. `corpus/rust/refocus_spawned_test_fn` records the
  shape through the real driver.
- **Six files split before this slice edited any of them** (ruling R5).
  `docs/CARRIED-DEBT.md` → a second archive volume (archives are numbered
  volumes ≤ 800 lines); `rust/HONESTY.md` §13 → `rust/HONESTY-REFOCUS.md`;
  `refocus_cmd.py` → `refocus_report.py`; `visit.rs` → `visit/walk.rs`;
  `splice.rs` → `assemble.rs`; `lines.rs` → `lines/facts.rs`. Every one a pure
  move, tests and goldens green either side.
- **The recorder's tests leave no footprint either** (ruling R6). The three
  `driver_smoke.rs` tests that ran the whole driver named no store, so each
  run converted a trace into `~/.sensorium` — the store of whoever ran the
  suite. They name a scratch store now, and a new test pins the rule they
  rely on: with `SENSORIUM_DIR` set, `HOME` is not consulted at all.
  `corpus/run_corpus.py` gains **`--require-driver`**, which turns a skipped
  case into exit 1 and says so on the summary line and in `--json`; CI's rust
  corpus step passes it, because that job builds a driver precisely so those
  cases run and a green summary over cases nobody recorded is the dishonesty
  this harness exists to refuse. `tests/test_release_tokens.py` pins the three
  places this package's version lands — `pyproject`, the installed
  distribution's metadata, and this file's newest header — in both of the
  states that header legally has.
- **E4″ measured once, 2026-09-08 — H1–H7 PASS, H8 STOP on an instrument
  cell.** Pre-registered and §1 byte-locked before the instrument existed, then
  read once over the 61 kept originals of E4 under this slice's driver. The two
  questions the slice asked are answered **PASS at n = 61**: the harness-thread
  rule moved the licence word exactly as §1.2 predicted — **57 granted**,
  WITHHELD on the four thread-spawning tests with their program-thread counts
  **1 / 4 / 4 / 4** (E4′ read **0** granted, all 61 withheld by the confound R1
  removes) — and the recorder's fragment is gone from the compare:
  `RUSTDOCFLAGS` in **0 of 61** changed lists, the strip clause naming it on
  **61 of 61**, with the rt hash **differing on 61 of 61** pairs, so the strip
  was tested on every one under a driver build different from the originals'
  (`0.5.2` here, read from each re-run trace's own `meta.driver_version`; the
  kept store's `0.5.0` is **E4's** own §2 fact about those originals, carried
  into this record's §1.1 pre-registration — no field of E4″ reads it, and
  E4′ §2's `0.5.1` was the driver of E4′'s own re-runs).
  The verdict, the pair, session set 1 and both control
  arms held (H3–H6), and the instrument's own honesty row passed over all 69
  pairs (H7). **H8 STOPPED on this record's own reader**, not on the workspace:
  its three commands were green (corpus rc 0 over 63 cases with
  `--require-driver`, pytest rc 0, `cargo test --workspace` rc 0) and
  `corpus/rust/refocus_spawned_test_fn` did run, but the cell asking whether the
  case is present compared the bare name against a listing that spells Rust
  cases `rust/<name>` and so read a measured-looking `False`. The STOP stands as
  measured — kill 6 forbids an instrument change after the measurement — and the
  one-line fix is ruled for the next slice.

## 0.8.5 — 2026-09-07

Rung 4, slice 3: **the rung-4 debts** — the seven items slices 1 and 2 left in
`docs/CARRIED-DEBT.md` with their fixes spelled out, closed. Python **0.8.5**;
**`cargo-sensorium 0.5.1`** for the hard-linked shim and the `driver.rs` split,
**`sensorium-transform 0.4.2`** for a focus resolution that no longer splices,
**`sensorium-rt 0.4.0`** unchanged (neither the wire nor the runtime moved).
`TRACE_FORMAT` stays **4**: nothing here writes a new key into a trace but
`refocus_children`, which is optional meta.

- **The licence knows the recorder's own thread from the program's** (ruling
  R1). `cargo test` runs every `#[test]` function on a thread libtest spawns
  for it, so the untraced-thread caveat fired on all 61 pairs of E4 for that
  reason and no other — a clause that cannot not fire is not a finding. A
  non-main thread whose ROOT frame's site the manifest marks `#[test]` is now
  a **harness thread**, subtracted from the licence's untraced-thread counts
  and **named wherever one of those counts is printed**: `and 1 harness thread
  (libtest's per-test thread, excluded as the recorder's own)` where the clause
  joins a count, `; 1 harness thread (…) is not among these counts` on the
  `threads:` line, which counts what WAS compared. The root anchors it, which
  is a **bound** and not soundness in both directions — a mark below the root
  excludes nothing, but a thread the PROGRAM spawns whose first instrumented
  frame is itself a `#[test]`/`#[bench]` fn is read as harness and the licence
  can be **granted** over it, while an `async` test fn carries no mark so its
  harness thread stays counted (found by review 2026-09-07, not measured;
  `rust/HONESTY-BLIND-SPOTS.md` item 28) — and the set is empty on any trace
  with no site marks
  (every **Python** trace, byte-identical output) and empty unless the main
  thread is a RECORDED fact.
- **A child run is not the pair** (ruling R2). A re-run whose test spawns an
  instrumented program writes a second trace carrying `refocus_of`, and the
  pair lookup counted it: `refocus` refused "more than one" and advised a
  single-target selector at a caller whose selector was already single. A
  linked trace whose `ppid` is **another** linked trace's `pid` is now excluded
  from the pair, named on the pair line as `child runs excluded from the pair:
  <ids>`, stamped into the pair's trace as `refocus_children`, and still listed
  by `runs`. The >1-candidate refusal carries the same clause in the same
  words. `corpus/rust/refocus_child_run` records the shape through the real
  driver.
- **A target directory that MOVED is read as a relocation, not as a change the
  world made.** A refocus re-runs under whatever `CARGO_TARGET_DIR` the caller
  has, and cargo derives `CARGO_BIN_EXE_*`, `LD_LIBRARY_PATH` and
  `RUSTDOCFLAGS` from the root, so a re-run from a fresh target differed on all
  four and withheld the licence for it. Nothing is excluded **by name** — that
  would let a
  program really handed one extra directory on the loader's path earn a full
  licence. Each DIFFERING key is asked whether its difference disappears when
  the original's root is substituted for the re-run's, entry by entry down a
  `PATH`-like list and anchored at path boundaries on both sides; a key the
  rule explains is named (`N variable(s) differ only by the target directory:
  …; treated as unchanged`) on the env line and kept in the trace even where
  the licence is withheld for another reason. Anything else still withholds.
- **`info` says which checks could not run at all**, instead of printing the
  `licence verified:` lines alone and leaving a reader to infer that every
  other check ran and failed: `licence unverifiable: output (not recorded),
  children (not witnessed)`, and nothing where the stamp is absent. Its
  `threads started:` line takes the same harness partition as the licence, on
  the same screen.
- **A Rust screen says what its streams are in Rust's words.** The
  `threads:` line's scope parenthetical reads `(events outside any test or
  spawned thread)`: this converter writes one thread row — the main thread's —
  and routes every other thread's events into `task_fingerprints`, so `asyncio`
  there named a runtime that never ran.
- **The wrapper shim is a hard link, not a ~40 MB copy per focus** (ruling R3,
  `cargo-sensorium` **0.5.1**). E4 counted 62 shim entries under one target
  directory totalling 2 506 729 440 bytes, all of them the same binary.
  `install_shim` now links, falling back to a copy on any error — a
  `CARGO_TARGET_DIR` on another mount included — and names both failures when
  both fail. Sharing the driver's inode is safe because the key already hashes
  the driver's own bytes. Two guards ride with it: the leftover temporary is
  **unlinked first**, because a `tmp` left by a run that died between install
  and rename may itself be a link to the driver and `fs::copy` onto it would
  truncate the driver; and `set_permissions` runs on the **copy path only**, so
  nothing here ever writes the driver's inode. `du` over the shim tree now
  counts those bytes once, however many keys are present.
- **`fn_items` enumerates through the census path** (ruling R7,
  `sensorium-transform` **0.4.2**). Resolving `--focus` ran the whole splicing
  transform on every `.rs` file of the workspace — every offset computed, every
  fragment placed, every rewritten source assembled — and threw the string away
  to read two lists off it. It now runs the walk alone, under a named
  `census::Mode` (`Emitting` / `Census` / `Counting`) so the fourth combination
  of the two `bool`s it replaced is unspellable. One answer MOVED, deliberately:
  a file whose walk is clean but whose splicing half would fail answered `[]`
  under 0.4.1 and answers with its full row list now, so a `--focus` naming a
  function that is plainly in the file is no longer refused before cargo runs
  because some other file could not be spliced.
- **`driver.rs` splits** (ruling R7): the invocation record to `invocation.rs`,
  the cargo child's environment and launch to `launch.rs`. Behaviour-preserving
  moves; the cargo child's variables, values and order are unchanged (a 14-line
  `Ground` construction was added in `driver.rs`) and `driver_smoke.rs` is
  green.
- **Every raw and assembled acceptance results file carries `schema_version`**
  (ruling R4): `"e9/1"`, `"e4/1"`, `"e4p/1"`, with the renderer stating once
  when the assembled schema is later than the raw's. The E9 and E4
  `results.json` committed with their records are NOT re-derived — a derivation
  is stated, not rewritten — and `docs/CARRIED-DEBT.md` notes that those two
  files predate the field.
- **E4′ was measured once and STOPPED on H1**
  (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md`): the
  licence was granted on **0** of 61 pairs where §1.2 predicted 57 — not
  because R1 failed, since the harness exclusion fired and was **named on 61
  of 61** `threads:` lines and the four pairs §1.2 named report the
  program's own counts 1, 4, 4, 4 — but because the env clause withheld on a
  single key, `RUSTDOCFLAGS`, whose driver-injected `--extern
  sensorium_rt=<target>/sensorium/rt/<hash>/…` fragment carries a hash that
  moved with the driver build (0.5.0 recorded the originals, 0.5.1 re-ran
  them), so the clause read the recorder's own footprint as a change the
  world made; H2–H6 passed as pre-registered (MATCH 61 of 61, one pair on
  every pair, the shim at the driver's own single inode on all 61,
  `schema_version` present, and corpus, Python suite and `cargo test
  --workspace` green). The STOP stands: it is not re-rolled, no `src` change
  was made after it, and the ruled fix — strip that fragment as the
  recorder's own, then **E4″** over a subject with an original recorded under
  a different driver build — is carried in `docs/CARRIED-DEBT.md`.
- **Not funded** (ruling R6, until a use asks): `--window` on a Rust trace,
  refocus over a multi-process invocation, an inference-variable opt-out, and a
  per-site volume cap. The declared blind spots stand.

**Earlier entries** — `0.8.4` and `0.8.3`, and `0.8.2`, `0.8.1`, `0.8.0`,
`0.7.0` and `0.6.0` before them — are in
[`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md): `0.7.0`/`0.6.0` moved there
2026-09-08, `0.8.2`/`0.8.1`/`0.8.0` 2026-09-09 and `0.8.4`/`0.8.3`
2026-09-10, every
time so this file stays under the repo-wide 800-line ceiling
`tests/test_ceiling.py` holds it to. A count of moved entries in this sentence
goes stale at the next cut, which is why it names them rather than counting
them. Pure moves: same wording, same order, same dates.
