# Query-CLI Exit-Status Convention (+ two closing rulings) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the query CLI's exit status carry the caller's next action — 0 answered yes, 1 answered no, 2 fix the call, 3 change the recording — with an invocation log that turns every future "agents would want this" claim into a measurable one; and close two small debts (the E5′-names ruling; the CI Rust toolchain drift).

**Architecture:** One tiny module `src/sensorium/exit.py` names the four codes; each query command's return sites are mapped to them by an explicit table (below) and pinned by tests; `cli.main` appends one JSON line per invocation to `<trace root>/invocations.jsonl` after dispatch, argv-only, opt-out by env. The `run` subcommand keeps propagating the target's own status. `diff`/`refocus` REFUSED moves from 2 to 3 — the one documented contract this touches — so the version becomes 0.7.0 and a CHANGELOG starts.

**Tech Stack:** Python 3.12+ (stdlib only in `src/`), pytest, the corpus + conformance-vector harnesses; one TOML file and one CI step for the toolchain pin.

**Spec:** `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` (Brice's finding: §3 the convention, §4 the log, §5 the collisions, §7 the slice order). The design authority for every ruling below is Claude's, delegated by Brice on 2026-09-04. Rigor: `~/.claude/skills/rigorous-experiments/SKILL.md` (mutation-tested pins; none-versus-zero; a withdrawn claim stays visible).

## Global Constraints

- **Branch:** `feat/exit-status-convention` from `main` @ `4707093`. Never push `main`. PR against `main`; merge is Brice's unless he delegates again.
- **Stdlib only** under `src/sensorium/` (the recorder and CLI are dependency-free); Python 3.12+; CI matrix 3.12/3.13/3.14 must stay green.
- **The `run` subcommand's exit status is the TARGET's** (`tests/test_boot_cli.py` pins 3 and 1 propagated) — never touched by this plan.
- **Every changed exit site gets a test that pins the new code and a mutation that flips it** (state the mutation and the failing output in the report). Python mutants: purge `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`. Mutant runs under `setsid` + timeout + kill by pgid + `ps -p`; never `pkill -f`.
- **Vectors and corpus change only where the convention applies**, each change justified by the row of the table below that mandates it — never "to make it pass". The Rust acceptance harness never reads a CLI exit code (verified), so nothing under `rust/tests/acceptance*` changes.
- **No box-local path in any committed file.** The untracked `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` is Brice's draft: this plan COMMITS it verbatim in Task 0 (it is the spec this plan argues from; Brice delegated the decision) — the only allowed touch is `git add` of the file as it is; never edit it.
- **Rust:** `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target` for any cargo command (Task 0's toolchain check only); one cargo at a time.
- Commit messages: conventional type; every commit ends with the two trailer lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`
- Every shell command starts `cd /home/brice/workspace/sensorium &&`. Never `git add -A`; explicit paths.

---

## Decisions (X1–X12)

| # | Decision | Why | Cost if wrong |
|---|---|---|---|
| X1 | The four codes, exactly the finding's §3: **0** answered affirmatively; **1** answered negatively (the trace says *no* or *none*); **2** the call is wrong (edit the command); **3** the trace cannot settle it (change the recording). Named in `src/sensorium/exit.py` as `ANSWERED = 0`, `NEGATIVE = 1`, `BAD_CALL = 2`, `UNSETTLED = 3`, each with a one-line docstring; no query command returns a bare integer literal after this plan. | The finding's argument: an agent branches on `$?` before it reads prose; today 0 means both "yes" and "nothing was checked". | none |
| X2 | The **site table** (below) is the contract. Every existing return site is mapped; the mapping is also the test matrix. | One table, one place. | A wrong row is a one-line change with a failing test. |
| X3 | **Empty answers are negative**: `grep` `matches: 0`, `tree` `no frames recorded`, `flow` with zero sightings, `exceptions` `no exceptions recorded`, `runs` with no traces → 1. `info` always 0 (it describes one trace; there is no "no" answer). | POSIX `grep` and the finding's §2 prior. | A caller that treated "none" as success now sees 1 — the intended change. |
| X4 | **`refocus`'s two gates keep two codes**: pre-rerun refusals (`_refusal`/`_refuse`, `TargetError` before the rerun, the Rust `capabilities.refocus: false` refusal) stay **2** — "no rerun was attempted" is the finding's own code-2 example; post-rerun `REFUSED`/UNVERIFIED is **3**. | The gate split already exists in the code and its docstring. | none |
| X5 | **`diff` REFUSED → 3** (all of `_unsafe_reasons`, empty streams, basis mismatch, missing task fingerprints, dup/`Task-N` ambiguity, Rust `seq_gaps`/`records_dropped`). `TraceLookupError`/`RefError`/`TraceFormatError` stay **2** in `cli.main`. | A refusal names a recording that would settle it. | The documented 0/1/2 table changes → version 0.7.0, CHANGELOG. |
| X6 | **`frame`/`flow` split their mixed code-1 sites**: "no such frame", "no activations of X", "recorded but not framed", "no event eN", "no CALL of X", "X is not captured at eN" → 1; `--nth` out of range, no ref given at all, malformed `--object` spec, "primitive has no identity — use `--value`" → 2. | The convention's whole point. | none |
| X7 | **`watch`**: SATISFIED 0; "not satisfied" 1; `NOTHING WAS CHECKED` 3; `REFUSED: watch needs line` 3; `--at` names nothing 1; bad flags/`--expr` 2. **`flow`**: needs `line`/`object_identity` 3. **`exceptions`**: the Rust rung-3 refusal 3; `no RAISE events recorded (see INCOMPLETE above)` 3; `no exceptions recorded` 1; any disposition listed 0. | Each message already says which action it wants. | none |
| X8 | **Invocation log**: after dispatch, `cli.main` appends one line `{"utc": <ISO-8601 Z>, "argv": [...], "exit": <int>, "error": <exception class name or null>}` to `paths.trace_root() / "invocations.jsonl"` (a sibling of `traces/`, so `runs`'s `*.db` glob never sees it). **Default on**; opt-out `SENSORIUM_NO_INVOCATION_LOG=1`; argv only, never the environment or cwd; an unwritable log prints one stderr line `sensorium: invocation log unwritable: <err>` and never changes the exit status. The `run` subcommand logs too (it is a `main()` return). | The finding §4: the census must exist before any flag is added on demand claims. | A file that grows one line per call; a reader can delete it. |
| X9 | **Collision renames (finding §5)**: `watch --near N` → `--misses N`, with `--near` kept as a hidden deprecated alias for one release that prints `sensorium: --near is deprecated; use --misses (removed in 0.8.0)` on stderr; `--fn` becomes **exact-first, then substring** in BOTH `grep` and `frame` (exact qualname match wins; otherwise substring; in `frame`, a substring that matches more than one distinct qualname prints the candidates and exits 2 — ambiguous reference = the call is wrong). `refocus --window` is NOT renamed (its meaning is tied to the recorder's focus semantics) — an inbox item, to be revisited with the census. | The finding's own list; bounded. | One alias to remove in 0.8.0. |
| X10 | **Docs**: README gains an "Exit statuses" section (the four meanings, one table, one sentence each) and the `refocus` table splits into "cannot refocus (exit 2, no rerun attempted)" prose + a REFUSED row at 3; "What refuses" says 3 for `exceptions`/`watch`/`flow` and 2 for `refocus`; every subcommand's `--help` gains an `epilog` with the one-sentence convention (`exit: 0 yes, 1 no, 2 fix the call, 3 change the recording`); `docs/TRACE-FORMAT.md`'s three exit mentions updated; `CHANGELOG.md` created with a 0.7.0 entry; `pyproject.toml` 0.7.0. The skill `~/.claude/skills/debugging-with-sensorium/SKILL.md` is outside the repo — the controller updates it after merge. | The channel is only load-bearing if the two consumers (README, skill) teach it. | none |
| X11 | **E5′-names (b) ruling** (from the rung-3 entry slice's record §5.1): repair 2 — the hash conjunct is WITHDRAWN as mis-specified; stored task fingerprints are move-sensitive by design (TRACE-FORMAT §7; spec §5.4 keys identity by file) and the pairing question is answered by E5′'s own `every task paired` condition, which read all matched. The STOP row stays exactly as measured; a dated "Ruling 2026-09-04 (Claude, delegated authority)" paragraph is added beside it; HONESTY/README/inbox sentences saying "ruling owed" become "ruled". No re-measure (an E5″ would restate E5′'s tasks_all_matched). | A withdrawn claim stays visible; nothing is re-read into a pass. | none |
| X12 | **CI Rust toolchain pinned** to the box's `1.96.0` via `rust/rust-toolchain.toml` (`channel = "1.96.0"`, `components = ["rustfmt", "clippy"]`, `profile = "minimal"`); CI's step becomes `rustup show` run inside `rust/` (installs the pinned toolchain + components on demand) and the cache key gains the toolchain channel string; bumps are deliberate commits. | Reproducible CI; new lints arrive when we choose. | New clippy lints are not seen until a bump. |

## The site table (X2) — every query-CLI exit site, its new code, and its pin

| Command | Situation (message as printed) | Code | Pin (test → mutation) |
|---|---|---|---|
| any | `TraceLookupError` / `RefError` / `TraceFormatError` caught in `cli.main` (`error: …` on stderr) | 2 | `tests/test_fmt.py` (exists); vector `v01-missing-required-key` 2 (exists) |
| any | argparse failure; Python < 3.12 | 2 | exists |
| `runs` | at least one trace listed | 0 | new test → flip to 1 |
| `runs` | `no traces recorded` | 1 | new test → flip to 0 |
| `info` | always | 0 | exists |
| `grep` | `matches: N`, N ≥ 1 | 0 | exists |
| `grep` | `matches: 0` (+ `_empty_note`) | 1 | `tests/test_grep.py:92` moves 0→1 → flip back |
| `grep` | `--kind LINE` on a trace that recorded no LINE events at all (the note says re-record with `--focus`) (**row added 2026-09-04 after the Task-2 review**) | 3 | new → flip |
| `grep` | `--limit < 1` | 2 | exists |
| `tree` | frames printed | 0 | exists |
| `tree` | `no frames recorded` | 1 | new test → flip |
| `tree` | `no such frame: …` / `no frame contains eN` / unframed CALL note | 1 | exists (`test_format2_fixture.py`) |
| `tree` | `--limit < 1` / `--depth < 0` | 2 | exists |
| `frame` | frame printed | 0 | exists |
| `frame` | `no such frame: f<id> does not exist` / `no recorded activations of X` / `recorded as N call(s) but not framed` | 1 | exists + new for each |
| `frame` | `--nth N is out of range` / no ref given (`give f<id> or --fn …`) / `--fn` substring ambiguous (X9) | 2 | new tests → flip to 1 |
| `exceptions` | at least one disposition listed | 0 | exists |
| `exceptions` | `no exceptions recorded` | 1 | new → flip |
| `exceptions` | `no RAISE events recorded (see INCOMPLETE above)` | 3 | new → flip |
| `exceptions` | an uncaught exception is known (unwind/exit meta) but no RAISE row carries its identity (**row added 2026-09-04 after Task 2 found the third arm**) | 3 | new → flip |
| `exceptions` | `REFUSED: exceptions on a rust trace … nothing was judged` | 3 | vector `v14` `exceptions-refuses-a-rust-trace` 2→3; new unit test |
| `exceptions` | `--limit < 1` | 2 | exists |
| `flow` | sightings printed | 0 | exists |
| `flow` | zero sightings (prints `sightings: 0` — add the line if absent) | 1 | new → flip |
| `flow` | `REFUSED: flow needs line` / `flow --object needs object_identity` | 3 | `tests/test_flow.py:374,377` 2→3; vector `v07` + `v14` 2→3 |
| `flow` | `no event eN` / `no CALL of X` / `X is not captured at eN` | 1 | new per message |
| `flow` | malformed `--object` spec / primitive has no identity (`use --value`) / `--limit < 1` | 2 | new per message |
| `watch` | SATISFIED | 0 | exists |
| `watch` | `not satisfied` (hits ≥ 1, some failed) | 1 | `tests/test_watch_verdict.py` rows for not-satisfied move 0→1 |
| `watch` | `verdict: NOTHING WAS CHECKED` | 3 | `test_watch_verdict.py:279` and `test_format2_fixture.py:161` move 0→3 |
| `watch` | `REFUSED: watch needs line` | 3 | `tests/test_watch.py:647-649` 2→3; vector `v14` `flow-and-watch-refuse-on-line` 2→3 |
| `watch` | `error: no recorded code matches --at` | 1 | exists |
| `watch` | `--limit`/`--misses` < 1, bad `--expr`, malformed `--after` | 2 | exists (`--near` → `--misses`) |
| `diff` | MATCH / MATCH modulo location / tasks-carry MATCH | 0 | exists |
| `diff` | DIVERGED | 1 | exists |
| `diff` | `verdict: REFUSED` (every reason) | 3 | `tests/test_diff.py` REFUSED rows 2→3 (`:321,417,432,449,612,626,660,691,711,811,818,851`); `:167` stays 2 |
| `refocus` | MATCH | 0 | exists |
| `refocus` | DIVERGED | 1 | exists |
| `refocus` | pre-rerun refusal (`no rerun was attempted`, `cannot resolve target`, missing `--focus`, unknown run) | 2 | exists (`tests/test_refocus.py:571-681`); vector `v14` `refocus-refuses-through-its-capability` stays 2 |
| `refocus` | post-rerun `refocus verdict: REFUSED … UNVERIFIED` | 3 | `tests/test_refocus.py:518-568` 2→3 |
| `run` | target's own status | as-is | untouched |

Corpus: every question that today relies on the default `expect_exit: 0` and whose command now answers "none"/"no"/"unsettled" gets an explicit `expect_exit` with the table row as its justification in the commit message; the honesty cases (`near_miss`, `suspended_handler`, `silent_swallow`, `async_handler`) are re-read individually and their outcome stated in the Task-4 report.

---

## File Structure

- Create: `src/sensorium/exit.py` (four constants + docstrings), `src/sensorium/invocations.py` (`record(argv, exit, error)`), `CHANGELOG.md`, `rust/rust-toolchain.toml`, `docs/EXIT-STATUS.md`? — NO: the README section is the one place (X10); no extra doc.
- Modify: `src/sensorium/cli.py` (log after dispatch; `error` = exception class caught), `src/sensorium/query/{grep_cmd,tree_cmd,frame_cmd,exceptions_cmd,flow_cmd,watch_cmd,diff_cmd,refocus_cmd,runs_cmd}.py` (return sites → `exit.*`; `flow` `sightings: 0` line; `watch --misses`; `--fn` exact-first), `src/sensorium/query/caps.py` (no change to text), `README.md`, `docs/TRACE-FORMAT.md`, `pyproject.toml` (0.7.0), `.github/workflows/ci.yml` (toolchain step + cache key), `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md` §5.1 (ruling paragraph), `rust/HONESTY.md`, `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md`, README "ruling owed" sentence.
- Tests: `tests/test_exit_codes.py` (new, the table as a parametrised matrix over synthetic traces via `tests.helpers.finalize_synthetic` — one row per table line that has no existing pin), `tests/test_invocations.py` (new), updates to `tests/test_grep.py`, `test_watch.py`, `test_watch_verdict.py`, `test_format2_fixture.py`, `test_flow.py`, `test_diff.py`, `test_refocus.py`, `test_frame.py`/`test_tree.py`/`test_exceptions.py`/`test_runs.py` as needed; vectors `v07`, `v14`; corpus `questions.yaml` files per the corpus rule.

---

### Task 0: Branch, spec committed, two rulings closed, toolchain pinned

**Files:** the plan; `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` (add as-is); `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md` §5.1; `rust/HONESTY.md`; `README.md` (the "ruling owed" sentence); `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §1; `rust/rust-toolchain.toml`; `.github/workflows/ci.yml`.

- [ ] `git checkout -b feat/exit-status-convention main`; `git add` the finding doc AS IS and the plan; commit `docs: adopt the query-CLI exit-status finding as the spec for its slice; plan`.
- [ ] X11: append to the E5′ record §5.1, after "Ruling owed to Brice…": a paragraph headed **Ruling 2026-09-04 (Claude, under design authority delegated by Brice the same day)** stating repair 2, the reasoning (stored fingerprints move-sensitive by design — TRACE-FORMAT §7, spec §5.4; the pairing answered by E5′'s `every task paired`), that the STOP row above stays as measured and the conjunct is withdrawn, and that no E5″ is run because it would restate a measured condition. Update the "ruling owed" sentences in HONESTY §3, README's gap callout, and inbox §1 to "ruled 2026-09-04: (b) withdrawn; see the record §5.1". §1–§4 of the record untouched (byte-lock diff on §1 in the report). Commit `docs: E5′-names conjunct (b) withdrawn as mis-specified — ruling recorded`.
- [ ] X12: write `rust/rust-toolchain.toml`:
  ```toml
  [toolchain]
  channel = "1.96.0"
  components = ["rustfmt", "clippy"]
  profile = "minimal"
  ```
  CI `rust` job: replace the `rustup component add rustfmt clippy` step with `run: rustup show` under `working-directory: rust` (this installs the pinned toolchain and its components); add `-1.96.0` to the cache key. Verify locally: `cd rust && rustup show active-toolchain` prints `1.96.0-…`; `cargo clippy --workspace --all-targets -- -D warnings` (target dir on /mnt/extra) clean. Commit `ci: pin the Rust toolchain to 1.96.0 (rust-toolchain.toml); CI installs it via rustup show`.

### Task 1: Invocation log

**Files:** Create `src/sensorium/invocations.py`; Modify `src/sensorium/cli.py`; Test `tests/test_invocations.py`.

**Interfaces:** `invocations.record(argv: list[str], exit_status: int, error: str | None) -> None` (never raises; writes one JSON line; honours `SENSORIUM_NO_INVOCATION_LOG`); `invocations.path() -> Path` = `paths.trace_root() / "invocations.jsonl"`.

Invariants → falsifiers:
1. Every `main()` return appends exactly one line whose `exit` equals the value returned (both the query path and the `run` path, and the three caught exception classes with `error` = class name). *Falsifier:* `tests/test_invocations.py` runs `cli.main` for a 0, a 1, a 2 and an exception case and reads the exit back from the file; **mutation:** log before dispatch (exit unknown → written as 0) → red.
2. argv only: the line has exactly the four keys; no `env`, no `cwd`. *Falsifier:* key-set assertion; mutation: add `cwd` → red.
3. `SENSORIUM_NO_INVOCATION_LOG=1` → no file written, no output. *Falsifier:* test; mutation: ignore the env → red.
4. Unwritable location (a file where the directory should be) → one stderr line, exit unchanged. *Falsifier:* test with `SENSORIUM_DIR` pointing at a regular file's child; mutation: let the exception escape → red.
5. `runs` never lists the log (it globs `traces/*.db`). *Falsifier:* test that `runs` output is unchanged after a log line exists.
Also: argparse's own `sys.exit(2)` escapes `main()` without a record — document that in the module docstring as the one unlogged path (parse failures never reach dispatch); do not wrap argparse.

- [ ] Steps: red tests → implement → green → mutations (4) → commit `feat(cli): invocation log — one JSON line per main() return under <trace root>/invocations.jsonl`.

### Task 2: `exit.py` + the listing commands (`runs`, `grep`, `tree`, `frame`, `exceptions`)

**Files:** Create `src/sensorium/exit.py`; Modify `runs_cmd.py`, `grep_cmd.py`, `tree_cmd.py`, `frame_cmd.py`, `exceptions_cmd.py`; Tests `tests/test_exit_codes.py` (new; the matrix rows for these commands), `tests/test_grep.py:92`, others as the table says.

- [ ] For each table row of these five commands: a red test (the matrix) → the site returns the named constant → green → mutation (flip to the neighbouring code) → recorded. `frame`'s five `_resolve` messages split 1 vs 2 per X6 (the `--fn` exact-first rule lands in Task 5 — here only the codes). `exceptions`: `no RAISE events recorded (see INCOMPLETE above)` → 3.
- [ ] Commit `feat(query): exit codes — runs/grep/tree/frame/exceptions answer 0/1/2/3 by the convention`.

### Task 3: `watch` and `flow`

**Files:** Modify `watch_cmd.py`, `flow_cmd.py`; Tests `tests/test_watch_verdict.py`, `tests/test_watch.py`, `tests/test_flow.py`, `tests/test_format2_fixture.py:161`, matrix rows.

- [ ] `watch`: `verdict()` returns the verdict class alongside the text (SATISFIED/NOT_SATISFIED/NOTHING_CHECKED) and `run` maps 0/1/3; `REFUSED: watch needs line` → 3. `flow`: refusals → 3; `resolve_object` errors split 1 vs 2 per X6; zero sightings prints `sightings: 0` and returns 1 (add the line if the output has no count; keep the existing wording for ≥ 1).
- [ ] Vectors `v07-flow-refuses-undeclared-line` and `v14-rust-refusals` (`flow-and-watch-refuse-on-line`) `expect_exit` 2→3, with the table row cited in the commit message; `refocus-refuses-through-its-capability` stays 2.
- [ ] Commit `feat(query): watch/flow — NOTHING WAS CHECKED and capability refusals exit 3; negative answers exit 1`.

### Task 4: `diff` and `refocus` REFUSED → 3, vectors, corpus, TRACE-FORMAT

**Files:** Modify `diff_cmd.py` (`run`: REFUSED → `exit.UNSETTLED`), `refocus_cmd.py` (`report()` REFUSED → 3; `_refuse` stays 2), `docs/TRACE-FORMAT.md` (`:349` line-capability row → 3; `:608-610` diff REFUSED → 3; `:33-34` stays 2), vector `v14` (`exceptions-refuses-a-rust-trace` 2→3), corpus `questions.yaml` files per the corpus rule; Tests `tests/test_diff.py` REFUSED rows, `tests/test_refocus.py:518-568`, matrix rows.

- [ ] Run the full corpus (`python corpus/run_corpus.py`, Python cases; and with the release driver for the Rust cases — `SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/release/cargo-sensorium CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target`) BEFORE changing any `expect_exit`; list every question whose exit changed; set `expect_exit` per the table row; state each in the report (the four honesty cases individually). Rebuild the release driver first if `rust/` changed (it did not in this plan — reuse the existing binary, record its sha).
- [ ] Commit `feat(query): diff/refocus REFUSED exit 3 (post-rerun only); TRACE-FORMAT, vectors, corpus follow the convention`.

### Task 5: Collision renames (X9)

**Files:** Modify `watch_cmd.py` (`--misses`, `--near` hidden alias with a stderr deprecation line), `grep_cmd.py` + `frame_cmd.py` (`--fn` exact-first-then-substring; `frame` ambiguity → 2 with candidates listed); Tests for each (alias prints the line and behaves identically; exact beats substring; ambiguity lists candidates and exits 2); `README.md` usage lines mentioning `--near`; corpus/vectors using `--near` (grep them) switch to `--misses`.

- [ ] Commit `feat(query): watch --misses (--near deprecated alias); --fn exact-first in grep and frame`.

### Task 6: Docs, version, changelog

**Files:** `README.md` (new "Exit statuses" section near the top of the command reference; the `refocus` table split per X10; "What refuses" prose; every command reference line that states a code), every `add_parser` in `cli.py`/`query/*.py` gains `epilog="exit: 0 yes, 1 no, 2 fix the call, 3 change the recording"` (test: `--help` of every subcommand contains it — one parametrised test), `docs/TRACE-FORMAT.md` (already in T4 — verify), `CHANGELOG.md` (new: `## 0.7.0 — 2026-09-04` with the contract change and the alias), `pyproject.toml` 0.7.0, `rust/HONESTY.md` if it states a query exit code (grep).

- [ ] Commit `docs: exit-status convention in README, --help epilogs, CHANGELOG 0.7.0; version 0.7.0`.

### Task 7: Close-out

- [ ] Full verification: `python -m pytest -q` on 3.12/3.13/3.14 venvs if present (else 3.13 + CI), `python corpus/run_corpus.py` (both halves), `python -m pytest -q tests/test_vectors.py`; `cargo clippy` once under the pinned toolchain (target dir on /mnt/extra) to prove the pin; PR body draft in the workspace (title `feat(cli): exit statuses carry the next action (0 yes / 1 no / 2 fix the call / 3 change the recording); invocation log; 0.7.0`), sections: What changed, The table, Contract change (diff/refocus REFUSED 2→3), Collision renames, Two closing rulings (E5′-names withdrawn; toolchain pinned), Verification, `## Rulings made by the controller` placeholder, ending lines.

---

## Self-review

- **Spec coverage:** finding §3 → X1/X2/T2–T4; §4 → X8/T1 (first, as the finding orders); §5 → X9/T5 (`--window` deferred with reason); §7 items 1–4 → T1, T2–T4, T4 (grep in T2), T5; §7 item 5 (re-read the log) → a post-merge inbox item. X11/X12 → T0.
- **Placeholders:** none — every site is in the table with its pin; the toolchain file is given in full.
- **Type consistency:** `exit.ANSWERED/NEGATIVE/BAD_CALL/UNSETTLED` used by name in T2–T5; `invocations.record(argv, exit_status, error)` called only from `cli.main`.
