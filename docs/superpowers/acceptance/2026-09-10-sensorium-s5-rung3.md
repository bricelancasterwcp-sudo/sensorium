# S5 rung 3 — naming the ambiguity: the untraced catcher, the window, the key: acceptance (pre-registered)

**Status: DONE.** §1 and §2 were written before any rung-3 code existed;
§3, §4 and §5 are the measured half and were written once the endpoints had
run. No endpoint STOPped.

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

Seven, each with the commit that carried it. Every one was decided and
committed **before** the endpoint it touches had read a number; a defect
found after a number is read is a finding in §4 and not an entry here.

| # | what changed | commit | why |
|---|---|---|---|
| 1 | The plan's T1 pin names `config.ts` | `11a02a4` | the pinned sentence quotes the file basename the verdict prints, and the fixture's file is `config.ts`; a pin quoting another name would have failed a correct reader |
| 2 | P3: the untraced-catcher SITE is the parent code object's own `(file, firstlineno, qualname)` | `11a02a4` | a CALL event's line is the CALLEE's definition line, not a place in the parent, so the parent's own first line is the one line on the wire that names the parent frame |
| 3 | The TypeScript key keeps the verdict's words, under `TS_MASK`, which exempts nothing | `7b849b3` | Gap 1 was never that the key held the sentence. `MASK` exempts `f16`/`f32`/`f64`/`f128` because RUST spells its float types that way (R-G8), so two of the three frame ids in the `useAiAssist` sink's verdicts survived masking as if they were type names and one place printed three blocks. Nothing on this wire is spelled `f<n>` for another reason. Dropping the sentence instead would have merged two re-raises from one origin that ended `→ swallowed` and `→ propagated`, and two propagations naming two different failing tests |
| 4 | The key names the ORIGIN only where the verdict names no site; the route joins under the same condition | `d4d7a21` | an unconditional origin component splits a sink by the places that reached it — the split the hand-built table had to undo — and §3.2 already says a shape FLAGS the origins its key ignored. Three rung-2 SWALLOWED blocks carry that flag (`useBuilderContent.<anonymous> L72` 3 origins, `GuardedButton.<anonymous> L29` 2, `createHooks.dispatch L98` 2), so an unconditional component would have made E-places read 32 against the locked 28 |
| 5 | The T0 script census: **six** `.sh` through the insecure default and **three** `.py` with a bare argv, not the plan prose's "five" and "four" | §2.2, read at `61816a5` | the census is the measured count and the pin is the measured one; the plan's prose was written from memory and is not what E-branch is read against |
| 6 | Four earlier rungs' scripts (`e10.sh`, `e11.sh`, `e5ts_split.sh`, `planted_change.sh`) added to `bin.sh`'s rule | `438c535` | spec §4.3 governs — "every script under `typescript/acceptance/` that invokes `sensorium`" — not the T0 census, which pinned a state and does not bound the fix. Ten scripts qualify; `e10p_eq.sh` and `e6.sh` mention the word and invoke nothing |
| 7 | **The fence's reading under the pre-registered merge** | `2564e00` | below |

**Entry 7, in full, because it is the one reading this pre-registration
could not settle for itself.** Two of §1's clauses cannot both hold once the
rung-3 key lands:

* **E-places** pre-registers the merge — the `useAiAssist.ts` L56 sink stops
  printing three blocks — and with it that the printed SWALLOWED shape count
  falls from 30 to **28**;
* **E6-TS′-fence** pre-registers every `SWALLOWED --` line of the re-read
  byte-identical to the rung-2 transcript's, *"brackets and ids included"*.

A merge cannot satisfy the second. Two of those three blocks stop being
printed at all, and the survivor's trailing bracket is the INVOCATION
bracket, which counts chains and processes across the whole invocation
(`exceptions_invocation.bracket`) — so merging three shapes necessarily
rewrites it. A literal line-by-line diff would therefore STOP on precisely
the change the other endpoint exists to pre-register. Nor are the three
lines "three identical lines" that a set comparison would collapse: they
name three different events (`e404`, `e370`, `e77`) and three different
frames (`f174`, `f128`, `f32`).

