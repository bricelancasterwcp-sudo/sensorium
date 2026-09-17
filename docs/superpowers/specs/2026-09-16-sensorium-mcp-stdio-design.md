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

### 2026-09-17 — MCP stdio shipped: the plan's decisions, the controller's rulings, and where the code differs

The slice ran as `docs/superpowers/plans/2026-09-16-sensorium-mcp-stdio.md`
(Tasks 0–12) on `feat/mcp-stdio`. Nothing in §§0–12 above is edited; this
section says what shipped, what was ruled while it shipped, and every place
the code and the sections above disagree. Where they disagree, **the code as
landed is what the docs describe**. D1–D34 are the decisions this one reports
against.

#### (a) The plan's decisions P1–P30, as shipped

| # | as shipped |
|---|---|
| P1 | The tool tables are EXPLICIT — `tools.QUERY_MODULES` (the nine), `EXECUTE_MODULES = (refocus_cmd,)`, `NOT_TOOLS = (redact_cmd,)` — and `test_every_query_module_is_placed` closes them over `cli._QUERY_MODULES`. Shipped as written; field derivation stays automatic, and a new *command* fails the suite until somebody places it. |
| P2 | `action.required is True` puts a field in `required`, and a required `_AppendAction` also gets `"minItems": 1`. Shipped as written (`watch --at`, `watch --expr`, `refocus --focus`), with the fix round adding that an EMPTY required array is a `missing_fields` rejection rather than an argv the CLI would refuse with exit 2. |
| P3 | The header words are `exit.MEANING`, a dict in `exit.py` holding D19's four sentences verbatim. Shipped as written — one source for the header, `INSTRUCTIONS` and the docs. |
| P4 | `--- stderr ---` is emitted whenever stderr is non-empty, stdout empty or not. Shipped as written, amending D20; **R10** fixed the join so the label always starts a line (a stdout without a trailing newline gains one), which is what makes the corpus client's `split_text` lossless. |
| P5 | Under the per-request model both `io.modelcontextprotocol/protocolVersion` and `…/clientCapabilities` are required, and a per-request request is recognised by the PRESENCE of the version key, never by `_meta` being present. Shipped as written, tightening D13; H2 test (h) pins the `-32602` naming the missing key. |
| P6 | Every per-request result carries `resultType: "complete"` and `_meta` serverInfo (the `{}` ping reply included); `server/discover` and `tools/list` also carry `ttlMs: 3600000` and `cacheScope: "private"`. Shipped as written, with **R1** giving each field one owner. |
| P7 | Under `--via mcp` a question whose command word is not a tool is asked through the CLI path and NAMED, never skipped: `CaseResult.via_cli`, the summary's `; N question(s) asked through the CLI (not tools)`, and a JSON `via_cli` key only when non-empty. Shipped as written, amending §8. |
| P8 | The per-case server's environment is `_cli`'s (`{**os.environ, "SENSORIUM_DIR": sdir, "PYTHONDONTWRITEBYTECODE": "1"}`), never the case's `env:` block. Shipped as written, amending §8. |
| P9 | `--store DIR` sets `os.environ["SENSORIUM_DIR"]` to the resolved path in the server process at start; children inherit it and `audit.path()` follows. Shipped as written. |
| P10 | `record`'s header reads `exit N: the recorded command's own status (2 and no trace when recording was refused)`; a signal-killed child reads `exit -S: killed by <name>`. Shipped as written, and H4 read the first string back off the wire. |
| P11 | The kill is `kill_group`: `killpg(SIGTERM)` → poll the GROUP and the leader every 0.05 s for 2.0 s → ALWAYS `killpg(SIGKILL)`, `ProcessLookupError` suppressed at every step. Shipped, **amended by R9**: the trailing `communicate` is the WORKER's, never the canceller's. |
| P12 | No CARRIED-DEBT archive cut at Task 0; Task 11 measures `538 + len(section)` and cuts only if the sum exceeds 800. Shipped as written, and the measurement said cut: 425 + 538 = 963, so PR C's section became `docs/CARRIED-DEBT-ARCHIVE-15.md`. |
| P13 | The README's stale corpus count is corrected in passing. Shipped as written: `115 cases and 253 questions`, re-measured at Task 8. |
| P14 | The E17 instrument is self-contained (`e17_run.py` holds its own `phase`, `_keep`, `_run`, `Refused`), with `PIN = "E17_DIR="`, its own lock test, and `part_word` (**DONE** iff H1–H6 all PASS). Shipped as written; the part word was DONE. |
| P15 | E17's preflight runs children by the venv's absolute interpreter and asserts `<venv>/bin/python -m sensorium mcp --help` exits 0 and the installed version is `0.18.0`; §9's `which -a sensorium` clause is replaced by this. Shipped as written — `which -a` is still PRINTED into the transcript, but nothing is asserted about PATH. |
| P16 | The audit's four rejection shapes (`unknown_tool`, `unknown_fields`, `bad_fields`, `missing_fields`), each with `code`, `reason`, `fields` and `message`. Shipped as written; **R11** also passes `tool`, `fields` and `message` through the content rule. |
| P17 | `tests/test_mcp_conformance.py` skips by name when `mcp` is absent, and CI gains a `conformance` job (Python 3.14, `.[dev,conformance]`). Shipped as written; ten tests, the pinned oracle `mcp` 2.2.0. |
| P18 | `--via mcp --compare-cli` joins CI: the `test` job's 3.14 leg only, plus the `rust` and `typescript` jobs beside their existing corpus step. Shipped as written. |
| P19 | The `mcp` parser's three strings, and the parser added to `test_vocab`'s builder so they are scanned like every other subcommand's. Shipped as written — including the `description=`, whose "every query command is a tool" is false of `redact` and is carried as a defect in CARRIED-DEBT (the README and `docs/mcp.md` were corrected at Task 8; this string was not). |
| P20 | `tools/list` ignores `cursor`; `ping` is `{}` under legacy and before any handshake, and carries `resultType`/`_meta` under a per-request version. Shipped as written. |
| P21 | Request ids are echoed and matched by JSON value with the type preserved. Shipped as written. |
| P22 | Boot answers `server/discover` from a table built before the reader thread starts; the e2e test asserts time-to-first-answer under 2 s. Shipped as written, and E17's latency cell measured spawn-to-discover at **49.5 ms**. |
| P23 | The corpus round trip is pinned at Namespace equality, never at argv equality. Shipped as written. |
| P24 | A `record` or `refocus` killed by cancel or timeout leaves an INCOMPLETE trace under the store, and H5 expects to see it. Shipped as written; H5 read one trace, one incomplete. |
| P25 | `from_argv` sends every positional and every option whose parsed value differs from the parser's default. Shipped as written. |
| P26 | Under `--compare-cli` the CLI path runs a second time only for `executes == False` tools, AFTER the MCP path, comparing `stdout` and `exit`; a `refocus` question is never re-run. The per-case server runs with `--max-output 1048576`. Shipped as written. |
| P27 | `initialize` echoes the offered version iff it is in `LEGACY` (`SUPPORTED[1:]`); anything else — unknown, or `2026-07-28` — is answered `LEGACY_LATEST = 2025-11-25`. Shipped as written, amending D12. |
| P28 | `NARROWING = ("depth", "limit", "after", "around", "context", "misses", "fn", "kind")`, so `tree`'s marker reads `narrow with: depth, limit, around`. Shipped as written, and a cells test derives H3's pre-registered regex from the code so the two cannot drift. |
| P29 | `INSTRUCTIONS` is §3.3's paragraph with its last sentence shortened, under 800 characters, pinned by a test. Shipped as written: **781** characters, byte-identical to §3.3 but for that sentence. |
| P30 | Argument-validation failures are a RESULT with `isError: true` carrying the exit-2 header and the rejection's message, not a protocol error; `Unknown tool: <name>` stays `-32602`. Shipped as written, amending D10's channel; the audit rejection lines (P16) are unchanged. |

#### (b) The controller's rulings R1–R19

Each was ruled during execution and is in the slice's gitignored ledger with
its evidence. The third column is the cost the ruling was taken at.

| R | the ruling | cost if wrong |
|---|---|---|
| R1 | (pre-flight) `result.call_result` and `result.rejection_result` add `resultType: "complete"` when `modern`; the server's `_modern()` adds ONLY the `_meta` serverInfo (and `ttlMs`/`cacheScope` where the method needs them), never a second `resultType`. One field, one owner. | a duplicated key is harmless JSON, so nothing |
| R2 | (pre-flight) `e17_cells.h1` reads `doc.get("via_cli", [])` and `doc.get("mcp_differences")`; a MISSING `mcp_differences` under a `--compare-cli` run is STOP as instrument, a missing `via_cli` is `[]`. | a vacuous H1 — guarded by the census clause |
| R3 | (pre-flight) the lock's one-byte mutation test asserts its needle occurs EXACTLY once in the record before mutating a copy; `"65536"` is not unique, and the needle shipped as `**115 cases / 253 questions**` with a `count == 1` guard. | a mutation test that passes vacuously — the uniqueness assertion prevents it |
| R4 | (Task 1, **REVERSED the same day**) `refocus`'s description was to be transcribed with `--` for its em dash, because every parser string was ASCII. Reversed to VERBATIM (U+2014): the spec is the binding authority and the CLI already prints non-ASCII (`fmt.py:103` `…`, `exceptions_group.py:439` `×`, `exceptions_typescript.py:598` `→`), so the ASCII argument was a preference, not a rule. All eleven descriptions are byte-identical to §2.2. | nothing — one character, no test depends on it |
| R5 | (Task 1) `schema.py` at 335 lines stands against the plan's ≤260: the plan's per-file numbers are budgets under the binding 800-line gate, not gates themselves, and the describe-vs-translate seam is recorded for a later split. It is **360** as shipped, after **R6**. | one split commit later (the ledger's final line on R5, 'STANDS'; the first ruling's cost read "a 335-line module where two ~170-line ones were intended; reversible in one commit") |
| R6 | (Task 2) `schema.py` gains a public `validate(ts, arguments)` extracted from `to_argv`'s three rejection passes (no behaviour change; `to_argv` calls it), so `tools.command_argv` can validate `record`'s arguments — whose `command` is an array positional `to_argv` cannot serialise — without re-implementing P30's rejections. | ~10 lines in `schema.py` |
| R7 | (for Task 5) `src/sensorium/mcp/cmd.py` imports only argparse/os/pathlib at module level and imports `server` and `tools` lazily inside `run(args)`, so `cli.py`'s module-level import of `cmd` cannot cycle through `tools` → `cli`. | an ImportError at CLI start, caught by the first test |
| R8 | (Task 3) `Child.__init__` takes `name: str | None = None` (the tool name for its one log line) and treats `cwd == ""` / `python == ""` as absent. | a log line saying `tool run` instead of `tool record`; a `""` cwd would otherwise make `Popen` raise |
| R9 | (Task 3) **The kill contract is SINGLE-READER.** `kill_group(proc, grace, reap=True)`; `cancel()` calls it with `reap=False` (signal TERM → grace → KILL, never `communicate`), then waits up to `REAP` on a `_done` event the worker sets after ITS `communicate` returns, and only if the worker is still blocked shuts the pipes. `run()`'s exception path reaps the leader. A `cancel()` after `_done` is a no-op. Two readers on one `Popen` is undefined in CPython's design (`subprocess.py:1239, 2116-2121` rebinds `_fileobj2output` for the second entrant); the plan mandated the shape without seeing it. | a cancel whose worker is blocked on an escaped descendant now waits REAP before the pipes are closed — the same bound as before |
| R10 | (Task 4) `text_of` joins header + stdout, then — only when stderr is non-empty — a newline if the text does not already end in one, then the label and stderr. A stdout without a trailing newline therefore gains one before the label; it is the only case `split_text` cannot recover exactly, and it does not occur in the corpus. | one byte of parity on a case that does not exist |
| R11 | (Task 4) The signal name is looked up under a guard (`signal.Signals(n).name`, `except ValueError` → `signal {n}`), so a real-time signal renders rather than raising inside the renderer; riders: `keep_tail = max(1, min(KEEP_TAIL, limit // 4))`, the two cap docstrings say a newline-free window is a raw byte cut that may end in U+FFFD, and `record_rejection` scrubs `tool`, `fields` and `message` too. | none observable at the enforced 4096-byte floor |
| R12 | (Task 5 split) Task 5 runs as 5a (`jsonrpc.py`, `corpus/mcp_client.py`) and 5b (`server.py`, `cmd.py`, `cli.py`, the e2e and cmd tests), each with its own review. | one extra review seat |
| R13 | (Task 5a) Id-less and null-id server objects go to `McpClient.unaddressed` and are never dropped; `wait(None, timeout)` pops the oldest; a blank stdout line is recorded in `bad_lines` like any other non-object line; ids are minted under the Condition; the drainer falls back to memory; a fresh `McpError` per raise. The client may grow to ≤ 320 lines (**329** as shipped, after R18). | 20 lines |
| R14 | (Task 5b) `server.py` at 490 lines is PARKED under R5's precedent; the named `lifecycle.py` split (the constants, `Session`, the era check, both handshake results) is for the final review to triage. It is **488** as shipped. | one split commit later |
| R15 | (Task 8) The README's `## MCP` section goes at the end of `## Use`; the Overhead headline keeps 194× and says it is the call-dense workload under `--focus`; "MCP wrapper" leaves the README's `## Not yet` list. | prose |
| R16 | (Task 9) The E17 pin table writes `E17_CARGO_BIN` / `E17_NODE_BIN` with `$HOME` as `~`, so only `E17_DIR=` lines carry a box path and the lock's rule holds while the pins stay informative. | a pin a reader expands by hand |
| R17 | (Task 10, H7) H7's `serve.sh` serves a FRESH store (`--store $E17_DIR/h7/store`), so the deploy-target session never writes the live store; the session is print mode (`claude -p … --output-format stream-json --verbose --allowedTools "mcp__sensorium__*" --model opus`) and the model is recorded in `h7.json`, as the locked row requires. Recorded as an amendment beside §1. | none to the reading; the row records the store and the model |
| R18 | (design, controller) **`structuredContent` and `outputSchema` LEAVE THE WIRE.** A `tools/call` result is text only; the header line is the exit's machine-readable carrier (`^exit (-?\d+): ` / `^no answer: `); `isError` stays (exit 2 or no exit). `OUTPUT_SCHEMA` is gone, `title` is still gated on 2025-06-18+, and `corpus/mcp_client.CallResult.exit` is parsed from the header. D21 is amended by this row; the LOCKED §1 of the record is not edited — a dated amendment beside it carries the consequences for H2(c) and H5. Why: the deploy target renders structured content INSTEAD of the text for every non-error result, so a structured twin that is not a complete representation hides the product. | a client that wanted the exit as JSON parses one line instead |
| R19 | (Task 9) `e17_cells.py` at 502 lines is PARKED under R5/R14's precedent; the split (one module per cell family) is for the final review to triage. It is **530** as shipped, after the fix round. | one split commit |

#### (c) Where the shipped code differs from §§2–10

Nineteen: seventeen at the merge-ready head, and 18-19 appended by the fix
wave that followed the final whole-branch review. Each is a place a reader of
the sections above would be told something the code does not do.

1. **The tool tables are explicit, not derived from `_QUERY_MODULES`**
   (**P1**, amending **D4**'s companion **D31**). That list has eleven
   entries and one of them is `redact_cmd`, which rewrites the store:
   derivation would have made `redact` a tool. Field derivation is still
   automatic; the three tuples are hand-written and a closure test holds
   them to the list. Where: `tools.py`, `tests/test_mcp_tools.py`.
2. **A required OPTION is in `required`** (**P2**). §2.3's table put only
   positionals there, so a model omitting `watch --at`, `watch --expr` or
   `refocus --focus` would have met argparse's exit 2 for a field the schema
   called optional. A required array also carries `"minItems": 1`, and an
   empty one is a `missing_fields` rejection. Where: `schema.derive`,
   `schema.validate`.
3. **The header's words come from `exit.MEANING`, not from the exit module's
   docstrings** (**P3**, amending **D19**'s source). Only exit 1's docstring
   matched the sentence D19 quoted. One dict now holds the four, and the
   header, `INSTRUCTIONS` and `docs/mcp.md` read from it. Where: `exit.py`.
4. **The stderr label is emitted whenever stderr is non-empty** (**P4**,
   amending **D20**'s "only when both are non-empty"). Two corpus refusals
   print only to stderr, and the corpus client must attribute a body to a
   stream. **R10** adds that the label always starts a line. Where:
   `result.text_of`.
5. **D13's leniency is gone before it shipped** (**P5**). Its falsifier —
   *if H2's official client sends `clientCapabilities` on every request, the
   next slice tightens* — was answered by reading the SDK at design time, so
   a per-request request missing either key is `-32602` naming it, and the
   session model is decided by the PRESENCE of the version key (a legacy
   request may carry `"_meta": {}`). Where: `server.version`,
   `tests/test_mcp_conformance.py` (h).
6. **`structuredContent` and `outputSchema` are not on the wire** (**R18**,
   amending **D21**). D21 declared `{"exit": N}` under an `outputSchema`; the
   deploy target passes the model only the structured content when one is
   present and drops the text for every non-error result, so the product's
   own answer never reached the model. Both keys are gone, the header is the
   machine-readable carrier, `isError` is unchanged, and our own client
   parses the exit off the header's second token where it used to read a
   JSON field — while the SDK's client and Claude Code's now get the text
   the header begins, which is the point. Where: `result.call_result`,
   `result.rejection_result`, `tools.to_wire`,
   `corpus/mcp_client.CallResult`.
7. **Claude Code opens the LEGACY handshake** (measured), correcting §3.1's
   sentence *Claude Code 2.1.258 on this box probes `server/discover` first
   and falls back to `initialize`*. Both H7 runs recorded
   `handshake initialize 2025-11-25 -> 2025-11-25` on the server's own stderr
   line. The official SDK v2 does probe discover first (H2 (a) connects at
   `2026-07-28`), so the sentence is right about the SDK and wrong about the
   client it names. Both lifecycles were built, which is why the correction
   costs nothing.
8. **`initialize` echoes only a LEGACY version** (**P27**, amending
   **D12**). D12 keyed the echo on the whole supported list, which includes
   `2026-07-28` — a version with no `initialize` — and the SDK refuses an
   `initialize` result outside its own handshake list. Where:
   `server.LEGACY`, `server.LEGACY_LATEST`.
9. **The narrowing list is ordered `depth, limit, after, around, …`**
   (**P28**). §5.1's rule sentence listed `{limit, depth, …}` while its
   example marker and §9's H3 row both read `depth, limit, around`; the
   example and the locked row win, and a cells test derives the
   pre-registered regex from `tools.narrowing_fields` so the two cannot
   drift. Where: `tools.NARROWING`.
10. **`INSTRUCTIONS` is 781 characters, one sentence shorter than §3.3**
    (**P29**). §3.3's paragraph is 808 characters against **D15**'s "under
    800", and no test had measured it; the last sentence became
    `` `record` and `refocus` execute your program and exist only under
    `--allow-run`. `` Everything else is byte-identical. Where:
    `server.INSTRUCTIONS`, pinned by `test_instructions`.
11. **An argument rejection is a RESULT, not a protocol error** (**P30**,
    amending **D10**'s channel). §2.5 routes every rejection through
    JSON-RPC `-32602`; both MCP revisions reserve that code for unknown
    tools and malformed requests and route input validation through
    `isError`, which is the channel a model sees and repairs from — D10's
    own reason for naming the fields. `Unknown tool: <name>` stays `-32602`
    (the spec's example, and D25 and H4 depend on it). The audit lines are
    unchanged. Where: `server._call`, `result.rejection_result`.
12. **The cancel signals and never reads** (**R9**, amending §4.3's
    sequence). §4.3 ends the kill with `proc.communicate(timeout=2.0)`,
    which the cancelling thread would enter while the worker was already
    inside its own. Shipped, the worker owns every byte and `cancel()` waits
    on its event. A cancelled call's `Outcome` holds what the worker
    collected. Where: `child.kill_group`, `child.Child.cancel`.
13. **The corpus routes a not-a-tool question through the CLI instead of
    skipping it** (**P7**, amending §8). §8 said such a question is *skipped
    and named*; `redact_retrofit`'s two tool questions are only true AFTER
    its three `redact` questions have rewritten the store, so skipping the
    three strands the two. They are asked through the CLI path and named on
    the summary and in `via_cli`. **P8** adds that the per-case server's
    environment is `_cli`'s and never the case's `env:` block — `info`
    prints `redaction: OFF (SENSORIUM_NO_REDACT)` from the live environment,
    so carrying the case's block into the server would have made MCP and CLI
    differ on that very case. Where: `corpus/via_mcp.py`,
    `corpus/run_corpus.py`.
14. **E17's preflight asserts the interpreter, not the PATH** (**P15**,
    replacing §9's `which -a sensorium` clause). `~/.local/bin/sensorium` is
    on this box's PATH six times; PATH emptiness was the wrong invariant, so
    the preflight asserts `<venv>/bin/python -m sensorium mcp --help` exits 0
    and that the version under that interpreter is `0.18.0`. `which -a` is
    still printed into the transcript. Four more of §9's readings were made
    exact by the plan's pre-registration block, which Task 0 appended to the
    record's §1 and locked there: **H3**'s bound is measured on the text
    AFTER the header with the marker line removed (neither is counted against
    65536); **H5**'s numbers are pinned (≥ 8 pings before the cancel, every
    ping under 1.0 s, the group gone within 2.0 s of the cancel, the timeout
    answered within 6 s and its group gone within 5 s of the send); **H6**'s
    method mints its own `sk-e17-…` token, verifies it in the server's own
    `/proc/<pid>/environ` before any question, and counts occurrences in the
    texts, `mcp.jsonl` and the stderr transcript; **H7**'s prompt is
    `probes/h7-prompt.txt`. What came LATER — after the block was locked and
    before any cell ran — is a dated amendment written BESIDE §1 rather than
    into it: **R16**'s `~` in the pin table, **R17**'s fresh H7 store and
    print mode, **R18**'s consequences for H2 (c) and H5, T_cli = 63 s
    setting H1's timer at its 600 s floor, and the per-cell fresh stores.
15. **§10's CARRIED-DEBT arithmetic was wrong, and the cut became a
    measurement** (**P12**). §10 said the file was at **795** and scheduled
    an archive cut at Task 0; it was **538** — 795 was PR A's number. The
    plan replaced the scheduled cut with the rule the file already carries:
    draft the section, measure, cut only if the sum exceeds 800. It did
    (425 + 538 = 963), so PR C's section moved to
    `docs/CARRIED-DEBT-ARCHIVE-15.md` at Task 11 rather than at Task 0. §10's
    README number held (**797**, and the `## Overhead` cut took it to 727
    before the slice wrote a word into it); its `CHANGELOG.md` number was 684
    against an actual **687**.
16. **Seven of §10's nine file budgets are exceeded**, three of them by
    enough to be ruled on and parked (**R5**, **R14**, **R19**) and four by
    small margins: `schema.py` **360** (§10 ≤250, the plan ≤260),
    `server.py` **488** (≤350 / ≤400), `corpus/mcp_client.py` **329**
    (≤200 / ≤300), `child.py` **240** (≤200 / ≤220), `tools.py` **220**
    (≤200 / ≤220), `result.py` **184** (≤150 / ≤180), `audit.py` **135**
    (≤120 / ≤130); `jsonrpc.py` **139** (≤200) and `cmd.py` **100** (≤100)
    are the two that held. Outside §10's list, `tests/acceptance_e17/
    e17_cells.py` is **530** against the plan's ≤300 (**R19**) and
    `docs/mcp.md` **330** against a ≤320 that Task 8's fix round raised to
    330 to fit the corrections its review demanded. The binding limit is the 800-line
    ceiling, which every one of them meets with room to spare; each parked
    ruling names the seam to split at, and none of the small margins buys a
    split on its own.
17. **`record`'s `cwd` and `python` ARE audited, and `refocus` takes no
    interpreter.** §2.5 says the two fields are passed to the child runner
    "never to argv", which is true, and §6.3 says the audit records
    "never … `cwd`" — meaning the SERVER's working directory. A `cwd` a model
    TYPED is an argument like any other and is written (through the content
    rule) as one. `refocus` re-runs under the server's own interpreter with
    no `python` override. Where: `tools.command_argv`, `audit.record_call`,
    `docs/mcp.md`, the 0.18.0 CHANGELOG entry.
18. **D28's "leaves the marker" is narrower than it reads** (**M7**, the
    final review's minor; the wording is narrowed, the behaviour is not).
    §6.3's first bullet says a model that types a secret into `grep`'s
    pattern "leaves the marker in the audit, not the value". That is true of
    a string the CONTENT rule MATCHES and of no other:
    `redact_content.content("hunter2")` returns it unchanged, and it is
    written to `mcp.jsonl` verbatim. The rule is nineteen shapes, each with a
    minimum length — a floor, not a secret scanner — so the clause before it
    ("arguments pass the content rule") is exact and the "so" clause
    over-reads it. `docs/mcp.md` now says what the rule actually does (which
    spans are replaced by `<redacted>`, and that a value in no published
    shape is written as typed) and that the CLI's own stdout may echo an
    argument back in any case. The audit is the census a hosted tier's policy
    argument will rest on, and an over-read claim there would be quoted
    later. Where: `docs/mcp.md`'s audit section, `docs/CARRIED-DEBT.md`'s
    settled entry.
19. **The wire is `ensure_ascii=True`** (**C2**, the same wave, amending
    §3.2's framing line, which says `ensure_ascii=False`). A method name, a
    tool name and a rejected field name are echoed back to the client as
    model-typed text, and a model does emit lone surrogates (a tokenizer
    splitting an emoji). Such a string cannot be encoded onto a UTF-8 stdout
    at all: the write raised `UnicodeEncodeError` — a `ValueError` — the
    writer's `except` swallowed it as a gone pipe, and the response vanished
    with nothing logged on any channel. Escaped, it is `\ud800` on the wire
    and `json.loads` hands the client back the same string. The same wave
    narrows that `except` to `BrokenPipeError` plus a ValueError off a stream
    that is actually CLOSED, which is what §3.2's "one lock, flushed per
    message" line always meant. Where: `jsonrpc.Writer._write`.

#### (d) E17's outcome

Measured **once**, 2026-09-17, **251.2 s** wall clock, under `e17.sh` from a
plain shell after a full rehearsal on a two-case subset: **DONE** — H1 parity
**PASS**, H2 conformance **PASS**, H3 the cap **PASS**, H4 the gate **PASS**,
H5 liveness **PASS**, H6 secrecy **PASS**, H7 the deploy target **reported**
(n = 1), latency **measured**. The reading is
`docs/superpowers/acceptance/2026-09-16-sensorium-e17-mcp.md` §2, with a
clause table per cell, the pins, the versions, the phase timings and an
erratum.

| cell | what was read |
|---|---|
| H1 | 115 cases / 253 questions against the locked census; 0 failures, 0 harness errors, no `exit_reason`, 0 skipped; **0 MCP/CLI differences** over every read-only question; `via_cli` exactly the locked three |
| H2 | pytest exited 0; **10 passed, 0 skipped** against §1's floor of 9, against the official SDK 2.2.0 |
| H3 | **65,135** bytes after the header with the marker removed, against the 65,536 bound; the same call through the CLI wrote **28,514,015**; one marker line matching the locked regex and naming `depth, limit, around`; a 306-line head and a 32-line tail; the audit line `truncated: true` |
| H4 | 9 tools without the flag and `-32602 Unknown tool: record`; 11 with it; `record` answered `exit 0: the recorded command's own status …`, `runs` listed the one trace, `exceptions` satisfied that case's `what-was-dropped` |
| H5 | 10 pings, the slowest answered in **0.8 ms**; the cancelled child's group gone **0.10 s** after the cancel with no response for that id; the next `runs` listed 1 trace, 1 INCOMPLETE; the timeout header exact, `isError` true, the exit `None`, answered 3.05 s and the group gone 3.06 s after the send |
| H6 | **0** occurrences of the minted token in the 4 result texts, in `mcp.jsonl` (4 lines) and in the 430-byte stderr transcript; H6b's audit line reads `<redacted>` |
| H7 | Claude Code **2.1.258**, model `claude-opus-5`, print mode, a fresh store: `record` passed `['main.py']`, **5** sensorium calls over `record`, `info`, `exceptions`, `tree` and `frame`, and the frame it named — **`load_all`** — IS the case's `truth`. Handshake: `initialize 2025-11-25 -> 2025-11-25` |
| latency | median `runs` through the wire **3704.9 ms** against **3709.1 ms** through the CLI, a ratio of **1.00×**; spawn to the `server/discover` answer **49.5 ms** |

**Erratum, same day, in the record.** The H7 row's rendered sentence says
*7 sensorium tool(s) used* and then lists `Skill` and `ToolSearch` among them:
the cell counted every distinct tool NAME in `h7.json`'s `tools_used`,
including Claude Code's own. The sensorium tools were **5**, which
`h7.json`'s `sensorium_tool_calls` field also says, and the locked "≥ 3"
holds either way. The measured values are untouched; the counting is a
rendering defect in `e17_cells.h7`, carried to the next slice in
CARRIED-DEBT.

#### (e) The finding this slice exists to have made

The design got the protocol right and the client wrong, and only the deploy
target could tell the difference.

`structuredContent: {"exit": N}` under an `outputSchema` (**D21**) is
spec-blessed, small, correct, and was green under every unit test, under the
official SDK's ten conformance tests, and over all 253 corpus questions with
zero MCP/CLI differences. Then H7 ran the real client. Claude Code 2.1.258
renders a result's structured content INSTEAD of its text whenever one is
present and the result is not an error: for every non-error call the model
received the eight bytes `{"exit":0}` and nothing else. It still found the
swallowed exception — by probing exit codes across **40** sensorium calls —
and said so itself: *assembled from binary answers — I never saw sensorium's
own SWALLOWED verdict line.* The product's entire output, the honest verdict
this tool exists to print, was invisible to the model it was written for.

**R18** took both keys off the wire and made the header the machine-readable
carrier. The same task, re-measured on the fixed server: **5** calls, the
frame named from the text.

The rule the next slice inherits: *a structured rendering that is not a
COMPLETE representation of the answer is not a convenience, it is a second
surface a client may prefer — and a conformance oracle proves you speak the
protocol, never that the client shows the user what you said.* The smoke test
that runs the real deploy target is what found it; run that test before the
docs are written, not after.
