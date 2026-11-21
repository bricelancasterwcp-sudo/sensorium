# Changelog: the earlier entries, volume 3

`0.13.0`, **moved here 2026-11-20** so
[`CHANGELOG.md`](../../CHANGELOG.md) stays under 800 lines. Volume 2 stood
at 759 lines, and this entry does not fit beside it. Volume 2 is not
appended to. A volume's number is its cut order, not its age: `0.13.0`
follows `0.12.0`, which volume 2 holds.

## 0.13.0 — 2026-09-12

**The debts rung 4 named, funded.** S5 rung 4 closed `DONE-WITH-STOP` with
three endpoints STOPped on its own instrument and a list of what it had left
undone; this slice pays that list. Two recorder gaps are closed for real (a
TypeScript function that returns through a `finally` now records the
finally's own statements, and a Rust block-like statement's LINE row now says
which names went out of scope on it) and rung 4's three STOPs are
re-adjudicated over its committed transcripts under a parser without the four
defects that produced them. Python **0.13.0**; **`sensorium-ts 0.4.0`** (the
RETURN row moves past a finally's rows, which is format-visible);
**`sensorium-rt 0.5.0`** and **`sensorium-transform 0.5.0`** (the wire
grammar gains a delta tag); **`cargo-sensorium 0.6.0`** (the converter reads
it). `TRACE_FORMAT` stays **4** and the wire stays **v1**. No header moves
and no record kind is added; a converter that predates tag 3 refuses a spool
carrying one by name, which is the honest reading of bytes it cannot
describe.

- **A RETURN now follows the rows of the `finally` it passed through.** The
  0.3.0 runtime's `ret` closed the frame before the program's own `finally`
  ran, so every statement that finally minted was dropped, blind spot **38**,
  declared at rung 4 and pinned there as an absence. `sensorium-ts 0.4.0`
  splits the exit in two: a `return` inside a try-with-finally renders
  `__srt.pend(__sf,(x))`, which records the value and leaves the frame open,
  and the wrapper's own `finally{__srt.seal(__sf)}` emits the RETURN after
  the finally's rows. The rule is **static and shape-scoped** (only a
  function whose own body carries a `return` lexically inside a `try` with a
  `finally` gets the deferred exit, nested closures excluded because they own
  their frames) so every other wrapper is byte-identical to 0.3.0's and no
  cost figure in `typescript/HONESTY-COST.md` moves. Measured: a census of
  114 files names **one** function with the shape, and the 0.3.0→0.4.0 golden
  diff over 102 files changes exactly that one function's wrapper, three
  lines. A `finally` the `try` reached by a `throw` is unchanged; it was
  already recorded in full.
- **An abandoned generator reads `unread`, not `undefined`.** A
  seal-deferred generator whose consumer walks away (`.return()`, a `break`
  out of `for…of`) never ran its body to a value, so `seal` emits
  `{k: 'unread'}` where nothing was pended (`f.pending ?? {k: 'unread'}`);
  only an abandoned generator reaches `seal` that way, because every other
  exit pends, a `return`, or the fallthrough close's `pend(__sf, undefined)`.
  A body that falls off its end still pends `undefined` explicitly, so the two
  cases are distinguishable in the record rather than merged into one claim
  the program did not make.
- **A Rust block-like statement's row says what it unbound.** Python has
  emitted `unbound` for `del` and the end of an `except … as e` since rung 3
  and TypeScript on every block-like statement's row since rung 4; Rust
  emitted none at all, so `watch`'s fold reported a `let` inside a block as
  in scope at every site after the block. `sensorium-rt 0.5.0` adds
  `line_unbinding(unit, site, deltas, unbound)` beside `line` (a second
  entry point, so every golden without a block is byte-identical) and the
  wire's existing delta tags gain **3**: a name with no value, written after
  the deltas, counted in the same `n` and under the same 2 KiB budget.
  `cargo-sensorium 0.6.0` reads it into `"unbound": [...]` on the row, and a
  name appearing as both a delta and an unbound in one record is refused by
  name, because a statement cannot write what it unbinds. The transform
  lists head-pattern bindings and the block's own direct `let`s in **source
  order**, and an `else if` chain is ONE statement. An `else if` is the
  outer `if`'s `else_branch` expression and takes no completion row of its
  own, so the outer statement's row unbinds the whole chain. A `let` with no
  initialiser is listed too: `unbound` means this name's scope ended here,
  which is true whether or not a probe ever bound it.
- **A shadowed name is popped, not re-read** (both recorders, stated at
  last). After `{ let x = 2; }` the outer `x` is alive, but a probe of it at
  block exit would read a name the statement did not write, so the block's
  row lists `x` as `unbound` and the fold reports it *not captured* until its
  next write, absence, never a stale value. It is the costly half of the
  rule and it now has an entry in both blind-spot lists with a falsifier
  each: `corpus/rust/focus_block_let`'s shadowed `x`, and a TypeScript unit
  test in `bindings.test.mjs`.
- **`info`'s `truncated values:` counts what inspect cut** (blind spot 36).
  A string cut at `util.inspect`'s 100 characters carries `trunc: false`, so
  the counter that read the flag alone under-reported. `js_inspect.is_clipped`
  now answers off the `… N more characters` tail as well as the flag, pinned
  by `corpus/typescript/focus_long_string`.
