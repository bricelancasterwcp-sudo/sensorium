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

**What the one session left behind**, measured at T9 — after the six arms
and before any read — and, for the two rows that say so, after the reads.
Box paths appear here for the same reason they appear in the table above: a
pin without its location is not a pin, and §2's tables are the only place
this record sanctions one.

| Item | Command | Value |
|---|---|---|
| `<store>`, created empty | `ls -A <store>` at T0 | **absent**, then created by `e12.sh`, which refuses a store that exists and is not empty — §1 records into a store that is EMPTY at T0, and a session that recorded into somebody else's traces would hash a set this rung never wrote |
| the six arms | `arms.jsonl` | U1 F1 U2 F2 U3 F3, interleaved, each behind the load guard (1-minute load `0.72`, `0.72`, `0.72`, `0.72`, `0.83`, `0.83`, all under 4.0), all six exit `0`, all six printing ` Test Files  1 passed (1)` and `      Tests  26 passed (26)` |
| the traces | `ls <store>/traces/*.db` | **6** — one container per arm; `du -sh <store>` `1.3M` |
| the hash list | `(cd <store> && sha256sum traces/*.db spool/*/*.jsonl invocations.jsonl)` → `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-tracehashes.txt` | **13 lines** — 6 `traces/*.db`, 6 `spool/<invocation>/*.jsonl`, 1 `invocations.jsonl`; every path relative to the store root, and `grep -c "/mnt/\|/home/"` over the file is `0` |
| the hash list's own sha256 | `sha256sum <the hash list>` | `32a5612111e981b461061efd32f0d6d1d4dc1da561fc34ae6701f26b336deafc` |
| the hash list verifies, after every read | `cd <store> && sha256sum -c <the hash list>` | **12 of 13 OK.** The thirteenth is `invocations.jsonl`, the one entry of the hashed set the reads themselves append to; it is checked as an APPEND instead — the journal's first 6 lines still hash to the listed `3a619cbb77356d191489828beaeb70f90cdc1a053e682cf29e1296a39df8221c`, which is what "appended, not rewritten" means. No trace and no spool moved: reading a trace does not write to it |
| the journal's delta | `wc -l <store>/invocations.jsonl` at T9 and after the reads | **6 → 19**, a delta of **13** — one line per read command in §1.5's list, whose length the assembler reads from this record and never from a literal |
| lens manifest, before the arms | `cd <lens> && sha256sum -c /mnt/extra/sensorium-s5/manifest-after.txt` | exit `0`, **748 OK, 0 FAILED** |
| lens manifest, after the arms | the same command, the arms the last thing to have touched the lens | exit `0`, **748 OK, 0 FAILED** — identical |
| the manifest file | `sha256sum /mnt/extra/sensorium-s5/manifest-after.txt` | `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`, 748 lines — the same sha the table above pins for `manifest-rung1-before.txt`: two names, one file's content, so the lens the hand count was read on is the lens the arms recorded |
| the recorder, read from a BOOT | `head -1 <store>/spool/<invocation>/*.jsonl` | `"version": "0.3.0"`, `"tier": "call"` on all six. The three U spools declare `{err_flow, object_identity}` and the three F spools `{err_flow, object_identity, line, locals}` — **`sensorium-ts 0.3.0`**, the version §2's last row says Task 2 makes it, and the split every arm's capability line is read from |
| the binary every instrument ran | `bin.sh`, `lens.sensorium_bin()` | `<repo>/.venv/bin/sensorium` — the branch's own, resolved two parents above `typescript/acceptance/` and refused if its `realpath` leaves the worktree. The global tool was never reinstalled from this worktree |

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


**The instrument census.** Six new scripts, all in one commit (`68b7eb9`),
all written and dry-run on `typescript/probes` before the lens was opened.
Every one sources `bin.sh` or `lens.sensorium_bin()`, every cell is
`{value, n, dropped}` through `lens.py`, and only the assembler stamps a
lens label. `tests/test_acceptance_scripts.py` (E-branch) enumerates the
scripts from `git ls-files`, so the census below is the tracked set and not
a list this record maintains by hand.

| Instrument | lines | what it reads, and what it writes |
|---|---|---|
| `typescript/acceptance/e12.sh` | `342` | the ONE session: manifest, U1 F1 U2 F2 U3 F3 under the load guard, one timed `node resolve.mjs`, manifest again, the hash list → `arms.jsonl`, `resolve.json`, `e12.json` |
| `typescript/acceptance/e12_report.py` | `676` | §1.5's thirteen commands against `<store>`, transcripts raw and redacted → `e12-reads.json` (cells H1, H2, H4, H5, H6) |
| `typescript/acceptance/e12_h3.py` | `189` | F1's first `parseDiceGroups` activation against the hand count → `e12-h3.json` |
| `typescript/acceptance/e12_cost.py` | `100` | `arms.jsonl`'s walls → `e12-h7.json` |
| `typescript/acceptance/e12_h8.sh` | `183` | the corpus, four suites, the vectors and `e7_report.py` over every saved transcript → `e12-h8.json` |
| `typescript/acceptance/assemble_rung4.py` | `259` | every cell, the hashed set, the journal's delta and the record's own sha → `…-focus.results.json` |
| `typescript/acceptance/e_fences.py` | `165` | reused, with R12's sentence and the hoist → `e-legacy.json`, `e-branch.json` |
| `typescript/acceptance/e7_report.py` | `166` | reused unchanged, once per transcript, `E7_NEEDLES=rung2` |

