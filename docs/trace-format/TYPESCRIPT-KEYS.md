# TypeScript-only meta keys (TRACE-FORMAT §4)

> Split out of `docs/TRACE-FORMAT.md` on 2026-09-09 (S5 rung 1) to keep that file under its 800-line ceiling, the same way §8's vector table was in 2026-09-04. Section numbering in TRACE-FORMAT is unchanged; that file's §4 is a pointer here.

Written by `sensorium ts ingest`'s builder (`src/sensorium/ts/build.py`,
`_meta` / `_container_meta` / `_invocation_meta`) and read by `info`,
`runs` and `Trace`. **Every one is printed only when the trace carries the
key**, so a TypeScript trace from an older converter simply says less —
never a zero, never "predates". Nothing here is required: the required set
is §4's, and it is the same for every language.

The keys divide by who knew the fact. The **invocation** keys are the
driver's and are identical on every trace of one `sensorium ts run`; the
**container** keys are one process's own; the **recording** keys are what
the conversion counted.

## Invocation — the driver's, identical across the invocation's traces

| Key | Meaning, and what reads it |
|---|---|
| `invocation` | The id of the `sensorium ts run` invocation this container belongs to. `runs` groups every trace of one invocation under a header naming the harness command (§6). |
| `harness` | `"vitest"` or `"node-test"` — the KIND of harness the driver recognised and wired. Not a program name: `node-test` is not a command. Which header `runs` prints is decided by `meta.lang`, never by this key being present (R27a). |
| `harness_command` | **The tokens the user typed after `--`**, before the driver consumed `--root`/`--config` out of them and before it re-issued its own: `["npx", "vitest", "run", "src/fog"]`. This is the one list here that is a COMMAND, and it is what `runs`' header and `info`'s `harness:` line print, joined by spaces (R26). Absent from a trace whose converter predates the key; the readers then fall back to `harness` + `harness_args`, which reconstructs a command nobody typed. |
| `harness_args` | The arguments **after** the harness word with `--root`/`--config` taken out, because the driver re-issues those itself (`ts/harness.Plan`). Machinery, not a command: nothing prints it where `harness_command` is present. |
| `harness_exit` | `{status, signal, basis}` — what the driver **waited for**, `basis` always `"waited"`. `status` and `signal` are exclusive. `runs`' header: `exit:1 (waited)`; `info`: `harness: vitest run src/fog  exit: 1 (waited)`. Absent when the driver was killed before the harness returned, which is not a harness that ended at 0. |
| `vitest` | The harness version, when one was read. `info` prints it in the parenthesis beside the interpreter: `node v24.16.0 (vitest 4.1.9, jsdom)`. |
| `driver_version` | The `sensorium ts` driver's own version. |
| `files_transformed`, `transform_excluded` | How many files the transform edited, and `{reason: count}` for the ones it refused. `info`: `files: 41 transformed; excluded: 3 (vitest-hoisted-factory x3)`. **By reason, never a bare count**: the reasons are the difference between "nothing happened in that file" and "nothing was watching it". The GRAIN follows the harness: vitest transforms once for the whole invocation, so every container of it carries the same numbers; `node --test` runs one child process per test file, so a trace carries what its own container transformed. Absent when nobody counted, never written as a zero. |

## Container — this one process's own

