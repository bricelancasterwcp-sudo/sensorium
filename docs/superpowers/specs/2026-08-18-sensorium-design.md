# Sensorium v1 — design

Date: 2026-08-18
Status: approved in brainstorm; awaiting written-spec review
Origin: [../../../ORIGIN.md](../../../ORIGIN.md)

## What this is

Sensorium records a Python program's execution — every call, return, and
exception, with captured values — into a queryable trace, so that an AI agent
debugging the program can *perceive* what actually happened instead of
inferring it from logs. The recorder wraps one bounded run; a CLI answers
questions from the trace in dense, stable plain text designed for a language
model's context window.

Two design commitments run through everything:

1. **Instrument honesty.** The tool never answers from data it does not have.
   Truncations are marked, uncaptured sites are counted, divergent reruns are
   labeled, unwitnessed subprocesses are listed. A partial answer that says it
   is partial beats a complete-looking answer that is not.
2. **No model inside the instrument.** Every command is deterministic. The
   sensorium reports; the consuming agent reasons. (The same separation
   witness draws: a model that writes its own alibi is just a better liar.)

## Decisions and rationale

| Decision | Choice | Why |
|---|---|---|
| Substrate | Python 3.12+ via PEP 669 `sys.monitoring` | In-program causality (args, locals, exceptions) with no changes to the target and near-zero cost on disabled events. Most-debugged local codebases are Python. Trace format stays substrate-agnostic for later native adapters. |
| Posture | Wrap a bounded run (`sensorium run -- cmd`) | Fits the real debugging loop (reproduce under recording), tolerates heavy instrumentation, keeps v1 to recorder + store + query layer. |
| Replay strategy | Refocus-by-rerun with fingerprint verification | Full deterministic record/replay of nondeterminism is a research project, and a half-faithful replay is an instrument that lies. Rerunning the same bounded command and *verifying* it was the same execution captures most of the value honestly. |
| Proving ground | Seeded-bug corpus with pre-registered questions | Ground truth is known because we planted the bugs. Becomes a permanent regression suite and overhead benchmark. Real targets (VTT backend) come after the basics are proven. |
| Home | `~/workspace/sensorium`, standalone repo | Same pattern as assay: a public-shaped, self-contained instrument. |

## Architecture

```
sensorium run --focus pkg.mod -- pytest tests/test_x.py
        │
        ▼
  boot (same interpreter, 3.12+)
  ├─ resolve target: console script │ file.py │ -m module
  ├─ install sys.monitoring hooks (recorder frames exempt)
  ├─ execute target in-process (runpy / entry point)
  └─ batched writer ──► ~/.sensorium/traces/<run-id>.db  (SQLite, WAL)
                                │
                                ▼
  sensorium info │ tree │ frame │ grep │ flow │ exceptions │ watch │ diff │ refocus
        └─ dense stable text (or --json), explicit windows, event ids everywhere
```

## 1. Trace model and store

One SQLite file per run: `~/.sensorium/traces/<run-id>.db`.

**Run metadata:** exact argv, cwd, env (hashed and stored for refocus), git SHA
and dirty-state hash when in a repo, Python version, exit status, start/end
times, event counts, capture caps in force, focus spec, whether stdin was
consumed (→ non-refocusable), child processes observed but not witnessed,
`INCOMPLETE` flag if the run died mid-record.

**Core tables:**

- `code_objects` — interned function identities: file, qualname, first line.
  Every event references one; "everything that happened in `fog.compute_visible`"
  is an indexed lookup.
- `frames` — one row per activation: parent frame, code object, call event id,
  return event id, depth. The call tree *is* this table.
- `events` — append-only stream ordered by monotonic event id (ordering is
  ground truth; wall-clock ns is carried, never trusted for ordering). Tagged
  with thread id. Kinds:
  - `CALL` — with captured arguments
  - `RETURN` — with captured value
  - `RAISE` — exception raised
  - `HANDLED` — exception caught, and where. Silently-swallowed exceptions
    become a first-class queryable fact.
  - `LINE` — focus-tier only, carrying *deltas* of changed locals, not full
    snapshots.

**Value capture** is structured, not stringly:

- Primitives (int, float, str, bool, None) stored natively — predicates can
  evaluate them later.
- Containers: type, length, capped element sample.
- Other objects: type, `id()` (so same-object provenance links work), and a
  size-capped safe-repr.
