# Rung 3 inbox — what rung 2 leaves for the Rust recorder's next rung

**Provenance.** Rung 2 (`sensorium-rt`/`sensorium-transform`/`cargo-sensorium`
0.1.0) shipped DONE-WITH-STOP: four pre-registered endpoints
(E2′, E3, E7, E8) read PASS, one (E5) reads STOP. Full evidence is
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`. This
document is the inbox rung 3 opens with, written the way rung 2's own §11
entry condition was written for rung 2: an ENTRY DECISION for Brice first,
then the smaller deferred items collected across rung 2's task reviews
(`.superpowers/sdd/2026-09-02-sensorium-rung2-recorder-v1/deferred-minors.md`,
gitignored ledger) and this rung's own findings §5.

Nothing here is ranked by effort; the entry decision is listed first because
rung 3's own corpus cases will spawn tasks and inherit whichever answer to it
Brice picks — building rung-3 `?`/sinks/arm-classification cases against an
unresolved task-naming rule would mean re-authoring them once the decision
lands.

## 1. Entry decision: how should a spawned task's identity survive a move?

**DECIDED 2026-09-03: (b), by Brice.** The three options below are kept as
the record of the decision; the executing plan is
`docs/superpowers/plans/2026-09-03-sensorium-rung3-entry-spawn-names.md`
(endpoint E5′, `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md`).

**The measured gap (E5, STOP).** `diff --ignore-moves` pairs **code objects**
correctly across a source-file split — 28 paired, 0 added, 0 removed, on the
bloomery `registry.rs` split the acceptance run performed. It does **not**
pair **spawned tasks** across the same split, because a spawned task's name
is `<parent task name> :: spawn@<file>:<line>` (spec §3.5) and the split
moved the one `spawn_task` call site the registry has from
`registry.rs:769` to `registry/mod.rs:248`. Four spawned-child task names
therefore read as "only in A" / "only in B" even though their causal stream
hashes are pairwise identical on both sides
(`04afbcbcacf6`, `5976ef054dbe` ×2, `63737389821f`) — the same work, ran
under a renamed identity. The rule's own escape hatch ("if it is a
test-order change … read it as the instrument working, else STOP") does not
apply — libtest ran the same six tests in the same order on both sides — so
the acceptance decision rule resolves to STOP. Full transcript: acceptance
document §3 (E5) and §4.

**Three options, stated neutrally — this is Brice's call, not a rung-2
finding to act on unilaterally:**

- **(a) Project task names through `moves` the way code-object keys already
  are.** `diff --ignore-moves` already builds a `moves:` table pairing
  code objects across files by qualname; a spawned task's derived name could
  be rewritten through that same table before the multiset comparison runs,
  so a task whose *site* moved but whose *content* did not would pair. Cost:
  the projection has to agree with the code-object pairing exactly, including
  its own unpaired/ambiguous cases (spec §6 — a qualname that is A-only or
  B-only under two or more files is not paired), so the task-name projection
  inherits every edge case the code-object one already has, doubled.
- **(b) Name a spawned task by something a move does not change** — the
  enclosing fn's qualname plus an ordinal, `<parent> :: spawn@<qualname>#k`,
  instead of a file:line. Cost: two spawn sites inside one enclosing fn
  become order-dependent (`#1`, `#2`, …), and an ordinal is a weaker identity
  than a source location for a human reading `tree`/`grep` output directly —
  a location tells a reader where to look; an ordinal does not.
- **(c) Treat unpaired-by-name tasks whose *projected streams* hash equal as
  a move in the verdict**, rather than as an addition and a removal. Cost:
  this is a verdict-time patch rather than a naming fix, so the task's
  *stored* name still changes across the move (any reader who diffs task
  names directly, outside `sensorium diff`, still sees a rename); it also
  requires computing and comparing every unpaired task's stream hash even
  when the counts already look wrong, which (a) and (b) do not.

