# The sensorium trace format

This is the contract a second recorder is written against. Everything below
is a statement about the code in this repository at the time of writing —
`src/sensorium/store/db.py` (schema, required meta, the open-time refusal),
`src/sensorium/store/reader.py` (how every value is read back),
`src/sensorium/record/boot.py` (what the Python recorder writes),
`src/sensorium/record/tracer.py` (what an event means) and
`src/sensorium/query/` (how each fact is rendered). Where a rule exists so a
reader can never print an absent record as a zero, the document says so:
that is the whole point of format 4.

The rules with teeth are the ones in `docs/trace-format/vectors/`. A vector
is a JSON description of a trace plus the questions the CLI must answer
about it; both recorders' test suites build the same vectors and run them
through the real command line (§8).

---

## 1. Purpose and versioning

`meta["trace_format"]` is stamped at creation. The current value is
`db.TRACE_FORMAT = 4`.

| Format | What it added |
|---|---|
| (absent) | A trace with no `trace_format` key at all predates the key and is read as format 1. |
| 1 | The original schema. Frame parentage was "the last frame opened on the thread" — a guess; `Trace.parentage_basis()` reports it as `"assumed"` and every view carries the caveat. |
| 2 | Async attribution: `events.task_id`, the `tasks` table, and the CALL-payload keys. Parentage becomes `"derived"`. |
| 3 | Inspectable coroutines: `frames.kind`, the `YIELD`/`RESUME` event kinds, and `task_fingerprints`. |
| 4 | The trace-format contract (this document). **No column changes.** It makes `recorder`, `lang` and `capabilities` required meta, and requires the finalize keys of §4 on any trace that says `incomplete = false`, so a second recorder can never have an absent record rendered as a zero. |
| 5 | **Model traces** (`lang: "model"`, recorder `sensorium-model`, S1 of the sensor-suite program): adds the `tokens` and `spans` tables, admits `fingerprint_basis: "per-generation"` and `exit_status_basis: "not-a-process-exit"`. Program recorders keep writing 4. Contract: [`trace-format/MODEL-TRACES.md`](trace-format/MODEL-TRACES.md). This sensorium (0.8.1) refuses a format-5 file by the newer-format rule below — the intended behavior until the S1 reader ships. |

Two refusals live in `db.open_trace`, and both raise `TraceFormatError`
(which `cli.main` turns into `error: …` on stderr and exit status 2):

- **A newer format is refused, never read.** `trace_format > 4` →
  `"… is trace format N, newer than this sensorium reads (up to 4); upgrade
  sensorium to open it"`. A reader must not guess at a layout it was not
  written for.
- **A finalized format-4 trace missing a required key is refused** (§4).

Readers are otherwise backward compatible: `Trace` decides what columns
exist by asking the tables (`PRAGMA table_info`), not by trusting the meta
key, so a format-1 file opens and answers what it can.

## 2. Storage

One SQLite file per run:

```
$SENSORIUM_DIR/traces/<run-id>.db        # default $SENSORIUM_DIR = ~/.sensorium
```

- **Run id shape**: `YYYYMMDD-HHMMSS-xxxxxx` — local-time stamp plus six hex
  characters (`paths.new_run_id`). A run id supplied from outside must be a
  single path component: not `""`, `"."` or `".."`, and equal to its own
  basename (`paths.is_valid_run_id`), because it is joined straight onto the
  traces directory. `paths.find_trace` resolves a reference by unique
  filename-stem prefix, plus the literal `last` (newest mtime).
- **Journal mode**: the writer sets `PRAGMA journal_mode=WAL` at creation
  (`db.create_trace`); the read path opens the file with no pragma at all.
  A trace is closed before it is queried in the ordinary flow. The Rust
  converter (`rust/cargo-sensorium/src/convert/sqlite.rs`) also sets
  `PRAGMA synchronous=NORMAL` and commits the WHOLE trace -- schema, every
  row, every meta key -- as ONE transaction, `COMMIT` immediately before the
  `.tmp` file is renamed into place. Committing per row (this converter's
  original shape) measured 1118.9s for one 119-process, 134,394-event
  invocation against the Python converter's 22.7s for the same invocation,
  ~49x slower, entirely attributable to one fsync'd transaction per `INSERT`;
  one transaction per trace measured 0.903s for that same invocation
  afterwards (n=1, read live at fix time). `synchronous=NORMAL` under WAL
  cannot corrupt the file on a crash (that guarantee is unconditional under
  WAL; `FULL`'s extra fsync only protects against losing the last few
  committed transactions on power loss) -- and a reader can never observe an
  earlier "committed" state of this file at all, because the tmp+rename means
  a trace's final name exists only after `COMMIT` has already returned.
  **Amended 2026-09-03 (drift closed): the acceptance document's own
  addendum re-measured the same spool, same command, formally (n=3) and reads
  1.197s** -- the 0.903s figure above is left as it was recorded (a single
  ad-hoc reading taken at fix time, same box, same spool) rather than
  silently replaced; the addendum's number is the one to quote
  (`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md`
  §3.1). Both are the same ~1000x order of improvement over the 1118.9s
  per-row baseline; neither reading is gated.
- **Permissions**: the file is created with the process umask — `0644` on a
  default Linux setup, readable by every account on the machine. A trace
  holds the entire process environment, everything the program wrote to
  stdout/stderr, the command line, the working directory, and captured
  values. Treat one the way you would treat a core dump or a `.env`; see
  the README's "What a trace file holds". There is no redaction pass.

## 3. Tables

The schema, verbatim from `db.SCHEMA`:

```sql
CREATE TABLE meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE code_objects (
  id INTEGER PRIMARY KEY,
  file TEXT NOT NULL,
  qualname TEXT NOT NULL,
  firstlineno INTEGER NOT NULL
);
CREATE TABLE frames (
  id INTEGER PRIMARY KEY,
  parent_id INTEGER,
  code_id INTEGER NOT NULL,
  call_event_id INTEGER NOT NULL,
  return_event_id INTEGER,
  depth INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  closed_by TEXT,
  unwind_exc TEXT,
  kind TEXT
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY,
  ts_ns INTEGER NOT NULL,
  thread_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  frame_id INTEGER,
  code_id INTEGER,
  line INTEGER,
  payload TEXT,
  task_id INTEGER
);
CREATE TABLE output (
  id INTEGER PRIMARY KEY,
  after_event_id INTEGER NOT NULL,
  stream TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE tasks (
  id INTEGER PRIMARY KEY,
  name TEXT,
  thread_id INTEGER NOT NULL
);
CREATE TABLE fingerprints (
  thread_id INTEGER PRIMARY KEY,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
CREATE TABLE task_fingerprints (
  task_id INTEGER PRIMARY KEY,
  name TEXT,
  hash TEXT NOT NULL,
  n_events INTEGER NOT NULL
);
CREATE INDEX idx_events_code ON events(code_id);
CREATE INDEX idx_events_frame ON events(frame_id);
CREATE INDEX idx_events_kind ON events(kind);
CREATE INDEX idx_frames_code ON frames(code_id);
```

