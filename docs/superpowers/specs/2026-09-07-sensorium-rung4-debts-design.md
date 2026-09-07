# Rung 4, slice 3 — the rung-4 debts

**Date:** 2026-09-07 · **Status:** design, approved in one message (Brice,
2026-09-07: "go") · **Design authority:** Claude — every ruling below is
Claude's, recorded here, none deferred · **Base:** main `24de001` (Python
0.8.4; driver 0.5.0 / transform 0.4.1 / rt 0.4.0) · **Branch:**
`feat/rung4-debts`

Slices 1 and 2 (PRs #19, #20) closed rung 4's features and left seven debts
with their fixes spelled out in `docs/CARRIED-DEBT.md`. This slice closes
them and measures the one that changes a printed verdict word.

## 0. Rulings (Claude, 2026-09-07)

| # | Debt | Ruling | Why · cost if wrong |
|---|---|---|---|
| R1 | the licence is WITHHELD on every `cargo test` pair by its untraced-thread clause | a non-main thread whose ROOT frame's site is a `#[test]`-marked fn is the **harness thread** (libtest's per-test thread); the licence excludes harness threads from its untraced-thread counts and names them; Python only | the manifest already marks test fns and `exceptions` already builds the lookup; Python traces carry no test marks so their path is unchanged by construction · cost: a `#[test]` fn that itself spawns nothing reads granted — which is the truth |
| R2 | a re-run whose test spawns an instrumented child yields two `refocus_of`-linked traces and a refusal naming the wrong cause | `find_pair` excludes a linked trace whose `ppid` equals another linked trace's `pid`; the parent is the pair; the excluded child run ids are printed on the pair line; `runs` still lists them | the answer is about the process the user recorded; the child stays visible · cost: a child that is itself the interesting process is not the pair — `runs` names it |
| R3 | one ~40 MB shim COPY per distinct focus | `install_shim` hard-links the driver, falling back to a copy on any error (cross-filesystem included); the key already hashes the driver's bytes, so a replaced driver changes the key | cargo keys the wrapper by path · cost: a hard link shares the inode with the driver, so `set_permissions` touches the driver too — it is already executable |
| R4 | `results.json` re-derivation policy | every raw and assembled results file carries `schema_version` (`"e9/1"`, `"e4/1"`, `"e4p/1"`); the renderer states once when the assembled schema is later than the raw's ("re-derived under X from a raw written under Y") | the entry slice's open item; cost: one string per file |
| R7 | housekeeping | `info` prints the unverifiable checks beside the licence lines; `driver.rs` splits into `invocation.rs` + `launch.rs`; the transform's census path populates sites and skip reasons so `fn_items` stops running the splicing transform | ceilings and cost · none |
| R6 | `--window`; refocus over multi-process invocations; an inference-variable opt-out; a per-site volume cap | **not funded** until a use asks; declared blind spots stand | — |

## 1. What ships

1. Python (`refocus_world.py`, `refocus_rust.py`, `info_cmd.py`, `vocab.py`): R1, R2, the `info` line. Python 0.8.5.
2. Driver (`rt_build.rs`, `driver.rs` → `invocation.rs`, `launch.rs`): R3, the split. `cargo-sensorium` 0.5.1.
3. Transform (`focus.rs`, `visit.rs`/`splice.rs`): `fn_items` via the census path. `sensorium-transform` 0.4.2.
4. Instruments: `schema_version` in the E9 and E4 runners/schemas/renderers; a new pass-2-only runner E4′.
5. A corpus case `refocus_child_run`; the E4′ record measured once; docs; CARRIED-DEBT strikes.

## 2. R1 — the harness thread

`refocus_world._licence_caveats` reads `meta.threads_started` / `live_threads` and the `fingerprints` rows. New: `harness_threads(trace) -> set[int]` = the serials of non-main threads whose root frame (`frames` row with `thread_id = serial`, `parent_id IS NULL`) has a `code_objects` `(qualname, file)` that `meta.sites` marks `test: true` (the same table `exceptions_rust._marks` builds). The untraced-thread counts subtract `len(harness_threads)`; the caveat line reads `no thread started besides the main one and 1 harness thread (libtest's per-test thread, excluded as the recorder's own)`; when program threads remain, the WITHHELD reason names their count and the harness exclusion. Python traces: `meta.sites` has no `test` marks → the set is empty → byte-identical output. `capabilities`, `TRACE_FORMAT`, the converter: unchanged. Blind spot 12's WITHHELD bullet is struck and corrected.

## 3. R2 — the child-run pair

`find_pair` reads `pid`/`ppid` from each candidate's meta (both recorded by the converter). Candidates whose `ppid` is another candidate's `pid` are children: excluded from the pair, listed as `child runs excluded from the pair: <ids>` on the pair line (stdout) and stamped as `refocus_children` on the new trace. One parent → the pair; still 0 or > 1 parents → REFUSED as today. `runs`/`info` unchanged.

