# Sensorium Rust recorder — reworked design

Date: 2026-09-01. Status: DRAFT for Brice's review. Supersedes the unwritten
design of the 2026-09-01 brainstorm session (sections 1–3 delivered in chat,
section 4 never written, no spec file). **Amended 2026-09-02 with rung 1's
measurements** — every such amendment is dated in place and nothing is deleted;
§13 collects them.

## 0. Provenance

The brainstorm fixed four decisions, all of which stand:

- **Approach A**: build-time source transformation (a `cargo sensorium`
  driver, a `syn` rewriter, a `sensorium-rt` runtime linked into the build,
  a converter that writes sensorium's SQLite trace format).
- **Bloomery first**: the wrap-one-run lifecycle; smithy-comp's hours-long
  compositor session (ring buffer, trigger dump) is a later lifecycle that
  reuses the recorder.
- **One repo**: the Rust crates live in `sensorium/rust/` as their own cargo
  workspace; `docs/TRACE-FORMAT.md` plus conformance vectors sit between the
  two recorders.
- **Standing ruling (2026-08-20)**: multi-language support never compromises
  the Python core; the trace schema becomes a frozen contract; sibling
  recorders carry their own honesty ledger and their own exceptions-verdict
  rules; no "80% works" polyglot mode.

The design was then reviewed adversarially: five dimension reviewers (cargo
mechanics, transformer soundness, format contract, measurement rigor,
bloomery fit), one refuter per finding with compile probes on this box, and a
completeness critic — 46 agents, 33 findings confirmed, 6 refuted. Every
mechanism below that differs from the brainstorm cites its finding number
(`F<n>`); the full record — brief, brainstorm transcript, all 33 findings
with verifier evidence, and the `diff` output on today's Python-trio pair —
is in `.superpowers/sdd/2026-09-01-rust-recorder-review/` (gitignored,
local-only, per the v1 precedent). Section 13 lists the deltas.

Three findings were blockers in the design as brainstormed:

1. `RUSTC_WRAPPER` + `CARGO_PRIMARY_PACKAGE` is the wrong cargo hook: not
   fingerprinted (a plain `cargo test` afterwards runs INSTRUMENTED binaries,
   and vice versa, silently), wrong scope (under `-p bloomery-daemon`, core and
   substrate compile untouched and undeclared), path-keyed (an upgraded
   transformer never rebuilds). F1, F8, F24.
2. libtest runs every `#[test]` on its own spawned thread named after the test
   path; the process main thread runs no workspace code. `diff`/`refocus`
   compare the main thread, so with the brainstorm's empty `tasks` table every
   cargo-test comparison is REFUSED (or falsely DIVERGED under the event-id-1
   fallback). F4, F10, F17, F25.
3. The stated first use — verify a file split "by trace" — reads DIVERGED by
   construction: the fingerprint hashes `file`, and the brainstorm put
   `module_path!()` into `qualname`, so a pure module move changes both keys of
   every moved function. Today's Python-trio split was compared by eye on
   `info` counts for exactly this reason. F16, F18, F26.

**Rung 1 was measured 2026-09-02** (pre-registered mechanics spike; code parked
on branch `spike/rust-mechanics`, never merged; evidence landed here). Findings:
`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`; machine-readable
results: `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.results.json`.
Every amendment below dated 2026-09-02 cites a §3 number, a §4 decision or a §5
gap of that findings document — including the §5.21–29 addendum appended to it
after the final review, which carries the spike's own evidence for the
amendments below in the document main ships. Where an amendment rests on a
ruling rather than on a measurement it says so as *controller ruling 2026-09-02
(ledger, local-only)* and cites nothing this repository does not carry; §13
collects them as a deltas table.

## 1. Goal, scope, non-goals

**Goal.** An agent debugging bloomery's Rust records one `cargo test`
invocation and asks sensorium's existing questions of it — `tree`, `frame`,
`grep`, `exceptions`, `diff`, `refocus`, `info`, `watch`, `flow` — with the
same honesty contract the Python recorder carries: every answer is a function
of the trace, and the instrument never answers from data it does not have.

**In scope for v1 (bloomery-first).**

- Workspace crates only, stable rustc, no nightly, no root, no hand annotation.
- Event kinds CALL, RETURN (with outcome and value), RAISE, HANDLED, LINE with
  locals under `--focus` (opt-in tier), panics.
- Threads: every thread attributed; libtest tests and workspace-spawned
  threads compared as named units of work.
- `diff`/`refocus` verdicts on bloomery test binaries, including a
  move-aware comparison for behaviour-preserving refactors.
- A Rust corpus, a Rust honesty ledger, and a trace-format contract with
  conformance vectors.

**Out of scope for v1** (each declared as a capability the trace states):

- Program output under libtest (`capabilities.output = false`; libtest owns
  the capture and `io::set_output_capture` is unstable; F32).
- Object identity (`capabilities.object_identity = false`; `flow --object`
  refuses on Rust traces; F22).
- Dependency-crate internals; mutation through a long-lived `&mut` reference;
  `?` inside macro arguments (F21, F6) — all named in the ledger, not implied.
- Async runtimes, the ring-buffer lifecycle, rr, attach-to-live.

## 2. Architecture

Four artifacts. Three are new and Rust; the fourth is the existing Python
query layer with the additions in §6.

| Artifact | Kind | Job |
|---|---|---|
| `sensorium-transform` | Rust lib | `syn` rewriter. Pure: original source + tier config + module path → spliced source + site manifest. No I/O. |
| `sensorium-rt` | Rust lib | Linked into every instrumented unit. Thread serials, global sequence, frame stack, capture probe, task registry, panic hook, spools. |
| `cargo-sensorium` | Rust bin | Driver (`cargo sensorium test …`), workspace wrapper (invoked by cargo per unit), converter (spools + manifests → `.db`). |
| `sensorium` | Python | Query CLI, unchanged in shape; §6 additions. |

```
cargo sensorium test -p bloomery-daemon --lib -- task::registry
  │
  ├─ mints an INVOCATION id; exports SENSORIUM_SPOOL=<traces>/spool/<invocation>,
  │  SENSORIUM_TIER, SENSORIUM_FOCUS_SITES, SENSORIUM_WINDOW_SITES
  ├─ RUSTC_WORKSPACE_WRAPPER=<versioned path>/cargo-sensorium   cargo test <args unchanged>
  │    └─ per workspace unit (cargo calls the wrapper; deps are never wrapped):
  │         passthrough: build scripts, proc-macro crates, `-vV`, `--print`, stdin probes
  │         else: mirror + splice (§3) → cd <mirror> → exec rustc <argv unchanged>
  │               --extern sensorium_rt=<rlib>       manifest → target/sensorium/manifests/<metadata>.json
  ├─ cargo runs each test binary as it always does (cwd, env, --exact, --test-threads untouched)
  │    └─ sensorium-rt in every instrumented process spools per thread under SENSORIUM_SPOOL
  └─ convert: one trace per OS process → ~/.sensorium/traces/<run-id>.db, meta.invocation groups them
```

### 2.1 The cargo hook (F1, F8, F24)

`RUSTC_WORKSPACE_WRAPPER`, not `RUSTC_WRAPPER`. Verified on cargo 1.96: cargo
invokes the workspace wrapper for every workspace member regardless of `-p`
and for nothing else; it hashes the wrapper into `-C metadata`, so
instrumented and plain artifacts coexist in one `target/` and switching back
recompiles nothing and runs the right binaries. The `--test` harness units go
through it too (they are the binaries to instrument). Cargo keys the wrapper
by PATH, not content, so the driver points the variable at a version-encoded
path (`target/sensorium/<transform+rt hash>/cargo-sensorium`, a shim) so an
upgrade rebuilds. The wrapper passes through untouched: crate name `___` or
`build_script_*`, `--crate-type proc-macro`, `-vV`, `--print`, and stdin
(`-`) invocations. No `CARGO_PRIMARY_PACKAGE` test, no `cargo metadata` call.

A user's own `RUSTC_WRAPPER` (sccache) is left alone.

**Amended 2026-09-02 (rung 1 measured).** "Cargo invokes the workspace wrapper
for every workspace member … and for nothing else" is true of `rustc` and
silent about `rustdoc`: **rustdoc is not routed through
`RUSTC_WORKSPACE_WRAPPER` at all**, so a doctest unit compiles without the
`--extern sensorium_rt` the instrumented rlibs need and fails `E0463` until the
driver carries the same linkage through **`RUSTDOCFLAGS`** (findings §5.23,
where the control that proves it — a `cargo test --doc` re-run with
`RUSTDOCFLAGS` unset, exiting non-zero on
`error[E0463]: can't find crate for sensorium_rt` — runs every time, not once).
Doctests are not a route to skip: with the linkage carried, **a doctest
process links the instrumented rlibs and DOES spool**, and its `exe` is a
`/tmp/rustdoctest*/rust_out` that rustdoc deletes immediately, so it no longer
exists when the converter runs (spike §5.11, measured on the probe workspace by
`mechanics.sh`; **not** exercised on bloomery, which has 0 doctests — hence no
rustdoc process among the 119 of §3). Rung 2's converter must keep expecting a
dead `exe`.

### 2.2 The mirror (F2, F7, F28)

Cargo invokes the wrapper with cwd = workspace root, the crate root as a
RELATIVE path, every other path absolute, and no remap flag. So the wrapper
builds a workspace-root mirror at `<workspace>/target/sensorium/mirror/`
(same filesystem as the sources): rewritten `.rs` files materialised from a
content-hash transform cache, every other entry symlinked at each level
(`target/` and `.git/` skipped), then `chdir`s into the mirror and execs
rustc with cargo's argv unchanged. Consequences, all verified: `mod`,
`#[path]`, `include_str!`/`include_bytes!` (bloomery has 18 sites, some
crossing crate directories) resolve; `file!()`, panic locations, backtraces
and debuginfo are byte-identical to the plain build; cargo's dep-info stays
workspace-relative so freshness works — edit real source → rebuild, no edit →
Fresh. ~~`--remap-path-prefix <mirror>=<workspace>` is appended only as belt
and braces.~~ *(struck 2026-09-02 — falsified; see amendment 1 below.)* Never
`/tmp`, never a per-file copy, never a rewrite of include literals.

**Amended 2026-09-02 (rung 1 measured), two corrections.**

1. **`--remap-path-prefix <mirror>=<workspace>` is load-bearing, not belt and
   braces.** Without it, backtraces print mirror paths: with the flag removed
   the probe's frames printed
   `/tmp/…/sensorium/mirror/probe-app/tests/e7.rs:22:5` where the plain arm
   printed `./tests/e7.rs:22:5` (findings §5.21). E7's verdict —
   "Panic locations, `file!()`/`line!()` values and every backtrace frame's
   `<file>:<line>` were byte-identical between the plain binary and the
   instrumented one under both `off` and `call`", **0 differences** (spike §4
   E7) — was measured with the flag appended, and is therefore evidence for the
   mirror *plus the remap*, not for the mirror alone. Everything else this
   paragraph claims (`mod`, `#[path]`, `include_str!`, dep-info freshness) held
   as written: E8 read **0 failed checks** on bloomery (spike §4 E8).
2. **The mirror is PER UNIT, not per workspace:
   `<workspace>/target/sensorium/mirror/<-C metadata>/`.** One crate root is
   compiled as several units (lib, lib `--test`, each `tests/*.rs`) with
   different `-C metadata` (§2.4), and a mirror keyed only by content let those
   twins overwrite each other's `__SENSORIUM_UNIT` static — events attributed
   to the wrong unit, invisible to both E7 and E8, roughly 1 in 3 under `-j16`
   (findings §5.22, which carries the diagnostic that named it and the six
   consecutive clean runs after the fix). Per-unit mirrors were then
   verified with **0 shared inodes across the probe's 9 unit mirrors**, at
   92 KB for all nine (they are symlink trees). Per-unit mirrors also make the
   cross-unit mirror lock unnecessary for correctness (the spike's units still
   take a shared one — a deferred minor, not a rung-2 design). Rung 2 does
   inherit that lock as a known weakness: `mirror::Lock`'s staleness rule is a
   120 s timeout broken
   unconditionally by the next wrapper, which never fired here (whole builds in
   5.5 s) — "evidence of *not having hit it*, not of correctness" (spike §5.12).

