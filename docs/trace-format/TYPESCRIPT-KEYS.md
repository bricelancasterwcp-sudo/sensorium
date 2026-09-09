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
| `harness` | `"vitest"` or `"node-test"` — the harness the driver recognised and wired. Its presence is what makes `runs` print a harness header rather than a cargo one. |
| `harness_args` | The arguments **after** the harness word (`ts/harness.Plan`), as re-issued. `runs` and `info` print `harness` + these, joined: `harness_args` alone names no program. |
| `harness_exit` | `{status, signal, basis}` — what the driver **waited for**, `basis` always `"waited"`. `status` and `signal` are exclusive. `runs`' header: `exit:1 (waited)`; `info`: `harness: vitest run src/fog  exit: 1 (waited)`. Absent when the driver was killed before the harness returned, which is not a harness that ended at 0. |
| `vitest` | The harness version, when one was read. `info` prints it in the parenthesis beside the interpreter: `node v24.16.0 (vitest 4.1.9, jsdom)`. |
| `driver_version` | The `sensorium ts` driver's own version. |
| `files_transformed`, `transform_excluded` | How many files the transform edited, and `{reason: count}` for the ones it refused. `info`: `files: 41 transformed; excluded: 3 (vitest-hoisted-factory x3)`. **By reason, never a bare count**: the reasons are the difference between "nothing happened in that file" and "nothing was watching it". |

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
| `tests_seen` | How many tests the **harness** registered, counted by the setup file. `info`: `tests: 11 as tasks, 11 seen by the harness`, and names the shortfall when they differ — a test the transform did not wrap ran and was recorded by nothing, so a bare task count would read as the whole file. |
| `task_name_basis` | Which rule named this trace's tasks: the provider's (`vitest`), the lexical `describe > title`, or `mixed`. Printed as `; task names: vitest`. |
| `task_name_conflicts` | Provider names that did not end with the string literal the transform passed; the task fell back to its lexical title and the disagreement was **counted rather than resolved**. Printed beside the basis it qualifies — alone it would name no rule to doubt. |
| `unhandled_rejections` | `[{type, msg, serial}]` from `process.on('unhandledRejection')` — a fact with no SITE, so it is here and never in `events` (§5). `info` prints the count, **including a zero on a complete trace**: the listener always ran, so that zero is measured. |
| `throw_flow_outside_frames` | RAISE/HANDLED records that fired with no open frame — a throw at module scope, a default-parameter expression that threw before its frame opened. There is no frame to attach an event to, so none was written; the count is the only trace of them. Printed when non-zero. |

## What is deliberately absent

`records_dropped` is **never written by this recorder**. A container killed
by `SIGKILL` did not get to count what it was about to write, and a number
the runtime cannot know is a number this recorder does not put in a trace:
the trace carries `incomplete: true` and the tail is declared unknowable
(`typescript/HONESTY.md` §5). There is also no `scheduled_by` on a
parentless frame: which frame **scheduled** a timer callback is a
relationship this recorder does not record, and depth 0 inside the right
task is the whole of what is claimed (§3 of the same file).
