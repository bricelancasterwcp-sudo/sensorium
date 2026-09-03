# Rung 1 — Rust mechanics spike (throwaway, pre-registered): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure, before any production Rust is written, whether the cargo mechanics the design rests on hold on bloomery: a `RUSTC_WORKSPACE_WRAPPER` build with a workspace-root mirror and a runtime linked by `--extern`, at the call/return tier only. The output is four numbers with pre-registered kill criteria (E0, E1, E2, E7, E8 of the spec) and two decisions: compile-once-gate-at-runtime versus a cargo feature, and the trace unit. The code is evidence, not product.

**Architecture:** A separate cargo workspace under `rust/spike/` on branch `spike/rust-mechanics`: a minimal runtime (`sensorium-rt`), a minimal transformer (`sensorium-transform`, entry guards only), and the driver/wrapper binary (`cargo-sensorium`). A throwaway Python converter turns spools into a format-4 trace using sensorium's own `TraceWriter`, so `info`/`diff` are the real commands. A measurement runner writes `results.json` with none-versus-zero discipline and renders the findings document. Nothing under `rust/spike/` merges to main; the findings document and a spec amendment do.

**Tech Stack:** stable rustc 1.96.0 / cargo 1.96.0 (pinned; no nightly); crates `syn` (full, visit, extra-traits), `proc-macro2` (span-locations), `serde`/`serde_json`, `libc`; Python 3.14 venv for the converter and runner; sensorium 0.5.0 (main @ b9873dd) as the reader.

**Spec:** `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` — §2 (mechanics: 2.1 hook, 2.2 mirror, 2.3 linkage, 2.4 site identity, 2.5 run model), §3.2 (entry guard), §4 (runtime: serials, sequence, spools, tasks), §5 (format 4), §8 (E0, E1, E2, E7, E8), §11 rung 1. The house rules for measurement are `~/.claude/skills/rigorous-experiments/SKILL.md`: pre-register, then obey; none-versus-zero; name the lens; mutation-test every test.

## Global Constraints

- Every number in §Pre-registration is committed (Task 0) BEFORE any crate exists. After a measurement completes, no threshold moves, no arm is added, no run is re-rolled; an infrastructure kill (build failure, box contention noted in the log) may be re-run from zero with the reason recorded.
- The bloomery tree at `/home/brice/workspace/bloomery` is read-only for this plan: no file under it is edited, `Cargo.lock` stays untouched, and the only writes are under `target/` (which is gitignored). `git -C ~/workspace/bloomery status --porcelain` must be empty before and after every task that touches it. Bloomery is pinned at the commit recorded in Task 0 (`e209ed9` on `split-python-trio` unless Brice moves it first); the pin is recorded in `results.json`.
- Ambient pins recorded in every results file: rustc/cargo versions, `RUSTFLAGS`/`CARGO_INCREMENTAL`/`RUSTC_WRAPPER` (all unset), `--test-threads` (cargo default), governor (`powersave`), `nproc` (16), 1-minute load before each arm, and whether any other build was running (the runner refuses to start an arm if load > 4.0).
- Runtime dependencies of `sensorium-rt`: `libc` only. The transformer and driver may use `syn`, `proc-macro2`, `serde_json`. No `rusqlite`; the converter is Python.
- No file over 800 lines, in Rust or Python.
- Spike code is labelled throwaway in every crate's `Cargo.toml` description and in `rust/spike/README.md`; it is never `cargo install`ed and never referenced from `pyproject.toml`.
- Commits: conventional prefixes, trailer lines per the session's git rules.

---

## Pre-registration (Task 0 commits this section verbatim as `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` §1 before any code)

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

---

### Task 0: Branch, pre-registration, ledger, preflight

**Files:**
- Create: `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` — §1 Pre-registration (the section above, verbatim), §2 Ambient pins (filled), §3 Results (empty table with `not measured` in every cell), §4 Decisions (empty), §5 Rung-2 gaps found (empty)
- Create: `rust/spike/README.md` (throwaway notice; how to build; how to run the measurement)
- Commit this plan file.

