# What the answers claim

Each command's output is written to be exact about its own limits. The short
form, and the exit table, stay in [../README.md](../README.md). `exceptions`,
`watch`, `flow`, and Rust `refocus` in full are [query.md](query.md).

## What the answers claim

This is the part worth reading. Each command's output is written to be exact
about its own limits, and the commands differ in how much they can establish.

### `diff`: shape, not location

`diff` compares two runs' causal streams on `(file, qualname, kind)`; a MATCH
is the same shape of execution, not the same values. A function moved to
another file changes `file` on every one of its events, so a pure move reads
DIVERGED at the first moved CALL. `diff --ignore-moves` pairs a function that
left one file with the same-named function that appeared in another (only
when that pairing is unique on both sides) and prints the pairing with the
verdict as `moved: helper  a.py -> b.py`. A name present under two files on
one side is left unpaired and any divergence inside it is still reported. A
planted call-site swap under the same move reads DIVERGED
(tests/test_diff_moves.py).

### `refocus`: three verdicts, and a bounded licence

`refocus` re-runs the recorded command with deeper capture and then asks
whether the rerun was the same execution, two gates, two different exit
codes, because "the call is wrong" and "the recording can't settle it" are
different next actions (see ["Exit statuses"](../README.md#exit-statuses)).

**Cannot refocus at all (exit 2, no rerun was attempted):** original trace
is INCOMPLETE; original run consumed stdin; the target no longer resolves;
the original working directory is gone; the original was recorded under the
per-thread fingerprint basis and ran asyncio tasks; the original trace
records no command to re-run, or no working directory to re-run from; or
the recorder declares `capabilities.refocus: false`. Every one of these is
caught before the program runs again, so the reader's next move is a
different command, not a different recording.

The program DID re-run, and the verdict below is about what came back:

| verdict | exit | means |
|---|---|---|
| MATCH | 0 | every thread that left a fingerprint in both runs produced the **identical sequence of `(file, qualname, kind)` for CALL/RETURN/RAISE/HANDLED** outside any asyncio task, every asyncio task's own stream has a counterpart of the same name and content on the other side (a multiset. The order tasks interleaved in is never compared), and there was at least one such event to compare |
| DIVERGED | 1 | the causal streams part, and the first divergence is named with a drill-in command for each side |
| REFUSED | 3 | the rerun happened (a new trace exists and is queryable) but no verdict could be issued against it. Four post-rerun reasons: there was nothing to compare (neither side recorded a causal event); a side could not be trusted (INCOMPLETE, or writes dropped after its database sealed); the two traces define a thread stream differently (a pre-0.4.0 trace against a 0.4.0 one, whenever either ran a task); or a trace ran asyncio tasks and holds no task fingerprint rows, so what those tasks did would drop out of the comparison in silence. Treat the new trace as a separate, UNVERIFIED execution. A new recording is what would settle it, which is what 3 means |

`diff --task NAME` diffs one task's stream by name; unnamed tasks match only
unnamed tasks. Traces recorded before 0.4.0 define a thread stream to
include task events (`info` says `per-thread basis`); comparing one of those
with a 0.4.0 trace is REFUSED whenever either ran a task. Asyncio's own
default `Task-<N>` names count as unnamed too. The number is creation
order, not an identity, so `diff --task` refuses a literal `Task-<N>` rather
than pretend it picks anything (Ruling 4). The name a task is compared under
is the one it had **when it first ran traced code**: the recorder reads
`get_name()` once, at the moment it mints that task's identity, so a
`set_name` afterwards is never seen by any comparison. A thread's fingerprint row can
hold zero events under this basis: a thread whose traced code all ran inside
asyncio tasks still gets a row of its own, just with nothing in it outside
those tasks.

**A MATCH is a statement about the shape of the execution, not a statement
that the two runs were the same.** It licenses one conclusion: the rerun took
the same path, so the deeper capture describes that same path. What no verdict
compares, sensorium prints beneath every one of them: argument and return
values, per-line state, timing, the order threads ran in relative to each
other, and **the recorder's own footprint**, which is structural and
unfixable. Deeper capture runs the program's `__repr__` inside hooks that
suppress themselves, so an instrument that perturbs the program it is watching
leaves no mark on the fingerprint at all. Comparing the two runs' captured
output is the only cross-check available, and a side effect that prints
nothing is invisible to that too.

Beside the verdict, `refocus` prints a **licence**, `verified against <run>
on exactly these points, and no others`, followed by the list of checks that
actually ran and agreed (source files unchanged by content, environment
variables compared, threads started, children witnessed). It is a bounded
enumeration of what was verified, not a summary judgment. **Any check that
could not run withholds the licence too**, with the reason itemised, because
"no git repository, so I could not tell" is a fact about the check and not
evidence that nothing moved. Two things it will not call a change are the
tool's own: a target directory that merely **moved**, and the recorder's own
`--extern sensorium_rt=…` fragment inside `RUSTDOCFLAGS`, whose hash moves
with every driver build, the first **re-rooted** before the compare, the
second **removed** from it, and both **named** on the line. A third,
**session set 1** (the handles a shell, terminal or agent session hands a
process, listed by name in [query.md](query.md)), is counted and named without
withholding, while every other differing variable withholds exactly as
before. The verdict and the licence are both stamped into the new trace, so
`info` and `runs` keep saying so long after the output has scrolled away.

DIVERGED is not a failure of the tool. For a program whose control flow
depends on state outside the process, DIVERGED is the correct answer; the new
trace is still recorded and queryable, and permanently labelled.

### `tree`: derived parentage, and what a task group claims

A parent link is the **caller frame**, verified by code identity, never
"the last frame opened on this thread", coroutines resumed by the event
loop, generators resumed by their consumer and callbacks from C all break
that assumption, and v1 made it. From trace format 3 a generator or
coroutine body opens a frame like any other, so `NULL` now means only that
the caller was never traced (the event loop, a library) or that it started
running before recording began, not, as on an older trace, that it was a
generator or coroutine `tree` could not frame. A trace recorded by a
format-1 sensorium is labelled `parentage: ASSUMED` because its links were
the guess.

Every non-function frame is marked with its kind (`[generator]`,
`[coroutine]`, `[async_generator]`) and closes with the state
`Trace.frame_state` derived from its YIELD/RESUME rows, `returned` and
`raised` render exactly as a plain function's do, and the suspension states
each name where the frame stopped and why: cancelled, abandoned, unwound by
some other exception thrown in, or still `suspended` at the end of the
recording. A root frame whose caller is named but not framed shows that
caller's name and, from format 3, the reason is always the same one, `(no frame: started before recording)`, never the arc-1 `(unframed)`
reading, which is kept byte-for-byte on older traces because it names a
limitation this version no longer has.

Grouping by task is a statement about causality *within* a task (one
task is sequential) and says nothing about order *between* tasks beyond
wall-clock event ids; the footer says so. Task identity is a serial
minted per task object, not the task's name (two tasks named alike do
not merge) and is `NULL` for everything that did not run inside an
asyncio task (code before/after the loop, and loop callbacks such as
`call_soon`/`add_done_callback`).

### `exceptions`, `watch` and `flow`: in full, one file away

The three commands whose claims need the most saying are
[query.md](query.md), moved there 2026-09-06 so the README stays
under 800 lines, wording and order unchanged, and, since 2026-09-07, that
file also holds a fourth section, `refocus` on a Rust trace, added there
rather than moved. What each of the three claims, in one paragraph:

**`exceptions`** classifies every raise as `swallowed`, `uncaught`,
`re-raised`, `propagated` or `ambiguous`, and **SWALLOWED is claimed only when
the recording establishes it**. Anything short of that is `ambiguous` with
the reason printed. On a Rust trace it prints one block per SHAPE rather than
one per chain, and it refuses outright on a trace whose recorder declares
`err_flow: false`. `query.md` carries the five dispositions, the Rust
disposition rules, the grouping key and what was measured about it.

**`watch`** evaluates a restricted predicate at every recorded site of the
named code (a CALL's arguments, a LINE's deltas) and prints a tally that
accounts for **all** of them: `sites`, `evaluated`, `hits`, `not-captured`,
`errors`. **Zero hits never reads as "the invariant held"**: a site the
predicate could not be evaluated at is counted with its reason, and a run
where nothing could be checked says `NOTHING WAS CHECKED` instead of
`hits: 0`.

**`flow`** follows a captured value by equality (`--value`) or one object by
address-plus-type (`--object`) through calls and returns. It is lineage over
captured values, **not** static dataflow analysis, and the command says so in
its own header; `--object` is corroborated rather than asserted, because
CPython recycles addresses.

### `info`, `runs`, and the state of the recording itself

- `info` prints `recorder`, `lang`, and a `capabilities` line. The
  recorder's own declaration when the trace carries one, and `undeclared
  (pre-format-4 Python recorder; read as full by every command)` when it does
  not, because reading an absent declaration as full is what a command does
  to decide whether to refuse, not something the trace ever said; from trace
  format 4, a bookkeeping field a trace's declared
  capabilities say should exist but does not is printed as the recorder's own
  declaration of that gap, never as a printed `0`, and never as the
  pre-format-4 "predates that bookkeeping" wording, which is kept for traces
  that actually predate it.
- Truncated captures are marked where they appear (a clipped string ends
  `~`, a sampled container ends `, ...`) and counted in `info`.
- A run whose recording died is labelled **INCOMPLETE**, in `info` and in the
  `runs` listing both. Its causal stream can stop anywhere without saying so.
- Writes dropped under load are reported as a **lower bound** (`>=N`): writes
  that arrive after the count was taken cannot be counted either.
- Subprocesses that were noticed are listed as unwitnessed, never silently
  ignored, and an empty list is not evidence that none ran. A child that can
  only be *counted* and not named (a `multiprocessing` spawn, which reaches
  the OS without going through `subprocess`) is reported as a count **on
  Python 3.14+**, where the underlying syscall raises an audit event; on 3.12
  and 3.13 that event does not exist, so such a spawn is unwitnessed entirely
  (which is why `refocus` withholds the "no child witnessed" licence there).
  Counted too are the threads a run started and any malfunction of the hook.
  None of these is printed when it is zero: a printed `0` would read as proof
  nothing was started, which is exactly what it is not.
