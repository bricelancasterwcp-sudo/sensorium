# Rung 2 — Rust recorder v1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first product Rust recorder — `sensorium-rt`, `sensorium-transform`, `cargo-sensorium` — so that `runs`, `info`, `tree`, `frame`, `grep` and `diff` (including `--ignore-moves`) answer on real bloomery traces with the same honesty contract the Python recorder carries, and prove it against pre-registered acceptance endpoints E2′, E3, E5, E7 and E8 on a writable clone of bloomery.

**Architecture:** A cargo workspace under `rust/` (three crates) written fresh against the amended spec, taking the parked spike (`origin/spike/rust-mechanics`, `rust/spike/`) as the proven starting shape for the wrapper, mirror, module walk and manifest. The runtime has zero dependencies and is compiled by the driver with a bare `rustc` invocation, so there is no rlib-location or second-`libc` question. Spools are `MAP_SHARED` mappings with a kind-last write discipline. A cargo *runner* role gives every test binary a witnessed exit status. The converter is Rust (`rusqlite`, bundled) and writes trace format 4 exactly as `docs/TRACE-FORMAT.md` states it; the Python side gains lang-keyed vocabulary, the `unread` marker in `tree`/`frame`, a `dbg` value tag, refusals for the commands rung 2 does not yet answer on Rust, seven new conformance vectors, and a cross-recorder test that converts hand-built spools and drives the real CLI.

**Tech Stack:** stable rustc/cargo 1.96.0 (pinned; no nightly); `syn` 2 (full, visit, extra-traits), `proc-macro2` (span-locations), `serde`/`serde_json` for the transformer and driver; `rusqlite` (bundled), `blake2`, `libc` for the driver only; the runtime uses `extern "C"` declarations and no crate; Python 3.12–3.14 for the reader; sensorium 0.5.0 → 0.6.0.

**Spec:** `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` — §2 (mechanics, as amended by rung 1), §3.1–3.2, §3.5–3.7 (transformer at this tier), §4 (runtime), §5 (format 4), §6 (query-layer changes), §7 (honesty ledger), §8 (endpoints), §9 (testing story), §10 (rung-2 acceptance), §11 rung 2 (the inbox: findings §5). **Findings:** `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` §4 (decisions) and §5.1–29 (gaps) are binding constraints on every task below. **Contract:** `docs/TRACE-FORMAT.md`. **Rigor:** `~/.claude/skills/rigorous-experiments/SKILL.md`.

## Global Constraints

