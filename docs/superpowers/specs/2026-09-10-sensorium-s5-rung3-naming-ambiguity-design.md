# S5 rung 3 — naming the ambiguity: the untraced catcher, the window, the key

*Design, 2026-09-10. Brainstormed with Brice; five sections approved in
turn (direction, naming stance, measurement, corpus and instruments, order).
Reader-side only: no runtime, transform or wire change.*

## 0. Provenance

Rung 2 (`docs/superpowers/specs/2026-09-10-sensorium-s5-rung2-throw-flow-design.md`,
PR #30, main `04345ee`) shipped DONE with its acceptance record
`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md`. Its §5 named
four gaps and the final review a neighbour; `docs/CARRIED-DEBT.md`'s rung-2
section carries them. This rung closes the ones a reader can close without a
new record on the wire:

- **Gap 4.** Of the 30 AMBIGUOUS shapes on the lens, 17 read §3.3 rule 5's
  catch-all, *no rule of this recorder reaches a verdict here*. The one that
  was diagnosed is a RAISE whose frame closed by unwind, whose traced parent
  closed by return, and for whose serial no HANDLED exists anywhere: untraced
  code sitting inside a traced frame caught it — vitest's `toThrow` and
  `rejects`, a React error boundary. The brainstorm spot-checked two more of
  the 17 against the lens source (`src/lib/sheets/formula.test.ts:37`,
  `src/components/PanelErrorBoundary.test.tsx:10-28`) and found the same
  footprint.
- **Gap 4's neighbour.** `catch (e) { console.error(e); throw e }` whose
  rethrow unwinds the test root also prints the catch-all, because rule 4's
  absorbing conjunct reads every handler of the serial and the earlier
  window's handler sits in a frame closed by the rethrow itself.
- **Gap 1.** The shape key masks event and frame ids out of the verdict's
  prose with a regex that exempts `f16`/`f32`/`f64`/`f128` (Rust type names
  a panic message can carry). On a TypeScript trace those are frame ids, so
  one clause at `src/hooks/useAiAssist.ts:56` printed as three shapes: 30
  shapes are 28 places.
- **Gaps 2 and 3, and the final review's minor.** Three reused acceptance
  instruments measured `main`'s binary until fixed; the lens label was
  stamped by six instruments at measurement time and by the assembler for the
  rest; E7″'s needle list matched `Err` inside `Error`; the callback-side
  bare-rethrow exclusion has no probe marker.

The lens is unchanged and so is the record of it: the rung-2 invocation
`20260910-150809-cbc8de` in `/mnt/extra/sensorium-s5/store-rung2ts` (by
label, never by path in a committed file) is this rung's whole lens
measurement. Nothing is recorded.

## 1. Goal, scope, non-goals

**Goal.** A reader that names the shape behind more than half of a real
suite's ambiguity, without minting a verdict from it; a rethrow to the
harness that reads as what it is; a shape key that counts places; acceptance
instruments that cannot measure the wrong binary again.

**In scope.** `src/sensorium/query/exceptions_typescript.py` (a new reason
before rule 5's catch-all; rule 4's absorbing conjunct scoped to the unit's
window; a tally by reason), `exceptions_group.py`'s TypeScript key,
`exceptions_invocation.py`'s summed tally line, four corpus cases and one
re-pin, one probe marker, the acceptance scripts' binary and label
discipline, vector v34, docs and versions.

**Non-goals.** No record for an untraced catcher — this runtime cannot see
one, and marking one would be a wire change. No sixth disposition word:
Python's five words stay the contract (§2.1). No change to the Rust key or to
any Rust or Python output. No new lens recording (§5). No `object_identity`
on TypeScript traces, no `refocus` for TypeScript: those are parity work,
not this rung's.

## 2. The rules module

### 2.1 The named reason

Between rule 4 and rule 5's catch-all a reason fires when all four hold:

1. the unit's window holds no HANDLED row for the serial (`unit.handled` is
   empty), and the unit has no escaping handler anywhere;
2. the outermost frame the serial unwound (`Index.left_frame`) exists and
   has a traced parent (`parent_id is not None`) — rule 4 has already
   declined on exactly this;
3. the parent is not the origin's own frame;
4. the serial is not an unhandled rejection (rule 1 would have taken it).

The line printed stays AMBIGUOUS and names the footprint. Three variants on
the parent's fate:

