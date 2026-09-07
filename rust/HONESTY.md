# The Rust recorder's honesty ledger

`sensorium-rt 0.4.0`, `sensorium-transform 0.4.1`, `cargo-sensorium 0.5.0` —
v1, the call tier, with err flow and the focus tier.
(~~`cargo-sensorium 0.4.0`~~, before it ~~`sensorium-rt 0.4.0`,
`sensorium-transform 0.4.0`,
`cargo-sensorium 0.4.0`~~, before them ~~`sensorium-rt 0.3.0`,
`sensorium-transform 0.3.1`, `cargo-sensorium 0.3.1`~~, and before those
~~`sensorium-rt 0.1.0`, `sensorium-transform 0.2.0`,
`cargo-sensorium 0.2.0`~~: `sensorium-transform`
and `cargo-sensorium` moved to `0.2.0` on 2026-09-03 for the `spawn_child`
naming change in §3, all three moved to `0.3.0` on 2026-09-05 for wire v3
and the err-flow records of §11, those same two moved to `0.3.1` later
that day for the borrow repair — `sensorium-rt` did not move, because neither
the wire nor the runtime changed — all three moved to `0.4.0` on
2026-09-06 for the focus tier's new wire kind, LINE (§12), and
`sensorium-transform` alone moved to `0.4.1` on 2026-09-07 for the
brace-delimited-macro-tail guard (ruling G1): a `src` fix to what a focused
build EMITS, so neither the wire nor the runtime nor the driver moved, and
`cargo-sensorium` alone moved to `0.5.0` later that day for `--refocus-of`
and the three invocation-scoped meta keys it writes (design 2026-09-07
§2.1-§2.2) — a driver and converter change that neither the wire, the
runtime nor the transformer felt.
`HONESTY.md` was
not versioned per-crate before 2026-09-03, so no edition older than that is
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
document does not carry assertions. The index is
[`rust/HONESTY-INDEX.md`](HONESTY-INDEX.md): the whole list, two columns.

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
annotation. **Added 2026-09-05 (rung 3):** RAISE and HANDLED at `?` sites, the
four written sinks, `let _ =` and classified `Err` arms; frames for closures
holding a `?`; chains minted at conversion; and the dispositions
`sensorium exceptions` prints on a Rust trace — §11. **Added 2026-09-06
(rung 4, slice 1):** under `cargo sensorium --focus <qualname>`, one LINE
event per completed statement of a focused function, carrying the bindings
that statement wrote, which is what makes `watch` and `flow` answer here
instead of refusing — §12. Not `refocus`, not `--window`, not program output,
and nothing per-line in a function no `--focus` named. §8 is the list, with
what declares each absence.

---

## 1. What a frame's outcome means

The section — what `ok`, `err`, `panic` and `none` each mean, what the exit
operand proves and what it does not, and the falsifier for every clause — is
[`rust/HONESTY-OUTCOMES.md`](HONESTY-OUTCOMES.md) (moved 2026-09-05, the
borrow repair, so this file stays under 800 lines; **the wording and order
there are unchanged**, so `§1` still names what it always named, one file
away). It is the split `docs/CARRIED-DEBT.md` named at rung 3's close, taken
deliberately rather than discovered at the ceiling.

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
    (vi) a spawn in an expression position the overridden
    container visitors skip — a fn's SIGNATURE (an array-length expression in
    a return type is the shape that surfaced it), an `impl` header's self
    type, a trait's const-generic default — is neither rewritten nor declared:
    the three fn visitors descend into the body only, and
    `visit_item_impl`/`visit_item_trait` visit `items` only — a pre-existing
    rung-2 hole, found and dated 2026-09-03, carried as an open item in
    `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3; (vii) a
    `fn` item nested inside a `const`/`static` initialiser now carries that
    item's name as a qualname prefix (`X::h`, where rung 2 wrote `h`) — a
    `Site.qualname` change, more correct, zero instances on bloomery
    (untested by fixture as of 2026-09-03 — traced in the code only;
    rung-3 inbox).

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
  (its §4 — this ledger does not assert that document's verdict; the
  STOP-conjunct question its §5.1 left open was ruled 2026-09-04: (b)
  withdrawn; see the record §5.1).
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

The list itself — items 1–14 from rung 2, and items 15–26 that rung 3 adds
for err flow — is
[`rust/HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md) (moved 2026-09-05,
rung 3, so this file stays under 800 lines; **the numbering there is
unchanged**, so `§8 item 7` still names what it always named, one file away).
Item 2 is the one entry rung 3 rewrote: `?` sites, sinks and `Err` arms are
recorded now, and that item is narrowed to the traces an earlier runtime
wrote rather than struck.

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
  return **and once per captured delta** (§12) — and no more often than that:
  a LINE probe takes its deltas as a closure and formats them inside
  `thread::enter_runtime()` (design 2026-09-06 A5), so nothing is formatted
  for a delta under `SENSORIUM_TIER=off`, and nothing is formatted for a delta
  while a `Debug` impl of this program is already running.

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