**The controller's recommendation is (b).** It is stable across exactly the
kind of move E5 tested (a file split) the same way code-object keys already
are (`(file, qualname, kind)` — the line is deliberately excluded from that
key, spec §5.4), it requires no change to the `moves:` projection machinery,
and it changes no `diff` output at all for a workspace that never moves a
spawn site (the ordinal is `#1` for a fn with one spawn, unconditionally).
This is the controller's own read, stated separately from the three options
above, which are stated neutrally.

**Whichever way this is decided, spec §3.5 and `rust/HONESTY.md` §3 need a
dated amendment recording the rule actually shipped, and a new corpus case
(`corpus/rust/spawn_across_move` or similar) pinning it — a rule with no
falsifier is not a promise (`rust/HONESTY.md`'s own standard).**

**Shipped 2026-09-03.** Both amendments landed: spec §3.5 and
`rust/HONESTY.md` §3 state the `<parent> :: spawn@<qualname>#<k>` rule. Its
falsifiers are `rust/sensorium-transform/tests/golden.rs`
(`a_spawn_site_is_named_by_its_enclosing_fn_and_its_ordinal`, fixture
`spawn_ordinals`), `rust/sensorium-transform/tests/edges.rs` (the
container-scope refusal), the new corpus case `corpus/rust/spawn_across_move`
(the spawning fn moved between two files across two runs of one crate, paired
by `diff --ignore-moves` and seen by plain `diff`), `corpus/rust/spawned_thread`
re-pinned to the new name, `rust/tests/mechanics.sh`, and the E5′ acceptance
record `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md`.

**Measured 2026-09-03:** E5′ (does `diff --ignore-moves` pair spawned tasks
across the move under rule (b)?) reads PASS and E5′-coverage reads PASS, but
E5′-names reads STOP on its second conjunct — a pre-registration defect, not
a product defect, because §1 named the trace's *stored* `task_fingerprints`
hash (which hashes `file` by design and so cannot equal across a move) as the
Method while its derivation column actually quoted the differ's *projected*
values; the repair (read the conjunct on the projected comparison, or drop it
and let E5′'s own pairing condition carry it) was ruled 2026-09-04: (b)
withdrawn; see the record §5.1.

## 2. Rung 3's own scope, unchanged from the spec

`?`, sinks, `Err`-arm classification, closures containing `?`, the Rust
`exceptions` disposition rules (SWALLOWED/PANICKED/RETURNED-TO-HARNESS/
AMBIGUOUS-by-default) and chain identity — spec §3.3, §6, §8 (E6). The
falsifier named ahead of time, in `rust/HONESTY.md` §1: `corpus/rust/outcome_generic`
— a generic `T` that is a `Result` only after monomorphisation reads `ok`,
untested until the generic-return-type case has a home.

**DONE 2026-09-05, DONE-WITH-PASS after a STOP and a repair slice.** Every
item above shipped: design
`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`
(R1–R16, §2a), plan
`docs/superpowers/plans/2026-09-04-sensorium-rung3-err-flow.md`, ledger
`rust/HONESTY.md` §11 with `rust/HONESTY-BLIND-SPOTS.md` items 15–26,
versions 0.3.0 / Python 0.8.0. E6′ read **STOP** (1 false SWALLOWED of 15,
`memory.rs:131`) on 2026-09-04; the R2 amendment was pre-registered and
re-measured, and E6‴ read **PASS** (0 false of 14, both arms, both readings)
on 2026-09-05 — the two acceptance records are
`docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md` and
`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md`. The
falsifier named ahead of time now has a home and is green:
`corpus/rust/outcome_generic`.

## 2a. Rung 4's inbox, opened by rung 3

Written the way rung 2 wrote this document's §1–§3: what the next rung starts
with, none of it ranked, each item with the thing that would settle it.

- ~~**LINE and locals under `--focus`** — the focus tier itself, spec §11 rung 4
  and §3.7. `capabilities.line`/`locals` are `false` today and every `watch`
  and `flow` refusal names them.~~ — **shipped 2026-09-06** as rung 4 slice 1
  (Python 0.8.3 / crates 0.4.0). One LINE per completed statement of a focused
  function, its `deltas` the bindings that statement wrote; `watch` and `flow`
  answer on such a trace. Measured once as **E9**, six PASS and one REPORTED,
  all seven rows as pre-registered, with **N = 26** and no line differing
  (`docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md`). The
  promise is `rust/HONESTY.md` §12; what a focus still does not reach is
  `rust/HONESTY-BLIND-SPOTS.md` item 3, narrowed rather than struck.
- ~~**`refocus` on a Rust trace** — `capabilities.refocus: false`; the Rust side
  is re-invocation, and the E4 endpoint is unmeasured. *(2026-09-06: this and
  `--window` are what rung 4's **slice 2** is, the focus tier having taken
  slice 1.)*~~ — **shipped 2026-09-07** as rung 4 slice 2 (Python 0.8.4 /
  `cargo-sensorium` 0.5.0 / `sensorium-transform` 0.4.1). `sensorium refocus
  <run> --focus <name>` re-runs the RECORDED invocation from the recorded
  `workspace_root` under the added focus, finds the pair in the store by
  `refocus_of`, and issues the comparator's unchanged verdict; five pre-rerun
  refusals answer first, each at exit 2. **E4 is measured** — five PASS and
  two REPORTED, all seven rows as pre-registered, **61 of 61 MATCH** with 0
  DIVERGED and 0 REFUSED over every `#[test]` of a real workspace
  (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md`). The
  promise is `rust/HONESTY.md` §13; what a re-run still does not compare is
  `rust/HONESTY-BLIND-SPOTS.md` item 12, narrowed rather than struck. ~~One
  finding is carried rather than fixed: the licence is structurally WITHHELD
  on every `cargo test` pair, by its untraced-thread clause
  (`docs/CARRIED-DEBT.md`, this slice's section).~~ — **taken 2026-09-07** by
  rung 4 **slice 3** (ruling R1, `11b7e8a`): libtest's per-test thread is the
  harness thread, out of the licence's untraced-thread counts and named on
  every line one of them appears on. **E4′** then measured the exclusion
  holding on 61 of 61 pairs while the word stayed WITHHELD on all 61 — by the
  ENV clause on `RUSTDOCFLAGS`, whose driver-injected rt-hash fragment is the
  recorder's own read as the world's (H1 **STOP**,
  `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md` §4). Carried
  to the next slice: strip the fragment, re-measure as E4″.
- **`--window` on a Rust trace remains open.** It needs a per-activation
  runtime check the Rust runtime does not have, so slice 2 refuses it by name
  at exit 2 rather than approximating it. ~~`docs/CARRIED-DEBT.md` carries the
  ruling owed on whether the window is a runtime check or a second
  compile-time selector.~~ — **Ruled 2026-09-07** by slice 3 (design
  `2026-09-07-sensorium-rung4-debts-design.md` §0, **R6**): **NOT FUNDED**
  until a use asks, together with refocus over a multi-process invocation, an
  inference-variable opt-out and a per-site volume cap; the declared blind
  spots stand. No ruling is owed any more — the item stays open because
  nothing shipped, and the refusal at exit 2 is still what a reader meets.
- **`.is_err()` / `.is_ok()` as OBSERVATION tags, not sinks.** Rung 3 dropped
  them from the probe list because a HANDLED there would report a predicate as
  a swallow (R2's erratum). The shape a reader still wants is a third class —
  *observed* — that says the program looked at the failure and names where,
  without ever being a SWALLOWED candidate. It would also settle the match-guard
  wording debt that E6‴ §5.2 leaves open (R15's ruling settles the verdict;
  it does not give the reader a word for what the guard did). *(2026-09-05,
  rung-4 entry N1: the WORDING debt is paid — `rust/HONESTY.md` §11 now says
  "Reading the error does not carry it out" and "a guarded arm's disposition
  is its body's" in the rule itself. What stays open here is the second half:
  a reader still has no WORD for what the guard did, which is what an
  observation tag would give.)*
- **An `.unwrap()` / `.expect()` probe — NOT demanded by the measurement.**
  Rung 3 derived PANICKED from the panic hook instead, and said an E6′ demand
  would re-open it. There was none: the clone's tallies are
  `swallowed 15, ambiguous 7` (E6′) and `swallowed 14, ambiguous 8` (E6‴) —
  **no PANICKED line at all on either run**, so the shape the probe would
  sharpen never occurred. Re-open it on the first target whose tally carries
  panics, not before.
- **A `--workspace` E6 slice with no `--lib`.** E6‴-W widened the selector and
  reached the same 2 of 29 located blast-radius arms, so the widening bought
  no coverage (E6‴ §5.1). Dropping `--lib` — integration tests, binaries,
  doctests — is the next measurement that could. *(X, 2026-09-08: closed by the borrow repair's
  **E6⁗-WS**, a `--workspace` arm with no `--lib` — 0 false rows of 782 over
  144 processes (`docs/CARRIED-DEBT-ARCHIVE.md`, the borrow-repair section).
  The measurement this item asked for was taken; nothing came back to mark
  it)*
- **A `chain.holder` field on the wire.** The holder is derived twice today
  (once in the converter's machine, once by the Python reader walking outward
  from a chain's last event); one field would delete both walks.
- **Three `chain.terminal` values with no conformance vector** —
  `panicked` (`tests/test_exceptions_rust.py`), `left_thread` and
  `handled_then_failed` (`tests/test_exceptions_rust_ambiguous.py`), pinned by
  the Python suite alone (`docs/trace-format/VECTORS.md`). *(Closed 2026-09-08
  by the queue slice's final fix wave, inventory row #23: the three vectors are
  `v20-exceptions-rust-panicked`, `v21-exceptions-rust-left-thread` and
  `v22-exceptions-rust-handled-then-failed`, each mutated on its own `terminal`
  and each reddening. The item above stands as written; this line is appended,
  never edited into it.)*
- **The in-source acknowledgment marker** — *added 2026-09-05 by the rung-4
  entry slice (design N8, deferred with its notation decided).*
  `// sensorium: acknowledged swallow — <reason>`, read by the transformer,
  carried through the manifest and the converter, and printed as
  `acknowledged N`. It is the shape that settles the three classes a reader
  may reasonably contest (`docs/CARRIED-DEBT.md`, the borrow-repair section):
  test-assertion arms, payload-free failures translated into a synthesised
  value, and a re-worded absence. It is Rust-side and a slice of its own. A
  file:line allowlist is rejected rather than deferred — such keys rot when
  lines move.
- **Grouping for Python traces** — *added 2026-09-05 by the rung-4 entry
  slice (design N7).* `exceptions` now prints one block per SHAPE on a Rust
  trace and one block per RAISE on a Python one, so the two languages differ
  in grain for a release. Closing it needs the thing the Rust side had to
  define first: **the site each Python disposition's verdict is about**, which
  is what the shape key is built from. The Rust key is
  `(tag, (file, line, qualname) of that site, masked verdict)`, with the
  origin site — and its masked route — standing in for every verdict that
  names no site.

## 3. Deferred minors carried out of rung 2's task reviews

Collected from `deferred-minors.md` (gitignored, in the rung-2 ledger) and
this rung's acceptance findings §5, none of which blocked rung 2 and none of
which is ranked:

- The rung-2 plan's Task 8 line for `runs`'s invocation header specified a
  `[exit <cargo_exit>]` suffix that correctly did not ship (cargo's own exit
  status is not something any process witnessed) — tidied, dated, in
  `docs/superpowers/plans/2026-09-02-sensorium-rung2-recorder-v1.md`. *(X, 2026-09-08: this item records its own
  closure — the plan line was tidied and dated. Marked here so a reader
  counting open items does not count it)*
- `diff --task` help text is still Python-worded on a Rust trace. *(Taken 2026-09-08 at `0d685ad`: the help line
  reads in the recorder's own words through `vocab.py`, and the corpus gate
  ran WITH the driver behind it)*
- `vocab.interp_line`'s `or "?"` fallback branch has no fixture reaching it. *(Taken 2026-09-08 at `0d685ad`: one fixture
  reaches the branch)*
- The Python `live_threads` line's pre-existing asymmetry (present before
  rung 2, not touched by it).
- Malformed-meta robustness in the Rust converter's read path (an orphan
  `.proc.json.tmp`, a mirror path leaking into a manifest) is hard-erred by
  name today; no fixture exercises the error text itself. *(Taken 2026-09-08 at `d836a77`: five fixtures
  in `tests/convert_errors.rs`, one per malformed-metadata refusal in the
  read path)*