**Amended 2026-09-03 (rung 2 shipped, decision D2).** Rung 2 replaced the
shared, timeout-based lock with **one `flock(LOCK_EX)` per unit** on
`<target>/sensorium/mirror/<metadata>.lock`, released by the kernel on
process death — no timeout, no staleness rule, no shared state to go stale.
Per-unit mirrors leave no shared mutable state to race on; the only
contention is two cargo processes building the same unit concurrently, which
`flock` serialises correctly. E2′ measured **108/108** units' mirrors checked
and **0** naming another unit's metadata (acceptance §3), consistent with the
lock holding under the acceptance run's own concurrency.

### 2.3 Linking the runtime (F24)

`sensorium-rt` is never in `Cargo.toml` (Cargo.lock stays untouched). The
driver builds `libsensorium_rt-<hash>.rlib` with the same rustc, target and
panic strategy at opt-level 3 into `target/<profile>/deps/`; cargo already
passes `-L dependency=<deps>` to every rustc invocation, so the wrapper adds
only `--extern sensorium_rt=<rlib>`. The runtime is optimised regardless of
the target profile because bloomery's dev-profile `cargo test` is the
workload (F19).

**Amended 2026-09-02 (rung 1 measured): a simpler linkage shape worked, and
the shape above is still the rung-2 refinement.** Rung 1 did not build the
runtime into the target workspace's `deps/`. It built
`cargo build --release -p sensorium-rt` in the *spike* workspace and had the
wrapper add `--extern sensorium_rt=<rlib>` plus
`-L dependency=<spike target/release/deps>` so the rt's own `libc` resolves
— a shape a controller ruling 2026-09-02 (ledger, local-only) allowed with a
STOP attached, because two `libc` crates in one graph at different hashes might
have been refused. **rustc accepted it**, and `liblibc-8fa2745d3cf757aa` (the
probe's dev deps) and `liblibc-21f15d3c5e5e6ae6` (the spike's release deps)
coexisted in one unit's graph for the whole run (findings §5.24). The
consequence is measured, not argued: **0 units fell back to the real tree**,
across 9/9 probe units, 77 units of the `-p bloomery-daemon` build and 108
units of the workspace-wide build, with **0 `fell back to the real tree` lines
in any build log** (spike §3 E2, §4 E2). Rung 2 may still move the rlib into
the target's own `deps/`; the record is that it did not block rung 1. Two
things this section owes rung 2 either way (findings §5.24): the
`-L dependency` shape resolved only because that directory held **exactly one**
`liblibc-*.rlib` — a second makes rustc refuse with "multiple candidates" and
the driver does not guard against it — and the rlib must be taken from `deps/`,
not from cargo's uplifted `target/release/libsensorium_rt.rlib`, whose
directory carries no `liblibc-*.rlib` at all.

**Amended 2026-09-03 (rung 2 shipped, decision D1).** Rung 2 resolved this
question with a zero-dependency runtime rather than the target-`deps/` shape
this section originally proposed: `sensorium-rt` has **no dependencies at
all** — no `libc`, nothing — so the two-`libc`-crates hazard measured above
cannot recur. The driver compiles it itself with one bare
`rustc --crate-type rlib --edition 2021 -C opt-level=3 -C panic=<strategy>`
invocation into
`<target>/sensorium/rt/<tool-hash>/<panic>/libsensorium_rt.rlib`; the
runtime's eight needed OS calls (`gettid`, `getpid`, `getppid`,
`clock_gettime`, `mmap`, `munmap`, `ftruncate`, `close`) are `extern "C"`
declarations. The runtime's source is embedded in the driver binary
(`include_str!`), so its version is the driver's version. The wrapper's
linkage is `--extern sensorium_rt=<rlib>` **and**
`-L dependency=<the rlib's own per-variant directory>` — amended a second
time after a pre-acceptance smoke test on the bloomery clone (2026-09-03): a
unit that depends on an ALREADY-INSTRUMENTED crate must resolve that crate's
own transitive `sensorium_rt` too, and rustc resolves a transitive crate by
search path, not by `--extern`. Measured: `--extern` alone gives
`E0463: can't find crate for sensorium_rt which bloomery_substrate depends
on`; adding `-L dependency=<rt dir>` fixes it. The probe workspace had passed
with `--extern` alone by resolver-order luck (its crate-root static resolved
before its `probe_core` uses); bloomery's `bloomery-daemon`
(`use bloomery_core::…`) did not. `RUSTDOCFLAGS` needed the same pair for the
same reason — rustdoc resolves a doctest's transitive crates by search path
too — confirming §2.1's rung-1 finding about `RUSTDOCFLAGS` rather than
replacing it. **Consequence, named in `rust/HONESTY.md` §8 item 7:** a unit
whose OWN DEPENDENCIES are instrumented cannot fall back to a plain compile
for ANY reason — the plain compile still needs `sensorium_rt` on the search
path its rmetas already reference, so a fallback for such a unit fails the
same `E0463` the instrumented build would have, and cargo's build fails
outright (measured on the bloomery clone, 2026-09-03, with a wrapper missing
the `-L`: `bloomery-daemon`'s lib unit was declared `fell_back: true` and the
build still exited 101). "Recorded nothing, built fine" — the ordinary
reading of a fallback — holds only for a unit whose own dependencies are
uninstrumented: a leaf workspace crate, or one depending only on registry
crates.

### 2.4 Site identity (F3, F33)

Cargo compiles one crate name as several units (lib, lib `--test`, bin, bin
`--test`, each `tests/*.rs`), each with its own `-C metadata` and its own
function set, and a test process links several instrumented units. So:

- The manifest is keyed by the unit's `-C metadata` hash and persisted at
  `target/sensorium/manifests/<metadata>.json` (cargo does not re-invoke the
  wrapper for fresh units, so the converter reads manifests from earlier
  wrapper runs).
- A site id is a `u32` packed as `unit_id:8 | site:24`. Each instrumented
  crate root gets `static UNIT: sensorium_rt::Unit = Unit::new("<metadata>")`,
  registered lazily; the spool's process header maps `unit_id → metadata`.
  A process that registers more than 255 units refuses to record rather than
  wrap.
- `--focus`/`--window` are resolved by the DRIVER after the build, against the
  manifests, with a Rust port of `FocusSpec.matches`/`WindowSpec.key`
  (`module` = the definition's module path as computed by the transformer
  walking `mod` declarations from the crate root; `qualname` = §5.4). The
  binary receives `SENSORIUM_FOCUS_SITES`/`SENSORIUM_WINDOW_SITES` as site-id
  lists; the runtime keeps only `u32` sets and a thread-local window depth.

**Amended 2026-09-02 (rung 1 measured): unit-keyed identity binds the mirror
too, and two measured limits follow.** Because the `__SENSORIUM_UNIT` static
lives in the crate root's *rewritten source*, a mirror shared between two units
of one crate root writes the wrong unit's identity into its twin — which is why
§2.2 is now per unit (`mirror/<-C metadata>/`). Two facts rung 2 inherits:

- **Site identity is per-unit, not per-source.** Measured: **7360 raw sites
  across 77 manifests against 1723 distinct `(file, qualname, firstlineno)`
  triples** — a 4.3× duplication, because `crates/bloomery-daemon/tests/common/`
  (13 files) is compiled into all 69 integration-test units and the daemon's lib
  is compiled at two feature sets (spike §5.8). Rung 1 does not need to merge
  them; any rung-2 feature that compares traces of *different* binaries does.
- **The 256-unit ceiling was never approached.** The workspace-wide build
  produced **108 units in total** and no single process linked more than a
  handful (spike §5.13), so the "refuses to record rather than wrap" path above
  is untested and is a real limit for a bigger workspace.

### 2.5 The run model (F4, F13, F23, F29)

`cargo test -p bloomery-daemon` runs 74 processes (lib harness, bin harnesses,
69 integration binaries, plus doctests), and 7 tests spawn the instrumented
`flywheel_tool`. *(Superseded 2026-09-02 — the measured counts are in
amendment 1 below; the sentence is left as written.)* Rules:

- **Cargo stays the runner.** `cargo sensorium test <args>` is
  `env … cargo test <args>`; `refocus` is the same command line with different
  `SENSORIUM_*` env, which cargo does not fingerprint, so no rebuild.
- **One trace per OS process.** `diff`, `refocus`, `main_thread_ident`,
  `exit_status`, `incomplete` and `uncaught` are per-process concepts in every
  reader; merging processes would force a `processes` dimension into all of
  them. Each process spools to `<spool>/<invocation>/<pid>.<tid>.spool` with
  a process header `{invocation, pid, ppid, exe, argv, cwd, start_ns, units}`;
  children inherit the env so they land beside their parent, and parentage is
  reconstructed from `ppid`.
- **`meta.invocation`** groups the traces; `runs` prints one group per
  invocation with the target binary per row. The driver prints the run ids it
  produced and WARNS when an invocation produced more than one test binary,
  naming a single-target selector (`--lib`, `--test X`, `--bin X`). The
  acceptance targets (§10) use single-target selectors; a batch `diff` across
  an invocation is a later rung.
- **Children are witnessed runs**, not unwitnessed subprocesses: the parent's
  `info` lists its children's run ids; a subprocess test therefore shows a
  child run id or an `unwitnessed child` line, never neither (F23).

**Amended 2026-09-02 (rung 1 measured), three corrections.**

