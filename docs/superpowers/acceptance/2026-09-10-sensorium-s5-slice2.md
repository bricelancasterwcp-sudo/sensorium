# S5 slice 2 — E6″, the converter ladder, the `node --test` extensions: acceptance (pre-registered)

**Status: pre-registration only.** This file was written and committed on the
feature branch `feat/s5-slice2` **before any line of slice-2 code existed**.
The commit that carries it changes nothing under `src/`, `typescript/src/`,
`rust/` or `corpus/`: it is this document and nothing else. §1 is the locked
contract — after a number is read, no threshold moves, no arm is added and no
run is re-rolled; an infrastructure kill may be re-run from zero with the
reason recorded. §3's cells are all `not measured (slice 2 pending)` and stay
that way until the endpoints run. §4 and §5 are written by hand at the end of
the slice.

The lock is enforced by `tests/test_acceptance_s5_slice2_lock.py`, which
compares the working tree's §1 against the commit that first carried it and,
separately, compares each of §1's seven verbatim bodies against
`git show <sha>:<source>` — so "verbatim" is a claim a test holds, not one
this prose makes.

## 1. Pre-registration

Seven blocks, copied verbatim from the two documents that own them. Nothing
below this line is paraphrased, reordered or reworded; the only editorial act
is that each source section's own heading is carried as the `###` sub-heading
that introduces its body here (spec §11's heading is `##` in its source file
and appears as `###` below), so that this record keeps its own §1–§5
numbering. The bodies are byte-for-byte the source sections. Sources, at the
commits named:

