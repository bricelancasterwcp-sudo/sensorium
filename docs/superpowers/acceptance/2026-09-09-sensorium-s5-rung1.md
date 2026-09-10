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
| 1-minute load, at pin time | `date -Iseconds; cat /proc/loadavg` | `2026-09-09T05:42:51-05:00`, then `0.75 1.39 1.12 3/2586 85297` — the close of this table's reading window |
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

### 2b. Re-pins and pre-run choices (the acceptance run, 2026-09-09 15:27–15:30 −05:00)

Task 0's table above is untouched. This block is appended by the acceptance
run (Task 10), which re-takes the pins that can move between preflight and the
run, records the one act it performs on the lens before any endpoint reads a
number, and pins the two §10 controls' targets **before** they are recorded.

**Ruling R3 — the spike leftover removed before anything was measured.** §2's
ambient fact 2 named `frontend/vitest.sensorium.config.mts` as a contamination
hazard for E6′'s marker grep and left the decision to E6′. It was removed
first, so that no endpoint of this run saw it:

| Item | Command | Value |
|---|---|---|
| the leftover, before | `ls -la <lens> \| grep -i sensorium` | `-rw-rw-r-- 1 brice brice 871 Sep 8 22:59 vitest.sensorium.config.mts` |
| its content, pinned before removal | `sha256sum <lens>/vitest.sensorium.config.mts` | `e8c5adbfbe516f7812802a6431d1cacbb6d6a8a6819ab6d46bdcb6947774223d` |
| the removal | `rm <lens>/vitest.sensorium.config.mts` | done 2026-09-09T15:27:56−05:00 |
| the leftover, after | `ls -la <lens> \| grep -i sensorium` | no match — nothing named `sensorium` at the lens root |
| anything else named for the recorder | `find <lens> -maxdepth 2 -name 'sensorium-probes' -o -maxdepth 2 -name '*.sensorium*'` | no output |

The file was outside the manifest set, so its removal cannot move the manifest —
and the re-check below confirms it did not.

**The pins re-taken, in the order they were read:**

| Item | Command | Value |
|---|---|---|
| date, 1-minute load | `date -Iseconds; cat /proc/loadavg` | `2026-09-09T15:28:10-05:00`, then `0.47 0.40 0.55 1/2566 1434684` — 0.47, under the 4.0 refusal threshold |
| free disk `/` | `df -h /` | `5.0G` available (100% used, 915G total) — floor 3 GB, passes with 2.0 GB to spare; 0.5 GB below Task 0's reading |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `70G` available (85% used, 469G total) — floor 8 GB, passes with 62 GB to spare |
| lens top level, after R3 | `ls -A <lens>` | `.claude .pytest_cache Dockerfile dist e2e e2e-shots index.html nginx.conf node_modules package-lock.json package.json public src start-vite.sh tsconfig.json vite.config.ts` — 15 entries, one fewer than Task 0's listing and the missing one is the leftover |
| lens manifest, re-read | `cd <lens> && (find src -type f \| sort; echo vite.config.ts; echo package.json) \| xargs sha256sum \| diff - <manifest>` | **identical**, `748` lines — the lens is byte-for-byte Task 0's |
| lens manifest, verified | `sha256sum -c <manifest>` | exit `0`, `748` OK, `0` FAILED |
| node | `node --version` | `v24.16.0` — unchanged |
| npm | `npm --version` | `11.13.0` — unchanged |
| nproc, governor | `nproc; cat …/scaling_governor` | `16`, `powersave` — unchanged |
| repo HEAD | `git rev-parse HEAD` | `29c505957ce6361bee0c249efab695cb11b35753` (branch `feat/s5-rung1-recorder-v1`); Task 0 pinned `216bfd8…`, the commit this record was written on |
| sensorium version | `.venv/bin/python -c "…version('sensorium')"` | `0.8.7` — unchanged |
| store for this run | `mkdir -p /mnt/extra/sensorium-s5/store-rung1/acceptance` | created; `SENSORIUM_DIR` for every trace Task 10 records |

**Re-pin verdict:** all three refusal rules still pass — `/mnt/extra` free 70 G ≥ 8 G;
`/` free 5.0 G ≥ 3 G; 1-minute load 0.47 ≤ 4.0. Proceeded; did not BLOCK.

**The §10 controls' targets, chosen and written down before either was recorded.**
Both run on their own throwaway `rsync` copy of the lens; the lens itself is
never edited.

