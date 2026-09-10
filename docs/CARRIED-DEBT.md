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

## 2026-09-10 — S5 slice 2 (Python 0.9.1 / sensorium-ts 0.1.1)

The slice that answers the two things rung 1 shipped open — E6′'s STOPped
timing clause and E10's design input — and fixes what the `node --test` path
was getting wrong. Ten plan decisions (P1–P10), and — read off the slice's
SDD ledger rather than counted by hand — **eleven** distinct controller
rulings, two of them stated twice (once in a task's risk table and again in
its bullet), one clause each:

1. the equivalence gate's side B stays the tip after Task 3; Task 5's R45
   edit touches only the zero-spool refusal and is not re-gated;
2. the global `sensorium` tool is not reinstalled from the worktree until
   Task 4's side A has converted, so Arm 0 and side A are not the new code;
3. `ingested.json` is dropped from all three spool copies (the marker makes
   `ingest` refuse and carries no measured data);
4. the timed region keeps `rss_run.py`'s ~16 ms start-up in **every** stage,
   so the bound stands as written and no threshold moves;
5. the 4.0 load guard admits repetitions on a jobs-16 cell's own decaying
   load — the pre-registered guard stands and the readings are in the JSON;
6. Task 3 absorbs two record minors and builds `TraceWriter.discard()`
   (rollback then close) behind `Builder.abort()`;
7. the streaming reader's UTF-8 refusal names the **line**, where the old
   reader named the file;
8. `sensorium diff` MATCH compares causal structure and row counts and not
   recorded values — so E10′-eq stands on its own pre-registered rule, and a
   NEW ungated check, E10′-eq-content, is pre-registered before it runs;
9. Task 7 adds `tests/test_ts_ingest_refusals.py` to CI's `typescript` job
   file list, for symmetry with the matrix jobs' bare `pytest -q`;
10. Task 6 re-runs `npm run probe:nodetest` once to capture `h-probes.json`
    for the assembler, the H-probes verdict staying Task 5's;
11. Task 7 absorbs three of Task 6's minors as edits and writes the rest
    into the record's §5 and this ledger.

Every one that moved the design's text is a dated row in §12 of
`docs/superpowers/specs/2026-09-10-sensorium-s5-slice2-design.md`, and the
`Ruling:` lines themselves are in
`.superpowers/sdd/2026-09-10-sensorium-s5-slice2/progress.md`. *(The count
read "Seven" until the final fix wave; this section's own process lesson is
that a summary count goes stale, so it is derived here and the list is what
a reader checks.)* Every
number below is copied from
`docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md`, whose §1 was
byte-locked before any of this code existed.

**Measured before it was written, the way the rule asks.** This section was
drafted at **250** lines against a live file of **452** — 415 at the
slice's start, plus **37** the strikes above added — which took it to
**703**, under the 800-line ceiling. Nothing was cut, and no volume
was opened. *(Re-measured 2026-09-10 after the task's review: the fix wave
added **19** lines here, so the section is **269** and the file **722**. A
line count stated in a paragraph goes stale the next time the paragraph's own
section is edited — this file's header has recorded that happening to three
volume counts — so the number is re-taken rather than left standing, and both
readings are kept. Re-measured a third time the same day, after the FINAL
review's fix wave struck the ` > ` row, enumerated the rulings above and
amended the version-token row: the section is **313** and the file **774**,
this sentence's own four lines included — writing the count moved the count,
which is the lesson in one line. Still under the 800-line ceiling.)*

### Settled

- **E6″ — PASS on all five clauses.** One guarded session on the lens (five
  plain runs, one call-tier recording, five plain runs, the manifest last):
  manifest **748 OK / 0 FAILED** before and after, ten of ten plain runs at
  `372 passed (372)` / `4278 passed (4278)` and **nothing dropped**, **0**
  `__srt` markers over the 2 cache directories that exist,
  `node_modules/.sensorium` **absent**, and the after arm's median
  **22.1136 s** inside the band **[21.9834, 22.3652]** — the before arm's own
  median **22.1743** ± its own range **0.1909**. The after arm is **0.0607 s
  faster** than the before arm. E6 is closed for this recorder on this lens,
  and the rung-1 spec's §11 carries the dated line saying so.