| Key | Meaning, and what reads it |
|---|---|
| `pid`, `ppid` | Process identity within the invocation. `info`: `container: pid 4242 …`. |
| `thread_id_os`, `is_main_thread` | Node's own `threadId`, and whether this container is the harness's main process or one of its workers. `info` prints `thread 0 (main)` / `thread 3 (worker)`. Worth a word because it says what the absent thread record means here: a worker's siblings are **other traces of this same invocation**, unlinked. |
| `node` | The Node version string, read off the container's own boot record. `info`'s interpreter line is `node <node>`, where a Python trace's is `python <version>`. |
| `wire` | The spool protocol version the runtime wrote. Read by the spool reader; nothing prints it. |
| `environment` | The vitest environment (`node`, `jsdom`, …) where exactly one was seen. In `info`'s interpreter parenthesis. |
| `test_file` / `test_files` | The root-relative path of the one test file this container ran, or the list where a reused worker ran several. `runs` prints `file: <path>` or `files: N` in place of a `cmd:` (§6); `info` prints the same beside the container line and keeps the whole argv on its `cmd:` line. **Carrying neither is a statement**: this container ran no test file (a `globalSetup`, any `node --test` process) and keeps its argv. |
| `exit_self_reported` | `{code, signal}` — what the container said about its **own** ending, from inside, on the way out. `info`: `container exit: self-reported code 1 (nobody waited)`. Absent where the container never got to observe its own ending, which is not the same fact as one that ended at 0. Distinct from `harness_exit` (waited, another process) and from `exit_status` (§4: always null / `unwitnessed` here, because the driver spawned the harness and not its workers). |

## Recording — what the conversion counted

| Key | Meaning, and what reads it |
|---|---|
| `tests_seen` | How many tests the **harness** registered, counted by the setup file. `info`: `tests: 11 as tasks, 11 seen by the harness`, and names the shortfall when they differ — a test the transform did not wrap ran and was recorded by nothing, so a bare task count would read as the whole file. **Present only where the counter ran**: the spool carries a `SEEN` or a `FILE_START`, or the invocation was vitest, whose setup file always runs. `node --test` runs no setup file, so its traces carry no key and `info` prints `tests: N as tasks` alone — never a zero nobody measured. |
| `task_name_basis` | Which rule named this trace's tasks: the provider's (`vitest`), the lexical `describe > title`, or `mixed`. Printed as `; task names: vitest`. |
| `task_name_conflicts` | Provider names that did not end with the string literal the transform passed; the task fell back to its lexical title and the disagreement was **counted rather than resolved**. Printed beside the basis it qualifies — alone it would name no rule to doubt. |
| `unhandled_rejections` | `[{type, msg, serial}]` from `process.on('unhandledRejection')` — a fact with no SITE, so it is here and never in `events` (§5). `info` prints the count, **including a zero on a complete trace**: the listener always ran, so that zero is measured. |
| `throw_flow_outside_frames` | RAISE/HANDLED records that fired with no open frame — a throw at module scope, a default-parameter expression that threw before its frame opened. There is no frame to attach an event to, so none was written; the count is the only trace of them. Printed when non-zero. |

## Throw flow

> Moved here on 2026-09-10 (S5 rung 2) from `docs/TRACE-FORMAT.md` §5, unchanged — that file stood at 799 of its 800 lines and this rung amends this section, so it moves whole before it is amended.
> That is R25's precedent, the same way §4's key table moved into this file in rung 1: one commit moves a section without changing a byte of it, another edits it in its new home.

A TypeScript `exc` is `{kind, type, msg, serial}` and **`kind` is written on every
one** — `"throw"` or `"rejection"` — because a kindless `exc` is read as Python's
(TRACE-FORMAT §5). `serial` is minted per thrown **object** through a `WeakMap`, so
`catch (e) { throw e }` is one exception with two RAISE rows; a thrown **primitive**
has none to hang it on and gets a fresh serial each time, stated rather than papered
over by merging on text. Vectors: `v25-exc-kind-throw-rejection`,
`v27-unhandled-rejection-in-meta`.

