# Sensorium S5 slice 2 — E6″, the converter ladder, and the `node --test` extensions: design

**Date:** 2026-09-10
**Status:** design, awaiting Brice's read; then writing-plans
**Follows:** `2026-09-09-sensorium-typescript-recorder-design.md` (rung 1,
DONE-WITH-STOP) and its record
`../acceptance/2026-09-09-sensorium-s5-rung1.md`
**Precedes:** rung 2, `exceptions` on TypeScript traces (own design doc)

---

## 0. Provenance

Rung 1 shipped with two numbers that were not verdicts. **E6′** STOPped on
its plain-band clause — a plain-after wall of **22.8678 s** against the plain
arm's own five-run min–max **[22.3136, 22.7221]**, 0.1457 s (0.65%) above it,
with the three contamination clauses (manifest, markers, wrapper directory)
holding exactly. The record's §5 gaps 5 and 6 name what the STOP rests on:
`e6.sh` ran its one timed measurement with no load guard, and a five-run
min–max is a range, not a tolerance. **E10** was REPORTED on its own second
branch: full-suite `ingest` at **45.5293 s** (n=3) against a plain wall of
**22.5925 s**, ×2.02, which the rule made design input naming "a Node
converter on `node:sqlite`, or a binary wire". Rung 1's final review left four
residuals in `docs/CARRIED-DEBT.md` (ruling R46): `.tsx`/`.jsx` under
`node --test` fail in Node's loader; an eligible `.mts` is transformed but
never type-stripped; the R45 no-spool refusal does not name the tally's
CommonJS exclusions; a stale `hook.mjs:98` citation (R47).

This slice closes all of that with pre-registrations, in the order the
measurement discipline asks: the rule before the instrument, the instrument
before the number, and the number where it falls.

**Two facts read before this design, both from things already on disk.**

1. **The full-suite spool set is one file's story.** The call arm's first
   invocation, `20260909-160038-f08e89` — 372 spools, 414,450,522 bytes —
   has this size distribution: min 11,357 B, median 97,439 B, p90 868,088 B,
   p99 8,256,512 B, **max 195,851,484 B**. The largest spool is
   `src/lib/map/gridDetect.test.ts`: **2,246,596 records, 47% of every byte
   in the set**. The converter parallelises per spool (`ingest_dir` hands one
   spool to one worker), so that file's serial conversion is the floor under
   any full-suite wall.
2. **An exploratory profile of that one spool, disclosed as such.** On
   2026-09-10, `ingest.convert` was run over that spool alone from the main
   checkout at `aaa8692`, into a scratch store on `/mnt/extra`, with nothing
   in the repository touched. It is **not a gate and not an endpoint**: no
   load guard, n=1, taken to ask where the seconds go before choosing what to
   change. Plain wall **16.33 s** for 2,246,552 events. Under `cProfile`
   (31.78 s profiled): `executemany` **4.567 s** over 13,175 calls; `commit`
   **2.717 s** over **4,433** calls — one commit per 512-event batch under
   `journal_mode=WAL` with the default `synchronous`; JSON decode
   (`json.loads` and its callees) **≈4.9 s**; `json.dumps` of event payloads
   **≈5.0 s**; the rest is the builder's own Python.

   Read together: the slowest single part of the suite converts alone in
   about a third of the full-suite wall, so the full run is roughly three
   times slower than its floor. That points at contention between sixteen
   workers — fsync storms from a commit every 512 events, on a box whose
   governor is `powersave` — and not at parse speed. The Rust converter met
   exactly this in rung 2 and fixed it with one transaction per trace plus
   `synchronous=NORMAL` (`rust/cargo-sensorium/src/convert/sqlite.rs`;
   1,118.867 s → 1.197 s, record `2026-09-02-sensorium-rung2-acceptance.md`
   §5). A binary wire could touch only the ≈15% of profiled time that is JSON
   decoding, and cannot close a factor of two. These readings are
   **predictions** for §3's Arm 0 to falsify, not findings.

A third fact, measured with a throwaway loader hook in the scratchpad on
node v24.16.0 (§4): a hook that hands back Node's own reported format
(`module-typescript`) with an **edited** source gets Node's native type
stripping on `.ts` and `.mts` alike; a `.tsx` throws
`ERR_UNKNOWN_FILE_EXTENSION` inside `nextLoad` before any hook sees it; a
non-erasable `enum` fails with `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` plain and
hooked alike.