## 11. Err flow

The section — which sites are recorded and under which `how`, what a chain is
and how its identity is derived, the five dispositions `sensorium exceptions`
prints and what each may mean, and the falsifier for every clause — is
[`rust/HONESTY-ERR-FLOW.md`](HONESTY-ERR-FLOW.md) (moved 2026-09-06, the focus
tier, so this file stays under 800 lines; **the wording and order there are
unchanged**, so `§11` still names what it always named, one file away). It is
the split this rung chose deliberately, the way rung 3 chose §1 and §8's list
before it, rather than one discovered at the ceiling.

## 12. The focus tier: LINE, and the deltas a statement wrote

Added 2026-09-06 by rung 4, slice 1
(`docs/superpowers/specs/2026-09-06-sensorium-rung4-focus-tier-design.md`, §3
and amendments A1–A12). `sensorium watch` and `sensorium flow` answer on a
Rust trace instead of refusing, and this section is what that answer may mean.
**None of it is true of a run without a `--focus`**: the tier is a
compile-time decision, so an unfocused build carries no LINE probe at all
rather than an inert one — §8 item 3 is what such a run still cannot see.

**One LINE per completed statement of a focused function, its `deltas` the
bindings that statement wrote and nothing else.** One probe after every
`syn::Stmt` at every block depth (§3.1), a parameters LINE first — even for a
function taking none (A2) — and a synthetic entry LINE for a `match`/`if let`
arm or `for` pattern that BINDS, once per entry or iteration, and none for one
that binds nothing (A3). A statement that `return`s, `break`s, `continue`s,
propagates with `?` or panics leaves no LINE of its own: its exit is already
the RETURN or RAISE row. A tail expression is not a statement, and a
bare-expression arm body becomes the wrapping block's tail (A1), so neither
takes a row. The tier re-probes a function on **every activation**, not once
per function.
*What says it in the trace*: `meta.focus`, the invocation's own list handed to
the converter and never read back out of an accumulated manifest (A9);
`meta.focus_matched`, the qualnames this build's own manifests matched;
`capabilities.line` and `capabilities.locals`, true only where some registered
unit of the run carries at least one LINE site; and `info`'s `focus:` and
`line=yes locals=yes` lines.

**`focus_matched` is an upper bound, because a manifest outlives the
invocation that wrote it** (added 2026-09-06, the whole-branch review's item
4): the union is taken over every in-scope manifest built under the same
CANONICAL focus (A9, A10), and manifests accumulate per focus (A8), so a
qualname can appear that this invocation did not build — a later run with a
different `-p`, or a function since deleted from a unit cargo saw no reason to
rebuild. It is bounded: same workspace, same focus, and it is a claim about
the BUILD only — `capabilities.line` / `locals` and `meta.sites` are the RUN's
own registered units and are unaffected, so no LINE row is ever attributed to
a function that did not produce it. The filter that would close it — keep a
match only where the manifest's source hashes are still present in the tree,
or its mtime is at or after the invocation's start — is `docs/CARRIED-DEBT.md`,
not taken here, because it is a `src` change after the measurement (R-F14).
*Falsified by* **E9 H3**
(`docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md` §4: **N = 26**
LINE rows over one activation of a real workspace function, against a count
hand-derived from these rules and locked before the transform could produce a
competing number — with **0** line differences against its per-line table);
`rust/sensorium-transform/tests/focus.rs` with the `golden_focus/` goldens,
compiled by the real rustc under `-D warnings`;
`rust/sensorium-rt/src/line/tests.rs`;
`rust/cargo-sensorium/tests/convert_frames.rs`; and the seven
`corpus/rust/focus_*` cases, each pinning a LINE count derived from these
rules and at least one ABSENCE. A delta naming a binding its statement did not
write would falsify it too, and of those the goldens are what would catch it.

