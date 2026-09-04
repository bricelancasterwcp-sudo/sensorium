# Rung-3 Entry Slice — Spawned-Task Names That Survive a Move — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Name a spawned task by its enclosing function's qualname plus an ordinal (`<parent> :: spawn@<qualname>#<k>`) instead of its `file:line`, so `diff --ignore-moves` pairs spawned tasks across a source-file move — then re-verify on the same bloomery split pair whose STOP this fixes, under a new pre-registration (E5′).

**Architecture:** The runtime is untouched: `sensorium_rt::spawn_child(site, f)` still composes `<parent task name> :: spawn@<site>`. Only the *site string* the transformer splices into the call changes, from `"<file>:<line>"` to `"<qualname>#<k>"`, and the unit manifest's `spawns` entries gain `qualname` and `ordinal` so the name ↔ location mapping stays recoverable. The converter passes manifest spawn entries through as opaque JSON, so it needs no change; the Python reader never parses task names, so it needs no change. Verification is a new pre-registered endpoint E5′ on the rung-2 acceptance clone's three branches (A original, B split, C split + planted swap), plus a new corpus case that moves a spawn site between two runs by a cargo feature, plus updated goldens.

**Tech Stack:** Rust (syn byte-offset splicer in `sensorium-transform`, `cargo-sensorium` driver), Python 3.12+ (corpus harness, acceptance runner), bloomery clone on `/mnt/extra`.

