# Rung-3 acceptance — Err flow: E6, E6′, E2″, E7″, E3″, E5″, E0″

The record of whether `sensorium exceptions` answers honestly on a Rust trace.
The binding design is
`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`
(R1–R16 and §2a, the chain machine); the plan that executes it is
`docs/superpowers/plans/2026-09-04-sensorium-rung3-err-flow.md`; the driver
these endpoints are measured with does not exist yet — it is the
`cargo-sensorium` binary built `--release` from this branch
(`feat/rung3-err-flow`) at Task 8's run time, with its commit and sha256
recorded in §2.

**§1 is byte-locked.** It is committed ALONE, before the transformer changes
that would let anyone see how the numbers were going to come out, and it is
the plan's Pre-registration section verbatim with the two `<N…>` placeholders
replaced by the counts Task 0 measured (`try_syn` = 401,
`try_macro_tokens` = 1, `rust/sensorium-transform/src/bin/census.rs` over the
clone at `e209ed9`, pinned in `rust/sensorium-transform/tests/census.rs`).
Task 8 refuses to run if this section differs from that commit; a completed
measurement is never re-rolled, and a miss is a STOP with its number.

## 1. Pre-registration

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| E6 | Does the Rust rule module ever accuse falsely on the corpus? | Every `corpus/rust/*` case with an `exceptions` question, run once under the rung-3 driver; a cross-case collector gathers every printed `SWALLOWED` line and every `dispositions:` tally line. | **For every case: printed SWALLOWED lines == the case's pre-registered swallow set (equality); every swallow case's set is non-empty; every `dispositions:` tally line equals the case's pre-registered tally. Any extra SWALLOWED line = a false accusation = STOP; any missing = STOP.** | Parent §8 E6; the critic's one-sided-subset gap closed. |
| E6′ | Does it accuse falsely on real code? | `cargo sensorium test -p bloomery-daemon --lib` on the clone (all tests), then `sensorium exceptions <run>` paged to completion; every SWALLOWED line hand-adjudicated against the source by the acceptance author, each with a one-line reason. | **0 false accusations** (an `Err` that was stored, returned, re-raised, or merely observed = false). Reported: the total lines per disposition. | E6 has no exposure outside the corpus; bloomery has ~200 `Err` arms. |
| E2″ | Does the transformer reach the `?` sites? | The checked-in census binary over the clone: `try_syn` = syn-visible `ExprTry` nodes; `try_macro_tokens` = `?` tokens inside macro invocations (reported separately, with `?Sized`/`$(…)?` confusions excluded by rule and stated); numerator = `kind: "try"` manifest rows from a from-scratch workspace build. | **numerator / try_syn ≥ 95.0%; 0 units fell back; `partial` rows == try_macro_tokens per file (reported).** Denominator counted BEFORE this section was locked: try_syn = `401`, try_macro_tokens = `1` (Task 0 fills the measured numbers before the byte-lock commit). | Parent §8 E2's second floor. |
| E7″ | Do panic locations survive the new wraps? | `rust/tests/mechanics.sh`'s E7 checks unchanged (lines AND columns) on the probe's existing panics, plus a new probe panic literal placed inside a `?` operand whose expected column shift is the wrap prefix's byte length, computed and written here before the run: prefix = `match ` (6 bytes) → shift +6 for the first byte of the operand. | **Existing checks: 0 differences. New check: line identical, column = original + 6 exactly.** | R15; the wrap moves bytes on a line, never lines. |
| E3″ | Does RAISE/HANDLED entering the fingerprint create false DIVERGED? | Rung 2's E3 protocol verbatim: 20 identical re-runs of one bloomery-daemon test binary, `diff` each against the first. | **DIVERGED 0/19, REFUSED 0/19.** | R12: causal kinds changed; the old measurement no longer covers the new stream. |
| E5″ | Does `diff --ignore-moves` still verify the split with the new events? | The E5′ protocol verbatim (A/B/C arms, the rung-2 schema class). | **A/B MATCH class with every task paired; A/C DIVERGED naming a step in the swapped fn.** | R12. |
| E0″ | Does the reader stay usable at the new event volume? | `info <run>` and `diff <run> <run>` on the E6′ trace, wall-timed, 60 s kill armed. | **Both under 60 s** (E0's kill rule); reported walls. | Parent §8 E0. |

Lens for every endpoint: dev profile; the clone at `e209ed9`; the driver built `--release` from this branch's HEAD at run time (commit + sha256 recorded); warm target (stated); `~/workspace/bloomery` untouched (HEAD/porcelain before and after); loads recorded at every arm's start; nothing gated on a wall.

**Reported without a gate:** E1″ (the `--lib` plain/call walls on `bloomery-daemon`, the rung-2 addendum's protocol and lens), RAISE/HANDLED counts and bytes per record on the E6′ run, `partial` and `closure` frame counts, the per-disposition tally on bloomery.

## 2. Environment

(written by Task 8 from the raw record)

## 3. Results

(written by Task 8 from the raw record)

## 4. Verdicts

(written by Task 8 from the raw record)

## 5. Gaps

(written by Task 8 from the raw record)