- `mint()` isolating test — `runid::mint`'s one-line forward (it must consult
  its own `minted` parameter, not just the directory) has no deterministic
  test that would catch that line reverting; the one mutation of Task 6's
  review that survived was caught by inspection, not by a test
  (`task-6-report.md`, "Concerns carried forward"). *(Taken
  2026-09-08 at `74d5fbb`:
  `convert::runid::tests::mint_consults_the_minted_set_and_not_only_the_directory`
  reddens when `minted` is ignored)*
- `Report`/`TraceSummary` unused — the in-process return value of
  `convert_dir` is not read by either caller today (the driver seam and the
  `convert` role both check only `Result::is_err`); kept, with an
  `#[allow(dead_code)]` and a comment, as the extension point a future
  in-process caller will want (`task-6-report.md` line 263). *(X,
  2026-09-08: closed by decision, not by work — the `#[allow(dead_code)]`
  and its comment ARE the disposition, and the item stood unstruck only
  because nothing came back to mark it)*
- Panic-RETURN tag validation — no test pins that a frame closed by a panic
  writes the RETURN wire tag/outcome the converter expects, independent of
  the writer that produced it (deferred at Task 6's review). *(Taken 2026-09-08 at `852a0f5`: the panic path
  is pinned by wire number, writer-independently, with its ok-outcome
  control beside it)*