| | |
|---|---|
| **E5-TS, the split — module** | `src/lib/distance/hexGeometry.ts` |
| **E5-TS — the two functions moved** | `isHexShape` (line 68) and `hexDistance` (line 188) |
| **E5-TS — the destination** | a new file `src/lib/distance/hexGeometryMoved.ts`; `hexGeometry.ts` imports both names back and re-exports them, so every import in the tree still resolves and no call site changes |
| **E5-TS — the test file recorded** | `src/lib/distance/hexGeometry.test.ts` (322 lines; it calls `hexDistance` 16 times and `isHexShape` 4 times directly, and reaches both again through `neighbors`, `stepsBetween`, `pathCost` and the shape-dispatch wrappers) |
| **E5-TS — why these two** | both are pure and **self-contained**: neither touches a module-private binding, so the move needs no other edit. The transform instruments both — `node -e` over `transform.mjs` lists `isHexShape` and `hexDistance` among `hexGeometry.ts`'s 14 instrumented sites — so both appear in the trace as code objects and can be paired |
| **The planted change — function** | `pathCost` in `src/lib/distance/distance.ts` (line 207), exercised by the same test file (lines 262–314) |
| **The planted change — the swap** | the `const law = terrainLaw(terrainSystem, kind);` call site is moved from **before** the diagonal branch to **after** it, so that `terrainLaw` and `isDiagonal`/`diagonalStepFt` execute in the opposite order. Nothing else changes |
| **The planted change — why this one** | it is **value-preserving**: every number `pathCost` returns is identical and the suite stays green, so the swap is invisible to the consumer's own tests and only the recorder's causal fingerprint can see it. All four functions are instrumented (`terrainLaw`, `applyLaw`, `isDiagonal`, `diagonalStepFt` are in `distance.ts`'s 21 instrumented sites), and the fingerprint is a rolling hash over `(file, qualname, kind)` — so two calls that swap order under **different** qualnames must move the digest, while a swap of two calls to the *same* function could not. That is why the swap is across two names and not within one |


---

## 3. Results

**Measured 2026-09-09 between 15:27 and 16:35 local time (−05:00)**, on the
lens §2 pins, by the instruments committed under `typescript/acceptance/`.
Every cell below is read out of
`docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.results.json`,
which each instrument wrote directly; nothing here was computed by hand. No
gated arm was re-run after its number was read; the three re-derivations that
did happen are **§5 gaps 3, 4 and 7**, and each re-read a file that was
already on disk.

**This section supersedes the header.** The file still opens *"Status:
pre-registration only"* and *"§3's cells are all `not measured (rung 1
pending)`"*, and those two sentences are now false. They are left standing on
purpose: lines 1–97 of this file — the header and the whole of §1 — are
byte-identical to `git show 29c5059:<this file>`, which is a thing a reader
can check in one command, and it is worth more than a tidy header. §3, §4 and
§5 below are the measured record.

**The lens, on every number below:** *VTT frontend at `0091e97` — vitest
4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores (powersave);
recorded by sensorium 0.8.7 / sensorium-ts 0.1.0 at `29c5059`* — the one
string `typescript/acceptance/LENS.txt` holds and every instrument stamps on
its own cell. The `Lens` column says **VTT** for it, once, rather than
repeating 165 characters thirty times.

`results.json` schema (none-versus-zero), carried unchanged from the rung-2
record: every measurement is
`{"value": <number|null>, "n": <int>, "lens": <string>, "dropped": [<reason>...]}`;
a `null` value with a non-empty `dropped` list is the only representation of
"not measured"; `0` is measured-and-zero; the renderer refuses to print a
`null` row as anything but `not measured (<reason>)`.

### 3.1 Gated endpoints (spec §8)

| Id | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E0′ | **372** containers carrying exactly one `test_file` | 372 traces | VTT | none |
| E1′ | **off/plain = 1.0587** (harness wall, conversion excluded) | 5 per arm | VTT | none |
| E2′ | **ratio 1.0000** — 5,378 instrumented of 5,378 eligible | 5,378 sites | VTT | none |
| E3-TS | **DIVERGED 0**, REFUSED 0, MATCH 19 | 19 pairs | VTT | none |
| E4′ | **20** shapes on their exact line; the planted report identical | 20 shapes | VTT | none |
| E5′ | **2** of 2 harnesses green | 2 harnesses | VTT | none |
| E6′ | manifest identical **PASS** (748 OK / 0 FAILED) · 372/4278 **PASS** · inside the plain band **STOP** (22.8678 s against [22.3136, 22.7221]) · 0 markers **PASS** · wrapper gone **PASS** | 4 clauses | VTT | none |
| E7′ | **0** occurrences of the eight leak needles | 8 needles | VTT | none |
| E8′ | **5** of 5 swallow shapes seen | 5 shapes | VTT | none |
| E9 | **0** — tasks (4,278) minus `tests_seen` (4,278) | 372 traces | VTT | none |
| E10 | **45.5293 s** median full-suite ingest | 3 repetitions | VTT | none |
| E11 | **5** of 5 claims held across both halves | 5 claims | VTT | none |

**Every cell above, with its pre-registered rule quoted beside it.**

**E0′** — rule: *"372 containers, one file each; any container with two files
or any file with none → STOP"*. The call arm's first full-suite invocation
(`20260909-160038-f08e89`) produced **372 traces**. The rule names two
failures and both were measured. *A container with two files:* **0** traces
carry `test_files` (the key the builder writes when a container starts more
than one file). *A file with none:* the 372 traces carry **372 distinct**
`test_file` values with no repeats, and the suite ran 372 files, so every
file the run executed has exactly one container and none is unrecorded.
Beside them, **0** traces carry neither key.

**E1′** — rule: *"off/plain ≤ 1.10 → the transform stays uncached; above → a
cache keyed on source sha becomes rung-1 work, not a NO-GO; call/plain
reported beside the spike's 1.131"*. Five interleaved plain→off→call triples,
each run at `372 passed (372)` / `4278 passed (4278)` with harness exit 0, so
no run was dropped and every arm has its full n=5.

**The load guard's own evidence is in the artifact, not just in this
sentence.** `arms.sh` reads `/proc/loadavg` immediately before every run and
`arm_line.py` writes the reading into that run's row, so all **fifteen**
readings are carried into `results.json` under the E1′ cell's `load_guard`
key — per arm and per run, not summarised: plain `0.68, 2.92, 3.43, 3.59,
3.63`; off `3.21, 3.92, 2.93, 3.79, 3.47`; call `3.24, 2.94, 3.88, 3.58,
3.48`. The key also carries `threshold: 4.0`, `min: 0.68`, `max: 3.92` and
`all_under_threshold: true`, so "every run was under the pre-registered
refusal" is a claim a reader checks against the numbers rather than takes.

| arm | timed as | walls (s) | median | min–max |
|---|---|---|---|---|
| plain | this runner's clock around `npx vitest run` | 22.3136, 22.3252, 22.5925, 22.6142, 22.7221 | **22.5925** | 22.3136–22.7221 |
| off | `harness.json`'s `wall_end_ts − wall_start_ts` | 23.6649, 23.7126, 23.9185, 23.9531, 23.9871 | **23.9185** | 23.6649–23.9871 |
| call | the same | 25.1789, 25.4890, 25.5832, 25.6130, 25.9376 | **25.5832** | 25.1789–25.9376 |

**off/plain = 1.0587**; **call/plain = 1.1324** (the spike measured 1.131 on
the same lens). Beside them, ungated, the DRIVER's own total wall — the
harness plus the conversion the driver runs after it: off median **23.9928 s**
(×1.062 of plain, conversion being empty at tier `off` by design), call median
**70.2505 s** (×3.1095). The call arm's total wall climbed run to run —
45.0430, 63.5882, 71.1134, 71.1949, 70.2505 — while its HARNESS wall did not
move at all (25.18–25.94); the conversion, not the recording, is what got
slower as the store filled. That is the same quantity E10 measures directly.

**E2′** — rule: *"after removing NAMED kinds the ratio is 1.000 (5,403 of
5,403 was measured); one unnamed miss → STOP"*. Over the lens's `src` tree
with the consumer's own TypeScript 5.9.3: **367 files** transformed,
**5,378 instrumented of 5,378 eligible, ratio 1.0000**, `failed` **[]**,
`parse_error` **[]**, and `excluded` **{}** — the census set produced no
exclusions at all, so there is no unnamed one. By frame kind: `function`
5,094, `coroutine` 284. Output/input **1.2543**.

**E3-TS** — rule: *"DIVERGED 0/19 and REFUSED 0/19; any → the comparator or
the recorder is wrong, STOP"*. `src/__tests__/useMeshVoice.test.tsx` recorded
**20** times through `sensorium ts run -- npx vitest run <file>`; all 20 left
a trace; `sensorium diff <first> <k>` for k=2…20 gave **19 exits of 0**,
**DIVERGED 0/19**, **REFUSED 0/19**, and one verdict repeated nineteen times:
`MATCH -- identical causal streams (398 events): the same sequence of (file,
qualname, kind) for CALL/RETURN/RAISE/HANDLED on the main thread`.

**E4′** — rule: *"20/20 on the exact line; the report byte-identical; a miss
is a regression of a measured 20/20 → STOP"*. The probe project's twenty
`// SITE` markers: **20 found, 20 on their exact line, `wrong: []`**. The
planted assertion: one `expect(1).toBe(2)` appended to
`src/lib/safeUrl.test.ts` on a throwaway copy of the lens, run plain and
through the driver. Both runs printed the same header,
`FAIL  src/lib/safeUrl.test.ts > planted acceptance failure`, and the same
single site reference for that file, **`src/lib/safeUrl.test.ts:44:13`** —
identical. Reported and not gated: the DRIVEN run's stack additionally walks
two frames inside the recorder's own runtime
(`typescript/src/rt.mjs:296:39` and `:296:23`); those are references to the
recorder, not to the planted file, and the planted site did not move. Because
of them the two reports are **not** byte-identical as whole texts, and this
endpoint's "byte-identical" was applied to the planted file's `FAIL` header
and site references only — **§5 gap 8** states that reading and quotes the two
extra frames.

