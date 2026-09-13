# S5 rung 4's debts — H2′'s hand count: the function-likes three specs select, counted before `e12p_report.py` exists

This table is the **prediction** E12′ H2′ is judged against (plan ruling A4).
It was written at Task 0, on a branch whose tip changed nothing under `src/`,
`typescript/src/` or `rust/`: `typescript/acceptance/e12p_report.py` does not
exist, no cell of E12′ has been computed, and nothing in this slice has
parsed a transcript. H2′ holds when this count, the resolver's site list in
the rung-4 record and the committed trace's `meta.functions_focused` are the
same number; a count this table got wrong is a **STOP**, recorded as a
finding, even where the resolver is right.

**What is read.** `src/lib/diceQueue.ts` of the lens — *VTT frontend at
0091e97 — vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores
(powersave); snapshot taken under sensorium 0.8.7 / sensorium-ts 0.1.0 at
29c5059* (`typescript/acceptance/LENS.txt`, verbatim) — opened read-only at
lines 68–80, 127–156 and 194–212. Nothing under the lens was modified; the
copy was verified byte-identical to rung 1's 748-entry manifest immediately
before this reading (748 OK, 0 FAILED — the record's §2).

**The three specs**, as rung 4's F arms passed them and as the rung-4
record's §1 writes them:

```
--focus diceQueue.ts:parseDiceGroups
--focus diceQueue.ts:forcedDiceFromSource
--focus diceQueue.ts:buildDiceQueueEntry
```

**The rule applied** is `typescript/src/focus.mjs`'s own, the container rule:
*"a value naming a CONTAINER selects everything under it on a `.` boundary"*
— `Fog` selects `Fog.compute`. A spec therefore selects the function it
names **and every function-like nested inside that function's body or its
parameter list**, at any depth, since each of those carries the named
function's qualname as its `.`-prefix. A function-like is a function
declaration, a function expression, a method or an arrow; `sitesOf` spells
an unnamed one `<container>.<anonymous>`.

**The source, as it stands in the lens** (only the lines that mint a row
below; the elided lines carry no function-like):

```ts
 68  export function parseDiceGroups(formula: string): Array<{ count: number; sides: number }> {
 …       (69–79: const, a place write, a `let`, a `while`, a `const`×2, an `if`, a `push`, a `return` — no function-like)
 80  }

127  export function forcedDiceFromSource(source: DiceRollSource): { dice: ForcedDie[]; skippedCount: number } {
 …
132    const declared = groups.reduce((sum, g) => sum + g.count, 0);
 …       (128–155: `if`s, `return`s, spread, `const`, `let`, two `for…of`, `push`, `+=` — no other function-like)
156  }

194  export function buildDiceQueueEntry(
195    source: DiceRollSource,
196    opts: EnqueueOptions,
197    idFactory: () => string = () => crypto.randomUUID(),
198    now: () => number = () => Date.now(),
199  ): DiceQueueEntry | null {
 …       (200–211: an `if`, a destructuring `const`, an `if`, a `return` of an object literal — no other function-like)
212  }
```

Lines 197 and 198 each carry a TYPE annotation that reads like an arrow
(`() => string`, `() => number`) and an INITIALISER that is one
(`() => crypto.randomUUID()`, `() => Date.now()`). Only the initialiser is a
function-like: a type annotation is erased before the transform ever walks
the tree, and it has no body to instrument. Each line therefore mints one
row here, not two.

## The count

| n | qualname | line | kind | how selected |
|---|---|---|---|---|
| 1 | `parseDiceGroups` | 68 | function declaration (exported) | named by the spec `diceQueue.ts:parseDiceGroups` |
| 2 | `forcedDiceFromSource` | 127 | function declaration (exported) | named by the spec `diceQueue.ts:forcedDiceFromSource` |
| 3 | `forcedDiceFromSource.<anonymous>` | 132 | arrow, the `reduce` callback `(sum, g) => sum + g.count` | container rule: nested in row 2's body |
| 4 | `buildDiceQueueEntry` | 194 | function declaration (exported) | named by the spec `diceQueue.ts:buildDiceQueueEntry` |
| 5 | `buildDiceQueueEntry.<anonymous>` | 197 | arrow, the default of parameter `idFactory` — `() => crypto.randomUUID()` | container rule: nested in row 4's parameter list |
| 6 | `buildDiceQueueEntry.<anonymous>` | 198 | arrow, the default of parameter `now` — `() => Date.now()` | container rule: nested in row 4's parameter list |

**The shared qualname.** Rows 5 and 6 are two distinct functions at two
distinct lines that `sitesOf` spells with ONE qualname,
`buildDiceQueueEntry.<anonymous>`, because neither arrow has a name and both
hang off the same container. `focus_matched` is a SET of `<file>:<qualname>`
strings and `functions_focused` is a count of instrumented functions, so the
two numbers differ by exactly one here: **`focus_matched` = 5**,
**`functions_focused` = 6**.

## What H2′ reads

- **The count (the gate):** the three specs select exactly **six**
  function-likes; `node resolve.mjs` names six sites and
  `meta.functions_focused` is 6.
- **The set (the second reading):** `meta.focus_matched` is **5**, and the
  one qualname two sites share is `buildDiceQueueEntry.<anonymous>`.

N = 6