- **A new TypeScript corpus case can ask an `exceptions` question** (blind
  spot 37). `typescript/acceptance/e6ts.py`'s `PRE_REGISTERED` table is
  re-registered by rung 3's own procedure (the row lands in its own commit
  with its adjudication, before the case's question exists) and the
  procedure is written down in the instrument that enforces it.
  `focus_catch_binding` is the first case to use it, and it caught the
  procedure's weak point (below).
- **`watch`'s "not in scope" guidance is keyed by language.** It named `del`
  and `except E as e:` (two Python statements) on a Rust or a TypeScript
  trace. `vocab.Terms` gains `scope_exit_note`, with Python's two entries
  character for character what the command printed before the field existed.
- Seams and hygiene, each a pure move or a mechanical fix: `tests/test_corpus.py`
  (at exactly 800) splits its harness half to `tests/test_corpus_harness.py`;
  `rt.mjs`'s naming block (`UNNAMED`, `titleOf`, `nameProvider`, `ask`,
  `nameFor`) moves to `typescript/src/naming.mjs` with the export set
  unchanged; `lineOf` and `terminatorFor` move to `typescript/src/positions.mjs`,
  which removes the `transform.mjs ⇄ probe.mjs` import cycle, a test now
  asserts the import graph over `typescript/src/` is acyclic; `CHANGELOG-ARCHIVE-2.md`
  opens, on the numbered-volume rule this file's debt ledger already uses.
  `captures()` on an odd pairs list **throws** rather than dropping the
  trailing name; `resolve.survey` wraps `sitesOf` in a `try`, counts the
  throw as unparsable and names the file; `Resolution.wall` is persisted as
  `resolver_wall_s` in the invocation's manifest, so an instrument can time
  the resolver without timing itself; `tests/test_ts_honesty_prose.py` reads
  `HONESTY-COST.md`'s three acceptance paths structurally, the same way it
  reads the blind-spot lists. The named minors rung 4 left in the readers,
  the recorder, the tests and the prose are closed at their sites, and
  `docs/CARRIED-DEBT.md` says which seven are not and why.
- Three new corpus cases (`focus_finally_return`, `focus_long_string`,
  `focus_block_let`) and an `exceptions` question on `focus_catch_binding`
  bring the corpus to **108 cases, 229 questions**. One new vector,
  **`v40-rust-line-unbound`**: the tag-3 row and its `frame` and `watch`
  renderings. One corpus filter is corrected: rung 2's `finally_return` case
  filtered vitest with the bare string `finally_return`, which a new
  directory named `focus_finally_return` also matches, so the case recorded
  two test files in unstable order; the filter is `"/finally_return"` now.

**The slice ships `DONE-WITH-STOP`**, seven gated endpoints and two fences,
each read once, six of the seven PASS (record
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md` §3–§5).
**E12′ closes rung 4's three STOPs**: over the same committed transcripts,
under a parser free of the four defects rung 4's post-mortem named, **H2′
5/5, H4′ 3/3 and H5′ 7/7**, six sites read three independent ways with
`focus_matched` one lower for the one qualname two anonymous arrows share;
all three `watch` triples, W2's clause read off the row's own `unbound`
rather than off a line number; and the CALL sighting the old parser printed
but could not see, found at `e10` with its line taken from the code object.
**E13 4/4**, **E14 5/5** and **H8′ 8/8**: on the same lens under
`sensorium-ts 0.4.0` the recorder reproduces rung 4's nine LINE rows
text-equal, the same six resolved sites, the same `CALL 117 RETURN 117 …
LINE 295` over 529 events, and leaves the lens byte-identical, 748 OK
before and after. The fences and the eight suite readings are green: 108
corpus cases / 229 questions / 0 failures, `pytest -q` **4228 passed, 24
skipped**, `cargo test --workspace` **804 passed**, `npm --prefix typescript
test` **559 passed**, the probes' **146** checks, and 0 of nine leak needles
over this slice's own transcripts.

**The one STOP is this slice's own pre-registration, and it reported it
against itself.** **E6-TS′** pre-registered `focus_catch_binding` at **0**
SWALLOWED; the answer prints **1**, by two derivations that agree. The clause
was written in `grep --kind HANDLED`'s vocabulary (a HANDLED event, traced
with confidence) and "nothing swallowed" was concluded from that confidence,
where `exceptions`'s own documented rule says `swallowed` is exactly this
shape: an absorbing handler took it and the frame holding the handler then
returned. The lesson is about WHICH VOCABULARY a hand adjudication is written
in. A pre-registration of a command's output must derive from that command's
own documented rule, never from a sibling command's kinds. The mechanism
worked: the wrong clause was left standing, a corrected one (**E6-TS″**,
22/22 PASS) was pre-registered beside it from the rule before any cell was
read, and both were measured once and reported.

`docs/TRACE-FORMAT.md`, `docs/trace-format/VECTORS.md`, `docs/query.md`,
`docs/corpus.md`, both HONESTY sets (TypeScript blind spot **38** struck and
**39** added; Rust **32** and **33** added), `rust/HONESTY.md`, `rust/HONESTY-INDEX.md`,
`rust/HONESTY-REFOCUS.md`, `docs/trace-format/TYPESCRIPT-KEYS.md` and the
three READMEs are amended to this state; the design's §12 carries all
thirteen amendments and every controller ruling that changed a section's
reading. `docs/CARRIED-DEBT.md` closes rung 4's carried debts (three of them
by this slice's own measurement) and opens this slice's.
