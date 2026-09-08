# Rung 4 slice 4 — the recorder's footprint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the recorder's own footprint from the refocus licence in three places (the driver's `RUSTDOCFLAGS` fragment, a program thread mistaken for the harness's, the session variables of the launching shell), measure the first two with E4″ over the 61 kept originals, and pay the small debts slice 3 named.

**Architecture:** Python-side licence changes in `refocus_env.py` / `refocus_world.py` (the driver and runtime are untouched); a corpus case falsifies the old harness rule under the real driver; the E4″ runner is a sibling entry over the E4′ instrument modules with two control arms; six files are split BEFORE anything else is edited.

**Tech Stack:** Python 3.12–3.14 (pytest), Rust 1.96.0 (`cargo test --workspace`, goldens), SQLite traces, the corpus harness `corpus/run_corpus.py`.

**Spec:** `docs/superpowers/specs/2026-09-08-sensorium-rung4-footprint-design.md` (rulings R1–R8; **amendment A-§3 supersedes §3**: R4 is *session set 1*, not a bearing set; §7 is E4″ in prose, which Task 3 locks).

## Global Constraints

- **Branch** `feat/rung4-footprint` off main `f598468`, main checkout `~/workspace/sensorium`; never push `main`; the merge is Brice's; one implementer at a time in the checkout.
- **Versions**: Python 0.8.5 → **0.8.6** (Task 9); `cargo-sensorium` 0.5.1 → **0.5.2** (Task 6); `sensorium-transform` 0.4.2 → **0.4.3** (Task 2); `sensorium-rt` stays 0.4.0; `TRACE_FORMAT` stays 4; `docs/TRACE-FORMAT.md` and `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` are never modified; PR #17's files untouched.
- **Pre-registration**: E4″ §1 alone, byte-locked (`awk '/^## 1/,/^## 2/' | sha256sum`, via `acceptance_rung3.byte_lock_facts`), dated amendments only, one measurement; a `.FAILED` before a number = infrastructure (relaunch from zero), after = STOP. **No `src/`, crate, corpus or instrument change after Task 8's measurement.** A dry run must differ from the real run in the dimension under test (an original from a different driver build).
- **Box rules**: cargo targets under `/mnt/extra/sensorium-rung2/` (`CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target` for this workspace, `corpus-target` for the corpus); one cargo at a time; never `pkill -f`; long runs `setsid nohup` with a pid file and `.DONE`/`.FAILED` markers; root disk ~5 GB free — nothing large on it.
- **Gates**: Python `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` (1864 collected at base); Rust `cd rust && cargo test --workspace && cargo test -p sensorium-rt --features test-hooks && cargo fmt --all -- --check && cargo clippy --workspace --all-targets -- -D warnings`; corpus WITH the driver = `cd rust && cargo build --release -p cargo-sensorium` then, from the repo root, `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/release/cargo-sensorium PYTHONDONTWRITEBYTECODE=1 .venv/bin/python corpus/run_corpus.py` (add `--require-driver` once Task 6 lands). **Every change to a printed sentence runs the corpus gate WITH the driver.**
- **Tests**: every new behaviour pinned by a mutation-tested test — mutate on a COMMITTED tree, purge `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`; none-vs-zero (`None` is unmeasured and named; `0` is measured); no test asserts a box path.
- **Repo hygiene**: no box path (`/mnt/extra`, `/home/brice`) in committed files except acceptance lens/pin rows and plans; every file ≤ 800 lines (split before growing); commits by explicit path, never `.superpowers/`; every commit ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`; task reports carry FIELD NAMES and file:line, never controller-supplied numbers.

---

### Task 0: The two docs ceilings — CARRIED-DEBT volume 2, HONESTY §13 → HONESTY-REFOCUS.md

**Files:**
- Create: `docs/CARRIED-DEBT-ARCHIVE-2.md`, `rust/HONESTY-REFOCUS.md`
- Modify: `docs/CARRIED-DEBT.md` (798 → ~225), `rust/HONESTY.md` (794 → ~640), `rust/HONESTY-INDEX.md:10-15` (the header sentence naming the moved files)

**Interfaces:** none (pure moves). Produces: `rust/HONESTY-REFOCUS.md` — the file Task 9's three amendments are appended to.

- [ ] Volume 2: header in the exact shape of `docs/CARRIED-DEBT-ARCHIVE.md:1-11` (title `# CARRIED-DEBT — volume 2`; the sentence that this is the second numbered volume, each kept under 800 lines, moved 2026-09-08 by rung 4 slice 4; **wording, order and strikes unchanged**; a deferred item is still open unless struck), then lines 21–595 of `docs/CARRIED-DEBT.md` at HEAD verbatim (slice 1 and slice 2's sections).
- [ ] Live file: delete 21–595; add one paragraph to the header after "The earlier sections moved 2026-09-06": rung 4 slices 1 and 2 moved 2026-09-08 to volume 2, archives are numbered volumes each under 800, this file keeps the newest sections and the next slice appends here.
- [ ] Verify the move is byte-exact: `diff <(git show HEAD:docs/CARRIED-DEBT.md | sed -n '21,595p') <(sed -n '<first body line>,$p' docs/CARRIED-DEBT-ARCHIVE-2.md)` prints nothing. Record the command and its empty output in the report.
- [ ] `rust/HONESTY-REFOCUS.md`: header in the shape of `rust/HONESTY-ERR-FLOW.md:1-12` (why this section, moved 2026-09-08, largest and most self-contained, unchanged wording/order, `§13` still names it), then `rust/HONESTY.md` lines 621–788 verbatim. In `rust/HONESTY.md` replace 621–788 with a stub in the exact shape of §11's (`rust/HONESTY.md:529-539`): heading `## 13. Refocus: the recorded command, run again one flag deeper`, one paragraph naming the file, the date, the ceiling, "**the wording and order are unchanged**", and that no citation of `§13` needed editing. `rust/HONESTY-INDEX.md` header: the sentence "Three sections themselves live one file away" becomes four, naming `rust/HONESTY-REFOCUS.md` for §13.
- [ ] Verify byte-exact as above against `git show HEAD:rust/HONESTY.md | sed -n '621,788p'`. `grep -rn "HONESTY.md#13\|HONESTY-REFOCUS" src tests rust docs README.md` — confirm no code reads §13 by line.
- [ ] Python suite green (`tests/test_honesty_prose.py` reads only `HONESTY-ERR-FLOW.md`); `wc -l` of all six files ≤ 800.
- [ ] Commit: `docs: CARRIED-DEBT volume 2 and HONESTY §13 move — two ceilings paid before the slice edits either file`

