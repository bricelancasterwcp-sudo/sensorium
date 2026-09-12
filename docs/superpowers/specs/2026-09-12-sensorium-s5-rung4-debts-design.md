# S5 rung 4's debts, funded — E12′, the finally seal, the Rust `unbound`, and the closable list: design

**Date:** 2026-09-12. **Base:** `main` @ `e6f5035` (PR #34, Python 0.12.0 /
sensorium-ts 0.3.0 / rt 0.4.1 / transform 0.4.4 / driver 0.5.3).
**Author:** Claude, design authority for sensorium (ruling 2026-09-07).
**Scope ruling (Brice, 2026-09-12):** "everything else is done and tested
properly" before the C conversation; debts first, then refocus for TypeScript
as its own slice; the Rust fold funded here too.

What this slice is: the button-up of S5 rung 4, on the 2026-09-08 button-up's
form. Everything mechanical or instrument-level that rung 4 left is closed and
tested; the three endpoints whose word was a fact about the instrument are
re-registered under fixed instruments; the one runtime gap rung 4 declared
(blind spot 38) is closed; and Rust's own fold debt, raised by building
TypeScript's `unbound` beside it, is closed by giving Rust the same row. What
it is not: a design conversation. Every item that needs a ruling on WHAT the
tool should say — the nested-arrow spelling, identity for anonymous
function-likes, place writes, `this`, the four unreachable shapes — stays in
the C pile with its reason restated in §9.

## 0. Rulings (Claude, 2026-09-12)

- **R1 — E12′ re-adjudicates, it does not re-run.** H2, H4 and H5 STOPped on
  the instrument (record §4.2/§4.4/§4.5, R37), and the data they were read
  from is committed and hash-locked (`…-focus-reads/`,
  `…-focus-tracehashes.txt`). A fresh lens session would answer a question
  about a parser with a new run's noise mixed in. The three are re-registered
  as readings of the COMMITTED transcripts under a fixed instrument, on the
  E6′→E6″ precedent's form (one new record section, one new instrument, the
  cited instrument untouched), plus ONE live run whose only job is to say
  this slice's recorder still produces the same rows on the same lens (H8′).
- **R2 — the finally seal is static and shape-scoped.** Only a function whose
  own body carries a `return` lexically inside a `try` with a `finally`
  (nested closures excluded, they own their frames) gets the deferred exit.
  Every other wrapper is byte-identical to 0.3.0's, so every locked cost
  number and every golden that does not carry the shape holds. A finally on
  every wrapper would move every cost figure for a shape most functions lack.
- **R3 — Rust `unbound` rides the LINE payload as a new delta tag, not a new
  record kind.** The wire already tags each delta (`0` no value, `1` debug
  text, `2` unread); `3` = unbound, name only. No header change, no new kind;
  an older converter meeting tag 3 refuses "unknown tag", which is the honest
  reading of a spool it cannot describe.
- **R4 — a shadowed name is popped, not re-read.** After `{ let x = 2; }` the
  outer `x` is alive, but a probe of it at block exit would read a name the
  statement did not write, and a moved outer binding makes that a compile
  error the transform cannot see. So the block's row lists `x` as `unbound`
  and the fold reports it as *not captured* until its next write — never a
  stale value. TypeScript's `declaredIn` already behaves this way, undocumented;
  both recorders get the same blind-spot entry (§5.5).
- **R5 — `line`'s signature does not change.** A block-like statement with
  names to unbind calls a second runtime entry point, `line_unbinding`, so
  every golden without a block is byte-identical.
