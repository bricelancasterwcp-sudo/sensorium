# CARRIED-DEBT

Appended at every merge: *what this slice settled* → *deferred, with
rulings* → *process lessons*. Resolved items are struck through, never
deleted.

Started 2026-09-05, at rung 3's close. Earlier slices carried their debt in
the rung-3 inbox
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3) and in the
gitignored plan ledgers; nothing there is restated here, and that document
stays the record for rungs 0–2.

## 2026-09-05 — S0, trace contract for the sensor-suite program (docs only; no version moves)

### Settled
- Trace format 5 defined for model traces (`docs/trace-format/MODEL-TRACES.md`): `tokens` + `spans`
  tables, generations as `tasks` rows, `lang: "model"`, `fingerprint_basis: "per-generation"`,
  `exit_status_basis: "not-a-process-exit"`. Program recorders stay on 4.
- The cross-trace join: `meta.join` (shared optional key), references over clocks, the one
  same-process `ts_ns` exception (TRACE-FORMAT §6).
- `signature` reading for program traces (MODEL-TRACES §8) — requested by crucible phase D.
- Design spec rulings R1–R10; Brice ruled §12 as recommended (topk 8, recorder off by default,
  `bless-noise` writes into A). Ledger: `.superpowers/sdd/2026-09-05-sensorium-s0-trace-contract/`.

### Deferred, awaiting S1 (each named where it lands)
- `query/vocab.py` model column; `exit_phrase` `n/a (model trace)`; `Trace` format-5 reader;
  `gens`/`tokens`/`spans`/`bless-noise`/`signature` commands; program-command refusals on a model
  trace (exit 2) — all pinned by `vectors/pending/m01–m10, p01`, promoted with the builder.
- `tests/vectors.py` must learn `tokens`/`spans` rows, two-trace vectors (`meta2`/`tokens2`), a
  pinned-reader harness (`m01`), `expect_absent`, `expect_col0`, `expect_same_key` — record each
  in VECTORS.md at promotion.
- README's three "trace format 4" sentences (lines ~345/387/578) stay true for program traces;
  add the format-5 sentence when the recorder ships, not before.
- `SENSORIUM_JOIN` → `meta.join` copy in `record/boot.py` (S3), with `tests/test_join_env.py`.
- The pending vector set is `m01–m10` with `m05` as three files (a/b/c) and `m07` as two
  (`m07a` present program trace, `m07b` trace-not-found), plus `p01`; README documents the extra
  keys `meta2`/`tokens2`/`spans2`/`codes2`/`frames2`/`events2`/`absent2`/`harness`.

### Deferred minors from the task reviews (the final review triages)
- MODEL-TRACES: bare `(R3)`/`(R4)`/`(R5)` citations (§1, §5, §7) not in the "design spec §11 Rn"
  form; three `###` subsection headings in §6/§7 beyond the spec's transcription.
- TRACE-FORMAT: the events-table sentence "`ts_ns` … never compared" has no forward pointer to
  §6's same-process exception.
- pending vectors: `m08`'s question id names the model trace as the joinless one (it is `meta2`);
  `m02` passes a placeholder `grep` pattern `x`; README could say that `start_ts`/`end_ts` (wall
  seconds) and token `ts` (monotonic ns) are different clocks by contract.
- model/HONESTY: index column header reads `Falsifier` where `rust/HONESTY-INDEX.md` says `What
  could falsify it`.

### Process lessons
- A docs-only slice still needs a pytest run per task: `test_vectors.py`'s count is the fence that
  `pending/` stayed invisible.
- The S2 fork's reading of GATE-B/C found seven plan-level corrections before any pre-registration
  was written; brief a fresh reader on the findings docs before locking anything.
- Design authority used for R1–R10 with cost-if-wrong recorded; Brice reviewed the spec, not each
  ruling — the ledger is what makes that reviewable later.
- A plan that quotes shell heredocs must be written with a unique outer terminator; `EOF` inside
  a code block truncated this plan's first write and ran its tail as shell (harmless, caught by
  `git log`/`git status` before anything else).