### Task 1: `refocus_cmd.py` → `refocus_report.py`

**Files:**
- Create: `src/sensorium/query/refocus_report.py`
- Modify: `src/sensorium/query/refocus_cmd.py` (789 → ~605)
- Test: `tests/test_refocus_report_split.py`

**Interfaces:** Produces `refocus_report.report(orig, new, res, orig_name, new_name, a)`, `_print_thread_line(orig, new, a)`, `_diverged_why(a)`, `_stamp(path, res, a)` — bodies byte-identical to `refocus_cmd.py:514-700`. `refocus_cmd.<name>` keeps resolving for all four through a re-export block in the shape of `refocus_cmd.py:159-165` (the `refocus_world` precedent, with the same three-line comment explaining one command in two files). `refocus_rust.py:451`'s import is untouched and resolves through the re-export.

- [ ] Write the failing test: the four names resolve from both modules to the SAME objects (`refocus_cmd.report is refocus_report.report`, etc.); `refocus_report` has a module docstring; `wc -l` of both files ≤ 800 (a test reading `Path(__file__)` relatives, no box path).
- [ ] Run it: FAIL (`refocus_report` missing).
- [ ] Move the four functions verbatim with the imports they need; add the re-export block; keep `refocus_cmd`'s module docstring where it is.
- [ ] Full Python suite green; `git diff --color-moved=zebra` shows only moves plus the two import blocks — paste `git diff --stat` in the report.
- [ ] Commit: `refactor(query): the report half of refocus_cmd moves to refocus_report.py — the ceiling paid before this slice's changes`

### Task 2: The transform's three splits (`sensorium-transform` 0.4.3)

**Files:**
- Create: `rust/sensorium-transform/src/visit/walk.rs`, `rust/sensorium-transform/src/assemble.rs`, `rust/sensorium-transform/src/lines/facts.rs`
- Modify: `visit.rs` (773 → ~510), `splice.rs` (762 → ~310), `lines.rs` (762 → ~425), `lib.rs:102-117` (`mod assemble;`), `rust/sensorium-transform/Cargo.toml` (0.4.3), `rust/Cargo.lock`

**Interfaces:** Produces the same public surface; internal paths change as listed. Callers of `crate::splice::run` become `crate::assemble::run` (grep; name each in the report).

- [ ] `visit.rs`: `mod walk;` and `visit/walk.rs` = `impl<'ast> Visit<'ast> for Ctx<'_>` (lines 514–773) verbatim. Exactly five `pub(super)` bumps: methods `fn_item`, `in_item`, `in_container`, `in_async_scope`, field `skipped`. `cargo test --workspace` green; fmt/clippy clean. Commit: `refactor(transform): the Visit impl moves to visit/walk.rs — Ctx stays where eight files import it`
- [ ] `splice.rs` → `assemble.rs`: `splice_order`, `run`, `assemble`, `check_spawn_ordinals`, `check_line_count`, `CRATE_ALLOW`, `CRATE_ALLOW_LEADING`, `unit_static`, `StaticPlacement` + `static_splice` + `checked_static_offset` + its impl + `adds_a_final_line`, `AllowPlacement` + `allow_placement` + `first_token_start` + `last_token`, and `#[cfg(test)] mod tests` (628–762) — verbatim. `stripped_prefix_len` STAYS (`census.rs` imports it). Zero visibility bumps expected; if one is needed, name it. Gates green. Commit: `refactor(transform): the splice engine and its tests move to assemble.rs — the vocabulary stays in splice.rs`
- [ ] `lines.rs`: `mod facts;` and `lines/facts.rs` = lines 444–762 verbatim (the free fns over `syn`). Exactly seven `pub(super)` bumps: `is_block_like`, `statement_span`, `stmt_diverges`, `is_conditionally_compiled`, `statement_deltas`, `binding_names`, `let_bindings`. Version 0.4.3 in `Cargo.toml` (+ `Cargo.lock`); `grep -rn "0.4.2" rust src tests corpus docs README.md CHANGELOG.md` — any pin of the transform token outside CHANGELOG history moves with it (name each). Gates green; goldens byte-identical (they are in the workspace tests). Commit: `refactor(transform): the statement facts move to lines/facts.rs (0.4.3) — three ceilings paid, behaviour byte-identical`
- [ ] Report: `wc -l` of the six Rust files; the three `git diff --stat`s; the bump list actually needed.