```
AMBIGUOUS -- caught by untraced code inside <parent qualname> (<parent file>): f<child> unwound, its caller f<parent> returned; not followed
AMBIGUOUS -- caught by untraced code inside <parent qualname> (<parent file>): f<child> unwound, its caller f<parent> had not closed at the end of the recording; not followed
AMBIGUOUS -- caught by untraced code inside <parent qualname> (<parent file>): f<child> unwound, its caller f<parent> later unwound with <exc>: a translation by untraced code, or a later failure, indistinguishable
```

`<child>` is `left_frame`'s id, `<parent>` its `parent_id`; `<parent file>`
is the parent code object's file as the rung-2 renderer already prints it
(basename). A parent that unwound with the same serial cannot occur: it
would itself be `left_frame`. A parent whose `closed_by` is `unwind` with
`unwind_exc` absent prints the third variant with `<exc>` as the existing
`fmt_exc` renders a missing value.

What the reason claims and what it does not: it claims the serial left
`f<child>` and never reached a traced handler, and that `f<parent>` went on.
It does not claim what the untraced code did with the failure — asserted on
it, rendered it, discarded it — which is why the word stays AMBIGUOUS
(Brice's ruling, §10).

### 2.2 The window-scoped absorbing conjunct

Rule 4's absorbing conjunct reads only the handlers in the unit's own window:
`_still_open_absorber` walks `unit.handled` filtered to the absorbing set,
not `unit.absorbing`. An earlier window's absorbing handler whose frame was
closed by this very rethrow is the rethrow's predecessor, and the origin's
block already says `re-raised → <word>` about it. So `catch (e) {
console.error(e); throw e }` unwinding the test root reads, for the origin,
`RE-RAISED -- raised again at e<id> (<site>) → propagated` and, for the
rethrow, `PROPAGATED -- to the harness: test "<name>" failed`.

Rule 3's escaping conjunct stays trace-global, exactly as rung 2 wrote it:
an escaped object can be rethrown from anywhere, and a later SWALLOWED for
it would be the false accusation the escape rule exists to prevent. Rule 4's
escaping decline (spec §14 R15 of rung 2) stays trace-global for the same
reason.

The suspended `.catch(async …)` handler that motivated the conjunct (rung 2,
Task 4's fix round) sits in the unit's own window and still declines rule 4.

### 2.3 The tally by reason

The `dispositions:` line is byte-identical to rung 2's. When `ambiguous` is
non-zero, one more line follows it, indented like the tally:

```
ambiguous by reason: escaped 13, untraced catcher 35, suspended 2, translated 1, primitive 1, orphan 1, unnamed 1
```

Keys, in this fixed order, zero entries omitted: `escaped` (§3.3 rule 5's
escaped-handler reason), `untraced catcher` (§2.1), `suspended` (the
handler's frame open at the end), `translated` (the handler's frame later
unwound with another serial), `primitive` (a primitive with no identity
across a rethrow), `orphan` (a HANDLED with an escaping `how` and no RAISE),
`incomplete` (the recording is INCOMPLETE and the rule declined on it),
`unnamed` (rule 5's catch-all). Every reason the module can print has
exactly one key; a new reason without a key is a test failure
(`tests/test_exceptions_typescript.py` walks the module's reason table).
`unnamed` is the number this rung is measured on (§5, E6-TS‴).

The invocation mode sums the line over members and prints it once, after its
summed `dispositions:` line, under the same rule.

### 2.4 What this cannot mint

No verdict word changes. The parent's return is evidence for a reason and
for nothing else; `_swallowed` is untouched, so E6-TS′'s thirty rows are
unchanged by construction, and §5 requires them byte-identical anyway.

## 3. The shape key

### 3.1 Components, not prose

The TypeScript renderer's shape key becomes a tuple of the classifier's own
parts: `(disposition, reason kind, site, origin site)`, where `site` is the
one the rung-2 rules already choose per disposition — the sink's HANDLED for
swallowed, the handler's for the escaped and opaque reasons, the parent code
object for the untraced-catcher reason (§3.2), the origin RAISE otherwise —
and `origin site` is the origin RAISE's code object and line. No masking, no
exemption. The `Renderer` gains one field, `key`, a callable from a unit and
its disposition to the tuple; `RUST.key` is the masked-prose key exactly as
today, so Rust output is byte-identical and the nineteen fenced Rust tests
stay unchanged.

### 3.2 The new reason's site

For the untraced-catcher reason the site is the parent's code object
(qualname and file). The four `Bomb` raises under one error boundary are one
shape; the formula errors thrown under `toThrow` inside one test file group
by the test frame's function. `origins: N distinct` and `messages: N
distinct` keep flagging what the key ignores, as rung 2's grouper does.

### 3.3 What the re-read must show

On the kept invocation the thirty SWALLOWED shapes become twenty-eight
places — S1, S11 and S17 of the rung-2 adjudication table are one clause —
and nothing else merges or splits: every other rung-2 SWALLOWED shape's sink
site is unique in that table. That is the E-places prediction (§5).

## 4. Corpus, probe, instruments

### 4.1 Four corpus cases

Under `corpus/typescript/`, one shape each, in the rung-2 style: a seeded
bug, a `questions.yaml` whose `exceptions` question pins the verdict line,
the reason line and both tally lines whole, and a `why_logs_fail` naming
`console.log`, `DEBUG` and a stack trace.

| case | shape | pinned reading |
|---|---|---|
| `untraced_catcher` | `expect(() => parse('x')).toThrow(FormulaError)` inside a test; `parse` throws | AMBIGUOUS, untraced catcher inside the test function, `its caller f<n> returned`; `ambiguous by reason: untraced catcher 1` |
| `untraced_catcher_rejection` | `await expect(fetchThing()).rejects.toThrow()`; `fetchThing` is `async` and throws | the same reason on a rejection-kind exc |
| `untraced_catcher_later_failure` | the `toThrow` shape, then a different `throw` out of the same test frame | the third variant, `later unwound with Error('…')`; the second throw PROPAGATED to the harness; red suite |
| `logged_rethrow_to_harness` | `catch (e) { console.error(e); throw e }` unwinding the test root | origin `RE-RAISED … → propagated` with its hops line, rethrow `PROPAGATED -- to the harness: test "…" failed`; `dispositions: re-raised 1, propagated 1`; red suite |

The existing `translated` case's wrapper raise (thrown inside `expect(() =>
…).toThrow(Wrapped)`) moves from the catch-all to the untraced-catcher
reason; its questions are re-pinned with that reason stated in the commit and
the corpus README. Every other rung-2 case is expected to print the same
lines; any other movement is named in the record with its cause. The
rung-2 E6-TS per-case SWALLOWED table is reused unchanged as the corpus fence
(§5).

### 4.2 The probe marker

`typescript/probes/src/escape.probe.test.ts` gains one `// ESCAPE` marker,
`callback_bare_rethrow`, for `.catch((e) => { throw e })`, expecting
`catch_callback`; `check.mjs`'s `escape:how` count rises by one. The totals
E8‴ pre-registers are read from the files at T0 (marker count per file,
check count), not from a run.

### 4.3 Instruments from the branch

Every script under `typescript/acceptance/` that invokes `sensorium`
resolves it as `<repo root>/.venv/bin/sensorium` and refuses, with the
resolved path printed, when that file is absent or when `realpath` of the
resolved binary is outside `<repo root>`. `lens.py` stamps the lens label on
every cell at assembly time and no instrument writes a `lens` field of its
own; a cell that arrives with one is a refusal. The E7 needle instrument
takes a matching rule per needle: whole-word (`\b…\b`) for `Err` and `Rust
disposition`, substring for the rest; the rule is printed in the transcript
header. `tests/test_acceptance_scripts.py` walks the scripts and asserts the
resolution rule and the absence of a `lens` writer outside `lens.py`
(E-branch, §5).

## 5. Pre-registered endpoints

Locked verbatim into the record's §1 at T0, byte-locked by
`tests/test_acceptance_s5_rung3_lock.py`, before any rung-3 code exists.

**The lens.** The rung-2 invocation, read from the store by label
(`LENS.txt`); its trace set is enumerated at T0 with a content hash per
trace, and the re-read at T5 refuses if any hash differs. Nothing is
recorded in this rung.

**The hand-read table (T0).** For each of the seventeen catch-all blocks in
`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt`
(the invocation transcript; 30 `SWALLOWED --` lines, 17 `no rule of this
recorder` lines, `dispositions: swallowed 261, ambiguous 53`): the origin as
printed, the lens source opened at the raise site and at every traced caller
up to the test, the untraced catcher the source shows (vitest `toThrow` /
`rejects`, an error boundary, a library's own `try`), the predicted reason
kind (`untraced catcher` with its variant, or `unnamed` when the source
shows no untraced catcher between the raise and a traced frame that went
on), and the predicted parent qualname. A shape whose source the reader
cannot decide is predicted `unnamed`. The table is the prediction; it is
locked before §2 is written.

| endpoint | question | measure | rule |
|---|---|---|---|
| E6-TS‴ | Does the reader name the seventeen truthfully? | one re-read of the invocation with the rung-3 reader; every printed untraced-catcher line compared to the hand-read table's row for that origin | **0 false names** — a printed name whose parent is not the table's, or printed for an origin the table predicted `unnamed`, is false → STOP. Reported: `unnamed` after, beside the table's predicted count; the count of table rows the reader left unnamed (a miss is reported, not a stop) |
| E6-TS′-fence | Did the new reader move a verdict? | every `SWALLOWED --` line, every `RE-RAISED`/`PROPAGATED`/`UNCAUGHT` line and the `dispositions:` line of the re-read, diffed against the rung-2 transcript above | byte-identical (ids included, the store is the same) → else STOP |
| E-places | Is the key the classifier's? | the SWALLOWED shape count on the re-read and the set of sink sites | exactly **28**, the 28 distinct sink sites of the rung-2 adjudication table, S1/S11/S17 one block with `[×3 …]` → else STOP |
| E6-TS | Does the corpus still pin it? | the corpus run with the driver; the per-case SWALLOWED set; the four new cases' and `translated`'s pinned lines | set equality with the rung-2 locked table; every new pin green → else STOP |
| E8‴ | Do the probes agree? | `npm run probe`; marker and check totals against the T0 file read | 0 failures, totals equal → else STOP |
| E7‴ | Does the reader speak this recorder's words? | the re-read transcript under the §4.3 matching rule, needles `oid`, `chain`, `Err`, `asyncio`, `python ?`, `cargo`, `coroutine`, `Rust disposition`, `Python's own`; vectors v30–v34 | 0 needles; vectors green → else STOP |
| E-legacy | Is the fence intact? | `tests/test_exceptions_rust*.py`, `test_exceptions_invocation.py`, `test_exceptions_python*.py` and the Rust grouper's fenced output; `git diff` of `exceptions_rust.py`, `exceptions.py`, `rust/` | byte-unchanged, tests green → else STOP |
| E-branch | Do the instruments run the branch? | `tests/test_acceptance_scripts.py` | green → else STOP |

**Stop rules** as rung 2's: no endpoint is re-run after its number is read;
a re-read whose trace-set hash differs from T0's is dropped and named; the
shipping word is **DONE** or **DONE-WITH-STOP** and nothing else. An
instrument defect found before a number is read is fixed and recorded in the
record's §2.3 with its commit; found after, it is a finding.

## 6. Testing story

- **Rules.** `tests/test_exceptions_typescript.py` gains the untraced-catcher
  reason on hand-built traces (each variant; the origin's-own-frame
  exclusion; a rejection kind), the window-scoped conjunct (the neighbour →
  PROPAGATED; the suspended `.catch(async …)` still declines), and the
  reason-table walk (every reason has a key). The T4-era hand-built traces
  use `how` words the transform actually emits (rung 2's final review, check
  B).
- **Key.** `tests/test_exceptions_typescript_grouping.py` (new, under the
  ceiling): three sinks at one site in frames 32, 128 and 174 → one block;
  two different clauses with equal prose → two blocks; the untraced-catcher
  site is the parent; the Rust key test file is untouched.
- **Vectors.** `v34-exceptions-typescript-untraced-catcher` (one trace, the
  reason line and the reason tally); v30–v33 re-pinned only where a reason
  line moved, with the reason in the commit.
- **Corpus.** The four cases; `corpus/run_corpus.py --only-dir typescript
  --require-driver`.
- **Instruments.** `tests/test_acceptance_scripts.py`.
- **Mutation.** The window-scoping predicate and the parent-fate switch each
  get a mutant run (`PYTHONDONTWRITEBYTECODE=1`, `__pycache__` purged,
  `setsid` + kill by process group) whose failing tests are named in the
  task report.

## 7. Order of work

Subagent-driven in one worktree under `/mnt/extra/sensorium-rung2/`; the
store is read, never written.

0. **T0** the record: spec §5 verbatim as §1; the hand-read table; the
   trace-set hash list; the E8‴ totals from the files; the needle rule; the
   lock test; a census of which acceptance scripts invoke `sensorium` and
   how (E-branch's denominator).
1. **T1** the rules (§2) with tests and v34.
2. **T2** the TypeScript key (§3), the grouping tests, Rust untouched.
3. **T3** the four corpus cases, the `translated` re-pin, the probe marker.
4. **T4** the instruments (§4.3) and `tests/test_acceptance_scripts.py`.
5. **T5** measurement, fence first: E-legacy, E6-TS, E8‴, E-branch; then
   the single re-read for E6-TS‴, E6-TS′-fence, E-places, E7‴; the record's
   §3–§5 and results JSON with provenance on every cell.
6. **T6** docs and versions: HONESTY §4 and blind spot 27, `docs/query.md`,
   the READMEs, CHANGELOG `## 0.11.0`, CARRIED-DEBT closing Gap 1–4 and the
   neighbour with dated lines, this spec's §12.
7. **T7** final review, one fix wave, PR; merge is Brice's.

## 8. Versions and ceilings

Python **0.11.0** (the reader changes what it prints on a TypeScript trace).
sensorium-ts stays **0.2.0**: no runtime, transform or wire change; the
probes are not the package. Trace format unchanged; wire 1.

Ceilings (`tests/test_ceiling.py`, 800 lines): `exceptions_typescript.py`
is 613 — the reason and the reason table fit; if not, the reasons move to
`exceptions_typescript_reasons.py`. `exceptions_group.py` gains one field.
`typescript/HONESTY.md` is 788: the §4 amendment is written net-neutral, with
the blind-spot text going to `HONESTY-BLIND-SPOTS.md` (279). CHANGELOG 756,
no cut. CARRIED-DEBT 657: append; cut the oldest section to an archive only
if the append crosses 800. README 790: at most one sentence. The new record
is exempt.

## 9. Decisions, with what each costs if wrong

| # | decision | cost if wrong |
|---|---|---|
| R1 | The untraced catcher is a **reason under AMBIGUOUS**, never a verdict | a reader who wanted "held outside the record" as a word reads a reason instead; nothing false is printed |
| R2 | Rule 4's absorbing conjunct is **window-scoped**; the escaping conjuncts stay trace-global | an absorbing handler in an earlier window that is genuinely still open when a later rethrow leaves the root would read PROPAGATED; the corpus has no such shape and the record will say whether the lens does |
| R3 | The TypeScript key is a **component tuple**; Rust keeps the masked prose | two different clauses with identical components cannot exist (site includes file and line); Rust's exemption stays Rust's |
| R4 | The untraced-catcher **site is the parent code object** | shapes under one test function merge even when their raises differ; `origins: N distinct` says so |
| R5 | The reason tally is a **second line**, printed only when ambiguous > 0 | one more line for a reader to parse; the first line is byte-identical for Python-shaped consumers |
| R6 | **No recording**: the kept invocation is the lens, its trace set hashed at T0 | if the store is lost before T5 the rung stops; the hash makes silent drift impossible |
| R7 | The **hand-read table is the prediction**, locked before §2 exists | a wrong prediction is a STOP even when the reader is right; that is the point |
| R8 | sensorium-ts stays 0.2.0 | a consumer sees a Python bump alone and looks for a recorder change that is not there; §0 says so |
| R9 | Instruments resolve **the branch's binary** and only the assembler stamps the label | a script run from outside a repo refuses; the assembler is the one place a label can be wrong |
| R10 | Needles are matched by a **stated rule**, whole-word for the two that are words | a needle that should be a substring is missed; the list is short and read |

## 10. Rulings from Brice

- Direction: rung 3 names the ambiguity (over object-identity parity,
  hygiene-only, or closing S5).
- Naming stance: a named reason under AMBIGUOUS, not a sixth word.
- Measurement: re-read the kept store only; no fresh lens run.
- §1–§5 of the brainstorm approved as presented.

## 11. The pre-registration, in one table

§5's endpoint table and its hand-read protocol, verbatim, plus the T0 pins:
the trace-set hash list, the E8‴ totals, the needle rule, the rung-2 E6-TS
per-case SWALLOWED table, and the predicted `unnamed` count after. Locked at
T0; `tests/test_acceptance_s5_rung3_lock.py`.

## 12. What changed against this design, and why

*Written at T6.*