**Spec:** `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` §3.5 (spawned threads, F31) and §11 rung-2 exit / rung-3 entry; the decision itself: `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §1 — **Brice ruled option (b) on 2026-09-03** ("do as recommended"). Task 0 records the ruling in both documents, dated and non-silent. Honesty ledger: `rust/HONESTY.md` §3. Rigor: `~/.claude/skills/rigorous-experiments/SKILL.md`. Prior record this slice must not touch: `docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` (E5 = STOP stays as measured).

## Global Constraints

- **Branch:** `feat/rung3-entry-spawn-names`, created from `feat/rung2-recorder-v1` @ `8bf1c3e` (PR #10, open). The PR for this slice is opened against `feat/rung2-recorder-v1` (GitHub retargets to `main` when #10 merges). Never rebase either branch; never push `main`.
- **`/home/brice/workspace/bloomery` is read-only, forever.** The only bloomery that may be built or checked out is the clone `/mnt/extra/sensorium-rung2/bloomery` (HEAD detached at `e209ed9`; branches `e5-split` @ `e8c79be`, `e5-planted` @ `fea50b1` already exist — never rewrite them, never push them).
- **Every artifact set lives on the second disk**: `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target` for this workspace, `/mnt/extra/sensorium-rung2/bloomery-target` for the clone, `SENSORIUM_PROBE_TARGET=/mnt/extra/sensorium-rung2/probe-target` for `mechanics.sh`, `/mnt/extra/sensorium-rung2/corpus-target` for the corpus, a NEW `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e5prime` for E5′ traces. The root disk has ~13 GB free; never build into a default `target/`. One cargo invocation at a time on any one target (concurrent runs produce phantom `E0786` failures).
- **No box-local path in any committed file** except the acceptance record's own lens rows (ruled in rung 2). Tests read the clone only from `SENSORIUM_BLOOMERY_CLONE` and skip by name when it is unset.
- **`-D warnings` clean** (clippy on the box's 1.96 AND the constructs CI's 1.98 lints: run `cargo clippy --workspace --all-targets -- -D warnings`); the rustc oracle for goldens stays `-D warnings` with empty stderr.
- **Every new or changed test is mutation-tested** (break the pinned line → the test fails → restore; state the mutation and the failing output in the report). Mutant runs under `setsid` with a timeout, killed by pgid on timeout and verified with `ps -p`; never `pkill -f`. Python mutations purge `__pycache__` and set `PYTHONDONTWRITEBYTECODE=1`.
- **Pre-registration is byte-locked before the instrument exists**: Task 0 commits E5′'s §1 first; Task 5 verifies §1 is byte-identical to that commit before reading any number. **A completed measurement is never re-rolled**; a miss is reported as STOP with the number that missed.
- **`rust/sensorium-rt/src/bin/scenario.rs` is at exactly 800 lines** — add no line to it (split into `src/bin/scenario/` first if an arm is ever needed; this plan needs none).
- **The untracked `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` is Brice's** — never stage it; never `git add -A`; explicit paths only.
- Commit messages: conventional type, and every commit ends with the two trailer lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`
- Every shell command starts `cd /home/brice/workspace/sensorium &&` (the shell's cwd does not persist).

---

## Decisions (N1–N9)

| # | Decision | Why | Cost if wrong |
|---|---|---|---|
| N1 | The site string is `<qualname>#<k>`: `qualname` is the enclosing **fn item's** file-local qualname exactly as the manifest's `files[<rel>][..].qualname` writes it (`Type::method`, `outer::inner`, `tests::a_test`); `k` is the **1-based ordinal among the WRAPPED spawn sites of that (file, qualname), in byte-offset source order**. Unwrapped (declared) sites consume no ordinal. | A move keeps the qualname; the line does not. Counting only wrapped sites keeps `k` dense and unaffected by an unrelated `Builder::spawn` nearby. | A fn with two rewritten spawns gets `#1`/`#2`; inserting one before them renumbers — an honest DIVERGED (that fn changed). |
| N2 | The runtime is unchanged: `derive(site)` still yields `<parent> :: spawn@<site>` / `spawn@<site>`; the child-of-main and empty-name rules stand. | The rt never interpreted the site string. | none |
| N3 | Manifest `spawns` entries gain `"qualname": "<qualname>"` and `"ordinal": <k>|null` (null when `wrapped: false`); `file` and `line` stay. The converter carries entries as opaque JSON into meta `spawns`, so the trace keeps the name ↔ location mapping without a converter change. | An ordinal is a weaker identity for a human than a location; the manifest keeps the location one lookup away. | none |
| N4 | The ordinal is assigned during the walk by a per-`(qualname)` counter on `Ctx` (reset per file, since `Ctx` is per file); `splice::run`, after its existing byte-offset sort of `spawns`, **re-derives** each wrapped site's rank within its qualname and, on any mismatch with the walk-assigned ordinal, synthesises a `syn::Error` at that site so the unit **falls back** (`fell_back: true`, reason names the site) rather than shipping a wrong name. | DFS order equals source order for every construct the goldens exercise, but "source order" is what N1 promises; the self-check makes the promise enforced, not assumed. | A theoretical DFS/source-order disagreement costs one unit's instrumentation, loudly, never a wrong name. |
| N5 | A spawn inside a closure, block, `match` arm or nested expression belongs to the nearest enclosing **fn item** (closures push no scope). A spawn reached with an empty scope (no enclosing fn item at all) is a synthesised error → fallback; valid Rust cannot call `std::thread::spawn` outside a fn body, so this branch is documented as unreachable-by-construction, not tested. | Matches how guards already attribute code to fn items. | none |
| N6 | Four caveats are documented in spec §3.5 and HONESTY §3, each with the observable consequence: (i) inserting a wrapped spawn earlier in the same fn renumbers later ones (DIVERGED on their names — honest); (ii) the qualname is file-local, so renaming the impl's self type or moving the fn into another `impl` block renames the task; (iii) two files in one unit with an identical file-local qualname each start at `#1` — the tasks share a name and `diff` compares them as a multiset by content (HONESTY §7's twin rule); (iv) trait-impl twins in one file (`Type::fmt` for `Display` and `Debug`) share the qualname, so their ordinals continue across the twins in source order. | A rule with unstated edges is a rule that surprises. | none |
| N7 | E5′ is a **new pre-registered endpoint** in a **new** acceptance document (`docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md`); the rung-2 document and its `results.json` are never edited. Same arms, same commands, same diff invocations as E5; predictions in §1 below. | The instrument changed; E5 stays STOP as measured. | none |
| N8 | The `spawned_thread` corpus case is re-pinned to the new name; a new case `spawn_across_move` moves the spawning fn between two files across two runs of one crate by a cargo feature (`second_run`), pinning `MATCH modulo location` with every task paired and plain `diff` DIVERGED. | The inbox's own standard: a rule with no falsifier is not a promise. | none |
| N9 | Versions: `sensorium-transform` and `cargo-sensorium` `0.1.0 → 0.2.0` (a recorded-name change); `sensorium-rt` and the Python package unchanged (no behaviour change). | Semver for a producer-side format change. | none |