**E5′** — rule: *"372/4278 green and `node --test` green with its rows; a red
vitest is NO-GO"*. Vitest: **all 5 call-arm runs** read `372 passed (372)` /
`4278 passed (4278)` at driver exit 0. `node --test`: **6 pass, 0 fail**, and
the probe checker over its spool read **15 checks, 0 failures**.

**E6′** — rule: *"manifest identical, 372/4278 inside the plain band, 0
markers, the wrapper directory gone"*. Run last, after every instrumented run
of this acceptance. Four clauses, measured one at a time:

| clause | measured | holds |
|---|---|---|
| manifest identical | `sha256sum -c` exit 0, **748 OK, 0 FAILED** | **yes** |
| 372/4278 … | one plain `npx vitest run`, exit 0, `372 passed (372)` / `4278 passed (4278)` | **yes** |
| … inside the plain band | wall **22.8678 s** against the plain arm's own min–max band **22.3136–22.7221 s** | **no** — 0.1457 s (0.65%) above the band's top |
| 0 markers | `grep -rl __srt` over `node_modules/.vite` and `node_modules/.vite-temp` (the two cache directories that existed): **0 files** | **yes** |
| the wrapper directory gone | `node_modules/.sensorium`: **absent** | **yes** |

**The manifest clause is verified twice, because `e6.sh` verifies it in the
wrong order to cover its own run.** The script checks the manifest FIRST and
then does its plain run, so its own `748 OK` says nothing about the run it is
about to make — the last thing to touch the lens is unaudited by the
instrument that audits the lens. The clause was therefore re-taken by hand
AFTER E6′ finished, twice with the same result: at **16:35** on the run day,
and again at **2026-09-09T16:57:12−05:00** while this record was being
corrected, both as `cd <lens> && sha256sum -c <the §2 manifest>` → **exit 0,
748 OK, 0 FAILED**. Nothing has been run against the lens between E6′ and
that second reading. The ordering is §5 gap 6.

**E7′** — rule: *"0 occurrences; plus `v23`/`v24` green"*. Ten reader commands
on one call-arm trace of `src/components/inventory/InventoryTab.test.tsx`; the
2,241-line transcript is committed beside this record as
`2026-09-09-sensorium-s5-rung1-e7-reader.txt`. Exits: `runs` 0, `info` 0,
`tree` 0, `frame` 0, `grep` 0, `exceptions` 3, `watch` 3, `flow` 3, `diff` 0,
`refocus` 2 — the three 3s and the 2 are this recorder's own refusals, each
naming what it does not carry. The eight needles, each matched as the literal
it is: `asyncio` **0**, `python ?` **0**, `cargo` **0**, `coroutine` **0**,
`Python's own` **0**, `threading`/`_thread` **0**, `Rust disposition` **0**,
`sensorium run --focus` **0** — **total 0**. Reported and not gated: the
transcript names Python once, in the `exceptions` refusal
(*"the Python rules index exception identity this trace does not carry"*),
which is a sentence about why a command refuses and matches none of the eight.
Vectors: `pytest -q tests/test_vectors.py -k "v23 or v24"` exit 0,
`3 passed, 1 skipped, 57 deselected in 0.38s`.

**E8′** — rule: *"5/5, reported per shape; rung 2 gates the rules"*. All five
swallow shapes seen, each counted only where **every** check naming it passed:
shape 1 (2 checks), shape 2 (2), shape 3 (3, the unhandled rejection),
shape 4 (2), shape 5 (3, including the one-serial check). **5/5.**

**E9** — rule: *"tasks = tests_seen (4,278) and conflicts = 0 → PASS; a
shortfall is named by shape and STOPs above 1%"*. Over the call arm's first
invocation's 372 traces: **tasks 4,278**, **`tests_seen` 4,278**, difference
**0** (0.0000%), **`task_name_conflicts` 0**, and **0 files** whose two counts
disagree — so there is no shortfall to name by shape. The 20-name sample, on
`src/components/inventory/InventoryTab.test.tsx`: the trace's first 20 task
names and vitest's own first 20 `fullName`s are **not identical as printed**,
and are **identical once the recorder's ` > ` join is replaced by a space**
(20 of 20, same segments, same order). The recorder writes
`InventoryTab > renders a resolved item and toggles equip`; vitest's JSON
reporter writes `InventoryTab renders a resolved item and toggles equip`.

