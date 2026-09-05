# Rung-4 entry acceptance, the grain of exceptions — H1–H6

The record of whether `exceptions`, now printing one block per SHAPE and
answering for a whole `cargo sensorium test` invocation, reproduces the
answers the rung-3 borrow-repair record already published — line for line,
site for site, tally for tally.

**Nothing here measures a program.** This slice changes what the reader
PRINTS and changes no crate (`cargo-sensorium` stays 0.3.1), so its question
is a question about output. The ORACLE is the PUBLISHED E6⁗ record,
`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json` at
`605db64` — its per-site tables, its 288 per-process tally lines and its
per-process swallow counts, measured on 2026-09-05, read here and **never
re-measured**. What is re-run is the reader, over the trace stores that
record cites.

**The kept stores are the INPUTS.** The three directories under
`/mnt/extra/sensorium-rung2/sensorium-dir/e6q` (`a`, `ws`, `ws0`) hold the
1 + 144 + 144 traces the E6⁗ arms recorded, and this run only reads them: no arm is recorded, no cargo command is run against the
clone, no target is emptied. Read-only means the traces. Every `sensorium`
call appends one audit row to the store's `invocations.jsonl` — a sibling of
`traces/` that `runs` and `find_trace` do not read, written by `cli.main` for
every invocation and unavoidable short of `SENSORIUM_NO_INVOCATION_LOG=1`,
which the E6⁗ protocol did not set either. The `traces/*.db` are counted and
their bytes summed before and after, and the audit rows this run added are
reported in §2, so the record states the one write it causes rather than
claiming a purity it does not have.

**§1 is byte-locked.** It is committed ALONE, after the definition, the
grouping, the invocation mode, their tests and the acceptance instrument, but
before any number below has been read, and it is design §4's pre-registration table carried verbatim
— with two substitutions a reader can check in one place: `err_stored`'s pin
line is named as the rulings shipped it (R-G4 as amended by R-G6), and the
ungated vary-line count names the four spellings R-G3/R-G5/R-G6 settled. The
runner refuses to run if this section differs from the commit that locked it
— compared with `awk '/^## 1/,/^## 2/'`, the sha recorded in §2 — and refuses
outright while no lock sha is set. §1 is not amended: there is one sha and no
dated note inside it. A completed measurement is never re-rolled, and a miss
is a STOP with its number.

## 1. Pre-registration

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| H1 | Did the definition or the grouping move a corpus verdict? | E6's collector over every `corpus/rust/*` case with an `exceptions` question (20), fresh corpus target, the 0.8.1 driver (crates unchanged). The pins updated by rule are listed here: `err_stored` and `err_rendered_into_value` (N2, the sentence), vector `v18` (N2), vector `v17` and `tests/test_exceptions_rust_gate.py` (N5, the continuation note), and `err_stored` again (N3/N4: its retry arm's two chains are one shape — the second head is no longer printed; the bracket `[×2: e4, e8]` and the line `messages: 2 distinct (first shown)` are pinned instead, and `origins:` is pinned ABSENT — R-G4 as amended by R-G6, which moved one site raising two different errors off the `origins:` label and onto `messages:`). | **20 of 20 equal** (swallow sets, tallies, and every pinned line). | Parent §8 E6, unchanged. |
| H2 | Does the grouped view reproduce the A record at the site grain? | `exceptions 20260905-091115-5da3dc` on the kept `a` store. | **Exactly 5 SWALLOWED groups**, counts `memory.rs:156 ×3, task/exec.rs:606 ×4, memory/store.rs:96 ×2, task/registry.rs:1084 ×4, task/registry.rs:379 ×1`; tally line byte-identical to the record's (`dispositions: swallowed 14, ambiguous 8`). | E6‴/E6⁗ §4.1's five shapes. |
| H3 | Does grouping change any per-process TALLY? | `exceptions <run>` on each of the 144 `ws` traces and each of the 144 `ws0` traces. | **Every tally line byte-identical** to the record's per-process `tally_line` (114 + 114 processes with chains; the 30 + 30 without print `no exceptions recorded`), and per trace the sum of SWALLOWED group counts == the record's `swallowed_count`. | N5: the tally counts chains. |
| H4 | Does the invocation view reproduce the record's per-site table? | `exceptions 20260905-091115-9e8e5a` on `ws`, and the `ws0` invocation likewise. | **ws: 91 SWALLOWED groups whose (site, count) multiset equals the record's 91-row table, summing to 782; tally `swallowed 782, ambiguous 330, panicked 2`; header counts 144 / 114 / 30; INCOMPLETE members 0. ws0: 98 groups summing to 812; tally `swallowed 812, ambiguous 300, panicked 2`.** | The record's §4.2/§4.3 tables and the summed per-process tallies (derived from `results.json` before this design was written: 114 tally lines per arm). |
| H5 | Is the invocation view usable? | Wall of H4's two commands, 60 s kill armed. | **Both under 60 s.** | E0's rule; 144 opens at ≈0.07 s each ≈ 10 s. |
| H6 | Did anything else move? | The whole Python suite (vectors v01–v19, the Python corpus, `tests/test_exceptions*.py`) and the Rust workspace tests. | **Python `exceptions` output byte-identical to 0.8.1** (the suite is the pin; no Python expectation changes); Rust workspace green; v17's single-shape blocks byte-identical. | N7. |

**Lens for every endpoint**: the reader is this repository's `.venv` Python
running `python -m sensorium` at the branch HEAD §2 records (Python and
`sensorium` versions in §2). The driver is `cargo-sensorium` **0.3.1** — the
binary already built under `/mnt/extra/sensorium-rung2/rust-target`, which
this slice does not change and this runner does **not rebuild**; its sha256 is
recorded in §2 before and after, and H1 is the only phase that runs it. The
inputs are the three kept stores
`/mnt/extra/sensorium-rung2/sensorium-dir/e6q/{a,ws,ws0}` — 1, 144 and 144
traces; the A run is `20260905-091115-5da3dc`, the `ws` invocation
`20260905-091115-9e8e5a` and the `ws0` invocation `20260905-091209-bfa73c`,
each asserted in the preflight against a member trace's own `meta` — and the
oracle is the committed `2026-09-05-sensorium-rung3-e6q.results.json` at
`605db64`, whose sha256 §2 records. H1 records into a **fresh** corpus target
and a **new, empty** `SENSORIUM_DIR`; the collector gives each case its own
`<workdir>/.sensorium`, so that directory stays empty and §2 says whether it
did. Nothing is gated on a wall except H5, whose 60 s kill is ARMED and whose
firing is a STOP, not an exception. Launched detached (`setsid nohup`), with a
`grain.DONE`/`.FAILED` marker carrying `exit=<n>`; nothing is read before the
marker exists. Every measurement is `{value, n, lens, dropped}`: a `null`
value with a reason is the only not-measured, `0` is measured-and-zero, and
**no endpoint is ever filled from the oracle** — the record is already in the
room, and a headline that borrowed from it could not fail.

