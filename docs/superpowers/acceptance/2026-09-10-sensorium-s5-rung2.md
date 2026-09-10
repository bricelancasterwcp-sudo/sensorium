# S5 rung 2 — the throw flow: `exceptions` on a TypeScript trace: acceptance (pre-registered)

**Status: pre-registration only.** This file was written and committed on the
feature branch `feat/s5-rung2` **before any line of rung-2 code existed**. The
commit that carries it changes nothing under `src/`, `typescript/src/`,
`rust/` or `corpus/`: it is this document and nothing else. §1 is the locked
contract — after a number is read, no threshold moves, no arm is added and no
run is re-rolled; an infrastructure kill may be re-run from zero with the
reason recorded. §3's cells are all `not measured (rung 2 pending)` and stay
that way until the endpoints run. §4 and §5 are written by hand at the end of
the rung.

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

## 3. Results

Each cell is filled when its endpoint runs and reads `not measured (rung 2
pending)` until then. A cell that is never measured is a **missing file** the
assembler reports as `null` plus `dropped` — never an omission, never a blank
that reads as a pass.

| Id | What it answers | Cell | Verdict |
|---|---|---|---|
| E6-TS | the corpus's verdicts | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E6-TS′ | false accusation on the lens | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E8″ | the probes' shapes | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E2″ | every catch site instrumented | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E3-TS″ | the comparator does not cry wolf | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E5″ | both harnesses run | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E7″ | the reader's words | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E1‴ | what the product costs | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E10″ | what conversion costs | not measured (rung 2 pending) | not measured (rung 2 pending) |

§2.2's two census rows are **not** E2″. They are the instrument's dry runs at
T0, with the numerator missing by construction; E2″ is the row above and is
unmeasured.

## 4. Decisions

Written when the endpoints have run: one verdict per pre-registered endpoint,
with **the rule quoted from §1** beside the number that answered it, and the
verdict word taken from that rule and from nowhere else. Endpoints whose cells
have not run are named at the end.

## 5. Gaps found

Numbered as they are found; a later task appends rather than renumbers.