## 4. R3 — the shim

`install_shim`: `fs::hard_link(exe, tmp).or_else(|_| fs::copy(exe, tmp).map(|_| ()))`, then the existing rename. Test: byte identity (existing) plus, on one filesystem, `metadata().ino()` equal between the driver and the shim; the fallback pinned by a temp-dir on a different filesystem when one exists (`/dev/shm` if mounted, else skipped by name).

## 5. R4 — `schema_version`

The runner writes `schema_version` into the raw record; `assemble_*` copies it and stamps its own `assembled.schema_version`; when they differ the renderer's §2 prints `re-derived under <assembled> from a raw written under <raw>`. Completeness tests include the field. E9 and E4 gain `"e9/1"` / `"e4/1"` (their committed results.json are NOT re-derived — R-F15/R-G15 precedent: a derivation is stated, not rewritten; CARRIED-DEBT notes the two files predate the field).

## 6. R7 — housekeeping

- `info`: after `licence verified:` lines, `licence unverifiable: output (not recorded), children (not witnessed)` when `refocus_licence_unverifiable` holds names; nothing when absent.
- `driver.rs` (791): `Invocation` + serde + `write_invocation` → `invocation.rs`; the cargo child's env/launch block → `launch.rs`; `go` orchestrates. Pure moves; behaviour byte-identical (the smoke tests pin it).
- `fn_items`: `Ctx` gains `record_sites: bool` (true in census-for-focus mode) gating the `sites`/`skipped` pushes independently of `emit`; `fn_items` runs `Ctx::new(..., emit=false, record_sites=true)` + `visit_file` and reads the `Ctx`; `census()`'s `Census` shape unchanged; a test that `fn_items` output equals the previous route's on every golden input.

## 7. Corpus — `refocus_child_run`

A `cargo run` program whose `main` spawns itself as an instrumented child (the `corpus/rust/abort` child-run shape) and waits; `cargo_args: ["run"]`. `refocus $RUN --focus main` → `verdict: MATCH`, exit 0, the pair line naming one excluded child run; `runs` shows two new traces linked by `refocus-of` (parent + child). Pins derived from §3 before recording.

## 8. E4′ — pre-registered

Record `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md`, §1 alone and byte-locked; runner `rust/tests/acceptance_e4p.py` (a sibling of E4's family, pass 2 only). Subject: the 61 originals of E4 (`raw_pass1.runs[*].run` in E4's archived raw record), copied into a FRESH store by `sqlite3 <src>.db "VACUUM INTO '<dst>.db'"` (a checkpointed single-file copy; the kept store is never written), a FRESH `CARGO_TARGET_DIR`; the driver built from this branch's HEAD; the clone at `e209ed9`, read-only.

**Loop.** For each of the 61 (E4 §1.1's order): `sensorium refocus <orig> --focus <name>` under the new rule.

**Expected, written first.** Licence **granted 57 of 61**; **WITHHELD on exactly four**: `a_pager_can_be_shared_across_threads` (1 program thread) and the three `pager_refusal_advice_test` server tests (4 worker threads each), each reason naming the program's own threads AND the excluded harness thread; MATCH 61 of 61 (the comparator is untouched); every pair found (pair 1 of 1); the shim census: 61 focused keys whose inode equals the driver's when on one filesystem (this box: both under `/mnt/extra`), bytes counted once.

| id | question | endpoint (both readings pre-committed) |
|---|---|---|
| H1 | does the harness rule change the licence word as predicted? | granted = 57 and withheld = the named four → PASS; any other partition → STOP (the rule or its lookup is wrong); each withheld reason names the harness exclusion → reported |
| H2 | is the verdict untouched? | MATCH 61 of 61 → PASS; ≠ → STOP |
| H3 | is the pair found? | 61 of 61 pairs of exactly one → PASS |
| H4 | does the shim link? | 61 focused keys; inode equality with the driver for every key on one filesystem → PASS; a copy where a link was possible → finding; bytes reported |
| H5 | schema_version present? | raw and assembled carry `e4p/1`; the E4 and E9 renderers print their fields on a dry assemble → PASS |
| H6 | nothing else moved? | corpus (incl. `refocus_child_run`) equal; Python suite green; `cargo test --workspace` green → PASS |

Kill rules as E4's (a `.FAILED` before any number is infrastructure; after, a STOP; once; bound 1 h; 1800 s per refocus).

## 9. Not in this slice

R6's four items; any change to the comparator; `TRACE_FORMAT`; PR #17's files (TRACE-FORMAT touched in exactly one place only if a sentence about the licence exists there — check; else not at all).
