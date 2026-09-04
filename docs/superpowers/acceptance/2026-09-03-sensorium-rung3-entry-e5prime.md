# Rung-3 entry acceptance — E5′: spawned-task names across a move

This document re-verifies the E5 STOP recorded in
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`
(§3, §4) — spawned-task names embedding a source `file:line` broke
`diff --ignore-moves`'s pairing across the `registry.rs` split, even though
the moved tasks' stream hashes matched pairwise — under the qualname-plus-
ordinal naming rule Brice ruled for rung-3 entry (option (b), spec §11). The
commit range measured is this branch, `feat/rung3-entry-spawn-names`, from
its start at `8bf1c3e` (the `feat/rung2-recorder-v1` tip) through the commit
that ships the renamed `spawn_child` site string.

## 1. Pre-registration

**Byte-locked:** this section is committed alone as the byte-lock; Task 5
refuses to run if this section differs from that commit.

| Id | Question | Method | Endpoint (decided before the instrument exists) | Derivation |
|---|---|---|---|---|
| E5′ | With spawned tasks named `<parent> :: spawn@<qualname>#<k>`, does `diff --ignore-moves` verify the same source-file split that E5 measured as STOP? | Same three arms as rung-2 E5: A = the clone @ `e209ed9`; B = branch `e5-split` @ `e8c79be`; C = branch `e5-planted` @ `fea50b1`. Each arm: `cargo sensorium test -p bloomery-daemon --lib -- task::registry` under the driver built from THIS slice's HEAD (sha256 recorded), `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/bloomery-target` (warm; lens stated), traces to a NEW `SENSORIUM_DIR`. Then `sensorium diff --ignore-moves <A> <B>`, `sensorium diff --ignore-moves <A> <C>`, and plain `sensorium diff <A> <B>` (reported). | **A/B = `MATCH modulo location` with ≥ 1 moved, 0 added, 0 removed, and EVERY task paired by name — all ten task streams, the six `task::registry::tests::<test>` tasks AND the four spawned children. A/C = `DIVERGED` naming a step inside the swapped fn.** Any miss → STOP (report the number that missed; no re-roll, no threshold moved). | Rung-2 E5 read A/B DIVERGED on exactly four spawned-child names; the names differed only in `registry.rs:769` vs `registry/mod.rs:248`, stream hashes pairwise identical. Under N1 both sides name that site `TaskRegistry::spawn_task#1`. |
| E5′-names | Do the four children carry the predicted name on both sides? | From each arm's trace: `sensorium info <run>` / the `tasks` table (via `sensorium grep`/`tree` output or the conformance reader) — collect every task name containing `spawn@`. | **On A and on B, every spawned-child task name is exactly `task::registry::tests::<test> :: spawn@TaskRegistry::spawn_task#1`, and the multiset of `(name, hash)` pairs on A equals B's.** A different suffix → STOP. | The registry has one literal `std::thread::spawn` site, inside `impl TaskRegistry { pub fn spawn_task(..) }`, on both branches (verified by reading both trees before this plan was written). |
| E5′-coverage | Did the transformer still instrument every unit of the three arms? | The manifests written by the arms' builds: count `fell_back: true`. | **0 units fell back across the three arms.** ≥ 1 → STOP (N4's fallback fired on real code). | The self-check in N4 must never fire on bloomery. |

Lens for every endpoint: dev profile; the clone at `/mnt/extra/sensorium-rung2/bloomery`; warm target (the rung-2 acceptance target directory, only the driver changed); `~/workspace/bloomery` untouched (HEAD and porcelain read before and after); the 1-minute load read at each arm's start; nothing pre-registered is gated on a wall.

**Reported without a gate:** each arm's wall and event/thread counts; plain `diff <A> <B>` verdict (expected DIVERGED on location — the instrument seeing the move); the `--task` A/C arm on `task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion` (as E5 did).

## 2. Environment