## 2026-09-05 — rung 3, Err flow (Python 0.8.0 / crates 0.3.0)

### Settled

- `sensorium exceptions` answers on a Rust trace: `?`, four written sinks,
  `let _ =`, classified `Err` arms, closure frames, chains minted at
  conversion, five dispositions behind the shared renderer.
- **The rule was wrong once and the record says so.** E6′ read STOP at 1
  false accusation of 15 (`memory.rs:131` — a `format!` PRODUCT escaping);
  the R2 amendment was pre-registered and re-measured to 0 false of 14 on two
  selectors and both readings (E6‴). Two acceptance documents, neither
  rewritten.
- A `?` the transformer cannot reach is a declared `partial` row, not a
  silent gap. E2″ 392/401 = 97.76 % with the `partial` count pre-registered
  and met.
- Panic locations: lines never move; a column shifts in exactly two places —
  inside a wrapped `?`/sink/`let _` operand by the 6 bytes of `match `
  (**measured**, predicted before both runs and met at both tiers), and after
  an arm probe or closure guard spliced at a same-line `{` by that probe's own
  byte length (**stated, unmeasured**; the shape is
  `rust/sensorium-transform/tests/golden/err_arms_three_ways.out.rs:14`).
- The ledger split: `rust/HONESTY.md` §8's list is now
  `rust/HONESTY-BLIND-SPOTS.md`, numbering unchanged, with rung 3's blind
  spots as items 15–26; the promise→falsifier index is
  `rust/HONESTY-INDEX.md` (moved at the final fix wave, rows unchanged but
  for §11's column row).

### Deferred, awaiting rulings

- ~~**`watch --near` outlived its deprecation.** 0.7.0 said the hidden alias
  would be removed in 0.8.0; 0.8.0 ships with it still present, because the
  release slice was documentation and version metadata only. Three ways out,
  and the choice is a ruling: remove it now in a code slice; re-date the
  promise in `README.md`, `watch_cmd.py` and `tests/test_watch.py` together;
  or keep it indefinitely and say so. Doing nothing leaves a 0.8.0 binary
  printing "(removed in 0.8.0)".~~ — resolved: `--near` removed from the
  parser (this slice); see `CHANGELOG.md` 0.8.0.
- **A `chain.holder` field on the wire.** The holder frame is derived twice
  today — once by the converter's chain machine, once by the Python reader
  walking outward from a chain's last event (`Index.unwound_holder` and
  `Index.harness_holder` in `query/exceptions_rust.py`). One wire field would delete
  both walks. Deferred because the derivation is sound over every §2a row and
  is pinned; a wire change is not free.
- **The nested-literal gap, recorded rather than repaired.** A value-format
  macro nested inside a logging macro's argument
  (`eprintln!("{}", keep(format!("{e}")))`) still reads HANDLED and can reach
  SWALLOWED — the R2 amendment's own class, one nesting level in. Exposure on
  the bloomery clone was measured **zero** before the decision, and the
  pre-registration was already locked, so a zero-exposure change would have
  bought no measurement. Named in design R16 and
  `rust/HONESTY-BLIND-SPOTS.md` item 23 **(a)**; untested by fixture. Item
  23 (b), the whole-word-`e` over-escape, is a different kind of thing — safe
  direction, AMBIGUOUS never an accusation — and its exposure is measured
  nowhere; the zero above covers (a) only.
