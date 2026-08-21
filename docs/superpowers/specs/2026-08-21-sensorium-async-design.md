# Async attribution: derived parentage and task identity

Status: design approved 2026-08-21, awaiting spec review
Supersedes nothing. Extends `2026-08-18-sensorium-design.md`, which listed
"async task attribution" under *Not in v1*.

## The problem, measured

v1 as shipped, Python 3.14.4, two independent asyncio tasks each calling a
plain sync helper three times:

```
$ sensorium tree last
f1 e1 <module>() -> None
  f2 e4 step(task='A', n=1) -> 'A:1'
  f3 e7 step(task='B', n=1) -> 'B:1'
  f4 e9 step(task='A', n=2) -> 'A:2'
  f5 e11 step(task='B', n=2) -> 'B:2'
  f6 e13 step(task='A', n=3) -> 'A:3'
  f7 e16 step(task='B', n=3) -> 'B:3'
```

Three defects, all live:

1. **Fabricated parentage.** `worker` called every one of those six. `<module>`
   called none of them. Two concurrent tasks are rendered as one sequential
   sibling list under a frame that is not their caller.
2. **A command contradicted by its own trace.** `frame --fn worker` answers
   `no such frame: no recorded activations of 'worker'`
   (`query/frame_cmd.py:33`), while `grep last worker` on the same trace
   returns `e3 CALL worker(name='A')`, `e6 CALL worker(name='B')` and both
   RETURNs. The activations are recorded; `frame` searches only `trace.frames()`
   and reports the absence of a frame as the absence of the activation.
3. **No disclosure.** `info` reports `CALL 10 RETURN 10` and hot functions
   `6x step, 1x <module>`; `worker` and `main` appear in neither the tree nor
   the summary, and nothing states that four recorded calls were not framed.

This is not a missing feature. It is the founding sentence — *the instrument
never answers from data it does not have* — violated by a tool that has been
used for three CastleVTT diagnoses on a codebase that is entirely FastAPI.

There is no async test and no async corpus case in v1:
`grep -rln "async def\|asyncio" tests/ corpus/` returns nothing.

## Root cause

`parent = tls.stack[-1]` (`record/tracer.py:407`) encodes an assumption: *the
last frame I opened on this thread is the caller of the frame I am opening
now*. That is stack discipline, and it is not a property of the language. It
fails wherever control re-enters user code from somewhere other than the
innermost recorded activation:

- a coroutine resumed by the event loop (loudest, and the case that motivated
  this work),
- a generator resumed by its consumer,
- a callback invoked from untraced C (`sorted(key=...)`),
- `atexit` handlers and signal handlers.

Coroutines are additionally *frameless* (`record/tracer.py:363`, on
`CO_GENERATOR|CO_COROUTINE|CO_ASYNC_GEN`): no frame is opened, and LINE is
disabled for their code permanently, "even when focused." That decision was
correct for v1 and is not reversed here — an abandoned generator never reaches
`PY_RETURN`/`PY_UNWIND`, so a frame opened for it would never close. Arc 2
addresses that directly; arc 1 leaves framelessness intact and stops the
guessing around it.

**Parentage stops being assumed and starts being derived.**

## Scope

Two arcs, sequenced. This spec is implementable as arc 1; arc 2 appears only
as the set of constraints arc 1 must not violate.

- **Arc 1 (this spec).** Derived parentage, task identity, honest query
  output, trace-format bump. Coroutines stay frameless. Nothing inside an
  `async def` becomes inspectable.
- **Arc 2 (later, own spec).** `PY_YIELD`/`PY_RESUME`, coroutine frames with
  suspension and abandonment states, per-task stacks, LINE/`--focus`/`watch`
  inside `async def`, per-task fingerprints.

## Measurements the design rests on

All on this box, Python 3.14.4, 200k iterations each. Sensorium's own measured
cost is ~6 µs/event, so the comparison column is what matters.

| Fact | Measured | Share of one event |
|---|---|---|
| `sys._getframe(2)` — read the true caller | 25 ns | 0.4% |
| `asyncio.current_task()` inside a running loop | 26 ns | 0.4% |
| `asyncio.events._get_running_loop()` outside a loop | 19 ns | 0.3% |
| `asyncio.current_task()` **outside** a loop (raises `RuntimeError`) | 93 ns | 1.6% |
| `'asyncio' in sys.modules` | 22 ns | 0.4% |

