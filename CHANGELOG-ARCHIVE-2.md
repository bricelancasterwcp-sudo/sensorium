# Changelog — the earlier entries, volume 2

`0.9.1` and `0.9.0`, **moved here 2026-09-12 (S5 rung 4's debts) so
[`CHANGELOG.md`](CHANGELOG.md) stays under 800 lines** — the fifth cut, and
the first that could not be taken into
[`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md). Volume 1 stood at **742**
lines when this cut was sized; these two entries are **271**, so appending them
there would have put the archive itself at 1,013 and broken the same ceiling
the cut exists to respect. `tests/test_ceiling.py` holds every tracked document
to 800 lines, an archive included — a file nobody edits any more is still a
file somebody reads.

So the archive becomes **numbered volumes, each kept under 800 lines, never
one growing file** — the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](docs/CARRIED-DEBT-ARCHIVE-2.md) set for the
debt ledger when the same thing happened to it, and which that ledger is now
eight volumes deep in. Volume 1 is closed: nothing is appended to it again.

**A volume's number is its cut order, not its age.** The two entries below are
NEWER than every entry in volume 1, which runs `0.8.6` down to `0.6.0`: a
volume is opened when the previous one fills, and what fills it is the size of
the entries that happened to be cut, not their dates. The version numbers are
the index that matters — `0.9.0` follows `0.8.7`, which is still in
`CHANGELOG.md`, and `0.9.1` follows `0.9.0`, wherever each file happens to sit.

`CHANGELOG.md` stood at **702** lines before the move and at **437** after it,
the 0.13.0 entry not yet written — 363 lines of room, where the largest entry
this project has ever shipped is 161 (`0.9.0`, below). The cut is taken before
the entry is drafted, which is what the second cut's confession in volume 1
asks for: size the cut against the room the next entry needs, never by eye.

**The wording, the order and the dates are unchanged**: the two entries below
are byte for byte the two that were removed from `CHANGELOG.md` — checked by
`diff` against the pre-cut file, empty — never rewritten, and a release that
happened stays a release that happened. `CHANGELOG.md` remains newest-first
and its newest header is still the released version's, the one thing
`tests/test_release_tokens.py` reads.

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