The reading taken, committed in `e6tsppp.py`'s docstring at `2564e00` before
the store was opened: the fence's own question is *"Did the new reader move a
verdict?"*, a verdict is the SENTENCE, and the trailing bracket is the
grouper's occurrence bookkeeping and E-places' business. So the gate is read
on the verdict sentence with its bracket stripped — **(a)** no sentence the
re-read prints may be absent from the rung-2 transcript, **(b)** no rung-2
sentence may be absent from the re-read except the pre-registered merge's,
**(c)** the `dispositions:` line compared whole — and the RAW line-by-line
diff, brackets and ids included, is carried in the cell (`raw_diff`) and
quoted verbatim in §4 so the reading can be judged rather than taken. The
literal reading's own difference count is reported beside it and is not
hidden by the reading that was chosen. §4 states both.

Two smaller ones, in the same commit and for the record rather than for a
gate: `e_fences.py` reports that the pre-registration's fenced test pattern
`tests/test_exceptions_python*.py` matches **no file in this tree** (the
Python reader is tested by `test_exceptions.py` and `test_exceptions_
synthetic.py`) and runs those two beside the gate without folding them into
it; and `e6ts.py`, `e7_report.py` and `e6tsppp.py` now take their recorder
from the environment, so every cell in §3 carries its own provenance
(`recorder_basis: own`) instead of the assembler's stamp.

## 3. Results

**Status: DONE.** Eight endpoints, every one read once, in P12's order: the
four fences first, then the single re-read of the kept invocation. No
endpoint STOPped, so the word this rung ships is `DONE` and not
`DONE-WITH-STOP`.

The numbers below are `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3.results.json`,
assembled by `typescript/acceptance/assemble_rung3.py`. Every cell is
`{value, n, lens, dropped}` plus `recorder` / `recorder_rev` /
`recorder_basis`; `recorder_basis` reads `own` on all eight, because every
instrument recorded its own. The recorder is **`sensorium 0.10.0 on
feat/s5-rung3 @ 2564e00be1fa42433dbb788311a22b4e578309fd`** — the version
does not move in this task: the bump to `0.11.0` is Task 6's, and a cell
claiming it here would name a recorder that did not take the reading.

| # | endpoint | cell (`value` of `n`) | the rule | word |
|---|---|---|---|---|
| 1 | E-legacy | **2 of 2** claims; `git diff 51978b1..HEAD --stat` over the fenced paths printed nothing; `75 passed` over the fenced tests and the Rust key's tuple equality | byte-unchanged, tests green → else STOP | **intact** |
| 2 | E6-TS | **21 of 21** cases matched the locked table; 0 differences, 0 dropped | set equality with the rung-2 locked table; every new pin green → else STOP | **no STOP** |
| 3 | E8‴ | **33 of 33** markers seen (19 `// SWALLOW` + 14 `// ESCAPE`); the checker ran **96** checks over 11 spools with **0** failures; `escape:count` asserted **14** | 0 failures, totals equal → else STOP | **no STOP** |
| 4 | E-branch | **1 of 1**; `tests/test_acceptance_scripts.py` → `9 passed` | green → else STOP | **intact** |
| 5 | E6-TS‴ | **0** false names over **20** printed untraced-catcher blocks; 17 of 17 hand-read rows named; **0** misses; `unnamed` after rung 3 = **0**, the table's prediction = **0**; 0 `no rule of this recorder` blocks left | 0 false names → else STOP; a miss is reported, not a stop | **no STOP** |
| 6 | E6-TS′-fence | **0** differences over the 29 gated lines the re-read prints (30 in rung 2 → 28 `SWALLOWED --` + 1 `dispositions:`); literal positional differences 21, all of them the shift two removed lines cause | every verdict sentence identical, nothing appearing, nothing disappearing but the pre-registered merge's, the tally whole → else STOP | **no STOP** |
| 7 | E-places | **28 of 28** SWALLOWED blocks; the `useAiAssist.ts` L56 sink printed once; the three multi-origin sinks still one block each | exactly 28, the rung-2 table's sink sites, S1/S11/S17 one block → else STOP | **no STOP** |
| 8 | E7‴ | **0** occurrences over **9** needles; vectors v30–v34 `10 passed` | 0 needles, vectors green → else STOP | **no STOP** |

