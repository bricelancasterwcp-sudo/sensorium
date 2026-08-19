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
library.

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

### `exceptions` — five dispositions, and a real refusal

Every raise is classified as `swallowed`, `uncaught`, `re-raised`,
`propagated`, or `ambiguous`, and the tally is printed.

**SWALLOWED is claimed only when the recording establishes it**: a HANDLED
event in a frame that then returned normally, with no later raise carrying the
same recorder identity, and no later raise that could be that same object at
that same address. Anything short of that is `ambiguous`, and the reason is
printed. In particular:

- A bare `finally` emits a handled-event with nothing caught — CPython
  compiles `finally` as an implicit handler — so a handled-event is never on
  its own read as "something was caught".
- Generators and coroutines are frameless: no frame is opened for them, so
  there is no "returned normally" to observe. A swallow inside one is
  genuinely unclassifiable and is reported `ambiguous`, never as a swallow.
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
  the OS without going through `subprocess`) is reported as a count, as are
  the threads a run started and any malfunction of the hook that counts them.
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
  prints but not filtered for what they contain.

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
    call_dense          default     0.0090    1.0812   119.8    185428       5.8
    call_dense          focused     0.0091    1.4773   162.8    278140       5.3
    work_between_calls  default     0.1087    0.2820     2.6     24004       7.2
    work_between_calls  focused     0.1083    0.3966     3.7     48006       6.0

    recorder fixed cost: 0.034s on a program that does nothing (0.0074s -> 0.0412s)

Across four runs of that command on this machine the multipliers span
120–125, 161–176, 2.6–2.7 and 3.7–3.8, the fixed cost sits at 0.034 s (six
consecutive measurements: 0.0331–0.0346 s), and the event counts do not move
at all. Measured while the machine was also running the test suite, that same
fixed cost reads 0.052 s — best of N removes noise *within* a measurement, and
nothing removes something else using the machine for the whole of it. Read
these as floors taken on an idle machine.

These are measurements of one machine and two workloads, not a promise about
yours. The multiplier is not a property of sensorium: recording costs about
**6 microseconds per event** here, and how much that is depends entirely on
how often the traced program calls things. `call_dense` is naive recursive
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

Eleven small programs with deliberately planted bugs, and nineteen questions
registered **before** any output was looked at: the question in plain language,
the known ground truth, the exact invocation expected to yield it, and why a
`print()` cannot answer it. Ground truth is known because the bugs were
planted. This is the regression suite, and it includes the honesty cases — a
DIVERGED verdict, an under-claimed generator swallow, a `watch` tally with
fourteen unchecked sites.

`--bench` reports; it never gates. Overhead is a tracked fact about a machine
and a workload, not a pass/fail property of the tool.

## Not in v1

Async task attribution, subprocess following, attach-to-live-server flight
recording, native (rr) substrates, MCP wrapper. See
`docs/superpowers/specs/2026-08-18-sensorium-design.md`.