**Invariants:**
- The pre-registration commit precedes every other commit on the branch; `git log --format=%s -- docs/superpowers/spikes/` proves it.
- Preflight recorded in §2: `rustc -V`, `cargo -V`, bloomery commit and `status --porcelain` (empty), `nproc`, governor, `RUSTFLAGS`/`CARGO_INCREMENTAL`/`RUSTC_WRAPPER` unset, free disk on the filesystem holding `bloomery/target` (measured 2026-09-02 before Task 0: a full set of the daemon's ~70 debug test binaries is 2–3 GB, so the instrumented second set plus the mirror and spools is ≈ 5 GB; refuse to proceed under 8 GB free — the floor is 5 GB × 1.5, amended down from a chosen 20 GB before any endpoint was read), and a plain `cargo test -p bloomery-daemon --no-run` wall time as the baseline build cost.

- [ ] **Step 1:** `git checkout -b spike/rust-mechanics main` (main @ b9873dd or later).
- [ ] **Step 2:** Write the spike document with §1 verbatim and §2 filled from the preflight commands; write `rust/spike/README.md`; commit: `docs(spike): pre-register the Rust mechanics spike (E0, E1, E2, E7, E8) before any code`.
- [ ] **Step 3:** Run the preflight; if disk or load refuses, stop and report — do not proceed to Task 1.

---

### Task 1: `sensorium-rt` — the call-tier runtime

**Files:**
- Create: `rust/spike/Cargo.toml` (workspace: `sensorium-rt`, `sensorium-transform`, `cargo-sensorium`, `probes/ws` excluded), `rust/spike/sensorium-rt/{Cargo.toml,src/lib.rs,src/spool.rs,src/thread.rs}`, `rust/spike/sensorium-rt/tests/*.rs`

**Interfaces (exact):**
- `pub struct Unit { .. }` with `pub const fn new(metadata: &'static str) -> Unit`; each instrumented crate root gets `#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = ::sensorium_rt::Unit::new("<-C metadata hash>");`. A unit registers lazily on its first `enter` and receives a process-unique `u8` id; registering a 256th unit makes the runtime refuse to record (every later `enter` is a no-op and a single stderr line says why).
- `pub fn enter(unit: &'static Unit, site: u32) -> Guard` — `Guard` is `#[must_use]`; its `Drop` emits RETURN with outcome `panic` when `std::thread::panicking()` is true, else `none`. Returns an inert guard (no record, no allocation) when the recorder is inert.
- Inert when `SENSORIUM_SPOOL` is unset, or `SENSORIUM_TIER=off`. `SENSORIUM_TIER` values: `off`, `call`; absent means `call`. Read once per process.
- Thread serial: a process-global `AtomicU32`; the thread whose `gettid() == getpid()` (libc) is serial 1 whether or not it emits; every other thread is minted on its first event.
- Global sequence: a process-global `AtomicU64`, one `fetch_add` per record.
- Spool files: `$SENSORIUM_SPOOL/<pid>.<thread_serial>.spool`, opened on the thread's first event; a per-thread `BufWriter` flushed by the thread-local's destructor (rung 2 replaces this with the `MAP_SHARED` design; the spike records the loss it implies: a thread alive at process exit loses its buffered tail — E0 reports `spools_without_end`). Process header `$SENSORIUM_SPOOL/<pid>.proc.json` written once at the first event of the process.
- Reentrancy: a thread-local depth counter; `enter` returns an inert guard while the runtime itself is running (spool open, header write).

**Wire format (verbatim — a converter is written against it):**

```
file header:  b"SNSR" u8 version=1  u32 thread_serial  u16 name_len  name_bytes
record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 reserved=0     (24 bytes, little-endian)
kind:         1 = CALL, 2 = RETURN, 255 = THREAD_END
outcome:      0 = none, 3 = panic   (1 = ok and 2 = err are reserved for rung 2)
site:         unit_id in bits 31..24, site index in bits 23..0
proc header:  {"pid":int,"ppid":int,"exe":str,"argv":[str],"cwd":str,"start_ns":int,"units":{"<unit_id>":"<metadata>"}}
```

`ts_ns` is `CLOCK_MONOTONIC` nanoseconds.

**Falsification tests (each mutation-checked: break the pinned line, the test fails, restore):**
- Serial 1 is the main thread even when a spawned thread emits first.
- Sequence numbers are strictly increasing across two threads' merged records.
- A guard dropped during unwinding writes RETURN with outcome 3; a normal return writes outcome 0.
- `SENSORIUM_TIER=off` writes no file; unset `SENSORIUM_SPOOL` writes no file and allocates nothing (assert no spool dir is created).
- THREAD_END is the last record of a thread that exits cleanly; a thread blocked at process exit leaves a spool without it (documented, tested with a leaked thread).
- A record is exactly 24 bytes; the file header round-trips the thread name.
- Micro-bench `fib(30)` under plain / off / call: reported in ns per call, three runs each, best-of-three; `sensorium-rt` at `opt-level = 3` in the bench profile.

- [ ] Commit: `feat(spike): sensorium-rt, call tier -- entry guard, serials, sequence, spools`.

---

### Task 2: `sensorium-transform` — entry guards by byte-offset splice

**Files:**
- Create: `rust/spike/sensorium-transform/{Cargo.toml,src/lib.rs,src/splice.rs,src/manifest.rs}`, `rust/spike/sensorium-transform/tests/golden/*.rs` (input/expected pairs), `tests/golden.rs`

**Interfaces (exact):**
- `pub fn transform(source: &str, file: &str, unit_metadata: &str, first_site: u32) -> Result<Transformed, syn::Error>` where `pub struct Transformed { pub source: String, pub sites: Vec<Site>, pub skipped: Vec<Skipped> }`, `pub struct Site { pub site: u32, pub file: String, pub qualname: String, pub firstlineno: u32 }`, `pub struct Skipped { pub file: String, pub qualname: String, pub line: u32, pub reason: &'static str }`.
- Injection: the first statement of every eligible fn body becomes `let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);` spliced at the byte offset just after the body's opening brace; the fragment is newline-free. The crate root additionally gets the `__SENSORIUM_UNIT` static appended on the LAST line (no new line before it), so no line number moves.
- Eligible: `ItemFn`, `ImplItemFn`, `TraitItemFn` with a body, at any nesting (inline `mod`, `impl` inside fn). Not eligible and recorded in `skipped` with reason: `const fn` (`"const"`), `extern` fns (`"extern"`), bodies inside `macro_rules!` (`"macro"`, none expected in bloomery). Closures are not fn items at this tier.
- `qualname` is the file-local path in Python's shape (spec §5.4): inline `mod` nesting + enclosing impl's self type + fn name (`Type::method`, `tests::setup`, `fn_name`). `firstlineno` is the line of the `fn` keyword.
- Sites are numbered from `first_site` in source order so a unit's sites are contiguous across its files.

**Invariants (each with a golden or property test):**
- `transformed.source.lines().count() == source.lines().count()` for every golden input and for every file of bloomery's workspace (a property test that walks `../../bloomery/crates/*/src` read-only, parses, transforms, and compares line counts — skipped if bloomery is absent).
- The transformed source re-parses with `syn`.
- Golden pairs cover: free fn, method in `impl`, trait default method, nested inline `mod`, `const fn` skipped, `extern "C"` skipped, generic fn, `unsafe fn`, a fn whose body starts with an attribute or a doc comment on the first statement, an empty body `{}`, a body on one line `fn f() { 1 }`, `#[test]` fn.
- The census used by E2 lives here: `pub fn census(source: &str) -> Census { fn_items, const_fns, extern_fns }` so instrumented ÷ eligible is computed by the same parser that instrumented.

- [ ] Commit: `feat(spike): sensorium-transform -- entry guards spliced at byte offsets, line count invariant`.

---

### Task 3: `cargo-sensorium` — driver, workspace wrapper, mirror, linkage

**Files:**
- Create: `rust/spike/cargo-sensorium/{Cargo.toml,src/main.rs,src/driver.rs,src/wrapper.rs,src/mirror.rs,src/rt_build.rs}`
- Create: `rust/spike/probes/ws/` — copy the design review's probe workspace from `/tmp/claude-1000/-home-brice/4a7bec9b-3369-479b-97f1-fa8021b3479b/scratchpad/review/probes/verify-build/ws/` (members `rt`, `app`; add: a lib `core` depended on by `app`, an integration test in `app/tests/` that spawns a thread and one that spawns `app`'s own bin, a bin target, and the E7 tests: a panicking test, an assert with `file!()`/`line!()`), plus `rust/spike/probes/ws/README.md`
- Create: `rust/spike/tests/mechanics.sh` (the E7/E8 probe-workspace checks as a script that exits non-zero on any failed check and prints one line per check)

