# Conformance vectors (TRACE-FORMAT §8)

> Moved out of `docs/TRACE-FORMAT.md` on 2026-09-04 (rung 3) to keep that file under the 800-line ceiling; `docs/TRACE-FORMAT.md` §8 is a pointer here. Section numbering in TRACE-FORMAT is unchanged.


`docs/trace-format/vectors/*.json`. Each file describes one trace and the
questions the CLI must answer about it:

```json
{"id": "v03-two-thread-order",
 "asserts": "events.id is causal order ACROSS threads within one process ...",
 "meta": {"trace_format": 4, "incomplete": false, "run_id": "$RUN", "...": "..."},
 "codes": [["/w/a.py", "main", 1], ["/w/a.py", "worker", 9]],
 "frames": [{"parent": null, "code": 1, "call": 1, "return": 4, "depth": 0, "thread": 1, "closed_by": "return", "kind": "function"},
            {"parent": null, "code": 2, "call": 2, "return": 3, "depth": 0, "thread": 2, "closed_by": "return", "kind": "function"}],
 "events": [{"ts": 1000, "thread": 1, "kind": "CALL", "code": 1, "line": 1, "payload": {"args": {}}, "task": null},
            {"ts": 2000, "thread": 2, "kind": "CALL", "code": 2, "line": 9, "payload": {"args": {}}, "task": null},
            {"ts": 3000, "thread": 2, "kind": "RETURN", "frame": 2, "code": 2, "line": null, "payload": {"value": {"k": "none"}}, "task": null},
            {"ts": 4000, "thread": 1, "kind": "RETURN", "frame": 1, "code": 1, "line": null, "payload": {"value": {"k": "none"}}, "task": null}],
 "fingerprints": "compute",
 "questions": [{"id": "roots-in-event-order",
                "ask": "Does `tree` render both threads' root frames, each against the event id it was called at?",
                "command": ["tree", "$RUN"],
                "expect_exit": 0,
                "expect_line": [["f1 e1", "main"], ["f2 e2", "worker"]],
                "expect_count": {"f1 e1": 1, "f2 e2": 1}}]}
```

- `codes`, `frames`, `events`, `tasks` are written in list order, so **ids
  are 1-based positions**: `frames[0]` is `f1`, `events[1]` is `e2`, and a
  frame's `code` / `call` / `return` refer to those positions. A frame may
  also carry `unwind_exc` (with `closed_by: "unwind"`); a `tasks` entry is
  `[id, name, thread]`, and an event's `task` names one.
- **The builder writes the rows the recorder writes.** A CALL is built with
  `frame_id` NULL whatever the vector says, and a vector that names a
  `frame` on a CALL row is refused rather than quietly built (§3); the
  frame is reached from its own `call` instead. `tests/test_vectors.py`
  asserts both halves on every vector.
- `fingerprints: "compute"` derives every row the way the recorder does —
  per task for events carrying a `task`, per thread for the rest — but over
  the file string the vector declares in `codes`, i.e. the **absolute
  `code_objects.file`**, where the Python recorder hashes a root-relative
  name (§7). A vector's stored hashes are therefore on the builder's basis
  (the same basis `diff --ignore-moves` re-hashes on) and are not comparable
  with hashes a Python run recorded. `threads_with_rows` forces a row
  (zero-count) for a thread that emitted nothing; task rows need no such key,
  because every entry in `tasks` gets one (§6) whether it ran an event or
  not.
- `copies: 2` makes the runner copy the built trace to a second run id, so a
  vector can ask a two-run question. `$RUN` and `$RUN2` are substituted in
  `meta` values and in commands. The copy is a byte copy: its
  `meta["run_id"]` still names the FIRST run, which nothing reads — `diff`
  labels its two sides by filename stem — so a two-run question is asked of
  `$RUN2` by path, never by the run id inside it.
- `questions` use the corpus's assertion vocabulary and are checked by
  `corpus.run_corpus.check_question` over stdout **and** stderr:
  `expect_exit` (default 0), `expect_contains`, `expect_line` (substrings
  that must share one line), `expect_count` (exact occurrences),
  `expect_absent`.

Run them:

```bash
python -m pytest tests/test_vectors.py
```

The builder is `tests/vectors.py` and the runner `tests/test_vectors.py`;
the runner drives the **real** CLI in a subprocess against a disposable
trace store, so a vector passes only if the shipped commands answer that
way.

**Every vector states what it asserts and asks at least one question.** The
`asserts` line is the claim in prose; a question with no assertion always
passes, which is the one thing a conformance suite must not contain, so the
runner refuses a vector or a question that carries neither. Add a vector for
each new enumeration value and each new rule — a rule with no vector is a
sentence in a document, not a contract.

