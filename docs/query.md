# What four answers claim, in detail

`exceptions`, `watch` and `flow` — the three commands whose claims need the
most saying — **moved here 2026-09-06 (the focus tier, rung 4 slice 1) so
`README.md` stays under 800 lines**. `docs/CARRIED-DEBT.md` named this split
at the rung-4 entry slice's close ("the next paragraph the README's
`exceptions` section wants should go to a file it links, not into the
README"), so it is taken deliberately rather than discovered at the ceiling.
**The wording and order are unchanged**; the README keeps a paragraph for
each with its load-bearing claim and a link here.

A fourth section was **added here 2026-09-07** (the refocus slice, rung 4
slice 2) rather than moved: `refocus` on a **Rust** trace, which is new
behaviour and not a relocation of anything. `refocus`'s own three verdicts and
its licence stay in [`../README.md`](../README.md), and this section is what
the Rust half of them means.

The rest of *What the answers claim* — `diff`, `refocus`'s general shape,
`tree`, `info` and `runs` — is still in [`../README.md`](../README.md), and so
is everything about what a trace file holds and what sensorium sees at all.
Read those first: they are what the commands below answer from.

### `exceptions` — five dispositions, and a real refusal

Every raise is classified as `swallowed`, `uncaught`, `re-raised`,
`propagated`, or `ambiguous`, and the tally is printed.

**SWALLOWED is claimed only when the recording establishes it**: a HANDLED
event in a frame that either returned normally, or later unwound because a
*different* exception was thrown into it at a suspension the handler had
already passed (a cancelled task, a dropped generator, or any other
thrown-in unwind) — with no later raise carrying the same recorder identity,
and no later raise that could be that same object at that same address.
Anything short of that is `ambiguous`, and the reason is printed. In
particular:

- A bare `finally` emits a handled-event with nothing caught — CPython
  compiles `finally` as an implicit handler — so a handled-event is never on
  its own read as "something was caught".
- Generators and coroutines have frames (trace format 3, shipped in 0.3.0),
  so a handler inside one is classified by exactly the rules above. A frame later
  unwound by a *different* exception thrown in after the handler ran does
  not make that earlier handler ambiguous — the verdict names the frame's
  own fate instead of claiming it "returned normally": `never returned
  (frame later cancelled at Ln)`, `(frame later abandoned at Ln)`, or
  `(frame later unwound by X thrown in at Ln)` for any other thrown-in
  exception. A generator or coroutine still suspended when recording stopped
  is `ambiguous … never closed`, the same refusal any unfinished frame gets.
  A trace recorded before format 3 opened no frame for a generator or
  coroutine body at all, so a handler inside one there has no `closed_by` to
  read and gets no verdict either — the refusal names whichever of the two
  reasons the trace's format actually supports.
- A handler in untraced code is `propagated`, which says where the exception
  went, not what was done with it.

So: `exceptions` finds swallowed exceptions it can prove, and names the ones
it cannot classify. It does not detect all swallowed exceptions.

**On a Rust trace the vocabulary is the language's, and so are the rules.**
An `Err` value travelling is not an exception unwinding, so `exceptions`
switches to a Rust rule module with five dispositions of its own —
`swallowed`, `panicked`, `returned-to-harness`, `propagated`, `ambiguous` —
computed over chains that the converter mints from `?` sites, the four
written sinks, `let _ =` and classified `Err` arms. **SWALLOWED is claimed
only where a written sink absorbed the chain and its frame then closed
`ok`**; `panicked` says the frame holding the chain unwound and never that
the panic was *caused by* the `Err`; and everything the grammar did not see
is `ambiguous` by design, never "propagated by default". What each verdict
may mean, and the twelve shapes err flow cannot see, are
[`rust/HONESTY-ERR-FLOW.md`](../rust/HONESTY-ERR-FLOW.md) §11 and
[`rust/HONESTY-BLIND-SPOTS.md`](../rust/HONESTY-BLIND-SPOTS.md) items 15–26;
the two measurements behind them are in `../README.md`'s Rust section.

