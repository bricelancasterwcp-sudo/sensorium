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

*written when the endpoints have run*

## 3. Results

*written when the endpoints have run*

## 4. Verdicts

*written when the endpoints have run*

## 5. Gaps

*written when the endpoints have run*