Endpoints 1 and 4 were read together, by one run of `e_fences.py`, which is
one step earlier for E-branch than P12's list spells. P12's purpose is that
no fence be read after the re-read, and both are: E-branch gates the very
instruments E6-TS, E8‴ and the re-read run on, so reading it before them is
the more conservative order, not a looser one.

**Three wording slips in §2, settled here rather than left standing.**

* §2.1 calls the rung-2 adjudication "the 30 sink sites E-places counts
  against". It is **30 printed `SWALLOWED --` lines over 28 distinct sink
  sites** — S1/S11/S17 are one site printed three times, which the same
  sentence goes on to say. E-places counts 28 and always did.
* §2.2 gives the `escape:count` pin as `355:  k.check('escape:count',
  want.length === 13, want.length);`. The pin is the **value**, not the line
  number: `13` before T3, `14` after. Read today, the check sits at line 355
  and asserts **14**.
* The hand read's row 1 calls TanStack Query's retryer "a library `try`". It
  is a `.catch` chain on the promise `queryFn` returned, not a `try` block —
  which is the row's own point, since a `.catch` the transform never saw
  leaves no handler row either way. The prediction it supports
  (`useCompendiumQuery.queryFn`, `returned`) is the one the reader printed.

## 4. Decisions

### 4.1 The one re-read

One command, run once, against a store verified byte-for-byte before it and
again after:

```
$ sensorium exceptions 20260910-150809-cbc8de --limit 10000
```

`SENSORIUM_DIR=<store>`, `SENSORIUM_MANIFEST_DIR` and `SENSORIUM_SPOOL`
scrubbed from the environment, the binary resolved by `lens.sensorium_bin()`
to the branch's own `.venv/bin/sensorium`. `sha256sum -c` of §2.1's list from
the store root: **744 OK, 0 FAILED** before the read, and 744 OK, 0 FAILED
after it. Exit 0; 169 lines of answer.

The transcript is committed as `docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3-exceptions.txt`.
Its sha256 as the reader printed it is
`e952c6765abf024bc7fc52b41b3c2128e04b7703375a551499e5e1fa94957c9d` (169
lines); the committed file carries E7‴'s nine-line needle-rule header
prepended by `e7_report.py` after the count was taken, so it is 179 lines and
sha256 `8ab73f693c9ac45b4f4843b92b25d404ed315002074481378caea29d3ccf3ac6`.
The gated counts were taken on the text before the header, which contains
none of the five gated line kinds and none of the nine needles.

**What the read nevertheless wrote, stated plainly.** Two paths under the
store have a new mtime: `traces/` (the directory, not a file in it — SQLite
opens each `.db` and its transient `-wal`/`-shm` companions come and go, and
all 372 `.db` files hash exactly as T0 hashed them) and
`invocations.jsonl`, which gained one line:

```
{"utc": "2026-09-11T07:29:54.370593Z", "argv": ["exceptions", "20260910-150809-cbc8de", "--limit", "10000"], "exit": 0, "error": null}
```

That file is the store's own command journal, appended by EVERY `sensorium`
command a store is asked — the T0 hand read wrote lines to it too, with its
`tree … --around e2305` calls. It is not a trace and it is not in §2.1's
hashed set, which is the 372 `traces/*.db` and the 372 spool `.jsonl` files
and nothing else. "The store is read, never written" in the Global
Constraints means no `ts run`, no `ingest`, no `record`, no `refocus`: none
ran, and no byte of the lens moved. The journal line is the read's own
receipt, and it is quoted here rather than left for someone to find.

Its tally lines:

```
dispositions: swallowed 261, ambiguous 53
ambiguous by reason: escaped 21, untraced catcher 32
```

The second line is the one rung 3 exists to print. Rung 2's seventeen
catch-all BLOCKS covered **32** chains (1+4+5+2+1+2+2+1+3+1+3+1+1+2+1+1+1);
all 32 are now `untraced catcher` and the remaining 21 are the `escaped`
sentences that already read that way. `unnamed` and `orphan` do not appear:
the reason line omits zeros, and there are none to print.

### 4.2 E6-TS‴ — the seventeen, against the hand read

