# The Rust recorder's honesty ledger — §11: err flow

Section 11 of [`rust/HONESTY.md`](HONESTY.md), **moved here 2026-09-06 (the
focus tier, rung 4 slice 1) so that file stays under 800 lines**. Rung 3's
close named §1 as the next split and rung 3 took it
(`rust/HONESTY-OUTCOMES.md`); no split was named after that, so this one is
chosen here rather than discovered at the ceiling: §11 is the largest section
and the most self-contained, and moving it leaves room for §12 and for the
rung after this one. **The wording and order are unchanged**, so `§11` still
names what it always named, one file away — including from the code comments
and the ledger's index, which cite `§n` as an identifier.

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

- **SWALLOWED** — a written sink (`.ok()`, `.unwrap_or*`, `let _ =`) or an
  `arm_handled` absorbed the chain in a frame that then closed `ok`, with no
  later RAISE of it, and **no value derived from the `Err` left the arm**: not
  the error itself (a return, a store, a move), not a rendering of it (a
  `format!` product), not the product of a call it was handed to (design B1: a
  `&e` is exempt only where that product is dropped).
  **Reading the error does not carry it out** — a match guard (`Err(e) if
  e.kind() == NotFound => {}`), a `&self` predicate whose result only steers
  control, a log line (`eprintln!("{e:?}")`) — so the failure never reached the
  caller and the verdict stands; **a guarded arm's disposition is its body's**.
  The verdict says the failure did not reach the caller, not that the program
  was wrong to drop it. A chain first seen at the sink itself is still
  SWALLOWED, detailed *born outside this thread's instrumented frames*. A
  reader who finds a value derived from the `Err` reaching the caller has found
  a FALSE accusation, and every pre-registration's gate on this verdict is
  0 of them. Adopted 2026-09-05 (rung-4 entry, N1) from design R15's rulings of
  2026-09-05 and the borrow repair's B1; the acceptance records of 2026-09-04
  and 2026-09-05 were adjudicated under this reading and say so. The tool's own
  words under an escaped arm are a quotation of this bullet:
  `a bound error that is stored, returned or moved out of the arm is not a swallow; an arm that only reads it (a guard, a predicate), formats or logs it and continues is one`
  (`tests/test_honesty_prose.py` pins it).
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
by any arm of that run (§5.5 there). **Two residuals stand, of two different
kinds.** A callee handed `&e` at a dropped call site that STORES a rendering
through `&self`, a capture or a global still reads `arm_handled` — item 23
**(d)**, R16 (vii), **untested by fixture** on a real tree. And the one
genuinely distinct shape among the four never-executed arms —
`codec_probe/boot.rs:110`, `return journal_degraded(pager,
fixture_set_unparseable_reason(&e))`, a borrow nested inside another call's
argument — is in the flip set but was never executed by any arm of this run,
so the repaired rule's treatment of the nested-argument shape is **asserted
and unit-tested, not measured** on a running tree (record §5.5).
