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

Measured 2026-09-02 on the box §2 pins, bloomery @ `e209ed9` (`split-python-trio`), rustc 1.96.0 (ac68faa20 2026-05-25). Runner: `rust/spike/measure.py` (raw logs and `results-raw.json` in the gitignored ledger). Every cell below is a number with its `n` and its lens, or `not measured (<reason>)`.

| Id | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| E0 | 0.03 s (worst of 4 medians; rule: > 60 s) | 3 | the LARGEST of the four medians (info and diff on --lib and on --test config_test); the rule is `> 60 s on --… | none |
| E1 | ×0.9975 (rule: > 1.5 → cargo feature) | 5 | median(off)/median(plain); wall clock of the whole command, dev profile, `cargo test -p bloomery-daemon` (P) … | none |
| E2 | 100.0% (floor 98%) | 2051 | instrumented distinct (file, qualname, firstlineno) / 2051 eligible; denominator = crates/*/src + crates/*/te… | none |
| E7 | 0 differences (rule: any → stop) | 4 | differences in `panicked at <file>:<line>:<col>`, in a `file!()`/`line!()` value, or in a backtrace frame's <… | none |
| E8 | 0 failed checks (rule: any → stop) | 4 | failed checks of E8(a), (c)+sentinel, (d); on BLOOMERY, `-p bloomery-daemon`, counting Compiling/Fresh of the… | none |

### E0 — one test binary as a trace unit

| Binary | events (run 1 / run 2) | trace bytes | threads | `info` wall | `diff` wall | spools without END |
|---|---|---|---|---|---|---|
| `lib` | 1388 / 1388 | 258048 / 258048 | 58 / 58 | 0.03 s | 0.03 s | 0 / 0 |
| `config_test` | 1226 / 1226 | 200704 / 204800 | 27 / 27 | 0.03 s | 0.03 s | 0 / 0 |

One whole `cargo test -p bloomery-daemon` call-arm invocation converted: **119 processes** (71 test binaries plus 48 spawned `flywheel-tool` children; bloomery-daemon has no doctests, so no rustdoc process appears — the doctest route is covered on the probe workspace by `mechanics.sh`), **132344 events**, **22196224 trace bytes** over 3299924 spool bytes (24.93 B/event on disk), conversion wall 22.7 s, **100 spools without `THREAD_END`** (3 processes: 64 of 81 threads in `api_v1_honesty_test`, 32 of 62 in `api_v1_test`, 4 of 71 in `api_native_test` — server threads alive at process exit, whose buffered tail is lost; §5).

`diff` verdict, verbatim (both pairs read the same way):

```
A 20260902-154453-fffd9c: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260902-154454-f2cbd5: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
note: A recorded more than one thread: 57 started through Python's own threading/_thread, 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 57 started through Python's own threading/_thread, 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: MATCH -- no causal event ran outside a task on either side, so the thread streams held nothing to compare; the tasks below carry the whole verdict
tasks: 57 task stream(s) on each side, compared by content as (name, hash): all matched; the ordering between tasks is not compared
```

### E1 — compile-once, gate at runtime

| Round | P (plain) | O (off) | C (call) |
|---|---|---|---|
| 1 | 8.268 s | 8.184 s | 8.434 s |
| 2 | 8.252 s | 8.206 s | 8.337 s |
| 3 | 8.207 s | 8.320 s | 8.335 s |
| 4 | 8.270 s | 8.231 s | 8.306 s |
| 5 | 8.208 s | 8.269 s | 8.493 s |
| **median** | 8.252 s | 8.231 s | 8.337 s |
| **min** | 8.207 s | 8.184 s | 8.306 s |
| **max** | 8.270 s | 8.320 s | 8.493 s |

median(off)/median(plain) = **×0.9975**; median(call)/median(plain) = ×1.0103. The instrumented walls include the driver's own fixed cost, measured separately at **0.025 s** (release driver; a debug one costs ≈0.5 s).

Micro-bench `fib(30)`, ns per call, best of 3, each arm its own process — TWO lenses, and E1's pre-registered lens is the first:

| Lens | plain | off | call | off/plain | call/plain |
|---|---|---|---|---|---|
| `caller=dev(opt0) rt=opt3` | 1.0595 | 6.2875 | 65.8710 | ×5.934 | ×62.172 |
| `caller=release(opt3) rt=opt3` | 0.5133 | 1.0499 | 61.4413 | ×2.045 | ×119.699 |

### E2 — transformer coverage of bloomery

| Quantity | Value | n | Lens |
|---|---|---|---|
| instrumented fn items, `-p bloomery-daemon` build | 1723 | 77 | distinct (file, qualname, firstlineno) over manifests with fell_back false, `cargo test -… |
| …of those, in `crates/*/src` | 679 | 77 | the same, restricted to crates/*/src |
| raw site total across manifests | 7360 | 77 | sum of sites across manifests -- larger than the distinct count because a crate compiled … |
| units that fell back to the real tree | 0 | 77 | manifests with fell_back true, `-p bloomery-daemon` build |
| `fell back to the real tree` stderr lines | 0 | 1 | `fell back to the real tree` lines across every build log of the E8 sequence |
| files a module walk could not reach | 0 | 77 | files a unit's module walk could not reach, unioned over manifests |
| fn items skipped by rule | 10 | 77 | fn items the transformer skipped by rule (const/extern/macro/async) |
| instrumented fn items, workspace-wide instrumented `--no-run` | 2051 | 108 | distinct fn items from a supplementary workspace-wide instrumented `--no-run` (declared a… |

Denominators, all from `sensorium-transform`'s own `census` — the parser that did the instrumenting — over bloomery @ `e209ed9`:

| Denominator | eligible fn items | E2 with the `-p bloomery-daemon` numerator (1723) | E2 with the workspace-wide numerator (2051) |
|---|---|---|---|
| `crates/*/src` + `crates/*/tests` (the plan's file set) | 2051 | 84.0% | 100.0% |
| `crates/*/src` only | 739 | 91.9% | (not comparable: the wide numerator spans both) |
| the files a `-p bloomery-daemon` build reaches | 1723 | 100.0% | (not comparable) |

Census: 2056 `fn` items with a body, 5 `const fn`, 0 `extern` fn, 0 `async` fn → 2051 eligible (739 over 82 files in `crates/*/src`, 1312 over 109 files in `crates/*/tests`). A `cargo test -p bloomery-daemon` build compiles 1723 of those 2051; the other 328 live in `bloomery-bench/src` (60), `bloomery-bench/tests`, `bloomery-core/tests` and `bloomery-substrate/tests` (268) — files that build never sees. See §4 for which reading the decision uses and why.

### E7 — line numbers, paths and backtraces

```
ok: e7_output_identical_plain_vs_off
ok: e7_output_identical_plain_vs_call
    [E7] plain output, durations masked:
      
      running 2 tests
      test assert_message_embeds_file_and_line - should panic ... e7: file!() = probe-app/tests/e7.rs, line!() = 21
      
      thread 'assert_message_embeds_file_and_line' (<tid>) panicked at probe-app/tests/e7.rs:26:5:
      probe assert at probe-app/tests/e7.rs:20
      note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
      ok
      test panics_with_a_known_message - should panic ... e7: about to panic at probe-app/tests/e7.rs:12
      
      thread 'panics_with_a_known_message' (<tid>) panicked at probe-app/tests/e7.rs:13:5:
      known probe panic
      ok
      
      test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in <masked>
      
    [E7] the e7 binary wrote 3 spool files under call