- Panic serial numbering on outside-frame panics — a PANIC record with no
  open frame to attach to (`panics_outside_frames`) has no test pinning how
  its serial is assigned or read back (deferred at Task 6's review). *(Taken 2026-09-08 at `852a0f5`: a panic with no
  open frame is shown to consume its thread's panic serial)*
- `runid`/driver id-mix helper — a small duplication between the driver's and
  the converter's run-id minting, not yet factored out. *(Taken
  2026-09-08 at `74d5fbb`: one mix for both minters, with a test saying the
  salt is the only addition)*
- A byte-exact pin for the `run:` line's own format (Task 9's conformance
  fixtures may be the right place). *(Taken
  2026-09-08 at `a9a5ed1` (with `245dee4`): `RUN_LINE` anchors the line's own
  keyed shape and its comment names all three shapes the writer emits — the
  same commit that closed the reader half of this pair)*
- The probe workspace's shared `SITE_*` consts. *(Reported 2026-09-08, not taken: `SITE_`
  matches nothing under `rust/probes/` or `rust/tests/` at this slice's HEAD.
  Reads as obsolete, and "I cannot find it" is not "it was fixed")*
- The tid-mask justification (why a recycled OS thread id is safe) is
  reasoned about in review notes but not written into the suite itself. *(Taken 2026-09-08 at `91f737d`: the paragraph is
  in `rust/sensorium-rt/tests/panics.rs` beside `mask_thread_ids`, saying
  why recycling makes masking safe and why E7's promise was never about the
  number)*
