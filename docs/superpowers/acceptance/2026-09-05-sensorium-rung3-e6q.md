# Rung-3 acceptance, the borrow repair — E6⁗-A, E6⁗-WS, E6⁗-WS0, E-flip, E6-again′, E7⁗, E0‴

The record of whether the `&e` rule repaired on 2026-09-05 — a shared borrow
is exempt only where the borrowing CALL's product is provably dropped —
accuses falsely where the repaired shapes actually EXECUTE, and of whether the
arm that measures it can reach those shapes at all.

This is a **new slice, not a re-roll**. The 2026-09-05 E6‴ acceptance
(`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md`) was
measured once and stands as written: E6‴-A and E6‴-W **PASS**, 0 false
accusations of 14 lines under both readings, and its §5.1 recorded that
`--lib` reached 2 of 29 blast-radius arms. Nothing there is re-run, re-scoped
or re-classified by this document. The binding design is
`docs/superpowers/specs/2026-09-05-sensorium-rung3-borrow-repair-design.md`
(B1–B8), which adds to and changes nothing in
`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (R1–R16
— R15's "both readings and the guarded-arm count beside them" and R16's
residual list bind here unchanged); the plan is
`docs/superpowers/plans/2026-09-05-sensorium-rung3-borrow-repair.md`.

Two drivers are measured, and which is which is the point of the control. The
**HEAD driver** is the `cargo-sensorium` binary built `--release` from this
branch (`feat/rung3-borrow-repair`) by the runner at run time, with its commit
and sha256 recorded in §2; E6⁗-A and E6⁗-WS run under it. The **BASE driver**
is built `--release` from the pre-repair `main` at `d1b1b57` in a worktree
under `/mnt/extra`, and E6⁗-WS0 — the discrimination control — runs under it,
into its own from-scratch target and its own trace store. `cargo-sensorium`
has no `--version` flag, so each driver's identity is its worktree's HEAD plus
the binary's sha256, and the version string each arm reports is read after the
run out of the trace that arm wrote.

**§1 is byte-locked.** It is committed ALONE, after the transformer, converter
and corpus changes and their tests but before any E6⁗ number has been read,
and it is design §4's pre-registration with the five census numbers Tasks 0
and 1 measured on the clone before this section was written filled in. The
runner refuses to run if this section differs from the commit that locked it —
compared with `awk '/^## 1/,/^## 2/'`, the sha recorded in §2 — and refuses
outright while no lock sha is set. §1 is not amended: unlike E6‴'s there is
one sha and no dated note inside it. A completed measurement is never
re-rolled, and a miss is a STOP with its number.

## 1. Pre-registration

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| E6⁗-A | Does the repaired rule accuse falsely on the arm rung 3 measured? | E6‴-A verbatim: `cargo sensorium test -p bloomery-daemon --lib` on the clone under the HEAD driver; `exceptions <run> --limit 100000`; every SWALLOWED line hand-adjudicated against the source under design R15's reading (log-and-continue is a TRUE swallow; a match guard's read is the BODY's disposition). | **0 false accusations**; both readings reported (amended = the gate; strictest pre-lock beside it); the guarded-arm count beside both. Reported: lines per disposition. **Predicted, no gate: 14 lines, the five source shapes of E6‴ §4.1** — none of E6‴'s fourteen involves a `&e` borrow, so B1 should move nothing here. | The same arm, the same protocol, comparable line for line with E6‴. |
| E6⁗-WS | Does it accuse falsely where the repaired shapes EXECUTE? | `cargo sensorium test --workspace` (no `--lib`) on the clone under the HEAD driver, from a target the prep build emptied; `exceptions` on EVERY recorded process (lib, bin, integration-test and doctest binaries); the union of SWALLOWED lines hand-adjudicated as above. | **0 false accusations** over the union; both readings; guarded count. Reported: processes recorded, per-process tally lines, walls, and of the flip set (E-flip) which arms EXECUTED (a HANDLED event whose `how` starts `arm_` at that site), named one by one — an arm never reached is not evidence. | E6‴ §5.1: `--lib` reaches 2 of 29 blast-radius arms; integration tests are where the rest live. |
| E6⁗-WS0 | Does the arm REACH the shape the repair is for? | The same command under the driver built `--release` from `d1b1b57` (the pre-repair `main`), into `/mnt/extra/sensorium-rung2/bloomery-target-control` (from scratch) and its own `SENSORIUM_DIR`; the same adjudication. | **≥ 1 false accusation at an arm E-flip lists** (predicted: `crates/bloomery-daemon/src/api_v1.rs:515`, reached by `api_v1_test.rs::oversized_prompt_gets_honest_400_not_truncation` and `…_has_the_full_openai_error_envelope`; `:396` is predicted NOT reached — no test found that posts an unknown model without an agent header — and is reported either way). **Not a merge gate**: a 0 here makes E6⁗-WS NOT DISCRIMINATING and the record says so (B5). | rigorous-experiments §1: an endpoint must be shown able to fail. |
| E-flip | Which arms did the repair move, exactly? | Two from-scratch `--workspace --no-run` builds of the clone — base driver into the control target, HEAD driver into the acceptance target — and a diff of their `kind: "arm"` manifest rows keyed `(file, line)` with the `how` each writes. | **`api_v1.rs:396` and `:515` read `arm_handled` BEFORE and `arm_ambiguous` AFTER; every changed row is `arm_handled → arm_ambiguous` (no other transition); the count of changed rows == the frozen census delta.** Frozen before the lock from the census binary on the clone: `arms_handled_before = 65`, `arms_handled_after = 54`, `arms_escaped_before = 121`, `arms_escaped_after = 132`, `arm_sites = 225`. | Settles CARRIED-DEBT's "different sets" item for this repair by taking the manifest diff rung 3 did not. |
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

## 2. Environment

(written by Task 5)
