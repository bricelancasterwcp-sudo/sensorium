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

## 3. Results

Not yet measured — Task 0 only pre-registers, clones, and pins the environment; no recorder code exists yet. Every cell below is `not measured (rung 2 pending)`.

| Id | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E2′ | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E3 | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E5 | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E7 | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) |
| E8 | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) | not measured (rung 2 pending) |

## 4. Decisions

(empty — written by hand after the run, quoting each pre-registered rule)

## 5. Gaps found

(empty)
