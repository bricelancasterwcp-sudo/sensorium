# sensorium

Record what a Python program actually did; ask it questions afterward.

Sensorium wraps one run of a program with PEP 669 (`sys.monitoring`)
instrumentation, streams every call, return, and exception — with captured
argument and return values — into a SQLite trace, and answers debugging
questions from that trace in dense plain text. It exists because reading logs
is reading a diary; this is watching the execution.

Two commitments run through all of it:

- **The instrument never answers from data it does not have.** Truncated
  captures are marked and counted, sites a predicate could not be evaluated at
  are counted rather than skipped, a recording that died is labelled, and a
  rerun that turned out to be a different execution says so permanently.
- **Nothing here guesses.** Every answer is a deterministic function of the
  recorded trace, and where the trace cannot settle a question the output says
  so instead of inferring. Sensorium reports; the agent reading it reasons.
  (`refocus` is the one command that *executes* anything — it re-runs your
  program, which is why its whole job is telling you whether what came back
  was the same execution.)

## Install

    uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"

Requires Python 3.12+ — the recorder is `sys.monitoring` and nothing else, so
on 3.11 it refuses to start rather than falling back to something weaker. No
runtime dependencies; the trace is a SQLite file written with the standard
library. One capability is version-gated: witnessing a `multiprocessing`
spawn needs the `_posixsubprocess.fork_exec` audit event, which arrived in
**3.14** — below it such a spawn is unwitnessed, and `refocus` says so by
withholding the "no child process witnessed" line rather than claiming it (see
["What the answers claim"](#what-the-answers-claim)). Everything else works
identically on 3.12 through 3.14, all three of which CI exercises.

## Use

    sensorium run -- pytest tests/test_fog.py     # record
    sensorium runs                                # what have I recorded
    sensorium info last                           # what am I looking at
    sensorium tree last --depth 3                 # what actually ran
    sensorium frame last --fn compute             # one activation, in full
    sensorium grep last compute --kind RETURN     # every event that mentions it
    sensorium exceptions last                     # what blew up, what got caught
    sensorium flow last --value 1800              # where did that number come from
    sensorium flow last --object build_key:record # what happened to that object
    sensorium diff RUN_A RUN_B                    # where two runs part
    sensorium refocus last --focus fog:compute    # re-run deeper, verified

Per-line state is opt-in at record time, so a predicate over locals needs a
run that captured them:

    sensorium run --focus fog:compute -- pytest tests/test_fog.py
    sensorium watch last --at fog:compute --expr 'visible > 100'

Asked against a run recorded without that `--focus`, `watch` does not report
zero hits — it reports `NOTHING WAS CHECKED` and prints the exact re-recording
command. Every example above was run as typed, against a small `fog.py` whose
`compute` sums cells into a `visible` local and whose `build_key(record)`
takes a dict, and a two-test `tests/test_fog.py`.

On an asyncio program `tree` groups by task, and from trace format 3 every
traced code object opens a frame — function, generator, coroutine, or async
generator alike — so a coroutine's callees nest under it exactly like a
plain function's do, tagged `[generator]`, `[coroutine]`, or
`[async_generator]` when the kind isn't `function`. A frame that suspended
carries a derived state as its tail: `~ cancelled (CancelledError thrown in
at Ln)`, `~ abandoned (dropped while suspended at Ln)`, `~ unwound by X
thrown in at Ln` for any other exception thrown in, or `~ suspended at Ln
at end of recording` for one still parked when recording stopped. A caller
named but not framed is still never re-parented — on a format-3 trace that
means it started running before recording began (`<- worker (no frame:
started before recording)`); a trace from before frames existed keeps arc
1's `(unframed)` wording exactly, because that recorder never opened frames
for coroutines at all. `--focus`, `watch`, and LINE capture all work inside
`async def` now: a focused coroutine's locals are captured at every LINE and
interleaved with its `~ YIELD`/`~ RESUME` rows in `frame`'s timeline, and
`info` reports `unframed calls: 0 (all calls framed in format 3)` on such a
trace. `--window` is an ancestry flag, not a call-stack depth, so it
survives a suspension: another task's calls made while the windowed frame is
parked are outside the window, and the windowed frame's own calls after it
resumes are still inside. A generator or coroutine resumed on a *different*
thread from the one that started it — a sync generator first stepped where
it was made and finished from a thread pool, which is what a streaming
response does — keeps the frame it opened: its suspensions, its return and
anything it calls stay on that frame, and every row still names the thread
that produced it.

Recording captures calls, returns, raises and handled-events for code under
the working directory the run started in — so `sensorium run -- pytest ...`
traces your tests and your code, and not pytest's. `--focus module:qualname`
adds line-level capture with local-variable deltas for the named code;
`--window QUALNAME` limits that capture to what runs inside one function's
activations. Traces land in `~/.sensorium` (or `$SENSORIUM_DIR`), one SQLite
file per run.

A run reference is a full run id, a unique prefix, or `last` (the most
recently written trace). Every query takes one — `runs` takes none and `diff`
takes two. Events are addressed as `eN` and frames as `fN`, and those ids are
stable, so an answer from one command is a runnable argument to the next:
`frame --fn NAME --nth N` picks among repeated activations and says how many
there are when `N` is out of range, and `flow --object` takes either
`e<id>:<name>` — any name captured at that event — or `<qualname>:<name>`,
which resolves to that function's **first CALL** and so names one of its
**arguments** (`<qualname>:return` follows the same activation to what it
handed back). A name that was not captured at the event a spec resolves to is
refused, with the names that *were* captured there listed.

## What the answers claim

This is the part worth reading. Each command's output is written to be exact
about its own limits, and the commands differ in how much they can establish.

### `refocus` — three verdicts, and a bounded licence

`refocus` re-runs the recorded command with deeper capture and then asks
whether the rerun was the same execution.

| verdict | exit | means |
|---|---|---|
| MATCH | 0 | every thread that left a fingerprint in both runs produced the **identical sequence of `(file, qualname, kind)` for CALL/RETURN/RAISE/HANDLED**, and there was at least one such event to compare |
| DIVERGED | 1 | the causal streams part, and the first divergence is named with a drill-in command for each side |
| REFUSED | 2 | no verdict could be issued — there was nothing to compare, or the recording could not be trusted |

**A MATCH is a statement about the shape of the execution, not a statement
that the two runs were the same.** It licenses one conclusion: the rerun took
the same path, so the deeper capture describes that same path. What no verdict
compares, sensorium prints beneath every one of them: argument and return
values, per-line state, timing, the order threads ran in relative to each
other — and **the recorder's own footprint**, which is structural and
unfixable. Deeper capture runs the program's `__repr__` inside hooks that
suppress themselves, so an instrument that perturbs the program it is watching
leaves no mark on the fingerprint at all. Comparing the two runs' captured
output is the only cross-check available, and a side effect that prints
nothing is invisible to that too.

Beside the verdict, `refocus` prints a **licence** — `verified against <run>
on exactly these points, and no others`, followed by the list of checks that
actually ran and agreed (source files unchanged by content, environment
variables compared, threads started, children witnessed). It is a bounded
enumeration of what was verified, not a summary judgment. **Any check that
could not run withholds the licence too**, with the reason itemised, because
"no git repository, so I could not tell" is a fact about the check and not
evidence that nothing moved. The verdict and the licence are both stamped into
the new trace, so `info` and `runs` keep saying so long after the output has
scrolled away.

DIVERGED is not a failure of the tool. For a program whose control flow
depends on state outside the process, DIVERGED is the correct answer; the new
trace is still recorded and queryable, and permanently labelled.

### `tree` — derived parentage, and what a task group claims

A parent link is the **caller frame**, verified by code identity, never
"the last frame opened on this thread" — coroutines resumed by the event
loop, generators resumed by their consumer and callbacks from C all break
that assumption, and v1 made it. From trace format 3 a generator or
coroutine body opens a frame like any other, so `NULL` now means only that
the caller was never traced (the event loop, a library) or that it started
running before recording began — not, as on an older trace, that it was a
generator or coroutine `tree` could not frame. A trace recorded by a
format-1 sensorium is labelled `parentage: ASSUMED` because its links were
the guess.

Every non-function frame is marked with its kind (`[generator]`,
`[coroutine]`, `[async_generator]`) and closes with the state
`Trace.frame_state` derived from its YIELD/RESUME rows — `returned` and
`raised` render exactly as a plain function's do, and the suspension states
each name where the frame stopped and why: cancelled, abandoned, unwound by
some other exception thrown in, or still `suspended` at the end of the
recording. A root frame whose caller is named but not framed shows that
caller's name and, from format 3, the reason is always the same one —
`(no frame: started before recording)` — never the arc-1 `(unframed)`
reading, which is kept byte-for-byte on older traces because it names a
limitation this version no longer has.

Grouping by task is a statement about causality *within* a task (one
task is sequential) and says nothing about order *between* tasks beyond
wall-clock event ids; the footer says so. Task identity is a serial
minted per task object, not the task's name — two tasks named alike do
not merge — and is `NULL` for everything that did not run inside an
asyncio task (code before/after the loop, and loop callbacks such as
`call_soon`/`add_done_callback`).

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
away: it fires when the condition is true, and it never was.

### `flow` — lineage, not dataflow analysis

`flow --value V` follows a captured value by equality through calls and
returns. `flow --object SPEC` follows one object's **identity by address plus
type** — and CPython recycles addresses, so this is corroborated rather than
asserted: a lineage is split where a constructor ran on the address, gaps are
reported as gaps, and the output states what it cannot establish. Both are
lineage over captured values; neither is static dataflow analysis, and the
command says so in its own header.

### `info`, `runs`, and the state of the recording itself

- Truncated captures are marked where they appear — a clipped string ends
  `~`, a sampled container ends `, ...` — and counted in `info`.
- A run whose recording died is labelled **INCOMPLETE**, in `info` and in the
  `runs` listing both — its causal stream can stop anywhere without saying so.
- Writes dropped under load are reported as a **lower bound** (`>=N`): writes
  that arrive after the count was taken cannot be counted either.
- Subprocesses that were noticed are listed as unwitnessed, never silently
  ignored — and an empty list is not evidence that none ran. A child that can
  only be *counted* and not named (a `multiprocessing` spawn, which reaches
  the OS without going through `subprocess`) is reported as a count **on
  Python 3.14+**, where the underlying syscall raises an audit event; on 3.12
  and 3.13 that event does not exist, so such a spawn is unwitnessed entirely
  (which is why `refocus` withholds the "no child witnessed" licence there).
  Counted too are the threads a run started and any malfunction of the hook.
  None of these is printed when it is zero: a printed `0` would read as proof
  nothing was started, which is exactly what it is not.

## What a trace file holds

A trace is one SQLite file under `$SENSORIUM_DIR` (default
`~/.sensorium/traces`), created with your umask — `0644` on a default Linux
setup, so readable by every account on the machine. In plaintext it holds:

- **the entire process environment** as it stood at record time, variable by
  variable — every variable the launching shell exported, 78 of them for the
  run that produced this paragraph — including any token, key or password
  among them;
- **everything the program wrote** to stdout and stderr, interleaved with the
  events it wrote them between;
- the command line, the working directory, the git commit, and content
  digests of every source file the run traced;
- captured argument, return and local values, clipped to the caps `info`
  prints but not filtered for what they contain;
- which asyncio task each event ran in, and the tasks' names.

`info` refuses to print the environment and `refocus` refuses to print the
variables it compared — both carry secrets, and both say so in their own
source. Nothing refuses to *store* it, and there is no redaction pass. Treat
a trace the way you would treat a core dump or a `.env`: sharing one shares
all of the above, and `SENSORIUM_DIR` is the only control over where it
lands.

## What sensorium sees at all

Python code that this run traced, in files under the run's own root. **Nothing
else.** No command here says anything about:

- any child process, by any mechanism;
- any thread not started through Python's own `threading` / `_thread`;
- any file the program read or wrote — only source files are hashed, so
  config, fixtures, databases and inputs move unseen;
- any code outside the run's root: the stdlib, site-packages, installed
  dependencies, `PYTHONPATH` modules, and whatever `--include` / `--exclude`
  filtered out;
- the environment beyond the variables a command names as compared;
- the clock, the network, and everything else the machine did.

This is stated as a category rather than as a list of mechanisms on purpose.
Five review rounds of `refocus` each found a mechanism the tool could not see;
an enumeration that looks complete is more dangerous than no enumeration,
because a reader who checks the list concludes their case was covered.

## Overhead

**Measured on this machine** — AMD Ryzen 7 9800X3D, Linux 7.0.0-28-generic,
CPython 3.14.4 — with `python corpus/run_corpus.py --bench`:

    workload            tier      baseline  recorded       x    events  us/event
    call_dense          default     0.0089    1.2509   141.3    185428       6.7
    call_dense          focused     0.0089    1.7106   191.3    278140       6.1
    work_between_calls  default     0.1172    0.3204     2.7     24004       8.5
    work_between_calls  focused     0.1177    0.4514     3.8     48006       7.0
    async_call_dense    default     0.0302    0.3268    10.8     40004       7.4
    await_dense         default     0.0515    0.2235     4.3     40004       4.3
    await_dense         focused     0.0511    0.3590     7.0     60005       5.1

    recorder fixed cost: 0.036s on a program that does nothing (0.0074s -> 0.0430s)

**What 0.2.0 added, measured against 0.1.0 on the same machine the same
day**, each side best-of-three in its own fresh venv, two independent runs
per side: `call_dense` went from 6.0 to 6.5 µs/event (+8%) and
`work_between_calls` from 8.3 to 8.4 (+1%); the call-dense multiplier moved
from 113× to 135× (+19%), of which roughly half is that same per-event cost
restated and half is the two builds' baselines differing by a millisecond.
The design note predicted about 0.05 µs/event for derived parentage plus
task identity; the in-situ cost is 0.1–0.5 µs/event depending on call
density — five to ten times the prediction, recorded here as a finding
rather than restated. `async_call_dense` runs every call inside a running
event loop and so pays the task-identity path in full: 7.4 µs/event, about
0.7 µs more than the synchronous call-dense case on this box.
`async_call_dense` registers no focus target — its body only calls a
one-line function — so it is reported for the default tier only;
`await_dense` prices coroutine-body focus instead.

On this same box, arc 2a's frame-and-suspension bookkeeping shows no
measurable regression against a fresh 0.2.0 worktree measured the same way:
`call_dense`/`work_between_calls`/`async_call_dense` measure
6.7/8.5/7.4 µs/event here versus 0.2.0's 6.7/8.1/7.6 — differences within
run-to-run noise in both directions.

`await_dense` isolates the cost arc 2 added: a coroutine that suspends
20,000 times on `asyncio.sleep(0)`, so almost every event it produces is a
YIELD or a RESUME on the same frame. Measured here it costs 4.3 µs/event by
default (5.1 focused), including the amortised recorder fixed cost (~0.9 µs
of that 4.3 — the 0.036s boot from the fixed-cost row above, spread over
40,004 events); about 3.4 µs/event without it. Against the **~114 ns** the
design note measured for the `sys.monitoring` PY_YIELD/PY_RESUME callbacks
alone, before any writing, that is roughly 30× the floor (38× including the
amortised fixed cost), the rest being the trace write and the derived-state
bookkeeping the bare callback does not pay for.
`us/event` is the figure that travels; the multiplier tracks how call-dense
the program is.

These are measurements of one machine and four workloads, not a promise
about yours. The multiplier is not a property of sensorium: recording costs
on the order of **4–9 microseconds per event** here, from 4.3 on the
per-suspension `await_dense` case up to 8.5 on `work_between_calls` (6.7 on
the call-dense case), and how much that is depends entirely on how often the
traced program calls or suspends. `call_dense` is naive recursive
`fib`, close to the worst case that exists — every microsecond of its baseline
is function calls. `work_between_calls` does real work inside each call, which
is what ordinary code looks like. Times are whole-command wall clock (best of
three, after an untimed warm-up), so every row includes interpreter startup
and recorder boot; the fixed cost is printed separately so it can be
subtracted.

`--focus` costs one further event per executed line of the focused code, so
its price depends on what you point it at: at the hot recursive function
above it adds a third again, and pointed at a function whose body is a hot
inner loop it would cost far more.

## Corpus

    python corpus/run_corpus.py            # verify against seeded bugs
    python corpus/run_corpus.py --show     # print the questions and commands
    python corpus/run_corpus.py --bench    # report recording overhead

Nineteen small programs with deliberately planted bugs, and thirty-six
questions registered **before** any output was looked at: the question in
plain language, the known ground truth, the exact invocation expected to
yield it, and why a `print()` cannot answer it. Ground truth is known
because the bugs were planted. This is the regression suite, and it
includes the honesty cases — a DIVERGED verdict, an under-claimed generator
swallow, a `watch` tally with fourteen unchecked sites, a task group that
answers which coroutine made the final write, a cancellation located at the
line a task was parked on, and arc 2's four: `abandoned_generator` (a
dropped generator's frame reads `~ abandoned`, never a fabricated `->`
return), `suspended_handler` (a handler frame still open when recording
stopped stays `ambiguous … never closed`, not a claimed swallow),
`window_across_suspension` (`--window` as ancestry survives a suspension —
another task's call parked in the middle is outside it, the windowed
frame's own call after it resumes is inside), and `async_handler` (`watch`
locals inside a focused coroutine, disambiguating two interleaved tasks a
print cannot tell apart).

`--bench` reports; it never gates. Overhead is a tracked fact about a machine
and a workload, not a pass/fail property of the tool.

## Not yet

Per-task fingerprints and `refocus`/`diff` comparing tasks by content (plan
2b): the `task_fingerprints` table exists in the schema but nothing writes
to it yet. Subprocess following, attach-to-live-server flight recording,
native (rr) substrates, MCP wrapper. See
`docs/superpowers/specs/2026-08-21-sensorium-arc2-inspectable-coroutines-design.md`
(extends `2026-08-21-sensorium-async-design.md`, arc 1's spec).