**The pins updated BY RULE before this section was locked.** H1's "20 of 20
equal" is stated against these, not against the 0.8.1 pins:
`corpus/rust/err_stored/questions.yaml` (N2's sentence, and the N3/N4 grain
under R-G4/R-G6 — the bracket `[×2: e4, e8]`, `messages: 2 distinct (first
shown)`, `origins:` absent, `expect_count` 1);
`corpus/rust/err_rendered_into_value/questions.yaml` (N2's sentence);
`docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json` (N2's
sentence); `docs/trace-format/vectors/v17-exceptions-rust-swallowed.json`
(N5's continuation note, now `--limit 2`); and
`tests/test_exceptions_rust_gate.py` (N5's continuation note, now
`--limit 5`). Each was moved by the rule the design states and by nothing
else, and each is named here before any number below exists.

Reported without a gate: output lines and bytes for the busiest `ws`
process before (0.8.1) and after; the 144 concatenated per-process outputs
versus the one invocation view; the number of groups whose `origins vary` /
`details vary` / `hops vary` line printed (an honesty count, not a gate) —
the shipped spellings, after rulings R-G3, R-G5 and R-G6, are `origins:` /
`messages:` / `details vary` / `routes:`, and all four are counted.

## 2. Environment

Measured 2026-09-05T18:04:58-0500 → 2026-09-05T18:07:10-0500 by `rust/tests/acceptance_grain.py`, launched detached; the raw facts it recorded are `results-grain-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-05-sensorium-rung4-entry-grain.results.json`, which `acceptance_grain_schema.assemble_grain` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless the locked range is byte-identical to the commit that locked it — and refuses outright while no lock sha is set. The range is awk '/^## 1/,/^## 2/' PLUS the definition of every footnote §1 references — here §1 references no footnote (`footnotes_in_range` = none), so the extended range and `awk '/^## 1/,/^## 2/'` are the same bytes. Checked at `05c3124`: 5807 bytes, sha256 `bdb9089249e6767738fbd1c6f1fbbe20168d6f0fbf68c4f3f9ca90a73d8bea52` on both sides — identical: yes. §1 was committed ALONE and never amended: there is no second sha (`original_lock` = None).

**The oracle.** `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json` at `605db64` (sha256 `7d1f10e51e8c3cf92e9deaf9b5e9d24f823ac4bd8bb7d045d7474b4ce6696588`) — sites {'a': 5, 'ws': 91, 'ws0': 98}, lines {'a': 14, 'ws': 782, 'ws0': 812}, processes with a tally line {'a': 1, 'ws': 114, 'ws0': 114}, without one {'a': 0, 'ws': 30, 'ws0': 30}. read from the committed record; nothing here was measured by this run, and no endpoint above is filled from it

| Pin | Value |
|---|---|
| repo HEAD at the run | `d699b4c24c9b1807c102cdc0aa04878678cf5f67` (branch `feat/rung4-entry-grain`) |
| driver (H1 only; NOT rebuilt by this run) | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` 0.3.1, mtime 2026-09-05T12:29:32-0500; rebuilt: no |
| driver sha256 | `50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f` — unchanged across the run: yes |
| kept trace stores (the INPUTS) | `/mnt/extra/sensorium-rung2/sensorium-dir/e6q`/{a,ws,ws0}; traces before a 1, ws 144, ws0 144; after a 1, ws 144, ws0 144; `traces/*.db` unchanged: yes |
| invocation ids the stores carry | ws `20260905-091115-9e8e5a`, ws0 `20260905-091209-bfa73c` |
| the one write this run causes | the kept stores' `traces/*.db` are INPUTS and are never written; every CLI call appends one audit row to the store's `invocations.jsonl`, a sibling of `traces/` that `runs` and `find_trace` do not read, and the counts before and after are both recorded — rows added: {'a': 1, 'ws': 145, 'ws0': 145} |
| fresh trace directory (H1's, which stays empty) | `/mnt/extra/sensorium-rung2/sensorium-dir/grain`; traces in it afterwards: 0 |
| corpus target (H1) — FRESH for this run | `/mnt/extra/sensorium-rung2/corpus-target-grain`, 255836621 bytes afterwards |
| Rust workspace target (H6's `cargo test`) | `/mnt/extra/sensorium-rung2/rust-target` |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| repo porcelain before / after | empty / empty |
| 1-minute load at the start | 0.47 |
| disk free on the repo's filesystem, before / after | 12.9 GB / 12.89 GB |

**Log locations.** Every command's log is under `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/acceptance-grain/logs`, one subdirectory per phase (`h2`, `h3-ws`, `h3-ws0`, `h4-ws`, `h4-ws0`, `h1`, `h6`).

1-minute load at each phase's start: H2 0.47, H3 0.47, H4 0.56, H1 0.56, H6 0.82.

**The driver was current before the launch, and the runner did not touch
it.** §1 pins `cargo-sensorium` 0.3.1, the binary already built under
`/mnt/extra/sensorium-rung2/rust-target`, and the runner does not rebuild it
— but H6 runs `cargo test --workspace` in that same target, which would
relink a stale driver in the middle of the run and leave the sha recorded
before the run different from the one recorded after. So `cargo build -p
cargo-sensorium` was run in `rust/` against that target BEFORE the launch, by
hand: it compiled nothing (`Finished dev profile in 0.11s`) and the sha256
did not move. The binary carries the string `cargo-sensorium 0.3.1`, and §2's
before-and-after shas are the same value, as is the sha H6 recorded after
`cargo test --workspace` (§4.6). No step of the measurement built anything.

**`SENSORIUM_NO_INVOCATION_LOG` was deliberately not set**, so the audit rows
this run added are reported above rather than engineered away. Setting it
could not have worked in any case: `acceptance_lib.plain_env()` strips every
`SENSORIUM_*` from each child's environment before the CLI sees it. The E6⁗
protocol that produced the oracle did not set it either.

## 3. Results

Every measurement is `{value, n, lens, dropped}`; a `null` value with a reason is the ONLY not-measured, and `0` is measured-and-zero. Rendered by `rust/tests/render_grain.py` from `2026-09-05-sensorium-rung4-entry-grain.results.json`. No verdict is decided here — §4 is.

| Id | Headline | n | Lens (abridged) | Dropped |
|---|---|---|---|---|
| H1 | 0 (rule: 20 of 20 equal (swallow sets, tallies, every pinned line)) | 20 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| H2 | 0 (rule: exactly 5 SWALLOWED groups at the record's five sites; 0 differences; the tally line byte-identical) | 5 | site-table differences (missing + extra + count diffs), of the record's sites; `sensorium exceptions <the A ru… | none |
| H3 | 0 (rule: every tally line byte-identical and every swallow count equal — 0 of 288) | 288 | per-process comparisons that differ (a tally line or a swallow count), of the comparisons made; `sensorium exc… | none |
| H4 | 8 (rule: the record's per-site tables reproduced — 0 differences; the summed tallies equal; header counts 144 / 114 / 30) | 2 | site-table differences summed over both invocation answers; compared against the PUBLISHED E6⁗ record (`docs/s… | none |
| H5 | 0.53 (rule: both answers under 60 s) | 2 | the SLOWEST of the two answers, seconds, of the arms timed; wall of H4's two `exceptions <invocation-id>` comm… | none |
| H6 | 0 (rule: the Python suite green and byte-identical expectations; the Rust workspace green) | None | `pytest -q` exit status -- 0 is green; the whole Python suite from the repo root under `plain_env()` plus `SEN… | none |

### H2 — the grouped view of the A run, at the site grain

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| site-table differences (the gate) | 0 | 5 | site-table differences (missing + extra + count diffs), of the record's sites; `sensorium exceptions <the A ru… | none |
| SWALLOWED groups printed | 5 | 14 | SWALLOWED groups printed, of the chains they account for -- §1 predicts 5 groups over 14 chains | none |
| chains those groups account for | 14 | 14 | chains the groups account for, of the record's SWALLOWED lines; `sensorium exceptions <the A run> --limit 1000… | none |
| the tally line is the record's | True | None | the printed `dispositions:` line is byte-identical to the record's for this process | none |
| sinks the join could not resolve | 0 | 5 | SWALLOWED groups whose sink event the trace does not hold -- anything but 0 is a hole in the comparison, not a… | none |

Command: `sensorium exceptions 20260905-091115-5da3dc --limit 100000` on run `20260905-091115-5da3dc` (exit 0, 0.041 s, 4701 bytes over 41 lines).  
Printed tally: `dispositions: swallowed 14, ambiguous 8`; the record's: `dispositions: swallowed 14, ambiguous 8`.  
Vary lines printed, by kind: `{'messages': 2}`.

The five shapes, as measured:

| sink | chains |
|---|---|
| `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory.rs:156` | 3 |
| `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/memory/store.rs:96` | 2 |
| `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/exec.rs:606` | 4 |
| `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:1084` | 4 |
| `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs:379` | 1 |

### H3 — every process of `ws` and `ws0`, one question each

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| per-process comparisons that differ (the gate) | 0 | 288 | per-process comparisons that differ (a tally line or a swallow count), of the comparisons made; `sensorium exc… | none |
| comparisons made | 288 | None | processes read, over both arms | none |
| `ws`: processes read | 144 | None | traces read in the kept `ws` store | none |
| `ws`: tally lines that are not the record's | 0 | 144 | processes whose printed `dispositions:` line is not the record's (or which did not print the empty-answer shap… | none |
| `ws`: swallow counts that are not the record's | 0 | 144 | processes where the SWALLOWED groups' chains do not sum to the record's `swallowed_count`; `sensorium exceptio… | none |
| `ws`: chains over this arm | 782 | 168 | chains over this arm, of the groups they were printed as | none |
| `ws0`: processes read | 144 | None | traces read in the kept `ws0` store | none |
| `ws0`: tally lines that are not the record's | 0 | 144 | processes whose printed `dispositions:` line is not the record's (or which did not print the empty-answer shap… | none |
| `ws0`: swallow counts that are not the record's | 0 | 144 | processes where the SWALLOWED groups' chains do not sum to the record's `swallowed_count`; `sensorium exceptio… | none |
| `ws0`: chains over this arm | 812 | 177 | chains over this arm, of the groups they were printed as | none |

`ws`: runs only in the store `[]`, only in the record `[]`; total output 182334 bytes over 1634 lines; vary lines `{'origins': 8, 'messages': 37, 'routes': 8}`.  
`ws0`: runs only in the store `[]`, only in the record `[]`; total output 179431 bytes over 1615 lines; vary lines `{'origins': 8, 'messages': 36, 'routes': 8}`.  

### H4 — the invocation view against the record's per-site tables

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| site-table differences over both arms (the gate) | 8 | 2 | site-table differences summed over both invocation answers; compared against the PUBLISHED E6⁗ record (`docs/s… | none |
| `ws`: site-table differences | 4 | 91 | missing + extra + count diffs against the record's per-site table, of its sites; `sensorium exceptions <the ws… | none |
| `ws`: merged SWALLOWED groups | 100 | 91 | merged SWALLOWED groups printed, of the record's sites; `sensorium exceptions <the ws invocation id> --limit 1… | none |
| `ws`: chains they account for | 782 | 782 | chains the groups account for, of the record's SWALLOWED lines; `sensorium exceptions <the ws invocation id> -… | none |
| `ws`: the summed tally is the record's | True | None | the printed `dispositions:` counts equal the record's SUM over its per-process tally lines; `sensorium excepti… | none |
| `ws`: the header's counts are the record's | True | 144 | the header's `N processes, k with Err chains, m with none` against the record's process count, its processes W… | none |
| `ws`: members named INCOMPLETE | 0 | 144 | members the answer named INCOMPLETE, of the members | none |
| `ws`: sinks the join could not resolve | 0 | 100 | groups whose sink event the named trace does not hold -- a hole, not a difference | none |
| `ws0`: site-table differences | 4 | 98 | missing + extra + count diffs against the record's per-site table, of its sites; `sensorium exceptions <the ws… | none |
| `ws0`: merged SWALLOWED groups | 103 | 98 | merged SWALLOWED groups printed, of the record's sites; `sensorium exceptions <the ws0 invocation id> --limit … | none |
| `ws0`: chains they account for | 812 | 812 | chains the groups account for, of the record's SWALLOWED lines; `sensorium exceptions <the ws0 invocation id> … | none |
| `ws0`: the summed tally is the record's | True | None | the printed `dispositions:` counts equal the record's SUM over its per-process tally lines; `sensorium excepti… | none |
| `ws0`: the header's counts are the record's | True | 144 | the header's `N processes, k with Err chains, m with none` against the record's process count, its processes W… | none |
| `ws0`: members named INCOMPLETE | 0 | 144 | members the answer named INCOMPLETE, of the members | none |
| `ws0`: sinks the join could not resolve | 0 | 103 | groups whose sink event the named trace does not hold -- a hole, not a difference | none |

`ws`: `sensorium exceptions 20260905-091115-9e8e5a --limit 100000` (exit 0, 0.53 s, 128167 bytes over 927 lines).  
`ws` header: `144 processes, 114 with Err chains, 30 with none`; tally `{'swallowed': 782, 'panicked': 2, 'ambiguous': 330}` against the record's summed `{'swallowed': 782, 'ambiguous': 330, 'panicked': 2}`; vary lines `{'messages': 39, 'origins': 11, 'routes': 11}`.  
`ws0`: `sensorium exceptions 20260905-091209-bfa73c --limit 100000` (exit 0, 0.515 s, 125820 bytes over 910 lines).  
`ws0` header: `144 processes, 114 with Err chains, 30 with none`; tally `{'swallowed': 812, 'panicked': 2, 'ambiguous': 300}` against the record's summed `{'swallowed': 812, 'ambiguous': 300, 'panicked': 2}`; vary lines `{'origins': 11, 'messages': 38, 'routes': 11}`.  

### H5 — is the invocation view usable?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| the slower of the two answers, s | 0.53 | 2 | the SLOWEST of the two answers, seconds, of the arms timed; wall of H4's two `exceptions <invocation-id>` comm… | none |
| walls, per arm | {'ws': 0.53, 'ws0': 0.515} | 2 | wall of H4's two `exceptions <invocation-id>` commands, 60 s kill ARMED; a kill is recorded as a kill, never r… | none |
| arms the 60 s kill fired on | 0 | 2 | arms the 60 s kill fired on -- any is a STOP on H5 | none |

### H6 — did anything else move?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| `pytest -q` exit status (the gate) | 0 | None | `pytest -q` exit status -- 0 is green; the whole Python suite from the repo root under `plain_env()` plus `SEN… | none |
| the suite's summary line | 1276 passed, 1 skipped in 85.99s (0:01:25) | None | the suite's own summary line, recorded whole | none |
| `cargo test --workspace` exit status | 0 | 38 | `cargo test --workspace` exit status, of its `test result:` lines | none |

`cargo test` results: `['test result: ok. 238 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.04s', 'test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.28s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.18s', 'test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.76s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.27s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 65 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s', 'test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 28 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.11s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.04s', 'test result: ok. 38 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.10s', 'test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.54s', 'test result: ok. 0 passed; 0 failed; 7 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 12 ignored; 0 measured; 0 filtered out; finished in 0.00s']`; the driver's sha256 afterwards `50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f`.  
Python logs `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/acceptance-grain/logs/h6/h6-pytest.log`; cargo logs `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/acceptance-grain/logs/h6/h6-cargo.log`; the only variables set for the suite: `['PYTHONDONTWRITEBYTECODE', 'SENSORIUM_CARGO_SENSORIUM']`.


### H1 — the corpus, against the pins updated BY RULE

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| printed SWALLOWED lines no registered group claims (false accusations) | 0 | 20 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| registered SWALLOWED groups with no printed line | 0 | 20 | registered SWALLOWED groups with no printed line; every `corpus/rust/*` case with an `exceptions` question, co… | none |
| questions whose swallow SET is not equal | 0 | 20 | questions whose printed swallow set is not EQUAL to the registered one (count, and a perfect matching both way… | none |
| questions whose `dispositions:` tally is not equal | 0 | 20 | questions whose printed `dispositions:` line differs from the registered whole line (or which printed one wher… | none |
| swallow cases that printed an empty set | 0 | 20 | questions registering a non-empty swallow set that printed no SWALLOWED line | none |
| the corpus's own (substring) reading's failures | 0 | 20 | the CORPUS's own reading of the same output (`run_corpus.check_question`: substring, not equality) -- reported… | none |

| Case | Question | SWALLOWED printed / registered | Set equal | Printed tally | Registered tally | Tally equal |
|---|---|---|---|---|---|---|
| `rust/abort` | `did-the-dying-child-drop-an-error` | 0 / 0 | yes | `(none printed)` | `(none registered)` | yes |
| `rust/cleanup_then_fail` | `was-the-cleanup-error-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/closure_try` | `what-did-the-question-mark-in-the-closure-return-from` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/dependency_swallow` | `did-the-cleanup-actually-work` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/err_arms` | `what-did-each-arm-do-with-its-error` | 1 / 1 | yes | `dispositions: swallowed 1, panicked 1, returned-to-harness 1` | `dispositions: swallowed 1, panicked 1, returned-to-harness 1` | yes |
| `rust/err_borrowed_into_value` | `was-the-open-failure-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 1` | `dispositions: ambiguous 1` | yes |
| `rust/err_propagation` | `how-many-failures-were-there` | 0 / 0 | yes | `dispositions: returned-to-harness 1` | `dispositions: returned-to-harness 1` | yes |
| `rust/err_rendered_into_value` | `was-the-unreadable-settings-error-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 1` | `dispositions: ambiguous 1` | yes |
| `rust/err_stored` | `were-the-retry-failures-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/interleaved_chains` | `was-either-failure-swallowed` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/join_handle` | `what-happened-to-the-workers-error` | 1 / 1 | yes | `dispositions: swallowed 1, ambiguous 1` | `dispositions: swallowed 1, ambiguous 1` | yes |
| `rust/keep_first_error` | `which-error-was-swallowed-and-which-way-did-it-travel` | 1 / 1 | yes | `dispositions: swallowed 1, ambiguous 1` | `dispositions: swallowed 1, ambiguous 1` | yes |
| `rust/logged_arm` | `was-the-refused-attempt-swallowed` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/macro_arg_partial` | `is-the-list-of-errors-complete` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/none_propagation` | `was-there-an-error-behind-the-panic` | 0 / 0 | yes | `(none printed)` | `(none registered)` | yes |
| `rust/outcome_generic` | `does-the-chain-follow-the-error-through-the-generic-frame` | 0 / 0 | yes | `dispositions: ambiguous 2` | `dispositions: ambiguous 2` | yes |
| `rust/panic` | `what-did-the-catch-do-with-the-panic` | 1 / 1 | yes | `dispositions: swallowed 1` | `dispositions: swallowed 1` | yes |
| `rust/returned_to_harness` | `where-did-the-error-the-harness-printed-come-from` | 0 / 0 | yes | `dispositions: returned-to-harness 1` | `dispositions: returned-to-harness 1` | yes |
| `rust/silent_swallow` | `which-settings-were-dropped` | 2 / 2 | yes | `dispositions: swallowed 2` | `dispositions: swallowed 2` | yes |
| `rust/unwrap_panic` | `what-happened-to-the-refusal` | 0 / 0 | yes | `dispositions: panicked 1` | `dispositions: panicked 1` | yes |

### Reported without a gate

**The busiest `ws` process** (`20260905-091125-fc7302`): 20166 bytes under 0.8.1 → 3360 bytes over 32 lines under 0.8.2, printed as 3 groups accounting for 54 chains (54 SWALLOWED lines in the record). the 0.8.1 bytes and swallow count are the E6⁗ record's `sweep_processes[]` row for this run, read and never re-measured -- 0.8.1 is not installed here; the record carries no LINE count for it, so that half is absent rather than derived

**144 per-process answers versus one invocation answer**: 182334 bytes over 1634 lines, against 128167 bytes over 927 lines. both halves measured by THIS run, under 0.8.2

**Vary lines that fired, by kind** (an honesty count, not a gate): `{'messages': 152, 'origins': 38, 'routes': 38}` — summed over every answer this run read: H2, H3/ws, H3/ws0, H4/ws, H4/ws0. blocks that printed a vary line, summed over EVERY answer this run read and named in `vary_counted_over` (H2, H3/ws, H3/ws0, H4/ws, H4/ws0); an honesty count, not a gate


## 4. Verdicts

Written by hand against §1's rules, from the raw record
(`results-grain-raw.json` and the logs beside it in the gitignored plan
ledger). One row per §1 endpoint, with the number that decided it. The run
was launched detached and measured ONCE; nothing was re-run, re-scoped or
re-classified after a number was read, and §1 was not touched — its sha256 is
`bdb9089249e6767738fbd1c6f1fbbe20168d6f0fbf68c4f3f9ca90a73d8bea52` before and
after (§2).

**One launch of this runner did not measure anything, and it is not this
one.** The first detached launch (2026-09-05T17:59:23-0500) died fourteen
seconds in, inside H2, on `NameError: name 'LOGS' is not defined` — after the
byte-lock, the preflight and the oracle read, and **before one `exceptions`
answer was asked for or one oracle comparison was printed**. That is
infrastructure, not a result: the plumbing was fixed and committed alone
(`d699b4c`, §5.5), the fresh locations were emptied, and the run below
started from zero. No number below was read twice, and none was read at all
before that commit.

| Id | §1's rule, verbatim | What was measured | Verdict |
|---|---|---|---|
| H1 | "**20 of 20 equal** (swallow sets, tallies, and every pinned line)." | **20** `corpus/rust/*` cases with an `exceptions` question, each recorded once under the 0.3.1 driver into a corpus target that was 0 bytes at the start. **0** printed SWALLOWED lines no registered group claims, **0** registered groups with no printed line, **0** unequal swallow sets, **0** unequal `dispositions:` lines, **0** swallow cases that printed nothing, and the corpus's own substring reading fails **0** of 20 — against the pins §1 names as updated BY RULE (§4.5). | **PASS** |
| H2 | "**Exactly 5 SWALLOWED groups**, counts `memory.rs:156 ×3, task/exec.rs:606 ×4, memory/store.rs:96 ×2, task/registry.rs:1084 ×4, task/registry.rs:379 ×1`; tally line byte-identical to the record's (`dispositions: swallowed 14, ambiguous 8`)." | **5** SWALLOWED groups accounting for **14** chains on the kept `a` store, at exactly the five sites with exactly the five counts §1 names — **0** differences over the record's 5 sites, **0** sinks the join could not resolve. Printed tally `dispositions: swallowed 14, ambiguous 8`, byte-identical to the record's for this process (§4.1). | **PASS** |
| H3 | "**Every tally line byte-identical** to the record's per-process `tally_line` (114 + 114 processes with chains; the 30 + 30 without print `no exceptions recorded`), and per trace the sum of SWALLOWED group counts == the record's `swallowed_count`." | **288** per-process comparisons — every trace of `ws` and of `ws0` — with **0** differences: **0** tally lines that are not the record's and **0** swallow counts that are not the record's, on each arm. 114 processes per arm printed a tally line and 30 printed `no exceptions recorded`, with **0** INCOMPLETE banners. The chains sum to **782** (`ws`) and **812** (`ws0`), the record's own totals (§4.2). | **PASS** |
| H4 | "**ws: 91 SWALLOWED groups whose (site, count) multiset equals the record's 91-row table, summing to 782; tally `swallowed 782, ambiguous 330, panicked 2`; header counts 144 / 114 / 30; INCOMPLETE members 0. ws0: 98 groups summing to 812; tally `swallowed 812, ambiguous 300, panicked 2`.**" | **4 site differences on each arm, 8 in all.** `ws`: **100** merged groups accounting for **782** chains over **89** distinct sites against the record's 91 — 2 sites missing, 0 extra, 2 count differences, **11** of 782 chains booked at a sibling file. `ws0`: **103** groups, **812** chains, **96** sites against 98 — 2 missing, 0 extra, 2 count differences, **10** of 812 chains mis-attributed. Everything else in the rule holds on both arms: the sums (782, 812), the tally counts (`swallowed 782, ambiguous 330, panicked 2` and `swallowed 812, ambiguous 300, panicked 2`), the header counts **144 / 114 / 30**, INCOMPLETE members **0**, unresolved sinks **0** (§4.3). | **STOP** (4 ≠ 0, each arm) |
| H5 | "**Both under 60 s.**" | **0** arms at or over the ceiling: `ws` **0.530 s**, `ws0` **0.515 s**, neither killed, both exit 0 — 144 traces opened and merged per answer (§4.4). | **PASS** |
| H6 | "**Python `exceptions` output byte-identical to 0.8.1** (the suite is the pin; no Python expectation changes); Rust workspace green; v17's single-shape blocks byte-identical." | `pytest -q` exit **0**: **1276 passed, 1 skipped** in 86.0 s, with no Python expectation changed by this slice — the suite carries the vectors v01–v19, the Python corpus and `tests/test_exceptions*.py`, and it is the pin. `cargo test --workspace` exit **0**: **38** `test result: ok.` lines, **606 passed, 0 failed, 19 ignored** (§4.6). | **PASS** |

**Overall: five of six, and the miss is exactly one thing.** Everywhere the
reader asks about ONE process — the A run's five shapes (H2), all 288
per-process answers (H3), all 20 corpus cases (H1) — the grouped output
reproduces the published record line for line, site for site, tally for
tally, with zero differences. The chains are conserved in the invocation view
too: 782 and 812, the record's own totals, with the summed dispositions and
the header's 144 / 114 / 30 exact.

What the invocation view does not reproduce is the record's per-FILE table.
Its shape key has no file in it, so two processes whose helper shares a
qualname AND a line number merge into one printed block, and the block names
only the first member's event and process. Eleven chains of 782 on `ws`, ten
of 812 on `ws0`, are therefore attributed to a sibling test file. The
counting is right and the addressing is not — and the record says STOP with
the number rather than repairing anything. §5.1 names every process, file and
chain involved.

### 4.1 H2 — the A run's five shapes, at the site grain

`sensorium exceptions 20260905-091115-5da3dc --limit 100000` on the kept `a`
store: exit 0, 0.041 s, 4701 bytes over 41 lines. Five SWALLOWED groups, and
each group's chain count booked at the sink its verdict names, resolved
through the trace's own `events` → `code_objects` join:

| sink | chains measured | the record's count | equal |
|---|---|---|---|
| `…/bloomery-daemon/src/memory.rs:156` | 3 | 3 | yes |
| `…/bloomery-daemon/src/task/exec.rs:606` | 4 | 4 | yes |
| `…/bloomery-daemon/src/memory/store.rs:96` | 2 | 2 | yes |
| `…/bloomery-daemon/src/task/registry.rs:1084` | 4 | 4 | yes |
| `…/bloomery-daemon/src/task/registry.rs:379` | 1 | 1 | yes |

Five groups, 14 chains, 0 missing, 0 extra, 0 count differences, 0 sinks the
join could not resolve. The record's own §4.1 adjudicated these as 14
separate SWALLOWED lines; this run reads the same 14 chains printed as 5
blocks. One vary line fired (`messages`, twice): two of the five shapes
absorbed more than one distinct message and the block says so.

### 4.2 H3 — 288 per-process comparisons, both arms

One `exceptions <run> --limit 100000` per trace, 144 on `ws` and 144 on
`ws0`, each compared against the record's `tally_line` for that process and
against its `swallowed_count`:

| | `ws` | `ws0` |
|---|---|---|
| processes read | 144 | 144 |
| runs only in the store / only in the record | 0 / 0 | 0 / 0 |
| tally lines that are not the record's | **0** | **0** |
| swallow counts that are not the record's | **0** | **0** |
| processes that printed `no exceptions recorded` | 30 | 30 |
| processes with a tally line | 114 | 114 |
| processes carrying an INCOMPLETE banner | 0 | 0 |
| SWALLOWED groups printed | 168 | 177 |
| chains those groups account for | **782** | **812** |
| total output | 182 334 bytes / 1634 lines | 179 431 bytes / 1615 lines |
| slowest single answer | 0.046 s | 0.045 s |

A process the record holds `None` for was checked for the empty-answer SHAPE
(`no exceptions recorded`, with no INCOMPLETE banner), never for a zero: 30
per arm, all 60 in that shape. The 782 and 812 are the record's own arm
totals, reached here by summing group brackets rather than counting printed
lines — which is N5's claim, measured.

### 4.3 H4 — the invocation view against the record's per-site tables

`ws`: `sensorium exceptions 20260905-091115-9e8e5a --limit 100000`, exit 0,
0.530 s, 128 167 bytes over 927 lines.
`ws0`: `sensorium exceptions 20260905-091209-bfa73c --limit 100000`, exit 0,
0.515 s, 125 820 bytes over 910 lines.

| | `ws` | `ws0` |
|---|---|---|
| merged SWALLOWED groups printed | 100 (§1 predicted 91) | 103 (§1 predicted 98) |
| chains they account for | **782** = the record's | **812** = the record's |
| distinct sites the groups resolve to | 89 | 96 |
| the record's sites | 91 | 98 |
| **site differences (the gate)** | **4** | **4** |
| sites missing | 2 | 2 |
| sites extra | **0** | **0** |
| sites with a different count | 2 | 2 |
| chains booked at the wrong file | 11 of 782 | 10 of 812 |
| header `N processes, k with Err chains, m with none` | `144, 114, 30` — the record's | `144, 114, 30` — the record's |
| summed `dispositions:` counts | `swallowed 782, panicked 2, ambiguous 330` = the record's sums | `swallowed 812, panicked 2, ambiguous 300` = the record's sums |
| INCOMPLETE members | **0** | **0** |
| sinks the join could not resolve | **0** | **0** |
| distinct processes the brackets NAME | 43 | 49 |

Every difference, both arms, in full — this is the whole of the miss:

| arm | kind | site | measured | the record |
|---|---|---|---|---|
| `ws` | missing | `…/bloomery-daemon/tests/api_native_agent_delete_test.rs:64` | 0 | 2 |
| `ws` | missing | `…/bloomery-daemon/tests/task_exec_run_test.rs:42` | 0 | 9 |
| `ws` | count | `…/bloomery-daemon/tests/pager_refusal_advice_test.rs:64` | 3 | 1 |
| `ws` | count | `…/bloomery-daemon/tests/task_exec_read_find_test.rs:42` | 18 | 9 |
| `ws0` | missing | `…/bloomery-daemon/tests/pager_refusal_advice_test.rs:64` | 0 | 1 |
| `ws0` | missing | `…/bloomery-daemon/tests/task_exec_run_test.rs:42` | 0 | 9 |
| `ws0` | count | `…/bloomery-daemon/tests/api_native_agent_delete_test.rs:64` | 3 | 2 |
| `ws0` | count | `…/bloomery-daemon/tests/task_exec_read_find_test.rs:42` | 18 | 9 |

The two count differences on each arm are exactly the two missing sites'
chains: 2 + 1 = 3 at one `:64`, 9 + 9 = 18 at one `:42`, on both arms. No
chain was lost, invented or double-counted anywhere — the arm totals are the
record's to the chain. §5.1 is the mechanism, with the processes named.

### 4.4 H5 — the walls

| arm | wall | kill armed | killed |
|---|---|---|---|
| `ws` | **0.530 s** | 60 s | no |
| `ws0` | **0.515 s** | 60 s | no |

144 traces opened, read and merged into one answer in about half a second —
§1's own estimate was ≈10 s at ≈0.07 s an open, so the answer is roughly
twenty times faster than the ceiling's derivation assumed, and 113 times
under the ceiling itself. Both exit 0; the kill did not fire on either arm.

### 4.5 H1 — the corpus, against the pins updated BY RULE

Twenty `corpus/rust/*` cases carry an `exceptions` question. Each was copied
into its own workdir, recorded once with the 0.3.1 driver into a corpus
target that was 0 bytes at the start, and answered with its own
`<workdir>/.sensorium` store — so the fresh `SENSORIUM_DIR` §1 requires
stayed empty, and §2 records that it did (0 traces in it afterwards).

All six of the collector's counts are **0 of 20**: no printed SWALLOWED line
that no registered group claims, no registered group with no printed line, no
unequal swallow set, no unequal `dispositions:` line, no swallow case that
printed an empty set, and no failure of the corpus's own substring reading.
The per-case table is §3's; the five files §1 names as moved BY RULE
(`err_stored`, `err_rendered_into_value`, `v18`, `v17`,
`tests/test_exceptions_rust_gate.py`) are all inside that 20 of 20 —
`rust/err_stored/were-the-retry-failures-swallowed` prints
`dispositions: ambiguous 2` against the registered `dispositions: ambiguous 2`
with a swallow set of 0 / 0, which is R-G4-as-amended-by-R-G6's grain
measured rather than asserted.

### 4.6 H6 — did anything else move?

| | value |
|---|---|
| `pytest -q` (whole suite, from the repo root) | exit **0** — `1276 passed, 1 skipped in 85.99s` |
| `cargo test --workspace` (in `rust/`, same target) | exit **0** — 38 `test result: ok.` lines |
| Rust tests, summed over those lines | **606 passed, 0 failed, 19 ignored** |
| driver sha256 after H6 | `50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f` — the sha the preflight recorded |
| the only variables set for the suite | `PYTHONDONTWRITEBYTECODE`, `SENSORIUM_CARGO_SENSORIUM` |

The Python suite is the pin: this slice changed no Python expectation, and
every vector (v01–v19, including v17's single-shape blocks and v18's
ambiguous merge), the Python corpus and `tests/test_exceptions*.py` are in
it. `cargo test --workspace` compiled nothing — no crate changed in this
slice — and the driver's sha256 afterwards is the one the preflight recorded,
so H1, which ran before H6, ran the binary §2 pins.

## 5. Gaps

### 5.1 The one place the grain does not reproduce the record: the shape key has no file in it

H4's four differences per arm are one mechanism, seen twice on each arm, and
the run's own evidence names every part of it.

`exceptions` in invocation mode merges chains into SHAPES across processes.
The key is the verdict, the qualname and the line — **not the file** — and
the printed bracket names only the first member: `[×N over M processes: first
e<id> in <run>, +K]`. When two processes' helpers share a qualname *and* a
line number in different files, their chains land in one block, and the file
of every member but the first is not printed anywhere in the answer.

Two such collisions exist in this workspace, and both fire on both arms:

**`sandbox` at L42, `sink_let_underscore`** — `20260905-091125-80bdb1`
(`…/tests/task_exec_read_find_test.rs:42`, 9 chains) and
`20260905-091125-80c4ab` (`…/tests/task_exec_run_test.rs:42`, 9 chains). The
invocation answer prints them as two merged blocks, `[×16 over 2 processes:
first e5 in 20260905-091125-80bdb1, +15]` and `[×2 over 2 processes: first
e24 in 20260905-091125-80bdb1, +1]`. Both name `80bdb1`, so all 18 chains
resolve to `task_exec_read_find_test.rs:42` and `task_exec_run_test.rs:42`
vanishes from the table.

**`fresh_dir` at L64, `sink_let_underscore`** — `20260905-091125-815542`
(`…/tests/pager_refusal_advice_test.rs:64`, 1 chain) and
`20260905-091125-fc4de2` (`…/tests/api_native_agent_delete_test.rs:64`, 2
chains), printed as `[×3 over 2 processes: first e5 in
20260905-091125-815542, +2]`. All 3 resolve to `pager_refusal_advice_test.rs`
and the other file vanishes. On `ws0` the same shape's first member is the
other process, which is why the two files swap roles between the arms in
§4.3's table — the direction of the loss follows whichever process the
invocation happened to reach first, which is itself worth knowing.

The per-process answers are not affected and were checked: H3 read all 288
and found the file attribution right in every one (0 unequal swallow counts,
0 unequal tally lines). The record's per-site table is therefore still
derivable from this build — from 144 answers, not from one.

**Under both readings of §1's H4, this is a STOP.** The strict reading
("91 SWALLOWED groups whose (site, count) multiset equals the record's 91-row
table") fails twice over: 100 groups, not 91, and the multiset differs at 4
sites. The generous reading — that the group count is a prediction and the
multiset equality is the gate — fails on the multiset alone. Nothing in the
run turns on which reading is taken, and no reading of §1 makes 4 into 0.

**What this does not say.** It does not say the invocation view is wrong
about how much was swallowed: 782 and 812 chains, the summed dispositions and
the header's 144 / 114 / 30 are the record's, exactly. It says the invocation
view is less specific than the record about WHERE, at 11 chains of 782 and 10
of 812, and that the answer gives a reader no way to notice.

**Nothing was repaired.** Post-lock, no code changed. A fix has a shape — put
the file in the shape key, or name the file in the merged bracket — and
choosing between them is a design question this record does not decide.

### 5.2 §1 predicted the group count from the record's SITE count, and shapes are not sites

§1's H4 says "91 SWALLOWED groups" for `ws` and "98" for `ws0`, derived from
the record's 91- and 98-row site tables. The measurement is 100 and 103. The
grouping is per SHAPE, and one site can carry several: a different `how`, a
different verdict, a different absorbing frame. Even with the site multiset
perfectly reproduced, that clause would have missed — §4.2's per-process
answers make the same point from the other side (168 and 177 groups over the
same 782 and 812 chains). The prediction was written before this document's
own definition of a group was measured against anything. It is recorded here,
not repaired, and it is not the reason H4 stopped.

### 5.3 §1's tally clause for H4 is spelled in an order the CLI does not print

§1's H4 writes the summed tally as `swallowed 782, ambiguous 330, panicked 2`;
the invocation answer prints `dispositions: swallowed 782, panicked 2,
ambiguous 330`. The counts are identical and the instrument compares counts,
which is also the reading H2's and H3's explicit "byte-identical" wording
contrasts with — those two clauses say byte-identical and were measured that
way (and passed); H4's does not. Under the counts reading the clause holds on
both arms; under a byte reading of that one string it does not, because §1's
author transcribed a JSON object's key order rather than a printed line. Both
readings are recorded because §1 is never edited; neither moves H4's verdict,
which the site multiset decided.

### 5.4 What this run did not measure

* **No program was measured.** This slice changes what `exceptions` prints
  and changes no crate; `cargo-sensorium` stays 0.3.1 and was not rebuilt by
  the runner. Every number about the workspace under measurement — the 91-
  and 98-row site tables, the 288 per-process tally lines, the per-process
  swallow counts — is the PUBLISHED E6⁗ record's, read at `605db64` (sha256
  in §2) and never re-measured. No endpoint above is filled from it.
* **0.8.1 was not run.** The before-and-after bytes for the busiest `ws`
  process are the record's `sweep_processes[]` row against this run's answer.
  The record carries no LINE count for 0.8.1, so that half of §3's
  reported-without-a-gate row is absent rather than derived.
* **Nothing was dropped.** Every `{value, n, lens, dropped}` cell in
  `results.json` carries a value; no cell is null, and no cell carries both a
  value and a dropped reason.
* **The kept stores were read, not written.** Their `traces/*.db` counts and
  total bytes are identical before and after (1 / 144 / 144), which §2
  records. The one write this run caused is the CLI's own audit log:
  `invocations.jsonl` grew by 1 row in `a`, 145 in `ws` and 145 in `ws0` —
  one per `sensorium` call, 144 of them H3's and 1 H4's on each multi-process
  arm. `SENSORIUM_NO_INVOCATION_LOG` was deliberately not set: the E6⁗
  protocol did not set it either, and `acceptance_lib.plain_env()` strips
  every `SENSORIUM_*` from each child, so setting it in the launcher would
  have changed nothing while implying a purity the run does not have.
* **No wall was gated except H5's.** H2 answered in 0.041 s, the 288
  per-process answers in 5.7 s per arm, H1's twenty recordings in 23 s, H6's
  pytest in 86 s and `cargo test --workspace` in 10.9 s. None of those is an
  endpoint.

### 5.5 The launch that measured nothing, and the commit that fixed it

The first detached launch (17:59:23) raised `NameError: name 'LOGS' is not
defined` in H2, fourteen seconds in. Fix round 1 of the instrument task had
moved the five phases into `acceptance_grain_phases.py`, where each opens
`logs_at(LOGS / "<phase>")` in its own namespace; the front door assigned
`acceptance_lib.LOGS` and `acceptance_phases.LOGS` and not that third
pointer. It failed **before any oracle comparison was printed** — the
byte-lock, the preflight and the oracle read had run, and no `exceptions`
command had — so under §1's own rule it is infrastructure. The plumbing was
fixed and committed ALONE (`d699b4c`), with three mutation-checked tests: the
runner assigns the phases module the run's root (dropping the assignment goes
red; pointing it one directory up goes red), `phase_h2` runs end to end and
opens its log directory under that root, and a fresh load of the phases
module declares the name and holds no location. §1 was not touched — its
sha256 is the lock's before and after. `sensorium-dir/grain` and
`corpus-target-grain` were emptied and the run below started from zero. The
failed launch's marker, log and partial record are kept beside this run's
under `acceptance-grain/failed-launch-1/`.

This is why §2's repo HEAD is `d699b4c` and not the lock+1 commit: one
instrument commit sits between the lock and the measurement, and it changed
the runner's plumbing only.

### 5.6 Reported without a gate

Restated from §3 with the set each number was counted over, because two of
them are the point of the slice:

* **The busiest `ws` process** (`20260905-091125-fc7302`): **20 166 bytes
  under 0.8.1 → 3360 bytes** over 32 lines under 0.8.2 — a **6.0×**
  reduction, printing the same 54 chains as 3 groups instead of 54 lines.
  The 0.8.1 figure is the record's, never re-measured.
* **144 per-process answers versus one invocation answer**: **182 334 bytes
  over 1634 lines** against **128 167 bytes over 927 lines** — 1.42× the
  bytes and 1.76× the lines to say it 144 times instead of once. Both halves
  were measured by this run, under 0.8.2. The comparison is not like for
  like and the record says so: the 144 answers carry the per-file attribution
  §5.1 shows the one answer loses.
* **Vary lines that fired, by kind**, summed over every answer this run read
  (H2, H3/`ws`, H3/`ws0`, H4/`ws`, H4/`ws0` — five answers, 1282 printed blocks):
  `messages` **152**, `origins` **38**, `routes` **38**, `details` **0**. An
  honesty count, not a gate. Three of the four spellings rulings R-G3, R-G5
  and R-G6 settled fired on this evidence; `details vary` never did, so that
  spelling is unexercised by this record and its wording is untested here.

### 5.7 Residuals found by this run, recorded and not repaired

1. **The shape key carries no file** (§5.1) — 11 chains of 782 and 10 of 812
   attributed to a sibling test file in the invocation view, invisibly to a
   reader of that answer. The only residual that moved a verdict.
2. **§1's group-count prediction conflated shapes with sites** (§5.2).
3. **§1's H4 tally string is in the oracle JSON's key order, not the CLI's**
   (§5.3).
4. **The invocation header's `panics:` line counts events, not the tally's
   tag.** Both arms print `panics: 8 recorded` beside a tally of
   `panicked 2`. §1 gates the tally, which matched exactly on both arms; the
   header line is not pre-registered and the two numbers count different
   things (unwind events recorded versus chains dispositioned). Noticed while
   reading H4's header, recorded, not repaired.
5. **The suite's skip count depends on one variable.** Run without
   `SENSORIUM_CARGO_SENSORIUM` the suite is `1268 passed, 9 skipped`; H6 sets
   it, and the module that is skipped without a built driver runs — `1276
   passed, 1 skipped`. Both were seen on this box on 2026-09-05, the first
   before the launch and the second inside H6. The pin is the second.

And the ones the earlier tasks recorded and this run did not touch: the
deferred `1 swallowing sites` grammar at S = 1 (the phrase was frozen for
H4's comparison and this run read it 0 times, both arms printing 100 and 103
swallowing sites), rung-3's R16 (v) by-value handoff blind spot, and design
B2's `self.record(&e);` side channel. None had exposure here and this run
falsifies none of them.