- Every truncation is marked on the stored value. The instrument may capture
  less than everything; it never pretends a truncated value is complete.
- Safe-repr never calls arbitrary `__repr__` unguarded, and capture runs with
  monitoring suspended: a tracer must not perturb or re-enter the program it
  is watching.

**Side streams:**

- stdout/stderr captured and interleaved by event id, so existing print/log
  output lines up against the causal stream.
- Per-thread **fingerprint**: rolling hash over the (code object, event kind)
  sequence. Two runs match iff their fingerprints match; this is what licenses
  refocus. Value contents and timing are deliberately excluded so that capture
  depth cannot alter the fingerprint.

**Capture tiers:**

- Default (no focus): CALL/RETURN/RAISE/HANDLED with value capture, for user
  code only — files under the run's cwd; stdlib and site-packages excluded
  (overridable with `--include` / `--exclude`).
- Focus (`--focus pkg.module` or `--focus pkg.module:func`, repeatable): adds
  `LINE` events and local-variable deltas for the named code.

Threads are supported and tagged. Subprocesses are not followed in v1; they
are listed in run metadata as observed-but-unwitnessed.

## 2. Recorder

`sensorium run [--focus SPEC]... [--include GLOB] [--exclude GLOB] -- <command>`

- Target forms: console script (resolved via `importlib.metadata` entry
  points), a `.py` path, or `-m module`.
- Executes the target **in-process** in the same 3.12+ interpreter after
  installing `sys.monitoring` hooks. Same-interpreter, 3.12+ is a hard
  requirement; the tool refuses clearly otherwise — no silent degradation.
- PEP 669 mechanics: CALL/RETURN/RAISE registered globally; LINE enabled only
  for code objects inside the focus, using per-code-object `DISABLE` so
  unfocused code costs near-nothing. Overhead targets: low single-digit
  multiple at default depth; focused capture may be heavy (bounded repro runs,
  not production). Both multipliers are measured by the corpus harness on
  every change — overhead is a tracked fact, not a hope.
- Re-entrancy guard: recorder frames are never traced; capture runs with
  monitoring suspended.
- Writing: in-memory buffer, batched appends, SQLite WAL. On crash or kill,
  flushed events form a valid partial trace; `info` labels it `INCOMPLETE`
  with the last witnessed event.
- Failure honesty: if monitoring cannot install, the target fails before
  entry, or the buffer exceeds its memory cap, the run dies loudly with a
  diagnosis — never a silently thin trace.

## 3. Query layer

One CLI; every subcommand reads a trace and emits dense, stable plain text:
fixed layouts, one fact per line, event ids on everything so any answer can be
drilled into. `--json` everywhere. No pager, no interactivity: windows are
explicit (`--limit`, `--after EVENT`), and truncated output states how much
remains and the exact command for the next window.

| Command | Question it answers |
|---|---|
| `runs` | What traces exist? |
| `info RUN` | What am I looking at? Exit status, exception summary, hot functions, caps in force, truncations, unwitnessed subprocesses, `INCOMPLETE`/refocus stamps. |
| `tree RUN [--root FRAME \| --around EVENT] [--depth N]` | What actually ran, in what order? Call-tree slice with args, returns, timings. |
| `frame RUN ID` | What happened inside this call? Arguments, local timeline (if focused), return/raise, children. |
| `grep RUN PATTERN [--kind K] [--fn QUALNAME]` | Where does this name/value appear? Search over function names and captured value content. |
| `flow RUN --value V \| --object EVENT:name` | Where did this value come from and go? Ordered provenance by primitive equality / object `id()`. Output is labeled: repr/identity-based lineage, not true dataflow analysis. |
| `exceptions RUN` | Every raise, where handled — with **swallowed silently** as an explicit flagged category. |
| `watch RUN --at QUALNAME --expr 'PRED'` | Every moment a predicate held at matching events — and for numeric comparisons, the near-misses: closest approaches to the boundary. |
| `diff RUN1 RUN2` | Where did two runs of the same command first diverge? Fingerprint divergence point with tree context on both sides. |

`watch` predicates run in a restricted evaluator over captured structured
values (primitives, container lengths) — no arbitrary Python, no live objects.
If a predicate needs a value not captured at some sites, the output says so:
"not captured at 47 of 203 sites (refocus to capture)" — never a silent skip.