Twenty printed untraced-catcher blocks, matched to rows by ORIGIN SITE TEXT
(the head line's `<qualname> L<line>`, the event id stripped) under the T0
ruling. Every row was named; none falsely.

| row | origin site text | block's head | printed parent | predicted parent | printed variant | predicted | verdict |
|---|---|---|---|---|---|---|---|
| 1 | `fetchCompendium L11` | `e2305 RAISE   fetchCompendium raise Error('Failed to load compendium: 500 boom') L11` | `useCompendiumQuery.queryFn` | `useCompendiumQuery.queryFn` | `returned` | `returned` | matched |
| 2 | `Bomb L11` | `e13 RAISE   Bomb raise Error('boom') L11` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 3 | `<anonymous>.<anonymous>.Flaky L42` | `e41 RAISE   <anonymous>.<anonymous>.Flaky raise Error('boom') L42` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 4 | `buildCastle.get L99` | `e214 RAISE   buildCastle.get raise PermissionDeniedError('permission denied: module did not declare a permission granting "castle.fog"') L99` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 5 | `buildCastle.set L103` | `e310 RAISE   buildCastle.set raise TypeError('castle.chat is read-only') L103` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 6 | `createHooks.emit L80` | `e371 RAISE   createHooks.emit raise Error('Hooks.emit: modules may only emit "module:m:*" events; "combat:start" is reserved or out of namespace') L80` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 7 | `h L61` | `e408 RAISE   h raise Error('passenger node: tag "script" is not allowed') L61` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 8 | `buildLevelUpDefinition.emit L570` | `e48 RAISE   buildLevelUpDefinition.emit raise Error('level-up definitions apply via onCompletePicks, not emit') L570` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 9 | `resolveAttack L115` | `e162 RAISE   resolveAttack raise Error('resolveAttack failed: 400') L115` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 9 | `resolveAttack L115` | `e182 RAISE   resolveAttack raise Error('resolveAttack failed: 500') L115` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 9 | `resolveAttack L115` | `e98 RAISE   resolveAttack raise Error('resolveAttack failed: 500') L115` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 10 | `resolveAttack L112` | `e140 RAISE   resolveAttack raise OutOfRangeError('Target out of reach or line of sight') L112` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 11 | `evalFormula.parseFactor L94` | `e1387 RAISE   evalFormula.parseFactor raise FormulaError("Unknown identifier 'mystery'") L94` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 11 | `evalFormula.parseFactor L94` | `e1686 RAISE   evalFormula.parseFactor raise FormulaError("Unknown identifier 'constructor'") L94` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 12 | `evalFormula.parseFactor L86` | `e1407 RAISE   evalFormula.parseFactor raise FormulaError("Unknown function 'sqrt'") L86` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 13 | `evalFormula.parseFactor L76` | `e1443 RAISE   evalFormula.parseFactor raise FormulaError('Unexpected end of formula') L76` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched (block covers 2 origins) |
| 14 | `evalFormula L42` | `e1451 RAISE   evalFormula raise FormulaError('Formula empty or too long') L42` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 15 | `evalFormula.parseFactor L74` | `e1666 RAISE   evalFormula.parseFactor raise FormulaError('Formula too deep') L74` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 16 | `loadImagePixels L117` | `e159 RAISE   loadImagePixels raise Error('Cannot read pixels from a tainted (cross-origin) canvas: https://evil/map.png — SecurityError: The canvas has been tainted by cross-origin data.') L117` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |
| 17 | `loadImagePixels L108` | `e189 RAISE   loadImagePixels raise Error('Could not acquire a 2D canvas context for image analysis') L108` | `<anonymous>.<anonymous>` | `<anonymous>.<anonymous>` | `returned` | `returned` | matched |

**The three splits** — one rung-2 block becoming several, because the rung-3
key holds the untraced catcher's PARENT and a shape that aggregated raises
under several test functions has several parents:

* **row 9** (`resolveAttack L115`), rung 2's `[×3 over 1 process: first e98
  …]`, is now three blocks: `e98` under `f38`, `e162` under `f60`, `e182`
  under `f70` — the three `it` bodies at `attackRoll.test.ts:73`, `:136` and
  `:152` the hand read's note 9 names, which predicted the split in as many
  words ("including if rung 3's site-bearing key splits the shape");
* **row 11** (`evalFormula.parseFactor L94`), rung 2's `[×3: e1387, e1686,
  e1700]`, is now two: `e1387` under `f685` and `e1686` (+`e1700`) under
  `f864` — the two `it` bodies at `formula.test.ts:33` and `:50` note 11
  names;
* **row 14** (`evalFormula L42`), rung 2's `[×2: e1446, e1451]`, is split by
  the same rule, and the two halves land differently — see the joined block
  below.

**The one block that covers more than one row.** Row 13's block:

```
  e1443 RAISE   evalFormula.parseFactor raise FormulaError('Unexpected end of formula') L76
    AMBIGUOUS -- caught by untraced code inside <anonymous>.<anonymous> (formula.test.ts): f710 unwound, its caller f709 returned; not followed  [×2 over 1 process: first e1443 in 20260910-150830-30a5cd, +1]
      origins: 2 distinct (first shown)
      messages: 2 distinct (first shown)
