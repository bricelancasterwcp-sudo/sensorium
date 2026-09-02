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

**Erratum 2026-09-02 (recorded before any E2 number was read; the table above is left byte-unchanged on purpose).** Two defects in the E2 row, neither of which moves a threshold:

- *Scope.* The row's lens column (`cargo test -p bloomery-daemon`, from this section's opening lens sentence) and its denominator (a census over the workspace's source) name **different file sets**: that build compiles 1723 of the workspace's 2051 eligible fn items, because `bloomery-bench` and the `tests/` of `bloomery-core` and `bloomery-substrate` are in no `-p bloomery-daemon` build. Both self-consistent readings are reported in §3 (numerator and denominator over the same files, three ways, all 100.0%) and the crossed figure (1723/2051 = 84.0%) is preserved there and named as scope-mismatched. See §5.14.
- *Derivation.* The row's derivation reads "5 `const fn` of 756 items are excluded by rule (99.3%)". The census counts **744** fn items in `crates/*/src` (2056 across `crates/*/src` + `crates/*/tests`); 756 was a mis-transcribed count. The corrected derivation on the src-only file set is 5 `const fn` of 744 items excluded by rule, i.e. **739/744 = 99.33%** expected — the same figure to two decimal places, for the same reason, so **the 98% floor stands exactly as pre-registered**.

No threshold changed. No arm was added to a timed endpoint. The supplementary workspace-wide build that supplies the comparable numerator was declared before the run and placed last in the protocol; see §4.

**Erratum continued, 2026-09-02 (appended on the docs branch after the final review; the §1 table above is still byte-unchanged).** Three facts the erratum leaves out. None of them moves a number and none of them changes the verdict.

- *The pre-registration rules the crossed reading out on its own terms.* The E2 row's own measurement column reads "eligible = every `fn` item in workspace source except `const fn` and `extern` fns, **counted by a syn census over the same files**". A numerator taken from a `-p bloomery-daemon` build against a whole-workspace denominator is not "the same files", so the crossed 1723/2051 reading violates the pre-registration **as written**, independently of any number it happens to produce.
- *The run was one detached process, and the supplementary build was in the script before it launched.* The runner ran once under `setsid nohup`; `results.json`'s `steps` records `[15:40:06] E2[daemon build]: distinct=1723 raw=7360 units=77 fell_back=0 unreached=0` and, as the last measured step of that same process before `cleanup`, `[15:45:02] E2[workspace build]: distinct=2051 raw=7895 units=108 fell_back=0 unreached=0`. The supplementary workspace-wide `--no-run` was already in `measure.py` — disk-guarded, placed after every timed arm — when the process was launched. Nothing was added mid-run and no arm was re-rolled.
- *The runner's DEFAULT assembly renders the crossed reading; the workspace headline was selected after the run.* `measure.py`'s assembler reads `os.environ.get("SENSORIUM_E2_DENOM", "all")`, and `all` pairs the `-p bloomery-daemon` numerator with the whole-workspace denominator — 1723/2051 = 84.0%, **below the floor**. The committed `results.json` carries `"e2_headline_denominator": "workspace"`, chosen by a controller ruling 2026-09-02 (ledger, local-only) after the run. **The verdict is neutral either way**: the pre-registered lens's own same-file reading, **1723/1723 = 100.0%**, passes the 98% floor with no supplementary build at all, and it is in §3's denominator table.

**Citation-form correction, 2026-09-02 (appended on the docs branch; the §1 table stays byte-unchanged).** The E1 row's derivation cites "spec §12.4". The spec has no §12.4: §12 is a numbered list of five rulings requested from Brice, and the ×1.5 threshold is **item 4** ("Compile-once vs cargo feature is decided by E1, not by ruling; the ruling requested is the 1.5× wall-clock threshold itself"). Read it as **spec §12, item 4**. No threshold moves.

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

The `steps` line `micro-bench: 0 lenses` beside this two-lens table is a first-pass regex artefact, not a missing measurement: the runner's in-run parser matches `result caller=(\S+) arm=` and the lens is TWO tokens (`caller=dev(opt0) rt=opt3`), so nothing matched and the count printed 0. The table's numbers come from the verbatim `result` lines the runner stored regardless — `results.json`'s `micro_bench.lines`, traced to `logs/bench-run.log` — which the assembler re-parses with the two-token lens.

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

| Denominator (eligible fn items) | Numerator, scoped to the same files | Numerator from the `-p bloomery-daemon` build | Numerator from the workspace-wide build |
|---|---|---|---|
| `crates/*/src` + `crates/*/tests` — the plan's file set (2051) | 2051/2051 = 100.0% | 1723/2051 = 84.0% (**scope-mismatched**) | 2051/2051 = 100.0% ← §4's reading |
| `crates/*/src` only (739) | 739/739 = 100.0% | 679/739 = 91.9% (**scope-mismatched**) | not comparable (the wide numerator spans src and tests) |
| the files a `-p bloomery-daemon` build reaches (1723) | 1723/1723 = 100.0% | 1723/1723 = 100.0% | not comparable (the wide numerator spans files this build never compiles) |

Every cell reads `<numerator>/<denominator>`. The diagonal — numerator and denominator over the same files — is the only self-consistent reading, and it is 100.0% three times over; the two cells marked **scope-mismatched** cross a one-package numerator with a whole-workspace denominator.

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

- **Test binaries cargo ran: 72** (from cargo's own `Running` lines), plus 1 `Doc-tests` target that ran 0 tests. Of those binaries, **71 spooled**; the 1 that did not is `bloomery_daemon-c359ed0433bcd7d2` (`unittests src/main.rs`), which ran 0 tests and so never entered an instrumented fn — not a recorder failure.
- Processes that spooled, and that E0 converted: **119** — the 71 binaries above plus 48 instrumented `flywheel-tool` children they spawned (1 distinct child executable). Three different counts, three different quantities: 72 run, 71 spooled, 119 processes.
- Events per second of recording (call arm): 1556988 events per second of ADDED wall, or 15874 per second of suite wall — LENS: the added wall is 0.085 s at n=5 and is inside the arms' own spread, so the first figure is an order of magnitude, not a rate.
- Bytes per event on disk: 24.93 (24 B/record plus one file header per thread).
- libtest thread naming as observed, on the `--lib` trace: 53 of 57 emitting non-main threads carry the test's own name (`codec_probe::fixtures::tests::parses_the_two_brief_examples`, `envelope_lens_names_are_pinned`, …) — exactly the 53 tests libtest ran. The remaining 4 (serials 55, 56, 57, 58) are threads the TESTS spawned and carry no name at all, so they become unnamed tasks in the trace (§5). `config_test`'s 26 threads are all named. Per-task naming needs no heuristic for a test thread and has no name to use for a spawned one.
- Per-process exit status available to the runtime: **0** — a design fact read off the wire format and the runtime, not an instrument's output; §1 pre-registered it as `expected: NOT available`, and every trace carries cargo's status instead (§5.1).
- Wall of `sensorium info`/`diff`: warm-read medians of 3 consecutive runs on the same trace files (runs 2–3 hit a warm page cache); no cold-start number was taken.
- Wall time of the spike's own build: 4.24 s — `cargo clean --release && cargo build --release`, 4 workspace units recompiled, third-party deps warm. PROVENANCE: this one ran before the runner existed, so it has no log in the ledger and the number is transcribed by hand from the preflight transcript in `task-5-report.md` §1; reported, not gated.

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
**×5.93** and call **×62.2**. Bloomery's suite records **15 874 events per second** of suite wall
(132 344 events / 8.337 s); `fib(30)` at the same lens records **30.4 million events per
second** — one `enter`/`Drop` pair per call at 65.871 ns/call is 2 / 65.871 ns = 3.04×10⁷
events/s, and the arm's own 129 242 130-byte spool confirms the pairing exactly
(24 B × 2 × 2 692 537 calls = 129 241 776 B, plus 354 B of per-thread file headers). Both
numbers are events per second; the call rate is half the second one (15.2 M calls/s) and
is not what is being compared. The gap is ≈1900×. The reading that survives is *compile-once-gate-at-runtime is free
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
what was MEASURED, not what is suspected. Numbering is append-only: item **20** was added after
review and belongs with section B, but keeps its own number so that §4's and the review's
references to §5.14 and §5.18 stay valid.

### A. Gaps in the recorder / converter (the four the plan predicted, and what they measured)

1. **Per-process exit status is not observable to the runtime.** *A design fact, not a
   measurement: no instrument was run for it.* Established by reading the wire format and the
   runtime — §1 pre-registered it as "expected: NOT available to the runtime", and §3 reports 0
   as that expectation holding. The record stream carries no exit code, and a `Drop`-based
   runtime cannot see one
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

20. **A thread the tests spawn has no name, and becomes an unnamed task.** *Measured: in the
    `--lib` trace, 53 of 57 emitting non-main threads carry the test's own name — exactly the 53
    tests libtest ran — and 4 (spool serials 55–58) carry the empty string.* Those four are
    threads the test bodies spawned themselves: libtest names the thread it runs a test on, and
    nothing names a thread a test spawns. The converter turns each into a `tasks` row with a NULL
    name, so `diff` compares them by `(name, hash)` with no name to compare on and `tree` prints
    a task the reader cannot identify. (`config_test`'s 26 threads are all named, which is why
    this is invisible in that half of E0.) Rung 2's `spawn_child` naming (spec §3.5) is what gives
    these threads a name; until it lands, per-task naming is complete only for threads libtest
    itself created.

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
18. **The `off` arm's ratio is below 1, and there is a systematic mechanism beside the noise.**
    ×0.9975 at n=5 with overlapping min–max ranges is "indistinguishable", not "faster", and is
    not to be quoted as a speedup. Beyond that spread, the fixed P,O,C order interacts with a
    **monotonically decaying background load**: the E8 instrumented build ran immediately before
    E1 with no cooldown, and the 1-minute load recorded at each arm's start falls across the run
    (medians **P 1.54 / O 1.18 / C 0.92**; P is the highest-load arm in 4 of the 5 rounds). A
    fixed order under a decaying load biases the first arm slow, which is exactly the direction
    that would push off/plain below 1. The pre-registered order stands and the effect is
    immaterial against a ×1.5 rule — but a future E1 should either interleave the order or wait
    for the load to settle, and a ratio read anywhere near the threshold under this design should
    not be believed.
19. **The instrumented artifact set is left behind on disk.** Cleanup removes
    `bloomery/target/sensorium` (104 MB measured) as the plan specifies, but the instrumented rlibs
    and ~70 test binaries stay in `bloomery/target/debug/deps` under their own `-C metadata` (free
    disk went 10.8 GB → 6.1 GB across the run). They are harmless and gitignored; `cargo clean` is the
    only way to reclaim them, and it would take the plain set with it.
### D. Appended on the docs branch after the final review (2026-09-02)

21. **`--remap-path-prefix <mirror>=<workspace>` is load-bearing, not belt and
    braces.** *Entries 21–29 were appended to this document on branch
    `docs/rung1-spike-findings` after the final review; the copy on
    `spike/rust-mechanics` — byte-identical to this document at commit
    `27995f0` — stops at entry 20 and does not carry any of them.* Measured,
    from **task 3's report** (falsification #2 of its §8 table — every check made to
    fail once, the breakage applied, `mechanics.sh` re-run, the source
    restored): with the flag not appended,
    `e7_backtrace_locations_identical` **FAILED**, the instrumented arm's
    backtrace frames printing
    `/tmp/…/sensorium/mirror/probe-app/tests/e7.rs:22:5` where the plain arm
    printed `./tests/e7.rs:22:5`. The mechanism is DWARF: rustc records the
    compilation directory (`DW_AT_comp_dir`) and that directory *is* the
    mirror, and std's backtrace printer resolves frames against it. `file!()`
    and `panicked at …` survive the mirror without the flag; backtraces do
    not. E7's **0 differences** (§4) is therefore evidence for the mirror
    **plus the remap**, never for the mirror alone — spec §2.2 called the flag
    "belt and braces" and is amended.

22. **The mirror must be per unit, `mirror/<-C metadata>/`, not one per
    workspace.** Measured, from **task 3's report** (§13 and §13.3a). Cargo
    compiles one crate root as several units — `probe-core/src/lib.rs` as
    `--crate-type lib` *and* again with `--test`, each with its own
    `-C metadata` — and the mirror's cache key was
    `<tool hash>:<sha256 of the original source>` with **no unit in it**, so
    the second unit found the file "fresh" and compiled a crate root whose
    `__SENSORIUM_UNIT` static named its twin. Every event that unit recorded
    was attributed to the wrong unit. E7 and E8 are blind to it (line numbers
    and freshness do not care) and the build is green. It surfaced only as an
    intermittent failure of `the_doctest_process_spools_a_probe_core_call` —
    **roughly 1 run in 3 under `-j16`** — whose printed diagnostic named it at
    once: `want=['25551d76021b1fd1']`,
    `seen=[…:units={'0': '447e8542d2a0157a'}:spools=1]`, the doctest linking
    `probe_core`'s **lib** rlib while the unit that registered was
    `probe_core`'s **test** unit. The fix is one mirror and one cache subtree
    per unit (`mirror/<metadata>/`, `cache/<metadata>/`), plus a deterministic
    check beside the probabilistic one
    (`every_units_mirror_carries_its_own_metadata`, 9 crate roots per run);
    **six consecutive clean runs after the fix, against 2 failures in 5
    before**. Task 3's re-review verified the shape on its own run: **0 shared
    inodes across the probe's 9 unit mirrors, 92 KB for all nine** (they are
    symlink trees). Per-unit mirrors also make the cross-unit lock of gap 12
    uncontended by construction — which is why that gap is a carried weakness
    and not a live race.

