# S5 rung 1 — TypeScript recorder v1: acceptance (pre-registered)

**Status: pre-registration only.** This file was written and committed on
2026-09-09 **before any line of the TypeScript recorder existed**. The commit
that carries it also carries the `typescript/` package skeleton — a
`package.json`, a `tsconfig.json`, a `.gitignore`, the committed
`package-lock.json`, an empty `test/`, and a single placeholder
`src/index.mjs` whose whole content is `export const VERSION = '0.1.0';`
(without one file `tsc` refuses the empty include set with TS18003). No
transform, no runtime, no driver, no reader change. §1 is the locked contract:
after a number is read, no threshold moves, no arm is added and no run is
re-rolled. §3's cells are all `not measured (rung 1 pending)` and stay that way
until the endpoints run. §4 and §5 are written by hand at the end of the rung.

## 1. Pre-registration

Three blocks, copied verbatim from the two documents that own them. Nothing
below this line is paraphrased, reordered or reworded; the only editorial act
is that each source section's own heading, which is `##` in its source file, is
carried as the `###` sub-heading that introduces its body here, so that this
record keeps its own §1–§5 numbering. The bodies are byte-for-byte the source
sections. Sources, at the commit this record is committed on top of
(`216bfd8ffd9ad3718db0f3fe0d7954e8beb2cdfe`):

- `docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md` — `## 8. Pre-registered endpoints for rung 1 (product acceptance)` and `## 10. First use`
- `docs/superpowers/plans/2026-09-09-sensorium-s5-rung1-recorder-v1.md` — `## Pre-registration (…)`, up to `## File structure`

### Spec `## 8. Pre-registered endpoints for rung 1 (product acceptance)` — verbatim

Written here before the product exists; the plan carries them verbatim and
the acceptance record quotes each rule beside its number. **Lens:** the
spike's — the VTT frontend copy at `0091e97` under
`/mnt/extra/sensorium-s5/vtt/`, vitest 4.1.9, Node 24.16, this box, store
under `/mnt/extra`, nothing on the root disk. **Control arm:** the spike's
instrument on the same lens (its numbers below are that arm). Stop rules as
the spike's: 1-minute load above 4.0 → wait; an arm with fewer than 5 runs
or a suite not at 372/4278 → `value: null`, named in `dropped`; no endpoint
re-run after its number is read.

| Id | Question | Measurement | Rule | Derivation |
|---|---|---|---|---|
| E0′ | Is the trace unit still the test file under the product? | containers, files per container, full suite at tier `call` | 372 containers, one file each; any container with two files or any file with none → STOP | E0's measured shape, now a claim |
| E1′ | What does the product cost? | walls n=5 per arm, interleaved plain/off/call, conversion excluded | off/plain ≤ 1.10 → the transform stays uncached; above → a cache keyed on source sha becomes rung-1 work, not a NO-GO; call/plain reported beside the spike's 1.131 | E1's bound, reused; the product adds a setup file, a name provider and the `yield` rewrite, none of which the spike had |
| E2′ | Does the transform still cover the consumer? | instrumented / eligible over the census set, per node kind, with every exclusion named | after removing NAMED kinds the ratio is 1.000 (5,403 of 5,403 was measured); one unnamed miss → STOP | a measured 100% may not regress silently |
| E3-TS | False DIVERGED? | one pre-named VTT test file recorded 20 times; `diff` each against the first | DIVERGED 0/19 and REFUSED 0/19; any → the comparator or the recorder is wrong, STOP | the Rust E3 rule, per-task basis |
| E4′ | Do sites keep their lines and columns? | the 20-shape probe under the product transform; one planted failing assertion's line and column as vitest reports it, instrumented against plain | 20/20 on the exact line; the report byte-identical; a miss is a regression of a measured 20/20 → STOP | E4, tightened from 19/20 because the number is now known |
| E5′ | Do both harnesses run? | the full suite under `sensorium ts run -- vitest run` (gate); the E3 probe under `-- node --test` | 372/4278 green and `node --test` green with its rows; a red vitest is NO-GO | E5 |
| E6′ | Is a plain run contaminated? | sha256 manifest before/after, plain counts after, marker grep of every cache dir, listing of `node_modules/.sensorium` after | manifest identical, 372/4278 inside the plain band, 0 markers, the wrapper directory gone | E6, plus the wrapper's removal |
| E7′ | Does the reader speak this recorder's words? | every command run on a product trace; transcript grepped for `asyncio`, `python ?`, `cargo`, `coroutine`, `Python's own`, `threading/_thread`, `Rust disposition`, `sensorium run --focus` | 0 occurrences; plus `v23`/`v24` green | E7's leak list, now a gate |
| E8′ | Are the five swallow shapes still seen? | the swallow probe | 5/5, reported per shape; rung 2 gates the rules | E8 |
| E9 | Are tests tasks, and named as vitest names them? | `tests_seen`, tasks, `task_name_conflicts` over the full suite; a sample of 20 task names against `vitest --reporter=json` full names | tasks = tests_seen (4,278) and conflicts = 0 → PASS; a shortfall is named by shape and STOPs above 1% | the spike's gap was 120/4,278 = 2.8%, all one shape, closed by rule in §3.4 |
| E10 | What does conversion cost? | `ingest` wall over the full-suite spool set (parallel), and over one file | reported; full-suite ingest ≤ the plain wall (22.08 s) → the converter stays in Python; above → design input: a Node converter on `node:sqlite` or a binary wire | Rust's converter did 132k events in 1.2 s; 4.1M events is ×31, so the bound is the suite's own wall, not Rust's number |
| E11 | Is the loss model honest? | (a) a probe test whose promise never settles under vitest's timeout; (b) a worker SIGKILLed mid-file | (a) the frame reads `suspended at end of recording` and the trace is complete; (b) `incomplete: true`, INCOMPLETE banner, `diff` refuses at exit 3; anything else → STOP | §4's loss model, both halves |

**Reported without a gate:** bytes per line and lines per second under the
product runtime; vitest's `transform` seconds per arm; output/input size;
`info` and `diff` latency on the largest file trace; the count of DIVERGED
pairs when two full-suite runs are `diff`ed file by file (a non-zero names
a nondeterministic test, which is a finding about the consumer).

### Spec `## 10. First use` — verbatim

