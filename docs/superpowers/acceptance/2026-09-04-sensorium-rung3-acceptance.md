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
| E6′ | Does it accuse falsely on real code? | `cargo sensorium test -p bloomery-daemon --lib` on the clone (all tests), then `sensorium exceptions <run>` paged to completion; every SWALLOWED line hand-adjudicated against the source by the acceptance author, each with a one-line reason. | **0 false accusations** (an `Err` that was stored, returned, re-raised, or merely observed = false).[^e6p-amend] Reported: the total lines per disposition. | E6 has no exposure outside the corpus; bloomery has ~200 `Err` arms. |
| E2″ | Does the transformer reach the `?` sites? | The checked-in census binary over the clone: `try_syn` = syn-visible `ExprTry` nodes; `try_macro_tokens` = `?` tokens inside macro invocations (reported separately, with `?Sized`/`$(…)?` confusions excluded by rule and stated); numerator = `kind: "try"` manifest rows from a from-scratch workspace build. | **numerator / try_syn ≥ 95.0%; 0 units fell back; `partial` rows == try_macro_tokens per file (reported).** Denominator counted BEFORE this section was locked: try_syn = `401`, try_macro_tokens = `1` (Task 0 fills the measured numbers before the byte-lock commit). | Parent §8 E2's second floor. |
| E7″ | Do panic locations survive the new wraps? | `rust/tests/mechanics.sh`'s E7 checks unchanged (lines AND columns) on the probe's existing panics, plus a new probe panic literal placed inside a `?` operand whose expected column shift is the wrap prefix's byte length, computed and written here before the run: prefix = `match ` (6 bytes) → shift +6 for the first byte of the operand. | **Existing checks: 0 differences. New check: line identical, column = original + 6 exactly.** | R15; the wrap moves bytes on a line, never lines. |
| E3″ | Does RAISE/HANDLED entering the fingerprint create false DIVERGED? | Rung 2's E3 protocol verbatim: 20 identical re-runs of one bloomery-daemon test binary, `diff` each against the first. | **DIVERGED 0/19, REFUSED 0/19.** | R12: causal kinds changed; the old measurement no longer covers the new stream. |
| E5″ | Does `diff --ignore-moves` still verify the split with the new events? | The E5′ protocol verbatim (A/B/C arms, the rung-2 schema class). | **A/B MATCH class with every task paired; A/C DIVERGED naming a step in the swapped fn.** | R12. |
| E0″ | Does the reader stay usable at the new event volume? | `info <run>` and `diff <run> <run>` on the E6′ trace, wall-timed, 60 s kill armed. | **Both under 60 s** (E0's kill rule); reported walls. | Parent §8 E0. |

Lens for every endpoint: dev profile; the clone at `e209ed9`; the driver built `--release` from this branch's HEAD at run time (commit + sha256 recorded); warm target (stated); `~/workspace/bloomery` untouched (HEAD/porcelain before and after); loads recorded at every arm's start; nothing gated on a wall.

**Reported without a gate:** E1″ (the `--lib` plain/call walls on `bloomery-daemon`, the rung-2 addendum's protocol and lens), RAISE/HANDLED counts and bytes per record on the E6′ run, `partial` and `closure` frame counts, the per-disposition tally on bloomery.

## 2. Environment

Measured 2026-09-05T00:58:26-0500 → 2026-09-05T01:00:26-0500 by `rust/tests/acceptance_rung3.py`, launched detached; the raw facts it recorded are `results-rung3-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-04-sensorium-rung3-acceptance.results.json`, which `acceptance_schema_rung3.assemble_rung3` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless §1 is byte-identical to the commit that locked it. Checked at `5bc71f7` with `awk '/^## 1/,/^## 2/'`: 3820 bytes, sha256 `98705aa3c7f7e88811efe9e020fa311ccaf968bce175465c471838c3b30d512a` on both sides — identical: yes. The ORIGINAL lock is `e34623c` (sha256 `bd04140521ee31ccc0f158083d5af2f2990ad8c7ab8860bb38a2d077b89181dd`, 3808 bytes); §1 was amended after it: yes (12 bytes added — the dated E6′ footnote).

**Byte-lock, extended — verified 2026-09-05T01:28:28-0500, AFTER the run, on the Task-8 review.** The range above is §1 alone, which covers the `[^e6p-amend]` MARKER and not the footnote's body — the sentence the whole E6′ adjudication turns on — so the lock had a hole at exactly the text it exists to pin. The locked range is now §1 **plus the definition of every footnote §1 references** (here: `[^e6p-amend]`). Over that range: at `5bc71f7` 4958 bytes, sha256 `78b8e60c653f3011c728e2c7612b08f8675448a2e85ddf9dd8920735a0b0ca7e`; at `e34623c` 3808 bytes, sha256 `bd04140521ee31ccc0f158083d5af2f2990ad8c7ab8860bb38a2d077b89181dd` — the amendment is 1150 bytes wide on this range (marker AND body), where the §1-only range showed only the marker's 12. Working tree identical to `5bc71f7`'s: yes. Derived after the run, by `acceptance_rung3.byte_lock_facts` over committed text; the run's own §1-only lock is in `byte_lock` above and is unchanged. No measured number depends on either range; §1 itself is byte-unchanged.

| Pin | Value |
|---|---|
| repo HEAD at the run | `a5322f9247fb2e0655bdac88d03fe992bedf642c` (branch `feat/rung3-err-flow`) |
| driver | `/mnt/extra/sensorium-rung2/rust-target/release/cargo-sensorium`, mtime 2026-09-04T23:21:50-0500 |
| driver sha256 | `797240307f819e8df2004d8721343e22f3359e825e3b153a846c3899ff102a48` — unchanged across the run: yes |
| census driver | `/mnt/extra/sensorium-rung2/rust-target/debug/census` (sha256 `1bda6e5c9a8c82d5870c8583b9510c735be8dde3deaa0f09ca7952e7afd3d06d`) |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| clone (the workspace under measurement) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| E5″ arm tips | A `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`, B `e8c79be1626f5808eb48a967d02a17217e614843`, C `fea50b14ba453a179e94dc96ca71a89a90c35f26` |
| clone porcelain before / after | empty / empty; restored to the pin: yes; `Cargo.lock` unchanged: yes |
| target (warm at the start; **emptied by E2″** for the from-scratch build, which then left it warm for every later arm) | `/mnt/extra/sensorium-rung2/bloomery-target` — 5707718404 bytes removed |
| corpus target (E6) | `/mnt/extra/sensorium-rung2/corpus-target` |
| probe target (E7″) | `/mnt/extra/sensorium-rung2/probe-target` |
| trace store (new and empty at the start) | `/mnt/extra/sensorium-rung2/sensorium-dir/rung3` |
| `~/workspace/bloomery` (READ-ONLY) | `/home/brice/workspace/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` → `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; porcelain empty → empty; unchanged: yes |
| 1-minute load at the start | 0.49 (ceiling 4.0) |
| disk free on the target's filesystem, before / after | 102.76 GB / 102.39 GB |
| E2″'s frozen denominator | try_syn = 401, try_macro_tokens = 1 (§1, counted by Task 0 before the byte-lock) |

1-minute load at each checked-out arm's start: `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` 3.09, `e5-split` 3.09, `e5-planted` 3.09, `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` 3.0.

## 3. Results

Every measurement is `{value, n, lens, dropped}`; a `null` value with a reason is the ONLY not-measured, and `0` is measured-and-zero. Rendered by `rust/tests/render_acceptance.py --doc rung3` from `2026-09-04-sensorium-rung3-acceptance.results.json`. No verdict is decided here — §4 is.

| Id | Headline | n | Lens (abridged) | Dropped |
|---|---|---|---|---|
| E6 | 0 (rule: printed SWALLOWED lines == the registered set for every case; any extra = a false accusation = STOP) | 17 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| E6′ | not measured (adjudicated by hand in §4 of the acceptance document, under both the amended and the strictest pre-lock readings of "merely observed") (rule: 0 false accusations on the bloomery clone) | 15 | FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks for every printed SWALLOWED line to be adjudicat… | adjudicated by hand in §4 of the acceptance document, under both the amended and the strictest pre-lock readings of "merely observed" |
| E2″ | 97.8% (rule: numerator / try_syn ≥ 95.0%; 0 units fell back) | 401 | instrumented 392 / 401 syn-visible `?`; numerator = DISTINCT (file, line) over `kind: "try"` manifest rows fro… | none |
| E7″ | 0 (rule: existing checks: 0 differences; new check: line identical, column = original + 6) | 6 | FAILED E7 checks on the probe's EXISTING panics (lines and columns), of the E7 checks that ran; `rust/tests/me… | none |
| E3″ | 0 (rule: DIVERGED 0/19, REFUSED 0/19) | 19 | DIVERGED + REFUSED verdicts over 19 diffs; `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs … | none |
| E5″ | 0 (rule: A/B MATCH class with every task paired; A/C DIVERGED) | 6 | pre-registered E5 conditions not met, of 6; three arms on three trees (original / split / split + one planted … | none |
| E0″ | 0 (rule: both under 60 s) | 2 | arms at or over the 60 s ceiling; `sensorium info <run>` and `sensorium diff <run> <run>` on the E6' trace, wa… | none |

### E6 — the Rust corpus, every `exceptions` question

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| printed SWALLOWED lines no group claims (false accusations) | 0 | 17 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| registered SWALLOWED groups with no printed line | 0 | 17 | registered SWALLOWED groups with no printed line; every `corpus/rust/*` case with an `exceptions` question, co… | none |
| questions whose swallow SET is not equal | 0 | 17 | questions whose printed swallow set is not EQUAL to the registered one (count, and a perfect matching both way… | none |
| questions whose `dispositions:` tally is not equal | 0 | 17 | questions whose printed `dispositions:` line differs from the registered whole line (or which printed one wher… | none |
| swallow cases that printed an empty set | 0 | 17 | questions registering a non-empty swallow set that printed no SWALLOWED line | none |
| the corpus's own (substring) reading's failures | 0 | 17 | the CORPUS's own reading of the same output (`run_corpus.check_question`: substring, not equality) -- reported… | none |

| Case | Question | SWALLOWED printed / registered | Set equal | Printed tally | Registered tally | Tally equal |
|---|---|---|---|---|---|---|
| `rust/abort` | `did-the-dying-child-drop-an-error` | 0 / 0 | yes | `(none printed)` | `(none registered)` | yes |
| `rust/cleanup_then_fail` | `was-the-cleanup-error-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/closure_try` | `what-did-the-question-mark-in-the-closure-return-from` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/dependency_swallow` | `did-the-cleanup-actually-work` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/err_arms` | `what-did-each-arm-do-with-its-error` | 1 / 1 | yes | `dispositions: swallowed 1, panicked 1, returned-to-harness 1` | `dispositions: swallowed 1, panicked 1, returned-to-harness 1` | yes |
| `rust/err_propagation` | `how-many-failures-were-there` | 0 / 0 | yes | `dispositions: returned-to-harness 1` | `dispositions: returned-to-harness 1` | yes |
| `rust/err_stored` | `were-the-retry-failures-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/interleaved_chains` | `was-either-failure-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/join_handle` | `what-happened-to-the-workers-error` | 1 / 1 | yes | `dispositions: swallowed 1, ambiguous 1` | `dispositions: swallowed 1, ambiguous 1` | yes |
| `rust/logged_arm` | `was-the-refused-attempt-swallowed` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/macro_arg_partial` | `is-the-list-of-errors-complete` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/none_propagation` | `was-there-an-error-behind-the-panic` | 0 / 0 | yes | `(none printed)` | `(none registered)` | yes |
| `rust/outcome_generic` | `does-the-chain-follow-the-error-through-the-generic-frame` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/panic` | `what-did-the-catch-do-with-the-panic` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/returned_to_harness` | `where-did-the-error-the-harness-printed-come-from` | 0 / 0 | yes | `dispositions: returned-to-harness 1` | `dispositions: returned-to-harness 1` | yes |
| `rust/silent_swallow` | `which-settings-were-dropped` | 2 / 2 | yes | `dispositions: swallowed 2` | `dispositions: swallowed 2` | yes |
| `rust/unwrap_panic` | `what-happened-to-the-refusal` | 0 / 0 | yes | `dispositions: panicked 1` | `dispositions: panicked 1` | yes |

### E6′ — the bloomery clone's `--lib` suite

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| SWALLOWED lines printed (each adjudicated in §4) | 15 | 22 | printed SWALLOWED lines, of the chains in scope; `cargo sensorium test -p bloomery-daemon --lib` on the clone … | none |
| SWALLOWED lines the collector could not parse | 0 | 15 | SWALLOWED lines the collector could not parse into (how, event, qualname, line) -- anything but 0 means the ad… | none |
| Err chains judged (`raised (N):`) | 22 | None | `raised (N):` -- Err chains the command judged | none |
| false accusations | not measured (adjudicated by hand in §4 of the acceptance document, under both the amended and the strictest pre-lock readings of "merely observed") | 15 | FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks for every printed SWALLOWED line to be adjudicat… | adjudicated by hand in §4 of the acceptance document, under both the amended and the strictest pre-lock readings of "merely observed" |

Tally line: `dispositions: swallowed 15, ambiguous 7`  
Header `partial:` line: `None`  
Header `panics:` line: `panics: 2 recorded -- this command judges Err flow; a panic is a frame's unwind, printed by `tree` and `frame``  
Paging note (`... N more`): `None`  
Run `20260905-005838-53c4c3`, 1424 events, recorded in 0.367 s; `exceptions` answered in 0.068 s (exit 0).

Every SWALLOWED line, with the sink the trace names for it (the adjudication itself is §4):

| # | how | sink | line |
|---|---|---|---|
| 1 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e317 (tests::fresh_dir L156) in f154, which returned ok` |
| 2 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e318 (tests::fresh_dir L156) in f157, which returned ok` |
| 3 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e319 (tests::fresh_dir L156) in f159, which returned ok` |
| 4 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e353 (tests::tempdir L606) in f176, which returned ok` |
| 5 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` (`MemoryStore::load` L96) | `SWALLOWED -- absorbed by arm_handled at e372 (MemoryStore::load L96) in f181, which returned ok` |
| 6 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:131` (`build_memory` L131) | `SWALLOWED -- absorbed by arm_handled at e391 (build_memory L131) in f192, which returned ok` |
| 7 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` (`MemoryStore::load` L96) | `SWALLOWED -- absorbed by arm_handled at e388 (MemoryStore::load L96) in f195, which returned ok` |
| 8 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e459 (tests::tempdir L606) in f221, which returned ok` |
| 9 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e460 (tests::tempdir L606) in f219, which returned ok` |
| 10 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e486 (tests::tempdir L606) in f237, which returned ok` |
| 11 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e499 (tests::fresh_dir L1084) in f242, which returned ok` |
| 12 | `sink_ok` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:379` (`classify_probe` L379) | `SWALLOWED -- absorbed by sink_ok at e523 (classify_probe L379) in f256, which returned ok` |
| 13 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e545 (tests::fresh_dir L1084) in f265, which returned ok` |
| 14 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e549 (tests::fresh_dir L1084) in f268, which returned ok` |
| 15 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e563 (tests::fresh_dir L1084) in f274, which returned ok` |

### E2″ — the transformer's reach over the clone's `?` sites

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| instrumented `?` sites / syn-visible `?` sites | 97.8% | 401 | instrumented 392 / 401 syn-visible `?`; numerator = DISTINCT (file, line) over `kind: "try"` manifest rows fro… | none |
| numerator — distinct `kind: "try"` manifest rows | 392 | 108 | distinct `kind: "try"` manifest rows | none |
| numerator — the raw sum over the build's manifests | 801 | 108 | the RAW sum of `try` rows over the build's manifests: two (crate_name, crate_type) pairs declare two manifests… | none |
| denominator — §1's frozen `try_syn` | 401 | 191 | §1's frozen `try_syn` over the clone | none |
| units that fell back | 0 | 108 | manifests with `fell_back: true` in the from-scratch workspace build | none |
| `fell back to the real tree` lines in the build log | 0 | 1 | `fell back to the real tree` lines in the build's own log | none |
| `partial` rows (distinct) | 1 | 108 | distinct `partial` rows; §1 reports these against try_macro_tokens = 1 per file | none |
| files a module walk could not reach | 0 | 108 | files a unit's module walk could not reach, unioned | none |
| census re-run at run time: `try_syn` | 401 | 191 | the census binary re-run over the clone at run time. REPORTED, not the denominator: §1 froze try_syn before th… | none |
| census re-run at run time: `try_macro_tokens` | 1 | 191 | the same re-run's macro-argument `?` tokens | none |

The re-run census agrees with the frozen denominator: yes.

`partial` rows per file: `crates/bloomery-bench/src/main.rs` 1; reasons: {'macro-arg': 1}.

### E7″ — panic locations under the new wraps

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| FAILED E7 checks on the probe's existing panics | 0 | 6 | FAILED E7 checks on the probe's EXISTING panics (lines and columns), of the E7 checks that ran; `rust/tests/me… | none |
| E7 checks that passed | 6 | 6 | E7 checks that passed | none |
| new operand panic: column shift, tier `call` | 6 | 1 | instrumented column minus plain column for the panic literal inside a `?` operand, tier `call`; §1 predicted 6… | none |
| new operand panic: column shift, tier `off` | 6 | 1 | the same, tier `off`: the wrapped bytes are identical, only the runtime's answer differs | none |
| new operand panic: line identical (1 = yes) | 1 | 1 | 1 when the panic's LINE is the same in both arms | none |

Predicted shift: **+6** (the wrap prefix `match `). Measured locations:

| Arm | file:line:col |
|---|---|
| plain | `probe-app/tests/e7_operand.rs:33:24` |
| off | `probe-app/tests/e7_operand.rs:33:30` |
| call | `probe-app/tests/e7_operand.rs:33:30` |

`mechanics.sh` exit 0, 47 checks ok; failures: none; skipped: none; driver sha256 unchanged across it: yes.

### E3″ — determinism with RAISE/HANDLED in the fingerprint

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| DIVERGED + REFUSED verdicts | 0 | 19 | DIVERGED + REFUSED verdicts over 19 diffs; `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs … | none |
| DIVERGED | 0 | 19 | `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE test binary built once; the binary's… | none |
| REFUSED | 0 | 19 | `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE test binary built once; the binary's… | none |
| MATCH | 19 | 19 | `sensorium diff <run 1> <run K>` for K = 2..N over N recorded runs of ONE test binary built once; the binary's… | none |
| runs that produced a trace | 20 | 20 | recorded runs that produced a trace | none |
| runs whose binary sha256 differed from run 1's | 0 | 20 | runs whose binary sha256 differed from run 1's | none |

### E5″ — `diff --ignore-moves` still verifies the split

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| pre-registered conditions not met | 0 | 6 | pre-registered E5 conditions not met, of 6; three arms on three trees (original / split / split + one planted … | none |
| code objects paired across a move (A/B) | 28 | 1 | code objects paired across a move by qualname (A/B) | none |

A/B verdict: **MATCH** — `verdict: MATCH -- no causal event ran outside a task on either side, so the thread streams held nothing to compare; the tasks below carry the whole verdict`  
A/C verdict: **DIVERGED** — `verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)`  
Conditions: `{'ab_verdict_is_match': True, 'ab_moved_at_least_one': True, 'ab_zero_added': True, 'ab_zero_removed': True, 'ab_every_task_paired': True, 'ac_verdict_is_diverged': True}`; not met: `[]`.

### E0″ — the reader at the new event volume

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| arms at or over the 60 s ceiling | 0 | 2 | arms at or over the 60 s ceiling; `sensorium info <run>` and `sensorium diff <run> <run>` on the E6' trace, wa… | none |
| `info <run>` wall (s) | 0.046 | 1 | `sensorium info <run>` and `sensorium diff <run> <run>` on the E6' trace, wall-timed, with E0's 60.0 s kill AR… | none |
| `diff <run> <run>` wall (s) | 0.047 | 1 | `sensorium info <run>` and `sensorium diff <run> <run>` on the E6' trace, wall-timed, with E0's 60.0 s kill AR… | none |
| the larger of the two (s) | 0.047 | 2 | `sensorium info <run>` and `sensorium diff <run> <run>` on the E6' trace, wall-timed, with E0's 60.0 s kill AR… | none |

`diff` verdict line: `verdict: MATCH -- no causal event ran outside a task on either side, so the thread streams held nothing to compare; the tasks below carry the whole verdict`.

### Reported without a gate

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| E1″ plain median (s) | 0.063 | 5 | `cargo test -p bloomery-daemon --lib` versus `cargo sensorium test -p bloomery-daemon --lib`, 5 rounds, order … | none |
| E1″ call median (s) | 0.132 | 5 | `cargo test -p bloomery-daemon --lib` versus `cargo sensorium test -p bloomery-daemon --lib`, 5 rounds, order … | none |
| E1″ overhead, call − plain (s) | 0.069 | 5 | call median minus plain median; `cargo test -p bloomery-daemon --lib` versus `cargo sensorium test -p bloomery… | none |
| RAISE events on the E6′ trace | 13 | 1424 | RAISE events on the E6' trace | none |
| HANDLED events on the E6′ trace | 17 | 1424 | HANDLED events on the E6' trace | none |
| bytes per record | 405.573 | 1424 | the E6' trace's size in bytes divided by its event count | none |
| trace bytes | 577536 | 1 | the E6' trace file's size | none |
| `meta.sites` JSON bytes | 230893 | 1 | JSON bytes of `meta.sites` on the E6' trace (the Task-4 watch item) | none |
| `meta.partial` rows on the trace | 0 | 1 | `meta.partial` rows on the E6' trace | none |
| closure frames | 0 | 697 | frames whose kind is `closure`, of every frame on the E6' trace | none |

Per-disposition tally on the clone: `{'swallowed': 15, 'ambiguous': 7}`.  
Site kinds on the trace: `{'fn': 628, 'try': 305, 'sink': 102, 'arm': 141, 'closure': 8}`.  
Event kinds: `{'CALL': 697, 'HANDLED': 17, 'RAISE': 13, 'RETURN': 697}`.  
Frame kinds: `{'function': 697}`.

E1″ walls, every round (a dropped arm is never re-rolled):

| Round | Arm | Order | Load | Wall (s) | Dropped |
|---|---|---|---|---|---|
| 1 | P | PC | 2.84 | 0.063 | none |
| 1 | C | PC | 2.4 | 0.147 | none |
| 2 | C | CP | 2.0 | 0.137 | none |
| 2 | P | CP | 1.7 | 0.074 | none |
| 3 | P | PC | 1.74 | 0.058 | none |
| 3 | C | PC | 1.55 | 0.129 | none |
| 4 | C | CP | 1.69 | 0.12 | none |
| 4 | P | CP | 1.87 | 0.073 | none |
| 5 | P | PC | 1.59 | 0.06 | none |
| 5 | C | PC | 1.34 | 0.132 | none |

## 4. Verdicts

Written by hand against §1's rules, from the raw record
(`results-rung3-raw.json` and the logs beside it in the gitignored plan
ledger). One row per §1 endpoint, with the number that decided it. The run was
launched detached and measured ONCE; nothing was re-run after a number was
read.

| Id | §1's rule, verbatim | What was measured | Verdict |
|---|---|---|---|
| E6 | "**For every case: printed SWALLOWED lines == the case's pre-registered swallow set (equality); every swallow case's set is non-empty; every `dispositions:` tally line equals the case's pre-registered tally. Any extra SWALLOWED line = a false accusation = STOP; any missing = STOP.**" | 17 `corpus/rust/*` cases with an `exceptions` question, each recorded once under the driver of §2. **0** printed SWALLOWED lines that no registered group claims, **0** registered groups with no printed line, **0** questions whose set is unequal, **0** whose `dispositions:` line differs from the registered whole line, **0** swallow cases that printed nothing. Seven of the seventeen questions print a swallow — eight lines in total (`closure_try` 1, `dependency_swallow` 1, `err_arms` 1, `join_handle` 1, `logged_arm` 1, `panic` 1, `silent_swallow` 2) — and the other ten registered an empty set and printed one. | **PASS** |
| E6′ | "**0 false accusations** (an `Err` that was stored, returned, re-raised, or merely observed = false).[^e6p-amend]" | **15** SWALLOWED lines printed on the clone's `--lib` run (22 chains judged; tally `swallowed 15, ambiguous 7`), every one adjudicated against the clone's source in §4.1. **1** of the 15 is a false accusation: row 6, `build_memory` at `crates/bloomery-daemon/src/memory.rs:131`, whose arm renders the error into the value it returns. **The same count, 1, under the strictest pre-lock reading** — §4.3. | **STOP** |
| E2″ | "**numerator / try_syn ≥ 95.0%; 0 units fell back; `partial` rows == try_macro_tokens per file (reported).**" | **392 / 401 = 97.7556 %** (≥ 95.0 %). **0** units with `fell_back: true` over the 108 unit-manifests of the from-scratch `--workspace --no-run` build, and **0** `fell back to the real tree` lines in that build's own log. **1** distinct `partial` row, in `crates/bloomery-bench/src/main.rs`, reason `macro-arg` — equal to §1's frozen `try_macro_tokens = 1`, in the one file that carries it. The 9-site residual is an instrument artifact of the numerator's `(file, line)` dedup, not unreached code — §5.7 names the eight lines and recounts 401 / 401. | **PASS** |
| E7″ | "**Existing checks: 0 differences. New check: line identical, column = original + 6 exactly.**" | **0** failures over the 6 existing E7 checks (`mechanics.sh` exit 0, 47 checks passed, 0 failed, 0 skipped). New check: plain `probe-app/tests/e7_operand.rs:33:24`, instrumented `…:33:30` — **line identical, column + 6 exactly**, on tier `call` AND on tier `off`. | **PASS** |
| E3″ | "**DIVERGED 0/19, REFUSED 0/19.**" | 20 recorded runs of one `bloomery_daemon` `--lib` binary whose sha256 was re-asserted equal before each (**0** mismatches), 19 diffs against the first: **DIVERGED 0/19, REFUSED 0/19, MATCH 19/19**. | **PASS** |
| E5″ | "**A/B MATCH class with every task paired; A/C DIVERGED naming a step in the swapped fn.**" | **0 of 6** conditions missed. A/B `--ignore-moves`: MATCH class, **28** code objects paired across the move, 0 added, 0 removed, every task paired. A/C: **DIVERGED**. | **PASS** |
| E0″ | "**Both under 60 s** (E0's kill rule); reported walls." | `info` **0.046 s**, `diff` **0.047 s**, with the 60 s kill armed (neither was killed). | **PASS** |

**Overall: STOP**, on E6′. The number that missed is **1 false accusation of
15 SWALLOWED lines** — the same under both readings of §1's "merely observed".
It was read once, and nothing was re-run, re-scoped or re-classified after it.
Six of the seven endpoints pass; the STOP is a finding about one rule in the
transformer's arm classifier (§5.1), not about the recorder or the reader.

### 4.1 The E6′ adjudication — every SWALLOWED line on the clone

Every line the run printed, in the order it printed them, adjudicated against
`/mnt/extra/sensorium-rung2/bloomery` at `e209ed9`. `log-and-continue?` marks
the class §1's post-lock amendment is about: an `Err(e) =>` arm whose body only
formats or logs `e` and then continues. Paths are workspace-relative to the
clone.

| # | Printed line | Sink `file:line` | log-and-continue? | Verdict (amended reading) | Reason, from the source |
|---|---|---|---|---|---|
| 1 | `SWALLOWED -- absorbed by sink_let_underscore at e317 (tests::fresh_dir L156) in f154, which returned ok` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` — a written sink discards a `NotFound`; nothing downstream can tell it happened. |
| 2 | `… at e318 (tests::fresh_dir L156) in f157 …` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | Same line, a second test thread. |
| 3 | `… at e319 (tests::fresh_dir L156) in f159 …` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | Same line, a third test thread. |
| 4 | `… absorbed by sink_let_underscore at e353 (tests::tempdir L606) in f176 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` in the exec tests' tempdir helper. |
| 5 | `… absorbed by arm_handled at e372 (MemoryStore::load L96) in f181 …` | `crates/bloomery-daemon/src/memory/store.rs:96` | **no** (the body is EMPTY — it neither logs nor formats) | **TRUE** | `Err(e) if e.kind() == io::ErrorKind::NotFound => { /* First boot: no file yet. */ }` — `e` is read only by the guard, the body drops it, and `load` returns `Ok(empty store)`. The failure reaches no caller. (The reading of the guard is §5.2.) |
| 6 | `… absorbed by arm_handled at e391 (build_memory L131) in f192 …` | `crates/bloomery-daemon/src/memory.rs:131` | no (it formats into the RETURNED value, and does not continue past it) | **FALSE** | `Err(e) => Arc::new(MemoryContext { …, disabled_reason: Some(format!("memory store unreadable: {e}")), store: None })` — the arm's value IS `build_memory`'s return value, and it carries the failure to the caller in `disabled_reason` with `store: None`. §1: an `Err` that was **stored** or **returned** is not a swallow. §5.1. |
| 7 | `… absorbed by arm_handled at e388 (MemoryStore::load L96) in f195 …` | `crates/bloomery-daemon/src/memory/store.rs:96` | **no** (empty body) | **TRUE** | Same arm as row 5, a second test thread. |
| 8 | `… absorbed by sink_let_underscore at e459 (tests::tempdir L606) in f221 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 4. |
| 9 | `… at e460 (tests::tempdir L606) in f219 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 4. |
| 10 | `… at e486 (tests::tempdir L606) in f237 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 4. |
| 11 | `… absorbed by sink_let_underscore at e499 (tests::fresh_dir L1084) in f242 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` in the registry tests' fresh-dir helper. |
| 12 | `… absorbed by sink_ok at e523 (classify_probe L379) in f256 …` | `crates/bloomery-daemon/src/task/registry.rs:379` | no (no binding) | **TRUE** | `.and_then(\|i\| obs.outcome[…].parse::<i64>().ok())` — `.ok()` discards a `ParseIntError` and the `match` falls through to `"inconclusive"`; the parse failure reaches nothing. |
| 13 | `… at e545 (tests::fresh_dir L1084) in f265 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 11. |
| 14 | `… at e549 (tests::fresh_dir L1084) in f268 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 11. |
| 15 | `… at e563 (tests::fresh_dir L1084) in f274 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 11. |

Eleven of the fifteen are the `let _ = fs::remove_dir_all(..)` idiom in three
test helpers, one is `.ok()` on a parse, two are the `NotFound` arm of
`MemoryStore::load`, and one — row 6 — is the miss. Every printed line was
parsed into `(how, event, qualname, line)` by the collector (**0** unparsed),
and every sink's file was resolved from the trace's own
`events → code_objects` join rather than from the sentence.

### 4.2 Why row 6 is a false accusation

The chain the tool printed, whole:

```
  e387 RAISE   MemoryStore::load raise std::io::error::Error('Os { code: 21, kind: IsADirectory, message: "Is a directory" }') L84
    SWALLOWED -- absorbed by arm_handled at e391 (build_memory L131) in f192, which returned ok
      hops: e387 MemoryStore::load L84 try -> e391 build_memory L131 arm_handled
```

The `Err` is born at `store.rs:84` — `let line = line?;` inside `load`'s
`Ok(file)` arm. The test that produces it (`memory.rs:235`,
`build_memory_disabled_reason_when_store_path_is_a_directory`) makes
`episodes.jsonl` itself a **directory**: `File::open` on a directory
succeeds on Linux and the first `read` fails with `EISDIR`, which is the
`Os { code: 21, kind: IsADirectory }` the trace carries. `store.rs:74`'s
`create_dir_all(parent)?` is a different statement and is not the origin.
The chain leaves `load` through the `?` on line 84 and arrives at

```rust
    match store::MemoryStore::load(&store_path) {
        Ok(store) => Arc::new(MemoryContext { …, disabled_reason: None, store: Some(Mutex::new(store)) }),
        Err(e) => Arc::new(MemoryContext {
            …,
            disabled_reason: Some(format!("memory store unreadable: {e}")),
            store: None,
        }),
    }
```

`build_memory` returns `Arc<MemoryContext>` — an infallible signature — so "the
frame returned ok" is trivially true of it and says nothing. What the arm did
with the error is put a rendering of it into the value it returned, beside
`store: None`, which is the field `MemoryContext::operational` gates every
caller on. The failure **reached the caller**, in a durable and inspectable
form. §1 names exactly that: "an `Err` that was **stored**, **returned**,
re-raised, or merely observed = false".

The mechanism is design R2's escape test. An `Err(e) =>` arm is classified
`arm_handled` when `e` provably does not escape, and a **format argument** is
treated as a provable shared borrow — which is true of the `io::Error` value
and false of what `format!` produces from it. `err_stored`'s corpus case pins
the honest answer for the neighbouring shape ("a bound error that is stored,
returned or moved out of the arm is not a swallow" → `ambiguous`), and the last
chain of this very run prints it for the arm at
`tests::a_syntax_error_is_rejected_when_python3_is_present` L197. Row 6 is the same
fact reached through `format!`, and the exemption routed it to `arm_handled`
instead of `arm_ambiguous`.

This is not the amended class. The post-lock amendment makes a **log-and-
continue** arm a TRUE swallow ("the failure never reached the caller; the log
is where it went"); row 6's format does not go to a log and the frame does not
continue past it — the formatted string is the arm's product and the function's
answer.

Two things this verdict does **not** claim. It does not say the recorder or
the converter is wrong: the record is accurate (a HANDLED at `build_memory`
L131 closing a chain whose holder then closed ok). And it does not say
`build_memory` is buggy — it is careful code doing exactly what its doc
comment says. The miss is in the classifier's reading of one arm shape.

### 4.3 The two counts

§1's E6′ endpoint was byte-locked at `e34623c` and its wording amended at
`5bc71f7`, before any E6′ number existed. §4 reports the count under both, so
a reader who rejects the amendment can re-derive the verdict.

| Reading | Count | Verdict |
|---|---|---|
| **The amended reading** (the GATE): a log-and-continue arm is a TRUE swallow | **1 false accusation of 15** | **STOP** |
| **The strictest pre-lock reading**: every log-and-continue arm counted FALSE as well | **1 false accusation of 15** | **STOP** |

The two agree, and the record says why rather than leaving it to be assumed:
**none of the fifteen lines is a log-and-continue arm.** Eleven have no binding
at all (`let _ =`), one is `.ok()`, two are an arm whose body is *empty* — it
neither logs nor formats — and the one miss formats into a returned value
rather than into a log. The class the amendment was written for does not occur
in `bloomery-daemon`'s `--lib` suite, so the amendment moved no number on this
run. That is a fact about this workspace, not a general one: the amendment
still binds, and `corpus/rust/logged_arm` is where the class is pinned.

## 5. Gaps

### 5.1 The finding: a format argument's *product* can escape

The E6′ miss is one rule, and it is narrow enough to state exactly. Design R2
classifies an `Err(e) =>` arm `arm_handled` — the class that can reach
SWALLOWED — when the binding provably does not escape, and it exempts a
**format argument** because `format!("{e}")` takes `e` by shared borrow. That
is true of the borrow and silent about the result: `Some(format!("…{e}"))`
stored in the arm's own returned value carries the failure out of the frame as
surely as `return Err(e)` does, and the tool then reports the frame as having
absorbed it and returned ok.

The repair is not applied here — applying one after reading the number is what
the protocol forbids — and the direction is a ruling for the design authority,
not this document. What is measurable now, for whoever rules it:

* the exposure on the clone is **1 line of 15** on `bloomery-daemon --lib`;
* the neighbouring, correctly-classified shape (`arm_ambiguous`, "bound it to
  a name and let the name escape") is already implemented and already fires on
  this same run, so the miss is a routing question inside the escape test, not
  a missing disposition;
* the Task-3 review flagged the same exemption class from the other side (the
  format-arg and `&e` exemptions applied inside `move` closures) and measured
  its clone exposure as 0/96 handled arms. That measurement was of the
  *closure* variant. This is the *stored-product* variant, and it is not 0.

### 5.2 §1's "merely observed" does not settle a match guard

Rows 5 and 7 (`Err(e) if e.kind() == io::ErrorKind::NotFound => { }`) were
adjudicated **TRUE**, and the reading deserves to be visible because §1's
wording admits another.

§1's amendment says "merely observed" means "read by a `&self` predicate
(`.is_err()`), or its value moved out of the arm". Taken to the letter, the
guard's `e.kind()` *is* a `&self` read, which would make rows 5 and 7 FALSE.
Two things rule against that letter-reading, and both are in the amendment
itself. First, its stated criterion is "the failure never reached the caller" —
and `load` returns `Ok(empty store)`, so nothing downstream can tell a
`NotFound` occurred. Second, the same amendment declares `eprintln!("{e:?}")`
a TRUE swallow, and that too is only a shared-borrow read of `e`; so "read by
a `&self` predicate" cannot mean "any shared-borrow read", or the amendment
would contradict itself in its own sentence. The `.is_err()` example points at
a shape design R2 never probes at all (`.is_err()`/`.is_ok()` take `&self` and
are not sinks), which is why it can never be accused.

**The verdict is robust to the disagreement.** Under the letter-reading the
count is 3 of 15 rather than 1 of 15, and E6′ is a STOP either way. No reading
of §1 makes this run a PASS.

### 5.3 The §1 amendment history, stated once

§1 was committed alone by Task 0 at `e34623c` (3808 bytes, sha256
`bd04140521ee…`), before the transformer changes. On 2026-09-05, after that
lock and before any E6′ number existed, the E6′ endpoint gained a dated
footnote clarifying "merely observed"; §1 is now 3820 bytes, sha256
`98705aa3c7f7…`, at `5bc71f7` — **12 bytes** longer, the footnote marker. The
runner refuses to start unless the working tree's §1 is byte-identical to
`5bc71f7`'s and records both shas; §2 prints them. §4.3 reports the count under
both readings. The original wording is still in §1, in the footnote, unedited.

**The locked range was widened on 2026-09-05, after the run** (Task-8 review):
`awk '/^## 1/,/^## 2/'` covers the `[^e6p-amend]` **marker** and not the
footnote's **body**, so the lock had a hole at exactly the sentence the E6′
adjudication turns on — and the "12 bytes" above is the marker alone. The range
is now §1 plus the definition of every footnote §1 references; over it the
amendment is **1150** bytes wide (marker and body), at `5bc71f7` 4958 bytes
sha256 `78b8e60c653f…` against `e34623c`'s 3808 and `bd04140521ee…`. §2 carries
both, `acceptance_rung3.locked_range` implements it, and
`tests/test_acceptance_rung3.py` pins that editing the footnote body moves the
locked sha while leaving the §1-only sha untouched — the hole, demonstrated.
No measured number depends on either range, and §1 is byte-unchanged.

### 5.4 E7″'s clause: which columns can move, and when

§1's E7″ endpoint measured one wrapped operand and found the predicted +6.
The clause `rust/HONESTY.md` needs is wider than that one shape, and this
document states it so the promise is not read as more than was measured:

> An instrumented build never moves a panic's LINE. It moves a panic's COLUMN
> in exactly two places: inside a wrapped `?`/sink/`let _` operand, by the six
> bytes of the `match ` prefix; and after an arm probe inserted at a **same-
> line arm block** — a one-line `Err(_) => { assert!(flag); 0 }` puts the probe
> between the `{` and `assert!`, moving `assert!`'s column by the probe's byte
> length.

Only the first of the two was measured here. The probe workspace's known
panics are in plain positions, so the six existing E7 checks measure the "no
movement anywhere else" half; the new probe measures the operand half exactly;
the same-line-arm-block half is **stated and unmeasured**, and a reader
debugging a column in that shape should expect a shift of the probe fragment's
length rather than 6.

### 5.5 What this run did not measure

* **E6′ is one package's `--lib` suite.** 15 SWALLOWED lines over 22 chains on
  `bloomery-daemon`. `bloomery-core` and `bloomery-substrate`, every
  integration test, and every `Err` arm those tests do not execute are outside
  it. §1 chose that scope; the count is not a census of the clone's ~225 arms.
* **Closure frames: 0 on the E6′ trace** (`frame_kinds` is `{"function": 697}`)
  although the manifests declare 8 closure sites for the units in it. The
  reported "closure frame count" is therefore a measured zero for this run and
  says nothing about the closure machinery, which `corpus/rust/closure_try`
  pins instead.
* **`meta.partial` rows on the trace: 0.** The clone's one `partial` row is in
  `bloomery-bench`, which the `--lib` run does not load, so `exceptions`
  printed no `partial:` header. The header's *rendering* is pinned by
  `corpus/rust/macro_arg_partial`, not here.
* **E1″ is reported, not gated**, and it is small-workload data: plain median
  **0.063 s**, call median **0.132 s**, overhead **0.069 s** over 5 rounds with
  no arm dropped (loads 1.34–2.84, ceiling 4.0). A 53-test unit suite is
  mostly process start-up in both arms; nothing about a long run follows.
* **The Task-4 `meta.sites` watch item is answered and needs no action.**
  `meta.sites` is **230 893 bytes** of the trace's 577 536 — 40 % of the file —
  and the reader walls that would have shown it are 0.046 s and 0.047 s. The
  ruling was "trim to frame rows only if the wall shows it": it does not.
* **E2″'s denominator was not re-derived.** §1 froze `try_syn = 401` and
  `try_macro_tokens = 1` before the lock; the census binary was re-run at run
  time and reported **401 / 1**, agreeing exactly — but the ratio is taken over
  the frozen numbers, and would have been even if the re-run had disagreed.

### 5.6 Two instrument facts the run exposed

* **The first launch died 10 s in and read no endpoint number.** At
  `2026-09-05T00:54:20-0500`, E2″'s manifest read raised `KeyError:
  'firstlineno'`: the rung-2 `acceptance_lib.read_manifests` keys a site on
  `(file, qualname, firstlineno)` and indexes that field, but rung 3's
  `ManifestSite` serialises `firstlineno` only for a `kind: "fn"` row and
  `line` for the rest (the build's manifests carried 2364 such rows). No gated
  number had been computed — the failure is inside the reader, before any
  endpoint value exists — so it is an infrastructure kill, and the run was
  relaunched from zero at `00:58:26` with a rung-3 reader
  (`acceptance_phases_rung3.read_manifests_rung3`, tested and mutation-tested).
  Both launches emptied and rebuilt the target, so the measured launch met the
  same target state its own E2″ arm creates. `acceptance_lib.py` is left
  byte-unchanged: it is the rung-2 record's instrument.
* **E6's tally comparison is stricter than the corpus harness's.** §1 asks for
  the printed `dispositions:` line to *equal* the case's registered tally;
  `run_corpus.check_question` asks only that the registered string be
  *contained* in the output, and `dispositions: swallowed 2` is a prefix of
  `dispositions: swallowed 2, ambiguous 1`. Both readings were computed:
  **0 failures under either** on all 17 questions. Likewise the swallow set is
  compared by a perfect matching in both directions, not by a per-group
  membership test — two registered groups cannot both claim one printed line
  while a second line goes unclaimed.

### 5.7 E2″'s residual of 9 is the numerator's line-dedup, not unreached code

*Clarification added **2026-09-05**, after the run, on the Task-8 review. **No
measured number changes**: the ratio is **392 / 401 = 97.7556 %** and its
verdict is **PASS**, exactly as measured and locked. What follows names an
instrument artifact the record did not name, from the run's own recorded
numbers.*

**Where the numerator is defined.** `acceptance_phases_rung3._try_rows` counts
**distinct `(file, line)`** over the `kind: "try"` rows of the manifests in the
measured build's own `-C metadata=` scope. The denominator `try_syn` counts
`syn` **`ExprTry` nodes**. The two are not the same unit: a source line
carrying two `?` contributes **2** to the denominator and **1** to the
numerator. Every one of the nine missing sites is that collapse.

**The eight lines**, from the clone at `e209ed9`. Per-file, the run's own
records (`raw_census_try.try_by_file` against `raw_e2pp.try.try_rows_by_file`)
disagree on **exactly four files and nowhere else**:

| File | `try_syn` | distinct rows | collapsed |
|---|---|---|---|
| `crates/bloomery-bench/src/switch.rs` | 38 | 33 | 5 |
| `crates/bloomery-core/src/profile.rs` | 4 | 2 | 2 |
| `crates/bloomery-bench/src/main.rs` | 13 | 12 | 1 |
| `crates/bloomery-daemon/src/drift.rs` | 11 | 10 | 1 |
| **total** | **401** | **392** | **9** |

and the lines are:

```
switch.rs:146   crate::pressure::check(&pressure, &observed, &status_line(client)?)?;
switch.rs:165   let status = client.expect("GET", "/status", "", 200)?.json()?;
switch.rs:219   let status = client.expect("GET", "/status", "", 200)?.json()?;
switch.rs:277   let status = client.expect("GET", "/status", "", 200)?.json()?;
switch.rs:415   let value = client.expect("POST", "/agents", &body, 201)?.json()?;
profile.rs:198  let cell = self.data.codecs.as_ref()?.get(codec)?.get(VERDICT_GRADE)?;
main.rs:80      let client = Client::new(required(args, "--daemon")?)?;
drift.rs:404    found.push((entry.metadata()?.modified()?, name, entry.path()));
```

Seven lines carry two `?` and one (`profile.rs:198`) carries three: 7 × 1 + 1 ×
2 = **9**.

**The recount: 401 / 401.** Counting, per `(file, line)`, the **maximum**
number of `try` rows any single unit-manifest declared there — which un-does
the dedup without double-counting the units that declare one source file twice
— gives **401 over 401, with zero per-file disagreement**, and the only keys
carrying more than one row are exactly the eight lines above (five at 2, two at
2, one at 3). The transformer reached every syn-visible `?` on the clone; the
9-site shortfall is in the numerator's *unit of count*, not in its coverage.

*Provenance of the recount.* It reads the manifests the measured build left on
the target, scoped to that build's own `-C metadata=` set. 106 of the 108 carry
mtimes inside E2″'s window (00:58:28–00:58:36); two were rewritten at
00:58:53–54 by an E5″ arm's build of the same units. That cannot move these
rows: all four files are byte-identical across the three arms — `switch.rs`
`68d1abb5…`, `profile.rs` `cd8c163d…`, `main.rs` `224a9475…`, `drift.rs`
`793040ba…` at `e209ed9`, `e5-split` **and** `e5-planted`.

**CARRIED-DEBT.** The `(file, line)` dedup erodes the ratio on any workspace
with more multi-`?` lines: it is a floor, not an estimate, and a codebase that
chains `?` more densely than bloomery would read materially lower through no
fault of the transformer. The repair is to dedup by `(file, line, col)` — the
manifest row would have to carry the column — or to count nodes directly, in a
later slice. It is not applied here: the ratio above is locked as measured.

[^e6p-amend]: **Amended 2026-09-05, AFTER the byte-lock (e34623c) and BEFORE any E6′ number was read.** "Merely observed" is clarified to mean: read by a `&self` predicate (`.is_err()`), or its value moved out of the arm (stored / returned / re-raised). An `Err(e) =>` arm whose body only formats or logs `e` and then continues (`eprintln!("{e:?}")`, `log::warn!`) is a TRUE swallow — the failure never reached the caller; the log is where it went. Trigger: the Task-7 corpus reviewer observed that R2 classifies format-only arms `arm_handled` (a format argument is a provable shared borrow) so the tool reports them SWALLOWED, while the pre-lock wording could be read as counting them "merely observed". Ruled by the design authority (design R15, §3 `logged_arm`; commit c4d2beb). **Both readings are reported in §4**: the adjudication table marks every log-and-continue SWALLOWED line as such, and the verdict line states the count of false accusations under the amended reading (the gate) AND under the strictest pre-lock reading (log-and-continue counted false), so a reader who rejects the amendment can re-derive the verdict.