23. **rustdoc bypasses `RUSTC_WORKSPACE_WRAPPER`, and doctests spool anyway.**
    Measured, from **task 3's report** (§13.3), by a control that runs every
    time rather than once:
    `without_rustdocflags_the_doctest_fails_E0463` re-runs the same
    `cargo test --doc` with the wrapper environment reconstructed by hand
    *minus* `RUSTDOCFLAGS` — no sabotage switch in the binary, the variable is
    simply not set — and requires a non-zero exit carrying
    `error[E0463]: can't find crate for sensorium_rt`. Cargo routes `rustc`
    through the workspace wrapper and says nothing about `rustdoc`, so the
    driver must carry the same `--extern sensorium_rt=<rlib>` and
    `-L dependency=…` through **`RUSTDOCFLAGS`**. Doctests are not a route to
    skip: the snippet itself is not instrumented, but the process **links the
    instrumented rlibs and DOES spool** real CALLs
    (`the_doctest_process_spools_a_probe_core_call`, measured
    `1 rust_out(1)`), from an `exe` that rustdoc has already deleted — the
    dead-`exe` consequence already carried as gap 11. Not exercised on
    bloomery, which has 0 doctests.

24. **The rt rlib built in the spike workspace linked, and two `libc` crates
    coexisted in one unit.** Measured, from **task 3's report** §4 ("Linkage:
    did two libc crates coexist?" — "**Yes.** No `STOP`/`BLOCKED`"). Rung 1
    did not build `sensorium-rt` into the target workspace's `deps/` as spec
    §2.3 specifies; it built it `--release` in the *spike* workspace and had
    the wrapper pass `--extern sensorium_rt=<rlib>` plus
    `-L dependency=<spike target/release/deps>` so the rt's own `libc`
    resolves. `probe_app` then linked its own
    `liblibc-8fa2745d3cf757aa.rlib` from the probe's dev deps *and*,
    transitively through `sensorium_rt`,
    `liblibc-21f15d3c5e5e6ae6.rlib` from the spike's release deps — different
    `-C metadata`, same source version, both in one unit. **rustc raised
    nothing**; `sensorium_rt` exposes no `libc` type across its API, which is
    why the two never have to be reconciled. The consequence is measured, not
    argued: **0 units fell back to the real tree** across the probe's 9 units,
    the 77 of the `-p bloomery-daemon` build and the 108 of the workspace-wide
    build, with 0 `fell back to the real tree` lines in any build log (§3 E2).
    **Two things are a rung-2 decision, not a rung-1 result (spec §2.3):**
    (a) the `-L dependency` shape works only because that directory held
    **exactly one** `liblibc-*.rlib` — a second would make rustc refuse with
    "multiple candidates", and the driver does not guard against it; (b) the
    rlib must be taken from `deps/`, not from cargo's uplifted
    `target/release/libsensorium_rt.rlib`, whose directory carries no
    `liblibc-*.rlib` at all. Whether the rlib moves into the target's own
    `deps/` is rung 2's call; the record is that it did not block rung 1.