- `Fixed`/`CapWriter` duplication between `sensorium-rt` and
  `sensorium-transform`'s test helpers (pre-existing, widened by one). *(Reported 2026-09-08, not taken: neither name is in
  `sensorium-transform` at HEAD. The duplication that does exist is two
  capped `fmt::Write` types inside `sensorium-rt`'s own production code with
  different cap semantics — a behaviour-risk merge, not a line)*
- Two `sensorium-rt` tests with no single-line mutation demonstrated against
  them yet. *(Reported 2026-09-08, not taken: it needs a
  mutation campaign rather than a line, and the review that filed it named
  neither test, so its subject is not decidable from the source)*
- `rust/tests/mechanics.sh`'s dependency-proxy shape for driving the built
  binary. *(Reported 2026-09-08, not taken: reshaping it is
  design work that lands on top of a split `mechanics.sh` still owes (795 of
  800))*
- Identifier naming for the acceptance runner's pair counts. *(Reported 2026-09-08, not taken: out of the
  taking task's file scope (`rust/tests/*.py`))*
- The `_sub` docstring in the acceptance runner. *(Reported 2026-09-08, not taken: same scope)*
- Unused `gen.py` encoders in the cross-recorder fixture generator. *(Reported 2026-09-08, not taken: same scope
  (`tests/fixtures/rust-spools/gen.py`))*
