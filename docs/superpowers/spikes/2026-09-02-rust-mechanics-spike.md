# Rust mechanics spike — findings (throwaway code, pre-registered)

Plan: `docs/superpowers/plans/2026-09-02-sensorium-rung1-mechanics-spike.md`
Spec: `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md`

## 1. Pre-registration

Lens for every endpoint: dev profile, `cargo test -p bloomery-daemon` as bloomery runs it (default `--test-threads`), this box (AMD Ryzen 7 9800X3D, 16 threads, `powersave` governor), `sensorium-rt` built at `opt-level = 3` regardless of profile, tier `call` = CALL/RETURN per instrumented fn item, no `?` sites, no locals, no output capture.

| Id | Question | Measurement | Decision rule | Derivation of the threshold |
|---|---|---|---|---|
| E0 | Is one test binary a usable trace unit? | Convert the spools of `--lib` (64 tests) and `--test config_test` (26 tests, the largest integration binary) and of every binary in one `cargo test -p bloomery-daemon` invocation; report events, trace bytes, `sensorium info` wall and `sensorium diff` wall (identical pair: two tier-call runs of the same binary) | STOP and re-plan the trace unit if `info` or `diff` exceeds 60 s on `--lib` or on `config_test` | 60 s is CHOSEN (the interactive debugging loop); sanity: after rung 0 the reader costs ≈1 µs/event (0.09 s at 93k), so 60 s ≈ 6×10⁷ events in one binary — the report shows how much slack that leaves |
| E1 | Does compile-once-gate-at-runtime survive? | Wall clock of `cargo test -p bloomery-daemon` (binaries pre-built per arm with `--no-run`), three arms: plain (no wrapper), off (instrumented, `SENSORIUM_TIER=off`), call (instrumented, tier call); 5 interleaved rounds P,O,C; report median, min, max per arm and the ratio of medians; plus a micro-bench `fib(30)` plain/off/call for ns per call, and clean `--no-run` wall and binary size per arm (reported, not gated) | median(off)/median(plain) > 1.5 → tiering becomes a cargo feature and `refocus` a rebuild | 1.5× is Brice's ruling (spec §12.4); sanity: the design review measured off at ×1.02 on ordinary code and ×3.4–4.9 on call-dense `fib(30)`, so a breach means the per-call branch is visible at test-suite granularity |
| E2 | Does the transformer cover bloomery? | From the manifests: fn items instrumented ÷ fn items eligible (eligible = every `fn` item in workspace source except `const fn` and `extern` fns, counted by a syn census over the same files); units that fell back to the real tree | floor 98% of eligible fn items; any fell-back unit is a finding that stops rung 2 until explained | spec §8 E2; 5 `const fn` of 756 items are excluded by rule (99.3%), leaving margin for closures-as-items the census may count differently |
| E7 | Are line numbers and paths preserved? | On the probe workspace: a test that panics with a known message, a test whose assert message embeds `file!()`/`line!()`, and `RUST_BACKTRACE=1` on the panic; run plain and instrumented (off and call), `--test-threads=1 -- --nocapture`; diff the outputs with durations masked | any difference in a `panicked at <file>:<line>:<col>` location, a `file!()`/`line!()` value, or a backtrace frame's `<file>:<line>` stops rung 2 | spec §3.1 and §7: byte-offset splicing plus the mirror with argv unchanged predict zero differences; a single difference falsifies the mechanism |
| E8 | Does cargo freshness survive, and can a plain build be contaminated? | On the probe workspace AND on bloomery: (a) instrumented `--no-run` twice → the second compiles no workspace unit; (b) touch one source line → exactly that unit and its dependents recompile; (c) plain `--no-run` after an instrumented build → no workspace unit compiles AND the plain binary run with `SENSORIUM_SPOOL` set writes no spool; (d) instrumented `--no-run` after (c) → no workspace unit compiles (both artifact sets coexist) | any failed check stops rung 2 | spec §2.1: `RUSTC_WORKSPACE_WRAPPER` is hashed into `-C metadata`, so the sets coexist; spec §2.2: dep-info stays workspace-relative, so freshness holds; the review verified both on a probe, never on bloomery |

Reported without a gate: events per second of recording (from E0 and the E1 call arm), bytes per event on disk, number of test binaries cargo ran, libtest thread naming as observed, per-process exit-status availability (expected: NOT available to the runtime — recorded as a rung-2 gap), and the wall time of the spike's own build.

Decisions this spike settles, written into the findings and the spec: (1) compile-once versus cargo feature (E1); (2) the trace unit (E0); (3) go / no-go for rung 2 on mechanics (E7, E8, E2). A NO on (3) means the mirror or wrapper design is reworked before rung 2, not patched during it.