- ~~**The `&e` rule repair, and the `--workspace` E6 arm that would measure it
  — one slice, both halves.** *The repair:* the escape test exempts `&e`
  because the borrow proves the arm kept the error, but the exemption is
  silent about what the CALL does with its product, so
  `Err(e) => { let (status, value) = map_error(&e, ..);
  V1Result::json(status, value) }` reads `arm_handled` and could print
  SWALLOWED while the failure reached the caller as an HTTP error — the R2
  amendment's class, one function call out (`rust/HONESTY-BLIND-SPOTS.md`
  item 23 (c), design R16). The shape of the repair: `&e` exempt only in a
  statement whose value is dropped. Static exposure on the clone is **2 arms**
  (`crates/bloomery-daemon/src/api_v1.rs:396` and `:515`), and **`--lib`
  executes neither** — which is the other half. *The arm:* E6‴-W widened the
  selector and executed the same 2 of the 29 located blast-radius arms as
  `-p bloomery-daemon --lib`, so the widening bought no reach; integration
  tests, binaries and doctests are where reach would come from. A
  `--workspace` E6 arm with no `--lib` is what makes the repair measurable
  rather than asserted, so both are pre-registered together. Found by the
  whole-branch review AFTER the numbers were read; recorded, not repaired, for
  the reason the process lesson below states.~~ — resolved 2026-09-05 by the
  borrow repair: the exemption now holds only where the borrowing call's
  product is provably dropped (design B1), and the
  `--workspace` arm measured it — **E6⁗-A PASS** (0 false accusations of 14),
  **E6⁗-WS PASS** (0 false of 782 over 144 processes), **E6⁗-WS0
  DISCRIMINATING** (the pre-repair driver printed 30 more lines, every one
  false, at 7 of the 11 flipped arms; the repaired driver printed none). See
  `CHANGELOG.md` 0.8.1 and
  `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`. What the
  repair leaves is the new section below.
- **The reviewer's static list and the census's 31 are different sets.** At
  most 27 of the reviewer's 31 entries can be among the census's 31, and at
  least 4 of the census's 31 are arms the list does not name. A BEFORE/AFTER
  manifest diff across the repair commit would settle it; this run did not
  take one.
  **Annotated 2026-09-05, and left OPEN.** The borrow repair took exactly
  that diff for ITS repair (E-flip): two from-scratch
  `--workspace --no-run` builds, 225 arm sites declared by each, **11**
  changed rows, every transition `arm_handled → arm_ambiguous`,
  `only_before = only_after = []`, and every row named —
  `crates/bloomery-daemon/src/api_native/agents.rs:57, :82, :93, :104,
  :156`, `api_native/models.rs:25, :140`, `api_v1.rs:396, :515`,
  `codec_probe/boot.rs:110`, `pager/paging.rs:673`. That settles the
  METHOD, and it settles the flip set of THIS repair. It does **not**
  settle this item: the two 31-element sets are the E6‴-era reviewer list
  and the E6‴-era census, neither of which was ever enumerated side by
  side, and no diff taken here identifies them. Open until someone
  enumerates those two sets, or rules that the question no longer needs
  answering.
- **`corpus/run_corpus.py::_run_ids` reads any stdout line starting `run: `
  as a trace id.** A case that printed `run: Err(..)` was misread; the case
  worked around it. Key the id line unambiguously in a later slice.
- **`rust/tests/mechanics.sh` is at 795 of 800 lines.** The next check added
  to it must split it first — and there is now a named check waiting for that
  split: **an E7 check for the second place a column can move.** The clause
  adopted at the final fix wave says a column shifts inside a wrapped operand
  by 6 bytes (measured) *and* after an arm probe or closure guard spliced at a
  same-line `{` by the probe's own byte length (stated, unmeasured). A probe
  panic in a one-line `Err(_) => { .. }` arm, plain against instrumented,
  would measure the second half; the shape is
  `rust/sensorium-transform/tests/golden/err_arms_three_ways.out.rs:14`.
- ~~**`rust/HONESTY.md` is at 796 of 800** after §11, even with §8's list
  moved out. The next promise added to it needs the next split chosen
  deliberately — the index, or §1 — rather than discovered at the
  ceiling.~~ — the split was taken at the final fix wave: the
  promise→falsifier index is `rust/HONESTY-INDEX.md`. It bought 17 lines and
  the wave's two clauses (the two-place column rule, the `&e` residual) spent
  them, so **the file is at 796 of 800 again** and the next split is now
  named: **§1**. Stated rather than left to be discovered, which is the point.
  — and taken 2026-09-05 by the borrow repair: §1 is now
  `rust/HONESTY-OUTCOMES.md`, wording and order unchanged, leaving
  `rust/HONESTY.md` at 713 lines after §11's repaired `&e` clause.