**The read-command list, as executed.** §1.5's thirteen, each run once,
`U1` = `20260912-015128-7bc2b2` and `F1` = `20260912-015130-42f691`; the
transcripts are committed, redacted, under
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/`.
Commands 09 and 10 are §1.5's tenth and ninth: §1.4 makes the `grep` the
lookup that produces the flow's `e<id>`, so the grep runs at its lookup
position (§2.3, entry 1). The set and the count are §1.5's.

| # | command, as §1.5 writes it | exit | transcript |
|---|---|---|---|
| 01 | `info U1` | 0 | `01-info-U1.txt` |
| 02 | `info F1` | 0 | `02-info-F1.txt` |
| 03 | `watch U1 --at parseDiceGroups --expr groups == 0` | 3 | `03-watch-U1-at-parseDiceGroups-expr-groups-0.txt` |
| 04 | `watch F1 --at parseDiceGroups --expr sides == 20` | 0 | `04-watch-F1-at-parseDiceGroups-expr-sides-20.txt` |
| 05 | `watch F1 --at parseDiceGroups --expr count == 1` | 0 | `05-watch-F1-at-parseDiceGroups-expr-count-1.txt` |
| 06 | `watch F1 --at parseDiceGroups --expr m == null` | 0 | `06-watch-F1-at-parseDiceGroups-expr-m-null.txt` |
| 07 | `flow F1 --value 20` | 0 | `07-flow-F1-value-20.txt` |
| 08 | `flow F1 --value "'1d20'"` | 0 | `08-flow-F1-value-1d20.txt` |
| 09 | `grep F1 dice --kind LINE` | 0 | `09-grep-F1-dice-kind-LINE.txt` |
| 10 | `flow F1 --object e367:dice` | 0 | `10-flow-F1-object-e367-dice.txt` |
| 11 | `grep F1 parseDiceGroups --kind CALL` | 0 | `11-grep-F1-parseDiceGroups-kind-CALL.txt` |
| 12 | `frame F1 --fn parseDiceGroups` | 0 | `12-frame-F1-fn-parseDiceGroups.txt` |
| 13 | `tree F1` | 0 | `13-tree-F1.txt` |

### 2.3 Instrument changes made before any endpoint ran

**Eleven, each with the commit that carried it.** Every one was decided and
committed **before** the endpoint it touches had read a number; a defect
found after a number is read is a finding in §4 and not an entry here. Ten
of the eleven are instrument changes carried by `68b7eb9`, the one commit
that carries this rung's instruments, written and dry-run on
`typescript/probes` before the lens was opened. Entry 3 is the exception and
says so in its own column: it is a NOTE, decided at `68b7eb9`, about two
diffs earlier tasks made.

| # | what changed | commit | why |
|---|---|---|---|
| 1 | **§1.5's ninth and tenth commands run in the other order**: `grep F1 dice --kind LINE` immediately before `flow F1 --object e<id>:dice` | `68b7eb9` | §1.5 lists the flow ninth and the grep tenth, and §1.4 makes the grep the LOOKUP that produces `e<id>` — the ninth command's argument is the tenth command's answer, so both orders cannot be run. The SET and the COUNT are §1.5's, and the count is what the journal's pre-registered delta is about; §1.5's own prose already calls that grep "§1.4's lookup". `e12_report.py`'s docstring and `e12-reads.json`'s `order_change` both name the swap |
| 2 | **The fence glob carries exactly ONE changed line, named in advance** — `tests/test_exceptions_rust_grouping.py:697`, the plan-mandated `site=site` after `Shape.site` became required (ruling R12) | `68b7eb9` | that file is inside `tests/test_exceptions_rust*.py`, so E-legacy's first claim reads one changed line and not zero. R12 names line 696; the measured line is **697** and this pin is the measured one. `e_fences.py`'s docstring names it |
| 3 | **Two further diffs the legacy reading names** (ruling R35): `docs/trace-format/vectors/v23-lang-typescript-prose.json`'s re-pin, forced by the `timeline_hint` rewrite (`frame` now names `sensorium ts run --focus <file>:<qualname>` where it used to say per-line capture is rung 3's), and `corpus/typescript/object_refused`'s rewrite into `object_identity` | a NOTE, at `68b7eb9`, on `3895a51` and `f0606b5`/`f501545` | this row is the only one in this table that is not a change `68b7eb9` carried: the two diffs are EARLIER tasks' — v23's re-pin at `3895a51` (Task 6's vectors), the corpus case's answer at `f0606b5` and its rename into `object_identity` at `f501545` (Task 8's) — and what `68b7eb9` carries is the decision to name them here before E-legacy was read. Neither is inside the fence, so neither moves E-legacy; both are the kind of change a reader of "did nothing else move?" should be handed rather than left to discover |
| 4 | `existing(FENCED_TESTS)` hoisted above the `git diff` in `e_fences.py`'s `legacy()` | `68b7eb9` | a fence pattern matching no file refuses the whole run, and refusing AFTER a diff has been taken leaves a reading nobody can use beside a refusal nobody asked for (Task 1's minor) |
| 5 | **H3's N is read from the hand-count FILE's LAST line** (`N = 9`), and `e12_h3.py` refuses when that line and the table's row count disagree | `68b7eb9` | the table and the sentence are two statements of one prediction and §1 calls the last line the gate. A prediction that contradicts itself has not been made, and nothing is measured against it (Task 0's minor) |
| 6 | **Each `--expr` is passed as ONE argv element**: the reader takes the rest of §1.5's line after `--expr ` | `68b7eb9` | §1.5 writes the predicate unquoted and last (`--expr groups == 0`) and says each `--expr` is one shell argument; `shlex.split` alone would hand `watch` three arguments and a usage error (Task 0's minor) |
| 7 | **The journal is verified as an APPEND, not as an unchanged file** | `68b7eb9` | the hash list is taken after the arms and BEFORE any read, as §1's plan block fixes, so the reads themselves append to `invocations.jsonl` and that one entry of the hashed set must fail a plain `sha256sum -c`. `assemble_rung4.py` checks the journal's first `<T9 line count>` lines against the listed hash — an append leaves them untouched, a rewrite does not — and its growth against §1.5's length, read from the record and never typed (ruling R6) |
| 8 | **`E12_RECORD`, a dry-run-only override of which record §1 is read from, with an assembler guard** | `68b7eb9` | every instrument was rehearsed end to end on `typescript/probes` against a scratch §1 shaped like this one, which is the only way the lookup, the thirteen reads and the journal arithmetic could be checked before the lens was opened. `e12-reads.json` records which file was read AND its sha256, and `assemble_rung4.py` REFUSES to assemble reads taken against a §1 that is not this record's |
| 9 | **An arm's run id is the container whose `run:` line names the subject file**, not the first line printed | `68b7eb9` | one `vitest run` of one file records one container here, but position is not the fact, and a second container would otherwise be silently dropped. Every `run:` line is carried in `arms.jsonl` and the id is `null` — a dropped run, not a guess — when more than one names the subject |
| 10 | **H5's gated population is the three qualnames §1 names, exactly** | `68b7eb9` | `--focus`'s prefix rule also selects a function-like nested inside a named one (`X.<anonymous>`), and §1.3's hand analysis enumerated the deltas of the three functions' OWN statements and reasoned about no other. A nested row is reported in `elsewhere_not_gated`, never gated: widening the gate past what the prediction covered would manufacture a STOP the prediction never risked |
| 11 | **`cargo test --workspace` runs from `rust/`** | `68b7eb9` | the workspace manifest is `rust/Cargo.toml`; from the repository root the command exits 101 with "could not find `Cargo.toml`". The dry run on the probe project read that 101 before any number of H8 was read, which is what a dry run is for |

## 3. Results

**Status: DONE-WITH-STOP.** Eight endpoints, every one read once, in the
order Task 9 fixes: the two fences, then the ONE session, then the thirteen
reads, then H3, H7, H8 and the assembler. Three endpoints STOPped — H2, H4
and H5 — so the word this rung ships is `DONE-WITH-STOP` and not `DONE`.
Nothing was re-run, no focus was narrowed and no threshold moved after a
number was read; §4 says of each STOP what the reading actually showed, and
two of the three are findings about the INSTRUMENT that read the endpoint
rather than about the recorder it was pointed at — which is a difference §4
states and §3 does not use to soften a word.

The numbers below are
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.results.json`,
assembled by `typescript/acceptance/assemble_rung4.py`, **with one stated
exception**: H8's four SUITE AGGREGATES — cargo's 773/0/23, node's 521/0,
the probes' 12 spools and 146 checks, and cargo's count of 44 `test result`
sections — are read from the session's own suite logs under `<out>/h8/logs`,
which are NOT committed. The H8 cell commits each suite's exit status and
the last three lines of its log and nothing more (`e12_h8.sh`'s `suite_in`
and its `tail`), so those four aggregates are traceable to a log this record
names per suite and not to a cell. Every other number in this section, H8's
corpus counts, its pytest counts and its needle total included, is a cell in
that file. The H8 row and §4.8 say so again where they use them, because a
figure whose source a reader has to infer is a figure this record has not
actually shown them. Every cell is
`{value, n, lens, dropped}` plus `recorder` / `recorder_rev` /
`recorder_basis`; `recorder_basis` reads `own` on all eight, because every
instrument recorded its own. The recorder is **`sensorium 0.11.0 /
sensorium-ts 0.3.0` on `feat/s5-rung4` @
`68b7eb942b445c954881fcfbafabf63e448b0c34`** — the Python version does not
move in this task: the bump to `0.12.0` is Task 10's, and a cell claiming it
here would name a recorder that did not take the reading.