Two consequences, both binding:

- Correct parentage plus task identity costs ~51 ns/event, **under 1% of what
  an event already costs.** There is no performance argument for keeping the
  guess.
- `current_task()` raises outside a running loop, and an exception per event
  in every synchronous program is not acceptable. The gate is
  `_get_running_loop()`, which is C-accelerated (`_asyncio`), returns `None`,
  and is cheaper than probing `sys.modules`.

Also measured: **frame objects do not support weak references**
(`TypeError: cannot create weak reference to 'frame' object`). Frame identity
must therefore be held as an address, which the design below makes sound
rather than assuming.

Verified by direct probe, not inferred: inside a `PY_START` callback,
`sys._getframe(2)` is the true caller (`caller=worker` for every `step`), and
`asyncio.current_task()` returns the correct task from inside the callback with
no reentrancy problem. A coroutine's own `PY_START` reports `caller=_run` —
the event loop — which is the truthful answer: `main` *created* the task, the
loop *entered* it. "Who awaited this" is a different question, answered by
task identity, not by the frame stack.

## D1. Derived parentage

`PY_START` already holds `sys._getframe(1)`, the frame being opened. It gains a
read of `sys._getframe(2)`, the caller, and a per-thread map of live frames:

```
tls.live[id(frame)] = (frame_id, code)    # on open
tls.live.pop(id(frame), None)             # on PY_RETURN / PY_UNWIND
```

Parent resolution at `PY_START`:

1. `caller = sys._getframe(2)`; `ValueError` (no such depth) → no parent.
2. `entry = tls.live.get(id(caller))`; miss → no parent.
3. **Verify** `entry.code is caller.f_code`; mismatch → treat as a miss.
4. Hit → `parent_id = entry.frame_id`, `depth = parent.depth + 1`.
   Miss → `parent_id = NULL`, `depth = 0`.

A miss is not an error and is not silently absorbed. `parent_id` is `NULL` and
the caller's interned code id is written to the CALL payload as `caller_code`,
so the query side can say *called by `worker`, which has no frame* rather than
inventing a parent or dropping the relationship. When there is no caller frame
at all (step 1), `caller_code` is absent, which is distinct from a miss.

### Why `id()` is sound here

This project has twice been burned by `id()` — recycled exception addresses,
recycled thread ids — and the ledger records both. The argument that it is safe
in this position is specific and must not be generalised:

- The map holds **only regular function frames**. A regular function's frame
  always terminates through `PY_RETURN` or `PY_UNWIND`, both of which are
  subscribed, so every entry is removed on the frame's death.
- An address can therefore never be recycled under a live key: the key is
  removed before the object it names can die.
- The things that *can* terminate without either event — abandoned generators
  and coroutines — are exactly the things that are frameless in arc 1 and so
  never enter the map at all.
- The `entry.code is caller.f_code` check in step 3 is a second, independent
  guard, and is what keeps arc 2 honest when coroutine frames do enter the map
  and abandonment becomes reachable.

Arc 2 must not put a suspendable frame into this map without also giving it a
terminal `ABANDONED` state. That is a constraint on arc 2, recorded here.

### A property gained on the close path

Frames currently close only when the stack top matches by code identity
(`tracer.py:433` and `tracer.py:459`: `tls.stack[-1][1] is code`). A mismatch
skips the pop, and the frame is never closed. Closing by address instead
(`tls.live.pop(id(frame))`) makes the close exact and independent of stack
skew. `tls.stack` is removed: LINE capture, exception-site frames and frame
close all look the activation up in `tls.live` by frame address, so there is
one authority, not two that must agree.

No claim is made here that the stack-top mismatch is reachable in v1. The point
is that the new mechanism does not depend on the question.

## D2. Task identity

Per event, gated so that synchronous programs pay 19 ns and nothing else:

```
loop = _get_running_loop()          # C-accelerated, returns None, never raises
task = current_task() if loop is not None else None
```

Identity is a **minted serial**, not `id()` and not the task's name:

- `id()` is recycled, and this project does not trust it for identity.
- Task names are not unique — `asyncio.create_task(..., name=...)` accepts
  duplicates, and two tasks sharing a display name must not merge.

