# Sensorium Rust recorder — reworked design

Date: 2026-09-01. Status: DRAFT for Brice's review. Supersedes the unwritten
design of the 2026-09-01 brainstorm session (sections 1–3 delivered in chat,
section 4 never written, no spec file).

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
Fresh. `--remap-path-prefix <mirror>=<workspace>` is appended only as belt
and braces. Never `/tmp`, never a per-file copy, never a rewrite of include
literals.

### 2.3 Linking the runtime (F24)

`sensorium-rt` is never in `Cargo.toml` (Cargo.lock stays untouched). The
driver builds `libsensorium_rt-<hash>.rlib` with the same rustc, target and
panic strategy at opt-level 3 into `target/<profile>/deps/`; cargo already
passes `-L dependency=<deps>` to every rustc invocation, so the wrapper adds
only `--extern sensorium_rt=<rlib>`. The runtime is optimised regardless of
the target profile because bloomery's dev-profile `cargo test` is the
workload (F19).

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

### 2.5 The run model (F4, F13, F23, F29)

`cargo test -p bloomery-daemon` runs 74 processes (lib harness, bin harnesses,
69 integration binaries, plus doctests), and 7 tests spawn the instrumented
`flywheel_tool`. Rules:

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
  `match (<e>) { __r => { ::sensorium_rt::stash_ret(SITE, (&&Probe(&__r)).cap()); __r } }`.
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
`<parent task name> :: spawn@<file>:<line>`, and sets the child's thread-local
task before running `f`. The child's events carry its own task id and its own
fingerprint, so a worker holding a lock inside a test is IN the verdict.
Threads spawned by dependency code (tiny_http's accept thread) get no name
and are compared as unnamed tasks by content multiset (arc-2b Ruling R4).

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

| Id | Measurement | Lens | Kill / floor |
|---|---|---|---|
| E0 | Sizing spike: events per test binary for `cargo test -p bloomery-daemon`; `info`/`diff` latency at that volume after the §6 reader fix | dev profile, tier `call` | `info` > 60 s on the largest binary → finer trace unit, stop and re-plan |
| E1 | Overhead: `corpus/rust/_bench` `call_dense` (fib 30) and `work_between_calls`, plain vs tier off/call/full; bloomery `cargo test -p bloomery-daemon` wall, plain vs tier-off vs tier-call | dev profile, rt at opt-level 3 | tier-off > 1.5× plain wall → tiering becomes a cargo feature and refocus a rebuild (the trade the brainstorm named); reported: `--no-run` time and binary size |
| E2 | Coverage on bloomery: instrumented fn items / fn items; instrumented `?` sites / `?` sites; units that fell back | workspace src + tests | floor 98% of fn items (5 const of 756 excluded by rule), 95% of `?` sites; any fell-back unit is a finding, not a pass |
| E3 | False DIVERGED: 20 identical re-runs of one bloomery-daemon test binary, default `--test-threads`, same binary hash and env; `diff` each against the first | per-task basis | DIVERGED 0/19 and REFUSED 0/19; any DIVERGED = comparator wrong, stop |
| E4 | `refocus` MATCH rate on the 7 `pager_*_test.rs` FakeSubstrate files, per test with `--exact`, expected-MATCH list written first | tier call → full | a MATCH on the expected list only; an unexpected DIVERGED is a finding |
| E5 | Split verification (§10): identical behaviour and execution order → MATCH modulo moves; one planted behavioural change (two call sites swapped) → DIVERGED naming the step | `diff --ignore-moves` | planted change reads MATCH → the verifier is void, the split is not trace-verified |
| E6 | False SWALLOWED on the Rust corpus | Rust exceptions rules | 0; any false accusation stops the rung |
| E7 | Line/path preservation: rewritten build's panic locations, `file!()`, backtrace frames byte-identical to the plain build on a probe with known panics | conformance | any difference stops the rung |
| E8 | Freshness and non-contamination: edit → rebuild; no edit → Fresh; plain `cargo test` after instrumented → Fresh AND uninstrumented (a sentinel the runtime prints) | cargo 1.96 | any contamination stops the rung |

Overhead multipliers are reported beside Python's (2.7× / 124.5× / 6 µs per
event) and never gate; the verifier's probe already shows tier-off is not
free on call-dense dev code (×3.4–4.9 on `fib(30)`, ×1.02 on ordinary code),
which is why E1's lens is bloomery's wall clock.

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
2. **Recorder v1** — frames with outcomes, tasks, `spawn_child`, panics,
   spools, converter, `runs`/`info`/`tree`/`frame`/`grep`/`diff` on Rust
   traces, rust/HONESTY.md, conformance vectors, corpus ports that need no
   `?`. Acceptance: E3, E5 on registry.rs, E7, E8.
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
