# S5, the refocus slice — `refocus` for TypeScript traces, and E15: acceptance (pre-registered)

**Status: PRE-REGISTERED.** §1 was written before any line of this slice's
code existed; §2, §3, §4 and §5 are the measured half and are written once
the endpoints have run.

What this record measures is spec §5's: one unfocused `sensorium ts run`
over a whole 372-file vitest suite, then 31 `sensorium refocus` re-runs of
it — one per selected member — and the two controls, read against the ten
endpoints H1–H10 that §1 carries. Nothing here is a benchmark: every
endpoint is a question with a pre-committed reading, and each is read ONCE.

§1 of this file was written and committed on the feature branch
`feat/s5-refocus-ts` **alone and before any line of this slice's code
existed**: the commit that carried it changed nothing under `src/`,
`typescript/src/` or `rust/`, and under `corpus/` only the three new case
directories this pre-registration is partly made of —
`corpus/typescript/refocus_match`, `corpus/typescript/refocus_diverged` and
`corpus/typescript/refocus_refused_reused_worker`, each committed RED, each
with its failing run recorded in the ledger before the code that turns it
green was written. §1 is the locked contract — after a number is read, no
threshold moves, no arm is added and nothing is re-run; an instrument defect
found before a number is read is fixed and written into §2 with its commit,
and found after, it is a finding.

**The subject is a COPY.** E15 records on a throwaway copy of the lens
(`typescript/acceptance/copy_lens.sh`), never on the lens itself. The lens is
READ-ONLY in this slice and is verified against rung 1's 748-entry manifest
before and after; control B's planted edit is made on the COPY, which is the
whole reason a copy exists.

**The one thing a human decided** is the survey table:
`docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript-survey.md`,
the 31 selected test files with a hand class, a hand-derived focus spec and
a measured resolver count. It is the only part of this pre-registration that
a reading of source decides rather than an instrument, it was written before
`typescript/acceptance/e15.py` existed, and it is pinned by sha256 as §1's
second-to-last line; the lock test recomputes that sha and refuses a table
that has moved by a byte.

The lock is enforced by `tests/test_acceptance_e15_lock.py`, which recomputes
§1's own sha256 and, separately, compares each of §1's two verbatim bodies
against `git show <sha>:<source>` — so "verbatim" is a claim a test holds,
not one this prose makes.

## 1. Pre-registration

Two blocks, copied verbatim from the two documents that own them. Nothing in
either is paraphrased, reordered or reworded; the only editorial act is that
each source section is introduced by a `###` sub-heading here — the design's
`## 5.` keeps its own words one level deeper, and the plan's block, whose
own heading is a sentence about Task 0 rather than a title, is introduced as
`### Pre-registration (plan)` — so that this record keeps its own §1–§5
numbering. The design's body is read to the next heading in its source; the
plan's is read to the horizontal rule that terminates its section there, so
neither carries a byte that is not the source's. Sources, at the commits
named:

- `docs/superpowers/specs/2026-09-13-sensorium-s5-refocus-typescript-design.md` at
  **`a8aa533`** (this branch's design commit) — `## 5. E15, pre-registered`,
  whole, up to `## 6.`
- `docs/superpowers/plans/2026-09-13-sensorium-s5-refocus-typescript.md` at
  **`4d8f3d9`** (this branch's plan, at its single plan commit) —
  `## Pre-registration (…)`, whole, up to the `---` that ends it

One box path appears inside §1, and only inside the verbatim plan block:
that block's own last-but-one bullet names the slice's locations as *all
under `/mnt/extra/sensorium-rung2/e15/`*. The block is carried byte-for-byte,
so the path is carried with it; editing it out would break the claim the lock
test holds. It is sanctioned here for that reason and for no other.
Everywhere else in this slice the lens is `<lens>`, the copy is `<copy>` and
the store is `<store>`, and §2's pin table will be the only other place in
this record where a box path is written.

### 5. E15, pre-registered

Record `docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md`;
§1 committed alone and byte-locked before the instrument exists, on the
`tests/test_acceptance_s5_debts_lock.py` pattern (a content sha, recomputed
on the working tree, with the amendment discipline that file documents);
instrument `typescript/acceptance/e15.py` (the loop, detached with markers,
`.DONE`/`.FAILED` with `exit=<n>`, env-var locations only), `e15_report.py`
(the cells, both readings), `assemble_e15.py` (`lens.stamp`, provenance,
writes-then-exits-1 on a provenance failure, ruling P9 of the debts slice).
Subject: a throwaway copy of the lens (`copy_lens.sh`) at VTT `0091e97`,
`typescript/acceptance/LENS.txt`'s own words, `node_modules` symlinked; a
fresh `SENSORIUM_DIR`; the `sensorium` of this branch (`lens.sensorium_bin`),
whose editable install is refreshed at preflight so that `driver_version`
reads **0.14.0** on every trace the record cites — the driver reads its
version from package metadata, and a stale install would stamp the previous
release's number on this slice's data.

**The originals.** ONE unfocused recording of the whole suite: `sensorium ts
run -- npx vitest run` from the copy's root — the harness command as the
rung-1 arms typed it. Its member count is `U`; every later count is read
against it.

**The selection, written first.** `find src -name '*.test.*' | LC_ALL=C
sort`, every twelfth file starting at index 0 — **31** of 372. For each, a
HAND survey classes it deterministic or names its source of divergence
(`Math.random`, a clock, a real timer, a network call, an order the program
does not fix), and names ONE focus spec: the first function, in source
order, of the first `src/` module the test file imports that
`resolve.mjs` selects; if the file imports none, the first function the
file itself defines. The list — file, class, reason where not
deterministic, focus spec, `node resolve.mjs`'s count for it — is §1's table
and is byte-locked. The expected-MATCH list is the deterministic rows. No
exception is invented for a file the survey cannot read; such a file is
listed as `unsurveyed` and its verdict is a reading, not a gate.

**Loop.** For each of the 31: `sensorium refocus <member> --focus <spec>`,
where `<member>` is the original's trace for that file — 31 whole-suite
re-runs. Then the two controls. Then the reads.

| id | question | endpoint (both readings pre-committed in §1) |
|---|---|---|
| H1 | does every original refocus without a pre-rerun refusal? | **0 of 31** refusals — each member carries `harness_command`, `harness_cwd`, one `test_file`, tier `call` |
| H2 | does every re-run complete? | **31 of 31** harness exits equal to `U`'s (status, signal, `waited`); a harness that ended differently is a **finding** carrying the exit, not a STOP |
| H3 | is the pair found, and how many siblings? | **31 of 31** exactly one candidate by `test_file`; linked count = `U`'s member count on **31 of 31**; a REFUSED after the re-run on the lookup is a **STOP** (the pairing) |
| H4 | MATCH on the expected list? | MATCH on every deterministic row; an unexpected DIVERGED is a **finding** recorded with the divergent event (E4's own reading); a REFUSED from the comparator is a **STOP** |
| H5 | what does the licence say? | reported per pair and summed: source verified **31 of 31**; environment verified **31 of 31** with the recorder's set NAMED on every line and harness set 1's count where it differs; output, children, threads UNVERIFIABLE **31 of 31**, each printed; harness exit equal **31 of 31**; **0** licence lines claiming an unverifiable check as verified; GRANTED on every MATCHed deterministic row (the expected-granted list is the expected-MATCH list — nothing in a per-file container's world is expected to move) |
| H6 | does the loop close? | three `watch --at <spec> --expr …` triples and one `flow --value` on three NEW traces named in §1, answering as predicted (verdict class and exit) |
| H7 | control B — a planted edit | `plant_edit.py` appends one failing test to one selected file in the copy; its refocus reads `source: CHANGED` naming the file and `licence: WITHHELD` with that reason, whatever the verdict; **1 of 1** |
| H8 | control C — a refusal | `refocus <member> --window 1` on one original: exit 2, the §2.3 sentence, and the store's trace count UNCHANGED before and after; **1 of 1** |
| H9 | what does it cost? | reported, no gate: per refocus the wall from launch to verdict, the harness's own `Duration`, the conversion's wall, the spool bytes and trace bytes the invocation added; the store and spool totals at the end |
| H10 | did nothing else move? | corpus every case equal, all three languages, `--require-driver`, the three new cases included; pytest; `cargo test --workspace`; `npm --prefix typescript test`; the probes; `tests/test_ceiling.py`; the E7 needle on the new output; `e_fences.py` legacy and branch, with the fence's report listing NO fenced path (this slice touches none: `rust/` is untouched, `exceptions*.py` untouched) |

**Kill rules.** As E4 and E12′: a `.FAILED` before any number is
infrastructure (archive, empty the fresh locations, relaunch from zero);
after a number it stands; measured once; nothing re-rolled; a reader at its
ceiling is the record. The loop runs detached, bounded at three hours, each
refocus at 900 s. **Disk**: each whole-suite invocation keeps its spool
directory under `<store>/spool/` (the driver's own behaviour, ~400 MB on the
lens) — 33 invocations is on the order of 13 GB, on a disk with 87 GB free;
the spools are kept until §3 is written and freed after, and the record
names the bytes. **Wall**: the lens's call-tier suite is ~24 s plus a
conversion measured at 16–45 s (rung 1), so ~45 minutes for the loop.

### Pre-registration (plan)

This block is carried verbatim into `docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md` §1 (A5) and is byte-locked with it. It states what §5 defers to the record and what Task 0 itself pre-registers:

- **The originals.** One `sensorium ts run -- npx vitest run` from the copy's root, tier `call`, no focus; `U` = the count of `run:` lines it prints; every member carries `harness_command == ["npx", "vitest", "run"]`, `harness_cwd == <copy root>`, one `test_file`, `env.SENSORIUM_TIER == "call"`. §2 records `U`. Rung 1's arm recorded 372 test files on this lens, so the prediction is `U == 372`; a `U` that differs is reported, not a STOP, and every later count is read against the measured `U`.
- **The selection** is the deterministic rule of §5 (`find src -name '*.test.*' | LC_ALL=C sort`, every twelfth from index 0) and produces **31** rows; the survey table `…-survey.md` lists them with `| n | test file | class | reason | focus spec | resolver matched |`, one row per file, `N = 31` as its last line, sha-pinned into §1. The expected-MATCH list is every row whose class is `deterministic`; a row classed `nondeterministic` names its reason and is a READING; a row classed `unsurveyed` is a reading. The expected-granted list equals the expected-MATCH list.
- **The three H6 reads**, named in the survey table's last block: three `watch --at <spec> --expr <expr>` triples on three refocused traces (rows 1, 16 and 31 of the table, their focus spec, a predicate the survey derives from the function's own source) and one `flow --value <literal>` read on row 16's trace, each with its predicted verdict class and exit.
- **Control B** edits row 2's test file with `plant_edit.py` on the COPY, refocuses row 2's original, and predicts `source: CHANGED` naming that file and `licence: WITHHELD` carrying the source reason; the verdict is a reading (the planted test is a new task, so the prediction is DIVERGED at the task multiset, and that is stated as a reading, not a gate).
- **Control C** runs `refocus <row 3's original> --window 1`, predicts exit 2 with §2.3's refusal-1 sentence, and the store's trace count equal before and after.
- **The corpus cases** commit RED at Task 0 with their hand-derived expectations: `refocus_match` (`verdict: MATCH`, exit 0, `siblings in the re-run: 0`, the licence line present, `WITHHELD` absent, the three unverifiable markers, `runs` with two `invocation ` headers and `refocus-of:$RUN`, `info last` with `harness cwd:` and `line=yes locals=yes`, `watch last --at fill --expr b == 2` SATISFIED); `refocus_diverged` (`verdict: DIVERGED`, exit 1, `at causal step 4:`); `refocus_refused_reused_worker` (refusal 7's sentence, exit 2, one `invocation ` header). A count corrected at Task 5 is corrected only in the direction the spec predicts and is logged in the ledger.
- **Versions expected:** Python `0.14.0` on every E15 trace's `driver_version`; `sensorium-ts 0.4.0` on every `recorder`; vitest `4.1.9`; node `v24.16.0`. §2 records what each actually was; a version token in any checked sentence is read from the trace, never hard-coded.
- **Locations** are §2's pin table only: the lens copy, the fresh store, the transcripts directory — all under `/mnt/extra/sensorium-rung2/e15/`.
- **Kill rules** are §5's; the loop budget is three hours, each refocus 900 s, each reader 120 s.

### Amended 2026-09-13 (ruling P16, before any endpoint ran)

Two clauses of the table above are pre-registration errors, found BEFORE any
of this slice's numbers was read — while Task 7 was reading the instrument
against the code it judges, and before `e15.sh` had been launched once.
Neither is edited: §1 is the locked contract, so each stands as written, is
MEASURED AND REPORTED as written, and STOPs where its literal fails. What
this paragraph adds is a corrected clause beside each, pinned here with both
of its readings, on the S5 rung-4 debts record's precedent (its §1.7 second
amendment, the same ruling number and the same discipline: add, never edit).

**H7, as locked** — "`plant_edit.py` appends one failing test to one selected
file in the copy; its refocus reads `source: CHANGED` naming the file and
`licence: WITHHELD` with that reason, whatever the verdict; **1 of 1**" —
asks for a line the command does not print on the verdict control B is
predicted to reach. `src/sensorium/query/refocus_report.py` prints a
`licence:` line only on a MATCH (`licence: WITHHELD -- this MATCH is about
call shape…` at its `:245`, the verified form at `:251`); on a DIVERGED it
prints the world findings under their own header, `differences in the world
between the two runs, any of which may be why:` (`:170`), and no licence line
at all. §1's own plan block states control B's predicted verdict as DIVERGED
(the planted test is a new task), as a reading rather than a gate. So H7's
`licence: WITHHELD` clause is expected to fail on a DIVERGED transcript, and
H7 STOPs there. That STOP is a finding about THIS pre-registration — the
phrase "whatever the verdict" was written as though one line carried the
source reason for every verdict — and not about the tool, whose behaviour was
fixed before §1 was written and is unchanged by this slice.

**H7′**, pre-registered here: the same two facts H7 asks for — the source
change was SEEN, and it was REPORTED to the reader — with the second one
looked for where the report actually puts it. `source: CHANGED` names the
planted file, AND the source reason is printed in the block the report prints
for the verdict reached: the `licence: WITHHELD …` reasons on a MATCH, the
`differences in the world between the two runs` block on a DIVERGED. The
holding reading is **1 of 1**. The other reading — the source reason absent
from that block, or `source: CHANGED` not naming the planted file, or a
verdict whose block this clause does not name — is a **STOP**.

**H8, as locked** — "`refocus <member> --window 1` on one original: exit 2,
the §2.3 sentence, and the store's trace count UNCHANGED before and after;
**1 of 1**" — spells a command this tree refuses before design §2.3 can run.
`--focus` is `required=True` on the `refocus` sub-parser
(`src/sensorium/query/refocus_cmd.py:186`), so argparse rejects the CALL with
its own usage line: the exit is 2 and the trace count is unchanged, as §1
predicts, but the sentence printed is argparse's and not refusal 1's. H8 is
RUN and REPORTED as written — the literal command, its exit, its stderr, its
own pair of trace counts — and STOPs on the sentence clause, by design.
Judging the `--focus`-bearing form under H8 would answer a question §1 did
not ask.

**H8′**, pre-registered here: `refocus <row 3's original> --window 1 --focus
<row 3's spec>`, the form that reaches design §2.3's refusal 1, read on the
same three clauses — exit 2; refusal 1's sentence verbatim, `--window is not
available for a TypeScript trace (the recorder has no per-activation gate);
nothing was re-run`; and the store's trace count equal before and after the
invocation. The holding reading is **1 of 1**; any of the three clauses
failing is a **STOP**.

`typescript/acceptance/e15_cells_controls.py` reads H7 and H8 by their
literal locked clauses and carries H7′ and H8′ as separate cells, `H7p` and
`H8p` — never as widenings of the first two, because a prediction satisfied
by a different line is not the prediction that was pinned — and the slice's
word counts an H7 or H8 STOP as a STOP, so this record's word is
DONE-WITH-STOP if either literal clause fails, exactly as the debts slice's
E6-TS′ made it. This amendment moves no row of the H1–H10 table, no bullet of
the plan block and no derivation above it; it adds these paragraphs and
nothing else. `ORIGINAL_LOCK` in `tests/test_acceptance_e15_lock.py` carries
the sha256 of §1 before this paragraph, recomputed from `74d574c`, and
`BYTE_LOCK` the sha after it, so the amendment is a fact the lock publishes
rather than a claim this prose makes.

### The survey, pinned

The survey table is the prediction E15's H4 and H5 are judged against, and
the only part of this pre-registration a human's reading of source decides
rather than an instrument. It was written at Task 0, before any of this
slice's code existed, and is pinned here by CONTENT: a table edited after a
number is read is not a prediction, so its sha256 is §1's second-to-last
line and the lock test recomputes it from the file on disk. The last line is
the plan commit the block above was read from, so the two things §1 defers
to — a file and a commit — are both named where the byte lock covers them.

survey: 10433230d34dfd96f7aeede1c637dbb217da1764bc98d00f50474b909ae5d46b
plan-commit: 4d8f3d9

## 2. Environment

Measured **2026-09-13T06:18:42-0500 → 2026-09-13T07:18:22-0500**, 59 min 40 s,
by `typescript/acceptance/e15.py`, launched ONCE and detached by
`typescript/acceptance/e15.sh`; pid 3555401; it wrote `<out>/e15.DONE`
carrying `exit=0`, and the raw facts it recorded are `<out>/results-e15-raw.json`
with `<out>/e15.log` and every transcript beside it. §3 below is computed from
`2026-09-13-sensorium-e15-refocus-typescript.results.json`, which
`typescript/acceptance/assemble_e15.py` derived from that raw file; every
number in §3 and §4 is quoted from a cell of that results file or from the raw
it was built from, and the transcripts those cells name are committed beside
this record in `2026-09-13-sensorium-e15-refocus-typescript-transcripts/`.

**Provenance, checked rather than asserted.** The assembler's four checks all
read OK on this run: `not_a_dry_run` (`preflight.dry_run` is `false`),
`driver_version` (`0.14.0`, §1's requirement on every trace this record
cites), `section_one_has_not_moved` (§1's sha256 recomputed from this file on
disk against `tests/test_acceptance_e15_lock.BYTE_LOCK`) and
`the_survey_has_not_moved` (the survey's sha256 against `SURVEY_LOCK`,
`10433230…5d46b`, §1's second-to-last line). The assembler was given
`sensorium-ts 0.4.0 / driver 0.14.0` as its recorder and
`e344fb6a494ece8b7f3a116e2a1aa8a0fb5324b6` as its rev, and exited 0.

**The box paths of this run are written HERE and nowhere else** — not in the
results file, not in a committed transcript, and elsewhere in this record only
in the one place §1 already sanctions: the verbatim plan block's own
locations bullet, carried byte-for-byte. This table is their one other
appearance; everywhere else they are the labels in its first column's
parentheses.

| Pin | Value |
|---|---|
| repo HEAD at the run | `e344fb6a494ece8b7f3a116e2a1aa8a0fb5324b6` (short `e344fb6`), branch `feat/s5-refocus-ts`; `git status --porcelain` empty before (`preflight.git_porcelain`) and after (`cleanup.repo_porcelain_after`) |
| the worktree (`<repo>`) | `/mnt/extra/sensorium-rung2/s5-refocus-ts` — every instrument ran from here under its own `.venv` |
| the lens (`<lens>`, READ-ONLY input) | `/mnt/extra/sensorium-s5/vtt/frontend` — *VTT frontend at 0091e97*, `typescript/acceptance/LENS.txt`'s own words; 372 test files; never the subject of a recording |
| the work root (`<work>`) | `/mnt/extra/sensorium-rung2/e15` — created by this run, absent before it |
| the copy under measurement (`<copy>`) | `/mnt/extra/sensorium-rung2/e15/lens` — `copy_lens.sh`, exit 0 in 0.067 s, 8 230 872 bytes of tree, `node_modules` a SYMLINK into the lens's; `npx vitest --version` read in the copy: `vitest/4.1.9 linux-x64 node-v24.16.0` |
| the trace store (`<store>`, FRESH) | `/mnt/extra/sensorium-rung2/e15/store` |
| the out directory (`<out>`) | `/mnt/extra/sensorium-rung2/e15/out` |
| the shared cargo target (`<target>`) | `/mnt/extra/sensorium-rung2/rust-target` — H10's `cargo test --workspace` only; passed as `E15_CARGO_TARGET`, never written into an instrument |
| the fence base | `5ab9861b141f74e9716277b80b7ffa5a88213e94` |
| version tokens — **READ OFF THE TRACES**, never from the instrument | `driver_version` **0.14.0**, `recorder` **sensorium-ts 0.4.0**, `node` **v24.16.0**, `vitest` **4.1.9** — the same four values in an original (`20260913-061850-5d6614`), in a refocused trace of the loop (`20260913-062030-79da45`, `focus ["AiPrepPanel.tsx:AiPrepPanel"]`) and in H6's row-16 trace (`20260913-064635-66a918`, `focus ["useMeshVoice.ts:loadVolumes"]`), each read with a read-only `sqlite3` open of the trace's `meta` table |
| the recorder string the run stamped | `sensorium 0.14.0 / sensorium-ts 0.4.0 at e344fb6a494e` (`preflight.recorder`) |
| reader | `<repo>/.venv/bin/python` → Python 3.13.13; `<repo>/.venv/bin/sensorium` |
| machine | 16 cpus |
| 1-minute load at the launch | 0.31 |
| disk free on the work filesystem, before / after | **90.98 GB / 54.16 GB** (the runner's floor is 30 GB) |

**The launch line**, as `e15.sh` was invoked from a plain shell:

```
E15_CARGO_TARGET=<target> bash typescript/acceptance/e15.sh <lens> <work> <out>
```

`e15.sh` exports `E15_LENS`, `E15_WORK`, `E15_OUT` and `PYTHONDONTWRITEBYTECODE=1`
and `setsid nohup`s `e15.py` with its output to `<out>/e15.log`. No location is
written inside any instrument; all four are arguments or variables.

**One launch, no relaunch.** `.FAILED` was never written, at any phase; §1's
kill rule for a pre-number `.FAILED` (archive, empty, relaunch from zero,
once) was never exercised, and there is no archived out directory beside this
record. The raw's `status` is `ok`, its `exit` is `0`, `loop.partial` is
`false`, `loop.incomplete` is `null`, `loop.budget_exhausted` is empty, and
`fences.partial` is `false`. No cell in the results file carries a `dropped`
reason and none carries a null value: twelve cells, twelve values.

**`U` and the originals.** ONE unfocused whole-suite recording,
`<repo>/.venv/bin/sensorium ts run -- npx vitest run` from `<copy>`,
invocation `20260913-061842-659583`: **`U` = 372** `run:` lines, 372 traces
reported, and `printed_and_recorded_disagree` empty — the printed member list
and the store agree file for file. Wall 38.289 s; vitest's own
`Duration  24.76s (transform 22.70s, setup 15.76s, import 52.09s, tests
97.29s, environment 161.18s)`; spool 424 769 319 bytes. The invocation's
harness exit is **`1 (waited)`**, and its vitest summary is

```
 Test Files  3 failed | 369 passed (372)
      Tests  4051 passed (4051)
```

**The three failed files, and why a file fails with zero failing tests.**
`<out>/originals.txt` names them under `⎯⎯⎯⎯⎯⎯ Failed Suites 3 ⎯⎯⎯⎯⎯⎯⎯`:

| file | the error vitest printed |
|---|---|
| `src/lib/aoe/aoe.vectors.test.ts` | `Error: aoe vector file not found; looked in: <copy>/docs/superpowers/specs/aoe-hex-vectors.json, <work>/docs/superpowers/specs/aoe-hex-vectors.json` — thrown at `resolveVectorFile` (`:66`) from module scope (`:70`) |
| `src/lib/distance/distance.vectors.test.ts` | `Error: vector file not found; looked in: <copy>/docs/superpowers/specs/rt-distance-vectors.json, <work>/docs/superpowers/specs/rt-distance-vectors.json` — `resolveVectorFile` (`:183`) from module scope (`:187`) |
| `src/lib/builder/emit/pf2eSheet.test.ts` | `Error: could not locate backend/app/systems/pf2e/data/classes.json from <copy>` — `findSeedPath` (`:22`) from module scope (`:24`) |

Each is a **load-time error**, not an unhandled rejection and not a failing
assertion: vitest lists all three in its run header as `❯ <file> (0 test)` and
under `Failed Suites`, which is the category it uses for a file whose module
body threw while being collected — so no test in those files ever ran, which
is why `Tests 4051 passed (4051)` carries no failures beside three failed
files. The cause is the subject, not the recorder: all three walk **out of the
frontend directory** for a data file (`docs/superpowers/specs/…`,
`backend/app/systems/pf2e/data/…`) that lives in the VTT repo above it, and
the lens — and therefore `<copy>` — is the `frontend` directory alone, with no
parent repo to find. Whether they also fail on the plain lens outside a
recording was NOT measured (§5.5).

**The load guard.** `e15.py` waits before each recording while the 1-minute
load is ≥ 4.0, 20 s per wait, at most 90. It waited **97 times = 1 940 s**
(32 min 20 s) of the run's 59 min 40 s: 0 at preflight, 0 before the
originals, **94** across the 31 loop rows — every row waited, 3 tries on 28 of
them, 4 on rows 9 and 12, 2 on row 26 — and 3 before the controls. The load it
released at ranged 2.96–3.98; the ceiling of 90 tries was never approached.

**The walls, per phase** (`phases`, seconds): preflight 0.04 · copy 0.218 ·
originals 38.351 · survey_check 0.0 · **loop 3 176.537** · controls 102.785 ·
fences 260.992 · reads 0.608 — **3 579.531 s** in total, against §1's
three-hour loop bound and 900 s per refocus (the slowest refocus was 46.337 s).

**What was copied into the tree, and the scrub.** 41 files were copied from
`<out>` into
`docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript-transcripts/`
through a one-off scrub (not committed) that replaces box paths by the labels
of the pin table above: the loop's **31** transcripts, the controls' **4**
(`control-b.txt`, `control-b-plant.txt`, `control-c.txt` and
`control-c-as-written.txt` — H7 and H8 cite the last two), the reads' **4**
(renamed `reads-*.txt`), plus `originals.txt` (the evidence for `U` and the
three failed suites above) and `e-fences.txt` (H10's own report), because
`<work>` is freed after this branch merges and an evidence file that dies with
it is not evidence. **33 of the 41** files carried at least one box path. The
replacements, by label: `<lens>` 1 188, `<copy>` 298, `<work>` 66, `<store>`
32, `<repo>` 32, `<out>` 0, `<target>` 0. A recursive grep for the four
absolute-path prefixes `assemble.FORBIDDEN` names returns nothing over that
directory, and nothing over the results file either — `assemble_e15.py`'s
`offenders()` refuses at exit 2 on a box path that survives its own redaction,
so the results file could not have been written with one.

**The lens: what was verified, and what was not.** The lens was never the
subject of a recording — every `sensorium ts run` and every `refocus` ran with
`harness_cwd` `<copy>` (read off the traces' `meta`) — and control B's planted
edit was made on `<copy>`, then restored and checked against the lens's own
copy of that file: `lens_sha256` and `copy_sha256` both
`9e3667baa740932126129dc648ba39be14f63bcc419a73f14ffd782f8ae084e4`,
`sha_equal: true`. But §1's preamble says the lens "is verified against rung
1's 748-entry manifest before and after", and **the runner does not do that** —
`e15.py` has no manifest check. What is available instead is an mtime sweep of
the lens taken after the run: no path under the lens outside `node_modules`
has an mtime later than the launch, and inside `node_modules` — which `<copy>`
reaches through a symlink — exactly two entries do: the directory itself
(07:13:43) and an EMPTY `node_modules/.vite-temp` (07:13:18), vite's own
scratch directory, written during control B's re-run. Whether `.vite-temp`
pre-existed and was merely touched cannot be told from an mtime. §5.9 carries
this.

## 3. Results

Twelve cells: §1's ten endpoints in §1's order, and ruling P16's two primed
readings published beside the two controls they re-read, never in place of
them. Every value below is the cell's own, quoted from
`2026-09-13-sensorium-e15-refocus-typescript.results.json`; every transcript
named is committed in
`2026-09-13-sensorium-e15-refocus-typescript-transcripts/`. No cell carries a
`dropped` reason — the loop ran all 31 rows, no row refused before its
re-run, and no pair lookup refused — so every "dropped" line below reads
*empty* and says so once here rather than twelve times.

### H1 — does every original refocus without a pre-rerun refusal?

- **Pre-registered, holding:** "**0 of 31** refusals — each member carries
  `harness_command`, `harness_cwd`, one `test_file`, tier `call`."
- **Pre-registered, other:** a row whose `refocus` refuses BEFORE the re-run
  ran no suite; the cell gates at 0, so one such row **STOPs** this record and
  is dropped by name from H2–H5.
- **Measured: 0 of 31, `holds: true`, word PASS.** `refusals` is empty.
  Evidence: `H1.evidence` of the results file; `<out>/e15.log`'s 31 `loop …`
  lines, each carrying `exit=` and a verdict.

### H2 — does every re-run complete?

- **Pre-registered, holding:** "**31 of 31** harness exits equal to `U`'s
  (status, signal, `waited`)."
- **Pre-registered, other:** a harness that ended differently is a **finding**
  carrying the exit, not a STOP.
- **Measured: 31 of 31, `holds: true`, word PASS**, `findings` empty. The
  originals' harness exit is **`1 (waited)`** — the three load-time failures of
  §2 — and every one of the 31 re-runs printed
  `exit: rerun 1 (waited)   original 1 (waited)`. The equality H2 asks for is
  an equality of a NON-ZERO exit, which is the sharper reading: a refocus that
  quietly repaired or lost those three failures would have broken it.
  Evidence: `H2.evidence.originals_harness_exit`; each row's
  `parsed.exit_line` in the raw; the `exit:` line of every transcript.

### H3 — is the pair found, and how many siblings?

- **Pre-registered, holding:** "**31 of 31** exactly one candidate by
  `test_file`; linked count = `U`'s member count on **31 of 31**."
- **Pre-registered, other:** a REFUSED after the re-run on the lookup is a
  **STOP** (the pairing).
- **Measured: 31 of 31, `holds: true`, word PASS.** `exactly_one_candidate`
  31, `linked_equal_to_U` 31, `U` **372**, `lookup_refusals` empty,
  `linked_findings` empty. Every row printed **371** siblings — the 372 traces
  of the re-run invocation minus the one that is the pair — on all 31 rows and
  on control B. Evidence: `H3.evidence`; each row's `parsed.pair` in the raw.

### H4 — MATCH on the expected list?

- **Pre-registered, holding:** "MATCH on every deterministic row" — the
  survey's 24.
- **Pre-registered, other:** "an unexpected DIVERGED is a **finding** recorded
  with the divergent event (E4's own reading); a REFUSED from the comparator
  is a **STOP**." A nondeterministic row's verdict is a READING and gates
  nothing.
- **Measured: 24 of 24, `holds: true`, word PASS.** `findings` empty,
  `comparator_refusals` empty, `no_verdict` empty. Across the whole loop the
  verdicts are **MATCH 30, DIVERGED 1**; the one DIVERGED is row 8, which the
  survey classes nondeterministic, so it is a reading and not a finding
  against the tool.

The loop, row by row (`H9.evidence.per_refocus` for the walls,
`H4.evidence`/`H5.evidence` for the verdicts and licences, the raw's
`loop.rows[*].parsed.pair.siblings` for the siblings):

| n | test file | class | verdict | licence | siblings | wall s | vitest `Duration` s | wall − harness s | transcript |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `src/__tests__/AiPrepPanel.test.tsx` | nondeterministic | MATCH | granted | 371 | 38.971 | 24.57 | 14.401 | `1-AiPrepPanel.test.txt` |
| 2 | `src/__tests__/CombatTrackerPf2ePersistent.test.tsx` | deterministic | MATCH | granted | 371 | 39.519 | 24.54 | 14.979 | `2-CombatTrackerPf2ePersistent.test.txt` |
| 3 | `src/__tests__/GmCockpit.test.tsx` | nondeterministic | MATCH | granted | 371 | 40.702 | 24.66 | 16.042 | `3-GmCockpit.test.txt` |
| 4 | `src/__tests__/PlayerViewRulesTabOrder.test.tsx` | deterministic | MATCH | granted | 371 | 40.575 | 24.51 | 16.065 | `4-PlayerViewRulesTabOrder.test.txt` |
| 5 | `src/__tests__/TurnCard.test.tsx` | nondeterministic | MATCH | WITHHELD | 371 | 40.843 | 24.57 | 16.273 | `5-TurnCard.test.txt` |
| 6 | `src/__tests__/api.test.ts` | deterministic | MATCH | granted | 371 | 40.727 | 24.56 | 16.167 | `6-api.test.txt` |
| 7 | `src/__tests__/classEditor.test.tsx` | deterministic | MATCH | granted | 371 | 42.872 | 24.76 | 18.112 | `7-classEditor.test.txt` |
| 8 | `src/__tests__/describeCharacter.test.tsx` | nondeterministic | DIVERGED | — (none printed) | 371 | 41.085 | 24.5 | 16.585 | `8-describeCharacter.test.txt` |
| 9 | `src/__tests__/footerSaveVsRest.test.ts` | deterministic | MATCH | granted | 371 | 41.527 | 24.57 | 16.957 | `9-footerSaveVsRest.test.txt` |
| 10 | `src/__tests__/levelingSettings.test.tsx` | nondeterministic | MATCH | granted | 371 | 40.806 | 24.51 | 16.296 | `10-levelingSettings.test.txt` |
| 11 | `src/__tests__/perfFlat.test.ts` | deterministic | MATCH | granted | 371 | 41.446 | 24.75 | 16.696 | `11-perfFlat.test.txt` |
| 12 | `src/__tests__/responsive/PanelDrawer.test.tsx` | deterministic | MATCH | granted | 371 | 41.229 | 24.48 | 16.749 | `12-PanelDrawer.test.txt` |
| 13 | `src/__tests__/roomStore.terrain.test.ts` | deterministic | MATCH | granted | 371 | 41.31 | 24.49 | 16.82 | `13-roomStore.terrain.test.txt` |
| 14 | `src/__tests__/shortcutRegistryDrift.test.ts` | deterministic | MATCH | granted | 371 | 41.371 | 24.62 | 16.751 | `14-shortcutRegistryDrift.test.txt` |
| 15 | `src/__tests__/uploadWithProgress.test.ts` | deterministic | MATCH | granted | 371 | 45.513 | 24.57 | 20.943 | `15-uploadWithProgress.test.txt` |
| 16 | `src/__tests__/useMeshVoice.test.tsx` | nondeterministic | MATCH | granted | 371 | 41.693 | 24.63 | 17.063 | `16-useMeshVoice.test.txt` |
| 17 | `src/__tests__/useWebSocket.test.tsx` | deterministic | MATCH | granted | 371 | 41.834 | 24.56 | 17.274 | `17-useWebSocket.test.txt` |
| 18 | `src/components/PanelErrorBoundary.test.tsx` | deterministic | MATCH | granted | 371 | 41.46 | 24.44 | 17.02 | `18-PanelErrorBoundary.test.txt` |
| 19 | `src/components/compendium/ItemEditor.test.tsx` | deterministic | MATCH | granted | 371 | 41.855 | 24.5 | 17.355 | `19-ItemEditor.test.txt` |
| 20 | `src/components/map/hexGrid.test.ts` | deterministic | MATCH | granted | 371 | 41.56 | 24.53 | 17.03 | `20-hexGrid.test.txt` |
| 21 | `src/components/pf2e/ActionPips.test.tsx` | deterministic | MATCH | granted | 371 | 41.926 | 24.48 | 17.446 | `21-ActionPips.test.txt` |
| 22 | `src/components/sheet/SpellCastPanel.test.tsx` | nondeterministic | MATCH | WITHHELD | 371 | 42.022 | 24.57 | 17.452 | `22-SpellCastPanel.test.txt` |
| 23 | `src/hooks/useWebSocket.diceDispatch.test.ts` | deterministic | MATCH | granted | 371 | 42.068 | 24.59 | 17.478 | `23-useWebSocket.diceDispatch.test.txt` |
| 24 | `src/lib/builder/archetypeOverrideLedger.test.ts` | deterministic | MATCH | granted | 371 | 46.337 | 24.64 | 21.697 | `24-archetypeOverrideLedger.test.txt` |
| 25 | `src/lib/builder/emit/dnd5eSheet.test.ts` | deterministic | MATCH | granted | 371 | 42.29 | 24.64 | 17.65 | `25-dnd5eSheet.test.txt` |
| 26 | `src/lib/builder/multiclassContext.test.ts` | deterministic | MATCH | granted | 371 | 41.988 | 24.44 | 17.548 | `26-multiclassContext.test.txt` |
| 27 | `src/lib/combat/rest.test.ts` | deterministic | MATCH | granted | 371 | 42.555 | 24.61 | 17.945 | `27-rest.test.txt` |
| 28 | `src/lib/dnd5e/classes.test.ts` | deterministic | MATCH | granted | 371 | 41.925 | 24.4 | 17.525 | `28-classes.test.txt` |
| 29 | `src/lib/items/resolveItem.test.ts` | deterministic | MATCH | granted | 371 | 42.429 | 24.6 | 17.829 | `29-resolveItem.test.txt` |
| 30 | `src/lib/pf2e/boosts.levelBoosts.test.ts` | deterministic | MATCH | granted | 371 | 42.208 | 24.59 | 17.618 | `30-boosts.levelBoosts.test.txt` |
| 31 | `src/lib/sheets/mergeSheetSnapshot.test.ts` | deterministic | MATCH | granted | 371 | 42.247 | 24.5 | 17.747 | `31-mergeSheetSnapshot.test.txt` |

**Six of the survey's seven nondeterministic rows MATCHed** — rows 1, 3, 5,
10, 16 and 22. The survey's reason on all seven is the same mechanism:
`waitFor`/`findBy*` outside `vi.useFakeTimers()` polls on a real 50 ms
interval, so the activation count of a callback defined in the test file is
decided by wall clock. On six of the seven that mechanism **did not bite at
the fingerprint**: the comparator's unit is an order-independent multiset of
CALL/RETURN/RAISE/HANDLED per task, and a poll that ran three times rather
than two changes a count the multiset does compare — so six MATCHes say the
callback happened to activate the same number of times in both runs, or that
the extra activations fell outside the compared frames. That is a finding
about the **survey**, not about the tool (§5.3).

**Row 8 is the one that diverged.** `src/__tests__/describeCharacter.test.tsx`,
focus `roomStore.ts:_persistMacros`, exit 1, no licence line. Its verdict
line:

```
refocus verdict: DIVERGED -- a task took a different path.
20260913-063214-1e13d7 is a DIFFERENT execution than 20260913-061850-a0c9e0;
it is still queryable, every `sensorium info 20260913-063214-1e13d7` says so,
and nothing it shows is a fact about 20260913-061850-a0c9e0
```

Its divergent step line, from `8-describeCharacter.test.txt`:

```
tasks: DIVERGED -- 5 task stream(s) originally, 5 on the rerun; only in A:
DescribeCharacter > GM + configured: drafts, maps the response via
aiDraftToState (content rows included), and calls onDraft 2c070ef49149,
DescribeCharacter > renders for a player when AI is configured and player
access is not disabled (self-service creation, unlike GM-only content
drafting) f0145c52b9f9; only in B: DescribeCharacter > GM + configured:
drafts, maps the response via aiDraftToState (content rows included), and
calls onDraft 3f88a5f996bb, DescribeCharacter > renders for a player when AI
is configured and player access is not disabled (self-service creation,
unlike GM-only content drafting) 262f4273c4be; first difference inside
DescribeCharacter > GM + configured: drafts, maps the response via
aiDraftToState (content rows included), and calls onDraft at causal step 193:
A e1283 CALL    DescribeCharacter  (<copy>/src/components/builder/DescribeCharacter.tsx)
/ B e1427 CALL    DescribeCharacter.<anonymous>  (<copy>/src/components/builder/DescribeCharacter.tsx)
```

Five task streams on each side, the same two named tasks on each side under
different content fingerprints, and the first difference at causal step 193 is
one CALL recorded as `DescribeCharacter` in the original and
`DescribeCharacter.<anonymous>` in the re-run — the same source file, a
different qualname for the frame. The report names the step, the two event
ids and both qualnames, which is what §1's "recorded with the divergent
event" asks for. Evidence: `H4.evidence.readings[3].divergent_line`;
`8-describeCharacter.test.txt`.

### H5 — what does the licence say?

- **Pre-registered, holding:** eight clauses, summed over the rows the loop
  ran — source verified 31 of 31; environment verified 31 of 31 with the
  recorder's set NAMED on every line and harness set 1's count where it
  differs; output, children and threads UNVERIFIABLE 31 of 31, each printed;
  harness exit equal 31 of 31; **0** licence lines claiming an unverifiable
  check as verified; GRANTED on every MATCHed deterministic row.
- **Pre-registered, other:** any clause failing is a **STOP**; an UNVERIFIABLE
  check printed as verified is the clause that exists to catch a licence that
  overclaims.
- **Measured: 8 of 8, `holds: true`, word PASS.** The sums:
  `rows` 31 · `source_verified` 31 · `env_verified` 31 · `recorder_set_named`
  31 · `harness_set_named` 31 · `harness_set_counted` 31 ·
  `unverifiable_output` 31 · `unverifiable_children` 31 ·
  `unverifiable_threads` 31 · `harness_exit_equal` 31 ·
  `claims_an_unverifiable_check` **0** · `granted_on_expected_granted`
  **24 of 24**. Harness set 1 fired on every row and was counted every time:
  `2 harness variable(s) differ: VITEST_POOL_ID, VITEST_WORKER_ID` — so this
  slice has no member of harness set 1 that never differed. Evidence:
  `H5.evidence.clauses` and `.sums`; each row's `parsed.licence_points`,
  `parsed.unverifiable` and `parsed.env_line`; every `licence:` line in the 31
  transcripts.

**The two WITHHELD licences, and why H5 still holds.** 28 rows were GRANTED, 2
WITHHELD, and 1 (row 8, the DIVERGED) printed no licence line at all. The two
WITHHELD rows are **5** (`src/__tests__/TurnCard.test.tsx`) and **22**
(`src/components/sheet/SpellCastPanel.test.tsx`). Both are MATCHes; both print
`licence: WITHHELD -- this MATCH is about call shape, and these checks say it
is not a statement about the run as a whole:` with one reason each, verbatim:

- row 5 — `the two containers reported different endings: SIGTERM originally,
  exit 0 on the rerun`
- row 22 — `the two containers reported different endings: exit 0 originally,
  SIGTERM on the rerun`

Both rows are classed **nondeterministic** by the locked survey, so neither is
in the expected-granted list, which §1 defines as the expected-MATCH list —
the 24 deterministic rows. The cell's own arithmetic confirms it:
`granted.expected_granted_rows` is exactly `[2, 4, 6, 7, 9, 11, 12, 13, 14,
15, 17, 18, 19, 20, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31]`, 24 rows, none of
them 5 or 22, and `granted.granted` equals `granted.expected_granted` at 24.
So H5's GRANTED-on-every-MATCHed-deterministic-row clause is untouched by the
two withholdings. What they say about the clause that withheld them is §5.2.
Evidence: `H5.evidence.granted`; `5-TurnCard.test.txt`,
`22-SpellCastPanel.test.txt`.

### H6 — does the loop close?

- **Pre-registered, holding:** "three `watch --at <spec> --expr …` triples and
  one `flow --value` on three NEW traces named in §1, answering as predicted
  (verdict class and exit)" — the survey's four predictions, each derived from
  the function's own source before any of them ran.
- **Pre-registered, other:** a read that does not answer as predicted is
  reported with what it said; the cell's rule is "each read's verdict class
  AND its exit equal to the survey's prediction", and it does not hold
  otherwise — **STOP**.
- **Measured: 3 of 4, `holds: false`, word STOP.**

| read | predicted | measured | agrees |
|---|---|---|---|
| Row 1 — `watch <row 1's refocus> --at AiPrepPanel --expr 'tool == "statblock"'` | SATISFIED, exit 0 | `verdict: SATISFIED at 10 of the 12 site(s) the predicate could be evaluated at`, exit 0, 0.156 s | yes |
| Row 16 — `watch <row 16's refocus> --at loadVolumes --expr 'raw != null'` | SATISFIED, exit 0 | `verdict: SATISFIED at 134 of the 134 site(s) the predicate could be evaluated at`, exit 0, 0.166 s | yes |
| Row 31 — `watch <row 31's refocus> --at isDeepEqual --expr 'a == b'` | SATISFIED, exit 0 | `verdict: SATISFIED at 31 of the 56 site(s) the predicate could be evaluated at`, exit 0, 0.136 s | yes |
| Row 16, the value read — `flow <row 16's refocus> --value 0.4` | **NOT FOUND, exit 1** | **FOUND**, `sightings: 115 event(s), 115 capture(s)`, exit 0, 0.148 s | **no** |

The three traces are the loop's own: `20260913-062030-79da45` (row 1,
`focus ["AiPrepPanel.tsx:AiPrepPanel"]`), `20260913-064635-66a918` (row 16,
`focus ["useMeshVoice.ts:loadVolumes"]`) and `20260913-071158-8af4f0` (row
31), each a trace this run recorded through `refocus` and none of them an
original — which is the "loop closes" part of the question, and it closed:
three of three `watch` reads answered on a refocused trace exactly as the
survey predicted, one of them (row 31) on a trace whose pair was MATCHed under
a GRANTED licence.

**The fourth read went the other way, and the survey said in advance how it
could.** The survey pre-registered NOT FOUND on the reasoning that "the only
capture-bearing function in that trace is `loadVolumes`, whose single local
`raw` is the object read out of `localStorage` BEFORE `saveVolume` writes
`0.4` into it", and then named its own falsifier: "a later `getStoredVolume`
that re-reads the store after the write would put `alice: 0.4` inside `raw`
and the read would come back FOUND — which is exactly the fact this read is
pre-registered to settle." It came back FOUND. The transcript
(`reads-4-flow.txt`) prints
`scope: 2764 capture(s) searched across 2764 event(s) in CALL args, RETURN
values and LINE local deltas` and 115 sightings, of which the 50 it shows are
every one a `RETURN  getStoredVolume -> 0.4   [return]`. So the value was
found, but not where the falsifier imagined it: not inside `raw` at a LINE
site of the focused function, but as the RETURN VALUE of `getStoredVolume` —
a function the focus spec does not name. The premise that only the focused
function bears captures is the part that was wrong: the tier is `call`, and at
`call` a RETURN value is recorded for the traced functions of the file, while
`--focus` adds the LINE-level local deltas for the one it names. Evidence:
`H6.evidence.reads` and `.findings`; `reads-1-watch.txt`,
`reads-2-watch.txt`, `reads-3-watch.txt`, `reads-4-flow.txt`.

### H7 — control B, a planted edit (the locked clause)

- **Pre-registered, holding:** "`plant_edit.py` appends one failing test to
  one selected file in the copy; its refocus reads `source: CHANGED` naming
  the file and `licence: WITHHELD` with that reason, whatever the verdict;
  **1 of 1**."
- **Pre-registered, other:** §1's `Amended 2026-09-13` paragraph, written
  before the run, states that this clause asks for a line the command does not
  print on the verdict control B is predicted to reach, and that H7 is
  measured and reported as written and **STOPs** where `licence: WITHHELD` is
  absent from a DIVERGED transcript.
- **Measured: 0 of 1, `holds: false`, word STOP.** The plant:
  `src/__tests__/CombatTrackerPf2ePersistent.test.tsx` on `<copy>`, an
  `it('e15-planted', () => { expect(1).toBe(2); });` block appended after 133
  lines, assertion at line 136 (`control-b-plant.txt`). The refocus
  (`refocus 20260913-061851-cb6398 --focus roomStore.ts:_persistMacros`) exited
  1 in 42.435 s with verdict **DIVERGED**, and its three clauses read:
  - `` `source: CHANGED` names the edited file ``: **true** —
    `source: CHANGED since the original run -- 1 of 34 file(s) differ by
    content: CombatTrackerPf2ePersistent.test.tsx`
  - `` `licence: WITHHELD` ``: **false** — `parsed.licence` and
    `parsed.licence_line` are both `null`; on a DIVERGED the report prints no
    licence line at all
  - `a withheld reason names the source change`: **false** —
    `withheld_reasons` is empty, because there is no withheld licence to carry
    one

  `licence_is_absent_on_a_diverged_verdict` is recorded `true` and
  `lens_restored` `true`. Evidence: `H7.evidence`; `control-b.txt`,
  `control-b-plant.txt`.

### H7′ — the same two facts, looked for where the report puts them

- **Pre-registered (ruling P16, before any endpoint ran), holding:**
  `source: CHANGED` naming the planted file AND the source reason printed in
  the block the report prints for the verdict reached — the
  `licence: WITHHELD …` reasons on a MATCH, the `differences in the world
  between the two runs` block on a DIVERGED — **1 of 1**.
- **Pre-registered, other:** the source reason absent from that block, or
  `source: CHANGED` not naming the planted file, or a verdict whose block the
  clause does not name — **STOP**.
- **Measured: 1 of 1, `holds: true`, word PASS.** Verdict DIVERGED;
  `block_read` "the `differences in the world between the two runs` block";
  the one reason in that block, and the one naming the source, are the same
  line: `1 source file(s) CHANGED between the two runs
  (CombatTrackerPf2ePersistent.test.tsx), so the rerun executed different code
  than the recording did`. So the source change was SEEN and it was REPORTED;
  what H7 got wrong was only where to look. Evidence: `H7p.evidence`;
  `control-b.txt`.

### H8 — control C, a refusal (the locked command)

- **Pre-registered, holding:** "`refocus <member> --window 1` on one original:
  exit 2, the §2.3 sentence, and the store's trace count UNCHANGED before and
  after; **1 of 1**."
- **Pre-registered, other:** §1's amendment, written before the run, states
  that `--focus` is `required=True` on the `refocus` sub-parser
  (`src/sensorium/query/refocus_cmd.py:186`), so argparse rejects the call
  before design §2.3 can run; H8 is run and reported as written and **STOPs**
  on the sentence clause.
- **Measured: 0 of 1, `holds: false`, word STOP.** The literal command,
  `refocus 20260913-061847-1651fd --window 1` (row 3's original), exited **2**
  with

  ```
  usage: sensorium refocus [-h] --focus FOCUS [--window WINDOW] run
  sensorium refocus: error: the following arguments are required: --focus
  ```

  Two of its three clauses hold — `exit 2` **true**, `the trace count is
  unchanged` **true** (12 276 before, 12 276 after) — and the third,
  `the §2.3 refusal-1 sentence, verbatim`, is **false**: `parsed.sentence` is
  `null`, because argparse answered first. Evidence: `H8.evidence`;
  `control-c-as-written.txt`.

### H8′ — the form that reaches refusal 1

- **Pre-registered (ruling P16, before any endpoint ran), holding:**
  `refocus <row 3's original> --window 1 --focus <row 3's spec>` → exit 2,
  refusal 1's sentence verbatim, and the trace count equal before and after —
  **1 of 1**.
- **Pre-registered, other:** any of the three clauses failing is a **STOP**.
- **Measured: 1 of 1, `holds: true`, word PASS.** The command
  `refocus 20260913-061847-1651fd --focus GmCockpit.tsx:GmCockpit --window 1`
  exited **2** in 0.134 s and printed, verbatim:

  ```
  error: cannot refocus 20260913-061847-1651fd: --window is not available for a
  TypeScript trace (the recorder has no per-activation gate); nothing was re-run
  no rerun was attempted; `sensorium ts run --focus <file>:<qualname> -- <harness
  command>` will record a fresh, UNVERIFIED invocation if that is what you want
  ```

  Trace counts **12 276 before, 12 276 between and 12 276 after** — the raw
  records all three, so the refusal is shown not to have written a trace at
  either point. Evidence: `H8p.evidence`; `control-c.txt`.

### H9 — what does it cost?

- **Pre-registered:** reported, **no gate** — per refocus the wall from launch
  to verdict, the harness's own `Duration`, the conversion's wall, the spool
  bytes and trace bytes the invocation added; the store and spool totals at the
  end. `holds` is `null` by design: there is no other reading, because there is
  no threshold.
- **Measured: 31 rows reported.** Word *reported*.

| n | focus spec | wall s | vitest `Duration` s | wall − harness s | spool bytes added | trace bytes added |
|---|---|---|---|---|---|---|
| — (the originals, unfocused) | — | 38.289 | 24.76 | — | 424 769 319 | — |
| 1 | `AiPrepPanel.tsx:AiPrepPanel` | 38.971 | 24.57 | 14.401 | 424 814 788 | 686 563 328 |
| 2 | `roomStore.ts:_persistMacros` | 39.519 | 24.54 | 14.979 | 424 795 307 | 686 493 696 |
| 3 | `GmCockpit.tsx:GmCockpit` | 40.702 | 24.66 | 16.042 | 425 513 148 | 687 292 416 |
| 4 | `useAiAssist.ts:runAiSettingsProbe` | 40.575 | 24.51 | 16.065 | 424 820 833 | 686 526 464 |
| 5 | `TurnCard.tsx:breakdownLabel` | 40.843 | 24.57 | 16.273 | 424 789 636 | 686 489 600 |
| 6 | `api.ts:apiFetch` | 40.727 | 24.56 | 16.167 | 425 430 713 | 687 173 632 |
| 7 | `ClassEditor.tsx:parseCsv` | 42.872 | 24.76 | 18.112 | 424 795 926 | 686 526 464 |
| 8 | `roomStore.ts:_persistMacros` | 41.085 | 24.5 | 16.585 | 424 797 089 | 686 497 792 |
| 9 | `roomStore.ts:_persistMacros` | 41.527 | 24.57 | 16.957 | 424 797 101 | 686 505 984 |
| 10 | `LevelingSettings.tsx:LevelingSettings` | 40.806 | 24.51 | 16.296 | 424 928 661 | 686 678 016 |
| 11 | `perfFlat.ts:shouldUsePerfFlat` | 41.446 | 24.75 | 16.696 | 424 799 686 | 686 501 888 |
| 12 | `PanelDrawer.tsx:PanelDrawer` | 41.229 | 24.48 | 16.749 | 425 032 959 | 686 772 224 |
| 13 | `roomStore.ts:_persistMacros` | 41.31 | 24.49 | 16.82 | 424 804 580 | 686 501 888 |
| 14 | `shortcutRegistryDrift.test.ts:readSrc` | 41.371 | 24.62 | 16.751 | 424 801 492 | 686 510 080 |
| 15 | `uploadWithProgress.ts:uploadWithProgress` | 45.513 | 24.57 | 20.943 | 424 830 113 | 687 099 904 |
| 16 | `useMeshVoice.ts:loadVolumes` | 41.693 | 24.63 | 17.063 | 424 816 080 | 686 497 792 |
| 17 | `useWebSocket.ts:buildDiceRollSourceFromChat` | 41.834 | 24.56 | 17.274 | 424 805 913 | 686 530 560 |
| 18 | `PanelErrorBoundary.tsx:PanelErrorBoundary.getDerivedStateFromError` | 41.46 | 24.44 | 17.02 | 424 806 753 | 686 518 272 |
| 19 | `ItemEditor.tsx:buildDraftInstruction` | 41.855 | 24.5 | 17.355 | 424 808 120 | 686 530 560 |
| 20 | `hexGrid.ts:snapToGridPoint` | 41.56 | 24.53 | 17.03 | 425 289 212 | 687 046 656 |
| 21 | `ActionPips.tsx:ActionPips` | 41.926 | 24.48 | 17.446 | 424 813 559 | 686 551 040 |
| 22 | `SpellCastPanel.tsx:SpellCastPanel` | 42.022 | 24.57 | 17.452 | 441 435 201 | 702 873 600 |
| 23 | `useWebSocket.ts:buildDiceRollSourceFromChat` | 42.068 | 24.59 | 17.478 | 424 804 867 | 686 534 656 |
| 24 | `advancement.ts:levelRecord` | 46.337 | 24.64 | 21.697 | 425 436 673 | 687 144 960 |
| 25 | `dnd5eSheet.ts:baseScores` | 42.29 | 24.64 | 17.65 | 424 806 321 | 686 518 272 |
| 26 | `multiclassContext.ts:normalize` | 41.988 | 24.44 | 17.548 | 424 808 298 | 686 530 560 |
| 27 | `rest.ts:capToward` | 42.555 | 24.61 | 17.945 | 424 816 597 | 686 505 984 |
| 28 | `classes.ts:classNameToken` | 41.925 | 24.4 | 17.525 | 424 839 890 | 686 534 656 |
| 29 | `resolveItem.ts:deepMerge` | 42.429 | 24.6 | 17.829 | 424 830 236 | 686 522 368 |
| 30 | `boosts.ts:isAbility` | 42.208 | 24.59 | 17.618 | 424 833 953 | 686 510 080 |
| 31 | `mergeSheetSnapshot.ts:isDeepEqual` | 42.247 | 24.5 | 17.747 | 424 807 158 | 686 534 656 |
| **31 rows, total** | | **1294.893** | **761.38** | **533.513** | **13 188 510 863** | **21 302 018 048** |

Walls: min **38.971 s** (row 1), median **41.693 s** (row 16), max
**46.337 s** (row 24) — the slowest row is 46.337 s against §1's 900 s
per-refocus ceiling, so no row came within a factor of nineteen of it. vitest's own `Duration` is almost flat, 24.40–24.76 s, so the
**wall minus harness** column is what `refocus` adds on top of re-running the
suite: 14.401–21.697 s, 533.513 s over the 31, a mean of 17.2 s. The unfocused
originals cost 38.289 s wall against a 24.76 s `Duration`, so the focused
re-runs are about 3 s slower than the unfocused recording of the same suite.

Bytes: each invocation adds ~425 MB of spool and ~687 MB of trace — 31
refocuses added **13 188 510 863** spool bytes and **21 302 018 048** trace
bytes. Row 22 is the one outlier in both columns (441 MB / 703 MB), and it is
also one of the two WITHHELD rows. At the end the store held **36 713 046 810**
bytes over **12 276 traces** and **33 spools** — 33 whole-suite invocations
(1 original + 31 refocuses + control B's) × 372 traces each, exactly — of which
the spool directory was **14 038 077 489** bytes; `<copy>` was 8 230 872 bytes.
Evidence: `H9.evidence.per_refocus`, `.totals`, `.originals`,
`.store_at_the_end`.

### H10 — did nothing else move?

- **Pre-registered, holding:** corpus every case equal, all three languages,
  `--require-driver`, the three new cases included; pytest; `cargo test
  --workspace`; `npm --prefix typescript test`; the probes;
  `tests/test_ceiling.py`; the E7 needle on the new output; `e_fences.py`
  legacy and branch, with the fence's report listing NO fenced path.
- **Pre-registered, other:** any suite non-zero, a needle hit, or a fence
  report naming a fenced file is a **STOP**.
- **Measured: 11 of 11 claims, `holds: true`, word PASS.** The seven suites:

| fence | exit | wall s | last line |
|---|---|---|---|
| corpus (`corpus/run_corpus.py --require-driver`) | 0 | 67.288 | `111 cases, 236 questions, 0 failures, 0 error(s)` |
| pytest (`-q -p no:cacheprovider`) | 0 | 177.309 | `4431 passed, 37 skipped in 177.02s (0:02:57)` |
| `cargo test --workspace` (in `rust/`) | 0 | 7.760 | `   Doc-tests sensorium_transform` |
| `npm --prefix typescript test` | 0 | 1.697 | `ℹ duration_ms 1634.306821` |
| `tsc` (`npm --prefix typescript run check`) | 0 | 1.608 | `> tsc -p tsconfig.json` |
| npm-probes (`npm --prefix typescript/probes run probe`) | 0 | 0.852 | the probe checker's own bar |
| ceiling (`tests/test_ceiling.py`) | 0 | 0.413 | `1030 passed in 0.23s` |

The **E7 needle** — the string `sensorium run --focus`, which this slice's
output must never print — was searched across **39** files of this run's own
output (`originals.txt`, the 31 transcripts, the three control transcripts and
the four read transcripts), recomputed AFTER the reads
(`needle_recomputed_after_the_reads: true`), and found **0 hits**.

The **fence's report**, `e-fences.txt`, whole:

```
{
  "e-legacy.json": {
    "value": 2, "n": 2, "dropped": [],
    "claims": {
      "the fenced files show zero diff against the branch point": true,
      "the fenced tests and the Rust key's tuple equality are green": true
    }
  },
  "e-branch.json": {
    "value": 1, "n": 1, "dropped": [],
    "claims": { "tests/test_acceptance_scripts.py is green": true }
  }
}
```

E-legacy fences seven paths — `src/sensorium/query/exceptions_rust.py`,
`src/sensorium/query/exceptions.py`, `rust/`,
`tests/test_exceptions_rust*.py`, `tests/test_exceptions_invocation.py`,
`tests/test_exceptions.py`, `tests/test_exceptions_synthetic.py` — against the
branch point `5ab9861b141f74e9716277b80b7ffa5a88213e94`, and its
`diff_stat_lines` is **`[]`**: the git diff over those seven paths from the
base to HEAD printed nothing, so the report **lists no fenced path**, which is
the claim §1 asks for beside the two green fence cells (118 passed for
E-legacy's suite, 10 passed for E-branch's). Evidence: `H10.evidence.claims`,
`.checks` and `.needle`; `e-fences.txt`; `fences.e_fences` in the raw.

## 4. Verdicts

Each word below is the cell's own `evidence.word`, produced by that
endpoint's rule and by no other; the slice's word is the results file's
`word`, which the assembler sets from the list of cells whose word is STOP.

| endpoint | rule, as the cell states it | value | word |
|---|---|---|---|
| H1 | 0 refusals before the re-run, of the rows the loop ran | 0 of 31 | **PASS** |
| H2 | the re-run's harness exit equals the originals' invocation exit, on every row | 31 of 31 | **PASS** |
| H3 | exactly one candidate by test file AND a linked count equal to `U`, on every row | 31 of 31 | **PASS** |
| H4 | MATCH on every deterministic row of the locked survey; a nondeterministic or unsurveyed row's verdict is a reading | 24 of 24 | **PASS** |
| H5 | §5's row, summed over every row the loop ran; an UNVERIFIABLE check is printed and never counted as verified | 8 of 8 clauses | **PASS** |
| H6 | each read's verdict class AND its exit equal to the survey's prediction | 3 of 4 | **STOP** |
| H7 | §1 LITERALLY: source CHANGED naming the file and a `licence: WITHHELD` line carrying that reason, whatever the verdict | 0 of 1 | **STOP** |
| H7′ | source CHANGED naming the file, and the source reason printed in the block the report prints for the verdict reached | 1 of 1 | **PASS** |
| H8 | §1 LITERALLY (`refocus <run> --window 1`, no `--focus`): exit 2, design §2.3's refusal-1 sentence, and a trace count equal before and after | 0 of 1 | **STOP** |
| H8′ | the same three clauses over `refocus <run> --focus <spec> --window 1`, the form that reaches design §2.3's refusal 1 | 1 of 1 | **PASS** |
| H9 | reported, no gate | 31 rows | *reported* |
| H10 | every suite exits 0, the needle finds nothing, and the fence's report lists no fenced path | 11 of 11 | **PASS** |

**The slice's word: `DONE-WITH-STOP`**, on three STOPs — H6, H7 and H8 — named
in the results file's `stops` list by their own rules.

**Two of the three STOPs are the pre-registration's own, and were pinned as
such BEFORE the run.** §1's `Amended 2026-09-13 (ruling P16, before any
endpoint ran)` paragraph says, in advance, that H7's `licence: WITHHELD` clause
asks for a line `refocus_report.py` prints only on a MATCH while §1's own plan
block predicts control B will DIVERGE, and that H8's command omits a
`required=True` argument so argparse answers before design §2.3 can; it
declares that each is measured and reported **as written** and STOPs on its
literal clause, and pre-registers H7′ and H8′ beside them with both readings
each. The run then read exactly that: H7 STOP / H7′ 1 of 1, H8 STOP / H8′ 1 of
1. Neither STOP is about the tool: on both points `refocus` behaves as §1's
amendment says it does, and this slice changed neither — a DIVERGED prints its
world findings under their own header and no licence line
(`refocus_report.py:170` against `:245`/`:251`), and `--focus` is
`required=True` on the `refocus` sub-parser (`refocus_cmd.py:186`), both read
off the tree before `e15.sh` was launched. This is the register
the S5 rung-4 debts record used for E6-TS′ (its §4.4) and for the same reason —
the clause was pre-registered before the answer was known, which is the only
thing that gives it force, and editing it once the answer was in would convert
a prediction into a description and leave no trace that anyone had been wrong.
So §1 keeps its words, the lock publishes the amendment as a fact
(`ORIGINAL_LOCK` unchanged at `40298b4f…fa8` from `74d574c`, `BYTE_LOCK` moved
once), and both readings of each control are reported here.

**The third STOP, H6, is the survey's — and it is the one this record did not
see coming.** Three of four reads answered exactly as predicted; the fourth,
`flow --value 0.4`, came back FOUND where the survey pinned NOT FOUND. The
survey named that falsifier itself and called it "exactly the fact this read is
pre-registered to settle", so the endpoint did its job: a pre-registered
prediction about the tool's reach was wrong, and the record says so instead of
widening the clause. It is a finding about the **survey's model of what a
`call`-tier trace captures**, not about `flow`, whose transcript printed its
scope, its sightings and its truncation note without being asked (§5.3).

## 5. Gaps

**5.1 H7 and H8 STOP on clauses this record wrote wrong.** H7 asked for a
`licence: WITHHELD` line "whatever the verdict" — one line assumed to carry the
source reason on every verdict — when `refocus_report.py` prints a `licence:`
line only on a MATCH (`:245` withheld, `:251` verified) and puts a DIVERGED's
world findings under `differences in the world between the two runs, any of
which may be why:` (`:170`). H8 spelled `refocus <run> --window 1` without
`--focus`, which `refocus_cmd.py:186` marks `required=True`, so argparse
refuses the call before design §2.3's refusal 1 can run. Both errors were found
at Task 7, while the instrument was being read against the code it judges, and
**before `e15.sh` had been launched once**; both were pinned in §1 by
amendment, with corrected clauses (H7′, H8′) carrying both of their readings,
before any endpoint ran. Neither STOP is about the tool. What each cost is one
endpoint that now reads as a STOP in a table of PASSes, and what each bought is
a second cell that asks the question the first one meant.

**5.2 P20 — the container-ending clause withheld two MATCHed licences for a
scheduler's choice.** Rows 5 and 22 are MATCHes whose licences were WITHHELD on
one reason each: `the two containers reported different endings: SIGTERM
originally, exit 0 on the rerun` (row 5) and the reverse (row 22). What differs
is how vitest's pool ended the worker fork that ran that file — a SIGTERM from
the pool versus the fork exiting 0 on its own — and the pool's choice is a fact
about the SCHEDULER, not about the world the program ran in: the same class of
fact as `VITEST_POOL_ID`/`VITEST_WORKER_ID`, which harness set 1 already NAMES
and never withholds on. Two symmetric rows in a 31-row loop, in opposite
directions, is what a scheduler's coin flip looks like. **Proposed closure:**
treat the container-ending disagreement as harness set 1 is treated — printed
and named on the licence line, never a reason to withhold — leaving the
withholding for endings that are the program's. **NOT APPLIED HERE**: this
record is measured once, and no number moves after a reading. The cost of the
proposal being wrong is two licences a later slice would grant that this one
withheld; the cost of leaving it is that every vitest row whose worker the pool
happens to kill loses a licence it earned.

**5.3 The survey's class rule bit once in seven, and its capture model was
wrong once.** Six of the seven rows the survey classed `nondeterministic`
MATCHed (rows 1, 3, 5, 10, 16, 22); one diverged (row 8). All seven carry the
same reason — a real 50 ms `waitFor`/`findBy*` poll the test never fakes — so
the class rule is a rule about a HAZARD, not about an outcome: the hazard is
real on all seven and moved the compared multiset on one. Row 8's divergence is
not even a poll count — it is one CALL recorded as `DescribeCharacter` in the
original and `DescribeCharacter.<anonymous>` in the re-run, at causal step 193
of the same source file — so the mechanism the survey named may not be the
mechanism that fired. Separately, H6's `flow` prediction rested on the premise
that "the only capture-bearing function in that trace is `loadVolumes`"; the
read found `0.4` 115 times as the RETURN value of `getStoredVolume`, which the
focus spec does not name. At tier `call` a RETURN value is recorded for the
file's traced functions and `--focus` adds the LINE-level local deltas for the
one it names, so "capture-bearing" is a wider set than "focused". A future
survey should class a row by whether the hazard can reach the compared
multiset, and should derive a `flow` prediction from the tier, not from the
focus.

**5.4 P5 — H6's closed loop rests on ONE row.** H6's four reads sit on survey
rows 1, 16 and 31, and rows **1** and **16** are classed nondeterministic. H6
is readable on all four regardless — its endpoint is the verdict class and exit
of the READ, not the verdict of the pair the trace came from — but the
demonstration that *the loop closes under a GRANTED licence* rests on **row 31
alone**. For the record, all three rows' licences did read `granted` (rows 1,
16 and 31 are all MATCH/granted in the loop table above); what row 31 alone
supplies is a granted licence on a row the survey **expected** to be granted.
Rows 1 and 16 were granted on a row whose verdict was a reading, so their grant
is an outcome, not a prediction met.

**5.5 The three failed suites were not tried on the plain lens.** Under the
recording, `src/lib/aoe/aoe.vectors.test.ts`,
`src/lib/distance/distance.vectors.test.ts` and
`src/lib/builder/emit/pf2eSheet.test.ts` fail at load with a missing data file
they look for outside the frontend directory (§2). Whether they fail the same
way on `<lens>` without any `sensorium` in the picture was **NOT MEASURED** —
running the plain suite is not one of §1's endpoints and this record does not
re-run anything after a number is read. The evidence that the recording is not
the cause is circumstantial but not nothing: the three errors are `ENOENT`-shaped
lookups relative to `process.cwd()`, the paths they print resolve above a
directory that has no parent repo in this layout, and H2 reads the SAME harness
exit `1 (waited)` on the unfocused original and on all 31 focused re-runs.

**5.6 The reused-worker mechanism was not exercised.** `refocus`'s refusal 7 —
the reused-worker case that `corpus/typescript/refocus_refused_reused_worker`
pins — needs a container that ran more than one test file, and no row of this
loop produced one: every invocation here ran vitest's default isolated forks,
one file per container, and nothing in E15 passes `--no-isolate` or
`--maxWorkers 1`. So the 31 rows say nothing about what `refocus` does with a
worker that carries a second file, and the corpus case remains that claim's
only evidence.

**5.7 What this record does NOT license.** (a) **Siblings.** Every row printed
371 siblings and every pair was found by `test_file`; that is a statement about
the LOOKUP, not a statement that the 371 other containers of the re-run match
their originals — nothing compared them, and the licence's own words say what
it covers. (b) **Values.** A MATCH is an order-independent multiset of
CALL/RETURN/RAISE/HANDLED per task; it is not an equality of values, and no
endpoint here compared one. `watch` and `flow` read values out of ONE trace
apiece. (c) **The second file of a reused worker** — §5.6. (d) **Output,
children and threads**: UNVERIFIABLE on all 31 rows, printed as such, and
therefore evidence of nothing in either direction. (e) **Anything outside the
`call` tier**: every recording here is `SENSORIUM_TIER=call`.

**5.8 The disk.** The 33 whole-suite invocations left **14 038 077 489 bytes**
(14.0 GB) of spool under `<store>/spool/`; §1 said the spools are kept until §3
is written and freed after, and they were: `<store>/spool` was removed after §3
above was written, freeing exactly those 14 038 077 489 bytes. The **22 675 054 592
bytes** (22.7 GB) of `<store>/traces` — 12 276 traces — are KEPT until this
branch merges, because every trace id this record cites is in them; freeing
`<work>` is a post-merge chore and the ledger carries it. The work filesystem
read 90.98 GB free before the run and 54.16 GB after it, and 68 290 424 832
bytes free once the spools were removed.

**5.9 The lens's manifest check did not run.** §1's preamble says the lens "is
verified against rung 1's 748-entry manifest before and after"; `e15.py` has no
such check, so this run verified the lens only through the copy's isolation and
control B's restore (`lens_sha256 == copy_sha256`, `sha_equal: true`). An mtime
sweep taken afterwards found nothing under the lens changed outside
`node_modules`, and inside it one entry the run left behind: an empty
`node_modules/.vite-temp` (mtime 07:13:18), vite's own scratch directory,
reached through the copy's `node_modules` symlink during control B's re-run,
with `node_modules`' own mtime moved to 07:13:43 by that write. The lens's *sources*
are untouched, but "READ-ONLY" was not literally true of the lens
**directory**, and no manifest was in a position to say so. A future runner
should verify the manifest at preflight and again at cleanup, and should decide
whether the copy's `node_modules` symlink is worth the one directory it lets
vite write.