The indexes are an access path, not evidence: a converter may create them at
the end of its write, and no query's correctness depends on one.

### meta

`key` → `value`, where **`value` is always JSON** (`db.set_meta` writes
`json.dumps`, `db.get_meta` reads `json.loads`). A string value is therefore
stored quoted; a bare word is not readable. See §4.

### code_objects

| Column | Meaning |
|---|---|
| `file` | The file the code was defined in, as the runtime reports it — absolute in the Python recorder (`code.co_filename`). Module identity lives here: two same-named functions in different files are two code objects. |
| `qualname` | The file-local path to the definition: `Class.method`, `outer.<locals>.inner`. Not module-qualified. |
| `firstlineno` | Line the definition starts on. |

Interning is the writer's job; ids need only be unique and stable within the
trace. Note that `file` here is **not** the string the fingerprint hashes
(§7).

### frames

One row per activation of a traced body.

| Column | Meaning and NULL semantics |
|---|---|
| `parent_id` | The **calling frame**. NULL = root (nothing traced was on the stack, or the caller had no open frame — the CALL payload's `caller_code` names it when it was traced). |
| `code_id` | → `code_objects.id`. Never NULL. |
| `call_event_id` | The `CALL` event that opened this frame. Never NULL, and `frames.call_event_id` is what decides "framed": a CALL whose id appears in no frame row is an *unframed* call (`Trace.unframed_calls`). |
| `return_event_id` | The `RETURN` event that closed it; NULL when the frame did not return (unwound, suspended, or still open). |
| `depth` | 0 for a root, parent + 1 otherwise. |
| `thread_id` | The thread **serial** (§6), not an OS id. |
| `closed_by` | `"return"`, `"unwind"`, or NULL = the frame was never closed (still open at end of recording, or suspended). **No third value.** A recorder that writes e.g. `"panic"` here gets it read as "not closed", which renders as a false ` (open)`. |
| `unwind_exc` | JSON object, the exception that unwound the frame; NULL otherwise. Shape in §5. |
| `kind` | `"function"`, `"generator"`, `"coroutine"`, `"async_generator"`. **Never NULL from format 3 on** — a NULL renders as the marker `[None]` on every line that shows the frame. `"function"` is the ordinary case and prints no marker at all (`tree_cmd.frame_line`). Columns absent on formats ≤ 2 default to `"function"` in the reader. |

How a frame *ended* is **derived** from that evidence plus the frame's last
`YIELD`/`RESUME` row (`reader.Trace.frame_state`), never stored: `returned`,
`raised`, `cancelled`, `abandoned`, `thrown`, `suspended`, `open`. A
recorder writes evidence; the reader names the state.

### events

| Column | Meaning and NULL semantics |
|---|---|
| `id` | Causal order (§6). 1-based, dense, assigned in write order. |
| `ts_ns` | Monotonic nanoseconds (`time.monotonic_ns()` in the Python recorder). For display and duration only — never compared, never hashed. |
| `thread_id` | Thread serial (§6). |
| `kind` | One of the seven kinds in §5. |
| `frame_id` | The frame this event ran INSIDE. **NULL on every CALL**, including the ones that open a frame: the frame does not exist yet when the CALL row is written (`tracer._on_start` passes `None`), and the link runs the other way, through `frames.call_event_id`. NULL too for any other event a recorder emits outside a frame. `RETURN`, `RAISE`, `HANDLED`, `LINE`, `YIELD` and `RESUME` carry the open frame's id. |
| `code_id` | The code object the event is about. NULL is allowed **only on a non-causal event**: `grep` skips a NULL-code row, but `causal_stream` / `task_stream` look the code up unconditionally, so a `CALL`/`RETURN`/`RAISE`/`HANDLED` row must carry one. |
| `line` | Source line. For `CALL` the definition line; for `LINE`/`RAISE`/`HANDLED`/`YIELD`/`RESUME` the line the event happened at; NULL on `RETURN` (no renderer reads it there). |
| `payload` | JSON object or NULL. Keys per kind in §5. |
| `task_id` | → `tasks.id`; NULL = the event ran in no unit of work. In the Python recorder NULL is **wider** than "no loop ran": loop callbacks run with no current task, and a task-identity lookup that raised also lands here (counted in `meta["task_errors"]`). |

### output

The program's own stdout/stderr, interleaved with the events by
`after_event_id` — the id of the last event written when the chunk was
produced (0 when nothing had been written yet). `stream` is `"stdout"` or
`"stderr"`; `data` is the text. A recorder that cannot capture output
declares `capabilities.output = false` and writes no rows (§4).

### tasks

One row per unit of work: an asyncio task in Python; a libtest test or a
spawned unit in Rust. `name` NULL means **the name could not be read**,
not that the unit had no name — `tree` and `info` say exactly that. Task ids
are per trace.

### fingerprints, task_fingerprints

`fingerprints`: one row per thread that ran traced code. The count is **0**
when every causal event on that thread ran inside a unit of work — a fact
with content ("this thread ran traced code, all of it inside tasks"), and
not the same fact as having no row, which every reader takes to mean the
thread ran no traced code at all. Readers must therefore keep a zero-count
row, including one for the main thread.

`task_fingerprints`: one row per minted unit of work, whatever state it was
left in, zero-count included. `name` is a copy of the `tasks` row's name, so
the multiset comparison reads `(name, hash)` from one table.

**Format 5 adds two tables**, `tokens` and `spans`, and reuses `tasks`/`task_fingerprints` for
generations; their DDL and NULL rules are in [MODEL-TRACES §3](trace-format/MODEL-TRACES.md#3-tables).

## 4. Meta

### The required set

`db.REQUIRED_META`, in the order missing keys are reported:

```
run_id, argv, cwd, env_hash, start_ts, end_ts, exit_status,
main_thread_ident, fingerprint_basis, truncated_count, source_hashes,
recorder, lang, capabilities
```

| Key | One line |
|---|---|
| `run_id` | The run's own id; matches the filename stem in the ordinary flow. |
| `argv` | The recorded command, as a list of strings. |
| `cwd` | Working directory at record time. |
| `env_hash` | A short digest of the environment, so two runs can be compared without printing it. **Per-recorder**: the Python recorder hashes `json.dumps(env, sort_keys=True)`, the Rust one sorted `k=v` lines. Two traces' digests are comparable only within one language — equal digests across recorders mean nothing, and unequal ones mean nothing either. |
| `start_ts`, `end_ts` | Wall-clock seconds (`time.time()`); `info` prints the difference as the duration. |
| `exit_status` | The status the recorded program ended with, or **null** when nobody witnessed it — read with `exit_status_basis` below, never alone. |
| `main_thread_ident` | The **serial** of the thread the target was invoked from, recorded at boot rather than inferred (§6). |
| `fingerprint_basis` | `"per-task"` or `"per-thread"` — what a per-thread fingerprint row covers (§7). Explicit, never defaulted by a writer. |
| `truncated_count` | How many captured values were clipped by the capture caps. |
| `source_hashes` | `{file: content-digest}` for every file the run traced code from. |
| `recorder` | Who wrote the trace: `"sensorium 0.8.0"`, `"sensorium-rt 0.3.0"`. Printed in every sentence about what this trace can and cannot say. Both are examples of the SHAPE, not pins — the value is whatever wrote the file, and a reader that compares against a literal is reading it wrong. |
| `lang` | `"python"`, `"rust"`. The reader defaults an absent `lang` to `"python"`, because nothing else existed before the key. |
| `capabilities` | The declaration; see below. |

### `exit_status` may be null, and `exit_status_basis` says why

A recorder cannot observe its own process's exit; a parent can. The Rust
driver installs a cargo runner shim that spawns each test binary, waits, and
records the status — so a runner-waited process carries
`exit_status_basis: "waited"` and the real status, while a process the runner
did not start (a child a test spawned itself) carries `exit_status: null` and
`exit_status_basis: "unwitnessed"`. `exit_signal` carries the signal number
where a waited process was killed by one, and `exit_status` is null there
too.

The readers print the basis with the status — `exit: 0 (waited)`,
`exit: 101 (waited)`, `exit: signal 9 (waited)`, `exit: unwitnessed`
(`query/vocab.exit_phrase`) — and a trace with no basis key at all predates
the distinction and prints exactly as it always did. Rendering a null as
`None` is the failure this key exists to stop: it reads as a status the
program ended with. An `unwitnessed` process never prints a signal either;
nobody waited, so nothing about the ending is known.

A third basis exists from format 5: `exit_status_basis: "not-a-process-exit"` with
`exit_status: null`, written by a recorder whose trace ends because recording was closed and not
because a process ended (a model trace, MODEL-TRACES §2). The readers print `exit: n/a (model
trace)`; rendering that null as a status, or as `0`, is the same failure this key already stops.

Vector: `v10-exit-status-unwitnessed`.

### Witness keys

`db.WITNESS_KEYS` — required **only when the recorder declares the
capability that produces them**:

| Capability | Keys |
|---|---|
| `threads` | `threads_started`, `live_threads` |
| `children` | `children`, `spawn_syscalls`, `audit_errors` |
| `stdin` | `stdin_consumed` |

A capability declared `false` means "not witnessed", and every reader prints
that as a declaration — never as `0`, never as "predates".

### The refusal rule

`db.missing_required` + `db.open_trace`: on a trace whose `trace_format` is
≥ 4 **and** whose `incomplete` is exactly `False`, any missing required key
(or missing witness key of a capability declared true) is a
`TraceFormatError` naming the file, the keys, and the recorder — or
`"an unnamed recorder"` when `recorder` is absent, null or not a string:

```
error: …/<run>.db claims to be finalized (incomplete = false) but lacks
required meta truncated_count -- written by vector 1.0; format 4 refuses
rather than read those as zero
```

Two details a converter must get right:

- **`incomplete` is the claim.** Write it `true` at the start of a run and
  `false` only after the finalize pass. A trace still being written, or one
  that died mid-run, has `incomplete = true` and is never refused for a
  missing key — it is read with the "INCOMPLETE" banner instead, and `diff`
  and `refocus` refuse to issue a verdict against it.
- **A `capabilities` that is present but not an object counts as missing.**
  A list, a string or a null is not a declaration a reader can act on; it is
  reported by name rather than read as ten capabilities the recorder never
  asserted.

Vector: `v01-missing-required-key`.

### Capabilities

`record.boot.CAPABILITIES` is the Python recorder's declaration, and the key
list is the vocabulary:

```python
CAPABILITIES = {"line": True, "locals": True, "return_value": True,
                "tasks": True, "threads": True, "children": True,
                "stdin": True, "output": True, "object_identity": True,
                "refocus": True}
```

What reads each one today:

| Capability | Who reads it, and what happens when it is `false` |
|---|---|
| `line` | `flow` and `watch` refuse outright, printing `REFUSED: <command> needs line, which recorder <r> declares it does not produce (capabilities.line: false); nothing was checked` and exiting 3 — the recording, not the call, is what would have to change (`query/caps.require`). |
| `object_identity` | `flow --object` refuses the same way. |
| `output` | `refocus` prints a blind-spot line — `"the program's output was not recorded on <side> (recorder <r> declares output: false), so the observer-effect cross-check did not run"` — instead of comparing two empty output tables and reporting agreement. |
| `threads` | Gates the `threads_started` / `live_threads` witness keys. `info` and `diff` say "declares threads not witnessed" rather than "predates" or `0`. |
| `children` | Gates `children` / `spawn_syscalls` / `audit_errors`, read the same way by `info` and `refocus`. |
| `stdin` | Gates `stdin_consumed`. |
| `refocus` | `refocus` refuses outright, through the same `caps.require` sentence, before anything is re-run — a rerun has side effects, so it is not something to attempt speculatively. That refusal exits **2**, not 3: nothing was re-run, so the reader's next move is a different command; `refocus`'s POST-rerun `verdict: REFUSED` exits 3. |
| `locals`, `return_value`, `tasks` | Declared, and printed by `info`; no command gates on them yet. Declare them truthfully anyway — a false declaration is a lie the readers will eventually act on. |
| `err_flow` | **Rust-only, and not in the list above**: `boot.CAPABILITIES` is the column the Python recorder also answers, and this key belongs to neither column — it is the RUNTIME's own statement that its records carry err flow, declared by `sensorium-rt` ≥ 0.3.0 in the process header and passed through untouched (`convert/meta.rs::capabilities_json`). A converter that wrote `true` on its own authority would be declaring a capability for a spool set that has none, so a header without it reads `false`. `exceptions` on a Rust trace needs it; see the amended rule below. |

One refusal used to be keyed on `lang` rather than on a capability, because
what was missing was not a record but a **rule**: `exceptions` on a
non-Python trace refuses with `REFUSED: exceptions on a <lang> trace needs
the Rust disposition rules (rung 3); the Python rules would misread Err
values as exceptions; nothing was judged`. The Python index reads
`exc["oid"]` (Rust has none), it lists only RAISE events (so an `Err`
returned and absorbed by a caller's `.ok()` would come back as "no
exceptions recorded"), and its rule 2 would report SWALLOWED for a frame
that re-returned an `Err` without `?`. Each of those is a confident wrong
answer about the program, which is worse than no answer.

**Amended 2026-09-04 (rung 3, design R9).** With the Rust rules written, the
thing an older Rust trace is missing is no longer the rule — it is the
**record**. So `exceptions` dispatches on `lang` FIRST and the three
languages part ways:

- `python` → the Python rules, unchanged.
- `rust` → `caps.require(trace, "err_flow", "exceptions")`. A rung-2 trace
  (`sensorium-rt` 0.2.0, no `err_flow` in its header) takes the standard
  capability sentence and exits **3** — the recording is what would have to
  change, and re-running it under a rung-3 runtime is the reader's next
  move. A trace that declares it gets the Rust dispositions.
- anything else → the lang-keyed refusal above, kept verbatim; only its
  `rust` branch retires.

Vectors: `v14-rust-refusals` pins the lang-keyed refusal, and pins it for
Rust until the Rust rule module (`query/exceptions_rust.py`) ships with the
dispositions; `v19-err-flow-capability-refusal` pins the capability refusal
and replaces `v14`'s `exceptions` question when it does.

`Trace.declares(cap)` has **three** answers, and the three are different
facts (`query/caps.witness_gap`):

| `declares(cap)` | When | The sentence it earns |
|---|---|---|
| `None` | No `capabilities` key at all **and** `lang == "python"` — the only recorder that existed before the declaration. | "…predates that bookkeeping" (the pre-format-4 wording, unchanged). |
| `False` | Declared false; omitted from a declaration that exists; or `capabilities` present but not an object; or absent on a non-Python trace. | "recorder <r> declares <cap> not witnessed (capabilities.<cap>: false) … absence of the record is not a record of absence". |
| `True` | Declared true **and** the witness record is still missing — a recording in flight, one that died before finalizing, or a doctored file. | "recorder <r> declares <cap> witnessed, but this trace carries no <keys> record -- the recording did not finish, or the record was removed". |

Vectors: `v02-declared-not-witnessed`, `v07-flow-refuses-undeclared-line`.

### Optional keys, by writer

**Written by both recorders, read with defaults** (never refused, because
no reader turns their absence into a number): `env` — the whole
environment, variable by variable, which may be withheld for privacy;
`info` refuses to print it and prints `env_hash` instead — `caps`, the
capture caps in force (`{"str": 200, "repr": 200, "sample": 8, "depth": 3}`
in the Python recorder), and the record-time filters `focus`, `include`,
`exclude`, `window`. These six, plus `join` — the cross-trace group and anchor object defined in
[MODEL-TRACES §7](trace-format/MODEL-TRACES.md#7-the-join), written by whichever recorder was
launched or written by a daemon session, copied verbatim from `SENSORIUM_JOIN` when that variable
holds a JSON object and omitted otherwise — are the shared optional set; they are not Python-only.

**Python-only, present today:**

| Key | Meaning |
|---|---|
| `python` | Interpreter version string. |
| `late_writes` | Trace writes that arrived after the database sealed — a **lower bound**. `Trace.dropped_writes()` reads it. Non-zero makes `diff` refuse a verdict. |
| `git_sha`, `git_dirty_hash` | Repository context — **not** a change detector; `source_hashes` is the check with that meaning. |
| `uncaught`, `task_errors`, `spawn_witnessing`, `refocus_of`, `refocus_*` | Run outcome, task-identity failures, spawn-witnessing platform fact, and the refocus stamps `info` prints back. |

**Rust-only, written today** by `cargo-sensorium`'s converter
(`rust/cargo-sensorium/src/convert/meta.rs`) and read by `info`, `runs` and
`Trace.dropped_writes()`. Every one of these is printed only when the trace
carries the key, so a Rust trace from an older converter simply says less:

| Key | Meaning, and what reads it |
|---|---|
| `invocation` | The id of the `cargo sensorium` invocation this process belongs to. `runs` groups every trace of one invocation under `invocation <id>: cargo <cargo_args>` (§6); `info` prints it beside the binary and the pid. |
| `pid`, `ppid` | Process identity within the invocation. `ppid` is what `child_runs` is derived from. |
| `exe` | Absolute path of the binary. `runs` prints its **basename** as the command; the full path stays on `info`'s `cmd:` line. |
| `toolchain`, `rustc_path` | What compiled it. `info`'s interpreter line is `toolchain: <toolchain>` where a Python trace's is `python <version>`. |
| `cargo_args`, `profile` | The cargo command and profile. `runs` prints `cargo_args` in the invocation header. |
| `tool_hash`, `driver_version` | The instrumenting driver's identity. |
| `instrumented_units` | Unit metadata hashes actually instrumented — the units THIS process registered, regardless of which workspace's target directory holds them. `info`: `units: N instrumented, ...`. |
| `uninstrumented` | `[{unit, crate_name, reason}]` — units that fell back to a plain build, **scoped to this invocation's own workspace**. A shared `CARGO_TARGET_DIR` holds every workspace's manifests in one `sensorium/manifests/` directory (measured live on a 13-crate corpus sharing one target: every trace's `info` printed another crate's `fell back` line), and this list is built from a scan of ALL of them; a manifest is included only when its `workspace_root` equals `invocation.json`'s. `info` counts them **with their reasons**: `1 fell back (lto x1)`. |
| `skipped` | `[{file, line, qualname, reason}]` — functions the transformer would not wrap (`const`, `extern`, `async`), for the units THIS process registered. **Not** workspace-scoped: `registered` is already the correct scope (this process's own proc header), and cargo's freshness caching can leave a unit's own manifest on disk from a build old enough to predate the `workspace_root` field entirely without the wrapper running again to refresh it (measured live on the same corpus: `rust/spawned_thread`'s own cached manifest carried no `workspace_root`, and filtering this list the same way `uninstrumented` is filtered silently dropped its own spawn site). Counted the same way as `uninstrumented`. |
| `partial` | `[{file, line, qualname, kind, reason}]` — err-flow sites the transformer could not REACH (design R6), for the units THIS process registered, scoped exactly as `skipped` is and for the same reason. `kind` is `"try"` or `"sink"` — what could not be reached — and `reason` is one of `"macro-arg"` (a `?` inside a macro invocation's tokens), `"async-block"` (a `?` inside an `async {}`, whose future may complete on another thread) or `"struct-literal"` (a `match` scrutinee beginning with a struct literal does not re-parse, so the wrap is refused). Honesty over coverage: an `Err` at one of these sites is recorded by nothing, so it reads AMBIGUOUS, and the list is how a reader learns the difference between "nothing happened there" and "nothing was watching there". |
| `sites` | `[{unit, site, file, qualname, kind, line, how?, test, main}]` — ONE row per instrumented site of the units THIS process registered, `?`/sink/arm sites included (design R1b: they share one per-unit index space with fn items). `kind` is `"fn"`, `"closure"`, `"try"`, `"sink"` or `"arm"`; `line` is the row's one line number whichever key the manifest spelled it under (`firstlineno` on a fn item, `line` on everything else); `how` rides only an err-flow row and names the byte that site writes. The reason this table is in the trace at all is `test` and `main`: the Rust disposition rules read them to say that a chain which left a frame went back to the harness rather than being lost (design R8), and there is nowhere else in a trace those marks could come from. Nothing prints it. |
| `spawns` | `[{file, line, wrapped, reason, qualname, ordinal}]` — every thread-spawning site, rewritten or declared, for the units THIS process registered. Not workspace-scoped, for the same reason as `skipped`. `qualname` is the enclosing NAMED ITEM's file-local path (a fn's own qualname, or a `const`/`static`/associated-const's path when the spawn is in an initialiser) — file-local, so two different files may each carry a site named `run`; a spawn with no named item around it at all (an enum discriminant's expression, say) makes the transformer refuse the file rather than name the child after its module. `ordinal` is the site's 1-based rank among the WRAPPED spawn sites of that `(file, qualname)` in source order, and is **null exactly when `wrapped` is false**: a declared site is not rewritten, takes no name and spends no ordinal. Together they are the site string a wrapped spawn's child is named by — `<parent task name> :: spawn@<qualname>#<ordinal>` (`rust/HONESTY.md` §3) — which is why a task name survives the file moving and the entry's `file`/`line` stay beside it as the lookup a person needs. `info`: `J spawn sites (W wrapped)`. |
| `unreached_files` | Files the recorder knew about and never reached, for the units THIS process registered. Not workspace-scoped, for the same reason as `skipped`. **Named, never counted alone**: `unreached files: 1 -- probe-app/src/maybe.rs`. Vector: `v15-unreached-files-declared`. |
| `manifests_unscoped` | Manifests under `<target>/sensorium/manifests/`, across the WHOLE directory, with no `workspace_root` at all — a manifest written before that field existed (`sensorium-transform`'s `Manifest` reads it with `#[serde(default)]`, so it deserialises as `""` rather than refusing the file), counted rather than silently excluded from `uninstrumented`'s scan with no trace of why. `info`: `manifests unscoped: N -- predate the workspace stamp`, printed only when non-zero. A manifest whose `workspace_root` is simply a DIFFERENT workspace (the ordinary shared-target case) is excluded from `uninstrumented` the same way but is not counted here — it is not old, just not this invocation's. This key says nothing about `skipped`/`spawns`/`unreached_files`, which are never filtered by `workspace_root` at all. |
| `units_refused` | `{"refused": bool, "at": <metadata or null>}`. When true, `info` prints `unit ceiling: recording REFUSED at unit <metadata> -- every later call in this process is unrecorded`: everything after that point is missing and nothing else in the trace says so. Vector: `v14-rust-refusals`. |
| `exit_status_basis`, `exit_signal` | `"waited"` / `"unwitnessed"`, and the signal a waited process was killed by. See the exit-status rule above. |
| `wall_start_ts`, `wall_end_ts` | The runner's own clock around the process; written only when the runner ran it. |
| `records_dropped` | `{"<thread serial>": n}` — writes the runtime **knew** it could not make (a failed `mmap`/`ftruncate` leaves that thread inert). |
| `seq_gaps` | Records minted and never found in any spool — a hole the merge **inferred**, at most one lost mid-write per thread (`rust/HONESTY.md` §4). The bound holds because the runtime mints the sequence number *inside* `Spool::record`, after the record is known writable: a record the spool refused consumes no number, so a witnessed drop is never also a hole. `info` prints it separately from `records_dropped`, because the two have different provenance; `Trace.dropped_writes()` **adds** them — they are disjoint, not overlapping — and a non-zero total makes `diff` refuse a verdict exactly as `late_writes` does. |
| `panics_unrecorded` | Frames that unwound with no PANIC record on their thread (the hook was replaced, or the panic began before recording). |
| `panics_outside_frames` | Panics recorded on a thread with no open frame — there is no frame to attach a RAISE to, and none was written. |
| `err_flow_records` | `{"raise": n, "handled": n}` — RAISE and HANDLED **records on the wire**, which is deliberately not the number of RAISE/HANDLED EVENTS in the trace. A record whose thread had no open frame is counted here and written as no event (see `err_flow_outside_frames`), and the origin RAISE the converter synthesises in front of a frame that closed `err` is an event that was never a record. Two numbers that differ is the ordinary case, not a discrepancy. |
| `err_flow_outside_frames` | Err-flow records that arrived on a thread with no open frame — a `?` inside a skipped `async fn`, or a site whose enclosing CALL was refused. There is no frame to attach the event to, so none was written; the count is the only trace of them, read the same way `panics_outside_frames` is. |
| `closure_frames` | CALL records that opened a frame at a **closure** site rather than a fn item (design R5: a closure containing `?` gets its own frame, qualname `<enclosing>::{{closure}}#k`). The cost of that decision, stated as a number. |
| `child_runs` | `[{run_id, pid, exe}]` — same-invocation processes whose `ppid` is this one. `capabilities.children` is **false** (this recorder hooks no spawn), so `info` prints the declaration AND `child runs: N -- <run ids>`: the declaration alone hides traces the reader could open, and the list alone reads as a complete inventory of the children. Vector: `v11-child-runs-linked`. |

**A note on wording, for the converter author — RESOLVED in 0.6.0 by the
vocabulary table.** Several sentences in `info`, `diff` and `tree` were
Python-worded on a fact that is not Python-specific: threads "started through
Python's own threading/_thread", a unit of work as "an asyncio task", an
interpreter line reading `python ?`. They rendered that way on a `lang: rust`
trace, and the first of them is a positive claim about provenance the trace
does not carry. `src/sensorium/query/vocab.py` is now the table: `terms(trace)`
returns the column for `meta["lang"]`, every renderer reads its words from it,
and `v13-lang-keyed-prose` plus `tests/test_vocab.py` pin the ABSENCE of
`asyncio`, `Python's own`, `threading/_thread`, `coroutine`, `generator` and
`python ?` from every command's output on a Rust trace. The Python column is
the exact string each renderer printed before the table existed — a reworded
Python sentence is a regression, and the legacy suite is the fence.

| Term | Python | Rust | model (format 5) |
|---|---|---|---|
| unit of work | `asyncio task` | `test or spawned thread` | `generation` |
| ...plural | `asyncio task(s)` | `tests or spawned threads` | `generations` |
| a nameless one | `(name unreadable)` — the name existed and `get_name()` raised | `(unnamed: spawned by dependency code)` — it never had one | `(unnamed: no fixture or goal id was supplied)` |
| where threads came from | `through Python's own threading/_thread` | `as OS threads (libtest's per-test threads and threads spawned by workspace code)` | n/a — a model trace declares `threads: false` |
| what ran the program | `python <meta.python>` | `toolchain: <meta.toolchain>` | `model: <meta.model.name> via <meta.model.engine>` |
| a runtime-minted name | `Task-N` is read as no name at all | none exist; every name is the program's | `gen-N` is read as no name at all |

The model column is contract only until S1 lands it in `query/vocab.py`; `terms()` today falls
back to the Python column for any third `lang`, which is the known limit the module's docstring
states.

## 5. Enumerations

### Event kinds

`CALL`, `RETURN`, `RAISE`, `HANDLED`, `LINE`, `YIELD`, `RESUME`.

`CALL`, `RETURN`, `RAISE`, `HANDLED` are the **causal kinds**
(`record.fingerprint.CAUSAL_KINDS`): they and only they enter a fingerprint,
a causal stream, and a `diff`. `LINE`, `YIELD` and `RESUME` are never
hashed, so capture depth can never move a fingerprint.

### Payload keys per kind

Payloads are JSON objects, and the readers reach for optional keys with
`.get`. The keys that are **indexed**, and so are required whenever their
container is present, are called out below: `fmt_exc` indexes an
exception's `type` and `msg`, and `fmt_value` indexes the fields of the tag
it was handed.

| Kind | Keys |
|---|---|
| `CALL` | `args` — `{name: value}`, values in the shape below. Optional: `unread: ["locals"]` when the frame's locals could not be read — **every view that renders a call must carry that marker**: `grep`, `tree` (`name() <unread: locals>`) and `frame` (`args: <unread: locals>`). `(none)` there reads as "called with no arguments", a claim about the program the trace never made; a Rust trace is entirely locals-free, so every one of its CALLs carries it (vector `v12-call-unread-marker-in-tree-and-frame`); `caller_code` (code id) / `caller: "untraced"` naming a caller that had no open frame. Two further keys, `parent_frame` and `unframed`, belong to formats ≤ 2, where coroutine and generator bodies opened no frame; from format 3 every traced body is framed and no recorder writes them, but the readers still render them for the older files. |
| `RETURN` | Optional `value` — one value, **absent** where nothing was captured (never a null tag standing in for one). Optional `outcome` — `"none"` (the site was never probed), `"ok"`, `"err"`, `"panic"`: what the frame ended WITH, which `err` distinguishes from `ok` without the reader having to parse the value. A frame that panicked carries `outcome: "panic"` and no `value`. An `outcome: "err"` RETURN carries **no error-type key of its own**: the Rust wire hands the converter the `E` type at that exit, and the converter spends it on the synthesised origin RAISE described below (`exc.type` there), which is where a reader looks for it. Vector: `v08-return-outcome-dbg-value`. |
| `RAISE`, `HANDLED` | `exc` — `{type, msg, serial}`, plus `oid` in Python and a `kind` on every Rust `exc` (below). Optional `loc`, and **where it sits differs by what raised**: on a Rust err-flow event it is INSIDE `exc`, `"<file>:<line>"` of the SITE, and it is inside `unwind_exc` too; on a Rust panic RAISE it is a payload-level SIBLING of `exc`, `"<file>:<line>:<col>"` where the panic fired. Either way it is not necessarily the frame's own line, and `frame` prints it after the exception. **`type` and `msg` are required**: `query/fmt.fmt_exc` indexes them (`e['type']`, `e['msg']`), and the one way to omit `msg` is to say so — `unread: ["msg"]` inside the `exc` object. What that renders as is keyed on `exc.kind`, because the two recorders leave a message unread for different reasons: an `exc` with no `kind` is Python's and renders `<message unreadable: __str__ raised>`; a Rust `exc` renders `<value not read: the arm binds no name>`, since the ONE Rust site that leaves `msg` unread is an `Err(_) =>` arm binding no name — a panic always carries text, even where that text says the panic was not recorded — and "`__str__` raised" would be a false explanation of it. `serial` is a per-thread exception identity, used to tell "the same exception, still travelling" from a new one. A Rust ERR-FLOW event adds `how` and `chain` beside `exc`; **a Rust panic RAISE carries neither** — no `how`, no `chain` — because a panic is not a chain the err-flow machine minted. See below. Vector: `v16-raise-handled-chain-serial-kind`. |
| `LINE` | `deltas` — `{name: value}` for the locals that changed; optional `unbound` — names that went out of scope this step; optional `unread: ["locals"]`. |
| `YIELD` | `awaiting` — a type name, what the frame parked on. |
| `RESUME` | `thrown` — the exception thrown into the frame, in `exc` shape; absent for an ordinary resumption. |

A captured **value** is a tagged object read by `query/fmt.fmt_value`:
`{"k": "none"}`, `{"k": "num"|"bool", "v": …}`, `{"k": "str", "v": …,
"trunc": bool}`, `{"k": "seq"|"map", "type": …, "len": n|null, "sample":
[…], "trunc": bool}`, `{"k": "obj", "type": …, "oid": n}`,
`{"k": "dbg", "v": "<text>", "trunc": bool}`, or
`{"k": "unread"}` (with `type` and `oid` where the recorder has them).
`len: null` prints `?`; an `unread` list names the reads the observed object
refused. A payload key a recorder cannot fill is **omitted**, never filled
with a zero or an empty string.

Two of those tags are what a recorder that does not decompose values writes,
and both render as themselves rather than as `?`:

- **`dbg`** — the value as the language's own formatter rendered it (Rust's
  `Debug`). The text IS the capture; there is nothing behind it to sample.
  `trunc: true` means the recorder's cap stopped the formatter mid-value, and
  the readers append `…`. A unit return is `{"k": "dbg", "v": "()"}`.
- **`unread` with no `type` and no `oid`** — the value existed and could not
  be read at all, by a recorder that has no object identity to offer either.
  It renders `<unread>`; `<unreadable ?#?>` would invent two fields it never
  had. With `type`/`oid` (the Python shape) it still renders
  `<unreadable Type#42>`.

`oid` (object identity) is Python-only; a recorder that cannot produce it
declares `capabilities.object_identity = false`, and `flow --object`
refuses rather than search for identities the trace does not carry.

### Rust err flow: `exc.kind`, `how`, and `chain`

A Rust RAISE is two different things wearing one event kind: a **panic**
unwinding, and an **`Err` value** travelling out of a function. They are
judged by different rules, so the payload says which:

```json
"exc": {"kind": "err", "type": "demo::ConfigError", "msg": "Missing(\"port\")",
        "serial": 4294967296, "loc": "demo/src/lib.rs:14"},
"how": "try",
"chain": {"serial": 4294967296, "hop": 1, "origin": "workspace",
          "translated": false, "terminal": "swallowed_candidate"}
```

**`exc.kind`** is `"err"` or `"panic"`, and **every `exc` object a Rust
recorder writes carries it** — the RAISE a panic produces, the `unwind_exc`
on the frame it closed, and every err-flow event. A reader selects on this
key and never on `type == "panic"`, which would misread a workspace error
type spelled that way. An `exc` with **no `kind` at all** is a Python
exception: the Python recorder does not write the key, and inventing a
default for it would put a word in that recorder's mouth.

The two kinds' **serials are disjoint namespaces within a thread**. Panic
serials are minted per thread from 1; `Err` chain serials are minted per
thread from `1 << 32` (4294967296), at CONVERSION time rather than at
record time — the wire carries no error identity, and the converter's chain
machine is what assigns one. So two events with the same serial on one
thread are the same thing, whichever kind they are, and a panic can never
be mistaken for a chain.

**`how`** names the site that recorded the event, and is the same word the
site's `sites` row carries: `try` (a `?`), `sink_ok` / `sink_unwrap_or` /
`sink_let_underscore` (`.ok()`, `.unwrap_or*()`, `let _ =`),
`arm_propagate` / `arm_handled` / `arm_ambiguous` (an `Err(..)` match arm,
classified by what its body does), and `exit`. The first three groups arrive
on the wire; **`exit` never does** — it is the converter's own, on the
origin RAISE it synthesises immediately before the RETURN of a frame that
closed `err`, so that an `Err` born by being *returned* has an event to be
reported at. `try`, `arm_propagate` and `exit` are RAISE-class (the `Err`
left the frame); the rest are HANDLED-class (something absorbed or observed
it).

**`chain`** is the identity the disposition rules are computed from:

| Key | Meaning |
|---|---|
| `serial` | The chain's own serial, equal to `exc.serial` on the same event. |
| `hop` | 1-based: the origin event is hop 1, and every RAISE-class event that continues the chain — a `?` or an `arm_propagate` — takes the next number, **including one that fires inside the frame already holding the chain**. A hop is therefore "one more step this `Err` took", not "one more frame boundary crossed": an in-frame `?` on the `Err` a callee just handed back increments it without the holder changing. An event that absorbs or observes a chain (the HANDLED classes) crosses nothing and carries the hop it happened at. |
| `origin` | `"workspace"` — the chain was born at an event this recording saw; or `"outside"` — the first thing seen of it was a HANDLED-class record with no open chain to continue, so the `Err` was born where this thread's recording does not reach. **Any** chainless HANDLED opens an `"outside"` chain, not only a sink: `sink_ok`, `sink_unwrap_or`, `sink_let_underscore` (`let _ = fs::remove_file(p);`), `arm_handled` and `arm_ambiguous` alike. "Outside" includes another thread: the chain machine is per-thread, so an `Err` an instrumented frame produced on a different thread arrives here with no chain of its own. |
| `translated` | This event's recorded type differs from the one the chain carried into it — a `From` conversion on the way out. One chain, and the header prints the origin's type with each hop's own beside it. (Since 2026-09-05 the exit hop at an `err` close goes to the held chain whose text the RETURN carries; before that it went to the innermost, which could label the wrong chain `translated`.) |
| `terminal` | **Present only on the chain's LAST event**, and omitted everywhere else: `swallowed_candidate`, `handled_then_failed`, `ambiguous_escaped`, `merged`, `panicked`, `returned_to_harness`, `left_thread`, `propagated`. How a chain ENDED is a fact about a later record — usually a RETURN, which is no chain's own event — so it is written where the chain's last event is, and a reader takes it from there rather than recomputing it. The words are the machine's, not the verdicts: `swallowed_candidate` is what the disposition rules turn into SWALLOWED after their own checks, never a verdict on its own. |

Two identity limits are documented rather than hidden. There is no error
identity on the wire, so a chain is followed by `(holder frame, type, Debug
text)`: **two `Err`s of one type with identical `Debug` text in one window
are one chain**. And a text the probe had to **truncate is not an identity
at all** — matching falls back to the type alone, because comparing one
200-byte prefix against another would SPLIT a chain whose two sites cut at
different places, and the fallback can only ever merge, which is the safe
direction. `exc.trunc: true` marks a cut message and `exc.type_trunc: true`
a cut type name; both are omitted when nothing was cut.

`exc.msg` means the same thing on every event, which takes one deliberate
unwrapping: an err-flow site reads the `Err`'s own payload (`Boom(7)`)
while a frame's exit reads the whole `Result` (`Err(Boom(7))`), so the
converter strips the derived `Err(..)` wrapper before writing the
synthesised origin RAISE. A probe that could read neither field — an
`Err(_) =>` arm binds nothing — takes the type of the chain it continues,
or the bare `"Err"` with `unread: ["type", "msg"]`. It never invents one.

Vector: `v16-raise-handled-chain-serial-kind`.

### closed_by, unwind_exc, and the panic mapping

`closed_by ∈ {"return", "unwind"}` or NULL (§3). A panic — or any Rust
unwind — is:

```json
"closed_by": "unwind",
"unwind_exc": {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1,
               "loc": "src/lib.rs:4:5"}
```

`kind: "panic"` is there for the same reason it is on the RAISE (§5's err
flow above): `unwind_exc` is an `exc` object, every `exc` object a Rust
recorder writes says which kind it is, and a frame's unwind is what the
Rust rules read to say a chain's holder PANICKED. `oid` appears here instead
of `kind` on a Python trace, and neither recorder writes both.

A panic the converter could not match to a PANIC record on the same thread
carries `serial: 0` and the literal message `<panic message not recorded: no
PANIC record preceded this unwind>` — the frame still says how it ended, and
the message says why it cannot be quoted rather than being left empty. Such
frames are counted in `panics_unrecorded` (§4). `loc` is optional and rides
with the panic when there was a record to read it from; `frame` prints it as
` at <file>:<line>:<col>` after the exception, and prints nothing where the
key is absent.

`type` and `msg` are what the renderers print (`!! panic('boom')`,
`unwound: panic('boom')`). `serial` matters for one specific derivation: a
frame closed by an unwind whose serial equals the serial of the exception
thrown in at its last `RESUME` is read as `cancelled` / `abandoned` /
`thrown` rather than `raised`. Writing `"panic"` as the `closed_by` value
instead is the mistake this vector exists to catch: the reader would see
"not closed" and print ` (open)` about a frame that is finished.

Vector: `v05-closed-by-unwind-panic`. Vector `v06-frames-kind-function`
pins the `kind` half of the same rule.

## 6. Identity and order

- **`events.id` is causal order across threads within one process.** Not a
  per-thread counter, not wall-clock order between processes: one dense
  sequence per trace, assigned in the order the recorder observed the
  events. Every renderer walks it. Two threads running at once therefore
  interleave in the id sequence — that interleaving is the record of what
  happened first. Vector: `v03-two-thread-order`.
- **`ts_ns` is monotonic** within a process and is not the ordering: it is
  for display and duration only.
- **`ts_ns` is comparable across two trace files in exactly one case:** both carry `join.anchor`
  with `clock == "monotonic"` and the same `process` — one process wrote both (a daemon's model
  trace and its `cargo-sensorium` harness trace). A reader that aligns them labels every such
  fact `by clock`, never `by order`, and refuses the alignment when either anchor is absent
  (MODEL-TRACES §7).
- **Thread serials are per process, main = 1.** `frames.thread_id` and
  `events.thread_id` carry the serial, not an OS thread id — two short-lived
  threads that recycle one OS id must key to distinct fingerprints. `main =
  1` is a **recorder convention that no reader enforces**: every reader that
  needs the main thread reads `main_thread_ident` (next bullet), so a
  recorder that mints serials in some other order is read correctly as long
  as it writes that key — and a recorder that writes `main = 1` but omits the
  key gets the reader's inferred fallback, not its convention.
- **`main_thread_ident` is written explicitly**, at boot, as the serial of
  the thread the target was invoked from. `Trace.main_thread_id()` falls
  back to "the thread of whichever event got id 1" only for traces that
  predate the key, and `Trace.main_thread_basis()` reports `"recorded"` vs
  `"inferred"` so no caller mistakes the guess for the fact. `diff` prints
  the basis in its header and only says "the main thread" when both sides
  are recorded.
- **`fingerprint_basis` is written explicitly** (§7). A trace without it is
  read as `"per-thread"`, because that is what the definition was before the
  marker existed.
- **Every unit of work gets a `tasks` row and a `task_fingerprints` row** —
  an asyncio task in Python; a libtest test or a spawned unit in Rust. A unit
  that ran no causal event gets a zero-count fingerprint row rather than no
  row.

**How `runs` lists what a build recorded.** One `cargo sensorium` invocation
writes one trace per process — a `cargo test --all-targets` run is a dozen
test binaries, their doctest processes, and any child they spawned. A trace
carrying `invocation` is listed under a header naming the command they all
came out of, its members indented two spaces and in name order, groups
ordered by their first member's name; a trace with no `invocation` (every
Python one) is listed exactly as before, in place:

```
invocation 20260903-114448-02faf3: cargo test --all-targets
  20260903-114448-f6236e  exit:unwitnessed  events:14  cmd: app-bin --abort
  20260903-114448-f6379a  exit:0 (waited)   events:6   cmd: e7-cb2baf323b4aa074
```

The header does **not** print cargo's own exit status: the traces do not
record one, and a number nothing witnessed is exactly what §4's exit rule
refuses. A member's `cmd:` is the basename of `exe` plus `argv[1:]` — the
full path is thirty characters of build directory and is `info`'s to print.
Vector: `v11-child-runs-linked`.

**How `diff` compares** (`query/diff_cmd`), because a converter's choices
here decide whether its traces can be compared at all:

1. **Thread streams, stepwise.** One thread per side — the main thread —
   compared step by step over `(file, qualname, kind)`, first difference
   reported. Order on one thread is the program's own doing, so order is
   content.
2. **Task streams, as a multiset of `(name, hash)`.** Which task ran first
   is a scheduling fact, not a fact about the program, so the interleaving is
   not compared. A name is content: `t::alpha` matches `t::alpha`, and an
   unnamed stream only ever matches another unnamed one. asyncio's default
   `Task-N` names encode creation order and nothing else, so they are read
   as **no name at all**.
3. **Under the per-task basis a thread's stream is the events that ran in no
   task.** A main thread that emitted nothing is not a failure: `diff` says
   the thread streams held nothing and the tasks carry the whole verdict.
   Vector: `v04-main-thread-silent-tasks-carry`.
4. **Refusals, not hedges.** `incomplete`, dropped writes, two empty streams
   with no task on either side, mismatched fingerprint bases, and a trace
   that ran units of work but recorded no fingerprints for them all produce
   `verdict: REFUSED` (exit 3: a refusal names a recording that would
   settle the comparison). A converter that leaves `task_fingerprints`
   empty for a run that had tasks makes every comparison of it refuse.

## 7. Fingerprints

A fingerprint is a rolling **blake2b, 16-byte digest** over the causal
events, one `update` per event (`record/fingerprint.py`):

```python
h.update(f"{file}\x1f{qualname}\x1f{kind}\n".encode())
```

with `kind` one of `CALL`, `RETURN`, `RAISE`, `HANDLED`. `n_events` is the
number of updates. Values, timing and `LINE` events are excluded by
construction, so capture depth can never alter a fingerprint.

Two things a converter must know about `file` here:

- **The Python recorder hashes a ROOT-RELATIVE file** (`prog.py`), while
  `code_objects.file` holds the absolute path. The two are deliberately
  different strings, and a hash computed over one basis cannot be looked up
  against the other.
- **`diff --ignore-moves` re-hashes both sides at query time over
  `code_objects.file`** (`query/moves.hash_stream`), never one side from the
  stored row and the other from a fresh computation. That is why the flag can
  pair a function that moved between files: the pairing is applied to the
  stream, and the stream is hashed again with the same function the recorder
  uses.

Under `fingerprint_basis = "per-task"` a thread's row covers the causal
events that ran in **no** unit of work, and each unit owns a row of its own.
Under `"per-thread"` (every trace recorded before the marker) a thread's row
covers every causal event on the thread, task events included. The two are
not comparable, and `diff` refuses to compare traces recorded under
different bases when either ran a task.

Format 5 adds a third basis, `"per-generation"`: one row per generation, the digest over sampled
token ids only (MODEL-TRACES §6). `diff` never compares a per-generation trace with either program
basis; that refusal exits 2 (a different call), not 3.

## 8. Conformance vectors

The vector table and its rules live in [`docs/trace-format/VECTORS.md`](trace-format/VECTORS.md) (moved 2026-09-04, rung 3, so this file stays under 800 lines; numbering here is unchanged). The vectors themselves are `docs/trace-format/vectors/v*.json`, run by `tests/test_vectors.py`.
