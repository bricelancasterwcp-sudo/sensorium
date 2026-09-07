# Rung 4 slice 3 — the rung-4 debts — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the seven rung-4 debts — the harness-thread licence rule, the child-run pair filter, the hard-linked shim, `schema_version`, the `info` line, the `driver.rs` split, `fn_items` via the census path — and measure the licence change once (E4′).

**Architecture:** Python-only licence and pair changes; a driver-side link-or-copy; a transform-side census flag; `schema_version` in both instruments plus a pass-2-only sibling runner that re-refocuses E4's 61 kept originals from a fresh copy of the store.

**Tech Stack:** Python 3.12+ (`sensorium` query CLI, pytest), Rust (`cargo-sensorium`, `sensorium-transform`), SQLite (`VACUUM INTO`), the E4 runner family.

**Spec:** `docs/superpowers/specs/2026-09-07-sensorium-rung4-debts-design.md` (rulings R1–R7; §8 is E4′ in prose, which Task 0 locks).

## Global Constraints

- **Branch** `feat/rung4-debts` off main `24de001`, main checkout; never push `main`; the merge is Brice's; PR #17's worktree/files untouched (`docs/TRACE-FORMAT.md` touched only if a licence sentence exists there — one place at most).
- **Versions**: Python 0.8.4 → **0.8.5** (Task 7); `cargo-sensorium` 0.5.0 → **0.5.1** (Task 3); `sensorium-transform` 0.4.1 → **0.4.2** (Task 4); rt 0.4.0 unchanged; `TRACE_FORMAT` 4.
- **Pre-registration**: E4′ §1 committed ALONE (Task 0), byte-locked (`awk '/^## 1/,/^## 2/' | sha256sum`), dated amendments only; one measurement; `.FAILED` before a number = infrastructure, after = STOP. **No `src/` or crate source change after Task 6's measurement.**
- **Box rules**: cargo targets under `/mnt/extra/sensorium-rung2/` (workspace `rust-target`; E4′ a FRESH `bloomery-target-e4p` and FRESH `sensorium-dir/e4p`); one cargo at a time; root disk ≈6.7 GB — nothing large on it; the kept E4 store `/mnt/extra/sensorium-rung2/sensorium-dir/e4` is READ-ONLY (copies by `VACUUM INTO` only); the clone `e209ed9` read-only; never `pkill -f`; long runs detached with markers.
- **Repo hygiene**: no box path in committed files except the record's lens rows and this plan; every file ≤ 800 (split before growing); commits by explicit path, never `.superpowers/`; every commit ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`; `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` never modified.
- **Tests**: every new behaviour pinned by a mutation-tested test (committed tree; purge `__pycache__`; `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider`); none-vs-zero.

---

### Task 0: E4′ pre-registration — §1 alone and locked
**Files:** create `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md` (header + `## 1`; `## 2`–`## 5` `(written by Task 6)`). Inputs: E4's record §1.1/§1.2 (the 61 names, files, the four thread-spawning tests) and E4's archived raw record `/mnt/extra/sensorium-rung2/sdd-archive/2026-09-07-sensorium-rung4-refocus/results-e4-raw.json` (`raw_pass1.runs[*]` → `run`, `name`, `target`).
- [ ] §1.1: the 61 `(name, file, original run id)` rows in E4's order; §1.2: the expected licence partition (57 granted; the four withheld by name with their program-thread counts 1/4/4/4) and the harness count 1 on every pair; the argv `sensorium refocus <orig> --focus <name>`; the fresh-store method (`VACUUM INTO` per original into `<SENSORIUM_DIR>/traces/<run>.db`; the copy's `meta.run_id` verified); the H-table (design §8) with both readings; the lens (fresh locations; the driver from HEAD; `TMPDIR` observed; the clone read-only — it is rebuilt by each refocus; the shim census method incl. `st_ino`; the version token from `meta.recorder`); kill rules. No box path outside the lens rows.
- [ ] Commit ALONE: `docs(rung4): E4′ pre-registered — §1 alone, before the instrument`; ledger sha + `sha256sum`.

### Task 1: R1 + the `info` line (Python)
**Files:** modify `src/sensorium/query/refocus_world.py` (`harness_threads(trace)`, the count subtraction, the caveat/withheld wording), `src/sensorium/query/vocab.py` (RUST harness phrase), `src/sensorium/query/info_cmd.py` (the `licence unverifiable:` line), `src/sensorium/query/refocus_rust.py` only if the caveat assembly lives there; tests `tests/test_refocus_licence_rust.py` (+ a sibling if > 800), `tests/rust_traces.py` (fixtures: a `#[test]`-marked site in `meta.sites`, a thread whose root frame is it, a program thread).
**Produces:** `harness_threads(trace: Trace) -> set[int]`; the printed lines of design §2; `info`'s line of design §6.
- [ ] Failing tests: harness-only pair → granted, caveat names 1 harness thread; harness + 1 program thread → WITHHELD naming 1 program thread and the harness exclusion; harness + 4 → 4; Python fixture → byte-identical caveats (the legacy `test_refocus_licence.py` untouched and green); `info` prints the unverifiable line iff the stamp holds names. Mutations: root-frame lookup off by `parent_id` (counts a non-root frame) → red; subtraction dropped → red; `info` line always printed → red.
- [ ] Commit `feat(query): the licence treats libtest's per-test thread as the recorder's own; info names the unverifiable checks`.