25. **The `BufWriter` spool's loss model, as measured — and `MAP_SHARED`
    remains the design.** Measured, from **task 1's report** (finding 1), by
    reading the spool bytes rather than reasoning about them: one guard on
    main, one blocked thread named `leaked`.

    | how the process ends | main's spool | the blocked thread's spool |
    |---|---|---|
    | return from `main` | 87 B, tail `…ff000000` = THREAD_END | 17 B (header only) |
    | `std::process::exit(0)` | **87 B, tail `…ff000000` — byte-identical shape** | 17 B (header only) |
    | `std::process::abort()` (rc 134) | **15 B (header only)** | 17 B (header only) |

    87 B is a 15-byte header (`11 + len("main")`) plus 3 × 24-byte records;
    17 B is `11 + len("leaked")`. So `exit()` runs the **calling** thread's
    thread-local destructors — glibc's `exit()` calls `__call_tls_dtors()` —
    and that thread's spool flushes complete and closed, while every other
    live thread keeps only its header; `abort()` and a fatal signal run no
    destructor at all and are the only total-loss row, main included. The two
    scenarios are `exit-with-live-thread` and `abort-with-live-thread`, both
    mutation-checked. This is narrower than "any process that does not return
    from `main` loses every thread's buffer", which task 1's first report said
    and withdrew. It is the case **for** spec §4's `MAP_SHARED` spool, not a
    change to it: `MAP_SHARED` makes all three rows moot. Until it lands, gap
    2's 100 tail-less spools in 3 of 119 processes are the same mechanism seen
    in the field.

