# Rung 4, slice 2 — `refocus` for Rust traces, and E4

**Date:** 2026-09-07 · **Status:** design, approved section by section in
conversation (Brice, 2026-09-07) · **Design authority:** Claude · **Base:**
main `2883a50` (Python 0.8.3; crates rt 0.4.0 / transform 0.4.0 / driver
0.4.0) · **Branch:** `feat/rung4-refocus`

Slice 1 (`docs/superpowers/specs/2026-09-06-sensorium-rung4-focus-tier-design.md`,
merged as PR #19) gave Rust traces LINE events and locals under a
compile-time `--focus`. This slice closes rung 4: `sensorium refocus` works
on a Rust trace by re-invoking the original `cargo sensorium` command under
an added focus and comparing the pair, and the pre-registered E4 row of the
recorder design (`docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md`
§13, row E4 — "refocus MATCH rate on the 7 `pager_*_test.rs` FakeSubstrate
files, per test with `--exact`, expected-MATCH list written first") is
measured.

## 0. Rulings this design rests on

| # | Question | Ruling (Brice, 2026-09-07) | Why |
|---|---|---|---|
| G1 | does the brace-macro tail guard land here? | **yes** — the one-line `is_tail` check in the transform's macro arm, its golden flipped from compile-fail to compile-pass | slice 2's focused builds run through the transform and slice 2 has its own pre-registered measurement, so the records stay honest; the inference-variable limitation stays declared (no stable-Rust fix) |
| G2 | where does `refocus` for Rust live? | **Python's re-run path** | one comparator, one verdict vocabulary, capability dispatch as today; the driver learns one flag |
| G3 | how does Python learn the new trace? | **`--refocus-of <run>` on the driver + a store lookup** on `refocus_of` | the link is durable in both traces and read by `info`/`runs` the same way for both languages; nothing parsed from stdout is load-bearing |

Two approaches were rejected for G3: parsing the driver's `run:` lines
(a link that lives only in Python's memory; a changed print silently breaks
refocus) and a `--json` driver flag (a new surface for one consumer).

## 1. What ships

1. Driver: `cargo sensorium --refocus-of <run-id> [--focus …] test|run …`;
   `refocus_of` in every produced process's meta; the flag validated
   against the current store.
2. Converter: `workspace_root`, `refocus_of`, `invocation_processes` in
   meta; `capabilities.refocus: true` for every trace this driver converts.
3. Python: a Rust branch in `sensorium refocus` — pre-rerun refusals, the
   subprocess re-run from the workspace root under the same store, the pair
   lookup by `refocus_of`, the unchanged comparator, the stamps, and two
   UNVERIFIABLE licence caveats (output, children).
4. The transform guard (G1), `sensorium-transform` 0.4.1.
5. Three Rust corpus cases (`refocus_match`, `refocus_diverged`,
   `refocus_refused_many`), Python tests on fixture traces, the E4 record
   and instrument, docs, versions: driver 0.5.0, transform 0.4.1, runtime
   0.4.0 unchanged, Python 0.8.4, `TRACE_FORMAT` 4 unchanged.

## 2. The re-run path (section 1, approved)

### 2.1 Driver

`--refocus-of <run-id>` is parsed where `--tier` and `--focus` are
(`rust/cargo-sensorium/src/driver_args.rs`), only before the first bare
`--`, at most once (a second occurrence refuses: `--refocus-of given twice`,
exit 2). The value must name a trace in the current store
(`$SENSORIUM_DIR/traces/<run-id>.db` exists); otherwise
`REFUSED: --refocus-of <run-id> names no trace in <store>; nothing was
built.`, exit 2, before any rewrite or build. The value is recorded in
`invocation.json` (`refocus_of`) and reaches the converter with the rest of
the invocation record, so every process of the invocation carries
`refocus_of` in its meta. The driver changes in no other way; `--focus`
resolution, the shim path and the mirror stamp are slice 1's.

### 2.2 Converter (`rust/cargo-sensorium/src/convert/meta.rs`)

Three optional meta keys, so `TRACE_FORMAT` stays 4:

| key | value | source |
|---|---|---|
| `workspace_root` | the workspace the invocation ran in | `invocation.json` (today ephemeral only) |
| `refocus_of` | the original run id | `invocation.json`, when `--refocus-of` was given; absent otherwise |
| `invocation_processes` | the number of runner processes this invocation produced | the count the driver already computes for its WARN |

`capabilities.refocus` becomes `true` unconditionally for traces this
driver converts (the recorder CAN be re-invoked); whether one particular
trace can be refocused is a refusal (§2.3), not a capability. `info` prints
`refocus_of` where it prints the Python key.

### 2.3 Python (`src/sensorium/query/refocus_cmd.py`, a Rust branch)

Dispatch on `trace.lang == "rust"` after the capability gate. Everything
below is the Rust branch; the Python branch is untouched.

**Pre-rerun refusals** (exit 2, `BAD_CALL`, nothing launched), in this
order after the existing capability/`incomplete` checks:

| condition | sentence |
|---|---|
| `--window` given | `REFUSED: --window is not available for a Rust trace (rung 4 leaves it out); nothing was re-run` |
| `invocation_processes` absent or ≠ 1 | `REFUSED: run <id> is one of <n> test binaries of its invocation; refocus needs an invocation with a single-target selector (--lib, --test X, --bin X) so one trace is the answer; nothing was re-run` |
| `workspace_root` absent | `REFUSED: run <id> records no workspace_root (recorded by cargo-sensorium 0.4.0 or earlier); nothing was re-run` |
| `workspace_root` gone | `REFUSED: workspace <path> no longer exists; nothing was re-run` |
| no driver | `REFUSED: no cargo-sensorium to re-run with — set SENSORIUM_CARGO_SENSORIUM or put cargo-sensorium on PATH; nothing was re-run` |

The driver is resolved exactly as the corpus runner resolves it
(`SENSORIUM_CARGO_SENSORIUM`, else `cargo-sensorium` on `PATH`).

**The re-run.** argv = `[driver, "--refocus-of", <run>, "--tier", <tier>,
"--focus", v1, "--focus", v2, …, *cargo_args]` where `<tier>` is the
original's `SENSORIUM_TIER` from its recorded `env` (omitted when absent,
so the driver's default `call` applies) and the focus list is the
original's `meta.focus` followed by the caller's `--focus` values, in that
order, de-duplicated by the driver's own set rule — never fewer than the
original's (Python's "only ever captures more"). cwd = `workspace_root`.
Environment: the caller's, with `SENSORIUM_DIR` as resolved for the
original's store (the same store), and nothing else set or stripped — the
environment is diffed afterwards, as for Python. The child's stderr streams
through to the user (a focused rebuild is visible); its stdout is captured
only for the report. No timeout: Python's `refocus` has none, and a cargo
build's length is the user's to judge; the E4 instrument bounds its own
loop.

**The pair.** After the child exits, Python lists the store's traces whose
`refocus_of == <run>` and whose recording started after the launch
timestamp. Exactly one → the pair. Zero (the driver refused, cargo failed
before recording, or the invocation produced nothing) → `verdict: REFUSED`
after the rerun, exit 3, with the driver's exit code and its last stderr
line as the reason. More than one → `REFUSED`, exit 3, naming the count and
the single-target sentence. The driver's `run:` lines are recorded in the
report but decide nothing.

## 3. Verdict, licence, guard (section 2, approved)

### 3.1 Verdict

`diff_cmd.compare(orig, new)` unchanged. For a Rust pair the fingerprints
are per task (a test or a spawned thread) over CALL, RETURN, RAISE and
HANDLED; LINE rows never enter the hash, so the focused re-run's LINE rows
cannot move it. MATCH, DIVERGED (first divergent event named) and REFUSED
keep their meaning and exits (0 / 1 / 3). The stamps (`refocus_verdict`,
`refocus_diverge_*`, `refocus_refused_reasons`, `refocus_licence*`) are
written into the NEW trace's meta through the same `db.set_meta`; the Rust
converter's `meta` table has the identical schema.

### 3.2 Licence on a Rust pair

| check | Rust | reads |
|---|---|---|
| source | runs for real | `source_hashes` (instrumented `.rs`, `Cargo.toml`/`.lock`, the binary) re-hashed now |
| environment | runs for real | `env` recorded in both traces |
| output | **UNVERIFIABLE** | `capabilities.output: false`; today the check would compare two empty sets and read as verified — the named bug class; on a Rust pair it prints and stamps `output: unverifiable (not recorded)` and withholds nothing |
| children | **UNVERIFIABLE** | `capabilities.children: false`; same treatment |
| exit status | runs for real | the recorded process exit of both |

The blind-spot lines printed after a Rust verdict come from the Rust
vocabulary table (`vocab.py`): output not recorded; threads from dependency
code unnamed; the re-run's rebuild is its own cost (`--focus` keys a fresh
shim and a rebuild of the matched units). `RUST.no_rerun_note` ("arrives
with rung 4") is retired.

### 3.3 The guard (G1)

`rust/sensorium-transform/src/lines.rs`, the `Stmt::Macro` arm: a
brace-delimited macro that is the block's tail takes no probe (it is the
tail operand, as the exits walk already treats it). The compile-fail golden
`focus_macro_tail` becomes a compile-pass golden pinning `ret(…, m! { 1 })`
with no `line(` after it, through the real-rustc oracle; a unit fn with a
tail brace macro pins one fewer LINE. HONESTY-BLIND-SPOTS' bullet is struck
and corrected; CARRIED-DEBT's item is struck as taken. `sensorium-transform`
0.4.1. The inference-variable commit stays declared and measured by its
compile-fail golden.

