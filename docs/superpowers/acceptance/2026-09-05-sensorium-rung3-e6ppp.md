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

Measured 2026-09-05T02:20:30-0500 → 2026-09-05T02:20:49-0500 by `rust/tests/acceptance_e6ppp.py`, launched detached; the raw facts it recorded are `results-e6ppp-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-05-sensorium-rung3-e6ppp.results.json`, which `acceptance_schema_e6ppp.assemble_e6ppp` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless the locked range is byte-identical to the commit that locked it. The range is awk '/^## 1/,/^## 2/' PLUS the definition of every footnote §1 references — here §1 references no footnote (`footnotes_in_range` = none), so the extended range and `awk '/^## 1/,/^## 2/'` are the same bytes. Checked at `254765b`: 5712 bytes, sha256 `9b0c2dfebe8a5d67250cad36ec9030967f7ac0c90447ab13c600e4086d243065` on both sides — identical: yes. The ORIGINAL lock is `33396b0` (sha256 `7803a2a1da73024e265b48c0b2929a7414bf1676404749cce3fd2192b71202ee`, 4655 bytes); §1 was amended after it: yes (1057 bytes added — the dated pre-measurement note inside "Reported without a gate").

| Pin | Value |
|---|---|
| repo HEAD at the run | `abadf7a72c8daa185cfda9c00886520e3e2caa92` (branch `feat/rung3-err-flow`) |
| driver | `/mnt/extra/sensorium-rung2/rust-target/release/cargo-sensorium`, mtime 2026-09-05T01:48:00-0500 |
| driver sha256 | `0ce80ad5aa884ac00a6fbc755354e27bab336a52932332ef0829b22cdb8cee42` — unchanged across the run: yes |
| census driver | `/mnt/extra/sensorium-rung2/rust-target/debug/census` (sha256 `42a4e8e6c30da1d17638a05568f64ac4be8fe2230861f50fcacd628ed2c5dc3c`) |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| clone (the workspace under measurement) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| clone porcelain before / after | empty / empty; restored to the pin: yes; `Cargo.lock` unchanged: yes |
| target (**emptied by the prep build**, which then left it warm for both measured arms) | `/mnt/extra/sensorium-rung2/bloomery-target` — 6090542658 bytes removed |
| corpus target (E6-again) — FRESH for this run | `/mnt/extra/sensorium-rung2/corpus-target-e6ppp`, 0 bytes at the start |
| probe target (E7‴) | `/mnt/extra/sensorium-rung2/probe-target` |
| trace store (new and empty at the start) | `/mnt/extra/sensorium-rung2/sensorium-dir/e6ppp`; per arm E6‴-A `/mnt/extra/sensorium-rung2/sensorium-dir/e6ppp/a`, E6‴-W `/mnt/extra/sensorium-rung2/sensorium-dir/e6ppp/w` |
| `~/workspace/bloomery` (READ-ONLY) | `/home/brice/workspace/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` → `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; porcelain empty → empty; unchanged: yes |
| driver `built_from` (recorded by the runner) | not measured (not recorded: this run's driver was built by the operator before launch and evidenced by its sha256 and mtime (§2, §5.8). `built_from` is recorded by the runner itself from this commit onward) |
| 1-minute load at the start | 0.59 |
| disk free on the target's filesystem, before / after | 101.89 GB / 101.96 GB |
| §1's frozen census (Task 10, before the lock) | arms_escaped_before 90, arms_escaped_after 121, arms_handled_before 96, arms_handled_after 65, arms_moved 31, arm_sites 225, source §1 |

**Log locations.** Every command's log is under `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-04-sensorium-rung3-err-flow/acceptance-e6ppp/logs`, one subdirectory per phase (`built-from`, `prep`, `arm-a`, `arm-w`, `e6-again`, `e7ppp`). **One exception, recorded 2026-09-05, after the run:** the prep build's own log went to `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-04-sensorium-rung3-err-flow/acceptance/logs/prep-workspace.log` — the rung-3 slice's log directory, not this document's. `acceptance_rung3`'s module body re-points `acceptance_lib.LOGS` when it is imported, and the prep phase ran outside a `logs_at` block, so it inherited that pointer. Nothing was clobbered (the rung-3 run writes no file of that name) and no measured number depends on it; the runner now re-asserts the pointer after the import AND wraps the phase, so a later run logs beside its own document.


1-minute load at each arm's start: prep (--workspace --no-run, from scratch) 0.62, E6‴-A 1.23, E6‴-W 1.23, E6-again 1.23, E7‴ 1.23.

## 3. Results

Every measurement is `{value, n, lens, dropped}`; a `null` value with a reason is the ONLY not-measured, and `0` is measured-and-zero. Rendered by `rust/tests/render_acceptance.py --doc e6ppp` from `2026-09-05-sensorium-rung3-e6ppp.results.json`. No verdict is decided here — §4 is.

| Id | Headline | n | Lens (abridged) | Dropped |
|---|---|---|---|---|
| E6‴-A | not measured (adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed") (rule: 0 false accusations on the clone's `-p bloomery-daemon --lib` suite) | 14 | FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks for every printed SWALLOWED line to be adjudicat… | adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed" |
| E6‴-W | not measured (adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed") (rule: 0 false accusations on the clone's `--workspace --lib` suite) | 14 | FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks for every printed SWALLOWED line to be adjudicat… | adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed" |
| E6-again | 0 (rule: printed SWALLOWED lines == the registered set for every case; any extra = a false accusation = STOP) | 18 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| E7‴ | 0 (rule: existing checks: 0 differences; new check: line identical, column = original + 6) | 6 | FAILED E7 checks on the probe's EXISTING panics (lines and columns), of the E7 checks that ran; `rust/tests/me… | none |