- **R6 — versions.** Python **0.13.0**, sensorium-ts **0.4.0** (the RETURN
  row moves past a finally's rows: a format-visible change), `sensorium-rt`
  **0.5.0** (wire grammar extended), `sensorium-transform` **0.5.0**,
  `cargo-sensorium` **0.6.0** (the converter reads tag 3). No licence clause
  turns on the rt hash — the README says the recorder's own `--extern
  sensorium_rt=…` fragment is REMOVED from the env compare and named — and
  LINE is not a causal kind, so a refocus pair across the boundary can still
  read MATCH; §5.6 says what such a pair reports.
- **R7 — the cut opens `CHANGELOG-ARCHIVE-2.md`.** `CHANGELOG.md` is at 702
  and this entry will not fit under the cut-before-append rule without a
  cut; the archive is at 742 and cannot take one. Volume 2 opens with a
  preamble in the archive's voice and a pointer from volume 1.
- **R8 — Rust's new tests take a new file.** `golden.rs` (788) and `edges.rs`
  (784) are inside the ceiling's last twelve lines; the unbound goldens and
  edges go to `rust/sensorium-transform/tests/unbound.rs`.

## 1. What ships

| Piece | Version | What changes |
|---|---|---|
| `sensorium` (Python) | 0.13.0 | `truncated_count` counts inspect's tail (bs 36); `info`/`exceptions_group`/`flow_cmd` minors; `test_corpus.py` split; reader unchanged for `unbound` (it already folds it) |
| `sensorium-ts` | 0.4.0 | the finally seal (`pend`/`seal`, the detector); `positions.mjs`; `resolve.survey` guard; `captures()` refuses a trailing unpaired name |
| `sensorium-rt` | 0.5.0 | `line_unbinding`; delta tag 3 |
| `sensorium-transform` | 0.5.0 | the unbind rule on block-like statements |
| `cargo-sensorium` | 0.6.0 | converter reads tag 3 → `unbound` on the row |
| instruments | — | `e12p_report.py` (+ `e12p.sh`); `e6ts.py`'s table re-registered by rung 3's procedure |
| records | — | `docs/superpowers/acceptance/<T0 date>-sensorium-s5-rung4-debts.md` (E12′, E13, E14, H8′), dated on the day T0 commits it |
| docs | — | TRACE-FORMAT (two sentences), TYPESCRIPT-KEYS, both HONESTY sets, blind spot 38 struck + 39/Rust-N added, CARRIED-DEBT struck + new section, CHANGELOG + ARCHIVE-2, corpus.md (the E6-TS procedure), the two skills' one line each |

## 2. The inventory (swept at `e6f5035`)

Ledger keys: CD = `docs/CARRIED-DEBT.md`, BS = `typescript/HONESTY-BLIND-SPOTS.md`,
REC = the rung-4 record. Classes as 2026-09-08: **A** mechanical, fundable;
**B** at the ceiling; **D** closable only by a dated note; **C** design-level,
not this slice.

### A — funded here

| # | ledger | title | how it closes | §
|---|---|---|---|---|
| 1 | CD §"gaps" 3, REC §4.4/§4.5 | H2/H4/H5 STOPped on the instrument | E12′, re-registered over committed data under `e12p_report.py` | 3 |
| 2 | CD §"gaps" 4 | `e12_report.py`'s parser drops a RETURN row (one space before `->`) | the new parser accepts one or two; the old file keeps its text | 3.2 |
| 3 | CD minors (last), BS 38, R42 | a finally after a return mints no row | the finally seal | 4 |
| 4 | CD §"deferred" 1 | Rust's fold keeps a dead block-scoped `let` alive | Rust `unbound` | 5 |
| 5 | BS 36, P7 | `truncated values:` misses an inspect-side cut | converter counts the `... N more characters` tail via `js_inspect.INSPECT_MORE` | 6.1 |
| 6 | BS 37 | a new TS corpus case cannot ask an `exceptions` question | the table re-registered by rung 3's procedure; `focus_catch_binding`'s row added in its own commit; the procedure written down | 6.2 |
| 7 | CD "files near the ceiling", last | `HONESTY-COST.md` / `HONESTY-BLIND-SPOTS.md` covered by no prose test | `tests/test_ts_honesty_prose.py` | 6.3 |
| 8 | CD minors, readers | `flow_cmd.py:565` unguarded `v["type"]`; `exceptions_group._one` `AttributeError` on a non-map; `sites._anchor` cwd fallback; `find_in_value` `path` third; `js_number` ≥ 2^53 | guard / named refusal / assert-or-refuse / leave with a comment where no caller reaches it | 6.4 |
| 9 | CD minors, recorder | `captures()` drops a trailing unpaired name; dead typedefs `bindings.mjs:25,26,28`; `({a = 1} = o)` untested; `isGuard`/`isGuardBody` re-derive `isStatementPosition`; `transform.mjs ⇄ probe.mjs` cycle; `resolve.survey` unguarded `sitesOf` | refuse loudly with the name; delete; test; derive; `positions.mjs`; `try` → counted unparsable with the file named on stderr | 6.4 |
| 10 | CD minors, tests | "777"→781; `test_ts_live.py:110`; `second_run` closed-key check; `cases.py:281-285` wording; `focus_async` needle; fixture `driver_version`; `naming.test.mjs` scrub; `resolve.test.mjs` temp roots; unused imports; `driver.py:84`; `Resolution.wall` persisted; `lock.py:391` slice | each as stated | 6.4 |
| 11 | CD minors, modules | `listNames` dedupe (documented why not); `bindings.test.mjs:307` name over-claims the `var` head | comment; rename the test to what it pins | 6.4 |
| 12 | CD minors, prose | `focus.md:296` tilde path; §1's "pin table" singular; §1.4's CALL table deviation | fix the tilde; the two record items are inside a locked §1 — a dated NOTE in CD only | 6.4 / D |
| 13 | CD "files near the ceiling" | `tests/test_corpus.py` at 800 | the harness half moves to `tests/test_corpus_harness.py` | 7 |
| 14 | CD "files near the ceiling" | `CHANGELOG-ARCHIVE.md` cannot take another cut | volume 2 (R7) | 7 |
| 15 | CD rung-3 §"new debts" 3 | spec §4.3's prose vs the shipped whole-word rule | the dated parenthesis §4.3 already asked for | 6.5 |

### B — at the ceiling, touched by A

`typescript/src/rt.mjs` 783 (+ the seal ≈ 30 lines → seam first, §7),
`tests/test_corpus.py` 800 (#13), `CHANGELOG.md` 702 / `CHANGELOG-ARCHIVE.md`
742 (#14), `README.md` 799 (net-zero or a seam, §7), `docs/TRACE-FORMAT.md`
788 (two sentences fit), `typescript/HONESTY.md` 786 (one line, fits),
`rust/sensorium-transform/tests/{golden,edges}.rs` (R8).

### D — closed by a dated note

CD rung-3 §"new debts" 1 (two variants unmeasured on a lens — nothing to
build), 4 (row 1's "library `try`" — the locked table keeps its words), 5
(`Index.left_frame` window-2 rethrow — rung-2 behaviour, no lens showed it,
a corpus case would pin a shape nobody has met; NOTE names the shape and the
test that would pin it), 6 (`lens.stamp()` on the three legacy assemblers —
frozen paths; NOTE), 2 (`test_acceptance_scripts.py` watched); #12's two
locked-record items.

### C — not this slice (§9)

The nested-arrow `--focus` spelling and anonymous-function identity (CD
§"gaps" 1–2); blind spots 28–31 (place writes, `this`, conditional
assignment, `switch` discriminant), 34 (`enum`/`namespace`/`static {}`), 35
(`undefined`/BigInt at `flow --value`); the `focus matched:` line's length
(accepted, R31) and its printing on Rust traces (accepted, R32); the skill
living outside the repo (the same arrangement as Python's and Rust's).

## 3. E12′ — the three endpoints, re-registered

### 3.1 The question and the data

The questions are rung 4's H2, H4 and H5, verbatim from the locked record's
§1 (record `2026-09-11-sensorium-s5-rung4-focus.md`, §1 sha-locked by
`tests/test_acceptance_s5_rung4_lock.py`). The data is what rung 4 read them
from: the transcripts committed under
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/` and
the trace hashes in `…-focus-tracehashes.txt`. Before any endpoint is read,
every transcript is `sha256sum -c`'d against the list the new record's §1
pins (the list is written from `git ls-files` at T0, not by hand), and the
store copy under `/mnt/extra/sensorium-s5/store-rung4ts` is checked against
`…-tracehashes.txt`. A hash that does not match STOPs the session before it
starts: the reading would be of data the record does not describe.

### 3.2 The instrument

`typescript/acceptance/e12p_report.py`. `e12_report.py` and `e12.sh` are
cited by a locked record and keep their text; each gains one header line
pointing at its successor (the `e6.sh`/`e6pp.sh` precedent). What the new
parser does differently, each a defect record §4.4/§4.5 named:

- **A CALL row's name is the token before its `(`.** `flow` prints
  `parseDiceGroups(formula='1d20')` where the old parser expected a bare
  qualname.
- **A CALL row's line is the code object's, read from the trace.** A printed
  CALL carries no `L<line>`; §1.3's `diceQueue.ts:68` is the definition line,
  which the `code` table holds. The population test for a CALL sighting
  therefore joins the printed event id to the trace, and reads `line` there.
- **A RETURN row's arrow takes one space or two.** `-> 20` and `->  20` are
  the same row.
- **A `watch` HIT is classed by its payload, not its line.** A row carrying
  `unbound` is a completion row; a row carrying deltas and no `unbound` on
  the same line is a head row. H4′'s W2 clause is read off that class.

And the **real-data acceptance test**, `tests/test_acceptance_e12p.py`: the
new parser over the committed transcripts must read exactly what §4.4/§4.5
found by hand — S2 found, `elsewhere_not_gated` five rows, W2 zero HITs on
completion rows and two on head rows — and must pass exactly what held (S1,
W1, W3, H6's two sightings). Each of those assertions is mutation-tested
against the parser line it pins before it counts. A dry run over the
transcript fixtures exercises every SHAPE the endpoints meet (a CALL row, a
one-space RETURN, a head row and a completion row on one line), which is the
lesson rung 4's rehearsal taught.

### 3.3 The three readings, pre-registered

Locked in the new record's §1 before `e12p_report.py` exists; each read ONCE;
a reading that does not match is a **STOP** recorded as a finding, no re-roll,
no second parser.

| Endpoint | Reads | Holds when |
|---|---|---|
| **H2′** | `node resolve.mjs` output in the record; `meta.functions_focused`, `meta.focus_matched` off the committed trace; a HAND count under the container rule written at T0 (the three named functions plus every function-like nested in them, read from `diceQueue.ts` at VTT `0091e97`) | hand count = resolver sites = `functions_focused` = **6**; `focus_matched` = **5**, and the one qualname two sites share is `buildDiceQueueEntry.<anonymous>`; the suite half exactly as §4.2 quotes it |
| **H4′** | the three committed `watch` transcripts | W1/W2/W3 all `SATISFIED`/exit 0; W2's HITs = **52**, of which **0** on a row whose `unbound` names `count` (the `while`'s completion rows — §1.2's clause as written) and **2** at line 72, both head rows (`m=[ … ]`, no `unbound`, `count=1`); W3's HITs = **15**, all at line 72 on rows carrying `m=null` and `unbound:count,sides` |
| **H5′** | the two committed `flow --value` transcripts + the trace's `code` table | S1 found (**9** sightings at `:74` in `parseDiceGroups`); S2 found (event `e10`, CALL, qualname `parseDiceGroups`, code-object line **68**); `elsewhere_not_gated` = **5** (1 + 4 RETURN rows); the transcripts' own `sightings:` totals **10** and **5** quoted beside; `unpredicted` = **0** |

The numbers are rung 4's, read once there, quoted here as the pre-registered
expectation of a parser that can see them. They are not re-measured; the
question is whether an instrument without the four defects reads them.

### 3.4 H8′ — the live confirmation

One run, last in the slice, on the lens (`/mnt/extra/sensorium-s5/vtt/frontend`,
VTT `0091e97`): the rung-1 manifest verified before and after (748 OK / 0
FAILED, else stop before start), then `sensorium ts run --focus <the three
specs> -- npx vitest run src/lib/diceQueue.test.ts` under this slice's driver
and recorder. Holds when: `node resolve.mjs` prints the same six sites;
`info` prints `focus matched: 5 … (6 functions)`; H3's nine LINE rows are
TEXT-equal to the record's §1.1 hand count (event ids may differ, the row text
may not); the suite line reads `26 passed (26)`; the marker grep and the
wrapper listing read clean. The focused file carries no return-inside-a-finally
shape (§4.6's census pins that), so this slice's transform of it must be
byte-identical to 0.3.0's: at T-last, `e6f5035`'s `transform.mjs` is run from
a temporary checkout over the same `diceQueue.ts` with the same three specs,
and the diff against this slice's output is empty. That empty diff is the
eighth clause.

### 3.5 Disposition

PASS on all four → H2, H4, H5 are closed for this recorder on this lens and
the rung-4 spec's §15 and CD get a dated line. STOP on any → the number
stands as a finding, and whether the instrument or the recorder is wrong is
the next record's question, not this one's.

## 4. The finally seal (TypeScript, blind spot 38)

### 4.1 Today

`spliceReturn` renders `return x` as `return __srt.ret(__sf,(x))`; `ret` sets
`f.open = false`, drops the frame from its stack and emits RETURN, all before
the program's own `finally` runs. Two consequences: every `line` from the
finally arrives on a closed frame and is dropped (bs 38), and a call made
inside the finally (`finally { cleanup() }`) opens under whatever frame is
now on top — attributed OUTSIDE its parent, in every tier. The same finally
reached by a `throw` is recorded in full, because `thr` runs in the wrapper's
`catch`, after it.

### 4.2 The rule

A function is **seal-deferred** when its own body — not a nested function,
arrow, method or class — contains a `ReturnStatement` whose ancestors, up to
the function, include a `TryStatement` with a `finallyBlock`, and the return
sits inside that try's `tryBlock` or `catchClause`. (A return inside the
`finallyBlock` itself is a return that no further finally of that try guards;
it counts only if an OUTER try-with-finally encloses it — same test, one
level up.) The detector lives in `escape.mjs` beside `finallyCompletes`,
which already walks these shapes; `sitesOf` reports it per site as
`deferred: true`, so `resolve.mjs` can print it and the census (§4.6) can
count it.

For a seal-deferred function only, three things change:

1. **`return x`** splices to `return __srt.pend(__sf,(x))`; a bare `return`
   to `return __srt.pend(__sf,undefined)`; the body's fallthrough close to
   `;__srt.pend(__sf,undefined)`.
2. **The wrapper** gains `finally{__srt.seal(__sf)}` after its `catch`.
3. **The runtime**: `pend(f, v)` stores `f.pending = dbg(v)` and returns `v`
   with the frame OPEN; `seal(f)` — on an open frame — closes it, drops it,
   and emits RETURN with `f.pending` (or `dbg(undefined)` if nothing pended);
   on a frame `thr` already closed it does nothing. `line` is unchanged: the
   frame is open through the finally, so its rows are minted. `call` is
   unchanged: a call inside the finally opens under `__sf`, where it belongs.

The order of the wrapper's clauses is what makes the semantics fall out
without a special case, and §4.3 is the table a reviewer should check it
against.

### 4.3 Semantics

| Shape | Rows | Why |
|---|---|---|
| `try { return 1 } finally { cleanup = 1 }` | LINE(cleanup=1) then RETURN 1 | pend keeps the frame open; seal emits after the finally |
| `try { return 1 } finally { return 2 }` | RETURN 2 | the second pend overwrites the first; JavaScript returns 2 |
| `try { return 1 } finally { throw e }` | LINE rows of the finally, then UNWIND e | `thr` runs in the wrapper's catch and closes; seal finds it closed |
| `try { throw e } catch { return 1 } finally { … }` | HANDLED, finally's LINEs, RETURN 1 | the catch's return pends |
| `try { return await p } finally { … }` (async) | YIELD/RESUME, finally's LINEs, RETURN | `y`/resume check `f.open`, still true |
| a generator with the shape | as above, then the existing `finally{gclose}`; `gclose` yields to `seal` (one exit, §4.4) | |
| a function WITHOUT the shape | byte-identical to 0.3.0 | R2 |

The RETURN row's position — after the finally's rows — is the order
Python's `sys.monitoring` already gives (`PY_RETURN` fires after the finally
body), so `TRACE-FORMAT.md`'s TypeScript clause gains the sentence and
Python's needs none. Rust has no finally.

