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

## 3. Deferred minors carried out of rung 2's task reviews

Collected from `deferred-minors.md` (gitignored, in the rung-2 ledger) and
this rung's acceptance findings §5, none of which blocked rung 2 and none of
which is ranked:

- The rung-2 plan's Task 8 line for `runs`'s invocation header specified a
  `[exit <cargo_exit>]` suffix that correctly did not ship (cargo's own exit
  status is not something any process witnessed) — tidied, dated, in
  `docs/superpowers/plans/2026-09-02-sensorium-rung2-recorder-v1.md`.
- `diff --task` help text is still Python-worded on a Rust trace.
- `vocab.interp_line`'s `or "?"` fallback branch has no fixture reaching it.
- The Python `live_threads` line's pre-existing asymmetry (present before
  rung 2, not touched by it).
- Malformed-meta robustness in the Rust converter's read path (an orphan
  `.proc.json.tmp`, a mirror path leaking into a manifest) is hard-erred by
  name today; no fixture exercises the error text itself.
- `mint()` isolating test — `runid::mint`'s one-line forward (it must consult
  its own `minted` parameter, not just the directory) has no deterministic
  test that would catch that line reverting; the one mutation of Task 6's
  review that survived was caught by inspection, not by a test
  (`task-6-report.md`, "Concerns carried forward").
- `Report`/`TraceSummary` unused — the in-process return value of
  `convert_dir` is not read by either caller today (the driver seam and the
  `convert` role both check only `Result::is_err`); kept, with an
  `#[allow(dead_code)]` and a comment, as the extension point a future
  in-process caller will want (`task-6-report.md` line 263).
- Panic-RETURN tag validation — no test pins that a frame closed by a panic
  writes the RETURN wire tag/outcome the converter expects, independent of
  the writer that produced it (deferred at Task 6's review).
- Panic serial numbering on outside-frame panics — a PANIC record with no
  open frame to attach to (`panics_outside_frames`) has no test pinning how
  its serial is assigned or read back (deferred at Task 6's review).
- `runid`/driver id-mix helper — a small duplication between the driver's and
  the converter's run-id minting, not yet factored out.
- A byte-exact pin for the `run:` line's own format (Task 9's conformance
  fixtures may be the right place).
- The probe workspace's shared `SITE_*` consts.
- The tid-mask justification (why a recycled OS thread id is safe) is
  reasoned about in review notes but not written into the suite itself.
- `Fixed`/`CapWriter` duplication between `sensorium-rt` and
  `sensorium-transform`'s test helpers (pre-existing, widened by one).
- Two `sensorium-rt` tests with no single-line mutation demonstrated against
  them yet.
- `rust/tests/mechanics.sh`'s dependency-proxy shape for driving the built
  binary.
- Identifier naming for the acceptance runner's pair counts.
- The `_sub` docstring in the acceptance runner.
- Unused `gen.py` encoders in the cross-recorder fixture generator.
- `trace._c` private-attribute access from a Python test helper.
- `cargo_driver()` re-resolved once per test case rather than cached.
- The acceptance runner's `"$RUN2" in str(spec)` scan (works, reads as
  incidental rather than designed).
- Abort core files: `corpus/rust/abort`'s child runs under whatever ulimit
  the box has, and a permissive one leaves a core file the corpus does not
  clean up.
- `rust/sensorium-rt/src/bin/scenario.rs` sits at exactly 800 lines (the
  house limit) — the next task that adds a test arm to it must split it into
  `src/bin/scenario/` first; none was planned before this document. *(Still
  true after the final fix wave: its one new arm reused an existing scenario.
  Source: final review 2026-09-03.)*
- `convert/mod.rs:141-147`'s WARN counts runner records, and on cargo 1.96
  those include doctest processes — so "N test binaries" can overstate by the
  doctest count. Source: final review 2026-09-03.
- `convert_perf.rs:57`'s test name (`a_hundred_thousand_record_spool_converts_in_seconds_not_minutes`) promises "seconds not minutes"; its own
  doc says the mutation it was written for measured 2.5 s under a 5 s bound.
  Honest as a floor, but the name reads as a fence. Source: final review
  2026-09-03.
- Function lengths against the "under 50 where the language allows"
  constraint: `frames::process` 274, `convert_one` 164, `wrapper::instrument`
  112, `driver::go` 100, `convert_dir` 99, `write_proc_header` 88. Bodies are
  linear and commented; style only. Source: final review 2026-09-03.
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
  2026-09-04.
- `visit_trait_item_const` (an associated const's default value inside a
  `trait` item) is a real code path — `in_item` names it exactly like
  `visit_item_const`/`visit_impl_item_const` — but no golden or edge-case
  fixture reaches it. Source: rung-3 entry slice 2026-09-03.
- `diff`'s verdict vocabulary: `MATCH modulo location` prints only on the
  thread-stream branch that has at least one causal event outside a task; a
  trace whose events all live in tasks instead reads `verdict: MATCH -- no
  causal event ran outside a task on either side, so the thread streams held
  nothing to compare; the tasks below carry the whole verdict`, even when
  code objects paired across a move (the `key:` line says so) — the wording
  should carry "modulo location" there too. Source: rung-3 entry slice
  2026-09-03.
- Golden for a fn nested inside a const/static initialiser (`X::h` prefix) —
  Source: rung-3 entry slice 2026-09-03.
- Fixture for a REFUSED crate-root file on the WRAPPER-BINARY path — the
  stderr line, `fell_back: false`, and the empty `files` as the driver writes
  them, for a root refused by a synthesised error. The plan level is already
  unit-tested: `wrapper.rs`'s
  `a_unit_whose_crate_root_cannot_be_rewritten_is_left_wholly_alone` builds a
  unit whose root does not parse and asserts `files`/`source_hashes`/
  `rewrites` cleared with `unreached_reasons` surviving; `wrapper_fallback.rs`'s
  `a_file_the_transformer_refused_names_its_reason_on_both_channels` covers a
  refused child file on the binary path. Source: rung-3 entry slice 2026-09-03
  (fix round 1); narrowed by the final review 2026-09-04.
- No unit tests on the acceptance instruments (`rust/tests/acceptance*.py`,
  `render_acceptance.py`) — repo-wide; mitigated by byte-identical re-renders
  in review. Source: rung-3 entry slice 2026-09-03 (Task 5 review).
- The converter's `spool.rs` tests create a temp dir under
  `std::env::temp_dir()` and never remove it
  (`rust/cargo-sensorium/src/convert/spool.rs:534`, `:549`, `:575`) — the
  module's pattern, not a regression of the newest of the three; a scope guard
  would tidy all three. Source: final review 2026-09-04.
- `refocus --window QUALNAME` reads as a size/range to the prior; rename
  candidate `--lines-in` or fold into `--focus` — deferred until the
  invocation-log census says agents trip on it. Source: exit-status slice
  2026-09-04 (X9).

None of the above changes a shipped behaviour; each is either untested
surface, a naming/factoring nit, or an operational note. They are listed here
so rung 3 does not have to re-discover them from `deferred-minors.md`, which
is gitignored and local to the rung-2 branch's own ledger.
