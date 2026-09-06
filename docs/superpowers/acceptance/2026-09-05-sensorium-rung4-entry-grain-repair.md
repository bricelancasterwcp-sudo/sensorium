# Rung-4 entry acceptance, the grain of exceptions — the REPAIR (H1′–H6′)

The record of whether `exceptions`, with the shape key repaired under ruling
R-G12, reproduces the answers the rung-3 borrow-repair record already
published — line for line, site for site, tally for tally.

**This repairs a STOP; it does not re-roll one.** The first measurement —
`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`, §1
locked at `05c3124`, measured 2026-09-05 — read H4 **STOP**: 4 site
differences on each arm. The shape key's site was the printed
`qualname L<line>` with no file in it, and this workspace carries a `sandbox`
at L42 in two test files and a `fresh_dir` at L64 in two more, so 21 chains
merged across processes and were booked under a sibling file while every
count stayed right (that record's §4.3 and §5.1). **That record stands
exactly as written**; nothing here amends it, and no number in it is
re-measured. Ruling R-G12 put the code object's `(file, line)` into the key
and gives a block whose site text collides inside one answer its file's
basename; commit `a86d67e` is that repair, and it is the only difference
between the reader measured there and the reader measured here. This
document's §1′ was written and locked before any number below was read.

**Nothing here measures a program.** This slice changes what the reader
PRINTS and changes no crate (`cargo-sensorium` stays 0.3.1), so its question
is a question about output. The ORACLE is the same one the first record used:
the PUBLISHED E6⁗ record,
`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json` at
`605db64` — its per-site tables, its 288 per-process tally lines and its
per-process swallow counts, measured on 2026-09-05, read here and **never
re-measured**. What is re-run is the reader, over the trace stores that record
cites.

**The kept stores are the INPUTS, and they are the same stores.** The three
directories under `/mnt/extra/sensorium-rung2/sensorium-dir/e6q` (`a`, `ws`,
`ws0`) hold the 1 + 144 + 144 traces the E6⁗ arms recorded, and this run only
reads them: no arm is recorded, no cargo command is run against the clone, no
target is emptied. Read-only means the traces. Every `sensorium` call appends
one audit row to the store's `invocations.jsonl` — a sibling of `traces/`
that `runs` and `find_trace` do not read, written by `cli.main` for every
invocation and unavoidable short of `SENSORIUM_NO_INVOCATION_LOG=1`, which
neither the E6⁗ protocol nor the first measurement set. The `traces/*.db` are
counted and their bytes summed before and after, and the audit rows this run
added are reported in §2, so the record states the one write it causes rather
than claiming a purity it does not have.

**The instrument is the first record's, through a sibling.**
`rust/tests/acceptance_grain_repair.py` is `rust/tests/acceptance_grain.py`
pointed at this document: the oracle, the preflight, the five phases, the site
comparison, the schema and the renderer are the same objects, asserted name by
name in `tests/test_acceptance_grain_repair.py`. What it overrides is this
document, its byte-lock, the ledger subdirectory `acceptance-grain-repair/`,
the markers `grain-repair.DONE`/`.FAILED`, H1′'s corpus workdir and the raw
and assembled record's file names — so nothing this run writes can land where
the first record's evidence lives.

**§1′ is byte-locked.** It is committed ALONE, after the repair and its tests,
but before any number below has been read, and it is the first document's §1
carried VERBATIM with three changes a reader can check in one place: every id
carries a prime; H4′'s endpoint states the multiset the repaired key predicts
(one shape per `(file, line)` site) and quotes the summed `dispositions:` line
in the order the tool prints it (`TAG_ORDER`) rather than the oracle's dict
order, which the first measurement recorded under both readings; and the lens
and the ungated list name this run's instrument, its markers, the first record
and the collision count. The runner refuses to run if this section differs
from the commit that locked it — compared with `awk '/^## 1/,/^## 2/'`, the
sha recorded in §2 — and refuses outright while no lock sha is set. ~~§1′ is not amended: there is one sha and no dated note inside it.~~ **§1′ carries TWO shas — the original lock `9bf64df` and the amendment `ae9a15b` — and one dated note, at §1′'s line 47, naming the reader commit measured. The struck sentence predates that amendment; corrected in place 2026-09-05 by Task 8's fix round 1, and it sits OUTSIDE the byte-locked range, which begins at `## 1`, so §1′'s sha is untouched (§5.7 item 2).** A completed measurement
is never re-rolled, and a miss is a STOP with its number — a second STOP here
is recorded as one, and what happens next is Brice's ruling.

## 1. Pre-registration

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| H1′ | Did the definition or the grouping move a corpus verdict? | E6's collector over every `corpus/rust/*` case with an `exceptions` question (20), fresh corpus target, the 0.8.1 driver (crates unchanged). The pins updated by rule are listed here: `err_stored` and `err_rendered_into_value` (N2, the sentence), vector `v18` (N2), vector `v17` and `tests/test_exceptions_rust_gate.py` (N5, the continuation note), and `err_stored` again (N3/N4: its retry arm's two chains are one shape — the second head is no longer printed; the bracket `[×2: e4, e8]` and the line `messages: 2 distinct (first shown)` are pinned instead, and `origins:` is pinned ABSENT — R-G4 as amended by R-G6, which moved one site raising two different errors off the `origins:` label and onto `messages:`). | **20 of 20 equal** (swallow sets, tallies, and every pinned line). | Parent §8 E6, unchanged. |
| H2′ | Does the grouped view reproduce the A record at the site grain? | `exceptions 20260905-091115-5da3dc` on the kept `a` store. | **Exactly 5 SWALLOWED groups**, counts `memory.rs:156 ×3, task/exec.rs:606 ×4, memory/store.rs:96 ×2, task/registry.rs:1084 ×4, task/registry.rs:379 ×1`; tally line byte-identical to the record's (`dispositions: swallowed 14, ambiguous 8`). | E6‴/E6⁗ §4.1's five shapes. |
| H3′ | Does grouping change any per-process TALLY? | `exceptions <run>` on each of the 144 `ws` traces and each of the 144 `ws0` traces. | **Every tally line byte-identical** to the record's per-process `tally_line` (114 + 114 processes with chains; the 30 + 30 without print `no exceptions recorded`), and per trace the sum of SWALLOWED group counts == the record's `swallowed_count`. | N5: the tally counts chains. |
| H4′ | Does the invocation view reproduce the record's per-site table? | `exceptions 20260905-091115-9e8e5a` on `ws`, and the `ws0` invocation likewise. | **ws: exactly 91 SWALLOWED shapes, one per (file, line) site, whose (site, count) multiset equals the record's 91-row table (782 chains); ws0: exactly 98 shapes / 812; the summed `dispositions:` line, in the tool's `TAG_ORDER`, reads `swallowed 782, panicked 2, ambiguous 330` (ws) and `swallowed 812, panicked 2, ambiguous 300` (ws0); header counts 144 / 114 / 30; INCOMPLETE members 0. Reported: the number of shapes whose site text collided within each answer and therefore print their file basename (expected ≥ 2 per arm: `sandbox L42`, `fresh_dir L64`).** | The record's §4.2/§4.3 tables and the summed per-process tallies (derived from `results.json` before this design was written: 114 tally lines per arm). |
| H5′ | Is the invocation view usable? | Wall of H4's two commands, 60 s kill armed. | **Both under 60 s.** | E0's rule; 144 opens at ≈0.07 s each ≈ 10 s. |
| H6′ | Did anything else move? | The whole Python suite (vectors v01–v19, the Python corpus, `tests/test_exceptions*.py`) and the Rust workspace tests. | **Python `exceptions` output byte-identical to 0.8.1** (the suite is the pin; no Python expectation changes); Rust workspace green; v17's single-shape blocks byte-identical. | N7. |

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
`grain-repair.DONE`/`.FAILED` marker carrying `exit=<n>`; nothing is read
before the marker exists. Every measurement is `{value, n, lens, dropped}`:
a `null` value with a reason is the only not-measured, `0` is
measured-and-zero, and
**no endpoint is ever filled from the oracle** — the record is already in the
room, and a headline that borrowed from it could not fail. The reader
differs from the first measurement's by ONE commit: `a86d67e`,
*fix(exceptions): the shape key carries the file; colliding site texts print
their file (R-G12)*. The first record —
`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`, §1
locked at `05c3124`, measured 2026-09-05, H4 **STOP** — stands unamended and
is not re-run; its numbers are what H4′ is read against. The instrument is
`rust/tests/acceptance_grain_repair.py`: `rust/tests/acceptance_grain.py`
pointed at this document, sharing the oracle, the preflight, the five
phases, the site comparison, the schema and the renderer as the same objects
(`tests/test_acceptance_grain_repair.py` asserts that), and differing only
in this document, its lock, the ledger subdirectory
`acceptance-grain-repair/`, the markers and the record's file names.
*Amended 2026-09-05 before any measurement: the reader commit measured is
`166a0c8` (a `collisions()` defect — it counted shapes sharing a site TEXT
rather than the distinct PLACES that text named, so two shapes at one place
printed a file no answer needed — found by Task 7's review after the lock at
`9bf64df`); both shas are recorded in §2.*

