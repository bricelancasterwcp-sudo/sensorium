# The TypeScript recorder's honesty ledger — §12: refocus

Section 12 of [`typescript/HONESTY.md`](HONESTY.md), **written here 2026-09-13
(S5's refocus slice) because that file stands five lines from its 800-line
ceiling and has no room for it**. The precedent is
[`../rust/HONESTY-REFOCUS.md`](../rust/HONESTY-REFOCUS.md), split from
`rust/HONESTY.md` 2026-09-08 for the same reason, and this ledger's own two
splits before it — [`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md)
(§10, 2026-09-10) and [`HONESTY-COST.md`](HONESTY-COST.md) (§9, 2026-09-11).
Rust's §13 was MOVED and its wording preserved; this one was never in
`HONESTY.md` at all, so nothing here has been re-worded and `§12` names this
section from the day it was written — including from the ledger's index,
which cites `§n` as an identifier.

## 12. Refocus: the recorded invocation, run again one flag deeper

Added 2026-09-13 by S5's refocus slice
(`docs/superpowers/specs/2026-09-13-sensorium-s5-refocus-typescript-design.md`,
rulings R1–R12 with P3, P9, P11 and P12). `sensorium refocus <run> --focus
<spec>` answers on a TypeScript trace instead of refusing, and this section is
what that answer may mean. **None of it is a claim that the two runs were the
same run**: §12's whole subject is a pair of executions and what comparing
them does and does not establish.

**What is re-run is the whole recorded INVOCATION, not a narrowed one**
(ruling R1). A vitest invocation is a pool: `npx vitest run src/config` starts
a harness that starts as many worker containers as it likes, each recording
its own trace, and a harness cannot be asked for one container without
changing what it does. So `refocus` re-runs `harness_command` verbatim, from
the `harness_cwd` the original recorded, under the original's store, with
`--refocus-of <run>` first and unconditional, then the ORIGINAL's recorded
tier, then the original's `meta.focus` followed by the values this call added
— a refocus only ever captures MORE, never differently. It runs
`sys.executable -m sensorium`, never a `sensorium` on `PATH`: a name on the
path could resolve to another version, and a pair compared across two
recorders is the one thing the verdict may not rest on. **Seven questions are
asked BEFORE anything is launched**, each answering at exit 2 with `nothing
was re-run` in it: `--window` was given; the original was recorded at
`--tier off`; it records no `harness_command`; it records no `harness_cwd`
(`sensorium ts 0.13.0` or earlier); that directory is gone; the project `root`
is gone; the container was a reused worker (below). A suite costs minutes and
has side effects of its own, so nothing about it is attempted speculatively.

**The pair is found in the store, never parsed out of what the driver
printed** (ruling R3). The driver stamps `refocus_of` into every trace of the
new invocation; Python then asks the store which traces carry that link and
started at or after the launch — a trace whose `start_ts` is unreadable is
EXCLUDED rather than assumed recent, because it cannot be shown to be this
re-run's. The driver's `run:` lines print to the terminal and decide nothing:
a load-bearing link that lived only in this process's memory would break
silently the day a print changed.

**Linked is not PAIRED, and that is this recorder's own problem** (ruling R4).
A suite of 372 test files re-runs as 372 linked traces, of which the reader
asked about one. The key that picks it is the container's `test_file` where it
ran one, its whole `argv` where it ran none — a `node --test` process, a
script — and a key of its own, matching nothing, for a reused worker, so a
container that ran several files cannot pair with an argv-keyed original
through the back door of the re-run. Exactly one candidate is the pair. Zero
is `verdict: REFUSED` after the rerun at exit 3, naming how many WERE linked
and the harness's exit, so a reader can tell a suite that never ran from a
suite that ran without this container; more than one is REFUSED by count,
because two containers of one invocation claiming one test file is a fact
about the harness this tool will not guess through. **The rest are SIBLINGS**:
re-executed, never compared, counted on the pair line
(`siblings in the re-run: 371 (not compared; UNVERIFIED)`), stamped as
`refocus_siblings` — the COUNT, not the ids, because the invocation id already
names them — and listed by `runs` as `verdict:UNVERIFIED`, which is exactly
what they have. Blind spot 40 is that bound stated on its own.

**The verdict is about call shape and nothing else.** `diff_cmd.compare` is
unchanged, in all three languages: a TypeScript pair compares per task — the
main stream is what ran in no test, and every test is a task named by its own
title — as an order-independent multiset over CALL, RETURN, RAISE and
HANDLED. **A LINE row never enters the hash**, which is what lets the deeper
re-run MATCH the run it came from at all. MATCH, DIVERGED and REFUSED keep the
meanings and the exits (0 / 1 / 3) the README's `refocus` section gives them,
and three verdict vocabularies for one question is how three recorders would
come to disagree about what MATCH means.

**A reused worker is nobody's pair, and the refusal reads the trace's own
frames** (ruling P3 amending R4, at `4a9b0a7`). A container that ran two test
files cannot be paired at all: which container of a re-run would be its pair
is the harness's scheduling, not a fact. The count is read TWICE and the
larger decides — the converter's `test_files` where it declared any, and
always the trace's own task ROOT frames, depth-0 frames whose call ran inside
a task, counted by the distinct code-object files whose basename carries
`.test.` or `.spec.` (vitest's own default `include` infixes). Both readings,
because under `--no-isolate` the converter records `test_file` singular and
never the plural key — the driver-written setup file's top-level `fileStart`
runs once under a shared module cache — so a reading that trusted the meta key
alone would miss the very shape this refusal exists for, and a converter that
under-reports must not be able to mask what the frames plainly show. **The
bound is blind spot 42**, and it claims LESS rather than more: a second file
whose callbacks all root in a shared helper is invisible to the frame reading,
so that container is not refused — it pairs by its first file, and the
comparator then reads DIVERGED at a named step or a MATCH of the container's
shape, never a guess.

**The licence beside the verdict is an enumeration**, and on a TypeScript pair
three of its checks cannot run at all. Source runs for real: the container's
`source_hashes` are absolute, so they re-hash from any directory and a changed
file is known before a suite is spent on it. The environment runs for real,
over the two traces' own recorded `env` and never this CLI's, under §3.3's two
sets. The **exit** runs for real (ruling R9), on the two endings somebody
observed. `output`, `children` and **`threads`** are printed and stamped
`unverifiable` rather than compared, because `capabilities.output`,
`capabilities.children` and `capabilities.threads` are all `false` on a
TypeScript trace and comparing them would compare empty sets and report
agreement — the named bug class. **An unverifiable check is never counted as a
verified one**; the two counts are two numbers and are never summed. `threads`
is the new one: until this slice the thread block's declared-false witness gap
was appended as a CAVEAT, which withheld every TypeScript licence for a check
that could not run — a clause that cannot not fire is not a finding.

**The environment's exemptions are named on the line, never hidden behind a
count** (ruling P12). Every key starting `SENSORIUM_` is the RECORDER's own
bookkeeping and is taken out of the compare, and that is not optional here:
`SENSORIUM_INVOCATION` is minted per invocation, and `SENSORIUM_SPOOL` and
`SENSORIUM_MANIFEST_DIR` both derive from a fresh spool directory, so three of
the seven differ on EVERY refocus by construction — and `SENSORIUM_FOCUS`
differs whenever the call deepens the focus, which is what a refocus is for
(`refocus_cmd._merged_focus` appends only what is not already there, so a call
that merely repeats the original's own `--focus` leaves it identical).
**Harness set 1** — `VITEST_POOL_ID` and `VITEST_WORKER_ID`, the pool's own
slot bookkeeping, exact membership and not a prefix — is counted, named and
never withholds, in session set 1's words and versioned in the same way, so a
key found to bear on what a program computes can leave the set with a date. The
line a granted TypeScript pair prints, whole:

    env: unchanged outside harness set 1 (<N> variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; 2 harness variable(s) differ: VITEST_POOL_ID, VITEST_WORKER_ID)  the recorder's own, also not compared: SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_MANIFEST_DIR, SENSORIUM_SPOOL, SENSORIUM_TIER, SENSORIUM_TS_PKG, SENSORIUM_TS_ROOT

It reads `outside session set 1 and harness set 1` where a session key differs
too. Everything the two sets do not cover withholds exactly as it does on a
Python or Rust pair: this tool cannot know which variables a program reads, so
the default stands and each enumerated exception has to earn its place.
**Harness set 1 is not compared, and blind spot 41 says so**: a program that
really did read its worker slot would not be caught by this licence.

**The exit clause reads the ending somebody WAITED for** (ruling R9). A vitest
worker is killed by its pool, so the container's own `exit_status` is `null`
with basis `unwitnessed` on every trace this recorder writes — the shared
licence clause over `exit_status` therefore compares null with null, reads
equal, and is SILENT, and silence in a licence check reads as agreement. The
branch compares the two endings that were really observed instead:
`harness_exit`, which the driver waited for and which alone carries a basis,
and `exit_self_reported`, the container's own word on the way out. They answer
different questions, so both are compared: a pair whose harnesses agree and
whose containers do not ran the same suite to the same total and killed one
worker differently. An ABSENT record is a caveat naming its side and never a
fact — "not recorded" is not "ended the same way" — and where both agree the
licence carries ONE fact, `harness exit equal (0, waited); container endings
equal`, because a reader told the answer twice has to work out whether it is
the same answer.

*What says it in the trace*: `meta.harness_cwd`, the directory the command was
typed in, which is what made the re-run possible and whose absence is the
fourth refusal; `meta.refocus_of`, the durable link the pair lookup reads;
`meta.refocus_siblings`, the count of containers re-executed and compared to
nothing, stamped even at 0 so an absent key means "written before the count
existed" and never "no siblings"; `meta.refocus_licence_unverifiable`, the
three checks that could not run, stamped so `info` replays them beside the
licence rather than leaving a later reader to infer that everything else was
checked and failed; and the stamps `refocus_verdict`, `refocus_diverge_*`,
`refocus_refused_reasons`, `refocus_licence`, `refocus_licence_reasons` and
`refocus_licence_verified`, which are what make a verdict outlive the terminal
it printed in.

*Falsified by* **E15**
(`docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md`,
§1 pre-registered before the instrument existed, over 31 members of one real
invocation of somebody else's suite): **H1**, that every original refocuses
without a pre-rerun refusal; **H2**, that every re-run completes with the
harness exit the original had; **H3**, the pairing — exactly one candidate by
`test_file` and a linked count equal to the invocation's member count, a
REFUSED from the lookup being a STOP; **H4**, MATCH on the expected list;
**H5**, what the licence says, with the recorder's set named on every line,
harness set 1 counted where it differs, the three checks UNVERIFIABLE and **0**
licence lines claiming an unverifiable check as verified; **H6**, that the loop
closes — a `watch` read on the refocused trace answering the question the
original could not; **H7**, a planted edit read as `source: CHANGED` with the
licence WITHHELD; **H8**, a refusal (`--window`) leaving the store's trace
count unchanged; **H9**, the cost, reported and gating nothing; **H10**, that
nothing else moved. Every number is *measured at Task 8*. Also by
`corpus/typescript/refocus_match` (MATCH at exit 0, the licence GRANTED, the
sibling count, the three unverifiable check lines and — of the four blind spots
— the whole-invocation one, through the real driver; all four, in order, and
the retired `arguments are not read` line's absence, are pinned over a
transcript by `tests/test_refocus_typescript_licence.py`
(`test_the_four_blind_spots_are_printed_in_order_and_the_retired_one_is_gone`)),
`corpus/typescript/refocus_diverged` (DIVERGED at exit 1, parting `at causal
step 4:`) and `corpus/typescript/refocus_refused_reused_worker` (the seventh
refusal, and a `runs` listing proving the store was left alone); and by
`tests/test_refocus_typescript.py`, `tests/test_refocus_typescript_licence.py`
and `tests/test_refocus_world_threads.py` on fixture traces. **A MATCH on a
pair whose per-task fingerprints differ** would falsify it, and so would **a
verdict issued against a trace the store cannot show carries `refocus_of`** —
the failure ruling R3 exists to prevent.

*What a MATCH on such a pair does NOT license.* It says nothing about the
**siblings**: they were re-executed and compared to nothing, and `UNVERIFIED`
is the whole of what is claimed for them (blind spot 40). It says nothing
about the **values** the two runs computed — the fingerprint is call shape,
and two runs can take the identical path over different data. It says nothing
about the **second file of a reused worker**, because a reused worker is
refused outright, and nothing about the second file of a container whose extra
test rooted in a helper, which pairs by its first file (blind spot 42). And it
says nothing about the worker-slot variables the environment check exempted
(blind spot 41), about program output, forked children or worker threads,
whose checks could not run at all, or about the cost: the whole suite ran to
answer about one container of it (blind spot 43).
