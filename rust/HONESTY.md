# The Rust recorder's honesty ledger

`sensorium-rt 0.3.0`, `sensorium-transform 0.3.1`, `cargo-sensorium 0.3.1` —
v1, the call tier, with err flow. (~~`sensorium-rt 0.1.0`,
`sensorium-transform 0.2.0`, `cargo-sensorium 0.2.0`~~: `sensorium-transform`
and `cargo-sensorium` moved to `0.2.0` on 2026-09-03 for the `spawn_child`
naming change in §3, all three moved to `0.3.0` on 2026-09-05 for wire v3
and the err-flow records of §11, and those same two moved to `0.3.1` later
that day for the borrow repair — `sensorium-rt` did not move, because neither
the wire nor the runtime changed; `HONESTY.md` was not versioned per-crate
before 2026-09-03, so no edition older than that is struck.)

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
`sensorium exceptions` prints on a Rust trace — §11. Not locals or LINE
(rung 4), not `refocus`, not program output. §8 is the list, with what
declares each absence.

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

## 11. Err flow

Added 2026-09-05 by rung 3
(`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`,
R1–R16 and its §2a chain machine). `sensorium exceptions` answers on a Rust
trace instead of refusing, and this section is what that answer may mean. It
is **§11, not the §10 the plan wrote**: §10 is rung 2's shipped cost section,
and §-numbers here are cited from code comments as identifiers.

**Only written sites are recorded, and the words are the site's own.** A
record exists at a `?` on a `Result` (`how: try`), at an `.ok()` receiver
(`sink_ok`), at an `.unwrap_or(..)` / `.unwrap_or_else(..)` /
`.unwrap_or_default()` receiver (`sink_unwrap_or`), at a
`let _ = <value expression>` (`sink_let_underscore`), and at an `Err(..) =>`
arm or `if let Err(..)` body classified by what its body does —
`arm_propagate`, `arm_handled`, or `arm_ambiguous`. `exit` is the converter's own `how`, on the origin RAISE it
synthesises in front of a frame that closed `err`, and never arrives on the
wire. Everything else is unprobed **on purpose**, and its `Err` reads
AMBIGUOUS rather than being guessed at: `.unwrap()`, `.expect()`,
`.is_err()`, `.is_ok()`, a panicking arm, and the shapes §8 items 15–26
enumerate. *Falsified by* `rust/sensorium-transform/tests/errflow.rs` and
`golden_errflow.rs` (a golden per shape, compiled by the real rustc under
`-D warnings`), and `rust/sensorium-rt/tests/err_flow.rs`.

