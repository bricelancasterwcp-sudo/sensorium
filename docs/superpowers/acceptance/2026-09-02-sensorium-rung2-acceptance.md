# Rung 2 — acceptance (pre-registered)

## 1. Pre-registration

Lens for every endpoint: dev profile; the bloomery **clone** at `/mnt/extra/sensorium-rung2/bloomery` @ `e209ed9` with `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/bloomery-target` (sources and target on different filesystems — the configuration this plan ships); `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir`; this box (AMD Ryzen 7 9800X3D, 16 threads, `powersave` governor); `sensorium-rt` at `opt-level = 3`; tier `call` = CALL and RETURN with outcome and captured return value, PANIC, tasks and `spawn_child` naming — no `?` sites, no locals, no output capture; default `--test-threads` unless a row says otherwise.

| Id | Question | Measurement | Decision rule | Derivation of the threshold |
|---|---|---|---|---|
| E2′ | Does the rung-2 transformer still cover bloomery? | From the manifests of one workspace-wide instrumented `--no-run` on the clone: instrumented fn items ÷ eligible fn items, numerator and denominator **over the same file set** (`crates/*/src` + `crates/*/tests`, counted by `sensorium-transform`'s own census: every `fn` item with a body except `const fn` and `extern` fns); units that fell back; spawn sites rewritten and unwrapped (reported) | floor 98% of eligible fn items; **any fell-back unit is a finding that stops the rung until explained** | spec §8 E2, re-read because the transformer changed (exit wraps, spawn rewrite); rung 1 read 2051/2051; the same-file-set rule is findings §5.14's lesson written into the row |
| E3 | Does the comparator report false DIVERGED? | Build `-p bloomery-daemon --lib` once (`--no-run`), record the test binary's sha256; run `cargo sensorium test -p bloomery-daemon --lib` 20 times with no rebuild (sha256 asserted equal before every run); `sensorium diff <run 1> <run K>` for K = 2..20 | **DIVERGED 0/19 and REFUSED 0/19**; any DIVERGED or REFUSED = the comparator or the recorder is wrong — STOP and diagnose before any other endpoint | spec §8 E3 verbatim; sanity: rung 1's identical `--lib` pair read MATCH with all 57 task streams matched, so a DIVERGED here is new behaviour of new code |
| E5 | Does `diff --ignore-moves` verify a source-file split? | A = the clone @ `e209ed9`; B = branch `e5-split`: `crates/bloomery-daemon/src/task/registry.rs` split into a `registry/` directory module by moving items verbatim (no body edited, `mod tests` stays where its path is `task::registry::tests`); C = branch `e5-planted`: B plus ONE planted change — two consecutive, independent call statements inside one non-test fn of the registry swapped. Each arm: `cargo sensorium test -p bloomery-daemon --lib -- task::registry`, then `sensorium diff --ignore-moves <A> <B>` and `<A> <C>`; plain `diff <A> <B>` reported | **A/B = `MATCH modulo location` with ≥ 1 moved, 0 added, 0 removed, every `task::registry::tests::*` task paired by name; A/C = `DIVERGED` naming a step inside the swapped fn.** A/C reading MATCH → the verifier is void, STOP; A/B reading DIVERGED → report the step, and if it is a test-order change (a test moved between discovery units) read it as the instrument working (spec §10 amended 2026-09-02), else STOP | spec §8 E5 and §10 rung 2; libtest orders tests by name, so a split that keeps the tests' module path keeps their order |
| E7 | Are line numbers and paths preserved? | (a) the probe workspace as in rung 1: a `#[should_panic]` test with a known message, one whose assert message embeds `file!()`/`line!()`, `RUST_BACKTRACE=1`, `--test-threads=1 -- --nocapture`, plain vs off vs call, durations and rustc's `(<tid>)` masked; (b) **on the clone**: `cargo test -p bloomery-daemon --lib -- --test-threads=1` output, plain vs call, durations masked | any difference in a `panicked at <file>:<line>:<col>`, a `file!()`/`line!()` value, a backtrace frame's `<file>:<line>`, or in (b) any difference in a `test … ok/FAILED` line or the `test result:` line → STOP | spec §8 E7; (b) closes findings §5.17 (E7 had only ever run on the probe) |
| E8 | Does cargo freshness survive, and can a plain build be contaminated? | On the clone, target on `/mnt/extra`, counting `Compiling`/`Fresh` from `cargo -v` **and** asserting the expected `Fresh` set: (a) instrumented `--no-run` twice → the second compiles no workspace unit; (b) append one comment line to `crates/bloomery-core/src/lib.rs` → exactly `bloomery-core` and its dependents recompile, then `git checkout` restores it; (c) plain `--no-run` after an instrumented build → no workspace unit compiles AND the plain `--lib` binary run with `SENSORIUM_SPOOL` set writes 0 spool files while the instrumented one writes > 0; (d) instrumented `--no-run` after (c) → no workspace unit compiles | any failed check → STOP | spec §8 E8; (b) on bloomery for the first time — the clone is writable |

Reported without a gate (each with `n` and lens): wall of `cargo test -p bloomery-daemon --lib` plain vs call, 5 rounds interleaved P,C then C,P alternating with a 10 s cool-down, so the return-value capture cost is visible against rung 1's call/plain ×1.0103; events per second and bytes per event; conversion wall for the whole invocation against rung 1's 22.7 s; live threads at process exit and, for each, whether its last record is complete (the `MAP_SHARED` claim); `seq_gaps` and `records_dropped` totals; `truncated_count`; `exit_status_basis` histogram across the invocation (`waited` / `unwitnessed`); `child_runs` counts; `spawn_child` sites rewritten / unwrapped; the driver's fixed cost (release build) and the runtime's rlib build time.

`results.json` schema (none-versus-zero): every measurement is `{"value": <number|null>, "n": <int>, "lens": <string>, "dropped": [<reason>...]}`; a `null` value with a non-empty `dropped` list is the only representation of "not measured"; `0` is measured-and-zero; the renderer refuses to print a `null` row as anything but `not measured (<reason>)`.

---

## 2. Ambient pins (preflight, recorded 2026-09-02 before any code exists)

| Item | Command | Value |
|---|---|---|
| rustc | `rustc -V` | `rustc 1.96.0 (ac68faa20 2026-05-25)` |
| cargo | `cargo -V` | `cargo 1.96.0 (30a34c682 2026-05-25)` |
| toolchains | `rustup toolchain list` | `stable-x86_64-unknown-linux-gnu (active, default)` — stable only, no nightly installed |
| nproc | `nproc` | `16` |
| governor | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | `powersave` |
| RUSTFLAGS | `echo "RUSTFLAGS=[$RUSTFLAGS]"` | `RUSTFLAGS=[]` (unset) |
| CARGO_INCREMENTAL | `echo "CARGO_INCREMENTAL=[$CARGO_INCREMENTAL]"` | `CARGO_INCREMENTAL=[]` (unset) |
| RUSTC_WRAPPER | `echo "RUSTC_WRAPPER=[$RUSTC_WRAPPER]"` | `RUSTC_WRAPPER=[]` (unset) |
| RUSTDOCFLAGS | `echo "RUSTDOCFLAGS=[$RUSTDOCFLAGS]"` | `RUSTDOCFLAGS=[]` (unset) |
| free disk `/` | `df -h /` | `15G` available on `/dev/nvme0n1p2` (99% used, 915G total) — floor is 3 GB, this passes with 12 GB to spare |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `114G` available on `/dev/nvme1n1p1` (75% used, 469G total) — floor is 8 GB, this passes with 106 GB to spare |
| 1-minute load | `cat /proc/loadavg` (checked immediately before the clone, gating the preflight decision to proceed) | `0.21 0.26 0.26 1/2183 3604592` — 1-minute load 0.21, well under the 4.0 refusal threshold |
| clone HEAD | `git -C /mnt/extra/sensorium-rung2/bloomery rev-parse HEAD` | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| clone status | `git -C /mnt/extra/sensorium-rung2/bloomery status --porcelain` | empty (clean) |
| clone origin | `git -C /mnt/extra/sensorium-rung2/bloomery remote -v` | `origin  /home/brice/workspace/bloomery (fetch/push)` — local tree, nothing pushable remotely |
| `~/workspace/bloomery` HEAD (before clone) | `git -C /home/brice/workspace/bloomery rev-parse HEAD` | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| `~/workspace/bloomery` HEAD (after clone) | `git -C /home/brice/workspace/bloomery rev-parse HEAD` | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` — unchanged |
| `~/workspace/bloomery` status (before and after clone) | `git -C /home/brice/workspace/bloomery status --porcelain` | empty (clean) both times |
| absence: user cargo config (toml) | `[ -e ~/.cargo/config.toml ]` | absent |
| absence: user cargo config (legacy) | `[ -e ~/.cargo/config ]` | absent |
| absence: clone cargo config | `[ -e /mnt/extra/sensorium-rung2/bloomery/.cargo/config.toml ]` | absent |
| clone `Cargo.lock` sha256 | `sha256sum /mnt/extra/sensorium-rung2/bloomery/Cargo.lock` | `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` |
| uv | `uv --version` | `uv 0.11.18 (x86_64-unknown-linux-gnu)` |
| `.venv` python | `.venv/bin/python -V` (sensorium repo) | `Python 3.14.4` |
| sensorium version | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.5.0` |
| mount: `/mnt/extra` | `findmnt -no SOURCE,FSTYPE /mnt/extra` | `/dev/nvme1n1p1 ext4` |
| mount: `/` | `findmnt -no SOURCE,FSTYPE /` | `/dev/nvme0n1p2 ext4` — a different block device and filesystem from `/mnt/extra`; every artifact directory (`rust-target`, `bloomery-target`, `corpus-target`, `sensorium-dir`) and the clone itself live on `/mnt/extra`, off the chronically near-full root filesystem |

**Preflight verdict:** all three refusal rules pass (`/mnt/extra` free 114G ≥ 8G; `/` free 15G ≥ 3G; 1-minute load 0.21 ≤ 4.0) — proceeded, did not BLOCK.

### Re-recorded immediately before the measured run (2026-09-03)

The table above was recorded on 2026-09-02, before any recorder code existed. These
are the same ambient facts as the acceptance runner itself read them, in its own
preflight, seconds before the first measured build. They are `results.json`'s
`pins` block, transcribed.

| Item | Value |
|---|---|
| run started | `2026-09-03T16:12:15-0500` (finished `2026-09-03T16:55:47-0500`) |
| branch commit under test | `e1993dfe77f0cb678b8921835eaa00cf03874194` on `feat/rung2-recorder-v1` |
| driver | `cargo-sensorium` 0.1.0, release, sha256 `e897ced8de9c5c3421719039030bc691159fcda30f93f7f6799652ed9fd392dd` — built from that commit before the run and asserted unchanged after it (`driver_unchanged: true`) |
| census driver | sha256 `367cc9055cf20669e07b37893c1394667d6bb41a69cbf1471b880240cbe5dc07` — a 35-line binary over `sensorium-transform::census`, source in the ledger |
| reader | `sensorium` 0.6.0 on Python 3.14.4, from the repo venv |
| rustc / cargo | `rustc 1.96.0 (ac68faa20 2026-05-25)` / `cargo 1.96.0 (30a34c682 2026-05-25)` |
| governor / nproc | `powersave` / 16 |
| RUSTFLAGS, CARGO_INCREMENTAL, RUSTC_WRAPPER, RUSTDOCFLAGS | all empty (unset) |
| clone HEAD | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`, `git status --porcelain` empty, detached |
| clone `Cargo.lock` sha256 | `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` — unchanged after the run |
| source tree (read-only) | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`, porcelain empty, **both before and after** (`source_bloomery_unchanged: true`) |
| artifact disk free | 115.12 GB before, 105.16 GB after (floor 8 GB) |
| root disk free | 13.82 GB before, 13.82 GB after (floor 3 GB) |
| 1-minute load at start | 0.30 (refusal threshold 4.0) |
| target directory | emptied at `2026-09-03T16:12:15-0500`; it held **0 bytes** (never written before this run), so E8's plain `--no-run` is a genuinely clean build |
| target emptied again for E2′ | `2026-09-03T16:12:37-0500`, removing 9 480 938 772 bytes — see §3's E2′ lens for why the stronger act is the correct one |

**Preflight verdict (the run's own):** all three refusal rules pass — proceeded, did not BLOCK.

**Independent check of the denominator, run by hand before the launch.**
`SENSORIUM_BLOOMERY_CLONE=<clone> cargo test -p sensorium-transform --test census -- --nocapture`
read the clone as: 191 files walked, 191 measured, 2056 `fn` items with a body,
5 `const fn`, 0 `extern` fn, 0 `async fn`, **2051 eligible**, 2051 instrumented,
8 spawn sites wrapped, 8 literal `std::thread::spawn(`, 0 line moves, 0 re-parse
failures. The census driver the runner uses reproduced every one of those totals
from the same crate's `census` function. Two instruments, one number.

## 3. Results

**Provenance of this section.** It is rendered by `rust/tests/render_acceptance.py` from `results.json`, which was assembled at 2026-09-03T17:35:04-0500 by `rust/tests/acceptance.py --assemble` from `results-raw.json` — the raw facts the run itself recorded — under the committed schema. Re-derived from the raw facts the run recorded, under the committed schema; no gated arm was re-run and no gated value was re-measured -- against the assembly the run itself wrote, only lens text differs, plus the dated `addendum` block when `results-addendum-raw.json` is present, which is a later reading of reported-without-a-gate items and of nothing else. The committed `…acceptance.results.json` is that assembly, byte for byte.

Measured on the §2 pins. Runner: `rust/tests/acceptance.py` (raw logs and `results-raw.json` in the gitignored ledger). Started 2026-09-03T16:12:14-0500, finished 2026-09-03T16:55:47-0500. Every cell below is a number with its `n` and its lens, or `not measured (<reason>)`.

| Id | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| E2′ | 100.0% (rule: floor 98% of eligible fn items; any fell-back unit stops the rung) | 2051 | instrumented 2051 / 2051 eligible fn items, both over crates/*/src + crates/*/tests; numerator = DISTINCT (fil… | none |
| E3 | 0 (rule: DIVERGED 0/19 and REFUSED 0/19) | 19 | DIVERGED + REFUSED verdicts over 19 diffs; `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs … | none |
| E5 | 2 (rule: A/B MATCH modulo location with ≥1 moved, 0 added, 0 removed, every task paired; A/C DIVERGED) | 6 | pre-registered E5 conditions not met, of 6; three arms on three trees (original / split / split + one planted … | none |
| E7 | 0 (rule: any difference stops the rung) | 7 | E7(a) failed checks + E7(b) masked differences; (a) `rust/tests/mechanics.sh` on the probe workspace: panic lo… | none |
| E8 | 0 (rule: any failed check stops the rung) | 5 | failed checks of 5; on the measured workspace with its target directory emptied first, counting Compiling/Fres… | none |

### E2′ — transformer coverage of the measured workspace

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| instrumented fn items, workspace-wide build | 2051 | 108 | distinct fn items from the workspace-wide instrumented --no-run | none |
| eligible fn items, same file set | 2051 | 191 | census eligible fn items over crates/*/src + crates/*/tests | none |
| instrumented fn items, package build | 1723 | 77 | distinct fn items from the from-scratch instrumented package build, read before E8(b) touched a source file | none |
| eligible fn items, the files that build reaches | 1723 | 158 | census eligible fn items over the files that package build reaches: crates/bloomery-core/src/, crates/bloomery… | none |
| package files outside the denominator's directories | 0 | 77 | files the package build instrumented that are NOT under the denominator's directories -- anything but 0 means … | none |
| units that fell back to the real tree | 0 | 108 | manifests with fell_back true in the workspace-wide build | none |
| `fell back to the real tree` stderr lines | 0 | 1 | `fell back to the real tree` lines across every E8 build log | none |
| files a module walk could not reach | 0 | 108 | files a unit's module walk could not reach, unioned | none |
| fn items skipped by rule | 10 | 108 | fn items skipped by rule (const/extern/async/macro) | none |
| spawn sites rewritten | 13 | 108 | spawn sites replaced with ::sensorium_rt::spawn_child -- the RAW SUM over the build's manifests, not a count o… | none |
| spawn sites declared, not rewritten | 0 | 108 | spawn shapes left alone and declared with a reason | none |
| declaring units (crate_name, crate_type) | 106 | 108 | distinct (crate_name, crate_type) pairs declaring a manifest | none |
| manifests outside the measured build's unit set | 0 | 108 | manifest files present but NOT in the measured build's unit set | none |
| units whose mirror was opened and checked | 108 | 108 | units whose mirror crate root was opened and found to name that unit's own -C metadata; a check that examined … | none |
| mirrors naming another unit's metadata | 0 | 108 | mirrors naming another unit's metadata | none |

Denominators, both from `sensorium-transform`'s own `census` — the parser that did the instrumenting — over the same tree:

| Denominator (eligible fn items) | Numerator over the SAME files | Reading |
|---|---|---|
| the whole workspace (2051) | 2051 | 100.0% ← §4's reading |
| the files a package build reaches (1723) | 1723 | 100.0% |

Census: 191 files walked, 191 parsed; 2056 `fn` items with a body, 5 `const fn`, 0 `extern` fn, 0 `async fn` → 2051 eligible.

### E3 — does the comparator report a false DIVERGED?

Test binary sha256 `143a4a4dc65ba31e494c23cbfbde91d0c6fc6a8ed51fb9218e9ae6e7a2497986`, asserted equal before every recorded run.

| K | run 1 | run K | verdict | CLI exit |
|---|---|---|---|---|
| 2 | `20260903-161246-4c1554` | `20260903-161301-61dc77` | MATCH | 0 |
| 3 | `20260903-161246-4c1554` | `20260903-161313-eaa146` | MATCH | 0 |
| 4 | `20260903-161246-4c1554` | `20260903-161325-2779d6` | MATCH | 0 |
| 5 | `20260903-161246-4c1554` | `20260903-161335-c50865` | MATCH | 0 |
| 6 | `20260903-161246-4c1554` | `20260903-161347-aebdeb` | MATCH | 0 |
| 7 | `20260903-161246-4c1554` | `20260903-161359-b1a87d` | MATCH | 0 |
| 8 | `20260903-161246-4c1554` | `20260903-161410-9d33d7` | MATCH | 0 |
| 9 | `20260903-161246-4c1554` | `20260903-161423-e2a13a` | MATCH | 0 |
| 10 | `20260903-161246-4c1554` | `20260903-161435-8f939f` | MATCH | 0 |
| 11 | `20260903-161246-4c1554` | `20260903-161447-ad509e` | MATCH | 0 |
| 12 | `20260903-161246-4c1554` | `20260903-161500-62fc84` | MATCH | 0 |
| 13 | `20260903-161246-4c1554` | `20260903-161513-208d4f` | MATCH | 0 |
| 14 | `20260903-161246-4c1554` | `20260903-161525-6a9dfc` | MATCH | 0 |
| 15 | `20260903-161246-4c1554` | `20260903-161537-0e6f0e` | MATCH | 0 |
| 16 | `20260903-161246-4c1554` | `20260903-161550-2bd9ff` | MATCH | 0 |
| 17 | `20260903-161246-4c1554` | `20260903-161603-2c713b` | MATCH | 0 |
| 18 | `20260903-161246-4c1554` | `20260903-161616-4b54e3` | MATCH | 0 |
| 19 | `20260903-161246-4c1554` | `20260903-161629-57fd1d` | MATCH | 0 |
| 20 | `20260903-161246-4c1554` | `20260903-161641-df9e1b` | MATCH | 0 |

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| DIVERGED verdicts | 0 | 19 | `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE test binary built once; the binary's… | none |
| REFUSED verdicts | 0 | 19 | `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE test binary built once; the binary's… | none |
| MATCH verdicts | 19 | 19 | `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE test binary built once; the binary's… | none |
| runs that produced a trace | 20 | 20 | recorded runs that produced a trace | none |
| runs whose binary sha256 moved | 0 | 20 | runs whose binary sha256 differed from run 1's | none |

### E5 — does `diff --ignore-moves` verify a source-file split?

| Arm | Tree | run | events | threads | tests run |
|---|---|---|---|---|---|
| A | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` | `20260903-161845-767c88` | 890 | 10 | 6 |
| B | `e5-split` | `20260903-161847-f822c5` | 890 | 10 | 6 |
| C | `e5-planted` | `20260903-161849-c2af01` | 890 | 10 | 6 |

| Pre-registered condition | Met |
|---|---|
| `ab_verdict_is_match` | NO |
| `ab_moved_at_least_one` | yes |
| `ab_zero_added` | yes |
| `ab_zero_removed` | yes |
| `ab_every_task_paired` | NO |
| `ac_verdict_is_diverged` | yes |

| E5 conditions not met | 2 | 6 | pre-registered E5 conditions not met, of 6; three arms on three trees (original / split / split + one planted … | none |

**A/B `--ignore-moves`** — `sensorium diff --ignore-moves 20260903-161845-767c88 20260903-161847-f822c5`, verbatim:

```
A 20260903-161845-767c88: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260903-161847-f822c5: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
note: A recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)
tasks: DIVERGED -- 10 task stream(s) on A, 10 on B; only in A: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 04afbcbcacf6, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 63737389821f; only in B: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 04afbcbcacf6, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 63737389821f; the ordering between tasks is not compared
moves:
  moved: OrganDecision::off  registry.rs -> mod.rs
  moved: TaskRegistry::get  registry.rs -> mod.rs
  moved: TaskRegistry::new  registry.rs -> mod.rs
  moved: TaskRegistry::spawn_task  registry.rs -> mod.rs
  moved: classify_probe  registry.rs -> organ.rs
  moved: contained  registry.rs -> helpers.rs
  moved: degrade  registry.rs -> helpers.rs
  moved: lock_entries  registry.rs -> helpers.rs
  moved: organ_after_run  registry.rs -> organ.rs
  moved: organ_before_run  registry.rs -> organ.rs
  moved: panic_message  registry.rs -> helpers.rs
  moved: panic_note  registry.rs -> helpers.rs
  ... +16 more moved
```

**A/C `--ignore-moves`** — `sensorium diff --ignore-moves 20260903-161845-767c88 20260903-161849-c2af01`, verbatim:

```
A 20260903-161845-767c88: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260903-161849-c2af01: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
note: A recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)
tasks: DIVERGED -- 10 task stream(s) on A, 10 on B; only in A: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 04afbcbcacf6, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion eb531e6a661d, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic 175adcac1853, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 63737389821f; only in B: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 04afbcbcacf6, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion f5438bbd0630, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic 00f0f252acd4, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 5976ef054dbe, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 63737389821f; the ordering between tasks is not compared
first difference inside task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion (A task t4, B task t5) at causal step 4:
  A:      e65 CALL    Journal::open  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-core/src/journal.rs)
  B:      e38 CALL    ImageStore::new  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/agents.rs)
