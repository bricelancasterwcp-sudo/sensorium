# sensorium as an MCP server — the local stdio slice

2026-09-16, against `main` @ `7844571` (0.17.0). The first slice of the
product direction Brice ruled on 2026-09-13: sensorium is to be offered as
an MCP service for companies with a free tier for individuals. This slice
ships the free tier as it will be used — one process, `sensorium mcp`, over
the developer's own store, speaking the Model Context Protocol on stdio —
and it is also the exact process a hosted deployment will later run per
tenant. Transport, upload, tenants and authentication are the next slice
(§11).

The design method is `designing-notation-for-llms` (the tool surface is a
notation a model emits) and the measurement method is `rigorous-experiments`
(§9 is pre-registered and both readings are written before the instrument
exists).

## 0. Rulings this design rests on

- **Shape (Brice, 2026-09-16):** local stdio server first. The tool
  surface, the policy knobs and the audit log ship now; a hosted transport
  is a later slice.
- **Execution (Brice, 2026-09-16):** read-only by default. `record` and
  `refocus` — the two operations that run the user's program — exist as
  tools only when the server is started with an explicit flag, default
  off. A hosted deployment never sets it.
- **Approach (Brice, 2026-09-16, of three offered):** the CLI is the tool
  surface. One tool per query command, schemas derived from the parsers,
  results are the CLI's own text, every call a child process. A single
  argv tool (no per-field rejection, no per-tool annotations) and a native
  structured API (a second rendering of every honesty claim) were
  rejected.
- **Design authority (standing, 2026-09-07):** the decisions numbered
  **D1–D34** below are Claude's; merges, scope, money and destructive
  actions are Brice's. Merge is a merge commit.
- **Zero runtime dependencies (standing):** the server is standard
  library only. The official Python SDK enters as a *development* extra,
  as a conformance oracle (§9 H2), never as something the product imports.

## 1. What ships

- `sensorium mcp [--allow-run] [--store DIR] [--max-output BYTES]
  [--timeout SECONDS] [--run-timeout SECONDS]` — a JSON-RPC 2.0 server on
  stdin/stdout, one line per message, that answers the MCP lifecycle
  (both the legacy `initialize` handshake and the 2026-07-28
  `server/discover` model), `ping`, `tools/list`, `tools/call` and the
  cancel notification.