**Interfaces (exact):**
- `cargo sensorium test [cargo args...]` — driver role: builds `libsensorium_rt-<hash>.rlib` with the same rustc, target and panic strategy at `opt-level = 3` into `<target>/<profile>/deps/` (rung 1: dev profile only), installs a shim at `<target>/sensorium/shim/<tool-version>-<transform-hash>/cargo-sensorium` (a copy or symlink of the running binary), then execs `cargo test <args>` with `RUSTC_WORKSPACE_WRAPPER=<shim>`, `SENSORIUM_SPOOL=<target>/sensorium/spool/<invocation-id>`, `SENSORIUM_TIER` passed through (default `call`), and prints the spool directory path and cargo's exit status. `--tier off|call` sets the env. Invocation id = `YYYYMMDD-HHMMSS-<6 hex>` (sensorium's run-id shape).
- Wrapper role (argv[1] is the real rustc path, per cargo's contract): pass through untouched when the crate name is `___` or starts with `build_script_`, when `--crate-type proc-macro` is present, when `-vV` or `--print` is present, or when the source is stdin (`-`). Otherwise: resolve the crate root (the one positional `.rs` argument, relative to cargo's cwd = workspace root), collect the unit's source files by following `mod` declarations and `#[path]` from the root (files the transformer cannot reach are left unrewritten and reported), transform each, materialise a workspace-root mirror at `<target>/sensorium/mirror/` (rewritten `.rs` written; every other entry symlinked at each level; `target/` and `.git/` skipped; idempotent, content-hash cached), write the manifest at `<target>/sensorium/manifests/<-C metadata>.json`, `chdir` into the mirror, and exec rustc with cargo's argv unchanged plus `--extern sensorium_rt=<rlib path>`. If rustc fails on the rewritten unit: retry once from the real tree with the original argv, mark `fell_back: true` in the manifest, and print one stderr line naming the unit.
- Manifest (verbatim): `{"unit":"<metadata>","crate_name":str,"crate_type":str,"files":{"<workspace-relative path>":[{"site":u32,"qualname":str,"firstlineno":u32}]},"skipped":[{"file":str,"qualname":str,"line":u32,"reason":str}],"fell_back":bool,"unreached_files":[str]}`. `file` paths in manifests are the ORIGINAL workspace paths, never mirror paths.