**A dropped delta is stated, never silently short.** A LINE payload is bounded
by `LINE_PAYLOAD_MAX` — 2048 bytes, room for nine fully capped
eight-character-named deltas (A5). When the next delta would not fit, it and
every later one are dropped and `flags.bit0` is set, which reaches the row as
`unread: ["locals"]`: the same marker every Rust CALL carries, meaning the
same thing, that a reader was not shown something and is being told so. Each
value is `Debug` text capped at 200 bytes exactly as a return value is (§2),
so a binding whose type has no `Debug` reads `{"k": "unread"}` and a clipped
one carries `trunc`. **The drop rule is untriggered in measurement**, said
rather than left to be inferred from an absence: E9 reports `flags.bit0` never
set on any of its four runs, beside 5 unread and 3 truncated deltas of F1's 17
(record §3, *reported without a gate*).

**A LINE needs an open frame.** The parameters LINE is spliced after the entry
guard (A6), so a LINE always falls inside its own function's CALL; a LINE
record whose thread has no open frame is a malformed stream, and the converter
refuses it naming the record rather than attaching it to a guessed frame.
*Falsified by* `rust/cargo-sensorium/tests/convert_errors.rs`.

**What a reader may do with a `dbg` value is a rule, not a record**, and it is
written where a reader meets it: `docs/TRACE-FORMAT.md`'s `LINE` row and its
capability prose. `watch --expr` and `flow --value` read these captures as
Debug TEXT, and the two are inverses on the literal domain (A11) — what one
calls a sighting the other cannot deny at the same site. That is weaker than
Python's typed captures, and is stated as such rather than presented as an
equivalent.

## 13. Refocus: the recorded command, run again one flag deeper

Added 2026-09-07 by rung 4, slice 2
(`docs/superpowers/specs/2026-09-07-sensorium-rung4-refocus-design.md`,
rulings G1–G3 with amendments B1 and B2). `sensorium refocus <run> --focus
<name>` answers on a Rust trace instead of refusing, and this section is what
that answer may mean. **None of it is a claim that the two runs were the same
run** — §13's whole subject is a pair of executions and what comparing them
does and does not establish.

**What is re-run is the RECORDED command, never a command the reader
retyped.** `refocus` takes the original trace's own `cargo_args`, runs them
from the `workspace_root` that original recorded, under the same store, with
`--refocus-of <run>` first and unconditional, then the original's recorded
tier, then the original's `meta.focus` followed by the values this call added
— so a refocus only ever captures MORE, never differently (design §2.3). Five
questions are asked BEFORE anything is launched, and each answers at exit 2
with `nothing was re-run` in it: `--window` was given; the run is one of *n*
processes of its invocation (test binaries and doctests), so no single trace
is the answer; the trace records no `workspace_root`; that workspace is gone;
there is no `cargo-sensorium` to re-run with. A re-run has side effects, so
nothing about it is attempted speculatively.

