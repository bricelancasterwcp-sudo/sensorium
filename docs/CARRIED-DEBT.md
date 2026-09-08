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

**Four items below come from the whole-branch review, which read them AFTER
E9 was measured.** Ruling R-F14 keeps them out of `src/`: the records describe
what that code recorded, so each is written here with its fix spelled out —
for Brice now, or for slice 2 — rather than repaired under the measurement.
Each is marked *ruling: Brice / slice 2*.

- ~~**A brace-delimited macro in TAIL position breaks the focused build.**
  `fn f() -> i32 { m! { 1 } }` — the shape of every `quote!`- or `html!`-
  terminated function, so of proc-macro and markup crates. `syn` reads the
  tail as a `Stmt::Macro` with `semi_token: None`; `lines.rs`'s
  `statement_end` gives a brace-delimited macro the byte after its closing
  brace without asking `is_tail`, so a LINE is minted after the return value.
  With the RETURN wrap around the same tail the output is
  `…, m! { 1 })::sensorium_rt::line(…)`, a PARSE error, so the unit falls
  back whole and loudly (`fallback::announce`) rather than losing a row.
  **The fix is one line**: `lines.rs`'s `Stmt::Macro` arm returns `None` when
  `is_tail`, exactly as `Stmt::Expr(expr, None)` above it already does.
  Measured by `rust/sensorium-transform/tests/focus_compile_fail/focus_macro_tail.rs`,
  which will fail loudly on the day the guard lands — that is the signal to
  delete the case and the blind-spot bullet together. Not in E9's subject.
  *Ruling: Brice / slice 2 — a `src` change after the measurement (R-F14).*~~
  — **TAKEN 2026-09-07 in slice 2 (ruling G1, design §3.3) at `2747c1c`**, as
  the one line the bullet named: `sensorium-transform` **0.4.1**. The signal
  fired exactly as written — the compile-fail case is deleted and the shape is
  now the compile-PASS golden `tests/golden_focus/focus_macro_tail.{in,out}.rs`,
  whose output the real-rustc oracle compiles under `-D warnings` with an empty
  stderr required. The golden carries the UNIT-fn half too (`fn u() { m! { a } }`,
  one fewer LINE), which never failed to build and so was never measured before:
  it recorded a completed statement for what is the function's value.
  `rust/HONESTY-BLIND-SPOTS.md` item 3's bullet is struck and corrected in
  place.
- **The autoref ladder COMMITS an open inference variable to `Debug`.** A
  `let` whose head type is still an inference variable at the probe —
  `let mut v = Vec::new();` then `v.push(Opaque)`, `let mut x = None;` then
  `x = Some(Opaque)`, `let x = Default::default();`, a `.collect()` typed
  later — resolves the ladder to its `Debug` rung there, so a later
  resolution to a type without `Debug` is `E0277` and the unit does not build.
  A generic `T` with no `Debug` bound is NOT this shape (the bound is
  unprovable rather than open, the ladder takes its fallback rung and records
  `unread`), and `Vec<u8>` compiles; both measured. **Two candidate designs,
  and the choice is the ruling.** (a) An OPT-OUT spelling — a per-`let` or
  per-function marker that declines the delta — which keeps every capture that
  works today and costs the author a word at the shapes that do not; the sub-
  question is where it is spelled, since the transform sees only `syn` and an
  attribute is the only thing it can read. (b) Decline the delta on any
  initializer with NO TYPE WITNESS — no ascription, no turbofish, no literal,
  no constructor path — which needs no author action and silently loses
  deltas on `let x = f();`, the commonest `let` there is, so its cost has to
  be measured before it is chosen and not after. Measured by
  `.../focus_compile_fail/focus_infer_debug.rs` against `focus_moved_value`.
  *Ruling: Brice / slice 2 — a `src` change after the measurement (R-F14).*
- **`focus_matched` can carry a STALE unit's match.** The union is over every
  in-scope manifest whose canonical focus equals the invocation's (A9/A10),
  and per-focus manifests accumulate (A8), so a qualname can appear that this
  invocation did not build: the same workspace and focus, a later run with a
  different `-p`, or a function since deleted from a unit cargo saw no reason
  to rebuild. Bounded, and it is a claim about the BUILD only —
  `capabilities.line` / `locals` and `meta.sites` are the run's registered
  units and are unaffected, so no LINE row is ever attributed to a function
  that did not produce it. **The candidate filter**: keep a manifest's matches
  only where its recorded source hashes are still present in the tree, or
  where its mtime is at or after the invocation's start. The mtime half is
  cheap and coarse (a rebuild-free re-run of the SAME focus would drop its own
  matches, so the two conditions are an OR, not an AND); the hash half is
  exact and costs a read per manifest. `rust/HONESTY.md` §12 states the bound
  in the meantime. *Ruling: Brice / slice 2 — a `src` change after the
  measurement (R-F14).*
