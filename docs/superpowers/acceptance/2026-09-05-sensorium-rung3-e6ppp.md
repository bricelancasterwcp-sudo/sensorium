# Rung-3 acceptance, the R2 repair — E6‴-A, E6‴-W, E6-again, E7‴

The record of whether the R2 amendment of 2026-09-05 — format PRODUCTS escape
the arm, only the unit-returning logging family keeps the bare-argument
exemption — actually removes the false accusation E6′ STOPped on, without
buying it with a new one somewhere else.

This is a **new slice, not a re-roll**. The 2026-09-04 acceptance
(`docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md`) was
measured once and stands as written: E6′ **STOP**, 1 false accusation of 15,
`build_memory` at the clone's `memory.rs:131`. Nothing there is re-run,
re-scoped or re-classified by this document. The binding design is
`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (R1–R16,
§2a, and the dated "R2 amendment — 2026-09-05" block above §2a); the plan is
`docs/superpowers/plans/2026-09-04-sensorium-rung3-err-flow.md` (Addendum
2026-09-05, tasks T10 and T11). The driver these endpoints are measured with
is the `cargo-sensorium` binary built `--release` from this branch
(`feat/rung3-err-flow`) at Task 11's run time, with its commit and sha256
recorded in §2.

**§1 is byte-locked.** It is committed ALONE, after the transformer change and
its tests but before any E6‴ number has been read, and it is the plan
addendum's pre-registration with the two numbers Task 10 measured on the clone
before this section was written (the arm census, below) filled in. It was
**amended once, dated, before any measurement** — the note is inside §1 itself,
in "Reported without a gate", so the lock covers it; §2 records both shas. Task 11
refuses to run if this section differs from the commit that locked it —
compared with `awk '/^## 1/,/^## 2/'`, both shas recorded in §2. A completed
measurement is never re-rolled, and a miss is a STOP with its number.

## 1. Pre-registration

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| E6‴-A | Does it still accuse falsely on real code, on the arm the repair was written for? | E6′'s protocol verbatim: `cargo sensorium test -p bloomery-daemon --lib` on the clone (all tests), then `sensorium exceptions <run>` paged to completion; every SWALLOWED line hand-adjudicated against the source by the acceptance author, each with a one-line reason. | **0 false accusations** (an `Err` that was stored, returned, re-raised, or merely observed = false; "merely observed" means read by a `&self` predicate (`.is_err()`), or its value moved out of the arm — an `Err(e) =>` arm whose body only formats or logs `e` and then continues (`eprintln!("{e:?}")`, `log::warn!`) IS a true swallow, because the failure never reached the caller and the log is where it went). Reported: the total lines per disposition, and the count under BOTH that reading and the strictest pre-lock reading (every log-and-continue arm counted false as well), so a reader who rejects the amendment can re-derive the verdict. | The E6′ row of 2026-09-04 with its dated footnote inlined; the same arm, the same protocol, so the two numbers are comparable line for line. |
| E6‴-W | And on the arms `--lib` never reached? | The same, widened: `cargo sensorium test --workspace --lib` on the clone, then `sensorium exceptions <run>` paged to completion; every SWALLOWED line hand-adjudicated against the source by the acceptance author, each with a one-line reason, under the same reading of "merely observed". | **0 false accusations**, same rule as E6‴-A, both readings reported. Reported: the total lines per disposition; and, of the **31** bound-`Err` arms the clone census moved HANDLED → ESCAPED, how many this run actually EXECUTED against how many exist statically — an arm the run never reaches is not evidence either way, and the record must say which number is which. | `-p bloomery-daemon --lib` executed exactly one of the blast-radius arms (E6′, row 6). A repair sized against ~30 arms that is measured on 1 is not measured. |
| E6-again | Did the repair break the corpus's own falsifier? | E6's protocol verbatim: every `corpus/rust/*` case with an `exceptions` question, run once under the rung-3 driver; a cross-case collector gathers every printed `SWALLOWED` line and every `dispositions:` tally line. The set now includes `corpus/rust/err_rendered_into_value` — 18 questions where E6 had 17. | **For every case: printed SWALLOWED lines == the case's pre-registered swallow set (equality); every swallow case's set is non-empty; every `dispositions:` tally line equals the case's pre-registered tally. Any extra SWALLOWED line = a false accusation = STOP; any missing = STOP.** | Parent §8 E6, unchanged. A rule change that fixes one tree and moves a corpus verdict is a regression, and equality is what catches it. |
| E7‴ | Do panic locations still survive the wraps? | `rust/tests/mechanics.sh`'s E7 checks (lines AND columns) on the probe's existing panics, plus the `?`-operand panic literal E7″ added, whose expected column shift is the wrap prefix's byte length: prefix = `match ` (6 bytes) → shift +6 for the first byte of the operand. | **Existing checks: 0 differences. New check: line identical, column = original + 6 exactly.** | R15, and the mechanics are the one thing a classifier change should not be able to touch — which is why it is measured rather than assumed. |

Lens for every endpoint: dev profile; the clone at `e209ed9`; the driver built `--release` from this branch's HEAD at run time (commit + sha256 recorded); warm target (stated); `~/workspace/bloomery` untouched (HEAD/porcelain before and after); loads recorded at every arm's start; nothing gated on a wall.

**Reported without a gate:** the total lines per disposition in BOTH arms (E6‴-A and E6‴-W), side by side, so the widening's cost in volume is visible; the executed-versus-static count of the blast-radius arms (above); and the clone's arm census across the repair, measured by Task 10 with `SENSORIUM_BLOOMERY_CLONE` at `e209ed9` before this section was locked — **arms escaped 90 → 121, arms handled 96 → 65** (31 arms moved), with every other census number unchanged (191 files, 2051 eligible, 401 `?` as syn nodes and 401 wrapped, 1 `?` in macro tokens, 302 sinks, 225 arm sites, 39 propagate, 0 panic, 9 closure frames, 8 spawns wrapped, 0 line moves, 0 re-parse failures). The Task-8 reviewer's static scan of the same tree estimated ~32; the measured number is 31 and no rule was tuned toward the estimate.

**Amended 2026-09-05, after `33396b0` and before any E6‴ number was read** (fix round 1 of the R2 amendment, commit `321e204`): the escape test's catch-all branch now scans string LITERALS as well as idents for every macro outside the logging family, so a bound name written as a format placeholder inside `anyhow!("{e}")`, `bail!`, `format_err!`, `ensure!` or a workspace render macro escapes rather than reading HANDLED — the same false-accusation class the amendment was written for, reached through a macro the amendment did not name. The frozen numbers above stand unaltered, and this change moved **0** further arms: the clone census re-run read-only at `e209ed9` is byte-for-byte the same, **arms handled 65 / arms escaped 121**, with every other pin unchanged. Corroborated independently: the clone contains 0 occurrences of `anyhow!`, `bail!`, `format_err!` and `ensure!`, so the hole's exposure on THIS tree is zero — a fact about bloomery, not about the rule. E6‴-W is where a non-zero exposure would show up, and its gate is unchanged.

## 2. Environment

## 3. Results

## 4. Verdicts

## 5. Gaps