These nineteen pin the rules this document states in prose. The first seven
were written before the Rust recorder existed; `v08`–`v15` were added in
0.6.0, when it did, and pin the values it actually writes rather than a guess
about them. `v16`–`v19` were added in rung 3: `v16` pins the SHAPE of an
`Err` chain (`exc.kind`, the serial namespace, `how` and `chain`), and
`v17`–`v19` pin what the Rust `exceptions` rules do with it — the one shape
called SWALLOWED, the shapes that are ambiguous by design, and the
capability refusal on a recording made before err-flow records existed.
`v14`'s `exceptions` question, which stood in for them while the rules did
not exist, retired into `v19`; its other three questions stand. The design
spec's §5.3 and §5.6 ask for one vector per value of every enumeration per
language, and that is still not complete: three `chain.terminal` values
(`panicked`, `left_thread`, `handled_then_failed`) are pinned only by
`tests/test_exceptions_rust.py`, not by a vector.

| Vector | Rule it pins |
|---|---|
| `v01-missing-required-key` | A finalized format-4 trace missing a required key is refused by name, naming its recorder. |
| `v02-declared-not-witnessed` | A declared-false capability is read as a declaration: `info` prints the declaration and why each record is absent, never "predates" and never a zero. |
| `v03-two-thread-order` | `events.id` is causal order across threads. |
| `v04-main-thread-silent-tasks-carry` | A silent main thread still gets a fingerprint row; the units of work carry the verdict. |
| `v05-closed-by-unwind-panic` | A panic is `closed_by = "unwind"` with an `unwind_exc`, and is never rendered as an open frame. |
| `v06-frames-kind-function` | `frames.kind` is never NULL; `"function"` renders as no marker. |
| `v07-flow-refuses-undeclared-line` | A command gated on a capability refuses on a trace that declares it false. |
| `v08-return-outcome-dbg-value` | A RETURN carries `outcome` beside its optional `value`; a `dbg` value renders as its text (with `…` when clipped) and a bare `unread` as `<unread>` — never as `?`. |
| `v09-zero-count-task-row` | A unit of work that ran no causal event still owns a `tasks` row and a zero-count fingerprint row, and `info` and `diff` count it. |
| `v10-exit-status-unwitnessed` | `exit_status` may be null; `exit_status_basis` says whether anyone waited, and the readers print the basis rather than `None`. |
| `v11-child-runs-linked` | `capabilities.children: false` and `child_runs` are printed together, never one without the other; `runs` groups a build's traces under their invocation. |
| `v12-call-unread-marker-in-tree-and-frame` | A CALL's `unread: ["locals"]` reaches every view — `tree`, `frame` and `grep` — and `(none)` never stands in for it. |
| `v13-lang-keyed-prose` | Every sentence about a trace is keyed on `meta["lang"]`: no `asyncio`, `Python's own`, `threading/_thread`, `coroutine`, `generator` or `python ?` on a Rust trace. |
| `v14-rust-refusals` | A command whose rules are one language's refuses on another's trace rather than answering with rules that do not apply; `info` prints the unit ceiling. |
| `v15-unreached-files-declared` | A file the recorder knew about and never reached is named, and the unit counts carry their reasons. |
| `v16-raise-handled-chain-serial-kind` | A Rust `Err` RAISE/HANDLED carries `exc.kind: "err"`, a chain serial from the `1 << 32` namespace, and a `chain` object beside its `how`; the frames those events fired in still read as RETURNED, not unwound. |
| `v17-exceptions-rust-swallowed` | `exceptions` reports one line per Err CHAIN at its origin, with every hop; a sink whose frame then returned ok is the one shape called SWALLOWED, a `#[test]` fn's return is `returned-to-harness` (the mark from `meta.sites`), `chain.terminal` is read and never recomputed, a clipped page never clips the tally, and `meta.partial` is printed by both `info` and `exceptions`. |
| `v18-exceptions-rust-ambiguous-merge` | AMBIGUOUS is the default and nothing falls through to an accusation: two different `Err`s in one window are `merged` and both ambiguous, a bound-and-escaped `Err(e) =>` arm is ambiguous, and the tally prints in the fixed order. |
| `v19-err-flow-capability-refusal` | What an older Rust recording lacks is a RECORD, so `exceptions` refuses through `capabilities.err_flow` with the standard sentence and exit 3, before any rule reads an event; the retired lang-keyed sentence does not come back, and no other command is gated. |