**Rulings already made in the brainstorm (2026-09-10):** Brice ruled that if
Arm A misses E10′'s bound the slice **stops at the report** — a Node converter
is a later slice with its own spec and equivalence gate, never a continuation
of this one. Instrument and design decisions are Claude's under the
2026-09-07 delegation and are recorded here with their cost if wrong (§9).

## 1. Goal, scope, non-goals

**Goal.** Turn rung 1's two open numbers into verdicts under new
pre-registrations, and close the four R46 residuals, without moving the trace
format.

**In scope.**

- **E6″** — the plain-band question re-asked with a load guard, a derived
  band, medians over n=5, and the manifest verified after the instrument's own
  runs (§2).
- **E10′** — a pre-registered ladder over the kept spool set: a diagnosis on
  main's code, then the Python write path one lever at a time, each measured,
  with an equivalence gate holding the traces identical (§3).
- **The `node --test` hook** — Node strips, the hook erases nothing; no JSX;
  the R45 refusal; citations by function (§4).
- **Two decisions recorded without work** (§5).
- Versions: Python **0.9.1**, `sensorium-ts` **0.1.1**. Trace format **4**
  unchanged; `docs/TRACE-FORMAT.md` is not opened.

**Non-goals, each named so its absence is a choice.**

- **Arm B, a Node converter on `node:sqlite`** — deferred by ruling (§0). If
  E10′ reports above the bound, the report carries every rung of the ladder
  and the design question stays open for its own slice.
- **Arm C, a binary wire** — dropped on the profile's number (§3.7).
- **Rung 2's `exceptions` rules**, argument capture, refocus, the browser
  runtime, the transform cache (rung-1 spec §11).
- **The untraced-caller tag** in `tree` (R29, a reader feature for all three
  languages) and **the 8/372 nondeterministic VTT files** (a consumer
  finding) stay where the ledger has them.
- **jest**, still refused by name.

## 2. E6″ — the plain band, pre-registered

**The question is E6's:** is a plain run of the consumer's suite contaminated
by a recording having happened? Three clauses ask it directly and held in
rung 1. The fourth is a timing clause, and it is the one rewritten here.

### 2.1 The session

One session, on the lens (`/mnt/extra/sensorium-s5/vtt/frontend`, VTT
`0091e97`, vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0), run **last
in the slice** so it exercises this slice's recorder, in this order:

1. **The §2 manifest verified before anything.** The rung-1 manifest
   (`/mnt/extra/sensorium-s5/manifest-rung1-before.txt`, 748 entries, file
   sha256 `eb4c5ddb…6c9a8`) is checked with `sha256sum -c`. Anything but 748
   OK / 0 FAILED means the lens moved since rung 1, and the session **stops
   before it starts**; nothing is measured on a lens that is not the one the
   band's history was taken on.
2. **Before arm:** five plain runs of the consumer's own command,
   `npx vitest run`, each behind the load guard E1′'s arms used — the
   1-minute load read from `/proc/loadavg`, the run held until it is below
   **4.0** (up to 90 tries, 20 s apart, then a refusal), the reading written
   into the artifact beside the wall.
3. **One call-tier full-suite run** through this slice's driver,
   `sensorium ts run -- npx vitest run`, `SENSORIUM_DIR` on `/mnt/extra`.
   This is the contamination source. Its harness wall and driver wall are
   reported (§3.6), ungated.