- `trace._c` private-attribute access from a Python test helper. *(Reported 2026-09-08, not taken: same scope)*
- `cargo_driver()` re-resolved once per test case rather than cached. *(Reported 2026-09-08, not taken: a cache has to
  live where all four callers can see it, which is the shared-helper move
  taken at `a9a5ed1` — the caching half was not)*
- The acceptance runner's `"$RUN2" in str(spec)` scan (works, reads as
  incidental rather than designed). *(Obsolete 2026-09-08: the scan reads `q["command"]` and carries the
  comment this nit asked for)*
- Abort core files: `corpus/rust/abort`'s child runs under whatever ulimit
  the box has, and a permissive one leaves a core file the corpus does not
  clean up. *(Taken 2026-09-08 at `a9a5ed1`: the case cleans
  its own core file)*
- `rust/sensorium-rt/src/bin/scenario.rs` sits at exactly 800 lines (the
  house limit) — the next task that adds a test arm to it must split it into
  `src/bin/scenario/` first; none was planned before this document. *(Still
  true after the final fix wave: its one new arm reused an existing scenario.
  Source: final review 2026-09-03.)* *(X, 2026-09-08: split to `src/bin/scenario/`;
  `scenario.rs` is 245 lines)*
- `convert/mod.rs:141-147`'s WARN counts runner records, and on cargo 1.96
  those include doctest processes — so "N test binaries" can overstate by the
  doctest count. Source: final review 2026-09-03. *(Taken 2026-09-08 at `9c82fde`: the WARN counts
  test binaries apart from doctest processes, with three tests behind it)*
- `convert_perf.rs:57`'s test name (`a_hundred_thousand_record_spool_converts_in_seconds_not_minutes`) promises "seconds not minutes"; its own
  doc says the mutation it was written for measured 2.5 s under a 5 s bound.
  Honest as a floor, but the name reads as a fence. Source: final review
  2026-09-03. *(Taken 2026-09-08 at `6abcc27`: renamed for the
  bound it asserts)*
- Function lengths against the "under 50 where the language allows"
  constraint: `frames::process` 274, `convert_one` 164, `wrapper::instrument`
  112, `driver::go` 100, `convert_dir` 99, `write_proc_header` 88. Bodies are
  linear and commented; style only. Source: final review 2026-09-03. *(**Ruled 2026-09-08 (R4): NOT this slice.**
  Splitting the converter's core is behaviour-risk work with no failing test
  behind it; it goes to the C conversation as a refactor needing its own
  review)*
- A spool whose first `ftruncate`/`mmap` fails leaves a 0-byte
  `<pid>.<serial>.spool` (`spool.rs:126-134`) that the converter refuses by
  name (`convert/spool.rs:66-71`), so one thread's inert-at-open costs the
  whole invocation's conversion. **A rung-3 design choice, both options
  stated:** unlink the file on open failure (the runtime owns the failure and
  leaves nothing behind, at the cost of losing the evidence that a thread
  tried), or have the converter treat a 0-byte spool as "opened and wrote
  nothing" with `records_dropped` unknown (the evidence survives, at the cost
  of a spool the trace cannot bound). Source: final review 2026-09-03.