- ~~**`fn_items` runs the whole splicing transform just to enumerate.**
  `focus.rs:150` calls `crate::transform(source, file, "", 0, false,
  &Focus::EMPTY)` and reads `sites` and `skipped` off the result, throwing the
  assembled output string away — and the driver calls it for every file of
  every cargo-metadata target before a focused build, to resolve `--focus` and
  to print the `Closest:` suggestions. **The fix**: take the route
  `splice::census` already takes — `Ctx::new(..)` then `visit_file(..)`, which
  classifies every fn and splices nothing — and read the sites off the `Ctx`
  instead of off a `Transformed`. It is the same walk without the string
  assembly, and `census()` is the proof that the walk alone is enough. Nothing
  is wrong with the current answers; this is cost, and it is unmeasured cost
  (E9 H6 could not separate compile from run, so there is no number for it
  here either). *Ruling: Brice / slice 2 — a `src` change after the
  measurement (R-F14).*~~ — **Taken 2026-09-07** at `22fbe02`, slice 3's ruling
  R7, by the route this bullet named.

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
- ~~**The shim is a COPY, once per distinct focus.** The focus hash rides in
  the wrapper shim's PATH, because cargo consults no `SENSORIUM_*` variable
  (amendment A8), so each focus costs ~40 MB of shim plus its own artifact
  set and its own manifests, all accumulating in the target directory across
  invocations. A hard link would delete the copy but needs a cross-filesystem
  fallback and a rule for when the source binary is replaced. **Ruling owed.**~~
  — **Taken 2026-09-07** at `36d2fe9`, slice 3's ruling R3: the hard link with
  a copy fallback, and the replaced-binary rule was already the key's own hash.
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
  `rust/cargo-sensorium/src/driver.rs` 763 — and ~~**this file, at 799 of 800
  after fix round 1: the next bullet added here MUST split it first**~~. For
  the others the next paragraph splits them first too; for this one the natural
  split is by slice, the oldest sections moving to a
  `docs/CARRIED-DEBT-ARCHIVE.md` it links, and it is named here rather than
  discovered at the ceiling. — **Taken 2026-09-06**, first commit of the
  post-review fix wave and alone: rung 3, the borrow repair and the rung-4
  entry slice are `docs/CARRIED-DEBT-ARCHIVE.md`, a pure move under the name
  this bullet gave it. The others stand.
- **A stale `rust/target/release/cargo-sensorium` sits on the ROOT disk**, a
  2026-09-04 build. Anyone who runs the corpus gate with that binary on
  `PATH` instead of the `/mnt`-side one gets failures that are about the
  binary and not the tree. Delete it or document it; it is not `.gitignore`'d
  away, it is simply old.
- ~~**A box-local path sits in a committed test, and no check reaches it.**
  `rust/sensorium-transform/tests/census.rs:6`'s doc comment names
  `/home/brice/workspace/bloomery`. It is **pre-existing on `main` at
  `9db30d0`**, and this slice touched that file at two other lines only (an
  import, and a `transform(..)` call gaining `&Focus::EMPTY`). The coverage
  half is the real debt: the box-path scan
  (`tests/test_acceptance_e9.py::…_names_no_box_path` and its siblings) walks
  only `rust/tests/<INSTRUMENT>`, so **no test reaches
  `rust/sensorium-transform/tests/` or any other crate's tests at all**.
  Widening the scan would have caught this one, and would catch the next.~~ —
  **taken 2026-09-06 in the post-review fix wave**, both halves. The scan now
  walks `rust/*/tests/**/*.{rs,py}` (`golden*/` fixtures excluded, being
  byte-compared transformer output), with a second test asserting the walk
  contains `census.rs` and is larger than the instrument so an empty walk
  cannot pass for a clean tree; measured discriminating (red on the one hit,
  green after). The docstring now says "the bloomery checkout the plan names".
  Both are test-file changes, so R-F14 does not reach them. The widened scan
  found **one** hit in 40 files — this one — and `src/` is clean.
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
- ~~**`results.json` re-derivation is still an OPEN ruling** — the entry
  slice's item above stands. E9 states its own practice rather than a policy:
  the file committed with the record IS a re-assembly, checked against the
  run's own, and the two differ at exactly one leaf path, `assembled.at`
  (record §4, corrected in §5.7 after the first wording named the wrong
  side). That is one record's practice, not the schema-version rule the
  entry slice asked for.~~ — **Taken 2026-09-07** at `e0f469c` under **ruling
  R4**: every raw and assembled results file carries `schema_version`
  (`"e9/1"`, `"e4/1"`, `"e4p/1"`), and the renderer states once when the
  assembled schema is later than the raw's. The E9 and E4 `results.json`
  committed with their records are NOT re-derived — a derivation is stated, not
  rewritten (R-F15/R-G15 precedent) — so **those two files predate the field**,
  which is the fact a later reader needs.