- `docs/superpowers/specs/2026-09-10-sensorium-s5-slice2-design.md` at **`bbd0781`** (the merge commit on `main` that this branch was cut from) — `### 2.2 The rule`, `### 3.2 Arm 0 — diagnosis on main's code`, `### 3.4 The rules`, `### 3.5 The equivalence gate`, `### 4.5 Probes and the checker`, `## 11. The pre-registration, in one table`
- `docs/superpowers/plans/2026-09-10-sensorium-s5-slice2.md` at **`9c81dfe`** (this branch's first commit, the plan) — `## Pre-registration (…)`, up to `## File structure`

### 2.2 The rule

Four clauses, a flat conjunction as E6′ was; a clause that does not hold is a
**STOP**, and the pre-registration carries no other word for it.

| Clause | Measured | Holds when |
|---|---|---|
| manifest identical | `sha256sum -c` after the after arm | exit 0, 748 OK, 0 FAILED |
| the suite is the suite | every plain run's counts | every run reads `372 passed (372)` and `4278 passed (4278)`; a run that does not is **dropped and named**, never averaged in |
| 0 markers | the grep over every cache directory that exists | 0 hits, ≥1 directory searched |
| wrapper gone | `node_modules/.sensorium` | absent |
| **the plain band** | medians of the two arms' walls | `median(after) ∈ [median(before) − range(before), median(before) + range(before)]`, where `range = max − min` over the before arm's usable walls |

**Derivation of the band.** The before arm's own median, plus or minus the
spread the before arm itself measured. No multiplier, no chosen width: the
arm's range is a number the session produced, not one this document picked.
On E1′'s plain arm — walls 22.3136, 22.3252, 22.5925, 22.6142, 22.7221 — that
would read **22.5925 ± 0.4085**. Stated openly: E6′'s single wall, 22.8678,
would sit inside that band; that is not why the band has this shape. The band
is fixed before the after arm runs, from an arm the after arm cannot
influence, and it is the after arm's **median over five guarded runs** that
must land in it — not one wall.

**Fewer than four usable walls in either arm** (dropped runs, guard
refusals) makes the timing clause a **STOP by instrument**: the band or the
median was not measured, and an unmeasured clause is not a held one.

### 3.2 Arm 0 — diagnosis on main's code

Measured on the T0 commit, **before any converter change**, so the ladder
has a baseline taken under the same guard as its rungs.

| Cell | What | n | Prediction (from §0's profile; to be falsified) |
|---|---|---|---|
| 0a | the largest spool alone, `--jobs 1`, one-spool copy | 3 | ≈ 16 s |
| 0b | the full set, `--jobs 1` | 3 | 40–50 s: the sum of every spool's serial cost plus per-spool setup |
| 0c | the full set, `--jobs 4` | 3 | between 0b and 0d |
| 0d | the full set, `--jobs 16` (E10's own cell, now guarded) | 3 | ≈ 45 s |
| 0e | the one file, default jobs | 5 | ≈ 0.36 s |

**Two readings are pre-stated so the number decides between them.** If 0d
is not well below 0b, the pool buys nothing and the mechanism is contention
or serialisation between workers — A1 is the right first lever. If 0d ≈ 0a,
there is no contention: the floor is the largest spool's own serial cost, and
the lever is the per-record cost (A4), not the write path. Reported, no
verdict.

### 3.4 The rules

| Clause | Measured | Rule |
|---|---|---|
| **full suite** | the median of **n=5** guarded repetitions of `sensorium ts ingest` at the default job count over the pinned set, on the slice's final converter | ≤ **22.5925 s** → **PASS**, the converter stays Python; above → **REPORTED** with every rung of the ladder (0a–0e and each lever's cells), and Arm B is a later slice by ruling. No STOP word on this clause: E10's rule carried none, and a cost is a fact with its `n` beside it |
| **the one file** | the median of n=5 guarded repetitions over the pinned one-file spool | ≤ **0.3638 × 1.10 = 0.4002 s** → **PASS**; above → **STOP**. A converter faster on the suite and slower on the workload the loop pays is the failure the ledger's E10 row warned about, and it is the one thing on this ladder that is allowed to stop it |
| **equivalence** | §3.5 | 372 MATCH, 0 DIVERGED, 0 REFUSED → PASS; anything else → **STOP** |

### 3.5 The equivalence gate

A converter that is faster and different has changed the trace, and the
trace is the product. The full-suite set is converted twice: once by **main's
converter at the T0 commit** (the tree before any lever) into store A, once
by **the slice's final converter** into store B, both from fresh copies. The
372 traces are paired by spool file name (each `run:` line prints its
`file:`), and `sensorium diff <A> <B>` runs once per pair. **372 MATCH, 0
DIVERGED, 0 REFUSED**, or STOP. The same spool goes in on both sides, so the
lens's eight nondeterministic test files cannot excuse a DIVERGED here: a
difference is the converter's. Reported beside it, ungated: per-table row
counts equal for every pair (`events`, `frames`, `tasks`, `code_objects`,
`fingerprints`, `task_fingerprints`, `output`), and the meta keys that differ
between the pairs are exactly the minted ones (`run_id` and what derives from
it).

### 4.5 Probes and the checker

Under `typescript/probes/nodetest/`, one test file per extension, run by
`npm run probe:nodetest` as an explicit file list (Node's default test
patterns are not relied on):

| File | Expected |
|---|---|
| `async.probe.test.ts` | as today: a spool, its tasks, the checker's async checks |
| `ext.probe.test.mts` | a spool with ≥1 task, types stripped by Node, `task_name_basis: lexical` |
| `ext.probe.test.mjs` | a spool with ≥1 task |
| `ext.probe.test.cjs` | **no spool** for that pid; its `_tally-<pid>.json` reads `files_transformed: 0`, `excluded: {commonjs: 1}` |

And two **controls**, not test files, run by `probes/nodetest/controls.mjs`
twice each — plain `node <file>` and `node --import ../src/register.mjs
<file>` with `SENSORIUM_TS_ROOT` and `SENSORIUM_TS_PKG` set, since
`register.mjs` refuses without them — comparing the error code strings:

| Control | Expected on both sides |
|---|---|
| `controls/enum.ts` | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` |
| `controls/jsx.tsx` | `ERR_UNKNOWN_FILE_EXTENSION` |

A mismatch between the two sides is a refusal from `controls.mjs` — the
recorder changed what loads. `check.mjs`'s nodetest mode gains one check per
row above. `tests/test_ts_live.py` drives the same directory through the
driver, and gains the R45 case: a root whose only test file is `.cjs`
refuses at exit 2 with §4.3's sentence.

### 11. The pre-registration, in one table

Carried verbatim into the record's §1 at T0 and byte-locked there.

| Id | Question | Measurement | Rule |
|---|---|---|---|
| E6″ | Is a plain run contaminated? | five guarded plain runs, one call run, five guarded plain runs; manifest after; markers; wrapper | manifest 748 OK / 0 FAILED; every run 372/4278 or dropped and named; 0 markers with ≥1 directory searched; wrapper absent; `median(after)` inside `median(before) ± range(before)`; <4 usable walls in an arm → STOP by instrument; any clause failing → STOP |
| E10′-suite | What does full-suite conversion cost? | n=5 guarded `ingest` at default jobs over the pinned f08e89 copy, final converter | ≤ 22.5925 s → PASS (Python stays); above → REPORTED with the whole ladder; Arm B deferred by ruling |
| E10′-file | What does one file cost? | n=5 guarded `ingest` over the pinned 611,016-byte spool | ≤ 0.4002 s → PASS; above → STOP |
| E10′-eq | Did the converter change the trace? | 372 pairs, main@T0 vs final, `sensorium diff` each | 372 MATCH / 0 DIVERGED / 0 REFUSED → PASS; else STOP |
| E10′-0 | Where do the seconds go? | Arm 0 cells 0a–0e on the T0 tree | reported against §3.2's predictions; no verdict |
| H-probes | Does `node --test` load what plain loads? | §4.5's four files and two controls | every row as its table says; a control mismatch → STOP |

### Plan section "Pre-registration (Task 0 commits spec §2.2, §3.2, §3.4, §3.5, §4.5 and §11 verbatim as the record's §1, plus these pins)" — verbatim

- **The full-suite set:** `/mnt/extra/sensorium-s5/store-rung1/acceptance/spool/20260909-160038-f08e89/` — 372 `.jsonl`, 414,450,522 bytes — copied whole (`invocation.json`, `harness.json`, `manifests/` included, `ingested.json` removed from the copy) to `/mnt/extra/sensorium-s5/e10-spool/f08e89/`; `sha256sum` over every file in the copy written to `/mnt/extra/sensorium-s5/e10-spool/f08e89.sha256` and its own sha256 quoted in §2.
- **The one file:** `20260909-155657-4965c3/1478098-0.jsonl` (611,016 bytes) with its directory's three JSON siblings, to `/mnt/extra/sensorium-s5/e10-spool/one/`; pinned the same way.
- **The big-spool copy for cell 0a:** `/mnt/extra/sensorium-s5/e10-spool/big/` holding only `1491993-0.jsonl` (195,851,484 bytes, `src/lib/map/gridDetect.test.ts`) plus the set's `invocation.json`, `harness.json`, `manifests/`.
- **The reference wall:** 22.5925 s (E1′'s plain median). **The one-file bound:** 0.4002 s. **Job counts:** 1, 4, 16 (16 = `os.cpu_count()` here, the driver's default).
- **The rung-1 manifest:** `/mnt/extra/sensorium-s5/manifest-rung1-before.txt` (748 entries, file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`), verified once at T0 and again by `e6pp.sh` before and after its own runs.
- **Reported without a gate:** spec §3.6 — events/s per rung on the big spool, peak RSS before/after A3, 0b/0d, the call run's harness and driver walls, the fresh set's ingest.

## 2. Ambient pins (preflight, recorded before any slice-2 code exists)

Every value below is the output of the command beside it, run on this box on
2026-09-09 between 22:39 and 22:51 local time (`-05:00`) — the session that
opens slice 2, which the plan and the spec date 2026-09-10 — before any file
under `src/`, `typescript/src/`, `rust/` or `corpus/` was touched. The lens is
the VTT frontend **copy** at `/mnt/extra/sensorium-s5/vtt/frontend` (VTT
`0091e97`); `~/workspace/projects/vtt` was neither read nor touched, and the
lens was read here by nothing but `sha256sum -c`. Box paths appear in this
table because a pin without its location is not a pin; the rule that no box
path is committed binds the results JSON and the code, as it did at rung 1.

| Item | Command | Value |
|---|---|---|
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| lens vitest | `node -e "console.log(require('<lens>/node_modules/vitest/package.json').version)"` | `4.1.9` |
| lens vite | same, `vite` | `6.4.3` |
| lens typescript | same, `typescript` | `5.9.3` |
| lens jsdom | same, `jsdom` | `29.1.1` |
| nproc | `nproc` | `16` — also the driver's default job count, so E10′'s `--jobs 16` cell is the default cell |
| governor | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | `powersave` |
| memory | `free -g` | total `29`, used `17`, free `9`, buff/cache `7`, available `12`; swap total `15`, used `0` (preflight). At pin time: free `8`, buff/cache `8`, available `12` |
| free disk `/` | `df -h /` | `4.9G` available on `/dev/nvme0n1p2` (100% used, 915G total) — the refusal floor is 3 GB; this passes with 1.9 GB to spare, and nothing this slice measures writes to `/` |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `64G` available on `/dev/nvme1n1p1` (86% used, 469G total) — the refusal floor is 8 GB; this passes with 56 GB to spare |
| mount `/` | `findmnt -no SOURCE,FSTYPE /` | `/dev/nvme0n1p2 ext4` |
| mount `/mnt/extra` | `findmnt -no SOURCE,FSTYPE /mnt/extra` | `/dev/nvme1n1p1 ext4` — a different block device and filesystem; the worktree, the venvs, the lens, the spool copies and every store live here |
| 1-minute load, preflight | `cat /proc/loadavg` (before anything was created or copied) | `0.94 0.67 0.58 1/2581 2223272` — 1-minute load **0.94**, under the 4.0 refusal threshold |
| 1-minute load, at pin time | `date -Iseconds; cat /proc/loadavg` | `2026-09-09T22:50:39-05:00`, then `0.90 1.12 0.87 1/2602 2267193` — the close of this table's reading window |
| worktree | `git rev-parse --abbrev-ref HEAD` | `feat/s5-slice2`, at `/mnt/extra/sensorium-rung2/s5-slice2`, cut from `main` at `bbd0781` |
| `git rev-parse HEAD` | `git rev-parse HEAD` | `9c81dfe666bda4f6961dca8bc4d1404ad985a68b` — the plan commit, this branch's only commit when the pins were taken. **T0** for every "main's converter" arm is this tree |
| worktree venv | `uv venv .venv --python 3.13 && uv pip install -p .venv/bin/python -e ".[dev]"` | `.venv/bin/python -V` → `Python 3.13.13` |
| 3.12 venv | `uv venv .venv312 --python 3.12 && uv pip install -p .venv312/bin/python -e ".[dev]"` | `Python 3.12.13` |
| 3.14 venv | `uv venv .venv314 --python 3.14 && uv pip install -p .venv314/bin/python -e ".[dev]"` | `Python 3.14.4` |
| sensorium, worktree venv | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.9.0` |
| sensorium, global tool | `$(dirname $(readlink -f $(which sensorium)))/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` (the tool venv under `~/.local/share/uv/tools/sensorium`) | `0.9.0` — the same version. The global tool is **never reinstalled from this worktree**: it is what Arm 0 and the equivalence gate's A side mean by "main's converter" |
| node installs | `npm ci --prefix typescript && npm ci --prefix typescript/probes && npm ci --prefix corpus/typescript` | `typescript/node_modules` 5 entries, `typescript/probes/node_modules` 65, `corpus/typescript/node_modules` 35 |
| store root | `mkdir -p /mnt/extra/sensorium-s5/store-slice2` | created; `SENSORIUM_DIR` for every trace this slice records or converts |
| lens manifest, verified | `cd <lens> && sha256sum -c /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | exit `0`, **748 OK, 0 FAILED** — the lens is byte-identical to the state rung 1 left it in. Manifest file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`, 748 lines, as the plan pins it |

### 2.1 The spool copies (E10′'s pinned workloads)

Made with `cp -r` from `/mnt/extra/sensorium-s5/store-rung1/acceptance/spool/`,
into `/mnt/extra/sensorium-s5/e10-spool/`. Each copy carries `invocation.json`,
`harness.json` and `manifests/`, and **no `ingested.json`** — the source's
ingest marker is dropped so a copy is a spool no converter has yet seen. (The
plan's bullet for `one/` says "its directory's three JSON siblings"; the same
bullet's rule for `f08e89/` says `ingested.json` is removed from the copy, and
`one/` is pinned "the same way", so all three copies are the two JSON siblings
plus `manifests/`. The deviation is named here rather than left to be noticed
later.)

Every value below is the output of the command beside it. `<c>` abbreviates
the copy `/mnt/extra/sensorium-s5/e10-spool/<name>/` and `<m>` its manifest
`/mnt/extra/sensorium-s5/e10-spool/<name>.sha256`; each manifest was written
by `cd <c> && find . -type f | sort | xargs sha256sum > <m>`.

| Copy | Source | Item | Command | Value |
|---|---|---|---|---|
| `e10-spool/f08e89/` | `20260909-160038-f08e89/` | `.jsonl` files | `ls <c>/*.jsonl \| wc -l` | `372` — the plan's pinned count (372 `.jsonl`), exactly |
|  |  | `.jsonl` bytes | `find <c> -maxdepth 1 -name '*.jsonl' -printf '%s\n' \| awk '{s+=$1} END{print s}'` | `414450522` — the plan's pinned number, exactly |
|  |  | all-file bytes | `find <c> -type f -printf '%s\n' \| awk '{s+=$1} END{print s}'`, cross-checked against `du -sb <c>` (agrees) | `415578161` |
|  |  | `manifests/` files | `ls <c>/manifests \| wc -l` | `726` |
|  |  | manifest lines | `wc -l < <m>` | `1100` |
|  |  | manifest sha256 | `sha256sum <m>` | `bcefbbd367e50e6f1adbd6c6c76172fcadd4235e0fd72b3264c6dc8a11d40844` |
|  |  | manifest re-verified | `cd <c> && sha256sum -c <m>` | `1100 OK, 0 FAILED` |
| `e10-spool/one/` | `20260909-155657-4965c3/` | `.jsonl` files | `ls <c>/*.jsonl \| wc -l` | `1` (`1478098-0.jsonl`) |
|  |  | `.jsonl` bytes | `find <c> -maxdepth 1 -name '*.jsonl' -printf '%s\n' \| awk '{s+=$1} END{print s}'` | `611016` — the plan's pinned number, exactly |
|  |  | all-file bytes | `find <c> -type f -printf '%s\n' \| awk '{s+=$1} END{print s}'`, cross-checked against `du -sb <c>` (agrees) | `678355` |
|  |  | `manifests/` files | `ls <c>/manifests \| wc -l` | `25` |
|  |  | manifest lines | `wc -l < <m>` | `28` |
|  |  | manifest sha256 | `sha256sum <m>` | `e5be630f0b1e4efc3f8c4c240ffebc22d59abd9328875b885c1930baa1e2de23` |
|  |  | manifest re-verified | `cd <c> && sha256sum -c <m>` | `28 OK, 0 FAILED` |
| `e10-spool/big/` | `20260909-160038-f08e89/` | `.jsonl` files | `ls <c>/*.jsonl \| wc -l` | `1` (`1491993-0.jsonl`) |
|  |  | `.jsonl` bytes | `find <c> -maxdepth 1 -name '*.jsonl' -printf '%s\n' \| awk '{s+=$1} END{print s}'` | `195851484` — the plan's pinned number, exactly |
|  |  | all-file bytes | `find <c> -type f -printf '%s\n' \| awk '{s+=$1} END{print s}'`, cross-checked against `du -sb <c>` (agrees) | `196979123` |
|  |  | `manifests/` files | `ls <c>/manifests \| wc -l` | `726` |
|  |  | manifest lines | `wc -l < <m>` | `729` |
|  |  | manifest sha256 | `sha256sum <m>` | `20513b79c80d8a789ff99f037ba94212c2fa4e20d0bd33cb2ca7c6403f0d95a4` |
|  |  | manifest re-verified | `cd <c> && sha256sum -c <m>` | `729 OK, 0 FAILED` |

A copy whose manifest no longer verifies is not the workload these endpoints
were pre-registered against.

### 2.2 Suite baselines (the regression fence)

Taken on the pin commit `9c81dfe`, before any slice-2 change. Every later task
restores these exactly, or names what moved.

**The pytest rows grew by eight at `ecac114`, and that is part of the fence.**
Task 0's own second commit adds `tests/test_acceptance_s5_slice2_lock.py`:
seven tests in the file itself, plus one more case in `tests/test_ceiling.py`,
which is parametrized over every tracked non-exempt file and so gains a case
for that file (the record adds none — it sits in an exempt directory). Measured
on `ecac114`, not derived: `.venv/bin/python -m pytest -q` → `3436 passed, 29
skipped`; `.venv312/bin/python -m pytest -q` → `3432 passed, 33 skipped`;
`.venv314/bin/python -m pytest -q` → `3440 passed, 25 skipped`. **From
`ecac114` onward those are the counts a later task restores.** Reading the
`9c81dfe` row instead — `3428 passed, 29 skipped` on 3.13 — does not mean the
fence held; it means the lock file is gone, which is the one way this
pre-registration could be unlocked while every suite still reported green.

| Suite | Command | Baseline at `9c81dfe` | The fence, from `ecac114` |
|---|---|---|---|
| pytest, 3.13 | `.venv/bin/python -m pytest -q` | `3428 passed, 29 skipped` (92.46 s) | `3436 passed, 29 skipped` (92.03 s) |
| pytest, 3.12 | `.venv312/bin/python -m pytest -q` | `3424 passed, 33 skipped` (94.17 s) | `3432 passed, 33 skipped` (94.28 s) |
| pytest, 3.14 | `.venv314/bin/python -m pytest -q` | `3432 passed, 25 skipped` (96.00 s) | `3440 passed, 25 skipped` (95.06 s) |
| TypeScript unit | `npm --prefix typescript test` | `tests 164`, `pass 164`, `fail 0`, `skipped 0` | unchanged † |
| TypeScript types | `npm --prefix typescript run check` | exit `0`, no diagnostics (`tsc -p tsconfig.json`; never `npx tsc -p` from the root — R4) | unchanged † |
| corpus, TypeScript | `.venv/bin/python corpus/run_corpus.py --only-dir typescript --require-driver` | `13 cases, 35 questions, 0 failures, 0 error(s)` | unchanged † |
| corpus, root | `.venv/bin/python corpus/run_corpus.py --only-dir .` | `20 cases, 39 questions, 0 failures, 0 error(s)` | unchanged † |
| live TypeScript | `SENSORIUM_TS_LIVE=1 .venv/bin/python -m pytest -q tests/test_ts_live.py` | `9 passed` (2.05 s) | unchanged † |

† The three pytest cells in the last column are measured on `ecac114`. The five
marked `unchanged †` are **not** re-measured: Task 0 adds one Python test file
and one record, and none of these five enumerates either — `npm test` and
`tsc` see only `typescript/`, the corpus runner counts cases under `corpus/`,
and the live row names one test file. Any of them moving is a real regression,
not this commit's arithmetic.

## 3. Results

Every cell below is `not measured (slice 2 pending)` and stays that way until
the endpoint runs. A cell that is never measured is a **missing file** the
assembler reports as `null` plus `dropped` — never an omission, never a blank
that reads as a pass.

| Id | Cell | Rule (from §1) | Result |
|---|---|---|---|
| E6″ | the plain band | manifest 748 OK / 0 FAILED; every run 372/4278 or dropped and named; 0 markers with ≥1 directory searched; wrapper absent; `median(after)` inside `median(before) ± range(before)`; <4 usable walls in an arm → STOP by instrument | not measured (slice 2 pending) |
| E10′-suite | n=5 guarded `ingest`, default jobs, pinned `f08e89` copy, final converter | ≤ 22.5925 s → PASS; above → REPORTED with the whole ladder | not measured (slice 2 pending) |
| E10′-file | n=5 guarded `ingest` over the pinned 611,016-byte spool | ≤ 0.4002 s → PASS; above → STOP | not measured (slice 2 pending) |
| E10′-eq | 372 pairs, main@T0 vs final, `sensorium diff` each | 372 MATCH / 0 DIVERGED / 0 REFUSED → PASS; else STOP | not measured (slice 2 pending) |
| E10′-0 | 0a — the largest spool alone, `--jobs 1`, one-spool copy, n=3 | reported against §3.2's prediction (≈ 16 s); no verdict | not measured (slice 2 pending) |
| E10′-0 | 0b — the full set, `--jobs 1`, n=3 | reported against §3.2's prediction (40–50 s); no verdict | not measured (slice 2 pending) |
| E10′-0 | 0c — the full set, `--jobs 4`, n=3 | reported against §3.2's prediction (between 0b and 0d); no verdict | not measured (slice 2 pending) |
| E10′-0 | 0d — the full set, `--jobs 16`, n=3 | reported against §3.2's prediction (≈ 45 s); no verdict | not measured (slice 2 pending) |
| E10′-0 | 0e — the one file, default jobs, n=5 | reported against §3.2's prediction (≈ 0.36 s); no verdict | not measured (slice 2 pending) |
| H-probes | §4.5's four probe files and two controls | every row as its table says; a control mismatch → STOP | not measured (slice 2 pending) |

**Reported without a gate** (spec §3.6): events/s per rung on the big spool,
peak RSS before and after A3, 0b and 0d, the call run's harness and driver
walls, and the fresh set's ingest — all `not measured (slice 2 pending)`.

## 4. Decisions

*Written by hand at the end of the slice.*

## 5. Gaps found

*Written by hand at the end of the slice.*