- **E10′ — PASS on all three gated clauses; the converter stays Python.**
  **E10′-suite 16.3859 s** (n=5) against the pinned **22.5925 s** wall,
  **E10′-file 0.1648 s** (n=5) against **0.4002 s**, and **E10′-eq 372 MATCH
  / 0 DIVERGED / 0 REFUSED** over the same set converted twice. Two levers,
  each its own commit with its cells measured before the next was written:
  `TraceWriter(durable=False)` (one transaction per trace,
  `synchronous=NORMAL`, committed in `close()`) and a **streaming spool
  reader** (BOOT from line 1, every later record yielded, `TraceWriter.
  discard()` behind `Builder.abort()`). End to end **2.7913×** on the suite
  and **2.1990×** on the one file, with the heaviest worker's peak resident
  down **2,269,696 → 290,948 kB** on the suite cell.
- **And the trace did not move.** Beside the gate, ungated and
  pre-registered *after* the gate was read so it could not touch its verdict:
  **E10′-eq-content**, every row of `events`, `frames`, `code_objects`,
  `tasks`, `fingerprints`, `task_fingerprints` and `output` compared column
  for column across all 372 pairs — **372 / 372 identical**, the only `meta`
  key differing on any pair being the minted `run_id`. The instrument was
  mutation-checked before it ran: a changed column, a deleted row and a
  changed `meta` value were each caught and named.
- **H1 — the loader hook returns Node's own format and erases nothing**
  (`05e5338`). It classified by extension and forced `format: 'module'`; it
  now asks `nextLoad` and takes the answer, so **Node** strips and the
  recorder splices. The `.mts` that was instrumented and never stripped now
  records.
- **H2 — one probe per extension, two controls, under `node --test`**
  (`761c935`). `.ts`, `.mts`, `.mjs`, `.cjs` and the controls `enum.ts` and
  `jsx.tsx`: `check.mjs nodetest` reads **25 checks, 0 failures**, and both
  controls fail **identically** hooked and plain
  (`ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`, `ERR_UNKNOWN_FILE_EXTENSION`,
  `same: true` twice). The controls discriminate, measured: against the
  pre-fix hook `enum.ts` **loaded** under the recorder and failed plain.