- **The parent spec is at 1 458 lines**, over the house ceiling and already
  over it (1 407) before this slice added §11's rung-3 verdict and §13's
  deltas table. Splitting a design spec's history is not a docs pass's call.
- **E2″'s numerator is `(file, line)`-deduped**, so the 97.76 % is a floor
  and the 9-site residual is an instrument artifact, not unreached code (the
  per-file recount is 401/401). A numerator that counts sites rather than
  lines would remove the footnote.
- **Rung-2's `acceptance_lib.read_manifests` breaks on rung-3 manifests** —
  it killed the first E6′ launch before any number was read, and was worked
  around in a rung-3 module rather than fixed at the source.
- ~~**A frame closing `err` while it holds TWO chains hops the INNERMOST one,
  whatever the text says.** `chains/mod.rs`'s exit hop is minted on the
  innermost held chain and does not run the text-matching search the RAISE and
  HANDLED rows use, so a keep-first-error shape (A calls B → `Err` B1, A calls
  C → `Err` C1, A returns B1) records the hop on C1, labelled `translated`,
  and leaves B1 without its hop. **Hop data wrong; never a SWALLOWED**, since
  both chains stay open and both end AMBIGUOUS or PROPAGATED. Named in design
  §2a and R16 on 2026-09-05, found by the whole-branch review after the
  numbers were read. The fix (`held_matching` first, innermost as the
  fallback) rides the next pre-registered slice, with a converter test on a
  hand-built spool as its falsifier.~~ — resolved 2026-09-05 by the borrow
  repair (design B3): `close_frame` now runs the text-preferring search
  first and falls back to the innermost.
  Falsifiers:
  `chains/tests.rs::an_err_close_hops_the_held_chain_whose_text_it_carries_not_the_innermost`,
  `rust/cargo-sensorium/tests/convert_errflow_chains.rs`, and
  `corpus/rust/keep_first_error`.
- **Three `chain.terminal` values have no conformance vector** —
  `panicked`, pinned by `tests/test_exceptions_rust.py` alone
  (`test_a_panic_on_the_holder_quotes_the_panic_and_claims_no_cause`), and
  `left_thread` and `handled_then_failed`, pinned by
  `tests/test_exceptions_rust_ambiguous.py` alone
  (`test_a_chain_that_left_a_spawned_threads_outermost_frame_is_ambiguous`,
  `test_a_sink_whose_frame_then_failed_is_ambiguous_not_swallowed`).
- ~~**`convert/chains/mod.rs`'s doc comment for `hop`** still carries the
  pre-correction wording ("each frame the chain crosses"), which
  `docs/TRACE-FORMAT.md` §5 corrected on 2026-09-05 to count in-frame hops
  too. A comment-only fix, deferred because this slice may not touch
  `rust/**/src`.~~ — resolved at `50c21c3`: the comment now states in-frame
  hops and cites `docs/TRACE-FORMAT.md` §5.

### Process lessons

- **A one-release deprecation is a promise the version bump collects.**
  Nothing in the release checklist looked for a string that names the version
  being cut, and the bump made a shipped sentence false. Grep the tree for
  the version you are about to write before you write it.
- **Mutation-testing the Python side needs `PYTHONPATH`, not a scratch
  copy.** A copy of the repo is not what pytest imports — the editable
  install's `.pth` points at the real tree, so a mutant in the copy is never
  executed and every test stays green, which reads as "the mutation
  survived". Either set `PYTHONPATH=<scratch>/src` so the scratch tree is
  what imports, or mutate in place under `git stash` discipline. Purge
  `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1` either way: a same-length
  mutation restored within the same second leaves CPython running the mutant.
- **Check that a difference is a difference before naming it a finding.**
  Rung 3's own version of this was cheaper than rung 2's, but the shape
  recurs: two numbers computed over different sets are not a divergence, and
  §5.5's "31 vs 31" was two instruments counting different things.