**A `?` the transformer could not reach is declared, not lost.** The unit
manifest carries a `partial` row `{file, line, qualname, kind, reason}` for
each, reason `macro-arg` (a `?` among a macro invocation's tokens),
`async-block`, or `struct-literal` (a `match` scrutinee beginning with a
struct literal does not parse, so the wrap is refused). They reach the trace
as the meta key `partial`, and both `info` and `exceptions` print the block —
so a reader is told the grammar had a hole *before* reading a tally computed
without it. *Falsified by* `corpus/rust/macro_arg_partial`, the goldens
`try_in_macro_arg` / `async_block_try` / `struct_literal_partial`, and E2″
below, whose `partial` count was pre-registered as a number and met it.

**The wrap moves no line, and shifts a column in exactly two places.** Every
injected fragment is newline-free (§9), so `file!()`, `line!()`, panic
locations and backtraces stay the plain build's under rung 3's new wraps too.
The two places are the 2026-09-04 record's §5.4 clause, adopted here
2026-09-05. **(a) Inside a wrapped `?`/sink/`let _` operand** — a panic literal
moves right by the wrap prefix's byte length, `match ` = **6 bytes**, and by
nothing else: **measured**, predicted before the run and met exactly at both
tiers (plain `e7_operand.rs:33:24`, instrumented `:33:30`). **(b) After an arm
probe or closure guard spliced at a same-line `{`** (or a `{ probe; expr }`
wrap) — everything after the probe on that line moves by *the probe's own byte
length*, not by 6; the shape is
`rust/sensorium-transform/tests/golden/err_arms_three_ways.out.rs:14`
(`Err(e) => { @P(9,HOW_ARM_PROPAGATE,e) Err(e) },`): **stated, unmeasured**.
*Falsified by* E7″ and E7‴ (§3 of the two acceptance records below) and
`rust/tests/mechanics.sh`'s six E7 checks, 0 differences in both runs — which
cover (a) and the *nowhere else* half; the missing check for (b) is
`docs/CARRIED-DEBT.md`.

**Chain identity is a derivation, and its limits are stated on the wire.**
There is no error identity on the wire at all: chain serials are minted at
CONVERSION from the per-thread record order, in a namespace disjoint from
panic serials (`exc.kind` is `"err"` or `"panic"`, and a reader selects on
that key, never on `type == "panic"`). A chain is followed by
`(holder frame, type, Debug text)`, so **two `Err`s of one type with
identical `Debug` text in one window are one chain**, and a text the probe
had to truncate is no identity at all — matching falls back to the type,
which can only merge, never split. The **holder** of a chain is likewise
derived, not carried: the Python reader walks outward from the chain's last
event to name the frame that held it. *Falsified by*
`rust/cargo-sensorium/src/convert/chains/`'s unit tests (`tests.rs`) on hand-built
spools, `corpus/rust/interleaved_chains`, and the vector
`v16-raise-handled-chain-serial-kind`.

**What each verdict claims, and what it does not.**

- **SWALLOWED** — a written sink or an `arm_handled` absorbed the chain in a
  frame that then closed `ok`, with no later RAISE of it. It says the failure
  did not reach the caller, not that the program was wrong to do that. A
  chain first seen at the sink itself is still SWALLOWED, detailed *born
  outside this thread's instrumented frames* — *this thread*, because the
  machine is per-thread and an `Err` handed over a `JoinHandle` is
  unknowable to the receiver by construction.
- **PANICKED** — the frame holding the chain unwound, quoting `unwind_exc`
  or saying the message was not recorded (§1). It says **the frame holding
  it unwound**, never that the panic happened *because of* the `Err`.
- **RETURNED_TO_HARNESS** — the chain left a frame whose manifest site is
  `test: true` or `main: true`. A fact about the mark, not about intent.
- **PROPAGATED** — the chain crossed ≥ 1 frame and was still open when the
  recording ended, on a frame neither marked. Every hop is listed, and the
  verdict says so: reachable only where the thread was still live at the end
  (`live_threads`) or its frames were not all instrumented.
- **AMBIGUOUS** — the default, and the largest class by design: an escaped
  binding, a merged window, a holder that closed `ok` with no sink seen, a
  chain absorbed in a frame that then failed for another reason
  (`handled_then_failed`), a chain that left a spawned thread into a
  `JoinHandle`. It is what the instrument says instead of guessing, and E6's
  whole job is that nothing leaks from here into SWALLOWED.

*Falsified by* `tests/test_exceptions_rust.py` and
`tests/test_exceptions_rust_ambiguous.py` — one test per §2a row, split
across the two at the 800-line ceiling — the vectors
`v17-exceptions-rust-swallowed` and `v18-exceptions-rust-ambiguous-merge`,
and sixteen `corpus/rust/*` cases: `silent_swallow`, `logged_arm`,
`dependency_swallow`, `err_stored`, `err_rendered_into_value`,
`cleanup_then_fail`, `interleaved_chains`, `err_arms`, `err_propagation`,
`returned_to_harness`, `closure_try`, `join_handle`, `unwrap_panic`,
`outcome_generic`, and — added 2026-09-05 by the borrow repair —
`err_borrowed_into_value` (`dispositions: ambiguous 1`, SWALLOWED registered
absent) and `keep_first_error` (`dispositions: swallowed 1, ambiguous 1`, the
one SWALLOWED line pinned to the arm that absorbed the chain).
**Three `chain.terminal` values are pinned by the Python suite only**, with
no conformance vector behind them: `panicked` by
`test_a_panic_on_the_holder_quotes_the_panic_and_claims_no_cause` in the
first file; `left_thread` and `handled_then_failed` by
`test_a_chain_that_left_a_spawned_threads_outermost_frame_is_ambiguous` and
`test_a_sink_whose_frame_then_failed_is_ambiguous_not_swallowed` in the
second. `docs/trace-format/VECTORS.md` says so too; closing it is a vector,
not a rule change.

**The capability, and the refusal on an older trace.** The runtime declares
`capabilities.err_flow: true` in the proc header and the converter passes it
through untouched rather than asserting it on its own authority — a header
without it reads `false`. `exceptions` dispatches on `trace.lang`, then
requires the capability, so a trace an earlier runtime wrote is REFUSED by
name at exit 3 and no rule sees its records. *Falsified by*
`docs/trace-format/vectors/v19-err-flow-capability-refusal.json` and
`tests/test_exceptions_rust_gate.py`.

**One thing the instrument does to your build that nothing else declares.**
The instrumented mirror carries
`#![allow(clippy::match_single_binding, clippy::needless_borrow)]` on every
crate root — the wraps are single-binding `match`es and can borrow needlessly
— so **a `cargo clippy` run UNDER the recorder would not report those two
lints in workspace code**. The plain tree is unaffected (§9: nothing is
written under a workspace except `<target>/sensorium/`), and a `Debug` impl
the probe invokes still runs, exactly as §9's last bullet says of return
values. *Falsified by*
`rust/sensorium-transform/tests/errflow.rs::the_crate_root_carries_the_allow_the_wraps_need`.

**One guard with no test, named rather than hidden.** The converter refuses a
RAISE/HANDLED record the chain machine minted no chain for
(`<label>: no chain was minted for this RAISE record`) — a defect guard on an
unreachable path (`err_flow_outside_frames` and the machine skip exactly the
same records), so no test exists: no input produces one without breaking the
converter first. Named here so a reader who ever sees that message knows it is
a converter bug, not a fact about their program.

**What this rung measured, both records.** Rung 3 was measured twice, and
both documents stand:

- `docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md` —
  **overall STOP**, on E6′. Six of seven endpoints PASS (E6 on 17 corpus
  cases, E2″ 392/401 = 97.76 %, E7″, E3″ 0/19, E5″, E0″ 0.046/0.047 s). E6′
  printed **15** SWALLOWED lines on the clone's `--lib` suite and **1 was
  false** under both readings: `build_memory` at `memory.rs:131`, an
  `Err(e) =>` arm whose `format!` PRODUCT is the value the function returns.
  The rule was wrong; the record says so, and nothing was re-run after the
  number was read.
- `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` — the
  repair slice, **overall PASS**. The R2 amendment (a bound name mentioned
  in `format!`/`format_args!`/`write!`/`writeln!` ESCAPES; only the logging
  family's bare arguments stay exempt) removed that accusation and bought no
  new one: **0 false of 14** on `-p bloomery-daemon --lib` and **0 false of
  14** on `--workspace --lib`, under the amended reading *and* the strictest
  pre-lock reading; E6-again equal on all three conjuncts over 18 corpus
  cases; E7‴ unchanged.

Two limits are part of that PASS, not footnotes to it. The widening to
`--workspace --lib` executed **the same 2** of the 29 located blast-radius
arms, buying no extra reach (§5.1 there). And **2 of the 14 lines are
match-guard arms** (`Err(e) if e.kind() == NotFound => { }`), which under a
letter-reading of "merely observed" would each be false and the verdict a
STOP; the gate is the amended reading, ruled durably in design R15 on
2026-09-05 — the disposition is the BODY's, and every table reports the
guarded-arm count beside both readings.

**The blind spots are §8, items 15–26**: the shapes err flow does not probe;
**one** residual false-accusation generator of the amended class (a
value-format macro nested inside a logging macro's argument), exposure on the
clone **measured zero** (2026-09-05 record §5.3), recorded rather than
repaired; a whole-word literal `e` in a non-logging macro, which over-escapes
in the **safe direction** (AMBIGUOUS, never an accusation) and whose exposure
is **measured nowhere**; and the `tracing`-field-syntax non-detection that
makes a low SWALLOWED count on some trees evidence of nothing. Each carries a
falsifier or the words **untested by fixture**.

**And one more the review found after the numbers were read — since
repaired.** The `&e` exemption was a fact about the BORROW alone, silent on
what the CALL does with its product. Since 2026-09-05 (the borrow repair,
design B1) a shared borrow is exempt only where the borrowing call's product
is provably dropped — an expression statement, a `let _ =`, or a logging
macro's argument — so
`Err(e) => { let (status, value) = map_error(&e, ..); V1Result::json(status, value) }`
reads AMBIGUOUS. **Measured, and the control discriminated**
(`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`): E6⁗-A
**PASS**, 0 false accusations of 14; E6⁗-WS **PASS**, 0 false of 782 over
144 processes of `cargo sensorium test --workspace`; and E6⁗-WS0
**DISCRIMINATING** — the same command under the PRE-repair driver printed 30
more lines, every one of them false, at 7 of the 11 arms the repair moved,
where the repaired driver printed none. Four of those 11 were never executed
by any arm of that run (§5.5 there). One residual stands: a callee handed
`&e` at a dropped call site that STORES a rendering through `&self`, a capture
or a global still reads `arm_handled` — item 23 **(d)**, R16 (vii),
**untested by fixture** on a real tree.

---

## Index: promise → falsifier

The whole list — one row per promise, with what could falsify it — moved to
[`rust/HONESTY-INDEX.md`](HONESTY-INDEX.md) on 2026-09-05 (rung 3's final fix
wave) so this file stays under 800 lines: the deliberate split
`docs/CARRIED-DEBT.md` asked for. Same rows, same order, keyed by section.