- **`reported.line_rows_per_run` published four nulls** (record §5.5 item 1):
  it reads `meta.counts`, a key the Rust trace's `meta` does not carry. The
  number is in the record — the census's `line_events`, 0 / 26 / 0 / 160 —
  so this is a duplicate field shaped for the Python recorder, and it is
  reported rather than a measurement cell, which is why the "no null without
  a reason" rule does not reach it.
- **The suite's skip count still depends on one variable** (record §5.5 item
  4): 1428 passed / 12 skipped without `SENSORIUM_CARGO_SENSORIUM` (1426 at the record's reading; the fix wave added two scan tests),
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
- **A design needed twelve dated amendments during implementation and review,
  and none of them was silent.** A1–A12 are appended, never edited into the
  sections above, and the sections read with the amendments applied. (Eleven
  during implementation; A12 came from the whole-branch review, after E9.)
  Twelve is a fact about how much a design of this size cannot settle on
  paper, worth knowing before the next one is written.
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

## 2026-09-07 — rung 4 slice 2, refocus and E4 (Python 0.8.4 / driver 0.5.0 / transform 0.4.1)

### Settled

- **The brace-delimited-macro-tail guard** — slice 1's first deferred item,
  struck above as taken at `2747c1c` under ruling G1. `sensorium-transform`
  **0.4.1**; the compile-FAIL case is gone and the shape is a compile-PASS
  golden through the real-rustc oracle, carrying the unit-fn half nobody had
  measured. It was the one slice-1 debt that was a broken build rather than a
  cost or a bound.
- **`refocus` on a Rust trace.** The driver takes `--refocus-of <run id>` and
  every run records `refocus_of`, `workspace_root` and `invocation_processes`;
  `capabilities.refocus` is **true** for every trace this driver converts, and
  whether one particular trace can be refocused is a refusal with a sentence.
  Python's Rust branch re-runs the RECORDED command from the recorded
  workspace into the same store, five pre-rerun refusals first, finds the pair
  in the STORE by `refocus_of` (ruling G3), and issues the unchanged
  comparator's verdict. `rust/HONESTY.md` §13 is the promise; what a re-run
  still does not compare is `rust/HONESTY-BLIND-SPOTS.md` item 12, narrowed
  rather than struck.
- **E4, measured once: five PASS and two REPORTED, all seven rows as
  pre-registered** (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md`,
  §1 byte-locked at `8e7d837` and amended once before the instrument existed
  at `413f601`, both shas carried). **61 of 61 MATCH**, 0 DIVERGED, 0 REFUSED,
  0 pre-rerun refusals, 0 focused build failures. No kill fired, nothing was
  dropped, the loop closed in 8 min 22 s of a 2-hour bound, and no endpoint
  fell back to an expectation. §1's own expectation that "the first focus pays
  for the rt build" was **falsified** and reported as such (first 6.661 s
  against a later mean of 6.988 s).
- **`RUST.no_rerun_note`'s "arrives with rung 4" is retired.** Nothing in the
  tree says it any more (grepped and pinned); the note now names the command a
  reader may run instead of the re-run that was refused, and it names
  `cargo sensorium`, never `sensorium run`, which cannot record this workspace.
- **Rulings G1–G3, B1, B2 and R-H1**, each in the ledger with its text: G1 the
  guard; G2 refocus lives in Python's re-run path (`refocus_rust.py`), not in
  the driver; G3 `--refocus-of` plus a store lookup on `refocus_of`, never a
  parse of the driver's `run:` line; B1 two §4 sentences of the design
  corrected before the lock (the `fresh_dir` forms; the scheduler hazard); B2
  the not-a-run-id refusal ratified and `invocation_processes` defined as the
  RUNNER's processes, doctests included; R-H1 the E4 lens amended
  pre-instrument (the survey's scope, the worker-thread discriminator, the
  citation lines).

### Deferred, awaiting rulings

- ~~**The licence's untraced-thread clause fires on every `cargo test` pair, so
  the licence is structurally never granted there.** E4 measured
  `licences granted` **0** on all 61 pairs while every count H4 gates on was
  exactly as pre-registered: libtest runs each test on a thread it spawns, and
  a thread that ran no traced code has no fingerprint to compare (measured
  counts 57×1, 1×2, 3×5 — record §5.2). **The candidate fix, named in the
  record and deliberately not applied:** treat libtest's per-test thread as
  the RECORDER's own rather than the program's, so it raises no caveat — the
  precedent being the recorder's own environment variables, which the same
  licence already names and excludes. It is a design question about what "the
  program's threads" means on a test harness, and it is not a `src` change to
  make after the measurement. **Ruling owed** (Brice / slice 3). Until it is
  made, a reader of a `cargo test` refocus should read the four printed
  counts, not the word — which `docs/query.md` now says.~~ — **Taken
  2026-09-07** at `11b7e8a` (with `d9115a5`) under **ruling R1**, and it is the
  named candidate fix: a non-main thread whose ROOT frame's site the manifest
  marks `#[test]` is the harness thread, excluded from the licence's
  untraced-thread counts and NAMED wherever one of them is printed. Measured
  by **E4′**, whose expected partition was byte-locked before the instrument
  existed: the exclusion held on **61 of 61** pairs in one spelling and the
  four named pairs reported the program's own counts 1, 4, 4, 4 — but **H1
  STOPPED**, because the ENV clause withheld all 61 first on `RUSTDOCFLAGS`
  (its own deferred item below), so the WORD's dependence on R1 is measured by
  nothing yet.
  `rust/HONESTY.md` §13 and `docs/query.md` carry the rule;
  `rust/HONESTY-BLIND-SPOTS.md` item 12's bullet is struck and corrected.
- **`--window` for Rust is still not shipped**, and is now refused by name at
  exit 2 rather than silently absent. It needs a per-activation runtime check
  the Rust runtime does not have. **Ruling owed** on whether the window is a
  runtime check or a second compile-time selector — slice 1 carried this and
  slice 2 did not take it. — **Ruled 2026-09-07
  (R6): NOT FUNDED until a use asks**, and the declared blind spots stand. The
  item is not struck: nothing shipped, and the refusal or the bound is still
  what a reader meets.
- **A refocus of a multi-process invocation is refused, not compared.** One
  `cargo sensorium test --workspace` is many runner processes and no single
  trace answers a question about the invocation, so `refocus` refuses at exit
  2 naming the count and the single-target selector. What a reader actually
  wants there — a verdict over the whole invocation, the way
  `sensorium exceptions <invocation-id>` already answers — is unbuilt and
  unspecified. **Ruling owed** on whether the unit of a refocus can be an
  invocation. — **Ruled 2026-09-07
  (R6): NOT FUNDED until a use asks**, and the declared blind spots stand. The
  item is not struck: nothing shipped, and the refusal or the bound is still
  what a reader meets.
- ~~**A single-target re-run whose test spawns a workspace CHILD is refused by
  count, and the sentence names the wrong cause.** The driver stamps
  `refocus_of` into every trace the invocation writes, and a child process the
  test itself spawns is instrumented and gets one — while
  `meta.invocation_processes` counts only the processes cargo hands the RUNNER
  (test binaries and doctests), so the original's count is 1 and no pre-rerun
  refusal fires. `find_pair` then finds TWO linked traces, and
  `refocus_rust.py` refuses at exit 3 with the single-target sentence
  (`refocus needs an invocation with a single-target selector (--lib, --test
  X, --bin X) so one trace is the answer`) at a caller whose selector was
  already single-target. **The verdict is right — two traces is not a pair —
  and the diagnosis is wrong**, which is the part that costs a reader time.
  Unmeasured: E4's subject spawns no child from a test (every pass-1
  invocation produced exactly one process), so this is derived from the code
  and the trace format, not observed. **Two candidate fixes, neither applied:**
  (1) exclude a linked trace whose `ppid` is another linked trace's `pid` — the
  converter already records `ppid` and already derives `child_runs` from it
  (`docs/TRACE-FORMAT.md`), so the parent of a pair is identifiable without a
  new key, and the refocus compares the parent; (2) keep the refusal but name
  the child runs in the sentence, so the reader is told a child was recorded
  rather than told to narrow a selector. (1) changes what a refocus ANSWERS
  and (2) only what it says, which is the choice to make. It is a `src` change
  after the measurement either way. **Ruling owed** (Brice / slice 3).~~ —
  **Taken 2026-09-07** at `d4cccd9` under **ruling R2**, which chose candidate
  (1): a linked trace whose `ppid` is another linked trace's `pid` is a child
  run, excluded from the pair, and candidate (2) rides along — the excluded ids
  are named on the pair line AND in the >1-candidate refusal, in one sentence
  used in both places. `corpus/rust/refocus_child_run` records the shape
  through the real driver, so the class is no longer derived-only.
- **The autoref ladder still COMMITS an open inference variable to `Debug`**,
  and the opt-out spelling is still unchosen. Slice 1's item stands verbatim
  above with its two candidate designs; slice 2 took the guard beside it and
  not this. The compile-fail golden `focus_infer_debug.rs` still measures it.
  **Ruling owed** (Brice). — **Ruled 2026-09-07
  (R6): NOT FUNDED until a use asks**, and the declared blind spots stand. The
  item is not struck: nothing shipped, and the refusal or the bound is still
  what a reader meets.
- ~~**The shim is a COPY, once per distinct focus — and the cost is now
  MEASURED.** Slice 1 estimated ~40 MB per focus; E4 counted **62** entries
  under `<CARGO_TARGET_DIR>/sensorium/shim` totalling **2 506 729 440** bytes
  (~40.4 MB each) after one unfocused pass and 61 focused re-runs, none
  reused, inside a fresh target that reached **25.8 GB** (record §3, §5.4). A
  hard link would delete the copy but needs a cross-filesystem fallback and a
  rule for when the source binary is replaced. **Ruling owed**, and it now has
  a number to be sized against.~~ — **Taken 2026-09-07** at `36d2fe9` (with
  `2b8b5fb` and `4edd5c7`) under **ruling R3**, `cargo-sensorium` **0.5.1**:
  `install_shim` hard-links the driver and falls back to a copy on any error,
  the cross-filesystem case included, naming both failures when both fail. The
  replaced-driver rule was already there — the key hashes the driver's own
  bytes — and two guards were added in review: the leftover temporary is
  unlinked FIRST (it may itself be a link to the driver, and `fs::copy` onto it
  truncates what it opens), and `set_permissions` runs on the copy path alone,
  so R3's conceded cost of writing the driver's inode is not paid at all.
- ~~**`fn_items` still runs the whole splicing transform just to enumerate.**
  Slice 1's item stands verbatim above, fix included (take `splice::census`'s
  route). Unmeasured cost then and unmeasured now: E4's H6 separates the
  refocus wall from cargo's build but not the resolution from the build.
  **Ruling owed** (Brice).~~ — **Taken 2026-09-07** at `22fbe02` (with
  `ba3edb5`) under **ruling R7**, `sensorium-transform` **0.4.2**, by the named
  route: `census::walk` runs `Ctx::new(.., Mode::Census, ..)` then `visit_file`
  and reads the rows off the `Ctx`. The cost is still unmeasured — nothing in
  this slice separates resolution from build either — so what was taken is the
  fix, not a number. One answer moved and is declared below.