- **A residual found after the numbers are read is recorded, not repaired.**
  Both the nested-literal gap and the `tracing`-syntax non-detection were
  found by review after the pre-registration was locked; repairing either
  would have changed the instrument between the lock and the reading. They
  are in the ledger, in the design, and in the acceptance record's own gaps
  section instead.

## 2026-09-05 — the borrow repair (Python 0.8.1 / transform + driver 0.3.1)

### Settled

- **The `&e` exemption is a rule about the borrowing call's dropped product**
  (design B1). A shared borrow is a provable non-escape only as a direct
  argument of a call that is a dropped call site — an expression statement, a
  `let _ =` with a plain wildcard, or a logging macro's argument; everywhere
  else it ESCAPES. On the bloomery clone (`e209ed9`) the census moves
  arms handled (`arm_handled`) 65 → 54 and arms escaped (`arm_ambiguous`)
  121 → 132 over the same 225 arm sites, with arms propagate
  (`arm_propagate`) unchanged at 39, and no line moved.
- **Measured, with a control that discriminated**
  (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`): **E6⁗-A
  PASS** (0 false accusations of 14 SWALLOWED lines, both readings, 2
  guarded); **E6⁗-WS PASS** (0 false of 782 lines over 144 recorded processes
  at 91 sink sites, both readings, 374 guarded lines at 6 sites); **E6⁗-WS0
  DISCRIMINATING** (the pre-repair driver printed 812 — the same 782 plus 30,
  all 30 false, at 7 of the 11 flipped arms; the repaired driver printed none
  there); **E-flip PASS** (11 changed rows, all `arm_handled →
  arm_ambiguous`, `11 == 65 − 54`, `only_before = only_after = []`);
  **E6-again′ PASS** (0 unequal of 20 corpus `exceptions` questions); **E7⁗
  PASS** (`mechanics.sh` 47 ok, 0 FAIL); **E0‴ PASS** (`info` 1.507 s, `diff`
  1.500 s). §1 was committed alone at `559e617`, sha256
  `c911724b…550e7c27`, and measured once.
- **The exit hop prefers text** (design B3). `close_frame` on `Outcome::Err`
  now gives the hop to the innermost hop-eligible held chain whose `last`
  text matches the RETURN's, falling back to the innermost — the pre-repair
  rule — only when none matches. Hop data only; no disposition and no wire field
  moved.
- **Two Rust corpus cases**, taking the Rust corpus to thirty-one:
  `err_borrowed_into_value` and `keep_first_error`.
- **`driver_version` separates the two drivers again.** The record's §5.7
  notes that all three arms reported `cargo-sensorium 0.3.0`, because the
  version bump runs after the measurement; this release moves
  `sensorium-transform` and `cargo-sensorium` to 0.3.1 and leaves
  `sensorium-rt` at 0.3.0.
- **`rust/HONESTY.md` §1 is `rust/HONESTY-OUTCOMES.md`** — the split rung 3
  named rather than one discovered at the ceiling. Wording and order
  unchanged; the file is at 713 lines with §11's repaired `&e` clause in it.
- **Two stale doc counts corrected**: `tests/test_corpus.py`'s docstring said
  "Eight of the thirteen rung-3 cases" have an empty swallow set and now says
  ten of seventeen (`corpus/rust/README.md`'s number); the top-level
  `README.md` said "Fourteen more cases live under `corpus/rust/`" and now
  says thirty-one, fourteen from rungs 0–2 and seventeen from rung 3.

### Deferred, awaiting rulings

- **The guarded-arm wording debt, now deciding 48 % of a headline** (record
  §5.3). §1's "merely observed" clause admits a letter-reading under which a
  match guard's read is the arm's disposition; under it **374 of E6⁗-WS's 782
  lines** would be false and BOTH workspace endpoints would STOP. The gate is
  design R15's ruled reading (the disposition is the BODY's), and every table
  reports the guarded count beside both readings. E6‴ could call this a
  wording debt at 2 lines of 14; it should be **paid in §1's wording before
  rung 4** rather than inherited a third time.
- **Three classes a reader may reasonably contest** (record §5.4), each
  adjudicated TRUE and each a STOP if a reader rules it false, because the
  gate is 0: (a) test-assertion arms, 31 lines at 31 sites; (b) payload-free
  failures translated into a synthesised value, 22 lines at 4 sites; (c)
  `drift.rs:694`'s re-worded absence, 14 lines (inside the guarded 374).
  None is a `&e`-through-a-function shape, so this repair touches none of
  them. **A per-site `--allow`, or an in-source marker, is the shape that
  would settle all three** — a design question, not a record's to answer.
- **Per-site adjudication is a reading of SOURCE, and R15's criterion is a
  property of EXECUTION** (record §5.2). Of the 1 608 lines adjudicated,
  §4.2 and §4.3 collapse the two workspace arms' 782 and 812 to one row per
  distinct sink site (§4.1's 14 keep E6‴'s per-line shape); the collapse is
  safe only where a site has one downstream disposition or nothing derived
  from the error survives the arm. **`pager/paging.rs:673` is the one site in
  the record whose verdict could turn on which path ran** (three downstream
  endings),
  and its row's stated reason had to be corrected in fix round 1.
- **Four of the eleven flipped arms were never executed** by any arm of the
  run (record §5.5): `api_native/agents.rs:93`, `:104`,
  `api_native/models.rs:25`, `codec_probe/boot.rs:110`. Three are the same
  `Err(e) => map_error(&e),` tail as arms that did run; `boot.rs:110` is the
  one genuinely distinct shape — a borrow nested inside another call's
  argument — so **the repaired rule's treatment of the nested-argument shape
  is asserted and unit-tested, not measured on a running tree**.
- **Two rows §1 asks for are ABSENT, not zero** (record §5.6): the
  plain-versus-instrumented `--workspace` wall (the rung-2 addendum lens) was
  not taken — no uninstrumented `--workspace` run was timed; and the
  **doctest-process split is not something the runner computes** — it records
  144 processes per WS arm and does not classify them by target kind. The
  second needs a per-process target-kind field in the instrument.
- **The side-channel residual, blind spot 23 (d).** A callee handed `&e` at a
  dropped call site that STORES a rendering through `&self`, a capture or a
  global still reads `arm_handled` and can reach SWALLOWED. A syntactic rule
  cannot see it; closing it needs inter-procedural analysis this recorder
  does not do. Pinned as today's reading by
  `a_dropped_call_that_stores_what_it_is_handed_is_still_handled_and_says_so`
  (`rust/sensorium-transform/src/arms.rs`) and named in design R16 (vii);
  **untested by fixture** on a real tree. The nested-literal gap (23 (a)) and
  the `tracing`-syntax non-detection (24) are unchanged by this slice and
  stay carried in the rung-3 section above.
- **`RUSTDOCFLAGS="-D warnings" cargo doc -p sensorium-transform --no-deps`
  fails** on two PRE-EXISTING private-module intra-doc links
  (`rust/sensorium-transform/src/lib.rs:435` and `:442`), verified identical
  before this branch. Rustdoc is not in the gate set (workspace tests,
  clippy `-D warnings`, `cargo fmt --check`, pytest), so nothing red was
  introduced and nothing was fixed here; the ruling is whether rustdoc joins
  the gate.
- **`tests/test_acceptance_e6q.py` is at 800 of 800 lines.** The next test
  added there must split the file first — the `rust/tests/mechanics.sh`
  precedent, stated before it is discovered at the ceiling.
- **A golden fixture carries the PRE-repair sentence in a comment.**
  `rust/sensorium-transform/tests/golden/err_arm_escaped.in.rs:59-60` says "a
  format argument and a shared borrow, the only two uses design R2 calls
  provable". Goldens were deliberately untouched this slice (E7⁗ rests on
  nothing moving), so the sweep waits for the next legitimate golden
  re-derivation.
- **The acceptance runner's own docs still carry the falsified expectation.**
  `rust/tests/acceptance_e6q.py`'s module doc (and the docstring of
  `test_each_arms_driver_version_is_read_from_the_trace_that_arm_wrote` in
  `tests/test_acceptance_e6q.py`) say the control's traces must read
  `cargo-sensorium 0.3.0` and the HEAD arms' the repaired version. Record
  §5.7 falsifies it — all three arms read 0.3.0 — and the measurement is
  complete, so the instrument was left as it stood rather than edited after
  the lock. Sweep when that runner is next legitimately touched.
- **Review minors, deferred rather than repaired after the lock**, one line
  each: the escape walker's `visit_stmt` match guard
  `Some(e) if self.walk_dropped_call(e)` is side-effecting (it walks before
  the arm is chosen; harmless today); no unit row pins a dropped call in
  RECEIVER position (`note(&e).ok();` reads Escaped — design-correct,
  unpinned); `close_frame` computes `preferred` on every outcome though only
  the `Err` branch reads it; `rust/tests/render_e6q.py` is not reachable from
  `render_acceptance.py --doc`; the base driver's sha256 is verified before
  the run but not re-checked at cleanup; `ARM_A["selector"] ==
  real_config(paths)["pkg"]` is unpinned; the E0‴ lens substitution
  yields the grammar "events's size" in two cells; **added at the final
  review**: no unit row pins the escape walker's CALLEE walk
  (`walk_dropped_call`'s `self.visit_expr(&c.func)`) — no test has a dropped
  call whose callee mentions the bound name; `phase_e6prime`'s step text now
  prints the selector, so the E6‴ runner's step line changed while its
  command did not; and `rust/tests/acceptance_schema_e6q.py::_prep`'s
  `arm_sites_distinct` cell can go null via `dropped = _drop(raw, key)`,
  which can be `[]` — a null with no reason, against the module's own rule,
  unreachable today because `arm_rows` always writes `distinct`.
- **`.await`/`?` wrapping a dropped call is not recognized as a dropped
  site.** `log(&e).await;` and `note(&e)?;` are, after `strip`, an
  `Expr::Await`/`Expr::Try` over the call, not the call itself, so
  `walk_dropped_call` does not match and the borrow ESCAPES — the safe
  direction (a lost AMBIGUOUS read, never a false SWALLOWED). Not exercised
  on the bloomery clone (E-flip's 11 changed rows == the frozen census
  delta) and not measured elsewhere. A later slice may unwrap
  `Expr::Await`/`Expr::Try` before matching `Expr::Call`/`Expr::MethodCall`.

### Process lessons

- **A control arm under the PRE-repair instrument is what makes a "0 false"
  PASS mean something.** E6⁗-WS's 0 of 782 would have been compatible with an
  arm that never reached the repaired shape; E6⁗-WS0 printed 30 false
  accusations at 7 arms under the old driver where the new one printed none,
  and only then could the record write **measured** rather than *asserted*.
  Design B5 wrote both branches before the numbers, so the downgrade was
  available and unattractive rather than unthinkable.
- **A §1 prediction can be falsified by its own run, and that is recorded as
  such.** §1 predicted `api_v1.rs:396` would NOT be reached ("no test found
  that posts an unknown model without an agent header"); it was reached, and
  was the busier of the two (7 events and 7 false accusations under the
  control, against 5 and 5 for `:515`). A "no test reaches this" claim
  derived by reading is a hypothesis. Nothing was re-scoped; §1 stands as
  written and record §5.1 says it was wrong.
- **A per-site adjudication table needs the source-versus-execution caveat
  stated, not assumed.** Collapsing lines to sites is safe only where the
  site has one downstream disposition; `paging.rs:673` is the counter-example
  this record contains, and it was caught by review rather than by the
  instrument.
- **Two implementers are never in one worktree.** Rung 3 lost staged files
  twice that way; this slice dispatched one implementer at a time and lost
  none.
- **The runner building its own driver was load-bearing.** The binary on the
  HEAD path was byte-identical to the base driver before the runner rebuilt
  it, so an arm that trusted the path would have measured the control twice
  and called it a PASS.