## 4. Refocus

`sensorium refocus RUN --focus NEW_SPEC [--window QUALNAME]`

Re-runs the recorded command (same argv, cwd, env restored) with deeper
capture, then compares per-thread fingerprints against the original:

- **MATCH** → new trace stamped `refocus-of: <run>, verified same execution`.
  Answers from it are legitimate answers about the original mystery.
- **DIVERGED** → first divergence point reported with tree context on both
  sides; new trace stamped `divergent-refocus`. Still queryable — it is a
  trace of a *different* execution, and every `info` header says so.

Timing differences never count as divergence; only the (code object, event
kind) sequence does — which is exactly what a focus change must not alter,
and the corpus verifies capture depth never shifts the fingerprint.

Preconditions, refused loudly if unmet: stdin was consumed (stamped
non-refocusable at record time); command no longer resolvable. Changed cwd
contents (git dirty-state hash, when available) warn but do not refuse.

Out of scope, permanently for v1: recording/replaying nondeterminism (time,
random, network). A nondeterministic program gets DIVERGED, and that is the
correct answer; a corpus program exists to prove it is reported.

`--window QUALNAME` narrows deep capture to activations of one function during
the rerun, keeping refocused traces small.

## 5. Corpus and verification

`corpus/` in-repo: ~10 self-contained Python programs (50–200 lines), each
with one seeded bug and a `questions.yaml` pre-registering, before the query
layer is built out:

- the debugging question in plain language,
- the ground-truth answer (known — we planted the bug),
- the sensorium invocation(s) expected to yield it,
- why plain logging cannot answer it.

`corpus/run_corpus.py` records each program, executes the registered queries,
asserts answers against ground truth, and reports overhead multipliers
(default and focused). It is the permanent regression suite and the
performance benchmark.

Bug classes, chosen so every command has at least one question only it can
answer:

1. Wrong value computed through a call chain → `flow` / `grep`
2. Silently swallowed exception → `exceptions`
3. Mutation-at-a-distance via aliasing → `flow --object`
4. Boundary near-miss that never quite fires → `watch`
5. Wrong branch taken → `tree` / `frame`
6. Pass-vs-fail divergence between two inputs → `diff`
7. State visible only under line-level capture → `refocus` MATCH path
8. Deliberately nondeterministic program → registered ground truth is that
   `refocus` reports DIVERGED (the honesty checks are themselves test
   subjects)
9. Unexpected None propagation → `flow` / `watch`
10. Double-call side effect → `tree` / `grep`

## Repo shape, testing, tooling

```
sensorium/
├── ORIGIN.md
├── README.md
├── pyproject.toml            # Python 3.12+, stdlib-only runtime deps
├── src/sensorium/
│   ├── record/               # boot, monitoring hooks, capture, store writer
│   ├── store/                # schema, trace reader
│   ├── query/                # one module per subcommand
│   └── cli.py
├── corpus/
│   ├── run_corpus.py
│   └── <program>/{main.py, questions.yaml}
├── tests/                    # pytest, TDD, 80%+ coverage
└── docs/superpowers/specs/
```

- No runtime dependencies beyond the standard library if at all possible —
  SQLite and `sys.monitoring` are stdlib; an instrument this low-level should
  be boring to install.
- Unit tests directly cover the sharp edges: capture caps, safe-repr guards,
  fingerprinting, the restricted predicate evaluator, partial-trace recovery.
  The corpus alone is too coarse to localize failures.

## Out of scope for v1 (recorded as later phases)

- Async task/coroutine attribution (needed before the VTT backend becomes a
  target)
- Subprocess following
- Attach-to-live-server flight-recorder mode (ring buffer, overhead budget)
- Native substrates (rr adapter for C/C++/Rust) — the trace format is designed
  not to preclude this
- MCP wrapper around the CLI

## Success criteria

v1 is done when:

1. All corpus questions are answered correctly by the registered invocations,
   including the honesty cases (DIVERGED reported; truncation and
   not-captured counts present where registered).
2. Overhead multipliers are measured and reported by the corpus harness:
   default depth in the low single digits, focused depth bounded and stated.
3. A cold agent session, given only a corpus program's failing behavior and
   the CLI, can collapse the mystery using sensorium queries alone — no
   added print statements.