Measured 2026-09-03T23:46:00-0500 → 2026-09-03T23:46:09-0500 by `rust/tests/acceptance_e5prime.py`, launched detached; the raw facts it recorded are `results-e5prime-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-03-sensorium-rung3-entry-e5prime.results.json`, which `acceptance_schema.assemble_e5prime` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless §1 is byte-identical to the commit that locked it. Checked at `10f2c59` with `awk '/^## 1/,/^## 2/'`: 3149 bytes, sha256 `2a036074ccf4eca0433f73b6b8e2698eda720078a07ab8afd908359d8ee8b9ff` on both sides — identical: yes.

| Pin | Value |
|---|---|
| driver commit | `0cb6b8b727735c1ca665a78245421a38d3b4de8b` (branch `feat/rung3-entry-spawn-names`) |
| driver | `/mnt/extra/sensorium-rung2/rust-target/release/cargo-sensorium`, built `--release` from that commit at 2026-09-03T23:20:07-0500 |
| driver sha256 | `ee3eca57d85c1cfa9bc31bbeb4d2e5c49cca2e72cfa698ecba9fa252df133675` — unchanged across the run: yes |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| clone (the workspace under measurement) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| arm A | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| arm B (`e5-split`) | `e8c79be1626f5808eb48a967d02a17217e614843` |
| arm C (`e5-planted`) | `fea50b14ba453a179e94dc96ca71a89a90c35f26` |
| clone porcelain before / after | empty / empty; restored to arm A detached: yes; `Cargo.lock` unchanged: yes |
| target (lens: **WARM** — the rung-2 acceptance target, only the driver changed) | `/mnt/extra/sensorium-rung2/bloomery-target` |
| manifests cleared before arm A | 185 stale manifests (1513858 bytes), so every `fell_back` counted in §3 belongs to this invocation |
| traces | `/mnt/extra/sensorium-rung2/sensorium-dir/e5prime` — new and empty at the preflight, refused otherwise |
| 1-minute load at the start | 0.12 |
| free disk at the start | 98.13 GB (target) / 13.58 GB (repo) |

The 1-minute load read at each arm's own first act (the `git checkout` that puts the arm's tree in place):

| Arm ref | At | 1-minute load |
|---|---|---|
| `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` | 2026-09-03T23:46:02-0500 | 0.19 |
| `e5-split` | 2026-09-03T23:46:06-0500 | 0.19 |
| `e5-planted` | 2026-09-03T23:46:08-0500 | 0.26 |
| `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` | 2026-09-03T23:46:08-0500 | 0.26 |

**`/home/brice/workspace/bloomery` was never checked out.** Its HEAD and porcelain were read before and after: `e209ed9b00f7` / empty before, `e209ed9b00f7` / empty after — unchanged: yes.

Two environment variables the shared preflight requires belong to phases this runner does not call and were not read: `SENSORIUM_CENSUS_DRIVER`, `SENSORIUM_PROBE_TARGET`.

## 3. Results

Rendered by `rust/tests/render_acceptance.py --doc e5prime` from `2026-09-03-sensorium-rung3-entry-e5prime.results.json`. Every cell is a number with its `n` and its lens, or `not measured (<reason>)`; `0` is a measured zero.

| Id | Value | n | Lens (abridged; the full lens is in the `results.json`) | Dropped |
|---|---|---|---|---|
| E5′ | 0 (rule: A/B MATCH-class with ≥1 moved, 0 added, 0 removed, all ten task streams paired; A/C DIVERGED inside the swapped fn) | 7 | pre-registered E5' conditions not met, of 7; three arms on three trees of the clone (A = e209ed9, B = e5-split… | none |
| E5′-names | 1 (rule: BOTH conjuncts — every spawn@ name exactly the predicted string on A and on B, AND A's multiset of (name, hash) equal to B's) | 2 | §1 E5'-names conjuncts missed, of 2 — (a) every spawn@ name is the predicted string, (b) the multiset of (name… | none |
| E5′-coverage | 0 (rule: 0 units fell back) | 12 | `fell_back: true` over the manifests each arm's build left in `<target>/sensorium/manifests/`, snapshotted the… | none |

### The three arms

