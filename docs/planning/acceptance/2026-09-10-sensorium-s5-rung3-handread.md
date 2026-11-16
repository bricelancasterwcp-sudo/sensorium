# S5 rung 3 — the hand read: the seventeen catch-all blocks, predicted before any rung-3 code exists

This table is the **prediction** E6-TS‴ is judged against. It was written at
Task 0, on a branch whose tip changed nothing under `src/`,
`typescript/src/`, `rust/` or `corpus/`: no `_untraced_catcher` exists yet, no
reason key exists yet, and no rung-3 reader has printed a line. The rung STOPs
on a row this table got wrong even where the reader is right, and that is the
design — a prediction written after the output is not a prediction.

**What is read.** The seventeen blocks of
`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2-e6tsp-exceptions.txt`
(sha256 `6f7f4687e09ee32b6123e909ff770e68f7fa4b8d4b360b7c92dbd9495b4e12ff`) whose
verdict line reads `AMBIGUOUS -- no rule of this recorder reaches a verdict
here` — rule 5's catch-all. They are listed in transcript order. For each, the
lens source was opened **at the raise site and at every traced caller up to
the test function**; the lens is the VTT frontend copy at `0091e97` named by
`typescript/acceptance/LENS.txt`, and every path below is lens-relative
(`src/…`). The recording read for the frame spellings is the rung-2
invocation `20260910-150809-cbc8de` in `<store>`, read-only, at the member
trace each block's `[in <run>]` bracket names; nothing was recorded.

**The rule this table applies, quoted from the design's §5** (byte-locked into
the record's §1 before this file was written):

