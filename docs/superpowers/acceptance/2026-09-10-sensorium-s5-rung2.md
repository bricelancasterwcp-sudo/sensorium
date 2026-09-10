# S5 rung 2 — the throw flow: `exceptions` on a TypeScript trace: acceptance (pre-registered)

**Status: measured (Task 7, 2026-09-10). The rung ships PASS — §5.**

§1 of this file was written and committed on the feature branch
`feat/s5-rung2` **before any line of rung-2 code existed**: the commit that
carried it changed nothing under `src/`, `typescript/src/`, `rust/` or
`corpus/`. §1 is the locked contract — after a number is read, no threshold
moves, no arm is added and no run is re-rolled; an infrastructure kill may be
re-run from zero with the reason recorded. It is byte-unchanged, and the lock
test says so. §2 keeps its preflight pins and gains §2.3, the instrument
changes made before any endpoint ran. §3, §4 and §5 were written when the
endpoints had run and are the measured half of this record.

The one thing this rung can be tempted to move after the fact is **E6-TS′'s
adjudication protocol** — the definition of a *true* SWALLOWED line — because
it is the only rule here that a human applies by reading source rather than a
number. It is therefore fixed below, byte-locked, before a single SWALLOWED
line has been printed.

The lock is enforced by `tests/test_acceptance_s5_rung2_lock.py`, which
compares the working tree's §1 against the commit that first carried it and,
separately, compares each of §1's two verbatim bodies against
`git show <sha>:<source>` — so "verbatim" is a claim a test holds, not one
this prose makes.

## 1. Pre-registration

Two blocks, copied verbatim from the two documents that own them. Nothing
below this line is paraphrased, reordered or reworded; the only editorial act
is that each source section's own heading is carried as the `###` sub-heading
that introduces its body here (both are `##` in their source files and appear
as `###` below), so that this record keeps its own §1–§5 numbering. The bodies
are byte-for-byte the source sections. Sources, at the commits named:

- `docs/superpowers/specs/2026-09-10-sensorium-s5-rung2-throw-flow-design.md` at **`db37351`** (the merge commit on `main` that this branch was cut from) — `## 7. Pre-registered endpoints`, whole: the lens sentence, the endpoint table, the E6-TS′ adjudication protocol and the stop rules that follow it
- `docs/superpowers/plans/2026-09-10-sensorium-s5-rung2-throw-flow.md` at **`f0a38e0`** (this branch's plan, at its second and final plan commit) — `## Pre-registration (…)`, up to `## File structure`

### 7. Pre-registered endpoints

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

### Plan section "Pre-registration (Task 0 commits spec §7's table and its adjudication protocol verbatim as the record's §1, plus these pins)" — verbatim

- **The lens:** `/mnt/extra/sensorium-s5/vtt/frontend`, VTT `0091e97`, manifest `/mnt/extra/sensorium-s5/manifest-rung1-before.txt` (748 entries) verified before and after every arm that touches it.
- **E3-TS″'s file, named now:** `src/__tests__/useMeshVoice.test.tsx` (rung 1's), twenty recordings, `diff` each against the first.
- **E6-TS′'s run:** ONE guarded `sensorium ts run -- npx vitest run` on the lens at tier `call` through THIS rung's recorder; then `sensorium exceptions <invocation>` with `--limit 10000`; the transcript committed beside the record; every SWALLOWED shape adjudicated under §7's protocol; the ambiguous-escaped count, the per-disposition tally and the number of shapes whose adjudication needed a second reading reported.
- **E7″'s needles**, each a literal: `oid`, `chain`, `Err`, `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own`, over the E6-TS′ transcript and over one single-trace `exceptions` transcript.
- **E8″'s shapes:** every `// SWALLOW` / `// ESCAPE` marker in `swallow.probe.test.ts` and `escape.probe.test.ts`, one check per marker.
- **E1‴ / E10″:** `arms.sh` ×5 batches interleaved; `e10p.sh` over the E6-TS′ run's spool set at jobs 16 n=5 and over its `useMeshVoice` spool n=5; reported beside 1.0587 / 1.1324 and 16.3859 s / 0.1648 s.
- **E6-TS's pre-registered set, per corpus case** (spec §6.1's verdict column, fixed here before any case exists): SWALLOWED lines — `silent_swallow` 1 (the `catch` in `loadConfig`), `logged_catch` 1, `callback_sink` 1, `callback_handled` 1, `await_rejection_caught` 1, `finally_return` 1, `dependency_throw` 1, `rethrow_hop` 1 (the rethrow's block); every other case 0. The exact line text is pinned by each case's `questions.yaml` (Task 6) before the collector runs (Task 7); a case whose count differs from this table STOPs, whatever its text.
- **Reported without a gate:** the count of HANDLED records per `how` on the lens run; the share of catch clauses reading `catch_escaped`.

## 2. Ambient pins (preflight, recorded before any rung-2 code exists)

Every value below is the output of the command beside it, run on this box on
2026-09-10 between 09:52 and 10:03 local time (`-05:00`) — the session
that opens rung 2 — before any file under `src/`, `typescript/src/`, `rust/`
or `corpus/` was touched. The lens is the VTT frontend **copy** at
`/mnt/extra/sensorium-s5/vtt/frontend` (VTT `0091e97`);
`~/workspace/projects/vtt` was neither read nor touched, and the lens was read
here by `sha256sum -c` and by the census instrument's AST walk, both of which
only read. Box paths appear in this table because a pin without its location
is not a pin; the rule that no box path is committed binds the results JSON
and the code, as it did at rung 1 and slice 2.

`<lens>` abbreviates `/mnt/extra/sensorium-s5/vtt/frontend` throughout.

| Item | Command | Value |
|---|---|---|
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| lens vitest | `node -e "console.log(require('<lens>/node_modules/vitest/package.json').version)"` | `4.1.9` |
| lens vite | same, `vite` | `6.4.3` |
| lens typescript | same, `typescript` | `5.9.3` |
| lens jsdom | same, `jsdom` | `29.1.1` |
| nproc | `nproc` | `16` — also the driver's default job count, so E10″'s `--jobs 16` cell is the default cell |
| governor | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | `powersave` |
| memory | `free -g` | total `29`, used `17`, free `7`, shared `4`, buff/cache `9`, available `12`; swap total `15`, used `0` |
| free disk `/` | `df -h /` | `4.9G` available on `/dev/nvme0n1p2` (100% used, 915G total) — the refusal floor is 3 GB; this passes with 1.9 GB to spare, and nothing this rung measures writes to `/` |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `69G` available on `/dev/nvme1n1p1` (85% used, 469G total) — the refusal floor is 8 GB; this passes with 61 GB to spare |
| mount `/` | `findmnt -no SOURCE,FSTYPE /` | `/dev/nvme0n1p2 ext4` |
| mount `/mnt/extra` | `findmnt -no SOURCE,FSTYPE /mnt/extra` | `/dev/nvme1n1p1 ext4` — a different block device and filesystem; the worktree, the venvs, the lens and every store live here |
| 1-minute load, preflight | `cat /proc/loadavg` (before anything was created) | `0.46 0.54 0.45 3/2568 3553075` — 1-minute load **0.46**, under the 4.0 refusal threshold |
| 1-minute load, at pin time | `date -Iseconds; cat /proc/loadavg` | `2026-09-10T10:03:26-05:00`, then `0.58 0.90 0.71 2/2589 3599376` — the close of this table's reading window |
| worktree | `git rev-parse --abbrev-ref HEAD` | `feat/s5-rung2`, at `/mnt/extra/sensorium-rung2/s5-rung2`, cut from `main` at `db37351` |
| `git rev-parse HEAD` | `git rev-parse HEAD` | `f0a38e0c5a2917a3c438afb41850a8769b80e6b8` — the plan's second commit, this branch's tip when the pins were taken. **T0** for this rung |
| worktree venv | `uv venv .venv --python 3.13 && uv pip install -p .venv/bin/python -e ".[dev]"` | `.venv/bin/python -V` → `Python 3.13.13` |
| 3.12 venv | `uv venv .venv312 --python 3.12 && uv pip install -p .venv312/bin/python -e ".[dev]"` | `Python 3.12.13` |
| 3.14 venv | `uv venv .venv314 --python 3.14 && uv pip install -p .venv314/bin/python -e ".[dev]"` | `Python 3.14.4` |
| sensorium, worktree venv | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.9.1` |
| sensorium, global tool | `$(dirname $(readlink -f $(which sensorium)))/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` (the tool venv under `~/.local/share/uv/tools/sensorium`) | `0.9.1` — the same version. The global tool is **never reinstalled from this worktree**: E1‴ and E10″ compare against recorded numbers, not against a rebuilt binary |
| node installs | `npm ci --prefix typescript && npm ci --prefix typescript/probes && npm ci --prefix corpus/typescript` | `typescript/node_modules` 5 entries, `typescript/probes/node_modules` 65, `corpus/typescript/node_modules` 35 |
| store root | `mkdir -p /mnt/extra/sensorium-s5/store-rung2ts` | created; `SENSORIUM_DIR` for every trace this rung records or converts |
| lens manifest, verified | `cd <lens> && sha256sum -c /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | exit `0`, **748 OK, 0 FAILED** — the lens is byte-identical to the state rung 1 left it in. Manifest file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`, 748 lines, as the plan pins it |

### 2.1 Suite baselines (the regression fence)

Taken on the pin commit `f0a38e0`, **before any of Task 0's own four
commits**. Every later task restores these exactly, or names what moved.

Two of Task 0's four commits add tests to the enumeration, so the fence a
later task restores is not the `f0a38e0` column: the lock-test commit adds
`tests/test_acceptance_s5_rung2_lock.py` (its own tests, plus one case in
`tests/test_ceiling.py`, which is parametrized over every tracked non-exempt
file) and the census commit adds `typescript/acceptance/census_catch.mjs`
(one more `test_ceiling.py` case; the record itself adds none, sitting in an
exempt directory). **That post-Task-0 fence is re-measured and named at the
head of Task 1 rather than derived here** — arithmetic on a test count is not
a measurement of one, which is the mistake slice 2's §2.2 had to correct with
a footnote.

| Suite | Command | Baseline at `f0a38e0` |
|---|---|---|
| pytest, 3.13 | `.venv/bin/python -m pytest -q` | `3488 passed, 30 skipped` (91.93 s) |
| pytest, 3.12 | `.venv312/bin/python -m pytest -q` | `3484 passed, 34 skipped` (93.80 s) |
| pytest, 3.14 | `.venv314/bin/python -m pytest -q` | `3492 passed, 26 skipped` (95.40 s) |
| TypeScript unit | `npm --prefix typescript test` | `tests 167`, `pass 167`, `fail 0`, `skipped 0` |
| TypeScript types | `npm --prefix typescript run check` | exit `0`, no diagnostics (`tsc -p tsconfig.json`; never `npx tsc -p` from the root — R4) |
| corpus, TypeScript | `.venv/bin/python corpus/run_corpus.py --only-dir typescript --require-driver` | `13 cases, 35 questions, 0 failures, 0 error(s)` |
| corpus, root | `.venv/bin/python corpus/run_corpus.py --only-dir .` | `20 cases, 39 questions, 0 failures, 0 error(s)` |
| live TypeScript | `SENSORIUM_TS_LIVE=1 .venv/bin/python -m pytest -q tests/test_ts_live.py` | `10 passed (2.59 s)` |
| the exceptions fences | `.venv/bin/python -m pytest -q tests/test_exceptions_rust.py tests/test_exceptions_rust_gate.py tests/test_exceptions_rust_ambiguous.py tests/test_exceptions_invocation.py tests/test_vectors.py tests/test_vocab.py` | `299 passed, 2 skipped (12.11 s)` — the Python and Rust `exceptions` output, the vectors and the vocabulary strings. **This rung must not move one of them**; a change here is the regression the Global Constraints forbid, not this rung's arithmetic |

The `npm run check` row was measured with the working tree at `f0a38e0` and
nothing untracked under `typescript/acceptance/`: the census instrument was
written before this table was assembled and moved out of the tree while the
baseline ran, because `tsconfig.json`'s `include` reaches `acceptance/**/*.mjs`
and an untracked file would otherwise have been inside the baseline it is
supposed to be measured against. With the census back in place the same
command reads exit `0` — reported here, not substituted for the baseline.

### 2.2 The census's dry runs (E2″'s `seen` half, before any splice)

`typescript/acceptance/census_catch.mjs` lands in this task's **fourth**
commit; the two runs below were taken from that file before the record was
committed, so the numbers are measured and this section is not a promise. The
instrument reads files and walks ASTs — it executes nothing and writes
nothing, so the read-only lens is read-only still (the manifest row above was
re-verified after these runs: 748 OK, 0 FAILED).

`spliced` is `{}` and `ratio` is `null` in both, and that is the honest
reading at T0: the transform does not record catch sites in its per-file
manifest until Task 2, so **E2″'s numerator does not exist yet**. Task 7
re-runs the same instrument against the same two roots and fills both halves.

| Root | Command | Value |
|---|---|---|
| the probe project | `node typescript/acceptance/census_catch.mjs typescript/probes` | files `11`, catch clauses `4`, `.catch(x)` sites `1`, `.then(x, y)` sites `0`, completing `finally` `0`; excluded `{}`; parse errors `[]`, failed `[]` |
| the lens | `node typescript/acceptance/census_catch.mjs <lens>` | files `741`, **catch clauses `177`**, `.catch(x)` sites `108`, `.then(x, y)` sites `2`, completing `finally` `0`; excluded `{"skip": 5}`; parse errors `[]`, **failed `[]`** |

`failed` empty on the lens is the instrument's own precondition: a count taken
over a tree it could not fully read is not the denominator E2″'s ratio needs,
and the row would say so rather than quietly report a smaller number.

**`finally_completing` reads 0 on both roots, and that is a measured zero, not
a rule that cannot fire.** A rule whose count is zero everywhere it is run is
indistinguishable from a rule that is broken, so spec §2.3's clause was
exercised on a throwaway fixture before these two rows were taken: a `finally`
holding `return` counts, one holding `continue` counts, one whose only
`return` sits inside a nested arrow does **not** (closure depth), and one that
only logs does not — 2 of 4, as written. The same fixture pinned the two call
arities: `.catch(fn)` counts and `.catch()` does not, `.then(fn, fn)` counts
and `.then(fn)` does not. The lens simply has no completing `finally` in its
`src`, which is a fact about the lens and is what E2″ will have to divide by.

### 2.3 Instrument changes made before any endpoint ran

Every one of these was made and recorded **before the endpoint it touches had
been measured**; none of them moved a threshold, and §1 is byte-unchanged
(the lock test is green).

**The escape rule was amended at Task 6.** A bare rethrow — `throw e;` whose
operand after any parentheses is the binding itself — is a traced EXIT and
not an escape, for `catch` clauses and for rejection callbacks alike (spec
§2.1's dated amendment, commits `68015dd` and `43e1fbd`), because the literal
rule barred every `throw e` hop from SWALLOWED and made §1's locked
`rethrow_hop` count unreachable by construction. No endpoint had been
measured; §7 and the count table are byte-unchanged.

The rest are Task 7's, the first three in its instrument commit `3db0f28`
and the fourth in the measurement commit that carries this record:

- **E2″'s numerator was written** into `census_catch.mjs` (Task 2's ruling):
  the transform's own output over the same files, matched marker by marker
  and line by line. Its denominator is unchanged — the lens row still reads
  741 files / 177 catch clauses / 108 `.catch` / 2 `.then` / 0 completing
  `finally`, as §2.2 pinned it at T0. Verified on a fixture that it names a
  sanctioned exclusion (a spread argument) and reports an unnamed miss.
- **`arms.sh`, `e3.sh` and `e7.sh` gained a `SENSORIUM_BIN` hook**, default
  unchanged. All three hard-coded the GLOBAL `sensorium`, which is main's
  recorder: E1‴, E3-TS″ and E7″ would have measured the binary already
  installed rather than the one this branch built, and the global tool is
  never reinstalled from a worktree.
- **E7″'s three identifier needles are matched word-bounded and
  case-sensitively.** `oid`, `chain` and `Err` are other recorders'
  identifiers; as case-insensitive substrings `Err` is satisfied by every
  `Error('…')` a verdict prints, `oid` by "avoid" and `chain` by
  "describe_chain", so that reading could not be passed by any answer that
  named an exception type. The six prose needles stay case-insensitive. This
  is the same correction `e7_report.py` already records having made once for
  `python ?`.
- **The adjudication table's row parser was tightened** from "a line starting
  `| S`" to "a first cell matching `S<digits>`", on the first read of the
  filled table: the file's own summary table has a row beginning `| SWALLOWED
  shapes printed |`, which the loose test booked as a malformed shape row and
  which held the cell at `null`. The number had not been taken; the report is
  a pure function of the saved transcript and the table, so re-running it is
  not a re-measurement — the sweep itself ran once and was not repeated.

**One infrastructure kill, re-run from zero.** E1‴'s first batch loop was
killed 2 minutes in by the shell harness's own command timeout, mid-run of
batch 1's `call` arm; 2 of the 15 runs had been written and no cell had been
produced. `arms.jsonl` was deleted and the five batches were re-run from
zero, detached, which is what §1's stop rules require of an infrastructure
kill.

## 3. Results

Every endpoint ran, in the order the plan fixes (the timed and lens-touching
arms last), each once. Every cell below is
`{value, n, lens, dropped}` in
`2026-09-10-sensorium-s5-rung2.results.json`, with the recorder
(`sensorium 0.9.1` / `sensorium-ts 0.2.0`) and the commit it ran at
(`3db0f28a655e6e8ccb6a4d1bb8c1260bb03dabe7`) beside it. Nothing was dropped:
every `dropped` list in the file is empty.

**On provenance**, because slice 2's final review found cells attributed to
the wrong recorder: the `lens` string every cell carries names the recorder
that produced the LENS (`sensorium 0.8.7` / `sensorium-ts 0.1.0`), which is
NOT the one that took these measurements. Two instruments record their own
under that name — E6-TS′'s and E8″'s cells read `recorder_basis: own` — and
E10″'s two carry the same sha under `converter_rev`, which is the name that
endpoint's ladder compares on. The assembler stamps the rest from the
session's own invocation and says so in each cell's `recorder_basis`. The
file's `recorded_by` block carries the pair once at the top.

**No row below reads PASS, and that is the Global Constraints' rule, not a
hedge:** *"Verdict words come from the rule (spec §3.3): no PASS on an
endpoint whose rule names none."* **Six** of this rung's nine rules name only
a failure word — STOP for five of them, NO-GO for E5″ — so what a clean
reading of one can say is that the word did not fire, and that is what its
verdict column says. The other **three** name no word at all: E7″ states two
conditions, and E1‴ and E10″ say "no gate". The word **PASS** appears once,
in §5, as the RUNG's shipping word, which is the one place §1 puts it (`a
false one → STOP (the rung ships DONE-WITH-STOP …)`). This is slice 2's own
correction applied from the start rather than after a review.

| Id | What it answers | Cell | Verdict |
|---|---|---|---|
| E6-TS | the corpus's verdicts | **17 of 17** cases equal to the locked table (n=17, 0 dropped); 8 SWALLOWED lines over the 17 answers, matching §1's eight swallow cases | **no STOP** — no difference |
| E6-TS′ | false accusation on the lens | **0 false SWALLOWED** of **30** adjudicated shapes (n=30, 0 dropped); tally `swallowed 261, ambiguous 53` over 314 raises in 53 of 372 processes | **no STOP** — the gate is met |
| E8″ | the probes' shapes | **32 of 32** markers seen (19 `// SWALLOW`, 13 `// ESCAPE`); checker 96 checks, 0 failures, 11 spools | **no STOP** — none missing |
| E2″ | every catch site instrumented | **ratio 1.0000** — 287 spliced of 287 eligible (177 catch clauses, 108 `.catch`, 2 `.then`, 0 completing `finally`) over 741 files; **0** named exclusions needed, **0** unspliced sites | **no STOP** — no unnamed miss |
| E3-TS″ | the comparator does not cry wolf | **DIVERGED 0/19, REFUSED 0/19** — 20 recordings, 20 with a trace, 19 pairs, 19 MATCH, 0 bad calls | **no STOP** |
| E5″ | both harnesses run | **2 of 2** claims: vitest `372 passed (372)` / `4278 passed (4278)`, exit 0; `node --test` checker `ok: true`, 25 checks, 3 spools, 0 failures | **no NO-GO** |
| E7″ | the reader's words | **0** occurrences of the nine needles, over BOTH transcripts (704 reader lines + 167 invocation lines); v30–v33 **green** (8 passed) | **both clauses met** — the rule names no word |
| E1‴ | what the product costs | **off/plain 1.0608**, **call/plain 1.1266** — harness-wall medians of n=5 per arm, conversion excluded; 15 of 15 runs green, every load reading under 4.0 (max 3.91). Rung 1 read 1.0587 / 1.1324 | **REPORTED — no gate** |
| E10″ | what conversion costs | the fresh set at jobs 16: median **16.0715 s** (n=5, 372 spools, 414 599 103 B); its `useMeshVoice` spool: median **0.1642 s** (n=5, 611 325 B). Slice 2 read 16.3859 s and 0.1648 s | **REPORTED — no gate** |

Reported beside the gates, as §1 asks and with no rule attached:

| Reported | Value |
|---|---|
| HANDLED records per `how`, over the lens run's 372 member traces | `catch` 36, `catch_callback` 182, `catch_escaped` 22, `sink_empty_catch` 37, `sink_empty_catch_callback` 8 — **285** in all |
| the share of catch clauses reading `catch_escaped` | **22 / 177 = 0.1243** — the escape rule's own verdict distribution over the lens, read off the transform's output, with `catch` 87 and `sink_empty_catch` 68 beside it |
| the lens run's spool | 372 files, 4 160 786 lines, **414 599 103 bytes**; harness wall 24.9513 s, driver wall 38.1300 s (the driver converts inline) |
| E6-TS′'s shapes needing a second reading | **15** of 30 (the constant-signal family) |
| escaped-ambiguous shapes | **13** of the 30 AMBIGUOUS shapes |

§2.2's two census rows are **not** E2″. They are the instrument's dry runs at
T0, with the numerator missing by construction; E2″'s row above is the
measured one, taken with the same instrument over the same root — and its
denominator reproduces §2.2's lens row exactly (741 / 177 / 108 / 2 / 0),
which is the evidence that adding the numerator did not move the half that
was already pinned.

## 4. Decisions

One verdict per pre-registered endpoint, with **the rule quoted from §1**
beside the number that answered it, and the verdict word taken from that rule
and from nowhere else. Nothing was re-rolled, no threshold moved, and every
endpoint ran exactly once. **Every endpoint of §1 has a cell**; none is
outstanding.

### 4.1 E6-TS — the corpus's verdicts

> the printed SWALLOWED lines `==` the pre-registered set per case (equality,
> not subset); every swallow case's set non-empty; the `dispositions:` tally
> compared whole; any difference → STOP

**No STOP.** All **17** TypeScript corpus cases that ask an `exceptions`
question were recorded through the driver and answered: **17 of 17** match
§1's locked table, and the eight cases §1 names as swallow cases each printed
a non-empty set (one line apiece; eight in all). The tally line was parsed
WHOLE and its `swallowed` term compared, never as a substring — and it was
compared against the count of printed `SWALLOWED --` lines as a second,
independent derivation. The two agreed on every case, so the tool's own tally
describes its own output. Nothing was dropped.

### 4.2 E6-TS′ — false accusation on somebody else's suite

> gate **0 false SWALLOWED**; a false one → STOP (the rung ships
> DONE-WITH-STOP with an amendment slice, Rust's precedent). Reported beside
> it: the per-disposition tally, the count of escaped-ambiguous shapes, and
> the count of shapes whose adjudication needed a second reading

**No STOP: 0 false SWALLOWED.** ONE guarded call-tier run of the VTT
frontend's whole suite (372 files, 4278 tests, 1-minute load 0.64 at the
guard) through this branch's recorder, then `exceptions
20260910-150809-cbc8de --limit 10000`, exit 0, nothing paged. The answer
printed **60 shapes — 30 SWALLOWED and 30 AMBIGUOUS** over a tally of
`swallowed 261, ambiguous 53` (314 raises, 53 of 372 processes with throws,
319 with none). **Every one of the 30 SWALLOWED shapes was read against the
VTT source at the sink site the verdict names** and adjudicated under §1's
protocol, one row each, in
`2026-09-10-sensorium-s5-rung2-e6tsp-adjudication.md`, which was written
whole before any number entered §3. **30 TRUE, 0 FALSE.**

Reported beside the gate: the tally above; **13** escaped-ambiguous shapes
(the other 17 AMBIGUOUS shapes read rule 5's last reason — Gap 4);
**15** shapes whose adjudication needed a second reading — the family whose
clause hands the caller a CONSTANT on failure (`setError('…')`, `return
fallback`, `return undefined`, `ok = false`), ten of which do not bind the
exception at all. §1's own rule settles that family on the TRUE side: it puts
"a clause that only logs" there, and `console.warn(e)` transmits the WHOLE
error to a channel a human reads, which is strictly more of the failure than
a fixed string transmits anywhere.

The declared blind spot Task 2 ruled on — a `.catch` whose receiver is not a
promise could write an orphan HANDLED and reach "SWALLOWED, born outside a
throw statement", which would be FALSE — **did not fire**: all eleven
callback shapes have a promise receiver (an `apiFetch`/`fetch` chain, a
`Promise.resolve(…)` chain, `r.json()`, or an `async` function's return).

### 4.3 E8″ — the probes' shapes

> every marker's record present per shape; a missing one → STOP

**No STOP.** `npm run probe` at tier `call`: checker `ok: true`, 11 spools,
**96 checks, 0 failures**. Against the population §1 fixes — every `//
SWALLOW` and `// ESCAPE` marker in the two probe files, counted out of the
sources by this endpoint's own instrument rather than taken from the checker
— **32 of 32 markers were seen**: 19 SWALLOW markers over the eleven shapes
(every shape's checks green) and 13 ESCAPE markers, `escape:count` 13 and
`escape:how` 13 as marked, `wrong: []`.

### 4.4 E2″ — every catch site instrumented

> ratio 1.000 after NAMED exclusions; one unnamed miss → STOP

**No STOP: ratio 1.0000.** Over the lens's `src`, **741** eligible files (5
excluded by `classify`, 0 parse errors, 0 files the census could not read):
177 catch clauses + 108 `.catch(x)` sites + 2 `.then(x, y)` sites + 0
completing `finally` = **287 sites seen**, and the transform's own output
carries a marker for **287** of them, matched line by line. **Zero sites
needed the named exclusion** (no `.catch`/`.then` on the lens carries a
spread argument) and **zero were unspliced**, so there is no miss, named or
unnamed. The denominator is byte-identical to §2.2's T0 dry run.

### 4.5 E3-TS″ — the comparator does not cry wolf

> DIVERGED 0/19, REFUSED 0/19; any → STOP

**No STOP.** `src/__tests__/useMeshVoice.test.tsx` recorded **20** times
through this branch's recorder, each behind the load guard; 20 recordings,
20 traces, 19 pairs diffed against the first: **19 MATCH, 0 DIVERGED, 0
REFUSED, 0 bad calls.** The comparator's own sentence names 398 causal events
compared, which are `(file, qualname, kind)` for CALL/RETURN/**RAISE**/
**HANDLED** — the two kinds this rung moved — so the pairs were compared over
exactly the rows that changed.

### 4.6 E5″ — both harnesses run

> 372/4278 green; `node --test` green with its rows; a red vitest is NO-GO

**No NO-GO.** The vitest half is E6-TS′'s one run (the plan's order: that run
doubles as this endpoint's): ` Test Files  372 passed (372)` and `      Tests
4278 passed (4278)`, driver exit 0. The `node --test` half:
`npm run probe:nodetest`, checker `mode: nodetest`, `ok: true`, **3 spools,
25 checks, 0 failures**.

### 4.7 E7″ — the reader's words

> 0 occurrences of `oid`, `chain`, `Err`, `asyncio`, `python ?`, `cargo`,
> `coroutine`, `Rust disposition`; plus v30–v33 green

**Both clauses met; the rule names no verdict word.** The nine needles §1's
plan block lists (the eight above plus `Python's own`) were counted over
BOTH transcripts §1 names: the single-trace reader transcript (every reader
command on one lens member, 704 lines, committed as
`…-e7-exceptions.txt`) and the E6-TS′ invocation transcript (167 lines,
committed beside it). **0 occurrences of every needle in both**, and the
ungated context counts are 0 too — the words `python` and `rust` do not
appear in either answer at all. `v30 or v31 or v32 or v33`: **8 passed**,
exit 0.

### 4.8 E1‴ — what the product costs

> reported beside rung 1's off/plain 1.0587 and call/plain 1.1324; no gate

**Reported.** Five interleaved batches of plain / off / call on the lens,
each run behind the load guard, through this branch's recorder
(`.venv/bin/sensorium` — see §2.3). **15 of 15 runs green** (`372 passed
(372)` / `4278 passed (4278)`, exit 0); nothing dropped; every load reading
under the 4.0 refusal, spread 2.83 – 3.91.

| arm | timed by | median (n=5) | min – max | vs plain |
|---|---|---|---|---|
| plain | the runner's own clock | **22.0945 s** | 22.0217 – 22.1465 | 1.0000 |
| off | the HARNESS wall (`harness.json`) | **23.4369 s** | 23.2963 – 23.9345 | **1.0608** |
| call | the HARNESS wall | **24.8921 s** | 24.8117 – 24.9396 | **1.1266** |
| off, driver total | the runner's clock | 23.5058 s | 23.3656 – 24.0815 | 1.0639 |
| call, driver total | the runner's clock | 40.1609 s | 38.1101 – 40.7587 | 1.8177 |

Beside rung 1's **off/plain 1.0587** and **call/plain 1.1324**: this rung's
recorder — which now splices a HANDLED into every catch clause, wraps every
rejection callback and marks every completing `finally` — costs **1.0608**
and **1.1266**. The call arm is *cheaper* than rung 1's by 0.0058 and the off
arm dearer by 0.0021, both inside the arms' own spread; the honest reading is
that the throw flow did not move the product's cost. The driver's TOTAL wall
on the call arm (1.8177×) carries the inline conversion of a 414 MB spool
set, which is E10″'s subject and not this arm's.

### 4.9 E10″ — what conversion costs

> reported beside slice 2's 16.3859 s and 0.1648 s; no gate

**Reported.** `e10p.sh` over the E6-TS′ run's own spool set, at the default
job count, five guarded repetitions each, on this branch's converter
(`3db0f28a…`). Nothing dropped: every repetition exited 0 and converted the
number of traces its copy held.

| cell | spools | bytes | median (n=5) | min – max | peak RSS | slice 2 |
|---|---|---|---|---|---|---|
| the fresh suite set, `--jobs 16` | 372 | 414 599 103 | **16.0715 s** | 15.997 – 16.5827 | 281 932 kB | 16.3859 s |
| its `useMeshVoice` spool, `--jobs 16` | 1 | 611 325 | **0.1642 s** | 0.1604 – 0.1857 | 27 036 kB | 0.1648 s |

Beside slice 2's **16.3859 s** and **0.1648 s**: **16.0715 s** and
**0.1642 s** — 0.3144 s and 0.0006 s faster, both inside the repetitions'
own spread, on a spool set 148 581 bytes LARGER than slice 2's because this
rung's recorder writes more HANDLED rows into it. The throw flow did not move
conversion's cost either. Every load reading was under 4.0 (3.19 – 3.84).

## 5. What the rung ships, and the gaps found

**S5 rung 2 ships PASS.** Every one of §1's nine endpoints ran, once, in the
plan's order, and not one of them fired its rule's failure word: E6-TS,
E6-TS′, E8″, E2″ and E3-TS″ took no STOP, E5″ took no NO-GO, E7″ met both of
its clauses, and E1‴ and E10″ are the two the pre-registration gates not at
all. **E6-TS′'s gate — the one that decides the shipping word — read 0 false
SWALLOWED over 30 hand-adjudicated shapes on a consumer's own suite**, so the
DONE-WITH-STOP branch §1 names ("a false one → STOP (the rung ships
DONE-WITH-STOP with an amendment slice)") is not taken and no amendment slice
is raised. Nothing was re-rolled, no threshold moved, no cell was measured
twice, and no cell is outstanding.

The four gaps below are findings, not stops: none is an endpoint's rule and
none changes a number above. Numbered as they are found; a later task appends
rather than renumbers.

**Gap 1 — the shape key's id mask carries Rust's float-type exclusion onto
TypeScript traces, and splits shapes that are one place.** `exceptions_group.
MASK` is `\b(?!f(?:16|32|64|128)\b)([ef])\d+\b`: `f32` and its siblings are
Rust type names a panic message can carry (ruling R-G8), so they are left
unmasked. On a TypeScript trace they are ordinary FRAME ids, and a shape
whose sink sits in frame 16, 32, 64 or 128 therefore keys on `in f32` where
its siblings key on `in f#`. Measured on the lens: the three SWALLOWED shapes
S1, S11 and S17 are the SAME clause at
`src/hooks/useAiAssist.ts:56` — verified by opening all three traces and
comparing `(file, line, qualname)`, which are identical — printed as three
blocks because their sinks sat in frames 174, 128 and 32. So the answer's
30 SWALLOWED shapes are **28 distinct places**. Nothing else moves: tallies
count units and not shapes (`swallowed 261` is unaffected), no verdict
changes, and the adjudication reached the same word for all three. The
grouper's own docstring already names the fix — *"keying on the classifier's
own components instead of on masked prose is the better answer and is
CARRIED-DEBT"* — and this is the first measurement of that debt on a
TypeScript lens.

**Gap 2 — three reused instruments were measuring the wrong binary, and it
took this rung to notice.** `arms.sh`, `e3.sh` and `e7.sh` hard-coded the
global `sensorium`, which is an editable install of `main`. Rung 1 and slice
2 measured the recorder they shipped only because their branch and the global
tool happened to agree; a rung that ships a new recorder would have reported
main's numbers under its own name. Fixed before any of the three ran here
(§2.3), default unchanged so the earlier readings stay reproducible.

**Gap 3 — E7″'s needle list cannot be applied as written.** §1's list
includes `Err`, `oid` and `chain`, and the instrument it inherits matches
needles as case-insensitive substrings. Under that reading `Err` is matched by
every `Error('…')` an answer prints, so the endpoint would STOP on any
transcript naming an exception type — it could not be passed by a correct
recorder. The reading was fixed before the count was taken (§2.3): those three
are matched word-bounded and case-sensitively, the six prose needles are not.
A pre-registered list of literals needs its matching rule pre-registered with
it; slice 2 hit the same edge on `python ?` and this is the second time.


**Gap 4 — on real code the modal AMBIGUOUS reason is the rules' last one,
and the shape behind it is an untraced catcher between two traced frames.**
Ungated, measured on the lens: of the 30 AMBIGUOUS shapes, **17** read
*"AMBIGUOUS -- no rule of this recorder reaches a verdict here"* (§3.3 rule
5's catch-all) and 13 read the escaped-handler reason. One of the 17 was
opened and diagnosed rather than guessed at: `Bomb raise Error('boom') L11`
in `20260910-150823-56b76a` is a RAISE whose frame (`Bomb`, f7) closed by
unwind, whose PARENT frame (f5, traced) closed by **return**, and for whose
serial there is **no HANDLED anywhere in the trace**. Rule 1 declines (not an
unhandled rejection), rule 2 declines (no later raise), rule 3 declines (no
absorbing handler), and rule 4 declines because the last unwind closes
neither a task root nor a frame whose parent is untraced — the parent is
traced and returned. What caught it is untraced code sitting INSIDE a traced
frame (a React error boundary, a vitest `toThrow`), which is the same blind
spot §6.1's Task-6 amendment already records for `translated` and
`test_failed`. **The rules decline instead of guessing, which is what keeps
E6-TS′'s gate at 0** — a rule that reached for a verdict here is exactly how a
false SWALLOWED would be minted — but "more than half of this lens's
ambiguous shapes are one un-named shape" is worth a name of its own before a
later rung decides whether it can be judged.
