# CARRIED-DEBT

Appended at every merge: *what this slice settled* → *deferred, with
rulings* → *process lessons*. Resolved items are struck through, never
deleted.

Started 2026-09-05, at rung 3's close. Earlier slices carried their debt in
the rung-3 inbox
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3) and in the
gitignored plan ledgers; nothing there is restated here, and that document
stays the record for rungs 0–2.

**The earlier sections moved 2026-09-06** — rung 3, the borrow repair and the
rung-4 entry slice are
[`docs/CARRIED-DEBT-ARCHIVE.md`](CARRIED-DEBT-ARCHIVE.md), wording, order and
strikes unchanged, so a deferred item there is still open unless it is struck.
The split was named in this file before it was taken (the focus tier's own
"files near the ceiling" bullet, below) rather than discovered at 800; the rule
above governs both files, and the next slice appends here.

## 2026-09-06 — rung 4 slice 1, the focus tier (Python 0.8.3 / crates 0.4.0)

### Settled

- **LINE and locals for Rust, under a compile-time `--focus`.** One probe
  after every statement of a focused function at every block depth, its
  `deltas` the bindings that statement wrote; a new wire kind LINE (6), the
  converter's row in the Python payload shape, `meta.focus` /
  `meta.focus_matched`, and `capabilities.line` / `locals` true exactly where
  a registered unit carries a LINE site. `watch` and `flow` answer on such a
  trace instead of refusing. `rust/HONESTY.md` §12 is the promise;
  `rust/HONESTY-BLIND-SPOTS.md` item 3 is what is left, narrowed rather than
  struck.
- **E9, measured once: six PASS and one REPORTED, all seven rows as
  pre-registered** (`docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md`).
  H3 read **N = 26** with a zero per-line diff, against a hand count locked
  before the transform could produce a competing number; H6 is **REPORTED**
  without a gate and without a usable cost signal. No kill fired, nothing was
  dropped, and no endpoint fell back to an expectation.
- **The reading of a non-block arm body is decided and now pinned.** E9 §5.1
  settled line 259 in favour of reading A — the arm-entry LINE is minted
  whether or not the body is a block, and the bare expression becomes the
  wrapping block's tail — and §5.5 item 2 recorded that nothing would catch a
  regression of it. `corpus/rust/focus_arm_bare` is that pin, added
  post-measurement and test-only.
- **Rulings R-F4 – R-F13**, each in the ledger with its text: R-F4 the arm
  wrap; R-F5 verdict words are the tool's own, never "MATCH"; R-F6 amendments
  as one dated commit; R-F7 the lazy line probe and a 2048-byte payload;
  R-F8 no runtime frame gate, a loud converter refusal instead; R-F9 task
  order; R-F10 → R-F11 focus scoping (`meta.focus` is the invocation's);
  R-F12 the refusal gate in CI's rust job; R-F13 the §1.4 lens amended
  pre-measurement, both locks carried.
- **The instrument's killed-cell rule is structural.** A phase that was
  killed publishes `null` with its reason for every cell derived from a
  partial answer, derived from what the block publishes rather than from a
  hand-kept list — the first list missed a cell, which is why the rule is
  structural and not a list.
- **Two documents were split before either passed 800 lines**, both
  deliberately: `rust/HONESTY.md` §11 is `rust/HONESTY-ERR-FLOW.md`, and the
  README's `exceptions`/`watch`/`flow` detail is `docs/query.md` (the split
  the entry slice named, struck above). Wording and order unchanged in both.

### Deferred, awaiting rulings

- **`--window` for Rust is slice 2's**, with `refocus` and E4. It needs a
  per-activation runtime check the Rust runtime does not have: the Python
  recorder gates LINE recording by ancestry at frame entry, and the Rust
  probe has no equivalent state to consult. **Ruling owed** on whether the
  window is a runtime check or a second compile-time selector.
- **Closure bodies and `async fn` bodies get no probes** (design §3.3). A
  closure's statements run when it is called and an `async` body's when it is
  polled; a probe's borrow inside an `async` block faces the same lifetime
  question that keeps `async fn` out of the entry guard. **Ruling owed** on
  whether closure bodies are reachable without the async half.
- **Place writes (`*p = e`, `a.b = e`, `v[i] = e`) and `&mut` mutation are
  not deltas.** Those statements mint a row with empty `deltas`, which says
  the line ran and nothing about what it changed — the largest honest gap in
  what a focused row carries.
- **CALL rows still carry no arguments on a Rust trace.** Under a focus the
  parameters LINE is where an argument exists, which is why every corpus case
  identifies an activation by position or by what it returned. Rung 2's
  reason has not changed; the focus tier makes the workaround visible.
