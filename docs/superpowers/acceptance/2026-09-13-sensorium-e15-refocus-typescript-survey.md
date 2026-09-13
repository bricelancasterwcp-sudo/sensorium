# S5, the refocus slice — E15's selection, surveyed by hand before the instrument exists

This table is the **prediction** E15's H4 and H5 are judged against (spec
§5, plan ruling A7). It was written at Task 0, on a branch whose tip changed
nothing under `src/`, `typescript/src/` or `rust/`: no line of
`typescript/acceptance/e15.py` exists, no trace has been recorded for this
slice, and no `refocus` has been run on a TypeScript recording by anything.
The **expected-MATCH list is every row whose class is `deterministic`**, and
the expected-granted list is the same list. A row classed `nondeterministic`
names its reason and is a READING; a row classed `unsurveyed` is a reading
too. A class this table got wrong is a finding against **this survey**, not
against the tool.

§1 of `docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md`
pins this file by sha256, and `tests/test_acceptance_e15_lock.py` recomputes
that sha on the working tree — so a row corrected after a verdict has
printed fails a test rather than passing unnoticed.

**What is read.** The lens — *VTT frontend at 0091e97 — vitest 4.1.9, vite
6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores (powersave); snapshot taken
under sensorium 0.8.7 / sensorium-ts 0.1.0 at 29c5059*
(`typescript/acceptance/LENS.txt`, verbatim) — opened READ-ONLY. Every path
below is relative to the lens root; no box path is written here. Nothing
under the lens was modified: it was verified byte-identical to rung 1's
748-entry manifest immediately after this reading (**748 OK, 0 FAILED**).

**The selection**, spec §5's own rule, run from the lens root:

```
find src -name '*.test.*' | LC_ALL=C sort | awk 'NR % 12 == 1'
```

372 test files, every twelfth from index 0 → **31** paths, in the order the
table numbers them.

**The focus spec**, spec §5's rule — *the first function, in source order, of
the first `src/` module the test file imports that `resolve.mjs` selects; if
the file imports none, the first function the file itself defines* — spelled
`<basename>:<qualname>`. Three readings of that sentence had to be fixed
before it named anything, and all three are written down here rather than
left in the table's results:

1. **"imports"** is the module specifier of an `import` or `await import(…)`
   statement, in source order, whose specifier resolves under `src/`. A
   `vi.mock('…')` call is not an import — it registers a factory — and a
   `import type` names no module the run loads, so the first **value**
   import is the one taken. Rows 20 and 27 are the only two where the two
   readings could differ, and in row 20 both name the same file.
2. **"the first function"** is the first eligible site of that module by
   line, skipping any qualname carrying an `<anonymous>` segment — a name no
   caller can type, which is why `resolve.mjs`'s own `suggestions` leaves
   them out. It bites on rows 3 and 22, whose modules open with anonymous
   module-level arrows.
3. **Row 14's module offers only anonymous sites**, so the spec's fallback
   clause is applied one step earlier than its literal condition: the
   resolver selects no typeable function of `shortcutRegistry.ts`, the test
   imports no other `src/` module, and the spec named is the first function
   the test file itself defines. The resolver's count for it is 1, not 0,
   which is what the clause exists to prevent.

**`resolver matched`** is measured, never guessed (plan ruling A7): one run
of `node typescript/src/resolve.mjs` per row, invoked exactly as
`typescript/acceptance/e12p.sh` step 3 invokes it —
`SENSORIUM_TS_ROOT=<lens> SENSORIUM_FOCUS=<the row's spec>` — and the number
is `len(matched)` off its one JSON line. Every row is ≥ 1; no spec had to be
re-derived for an empty match.

**The class**, spec §5's rule — `deterministic` unless the test file or that
module reads `Math.random`, `Date.now`/`new Date()`/`performance.now` into a
branch, a real timer the test does not fake, `fetch`/a socket, or iterates an
unordered collection into a branch. Three readings again:

1. **The unit the class is about is the comparator's.** A TypeScript pair
   compares as an order-independent multiset of CALL/RETURN/RAISE/HANDLED
   per task (spec §3.1); LINE rows never enter it. So a value that is random
   but never branched on cannot move the verdict — which is why the four
   `roomStore.ts` rows stay deterministic even though the store mints ids
   with `` `${Date.now()}_${Math.random()…}` ``: the id is a string, not a
   branch.
2. **JavaScript has no unordered collection here.** Object keys, `Map` and
   `Set` iterate in insertion order by the language, so `Object.keys(…)` and
   `for (const x of set)` are ordered iterations and no row is classed on
   one.
3. **The class is about what the run REACHES.** A socket or a clock in a
   function the test never calls cannot move the causal stream; where a
   module carries one, the row's reason cell says where it sits and what
   keeps the test out of it.