4. **After arm:** five plain runs, same command, same guard.
5. **Then, in this order:** the manifest verified again — now the last thing
   that touched the lens is the after arm, which is what the clause is for;
   the marker grep (`grep -rl __srt` over `node_modules/.vite*`, `.vite`,
   `node_modules/.vitest*`, each directory searched written down, so "0
   hits" is never "0 directories"); the wrapper directory
   `node_modules/.sensorium` listed.

### 2.2 The rule

Four clauses, a flat conjunction as E6′ was; a clause that does not hold is a
**STOP**, and the pre-registration carries no other word for it.

| Clause | Measured | Holds when |
|---|---|---|
| manifest identical | `sha256sum -c` after the after arm | exit 0, 748 OK, 0 FAILED |
| the suite is the suite | every plain run's counts | every run reads `372 passed (372)` and `4278 passed (4278)`; a run that does not is **dropped and named**, never averaged in |
| 0 markers | the grep over every cache directory that exists | 0 hits, ≥1 directory searched |
| wrapper gone | `node_modules/.sensorium` | absent |
| **the plain band** | medians of the two arms' walls | `median(after) ∈ [median(before) − range(before), median(before) + range(before)]`, where `range = max − min` over the before arm's usable walls |

**Derivation of the band.** The before arm's own median, plus or minus the
spread the before arm itself measured. No multiplier, no chosen width: the
arm's range is a number the session produced, not one this document picked.
On E1′'s plain arm — walls 22.3136, 22.3252, 22.5925, 22.6142, 22.7221 — that
would read **22.5925 ± 0.4085**. Stated openly: E6′'s single wall, 22.8678,
would sit inside that band; that is not why the band has this shape. The band
is fixed before the after arm runs, from an arm the after arm cannot
influence, and it is the after arm's **median over five guarded runs** that
must land in it — not one wall.

**Fewer than four usable walls in either arm** (dropped runs, guard
refusals) makes the timing clause a **STOP by instrument**: the band or the
median was not measured, and an unmeasured clause is not a held one.

### 2.3 The instrument

`typescript/acceptance/e6pp.sh <lens dir> <manifest> <store dir> <out dir>`
and `e6pp_report.py`. `e6.sh` is **not edited**: the rung-1 record cites it
by name as E6′'s instrument, and an instrument a locked record cites keeps
its text. It gains one header line pointing at `e6pp.sh`.

What the script writes: one JSON line per run into `e6pp.jsonl` — arm
(`before`/`after`), index, load reading, wall, exit status, whether both
count lines were read, vitest's `Duration` line; the call run's line with its
invocation id, harness wall and driver wall; the manifest check's output
(after); the marker grep with its searched list; the wrapper listing. The
report script derives the band, the two medians, the dropped list, and the
five clause verdicts, and `assemble.py` gains an `E6″` block that reads them.

**`assemble.py`'s `loads` list is filtered the way `walls` is.** The
ledger names it as a latent misalignment (`docs/CARRIED-DEBT.md`, the S5
section's instrument notes): a dropped run's load reading stayed in `loads`
while its wall left `walls`. Fixed before E6″ uses that assembler.

### 2.4 Disposition, pre-committed

- **PASS on all five:** E6 is closed for this recorder on this lens; the
  rung-1 spec's §11 entry gets a dated line saying so.
- **STOP on the band with the three contamination clauses clean, again:**
  the number stands; the record declares the mechanism **unknown**; the next
  step is a mechanism hunt (what the after arm does differently — cache
  state, file timestamps, the shape of vitest's own `Duration` breakdown),
  **not a third band**. No re-roll, no averaging with E6′.
- **STOP on a contamination clause:** the recorder left something behind,
  which is a defect in this slice's cleanup path; fix, and the whole session
  runs again as a new pre-registered attempt with its own record section.

## 3. E10′ — the converter ladder, pre-registered

**The question is E10's:** what does conversion cost, on the full suite and
on the one file a debugging loop pays for? The bound is E10's: full-suite
ingest at or under the lens's own plain wall.

### 3.1 The workload, pinned before any code

- **The full-suite set:** `20260909-160038-f08e89` — 372 spools,
  414,450,522 bytes, plus its `invocation.json`, `harness.json` and
  `manifests/` — **copied** from
  `/mnt/extra/sensorium-s5/store-rung1/acceptance/spool/` to
  `/mnt/extra/sensorium-s5/e10-spool/f08e89/`, its `ingested.json` removed
  from the copy, and a sha256 manifest of every file in the copy written and
  committed with the record. Every arm converts a **fresh copy of that copy**
  into a **fresh store**, both under `/mnt/extra`, both outside the timed
  region, exactly as `e10.sh` does now.
- **The one file:** E3-TS's first spool by timestamp,
  `20260909-155657-4965c3/1478098-0.jsonl` — **611,016 bytes**, the size
  E10 reported — copied and pinned the same way. T0 confirms the name and
  the byte count from the copy, and the record quotes both.
- **The reference wall:** **22.5925 s**, E1′'s plain median on this lens,
  the number E10 was read against. Pinned as a constant of the rule, not
  re-measured: the converter's cost is being held to what the suite itself
  costs, and that number is on record.
- **The load guard** every timed repetition waits behind: the same rule as
  §2.1 step 2. `e10.sh` never had one (record §5 gap 5); its successor does.
- **Job counts:** `sensorium ts ingest --jobs N`; the default is
  `os.cpu_count()` = 16 on this box, which is what the driver uses.
- **The instrument:** `typescript/acceptance/e10p.sh <spool copy> <scratch>
  <label> <jobs> [n]` and `e10p_report.py` — `e10.sh`'s shape (a fresh copy
  and a fresh store per repetition, both outside the timed region) plus the
  load guard, the job count as an argument, and the load reading written
  beside every wall. `e10.sh` is not edited (§5).

### 3.2 Arm 0 — diagnosis on main's code

Measured on the T0 commit, **before any converter change**, so the ladder
has a baseline taken under the same guard as its rungs.

| Cell | What | n | Prediction (from §0's profile; to be falsified) |
|---|---|---|---|
| 0a | the largest spool alone, `--jobs 1`, one-spool copy | 3 | ≈ 16 s |
| 0b | the full set, `--jobs 1` | 3 | 40–50 s: the sum of every spool's serial cost plus per-spool setup |
| 0c | the full set, `--jobs 4` | 3 | between 0b and 0d |
| 0d | the full set, `--jobs 16` (E10's own cell, now guarded) | 3 | ≈ 45 s |
| 0e | the one file, default jobs | 5 | ≈ 0.36 s |

**Two readings are pre-stated so the number decides between them.** If 0d
is not well below 0b, the pool buys nothing and the mechanism is contention
or serialisation between workers — A1 is the right first lever. If 0d ≈ 0a,
there is no contention: the floor is the largest spool's own serial cost, and
the lever is the per-record cost (A4), not the write path. Reported, no
verdict.

### 3.3 Arm A — the Python write path, one lever per commit

Each lever is its own commit, measured on the same cells (0a, 0d, 0e) with
the same guard, **against the previous rung's numbers**. The prediction is
written before the code.

**A1 — one transaction per trace, `synchronous=NORMAL`.** `TraceWriter`
gains a `durable: bool = True` constructor argument. With `durable=False`:
`PRAGMA synchronous=NORMAL` (under the `journal_mode=WAL` `create_trace`
already sets), one `BEGIN`, every batch flush and every `set_meta` /
fingerprint write inside it, **one commit in `close()`**, then the rename
into place that `convert` already does. The converter passes
`durable=False`; **the Python recorder keeps the default**, because it writes
traces live and a partial trace is worth keeping there — that is what the
per-batch commit is for, and it stays. This is the Rust converter's own
change transferred, with its own argument: there is no earlier "committed"
state of THIS file a reader could be shown, because the file is renamed into
place only after the commit; `synchronous` below that point buys speed, not
correctness. The contract's "`incomplete` is written true at the start" is
kept literally — the first statement of the transaction — and a build that
dies leaves a temporary file `convert` unlinks, never a visible trace; a
worker SIGKILLed mid-build leaves the dotted `.tmp` trio exactly as today
(R42's path), which `runs` never lists.
*Prediction:* 0a ≤ **13.5 s** (the 2.7 s of commits gone), 0d ≤ 0a + 3 s
(the contention gone with the fsyncs), 0e unchanged.

**A3 — a streaming spool reader.** `spool.read` materialises the whole
file as text and then as a list of dicts — memory linear in spool size, a
limit the ledger declares (`typescript/HONESTY.md` §5, "materialised
whole"). It becomes an iterator the builder consumes once: BOOT must be the
**first** line (the property the module's own docstring states; a BOOT
anywhere else is a refusal naming the line), a second BOOT is refused when
met, the torn tail is detected at the end, and `exit`/`torn_tail` are filled
by the time the builder's `_meta` reads them, which is after the loop. Every
refusal the current reader makes is kept and tested; the difference is that
a mid-file refusal now aborts a build in progress, whose temporary file
`convert` already unlinks.
*Prediction:* wall within noise of A1; the largest worker's peak RSS falls
from the order of a gigabyte to the order of 100 MB. RSS reported, ungated.

**A2 — largest-first dispatch** and **A4 — the per-record Python cost**
(the constant CALL payload `{"args": {}, "unread": ["locals"]}` serialised
once per event, 1.1M times on the largest spool; `_trunc` on every RETURN;
the fingerprint update) are **taken only if A1 + A3 leave 0d above the
bound**, in that order, each measured. If the bound is met after A1, A2 and
A4 are not built: a lever that cannot move a verdict is not free.

### 3.4 The rules

| Clause | Measured | Rule |
|---|---|---|
| **full suite** | the median of **n=5** guarded repetitions of `sensorium ts ingest` at the default job count over the pinned set, on the slice's final converter | ≤ **22.5925 s** → **PASS**, the converter stays Python; above → **REPORTED** with every rung of the ladder (0a–0e and each lever's cells), and Arm B is a later slice by ruling. No STOP word on this clause: E10's rule carried none, and a cost is a fact with its `n` beside it |
| **the one file** | the median of n=5 guarded repetitions over the pinned one-file spool | ≤ **0.3638 × 1.10 = 0.4002 s** → **PASS**; above → **STOP**. A converter faster on the suite and slower on the workload the loop pays is the failure the ledger's E10 row warned about, and it is the one thing on this ladder that is allowed to stop it |
| **equivalence** | §3.5 | 372 MATCH, 0 DIVERGED, 0 REFUSED → PASS; anything else → **STOP** |

### 3.5 The equivalence gate

A converter that is faster and different has changed the trace, and the
trace is the product. The full-suite set is converted twice: once by **main's
converter at the T0 commit** (the tree before any lever) into store A, once
by **the slice's final converter** into store B, both from fresh copies. The
372 traces are paired by spool file name (each `run:` line prints its
`file:`), and `sensorium diff <A> <B>` runs once per pair. **372 MATCH, 0
DIVERGED, 0 REFUSED**, or STOP. The same spool goes in on both sides, so the
lens's eight nondeterministic test files cannot excuse a DIVERGED here: a
difference is the converter's. Reported beside it, ungated: per-table row
counts equal for every pair (`events`, `frames`, `tasks`, `code_objects`,
`fingerprints`, `task_fingerprints`, `output`), and the meta keys that differ
between the pairs are exactly the minted ones (`run_id` and what derives from
it).

### 3.6 Reported without a gate

The events-per-second of the largest spool under each rung; the peak RSS of
the largest worker before and after A3 (`resource.getrusage(RUSAGE_CHILDREN)`
around the subprocess); the parallel speedup 0b/0d; the harness wall and
driver wall of §2.1's call run — the driver wall is the number that climbed
45.0 → 70.3 s across rung 1's five call runs (record §5 gap 13), and the
slice's driver, which converts inline, is read once more on a fresh
recording; and the full-suite ingest of **that fresh spool set** as a second,
uncontrolled reading beside the pinned one.

### 3.7 What was dropped, and on what number

**Arm C, the binary wire, is not on the ladder.** In the §0 profile, JSON
decoding is ≈4.9 s of 31.78 s profiled — about 15%. A wire with zero parse
cost could remove at most that share, and the gap to close is a factor of
two. A wire change would also open `docs/TRACE-FORMAT.md` (at 799 of 800
lines) and every reader of the spool. If Arm 0's cells falsify the
contention reading — 0d ≈ 0a with the residual inside the parse — this
paragraph is the first thing the record revisits, with the new number beside
the old.

## 4. The `node --test` extensions

### 4.1 H1 — Node strips; the hook erases nothing

`typescript/src/hook.mjs` returns, for an ES-module result,
`{ format: loaded.format, source: <instrumented, still typed>, shortCircuit:
true }`. `transpileModule` and the `STRIP` set are deleted; the consumer's own
TypeScript stays `require`d, because the transform parses against it (that
was never the stripper's). Node then strips
`module-typescript` sources with the same stripper plain `node --test` uses
— the one that already loads the consumer's `.ts` when nothing of ours is
present — and hands `module` sources through. `.mts` is therefore stripped
(closing the residual), and a construct Node's strip-only mode rejects
(`enum`, `namespace`, parameter properties) fails **identically** plain and
hooked, with Node's own error, which is the R37 principle carried one step
further: Node decides the format **and** the erasure. A consumer running
under `--experimental-transform-types` gets exactly that, where the old hook
overrode it.

The transform's own header is an `import`, and it inserts no syntax that
strip-only mode rejects; the probe with the enum control (§4.5) is the
falsifier.

### 4.2 H2 — no JSX under `node --test`

`.tsx` and `.jsx` throw `ERR_UNKNOWN_FILE_EXTENSION` inside `nextLoad`
before any `load` hook runs. **The hook carries no JSX.** A recorder that
made an unloadable file loadable would be changing the program, which is the
one thing this recorder promises not to do. HONESTY §7 states it as: such a
file is **outside Node's own scope** under `node --test` — not an exclusion
of ours and not counted, because the hook never sees it. A probe asserts the
loader's error reaches the consumer unchanged (§4.5). `classify()` still
names `.tsx`/`.jsx` eligible — that is the vitest plugin's scope, unchanged.

### 4.3 H3 — the no-spool refusal names the exclusions (R45)

When `ingest_dir` finds no spools, it reads the invocation's tallies
(`<spool>/manifests/_tally.json` and every `_tally-<pid>.json`). If they
exist and every one reads `files_transformed: 0` with a non-empty
`excluded`, the refusal says so:

> no spools in `<dir>`: this run transformed 0 files and excluded N as
> CommonJS (`commonjs: N` across k tallies); this recorder instruments ES
> modules only, so a CommonJS-only suite records nothing

Exit **2**, as today. Where the tallies show transformed files and still no
spool, or no tally at all, today's sentence stands — a different thing went
wrong and the converter does not guess which. The wrapper's own refusal
(R41) keeps first place.

### 4.4 H4 — citations by function (R47)

`docs/CARRIED-DEBT.md`'s `hook.mjs:98` becomes `hook.mjs` `load`. H1 moves
those lines again, and a line number in a ledger is a citation that goes
stale on the next edit; a function name is not.

### 4.5 Probes and the checker

Under `typescript/probes/nodetest/`, one test file per extension, run by
`npm run probe:nodetest` as an explicit file list (Node's default test
patterns are not relied on):

| File | Expected |
|---|---|
| `async.probe.test.ts` | as today: a spool, its tasks, the checker's async checks |
| `ext.probe.test.mts` | a spool with ≥1 task, types stripped by Node, `task_name_basis: lexical` |
| `ext.probe.test.mjs` | a spool with ≥1 task |
| `ext.probe.test.cjs` | **no spool** for that pid; its `_tally-<pid>.json` reads `files_transformed: 0`, `excluded: {commonjs: 1}` |

And two **controls**, not test files, run by `probes/nodetest/controls.mjs`
twice each — plain `node <file>` and `node --import ../src/register.mjs
<file>` with `SENSORIUM_TS_ROOT` and `SENSORIUM_TS_PKG` set, since
`register.mjs` refuses without them — comparing the error code strings:

| Control | Expected on both sides |
|---|---|
| `controls/enum.ts` | `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX` |
| `controls/jsx.tsx` | `ERR_UNKNOWN_FILE_EXTENSION` |

A mismatch between the two sides is a refusal from `controls.mjs` — the
recorder changed what loads. `check.mjs`'s nodetest mode gains one check per
row above. `tests/test_ts_live.py` drives the same directory through the
driver, and gains the R45 case: a root whose only test file is `.cjs`
refuses at exit 2 with §4.3's sentence.

## 5. Decisions recorded without work

- **The describe-chain join stays ` > `.** The record's §5 gap 10 raised
  whether §3.4 should emit vitest's JSON reporter's space-joined `fullName`.
  Decided: no. ` > ` is vitest's **own console spelling** for nested names —
  what the consumer sees in a failing test's header — and the JSON reporter's
  join is that reporter's. E9's rule attaches nothing to it either way.
- **`e6.sh` and `e10.sh` are not edited.** Each is the instrument a locked
  record cites; each gains a header line naming its successor
  (`e6pp.sh`, `e10p.sh`).

## 6. Testing story

- **The writer's non-durable mode.** Unit tests hold that a trace finalized
  with `durable=False` is identical in every table and every meta key to one
  finalized with `durable=True` from the same records, on the ten
  `tests/fixtures/ts-spools/` fixtures; that `synchronous` reads `1`
  (NORMAL) and `journal_mode` reads `wal` on the open connection (the Rust
  writer's own test, transferred); that an abort mid-build leaves no `.db`;
  and that the Python recorder's writer still commits per batch: the
  existing writer tests pass unchanged, and if none of them pins the
  per-batch commit, one is added that reads a partial trace back after a
  flush with no `close()`.
- **The streaming reader.** Every refusal `spool.read` makes today has a
  test; each is re-pointed at the iterator, and two are added: a BOOT on
  line 2 (refused, naming the line) and a second BOOT met late (refused;
  the temporary file gone). Peak RSS is an instrument number, not a test.
- **Mutation checks** on `writer.py`'s new branch and the reader, with the
  two gotchas from memory applied: `PYTHONDONTWRITEBYTECODE=1` and
  `__pycache__` purged between mutants, and every mutant run under `setsid`
  and killed by process group on timeout.
- **The hook.** `typescript/test/hook.test.mjs` gains: an ESM `.ts` result
  keeps `format: 'module-typescript'` and is still typed on return; a
  `module` result is returned as `module`; CommonJS formats are excluded and
  counted unchanged. The probes and controls (§4.5) run in CI's `typescript`
  job.
- **Unchanged and re-run:** the full pytest suite, `npm --prefix typescript
  test`, `npm --prefix typescript run check` (R4: never `npx tsc -p` from the
  root), the corpus (`--only-dir typescript --require-driver` and
  `--only-dir .`), the live suite. No trace key moves, so no vector changes.

## 7. Order of work

Subagent-driven in a worktree under `/mnt/extra/sensorium-rung2/`, as rung 1
was; a plan (writing-plans) carries §2.2, §3.4, §3.5 and §4.5 **verbatim**.

- **T0 — pre-registration, locked by commit before any code.** The record
  `docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md` §1: every
  rule above, the Arm 0 predictions, the ambient pins (node, vitest, vite,
  jsdom, governor, cores, RAM, filesystem, the global tool's version, the
  git rev), the spool copies made and sha-pinned, the rung-1 manifest
  verified once.
- **T1 — Arm 0** on the T0 tree, all five cells, into the record's §3.
- **T2 — A1**, tests first, then its three cells.
- **T3 — A3**, tests first, then its cells and the RSS numbers. A2/A4 only
  by §3.3's condition.
- **T4 — the equivalence gate** and E10′'s two verdict clauses.
- **T5 — the hook** (H1, H2), the probes and controls, the checker, the
  live test; then H3 and H4.
- **T6 — E6″**: `e6pp.sh`, the report, the assembler block and the `loads`
  fix; then the session, run last.
- **T7 — documents** (§8), the rung-1 spec's §11 dated line, the ledger's
  section under its own cut rule, the CHANGELOG entry, the versions.
- **T8 — final review** (fable, whole branch), one fix wave, PR for Brice.

## 8. Versions, ceilings, documents

- Python **0.9.1**: the converter's write path and reader, the R45 refusal.
  `sensorium-ts` **0.1.1**: the hook. `TRACE_FORMAT` stays **4**; no vector
  moves; `docs/TRACE-FORMAT.md` (799/800) is not opened.
- **Ceilings** (`tests/test_ceiling.py`, 800 lines, records exempt):
  `README.md` is at 782 — its TypeScript section takes **at most one
  sentence**, or none; `typescript/HONESTY.md` (673) takes dated amendments
  in §5 (memory no longer linear), §7 (Node strips; JSX outside Node's
  scope; the R45 sentence) and §9 (E6″ and E10′'s numbers once measured);
  `docs/CARRIED-DEBT.md` (415) gets this slice's section, measured against
  the ceiling before it is written, the oldest section cut first if needed.
- `typescript/README.md` describes the hook as it now is.
- `CHANGELOG.md` gains `0.9.1 — sensorium-ts 0.1.1` with the verdicts as
  measured, the STOP word used wherever the record uses it.

## 9. Decisions, with what each costs if wrong

| # | Decision | Cost if wrong |
|---|---|---|
| S1 | E6″'s band is the before arm's median ± its own range, no multiplier | a before arm with an unusually tight range produces a false STOP; §2.4's disposition handles it without moving the band |
| S2 | The before arm is taken in the same session as the after arm, not borrowed from E1′ | eleven guarded suite runs (≈ 15 min with guard waits) instead of six; buys a reference under this day's box state |
| S3 | E6″ runs last in the slice | the session exercises this slice's recorder; a cleanup defect found there costs a second session (§2.4) |
| S4 | E10′'s reference wall is E1′'s 22.5925 s, pinned, not re-measured | if the box is slower this week the bound is harsher than "the suite's own wall today"; the number is on record and the comparison is stated |
| S5 | Arm 0 is measured on the T0 tree before any lever | a day of instrument time; buys a baseline under the same guard the levers get |
| S6 | A1 transfers the Rust converter's fix (`durable=False`: one transaction, NORMAL) rather than `journal_mode=OFF` + an explicit fsync | the WAL doubles the largest trace's write (≈ 330 MB once more on NVMe, well under a second); if A1's residual is the write itself, `journal_mode=OFF` is the next lever, recorded then |
| S7 | The Python recorder keeps per-batch commits | none: the two writers want different things and now say so with one argument |
| S8 | A3's reader requires BOOT on line 1 | a spool with BOOT elsewhere converted before and is refused now; the runtime writes BOOT first by rule (rung-1 R-rulings), so none exists |
| S9 | A2 and A4 are conditional on A1 + A3 missing the bound | a faster converter than the bound requires is not built; the numbers say what was left |
| S10 | Arm C dropped on the profile's 15% | if Arm 0 falsifies the contention reading, §3.7 is revisited with the new number |
| S11 | The hook returns Node's format and erases nothing | a consumer whose `.ts` uses non-erasable syntax under `node --test` was already failing plain; matched behaviour, by test |
| S12 | No JSX in the hook | none for any suite that runs plain; a consumer wanting JSX under `node --test` needs a Node feature, not a recorder feature |
| S13 | The R45 sentence fires only on `files_transformed: 0` with a non-empty `excluded` | a partial CommonJS suite with a real recording failure keeps today's sentence — which is correct: the converter does not guess |
| S14 | The one-file clause is the ladder's only STOP | the suite bound reports, the loop's workload gates: a rewrite that helped the wrong workload cannot ship |

## 10. Rulings from Brice

Scope, merges, money, destructive actions only.

1. **Ruled 2026-09-10:** Arm B stops at the report; a Node converter is a
   later slice.
2. **Owed, destructive order:** the spool-set copy (§3.1) is made and
   sha-pinned **before** `/mnt/extra/sensorium-s5/store-rung1` and
   `acceptance-rung1` are freed; the lens copy `/mnt/extra/sensorium-s5/vtt`
   stays through E6″.
3. **Owed:** merge of this design PR, then of the slice.

## 11. The pre-registration, in one table

Carried verbatim into the record's §1 at T0 and byte-locked there.

| Id | Question | Measurement | Rule |
|---|---|---|---|
| E6″ | Is a plain run contaminated? | five guarded plain runs, one call run, five guarded plain runs; manifest after; markers; wrapper | manifest 748 OK / 0 FAILED; every run 372/4278 or dropped and named; 0 markers with ≥1 directory searched; wrapper absent; `median(after)` inside `median(before) ± range(before)`; <4 usable walls in an arm → STOP by instrument; any clause failing → STOP |
| E10′-suite | What does full-suite conversion cost? | n=5 guarded `ingest` at default jobs over the pinned f08e89 copy, final converter | ≤ 22.5925 s → PASS (Python stays); above → REPORTED with the whole ladder; Arm B deferred by ruling |
| E10′-file | What does one file cost? | n=5 guarded `ingest` over the pinned 611,016-byte spool | ≤ 0.4002 s → PASS; above → STOP |
| E10′-eq | Did the converter change the trace? | 372 pairs, main@T0 vs final, `sensorium diff` each | 372 MATCH / 0 DIVERGED / 0 REFUSED → PASS; else STOP |
| E10′-0 | Where do the seconds go? | Arm 0 cells 0a–0e on the T0 tree | reported against §3.2's predictions; no verdict |
| H-probes | Does `node --test` load what plain loads? | §4.5's four files and two controls | every row as its table says; a control mismatch → STOP |