- **`flow --object` on a Rust trace stays REFUSED** through
  `object_identity: false`, and `constructions()`'s receiver logic is
  untouched.
- **No per-site volume cap.** A focused loop of 10⁶ iterations writes 10⁶
  LINE records per statement; the focus is the budget. E9's H6 was to inform
  this and could not: libtest read 0.00 s on all four binaries and every wall
  was compilation-dominated, so **there is no measured cost to size a cap
  against**. F2's 160 rows over 20 activations of 8 is the only density
  number the run produced. **Ruling owed**, and it needs a measurement first.
- **The cost residual needs a different instrument, not a bigger subject
  alone** (record §5.5 item 3): a subject whose test binary takes long enough
  to time AND an instrument that separates compile from run — a warm target,
  or timing the built test binary directly rather than the `cargo sensorium`
  invocation around it.
- **The shim is a COPY, once per distinct focus.** The focus hash rides in
  the wrapper shim's PATH, because cargo consults no `SENSORIUM_*` variable
  (amendment A8), so each focus costs ~40 MB of shim plus its own artifact
  set and its own manifests, all accumulating in the target directory across
  invocations. A hard link would delete the copy but needs a cross-filesystem
  fallback and a rule for when the source binary is replaced. **Ruling owed.**
- **`sha256.rs` now exists in THREE crates** — runtime, transform and driver
  — kept in sync by the same NIST vectors. D1 forces the first two; the
  transform's copy is this slice's, for `focus_hash`. Three copies of ~300
  lines is past the point where "a duplication D1 forces" describes it.
- **`info` renders an ABSENT `focus` as `focus: -`.** The converter honours
  none-vs-zero and writes no `focus` key at all on an unfocused run
  (`rust/cargo-sensorium/tests/convert_meta.rs`), and the reader then
  collapses absent and empty into one dash. Design §6's
  `focus_unfocused_refuses` line — "`info` shows no `focus` key" — is
  therefore pinned as `focus: -` rather than literally. Fixing the reader
  would let the literal pin be taken.
- **`rust/cargo-sensorium/tests/convert.rs` is 833 lines**, over the ceiling
  and **pre-existing since `089768d`** — this slice did not touch it. Named
  here so the next legitimate touch splits it rather than discovering it.
- **Files near the ceiling**, none of them over it:
  `rust/tests/acceptance_e9_phases.py` 788, `rust/sensorium-transform/tests/edges.rs`
  784, `rust/sensorium-transform/src/splice.rs` 775,
  `rust/sensorium-transform/src/visit.rs` 767,
  `rust/sensorium-transform/src/lines.rs` 749 and
  `rust/cargo-sensorium/src/driver.rs` 763 — and **this file, at 799 of 800
  after fix round 1: the next bullet added here MUST split it first**. For
  the others the next paragraph splits them first too; for this one the natural
  split is by slice, the oldest sections moving to a
  `docs/CARRIED-DEBT-ARCHIVE.md` it links, and it is named here rather than
  discovered at the ceiling.
- **A stale `rust/target/release/cargo-sensorium` sits on the ROOT disk**, a
  2026-09-04 build. Anyone who runs the corpus gate with that binary on
  `PATH` instead of the `/mnt`-side one gets failures that are about the
  binary and not the tree. Delete it or document it; it is not `.gitignore`'d
  away, it is simply old.
- **A box-local path sits in a committed test, and no check reaches it.**
  `rust/sensorium-transform/tests/census.rs:6`'s doc comment names
  `/home/brice/workspace/bloomery`. It is **pre-existing on `main` at
  `9db30d0`**, and this slice touched that file at two other lines only (an
  import, and a `transform(..)` call gaining `&Focus::EMPTY`). The coverage
  half is the real debt: the box-path scan
  (`tests/test_acceptance_e9.py::…_names_no_box_path` and its siblings) walks
  only `rust/tests/<INSTRUMENT>`, so **no test reaches
  `rust/sensorium-transform/tests/` or any other crate's tests at all**.
  Widening the scan would have caught this one, and would catch the next.
- **The composite-loop residual.** A `loop` a `break` leaves, nested inside a
  composite statement (`unsafe { loop { break; } }`, a `match` whose every arm
  is such a loop), is called diverging by the shared exit walk and loses its
  LINE. It costs a row and never a build; closing it means duplicating that
  walk's composite recursion in the line pass.
- **The uppercase-initial heuristic.** A pattern name whose first character is
  uppercase is read as a path pattern and mints no delta, because `syn` cannot
  tell `None` from a binding and resolution is rustc's job. The cost is a
  missed delta for a binding written against Rust's own naming convention;
  the alternative is a workspace that does not compile under a focus.