**E10** — rule: *"reported; full-suite ingest ≤ the plain wall (22.08 s) → the
converter stays in Python; above → design input: a Node converter on
`node:sqlite` or a binary wire"*. Over a copy of the call arm's first
invocation's spool set — **372 spools, 414,450,522 bytes** — with a fresh
store each repetition and the copy outside the timed region:
**45.5293, 45.3636, 45.5584 s, median 45.5293 s**. Against this run's own
plain median (22.5925 s) that is **×2.02**; against the 22.08 s the rule
names, **×2.06**. One file's spool (E3-TS's first, 611,016 bytes):
**0.3748, 0.3638, 0.3586 s, median 0.3638 s**.

**E11** — rule: *"(a) the frame reads `suspended at end of recording` and the
trace is complete; (b) `incomplete: true`, INCOMPLETE banner, `diff` refuses
at exit 3; anything else → STOP"*.

- **(a), 2 of 2.** The `never_settles` probe's trace: `tree` prints
  `f1 e1 <anonymous>() … [async]  ~ suspended at end of recording` and
  `f2 e2 parks() … [async]  ~ suspended at end of recording`, and `info`
  prints **no** line beginning `INCOMPLETE:` — the frame never returned, and
  the recording is whole.
- **(b), 3 of 3.** A full-suite run with the container that had declared
  `src/components/inventory/InventoryTab.test.tsx` found by its own spool
  (`1568484-0.jsonl`) and `kill -9`ed by pid — never `pkill -f`. Its trace
  carries **`incomplete: true`**; `info` prints
  `INCOMPLETE: recording ended without a finalize pass (process died
  mid-record); exit/uncaught/children/truncated-count fields below are
  UNKNOWN, not zero`; and `sensorium diff <it> <a complete trace of the same
  file>` **exits 3** with `verdict: REFUSED -- cannot issue a MATCH/DIVERGED
  verdict`.

### 3.2 The two gated controls (spec §10)

| Control | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E5-TS, the split | **4** of 4 claims held | 4 claims | VTT | none |
| The planted change | **2** of 2 claims held | 2 claims | VTT | none |

**E5-TS, the split** — rule: *"Plain `diff` reads DIVERGED at the first moved
function (the fingerprint hashes the file); `diff --ignore-moves` reads
`MATCH modulo location` with exactly those two code objects in `moved:` and
every task paired by name. Anything else → STOP: the verifier cannot see
through a move."* On its own `rsync` copy of the lens, `isHexShape` (4 lines)
and `hexDistance` (11 lines) were cut out of
`src/lib/distance/hexGeometry.ts` byte for byte and pasted into a new
`src/lib/distance/hexGeometryMoved.ts`, which the old module imports back and
re-exports; `src/lib/distance/hexGeometry.test.ts` was recorded before and
after (both at `1 passed (1)` / `56 passed (56)`, driver exit 0).

- plain `diff`: **exit 1**, `verdict: MATCH on the thread stream (14 events);
  DIVERGED on the tasks (below)`
- `diff --ignore-moves`: **exit 0**, `verdict: MATCH modulo location --
  identical causal streams (14 events) once 2 moved code object(s) are paired
  by qualname on the main thread`
- `moved:` **exactly two**, and exactly the two that moved —
  `hexDistance  hexGeometry.ts -> hexGeometryMoved.ts` and
  `isHexShape  hexGeometry.ts -> hexGeometryMoved.ts` — with **no**
  `removed (only in A)`, `added (only in B)` or `unpaired` line
- tasks: `56 task stream(s) on each side, compared by content as (name, hash):
  all matched`

**The planted change** — rule: *"Two call sites swapped in one VTT function →
`diff` DIVERGED naming the step. A MATCH voids the verifier and STOPs."* On a
second copy, one line of `pathCost` in `src/lib/distance/distance.ts` moved
from line 225 to line 232: `const law = terrainLaw(terrainSystem, kind);` now
runs **after** the diagonal branch instead of before it, so `terrainLaw` and
`isDiagonal`/`diagonalStepFt` execute in the opposite order. Every value
`pathCost` returns is unchanged and **both recordings read `56 passed (56)`**
— the swap is invisible to the consumer's own tests.

`sensorium diff <before> <after>`: **exit 1**, and the report names the step:

```
first difference inside hex step law > square is byte-identical to the
unshaped call (the back-compat contract) (A task t56, B task t56) at causal
step 16:
  A:      e87517 CALL    terrainLaw  (…/src/lib/distance/distance.ts)
  B:      e87517 CALL    isDiagonal  (…/src/lib/distance/distance.ts)
```

### 3.3 First use (spec §10's six invocations)

Spec §10's first two lines are the call arm's own runs 1 and 2 — already
recorded and already counted — so they were not recorded a third time for a
demonstration; the other four commands were asked of them. §10's example named
a `src/fog/compute.test.ts` and a function `compute`, neither of which this
lens has; the file and the function are named below.

| Invocation | Value | n | Lens | Dropped |
|---|---|---|---|---|
| `sensorium ts run -- vitest run` (A) | invocation `20260909-160038-f08e89`, harness exit 0, `372 passed (372)` / `4278 passed (4278)`, **372 traces** | 1 run | VTT | none |
| `sensorium ts run -- vitest run` (B) | invocation `20260909-160541-9c665a`, harness exit 0, same counts, **372 traces** | 1 run | VTT | none |
| `sensorium runs` | exit 0; **two groups, 372 traces each**, each headed `invocation <id>: npx vitest run  exit:0 (waited)` | 2 groups | VTT | none |
| `sensorium diff <A:file> <B:same>` | exit 0, `verdict: MATCH -- identical causal streams (180 events)` on `src/components/inventory/InventoryTab.test.tsx` | 1 pair | VTT | none |
| `sensorium tree <A:one file> --depth 3` | exit 0; the tree opens `no test` for the import-time frames and then one `task tN: <test name>` group per test | 1 trace | VTT | none |
| `sensorium frame <run> --fn <fn>` | exit 0; `f102 deriveAttacks.ts:deriveWeaponAttacks  [e200..e215]  thread 1  task t1 (InventoryTab > renders a resolved item and toggles equip)` — one activation, with its return value | 1 frame | VTT | none |