### Task 3: E4″ pre-registration — §1 alone, byte-locked

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md` (§0 + §1 ONLY), `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp-rows.md`, `rust/tests/acceptance_e4pp_lock.py`
- Test: `tests/test_acceptance_e4pp_lock.py`

**Interfaces:** Produces `acceptance_e4pp_lock.DOC`, `ROWS_DOC`, `RESULTS`, `BYTE_LOCK: str` (the commit that added §1), `ROWS_SHA256: str`; Task 7's runner imports these and refuses when `BYTE_LOCK` is falsy. Consumes the design §7 + A-§3 and the E4′ record's §1 as the shape (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md` §1.1–§1.5).

- [ ] Rows sibling: the 61 rows of E4′ §1.1 in the same order and columns, plus a column `expected licence` = `granted` / `WITHHELD (1 program thread)` / `WITHHELD (4 program threads)` per E4′ §1.2 (57 / 1 / 3). Source: `rust/tests/acceptance_e4p_rows.ROWS`; do not retype names — generate the table from `ROWS` and paste.
- [ ] §0 Provenance (one paragraph: what E4′ found, why a second build is the subject, design + amendment shas). §1 with: **1.1** subject = the 61 originals in the kept E4 store (driver 0.5.0), named by the rows file **and its sha256 printed here**; **1.2** the expected partition, E4′ §1.2's paragraphs and table verbatim (57 granted; the four named with 1/4/4/4; a WITHHELD reason that never subtracted is H1's STOP); **1.3** instrument = this slice's driver (`cargo-sensorium 0.5.2` built by the preflight from the measurement commit, sha recorded in §2), fresh `SENSORIUM_DIR` and `CARGO_TARGET_DIR`, arms A/B/C exactly as the design §7 + A-§3 define them (B injects `E4PP_INPUT=1`; C injects the first key of session set 1, in the list order of A-§3, absent from both the original's recorded env and the runner's, chosen and recorded at preflight), the launch guard (parity on every key outside session set 1 after the recorder's exclusions, the relocation rule and the strip; the session keys that differ recorded BEFORE any refocus — expected on this box, from the 2026-09-08 measurement, exactly `CLAUDE_CODE_SESSION_ID`; a different set is REPORTED, since the launch shell is the instrument's, not the subject's); the dry-run rule; **1.4** the H-table H1–H8 + `reported` copied from the design §7 with A-§3's substitutions (H4 = session names, H5 = `E4PP_INPUT`, H6 = the chosen session key), and the kills (a `.FAILED` before any number = infrastructure; after = STOP; measured once; bound 1.5 h; 1800 s per refocus; kill 6 = no `src`/crate/corpus/instrument change after the measurement); **1.5** what the record will publish beyond the table: the two tool hashes, `driver_version` on both sides, K and its names, wall per arm, arm B's verdicts.
- [ ] Commit the two docs: `docs(rung4): E4″ pre-registration — §1 alone, the 61 rows in a sibling`. Take its sha.
- [ ] Lock module with `BYTE_LOCK = "<that sha>"`, `ROWS_SHA256` = `sha256sum` of the rows file, `DOC`/`ROWS_DOC`/`RESULTS` paths (repo-relative via `acceptance_lib.REPO`).
- [ ] Lock tests: (1) `acceptance_rung3.byte_lock_facts(DOC, BYTE_LOCK, None)["identical"]` is True on the real tree; (2) §1 contains `ROWS_SHA256` and the rows file hashes to it; (3) a one-byte edit to §1 in a temp copy is refused; (4) §1 has rows `| H1 |` … `| H8 |` and `| reported |`; (5) the document has no `## 2` heading yet — pre-registration alone. Run: all PASS.
- [ ] Commit: `test(rung4): the E4″ lock — §1 byte-locked, the rows by sha256`

### Task 4: R1 the fragment strip + R4 session set 1 (Python 0.8.6's licence)

**Files:**
- Modify: `src/sensorium/query/refocus_env.py`, `src/sensorium/query/refocus_world.py:238-320` (`_env_diff`, `_env_state`), `docs/query.md:221-262`, `README.md:205-215`, corpus `questions.yaml` files whose expectations pin the env fact (name each)
- Test: `tests/test_refocus_env.py`, `tests/test_refocus_rust.py`, `tests/test_refocus_licence.py`