- **`focus_matched` can still carry a STALE unit's match.** Slice 1's item
  stands verbatim above with its candidate filter. `rust/HONESTY.md` §12
  states the bound in the meantime, and nothing in slice 2 touched it.
  **Ruling owed** (Brice).
- ~~**`info` does not print `refocus_licence_unverifiable`.** The stamp is
  written into the new trace's meta and `info` prints `licence: granted` or
  `WITHHELD` without saying which checks could not run at all — so the two
  UNVERIFIABLE checks survive in the trace and not in the line a later reader
  meets. Raised at Task 3's review as Minor 4 and eligible for a small `src`
  change only BEFORE the measurement; Task 6 has measured, so it is carried
  here instead. **The fix, spelled out so the next slice need not re-derive
  it:** `info`'s refocus line reads the `refocus_licence*` stamps already;
  append the unverifiable check names where the stamp holds them.~~ — **Taken
  2026-09-07** at `11b7e8a` under **ruling R7**, by exactly that fix:
  `licence unverifiable: output (not recorded), children (not witnessed)`, and
  no line at all where the stamp is absent.
- ~~**`rust/cargo-sensorium/src/driver.rs` is at 791 of 800**, up from 763 by
  this slice's `--refocus-of` parsing and its two refusals. The next change to
  that file splits it first — the natural seam is the argv parsing, which
  `driver_args.rs` and `refocus_of.rs` already carry most of.~~ — **Taken
  2026-09-07** at `03a68d3` and `095be7e` under **ruling R7**, along a
  different seam than the one guessed here: the invocation record to
  `invocation.rs` (377) and the cargo child's environment and launch to
  `launch.rs` (202), leaving `driver.rs` at **328**. Pure moves, pinned by the
  smoke tests.
