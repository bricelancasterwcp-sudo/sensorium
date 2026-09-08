# The queue, buttoned up — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every open carried debt in buckets A (mechanical fixes with a stated fix), B (files over the 800-line ceiling) and D (dated notes), strike the X items, and land a repo-wide ceiling gate — with no measurement and no behaviour change that a pre-registration governs.

**Architecture:** Pure-move splits first (`programs.py` → test files → `convert.rs` → `tracer.py` → `refocus_world.py`), then the fixes grouped by owner (Python query wording; crates; instruments; corpus + ledgers), then the ceiling gate, then the release. One implementer at a time in the checkout.

**Tech Stack:** Python 3.12–3.14 (pytest), Rust 1.96.0, the corpus harness with the release driver.

**Spec:** `docs/superpowers/specs/2026-09-08-sensorium-debts-buttonup-design.md` — §0 rulings R1–R9; §2 the inventory (row numbers below are its `#`); §3 the split seams. The seam map with line ranges is in the ledger workspace as `inventory-ceiling-splits.md` (gitignored; the design §3 carries the seams).

## Global Constraints

- **Branch** `feat/debts-buttonup` off main `f14d2f6`, main checkout; never push `main`; the merge is Brice's; one implementer at a time.
- **Versions**: Python 0.8.6 → **0.8.7** (Task 7); rt 0.4.0 → **0.4.1**, transform 0.4.3 → **0.4.4**, driver 0.5.2 → **0.5.3** (Task 4); `TRACE_FORMAT` stays 4; `docs/TRACE-FORMAT.md` untouched; byte-locked acceptance §1s never edited; no acceptance `results.json` re-assembled.
- **Pure moves**: every split proved by `git diff --color-moved=zebra` (moved lines all marked) and by equal `pytest --collect-only -q` totals (Python) or equal test counts (`cargo test` summary lines) before and after; the only permitted non-move edits are the ones the design §3 names (imports, re-export blocks, `pub(super)`, the `_SENSORIUM_DIR` patch repoint).
- **Gates**: Python `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` (2255 passed / 15 skipped at base); Rust from `rust/` with `export CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target`: `cargo test --workspace && cargo test -p sensorium-rt --features test-hooks && cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings`; corpus WITH the driver: rebuild `cargo build --release -p cargo-sensorium` whenever `rust/` changed, then from the repo root `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/release/cargo-sensorium PYTHONDONTWRITEBYTECODE=1 .venv/bin/python corpus/run_corpus.py --require-driver` (63 cases, 0 failures, no skips). **Every printed-sentence change runs the corpus gate WITH the driver** (R6).
- **Tests**: every new behaviour or fence pinned by a mutation-tested test on a COMMITTED tree (purge `__pycache__`; `PYTHONDONTWRITEBYTECODE=1`); none-vs-zero; no box path in committed files (`/mnt/extra`, `/home/brice`); every touched file ≤ 800 and the repo-wide gate green from Task 5 on.
- **Commits** by explicit path, never `.superpowers/`; each ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`; one cargo at a time; never `pkill -f`.

---

### Task 1: The Python test-file splits (B: eight files)

**Files:** split `tests/programs.py`, `tests/test_tree_frame.py`, `tests/test_boot_cli.py`, `tests/test_exceptions.py`, `tests/test_diff.py`, `tests/test_tracer.py`, `tests/test_refocus.py`, `tests/test_acceptance_e6q.py`, `rust/tests/acceptance_schema.py` per design §3 (new names there); modify the importers of `tests.programs` (three, per the seam map).

**Interfaces:** none new. Produces: every listed file ≤ 800; `tests/flow_programs.py` exporting the flow-shape programs the three importers now take from it; `tests/test_tracer.py`'s classification half in `tests/test_tracer_classify.py` (its `_SENSORIUM_DIR` monkeypatch still targets `sensorium.record.tracer` until Task 3 repoints it).

- [ ] For each file, in the design's order: record `pytest --collect-only -q <file> | tail -1`; move the block at the named banner into the new file with the imports/fixtures it needs (shared helpers imported from the first file, the `tests/test_acceptance_e4pp_phases2.py:29-31` idiom); re-collect: the sum equals the old count. One commit per file: `test: <file> split at <banner> — <old> → <a> + <b> lines, a pure move`.
- [ ] `programs.py`: take BOTH seams (flow shapes → `flow_programs.py`; the async block → `async_programs.py`) so it lands near 634; update the importers; grep proves no `from tests.programs import <moved name>` remains.
- [ ] Full Python suite green after each commit; `wc -l` table in the report.

### Task 2: The Rust test splits (B: two files) and the crate hygiene rows

**Files:** `rust/cargo-sensorium/tests/convert.rs` → `tests/convert_runner.rs` (G7+G8 + `OutputExt`; helpers duplicated per the house pattern; `count` not copied); `rust/cargo-sensorium/src/convert/chains/tests.rs` → `tests_terminals.rs` (eight `pub(super)`); then rows **#16** (`expr_attrs` loud fallthrough with a test), **#24** (the two intra-doc links; `RUSTDOCFLAGS="-D warnings" cargo doc -p sensorium-transform --no-deps` passes), **#46** (the WARN excludes doctest processes, test), **#47** (rename to its bound), **#54** (spool temp-dir scope guard at all three sites), **#38–#41** (fixtures: malformed meta per hard error; `mint()` isolating; panic tag/outcome; outside-frame panic serial), **#42** (`runid`/driver id-mix helper deduped), **#50/#52/#53** (trait-const fixture; nested-fn golden; wrapper-binary refused-root fixture), **#22** (`acceptance_lib.read_manifests` fixed at source, workaround dropped), **#44**'s eleven rung-2 nits (one line each; any that is not mechanical is reported, not done).

- [ ] Splits first (two commits, zebra-proved, `cargo test --workspace` count equal).
- [ ] Each row its own commit or a small batch by file; a test per behaviour change; the four Rust gates after each batch.
- [ ] Report: the `#44` nits actually taken vs reported.

