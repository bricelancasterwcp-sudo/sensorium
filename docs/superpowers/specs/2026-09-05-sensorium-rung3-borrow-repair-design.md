# Rung 3 — the borrow repair (design)

Written 2026-09-05, after rung 3 merged (`main` @ `d1b1b57`, sensorium 0.8.0 /
crates 0.3.0). Design authority: Claude, under Brice's rung-3 ruling. The
binding parent is `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`
(R1–R16, §2a, the dated R2 amendment); this document adds to it and changes
none of its measured records. The trigger is `docs/CARRIED-DEBT.md`
(2026-09-05): *"the `&e` rule repair, and the `--workspace` E6 arm that would
measure it — one slice, both halves"*, and *"a frame closing `err` while it
holds TWO chains hops the INNERMOST one … the fix rides the next pre-registered
slice, with a converter test on a hand-built spool as its falsifier"*. Both
were found by the whole-branch review AFTER rung 3's numbers were read and
were recorded, not repaired, for that reason. This is the slice that repairs
them, and measures the repair.

## 0. What this slice must make true

1. **The rule.** An `Err(e) =>` arm that hands `&e` to a function and KEEPS
   the call's product — `let (status, value) = map_error(&e, ..);
   V1Result::json(status, value)` (the clone's `api_v1.rs:396` and `:515`),
   or `Err(e) => map_error(&e),` as a tail — reads `arm_ambiguous`, never
   `arm_handled`. A log-and-continue through a helper whose product is
   dropped (`report(&e);`) stays `arm_handled`, so it is still a SWALLOWED
   candidate.
2. **The measurement.** The repaired rule is measured where the shape
   EXECUTES: a `cargo sensorium test --workspace` arm with no `--lib`
   (integration tests, bins and doctests run), every SWALLOWED line
   hand-adjudicated, gate 0 false accusations — AND a control run of the
   same arm under the pre-repair driver that must show the arm reaches the
   shape (≥ 1 false accusation at a `&e`-through-a-function arm). A PASS
   whose control did not discriminate is recorded as NOT DISCRIMINATING and
   the repair stays "asserted, not measured", which is where it is today.
   This is the E6‴ §5.1 lesson written into the pre-registration.
3. **The hop.** A frame closing `err` while holding two chains gives the exit
   hop to the held chain whose recorded text the RETURN carries; the innermost
   is the fallback, not the rule.
4. **The discipline.** Pre-registration byte-locked before any number is read;
   every changed or new test mutation-tested; records appended, never
   rewritten; the rung-3 design amended by dated pointer, not rewritten.

## 1. Decisions (B1–B8)

Cost-if-wrong is stated per row, as the rung-3 table does.

| Id | Decision | Why | Cost if wrong |
|---|---|---|---|
| B1 | **The `&e` exemption applies only where the borrowing CALL's product is provably dropped.** A shared borrow `&<bound name>` is a provable non-escape when it is a DIRECT argument of a call or method call that is (a) the whole expression of an expression statement ending in `;`, or of a `let _ = …;` with a plain wildcard pattern and no `else`; or (b) a top-level argument of a LOGGING-family macro, or a direct argument of a call/method call that is itself a top-level argument of one (the macro's value is `()` and its text goes to the log). A bare `&e` as a logging macro's top-level argument stays exempt as today. **Everywhere else the borrow ESCAPES**: a `let` with any other pattern, a tail expression (of the arm, a block, a closure, an `if` branch), a call nested inside another call's argument, a condition, a match scrutinee, a struct-literal field, an operand. Inside a `move` closure or `async move` block nothing is exempt (unchanged); `&mut e` is walked like anything else (unchanged). Full statement in §2. | The exemption proved the BORROW cannot outlive the arm and said nothing about the call's VALUE; `map_error(&e, ..)` returns the failure as an HTTP status and body the caller receives. "Dropped at the semicolon" is the only syntactic fact that closes the product channel. | Arms that hand a helper `&e` in a tail or a `let` read AMBIGUOUS where they read HANDLED — the safe direction by R2's own rule. The census and the flip diff (B4) count them. |
| B2 | **The residual is named, not hidden.** A callee that stores a RENDERING of the borrow through a side channel — `&self`, a captured variable, a global (`self.record(&e);`) — is invisible to a syntactic rule; that arm still reads `arm_handled`. Recorded as `rust/HONESTY-BLIND-SPOTS.md` item 23 **(d)**, pinned by a unit row that documents today's reading, marked *untested by fixture* on any real tree. Item 23 (c) becomes "repaired 2026-09-05, measured by E6⁗". | R2's method: catch what the syntax shows, state what it cannot. B1 closes the product channel; the side channel needs inter-procedural analysis this recorder does not do. | One false SWALLOWED on a tree whose logging helper stores what it is handed — named in HONESTY, never silent. |
| B3 | **The exit hop prefers text.** In `chains/mod.rs::close_frame`, on `Outcome::Err`, the hop goes to the innermost HOP-ELIGIBLE held chain (not `merged`, not `sink`) whose `last` text `matches` the RETURN's text; only when no eligible chain matches does it fall back to the innermost eligible held chain — today's rule. Every other chain the frame holds behaves exactly as today (changes hands to the parent). A RETURN whose text is a wildcard (cut or unreadable) matches every chain, so the fallback IS today's behaviour there — stated. Wire unchanged; the Python reader unchanged. | The RAISE/HANDLED rows already search `held_matching` first (Task 4 fix round 2); the `err` close row was the one row that did not, and on a keep-first-error shape it labelled the wrong chain `translated`. | Hop DATA on a shape with two same-text chains in one frame — which R7 says cannot occur (equal text is one chain). Never a verdict. |
| B4 | **The arms** (pre-registered together, §4): **E6⁗-A** = E6‴-A verbatim (`-p bloomery-daemon --lib`, HEAD driver; gate 0 false, both readings, guarded count); **E6⁗-WS** = `cargo sensorium test --workspace` (no `--lib`) under the HEAD driver, `exceptions` on EVERY recorded process (the union is the method, not a deviation), gate 0 false, both readings, guarded count; **E6⁗-WS0** = the same arm under the driver built from the base commit `d1b1b57`, into its OWN from-scratch target and trace store, endpoint ≥ 1 false accusation at a `&e`-through-a-function arm (B5); **E-flip** = BEFORE/AFTER `kind: "arm"` manifest diff from two from-scratch `--workspace --no-run` builds (base driver, HEAD driver), gate: `api_v1.rs:396` and `:515` go `arm_handled → arm_ambiguous`, and no transition other than `arm_handled → arm_ambiguous` occurs; **E6-again′** = the corpus collector, equality, now 20 questions; **E7⁗** = `mechanics.sh` 0 failures; **E0‴** = `info`/`diff` under 60 s on the WS arm's largest process. Reported without a gate: walls, processes, per-process tallies, which flipped arms executed, the census delta frozen before the lock. | E6‴'s `--lib` widening executed the same 2 of 29 blast-radius arms and bought no reach; the shapes B1 repairs live behind integration tests. The plain `cargo test --workspace` on the clone was timed before this design: 17 s from scratch, 948 tests over 105 binaries, 0 failed — the arm is cheap. | A STOP is a finding. A control that does not discriminate downgrades the claim, not the merge. |
| B5 | **What the control licenses.** If E6⁗-WS0 prints ≥ 1 SWALLOWED line at an arm E-flip lists (predicted: `api_v1.rs:515`, driven by `api_v1_test.rs::oversized_prompt_*` through `PromptTooLarge` → `map_error(&e, ..)` → a 400 the caller receives) and E6⁗-WS prints 0 there, the record may say **"measured: the repair removed a false accusation the arm reached."** If the control prints 0 such lines, the record says **"NOT DISCRIMINATING: the arm did not reach the shape"** and CARRIED-DEBT keeps the item open with that fact. The control never gates the merge. | An endpoint that all-passes can license the mistake it was written to prevent when it never reaches the shape (rigorous-experiments §1). The rung-3 record already learned this once. | None hidden: both numbers are printed either way. |
| B6 | **Versions**: `sensorium-transform` 0.3.0 → 0.3.1 (the rule), `cargo-sensorium` 0.3.0 → 0.3.1 (the hop; `DRIVER_VERSION` and its three pins move together), `sensorium-rt` stays 0.3.0 (no wire or runtime change; its `RT_VERSION` pins stay), Python 0.8.0 → 0.8.1 (corpus, tooling, docs). The release task greps the tree for every version string it is about to write (CARRIED-DEBT's lesson). | Two crates changed behaviour; one did not. | A stale pin fails a test loudly. |
| B7 | **Docs by pointer, records by append.** The rung-3 design gains dated one-line pointers at its R2 amendment block, its §2a "cell the review named" paragraph, and R16 (iv)/(vi) — "repaired 2026-09-05, see this document"; nothing there is rewritten. `rust/HONESTY.md` §11's closing `&e` paragraph is REPLACED by a shorter repaired one (the file is at 796/800; if the section grows, §1 is the named split); `rust/HONESTY-BLIND-SPOTS.md` 23 (c) → repaired, 23 (d) added; `rust/HONESTY-INDEX.md` §11 rows cite E6⁗; `docs/TRACE-FORMAT.md` §5's `translated` row gains one dated sentence on the exit hop; `corpus/rust/README.md` gains two rows; `CHANGELOG.md` 0.8.1; `docs/CARRIED-DEBT.md` strikes the two repaired items and the "different sets" item for THIS repair's flip set, and appends this slice's section. | The house rule: resolved items struck through, never deleted; specs amended non-silently. | Wording only. |
| B8 | **Process**: branch `feat/rung3-borrow-repair` from `d1b1b57`; ledger `.superpowers/sdd/2026-09-05-sensorium-rung3-borrow-repair/`; subagent-driven development with one implementer per worktree at a time (two implementers in one worktree swept each other's staged files twice in rung 3); every commit by explicit path with `git show --stat` checked; a review per task, a whole-branch final review, one fix wave; the pre-registration committed ALONE after the code changes and their tests and before any number is read; **no code change after the lock** — a residual found by review after the numbers is recorded, not repaired; PR opened against `main`, merge is Brice's. | Rung 3's process lessons, applied. | — |

## 2. The rule, precisely

The escape test (`rust/sensorium-transform/src/escape.rs`) walks an arm's body
and reports ESCAPED the moment a bound name is used anywhere that is not a
provable non-escape. Today there are two provable non-escapes: a bare name as
a logging macro's argument, and a shared borrow `&name` ANYWHERE
(`visit_expr_reference`). This slice replaces the second with a rule about
the borrowing call's product.

**Dropped-value contexts.** Define a call site as *dropped* when, after
stripping parentheses, it is:

1. the whole expression of `Stmt::Expr(expr, Some(semi))` — an expression
   statement ending in `;`; or
2. the initialiser of `Stmt::Local` whose pattern is `_`, with or without a
   type ascription (`Pat::Wild`, or `Pat::Type` over `Pat::Wild`), and which
   has no `else` block; or
3. a top-level argument of a LOGGING-family macro (`LOGGING_MACROS`, unchanged
   list of nine), after the named-argument strip the macro reader already
   performs.

**The exemption.** A shared borrow `&name` of a bound name is exempt when it
is a DIRECT argument (not the receiver, not nested inside another expression)
of a call (`Expr::Call`) or method call (`Expr::MethodCall`) that is a dropped
call site, and `moved == 0` (not inside a `move` closure or `async move`
block). A bare `&name` that is itself a logging macro's top-level argument is
exempt (the borrow goes to `format_args!`, whose product goes to the log).
Nothing else about the borrow is exempt: `visit_expr_reference` no longer
returns early, so a `&name` anywhere else walks into the name and escapes.

**Shapes, as the unit rows will pin them** (`class_of`, `rust/sensorium-transform/src/arms.rs` tests):

| Shape | Class | Why |
|---|---|---|
| `Err(e) => { note(&e); 0 }` | Handled | dropped call site (1); today's row, unchanged |
| `Err(e) => { self.report(&e); 0 }` | Handled | method call, dropped (1); pins blind spot 23 (d) with a comment |
| `Err(e) => { let _ = note(&e); 0 }` | Handled | dropped (2) |
| `Err(e) => { note(&e, 1, "x"); 0 }` | Handled | other arguments do not matter |
| `Err(e) => { if c { note(&e); } 0 }` | Handled | the inner statement is dropped (1) |
| `Err(e) => { println!("{}", &e); 0 }` | Handled | bare borrow as a logging argument (3); today's row |
| `Err(e) => { println!("{}", render(&e)); 0 }` | Handled | call as a logging argument (3): the product is printed |
| `Err(e) => { let c = \|\| { note(&e); }; c(); 0 }` | Handled | a plain closure borrows; the inner statement is dropped |
| `Err(e) => { let c = move \|\| 1; drop(c); note(&e); 0 }` | Handled | today's row, unchanged |
| `Err(e) => { let (s, v) = map_error(&e, None); json(s, v) }` | **Escaped** | the clone's `:396` — a `let` keeps the product |
| `Err(e) => map_error(&e),` | **Escaped** | a tail: the product is the arm's value (the clone's `api_native/*.rs` shape) |
| `Err(e) => { let r = describe(&e); r }` | **Escaped** | a `let` keeps the product |
| `Err(e) => { v.push(render(&e)); 0 }` | **Escaped** | nested: `render`'s product is handed on |
| `Err(e) => { if check(&e) { 1 } else { 0 } }` | **Escaped** | a condition; the value flows |
| `Err(e) => match &e { _ => 0 },` | **Escaped** | a scrutinee |
| `Err(e) => { let c = \|\| note(&e); c(); 0 }` | **Escaped** | the closure's TAIL is not a dropped site — **this row flips** from today's Handled, with a comment saying so |
| `Err(e) => { note(&e) }` | **Escaped** | a block tail; write `note(&e);` to be seen |
| `Err(e) => { println!("{}", wrap(render(&e))); 0 }` | **Escaped** | nested inside the logging argument's call |
| `Err(e) => { thread::spawn(move \|\| note(&e)); 0 }` | **Escaped** | `move`: unchanged |

Every row above is a test, red before the change. The goldens under
`rust/sensorium-transform/tests/golden/` that carry an arm with a `&e` borrow
are re-derived with the reason in the commit; any golden whose `how` byte
changes is listed in the task report. `census` needs no code change: it
counts by the same `classify`.

**What the transform does NOT change.** No splice fragment changes, so no
line moves and no column shifts differently from 0.8.0 — E7⁗ re-runs
`mechanics.sh` to say so with a number rather than an argument.

## 3. The exit hop

`close_frame(seq, Outcome::Err, text)` today walks the closing frame's chains
innermost-first and hands `hop_out` to the first eligible one it meets
(`consumed_err`). The slice computes, before the walk, `preferred =` the
innermost chain the frame holds that is not `merged`, not `sink`, and whose
`last.matches(text)`; during the walk an eligible chain takes the hop only if
`preferred` is `None` (fallback: innermost, as today) or `preferred == i`.
`open_at_exit` fires exactly when it fires today (no chain took the hop).

Falsifiers, each mutation-tested by restoring the innermost-first line:

- `rust/cargo-sensorium/src/convert/chains/tests.rs` —
  `an_err_close_hops_the_held_chain_whose_text_it_carries_not_the_innermost`:
  A calls B → `ret_err("E", "B1")` (chain B1 held by A); A calls C →
  `ret_err("E2", "C1")` (chain C1 held by A, innermost); A `ret_err("E",
  "B1")`. Asserts: exactly two serials; the hop event at A's close carries
  B1's serial, `translated == false`, `hop == 2`; C1 has no `ExitBefore`
  event; neither terminal is `Merged`.
- `rust/cargo-sensorium/tests/convert_errflow_chains.rs` — the same shape
  through the real binary on a hand-built spool (`SpoolBuilder`), asserting
  the converted RAISE row's `chain.serial` and `chain.translated`.
- `corpus/rust/keep_first_error` — a crate whose `main` calls two failing
  helpers and returns the FIRST error; `exceptions` prints the first chain's
  hops without `(translated …)` and the tally carries no swallow (§5).

The Python reader derives holders by walking frames, not hops
(`Index.unwound_holder`, `Index.harness_holder`); the suite runs unchanged
and the corpus case pins the rendering.

## 4. Pre-registration (the table the acceptance document's §1 will carry)

Document: `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`
(E6⁗ — four primes — following E6 / E6′ / E6‴). §1 is written by the
acceptance-tooling task AFTER the transformer, converter and corpus changes
and their tests are in, with the frozen numbers below filled from the census
binary and the flip diff, and committed ALONE. The runner refuses to start if
§1 differs from that commit (`awk '/^## 1/,/^## 2/'`, sha recorded). A
completed measurement is never re-rolled; a miss is a STOP with its number.

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| E6⁗-A | Does the repaired rule accuse falsely on the arm rung 3 measured? | E6‴-A verbatim: `cargo sensorium test -p bloomery-daemon --lib` on the clone under the HEAD driver; `exceptions <run> --limit 100000`; every SWALLOWED line hand-adjudicated against the source under design R15's reading (log-and-continue is a TRUE swallow; a match guard's read is the BODY's disposition). | **0 false accusations**; both readings reported (amended = the gate; strictest pre-lock beside it); the guarded-arm count beside both. Reported: lines per disposition. **Predicted, no gate: 14 lines, the five source shapes of E6‴ §4.1** — none of E6‴'s fourteen involves a `&e` borrow, so B1 should move nothing here. | The same arm, the same protocol, comparable line for line with E6‴. |
| E6⁗-WS | Does it accuse falsely where the repaired shapes EXECUTE? | `cargo sensorium test --workspace` (no `--lib`) on the clone under the HEAD driver, from a target the prep build emptied; `exceptions` on EVERY recorded process (lib, bin, integration-test and doctest binaries); the union of SWALLOWED lines hand-adjudicated as above. | **0 false accusations** over the union; both readings; guarded count. Reported: processes recorded, per-process tally lines, walls, and of the flip set (E-flip) which arms EXECUTED (a HANDLED event whose `how` starts `arm_` at that site), named one by one — an arm never reached is not evidence. | E6‴ §5.1: `--lib` reaches 2 of 29 blast-radius arms; integration tests are where the rest live. |
| E6⁗-WS0 | Does the arm REACH the shape the repair is for? | The same command under the driver built `--release` from `d1b1b57` (the pre-repair `main`), into `/mnt/extra/sensorium-rung2/bloomery-target-control` (from scratch) and its own `SENSORIUM_DIR`; the same adjudication. | **≥ 1 false accusation at an arm E-flip lists** (predicted: `crates/bloomery-daemon/src/api_v1.rs:515`, reached by `api_v1_test.rs::oversized_prompt_gets_honest_400_not_truncation` and `…_has_the_full_openai_error_envelope`; `:396` is predicted NOT reached — no test found that posts an unknown model without an agent header — and is reported either way). **Not a merge gate**: a 0 here makes E6⁗-WS NOT DISCRIMINATING and the record says so (B5). | rigorous-experiments §1: an endpoint must be shown able to fail. |
| E-flip | Which arms did the repair move, exactly? | Two from-scratch `--workspace --no-run` builds of the clone — base driver into the control target, HEAD driver into the acceptance target — and a diff of their `kind: "arm"` manifest rows keyed `(file, line)` with the `how` each writes. | **`api_v1.rs:396` and `:515` read `arm_handled` BEFORE and `arm_ambiguous` AFTER; every changed row is `arm_handled → arm_ambiguous` (no other transition); the count of changed rows == the frozen census delta.** Frozen before the lock from the census binary on the clone: `arms_handled_before = <N1>`, `arms_handled_after = <N2>`, `arms_escaped_before = <N3>`, `arms_escaped_after = <N4>`, `arm_sites = <N5>`. | Settles CARRIED-DEBT's "different sets" item for this repair by taking the manifest diff rung 3 did not. |
| E6-again′ | Did the repair or the hop move a corpus verdict? | E6's protocol verbatim over every `corpus/rust/*` case with an `exceptions` question — now 20 questions: the 18 of E6‴ plus `err_borrowed_into_value` and `keep_first_error`. Fresh corpus target. | **For every case: printed SWALLOWED lines == the registered set (equality); every swallow case's set non-empty; every `dispositions:` line equal. Any extra or missing line = STOP.** | Parent §8 E6, unchanged. |
| E7⁗ | Did anything move a line or a column? | `rust/tests/mechanics.sh` on the probe workspace with the HEAD driver. | **0 failures, 0 differences** (47 checks as of E6‴; the count reported). | The splice is untouched; the number says so. |
| E0‴ | Does the reader stay usable on the widest trace yet? | `info <run>` and `diff <run> <run>` on the E6⁗-WS process with the most events, 60 s kill armed. | **Both under 60 s**; walls reported. | Parent §8 E0; the workspace arm is the largest volume recorded so far. |

**Lens for every endpoint**: dev profile; the clone at `e209ed9`; the HEAD
driver built `--release` by the runner (commit + sha256 + `built_from`
recorded); the base driver built `--release` from `d1b1b57` in a worktree
under `/mnt/extra` (commit + sha256 recorded); each arm's target from scratch
by its prep build (stated); `~/workspace/bloomery` untouched (HEAD/porcelain
before and after); loads at every arm's start; nothing gated on a wall. Budgets
derived from the plain run measured before this design (17 s from scratch,
948 tests, 105 binaries): 30 min per build, 60 min per instrumented run, as
kill ceilings only. Launched detached (`setsid nohup`), pid file + `.DONE`/
`.FAILED` marker, nothing read before the marker exists.

**Reported without a gate**: the per-process SWALLOWED counts and tallies of
both WS arms side by side; the walls of the plain run, the instrumented runs
and the builds; the number of doctest processes recorded; E1-style plain/call
wall on `--workspace` (the rung-2 addendum lens); the guarded-arm rows named.

## 5. Corpus and tests

- **`corpus/rust/err_borrowed_into_value`** — the fourth side beside
  `logged_arm` (borrow, print, drop → swallow), `err_stored` (move → escaped)
  and `err_rendered_into_value` (format product → escaped): an arm that
  hands `&e` to a helper and returns what the helper built
  (`Err(e) => { let (code, body) = describe(&e); Reply { code, body } }`).
  `exceptions` → `dispositions: ambiguous 1`, `expect_absent: ["SWALLOWED",
  "dispositions: swallowed"]`, the arm line named `bound it to a name and let
  the name escape`; a `tree` question shows the reply carrying the rendering.
  Seeded bug in the `why_logs_fail` shape of the sibling. Mutation: change the
  arm to `report(&e);` + a default → the question goes red with `swallowed 1`.
- **`corpus/rust/keep_first_error`** — `main` calls `first()` (Err A1) then
  `second()` (Err B1) and returns A1; `exceptions` prints A1's chain with an
  exit hop and no `(translated …)`, B1's chain ambiguous, no swallow; a `tree`
  question pins both returns. Mutation: revert B3 → the hop lands on B1's
  chain labelled translated → red.
- **Transformer**: the §2 rows; goldens re-derived; the rustc oracle at
  `-D warnings`; the census re-run on the clone (numbers into §1).
- **Converter**: the two B3 falsifiers; the existing chain tests unchanged.
- **Acceptance tooling**: `rust/tests/acceptance_e6q.py` — a SIBLING of
  `acceptance_e6ppp.py` reusing `phase_e6prime` (which gains an explicit
  selector tail so an arm can be `--workspace` with no `--lib`; the E6‴
  runner's default stays `--lib` and its tests stay green), `phase_prep_build`
  per target, `build_driver` for HEAD plus a base-driver builder, the flip
  diff, the union adjudication table, E0‴ and mechanics; a schema
  (`acceptance_schema_e6q.py`) whose false-accusation cells are `None` with a
  reason (hand adjudication) and never a computed zero; a renderer; and
  box-free tests (`tests/test_acceptance_e6q.py`) for the byte-lock, the two
  arms' one-flag difference, the control's separate driver/target/store, the
  flip diff's transition check, and none-versus-zero. Every test
  mutation-tested.
- **Python**: no code change expected; the suite and the corpus are the check.

## 6. Order of work

T0 branch + ledger + the base driver built from `d1b1b57` (worktree under
`/mnt/extra`, sha recorded) + the BEFORE census on the clone + the BEFORE
manifests (base driver, from-scratch `--workspace --no-run` into the control
target); T1 transformer rule (§2) + rows + goldens + AFTER census; T2
converter hop (§3) + falsifiers; T3 the two corpus cases + README rows; T4
acceptance tooling + tests, then §1 written with the frozen numbers and
committed ALONE (lock sha into the ledger); T5 measurement, detached, once —
hand adjudication of every SWALLOWED line in the three arms, §2–§5, results
json; T6 docs, versions, CHANGELOG, CARRIED-DEBT, design pointers, PR body;
final review; fix wave; push; PR.

## 7. Not in this slice

The nested-literal gap (23 (a), exposure measured zero); the `tracing`
field-syntax non-detection (24); a `chain.holder` wire field; E2″'s
`(file, line)` numerator; `acceptance_lib.read_manifests` on rung-3 manifests;
the `mechanics.sh` split and the E7 second-place column check; the parent
spec's length; the `_run_ids` `run:` keying; the three `chain.terminal`
conformance vectors; any change to which sites are probed.

## 8. Deltas to the rung-3 design (dated pointers T6 adds; nothing rewritten)

- After the "R2 amendment — 2026-09-05" block: *"Amended again 2026-09-05 by
  the borrow repair: the `&e` exemption is a rule about the borrowing call's
  dropped product — `docs/superpowers/specs/2026-09-05-sensorium-rung3-borrow-repair-design.md`
  §2, measured by E6⁗."*
- §2a's "cell the whole-branch review named": *"Repaired 2026-09-05 (borrow
  repair, B3): the `err` close row now runs the text-preferring search;
  falsifiers in `chains/tests.rs` and `convert_errflow_chains.rs`."*
- R16 (iv) and (vi): *"repaired 2026-09-05 — see the borrow-repair design"*;
  R16 gains (vii), the side-channel residual of B2.