The one thing that does move the multiset on this lens is
`@testing-library`'s `waitFor` (and the `findBy*` queries built on it):
outside `vi.useFakeTimers()` it polls on a real 50 ms interval and calls its
callback until the callback stops throwing, so the number of activations of
a callback DEFINED IN THE TEST FILE — and therefore traced — is decided by
wall clock rather than by the program. That is "a real timer the test does
not fake", and it is the reason on all seven nondeterministic rows.

## The table

| n | test file | class | reason | focus spec | resolver matched |
|---|---|---|---|---|---|
| 1 | `src/__tests__/AiPrepPanel.test.tsx` | nondeterministic | `findByText` polls on a real timer this test never fakes, so its callback's activation count is decided by wall clock | `AiPrepPanel.tsx:AiPrepPanel` | 4 |
| 2 | `src/__tests__/CombatTrackerPf2ePersistent.test.tsx` | deterministic | — (`global.fetch` is a `vi.fn` in every case; the store's id-minting `Date.now()`/`Math.random()` feeds a string, not a branch) | `roomStore.ts:_persistMacros` | 1 |
| 3 | `src/__tests__/GmCockpit.test.tsx` | nondeterministic | `waitFor` polls on a real timer this test never fakes, so its callback's activation count is decided by wall clock | `GmCockpit.tsx:GmCockpit` | 32 |
| 4 | `src/__tests__/PlayerViewRulesTabOrder.test.tsx` | deterministic | — (the module's only `apiFetch` sits in `probeAiConfigured`, which `vi.spyOn(useAiAssistModule, 'useAiAssist')` keeps this test out of) | `useAiAssist.ts:runAiSettingsProbe` | 1 |
| 5 | `src/__tests__/TurnCard.test.tsx` | nondeterministic | `waitFor` polls on a real timer this test never fakes, so its callback's activation count is decided by wall clock | `TurnCard.tsx:breakdownLabel` | 1 |
| 6 | `src/__tests__/api.test.ts` | deterministic | — (the module's `fetch` is `vi.stubGlobal`'d for every case) | `api.ts:apiFetch` | 1 |
| 7 | `src/__tests__/classEditor.test.tsx` | deterministic | — | `ClassEditor.tsx:parseCsv` | 2 |
| 8 | `src/__tests__/describeCharacter.test.tsx` | nondeterministic | `waitFor` polls on a real timer this test never fakes, so its callback's activation count is decided by wall clock | `roomStore.ts:_persistMacros` | 1 |
| 9 | `src/__tests__/footerSaveVsRest.test.ts` | deterministic | — (the store's `saveCharacterSheet` is replaced with a `vi.fn`, so no request leaves the process) | `roomStore.ts:_persistMacros` | 1 |
| 10 | `src/__tests__/levelingSettings.test.tsx` | nondeterministic | `waitFor` polls on a real timer this test never fakes, so its callback's activation count is decided by wall clock | `LevelingSettings.tsx:LevelingSettings` | 12 |
| 11 | `src/__tests__/perfFlat.test.ts` | deterministic | — | `perfFlat.ts:shouldUsePerfFlat` | 1 |
| 12 | `src/__tests__/responsive/PanelDrawer.test.tsx` | deterministic | — | `PanelDrawer.tsx:PanelDrawer` | 4 |
| 13 | `src/__tests__/roomStore.terrain.test.ts` | deterministic | — (`vi.mock('../lib/api')` takes `apiFetch` out of the store's terrain path) | `roomStore.ts:_persistMacros` | 1 |
| 14 | `src/__tests__/shortcutRegistryDrift.test.ts` | deterministic | — (`readFileSync` over files of the checkout, which do not move between the two runs) | `shortcutRegistryDrift.test.ts:readSrc` | 1 |
| 15 | `src/__tests__/uploadWithProgress.test.ts` | deterministic | — (the module's `XMLHttpRequest` is a `FakeXhr` the test installs and restores) | `uploadWithProgress.ts:uploadWithProgress` | 14 |
| 16 | `src/__tests__/useMeshVoice.test.tsx` | nondeterministic | eight `waitFor`s poll on a real timer in the first describe — only the Track-A2 describe fakes timers — so their callbacks' activation counts are decided by wall clock | `useMeshVoice.ts:loadVolumes` | 1 |
| 17 | `src/__tests__/useWebSocket.test.tsx` | deterministic | — (`WebSocket` and `fetch` are both stubbed; the one non-faked reconnect `setTimeout` is 500–1000 ms out and RTL's `afterEach` unmount clears it two assertions later) | `useWebSocket.ts:buildDiceRollSourceFromChat` | 1 |
| 18 | `src/components/PanelErrorBoundary.test.tsx` | deterministic | — | `PanelErrorBoundary.tsx:PanelErrorBoundary.getDerivedStateFromError` | 1 |
| 19 | `src/components/compendium/ItemEditor.test.tsx` | deterministic | — | `ItemEditor.tsx:buildDraftInstruction` | 1 |
| 20 | `src/components/map/hexGrid.test.ts` | deterministic | — | `hexGrid.ts:snapToGridPoint` | 1 |
| 21 | `src/components/pf2e/ActionPips.test.tsx` | deterministic | — | `ActionPips.tsx:ActionPips` | 3 |
| 22 | `src/components/sheet/SpellCastPanel.test.tsx` | nondeterministic | `waitFor` polls on a real timer this test never fakes, so its callback's activation count is decided by wall clock | `SpellCastPanel.tsx:SpellCastPanel` | 36 |
| 23 | `src/hooks/useWebSocket.diceDispatch.test.ts` | deterministic | — (the module's `crypto.randomUUID`, `new Date()`, `Math.random` and `WebSocket` all sit inside `useWebSocket()`, which this 20-line test never calls) | `useWebSocket.ts:buildDiceRollSourceFromChat` | 1 |
| 24 | `src/lib/builder/archetypeOverrideLedger.test.ts` | deterministic | — | `advancement.ts:levelRecord` | 2 |
| 25 | `src/lib/builder/emit/dnd5eSheet.test.ts` | deterministic | — | `dnd5eSheet.ts:baseScores` | 1 |
| 26 | `src/lib/builder/multiclassContext.test.ts` | deterministic | — | `multiclassContext.ts:normalize` | 1 |
| 27 | `src/lib/combat/rest.test.ts` | deterministic | — | `rest.ts:capToward` | 1 |
| 28 | `src/lib/dnd5e/classes.test.ts` | deterministic | — | `classes.ts:classNameToken` | 1 |
| 29 | `src/lib/items/resolveItem.test.ts` | deterministic | — | `resolveItem.ts:deepMerge` | 1 |
| 30 | `src/lib/pf2e/boosts.levelBoosts.test.ts` | deterministic | — | `boosts.ts:isAbility` | 1 |
| 31 | `src/lib/sheets/mergeSheetSnapshot.test.ts` | deterministic | — | `mergeSheetSnapshot.ts:isDeepEqual` | 3 |

**24 deterministic · 7 nondeterministic · 0 unsurveyed.** The expected-MATCH
list is the 24; the expected-granted list is the same 24.

### H6 reads

Four reads on three REFOCUSED traces — rows 1, 16 and 31 — each with its
predicted verdict class and exit, derived from the function's own source
before any of them was run. H6 holds when all four answer as predicted; one
that does not is reported with what it said.

- **Row 1** — `watch <row 1's refocus> --at AiPrepPanel --expr 'tool == "statblock"'`
  → **SATISFIED, exit 0**. `const [tool, setTool] = useState('statblock')` is
  the component's second statement and binds `tool` on every first render, so
  the predicate holds at the sites after it in all four tests; the fourth
  test ("switches tools via the tab nav") re-renders with `'names'`, so some
  sites will not satisfy and the verdict line reports hits against evaluable
  sites rather than against all of them, the shape
  `corpus/typescript/focus_finally_return` pins.
- **Row 16** — `watch <row 16's refocus> --at loadVolumes --expr 'raw != null'`
  → **SATISFIED, exit 0**. `loadVolumes`'s one statement binds
  `raw = JSON.parse(localStorage.getItem(KEY) || '{}')`, which is `{}` on an
  empty store and a parsed object otherwise — never `null`, because
  `saveVolume` is the only writer and it writes an object. The function is
  reached twice over: `getStoredVolume` calls it as each peer attaches, and
  `setPeerVolume` calls it through `saveVolume`.
- **Row 31** — `watch <row 31's refocus> --at isDeepEqual --expr 'a == b'`
  → **SATISFIED, exit 0**. `mergeSheetSnapshot` calls
  `isDeepEqual(nextR[key], baseR[key])` for every key present in both
  snapshots, and the untouched keys — the whole point of the merge — pass
  identical primitives, so `a == b` holds at the parameters row of those
  activations and fails at the ones the editor changed.
- **Row 16, the value read** — `flow <row 16's refocus> --value 0.4`
  → **NOT FOUND, exit 1**, with the searched scope printed beside the
  emptiness (`corpus/typescript/focus_loop_counter`'s second `flow`). The
  only capture-bearing function in that trace is `loadVolumes`, whose single
  local `raw` is the object read out of `localStorage` BEFORE
  `saveVolume` writes `0.4` into it; `0.4` itself is bound in `saveVolume`,
  which this focus does not reach. The falsifier is named because it is the
  interesting half: `flow_values.find_in_value` walks nested maps, so a
  later `getStoredVolume` that re-reads the store after the write would put
  `alice: 0.4` inside `raw` and the read would come back FOUND — which is
  exactly the fact this read is pre-registered to settle.

N = 31