### Task 3: `tracer.py` split (B) and `sha256` consolidation (R3) — the crates' versions

**Files:** `src/sensorium/record/tracer.py` → `tracer_frames.py` + `tracer_exc.py` per design §3 (re-exports; `_CONTROL_FLOW_EXC` removed as dead; `tests/test_tracer*.py`'s `_SENSORIUM_DIR` patch repointed to `tracer_frames` in the SAME commit); `rust/sensorium-rt/src/sha256.rs` becomes `pub mod sha256` (rt **0.4.1**), `sensorium-transform` and `cargo-sensorium` drop their copies and depend on rt (transform **0.4.4**, driver **0.5.3**; `Cargo.lock`); the NIST-vector tests stay in rt and the two dependents get one smoke test each that hashes through rt.

- [ ] `tracer.py`: RED first for the patch repoint (run `tests/test_tracer.py` after the move but before the repoint: the `_SENSORIUM_DIR` test fails on a full event list); move; repoint; GREEN; full Python suite; corpus gate WITH the driver (the tracer is the Python recorder — every Python case exercises it). Commit: `refactor(record): tracer.py splits by responsibility — frames/classification and exception refs move out; the one patch repointed`.
- [ ] `sha256`: rt exposes the module; dependents switch; `grep -rn "mod sha256" rust/` shows one definition; four Rust gates; version bumps + lock; the driver rebuilt for the corpus gate. Commit: `refactor(crates): one sha256 — sensorium-rt owns it (0.4.1); transform 0.4.4 and driver 0.5.3 take it from rt`.

### Task 4: `refocus_world.py` split (B #55) and the Python query fixes (A)

**Files:** `src/sensorium/query/refocus_world.py` → `refocus_threads.py` (the four thread functions; re-export block in the `refocus_cmd.py:161-171` idiom); then rows **#6** (the session clause carried into the withheld pair's FACT — `info` replays what the screen said; a test that reads `refocus_licence_verified`/facts), **#7** (`is_relocation_note` → `is_env_rule_note`, both callers, docstring), **#20** (the scheduling caveat: one printed sentence on a MATCH with >1 thread, in `refocus_report.py`, through `vocab` if language-bearing), **#14** (`info` prints `focus: none` for an absent focus — pick the spelling the existing `info` lines use for absence; the literal pin then taken), **#18** (`exceptions_rust.py:431,448,462` point at `HONESTY-ERR-FLOW.md` / blind spots 15–26), **#27** (a typed exception replaces the message sniff at `exceptions_cmd.py:671`), **#28**'s printed half (qualify "born outside this thread's instrumented frames"), **#30** (the invocation header's noun), **#31** (one word on the panics line; a `details vary` fixture), **#36** (`diff --task` help in the recorder's words), **#37** (the `interp_line` `or "?"` fixture), **#51** (`diff`'s "modulo location" on the all-in-tasks branch), **#19** (one driver resolution: a helper under `src/sensorium/` used by `refocus_rust.py`, `run_corpus.py`, `test_focus_refusal.py`; the `…_resolutions_agree` test kept), **#21/#43** (`run_corpus._run_ids` keyed on an unambiguous `run:` line shape + the byte-exact conformance pin), **#45** (`corpus/rust/abort` cleans its core file), **#10**'s corpus assertion (the spawned root is the MARKED fn) and its two comments.

- [ ] The split first (one commit, zebra-proved).
- [ ] Each printed-sentence row: change → unit test (exact line) → corpus gate WITH the driver → the case expectation updated to what the tool prints, named in the report.
- [ ] Mutation on each new fence; full Python suite; `refocus_world.py` and every touched file ≤ 800.

### Task 5: The repo-wide ceiling gate (R1)

**Files:** create `tests/test_ceiling.py`.

**Interfaces:** the test enumerates `git ls-files -- '*.py' '*.rs' '*.sh' 'README.md' 'docs/*.md' 'rust/*.md'` minus `docs/superpowers/{acceptance,plans,specs}/`, and asserts each ≤ 800 with the file and count in the failure message; it also asserts the exemption list is exactly those three directories (so a future record cannot be exempted silently).

- [ ] Write it; run it: GREEN only if Tasks 1–4 left nothing over (any file it names is a Task 1–4 miss — fix there, not by widening the exemption). Mutation: lower the limit to 700 → it names files; restore.
- [ ] Commit: `test: a repo-wide 800-line gate over code and living docs; records exempt by name`.

### Task 6: The instruments (A: E4″ gaps and the runner minors)

**Files:** `rust/tests/acceptance_e4pp*.py`, `render_e4pp.py`, `rust/tests/acceptance_e4p_read.py`, `acceptance_e4p.py`/tests, `acceptance_e9*.py`, `acceptance_e6q.py`, `render_grain.py`, `tests/test_acceptance_*.py`. Rows **#1** (the presence reader matches the collector's last path segment AND the whole name; `null` + `case_listing.command`/`rc` when the listing is absent), **#2** (the STOP label derived from the failing cell; both printed when they disagree), **#3** (`driver_version` read from the copied original too), **#4** (fragment counts lifted into an H2 cell and `reported.rt_hashes.by_pair[*]`), **#5** (`walls_s.driver_build`, `walls_s.dry`, per-arm cargo time), **#8** (`ENV_RECORDER_OWN` anchored on its own clause start), **#9**'s seven minors, **#12** (the E4′ lock test diffs the whole pre-amendment range), **#17** (`line_rows_per_run` from the census or dropped, with a reason), **#25** (the e6q runner's stale docs, now that Task 1 split its test file), **#32** (`render_grain` literals derived), **#33** (the grain scan walks the directory), **#26**'s and **#35**'s runner-side one-liners (report which were taken).

- [ ] R5 binds: unit tests on synthetic records for every fix; no results file re-assembled; each E4″ gap gets a dated "closed at <commit>" line in `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp-findings.md`.
- [ ] Check `acceptance_e4p_read.py` and `acceptance_e4pp_phases.py` after the edits; split at a `# ----` banner if over 780 (R9).
- [ ] Full Python suite; every instrument module ≤ 800.

### Task 7: Ledgers, D notes, X strikes, versions, release (Python 0.8.7)

**Files:** `docs/CARRIED-DEBT.md` (this slice's section appended LAST: Settled with strikes of every A/B row taken, in the section where each was raised — `docs/CARRIED-DEBT-ARCHIVE.md`, `-ARCHIVE-2.md` and the live file all get their strikes; Deferred = the C rows restated in one line each with "C, not funded this slice"; Process lessons), the D notes (**#62–#66**, dated, in the ledger or the findings sibling — never inside a locked §1), the X strikes (**#67–#73**), `rust/HONESTY-BLIND-SPOTS.md` (**#49** the expression-position spawn declared; **#28**'s ledger half, R16 (v)), `rust/HONESTY-INDEX.md` (**#29**'s §11 row + the `JoinHandle` gloss and vector `v18`/`test_honesty_prose` items), the rung-4-entry design spec's continuation note (**#34**, a dated amendment), `rust/HONESTY-REFOCUS.md:181`'s bare rule and `refocus_cmd.py`'s two "two files" comments (**#11**), the three `chain.terminal` conformance vectors (**#23**, `docs/trace-format/vectors/` + the reader's vector test), `rm rust/target/release/cargo-sensorium` (**#15**, R7 — untracked), `CHANGELOG.md` (`## 0.8.7 — <date>` with every row taken, by number), `pyproject.toml` 0.8.7 + the editable-install refresh (`uv pip install -p .venv/bin/python -e . --no-deps`), `README.md`/`rust/README.md` tokens.

- [ ] Strikes and notes first (one commit); then the release commit in `c471b9d`'s shape with a `Gates:` paragraph carrying the real counts (Python; four Rust gates; corpus WITH the driver `--require-driver`; the ceiling gate).
- [ ] Box-path scan over `git diff --name-only f14d2f6`; every touched file ≤ 800; `pr-body.md` in the ledger.

### After Task 7 — final review, fix wave, PR

Final whole-branch review (fable): every split byte-identical; every A row either taken (with its strike) or reported with a reason; no behaviour change under a pre-registration; the C list intact. One fix wave (any file — nothing here is locked, but no results file is re-assembled); scoped re-review; push `feat/debts-buttonup`; PR; CI green; merge is Brice's; archive the ledger.

## Self-review

- Spec coverage: R1 → Task 5; R2 → Tasks 1–4; R3 → Task 3; R4 → not in slice (Task 7's Deferred restates #48 under C); R5 → Task 6; R6 → Tasks 4/6; R7 → Task 7; R8 → Task 7; R9 → Task 6. Every A row of §2 appears in exactly one task above (#1–5, 8, 9, 12, 17, 25, 26, 32, 33, 35 → T6; #6, 7, 10, 14, 18–21, 27, 28, 30, 31, 36, 37, 43, 45, 51 → T4; #13 → T3; #16, 22, 24, 38–42, 44, 46, 47, 50, 52–54 → T2; #11, 15, 23, 29, 34, 49 → T7); B rows → T1–T4; D → T7; X → T7.
- Placeholders: none; each row's fix is the inventory's stated one.
- Names: `refocus_threads.py`, `tracer_frames.py`, `tracer_exc.py`, `flow_programs.py`, `async_programs.py`, `convert_runner.rs`, `tests_terminals.rs`, `is_env_rule_note`, `tests/test_ceiling.py` — consistent between §1 of the design and the tasks.