- **H3 / R45 — a run that recorded nothing says why when the tallies know**
  (`5af2def`). Where every tally reads `files_transformed: 0` and the
  exclusions are non-empty, the refusal names them by reason with counts
  (`commonjs x2, parse-error x1`), the ES-modules-only clause appended only
  when `commonjs` is among them (plan P6, R27's precedent). A partial suite
  keeps the old sentence: a real recording failure is not an exclusion.
- **H4 / R47 — `hook.mjs:98` became `hook.mjs` `load`** (`90d6380`). A line
  number in a ledger is a citation that goes stale on the next edit; H1 moved
  those lines in this same slice. No `hook.mjs:<line>` citation remains in
  any document this slice can edit.
- **The `loads` fix** (`ecdc631`, spec §2.3). `assemble.py`'s `arm_stats`
  zipped the arm's `loads` against its **kept** walls while `loads` held a
  row per attempt, so a dropped run would have misaligned every later
  reading. Rung 1 dropped no run, which is why the misalignment stayed
  latent; it is filtered now, before `e6pp` used the assembler.
- **The R45 sentence's ordering, and the refusal tests.** Reasons are
  rendered `sorted()` so the sentence is stable across dictionary order, and
  `tests/test_ts_ingest_refusals.py` is now named in CI's `typescript` job
  file list beside the rest of the recorder suite (the matrix jobs' bare
  `pytest -q` already ran it; the list is for symmetry).

### Deferred, with rulings

Each row is a decision that was made rather than a thing forgotten, with the
number or the ruling that made it and what it costs if it was wrong.

- **A2, largest-first dispatch — not built.** Spec §3.3 conditioned it on
  A1 + A3 leaving the suite cell above the bound; a3's 0d read **16.5088 s**,
  **6.0837 s** below the 22.5925 s bound. *Cost if wrong:* a converter faster
  than the verdict needed is not built, and the numbers say exactly how much
  headroom was left.
- **A4, the per-record Python cost — not built**, on the same condition and
  the same number. *Cost if wrong:* the same, plus the attribution question
  A3 raised (which share of its 1.25 s is decode, allocator or collector)
  stays unanswered.
- **Arm B — a Node or Rust converter — never built** (*Brice's ruling
  2026-09-10, spec §10.1*): Arm B stops at the report, a Node converter is a
  later slice. The suite clause PASSed, so nothing asked for it. *Cost if
  wrong:* none this slice can see; the ladder's rungs are on record for
  whoever raises it.
- **The non-durable writer's transient WAL is unmeasured at the job count
  the gate ran.** Measured once at `--jobs 1`: a **335,895,392-byte** `-wal`
  beside a **333,832,192-byte** database, so transient disk is ≈ **2×** per
  in-flight trace, and at the default job count it is the sum over the
  workers building at that moment. 63 GB were free and nothing came near the
  disk. *Cost if wrong:* this box has run at ~3 GB free on `/`, and a
  full-suite conversion there could fail on space in a way no cell here
  would predict.
- **`Builder`'s class docstring does not say the build is non-durable by
  default** (T2 M3). One sentence. *Cost if wrong:* a reader of the class
  learns the default from the constructor signature instead.
- **A `Spool` that is never iterated leaves its handle to the collector**
  (T3 M3) — a `ResourceWarning` under `-W error`, not a leak in any shipped
  path. *Cost if wrong:* a future caller that constructs and abandons spools
  in a loop holds file descriptors longer than it should.
- **`torn_tail` still has no production consumer** (T3 M7, pre-existing).
  The streaming reader fills it as it walks; nothing reads it. *Cost if
  wrong:* a truncated spool converts with the fact recorded and unreported.
- **`sensorium diff` exit 0 counts its leniencies as MATCH** (T4 M5):
  "MATCH modulo location" and "nothing to compare" are not separated from a
  plain MATCH by the gate's instrument. Closed in practice by
  E10′-eq-content's 372/372 — the rows are identical, so no pair could have
  been leniently matched — but the instrument still cannot tell them apart.
  *Cost if wrong:* a future gate on a set where the leniencies fire reads
  MATCH for something weaker.
- **`probes/check.mjs` collapses duplicate probe names and pins no spool
  count** (T5 M3). It asserted 3 spools here because the run produced 3.
  *Cost if wrong:* a probe file that silently stopped producing a spool could
  be masked by another with the same name.
- **No test discriminates the `sorted()` in R45's reason rendering** (T5 M2):
  a mutant that drops it survives on any single-reason fixture. *Cost if
  wrong:* the sentence's ordering becomes dictionary order and the refusal
  text varies run to run.
- **`e10p.sh` records a peak RSS of `0` silently** if the `maxrss_kb=` line
  fails to parse (`${maxrss:-0}`, T1 M3). Every repetition of every cell
  parsed, and each report says so. *Cost if wrong:* a future rung reads a
  zero as a measurement.
- **A dropped plain run STOPs E6″'s suite clause outright** (T6 M2), so the
  "fewer than four usable walls" STOP-by-instrument is nearly unreachable —
  the conjunction fails first. It is the conservative direction (an
  instrument that cannot manufacture a PASS), and it was not disclosed in the
  pre-registration. *Cost if wrong:* a future session reading the rule
  expects a graceful degradation it will not get.
- **The five E6″ clauses cannot see a failed call run** (T6 M3). The call run
  is the contamination *source* and deliberately outside the clause (record
  §5 gap 10); its greenness was checked by hand — call row ok, exit 0, 372
  spools. *Cost if wrong:* a session whose recording half-failed reads as a
  clean PASS unless someone looks.
- **The manifest's sha256 is recorded, not enforced** (T6 M4). `e6pp.sh`
  derives the expected OK count from the manifest's own `wc -l`, so it writes
  the manifest's sha into the cell to anchor *which* 748 — but nothing
  compares that sha to the pinned value automatically. *Cost if wrong:* a
  truncated or swapped manifest passes the count clause and the mismatch is
  visible only to a reader who checks the sha by eye.
- **`assemble_slice2` can emit `null` with an empty `dropped`** on two
  branches (T6 M5), where the file's own rule is that a missing cell is
  `null` **plus** a reason. *Cost if wrong:* a cell reads as absent with
  nothing saying why.
- **The band's width is a property of the session, not of the rule** (record
  §5 gap 8): ±0.1909 s here against the ±0.4085 s spec §2.2's worked example
  derives from E1′. A PASS here is a claim against a tighter yardstick, not a
  tighter claim, and sensitivity is not comparable across sessions. A session
  wanting stable sensitivity would pre-register a floor on the band's width —
  which §2.2 deliberately refused, a chosen width being the thing it refused.
  *Cost if wrong:* a later E6 whose control arm is noisier passes a clause this
  one would have failed, and the two PASSes get read as the same claim.