`results.json` schema (none-versus-zero): every measurement is `{"value": <number|null>, "n": <int>, "lens": <string>, "dropped": [<reason>...]}`; a `null` value with a non-empty `dropped` list is the only representation of "not measured"; `0` is measured-and-zero. The renderer refuses to print a table row whose `value` is `null` as anything but `not measured (<reason>)`.

## 2. Ambient pins (preflight, recorded 2026-09-02 before any code exists)

| Item | Command | Value |
|---|---|---|
| rustc | `rustc -V` | `rustc 1.96.0 (ac68faa20 2026-05-25)` |
| cargo | `cargo -V` | `cargo 1.96.0 (30a34c682 2026-05-25)` |
| toolchains | `rustup toolchain list` | `stable-x86_64-unknown-linux-gnu (active, default)` — stable only, no nightly installed |
| bloomery commit | `git -C /home/brice/workspace/bloomery rev-parse HEAD` | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| bloomery branch | `git -C /home/brice/workspace/bloomery branch --show-current` | `split-python-trio` |
| bloomery status | `git -C /home/brice/workspace/bloomery status --porcelain` | empty (clean) — re-checked after the timed build below, still empty |
| nproc | `nproc` | `16` |
| governor | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | `powersave` |
| RUSTFLAGS | `echo "RUSTFLAGS=[$RUSTFLAGS]"` | `RUSTFLAGS=[]` (unset) |
| CARGO_INCREMENTAL | `echo "CARGO_INCREMENTAL=[$CARGO_INCREMENTAL]"` | `CARGO_INCREMENTAL=[]` (unset) |
| RUSTC_WRAPPER | `echo "RUSTC_WRAPPER=[$RUSTC_WRAPPER]"` | `RUSTC_WRAPPER=[]` (unset) |
| free disk | `df -h /` (same filesystem as `bloomery/target`, confirmed with `df -h /home/brice/workspace/bloomery/target`) | `9.9G` available on `/dev/nvme0n1p2` (99% used, 915G total) — floor is 8 GB, this passes with 1.9 GB to spare |
| 1-minute load | `cat /proc/loadavg` (checked immediately before the timed build) | `0.42 0.33 0.36 1/2282 2377667` — 1-minute load 0.33, well under the 4.0 refusal threshold |
| baseline build wall | `cd /home/brice/workspace/bloomery && /usr/bin/time -f "%e" cargo test -p bloomery-daemon --no-run` | **4.76 s** |
| uv | `uv --version` | `uv 0.11.18 (x86_64-unknown-linux-gnu)` |
| `.venv` python | `.venv/bin/python -V` (sensorium repo) | `Python 3.14.4` |
| sensorium version | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.5.0` |

**Lens for the baseline build wall:** this is a genuinely clean build of the `bloomery-daemon` crate — Brice ran `cargo clean -p bloomery-daemon` immediately before this task to free disk, so no `bloomery-daemon` artifact existed; `core`/`substrate` and all third-party dependency crates were already built and warm in `target/debug/deps` and were reused unchanged. The number is therefore "compile `bloomery-daemon`'s lib plus link its ~70 test binaries against already-built deps," not "compile the whole workspace from nothing." Confirmed genuine (not a `Fresh`, no-op run): the `.fingerprint/bloomery-daemon-*` entries and `target/debug/deps/libbloomery_daemon-*.rlib`/`.rmeta` carry mtimes inside the same few seconds as the command's execution window. 4.76 s is faster than the plan's "expect a few minutes" framing predicted for this box under this lens (fast NVMe, warm page cache, all deps prebuilt, 16 threads available for the test-binary linking fan-out) — recorded as observed, not adjusted.

## 3. Results

Every cell is `not measured (spike not yet run)` — no crate under `rust/spike/` exists yet; this document is committed before Task 1.

| Id | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E0 | not measured (spike not yet run) | — | — | spike not yet run |
| E1 | not measured (spike not yet run) | — | — | spike not yet run |
| E2 | not measured (spike not yet run) | — | — | spike not yet run |
| E7 | not measured (spike not yet run) | — | — | spike not yet run |
| E8 | not measured (spike not yet run) | — | — | spike not yet run |

## 4. Decisions

| # | Decision | Verdict |
|---|---|---|
| 1 | Compile-once-gate-at-runtime versus a cargo feature (E1) | pending |
| 2 | The trace unit (E0) | pending |
| 3 | Go / no-go for rung 2 on mechanics (E7, E8, E2) | pending |

## 5. Rung-2 gaps found

(empty — populated by Task 5 against the measured evidence)