**The pair is found in the store, never parsed out of what the driver
printed** (ruling G3). The driver stamps `refocus_of` into every process of
the new invocation; Python then lists the traces carrying that link whose
recording started after the launch. Exactly one is the pair. Zero — the driver
refused, cargo failed before recording, the invocation produced nothing — is
`verdict: REFUSED` after the rerun at exit 3, carrying the driver's exit ~~and
its last stderr line~~. **Corrected 2026-09-07** (design amendment B3): the
child's stderr is STREAMED and never captured — a focused rebuild's progress
belongs to the person waiting for it — so there is no last line to carry. The
refusal names the exit and points at what already printed: `the re-run
produced no trace linked to <run> (driver exit <n>); see the driver's output
above`. More than one is REFUSED by count. Neither case guesses.

**The verdict is about call shape and nothing else.** `diff_cmd.compare` is
slice-1's, unchanged: for a Rust pair the fingerprint is per task — a test, or
a spawned thread — over CALL, RETURN, RAISE and HANDLED, and **a LINE row
never enters the hash**, which is what lets a deeper re-run MATCH the run it
came from at all. Tasks are compared as an order-independent multiset of
`(name, hash)`, so which worker of a pool served which request is not a
difference; MATCH, DIVERGED and REFUSED keep the meanings and the exits (0 /
1 / 3) the README's `refocus` section gives them.
*What says it in the trace*: `meta.refocus_of`, the link; `meta.workspace_root`
and `meta.invocation_processes`, the two facts three of the five refusals are
read from; `capabilities.refocus`, true for every trace this driver converts —
whether one PARTICULAR trace can be refocused is a refusal, not a capability;
and the stamps `refocus_verdict`, `refocus_diverge_*`,
`refocus_refused_reasons` and `refocus_licence*` written into the NEW trace's
meta, which is what makes a verdict outlive the terminal it printed in.

*Falsified by* **E4 H3**
(`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md` §4: **61 of
61 MATCH**, 0 DIVERGED and 0 REFUSED over every `#[test]` of the seven
`pager_*_test.rs` files of a workspace nobody wrote this recorder for, one
test at a time under `--exact`, against an expected-MATCH list written and
byte-locked before the instrument existed); by `corpus/rust/refocus_match`,
`corpus/rust/refocus_diverged` and `corpus/rust/refocus_refused_many`, which
pin the three outcomes through the real driver; and by
`tests/test_refocus_rust.py` on fixture traces. A **MATCH on a pair whose
per-task fingerprints differ** would falsify it, and so would **a pair not
linked by `refocus_of`** — a verdict issued against a trace the store cannot
show came from this re-run is the failure this design's G3 exists to prevent.

**The licence beside the verdict is an enumeration, and on a `cargo test` pair
it is never granted.** Source and environment are checked for real
(`source_hashes` re-hashed now; the two traces' recorded `env` compared), and
so is the recorded process exit; `output` and `children` are printed and
stamped **`unverifiable`** rather than compared, because `capabilities.output`
and `capabilities.children` are `false` on a Rust trace and comparing two
empty sets would read as agreement — the named bug class (design §3.2). An
unverifiable check is **never counted as a verified one**; the two counts are
printed as two numbers and never summed. E4 measured that at n = 61: source
61 of 61, environment 61 of 61, exit 61 of 61, output and children
UNVERIFIABLE 61 of 61, and **0 licence lines claiming an unverifiable check as
verified** (record §3, §4 H4). What the same run also measured is that the
printed WORD was **WITHHELD on all 61** — the licence's untraced-thread clause
fires on every `cargo test` trace, because libtest runs each test on a thread
it spawns (thread counts 57×1, 1×2 and 3×5 across the 61 pairs). That is a
design question about what "the program's threads" means on a test harness,
recorded as a finding in that record's §5.2 and carried to
`docs/CARRIED-DEBT.md`; it is not applied here and no promise above depends on
it. On a `cargo run` pair with no harness thread the licence IS granted, which
`corpus/rust/refocus_match` pins over exactly four points.

---

## Index: promise → falsifier

The whole list — one row per promise, with what could falsify it — moved to
[`rust/HONESTY-INDEX.md`](HONESTY-INDEX.md) on 2026-09-05 (rung 3's final fix
wave) so this file stays under 800 lines: the deliberate split
`docs/CARRIED-DEBT.md` asked for. Same rows, same order, keyed by section.