- **"Under 4.0" is not "idle"** (record §5 gap 9). Ten of the eleven guarded
  readings were above 3.0 and only the before arm's first run was cold
  (0.35). The asymmetry runs **against** a contamination finding — the arm on
  the quieter box is the slower one — but a guard that wanted the arms
  ambient-matched would wait for a *return* to a baseline, not for a ceiling.
  *Cost if wrong:* on a session where the asymmetry ran the other way, ambient
  load and not the recording would be the thing the band measured.
- **The instrument's timed region includes its own wrapper's start-up**
  (record §5 gap 1), now **8.3%** of the gated one-file cell (0.0137 s of
  0.1648 s). Both walls fall the same side of both bounds, so no verdict
  turns on it. *Cost if wrong:* a bound within 10% of the truth would be
  decided by an interpreter start-up; a later instrument should time the
  child alone or say which wall the rule reads.
- **The record's `### 3.6`–`### 3.11` shadow the spec's own §3.6/§3.7
  numbering** (T3 M4). Every citation that could be ambiguous is qualified
  "spec §3.x" in place; the headings themselves were not renumbered because
  §1 quotes the spec's and §1 is byte-locked. *Cost if wrong:* a reader
  follows "§3.7" to the wrong document.
- **Job-count independence of the converter's output is an inference, not a
  measurement** (T4 M8). Both sides of the equivalence gate ran at the
  default job count, so the 372 MATCH says nothing about whether `--jobs 1`
  and `--jobs 16` write the same trace. Nothing in the converter is
  job-count-dependent by construction. *Cost if wrong:* a dispatch change
  (A2, if it is ever built) could move output without this gate noticing.
- **Rung 1's results file was written by an assembler that no longer
  exists** (record §5 gap 11). The `loads` fix landed after that file was
  produced and it was **not** regenerated: nothing in it moves (rung 1
  dropped no run), and re-running it today would change a locked record's
  evidence rather than reproduce it. *Cost if wrong:* none measured; the
  provenance is the point and it is written down.
- **`assemble.py`'s `load()` leaks a filesystem path into an absent-file
  reason**, where every other field is redacted. No absent cell occurred, so
  no path shipped. *Cost if wrong:* one box path in a committed results file
  — which is exactly what `offenders()` exists to refuse.