## Pre-registration — E5′ (Task 0 commits this section byte-for-byte as §1 of the new acceptance document; Task 5 verifies it is byte-identical before reading any number)

| Id | Question | Method | Endpoint (decided before the instrument exists) | Derivation |
|---|---|---|---|---|
| E5′ | With spawned tasks named `<parent> :: spawn@<qualname>#<k>`, does `diff --ignore-moves` verify the same source-file split that E5 measured as STOP? | Same three arms as rung-2 E5: A = the clone @ `e209ed9`; B = branch `e5-split` @ `e8c79be`; C = branch `e5-planted` @ `fea50b1`. Each arm: `cargo sensorium test -p bloomery-daemon --lib -- task::registry` under the driver built from THIS slice's HEAD (sha256 recorded), `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/bloomery-target` (warm; lens stated), traces to a NEW `SENSORIUM_DIR`. Then `sensorium diff --ignore-moves <A> <B>`, `sensorium diff --ignore-moves <A> <C>`, and plain `sensorium diff <A> <B>` (reported). | **A/B = `MATCH modulo location` with ≥ 1 moved, 0 added, 0 removed, and EVERY task paired by name — all ten task streams, the six `task::registry::tests::<test>` tasks AND the four spawned children. A/C = `DIVERGED` naming a step inside the swapped fn.** Any miss → STOP (report the number that missed; no re-roll, no threshold moved). | Rung-2 E5 read A/B DIVERGED on exactly four spawned-child names; the names differed only in `registry.rs:769` vs `registry/mod.rs:248`, stream hashes pairwise identical. Under N1 both sides name that site `TaskRegistry::spawn_task#1`. |
| E5′-names | Do the four children carry the predicted name on both sides? | From each arm's trace: `sensorium info <run>` / the `tasks` table (via `sensorium grep`/`tree` output or the conformance reader) — collect every task name containing `spawn@`. | **On A and on B, every spawned-child task name is exactly `task::registry::tests::<test> :: spawn@TaskRegistry::spawn_task#1`, and the multiset of `(name, hash)` pairs on A equals B's.** A different suffix → STOP. | The registry has one literal `std::thread::spawn` site, inside `impl TaskRegistry { pub fn spawn_task(..) }`, on both branches (verified by reading both trees before this plan was written). |
| E5′-coverage | Did the transformer still instrument every unit of the three arms? | The manifests written by the arms' builds: count `fell_back: true`. | **0 units fell back across the three arms.** ≥ 1 → STOP (N4's fallback fired on real code). | The self-check in N4 must never fire on bloomery. |

Lens for every endpoint: dev profile; the clone at `/mnt/extra/sensorium-rung2/bloomery`; warm target (the rung-2 acceptance target directory, only the driver changed); `~/workspace/bloomery` untouched (HEAD and porcelain read before and after); the 1-minute load read at each arm's start; nothing pre-registered is gated on a wall.

**Reported without a gate:** each arm's wall and event/thread counts; plain `diff <A> <B>` verdict (expected DIVERGED on location — the instrument seeing the move); the `--task` A/C arm on `task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion` (as E5 did).

---

## File Structure

