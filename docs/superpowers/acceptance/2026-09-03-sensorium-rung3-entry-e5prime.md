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

(written by Task 5 from the raw record)

## 3. Results

(written by Task 5 from the raw record)

## 4. Verdicts

(written by Task 5 from the raw record)

## 5. Gaps

(written by Task 5 from the raw record)