drill into A: sensorium tree 20260903-161845-767c88 --around e65
drill into B: sensorium tree 20260903-161849-c2af01 --around e38
moves:
  moved: OrganDecision::off  registry.rs -> mod.rs
  moved: TaskRegistry::get  registry.rs -> mod.rs
  moved: TaskRegistry::new  registry.rs -> mod.rs
  moved: TaskRegistry::spawn_task  registry.rs -> mod.rs
  moved: classify_probe  registry.rs -> organ.rs
  moved: contained  registry.rs -> helpers.rs
  moved: degrade  registry.rs -> helpers.rs
  moved: lock_entries  registry.rs -> helpers.rs
  moved: organ_after_run  registry.rs -> organ.rs
  moved: organ_before_run  registry.rs -> organ.rs
  moved: panic_message  registry.rs -> helpers.rs
  moved: panic_note  registry.rs -> helpers.rs
  ... +16 more moved
```

**A/B plain `diff` (reported)** — `sensorium diff 20260903-161845-767c88 20260903-161847-f822c5`, verbatim:

```
A 20260903-161845-767c88: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260903-161847-f822c5: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
note: A recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)
tasks: DIVERGED -- 10 task stream(s) on A, 10 on B; only in A: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager 26a265597336, task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 5da1393dcf56, task::registry::tests::classify_probe_reads_only_completed_runs_and_only_real_exit_codes 36ff86c6f2f7, task::registry::tests::contained_catches_a_panic_journals_it_and_lets_the_caller_continue c63a56b6024d, task::registry::tests::get_on_unknown_task_id_is_none e833efccb6ca, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion 4d3f4bbfbc54, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 f40193423b12, task::registry::tests::task_ids_are_unique_and_monotonic 3a0ca087b26a, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 47d897532d1b, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry.rs:769 f40193423b12; only in B: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager ed73375d7a1d, task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 0763e6a2f9a4, task::registry::tests::classify_probe_reads_only_completed_runs_and_only_real_exit_codes 3bd10a0c2c57, task::registry::tests::contained_catches_a_panic_journals_it_and_lets_the_caller_continue bf5999564745, task::registry::tests::get_on_unknown_task_id_is_none 873c6645ba56, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion b165faa53908, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 2d03ae901491, task::registry::tests::task_ids_are_unique_and_monotonic d0e11f792e4a, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 2d03ae901491, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248 82e1d6d4fbdc; the ordering between tasks is not compared
first difference inside task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager (A task t3, B task t7) at causal step 0:
  A:      e1 CALL    tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs)
  B:      e40 CALL    tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry/mod.rs)