### 3.4 Reported without a gate (spec §8's list)

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| bytes per line, product runtime | **99.61 B/line** (median over the 5 call runs; 2,072,244,794 B over 20,802,850 lines in total) | 5 runs | VTT | none |
| lines per second, product runtime | **162,629.8 lines/s** (median; lines ÷ the run's own harness wall) | 5 runs | VTT | none |
| vitest `transform` seconds per arm | plain **10.24 s**, off **21.64 s**, call **21.43 s** (medians) | 5 per arm | VTT | none |
| output/input size | **1.2543** (the census's `bloat`: transformed bytes ÷ source bytes over 367 files) | 367 files | VTT | none |
| `info` latency, largest file trace | **0.5401 s** median (0.8699, 0.5401, 0.5324) on `src/lib/map/gridDetect.test.ts`, a **333,832,192-byte** trace | 3 | VTT | none |
| `diff` latency, largest file trace | **0.6867 s** median (0.8905, 0.6867, 0.6835), same trace against its counterpart in run 2 | 3 | VTT | none |
| DIVERGED pairs, two full-suite runs `diff`ed file by file | **8** of 372 (364 MATCH, 0 REFUSED, 0 bad calls; every file recorded by both runs) | 372 pairs | VTT | none |

The eight files whose two recordings diverged, which spec §8 reads as *"a
finding about the consumer"* and not about the recorder:
`src/__tests__/AiSetupWizard.test.tsx`,
`src/__tests__/builderDispatch.test.tsx`,
`src/__tests__/describeCharacter.test.tsx`,
`src/__tests__/dnd5eBuilderDefinition.test.tsx`,
`src/__tests__/pickEntryCopy.test.tsx`,
`src/components/compendium/ItemEditor.ai.test.tsx`,
`src/components/sheet/SheetRenderer.rankControl.test.tsx`,
`src/components/sheet/SheetRenderer.writeThrough.test.tsx`.

---

## 4. Decisions

One row per pre-registered endpoint, its rule quoted from §1 verbatim, the
measured number from §3, and the verdict in the rule's own words. Written by
hand from §3; §3 was written from `results.json`.

| Id | The rule, verbatim from §1 | Measured | Verdict |
|---|---|---|---|
| E0′ | *"372 containers, one file each; any container with two files or any file with none → STOP"* | 372 containers, 372 with one `test_file`, **0** with `test_files` (no container took two files), **372 distinct** file names over 372 files run (no file went unrecorded), 0 with neither key | **PASS** — the trace unit is still the test file |
| E1′ | *"off/plain ≤ 1.10 → the transform stays uncached; above → a cache keyed on source sha becomes rung-1 work, not a NO-GO; call/plain reported beside the spike's 1.131"* | off/plain **1.0587**; call/plain **1.1324** | **PASS — the transform stays uncached.** No source-sha cache becomes rung-1 work |
| E2′ | *"after removing NAMED kinds the ratio is 1.000 (5,403 of 5,403 was measured); one unnamed miss → STOP"* | ratio **1.0000**, 5,378 of 5,378, `excluded` empty, `failed` empty, `parse_error` empty | **PASS** — the measured 100% did not regress |
| E3-TS | *"DIVERGED 0/19 and REFUSED 0/19; any → the comparator or the recorder is wrong, STOP"* | DIVERGED **0/19**, REFUSED **0/19** | **PASS** — no false DIVERGED |
| E4′ | *"20/20 on the exact line; the report byte-identical; a miss is a regression of a measured 20/20 → STOP"* | **20/20** on the exact line; the planted `FAIL` header and `…:44:13` identical plain against driven | **PASS** — sites keep their lines and columns. The verdict rests on the reading §5 gap 8 names: the planted assertion's line and column, and the test-file frames, byte-identical. The driven report also carries two `rt.mjs` frames the plain one does not, so the reports are not byte-identical as whole texts |
| E5′ | *"372/4278 green and `node --test` green with its rows; a red vitest is NO-GO"* | 5 of 5 call-arm runs at 372/4278, exit 0; `node --test` 6 pass 0 fail, checker 15/15 | **PASS** — both harnesses run |
| E6′ | *"manifest identical, 372/4278 inside the plain band, 0 markers, the wrapper directory gone"* | manifest identical (748/0); 372/4278 green; wall **22.8678 s** against a band of **22.3136–22.7221 s**; **0** markers; wrapper **absent** | **STOP — on the plain-band clause: the plain-after wall 22.8678 s sits above the plain arm's band [22.3136, 22.7221]; the manifest, marker and wrapper clauses hold exactly.** §1's rule is a flat conjunction and §1's own stop rules govern a rule that does not hold, so this is a STOP and not a lesser word. It fired on the one clause of the four that is a timing clause; the three that ask directly about contamination read clean, which is a fact about WHERE the STOP landed and not a reason to soften it. The wall stands as measured — no re-roll. Two instrument gaps bear on it (§5 gaps 5 and 6): `e6.sh` has no load guard though the clause is a timing clause, and a five-run min–max is a range and not a tolerance. Re-measuring belongs in the next slice as a NEW pre-registration, E6″, not in this one |
| E7′ | *"0 occurrences; plus `v23`/`v24` green"* | **0** occurrences across all eight needles; vectors exit 0 | **PASS** — the reader speaks this recorder's words |
| E8′ | *"5/5, reported per shape; rung 2 gates the rules"* | **5/5** | **PASS** — the five swallow shapes are still seen |
| E9 | *"tasks = tests_seen (4,278) and conflicts = 0 → PASS; a shortfall is named by shape and STOPs above 1%"* | tasks **4,278** = `tests_seen` **4,278**; conflicts **0**; shortfall **0** (0.0000%) | **PASS** — tests are tasks, with no shortfall to name. The rule attaches no threshold to the 20-name sample, so the sample does not gate; what it measured (the ` > ` join) is §5's |
| E10 | *"reported; full-suite ingest ≤ the plain wall (22.08 s) → the converter stays in Python; above → design input: a Node converter on `node:sqlite` or a binary wire"* | full-suite ingest median **45.5293 s** against a plain wall of 22.5925 s (rule's figure 22.08 s) | **REPORTED — above the bound, so this is design input and not a STOP**: the rule's own second branch. A Node converter on `node:sqlite`, or a binary wire, is now a live design question for the next rung |
| E11 | *"(a) the frame reads `suspended at end of recording` and the trace is complete; (b) `incomplete: true`, INCOMPLETE banner, `diff` refuses at exit 3; anything else → STOP"* | (a) **2/2**; (b) **3/3** | **PASS** — the loss model is honest on both halves. The first reading of (b) said 2/3; the instrument, not the product, was wrong, and §5 records it |
| E5-TS, the split | *"Plain `diff` reads DIVERGED at the first moved function … `diff --ignore-moves` reads `MATCH modulo location` with exactly those two code objects in `moved:` and every task paired by name. Anything else → STOP"* | exit 1 DIVERGED; exit 0 `MATCH modulo location`; `moved:` exactly `hexDistance` and `isHexShape`, nothing added/removed/unpaired; 56 tasks each side, all matched | **PASS** — the verifier sees through a move |
| The planted change | *"Two call sites swapped in one VTT function → `diff` DIVERGED naming the step. A MATCH voids the verifier and STOPs."* | exit 1 DIVERGED at causal step 16, `A: CALL terrainLaw` against `B: CALL isDiagonal`, with both suites at 56/56 | **PASS** — and the strongest form of it: the swap is value-preserving, so the consumer's own tests could not see it and only the recording did |

**The rung's answer.** *(Amended 2026-09-09, in the doc pass, on this
paragraph only: the sentence below read "Eleven of the twelve gated endpoints
and both §10 controls PASS on their own rules", which counted E10's REPORTED
as a PASS. The table above always read REPORTED for it; the count is corrected
here rather than in the table, and no verdict moved.)* **Ten of the twelve
gated endpoints PASS**, and both §10 controls PASS, on their own rules. **One
is a STOP — E6′, on its plain-band clause** — the one clause of its four that
is a timing clause; its manifest, marker and wrapper clauses hold exactly.
**One is REPORTED and gates nothing — E10**, which lands on the second branch
of its own rule: reported, design input, not a STOP.

**The rung therefore ships DONE-WITH-STOP on E6′.** A STOP stands where it
fires: nothing here re-rolls the 22.8678 s wall, moves the band, or renames
the verdict. What the STOP is understood to rest on is written down rather
than argued away — two instrument gaps, §5 gaps 5 and 6 (`e6.sh` runs its one
timed measurement with no load guard, and the band is a five-run min–max with
no slack by construction) — and the disposition is that E6′ is **re-measured
in the next slice under a NEW pre-registration, E6″**, whose band clause is
stated with a derived width. §1 is locked, so nothing about E6′ is restated
here; E6″ is a new commitment, made before its instrument exists, and this
record does not write it.

---

## 5. Gaps found

Seventeen entries, each saying what was MEASURED.

**Four are defects in the instruments** — two found by the dry runs and fixed
before their endpoints read anything (1, 2), and two found only AFTER a number
had been printed (3, 4). **Three are holes in an instrument's procedure**: the
missing load guards and the unrecorded loads (5), the band's shape and the
manifest's ordering (6), and E2′'s ratio being blind to a function the walker
never visits (17). **Three record something this run DID that a reader would
not infer from a verdict**: an instrument re-read after its endpoint had
reported (7), a pre-registered phrase applied in a narrower reading than its
widest (8), and a pinned procedure replaced by a different one (9). **The
remaining seven** (10–16) are facts about the product, the lens or the
consumer that this run turned up and that no rule asked about.

Gaps 5 and 6 are the two the E6′ STOP rests on, and neither is offered as a
reason to discount it.

**1. E7′'s `python ?` needle was a regex, and matched an honest sentence.**
*(Instrument defect, found in a dry run on `typescript/probes`, fixed before
E7′ read any number — commit `6fdeaa7`.)* `python ?` is not "the word python":
it is `info`'s interpreter line as the spike caught it printing on a
TypeScript trace, `python ?  env:6fc1f0a955a4ac5b`, with the `?` where a
Python version would be. Matched as a regex with the space optional it also
matches `exceptions`' refusal — *"the Python rules index exception identity
this trace does not carry"* — which is a sentence written to tell a
TypeScript user why a command refuses. The dry run read 1; the literal reads
0. `threading/_thread` is kept as a word-boundaried pattern for the same
reason in reverse: bare `_thread` is a substring of this recorder's own
`main_thread_ident`.

**2. `arm_line.py` split vitest's `Duration` line on the letter `s`.**
*(Instrument defect, found in a dry run, fixed before the arms ran — commit
`6fdeaa7`.)* On the lens vitest prints `transform 10.26s`; on the small probe
project it prints `transform 123ms`, and the splitter produced `123m` and
raised. It raised rather than recording a wrong number, which is how it was
found; it now parses the unit.

**3. E11's INCOMPLETE needle held one of four wordings — and was found only
AFTER E11(b) printed a number.** Four commands print an incomplete banner and
they print four different sentences (`info_cmd`: *"recording ended without a
finalize pass"*; `caps` and `exceptions_cmd`: *"this recording never
finalized"*; `exceptions_invocation` names the run). The instrument held
`caps`'s sentence as a literal, so it read `info`'s banner as ABSENT when it
was the second line of the output, and **E11(b)'s first reading was 2 of 3**,
with `info_prints_incomplete_banner: false`. The banner was there verbatim.
The needle is now `^INCOMPLETE:` — which is what "the INCOMPLETE banner"
means — and the corrected reading is **3 of 3**. Both readings are stated
here; the corrected one re-read the SAME two traces, which had not changed
and could not, and re-ran no recording. The same defect silently weakened
E11(a)'s "no INCOMPLETE banner" claim, which under the wrong literal could
not have failed; re-derived, (a) still reads 2 of 2, this time having
actually been tested.

**4. The planted change's "names the step" check looked at the wrong line —
also found after the number.** When two runs part inside a task rather than
on the thread stream, the verdict line says `DIVERGED on the tasks (below)`
and the step number is printed two lines later by the task section:
`… at causal step 16:`. The instrument searched only the verdict line, so its
**first reading was 1 of 2** with `verdict_names_the_step: false` — over a
report that named the step plainly. Re-derived from the same saved `diff`
transcript, with no command re-run at all, it reads **2 of 2**. Entries 3 and
4 are one class: a needle aimed at a wording rather than at the thing, which
is the "value that looks like a measurement but is not" bug the discipline
warns about, and both were caught only because the raw transcripts were kept.

**5. Two instruments that time something have no load guard: `e6.sh` and
`e10.sh`.** `arms.sh` waits for the 1-minute load to drop below 4.0 before
every run, because E1′ is a timing endpoint, and it writes each reading into
the artifact (§3's E1′ block). **`e6.sh` does neither** — it never opens
`/proc/loadavg` — and yet its third clause is a timing clause: a wall against
the plain arm's band. **That is the instrument gap under the STOP E6′ fired.**

*What the load actually was, and how that is known.* `/proc/loadavg` was read
BY HAND at roughly 16:32, immediately before `e6.sh` was started, and it read
`0.86 3.39 4.68` — 1-minute 0.86, 5-minute 3.39, 15-minute 4.68, the tail of
372 `sensorium diff` subprocesses that had just finished. **Those three
numbers are in no artifact**: no instrument recorded them, they cannot be
re-derived from anything on disk, and they are quoted here only as the
operator's own observation. They are not evidence that the load caused the
0.1457 s, and this record does not claim it did.

**The plain-after wall stands as measured at 22.8678 s.** It is not re-rolled,
not re-run under a guard, and not averaged with anything: the STOP fired on
the number that was read, and adding a guard to `e6.sh` is work for the E6″
pre-registration in the next slice, not a licence to take the measurement
again in this one.

**`e10.sh` has the same hole and it does not matter here.** E10 times three
ingest repetitions with no load guard either. Its verdict is a comparison of
45.5293 s against a 22.5925 s plain median — a margin of **×2.02**, with the
three repetitions spanning 45.3636–45.5584 s (0.4% apart). No plausible load
effect closes a factor of two, so the missing guard is immaterial to E10's
verdict; it is recorded because the next slice should fix both instruments
together and because "immaterial" is a judgement that should be written down
with its margin rather than left implicit.

**6. E6′'s band is a 5-run min–max, which is a range and not a tolerance.**
Beyond the instrument gap above, the clause itself has no slack by
construction: five runs' min–max on this lens spans 0.41 s (1.8%), and a
sixth run has no reason to land inside it. The three clauses of E6′ that ask
about contamination directly all read clean. Whether "inside the plain band"
should be a band with a stated width — 2 SE of the plain arm, say — is a
ruling for the next slice, and this record does not make it: §1 is locked, the
number is what it is, and the STOP it produced stands.

**And `e6.sh` checks the manifest in the wrong order to cover its own run.**
The script's sequence is: verify the manifest, then do the plain run, then
grep for markers, then list the wrapper directory. So its own `748 OK` is a
statement about the lens BEFORE the last thing that touched it, and the one
run E6′ itself makes is the one run its manifest clause does not audit. The
hole was closed by hand rather than by the instrument — `cd <lens> &&
sha256sum -c <the §2 manifest>` re-taken after E6′ finished, at 16:35 on the
run day and again at 2026-09-09T16:57:12−05:00, **exit 0, 748 OK, 0 FAILED**
both times, with nothing run against the lens in between (§3's E6′ block
carries the same two readings). E6″ should verify the manifest after its own
run, not before it.

**7. E9 was re-read to add a descriptive field, after its number had been
read.** The third of the three re-derivations §3 names, and the only one this
section did not previously carry. After E9's cell was written, `e9.py` was
given a `separator_normalised_identical` field — a derived comparison that
says whether the two name lists agree once the recorder's ` > ` join is
replaced by a space — and re-run over the SAME store, the SAME invocation and
the SAME `e9.json` vitest report, none of which had changed. **E9's `value`
was 0 before and 0 after**, `tasks` 4,278 and `tests_seen` 4,278 both times,
and no threshold moved; what the re-read added was gap 10's characterisation,
which without it would have been a claim in prose with no field behind it.
Recording it because a re-run of an instrument after its endpoint has reported
is exactly the move that needs a paper trail, whether or not it changed a
number — and here it did not.

**8. E4′'s "byte-identical" was applied to part of the report, and that
narrowing is the instrument's, not §1's.** §1 says *"the report
byte-identical"*. `sites.py` compares `{fail_lines, refs}` — the `FAIL`
headers naming the planted file, and every `path:line:col` it printed FOR
that file — and deliberately excludes a third field, `other_refs`, from the
comparison. It excludes it because the two reports differ there: the driven
run's stack carries two frames the plain run does not,

```
❯ <worktree>/typescript/src/rt.mjs:296:39
❯ sensoriumTask <worktree>/typescript/src/rt.mjs:296:23
```

*(Amended 2026-09-09, in the doc pass: the two lines above were quoted
verbatim from vitest, which printed the recorder's runtime by a relative path
out of the lens — four `../` segments and the name of the worktree this rung
was built in. That prefix names this box and nothing about the product, so it
is written `<worktree>`; the file, the line and the column are the run's own
and are unchanged.)*

so the two reports are **not** byte-identical as whole texts, and E4′'s PASS
rests on the narrower reading *"the failing assertion's line and column, and
the test-file frames, byte-identical"* — which is what the endpoint's question
asks (*"Do sites keep their lines and columns?"*) and what its Measurement
column pins (*"one planted failing assertion's line and column as vitest
reports it"*). Both readings are measured and both are in §3: the planted
site's `src/lib/safeUrl.test.ts:44:13` and its `FAIL` header are identical,
and the driven report has two extra frames pointing into the recorder's own
runtime. Naming it because a reader who takes "byte-identical" at its widest
would be entitled to a different verdict, and should not have to diff the logs
to discover which reading was used.

**9. E11(b) did not use §1's pinned `pgrep`; it used the recorder's own
spool.** §1 pins the victim as *"found by `pgrep -f '^[^ ]*node .*forks'`
anchored (never `pkill -f` unanchored: it self-matches)"*. `e11.sh` finds it a
different way: it polls the invocation's spool directory for the `.jsonl`
whose records declare `src/components/inventory/InventoryTab.test.tsx` and
takes the pid out of that spool's own filename (`1568484-0.jsonl` → pid
1568484). The substitution is deliberate and strictly more exact — an anchored
`pgrep` over `forks.js` matches EVERY fork of the pool, of which a 16-core run
has many, and none of their command lines names the test file, so a `pgrep`
would still have needed a second step to pick the right one; the spool IS the
recorder saying which container took which file. The pin's safety intent —
never an unanchored pattern that can match the killing process itself — holds
completely: nothing in this run called `pkill` at all, and the only kill issued
was `kill -9 <one pid>` at a pid read from a filename. The victim's
`/proc/<pid>/cmdline` was logged before the kill and is in the record's
evidence, and it is the vitest fork the pinned pattern describes:
`node … --conditions development …/vitest/dist/workers/forks.js`. Naming it
because a pinned procedure was replaced, which a reader may not infer from a
verdict.

**10. The recorder joins a describe chain with ` > `; vitest's JSON reporter
joins it with a space.** E9's 20-name sample is **not** identical as printed
and **is** identical once ` > ` is replaced by a space — same segments, same
order, 20 of 20. `InventoryTab > renders a resolved item and toggles equip`
against `InventoryTab renders a resolved item and toggles equip`. E9's rule
attaches no threshold to the sample, so this gates nothing; but the endpoint's
question is *"are tests … named as vitest names them?"* and the honest answer
is: the same name, spelled with a visible separator. Whether the recorder
should emit vitest's own `fullName` spelling is a design question this record
raises and does not settle.

**11. E2′'s census set does not include test files, and the run-time transform
excludes something the census never sees.** The census walks `src` with
`.test.`/`.spec.`/`.d.ts`/setup files skipped, and over that set reports
`excluded: {}` — no exclusions at all. `info` on a call-arm trace reports the
RUN's tally for the same lens: `files: 725 transformed; excluded: 344
(vitest-hoisted-factory x344)`. The two numbers are about different sets and
neither contradicts the other, but E2′'s rule is *"every exclusion named"* and
the only exclusion this lens actually produces lives entirely outside the set
E2′ measures. The exclusion IS named where it occurs; the gap is that the
census cannot see it.

**12. Eight of the lens's 372 test files record differently on two runs of the
same suite.** Spec §8 asks for this count without a gate and reads a non-zero
as *"a finding about the consumer"*. It is 8 of 372 (2.2%), the eight are
named in §3.4, and none of them is `useMeshVoice.test.tsx`, whose twenty
recordings were all identical (E3-TS). Nothing here is a recorder defect: the
comparator refused nothing and mis-called nothing; eight VTT test files take
different code paths on different runs.

**13. The driver's conversion, not its recording, is what costs.** E1′'s call
arm moved the harness wall by 13.2% (25.5832 s against 22.5925 s) while the
DRIVER's total wall was 3.1× plain, and E10 measures the difference directly:
45.53 s to convert 372 spools and 414 MB. The call arm's total wall also
climbed run to run — 45.0, 63.6, 71.1, 71.2, 70.3 s — with the harness wall
flat, so the conversion slowed as the store filled. That is E10's design
input with a second, independent reading of the same effect beside it.

**14. E11(a)'s trace came from a driven probe run, not from E4′'s.** E4′ runs
the probes DIRECTLY (`SENSORIUM_PROBE_DIRECT=1`), which writes spools and no
`invocation.json`, and `sensorium ts ingest` refuses a directory that no
driver wrote — correctly, since a spool set with no driver record cannot say
what produced it. E11(a) needs a TRACE, so the probes were additionally
recorded through the driver and (a) read that trace. The two runs agree: the
checker over the driven run's spool read the same **77 checks, 0 failures** as
the direct one. Naming it because the brief expected one probe run and there
were two.

**15. The control copies are not byte-for-byte the lens.** `copy_lens`
excludes `node_modules` (symlinked to the lens's, as the brief specifies) and
three more directories — `dist`, `.pytest_cache` and `e2e-shots`: build
output, a pytest cache and screenshots, none of which a recorded test reads.
Both
controls' `before` recordings read `1 passed (1)` / `56 passed (56)`, the same
as the lens's own, so nothing the recorded test file needs was left behind;
recorded because it is a difference between the copies and the lens.

**16. E2′'s ratio held at 1.000 while its DENOMINATOR moved.** The spike
measured 5,403 of 5,403 over 368 files with `excluded: {}` and a bloat of
1.2421; this run measures **5,378 of 5,378 over 367 files**, `excluded: {}`,
bloat 1.2543 — one file and 25 sites fewer on the same lens at the same
commit. The two numbers come from two DIFFERENT census instruments (the
spike's, and the `census.mjs` in this tree, which also reports `by_kind` in
the contract's frame kinds — `function` 5,094, `coroutine` 284 — where the
spike reported TypeScript AST node kinds). §1's rule gates the ratio, and the
ratio is 1.000 both times; the totals are not comparable across two
instruments and this record does not treat them as a regression. Naming it
because "5,403 of 5,403 was measured" is written into the rule, and a reader
who takes 5,378 for a shortfall would be reading two lenses as one.

**17. E2′'s ratio cannot see a function the transform's walker never
visits.** `eligible` is `instrumented` plus the transform's own NAMED
function-level exclusions, so a function-like node the walker does not reach
appears in neither term and the ratio stays 1.000 by construction. That is a
limit of the endpoint, not a defect found in it: the exclusion channel is
demonstrably live on this lens — `info` on a call-arm trace reports the RUN's
tally as `files: 725 transformed; excluded: 344 (vitest-hoisted-factory
x344)` — so the empty `excluded` here is a measured absence over the census
set and not a field nobody writes. What E2′ proves is that the transform
instrumented everything it SAW; what would prove it saw everything is a
different instrument, and this rung did not build one.