- **`Expr::RawAddr` and any future `syn` variant in `expr_attrs`.** The
  attribute walk enumerates `syn::Expr` variants by hand
  (`rust/sensorium-transform/src/lines.rs:617`), so a variant `syn` adds later
  silently falls through to "no attributes" and its `#[cfg]` decline is lost.
  Nothing fails loudly when that happens.
- **The refusal gate is unverified on a real CI runner.** `.github/workflows/ci.yml`
  gained the exit-2 focus refusal check in the rust job (R-F12), and no
  runner has executed it until this PR does.
- **`results.json` re-derivation is still an OPEN ruling** — the entry
  slice's item above stands. E9 states its own practice rather than a policy:
  the file committed with the record IS a re-assembly, checked against the
  run's own, and the two differ at exactly one leaf path, `assembled.at`
  (record §4, corrected in §5.7 after the first wording named the wrong
  side). That is one record's practice, not the schema-version rule the
  entry slice asked for.
- **`reported.line_rows_per_run` published four nulls** (record §5.5 item 1):
  it reads `meta.counts`, a key the Rust trace's `meta` does not carry. The
  number is in the record — the census's `line_events`, 0 / 26 / 0 / 160 —
  so this is a duplicate field shaped for the Python recorder, and it is
  reported rather than a measurement cell, which is why the "no null without
  a reason" rule does not reach it.
- **The suite's skip count still depends on one variable** (record §5.5 item
  4): 1426 passed / 12 skipped without `SENSORIUM_CARGO_SENSORIUM`,
  1437 / 1 with it. The entry slice carried the same residual at 1293/9
  against 1301/1; the delta is now 11 tests rather than 8.
- **`src/sensorium/query/exceptions_rust.py` names `rust/HONESTY.md` at three
  sites, and after this slice's split one of them is PRINTED.** `:431` (a
  comment above `ESCAPED_DETAIL`) and `:448` (a docstring) cite
  `rust/HONESTY.md` §11 for the SWALLOWED definition; the section still names
  what it always named, so those two are stale PATHS, correctable in the
  post-review fix wave. **`:462` is different**: it sits inside a
  `Disposition` detail the tool PRINTS — *"it left the grammar this recorder
  watches (rust/HONESTY.md names the shapes that are not probed); no sink
  recorded is not evidence that nothing absorbed it"* — and after the split
  that file no longer names those shapes. Changing a printed line after E9
  was measured is CARRIED-DEBT and not a fix, under the classification rule.
  The correction, spelled out so the next slice need not re-derive it: the
  unprobed shapes are named by `rust/HONESTY-ERR-FLOW.md` (§11's "everything
  else is unprobed **on purpose**" paragraph) and `rust/HONESTY-BLIND-SPOTS.md`
  items 15–26.

### Process lessons

- **Two facts about this pipeline were discoverable only by RUNNING it.**
  Cargo consults no `SENSORIUM_*` variable, so the mirror stamp alone left
  the flag inert — a second invocation under a new focus printed
  `Finished in 0.00s` and re-ran the first build's binary; and per-focus
  manifests ACCUMULATE, so a union over "all in-scope manifests" let an
  earlier focused build label an unfocused run. Both were found by an
  end-to-end run by hand, neither by a test. Every driver task carries one.
- **A design needed eleven dated amendments during implementation, and none
  of them was silent.** A1–A11 are appended, never edited into the sections
  above, and the sections read with the amendments applied. Eleven is a fact
  about how much a design of this size cannot settle on paper, worth knowing
  before the next one is written.
- **Mutation-test only a COMMITTED tree.** An uncommitted fix was wiped by a
  `git checkout --` inside a mutation round. The tree under test has to be
  the tree in the index.
- **Reviewers producing REAL output shapes caught parser assumptions no
  fixture would.** A reviewer who recorded an actual corpus case, rather than
  reasoning about the expected shape, found what a hand-written fixture had
  agreed with.
- **The instrument's killed-cell rule must be structural**, derived from what
  a block publishes, never a hand-kept list: the first list missed a cell,
  which would have let a partial answer be published as a measured one.
- **File ceilings are checked at every fix round**, not only at task end —
  and at close-out, two documents needed splitting BEFORE the paragraph that
  would have pushed them over, which is the cheap moment to do it.
- **A reader fix after the lock is a dated lens amendment with both shas**
  (R-F13, and R-G13 before it). E9's `--limit 1000` was amended in its own
  commit `ffaed19` after the original lock `a4264b5`, before any number was
  read, and the record carries both.