- **Nine query tools** always: `runs`, `info`, `tree`, `frame`, `grep`,
  `exceptions`, `flow`, `watch`, `diff`. **Two more** under `--allow-run`:
  `refocus` and `record` (the CLI's `run`). `redact` is never a tool
  (**D1**: it rewrites the store; the store's owner runs it from a shell,
  a hosted tier runs it server-side).
- Every tool's input schema is **derived at boot** from the command's
  argparse parser (§2). A CLI flag added later is a tool field with no
  MCP change, so the two surfaces cannot drift.
- Every call runs `sys.executable -m sensorium <argv>` as a child in its
  own session (§4). The result is the CLI's stdout under a one-line exit
  header, the exit status also as structured content (§5).
- Policy for this deployment: an output cap with a narrowing trailer,
  the execution gate, and an audit file `mcp.jsonl` beside the invocation
  log (§6).
- The corpus runner gains `--via mcp` and asks its 253 questions through
  the server (§8); E17 measures parity, conformance, the cap, the gate,
  liveness, secrecy and one real Claude Code session (§9).
- Python **0.18.0**. Trace format, the Rust and the TypeScript recorders
  unchanged.

## 2. The tool surface

### 2.1 Names

Tool names are the command names. The model already knows them from
`--help`, the README and the debugging skills, and MCP clients namespace
them (`mcp__sensorium__grep`), so a bare `grep` collides with nothing
(designing-notation §2: familiar spelling, familiar concept).

One exception, **D2**: the CLI's `run` is the tool **`record`**. As a tool
name `run` reads as "execute" in every client's prior and is the same word
as the `run` *field* every query carries; `record` is the README's first
verb and precise.

### 2.2 Descriptions — one source, two surfaces

A tool's description is the parser's `help=` one-liner, a full stop, and
its `description=` sentence — the same two strings `sensorium <cmd>
--help` prints (**D3**). Today every query parser has a `help=` and no
`description=`; this slice writes the eleven sentences below into the
parsers, so `--help` gains them too. Each sentence carries what the prior
does not supply (designing-notation §5): what the answer claims, and the
house meaning of any spelling that collides with a tool the model knows
better.

| tool | help (exists) | description (new) |
|---|---|---|
| `runs` | list recorded traces | One line per trace, oldest first: run id, exit, event count, the command; a refocus rerun names its original and its verdict. |
| `info` | summarize one trace | Recorder, language, the capabilities the trace declares, what was recorded and what was not, focus, the redaction stamp; read it before any other question on a run. |
| `tree` | call-tree slice | Parentage derived from the event stream; `--around` centres the slice on an event id, `--root` on a frame id; nested dict contents are elided, `frame` prints them. |
| `frame` | one activation in full | Arguments, return or raise, and the per-line locals timeline when the run was recorded with `--focus`; frame ids fN come from `exceptions`, `tree` and `grep`. |
| `grep` | search events by name or value | Every CALL, RETURN, RAISE, HANDLED or LINE event whose name or rendered value contains the pattern; `--after` resumes from an event id a previous answer showed. |
| `exceptions` | raises, handles, swallows | Every raise classified swallowed, uncaught, re-raised, propagated or ambiguous, with the reason; SWALLOWED is claimed only when the recording proves it. |
| `flow` | provenance of a value or an object | `--value` follows a literal by equality through captured arguments, locals and returns; `--object` follows one identity from the event that captured it; one of the two is required, and each refuses by name what the recording did not capture. |
| `watch` | predicate over captured state | A gdb-style watchpoint evaluated after the fact at every recorded site of one function; needs a `--focus` recording, and NOTHING WAS CHECKED is a refusal, never a pass. |
| `diff` | first causal divergence between two runs | Aligns the two causal streams and names the first event where they part, with drill-in commands; MATCH or DIVERGED, or REFUSED when no verdict exists. |
| `refocus` | re-run a recorded command with deeper capture, verified | Executes the recorded command again with the added `--focus` and reports whether it was the same execution — MATCH, DIVERGED or REFUSED; the licence names what was compared. |
| `record` (`run`) | record one execution | Runs the command under the recorder from `cwd` and writes one trace; only code under `cwd` is recorded; the command is a .py file, a `-m` module or a console script, never `python` itself. |

`--around`, `--after`, `watch` and `diff --context` are the collisions the
2026-09-02 notation pass named (`-C` is context in grep and a directory in
make; `after` is a cursor in Relay and a context count in grep; `watch`
is a periodic re-run in coreutils and a watchpoint in gdb); each sentence
above pulls the intended prior by naming what the value is.

### 2.3 Fields — derived from the parsers

At boot `schema.derive()` builds a private `argparse` subparsers object,
calls every query module's `add_parser(sub)` on it, and reads each
subparser's actions (**D4**). The rules, closed:

| argparse | JSON Schema |
|---|---|
| `dest` | the field name, as is (`run_a`, `ignore_moves`) |
| `type=int` | `"type": "integer"` |
| `_StoreTrueAction` | `"type": "boolean"` |
| `_AppendAction` | `"type": "array", "items": {"type": "string"}` |
| `choices=(...)` | `"enum": [...]` |
| anything else | `"type": "string"` |
| positional, `nargs=None` | in `required` |
| positional, `nargs="?"` | optional |
| `default` not `None`/`[]`/`False` | `"default": <value>` (informational) |
| `help=` | `"description"` |
| `help=argparse.SUPPRESS` | the field does not exist |
| `help` empty or `None` | **the server refuses to boot**, exit 2, naming command and field |

Three deliberate rules on top:

- **D5 — `run` defaults to `last`.** Wherever a parser has a positional
  named exactly `run`, the field is optional with `"default": "last"`, and
  an absent field becomes the argv word `last`. The model stops echoing
  the same word on every call (designing-notation §1: delete ceremony).
  `diff`'s `run_a`/`run_b` stay required — there is no "last two".
- **D6 — no `oneOf` for `flow`.** `--value | --object` is an argparse
  mutually-exclusive group; both fields are optional strings and the
  description says one is required. Both-or-neither is the CLI's own
  exit 2 with its own sentence; the schema does not duplicate a rule the
  answer already states.
- **D7 — `record` is the one hand-written schema.** `run`'s parser has a
  `REMAINDER` positional and two suppressed flags, so it is not derived.
  Its fields: `command` (array of string, required, at least one element:
  the target argv exactly as the CLI's `-- <command>` takes it), `focus`,
  `include`, `exclude` (arrays), `window` (string), and two the CLI reads
  from its process instead — `cwd` (string; the directory to record from,
  default the server's own) and `python` (string; the interpreter to
  record under, default the server's own; it must import sensorium and
  the target's dependencies, the setup rule the debugging skill already
  states). A test asserts every non-suppressed option of `_add_run_parser`
  appears in this schema, so a flag added to `run` fails the suite until
  `record` carries it.

Seventeen fields have empty help today (`run` on eight commands, `tree
--depth/--limit`, `grep pattern/--kind/--limit`, `exceptions --limit`,
`flow --limit`, `watch --limit`, `diff run_a/run_b`). This slice writes
them; the boot refusal keeps the next slice honest. **D8:** a shared
constant `RUN_HELP` = *run id, a unique prefix of one, or `last` (the
newest trace)* is used on every plain `run`; `exceptions` keeps its longer
sentence (it also accepts an invocation id). `--limit` reads *most rows to
print*; `pattern` reads *substring matched against event names and
rendered values*.

### 2.4 Annotations

Query tools: `readOnlyHint: true`, `destructiveHint: false`,
`idempotentHint: true`, `openWorldHint: false`. `record` and `refocus`:
`readOnlyHint: false`, `destructiveHint: false`, `idempotentHint: false`,
`openWorldHint: true` (they run a program that may do anything). `title`
is the tool name. No icons (**D9**).

### 2.5 From arguments to argv

`schema.to_argv(tool, arguments)` validates then rebuilds (**D10**):

1. Every key must be a field of the tool; an unknown key is rejected as
   JSON-RPC `-32602` with `unknown field 'x' for grep; fields: run,
   pattern, kind, fn, after, limit` — the field and the whole valid set,
   because the diagnostic is where a model repairs (designing-notation §8).
2. Every value must match its type (integer, boolean, array of string,
   string; enum member) — rejected the same way, naming the field and the
   expected type.
3. Required fields present, or rejected naming the missing ones.
4. argv = command word, positionals in parser order (`run` substituted
   `last` when absent), then each option as `--name value`; a true boolean
   as the bare flag; an array repeated once per element; integers as
   decimal strings. `record` maps to `run [--focus …]… [--window …] --
   <command…>` and passes `cwd`/`python` to the child runner, never to
   argv.

Every rejection is an audit line (§6.3): that is the demand census the
next slice reads (designing-notation §3: a surface that rejects).

## 3. Protocol

### 3.1 Versions and lifecycle

Supported: `["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"]`
(**D11**). Claude Code 2.1.258 on this box probes `server/discover` first
and falls back to `initialize`; the official SDK v2 does the same. Both
are answered:

- `server/discover` → `{resultType: "complete", supportedVersions,
  capabilities: {tools: {}}, instructions, ttlMs: 3600000, cacheScope:
  "private"}` (`DiscoverResult` extends `CacheableResult`, whose two
  fields are required; the tool list is fixed for the life of the process
  and belongs to one user's store). The session is then in the
  **per-request** model.
- `initialize {protocolVersion, capabilities, clientInfo}` → if the
  version is in the supported list, echo it; otherwise answer
  `2025-11-25` (**D12**: a client that sent `initialize` is on the legacy
  model, and 2026-07-28 has no `initialize`, so "the latest we support" is
  the latest legacy one). Result: `{protocolVersion, capabilities: {tools:
  {}}, serverInfo: {name: "sensorium", version: <package version>},
  instructions}`. `notifications/initialized` is accepted and ignored. The
  session is then in the **legacy** model at that version.
- Under the per-request model every request carries
  `_meta["io.modelcontextprotocol/protocolVersion"]`; one outside the list
  is `-32022 Unsupported protocol version` with `data: {supported,
  requested}`. **D13:** a `_meta` that carries the version but not
  `clientCapabilities` is tolerated and counted (`meta_incomplete` in the
  audit line), not rejected, although 2026-07-28 says MUST reject — a
  server that turns away real clients on a field it never reads has the
  cost backwards. Falsifier: if H2's official client sends
  `clientCapabilities` on every request, the next slice tightens.
- A request that is neither `ping`, `initialize` nor `server/discover`,
  arriving before either handshake and without a `_meta` version, is
  `-32602 not initialized: send initialize or server/discover first, or
  carry _meta protocolVersion`.

### 3.2 Methods

| method | answer |
|---|---|
| `ping` | `{}` — from the reader thread, never queued (§4.2) |
| `tools/list` | `{tools}`; under the per-request model also `resultType: "complete"`, `ttlMs: 3600000`, `cacheScope: "private"`. No pagination: eleven tools fit one page; a `cursor` is ignored. |
| `tools/call {name, arguments}` | §5, or `-32602 Unknown tool: <name>` (the spec's own example wording) |
| `notifications/cancelled {requestId}` | §4.3 |
| `notifications/initialized`, `notifications/roots/list_changed`, any unknown notification | ignored |
| `logging/setLevel`, `resources/*`, `prompts/*`, `completion/*`, anything else | `-32601 Method not found` — the server declares only `tools` |

Framing (**D14**): one JSON object per line, UTF-8, no embedded newlines;
responses written with `separators=(",", ":")`, `ensure_ascii=False`, a
trailing `\n`, under one lock, flushed per message. A line that is not
JSON is `-32700` with `id: null`; a JSON array is `-32600` (batching left
the protocol in 2025-06-18); an object without `method` is `-32600`. The
server never writes anything but JSON-RPC to stdout; everything
diagnostic goes to stderr, one line each, prefixed `sensorium mcp:`.

### 3.3 `instructions`

Sent in both handshakes; the words the model does not get from its prior
(designing-notation §5), under 800 characters (**D15**):

> sensorium answers debugging questions from a recorded execution trace.
> Start with `runs`, then `info` on the run you mean; `last` is the newest
> trace and the default. Event ids eN and frame ids fN printed by one
> answer are valid arguments to the next. Every result begins with an exit
> line: 0 answered, 1 the trace says no or none, 2 fix the arguments and
> ask again, 3 the trace cannot settle it and only a new recording can.
> Never repeat a 3 on the same run; never re-record on a 2. Two plays: a
> wrong value or a swallowed error is `exceptions`, then `frame` on the
> guilty fN, then `tree` with `around` set to the parent's event id; a
> flaky or environment-dependent test is two recordings and `diff`.
> `record` and `refocus` execute your program and exist only when the
> server was started with `--allow-run`.

## 4. Process model

### 4.1 Every call is a child

`child.run(argv, cwd, python, timeout)` spawns
`[python, "-m", "sensorium", *argv]` with `cwd`, `stdin=DEVNULL`,
`stdout=PIPE`, `stderr=PIPE`, `start_new_session=True`, the server's
environment plus `SENSORIUM_DIR` when `--store` was given (**D16**).
`python` is `sys.executable` for every query and for `record` without a
`python` field. Never a `sensorium` found on PATH: the stale-driver
lesson (ledger rule R3 of the redaction slice) applies to the server's own
interpreter as much as to cargo.

`stdin=DEVNULL` is load-bearing: the server's stdin is the JSON-RPC
stream, and a child that inherited it would eat the client's next
request.

Why a child and not `cli.main` in-process: `sensorium run` executes the
target *in the recording process* under `sys.monitoring`, so an in-process
`record` would import the user's program into the server; a query that
raises would take the server down; `cwd` and `SENSORIUM_DIR` are process
state; and a timeout on an in-process call has no clean kill. The cost is
one interpreter start per call, reported in §9 and never gated.

Timeouts (**D17**): `--timeout` for query tools, default 60 s;
`--run-timeout` for `record` and `refocus`, default 600 s. There is no
per-call timeout field in this slice; falsifier: an audit census showing
`timeout: true` lines is the demand that adds one.

### 4.2 Two threads, one order

The **reader** thread owns stdin: parse each line; answer `ping`
immediately; handle `notifications/cancelled`; put every other request
on a queue. The **worker** thread takes requests in order and answers
them (**D18**). Calls are therefore serialized — a client issuing two
`tools/call`s concurrently gets them one after the other — and a
two-minute `record` never leaves a `ping` unanswered, which is what would
make a client declare the server dead. Concurrency across calls is a
non-goal for a single developer's store; the hosted slice owns it.

### 4.3 Cancel, timeout, exit

- **Cancel.** `notifications/cancelled {requestId}` naming the in-flight
  call: `os.killpg(pgid, SIGTERM)`, two seconds, `SIGKILL`; **no response
  is sent for that id** (the spec: the result will be unused; a response
  after a cancel is ignored). Naming a queued request: it is dropped. Both
  are audit lines with `cancelled: true`. Kill by process group, never by
  name — `pkill -f` self-matches and a killed parent leaves the test
  process running (memory: mutation-harness lesson).
- **Timeout.** The same kill; the response is a result with `isError:
  true`, header `no answer: timed out after N s (server flag --timeout /
  --run-timeout)`, `structuredContent.exit: null` (§5); audit `timeout:
  true`.
- **Spawn failure** (the `python` field names nothing runnable): `isError:
  true`, header `no answer: <OSError text>`, exit `null`.
- **Server exit.** EOF on stdin or SIGTERM: kill the in-flight child's
  group, flush, exit 0. A child's own crash (signal) is an exit line like
  any other: `exit -11:` and the header names the signal.

## 5. The result

```
exit 1: the trace answered negatively -- no match, no frame, no exception, none
<stdout, verbatim>
--- stderr ---
<stderr, only when non-empty>
```

- **D19 — the header** is the first line, always, and its words are the
  exit module's own docstrings, which the debugging skills already teach:
  `exit 0: the trace answered affirmatively` · `exit 1: the trace answered
  negatively -- no match, no frame, no exception, none` · `exit 2: the
  call is wrong -- fix the arguments and ask again` · `exit 3: the trace
  cannot settle it -- change the recording and re-record`. `record`'s exit
  is not the four-way contract: its header reads `exit N: the recorded
  command's own status (2 and no trace when recording was refused)`. A
  child killed by a signal: `exit -S: killed by SIG…`. A call that
  produced no exit: `no answer: <cause>` (§4.3). A model branches on the
  header before it reads prose, exactly as the skill says to branch on
  `$?`.
- **D20 — stderr** follows stdout under a `--- stderr ---` line only when
  both are non-empty; when stdout is empty (an argparse rejection) stderr
  follows the header directly. The label is a line of its own so the
  corpus client can split it back out (§8).
- **D21 — `structuredContent`** is `{"exit": N}` (`null` for no answer),
  declared by `outputSchema` `{"type": "object", "properties": {"exit":
  {"type": ["integer", "null"]}}, "required": ["exit"]}`. Under
  `2025-03-26`, which predates structured content, neither is sent.
- **D22 — `isError`** is true exactly when the exit is **2** or there is no
  exit. 2 is the case the model should repair itself, which is what the
  spec says `isError` is for. 1 and 3 are answers about the trace, not
  errors of the call, and stay `false`.
- Under the per-request model the result also carries `resultType:
  "complete"`.

### 5.1 The output cap

`--max-output BYTES`, default **65536** (**D23**; Claude Code's own cap is
about 25k tokens, and the server's must sit under it so the cut is ours
and named, not the client's and silent). The cap applies to the text
after the header. A text over the cap keeps its **first `cap − 4096`
bytes and its last 4096 bytes**, each cut back to a line boundary, with
one marker line between:

```
[... 1,842 lines (312,006 bytes) omitted; narrow with: depth, limit, around ...]
```

Head and tail, not head alone (**D24**), because `diff` and `refocus`
print their verdict and their drill-in commands last, and a model handed
only the head of a DIVERGED answer has the exit and not the fork. The
narrowing list is the tool's own fields intersected with `{limit, depth,
after, around, context, misses, fn, kind}` in that order; `runs` and
`info` have none and the marker says `narrow with: nothing on this tool`.
A truncated call is `truncated: true` in the audit line.

## 6. Policy and audit

What the redaction spec's §11 reserved for "the MCP policy layer", cut to
what a single developer's deployment needs and no further:

### 6.1 The execution gate

Without `--allow-run`, `record` and `refocus` are absent from
`tools/list` **and** a `tools/call` naming them is `-32602 Unknown tool:
record` — the same answer as any name the server never had (**D25**),
because a distinguishable "exists but disabled" answer invites the model
to look for the switch. `docs/mcp.md` says the flag exists; the wire does
not.

### 6.2 Environment exposure

Checked before design: no query command prints an environment *value*
(`info` prints the hash, the count and the redacted *names*; `refocus`
names a variable that rotated; `watch`'s `env[...]` is the expression's
local environment). Rule v1 already withholds values at the writer. There
is therefore no `--hide-env` knob in this slice (**D26**), and a command
that starts printing values is the change that adds one.

### 6.3 The audit file

`<store root>/mcp.jsonl`, sibling of `invocations.jsonl`, created
`0600`, one JSON line per `tools/call` and per rejection (**D27**):

```
{"utc": "...", "tool": "grep", "arguments": {"run": "last", "pattern": "<redacted>"},
 "exit": 1, "bytes": 4120, "truncated": false, "ms": 84}
{"utc": "...", "tool": "grep", "rejected": {"code": -32602,
 "unknown_fields": ["regex"], "message": "unknown field 'regex' for grep; fields: ..."}}
{"utc": "...", "tool": "record", "arguments": {...}, "exit": null, "timeout": true, "ms": 600012}
```

- **Arguments pass the content rule** (`redact_content.content`) string
  by string before they are written (**D28**): a model that types a
  secret into `grep`'s pattern or `watch`'s expression leaves the marker
  in the audit, not the value. The invocation log the child writes does
  not apply the rule to argv — an asymmetry older than this slice, named
  in CARRIED-DEBT, not changed here.
- Never the environment, never `cwd`, never the result text: `bytes` says
  how much was shown and `truncated` whether all of it; "what was shown"
  in full is the trace itself, which the tenant already holds.
- `SENSORIUM_NO_INVOCATION_LOG` disables this file too (**D29**): the user
  has one word for "log nothing about my calls" and it should keep meaning
  that. The server says so once on stderr at boot.
- Each call also lands in `invocations.jsonl` through the child's own
  `cli.main`, argv and exit, as every CLI call does. No `via` field is
  added there (**D30**): its four-key shape is a contract the E4
  instruments read.

## 7. `sensorium mcp` — the command

Registered in `cli.py` beside `run` and `ts`, **never** in
`_QUERY_MODULES` (**D31**): the tool table is derived from that list, and
the server must not be able to become a tool of itself. Flags: `--allow-
run` (§6.1), `--store DIR` (sets `SENSORIUM_DIR` for the audit path and
every child; default the inherited one), `--max-output BYTES` (§5.1),
`--timeout SECONDS`, `--run-timeout SECONDS` (§4.1). `--allow-run` is
Deno's spelling for exactly this permission. The command's exit: 0 at EOF
or SIGTERM, 2 when the schema derivation refuses (§2.3) or a flag is
malformed.

Registration in Claude Code, the documented line:

    claude mcp add sensorium -- <venv>/bin/sensorium mcp --allow-run

from the project's own venv, for the same reason the debugging skill
gives: `record` runs under the server's interpreter unless `python` says
otherwise.

## 8. The corpus, asked through the server

`corpus/run_corpus.py --via mcp` (**D32**) replaces the one seam every
question already passes through — `_cli(args, cwd, sdir, extra_env)`,
which runs `[sys.executable, "-m", "sensorium", *args]` — with
`corpus/mcp_client.py`:

- One server per case: `sensorium mcp --allow-run --store <sdir>`, cwd the
  case's working directory, the case's `env:` block in its environment;
  torn down at the case's end. Recording stays the harness's own (the
  Python, cargo and vitest paths are unchanged); only the *questions* go
  through the wire.
- Each question's argv is parsed with the same derived parsers into
  `{dest: value}` — positionals plus every option whose value is not its
  default — and sent as `tools/call`. The returned object carries
  `.stdout` = the text with the header line removed and the `--- stderr
  ---` section split off into `.stderr`, and `.returncode` =
  `structuredContent.exit`. `check_question` is untouched.
- A question whose command is not a tool (`redact`, `ts`, `run`) is
  **skipped and named** — `not a tool: N questions` on the summary line,
  never a failure and never silent (the corpus lesson of PR C:
  the runner names skips, a reader must not take 0 failures for "all
  asked"). Task 0 counts them and locks the list.
- The round trip is pinned on its own: for every corpus question,
  `to_argv(tool, parse(argv))` re-parses to a Namespace equal to
  `parse(argv)`.

## 9. E17, pre-registered

Measured **once**, after the branch is complete and reviewed, on this
box, from a plain shell (not inside the session that wrote the code).
Work root `E17_DIR=/mnt/extra/sensorium-rung2/e17`; instrument
`tests/acceptance_e17/e17.py` with cells in `e17_cells.py`, assembled by
`assemble_e17.py` into `docs/superpowers/acceptance/<date>-sensorium-e17-
mcp.md`; rehearsed first under `e17-dry` on a two-case corpus subset so
every artifact path the reading step needs is checked to exist before the
run. Lens on every number: Python version, `sensorium 0.18.0`, the
official `mcp` client's version, Claude Code's version. Both readings
written here before the instrument exists; the point estimate decides; an
infrastructure kill (any cell over 10 min, the part over 45 min) is a
rerun from zero, never a splice.

| H | Claim | PASS | STOP |
|---|---|---|---|
| **H1 parity** | `run_corpus.py --via mcp --require-driver` over all cases. For every question on a **read-only** tool the harness also runs the CLI path and compares: stdout byte-identical, exit identical. `refocus` questions (they execute, and a rerun's text carries a fresh run id) are held to their expectations and exit only. | 0 failures; every read-only question byte-identical and exit-identical; skipped set equals Task 0's locked not-a-tool list exactly | any failure, any difference, any skip outside the list — named per question |
| **H2 conformance** | The official Python SDK client (dev extra `conformance`, pinned major) over stdio: (a) its default connect succeeds (discover, or initialize on fallback); (b) `list_tools` = 9 names without `--allow-run`, 11 with; (c) `call_tool("runs")` returns one text block whose first line matches `^exit [0-3]: ` and `structuredContent.exit` an int; (d) a hand-written minimal client: `initialize` with `2025-03-26` echoed, with `1900-01-01` answered `2025-11-25`, a `_meta` version `1900-01-01` answered `-32022` with the supported list. | all of a–d | any |
| **H3 the cap** | `tree` with `depth 50`, `limit 100000` on the largest trace (by event count, from `runs`) in a `cp -a` copy of `~/.sensorium/traces`. Instrument check first: the same call through the CLI exceeds 65536 bytes, else the cell measured nothing and STOPs as instrument. | text ≤ 65536 + marker; marker names `depth, limit, around`; head and tail both non-empty; audit `truncated: true` | any |
| **H4 the gate** | Without the flag: `tools/list` names exactly the nine; `tools/call record` is `-32602 Unknown tool: record`. With it: eleven; `record` of the `silent_swallow` corpus program from its directory answers `exit 0:`, a trace appears under `--store`, and `exceptions` on it through the wire satisfies that case's expectations. | all | any |
| **H5 liveness** | With the flag, `record` of `probes/sleeper.py` (sleeps 30 s). The client pings every 0.5 s during the call: every ping answered under 1 s (max recorded). Cancel at 5 s: the child's process group gone within 2 s (`os.killpg(pgid, 0)` raises), the next `tools/call` answered. Then `--run-timeout 3` on the same probe: header `no answer: timed out after 3 s…`, `isError: true`, group gone within 5 s of the call. | all | any |
| **H6 secrecy** | The `secret_in_env` case through the wire with its token in the server's environment: the token appears in no result text (the case's `expect_absent`), not in `mcp.jsonl`, not in the server's stderr transcript. **H6b:** a `grep` call whose pattern is `sk-e17-<33 random>` (minted, never committed): the audit line holds `<redacted>`, not the value; the child's stdout may hold it (the CLI echoes the pattern) and that is the CLI's documented behaviour, not this cell's. | 0 occurrences in the three places; H6b marker present, value absent from the audit | any occurrence |
| **H7 the deploy target** | One Claude Code session (`claude mcp add … --allow-run`, cwd a copy of `silent_swallow`), prompt: *record the tests and find the swallowed exception using the sensorium tools only*. Transcript kept. **n = 1, reported not gated**, tier stated (the model Claude Code ran that day). | the session used ≥ 3 sensorium tools and named the swallowing frame the case's `truth` names | reported either way; a STOP names what the model did instead |
| **latency** | 20 × `runs` through the wire vs 20 × `python -m sensorium runs` directly, same store, medians and the ratio. **Never gated.** | — | — |

Pinned ambient variables: `SENSORIUM_DIR` per cell as stated,
`SENSORIUM_NO_INVOCATION_LOG` unset, `PYTEST_ADDOPTS` unset, the venv's
own `python`, no `sensorium` on PATH ahead of it (asserted by the
instrument's preflight, which prints `which -a sensorium`). Every cell
writes its transcript under `$E17_DIR/<cell>/`; `None` for an unmeasured
value and a `dropped` list, never a zero that was not measured.

## 10. Contract, tests, docs, versions, seams

- **Tests** (pytest, each mutation-checked before it counts): schema
  derivation per rule of §2.3 including the boot refusal and D5/D6/D7;
  `to_argv` acceptance and each rejection's wording; the `record` drift
  guard; framing (`-32700`, `-32600` on arrays, unknown method);
  lifecycle in both models including D12/D13 and `-32022`; an
  end-to-end server over a pipe with a minimal in-test client (list,
  call, cap, header, stderr label, `isError`, `structuredContent`,
  legacy-omits-structured); child timeout and kill-by-group (a sleeper
  whose own child must die too); audit lines including the content rule
  and the knob; the corpus round-trip property (§8).
- **Corpus:** no new case; `--via mcp` is the whole corpus asked again.
  `corpus/run_corpus.py --via mcp --require-driver` joins the gate list in
  `docs/corpus.md` and CI. If `run_corpus.py` cannot take the mode within
  the ceiling, the mode lives in `corpus/via_mcp.py` and `run_corpus.py`
  dispatches to it.
- **CI:** the existing matrix installs `.[dev]`; a new job installs
  `.[dev,conformance]` on one Python and runs the H2 client suite. The
  `mcp` package is pinned `>=2.2,<3` in the extra and never imported
  outside `tests/`.
- **Docs:** `docs/mcp.md` (new: what a tool is, the eleven, the header,
  the cap, the gate, the audit, registration, what the server refuses);
  the README at **797** takes the cut *before* the slice writes into it —
  `## Overhead` (91 lines) moves whole to `docs/overhead.md`, wording
  unchanged, the README keeping three lines and a link (the `query.md`
  and `corpus.md` precedent) — then gains `## MCP` (≤ 12 lines) and a row
  in *Use*. `docs/query.md` (798) and `docs/TRACE-FORMAT.md` (797) are not
  touched. `CHANGELOG.md` (684) takes 0.18.0. `docs/CARRIED-DEBT.md` is at
  **795**: PR C's section moves to `CARRIED-DEBT-ARCHIVE-15.md` under a
  dated note at Task 0 so the merge-time section fits.
- **Versions:** Python **0.18.0** (a new command and package). `serverInfo.
  version` reads the installed package's version. Trace format 4,
  `sensorium-rt`, `cargo-sensorium`, `sensorium-ts`: unchanged, no bumps.
- **Files and budgets** (all under `src/sensorium/mcp/`): `jsonrpc.py`
  ≤ 200 (framing, errors, the locked writer) · `schema.py` ≤ 250
  (derive, to_argv, the `record` schema) · `tools.py` ≤ 200 (the table,
  descriptions, annotations, the gate, narrowing sets) · `child.py`
  ≤ 200 (spawn, wait, kill by group, Outcome) · `result.py` ≤ 150
  (header, stderr label, cap, structured) · `audit.py` ≤ 120 ·
  `server.py` ≤ 350 (session state, reader, worker, dispatch,
  instructions) · `cmd.py` ≤ 100. `corpus/mcp_client.py` ≤ 200.
  `tests/acceptance_e17/{e17.py, e17_cells.py, assemble_e17.py,
  probes/sleeper.py}`, `e17.py` ≤ 500 or split before it grows. The
  query modules change only in `add_parser` (help and description
  strings, **D33**: no behaviour change rides in this slice).
- **Skills:** the three `debugging-*-with-sensorium` skills gain a
  *through MCP* paragraph after E17, as local files outside the repo —
  the repo's side is `docs/mcp.md` (**D34**).

## 11. Not in this slice

- **Streamable HTTP, authentication, tenants, upload, name lists, tier
  gating** — the hosted slice. The tool surface, the header, the cap and
  the audit line are designed to be what that slice runs per tenant
  unchanged.
- **Traces as MCP resources, prompts, tool-list-changed notifications,
  progress notifications, streaming output** — none demanded yet; a
  census line that shows the demand is what adds one.
- **A per-call timeout field, an `env` field on `record`** — the second
  is a secret-into-trace vector on purpose left out; the first waits on
  the timeout census (§4.1).
- **`redact` as a tool; `seal`; scanner parity** — as the redaction spec
  left them.
- **Concurrent calls** — serialized by design (§4.2).
- **Windows** — the process-group kill and the file modes are POSIX; the
  server does not refuse to start there, and `docs/mcp.md` says what is
  advisory.
- **Rewriting the debugging skills to prefer MCP over the shell** — a
  ruling after E17's H7, not before it.

## 12. Risks named

- **Protocol drift.** 2026-07-28 moved the lifecycle and added required
  cache fields on list results; the schema may move again before the
  hosted slice. Bound by H2 (the official client) and H7 (the real
  deploy target); the hand-rolled server is ~1,500 lines to keep current
  and the alternative was a ten-package runtime dependency.
- **D13's leniency** is a spec deviation with a falsifier attached.
- **`run` defaulting to `last`** (D5) can hand the model the wrong trace
  after a `record` that was refused (no new trace, `last` is the old
  one). `record`'s header says *no trace* in that case, and `info` names
  its command on the first line; the model has both.
- **The cap's middle cut** can fall inside a multi-line value in `frame`;
  the marker is on its own line and the counts say what is missing.
- **Serialized calls** make a client that fans out tool calls slower,
  not wrong.
- **H7 is n = 1** and says so; it is the deploy-target smoke, not a rate.

## 13. Dated amendments

(none yet)