Two invocations of the consumer's own suite, then the question the tool
exists for:

```
sensorium ts run -- vitest run                 # A
sensorium ts run -- vitest run                 # B
sensorium runs                                 # two groups, 372 files each
sensorium diff <A:src/fog/compute.test.ts> <B:same>   # MATCH, per file
sensorium tree <A:one file> --depth 3          # tests as task groups
sensorium frame <run> --fn compute             # one activation, return value
```

Expected: every same-file pair MATCH (E3-TS at invocation scale, reported),
`tree` grouping by test, `info` naming the harness and the file. Then two
controls on a throwaway copy of the lens, both gated (the Rust E5 shape):

- **E5-TS, the split.** Two functions of one VTT module moved to a new
  file, nothing else changed; record the test file that exercises them.
  Plain `diff` reads DIVERGED at the first moved function (the fingerprint
  hashes the file); `diff --ignore-moves` reads `MATCH modulo location` with
  exactly those two code objects in `moved:` and every task paired by name.
  Anything else → STOP: the verifier cannot see through a move.
- **The planted change.** Two call sites swapped in one VTT function →
  `diff` DIVERGED naming the step. A MATCH voids the verifier and STOPs.

### Plan section "Pre-registration (Task 0 commits spec §8's table and §10's two controls verbatim as docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md §1, plus these pins)" — verbatim

- **E3-TS's file, named now:** `src/__tests__/useMeshVoice.test.tsx` (39 `await`s, 3 timer sites, 21 tests on the lens). Twenty `sensorium ts run -- npx vitest run src/__tests__/useMeshVoice.test.tsx`, `diff` each against the first.
- **E9's sample:** the first 20 task names of the trace for `src/components/inventory/InventoryTab.test.tsx`, against `fullName`s from one plain `npx vitest run --reporter=json --outputFile=<store>/e9.json` of the same file.
- **E10's lens:** `sensorium ts ingest` over the full-suite spool set of E0′'s run, n=3, median; and over E3-TS's first spool.
- **E11(b)'s kill:** `kill -9` of the forked child running `InventoryTab.test.tsx` during a full-suite run, found by `pgrep -f '^[^ ]*node .*forks'` anchored (never `pkill -f` unanchored: it self-matches).
- **Reported without a gate:** as spec §8's list.


---

## 2. Ambient pins (preflight, recorded 2026-09-09 before any code exists)

Every value below is the output of the command beside it, run on this box on
2026-09-09 between 05:31 and 05:43 local time (`-05:00`), before the
`typescript/` skeleton was written and before any recorder code existed. The
lens is the VTT frontend **copy** at `/mnt/extra/sensorium-s5/vtt/frontend`
(VTT `0091e97`); `~/workspace/projects/vtt` was neither read nor touched.

