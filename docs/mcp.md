# sensorium as an MCP server

One process over your own store, speaking the Model Context Protocol on stdio;
no runtime dependency was added to serve it, and every query command the
README teaches except `redact` is a tool with the same words on it.

This page is what a client is offered, what a result means, what the server
refuses and what it does not do yet. The tool table below is pasted from
`sensorium.mcp.tools.table(True)` and pinned to it cell by cell by
`tests/test_mcp_docs.py`: a reworded command changes both or neither.

## Registering

    claude mcp add sensorium -- <venv>/bin/sensorium mcp --allow-run

**From the project's own venv, by absolute path.** `record` spawns
`<interpreter> -m sensorium run -- <your command>`, and that interpreter is
the server's own unless the call sets `python`; Python `refocus` re-runs the
recorded target inside that same child. A server started from some other
environment therefore records your program under an interpreter that cannot
import its dependencies. `<venv>/bin/python -m sensorium mcp` is the same
thing; a bare `sensorium` off `PATH` is not, for the reason a stale driver is
never the one you meant.

`--store DIR` is the trace store to serve: resolved to an absolute path and
exported as `SENSORIUM_DIR` before the tool table is built and before any
child is spawned, so the server and every call it makes read one store.
Without it, the store it inherited (`$SENSORIUM_DIR`, else `~/.sensorium`).

| flag | default | what it does |
|---|---|---|
| `--allow-run` | off | offer `record` and `refocus`, the two tools that execute your program |
| `--store DIR` | the inherited store | the store to serve, as `SENSORIUM_DIR` for the server and every call |
| `--max-output BYTES` | `65536` | cap one answer's body; minimum `4096` |
| `--timeout SECONDS` | `60` | how long one query tool may take |
| `--run-timeout SECONDS` | `600` | the same bound for `record` and `refocus` |

A bad flag is a refusal to START, in the CLI's words on stderr and exit 2 --
there is no client yet to send JSON-RPC to:

    sensorium mcp: --max-output 10 is below the 4096-byte minimum
    sensorium mcp: --timeout 0 is not a positive number of seconds

Diagnostics go to stderr and nothing else does: stdout is JSON-RPC. One line
names the surface at boot (`serving 11 tools (allow_run=True) store=...`), one
per handshake, one per spawned child (`child <pid> pgid <pid> tool <name>`),
one for the exit reason (`exit 0 (eof)`, `(sigterm)`, `(pipe)`).

## The tools

Eleven with `--allow-run`, nine without, listed in this order. Each
description is the command's own `help=` and `description=` -- the two
sentences `sensorium <cmd> --help` prints -- and each tool's fields are read
off that command's parser, so neither a sentence nor a flag can disagree with
the CLI.

| tool | present | description |
|---|---|---|
| `runs` | always | list recorded traces. One line per trace, oldest first: run id, exit, event count, the command; a refocus rerun names its original and its verdict. |
| `info` | always | summarize one trace. Recorder, language, the capabilities the trace declares, what was recorded and what was not, focus, the redaction stamp; read it before any other question on a run. |
| `tree` | always | call-tree slice. Parentage derived from the event stream; `--around` centres the slice on an event id, `--root` on a frame id; nested dict contents are elided, `frame` prints them. |
| `frame` | always | one activation in full. Arguments, return or raise, and the per-line locals timeline when the run was recorded with `--focus`; frame ids fN come from `exceptions`, `tree` and `grep`. |
| `grep` | always | search events by name or value. Every CALL, RETURN, RAISE, HANDLED or LINE event whose name or rendered value contains the pattern; `--after` resumes from an event id a previous answer showed. |
| `exceptions` | always | raises, handles, swallows. Every raise classified swallowed, uncaught, re-raised, propagated or ambiguous, with the reason; SWALLOWED is claimed only when the recording proves it. |
| `flow` | always | provenance of a value or an object. `--value` follows a literal by equality through captured arguments, locals and returns; `--object` follows one identity from the event that captured it; one of the two is required, and each refuses by name what the recording did not capture. |
| `watch` | always | predicate over captured state. A gdb-style watchpoint evaluated after the fact at every recorded site of one function; needs a `--focus` recording, and NOTHING WAS CHECKED is a refusal, never a pass. |
| `diff` | always | first causal divergence between two runs. Aligns the two causal streams and names the first event where they part, with drill-in commands; MATCH or DIVERGED, or REFUSED when no verdict exists. |
| `refocus` | `--allow-run` | re-run a recorded command with deeper capture, verified. Executes the recorded command again with the added `--focus` and reports whether it was the same execution — MATCH, DIVERGED or REFUSED; the licence names what was compared. |
| `record` | `--allow-run` | record one execution. Runs the command under the recorder from `cwd` and writes one trace; only code under `cwd` is recorded; the command is a .py file, a `-m` module or a console script, never `python` itself. |