A `WeakKeyDictionary` from task object to serial, mirroring the existing
`_TLS.thread_serial` design (`tracer.py:310-314`), so a finished task's entry
dies with it and a long-lived program does not accumulate them. The display
name rides in the payload beside the serial, for output only.

Events carry `(thread_serial, task_serial)`. `task_serial` is `NULL` for every
event recorded outside a running loop, which is the common case and must not
be rendered as a task called "none".

## D3. Query surface

### `tree`

Groups by task, shows unframed coroutine calls in their true position, and
never invents a parent:

```
outside any event loop
  f1 e1 <module>() -> None
task t1: Task-1
  e2 main()  [coroutine, unframed]
task t2: task-A
  e3 worker(name='A', delay=0.01)  [coroutine, unframed]
    f2 e4 step(task='A', n=1) -> 'A:1'  <- worker (unframed)
    f4 e9 step(task='A', n=2) -> 'A:2'  <- worker (unframed)
    f6 e13 step(task='A', n=3) -> 'A:3'  <- worker (unframed)
task t3: task-B
  e6 worker(name='B', delay=0.02)  [coroutine, unframed]
    f3 e7 step(task='B', n=1) -> 'B:1'  <- worker (unframed)
    f5 e11 step(task='B', n=2) -> 'B:2'  <- worker (unframed)
    f7 e16 step(task='B', n=3) -> 'B:3'  <- worker (unframed)
order between tasks is wall-clock (event ids), not causal; within one task it is causal
4 unframed call(s) shown as events: coroutine/generator code opens no frame in this version (no tree, frame, focus or watch inside them)
```

The `<- worker (unframed)` tag is the parentage statement: `step`'s caller
is `worker`, which has no frame, so `step` is indented under its task and
*named* as called by `worker` — not drawn as a child of the `e3` event,
which would claim an activation-level link the trace does not hold (that is
arc 2). The task serial (`t2`) is printed beside the name because names are
not unique.

Grouping is by task because a task is a causally coherent stream and the
interleaving between tasks is not. Event ids remain globally monotonic, so the
real execution order stays recoverable from the output without a second
command and without a flag. `<module>` ran before `asyncio.run` started a loop,
so it has no task and is not placed in one; "outside any event loop" is a
statement, not a task called none.

### `frame`

`--fn NAME` searches events as well as frames. Three distinct answers where
there is one today:

| Situation | Answer |
|---|---|
| no CALL events for that qualname | `no recorded activations of 'NAME'` (unchanged) |
| CALL events exist, no frames | `'NAME' was recorded as N call(s) but not framed (coroutine); see: sensorium grep RUN NAME` |
| frames exist | unchanged |

### `info`

Adds a count of unframed calls and the tasks seen. `worker` and `main` stop
being absent from `hot functions`, which today counts frames rather than calls.

## D4. Trace format, and old traces

`TRACE_FORMAT` (`store/db.py:6`) goes 1 → 2. The existing refusal
(`db.py:90`, a new reader rejects a trace from the future) already covers the
forward direction.

The backward direction is a new honesty case and the one most easily missed:
**a format-1 trace opened by a format-2 reader must not render as though its
parent links were derived.** Its `parent_id` values were assumed, and the
output must label them assumed, not silently inherit the credibility of the new
mechanism. Same trace, same command, different claim — because the recording
was made by a recorder that could not tell.

Schema delta, all additive — no existing column changes meaning:

- `events` gains `task_id INTEGER` (nullable; NULL outside a running loop).
  A column rather than a payload key because `tree` groups on it and `info`
  counts on it, and neither should have to parse every payload to do so.
- new table `tasks (id INTEGER PRIMARY KEY, name TEXT, thread_id INTEGER)` —
  the serial→name mapping written once per task, not once per event.
- `caller_code` is a CALL payload key (JSON), present only on a parentage miss.
- `frames` is unchanged.

A format-2 reader opening a format-1 trace finds no `task_id` column and no
`tasks` table; it treats every event as outside any loop and, per the rule
above, labels the parentage assumed. It does not fail.

## Honesty rules

What the arc-1 output must state rather than imply:

1. Ordering **between** tasks is wall-clock, not causal. The grouped layout
   must not be readable as a claim about which task ran first; the footer says
   so, and event ids carry the real order.