| Item | Command | Value |
|---|---|---|
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| lens vitest | `node -e "…require('<lens>/node_modules/vitest/package.json').version"` | `4.1.9` |
| lens vite | same, `vite` | `6.4.3` |
| lens typescript | same, `typescript` | `5.9.3` |
| lens jsdom | same, `jsdom` | `29.1.1` |
| lens react | same, `react` | `18.3.1` |
| lens pixi.js | same, `pixi.js` | `8.19.0` |
| lens `node_modules` breadth | `ls <lens>/node_modules \| wc -l` | `160` entries |
| nproc | `nproc` | `16` |
| governor | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | `powersave` |
| `NODE_OPTIONS` | `echo "NODE_OPTIONS=[${NODE_OPTIONS-<unset>}]"` | `NODE_OPTIONS=[<unset>]` — unset |
| `VITEST` | `echo "VITEST=[${VITEST-<unset>}]"` | `VITEST=[<unset>]` — unset |
| `CI` | `echo "CI=[${CI-<unset>}]"` | `CI=[<unset>]` — unset |
| free disk `/` | `df -h /` | `5.5G` available on `/dev/nvme0n1p2` (100% used, 915G total) — floor is 3 GB, this passes with 2.5 GB to spare |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `71G` available on `/dev/nvme1n1p1` (85% used, 469G total) — floor is 8 GB, this passes with 63 GB to spare |
| mount `/` | `findmnt -no SOURCE,FSTYPE /` | `/dev/nvme0n1p2 ext4` |
| mount `/mnt/extra` | `findmnt -no SOURCE,FSTYPE /mnt/extra` | `/dev/nvme1n1p1 ext4` — a different block device and filesystem; every artifact set (`SENSORIUM_DIR`, the lens, the throwaway venvs' host worktree) lives here, off the chronically near-full root filesystem |
| 1-minute load, preflight | `cat /proc/loadavg` (checked before anything was created) | `1.32 0.70 0.54 1/2580 42257` — 1-minute load 1.32, under the 4.0 refusal threshold |
| 1-minute load, immediately before the timed baseline | `cat /proc/loadavg` | `0.77 0.70 0.55 1/2583 44216` — 0.77, under 4.0 |
| 1-minute load, at pin time | `cat /proc/loadavg` | `0.75 1.39 1.12 3/2586 85297` |
| store root | `mkdir -p /mnt/extra/sensorium-s5/store-rung1` | created; `SENSORIUM_DIR` for every trace this rung records |
| lens manifest | `cd <lens> && (find src -type f \| sort; echo vite.config.ts; echo package.json) \| xargs sha256sum > /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | **748 entries** — the expected count, exactly. Manifest file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`; first entry `src/App.tsx`, last three `src/vite-env.d.ts`, `vite.config.ts`, `package.json` |
| lens manifest re-read after the plain baseline | the same pipeline, `diff`ed against the file | identical — the plain run wrote nothing into the manifest set |
| **plain `npx vitest run` on the lens — Test Files** | `cd <lens> && /usr/bin/time -f "WALL_SECONDS=%e MAXRSS_KB=%M" npx vitest run` | ` Test Files  372 passed (372)` |
| **plain `npx vitest run` on the lens — Tests** | same run | `      Tests  4278 passed (4278)` |
| **plain `npx vitest run` on the lens — vitest Duration** | same run | `   Duration  22.30s (transform 10.26s, setup 12.31s, import 32.47s, tests 79.31s, environment 165.80s)` |
| **plain `npx vitest run` on the lens — wall, RSS** | same run | `WALL_SECONDS=22.62 MAXRSS_KB=572788`, process exit `0`. Started `05:35:14`. Full log: `<store>/baseline-vitest-plain.log` |
| Python suite, 3.12 | `PYTHONDONTWRITEBYTECODE=1 SENSORIUM_DIR=<store>/baseline-312 .venv312/bin/python -m pytest -q -p no:cacheprovider` | `2979 passed, 23 skipped in 89.58s (0:01:29)`, exit `0` — Python 3.12.13 |
| Python suite, 3.13 | same, `.venv313` = the worktree's own `.venv` / `<store>/baseline-313` | `2983 passed, 19 skipped in 66.65s (0:01:06)`, exit `0` — Python 3.13.13. (The controller's independent baseline of the same suite read the same `2983 passed, 19 skipped`.) |
| Python suite, 3.14 | same, `.venv314` / `<store>/baseline-314` | `2987 passed, 15 skipped in 95.68s (0:01:35)`, exit `0` — Python 3.14.4 |
| sensorium version | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.8.7`. **`.venv/bin/sensorium --version` is not a supported invocation** — it exits 2 with the argparse usage line (`sensorium: error: the following arguments are required: cmd`); the pin is read from installed metadata instead |
| sensorium install | `.venv/bin/python -c "import sensorium, pathlib; print(pathlib.Path(sensorium.__file__).parents[1])"` | `/mnt/extra/sensorium-rung2/s5-rung1/src` — an editable install of this checkout, as P10 assumes |
| uv | `uv --version` | `uv 0.11.18 (x86_64-unknown-linux-gnu)` |
| repo HEAD | `git rev-parse HEAD` (worktree `/mnt/extra/sensorium-rung2/s5-rung1`, branch `feat/s5-rung1-recorder-v1`) | `216bfd8ffd9ad3718db0f3fe0d7954e8beb2cdfe` |
| repo status before the skeleton | `git status --porcelain` | empty (clean) |
| `typescript/` dependency tree | `npm ls --depth=0` in `typescript/` after `npm ci` | `sensorium-ts@0.1.0` → `@types/node@24.13.3`, `magic-string@0.30.21`, `typescript@5.9.3` |

**Preflight verdict:** all three refusal rules pass — `/mnt/extra` free 71 G ≥ 8 G;
`/` free 5.5 G ≥ 3 G; 1-minute load 1.32 ≤ 4.0, and 0.77 immediately before the
one timed measurement. Proceeded; did not BLOCK.

**Two ambient facts recorded because a later task must act on them, not because
a rule was broken:**

1. **The root filesystem is at 5.5 GB free (100% used).** It clears the 3 GB
   floor by 2.5 GB and nothing this rung measures writes to `/`, but the margin
   is a third of what rung 2 had. Every artifact set stays on `/mnt/extra`, and
   `uv cache clean` is never run (the VTT license-server venv symlinks into it).
2. **One spike leftover sits in the lens:** `frontend/vitest.sensorium.config.mts`
   (871 bytes, mtime 2026-09-08 22:59), a throwaway wrapper config that imports
   the spike's plugin from `~/workspace/sensorium/spike/typescript/vite-plugin.mjs`.
   It is **outside the manifest set** (not under `src/`, not `vite.config.ts`,
   not `package.json`) and vitest does **not** auto-load it — the auto-loaded
   names are `vitest.config.*` then `vite.config.*`, and this file matches
   neither, so it is reachable only through an explicit `--config`. The
   `05:35:14` plain baseline above therefore ran on `vite.config.ts`, and read
   the pinned `372 passed (372)` / `4278 passed (4278)`. No `sensorium-probes/`
   directory and no `node_modules/.sensorium` exist in the lens
   (`find frontend -name 'sensorium-probes' -o -name '*.sensorium*'` returns
   only that one config file). **The lens is read-only for Task 0, so the file
   was left in place.** E6′ must decide whether to remove it before it reads
   its number; leaving it is a contamination hazard for a "the wrapper
   directory is gone" check that greps by name.

---

## 3. Results

**Nothing here is measured yet.** Every cell reads
`not measured (rung 1 pending)`. This section is filled once, from the run's
own raw facts, after the endpoints execute; a cell is written exactly once and
no gated arm is re-run after its number is read.

`results.json` schema (none-versus-zero), carried unchanged from the rung-2
record: every measurement is
`{"value": <number|null>, "n": <int>, "lens": <string>, "dropped": [<reason>...]}`;
a `null` value with a non-empty `dropped` list is the only representation of
"not measured"; `0` is measured-and-zero; the renderer refuses to print a
`null` row as anything but `not measured (<reason>)`.

### 3.1 Gated endpoints (spec §8)

| Id | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E0′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E1′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E2′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E3-TS | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E4′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E5′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E6′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E7′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E8′ | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E9 | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E10 | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| E11 | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |

### 3.2 The two gated controls (spec §10)

| Control | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E5-TS, the split | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| The planted change | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |

### 3.3 First use (spec §10's six invocations)

| Invocation | Value | n | Lens | Dropped |
|---|---|---|---|---|
| `sensorium ts run -- vitest run` (A) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `sensorium ts run -- vitest run` (B) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `sensorium runs` | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `sensorium diff <A:src/fog/compute.test.ts> <B:same>` | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `sensorium tree <A:one file> --depth 3` | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `sensorium frame <run> --fn compute` | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |

### 3.4 Reported without a gate (spec §8's list)

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| bytes per line, product runtime | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| lines per second, product runtime | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| vitest `transform` seconds per arm | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| output/input size | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `info` latency, largest file trace | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| `diff` latency, largest file trace | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |
| DIVERGED pairs, two full-suite runs `diff`ed file by file | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) | not measured (rung 1 pending) |

---

## 4. Decisions

*Empty — written by hand at the end of the rung, not by a runner. Each row will
quote the pre-registered rule from §1 verbatim beside the measured number from
§3 and a verdict.*

---

## 5. Gaps found

*Empty — written at the end of the rung. Each entry will say what was MEASURED,
not what is suspected.*