### Task 2: R2 + the corpus case
**Files:** `src/sensorium/query/refocus_rust.py` (`find_pair` returns parents + children; the pair line; `refocus_children` stamp), `tests/test_refocus_rust.py`; `corpus/rust/refocus_child_run/` (+ `corpus/rust/README.md`).
- [ ] Failing tests: 2 linked candidates where B's `ppid == A.pid` → pair A, children [B]; 3 candidates (A, child of A, unrelated C) → REFUSED count 2 naming C's cause; the stamp; the printed line. Mutation: ppid filter dropped → red. Corpus: derive pins from design §7 (the `abort` case shows the child-run shape); gate 62 cases 0 failures. Commit `feat(query): a child run is not the pair — refocus answers about the parent and names the child`.

### Task 3: R3 + the `driver.rs` split (driver 0.5.1)
**Files:** `rust/cargo-sensorium/src/rt_build.rs` (`install_shim` link-or-copy + tests), new `invocation.rs` (pure move of `Invocation` + serde + `write_invocation`) and `launch.rs` (the cargo child env/launch), `driver.rs` (orchestrates; < 500), `Cargo.toml` 0.5.1 + pins.
- [ ] Split first as two pure-move commits (behaviour byte-identical; `driver_smoke.rs` green); then the link: tests — byte identity; same-fs inode equality (`std::os::unix::fs::MetadataExt::ino`); the fallback via `/dev/shm` when mounted (skipped by name otherwise). Mutation: link removed → the inode test red. Commit `feat(driver): the shim is a hard link when it can be, a copy when it cannot (0.5.1)`.

### Task 4: `fn_items` via the census path (transform 0.4.2)
**Files:** `rust/sensorium-transform/src/visit.rs`/`splice.rs` (`Ctx.record_sites`), `focus.rs` (`fn_items` reads the `Ctx`), `Cargo.toml` 0.4.2; tests: `fn_items` equals the previous route on every golden input (compute both in the test), `census()` shape unchanged, resolution on the driver's fixture workspace unchanged.
- [ ] Commit `perf(transform): fn_items enumerates through the census path — no splice for resolution (0.4.2)`.

### Task 5: `schema_version` + the E4′ runner
**Files:** `rust/tests/acceptance_e9*.py`, `acceptance_e4*.py`, `render_e9.py`, `render_e4.py` (the field + the re-derivation sentence; committed results.json NOT re-derived); new `rust/tests/acceptance_e4p.py` (+ `_phases/_schema/_cells/render` as needed; ≤ 800 each) — BYTE_LOCK Task 0's sha; env `SENSORIUM_DRIVER`, `SENSORIUM_E4_STORE` (the kept store, read-only), `SENSORIUM_BLOOMERY`, `SENSORIUM_E4P_TARGET` (fresh), `SENSORIUM_DIR` (fresh), `SENSORIUM_RUST_TARGET`; preflight copies the 61 originals by `VACUUM INTO` and verifies `meta.run_id`; the loop; H1–H6; the shim inode census; killed-cell rule structural; markers `e4p.DONE/FAILED`; tests `tests/test_acceptance_e4p*.py` (lock; the 61-row table derived from the locked doc; the partition check; parsers on real output; the box-path scan).
- [ ] Commit `test(rung4): schema_version in every results file; the E4′ runner — pass 2 re-run over the 61 kept originals under the harness rule`.

### Task 6: Measure E4′ once; §2–§5
As slice 2's Task 6: preflight (kept store untouched — record its mtimes before/after), launcher under `<ledger>/acceptance-e4p/launch.sh`, detached, poll ≤ 1 h 15 min, read nothing before the marker, kill rules, determinism, §2–§5, commit record + results.json.

### Task 7: Docs, versions, close-out
HONESTY (§13's licence sentence; blind spot 12's WITHHELD bullet struck + corrected; the harness definition; child runs), TRACE-FORMAT (only if it states the licence rule — check; at most one place), `docs/query.md`, READMEs, CHANGELOG 0.8.5 + crates block (driver 0.5.1, transform 0.4.2), `pyproject.toml` 0.8.5, CARRIED-DEBT (strike R1–R4/R7 items with commits; the E9/E4 results.json predate `schema_version`; process lessons), inbox; full gate; PR body draft.

### After Task 7 — final review, fix wave, PR
Whole-branch review (fable) on `24de001..HEAD`; no src after Task 6's measurement; ONE fix wave; re-review; push; PR; CI; merge is Brice's.

## Self-review
- Coverage: §2 → T1; §3 → T2; §4 → T3; §5 → T5; §6 → T1 (info), T3 (split), T4 (fn_items); §7 → T2; §8 → T0/T5/T6; §9 by omission.
- Placeholders: none. Types: `harness_threads(trace) -> set[int]` used by T1 only; `find_pair` returns parents + children (T2) read by T5's parser through the printed pair line; env names identical in T5 and Task 6's launcher.