> the origin as printed, the lens source opened at the raise site and at every
> traced caller up to the test, the untraced catcher the source shows (vitest
> `toThrow` / `rejects`, an error boundary, a library's own `try`), the
> predicted reason kind (`untraced catcher` with its variant, or `unnamed`
> when the source shows no untraced catcher between the raise and a traced
> frame that went on), and the predicted parent qualname. A shape whose source
> the reader cannot decide is predicted `unnamed`.

**How the parent is predicted.** The reason names the traced parent of the
OUTERMOST frame the serial left, and its variant is that parent's fate:
`returned` (the parent closed by return), `had not closed` (it was still open
at the end of the recording), `later unwound` (it closed by unwinding with a
different exception). The qualname is spelled as the trace holds it — the
code object's qualname, which for a vitest test body is `<anonymous>.<anonymous>`
(a `describe` arrow containing an `it`/`test` arrow), **not** the test title.
That spelling was checked against `sensorium tree <member run> --around <e…>`
for every row below, so the T5 comparison is exact.

**Cell convention.** Code text is wrapped in backticks for markdown; the
verbatim string is the cell's content with the enclosing backticks removed.
The `origin as printed` cell is the block's RAISE line exactly as the
transcript prints it, leading indentation stripped, ids included. No cell in
the table contains a pipe character — row 16's catcher names its regex's two
alternatives in words rather than quoting the alternation — so splitting a
row on `|` yields its eight cells and every one of the seventeen origins is
byte-exact against the transcript.

**What the seventeen come to.** All seventeen are test-harness shapes: a
failure thrown inside traced code, taken by an untraced catcher (vitest's
`toThrow`, vitest's `rejects`, a React error boundary, or TanStack Query's own
retryer), with the traced frame directly above the unwind going on normally.
Every parent closed by **return**; no row is predicted `had not closed` or
`later unwound`, and no row is predicted `unnamed`. Eight rows needed a second
reading; their reasons are below the table.

## The table

| # | origin as printed | raise site | traced callers to the test | untraced catcher the source shows | predicted variant | predicted parent qualname | reading |
|---|---|---|---|---|---|---|---|
| 1 | `e2305 RAISE   fetchCompendium raise Error('Failed to load compendium: 500 boom') L11` | `src/hooks/useCompendiumQuery.ts:11` | `useCompendiumQuery.queryFn`, `renderControls`, `<anonymous>.<anonymous>` | a library `try` — TanStack Query's retryer awaits the promise `queryFn` returned and stores the rejection as the query's `error`; nothing in `useCompendiumQuery.ts` catches it (`useQuery({ queryFn: () => fetchCompendium(roomId as string) })`, L23-28) | `returned` | `useCompendiumQuery.queryFn` | second reading |
| 2 | `e13 RAISE   Bomb raise Error('boom') L11` | `src/components/PanelErrorBoundary.test.tsx:11` | `<anonymous>.<anonymous>` | a React error boundary — react-dom's render-phase catch, routed to `PanelErrorBoundary.getDerivedStateFromError` / `componentDidCatch` (`src/components/PanelErrorBoundary.tsx:26,30`); neither is a `catch` clause or a `.catch(…)`, so the transform spliced no handler row | `returned` | `<anonymous>.<anonymous>` | second reading |
| 3 | `e41 RAISE   <anonymous>.<anonymous>.Flaky raise Error('boom') L42` | `src/components/PanelErrorBoundary.test.tsx:42` | `<anonymous>.<anonymous>` | the same React error boundary, this time around `Flaky` (`render(<PanelErrorBoundary label="AI Prep"><Flaky /></PanelErrorBoundary>)`, L45) | `returned` | `<anonymous>.<anonymous>` | second reading |
| 4 | `e214 RAISE   buildCastle.get raise PermissionDeniedError('permission denied: module did not declare a permission granting "castle.fog"') L99` | `src/lib/modules/castleBridge.ts:99` | `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => (castle as Record<string, any>).fog).toThrow(PermissionDeniedError)` (`src/__tests__/moduleSystem.test.ts:57`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 5 | `e310 RAISE   buildCastle.set raise TypeError('castle.chat is read-only') L103` | `src/lib/modules/castleBridge.ts:103` | `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => { (castle as Record<string, any>).chat = 'x'; }).toThrow()` (`src/__tests__/moduleSystem.test.ts:71-73`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 6 | `e371 RAISE   createHooks.emit raise Error('Hooks.emit: modules may only emit "module:m:*" events; "combat:start" is reserved or out of namespace') L80` | `src/lib/modules/hooks.ts:80` | `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => ctrl.hooks.emit('combat:start' as never, {})).toThrow()` (`src/__tests__/moduleSystem.test.ts:123`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 7 | `e408 RAISE   h raise Error('passenger node: tag "script" is not allowed') L61` | `src/lib/modules/passengerNode.ts:61` | `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => h('script' as any, {}, [])).toThrow()` (`src/__tests__/moduleSystem.test.ts:151`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 8 | `e48 RAISE   buildLevelUpDefinition.emit raise Error('level-up definitions apply via onCompletePicks, not emit') L570` | `src/lib/builder/definitions/dnd5eLevelUp.ts:570` | `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => def.emit({ picks: {} }, { players: [] })).toThrow()` (`src/lib/builder/definitions/dnd5eLevelUp.test.ts:44`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 9 | `e98 RAISE   resolveAttack raise Error('resolveAttack failed: 500') L115` | `src/lib/combat/attackRoll.ts:115` | `<anonymous>.<anonymous>` | vitest `rejects` — `await expect(resolveAttack('r1', 'atk-1', attack.name, 'tgt-1', 'normal')).rejects.toThrow()` (`src/lib/combat/attackRoll.test.ts:79`); the async frame unwinds with the rejection and the test frame returns | `returned` | `<anonymous>.<anonymous>` | second reading |
| 10 | `e140 RAISE   resolveAttack raise OutOfRangeError('Target out of reach or line of sight') L112` | `src/lib/combat/attackRoll.ts:112` | `<anonymous>.<anonymous>` | vitest `rejects` — `await expect(resolveAttack(…)).rejects.toBeInstanceOf(OutOfRangeError)` (`src/lib/combat/attackRoll.test.ts:132`) | `returned` | `<anonymous>.<anonymous>` | second reading |
| 11 | `e1387 RAISE   evalFormula.parseFactor raise FormulaError("Unknown identifier 'mystery'") L94` | `src/lib/sheets/formula.ts:94` | `evalFormula.parseTerm`, `evalFormula.parseExpr`, `evalFormula`, `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => evalFormula('mystery + 1', {})).toThrow(FormulaError)` (`src/lib/sheets/formula.test.ts:34`) | `returned` | `<anonymous>.<anonymous>` | second reading |
| 12 | `e1407 RAISE   evalFormula.parseFactor raise FormulaError("Unknown function 'sqrt'") L86` | `src/lib/sheets/formula.ts:86` | `evalFormula.parseTerm`, `evalFormula.parseExpr`, `evalFormula`, `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => evalFormula('sqrt(4)', {})).toThrow(FormulaError)` (`src/lib/sheets/formula.test.ts:37`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 13 | `e1443 RAISE   evalFormula.parseFactor raise FormulaError('Unexpected end of formula') L76` | `src/lib/sheets/formula.ts:76` | `evalFormula.parseTerm`, `evalFormula.parseExpr`, `evalFormula`, `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => evalFormula('1 +', {})).toThrow(FormulaError)` (`src/lib/sheets/formula.test.ts:40`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 14 | `e1446 RAISE   evalFormula raise FormulaError('Formula empty or too long') L42` | `src/lib/sheets/formula.ts:42` | `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => evalFormula('', {})).toThrow(FormulaError)` (`src/lib/sheets/formula.test.ts:41`) | `returned` | `<anonymous>.<anonymous>` | second reading |
| 15 | `e1666 RAISE   evalFormula.parseFactor raise FormulaError('Formula too deep') L74` | `src/lib/sheets/formula.ts:74` | `evalFormula.parseFactor` ×41 (the unary-minus recursion), `evalFormula.parseTerm`, `evalFormula.parseExpr`, `evalFormula`, `<anonymous>.<anonymous>.<anonymous>`, `<anonymous>.<anonymous>` | vitest `toThrow` — `expect(() => evalFormula('-'.repeat(60) + '1', {})).toThrow(FormulaError)` (`src/lib/sheets/formula.test.ts:48`) | `returned` | `<anonymous>.<anonymous>` | first reading |
| 16 | `e159 RAISE   loadImagePixels raise Error('Cannot read pixels from a tainted (cross-origin) canvas: https://evil/map.png — SecurityError: The canvas has been tainted by cross-origin data.') L117` | `src/lib/map/imagePixels.ts:117` | `<anonymous>.<anonymous>` | vitest `rejects.toThrow` — `await expect(loadImagePixels(…)).rejects.toThrow(…)` against a regex matching `tainted` or `cross-origin` (`src/lib/map/imagePixels.test.ts:126-128`) | `returned` | `<anonymous>.<anonymous>` | second reading |
| 17 | `e189 RAISE   loadImagePixels raise Error('Could not acquire a 2D canvas context for image analysis') L108` | `src/lib/map/imagePixels.ts:108` | `<anonymous>.<anonymous>` | vitest `rejects.toThrow` — `await expect(loadImagePixels(…)).rejects.toThrow(/context/i)` (`src/lib/map/imagePixels.test.ts:131-134`) | `returned` | `<anonymous>.<anonymous>` | first reading |

## The second readings

1. The only row whose parent is not a test body. `fetchCompendium` is an `async` function; the frame that unwinds is its own, and the frame directly above it is the arrow TanStack Query holds as `queryFn` — which returned a pending promise and is therefore the frame that "went on". The test body (`<anonymous>.<anonymous>`, two frames further out, via `renderControls`) is not the prediction: naming it would be naming a frame the serial never touched.
2. Reading `PanelErrorBoundary.tsx` was needed to be sure the boundary contributes no handler row: `getDerivedStateFromError` and `componentDidCatch` are React lifecycle methods, not `catch` clauses, so the transform (which wraps `catch` clauses and `.catch`/`.then(_, fn)` call sites) spliced nothing, and the catcher is react-dom itself.
3. Same reasoning as row 2, and it had to be checked separately because `Flaky` is declared inside the test body (qualname `<anonymous>.<anonymous>.Flaky`) rather than at module scope, which changes the qualname but not the frame above the unwind.
9. The shape aggregates three raises (`[×3: e98, e162, e182]` in the member trace) from three different `it` bodies at `attackRoll.test.ts:73`, `:136` and `:152`; each body's frame returned and each is spelled `<anonymous>.<anonymous>`, so the prediction holds for the printed block and for every member, including if rung 3's site-bearing key splits the shape.
10. Two raises share this raise site in the same trace and get different verdicts: `e118` (the `it` at `:95`, which wraps the call in its own `try { … } catch (e) { … }`) printed the escaped reason and is NOT a catch-all block, while `e140` (the `it` at `:122`) reaches `rejects.toBeInstanceOf` with no traced catch at all. Only the second is a row here.
11. The shape aggregates three raises (`[×3: e1387, e1686, e1700]`, three distinct messages) from two `it` bodies — `formula.test.ts:33` (`mystery`) and `:50` (`constructor`, `toString`). Both bodies returned and both are spelled `<anonymous>.<anonymous>`.
14. The shape aggregates two raises (`[×2: e1446, e1451]`) from two `it` bodies — `formula.test.ts:39` (the empty formula) and `:43` (the over-long one) — and is the one formula row whose throw happens in `evalFormula`'s own body rather than in `parseFactor`, so its caller list is two frames, not six.
16. The raise at `:117` is a NEW object thrown from inside `loadImagePixels`'s own `try { … } catch (error) { … }` (L112-120); the DOMException it translates (`e157`, from `FakeCanvas.getContext.getImageData`) is a separate unit that printed the escaped reason. This row is the translation, which no traced code catches — vitest's `rejects` does.
predicted unnamed after rung 3: 0