`redact` is a query command too, and deliberately NOT a tool: it rewrites
a stored trace, which is not a question anyone asks a debugger, and the store's
owner runs it from a shell. A call to it answers `-32602 Unknown tool: redact`.

## Reading a result

Every result's FIRST line says what happened, and it is the four exit
meanings' own words rather than a second copy of them:

    exit 0: the trace answered affirmatively
    exit 1: the trace answered negatively -- no match, no frame, no exception, none
    exit 2: the call is wrong -- fix the arguments and ask again
    exit 3: the trace cannot settle it -- change the recording and re-record

Two statuses are not that four-way contract and say so. `record` is the CLI's
`run`, whose exit is the recorded command's own, so its header reads `exit
<N>: the recorded command's own status (2 and no trace when recording was
refused)` -- an `exit 2` there means your program exited 2, or that recording
was refused and there is no trace, never "the call is wrong". A child killed
by a signal has no status at all and reads the same on every tool
(`exit -15: killed by SIGTERM`, or `signal 35` for one CPython does not name);
an exit outside the contract is named rather than rendered as an answer
(`an exit outside the query contract`).

A call that produced no exit -- a timeout, a cancel, a spawn that never
happened -- has no number to report, and inventing one would be a lie a model
acts on. It reads

    no answer: timed out after 60 s (server flag --timeout / --run-timeout)

Below the header is the child's stdout, then, whenever stderr is non-empty,
this label on a line of its own and the child's stderr under it:

    --- stderr ---

The label is always present when there is stderr, even with an empty stdout,
so a client can split the text back into `(stdout, stderr, exit)`. One byte is
lost in doing so: a stdout that lacked its trailing newline gains one before
the label, and that case alone cannot be reassembled byte-exactly.

A result is TEXT, and only text: the exit's machine-readable carrier is the
header line, read off its first token. No result carries `structuredContent`
and no tool an `outputSchema` -- a client may show a model the structured twin
INSTEAD of the text, and the deploy target we measured does exactly that.

`isError` is set exactly when the exit is 2 or there is no exit: 2 is the call
the model should repair itself, which is what the protocol says the flag is
for, while 1 and 3 are answers ABOUT the trace and a signal is a death, not a
misuse. The key is omitted, not sent `false`, when it does not apply.

## `run` defaults to `last`

Every query tool's `run` field is optional and defaults to `last`, the most
recently written trace. The CLI's own `run` positional is still required --
the default lives in the tool schema, so a model can ask `exceptions` a
question without a `runs` call in front of every one. It is also the one thing
that can hand back the wrong trace: after a `record` that was REFUSED there is
no new trace and `last` is the old one, which is why `record`'s header says
*no trace* in that case and `info` names the command on its first line.

## The cap

One answer's body is capped at `--max-output` bytes, 64 KiB by default,
beneath whatever silent cap the client applies of its own. The cut keeps a
HEAD and a TAIL, not a head: `diff` and `refocus` print their verdict and
their drill-in commands LAST, and a model handed only the head of a DIVERGED
answer has the exit and not the fork. Up to 4 KiB (at most a quarter of the
limit) is kept from the end. The header line is never cut -- the cap applies
to everything after the first newline -- and what was removed is named on its
own line, which is not itself counted against the limit:

    [... 1,284 lines (57,113 bytes) omitted; narrow with: depth, limit, around ...]

`narrow with:` lists the fields THIS tool narrows by: `depth, limit, around`
on `tree`, `limit, after, fn, kind` on `grep`, `fn` on `frame`,
`limit, after` on `exceptions` and `flow`, `limit, after, misses` on `watch`,
`context` on `diff`. A tool with none -- `runs`, `info`, `record`, `refocus`
-- says `narrow with: nothing on this tool`. Both kept halves are cut back to
a line boundary when the kept window holds a newline; a window without one is
a raw byte cut and may begin or end in U+FFFD.

## `--allow-run`

Without the flag the table has nine tools: `record` and `refocus` are absent
from `tools/list`, and a call to either comes back `Unknown tool: record` --
the wire shows no trace of the flag, because a tool the server will not offer
is a tool it does not have. With the flag:

* **`record`** takes `command` (required: the program as its own argv -- a
  `.py` file, `-m` and a module, or a console script, with its arguments, and
  never `python`), `focus`, `include`, `exclude`, `window`, and two fields that
  are the child's PROCESS rather than its arguments: **`cwd`**, the directory
  to record from, which also bounds what gets recorded, and **`python`**, the
  interpreter to record under, which must import sensorium and your program's
  dependencies. Both default to the server's own.
* **`refocus`** re-runs the command a trace remembers with a deeper `--focus`
  and reports whether it was the same execution.

**Every call inherits the server's whole environment**, `record` included,
plus the `SENSORIUM_DIR` that `--store` exports. That is not incidental: it is
how the CLI's own `SENSORIUM_*` variables and your program's own variables
(a `PATH`, a `VIRTUAL_ENV`, a database URL) reach the child at all. There is no
`env` field on `record`, nothing a model types can add a variable, and nothing
is filtered out on the way in -- so whatever the MCP client's environment
holds, tokens included, is the environment your program is recorded under.
Start the server from an environment you are willing to record under. What a
RECORDING then keeps of it is the redaction rule's business (values are
withheld at the writer, which is why an `env` field was left out on purpose);
what the AUDIT keeps of it is nothing at all, as the section below says.

**Stdin is `/dev/null` for every call, without exception** -- the server's own
stdin is the JSON-RPC stream, and a child that inherited it would read the
client's next request and stall the session with neither side at fault. So a
recorded program that reads stdin sees EOF, and the recording is stamped
`stdin_consumed`; `refocus` then refuses it by name, because a rerun reads
different stdin, or none, and no verdict about it would be honest.

**A cancelled or timed-out recording leaves an INCOMPLETE trace.** The
recorder never reached its finalize pass, so exit, uncaught, children and the
truncated counts are UNKNOWN rather than zero; `runs` flags that trace
`[INCOMPLETE]` and `info` says so on the line under its id. It is a real trace
and you can read it; it is not one to conclude anything from about how the
program ended.

## Timeouts and cancel

A query tool gets `--timeout` seconds (60 by default) and `record` and
`refocus` get `--run-timeout` (600), which is the same bound spelled longer
for the two tools expected to take longer. On expiry the call's whole process
GROUP is killed -- SIGTERM, up to two seconds for the group to empty, then
SIGKILL whether or not anything answered -- and the call is answered
`no answer: timed out after N s (server flag --timeout / --run-timeout)`.

`notifications/cancelled` is handled on the reading thread, so it reaches a
call the worker is blocked inside. The same group kill runs, and the cancelled
call is **never answered**: the client has stopped waiting and may have reused
the id. A cancel that lands while the request is still queued removes it, and
nothing is spawned. The request id is compared as the JSON value it arrived
as: `"7"` is not the call whose id is `7`.

## The audit file

`mcp.jsonl` sits beside `invocations.jsonl` at the store root, created 0600
under a 0700 directory -- and re-tightened to 0600 whenever it is opened with
group or other bits on it, so a file left readable by an older build, a
restore or a copy under another umask does not stay that way (the DIRECTORY
keeps whatever mode it has, as it always did) -- and is invisible to every
trace lookup: `runs` and `find_trace` glob `traces/*.db`, and this file is not
under `traces/`. One compact JSON line per answered call, per cancel, and per
REFUSED call -- one naming a tool this server does not have, or one whose
arguments were rejected. A malformed `tools/call` and every
transport-level refusal are answered and NOT audited: no tool was named, so
there is nothing to record them under.

| line | fields |
|---|---|
| a call | `utc`, `tool`, `arguments`, `exit`, `bytes`, `truncated`, `ms`; `timeout: true` when it expired; `cause` when there was no exit and it was not a cancel |
| a rejection | `utc`, `tool`, `rejected: {code, reason, fields, message}` -- `fields` only when there were fields to name |
| a cancel | `utc`, `tool` (null when the cancelled request was not a `tools/call`), `arguments`, `cancelled: true`, `queued` (whether it was still in the queue), `ms` (null when nothing was spawned) |

`reason` is data, not prose -- `unknown_tool`, `unknown_fields`, `bad_fields`,
`missing_fields` -- because a census that had to parse English would stop
matching the first time the wording improved. `bytes` is the length of the
text actually shown and `truncated` whether that was all of it.

What is NEVER written: the process environment, the server's working
directory, the result text. The environment is never written even though every
child RUNS under a copy of it (see `--allow-run` above) -- this file is a
census of CALLS, and the process it ran in is not one of the things it counts.

Arguments pass the redaction content rule before they are written, and that
includes a tool name, a field name and a rejection message, which are
model-typed text like any other. What that rule does, exactly: it replaces the
SPANS it recognises -- nineteen shapes, each with a minimum length, listed in
[`docs/trace-format/redaction-v1.json`](trace-format/redaction-v1.json). A
value it recognises (an `AKIA…`, a `ghp_…`, a bearer header, a URL's
userinfo) leaves `<redacted>` here instead of itself; a value it does not
(`hunter2`, an internal token in no published shape) is written as typed. It is
a floor, not a secret scanner, and this is not the only place an argument
appears: the CLI's own stdout may echo one back, and the result text is what
the client shows the model. `record`'s own `cwd` and `python` are ordinary
arguments of that call and are written as such, through the same rule.

`SENSORIUM_NO_INVOCATION_LOG` disables this file too -- one word for "log
nothing about my calls", read through the invocation log's own knob rather
than re-implemented; the server says so once on stderr at boot
(`audit off (SENSORIUM_NO_INVOCATION_LOG)`). Nothing here raises: a location
it cannot write to prints one line and returns. Each call ALSO lands in
`invocations.jsonl`, written by the child the way any `sensorium` invocation
is, and the server's own process writes one line there when it exits.

## What the server refuses

An unknown tool is a protocol error, because there was nothing to run:

    -32602  Unknown tool: recrod

A call whose ARGUMENTS are wrong is not. Both eras reserve `-32602` for
unknown tools and malformed requests and route argument validation through
`isError`, which is the channel the model sees and repairs from -- naming the
fields in an error the client swallows would defeat the point of naming them.
So it comes back as an ordinary result, `isError` set, in the CLI's exit-2
words, with ONE of three reasons under them -- here all three on `grep`:

    exit 2: the call is wrong -- fix the arguments and ask again
    unknown field 'depth' for grep; fields: run, pattern, kind, fn, after, limit
    bad value for 'limit' on grep: expected integer
    missing required field(s) for grep: pattern

Unknown fields are checked first, then bad values, then missing ones, and
whichever category fires names all of its offenders at once: a caller told of
one bad field at a time needs one round trip per mistake, and a missing field
reported ahead of a misspelt one sends the retry after the wrong thing. The
rest are protocol errors:

| code | when |
|---|---|
| `-32602` | an unknown tool; `tools/call needs a string name and an object arguments`; `server/discover` without `_meta` protocolVersion; a modern request without `_meta` `io.modelcontextprotocol/clientCapabilities`; a legacy request before `initialize` |
| `-32022` | a `_meta` protocolVersion this server does not speak; the data carries `supported` and `requested` |
| `-32601` | an unknown method |
| `-32603` | our bug -- one stderr line naming the class, and `{"type": "<ClassName>"}` in the data; the request is answered rather than lost |

Transport-level refusals are `-32700` (a line that is not JSON, answered with
a null id), `-32600` (a batch, which left the protocol in 2025-06-18; or an
object with no string `method`) and `-32602` for a `params` that is not an
object. A blank line is not a message and is skipped.

## Protocol

Four revisions: **2026-07-28**, **2025-11-25**, **2025-06-18**,
**2025-03-26**. Both lifecycles are served by one process. A request whose
`_meta` carries `io.modelcontextprotocol/protocolVersion` is answered
statelessly under 2026-07-28's per-request model; a request without that KEY
is legacy and needs `initialize` first (`initialize` and `ping` are the only
methods exempt). The key's absence decides, never its value -- the official
SDK sends `"_meta": {}` on every legacy request. A client may open with
either; the E17 record's H7 row names the one Claude Code opened with.

`initialize` echoes the offered version when it is one of the three legacy
ones and answers `2025-11-25` otherwise, returning `capabilities`,
`serverInfo` and `instructions` -- a short paragraph telling the model to
start at `runs`, that ids from one answer are arguments to the next, and what
the four exit statuses mean. `server/discover` is the modern probe and returns
the same instructions plus `supportedVersions`.

A modern result carries `resultType: "complete"` (we never stream) and `_meta`
with `io.modelcontextprotocol/serverInfo` -- name and version. A listing and
`server/discover` also carry `ttlMs` and `cacheScope: "private"`: the tools are
this process's CLI over one developer's store. `title` arrived in 2025-06-18
and a 2025-03-26 client is not sent one. `ping` is answered on the reading
thread, never queued, so a liveness check behind a three-minute `record` does
not report the server dead while it is working; `notifications/cancelled` is
handled there too.

* [2026-07-28 basic/versioning](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning)
* [2026-07-28 basic/transports/stdio](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio)
* [2026-07-28 server/tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
* [2025-11-25 basic/lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)

## Not in this version

* **Streamable HTTP, authentication, tenants, upload, name lists, tier
  gating** -- the hosted slice; this surface is meant to be what it runs per
  tenant, unchanged.
* **Traces as MCP resources, prompts, tool-list-changed notifications,
  progress notifications, streaming output** -- none demanded yet; a census
  line showing the demand is what adds one.
* **A per-call timeout field** -- waiting on the timeout census.
* **An `env` field on `record`** -- a secret-into-trace vector, left out on
  purpose.
* **`redact` as a tool, `seal` and scanner parity** -- as the redaction work
  left them.
* **Rewriting the debugging skills to prefer MCP over the shell** -- a ruling
  after E17's H7, not before it.
* **Concurrent calls** -- serialized by design: the store is SQLite and a call
  is a child process, so the honest offer is one question at a time. A client
  that fans out is slower, not wrong.

## On Windows

Advisory and untested. There are no process groups, so the timeout and cancel
kill falls back to `terminate` on the child leader, a grace wait, then `kill`
-- anything that child spawned and that ignored the signal survives. The 0600
mode on `mcp.jsonl` and the 0700 on the store root are POSIX modes and mean
something else there. The server does not refuse to start; nothing on this
page about the kill or the file modes is claimed for it.