**Interfaces.** `refocus_env.py` produces:
- `RECORDER_FRAGMENT = re.compile(r"(?:^| )--extern sensorium_rt=(?P<dir>\S+/sensorium/rt/[0-9a-f]{16}/(?:unwind|abort))/libsensorium_rt\.rlib -L dependency=(?P=dir)(?= |$)")`
- `strip_recorder_fragment(value: str) -> tuple[str, int]` — every match removed, single spaces collapsed, ends trimmed, count returned.
- `_STRIPPED = "the recorder's own fragment stripped before comparing: "`; `stripped_clause(names: list[str]) -> str` = `f"{_STRIPPED}{', '.join(names)}"` or `""`.
- `SESSION_SET = 1`; `SESSION_ORDER: tuple[str, ...]` = A-§3's exact names in its printed order; `SESSION_EXACT = frozenset(SESSION_ORDER)`; `SESSION_PREFIXES = ("CLAUDE_CODE_",)`; `is_session_key(name: str) -> bool`.
- `is_relocation_note(fact)` true when `_RELOCATED in fact or _STRIPPED in fact` (docstring: the names a rule explained, by either rule).
`refocus_world._env_diff(was, now) -> tuple[list[str], list[str], list[str], list[str]]` = `(changed, relocated, stripped, session)`; per key, in order: skip `_UNCOMPARED_ENV`; strip both sides (a count > 0 on either side puts the key in `stripped`); equal → not a difference; `differs_only_by_root` on the remainders → `relocated`; `is_session_key` → `session`; else `changed`. Only `changed` withholds. `_env_state` signature unchanged; its lines, exactly:
- nothing in `changed` or `session`: today's strings byte for byte, plus the clauses (`relocated_clause`, `stripped_clause`, joined by `; `, prefixed `  ` on the line and `; ` on the fact — today's `on_line`/`on_fact` shape).
- only `session`: line `env: unchanged outside session set 1 (<N> variables compared; not compared: <ignored>; <K> session variable(s) differ: <names ≤8, +M more>)<clauses>`; fact `<N> environment variable(s) compared and unchanged outside session set 1 in the environment the rerun executed under; not compared: <ignored>; <K> session variable(s) differ: <names>` + clauses; caveat `None`.
- `changed` non-empty: today's `env: CHANGED since the original run -- <M> variable(s) differ: <names>   (names only)` over `changed` only, then `; <K> session variable(s) differ: <names>` when K > 0, then the clauses; today's caveat sentence over `changed`; the fact = clauses-or-None as today.
`N` = `len((set(was) | set(now)) - _UNCOMPARED_ENV)` as today. `refocus_rust._env_of`/`_verify` and `refocus_cmd.assess` unchanged (the re-export block already names `_env_diff`; callers of its old 2-tuple — grep `_env_diff(` in src and tests — are updated).