| Arm | Tree | run | events | threads | tests | run wall (s) |
|---|---|---|---|---|---|---|
| A | `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` | `20260903-234606-be8f1c` | 890 | 10 | 6 | 0.07 |
| B | `e8c79be1626f5808eb48a967d02a17217e614843` | `20260903-234608-042036` | 890 | 10 | 6 | 0.07 |
| C | `fea50b14ba453a179e94dc96ca71a89a90c35f26` | `20260903-234608-74a53f` | 890 | 10 | 6 | 0.07 |

The wall is reported without a gate: nothing pre-registered rests on it.

### E5′ — does `diff --ignore-moves` verify the split now?

| Pre-registered condition | Met |
|---|---|
| `ab_verdict_is_match` | yes |
| `ab_moved_at_least_one` | yes |
| `ab_zero_added` | yes |
| `ab_zero_removed` | yes |
| `ab_every_task_paired` | yes |
| `ac_verdict_is_diverged` | yes |
| `ab_all_ten_task_streams_paired` | yes |

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| E5′ conditions not met | 0 | 7 | pre-registered E5' conditions not met, of 7; three arms on three trees of the clone (A = e209ed9, B = e5-split… | none |
| code objects paired across a move (A/B) | 28 | 1 | code objects paired across a move by qualname (A/B `--ignore-moves`, from the `key:` line) | none |
| task streams on each side (A/B) | 10 | 10 | task streams on each side of the A/B `--ignore-moves` diff, compared by content as (name, hash) -- the tool's … | none |

**How the A/B verdict line is read.** §1's label `MATCH modulo location` denotes the committed rung-2 `_e5` condition class (verdict token startswith MATCH; >= 1 moved; 0 added; 0 removed; every task paired), because on a trace whose causal events all live in tasks the literal string prints only on the thread-stream branch. Ruled in the ledger before the run, not after the number.

### E5′-names — the four children's names, and their hashes

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| §1 conjuncts missed, of 2 | 1 | 2 | §1 E5'-names conjuncts missed, of 2 — (a) every spawn@ name is the predicted string, (b) the multiset of (name… | none |
| spawn@ names equal to the predicted string | 8 | 8 | spawned-child task names equal to the predicted string; every task name containing `spawn@` on arms A and B, r… | none |
| spawn@ names NOT the predicted string | 0 | 8 | spawned-child task names that are NOT the predicted string, of the four on A plus the four on B; every task na… | none |
| spawn@ task streams on arm A | 4 | 10 | task streams on arm A whose name contains `spawn@`, of every task stream in that trace | none |
| spawn@ task streams on arm B | 4 | 10 | task streams on arm B whose name contains `spawn@`, of every task stream in that trace | none |
| (name, hash) pairs whose STORED hash differs, A vs B | 4 | 4 | of the four (name, hash) pairs, those whose HASH component differs between A and B; the STORED `task_fingerpri… | none |

| §1 conjunct | Met |
|---|---|
| `every_spawn_name_is_the_predicted_string` | yes |
| `stored_name_hash_multiset_a_equals_b` | NO |

Predicted string: `task::registry::tests::<test> :: spawn@TaskRegistry::spawn_task#1`. The stored multiset of (name, hash) pairs on A equals B's: NO. What the differ itself says about the same pairs, verbatim from the A/B `--ignore-moves` run:

```
tasks: 10 task stream(s) on each side, compared by content as (name, hash): all matched; the ordering between tasks is not compared
```

The four `spawn@` streams on each side, verbatim, with the stored `task_fingerprints.hash`:

| Side | Task name | Stored hash |
|---|---|---|
| A | `task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@TaskRegistry::spawn_task#1` | `5da1393dcf56b99067778684b4bdcbb5` |
| A | `task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@TaskRegistry::spawn_task#1` | `f40193423b122b4f5d2325ae30cbae10` |
| A | `task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1` | `47d897532d1b52bf4c7369c0b37cb8e8` |
| A | `task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1` | `f40193423b122b4f5d2325ae30cbae10` |
| B | `task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@TaskRegistry::spawn_task#1` | `0763e6a2f9a4aa017b9a49b1a1fe11dd` |
| B | `task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@TaskRegistry::spawn_task#1` | `2d03ae9014910e0c41941cced47760b2` |
| B | `task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1` | `2d03ae9014910e0c41941cced47760b2` |
| B | `task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1` | `82e1d6d4fbdcc7597302ac8102394140` |

