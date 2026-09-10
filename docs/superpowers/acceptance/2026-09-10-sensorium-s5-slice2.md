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

Each cell is filled when its endpoint runs and reads `not measured (slice 2
pending)` until then. A cell that is never measured is a **missing file** the
assembler reports as `null` plus `dropped` — never an omission, never a blank
that reads as a pass. **Filled so far:** E10′-0's five cells and the three
§3.6 quantities Arm 0 supplies — measured 2026-09-09 on the global tool at
main `bbd0781`, detail and reading in §3.1 — and the ladder's **a1** rung
(0a, 0d, 0e re-measured on the worktree's converter at `2a273cf`), detail
and its three falsified predictions in §3.2.

| Id | Cell | Rule (from §1) | Result |
|---|---|---|---|
| E6″ | the plain band | manifest 748 OK / 0 FAILED; every run 372/4278 or dropped and named; 0 markers with ≥1 directory searched; wrapper absent; `median(after)` inside `median(before) ± range(before)`; <4 usable walls in an arm → STOP by instrument | not measured (slice 2 pending) |
| E10′-suite | n=5 guarded `ingest`, default jobs, pinned `f08e89` copy, final converter | ≤ 22.5925 s → PASS; above → REPORTED with the whole ladder | not measured (slice 2 pending) |
| E10′-file | n=5 guarded `ingest` over the pinned 611,016-byte spool | ≤ 0.4002 s → PASS; above → STOP | not measured (slice 2 pending) |
| E10′-eq | 372 pairs, main@T0 vs final, `sensorium diff` each | 372 MATCH / 0 DIVERGED / 0 REFUSED → PASS; else STOP | not measured (slice 2 pending) |
| E10′-0 | 0a — the largest spool alone, `--jobs 1`, one-spool copy, n=3 | reported against §3.2's prediction (≈ 16 s); no verdict | **17.5439 s** median, n=3, 17.3953 – 27.3839; 1-min loads 0.29/0.73/0.86; peak RSS 2,273,872 kB; the global tool, main `bbd0781` — §3.1 |
| E10′-0 | 0b — the full set, `--jobs 1`, n=3 | reported against §3.2's prediction (40–50 s); no verdict | **154.3012 s** median, n=3, 152.7924 – 154.5061; 1-min loads 3.62/2.32/2.19; peak RSS 2,272,256 kB; the global tool, main `bbd0781` — §3.1 |
| E10′-0 | 0c — the full set, `--jobs 4`, n=3 | reported against §3.2's prediction (between 0b and 0d); no verdict | **67.9342 s** median, n=3, 67.1653 – 67.9709; 1-min loads 0.82/3.5/3.78; peak RSS 2,270,804 kB; the global tool, main `bbd0781` — §3.1 |
| E10′-0 | 0d — the full set, `--jobs 16`, n=3 | reported against §3.2's prediction (≈ 45 s); no verdict | **45.7378 s** median, n=3, 43.5478 – 45.8268; 1-min loads 2.09/3.97/3.79; peak RSS 2,269,696 kB; the global tool, main `bbd0781` — §3.1 |
| E10′-0 | 0e — the one file, default jobs, n=5 | reported against §3.2's prediction (≈ 0.36 s); no verdict | **0.3624 s** median, n=5, 0.2736 – 0.4051; 1-min loads 0.96/0.96/0.96/0.96/0.96; peak RSS 30,828 kB; the global tool, main `bbd0781` — §3.1 |
| H-probes | §4.5's four probe files and two controls | every row as its table says; a control mismatch → STOP | not measured (slice 2 pending) |

**Reported without a gate** (spec §3.6). Measured on Arm 0 (§3.1): **0b/0d
= 154.3012 / 45.7378 = 3.3736×**, the parallel speedup on main's converter;
**128,053 events/s** on the big spool at this rung (2,246,552 events in
17.5439 s, cell 0a); and **2,273,872 kB** peak resident in the heaviest
worker before A3 (cell 0a; the other three full-set cells read within 0.2%
of it).
After A1 (§3.2), on the worktree's converter at `2a273cf`: **152,851
events/s** on the big spool (2,246,552 events in 14.6977 s), and peak
resident unmoved at 2,273,996 kB (0a) / 2,270,016 kB (0d).
Still `not measured (slice 2 pending)`: events/s on the rungs after A1, peak
RSS after A3, the call run's harness and driver walls, and the fresh set's
ingest.

### 3.1 E10′ Arm 0 — the diagnosis on main's converter

Measured 2026-09-09 between 23:23 and 23:39 local time (`-05:00`) by
`typescript/acceptance/e10p.sh`: E10's instrument with the load guard record
§5 gap 5 said it lacked, the job count as an argument, and the peak resident
size of the heaviest worker taken through `rss_run.py`. Each repetition
copies the pinned §2.1 spool copy and converts the copy into a fresh store,
both made and removed **outside** the timed region, exactly as `e10.sh` did.

**The converter is the global tool, main `bbd0781`** — the 0.9.0 converter
§2 pins, never reinstalled from this worktree, which is what "main's code"
means for this arm and for the equivalence gate's A side. Every cell's JSON
carries `converter_bin` and `converter_rev`; `converter_rev` is
`bbd07816c9c769307b5fb0a17f37f51707d419ad` in all five.

The cells ran in the order 0a, 0e, 0c, 0b, 0d — cheapest first, so an
instrument defect would have surfaced on a one-minute cell rather than a
seven-minute one. **Nothing was dropped:** all seventeen repetitions exited
`0` and converted exactly the copy's `.jsonl` count (1, 1, 372, 372, 372), so
every cell's `n` is the count it asked for.

| Cell | Workload | jobs | n | Prediction (§1) | Median | min – max | 1-min load per rep | Peak RSS, heaviest worker |
|---|---|---|---|---|---|---|---|---|
| 0a | `big/` — 1 spool, 195,851,484 B | 1 | 3 | ≈ 16 s | **17.5439 s** | 17.3953 – 27.3839 | 0.29, 0.73, 0.86 | 2,273,872 kB |
| 0b | `f08e89/` — 372 spools, 414,450,522 B | 1 | 3 | 40–50 s | **154.3012 s** | 152.7924 – 154.5061 | 3.62, 2.32, 2.19 | 2,272,256 kB |
| 0c | `f08e89/` | 4 | 3 | between 0b and 0d | **67.9342 s** | 67.1653 – 67.9709 | 0.82, 3.5, 3.78 | 2,270,804 kB |
| 0d | `f08e89/` | 16 | 3 | ≈ 45 s | **45.7378 s** | 43.5478 – 45.8268 | 2.09, 3.97, 3.79 | 2,269,696 kB |
| 0e | `one/` — 1 spool, 611,016 B | 16 | 5 | ≈ 0.36 s | **0.3624 s** | 0.2736 – 0.4051 | 0.96 (all five) | 30,828 kB |

Two predictions land, one lands near, one holds, one is falsified. 0e is 0.3624 s against ≈ 0.36 s and 0d is 45.7378 s against
≈ 45 s. 0a is 17.5439 s against ≈ 16 s, 9.6% high, and its third repetition
at 27.3839 s is the single outlier in the whole arm — kept, because the rule
drops a repetition for a non-zero status or a wrong trace count and for
nothing else, and the median is what the cell quotes. 0c is between 0b and
0d, as predicted. **0b is 154.3012 s against a predicted 40–50 s — a little
over three times the prediction** — and it is the cell that moves the
reading.

**The two readings pre-stated in §1** (spec §3.2), quoted before either is
named:

> If 0d is not well below 0b, the pool buys nothing and the mechanism is
> contention or serialisation between workers — A1 is the right first lever.

> If 0d ≈ 0a, there is no contention: the floor is the largest spool's own
> serial cost, and the lever is the per-record cost (A4), not the write
> path.

**Neither antecedent holds, and the numbers say which way each fails.** 0d
is well below 0b — 45.7378 s against 154.3012 s, a **3.3736×** speedup — so
the pool does buy something and the first reading's premise is false as
stated. 0d is not ≈ 0a either — 45.7378 s is **2.607×** the 17.5439 s the
largest spool costs on its own, 28.19 s above that floor — so the second
reading's premise is false as well. What Arm 0 reports instead is a pool
with a real but poor return, 3.3736× from sixteen workers and 2.2713× from
the first four (0c, 67.9342 s), stalling well above the floor the largest
spool sets. Both mechanisms the two readings separate are therefore still
live: there is contention, or sixteen workers would scale nearer sixteen;
and there is a serial floor, or 0d would sit nearer 0a. Arm 0 does not
choose between them, and this paragraph does not either — the levers earn
their verdicts on their own cells. A **reading, not a verdict**: the plan's
order (A1, then A3) is unchanged by this arm, which neither confirmed nor
removed its premise, and §3.7's "0d ≈ 0a" trigger for revisiting Arm C did
not fire.

Ungated beside it: the heaviest worker peaks at 2,269,696–2,273,872 kB —
about 2.2 GiB — on every full-set cell and on the one-spool `big/` cell
alike, the four spread across 0.2% at every job count, and at 30,828 kB
(about 30 MiB) on the one small file. The largest spool
sets the memory high-water mark whatever the job count, which is the reading
A3's prediction ("from the order of a gigabyte to the order of 100 MB") is
aimed at.

**Two properties of the instrument, written down now so a later rung is not
surprised by them.** (1) The timed region is the `rss_run.py` wrapper around
`ingest`, so every wall carries that wrapper's own interpreter start-up.
`rss_run.py` prints `child_wall` — its clock around `subprocess.run` alone —
into each log for exactly this reason: across all seventeen repetitions the
difference is **0.013–0.022 s**, median 0.0162 s, which is 4.5% of cell 0e's
median and under 0.1% of every other cell's. The record quotes the whole
timed region, which is what the pre-registered instrument measures. (2) The
guard admitted repetitions at 1-minute loads of 3.97, 3.79, 3.78 and 3.62 —
the decay of the instrument's **own** previous repetition, not another
tenant. On sixteen cores a 4.0 threshold sits below what a `--jobs 16` cell
generates, so back-to-back repetitions wait only until the previous one's
average has decayed past it, not until the box is idle. The threshold is
pre-registered and was not moved; every reading is in its cell's `loads`.

### 3.2 E10′ A1 — one transaction per trace, `synchronous=NORMAL`

Measured 2026-09-10 by the same `typescript/acceptance/e10p.sh`, on the same
three pinned workloads, under the same guard, in the order 0e, 0a, 0d
(cheapest first). **The converter is the worktree's own
`.venv/bin/sensorium` at `feat/s5-slice2` `2a273cf`** — main `bbd0781` plus
this slice's commits, of which exactly one touches `src/`: `TraceWriter`
gains `durable=False`, which sets `PRAGMA synchronous=NORMAL` under the WAL
`create_trace` already sets and commits once, in `close()`, instead of once
per 512-event batch and once per `set_meta` / fingerprint write. `Builder`
passes it; the Python recorder keeps the durable default. Every cell's JSON
carries `converter_rev`
`2a273cf52de31d009d3d44067e12add2cee5b5ec`. **Nothing was dropped:** all
eleven repetitions exited `0` and converted exactly the copy's `.jsonl`
count (1, 1, 372).

**The ladder.** Each cell is the same workload at the same job count, one
row per rung; `arm0` is §3.1's, repeated here so the two are read together.

| Stage | Cell | jobs | n | Median | min – max | 1-min load per rep | Peak RSS, heaviest worker | Converter |
|---|---|---|---|---|---|---|---|---|
| arm0 | 0a — `big/`, 1 spool, 195,851,484 B | 1 | 3 | 17.5439 s | 17.3953 – 27.3839 | 0.29, 0.73, 0.86 | 2,273,872 kB | the global tool, main `bbd0781` |
| **a1** | 0a — `big/` | 1 | 3 | **14.6977 s** | 14.6106 – 14.8340 | 0.58, 0.75, 0.80 | 2,273,996 kB | the worktree's venv, `feat/s5-slice2` `2a273cf` |
| arm0 | 0d — `f08e89/`, 372 spools, 414,450,522 B | 16 | 3 | 45.7378 s | 43.5478 – 45.8268 | 2.09, 3.97, 3.79 | 2,269,696 kB | the global tool, main `bbd0781` |
| **a1** | 0d — `f08e89/` | 16 | 3 | **17.7740 s** | 17.4102 – 17.9927 | 0.78, 1.84, 2.96 | 2,270,016 kB | the worktree's venv, `feat/s5-slice2` `2a273cf` |
| arm0 | 0e — `one/`, 1 spool, 611,016 B | 16 | 5 | 0.3624 s | 0.2736 – 0.4051 | 0.96 (all five) | 30,828 kB | the global tool, main `bbd0781` |
| **a1** | 0e — `one/` | 16 | 5 | **0.1647 s** | 0.1646 – 0.1902 | 0.66, 0.66, 0.68, 0.68, 0.68 | 31,372 kB | the worktree's venv, `feat/s5-slice2` `2a273cf` |

A1 moves every cell: 0a by **1.1936×** (2.8462 s gone), 0d by **2.5733×**
(27.9638 s gone), 0e by **2.2004×** (0.1977 s gone).

**The three predictions spec §3.3 wrote before the code, quoted, each
against the number that answered it. All three are falsified.**

| A1 prediction (spec §3.3) | Measured | Held? |
|---|---|---|
| "0a ≤ **13.5 s** (the 2.7 s of commits gone)" | **14.6977 s** | **No** — 1.1977 s above the bound |
| "0d ≤ 0a + 3 s (the contention gone with the fsyncs)" | **17.7740 s** against a bound of 17.6977 s (0a + 3) | **No** — 0.0763 s above it, 0.43% |
| "0e unchanged" | **0.1647 s** against arm0's 0.3624 s | **No** — 2.2004× faster, not unchanged |

The three fail differently, and one of them fails in the fast direction.
**0a** removed 2.8462 s where the prediction attributed 2.7 s to commits,
but its bound was absolute (13.5 s) and was written against a predicted 0a
of ≈ 16 s while Arm 0 measured 17.5439 s — 1.5439 s of the 1.1977 s miss is
the base the subtraction started from. The bound is missed all the same.
**0d** misses by 76 ms after removing 27.9638 s, on a bound that moved down
with 0a; what the cell shows beside the miss is that 0d is now **1.2093×**
0a rather than Arm 0's 2.607× — the gap to the largest spool's serial cost
is 3.0763 s, not 28.1939 s. **0e** is the prediction that fails on its
face: the one-file cell was not commit-free, it was commit-*dominated*, and
more than half of its 0.3624 s was commits — a 611 KB spool pays the same
~35 finalize fsyncs a 195 MB one does. No threshold moved and no cell was
re-rolled; these are the numbers the pre-registered cells produced. Whether the remaining cost is A3's or A4's is
those rungs' to measure, and the gated clauses (E10′-suite, E10′-file,
E10′-eq) are measured on the slice's final converter at their own `n` and
are still `not measured (slice 2 pending)` above.

Ungated beside it: **152,851 events/s** on the big spool at this rung
(2,246,552 events in 14.6977 s), against Arm 0's 128,053. Peak resident is
unmoved — 2,273,996 kB on 0a and 2,270,016 kB on 0d, within 0.2% of Arm 0's
readings, which is expected: A1 changes when rows are committed, not how
many are held. RSS is A3's quantity.

One instrument note, following §3.1's: the wrapper's own interpreter
start-up is now a larger share of the 0e cell, because the cell shrank.
`child_wall` across those five repetitions is 0.1503–0.1732 s against walls
of 0.1646–0.1902 s — a median difference of 0.0143 s, **8.7%** of the
cell's median (it was 4.5% at Arm 0). The record quotes the whole timed
region, as pre-registered; the gated E10′-file clause (≤ 0.4002 s) has
0.2355 s of headroom at this rung either way. Every repetition's
`maxrss_kb` parsed (no cell reports a 0).

## 4. Decisions

*Written by hand at the end of the slice.*

## 5. Gaps found

*Written by hand at the end of the slice.*