**`how`** names the shape that recorded the event, and the enumeration is the
declaration — a shape outside it produced no record: `throw` (the RAISE a `throw`
statement writes when it fires); `catch` (the binding never left the clause, or
left it only as a `console.*` argument); `catch_escaped` (the binding left the
clause other than through a `console.*` argument). A **bare rethrow** —
`throw e;` at closure depth 0, whose operand after any parentheses is the
binding itself — is a traced EXIT and not a mention, so it does not make a
clause `catch_escaped`, and, by the same rule read over a rejection handler's
parameter, does not make one `catch_callback_escaped` either
(`.catch((e) => { throw e })` is `catch_callback`, while
`.catch((e) => { seen.push(e); throw e })` and `.catch((e) => { throw wrap(e) })`
stay `catch_callback_escaped`); the RAISE it writes carries the same serial and
the rule module reads the pair as a hop (amended 2026-09-10, spec §2.1). Then
`sink_empty_catch` (an empty
`catch {}` block); `catch_callback` (an inline rejection handler whose parameter
never left its body, or left it only as a `console.*` argument);
`catch_callback_escaped` (an inline rejection handler whose parameter left its body
some other way); `catch_callback_opaque` (a handler defined elsewhere);
`sink_empty_catch_callback` (an inline rejection handler with an empty body); and
`sink_finally_return` (a `finally` that completes with a throw in flight, whose
`exc` is the marked throw's own, COMPLETE — `kind`, `type`, `msg` and `serial`
exactly as the RAISE (or the synthetic marking clause) wrote them, nothing unread:
the mark holds the whole `exc` object, not just its serial. Two shapes are
declared blind spots instead (P1): a `try` that already has its own `catch`
clause gets no synthetic marking clause (only a catch-less `try` gains one,
`transform.mjs`'s `spliceFinally`), so an awaited callee rejecting inside that
catch's body, then a completing `finally`, records nothing — a *synchronous*
`throw` inside that same body is a `raise` and marks as usual; and `thr` (a
callee's frame closing by throw) sets no mark of its own, so a throw a callee
unwound with reaches the caller's mark only through the caller's own synthetic
clause, never any other way). What is still recorded by nothing: a
`finally` with no completion statement; `.finally(fn)`, never a handler;
a `Promise.reject(v)`, whose handler's HANDLED carries no RAISE and reads *born
outside a throw statement*; a throw inside a promise executor with no open frame,
counted in `throw_flow_outside_frames`; and a throw in untraced code (`JSON.parse`,
a library), whose HANDLED likewise carries no RAISE and reads *born outside traced
code*.

`sensorium-ts` 0.2.0 declares `capabilities.err_flow: true` in its BOOT record, and
the converter carries that declaration into `meta` over the constant it otherwise
writes (`src/sensorium/ts/build.py`). What the declaration guarantees is the
recorder's own statement that these rows now carry what a disposition verdict
needs. Reading them by rule is `src/sensorium/query/exceptions_typescript.py`'s,
and the refusal is gated on this key rather than on `lang`: a 0.2.0 recording is
JUDGED — five words, `swallowed` the only accusation among them
(`v30-exceptions-typescript-swallowed`, `v31-exceptions-typescript-escaped-ambiguous`)
— and a 0.1.x one refuses at exit 3 with the capability sentence, because what
it lacks is the record (`v32-err-flow-typescript-capability-refusal`). The
lang-keyed sentence that named absent TypeScript rules is retired.

Two things go to `meta` and never to `events`, because §3 refuses a causal event
with no `code_id` and inventing a code object would put a site in the program that
has none: an unhandled rejection (`unhandled_rejections`, `[{type, msg, serial}]`)
and a RAISE/HANDLED with no open frame (`throw_flow_outside_frames`).

## What is deliberately absent

`records_dropped` is **never written by this recorder**. A container killed
by `SIGKILL` did not get to count what it was about to write, and a number
the runtime cannot know is a number this recorder does not put in a trace:
the trace carries `incomplete: true` and the tail is declared unknowable
(`typescript/HONESTY.md` §5). There is also no `scheduled_by` on a
parentless frame: which frame **scheduled** a timer callback is a
relationship this recorder does not record, and depth 0 inside the right
task is the whole of what is claimed (§3 of the same file).