### E5′-coverage — did the transformer instrument every unit?

| Quantity | Value | n | Lens | Dropped |
|---|---|---|---|---|
| units that fell back to the real tree | 0 | 12 | `fell_back: true` over the manifests each arm's build left in `<target>/sensorium/manifests/`, snapshotted the… | none |

| Arm | unit manifests read | written by this arm | fell back | spawn sites wrapped | spawn sites declared, not wrapped | unreached files |
|---|---|---|---|---|---|---|
| A | 4 | 4 | 0 | 8 | 0 | 0 |
| B | 4 | 2 | 0 | 8 | 0 | 0 |
| C | 4 | 2 | 0 | 8 | 0 | 0 |

| Arm | crate | type | fell back | files | sites | spawn sites | compiled by this arm |
|---|---|---|---|---|---|---|---|
| A | `bloomery_core` | lib | no | 18 | 94 | 0 | yes |
| A | `bloomery_daemon` | lib | no | 48 | 494 | 4 | yes |
| A | `bloomery_substrate` | lib | no | 5 | 40 | 0 | yes |
| A | `bloomery_daemon` | test | no | 48 | 494 | 4 | yes |
| B | `bloomery_core` | lib | no | 18 | 94 | 0 | no |
| B | `bloomery_daemon` | lib | no | 50 | 494 | 4 | yes |
| B | `bloomery_substrate` | lib | no | 5 | 40 | 0 | no |
| B | `bloomery_daemon` | test | no | 50 | 494 | 4 | yes |
| C | `bloomery_core` | lib | no | 18 | 94 | 0 | no |
| C | `bloomery_daemon` | lib | no | 50 | 494 | 4 | yes |
| C | `bloomery_substrate` | lib | no | 5 | 40 | 0 | no |
| C | `bloomery_daemon` | test | no | 50 | 494 | 4 | yes |

`unreached_reasons` (the manifest key a refusal on real code would show up in) was empty on every unit of every arm: no reason recorded on any unit.

### The four diffs, verbatim

**A/B `--ignore-moves` — the endpoint** — `sensorium diff --ignore-moves 20260903-234606-be8f1c 20260903-234608-042036`, exit 0:

```
A 20260903-234606-be8f1c: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260903-234608-042036: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
note: A recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: MATCH -- no causal event ran outside a task on either side, so the thread streams held nothing to compare; the tasks below carry the whole verdict
tasks: 10 task stream(s) on each side, compared by content as (name, hash): all matched; the ordering between tasks is not compared
moves:
  moved: OrganDecision::off  registry.rs -> mod.rs
  moved: TaskRegistry::get  registry.rs -> mod.rs
  moved: TaskRegistry::new  registry.rs -> mod.rs
  moved: TaskRegistry::spawn_task  registry.rs -> mod.rs
  moved: classify_probe  registry.rs -> organ.rs
  moved: contained  registry.rs -> helpers.rs
  moved: degrade  registry.rs -> helpers.rs
  moved: lock_entries  registry.rs -> helpers.rs
  moved: organ_after_run  registry.rs -> organ.rs
  moved: organ_before_run  registry.rs -> organ.rs
  moved: panic_message  registry.rs -> helpers.rs
  moved: panic_note  registry.rs -> helpers.rs
  ... +16 more moved
```

**A/C `--ignore-moves` — the negative control** — `sensorium diff --ignore-moves 20260903-234606-be8f1c 20260903-234608-74a53f`, exit 1:

```
A 20260903-234606-be8f1c: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260903-234608-74a53f: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
note: A recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)
tasks: DIVERGED -- 10 task stream(s) on A, 10 on B; only in A: task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion eb531e6a661d, task::registry::tests::task_ids_are_unique_and_monotonic 175adcac1853; only in B: task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion f5438bbd0630, task::registry::tests::task_ids_are_unique_and_monotonic 00f0f252acd4; the ordering between tasks is not compared
first difference inside task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion (A task t6, B task t5) at causal step 4:
  A:      e40 CALL    Journal::open  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-core/src/journal.rs)
  B:      e18 CALL    ImageStore::new  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/agents.rs)
drill into A: sensorium tree 20260903-234606-be8f1c --around e40
drill into B: sensorium tree 20260903-234608-74a53f --around e18
moves:
  moved: OrganDecision::off  registry.rs -> mod.rs
  moved: TaskRegistry::get  registry.rs -> mod.rs
  moved: TaskRegistry::new  registry.rs -> mod.rs
  moved: TaskRegistry::spawn_task  registry.rs -> mod.rs
  moved: classify_probe  registry.rs -> organ.rs
  moved: contained  registry.rs -> helpers.rs
  moved: degrade  registry.rs -> helpers.rs
  moved: lock_entries  registry.rs -> helpers.rs
  moved: organ_after_run  registry.rs -> organ.rs
  moved: organ_before_run  registry.rs -> organ.rs
  moved: panic_message  registry.rs -> helpers.rs
  moved: panic_note  registry.rs -> helpers.rs
  ... +16 more moved
```

**A/B plain `diff` (reported without a gate)** — `sensorium diff 20260903-234606-be8f1c 20260903-234608-042036`, exit 1:

```
A 20260903-234606-be8f1c: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
B 20260903-234608-042036: threads 1  compared: t1 [recorded main thread]  fp cae66941d9efbd404e4d88758ea67670
note: A recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
note: B recorded more than one thread: 10 started as OS threads (libtest's per-test threads and threads spawned by workspace code), 1 left a fingerprint; only the thread named above was compared -- a MATCH here is not a MATCH on the whole run, and a thread that ran no traced code leaves no fingerprint to compare at all
verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)
tasks: DIVERGED -- 10 task stream(s) on A, 10 on B; only in A: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager 26a265597336, task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@TaskRegistry::spawn_task#1 5da1393dcf56, task::registry::tests::classify_probe_reads_only_completed_runs_and_only_real_exit_codes 36ff86c6f2f7, task::registry::tests::contained_catches_a_panic_journals_it_and_lets_the_caller_continue c63a56b6024d, task::registry::tests::get_on_unknown_task_id_is_none e833efccb6ca, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion 4d3f4bbfbc54, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@TaskRegistry::spawn_task#1 f40193423b12, task::registry::tests::task_ids_are_unique_and_monotonic 3a0ca087b26a, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1 47d897532d1b, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1 f40193423b12; only in B: task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager ed73375d7a1d, task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager :: spawn@TaskRegistry::spawn_task#1 0763e6a2f9a4, task::registry::tests::classify_probe_reads_only_completed_runs_and_only_real_exit_codes 3bd10a0c2c57, task::registry::tests::contained_catches_a_panic_journals_it_and_lets_the_caller_continue bf5999564745, task::registry::tests::get_on_unknown_task_id_is_none 873c6645ba56, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion b165faa53908, task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion :: spawn@TaskRegistry::spawn_task#1 2d03ae901491, task::registry::tests::task_ids_are_unique_and_monotonic d0e11f792e4a, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1 2d03ae901491, task::registry::tests::task_ids_are_unique_and_monotonic :: spawn@TaskRegistry::spawn_task#1 82e1d6d4fbdc; the ordering between tasks is not compared
first difference inside task::registry::tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager (A task t7, B task t7) at causal step 0:
  A:      e43 CALL    tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs)
  B:      e40 CALL    tests::a_panicking_worker_becomes_error_not_stuck_running_and_does_not_poison_the_pager  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry/mod.rs)
drill into A: sensorium tree 20260903-234606-be8f1c --around e43
drill into B: sensorium tree 20260903-234608-042036 --around e40
```