### 3.4 Printing gate — three Rust corpus cases

Each is a real re-run inside the gate under the built driver (the corpus
runner records the case once; a `refocus` question then re-invokes the
driver itself — the gate's driver env is what it uses).

| case | program | pins |
|---|---|---|
| `refocus_match` | a deterministic `fn fill()` program, `cargo_args: ["run"]` | `refocus $RUN --focus fill` → `verdict: MATCH`, exit 0; the new trace's `info` shows `refocus_of: $RUN`, `focus: fill`, `line=yes`; `watch <new> --at fill --expr b == 2` SATISFIED — the loop |
| `refocus_diverged` | a program whose second run reads a marker file its first run wrote and takes another branch | `refocus $RUN --focus main` → `verdict: DIVERGED`, exit 1, the divergent event named |
| `refocus_refused_many` | a crate whose `cargo_args: ["test"]` builds two test binaries | `refocus $RUN --focus …` → the single-target sentence, exit 2, and the store holds no new trace |

Python tests on fixture Rust traces (`tests/rust_traces.py` gains
`workspace_root`, `invocation_processes`, `refocus_of`): every pre-rerun
refusal; the pair lookup (0 / 1 / 2 candidates); the two UNVERIFIABLE
caveats present and the output check never "verified"; the stamps; the
merged-focus order; the driver resolution — each mutation-tested.

## 4. E4, pre-registered (section 3, approved)

Record `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md`; §1
committed alone and byte-locked before the instrument exists; runner
`rust/tests/acceptance_e4.py` family on the E9 pattern (env-var locations
only, phases, `.DONE`/`.FAILED` markers with `exit=<n>`, both readings per
row, the structural killed-cell rule, `acceptance` from the raw record's
`byte_lock.doc`). Subject: the bloomery clone at `e209ed9`, read-only; a
fresh `CARGO_TARGET_DIR` and a fresh `SENSORIUM_DIR`; the driver built from
this branch's HEAD.

**Loop.** Pass 1 (originals): for each of the 61 `#[test]` fns in the seven
`FakeSubstrate` files (`pager_codec_gate_test` 20, `pager_obligation_test`
15, `pager_refusal_advice_test` 4, `pager_remove_agent_test` 4,
`pager_reservation_test` 8, `pager_test` 4, `pager_weights_test` 6):
`cargo sensorium test -p bloomery-daemon --test <file> -- <name> --exact`,
unfocused. Pass 2: for each original, `sensorium refocus <run> --focus
<name>` — one focus per test, 61 focused rebuilds, cost reported.

**Expected-MATCH list, written first:** all 61, the thread-spawning
`a_pager_can_be_shared_across_threads` included (its spawned thread is a
task with its own fingerprint; the join is deterministic). No exception
pre-registered: the survey found no nondeterminism (no `SystemTime`,
`rand`, `Instant`, random temp names; `fresh_dir` uses fixed names, safe
under `--exact`), no brace-macro tail, no inference-variable head type.

| id | question | endpoint (both readings pre-committed in §1) |
|---|---|---|
| H1 | does every original refocus without a pre-rerun refusal? | 0 of 61 refusals (each original is a single-process invocation) |
| H2 | does every re-run complete? | 61 of 61; a focused build failure is a **STOP** (the compile-limitation class, guard in) |
| H3 | MATCH on the expected list? | 61 of 61 MATCH; an unexpected DIVERGED is a **finding** recorded with the divergent event, not a STOP (the E4 row's own reading); a REFUSED after the rerun is a **STOP** (the instrument or the pairing) |
| H4 | what does the licence say? | reported: source and environment verified 61 of 61; output and children UNVERIFIABLE 61 of 61 with the caveat printed each time |
| H5 | does the loop close? | three `watch` triples on the NEW traces — E9's W1 and W3 on the refocused `missing_stats_is_a_contract_violation_not_a_reply`, and one triple from another file chosen in §1 — answer as predicted (verdict class and exit) |
| H6 | what does it cost? | reported, no gate: per refocus the invocation wall and cargo's own build time, the first focus versus later ones distinguished; the shim copies counted and sized under the target directory at the end |
| H7 | did nothing else move? | corpus every case equal (the three new ones included); Python suite green; `cargo test --workspace` green |

**Kill rules.** As E9: a `.FAILED` before any number is infrastructure
(archive, empty the fresh locations, relaunch from zero); after a number it
stands; measured once; nothing re-rolled; a reader at its ceiling is the
record. The loop runs detached with markers, bounded at two hours, each
cargo invocation at 1800 s.

## 5. Not in this slice

`--window` (per-activation runtime state); refocus over a multi-process
invocation (refused by name); an opt-out spelling for the inference-variable
limitation; any change to the comparator or to Python's own refocus branch;
`TRACE_FORMAT` (stays 4; format 5 is PR #17's).

## 6. Risks named

- **Sixty-one focused rebuilds** at roughly five seconds and forty
  megabytes each (slice 1's H6 and A8): about five minutes and 2.5 GB; the
  instrument bounds the loop and H6 reports the cost. A hard-linked shim is
  CARRIED-DEBT, not this slice.
- **A stale pair.** `refocus_of` plus the launch timestamp identify the
  pair; a concurrent invocation into the same store with the same
  `--refocus-of` would yield two candidates → REFUSED by count, never a
  guess.
- **The licence reads as weaker than Python's** on a Rust pair (two
  UNVERIFIABLE checks). That is the honest reading; the alternative was a
  false "verified".

## 7. Dated amendments

- **B1 (2026-09-07, after Task 0's review) — two sentences of §4 were
  wrong as written.** "`fresh_dir` uses fixed names" holds for
  `common::pager::fresh_dir`, which six of the seven files use;
  `pager_refusal_advice_test.rs:60` defines its own pid-plus-sequence form
  (harmless to the fingerprint, which hashes file, qualname and kind only).
  "The survey found no nondeterminism" holds for values and clocks; three
  tests of that same file drive `serve_fake`'s four worker threads over one
  queue, and which worker serves which request is the scheduler's, so their
  per-thread fingerprints can legitimately partition differently. E4's
  locked §1 pre-registers both, keeps the 61-of-61 gate, and (by its lens
  amendment under ruling R-H1) names the discriminator: a DIVERGED on those
  three is the hazard only when the worker tasks' total event count is
  preserved and the MAIN stream MATCHes.

