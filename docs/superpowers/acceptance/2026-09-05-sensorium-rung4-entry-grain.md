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

*(written by Task 5, from the run's own record)*