- [ ] Failing tests first, in `tests/test_refocus_env.py` (drive through `_pair` with `cargo_env`-style dicts at `/build/target-a` vs `/build/target-b`): (a) both sides carry the fragment with the two REAL hashes of E4′ §4 (`d9ce385a08c6646b` → `83d9294b8135c157`), roots moved → `env: unchanged (…)  … differ only by the target directory: …; the recorder's own fragment stripped before comparing: RUSTDOCFLAGS`, licence granted, `RUSTDOCFLAGS` absent from any relocated or changed list; (b) a world flag `--cfg docsrs` before our fragment on one side only → CHANGED naming `RUSTDOCFLAGS`; (c) two tokens naming different directories → nothing stripped, CHANGED; (d) a Python pair (no fragment) → lines byte-identical to today's; (e) `strip_recorder_fragment` unit cases: empty, fragment only → `("", 1)`, `"--cfg docsrs " + frag` → `("--cfg docsrs", 1)`, two fragments → count 2. Session set: (f) `CLAUDE_CODE_SESSION_ID` differing alone → granted, the exact new line with K = 1; (g) `TZ` differing → withheld naming `TZ`; (h) `CLAUDE_CODE_SESSION_ID` + `TZ` → withheld, both the CHANGED text and the `; 1 session variable(s) differ: CLAUDE_CODE_SESSION_ID` clause; (i) parametrised over every name in `SESSION_ORDER` and one `CLAUDE_CODE_X` → never withholds; (j) `CLAUDE_CODEX`, `XDG_SESSION_IDX` → withhold; (k) a key present on ONE side only that is a session key → `session`, not `changed`. `tests/test_refocus_licence.py::test_refocus_withholds_the_licence_when_the_environment_differs` stays byte-identical and green — it is the falsifier A-§3 names.
- [ ] Run: FAIL. Implement. Run: PASS. Full suite green.
- [ ] Mutate on the committed tree: invert `is_session_key`; drop the backreference from the regex; make `stripped` keys land in `changed`; drop the K clause. Each must fail a test. Restore, purge `__pycache__`.
- [ ] Docs: `docs/query.md` two paragraphs beside the relocation rule (`:232-262`): the fragment rule (what is stripped, why both tokens, the printed clause) and session set 1 (the list, the one-sentence argument per group, versioned with dated exits, the printed line, that everything else still withholds and why — A-§3's `REFOCUS_TEST_LIMIT` reasoning in one sentence). `README.md:205-215` gains one sentence naming both.
- [ ] Corpus gate WITH the driver (build the release driver first). Rust refocus cases whose `expect_contains` pin the env fact text now carry the strip clause — update the expectation to the printed line and name each edited file in the report. Summary line pasted.
- [ ] Commits: `feat(query): the recorder's own RUSTDOCFLAGS fragment is stripped before the environment compare (R1)` then `feat(query): session set 1 — session-identity variables are named and never withhold; everything else still does (R4, A-§3)`

### Task 5: R3 the harness anchor + the corpus case that falsifies the old rule

**Files:**
- Modify: `src/sensorium/query/refocus_world.py:348-391` (`harness_threads` + docstring), `tests/rust_traces.py:267-347` (`libtest_trace` gains two parameters), `corpus/rust/README.md`, `README.md` (the corpus count sentence near `:499`)
- Create: `corpus/rust/refocus_spawned_test_fn/{Cargo.toml,src/lib.rs,questions.yaml}`
- Test: `tests/test_refocus_licence_rust.py`

**Interfaces:** `harness_threads(trace) -> set[int]` keeps its signature. New rule, exactly: for each non-main thread, only its FIRST root (lowest frame id; `trace.roots()` is id-ordered so first-seen wins, later roots never add) decides; a thread whose `tasks` row name starts with `spawn@` or contains ` :: spawn@` is skipped BEFORE its root is read (`Trace.task(serial)`, `store/reader.py:202-208`); a root whose site has no row (the `async` shape) has no mark and is counted. The docstring says only what is true: root-anchored, first root, spawn-named never, `async` unmarked and counted, empty unless the main thread is recorded. `libtest_trace` gains `spawned_on_marked_fn: int = 0` (program threads whose root code is `TEST_FN` and whose `tasks` row name is `f"{TEST_FN} :: spawn@{TEST_FN}#{i+1}"`) and `two_roots: bool = False` (one program thread with root 1 = `WORKER_FN`, root 2 = `TEST_FN`, both `parent=None`, `depth=0`).

- [ ] Failing tests: (a) `spawned_on_marked_fn=1` → `harness_threads` = `{HARNESS_SERIAL}` only; the licence WITHHELD; the thread sentence `started 1 thread(s) besides the main one and 1 harness thread (`; (b) `two_roots=True` → the thread counted; (c) today's case (marked root on the libtest thread, no spawn name) → harness, kept; (d) a root whose code has no site row → counted; (e) `info` and `diff_notes` consumers still print the harness note (one assertion each, existing tests may cover). Run: (a) FAILS under the old rule (that is the point — record its failure output).
- [ ] Implement; PASS; full suite green; mutate (any-root instead of first; drop the spawn-name guard; match `spawn@` as a suffix) — each fails.
- [ ] Corpus case, copying `corpus/rust/spawned_thread`'s shapes: `Cargo.toml` (package `corpus_refocus_spawned_test_fn`, lib `refocus_spawned_test_fn`), `src/lib.rs` = `pub fn work() -> u32 { 7 }` and `#[cfg(test)] mod tests` with `#[test] fn helper_test() { assert_eq!(work(), 7); }` and `#[test] fn spawns_a_marked_fn() { std::thread::spawn(|| helper_test()).join().expect("joined"); }`; `cargo_args: ["test"]`. Questions (truth / why_logs_fail prose written in the corpus's voice): (1) `info $RUN` → `expect_line` with `threads started: 1 besides the main one and 2 harness threads (libtest's per-test thread, excluded as the recorder's own)` and the task name `spawn@tests::spawns_a_marked_fn#1`; (2) `refocus $RUN --focus tests::spawns_a_marked_fn` → `expect_contains` `licence: WITHHELD` and `started 1 thread(s) besides the main one and 2 harness threads`, `expect_absent` `licence: verified against`. The truth paragraph states the falsifier: under the root-mark-anchored rule this pair read `no thread started besides the main one` and GRANTED. Pin the printed lines from the real output only after checking them against this expectation; any mismatch is a finding for the report, not a reason to edit the expectation.
- [ ] `corpus/rust/README.md` row; `README.md` counts. Corpus gate WITH the driver green; summary pasted.
- [ ] Commit: `fix(query): the harness rule anchors on the FIRST root and never on a spawn-named task (R3, blind spot 28) — with the corpus case the old rule fails`

### Task 6: The small carried items + `cargo-sensorium` 0.5.2

