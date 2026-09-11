# S5 rung 3 — naming the ambiguity: the untraced catcher, the window, the key: acceptance (pre-registered)

**Status: not measured (rung 3 pending).** §1 and §2 are written; §3, §4 and
§5 are stubs until the endpoints have run.

§1 of this file was written and committed on the feature branch
`feat/s5-rung3` **before any line of rung-3 code existed**: the commit that
carried it changed nothing under `src/`, `typescript/src/`, `rust/` or
`corpus/`. §1 is the locked contract — after a number is read, no threshold
moves, no arm is added and nothing is re-read; an instrument defect found
before a number is read is fixed and written into §2.3 with its commit, and
found after, it is a finding. §2 keeps this rung's preflight pins. §3, §4 and
§5 are written when the endpoints have run and are the measured half of this
record.

The one thing this rung can be tempted to move after the fact is **the
hand-read table** — the seventeen predictions E6-TS‴ compares the new
reader's output against — because it is the only part of this
pre-registration that a human's reading of source decides rather than an
instrument. It lives in `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3-handread.md`,
was written before any rung-3 code existed, and is pinned by sha256 as §1's
last line; the lock test recomputes that sha and refuses a table that has
moved by a byte.

**Nothing is recorded in this rung.** The lens is the rung-2 invocation
`20260910-150809-cbc8de`, already in the store; §2.1 pins a content hash for
each of its 744 files, and the T5 re-read refuses if any hash differs.

The lock is enforced by `tests/test_acceptance_s5_rung3_lock.py`, which
compares the working tree's §1 against the commit that first carried it and,
separately, compares each of §1's two verbatim bodies against
`git show <sha>:<source>` — so "verbatim" is a claim a test holds, not one
this prose makes.

## 1. Pre-registration

Two blocks, copied verbatim from the two documents that own them. Nothing
below this line is paraphrased, reordered or reworded; the only editorial act
is that each source section's own heading is carried as the `###` sub-heading
that introduces its body here (both are `##` in their source files and appear
as `###` below), so that this record keeps its own §1–§5 numbering. The bodies
are byte-for-byte the source sections, each read to the next heading in its
source — which is why the plan block below ends with the horizontal rule that
terminates it in the plan file: the rule is part of the section's body, not a
choice made here. Sources, at the commits named:

- `docs/superpowers/specs/2026-09-10-sensorium-s5-rung3-naming-ambiguity-design.md` at **`51978b1`** (the merge commit on `main` that this branch was cut from) — `## 5. Pre-registered endpoints`, whole: the lens paragraph, the hand-read paragraph, the endpoint table and the stop rules that follow it
- `docs/superpowers/plans/2026-09-10-sensorium-s5-rung3-naming-ambiguity.md` at **`11a02a4`** (this branch's plan, at its second and final plan commit) — `## Pre-registration (…)`, whole, up to `### Task 0`

### 5. Pre-registered endpoints

Locked verbatim into the record's §1 at T0, byte-locked by
`tests/test_acceptance_s5_rung3_lock.py`, before any rung-3 code exists.

**The lens.** The rung-2 invocation, read from the store by label
(`LENS.txt`); its trace set is enumerated at T0 with a content hash per
trace, and the re-read at T5 refuses if any hash differs. Nothing is
recorded in this rung.

**The hand-read table (T0).** For each of the seventeen catch-all blocks in
`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt`
(the invocation transcript; 30 `SWALLOWED --` lines, 17 `no rule of this
recorder` lines, `dispositions: swallowed 261, ambiguous 53`): the origin as
printed, the lens source opened at the raise site and at every traced caller
up to the test, the untraced catcher the source shows (vitest `toThrow` /
`rejects`, an error boundary, a library's own `try`), the predicted reason
kind (`untraced catcher` with its variant, or `unnamed` when the source
shows no untraced catcher between the raise and a traced frame that went
on), and the predicted parent qualname. A shape whose source the reader
cannot decide is predicted `unnamed`. The table is the prediction; it is
locked before §2 is written.

| endpoint | question | measure | rule |
|---|---|---|---|
| E6-TS‴ | Does the reader name the seventeen truthfully? | one re-read of the invocation with the rung-3 reader; every printed untraced-catcher line compared to the hand-read table's row for that origin | **0 false names** — a printed name whose parent is not the table's, or printed for an origin the table predicted `unnamed`, is false → STOP. Reported: `unnamed` after, beside the table's predicted count; the count of table rows the reader left unnamed (a miss is reported, not a stop) |
| E6-TS′-fence | Did the new reader move a verdict? | every `SWALLOWED --` line, every `RE-RAISED`/`PROPAGATED`/`UNCAUGHT` line and the `dispositions:` line of the re-read, diffed against the rung-2 transcript above | byte-identical (ids included, the store is the same) → else STOP |
| E-places | Is the key the classifier's? | the SWALLOWED shape count on the re-read and the set of sink sites | exactly **28**, the 28 distinct sink sites of the rung-2 adjudication table, S1/S11/S17 one block with `[×3 …]` → else STOP |
| E6-TS | Does the corpus still pin it? | the corpus run with the driver; the per-case SWALLOWED set; the four new cases' and `translated`'s pinned lines | set equality with the rung-2 locked table; every new pin green → else STOP |
| E8‴ | Do the probes agree? | `npm run probe`; marker and check totals against the T0 file read | 0 failures, totals equal → else STOP |
| E7‴ | Does the reader speak this recorder's words? | the re-read transcript under the §4.3 matching rule, needles `oid`, `chain`, `Err`, `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own`; vectors v30–v34 | 0 needles; vectors green → else STOP |
| E-legacy | Is the fence intact? | `tests/test_exceptions_rust*.py`, `test_exceptions_invocation.py`, `test_exceptions_python*.py` and the Rust grouper's fenced output; `git diff` of `exceptions_rust.py`, `exceptions.py`, `rust/` | byte-unchanged, tests green → else STOP |
| E-branch | Do the instruments run the branch? | `tests/test_acceptance_scripts.py` | green → else STOP |

**Stop rules** as rung 2's: no endpoint is re-run after its number is read;
a re-read whose trace-set hash differs from T0's is dropped and named; the
shipping word is **DONE** or **DONE-WITH-STOP** and nothing else. An
instrument defect found before a number is read is fixed and recorded in the
record's §2.3 with its commit; found after, it is a finding.

### Plan section "Pre-registration (Task 0 commits spec §5 verbatim as the record's §1, plus this block)" — verbatim

- **The lens:** the rung-2 invocation `20260910-150809-cbc8de`, read by label from `LENS.txt`; its trace set is the 372 `traces/*.db` plus the spool `.jsonl` files, each `sha256` listed in `…-s5-rung3-tracehashes.txt` at T0; a re-read whose list differs is dropped and named.
- **The hand-read table** (`…-s5-rung3-handread.md`, T0, before any rung-3 code): one row per catch-all block in `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt` (17 rows): origin as printed; lens `file:line` of the raise; every traced caller up to the test, by qualname; the untraced catcher the source shows; predicted reason variant (`returned` / `had not closed` / `later unwound`) or `unnamed`; predicted parent qualname; the reading's difficulty (`first reading` / `second reading`). Its last line is the predicted `unnamed` count after rung 3.
- **E6-TS‴ gate:** 0 false names; a printed untraced-catcher line whose parent qualname is not the row's, or printed for a row predicted `unnamed`, is false. A row predicted named that the reader leaves unnamed is a miss, reported with its count, not a STOP.
- **E6-TS′-fence:** every `SWALLOWED --`, `RE-RAISED --`, `PROPAGATED --`, `UNCAUGHT --` and `dispositions:` line of the re-read byte-identical (brackets and ids included) to the rung-2 transcript above, else STOP.
- **E-places:** SWALLOWED shapes exactly 28; the merged block is `useAiAssist.ts:56`'s (rung-2 adjudication rows S1, S11, S17) printed once with `[×3 …]`; every other rung-2 SWALLOWED block unchanged, else STOP.
- **E6-TS per-case SWALLOWED set:** rung 2's locked table unchanged (`silent_swallow` 1, `logged_catch` 1, `callback_sink` 1, `callback_handled` 1, `await_rejection_caught` 1, `finally_return` 1, `dependency_throw` 1, `rethrow_hop` 1, every other rung-2 case 0) and the four new cases 0 each; `translated`'s wrapper block reads the untraced-catcher reason (`returned` variant, parent the test function).
- **E8‴:** `escape.probe.test.ts` carries 14 `// ESCAPE` markers (13 + `callback_bare_rethrow catch_callback`), `swallow.probe.test.ts` 19 `// SWALLOW` markers, `check.mjs` `escape:count` expects 14; 96 checks, 0 failed.
- **E7‴ needles and rule:** `NEEDLES_RUNG2` reused as `rung3` — `oid`, `chain`, `Err` whole-word and case-sensitive; `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own` substring and case-insensitive — printed in the transcript header; 0 hits over the re-read transcript; vectors v30–v34 green.
- **E-legacy:** the fenced files above show zero diff against `51978b1`; their tests green; `Shape.key` for the Rust fixture in `tests/test_exceptions_typescript_grouping.py` equals the pre-change tuple.
- **E-branch:** `tests/test_acceptance_scripts.py` green.
- **Versions:** Python 0.11.0, sensorium-ts 0.2.0, wire 1, trace format 4.

---

### The hand read this pre-registration locks

The seventeen predictions E6-TS‴ judges the reader against were written at
Task 0, before any rung-3 code existed, and are pinned here by content. A
table edited after a number is read is not a prediction, so the file's sha256
is §1's last line and the lock test recomputes it:

a117ea30a9a288d4c79aebbf3d11fd3562cfe3ae91a26ebe3dbfce430b624798  docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3-handread.md

## 2. Ambient pins (preflight, recorded before any rung-3 code exists)

Every value below is the output of the command beside it, run on this box on
2026-09-10 between 22:50 and 23:20 local time (`-05:00`) — the session that
opens rung 3 — before any file under `src/`, `typescript/src/`, `rust/` or
`corpus/` was touched. The lens is the VTT frontend **copy** at
`/mnt/extra/sensorium-s5/vtt/frontend` (VTT `0091e97`);
`~/workspace/projects/vtt` was neither read nor touched, and the lens was read
here by `sha256sum -c`, by `grep -rn` and by opening seventeen raise sites and
their callers, all of which only read. The store is
`/mnt/extra/sensorium-s5/store-rung2ts`; it was read by `sha256sum` and by
`sensorium info` / `tree` / `exceptions`, none of which write. Box paths appear
in this table because a pin without its location is not a pin; the rule that no
box path is committed binds every other file this rung produces, as it did at
rung 1, slice 2 and rung 2.

`<lens>` abbreviates `/mnt/extra/sensorium-s5/vtt/frontend` and `<store>`
abbreviates `/mnt/extra/sensorium-s5/store-rung2ts` throughout the rest of
this rung's files.

| Item | Command | Value |
|---|---|---|
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| nproc | `nproc` | `16` |
| 1-minute load, at pin time | `date -Iseconds; cat /proc/loadavg` | `2026-09-10T22:58:07-05:00`, then `1.19 0.88 0.63 3/2727 991974` — 1-minute load **1.19**, under the 4.0 refusal threshold. Rung 3 times nothing, so no arm is behind the load guard; the reading is kept because a box under load is a box whose readings deserve a second look |
| free disk `/` | `df -h /` | `4.7G` available on `/dev/nvme0n1p2` (100% used, 915G total) — the refusal floor is 3 GB; nothing this rung writes goes to `/` |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `63G` available on `/dev/nvme1n1p1` (86% used, 469G total) — the refusal floor is 8 GB. Rung 3 records nothing, so this number is not expected to move |
| worktree | `git rev-parse --abbrev-ref HEAD` | `feat/s5-rung3`, at `/mnt/extra/sensorium-rung2/s5-rung3`, cut from `main` at `51978b1` |
| `git rev-parse HEAD` | `git rev-parse HEAD` | `11a02a49d6e33742ee8fe9084b195256d1467a53` — the plan's second and final plan commit, this branch's tip when the pins were taken. **T0** for this rung |
| worktree venv | `.venv/bin/python -V` | `Python 3.13.13` (editable install of this worktree) |
| sensorium, worktree venv | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.10.0` — becomes `0.11.0` at Task 6 |
| sensorium, global tool | `$(dirname $(readlink -f $(which sensorium)))/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.10.0` — the same version. The global tool is **never reinstalled from this worktree** |
| sensorium-ts | `node -e "console.log(require('./typescript/package.json').version)"` | `0.2.0` — unchanged by this rung |
| lens manifest, verified | `cd <lens> && sha256sum -c /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | exit `0`, **748 OK, 0 FAILED** — the lens is byte-identical to the state rung 1 left it in and rung 2 read it in, so the hand read read the same source the lens run recorded. Manifest file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`, 748 lines |

### 2.1 The lens trace set, hashed (what the T5 re-read is refused against)

Nothing in this rung records. The lens is the rung-2 invocation
`20260910-150809-cbc8de` as it already sits in `<store>`, and the T5 re-read
reads exactly these bytes or is dropped and named.

| Item | Command | Value |
|---|---|---|
| the hash list | `(cd <store> && sha256sum traces/*.db spool/20260910-150809-cbc8de/*.jsonl)` → `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3-tracehashes.txt` | **744 lines** — 372 `traces/*.db` and 372 `spool/20260910-150809-cbc8de/*.jsonl`; every path relative to the store root, no box path in the file |
| `.db` lines | `grep -c '^[0-9a-f]\{64\}  traces/.*\.db$' <the hash list>` | `372` |
| `.jsonl` lines | `grep -c '^[0-9a-f]\{64\}  spool/20260910-150809-cbc8de/.*\.jsonl$' <the hash list>` | `372` |
| the hash list verifies | `cd <store> && sha256sum -c <the hash list>` | exit `0`, **744 OK, 0 FAILED** — read back against the store it was taken from |
| the hash list's own sha256 | `sha256sum <the hash list>` | `6624aba596a544ab0f834f45828f10fc0ab9fc1b7860a9e365e075da2862c3bd` |
| the rung-2 transcript | `sha256sum docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt` | `6f7f4687e09ee32b6123e909ff770e68f7fa4b8d4b360b7c92dbd9495b4e12ff`, 167 lines |
| its catch-all blocks | `grep -c "no rule of this recorder" <the transcript>` | `17` — the seventeen rung 3 exists to name |
| its SWALLOWED lines | `grep -c "SWALLOWED --" <the transcript>` | `30` — E6-TS′-fence compares every one of them byte-for-byte |
| its tally line | `grep "^dispositions:" <the transcript>` | `dispositions: swallowed 261, ambiguous 53` |
| the rung-2 adjudication | `sha256sum docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-adjudication.md` | `d9d45489cb6aacc45a6a901ca7b001041159607eb51713e6afd433ac6a8202ca` — the 30 sink sites E-places counts against, S1/S11/S17 being one site printed three times |
| the hand-read table | `sha256sum docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3-handread.md` | `a117ea30a9a288d4c79aebbf3d11fd3562cfe3ae91a26ebe3dbfce430b624798` — the same value §1's last line carries |
| what it predicts | `grep -c '^\| [0-9]' <the hand read>` (the pipe escaped for this table); its last line | **17 rows**, all predicting the untraced-catcher reason with the `returned` variant; 16 predict the parent `<anonymous>.<anonymous>` and one predicts `useCompendiumQuery.queryFn`; 8 needed a second reading; **`predicted unnamed after rung 3: 0`** |

### 2.2 The counts this rung's endpoints move against

**E8‴'s markers, as they stand today.** The pre-registration states the
post-T3 values (14 `// ESCAPE`, 19 `// SWALLOW`, `escape:count` expecting 14);
these are the values before T3 adds the `callback_bare_rethrow catch_callback`
marker. The `^\s*// ` anchor is what excludes the files' format-comment lines,
which describe the marker syntax rather than marking a shape.

| Item | Command | Value |
|---|---|---|
| escape markers | `grep -c '^\s*// ESCAPE ' typescript/probes/src/escape.probe.test.ts` | `13` (pre-registered after T3: **14**) |
| swallow markers | `grep -c '^\s*// SWALLOW ' typescript/probes/src/swallow.probe.test.ts` | `19` (pre-registered after T3: **19**, unchanged) |
| the checker's expectation | `grep -n "escape:count" typescript/probes/check.mjs` | `355:  k.check('escape:count', want.length === 13, want.length);` (pre-registered after T3: **14**) |

**The script census** (E-branch's surface: which acceptance scripts would run
a `sensorium` that is not this branch's).

| Item | Command | Value |
|---|---|---|
| scripts naming `sensorium` at all | `grep -ln sensorium typescript/acceptance/*.sh typescript/acceptance/*.py` | `26` of the 42 (`14` `.sh`, `28` `.py`) |
| `.sh` resolving it through the override | `grep -ln 'SENSORIUM_BIN:-sensorium' typescript/acceptance/*.sh` | **6**: `arms.sh`, `e10p.sh`, `e3.sh`, `e6pp.sh`, `e6tsp.sh`, `e7.sh` — each `SENSORIUM_BIN="${SENSORIUM_BIN:-sensorium}"`, so `SENSORIUM_BIN=.venv/bin/sensorium` points them at this branch |
| `.py` passing a bare argv | `grep -ln '\["sensorium"' typescript/acceptance/*.py` | **3**: `e11_report.py`, `firstuse.py`, `reported.py` — each `subprocess.run(["sensorium", …])` with no override, so they run the GLOBAL tool whatever the branch holds. The plan's Task-0 prose says "four `.py`"; the measured count is three, and this pin is the measured one |
| `.py` writing a `"lens"` key outside `lens.py` / `assemble*.py` | `grep -ln '"lens"' typescript/acceptance/*.py` then dropping `lens.py` and `assemble*.py` from the 5 it returns | **1**: `arm_line.py:72` (`"lens": env["LENS"]`) — the redaction surface the no-box-path rule binds |

**The rung-2 E6-TS table, as the corpus stands today** (E6-TS requires set
equality against it; the four new cases T4 adds are pre-registered at 0 each).

| Item | Command | Value |
|---|---|---|
| TypeScript corpus cases asking an `exceptions` question | `grep -l exceptions corpus/typescript/*/questions.yaml \| wc -l` | `17` |
| cases pinning exactly one SWALLOWED line | `grep -c 'SWALLOWED --' corpus/typescript/*/questions.yaml \| grep ':1$' \| wc -l` | `8`: `await_rejection_caught`, `callback_handled`, `callback_sink`, `dependency_throw`, `finally_return`, `logged_catch`, `rethrow_hop`, `silent_swallow` — one apiece |
| cases pinning none | the same, `grep ':0$'` | `9`: `asserted_catch`, `callback_escaped`, `callback_opaque`, `escaped_catch`, `primitive_rethrow`, `suspended_handler`, `test_failed`, `translated`, `unhandled_rejection_in_info` — zero apiece |

**The ceilings** (`tests/test_ceiling.py`, 800 lines; `docs/superpowers/`
exempt). Every file the plan names as at risk, measured before any edit.

| Item | Command | Value |
|---|---|---|
| `src/sensorium/query/exceptions_typescript.py` | `wc -l` | `613` — the reason and the reason table stay inside it unless it crosses 780 |
| `src/sensorium/query/exceptions_group.py` | `wc -l` | `419` |
| `src/sensorium/query/exceptions_invocation.py` | `wc -l` | `447` |
| `src/sensorium/query/exceptions_cmd.py` | `wc -l` | `767` — 33 lines of headroom for `Disposition.reason` |
| `typescript/HONESTY.md` | `wc -l` | `788` — §4's amendment must be net-neutral; new prose goes to the blind-spots file |
| `typescript/HONESTY-BLIND-SPOTS.md` | `wc -l` | `279` |
| `CHANGELOG.md` | `wc -l` | `756` |
| `docs/CARRIED-DEBT.md` | `wc -l` | `657` |
| `README.md` | `wc -l` | `790` — at most one sentence |
| `tests/test_exceptions_typescript.py` | `wc -l` | `610` — new test files rather than growth past 780 |

### 2.3 Instrument changes made before any endpoint ran

**None yet.** This section exists so that a defect found in an instrument
*before* a number is read has a place to be recorded with its commit; a
defect found *after* a number is read is a finding in §4, not an entry here.

## 3. Results

**Not measured (rung 3 pending).**

## 4. Decisions

**Not measured (rung 3 pending).**

## 5. What the rung ships

**Not measured (rung 3 pending).**