### 4.4 The generator seam

A generator wrapper today ends `finally{__srt.gclose(__sf)}` (the `.return(v)`
close). A seal-deferred generator must not emit two exits: `seal` runs first
(inner finally), closes the frame, and `gclose` then meets a closed frame and
is a no-op — which is the existing contract ("a frame `ret` or `thr` has
already closed is left exactly as they left it"). No new rule; a test pins
the single RETURN.

### 4.5 What flips, on purpose

- `typescript/test/rt.focus.test.mjs`'s *a statement in a finally after the
  return mints no row* becomes *…mints its row, and the RETURN follows it*:
  the same two bodies, `f`'s finally LINE now present with `cleanup=1`, and
  `RETURN`'s index in `recs` greater than that LINE's. The assertion is
  inverted in the same commit as the runtime change, never before.
- Blind spot 38 is struck with the date and the pointer; `HONESTY.md` §
  *frames* gains one line (a return's RETURN row follows the finally it
  passes through); `TYPESCRIPT-KEYS.md` § *Under a focus* gains the sentence.
- A corpus case, `corpus/typescript/focus_finally_return`, committed at T0
  with its questions written against the FIXED behaviour: a `watch --at f
  --expr cleanup == true` that is `SATISFIED`, a `frame` whose LINE for the
  finally's statement precedes its RETURN, and a `tree` where a `cleanup()`
  called from the finally is `f`'s child. Under 0.3.0 those fail; the RED run
  is recorded in the ledger before the runtime changes (the strict-xfail
  lesson, in the corpus harness's own terms: the case is listed in the plan
  as red-until-task-N).

### 4.6 The census, locked before the transform changes

`typescript/acceptance/census_deferred.mjs` walks a root with `sitesOf` and
prints every seal-deferred site. At T0 it runs over `typescript/probes`,
`corpus/typescript` and the lens's `src/lib/diceQueue.ts`, and the record's
§1 pins the three lists (predicted: the probes carry whatever fixtures rung
1–4 wrote with the shape, counted by hand at T0; the corpus carries exactly
`focus_finally_return`'s functions and `finally_return`'s; the lens file
carries **0**). E13's second clause is that the transform golden diff between
0.3.0 and 0.4.0 over those roots changes exactly the wrappers the census
named and no other byte.

## 5. The Rust `unbound`

### 5.1 The gap

`sites_for` folds `deltas` forward and pops `unbound`. Python emits `unbound`
for `del` and the end of `except … as e`; TypeScript on every block-like
statement's row; Rust emits none, so `{ let x = 1; }` leaves `x` in the fold
at every later site of the frame, and a `watch` predicate over `x` is
evaluated where `x` is dead.

### 5.2 The rule (transform)

A **block-like statement** is `is_block_like`'s list: `Expr::Block`,
`Unsafe`, `If`, `Match`, `Loop`, `While`, `ForLoop`, `TryBlock`, `Async`,
`Const` — in statement position, with or without a `;`, minted today at
`block_like_end`. Its row's `unbound` is, in source order, each name once:

- every `Stmt::Local` pattern's `binding_names` in each of its DIRECT blocks
  (an `if`'s then and else, a `match` arm's block, a loop body, the plain
  block itself) — not the blocks of a nested block-like statement, which
  unbinds its own;
- its own head pattern's names: `for <pat> in`, `if let <pat>`, `while let
  <pat>`, and each `match` arm's pattern (the names the arm-entry row bound);
- a `let`-chain's names (`let_bindings`, the same helper the entry row uses).

Not unbound: names bound by a nested closure or `async` block (the walk stops
there today and still does); an `Async` or `Const` block-like statement
unbinds nothing at all, since no probe inside it ever bound a name (a row
that said a name went out of scope where none came in would be a row that
invents); a `let` whose statement `is_conditionally_compiled`
(no delta, no unbind — the symmetric rule); a name that
`is_binding_name` rejects. A `let`-`else` binds like a `let`. A name bound in
BOTH a head pattern and an inner `let` is listed once.

The fragment for a block-like statement with names to unbind is

```
::sensorium_rt::line_unbinding(&crate::__SENSORIUM_UNIT, <site>, || [<deltas>], &[<"a">, <"b">]);
```

and for one with none, `line(...)` exactly as today (R5). `statement_deltas`
is unchanged; `lines/facts.rs` gains `unbound_of(expr) -> Vec<String>`
beside it, and `lines.rs`'s `statement` passes both to `emit`.

### 5.3 The wire (rt 0.5.0)

`line_unbinding<const N: usize>(unit, site, deltas, unbound: &'static [&'static str])`
writes the deltas exactly as `write_line_payload` does, then one block per
unbound name: `u16 name_len, name, u8 tag = 3, u8 0`. `n` counts both. The
2 KiB budget applies to the whole; a name that does not fit sets `bit0` and
stops, the same as a delta (a row that is a prefix of what the statement
did). `line` is untouched and never writes tag 3.

### 5.4 The converter (driver 0.6.0)

`parse_line_payload` reads tag 3 as a name with no value; `LinePayload` gains
`unbound: Vec<String>` in record order. `frames.rs`'s `KIND_LINE` arm writes
`"unbound": [...]` on the row when the vector is non-empty, beside `deltas`
and `unread`. A name that appears as BOTH a delta and an unbound in one
record is a refusal naming the record and the name (a statement cannot write
what it unbinds), extending the duplicate-name check. Vector
`v40-rust-line-unbound.json` pins the row and its `frame`/`watch` rendering.

### 5.5 The reader, and the shadow reading

Nothing changes in `watch_cmd.sites_for`: it already pops `unbound` after
binding `deltas`. What both recorders now DO, and neither said, is R4: a
block that shadows an outer name pops the name, so `watch` reports it
*not captured* at sites after the block until its next write. Blind spot
**39** (TypeScript) and a new Rust blind-spot entry state it, each with a
falsifier (`focus_block_let`'s shadowed `x`; a TS unit test in
`bindings.test.mjs`). This is the honest reading — absence, never a stale
value — and the cost is named: a reader watching a shadowed outer binding
must ask at a site before the block or after its next write.

### 5.6 The licence

No clause of the refocus licence turns on the rt hash: the README says the
recorder's own `--extern sensorium_rt=…` fragment inside `RUSTDOCFLAGS` is
REMOVED from the env compare and named on the line, and `driver_version` is
read from both sides and reported (the 2026-09-08 button-up's item 3). LINE
is not a causal kind (`CAUSAL_KINDS` excludes it), so an original recorded
under driver 0.5.3 and re-run one flag deeper under 0.6.0 compares the same
fingerprints and can read MATCH; what the pair reports is the two
`driver_version`s, and the deeper trace's rows carry `unbound` where the
original's could not. No corpus `refocus_*` case crosses the boundary, since
each records both runs under one driver; the cross-version reading is stated
in `HONESTY-REFOCUS.md` as a sentence, not measured.

### 5.7 The corpus case and the goldens

`corpus/rust/focus_block_let`: a focused function with a plain block `let`,
an `if let`, a `for` pattern, a `match` with a binding arm, and a block that
shadows an outer `let`. Its questions pin: `frame` shows `unbound: x` on the
block's row; `watch --expr x == 2` after the block is *not captured* there
(the `unavailable` tally names `x`), `SATISFIED` inside it; the shadowed case
per §5.5. `tests/unbound.rs` (R8) holds the transform goldens for each
head-pattern shape and the edges: a `let` inside a nested closure (not
unbound), a `cfg`'d `let` (not unbound), a name in both head and body (once),
a block with nothing to unbind (fragment unchanged: `line(...)`).

## 6. The closable list

### 6.1 Blind spot 36 — the inspect tail

`js_inspect._MORE` becomes `INSPECT_MORE`, public, one definition.
`ts/build.py`'s capture walk counts a `str` capture whose text matches it
(outside the closing quote — `_body`'s rule) as truncated, beside `trunc`,
`type_trunc` and `name_trunc`. `info`'s `truncated values:` then counts it.
`corpus/typescript/focus_long_string` records a 100-character and a
101-character string under a focus: the 100 is spelled whole, the 101
carries the tail, `truncated values: 1`, and `flow --value` of the full
101-character literal sights **0** — the capture is a prefix, read as
TRUNCATED and never compared as a value (plan P7) — which measures the
100/101 boundary the deferred minor said was asserted and not measured.

### 6.2 Blind spot 37 — the E6-TS table

Rung 3's own precedent is the procedure: a new TypeScript corpus case that
asks an `exceptions` question adds its row to `e6ts.PRE_REGISTERED` (and to
`PRE_REGISTERED_REASON_LINE` when it pins a reason line) **in a commit before
the commit that records its answer**, with the hand adjudication in the commit
message. This slice does it for `focus_catch_binding` (row: **0** SWALLOWED,
reason line `None`; hand read: one HANDLED at the catch clause, nothing
swallowed) and switches its pin from `grep --kind HANDLED` to the
`exceptions` question the case wanted. The procedure goes into `e6ts.py`'s
docstring and `docs/corpus.md`'s TypeScript section; blind spot 37 is struck
with the pointer. `focus_finally_return` and `focus_long_string` ask no
`exceptions` question and need no row.

### 6.3 The prose tests

`tests/test_ts_honesty_prose.py`: every numbered entry of
`typescript/HONESTY-BLIND-SPOTS.md` names a *Falsifier:* file and test title,
the file exists, and the title appears in it verbatim; every path
`typescript/HONESTY-COST.md` cites as evidence exists. For
`rust/HONESTY-BLIND-SPOTS.md`, whose entries cite tests as *Falsified by*
paths or as "no case in the tree pins it", every test path an entry names
exists (31 entries today; the test enumerates them, so an entry that cites
nothing is listed, not skipped). A prose test
that reads structure is the check that a promise moved out of `HONESTY.md`
is still a promise a test reads.

### 6.4 The minors

One task, by file, each as CD's minors section states it (inventory #8–#12).
The two that are more than a line: **`positions.mjs`** takes `lineOf` and
`terminatorFor` out of `transform.mjs`, `probe.mjs` imports it, and the
cycle is gone (a test asserts the import graph is acyclic over `src/`);
**`resolve.survey`** wraps `sitesOf` in a `try`, counts the throw as
unparsable and names the file on stderr, and a test feeds it a file the
consumer's TypeScript throws on. `Resolution.wall` is persisted into the
manifest so an instrument can time the resolver without timing itself.

### 6.5 The rung-3 leftovers

#15 is the dated parenthesis spec §4.3 asked for. The five D items get their
NOTE in this slice's CD section, each naming what would close it and why it
is not closed here.

## 7. Seams

- `tests/test_corpus.py` → the loader/validation half stays; the harness
  half (from `CARGO_QUESTION` down: cargo/vitest specs, `sub_run_ids`, the
  expectation checkers, `run_case`, `main`, `test_corpus_passes`) moves to
  `tests/test_corpus_harness.py`. A pure move, verified by the test-name set
  being identical before and after.
- `typescript/src/rt.mjs` → before the seal lands, the capture side
  (`captures`, `dbg`, `exc`, the object-serial table) moves to
  `typescript/src/capture.mjs`; `rt.mjs` imports it. None of the three is
  exported today (verified at design time: `rt.mjs`'s export set is `flush`,
  `file`, `task`, `suite`, `nameProvider`, `call`, `line`, `ret`, `gclose`,
  `thr`, `y`, `r`, `raise`, `handled`, `mark`, `handledFinally`, `catchCb`,
  `fileStart`, `seen`), so the seam changes no export and the probes and
  `setup.mjs`, which import from `rt.mjs`, see the same module.
- `CHANGELOG.md` → the 0.9.x entries are cut to the NEW
  `CHANGELOG-ARCHIVE-2.md` (preamble in the archive's voice, the numbering
  rule stated, a pointer from `CHANGELOG-ARCHIVE.md`'s head and from
  `CHANGELOG.md`'s), before the 0.13.0 entry is appended (R7). The entry is
  drafted and measured first.
- `README.md` at 799: this slice's README changes are the version line and
  one sentence on `unbound`; both land net-zero by trimming the same section,
  or the section takes a seam. The plan says which before the edit.
- `rust/sensorium-transform/tests/unbound.rs` (R8).
- `docs/CARRIED-DEBT.md` at 538: this section is drafted and measured before
  it is appended; the oldest section is cut to volume 9 if it would cross.

## 8. Acceptance — pre-registered

Every endpoint below is written into the record's §1 and committed BEFORE the
instrument or the code it measures exists (T0), then read ONCE. A clause
that does not hold is a **STOP** recorded as a finding; nothing is re-run,
re-rolled or re-parsed. Instrument defects found after a number are findings,
and the number stands.

| Endpoint | Question | Clauses (all must hold) |
|---|---|---|
| **E12′ H2′/H4′/H5′** | does an instrument without the four defects read what rung 4's post-mortem read by hand? | §3.3's table, plus the hash preflight §3.1 |
| **H8′** | does this slice's recorder still produce the same rows on the same lens? | §3.4's eight clauses |
| **E13** | is a finally after a return recorded, and only where the shape exists? | `focus_finally_return` green with its RED run in the ledger; the census lists (§4.6) match the golden diff exactly; the lens file's list is empty; `HONESTY-COST.md`'s cited numbers are untouched (the seam and the seal change no unfocused wrapper) |
| **E14** | does Rust's row say what its block unbound, and does the fold honour it? | `focus_block_let` green; `v40` round-trips; the tag-3 refusal cases in `spool/tests.rs`; every existing Rust corpus case equal (no block-free fragment moved); `refocus_*` cases equal |
| **E6-TS′** | does the re-registered table hold? | `e6tsppp.py` over every TS case with an `exceptions` question: every row matches, `focus_catch_binding` included; the swallow set non-empty |
| **fences** | did anything else move? | `python corpus/run_corpus.py --require-driver` every case equal (all three languages); `.venv/bin/python -m pytest -q`; `cargo test --workspace`; `npm --prefix typescript test`; the probes; `tests/test_ceiling.py`; the E7 needle on TS output; `e_fences.py` legacy and branch — the legacy fence's `FENCED` set covers `rust/` whole, `exceptions.py`, `exceptions_rust.py` and the four `test_exceptions*` files; this slice edits `rust/` by design (§5) and NOTHING else in that set, so the record's §1 names `rust/` as the one fenced path expected to move and the fence's report must list only paths under it |

Baselines (suite counts, corpus case count, the ceiling census, `df`) are
taken at T0 and written into the record's §2, the ambient pins.

## 9. Not in this slice

- **The nested-arrow spelling and identity for anonymous function-likes** (CD
  §"gaps" 1–2). A spelling meaning *this function and not what it nests* is a
  design question about what `--focus` promises, and a qualname that is not
  an identity is the same question from the other side. Both are the C
  conversation's; refocus (slice 2) inherits them as stated.
- **Blind spots 28–31, 34, 35.** Each was deferred by a ruling whose reason
  still holds (a snapshot-and-diff's cost; `this` as a pseudo-argument on
  demand; a row that does not invent a write; the erased binders; a value one
  command can read and the other cannot spell). Design-level: C.
- **The browser runtime** (S5 rung 5): after refocus, its own brainstorm.
- **A `--focus` cache, `--window`, probes inside `eval`**: rung 4's
  non-goals, unchanged.

## 10. Process

Worktree `/mnt/extra/sensorium-rung2/s5-rung4-debts` on `feat/s5-rung4-debts`
off `e6f5035`; venv `[dev]` + the three `node_modules`; ledger
`.superpowers/sdd/2026-09-1X-sensorium-s5-rung4-debts/`. Subagent-driven:
one implementer per task, reviews between, rulings appended to the ledger and
to §11 here. TDD with mutation testing on every test that pins a number or a
row (the pyc rule: purge `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`). T0 =
the pre-registration commit (record §1 + §2, the census lists, the E6-TS row,
the corpus cases RED); the last task = H8′ and the record's §3–§5, then the
CD section, the CHANGELOG cut and entry, versions. Final review, PR; merge is
Brice's. After merge: archive the ledger, remove the worktree, reinstall the
tool and `cargo-sensorium`.

## 11. Rulings from Brice (this brainstorm, 2026-09-12)

- Scope: debts first, then refocus for TypeScript; the C conversation on hold
  until everything else is done and tested properly.
- The Rust fold is funded in this slice, its own task, despite the wire cost.
- E12′ re-adjudicates the committed data (the recommended form), not a full
  re-run.

## 12. Amendments

Appended at execution, dated, each naming the section it amends. None yet.