drill into A: sensorium tree 20260903-161845-767c88 --around e1
drill into B: sensorium tree 20260903-161847-f822c5 --around e40
```

**A/C, one task (drill-down)** — `sensorium diff --ignore-moves --task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion 20260903-161845-767c88 20260903-161849-c2af01`, verbatim:

```
A 20260903-161845-767c88: compared: task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion (t4)
B 20260903-161849-c2af01: compared: task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion (t5)
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
note: only task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion was compared -- nothing is claimed here about the thread streams, the other tasks, or the order any of them ran in
verdict: DIVERGED at causal step 4
  common  e6 CALL    tests::fresh_dir  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs) (paired with mod.rs)
  common  e15 RETURN  tests::fresh_dir  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs) (paired with mod.rs)
  common  e18 CALL    tests::build_pager  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs) (paired with mod.rs)
  A:      e65 CALL    Journal::open  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-core/src/journal.rs)
  B:      e38 CALL    ImageStore::new  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/agents.rs)
drill into A: sensorium tree 20260903-161845-767c88 --around e65
drill into B: sensorium tree 20260903-161849-c2af01 --around e38
moves:
  moved: OrganDecision::off  registry.rs -> mod.rs
  moved: TaskRegistry::get  registry.rs -> mod.rs
  moved: TaskRegistry::new  registry.rs -> mod.rs
  moved: TaskRegistry::spawn_task  registry.rs -> mod.rs
  moved: classify_probe  registry.rs -> organ.rs
  moved: contained  registry.rs -> helpers.rs
  moved: degrade  registry.rs -> helpers.rs
  moved: lock_entries  registry.rs -> helpers.rs
  moved: organ_after_run  registry.rs -> organ.rs
  moved: organ_before_run  registry.rs -> organ.rs
  moved: panic_message  registry.rs -> helpers.rs
  moved: panic_note  registry.rs -> helpers.rs
  ... +16 more moved
