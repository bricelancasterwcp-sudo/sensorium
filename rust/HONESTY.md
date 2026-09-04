# The Rust recorder's honesty ledger

`sensorium-rt 0.1.0`, `sensorium-transform 0.2.0`, `cargo-sensorium 0.2.0` —
v1, the call tier. (`sensorium-transform` and `cargo-sensorium` moved to
`0.2.0` on 2026-09-03 for the `spawn_child` naming change in §3; `HONESTY.md`
was not versioned per-crate before this, so no prior edition of this line is
struck.)

Sensorium's founding rule is that **the instrument never answers from data it
does not have**. The Python recorder keeps its half of that rule in the
README's *What the answers claim*, *What a trace file holds* and *What
sensorium sees at all*. This is the Rust recorder's half, and it is written to
the same standard the standing ruling of 2026-08-20 set: a sibling recorder
carries its own honesty ledger, and multi-language support never softens the
core.

**How to read a section.** Each one states a promise, says **what in the trace
says it** — a manifest field, a meta key, or a line `sensorium info` prints —
and names **what could falsify it**: a corpus case or a test, by path. A
promise with no falsifier is not a promise, it is an assertion, and this
document does not carry assertions. The index at the end is the whole list in
two columns.

**Provenance.** Spec §7 requires this document *before* the transformer, so it
is written first and the code is written to it — not the other way round. The
design is
`docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md`; the
measurements it rests on are
`docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` (rung 1, cited
below as *findings §n*); the endpoints named E2′, E3, E5, E7 and E8 are
pre-registered in
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`. Where a
falsifier is a file that a later task of the rung-2 plan creates, the path here
is the name that task must use.

**What this version records.** Tier `call`: CALL and RETURN with an outcome and
a captured return value, panics, per-thread spools, tasks, and `spawn_child`
naming — for workspace crates, on Linux, on stable rustc, with no hand
annotation. Not `?` sites (rung 3), not locals or LINE (rung 4), not program
output. §8 is the list, with what declares each absence.

---

## 1. What a frame's outcome means

Every frame closes with exactly one outcome, carried in the RETURN event's
payload as `{"outcome": "ok" | "err" | "panic" | "none"}`.

- **`ok` / `err` are read from the value at the exit operand** — the tail
  expression, and every `return <e>` at closure depth 0, of a function whose
  return type is neither `()` nor `!`. `err` means that value was
  `Result::Err` *at the moment it crossed the function boundary*; `ok` means it
  was anything else, `Result::Ok` and non-`Result` values alike. This is a fact
  about the boundary, not about the body: an `Err` built and absorbed inside
  the function never shows as `err`, and an `Ok` that wraps a failure of some
  other kind is `ok`.
- **A function with nothing to return** (`-> ()`, or no return type) has no
  exit operand to probe. Its frame closes `ok` with the recorded value `()`
  when it returned normally.
- **`panic` comes from the panic hook, and where it does not, the trace says
  so.** The guard reads `std::thread::panicking()` at *both* ends of its frame —
  once at `enter`, once when it drops — and closes `panic` only on a
  false-to-true transition across the frame (**amended 2026-09-03**; it used to
  read the exit alone). A panic that begins while the thread is already
  unwinding aborts the process, so a frame a `Drop` opened *during* someone
  else's unwind cannot have panicked itself: it closes on its own outcome, which
  for the usual `-> ()` `Drop` body is `ok`. Before the amendment such a frame
  read `panic` although it had returned, and the converter then attached the
  *outer* panic's message and serial to it. Falsifier:
  `rust/sensorium-rt/tests/outcomes.rs::a_frame_entered_during_an_unwind_did_not_itself_panic`
  (scenario `panic-truncated-before-spool`, whose `EntersOnDrop` local opens its
  thread's first spool from inside the unwind).
  The hook — installed on the process's first recording `enter`, chained to
  whatever was there — writes a PANIC record on that thread. The frame's
  `closed_by` is `"unwind"` and `unwind_exc` is
  `{"type": "panic", "msg", "serial", "loc"}` taken from the most recent PANIC
  record on the thread. `closed_by` is never the string `"panic"` — a reader
  renders that as a false ` (open)`.
  **A frame can still close `panic` with no PANIC record to take it from**, and
  it is not a lookup failure: the program installed its own hook *after* ours
  (ours is gone; the program's own output is unaffected either way), or the
  thread's spool had gone inert and could not accept the hook's record (§4)
  (reasoned from `emit_if_open` → `Spool::record` refusing on `broken`; not
  exercised by a test in this wave).
  Then the converter writes `unwind_exc` as `{"type": "panic"}` with `"msg"` set
  to `"<panic message not recorded: no PANIC record preceded this unwind>"`, and
  counts the frame in the meta key `panics_unrecorded`. So a reader sees
  `unwind` with a named absence, never a message the recorder guessed. The
  first case is not reachable in a libtest-shaped run, where the test function's
  own `enter` comes first. A thread that panicked before it had recorded
  anything still gets no PANIC record at all — the hook opens no spool, because
  a hook that could fail could print, and printing on an already-panicking
  thread aborts the process (§4) — but it now leaves no `panic`-closed frame
  either: the only frames it opens are opened during the unwind, and they
  return.
- **`none` means a *value-returning* function's frame closed with nothing
  probed at its own site** — the qualifier matters, because a `-> ()` function
  also stashes nothing and reads `ok` (above): the wire carries no per-site
  knowledge, and the manifest's `ret: unit` is what separates the two at
  conversion. The ordinary cases, all of them properties of the source, are: a
  `?` that propagated past the tail, a syntactically diverging operand
  (`return`/`break`/`continue`, a `loop` with no valued `break`, a call of
  `panic!`, `unreachable!`, `todo!`, `unimplemented!`, `std::process::exit`,
  `std::process::abort`), or a `-> !` function. `none` is not "no error"; it is
  "this trace does not know".
- **That list is not closed, and the mechanism can produce `none` too.** A
  frame's exit operand leaves its capture on a per-thread LIFO stack keyed by
  `(site, frame depth)`, and the frame's own guard takes it back — top of stack,
  both keys matching, or nothing. The key is what makes the ordinary case safe:
  a local (or a tail temporary) whose `Drop` calls instrumented code opens a
  whole frame *between* an exit operand and its guard, at the same site if the
  `Drop` re-enters the same function, and neither frame can take the other's
  value. What remains, stated rather than left to be found:
  **the stack holds 64 pending captures**, and a 65th is refused, so that frame
  closes `none` — 64 is the depth of a chain of `Drop`s that each call
  instrumented code, not of the call stack, so no measured workload comes near
  it; and a capture left by a frame whose CALL was never written (its spool had
  already failed, so `records_dropped` is non-zero) is taken by nobody. Neither
  is signalled beyond the `none` itself. A run whose `records_dropped` is zero
  has met neither.
- **A generic return type reads `ok` even when the value is an `Err`.** The
  capture probe's specialisation is resolved where the fragment sits — inside
  the generic function, where `T` is not known to be a `Result` — so a
  `fn f<T>() -> T` monomorphised to `Result<_, _>` and returning `Err` closes
  `ok`. The outcome is a property of the *static* type at the exit operand.

**Falsified by** `rust/sensorium-rt/tests/panics.rs` (the PANIC record's
location, message and non-string payload, and the wire order CALL, PANIC,
RETURN `panic` on one thread), `rust/sensorium-rt/tests/outcomes.rs` (one arm
per outcome, read off the spool bytes by a parser written from the wire
format, not from the writer — including the three arms that pin the stack: a
`Drop` that calls a `-> ()` unit fn while an `Err` is pending, a `Drop` that
re-enters the same site one level down, and a re-entered site whose own frame
leaves by `?` and so must not take the outer frame's capture),
`corpus/rust/panic` (`closed_by unwind`, `unwind_exc.type panic`), and
— for the generic case, which this rung does not fix —
`corpus/rust/outcome_generic`, **deferred to rung 3** and named here so the
limit has an address before it has a test.

## 2. What a return value is

- The RETURN payload carries `{"k": "dbg", "v": <text>, "trunc": <bool>}`.
  `<text>` is the value's `Debug` rendering — what `{:?}` printed, not
  `Display`, and not a structural capture of fields — formatted through a
  writer that **stops at 200 bytes** and sets `trunc`: the writer returns an
  error at the cap, and what you get back is the value's first 200 bytes.
- **What the cap bounds, and what it does not** (measured 2026-09-02 while
  building the runtime; narrower than this ledger first claimed, and than the
  design's D10 assumed). It always bounds the *bytes*: the text captured, the
  `String` allocated and the wire payload are 200 bytes for a three-element
  `Vec` and for a million-element one alike. It bounds the *work* only when the
  value's `Debug` impl propagates the writer's error — the `write!(f, ..)?`
  idiom nearly every hand-written impl uses — where formatting stops at the cap:
  10⁷ items cost 1.5 µs with the cap against 99 ms without it. It does **not**
  bound the work for std's collection impls: `Formatter::debug_list` and
  `debug_map` short-circuit their *writes* once the writer errors but still walk
  every element, so capturing a 10⁶-element `Vec<u8>` costs about 10 ms whatever
  the cap is. Returning a huge collection from an instrumented function is
  therefore linear in the collection, once per call. The trace is bounded; the
  clock is not.
- **A value with no `Debug` impl reads `<unread>`** (payload `{"k": "unread"}`).
  So does a value whose `Debug` impl panics: the panic is caught inside the
  instrument, the program is not unwound, and nothing is printed. **The two are
  indistinguishable in the trace** — `<unread>` means "not read", and this
  recorder does not say why.
- **Both of those hold only where unwinding does.** The catch is
  `std::panic::catch_unwind`, which catches nothing under `-C panic=abort`, and
  the driver builds the runtime at whichever panic strategy the unit under test
  uses (D1). On an abort-profile workspace a `Debug` impl that panics ends the
  process instead of reading `<unread>`, and no frame ever closes `panic`
  because nothing unwinds. Nothing in the trace says so — it is declared here,
  and bloomery's profiles do not set it.
- **`<unread>` is never `()` and `()` is never `<unread>`.** A `()`-returning
  function records the value `()` as a recorded fact; a value that could not be
  read records `<unread>`. A reader that sees `()` is looking at a
  measurement, not at a placeholder.
- **Truncation is counted, not just marked**: per thread in the spool header,
  summed into the meta key `truncated_count`, which `info` prints.

**Falsified by** `rust/sensorium-rt/tests/values.rs` — the `!Debug` arm, the
panicking-`Debug` arm, the cap arm (a 10³- and a 10⁶-element `Vec` read back as
the same 200 bytes with `trunc` set), the arm that pins the work bounded on an
impl that propagates the error, and the header counter — with
`docs/trace-format/vectors/v08-return-outcome-dbg-value.json` pinning how a
reader renders it.

## 3. Threads, tasks and names

- Every thread that emits gets a process-global serial. The thread with
  `gettid() == getpid()` is serial 1 whether or not it ever emits, and
  `main_thread_ident = 1` is written explicitly rather than inferred.
- **Every non-main thread that emits is a task**, with one `tasks` row and one
  `task_fingerprints` row; `fingerprint_basis` is `"per-task"`. A zero-count
  fingerprint row for the main thread means "ran traced code only inside
  tasks" — not "ran nothing".
- **libtest names the thread it runs a `#[test]` on**, so under `cargo test` a
  test *is* a task, named by its test path. That is what lets `diff` compare
  two runs of a test binary whose main thread runs no workspace code at all.
