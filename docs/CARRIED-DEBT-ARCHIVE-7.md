# CARRIED-DEBT — volume 7

The S5 slice-2 section — the E6″ ceiling exception and the E10′ converter
ladder — moved here **2026-09-11** (S5 rung 3, naming the ambiguity, in its
final review's fix wave) so [`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays
under 800 lines. It is the seventh numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file.

The move was measured before it was made, the way the ledger's own lesson
asks: the fix wave's four new debt rows were drafted at **40** lines against a
live file of **799**, which would have taken it to **839** — 39 over the
ceiling before this volume's own pointer paragraph was counted — so the oldest
section was cut rather than the ceiling discovered.

**The wording, the order and the strikes are unchanged**, with no exception:
nothing below was edited in the move, a resolved item is struck through here
exactly as it was in the live file, and nothing is deleted. The house rule
stated in `docs/CARRIED-DEBT.md`'s header governs every volume, and a deferred
item below is still open unless it is struck.

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