- Modify: `rust/sensorium-transform/src/lib.rs` — `SpawnSite { file, line, wrapped, reason }` gains `qualname: String`, `ordinal: Option<u32>`.
- Modify: `rust/sensorium-transform/src/spawn.rs` — `site_argument(site_name: &str, use_path: Option<&str>) -> String` (was `(file, line, use_path)`); module docs.
- Modify: `rust/sensorium-transform/src/visit.rs` — `Ctx` gains `spawn_ordinals: HashMap<String, u32>`; `declare_spawn`/`rewrite_spawn` record qualname + ordinal; a `fn enclosing_qualname(&self) -> Option<String>` (scope join; `None` when empty).
- Modify: `rust/sensorium-transform/src/splice.rs` — after the `spawns.sort_by_key(offset)`, the N4 self-check.
- Modify: `rust/sensorium-transform/src/manifest.rs` — JSON for the two new fields (doc comment).
- Modify: goldens `rust/sensorium-transform/tests/golden/{spawn_thread,spawn_shapes,run_mutex_guard}.out.rs`; Create: `spawn_ordinals.in.rs`/`.out.rs`; Modify: `tests/golden.rs` (site assertions), `tests/common/mod.rs` (no change to the placeholder grammar — `@A(<site>)`/`@I(<path>;<site>)` take the new site text).
- Modify: `rust/cargo-sensorium/src/convert/spool.rs` (manifest fixture strings in tests, if they list spawn entries), `tests/fixtures/rust-spools/gen.py` (manifest fixtures), `docs/TRACE-FORMAT.md` §4 (`spawns` entry fields).
- Modify: `corpus/rust/spawned_thread/questions.yaml`; Create: `corpus/rust/spawn_across_move/{Cargo.toml,src/lib.rs,src/worker.rs,src/worker_moved.rs,questions.yaml}`; Modify: `corpus/rust/README.md`.
- Modify: `rust/HONESTY.md` §3 (+ index row), `README.md` (the "one known gap" callout), `rust/README.md` (naming line if any), spec §3.5/§11/§13, `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §1.
- Create: `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md` (+ `.results.json`), `rust/tests/acceptance_e5prime.py` (reuses `acceptance_phases.phase_e5`, `acceptance_lib`, `acceptance_schema._e5`), additions to `rust/tests/acceptance_schema.py` / `render_acceptance.py` for the two extra conditions.
- Modify: `rust/sensorium-transform/Cargo.toml`, `rust/cargo-sensorium/Cargo.toml` (0.2.0), `rust/Cargo.lock`.

---

### Task 0: Branch, pre-registration, and the ruling recorded

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md` (§1 only, verbatim from this plan's Pre-registration section; §2–§5 headings present and empty)
- Modify: `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` §3.5, §11
- Modify: `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §1
- Commit: this plan file

- [ ] **Step 1:** `git checkout -b feat/rung3-entry-spawn-names` from `feat/rung2-recorder-v1` @ `8bf1c3e`; confirm `git status --porcelain` shows only the untracked exit-status finding.
- [ ] **Step 2:** Write the acceptance document: title, a two-sentence preamble naming the rung-2 E5 STOP it re-verifies and the commit range, then `## 1. Pre-registration` containing the three-row table and the lens/reported paragraphs **byte-for-byte** from this plan, then empty `## 2. Environment`, `## 3. Results`, `## 4. Verdicts`, `## 5. Gaps`. Commit alone: `docs(rung3-entry): pre-register E5′ — spawned-task names across a move` and record the commit sha in the ledger (this is the byte-lock).
- [ ] **Step 3:** Spec §3.5: append a dated amendment ("**Amended 2026-09-03 (Brice's ruling, rung-3 entry):** …") stating N1 verbatim, N3, and the four N6 caveats; keep the old `spawn@<file>:<line>` text visible with a strike or footnote. Spec §11: under the rung-2 exit amendment, add "**Decided 2026-09-03 by Brice: option (b).** Executed as the rung-3 entry slice (plan `docs/superpowers/plans/2026-09-03-sensorium-rung3-entry-spawn-names.md`, endpoint E5′)". Inbox §1: prepend "**DECIDED 2026-09-03: (b), by Brice.** The three options below are kept as the record of the decision; the executing plan is …" — do not delete the options.
- [ ] **Step 4:** Commit the spec/inbox edits and this plan: `docs(rung3-entry): record Brice's E5 ruling (option b); plan`. Report both shas.

### Task 1: The transformer names a spawn site by qualname and ordinal

**Files:**
- Modify: `rust/sensorium-transform/src/{lib.rs,spawn.rs,visit.rs,splice.rs,manifest.rs}`
- Test: `rust/sensorium-transform/tests/golden.rs`, goldens listed above, unit tests in `spawn.rs`/`splice.rs`

**Interfaces:**
- Produces: `SpawnSite { file: String, line: u32, wrapped: bool, reason: Option<&'static str>, qualname: String, ordinal: Option<u32> }`; manifest JSON entries `{"file","line","wrapped","reason","qualname","ordinal"}`; the spliced site literal `"<qualname>#<k>"` (escaped through `escape_string_literal` — a qualname is identifier text and `::`, but escape anyway).

Invariants (each with a falsifier the implementer writes):
1. **Site text.** A wrapped site inside `fn a()` splices `"a#1"`; a second wrapped site later in `a` splices `"a#2"`; a wrapped site in `impl T { fn m() }` splices `"T::m#1"`; inside `fn outer() { fn inner() { spawn } }` splices `"outer::inner#1"`; inside a closure inside `fn c()` splices `"c#1"`; inside `impl Drop for X { fn drop() }` splices `"X::drop#1"`; inside `mod tests { #[test] fn t() }` splices `"tests::t#1"`. *Falsifier:* golden `spawn_ordinals` covering all seven shapes plus a `std::thread::Builder::new().spawn(..)` between two wrapped sites (declared `builder`, no ordinal; the sites around it read `#1` and `#2`), asserted via `@A(...)`/`@I(...;...)` placeholders in the `.out.rs` and `sites(&t)`/`spawns(&t)` assertions in `golden.rs`; the rustc oracle compiles it clean.
2. **Manifest fields.** Every `spawns` entry carries `qualname` (always) and `ordinal` (an integer for `wrapped: true`, `null` otherwise). *Falsifier:* a `golden.rs` assertion over `spawn_ordinals`'s `Transformed.spawns` listing `(line, qualname, ordinal, wrapped, reason)` in full.
3. **Ordinal = source-order rank** among wrapped sites of the same `(file, qualname)`. *Falsifier:* a test that, for every golden with spawns, sorts the wrapped entries by `line` per qualname and asserts `ordinal == rank + 1`.
4. **Self-check fallback (N4).** `splice::run`'s post-sort re-derivation, on a mismatch, returns the synthesised-error path the other three synthesised errors use (unit falls back, reason text names `"spawn ordinal"` and the site's line). *Falsifier:* a unit test that constructs a `Walked`/`Ctx` result with a deliberately wrong ordinal and asserts the error; plus a mutation of the walk counter (never increment) that the goldens catch AND the self-check catches (both must be red).
5. **Unchanged rewrite otherwise:** the callee replacement and the `use … as _;` wrapper are byte-identical to before except the site text (goldens `spawn_thread`, `spawn_shapes`, `run_mutex_guard` updated only in the site argument).
6. **Census pin unchanged:** `SENSORIUM_BLOOMERY_CLONE` census still reads 191 files / 2051 fn items / 8 spawn sites (all 8 wrapped) and 0 synthesised errors.