**Files:**
- Modify: `rust/cargo-sensorium/tests/driver_smoke.rs:65,230,338`, `rust/cargo-sensorium/Cargo.toml` (0.5.2), `rust/Cargo.lock`, `corpus/run_corpus.py:536-599`, `.github/workflows/ci.yml:37-43,135-138`, `CHANGELOG.md` (new `## 0.8.6 (unreleased)` header at the top with this slice's bullets so far)
- Create: `tests/test_release_tokens.py`; a run_corpus test (in the existing `tests/test_run_corpus*.py` if one exists — grep — else `tests/test_run_corpus_require_driver.py`)

**Interfaces:** `run_corpus.main(argv)` accepts `--require-driver`; returns 1 when any case was skipped under it; the summary line gains `; --require-driver was given and <n> case(s) could not run`; `--json` output gains `"require_driver": bool` and, when it forced the exit, `"exit_reason": "<that sentence>"`.

- [ ] `driver_smoke.rs`: `.env("SENSORIUM_DIR", s.p("sensorium-dir"))` on the three `Command`s (the `spooldir.rs:77-83` shape); add `the_store_is_the_env_var_never_home`: `HOME` = scratch A, `SENSORIUM_DIR` = scratch B, run the driver once, assert a trace under B and no `A/.sensorium`. `cargo test -p cargo-sensorium` green.
- [ ] Failing tests for `--require-driver`: no driver + flag → returncode 1 and the sentence; no driver, no flag → 0 and today's skip note; `--json` fields. Implement; PASS.
- [ ] CI: the rust corpus step runs `python corpus/run_corpus.py --require-driver`; the Python matrix comment says "the Rust cases" with no number.
- [ ] `tests/test_release_tokens.py`: `pyproject.toml`'s version == `importlib.metadata.version("sensorium")` always; the newest `CHANGELOG.md` header `## X.Y.Z (unreleased)` → X.Y.Z is exactly pyproject's patch + 1; `## X.Y.Z — YYYY-MM-DD` → equals pyproject's and the date parses. Add the `## 0.8.6 (unreleased)` header now (the test's unreleased branch is the one that is green mid-slice).
- [ ] Version 0.5.2 (+ lock); `grep -rn "0\.5\.1" rust src tests corpus docs README.md` — any pin of the driver token outside CHANGELOG history moves with it (the slice-2 driver drift test may pin a shape, not a value — read it). Rust gates green.
- [ ] Commit: `chore(driver): 0.5.2 — the smoke tests keep their traces out of ~/.sensorium; corpus --require-driver in CI; the release tokens pinned`

### Task 7: The E4′ instrument gaps + the E4″ runner

**Files:**
- Modify: `rust/tests/acceptance_e4p_read.py` (`licence_partition`, new regexes), `rust/tests/acceptance_e4p_schema.py:185`, `rust/tests/acceptance_e4p_preflight.py:389-394` (+ a stdout/stderr helper), `rust/tests/acceptance_e4p_phases.py:206` (`refocus_one(paths, cfg, row, extra_env=None)`)
- Create: `rust/tests/acceptance_e4pp.py`, `acceptance_e4pp_arms.py`, `acceptance_e4pp_phases.py`, `acceptance_e4pp_preflight.py`, `acceptance_e4pp_schema.py`, `render_e4pp.py`
- Test: `tests/test_acceptance_e4pp.py`, `tests/test_acceptance_e4pp_arms.py`, `tests/test_acceptance_e4pp_phases.py`, plus the E4′ tests updated for the gap fixes (`tests/test_acceptance_e4p_read.py`, `_record.py`, `_preflight.py`)

