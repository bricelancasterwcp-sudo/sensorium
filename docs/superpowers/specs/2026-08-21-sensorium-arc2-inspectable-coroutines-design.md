# Arc 2: inspectable coroutines — frames, suspension, and per-task fingerprints

Status: plan 2a implemented on feat/async-arc2; plan 2b pending
Extends `2026-08-21-sensorium-async-design.md` (arc 1, shipped as 0.2.0 in
PR #2, `main` @ d59cafc), which recorded the constraints this spec honours in
its closing section. Supersedes nothing.

Two plans will implement it, in order: **plan 2a** (frames, suspension
states, inspection — §D1–D5, §D7) and **plan 2b** (per-task fingerprints —
§D6). One spec, because 2b's needs shape 2a's schema.

## What arc 1 left, measured

After arc 1 a coroutine or generator is recorded as an **unframed CALL
event**: its sync callees are attributed to it by name (`<- worker
(unframed)`), its task is known, but the coroutine itself has no frame — so
nothing *inside* an `async def` is inspectable. Measured on 0.2.0:

- `--focus mod:coroutine` records no LINE; `watch` says `NOTHING WAS CHECKED`
  with the real reason ("coroutine/generator code opens no frame in this
  version") — honest, and useless for the field case (FastAPI handlers).
- `exceptions` classifies a handler inside a generator/coroutine as
  `ambiguous … generators and coroutines open no frame`, pinned as the honest
  under-claim by `corpus/generator_swallow`.
- `tree` cannot say whether a coroutine returned, was cancelled, was dropped
  while suspended, or is still parked; `frame --fn coroutine` says "recorded
  but not framed".
- `refocus` fingerprints are per-thread and include every task's events, so
  on any concurrent program a different interleaving produces DIVERGED.

## Measurements the design rests on

All on this box, CPython 3.14.4, `sys.monitoring`, throwaway probes
(`p1_events.py`, `p2_sig_cost.py`, job scratch; not committed).

**Events a suspendable frame emits, with frame identity:**

```
generator, full life             generator, DROPPED while suspended    task CANCELLED at an await
PY_START  gen  frame=92f0        PY_START  gen  frame=92f0             PY_START  worker frame=5970
LINE…  PY_YIELD gen frame=92f0   PY_YIELD  gen  frame=92f0             PY_YIELD  worker frame=5970
PY_RESUME gen  frame=92f0        PY_THROW  gen  frame=92f0  (GeneratorExit)  PY_THROW worker frame=5970 (CancelledError)
…  PY_RETURN gen frame=92f0      PY_UNWIND gen  frame=92f0             LINE worker line=29 (the await line re-executes)
                                                                       PY_UNWIND worker frame=5970
```

Facts, each binding:

1. **Frame identity is stable across suspension.** The same `id(frame)` is
   reported at `PY_START`, `PY_YIELD`, `PY_RESUME`, `PY_RETURN`/`PY_UNWIND`.
   Arc 1's `tls.live` (keyed by `id(frame)`, verified by `entry.code is
   frame.f_code`) therefore extends to suspendable frames unchanged, and the
   code-identity guard arc 1 installed "for arc 2" is the guard this spec
   relies on.

   **Erratum (0.3.0):** this was measured IN ONE THREAD, and the sentence
   above quietly assumed resumption happens there. It need not: a generator
   first `next`ed on the thread that made it can be stepped from a thread
   pool afterwards (`iterate_in_threadpool`, the shape a streaming response
   uses), and a task can be resumed by a loop running on another thread.
   `id(frame)` is still stable — it is the per-thread MAP that cannot hold
   the entry. So the recorder parks a suspended frame's entry in a
   tracer-level table at `PY_YIELD` (moving it out of the suspending
   thread's map, one owner at a time) and hands it to whichever thread's
   callback next misses on it, under the same `entry.code is frame.f_code`
   guard; a parked frame is alive, so its address cannot be recycled while
   its entry waits. The frames row keeps the thread that opened the frame
   and each event carries the thread that produced it. Shipped in 0.3.0.
2. **Abandonment is observable.** Dropping a suspended generator fires
   `PY_THROW(GeneratorExit)` then `PY_UNWIND` at collection time (refcount
   drop on CPython). Cancelling a task fires `PY_THROW(CancelledError)` then
   `PY_UNWIND`. Only a frame still suspended when recording *stops* leaves no
   terminal event.
3. **LINE fires inside coroutines and generators with readable locals**
   (`locals=['tag','y']`), so `--focus`/`watch` inside `async def` need no
   new capture mechanism — only a frame to attach to.
4. `PY_THROW`'s callback receives the exception object (`(code, offset,
   exc)`); `PY_YIELD` receives the yielded value (`None` for
   `asyncio.sleep(0)`, a `Future` for a real wait); `PY_RESUME` receives
   `(code, offset)`. `STOP_ITERATION` fires for the artificial StopIteration
   when an awaited coroutine returns — control flow, ignored like
   `StopIteration` is today.
5. At `PY_RESUME`, `asyncio.current_task()` is the resumed task and
   `frame.f_back` is the event loop's `_run` — resumption is entered by the
   loop; the awaiting coroutine, when there is one, is the frame's *parent*,
   derived at `PY_START` exactly as arc 1 does (`await inner()` →
   `inner.f_back` is the awaiter).
6. **Cost floor:** on 20 000 awaits, YIELD+RESUME add 40 000 callbacks at
   ~114 ns each before any writing. An await-heavy program roughly doubles
   its event count; a program with no suspension pays nothing new.

Consequences the design takes from these: no per-task stacks are needed
(parentage is already derived per frame; `--window` becomes an ancestry
flag on the frame entry, §D1); "abandoned" and "cancelled" are facts the
trace holds, not inferences (§D2); the only residual state is "suspended at
end of recording" (§D2); the per-event cost is the same order as every other
event (§D8).

## D1. Recorder: frames for everything, suspension as events

**Framing.** `_classify` stops deciding *whether* code is framed; every
traced code object gets a frame at `PY_START`. `_GENLIKE` survives only to
label the frame's **kind** — `function`, `generator`, `coroutine`,
`async_generator` — written to the new `frames.kind` column (§D3). The
`frameless` gates in `_on_start`, `_on_line`, `_exc_event` and the window
accounting are removed; the `unframed`/`parent_frame` CALL-payload keys stop
being written (no unframed call exists in a format-3 trace). `_note_caller`'s
`caller_code` survives for its one remaining case — a traced caller whose
frame started before recording did — and `tree`'s tag wording follows (§D4).

**Three new subscriptions**, each a callback that honours `in_hook` like the
others and looks its activation up in `tls.live` by frame identity:

| monitoring event | recorded as | payload |
|---|---|---|
| `PY_YIELD` | event kind `YIELD`, `line = frame.f_lineno` | `awaiting`: the **type name** of the yielded object (`Future`, `NoneType`, `Task`, a program class name) — `plain_str(type(v).__name__)`, never `repr`: no program dunder runs, nothing large is stored |
| `PY_RESUME` | event kind `RESUME` | none |
| `PY_THROW` | event kind `RESUME` | `thrown`: `capture_exc(exc, serial)` — the exception now in flight in that frame |

`STOP_ITERATION` is not subscribed. `YIELD`/`RESUME` are recorded into the
same events table, stamped with thread and task like every event, and are
**never** passed to `Fingerprint.update` (§D6, honesty rule 3).

**The live entry** `[frame_id, code, code_id, prev_locals, depth]` gains
two slots: `suspended` (set on YIELD, cleared on RESUME; read at `uninstall`
to write nothing — an entry still present and suspended is the §D2
"suspended at end of recording" state, which the reader derives) and
`in_window` (true if this code is the `--window` target or the parent entry's
`in_window` is true). `tls.window_depths` is retired: `_on_line` consults
`entry.in_window`. This is exact per activation and survives suspension —
a coroutine parked inside the window keeps its descendants in the window
when it resumes, and a different task's helper running *during* that
suspension is not in the window, which the per-thread counter got wrong.

**Close paths** are arc 1's: `PY_RETURN`/`PY_UNWIND` delete the entry by
frame identity when `entry.code is code`. Because suspendable frames can
now be in the map while other frames start and end, the `code is` check on
every lookup is what keeps a recycled address from matching a stale entry —
arc 1's constraint #1 is met by observation (fact 2: the frame's own
`PY_UNWIND` removes it) plus the guard, not by a counter.

**Exceptions inside suspendable frames** get frame ids: `_exc_event`'s
lookup is the same `tls.live[id(frame)]` with no kind exclusion. The
existing in-flight bookkeeping (`_ExcRefs`, serials, RERAISE handling) is
unchanged; `RESUME` with `thrown` uses `refs.identify(exc)` so the serial on
the RESUME row is the serial the following `PY_UNWIND`'s `unwind_exc`
carries — that equality is what §D2 uses to say "cancelled", not a type
check alone.

**Retired:** the record-time warning "`--focus X matched only
coroutine/generator code`" and `meta.focus_unframed` (the situation cannot
arise; `Tracer.unframed_focus()`, `_focus_hits` go with it; the boot test is
replaced by one that shows `--focus` on a coroutine records LINE).

**Unchanged:** task identity (`_task_serial`, stamped on RESUME too),
`_parent_of`, `_note_caller`, `plain_str`/`capture_value` guards,
`_LateWriteGuard` (which gains no new method — `add_event` carries the new
kinds).

## D2. Frame states — derived, never stored

A frame's state is a deterministic function of `closed_by`, `unwind_exc`,
and its own last events. The reader computes it; nothing in the recorder
"decides" a state.

| state | evidence |
|---|---|
| **returned** | `closed_by = 'return'` |
| **raised** | `closed_by = 'unwind'`, and the unwind's serial is NOT the `thrown` serial of the frame's last `RESUME` |
| **cancelled** | `closed_by = 'unwind'`, last own event sequence `YIELD … RESUME(thrown=CancelledError, serial s)`, `unwind_exc.serial == s` |
| **abandoned** | same shape with `GeneratorExit` — the program dropped the generator/coroutine while it was suspended |
| **unwound by a thrown-in exception** | same shape with any other thrown type (`gen.throw(ValueError)`) — named, not classified further |
| **suspended at end of recording** | `closed_by IS NULL` and the frame's last own event is `YIELD` |
| **open** | `closed_by IS NULL` otherwise — running (or abandoned *unobserved*) when recording stopped |

"Last own event" means the last event with that `frame_id` of kind
`YIELD`/`RESUME`/`CALL` (LINE rows do not change the state). The state names
the parked line: `suspended at L29`, `cancelled (CancelledError thrown in at
L29)`. The reader exposes it as `Trace.frame_state(frame) -> (state, line,
exc | None)`, used by `tree`, `frame`, `exceptions`.

## D3. Schema — trace format 3

`TRACE_FORMAT` 2 → 3. Additive only; no existing column changes meaning.

- `frames.kind TEXT` — `function` | `generator` | `coroutine` |
  `async_generator`. Absent on formats ≤ 2; the reader returns `function`
  for framed code and keeps the arc-1 unframed machinery for the rest.
- events: new `kind` values `YIELD`, `RESUME`; payload keys `awaiting`,
  `thrown`.
- `task_fingerprints (task_id INTEGER PRIMARY KEY, name TEXT, hash TEXT NOT
  NULL, n_events INTEGER NOT NULL)` — written by plan 2b; created by the
  format-3 schema now so 2b is not a second format bump. `fingerprints`
  (per thread) is unchanged in shape; its *meaning* narrows in 2b (§D6).
- The CALL-payload keys `unframed` and `parent_frame` are no longer written.
  `caller_code` / `caller` are.

A real format-2 trace, recorded by 0.2.0 under `env -i` (the arc-1 fixture
discipline), is committed before the bump; the fixture tests assert that a
format-3 reader renders it with arc 1's wording — unframed lines, the
"ambiguous / no frame recorded" arm, `(name unreadable)` — and never claims a
state it cannot derive.

## D4. Query surface

**`tree`.** Coroutine and generator frames render like every frame — `fN
eM qual(args)` — with a kind marker and a state tail from §D2:

```
task t2: task-A
  f3 e3 worker(name='A')  [coroutine] -> 'A:3'
    f4 e4 step(task='A', n=1) -> 'A:1'
task t3: task-B
  f5 e6 worker(name='B')  [coroutine]  ~ cancelled (CancelledError thrown in at L29)
    f6 e7 step(task='B', n=1) -> 'B:1'
```

Tails: `-> value`, `!! Exc(...)` (raised), `~ cancelled (… at Ln)`,
`~ abandoned (dropped while suspended at Ln)`, `~ unwound by Exc thrown in at
Ln`, `~ suspended at Ln at end of recording`, `(open)`. Task grouping,
footers, `--limit`/`--depth` accounting are arc 1's; the unframed-call lines
and the `<- NAME (unframed)` tag appear only for format ≤ 2 traces; on
format 3 a `caller_code` tag reads `<- NAME (no frame: started before
recording)`. `--around eN` on a `YIELD`/`RESUME` event resolves to its frame.

**`frame`.** Header gains the kind and state: `f5 main.py:worker
[coroutine]  [e6..?]  thread 1  task t3 (task-B)  depth 0  state: cancelled at
L29`. The timeline interleaves LINE rows with `~ YIELD L29 awaiting Future`,
`~ RESUME`, `~ RESUME (CancelledError thrown in)`; children include coroutine
children. `--fn` counts framed activations only (every activation is framed
on format 3); the arc-1 "recorded but not framed" answer survives for old
traces.

**`exceptions`.** The five dispositions apply to handlers inside suspendable
frames under the existing evidence rules (a HANDLED in a frame whose
`closed_by = 'return'` and no later RAISE of the serial → swallowed, etc.).
The "handled at eN … no frame recorded → ambiguous" arm survives only for
format ≤ 2 traces. One rule is added for the new shape: **a frame unwound by
a thrown-in exception (§D2 cancelled/abandoned/thrown) does not make an
earlier handler in it ambiguous** — the handler's exception did not
propagate; the frame later died of something thrown in after a YIELD. The
rendering says so: `swallowed at eN in worker (frame later cancelled at L29)`.

**`watch`.** Sites exist in coroutine frames exactly as in sync frames (CALL
args, LINE deltas). `--at mod:coroutine` on a run recorded with that
`--focus` evaluates; the arc-1 "opens no frame in this version" explanation
survives only for old traces. A `YIELD`/`RESUME` row is not a site (no
locals snapshot is taken at suspension — the LINE before it is).

**`info`.** `recorded:` gains `YIELD n  RESUME n`; `unframed calls:` reads
`0 (all calls framed in format 3)` on new traces; `tasks:` as arc 1.

**`grep`.** `e12 YIELD   worker L29 awaiting Future`, `e14 RESUME  worker`,
`e15 RESUME  worker thrown CancelledError() L29`.

**`flow`.** Unchanged; values captured at LINE/CALL/RETURN inside coroutines
are now reachable.

## D5. `--focus`, `--window`, `--include` inside async code

`--focus mod:qualname` on a coroutine records LINE for its frame. `--window
QUAL` with a coroutine target keeps every descendant activation in the
window across its suspensions and excludes anything that ran in another task
meanwhile (§D1 `in_window`). A sync helper called from two tasks, one inside
the window and one not, is captured only for the in-window task — which is
the first time `--window` means what its docstring says under concurrency.

## D6. Plan 2b — per-task fingerprints

Recorder: each task serial owns a `Fingerprint` over its `CALL/RETURN/RAISE/
HANDLED` events (never YIELD/RESUME/LINE); the thread fingerprint covers
only events with `task_id IS NULL`. At `uninstall`, `task_fingerprints`
rows `(task_id, name, hash, n_events)` are written beside the per-thread
rows.

Comparison (`refocus`, `diff`): thread streams as today, plus tasks compared
as a **multiset of `(name, hash)`** — order-independent, so a different
interleaving cannot manufacture a DIVERGED, and two tasks sharing a name
are matched by content. DIVERGED names the task stream(s) with no
counterpart and, for the first such pair sharing a name, the first differing
`(file, qualname, kind)` with a drill-in command on each side. REFUSED when
there is nothing to compare. The licence adds, beside the recorder-footprint
blind spot: `N task stream(s) compared by content; the ordering between
tasks is not compared`. `diff` gains `--task NAME` to diff one task's stream
by name. Unnamed tasks (`name IS NULL`) match only unnamed tasks.

## Honesty rules (arc 2)

1. A suspended frame is never rendered as running; its state names the
   line it is parked on.
2. "Cancelled" and "abandoned" are claimed only on an observed thrown-in
   unwind whose serial matches; a frame still suspended when recording
   stopped is "suspended at end of recording" — not abandoned, not open.
3. `YIELD`/`RESUME` never enter a fingerprint (their count depends on
   contention); the awaited object is recorded as a type name only.
4. Format ≤ 2 traces keep arc 1's wording everywhere — no retroactive state
   claims, no retroactive dispositions.
5. `exceptions` decides handlers inside suspendable frames by the same
   evidence rules as sync frames; the D4 thrown-in rule is stated on the
   line, not implied.
6. Cost is disclosed: the README states the measured per-event cost of
   YIELD/RESUME with provenance, and that await-heavy programs roughly
   double their event count.

## Verification

Project norms: tests first, each mutation-checked (`__pycache__` purged,
`PYTHONDONTWRITEBYTECODE=1`); corpus questions registered before their
programs are run; matrix 3.12/3.13/3.14 (`PY_YIELD`/`PY_RESUME`/`PY_THROW`
exist since 3.12).

Corpus — **re-registered** (the changes are the point):
- `generator_swallow`: the under-claim lifts → `dispositions: swallowed 2`,
  the `no frame recorded` line gone. The case's docstring records that this
  was an under-claim by contract until frames existed.
- `async_cancelled`: task-B's `worker` frame shows `~ cancelled (CancelledError
  thrown in at L29)`; `where-was-b-when-cancelled` pins the state, not only
  the RAISE.
- `async_focus`: `watch --at main:worker --expr "name == 'A'"` reports a HIT
  with the site; `NOTHING WAS CHECKED` must be absent.
- `async_interleaved`: `update` frames are children of `writer` frames;
  the `<- writer (unframed)` tags are gone; the task-group pins stay.
- `unframed_callers`: `parse` frames are children of the `rows` generator
  frame; `rank` unchanged.

Corpus — **new**: an abandoned generator (dropped while suspended → `~
abandoned`); a generator suspended at end of recording; `--window` on a
coroutine while another task's helper runs during its suspension (the
helper must be outside the window); a FastAPI-shaped async handler calling
a sync helper, recorded with `--focus` on the handler, `watch` HIT inside it
— the field acceptance target, to be tried on CastleVTT after merge.

Bench: an await-dense workload; the measured per-event cost goes in the
README; a divergence of an order of magnitude from the 114 ns callback floor
is a finding to record, not restate.

## What is still out of scope

Subprocess following; live attach; rr adapter; MCP wrapper; sub-line
(expression-level) capture. Still stated in the README.

## Constraints carried from arc 1, and how this spec meets them

1. *A suspendable frame entering `tls.live` requires a terminal ABANDONED
   state.* Met: abandonment is observed (`PY_THROW(GeneratorExit)` +
   `PY_UNWIND`) and the residual is named "suspended at end of recording";
   the `code is` guard stays on every lookup.
2. *Fingerprints per task; interleaving not compared.* §D6.
3. *`task_serial` is the key.* `task_fingerprints.task_id` is the serial;
   names ride for matching by content.
4. *Erratum: `task_id NULL` = no current asyncio task.* Unchanged; 2b's
   thread fingerprint is defined over exactly those events.
