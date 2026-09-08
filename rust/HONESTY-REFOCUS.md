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


## Amendments — rung 4 slice 4, the recorder's footprint (2026-09-08)

Appended after the moved body and never edited into it: the two **Corrected
2026-09-07** notes and the **Ruled and applied 2026-09-07** paragraph above set
the register, and a paragraph that was true when it was written stays as it was
written. Each amendment names the commit that applied it and what could
falsify it.

**Ruled and applied 2026-09-08 — the recorder's own compiler flags are not a
change the world made** (design 2026-09-08 R1, at `0810bee` with `83d48ff`).
The paragraph above ends on E4′'s finding: the licence withheld on all 61 pairs
for one key, `RUSTDOCFLAGS`, whose driver-injected rt hash is the recorder's
own footprint read as the world's. That fragment — and only that fragment — is
now removed from **both** sides before the compare: `--extern
sensorium_rt=<root>/sensorium/rt/<16 hex>/<unwind|abort>/libsensorium_rt.rlib`
together with the `-L dependency=<the same directory>` that resolves it, the
two tokens naming ONE directory. The backreference is the whole fence — two
tokens naming two directories are not a shape this recorder writes and are left
for the world's compare — and a value in which nothing matched comes back byte
for byte as it came (`strip_recorder_fragment`,
`src/sensorium/query/refocus_env.py`). What is left of the variable is compared
exactly as before, equality first and then the relocation rule above, so a
`RUSTDOCFLAGS` the world also wrote to still withholds on the remainder. A
variable this tool compared less of is never silent: `; the recorder's own
fragment stripped before comparing: RUSTDOCFLAGS` rides on the env line and in
the stamped fact.

*Measured by* **E4″ H2**
(`docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp.md`, §3 and §4)
at n = 61 over the same 61 kept originals — recorded by driver **0.5.0** and
re-run here by **0.5.2**, a different build by construction and the one
condition E4′ could not create. `RUSTDOCFLAGS` is in **0 of 61** changed lists;
the strip clause names it on **61 of 61**; E4′'s four relocated keys are
unmoved on 61 of 61; and the rt hash the fragment carries **differs on 61 of
61** pairs (`d9ce385a08c6646b` on every original against `45773c80095d5b87` on
every re-run), with none unread — so there is no pair on which the strip fired
untested. The reading's other half, the count of fragments removed per key per
side, was read (**1** per side on 61 of 61, `occurrences` **2**) and lifted
into no published cell: gap 4 of
`docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp-findings.md`.
*Also falsified by* `tests/test_refocus_env.py` — a world flag beside the
fragment still withholds, two tokens naming different directories are not our
fragment, a pair with no fragment reads exactly as it did, and the removal and
its count are pinned directly. A Python trace cannot carry the fragment at all,
so every line a Python pair prints is the line it printed before this rule
existed.

**Ruled and applied 2026-09-08 — where a re-run was launched from is not what
the program computes** (design 2026-09-08 R4 as amended by A-§3, at `09aad49`).
A refocus launched from another shell met a licence it could not earn: the
handles a shell, terminal, agent or login session hands a process differ there,
and every differing key withheld. **Session set 1** is the one enumerated
exception — positive, versioned and named in the printed line: exact
`DBUS_SESSION_BUS_ADDRESS`, `XDG_SESSION_ID`, `TERM_SESSION_ID`, `WINDOWID`,
`TMUX`, `TMUX_PANE`, `SSH_AGENT_PID`, `SSH_AUTH_SOCK`, `SSH_CLIENT`,
`SSH_CONNECTION`, `SSH_TTY`, `INVOCATION_ID`, `JOURNAL_STREAM`,
`SYSTEMD_EXEC_PID`, plus the prefix `CLAUDE_CODE_` (`SESSION_SET`,
`SESSION_ORDER`, `is_session_key` in `refocus_env.py`). A member that differs
is **counted, named, and never withholds**:

    env: unchanged outside session set 1 (<N> variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; 1 session variable(s) differ: CLAUDE_CODE_SESSION_ID)

