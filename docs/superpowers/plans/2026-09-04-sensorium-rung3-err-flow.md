# Rung 3 — Err Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sensorium exceptions` answers on a Rust trace — every `?`, sink, and `Err` arm the transformer can see is recorded, chains are minted at conversion, and the Rust rule module names swallowed / panicked / returned-to-harness / propagated / ambiguous with zero false SWALLOWED on the corpus (E6) and on bloomery (E6′).

**Architecture:** The transformer (`rust/sensorium-transform`) gains probe sites for `?`, the four sinks, `let _ = <value>`, and classified `Err` arms, plus frames for closures containing `?`; the runtime (`rust/sensorium-rt`) gains wire v3 record kinds RAISE (4) / HANDLED (5), the `err_site*` entry points with a three-level probe ladder, a typed `err` RETURN, and `capabilities.err_flow`; the converter (`rust/cargo-sensorium`) writes RAISE/HANDLED events with `exc {kind, type, msg, serial, loc}` and mints chain serials by the design's transition table; the Python reader gains `query/exceptions_rust.py` behind the shared renderer; TRACE-FORMAT, vectors v16–v19, ten corpus cases, and a pre-registered acceptance (E6/E6′/E2″/E7″/E3″/E5″/E0″) close it.

**Tech Stack:** Rust 1.96.0 (pinned; `syn` full/visit, stdlib-only runtime), Python 3.12+ (stdlib-only reader), pytest, the corpus + vector harnesses, the rung-2 acceptance tooling (`rust/tests/acceptance*.py`), the bloomery clone on `/mnt/extra`.

**Spec:** `docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md` (R1–R16 and §2a the chain machine — the binding design; committed by Task 0) arguing from the parent `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` §3.3/§6/§8/§9/§11. Honesty ledger: `rust/HONESTY.md` (§1 outcomes, §8 fallback, a new §10 Err flow). Rigor: `~/.claude/skills/rigorous-experiments/SKILL.md`. Prior records never touched: `docs/superpowers/acceptance/2026-09-02-*` and `2026-09-03-*`.

## Global Constraints

