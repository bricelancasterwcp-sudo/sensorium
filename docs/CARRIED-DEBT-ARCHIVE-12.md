# CARRIED-DEBT — volume 12

The 2026-09-13 section — S5, refocus for TypeScript — moved here
**2026-09-14** (secrets redaction, PR B, in its ledger task) so
[`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays under 800 lines. It is the
twelfth numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file.

The move was measured before it was made, the way the ledger's own lesson
asks: PR B's section was drafted at **414** lines against a live file of
**722**, which would have taken it to **1,136** — three hundred and
thirty-six over the ceiling. One section had to go whichever way the
arithmetic fell, and no other cut would have been enough on its own: the
moved section is **352** lines, and the live file is **795** after both the
cut and the append.
Content was not trimmed to fit; the oldest section was cut, which is the rule.

**The wording, the order and the strikes are unchanged** — nothing was edited
BY the move, a resolved item is struck through here exactly as it was in the
live file, and nothing is deleted. PR B made no strike inside this section:
nothing it carried was closed by the value half, so every deferred item below
travels open. The house rule stated in `docs/CARRIED-DEBT.md`'s header governs
every volume, and a deferred item below is still open unless it is struck.

## 2026-09-13 — S5, refocus for TypeScript (Python 0.14.0 / sensorium-ts 0.4.0)

The slice that gives `refocus` its third language. A vitest invocation is a
POOL, so the whole recorded invocation is re-run as typed and the reader is
told which of the traces that came back is the PAIR and what is being claimed
about the rest. Ten plan decisions (**A1–A10**) and twenty-three controller
rulings (**P0–P22**); every one that changed a sentence of the design is in
its §9, and the ones that changed none are listed there too rather than left
to be noticed. **The slice ships `DONE-WITH-STOP`** — twelve E15 cells read
once each, nine PASS, one *reported*, three STOP. Two of the three STOPs are
this record's own pre-registration, pinned by a dated §1 amendment with
corrected clauses beside them **before the instrument was launched once**; the
third is the survey's premise about which functions bear captures at the
`call` tier. None of the three is about the tool, and the record says so
(`docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md`
§3–§5).

### Settled — closed here

- **`refocus` is no longer TypeScript's "not yet".** Rung 4 named it the
  non-goal ("next slice, on these rows"); `typescript/README.md`'s *Not yet*
  list loses it, `typescript/HONESTY.md` §5.2 and index row 7 stop calling
  `refocus: false` a flat declaration (ruling **P9**, a dated in-place
  parenthesis on the `err_flow` 2026-09-10 precedent), and
  `capabilities.refocus` is **true** on every trace this driver converts —
  whether one particular trace can be refocused is a refusal, not a
  capability (R10). Measured, not asserted: E15's **H1 0 of 31** pre-rerun
  refusals over real members of somebody else's suite.
- **Two vocabulary lines retired, both of which had gone false.**
  `no_rerun_note`'s *"refocus is not yet this recorder's"* becomes the Python
  and Rust shape, naming `sensorium ts run --focus <file>:<qualname> --
  <harness command>`; and *"arguments are not read in this version"* is gone
  from the blind-spot block — rung 4 gave a focused site its arguments and a
  refocus always deepens the focus, so the line had been false on every trace
  a refocus produces. Its absence is pinned over a transcript by
  `tests/test_refocus_typescript_licence.py`.
- **`js_inspect._MORE`** — the §2026-09-12 item that scheduled its own
  removal "at the next Python minor" — is removed, and that item is **struck
  where it stands** (ruling **S2**), which is now
  [`CARRIED-DEBT-ARCHIVE-11.md`](CARRIED-DEBT-ARCHIVE-11.md), this file's
  ceiling having cut that section there before this one was appended; the
  strike carries a dated pointer back here. Zero consumers before and after;
  `tests/test_js_inspect.py` asserts the name is gone and that `INSPECT_MORE`
  is the public one — and its docstring's "CARRIED-DEBT §2026-09-12" citation
  now names a volume rather than the live file, which the final fix wave
  takes.

### The gaps E15 found (record §5)

1. **H7 and H8 STOP on clauses this record wrote wrong** (§5.1). H7 asked for
   a `licence: WITHHELD` line "whatever the verdict" where `refocus_report.py`
   prints one only on a MATCH; H8 spelled `refocus <run> --window 1` without
   the `--focus` that `refocus_cmd.py:186` marks `required=True`, so argparse
   answered before design §2.3 could. Both were found while the instrument was
   being read against the code it judges and **before `e15.sh` ran once**, and
   both were pinned by amendment rather than edited away (ruling **P16**).
   *Closed by* the corrected clauses already measured beside them — **H7′ 1 of
   1**, **H8′ 1 of 1**; nothing is left open but the discipline. *Cost if
   wrong:* two STOPs in a table of PASSes that a hurried reader mistakes for
   two defects in the tool.
2. **P20 — the container-ending clause withheld two MATCHed licences for a
   scheduler's coin flip** (§5.2). Rows 5 and 22 are MATCHes whose licences
   were WITHHELD on one reason each — `SIGTERM originally, exit 0 on the
   rerun` and its exact reverse — which is how vitest's pool ended the worker
   fork, not a fact about the world the program ran in: the same class as
   `VITEST_POOL_ID`/`VITEST_WORKER_ID`, which harness set 1 already names and
   never withholds on. **Proposed closure, NOT APPLIED:** count a
   container-ending disagreement the way harness set 1 is counted — printed,
   named, never a reason to withhold — leaving the withholding for endings
   that are the program's. *Cost if wrong:* two licences a later slice grants
   that this one withheld; the cost of leaving it is that every vitest row
   whose worker the pool happens to kill loses a licence it earned.
3. **The survey's class rule is a rule about a HAZARD, and its capture model
   was wrong** (§5.3). Six of the seven rows classed nondeterministic MATCHed
   and one (row 8) diverged, on a CALL recorded as `DescribeCharacter`
   originally and `DescribeCharacter.<anonymous>` in the re-run — so the
   mechanism the survey named may not be the one that fired. Separately, H6's
   `flow --value 0.4` prediction rested on "the only capture-bearing function
   in that trace is `loadVolumes`"; the read found `0.4` **115** times as the
   RETURN value of `getStoredVolume`, which the focus spec does not name. **H6
   is a STOP and was not re-rolled** (ruling **P21**): the read was not
   repeated and the clause was not widened to admit FOUND. *Closed by* a
   future survey that classes a row by whether the hazard can reach the
   compared multiset, and derives a `flow` prediction from the TIER rather
   than from the focus. *Cost if wrong:* a survey that keeps predicting reads
   in the wrong vocabulary, which is one STOP per slice that teaches nothing
   new.
4. **P5 — H6's closed loop rests on ONE row** (§5.4). Its four reads sit on
   survey rows 1, 16 and 31, and rows 1 and 16 are classed nondeterministic.
   H6 is readable on all four — its endpoint is the READ's verdict class and
   exit, not the pair's — but *the loop closes under a GRANTED licence* rests
   on **row 31** alone; rows 1 and 16 were granted on rows whose verdict was
   itself a reading. *Closed by* a later loop whose reads sit on deterministic
   rows by construction. *Cost if wrong:* the demonstration is narrower than
   the sentence describing it, which is why the sentence says so.
5. **The three load-time failures were never tried on the plain lens**
   (§5.5). `src/lib/aoe/aoe.vectors.test.ts`,
   `src/lib/distance/distance.vectors.test.ts` and
   `src/lib/builder/emit/pf2eSheet.test.ts` fail at load under the recording,
   looking for a data file above the frontend directory; whether they fail the
   same way with no `sensorium` in the picture was **NOT MEASURED** — running
   the plain suite is not one of §1's endpoints. *Closed by* one plain `npx
   vitest run` on the lens, outside a measured run. *Cost if wrong:* a
   circumstantial exoneration (ENOENT shapes, a cwd-relative path with no
   parent repo, and H2 reading the same `1 (waited)` on the unfocused original
   and all 31 focused re-runs) stands where a one-command fact would do.
6. **The reused-worker mechanism was not exercised by E15** (§5.6). Every row
   ran vitest's default isolated forks, one file per container; nothing in
   E15 passes `--no-isolate` or `--maxWorkers 1`. The corpus case is that
   claim's only evidence, and it pins **condition (b) only** — the derived
   task-ROOT-frame count — because under `--no-isolate` the converter records
   `test_file` singular and never the plural key (ruling **P3**). Condition
   (a), the `meta.test_files` count, is pinned by fixture traces alone
   (`tests/test_refocus_typescript.py`), since no converter writes the key
   today. *Closed by* a later measurement that records a reused worker for
   real, or by a converter that writes the plural key. *Cost if wrong:* a
   refusal half of whose condition has never seen a real recording.
7. **What the record does NOT license** (§5.7), restated because it is the
   half a reader skips: the **371 siblings** are a statement about the
   LOOKUP, not about their own pairs; a MATCH is an order-independent
   multiset of CALL/RETURN/RAISE/HANDLED per task and not an equality of
   VALUES; the second file of a reused worker is refused outright and the
   second file of a container whose extra test rooted in a helper is
   invisible to the derived check (blind spot 42); output, children and
   threads were UNVERIFIABLE on all 31 rows and are evidence of nothing in
   either direction; and every recording here is `SENSORIUM_TIER=call`.
8. **The disk** (§5.8). The 33 whole-suite invocations left **14 038 077 489**
   bytes (14.0 GB) of spool, which were freed after §3 was written exactly as
   §1 said they would be. The **22 675 054 592** bytes (22.7 GB) of traces —
   **12 276** of them — are KEPT on the work filesystem until this branch
   merges, because every trace id the record cites is in them: **freeing them
   is a post-merge chore**, and the PR body carries it. Two extra evidence
   files, `originals.txt` and `e-fences.txt`, are committed under the
   transcripts directory beside the 38 transcripts; §5.8's
   `68 290 424 832` free bytes is labelled in the record as a hand `df`
   reading present in neither the raw nor the results file (ruling **P22**).
9. **The lens's manifest check did not run, and the lens was not read-only**
   (§5.9). §1's preamble says the lens "is verified against rung 1's
   748-entry manifest before and after"; `e15.py` has no such check. The
   full-depth sweep found three paths newer than the launch, all under
   `node_modules` and none a source file — the directory itself, an empty
   `.vite-temp`, and vitest's per-file results cache
   (`node_modules/.vite/vitest/<sha>/results.json`, 39 667 bytes). Because
   `copy_lens.sh` **symlinks** `node_modules`, there was ONE of that file,
   inside the lens, shared and rewritten by all 33 invocations: "the lens is
   READ-ONLY" was not literally true, and the 33 invocations were not
   independent of each other the way a fresh copy per invocation would make
   them. *Closure, for the runner that comes next:* (a) `copy_lens.sh` copies
   or read-only-binds `node_modules` instead of symlinking it, so a harness
   writing its own caches writes them inside the throwaway copy; (b) `e15.py`
   verifies the manifest at preflight AND at cleanup, so a claim §1's preamble
   makes is one the instrument holds — the E12 instruments had such a hash and
   E15's does not. *Cost if wrong:* a record whose isolation claim rests on
   prose, and a shared mutable file whose harmlessness this run can assert but
   not demonstrate. Neither is applied here: the instrument is not edited
   after a number is read.

### Deferred by ruling

Each was ruled at execution, is in the design's §9 or this slice's ledger, and
leaves something a later slice may want.

- **The two drops are RULINGS, not debts** (**S1**, Brice, 2026-09-13). The
  **C conversation** — the 44 design-level rows of the rung-4 debts design's
  §9 — is **dropped, not on hold**. The **token-cost measurement** is dropped
  with it: its branch `feat/token-cost-measure` is kept LOCAL at `7c0009b`
  (21 commits, never pushed) as a record, and nothing on `main` names either.
  They are written here because this ledger is the only place that says what
  happened to them. *Cost if wrong:* two bodies of work whose disposition
  lives in one paragraph — which is the reason the paragraph exists.
- **Refocus by invocation id** (design §7): every pair compared, a roll-up
  verdict and an exit for a mixed result. A different report shape and its own
  brainstorm, and the natural next step now that the pair rule has been
  measured. *Cost if wrong:* a reader with 372 containers asks 372 questions.
- **A narrowing spelling** (`--only-this-file`, design §7): rejected by **R1**
  for this slice, because a narrowed command is a command the reader never
  typed and a re-run that quietly runs something else is not evidence about
  the run in hand. Blind spot **43** declares the cost instead of hiding it
  behind a default. *Cost if wrong:* every question costs the whole suite,
  which is exactly what the blind spot says.
- **Blind spot 42's real closure is a runtime change, not a reader one**
  (**R11**, **P3**). The derived check reads the trace's own task ROOT frames;
  a second test file whose callbacks all root in a non-test helper is
  invisible to it, and the container pairs by its first file — DIVERGED or
  MATCH on the container's shape, never a guess. Closing it needs the setup
  file to mark every file start under a shared module cache, which is the
  recorder's business. *Cost if wrong:* a pair that is honestly named and
  honestly compared, over a container that ran more than the reader thinks.
- **P20's proposed closure** and **§5.9's two closures** are written above
  with their costs and are NOT applied: this record is measured once and
  neither a number nor its instrument moves after a reading.
- **`refocus_typescript.py` is one module for seven refusals, the re-run, the
  pair and the licence bridge**, at 705 lines. The linked scan inside it is a
  ~20-line copy of `refocus_rust.find_pair`'s (plan-mandated shape); a shared
  `_linked_traces` in `refocus_licence.py` is the tidy, and the next edit to
  either is where it pays for itself. *Cost if wrong:* two scans to keep in
  step.

### Files near the ceiling

The 800-line gate (`tests/test_ceiling.py`) covers every tracked `.py`,
`.rs`, `.sh`, `.md`, `.mjs`, `.ts` and `.tsx`. These are the ones this slice
wrote in, measured at its last commit, whose next edit must take a seam
rather than a paragraph (ruling **P14**: the gate binds, not a plan's size
estimate):

- **`rust/HONESTY-BLIND-SPOTS.md` 800** — at the gate exactly, untouched by
  this slice; §2026-09-12's **P15** note stands, and its next entry opens a
  volume.
- **`README.md` 799** — took this slice's refocus sentence **net-zero**,
  trimming the same section; the seam is the TypeScript section itself.
- **`docs/query.md` 797** — the seam is **`docs/query-typescript.md`**, on
  the `HONESTY-REFOCUS.md` precedent that this slice already used once.
- **`typescript/HONESTY.md` 795** — the seam is the one this slice took: the
  next section opens in its own file, as §12 *Refocus* did.
- **`tests/test_ts_ingest_meta.py` 789** and
  **`tests/test_refocus_typescript.py` 783** — the refocus tests already live
  in two files (`tests/test_refocus_typescript_licence.py` 361 is the second);
  the ingest tests' seam is `tests/test_ts_ingest_refocus.py` 95, which this
  slice opened.
- **`src/sensorium/query/refocus_world.py` 710** and
  **`refocus_typescript.py` 705** — `refocus_licence.py` (133) was opened at
  Task 1 precisely because `refocus_world.py` would otherwise have stood at
  792, and it is where the next shared helper goes.
- **`CHANGELOG.md` 689** after the 0.14.0 entry — `CHANGELOG-ARCHIVE-2.md`
  opened at 0.13.0 and takes the next cut.
- **This file** — the section above was drafted and measured before it was
  written, the way the rule at the top asks.
- Other tracked files sit between 770 and 800 and are not listed: a hand-kept
  list of the files somebody remembered is the thing `test_ceiling.py`'s
  pattern scope replaced.

### Deferred minors, per task

Small, named, none measured away; the ledger holds every one and this is the
roll-up. The items already stated above — `_MORE`, blind spot 42's closure,
the linked-scan copy, P20 and §5.9's closures — are not repeated.

- **Task 0 (pre-registration and the RED cases):** the reused-worker truth
  named `test_files` as the mechanism (reworded at Task 5 under P3,
  expectation unchanged); the lock test carries duplicate
  `working_tree_sha256`/`section1_sha256` keys, and the survey's mutation
  test writes a temporary file only to hash it.
- **Task 1 (the shared world):** an 88-char docstring line in
  `tests/test_acceptance_e4p_read.py`; `tests/test_refocus_world_threads.py`
  pins `callable` where identity (`refocus_world.env_of is
  refocus_licence.env_of`) is the claim; the task report said
  `refocus_world.py` 693 where `wc` said 692.
- **Task 2 (driver, converter, vector):** `driver.py`'s `paths.traces_dir()`
  mkdirs the store's `traces/` on a refused link (harmless — `runs` creates it
  too, and the README's promise is about the SPOOL directory);
  `info_typescript.py`'s truthiness guard where "key present" is the rule
  (equivalent on every real trace); `_record(..., link=None)`'s default has
  one caller.
- **Task 3 (the branch):** three meta reads per trace in the linked scan
  (`all_meta` once would do); the >1-candidate sentence says "claiming one
  test file" on an argv key; `_drive(program=)` is a dead parameter; the
  every-refusal-carries-the-note test covers 5 of 7 (3 and 4 skipped);
  `import sys`/`import os` inside five test bodies; a test named
  `…printed_after_the_verdict` asserts presence only; `_key_text` renders a
  `("test_files", …)` key as `argv …` (reachable only for a length-1
  `test_files` original, which no converter writes); and
  `tests/refocus_ts_fixtures.py`'s local `paths` shadows the module import.
- **Task 4 (the licence):** the env-line assertions are substrings rather
  than one whole-line pin; three spellings of a harness ending
  (`_harness_exit`, `_harness_side`, `_agreed_harness`) where one
  `_harness_core` would do; `_agreed_harness` is typed `dict` but fed
  `dict | None` (safe by call order); the new test file overlaps the other's
  refusal, exit and blind-spot tests; a docstring-asserting test, with
  `SENSORIUM_MANIFEST_DIR` missing from the behavioural parametrize; four
  unreached guard branches untested; the withheld end-to-end test does not
  pin its `exit:` line; and a 94-char docstring line at
  `refocus_typescript.py:71`.
- **Task 5 (the corpus):** a grep false-positive on the word "command's";
  `corpus/typescript/README.md`'s focus table is stale (pre-existing).
- **Task 6 (the docs):** `README.md`'s refocus clause sits semicolon-joined
  to `ts run`'s refusal list (pre-existing ambiguity); `typescript/HONESTY.md`
  §10's range row lost entry 39's date, and says "under 800" where the gate is
  `<= 800`; `HONESTY-REFOCUS.md` restates `docs/query.md`'s exit paragraph
  (the house pattern); `is_recorder_key`'s docstring still says **FOUR**
  `SENSORIUM_*` variables differ by construction where the docs now say three
  plus `SENSORIUM_FOCUS` when the call deepens; and a fix report cited two
  README lines as 83-column precedents that are 81 characters and 83 bytes
  (the em dash).
- **Task 7 (the instrument):** the box-path grep's three hits are the rule's
  own needles in tests; H5's docstring says seven clauses where the table has
  eight; `needle()` counts a file before reading it and continues on OSError;
  `sha256_file`'s `None == None` reads as restored; `wait_for_load`'s message
  says `preflight: load` inside the loop; the `DURATION` regex is duplicated
  in `e15_read` and `e15_phases`; H10 does not check the three new corpus
  cases beyond the corpus exit; `tests/test_acceptance_e15_assemble.py`'s
  `INSTRUMENT` list was not extended for `e15_cells_controls.py` (a hole in
  the box-path guard, over a file that is clean); `e15_report.py`'s
  `LOOP_GATED` is dead and the gate hand-repeated in five cells;
  `exit_code_of(SystemExit(0))` could write `.DONE` over an error (latent,
  unreachable today); `fence_commands()` mkdirs as a side effect of building
  a list; the raw-shape docstring lacks `traces_between`/`as_written`;
  `env_paths()` refuses without a marker when a variable is unset
  (unreachable via `e15.sh`); a comment's literal `lens` clears the E-branch
  fence by one space; and the task report's `e15.py` line count 487 against
  494.
- **Task 8 (the measurement):** §4's "rule, as the cell states it" column
  truncates H7, H7′ and H9; §5 uses bold `**5.x**` paragraphs where the
  precedents use `### 5.x`; and §3's H9 says "about 3 s slower" where the
  arithmetic is 3.5 s (41.77 against 38.289).

### Process lessons

- **An always-word must be re-derived from the code, not carried.** The
  design said four `SENSORIUM_*` variables "fire on every refocus by
  construction"; three do, and `SENSORIUM_FOCUS` joins them only when the call
  deepens the focus. The claim was true of the Rust sentence it was adapted
  from and nobody re-read it against the branch it now described. A sentence
  containing *every*, *always* or *by construction* is a claim with a
  derivation, and the derivation is the part that has to be redone.
- **A pre-registered READ must be derived from the recorder's own tier rule.**
  H6's `flow --value` prediction was written in `--focus`'s vocabulary — only
  the focused function bears captures — where the trace's tier is what decides:
  at `call` a RETURN value is recorded for the file's traced functions and
  `--focus` only adds the LINE-level local deltas for the one it names. This
  is the S5 rung-4 lesson (a pre-registration written in the wrong command's
  vocabulary) **one command over**, which is what makes it a rule rather than
  an anecdote.
- **A "read-only" claim about a directory needs a full-depth sweep and a
  manifest, not a depth-1 listing.** The lens was called read-only on the
  strength of a shallow check; a full-depth mtime sweep found a file the run
  had rewritten 33 times through a symlink the copy owns (§5.9). A claim of
  the form *nothing moved* is only as strong as the sweep that looked, and a
  manifest hash before and after is the version of it an instrument can hold.
- **A refusal keyed on a key nobody writes is dead on arrival — read the
  trace instead.** Design §2.3 row 7 fired on `meta.test_files`, which the
  converter never writes under `--no-isolate` because the driver's setup file
  runs its top-level `fileStart` once under a shared module cache. Widening
  the CONDITION on the reader side (the trace's own task ROOT frames, counted
  as `max(declared, derived)` under **P11**) kept the sentence, the exit and
  the locked corpus expectation unchanged and cost no recorder change.
- **A brief's guessed count is not the tree's.** The corpus README's numbers
  were briefed as "forty-five cases / thirteen focus cases" and the tree said
  forty-seven and twelve — none of the three new cases records under a
  `record: {focus}`. A count in a brief is a guess about the tree at dispatch
  time; the command that recomputes it is the durable half. (The companion
  rule from §2026-09-12 still holds: a plan's line-count estimate is not a
  gate — the ceiling is, which is ruling **P14** in one line.)
- **Two pre-registration errors found before a launch are worth more than a
  clean table.** H7's and H8's clauses were wrong, were caught while the
  instrument was read against the code it judges, and were pinned by
  amendment with corrected clauses beside them rather than edited. Editing
  either would have converted a prediction into a description and left no
  trace that anyone had been wrong; what it cost is two STOPs in a table of
  PASSes, and what it bought is two cells that ask the question the first
  ones meant.