- ~~**`docs/TRACE-FORMAT.md`'s `capabilities.err_flow` sentence still names
  `sensorium-ts 0.1.0`**, and so does
  `corpus/typescript/exceptions_refused/questions.yaml:12` ("no TypeScript
  disposition rules exist in 0.1.0", in the case's `truth` prose) — **two**
  version tokens this slice left standing, not one. *(Amended 2026-09-10 in
  the final fix wave: this row claimed to be the only one.)* Both are true
  of 0.1.0 and still true of 0.1.1 — the same rung still owes the
  disposition rules, and `capabilities.err_flow` is false in both — and the
  corpus file is left alone because no test reads that prose, and
  `docs/TRACE-FORMAT.md` sits at **799** of 800 lines, which this slice
  pre-committed not to open (plan Global Constraints). *Cost if wrong:* a
  reader on 0.1.1 goes looking for a version statement that has not moved
  because it did not need to. The four others the first pass missed were
  taken 2026-09-10 rather than deferred, so this row — in its two places —
  is the whole of the deferral: `typescript/README.md`'s
  "Arguments are unread" and `typescript/HONESTY.md`'s `capabilities.err_flow`
  sentence are now **version-free** ("in this version"), because both describe
  the package as it is rather than a recording; and `typescript/README.md`'s
  "Not yet" clause and `typescript/HONESTY.md`'s "a trace this 0.1.0 runtime
  wrote" **keep `0.1.0` and name `0.1.1` beside it**, because both are about
  traces a 0.1.0 runtime actually wrote and both versions declare the same
  capability.~~ — **Both closed 2026-09-10, S5 rung 2**, and neither by a
  version-token sweep: `docs/TRACE-FORMAT.md`'s sentence was rewritten when
  `err_flow` became a key **two** recorders declare (it names `sensorium-ts`
  ≥ 0.2.0 now), and the corpus case was renamed `silent_swallow` with its
  `truth` prose rewritten to the verdict it now gets. The deferral was right:
  both tokens were true when they were left, and the slice that made them
  false is the slice that fixed them.
- **`task_name_basis` is spelled `lexical` in prose and `title` on the wire**
  (record §5 gap 6). Same fact, two spellings; the checker asserts the value
  the recorder writes. *Cost if wrong:* a reader goes looking for a third
  basis.

The per-task minors this slice did not fund are in the slice's SDD ledger
(`.superpowers/sdd/2026-09-10-sensorium-s5-slice2/progress.md`, each task's
"Minors deferred" line), archived with the worktree.

### Process lessons

- **Two instrument defects were found only by running the instrument, and
  both were found before the number was.** The first H-probes run STOPped on
  `ext:cjs:tally` with two orphan tallies instead of one: `controls.mjs` had
  spawned its hooked side with `SENSORIUM_MANIFEST_DIR` inherited, so a
  control's child wrote a tally into the run's own manifest directory and
  read as a second child that recorded nothing. Nothing about the recorder
  was wrong; an instrument that shares a directory with the run it measures
  is. It was fixed, the run repeated from zero, and the first run's only
  reading is the defect. The second was caught by mutation: `e6pp_report.py`
  had a test that compared the after arm's **wall** where the rule compares
  its **median**, and a mutant that swapped them survived until the mutation
  round found it — fifteen mutations, one real gap. An instrument gets the
  same evidence standard as the thing it measures, or the measurement is
  worth what the instrument's tests are worth.
- **A prediction can fail in the fast direction, and that is still a
  falsification.** Six of the ten per-cell predictions this ladder
  pre-registered did not hold as written, and **five of the six were faster
  than predicted** — A1's "0e unchanged" by a factor of 2.2004, A3's "wall
  within noise" by about 1.25 s on each large cell. The temptation each time
  is to read a happy number as a held prediction; the discipline is that the
  prediction said something specific and the cell said something else, so the
  prediction is falsified and the record says which way. What the misses
  bought is the diagnosis they forced: the one-file spool was
  commit-*dominated*, and a memory lever moved the wall as well as the bytes.
- **Check that two numbers are the same kind of number before naming their
  difference a finding.** Rung 1's E10 reading and this slice's Arm 0 both
  measure "full-suite ingest", and neither is comparable to E6″'s call run
  (n=1, unguarded within itself, over a set nothing pinned) — the record says
  so in three places rather than letting a reader subtract them. The same
  care named the wrapper's start-up as part of the timed region *before* a
  gated clause stood on it, and named the band's width as a session property
  *before* the band was read.
- **Draft, measure, then cut.** The previous CHANGELOG cut was sized by
  guessing at the entry's length and the file landed at 833. This one drafted
  the `0.9.1` entry first (**105** lines against a live file of **756**,
  which would have taken it to **862**), and only then cut — two entries
  rather than one, with the arithmetic for both written into the archive's
  own note. The same order was used for this section.

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
  in the slice-2 section it belongs to, because that section is still live and
  a strike is where the reader meets the row.
- **The invocation refusal named one of the two languages it answers for.**
  `_member_refusal` said `exceptions` across an invocation "is defined for Rust
  traces" — true when written, false since Task 4. It now names Rust **and**
  TypeScript and says the member's language is not ruled. Its byte-pin is a
  **fenced Rust test**, and the sentence and the pin moved in one commit; that
  is the one sanctioned change to a fenced Rust test in this rung, and the
  commit body says so.
- **The grouper is one module with two renderers.** `exceptions_group` was
  Rust-only prose; it now takes a per-language `Renderer` and a `site()`
  callable, `group_chains` staying as a thin wrapper. Every Rust caller and
  every Rust test is byte-unchanged, which is the evidence rather than the
  claim.

### The four gaps this rung's measurement found (record §5)

Findings, not stops: none is an endpoint's rule and none moves a number.

- **Gap 1 — the shape key's id mask carries Rust's float-type exclusion onto
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
  a reader counts places from a shape count and is over by two in thirty.
- **Gap 2 — three reused instruments were measuring the wrong binary, and it
  took this rung to notice.** `arms.sh`, `e3.sh` and `e7.sh` hard-coded the
  global `sensorium`, which is an editable install of `main`; a rung that ships
  a new recorder would have reported main's numbers under its own name. Fixed
  before any of the three ran here (record §2.3), default unchanged so the
  earlier readings stay reproducible. **Closing it** means a shared rule that
  every acceptance instrument takes its binary from the branch under test, and
  a check that says which binary a cell used. *Cost if wrong:* a future slice
  reuses a fourth instrument with the same hard-coding.
- **Gap 3 — E7″'s needle list cannot be applied as written.** §1's list
  includes `Err`, `oid` and `chain`, and the inherited instrument matched
  needles as case-insensitive substrings: under that reading `Err` is matched
  by every `Error('…')` an answer prints, so the endpoint would STOP on any
  transcript naming an exception type and could not be passed by a correct
  recorder. The reading was fixed before the count was taken (record §2.3);
  slice 2 hit the same edge on `python ?` and this is the **second** time.
  **Closing it** means pre-registering a needle's MATCHING RULE beside the
  needle. *Cost if wrong:* a third slice writes a list of literals whose rule
  is discovered when the instrument runs.
- **Gap 4 — on real code the modal AMBIGUOUS reason is the rules' last one,
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
  half of a real lens's ambiguity stays unnamed.

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
  ruling), so `handledFinally` writes a complete `exc` and nothing `unread`
  beyond the two keys the block genuinely cannot know. *Cost if wrong:* one
  object per marked frame instead of a number.
- **E2″'s numerator comes from the transform's OWN OUTPUT** (T2 ruling):
  `census_catch.mjs` runs `transformSource` over each eligible file and counts
  the markers by `how` word; no manifest key was added. *Cost if wrong:* a
  census that reads text the transform wrote rather than a manifest it
  declared — the goldens hold the text's shape.
- **The assembler stamps `recorder_basis` on every cell** (T7 ruling), `own`
  on the two that record themselves. A re-assembly of saved cells is not a
  re-measurement, which is what slice 2's misattribution lesson asked for.

### Deferred minors, per task

Each is a review's `M`, deferred with its cost; the full text is in the SDD
ledger (`.superpowers/sdd/2026-09-10-sensorium-s5-rung2-throw-flow/progress.md`,
each task's "Minors deferred" line), archived with the worktree.

- **T0:** the record's report line counts went stale post-amendment (M2/M3);
  §1's preamble calls its wrapped plan-block heading "the only editorial act"
  (M6).
- **T2:** `console.log({ e })` — a shorthand inside a console argument — reads
  logged and is untested either way (M2); the climb-through inverts the
  module header's "errs toward escaped" promise (M3); `checkEscape`'s `got`
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