**One block per shape, not one per chain** (0.8.2, Rust traces only). Two
chains are one *shape* when they share a disposition, the site the verdict is
about — the sink for `swallowed`, the arm for an escaped `ambiguous`, the
origin site for every verdict that names no site — and the verdict text once
event and frame ids are masked. A shape prints the FIRST chain's block exactly
as a lone chain prints it and appends a bracket naming the group — two spaces,
then `[×2: e3, e7]` — to the verdict line
`SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, which returned ok`.
The ids are the members' ORIGIN event ids — what the head line above prints,
what `--after` filters on, what `grep` and `tree` take — so the
printed sentence is always true of a named chain; eight show, then `… +K`.
The `raised (N):` header and the `dispositions:` tally both still count
CHAINS, so every tally in every record stays comparable line for line — which
means `raised (54):` can stand above three blocks.

**Members differing in something the key does not look at are flagged, never
merged silently**: `origins: N distinct (first shown)` (different origin
sites), `messages: N distinct (first shown)` (different error texts),
`details vary (N distinct; first shown)`, `routes: N distinct (first shown)`
— with `(this one has none)` in place of `(first shown)` where the printed
member has no line of that kind, so a flag never points at a line that is not
there. `--limit` counts SHAPES, and the continuation raises the limit instead
of handing back an event cursor, which over grouped output would re-show a
partial group: `... 2 more; continue with: sensorium exceptions <run>
--limit 3`.

**`sensorium exceptions <invocation-id>` answers for a whole
`cargo sensorium test` invocation** — the id is the one `runs` already prints
above the group. Every member trace is opened, classified and merged on the
same key, the bracket naming the spread across processes; a member that never
finalized is NAMED before any answer about chains, and the tally is the sum:

    invocation 20260101-000000-abcdef: cargo test --workspace -- 3 processes, 2 with Err chains, 1 with none
    INCOMPLETE: 20260101-000000-aaa003 never finalized -- its Err chains after the cut are not below
    raised (3 chains over 2 processes, 2 swallowing sites):
      e3 RAISE   read_config raise demo::ConfigError('Missing("port")') L14
        SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, which returned ok  [×2 over 2 processes: first e3 in 20260101-000000-aaa001, +1]
      e7 RAISE   read_config raise demo::ConfigError('Missing("port")') L14
        SWALLOWED -- absorbed by sink_ok at e9 (load L45) in f1, which returned ok  [in 20260101-000000-aaa002]
    dispositions: swallowed 3