- **`last` is mtime-ordered.** A refocus writes a trace whose id nothing could
  have spelled in advance, so `last` is how a corpus case and a reader address
  it — and `last` is the store's newest by FILE MTIME, not by any recorded
  clock. It is unambiguous inside a corpus case, whose store holds exactly two
  traces; it is not in a shared store, and a case that refocused twice would
  need `runs` to name which trace it means. Stated in `docs/query.md` and
  `corpus/rust/README.md`; the reader-side fix (order by the recorded start,
  or let `refocus` print an addressable id) is not taken.
- **The digest floor is a number, and it is 16 hex characters.**
  `refocus_world._MIN_DIGEST = 16` is the narrowest width either recorder
  writes (`boot.hash_file` keeps 16 of the sha256; `cargo-sensorium` writes
  all 64), so no real trace is refused by it — and without it an empty digest
  would prefix-match every file and read `source: unchanged` over code nobody
  hashed. It is a floor chosen against today's two recorders, and a third that
  wrote narrower digests would meet a refusal rather than a rule.
- **One driver resolution, THREE copies of it.** `refocus_rust.driver`,
  `corpus/run_corpus.cargo_driver` and `tests/test_focus_refusal._driver`
  each resolve `SENSORIUM_CARGO_SENSORIUM` then `PATH`. They are separate on
  purpose — `corpus/` is not in the wheel, so the query command cannot import
  it — which makes drift between them silent, so
  `tests/test_refocus_rust.py::test_all_three_driver_resolutions_agree` pins
  all three against four inputs. **Pinned equal, not unified**; unifying them
  needs the shared helper to live under `src/sensorium/`.