```

Its second member is `e1446` — row 14's first half — because the `it` body
at `formula.test.ts:39` contains BOTH expectations, so `parseFactor L76` and
`evalFormula L42` unwound into the same parent frame `f709` and are one
shape under a key that holds the parent. The reader cannot show an origin it
did not print, so **this comparison saw one of the two**: the shown origin
is row 13's and its parent is row 13's prediction. It is recorded as a
limitation of what one block can display, not as a false name, and row 14 is
independently matched by its other half, `e1451` under `f731`, which prints
its own block. Both rows predict `<anonymous>.<anonymous>` and `returned`,
so nothing in the joined block contradicts either.

**The row that was not a test body.** Row 1 — the hand read's hardest call,
and the only one whose parent is not a vitest callback:

```
  e2305 RAISE   fetchCompendium raise Error('Failed to load compendium: 500 boom') L11
    AMBIGUOUS -- caught by untraced code inside useCompendiumQuery.queryFn (useCompendiumQuery.ts): f1105 unwound, its caller f1104 returned; not followed  [in 20260910-150813-fa928f]
```

The prediction reasoned that the frame above `fetchCompendium`'s is the
arrow TanStack Query holds as `queryFn`, which returned a pending promise
and is therefore the frame that went on, and that naming the test body two
frames further out would name a frame the serial never touched. The reader
printed `useCompendiumQuery.queryFn`.

**Nothing was missed and nothing was false.** 17 of 17 rows named, 0 rows
left unnamed, 0 names printed for an origin with no row, 0 blocks still
reading `no rule of this recorder reaches a verdict here`. The hand read's
last line predicted `predicted unnamed after rung 3: 0`; the reason line
prints no `unnamed` term at all.

### 4.3 E6-TS′-fence — the diff, verbatim

The raw difference over the five gated line kinds, ids and brackets
included, as the instrument carries it in `raw_diff`. Four lines, and all
four are the pre-registered merge:

```
- SWALLOWED -- caught by catch_callback at e404 (probeAiConfigured L56) in f174, which returned  [×130 over 11 processes: first e404 in 20260910-150810-4299a0, +129]
- SWALLOWED -- caught by catch_callback at e370 (probeAiConfigured L56) in f128, which returned  [in 20260910-150820-3e4dba]
- SWALLOWED -- caught by catch_callback at e77 (probeAiConfigured L56) in f32, which returned  [in 20260910-150822-6724b0]
+ SWALLOWED -- caught by catch_callback at e404 (probeAiConfigured L56) in f174, which returned  [×132 over 11 processes: first e404 in 20260910-150810-4299a0, +131]
```

Every one of the other 27 `SWALLOWED --` lines is byte-identical, bracket and
ids included, and so is `dispositions: swallowed 261, ambiguous 53`. The
re-read prints no `RE-RAISED --`, `PROPAGATED --` or `UNCAUGHT --` line, and
neither did rung 2.

Under §2.3's reading — sentence identical, bracket E-places' — this is **0
differences**. Under the literal reading the cell also reports **21**
positional differences and a line-count difference (31 → 29); nineteen of
the twenty-one are the shift the two removed lines cause below them, and the
other two are the `e404` bracket and the tail. The instrument carries that
list whole (`literal_detail`), so both readings are on the record and the
verdict word is attached to the one §2.3 states.

### 4.4 E-places — the merged block, quoted

```
  e404 HANDLED probeAiConfigured handled Error('network down') L56
    SWALLOWED -- caught by catch_callback at e404 (probeAiConfigured L56) in f174, which returned  [×132 over 11 processes: first e404 in 20260910-150810-4299a0, +131]
      born outside a throw statement (a reject())
      messages: 2 distinct (first shown)