```

### E7 — line numbers, paths and backtraces

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| (a) E7 checks passed on the probe | 6 | 6 | E7 checks that passed in mechanics.sh | none |
| (a) E7 checks failed on the probe | 0 | 6 | E7 checks that failed in mechanics.sh | none |
| (a) mechanics.sh checks passed | 44 | 1 | every check mechanics.sh passed (E7 and E8 on the probe, and the rest of rust/HONESTY.md's falsifiable half) | none |
| (a) mechanics.sh checks failed | 0 | 1 | every check mechanics.sh failed | none |
| (b) differences, plain vs call | 0 | 56 | differences in the masked libtest section, the `test result:` line, or a panic location, plain vs call | none |
| (b) panic locations on the plain side | 0 | 2 | `panicked at <file>:<line>:<col>` locations on the plain side -- 0 would make the location comparison vacuous,… | none |
| (b) spool files the instrumented arm wrote | 60 | 1 | spool files the instrumented arm wrote -- 0 would mean E7(b) compared a tool that did nothing | none |

The driver's sha256 was unchanged across mechanics.sh: True.

### E8 — cargo freshness, and contamination of a plain build

| Check | Result | Compiled | Fresh |
|---|---|---|---|
| `a_second_instrumented_compiles_nothing` | PASS | `[]` | `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` |
| `c_plain_after_instrumented_compiles_nothing` | PASS | `[]` | `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` |
| (c) sentinel: the plain binary writes no spool, the instrumented one does | PASS | plain wrote 0 spool files | instrumented wrote 58 |
| `d_instrumented_after_plain_compiles_nothing` | PASS | `[]` | `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` |
| `b_touch_recompiles_that_unit_and_its_dependents` | PASS | `['bloomery-core', 'bloomery-daemon']` | `['bloomery-substrate']` |

The expected `Fresh` set is `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` — asserted, not merely 'compiled nothing', because a build that dies before its first `Compiling` line also compiles nothing.

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| baseline build wall (s) | 7.157 | 1 | wall of the plain `--no-run` on an EMPTIED target directory: a genuinely clean build of this package's whole b… | none |
| instrumented build wall (s) | 6.889 | 1 | wall of the first instrumented `--no-run` on the same emptied target | none |

### Reported without a gate

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| wall, plain median (s) | 0.059 | 5 | wall clock of `cargo test <pkg> --lib` (P) versus `cargo sensorium test <pkg> --lib` (C), binaries pre-built, … | none |
| wall, call median (s) | 1.666 | 5 | wall clock of `cargo test <pkg> --lib` (P) versus `cargo sensorium test <pkg> --lib` (C), binaries pre-built, … | none |
| wall ratio call/plain | 28.2373 | 5 | median(call)/median(plain); wall clock of `cargo test <pkg> --lib` (P) versus `cargo sensorium test <pkg> --li… | none |
| processes in one whole invocation | 119 | 1 | traces converted from one `cargo sensorium test -p <pkg>` invocation: every test binary plus every instrumente… | none |
| events in one whole invocation | 134394 | 119 | CALL/RETURN/PANIC records converted | none |
| trace bytes | 32198656 | 119 | sum of the format-4 .db files | none |
| spool bytes | 13789264 | 119 | sum of the on-disk spool files | none |
| bytes per event (trace) | 239.584 | 134394 | trace bytes / events | none |
| bytes per event (spool) | 102.603 | 134394 | spool bytes / events (24 B per record plus one header per thread) | none |
| events per second of suite wall | 123.5 | 119 | events / the whole invocation's wall, conversion included -- an order of magnitude for the suite, not a record… | none |
| conversion wall (s) | 1118.867 | 119 | `cargo-sensorium convert <spool>` over the SAME spool the invocation just converted in-process, so the number … | none |
| child runs named by a parent | 48 | 119 | child run ids named by a parent trace | none |
| live threads at process exit | 100 | 119 | threads with no THREAD_END record at process exit, summed over every trace of the invocation | none |
| live threads with a torn last record | 0 | 1250 | spool files whose last record runs past the end of the file: the MAP_SHARED claim, read from the spool bytes r… | none |
| seq gaps | 0 | 119 | seq gaps summed over the invocation's traces | none |
| records dropped | 0 | 119 | records the runtime dropped, summed | none |
| truncated captures | 5729 | 119 | captured values truncated at the repr cap, summed | none |
| panics unrecorded | 0 | 119 | panics the runtime saw but could not attribute | none |
| manifests unscoped | 0 | 119 | manifests with no workspace_root -- 0 is the expected reading on a from-scratch target | none |
| exit_status_basis across the invocation | waited x 71, unwitnessed x 48 | 119 | the basis each process's `exit_status` was written on, one per trace: `waited` = the target runner spawned tha… | none |
| driver fixed cost (s) | 0.021 | 3 | median of 3 no-op `--no-run` builds through the release driver minus the median of 3 straight to cargo, same p… | none |
| runtime rlib build (s) | 0.153 | 1 | one `--no-run` with <target>/sensorium/rt removed, minus the warm no-op driver median above: the runtime's own… | none |
| mean wall of one recorded --lib run (s) | 12.38 | 20 | mean wall of one recorded `--lib` invocation during E3 (build Fresh, conversion included) | none |