**A/C, one task (reported without a gate)** — `sensorium diff --ignore-moves --task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion 20260903-234606-be8f1c 20260903-234608-74a53f`, exit 1:

```
A 20260903-234606-be8f1c: compared: task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion (t6)
B 20260903-234608-74a53f: compared: task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion (t5)
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
note: only task task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion was compared -- nothing is claimed here about the thread streams, the other tasks, or the order any of them ran in
verdict: DIVERGED at causal step 4
  common  e31 CALL    tests::fresh_dir  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs) (paired with mod.rs)
  common  e38 RETURN  tests::fresh_dir  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs) (paired with mod.rs)
  common  e39 CALL    tests::build_pager  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/task/registry.rs) (paired with mod.rs)
  A:      e40 CALL    Journal::open  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-core/src/journal.rs)
  B:      e18 CALL    ImageStore::new  (/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/src/agents.rs)
drill into A: sensorium tree 20260903-234606-be8f1c --around e40
drill into B: sensorium tree 20260903-234608-74a53f --around e18
moves:
  moved: OrganDecision::off  registry.rs -> mod.rs
  moved: TaskRegistry::get  registry.rs -> mod.rs
  moved: TaskRegistry::new  registry.rs -> mod.rs
  moved: TaskRegistry::spawn_task  registry.rs -> mod.rs
  moved: classify_probe  registry.rs -> organ.rs
  moved: contained  registry.rs -> helpers.rs
  moved: degrade  registry.rs -> helpers.rs
  moved: lock_entries  registry.rs -> helpers.rs
  moved: organ_after_run  registry.rs -> organ.rs
  moved: organ_before_run  registry.rs -> organ.rs
  moved: panic_message  registry.rs -> helpers.rs
  moved: panic_note  registry.rs -> helpers.rs
  ... +16 more moved
```

## 4. Verdicts

Written by hand against §1's rules, from the raw record
(`results-e5prime-raw.json` and the logs beside it in the gitignored plan
ledger). One row per §1 endpoint, with the number that decided it.

| Id | §1's rule, verbatim | What was measured | Verdict |
|---|---|---|---|
| E5′ | "**A/B = `MATCH modulo location` with ≥ 1 moved, 0 added, 0 removed, and EVERY task paired by name — all ten task streams, the six `task::registry::tests::<test>` tasks AND the four spawned children. A/C = `DIVERGED` naming a step inside the swapped fn.** Any miss → STOP" | A/B: 28 moved, 0 added, 0 removed, 0 unpaired, **10 task streams on each side, all matched**; verdict line quoted below. A/C: DIVERGED, first difference at causal step 4 inside `task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion` — A `Journal::open`, B `ImageStore::new`, the two statements the plant swapped inside `tests::build_pager`. **0 of 7 conditions missed** (the seven are not seven independent facts: `ab_all_ten_task_streams_paired` implies `ab_every_task_paired`, so that pair overlaps). | **PASS** |
| E5′-names | "**On A and on B, every spawned-child task name is exactly `task::registry::tests::<test> :: spawn@TaskRegistry::spawn_task#1`, and the multiset of `(name, hash)` pairs on A equals B's.** A different suffix → STOP." | Conjunct (a): **8 of 8** spawned-child names (four on A, four on B) are exactly the predicted string; **0** carry a different suffix. Conjunct (b), read on the source §1's Method names — the trace's `task_fingerprints` table: the multisets are **not** equal, **4 of 4** pairs differ in the hash component. **1 of 2 conjuncts missed.** | **STOP** |
| E5′-coverage | "**0 units fell back across the three arms.** ≥ 1 → STOP (N4's fallback fired on real code)." | **0** units with `fell_back: true`, over 12 unit-manifests read across the three arms (4 distinct units; `unreached_reasons` empty on every one). | **PASS** |

**Overall: STOP**, on E5′-names. The number that missed is 4 of 4 stored
`(name, hash)` pairs. It was read once, and no arm was re-run.

### 4.1 The A/B verdict line, quoted, and how it is read