26. **`#[cfg_attr(.., path = ..)]` modules are never evaluated and go to
    `unreached_files`.** Measured, from **task 3's report** (§10 finding 5,
    pinned by
    `cfg_attr_path_records_the_default_file_unreached_and_never_rewrites_it`).
    The module walk resolves `mod` declarations from the crate root by the
    file-system rules and by a literal `#[path = ..]`; it does
    **not** evaluate `cfg_attr`, so a module declared
    `#[cfg_attr(windows, path = …)]` is recorded as unreached rather than
    guessed at — conservative by design, and the reason the walk over-matches
    any attribute containing "path" rather than under-matching. On the probe
    workspace that is exactly **1** file (`maybe.rs`); on bloomery it cost
    nothing, §3 reporting **0** files a module walk could not reach across 77
    manifests. Rung 2 can do better without evaluating `cfg` itself: rustc's
    own argv carries the `--cfg` flags for the unit being compiled, and the
    wrapper already reads that argv.

27. **`(file, qualname)` is not unique inside one file, and bloomery has a
    live case.** Named in **task 2's report**'s review round as a deferred
    minor — "1 bloomery file, 2 sites: main.rs `run` ×2". The file is
    `crates/bloomery-daemon/src/main.rs` at bloomery `e209ed9`; it declares
    `fn run` **twice** at top level — `#[cfg(feature = "llama")] fn run(config: Config,
    journal: Journal) -> !` and `#[cfg(not(feature = "llama"))] fn
    run(_config: Config, _journal: Journal) -> !`. Both carry the same
    `(file, qualname)` and differ only in `firstlineno`. Rung 1's *site*
    identity is the triple `(file, qualname, firstlineno)` and separates them
    — which is why §3's distinct counts are unaffected — but spec §5.4's
    `code_objects` identity is `file` plus the file-local qualname, and merges
    them into one code object with two bodies. Cfg-gated twins are the case
    bloomery actually has; several trait impls of one type, and a nested `fn`
    sharing a name across two inline `mod`s, are the same shape. This is a
    **§5.4 consequence to name**, not a defect found: rung 2 decides whether
    `code_objects` carries the line, or whether the merge is the intended
    reading and `tree`/`diff` must say so.

