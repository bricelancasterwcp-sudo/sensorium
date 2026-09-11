# S5 rung 4 — the focus tier for TypeScript: acceptance (pre-registered)

**Status: PRE-REGISTERED.** §1 and §2 were written before any rung-4 code
existed; §3, §4 and §5 are the measured half and are written once the
endpoints have run.

§1 of this file was written and committed on the feature branch
`feat/s5-rung4` **before any line of rung-4 code existed**: the commit that
carried it changed nothing under `src/`, `typescript/src/`, `rust/` or
`corpus/`. §1 is the locked contract — after a number is read, no threshold
moves, no arm is added and nothing is re-run; an instrument defect found
before a number is read is fixed and written into §2.3 with its commit, and
found after, it is a finding. §2 keeps this rung's preflight pins. §3, §4 and
§5 are written when the endpoints have run and are the measured half of this
record.

The one thing this rung can be tempted to move after the fact is **the hand
count** — the nine LINE rows H3 judges the transform against — because it is
the only part of this pre-registration that a human's reading of source
decides rather than an instrument. It lives in
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-handcount.md`, was
written before `typescript/src/bindings.mjs` and `probe.mjs` existed, before
the runtime had a `line` and before the converter had an `_on_line`, and is
pinned by sha256 as §1's last line; the lock test recomputes that sha and
refuses a table that has moved by a byte.

**This rung records.** Six `vitest run` invocations of one lens test file —
three unfocused (U1 U2 U3) and three focused (F1 F2 F3), interleaved
U1 F1 U2 F2 U3 F3 — into a store that is EMPTY at T0, named `<store>` in
every committed file of this rung and reached only through `SENSORIUM_DIR`.
The lens is read-only for the whole rung and is bracketed by `sha256sum -c`
of its manifest.

The lock is enforced by `tests/test_acceptance_s5_rung4_lock.py`, which
compares the working tree's §1 against the commit that first carried it and,
separately, compares each of §1's two verbatim bodies against
`git show <sha>:<source>` — so "verbatim" is a claim a test holds, not one
this prose makes.

## 1. Pre-registration

Two blocks, copied verbatim from the two documents that own them, and five
sub-sections that write down what those blocks defer to this record. Nothing
in the two blocks is paraphrased, reordered or reworded; the only editorial
act is that each source section's own heading is carried as the `###`
sub-heading that introduces its body here (both are `##` in their source
files and appear as `###` below), so that this record keeps its own §1–§5
numbering. The bodies are byte-for-byte the source sections, each read to
the next heading in its source — which is why the plan block below ends with
the horizontal rule that terminates it in the plan file: the rule is part of
the section's body, not a choice made here. Sources, at the commits named:

- `docs/superpowers/specs/2026-09-11-sensorium-s5-rung4-focus-tier-design.md` at **`aea6b47`** (the merge commit on `main` that this branch was cut from) — `## 8. Acceptance — E12, pre-registered (section 7, approved)`, whole: the record paragraph, the lens/store/subject paragraph, the H1–H8 table, the lens sentence and the instruments paragraph
- `docs/superpowers/plans/2026-09-11-sensorium-s5-rung4-focus-tier.md` at **`c70b2cf`** (this branch's plan, at its single plan commit) — `## Pre-registration (…)`, whole, up to `### Task 0`

One box path appears inside §1, and only inside the verbatim spec block:
that block's own words say the store is "a fresh directory under
`/mnt/extra/sensorium-s5/`". The block is carried byte-for-byte, so the
path is carried with it; editing it out would break the claim the lock
test holds. It is sanctioned here for that reason and for no other.
Everywhere else in this rung the store is `<store>` and the lens is
`<lens>`, and §2's pin table is the only other place in this record where
a box path is written.

### 8. Acceptance — E12, pre-registered (section 7, approved)

Record: `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md`
(dated by the day §1 locks; a later lock day renames it and §15 says so).
**§1 is committed alone and byte-locked** (`awk '/^## 1/,/^## 2/' |
sha256sum`) before the transform can splice a probe, the runtime can write
one, or the driver can resolve a spec; the runner refuses to start unless
the range is byte-identical to the locking commit. A dated amendment inside
§1, if any, is committed alone and adds a second sha, as rung-4 E9 did.

**The lens** is the VTT frontend copy at `0091e97` already named by
`typescript/acceptance/LENS.txt`, read-only for the whole run. **The store**
is a fresh directory under `/mnt/extra/sensorium-s5/`, named by the rung
and reached by label from the runner's environment, never by path in a
committed file. **The subject** is one test file, `src/lib/diceQueue.test.ts`,
and three pure functions of `src/lib/diceQueue.ts` chosen by reading the
source: `parseDiceGroups` (line 68: a `while` head assigning `m`,
per-iteration consts, an `if` block), `forcedDiceFromSource` (line 127: early
returns, a nested `for…of`, `+=`) and `buildDiceQueueEntry` (line 194: a
destructuring `const`). **Two runs**: U, `sensorium ts run -- npx vitest run
src/lib/diceQueue.test.ts`; F, the same under `--focus diceQueue.ts:<each of
the three>`.

| id | question | endpoint, both readings pre-committed |
|---|---|---|
| H1 | does an unfocused run stay unfocused? | U: `capabilities.line = false` and `locals = false`; LINE rows = 0; `watch U --at parseDiceGroups --expr groups == 0` prints `REFUSED: watch needs line, which recorder sensorium-ts 0.3.0 declares it does not produce (capabilities.line: false); nothing was checked`, exit 3. Second reading: the version token is `trace.recorder` as §2 records it |
| H2 | does a focus resolve and run? | the resolver's output names exactly three sites, `src/lib/diceQueue.ts:<each>`; F's vitest pass/fail counts equal U's, beside each run's exit status. A focused file that fails to load, or a suite whose counts move, is a **STOP** — no fallback, no narrower focus |
| H3 | one LINE per completed statement? | the FIRST activation of `parseDiceGroups` in F carries **N** LINE rows, N hand-counted in §1.1 line by line under §3.1–3.4 of this design, head rows and `unbound` lists written beside each; **N = PASS**; any other count a STOP with the diff of lines. Second reading: the rows' `line` values equal §1.1's list in order |
| H4 | does `watch` answer? | three triples (`--at`, `--expr`, verdict word + exit) written in §1.2 from the source under §4.1–4.2, at least one over a head row's binding and one over an `unbound` name after its block; all three as predicted → PASS. A verdict/exit disagreement is a finding about `Verdict`/`STATUS`, reported |
| H5 | does `flow --value` see it? | two sightings (literal, name, line) predicted in §1.3 among the three functions' LINE deltas, both found and no unpredicted sighting there → PASS; sightings elsewhere in the trace (RETURN values, other files) reported beside, not gated |
| H6 | is identity exact? | `flow --object e<id>:dice`, where `e<id>` is the first LINE row of `forcedDiceFromSource` carrying `dice` in F — a lookup step written in §1.4 (`grep F dice --kind LINE`, first row of that qualname), not a number, since an event id cannot exist before the run; the endpoint is the count and the serial: exactly two sightings — that row and the destructuring row in `buildDiceQueueEntry` — one serial, `continuity: exact`; second reading: the two sightings' `type` both `Array` |
| H7 | what does it cost? | F against U, the test file's wall, n=3 each, interleaved, medians, under the slice-2 load guard (`e6pp.sh`'s); the resolver's wall beside it; **reported, not gated** |
| H8 | did nothing else move? | every corpus case equal (Python, Rust, TypeScript, the ten new ones included); the Python suite, `cargo test --workspace`, the Node tests and the probes green; E7's needle grep at 0 over every transcript this rung prints |

**Lens sentence.** Values are read under §4.1; N uses §3.1–3.4's
definitions; a site is a `watch` site under `watch_cmd`'s own CLAIM. Measured
once; a `.FAILED` before any number is infrastructure (relaunch from zero,
archived); after a number it is a STOP.

