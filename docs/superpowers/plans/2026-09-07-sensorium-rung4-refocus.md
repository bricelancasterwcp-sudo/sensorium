# Rung 4 slice 2 — `refocus` for Rust traces, and E4 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sensorium refocus <run> --focus <q>` works on a Rust trace by re-invoking the original `cargo sensorium` command under the added focus and comparing the pair, and the pre-registered E4 (refocus MATCH rate over the 61 tests of the seven `FakeSubstrate` pager files) is measured once.

**Architecture:** The driver learns `--refocus-of <run>` and the converter records `workspace_root`, `refocus_of` and `invocation_processes`, flipping `capabilities.refocus` to true. Python's `refocus` gains a Rust branch in a new module: five pre-rerun refusals, a subprocess re-run from the workspace root under the same store, the pair found by `refocus_of`, the unchanged fingerprint comparator, the same stamps, and two UNVERIFIABLE licence caveats. The transform's brace-macro tail guard lands first so E4's focused builds run the fixed transform.

**Tech Stack:** Rust (`cargo-sensorium` driver/converter, `sensorium-transform`), Python 3.12+ (`sensorium` query CLI, pytest), the E9 acceptance-runner pattern.

**Spec:** `docs/superpowers/specs/2026-09-07-sensorium-rung4-refocus-design.md` (rulings G1–G3; §2–§4 approved; §4 is E4 in prose, which Task 0 turns into the locked §1).

## Global Constraints