- **The pre-registered discriminator's second condition has no subject on
  `cargo test` material.** §1.4's rule for telling the named worker-thread
  hazard from a recorder finding is two conditions — the worker tasks' total
  event count preserved, AND the MAIN stream MATCHing — and every one of E4's
  122 traces carries a **0-event** MAIN stream, because libtest runs each test
  on a spawned thread the converter records as a *task*. Condition (2) is
  therefore true by construction and would have discriminated nothing; a
  DIVERGED would have rested entirely on condition (1). The discriminator was
  never asked, so no verdict depends on it (record §5.3). A discriminator that
  works on `cargo test` material is a **pre-registration for a later record**,
  not a repair of this one.
- **The named hazard fired once and the comparator absorbed it, which is a
  reading to keep rather than a defect to fix.** On 1 of the 61 pairs the
  per-`task_id` assignment moved between the two runs — the workers carried
  (216, 205, 151, 233, 151) events on one side and (216, 205, 233, 151, 151)
  on the other, total 956 both sides — while the multiset of `(name, hash)`
  was identical, so the verdict was MATCH (record §5.3). B1's reasoning was
  exercised, not merely unfalsified. What is carried is that **a MATCH does
  not say the two runs scheduled the same way**, which no printed line
  currently states beside a Rust verdict.