The line the A/B `--ignore-moves` diff actually printed:

```
verdict: MATCH -- no causal event ran outside a task on either side, so the thread streams held nothing to compare; the tasks below carry the whole verdict
```

with, in the same output:

```
key: (file, qualname, kind), with 28 code object(s) paired across a move by qualname -- see moves below
tasks: 10 task stream(s) on each side, compared by content as (name, hash): all matched; the ordering between tasks is not compared
```

and no `added (only in B):`, `removed (only in A):` or `unpaired ` section.

**The reading, ruled before the run** (plan ledger, Task 3; `t5-context.md` §4
— written before any E5′ number existed, and not a re-interpretation after
one): on a trace whose causal events all live in tasks, the literal string
`MATCH modulo location` prints only on the thread-stream branch of
`_print_thread_match`, and here both thread streams are empty. §1's label
therefore denotes the condition **class** the committed rung-2 schema
`acceptance_schema._e5` already encodes — verdict token startswith `MATCH`;
≥ 1 moved; 0 added; 0 removed; every task paired — and E5′'s A/B condition is
judged by that class, with §1's "all ten task streams" clause added as a
seventh condition. All seven are met — and the seven overlap rather than
stacking: `ab_all_ten_task_streams_paired` is the stronger form of
`ab_every_task_paired` (it adds only the count), so the score is six
independent facts plus one refinement, not seven independent ones.

The A/C control printed:

```
verdict: the thread stream held no causal events on either side; DIVERGED on the tasks (below)
```

which `_verdict` reads as DIVERGED (the token is read before `MATCH` for
exactly this shape), and the first difference it names is inside the swapped
fn. The negative control holds: the instrument still sees a one-statement swap
through the same `--ignore-moves` leniency that pairs 28 moved code objects.

### 4.2 Why E5′-names reads STOP, and what is *not* being claimed

What the rung-2 E5 STOP was: the four spawned children's names embedded
`registry.rs:769` on A and `registry/mod.rs:248` on B, so `--ignore-moves`
could not pair them (`--ignore-moves` projects code-object keys, not task
names). **That failure is gone.** All eight names are now
`task::registry::tests::<test> :: spawn@TaskRegistry::spawn_task#1`, byte for
byte, and the A/B diff pairs all ten task streams.

What missed is §1's second conjunct, read on the column §1's own Method names.
`TRACE-FORMAT.md` §7 defines the stored fingerprint as a rolling blake2b over
`f"{file}\x1f{qualname}\x1f{kind}\n"` per causal event, and says in the same
section that

> `diff --ignore-moves` re-hashes both sides at query time over
> `code_objects.file` (`query/moves.hash_stream`), never one side from the
> stored row and the other from a fresh computation.

So a file move changes the **stored** hash by construction, and the tool never
reads that column when it pairs across a move. Measured here: all four stored
hashes differ between A and B (§3's table lists them), while the differ's own
`tasks:` line — quoted in §3, over the same four streams plus the six test
tasks — says `compared by content as (name, hash): all matched`.

Both numbers are in §3. Neither reading is chosen here in place of the other:
§1's Method column names the trace's tasks table, the pre-run dispatch
instructed that the multiset be read from `task_fingerprints`, and that is
what was read and what missed. **No ruling on which `hash` §1 meant was made
before the run** — unlike the A/B verdict-line reading, which was — so the
miss is reported as a miss, with its number, and the endpoint is not
re-interpreted after the fact. §5.1 states the defect this exposes in the
pre-registration itself; the repair is Brice's to rule, and none was applied
here.

## 5. Gaps

### 5.1 The E5′-names hash conjunct is unsatisfiable across a file move

This is the finding, and it is a defect in the **pre-registration**, not in
the code under measurement. §1 asks for "the multiset of `(name, hash)` pairs
on A equals B's" over a pair of arms that differ by exactly a file move, and
names the trace's tasks table as the source. By `TRACE-FORMAT.md` §7 the
stored hash hashes `file` per causal event, so across a move it *cannot* be
equal — the conjunct could not have been met by any implementation of the
naming rule, including a perfect one. The condition was written as a
restatement of §1's derivation column, which says rung-2's four children had
"stream hashes pairwise identical"; those pairwise-identical values
(`04afbcbcacf6`, `5976ef054dbe`, `5976ef054dbe`, `63737389821f` in the rung-2
record) are the differ's **re-hashed, move-lenient** values, not the stored
column. The two are different quantities and §1 conflated them.

Arm C corroborates the mechanism from the other side: its four stored
spawn-child hashes are byte-identical to B's (`0763e6a2…`, `2d03ae90…`,
`82e1d6d4…`, `2d03ae90…`, in task-id order), because `e5-planted` sits on
`e5-split`'s file layout and the planted swap is in the parent helper
`tests::build_pager`, not in the children. A behavioural change that the
A/C diff *does* catch leaves these four stored hashes untouched, while a
pure file move changes all four: the stored hash tracks file layout, not
the children's behaviour.