- **`spawn_child` names threads spawned by workspace code.** ~~A rewritten
  `std::thread::spawn` site produces the name
  `<parent task name> :: spawn@<file>:<line>`, or `spawn@<file>:<line>` when
  the spawning thread has no *task* name — the main thread's std-given `main`
  is a thread name, not a task name, so a child of `main` is `spawn@<site>`
  alone (a task row belongs to every *non-main* thread, above), and an empty
  name is no name.~~ **Superseded 2026-09-03** (rung-3 entry decision (b),
  `docs/superpowers/plans/2026-09-03-sensorium-rung3-entry-spawn-names.md`
  decisions N1, N5, N6): a rewritten `std::thread::spawn` site now produces
  the name `<parent task name> :: spawn@<qualname>#<k>`, or
  `spawn@<qualname>#<k>` alone when the spawning thread has no *task* name
  (the main thread's std-given `main` is a thread name, not a task name, so a
  child of `main` still carries no parent prefix — a task row belongs to
  every *non-main* thread, above — and an empty name is still no name).
  `qualname` is the enclosing NAMED ITEM's file-local qualname: a fn item,
  where it is exactly that fn's manifest `Site.qualname` (`Type::method`,
  `outer::inner`, `tests::t`); or, when the spawn sits in a closure inside a
  `const`/`static`/associated-`const` initialiser with no fn frame above it,
  that item's own file-local path (`F`, `m::H`, `T::F`) — a path no `Site`
  carries, because the item itself is not instrumented, only the child it
  spawns is named. `k` is the 1-based ordinal among the WRAPPED spawn sites
  of that `(file, qualname)`, in byte-offset source order; a declared
  (unwrapped) shape consumes no ordinal. The unit manifest's `spawns`
  entries carry both `qualname` and `ordinal` (`null` for a declared shape)
  alongside the existing `file`/`line`, so the location stays one lookup
  away from the name. The `JoinHandle`, panic propagation and the OS thread
  name are unchanged.
  - **Caveats** (each is a real observable consequence, not a hypothetical):
    (i) inserting a wrapped spawn earlier in the same item renumbers every
    later ordinal in that item — an honest DIVERGED, not silent corruption;
    (ii) the qualname is file-local, so renaming an `impl` block's self type,
    or moving the fn between `impl` blocks, renames the task; (iii) two
    files in one compilation unit that share an identical file-local
    qualname each start their own `#1`, and the tasks are compared as a
    multiset by content (§7's twin rule); (iv) trait-impl twins in one file
    (`Type::fmt` for `Display` and for `Debug`) share one qualname, so their
    ordinals CONTINUE across the twins in source order rather than each
    starting at `#1`; (v) a spawn whose innermost scope is a
    `mod`/`impl`/`trait` container — with no fn/const/static frame above it
    — is REFUSED: that file is not instrumented at all, loudly on stderr,
    rather than being named after the container, and this is REACHABLE, not
    theoretical — an enum discriminant expression and an array-length
    expression in a struct field's type are both expressions that sit
    directly inside a `mod` body, both compile with a spawning closure
    inside (measured on rustc 1.96), and syn's default visitors reach them;
    (vi) a spawn inside a fn's SIGNATURE expression (an array-length
    expression in a return type is the shape that surfaced it) is neither
    rewritten nor declared — the three fn visitors descend into the body
    only — a pre-existing rung-2 hole, found and dated 2026-09-03, carried
    as an open item in
    `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3; (vii) a
    `fn` item nested inside a `const`/`static` initialiser now carries that
    item's name as a qualname prefix (`X::h`, where rung 2 wrote `h`) — a
    `Site.qualname` change, more correct, zero instances on bloomery.

  **Falsified by** (the naming rule, 2026-09-03):
  `rust/sensorium-transform/tests/golden.rs`
  (`a_spawn_site_is_named_by_its_enclosing_fn_and_its_ordinal`, run against
  fixture `spawn_ordinals` — the seven fn shapes, the five initialiser
  shapes, and the `T::fmt` twins), `rust/sensorium-transform/tests/edges.rs`
  (`a_spawn_with_no_enclosing_named_item_is_refused_not_named_after_the_container`
  — the container refusal, both the enum-discriminant and array-length
  shapes), `corpus/rust/spawn_across_move` (the same worker paired across a
  file move by `diff --ignore-moves`, and seen as moved by plain `diff`),
  `corpus/rust/spawned_thread`, `rust/tests/mechanics.sh` (two checks pin
  `<test fn> :: spawn@<test fn>#1`), and the E5′ acceptance record
  `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md`
  (its §4 — this ledger does not assert that document's verdict).
- **A spawn shape the transformer does not rewrite is declared, not silently
  missed**: `Builder::spawn` (`reason: "builder"`), `thread::scope`
  (`"scoped"`), other one-argument `.spawn(f)` method calls (`"method"`), and a
  path ending in `thread::spawn` taking an argument count
  `std::thread::spawn` does not (`"arity"` — unreachable in code that compiles,
  listed rather than dropped so nothing the suffix rule matched is silently
  ignored) are listed in the unit manifest's `spawns` with `wrapped: false` and
  that `reason`, and `info` prints `J spawn sites (W wrapped)`. A **zero**-
  argument `.spawn()` is `Command::spawn`, not a thread, and is not a spawn
  shape at all: listing it would put a thread in the manifest that never
  existed.
- **A thread spawned by dependency code has no name at all.** Its `tasks` row's
  name is NULL, `tree` identifies it only as unnamed, and `diff` compares such
  tasks as an unnamed multiset by content: a divergence inside one is reported,
  but *which* one it was cannot be named. Rung 1 measured the hole this closes
  — 4 of 57 emitting non-main threads in a bloomery `--lib` trace carried no
  name (findings §5.20).

**Falsified by** `corpus/rust/spawned_thread` (a worker holding a lock inside a
test is named in the verdict), `corpus/rust/libtest_threads` (`--test-threads=1`
against `--test-threads=4` reads MATCH with the tasks carrying it, and names the
four tests that are the tasks), `rust/sensorium-rt/tests/spawn.rs` (parent,
grandchild, main-spawned and dependency-shaped names) and
`rust/sensorium-rt/tests/serials.rs`. The separate promise that a per-task trace
whose task fingerprints are gone is REFUSED rather than MATCHed is falsified by
`tests/test_diff.py::test_diff_refuses_a_per_task_trace_whose_task_fingerprints_are_missing`
(both the plain and the `--task` arm) and, on the positive side, by
`docs/trace-format/vectors/v04-main-thread-silent-tasks-carry` — a zero-count
row is kept and counted, so "no row" and "a row saying zero" stay different
facts. (**Amended 2026-09-03**: this paragraph said `libtest_threads` ran
against `8` and carried a counter-truth question that deletes the fingerprints.
It runs against `4`, and the counter-truth was dropped by ruling at Task 10 as
already pinned by the two falsifiers just named; the ledger had not followed.)

## 4. What a spool loses

Spools are `MAP_SHARED` file-backed mappings, one per emitting thread. Every
field of a record is written before its `kind` byte, and `kind` last with a
Release store, so **a record is complete iff its `kind` is non-zero**; a reader
stops at the first zero. The kernel owns the pages, so the file survives a
thread that never returns, `process::exit`, `abort`, and SIGKILL.

- **The loss, stated as a bound:** a record being written at the instant the
  process dies is lost — **at most one per thread, and only that one**.
  Everything written before it is on disk. This is the whole of what a crash
  costs.
- **A lost record leaves a hole in the process-global sequence**, and the
  converter counts holes: the meta key `seq_gaps`, which `info` prints as
  `seq gaps: n -- records minted and never found in any spool (one lost
  mid-write per thread at most; see rust/HONESTY.md §4)`.
- **`records_dropped` is a different number**: what the runtime *knew* it could
  not write — a failed `ftruncate` or `mmap` sets the thread inert and counts
  every later record. `seq_gaps` is inferred from the merge; `records_dropped`
  is witnessed by the writer. Both are summed by `Trace.dropped_writes()`, and
  a non-zero total makes `diff` refuse a verdict rather than issue one over a
  hole.
- **The two are disjoint, and one line of the runtime is why** (**amended
  2026-09-03**): the sequence number is minted *inside* `Spool::record`, after
  the record is known to fit a mapping that can still be grown, so a refused
  record consumes no number and leaves no hole. Until this was fixed every
  witnessed drop was ALSO counted as a `seq_gap` — on a two-thread process with
  a 64 KiB limit, 3382 witnessed drops read as `records_dropped` 3382 plus
  `seq_gaps` 1190, and the bound above did not hold for `seq_gaps`. It holds
  now: `seq_gaps` counts only records minted and lost, which is at most one
  per thread. Falsified by
  `rust/sensorium-rt/tests/seq_contiguity.rs::a_refused_record_consumes_no_sequence_number`
  — the seqs a whole process WROTE are `0..=max` with nothing missing — and by
  `rust/cargo-sensorium/tests/convert.rs::a_thread_whose_spool_went_inert_costs_no_seq_gaps`
  on the converter's side. The first needs `SENSORIUM_TEST_SPOOL_LIMIT` to force
  the refusals, so like the disk-full arm it is `test-hooks`-gated and runs in
  that CI step rather than in `cargo test --workspace`. It must be
  multi-threaded to have content: on a single thread the spool breaks and stays
  broken, so every refusal falls past that thread's last write and the union is
  contiguous either way (measured — with the seq minted before the check,
  `spool-limit 6000` reads 0 gaps while `two-threads 3000` reads 1282), which is
  why the test asserts that interleaving as a precondition.
- **A thread still running when the process exits has no `THREAD_END`.** The
  converter lists it in `live_threads` and leaves its frames open; `incomplete`
  stays `false`, because the *process* finished even though the thread did not.
  That is the distinction a reader most easily misreads, which is why `info`
  prints both facts rather than one. A thread whose spool went inert could not
  write `THREAD_END` either, so it lands in `live_threads` having finished:
  where `records_dropped` is non-zero `info` offers that second reading beside
  the first rather than asserting the thread was running.
- Rung 1's `BufWriter` spool lost a live thread's entire buffered tail, and
  lost it silently: 100 spool files without `THREAD_END` in 3 of 119 processes,
  and `abort()` losing every thread's tail including main's (findings §5.2,
  §5.25). `MAP_SHARED` is what reduces that to the one-record bound above.

**Falsified by** `rust/sensorium-rt/tests/durability.rs` — a thread blocked in
`recv()` with N complete records while the process returns from `main`, calls
`process::exit(0)`, calls `abort()`, and is SIGKILLed, each row read off the
bytes; plus the synthetic disk-full arm that pins `records_dropped`, which is
`#[cfg(feature = "test-hooks")]` and so has its own CI step
(`cargo test -p sensorium-rt --features test-hooks`) — a plain
`cargo test --workspace` compiles it out — and by `corpus/rust/abort`. The acceptance run reports `seq_gaps`, `records_dropped`
and per-live-thread last-record completeness for a whole invocation
(acceptance §3, *reported without a gate*).

## 5. Exit status

- **`exit_status` is this process's own status, and only when sensorium's
  runner started this process.** The driver installs itself as cargo's target
  runner, so cargo hands it every test binary — and, on cargo 1.96, every
  doctest process (measured 2026-09-02). The runner spawns, waits, and records
  the status: `exit_status_basis: "waited"`, with `exit_signal` set when the
  process died by a signal.
- **Anything the runner did not start carries `exit_status: null` and
  `exit_status_basis: "unwitnessed"`**, and `info` prints `exit: unwitnessed`.
  A child a test spawned itself is the ordinary case. Not a zero, not a guess.
- **It is never borrowed from cargo.** Rung 1 wrote cargo's status onto all 119
  traces of one invocation, so every process of a run claimed the same number
  (findings §5.1). This version does not: a status in a trace is a status
  somebody waited for.
- **A process that died inside a frame leaves that frame open.** `closed_by` is
  NULL and `tree` shows it open — that open frame is the record of the death.
  `incomplete` is `false` because conversion finished; the open frame and
  `exit: unwitnessed` are what say the process did not.
- The limitation this rests on: a runner set in a workspace's
  `.cargo/config.toml` is replaced rather than chained (§8).

**Falsified by** `rust/cargo-sensorium/tests/runner.rs` (exit 0, exit 7 and
SIGKILL each yielding the matching record and the matching runner exit code,
with stdio byte-identical through it), `corpus/rust/abort`,
`rust/tests/mechanics.sh` (every test binary and the doctest process carry a
runner record and read `waited`), and
`docs/trace-format/vectors/v10-exit-status-unwitnessed.json`. The acceptance
run reports the `waited`/`unwitnessed` histogram across an invocation.

## 6. Children

- **`capabilities.children` is `false`.** This recorder hooks no spawn
  primitive. It cannot tell you that a process created another process, and
  `info` says so in the recorder's own words: *declares children not witnessed
  (capabilities.children: false), so there is no children / spawn_syscalls /
  audit_errors record to read; absence of the record is not a record of
  absence.*
- **What it can tell you is the join:** an instrumented child of the same
  invocation is linked to its parent by `ppid`, recorded as the parent's
  `child_runs: [{run_id, pid, exe}]` and printed by `info` as
  `child runs: N -- <run ids>` immediately after that declaration. So a
  subprocess test shows either a child's run id or the declaration that spawns
  are not witnessed — **never neither**.
- **A child that ran no instrumented code is invisible.** A `ls`, a dependency
  binary, anything outside the workspace: no spool, no run id, no row. Its
  absence from `child_runs` is not evidence that it did not run.

**Falsified by** `corpus/rust/abort` (the parent's `child_runs` names the
aborting child; the child's own trace reads `exit: unwitnessed`),
`docs/trace-format/vectors/v11-child-runs-linked.json`, and the `child-linked`
fixture of `tests/test_rust_convert.py`.

## 7. Site identity

- **At record time a site is per compiled unit**, not per source function:
  `unit_id` in the top 8 bits, site index in the low 24. Cargo compiles one
  crate root as several units — lib, lib `--test`, each `tests/*.rs`, each
  feature set — so one source function has a different site id in every unit
  that compiles it. Measured on bloomery: 7360 raw sites across 77 manifests
  against 1723 distinct `(file, qualname, firstlineno)` triples, a 4.3×
  duplication (findings §5.8).
- **At conversion they are merged.** `code_objects` is interned on
  `(file, qualname, firstlineno)` with `file` absolute and `qualname` the
  file-local path in Python's shape (`Type::method`, `tests::setup`,
  `outer::{{closure}}`) — never `module_path!()`. The 13 `tests/common` files
  compiled into 69 integration units collapse to one code object each.
- **The consequence, named rather than left to be discovered:** `diff` keys
  code objects on `(file, qualname, kind)` — *without* the line — so two
  functions that share a file and a qualname and differ only in line are one
  key to `diff` and to `--ignore-moves`' pairing. The common instance is two
  trait impls on one type: `qualname` is `<self type>::<method>`
  (`self_type_name`, `visit.rs:417-425`), so `impl Display for Row` and
  `impl Debug for Row` in one file both give `Row::fmt`, and the trait they
  implement is nowhere in the key. Any type with both impls has this shape.
  The cfg-gated twin is the same collision from the other direction: bloomery's
  `crates/bloomery-daemon/src/main.rs` declares `fn run` twice, once under
  `#[cfg(feature = "llama")]` and once under `#[cfg(not(...))]` (findings
  §5.27). The trace distinguishes them; **`diff` cannot**.
- **Fingerprints hash the workspace-relative path**, while `code_objects.file`
  is absolute — and the two comparisons that follow run in opposite
  directions. *Stored* hashes are relocation-insensitive by construction (D9),
  so two checkouts of the same tree at different paths compare equal on them.
  `diff --ignore-moves` does not use them: it re-hashes both sides at query
  time over what `code_objects` holds, which is the **absolute** file
  (`src/sensorium/query/moves.py`, `hash_stream`). That is what makes a split
  verifiable across a refactor **within one tree** — the same string on both
  sides — and it is exactly what breaks between two checkouts at different
  paths. Compare traces from one tree, or expect the pairing to be the thing
  that fails.

**Falsified by** E3 (20 identical re-runs of one test binary, same binary hash:
DIVERGED 0/19 and REFUSED 0/19) and E5 (`diff --ignore-moves` on the
registry.rs split, plus the planted call-site swap that must read DIVERGED) in
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`, by
`rust/cargo-sensorium/tests/unit_identity.rs` (two units of one crate root get
two mirrors with two different unit statics — and the check asserts it examined
more than zero crate roots, findings §5.29), and by the identical-pair fixture
of `rust/cargo-sensorium/tests/convert.rs`.

## 8. What this recorder cannot see

Stated as categories wherever a category is honest. Five review rounds of the
Python `refocus` each found a mechanism the tool could not see; an enumeration
that looks complete is more dangerous than no enumeration, because a reader who
checks the list concludes their case was covered.

**What it does see, so the list below is bounded.** Every function item with a
body in a workspace crate gets a frame, except the skips items 5 and 6 declare;
every unit either instruments or says it fell back. Rung 1 measured 100.0% of
eligible function items on bloomery (2051/2051), and this rung re-measures it
as **E2′**, where a floor of 98% applies and *any* fell-back unit is a finding
that stops the rung until it is explained. *Falsified by* E2′ in
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` and by
`rust/sensorium-transform/tests/census.rs`, which requires
`instrumented + async == eligible` over a real workspace's files.

Each entry below names **what declares it** — the field or line a reader meets
without knowing this document exists.

1. **Dependency-crate internals.** Only workspace units are instrumented
   (cargo's workspace wrapper is the hook). A call into `serde` or `tokio`
   shows as the caller's frame and its return; the inside is not there.
   *Declared by* the meta key `instrumented_units` and `info`'s
   `units: N instrumented, …` line.
2. **`?` sites, sinks, and `Err` arms — rung 3.** No RAISE or HANDLED is
   recorded at a `?`; `.ok()`, `.unwrap_or*()`, `let _ =` and `Err(..) =>` arms
   are not classified. Everything a rung-2 trace says about a `?` that
   propagated is `outcome: none` on the frame it left (§1). *Declared by* the
   refusal `exceptions` prints: `REFUSED: exceptions on a rust trace needs the
   Rust disposition rules (rung 3); the Python rules would misread Err values
   as exceptions; nothing was judged`. The dispositions and chain identity that
   spec §6 defines — SWALLOWED, PANICKED, RETURNED-TO-HARNESS, and
   AMBIGUOUS-by-default the moment an `Err` leaves the enumerated grammar —
   are rung 3's, and this ledger gains their section when they land, not
   before.
3. **Locals, and per-line state — rung 4.** Nothing is captured between a
   function's entry and its exit, so a value that changed in place mid-frame,
   including mutation through a long-lived `&mut`, is invisible. *Declared by*
   `capabilities.line: false` and `capabilities.locals: false`; by the
   `"unread": ["locals"]` marker every CALL payload carries, which `tree`
   renders as `name() <unread: locals>` and `frame` as
   `args: <unread: locals>` — never `(none)`, which would read as "called with
   no arguments"; and by the refusal `watch` and `flow` print:
   `REFUSED: watch needs line, which recorder sensorium-rt 0.1.0 declares it
   does not produce (capabilities.line: false); nothing was checked`.
4. **What the program printed.** libtest owns the capture and the hook that
   would take it is unstable. *Declared by* `capabilities.output: false`: the
   `output` table is empty, and every reader prints the declaration instead of
   a zero.
5. **`async fn` bodies.** Skipped whole — an entry guard would live across
   every `.await`, and the guard is the sole emitter of a RETURN (§1) — so an
   async
   function gets no frame at all rather than a wrong one. *Declared by* the
   manifest's `skipped: [{reason: "async"}]`, carried into the meta key
   `skipped` and printed by `info` as `K skipped (<reasons>)`. bloomery has
   zero; a workspace with async functions gets one skip record each and no
   invented frames.
6. **`const fn`, `extern` functions, and function bodies inside
   `macro_rules!`.** Same declaration, reasons `const`, `extern`, `macro`.
   A `?` inside a macro argument is invisible to the parser for the same
   reason; that is rung 3's problem and rung 3's manifest field.
7. **A unit that fell back to the real tree.** Nothing in it is instrumented:
   no frames, no returns, no sites. The reasons are `rustc: <first error
   line>`, `lto`, `cross-target`, an absolute crate root, and
   `wrapper: <error>`. *Declared by* the unit manifest's `fell_back: true` and
   `fallback_reason`, the meta key `uninstrumented`, and `info`'s
   `M fell back (<reasons>)`. **Every** fallback path writes or patches a
   manifest — rung 1 had one that reported to the log channel only, and a
   coverage check reading manifests alone would have scored it as instrumented
   (findings §5.29). A fallback in a shared `tests/common/*.rs` uninstruments
   every test binary that includes it, and the manifests say which.
   **And a fallback is not always an escape.** A unit whose DEPENDENCIES are
   instrumented cannot be compiled plainly: their rmetas already reference
   `sensorium_rt`, so the passthrough rustc run needs the runtime as much as
   the instrumented one did. When such a unit falls back for a reason that is
   about the runtime's linkage, the plain compile fails with the same
   `E0463: can't find crate for <dependency>` and cargo's build fails —
   measured on the bloomery clone, 2026-09-03, on a fresh target with a wrapper
   that sent `--extern sensorium_rt=<rlib>` and no `-L dependency=<rt dir>`:
   `bloomery-daemon`'s lib unit was declared
   `fell_back: true, fallback_reason: "rustc: can't find crate for
   bloomery_core"` and the build then exited 101 anyway. The manifest is
   therefore the record of what the recorder did NOT instrument, never a
   promise that the build survived it.
   **The condition is the unit's own dependencies, not the fallback's reason.**
   A fallback replays the argv cargo built, with no `--extern` and no `-L` of
   ours, so *every* reason takes the same plain compile — including `lto` and
   `cross-target`, which are decided before instrumenting, and
   `wrapper: <error>`. A unit with instrumented dependencies therefore fails
   `E0463` on a `lto` fallback exactly as it does on a runtime-linkage one.
   "Recorded nothing, built fine" is what a fallback means **only when that
   unit's own dependencies are uninstrumented** — a leaf workspace crate, or
   one that depends only on registry crates. Which units those are is readable
   from the manifests: a fallen-back unit whose dependencies have manifests of
   their own is in the failing case.
   The linkage this rests on is the wrapper's `--extern sensorium_rt=<rlib>`
   **and** `-L dependency=<the rlib's own per-variant directory>` (plan
   decision D1 as amended): rustc resolves a dependency's own `sensorium_rt`
   through the search path, not the extern map.
8. **A module the module walk could not reach.** `#[cfg_attr(.., path = ..)]`
   is not evaluated — the walk resolves `mod` declarations and literal
   `#[path]`, and refuses to guess at a conditional one. *Declared by* the unit
   manifest's `unreached_files`, carried into the meta key of the same name
   over the units this process registered, and printed by `info` as
   `unreached files: N -- <paths>`. A file the walk never reached is a file
   whose functions have no sites at all, so the declaration has to travel with
   the trace: a limit whose declaration a reader cannot reach is half a
   declaration. bloomery has zero such files (findings §5.26).
   **Amended 2026-09-03** (rung-3 entry, Task-1 review B): `unreached_files`
   is not only the cfg-gated-path case above. A file the walk resolved but
   the wrapper could not READ, and a file the walk read but
   `sensorium-transform` REFUSED (an unparseable file, or one of the
   transformer's own synthesised errors — a spawn with no named item around
   it, a rewrite that would move a line, a wrapped spawn's ordinal
   disagreeing with source order) both land in `unreached_files` too, and
   only the last case carries a message: the wrapper prints `sensorium: unit
   <crate> (<metadata>): <rel>: <message>` on stderr and records `<message>`
   under the manifest key `unreached_reasons`, keyed by the same
   workspace-relative path. A file the wrapper cannot read gets no entry in
   `unreached_reasons` — `read` hands back an `Option`, so there is no
   message to quote, and inventing one would be worse than the silence.
   `fell_back` stays `false` for a refused file: this is one file's
   instrumentation lost, not the whole unit's, and every other file in the
   unit still is. The one exception is the crate root: if the file holding
   `__SENSORIUM_UNIT` is among the refused files, the whole unit ends up with
   no files instrumented at all (every guard would otherwise reference a
   static that does not exist) — still not `fell_back: true`; only
   `unreached_reasons` says why the unit came back empty. *Falsified by*
   `rust/cargo-sensorium/tests/wrapper_fallback.rs`'s
   `a_file_the_transformer_refused_names_its_reason_on_both_channels`.
9. **Why a return value was unread** (§2): a missing `Debug` impl and a
   panicking one read the same.
10. **A runner set in a workspace's `.cargo/config.toml`.** The driver sets
    `CARGO_TARGET_<HOST>_RUNNER` in the environment, which overrides the
    config file, and only an env-set `SENSORIUM_INNER_RUNNER` is chained. On
    such a workspace the recorded run is not the run the config describes —
    and **no field in the trace says so**. It is declared here, and in the
    acceptance document's §2 pins, which record that no config-file runner
    existed on the box or in the tree that was measured. *Falsified by* adding
    one to `rust/probes/ws/` and re-running `rust/tests/mechanics.sh`.
11. **Object identity.** There is no Rust `id()`: two `Vec`s with the same
    contents are one value to this trace. *Declared by*
    `capabilities.object_identity: false`; `flow --object` refuses.
12. **A deeper re-run.** `refocus` re-invokes the recorder and compares, and
    the Rust side of it is rung 4. *Declared by* `capabilities.refocus: false`;
    `refocus` refuses with the `caps.require` sentence, naming the capability
    and the recorder.
13. **Anything after the 256th instrumented unit in one process.** Unit ids
    run `0..=254`; the 256th distinct unit makes the runtime refuse to record
    rather than wrap the id and attribute events to the wrong unit, and every
    later `enter` in that process is inert. The refusal is **in the trace, not
    only on stderr**: the proc header's `refused` becomes that unit's metadata,
    the converter writes it as the meta key `units_refused`
    (`{"refused": bool, "at": <metadata or null>}`), and `info` prints
    `unit ceiling: recording REFUSED at unit <metadata> -- every later call in
    this process is unrecorded`. A trace past the ceiling is short **and says
    so**. The ceiling has never been approached (a workspace-wide bloomery
    build produced 108 units *in total*, findings §5.13), so the path is driven
    by a test and by nothing else yet. *Falsified by*
    `rust/sensorium-rt/tests/units.rs`.
14. **Everything the Python README's *What sensorium sees at all* rules out**,
    which is not language-specific: any file the program read or wrote, the
    environment beyond the variables a command names as compared, the clock,
    the network, and everything else the machine did. *Declared by*
    `source_hashes`, which is the whole of what the trace pins about the world
    outside the process — the source files the instrumented units were built
    from, and nothing else. Config, fixtures, databases and inputs move
    unseen.

## 9. Preserved by construction, and tested

Recording changes what the program does only in the ways §10 and the last
bullet name. Everything here is a tested claim, not a design intention.

- **Line numbers and file paths.** Injected fragments are newline-free and
  spliced at `syn`'s byte offsets, so a rewritten file has exactly the original
  line count. **There is exactly one exception, and it is the appended line
  itself**: on a crate root whose last token is a line doc comment or a shebang
  that runs to EOF with no newline after it, "after the last token" is inside
  that line, and a static spliced there is commented out or becomes part of the
  shebang — so in that one shape the unit static's fragment carries a leading
  newline. It can only ever add a FINAL line, no existing line moves, such a
  file has no items (hence no `mod` declarations, hence no other file in its
  unit, hence no guard anywhere that could reference the static), and the added
  line is recorded per file as the manifest's `appended_line` — the same field
  that records the item-free crate roots whose static simply lands past the
  final newline. `file!()`, `line!()`, panic
  locations and every backtrace frame's `<file>:<line>` are the plain build's,
  because the build runs in a per-unit mirror with
  `--remap-path-prefix=<mirror>=<workspace>` appended — a flag rung 1 found to
  be load-bearing rather than belt and braces: without it backtraces print
  mirror paths (findings §5.21).
  *Falsified by* E7(a) in `rust/tests/mechanics.sh` and E7(b) on a real
  workspace (acceptance §3), and by `rust/sensorium-transform/tests/golden.rs`,
  where every golden asserts the output's line count.
- **Temporary lifetimes, drop order and lock hold times at every wrapped
  site.** The exit operand is passed as an argument to `ret`, evaluated exactly
  where the tail was; the capture closure is passed *before* it, so a diverging
  operand leaves nothing unreachable behind it. Nothing is ever `let`-hoisted:
  a hoist is `E0716` on a guard-borrowing operand and, where it compiles,
  releases a `MutexGuard` early.
  *Falsified by* `rust/sensorium-transform/tests/oracle.rs` — a `Drop`-logging
  guard held across a wrapped tail logs the same order with and without the
  transform, and a `MutexGuard` in a wrapped tail is released at the same point
  (read by a `try_lock` from another thread).
- **No new diagnostics.** Every golden's output is compiled by the real rustc
  under `-D warnings` with zero diagnostics. This is why the exit form is a
  call and not spec §3.2's `match (<e>)` wrap: the parentheses trip
  `unused_parens`, and under a crate's own `#![deny(warnings)]` a whole unit
  would fall back. *Falsified by* the same `oracle.rs`.
- **Cargo freshness, and a plain build that stays plain.** The wrapper is
  hashed into `-C metadata`, so instrumented and plain artifacts coexist in one
  `target/`, switching back recompiles nothing and runs the right binaries, and
  an edit still rebuilds exactly what it should. Nothing is written under a
  workspace except `<target>/sensorium/`. `Cargo.lock` is untouched:
  `sensorium-rt` is never a dependency — the driver compiles it with one bare
  `rustc` invocation and the wrapper adds one `--extern`.
  *Falsified by* E8(a)–(d) in `rust/tests/mechanics.sh` and on a real workspace
  (acceptance §3), including the sentinel that requires a *plain* binary run
  with `SENSORIUM_SPOOL` set to write zero spool files.
- **The program's own output and panic behaviour.** The panic hook writes one
  record and then calls the hook it replaced, so stderr is byte-identical with
  and without the runtime installed. *Falsified by*
  `rust/sensorium-rt/tests/panics.rs`.
- **What is *not* preserved, stated beside what is.** Wall time and disk (§10).
  RETURN fires before a tail-expression temporary's own `Drop` under edition
  2021 — observable only if a workspace `Drop` impl runs in a tail temporary.
  And a `Debug` impl invoked by the instrument **runs**: reentrancy keeps it
  from emitting and `catch_unwind` keeps its panic from escaping, but its side
  effects are real. A `Debug` that mutates or logs will do so once per captured
  return.

## 10. Cost is reported, never gated

Overhead is a tracked fact about a machine and a workload, not a pass/fail
property of the tool. Every number ships with its `n` and its lens, and no
number in this rung gates anything.

- **The headline and its limit, together.** On bloomery's
  `cargo test -p bloomery-daemon` suite wall, rung 1 measured tier-off/plain
  **×0.9975** and call/plain **×1.0103** (n=5 per arm). That is
  *indistinguishable*, not *faster*, and it is not to be quoted as a speedup —
  the arms ran in a fixed order under a decaying background load, which biases
  the first arm slow (findings §5.18). On `fib(30)` at `opt-level = 0` the same
  gate costs **×5.934**, about +5.2 ns per site. Both are true: bloomery's
  suite records 15 874 events per second where `fib(30)` records 3.04×10⁷, a
  ≈1900× density gap. Compile-once-gate-at-runtime is free on code shaped like
  a test suite, **and only there**.
- **`--tier off` is a runtime gate, not a rebuild.** Everything compiles in
  once and the tier is read from the environment, so changing it recompiles
  nothing. That decision was made by measurement against a ×1.5 rule and is not
  re-decided here; the first call-dense target re-opens it.
- **What v1 adds and reports:** return-value capture at tier `call`, against
  rung 1's ×1.0103; the conversion wall for a whole invocation; events per
  second and bytes per event; the driver's own fixed cost.
- If a reported wall exceeds the threshold rung 1 pre-registered, that is a
  finding written into the acceptance document — not a silent trade, and not a
  reason to stop recording.

**Falsified by** the reported walls of the acceptance run
(`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` §3,
*reported without a gate*): plain against call in alternating order with a
cool-down, the load recorded per arm, and an arm **dropped rather than
re-rolled** if the box was busy when it started.

---

## Index: promise → falsifier

| § | Promise | What could falsify it |
|---|---|---|
| 1 | Outcomes are `ok`/`err` from the exit operand, `panic` from the hook, `none` when nothing was probed; a `panic` with no PANIC record behind it says so and is counted | `rust/sensorium-rt/tests/outcomes.rs`, `rust/sensorium-rt/tests/panics.rs`, `corpus/rust/panic` |
| 1 | A generic `T` that is a `Result` only after monomorphisation reads `ok` | `corpus/rust/outcome_generic` (rung 3, deferred) |
| 2 | A return value is `Debug` text capped at 200 bytes; `!Debug` and panicking `Debug` read `<unread>`; `()` is never `<unread>` | `rust/sensorium-rt/tests/values.rs`, `docs/trace-format/vectors/v08-return-outcome-dbg-value.json` |
| 3 | Every emitting non-main thread is a named task where a name exists; `spawn_child` derives the name; dependency threads are unnamed and compared as a multiset | `corpus/rust/spawned_thread`, `corpus/rust/libtest_threads` (`--test-threads=1` against `4`), `rust/sensorium-rt/tests/spawn.rs`, `rust/sensorium-rt/tests/serials.rs`; the REFUSED-on-deleted-fingerprints promise by `tests/test_diff.py` (`test_diff_refuses_a_per_task_trace_whose_task_fingerprints_are_missing`) and `docs/trace-format/vectors/v04-main-thread-silent-tasks-carry` |
| 3 | A rewritten spawn site's child is named `<parent> :: spawn@<qualname>#<k>` — `qualname` the enclosing named item's file-local path, `k` a source-order ordinal among that item's wrapped sites (rung-3 entry, 2026-09-03) | `rust/sensorium-transform/tests/golden.rs` (`a_spawn_site_is_named_by_its_enclosing_fn_and_its_ordinal`, fixture `spawn_ordinals`), `rust/sensorium-transform/tests/edges.rs` (`a_spawn_with_no_enclosing_named_item_is_refused_not_named_after_the_container`), `corpus/rust/spawn_across_move`, `corpus/rust/spawned_thread`, `rust/tests/mechanics.sh`, E5′ in `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md` (§4) |
| 4 | A crash loses at most one record per thread; holes are `seq_gaps`; `records_dropped` is what the writer knew it lost, and the two are disjoint | `rust/sensorium-rt/tests/durability.rs`, `rust/sensorium-rt/tests/seq_contiguity.rs` (`a_refused_record_consumes_no_sequence_number`, `test-hooks`), `rust/cargo-sensorium/tests/convert.rs` (`a_thread_whose_spool_went_inert_costs_no_seq_gaps`), `corpus/rust/abort` |
| 5 | `exit_status` is `waited` only for processes our runner started; everything else is `unwitnessed`, never borrowed from cargo | `rust/cargo-sensorium/tests/runner.rs`, `corpus/rust/abort`, `rust/tests/mechanics.sh`, `docs/trace-format/vectors/v10-exit-status-unwitnessed.json` |
| 6 | Spawns are not witnessed; instrumented children are linked by `ppid`; a child that ran no instrumented code is invisible | `corpus/rust/abort`, `docs/trace-format/vectors/v11-child-runs-linked.json`, `tests/test_rust_convert.py` (`child-linked`) |
| 7 | Sites are per unit at record time and merged on `(file, qualname, firstlineno)` at conversion; `diff` cannot separate cfg-gated twins | E3 and E5 in `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`, `rust/cargo-sensorium/tests/unit_identity.rs`, `rust/cargo-sensorium/tests/convert.rs` |
| 8 | Every eligible function in a workspace crate is instrumented, or its unit says it fell back | E2′ in `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`, `rust/sensorium-transform/tests/census.rs` |
| 8 | Every blind spot is declared in a manifest field, a meta key or an `info` line — including the unreached-module and unit-ceiling declarations, which reach the trace as `unreached_files` and `units_refused`, and (amended 2026-09-03) a REFUSED file's own message, which reaches it as `unreached_reasons`; the one declaration that does not exist (a config-file runner replaced rather than chained) says so | `rust/tests/mechanics.sh` (fallbacks in both channels; a unit using an instrumented dependency), `rust/sensorium-rt/tests/units.rs` (the unit ceiling), `rust/cargo-sensorium/tests/wrapper_fallback.rs` (`a_file_the_transformer_refused_names_its_reason_on_both_channels`), `docs/trace-format/vectors/v14-rust-refusals.json`; §8.10 itself is falsified by adding a config-file runner to `rust/probes/ws/` and re-running mechanics.sh, which no shipped check does |
| 9 | Line numbers, paths, backtraces, drop order, lock hold times, freshness and plain builds are unchanged | E7 and E8 in the acceptance document and `rust/tests/mechanics.sh`, `rust/sensorium-transform/tests/oracle.rs`, `rust/sensorium-transform/tests/golden.rs`, `rust/sensorium-rt/tests/panics.rs` |
| 10 | Cost is reported with `n` and lens, and gates nothing | the acceptance document's *reported without a gate* section |