- **`/home/brice/workspace/bloomery` is read-only, forever, for this plan.** Nothing under it is edited, built into, or measured on. The measurement target is a LOCAL CLONE at `/mnt/extra/sensorium-rung2/bloomery` pinned at `e209ed9` (Task 0); the clone is the only bloomery tree any task may write to, and E5's split and E8(b)'s edit happen there on throwaway branches.
- **The second disk carries every artifact set.** `/mnt/extra` (469 GB ext4, ≈114 GB free on 2026-09-02; the root disk is chronically near-full). Every task exports `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target` for the `rust/` workspace, `/mnt/extra/sensorium-rung2/bloomery-target` for the clone, `/mnt/extra/sensorium-rung2/corpus-target` for `corpus/rust`, and `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir` for every trace a task records. **No box path is ever committed**: no `.cargo/config.toml` under the repo names `/mnt/extra`; the env vars live in the ledger and the task briefs. Preflight (Task 0 and again before Task 11) refuses under 8 GB free on `/mnt/extra` **and** 3 GB free on `/`.
- **The spike is a shape, not a source.** `rust/spike/` (branch `spike/rust-mechanics`) is never cherry-picked; an implementer may read it and re-author. Every file that lands under `rust/` is product: `version = "0.1.0"`, no "throwaway" wording, `publish = false`.
- **Pre-registration is committed before any code** (Task 0). After a number is read, no threshold moves, no arm is added, no run is re-rolled; an infrastructure kill may be re-run from zero with the reason recorded.
- **Legacy Python CLI output is byte-identical** on every pre-existing test and fixture; the existing suite (807 passed 1 skipped on 3.12/3.13/3.14, corpus 20/39/0) is the regression fence for every Python task.
- **Dependency policy:** `sensorium-rt` — none (FFI via `extern "C"`); `sensorium-transform` — `syn`, `proc-macro2`, `serde`, `serde_json`; `cargo-sensorium` — those plus `rusqlite` (`bundled`), `blake2`, `libc`. No `cargo_metadata`, no `sha2` (the spike's 90-line SHA-256 with NIST vectors is re-authored), no Python runtime dependency added.
- No file over 800 lines, Rust or Python. Functions under 50 lines where the language allows.
- Every test is mutation-checked before it counts (break the pinned line, watch it fail, restore); Python mutation runs purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`.
- Commits: conventional prefixes; trailer lines per the session's git rules.
- Cargo freshness must survive the wrapper, so the wrapper never writes under a workspace except `<target>/`; `git status --porcelain` of the clone is empty before and after every task that touches it, except on E5's and E8(b)'s named branches.

---

## Decisions this plan makes (each amends the spec non-silently in Task 12)

The handoff listed six open rung-2 design questions; the findings' §5 listed the gaps. Decided here, with the cost if wrong:

| # | Question | Decision | Why | Cost if wrong |
|---|---|---|---|---|
| D1 | Where the runtime rlib lives (spec §2.3; findings §5.24) | **`sensorium-rt` has zero dependencies and is compiled by the driver with one bare `rustc` invocation** (`--crate-type rlib --edition 2021 -C opt-level=3 -C panic=<strategy>`) into `<target>/sensorium/rt/<tool-hash>/<panic>/libsensorium_rt.rlib`; the wrapper adds `--extern sensorium_rt=<rlib>` **and `-L dependency=<the rlib's own directory, i.e. <rt dir>/<panic variant>>`** — amended a second time after the pre-acceptance smoke on the bloomery clone (2026-09-03): a unit that depends on an INSTRUMENTED crate must resolve that crate's transitive `sensorium_rt`, and rustc resolves transitive crates by search path, not by `--extern` (measured: `--extern` alone → `E0463: can't find crate for sensorium_rt which bloomery_substrate depends on`; `-L dependency=<rt dir>` alone succeeds). The probe workspace passed by resolver-order luck (its crate-root static was resolved before its `probe_core` uses); bloomery's top-of-module `use bloomery_core::…` was not. **Amended after Task 7 measured it: `RUSTDOCFLAGS` must carry `--extern sensorium_rt=<rlib>` AND `-L dependency=<rt dir>`** — rustdoc resolves a doctest's TRANSITIVE crates (`sensorium_rt` reached through an instrumented rlib) by search path, and without the `-L` every doctest fails `E0463`; the rt dir holds exactly one rlib and no dependency, so the single-candidate hazard of rung 1 cannot recur. The runtime's source is embedded in the driver binary (`include_str!`), so its version is the driver's version. | Removes the single-candidate `liblibc` hazard and the two-`libc` graph outright; the runtime needs `gettid`, `getpid`, `getppid`, `clock_gettime`, `mmap`, `munmap`, `ftruncate`, `close` — eight `extern "C"` lines. | A unit built with `-C lto` or a non-host `--target` cannot link a plain rlib; the wrapper detects both in argv and falls back for that unit with a manifest reason (`lto`, `cross-target`). Bloomery uses neither. |
| D2 | The mirror lock (findings §5.12) | **One `flock(LOCK_EX)` per unit** on `<target>/sensorium/mirror/<metadata>.lock`, released by the kernel on process death. No timeout, no staleness rule, no shared lock. | Per-unit mirrors have no shared mutable state; the only contention is two cargos building the same unit concurrently, which `flock` serialises correctly. | None known; `flock` is POSIX on Linux, and v1 is Linux-only (§4 `gettid`). |
| D3 | `#[cfg_attr(.., path = ..)]` (findings §5.26) | **Deferred**, still `unreached_files`, declared. | 0 cases in bloomery; the wrapper reads `--cfg` from argv but evaluating predicates is a rung-3+ nicety. | A workspace using it gets one declared-unreached file per site; `info` names it. |
| D4 | Per-process exit status (findings §5.1) | **A cargo runner role.** The driver sets `CARGO_TARGET_<HOST>_RUNNER=<shim> --runner`; cargo then invokes the shim to run every test binary. The runner spawns the binary with stdio inherited, waits, writes `<spool>/<pid>.runner.json` (`exit_status` or `signal`, wall start/end, argv) and exits with the same status (`128+signal` on a signal). **Measured 2026-09-02 on cargo 1.96 (scratch probe): the runner is invoked for every test binary AND for every doctest process (`/tmp/rustdoctest*/rust_out` was handed to it), so doctests are runner-waited too.** Processes the runner did not start (children a test spawns) carry `exit_status: null` with `exit_status_basis: "unwitnessed"`; runner-waited ones carry the real status with basis `"waited"`. The reader prints `exit: unwitnessed` for a null. | The runtime cannot observe exit; the parent can. Cargo already has the hook. | A user with their own runner in `.cargo/config.toml` is chained through `SENSORIUM_INNER_RUNNER` only when set in the env; a config-file runner is a declared v1 limitation (bloomery has none — `~/.cargo/config.toml` and the clone's are absent). |
| D5 | Converter language | **Rust, in `cargo-sensorium`**, `rusqlite` bundled, writing `db.SCHEMA` verbatim; the driver runs it after cargo exits. | Spec §2's table; the spike's Python converter took 22.7 s for one invocation and needed the Python package on PATH to record at all. | A drift between the Rust writer and `docs/TRACE-FORMAT.md` is exactly what Task 9's cross-recorder test exists to catch. |
| D6 | Async model (spec §3.2 amended) | **Still skipped, still declared** (`reason: "async"`). | 0 `async fn` in bloomery; a frame model for futures is a design of its own. | A workspace with async fns gets `skipped` entries `info` prints; no frame is faked. |
| D7 | Child processes (findings §5.7) | **N traces with a join key.** `capabilities.children = false` (the recorder hooks no spawn) **plus** the Rust-only key `child_runs: [{run_id, pid, exe}]` derived from `ppid` within one invocation. `info` prints both the declaration and the `child runs:` line. | "A child run id or the declaration that spawns are not witnessed — never neither" satisfies F23 without rewriting `Command`. | A child that ran no instrumented code leaves no trace and is not listed; the declaration line says so. |
| D8 | Per-unit site identity (findings §5.8, §5.27) | **Resolved at conversion**: `code_objects` is interned on `(file, qualname, firstlineno)`, so the 13 `tests/common` files compiled into 69 units collapse to one code object each, and the `main.rs` `run` twins stay two code objects. `HONESTY.md` names the `diff`-stream consequence (`(file, qualname, kind)` cannot tell the twins apart). | The schema already has the line; nothing new to store. | None for E3/E5; a future "compare traces of different binaries" feature inherits the manifest join. |
| D9 | Fingerprint file basis | **Workspace-relative path** (the manifest key), as spec §5.4 says and the Python recorder does; `code_objects.file` is absolute. `diff --ignore-moves` re-hashes over the absolute file on both sides, which is the same string on both sides of E5. | Relocation-insensitive stored hashes. | Two clones at different paths never plain-`diff` equal on thread streams — same as Python today. |
| D10 | Return values at tier `call` | **Captured at tier `call`** (the default) via the exit-operand form below, `Debug` through a *capping writer* that aborts formatting after the cap. **Measured (Task 2): the cap bounds the FORMATTING work, not the walk** — std's `debug_list`/`debug_map` still iterate every element after the writer errors (10⁶-element `Vec`: ≈10 ms capped vs ≈8 ms uncapped), while a `Debug` impl that propagates the error stops at the cap (10⁷ items: 1.5 µs vs 99 ms). Capture cost is therefore linear in a returned std collection's length and O(cap) otherwise; Task 11 reports it under that lens. The added wall on bloomery's `--lib` is REPORTED (Task 11), not gated — E1 was decided in rung 1 and stands. | Ruling 2 of spec §12 ("carry them"); a separate tier would be a lever nobody asked for. | If the reported wall exceeds ×1.5, that is a finding for the spec's E1 row and Task 12 states it; nothing in this rung re-decides tiering. |

The exit-operand form (spec §3.2's `match` wrap is **replaced**; the `match (<e>)` shape trips `unused_parens`, and under `#![deny(warnings)]` a whole unit would fall back):

```rust
// tail expression <e> of a non-unit fn, and every `return <e>` at closure depth 0, become:
::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, SITE, |__r| { use ::sensorium_rt::probe::*; ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome()) }, <e>)
```

**Verified 2026-09-02 on rustc 1.96 under `#![deny(warnings)]` (scratch probe, 14 shapes: struct-literal tail, `Box<dyn Trait>` tail, `&String -> &str` deref coercion, `?` tail, `Err` tail, `!Debug` return, early `return` inside `if`, `format!` tail, a generic `T: Clone` return, `Option` tail, a `Drop`-logging guard held across the tail, a `MutexGuard` in the tail, `Result` outcomes) — zero diagnostics, drop order and lock release unchanged, outcomes `Ok`/`Err` correct.** The probe traits take `&self`; the specialised impls (`T: Debug`, `Result<T, E>`) are on `&Probe<'_, T>` and the fallbacks on `Probe<'_, T>` by value, and the call site is `(&&Probe(__r))` — the autoref order of dtolnay's case study; with `self` by value or impls on `&&Probe` the fallback wins every time (measured: the specialised trait was reported dead). The closure comes BEFORE the operand, so a diverging operand leaves nothing unreachable after it; the operand is an argument, which is a coercion site, so `Box<dyn T>` and `&String -> &str` tails still coerce; temporaries of `<e>` live exactly as long as they did as a tail. `ret<T>(unit, site, cap: impl FnOnce(&T) -> (Capture, Outcome), v: T) -> T` calls `cap` only when the recorder is live. Operands the transformer does **not** wrap, because they are syntactically diverging (`outcome = none`, as spec §3.2 already says for `-> !`): `return`/`break`/`continue` expressions, a `loop` without a valued `break`, calls of `panic!`, `unreachable!`, `todo!`, `unimplemented!`, `std::process::exit`, `std::process::abort` (path suffix match), **and — amended after Task 4's oracle measured `unreachable_code` — any composite whose every arm diverges by these rules recursively (an `if`/`else`, `match`, or block whose tail/arms all diverge)**. A bare block tail `{ e }` with no statements is wrapped by wrapping `e` INSIDE the braces (a wrapped outer block fires `unused_braces`). Both shapes measured 0 occurrences over the clone's 1022 value-returning fn items; the rules exist so a workspace that has them never falls back.

---

## Pre-registration (Task 0 commits this section verbatim as `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` §1 before any code exists)

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

## File structure

```
rust/
├── Cargo.toml                    workspace: sensorium-rt, sensorium-transform, cargo-sensorium; exclude = ["probes"]
├── README.md                     how to build, install (`cargo install --path rust/cargo-sensorium`), record, and what v1 does not do
├── HONESTY.md                    the Rust honesty ledger (spec §7) — written in Task 1, before the transformer
├── sensorium-rt/                 zero-dependency runtime
│   └── src/{lib.rs, ffi.rs, spool.rs, thread.rs, probe.rs, panic.rs, tasks.rs}
├── sensorium-transform/          syn rewriter, pure
│   └── src/{lib.rs, splice.rs, exits.rs, spawn.rs, manifest.rs}   tests/golden/*.in.rs|*.out.rs, tests/{golden.rs, oracle.rs, census.rs}
├── cargo-sensorium/              one binary, four roles: driver, wrapper, runner, convert
│   └── src/{main.rs, args.rs, driver.rs, rt_build.rs, rt_src.rs, wrapper.rs, mirror.rs, modtree.rs, runner.rs, sha256.rs,
│            convert/{mod.rs, spool.rs, merge.rs, frames.rs, meta.rs, sqlite.rs, fingerprint.rs, runid.rs}}
├── probes/ws/                    the probe workspace (own Cargo.lock, committed)
└── tests/mechanics.sh            E7(a), E8 on the probe, runner, doctest, spawn naming, panic, abort, durability, cross-filesystem target
corpus/rust/                      a cargo workspace of corpus cases (own Cargo.lock); run by corpus/run_corpus.py with `program: cargo`
src/sensorium/query/vocab.py      lang-keyed vocabulary
docs/trace-format/vectors/v08..v14 seven new vectors
tests/test_rust_convert.py        cross-recorder conformance: spool fixtures → cargo-sensorium convert → the real CLI
tests/fixtures/rust-spools/<case>/ hand-built spool dirs + questions.json
docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md   §1 pre-registration, §2 pins, §3 results, §4 decisions, §5 gaps
```

---

### Task 0: Branch, pre-registration, the clone, preflight

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` — §1 Pre-registration (the section above, verbatim), §2 Ambient pins (filled), §3 Results (every cell `not measured (rung 2 pending)`), §4 Decisions (empty), §5 Gaps found (empty)
- Commit this plan file.

**Invariants:**
- The pre-registration commit precedes every other commit on the branch (`git log --format=%s -- docs/superpowers/acceptance/` proves it).
- §2 records: `rustc -V`, `cargo -V`, `rustup toolchain list` (stable only), `nproc`, governor, `RUSTFLAGS`/`CARGO_INCREMENTAL`/`RUSTC_WRAPPER`/`RUSTDOCFLAGS` unset, `df -h /` and `df -h /mnt/extra`, the clone's `HEAD` = `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` and `status --porcelain` empty, `~/workspace/bloomery` `status --porcelain` empty and `HEAD` unchanged, the absence of `~/.cargo/config.toml` and of `<clone>/.cargo/config.toml`, and the sha256 of the clone's `Cargo.lock`.
- The clone is `git clone /home/brice/workspace/bloomery /mnt/extra/sensorium-rung2/bloomery && git -C … checkout e209ed9` (local, no network); its `origin` is the local tree, so nothing can be pushed anywhere by accident.
- Preflight refuses under 8 GB free on `/mnt/extra` or 3 GB on `/`; refuses if 1-minute load > 4.0.

- [ ] **Step 1:** `git checkout -b feat/rung2-recorder-v1 main` (main @ `02bc620` or later).
- [ ] **Step 2:** `mkdir -p /mnt/extra/sensorium-rung2/{rust-target,bloomery-target,corpus-target,sensorium-dir}`; make the clone; run the preflight; write §2.
- [ ] **Step 3:** Commit: `docs(rung2): pre-register E2', E3, E5, E7, E8 before any recorder code exists`.

---

### Task 1: `rust/HONESTY.md`, `rust/README.md`, the workspace skeleton

**Files:**
- Create: `rust/HONESTY.md`, `rust/README.md`, `rust/Cargo.toml` (members declared; crate directories created in later tasks, so `members` lists only what exists at each commit — the same ruling rung 1 used), `rust/.gitignore` (`target/`)

**Interfaces:**
- `HONESTY.md` is structured as spec §7 says: one section per promise, each with **the corpus case or test that could falsify it** named by path (cases land in Task 10; the names are fixed here and Task 10 must use them). Sections, at minimum:
  1. *What a frame's outcome means* — `ok`/`err` from the probe on the returned value at the exit operand; `panic` from the hook; `none` for `?`-bypass, diverging operands, `-> !`; a generic `T` that is a `Result` only after monomorphisation reads `ok` (falsified by `corpus/rust/outcome_generic` — a rung-3 case, named now).
  2. *What a return value is* — `Debug` text capped at 200 bytes by a writer that aborts formatting; `!Debug` reads `<unread>`; never `()` for an unread.
  3. *Threads, tasks and names* — every non-main thread that emits is a task; libtest names test threads; `spawn_child` names workspace-spawned ones `<parent task> :: spawn@<file>:<line>` (or `spawn@<file>:<line>` from the main thread); dependency-spawned threads are unnamed and compared as an unnamed multiset (falsified by `corpus/rust/spawned_thread`).
  4. *What a spool loses* — a record being written at the instant of SIGKILL/abort is lost uncounted, at most one per thread, visible as a `seq_gaps` count; `records_dropped` counts what the runtime knew it could not write (falsified by `corpus/rust/abort` and `sensorium-rt/tests/durability.rs`).
  5. *Exit status* — `waited` only for processes the runner started (every test binary and, on cargo 1.96, every doctest process); `unwitnessed` for anything a test spawned itself; never borrowed from cargo.
  6. *Children* — instrumented children are linked by `ppid`; spawns are not witnessed; a child that ran no instrumented code is invisible.
  7. *Site identity* — per-unit at record time, merged on `(file, qualname, firstlineno)` at conversion; cfg-gated twins are two code objects that `diff` cannot tell apart.
  8. *Cannot see* — dependency internals; `?` (rung 3); locals and LINE (rung 4); output under libtest; `async fn` (declared skip); `const`/`extern` fns; a unit that fell back (declared, with reason: rustc rejection, `lto`, `cross-target`, absolute crate root); `#[cfg_attr(path)]` modules (unreached, declared); a `Debug` impl that panics (recorded `<unread>`, the panic swallowed inside the instrument); a user runner set in `.cargo/config.toml`.
  9. *Preserved by construction, tested* — line numbers and paths (E7), temporary lifetimes and drop order at every wrapped site (the oracle test), cargo freshness and plain builds untouched (E8), no new warnings under `-D warnings` (the oracle test), `Cargo.lock` untouched.
  10. *Cost is reported, never gated.*
- `README.md`: build (`CARGO_TARGET_DIR` note, no path), install, `cargo sensorium test|run [--tier off|call] <cargo args>`, what gets printed (`run:` lines, the multi-binary WARN), where traces go, and the "not yet" list (`?`, locals, `watch`/`flow`/`exceptions`/`refocus` on Rust traces refuse in this version).

**Invariants:** every promise names its falsifier; every "cannot see" is also in the transformer's or converter's declared output (a manifest field, a meta key, or an `info` line) — the ledger claims nothing the trace does not carry.

- [ ] Write both documents and the skeleton; commit: `docs(rust): the honesty ledger before the transformer, and the workspace skeleton`.

---

### Task 2: `sensorium-rt` — spools, the guard, outcomes and return values

**Files:**
- Create: `rust/sensorium-rt/{Cargo.toml, src/lib.rs, src/ffi.rs, src/spool.rs, src/thread.rs, src/probe.rs}`, `rust/sensorium-rt/tests/{common/mod.rs, wire.rs, inert.rs, outcomes.rs, values.rs, durability.rs, serials.rs, units.rs}`, `rust/sensorium-rt/src/bin/scenario.rs` (the subject process the integration tests drive)

**Interfaces (exact — the transformer and the converter are written against these):**
- `pub struct Unit`; `pub const fn new(metadata: &'static str) -> Unit`; each instrumented crate root gets `#[doc(hidden)] pub static __SENSORIUM_UNIT: ::sensorium_rt::Unit = ::sensorium_rt::Unit::new("<-C metadata>");`. Lazy registration on first `enter`; ids `0..=254`; the 256th distinct unit makes the runtime refuse (one stderr line, every later `enter` inert).
- `#[must_use] pub struct Guard`; `#[inline] pub fn enter(unit: &'static Unit, site: u32) -> Guard`. The guard's `Drop` is the sole RETURN emitter: outcome `panic` when `std::thread::panicking()`, else the stashed outcome, else `none`; the stashed value rides with it. A guard that recorded its CALL always records its RETURN.
- `pub fn ret<T>(unit: &'static Unit, site: u32, cap: impl FnOnce(&T) -> (Capture, Outcome), v: T) -> T` — stashes `(packed site, cap(&v))` in a thread-local slot and returns `v`; calls `cap` only when the recorder is live on this thread. The guard consumes the slot only if the packed site matches its own; a mismatched slot is discarded (a `return` inside an unwrapped nested construct cannot poison an outer frame).
- `pub mod probe`: `pub struct Probe<'a, T: ?Sized>(pub &'a T)`; traits `DebugCap` (`impl<T: Debug + ?Sized> DebugCap for &Probe<'_, T>`) and `NoDebugCap` (`impl<T: ?Sized> NoDebugCap for Probe<'_, T>`) both providing `fn debug_cap(&self) -> Capture`; traits `ResultOutcome` (`impl<T, E> ResultOutcome for &Probe<'_, Result<T, E>>`) and `AnyOutcome` (`impl<T: ?Sized> AnyOutcome for Probe<'_, T>`) both providing `fn outcome(&self) -> Outcome`. All four methods take `&self`; the specialised impls are on the reference type and the fallbacks on the value type, so `(&&Probe(x)).debug_cap()` resolves to the specialised impl when `T: Debug` and to the fallback otherwise (verified — see *Decisions*). A test pins both arms: `(&&Probe(&3u8)).debug_cap().text == Some("3")` and `(&&Probe(&NoDbg)).debug_cap().text == None`. `pub struct Capture { pub text: Option<String>, pub truncated: bool }` (`None` = unread); `pub enum Outcome { None = 0, Ok = 1, Err = 2, Panic = 3 }`.
- Capture caps: `Debug` formatted through a `fmt::Write` that counts bytes and returns `Err` after **200 bytes**, so formatting a million-element `Vec` costs O(200); the truncated flag is set; the thread's `truncated` header counter is incremented. A `Debug` that panics is caught (`catch_unwind(AssertUnwindSafe)`) and reads `Capture { text: None, .. }`; the panic hook (Task 3) stays silent for it.
- Tier: `SENSORIUM_TIER` ∈ `off` | `call` (absent/empty = `call`; anything else refused with one stderr line, inert). `SENSORIUM_SPOOL` unset or empty = inert. Read once per process.
- Thread serials: process-global `AtomicU32` from 2; the thread whose `gettid() == getpid()` is serial 1 whether or not it emits. Global sequence: `AtomicU64`, one `fetch_add(Relaxed)` per record. Timestamps: `CLOCK_MONOTONIC` ns.
- Reentrancy: thread-local depth with a drop-guard; `enter` returns an inert guard while depth > 0.

**Wire format v2 (verbatim — a converter is written against it; nothing here may drift):**

```
spool file:   <SENSORIUM_SPOOL>/<pid>.<thread_serial>.spool   -- one per emitting thread, MAP_SHARED
file header:  b"SNSR" u8 version=2 u8 flags=0 u16 name_len u32 thread_serial u64 records_dropped u64 truncated  name_bytes
              (fixed 28 bytes, then name_bytes; records start at 28 + name_len; records_dropped and truncated are
               rewritten IN PLACE through the mapping and are final only once THREAD_END is present)
record:       u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 payload_len  [payload_len bytes]
kind:         0 = UNWRITTEN (the mapped tail; the reader STOPS at the first kind 0), 1 = CALL, 2 = RETURN,
              3 = PANIC, 255 = THREAD_END
outcome:      RETURN only: 0 none, 1 ok, 2 err, 3 panic; 0 on every other kind
site:         unit_id in bits 31..24, site index in bits 23..0; 0 on PANIC and THREAD_END (no site applies)
RETURN payload:  u8 tag (0 = no value, 1 = debug text follows, 2 = unread) u8 truncated(0|1) then UTF-8 text
PANIC payload:   u16 loc_len, loc UTF-8 ("<file>:<line>:<col>" as the hook saw it), then the message UTF-8 (rest)
write order:  every field of a record except `kind` first, then `kind` with a Release store -- a record is
              complete iff kind != 0; a reader that meets kind 0 has reached the end of what was written
growth:       the file is ftruncate'd and mapped in 64 KiB chunks; a failed ftruncate/mmap sets the thread
              inert and counts every later record in records_dropped; THREAD_END is written by the
              thread-local destructor, which then ftruncates the file to its written length
proc header:  <SENSORIUM_SPOOL>/<pid>.proc.json  written at the process's first event and rewritten at each
              unit registration: {"pid":int,"ppid":int,"exe":str,"argv":[str],"cwd":str,"start_ns":int,
              "start_realtime_ns":int,"env":{str:str},"env_hash":"<sha256 hex, first 16>","units":{"<unit_id>":"<metadata>"},
              "refused":{"at":"<metadata>"}|null,"rt_version":"sensorium-rt 0.1.0"}
              (`refused` is null until the 256th distinct unit registers; then the header is rewritten with that unit's metadata)
              env_hash = sha256 over "\n".join(f"{k}={v}" for sorted env items), first 16 hex chars. NOT the
              Python recorder's formula (boot.py hashes json.dumps(env, sort_keys=True)); env_hash is compared only
              within one language and TRACE-FORMAT.md says so (ruling, Task 2 concern 1).
```

**Invariants, each with its test (mutation-checked):**
- `wire.rs`: header and record bytes exactly as above, parsed by a test-side parser written from this block, not from `spool.rs`.
- `inert.rs`: with `SENSORIUM_SPOOL` unset the subject creates no file and no directory anywhere; with `SENSORIUM_TIER=off` the same; a bad tier prints one line and creates nothing.
- `outcomes.rs`: a fn returning `Ok(3)` → RETURN outcome 1 with text `Ok(3)`; `Err("x")` → 2; a `?`-bypass → 0 with tag 0; a panic → 3; a `()`-returning fn (the transformer emits no `ret` for it) → **wire outcome 0, tag 0** — the runtime knows nothing per site; the converter turns a `ret: unit` site's `none` into `ok` with value `()` (Task 6), because a `-> ()` fn cannot contain `?` (ruling, Task 1 concern 2).
- `values.rs`: a `!Debug` return reads tag 2; a 10⁶-element `Vec<u8>` return produces ≤ 200 text bytes with truncated = 1 (the text is capped; the walk is std's and stays linear — amended after Task 2 measured it) and a `Debug` impl that propagates the writer's error stops at the cap (pinned against an uncapped format of the same value); a `Debug` impl that panics reads tag 2 and the process continues; the thread header's `truncated` counter equals the number of truncated captures.
- `durability.rs` (the `MAP_SHARED` claim, read off the bytes): a thread blocked in `recv()` with N complete records when the process (a) returns from `main`, (b) calls `process::exit(0)`, (c) calls `abort()`, (d) is SIGKILLed — in every row the blocked thread's spool holds all N records complete, followed by kind-0 tail; only `THREAD_END` is absent. A synthetic disk-full (`SENSORIUM_TEST_SPOOL_LIMIT=<bytes>` honoured by the runtime under `cfg(feature = "test-hooks")` only) makes the thread inert and `records_dropped` equals the count of `enter`s after the limit.
- `serials.rs`: main is 1 even when a spawned thread emits first; two threads' seqs interleave strictly increasing; recycled OS thread ids get fresh serials.
- `units.rs`: two units in one process get ids 0 and 1 and the proc header maps both; the 256th refuses.
- The hot inert path is one acquire load, one compare, and the guard value (a test disassembles nothing; the invariant is the `enter` body's shape, reviewed).

- [ ] Write the tests first (RED), the runtime, mutation-check, commit: `feat(rt): sensorium-rt 0.1.0 -- MAP_SHARED spools (wire v2), outcomes, capped return values`.

---

### Task 3: `sensorium-rt` — the panic hook, `spawn_child`, tasks

**Files:**
- Create: `rust/sensorium-rt/src/{panic.rs, tasks.rs}`; tests `rust/sensorium-rt/tests/{panics.rs, spawn.rs}`; extend `scenario.rs`

**Interfaces (exact):**
- `pub fn spawn_child<F, T>(site: &'static str, f: F) -> std::thread::JoinHandle<T> where F: FnOnce() -> T + Send + 'static, T: Send + 'static` — reads the current thread's task name (the thread-local override if set, else `std::thread::current().name()`, else none), then `std::thread::spawn(move || { set_task_name(<derived>); f() })` where `<derived>` = `"<parent task name> :: spawn@<site>"` when the parent has a TASK name — the override, or the OS thread name of a NON-main thread — and `"spawn@<site>"` otherwise. The main thread is not a task even though std names it `"main"`, so a child of main is `"spawn@<site>"` (ruling, Task 3 concern 1). The JoinHandle, panic propagation and the child's OS thread name are unchanged.
- The spool header's `name` is the task name: the override when set, else the OS thread name, else empty.
- Panic hook: installed once, on the process's first RECORDING `enter` (not inside `init`: `std::panic::set_hook` panics when called from a panicking thread, and a first `enter` reached from a `Drop` during an unwind would double-panic and abort; installing only when recording also leaves the inert path untouched — amended after Task 3's review), via `std::panic::take_hook`/`set_hook`; ours writes one PANIC record (message from `payload().downcast_ref::<&str>()` / `<String>`, else `"<non-string payload>"`; location from `PanicHookInfo::location()`), then calls the previous hook so every byte of output is unchanged. While the thread is inside the runtime (depth > 0) the hook records nothing and does not chain (a `Debug` impl that panics inside the instrument is silent).
- The panic serial is per thread, minted at each PANIC record; the converter attaches the most recent PANIC on the thread to every frame that then closes `panic`.

**Invariants, each with its test:**
- `panics.rs`: a test that panics inside a frame produces PANIC (with location `<file>:<line>:<col>` matching `file!()`/`line!()` of the `panic!`) then RETURN outcome 3; a `catch_unwind` in an instrumented outer fn produces PANIC, inner RETURN 3, outer RETURN 1 (ok); the process's stderr is byte-identical with and without the runtime installed (the chained hook).
- `spawn.rs`: a child spawned from a named test thread has the derived name in its spool header; a grandchild has both `::` segments; a child spawned from main has `spawn@…` alone; a dependency-style `std::thread::spawn` (not rewritten) has the OS name or empty; the JoinHandle returns the closure's value and re-raises its panic exactly as `std::thread::spawn` does.

- [ ] Tests first, implement, mutation-check, commit: `feat(rt): chained panic hook, spawn_child task naming`.

---

### Task 4: `sensorium-transform` — entry guards, exit operands, spawn sites, the manifest

**Files:**
- Create: `rust/sensorium-transform/{Cargo.toml, src/lib.rs, src/splice.rs, src/exits.rs, src/spawn.rs, src/manifest.rs}`, `tests/golden/*.in.rs|*.out.rs`, `tests/{golden.rs, oracle.rs, census.rs}`, `tests/oracle-crate/` (a tiny crate the oracle compiles)

**Interfaces (exact):**
- `pub fn transform(source: &str, file: &str, unit_metadata: &str, first_site: u32, is_crate_root: bool) -> Result<Transformed, syn::Error>`; `pub fn census(source: &str) -> Census` (the rung-1 shapes: `Transformed { source, sites, skipped, appended_line }`, `Site { site, file, qualname, firstlineno, ret }`, `Skipped { file, qualname, line, reason }`, `Census { fn_items, const_fns, extern_fns, async_fns, parsed }` with `eligible()`), plus:
  - `Site.ret: RetKind` ∈ `Unit` (no return type, or `-> ()`), `Value` (any other return type; the exits were wrapped), `Never` (`-> !`).
  - `Transformed.spawns: Vec<SpawnSite>`, `SpawnSite { file, line, wrapped: bool, reason: Option<&'static str> }` — `wrapped` for a call whose callee path ends in `thread::spawn` with ≥ 2 segments and exactly one argument; `reason` ∈ `"builder"`, `"scoped"`, `"method"`, `"arity"` (a path-call `…spawn(…)` with ≠ 1 argument) for the shapes left alone; a zero-argument METHOD `.spawn()` (`Command::spawn`) is not a thread spawn and is not listed.
- Injected fragments, newline-free, spliced at `Span::byte_range()` offsets exactly as the spike did (BOM/shebang prefix measured, every offset checked against the byte the grammar requires):
  - entry: `let _sens_guard = ::sensorium_rt::enter(&crate::__SENSORIUM_UNIT, <site>);` after the body's `{` (past inner attributes and inner doc comments);
  - exit (see *Decisions*): the tail expression and every `return <e>` at closure depth 0 of a `RetKind::Value` fn, excluding syntactically diverging operands, become `::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, <site>, |__r| { use ::sensorium_rt::probe::*; ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome()) }, <e>)` — two splices per operand (an open fragment before, `)` after);
  - spawn: `std::thread::spawn(<f>)` → `::sensorium_rt::spawn_child("<file>:<line>", <f>)` — the callee path replaced in place, one splice. **Amended after Task 4's oracle:** replacing a NON-`std`-rooted callee (`thread::spawn` under `use std::thread;`) orphans the import and fires `unused_imports` — a new diagnostic and a hard error under `deny(warnings)` — so for those the site argument is the block `{ #[allow(unused_imports)] use <callee path> as _; "<file>:<line>" }`, which keeps the import used; a `::std::thread::spawn`/`std::thread::spawn` callee takes the bare string;
  - crate root: the `__SENSORIUM_UNIT` static after the file's last token (the rung-1 doc-comment rules).
- Skip list, declared per fn: `const` (E0493/E0015), `extern` (ABI present), `async`, `macro` (fn tokens inside `macro_rules!`). Closures get no guard in this rung (spec §3.3's closure frames are rung 3); a `return` inside a closure or async block is at closure depth ≥ 1 and is never wrapped.
- Manifest (`manifest.rs`, serialise-only), verbatim:

```json
{"unit":"<metadata>","crate_name":str,"crate_type":str,
 "files":{"<workspace-relative path>":[{"site":u32,"qualname":str,"firstlineno":u32,"ret":"unit"|"value"|"never"}]},
 "skipped":[{"file":str,"qualname":str,"line":u32,"reason":"const"|"extern"|"async"|"macro"}],
 "spawns":[{"file":str,"line":u32,"wrapped":bool,"reason":str|null}],
 "source_hashes":{"<workspace-relative path>":"<sha256 hex of the ORIGINAL bytes>"},
 "fell_back":bool,"fallback_reason":str|null,"unreached_files":[str],"appended_line":{"<path>":bool}}
```
  (`source_hashes` and `fallback_reason` are filled by the wrapper, Task 5; the manifest type carries them.)

**Invariants, each with its test:**
- `golden.rs`: one `.in.rs`/`.out.rs` pair per rule — free fn, impl method, trait default, nested fn, nested mod, generic, unsafe, test fn, `const`/`extern`/`async` skips, `macro_rules!`, inner attrs, inner doc comments, body attrs, shebang+UTF-8, crate-root static placements (the rung-1 set) **plus**: unit fn (no wrap), value tail, `return <e>` inside `if`/`match`/loop bodies, a `return` inside a closure (not wrapped), a struct-literal tail (`Self { a: 1 }`), a `?` tail, a `format!` tail (wrapped), `panic!`/`todo!`/`process::exit` tails (not wrapped), `-> !` (no wrap, `ret: never`), a `loop` tail with `break value` (wrapped) and without (not), `std::thread::spawn` / `thread::spawn` (wrapped), `Builder::new().spawn` and `thread::scope` (unwrapped, reasons). Every golden asserts `lines(out) == lines(in) + appended_line`.
- `oracle.rs`: every golden's output is compiled by the real `rustc` (`--edition 2021 -D warnings --extern sensorium_rt=<rlib built by the test from ../sensorium-rt>`) and **compiles with zero diagnostics**; a `Drop`-order probe (a struct whose `Drop` appends to a log, held in a `let` and returned through a wrapped tail) logs the same order with and without the transform; a `MutexGuard` held across the wrapped tail is released at the same point (`try_lock` from another thread reads the same before/after). This is the test that pins "no new borrow errors, no drop-order change, no warnings".
- `census.rs`: `instrumented + async_fns == eligible` on the clone's 191 files (the clone path comes ONLY from the env var `SENSORIUM_BLOOMERY_CLONE` — no default, no box path in the source; skipped by name when unset — CI has no clone), 0 line moves, 0 re-parse failures; the count of `wrapped` spawn sites equals the count of literal `std::thread::spawn(` in the files (8 at `e209ed9`).

- [ ] Goldens and oracle first (RED), implement `splice.rs`/`exits.rs`/`spawn.rs`, mutation-check, commit: `feat(transform): sensorium-transform 0.1.0 -- entry guards, exit operands, spawn sites`.

---

### Task 5: `cargo-sensorium` — driver, wrapper, runner

**Files:**
- Create: `rust/cargo-sensorium/{Cargo.toml, build.rs, src/main.rs, src/args.rs, src/driver.rs, src/rt_build.rs, src/rt_src.rs, src/wrapper.rs, src/mirror.rs, src/modtree.rs, src/runner.rs, src/sha256.rs}`, tests `rust/cargo-sensorium/tests/{wrapper_fallback.rs, unit_identity.rs, runner.rs}`

**Interfaces (exact):**
- Roles, decided by `args::role`: **driver** (`cargo sensorium test|run [--tier off|call] <cargo args…>`; also `cargo-sensorium sensorium …` as cargo invokes it), **wrapper** (argv[1] is a rustc path — cargo's `RUSTC_WORKSPACE_WRAPPER` contract), **runner** (`cargo-sensorium --runner <binary> [args…]`), **convert** (`cargo-sensorium convert <spool dir>`, Task 6).
- Driver: `cargo locate-project --workspace` for the root; `CARGO_TARGET_DIR` honoured (default `<ws>/target`); host triple from `rustc -vV`; the runtime built by `rt_build` (D1) at `<target>/sensorium/rt/<tool-hash>/unwind/libsensorium_rt.rlib` (`abort` built lazily by the wrapper when a unit's argv carries `-C panic=abort`); `tool-hash` = sha256 of the driver binary + the embedded runtime source; shim at `<target>/sensorium/shim/<tool-hash>/cargo-sensorium` (a copy of the running binary); invocation id in sensorium's run-id shape, **local time** (`localtime_r`); spool dir `<target>/sensorium/spool/<invocation>/`; writes `<spool>/invocation.json` **before** cargo starts and completes it after:

```json
{"invocation":str,"subcommand":"test"|"run","cargo_args":[str],"tier":str,"toolchain":"<rustc -vV first line>","host":str,
 "profile":"dev"|"release","workspace_root":str,"target_dir":str,"tool_hash":str,"driver_version":"cargo-sensorium 0.1.0",
 "start_ts":float,"end_ts":float|null,"cargo_exit":int|null}
```
  then runs `cargo <subcommand> <args unchanged>` with env: `RUSTC_WORKSPACE_WRAPPER=<shim>`, `RUSTDOCFLAGS=<user's> --extern sensorium_rt=<rlib>`, `CARGO_TARGET_<HOST>_RUNNER=<shim> --runner` (chaining `SENSORIUM_INNER_RUNNER` if set), `SENSORIUM_SPOOL`, `SENSORIUM_TIER`, `SENSORIUM_TARGET`, `SENSORIUM_WS`, `SENSORIUM_RT_DIR`, `SENSORIUM_TOOL_HASH`, `SENSORIUM_INVOCATION`; after cargo exits it runs the converter (Task 6) on the spool dir, prints one `run: <id>  pid: <pid>  exe: <basename>  events: <n>  threads: <k>  exit: <status|unwitnessed>` line per trace, prints `WARN: this invocation produced N test binaries; a single-target selector (--lib, --test X, --bin X) makes one trace the answer` when N > 1, and exits with cargo's status.
- Wrapper: the rung-1 shape with these changes — per-unit mirror `<target>/sensorium/mirror/<metadata>/` under a per-unit `flock` (D2); `--remap-path-prefix=<mirror>=<ws>` appended (findings §5.21); only `--extern sensorium_rt=<rlib>` appended (no `-L`); the manifest's `source_hashes` filled from the bytes read; fallbacks (**every one writes or patches a manifest with `fell_back: true` and a `fallback_reason`** — findings §5.29): rustc rejects the rewrite (`"rustc: <first error line>"`), absolute crate root, `-C lto` present, `--target` present, wrapper error (`"wrapper: …"`). Passthrough (no manifest) exactly for: crate name `___` or `build_script_*`, `--crate-type proc-macro`, `-vV`, `--print`, stdin source. No bisect in v1: a rejected unit falls back whole (the spike measured 0 rejections on bloomery; bisection is a declared non-feature until a rejection is seen).
- Runner: spawns `<binary> [args…]` with stdio inherited and the environment untouched, waits, writes `<SENSORIUM_SPOOL>/<child pid>.runner.json` = `{"pid":int,"exit_status":int|null,"signal":int|null,"wall_start_ts":float,"wall_end_ts":float,"argv":[str]}`, exits with the child's code (`128+signal` on a signal). Without `SENSORIUM_SPOOL` it still runs the binary and writes nothing.

**Invariants, each with its test:**
- `runner.rs`: exit 0, exit 7, and SIGKILL each yield the matching JSON and the matching runner exit code; stdout/stderr pass through unchanged (a child that prints 1 MB is byte-identical through the runner).
- `wrapper_fallback.rs`: each fallback shape leaves a manifest with `fell_back: true` and the named reason, including the absolute-root and wrapper-error shapes (driven through the real binary with a fake rustc).
- `unit_identity.rs`: two units of one crate root get two mirrors with two different `__SENSORIUM_UNIT` statics; the check asserts `checked > 0` (findings §5.29).
- `rt_build`: building the runtime twice with the same hash is a no-op (mtime unchanged); a changed embedded source changes the hash and rebuilds; `abort` and `unwind` variants coexist.
- Unit tests for `args` (role detection, `--tier` before/after `--`, `test`/`run` only), `driver::runner_env_var("x86_64-unknown-linux-gnu") == "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER"`, `utc→local` run-id stamp against `date +%Y%m%d-%H%M%S`, `sha256` against the NIST vectors, `modtree` (the rung-1 set), `mirror` (the rung-1 set, plus: the lock is per unit and released on process death — a test that kills a holder and acquires).

- [ ] Tests first, implement, mutation-check, commit: `feat(driver): cargo-sensorium 0.1.0 -- driver, workspace wrapper, runner`.

---

### Task 6: `cargo-sensorium convert` — the Rust converter

**Files:**
- Create: `rust/cargo-sensorium/src/convert/{mod.rs, spool.rs, merge.rs, frames.rs, meta.rs, sqlite.rs, fingerprint.rs, runid.rs}`, tests `rust/cargo-sensorium/tests/convert.rs`, fixtures `rust/cargo-sensorium/tests/spools/<case>/`

**Interfaces (exact):**
- `cargo-sensorium convert <spool dir>` (the driver calls the same function in-process): reads `invocation.json`, every `<pid>.proc.json`, `<pid>.<serial>.spool`, `<pid>.runner.json`, and every manifest under `<target>/sensorium/manifests/`; writes one trace per pid to `$SENSORIUM_DIR/traces/<run-id>.db` (default `~/.sensorium/traces`; run id minted per trace in the run-id shape, local time, a fresh 6-hex suffix); prints the `run:` lines. Any spool, header or manifest it cannot read honestly is a hard error naming the file (an orphan spool, a mirror path in a manifest, a missing manifests dir, a `seq` that goes backwards).
- Schema: `db.SCHEMA` **verbatim** from `src/sensorium/store/db.py` (the four `CREATE INDEX` lines included), `PRAGMA journal_mode=WAL`, `meta.value` always JSON (`serde_json` compact), `trace_format` = 4 written first, `incomplete = true` written before any row and `false` **last**.
- Mapping (the spike's proven mapping, extended):
  - k-way merge by `seq`, strictly increasing; a missing seq is a gap → `seq_gaps` counted;
  - CALL → `events` row (`frame_id` NULL, `code_id` interned on `(abs file, qualname, firstlineno)`, `line = firstlineno`, payload `{"args":{},"unread":["locals"]}`, `task_id` = thread serial for non-main threads, NULL for main) + `frames` row (`parent` = innermost open frame on the thread, `depth`, `kind = "function"`);
  - RETURN → `events` row (`frame_id` = the frame, `line` NULL, payload `{"outcome": "ok"|"err"|"panic"|"none"}` plus `"value": {"k":"dbg","v":<text>,"trunc":bool}` when tag 1, `{"k":"unread"}` when tag 2, and, for a `ret: unit` site whose wire outcome is `none` (0), outcome `ok` with value `{"k":"dbg","v":"()"}` — the wire carries no per-site knowledge, the manifest does, and a `-> ()` fn cannot contain `?`; a `ret: unit` site with wire outcome `panic` stays `panic`); `close_frame` with `closed_by = "return"`, or `"unwind"` + `unwind_exc = {"type":"panic","msg":<hook msg>,"serial":<panic serial>,"loc":<loc>}` when outcome 3;
  - PANIC → a RAISE `events` row on the innermost open frame (`line` from the location when its file is the frame's file, else NULL; payload `{"exc": {"type":"panic","msg":…, "serial":…}, "loc": "<file>:<line>:<col>"}`), and it becomes the pending unwind for that thread until a non-panic RETURN;
  - tasks: one `tasks` row per non-main thread that emitted a causal event (`id` = serial, `name` = header name or NULL when empty), one `task_fingerprints` row per task (zero-count included), one `fingerprints` row for the main thread (zero-count included) — the Python zero-count rules of TRACE-FORMAT §3;
  - fingerprints: blake2b-16 over `"{file}\x1f{qualname}\x1f{kind}\n"` with `file` = the **workspace-relative** manifest path (D9); `fingerprint_basis = "per-task"`;
  - meta, required: `run_id`, `argv` (proc header), `cwd`, `env_hash` (proc header), `start_ts` = `start_realtime_ns / 1e9`, `end_ts` = `start_ts + (last ts_ns − start_ns)/1e9`, `exit_status` (runner json, else `null`), `main_thread_ident = 1`, `fingerprint_basis`, `truncated_count` (sum of headers), `source_hashes` (union over the units this process registered), `recorder = "sensorium-rt 0.1.0"`, `lang = "rust"`, `capabilities = {"line":false,"locals":false,"return_value":true,"tasks":true,"threads":true,"children":false,"stdin":false,"output":false,"object_identity":false,"refocus":false}`, witness keys `threads_started` (non-main spools) and `live_threads` (spools without THREAD_END, by name); optional shared: `env` (proc header), `caps = {"repr": 200}`; Rust-only: `invocation`, `pid`, `ppid`, `exe`, `toolchain`, `cargo_args`, `profile`, `instrumented_units`, `uninstrumented` (fell-back units, with reasons), `skipped`, `spawns`, `unreached_files` (the manifest lists for registered units — `unreached_files` so a declared-unreached module reaches the trace, Task 1 concern 3), `units_refused` (`{"refused": bool, "at": <metadata or null>}` from the proc header — the 256-unit refusal must reach the trace, not only stderr), `exit_status_basis` (`"waited"`|`"unwitnessed"`), `exit_signal`, `records_dropped` (`{serial: n}`), `seq_gaps`, `child_runs` (`[{run_id, pid, exe}]` for processes of the same invocation whose `ppid` is this pid — the converter assigns every run id first, then writes), `rt_version`, `driver_version`.
- Blake2b pin (computed with `hashlib.blake2b(digest_size=16)` on 2026-09-02; `blake2::Blake2b<U16>` must reproduce all three): empty input → `cae66941d9efbd404e4d88758ea67670`; one update `crates/demo/src/lib.rs␟main␟CALL⏎` → `f71e39f5d40e5af43313cbbfba9a01d2`; that update followed by the same file/qualname with `RETURN` → `57227ad2c76269e0e899ed211a58ba96`, count 2.

**Invariants, each with its test:**
- `convert.rs` over hand-built fixtures (bytes written by the test from the wire block — never by the runtime): the identical-pair fixture converts to two traces whose stored fingerprints are equal; a torn tail (kind 0 after N records) yields N events and `seq_gaps = 0`; a missing seq yields `seq_gaps = 1`; a live thread yields `live_threads` naming it and `incomplete = false`; a panic fixture yields RAISE + `closed_by unwind` + `unwind_exc.type = "panic"`; the runner json yields `exit_status` and basis `waited`, its absence yields `null` and `unwitnessed`; a parent/child pair yields `child_runs` on the parent; an orphan spool, a mirror path, a backwards seq each error by name; the three blake2b pins hold; the written schema string equals `db.SCHEMA` (the test embeds it verbatim from `src/sensorium/store/db.py` and Task 9 cross-checks by opening the file with the Python reader).
- Conversion of the rung-1-sized invocation (119 processes, 132k events) is timed and reported by Task 11, not gated.

- [ ] Tests first, implement, mutation-check, commit: `feat(driver): the Rust converter -- spools and manifests to trace format 4`.

---

### Task 7: The probe workspace and `rust/tests/mechanics.sh`

**Files:**
- Create: `rust/probes/ws/` (re-authored from the rung-1 probe: `probe-core`, `probe-app` with lib/bin/tests, `probes/ext` outside the workspace, the E7 tests, `threads.rs`, `spawn_bin.rs`, plus NEW: a `#[should_panic]` test inside a nested frame, a test that calls `std::process::abort()` in a child process it spawns, a test that leaves a thread blocked at exit, a doctest, a `Result`-returning test fn, a `Debug`-panicking return value), committed `Cargo.lock`; `rust/tests/mechanics.sh`

**Checks (one line per check, exit non-zero on any failure; every check is falsified once during the task and the falsification recorded in the report):**
- E7(a) as pre-registered, 4 checks × 2 arms, with `e7_binary_is_actually_instrumented` (spool count > 0).
- E8(a)–(d) on the probe with `CARGO_TARGET_DIR` on `/mnt/extra` (a different filesystem from the sources) — the configuration Task 11 uses — counting `Compiling`/`Fresh` and asserting the expected `Fresh` set (a build that dies also compiles nothing).
- Runner: every test binary's `<pid>.runner.json` exists with `exit_status = 0`; the abort child's trace carries `exit_status_basis: unwitnessed` and its parent's `child_runs` names it.
- Doctest: `cargo sensorium test --doc` passes (RUSTDOCFLAGS linkage); the control `env -u RUSTDOCFLAGS` re-run fails with `E0463`; the doctest process spools and converts with a dead `exe` recorded AND a `<pid>.runner.json` (cargo 1.96 routes doctests through the runner — measured 2026-09-02), so its trace reads `exit_status_basis: waited`.
- Naming: the thread `threads.rs` spawns via `std::thread::spawn` appears as a task named `<test> :: spawn@probe-app/tests/threads.rs:<line>`; `info` prints it.
- Panic: the nested panicking frame reads `closed_by unwind` and `unwind_exc.type panic` in `frame`; the outer frame that caught it reads `-> Ok` (or its value).
- Durability: the blocked-thread test's trace lists the thread in `live_threads` with its last record complete (`info` shows its events; `seq_gaps = 0`).
- Every unit's mirror carries its own metadata, `checked > 0`.
- The probe's `Cargo.lock` and the workspace tree (`git status --porcelain`) are byte-identical before and after; nothing outside `<target>` was written.
- The tool never falls back on the probe: `fell_back: true` count is 0 across manifests **and** 0 `fell back` lines in the build log (both channels).

- [ ] Write the checks (each falsified), then make them pass; commit: `test(rust): probe workspace and mechanics checks -- E7(a), E8, runner, doctest, naming, panic, durability`.

---

### Task 8: The Python reader on Rust traces — vocabulary, `unread`, exit basis, refusals, vectors, contract

**Files:**
- Create: `src/sensorium/query/vocab.py`; `docs/trace-format/vectors/v08-return-outcome-dbg-value.json`, `v09-zero-count-task-row.json`, `v10-exit-status-unwitnessed.json`, `v11-child-runs-linked.json`, `v12-call-unread-marker-in-tree-and-frame.json`, `v13-lang-keyed-prose.json`, `v14-rust-refusals.json`; `tests/test_vocab.py`
- Modify: `src/sensorium/query/{fmt.py, tree_cmd.py, frame_cmd.py, info_cmd.py, runs_cmd.py, diff_cmd.py, refocus_cmd.py, exceptions_cmd.py, watch_cmd.py, flow_cmd.py}`, `src/sensorium/store/reader.py` (`dropped_writes` adds `seq_gaps`), `docs/TRACE-FORMAT.md`, `pyproject.toml` (0.6.0), `README.md` (the version line only; the Rust section is Task 12)

**Interfaces (exact):**
- `vocab.py`: `def terms(trace) -> Terms`, `Terms` a frozen dataclass with `task_noun`, `task_noun_plural`, `thread_origin`, `unnamed_task`, `default_name_note`, `interp_line(meta) -> str`. For `lang == "python"` every string is **the exact string the renderer prints today** (moved, not reworded); for `lang == "rust"`: `task_noun = "test or spawned thread"`, `thread_origin = "as OS threads (libtest's per-test threads and threads spawned by workspace code)"`, `unnamed_task = "(unnamed: spawned by dependency code)"`, `default_name_note = None`, `interp_line = "toolchain: <meta toolchain>"`. Every site the six rung-2 commands can reach on a Rust trace reads its words from `terms(trace)`; `tests/test_vocab.py` runs `runs`, `info`, `tree`, `frame`, `grep`, `diff` on the Rust vectors and asserts none of `asyncio`, `Python's own`, `threading/_thread`, `coroutine`, `generator`, `python ?` appears.
- `tree_cmd.frame_line` and `frame_cmd`: a CALL payload carrying `unread: ["locals"]` renders `name() <unread: locals>` in `tree` and `args: <unread: locals>` in `frame` (never `(none)`); a Python trace without the key is byte-identical to today.
- `fmt.fmt_value`: new tag `{"k":"dbg","v":str,"trunc":bool}` renders as the raw text with `…` appended when truncated; `{"k":"unread"}` with no `type`/`oid` renders `<unread>`.
- `info` on `lang == "rust"`: line 2 is the `interp_line`; `exit: <n> (waited)` / `exit: unwitnessed`; `invocation: <id>  binary: <exe basename>`; `units: N instrumented, M fell back (<reasons>), K skipped (<reasons>), J spawn sites (W wrapped)`; `unreached files: N -- <paths>` when non-zero; `unit ceiling: recording REFUSED at unit <metadata> -- every later call in this process is unrecorded` when `units_refused.refused`; `child runs: N -- <run ids>` after the `children` declaration line; `live threads` line unchanged in fact, reworded via vocab; `seq gaps: n -- records minted and never found in any spool (one lost mid-write per thread at most; see rust/HONESTY.md §4)` when non-zero; `records dropped: …` when non-zero.
- `runs`: traces carrying `invocation` are grouped under a header `invocation <id>: cargo <cargo_args> [exit <cargo_exit>]` in name order, members indented two spaces, `exit:unwitnessed` where null; Python traces render exactly as today.
- Refusals on `lang == "rust"` (exit 2, wording via `caps.require` where a capability exists, else a named rung): `exceptions` → `REFUSED: exceptions on a rust trace needs the Rust disposition rules (rung 3); the Python rules would misread Err values as exceptions; nothing was judged`; `refocus` → `caps.require(trace, "refocus", "refocus")`; `watch`/`flow` already refuse on `line: false`.
- `reader.Trace.dropped_writes()` = `late_writes` or (`sum(records_dropped) + seq_gaps`); `diff` keeps refusing on non-zero.
- `TRACE-FORMAT.md`: §5 gains `dbg`, the RETURN `outcome` key, the PANIC-as-RAISE payload (`loc`); §4 lists the Rust-only keys **now written** (moved out of "planned"), `exit_status` null + `exit_status_basis`, `child_runs`, `seq_gaps`; §6 the `runs` grouping; §8 the seven new vectors with the rule each pins.

**Invariants:** the seven vectors each assert one rule and pass through the real CLI; every pre-existing test passes unchanged; `test_vocab.py` is green on the Rust vectors and mutation-checked (put `asyncio` back at one site → fails).

- [ ] Vectors and `test_vocab.py` first (RED), implement, mutation-check, commit in two parts: `feat(query): lang-keyed vocabulary, unread marker in tree/frame, dbg values, exit basis, child runs` and `docs(format): rung-2 keys, dbg tag, seven new vectors; version 0.6.0`.

---

### Task 9: Cross-recorder conformance and CI

**Files:**
- Create: `tests/test_rust_convert.py`, `tests/fixtures/rust-spools/<case>/{invocation.json, manifests/<metadata>.json, spool/<pid>.proc.json, spool/<pid>.<serial>.spool, spool/<pid>.runner.json, questions.json}` for cases `identical-pair`, `panic-unwind`, `live-thread`, `child-linked`, `unwitnessed-exit`, `unnamed-task`; a `tests/fixtures/rust-spools/gen.py` that writes the binary spools from a JSON description (so a fixture is readable and regenerable)
- Modify: `.github/workflows/ci.yml` (a `rust` job: `cargo build --release -p cargo-sensorium`, `cargo test --workspace` under `rust/`, `rust/tests/mechanics.sh`, then the Python suite on 3.14 with `SENSORIUM_CARGO_SENSORIUM=<built binary>` so `test_rust_convert.py` and `corpus/rust` run; the Python matrix jobs skip both with a named skip when the env var is absent)

**Invariants:** each fixture converts through the built binary and every question passes through the real CLI (`check_question`, as the vectors do); `identical-pair` reads `MATCH` with the tasks carrying the verdict; `panic-unwind`'s `frame` shows `unwound: panic('boom')`; `live-thread`'s `info` lists the thread with all its events; `child-linked`'s parent `info` prints `child runs: 1`; `unwitnessed-exit` prints `exit: unwitnessed`; `unnamed-task`'s `diff` against itself matches as an unnamed multiset. The Python reader opens every produced trace with no `TraceFormatError` — the one test that catches a Rust-writer/contract drift.

- [ ] Fixtures via `gen.py`, the test, CI; commit: `test(conformance): spool fixtures through cargo-sensorium convert and the real CLI; Rust CI job`.

---

### Task 10: The Rust corpus and `run_corpus.py --program cargo`

**Files:**
- Create: `corpus/rust/Cargo.toml` (workspace, members = cases, own `Cargo.lock`), `corpus/rust/<case>/{Cargo.toml, src/main.rs | src/lib.rs, questions.yaml}` for: ports `double_call`, `near_miss`, `nondeterministic`, `none_propagation`, `pass_vs_fail`, `unit_mismatch`, `wrong_branch`; Rust-only `panic` (`closed_by unwind`, `unwind_exc.type panic` in `frame`/`tree`), `abort` (the case's main spawns an instrumented child that calls `std::process::abort()` mid-frame: the parent's `child_runs` names the child, the child's `info` reads `exit: unwitnessed` and its `tree` shows the aborting frame open, `diff` of the child against a clean sibling run is REFUSED or DIVERGED — the question pins which, from the recorded truth), `libtest_threads` (`cargo sensorium test -- --test-threads=1` vs `8`: `diff` MATCH with tasks carrying; the counter-truth question asks `diff` of a trace whose `task_fingerprints` were deleted by the case's `record` step and expects REFUSED), `spawned_thread` (a worker spawned by a test holds a lock; `tree` and `diff` name `<test> :: spawn@…`); refusals `aliasing` (`flow --object` → the `object_identity: false` text) and `stale_cache` (`watch` → the `line: false` text)
- Modify: `corpus/run_corpus.py` — `program: cargo` with `cargo_args: [...]` (and `second_run: {cargo_args: [...]}`), recording via `$SENSORIUM_CARGO_SENSORIUM` (or `cargo sensorium` on PATH) from `corpus/rust/` with `-p <case>`; the `run:` line parsed exactly as the Python `run:` line is; skip with a named reason when no driver is available; `--bench` unchanged (Python only)

**Invariants:** every question pre-registers `why_logs_fail` naming which of `dbg!`, `RUST_LOG`, `RUST_BACKTRACE` fails; every case is recorded and its questions pass; every case's truth is planted and stated; the corpus count line reads `13 cases / N questions / 0 errors`; no case needs `?`, locals, or output.

- [ ] Author the cases with truths first, extend the runner, run to green, commit: `feat(corpus): the Rust corpus -- seven ports, four Rust-only cases, two refusals`.

---

### Task 11: The acceptance run — E2′, E3, E5, E7, E8 on the clone

**Files:**
- Create: `rust/tests/acceptance.py` (the runner: none-versus-zero `results.json`, every arm logged), `rust/tests/render_acceptance.py` (results → §3 tables)
- Modify: `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` §3 (rendered), §4 (written by hand against the pre-registered rules, quoting numbers), §5 (gaps); commit `…-acceptance.results.json` beside it; raw logs and `results-raw.json` in the ledger (gitignored)

**Protocol (the runner enforces it; a human follows the same order):**
1. Preflight: load ≤ 4.0, `/mnt/extra` ≥ 8 GB, `/` ≥ 3 GB, clone clean @ `e209ed9`, `~/workspace/bloomery` untouched (HEAD + porcelain), pins recorded; `cargo install --path rust/cargo-sensorium --root /mnt/extra/sensorium-rung2/tool` and the Python venv's `sensorium` at 0.6.0.
2. E8 on the clone, in the pre-registered order (a) → (c)+sentinel → (d), then (b) on branch `e8-touch` with restore; the plain arm's `--no-run` is the baseline build wall (this is a cold target dir on `/mnt/extra`: a genuinely clean build of the whole workspace, deps included — the lens says so).
3. E2′ from the manifests of a workspace-wide instrumented `--no-run`, against the census over the same files. **Scope every manifest-derived count to the measured build's own units** (the set of `-C metadata=` values in that build's `cargo -v` log — complete only when the build compiles every unit, i.e. a from-scratch target, because cargo does not invoke the wrapper for fingerprint-fresh units (Task 9 measured an empty set on a warm target); the acceptance builds run on the clone's fresh `bloomery-target`, and `rm -rf <target>/sensorium/manifests` before the measured build is the belt-and-braces the runner performs and records): the wrapper's path is hashed into cargo's metadata, so a rebuilt driver leaves the previous tool hash's manifests behind in `<target>/sensorium/manifests/` and an unscoped scan would inflate the numerator (found by Task 9 on a fresh build; ruling in the ledger). State the scoping in the lens.
4. E3: `--no-run` for `--lib`, sha256 the binary, 20 recorded runs, 19 diffs.
5. Reported walls: 5 rounds of plain vs call on `--lib` in the alternating order, 10 s cool-down, load recorded per arm, an arm dropped (not re-rolled) if load > 4.0 at its start.
6. E7(b): plain vs call `--lib -- --test-threads=1`, masked, diffed; E7(a) from `mechanics.sh` recorded.
7. E5: create `e5-split` (the implementer performs the split by hand — verbatim moves, `mod tests` path preserved — and commits it on the clone), record A, B; create `e5-planted` from `e5-split` with the one swap, record C; the three `diff` commands; the diff outputs verbatim into the report. The split patch is saved to the ledger as `e5-split.patch` for Brice; it is not pushed anywhere.
8. Whole-invocation report: one `cargo sensorium test -p bloomery-daemon` (all binaries) → conversion wall, process counts (run / spooled / converted), `exit_status_basis` histogram, `child_runs`, live threads with last-record completeness, `seq_gaps`, `records_dropped`, `truncated_count`.
9. `render_acceptance.py` writes §3; §4 is written by hand quoting each rule and number and saying PASS / STOP; §5 lists every gap surfaced.
10. Cleanup: the clone back on `e209ed9` with `status --porcelain` empty (the E5/E8 branches kept locally); `~/workspace/bloomery` untouched; disk reported.

The run is detached (`setsid nohup … &`, pid file, `.DONE` marker, a watcher that distinguishes death from silence — rigorous-experiments §5); nothing is read before it completes.

**Invariants:** every §3 cell is a number with `n` and lens or `not measured (<reason>)`; the E3 table lists all 19 verdicts; the E5 section carries the three verbatim `diff` outputs and the split's file table; §4 quotes each pre-registered rule verbatim beside its number; a STOP verdict on any endpoint ends the rung's PR at a findings document, exactly as rung 1's plan said for a NO.

- [ ] Commit: `docs(rung2): acceptance results, decisions, and gaps -- E2', E3, E5, E7, E8 on the bloomery clone`.

---

### Task 12: Land it — README, spec amendments, PR

**Files:**
- Modify: `README.md` (a Rust section: install, record, what answers, what refuses, the cost numbers from Task 11 beside Python's), `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` (dated, non-silent amendments: §2.3 → D1; §2.2 lock → D2; §2.5 runner + exit status → D4, children → D7; §3.2 the `ret` form replacing the `match` wrap, with the `unused_parens` reason; §3.5 confirmed with the naming shape; §4 wire v2 and the kind-last rule; §5.1 the keys now written; §6 items done / refusals in this rung; §8 measured column for E2′/E3/E5/E7/E8; §10 rung 2 verdict; §11 rung 2 DONE with the next rung's inbox; §13 a rung-2 deltas table), `docs/TRACE-FORMAT.md` (any last drift Task 9 exposed), `CHANGELOG` section in README if that is where versions are noted
- The PR body: goal, what shipped, the five verdicts with numbers, the decisions table, what refuses on Rust traces and why, the do-not-retry list, the ledger path.

**Invariants:** nothing in the spec is deleted — struck through and dated; every amendment cites a §3/§4/§5 number of the acceptance document or says *controller ruling 2026-09-0x (ledger, local-only)*; the final whole-branch review (fable) precedes push and PR; CI (Python matrix + the Rust job) green before merge; origin in sync after merge.

- [ ] Commit: `docs: rung 2 shipped -- README Rust section, spec amendments, format contract`.

---

## Self-review against the spec

- **Spec coverage.** §2.1 hook, passthrough, versioned shim → T5. §2.1 rustdoc/RUSTDOCFLAGS → T5, T7. §2.2 per-unit mirror, remap, lock → T5 (D2). §2.3 linkage → D1/T5. §2.4 site identity, manifest per unit, 256 ceiling → T2, T4, T5; focus/window resolution → rung 4. §2.5 cargo stays the runner, one trace per process, invocation grouping, WARN, children → T5, T6, T8 (D4, D7). §3.1 splicing → T4. §3.2 guard, exit operands, outcomes, skips, `process::exit` open frame → T2, T4. §3.3 `?`/sinks/arms → rung 3 (declared in HONESTY §8). §3.4 locals/LINE → rung 4. §3.5 `spawn_child` → T3, T4. §3.6 reentrancy, `catch_unwind` → T2, T3. §3.7 tiers `off`/`call` (`full` reserved), fallback per unit with reason → T2, T5. §4 serials, sequence, `MAP_SHARED`, `THREAD_END`, live threads, tasks, panic hook, capped values → T2, T3, T6. §5.1 required/witness/Rust-only keys, one choke point → T6, T8. §5.2 gating → T8. §5.3 enumerations → T6, T8 (v08, v05 already). §5.4 code identity → T6 (D8, D9). §5.5 ordering → T6 (v03 already). §5.6 vectors → T8, T9. §6 reader fix (done), `--ignore-moves` (done), `exceptions` rust rules → rung 3 (refusal in T8), `refocus` rust → rung 4 (refusal in T8), vocabulary → T8, `runs`/`info` → T8, `tree`/`frame` unread → T8, lang-keyed prose → T8. §7 ledger → T1. §8 E2′/E3/E5/E7/E8 → T0, T11; E1 reported only (D10); E4/E6 later rungs. §9 goldens, probe workspace, rt tests, vectors, corpus (the "need no `?`" subset), CI → T4, T7, T2/T3, T8/T9, T10, T9. §10 rung 2 → T11. Findings §5.1 → D4; §5.2/§5.25 → T2 durability; §5.3 → T4/T5 source_hashes; §5.4 → declared; §5.5 → T8; §5.6 → T8; §5.7 → D7; §5.8/§5.27 → D8; §5.9 → T2 proc header (env, realtime) + T5 invocation.json (toolchain); §5.10 → T2 counters; §5.11 → T6 dead exe; §5.12 → D2; §5.13 → T2 units test; §5.14 → E2′ row; §5.17 → E7(b); §5.18 → reported walls alternate order + cool-down; §5.19 → target on /mnt/extra; §5.20 → T3; §5.21 → T5 remap; §5.22 → T5 per-unit mirror; §5.23 → T5/T7 doctest; §5.24 → D1; §5.26 → D3; §5.28 → reported, the lever untouched; §5.29 → T5 fallback manifests + `checked > 0`.
- **Placeholder scan.** No TBD/TODO; every code step names its test and its file; the wire format, manifest, invocation.json, runner.json, the exit form, the schema reference, and the blake2b pins are verbatim.
- **Type consistency.** `enter(&'static Unit, u32) -> Guard`, `ret<T>(&'static Unit, u32, impl FnOnce(&T) -> (Capture, Outcome), T) -> T`, `spawn_child(&'static str, F) -> JoinHandle<T>`, `Probe(&T)` with `debug_cap()`/`outcome()` — used identically in T2, T3, T4's fragments and T7's checks. `Site.ret` ∈ `unit|value|never` in T4's manifest and T6's mapping. `exit_status_basis` ∈ `waited|unwitnessed` in T5, T6, T8, T9. `child_runs` shape in T6, T8, T9. `seq_gaps` in T6, T8, T9.