Two repairs are available; neither is applied here, because applying one after
reading the number is exactly what the protocol forbids:

1. read the conjunct on the differ's `(name, hash)` comparison — the
   `tasks:` line, which is what §1's derivation column was quoting — in which
   case this run's number is "all matched"; or
2. drop the hash conjunct from E5′-names and let E5′'s `every task paired`
   condition carry it, which is where the pairing question actually lives.

Ruling owed to Brice. Until then E5′-names stands as STOP with 4 of 4.

### 5.2 `MATCH modulo location` is a label, not a string the tool prints

Rung 2's §1 and this document's §1 both name the A/B endpoint
`MATCH modulo location`. On a task-only trace the tool never prints that
string (§4.1). The reading was ruled before this run, and the corpus case
`corpus/rust/spawn_across_move` (Task 3) pins the real wording, but the
vocabulary should be corrected where the endpoint is written, not repaired by
a ruling each time it is measured.

### 5.3 What the arms did and did not cover

* **The lens is a warm target, and it shows.** Arm A's build compiled all four
  units of a `-p bloomery-daemon --lib` build (4.37 s); arms B and C recompiled
  only `bloomery-daemon` (lib and lib test) in 1.19 s and 0.70 s, because cargo
  found `bloomery-core` and `bloomery-substrate` fresh. E5′-coverage's n is
  therefore 12 **unit-manifests** over 4 **distinct units**, 8 of them written
  by the arm that read them and 4 carried over from the previous arm. The
  manifests directory was cleared before arm A, so no rung-2 manifest is in
  the count.
* **E5′-coverage is not a workspace coverage figure.** It counts fall-backs
  over the units a `-p bloomery-daemon --lib` build reaches, which is what §1
  asked ("the manifests written by the arms' builds"). Rung 2's E2′ measured
  workspace coverage; nothing here re-measures it.
* **`unreached_reasons` was empty on every unit of every arm.** N4's refusal
  did not fire on bloomery — a negative observation over 4 units of one
  workspace, not evidence that it cannot fire.
* **The MATCH is on ten task streams, not ten threads.** Both arms recorded 10
  OS threads and exactly 1 left a thread fingerprint; the diff says so in its
  own `note:` lines, and the thread streams held no causal events. The tasks
  carried the whole verdict on both the A/B and the A/C side.
* **One process per arm.** Each arm's recorded invocation printed exactly one
  `run:` line (890 events, 10 threads, exit 0), so `phase_e5`'s "the run with
  the most events" dropped nothing.

### 5.4 Reported without a gate

Walls, on the §2 lens (warm target, one sample each — nothing pre-registered
rests on them): builds 4.37 s (A), 1.19 s (B), 0.70 s (C); recorded runs
0.07 s each; the whole run, preflight to cleanup, 9 s. Plain `diff <A> <B>`
read **DIVERGED** — the instrument seeing the move, as §1 expected — and the
`--task` drill-down on
`task::registry::tests::spawn_task_runs_in_background_and_get_reflects_completion`
read **DIVERGED at causal step 4**. Both outputs are in §3 verbatim.