| Round | P (plain) | C (call) |
|---|---|---|
| 1 | 0.059 s | 3.939 s |
| 2 | 0.084 s | 1.661 s |
| 3 | 0.057 s | 1.689 s |
| 4 | 0.07 s | 1.664 s |
| 5 | 0.057 s | 1.666 s |
| **median** | 0.059 s | 1.666 s |
| **min** | 0.057 s | 1.661 s |
| **max** | 0.084 s | 3.939 s |

### 3.1 Addendum — reported items re-measured after the converter fix (commit `c90cb72`, 2026-09-03)

**Nothing gated is re-measured here.** The five verdicts of §4 and every §3 cell they rest on are the numbers the acceptance run recorded at `46074ef`, and they stand. What changed since: the converter's one-transaction-per-trace fix (`synchronous=NORMAL` under WAL) landed after the acceptance run, so the reported-without-a-gate items -- and only those -- were read again. Measured with the release driver built from `c90cb72c6b51f5d61ac13b0bf20b12ebc29282b0`, sha256 `723fbb4839cea8b277a0195f904ab01a2676bfa1e6ba62f29fbc8c7645e61ff0`, 2026-09-03T17:30:32-0500 → 2026-09-03T17:32:19-0500, clone at `e209ed9b00f7`, 1-minute load 0.35 at the start.