2. Nothing inside an `async def` is inspectable. `watch`, `--focus` and LINE
   against coroutine code must say so explicitly — following the
   `NOTHING WAS CHECKED` precedent — and must never return an empty result that
   reads as "nothing happened."

   Measured on v1: `run --focus repro:worker` (a coroutine) is accepted
   silently, and `watch last --at repro:worker --expr 'name == "A"'` reaches
   `NOTHING WAS CHECKED` — the right verdict — but explains it as
   `NEVER RECORDED: 'name' … either it is misspelled, or it lives in frames
   this run did not record`. Both offered reasons are false: `name` is a
   captured argument of `worker` (it is right there in the CALL payload), and
   the run did record `worker`. The true reason — *coroutine code opens no
   frame in this version, and watch sites are frames* — is not among the
   candidates. Honest-by-accident with a misleading diagnosis is a defect:
   `watch` must name the real reason, and `run` must say at record time that a
   `--focus` pattern matched only code that cannot emit LINE, rather than
   accept it and leave `watch` to be the messenger.
3. A parent link that could not be derived is `NULL` and is displayed as
   unattributed with the true caller named. It is never backfilled with a
   plausible ancestor.
4. A format-1 trace's parentage is labelled assumed.
5. `refocus`'s licence gains nothing in arc 1. It must not begin claiming
   anything about task identity or interleaving, because arc 1 compares
   neither.

## Verification

Project norms apply: tests written first, each new test mutation-checked
(a deliberate defect in the code under test must fail it), and the corpus
extended with questions **pre-registered before any output is looked at** —
the question in plain language, the known ground truth, the exact invocation,
and why `print()` cannot answer it.

New corpus cases:

1. **Interleaved tasks, wrong attribution.** Two tasks mutating shared state;
   the question is which task wrote the final value. Ground truth is known
   because the bug is planted. v1 answers this wrongly today, which makes it a
   regression test for the fabrication itself.
2. **Callback from untraced C.** `sorted(key=...)` where the key function is
   user code — parentage derived through a C frame, no async involved. This is
   the case that proves the fix is about parentage and not about asyncio.
3. **Abandoned task.** A task cancelled while suspended, to pin arc 1's
   behaviour (its calls are recorded and attributed; no frame is claimed) and
   to be the failing case arc 2 must then satisfy.
4. **Format-1 trace.** A checked-in format-1 trace recorded by the v1
   recorder at `e384ef4` (small; the two-task repro above is enough), opened
   by the new reader, asserting the parentage is labelled assumed and that
   the open does not fail. Generated once by a pinned interpreter and
   committed, not regenerated per run — the point is that it is *old*.
5. **Focus on a coroutine.** `run --focus` on coroutine-only code warns at
   record time; `watch` against it names the real reason. Pins honesty rule 2
   and is the failing case arc 2 must turn into a working one.

`corpus/run_corpus.py --bench` is re-run to confirm the ~51 ns/event prediction
in situ. It reports; it does not gate. If the in-situ cost diverges from the
microbenchmark by more than an order of magnitude, that is a finding to record,
not a number to quietly restate.

Existing suite must stay green on 3.12, 3.13 and 3.14 (CI matrix already
exists), including the 6 alloc-precondition skips on 3.12.

## Known limitations carried forward

Unchanged by arc 1, still stated in the README:

- no LINE, `--focus` or `watch` inside `async def` (arc 2)
- no subprocess following; `multiprocessing` spawn is witnessed only on 3.14+
- no live attach, no rr adapter
- traces store the full environment in plaintext at 0644 with no redaction pass

## Arc 2 constraints recorded now

1. A suspendable frame entering `tls.live` requires a terminal `ABANDONED`
   state; the `code is` check is the guard, not the solution.
2. `refocus` fingerprints are per-thread (`tracer.py:367`). Async interleaving
   is nondeterministic, so extending the per-thread fingerprint over async
   events would make `MATCH` unreachable on any concurrent program. Arc 2
   fingerprints **per task**: each task's causal stream compared
   independently, and the interleaving between tasks explicitly not compared —
   stated in the licence, in the same terms as the recorder's own footprint.
3. Arc 1's `task_serial` must be the identity arc 2's per-task stacks and
   fingerprints key on. It is not a display convenience.
