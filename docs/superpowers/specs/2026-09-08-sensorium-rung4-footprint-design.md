# Rung 4, slice 4 — the recorder's footprint

**Date:** 2026-09-08 · **Status:** design, approved in one message (Brice,
2026-09-08: "go ahead and start slice 4") · **Design authority:** Claude —
every ruling below is Claude's, recorded here, none deferred · **Base:** main
`f598468` (Python 0.8.5; driver 0.5.1 / transform 0.4.2 / rt 0.4.0) ·
**Branch:** `feat/rung4-footprint`

Slice 3 (PR #21) measured E4′ once and STOPPED on H1: the licence's
environment clause read the driver's own `RUSTDOCFLAGS` fragment as a change
the world made, so the harness rule's question went unanswered. This slice
removes the recorder's footprint from the licence in the three places it
still shows — that fragment, a program thread mistaken for the harness's, and
the session variables of the shell a re-run was launched from — measures the
first two, and pays the small debts slice 3 named with their fixes.

## 0. Rulings (Claude, 2026-09-08)

| # | Debt | Ruling | Why · cost if wrong |
|---|---|---|---|
| R1 | `RUSTDOCFLAGS` carries the driver's `--extern sensorium_rt=… -L dependency=…` and its rt hash moves with every driver build (`rust/HONESTY-BLIND-SPOTS.md` 27) | every occurrence of the recorder's fragment is **stripped from both sides before the compare**; the remainder is the world's and is compared exactly as before (equality, then the relocation rule); the env line and the stamped fact name the key the strip touched | the fragment's shape is exact — `sensorium_rt`, `/sensorium/rt/<16 hex>/<unwind\|abort>/`, and both tokens naming ONE directory — so nothing the world put in that variable can hide inside it; cost if wrong: a world change spelled exactly like our fragment, which no world has a reason to write |
| R2 | E4′ answered nothing about the harness rule | **E4″**: pass 2 over the 61 kept originals (driver 0.5.0) under this slice's driver — a different build by construction, the one condition the confound is visible under — plus two 4-pair control arms for R4; expected granted 57 / WITHHELD §1.2's four; new record, own lock, fresh store and target | a dry run under one build cannot see the confound (the rt-hash lesson); cost of not measuring: the strip ships on a fixture only |
| R3 | a thread the program spawns onto a `#[test]`-marked fn is read as the harness's and the licence GRANTED over it (blind spot 28) | a thread whose task name is `spawn@…` (or `… :: spawn@…`) is **never** harness whatever its root's mark; only the **FIRST** root frame's mark counts; an `async` test fn carries no mark and stays counted — declared, and pinned; measured by a corpus case that spawns a thread onto a marked fn before it ships | the false grant claims MORE; cost if wrong: a licence granted over a program thread |
| R4 | a re-run launched from another SHELL meets an unearnable licence — session-identity variables differ (E4′ A1, carried) | **bearing set 1**, a positive, versioned list: exact `PATH HOME USER LOGNAME LANG TZ TMPDIR DEBUGINFOD_URLS`, prefixes `LC_ CARGO RUST LD_ DYLD_ SSL_CERT_ PYTHON`; a differing bearing key withholds as today; every other differing key is **counted and named, never withholding**; the line names the set; one rule for both languages; `docs/query.md` carries the house meaning | a positive list can be read and argued with; a negative one cannot; cost if wrong: a program that read a variable outside the set got different input under a granted licence — the set is versioned so that finding has a place to land |
| R5 | four files within 30 lines of the ceiling, two docs at it | **split first, before any other edit**: `docs/CARRIED-DEBT.md` → volume 2 of the archive; `rust/HONESTY.md` §13 → `rust/HONESTY-REFOCUS.md`; `refocus_cmd.py` → `refocus_report.py`; `visit.rs` / `splice.rs` / `lines.rs` each to a named sibling | the ceiling is a rule this repo has kept by naming the split before it is discovered |
| R6 | small carried items with their fixes already written | driver tests set `SENSORIUM_DIR`; corpus `--require-driver`; `tests/test_release_tokens.py`; the `harness_threads` docstring | each is a debt bullet whose fix is one screen; leaving them costs another slice's bullet |
| R7 | slice 2's R6 four (`--window`, multi-process refocus, inference-variable opt-out, per-site volume cap) | **not funded** until a use asks; blind spots stand | — |
| R8 | 32 GB free on `/mnt/extra`; E4′'s target is 21 GB and E4's 24 GB | `bloomery-target-e4` (E4's build cache; its record is closed and its subject set is the trace store, not the target) is removed before the launch; `bloomery-target-e4p` stays until this slice closes; E4″ builds fresh into `bloomery-target-e4pp` and records into `sensorium-dir/e4pp` | build caches are reproducible; the records and stores are the evidence |

## 1. What ships

1. Python (`refocus_env.py`, `refocus_world.py`, `refocus_rust.py`, the new `refocus_report.py`): R1, R3, R4, the docstring. Python **0.8.6**.
2. Driver: no behaviour change; three `driver_smoke.rs` tests set `SENSORIUM_DIR`. `cargo-sensorium` **0.5.2** — the number exists so E4″'s record can name its driver by token, not only by sha (`driver_version` is what a trace carries).
3. Transform: three pure splits, behaviour byte-identical (goldens pin it). `sensorium-transform` **0.4.3**.
4. Corpus: `refocus_spawned_test_fn`; `run_corpus.py --require-driver`; CI's rust step uses it.
5. Instruments: three E4′ gap fixes in the shared `acceptance_e4p_*` modules; a sibling entry `acceptance_e4pp.py` with its arms module; the E4″ record measured once.
6. Docs: `HONESTY-REFOCUS.md` amended (three dated paragraphs), blind spots 27/28 closed with dated clauses, INDEX rows, `query.md` + README, CHANGELOG, CARRIED-DEBT's new section. `TRACE_FORMAT` stays 4; PR #17's files untouched.

## 2. R1 — the fragment

`refocus_env.py` gains `strip_recorder_fragment(value: str) -> tuple[str, int]`: removes every match of

```
(?:^| )--extern sensorium_rt=(?P<dir>\S+/sensorium/rt/[0-9a-f]{16}/(?:unwind|abort))/libsensorium_rt\.rlib -L dependency=(?P=dir)(?= |$)
```

and returns the remainder (surrounding single spaces collapsed, ends trimmed) with the count removed. The backreference is the rule: two tokens that do not name one directory are not our fragment and are left for the world's compare. `_env_diff` applies it to both sides of every key before the equality test and returns a third list, `stripped` — the keys on which a fragment was removed from at least one side. Anything that remains is compared exactly as today: equal → not a difference; else the relocation rule; else changed. Python traces never match; their lines stay byte for byte.

**Printed** (line and fact, the two channels agree): after the relocation clause, `; the recorder's own fragment stripped before comparing: RUSTDOCFLAGS` — present only when `stripped` is non-empty. `relocated_clause` grows a sibling `stripped_clause`; `is_relocation_note` learns the new prefix so `assess` keeps the note on a withheld pair too.

**Tests**: the E4′ pair's two real values (§4 of that record) as a fixture — same root moved, hash moved — reads unchanged; a world flag added after our fragment still withholds; a fragment whose two tokens name different directories is not stripped; a Python pair's lines are byte-identical to today's; mutation on each.

## 3. R4 — bearing set 1

`refocus_env.py`: `BEARING_SET = 1`, `BEARING_EXACT`, `BEARING_PREFIXES` as R4 lists, `is_bearing(key) -> bool`. `_env_diff` partitions `changed` into `bearing` and `other` (a key present on one side only is a difference, as today, then partitioned like any other). Only `bearing` withholds.

**Printed, exactly.** When nothing differs: today's lines, byte for byte. When only `other` differ:

```
env: unchanged on bearing set 1 (<N> variables compared; not compared: <ignored>; <K> other variable(s) differ, not bearing: <names, ≤8, +M more>)<relocation><strip>
```

fact: `<N> environment variable(s) compared and unchanged on bearing set 1 in the environment the rerun executed under; not compared: <ignored>; <K> other differ, not bearing: <names>` + clauses; caveat `None`. When a bearing key differs: today's `env: CHANGED since the original run -- <M> variable(s) differ: <names>   (names only)` and today's caveat sentence, unchanged, over the BEARING names only, followed on the line by `; <K> other variable(s) differ, not bearing: <names>` when K > 0. The Rust branch's `; the recorder's own, also not compared: …` sentence stays where it is. `N` counts what was compared (as today); `K` is the other-set's size, never capped; the names are capped at 8 as the changed names are.

**Tests**: a session key (`DBUS_SESSION_BUS_ADDRESS`) differing alone → granted, counted, named, K exact; `TZ` differing → withheld naming `TZ`; both → withheld, the line carries both clauses; each exact name and each prefix in the set withholds (parametrised); `LC_ALL` and `LCX` decide differently; a Python pair with one session key differing reads the new line. Existing tests that pinned withholding on a key outside the set move to a key inside it, each move named in the task report. Every wording change runs the corpus gate WITH the driver.

**Docs**: `docs/query.md` §refocus, a paragraph beside the relocation rule — what the set is, its version, that a key outside it is named and never withholds, and why the list is positive; README's licence paragraph gains one sentence.

## 4. R3 — the harness anchor

`refocus_world.harness_threads`: per non-main thread, the FIRST root (`roots()` is frame-id ordered, so first seen wins; later roots never add); a thread whose task row's name starts with `spawn@` or contains ` :: spawn@` is skipped before its root is read. Docstring rewritten to say what is true: root-anchored, first root, spawn-named never, `async` unmarked and counted. Consumers (`harness_exclusion`, `harness_note`, `diff_notes`, `info_cmd`) keep their signatures.

**Tests** (`tests/test_refocus_licence_rust.py`, fixtures via `rust_traces.libtest_trace`): a program thread named `spawn@<qualname>#1` rooted on `TEST_FN` → counted, licence withheld naming 1 program thread; a thread whose first root is `WORKER_FN` and whose second root is `TEST_FN` → counted; a libtest thread rooted on `TEST_FN` with no spawn name → harness (today's case, kept); a thread rooted on a fn with no site row (the `async` shape) → counted. Mutation on each.

**Corpus** `corpus/rust/refocus_spawned_test_fn`: two `#[test]` fns, the second doing `std::thread::spawn(|| helper_test()).join().unwrap()` (the closure shape, the one the transform rewrites — copy the shape of the existing thread cases); recorded with the spawning test alone (`--exact`); question `refocus $RUN --focus <the spawning test>` → `licence: WITHHELD` and the thread reason `started 1 thread(s) besides the main one and 1 harness thread (…)`. This is R3 measured under the real driver; the corpus gate with the driver is H8's gate.

## 5. R5 — the splits

- `docs/CARRIED-DEBT.md` (798): the archive is itself at 594, so **archives are numbered volumes ≤ 800**. New `docs/CARRIED-DEBT-ARCHIVE-2.md` receives slice 1 (21–328) and slice 2 (329–595), wording, order and strikes unchanged, with a header in the volume-1 shape; the live file's header names both volumes; the live file keeps slice 3 and gains this slice's section (newest LAST).
- `rust/HONESTY.md` (794): §13 (621–788) → `rust/HONESTY-REFOCUS.md`, a pure move; the stub keeps `§13` as the identifier (the §11 precedent, verbatim shape); `HONESTY-INDEX.md`'s header names the fourth file; no citation is edited. This slice's three amendments to §13 land in the new file AFTER the move, each dated.
- `src/sensorium/query/refocus_cmd.py` (789): `report`, `_print_thread_line`, `_diverged_why`, `_stamp` → `refocus_report.py`; the re-export block precedent (`refocus_cmd.py:159–165`) repeated so `refocus_cmd.<name>` resolves; a byte-for-byte move test in the shape of `tests/test_refocus_rust.py:608`.
- `rust/sensorium-transform/src/visit.rs` (773): `impl Visit for Ctx` → `visit/walk.rs` (`mod walk;` in `visit.rs`); five `pub(super)` bumps (`fn_item`, `in_item`, `in_container`, `in_async_scope`, field `skipped`), nothing wider.
- `splice.rs` (762): the engine and its tests → `assemble.rs` (`splice_order`, `run`, `assemble`, `check_spawn_ordinals`, `check_line_count`, `CRATE_ALLOW`, `CRATE_ALLOW_LEADING`, `unit_static`, both placement families, `mod tests`); `stripped_prefix_len` stays (`census.rs` imports it); zero visibility bumps.
- `lines.rs` (762): the analysis half (444–762, free fns over `syn`) → `lines/facts.rs`; seven `pub(super)` bumps named in the map (`is_block_like`, `statement_span`, `stmt_diverges`, `is_conditionally_compiled`, `statement_deltas`, `binding_names`, `let_bindings`).

Each split is one commit, `cargo test --workspace` + goldens green before and after, `cargo fmt`/`clippy -D warnings` clean.

## 6. R6 — the small carried items

- `driver_smoke.rs:65,230,338`: `.env("SENSORIUM_DIR", s.p("sensorium-dir"))` on each `Command`; a test pins that a workspace test run leaves `~/.sensorium` untouched (run under a scratch `HOME`).
- `corpus/run_corpus.py --require-driver`: exit 1 when any case was skipped; the summary line ends `; --require-driver was given and <n> case(s) could not run`; `--json` carries `require_driver` and the same reason; CI's rust corpus step passes the flag; the Python matrix's comment loses its stale number.
- `tests/test_release_tokens.py`: `pyproject.toml` == `importlib.metadata.version('sensorium')`, always; the newest `CHANGELOG.md` header: if `(unreleased)`, its version is the next number above pyproject's; if dated (`YYYY-MM-DD`), it equals pyproject's. Both states green, so the test never lies mid-slice.

## 7. E4″ — pre-registered (prose; Task 1 locks §1)

Record `docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md` (+ `-rows.md`, `.results.json`), §1 alone and byte-locked; runner `rust/tests/acceptance_e4pp.py`, a sibling entry over the E4′ modules with its own paths, `schema_version` `e4pp/1`, and an arms module. Subject: the 61 originals of E4 §1.1 in the kept store (driver 0.5.0), copied by `VACUUM INTO` into `sensorium-dir/e4pp`; driver = this slice's `cargo-sensorium 0.5.2` built from the measurement commit; fresh `CARGO_TARGET_DIR=bloomery-target-e4pp`.

**Instrument fixes first, checked by the dry run**: the partition reads the harness count from the `threads:` line when the licence's thread clause is silent, and every count names the line it came from; `licence_verified_counts` is built from the per-row licence dicts; the version probe records `null` with its reason on failure and probes `importlib.metadata`, the token the package exposes.

**Launch guard, revised for R4**: the preflight requires parity between the runner's process environment and every original's recorded one on the **bearing set only**, after the recorder's exclusions, the relocation rule and the strip; every non-bearing difference is allowed and its key set recorded in §2 BEFORE any refocus runs — H4 and H6 compare against that set by name.

**Arms.** A: the 61, `refocus <orig> --focus <name>` under the guard. B (bearing control): the first three rows of §1.1 expected granted plus `a_pager_can_be_shared_across_threads`, re-run with `TZ` set to a value the runner chooses to differ from the original's recorded one (or its absence). C (non-bearing control): the same four, re-run with `E4PP_MARK=<launch stamp>` added. Each arm has its own launch environment written into the record.

**Dry run** (2 pairs from the kept store into `-dry` siblings, one expected granted and `a_pager_can_be_shared_across_threads`): must show the strip clause firing on an original whose rt hash differs from the re-run's — a dry run under one build is not a dry run of this instrument.

| id | question | endpoint (both readings pre-committed) |
|---|---|---|
| H1 | does the harness rule change the licence word as predicted? | granted 57 and WITHHELD exactly §1.2's four, each reason subtracting to 1/4/4/4 and naming the harness exclusion → PASS; any other partition → STOP |
| H2 | is the fragment gone from the compare? | `RUSTDOCFLAGS` in no changed list on 61/61; the strip clause names it on 61/61; the relocated set on 61/61 is exactly E4′'s measured four (`CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH`) → PASS; else STOP |
| H3 | verdict and pair untouched? | MATCH 61/61; pair 1 of 1 on 61/61 → PASS; else STOP |
| H4 | do other differences stay outside the vote? | on 61/61 the line's other-set equals the preflight's recorded set by name and K by count; no withholding reason cites a non-bearing key → PASS; else STOP |
| H5 | does the set still bite? | arm B WITHHELD 4/4, each env caveat naming `TZ`; the fourth keeps its thread reason → PASS; any granted → STOP |
| H6 | is the other-count exact? | arm C's licence word equals arm A's on 4/4; other-set = preflight set ∪ {`E4PP_MARK`}, K exact → PASS; else STOP |
| H7 | is the instrument honest? | no partition cell `None` on a pair whose licence printed; each count carries its source line; `licence_verified_counts` non-null; the version probe is a token or `null` + reason → PASS; else STOP (instrument) |
| H8 | nothing else moved? | corpus WITH the driver equal, `refocus_spawned_test_fn` included; Python suite green; `cargo test --workspace` green → PASS |
| reported | wall per arm; arm B's verdicts (a `TZ` the program read is a finding, not a gate); the two tool hashes; K and its names; `driver_version` on both sides |

Kill rules as E4′'s: a `.FAILED` before any number is infrastructure (relaunch from zero); after, a STOP; measured once; bound 1.5 h; 1800 s per refocus; no `src/` or crate change after the measurement.

## 8. Not in this slice

R7's four; any change to the comparator or the verdict; `TRACE_FORMAT`; PR #17's files; the "`&e`-through-a-function" and window items of earlier inboxes.

## Amendments

Appended, never edited in place. Each entry names the section it amends and
the date it was made.

**A-§3 — R4 is a session set, not a bearing set (2026-09-08, before any
code and before §1 was locked).** §3 as first written kept a positive list of
"bearing" variables and let every other differing key through, named. That
design has a falsifier already in the suite:
`tests/test_refocus_licence.py::test_refocus_withholds_the_licence_when_the_environment_differs`
records under `REFOCUS_TEST_LIMIT=10` and refocuses without it — a variable the
program READS, so the rerun printed a different value under an identical call
shape — and pins `licence: WITHHELD`. `REFOCUS_TEST_LIMIT` is on no bearing
list anyone would write, so §3 would have GRANTED over a program that
demonstrably got different input: the direction that claims more, exactly
what the licence exists to refuse. The tool cannot know which variables a
program reads; a positive list of the ones that "bear" is a guess dressed as a
rule. **Ruled instead:** today's rule stands — any differing key withholds —
with ONE new positive, versioned exception, **session set 1**: variables that
identify the shell, terminal, agent or login session a process was launched
from and that a program has no reason to read. A session key that differs is
**named and never withholds**; everything else is what it always was.
Measured before this ruling, against one of the 61 kept originals from this
session's own shell (names only): after the recorder's exclusions, 73 keys
equal, 0 added, 3 missing (`PYTHONDONTWRITEBYTECODE`, `SSL_CERT_DIR`,
`SSL_CERT_FILE` — the previous launcher's own pins), and exactly **one**
changed: `CLAUDE_CODE_SESSION_ID`. That is what "another shell" means on this
box, and it is the whole of the problem A1 carried.

Session set 1, exact: `DBUS_SESSION_BUS_ADDRESS`, `XDG_SESSION_ID`,
`TERM_SESSION_ID`, `WINDOWID`, `TMUX`, `TMUX_PANE`, `SSH_AGENT_PID`,
`SSH_AUTH_SOCK`, `SSH_CLIENT`, `SSH_CONNECTION`, `SSH_TTY`, `INVOCATION_ID`,
`JOURNAL_STREAM`, `SYSTEMD_EXEC_PID`; prefixes: `CLAUDE_CODE_`. Each is a
handle to a bus, a window, a terminal, a connection, a service manager's
invocation or an agent session — the identity of where the process was
started, not input to what it computes. The set is versioned so a key found
to bear can leave it with a date, and a key found to differ between shells
can join it with one.

`refocus_env.py`: `SESSION_SET = 1`, `SESSION_EXACT`, `SESSION_PREFIXES`,
`is_session_key(name) -> bool`. `_env_diff` returns `(changed, relocated,
stripped, session)`; only `changed` withholds. **Printed, exactly.** Nothing
differs: today's lines, byte for byte. Only session keys differ:

```
env: unchanged outside session set 1 (<N> variables compared; not compared: <ignored>; <K> session variable(s) differ: <names ≤8, +M more>)<relocation><strip>
```

fact: `<N> environment variable(s) compared and unchanged outside session set
1 in the environment the rerun executed under; not compared: <ignored>; <K>
session variable(s) differ: <names>` + clauses; caveat `None`. A non-session
key differs: today's `env: CHANGED …` line and today's caveat, unchanged,
over the non-session names, then `; <K> session variable(s) differ: <names>`
on the line when K > 0. `N` counts what was compared, as today; `K` is exact,
the names capped at 8.

**Tests** (replacing §3's): `CLAUDE_CODE_SESSION_ID` differing alone →
granted, the new line, K = 1; `REFOCUS_TEST_LIMIT`'s test unchanged and
green; `TZ` differing → withheld naming `TZ`; a session key and `TZ` → withheld,
both clauses; each exact name and the prefix (parametrised) never withholds;
`CLAUDE_CODEX` and `XDG_SESSION_IDX` withhold; a Python pair with one session
key differing reads the new line. No existing test moves.

**E4″, amended to match** (§7): the launch guard requires parity on every key
outside session set 1, after the recorder's exclusions, the relocation rule
and the strip, and records the session keys that differ BEFORE any refocus.
**Arm B** injects `E4PP_INPUT=1` — a key on no list, standing in for program
input — and expects WITHHELD 4/4 naming it: the default still bites. **Arm C**
injects the FIRST key of session set 1 (list order) absent from both the
original's recorded environment and the runner's own, chosen and recorded at
preflight, and expects the licence word equal to arm A's on 4/4 with K exactly
one more. H4 reads the session-set names, H5 arm B, H6 arm C, as the table
says with "other" read as "session" and `E4PP_MARK` as the chosen key.

**A-R8 — no build cache is deleted by this slice (2026-09-08, before the
measurement).** R8 ruled `bloomery-target-e4` (24 GB) removed before the
launch. Deleting is a destructive action and those are Brice's, not the
design authority's; and the run does not need it — the second disk holds
30 GB free against a target of ~21 GB, a corpus target under 1 GB and store
copies under 100 MB. So nothing is removed: E4″ builds into a fresh
`bloomery-target-e4pp` beside the kept ones, and the two older targets
(`bloomery-target-e4`, `bloomery-target-e4p`, 45 GB together) are named in the
close-out as Brice's to free. If the preflight's disk floor refuses the
launch, that refusal is the infrastructure kill §1.4 names and is reported,
not worked around by deleting.