28. **At `opt-level = 0` the gate costs ~5 ns per site: the shape of a
    cross-crate call, not of a predicted branch.**
    Measured, from **task 1's report** (the two-lens bench table). At E1's own
    pre-registered lens (`caller=dev(opt0) rt=opt3`), `fib(30)` costs
    **1.3484 ns/call plain against 6.2475 ns/call at tier `off` — ×4.633,
    +4.899 ns per call**, and 67.3076 ns/call at tier `call`. §3's table is
    the same bench re-run by the runner at the same lens (1.0595 / 6.2875 —
    ×5.934, +5.228 ns): the added nanoseconds agree, the ratio differs because
    the plain baseline does, and the first reading sits at the top of the
    design review's ×3.4–4.9 band while the second is above it — neither is
    below. That the ~5 ns are a call rather than a branch is an INFERENCE from
    the shape, not a measurement of it: `#[inline]` on `enter` cannot fire
    across a crate boundary at `opt-level = 0`, and no disassembly was taken.
    Against that, E1's suite-wall reading is **×0.9975** and bloomery's suite
    records 15 874 events per second where `fib(30)` records 3.04×10⁷ — the
    ≈1900× density gap of §4 — so whatever those nanoseconds are, they are
    **immaterial at suite granularity, and only there**. This is the rung-2
    lever if recording ever has to get cheaper, and the release-caller lens
    (×2.045, 0.5133 → 1.0499 ns/call, §3) is the measurement of what letting
    the gate inline across the crate boundary would buy — which is also the
    experiment that would settle the inference above.

29. **The wrapper's absolute-crate-root fallback writes no manifest.** Read
    off the wrapper's own source (`cargo-sensorium/src/wrapper.rs`) and
    measured as 0 on bloomery. When cargo hands the wrapper an **absolute**
    crate root — workspace members get a relative one, so an absolute root is
    not the shape the mirror was designed for — the wrapper prints
    `sensorium: unit <crate> (<metadata>) fell back to the real tree: absolute
    crate root <path>` and passes straight through to rustc **without writing
    or patching a manifest**. Every other fallback path either patches
    `fell_back: true` into the unit's manifest or writes a stub, so this one
    is visible to the **log channel only**. `mechanics.sh`'s `no_unit_fell_back`
    reads both channels and would still catch it; a rung-2 identity or coverage
    check that reads manifests alone would not. It never fired here: §3 reports
    0 fell-back units across 77 manifests and 0 `fell back to the real tree`
    lines across every build log. The same shape one level up:
    `every_units_mirror_carries_its_own_metadata` counts the crate roots it
    checked and prints the count, but asserts only that the bad list is empty,
    so at `checked == 0` it passes vacuously. **Rung 2's identity check must
    assert `checked > 0`.**