**Invariants (tested by `mechanics.sh` on the probe workspace; the same checks run on bloomery in Task 5):**
- E8(a)–(d) as pre-registered, counted from cargo's `Compiling`/`Fresh` output (`-v`).
- E7 zero differences.
- A plain build's binary, run with `SENSORIUM_SPOOL` set, writes no spool; an instrumented one does.
- `cargo test` from the mirror leaves `file!()` and panic locations at workspace-relative paths (argv unchanged, `chdir` into the mirror) — checked by E7.
- The wrapper never writes under the workspace except `target/`.
- The probe workspace's `Cargo.lock` is byte-identical before and after.

- [ ] Commit: `feat(spike): cargo-sensorium -- workspace wrapper, mirror, rt linkage, manifests`.

---

### Task 4: Converter (Python, throwaway) and the first real trace

**Files:**
- Create: `rust/spike/convert.py` (uses `sensorium.store.writer.TraceWriter`, `sensorium.record.fingerprint.Fingerprint`, `sensorium.paths.new_run_id`), `rust/spike/tests/test_convert.py`

**Interfaces (exact):**
- `python rust/spike/convert.py <spool-dir> --target <bloomery-or-probe target dir> [--cargo-exit N] [--argv ...]` → one trace per `<pid>` under `$SENSORIUM_DIR/traces/<run-id>.db`, prints one line per trace: `run: <id>  pid: <pid>  exe: <basename>  events: <n>  threads: <k>  spools_without_end: <m>`.
- Mapping to format 4: `code_objects(file=<absolute workspace path>, qualname, firstlineno)` from manifests keyed by `unit_id → metadata` from the proc header; events CALL/RETURN with `ts_ns`, `thread_id` = spool serial, ordered by `seq` (k-way merge); frames from a per-thread stack (`parent_id`, `depth`, `call_event_id`, `return_event_id`, `closed_by` = `return` for outcome 0, `unwind` with `unwind_exc = {"type":"panic","msg":"","serial":<seq>,"oid":<seq>}` for outcome 3; a frame still open at THREAD_END or at end of spool stays open); `frames.kind = "function"`; every non-main thread with ≥1 event is a `tasks` row named by its thread name (NULL when unnamed), its events carry `task_id`, and it gets a `task_fingerprints` row; the main thread gets a `fingerprints` row over its NULL-task events (zero-count when none); `fingerprint_basis = "per-task"`; `main_thread_ident = 1`.
- Meta (all `REQUIRED_META` keys, spec §5.1): `recorder = "sensorium-rt 0.0.0-spike"`, `lang = "rust"`, `capabilities = {"line": false, "locals": false, "return_value": false, "tasks": true, "threads": true, "children": false, "stdin": false, "output": false, "object_identity": false, "refocus": false}`, `threads_started = spools - 1`, `live_threads = [names of spools without THREAD_END]`, `truncated_count = 0`, `records_dropped = {}`, `source_hashes = {}` (spike; rung 2 hashes the instrumented files), `exit_status = --cargo-exit` (a rung-2 gap: per-process status is not observable by the runtime — recorded in the findings §5), `env_hash` of the driver's environment, `invocation`, `pid`, `ppid`, `exe`, `toolchain`, `cargo_args`, `profile`, `instrumented_units`, `uninstrumented` (units with `fell_back`), `skipped` (from manifests), `incomplete = false` last.