— the tool's own output, pinned by `tests/test_exceptions_invocation.py`. That
header's `swallowing sites` counts printed BLOCKS, not distinct sites, and the
two are not equal on a real sweep: a known misnomer, carried in
[`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md). `--after` is **refused** in
this mode and exits **2** — an event id belongs to one process and this answer
spans many — and a member whose recorder declares `capabilities.err_flow:
false` refuses the whole answer, naming it.

**What the grain was measured to be worth.** On the E6⁗ workspace sweep's
busiest process, 54 SWALLOWED lines print as **3** shapes (20 166 bytes under
0.8.1 → 3 360 bytes over 32 lines); the 144 per-process answers that sweep
needed — 182 334 bytes over 1634 lines — become **one** answer of 128 167
bytes over 927 lines
(`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md` §3;
the repair's re-measurement under the shipped key reads 129 355 bytes over 936
lines, its §3). It was measured twice and the second record's H4′ verdict is
open — read §4 and §5.2 of both records before quoting any of this.

**Python traces are untouched**: they still print one block per raise and page
by event id. Grouping there waits on a definition of the site each Python
disposition's verdict is about, and is a rung-4 item.

### `watch` — a predicate at every recorded site

`watch` evaluates a restricted expression at every recorded site of the named
code — a CALL's arguments, a LINE's locals — and prints a tally that accounts
for all of them:

    sites: 9   evaluated: 7   hits: 0   not-captured: 2   errors: 0

**Zero hits never reads as "the invariant held."** A site the predicate could
not be evaluated at is not a site where it was false, so unevaluable sites are
counted, their reasons are printed (not in scope / recorded as an object /
recorded as a container / recorded truncated), and a run where nothing could
be checked says `NOTHING WAS CHECKED` instead of `hits: 0`. Where re-recording
would fix it, the exact `sensorium run --focus ...` command is printed;
where it would not, the output says so.

A predicate naming something the trace never recorded anywhere raises a
warning even when the rest of the predicate produced hits — a typo'd name is
otherwise a silent zero. When there are no hits, `watch` reports the closest
approaches with their margins, which is the question a threshold log throws
away: it fires when the condition is true, and it never was. `--misses N`
sets how many of those near-misses to show (default 5); the pre-0.8.0
`--near` alias has been removed.

### `flow` — lineage, not dataflow analysis

`flow --value V` follows a captured value by equality through calls and
returns. **On a Rust trace, spell the literal as the trace prints it**: `flow`
compares a `dbg` capture's Debug TEXT while `watch --expr` compares resolved
values, so `flow --value 5.0` finds no sighting of an integer capture printed
`5` even though `watch --expr x == 5.0` is true of that same capture (design
A12). `tree`, `frame` and `grep` all show the spelling to use. `flow --object SPEC` follows one object's **identity by address plus
type** — and CPython recycles addresses, so this is corroborated rather than
asserted: a lineage is split where a constructor ran on the address, gaps are
reported as gaps, and the output states what it cannot establish. Both are
lineage over captured values; neither is static dataflow analysis, and the
command says so in its own header.

### `refocus` on a Rust trace — the recorded command, run again

**Added 2026-09-07 (rung 4 slice 2, `cargo-sensorium` 0.5.0).** `refocus`
answers on a Rust trace instead of refusing on `capabilities.refocus`. The
three verdicts, their exits and the licence's shape are `../README.md`'s
`refocus` section, unchanged; what follows is the Rust half.

**Five refusals come first, and none of them runs anything.** They are about
this RUN, not about the recorder, and each exits **2** with `nothing was
re-run` in it:

- `--window` was given — it needs a per-activation runtime check the Rust
  runtime does not have, so it is refused by name rather than approximated.
- The run is one of *n* processes of its invocation. The count is every runner
  process cargo handed the driver — test binaries **and doctests** — so a
  `cargo test -p foo` that builds two integration tests is two processes and
  no single trace is the answer to a question about the invocation. The
  sentence is `corpus/rust/refocus_refused_many`'s pin:

      error: cannot refocus <run>: run <run> is one of 2 processes of its invocation (test binaries and doctests); refocus needs an invocation with a single-target selector (--lib, --test X, --bin X) so one trace is the answer; nothing was re-run

  A single-target selector (`--lib`, `--test X`, `--bin X`) excludes doctests
  and is what makes the count 1.
- The trace records no `workspace_root` — a recording made by
  `cargo-sensorium 0.4.0` or earlier, which wrote no such key.
- That workspace no longer exists on this machine.
- There is no `cargo-sensorium` to re-run with: set
  `SENSORIUM_CARGO_SENSORIUM` or put the driver on `PATH`.

Each of these also prints the Rust `no rerun was attempted` note, which names
what a reader may do INSTEAD — and names the command that can record this
workspace, never `sensorium run`, which cannot
(`corpus/rust/refocus_refused_many` pins the sentence whole).

**The re-run is the recorded command, from the recorded workspace, into the
same store.** `refocus` builds the driver argv itself: `--refocus-of <run>`
first and unconditional, then the ORIGINAL's recorded tier — never one this
call asserts — then the original's `meta.focus` followed by the values you
added, then the original's own cargo argv. So a refocus only ever captures
MORE. The announced command is `corpus/rust/refocus_match`'s pin:

    refocus-of: <run>   cmd: <driver> --refocus-of <run> --tier call --focus fill run

cwd is the recorded `workspace_root`; `SENSORIUM_DIR` resolves to the store
the original lives in; the child's stderr streams through, because a focused
rebuild is visible work and takes seconds.

**The pair is found in the store, never in what the driver printed.** After
the child exits, `refocus` lists the traces whose `refocus_of` is this run and
whose recording started after the launch. Exactly one is the pair; **zero** —
the driver refused, cargo failed before recording, the invocation produced
nothing — is `verdict: REFUSED` after the rerun at exit **3**, carrying the
driver's exit and its last stderr line; **more than one** is REFUSED by count.
Neither guesses. The link is what `runs` prints beside the verdict —
`refocus-of:<run>  verdict:MATCH(granted:4,see-info)`
(`corpus/rust/refocus_match`) — and what `info` prints on the new trace.

**MATCH, DIVERGED and REFUSED mean exactly what they mean on a Python pair**,
and the comparator is unchanged. For a Rust pair the fingerprint is per task —
a test, or a spawned thread — over CALL, RETURN, RAISE and HANDLED, and **a
LINE row never enters the hash**, which is what lets the deeper re-run MATCH
the run it came from. Tasks are compared as an order-independent multiset, so
a worker pool that split the same work across different workers is not a
difference. The two verdict lines, from `corpus/rust/refocus_match` and
`corpus/rust/refocus_diverged`:

    refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
    refocus verdict: DIVERGED -- the compared thread took a different path

**Two of the licence's checks cannot run at all on a Rust pair, and say so.**
Source, environment and exit status are checked for real. `output` and
`children` are not: `capabilities.output` and `capabilities.children` are
`false` on a Rust trace, so comparing them would compare two empty sets and
report agreement — the named bug class. They print under their own heading and
are stamped, never counted (`corpus/rust/refocus_match`):

    checks that could not run on this pair
    output: unverifiable (not recorded)
    children: unverifiable (not witnessed)

An unverifiable check is **never** counted as a verified one; the two counts
are two numbers and are never summed.

**The blind-spot block after a Rust verdict is the Rust vocabulary's**, and
its third line is the one only a re-run can owe (`corpus/rust/refocus_match`
pins all three):

    output not recorded (capabilities.output: false)
    threads from dependency code are unnamed
    the re-run's rebuild is its own cost: --focus keys a fresh shim and a rebuild of the matched units

**Measured, and it changes how a `cargo test` refocus should be read.** E4
re-ran all 61 `#[test]` functions of a real workspace one at a time
(`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md`): **61 of 61
MATCH**, 0 DIVERGED, 0 REFUSED, with source, environment and exit each
verified 61 of 61 and output and children UNVERIFIABLE 61 of 61. **And the
licence was WITHHELD on every one of the 61** — `licences granted` is 0. The
cause is the untraced-thread clause, and it cannot not fire on a `cargo test`
trace: libtest runs each test on a thread it spawns, so there is always at
least one thread with no fingerprint to compare (the measured counts are 57
pairs with 1 such thread, 1 with 2, and 3 with 5). That is a design question
about what "the program's threads" means on a test harness — carried in
[`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) with its candidate fix, and
deliberately not applied. **So on a `cargo test` pair, read the four counts,
not the word.** On a `cargo run` pair there is no harness thread and the
licence IS granted, which `corpus/rust/refocus_match` pins over four points.

**One caveat about `last`.** A refocus writes a NEW trace whose id no script
could have spelled in advance, so the way to ask it a question is `last` —
which is the store's newest trace **by file mtime**, not by any recorded
clock. Inside a corpus case that is unambiguous, because the case's store
holds exactly two traces and the refocus just wrote the second; in a store you
share between runs it is not, and `sensorium runs` (which prints the
`refocus-of:` link) is what names the trace you actually mean.