- [ ] **Step 1:** Write the `spawn_ordinals` golden pair and the `golden.rs` assertions first; run — they fail (site text is `file:line`).
- [ ] **Step 2:** Implement: `Ctx.spawn_ordinals: HashMap<String,u32>`; `enclosing_qualname()` = `scope.join("::")` (or `None` when empty → `fail(span, "spawn site outside any fn item")`); `rewrite_spawn` computes `k = *counter.entry(q).and_modify(+1).or_insert(1)`, builds `site_name = format!("{q}#{k}")`, calls `spawn::site_argument(&site_name, use_path)`, and `declare_spawn(offset, line, None, q, Some(k))`; `declare_spawn` for declared shapes passes `Some(q)` and `None`.
- [ ] **Step 3:** `splice::run` self-check after the sort: group wrapped spawns by `(qualname)`, walk in offset order, expect `ordinal == running count`; mismatch → synthesised error (same `Err` type the other three use), test it.
- [ ] **Step 4:** Update the three existing goldens' site text; run the whole transform suite + census (with `SENSORIUM_BLOOMERY_CLONE=/mnt/extra/sensorium-rung2/bloomery`, `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target`).
- [ ] **Step 5:** Mutations (each red then restored): counter never increments; qualname replaced by the file name; self-check comparison inverted; `ordinal` serialised as `wrapped` (field swap). Record outputs.
- [ ] **Step 6:** Bump `rust/sensorium-transform/Cargo.toml` to 0.2.0. Commit: `feat(transform): spawn sites named by enclosing-fn qualname + ordinal (E5 option b)`.