**The pins updated BY RULE before this section was locked.** H1′'s "20 of 20
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
`messages:` / `details vary` / `routes:`, and all four are counted; and the
number of shapes whose printed site text collided inside one answer and
therefore carry their file's basename (R-G12), per arm.

## 2. Environment

Rendered by `rust/tests/render_grain.py` from the assembled record and pasted
here **with the two clauses still wrong for this document struck through and corrected**: the renderer and schema are the FIRST record's objects, shared by reference — this instrument's design — and two of the strings `render_grain` hardcodes are that record's (§5.7 items 1–2). A third, the results file's name, was a wrong VALUE rather than a literal and is repaired at its derivation instead (R-G15, §5.7 item 1). Nothing they misname is a measurement.

Measured 2026-09-05T19:46:28-0500 → 2026-09-05T19:49:12-0500 by `rust/tests/acceptance_grain_repair.py`, launched detached; the raw facts it recorded are ~~`results-grain-raw.json`~~ **`results-grain-repair-raw.json`** in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-05-sensorium-rung4-entry-grain-repair.results.json`, which `acceptance_grain_schema.assemble_grain` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless the locked range is byte-identical to the commit that locked it — and refuses outright while no lock sha is set. The range is awk '/^## 1/,/^## 2/' PLUS the definition of every footnote §1 references — here §1 references no footnote (`footnotes_in_range` = none), so the extended range and `awk '/^## 1/,/^## 2/'` are the same bytes. Checked at `ae9a15b`: 7437 bytes, sha256 `e894f473b79c0ee432088b0a913fb01fd4702c2acce9894a134442379ece8015` on both sides — identical: yes. ~~§1 was committed ALONE and never amended: there is no second sha (`original_lock` = 9bf64df).~~ **§1′ was committed ALONE at `9bf64df` (sha256 `62ddc575fb3d37d426bf5d091edd9307748f17da94617aacb44307586ca86038`, 7087 bytes) and AMENDED ONCE before any number below was read, at `ae9a15b` (sha256 `e894f473b79c0ee432088b0a913fb01fd4702c2acce9894a134442379ece8015`, 7437 bytes) — a 350-byte dated sentence in the lens naming the reader commit actually measured. The run's own byte-lock check carries both shas and the flag `amended_after_the_original_lock: true`; the renderer's sentence is written for the unamended case and prints the second sha beside a denial of it.**

**The oracle.** `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.results.json` at `605db64` (sha256 `7d1f10e51e8c3cf92e9deaf9b5e9d24f823ac4bd8bb7d045d7474b4ce6696588`) — sites {'a': 5, 'ws': 91, 'ws0': 98}, lines {'a': 14, 'ws': 782, 'ws0': 812}, processes with a tally line {'a': 1, 'ws': 114, 'ws0': 114}, without one {'a': 0, 'ws': 30, 'ws0': 30}. read from the committed record; nothing here was measured by this run, and no endpoint above is filled from it

| Pin | Value |
|---|---|
| repo HEAD at the run | `c862c5ffd0b51f65141408361bf9bb901032ea08` (branch `feat/rung4-entry-grain`) |
| driver (H1 only; NOT rebuilt by this run) | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` 0.3.1, mtime 2026-09-05T12:29:32-0500; rebuilt: no |
| driver sha256 | `50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f` — unchanged across the run: yes |
| kept trace stores (the INPUTS) | `/mnt/extra/sensorium-rung2/sensorium-dir/e6q`/{a,ws,ws0}; traces before a 1, ws 144, ws0 144; after a 1, ws 144, ws0 144; `traces/*.db` unchanged: yes |
| invocation ids the stores carry | ws `20260905-091115-9e8e5a`, ws0 `20260905-091209-bfa73c` |
| the one write this run causes | the kept stores' `traces/*.db` are INPUTS and are never written; every CLI call appends one audit row to the store's `invocations.jsonl`, a sibling of `traces/` that `runs` and `find_trace` do not read, and the counts before and after are both recorded — rows added: {'a': 1, 'ws': 145, 'ws0': 145} |
| fresh trace directory (H1's, which stays empty) | `/mnt/extra/sensorium-rung2/sensorium-dir/grain-repair`; traces in it afterwards: 0 |
| corpus target (H1) — FRESH for this run | `/mnt/extra/sensorium-rung2/corpus-target-grain-repair`, 255849766 bytes afterwards |
| Rust workspace target (H6's `cargo test`) | `/mnt/extra/sensorium-rung2/rust-target` |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| repo porcelain before / after | empty / empty |
| 1-minute load at the start | 0.55 |
| disk free on the repo's filesystem, before / after | 12.85 GB / 12.84 GB |

**Log locations.** Every command's log is under `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/acceptance-grain-repair/logs`, one subdirectory per phase (`h2`, `h3-ws`, `h3-ws0`, `h4-ws`, `h4-ws0`, `h1`, `h6`).

1-minute load at each phase's start: H2 0.75, H3 0.75, H4 0.95, H1 1.04, H6 1.16.

**One launch, and it measured this record.** Launched once, detached, at
2026-09-05T19:46:28-0500 (`setsid nohup bash
<ledger>/acceptance-grain-repair/launch.sh`, runner pid 3896233); wrote
`grain-repair.DONE` carrying `exit=0` at 19:49:12 — 2 min 44 s. Nothing was
read before that marker existed: not the log, not the raw record, not
`results.json`. There is no `failed-launch-*` directory beside this record
because there was no failed launch. The launcher is the first record's
(`../acceptance-grain/launch.sh`) with three things changed — the pid file
and its ledger directory, the two FRESH locations §1′ requires, and the
sibling runner it execs — diffed before the launch: the five other `export`
lines (`SENSORIUM_E6Q_STORES`, `SENSORIUM_DRIVER`, `SENSORIUM_RUST_TARGET`,
`SENSORIUM_CARGO_SENSORIUM`, `PYTHONDONTWRITEBYTECODE`) are byte-equal.
**Both fresh locations were absent before the launch** — each returned `No
such file or directory` in the preflight — and the runner made them.

**The driver was current before the launch, and the runner did not touch
it.** §1′ pins `cargo-sensorium` 0.3.1, already built under
`/mnt/extra/sensorium-rung2/rust-target`, and the runner does not rebuild it
— but H6′ runs `cargo test --workspace` in that same target, which would
relink a stale driver mid-run. So `cargo build -p cargo-sensorium` was run in
`rust/` against that target BEFORE the launch, by hand, with `pgrep -a cargo`
and `pgrep -a rustc` both empty first: it compiled nothing (`Finished dev
profile in 0.03s`) and the sha256 did not move. This slice changed no crate.
The binary carries the string `cargo-sensorium 0.3.1`, and the sha256
`50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f` is the
same before the build, after it, in the runner's preflight, and after H6′'s
`cargo test --workspace` (§4.6) — the value the first record pins too. No
step of the measurement built anything.

**The suite was green before the launch too**: `PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m pytest -q -p no:cacheprovider` from the repo root — exit
0, **1293 passed, 9 skipped in 61.4 s**. H6′ runs the same suite with
`SENSORIUM_CARGO_SENSORIUM` set and reads **1301 passed, 1 skipped**: the
eight tests that skip without a built driver run there — the first record's
§5.7 residual 5, measured again.

**`SENSORIUM_NO_INVOCATION_LOG` was deliberately not set**, so the audit rows
this run added are reported above rather than engineered away — and it could
not have worked anyway: `acceptance_lib.plain_env()` strips every
`SENSORIUM_*` from each child before the CLI sees it, and neither the E6⁗
protocol nor the first measurement set it. The rows were counted
independently of the runner: `invocations.jsonl` went `a` 3 → 4, `ws`
295 → 440, `ws0` 290 → 435 — **1 / 145 / 145 added**, exactly the runner's
cleanup line, one per `sensorium` call (144 H3′'s and 1 H4′'s per
multi-process arm). The `traces/*.db` are byte-unchanged: 1 / 144 / 144 files
and 581 632 / 1 032 368 128 / 1 032 294 400 bytes before and after, summed by
hand as well as by the runner.

## 3. Results

Every measurement is `{value, n, lens, dropped}`; a `null` value with a reason is the ONLY not-measured, and `0` is measured-and-zero. Rendered by `rust/tests/render_grain.py` from `2026-09-05-sensorium-rung4-entry-grain-repair.results.json`. No verdict is decided here — §4 is. **The renderer prints the endpoint ids unprimed (`H1`…`H6`) because it is the first record's object; in this document they are H1′–H6′ throughout, and §4 uses the primed ids — §5.7.**

| Id | Headline | n | Lens (abridged) | Dropped |
|---|---|---|---|---|
| H1 | 0 (rule: 20 of 20 equal (swallow sets, tallies, every pinned line)) | 20 | printed SWALLOWED lines no registered group claims -- §1's false accusations; every `corpus/rust/*` case with … | none |
| H2 | 0 (rule: exactly 5 SWALLOWED groups at the record's five sites; 0 differences; the tally line byte-identical) | 5 | site-table differences (missing + extra + count diffs), of the record's sites; `sensorium exceptions <the A ru… | none |
| H3 | 0 (rule: every tally line byte-identical and every swallow count equal — 0 of 288) | 288 | per-process comparisons that differ (a tally line or a swallow count), of the comparisons made; `sensorium exc… | none |
| H4 | 0 (rule: the record's per-site tables reproduced — 0 differences; the summed tallies equal; header counts 144 / 114 / 30) | 2 | site-table differences summed over both invocation answers; compared against the PUBLISHED E6⁗ record (`docs/s… | none |
| H5 | 0.581 (rule: both answers under 60 s) | 2 | the SLOWEST of the two answers, seconds, of the arms timed; wall of H4's two `exceptions <invocation-id>` comm… | none |
| H6 | 0 (rule: the Python suite green and byte-identical expectations; the Rust workspace green) | None | `pytest -q` exit status -- 0 is green; the whole Python suite from the repo root under `plain_env()` plus `SEN… | none |

### H2 — the grouped view of the A run, at the site grain

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| site-table differences (the gate) | 0 | 5 | site-table differences (missing + extra + count diffs), of the record's sites; `sensorium exceptions <the A ru… | none |
| SWALLOWED groups printed | 5 | 14 | SWALLOWED groups printed, of the chains they account for -- §1 predicts 5 groups over 14 chains | none |
| chains those groups account for | 14 | 14 | chains the groups account for, of the record's SWALLOWED lines; `sensorium exceptions <the A run> --limit 1000… | none |
| the tally line is the record's | True | None | the printed `dispositions:` line is byte-identical to the record's for this process | none |
| sinks the join could not resolve | 0 | 5 | SWALLOWED groups whose sink event the trace does not hold -- anything but 0 is a hole in the comparison, not a… | none |

Command: `sensorium exceptions 20260905-091115-5da3dc --limit 100000` on run `20260905-091115-5da3dc` (exit 0, 0.083 s, 4701 bytes over 41 lines).  
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
| site-table differences over both arms (the gate) | 0 | 2 | site-table differences summed over both invocation answers; compared against the PUBLISHED E6⁗ record (`docs/s… | none |
| `ws`: site-table differences | 0 | 91 | missing + extra + count diffs against the record's per-site table, of its sites; `sensorium exceptions <the ws… | none |
| `ws`: merged SWALLOWED groups | 103 | 91 | merged SWALLOWED groups printed, of the record's sites; `sensorium exceptions <the ws invocation id> --limit 1… | none |
| `ws`: chains they account for | 782 | 782 | chains the groups account for, of the record's SWALLOWED lines; `sensorium exceptions <the ws invocation id> -… | none |
| `ws`: the summed tally is the record's | True | None | the printed `dispositions:` counts equal the record's SUM over its per-process tally lines; `sensorium excepti… | none |
| `ws`: the header's counts are the record's | True | 144 | the header's `N processes, k with Err chains, m with none` against the record's process count, its processes W… | none |
| `ws`: members named INCOMPLETE | 0 | 144 | members the answer named INCOMPLETE, of the members | none |
| `ws`: sinks the join could not resolve | 0 | 103 | groups whose sink event the named trace does not hold -- a hole, not a difference | none |
| `ws0`: site-table differences | 0 | 98 | missing + extra + count diffs against the record's per-site table, of its sites; `sensorium exceptions <the ws… | none |
| `ws0`: merged SWALLOWED groups | 105 | 98 | merged SWALLOWED groups printed, of the record's sites; `sensorium exceptions <the ws0 invocation id> --limit … | none |
| `ws0`: chains they account for | 812 | 812 | chains the groups account for, of the record's SWALLOWED lines; `sensorium exceptions <the ws0 invocation id> … | none |
| `ws0`: the summed tally is the record's | True | None | the printed `dispositions:` counts equal the record's SUM over its per-process tally lines; `sensorium excepti… | none |
| `ws0`: the header's counts are the record's | True | 144 | the header's `N processes, k with Err chains, m with none` against the record's process count, its processes W… | none |
| `ws0`: members named INCOMPLETE | 0 | 144 | members the answer named INCOMPLETE, of the members | none |
| `ws0`: sinks the join could not resolve | 0 | 105 | groups whose sink event the named trace does not hold -- a hole, not a difference | none |

`ws`: `sensorium exceptions 20260905-091115-9e8e5a --limit 100000` (exit 0, 0.565 s, 129355 bytes over 936 lines).  
`ws` header: `144 processes, 114 with Err chains, 30 with none`; tally `{'swallowed': 782, 'panicked': 2, 'ambiguous': 330}` against the record's summed `{'swallowed': 782, 'ambiguous': 330, 'panicked': 2}`; vary lines `{'messages': 39, 'origins': 11, 'routes': 11}`.  
`ws0`: `sensorium exceptions 20260905-091209-bfa73c --limit 100000` (exit 0, 0.581 s, 126645 bytes over 916 lines).  
`ws0` header: `144 processes, 114 with Err chains, 30 with none`; tally `{'swallowed': 812, 'panicked': 2, 'ambiguous': 300}` against the record's summed `{'swallowed': 812, 'ambiguous': 300, 'panicked': 2}`; vary lines `{'origins': 11, 'messages': 38, 'routes': 11}`.  

### H5 — is the invocation view usable?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| the slower of the two answers, s | 0.581 | 2 | the SLOWEST of the two answers, seconds, of the arms timed; wall of H4's two `exceptions <invocation-id>` comm… | none |
| walls, per arm | {'ws': 0.565, 'ws0': 0.581} | 2 | wall of H4's two `exceptions <invocation-id>` commands, 60 s kill ARMED; a kill is recorded as a kill, never r… | none |
| arms the 60 s kill fired on | 0 | 2 | arms the 60 s kill fired on -- any is a STOP on H5 | none |

### H6 — did anything else move?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| `pytest -q` exit status (the gate) | 0 | None | `pytest -q` exit status -- 0 is green; the whole Python suite from the repo root under `plain_env()` plus `SEN… | none |
| the suite's summary line | 1301 passed, 1 skipped in 110.29s (0:01:50) | None | the suite's own summary line, recorded whole | none |
| `cargo test --workspace` exit status | 0 | 38 | `cargo test --workspace` exit status, of its `test result:` lines | none |

`cargo test` results: `['test result: ok. 238 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.98s', 'test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.26s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.18s', 'test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.72s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.27s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 65 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s', 'test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 28 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.10s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s', 'test result: ok. 38 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.10s', 'test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.53s', 'test result: ok. 0 passed; 0 failed; 7 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 12 ignored; 0 measured; 0 filtered out; finished in 0.00s']`; the driver's sha256 afterwards `50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f`.  
Python logs `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/acceptance-grain-repair/logs/h6/h6-pytest.log`; cargo logs `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-05-sensorium-rung4-entry-grain/acceptance-grain-repair/logs/h6/h6-cargo.log`; the only variables set for the suite: `['PYTHONDONTWRITEBYTECODE', 'SENSORIUM_CARGO_SENSORIUM']`.


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

**144 per-process answers versus one invocation answer**: 182334 bytes over 1634 lines, against 129355 bytes over 936 lines. both halves measured by THIS run, under 0.8.2

**Vary lines that fired, by kind** (an honesty count, not a gate): `{'origins': 38, 'messages': 152, 'details': 0, 'routes': 38}` — summed over every answer this run read: H2, H3/ws, H3/ws0, H4/ws, H4/ws0. blocks that printed a vary line, summed over EVERY answer this run read and named in `vary_counted_over` (H2, H3/ws, H3/ws0, H4/ws, H4/ws0); every spelling is reported, so a kind at 0 printed none rather than going unlooked-at; an honesty count, not a gate

**Shapes that named their file** (R-G12, an honesty count, not a gate): `{'H2': 0, 'H3/ws': 0, 'H3/ws0': 0, 'H4/ws': 6, 'H4/ws0': 4}`. printed blocks whose site parenthetical carries ` in <file>` because their site text named more than one place in THAT answer (R-G12), one number per answer read; an honesty count, not a gate. An answer absent from this map recorded no count rather than a zero.


## 4. Verdicts

Written by hand against §1′'s rules, from the raw record and its logs in the
gitignored plan ledger. One row per §1′ endpoint, with the number that
decided it. The
run was launched ONCE, detached, 19:46:28 → 19:49:12 on 2026-09-05, and
measured once; nothing was re-run, re-scoped or re-classified after a number
was read, and §1′ was not touched — its sha256 is
`e894f473b79c0ee432088b0a913fb01fd4702c2acce9894a134442379ece8015` before and
after (§2), at the amended lock `ae9a15b`.

**No launch failed and none was discarded**: the first record's measurement
needed a second launch after an infrastructure death that measured nothing
(its §5.5); this one did not. There is exactly one `grain-repair.DONE`, exit
0, and no `failed-launch-*` beside it. **The assembly is deterministic over
the raw record**, checked after `.DONE` as the first record checked its own:
`--assemble` re-run once produced a `results.json` byte-identical apart from
the `assembled.at` stamp and a `section-2-3.md` byte-identical outright, with
the raw record's md5 `33c7341ec64d9479a3266d365a54feff` before and after.

| Id | §1′'s rule, verbatim | What was measured | Verdict |
|---|---|---|---|
| H1′ | "**20 of 20 equal** (swallow sets, tallies, and every pinned line)." | **20** `corpus/rust/*` cases with an `exceptions` question, each recorded once under the 0.3.1 driver into a corpus target that was 0 bytes at the start. **0** printed SWALLOWED lines no registered group claims, **0** registered groups with no printed line, **0** unequal swallow sets, **0** unequal `dispositions:` lines, **0** swallow cases that printed nothing, and the corpus's own substring reading fails **0** of 20 — against the pins §1′ names as updated BY RULE (§4.5). | **PASS** |
| H2′ | "**Exactly 5 SWALLOWED groups**, counts `memory.rs:156 ×3, task/exec.rs:606 ×4, memory/store.rs:96 ×2, task/registry.rs:1084 ×4, task/registry.rs:379 ×1`; tally line byte-identical to the record's (`dispositions: swallowed 14, ambiguous 8`)." | **5** SWALLOWED groups accounting for **14** chains on the kept `a` store, at exactly the five sites with exactly the five counts §1′ names — **0** differences over the record's 5 sites, **0** sinks the join could not resolve, **0** blocks disambiguated. Printed tally `dispositions: swallowed 14, ambiguous 8`, byte-identical to the record's. The whole answer is byte-identical to the first measurement's (§4.1). | **PASS** |
| H3′ | "**Every tally line byte-identical** to the record's per-process `tally_line` (114 + 114 processes with chains; the 30 + 30 without print `no exceptions recorded`), and per trace the sum of SWALLOWED group counts == the record's `swallowed_count`." | **288** per-process comparisons — every trace of `ws` and of `ws0` — with **0** differences: **0** tally lines that are not the record's and **0** swallow counts that are not the record's, on each arm. 114 processes per arm printed a tally line and 30 printed `no exceptions recorded`, with **0** INCOMPLETE banners and **0** blocks disambiguated. Chains sum to **782** and **812**, the record's own totals. Every one of the 288 answers is identical to the first measurement's in bytes, lines, tally, groups and chains (§4.2). | **PASS** |
| H4′ | "**ws: exactly 91 SWALLOWED shapes, one per (file, line) site, whose (site, count) multiset equals the record's 91-row table (782 chains); ws0: exactly 98 shapes / 812; the summed `dispositions:` line, in the tool's `TAG_ORDER`, reads `swallowed 782, panicked 2, ambiguous 330` (ws) and `swallowed 812, panicked 2, ambiguous 300` (ws0); header counts 144 / 114 / 30; INCOMPLETE members 0.**" (its ungated `Reported:` clause — the collision count — is §5.6) | **0 site differences on each arm, 0 in all.** `ws`: **103** merged shapes accounting for **782** chains over **91** distinct sites against the record's 91 — 0 missing, 0 extra, 0 count differences, **0** chains booked at a sibling file. `ws0`: **105** shapes, **812** chains, **98** sites against 98 — 0 / 0 / 0. The summed `dispositions:` lines print byte-identical to §1′'s two quoted strings; header counts **144 / 114 / 30**; INCOMPLETE members **0**; unresolved sinks **0** (§4.3). **The one clause that missed is the shape COUNT: 103 ≠ 91 and 105 ≠ 98, and shapes are not one-per-site — §5.2.** | 0 site differences per arm — **PASS** under the gate reading (the site multiset, the instrument's committed rule); **STOP** under the strict reading (103 / 105 shapes ≠ 91 / 98) — ruling: **Brice** (§5.2) |
| H5′ | "**Both under 60 s.**" | **0** arms at or over the ceiling: `ws` **0.565 s**, `ws0` **0.581 s**, neither killed, both exit 0 — 144 traces opened and merged per answer (§4.4). | **PASS** |
| H6′ | "**Python `exceptions` output byte-identical to 0.8.1** (the suite is the pin; no Python expectation changes); Rust workspace green; v17's single-shape blocks byte-identical." | `pytest -q` exit **0**: **1301 passed, 1 skipped** in 110.3 s, with no Python expectation changed by this slice — the suite carries the vectors v01–v19, the Python corpus and `tests/test_exceptions*.py`, and it is the pin. `cargo test --workspace` exit **0**: **38** `test result: ok.` lines, **606 passed, 0 failed, 19 ignored** (§4.6). | **PASS** |

**Overall: five PASS, and H4′'s verdict depends on the reading (§5.2).** Not in
doubt is that the repair did its one job and moved nothing else. The first
record's H4 STOP was 4 site differences per arm — 11 chains of 782 and 10 of 812
booked at a sibling test file, invisibly to a reader. Under R-G12 that number is
**0 on both arms**. Everywhere the first record already reproduced the published
E6⁗ record — the A run, all 288 per-process answers, all 20 corpus cases — this
run reproduces it again, identically rather than merely equivalently: H2′'s
answer has the same sha256, and all 288 per-process answers match in bytes,
lines, tally, groups and chains. **Only the two invocation views changed**, by +3
and +2 blocks, where the collisions were. What did NOT come true is §1′'s
prediction of how MANY blocks that would take: 91 and 98 predicted, 103 and 105
measured. The addressing is exact; the block count is not the site count and
never could have been. H4′ therefore reads **PASS** under the gate reading and
**STOP** under the strict one; which binds is **Brice's ruling**, and no number
here turns on it (§5.2).

### 4.1 H2′ — the A run's five shapes, at the site grain

`sensorium exceptions 20260905-091115-5da3dc --limit 100000` on the kept `a`
store: exit 0, 0.083 s, 4701 bytes over 41 lines. Five SWALLOWED groups over
14 chains, each booked at the sink its verdict names through the trace's own
`events` → `code_objects` join, at exactly §1′'s five sites with §1′'s five
counts (the table is §3's): 0 missing, 0 extra, 0 count differences, 0
unresolved sinks, **0 blocks carrying a file basename** — nothing here
collides, so R-G12 prints nothing new. The stdout is **byte-identical to the
first measurement's** (sha256 `ff7d0ac8449e…`), the first half of the
control.

### 4.2 H3′ — 288 per-process comparisons, both arms

One `exceptions <run> --limit 100000` per trace, 144 per arm, each compared
against the record's `tally_line` and `swallowed_count` for that process:

| | `ws` | `ws0` |
|---|---|---|
| processes read (runs only in the store / only in the record: 0 / 0) | 144 | 144 |
| tally lines that are not the record's | **0** | **0** |
| swallow counts that are not the record's | **0** | **0** |
| processes that printed `no exceptions recorded` | 30 | 30 |
| processes with a tally line | 114 | 114 |
| processes carrying an INCOMPLETE banner | 0 | 0 |
| SWALLOWED groups printed | 168 | 177 |
| chains those groups account for | **782** | **812** |
| blocks that named their file (R-G12) | **0** | **0** |
| total output | 182 334 bytes / 1634 lines | 179 431 bytes / 1615 lines |
| slowest single answer | 0.076 s | 0.071 s |

Those totals are the first measurement's to the byte, and so is every row
above them: process by process, all **288** answers match it in bytes, lines,
tally line, groups and chains — the second half of the control. No
per-process answer holds a site text naming two places, so none changed. That
**closes by construction** the caveat the first record's fix round 1 needed a
read-only trace sweep for: that view used the same file-less key and was
un-hit only empirically.

### 4.3 H4′ — the invocation view against the record's per-site tables

`ws`: `sensorium exceptions 20260905-091115-9e8e5a --limit 100000`, exit 0,
0.565 s, 129 355 bytes over 936 lines.
`ws0`: `sensorium exceptions 20260905-091209-bfa73c --limit 100000`, exit 0,
0.581 s, 126 645 bytes over 916 lines.

| | `ws` | `ws0` | the first record's `ws` / `ws0` |
|---|---|---|---|
| merged SWALLOWED shapes printed | 103 (§1′ predicted 91) | 105 (§1′ predicted 98) | 100 / 103 |
| chains they account for | **782** = the record's | **812** = the record's | 782 / 812 |
| distinct sites the shapes resolve to | **91** | **98** | 89 / 96 |
| the record's sites | 91 | 98 | 91 / 98 |
| **site differences (the gate)** | **0** | **0** | **4 / 4** |
| sites missing | **0** | **0** | 2 / 2 |
| sites extra | **0** | **0** | 0 / 0 |
| sites with a different count | **0** | **0** | 2 / 2 |
| chains booked at the wrong file | **0 of 782** | **0 of 812** | 11 of 782 / 10 of 812 |
| header `N processes, k with Err chains, m with none` | `144, 114, 30` — the record's | `144, 114, 30` — the record's | same |
| summed `dispositions:` counts | `swallowed 782, panicked 2, ambiguous 330` | `swallowed 812, panicked 2, ambiguous 300` | same |
| INCOMPLETE members | **0** | **0** | 0 / 0 |
| sinks the join could not resolve | **0** | **0** | 0 / 0 |
| distinct processes the brackets NAME | 44 | 50 | 43 / 49 |
| blocks carrying a file basename (R-G12) | **6** | **4** | not printable |

`compare.missing`, `compare.extra` and `compare.count_diffs` are the empty
list on both arms — the whole of the gate: the (site, count) multiset the
answer resolves to IS the published record's 91-row and 98-row table.

**The six and four blocks that name a file are exactly the collisions the
first record diagnosed**, printed apart at last. From the `ws` answer, the
six blocks, with only the trailing `, which returned ok` elided at the `…`:

```
SWALLOWED -- absorbed by sink_let_underscore at e5 (sandbox L42 in task_exec_read_find_test.rs) in f2 …  [×8 over 1 process: first e5 in 20260905-091125-80bdb1, +7]
SWALLOWED -- absorbed by sink_let_underscore at e24 (sandbox L42 in task_exec_read_find_test.rs) in f16 …  [in 20260905-091125-80bdb1]
SWALLOWED -- absorbed by sink_let_underscore at e3 (sandbox L42 in task_exec_run_test.rs) in f2 …  [×8 over 1 process: first e3 in 20260905-091125-80c4ab, +7]
SWALLOWED -- absorbed by sink_let_underscore at e26 (sandbox L42 in task_exec_run_test.rs) in f16 …  [in 20260905-091125-80c4ab]
SWALLOWED -- absorbed by sink_let_underscore at e5 (fresh_dir L64 in pager_refusal_advice_test.rs) in f4 …  [in 20260905-091125-815542]
SWALLOWED -- absorbed by sink_let_underscore at e10 (fresh_dir L64 in api_native_agent_delete_test.rs) in f4 …  [×2 over 1 process: first e10 in 20260905-091125-fc4de2, +1]
```

8 + 1 = **9** chains at `task_exec_read_find_test.rs:42` and 8 + 1 = **9** at
`task_exec_run_test.rs:42` — the record's 9 and 9, where the first
measurement booked all 18 at the first file; 1 at
`pager_refusal_advice_test.rs:64` and 2 at
`api_native_agent_delete_test.rs:64` — the record's 1 and 2, where the first
measurement booked all 3 at the first file. Every merged bracket in the six
now reads `over 1 process`: none is a cross-file merge any more. `ws0` prints
the same four sites in FOUR blocks (`fresh_dir L64` ×2 in
`20260905-091219-04e884` and 1 in `…-093072`; `sandbox L42` ×9 in `…-094ebf`
and ×9 in `…-09573f`) against `ws`'s six, which is the whole of why `ws`
gains 3 shapes and `ws0` 2: on `ws` the `sandbox` chains were ALREADY two
blocks (the first record's `[×16 …]` and `[×2 …]`, split by absorbing frame
`f2` / `f16`, each merging both files) and each split in two, +2, with
`fresh_dir`'s single block splitting for +1; on `ws0` `sandbox` was one block
of 18 and `fresh_dir` one of 3, +1 each. The arithmetic closes: 100 → 103 and
103 → 105, +9 and +6 lines, +1188 and +825 bytes, +1 named process per arm.
**A key that gains a component can only split shapes, never merge them** —
which is also why §1′'s 91 and 98 were unreachable from 100 and 103 (§5.2).

### 4.4 H5′ — the walls

| arm | wall | kill armed | killed |
|---|---|---|---|
| `ws` | **0.565 s** | 60 s | no |
| `ws0` | **0.581 s** | 60 s | no |

144 traces opened, read and merged per answer in about six tenths of a
second, against §1′'s ≈10 s derivation and a 60 s ceiling — roughly 103 times
under it. Both exit 0; the kill fired on neither arm. Both are slightly
slower than the first measurement's (0.530 / 0.515) on a box at a higher load
(0.95 against 0.56 at H4's start), but H5′ gates a ceiling, not a comparison,
and nothing here is read as a regression.

### 4.5 H1′ — the corpus, against the pins updated BY RULE

Twenty `corpus/rust/*` cases carry an `exceptions` question. Each was copied
into its own workdir, recorded once with the 0.3.1 driver into a corpus
target that was 0 bytes at the start (255 849 766 bytes afterwards), and
answered from its own `<workdir>/.sensorium` store — so the fresh
`SENSORIUM_DIR` §1′ requires stayed empty, and §2 records that it did.

All six of the collector's counts are **0 of 20**: no printed SWALLOWED line
no registered group claims, no registered group with no printed line, no
unequal swallow set, no unequal `dispositions:` line, no swallow case that
printed nothing, no failure of the corpus's own substring reading. The
per-case table is §3's; the five files §1′ names as moved BY RULE
(`err_stored`, `err_rendered_into_value`, `v18`, `v17`,
`tests/test_exceptions_rust_gate.py`) are inside that 20 of 20. R-G12 changes
nothing here: a single-process case has no cross-process merge to
disambiguate, and all twenty print the tally the first measurement read.

### 4.6 H6′ — did anything else move?

| | value |
|---|---|
| `pytest -q` (whole suite, from the repo root) | exit **0** — `1301 passed, 1 skipped in 110.29s` |
| `cargo test --workspace` (in `rust/`, same target) | exit **0** — 38 `test result: ok.` lines |
| Rust tests, summed over those lines | **606 passed, 0 failed, 19 ignored** |
| driver sha256 after H6′ | `50e3264c45d5c4f7faec1708730352968ea1dd1f8e4ebab1b7e0dcaf707ad40f` — the sha the preflight recorded (the only variables set for the suite: `PYTHONDONTWRITEBYTECODE`, `SENSORIUM_CARGO_SENSORIUM`) |

The Python suite is the pin for the REPAIR too — vectors v01–v19 including
v17's single-shape blocks and v18's ambiguous merge, the Python corpus,
`tests/test_exceptions*.py` — and it is green with no expectation changed by
this slice: `a86d67e`, `166a0c8` and `34ab82e` touch
`src/sensorium/query/exceptions_*.py` and ADD tests, editing no vector, no
`corpus/*/questions.yaml` and no existing expectation. 1276 → 1301 as those
three and the sibling runner's test module added tests. `cargo test
--workspace` compiled nothing, and the driver's sha256 afterwards is the
preflight's, so H1′, which ran before H6′, ran the binary §2 pins.

## 5. Gaps

### 5.1 What the repair changed, and the control that says it changed nothing else

The first record's H4 STOP was one mechanism: the shape key was verdict +
qualname + line with **no file**, so two processes whose helper shared a
qualname *and* a line merged into one block naming only the first member's
file. Under R-G12 the key is the site event's own identity —
`(file, line, qualname)` off its code object — and where one answer prints
two shapes whose site text collides, each verdict carries the file's
basename. Measured against the published E6⁗ record, the move is §4.3's
last column: sites resolved 89 → **91** of 91 and 96 → **98** of 98, site
differences 4 / 4 → **0 / 0**, chains booked at a sibling file 11 of 782 and
10 of 812 → **0 / 0**, shapes printed 100 / 103 → 103 / 105, and blocks
naming their file 6 and 4 where the first build could not print one.

Every one of those traces to a field in the two raw records:
`raw_h4.arms.<arm>.compare.measured_sites` (89 → 91, 96 → 98),
`compare.differences` (4 → 0), `compare.missing` / `extra` / `count_diffs`
(each a two-element list → the empty list), `raw_h4.arms.<arm>.groups`
(100 → 103, 103 → 105) and `raw_h4.arms.<arm>.disambiguated` — a field the
first instrument did not have, published per answer in `results.json` as
`reported.disambiguated_shapes`.

**And the control is discriminating** — a repair that moved the site
attribution could have moved anything else, and this one did not:

* **H2′'s whole answer is byte-identical** to the first measurement's —
  sha256 `ff7d0ac8449e…` on both.
* **All 288 per-process answers are identical** in bytes, lines, tally line,
  groups and chains, arm totals included (182 334 / 1634 and 179 431 / 1615).
* **Zero blocks named a file** in any of those 289 answers
  (`disambiguated_shapes` = `{'H2': 0, 'H3/ws': 0, 'H3/ws0': 0, 'H4/ws': 6,
  'H4/ws0': 4}`): no site text in any of them names two places.
* The only two answers that moved are the invocation views, by exactly the
  collisions: +3 and +2 shapes, +9 and +6 lines, +1188 and +825 bytes, +1
  named process each.

The change fires where the defect was and nowhere else — the evidence shape
the E6⁗ borrow repair called for. It also **closes by construction** what the
first record's fix round 1 could only establish empirically: the per-process
view used the same file-less key and was un-hit here as a matter of fact; it
is now un-hit because the key carries the file.

### 5.2 §1′ asserted one shape per site, and that clause was unreachable before it was locked

§1′'s H4′ endpoint opens *"ws: exactly 91 SWALLOWED shapes, one per (file,
line) site …; ws0: exactly 98 shapes"*. Measured: **103 and 105**, over 91 and
98 sites, with the (site, count) multiset exact. Twelve `ws` blocks and seven
`ws0` blocks share a site with another block, because a shape is not a site:
one site can carry several, split by the absorbing frame, the verdict or the
`how` (§4.3 shows both `sandbox L42` files doing it on `ws`).

This is the first record's §5.2 **repeated**, and its §5.8 asked the successor
not to repeat it: *"whose §1 … also carries the two clauses §5.2 and §5.3
falsified here: the summed tally stated in the tool's own `TAG_ORDER`, and group
count predicted == site count rather than assumed equal to it."* §1′'s preamble
claims that was done — *"H4′'s endpoint states the multiset the repaired key
predicts (one shape per `(file, line)` site)"* — but the endpoint sentence still
spells the equality as a requirement.

**And this time the clause could not have come true.** §1′ was locked AFTER the
first measurement, which had already published 100 `ws` shapes and 103 on `ws0`;
adding a component to a key can only SPLIT shapes, never merge them, so the
counts could only rise and no outcome could have produced 91 and 98. A clause no
result can satisfy does not discriminate; §1′ carried one.

**Both readings, and how §4 reports them.**

* **Strict conjunctive** — every clause must hold. It does not: 103 ≠ 91 and 105
  ≠ 98. H4′ is then a **STOP** with 0 site differences and the wrong block count.
* **The gate reading** — the endpoint is the (site, count) multiset and the shape
  count a prediction beside it. H4′ is then a **PASS**, 0 differences per arm.

§4's cell carries BOTH and names **Brice** as the ruler. It puts the gate
reading first, on three things that all **predate the lock and the number**: (1)
H4′'s Question column asks *"Does the invocation view reproduce the record's
per-site table?"* — the table, not the block count; (2) the instrument's
operationalisation of H4 is committed in `4525227`, before either lock, where
`render_grain.py:41` prints §3's headline rule as *"the record's per-site tables
reproduced — 0 differences; the summed tallies equal; header counts 144 / 114 /
30"* — no shape count in it — and `:199` labels the headline measurement
*"site-table differences over both arms (the gate)"*; (3) the first record
decided the identical clause the same way on the same instrument — *"It is
recorded here, not repaired, and it is not the reason H4 stopped"* (its §5.2) —
where it cost nothing, since both readings said STOP. Here it costs the verdict,
which is why the reading is argued from evidence older than the number rather
than chosen after it, and why the verdict cell states both and defers.

**No number in §3 or §4 depends on which reading binds**: 0 site differences per
arm, 103 and 105 shapes, 91 and 98 sites, either way. If Brice takes the strict
reading, H4′ is a STOP at 103 / 105 and the slice ships with two STOP records —
and §1′ is still never edited to make it otherwise. What a correctly stated H4′
would have said: *the (site, count) multiset equals the record's table; the shape
count is REPORTED, expected to be at least the site count and at least the first
measurement's 100 / 103* — a sentence for a third pre-registration, written here
rather than into §1′.

### 5.3 Of the two clauses the first record sent forward, one landed

§1′ was asked to fix two things the first measurement falsified, and the
tally one **worked**: §1′ quotes the summed line in the tool's `TAG_ORDER`,
and both arms printed it byte for byte — `dispositions: swallowed 782,
panicked 2, ambiguous 330` and `dispositions: swallowed 812, panicked 2,
ambiguous 300` — so the reading ambiguity the first record had to adjudicate
twice (its §5.3) does not exist here. The shape-count one did not land
(§5.2). Two clauses sent forward, one arrived: this loop's measured rate at
carrying its own corrections, worth a line in the next plan.

### 5.4 What this run did not measure

* **No program was measured.** This slice changes what `exceptions` prints
  and no crate; `cargo-sensorium` stays 0.3.1, unrebuilt. Every number about
  the workspace under measurement — the 91- and 98-row site tables, the 288
  tally lines, the swallow counts — is the PUBLISHED E6⁗ record's, read at
  `605db64` (sha256 in §2) and never re-measured; no endpoint is filled from
  it.
* **The first record was not re-measured.** Its numbers appear only in
  §4.3's comparison column, read from its archived raw record; its H4 stays
  STOP at 4 differences per arm.
* **0.8.1 was not run.** The busiest-process before-bytes are the record's
  `sweep_processes[]` row; it carries no LINE count for 0.8.1, so that half
  of §3's ungated row is absent rather than derived.
* **Nothing was dropped.** Every `{value, n, lens, dropped}` cell in
  `results.json` carries a value; none is null, none carries both.
* **The kept stores were read, not written** — 1 / 144 / 144 files and
  581 632 / 1 032 368 128 / 1 032 294 400 bytes before and after, checked by
  hand as well as by the runner; the one write is the audit log's 1/145/145.
* **No wall was gated except H5′'s**: H2′ 0.083 s, the 288 per-process
  answers 9.36 s per arm, H1′'s twenty recordings 23 s, H6′'s pytest 110 s,
  `cargo test` 10 s — none an endpoint or a comparison.

### 5.5 One launch

The first measurement needed two (its §5.5: an infrastructure death that
asked for no `exceptions` answer, licensed by `audit rows added {'a': 0,
'ws': 0, 'ws0': 0}`). This one was launched once and finished once: pid
3896233, `grain-repair.DONE` with `exit=0`, 19:46:28 → 19:49:12. Nothing was
read before the marker, nothing was killed, `pkill` was not used, and there
is no `failed-launch-*` directory and no partial record. The rule that
licensed the first relaunch was never exercised — said here rather than left
to be inferred from an absence.

### 5.6 Reported without a gate

Restated from §3 with the set each number was counted over:

* **The busiest `ws` process** (`20260905-091125-fc7302`): **20 166 bytes
  under 0.8.1 → 3360 bytes** over 32 lines under 0.8.2 — **6.0×**, the same
  54 chains as 3 groups. The 0.8.1 figure is the record's, never re-measured;
  this process holds no colliding site text, so R-G12 left its answer alone.
* **144 per-process answers versus one invocation answer**: **182 334 bytes
  over 1634 lines** against **129 355 bytes over 936 lines** — 1.41× the
  bytes, 1.75× the lines, both halves measured by this run under 0.8.2. The
  comparison is closer to like for like than the first record's: the one
  answer no longer loses the per-file attribution the 144 carry, which cost
  it 1188 bytes and 9 lines.
* **Vary lines that fired, by kind**, over every answer this run read (H2′,
  H3′/`ws`, H3′/`ws0`, H4′/`ws`, H4′/`ws0` — **1287** printed blocks):
  `messages` **152**, `origins` **38**, `routes` **38**, `details` **0** —
  identical to the first measurement's counts over 1282 blocks; the five
  extra blocks are the split shapes and none printed a vary line. `details
  vary` **still never fired**, unexercised here too. The 1287 and 1282
  denominators are **not** a `results.json` field: they are counted from the
  phase logs with `parse_shapes` (11+385+383+256+252 here, 11+385+383+253+250
  for the first run), as the first record's §5.6 did.
* **Blocks that named their file** (R-G12): `{'H2': 0, 'H3/ws': 0,
  'H3/ws0': 0, 'H4/ws': 6, 'H4/ws0': 4}` — §1′ expected ≥ 2 per invocation
  arm (`sandbox L42`, `fresh_dir L64`); both clear it. An answer absent from
  that map recorded no count rather than a zero; none is absent.

### 5.7 Residuals found by this run, recorded and not repaired

1. **`results.json` named the wrong document — REPAIRED at its derivation
   (ruling R-G15).** `assemble_grain` published the module constant `DOC`, the
   FIRST record's path, so this record's `acceptance` attributed its numbers to
   the record it exists to repair while `byte_lock.doc` two keys below named the
   right one. Fixed 2026-09-05 in `e9f050d`, which DERIVES it from the raw
   record's own `byte_lock.doc` — what `assembled.note` already claimed of every
   value in the file. Re-assembled ONCE from the UNTOUCHED raw file (md5
   `33c7341ec64d9479a3266d365a54feff` before and after), **exactly two leaf paths
   changed: `acceptance` and `assembled.at`** — no phase re-ran, no number moved.
   The FIRST record is unaffected: its `byte_lock.doc` IS `DOC`, and re-assembling
   it with and without the change gives the identical diff against its file.
2. **Two prose literals and one self-contradicting sentence remain, struck in
   place and carried as debt.** `render_grain` hardcodes the raw record's name
   (`:60`) and prints the ids unprimed (`:327`); its byte-lock sentence says *"§1 was committed ALONE and never amended: there is no second sha"* and
   then interpolates the second sha (`:75`) — written for the unamended case this
   record is the first to fall outside. **The same false sentence stood in this
   document's own header prose**, struck and corrected there too, above `## 1`
   and outside the locked range, so §1′'s sha is unmoved. Not
   repaired now — `OVERRIDES` covers the runner's literals, not its
   collaborators', and that boundary is the debt.
3. **The invocation header's `panics:` line counts events, not the tally's
   tag** — both arms print `panics: 8 recorded` beside `panicked 2`, as in
   the first record's §5.7 item 4; untouched by R-G12.
4. **The header calls blocks "sites".** `ws` prints *"raised (1114 chains
   over 114 processes, **103 swallowing sites**)"* and `ws0` 105, where the
   published record has 91 and 98 SITES — §5.2's conflation shipped in the
   output rather than only in a pre-registration, and R-G12 widens the gap it
   names (100 vs 91 → 103 vs 91) precisely by making the addressing right.
   The first record deferred the neighbouring `1 swallowing sites` grammar at
   S = 1; this is another edge of the same word. Not repaired.
5. **The suite's skip count still depends on one variable** (`1293 passed, 9
   skipped` without `SENSORIUM_CARGO_SENSORIUM`, `1301 passed, 1 skipped`
   with it) — both seen today, in the preflight and inside H6′.

And the ones earlier records carry that this run did not touch: rung-3's R16
(v) by-value handoff blind spot and design B2's `self.record(&e);` side
channel. Neither had exposure here and this run falsifies neither.

### 5.8 What this record licenses, and what it does not

It licenses design N3 **as amended by R-G12** at the site grain: on this
workspace, over these two invocation answers and these 288 per-process ones,
the key `(file, line, qualname)` reproduces the published E6⁗ record's
per-site tables exactly — 0 differences per arm where the file-less key read
4 — leaving every answer with nothing to tell apart byte-identical.

It does **not** license any of the following, and none is done here:

* **Re-opening the first record.** Its H4 stays STOP with 4 site differences
  per arm, its §1 stays locked at `05c3124`, and nothing here amends it — two
  records, two locks, two measurements, each taken once.
* **A third measurement.** Whatever reading of §1′'s shape-count clause binds
  (§5.2), this run is the repair's one measurement. The clause is not
  repaired by editing §1′; a corrected H4′ would be a NEW pre-registration in
  a NEW document, measured once — the first record's §5.8 rule applied to
  itself.
* **Any claim about a program.** No crate changed, `cargo-sensorium` stayed
  0.3.1 and unrebuilt, and every number about the workspace under measurement
  is the published record's.
* **Any claim beyond this workspace.** Two collisions exist here and both
  were repaired; three helpers at one `(qualname, line)`, or a collision
  inside one process, is untested — §5.1's "un-hit by construction" is a
  claim about the key, not a measurement of such a workspace.