**Invariants (tests, mutation-checked):**
- A converted probe trace opens under `sensorium` 0.5.0 (`Trace.open` does not refuse); `sensorium info` prints `recorder: sensorium-rt 0.0.0-spike  lang: rust` and the declared capabilities; `sensorium flow` refuses (`line: false`); `sensorium tree` renders frames with no `[None]`.
- Two tier-call runs of the probe's test binary convert to traces whose `sensorium diff` reads `MATCH` with "the tasks below carry the whole verdict" (main thread silent, tests as tasks). Two runs with a test body changed read DIVERGED naming the task.
- The k-way merge yields strictly increasing `seq`; a frame stack never goes negative; a RETURN with no open frame is a converter error, not a silent skip.
- A synthetic spool with a leaked thread converts with `live_threads` naming it and `incomplete = false` (the process finished; the thread did not).

- [ ] Commit: `feat(spike): spool -> format-4 converter (throwaway), tests as tasks`.

---

### Task 5: The measurement run

**Files:**
- Create: `rust/spike/measure.py` (the runner), `rust/spike/render.py` (results.json → the findings document's §3 tables)
- Modify: `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` (§3 results, §4 decisions, §5 rung-2 gaps)
- Ledger: `.superpowers/sdd/2026-09-02-sensorium-rung1-mechanics-spike/results.json` and every raw log (gitignored); a copy of `results.json` is committed beside the findings document as `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.results.json`.

**Protocol (the runner enforces it; a human running it by hand follows the same order):**
1. Preflight again (load ≤ 4.0, disk, bloomery clean, pin recorded). Refuse otherwise.
2. E8 on bloomery, in this order, counting workspace units from `cargo -v`: plain `--no-run` (baseline build wall, reported) → instrumented `--no-run` (build wall, reported) → instrumented `--no-run` again, check (a) → plain `--no-run`, check (c), with the sentinel check on the `--lib` binary → instrumented `--no-run`, check (d). Check (b) (edit one source line → only that unit and its dependents recompile) runs on the probe workspace only, because the bloomery tree is read-only for this plan; the results table says so in the lens column.
3. E2 from the manifests written in step 2 versus the census over `crates/*/src` and `crates/*/tests`.
4. E1: five rounds of P, O, C in that order, each `cargo test -p bloomery-daemon` (already built, so the wall is test execution); record wall, per-arm medians, ratio; between rounds sleep 10 s; abort the arm and mark `dropped` if load exceeds 4.0 at its start.
5. E0: convert the spools of the last C round: all binaries (report totals), then `--lib` and `--test config_test` individually; a second tier-call run of each of those two produces the identical pair; time `sensorium info` and `sensorium diff` on each with `/usr/bin/time -f %e`, three runs, report the median.
6. E7 on the probe workspace (Task 3's script), recorded into results.json.
7. Micro-bench (Task 1) recorded.
8. `render.py` writes §3; the runner never writes §4 — the decisions are written by hand against the pre-registered rules, quoting the numbers.
9. Cleanup: `rm -rf ~/workspace/bloomery/target/sensorium`; `git -C ~/workspace/bloomery status --porcelain` empty; `Cargo.lock` unchanged (hash recorded before and after).

**Invariants:** every cell in §3 is a number with its `n` and lens, or `not measured (<reason>)`; the E1 table shows all 15 raw walls; the decision text in §4 quotes the rule and the number and says PASS / KILL; §5 lists every gap the spike surfaced (expected at least: per-process exit status, buffered-spool loss on leaked threads, `source_hashes` empty, `output` not captured).

- [ ] Commit: `docs(spike): results, decisions, and rung-2 gaps for the Rust mechanics spike`.

---

### Task 6: Land the evidence, park the code

**Files:**
- Modify (on a short branch from main, cherry-picked from the spike branch): `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`, `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.results.json`, `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` (§8 table gains a "measured (rung 1)" column with the five numbers; §11 rung 1 marked DONE with the two decisions; §2/§4 amended only where a measurement falsified a sentence — dated, non-silent)

- [ ] Push `spike/rust-mechanics` (never merged; the README says so). Open a PR `docs/rung1-spike-findings` → `main` carrying only the three files above. CI stays Python-only; nothing under `rust/` is built by CI.

---

## Self-review

**Spec coverage:** §11 rung 1 names E0/E1/E7/E8 and the two decisions — Tasks 0 and 5 pre-register and measure them; E2's fn-item floor is measurable at the call tier and is added; §2.1–2.5, §3.2, §4 mechanics are exercised by Tasks 1–3 at the call tier only, as §11 specifies; §5 meta is produced by Task 4 so the real reader is the instrument.

**Rigor:** thresholds carry their derivation or are marked CHOSEN with a sanity check; the point estimate decides; infrastructure kills are recorded separately; none-versus-zero is in the results schema; every test is mutation-checked; the bloomery tree is read-only and its pin recorded; the spike code is labelled throwaway and never merged.

**Placeholder scan:** none. Verbatim text appears only for the spool record, the proc header, the manifest, the env variables and the CLI — the wire formats a fresh implementer would otherwise guess.