Everything else withholds exactly as it did. It is **not** a list of the
variables that "bear" on a program: that design — the one this slice started
with — had its falsifier already in the suite, a test that records under
`REFOCUS_TEST_LIMIT` and re-runs without it, a variable the program
demonstrably reads and one no bearing list anyone would write carries, and it
would have granted a full licence over a program that got different input. The
version number is in the printed line so that a key found to bear can leave the
set with a date, and so a reader can tell which list a given trace was judged
against.

*Measured by* **E4″ H4, H5 and H6** (same record, §3 and §4). H4: the printed
session set equalled the preflight's pin by name and by size on **61 of 61** —
`CLAUDE_CODE_SESSION_ID`, K **1** — and **not one** withholding cited a key of
the set, which is the whole of the rule. H5, the control that the exemption did
not eat the licence: arm B added `E4PP_INPUT`, a key on no list, to four pairs'
launch environment, and all **4 of 4** came back WITHHELD with the env caveat
naming it — one granted line there would have been a STOP. H6, the control that
the count is exact: arm C added the first name of session set 1 absent from
both sides (`TERM_SESSION_ID`, derived at preflight rather than picked), and
the licence word equalled arm A's on **4 of 4** with K exactly one greater,
**2**. *Also falsified by* `tests/test_refocus_env.py` — every member
parametrised, a name that merely resembles one still withholding, a session key
beside a real change withholding and naming both — and by
`tests/test_refocus_licence.py::test_refocus_withholds_the_licence_when_the_environment_differs`,
the bearing design's own falsifier, green and unchanged.

**Ruled and applied 2026-09-08 — the anchor is the FIRST root, and a
spawn-named thread is never the harness's** (design 2026-09-08 R3, at
`b2f07e3`). The paragraph above states R1's rule as ROOT-MARK-ANCHORED and a
BOUND: upward, `thread::spawn(|| a_test_fn())` put a MARKED root on a thread the
PROGRAM started, that thread was subtracted, and the licence could be GRANTED
over it — the direction that claims more, blind spot 28. Two clauses close that
end, both in `refocus_world.harness_threads`: a thread whose task the runtime
named at a spawn site (`spawn@<qualname>#<k>`, or `<parent> :: spawn@…`) is
**never** the harness's whatever its root's mark, because that name is a
recorded fact about who started it; and only the **FIRST** root frame's mark
decides, where the rule as shipped excluded on any root. An `async` test fn
still carries no site row at all, so its thread stays counted as the program's
— the end that claims less, unchanged. The docstring says that now, and no
longer claims soundness in both directions.

*Measured by* `corpus/rust/refocus_spawned_test_fn`, through the real driver
under `--require-driver`: a test that spawns a thread onto another `#[test]` fn
reads `threads started: 1 besides the main one and 2 harness threads (…)` and
`licence: WITHHELD`, whose reason is `started 1 thread(s) besides the main one
and 2 harness threads (…)` — where the rule this amendment replaces printed `no
thread started besides the main one and 3 harness threads` and **granted**.
*Also falsified by* `tests/test_refocus_licence_rust.py`: a program thread named
`spawn@…` and rooted on a marked fn is counted; a thread whose first root is
ordinary and whose second is marked is counted; a libtest thread with no spawn
name is still the harness's; a root whose site the manifest never wrote is
counted.

**E4″'s 61 pairs do not exercise it, and the record says so.** H1's partition —
**57** granted, WITHHELD on §1.2's four thread-spawning tests with program-thread
counts **1 / 4 / 4 / 4** — is unmoved by this amendment: those tests spawn
through ordinary `worker` fns and through `serve_fake()`, never through a
marked one, so the mechanism cannot arise on any of them. R3's evidence is the
corpus case at n = 1, not this record's n = 61 (the findings sibling's *what
this record does not license*).
