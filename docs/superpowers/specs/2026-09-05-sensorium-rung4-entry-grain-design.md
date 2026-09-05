# Rung-4 entry — the grain of `exceptions`, and what SWALLOWED claims (design)

Written 2026-09-05, after the borrow repair merged (`main` @ `e307d90`,
sensorium 0.8.1 / crates 0.3.1). Design authority: Claude, under Brice's
rung-3 ruling; Brice chose this slice ahead of rung 4 proper ("both, in that
order", 2026-09-05). Binding parents: the rung-3 design
(`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`,
R8/R15/R16) and the borrow-repair design
(`docs/superpowers/specs/2026-09-05-sensorium-rung3-borrow-repair-design.md`,
B4/B5). Notation rules: `~/.claude/skills/designing-notation-for-llms`;
measurement rules: `~/.claude/skills/rigorous-experiments`.

## 0. What this slice must make true, and why now

The E6⁗ record (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`)
left two things for the entry of rung 4, both in `docs/CARRIED-DEBT.md`:

1. **The wording debt.** §1's "merely observed" clause admits a letter-reading
   under which a match guard's read makes the arm's disposition; under it
   374 of E6⁗-WS's 782 SWALLOWED lines would be FALSE and both workspace
   endpoints a STOP. The gate is design R15's ruled reading (the disposition
   is the BODY's), restated in three records now. It must be paid at its
   source — one definition, cited — before a fourth pre-registration copies
   the clause.
2. **The grain.** The record's own adjudication could not be done at the
   grain the tool prints. `exceptions` prints one block per CHAIN; on the
   workspace run the busiest process printed 54 blocks, 52 of them one site
   (`http.rs:236`), and the question "did the workspace run swallow anything"
   took 144 invocations, one per process. The adjudicator invented a per-site
   table by hand (§4.2, 91 rows) to read 782 lines. That table is the grain
   an LLM reader needs; the tool should print it.

Measured facts this design rests on (from the record's `results.json`, not
re-measured): 144 processes in the `--workspace` invocation; 78 with at least
one SWALLOWED chain, 114 with any chain; max 54 SWALLOWED chains in one
process (52 at one site); median 6; 91 distinct sink sites over 782 chains;
the same site repeats up to 52 times inside one process and up to 303 times
across the invocation; `exceptions` on the largest single process (5.95 M
events) takes 0.07 s. In the corpus, no case has a repeated site
(`silent_swallow`'s two swallows are two sinks), and conformance vectors
v17/v18 pin one chain per shape.

## 1. Decisions (N1–N8)

| Id | Decision | Why | Cost if wrong |
|---|---|---|---|
| N1 | **One definition of SWALLOWED, written once.** `rust/HONESTY.md` §11's SWALLOWED bullet becomes the canonical definition (§2 below): a written sink or an `arm_handled` absorbed the chain in a frame that then closed `ok`, and no VALUE derived from the `Err` — the error, a rendering of it, or a call's product built from it — left the arm by any channel (return, store, move, a kept product). READING the error does not carry it out: a match guard, a `&self` predicate whose result only steers control, a log line. A guarded arm's disposition is its body's. Everything else that cites the rule — design R15, the tool's own sentence in `query/exceptions_rust.py`, the next pre-registration's E6 row — CITES §11 by name and restates nothing. | Three records restated the reading and the third one decided 48 % of a headline. A definition with one home cannot drift. | None: wording. |
| N2 | **The tool's sentence gains the read clause** and is pinned to the ledger: `_escaped`'s detail becomes *"a bound error that is stored, returned or moved out of the arm is not a swallow; an arm that only reads it (a guard, a predicate), formats or logs it and continues is one"*. A test asserts that sentence is a substring of `rust/HONESTY.md` §11. The two corpus cases and the vector that pin the old sentence (`corpus/rust/err_stored`, `corpus/rust/err_rendered_into_value`, `docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json`) are updated BY THIS RULE before the pre-registration is locked, and §1 names them. | The tool's words are the promise a reader meets first; they must be the ledger's. | A corpus pin update that is not the rule's — the record lists the three. |
| N3 | **`exceptions` on a Rust trace prints one block per SHAPE, not per chain.** Two chains are one shape when they have the same disposition tag, the same SITE the verdict is about, and the same verdict text after masking event and frame ids. The site the verdict is about: the SINK for `swallowed` / `handled_then_failed`; the ARM for `ambiguous` (escaped); the ORIGIN site for every disposition whose verdict names no site (`ambiguous` no-sink and merged, `propagated`, `returned-to-harness`, `panicked`, `left_thread`). `Disposition` gains a `site` field the classifier sets; the renderer keys on `(tag, site or origin site, masked verdict)`. Grouping is by first appearance, in origin order. | The record's per-site table IS this key: 91 rows for 782 swallows, keyed by sink. A key that included the origin or the hops would split one sink into paths and stop matching the grain a reader adjudicates at. | A reader who wanted per-chain output drills with `grep e<id>` / `frame f<id>`; nothing is lost from the trace. |
| N4 | **A group of one is printed byte-for-byte as today.** A group of N > 1 prints the FIRST chain's block exactly as today — its head, its verdict sentence (true of that chain, with its own ids), its detail and hops — and appends to the verdict line a bracket naming the group: `SWALLOWED -- absorbed by arm_handled at e1204 (Server::serve L236) in f88, which returned ok  [×52: e1204, e1311, e1418, … +49]`. *(Amended 2026-09-05 before implementation: the first draft rewrote the sentence per disposition — "in 52 frames, each of which returned ok" — which needs a rewrite rule per verdict and can misstate a member; the bracket keeps every printed sentence true of a named chain and adds one fact.)* When the group's masked heads, details or hops are not all equal, one more line says so: `origins: 5 distinct (first shown)` / `details vary (3 distinct; first shown)` / `hops: 4 distinct paths (first shown)`. No new flag: the grouped view is the notation; drilling down is the existing commands' job. | Subtractive (skill §1): delete repetition, add no vocabulary. `×N` is the count spelling the records already use (`memory.rs:156 ×3`) and has no CLI collision; a `--no-group` flag would collide with `ls`'s. | A group whose members differ in a way the masked key does not see is FLAGGED (origins/details/hops vary), never silently merged. |
| N5 | **The `dispositions:` tally still counts CHAINS.** `--limit` counts GROUPS; `--after e<id>` keeps its meaning (chains whose origin is after that event are in scope; groups form over the scope). The continuation note becomes `... K more shape(s); continue with: sensorium exceptions <run> --limit <shown+K>` — paging by raising the limit, because an event-id cursor over grouped output would re-show partial groups. | Every tally in every record stays comparable line for line. A cursor that lies is worse than no cursor. | A reader pages by limit instead of by event; `--after` remains for "after this point". |
| N6 | **`sensorium exceptions <invocation-id>` answers for a whole `cargo sensorium test` invocation.** When `<ref>` matches no trace stem but equals (or uniquely prefixes) the `meta.invocation` of one or more traces, the command opens every member trace, classifies each with the Rust rules, and merges groups across processes on the same key, the bracket naming the spread: `… which returned ok  [×303 over 11 processes: first e1204 in 20260905-091125-fc7302, +302]`. Header: `invocation <id>: cargo <args> -- 144 processes, 114 with Err chains, 30 with none`; every INCOMPLETE member is NAMED before the answer (none-vs-zero: an incomplete process is a gap in the whole); `partial` rows are the union with their process named; `panics` is the sum. The tally is the sum of the members' tallies. `--after` is REFUSED in this mode (`--after names an event of one process; this answer spans 144 — page with --limit`, exit 2). Exit status: 0 if any chain, 1 if none and every member is whole, 3 if none and any member is INCOMPLETE. A member whose recorder declares `err_flow: false` refuses the whole answer, naming it. | `runs` already groups traces by invocation and prints the id; the question an agent asks after `cargo sensorium test --workspace` is about the invocation, and today it costs 144 calls. The id is the one `runs` prints — familiar spelling, existing concept. | Cost is 144 SQLite opens (~0.07 s each measured on the largest); H5 gates it at 60 s. |
| N7 | **Python traces are untouched.** The Python `exceptions` rules and output are byte-identical to 0.8.1 (the shared renderer's Python path does not group). Grouping for Python is a rung-4 inbox item, to be done under the same key rule once the Python dispositions' "site the verdict is about" is defined. | The corpus pins 20 Python cases on per-raise output; this slice is Rust-side by scope. | Two languages differ in grain for one release; stated in the README. |
| N8 | **Deferred, named:** the in-source acknowledgment marker (`// sensorium: acknowledged swallow — <reason>`, read by the transformer, carried through the manifest and converter, printed as `acknowledged N`) is the shape that settles the record's three contestable classes, and it is a Rust-side slice of its own — a file:line allowlist is rejected now because such keys rot when lines move (rigorous-experiments §4). `.is_err()`/`.is_ok()` observation tags, LINE/locals and `refocus` are rung 4 proper. | Keep the entry slice reader-side; the marker's notation is decided so rung 4 can pick it up without re-deciding. | — |

## 2. The definition (N1), verbatim — the text `rust/HONESTY.md` §11 will carry

> **SWALLOWED** — a written sink (`.ok()`, `.unwrap_or*`, `let _ =`) or an
> `arm_handled` absorbed the chain in a frame that then closed `ok`, with no
> later RAISE of it, and **no value derived from the `Err` left the arm**:
> not the error itself (a return, a store, a move), not a rendering of it (a
> `format!` product), not the product of a call it was handed to (design B1:
> a `&e` is exempt only where that product is dropped). **Reading the error
> does not carry it out** — a match guard (`Err(e) if e.kind() == NotFound
> => {}`), a `&self` predicate whose result only steers control, a log line
> (`eprintln!("{e:?}")`) — so the failure never reached the caller and the
> verdict stands; **a guarded arm's disposition is its body's**. The verdict
> says the failure did not reach the caller, not that the program was wrong
> to drop it. A chain first seen at the sink itself is still SWALLOWED,
> detailed *born outside this thread's instrumented frames*. A reader who
> finds a value derived from the `Err` reaching the caller has found a FALSE
> accusation, and every pre-registration's gate on this verdict is 0 of
> them. Adopted 2026-09-05 (rung-4 entry, N1) from design R15's rulings of
> 2026-09-05 and the borrow repair's B1; the acceptance records of
> 2026-09-04 and 2026-09-05 were adjudicated under this reading and say so.

Design R15 gains one dated line: *"Definition moved 2026-09-05 to
`rust/HONESTY.md` §11 (rung-4 entry N1); this row's guard ruling is its
source and is not restated elsewhere."*

## 3. The grouped block (N3–N5), by example

Today (the E6⁗-A run, 4 of its 14 blocks):

```
  e412 HANDLED tests::tempdir handled std::io::error::Error('Os { code: 2, kind: NotFound, … }') L606
    SWALLOWED -- absorbed by sink_let_underscore at e412 (tests::tempdir L606) in f204, which returned ok
      born outside this thread's instrumented frames; absorbed at sink_let_underscore
  e417 HANDLED tests::tempdir handled std::io::error::Error('Os { code: 2, kind: NotFound, … }') L606
    SWALLOWED -- absorbed by sink_let_underscore at e417 (tests::tempdir L606) in f197, which returned ok
      born outside this thread's instrumented frames; absorbed at sink_let_underscore
  …
```

After:

```
  e412 HANDLED tests::tempdir handled std::io::error::Error('Os { code: 2, kind: NotFound, … }') L606
    SWALLOWED -- absorbed by sink_let_underscore at e412 (tests::tempdir L606) in f204, which returned ok  [×4: e412, e417, e420, e443]
      born outside this thread's instrumented frames; absorbed at sink_let_underscore
```

*(Amended 2026-09-05 before implementation, with N4: the bracket form.)*

The id list shows at most 8 ids, then `… +K`. The tally line is unchanged
(`dispositions: swallowed 14, ambiguous 8`): 14 chains, printed as 5 shapes.
A single chain prints exactly as today.

Invocation mode, the header and one group:

```
invocation 20260905-091115-9e8e5a: cargo test --workspace -- 144 processes, 114 with Err chains, 30 with none
raised (1114 chains over 114 processes, 91 swallowing sites):
  e1204 HANDLED Server::serve handled std::io::error::Error('Os { code: 11, kind: WouldBlock, … }') L236
    SWALLOWED -- absorbed by arm_handled at e1204 (Server::serve L236) in f88, which returned ok  [×303 over 11 processes: first e1204 in 20260905-091125-fc7302, +302]
  …
dispositions: swallowed 782, ambiguous 330, panicked 2
```

Masking for the key: `e<digits>` → `e#`, `f<digits>` → `f#` in the verdict
text only. The site the verdict is about comes from the classifier, not from
parsing the sentence.

## 4. Pre-registration (the table the acceptance document's §1 will carry)

Document: `docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`.
The oracle is the PUBLISHED E6⁗ record's `results.json` — numbers already
measured, never re-measured here — and the KEPT trace stores under
`/mnt/extra/sensorium-rung2/sensorium-dir/e6q/{a,ws,ws0}` (the raw evidence
the record cites; the box path is a lens row). §1 is committed ALONE after
the code and its tests, before any number below is read; the runner refuses
on a byte difference; a miss is a STOP with its number.

| Id | Question | Method | Endpoint | Derivation |
|---|---|---|---|---|
| H1 | Did the definition or the grouping move a corpus verdict? | E6's collector over every `corpus/rust/*` case with an `exceptions` question (20), fresh corpus target, the 0.8.1 driver (crates unchanged). The three pins N2 updates by rule are listed here: `err_stored`, `err_rendered_into_value`, vector `v18`. | **20 of 20 equal** (swallow sets, tallies, and every pinned line). | Parent §8 E6, unchanged. |
| H2 | Does the grouped view reproduce the A record at the site grain? | `exceptions 20260905-091115-5da3dc` on the kept `a` store. | **Exactly 5 SWALLOWED groups**, counts `memory.rs:156 ×3, task/exec.rs:606 ×4, memory/store.rs:96 ×2, task/registry.rs:1084 ×4, task/registry.rs:379 ×1`; tally line byte-identical to the record's (`dispositions: swallowed 14, ambiguous 8`). | E6‴/E6⁗ §4.1's five shapes. |
| H3 | Does grouping change any per-process TALLY? | `exceptions <run>` on each of the 144 `ws` traces and each of the 144 `ws0` traces. | **Every tally line byte-identical** to the record's per-process `tally_line` (114 + 114 processes with chains; the 30 + 30 without print `no exceptions recorded`), and per trace the sum of SWALLOWED group counts == the record's `swallowed_count`. | N5: the tally counts chains. |
| H4 | Does the invocation view reproduce the record's per-site table? | `exceptions 20260905-091115-9e8e5a` on `ws`, and the `ws0` invocation likewise. | **ws: 91 SWALLOWED groups whose (site, count) multiset equals the record's 91-row table, summing to 782; tally `swallowed 782, ambiguous 330, panicked 2`; header counts 144 / 114 / 30; INCOMPLETE members 0. ws0: 98 groups summing to 812; tally `swallowed 812, ambiguous 300, panicked 2`.** | The record's §4.2/§4.3 tables and the summed per-process tallies (derived from `results.json` before this design was written: 114 tally lines per arm). |
| H5 | Is the invocation view usable? | Wall of H4's two commands, 60 s kill armed. | **Both under 60 s.** | E0's rule; 144 opens at ≈0.07 s each ≈ 10 s. |
| H6 | Did anything else move? | The whole Python suite (vectors v01–v19, the Python corpus, `tests/test_exceptions*.py`) and the Rust workspace tests. | **Python `exceptions` output byte-identical to 0.8.1** (the suite is the pin; no Python expectation changes); Rust workspace green; v17's single-shape blocks byte-identical. | N7. |

Reported without a gate: output lines and bytes for the busiest `ws`
process before (0.8.1) and after; the 144 concatenated per-process outputs
versus the one invocation view; the number of groups whose `origins vary` /
`details vary` / `hops vary` line printed (an honesty count, not a gate).

## 5. Tests (each mutation-tested)

- `tests/test_exceptions_rust_grouping.py` (new, synthetic traces via
  `tests/rust_traces.py`): two chains at one sink → one `×2` block with both
  ids and the unchanged tally; two chains at two sinks → two blocks
  byte-identical to today; a sink group whose origins differ → the `origins:
  2 distinct` line; `ambiguous` no-sink chains at two origin sites → two
  groups (origin is the site); `--limit 1` with two groups → one block and
  `... 1 more shape; continue with: … --limit 2`; `--after` still scopes by
  origin id; 9 ids → `… +1`.
- `tests/test_exceptions_invocation.py` (new): three synthetic traces sharing
  `meta.invocation`, one INCOMPLETE → the header counts, the INCOMPLETE line
  naming the run, groups merged `×N over M processes`, the summed tally,
  exit 0/1/3 by the rule, `--after` refused with exit 2, a member without
  `err_flow` refusing the whole, an ambiguous prefix refused, a ref that is
  neither a trace nor an invocation → the existing `no trace matches` error.
- `tests/test_honesty_prose.py` (new): the tool's `_escaped` sentence is a
  substring of `rust/HONESTY.md` §11; the SWALLOWED bullet contains the
  four load-bearing phrases ("no value derived from the `Err` left the
  arm", "Reading the error does not carry it out", "a guarded arm's
  disposition is its body's", "0 of them").
- Acceptance tooling: `rust/tests/acceptance_grain.py` (H1–H6 against the
  kept stores and the record's `results.json`; box-free tests for its oracle
  parsing and its byte-lock in `tests/test_acceptance_grain.py`).

## 6. Order of work

T0 branch + ledger + baseline (this document committed; the kept stores'
presence and the record's oracle numbers extracted into the ledger); T1 the
definition (HONESTY §11, R15 pointer, the tool's sentence, the three pins by
rule, the prose test); T2 grouping (`Disposition.site`, the renderer split
into `exceptions_group.py`, tests); T3 invocation mode (`paths` resolution of
an invocation id, `exceptions_invocation.py`, tests); T4 acceptance tooling +
§1 committed ALONE (lock sha recorded); T5 the measurement, once, and §2–§5;
T6 docs (README `exceptions` section, `rust/README.md`, CHANGELOG 0.8.2,
CARRIED-DEBT strikes for the wording debt, the rung-3 inbox §2a additions),
version 0.8.2; final review; fix wave; PR.

## 7. Not in this slice

The acknowledgment marker (N8); grouping for Python traces (N7); `.is_err()`
/ `.is_ok()` observation tags; LINE/locals; `refocus` on Rust; any change to
the transformer, runtime or converter (crates stay 0.3.1); any change to what
is or is not SWALLOWED (the definition is the ruled reading written down,
not a new rule — H1–H4 are the proof).