```

**A finding, and it is a finding rather than a §2.3 entry because it is
about a number that was read.** §1's E-places clause says the merged block
prints "once with `[×3 …]`". It prints once — which is the clause's
substance — but the bracket reads `[×132 over 11 processes: first e404 in
20260910-150810-4299a0, +131]`. `[×3 …]` was never a string this tool could
print for this shape: the invocation bracket counts CHAINS and PROCESSES,
never blocks, and the three rung-2 members already carried 130, 1 and 1
chains. The arithmetic is conserved exactly — 130 + 1 + 1 = **132** — and the
process count stays **11** rather than rising to 13, because the two members
that printed their own block in rung 2 were already among the eleven
processes contributing to `e404`'s shape: under the new mask their two
shapes merge INSIDE their member trace, so each member still contributes one
append.

The clause is read as a prediction of the bracket's shape (printed once, with
a `×N` bracket) and the `3` as a miscount of what that bracket holds. The
endpoint's own measure — "the SWALLOWED shape count on the re-read and the
set of sink sites" — is met exactly, and §4.3 is the proof that the SET did
not otherwise move: no sentence appeared, and the only two that vanished are
this merge's. Had the word been read off the literal string, E-places would
have STOPped on a sentence naming an unprintable number.

The three rung-2 SWALLOWED blocks the pre-registration keeps SINGLE are
single, with their origin flags intact — which is `d4d7a21`'s fix
(instrument change 4) measured rather than argued:

| sink | blocks | `origins: N distinct` |
|---|---|---|
| `useBuilderContent.<anonymous> L72` | 1 | 3 |
| `GuardedButton.<anonymous> L29` | 1 | 2 |
| `createHooks.dispatch L98` | 1 | 2 |

### 4.5 E6-TS — the corpus

`e6ts.py` over every TypeScript corpus case that asks an `exceptions`
question: **21** of the 32 case directories, which is the 17 rung 2 locked
plus T4's four. All 21 matched. The collector compares the printed
`dispositions:` line WHOLE (a substring match would let `dispositions:
swallowed 1` satisfy a case whose tally grew a term), counts `SWALLOWED --`
lines independently of the tally and refuses a case where the two disagree,
compares the whole `ambiguous by reason:` line for the five cases that pin
one, and runs each case's own `expect_line` / `expect_absent` pins through
the corpus harness's own checker over the same recording.

The four new cases print 0 `SWALLOWED --` lines each, as pre-registered.
`translated` prints `ambiguous by reason: escaped 1, untraced catcher 1`:
its wrapper block reads the untraced-catcher reason beside the original's
escaped one, on one recording, which is the pre-registration's own sentence.

**One wording note, decided before the number and recorded here.** §1 says
`translated`'s reason has "parent the test function". The reader prints
`caught by untraced code inside <anonymous> (translated.test.ts)`: the
qualname the trace holds for the test callback's code object, not the test's
title. Naming the FRAME is what P3 chose and what every row of the hand read
was checked against; "the test function" in §1 is that frame, spelled the way
the wire spells it.

### 4.6 E8‴ and E7‴

**E8‴.** `npm run probe` in `typescript/probes`, `SENSORIUM_TIER=call`, spool
and manifest directory outside the repository. `node v24.16.0`, `npm
11.13.0`, at `2564e00be1fa42433dbb788311a22b4e578309fd`. The checker read 11
spools and ran **96** checks with **0** failures; `escape:count` asserted
**14**. The markers read from the files: `grep -c '^\s*// ESCAPE '
escape.probe.test.ts` = **14**, `grep -c '^\s*// SWALLOW '
swallow.probe.test.ts` = **19** — the post-T3 values §1 pre-registers, the
14th being T3's `callback_bare_rethrow catch_callback`. `e8pp.py` counts the
denominator out of the probe sources rather than out of the checker, so a
checker that stopped asserting a marker would shrink the ratio's numerator
and not its population: 33 of 33.

**E7‴.** `e7_report.py` with `E7_NEEDLES=rung3` over the saved transcript —
driven directly rather than through `e7.sh`, because nothing had to be run
again to read it. Nine needles, `oid` / `chain` / `Err` whole-word and
case-sensitive and the six prose ones substring and case-insensitive, the
rule printed into the transcript's own header where a reader of the committed
file can see it. **0 occurrences of all nine.** The three ungated context
words (`python`, `rust`, `asyncio task`) are 0 as well. Vectors v30–v34: `10
passed, 61 deselected`.

### 4.7 E-legacy and E-branch

`git diff 51978b1..HEAD --stat --` over `exceptions_rust.py`,
`exceptions.py`, `rust/`, `tests/test_exceptions_rust*.py`,
`tests/test_exceptions_invocation.py` and `tests/test_exceptions_python*.py`
printed nothing. The fenced tests plus
`tests/test_exceptions_typescript_grouping.py::test_the_rust_key_is_todays_tuple_verbatim`
— the one check that states the Rust key as a TUPLE EQUALITY rather than as
prose — are `75 passed`. `tests/test_acceptance_scripts.py` is `9 passed`.

**One dropped reason, carried rather than swallowed.** The fenced pattern
`tests/test_exceptions_python*.py` matches **no file in this tree**: the
Python reader is tested by `tests/test_exceptions.py` and
`tests/test_exceptions_synthetic.py`. The pattern is kept in the cell
exactly as §1 spells it, the miss is named in `dropped`, and those two files
are run beside the gate and reported without being folded into it —
`43 passed`. The fence's substance (the Python reader still passes its own
tests) holds under either reading; only the spelling of the pattern was
wrong, and the record says so rather than quietly widening a locked clause.

## 5. What the rung ships

**DONE.**

Eight endpoints, eight words, no STOP. `sensorium exceptions` on a
TypeScript trace now names the untraced-catcher footprint by name: the
seventeen shapes that read `no rule of this recorder reaches a verdict here`
on the rung-2 lens all read a reason instead, every one of them the reason a
human predicted from the source before any of this code existed, and none of
them a reason the recording does not hold. The catch-all is empty on this
lens — 32 chains moved out of it and 0 remain — and the tool did not buy that
by moving a verdict: the 27 swallow sentences it printed in rung 2 and still
prints are byte-identical, ids and brackets included.

What this rung actually establishes, as distinct from what it shipped:

1. **The hand read was right seventeen times out of seventeen**, including
   the one row whose parent is not a test body (`useCompendiumQuery.queryFn`)
   and the eight that needed a second reading. A reader predicting the tool's
   output from source, before the tool could print it, is the only evidence
   available that the new sentence says something true rather than something
   consistent.
2. **The site-bearing key splits where the hand read said it would.** Three
   rung-2 shapes became six blocks, each under its own test frame; no split
   changed a verdict and every split block matched the same row.
3. **One place stopped printing as three.** Gap 1 was a mask borrowed from
   another language's type names, not a key that held too much, and removing
   the borrowing was enough.

Three things this rung leaves open, none of them a stop:

* **A block can cover origins from two rows.** Row 13's does, because two
  expectations in one `it` body unwind into one parent frame, and the reader
  shows one origin and counts the rest. The count is honest (`origins: 2
  distinct (first shown)`) and the hidden member was recoverable here only
  because row 14 had a second half that printed on its own. A reader who
  wants every origin of a shape still has no way to ask for them.
* **`[×3 …]`.** §1 pre-registered a bracket string the tool cannot print
  (§4.4). Nothing measured moved, but a pre-registration that names a printed
  string should name one the printer can produce, and the next rung should
  pin brackets by their arithmetic rather than by a quoted literal.
* **A locked clause can name a file that does not exist.** §1's
  `tests/test_exceptions_python*.py` never matched anything (§4.7). The fence
  held under the intent reading and the record says so, but a pre-registration
  is only as good as the population it can actually enumerate, and a T0 step
  that expanded every fenced pattern once would have caught it.

The rung's word is **DONE**.
