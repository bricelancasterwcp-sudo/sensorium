# S5 rung 4's debts, funded — E12′, the finally seal, the Rust `unbound`, the closable list: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close everything mechanical or instrument-level that S5 rung 4 left — H2/H4/H5 re-registered under a fixed instrument, the finally-after-return gap sealed in the TypeScript runtime, Rust's LINE row given `unbound`, blind spots 36–38 struck, the E6-TS table re-registered, the minors fixed, the ceiling files seamed — each closure tested and the whole measured once against a pre-registration.

**Architecture:** E12′ re-adjudicates the committed rung-4 transcripts with a new parser (`e12p_report.py`) that reads a CALL row's name before its `(`, a CALL's line off the trace's `code` table, one-or-two-space arrows, and a `watch` HIT's class off its payload; one live lens run (H8′) confirms this slice's recorder still mints the same rows. The finally seal is static and shape-scoped: only a function whose own body returns from inside a `try` with a `finally` gets `pend`/`seal`; every other wrapper is byte-identical. Rust `unbound` rides the LINE payload as delta tag 3 through a second runtime entry point `line_unbinding`; the converter writes `unbound` on the row; the reader already folds it. A shadowed name is popped, never re-read, in both recorders.

**Tech Stack:** Node ≥ 24 ESM `.mjs` + JSDoc under `tsc --checkJs` (`typescript/`), `magic-string`, the consumer's own `typescript`; Python 3.13 (`src/sensorium/`), pytest; Rust 2021 (`rust/`: `syn`, `proc-macro2`; zero-dependency `sensorium-rt`); the corpus runner (`corpus/run_corpus.py`); vitest 4 on the lens.