- **Branch** `feat/rung3-err-flow` from `main` @ `bd8c6cb`. PR against `main`; merge is Brice's unless delegated. Never push `main`.
- **`/home/brice/workspace/bloomery` is read-only, forever.** The only bloomery built or checked out is the clone `/mnt/extra/sensorium-rung2/bloomery` (HEAD detached at `e209ed9`; branches `e5-split` @ `e8c79be`, `e5-planted` @ `fea50b1` — never rewritten, never pushed).
- **Every artifact set on the second disk**: `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target` (workspace), `/mnt/extra/sensorium-rung2/bloomery-target` (clone), `SENSORIUM_PROBE_TARGET=/mnt/extra/sensorium-rung2/probe-target`, `/mnt/extra/sensorium-rung2/corpus-target`, a NEW `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/rung3` for the acceptance. Root disk ≈ 13 GB free: never a default `target/`. ONE cargo invocation at a time per target.
- **No box-local path in any committed file** except the acceptance record's lens rows and this plan. Tests read the clone only from `SENSORIUM_BLOOMERY_CLONE`, skipping by name when unset.
- **`-D warnings` clean** on 1.96.0 (`cargo clippy --workspace --all-targets -- -D warnings`, `cargo fmt --check`); the rustc oracle for goldens stays `-D warnings` with empty stderr.
- **Every new or changed test is mutation-tested** (the mutation and its failing output in the report); mutant runs under `setsid` + timeout + kill by pgid + `ps -p`; never `pkill -f`; Python mutants purge `__pycache__` with `PYTHONDONTWRITEBYTECODE=1`.
- **Pre-registration byte-locked before the transformer changes** (Task 0's last commit); Task 8 refuses to run if §1 differs; a completed measurement is never re-rolled; a miss is STOP with its number.
- **`rust/sensorium-rt/src/bin/scenario.rs` is split in Task 0** before any arm is added; no file over 800 lines afterwards.
- **The line count of every instrumented file is unchanged by the transform** (`splice::check_line_count`) — every new fragment is single-line.
- **Panic locations**: lines never move; a column shifts only inside a wrapped operand, by the wrap prefix's byte length (E7″ measures it; HONESTY states it).
- The untracked-file rule: never `git add -A`; explicit paths; commit messages end with the two trailer lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`
- Every shell command starts `cd /home/brice/workspace/sensorium &&`.

---

## Decisions carried from the design (the plan's D-table = the design's R-rows)

D1 = R1/R1b (wire v3 + typed site table), D2 = R2 (the probed sites), D3 = R3/R4 (the probe ladders and entry points), D4 = R5 (closures with `?`; async blocks unframed), D5 = R6 (`partial`), D6 = R7/§2a (the chain machine), D7 = R8 (dispositions), D8 = R9 (`err_flow`, dispatch order), D9 = R10 (tier), D10 = R11 (the Rust module), D11 = R12 (fingerprints; E3″/E5″), D12 = R13 (versions, vectors), D13 = R14 (scenario split), D14 = R15 (acceptance), D15 = R16 (blind spots). Every task cites the rows it implements; a task that needs a decision the design lacks stops and the controller rules (ledger).

## Pre-registration — §1 of `docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md` (Task 0 writes it AFTER the census count and commits it alone; Task 8 verifies byte-identity)

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| E6 | Does the Rust rule module ever accuse falsely on the corpus? | Every `corpus/rust/*` case with an `exceptions` question, run once under the rung-3 driver; a cross-case collector gathers every printed `SWALLOWED` line and every `dispositions:` tally line. | **For every case: printed SWALLOWED lines == the case's pre-registered swallow set (equality); every swallow case's set is non-empty; every `dispositions:` tally line equals the case's pre-registered tally. Any extra SWALLOWED line = a false accusation = STOP; any missing = STOP.** | Parent §8 E6; the critic's one-sided-subset gap closed. |
| E6′ | Does it accuse falsely on real code? | `cargo sensorium test -p bloomery-daemon --lib` on the clone (all tests), then `sensorium exceptions <run>` paged to completion; every SWALLOWED line hand-adjudicated against the source by the acceptance author, each with a one-line reason. | **0 false accusations** (an `Err` that was stored, returned, re-raised, or merely observed = false; *clarified 2026-09-05 before the byte-lock (design R15): "merely observed" = read by a `&self` predicate or its value moved out of the arm — a format-only/log-and-continue arm is a TRUE swallow*). Reported: the total lines per disposition. | E6 has no exposure outside the corpus; bloomery has ~200 `Err` arms. |
| E2″ | Does the transformer reach the `?` sites? | The checked-in census binary over the clone: `try_syn` = syn-visible `ExprTry` nodes; `try_macro_tokens` = `?` tokens inside macro invocations (reported separately, with `?Sized`/`$(…)?` confusions excluded by rule and stated); numerator = `kind: "try"` manifest rows from a from-scratch workspace build. | **numerator / try_syn ≥ 95.0%; 0 units fell back; `partial` rows == try_macro_tokens per file (reported).** Denominator counted BEFORE this section was locked: try_syn = `<N1>`, try_macro_tokens = `<N2>` (Task 0 fills the measured numbers before the byte-lock commit). | Parent §8 E2's second floor. |
| E7″ | Do panic locations survive the new wraps? | `rust/tests/mechanics.sh`'s E7 checks unchanged (lines AND columns) on the probe's existing panics, plus a new probe panic literal placed inside a `?` operand whose expected column shift is the wrap prefix's byte length, computed and written here before the run: prefix = `match ` (6 bytes) → shift +6 for the first byte of the operand. | **Existing checks: 0 differences. New check: line identical, column = original + 6 exactly.** | R15; the wrap moves bytes on a line, never lines. |
| E3″ | Does RAISE/HANDLED entering the fingerprint create false DIVERGED? | Rung 2's E3 protocol verbatim: 20 identical re-runs of one bloomery-daemon test binary, `diff` each against the first. | **DIVERGED 0/19, REFUSED 0/19.** | R12: causal kinds changed; the old measurement no longer covers the new stream. |
| E5″ | Does `diff --ignore-moves` still verify the split with the new events? | The E5′ protocol verbatim (A/B/C arms, the rung-2 schema class). | **A/B MATCH class with every task paired; A/C DIVERGED naming a step in the swapped fn.** | R12. |
| E0″ | Does the reader stay usable at the new event volume? | `info <run>` and `diff <run> <run>` on the E6′ trace, wall-timed, 60 s kill armed. | **Both under 60 s** (E0's kill rule); reported walls. | Parent §8 E0. |

Lens for every endpoint: dev profile; the clone at `e209ed9`; the driver built `--release` from this branch's HEAD at run time (commit + sha256 recorded); warm target (stated); `~/workspace/bloomery` untouched (HEAD/porcelain before and after); loads recorded at every arm's start; nothing gated on a wall.

**Reported without a gate:** E1″ (the `--lib` plain/call walls on `bloomery-daemon`, the rung-2 addendum's protocol and lens), RAISE/HANDLED counts and bytes per record on the E6′ run, `partial` and `closure` frame counts, the per-disposition tally on bloomery.

---

## File Structure

- Runtime: `rust/sensorium-rt/src/{spool.rs (wire v3), lib.rs (err_site/err_site_value/err_site_unbound, capability), probe.rs (three-level ladder; two-level value ladder; type_name), thread.rs}`, `src/bin/scenario/{main.rs, ret.rs, panic.rs, spawn.rs, values.rs, threads.rs, units.rs, errflow.rs}` (split of the 800-line file), tests `err_flow.rs`, `outcomes.rs` (+ typed err RETURN).
- Transform: `src/lib.rs` (`Site.kind`, `SiteKind`, `Partial`, `Census.try_*`), `src/visit.rs` (`visit_expr_try`, `visit_expr_method_call` sinks, `visit_local` `let _`, `visit_expr_match`/`visit_arm` + `visit_expr_if` for `if let Err`, `visit_expr_closure`, `visit_expr_async` skip, `#[test]`/`main` marks), `src/errflow.rs` (new: classification of arms — PROPAGATE/PANIC/ESCAPED/handled; the escape test; the sink list), `src/splice.rs` (new `Kind` variants `ErrOpen`/`ErrClose`/`ArmProbe`/`ClosureGuard`, ordering), `src/manifest.rs` (`kind`, `how`, `line`, `test`, `main`, `partial`), `src/bin/census.rs` (new), tests: goldens (`try_stmt`, `try_tail_and_stmt`, `try_option`, `try_in_macro_arg`, `sinks`, `sink_place_receiver`, `let_underscore`, `err_arms_three_ways`, `err_arm_escaped`, `if_let_err`, `closure_try`, `closure_no_try`, `async_block_try`), `edges.rs`, `census.rs` (`PINNED_TRY_SYN`, `PINNED_TRY_MACRO`), `oracle.rs` (the two run-cases gain an err-flow probe).
- Driver: `src/convert/spool.rs` (kinds 4/5 + typed err RETURN parse), `src/convert/frames.rs` (RAISE/HANDLED events, synthetic origin RAISE at an `err` close, `exc.kind`, chain serials, `loc` from the manifest line), `src/convert/chains.rs` (new: the §2a machine as a pure function over a thread's records — unit-tested on hand-built sequences), `src/convert/meta.rs` (`partial`, `err_flow_records` counts), `src/wrapper.rs` (passes `is_bin_root` for the `main` mark).
- Python: `src/sensorium/query/exceptions_rust.py` (new), `exceptions_cmd.py` (lang dispatch; `_language_refusal` keeps its default arm), `caps.py` (unchanged), `store/reader.py` (only if a helper is needed for `exc.kind`), `tests/test_exceptions_rust.py` (new; one test per §2a row), `tests/fixtures/rust-spools/gen.py` (kinds 4/5), vectors v16–v19, `docs/TRACE-FORMAT.md` (§4 `err_flow`, `partial`; §5 `exc.kind`, typed err RETURN; §8 vectors).
- Corpus: `corpus/rust/{silent_swallow, err_propagation, interleaved_chains, unwrap_panic, err_arms, err_stored, dependency_swallow, cleanup_then_fail, join_handle, closure_try, returned_to_harness, macro_arg_partial, outcome_generic}` + `exceptions` questions on `panic`, `none_propagation`, `abort`; `corpus/rust/README.md`.
- Acceptance: `docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md` (+ `.results.json`), `rust/tests/acceptance_rung3.py` (new runner), `acceptance_schema.py` (`assemble_rung3`), `render_acceptance.py` (`--doc rung3`), `acceptance_phases.py` (a `phase_e6` collector; E2″ from the census bin).
- Docs: `rust/HONESTY.md` (§1 typed err, §10 Err flow promises + blind spots, index), `README.md`, `rust/README.md`, `CHANGELOG.md` (0.8.0), `pyproject.toml`, the four `Cargo.toml` versions, the parent spec §11/§13 amendments.

---

### Task 0: Branch, split, census count, pre-registration byte-lock

**Files:** the design doc + this plan (commit); `rust/sensorium-rt/src/bin/scenario/` (the split); `rust/sensorium-transform/src/bin/census.rs` + `src/lib.rs` (`Census.try_syn`, `Census.try_macro_tokens`); `rust/sensorium-transform/tests/census.rs` (`PINNED_TRY_SYN`, `PINNED_TRY_MACRO` measured and pinned); the acceptance document §1.

- [ ] `git checkout -b feat/rung3-err-flow main`; commit the design doc and this plan (`docs(rung3): design (R1–R16, chain machine) + plan`).
- [ ] **Split `scenario.rs`** into `src/bin/scenario/main.rs` (dispatch) + one module per existing blank-line group (`ret`, `values`, `panics`, `spawn`, `threads`, `units`); `cargo test -p sensorium-rt` must pass byte-for-byte the same 40 scenarios (the dispatch match unchanged; every scenario's stdout identical — pin with the existing tests); no file over 400 lines. Commit `refactor(rt): split scenario.rs into src/bin/scenario/ (800-line ceiling)`.
- [ ] **Census counts** (D14): `Census` gains `try_syn` (every `syn::ExprTry` the walk meets, all positions) and `try_macro_tokens` (`?` punct tokens inside `Macro.tokens` of every macro invocation in fn bodies, excluding a `?` immediately following `)` inside a `$( … )` repetition — only in `macro_rules!` bodies, which the walk already skips — and a `?` that is a `?Sized` bound: `?` followed by an ident `Sized`); `src/bin/census.rs` prints one JSON row per `.rs` file under a directory (`{file, parsed, fn_items, const_fns, extern_fns, async_fns, eligible, try_syn, try_macro_tokens}`); run it over the clone (`SENSORIUM_BLOOMERY_CLONE`); pin both totals in `tests/census.rs` beside the existing three pins. Commit `feat(transform): checked-in census binary; ?-site counts pinned on the clone`.
- [ ] **Pre-registration**: write the acceptance document with §1 verbatim from this plan's table with `<N1>`/`<N2>` replaced by the measured totals; §2–§5 empty; commit ALONE (`docs(rung3): pre-register E6/E6′/E2″/E7″/E3″/E5″/E0″`), record the sha in the ledger.

### Task 1: Runtime — wire v3, `err_site*`, typed `err` RETURN, capability

**Files:** `rust/sensorium-rt/src/{spool.rs, lib.rs, probe.rs, thread.rs}`, `src/bin/scenario/errflow.rs` (new arms: `try-err`, `try-ok`, `try-option`, `sink-ok-err`, `sink-ok-ok`, `let-underscore-err`, `arm-value-debug`, `arm-value-nodebug`, `arm-unbound`, `err-nodebug`, `err-big`, `typed-err-return`), tests `err_flow.rs`, `outcomes.rs`, `durability.rs` (kind 4/5 torn-tail rows).

Wire (verbatim, the contract Task 4's parser mirrors independently):
```text
header: b"SNSR" u8 version=3 …  (unchanged layout)
record: u64 seq  u64 ts_ns  u32 site  u8 kind  u8 outcome_or_how  u16 payload_len  [payload]
kind 4 RAISE / 5 HANDLED: outcome_or_how = how (1 try, 2 sink_ok, 3 sink_unwrap_or, 4 sink_let_underscore, 5 arm_propagate, 6 arm_handled, 7 arm_ambiguous, 8 exit [converter-synthesised only, never on the wire])
  payload: u8 flags (bit0 msg present, bit1 msg truncated, bit2 type truncated, bit3 type present) u16 type_len type_bytes  then msg bytes (rest)
kind 2 RETURN with outcome 2 (err): payload = u8 tag u8 truncated  u8 type_flags(bit0 present, bit1 truncated) u16 type_len type_bytes  then the value text (rest)   — the tag/truncated bytes exactly as v2, the type block inserted after them
```
Invariants → falsifiers:
1. `err_site(unit, site, how, probe)` writes a RAISE (how ∈ try/arm_propagate) or HANDLED (the sink/arm hows) only when the ladder saw `Err`; `Ok`/`Option`/non-Result → nothing. *Falsifier:* scenario arms + a converter-side parse in `err_flow.rs`; mutation: write on `Ok` → red.
2. The three-level ladder resolves `Result<!Debug, Debug>` to type + text, `Result<T, !Debug>` to type only (`flags` bit3 set, bit0 clear), non-Result to nothing (the critic's four arms as a unit test on the ladder's return value).
3. `err_site_value` (two-level: Debug / not) and `err_site_unbound` (no type, no text) write what R4 says; a `Debug` that panics reads as truncated-unread like rung 2's values (`catch_unwind` reuse).
4. Typed `err` RETURN: outcome err carries `E`'s type (bit0) with the value text unchanged from v2; outcome ok/none/panic payloads unchanged byte-for-byte (a v2 golden spool of ok/none/panic records still parses under the v3 parser — Task 4 pins).
5. Caps: type 120 bytes with bit2 on truncation; msg 200 bytes bit1 (reuse `cap_utf8`).
6. `capabilities.err_flow: true` in the proc header; the rt version 0.3.0 in the header's `rt_version`.
7. Kind-last Release store and the seq-minting-after-fit rule hold for kinds 4/5 (`seq_contiguity` extended to a two-thread errflow scenario).
- [ ] Red tests → implement → green → mutations (write-on-Ok; ladder level swap; drop bit2; forget the type block on err) → commit `feat(rt): wire v3 — RAISE/HANDLED records, err_site ladder, typed err RETURN, capabilities.err_flow`.

### Task 2: Transformer — `?` and sinks

**Files:** `rust/sensorium-transform/src/{lib.rs, visit.rs, errflow.rs, splice.rs, manifest.rs}`, goldens `try_stmt`, `try_tail_and_stmt`, `try_option`, `try_in_macro_arg`, `sinks`, `sink_place_receiver`, `let_underscore`, `tests/golden.rs`, `tests/edges.rs`, `tests/oracle.rs`.

Fragments (verbatim; `SITE` = the site number, `HOW` = the `how` byte's constant name in `sensorium_rt`):
```rust
// ? on <operand>  →  (the real `?` stays outside)
match <operand> { __t => { ::sensorium_rt::err_site(&crate::__SENSORIUM_UNIT, SITE, ::sensorium_rt::HOW_TRY, { use ::sensorium_rt::probe::*; (&&&Probe(&__t)).err_cap() }); __t } }?
// sink receiver <recv>.ok()  →  (the method call stays outside; only VALUE-expression receivers)
match <recv> { __t => { ::sensorium_rt::err_site(…, ::sensorium_rt::HOW_SINK_OK, { … (&&&Probe(&__t)).err_cap() }); __t } }.ok()
// let _ = <value expr>;  →
let _ = match <value expr> { __t => { ::sensorium_rt::err_site(…, ::sensorium_rt::HOW_SINK_LET_UNDERSCORE, …); __t } };
```
Invariants → falsifiers:
1. Every `syn::ExprTry` at closure depth 0 of an instrumented fn (statement, tail, `return` operand, nested in a call argument) is wrapped exactly once (a `?` whose operand contains another `?` wraps both, innermost first); `?` inside a macro invocation's tokens is not wrapped and is listed in `partial` (reason `macro-arg`) with the fn's qualname. *Goldens* + `-D warnings` oracle; mutation: skip statement-position → red.
2. Sinks: only `.ok()`, `.unwrap_or(..)`, `.unwrap_or_else(..)`, `.unwrap_or_default()` receivers, and only when the receiver is a **value expression** (a call, a method call, a `?`-expression, a block, a literal `Err(..)`/`Ok(..)`): a place-expression receiver (path, field, index, deref, `self.field`) of these by-value sinks IS wrapped — the wrap moves the receiver exactly as the original call does (**corrected 2026-09-04 after Task 2 measured that E0507 does not reproduce for by-value sinks**; the exclusion stands only for the `&self` predicates R2 never probes). `.is_err()`/`.is_ok()` are never wrapped. Goldens `sinks` + `sink_place_receiver`; mutation: wrap a place receiver → the oracle goes red (E0507).
3. `let _ = <value expr>` wrapped; `let _ = <place expr>` untouched (golden `let_underscore`).
4. Each wrapped site is a manifest row `{site, kind: "try"|"sink", how, line, qualname}` from the same `next_site` counter; `sites_by_index` in the converter keeps working (Task 4 pins the mixed numbering).
5. Line count unchanged; every fragment single-line; `escape` not needed (no strings).
6. Census identities, per file, on every golden and on the clone (`census.rs`): `try rows + partial(struct-literal) == try_syn` (nodes) and `partial(macro-arg) == try_macro_tokens` (tokens; a macro-arg `?` is a token with no node — corrected 2026-09-04 after Task 2).
- [ ] Commit `feat(transform): ? sites and the four sinks probed in place; partial declared`.

### Task 3: Transformer — arms, `if let Err`, closures with `?`, marks

**Files:** `src/visit.rs`, `src/errflow.rs`, `src/splice.rs`, `src/manifest.rs`, goldens `err_arms_three_ways`, `err_arm_escaped`, `if_let_err`, `closure_try`, `closure_no_try`, `async_block_try`, `test_marks`, `tests/golden.rs`, `tests/edges.rs`, `census.rs` (arm counts reported, not pinned).

Arm probe fragments: the arm body becomes `{ ::sensorium_rt::err_site_value(&crate::__SENSORIUM_UNIT, SITE, ::sensorium_rt::HOW_ARM_PROPAGATE, { use ::sensorium_rt::probe::*; (&&Probe(&e)).err_cap_value() }); <body> }` for a bound pattern (`e` = the bound ident), `err_site_unbound(…, HOW)` for an unbound one; PANIC-classified arms get nothing.
Invariants → falsifiers:
1. Classification (R2): PROPAGATE if the body contains `?` at closure depth 0, a `return Err(..)`, or ends in `Err(..)`; PANIC if a panic-family macro (`panic!`, `unreachable!`, `todo!`, `unimplemented!`, `assert!`/`assert_eq!`/`assert_ne!`? — **ruling: only the four diverging macros count; an `assert!` may pass**) appears at closure depth 0; ESCAPED if the pattern binds a name and that name appears anywhere in the body other than (a) inside a format-family macro's arguments, (b) as `&e`/`&mut e`… — no: only `&e` (shared borrow) — (c) as the receiver of `.to_string()`/`.kind()`… — **ruling: (a) and (b) only; anything else is ESCAPED**; else HANDLED. Golden `err_arms_three_ways` (one arm each of propagate/panic/handled) and `err_arm_escaped` (push into a Vec; pass by value to a fn; `last = Some(e)`), `if_let_err` (both `if let Err(e)` bodies and `if let Err(_)`). Mutation: treat a stored `e` as handled → red.
2. `#[test]`/`#[bench]` fn items get `test: true`; a bin crate root's `fn main` gets `main: true` (config flag `is_bin_root` passed by the wrapper — Task 4 wires it; the transform test passes it directly).
3. Closures containing `?` at closure depth 1 (their own body) get a frame: guard at the body's `{` (or the expression body wrapped in `{ guard; <expr> }` — a block-body closure only; an expression-body closure `|x| f(x)?` gets `{ let _g = enter(..); f(x)? }`), qualname `<enclosing>::{{closure}}#k`, `kind: "closure"` in the manifest, exit operand probed like a fn's (`ret(...)` on the tail / `return`); closures without `?` unchanged; `async {}` / `async move {}` / `async |..|` are never framed and a `?` inside is `partial` reason `async-block`. Goldens; oracle; mutation: frame a `?`-less closure → the golden `closure_no_try` goes red.
4. The `?` inside a framed closure attributes to the CLOSURE's site (its `try` row's qualname is the closure's), and the enclosing fn's tail wrap still works (`try_tail_and_stmt` + `closure_try` together).
- [ ] Commit `feat(transform): Err arms classified (propagate/escaped/handled; panic unprobed), if-let Err, closures with ? framed, test/main marks`.

### Task 4: Converter — RAISE/HANDLED events, chains, marks, `partial`

**Files:** `rust/cargo-sensorium/src/convert/{spool.rs, frames.rs, chains.rs (new), meta.rs, sqlite.rs (no schema change)}`, `src/wrapper.rs` (`is_bin_root`), tests `convert.rs`, `chains.rs` unit tests, fixtures.

Invariants → falsifiers (the §2a table is the contract; one test per row):
1. Parser: kinds 4/5 + the typed err RETURN, mirrored independently from the rt (a v2 ok/none/panic spool parses unchanged under v3).
2. Events: RAISE/HANDLED rows with `frame_id`/`code_id` of the current top frame, `line` from the manifest row, payload `{"exc": {"kind": "err", "type", "msg" | "unread": ["msg"], "serial", "loc": "<file>:<line>"}, "how": "<how>"}`; a frame closing `err` emits a synthetic RAISE (`how: "exit"`) immediately before its RETURN with the typed err RETURN's type and value text; panic RAISEs gain `"kind": "panic"` (serial namespace unchanged for panics).
3. `chains::mint(records_of_thread, sites) -> Vec<ChainEvent>`: a pure function implementing §2a — tests: hop (`?`-then-return through three frames → one serial, three hops), interleave (Merged), nested chain (callee raises its own while an outer chain is in flight → two serials, no merge), translated hop (arm_propagate then err-close with a different type), chainless HANDLED (a HANDLED with no open chain → its own serial, `origin: "outside"`), sink-then-ok (SWALLOWED candidate marked), sink-then-err (marked `handled_then_failed`), THREAD_END with an open chain on a `test: true` frame / on a spawned thread / on neither. Mutation per row.
4. `exc.serial` for `kind: "err"` chains starts at `1 << 32` per thread (disjoint from panic serials); `chain` metadata written into the event payload: `{"chain": {"serial", "hop": n, "origin": "workspace"|"outside", "translated": bool}}`.
5. Meta: `partial` (registered-unit-scoped, like `skipped`), `err_flow_records: {raise: n, handled: n}`, `closure_frames: n`; `capabilities.err_flow` passed through from the proc header; site table in meta gains `kind`/`test`/`main` per row (the reader needs `test`/`main`).
6. `sites_by_index` refuses a CALL/RETURN on a `try`/`sink`/`arm` site and a RAISE/HANDLED on a `fn`/`closure` site, naming the site.
7. Fingerprints: RAISE/HANDLED enter the per-thread and per-task streams (TRACE-FORMAT §5's causal kinds) — a test pins that a run with one `?` differs in fingerprint from the same run without.
- [ ] Commit `feat(convert): RAISE/HANDLED events with chains minted per the design's transition table; typed err origin; partial; marks`.

### Task 5: TRACE-FORMAT, vectors, fixtures

**Files:** `docs/TRACE-FORMAT.md` (§4 `err_flow` capability + the amended "keyed on lang" paragraph, `partial`, `err_flow_records`, `closure_frames`, site `kind`/`test`/`main`; §5 `exc.kind`, `chain`, the typed err RETURN; §8 vectors), `docs/trace-format/vectors/v16..v19`, `tests/fixtures/rust-spools/gen.py` (kinds 4/5, typed err RETURN, an errflow case), `tests/test_rust_convert.py`, `tests/vectors.py` (no change expected).
- [ ] v16 pins `exc.kind`/`serial` namespace and `chain` on a RAISE→HANDLED pair (format-level, no rule module needed). **v17 (SWALLOWED), v18 (Merged/AMBIGUOUS) and v19 (a `capabilities` object without `err_flow` → `exceptions` exit 3 with the standard sentence) ship in Task 6 with the rule module, and v14's `exceptions` question is removed there** — pytest runs the vectors at every task, so a verdict vector cannot precede the verdicts (pre-flight ruling 2026-09-04). Commit `docs(trace-format): err flow — exc.kind, chains, typed err RETURN, err_flow capability; vectors v16–v19`.

### Task 6: Python — `exceptions_rust.py`

**Files:** `src/sensorium/query/exceptions_rust.py` (new), `exceptions_cmd.py` (dispatch: `if trace.lang == "rust": return exceptions_rust.run(trace, args, renderer pieces)`; `_language_refusal` keeps its default), `tests/test_exceptions_rust.py`, `tests/helpers.py` (a synthetic Rust-trace builder with `capabilities.err_flow`, site table marks).
Invariants → falsifiers: one test per §2a row's verdict on a synthetic trace (SWALLOWED at a sink then `ok`; AMBIGUOUS on `ok` with no sink; PANICKED on unwind with a quoted and with an unrecorded message; RETURNED_TO_HARNESS on a `test: true` holder at thread end; AMBIGUOUS on a spawned thread's outermost `err`; Merged; translated hop header; chainless SWALLOWED "born outside instrumented code"; handled-then-failed AMBIGUOUS); the tally order `swallowed, panicked, returned-to-harness, propagated, ambiguous`; `--after`/`--limit` paging identical to Python's; exit codes 0/1/3 per 0.7.0 (`none_status` for the empty answer on INCOMPLETE); the capability refusal (exit 3) before any rule runs; a Python trace's output byte-identical to 0.7.0 (the whole Python `exceptions` suite unchanged). Mutation per verdict.
- [ ] Vectors v17/v18/v19 added here; v14's `exceptions-refuses-a-rust-trace` question removed (its other three questions stay). Commit `feat(query): exceptions on a Rust trace — chains, five dispositions, shared renderer; vectors v17–v19`.

### Task 7: Corpus

**Files:** the thirteen cases named in the file structure (the capability refusal is vector v19's, not a cargo case — no runtime test hook) (each a self-contained crate with `questions.yaml`; `why_logs_fail` naming `dbg!`/`RUST_LOG`/`RUST_BACKTRACE`), `exceptions` questions added to `panic`, `none_propagation`, `abort`; `corpus/rust/README.md`; existing Rust questions re-pinned where event ids moved (R12), each with the reason.
- [ ] Each case's `questions.yaml` pre-registers its swallow set and tally line (the E6 collector reads `expect_line` rows tagged `SWALLOWED` and the `dispositions:` line); every case falsified once by removing its planted shape (red) and restored. Run with the release driver: 47 cases / all questions / 0 failures. Commit `test(corpus): thirteen Err-flow cases; exceptions questions on panic/none_propagation/abort; re-pins`.

### Task 8: Acceptance run (E6, E6′, E2″, E7″, E3″, E5″, E0″; reported E1″)

**Files:** `rust/tests/acceptance_rung3.py` (new, modelled on `acceptance_e5prime.py`: byte-lock check, preflight, the phases, `.DONE`), `acceptance_phases.py` (`phase_e6` = the corpus run + collector; `phase_e2pp` = census bin + manifests; `phase_e7pp` = mechanics + the new probe panic; E3/E5 reuse), `acceptance_schema.py` (`assemble_rung3`), `render_acceptance.py` (`--doc rung3`), the acceptance document §2–§5, `rust/tests/mechanics.sh` + `rust/probes/ws` (the new `?`-operand panic probe with its predicted column).
- [ ] Run detached; measure once; write §2–§5 by hand from the raw record; E6′'s adjudication table is part of §4 (every SWALLOWED line on bloomery with its verdict and reason). Commit `docs(rung3): acceptance measured — <verdicts>`.

### Task 9: Docs, versions, close-out

**Files:** `rust/HONESTY.md` (§1 typed err outcome; new §10 "Err flow": the sites, the chain identity limits, the blind spots R16, each promise with its falsifier; index), `README.md` (`exceptions` on Rust; what refuses now: `refocus`/`watch`/`flow` only), `rust/README.md`, `CHANGELOG.md` 0.8.0, `pyproject.toml` 0.8.0, `Cargo.toml` ×3 (0.3.0), parent spec §11 rung 3 DONE + §13 deltas, the inbox (rung-4 items), PR body draft in the workspace.
- [ ] Full sequential verification; commit `docs(rung3): HONESTY §10 Err flow; README; CHANGELOG 0.8.0; versions`.

---

## Self-review

- **Spec coverage:** R1/R1b → T1/T2/T4; R2 → T2/T3; R3/R4 → T1 (ladders) + T2/T3 (fragments); R5 → T3; R6 → T2/T3/T4/T5; R7/§2a → T4 (`chains.rs`) + T6 (verdicts); R8 → T6; R9 → T1/T5/T6; R10 → T1; R11 → T6; R12 → T4 (fingerprint test) + T8 (E3″/E5″) + T7 (re-pins); R13 → T5/T9; R14 → T0; R15 → T0/T8; R16 → T7 (cases) + T9 (HONESTY).
- **Placeholders:** `<N1>`/`<N2>` are filled by Task 0 before the byte-lock — by design, not a placeholder left to the run; the arm-classification rulings inside Task 3 are stated (only the four diverging macros; only format args and `&e` count as non-escaping).
- **Type consistency:** `how` names (`HOW_TRY`, `HOW_SINK_OK`, `HOW_SINK_UNWRAP_OR`, `HOW_SINK_LET_UNDERSCORE`, `HOW_ARM_PROPAGATE`, `HOW_ARM_HANDLED`, `HOW_ARM_AMBIGUOUS`) are the rt's constants used verbatim by T2/T3 and mirrored by T4's parser; `exc.kind ∈ {"err","panic"}`; chain serials `≥ 1<<32`; manifest `kind ∈ {fn, closure, try, sink, arm}`; `partial` reasons `{macro-arg, async-block, struct-literal}`.

---

## Addendum 2026-09-05 — repair slice after E6′ STOP (design R2 amendment)

### Task 10: R2 amendment — format products escape; corpus case; E6‴ pre-registration

**Files:** Modify `rust/sensorium-transform/src/arms.rs` (`FORMAT_MACROS` → the logging family only; `format`/`format_args`/`write`/`writeln` mentions escape), its unit rows and goldens (`tests/golden/err_arm_escaped*`), `rust/sensorium-transform/src/bin/census.rs` unchanged; Create `corpus/rust/err_rendered_into_value/` (an `Err(e) =>` arm whose tail value carries `format!("..{e}")` into the function's return → `dispositions: ambiguous 1`, `expect_absent: ["SWALLOWED", "dispositions: swallowed"]`, `why_logs_fail`); Modify `corpus/rust/README.md`; Create `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` §1 (pre-registration, committed ALONE after everything else in this task).

**Interfaces:** Consumes the escape test (`EscapeWalk`, `format_arg_escapes`) and `Class`; Produces no new wire/manifest shape (the arm's `how` byte is unchanged; only the classification moves HANDLED→ESCAPED for the affected shapes).

- [ ] Failing unit rows: `Err(e) => Wrap { msg: format!("{e}") }` → Escaped; `Err(e) => { let s = format!("{e}"); v.push(s); 0 }` → Escaped; `Err(e) => { write!(buf, "{e}").ok(); 0 }` → Escaped; controls: `Err(e) => { eprintln!("{e:?}"); 0 }` → Handled; `Err(e) => { log::warn!("{e}"); 0 }` → Handled; `Err(e) => println!("{e}")` → Handled. Run red → implement → green; goldens updated with the reason in the commit; clone census re-run and the escaped/handled counts reported (expect handled ↓ by ≈ the ~32 format-product arms, escaped ↑ by the same).
- [ ] Corpus case built and run through the real toolchain; mutation: change the arm to `eprintln!` → the question must go red (`swallowed 1`).
- [ ] `docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` §1: E6‴-A (E6′'s row verbatim, gate 0 false, both readings reported), E6‴-W (`cargo sensorium test --workspace --lib` on the clone; every SWALLOWED line hand-adjudicated; gate 0 false; reported: lines per disposition, executed-vs-static count of the ~32 blast-radius arms), E6-again (the corpus collector, equality, incl. the new case), E7‴ (mechanics unchanged, 0 differences). Lens rows verbatim from the rung-3 doc. Commit ALONE: `docs(rung3): pre-register E6‴-A/E6‴-W/E6-again/E7‴` — record the sha in the ledger.

### Task 11: E6‴ measurement

**Files:** `rust/tests/acceptance_rung3.py` (+ `--doc e6ppp` mode or a sibling runner reusing `phase_e6`, the E6′ phase, the byte-lock check against Task 10's sha), the acceptance doc §2–§5.
- [ ] Preflight (clone HEAD/porcelain, fresh `SENSORIUM_DIR`, driver built --release from HEAD, sha recorded); run detached; measure ONCE; hand-adjudicate every SWALLOWED line in both arms (both readings); write §2–§5; commit `docs(rung3): E6‴ measured — <verdicts>`.