1. **The process counts, measured.** One call-arm
   `cargo test -p bloomery-daemon` invocation: **72 test binaries run** (from
   cargo's own `Running` lines) plus 1 `Doc-tests` target that ran 0 tests;
   **71 of those binaries spooled** — the one that did not
   (`unittests src/main.rs`) ran 0 tests and so never entered an instrumented
   fn, "not a recorder failure"; and **119 processes spooled and were
   converted**, the 71 binaries plus **48** spawned instrumented
   `flywheel-tool` children of 1 distinct executable. In the spike's words:
   "Three different counts, three different quantities: 72 run, 71 spooled, 119
   processes" (spike §3, *Reported without a gate*). The 119 carried **132 344
   events** and 22 MB of traces, converted in 22.7 s. The parentage this
   section promises is on disk (`ppid` in each proc header) and rung 1's
   converter throws it away — every trace declares `capabilities.children =
   false`, so rung 2 must decide whether an invocation is one trace with
   children or N traces with a join key (spike §5.7).
2. **The driver is built `--release`.** Its fixed per-invocation cost is
   **0.025 s** as a release binary against **≈0.5 s** as a debug one (spike §3
   E1: "The instrumented walls include the driver's own fixed cost, measured
   separately at 0.025 s (release driver; a debug one costs ≈0.5 s)"). A debug
   driver would be ~6% of E1's 8.25 s suite wall — inside the endpoint it is
   measuring.
3. **`exit_status` is borrowed from cargo, and that is a rung-2 gap.**
   Per-process exit status is **not observable to the runtime**: the record
   stream carries no exit code and a `Drop`-based runtime sees neither
   `std::process::exit` nor a test binary's normal return. Rung 1's converter
   therefore writes **cargo's** status for every process of an invocation with
   `exit_status_basis = "cargo"`, so all 119 traces of one invocation carry the
   same number (spike §5.1; §3 reports the runtime's availability as **0**,
   which §1 had pre-registered as "expected: NOT available"). Rung 2 must
   either record the status at the process's own exit — an `atexit`/destructor
   hook that survives `exit()`, or the parent recording each child's `wait`
   status — or declare `exit_status` **unwitnessed** rather than borrowed.

4. **Amended 2026-09-03 (rung 2 shipped, decisions D4 and D7).** Item 3 above
   is resolved by **D4: a cargo runner role.** The driver sets
   `CARGO_TARGET_<HOST>_RUNNER=<shim> --runner`; cargo invokes the shim for
   every test binary AND — measured on cargo 1.96 — every doctest process; the
   runner spawns, waits, and writes `<pid>.runner.json` with the real status.
   A runner-waited process carries `exit_status_basis: "waited"` with the real
   code (or `exit_signal` on a signal); anything the runner did not start (a
   child a test spawned itself) carries `exit_status: null` and
   `exit_status_basis: "unwitnessed"` — never cargo's number wearing another
   process's name. Measured on the acceptance run's whole `-p bloomery-daemon`
   invocation (119 processes): **`waited` × 71, `unwitnessed` × 48** — the 71
   test binaries the runner started, the 48 `flywheel-tool` children they
   spawned themselves. Item 1's parentage question is resolved by **D7**:
   `capabilities.children` stays `false` (this recorder hooks no spawn
   primitive, so it cannot witness a spawn as it happens), and the Rust-only
   key `child_runs: [{run_id, pid, exe}]` links a same-invocation child to its
   parent by `ppid`; `info` prints the declaration and the `child runs:` line
   together, never one without the other (F23). Measured: **48** child run
   ids named by a parent across the same invocation (acceptance §3, *reported
   without a gate*).

## 3. The transformer

Two hazards decide every rule: rustc can refuse an injected capture (no
`Debug`, or an illegal borrow), and an injection can change the program
(temporary lifetimes, lock hold times, drop order). The transformer therefore
never `let`-hoists an operand, never re-prints the AST, and only injects where
safety is structural.

### 3.1 Emission: byte-offset splicing (F7)

`syn` parses the original text; every injected fragment is spliced at
`Span::byte_range()` offsets and is newline-free, so the rewritten file has
exactly the original line numbers. Verified: a `quote` re-emission collapses a
file to one line (panic at `:1:363` instead of `:13:53`); splicing keeps
`line!()`, panic locations and rustc error lines intact. "Line numbers and
paths are preserved" is a tested contract in the Rust ledger (E7).

### 3.2 Frames: entry guard and outcome (F9, F21, F30)

- First statement of every eligible fn body:
  `let _sens_guard = ::sensorium_rt::enter(SITE);` — first-declared is
  last-dropped, so every `let`-bound local (MutexGuards included) drops before
  RETURN. The guard's `Drop` is the SOLE emitter of RETURN and is correct
  through `?`, `return`, and panic unwind.
- Every exit operand of a non-`()` fn — the tail expression and each
  `return <e>` — is wrapped in place as
  ~~`match (<e>) { __r => { ::sensorium_rt::stash_ret(SITE, (&&Probe(&__r)).cap()); __r } }`~~
  *(struck 2026-09-03 — replaced; see the amendment after the skip-list bullet
  below: the parenthesised `match (<e>)` shape trips `unused_parens` under
  `#![deny(warnings)]`, measured while building rung 2's transformer)*.
  Identical temporary scope to the original (no new borrow errors, no
  drop-order change; a return value cannot borrow a tail temporary — that is
  already E0515). The guard attaches the stashed value and outcome on drop.
- Every frame therefore closes with an OUTCOME in `{ok, err, panic, none}`:
  `ok`/`err` from the probe on the returned `Result` (or `ok` for non-Result
  values), `panic` from the panic hook, `none` for `?` exits that bypassed the
  tail (the `?` site already recorded the Err), `-> !`, and unwinding
  `Drop`s. Python readers see `closed_by = "return"` or `"unwind"` with
  `unwind_exc = {"type": "panic", "msg": …, "serial": …}` (§5.3); the outcome
  is a payload key the Rust exceptions rules read.
- Skipped, and declared per fn in the manifest (`skipped: [{site, reason}]`):
  `const fn` (E0493/E0015; bloomery has five feeding const pins),
  `extern "C"` fns, fns inside `macro_rules!` bodies (none in bloomery). A fn
  that ends in `process::exit` keeps its frame open (`closed_by NULL`, the
  existing "open" state); run-level `incomplete` is cleared only by finalize.
- Edition 2021 note for the ledger: RETURN fires before a tail-expression
  temporary's own `Drop`; observable only if a workspace `Drop` impl runs in a
  tail temporary (bloomery has one `Drop` impl).
- **Added to the skip list 2026-09-02 (rung 1 measured): `async fn`, reason
  `async`.** The entry guard would live across every `.await`, which
  contradicts this section's sole-emitter rule, so rung 1 skips async fns and
  declares them like any other skip — a controller ruling 2026-09-02 (ledger,
  local-only): `async fn` is skipped at this tier with reason `"async"`, and
  rung 2 decides the async model.
  The skip costs bloomery nothing: the census counted **0 `async` fn** among
  2056 fn items with a body, and the run's **10** skip records are its 5
  `const fn` seen once in each of the two feature sets the daemon's lib is
  compiled at (spike §3 E2, §4 E2). E2 read **100.0%** with `async` on the skip
  list, so the §8 floor is untouched. Rung 2 decides whether async fns get a
  frame model or stay declared-and-skipped.

**Amended 2026-09-03 (rung 2 shipped): the exit form is `ret()`, not the
struck `match` wrap above.** The parenthesised
`match (<e>) { __r => { … } }` shape trips rustc's `unused_parens` lint, and a
crate under its own `#![deny(warnings)]` would fall back on every wrapped
fn — measured while building the transformer. Rung 2 ships instead:

```rust
::sensorium_rt::ret(&crate::__SENSORIUM_UNIT, SITE, |__r| { use ::sensorium_rt::probe::*; ((&&Probe(__r)).debug_cap(), (&&Probe(__r)).outcome()) }, <e>)
```

Verified under `#![deny(warnings)]` across 14 shapes (struct-literal tail,
`Box<dyn Trait>` tail, deref-coercion tail, `?` tail, `Err` tail, `!Debug`
return, early `return` inside `if`, `format!` tail, a generic `T: Clone`
return, `Option` tail, a `Drop`-logging guard held across the tail, a
`MutexGuard` in the tail, `Ok`/`Err` outcomes): zero diagnostics, drop order
and lock-release point unchanged. The probe traits take `&self`; the
specialised impls (`T: Debug`, `Result<T, E>`) are on `&Probe<'_, T>` and the
fallbacks on `Probe<'_, T>` by value, and the call site's `(&&Probe(__r))` is
the autoref order that makes the specialised impl win when it applies. The
closure is passed BEFORE the operand — an argument-evaluation-order
guarantee, not a coincidence — so a diverging operand leaves nothing
unreachable after it. **Not wrapped**, because each is syntactically
diverging and the frame already closes `none`, the same way `-> !` does:
`return`/`break`/`continue` expressions, a `loop` with no valued `break`,
calls of `panic!`/`unreachable!`/`todo!`/`unimplemented!`/
`std::process::exit`/`std::process::abort`, and — found only once real code
was measured against the rule — **any composite whose every arm diverges by
these rules recursively** (an `if`/`else`, `match`, or block whose every
tail/arm diverges). A bare block tail `{ e }` with no statements is wrapped
by wrapping `e` *inside* the braces, because a wrapped outer block fires
`unused_braces`. Both shapes measured **0** occurrences over the bloomery
clone's 1022 value-returning fn items — the rules exist so a workspace that
DOES have them never falls back. Unit-returning (`RetKind::Unit`) fns get no
`ret` call at all: the wire records outcome `none` for them, and the
converter maps that to `ok` with the recorded value `()` via the manifest's
`ret: unit` field, because a `-> ()` fn cannot contain a bare `?` that would
make `none` mean anything else there.

### 3.3 `?`, sinks and Err arms (F5, F6, F11)

- `<operand>?` → `::sensorium_rt::try_site!(SITE, <operand>)?`, which expands
  to the in-place form `match <operand> { __t => { probe(SITE, &__t); __t } }`.
  The scrutinee's temporaries live exactly as long as in the original (a
  `let` hoist is E0716 on guard-borrowing operands and, where it compiles,
  releases a MutexGuard early — verified with `try_lock`). The real `?` does
  the propagation, so the transformer needs no Option/Result/`Try` knowledge.
  The probe emits RAISE only when it sees `Result::Err`; `Option::None` emits
  nothing.
- Sinks: `.ok()`, `.unwrap_or*()`, `.is_err()`/`.is_ok()` receivers and
  `let _ = <value expression>` get the same match-wrap; HANDLED is emitted
  only when the probe sees `Result::Err`. `let _ = <place expression>` (path,
  field, index, deref) gets nothing — it moves nothing and swallows nothing.
- `Err(..) =>` arms and `if let Err(..)` bodies are classified syntactically:
  PROPAGATE if the body contains `?` at closure depth 0, `return Err(..)`, or
  ends in `Err(..)` → RAISE at the arm; PANIC if it contains a panic-family
  macro; else HANDLED. Bloomery census: 200 Err arms (28 propagate, 42 panic),
  25 `if let Err` (11 propagate, 1 panic) — the brainstorm's unconditional
  HANDLED would have reported a swallow in every one of those frames.
- Closures containing `?` get their own frame (guard at closure-body entry,
  qualname `outer::{{closure}}`) so a `?` that returns from the closure is
  never read as an exit of the enclosing fn. `?` inside macro arguments is
  invisible to `syn`; the fn is marked partially instrumented in the manifest
  (`partial: [{site, reason: "macro-arg"}]`).

### 3.4 Locals and LINE (brainstorm §2, unchanged in rule, restated)

Injection points that are provably safe: fn entry (parameters); immediately
after `let x = …` and `x = …`; statement boundaries (NLL has ended any
temporary `&mut`). The transformer tracks each binding and stops capturing it
the moment its name appears in any position it cannot prove is a shared
borrow (passed by value, returned, assigned away, `for`-consumed, bound by
`&mut`); it cannot know `Copy`, so it assumes moves it cannot rule out. The
failure mode is under-capture (`unread`), never a broken build. Mutation
through a long-lived reference is invisible and the ledger says so. Capture
uses the autoref `Debug` probe (verified on stable 1.96 for references,
`dyn Trait`, slices and unbounded generics): a `!Debug` value records as
`unread`.

### 3.5 Threads spawned by workspace code (F31)

`std::thread::spawn(f)` and `Builder::spawn(f)` at instrumented sites (matched
by path suffix; all 8 bloomery sites are literal `std::thread::spawn`; other
shapes are listed in the manifest as unwrapped) become
`::sensorium_rt::spawn_child(SITE, f)`: on the parent thread it reads the
current task's name, mints a NEW task serial named
~~`<parent task name> :: spawn@<file>:<line>`~~ [^spawn-name-amended], and
sets the child's thread-local task before running `f`. The child's events
carry its own task id and its own fingerprint, so a worker holding a lock
inside a test is IN the verdict.

[^spawn-name-amended]: Superseded 2026-09-03 — see the dated amendment at the
end of this section; the site string is no longer `<file>:<line>`.
Threads spawned by dependency code (tiny_http's accept thread) get no name
and are compared as unnamed tasks by content multiset (arc-2b Ruling R4).

**Confirmed 2026-09-02 (rung 1 measured), with the count.** Rung 1 has no
`spawn_child`, and the hole it leaves is visible: in the `--lib` trace, **53 of
57 emitting non-main threads carry the test's own name** — exactly the 53 tests
libtest ran — and **4** (spool serials 55–58) carry the empty string, because
libtest names the thread it runs a test on and nothing names a thread a *test*
spawns. Rung 1's converter turns each into a `tasks` row with a NULL name, so
`diff` compares them by `(name, hash)` with no name to compare on and `tree`
prints a task the reader cannot identify (spike §5.20; `config_test`'s 26
threads are all named, which is why this is invisible in that half of E0).
`spawn_child` as designed above is what names them; until it lands, per-task
naming is complete only for threads libtest itself created.

**Confirmed 2026-09-03 (rung 2 shipped), with the naming shape exactly as
designed.** `spawn_child` ships as this section specifies: a rewritten
`std::thread::spawn` site names its child
`<parent task name> :: spawn@<file>:<line>` when the spawning thread has a
TASK name, and `spawn@<file>:<line>` alone when it does not — which includes
a spawn from `main`, because std's own `"main"` thread name is a thread name,
not a task name (main is not a task; `rust/HONESTY.md` §3). Measured at
acceptance scale: the registry.rs split (E5, §8 and §10 below) moved a
`spawn_task` call site from `registry.rs:769` to `registry/mod.rs:248`, and
all four affected spawned-task names moved with it —
`…spawn@crates/bloomery-daemon/src/task/registry.rs:769` on one side,
`…spawn@crates/bloomery-daemon/src/task/registry/mod.rs:248` on the other —
while their stream hashes stayed pairwise identical
(`04afbcbcacf6`, `5976ef054dbe` ×2, `63737389821f`). That is the mechanism
working exactly as designed, and it is also **the cause of E5's STOP**: a
task name that embeds a spawn site is exact and reproducible, and also
renamed by the very kind of refactor `--ignore-moves` exists to see through.
§8's spawn-site count: **13** raw spawn sites rewritten across 108 manifests
(a raw sum, not a distinct count — two `(crate_name, crate_type)` pairs each
declare two manifests) against the census's **8** distinct literal
`std::thread::spawn(` sites over the same tree — `rust/HONESTY.md` §7 and
the acceptance document §4 name the duplication.

**Amended 2026-09-03 (Brice's ruling, rung-3 entry):** the site string in the
naming rule above is superseded. Brice ruled option (b) of the rung-2 exit
amendment (§11) and the rung-3 inbox
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §1): a spawned
task is named by something a move does not change — the enclosing fn's
qualname plus an ordinal — not by `<file>:<line>`. Executed as the rung-3
entry slice, plan
`docs/superpowers/plans/2026-09-03-sensorium-rung3-entry-spawn-names.md`,
endpoint E5′
(`docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md`).

N1 (verbatim, from that plan's Decisions table): "The site string is
`<qualname>#<k>`: `qualname` is the enclosing **fn item's** file-local
qualname exactly as the manifest's `files[<rel>][..].qualname` writes it
(`Type::method`, `outer::inner`, `tests::a_test`); `k` is the **1-based
ordinal among the WRAPPED spawn sites of that (file, qualname), in
byte-offset source order**. Unwrapped (declared) sites consume no ordinal."

N3: manifest `spawns` entries gain `"qualname": "<qualname>"` and
`"ordinal": <k>|null` (null when `wrapped: false`); `file` and `line` stay,
so the trace keeps the name ↔ location mapping without a converter change.

N6 documents four caveats, each with its observable consequence: (i)
inserting a wrapped spawn earlier in the same fn renumbers later ones — an
honest DIVERGED on their names, not a bug; (ii) the qualname is file-local,
so renaming the impl's self type or moving the fn into another `impl` block
renames the task; (iii) two files in one unit with an identical file-local
qualname each start at `#1` — the tasks share a name and `diff` compares
them as a multiset by content (HONESTY §7's twin rule); (iv) trait-impl
twins in one file (e.g. `Type::fmt` for `Display` and `Debug`) share the
qualname, so their ordinals continue across the twins in source order.

### 3.6 Reentrancy and capture faults (F32)

A thread-local capture depth with a drop-guard (so a panicking `Debug::fmt`
cannot leave it set); `enter()` returns a no-op guard while depth > 0, so a
workspace `impl Debug` invoked by the instrument emits nothing (Python's
`in_hook`). Every capture runs under `catch_unwind`; an instrument-provoked
panic records `unread` instead of unwinding the program.

### 3.7 Tiers and the build-failure fallback

Everything compiles in once; `SENSORIUM_TIER` (`off`, `call`, `full`) and the
site lists gate emission at runtime, so `refocus` is a re-run. This stands
only while E1's kill criterion holds (§8). If rustc rejects a rewritten unit,
the wrapper bisects over that unit's files (bounded, each retry a full unit
compile), then falls back to the real tree for that unit; the manifest records
`uninstrumented: [files]` per unit and `info` reports it. A fallback in
`tests/common/*.rs` uninstruments every test binary that includes it — the
manifest says which, one line per binary, never silently.

**Amended 2026-09-02 (rung 1 measured): the criterion held, and the gate is a
call, not a branch.** `median(off)/median(plain) = ×0.9975` against the ×1.5
kill rule (n=5 per arm, 0 dropped), so everything above stands: tiering does
not become a cargo feature and `refocus` does not become a rebuild (spike §4,
decision 1). But the *"predictable branch"* per site — the brainstorm's phrase,
which §13's first table already replaced with E0–E8 rather than with a number —
is, at the lens this was measured at, **a real cross-crate call per site**:
`#[inline]` on
`enter` buys nothing at `opt-level = 0`, and `fib(30)` costs **1.0595 ns/call
plain against 6.2875 ns/call at tier `off` — ×5.934**, about +5.2 ns of call
per site (spike §3 E1, lens `caller=dev(opt0) rt=opt3`; the release-caller lens
reads ×2.045). The honest statement is **immaterial at suite granularity, and
only there**: bloomery's suite records **15 874 events per second** of suite
wall while `fib(30)` records **3.04×10⁷** — a gap of ≈1900× — and §4 states the
ruling with that limit, "compile-once-gate-at-runtime is free on code shaped
like bloomery's test suite", not free. Re-open this decision the first time
rung 2 points at a call-dense suite; the threshold is §8's E1 row. Also
measured: the fallback path above never fired (0 units fell back, §2.3
amended), so the bisect-and-fall-back machinery is untested in anger.

## 4. The runtime (`sensorium-rt`)

- **Thread serials**: process-global `AtomicU32`, minted on a thread's first
  event; the main thread (Linux: `gettid() == getpid()`) is serial 1 even if
  it never emits, and `main_thread_ident = 1` is written explicitly (F12).
- **Global order**: every record carries a process-global `AtomicU64`
  sequence (one `fetch_add` per event — exact cross-thread causality, which
  `tree`'s footer and `exceptions`' `x.id > r.id` rely on) and
  `CLOCK_MONOTONIC` ns for `ts_ns`. The converter k-way-merges spools by
  sequence; frame ids are assigned from the merged order (F13).
- **Spools are `MAP_SHARED` file-backed mappings**, one per thread, grown by
  `set_len` + remap, no userspace buffer and no lock: the kernel keeps the
  pages on normal exit, on a thread that is still blocked in `recv()` when
  libtest exits, and on SIGKILL/abort. The thread header carries the thread
  name; a clean thread exit appends `THREAD_END`. The converter derives
  `threads_started` (spools), `live_threads` (spools without `THREAD_END`,
  with each one's innermost open frame), and per-thread `records_dropped`;
  frames of live threads stay open and `info` prints them as
  `still running at exit` (F20, F27).
- **Tasks**: every non-main thread that emits an event is a task row
  (`name` = its thread name: libtest sets `mod::path::test`, `spawn_child`
  sets the derived name, dependency threads are NULL), every event on it
  carries that task id, and the converter writes one `task_fingerprints` row
  per task and `fingerprint_basis = "per-task"`. Thread fingerprint rows cover
  NULL-task events only (the main thread), so a zero-count row means "ran
  traced code only inside tasks" (arc-2b Ruling R5). `diff` already lets task
  rows carry the verdict when both main streams are empty (diff_cmd.py
  `if not sa and not sb and tasks["verdict"] is None`), so no diff change is
  needed for the libtest shape (F10, F17, F25).
- **Panic hook**: records the panic payload and location against the
  thread's open frame; the guard's `Drop` closes the frame `unwind`.
- **Values**: `Debug` output capped like `capture.py` (str/repr length, sample,
  depth), truncation counted per thread and summed into `truncated_count`.

**Amended 2026-09-02 (rung 1 measured): the loss model, measured on the spike's
`BufWriter` spool — and `MAP_SHARED` remains the answer.** Rung 1 spooled
through a per-thread `BufWriter` flushed by a thread-local destructor, **not**
the `MAP_SHARED` mapping specified above, so its measured losses are the case
for that design rather than a change to it:

- **A thread alive at process exit loses its buffered tail, silently.**
  Measured: **100 spool files without a `THREAD_END` record, in 3 of 119
  processes** — 64 of 81 threads in `api_v1_honesty_test`, 32 of 62 in
  `api_v1_test`, 4 of 71 in `api_native_test`, all daemon HTTP server threads
  still running when the test binary exited. The converter reports them in
  `live_threads` and still sets `incomplete = false` (the *process* finished;
  the thread did not) — "which is the right distinction and also the one a
  reader will misread". **The loss is silent in the trace's own event counts**
  (spike §5.2). Until `MAP_SHARED` lands, any trace of a server-shaped test
  under-reports those threads' tails by an unmeasured amount.
- **`process::exit` flushes only the calling thread.** Measured on the
  runtime's own tests: `exit()` runs the **calling** thread's thread-local
  destructors, so that thread's spool does flush, while every other live thread
  loses its buffered tail; `abort` and a fatal signal lose every thread's tail.
  Read off the spool bytes, not argued: after `exit(0)` main's spool is **87 B
  ending in `THREAD_END`** and the live thread's is **17 B, header only**;
  after `abort()` both are header-only (findings §5.25, which carries the
  three-row table and the `__call_tls_dtors` mechanism). This is narrower than
  "process::exit loses everything" and wider
  than §3.2's frame note; `MAP_SHARED` is what makes all three cases moot.
- **Two of this section's fields are asserted, not witnessed, in rung 1.**
  `truncated_count = 0` and `records_dropped = {}` are written by a runtime
  with no drop counter, so a spool that lost records converts to a trace that
  positively claims nothing was dropped (spike §5.10); and `source_hashes` is
  `{}` in every rung-1 trace, so nothing pins the source a trace was recorded
  against (spike §5.3) — which §6's `refocus` sameness check depends on.
  Rung 2 fixes or declares each.

**Amended 2026-09-03 (rung 2 shipped): wire format v2, verbatim, and the
kind-last write discipline that closes the tail-loss gap above.** Every
record is
`u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome  u16 payload_len  [payload]`,
and **every field except `kind` is written first, `kind` last with a Release
store** — kind 0 marks the unwritten tail a `MAP_SHARED` file is zero-filled
with, and a reader stops at the first zero it meets. That is the whole of the
durability rule from the paragraph above, restated as a mechanism: **a
record is complete iff its `kind` is non-zero**, so the file survives a
thread that never returns, `process::exit`, `abort`, and SIGKILL, and the
only possible loss is one record caught mid-write, at most one per thread —
counted at conversion as `seq_gaps` (a hole the merge infers) separately from
`records_dropped` (what the writer itself knew it could not write, e.g. a
failed `ftruncate`/`mmap`). The 28-byte file header
(`b"SNSR" u8 version=2 u8 flags=0 u16 name_len u32 thread_serial
u64 records_dropped u64 truncated`, then the thread name) carries
`records_dropped` and `truncated`, rewritten in place through the mapping and
final only once `THREAD_END` is present; growth is `ftruncate` + remap in
64 KiB chunks. The per-process `.proc.json` header is written
tmp-then-renamed, so a kill between the two can leave an orphan
`.proc.json.tmp` the converter must not match. `env_hash` is sha256 over
`"\n".join(f"{k}={v}" for sorted env items)`, first 16 hex chars — **not**
the Python recorder's `json.dumps(env, sort_keys=True)` formula; the two are
comparable only within one language, and `docs/TRACE-FORMAT.md` §4 says so.
Measured on the acceptance run's whole invocation: **0** `seq_gaps`, **0**
`records_dropped`, **0** `panics_unrecorded`, **5729** captured return values
truncated at the 200-byte cap, **100** live threads at process exit with
**0 of 1250** spool files carrying a torn last record (parsed directly off
the spool bytes, outside the converter) — rung 1's tail-loss gap is closed on
the record side.

## 5. The contract: `docs/TRACE-FORMAT.md`, trace format 4

The schema (`code_objects`, `frames`, `events`, `output`, `tasks`,
`fingerprints`, `task_fingerprints`) takes Rust data without a column change.
What format 4 adds is a REQUIRED META SET and pinned enumerations; the bump is
kept because a format-3 Rust trace makes every pre-Rust reader print false
provenance lines (observed: "predates the recorder's thread bookkeeping",
"recorded before task fingerprints existed"). The named cost: readers ≤ 0.4.0
refuse new Python traces too. Acceptable now that the global tool is an
editable install of the repo (fixed today; it had been a 0.1.0 snapshot).

### 5.1 Meta (F12, F20)

Two classes, both written by BOTH recorders:

- **Language-neutral required keys**: `run_id`, `argv`, `cwd`, `env`,
  `env_hash`, `exit_status`, `incomplete`, `start_ts`, `end_ts`,
  `main_thread_ident`, `fingerprint_basis` (explicit, never defaulted),
  `source_hashes`, `caps`, `focus`, `include`, `exclude`, `window`,
  `recorder` (`"sensorium 0.5.0"` / `"sensorium-rt 0.1.0"`), `lang`
  (`"python"` / `"rust"`), `capabilities`.
- **Witness keys bound to a capability**: `threads_started` + `live_threads`
  ↔ `capabilities.threads`; `children` + `spawn_syscalls` + `audit_errors` ↔
  `capabilities.children`; `stdin_consumed` ↔ `capabilities.stdin`;
  `truncated_count` + `records_dropped` ↔ finalize. A capability that is
  `false` means "declares not witnessed"; readers print that, never "predates"
  and never a zero.
- **Rust-only keys**: `invocation`, `pid`, `ppid`, `exe`, `toolchain`,
  `cargo_args`, `profile`, `instrumented_units` (metadata hashes),
  `uninstrumented`, `skipped`, `partial`.
- **One choke point**: `Trace.open` on a format-4 trace with
  `incomplete = false` refuses with `TraceFormatError` naming recorder and key
  if any required key is missing. The reader's `.get(key, 0)` sites are then
  unreachable on format 4 and untouched for format 3. The "predates" sentences
  key on `recorder` + `trace_format`, not on key absence.
- **Refused-on-absence subset** (amended 2026-09-02 while planning rung 0):
  the keys the readers would otherwise default to a number are the ones
  refused — `run_id`, `argv`, `cwd`, `env_hash`, `start_ts`, `end_ts`,
  `exit_status`, `main_thread_ident`, `fingerprint_basis`, `truncated_count`,
  `source_hashes`, `recorder`, `lang`, `capabilities`, plus the witness keys of
  every capability declared true. `env`, `caps`, `focus`, `include`,
  `exclude`, `window` are written by both recorders and read with defaults;
  `env` in particular may be withheld for privacy. `late_writes` stays
  Python-only and `records_dropped` Rust-only; `Trace.dropped_writes()` reads
  either.

**Amended 2026-09-03 (rung 2 shipped): the keys actually written.**
`docs/TRACE-FORMAT.md` §4 is now the authoritative, current list (this
section is left as written, design-time); the shipped converter
(`rust/cargo-sensorium/src/convert/meta.rs`) writes, beyond the
language-neutral required set: `invocation`, `pid`, `ppid`, `exe`,
`toolchain`, `rustc_path` (an addition against this section's original
list), `cargo_args`, `profile`, `tool_hash`, `driver_version`,
`instrumented_units`, `uninstrumented` (workspace-scoped via the manifest's
`workspace_root`), `skipped` / `spawns` / `unreached_files`
(registered-unit-scoped, not workspace-scoped — `docs/TRACE-FORMAT.md` §4
states why the two scopings differ), `units_refused`, `exit_status_basis`,
`exit_signal`, `wall_start_ts` / `wall_end_ts`, `records_dropped`,
`seq_gaps`, `panics_unrecorded`, `panics_outside_frames`, `child_runs`,
`manifests_unscoped`. `partial` (this section's original list) did not
ship — `?`-site partial instrumentation is rung 3's (§3.3 is undone this
rung), so no manifest carries it yet. The `dbg` value tag (§5.3) rides in the
RETURN payload's `value` key beside the required `outcome`; a Rust
RAISE/HANDLED payload carries `loc` (where a panic fired), not the `chain`
key this section's design-time text names — chain identity is rung 3's, with
`?`.

### 5.2 Capabilities and command gating

`capabilities = {line, locals, return_value, tasks, threads, children, output,
object_identity, refocus}`. Each query command declares what it needs;
`flow` on `line: false` says `no LINE events — recorder sensorium-rt 0.1.0
declares line: false`, `flow --object` refuses on `object_identity: false`,
`refocus` prints a blind-spot line when either side's `output` is false
instead of passing `_output_difference` on two empty tables (F32). Absent
`capabilities` on a non-python recorder is a refusal, never "full".

### 5.3 Enumerations (F15)

Pinned with one conformance vector each: event kinds; `frames.kind` (Rust
writes `"function"` for fns and closures — never NULL, which renders as
`[None]`); `closed_by ∈ {return, unwind}` (a panic is `unwind` with
`unwind_exc = {"type": "panic", "msg", "serial", "oid"}`; `"panic"` as a
`closed_by` value renders as a false ` (open)`); payload keys per event kind
per language (`oid` is Python-only; `type` and `msg` are required by
`fmt_exc`; Rust RAISE/HANDLED carry `chain` and `outcome`).

### 5.4 Code identity (F16, F18, F26)

`code_objects.qualname` is the FILE-LOCAL path in Python's shape: inline
`mod` nesting + enclosing impl type + fn — `Type::method`, `tests::setup`,
`outer::{{closure}}` — computed by `syn` from the file, no `module_path!()`.
`file` is absolute like `co_filename`; the root-relative form belongs to the
fingerprint basis only, as today. Module identity lives in `file`, exactly as
Python disambiguates two `class Foo` by `co_filename`; the module path is
kept in the manifest for `--focus` resolution only.

### 5.5 Ordering and identity

`events.id` is causal order across threads within a process (§4); `ts_ns` is
monotonic; frame ids are unique per trace; thread serials are per process,
main = 1; task ids are per trace. Conformance vectors: a two-thread interleave
whose event ids must alternate; a trace whose main thread emits nothing.

### 5.6 Conformance vectors

`docs/trace-format/vectors/`: one `.db` per enumeration value and per
required-key rule, a format-4 trace with every witness capability false whose
`info` must print the declared-not-witnessed lines, a trace missing a
required key that `Trace.open` must refuse, and the two ordering vectors. Both
recorders' test suites read the same vectors.

## 6. Query-layer changes

- **Reader performance (F14).** Measured today: `info` 54 s on a 93k-event
  bloomery trace, 281 s at 200k, because `unframed_calls` LEFT JOINs `frames`
  on the unindexed `call_event_id` (one frames scan per CALL). Fix in
  `reader.py` only: `WHERE … AND e.id NOT IN (SELECT call_event_id FROM
  frames)` — verified 53.9 s → 0.011 s, row-identical; and `children()` /
  `roots()` / `frame_containing()` served from a lazily built per-connection
  parent map (0.25 s at 1M frames). No index becomes a contract requirement;
  indexes are an access path, not evidence.
- **`diff --ignore-moves` (F16, F18, F26).** Git-style rename detection at
  query time, both languages, no schema or stored-hash change: key both runs'
  code objects by `(file, qualname, kind)`; pair an A-only entry with a B-only
  entry when `(qualname, kind)` match and the pairing is unambiguous; recompute
  the thread and task streams with the pairing applied and compare. A
  qualname that is A-only under two or more files, or B-only under two or
  more files, is NOT paired: it is listed as unpaired and its events keep
  their recorded keys, so a divergence inside it is reported as DIVERGED —
  never "MATCH with an undetectable region" (amended 2026-09-02). Task
  streams are re-hashed at query time on both sides, because the stored task
  hashes use a root-relative file. Verdict wording: `MATCH modulo location —
  identical causal streams (n events) once N moved code object(s) are paired
  by qualname`, followed by a `moves:` block (`moved: helper  a.py -> b.py`,
  `added (only in B)`, `removed (only in A)`, `unpaired`). It never claims
  values, lines or timing. The header prints the key used so a reader can
  never mistake which comparison produced MATCH.
- **`exceptions` for `lang = rust` (F11, F21).** A Rust rule module with its
  own index, chain identity and dispositions behind the shared renderer
  (`Disposition`, header, tally, `--after` paging, `fmt_event`), dispatched on
  `meta["lang"]`. The brainstorm's "vocabulary swap" is withdrawn: the Python
  index reads `exc["oid"]` unconditionally (KeyError without it), lists only
  RAISE events (an `Err` born by `return Err(..)` — 107 sites in bloomery —
  and absorbed by a caller's `.ok()` would print "no exceptions recorded"),
  and rule 2 reports SWALLOWED for a frame that re-returns an `Err` without
  `?`. Rust dispositions are defined on frame OUTCOMES (§3.2): a frame RAISES
  iff it closes `err` (observe the boundary, not the constructor);
  HANDLED only at the written sink list; SWALLOWED iff a HANDLED sink absorbed
  the chain and no later RAISE of the chain occurred before its frame closed
  `ok`; AMBIGUOUS the moment an `Err` value leaves the enumerated grammar
  (bound to a name and stored, passed by value to a dependency fn, dropped
  without `let _`) — never `propagated` by default; PANICKED; and
  RETURNED-TO-HARNESS for a test fn that returned `Err`. Chain identity is a
  per-thread serial minted at the origin RAISE and carried through consecutive
  `?`/return-err sites; two distinct `Err`s interleaved in one chain window
  merge into AMBIGUOUS and the corpus pins that.
- **`refocus` for `lang = rust`.** Re-invokes `cargo sensorium --refocus-of
  <run>` with the recorded `cargo_args`, deeper tier/focus env, and compares
  the new process's trace; the sameness check gains the binary hash
  (`source_hashes` covers the instrumented `.rs` files, `Cargo.toml`,
  `Cargo.lock`, and the test binary), which is stronger than Python's
  env-and-git comparison. Blind spots printed: output not recorded, threads
  from dependency code unnamed.
- **Vocabulary.** ~50 renderer sites that say coroutine/generator/asyncio task
  move to a per-language table keyed on `meta["lang"]`; Rust says fn/closure,
  test, spawned thread. Two languages, only the terms in use.
- **`runs` and `info`.** `runs` groups by `invocation`; `info` prints
  recorder, lang, capabilities, instrumented/uninstrumented/skipped/partial
  units, children run ids, live threads.
- **`tree` and `frame` must render the CALL payload's `unread` marker (added
  2026-09-02, rung 1 measured).** A Python-core gap, surfaced by Rust because a
  Rust trace is *entirely* locals-free. Same trace, same event: `sensorium
  grep` prints `e11 CALL load_config() <unread: locals>`, while `sensorium
  tree` prints `f47 e66 default_probe_timeout_secs() -> ?` and `sensorium frame
  f11` prints `args: (none)` (spike §5.6). `(none)` reads as "called with no
  arguments"; the truth is "arguments were never read" — the named bug class, a
  value that looks like a measurement and is not. Mechanically:
  `tree_cmd.frame_line` renders CALL args without reading the payload's
  `unread` key; only `grep`'s `fmt_event` reads it (spike §5.6). The fix is
  rung-2 Python work and is not Rust-specific — it is wrong on a Python trace
  recorded with `capabilities.locals = false` too.
- **The reader's prose must key off `meta.lang` before a Rust trace is handed
  to anyone (added 2026-09-02, rung 1 measured).** Verbatim from `sensorium
  info` and `sensorium diff` on a real bloomery *Rust* trace: `python ?`; "0
  causal events outside any **asyncio** task"; "each thread row covers the
  events that ran in no **asyncio** task"; "threads started: 26 besides the
  main one, **through Python's own threading/_thread**" (spike §5.5). None of
  that is true of a `sensorium-rt` trace, and the `threading/_thread` line is a
  positive claim about provenance the trace does not carry. This is the
  "Vocabulary" bullet above, promoted from a renaming to a correctness fix, and
  it is why §11 moved the per-language table into rung 2.

**Amended 2026-09-03 (rung 2 shipped): what landed against this section's
list, and what did not.** Done: the lang-keyed vocabulary table
(`src/sensorium/query/vocab.py`, `terms(trace)`), the CALL payload's `unread`
marker rendered in `tree` and `frame` (not only `grep`), `runs` grouping by
`invocation` with per-member `exit:`/`events:`/`cmd:`, the exit-status
rendering (`waited`/`unwitnessed`, never a bare `None`), and refusals for
`exceptions` (needs the Rust disposition rules, rung 3), `refocus`
(`capabilities.refocus: false`, rung 4), and `watch`/`flow`
(`capabilities.line: false`, rung 4) — each printing why and exiting 2, never
answering from a capability the trace does not carry. `diff --ignore-moves`
ships exactly as this section specifies, including the `moves:` block and the
never-claims-values-lines-or-timing rule; it is what E5 (§8, §10) measured
against. **Not done, carried to the rung-3 inbox**
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md`): the Rust
`exceptions` dispositions and chain identity (rung 3, as this section already
said); `refocus` for `lang = rust` (rung 4, as this section already said);
`diff --task` help text (still Python-worded for a Rust trace);
`vocab.interp_line`'s `or "?"` fallback (no fixture reaches it, so it is
unverified); the Python `live_threads` line's pre-existing asymmetry this
section did not touch.

## 7. The Rust honesty ledger: `rust/HONESTY.md` (F21)

Written before the transformer, one section per promise, each with the corpus
case that could falsify it:

- Dispositions and chain identity (§6), with the AMBIGUOUS-by-default rule.
- Cannot see: dependency internals; mutation through a long-lived reference;
  `?` in macro arguments; closure-internal flow of an `Err` that never crosses
  a frame; threads spawned by dependency code (unnamed); a fn skipped as
  `const`/`extern`; a unit that fell back; process::exit and abort (frames
  open, `incomplete`); program output under libtest.
- Preserved by construction, tested: line numbers, file paths, panic
  locations, temporary lifetimes and drop order at every wrapped site,
  cargo freshness, plain builds untouched.
- Cost is a reported fact, never a gate (README's `--bench` rule).

## 8. Pre-registered endpoints and kill criteria (F19, F17, F18, F21)

Written into the plan before the first line of the transformer; each names its
lens.

| Id | Measurement | Lens | Kill / floor | Measured (rung 1, 2026-09-02) |
|---|---|---|---|---|
| E0 | Sizing spike: events per test binary for `cargo test -p bloomery-daemon`; `info`/`diff` latency at that volume after the §6 reader fix | dev profile, tier `call` | `info` > 60 s on the largest binary → finer trace unit, stop and re-plan | **0.03 s** — the largest of the four medians (`info`/`diff` × `--lib`/`config_test`, n=3 each) — **PASS** |
| E1 | Overhead: `corpus/rust/_bench` `call_dense` (fib 30) and `work_between_calls`, plain vs tier off/call/full; bloomery `cargo test -p bloomery-daemon` wall, plain vs tier-off vs tier-call | dev profile, rt at opt-level 3 | tier-off > 1.5× plain wall → tiering becomes a cargo feature and refocus a rebuild (the trade the brainstorm named); reported: `--no-run` time and binary size | **×0.9975** off/plain (n=5 per arm, 0 dropped); call/plain ×1.0103 — **PASS** |
| E2 | Coverage on bloomery: instrumented fn items / fn items; instrumented `?` sites / `?` sites; units that fell back | workspace src + tests | floor 98% of fn items (5 const of 756 excluded by rule), 95% of `?` sites; any fell-back unit is a finding, not a pass | **100.0%** of fn items (2051/2051 eligible), **0** units fell back — **PASS** (see the footnote) |
| E3 | False DIVERGED: 20 identical re-runs of one bloomery-daemon test binary, default `--test-threads`, same binary hash and env; `diff` each against the first | per-task basis | DIVERGED 0/19 and REFUSED 0/19; any DIVERGED = comparator wrong, stop | not measured (rung 2) |
| E4 | `refocus` MATCH rate on the 7 `pager_*_test.rs` FakeSubstrate files, per test with `--exact`, expected-MATCH list written first | tier call → full | a MATCH on the expected list only; an unexpected DIVERGED is a finding | not measured (rung 4) |
| E5 | Split verification (§10): identical behaviour and execution order → MATCH modulo moves; one planted behavioural change (two call sites swapped) → DIVERGED naming the step | `diff --ignore-moves` | planted change reads MATCH → the verifier is void, the split is not trace-verified | not measured (rung 2) |
| E6 | False SWALLOWED on the Rust corpus | Rust exceptions rules | 0; any false accusation stops the rung | not measured (rung 3) |
| E7 | Line/path preservation: rewritten build's panic locations, `file!()`, backtrace frames byte-identical to the plain build on a probe with known panics | conformance | any difference stops the rung | **0 differences** across 4 checks and 2 arms (off, call), probe workspace — **PASS** |
| E8 | Freshness and non-contamination: edit → rebuild; no edit → Fresh; plain `cargo test` after instrumented → Fresh AND uninstrumented (a sentinel the runtime prints) | cargo 1.96 | any contamination stops the rung | **0 failed checks** — (a), (c)+sentinel, (d) on bloomery; (b) on the probe — **PASS** |

Overhead multipliers are reported beside Python's (2.7× / 124.5× / 6 µs per
event) and never gate; the verifier's probe already shows tier-off is not
free on call-dense dev code (×3.4–4.9 on `fib(30)`, ×1.02 on ordinary code),
which is why E1's lens is bloomery's wall clock. *(Measured 2026-09-02 at
E1's own dev-profile lens: **×5.934** on `fib(30)`, outside the design
review's ×3.4–4.9 range and in the same direction — spike §3 E1. The
suite-wall reading is ×0.9975.)*

**The measured column was added 2026-09-02**; every cell in it quotes §4 of the
findings document, which prints the kill rule verbatim beside the number.
"not measured" is neither a zero nor a pass: those four endpoints belong to
later rungs (§11), and the spike says what its five PASSes do not license —
"None of them says the recorded trace *answers a debugging question* about
Rust, and none of them was measured on a second workspace."

**E2 row — dated footnote (2026-09-02).** Two defects in the row as written,
neither of which moved the floor, both recorded before any E2 number was read:

- *The derivation's item count is wrong.* "5 const of 756 excluded by rule" —
  the transformer's own census counts **744** fn items in `crates/*/src` (2056
  across `crates/*/src` + `crates/*/tests`); 756 was a mis-transcription. The
  corrected derivation is 5 `const fn` of 744, i.e. **739/744 = 99.33%**
  expected — the same figure to two decimal places, for the same reason, so
  **the 98% floor stands exactly as pre-registered** (findings §1 erratum).
- *The lens and the denominator name different file sets.* This row's
  denominator is "workspace src + tests" (2051 eligible fn items) while the
  spike's lens is `cargo test -p bloomery-daemon`, a build that compiles only
  **1723** of them; crossing the two yields 1723/2051 = **84.0%**, a number
  about cargo's package selection rather than about the transformer. The fix
  was declared before the run and a supplementary workspace-wide instrumented
  `--no-run` was placed last in the protocol, so numerator and denominator span
  the same files: **2051/2051, 1723/1723 and 739/739 — 100.0% three ways**
  (findings §3 denominator table, §4 E2, §5.14). A reader who prefers the other
  reading has one command in §4 to re-render it.
- *`?`-site coverage is not measured.* The spike's tier is `call` only, so this
  row's second floor (95% of `?` sites) moves to rung 3 with §3.3.

Three further facts about that second defect, stated because a footnote that
omits them reads as a number chosen after the fact (findings §1, *Erratum
continued*):

- *The pre-registration excludes the crossed reading on its own terms.* The
  spike's E2 row defines its denominator as a count "**counted by a syn census
  over the same files**". A numerator from a `-p bloomery-daemon` build against
  a whole-workspace denominator is not the same files, so 1723/2051 violates
  the pre-registration **as written** — independently of what number it yields.
- *The run was one detached process, and the supplementary build was in the
  script before it launched.* `results.json`'s `steps` records
  `[15:40:06] E2[daemon build]: distinct=1723 …` and, as the last measured step
  of that same process before `cleanup`,
  `[15:45:02] E2[workspace build]: distinct=2051 …`. The workspace-wide
  `--no-run` was already in the runner — disk-guarded, after every timed arm —
  when the process started. Nothing was added mid-run; no arm was re-rolled.
- *The runner's DEFAULT assembly renders the crossed reading, and the headline
  was selected after the run.* The assembler defaults to
  `SENSORIUM_E2_DENOM=all`, which pairs the one-package numerator with the
  whole-workspace denominator: 1723/2051 = 84.0%, **below this row's floor**.
  The committed `results.json` carries `"e2_headline_denominator": "workspace"`,
  chosen by a controller ruling 2026-09-02 (ledger, local-only) after the run.
  **The floor's verdict is neutral either way**: the pre-registered lens's own
  same-file reading, **1723/1723 = 100.0%**, passes with no supplementary build
  at all.

**Rung 2 measured column — dated addition (2026-09-03).** The table above
still reads "not measured (rung 2)" for E3 and E5, and its E2/E7/E8 rows are
rung 1's numbers on the *mechanics spike*, not on product code — left as
written, because nothing above is wrong, only superseded. Rung 2
pre-registered E2 again as **E2′**
(`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` §1,
re-read because the transformer changed: exit wraps, spawn rewrite) and
measured all five endpoints on the bloomery **clone**, product code,
`sensorium-rt`/`sensorium-transform`/`cargo-sensorium` 0.1.0:

| Id | Rule (§1 of the acceptance document, verbatim) | Measured | Verdict |
|---|---|---|---|
| E2′ | floor 98% of eligible fn items; any fell-back unit stops the rung | **100.0%** — 2051/2051 eligible fn items (workspace-wide), 1723/1723 (package build); 0 fell back | **PASS** |
| E3 | DIVERGED 0/19 and REFUSED 0/19 | **0 DIVERGED, 0 REFUSED** over 19 diffs of 20 identical re-runs, one binary, sha256 unmoved | **PASS** |
| E5 | A/B MATCH modulo location, every task paired by name; A/C DIVERGED naming the step | A/C **DIVERGED**, naming `Journal::open` vs `ImageStore::new` inside the swapped fn — the negative control holds. A/B **DIVERGED**: 28 code objects paired, 0 added, 0 removed, all six `task::registry::tests::*` tasks paired — but **4 spawned child tasks unpaired by name** (their spawn site moved with the split; stream hashes identical pairwise) | **STOP** |
| E7 | any difference in a panic location, `file!()`/`line!()`, a backtrace frame, a `test …` line, or `test result:` → STOP | **0 differences**: (a) 6/6 checks on the probe (44/44 `mechanics.sh` checks); (b) 0/56 masked lines on the clone, instrumented arm wrote 60 spool files (not vacuous) | **PASS** |
| E8 | any failed check → STOP | **0 failed checks of 5** — (a), (c)+sentinel, (d), (b) on the clone, expected `Fresh` set asserted each time | **PASS** |

Four endpoints pass on mechanics; one — E5, the only endpoint that asks
whether a trace can *verify a refactor* — reads **STOP**, on task NAMING, not
on the causal streams `--ignore-moves` pairs (§10, §11 below carry the
consequence). Source: the acceptance document's §3 (raw numbers) and §4 (the
verdicts, hand-written against the pre-registered rules).

## 9. Testing story (the brainstorm's unwritten section 4; F22)

- **`sensorium-transform` golden tests**: input `.rs` → spliced output, byte
  exact, one per rule in §3, plus "line count unchanged" asserted on every
  golden; property test: splice(x) parses and has `lines(x)` lines.
- **Probe workspace** (`rust/probes/ws/`: lib + bin + build script +
  proc-macro member + a non-member path dep + two integration files, one that
  spawns the bin): the cargo-mechanics facts in §2 as tests — wrapper scope,
  passthrough, coexistence of artifacts, freshness (E8), mirror resolution of
  `include_str!` across crates, `#[path]`, unit/manifest join, child process
  spool placement, libtest thread naming under both `--test-threads` settings.
- **`sensorium-rt` tests**: reentrancy, `catch_unwind` capture, spool
  durability under a leaked blocked thread and under `abort()`, sequence
  monotonicity across threads, task naming, `spawn_child` naming.
- **Conformance vectors** (§5.6) read by both suites.
- **Rust corpus** `corpus/rust/<case>/{Cargo.toml, src/main.rs,
  questions.yaml}` run by `run_corpus.py` with `program: cargo`; every case
  pre-registers `why_logs_fail` naming which of `dbg!`, `RUST_LOG`,
  `RUST_BACKTRACE` fails and why. Ports (9): `silent_swallow` (`.ok()` /
  `let _ =`), `double_call`, `near_miss`, `nondeterministic`,
  `none_propagation` (Option), `pass_vs_fail`, `unit_mismatch`,
  `wrong_branch`, `stale_cache` (`Arc<Mutex>`). Refusal cases (2): `aliasing`
  and `stale_cache --object` expecting the `object_identity: false` refusal
  text. Rust-only (7): through-reference mutation (`watch` shows the site
  not-captured, never `held`); a fell-back unit (`info` names it, `tree` on
  its fns refuses); panic (`closed_by unwind`, `unwind_exc.type panic`);
  abort (`incomplete: true`, `diff` REFUSED); libtest (MATCH across
  `--test-threads=1` vs `8` under tasks-as-tests, with the counter-truth that
  without tasks the verdict is REFUSED); spawned-thread task (a worker
  holding a lock inside a test is named in the verdict); interleaved chains
  (two `Err`s in one window → AMBIGUOUS, never a false SWALLOWED). The 10
  async/generator cases have no analogue on a zero-async target and are not
  ported.
- **CI**: a stable-Rust job builds `rust/`, runs the golden, probe-workspace
  and rt tests, then `corpus/rust`; the Python matrix stays as is and gains
  the vector suite.

## 10. Acceptance targets

**Rung 0 (Python core, before any Rust):** re-verify today's Python-trio
split with the new instrument instead of by eye:

```
sensorium diff --ignore-moves 20260901-210300-edca03 20260901-210520-7f8854
```

Expected — **amended 2026-09-02, after the run, against the adjudicated
result; the original expectation of `MATCH modulo location` was wrong**:
`DIVERGED at causal step 451`, at the first change of TEST COLLECTION ORDER,
with all 53 moved code objects paired first and the `moves:` block standing
as the relocation table (the moved list exactly the classes and methods the
e209ed9 file table relocated; the new files' import-time frames reported
under `module frames not compared`). The step it names is A's `e454 CALL
StampAuditTests` inside `test_recompute_v2.py`'s import against B's `e462
RETURN <module>` of that same file — the class now lives in a new file that
`unittest discover` imports LATER, so the split changed the order the tests
were collected and run in, not only where they live. A sequence comparison
must report an order change: that is the difference between this instrument
and e209ed9's own verification, which compared event COUNTS (`93,273 →
93,283`, `+5 CALL`) and is order-blind by construction. Evidence, verbatim
output and drill-ins:
`.superpowers/sdd/2026-09-02-sensorium-rung0-python-prep/task-7-acceptance.md`.
A MATCH on this pair would require an order-INSENSITIVE per-unit comparison —
the tests-as-units shape of §4, where each test is a unit of work with its
own `task_fingerprints` row and the units are compared as a multiset —
recorded here as a candidate, not built, and not a rung-0 deliverable.
Today's plain `diff` on the same pair says `DIVERGED at causal step 426`, at
the first moved module rather than at the order change. E5's planted change
on a throwaway copy → DIVERGED naming the step. `sensorium info` on the 93k
trace under 1 s.

**Rung 2 (the first Rust use):** the registry.rs split.

```
cargo sensorium test -p bloomery-daemon --lib -- task::registry      # before the split
cargo sensorium test -p bloomery-daemon --lib -- task::registry      # after
sensorium diff --ignore-moves <before> <after>
```

Expected: `MATCH modulo location: N moved, 0 added, 0 removed` (Rust adds no
module-level frames, so unlike the Python trio there is no `+5 CALL`), every
`task::registry::tests::*` task paired by name, `info` counts identical, and
E5's planted swap → DIVERGED naming the step. **This target assumes the split
does not change test order**, which is why it is stated for a SOURCE file:
moving items between source files leaves libtest's collection alone, where the
rung-0 Python trio's TEST-file split moved tests between discovery units and
duly read DIVERGED. If the registry.rs split moves `#[test]` fns between
files, expect the same DIVERGED for the same reason, and read it as the
instrument working. Then the same for `pager.rs`,
`drift.rs`, `task_loop.rs` with `--test` selectors chosen from the tests that
import them.

**Amended 2026-09-03 (rung 2 measured; the expected verdict above is
superseded, not deleted).** The registry.rs split ran exactly as this section
specifies, and its measured result is **not** the `MATCH modulo location`
this section expected — the measured verdict is `DIVERGED`, and the
divergence is *not* a test-order change (libtest ran the same six
`task::registry::tests::*` in the same order on both sides, and all six
paired by name). What diverged is four *spawned child* task names, because
`spawn_task`'s own call site moved from `registry.rs:769` to
`registry/mod.rs:248` and `spawn_child`'s derived name (§3.5) embeds the
spawn site. This section's own escape hatch ("if it is a test-order change …
read it as the instrument working, else STOP") therefore resolves to
**STOP**, exactly as the acceptance document's pre-registered decision rule
(E5, §1) requires. The planted-swap half of the target held without
qualification: `diff --ignore-moves` on A/`e5-planted` read `DIVERGED`,
naming `Journal::open` (A) against `ImageStore::new` (B) at the swapped step
— the verifier is not void. Full evidence, all three verbatim `diff` outputs
and the file-by-file split table:
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` §3
(E5) and §4. This is a design gap in what a spawned task's NAME is built
from, not a bug in `--ignore-moves`'s pairing (which paired all 28 non-spawn
code objects correctly) — see §11's rung-3 entry decision below.

## 11. Order of work (rungs)

0. **Python core prep** — reader fix (§6), `diff --ignore-moves` with the E5
   mutation test, format-4 meta contract on the Python writer and reader with
   the one-choke-point refusal, `docs/TRACE-FORMAT.md` + vectors, capability
   gating. Acceptance: §10 rung 0. Version 0.5.0. Plan:
   `docs/superpowers/plans/2026-09-02-sensorium-rung0-python-prep.md`. The
   per-language vocabulary table moves to rung 2: no Rust trace exists to
   render yet, and the terms are the recorder's to define.
1. **Mechanics spike (throwaway, pre-registered E0/E1/E7/E8)** — workspace
   wrapper + mirror + rt linkage + call/return tier only, no `?`, no locals;
   probe workspace and bloomery. Its output is the E1 decision (compile-once
   vs cargo feature) and the E0 trace unit. Kept only as evidence.
   **DONE 2026-09-02 — E0, E1, E2, E7 and E8 all PASS** (§8's measured column;
   E2 was added to the spike because the call tier makes it measurable). Plan:
   `docs/superpowers/plans/2026-09-02-sensorium-rung1-mechanics-spike.md`.
   Findings: `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`.
   The three decisions it settles (findings §4):
   - **Compile once, gate at runtime** — ×0.9975 against a ×1.5 rule.
     "Tiering does not become a cargo feature and `refocus` does not become a
     rebuild." Stated with its limit: the same gate costs ×5.93 on `fib(30)` at
     opt-0, so the decision re-opens the first time a call-dense suite is the
     target (§3.7, amended).
   - **One test binary — one process — is the trace unit**, with libtest's
     test threads as tasks; 0.03 s to `info` or `diff` one, against a 60 s
     budget. A whole invocation is also carryable at these sizes (119
     processes, 132 344 events, 22 MB, 22.7 s to convert), so "the choice of
     the binary is about *what a question is asked of*, not about what the
     reader can carry".
   - **GO for rung 2 on mechanics** — 0 output differences, 0 failed freshness
     checks, 0 fallbacks, 100.0% coverage; "the mirror +
     `RUSTC_WORKSPACE_WRAPPER` design is not reworked before rung 2".
   What the PASSes do not license, verbatim: "None of them says the recorded
   trace *answers a debugging question* about Rust, and none of them was
   measured on a second workspace. Rung 2 starts with the gaps in §5, not with
   these five PASSes." The spike's code is parked on branch
   `spike/rust-mechanics` and is never merged; only this evidence lands.
2. **Recorder v1** — frames with outcomes, tasks, `spawn_child`, panics,
   spools, converter, `runs`/`info`/`tree`/`frame`/`grep`/`diff` on Rust
   traces, rust/HONESTY.md, conformance vectors, corpus ports that need no
   `?`. Acceptance: E3, E5 on registry.rs, E7, E8. **Entry condition added
   2026-09-02:** the rung-2 gaps in the findings' §5 are this rung's inbox —
   the recorder ones (`exit_status` borrowed, spool tails lost, empty
   `source_hashes`, no output), the Python-core ones now carried in §6
   (`tree`/`frame` `unread`, language-keyed prose), and the design questions
   (child-process linkage, per-unit site identity, unnamed spawned threads).

   **Amended 2026-09-03: rung 2 is DONE-WITH-STOP.** E2′, E3, E7, E8 read
   PASS; E5 reads STOP (§8, §10 above; full evidence in
   `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`).
   The pre-registered consequence is taken as written: the PR ships the
   implementation and the evidence, ending at a findings document rather than
   a clean GO, and E5's fix becomes a **rung-3 ENTRY DECISION for Brice**
   rather than a rung-2 patch, because it is a choice among designs, not a
   bug fix:

   - **(a)** project task names through `moves` the way code-object keys
     already are;
   - **(b)** name a spawned task by something a move does not change — the
     enclosing fn's qualname plus an ordinal (`<parent> :: spawn@<qualname>#k`)
     instead of a file:line;
   - **(c)** treat unpaired-by-name tasks whose *projected streams* hash equal
     as a move in the verdict, rather than as an addition and a removal.

   These three are stated neutrally; **the controller's recommendation is
   (b)**, because it is stable across exactly the kind of move E5 tested (a
   file split) the same way code-object keys already are, and it changes no
   `diff` output for a workspace that never moves a spawn site. The rung-3
   inbox (`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md`)
   carries this decision first, ahead of `?`/sinks/arm work, because rung 3's
   own corpus cases will spawn tasks and inherit whichever answer Brice
   picks. That document also carries the smaller deferred items this rung's
   review rounds collected (mutation-test gaps, doc precision, a file at its
   800-line limit) — none of them block the entry decision above.

   **Decided 2026-09-03 by Brice: option (b).** Executed as the rung-3 entry
   slice (plan `docs/superpowers/plans/2026-09-03-sensorium-rung3-entry-spawn-names.md`,
   endpoint E5′).
3. **Err flow** — `?`, sinks, arm classification, closures, Rust `exceptions`
   rules, corpus swallow/panic/interleave cases. Acceptance: E6.
4. **Focus tier** — LINE/locals under `--focus`, `watch`/`flow`, driver-side
   focus resolution, `refocus` via re-invocation, reentrancy, E4, the
   through-reference and fell-back corpus cases.
5. Later — batch `diff` across an invocation; smithy-comp lifecycle.

Each rung is its own plan (writing-plans skill) and its own PR; rung 0 is a
Python-only PR and ships before rung 1 starts.

## 12. Rulings requested from Brice

**All five RULED 2026-09-02 by Brice, as recommended: per-process traces,
RETURN values carried, format bump to 4, the 1.5× threshold for E1, rung 0
ships first as a Python-only PR.**

1. **Trace unit** — one trace per OS process grouped by invocation (this
   spec), or one merged trace per invocation with a `processes` dimension
   pushed through every reader. Recommendation: per process.
2. **RETURN values** — carried via the exit-operand wrap (this spec) or
   dropped for v1 with `return_value: false`. Recommendation: carry them;
   the wrap is the same verified form as `try_site!`.
3. **Format bump 3 → 4** with the stated cost to old readers. Recommendation:
   bump.
4. **Compile-once vs cargo feature** is decided by E1, not by ruling; the
   ruling requested is the 1.5× wall-clock threshold itself.
5. **Rung 0 ships first**, as a Python-only PR, and the Python-trio
   re-verification is its acceptance. Recommendation: yes.

## 13. What changed against the 2026-09-01 brainstorm, and why

| Brainstorm said | This spec says | Finding |
|---|---|---|
| `RUSTC_WRAPPER` gated on `CARGO_PRIMARY_PACKAGE` | `RUSTC_WORKSPACE_WRAPPER`, versioned path, passthrough list | F1, F8, F24 |
| rewrite each `.rs` to tmp | workspace-root mirror under `target/sensorium`, argv unchanged, splice at byte offsets | F2, F7, F28 |
| per-crate manifest, bare 32-bit site id | manifest per `-C metadata` unit, `unit:8 | site:24` | F3, F33 |
| "runs the built binary"; `diff` needs no Rust work | cargo stays the runner; one trace per process; tests and spawned threads are tasks | F4, F10, F13, F17, F25, F29, F31 |
| RAISE at `?` "with the Err value", no form given | in-place `try_site!` match-wrap; `let`-hoisting forbidden | F5 |
| HANDLED at every `.ok()`/`unwrap_or`/`let _`/`if let Err`/`Err` arm | arm classification; Option never emits; place-expression `let _` skipped | F6 |
| RETURN from the guard's `Drop` (no value) | guard is the sole emitter; exit operands stash value and outcome | F30 |
| `exceptions` ports with a vocabulary swap | Rust rule module behind the shared renderer; dispositions on outcomes; AMBIGUOUS by default | F11, F21 |
| `frames.kind` NULL, `closed_by = panic` | `kind = function`, `closed_by = unwind` + `unwind_exc.type = panic` | F15 |
| qualname = `module_path!()` + impl | file-local Python shape; module path only in the manifest | F16, F18, F26 |
| meta: new keys only | required-key table, witness keys bound to capabilities, refusal at open | F12, F20 |
| per-thread spool, no exit rule | `MAP_SHARED` spools, `THREAD_END`, live threads derived | F27 |
| no reentrancy rule, `output` capability | capture depth guard + `catch_unwind`; `output: false` under libtest with a refocus blind-spot line | F32 |
| focus decided at runtime from a wrapper-side manifest | driver resolves names to site ids after the build | F33 |
| "faster than Python", "near-total coverage", "predictable branch" | E0–E8 with kill criteria; cost reported, never gated | F19 |
| no section 4 | §9 testing story, §7 ledger, §10 acceptance | F21, F22 |
| reader cost absent | `info` 54 s → 0.01 s reader fix in rung 0 | F14 |

### Rung-1 deltas: what the measurement changed in this spec (2026-09-02)

Every row is a sentence of this spec that rung 1 falsified or sharpened. The
evidence column names a §3 number, a §4 decision or a §5 gap of
`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` — §5.21–29 of that
document being the addendum that carries the spike's own evidence for the rows
below. Where the evidence is a ruling rather than a measurement the cell says
*controller ruling 2026-09-02 (ledger, local-only)*; no row cites a path this
repository does not carry.

| This spec said | Rung 1 measured | Evidence |
|---|---|---|
| `--remap-path-prefix <mirror>=<workspace>` is "appended only as belt and braces" (§2.2) | **Load-bearing**: without it backtraces print mirror paths. E7's 0 differences was measured *with* it | findings §5.21; §4 E7 |
| one workspace-root mirror (§2.2) | **One mirror per unit**, `mirror/<-C metadata>/`. A shared mirror let a crate root's lib and `--test` twins overwrite each other's `__SENSORIUM_UNIT` static — wrong-unit attribution, ~1 in 3 under `-j16`, invisible to E7 and E8 | findings §5.22 |
| the wrapper runs "for every workspace member … and for nothing else" (§2.1) | **rustdoc bypasses it**: the linkage must go through `RUSTDOCFLAGS`, and doctest processes DO spool, from a `/tmp/rustdoctest*/rust_out` deleted before conversion | findings §5.23, §5.11 |
| `sensorium-rt` built into the target workspace's `deps/` (§2.3) | Rung 1 built it in the spike workspace with `-L dependency=…`; **two `libc` crates coexisted and rustc accepted it**; 0 units fell back across 9 + 77 + 108 units | findings §5.24; §3 E2, §4 E2 |
| `cargo test -p bloomery-daemon` "runs 74 processes … 7 tests spawn the instrumented `flywheel_tool`" (§2.5) | **72 binaries run, 71 spooled, 119 processes** (48 `flywheel-tool` children), 132 344 events | findings §3, *Reported without a gate* |
| driver cost unstated (§2.5) | The driver must be **`--release`**: 0.025 s fixed vs ≈0.5 s debug | findings §3 E1 |
| `exit_status` is a per-process meta key (§2.5, §5.1) | **Not observable to the runtime.** Rung 1 borrows cargo's status for all 119 traces of an invocation, `exit_status_basis = "cargo"` | findings §5.1; §3 reports availability 0 |
| skip list = `const fn`, `extern "C"`, `macro_rules!` bodies (§3.2) | **Plus `async fn`, reason `async`** — the guard would live across `.await`. 0 async fns in bloomery, so E2's 100.0% is unaffected | controller ruling 2026-09-02 (ledger, local-only); findings §3 E2 |
| "predictable branch" per site — the brainstorm's phrase, replaced above by E0–E8 rather than by a number (§3.7) | **A real cross-crate call at opt-level 0**: `fib(30)` off ×5.934 (1.0595 → 6.2875 ns/call). Immaterial at suite granularity (×0.9975) and only there — a ≈1900× density gap | findings §3 E1, §4 decision 1 |
| `MAP_SHARED` spools keep pages on any exit (§4) | Rung 1's `BufWriter` spool **loses a live thread's tail silently**: 100 spools without `THREAD_END` in 3 of 119 processes; `exit()` flushes only the calling thread; `abort`/signal lose all. `MAP_SHARED` remains the design | findings §5.25, §5.2 |
| `truncated_count`, `records_dropped`, `source_hashes` as written keys (§4, §5.1) | **Asserted, not witnessed** in rung 1: no drop counter, and `source_hashes = {}` in every trace | findings §5.10, §5.3 |
| `spawn_child` names workspace-spawned threads (§3.5) | The need is measured: **4 of 57** emitting non-main threads in the `--lib` trace carry no name at all | findings §5.20 |
| `tree`/`frame` need no Rust-driven change (§6) | **They drop the CALL payload's `unread` marker that `grep` keeps** — `args: (none)` where the truth is "never read". A Python-core gap, now rung-2 work | findings §5.6 |
| E2's floor derivation, "5 const of 756 excluded by rule" (§8) | Census counts **744** in `crates/*/src` (2056 with tests) → 739/744 = 99.33%; and the row's denominator crossed file sets with the lens. **Floor unchanged**; 100.0% three ways | findings §1 erratum, §3, §5.14 |

### Rung-2 deltas: what shipping and measuring the recorder changed against this spec (2026-09-03)

Every row is a decision this rung's plan made (its own "Decisions this plan
makes" table) or a sentence of this spec rung 2 confirmed, sharpened, or
falsified while shipping product code — as against rung 1's *spike*, which
only measured mechanics. The evidence column names a decision id (D1–D10, the
rung-2 plan's own table) or a §3/§4/§5 number of
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`.

| This spec (or rung 1) said | Rung 2 decided or measured | Evidence |
|---|---|---|
| runtime rlib built into the target workspace's `deps/`, linked via `-L dependency=<spike release deps>` (§2.3, rung-1 amendment) | **Zero-dependency runtime**, compiled by the driver with one bare `rustc` line; linkage needs `-L dependency=<rt dir>` **in addition to** `--extern`, for both the wrapper and `RUSTDOCFLAGS`, whenever a unit's own dependencies are instrumented | D1; §2.3 amendment above; `rust/HONESTY.md` §8 item 7 |
| the spike's mirror lock: shared, 120 s timeout (§2.2, rung-1 amendment) | **One `flock` per unit, no timeout** — per-unit mirrors leave nothing shared to go stale | D2; §2.2 amendment above; E2′ 108/108 checked |
| `#[cfg_attr(.., path = ..)]` unevaluated, `unreached_files` declared (§2.4) | **Unchanged, still deferred** — 0 cases in bloomery | D3 |
| `exit_status` borrowed from cargo, `exit_status_basis = "cargo"` (§2.5, rung-1 amendment) | **A cargo runner role**: `waited` for every runner-started process (test binaries and doctests both), `unwitnessed` for anything a test spawned itself | D4; §2.5 amendment above; `waited`×71 / `unwitnessed`×48 |
| converter language undecided | **Rust**, `rusqlite` bundled — and its first shape committed a fsync per row, measured **1118.9 s** for one invocation before the fix landed | D5; acceptance §3.1 addendum; `docs/TRACE-FORMAT.md` §2 |
| async fns: skipped, reason `async` (§3.2, rung-1 amendment) | **Unchanged** — 0 `async fn` in bloomery, so E2′'s 100.0% is unaffected | D6 |
| children: parentage on disk, thrown away by the converter (§2.5, rung-1 amendment) | **N traces with a join key**: `capabilities.children = false` **and** `child_runs` linked by `ppid` — never neither | D7; §2.5 amendment above; 48 child runs named |
| site identity per-unit, un-merged (§2.4, rung-1 amendment) | **Merged at conversion** on `(file, qualname, firstlineno)`; `diff` still cannot separate two fns sharing a file and qualname at different lines (bloomery's cfg-gated `main.rs::run` twins) | D8; `rust/HONESTY.md` §7 |
| fingerprint file basis unresolved | **Workspace-relative** (stored), **absolute** for `code_objects.file`; `diff --ignore-moves` re-hashes the absolute string on both sides, at query time | D9; `rust/HONESTY.md` §7 |
| RETURN values: ruled "carry them" (§12), form undesigned | **Captured at tier `call`** via `ret()` (§3.2 amendment above); the 200-byte cap bounds `Debug` *formatting*, not std's collection walk (10⁶-element `Vec`: ≈10 ms with the cap, ≈8 ms without it — the counterintuitive direction, `rust/sensorium-rt/tests/values.rs`) | D10; acceptance §3, *reported without a gate* |
| exit form: `match (<e>) { __r => { … } }` (§3.2) | **Replaced by `ret()`** — the `match (<e>)` shape trips `unused_parens` under `#![deny(warnings)]`, measured while building the transformer | §3.2 amendment above |
| `spawn_child` naming, designed not shipped (§3.5) | **Shipped exactly as designed**, and its own site-in-name shape is what E5 measures as a gap: a spawn site that moves renames the task | §3.5 amendment above; E5 |
| §10 rung 2's expected verdict: `MATCH modulo location` on the registry.rs split | **Measured `DIVERGED`** — not a test-order change, but four spawned child task names whose site moved with the split | §10 amendment above; acceptance §3 (E5), §4 |
| §11 rung 2: entry condition only, no exit stated | **DONE-WITH-STOP.** E2′/E3/E7/E8 PASS, E5 STOP; the fix is a rung-3 entry decision for Brice among three options, stated neutrally, with the controller's own recommendation named separately | §11 amendment above; acceptance §4 |