**Interfaces.** Gap fixes: `licence_partition(parsed)` never leaves `program_threads`/`harness_threads` `None` when `parsed["licence"]` printed AND the `threads:` line parsed — it falls back to `threads_harness` (already parsed) and the threads line's program count, and records `counts_source: "licence-clause" | "threads-line" | None`; `assemble_e4p`'s `licence_verified_counts` = `{"source_verified": n, "env_verified": n, "exit_verified": n, "output_unverifiable": n, "children_unverifiable": n, "n": rows}` counted over `raw_pass2.refocuses[*].licence` (the E4′ results file is NOT re-assembled — records are not rewritten); the version probe = `{"token": str | None, "reason": str | None}` from `importlib.metadata.version("sensorium")` capturing stdout AND stderr. New parser fields in `parse_refocus`: `env_stripped_keys` (from `ENV_STRIPPED = re.compile(r"the recorder's own fragment stripped before comparing: (?P<names>[^;)\n]+)")`), `env_session_n: int | None`, `env_session_keys: list[str]` (from `(?P<k>\d+) session variable\(s\) differ: (?P<names>[^)\n]+)`, names de-suffixed of `, +N more`), `env_unchanged_outside_session: bool`.
E4″: `acceptance_e4pp.py` = the E4′ entry's shape with `PLAN = REPO/.superpowers/sdd/2026-09-08-sensorium-rung4-footprint`, `BASE = PLAN/"acceptance-e4pp"`, `E4PP_ENV` mapping `SENSORIUM_E4PP_TARGET → "sensorium_e4p_target"` (the shared phases read that key; the mapping is documented in a comment), `SCHEMA_VERSION = "e4pp/1"`, locks from `acceptance_e4pp_lock`, markers `e4pp.DONE`/`e4pp.FAILED`, `--dry` (2 pairs: the first row expected granted and `a_pager_can_be_shared_across_threads`, outputs to `-dry` siblings, never the tracked results). `acceptance_e4pp_arms.py`: `ARM_B_KEY = "E4PP_INPUT"`, `arm_rows(rows) -> list[dict]` (the first three rows whose expected licence is granted, in rows order, plus the row named `a_pager_can_be_shared_across_threads` — by FIELD, never by index), `choose_session_key(original_env: dict, environ: dict) -> str | None` (first of `refocus_env.SESSION_ORDER` absent from both; `None` is a Refused at preflight), `arm_env(base: dict, key: str, value: str) -> dict`, `run_arm(paths, cfg, rows, key, value, tag) -> dict` reusing `eph.refocus_one(..., extra_env={key: value})`. `acceptance_e4pp_preflight.py`: `session_parity(kept, rows, environ=None) -> dict` = E4′'s `env_parity` shape with `is_session_key` differences allowed and returned as `session_differs: list[str]` (sorted), everything else `Refused` naming every key. `acceptance_e4pp_phases.py`: `phase_h1 = eph.phase_h1`; `phase_h2_fragment(two)`; `phase_h3_verdict_pair(two)` (E4′'s H2 + H3); `phase_h4_session(two, session_differs)`; `phase_h5_input(arm_b)`; `phase_h6_session_key(two, arm_c, session_differs, key)`; `phase_h7_instrument(raw)`; `phase_h8_nothing_else(paths)` = `eph2.phase_h6` with the corpus command carrying `--require-driver`. Every phase returns `{"verdict": "PASS"|"STOP"|"REPORTED", ...}` and `None` for any cell it could not read, with a `dropped` list.

- [ ] Gap fixes with failing tests first (a WITHHELD-by-env parsed record → counts from the threads line, `counts_source == "threads-line"`; a granted one → `"licence-clause"`; `licence_verified_counts` from a two-row raw; the probe on a missing module → `token None`, reason non-empty). E4′'s existing tests green. Commit: `test(rung4): E4′ instrument gaps closed — the partition reads the threads line and says so, verified counts from the rows, the version probe records null with its reason`
- [ ] E4″ modules with failing tests first: parser regexes on real-shaped lines (build the lines from Task 4's exact templates); `arm_rows` by field; `choose_session_key` (absent-on-both rule; list order; `None`); each phase on synthetic records incl. the None-vs-zero cells, a killed pair, and a pair whose `RUSTDOCFLAGS` sits in the changed list (H2 STOP); the lock wiring refuses on a falsy `BYTE_LOCK`; every instrument module ≤ 800 (parametrised like `tests/test_acceptance_e4p.py:500`). Mutation on the phases (flip one comparison each). Commit: `test(rung4): the E4″ runner — a sibling entry over the E4′ modules, arms B and C, the session-aware guard`
- [ ] Report: module line counts; the `paths` keys and env names the launcher must export (`SENSORIUM_DRIVER`, `SENSORIUM_E4_STORE`, `SENSORIUM_BLOOMERY`, `SENSORIUM_E4PP_TARGET`, `SENSORIUM_DIR`, `SENSORIUM_RUST_TARGET`, `SENSORIUM_CARGO_SENSORIUM`, plus the three pins `PYTHONDONTWRITEBYTECODE`, `SSL_CERT_DIR`, `SSL_CERT_FILE`, and `unset TMPDIR`).

### Task 8: Measure E4″ once (controller-run), then write §2–§5

**Files:**
- Create (ledger, uncommitted): `.superpowers/sdd/2026-09-08-sensorium-rung4-footprint/acceptance-e4pp/launch.sh`
- Modify (after the run): `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md` (§2–§5), `-rows.md` (measured columns), `.results.json` (assembled by the runner)

- [ ] Controller: `rm -rf /mnt/extra/sensorium-rung2/bloomery-target-e4` (R8; record `df -h /mnt/extra` before/after in the ledger). Launcher in the archived E4′ shape with the E4″ names; `--dry` first: read the two pairs' output — the strip clause present, `RUSTDOCFLAGS` in no changed list, the session line naming exactly the preflight's set, the two licence words as expected. An instrument defect found here is fixed and the lens amended (dated, before any real number); an expectation is never edited.
- [ ] Real run: `setsid nohup launch.sh > logs/e4pp.log 2>&1 &`; poll the markers (never `pkill -f`; on a bound, kill the pgid); `.DONE` → the runner assembled `RESULTS` and rendered §2/§3.
- [ ] Implementer (fresh, given FIELD NAMES only): write §4 (each H, the cells from `results.json` by key path, both readings) and §5 (what the numbers mean; gaps found; what the record does not license), in the E4′ record's voice; fill the rows sibling's measured columns from `results.json`; `CHANGELOG.md` 0.8.6 bullet naming the verdicts. The rows sibling's sha changes → §1 stays byte-identical (the lock is on §1's text; the sibling's sha in §1 names the PRE-measurement rows file — state in §2 that the measured columns were appended after and give both shas).
- [ ] Commit: `docs(rung4): E4″ measured once — <H1..H8 verdicts in one line>`

### Task 9: Docs, versions, close-out (Python 0.8.6)

**Files:**
- Modify: `rust/HONESTY-REFOCUS.md` (three dated amendments), `rust/HONESTY-BLIND-SPOTS.md` (27, 28 closed with dated clauses, never deleted; new item 29), `rust/HONESTY-INDEX.md` (§13 rows cite E4″ H1/H2, the corpus case, the tests; a §8 row for 29), `docs/query.md` / `README.md` (only if Task 4 left a sentence stale; the Rust section's E4′ paragraph gains E4″'s result), `CHANGELOG.md` (`## 0.8.6 — <date>`), `pyproject.toml` (0.8.6), `docs/CARRIED-DEBT.md` (this slice's section: Settled with strikes of slice 3's bullets this slice paid — RUSTDOCFLAGS, R1's anchor, `SENSORIUM_DIR`, the corpus gate, the release tokens, the docstring, the five ceilings; Deferred with rulings — R7's four, session set 1's exits, the rung-5 lever "env reads as recorded facts: compare only the variables the program READ"; Process lessons)
- Create (ledger): `pr-body.md`

- [ ] Item 29, declared: a session-set variable a program reads is not compared — named on the line, never withholding; falsified by a program whose output depends on a key in `SESSION_ORDER`.
- [ ] `pyproject.toml` 0.8.6, then `uv pip install -e .` (or the venv's editable refresh) and verify `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` prints `0.8.6`; `tests/test_release_tokens.py` green in the dated state.
- [ ] Box-path scan over every file this slice touched: `git diff --name-only f598468 | xargs grep -ln "/mnt/extra\|/home/brice"` — only acceptance lens/pin rows and plans may appear.
- [ ] Gates: Python suite; Rust gates; corpus WITH the driver `--require-driver`; every touched file ≤ 800.
- [ ] Release commit in `c471b9d`'s shape (message body: the token transition, the install refresh, each doc, then a `Gates:` paragraph with the real counts). Commit: `chore(release): sensorium 0.8.6 — the recorder's footprint (driver 0.5.2, transform 0.4.3)`

### After Task 9 — final review, fix wave, PR

Final whole-branch review (fable): src correct against R1/R3/R4 + A-§3; every prose number in the record traces to `results.json`; the lock shas verified in-tree and in `git show`. One fix wave (instrument/tests/docs only — never `src/` after the measurement); scoped re-review; push `feat/rung4-footprint`; open the PR with `pr-body.md`; CI green on all checks; merge is Brice's. Then: delete the branch local+remote, verify origin sync, archive the ledger dir to `/mnt/extra/sensorium-rung2/sdd-archive/2026-09-08-sensorium-rung4-footprint/`, update memory.

## Self-review

- Spec coverage: R1 → Task 4; R2 → Tasks 3, 7, 8; R3 → Task 5; R4 (A-§3) → Task 4; R5 → Tasks 0–2; R6 → Tasks 5 (docstring) and 6; R7 → Task 9's Deferred; R8 → Task 8; §1 what ships items 1–6 → Tasks 4/5 (1), 6 (2), 2 (3), 5/6 (4), 7/8 (5), 9 (6).
- Placeholders: none; every printed string is given verbatim where a task pins it.
- Names used across tasks: `strip_recorder_fragment`, `stripped_clause`, `SESSION_ORDER`, `SESSION_EXACT`, `SESSION_PREFIXES`, `is_session_key`, `_env_diff` 4-tuple, `harness_threads`, `libtest_trace(spawned_on_marked_fn, two_roots)`, `acceptance_e4pp_lock.{DOC,ROWS_DOC,RESULTS,BYTE_LOCK,ROWS_SHA256}`, `refocus_one(..., extra_env)`, `session_parity`, `choose_session_key`, `arm_rows`, `ARM_B_KEY` — consistent between the task that defines and the tasks that consume.

## Amendments

Appended, never edited in place: the task text above is the record of what was
planned, and each note below says how a line of it was read when it was
executed.

- **2026-09-08 — line 178's "instrument/tests/docs only" reads as kill 6.**
  The "After Task 9" paragraph calls the post-review fix wave
  "instrument/tests/docs only — never `src/`", which is looser than the rule it
  serves: the Global Constraint at line 17 and §1.4's locked **kill 6** forbid
  any `src/`, crate, **corpus or instrument** change after Task 8's
  measurement. The narrower rule governs. The fix wave therefore never touches
  `rust/tests/acceptance_e4pp*.py` or `rust/tests/render_e4pp.py` — the
  instrument that produced the numbers — nor `corpus/`; it may touch
  `tests/` and `docs/` only. Line 178 stands as written; this note is how it
  was read.

- **2026-09-08 — line 159's `rm -rf` was superseded by design amendment A-R8
  and nothing was deleted.** Task 8's first bullet instructs the controller to
  `rm -rf /mnt/extra/sensorium-rung2/bloomery-target-e4` before the launch,
  citing R8. **A-R8** (design §, dated 2026-09-08, taken *before* the
  measurement at `2b0eb5b`) superseded it: deleting is a destructive action and
  those are Brice's, not the design authority's, and the run did not need the
  space. Nothing was removed. E4″ built into a fresh `bloomery-target-e4pp`
  beside the kept ones, and `bloomery-target-e4` and `-e4p` are named in the
  close-out (`docs/CARRIED-DEBT.md`, Deferred) as Brice's to free. The `df -h`
  before/after this bullet asks for therefore brackets a launch, not a
  deletion.
