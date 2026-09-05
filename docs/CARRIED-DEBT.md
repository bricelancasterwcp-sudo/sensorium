# CARRIED-DEBT

Appended at every merge: *what this slice settled* → *deferred, with
rulings* → *process lessons*. Resolved items are struck through, never
deleted.

Started 2026-09-05, at rung 3's close. Earlier slices carried their debt in
the rung-3 inbox
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3) and in the
gitignored plan ledgers; nothing there is restated here, and that document
stays the record for rungs 0–2.

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
- **The `&e` rule repair, and the `--workspace` E6 arm that would measure it
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
  the reason the process lesson below states.
- **The reviewer's static list and the census's 31 are different sets.** At
  most 27 of the reviewer's 31 entries can be among the census's 31, and at
  least 4 of the census's 31 are arms the list does not name. A BEFORE/AFTER
  manifest diff across the repair commit would settle it; this run did not
  take one.
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
- **A frame closing `err` while it holds TWO chains hops the INNERMOST one,
  whatever the text says.** `chains/mod.rs`'s exit hop is minted on the
  innermost held chain and does not run the text-matching search the RAISE and
  HANDLED rows use, so a keep-first-error shape (A calls B → `Err` B1, A calls
  C → `Err` C1, A returns B1) records the hop on C1, labelled `translated`,
  and leaves B1 without its hop. **Hop data wrong; never a SWALLOWED**, since
  both chains stay open and both end AMBIGUOUS or PROPAGATED. Named in design
  §2a and R16 on 2026-09-05, found by the whole-branch review after the
  numbers were read. The fix (`held_matching` first, innermost as the
  fallback) rides the next pre-registered slice, with a converter test on a
  hand-built spool as its falsifier.
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