| Item | at `46074ef` | at `c90cb72` | n | Lens of the re-measurement |
|---|---|---|---|---|
| conversion wall, whole invocation (s) | 1118.867 | 1.197 | 3 | `cargo-sensorium convert <spool>` over the SAME spool directory the acceptance run recorded and had already co… |
| wall, plain median (s) | 0.059 | 0.058 | 5 | wall clock of `cargo test -p bloomery-daemon --lib` (P) versus `cargo sensorium test -p bloomery-daemon --lib`… |
| wall, call median (s) | 1.666 | 0.125 | 5 | wall clock of `cargo test -p bloomery-daemon --lib` (P) versus `cargo sensorium test -p bloomery-daemon --lib`… |
| wall ratio call/plain | 28.2373 | 2.1552 | 5 | median(call)/median(plain); wall clock of `cargo test -p bloomery-daemon --lib` (P) versus `cargo sensorium te… |
| conversion wall, one `--lib` trace (s) | not measured (no 46074ef counterpart: this row is new to the addendum) | 0.014 | 3 | `cargo-sensorium convert` over the spool of ONE recorded `--lib` invocation (1390 events, 1 process), a second… |
| one recorded `--lib` invocation wall (s) | not measured (no 46074ef counterpart: this row is new to the addendum; the nearest 46074ef figure is E3's mean over 20 recorded runs (12.38 s), a different estimand) | 0.102 | 1 | one `cargo sensorium test -p bloomery-daemon --lib`, build Fresh, conversion included, whose spool the row abo… |
| driver fixed cost (s) | 0.021 | 0.073 | 5 | median of 5 no-op `--tier off --no-run` invocations through the driver minus the median of 5 straight to cargo… |
| driver no-op invocation wall (s) | not measured (no 46074ef counterpart: this row is new to the addendum) | 0.125 | 5 | the absolute wall of one no-op `--tier off --no-run` invocation, median of 5, nothing to subtract; the SAME ac… |
| runtime rlib build (s) | 0.153 | 0.138 | 1 | one `--no-run` with `<target>/sensorium/rt` removed (1312068 bytes), minus the warm no-op median above; n=1, a… |

| Round | P (plain) | C (call) | load at P | load at C |
|---|---|---|---|---|
| 1 | 0.058 s | 0.126 s | 1.05 | 0.96 |
| 2 | 0.07 s | 0.115 s | 0.77 | 0.81 |
| 3 | 0.057 s | 0.125 s | 0.65 | 0.55 |
| 4 | 0.07 s | 0.112 s | 0.47 | 0.46 |
| 5 | 0.058 s | 0.125 s | 0.54 | 0.46 |
| **median** | 0.058 s | 0.125 s | — | — |
| **min** | 0.057 s | 0.112 s | — | — |
| **max** | 0.07 s | 0.126 s | — | — |


## 4. Decisions

Written by hand, not by the runner. Every row quotes the pre-registered rule from §1
verbatim and the measured number from §3.

| Id | Pre-registered rule (§1, verbatim) | Measured | Verdict |
|---|---|---|---|
| E2′ | "floor 98% of eligible fn items; **any fell-back unit is a finding that stops the rung until explained**" | **100.0%** — 2051 instrumented of 2051 eligible, numerator and denominator over the same file set; **0** units fell back, **0** `fell back to the real tree` lines, **0** unreached files | **PASS** |
| E3 | "**DIVERGED 0/19 and REFUSED 0/19**; any DIVERGED or REFUSED = the comparator or the recorder is wrong — STOP and diagnose before any other endpoint" | **0 DIVERGED, 0 REFUSED** over 19 diffs; 19 MATCH, CLI exit 0 each; the binary's sha256 was equal before all 20 runs | **PASS** |
| E5 | "**A/B = `MATCH modulo location` with ≥ 1 moved, 0 added, 0 removed, every `task::registry::tests::*` task paired by name; A/C = `DIVERGED` naming a step inside the swapped fn.** A/C reading MATCH → the verifier is void, STOP; A/B reading DIVERGED → report the step, and if it is a test-order change (a test moved between discovery units) read it as the instrument working (spec §10 amended 2026-09-02), else STOP" | **A/C = DIVERGED**, naming `Journal::open` (A) against `ImageStore::new` (B) at causal step 4 inside the swapped fn — the half that had to hold, holds. **A/B = DIVERGED**, with 28 moved, 0 added, 0 removed, and the six `task::registry::tests::<test>` tasks paired — but **four spawned child tasks unpaired**, and the divergence is **not** a test-order change | **STOP** |
| E7 | "any difference in a `panicked at <file>:<line>:<col>`, a `file!()`/`line!()` value, a backtrace frame's `<file>:<line>`, or in (b) any difference in a `test … ok/FAILED` line or the `test result:` line → STOP" | **0 differences**: (a) 6 of 6 E7 checks pass on the probe (44 of 44 `mechanics.sh` checks pass, 0 fail); (b) 0 differences over 56 masked lines on the clone, identical `test result:` lines, and the instrumented arm wrote 60 spool files so the comparison is not vacuous | **PASS** |
| E8 | "any failed check → STOP" | **0 failed checks of 5**: (a), (c)+sentinel, (d) and (b), all on the clone, with the expected `Fresh` set asserted each time | **PASS** |

**One endpoint reads STOP, so the rung's PR ends at a findings document.** That is the
pre-registered consequence, taken as written. Nothing below softens it, and no product
code was changed in this task.

### E2′ — 100.0%, with the estimand fixed before the number was read

Two facts make this row readable, and both are measured:

1. Over every file it compiled, the workspace-wide instrumented `--no-run` instrumented
   **2051 of 2051** eligible fn items. **0** manifests carry `fell_back`, **0** build
   logs contain a `fell back to the real tree` line — the two channels a fallback has
   to appear in, both empty — **0** files were unreachable by a module walk, and the
   only items skipped were skipped by rule (10 records, all `const`: bloomery's 5
   `const fn` seen once in each of the two feature-sets the daemon's lib is compiled at).
2. The **package** build (`-p bloomery-daemon`) instrumented **1723 of 1723** over the
   files *it* reaches. The two readings are the same shape rung 1 reported, and both
   are diagonal: numerator and denominator over the same files. `0` files of the package
   build's numerator lie outside its denominator's directories — asserted, not assumed,
   because rung 1's findings §5.14 is exactly the failure of crossing those scopes.

**The scoping, stated so it can be checked.** Every manifest-derived count is scoped to
its own build's unit set — the `-C metadata=` values in that build's `cargo -v` log —
and that set is complete only when cargo compiles every unit, because cargo does not
invoke the wrapper for a fingerprint-fresh one. The runner therefore emptied the whole
target directory before the measured workspace-wide build (9 480 938 772 bytes, at
`16:12:37`), not merely the manifests directory: clearing manifests over a warm target
would have *lost* every unit the E8 sequence had already compiled, and the numerator
would have been missing exactly the units measured hardest. **0** manifests outside the
measured build's unit set entered either count. The package reading comes from E8's own
from-scratch instrumented build, read before E8(b) touched a file.

**The per-unit assertion, and what it counted.** Every one of the 108 manifests was
followed to its unit's mirror: **108 checked, 0 naming another unit's metadata**. The
count is reported because a check that examined nothing proves nothing. 106 distinct
`(crate_name, crate_type)` pairs declare those 108 manifests — two pairs declare two
manifests each (`bloomery_daemon`/`test` and `bloomery_bench`/`test`), which is why the
raw spawn-site sum is 13 against the census's 8 distinct literal
`std::thread::spawn(` sites (§5.8). *Why* those two pairs each produced two manifests
is not something this run's evidence says, and nothing here asserts it.

### E3 — 0 DIVERGED, 0 REFUSED, over a binary that provably never moved

Twenty recorded runs of one `--lib` binary built once; its sha256
(`143a4a4dc65ba31e…`) was re-read and compared before every single run, and moved
**0** times. Every run recorded **1390** events. All 19 diffs against run 1 read
MATCH with CLI exit 0. This is the endpoint that would have condemned the comparator
or the recorder, and it is clean.

### E5 — the negative control works; the positive control does not, and the reason is exact

**The split, item by item** (branch `e5-split` on the clone; the patch is in the ledger
as `e5-split.patch`). `crates/bloomery-daemon/src/task/registry.rs` (1395 lines) became a
directory module of three files. Every item block below moved **byte-identically**;
`*` marks the ten that gained a `pub(super)` prefix so a sibling or the parent could
still reach them, and nothing else in any item changed.

| Destination | Items moved there |
|---|---|
| `registry/mod.rs` | the module docs (lines 1–101, verbatim), `type Entries`, `struct OrganDecision` + `impl OrganDecision`, `struct OrganOutcome<'a>`, `pub struct TaskRegistry`, `impl Default for TaskRegistry`, `impl TaskRegistry` (`new`, `spawn_task`, `get`), and `#[cfg(test)] mod tests` — which is why every test keeps the path `task::registry::tests::*` and libtest's name ordering is unchanged |
| `registry/helpers.rs` | `panic_message`, `panic_payload_message` (both already `pub(crate)`, re-exported from `mod.rs` so `crate::task::registry::panic_message` still resolves for `codec_probe` and `api_native`), `lock_entries`*, `without_evidence`*, `lock_store`*, `record`*, `degrade`*, `panic_note`, `contained`*, `now_millis`* |
| `registry/organ.rs` | `classify_probe`*, `organ_before_run`*, `organ_after_run`*, `is_scored_outcome` |

The 13 `use` declarations were re-derived per file rather than moved (a directory module
cannot share one import block); the tree compiles warning-free and all 53 `--lib` tests,
including the six `task::registry::tests::*`, pass on both branches. **Evidence, run
2026-09-03 after the acceptance run and archived rather than asserted** (the acceptance
run's own E5 arms filter to `task::registry`, so its logs read `6 passed … 47 filtered
out` and could not support this sentence): `cargo test -p bloomery-daemon --lib` on
`e5-split` @ `e8c79be1626f` and on `e5-planted` @ `fea50b14ba45`, exit 0 each, each
`test result: ok. 53 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out`, each with
the six `task::registry::tests::*` among them and **0** `warning` lines, each preceded by
a real `Compiling bloomery-daemon` line rather than a no-op. Full logs in the ledger as
`acceptance/logs/e5-B-lib-tests.log` and `acceptance/logs/e5-C-lib-tests.log`. The clone
was returned to `e209ed9` with `git status --porcelain` empty afterwards. This is a
property of the two branches, not of any gated arm: no E5 number was re-measured.

Branch `e5-planted` adds exactly one change on top: the two consecutive independent
call statements
`let journal = Journal::open(&dir.join("pager.jsonl")).unwrap();` and
`let images = ImageStore::new(&dir.join("img")).unwrap();` in `tests::build_pager` are
swapped (`e5-planted.patch`, 1 insertion, 1 deletion).

**A/C is the half that could have voided the verifier, and it holds.** With one pair of
consecutive independent call statements swapped, `diff --ignore-moves` read DIVERGED and
named the step: `A: e65 CALL Journal::open` against `B: e38 CALL ImageStore::new`, at
causal step 4, inside the swapped fn, after three common steps. The drill-down by task
prints the same divergence with the three common steps above it. A behaviour-preserving
split does not hide a reordering.

**A/B is the half that fails, and it fails on task NAMES, not on causal streams.** The
pairing itself is right: 28 code objects paired across the move by qualname, **0 added,
0 removed, 0 unpaired**, and all six `task::registry::tests::<test>` tasks matched by
content. What did not match are four *spawned child* tasks, whose names embed the spawn
site's file and line:

```
only in A: … a_panicking_worker… :: spawn@crates/bloomery-daemon/src/task/registry.rs:769      04afbcbcacf6
only in B: … a_panicking_worker… :: spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248  04afbcbcacf6
```

The stream hashes are **identical, pairwise**, across all four (`04afbcbcacf6`,
`5976ef054dbe`, `5976ef054dbe`, `63737389821f` on both sides). The two runs did the same
work; only the *name* of the task moved, because `spawn_task` moved from
`registry.rs:769` to `registry/mod.rs:248` and the child's name is built from that
location. `--ignore-moves` pairs code objects by qualname; it does not project task
names, so a pure file move renames a task and the multiset comparison reports DIVERGED.

The rule's own escape hatch does not apply: the divergence is **not** a test-order
change (no test moved between discovery units; libtest ran the same six tests in the
same order on both sides, and all six paired). The rule then says, verbatim, "else
STOP". **STOP.**

What this costs, stated plainly: `diff --ignore-moves` verifies a source-file split for
every function it traced, and reports a divergence anyway as soon as the split moves a
`spawn` site — which a split of a file containing one is guaranteed to do. That is the
use case the endpoint exists for.

### E7 — 0 differences, with one half of (b) declared vacuous

(a) On the probe workspace, all six E7 checks pass — panic locations, `file!()`/`line!()`
values and every backtrace frame's `<file>:<line>` byte-identical between plain and both
instrumented tiers, with durations and rustc's `(<tid>)` masked and nothing else — inside
a script whose 44 checks all passed. The driver's sha256 was unchanged across the script,
so the thing measured is the thing pinned in §2.

(b) On the clone, `cargo test -p bloomery-daemon --lib -- --test-threads=1` produced
**0** differences over 56 masked lines, and the `test result:` lines are identical
(`ok. 53 passed; 0 failed; …`). The instrumented arm wrote **60** spool files during that
same comparison, so it was not a tool that did nothing.

**The vacuous half, named.** (b) found **0** `panicked at` locations on either side —
libtest captures a passing test's output, and every test in this suite passes, so the
panic-location half of (b) compared nothing. The (a) arm carries that half, on a suite
built to panic on purpose. This is a limit of (b) as pre-registered, not a failure, and
it is §5.7.

### E8 — 0 failed checks, on a real workspace, with (b) for the first time

(a) a second instrumented `--no-run` compiled nothing and found exactly
`['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` Fresh; (c) a plain
`--no-run` after it did the same; (d) an instrumented one after that did the same again.
The expected `Fresh` set is asserted, not merely "compiled nothing", because a build that
dies before its first `Compiling` line also compiles nothing.

The sentinel is what makes (c) mean something: run with `SENSORIUM_SPOOL` set and
`SENSORIUM_TIER=call`, the **plain** `--lib` binary wrote **0** spool files and the
instrumented one wrote **58**. A plain build cannot be contaminated into recording.

(b) ran on bloomery for the first time (rung 1 could only run it on the probe): appending
one comment line to `crates/bloomery-core/src/lib.rs` recompiled exactly
`['bloomery-core', 'bloomery-daemon']` and left `['bloomery-substrate']` Fresh — the
derived expectation, since `bloomery-substrate` does not depend on `bloomery-core`. The
file was restored byte-for-byte and the clone's porcelain is empty.

### What these numbers do not license

Four endpoints pass on mechanics: the transformer reaches the code, the comparator does
not lie about a repeated run, the output survives, the build survives. **None of them
says the recorded trace answers a debugging question about Rust**, and the one endpoint
that asked whether a trace can *verify a refactor* reads STOP. The conversion cost
(§5.2) is not gated by anything in §1 and is, on this evidence, the largest practical
obstacle to using the recorder at invocation scale.

## 5. Gaps found

Everything this run surfaced that rung 3 must decide, close, or knowingly carry. Each
entry says what was MEASURED, not what is suspected.

1. **A task's identity is a name that embeds its spawn site, so a file move renames it
   — and `--ignore-moves` does not project task names.** *Measured: E5's A/B read
   DIVERGED with 28 code objects paired, 0 added, 0 removed, all six test tasks matched,
   and four spawned child tasks unmatched whose stream hashes are pairwise identical
   across the two sides* (`04afbcbcacf6`, `5976ef054dbe` ×2, `63737389821f`). The child
   task's name is `…::<test> :: spawn@<file>:<line>`, and the split moved that site from
   `registry.rs:769` to `registry/mod.rs:248`. This is the rung's STOP. The fix is a
   decision, not a patch: either project task names through `moves` the way code-object
   keys are projected, or name a spawned task by something a move does not change, or
   declare in the verdict that unpaired-by-name tasks whose projected streams hash equal
   are a move and not a divergence.
2. **Conversion of one whole invocation costs 1118.9 s (18.6 min) against rung 1's
   22.7 s — about 49× — for the same workspace and a comparable event count** (119
   processes, 134 394 events, 32.2 MB of traces, 13.8 MB of spool). *Measured as a
   second, warm-cache pass over the same spool the invocation had just converted
   in-process; the in-process conversion inside the invocation cost the same order (the
   invocation's own wall was 1088.6 s with a 2.8 s pre-build).* **Diagnosis, from the
   code and the observed I/O rather than from a second measurement:**
   `convert/sqlite.rs` sets `journal_mode=WAL` but wraps no inserts in an explicit
   transaction and leaves `synchronous` at its default, so every row is its own
   committed transaction — one fsync each. **OBSERVED, not measured** — read live from
   `/proc` and `iostat` while the run was in `D` state, with no artifact in the ledger
   to check them against, unlike every other number in this section: the process
   showed `wchan: jbd2_log_wait_commit`, `/proc/<pid>/io` reported 2.59 GB written for
   32 MB of traces, and the artifact device sat at 98.8% utilisation. Rung 3 should
   wrap each trace in one transaction (and consider `synchronous=NORMAL`, which WAL
   makes safe against process crashes) before any conversion number is quoted again.
   **Fixed in `bcc9c9f` (2026-09-03), reviewed clean at `da186e8`: one transaction
   per trace under WAL with `synchronous=NORMAL`. Re-measured in §3.1 — the same
   spool, converted again by the same command, now reads 1.197 s (n=3) against the
   1118.9 s above: about 935× — and the `--lib` call/plain ratio of §5.3 falls from
   ×28.24 to ×2.16.** The paragraph above is left as it was measured; this sentence
   is the amendment, not a replacement.
3. **The `--lib` call/plain wall ratio is ×28.24 and is dominated by conversion, not by
   recording.** *Measured: median plain 0.059 s against median call 1.666 s, n=5 per
   arm, 0 dropped, 1-minute load **0.51–2.17** at the arm starts (every arm under the
   4.0 refusal threshold, so nothing was dropped and nothing may be).* The two
   highest-load arms are round 1 — P at 2.17 and C at **1.84** — and round 1's call arm
   is the run's outlier at **3.939 s**, more than twice each of the other four call arms
   (1.661, 1.689, 1.664, 1.666). The medians and the ratio are taken over all five and
   are unaffected; the outlier is named here rather than smoothed away, and its load
   context is what a reader needs to question it.

   The plain arm runs 53 tests in 0.09 s; the call arm runs the same tests and then
   converts 1390 events in the same process. **This is not comparable to rung 1's
   ×1.0103**, which timed `cargo test -p bloomery-daemon` (a 8.25 s suite) and
   converted separately. Whatever
   §5.2 costs, this ratio carries it; a comparable rung-1-style number needs the
   conversion split out of the timed command.
   **Re-measured after §5.2's fix (2026-09-03, §3.1): ×2.1552 — plain 0.058 s,
   call 0.125 s, n=5 each — and the conversion of that same `--lib` trace, timed
   alone, is 0.014 s (n=3). This reading confirms the claim above rather than
   replacing it: the ratio WAS conversion-dominated, and what is left of the gap
   after conversion is mostly the driver's own fixed cost (0.073 s, §3.1). The
   lens caveat stands: rung 1's ×1.0103 timed a different command with the
   conversion outside it, and the two are still not equals.**
4. **48 of 119 processes carry `exit_status_basis = "unwitnessed"`.** *Measured: the
   histogram is `waited × 71, unwitnessed × 48`, one row per trace.* The 71 test
   binaries cargo runs go
   through the target runner, which waits for them and records the status nothing inside
   the process can see; the 48 `flywheel-tool` children they spawn do not, so their
   status is declared unwitnessed rather than borrowed. Rung 1's gap 1 ("`exit_status`
   is borrowed from cargo for every process") is closed for the binaries and open for
   the children.
5. **100 threads were still alive at process exit, and 0 of 1250 spool files has a torn
   last record.** *Measured by parsing the spool bytes directly, outside the converter
   that wrote them: 100 spool files carry no `THREAD_END`, and every one of them ends on
   a complete record.* Rung 1's gap 2 — a live thread's buffered tail is lost — is closed
   on the record side by the `MAP_SHARED` spool. What is **not** measured here is whether
   any event that thread would have emitted after the last flush is missing; the trace
   still reports `incomplete = false` for a process whose threads did not finish, which
   remains the distinction a reader will misread.
6. **5729 captured return values were truncated at the repr cap.** *Measured:
   `truncated_count` summed over the invocation's 119 traces.* The traces under-report
   those values by an unmeasured amount; the count is what says so. `seq_gaps` and
   `records_dropped` are both **0**, and `panics_unrecorded` is **0**, so nothing else
   was lost.
7. **E7(b)'s panic half was vacuous.** *Measured: 0 `panicked at` locations on either
   side.* libtest captures a passing test's output and every test in the daemon's `--lib`
   suite passes, so (b) compared the test lines and the result line — which is what its
   rule names — and compared no panic location at all. Rung 3 should either run (b) with
   `--nocapture` or state that the panic half lives only in (a).
8. **`spawn_sites_rewritten` = 13 is a raw sum across manifests, not a distinct count.**
   *Measured: 13 across the 108 manifests, against the census's 8 distinct literal
   `std::thread::spawn(` sites over the same tree.* Two `(crate_name, crate_type)` pairs
   declare two manifests each (`bloomery_daemon`/`test`, `bloomery_bench`/`test`), so
   the sites in the files they share are summed twice. The manifests carry
   no distinct spawn-site identity today; the census is the only instrument that reports
   one.
9. **The E5 plant could not be placed in production code.** *Measured: the registry's
   production fns that run under `-- task::registry` contain four pairs of consecutive
   statements (`spawn_task` lines 759/760, 763/764, 767/768, 922/923) and every one is
   either data-dependent or calls only uninstrumented std functions* — so no pair of
   consecutive **independent** call statements exists there whose swap the trace could
   see. The swap therefore went in `tests::build_pager`, a non-`#[test]` helper fn of the
   registry (`Journal::open` and `ImageStore::new`), which satisfies the
   pre-registration's words and is a negative control on the *instrument*, not on
   production code.
10. **The split needed 10 visibility prefixes and re-derived `use` lines.** *Measured:
    every item block moved byte-identically (a mechanical check compared each block
    against `git show e209ed9:…registry.rs`); the only non-verbatim changes are ten
    `pub(super)` prefixes on items a sibling or the parent now reaches, and the 13 `use`
    lines, which were distributed per file rather than moved.* No fn body was edited. A
    reader checking "verbatim" should read it as "no body, and no signature except its
    visibility".
11. **The two E2′ readings come from two different from-scratch builds.** *Measured: the
    package numerator from E8's instrumented build (77 units, target emptied at
    16:12:15), the workspace numerator from a second build after the target was emptied
    again (154 metadata units in the log, 108 manifests, at 16:12:37).* Both are
    self-consistent and diagonal; neither is a subset reading of the other's manifests.
12. **The acceptance leaves 10.33 GB in the target directory and 78.1 MB of traces**, and
    the artifact disk went from 115.12 GB to 105.16 GB free. The traces are evidence and
    are kept; the target is not.