- A spawn in an expression position the overridden container visitors skip is
  neither rewritten nor declared. The class: a fn's SIGNATURE (an array-length
  expression in a return type, e.g. `fn n(&self) -> [u8; { ..closure that
  spawns.. }]`, is the shape that surfaced it), an `impl` header's self type,
  and a trait's const-generic default. The three fn visitors descend into the
  body only, and `visit_item_impl`/`visit_item_trait` visit `items` only.
  Source: rung-3 entry slice 2026-09-03; class widened by the final review
  2026-09-04. *(Declared 2026-09-08 by the queue slice:
  `rust/HONESTY-BLIND-SPOTS.md` **item 31**, which is the A half of this
  item. Rewriting those positions stays a C item)*
- `visit_trait_item_const` (an associated const's default value inside a
  `trait` item) is a real code path — `in_item` names it exactly like
  `visit_item_const`/`visit_impl_item_const` — but no golden or edge-case
  fixture reaches it. Source: rung-3 entry slice 2026-09-03. *(Taken 2026-09-08 at `d17eb20`: the golden
  `fns_nested_in_const_static_and_trait_const_initialisers` reaches it)*
- `diff`'s verdict vocabulary: `MATCH modulo location` prints only on the
  thread-stream branch that has at least one causal event outside a task; a
  trace whose events all live in tasks instead reads `verdict: MATCH -- no
  causal event ran outside a task on either side, so the thread streams held
  nothing to compare; the tasks below carry the whole verdict`, even when
  code objects paired across a move (the `key:` line says so) — the wording
  should carry "modulo location" there too. Source: rung-3 entry slice
  2026-09-03. *(Taken 2026-09-08 at `0d685ad`: it does, and the
  corpus gate ran WITH the driver behind the changed sentence)*
- Golden for a fn nested inside a const/static initialiser (`X::h` prefix) —
  Source: rung-3 entry slice 2026-09-03. *(Taken
  2026-09-08 at `d17eb20`, the same golden)*
- Fixture for a REFUSED crate-root file on the WRAPPER-BINARY path — the
  stderr line, `fell_back: false`, and the empty `files` as the driver writes
  them, for a root refused by a synthesised error. The plan level is already
  unit-tested: `wrapper.rs`'s
  `a_unit_whose_crate_root_cannot_be_rewritten_is_left_wholly_alone` builds a
  unit whose root does not parse and asserts `files`/`source_hashes`/
  `rewrites` cleared with `unreached_reasons` surviving; `wrapper_fallback.rs`'s
  `a_file_the_transformer_refused_names_its_reason_on_both_channels` covers a
  refused child file on the binary path. Source: rung-3 entry slice 2026-09-03
  (fix round 1); narrowed by the final review 2026-09-04. *(Taken 2026-09-08 at `017a4a1`:
  `a_refused_crate_root_leaves_the_unit_empty_without_calling_it_a_fallback`
  pins the stderr line, `fell_back: false` and the empty `files`)*
- No unit tests on the acceptance instruments (`rust/tests/acceptance*.py`,
  `render_acceptance.py`) — repo-wide; mitigated by byte-identical re-renders
  in review. Source: rung-3 entry slice 2026-09-03 (Task 5 review).
- The converter's `spool.rs` tests create a temp dir under
  `std::env::temp_dir()` and never remove it
  (`rust/cargo-sensorium/src/convert/spool.rs:534`, `:549`, `:575`) — the
  module's pattern, not a regression of the newest of the three; a scope guard
  would tidy all three. Source: final review 2026-09-04. *(Taken 2026-09-08 at `1530f68`: a scratch
  directory removes itself when it leaves scope, on an unwind too)*
- `refocus --window QUALNAME` reads as a size/range to the prior; rename
  candidate `--lines-in` or fold into `--focus` — deferred until the
  invocation-log census says agents trip on it. Source: exit-status slice
  2026-09-04 (X9).

None of the above changes a shipped behaviour; each is either untested
surface, a naming/factoring nit, or an operational note. They are listed here
so rung 3 does not have to re-discover them from `deferred-minors.md`, which
is gitignored and local to the rung-2 branch's own ledger.