### Task 2: Driver, fixtures, and TRACE-FORMAT carry the new entry fields

**Files:**
- Modify: `rust/cargo-sensorium/src/convert/spool.rs` (test manifest strings), `rust/cargo-sensorium/src/wrapper.rs` (any test pinning a spawn entry), `rust/cargo-sensorium/tests/*` (any pinned manifest), `tests/fixtures/rust-spools/gen.py` + committed fixture manifests, `tests/test_rust_convert.py`, `docs/TRACE-FORMAT.md` §4 (`spawns` row: entry fields incl. `qualname`, `ordinal`), `rust/cargo-sensorium/Cargo.toml` (0.2.0), `rust/Cargo.lock`.

Invariants:
1. The converter passes `qualname`/`ordinal` through into meta `spawns` unchanged (it stores `Vec<serde_json::Value>`). *Falsifier:* a converter test whose manifest fixture carries `"qualname":"a","ordinal":2` and asserts the trace's meta `spawns[0]` has both, verbatim.
2. `info` still prints `J spawn sites (W wrapped)` (unchanged); vectors v01–v15 unchanged (`git diff --stat -- docs/trace-format/vectors` empty).
3. The Python conformance fixtures' manifests (gen.py) carry the two fields so `test_rust_convert` exercises the passthrough end to end.
4. `mechanics.sh` 44/44 on the probe (the probe's spawn test asserts a task name — update the expected text to `<parent> :: spawn@<qualname>#1` and say which check).

- [ ] Steps: write the converter passthrough test (red), update fixtures, run `cargo test --workspace`, `bash rust/tests/mechanics.sh`, `python -m pytest -q tests/test_rust_convert.py tests/test_corpus.py`, mutation on the passthrough test (drop the field in the fixture → red). Commit: `feat(driver): manifest spawn entries carry qualname + ordinal; TRACE-FORMAT §4`.

### Task 3: Corpus — re-pin `spawned_thread`, add `spawn_across_move`

**Files:**
- Modify: `corpus/rust/spawned_thread/questions.yaml` (every `spawn@src/lib.rs:33` → `spawn@tests::a_worker_holds_the_ledger#1`; the `truth:` prose says "named for its parent test and the spawning function's qualname and ordinal, not a line"; the `--task` argument likewise), `corpus/rust/README.md` row.
- Create: `corpus/rust/spawn_across_move/Cargo.toml` (package `corpus_spawn_across_move`, lib `spawn_across_move`, `[features] moved = []`), `src/lib.rs`, `src/worker.rs`, `src/worker_moved.rs`, `questions.yaml`.

The crate, exactly:

```rust
// src/lib.rs
//! Rust-only case: the function that spawns the worker MOVES to another file
//! between the two runs (a cargo feature selects which file compiles), and
//! nothing else changes. The planted truth is about the INSTRUMENT: a spawned
//! task's name is `<parent> :: spawn@<fn qualname>#<k>`, which a move does not
//! change, so `diff --ignore-moves` pairs the worker across the move while a
//! plain `diff` sees the move.
#[cfg(not(feature = "moved"))]
mod worker;
#[cfg(feature = "moved")]
#[path = "worker_moved.rs"]
mod worker;

pub fn apply(balance: u32, delta: u32) -> u32 { balance + delta }

#[cfg(test)]
mod tests {
    #[test]
    fn the_worker_is_named_across_a_move() {
        assert_eq!(crate::worker::start(5), 5);
    }
}
```

```rust
// src/worker.rs  and  src/worker_moved.rs — IDENTICAL text
pub fn start(delta: u32) -> u32 {
    std::thread::spawn(move || crate::apply(0, delta))
        .join()
        .expect("worker joined")
}
```

**Plan note (D3):** `#[path = "..."]` without `cfg_attr` is a plain attribute the mod-tree walker follows; if the walker does NOT follow `#[path]` (check `rust/cargo-sensorium/src/modtree.rs` first), use two distinct module names instead — `#[cfg(not(feature="moved"))] mod worker;` / `#[cfg(feature="moved")] mod worker_moved;` with `#[cfg(feature="moved")] use worker_moved as worker;` — and say which shape shipped and why.

`questions.yaml` (three questions; `cargo_args: ["test"]`, `second_run: {cargo_args: ["test", "--features", "moved"]}`):
1. `tree $RUN` — `expect_contains`: `spawn@start#1`; `expect_line`: `["task t3: tests::the_worker_is_named_across_a_move :: spawn@start#1"]`.
2. `diff --ignore-moves $RUN $RUN2` — `expect_line`: `["verdict: MATCH modulo location"]` and the moved-count line as the tool prints it (read `.superpowers/sdd/2026-09-02-sensorium-rung2-recorder-v1/acceptance/logs/e5-ab-moves.log` for the exact phrasing of the moved/added/removed and tasks lines; copy the shape, not the numbers); `expect_absent: ["DIVERGED", "REFUSED", "only in A", "only in B"]`.
3. `diff $RUN $RUN2` (plain) — `expect_line`: `["verdict: DIVERGED"]` and the line naming `src/worker.rs` against `src/worker_moved.rs`; `truth:` says the plain comparison sees the move and the projected one does not, which is the whole point.

Each `why_logs_fail` states why a log line cannot say that a worker in run 2 is *the same worker* as in run 1 (a thread name is a runtime number; a log carries no identity that survives a refactor).

- [ ] Steps: build the release driver from HEAD; `SENSORIUM_CARGO_SENSORIUM=<driver> CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target python corpus/run_corpus.py` → 34 cases, 0 failures; falsify the new case by editing `worker_moved.rs` to spawn twice (the name becomes `#2` for the second → question 2 reads DIVERGED) and by removing the feature switch (plain diff reads MATCH → question 3 red); restore; `pytest tests/test_corpus.py`. Commit: `test(corpus): spawn_across_move pins names across a file move; spawned_thread re-pinned`.

### Task 4: Ledgers and docs

**Files:** `rust/HONESTY.md` §3 bullet + falsifier paragraph + index row; `README.md` "one known gap" callout → "fixed 2026-09-03 (rung-3 entry), verified by E5′: <link>" keeping the measured-gap text as history; `rust/README.md`; spec §13 delta row; `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §1 (already marked decided in T0 — add the falsifiers shipped).

HONESTY §3's bullet becomes (keep the old text struck, dated): "A rewritten `std::thread::spawn` site produces the name `<parent task name> :: spawn@<qualname>#<k>` …" with N1's definition, the child-of-main rule unchanged, and N6's four caveats each in one sentence. **Falsified by** `rust/sensorium-transform/tests/golden.rs` (`spawn_ordinals`), `corpus/rust/spawn_across_move`, `corpus/rust/spawned_thread`, and the E5′ acceptance record.

- [ ] Commit: `docs(rung3-entry): HONESTY §3 naming rule, README gap closed, spec §13 delta`.

### Task 5: E5′ — the measurement

**Files:**
- Create: `rust/tests/acceptance_e5prime.py` (reuses `acceptance_lib`, `acceptance_phases.phase_e5`, `acceptance.real_config`; adds the names check and the fell-back count; writes `results-e5prime-raw.json` into THIS plan's ledger dir; detached: `setsid nohup … &`, pid file, `.DONE exit=<n>`)
- Modify: `rust/tests/acceptance_schema.py` (an `e5prime` assembler: E5′ = `_e5` conditions + `all_tasks_paired` + `names_as_predicted` + `units_fell_back == 0`, none-versus-zero), `rust/tests/render_acceptance.py` (renders the new document's §3 from its `results.json`)
- Modify: `docs/superpowers/acceptance/2026-09-03-sensorium-rung3-entry-e5prime.md` §2–§5 (+ `.results.json`)

Protocol:
1. **§1 byte-lock check** first: `git show <T0 sha>:<doc> | awk '/^## 1/,/^## 2/'` must equal the working tree's §1; refuse otherwise.
2. Preflight (refuse on failure): `/mnt/extra` ≥ 8 GB free, `/` ≥ 3 GB, load ≤ 4.0, clone porcelain empty and HEAD `e209ed9`, `~/workspace/bloomery` HEAD + porcelain recorded, driver built `--release` from HEAD with sha256 recorded, `SENSORIUM_DIR` new and empty.
3. Arms A, B, C exactly as `phase_e5` runs them; after each arm, read the manifests under `<bloomery-target>/sensorium/manifests/` written by THIS build (the invocation's manifest set — `acceptance_phases` already knows how E2′ scoped it) and count `fell_back`.
4. Names: for A and B, list every task name containing `spawn@` with its hash (the reader: `python -m sensorium` has no `tasks` command — use `sqlite3 <trace> "select name from task_fingerprints"` through `acceptance_lib` or the `sensorium.store.reader` API; say which) and compare against the predicted string and multiset.
5. Diffs as E5; verdict assembly per §1; clone returned to `e209ed9` detached, porcelain empty; `~/workspace/bloomery` re-read unchanged.
6. Render §2/§3 from `results.json`; write §4 verdict rows and §5 gaps BY HAND from the raw record, each number with `n` and lens; report walls without a gate.

- [ ] Commit: `docs(rung3-entry): E5′ measured — <verdict>` (the verdict word in the subject, whatever it is).

### Task 6: Close-out

- [ ] Version bumps done in T1/T2; `rust/Cargo.lock` updated; `CHANGELOG.md` if present.
- [ ] PR body draft in the ledger (not committed): what changed, E5′ verdicts with numbers, the four caveats, rulings placeholder, the standard trailer lines; base branch `feat/rung2-recorder-v1`.
- [ ] Full sequential verification on the box: `cargo test --workspace`, `cargo test -p sensorium-rt --features test-hooks`, `cargo clippy --workspace --all-targets -- -D warnings`, `bash rust/tests/mechanics.sh`, `python -m pytest -q`, corpus 34/…/0.

---

## Self-review

- **Spec coverage:** §3.5 rule → T1 (code) + T0/T4 (text); §11 decision → T0; inbox's "dated amendment + corpus case" requirement → T3/T4; E5′ → T0 (§1) + T5; TRACE-FORMAT for the manifest fields → T2; HONESTY falsifiers → T1/T3/T4/T5.
- **Placeholders:** none; the corpus crate and questions are given in full; the acceptance protocol names each step and refusal.
- **Type consistency:** `SpawnSite.ordinal: Option<u32>` (T1) = manifest `ordinal: <int>|null` (T1/T2) = fixture field (T2); `site_argument(site_name, use_path)` used only in `visit.rs`; the corpus task name `tests::the_worker_is_named_across_a_move :: spawn@start#1` follows N1 with file-local qualname `start` (worker.rs has no enclosing mod scope inside the file) and libtest's test path as the parent.