The assembler's three verifications all held before a single number was
published: the reads were taken against THIS record (sha
`da7d3ce6a4ad06060da583601576099d70c1c8fce0468167f98ca95e17cd8f2c`); the
hashed set verified 12 of 13 with the thirteenth, `invocations.jsonl`,
appended and not rewritten; and the journal grew by exactly 13 lines, the
length of §1.5's list read from this file.

That first sha is of the record FILE as it stood at assembly time — §1 and
§2 written, §3, §4 and §5 still the pre-registration's placeholder — so the
check is a ONE-SHOT provenance check and not a standing one: writing these
three sections moves the file's sha, and re-running `assemble_rung4.py`
against this record now refuses. That is the guard doing what it was built
for (it refused the dry run's scratch §1 the same way) and it is also its
limit, stated here rather than discovered by the next reader who runs the
assembler. The `verification` block of the results file carries both shas as
they were; a standing version of the check would hash §1's byte range alone,
which is what `tests/test_acceptance_s5_rung4_lock.py` already does.

| # | endpoint | cell (`value` of `n`) | the rule | word |
|---|---|---|---|---|
| H1 | does an unfocused run stay unfocused? | **4 of 4** — U1 declares `line: false` and `locals: false`; `SELECT count(*) … kind='LINE'` = **0**; `watch U1 --at parseDiceGroups --expr groups == 0` printed §1's sentence byte-for-byte and exited **3**. Second reading: the version token inside that sentence, `sensorium-ts 0.3.0`, IS the trace's own `recorder` | both readings as §1 writes them → PASS | **PASS** |
| H2 | does a focus resolve and run? | **3 of 4** — the resolver named **six** sites where §1 pre-commits three; F1's `Test Files  1 passed (1)` and `Tests  26 passed (26)` equal U1's, both arms exit 0; `grep F1 parseDiceGroups --kind CALL` printed `e10 CALL    parseDiceGroups(formula='1d20')` first | exactly three sites named, the counts unmoved → PASS; a focused file that fails to load, or a suite whose counts move, is a STOP | **STOP** |
| H3 | one LINE per completed statement? | **4 of 4** — the first `parseDiceGroups` activation in F1 (`f6`, `args: formula='1d20'`) carries **9** LINE rows; their `line` values in order are **69, 70, 71, 72, 73, 74, 76, 75, 72**; every row's delta names and every row's `unbound` names equal the hand count's, in order. `diff_of_lines` is empty | **N = 9 → PASS**; any other count a STOP with the diff of lines | **PASS** |
| H4 | does `watch` answer? | **2 of 3** — W1 `sides == 20` SATISFIED exit 0, W3 `m == null` SATISFIED exit 0, W2 `count == 1` SATISFIED exit 0 *and* two HIT rows at line 72, which the cell reads as W2's extra clause failing. No verdict disagreed with its exit | all three triples as §1.2 predicts → PASS; a verdict/exit disagreement is a finding, reported | **STOP** |
| H5 | does `flow --value` see it? | **2 of 3** — S1 (`20`, `sides`, `diceQueue.ts:74`) found, 9 LINE sightings of it; S2 (`'1d20'`, `formula`, the CALL's `arg formula`) **not seen by the cell**, though the transcript prints it; no unpredicted triple in the gated population | both sightings found and no third triple in the population → PASS; sightings elsewhere reported, not gated | **STOP** |
| H6 | is identity exact? | **4 of 4** — §1.4's lookup found `e367` (the fourth `dice` LINE row of `forcedDiceFromSource` at L138, the first whose activation `buildDiceQueueEntry` called); `flow F1 --object e367:dice` printed **`sightings: 2 event(s), 2 capture(s)`** at `diceQueue.ts:138` and `diceQueue.ts:202`, **one serial** (`#64` covers both), `continuity: exact (serial identity)`, and both captures' `type` is `Array` | exactly two sightings, one serial, continuity exact, both `Array` → PASS | **PASS** |
| H7 | what does it cost? | unfocused median **0.7955 s** (n=3, walls 1.1162 / 0.7955 / 0.7874), focused median **1.8946 s** (n=3, walls 1.8946 / 1.9147 / 1.8899), ratio **×2.3816**; the resolver **1.132 s** over 830 files scanned; 0 runs dropped; every arm guarded at a 1-minute load of 0.72–0.83 | reported, not gated | **reported** |
| H8 | did nothing else move? | **6 of 6** — five suite exits all `0` and the needle total `0`, which is what the cell holds. From the cell: corpus `105 cases, 220 questions, 0 failures, 0 error(s)`; `pytest -q` `4090 passed, 33 skipped`; `e7_report.py` with `E7_NEEDLES=rung2` over all **13** transcripts, **0** occurrences of the nine needles. From the session's logs, named and not committed: `cargo test --workspace` 44 `test result: ok` sections summing to **773 passed, 0 failed, 23 ignored** (`<out>/h8/logs/cargo.log`; the cell's committed tail is the LAST of those 44 sections, `sensorium_transform`'s doc-tests, `test result: ok. 0 passed; 0 failed; 14 ignored` — one section, not the total, and not a contradiction of it); `npm --prefix typescript test` **pass 521, fail 0** (`npm-typescript.log`); `npm --prefix typescript/probes run probe` `ok: true`, 12 spools, **146 checks, 0 failures** (`npm-probes.log`) | every corpus case equal, the suites green, E7's needles at 0 → else STOP | **PASS** |

**Reported beside H8, gating nothing** (the two fences, read FIRST, before
the session opened the store):

| endpoint | cell | reading |
|---|---|---|
| E-legacy | **1 of 2** | `git diff aea6b47..HEAD --stat` over the fenced paths prints ` tests/test_exceptions_rust_grouping.py \| 2 +-` — the ONE line §2.3's entry 2 named in advance. The fenced tests and the Rust key's tuple equality are green: `118 passed` |
| E-branch | **1 of 1** | `tests/test_acceptance_scripts.py` green |

## 4. Decisions

### 4.1 H1 — the unfocused arm stayed unfocused, and said so in its own words

U1's `capabilities` map reads `line: false, locals: false` (the converter's
floor, `sensorium.ts.build.CAPABILITIES`, unridden because the U arms' BOOT
declares only `{err_flow, object_identity}` — §2.1's BOOT row). Its
`events` table holds **0** rows of kind `LINE`. And `watch` refused with the
sentence §1 pre-committed, byte for byte:

```
REFUSED: watch needs line, which recorder sensorium-ts 0.3.0 declares it does not produce (capabilities.line: false); nothing was checked
```

at exit **3**. The second reading is the one that makes the sentence a
measurement rather than a string two files happen to share: the version
token inside it (`sensorium-ts 0.3.0`) was compared against the TRACE's own
`recorder` value, read from the same database, and they are equal. The
refusal names the recorder that recorded, not the recorder that is installed.

### 4.2 H2 — a spec names a function AND every function-like nested in it

The suite half held exactly: F1 and U1 both printed ` Test Files  1 passed
(1)` and `      Tests  26 passed (26)`, both exited 0, and the focused CALL
printed as §1 writes it — `e10 CALL    parseDiceGroups(formula='1d20')`,
first row of `grep F1 parseDiceGroups --kind CALL`. Neither of the two
failures §1's H2 sentence names as STOPs occurred: no focused file failed to
load, and no count moved.

The site count is what did not hold. `node resolve.mjs` on the three specs
named **six**:

```
src/lib/diceQueue.ts:parseDiceGroups
src/lib/diceQueue.ts:forcedDiceFromSource
src/lib/diceQueue.ts:forcedDiceFromSource.<anonymous>
src/lib/diceQueue.ts:buildDiceQueueEntry
src/lib/diceQueue.ts:buildDiceQueueEntry.<anonymous>
src/lib/diceQueue.ts:buildDiceQueueEntry.<anonymous>
```

This is `focus.mjs`'s prefix rule working as designed and as documented —
*"`Fog` selects `Fog.compute`"* — applied to function-likes the
pre-registration did not enumerate: the arrow in
`groups.reduce((sum, g) => sum + g.count, 0)` inside `forcedDiceFromSource`,
and the two default-parameter arrows of `buildDiceQueueEntry`
(`idFactory = () => crypto.randomUUID()`, `now = () => Date.now()`). §1's
subject paragraph chose "three pure functions … chosen by reading the
source" and predicted three sites; the source it was read from carries three
more function-likes inside those three, and a spec that names a container
selects them. The STOP is on the pre-committed number, and the finding is
that **"how many functions does a spec select" is not answerable from the
names a reader types** — it depends on what is nested inside them, which is
exactly the sort of thing `resolve.mjs` exists to be asked BEFORE a run, and
exactly what it answered.

A second reading fell out of it, R22/R31's, and it is worth more than the
first. `info F1` prints:

```
focus matched: 5 — src/lib/diceQueue.ts:buildDiceQueueEntry, src/lib/diceQueue.ts:buildDiceQueueEntry.<anonymous>, src/lib/diceQueue.ts:forcedDiceFromSource, src/lib/diceQueue.ts:forcedDiceFromSource.<anonymous>, src/lib/diceQueue.ts:parseDiceGroups (6 function(s) focused by the transform)
```

`meta.focus_matched` holds **5** and `meta.functions_focused` **6**, and the
line prints both because they differ. They differ for a reason the design
predicted in the abstract and this lens supplies concretely: `focus_matched`
is a set of `<file>:<qualname>` strings and the two default-parameter arrows
of `buildDiceQueueEntry` share one qualname
(`buildDiceQueueEntry.<anonymous>`), while the transform instrumented both.
R31's parenthetical is the only place a reader is told the two numbers are
not the same number — without it, `focus matched: 5` would have been the
whole story and one instrumented function would have been invisible.

### 4.3 H3 — the hand count was right, row for row

Nine LINE rows, and the diff of lines is empty. `frame F1 --fn
parseDiceGroups` prints the activation whole:

```
f6 diceQueue.ts:parseDiceGroups  [e10..e20]  thread 1  task t1 (parseDiceGroups > parses a single group)  depth 1  closed: return
args: formula='1d20'
timeline:
  e11 LINE    parseDiceGroups L69  groups=[]
  e12 LINE    parseDiceGroups L70
  e13 LINE    parseDiceGroups L71  m=undefined
  e14 LINE    parseDiceGroups L72  m=[ '1d20', '1', '20', index: 0, input: '1d20', groups: undefined ]
  e15 LINE    parseDiceGroups L73  count=1
  e16 LINE    parseDiceGroups L74  sides=20
  e17 LINE    parseDiceGroups L76
  e18 LINE    parseDiceGroups L75
  e19 LINE    parseDiceGroups L72  m=null  unbound:count,sides
return: [ { count: 1, sides: 20 } ]
```

Every clause of §1.1 is in that block. **N = 9.** The `line` values are 69,
70, 71, 72, 73, 74, 76, 75, 72 — line 72 twice (the head row at entry and
the `while` statement's own completion row), lines 77, 78 and 80 not at all,
and 76 before 75 because the `if` completes after its body. Three rows carry
empty deltas (70, the place write; 76, the expression statement; 75, the
`if` completing). Exactly one row carries `unbound`, and it is the `while`'s
own: `unbound:count,sides`. `m` is `undefined` at 71, a match array at the
head row and `null` at the completion row — plan P1(a)'s reading, which the
per-entry rule alone would have left unreported.

This is the endpoint the rung exists for, and it is the one the pressure to
fudge was pre-registered against (§1's opening, and the hand count's own
sha256 as §1's last line, recomputed by the lock test). It needed no fudging.

### 4.4 H4 — two triples as predicted, and one clause the instrument read too strongly

All three verdicts and all three exits are §1.2's: `SATISFIED` / 0 three
times, and no verdict disagreed with its status. W1 hit at 31 of 64
evaluable sites, W2 at 52 of 77, W3 at 15 of 120; the not-captured tallies
are 101, 88 and 45 of 165 recorded sites, reported and not predicted, as
§1.2 says.

W3 is the head-binding reading and it held cleanly: all fifteen of its HITs
are at line 72 carrying `m=null  unbound:count,sides` — the `while`
statement's own completion rows, the row that only exists because plan P1(a)
gives a guarded statement's completion row its head's assignment targets.

W2's extra clause is where the cell reads a miss. §1.2 predicts **"no HIT at
line 72's `while`-completion row"** — the `unbound` reading: `count` dies on
that row, so the predicate cannot be evaluated there. The cell tested "no HIT
at line 72", which is a STRICTLY STRONGER claim, because line 72 carries two
different rows: the completion row AND the head row minted on each entry.
Two HITs came back:

```
HIT   e32 LINE    parseDiceGroups L72  m=[ '2d6', '2', '6', index: 5, input: '1d20+2d6+3', groups: undefined ]   state: count=1
HIT   e86 LINE    parseDiceGroups L72  m=[ '2d6', '2', '6', index: 5, input: '1d20+2d6', groups: undefined ]   state: count=1
```

Both carry `m=[ … ]` and no `unbound`: they are HEAD rows, the synthetic
first row of a second loop entry, at which `count` is still 1 from the
previous iteration's fold. Not one completion row (`m=null
unbound:count,sides`) appears among W2's hits. §1.2's clause, read as §1.2
writes it, held; the cell's stronger reading of it did not, and the cell's
number stands.

**This is an instrument defect found after a number was read, which makes it
a finding and not a fix** (§1's own rule, and the reason it is here in §4
rather than in §2.3). The defect is one line of `e12_report.py`: `h4`
compares a HIT's `line` against §1.2's, and a `line` alone cannot tell a
`while`'s head row from its completion row. The row's own payload can — the
completion row is the one with `unbound` — and the fix, if a later rung wants
one, is to read the clause off `unbound` rather than off the line number.
Recorded as carried debt; the number is not re-measured.

### 4.5 H5 — S1 found, S2 printed but not parsed

`flow F1 --value 20` sights `sides` at `diceQueue.ts:74` nine times inside
`parseDiceGroups`, which is S1, and the population held no other triple.
Its tenth sighting is outside the gate and is reported: `e288 RETURN
buildForcedNotation.<anonymous> -> 20   [return]`. §1.3's own ungated hand
reading — "the file drives fifteen `parseDiceGroups` activations, exactly
one of them with `formula === '1d20'`" — is measured exactly: `tree F1`
prints 15 `parseDiceGroups(formula=…)` activations and exactly one of them
`parseDiceGroups(formula='1d20')`.

S2's sighting is in the trace and in the committed transcript:

```
$ sensorium flow F1 --value "'1d20'"
flow of '1d20' (str) in 20260912-015130-42f691
  captured-value equality, not true dataflow analysis: the trace records values, not the edges between them
  e10 CALL    parseDiceGroups(formula='1d20')   [arg formula]
  e278 RETURN  buildForcedNotation.<anonymous> -> '1d20'   [return]
  e286 RETURN  buildForcedNotation.<anonymous> -> '1d20'   [return]
  e304 RETURN  buildForcedNotation.<anonymous> -> '1d20'   [return]
  e320 RETURN  buildForcedNotation.<anonymous> -> '1d20'   [return]
sightings: 5 event(s), 5 capture(s)
```

`e10 CALL    parseDiceGroups(formula='1d20')   [arg formula]` is the
(literal, name, activation) triple §1.3 names, on the `parseDiceGroups('1d20')`
CALL, and the four `RETURN` rows are exactly the "sightings elsewhere in the
trace (RETURN values, other files)" §1.3 says are reported and not gated.
The cell nevertheless read `S2 found: false`, for two reasons, both in
`e12_report.py`'s row parser and both instrument defects found AFTER the
number:

1. **A CALL row's qualname is not a bare qualname.** `rows_of` takes the
   token after the kind as the function's name; on a CALL, `flow` prints
   `parseDiceGroups(formula='1d20')` there, so the population test
   `qualname ∈ {the three}` failed on a row that IS one of the three.
2. **A printed CALL row carries no `L<line>`.** §1.3's `line` column for S2
   is `diceQueue.ts:68`, the function's definition line, which the trace
   holds on the code object and `flow` does not print for a CALL. Even with
   (1) fixed, the row would not have matched on the line, and the reading
   would have had to come off the trace rather than off the printed row.

The same parser has a third, smaller gap that this record must own because
it makes a REPORTED field incomplete rather than a gated one wrong: a
`RETURN` row (`e288 RETURN  buildForcedNotation.<anonymous> -> 20
[return]`) has one space before its `->` where the parser requires two, so
`elsewhere_not_gated` in the H5 cell lists one row where the two transcripts
between them print five. The counts the transcripts print — `sightings: 10`
and `sightings: 5` — are the honest totals and are quoted above and in the
committed transcripts; the cell's `elsewhere_not_gated` list is not.

None of the three touches H6, whose two sightings are both LINE rows and
whose independent check is the printed `sightings: 2 event(s), 2
capture(s)`.

### 4.6 H6 — the identity is exact, and §1.4's correction was the right one

The lookup ran as §1.4 writes it. `grep F1 dice --kind LINE` printed seven
rows at `forcedDiceFromSource L138`; the trace's frame parentage says the
first three were called from `<anonymous>.<anonymous>` (the test callbacks
of the `forcedDiceFromSource` describe block) and the last four from
`buildDiceQueueEntry`. The first row `buildDiceQueueEntry` called is
**`e367`** — the FOURTH `dice` LINE row of `forcedDiceFromSource` in F1,
which is precisely what §1.4's "reported, not gated" sentence predicted by
hand.

`flow F1 --object e367:dice`:

```
flow of object #64 (Array) in 20260912-015130-42f691
  identity is a per-object serial minted once and never reused: every sighting is the same object
  e367 LINE    forcedDiceFromSource L138  dice=[]   [local dice]
  e378 LINE    buildDiceQueueEntry L202  dice=[ { sides: 20, value: 17 } ], skippedCount=0   [local dice]
sightings: 2 event(s), 2 capture(s)
continuity: exact (serial identity)
```

Exactly two sightings, at `diceQueue.ts:138` and `diceQueue.ts:202`; one
serial (`#64` is the oid of the capture at both events, read from the two
payloads); `continuity: exact (serial identity)`; and both captures' `type`
is `Array`. The array is EMPTY at 138 and holds one die at 202 — the same
object, two contents, which is the whole of what a serial buys over a
rendered value.

§1.4's amendment earns its place here. The plain first-row reading — "the
first LINE row of `forcedDiceFromSource` carrying `dice`" — would have
picked `e101`, whose activation the test file called directly; that array is
sighted once, and H6 would have STOPped on a correct recorder. The
correction was made at T0, before any rung-4 code existed, and the measured
parentage (`e101`, `e151`, `e237` → `<anonymous>.<anonymous>`; `e367`,
`e420`, `e463`, `e511` → `buildDiceQueueEntry`) is its proof.

### 4.7 H7 — what the focus tier cost here

Reported, not gated. One test file, 26 tests, three runs each way,
interleaved, every run guarded at a 1-minute load between 0.72 and 0.83:

| arm | walls (s) | median (s) |
|---|---|---|
| U, unfocused | 1.1162, 0.7955, 0.7874 | **0.7955** |
| F, focused on three specs | 1.8946, 1.9147, 1.8899 | **1.8946** |

**×2.3816** on the median, 0 runs dropped. Two readings sit beside it and
neither is a threshold. The U arm's first wall is its slowest by 40% and the
F arm's three are within 25 ms of each other — a cold-start cost that the
focused arm paid on the U side of the interleave. And the two arms recorded
the same call tier — `CALL 117  RETURN 117` in both — with the F arm adding
**295 LINE rows** on top (234 events against 529, `info U1` against
`info F1`), so what the wall bought is a per-statement record of six
functions and not a slower run of the same recording.

The resolver ran once, timed by `e12.sh` because `Resolution.wall` is not
persisted (Task 5): **1.132 s** to walk and parse 830 files under the lens
root, 0 unparsable. That is paid once per invocation, before the harness
starts, and it is what turns a mistyped spec into a refusal in a second
rather than into a suite that recorded the wrong thing.

### 4.8 H8 and the two fences — nothing else moved

Six clauses, all held. The corpus ran all three directories with
`--require-driver`: **105 cases, 220 questions, 0 failures, 0 errors**, the
ten new focus cases included. `pytest -q`: **4090 passed, 33 skipped**.
`cargo test --workspace` from `rust/`: 44 `test result: ok` sections summing
to **773 passed, 0 failed, 23 ignored**. `npm --prefix typescript test`:
**521 passed, 0 failed**. `npm --prefix typescript/probes run probe`:
checker `ok: true`, 12 spools, **146 checks, 0 failures**. And
`e7_report.py` with `E7_NEEDLES=rung2` over all **13** committed
transcripts: **0** occurrences of the nine needles, over 398 lines of
transcript.

**Where each of those figures comes from, because they do not all come from
the same place.** The H8 cell holds, per suite, an exit status and the last
three lines of that suite's log, and nothing else (`e12_h8.sh`'s `suite_in`
writes `<out>/h8/logs/<label>.log` and the cell's `tail` takes three lines
off it). So the corpus counts, the pytest counts and the needle total above
ARE cells — they are the last line of their logs, or `e7_report.py`'s own
`value` — and the four aggregates are not: cargo's **773 passed, 0 failed,
23 ignored** and its **44** sections are an `awk` sum over every `test
result:` line of `<out>/h8/logs/cargo.log`, node's **521 passed, 0 failed**
is the `ℹ pass` / `ℹ fail` block of `npm-typescript.log`, and the probes'
**12 spools, 146 checks, 0 failures** is the checker's JSON at the end of
`npm-probes.log`. Those three logs are session artefacts and are not
committed; the exits that gate the clause are.

One of those numbers needs a sentence of its own, because the committed cell
appears to contradict it. Cargo's tail in the results file reads `test
result: ok. 0 passed; 0 failed; 14 ignored` — that is the LAST of the 44
`test result:` sections `cargo test --workspace` prints, `sensorium_
transform`'s doc-tests, and 44 is one section per test target of this
workspace with the doc-test sections among them. The **773** above is the
`awk` sum over all 44, not a second reading of that one line. A reader
checking §3 against `…-focus.results.json` will find the 14-ignored section
there and should read it as the tail it is; the sum lives in the log this
paragraph names.

§2.2's pre-registered risk did not fire. `oid` is one of the nine needles,
matched word-bounded and case-sensitively, and §5.1 mints an `oid` on the
wire; the reader prints that number as a SERIAL — `flow of object #64
(Array)`, and the caveat line calls it *"a per-object serial minted once and
never reused"* — and never prints the wire key's NAME. `grep -rnw oid` over
the thirteen committed transcripts returns nothing. The risk was named
before the reading and the reading is 0.

The two fences were read FIRST, before the session opened the store, so that
no fence could fail after a number had been taken. E-legacy is **1 of 2**:
its diff clause reads one changed line, not zero, and the line is the one
§2.3's entry 2 named in advance —
`tests/test_exceptions_rust_grouping.py:697`, the `site=site` the plan's own
`Shape.site` requirement forces on a fixture inside the fence glob. Its test
clause is green (`118 passed`, the fenced tests plus the Rust key's tuple
equality). E-branch is **1 of 1**. Two further diffs are named rather than
left to be discovered, neither inside the fence (§2.3, entry 3): v23's
re-pin, forced by the `timeline_hint` rewrite, and `object_refused`'s
rewrite into `object_identity`.

## 5. What the rung ships

**`DONE-WITH-STOP`.**

**What is established.** A TypeScript recorder that records per statement
when it is asked to and does not when it is not, measured on 830 files of a
real frontend rather than on a probe:

* **The transform's grain is the one the design specified, exactly.** H3 is
  the rung's centre and it PASSed on the first reading: nine LINE rows for
  `parseDiceGroups('1d20')`, their lines in the predicted order, their
  deltas and their one `unbound` list row for row against a table written
  before `bindings.mjs`, `probe.mjs`, the runtime's `line` or the
  converter's `_on_line` existed. A head row per entry, the `while`'s own
  completion row carrying `m`'s last write, `count` and `sides` dying on it,
  the `if` completing after its body, no row for `return`, no row for the
  guard that failed. Nine predictions, nine hits, empty diff.
* **The tier is opt-in and says so.** H1: an unfocused arm declares
  `line: false` / `locals: false`, writes zero LINE rows, and `watch`
  refuses it in a sentence that names the recorder the TRACE carries at exit
  3 — absence of the record reported as the recorder's declaration, not as a
  fact about the program.
* **Identity is exact and the reader shows it as a serial.** H6: two
  sightings of one array across two functions, one serial, `continuity:
  exact (serial identity)`, both `Array` — empty at `diceQueue.ts:138` where
  it is created and holding one die at `diceQueue.ts:202` where it is
  destructured, which is the same object under two renderings and is exactly
  what a serial buys over a printed value. And the wire key's NAME never
  reaches a printed line (H8's needle grep for `oid`, 0 over 13
  transcripts).
* **Nothing else moved.** H8: the whole corpus equal (105 cases, 220
  questions, 0 failures — a cell), four suites green by exit status (cells),
  the probes' 146 checks green (read from `<out>/h8/logs/npm-probes.log`,
  named in §4.8 and not committed), and the two fences read before the
  session.
* **The cost is known.** H7: ×2.38 on the median wall of one 26-test file
  for a per-statement record of six functions, plus 1.132 s of resolution
  once per invocation.

**The gaps this rung found, and did not paper over.**

1. **A spec selects what is nested inside what it names (H2, STOP).** Three
   typed specs resolved to six sites, because `forcedDiceFromSource` holds a
   `reduce` arrow and `buildDiceQueueEntry` holds two default-parameter
   arrows, and `focus.mjs`'s prefix rule selects a container's members. The
   behaviour is documented and deliberate; the *pre-registration* predicted
   three because it counted the functions a reader names, not the
   function-likes a spec selects. Anyone who writes "focus these three
   functions" on a real file should expect the resolver to answer with more
   than three, and `resolve.mjs` is where they will find out — before the
   run. Whether `--focus` should offer a spelling that means "this function
   and not its nested arrows" is a design question this rung raises and does
   not answer.
2. **`focus_matched` and `functions_focused` differ, and the difference is
   real (H2, reported).** 5 against 6, because two anonymous arrows share
   one `<file>:<qualname>`. R31's parenthetical is what makes the second
   number visible at all; without it a reader would have been told five and
   the transform would have instrumented six. A qualname is not an identity
   for an anonymous function-like — a fact worth carrying into any later
   work on `--focus` spellings.
3. **Two of this rung's three STOPs are the instrument's, not the
   recorder's (H4, H5).** H4's cell tested "no HIT at line 72" where §1.2
   predicted "no HIT at the `while`-COMPLETION row", and line 72 carries a
   head row too; the head rows that hit are second-entry rows at which
   `count` is legitimately still 1, and no completion row hit. H5's cell
   could not see a CALL sighting the transcript prints, because a CALL row's
   printed name carries its argument list and a printed CALL row carries no
   line at all. Both were found after their numbers were read, so both are
   findings and the numbers stand. **The lesson is about the dry run, not
   about the reader**: the rehearsal on `typescript/probes` exercised a LINE
   sighting and a loop whose extra clause happened to hold, so neither
   defect had a chance to show. A dry run that does not exercise every
   SHAPE an endpoint can meet is a dry run that verifies plumbing and not
   reading.
4. **`e12_report.py`'s row parser drops a `RETURN` row** (one space before
   `->` where it requires two), which under-reports an ungated field. Named
   here because a reported list that is quietly short is worse than no list.

**Carried debt for the next rung**, none of it re-measured here: the three
parser readings of item 3 and 4 (`h4`'s clause off `unbound` rather than off
the line, `rows_of`'s CALL name and its `RETURN` spacing, and a CALL
sighting's line read from the code object rather than from the printed row);
and the design question of item 1.

**What a reader can do with this that they could not before.** Ask a
TypeScript test suite what a function's statements actually wrote, one row
per completed statement, with the names that went out of scope named — and
be told, by the recording itself, when the run they are holding cannot
answer.