- **Rung-5 candidates**, both wanting a measurement first: a per-site volume
  cap (slice 1's item, still with no cost to size against), and the cost
  instrument E4's H6 and E9's §5.5 both asked for — a subject whose test
  binary takes long enough to time, and an instrument that separates compile
  from run. The volume cap is one of R6's four: **Ruled 2026-09-07 (R6): NOT
  FUNDED until a use asks**, and the declared blind spots stand. The item is
  not struck: nothing shipped, and the refusal or the bound is still what a
  reader meets.

### Process lessons

- **A reviewer's proof-by-PROBE found an agreement no golden could.** Six
  macro-tail shapes were pushed through the real transform rather than
  reasoned about against a fixture, and what came back settled the guard's
  scope — the negative half included (a brace macro that is NOT a tail keeps
  its probe), which is what stops the arm being widened to every brace macro
  without the suite saying so. It is the same lesson slice 1 recorded about
  reviewers producing real output shapes, now on a second mechanism.
- **The corpus is the printing gate for a re-run, and a real re-invocation
  inside a question works.** The three `refocus_*` cases are the only cases
  whose QUESTIONS record: the harness records the case once and the question
  then launches the driver itself, through the environment `run_corpus._cli`
  passes down. That the pattern works at all was not obvious before it ran.
- **A pre-registered discriminator turns a post-hoc diagnosis into a check.**
  R-H1 amended E4's lens BEFORE the instrument existed, so the worker-thread
  hazard had a rule to be judged by rather than an explanation to be offered
  afterwards. The rule then proved to have no subject here (above) — which is
  itself a finding, and only available because the rule was written first.
- **One implementer at a time, even for a fix round.** Task 1's post-review
  fixes queued behind Task 2 by rule rather than sharing the worktree; the
  alternative is a second implementer's commit sweeping the first's staged
  files, which this project has already paid for once.
- **`pgrep` before every cargo when a reviewer may be holding it.** A build
  and a reviewer's `cargo test` share one target lock, and the second one
  blocks silently rather than failing.
- **A record's version token comes from installed distribution metadata, not
  from the tree.** Both E9 and E4 printed the reader as `sensorium 0.6.0`
  because that is what `importlib.metadata.version('sensorium')` reports in
  this `.venv`; `pyproject.toml` said 0.8.3 and 0.8.4 at those HEADs. Nothing
  in either record gates on the token, so no number moved — but a record that
  names its own reader wrongly twice will eventually name it wrongly where it
  matters. **`pip install -e .` before the next record**, and read the token
  back in the preflight rather than in the finished document.

## 2026-09-07 — rung 4 slice 3, the rung-4 debts (Python 0.8.5 / driver 0.5.1 / transform 0.4.2)

### Settled

- **The harness thread** — slice 2's first deferred item, struck above as taken
  at `11b7e8a` (with `d9115a5`, `2d38ff4`, `85d1860` and `b1a7771`) under
  **ruling R1**. A non-main thread whose ROOT frame's site the manifest marks
  `#[test]` is the recorder's own, subtracted from the licence's
  untraced-thread counts and NAMED wherever one of those counts is printed —
  joined to the count where the sentence counts what WAS compared, and set
  apart in a clause of its own on the line that counts what was not. Python
  traces carry no site marks, so their output is byte-identical by
  construction.
- **A child run is not the pair** — struck above as taken at `d4cccd9` (with
  the corpus case at `79cda14`) under **ruling R2**. The pair lookup excludes a
  linked trace whose `ppid` is another linked trace's `pid`, names the excluded
  ids on the pair line and in the >1-candidate refusal, and stamps them as
  `refocus_children`; `runs` still lists them.
- **A target directory that MOVED is not a world that changed** (Task 5b, at
  `1a76757` with `d43b7aa`). Not one of §0's seven: it was found in Task 5's
  dry run, ruled before any E4′ number was read, and recorded as the record's
  own amendment A1. Keys whose values differ ONLY by substituting the recorded
  `CARGO_TARGET_DIR` root for the current one — entry by entry down a
  `PATH`-like list, anchored at path boundaries on both sides — are named and
  treated as unchanged; nothing is excluded by name, and every other difference
  still withholds.
- **The shim is a hard link** — struck above as taken at `36d2fe9` (with
  `2b8b5fb` and `4edd5c7`) under **ruling R3**, `cargo-sensorium` **0.5.1**,
  with the unlink-first guard and `set_permissions` on the copy path alone, so
  the driver's own inode is never written.
- **`schema_version` in every results file** — struck above as taken at
  `e0f469c` under **ruling R4**, with the E9 and E4 files stated as predating
  the field rather than re-derived.
- **Housekeeping** — struck above as taken under **ruling R7**: `info`'s
  `licence unverifiable:` line at `11b7e8a`; `driver.rs` split to
  `invocation.rs` and `launch.rs` at `03a68d3` and `095be7e`; `fn_items`
  through the census path at `22fbe02` (with `ba3edb5`), `sensorium-transform`
  **0.4.2**.
- **A Rust screen says what its streams are in Rust's words** (`4ed802d`). The
  `threads:` line's scope parenthetical reads `(events outside any test or
  spawned thread)`; this converter writes one thread row and routes every other
  thread's events into `task_fingerprints`, so `asyncio` there named a runtime
  that never ran.
- **E4′, pre-registered §1-alone and byte-locked before the instrument
  existed** (`2991c3b`), amended once before any number was read (`d5efaab`,
  amendment A1 — the env clause and the launch environment) with the lock test
  following the amendment and carrying the original sha (`8954d3a`), and a
  preflight that refuses to launch unless this process's environment matches
  every original's recorded one under the licence's own exclusions
  (`10e2712`, `pins.env_parity`). The record carries its own numbers.

### Deferred, with rulings

- **The env clause's tiered set is RULED and NOT BUILT.** The relocation rule
  above closes the target-directory case; a re-run launched **from another
  shell** still meets an unearnable licence, because session-identity variables
  differ there and every differing key that is not the recorder's own or shell
  bookkeeping withholds. *The ruling, so the next slice need not re-derive it*
  (E4′ §1.5, *carried, not built*): a named, versioned **positive set** of
  build-and-run-bearing variables — `PATH`, `HOME`, `USER`, `LOGNAME`, `LANG`,
  `LC_*`, `TZ`, `TMPDIR`, `CARGO*`, `RUST*`, `LD_*`, `DYLD_*`, `SSL_CERT_*`,
  `PYTHON*`, `DEBUGINFOD_URLS` — withholds; every other differing key is
  counted and NAMED but does not withhold. Not built before this measurement
  because fewer source changes before a measurement is the rule and E4′ does
  not need it: its runner pins the two certificate variables and refuses on any
  other difference instead.
- **`src/sensorium/query/refocus_cmd.py` is at 789 of 800.** The next change to
  that file splits it first. The natural seam is the report: `_print_thread_line`,
  `_diverged_why`, the verdict block and the blind-spot print are one screen's
  worth of printing sitting beside the re-run's control flow.
- **`visit.rs` 773, `splice.rs` 762 and `lines.rs` 762**, all under
  `rust/sensorium-transform/src`, and `rust/HONESTY.md` at **792 of 800**
  after this slice's §13 and its fix round — the NEXT sentence added to that
  file splits it first, not the one after. The rule this file has kept twice applies: the next change to
  any of them splits it first rather than discovering the ceiling. For
  `visit.rs` the seam is the `Ctx` bookkeeping against the `Visit` impl; for
  `rust/HONESTY.md` it is the one the index already took — a section moves to a
  file it links.
- **`cargo test --workspace` writes traces into the developer's real store.**
  Several driver tests record through the real pipeline without setting
  `SENSORIUM_DIR`, so a workspace test run leaves runs in `~/.sensorium/traces`
  and a later `sensorium last` can name one of them. *The fix*: every test that
  records sets `SENSORIUM_DIR` to its own temporary directory, the way
  `convert*.rs` already do. It is a test-only change and it was not made after
  the measurement.
- **The corpus gate is the only gate that catches a changed CLI sentence, and a
  run without the driver reports the Rust cases as SKIPPED rather than
  failing.** That is correct for the Python CI matrix, which has no Rust
  toolchain — but it means a green local run proves nothing about a printed
  Rust line unless `SENSORIUM_CARGO_SENSORIUM` is set. Two fix rounds of this
  slice shipped with those cases skipped before the gate was run with the
  driver. *The fix, unbuilt*: make a skipped Rust case a non-zero exit under an
  explicit `--require-driver`, and use it wherever printed wording changed.
- **`tasks:` and "task stream" are the last asyncio nouns on a Rust screen.**
  `vocab.py` moved every language-bearing sentence to the recorder's own words;
  these two stayed, and they are the trace format's own word for the row —
  `tasks` is a table, and a Rust thread's stream really is a `task_fingerprints`
  row. *Ruled: left alone.* Renaming the printed noun without renaming the
  table would put two words on one fact, which is the failure `vocab.py` exists
  to prevent. If it moves, it moves in both places at once.
- **The zero-candidate refusal wording under a pid cycle.** `find_pair` reads a
  trace as a child when its `ppid` is ANOTHER linked trace's `pid`. Two traces
  each naming the other would leave no candidate at all, and the refusal would
  say the re-run produced no linked trace when it produced two. *Ruled: left as
  is.* The topology is impossible — a pid cycle is not a process tree — and a
  branch written for it could never be exercised, so it would be untested code
  standing where an honest refusal already stands.
- **The fourth E4′ lock test checks table rows and a 200-character prefix, not
  a full line diff.** `test_the_amendment_ADDED_section_1_5_and_moved_no_earlier_row`
  compares every `|` row of §1 byte for byte at the two commits and then asserts
  the amended §1 starts with the first 200 characters of the original's
  pre-§1.5 text. A prose edit in §1.3 or §1.4 beyond that prefix, made in the
  same commit as the amendment, would pass. The rows are what the endpoints
  read, which is why the row check is the load-bearing one; a full diff of the
  pre-amendment range is the stronger check and was not written.
- **`RUSTDOCFLAGS` carries the recorder's own footprint, and the env clause
  reads it as the world's.** E4′'s H1 STOPPED on it: the driver injects
  `--extern sensorium_rt=<target>/sensorium/rt/<hash>/…` with its
  `-L dependency=…`, the 5b rule relocates the target root inside it correctly,
  and the `<hash>` — which keys the `sensorium-rt` build — moved anyway,
  because the originals were recorded by driver **0.5.0** and re-run by
  **0.5.1**. `differs_only_by_root` is right to return false; the key falls
  into the changed list and withholds. *The ruling, from the record's §5*: the
  driver-injected fragment is **stripped before the compare as the recorder's
  own**, on the precedent this licence already sets twice (the `SENSORIUM_*`
  variables, and R1's harness thread); **anything else in `RUSTDOCFLAGS` stays
  the world's** and still withholds — the rule is about that fragment, never
  the variable. Then **E4″** re-measures §1.2's question over a subject that
  includes an original recorded under a different driver build, the one
  condition under which the confound is visible. Not applied in this slice:
  kill 6 forbids a `src` change after the measurement to make it come out
  differently.
- **R6's four items are ruled NOT FUNDED**, in the design's own words: *`--window`;
  refocus over multi-process invocations; an inference-variable opt-out; a
  per-site volume cap — **not funded** until a use asks; declared blind spots
  stand.* Each of the four still has its own bullet above, unstruck, because
  nothing shipped and the refusal or the bound is still what a reader meets.

### Process lessons

- **Mutation-test on a COMMITTED tree.** A mutation run over an uncommitted
  working tree cannot be undone by `git checkout`, and a same-length mutation
  restored within the same second leaves CPython running the mutant's stale
  bytecode. Both are avoidable by mutating from a commit and purging
  `__pycache__`; this slice's two surviving mutants (`85d1860`) were found that
  way.
- **Every Python change to a printed sentence runs the corpus gate WITH the
  driver.** The Python suite pins the words a fixture reaches; the corpus is
  the only gate that puts the real driver behind them, and it skips silently
  enough that two fix rounds went by with the Rust cases unrun. A printed line
  changed without that gate is a line nobody checked.
- **A preflight DRY RUN before a measurement found two instrument confounds
  that no amount of re-reading the pre-registration would have.** §1.2's
  expected licence partition had been derived from the prior run's thread
  counts alone; a fresh `CARGO_TARGET_DIR` (mandated by the same document for
  H4's inode census) would have withheld the licence on all 61 pairs for a
  reason unrelated to R1, and the launch shell's own variables would have done
  it again. Both were ruled and recorded as amendment A1 **before any number
  was read**. The lesson is the order: run the instrument's first pair, read
  what it printed, and amend the lens then — not after the loop closes, when an
  amendment is indistinguishable from a rationalisation.
- **A record's version token comes from installed metadata, and this one was
  stale twice over.** E4′'s §2 recorded the installed distribution token as
  `0.6.0` while `pyproject.toml` said 0.8.4 — the same editable-install
  staleness E9 and E4 already paid for, now on a third record. Worse, the
  preflight's tree-side probe ran `import sensorium; print(sensorium.__version__)`
  against a package that has no `__version__` and captured **stdout only**, so
  the `AttributeError` on stderr became `""` in the lens: a failed probe
  recorded as a blank that reads as measured. Both stand — records are not
  rewritten, and no endpoint gates on either token. **The fix belongs to 7b**:
  refresh the install after the version bump, and a probe that fails records
  `null` with its reason.