ok: e7_binary_is_actually_instrumented
    [E7] backtrace locations (plain): probe-app/tests/e7.rs:26:5 probe-app/tests/e7.rs:20 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/std/src/panicking.rs:689:5 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/core/src/panicking.rs:80:14 ./tests/e7.rs:26:5 ./tests/e7.rs:19:41 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/core/src/ops/function.rs:250:5 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/core/src/ops/function.rs:250:5 probe-app/tests/e7.rs:12 probe-app/tests/e7.rs:13:5 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/std/src/panicking.rs:689:5 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/core/src/panicking.rs:80:14 ./tests/e7.rs:13:5 ./tests/e7.rs:11:33 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/core/src/ops/function.rs:250:5 /rustc/ac68faa20c58cbccd01ee7208bf3b6e93a7d7f96/library/core/src/ops/function.rs:250:5 
ok: e7_backtrace_locations_identical
```

`rust/spike/tests/mechanics.sh`: 21 checks passed, 0 failed, exit 0.

### E8 — cargo freshness, and contamination of a plain build

| Check | Result | Compiled | Fresh |
|---|---|---|---|
| (a) a second instrumented `--no-run` compiles no workspace unit | PASS | `[]` | `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` |
| (c) a plain `--no-run` after it compiles no workspace unit | PASS | `[]` | `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` |
| (c) sentinel: the plain `--lib` binary writes no spool, the instrumented one does | PASS | plain wrote 0 spool files, instrumented wrote 58 | — |
| (d) an instrumented `--no-run` after the plain one compiles no workspace unit | PASS | `[]` | `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` |
| (b) touch one line → exactly that unit and its dependents recompile | PASS | probe workspace only (bloomery is read-only for this plan) | — |

The expected `Fresh` set is `['bloomery-core', 'bloomery-daemon', 'bloomery-substrate']` — asserted, not merely 'compiled nothing', because a build that dies before its first `Compiling` line also compiles nothing.

Reported, not gated: `--no-run` wall 0.045 s plain (LENS: the plain artifacts pre-existed, so this is a freshness check, not a build) versus 5.48 s for a genuine clean instrumented build of all 77 units; `--lib` test binary 49870320 bytes plain versus 50044080 bytes instrumented (+0.35%).

### Reported without a gate

- Test binaries and processes cargo ran: **119** spooling processes (72 distinct executables).
- Events per second of recording (call arm): 1556988 events per second of ADDED wall, or 15874 per second of suite wall — LENS: the added wall is 0.085 s at n=5 and is inside the arms' own spread, so the first figure is an order of magnitude, not a rate.
- Bytes per event on disk: 24.93 (24 B/record plus one file header per thread).
- libtest thread naming as observed: every spawned test thread carries the test's own name (`codec_probe::fixtures::tests::parses_the_two_brief_examples`, `envelope_lens_names_are_pinned`, …), so the converter's per-task naming needs no heuristic.
- Per-process exit status available to the runtime: **0** (measured-and-zero, not unmeasured) — every trace carries cargo's status instead (§5).
- Wall time of the spike's own build: 4.24 s.

Cleanup: `104559671` bytes of `bloomery/target/sensorium` removed (exists after: `False`); `git -C ~/workspace/bloomery status --porcelain` empty; `Cargo.lock` sha256 unchanged (`c089018581c9bd62…`).

## 4. Decisions

Written by hand, not by the runner. Every row quotes the pre-registered rule from §1 verbatim
and the measured number from §3.

### The five endpoints

| Id | Pre-registered rule (§1, verbatim) | Measured | Verdict |
|---|---|---|---|
| E0 | "STOP and re-plan the trace unit if `info` or `diff` exceeds 60 s on `--lib` or on `config_test`" | **0.03 s**, the largest of the four medians (`info` and `diff`, `--lib` and `config_test`, n=3 each) | **PASS** |
| E1 | "median(off)/median(plain) > 1.5 → tiering becomes a cargo feature and `refocus` a rebuild" | **×0.9975** (n=5 per arm, 0 dropped) | **PASS** |
| E2 | "floor 98% of eligible fn items; any fell-back unit is a finding that stops rung 2 until explained" | **100.0%** (2051 of 2051 eligible); **0** units fell back, **0** unreached files | **PASS** |
| E7 | "any difference in a `panicked at <file>:<line>:<col>` location, a `file!()`/`line!()` value, or a backtrace frame's `<file>:<line>` stops rung 2" | **0 differences** across 4 checks and 2 arms (off, call) | **PASS** |
| E8 | "any failed check stops rung 2" | **0 failed checks**: (a), (c) + sentinel, (d) on bloomery; (b) on the probe workspace | **PASS** |

**E0 — 0.03 s against a 60 s rule.** The rule's own sanity note reads "60 s ≈ 6×10⁷ events in one
binary — the report shows how much slack that leaves". The largest single test binary in the whole
invocation carried **6788 events**; `config_test` carried 1226 and `--lib` 1388. The slack is four
orders of magnitude on events and three on wall clock. `diff` on the identical pair read **MATCH**
with "the tasks below carry the whole verdict" and "26 (resp. 57) task stream(s) on each side …
all matched" — the shape Task 4 predicted, on real bloomery traces.

**E1 — ×0.9975, which is to say: not distinguishable from plain.** The off arm's median (8.231 s)
is *below* the plain arm's (8.252 s); the arms' own min–max spreads (8.207–8.270, 8.184–8.320,
8.306–8.493) overlap. The honest statement is not "the gate costs 0.25% less than nothing" but
"at this suite's call density the per-call branch is invisible, and the measurement cannot
resolve its sign". The call arm costs ×1.0103 — about **85 ms of added wall** over 8.25 s, for
132 344 recorded events. The lens matters and the micro-bench states its limit in the other
direction: on `fib(30)` at E1's pre-registered lens (`caller=dev(opt0) rt=opt3`), off costs
**×5.93** and call **×62.2**. Bloomery's suite records ≈16 000 events per second of suite wall;
`fib(30)` records ≈15 000 000. The reading that survives is *compile-once-gate-at-runtime is free
on code shaped like bloomery's test suite*, not *free*.

**E2 — 100.0%, and the estimand had to be fixed before it could be read.** Two facts, both
measured, are needed to read this row honestly:

1. Over every file it compiled, the transformer instrumented **1723 of 1723** eligible fn items —
   no unit fell back to the real tree (0 manifests flagged, 0 `fell back to the real tree` lines
   in any build log), no module walk failed to reach a file (0 `unreached_files`), and the only
   items it skipped were skipped by rule (10 records, all `const`, which is bloomery's 5 `const fn`
   seen once in each of the two feature-sets `bloomery-daemon`'s lib is compiled at).
2. `cargo test -p bloomery-daemon` — the build §1's lens names — **compiles only 1723 of the
   workspace's 2051 eligible fn items**. The other 328 live in `bloomery-bench/src` (60) and in
   `bloomery-bench/tests`, `bloomery-core/tests` and `bloomery-substrate/tests` (268): files that
   command never sees, in packages it never builds.

So the numerator from the `-p bloomery-daemon` build and the denominator over
`crates/*/src` + `crates/*/tests` are **not the same file set**, and crossing them yields
1723/2051 = **84.0%** — a number about cargo's package selection, not about the transformer. This
was found during preflight (from the census and the package graph), *before* any E2 number was
read, and the fix was declared before the run: a supplementary workspace-wide instrumented
`--no-run` was added at the END of the protocol, so the numerator could be read against the
pre-registered denominator on the same file set. It compiled 108 units, fell back 0 times, and
instrumented **2051 of 2051**. No threshold moved, no timed arm changed, and every reading is in
§3's denominator table so the alternative verdict can be checked:

- numerator and denominator both whole-workspace: **2051/2051 = 100.0% → PASS** ← the decision
- numerator and denominator both `-p bloomery-daemon`-scoped: 1723/1723 = 100.0% (also PASS)
- the mismatched cross-reading: 1723/2051 = 84.0% (would KILL); `crates/*/src` only: 679/739 = 91.9%

Re-render the other way with `SENSORIUM_E2_DENOM=all .venv/bin/python rust/spike/measure.py
--assemble && .venv/bin/python rust/spike/render.py`. **This is the one place a reader should
audit before trusting §4**, and it is flagged again in §5.

**E7 — 0 differences.** Panic locations, `file!()`/`line!()` values and every backtrace frame's
`<file>:<line>` were byte-identical between the plain binary and the instrumented one under both
`off` and `call`, with durations and rustc 1.96's OS thread id masked and nothing else. The check
is not vacuous: the same `e7` binary wrote 3 spool files under `call` in the same script run
(`e7_binary_is_actually_instrumented`), so the identical output came from an instrumented build,
not from a tool that did nothing. **Lens: the probe workspace, not bloomery** — the bloomery tree
is read-only for this plan, and E7 needs a test that panics on purpose.

**E8 — 0 failed checks, on bloomery.** A second instrumented `--no-run` compiled nothing and found
`bloomery-core`, `bloomery-daemon`, `bloomery-substrate` Fresh; a plain `--no-run` after it did the
same; an instrumented one after that did the same again. Both artifact sets coexist under different
`-C metadata` (`bloomery_daemon-3682b2428060a42c` plain, `bloomery_daemon-1c4c106b05035b8f`
instrumented). The sentinel is what makes (c) mean something: the **plain** `--lib` binary, run with
`SENSORIUM_SPOOL` set and `SENSORIUM_TIER=call`, wrote **0** spool files, while the instrumented one
wrote **58** — a plain build cannot be contaminated into recording. Check (b) is probe-only and says
so in §3's table.

### The three decisions this spike settles

| # | Decision | Verdict |
|---|---|---|
| 1 | Compile-once-gate-at-runtime versus a cargo feature (E1) | **Compile once, gate at runtime.** ×0.9975 against a ×1.5 rule. Tiering does not become a cargo feature and `refocus` does not become a rebuild. |
| 2 | The trace unit (E0) | **One test binary — one process — is the trace unit**, with libtest's test threads as tasks. 0.03 s to `info` or `diff` it, against a 60 s budget. |
| 3 | Go / no-go for rung 2 on mechanics (E7, E8, E2) | **GO.** 0 output differences, 0 failed freshness checks, 0 fallbacks, 100.0% coverage. The mirror + `RUSTC_WORKSPACE_WRAPPER` design is not reworked before rung 2. |

**Decision 1, stated with its limit.** The ruling is that the runtime gate survives *at test-suite
granularity on bloomery*. It is not a claim about call-dense code: the same gate costs ×5.9 on
`fib(30)` at opt-0. If rung 2 ever measures a target whose suite is call-dense, this decision is
the one to re-open — the threshold is in §1 and the instrument is `rust/spike/measure.py`.

**Decision 2, stated with its limit.** One binary is a comfortable trace unit; so, at these sizes,
is a whole invocation (119 processes, 132 344 events, 22 MB of traces, 22.7 s to convert). The
choice of the binary is about *what a question is asked of*, not about what the reader can carry.

**What these numbers do not license.** Every endpoint here is mechanics: does the build survive,
does the output survive, does the transformer reach the code, is the trace readable. None of them
says the recorded trace *answers a debugging question* about Rust, and none of them was measured on
a second workspace. Rung 2 starts with the gaps in §5, not with these five PASSes.

## 5. Rung-2 gaps found

Everything the spike surfaced that rung 2 must decide, close, or knowingly carry. Each entry says
what was MEASURED, not what is suspected.

### A. Gaps in the recorder / converter (the four the plan predicted, and what they measured)

1. **Per-process exit status is not observable to the runtime.** *Measured: 0 processes with their
   own status.* The wire format carries no exit code, and a `Drop`-based runtime cannot see one
   (`std::process::exit` and a test binary's normal return both bypass it). The converter therefore
   writes **cargo's** status as `exit_status` for every process of an invocation
   (`exit_status_basis = "cargo"`), so all 119 traces of one call-arm invocation carry the same
   number. Rung 2 must either record the status at the process's own exit (an `atexit`/destructor
   hook that survives `exit()`, or the parent recording each child's `wait` status) or declare
   `exit_status` unwitnessed rather than borrowed.
2. **A thread alive at process exit loses its buffered spool tail.** *Measured: 100 spool files
   without a `THREAD_END` record, in 3 of 119 processes* — 64 of 81 threads in `api_v1_honesty_test`,
   32 of 62 in `api_v1_test`, 4 of 71 in `api_native_test`. These are the daemon's HTTP server
   threads: they are still running when the test binary exits, so their per-thread `BufWriter` is
   never flushed by the thread-local destructor. The converter reports them in `live_threads` and
   still sets `incomplete = false` (the *process* finished; the thread did not) — which is the right
   distinction and also the one a reader will misread. The spec's rung-2 `MAP_SHARED` spool design
   closes this; until it lands, any trace of a server-shaped test under-reports those threads' tails
   by an unmeasured amount. **The loss is silent in the trace's own event counts.**
3. **`source_hashes` is empty.** *Measured: `{}` in every trace.* The spike never hashes the
   instrumented files, so nothing in a trace pins the source it was recorded against. Combined with
   gap 8 (site identity is per-unit), a trace cannot today prove which revision of a file its
   `firstlineno` values refer to.
4. **Output is not captured.** *Measured: `capabilities.output = false`.* libtest's own capture sits
   between the test and the recorder; the spike does not touch it. Every question of the form "what
   did this test print" is unanswerable from a rung-1 trace.

### B. Gaps the measurement itself surfaced

5. **The query CLI narrates a Rust trace in Python.** Verbatim, from `sensorium info` and
   `sensorium diff` on a real bloomery trace: `python ?`; "0 causal events outside any **asyncio**
   task"; "each thread row covers the events that ran in no **asyncio** task"; "threads started: 26
   besides the main one, **through Python's own threading/_thread**". None of that is true of a
   `sensorium-rt` trace, and the `threading/_thread` line is a positive claim about provenance the
   trace does not carry. The reader is a shared surface now; rung 2 needs its prose to key off
   `meta.lang` (or the phrasing to become language-neutral) before a Rust trace is handed to anyone.
6. **`tree` and `frame` drop the `unread` marker that `grep` keeps.** Same trace, same event:
   `sensorium grep` prints `e11 CALL load_config() <unread: locals>`, while `sensorium tree` prints
   `f47 e66 default_probe_timeout_secs() -> ?` and `sensorium frame f11` prints `args: (none)`.
   `(none)` reads as "called with no arguments"; the truth is "arguments were never read". This is a
   Python-core gap (`capabilities.locals = false` is not new), surfaced by Rust because a Rust trace
   is *entirely* locals-free. It is the named bug class: a value that looks like a measurement and is
   not.
7. **Child processes spool but are not linked to their parent.** *Measured: 48 of the 119 processes
   in one invocation were spawned `flywheel-tool` children*, each converted into its own trace, while
   every trace declares `capabilities.children = false` and `info` says so ("there is no
   child-process record to read; absence of the record is not a record of absence"). The relationship
   exists on disk (`ppid` in each proc header) and is thrown away by the converter. Rung 2 should
   decide whether a `cargo test` invocation is one trace with children or N traces with a join key.
8. **Site identity is per-unit, not per-source.** *Measured: 7360 raw sites across 77 manifests
   against 1723 distinct `(file, qualname, firstlineno)` triples* — a 4.3× duplication, because
   `crates/bloomery-daemon/tests/common/` (13 files) is compiled into all 69 integration-test units
   and `bloomery-daemon`'s lib is compiled at two feature sets. The same source function therefore
   has a different site id in every unit that compiles it. Rung 1 does not need to merge them; any
   rung-2 feature that compares two traces of *different* binaries does.
9. **`env_hash`, `toolchain`, `start_ts` and `end_ts` are conversion-time approximations, not
   recorded facts.** `env_hash` digests the *converter's* environment (the wire format carries none),
   `toolchain` is whatever `rustc --version` says when `convert.py` runs, and the timestamps are
   derived from the spool's monotonic span anchored at conversion time. They are plausible values in
   fields a reader will take as witnessed.
10. **`truncated_count = 0` and `records_dropped = {}` are asserted, not witnessed.** The runtime has
    no drop counter; a spool that lost records (a full disk, a killed thread) converts to a trace that
    positively claims nothing was dropped.
11. **A doctest process's `exe` no longer exists when the converter runs.** Measured on the probe
    workspace (`mechanics.sh`: `the_doctest_process_spools_a_probe_core_call`): doctests link the
    instrumented rlibs and DO spool, but their executable is a `/tmp/rustdoctest*/rust_out` that
    rustdoc deletes immediately. **Not exercised on bloomery** — `bloomery-daemon` has 0 doctests, so
    no rustdoc process appears among the 119. Rung 2's converter must keep expecting a dead `exe`.
12. **The mirror's lock is a spike-grade lock.** `mirror::Lock` is a lock *directory* whose staleness
    rule is a 120-second timeout (`STALE_AFTER`), broken unconditionally by the next wrapper — chosen
    so a spike cannot deadlock a build when a wrapper process dies. Under a 16-way cargo build that is
    a real race: a mirror update that legitimately exceeds 120 s would be raided by a peer. It never
    fired here (77 and 108 units, whole builds in 5.5 s), which is evidence of *not having hit it*,
    not of correctness.
13. **The 256-unit ceiling was never approached.** The runtime refuses to record past a 256th unit in
    one process. The workspace-wide build produced 108 units *in total*; no single process here
    linked more than a handful. Untested, and a real limit for a bigger workspace.

### C. Method gaps in this measurement, recorded so the next one does not repeat them

14. **E2's estimand was mismatched in the plan and had to be fixed before the number could be read.**
    §1's lens names `cargo test -p bloomery-daemon`; the plan's step 3 names a census over
    `crates/*/src` + `crates/*/tests`. Those are different file sets — 1723 eligible items versus
    2051 — and crossing them scores cargo's package selection as transformer coverage (84.0%). The
    mismatch was found in preflight, the supplementary workspace-wide build was declared before the
    run, and §3 carries every denominator. **A reader who disagrees with the reading in §4 has one
    command to re-render the other way**; the raw manifests are in the ledger. The lesson is the
    known one: check estimand comparability before a difference is named a finding.
15. **`--lib` has 53 tests, not the 64 §1 predicts.** *Measured: `running 53 tests`.* `config_test`
    has exactly the 26 §1 predicts. The 64 was stale when it was written; it changed no threshold and
    is recorded rather than silently corrected.
16. **The E1 "plain" arm's `--no-run` wall is not a build.** §3 reports 0.045 s for it with that lens
    attached: bloomery's plain artifacts already existed (Task 0 built them at 4.76 s), so the plain
    number is a freshness check and the instrumented 5.48 s is a genuine clean build of 77 units. The
    two are not a build-cost comparison and §3 says so in the cell.
17. **E7 and E8(b) are probe-workspace measurements.** Bloomery is read-only for this plan, so the
    output-identity endpoint and the "touch one line" freshness check ran on `rust/spike/probes/ws/`.
    E8(a), (c) + sentinel and (d) *did* run on bloomery. Rung 2 should re-measure E7 on a real target
    the first time it is allowed to write one.
18. **The `off` arm's ratio is below 1 and the measurement cannot resolve its sign.** ×0.9975 at n=5
    with overlapping min–max ranges is "indistinguishable", not "faster". Reported as measured; not
    to be quoted as a speedup.
19. **The instrumented artifact set is left behind on disk.** Cleanup removes
    `bloomery/target/sensorium` (104 MB measured) as the plan specifies, but the instrumented rlibs
    and ~70 test binaries stay in `bloomery/target/debug/deps` under their own `-C metadata` (free
    disk went 10.8 GB → 6.1 GB across the run). They are harmless and gitignored; `cargo clean` is the
    only way to reclaim them, and it would take the plain set with it.