- **Branch** `feat/rung4-refocus` off main `2883a50`, in the main checkout; never push `main`; the merge is Brice's. The S0 session owns PR #17 and its worktree — never touch them.
- **Versions**: `cargo-sensorium` 0.4.0 → **0.5.0** (Task 2), `sensorium-transform` 0.4.0 → **0.4.1** (Task 1), `sensorium-rt` **0.4.0 unchanged**, Python `pyproject.toml` 0.8.3 → **0.8.4** (Task 7), `TRACE_FORMAT` **4**. `docs/TRACE-FORMAT.md`: exactly ONE place — the `refocus` capability prose (PR #17 owns the file; merge `main` first if #17 landed).
- **The pre-registration** (E4 §1) is committed ALONE (Task 0) and byte-locked by `awk '/^## 1/,/^## 2/' <doc> | sha256sum`; dated amendments only (both shas carried); both readings pre-committed; one measurement; `.FAILED` before any number = infrastructure, after = a STOP. **After Task 6's measurement no `src/` or crate source changes** — the final fix wave is docs/tests/instrument only.
- **Box rules**: every cargo target under `/mnt/extra/sensorium-rung2/` (workspace: `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target`; E4: a FRESH `bloomery-target-e4`, a FRESH `sensorium-dir/e4`); one cargo at a time (`pgrep -a cargo` empty first); root disk ≈12 GB free; `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9` is READ-ONLY; never `pkill -f`; long runs `setsid nohup … &` with pid file + `.DONE`/`.FAILED` markers.
- **Repo hygiene**: no box-local path in a committed file except the record's lens/pin rows and this plan (the box-path scan now covers `rust/*/tests`); every file ≤ 800 lines, split BEFORE growing (`refocus_cmd.py` 757, `driver.rs` 763, `lines.rs` 749 are near); commits by explicit path (never `git add -A`, never `.superpowers/`); every commit ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`; `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` is Brice's — never modify.
- **Tests**: every new behaviour pinned by a test that FAILS under a one-line mutation of the pinned line (mutate a COMMITTED tree; purge `__pycache__`; `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`; Rust `cargo test -p <crate>`). None-vs-zero: unmeasured is `None` and named, never 0.
- **Notation**: the refusal sentences are the design's §2.3 table verbatim; verdict words are the tool's (MATCH / DIVERGED / REFUSED, exits 0/1/3; pre-rerun refusals exit 2).

---

## File map

| file | responsibility |
|---|---|
| `rust/sensorium-transform/src/lines.rs` (`Stmt::Macro` arm) + `tests/golden_focus/focus_macro_tail*` + `tests/common/mod.rs` | G1 guard; the compile-fail case becomes a compile-pass golden |
| `rust/cargo-sensorium/src/driver_args.rs` | `--refocus-of` parsing (`DriverArgs.refocus_of: Option<String>`) |
| `rust/cargo-sensorium/src/refocus_of.rs` (new) | the store check (`$SENSORIUM_DIR/traces/<id>.db` exists) and the refusal sentence |
| `rust/cargo-sensorium/src/driver.rs` | `Invocation.refocus_of`; one call to the check before any build |
| `rust/cargo-sensorium/src/convert/meta.rs`, `convert/mod.rs` | `workspace_root`, `refocus_of`, `invocation_processes`; `capabilities.refocus: true` |
| `src/sensorium/query/refocus_rust.py` (new) | the Rust branch: refusals, re-run, pair lookup, caveat markers |
| `src/sensorium/query/refocus_cmd.py`, `refocus_world.py`, `vocab.py`, `info_cmd.py` | dispatch on `lang == "rust"`; UNVERIFIABLE output/children on a Rust pair; `no_rerun_note` retired; `refocus_of` printed |
| `tests/rust_traces.py`, `tests/test_refocus_rust.py` (new) | fixture keys; the Python pins |
| `corpus/rust/refocus_match`, `refocus_diverged`, `refocus_refused_many` | the printing gate |
| `rust/tests/acceptance_e4*.py`, `render_e4.py`, `tests/test_acceptance_e4*.py` | the instrument |
| `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md` (+ `.results.json`) | the record |
| docs, HONESTY*, CHANGELOG, CARRIED-DEBT, inbox, READMEs, `pyproject.toml` | Task 7 |

---

### Task 0: E4 pre-registration — §1 committed alone and locked

**Files:** create `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md` (header + `## 1. Pre-registration`; `## 2`–`## 5` headings carry `(written by Task 6)`). Inputs, read-only: the clone at `e209ed9`, `crates/bloomery-daemon/tests/{pager_codec_gate_test,pager_obligation_test,pager_refusal_advice_test,pager_remove_agent_test,pager_reservation_test,pager_test,pager_weights_test}.rs`; the E9 record's §1 as the form; design §4.

**Produces:** §1 with: the 61 `#[test]` fn names per file (enumerated from the source, each with its line), the per-test argv of pass 1 (`cargo sensorium test -p bloomery-daemon --test <file> -- <name> --exact`) and of pass 2 (`sensorium refocus <run> --focus <name>`), the expected-MATCH list (all 61, the thread test named), H1–H7 with both readings and the verdict words (PASS / STOP / finding / REPORTED) exactly as design §4's table, the lens (fresh locations, tier default, audit log not silenced, `TMPDIR` observed, the clone read-only, the driver built from this branch's HEAD, the shim count/size measured under the target dir), the kill rules, and the three H5 `watch` triples (E9's W1 and W3 on the refocused `missing_stats_is_a_contract_violation_not_a_reply` — copy their `--expr`, predicted verdict class and line from E9 §1.2 — plus one triple from another file derived from its source with certainty).

- [ ] Enumerate the 61 tests (`grep -n '#\[test\]' -A1` per file; count 20/15/4/4/8/4/6) and any `#[ignore]` (an ignored test is not run by `--exact`? — check libtest: `--exact <name>` runs it only with `--ignored`; if any is ignored, pre-register it as EXCLUDED with the reason and adjust N).
- [ ] Write §1; no box path except the lens rows; commit ALONE: `docs(rung4): E4 pre-registered — §1 alone, before the instrument`; ledger the sha and `sha256sum`.

### Task 1: The guard (G1) — `sensorium-transform` 0.4.1

**Files:** modify `rust/sensorium-transform/src/lines.rs` (the `Stmt::Macro` arm at ~:256-268: when `is_tail` and the delimiter is a brace, no probe), `rust/sensorium-transform/tests/common/mod.rs` (move `focus_macro_tail` from the compile-fail list to `FOCUS_CASES`), `tests/golden_focus/focus_macro_tail.{in,out}.rs` (the `.out.rs` now pins `ret(…, m! { 1 })` with NO `line(` after it; a unit fn `fn u() { m! { a } }` pins one fewer LINE), `rust/HONESTY-BLIND-SPOTS.md` (the brace-macro bullet struck + "fixed in 0.4.1" correction), `Cargo.toml` 0.4.1 (+ pins).
**Interfaces:** consumes `is_tail` as `statement_end(stmt, is_tail)` receives it (`lines.rs:239`). Produces: no LINE after a tail brace macro; every other golden byte-identical.
- [ ] Failing test first: move the case to `FOCUS_CASES` with the new `.out.rs` → the byte pin fails on the extra `line(`; oracle compiles it after the fix. Mutation: revert the guard → the byte pin and the oracle red.
- [ ] `cargo test -p sensorium-transform` green; clippy; fmt; commit `fix(transform): a brace-delimited macro in tail position takes no LINE probe — the focused build of a quote!-shaped fn compiles (0.4.1)`.

### Task 2: Driver `--refocus-of` and converter meta — `cargo-sensorium` 0.5.0

**Files:** `driver_args.rs` (`DriverArgs.refocus_of: Option<String>`; `--refocus-of <v>` / `=<v>`, before the first `--`, at most once → `Err("--refocus-of given twice")`; empty value → `Err("--refocus-of needs a run id")`), new `rust/cargo-sensorium/src/refocus_of.rs` (`pub fn check(store: &Path, run_id: &str) -> Result<(), String>` — refuses `REFUSED: --refocus-of <run-id> names no trace in <store>; nothing was built.` when `<store>/traces/<run-id>.db` is absent; the store is `$SENSORIUM_DIR` resolved as `runid.rs` resolves it), `driver.rs` (call the check before resolution/build; `Invocation.refocus_of: Option<String>`), `convert/meta.rs` + `convert/mod.rs` (`workspace_root` from the invocation record; `refocus_of` when present; `invocation_processes` = `runner_processes`; `CAPABILITIES` `("refocus", true)`), `src/sensorium/query/info_cmd.py` (print `refocus_of` where the Python key prints — it is the same key; confirm nothing branches on lang), version 0.5.0 (+ `DRIVER_VERSION`, smoke test pins, `Cargo.lock`).
**Produces:** meta keys `workspace_root` (str), `refocus_of` (str, optional), `invocation_processes` (int); `capabilities.refocus == true` on every trace this driver converts.
- [ ] Failing tests: `parse_args` cases (given, `=` form, twice → Err, empty → Err, after `--` ignored); `refocus_of::check` on a temp store (present → Ok; absent → the exact sentence); converter tests: a synthetic invocation record with `refocus_of` → the meta key on every process; without → absent; `invocation_processes` equals the runner count (1 and 2); `capabilities.refocus` true; `workspace_root` present.
- [ ] End-to-end by hand on `corpus/rust/silent_swallow` (scratch target + store under `/mnt/extra/sensorium-rung2/`): `run` → then `--refocus-of <that run> --focus load run` → `info` on the new trace shows `refocus_of`, `workspace_root`, `invocation_processes: 1`, `capabilities.refocus: true`; `--refocus-of nosuch run` → the sentence, exit 2, nothing built. Paste outputs. Mutations: the store check inverted; `invocation_processes` hard-coded 1.
- [ ] Commit `feat(driver,convert): --refocus-of links a re-run to its original; meta records workspace_root, refocus_of and invocation_processes; capabilities.refocus true (0.5.0)`.

### Task 3: Python — the Rust branch of `refocus`

**Files:** create `src/sensorium/query/refocus_rust.py` (≤ 800), modify `refocus_cmd.py:735` `run` (after the capability/`incomplete` checks: `if trace.lang == "rust": return refocus_rust.run(args, orig, orig_name, meta)`; nothing else in the Python branch changes), `refocus_world.py` (`_output_difference` and the children/spawn check return an UNVERIFIABLE caveat when `capabilities.output`/`children` is false — a new marker string `output: unverifiable (not recorded)` / `children: unverifiable (not witnessed)`, added to `_licence_caveats` and stamped; the licence is NOT withheld by them), `vocab.py` (RUST `no_rerun_note` retired; a `refocus_blind_spots` tuple: output not recorded; threads from dependency code unnamed; the re-run's rebuild is its own cost), `tests/rust_traces.py` (fixture builders gain `workspace_root`, `invocation_processes`, `refocus_of`, `cargo_args`, `env`, `source_hashes`), create `tests/test_refocus_rust.py`.
**Produces:** `refocus_rust.run(args, orig: Trace, orig_name: str, meta: dict) -> int`; `refocus_rust.refusal(meta, args, driver) -> str | None` (the five sentences of design §2.3, in order); `refocus_rust.rerun_argv(meta, requested_focus, driver) -> list[str]` (`[driver, "--refocus-of", run_id, ("--tier", tier)?, ("--focus", v)*, *cargo_args]` with the merged order original-then-caller); `refocus_rust.find_pair(store, run_id, launched_at) -> list[str]` (run ids with `refocus_of == run_id` recorded after `launched_at`); `refocus_rust.driver() -> str | None` (identical to `run_corpus.cargo_driver`: env then PATH — import or copy; say which).
- [ ] Failing tests first (fixture traces, no cargo): each refusal sentence and exit 2 in order; `rerun_argv` exact list incl. tier from `env["SENSORIUM_TIER"]` and the merged focus order; `find_pair` 0/1/2 with the timestamp filter; the re-run is launched with `cwd == workspace_root` and the caller's env plus `SENSORIUM_DIR` (patch `subprocess.run`, assert the call); the pair 0 → REFUSED exit 3 naming the driver exit and last stderr line; 2 → REFUSED naming the count and the selector sentence; 1 → `diff_cmd.compare` called on the pair and the stamps written into the NEW trace (read them back); the two UNVERIFIABLE caveats present, `refocus_licence` not withheld by them, and the old output check never says verified on a Rust pair; `--window` refused; `no_rerun_note` gone from the Rust REFUSED path (the capability refusal for OLD traces without `workspace_root` still prints the §2.3 sentence). Mutations: drop the timestamp filter; merged-focus order swapped; the output caveat replaced by "verified".
- [ ] Commit `feat(query): refocus on a Rust trace — five refusals, the re-run from the workspace root, the pair by refocus_of, two unverifiable licence checks`.

### Task 4: Corpus — three refocus cases

**Files:** `corpus/rust/refocus_match/`, `refocus_diverged/`, `refocus_refused_many/` (+ `corpus/rust/README.md`). Each question that runs `refocus` re-invokes the driver inside the gate (`run_corpus` passes `SENSORIUM_CARGO_SENSORIUM` through — confirm `plain_env`-style stripping does not remove it for `refocus`; if it does, the runner needs `SENSORIUM_CARGO_SENSORIUM` re-added for `refocus` questions — say so).
- `refocus_match`: `fn fill()` program, `cargo_args: ["run"]`; `refocus $RUN --focus fill` → `verdict: MATCH`, exit 0; then `info` on the NEW run (the runner must learn the new run id — pin via `runs` showing `refocus_of`, or `info $RUN2` if the runner supports a second run ref — design the question around what the runner can address; if it cannot address the new run, pin `refocus`'s own stdout lines naming the new run and `line=yes`).
- `refocus_diverged`: `main` writes `marker` on the first run if absent and branches on its presence; `refocus $RUN --focus main` → `DIVERGED`, exit 1, the divergent event line.
- `refocus_refused_many`: a crate with `tests/a.rs` and `tests/b.rs`, `cargo_args: ["test"]`; `refocus $RUN --focus …` → the selector sentence, exit 2; `runs` shows no new invocation.
- [ ] Derive each pin from design §3.4 before running; gate: `tests/test_corpus.py` with the built driver → 61 cases, 0 failures; mutation per case (an exit).
- [ ] Commit `test(corpus): refocus_match, refocus_diverged, refocus_refused_many — the Rust refocus loop pinned`.

### Task 5: E4 runner (instrument), locked to Task 0

**Files:** `rust/tests/acceptance_e4.py` (+ `_phases.py`, `_read.py`, `_schema.py`, `_cells.py`, `render_e4.py` as the E9 family; each ≤ 800), `tests/test_acceptance_e4*.py`. Reuse `acceptance_lib`, `acceptance_rung3.byte_lock_check`, and the E9 modules' helpers by import where they are generic (killed-cell rule, `measurement_keys`, the box-path scan).
**Env contract:** `SENSORIUM_DRIVER`, `SENSORIUM_BLOOMERY`, `SENSORIUM_E4_TARGET` (fresh), `SENSORIUM_DIR` (fresh), `SENSORIUM_RUST_TARGET`; `BYTE_LOCK` = Task 0's sha. Phases: preflight (clone sha/porcelain/`Cargo.lock`; fresh locations; driver sha; `TMPDIR`; the 61 names re-derived from the source and compared to §1's list — a mismatch is a refusal); pass 1 (61 originals, each `guarded` at 1800 s, the first is the cold build); pass 2 (61 `sensorium refocus <run> --focus <name>` through the CLI with the driver env, each guarded at 1800 s; stdout/stderr, exit, the new run id from the store by `refocus_of`); H1–H7 per §1 with both readings; the shim census (count and bytes of `<target>/sensorium/shim/*`); H5's three `watch` triples on the NEW traces; H7 (corpus incl. the three new cases, pytest, `cargo test --workspace`). Killed-cell rule structural; `--assemble`/`--render`; markers `e4.DONE`/`e4.FAILED`; `exit=7` STOP classes (H2 build failure; H3 REFUSED) vs `exit=3` infrastructure.
- [ ] Box-free tests (lock facts incl. both shas if amended, schema completeness, none-vs-zero, the all-killed walk, the parsers on REAL `refocus` output produced from `corpus/rust/refocus_match` under the warm corpus target, the name-list check, the box-path scan); mutations; dry run over a hand-written raw record.
- [ ] Commit `test(rung4): E4 runner — refocus measured over the 61 pager tests, locked to <sha>`.

### Task 6: Measure E4 once; §2–§5 of the record

Exactly Task 8 of slice 1's discipline: preflight, build the driver from HEAD, the launcher `<ledger>/acceptance-e4/launch.sh` (five env vars, `TMPDIR` unset), `setsid nohup`, poll ≤ 2 h, read nothing before the marker, the kill rules, determinism, §2–§5 with every number naming its field, §1 sha unchanged, commit record + results.json.

### Task 7: Docs, versions, close-out

`rust/HONESTY.md` (a §13 promise: refocus on a Rust trace re-invokes the recorded command under the added focus and compares the causal fingerprints; falsifiers: E4 H3; a MATCH on a pair whose fingerprints differ), `HONESTY-BLIND-SPOTS.md` (output/children unverifiable on a refocus; multi-process invocations refused), `HONESTY-INDEX.md`, `docs/TRACE-FORMAT.md` (the ONE `refocus` capability sentence: "for `lang = rust`, true for traces converted by cargo-sensorium ≥ 0.5.0; a trace of a multi-process invocation is refused by `refocus`, not by the capability"), `rust/README.md` (`--refocus-of`; the "Not yet" list loses `refocus`, keeps `--window`), `docs/query.md` (`refocus` on Rust: the refusals, the pair, the caveats), `CHANGELOG.md` (`## 0.8.4 — <date>` + crates block driver 0.5.0 / transform 0.4.1; E4 as recorded), `pyproject.toml` 0.8.4, `docs/CARRIED-DEBT.md` (new section: settled — the guard, refocus; deferred — `--window`, multi-process refocus, the opt-out, hard-linked shim, `fn_items` cost, `focus_matched` staleness (still); process lessons), the inbox (`refocus` + E4 struck as shipped; `--window` remains), the debugging skill's contract unchanged (`sensorium refocus last --focus …` now answers on Rust). Full gate; PR body draft in the ledger.

### After Task 7 — final review, fix wave, PR

Whole-branch review (fable) on `2883a50..HEAD`; the classification rule (no src/crate change after Task 6's measurement); ONE fix wave; scoped re-review; push; PR (merge main first if #17 landed); CI green; merge is Brice's.

## Self-review

- Spec coverage: §2.1 → T2; §2.2 → T2; §2.3 → T3; §3.1/§3.2 → T3 (+ T7 docs); §3.3 → T1; §3.4 → T4; §4 → T0/T5/T6; §5 honoured by omission; §6 → T5's bounds, T3's pair-count refusal, T3's caveats.
- Placeholders: none; values Task 0 derives are named as its outputs.
- Type consistency: `DriverArgs.refocus_of: Option<String>` (T2) is what `Invocation.refocus_of` carries and what `meta.refocus_of` reads; `refocus_rust.run/refusal/rerun_argv/find_pair/driver` (T3) are what T5's phases and T4's cases exercise through the CLI; meta keys `workspace_root`/`invocation_processes`/`refocus_of` spelled identically in T2, T3 and T5.