**Spec:** `docs/superpowers/specs/2026-09-12-sensorium-s5-rung4-debts-design.md` (PR #35, branch `docs/s5-rung4-debts-design` @ `3ecbb65`). The spec is the authority; this plan is its argument. Section numbers below (§n) are the spec's unless prefixed by a file name.

## Global Constraints

- **Base and branch.** `feat/s5-rung4-debts` off `docs/s5-rung4-debts-design` @ `3ecbb65` (so the spec travels in the branch; PR #35 merges into `main` independently and the feature PR retargets nothing). Worktree `/mnt/extra/sensorium-rung2/s5-rung4-debts`; venv `.venv` (Python 3.13, `uv pip install -e '.[dev]'`); `npm ci` in `typescript/`, `typescript/probes/` and `corpus/typescript/`; `cargo build --workspace` with `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/s5-debts-target`. Ledger `.superpowers/sdd/2026-09-12-sensorium-s5-rung4-debts/`.
- **No box path in a committed file.** `grep -rn "/mnt/\|/home/"` over every committed file must hit only the record's §2 pin table, which sanctions it in its own sentence.
- **Pre-registration is committed alone and before any code** (Task 0) and byte-locked by `tests/test_acceptance_s5_debts_lock.py`: the commit that carries the record's §1 changes nothing under `src/`, `typescript/src/`, `rust/` or `corpus/` except the three new corpus cases' own directories, which §1 names as RED-until-task.
- **Verdict words come from the rule** (§8): per endpoint `PASS` / `STOP` exactly as its rule reads, `reported` for what is not gated; the slice's word is `DONE` or `DONE-WITH-STOP`. A STOP is a finding; nothing is re-run, re-rolled or re-parsed.
- **Legacy output is byte-identical:** every Python corpus case; every Rust corpus case (the new `focus_block_let` excepted); every existing vector; every unfocused TypeScript wrapper and every focused one without §4.2's shape; every Rust LINE fragment of a statement that unbinds nothing (`line(...)` unchanged, R5). Trace format stays **4**; the TypeScript wire stays **1**; the Rust LINE payload grammar is EXTENDED by tag 3 and nothing else.
- **Versions** (R6): sensorium-ts **0.4.0** at Task 3 (`typescript/package.json` + `package-lock.json` lines 3 and 9, `typescript/src/index.mjs` `VERSION`, `tests/ts_traces.py` recorder strings, `src/sensorium/ts/wrapper.py:57`, `typescript/README.md:11`, `README.md:691`); `sensorium-rt` **0.5.0** at Task 5, `sensorium-transform` **0.5.0** at Task 6, `cargo-sensorium` **0.6.0** at Task 7 (`rust/*/Cargo.toml`, `rust/cargo-sensorium/src/invocation.rs:377,414`, `tests/test_acceptance_e9_read.py:221`, `rust/README.md:11-30`, `README.md:518-521,550`); Python **0.13.0** at Task 12 (`pyproject.toml`, `README.md:550`, the three `tests/fixtures/ts-spools/*/invocation.json` `driver_version`).
- **Ceilings** (`tests/test_ceiling.py`, 800; `docs/superpowers/{acceptance,plans,specs}/` exempt): `CHANGELOG.md` cut at Task 1 BEFORE anything else (R7); `tests/test_corpus.py` split at Task 1; `typescript/src/rt.mjs` seamed at Task 1 before Task 3 adds to it; `rust/sensorium-transform/tests/{golden,edges}.rs` untouched — new Rust tests in `tests/unbound.rs` (R8); `README.md` (799) edits net-zero or seamed; `docs/TRACE-FORMAT.md` (788) gains at most twelve lines; `docs/CARRIED-DEBT.md` section drafted and measured before it is appended (Task 12).
- **Tests:** TDD per task; every new Python predicate, every new JS analysis and every new Rust rule mutation-checked (break the line the test pins, the test must FAIL, restore) under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged before each run (the pyc rule). Mutation results go in the task report as `mutant → test that failed`.
- **Commits:** conventional prefixes; the session's trailer lines. A task's commits are by-path (`git add <files>`), never `-A`; `git show --stat` after every commit.
- **Gotchas carried:** `pkill -f`/`pgrep -f` self-match; helper scripts scrub `SENSORIUM_MANIFEST_DIR`, `SENSORIUM_SPOOL`, `SENSORIUM_FOCUS`; the corpus runner's `expect_line` is a substring match per cell; `sensorium --version` is not a flag (`uv tool list`); the lens is READ-ONLY and its manifest is checked before and after any run on it; the legacy fence covers `rust/` whole, so its report WILL list `rust/` paths this slice changed and §1 says so.

---

## File structure

| file | responsibility |
|---|---|
| `typescript/acceptance/e12p_report.py` (new) | E12′: the fixed parser and the three cells H2′/H4′/H5′, read off the COMMITTED transcripts; imports `e12_report`'s unchanged helpers (`section1`, `one`, `preregistration`, `table_cells`, `LABELS`, `db`, `meta`) and defines its own `ROW2`, `rows_of2`, `call_line_of` |
| `typescript/acceptance/e12p.sh`, `e12p_h8.py` (new) | H8′: one focused lens run under this slice's recorder, manifest before/after, resolver, `info`, the nine-row read, the 0.3.0-vs-0.4.0 transform diff; the reader that turns it into the H8′ cell |
| `typescript/acceptance/census_deferred.mjs` (new) | prints every seal-deferred site under a root, JSON, via `sitesOf` |
| `typescript/acceptance/assemble_s5debts.py` (new) | `results.json` from `e12p-reads.json`, `e12p-h8.json`, `e13.json`, `e14.json`, `e6tsp.json`, the fences and the suites |
| `typescript/acceptance/e12_report.py`, `e12.sh` | one header line each pointing at the successor; NO other change |
| `typescript/acceptance/e6ts.py` | `PRE_REGISTERED["focus_catch_binding"] = 0` (Task 0's own commit); the docstring's procedure paragraph (Task 8) |
| `typescript/src/naming.mjs` (new, Task 1) | `UNNAMED`, `titleOf`, `nameProvider`, `ask`, `nameFor` — moved whole out of `rt.mjs`; `rt.mjs` re-exports `nameProvider` |
| `typescript/src/positions.mjs` (new, Task 1) | `lineOf`, `terminatorFor` — moved out of `transform.mjs`; `probe.mjs` imports it; the cycle is gone |
| `typescript/src/escape.mjs` | `deferredExit(ts, fn)` — the §4.2 detector |
| `typescript/src/transform.mjs` | `Site.deferred`; `Splicer.deferred: Set<Node>`; `spliceFunction` emits the `finally{__srt.seal(__sf)}` wrapper and `spliceReturn` the `pend` form on deferred functions |
| `typescript/src/rt.mjs` | `pend(f, v)`, `seal(f)`; `captures` refuses an odd list |
| `typescript/src/resolve.mjs` | prints `deferred` per matched site; `survey` guards `sitesOf` |
| `typescript/src/bindings.mjs`, `probe.mjs` | dead typedefs gone; `isGuard`/`isGuardBody` derived from `isStatementPosition`'s parent relation |
| `typescript/test/rt.focus.test.mjs`, `test/rt.seal.test.mjs` (new), `test/transform.seal.test.mjs` (new), `test/golden/focus-finally-*.ts`, `test/escape.test.mjs`, `test/resolve.test.mjs`, `test/naming.test.mjs`, `test/bindings.test.mjs`, `test/graph.test.mjs` (new) | the JS tests |
| `src/sensorium/query/js_inspect.py` | `INSPECT_MORE` public |
| `src/sensorium/ts/build.py` | the tail counted; `AttributeError` in the refusal tuple |
| `src/sensorium/query/flow_cmd.py`, `src/sensorium/ts/focus.py`, `src/sensorium/ts/driver.py` | the minors |
| `tests/test_corpus_harness.py` (new, Task 1), `tests/test_corpus.py` | the split |
| `tests/test_acceptance_e12p.py` (new) | the real-data acceptance test over the committed transcripts + the parser's unit tests |
| `tests/test_ts_honesty_prose.py` (new) | the prose tests for both blind-spot files and `HONESTY-COST.md` |
| `tests/test_acceptance_s5_debts_lock.py` (new, Task 0) | the byte lock on the new record's §1 |
| `rust/sensorium-rt/src/line.rs` (+ `line/tests.rs`) | `TAG_UNBOUND = 3`, `line_unbinding`, `write_line_payload` gains the `unbound` slice |
| `rust/sensorium-transform/src/lines.rs`, `lines/facts.rs` | `unbound_of(expr)`, `line_unbinding_fragment`, the walker passing both |
| `rust/sensorium-transform/tests/unbound.rs` (new) + `tests/golden_focus/focus_unbound_*.{in,out}.rs` | the goldens and edges |
| `rust/cargo-sensorium/src/convert/spool/line.rs` (+ `tests.rs`), `convert/frames.rs` | tag 3 parsed; `unbound` on the row; the both-delta-and-unbound refusal |
| `docs/trace-format/vectors/v40-rust-line-unbound.json`, `VECTORS.md` | the contract pin |
| `corpus/typescript/{focus_finally_return,focus_long_string}/`, `corpus/rust/focus_block_let/`, `corpus/typescript/focus_catch_binding/questions.yaml` | the three new cases (T0, RED-until-task) and the re-pinned one |
| `typescript/HONESTY.md`, `HONESTY-BLIND-SPOTS.md`, `rust/HONESTY.md`, `rust/HONESTY-BLIND-SPOTS.md`, `rust/HONESTY-INDEX.md`, `rust/HONESTY-REFOCUS.md`, `docs/TRACE-FORMAT.md`, `docs/trace-format/TYPESCRIPT-KEYS.md`, `docs/corpus.md`, `docs/CARRIED-DEBT.md`, `CHANGELOG.md`, `CHANGELOG-ARCHIVE.md`, `CHANGELOG-ARCHIVE-2.md` (new), `README.md`, `rust/README.md`, `typescript/README.md` | the prose |
| `docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md` (+ `-h2-handcount.md`, `-census.md`, `.results.json`, `-reads/`) | the record |
| `~/.claude/skills/debugging-typescript-with-sensorium/SKILL.md`, `…/debugging-rust-with-sensorium/SKILL.md` (outside the repo) | one line each: the RETURN-after-finally order; `unbound` on a Rust block's row |

## Decisions this plan makes (each amends the spec non-silently; Task 12 appends them to the spec's §12)

| # | decision | why |
|---|---|---|
| A1 | **The `rt.mjs` seam is the naming block, not the capture side.** `dbg`, `exc` and `cap` already live in `dbg.mjs`; `captures` is 8 lines. What moves is `UNNAMED`, `titleOf`, `nameProvider` (with the `provider` state), `ask` and `nameFor` (`rt.mjs:301-314, 372-409`, ~55 lines with their comments) to `typescript/src/naming.mjs`; `rt.mjs` does `export { nameProvider } from './naming.mjs'` and imports `nameFor`, `titleOf`, `UNNAMED`. The export set is unchanged (§7's constraint), and `naming.test.mjs` already exercises the moved rules through `rt.mjs`. | spec §7 named three functions of which two are not in the file |
| A2 | **`e12p_report.py` imports `e12_report.py`'s helpers rather than copying them.** A locked record cites `e12_report.py` by name and its text keeps still; an `import` reads it and changes nothing. The new module owns only what changed: `ROW2`, `rows_of2`, `call_line_of`, `h2p`, `h4p`, `h5p`, `main`. | §3.2 "keeps its text"; DRY |
| A3 | **`Site` gains `deferred: boolean`** (not a separate list): `planSites` computes it beside `focused`, `sitesOf` reports it, `resolve.mjs` prints it per matched site as `deferred: true/false`. Only a deferred AND instrumented function gets the wrapper; focus is irrelevant to the seal (the seal is a frame-lifetime fix in every tier). | §4.2 "sitesOf reports it per site" |
| A4 | **The H2′ hand count is a table, sha-pinned into §1 like rung 4's**: `…-h2-handcount.md` with one row per function-like under the three specs — `| n | qualname | line | kind | how selected |` — and a last line `N = 6`. The lock test recomputes its sha from disk. | §3.3 "a HAND count … written at T0"; rung 4's precedent |
| A5 | **The census at T0 is by hand, the script comes with the detector.** §4.6's script cannot run at T0 (no detector yet), so `…-census.md` lists by hand every function under `typescript/probes/src`, `corpus/typescript` and the lens's `diceQueue.ts` whose own body returns from inside a try-with-finally, found by `grep -n finally` then reading each hit; E13's clause is that `census_deferred.mjs` (Task 3) prints exactly that list. | §4.6; the rung-4 hand-count precedent |
| A6 | **The Rust fragment for a block-like statement with names to unbind is** `::sensorium_rt::line_unbinding(&crate::__SENSORIUM_UNIT, <site>, || [<deltas>], &[<"a">, <"b">]);` **and `line_unbinding` writes tag-3 blocks AFTER the deltas.** Names are `&'static [&'static str]` so the fragment is a literal and the runtime allocates nothing. | §5.2–5.3 |
| A7 | **`focus_catch_binding`'s E6-TS row lands in Task 0's own commit, before the case's `exceptions` question exists** (Task 8 adds the question). The commit message carries the hand adjudication: *one HANDLED at the catch clause (`retry.ts:17`), nothing swallowed, no `ambiguous by reason:` line.* | §6.2 |
| A8 | **The three fixture `driver_version` values become `"0.13.0"` at Task 12**, when Python's version moves; not `"0.12.0"` now. | one bump, not two |
| A9 | **`sites._anchor`'s cwd fallback is already the documented Python-trace rule** (`root` or `cwd`, else `None`); the minor is closed by the comment it already carries plus a dated NOTE. No code change. | read at plan time |
| A10 | **`captures()` on an odd-length list throws** `TypeError('captures: an odd pairs list — <n> entries')`, caught by nothing: the transform is the only caller and an odd list is a transform bug, which should surface as a loud failure of the instrumented file, not as a dropped name. | §2 A #9 "refuse loudly" |
| A11 | **`Resolution.wall` is persisted in the invocation's manifest as `resolver_wall_s`**, written by `driver.py` beside `focus_matched`; `info` does not print it. | §6.4 |

## Pre-registration (Task 0 commits spec §8's table verbatim as the record's §1, plus this block)

The record's §1 carries, verbatim: spec §3.3's table (H2′/H4′/H5′), §3.4's eight clauses (H8′), §8's table (every endpoint), and this block. Read ONCE each; a clause that does not hold is a STOP recorded in §4 as a finding.

- **§1.1 The hashes.** The thirteen transcripts under `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/` listed by `git ls-files` with each file's sha256 (`sha256sum` format), and the store list `…-focus-tracehashes.txt` cited by its own sha256. Verified by `e12p_report.py` before any cell is read; a mismatch is exit 4 and no number.
- **§1.2 H2′'s hand count** — `…-h2-handcount.md`, sha-pinned as §1's last line (A4). Predicted N = 6; predicted `focus_matched` = 5 with the one shared qualname `buildDiceQueueEntry.<anonymous>`.
- **§1.3 H4′** — W2's HITs 52, of which 0 on a row whose `unbound` names `count` and 2 at line 72 (head rows: `m=[ … ]`, no `unbound`, `count=1`); W1 31 of 64; W3 15 at line 72 on rows carrying `m=null` and `unbound:count,sides`; verdict words and exits as §1.2 of the rung-4 record.
- **§1.4 H5′** — S1 found (9 sightings, `:74`, `parseDiceGroups`); S2 found (`e10`, CALL, `parseDiceGroups`, code-object line 68); `elsewhere_not_gated` 5; the transcripts' `sightings:` totals 10 and 5; `unpredicted` 0.
- **§1.5 E13** — `…-census.md` (A5), sha-pinned: the hand list of seal-deferred functions in the three roots; predicted lens list EMPTY; `census_deferred.mjs` must print it exactly; the transform golden diff 0.3.0→0.4.0 over `typescript/probes/src` and `corpus/typescript` changes exactly those functions' wrappers and no other byte (Task 11's diff); `corpus/typescript/focus_finally_return` green with its RED run logged in the ledger at T0.
- **§1.6 E14** — `corpus/rust/focus_block_let` green with its RED run logged; `v40` round-trips; the tag-3 refusals; every other Rust corpus case equal; `refocus_*` equal.
- **§1.7 E6-TS′** — every TS case with an `exceptions` question matches the table, `focus_catch_binding` at 0, the swallow set non-empty (rung 3's instrument `e6tsppp.py` + `e6ts.py`).
- **§1.8 Fences** — the corpus (`--require-driver`, all three languages), pytest, `cargo test --workspace`, `npm --prefix typescript test`, the probes, `tests/test_ceiling.py`, `e7_report.py` needle `sensorium run --focus` on TS output, `e_fences.py` legacy (expected movers: paths under `rust/` ONLY) and branch.
- **§1.9 H8′** — spec §3.4's eight clauses, run LAST.

---

### Task 0: The record's §1, the two hand lists, the E6-TS row, the three RED cases, the lock

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md`, `…-h2-handcount.md`, `…-census.md`, `tests/test_acceptance_s5_debts_lock.py`, `corpus/typescript/focus_finally_return/{finally.ts,focus_finally_return.test.ts,questions.yaml}`, `corpus/typescript/focus_long_string/{long.ts,focus_long_string.test.ts,questions.yaml}`, `corpus/rust/focus_block_let/{Cargo.toml,src/main.rs,questions.yaml}`
- Modify: `typescript/acceptance/e6ts.py:73-98` (one row, its OWN commit, A7)
- Read only: `/mnt/extra/sensorium-s5/vtt/frontend/src/lib/diceQueue.ts` (68–82, 127–156, 194–212), `typescript/probes/src/*.ts`, `corpus/typescript/*/*.ts`

**Interfaces:** Produces the record Task 11 fills; the two hand tables `e12p_report.py` and `census_deferred.mjs` are held against; the three cases whose questions are the pre-registration of E13/E14 and the P7 boundary.

- [ ] **Step 1: The E6-TS row, alone.** In `e6ts.py`'s `PRE_REGISTERED`, after `"logged_rethrow_to_harness": 0,` add a comment `# This slice (2026-09-12): re-registered by rung 3's procedure BEFORE the case's exceptions question exists.` and the row `"focus_catch_binding": 0,`. Run `.venv/bin/python -m pytest -q tests/test_acceptance_s5_rung3_lock.py tests/test_acceptance_scripts.py` (green: the lock is on the record, not the table). Commit: `test(e6ts): pre-register focus_catch_binding at 0 SWALLOWED — one HANDLED at retry.ts:17, nothing swallowed, no reason line`.
- [ ] **Step 2: H2′'s hand count.** Open `diceQueue.ts` in the lens copy. Under the container rule (spec §2's "a spec selects what is nested inside what it names"), list every function-like under `diceQueue.ts:parseDiceGroups`, `:forcedDiceFromSource`, `:buildDiceQueueEntry`: the three named, the `reduce` arrow inside `forcedDiceFromSource`, the two default-parameter arrows of `buildDiceQueueEntry`. Write `…-h2-handcount.md` as `| n | qualname | line | kind | how selected |` rows 1–6, last line `N = 6`, and one sentence naming the shared qualname (`buildDiceQueueEntry.<anonymous>` twice → `focus_matched` 5).
- [ ] **Step 3: The census by hand.** `grep -rn 'finally' typescript/probes/src corpus/typescript --include='*.ts' --include='*.mjs'` and the lens file; read each hit; a function counts when ITS OWN body (not a nested closure) has a `return` inside the `tryBlock` or `catchClause` of a `try` that has a `finallyBlock`. Write `…-census.md`: three tables (`| file | qualname | line |`), the lens table empty with the sentence *no function of `diceQueue.ts` returns from inside a try-with-finally*, each table ending `N = <count>`. Include `corpus/typescript/finally_return` (rung 2's case — read it: if its shape is a return in the FINALLY with no enclosing try, it does not count; say which) and this task's `focus_finally_return`.
- [ ] **Step 4: The three cases, RED.** Model each on its sibling (`corpus/typescript/focus_block_scope`, `corpus/rust/focus_loop_counter`).
  - `focus_finally_return/finally.ts`: `export function settle(flag: boolean): number { let cleanup = 0; try { if (flag) return 1; return 2; } finally { cleanup = 1; note(cleanup); } } export function note(n: number): number { return n; }` — `settle(true)` from the test. `questions.yaml` (`record: {focus: ["finally.ts:settle"]}`): (1) `watch $RUN --at settle --expr cleanup == 1` → `expect_contains: ["verdict: SATISFIED at 1 of the"]`, `expect_line: [["HIT", "LINE", "settle L", "cleanup=1"]]`, `expect_exit: 0`; (2) `frame $RUN --fn settle` → `expect_line: [["LINE", "settle L", "cleanup=1"], ["return: 1"]]` and an `expect_count: {"LINE": <n>}` counted BY HAND from §4.3 and TYPESCRIPT-KEYS' table before the run — the `let cleanup` row, the `try` statement's own completion row, and the two finally statements' rows; a `return` diverges and mints none. Write the number you derive; the RED run at T0 may correct it only in the direction the spec predicts, and the correction is logged with its reason; (3) `tree $RUN` → `expect_line: [["settle(flag=true)"], ["note(n=1)"]]` with `note` INDENTED under `settle` — pin it with `expect_contains: ["    note(n=1)"]` (four spaces deeper than `settle`'s indent; read `tree`'s indent unit off `focus_block_scope`'s output).
  - `focus_long_string/long.ts`: `export function pad(n: number): string { const s100 = 'a'.repeat(100); const s101 = 'b'.repeat(101); return s100.length + s101.length === n ? s100 : s101; }` — questions (`record: {focus: ["long.ts:pad"]}`): (1) `info $RUN` → `expect_contains: ["truncated values: 1"]`; (2) `frame $RUN --fn pad` → `expect_contains: ["s100='aaaa", "... 1 more character"]`, `expect_absent: ["s100='aaa… "]`-style check that the 100 is spelled whole: pin `"s100='" + "a"*100 + "'"` as a single `expect_contains` entry written out in full; (3) `flow $RUN --value "'<101 b's>'"` → `expect_contains: ["sightings: 0 event(s)"]`, `expect_exit: 1`.
  - `focus_block_let/src/main.rs`: `fn shape(v: &[i32]) -> i32 { let x = 1; let mut acc = 0; { let x = 2; acc += x; } if let Some(first) = v.first() { acc += first; } for item in v { acc += item; } match v.len() { n if n > 1 => { let big = n as i32; acc += big; } _ => {} } acc + x }` with `fn main() { println!("{}", shape(&[3, 4])); }`; `cargo_args: ["--focus", "shape", "run"]`. Questions: (1) `frame $RUN --fn shape` → `expect_line` rows for the block's completion row `unbound:x`, the `if let`'s `unbound:first`, the `for`'s `unbound:item`, the `match`'s `unbound:big,n` (order = source order: head pattern then body `let`s — write `n,big`? The rule in spec §5.2 lists head-pattern names FIRST then inner `let`s: `unbound:n,big`); (2) `watch $RUN --at shape --expr x == 2` → `expect_contains: ["verdict: SATISFIED at 1 of the", "x: not in scope at this site"]` — the shadow reading (R4): after the block `x` is popped, so `x == 1` at the tail is NOT evaluable — pin that too: (3) `watch $RUN --at shape --expr x == 1` → `expect_contains: ["verdict: SATISFIED at"]` with the hits only at sites BEFORE the block (`expect_line: [["HIT", "LINE", "shape L", "x=1"]]`) and `expect_absent: ["acc=9"]`-style: pin that no HIT row carries the tail's state — use `expect_count: {"HIT": 2}` computed by hand (parameters row + `let mut acc` row hold `x=1`; the block's row pops it).
  Run the corpus for the three: `.venv/bin/python corpus/run_corpus.py --require-driver focus_finally_return focus_long_string focus_block_let` → all three FAIL; paste the failure lines into the ledger under *RED runs at T0*.
- [ ] **Step 5: The record.** §1 = spec §8's table verbatim (its `##` carried as `###`) + this plan's Pre-registration block verbatim (up to `### Task 0`), then §1.1–§1.9 as the block names them with §1.1's hash list generated by `git ls-files docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads | xargs sha256sum` and `sha256sum docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-tracehashes.txt`, then the two hand tables' `sha256sum` lines LAST. §2 = the ambient pins: suite counts (`pytest -q`, `cargo test --workspace`, `npm --prefix typescript test`, the probes), corpus case count, the ceiling census (`git ls-files -- '*.md' '*.py' '*.mjs' '*.ts' '*.rs' '*.sh' | grep -v '^docs/superpowers/' | xargs wc -l | sort -rn | head -30`), `df -h /mnt/extra`, the lens pin row (VTT `0091e97`, manifest `…/manifest-rung1-before.txt` 748 entries, its sha256), the legacy fence's `FENCED` list quoted with `rust/` marked *expected to move*.
- [ ] **Step 6: The lock test**, modelled line for line on `tests/test_acceptance_s5_rung4_lock.py`: `DOC`, `HANDCOUNT_REL = "…-h2-handcount.md"`, `CENSUS_REL = "…-census.md"`, `BYTE_LOCK = "<sha of Step 5's §1>"`, `ORIGINAL_LOCK = None`, `_SPEC = "docs/superpowers/specs/2026-09-12-sensorium-s5-rung4-debts-design.md"`, `_PLAN = "docs/superpowers/plans/2026-09-12-sensorium-s5-rung4-debts.md"`; the verbatim checks against `git show <sha>:<source>` for §8 and the Pre-registration block; the two pinned-sha checks (the last two non-blank lines of §1); the hand count's shape (`| n | qualname | line | kind | how selected |`, rows 1–6, `N = 6`); the census's shape (three tables, each `N = <count>`, the lens table's N = 0). Run it green.
- [ ] **Step 7: Commit** (the record, the two tables, the lock, the three cases) with `git add` by path; message `test(s5-debts): pre-registration — E12′ over the committed transcripts, E13/E14 cases RED, the lock`. Confirm `git show --stat HEAD` lists nothing under `src/`, `typescript/src/`, `rust/` except `corpus/rust/focus_block_let/`.

---

### Task 1: Seams and the cut — `test_corpus.py`, `naming.mjs`, `positions.mjs`, `CHANGELOG-ARCHIVE-2.md`

**Files:**
- Create: `tests/test_corpus_harness.py`, `typescript/src/naming.mjs`, `typescript/src/positions.mjs`, `typescript/test/graph.test.mjs`, `CHANGELOG-ARCHIVE-2.md`
- Modify: `tests/test_corpus.py` (lines 395–800 move out), `typescript/src/rt.mjs`, `transform.mjs`, `probe.mjs`, `CHANGELOG.md`, `CHANGELOG-ARCHIVE.md`, `typescript/README.md` (module table, two rows)

**Interfaces:** Produces `naming.mjs` exporting `UNNAMED`, `titleOf`, `nameProvider`, `ask`, `nameFor` (signatures exactly as in `rt.mjs` today); `positions.mjs` exporting `lineOf(sf, pos)` and `terminatorFor(ctx, statement)`; `rt.mjs` keeps its export set (`nameProvider` re-exported).

- [ ] **Step 1: `test_corpus.py` split.** Record the test-name set: `.venv/bin/python -m pytest --collect-only -q tests/test_corpus.py | sort > /tmp/before.txt` (scratch, not committed). Move lines from `# -- the cargo half` (395) to the end into `tests/test_corpus_harness.py` with the same imports (`subprocess`, `textwrap`, `Path`, `pytest`, `pytest.importorskip("yaml")`, `from corpus import run_corpus`) and `GOOD_QUESTION`, `PROGRAM`, `_case`, `_load_one` imported from the original: `from tests.test_corpus import GOOD_QUESTION, PROGRAM, _case, _load_one` (`tests` is importable as a package from the repo root — `tests/test_vectors.py` already does `from tests.vectors import …`). Docstring: *the harness half of `test_corpus.py`, moved 2026-09-12 (S5 rung 4's debts) so the file stays under 800; the last test runs the real corpus.* Collect again over both files; the union must equal `/tmp/before.txt` exactly. Run both green. Commit `test(corpus): split the harness half into test_corpus_harness.py — a pure move, the collected set identical`.
- [ ] **Step 2: `naming.mjs`.** Cut `UNNAMED`, `titleOf`, `provider` + `nameProvider`, `ask`, `nameFor` (with their JSDoc) into `typescript/src/naming.mjs`; `nameProvider` there takes an `on` argument? No — it reads `on`, which is `rt.mjs` state: make `naming.mjs` export `setProvider(fn)` (the body of today's `nameProvider` minus the `on` check) and keep in `rt.mjs`: `export function nameProvider(fn) { if (!on) return; setProvider(fn); }`. Export set unchanged. `rt.mjs` imports `{ nameFor, setProvider, titleOf, UNNAMED }`. `npm --prefix typescript test` green; `npm --prefix typescript run check` (tsc) green. `wc -l typescript/src/rt.mjs` must read ≤ 735. Commit `refactor(rt): the naming rules move to naming.mjs — export set unchanged`.
- [ ] **Step 3: `positions.mjs`.** Move `lineOf` (`transform.mjs:173`) and `terminatorFor` (`:343`) into `typescript/src/positions.mjs`; `transform.mjs` and `probe.mjs` import them from there; `probe.mjs` no longer imports from `transform.mjs`. Write `typescript/test/graph.test.mjs`: read every `src/*.mjs`, collect `import … from './x.mjs'` edges, assert no cycle (DFS with a colour map; the test prints the cycle path on failure). Run it: green now; mutation: temporarily add `import './transform.mjs'` to `probe.mjs` → the test FAILS naming `probe.mjs → transform.mjs → probe.mjs`; restore. Commit `refactor(transform): positions.mjs — lineOf and terminatorFor out, the probe/transform cycle gone; graph test`.
- [ ] **Step 4: The cut.** `CHANGELOG.md` lines 279–549 (`0.9.1`, `0.9.0`) move to a NEW `CHANGELOG-ARCHIVE-2.md` whose head reads: `# Changelog — the earlier entries, volume 2` + a paragraph in `CHANGELOG-ARCHIVE.md`'s voice: moved here 2026-09-12 (S5 rung 4's debts) so `CHANGELOG.md` stays under 800 lines — the third cut; volume 1 stands at 742 and cannot take another section, so the archive is numbered volumes from here, each under 800, never one growing file (the `CARRIED-DEBT-ARCHIVE-2.md` rule). Add to `CHANGELOG-ARCHIVE.md`'s head one sentence pointing at volume 2, and to `CHANGELOG.md`'s tail note (line ~697) the same. Verify byte-identity of the moved text: `diff <(sed -n '279,549p' CHANGELOG.md.orig) <(sed -n '<start>,<end>p' CHANGELOG-ARCHIVE-2.md)` empty (keep `.orig` in scratch only). `tests/test_ceiling.py` green. Commit `docs(changelog): cut 0.9.1 and 0.9.0 to CHANGELOG-ARCHIVE-2.md — volume 2 opened, a pure move`.
- [ ] **Step 5: README module rows.** Two rows in `typescript/README.md`'s table for `naming.mjs` and `positions.mjs`, one line each. Commit `docs(ts): module table — naming.mjs, positions.mjs`.

---

### Task 2: E12′'s instruments — `e12p_report.py`, its real-data test, `e12p.sh` + `e12p_h8.py`, `assemble_s5debts.py`

**Files:**
- Create: `typescript/acceptance/e12p_report.py`, `e12p.sh`, `e12p_h8.py`, `assemble_s5debts.py`, `tests/test_acceptance_e12p.py`
- Modify: `typescript/acceptance/e12_report.py` (line 1: one header comment), `e12.sh` (line 2: one header comment)

**Interfaces (verbatim):**
```python
# e12p_report.py
from e12_report import (LABELS, db, meta, one, preregistration, section1,
                        table_cells, subsection, usage, emit, cell)  # unchanged helpers

#: A row as every listing command prints it, read correctly for a CALL
#: (`name(args…)` before any `L<line>`) and for a RETURN whose `->` follows
#: ONE space. `qual` stops at `(` or whitespace; `args` is the parenthesised
#: text when present.
ROW2 = re.compile(r"^\s*(?:HIT\s+)?e(?P<eid>\d+) (?P<kind>[A-Z]+)\s+"
                  r"(?P<qual>[^\s(]+)(?P<args>\([^)]*\))?"
                  r"(?: L(?P<line>\d+))?(?:\s+->\s+(?P<ret>.*?))?"
                  r"(?:\s\s(?P<rest>.*))?$")

def rows_of2(text: str) -> list[dict]: ...   # same keys as rows_of + "args", "ret", "unbound": list[str] parsed from `unbound:a,b` in rest
def call_line_of(conn, eid: int) -> int | None: ...  # SELECT codes.firstlineno via events.code_id for the CALL event
def h2p(pre, handcount_rows, resolve_json, conn) -> dict: ...   # hand N == len(resolve matched) == meta.functions_focused; focus_matched == 5; shared qualname named
def h4p(pre, watch_reads) -> dict: ...  # W2: hits total, hits on rows whose unbound contains "count" (must be 0), hits at line 72 (must be 2, both without unbound)
def h5p(pre, flow_reads, focused, conn) -> dict: ...  # CALL rows joined to the code table for their line
def main(argv) -> int: ...  # e12p_report.py <reads dir> <store> <out dir>: verifies §1.1's hashes FIRST (exit 4 on mismatch), then the three cells → e12p-reads.json
```
The transcripts are READ from `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/` (the committed copies); the store is `/mnt/extra/sensorium-s5/store-rung4ts` (its `traces/*.db` hashed against `…-tracehashes.txt` before opening, read-only). `e12p_h8.py <out dir>` reads `e12p.sh`'s outputs into the H8′ cell (eight clauses, each `{holds, evidence}`). `assemble_s5debts.py <results dir>` builds `results.json` with `gated: {H2p, H4p, H5p, H8p, E13, E14, E6TSp}` and `reported: {fences, suites, census, transform_diff}`.

- [ ] **Step 1: The parser's unit tests first** (`tests/test_acceptance_e12p.py`): `rows_of2` on the five literal lines below returns the named fields — `  e10 CALL    parseDiceGroups(formula='1d20')   [arg formula]` → `qualname == "parseDiceGroups"`, `args == "(formula='1d20')"`, `line is None`, `labels == ["arg formula"]`; `  e288 RETURN  buildForcedNotation.<anonymous> -> 20   [return]` → `kind == "RETURN"`, `ret == "20"`; `  HIT   e32 LINE    parseDiceGroups L72  m=[ '2d6', … ]   state: count=1` → `hit`, `line == 72`, `unbound == []`; `  HIT   e40 LINE    parseDiceGroups L72  m=null unbound:count,sides   state: …` → `unbound == ["count", "sides"]`; `  e16 LINE    parseDiceGroups L74  sides=20   [local sides]` → `labels == ["local sides"]`. Run: FAIL (module missing).
- [ ] **Step 2: `rows_of2` and `ROW2`.** Implement; run the five green. Mutation: change `\s+->\s+` back to `\s\s->` → the RETURN case FAILS; restore. Change `[^\s(]+` to `\S+` → the CALL case FAILS; restore.
- [ ] **Step 3: The real-data test.** In the same test file, `REAL = REPO / "docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads"`; `test_h5p_reads_S2_off_the_committed_transcript`: parse `08-flow-F1-value-1d20.txt` → exactly one CALL row, qualname `parseDiceGroups`, eid 10; four RETURN rows; `test_h5p_elsewhere_is_five_across_the_two_flow_transcripts` (1 from `07-…`, 4 from `08-…`); `test_h4p_W2_has_no_hit_on_a_completion_row_and_two_head_rows_at_72` over `05-watch-…count-1.txt`: total hits 52, hits with `"count" in unbound` == 0, hits at line 72 == 2 and both `unbound == []`; `test_h4p_W3_fifteen_completion_rows` over `06-…m-null.txt`: 15 hits, all line 72, all `unbound == ["count", "sides"]`; `test_h4p_W1_thirty_one` over `04-…`; `test_h2p_resolver_output_in_the_record_names_six`: parse the fenced block under `### 4.2` of the rung-4 record → 6 lines, 5 distinct qualnames. These are the numbers §1 pre-registers; the test file's docstring says so and says which STOP each one turns into a PASS *of the instrument*. Run: green (or fix the parser until the committed data reads as the post-mortem said — that is the point). Mutation: in `rows_of2`, drop the `unbound` parse → W2's completion test FAILS; restore.
- [ ] **Step 4: `call_line_of` + `h5p`'s S2 line.** Test against the store copy (skip-by-name if `/mnt/extra/sensorium-s5/store-rung4ts` is absent: `pytest.skip("store copy not on this box")`): `call_line_of(conn, 10) == 68` on `20260912-015130-42f691.db`. Implement with `SELECT c.firstlineno FROM events e JOIN codes c ON c.id = e.code_id WHERE e.id = ?` (read the schema first: `sqlite3 <db> .schema events codes`; if the column names differ, use the trace API `Trace(...).event(eid).code.firstlineno` from `src/sensorium/query` — one or the other, named in the docstring).
- [ ] **Step 5: `main`, the hash preflight, the three cells → `e12p-reads.json`.** Structure as `e12_report.main`: `cell(value, n, dropped, rule=…, **evidence)`; every cell carries `recorder`, `instrument: "e12p_report.py"`, `data: "committed transcripts of 2026-09-11"`. Dry run over the committed data writes the file; commit nothing from it yet (Task 11 measures).
- [ ] **Step 6: `e12p.sh` and `e12p_h8.py`.** `e12p.sh <lens dir> <manifest> <store dir> <out dir> <base checkout>`: manifest before (`sha256sum -c`, stop on any FAILED); ONE `sensorium ts run --focus diceQueue.ts:parseDiceGroups --focus diceQueue.ts:forcedDiceFromSource --focus diceQueue.ts:buildDiceQueueEntry -- npx vitest run src/lib/diceQueue.test.ts` behind the load guard (copy `e6pp.sh`'s guard function verbatim); `node <pkg>/src/resolve.mjs` with `SENSORIUM_TS_ROOT`/`SENSORIUM_FOCUS` → `resolve.json`; `sensorium info <run>`; `sensorium frame <run> --fn parseDiceGroups` for the activation with `formula='1d20'` (the read command from the rung-4 record's §1.5, verbatim); the transform diff: `node -e` script that imports `<base checkout>/typescript/src/transform.mjs` and this tree's, runs `transformSource` on `diceQueue.ts` with the three specs, writes both outputs, `diff` → `transform.diff` (must be empty); manifest after; marker grep (`grep -rl __srt node_modules/.vite* .vite node_modules/.vitest*`, each searched dir listed); `node_modules/.sensorium` listing. `e12p_h8.py` reads all of it into eight `{holds, evidence}` clauses and the nine-row text comparison against the rung-4 record's §1.1 table (parse it with `_handcount_rows`' regex from the lock test: `^\| \d+ \|`; compare the `deltas`/`unbound` cells to the `frame` rows' text).
- [ ] **Step 7: `assemble_s5debts.py`.** Model on `assemble_rung4.py`: `READS_FILE = "e12p-reads.json"`, `GATED_FILES = {"H8p": "e12p-h8.json", "E13": "e13.json", "E14": "e14.json", "E6TSp": "e6tsp.json"}`, `FENCE_FILES` as rung 4's, `ORDER = ["H2p","H4p","H5p","H8p","E13","E14","E6TSp"]`; `verify_hashes` over §1.1's list. Unit test: an assembly from fixture JSONs produces the schema (`gated`/`reported`/`verification`/`recorded_by` keys) and refuses a missing cell by name.
- [ ] **Step 8: Header lines.** `e12_report.py` line 1 gains `# Succeeded for H2/H4/H5 by e12p_report.py (2026-09-12); this file is cited by a locked record and keeps its text.`; `e12.sh` line 2 gains the same for `e12p.sh`. `tests/test_acceptance_scripts.py` green (the bin.sh rules). Commit everything: `test(e12′): the fixed instrument — e12p_report.py reads CALL names, code-table lines, one-space arrows and HIT classes; real-data test over the committed transcripts; e12p.sh/e12p_h8.py for H8′; assemble_s5debts.py`.

---

### Task 3: The finally seal — detector, transform, runtime, census, prose; sensorium-ts 0.4.0

**Files:**
- Modify: `typescript/src/escape.mjs`, `transform.mjs`, `rt.mjs`, `resolve.mjs`, `index.mjs`, `package.json`, `package-lock.json`, `tests/ts_traces.py`, `src/sensorium/ts/wrapper.py:57`, `typescript/README.md:11`, `README.md:691`, `typescript/HONESTY.md` §11, `typescript/HONESTY-BLIND-SPOTS.md` (38 struck), `docs/trace-format/TYPESCRIPT-KEYS.md` (§ *The LINE row*), `docs/TRACE-FORMAT.md:510`
- Create: `typescript/acceptance/census_deferred.mjs`, `typescript/test/rt.seal.test.mjs`, `test/transform.seal.test.mjs`, `test/golden/focus-finally-return.ts` (+ `.expected.mjs` per the goldens' existing convention — read `test/golden/` first and follow it)
- Test: `typescript/test/escape.test.mjs`, `rt.focus.test.mjs` (the flip), `resolve.test.mjs`

**Interfaces (verbatim):**
```js
// escape.mjs
/**
 * Whether a function's OWN body returns from inside a `try` that has a
 * `finally` (§4.2): a ReturnStatement, at closure depth 0, whose ancestors up
 * to `fn` include a TryStatement with a finallyBlock, the return sitting in
 * that try's tryBlock or catchClause (a return inside the finallyBlock itself
 * counts only through an OUTER such try).
 * @param {TS} ts @param {FunctionLike} fn @returns {boolean}
 */
export function deferredExit(ts, fn) { … }

// transform.mjs — Site and Splicer gain one field each
/** @typedef {{qualname: string, line: number, kind: FrameKind, focused: boolean, deferred: boolean}} Site */
/** @typedef {{…, focused: Set<Node>, deferred: Set<Node>, isTestFile: boolean}} Splicer */
const CLOSE_BLOCK_DEFERRED = ';__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}';
const CLOSE_BLOCK_GEN_DEFERRED = ';__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf);__srt.gclose(__sf)}';
// spliceReturn on a deferred function: `__srt.pend(__sf,(` … `))` and ` __srt.pend(__sf,undefined)${end}`

// rt.mjs
/** @param {Frame|null} f @template T @param {T} v @returns {T} stores the value; the frame stays OPEN */
export function pend(f, v) { if (!on || !f || !f.open) return v; f.pending = dbg(v); return v; }
/** @param {Frame|null} f @returns {void} closes an OPEN frame with the pended value (or `undefined`); a closed frame is left as `thr` left it */
export function seal(f) {
  if (!on || !f || !f.open) return;
  f.open = false; drop(f);
  emitTs({ e: 'RETURN', f: f.id, t: taskId(f), v: f.pending ?? dbg(undefined) });
}
// Frame typedef gains `pending?: Captured`
```
`resolve.mjs` prints `deferred` on every `matched` entry. `census_deferred.mjs <root>` walks like `resolve.survey` and prints `{"deferred": [{rel, qualname, line}], "files_scanned": n}`.

- [ ] **Step 1: `deferredExit` tests** (`escape.test.mjs`): true for `function f(){ try { return 1 } finally { g() } }`; true for a return in the `catch` of such a try; false for `function f(){ try { return 1 } catch {} }` (no finally); false when the return is inside a nested arrow within the try; false for `function f(){ try {} finally { return 1 } }` (the return is in the finally itself, no outer try); true for `function f(){ try { try {} finally { return 1 } } finally {} }` (outer try guards it); false for an expression-bodied arrow. Run: FAIL. Implement with a recursive visit that stops at `opensClosure` and carries the ancestor set of open `try`-with-finally blocks and which clause it is in. Run: green. Mutation: make the catch-clause branch return false → the second case FAILS; restore.
- [ ] **Step 2: `planSites` / `Site.deferred` / `Splicer.deferred`.** `transform.seal.test.mjs`: `sitesOf` on the fixtures marks `deferred` per function; `transformSource` on a fixture WITHOUT the shape is byte-identical to the current golden (assert against the committed `.expected` of an existing focus golden); on `focus-finally-return.ts` the wrapper carries `finally{__srt.seal(__sf)}` and the return reads `__srt.pend(__sf,(1))`. Write the golden by running the transform once the code is in, then READ it by hand against §4.2 before committing it. Mutation: make `spliceReturn` ignore `deferred` → the golden test FAILS; restore.
- [ ] **Step 3: `pend`/`seal` and the semantics table** (`rt.seal.test.mjs`, one test per §4.3 row, each body written the way the transform splices it — copy the shape of `rt.focus.test.mjs:225-236`): LINE(cleanup=1) then RETURN 1, with `recs.indexOf(RETURN) > recs.indexOf(LINE)`; `finally { return 2 }` → one RETURN `2`; `finally { throw }` → LINE rows then UNWIND, NO RETURN; catch-return → HANDLED, LINEs, RETURN; async with `await` in the try → YIELD, RESUME, LINEs, RETURN; generator with the shape → exactly one RETURN (seal's), `gclose` a no-op; `cleanup()` called inside the finally → its CALL's `p` is `f`'s id. Run: FAIL. Implement `pend`/`seal`. Run: green. Mutation: make `seal` skip `drop(f)` → the nested-call attribution test FAILS (the child's parent is wrong on the NEXT call); restore.
- [ ] **Step 4: The flip.** In `rt.focus.test.mjs`, rename the bs-38 test to `'a statement in a finally after the return mints its row, and the RETURN follows it (blind spot 38 closed)'`; the assertions: `linesOf(returned).map(r => [r.l, r.d.cleanup.v]) deep-equals [[3, '1']]`, and the RETURN's index in `out.recs` is greater than that LINE's; keep `g`'s assertion. Same commit as Step 3's runtime change — never before.
- [ ] **Step 5: `resolve.mjs`** prints `deferred`; `survey` wraps `sitesOf` in `try { … } catch (e) { unparsable += 1; process.stderr.write(\`resolve: ${rel}: ${e.message}\n\`); continue; }`. `resolve.test.mjs`: `survey` is exported with a third parameter `deps = { sitesOf }` (the real one by default); the test calls `survey(root, ts, { sitesOf: (code, file) => { if (file.endsWith('bad.ts')) throw new Error('consumer typescript threw'); return sitesOf(code, file, …); } })` over a root holding `good.ts` and `bad.ts` → `files_unparsable === 1`, `eligible` holds `good.ts`'s sites only, and a captured stderr line names `bad.ts` and the message. A second test runs `resolve.mjs` end to end over a plain root to show `deferred` in the JSON (`false` for a plain function, `true` for one with the shape). Also move `resolve.test.mjs`'s temp roots to `os.tmpdir()` (the minor) and say why in the header.
- [ ] **Step 6: `census_deferred.mjs`.** Run over `typescript/probes/src`, `corpus/typescript`, and the lens file's directory; the printed list must equal `…-census.md`'s three tables EXACTLY (write a tiny comparer in `e12p_h8.py`'s module: `census_matches(md_path, json_path) -> bool`, unit-tested on a fixture pair). If it differs, the difference is a FINDING about the hand list (recorded in the ledger) — do not edit the pinned table; `e13.json` carries both lists and `holds: false`.
- [ ] **Step 7: Version 0.4.0**, every token in Global Constraints. `tests/ts_traces.py` recorder strings → `sensorium-ts 0.4.0`.
- [ ] **Step 8: Prose.** `HONESTY-BLIND-SPOTS.md` 38 struck (`~~…~~ — **closed 2026-09-12, S5 rung 4's debts**: the seal…`, pointer to `rt.seal.test.mjs`); `HONESTY.md` §11 gains one sentence after *The promise*: *A `return` that passes through a `finally` closes its frame AFTER the finally's rows, so the RETURN row follows them and a call the finally makes is the frame's child (0.4.0; blind spot 38 closed).* and one index row; `TYPESCRIPT-KEYS.md` § *The LINE row* gains the same sentence; `TRACE-FORMAT.md:510`'s TypeScript clause gains *and a RETURN row follows the rows of any `finally` the return passed through, which is Python's order* (count the lines: ≤ 12 added to the file).
- [ ] **Step 9: Full checks.** `npm --prefix typescript test`, `npm --prefix typescript run check`, `npm --prefix typescript/probes run probe` (its checker reads through `rt.mjs`'s exports — unchanged), `.venv/bin/python -m pytest -q tests/test_ts_*.py tests/test_vocab.py`. Commit `feat(ts): the finally seal — pend/seal on a shape-scoped wrapper, deferredExit, Site.deferred, census; blind spot 38 closed; sensorium-ts 0.4.0`.

---

### Task 4: Blind spot 36 and the two TypeScript corpus cases green

**Files:**
- Modify: `src/sensorium/query/js_inspect.py:103`, `src/sensorium/ts/build.py:406-410,179`, `typescript/HONESTY-BLIND-SPOTS.md` (36 struck), `docs/trace-format/TYPESCRIPT-KEYS.md:266`
- Test: `tests/test_ts_ingest_focus.py` (or the file that tests `_trunc`), `tests/test_js_inspect.py`

**Interfaces:** `js_inspect.INSPECT_MORE` (the compiled regex, public; `_MORE` kept as an alias for one release with a comment); `build.py._trunc(obj)` counts `INSPECT_MORE.search(obj["v"])` for a `dbg` capture whose `v` is a quoted string whose closing quote precedes the tail (use `js_inspect._body(text) is _CLIPPED`-style check: import `_body` and `_CLIPPED` if they exist, else `INSPECT_MORE.search` on the text with the quote rule inline).

- [ ] **Step 1: Failing test.** A spool fixture record with `d: {"s": {"k":"dbg","v":"'aaaa…'... 1 more character","trunc":false}}` → converted meta `truncated_count == 1`; a capture whose CONTENT ends `... 50 more characters` inside the closing quote → 0. Run: FAIL.
- [ ] **Step 2: Implement** (`_trunc` + `INSPECT_MORE`). Run: green. Mutation: drop the quote rule → the second case FAILS; restore.
- [ ] **Step 3: The refusal tuple.** `build.py:179` `except (KeyError, TypeError, IndexError, AttributeError)`; test: a CALL record whose `a` is a string → `ConversionError` naming the record, not `AttributeError`. Mutation: remove `AttributeError` → FAILS; restore.
- [ ] **Step 4: Corpus.** `.venv/bin/python corpus/run_corpus.py --require-driver focus_long_string focus_finally_return` → both green (adjust ONLY a hand-miscounted `expect_count` and say so in the ledger with the RED line and the reason, per Task 0 Step 4's rule). Then the whole TS corpus.
- [ ] **Step 5: Prose.** 36 struck with the pointer to the case; `TYPESCRIPT-KEYS.md:266`'s sentence becomes *`info`'s `truncated values:` count includes it from 0.13.0*. Commit `feat(ts-ingest): truncated values counts inspect's tail (blind spot 36); AttributeError refused by name; focus_long_string and focus_finally_return green`.

---

### Task 5: Rust runtime — `line_unbinding`, tag 3; sensorium-rt 0.5.0

**Files:**
- Modify: `rust/sensorium-rt/src/line.rs`, `line/tests.rs`, `rust/sensorium-rt/Cargo.toml`, `rust/sensorium-rt/src/lib.rs` (re-export)

**Interfaces (verbatim):**
```rust
/// `bit0..` unchanged. The fourth delta tag: a name with no value that went out
/// of scope on this row (design 2026-09-12 R3).
pub(crate) const TAG_UNBOUND: u8 = 3;

/// A block-like statement's LINE: the deltas it wrote AND the names its inner
/// blocks and its own head pattern bound, which are dead after it. `unbound`
/// is written after the deltas as tag-3 blocks; `line` is unchanged and never
/// writes one.
pub fn line_unbinding<const N: usize>(
    unit: &'static Unit,
    site: u32,
    deltas: impl FnOnce() -> [(&'static str, Capture); N],
    unbound: &'static [&'static str],
)

pub(crate) fn write_line_payload(
    buf: &mut [u8; LINE_PAYLOAD_MAX],
    deltas: &[(&str, Capture)],
    unbound: &[&str],          // NEW third argument; `line` passes `&[]`
) -> (u16, bool)
```
Each unbound block: `u16 name_len, name, u8 3, u8 0`; `n` counts deltas + unbound; the budget check `2 + name.len() + 2` applies; a name that does not fit sets bit0 and stops.

- [ ] **Step 1: The vector test first** (`line/tests.rs`): `one_delta_and_two_unbound_encode_to_the_bytes_the_wire_format_names`: deltas `[("x", debug("5"))]`, unbound `["a", "bb"]` → bytes `00 | 03 00 | 01 00 'x' 01 00 01 00 '5' | 01 00 'a' 03 00 | 02 00 'b' 'b' 03 00`, len 22. Plus `an_unbound_name_that_does_not_fit_sets_bit0_and_stops` (fill to the budget with deltas, one long name). Run: FAIL (no third argument).
- [ ] **Step 2: Implement**; existing tests updated to pass `&[]`; run `cargo test -p sensorium-rt`. Mutation: write tag 2 instead of 3 → the vector test FAILS; restore.
- [ ] **Step 3: `line_unbinding`** mirrors `line` → `emit_line_unbinding` → `write_and_emit(dir, site, &deltas, unbound)`; re-exported from `lib.rs` beside `line`. Version `0.5.0`; `rust/README.md`'s version paragraph gains its sentence (Task 7 finishes the paragraph). Commit `feat(rt): line_unbinding and delta tag 3 — a block's dead names ride the LINE payload; sensorium-rt 0.5.0`.

---

### Task 6: Rust transform — the unbind rule; sensorium-transform 0.5.0

**Files:**
- Modify: `rust/sensorium-transform/src/lines.rs`, `lines/facts.rs`, `Cargo.toml`
- Create: `rust/sensorium-transform/tests/unbound.rs`, `tests/golden_focus/focus_unbound_{block,iflet,for,match,shadow,nested,cfg,tail}.{in,out}.rs`; `common::FOCUS_CASES` rows for each

**Interfaces (verbatim):**
```rust
// lines/facts.rs
/// The names a block-like statement unbinds on completion (design §5.2), in
/// source order, each once: its own head pattern's names (`for`/`if let`/
/// `while let`/each `match` arm's pattern, via `binding_names`/`let_bindings`),
/// then every `Stmt::Local` pattern in each of its DIRECT blocks — not a nested
/// block-like statement's (it unbinds its own), not a closure's or `async`
/// block's, not a `cfg`'d statement's. `Expr::Async` and `Expr::Const` unbind
/// nothing. Empty for a statement that is not block-like.
pub(super) fn unbound_of(expr: &Expr) -> Vec<String>

// lines.rs
fn line_unbinding_fragment(site: u32, names: &[String], unbound: &[String]) -> String
// `::sensorium_rt::line_unbinding(&crate::__SENSORIUM_UNIT, {site}, || [{deltas}], &[{"a", "b"}]);`
// `Walk::statement` calls `unbound_of` on a `Stmt::Expr(expr, _)` whose end came from `block_like_end`, and `emit` takes the extra slice; `line_fragment` is used when it is empty.
```

- [ ] **Step 1: The goldens first.** Write the eight `.in.rs` fixtures (each a focused fn named in `FOCUS_CASES`): `block` (`{ let x = 2; acc += x; }`), `iflet`, `for`, `match` (a binding arm with a body `let`), `shadow` (outer `let x`, inner `let x`), `nested` (a `let` inside a nested `if` inside the block — only the inner `if` unbinds it), `cfg` (`#[cfg(unix)] let a = 1;` inside a block — not unbound), `tail` (a block with nothing to unbind — fragment is `line(...)` unchanged). Write the `.out.rs` by HAND from the rule, then `tests/unbound.rs` with one `#[test]` per fixture asserting the transformed text equals the `.out.rs` (the `golden.rs` pattern via `common::run_focus`). Run: FAIL.
- [ ] **Step 2: `unbound_of`** with unit tests in `facts.rs`'s `mod tests` (the existing `stmt(source)` helper): each rule row above as a case. Run green. Mutations: drop the head-pattern branch → `for` FAILS; recurse into nested block-likes → `nested` FAILS; restore each.
- [ ] **Step 3: The walker + fragment.** Goldens green. `cargo test -p sensorium-transform` all green (the existing goldens are byte-identical: none carries a block-scoped `let`? — CHECK by running; if one does, that golden's `.out.rs` gains its `line_unbinding` fragment and the change is named in the task report as the rule reaching an existing fixture, which is expected, not a defect). Version `0.5.0`. Commit `feat(transform): a block-like statement's LINE names what it unbound — line_unbinding fragment, eight goldens, edges; sensorium-transform 0.5.0`.

---

### Task 7: Rust converter, vector v40, the corpus case, Rust prose; cargo-sensorium 0.6.0

**Files:**
- Modify: `rust/cargo-sensorium/src/convert/spool/line.rs`, `spool/tests.rs`, `convert/frames.rs:334-384`, `Cargo.toml`, `src/invocation.rs:377,414`, `tests/test_acceptance_e9_read.py:221`, `rust/README.md:11-32`, `README.md:518-521,550`, `rust/HONESTY.md` §12, `rust/HONESTY-BLIND-SPOTS.md`, `rust/HONESTY-INDEX.md`, `rust/HONESTY-REFOCUS.md`, `docs/TRACE-FORMAT.md:510`, `docs/trace-format/VECTORS.md`
- Create: `docs/trace-format/vectors/v40-rust-line-unbound.json`
- Test: `rust/cargo-sensorium/tests/convert_frames.rs`, `tests/test_vectors.py` (auto)

**Interfaces (verbatim):**
```rust
pub struct LinePayload { pub dropped: bool, pub deltas: Vec<(String, Value)>, pub unbound: Vec<String> }
// read_value: TAG_UNBOUND => Ok(UNBOUND_MARKER) — a sentinel the loop routes into `unbound` instead of `deltas`;
// the duplicate check spans BOTH lists: a name in deltas and in unbound, or twice in either, is
//   "{label}: LINE payload names `{name}` as both a delta and an unbound name; a statement cannot write what it unbinds"
// the unknown-tag message becomes "which is not 0..=3"
// frames.rs: if !parsed.unbound.is_empty() { obj.insert("unbound", json!(parsed.unbound)); }
```

- [ ] **Step 1: Parser tests first** (`spool/tests.rs`): tag-3 block → `unbound == ["a"]`, `deltas` empty; the both-lists refusal text; tag 4 → `not 0..=3`. Run: FAIL. Implement. Mutation: route tag 3 into `deltas` → the first FAILS; restore.
- [ ] **Step 2: `frames.rs`** writes `unbound`; `convert_frames.rs`: `a_line_record_with_unbound_names_writes_them_on_the_row` (fixture via `line_fixture` + a tag-3 block) → payload `{"deltas": {}, "unbound": ["x"]}`; no `unbound` key when empty. Mutation: drop the insert → FAILS; restore.
- [ ] **Step 3: v40.** Model on v36: `meta.lang: "rust"`, one focused frame, three LINE rows — a `let x` delta row, a block completion row with `unbound: ["x"]`, a tail-side row — and `questions`: `frame` prints `unbound:x` on the block's row; `watch --expr x == 2` reads `x: not in scope at this site` after it. `tests/test_vectors.py` green; `VECTORS.md` row.
- [ ] **Step 4: Version 0.6.0** everywhere in Global Constraints; `cargo build --workspace --release` into `$CARGO_TARGET_DIR`. The corpus runner and `refocus` take the driver from `$SENSORIUM_CARGO_SENSORIUM`, else `cargo-sensorium` on PATH (`corpus/run_corpus.py:78`, `refocus_rust.driver()`); the box's PATH binary stays 0.5.3 until Brice reinstalls after merge, so every corpus and acceptance run in this slice from here on exports `SENSORIUM_CARGO_SENSORIUM=$CARGO_TARGET_DIR/release/cargo-sensorium`, and the ledger records that line once. A run that forgot it reads `driver_version: cargo-sensorium 0.5.3` in `info`, which is the check.
- [ ] **Step 5: Corpus.** `focus_block_let` green (same correction rule as Task 4); then EVERY Rust case (`--require-driver`), including the `refocus_*` ones.
- [ ] **Step 6: Prose.** `TRACE-FORMAT.md:510`'s Rust clause gains *and, from `sensorium-rt 0.5.0`, `unbound` on a block-like statement's own row — the names its inner blocks and its own head pattern bound — the same rule as TypeScript's; a shadowed outer name is popped too and reads `not in scope` until its next write.* `rust/HONESTY.md` §12: one paragraph (the promise, what says it — the row's `unbound`, `frame`'s `unbound:` — and the shadow reading) + an index row in `HONESTY-INDEX.md`; `rust/HONESTY-BLIND-SPOTS.md`: entry 32 *A block that shadows an outer binding pops the name* with *Falsified by* `corpus/rust/focus_block_let` (question 3); `HONESTY-REFOCUS.md`: one sentence under the licence's LINE-not-causal line — *an original under driver 0.5.x re-run under 0.6.0 compares the same fingerprints; the deeper trace's rows carry `unbound` where the original's could not, and the pair reports both `driver_version`s.* `rust/README.md`'s version paragraph gains the 2026-09-12 sentence for all three crates. `README.md` lines 518–521 and 550 updated. Commit `feat(convert): unbound on the Rust LINE row (tag 3), v40, focus_block_let; the shadow reading in both honesty sets; cargo-sensorium 0.6.0`.

---

### Task 8: The E6-TS table's procedure and the re-pinned case

**Files:**
- Modify: `corpus/typescript/focus_catch_binding/questions.yaml` (question 2), `typescript/acceptance/e6ts.py` (docstring), `docs/corpus.md` (the TypeScript paragraph, ~line 78), `typescript/HONESTY-BLIND-SPOTS.md` (37 struck)

- [ ] **Step 1: The question.** Replace question 2's `command` with `["exceptions", "$RUN"]` and `expect_exit: 0`. The case has ONE HANDLED and nothing swallowed, so the answer is `exceptions`' handled-only shape. Record the case once (`corpus/run_corpus.py --show focus_catch_binding` prints the command; run it by hand against that recording) to read the exact tally line the command prints for a handled-only trace, then pin it: `expect_absent: ["SWALLOWED --"]`, `expect_line: [[<the tally line, verbatim>]]`, and keep the HANDLED row pin `["HANDLED attempts handled Error('bad key: oops') L17"]` as a second `expect_line` group. Rewrite the `truth` text to say the `exceptions` command's own tally is the answer and that the table row §1 pre-registered (0 SWALLOWED) is what E6-TS′ reads it against.
- [ ] **Step 2: E6-TS′ dry run.** `.venv/bin/python typescript/acceptance/e6ts.py <scratch> focus_catch_binding` → `value 1 of 1`, no KeyError. Then the full run with no filter → every case matches; save `e6tsp.json` under the results dir for Task 11 (it is re-run there — this is the rehearsal).
- [ ] **Step 3: The procedure**, written once in `e6ts.py`'s docstring under a heading `HOW A NEW CASE ASKS AN exceptions QUESTION` (three sentences: add the row in its own earlier commit; the hand adjudication in that commit's message; then the question) and once in `docs/corpus.md`'s TypeScript paragraph. 37 struck with the pointer. Commit `test(corpus): focus_catch_binding asks its exceptions question — the E6-TS table's re-registration procedure written down (blind spot 37 closed)`.

---

### Task 9: The prose tests and the minors

**Files:**
- Create: `tests/test_ts_honesty_prose.py`
- Modify (each one line unless stated): `src/sensorium/query/flow_cmd.py:565` (`v.get("type")`, refuse by name when absent: `Unresolved(f"{name!r} at e{at.id} carries an oid and no type; the capture is not the shape 0.3.0 declares", BAD_CALL)`), `src/sensorium/query/flow_values.py` (`find_in_value`: a comment saying why `path` is third — keyword-only callers — or reorder if every caller is keyword: check with `grep -rn 'find_in_value('`), `src/sensorium/query/js_inspect.py` (`js_number`: a docstring line on ≥ 2^53 — exact digits, no caller), `typescript/src/rt.mjs` (`captures`: A10), `typescript/src/bindings.mjs:25-28` (dead typedefs deleted — confirm with `tsc` that nothing references them), `typescript/src/probe.mjs:67-120` (`isGuard` = the six kinds; `isGuardBody` re-expressed through `bindings.isStatementPosition`'s parent relation — read both and write ONE predicate the other derives from; the goldens must stay byte-identical), `typescript/test/bindings.test.mjs` (a `({a = 1} = o)` case: `writesOf` returns `['a']`; the test at ~307 renamed to what it pins — read the test body: if the name says `var` head and the assertion reads the incrementor, rename to `writesOf a for reaches the incrementor's assignment`), `typescript/test/naming.test.mjs:30` (also `delete inherited.SENSORIUM_MANIFEST_DIR`), `tests/test_ts_ingest_meta.py` (find the literal `777` or the sentence that states the probe checks count; correct to what `wc -l`/the checker prints today and cite the command), `tests/test_ts_live.py:110` (the 103 asserted: `assert sum(...) == 103` off the checker's own count line, or the docstring stops stating a number), `corpus/cases.py:281-285` (the message says *the '{VITEST}' driver never receives it* — reword to name the vitest driver's closed key set rather than "the Python recorder's"), `corpus/typescript/focus_async/questions.yaml:27` (drop the leading `e4 ` from the needle: `"LINE    load L20\n  ~ e7 YIELD"` → pin without event ids: `"LINE    load L20"` and `"YIELD   load awaiting Promise"` as two entries), `tests/test_ts_driver_focus.py:16-17` (unused imports), `src/sensorium/ts/driver.py:84` (`args.focus` read directly; the three Namespaces in tests gain `focus=[]`), `src/sensorium/ts/focus.py` + `driver.py` (A11: `resolver_wall_s` into the manifest; a test reads it back), `tests/test_acceptance_s5_rung4_lock.py:391` (`r[:70]` → `"|".join(r)[:70]`), `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md:296` (§2 prose, NOT §1: `~/workspace/projects/vtt` → *the VTT working tree*), `typescript/src/bindings.mjs` `listNames` (a comment: not deduped because only a duplicate declarator reaches the second branch, and `tsc` refuses one), `docs/superpowers/specs/2026-09-10-sensorium-s5-rung3-naming-ambiguity-design.md` §4.3 (the dated parenthesis: *(2026-09-12: the locked transcript header and the shipped instrument bind — `oid`/`chain`/`Err` whole-word, `Rust disposition` substring, record §4.6 — not this sentence.)*)

- [ ] **Step 1: The prose tests.** `tests/test_ts_honesty_prose.py`: (a) parse `typescript/HONESTY-BLIND-SPOTS.md` into numbered entries (`^\s*(\d+)\. \*\*` … up to the next), for each un-struck entry find `*Falsifier:*` … a backticked path and a parenthesised italic title; assert the path exists under the repo and the title's text (without the italics) appears in the file; struck entries (`~~`) are skipped BY NAME in the report (a list the test prints); (b) `typescript/HONESTY-COST.md`: every backticked `../docs/superpowers/acceptance/…` path exists; (c) `rust/HONESTY-BLIND-SPOTS.md`: every backticked path under `rust/…tests/…` or `tests/…` or `corpus/…` inside an entry exists; entries citing none are listed. Write the tests, run: whichever fails names a real drift — fix the DOCUMENT (a wrong path) not the test, and say so. Mutation: edit one falsifier title in a scratch copy of the file and point the test at it → FAILS; restore (do this via a `tmp_path` copy inside a dedicated test rather than touching the tracked file).
- [ ] **Step 2: The minors**, one commit per file group (readers / recorder / tests / prose), each with its test where a behaviour changes (`v.get("type")` refusal; `captures` throw; `writesOf` default; `resolver_wall_s`; `cases.py` wording asserted by the existing refusal test). Goldens byte-identical after the `isGuard` derivation (`npm --prefix typescript test`). Full suites at the end: pytest, `npm test`, tsc, probes.

---

### Task 10: The D notes, README net-zero, the skills

**Files:**
- Modify: `docs/CARRIED-DEBT.md` (only STRIKES of closed items in the rung-3 and rung-4 sections, each `~~…~~ — **closed 2026-09-12, S5 rung 4's debts**: <pointer>`; the new section is Task 12's), `README.md` (the two version lines + one sentence on Rust `unbound`, net-zero: trim the same section by the lines added — name the trimmed sentence in the commit), `~/.claude/skills/debugging-typescript-with-sensorium/SKILL.md`, `~/.claude/skills/debugging-rust-with-sensorium/SKILL.md` (one line each, outside the repo; noted in the ledger)

- [ ] **Step 1: Strikes.** Strike in place only what is CLOSED BY CODE at this point: the blind-spot 36, 37 and 38 items, the minors list's closed entries, the "files near the ceiling" bullets for `test_corpus.py` and `CHANGELOG-ARCHIVE`, the prose-test bullet, rung-3 §"new debts" 3 (§4.3), and the "deferred by ruling" bullet 1 (Rust fold). The rung-4 §"gaps" bullets 3 and 4 (E12′) are NOT struck here: they strike at Task 12, after Task 11 has measured, with the record as their pointer. `wc -l docs/CARRIED-DEBT.md` after: must leave room for Task 12's section (draft it FIRST, measure, then decide whether volume 9 opens — Task 12).
- [ ] **Step 2: README** net-zero; `tests/test_ceiling.py` green.
- [ ] **Step 3: Skills.** One line each; commit nothing (outside the repo); the ledger records the two lines verbatim.
- [ ] Commit `docs: strikes for the closures code made; README net-zero`.

---

### Task 11: Measure — E12′, E13, E14, E6-TS′, the fences, then H8′ last; the record's §3–§5

**Files:**
- Modify: the record (§3 results, §4 decisions, §5 gaps), `…-reads/` (H8′'s transcripts, redacted), `.results.json`
- Run only: every instrument of Task 2, `census_deferred.mjs`, `e6tsppp.py`/`e6ts.py`, `e_fences.py`, `e7_report.py`, the suites

- [ ] **Step 1: Preflight.** The lock test green; `git status` clean; the lens manifest `sha256sum -c` (748 OK); the store copy's hashes against `…-tracehashes.txt`; `df -h /mnt/extra` ≥ 20 GB free; no other recording running (`pgrep -a sensorium`, `pgrep -a vitest` — beware self-match). Load guard ready (copy of `e6pp.sh`'s).
- [ ] **Step 2: E12′.** `e12p_report.py <committed reads dir> /mnt/extra/sensorium-s5/store-rung4ts <results>/e12p` → `e12p-reads.json`. Read each cell ONCE. Write §3.1.
- [ ] **Step 3: E13.** `census_deferred.mjs` over the three roots vs `…-census.md` → `e13.json` (clause 1); the transform diff 0.3.0 vs 0.4.0 over `typescript/probes/src` and `corpus/typescript` (the `node -e` script from `e12p.sh`, run over directories): the set of files whose output changed must equal the census's file set and, within each, only lines inside the named functions' wrappers (`diff -u`, saved) (clause 2); the corpus case green (clause 3); `HONESTY-COST.md`'s numbers untouched (`git diff --stat` on it is empty) (clause 4). §3.2.
- [ ] **Step 4: E14.** The corpus case; `tests/test_vectors.py::test_vector[v40…]`; the tag-3 refusal tests; every Rust corpus case equal; → `e14.json`. §3.3.
- [ ] **Step 5: E6-TS′.** `e6ts.py <scratch>` with no filter → `e6tsp.json`. §3.4.
- [ ] **Step 6: The fences and suites.** The eight of §1.8, each exit status carried; the legacy fence's report must list only paths under `rust/` (predicted) — anything else is a STOP on the fence; `e7_report.py` needle. §3.5.
- [ ] **Step 7: H8′, last.** `e12p.sh <lens> <manifest> <fresh store on /mnt/extra> <results>/h8 <base checkout of e6f5035>` → `e12p_h8.py` → `e12p-h8.json`. Redact the transcripts (`<lens>`, `<store>`, `<repo>`, `<home>`) into the record's `-reads/` directory. §3.6.
- [ ] **Step 8: Assemble.** `assemble_s5debts.py <results>` → `.results.json`; §4 one subsection per endpoint with the verdict word from its rule; §5 what the slice ships and any gap found (an instrument defect found AFTER a number is a finding here, the number stands). The slice's word. Commit `docs(s5-debts): the record — E12′/E13/E14/E6-TS′/fences/H8′ measured once`.

---

### Task 12: Versions, the changelog, CARRIED-DEBT, the spec's amendments, final review, the PR

**Files:**
- Modify: `pyproject.toml` (0.13.0), `README.md:550`, `tests/fixtures/ts-spools/*/invocation.json` (`driver_version: "0.13.0"`, A8), `CHANGELOG.md` (the entry), `docs/CARRIED-DEBT.md` (the section + the E12′ strikes), the spec §12 (A1–A11 appended, dated), `docs/superpowers/specs/2026-09-11-sensorium-s5-rung4-focus-tier-design.md` §15 (one dated line: H2/H4/H5 re-registered → this record)

- [ ] **Step 1: Draft and measure.** Write the 0.13.0 entry in scratch, `wc -l`; `CHANGELOG.md` (post-cut) + entry must be ≤ 790; if not, cut `0.10.0` to volume 2 first (the same pure-move rule). Write the CARRIED-DEBT section in scratch (*Settled — rung 4's own debts, closed here* / *The gaps this slice's measurement found* / *Deferred by ruling* (the D notes with what would close each) / *Files near the ceiling* (the census from §2) / *Deferred minors, per task* / *Process lessons*); `wc -l` + the live file ≤ 795, else cut the oldest section to `CARRIED-DEBT-ARCHIVE-9.md` first.
- [ ] **Step 2: Versions** (Python 0.13.0 tokens); `uv pip install -e '.[dev]'` in the worktree venv; `sensorium info` on a v40-built trace prints the new recorder strings (`tests/test_vectors.py`).
- [ ] **Step 3: Append** the entry, the section, the spec's §12 amendments (each `A<n> (2026-09-12, Task <k>): …`), the rung-4 spec's §15 line, the E12′ strikes in CARRIED-DEBT (rung-4 §"gaps" 3–4 → the record). `tests/test_ceiling.py` green.
- [ ] **Step 4: Final review** (superpowers:requesting-code-review, the whole branch against the spec: every §8 endpoint has a cell; every A-list item has a commit; every struck item has a pointer; no box path; the export-set and byte-identity claims re-checked by command); one fix wave; the suites once more.
- [ ] **Step 5: Push and PR** (`feat/s5-rung4-debts` → `main`), body = the record's §5 + the verdict word + the amendment list; merge is Brice's. Ledger: the archive path, the worktree to remove, the two tools to reinstall (`uv tool install --reinstall --python 3.13 --editable ~/workspace/sensorium`; `cargo install --path rust/cargo-sensorium --target-dir /mnt/extra/sensorium-rung2/rust-target`).

---

## Self-review against the spec

- **§0 R1–R8:** R1 → Task 2 + Task 11 Step 2; R2 → Task 3 (A3 keeps focus out of the seal decision); R3/R5 → Task 5; R4 → Task 6's `shadow` golden + Task 7's prose + Task 0's `focus_block_let` question 3; R6 → Tasks 3/5/6/7/12; R7 → Task 1 Step 4; R8 → Task 6.
- **§1 table:** every row has a task (Python minors → Task 4/9; `positions.mjs`/survey/captures → Tasks 1/3/9; rt/transform/driver → 5/6/7; instruments → 2; records → 0/11; docs → 3/7/8/10/12).
- **§2 inventory:** A #1–#15 → Tasks 2/3/5–7/4/8/9/9/9/9/9/1/1/9; B → Task 1 + Global Constraints; D → Task 12's section; C → untouched (Task 12's section restates them under *Deferred by ruling* with the C label).
- **§3:** 3.1 hashes → Task 0 §1.1 + Task 2 Step 5; 3.2 four defects → Task 2 Steps 1–4; 3.3 table → §1.2–§1.4 + Task 11; 3.4 eight clauses → Task 2 Step 6 + Task 11 Step 7; 3.5 → Task 11 Step 8.
- **§4:** 4.2 rule → `deferredExit` + `Site.deferred`; 4.3 table → `rt.seal.test.mjs` one test per row; 4.4 → the generator test; 4.5 flip/prose/case → Task 3 Steps 4, 8; Task 0 Step 4; 4.6 census → A5 + Task 3 Step 6 + Task 11 Step 3.
- **§5:** 5.2 rule → `unbound_of` + goldens; 5.3 wire → Task 5; 5.4 converter → Task 7 Steps 1–2; 5.5 shadow → the goldens, the corpus question, both blind-spot entries; 5.6 licence → Task 7 Step 6's `HONESTY-REFOCUS` sentence; 5.7 → Task 0 + Task 6.
- **§6:** 6.1 → Task 4; 6.2 → Task 0 Step 1 + Task 8; 6.3 → Task 9 Step 1; 6.4 → Task 9 Step 2 (+ Task 1 for `positions.mjs`, Task 3 for `survey`); 6.5 → Task 9's spec §4.3 line + Task 12's D notes.
- **§7 seams:** all five in Task 1 (+ Task 12 for CARRIED-DEBT's own cut).
- **§8 acceptance:** every endpoint is a Task 11 step and a §1 clause.
- **§9:** nothing here touches the C items.
- **§10:** Global Constraints + Task 12 Step 5.
- **Placeholder scan:** the only "read it first and decide" instructions are where the plan cannot see the runtime output (an `expect_count` the RED run corrects, the `exceptions` tally wording, the sqlite column names) and each says what to do in both outcomes.
- **Type consistency:** `deferredExit(ts, fn)`, `Site.deferred`, `Splicer.deferred`, `pend(f, v)`, `seal(f)`, `line_unbinding(unit, site, deltas, unbound)`, `write_line_payload(buf, deltas, unbound)`, `unbound_of(expr)`, `LinePayload.unbound`, `rows_of2`, `call_line_of`, `h2p`/`h4p`/`h5p`, `INSPECT_MORE`, `resolver_wall_s` — used with the same names in every task that mentions them.
