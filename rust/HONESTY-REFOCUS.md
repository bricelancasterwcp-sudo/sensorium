# The Rust recorder's honesty ledger — §13: refocus

Section 13 of [`rust/HONESTY.md`](HONESTY.md), **moved here 2026-09-08 (the
recorder's footprint, rung 4 slice 4) so that file stays under 800 lines**.
The focus tier named §11 as its split and took it
(`rust/HONESTY-ERR-FLOW.md`); no split was named after that, so this one is
chosen here rather than discovered at the ceiling: §13 is now the largest
section and the most self-contained — its whole subject is a pair of
executions and what comparing them does and does not establish — and moving it
leaves room for the sections this slice and the rung after it will add. **The
wording and order are unchanged**, so `§13` still names what it always named,
one file away — including from the code comments and the ledger's index, which
cite `§n` as an identifier.

## 13. Refocus: the recorded command, run again one flag deeper

Added 2026-09-07 by rung 4, slice 2
(`docs/superpowers/specs/2026-09-07-sensorium-rung4-refocus-design.md`,
rulings G1–G3 with amendments B1 and B2). `sensorium refocus <run> --focus
<name>` answers on a Rust trace instead of refusing, and this section is what
that answer may mean. **None of it is a claim that the two runs were the same
run** — §13's whole subject is a pair of executions and what comparing them
does and does not establish.

**What is re-run is the RECORDED command, never a command the reader
retyped.** `refocus` takes the original trace's own `cargo_args`, runs them
from the `workspace_root` that original recorded, under the same store, with
`--refocus-of <run>` first and unconditional, then the original's recorded
tier, then the original's `meta.focus` followed by the values this call added
— so a refocus only ever captures MORE, never differently (design §2.3). Five
questions are asked BEFORE anything is launched, and each answers at exit 2
with `nothing was re-run` in it: `--window` was given; the run is one of *n*
processes of its invocation (test binaries and doctests), so no single trace
is the answer; the trace records no `workspace_root`; that workspace is gone;
there is no `cargo-sensorium` to re-run with. A re-run has side effects, so
nothing about it is attempted speculatively.

**The pair is found in the store, never parsed out of what the driver
printed** (ruling G3). The driver stamps `refocus_of` into every process of
the new invocation; Python then lists the traces carrying that link whose
recording started after the launch. ~~Exactly one is the pair.~~
**Corrected 2026-09-07** (design 2026-09-07 §3, ruling R2, at `d4cccd9`): not
every linked trace is a CANDIDATE. A test that spawns an instrumented program
writes a second linked trace, and counting it made the lookup say "more than
one" about a re-run that produced one answer. A linked trace whose `ppid` is
ANOTHER linked trace's `pid` is a **child run** — excluded from the pair, named
on the pair line as `child runs excluded from the pair: <ids>`, stamped as
`refocus_children`, and still listed by `runs`, so a child that is itself the
interesting process is unpaired rather than lost. Exactly one CANDIDATE is the
pair. Zero — the driver
refused, cargo failed before recording, the invocation produced nothing — is
`verdict: REFUSED` after the rerun at exit 3, carrying the driver's exit ~~and
its last stderr line~~. **Corrected 2026-09-07** (design amendment B3): the
child's stderr is STREAMED and never captured — a focused rebuild's progress
belongs to the person waiting for it — so there is no last line to carry. The
refusal names the exit and points at what already printed: `the re-run
produced no trace linked to <run> (driver exit <n>); see the driver's output
above`. More than one is REFUSED by count, and that refusal carries the same
`child runs excluded from the pair:` clause, because a count of the candidates
alone would otherwise describe two of the three traces the re-run really wrote.
Neither case guesses.

**The verdict is about call shape and nothing else.** `diff_cmd.compare` is
slice-1's, unchanged: for a Rust pair the fingerprint is per task — a test, or
a spawned thread — over CALL, RETURN, RAISE and HANDLED, and **a LINE row
never enters the hash**, which is what lets a deeper re-run MATCH the run it
came from at all. Tasks are compared as an order-independent multiset of
`(name, hash)`, so which worker of a pool served which request is not a
difference; MATCH, DIVERGED and REFUSED keep the meanings and the exits (0 /
1 / 3) the README's `refocus` section gives them.
*What says it in the trace*: `meta.refocus_of`, the link; `meta.workspace_root`
and `meta.invocation_processes`, the two facts three of the five refusals are
read from; `capabilities.refocus`, true for every trace this driver converts —
whether one PARTICULAR trace can be refocused is a refusal, not a capability;
and the stamps `refocus_verdict`, `refocus_diverge_*`,
`refocus_refused_reasons` and `refocus_licence*` written into the NEW trace's
meta, which is what makes a verdict outlive the terminal it printed in.

*Falsified by* **E4 H3**
(`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md` §4: **61 of
61 MATCH**, 0 DIVERGED and 0 REFUSED over every `#[test]` of the seven
`pager_*_test.rs` files of a workspace nobody wrote this recorder for, one
test at a time under `--exact`, against an expected-MATCH list written and
byte-locked before the instrument existed); by `corpus/rust/refocus_match`,
`corpus/rust/refocus_diverged` and `corpus/rust/refocus_refused_many`, which
pin the three outcomes through the real driver; and by
`tests/test_refocus_rust.py` on fixture traces. A **MATCH on a pair whose
per-task fingerprints differ** would falsify it, and so would **a pair not
linked by `refocus_of`** — a verdict issued against a trace the store cannot
show came from this re-run is the failure this design's G3 exists to prevent.

**The licence beside the verdict is an enumeration**, and ~~on a `cargo test`
pair it is never granted~~ — **corrected 2026-09-07** in the next paragraph.
Source and environment are checked for real (`source_hashes` re-hashed now; the
two traces' recorded `env` compared key by key, with a target directory that
MOVED read as a relocation rather than as a change — the rule below), and
so is the recorded process exit; `output` and `children` are printed and
stamped **`unverifiable`** rather than compared, because `capabilities.output`
and `capabilities.children` are `false` on a Rust trace and comparing two
empty sets would read as agreement — the named bug class (design §3.2). An
unverifiable check is **never counted as a verified one**; the two counts are
printed as two numbers and never summed. E4 measured that at n = 61: source
61 of 61, environment 61 of 61, exit 61 of 61, output and children
UNVERIFIABLE 61 of 61, and **0 licence lines claiming an unverifiable check as
verified** (record §3, §4 H4). ~~What the same run also measured is that the
printed WORD was **WITHHELD on all 61** — the licence's untraced-thread clause
fires on every `cargo test` trace, because libtest runs each test on a thread
it spawns (thread counts 57×1, 1×2 and 3×5 across the 61 pairs). That is a
design question about what "the program's threads" means on a test harness,
recorded as a finding in that record's §5.2 and carried to
`docs/CARRIED-DEBT.md`; it is not applied here and no promise above depends on
it.~~

**Ruled and applied 2026-09-07** (design 2026-09-07 §2, ruling R1, at
`11b7e8a` with `d9115a5`): a NON-MAIN thread whose ROOT frame's site the
manifest marks `#[test]` is the **harness thread** — libtest's own, not the
program's — and it comes out of the licence's untraced-thread counts and is
**named wherever one of those counts is printed**, never quietly dropped: a
smaller number where a larger one used to be, with nothing on the line to say
why, is a number that looks measured standing in for a fact that was removed.
The words are the recorder's own — a count it joins reads `and 1 harness thread
(libtest's per-test thread, excluded as the recorder's own)`, and on a line
counting what was NOT compared the same fact takes a slot of its own,
`; 1 harness thread (…) is not among these counts`. The rule is
**ROOT-MARK-ANCHORED**, a BOUND and not soundness in both directions: a thread
the PROGRAM spawns whose first instrumented frame is itself a `#[test]`/
`#[bench]` fn is read as harness and subtracted, so the licence can be
**GRANTED** over a program thread. Blind spot **28** states the bound in full,
with the other end and the ruled fix. The set is empty where sites carry no
marks at
all — every Python trace — and empty unless the main thread is a RECORDED fact,
because subtracting on a guess is the one way this rule could take a thread out
of a count it was never in. Both empty cases leave every count as it was, the
direction that claims less.

*Measured by* **E4′** (`…/2026-09-07-sensorium-rung4-e4p.md`), whose expected
partition — which of the 61 pairs read granted, which stay withheld, by name —
was byte-locked before the instrument existed. **H1 STOPPED**: granted **0** of
61 where §1.2 predicted 57. The record's §4 says why the STOP is not R1's — the
exclusion is named on **61 of 61** `threads:` lines in one spelling, the four
pairs §1.2 named report the program's own counts **1, 4, 4, 4** (E4's raw
2, 5, 5, 5 less the one harness thread), and no WITHHELD reason failed to
subtract. What withheld all 61 was the **env** clause on one key,
`RUSTDOCFLAGS`, whose driver-injected `--extern sensorium_rt=…` rt-hash
fragment moved because the originals were recorded by driver 0.5.0 and re-run
by 0.5.1: the recorder's own footprint read as the world's, the bug class this
rule had just closed one check along. R1 is exercised and unfalsified; H1's
question is **unanswered**, ruled to the next slice (strip the fragment as the
recorder's own, re-measure as E4″). *Also falsified by*
`corpus/rust/refocus_match`, the two thread cases and
`tests/test_refocus_rust.py`: a harness thread found on a Python trace, or a
program thread taken out of a count as though it were the harness's, would
falsify it. On a `cargo run` pair there is no harness thread at all and the
licence IS granted, which `corpus/rust/refocus_match` pins over exactly four
points.

**A target directory that MOVED is the same world, and is named as one.** A
refocus re-runs the program under whatever `CARGO_TARGET_DIR` the caller has,
and cargo hands the test binary four variables that embed the root
(`CARGO_TARGET_DIR`, `CARGO_BIN_EXE_*`, `LD_LIBRARY_PATH`, `RUSTDOCFLAGS`), so
a re-run from a fresh target differed on all four and withheld the licence for
it. **Nothing is excluded by name** (design 2026-09-07 §2, Task 5b, at
`1a76757` with `d43b7aa`): excluding those four would let a program really
handed one extra directory on the loader's path earn a full licence. Each
DIFFERING key is asked one question instead — does the difference disappear
when the original's target root is rewritten to the re-run's? — compared entry
by entry down a `PATH`-like list, because a list that gained or lost an entry
is a change however the rest reads, and anchored at path boundaries on both
sides, so a sibling directory is not read as the root relocated. If it does,
the key is NAMED and the licence still holds: `N variable(s) differ only by the
target directory: <names>; treated as unchanged`, printed on the env line and
kept in the trace even where the licence is withheld for another reason, so
`info` never replays a licence whose terminal said more. Anything else — a
value that moved for a second reason, a key present on one side only — is a
change and withholds as before. E4′ measured both halves at once: the four
target-rooted keys relocated and named on all 61 pairs, and `RUSTDOCFLAGS`
withholding on all 61 because a second thing inside it moved. A Python pair
records no target root, so every string it prints is the one it printed before
this rule existed.

---