### E6‴-A — the clone's `-p bloomery-daemon --lib` suite

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| SWALLOWED lines on the primary process (each adjudicated in §4) | 14 | 22 | printed SWALLOWED lines on the PRIMARY process, of the chains in scope; `cargo sensorium test -p bloomery-daem… | none |
| SWALLOWED lines over EVERY process (primary + sweep) | 14 | 1 | printed SWALLOWED lines over EVERY process this arm recorded (primary + sweep), of the processes recorded; `ca… | none |
| SWALLOWED lines the sweep added | 0 | 0 | SWALLOWED lines the sweep added, of the processes swept; reported without a gate | none |
| SWALLOWED lines the collector could not parse | 0 | 14 | SWALLOWED lines the collector could not parse into (how, event, qualname, line) -- anything but 0 means a row … | none |
| guarded arms (R15; restates §5.2, not a new measurement) | 2 | 14 | SWALLOWED lines whose `Err` binding is read ONLY by a match GUARD -- the class §1's "read by a `&self` predica… | none |
| Err chains judged on the primary (`raised (N):`) | 22 | None | `raised (N):` on the primary process -- Err chains the command judged | none |
| processes recorded | 1 | None | processes the arm recorded (one per test binary) | none |
| false accusations | not measured (adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed") | 14 | FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks for every printed SWALLOWED line to be adjudicat… | adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed" |

Selector: `-p bloomery-daemon --lib`  
Primary tally line: `dispositions: swallowed 14, ambiguous 8`  
Header `partial:` line: `None`  
Header `panics:` line: `panics: 2 recorded -- this command judges Err flow; a panic is a frame's unwind, printed by `tree` and `frame``  
Paging note (`... N more`): `None`  
Primary run `20260905-022041-685d12`, 1424 events, recorded in 0.124 s; `exceptions` answered in 0.067 s (exit 0).

Every SWALLOWED line, with the sink the trace names for it (the adjudication itself is §4):

| # | how | sink | line |
|---|---|---|---|
| 1 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e261 (tests::fresh_dir L156) in f136, which returned ok` |
| 2 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e265 (tests::fresh_dir L156) in f133, which returned ok` |
| 3 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` (`MemoryStore::load` L96) | `SWALLOWED -- absorbed by arm_handled at e307 (MemoryStore::load L96) in f154, which returned ok` |
| 4 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e387 (tests::fresh_dir L156) in f190, which returned ok` |
| 5 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` (`MemoryStore::load` L96) | `SWALLOWED -- absorbed by arm_handled at e392 (MemoryStore::load L96) in f195, which returned ok` |
| 6 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e411 (tests::tempdir L606) in f200, which returned ok` |
| 7 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e417 (tests::tempdir L606) in f208, which returned ok` |
| 8 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e418 (tests::tempdir L606) in f210, which returned ok` |
| 9 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e421 (tests::tempdir L606) in f205, which returned ok` |
| 10 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e445 (tests::fresh_dir L1084) in f220, which returned ok` |
| 11 | `sink_ok` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:379` (`classify_probe` L379) | `SWALLOWED -- absorbed by sink_ok at e476 (classify_probe L379) in f235, which returned ok` |
| 12 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e491 (tests::fresh_dir L1084) in f238, which returned ok` |
| 13 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e498 (tests::fresh_dir L1084) in f246, which returned ok` |
| 14 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e514 (tests::fresh_dir L1084) in f250, which returned ok` |

### E6‴-W — the clone's `--workspace --lib` suite

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| SWALLOWED lines on the primary process (each adjudicated in §4) | 14 | 22 | printed SWALLOWED lines on the PRIMARY process, of the chains in scope; `cargo sensorium test --workspace --li… | none |
| SWALLOWED lines over EVERY process (primary + sweep) | 14 | 3 | printed SWALLOWED lines over EVERY process this arm recorded (primary + sweep), of the processes recorded; `ca… | none |
| SWALLOWED lines the sweep added | 0 | 2 | SWALLOWED lines the sweep added, of the processes swept; reported without a gate | none |
| SWALLOWED lines the collector could not parse | 0 | 14 | SWALLOWED lines the collector could not parse into (how, event, qualname, line) -- anything but 0 means a row … | none |
| guarded arms (R15; restates §5.2, not a new measurement) | 2 | 14 | SWALLOWED lines whose `Err` binding is read ONLY by a match GUARD -- the class §1's "read by a `&self` predica… | none |
| Err chains judged on the primary (`raised (N):`) | 22 | None | `raised (N):` on the primary process -- Err chains the command judged | none |
| processes recorded | 3 | None | processes the arm recorded (one per test binary) | none |
| false accusations | not measured (adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed") | 14 | FALSE ACCUSATIONS. Not measurable by this instrument: §1 asks for every printed SWALLOWED line to be adjudicat… | adjudicated by hand in §4 of the acceptance document, under both the amended reading (the gate) and the strictest pre-lock reading of "merely observed" |

Selector: `--workspace --lib`  
Primary tally line: `dispositions: swallowed 14, ambiguous 8`  
Header `partial:` line: `None`  
Header `panics:` line: `panics: 2 recorded -- this command judges Err flow; a panic is a frame's unwind, printed by `tree` and `frame``  
Paging note (`... N more`): `None`  
Primary run `20260905-022041-6432f1`, 1424 events, recorded in 0.177 s; `exceptions` answered in 0.065 s (exit 0).

Every SWALLOWED line, with the sink the trace names for it (the adjudication itself is §4):

| # | how | sink | line |
|---|---|---|---|
| 1 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e385 (tests::fresh_dir L156) in f190, which returned ok` |
| 2 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` (`MemoryStore::load` L96) | `SWALLOWED -- absorbed by arm_handled at e394 (MemoryStore::load L96) in f195, which returned ok` |
| 3 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e419 (tests::tempdir L606) in f203, which returned ok` |
| 4 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e424 (tests::tempdir L606) in f212, which returned ok` |
| 5 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e425 (tests::fresh_dir L156) in f208, which returned ok` |
| 6 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e426 (tests::tempdir L606) in f205, which returned ok` |
| 7 | `arm_handled` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` (`MemoryStore::load` L96) | `SWALLOWED -- absorbed by arm_handled at e439 (MemoryStore::load L96) in f224, which returned ok` |
| 8 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` (`tests::tempdir` L606) | `SWALLOWED -- absorbed by sink_let_underscore at e444 (tests::tempdir L606) in f220, which returned ok` |
| 9 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` (`tests::fresh_dir` L156) | `SWALLOWED -- absorbed by sink_let_underscore at e445 (tests::fresh_dir L156) in f214, which returned ok` |
| 10 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e485 (tests::fresh_dir L1084) in f237, which returned ok` |
| 11 | `sink_ok` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:379` (`classify_probe` L379) | `SWALLOWED -- absorbed by sink_ok at e496 (classify_probe L379) in f246, which returned ok` |
| 12 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e523 (tests::fresh_dir L1084) in f255, which returned ok` |
| 13 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e534 (tests::fresh_dir L1084) in f262, which returned ok` |
| 14 | `sink_let_underscore` | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` (`tests::fresh_dir` L1084) | `SWALLOWED -- absorbed by sink_let_underscore at e535 (tests::fresh_dir L1084) in f266, which returned ok` |

### E6-again — the Rust corpus, every `exceptions` question

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| printed SWALLOWED lines no group claims (false accusations) | 0 | 18 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| registered SWALLOWED groups with no printed line | 0 | 18 | registered SWALLOWED groups with no printed line; every `corpus/rust/*` case with an `exceptions` question, co… | none |
| questions whose swallow SET is not equal | 0 | 18 | questions whose printed swallow set is not EQUAL to the registered one (count, and a perfect matching both way… | none |
| questions whose `dispositions:` tally is not equal | 0 | 18 | questions whose printed `dispositions:` line differs from the registered whole line (or which printed one wher… | none |
| swallow cases that printed an empty set | 0 | 18 | questions registering a non-empty swallow set that printed no SWALLOWED line | none |
| the corpus's own (substring) reading's failures | 0 | 18 | the CORPUS's own reading of the same output (`run_corpus.check_question`: substring, not equality) -- reported… | none |

| Case | Question | SWALLOWED printed / registered | Set equal | Printed tally | Registered tally | Tally equal |
|---|---|---|---|---|---|---|
| `rust/abort` | `did-the-dying-child-drop-an-error` | 0 / 0 | yes | `(none printed)` | `(none registered)` | yes |
| `rust/cleanup_then_fail` | `was-the-cleanup-error-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/closure_try` | `what-did-the-question-mark-in-the-closure-return-from` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/dependency_swallow` | `did-the-cleanup-actually-work` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/err_arms` | `what-did-each-arm-do-with-its-error` | 1 / 1 | yes | `dispositions: swallowed 1, panicked 1, returned-to-harness 1` | `dispositions: swallowed 1, panicked 1, returned-to-harness 1` | yes |
| `rust/err_propagation` | `how-many-failures-were-there` | 0 / 0 | yes | `dispositions: returned-to-harness 1` | `dispositions: returned-to-harness 1` | yes |
| `rust/err_rendered_into_value` | `was-the-unreadable-settings-error-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 1` | `dispositions: ambiguous 1` | yes |
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

### E7‴ — panic locations under the wraps

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| failed E7 checks on the probe's existing panics | 0 | 6 | FAILED E7 checks on the probe's EXISTING panics (lines and columns), of the E7 checks that ran; `rust/tests/me… | none |
| E7 checks that passed | 6 | 6 | E7 checks that passed | none |
| `?`-operand panic: column shift, tier `call` | 6 | 1 | instrumented column minus plain column for the panic literal inside a `?` operand, tier `call`; §1 predicted 6… | none |
| the same, tier `off` | 6 | 1 | the same, tier `off`: the wrapped bytes are identical, only the runtime's answer differs | none |
| `?`-operand panic: line identical (1 = yes) | 1 | 1 | 1 when the panic's LINE is the same in both arms | none |

Locations: plain `probe-app/tests/e7_operand.rs:33:24`, tier `off` `33:30`, tier `call` `33:30`; §1 predicted a shift of 6.  
`mechanics.sh`: exit 0, 47 ok, 0 FAIL, 0 skip; driver sha unchanged across it: yes.

### Reported without a gate

**Per-disposition tallies, both arms side by side.**

| Arm | processes | primary `dispositions:` line | all processes summed |
|---|---|---|---|
| E6‴-A | 1 | `dispositions: swallowed 14, ambiguous 8` | {'swallowed': 14, 'ambiguous': 8} |
| E6‴-W | 3 | `dispositions: swallowed 14, ambiguous 8` | {'swallowed': 14, 'ambiguous': 15} |

**The blast radius: static, and executed.**

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| entries in the reviewer's static list | 31 | None | entries in the reviewer's list | none |
| of them, carrying a line (intersectable) | 29 | None | entries carrying a line, so intersectable | none |
| of them, named only by file pattern | 2 | None | entries named only by file pattern (`codec_fixtures_*`), which no (file, line) key can match | none |
| located entries that resolve to an arm site | 29 | 29 | `kind: "arm"` rows of the from-scratch `--workspace --no-run` build's own manifests, scoped to that build's `-… | none |
| of those, reading `arm_ambiguous` now | 25 | 29 | of the resolved entries, those the build's manifests now classify `arm_ambiguous` -- the class the R2 amendmen… | none |
| EXECUTED by E6‴-A | 2 | 29 | E6‴-A: located static blast-radius arms this arm EXECUTED, of the located static arms; `kind: "arm"` rows of t… | none |
| EXECUTED by E6‴-W | 2 | 29 | E6‴-W: located static blast-radius arms this arm EXECUTED, of the located static arms; `kind: "arm"` rows of t… | none |
| arm sites that fired at all, E6‴-A | 4 | None | E6‴-A: distinct arm sites that fired at all (the whole tree, not only the blast radius) | none |
| arm sites that fired at all, E6‴-W | 5 | None | E6‴-W: distinct arm sites that fired at all (the whole tree, not only the blast radius) | none |

Unresolved static entries: [].  
Suffixes matching more than one file with an arm at that line: [].  
§1's frozen census (cited, not re-derived): {'arms_escaped_before': 90, 'arms_escaped_after': 121, 'arms_handled_before': 96, 'arms_handled_after': 65, 'arms_moved': 31, 'arm_sites': 225, 'source': '§1'}.

**The prep build** (from-scratch `--workspace --no-run`, which emptied the target so every unit was compiled by this driver and the manifest set is complete):

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| distinct `kind: "arm"` manifest rows | 225 | None | distinct (file, line) `kind: "arm"` manifest rows of this build | none |

exit 0 in 9.351 s over 154 unit(s); arm rows by `how`: {'arm_ambiguous': 121, 'arm_handled': 65, 'arm_propagate': 39}; raw rows 450.

## 4. Verdicts

Written by hand against §1's rules, from the raw record
(`results-e6ppp-raw.json` and the logs beside it in the gitignored plan
ledger). One row per §1 endpoint, with the number that decided it. The run was
launched detached and measured ONCE; nothing was re-run, re-scoped or
re-classified after a number was read.

| Id | §1's rule, verbatim | What was measured | Verdict |
|---|---|---|---|
| E6‴-A | "**0 false accusations** (an `Err` that was stored, returned, re-raised, or merely observed = false … an `Err(e) =>` arm whose body only formats or logs `e` and then continues … IS a true swallow)" | **14** SWALLOWED lines on the clone's `-p bloomery-daemon --lib` run (22 chains judged; tally `swallowed 14, ambiguous 8`; 1 process, so the sweep had nothing to add), every one adjudicated against the clone's source in §4.1. **0** false accusations under the amended reading; **0** under the strictest pre-lock reading — §4.3. | **PASS** |
| E6‴-W | "**0 false accusations**, same rule as E6‴-A, both readings reported." | **14** SWALLOWED lines over ALL THREE processes of the clone's `--workspace --lib` run — 14 on the `bloomery_daemon` lib binary (22 chains; tally `swallowed 14, ambiguous 8`) and **0** on the `bloomery_bench` (184 events, `dispositions: ambiguous 4`) and `bloomery_substrate` (35 events, `dispositions: ambiguous 3`) binaries the sweep read. Every line adjudicated in §4.2. **0** false accusations under the amended reading; **0** under the strictest pre-lock reading — §4.3. Executed-versus-static, as §1 requires: **2** of the **29** located blast-radius arms, of **31** the reviewer's list enumerates (§4.5). | **PASS** |
| E6-again | "**For every case: printed SWALLOWED lines == the case's pre-registered swallow set (equality); every swallow case's set is non-empty; every `dispositions:` tally line equals the case's pre-registered tally. Any extra SWALLOWED line = a false accusation = STOP; any missing = STOP.**" | **18** `corpus/rust/*` cases with an `exceptions` question — E6's 17 plus `err_rendered_into_value` — each recorded once under the driver of §2. **0** printed SWALLOWED lines that no registered group claims, **0** registered groups with no printed line, **0** questions whose set is unequal, **0** whose `dispositions:` line differs from the registered whole line, **0** swallow cases that printed nothing. Eight lines printed in total, over the same seven cases as E6; the new case prints none and pins `dispositions: ambiguous 1`. | **PASS** |
| E7‴ | "**Existing checks: 0 differences. New check: line identical, column = original + 6 exactly.**" | **0** failures over the 6 existing E7 checks (`mechanics.sh` exit 0, 47 checks passed, 0 failed, 0 skipped; driver sha256 unchanged across it). New check: plain `probe-app/tests/e7_operand.rs:33:24`, instrumented `…:33:30` — **line identical, column + 6 exactly**, on tier `call` AND on tier `off`. | **PASS** |

**Overall: PASS.** The R2 amendment removed the one false accusation E6′
STOPped on and bought no new one: 14 SWALLOWED lines where E6′ printed 15, the
missing line is exactly row 6 (`build_memory` at `memory.rs:131`), and all 14
survivors are true swallows under both readings §1 asks for. The corpus's own
falsifier is unmoved (18 of 18 equal on all three conjuncts) and the mechanics
are untouched.

Two things this PASS does **not** say, both measured rather than assumed.
It does not say the repair was exercised broadly: `--workspace --lib` executed
the **same 2** of the 29 located blast-radius arms as `-p bloomery-daemon
--lib`, so the widening cost two extra processes and bought no extra reach
(§5.1). And it does not settle §1's "merely observed" for a match guard: under
the letter-reading of that clause both arms would read **2 of 14** and the
verdict would be a STOP (§5.2). The gate is the amended reading, and it is met.

### 4.1 The E6‴-A adjudication — every SWALLOWED line on the clone

Every line the run printed, in the order it printed them, adjudicated against
`/mnt/extra/sensorium-rung2/bloomery` at `e209ed9`, read fresh from the clone
after the run. `log-and-continue?` marks the class §1's amendment is about: an
`Err(e) =>` arm whose body only formats or logs `e` and then continues. Paths
are workspace-relative to the clone.

| # | Printed line | Sink `file:line` | log-and-continue? | Verdict (amended reading) | Reason, from the source |
|---|---|---|---|---|---|
| 1 | `SWALLOWED -- absorbed by sink_let_underscore at e261 (tests::fresh_dir L156) in f136, which returned ok` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` — a written sink discards a `NotFound`; the next statement is `create_dir_all(&dir).unwrap()` and nothing downstream can tell the removal failed. |
| 2 | `… at e265 (tests::fresh_dir L156) in f133 …` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | Same line, a second test thread. |
| 3 | `… absorbed by arm_handled at e307 (MemoryStore::load L96) in f154 …` | `crates/bloomery-daemon/src/memory/store.rs:96` | **no** (the body is EMPTY — it neither logs nor formats) | **TRUE** | `Err(e) if e.kind() == io::ErrorKind::NotFound => { // First boot: no file yet. Empty store, not an error. }` — `e` is read only by the guard, the body drops it, and `load` returns `Ok(MemoryStore { … })`. The failure reaches no caller. (The reading of the guard is §5.2.) |
| 4 | `… at e387 (tests::fresh_dir L156) in f190 …` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | Same line as row 1, a third test thread. |
| 5 | `… absorbed by arm_handled at e392 (MemoryStore::load L96) in f195 …` | `crates/bloomery-daemon/src/memory/store.rs:96` | **no** (empty body) | **TRUE** | Same arm as row 3, a second test thread. |
| 6 | `… absorbed by sink_let_underscore at e411 (tests::tempdir L606) in f200 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` in the exec tests' `tempdir` helper, followed by `create_dir_all(&dir).unwrap()`. |
| 7 | `… at e417 (tests::tempdir L606) in f208 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 6. |
| 8 | `… at e418 (tests::tempdir L606) in f210 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 6. |
| 9 | `… at e421 (tests::tempdir L606) in f205 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 6. |
| 10 | `… absorbed by sink_let_underscore at e445 (tests::fresh_dir L1084) in f220 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` in the registry tests' `fresh_dir` helper. |
| 11 | `… absorbed by sink_ok at e476 (classify_probe L379) in f235 …` | `crates/bloomery-daemon/src/task/registry.rs:379` | no (no binding) | **TRUE** | `.and_then(\|i\| obs.outcome[i + " exit ".len()..].parse::<i64>().ok())` — `.ok()` discards a `ParseIntError` and the `match` falls through to `"inconclusive"`; the parse failure reaches nothing. |
| 12 | `… at e491 (tests::fresh_dir L1084) in f238 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 10. |
| 13 | `… at e498 (tests::fresh_dir L1084) in f246 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 10. |
| 14 | `… at e514 (tests::fresh_dir L1084) in f250 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 10. |

Three of the fourteen are the `let _ = fs::remove_dir_all(..)` idiom in
`memory.rs`'s test helper, four the same idiom in `exec.rs`'s, four the same in
`registry.rs`'s, one is `.ok()` on a parse, and two are the `NotFound` arm of
`MemoryStore::load`. Every printed line was parsed into
`(how, event, qualname, line)` by the collector (**0** unparsed), and every
sink's file was resolved from the trace's own `events → code_objects` join
rather than from the sentence.

### 4.2 The E6‴-W adjudication — every SWALLOWED line, all three processes

`--workspace --lib` recorded three processes. Fourteen SWALLOWED lines came
from the `bloomery_daemon` lib binary (the primary, which §1's
`exceptions <run>` names); the sweep read the other two and both printed
**none**. The fourteen are the same five source shapes as §4.1 — the same
arms, on a second independent execution.

| # | Printed line | Sink `file:line` | log-and-continue? | Verdict (amended reading) | Reason, from the source |
|---|---|---|---|---|---|
| 1 | `SWALLOWED -- absorbed by sink_let_underscore at e385 (tests::fresh_dir L156) in f190, which returned ok` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | `let _ = std::fs::remove_dir_all(&dir);` — §4.1 row 1's line. |
| 2 | `… absorbed by arm_handled at e394 (MemoryStore::load L96) in f195 …` | `crates/bloomery-daemon/src/memory/store.rs:96` | **no** (empty body) | **TRUE** | The `NotFound` guard arm; `load` returns `Ok(MemoryStore { … })` — §4.1 row 3. |
| 3 | `… absorbed by sink_let_underscore at e419 (tests::tempdir L606) in f203 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | The exec tests' `tempdir` helper — §4.1 row 6. |
| 4 | `… at e424 (tests::tempdir L606) in f212 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 3. |
| 5 | `… at e425 (tests::fresh_dir L156) in f208 …` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | Same line as row 1. |
| 6 | `… at e426 (tests::tempdir L606) in f205 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 3. |
| 7 | `… absorbed by arm_handled at e439 (MemoryStore::load L96) in f224 …` | `crates/bloomery-daemon/src/memory/store.rs:96` | **no** (empty body) | **TRUE** | Same arm as row 2, a second test thread. |
| 8 | `… at e444 (tests::tempdir L606) in f220 …` | `crates/bloomery-daemon/src/task/exec.rs:606` | no (no binding) | **TRUE** | Same line as row 3. |
| 9 | `… at e445 (tests::fresh_dir L156) in f214 …` | `crates/bloomery-daemon/src/memory.rs:156` | no (no binding) | **TRUE** | Same line as row 1. |
| 10 | `… absorbed by sink_let_underscore at e485 (tests::fresh_dir L1084) in f237 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | The registry tests' `fresh_dir` helper — §4.1 row 10. |
| 11 | `… absorbed by sink_ok at e496 (classify_probe L379) in f246 …` | `crates/bloomery-daemon/src/task/registry.rs:379` | no (no binding) | **TRUE** | `.ok()` on the exit-code parse — §4.1 row 11. |
| 12 | `… at e523 (tests::fresh_dir L1084) in f255 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 10. |
| 13 | `… at e534 (tests::fresh_dir L1084) in f262 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 10. |
| 14 | `… at e535 (tests::fresh_dir L1084) in f266 …` | `crates/bloomery-daemon/src/task/registry.rs:1084` | no (no binding) | **TRUE** | Same line as row 10. |

**A deviation from §1's letter, in the safe direction, stated.** §1's method
says "`sensorium exceptions <run>`" — one run. `--workspace --lib` records one
process per lib test binary, and an arm the primary trace never saw is exactly
what E6‴-W exists to look at, so the command was run again on each of the
other two processes and the adjudication above is over the UNION. That can
only add lines to a "0 false accusations" endpoint, never remove them. It
added none: `bloomery_bench` printed `dispositions: ambiguous 4` and
`bloomery_substrate` `dispositions: ambiguous 3`, with no SWALLOWED line in
either.

### 4.3 The counts, both arms, both readings

§1 requires the count under the amended reading (the gate) and under the
strictest pre-lock reading, "so a reader who rejects the amendment can
re-derive the verdict".

| Arm | Reading | Count | Guarded arms (R15) | Verdict |
|---|---|---|---|---|
| E6‴-A | **The amended reading** (the GATE): a log-and-continue arm is a TRUE swallow | **0 false accusations of 14** | **2 of 14** (§4.1 rows 3, 5) | **PASS** |
| E6‴-A | **The strictest pre-lock reading**: every log-and-continue arm counted FALSE as well | **0 false accusations of 14** | **2 of 14** (§4.1 rows 3, 5) | **PASS** |
| E6‴-W | **The amended reading** (the GATE) | **0 false accusations of 14** | **2 of 14** (§4.2 rows 2, 7) | **PASS** |
| E6‴-W | **The strictest pre-lock reading** | **0 false accusations of 14** | **2 of 14** (§4.2 rows 2, 7) | **PASS** |

**The `guarded arms` column, added 2026-09-05 after the run**, on design R15
at `1770515` — committed after this run and requiring every acceptance table
to report the guarded-arm count beside both readings. It is **not a new
measurement**: it restates, in the table where a reader compares the two
readings, the number §5.2 below already published by hand — the SWALLOWED
lines whose `Err` binding is read ONLY by a match guard
(`Err(e) if e.kind() == io::ErrorKind::NotFound => { }`). Both counts are also
in `results.json` as `endpoints.<arm>.guarded_arms`, each carrying
`provenance: "hand adjudication, §5.2"`. No verdict, count or measured number
moved; under the letter-reading of §1's `&self`-predicate clause these are the
lines that would flip, which is exactly why R15 wants them visible here.

The two readings agree in both arms, and the record says why rather than
leaving it to be assumed: **none of the twenty-eight lines is a
log-and-continue arm.** Twenty-two have no binding at all (`let _ =`), two are
`.ok()` on a parse, and four are an arm whose body is *empty* — it neither
logs nor formats. The class the amendment was written for still does not occur
anywhere `--lib` reaches in this workspace; it is pinned by
`corpus/rust/logged_arm` instead, which E6-again exercised and passed. That is
a fact about bloomery, not a general one (§5.4).

### 4.4 The arm E6′ STOPped on, and what it does now

E6′ printed fifteen lines and one of them was false: row 6, `build_memory` at
`crates/bloomery-daemon/src/memory.rs:131`, whose `Err(e) =>` arm renders the
error into the `MemoryContext` it returns
(`disabled_reason: Some(format!("memory store unreadable: {e}"))`, beside
`store: None`). Under the R2 amendment that arm's `format!` PRODUCT escapes,
so the arm is `arm_ambiguous` and can never reach a SWALLOWED verdict.

Three independent facts of this run say it moved, and none of them is the
absence of a line:

* the prep build's own manifests classify `crates/bloomery-daemon/src/memory.rs:131`
  as `arm_ambiguous` (§3, "the blast radius");
* both arms EXECUTED that site — it is one of the two blast-radius arms this
  run reached, with one HANDLED event each (§4.5) — so the arm ran and was
  judged, rather than going unvisited;
* both arms' `dispositions:` line moved from E6′'s `swallowed 15, ambiguous 7`
  to `swallowed 14, ambiguous 8`: the line did not vanish, it changed class.

### 4.5 Executed versus static, the blast radius

§1 asks, of the 31 arms the clone census moved HANDLED → ESCAPED, "how many
this run actually EXECUTED against how many exist statically — an arm the run
never reaches is not evidence either way, and the record must say which number
is which".

| Number | Value | What it is |
|---|---|---|
| entries in the Task-8 reviewer's static list | **31** | as `t10-context.md` writes it |
| of them, carrying a line and so intersectable | **29** | the other two are named only as "two `codec_fixtures_*` tests" |
| located entries that resolve to an arm site in this build's manifests | **29 of 29** | 0 unmatched, 0 suffixes ambiguous |
| of those, classified `arm_ambiguous` by this build | **25 of 29** | the remaining 4 are `arm_propagate` and were never `arm_handled` — §5.5 |
| **EXECUTED by E6‴-A** | **2 of 29** | `task/registry.rs:293` (`contained`) and `memory.rs:131` (`build_memory`) |
| **EXECUTED by E6‴-W** | **2 of 29** | the same two |
| arm sites that fired at all, anywhere in the tree | **4** (A), **5** (W) | the whole tree, not only the blast radius |

E6′'s row-6 footnote said `-p bloomery-daemon --lib` "executed exactly one of
the blast-radius arms". Under this run's own instrument the number for that
same arm is **two**, and the widening to `--workspace --lib` does not change
it. §5.1 says why, and what would.

## 5. Gaps

### 5.1 The widening bought no reach, and the record should not be read as if it did

`--workspace --lib` cost two extra processes (`bloomery_bench`, 184 events;
`bloomery_substrate`, 35 events) and returned **0** further SWALLOWED lines
and **0** further blast-radius arms. Both arms executed the same 2 of the 29
located static arms; 27 were never reached by either.

The reason is structural, not accidental. `--lib` builds and runs lib test
targets only, so it excludes by construction:

* `crates/bloomery-daemon/src/bin/flywheel_tool.rs:383` — a **bin** crate root;
* the two `codec_fixtures_*` entries — **integration tests** under
  `crates/bloomery-daemon/tests/`;

and it reaches the remaining 28 located entries only if some lib unit test
drives that code path with an `Err`. Two do — `task/registry.rs:293` and
`memory.rs:131` — and 26 do not: 22 sit in daemon code (`drift.rs` 5,
`swap.rs` 1, `task/exec.rs` 7, `task/exec_run.rs` 1, `swap/job.rs` 5,
`drift/watch.rs` 3) whose failure paths this workspace exercises from
integration tests, 3 are `task/registry.rs`'s other arms (615, 643, 773), and
one is `crates/bloomery-substrate/src/llama.rs:406` — in the crate whose lib
tests DID run in E6‴-W (35 events, `dispositions: ambiguous 3`) without ever
reaching it.

So **"0 false accusations" is measured over the same two arms in both arms of
this run.** What it establishes is that the repair did not introduce a false
accusation anywhere `--lib` reaches, on 28 adjudicated lines. What it does not
establish is anything about the other 27 arms, and no reader should take
E6‴-W's PASS as evidence about them. The arm that would: `cargo sensorium test
--workspace` (no `--lib`), which builds and runs the bins and integration
tests as well. That is a wider arm than §1 pre-registered and it is not taken
here — a new arm chosen after the numbers are in is a re-roll.

### 5.2 §1's "merely observed" still does not settle a match guard — and this time the verdict turns on it

Rows 3 and 5 of §4.1 and rows 2 and 7 of §4.2
(`Err(e) if e.kind() == io::ErrorKind::NotFound => { }`) were adjudicated
**TRUE**, four lines in total. §1's wording admits another reading: "merely
observed" means "read by a `&self` predicate (`.is_err()`), or its value moved
out of the arm", and the guard's `e.kind()` *is* a `&self` read. Under that
letter-reading each arm reads **2 false accusations of 14** and **both
endpoints are a STOP**.

The rung-3 acceptance recorded the same disagreement (its §5.2) at a point
where the verdict was a STOP either way. Here it is not, so the three reasons
the Task-8 reviewer gave for the TRUE reading are what the PASS rests on, and
they are repeated rather than referred to:

1. **The amendment's own stated criterion is "the failure never reached the
   caller."** `MemoryStore::load` returns `Ok(MemoryStore { … })` on this arm —
   an empty store, `parse_errors: 0` — so no caller can tell a `NotFound`
   occurred.
2. **The same amendment declares `eprintln!("{e:?}")` a TRUE swallow**, and
   that is also only a shared-borrow read of `e`. "Read by a `&self`
   predicate" therefore cannot mean "any shared-borrow read", or the sentence
   contradicts itself.
3. **The `.is_err()` example points at a shape design R2 never probes at
   all.** `.is_err()`/`.is_ok()` take `&self` and are not sinks, so an arm
   reached through one can never be accused; the example cannot be the general
   rule, because under the general rule it would name a shape that cannot
   occur.

A fourth observation, this run's own: a guard's boolean is consumed by the
`match` itself and produces nothing the caller can read, where `.is_err()`'s
result is precisely the value the surrounding code acts on. **This is a
wording debt on §1, not a measurement question**, and it should be settled
before rung 4 rather than inherited: the endpoint as written is not
self-consistent, and a reader who takes it literally reads this run as a STOP.

### 5.3 A residual false-accusation generator of the amended class, with zero exposure here

A value-format macro nested inside a logging macro's argument —
`eprintln!("{}", keep(format!("{e}")))` — still reads HANDLED, because the
logging family's exemption reads the top-level arguments and the escape is one
level down. It is the same class the R2 amendment was written for, reached
through a nesting the amendment does not name.

Exposure on this tree is **zero**, and that was checked rather than assumed
(Task 10, fix round 1: the clone contains no such nesting, and no `anyhow!`,
`bail!`, `format_err!` or `ensure!` at all). So this run could not have
falsified it and does not. It is a live hole on any workspace that writes that
shape, and it is deferred to the design authority rather than repaired after
the numbers were read.

### 5.4 A low SWALLOWED volume is not evidence the rule works

`tracing`-style field syntax (`err = ?e`, `error = %e`) mentions the bound name
as a token, so it escapes unconditionally under the current rule: **no
log-and-continue arm can read SWALLOWED on a workspace that logs that way.**
On such a tree E6‴-W's headline would be a small number for a reason that has
nothing to do with the classifier being right.

The clone's exposure to that shape is also zero — which is why §4.3 could
report that none of the twenty-eight lines is a log-and-continue arm. Both
facts point the same way: **the amended class is pinned by
`corpus/rust/logged_arm` and by nothing on this tree**, and the two arms'
zeros are evidence about false accusations, not about the amendment's own
class.

### 5.5 The reviewer's static list and the census's 31 are not the same set

Task 10's census measured **31** arms moving HANDLED → ESCAPED. The Task-8
reviewer's list enumerates **31** entries. They are not the same 31, and this
run can say so from the manifests:

* 4 of the 29 located entries (`swap/job.rs` 250, 266, 282 and
  `drift/watch.rs:381`) are classified **`arm_propagate`**, not
  `arm_ambiguous`. The classifier tests an `Err(..)` tail FIRST (Task 10, fix
  round 1, row 9), so these were `arm_propagate` before the amendment too:
  they never were `arm_handled` and never moved.
* 2 entries are unlocated (`codec_fixtures_*`, no line given) and cannot be
  intersected at all.

So at most **25 + 2 = 27** of the reviewer's entries can be among the census's
31, and at least 4 of the 31 that moved are arms the reviewer's list does not
name. The gap Task 10 flagged as "31 vs ~32, unexplained" is therefore not one
number against another — it is two different sets, and neither instrument was
tuned toward the other. Identifying the census's 31 exactly would need a
BEFORE/AFTER manifest diff across the repair commit, which this run did not
take.

### 5.6 The prep build corroborates the census from a second instrument

Reported without a gate, and worth stating because it was not designed as a
check: the from-scratch `--workspace --no-run` build's own manifests declare
**225** distinct `kind: "arm"` sites, `{arm_ambiguous 121, arm_handled 65,
arm_propagate 39}`. Task 10's census binary, a different program reading the
same tree, reported **arm sites 225, escaped 121, handled 65, propagate 39**
after the repair. The two agree exactly. §1's frozen census is cited by this
document, never re-derived, and this agreement is corroboration rather than a
re-measurement.

### 5.7 What this run did not measure

* **Nothing was dropped.** Every `{value, n, lens, dropped}` cell in
  `results.json` has an empty `dropped` list and a non-null value, except the
  two that are null by design: `endpoints.E6pppA.headline` and
  `endpoints.E6pppW.headline`, each `dropped = ["adjudicated by hand in §4 …
  under both the amended reading (the gate) and the strictest pre-lock reading
  of \"merely observed\""]`. No program can adjudicate a SWALLOWED line
  against the clone's source, so the schema publishes the lines and refuses to
  publish a count it did not compute. The counts are §4.3.
* **E2″, E3″, E5″, E0″ and E1″ were not re-run.** §1 pre-registers four
  endpoints and this run took exactly those four; the rung-3 record of
  2026-09-04 stands as written for the rest.
* **The target was not warm at the start.** §1's lens says "warm target
  (stated)", and it is stated here: the run opened with a from-scratch
  `--workspace --no-run` PREP build that emptied the target (6 090 542 658
  bytes) and rebuilt it in 9.351 s. Two reasons, both about honesty rather
  than speed — cargo never hands a fingerprint-fresh unit to the wrapper, so a
  warm target could have run test binaries an OLDER transformer emitted, and
  only a build that compiles every unit leaves a complete manifest set for
  §4.5's blast radius. Both measured arms then ran against the warm target
  that build left.
* **The two `codec_fixtures_*` entries were never located.** They carry no
  line in the reviewer's list and nine files in the clone match the pattern.
  They are counted as unlocated in every table and matched by nothing.
* **The census was not re-run.** §1 froze it before the lock; this document
  cites those numbers and §5.6 reports the manifests' independent agreement.

### 5.8 The driver's provenance, corroborated after the run

**Recorded 2026-09-05, after the run.** §1's lens says the driver is "built
`--release` from this branch's HEAD at run time (commit + sha256 recorded)".
This run evidenced that with the binary's existence and sha256
(`0ce80ad5aa88…`, unchanged across the run and after both commits) and with
cargo's own report that every unit was Fresh — which is a claim about the
operator's `cargo build`, not a fact the runner produced. The reviewer's
independent corroboration, from mtimes on this box, is therefore recorded
here rather than left implicit:

| Fact | Value |
|---|---|
| driver binary mtime | 2026-09-05T01:48:00.339-0500 |
| newest driver-source mtime | 2026-09-05T01:47:16.900-0500 (`rust/sensorium-transform/src/arms.rs`; `escape.rs` 01:47:16.897) |
| gap | **43.4 s** — the binary is younger than the last edit to the transformer |
| the commit those bytes became | `321e204` (`fix(transform): every non-logging macro's literals are scanned for a bound Err name`), authored 01:49:22, i.e. after the build |

So the measured binary contains the literal-scan fix of fix round 1, and not
an earlier transformer. This is corroboration of a lens claim, not a
measurement: nothing in §3 or §4 depends on it, and it could only ever have
falsified the run, never changed a number in it.

The instrument no longer needs the corroboration. `acceptance_e6ppp.py` now
runs `cargo build --release -p cargo-sensorium` itself before the preflight
and records `built_from` — the repo HEAD at build time, cargo's exit code, and
the driver's sha256 before and after, with a non-zero exit REFUSING the run.
This run predates that, so `environment.built_from` in `results.json` is
`null` with exactly that reason; runs from this commit onward carry the fact
instead of the argument.

### 5.9 Row 11 is a true swallow that a reader may reasonably want to whitelist

`classify_probe` at `crates/bloomery-daemon/src/task/registry.rs:379` —
`.and_then(\|i\| obs.outcome[i + " exit ".len()..].parse::<i64>().ok())`, with a
deliberate `_ => "inconclusive"` fallback and a comment saying so — is the one
accusation in this record a bloomery author is most likely to contest, and it
is worth naming plainly: it IS a true swallow under §1, R2 and R8 (`.ok()` is
a written sink, the `ParseIntError` reaches no caller, and the frame returned
ok), *and* it is deliberate, documented, correct code whose author would
reasonably want the tool to stop mentioning it. Those two facts are not in
tension — the disposition is about where the failure went, not about whether
the code is right — but a tool that cannot be told the difference will be
argued with. A per-site `--allow` (or an in-source marker) is the shape that
would settle it; it is CARRIED-DEBT for the docs task, not a change to this
record or to any rule measured here.