**Instruments** (`typescript/acceptance/`, rung 3's discipline): every script
sources `bin.sh` and resolves `<repo root>/.venv/bin/sensorium`; every cell is
`{value, lens, dropped}` through `lens.py`; `e_fences.py` names real files
(§6.3); the assembler `assemble_rung4.py` verifies the hashed set — `traces/
*.db`, spool `*.jsonl`, `invocations.jsonl` with its pre-registered delta —
after every read; the E7 reporter writes its header to a sibling file. The
store-rung2ts directory (6.2 GB) is not read by this rung and may be freed
once E12's §1 is locked — Brice's call, named in the ledger.

### Plan section "Pre-registration (Task 0 commits spec §8's table verbatim as the record's §1, plus this block)" — verbatim

- **The lens and the store:** the VTT frontend copy at `0091e97` (`LENS.txt`), manifest-checked before and after every session; a fresh store `<store>` (`SENSORIUM_DIR`), empty at T0, hashed at T9 — every `traces/*.db`, every `spool/<invocation>/*.jsonl`, AND `invocations.jsonl`, listed in `…-s5-rung4-tracehashes.txt` after the arms and before any read; the journal's pre-registered delta is exactly one line per read command in §1.5's list, checked by the assembler after the reads.
- **The subject:** `src/lib/diceQueue.test.ts`; U = `sensorium ts run -- npx vitest run src/lib/diceQueue.test.ts`; F = the same with `--focus diceQueue.ts:parseDiceGroups --focus diceQueue.ts:forcedDiceFromSource --focus diceQueue.ts:buildDiceQueueEntry`. Three U and three F runs, interleaved U1 F1 U2 F2 U3 F3 under the load guard (`e6pp.sh`'s: 1-minute load under 4.0, up to 90 tries 20 s apart); H1–H6 read U1 and F1 (plan P13).
- **§1.1, the hand count for H3:** the first activation of `parseDiceGroups` in F1 is `parseDiceGroups('1d20')` (the first `it` of the file's first `describe`; vitest runs a file's tests in order). Counted under spec §3.1–3.4 and plan P1: one row per completed statement at every depth, a head row per iteration whose guard binds or assigns, the while's own row after the loop, no row for `return`, the CALL carrying `args` instead of a parameters row. The table lists every row with its source line, its `deltas` names and its `unbound` names; **N is the gate**; the file's lines are read at T0 from the copy (function at line 68), never from this plan.
- **§1.2, three `watch` triples for H4** on F1, `--at parseDiceGroups`: W1 `sides == 20` → **SATISFIED, exit 0**; W2 `count == 1` → **SATISFIED, exit 0, and no HIT row at the `while` statement's line** (the `unbound` reading: `count` dies on that row); W3 `m == null` → **SATISFIED, exit 0** (plan P1: the while's row carries `m`'s last write). Hits and the not-captured tally are reported, not predicted.
- **§1.3, two `flow --value` sightings for H5** on F1 among the three functions' LINE deltas: `flow --value 20` sights `sides` at the `const sides` row of the `'1d20'` activation; `flow --value "'1d20'"` sights `formula` as `arg formula` on that activation's CALL. Both found → PASS; every other sighting reported.
- **§1.4, the identity for H6:** `e<id>` = the first LINE row of `forcedDiceFromSource` carrying `dice` in F1, found by `grep F1 dice --kind LINE` (a lookup, not a number); `flow --object e<id>:dice` → exactly two sightings, that row and `buildDiceQueueEntry`'s `const { dice, skippedCount }` row, one serial, both `type` `Array`, `continuity: exact (serial identity)`.
- **§1.5, the read commands** (the journal's expected delta): `info` ×2, `watch` ×3, `flow` ×3, `grep` ×2, `frame` ×1, `tree` ×1 — twelve lines; listed verbatim in §1.5 with their arguments.
- **H1:** U1 `capabilities.line = false`, `locals = false`; LINE rows 0 (a `SELECT count(*) FROM events WHERE kind='LINE'`); `watch U1 --at parseDiceGroups --expr groups == 0` prints `REFUSED: watch needs line, which recorder sensorium-ts 0.3.0 declares it does not produce (capabilities.line: false); nothing was checked`, exit 3.
- **H2:** the resolver names exactly `src/lib/diceQueue.ts:parseDiceGroups`, `…:forcedDiceFromSource`, `…:buildDiceQueueEntry`; F1's `Test Files`/`Tests` lines equal U1's; `grep F1 parseDiceGroups --kind CALL` prints `parseDiceGroups(formula='1d20')` first. A focused file that fails to load, or a moved count, is a STOP.
- **H7:** medians of the three U and three F walls; the resolver's wall from `e12.sh`'s own timing of `node resolve.mjs`; reported.
- **H8:** `python corpus/run_corpus.py --require-driver` every case equal; `.venv/bin/python -m pytest -q`; `cargo test --workspace`; `npm --prefix typescript test`; `npm --prefix typescript/probes run probe`; `e7_report.py` with `E7_NEEDLES=rung2` at 0 over every transcript of §1.5's reads.
- **Versions:** sensorium-ts 0.3.0, Python 0.12.0, wire 1, trace format 4.

---

### 1.1 The hand count for H3

The count H3 gates on was derived by hand from the lens source at Task 0 and
lives in its own file,
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-handcount.md`,
pinned by sha256 as §1's last line. It counts the **first** activation of
`parseDiceGroups` in F1, which is `parseDiceGroups('1d20')` — the call at
`diceQueue.test.ts:16`, in the first `it` of the file's first `describe`;
`describe` callbacks only register, and the `it` bodies run in file order, so
no earlier activation exists in the run.

- **N = 9** — nine LINE rows. **N = PASS**; any other count is a STOP with
  the diff of lines (spec H3).
- **The rows' `line` values, in order** (H3's second reading): **69, 70, 71,
  72, 73, 74, 76, 75, 72**. Line 72 carries two rows — the `while` head's
  per-entry row and, after the loop, the `while` statement's own completion
  row — and lines 77, 78 and 80 carry none: every row's `line` is its
  statement's FIRST line, as the Rust focus design fixed it (its §3.1,
  "`line` = the statement's first line"), not the line of the closing brace
  the probe is spliced after.
- **Rows carrying `unbound`: 1** — the `while`'s own row, `count, sides`.
  Every other row's `"u"` is absent from the record (§3.6).
- **Rows with empty `deltas`: 3** — line 70 (a place write), line 76 (an
  expression statement that writes no identifier) and line 75 (the `if`
  completing).
- The parameter `formula` mints **no** row: the CALL carries `args` (§3.3),
  so N counts statements only. `return groups;` at line 79 mints no row
  (§3.1). The failed second evaluation of the `while` head mints no row
  (§3.2).

The hand-count file writes the rule that mints every row beside it, and why
each guard is true or false for `'1d20'`. It is the prediction; it is locked
before §2 is written.

### 1.2 Three `watch` triples for H4

All three on F1, `--at parseDiceGroups`, read under §4.1–4.2. The verdict
word is `watch`'s own (`SATISFIED` / `not satisfied` / `NOTHING WAS
CHECKED`), and the exit status is `STATUS`'s mapping of it (`ANSWERED` 0,
`NEGATIVE` 1, `UNSETTLED` 3). All three as predicted → PASS. Hits and the
not-captured tally are reported, not predicted. A verdict/exit disagreement
is a finding about `Verdict`/`STATUS`, reported.

| # | `--at` | `--expr` | verdict word | exit | the reading it carries |
|---|---|---|---|---|---|
| W1 | `parseDiceGroups` | `sides == 20` | `SATISFIED` | `0` | a plain statement delta: `const sides = parseInt(m[2], 10);` (line 74) writes `20` on this activation |
| W2 | `parseDiceGroups` | `count == 1` | `SATISFIED` | `0` | **and no HIT at line 72's `while`-completion row** — the `unbound` reading: `count` is one of the two names that die on that row (§3.4), so the fold has popped it and the predicate cannot be evaluated there |
| W3 | `parseDiceGroups` | `m == null` | `SATISFIED` | `0` | the head-binding reading under plan P1(a): the `while` statement's own row carries `m`'s LAST write, `null`, which §3.2's per-entry rule alone would leave unreported. `m` is `undefined` at line 71 and a match array at the head row, neither of which is `null` |

W3 is the triple over a head row's binding and W2 the triple over an
`unbound` name after its block, as spec H4 requires.

### 1.3 Two `flow --value` sightings for H5

A **sighting** is the `(literal, name, line)` triple spec H5 names, so one
triple seen in several activations is one sighting. The gated population is
the LINE `deltas` and the CALL `args` of the three focused functions in F1;
sightings elsewhere in the trace (RETURN values, other files) are reported
beside, not gated. Both found and no third triple in that population → PASS.

| # | command | literal | name | line | what it is |
|---|---|---|---|---|---|
| S1 | `flow F1 --value 20` | `20` | `sides` | `diceQueue.ts:74` | a LINE delta of `parseDiceGroups` — `const sides = parseInt(m[2], 10);` |
| S2 | `flow F1 --value "'1d20'"` | `'1d20'` | `formula` | `diceQueue.ts:68` | the CALL's `arg formula` on the `parseDiceGroups('1d20')` activation (§3.3) |

Why no third triple, by hand over the lens: within the three focused
functions the only numeric deltas are `count` (1, 2 or 4 across this file's
formulas), `sides`, `declared` (0, 1, 2, 3, 4 or 5), `skippedCount` (0, 1 or
2) and the `for…of` head binding `value` (15, 4, 3, 5, 12, 7, 17, 19) — only
`sides` is ever `20` — and every other delta is an array or an object, whose
`util.inspect` text is never `20`. The only string in the population is
`parseDiceGroups`'s `formula` argument; `forcedDiceFromSource` and
`buildDiceQueueEntry` are called with objects. Reported, not gated: by hand
the file drives fifteen `parseDiceGroups` activations, exactly one of them
with `formula === '1d20'`, and `sides` is `20` on several of them — one
triple, several events.

### 1.4 The identity for H6

`e<id>` is found by a **lookup**, never by a number: an event id cannot exist
before the run. The lookup, run on F1:

1. `grep F1 dice --kind LINE` — the LINE rows carrying the name `dice`.
2. Take the row at `diceQueue.ts:138` (`const dice: ForcedDie[] = [];`) of
   the **first `forcedDiceFromSource` activation that `buildDiceQueueEntry`
   called**. Its event id is `e<id>`.
3. `flow F1 --object e<id>:dice`.

**Why step 2 says "that `buildDiceQueueEntry` called" where spec §8's H6 rule
says "the first LINE row of `forcedDiceFromSource` carrying `dice`".** The
spec defers the lookup to this section ("a lookup step written in §1.4"), and
the plain first-row reading names a row with exactly ONE sighting, which
would STOP a correct reader. `forcedDiceFromSource`'s first three activations
that reach line 138 are called from `diceQueue.test.ts`, which is not focused
and therefore has no LINE rows; the array those activations create is sighted
only at line 138, and the object returned at line 155 holds it NESTED, which
§1 of the design puts out of scope. Only an activation that
`buildDiceQueueEntry` called has the second sighting the rule names — the
`const { dice, skippedCount } = forcedDiceFromSource(source);` row at
`diceQueue.ts:202`. This correction is made at T0, before any rung-4 code
exists and before any number is read; the spec's §8 stays verbatim above and
Task 10's §15 records the amendment.

The endpoint, unchanged from spec H6: **exactly two sightings** — the
`diceQueue.ts:138` row and the `diceQueue.ts:202` destructuring row — **one
serial**, `continuity: exact`; second reading: both sightings' `type` is
`Array`. Reported, not gated: by hand that row is the fourth `dice` LINE row
of `forcedDiceFromSource` in F1 (three earlier activations reach line 138
from the `forcedDiceFromSource` describe block; the three that do not reach
it return at line 134 on a count mismatch), and its activation is the one
`buildDiceQueueEntry` makes for the test at `diceQueue.test.ts:143`.

### 1.5 The read commands

**Thirteen** commands, listed here verbatim with their arguments, in the
order they are run. `U1` and `F1` stand for the two run ids, which do not
exist until the arms have run and are substituted at measurement; every
command is run as `sensorium <command>` against `<store>` through
`SENSORIUM_DIR`, and each `--expr` is one shell argument.

```
info U1
info F1
watch U1 --at parseDiceGroups --expr groups == 0
watch F1 --at parseDiceGroups --expr sides == 20
watch F1 --at parseDiceGroups --expr count == 1
watch F1 --at parseDiceGroups --expr m == null
flow F1 --value 20
flow F1 --value "'1d20'"
flow F1 --object e<id>:dice
grep F1 dice --kind LINE
grep F1 parseDiceGroups --kind CALL
frame F1 --fn parseDiceGroups
tree F1
```

**The journal's expected delta is the length of this list: thirteen lines**,
one per read command, checked by the assembler after the reads. Where the
plan block above says "twelve lines" it counts `watch` three times — the
three F1 triples of §1.2 — and leaves out H1's refusal on U1, which is the
third command here and is a read like any other. The block is carried
verbatim and is not edited; this list is the one the journal is checked
against.

Three of the thirteen are not §1.2's triples: `watch U1 …` is H1's refusal
(exit 3, nothing checked); `grep F1 dice --kind LINE` is §1.4's lookup; and
`grep F1 parseDiceGroups --kind CALL` is H2's third reading, which must print
`parseDiceGroups(formula='1d20')` first. `frame F1 --fn parseDiceGroups` is
read for the first activation's timeline and `tree F1` for the run's shape.

---

The hand count is the prediction H3 is judged against. It was written at Task
0, before any rung-4 code existed, and is pinned here by content: a table
edited after a number is read is not a prediction, so the file's sha256 is
§1's last line and the lock test recomputes it.

df0fe871d17b7762f716bb326cd841425505895a13fe9777d4357ed7f04518b7  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-handcount.md

## 2. Ambient pins (preflight, recorded before any rung-4 code exists)

Every value below is the output of the command beside it, run on this box on
2026-09-11 between 17:55 and 18:20 local time (`-05:00`) — the session that
opens rung 4 — before any file under `src/`, `typescript/src/`, `rust/` or
`corpus/` was touched. The lens is the VTT frontend **copy** (VTT `0091e97`)
that the first row below pins, abbreviated `<lens>` throughout the rest of
this rung's files; `~/workspace/projects/vtt` was neither read nor touched,
and the lens was read here by `sha256sum -c` and by opening three functions
of `src/lib/diceQueue.ts` and the whole of `src/lib/diceQueue.test.ts`, all
of which only read. The store this rung records into is the second row's,
abbreviated `<store>`; it does not exist yet.

Box paths are written **only in the pin tables of this section** — this
table and §2.1's, §2.1 being part of §2 — because a pin without its location
is not a pin, and the tables are the one place this record sanctions them.
This prose names the lens and the store by their labels alone, so every box
path in §2 is a table row. The rule that no box path is committed binds
every other file this rung produces, as it did at rung 1, slice 2, rung 2
and rung 3.

| Item | Command | Value |
|---|---|---|
| `<lens>`, the label | `ls -d /mnt/extra/sensorium-s5/vtt/frontend` | exists — the VTT frontend **copy** at VTT `0091e97`, read-only for the whole rung. `<lens>` abbreviates this path throughout the rest of this rung's files |
| `<store>`, the label | `ls -d /mnt/extra/sensorium-s5/store-rung4ts` | **does not exist** at T0 — `<store>` abbreviates this path throughout the rest of this rung's files; it is created empty by the first arm, reached only through `SENSORIUM_DIR`, and hashed at T9 |
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| nproc | `nproc` | `16` |
| 1-minute load, at pin time | `date -Iseconds; cat /proc/loadavg` | `2026-09-11T18:00:51-05:00`, then `0.44 0.45 0.39 2/2615 2776919` — 1-minute load **0.44**, under the 4.0 threshold H7's load guard (`e6pp.sh`'s) waits for |
| free disk `/` | `df -h /` | `4.4G` available on `/dev/nvme0n1p2` (100% used, 915G total) — the refusal floor is 3 GB; nothing this rung writes goes to `/` |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `63G` available on `/dev/nvme1n1p1` (86% used, 469G total) — the refusal floor is 8 GB, and this rung's six arms write into `<store>` on this device |
| worktree | `git rev-parse --abbrev-ref HEAD` | `feat/s5-rung4`, at `/mnt/extra/sensorium-rung2/s5-rung4`, cut from `main` at `aea6b47` |
| `git rev-parse HEAD` | `git rev-parse HEAD` | `c70b2cfe498788667766ef41257f61e5fc6af73f` — the plan's single plan commit, this branch's tip when the pins were taken. **T0** for this rung |
| worktree venv | `.venv/bin/python -V` | `Python 3.13.13` (editable install of this worktree) |
| sensorium, worktree venv | `.venv/bin/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.11.0` — becomes `0.12.0` at Task 10 |
| sensorium, global tool | `$(dirname $(readlink -f $(which sensorium)))/python -c "import importlib.metadata as m; print(m.version('sensorium'))"` | `0.11.0` — the same version. The global tool is **never reinstalled from this worktree**; this rung's binary is `.venv/bin/sensorium` |
| sensorium-ts | `node -e "console.log(require('./typescript/package.json').version)"` | `0.2.0` — becomes `0.3.0` at Task 2 |

### 2.1 The lens and the store

The lens is named by its own line, which is what every other file of this
rung quotes instead of a path.

| Item | Command | Value |
|---|---|---|
| the lens line | `cat typescript/acceptance/LENS.txt` | `VTT frontend at 0091e97 — vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores (powersave); snapshot taken under sensorium 0.8.7 / sensorium-ts 0.1.0 at 29c5059 (the snapshot's own provenance; each cell names its own recorder)` — one line, the whole file |
| lens manifest, verified | `cd <lens> && sha256sum -c /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | exit `0`, **748 OK, 0 FAILED** — the lens is byte-identical to the state rung 1 left it in and rungs 2 and 3 read it in, so the hand count read the same source the arms will record. Manifest file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`, 748 lines |
| the subject | `wc -l <lens>/src/lib/diceQueue.ts <lens>/src/lib/diceQueue.test.ts` | `212` and `188` lines; `parseDiceGroups` at line 68, `forcedDiceFromSource` at 127, `buildDiceQueueEntry` at 194 — the three the F arms focus |
| the rung-2 store, not read | `du -sh /mnt/extra/sensorium-s5/store-rung2ts` | `6.2G` — not opened by this rung; spec §8 leaves freeing it to Brice, named in the ledger |

### 2.2 The ceilings, and the counts this rung's endpoints move against

**The ceilings** (`tests/test_ceiling.py`, 800 lines; `docs/superpowers/`
exempt). Every file the plan names as at risk, measured before any edit.

| Item | Command | Value |
|---|---|---|
| `CHANGELOG.md` | `wc -l` | `800` — **at the ceiling**; cut at Task 1 before anything else |
| `typescript/HONESTY.md` | `wc -l` | `799` — one line of headroom; §9 moves at Task 1 |
| `typescript/src/transform.mjs` | `wc -l` | `765` — the task-boundary code moves to `tasks.mjs` at Task 1; the focus splices live in a new `probe.mjs` |
| `docs/TRACE-FORMAT.md` | `wc -l` | `781` — three sentences, nothing more |
| `tests/test_ts_ingest_meta.py` | `wc -l` | `777` — the converter's focus tests go to a new `tests/test_ts_ingest_focus.py` |
| `src/sensorium/query/flow_cmd.py` | `wc -l` | `742` — about 30 lines to come; if it would cross, the serial branch goes to `flow_values.py` |
| `typescript/src/rt.mjs` | `wc -l` | `705` — about 45 lines to come |
| `docs/CARRIED-DEBT.md` | `wc -l` | `530` — appended to |

**The version tokens.** `sensorium-ts` becomes `0.3.0` at Task 2. Every
`0.2.0` in the plan's list, counted as it stands, so that the bump can be
checked as a count rather than as a claim.

| Item | Command | Value |
|---|---|---|
| `0.2.0` tokens in the plan's named set | `grep -rc "0\.2\.0"` over `typescript/package.json`, `typescript/package-lock.json`, `typescript/src/index.mjs`, `typescript/test/rt.test.mjs`, `src/sensorium/ts/wrapper.py`, `tests/test_ts_wrapper.py`, `tests/test_ts_live.py`, `tests/ts_traces.py`, `docs/trace-format/vectors/v30…v34*.json` and the four `corpus/typescript/*/questions.yaml` | **25** — `package-lock.json` 2, `package.json` 1, `index.mjs` 1, `rt.test.mjs` 1, `wrapper.py` 1, `test_ts_wrapper.py` 1, `test_ts_live.py` 1, `ts_traces.py` 3, v30 2, v31 2, v33 2, v34 2, `object_refused` 2, `silent_swallow` 2, `pass_vs_fail` 1, `watch_refused` 1 |
| the vector that must NOT move | `grep -n recorder docs/trace-format/vectors/v32-err-flow-typescript-capability-refusal.json` | `"recorder": "sensorium-ts 0.1.1"` — v32 is the 0.1.x capability refusal and carries no `0.2.0` token at all. The plan's Global Constraints say "vectors v30–v34's `recorder`"; the measured set is **v30, v31, v33, v34**, and this pin is the measured one |
| Python version | `.venv/bin/python -c "…version('sensorium')"` | `0.11.0` → `0.12.0` at Task 10; `tests/test_release_tokens.py` binds `pyproject` to the CHANGELOG's newest header |

**The E7 needle list.** H8 runs `e7_report.py` with `E7_NEEDLES=rung2` over
every transcript of §1.5's thirteen reads. The population an endpoint counts
over is part of the instrument, so it is committed rather than passed on a
command line, and it is pinned here as it stands at T0.

| Item | Command | Value |
|---|---|---|
| the list | `grep -n "NEEDLES_RUNG2" -A 11 typescript/acceptance/e7_report.py` | nine needles — `oid`, `chain`, `Err` word-bounded and case-sensitive; `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own` substring and case-insensitive |
| the selector | `grep -n "^LISTS" typescript/acceptance/e7_report.py` | `LISTS = {"rung2": NEEDLES_RUNG2, "rung3": NEEDLES_RUNG2}` — `rung2` is the list H8 names; anything else falls back to rung 1's |
| what it means for this rung | — | `oid` is one of the nine, and §5.1 mints an `oid` on the wire. A reader that PRINTS the word would be a hit: the identity a reader shows is a serial, and `oid` is the runtime's own key. This is a pre-registered risk, not a threshold to move later |

### 2.3 Instrument changes made before any endpoint ran

**None yet.** Every entry here carries the commit that made it and is
decided BEFORE the endpoint it touches has read a number; a defect found
after a number is read is a finding in §4 and not an entry here.

## 3. Results

**Not measured (rung 4 pending).**

## 4. Decisions

**Not measured (rung 4 pending).**

## 5. What the rung ships

**Not measured (rung 4 pending).**
