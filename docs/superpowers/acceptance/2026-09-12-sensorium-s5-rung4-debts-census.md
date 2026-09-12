# S5 rung 4's debts — the seal-deferred census: counted by hand before the detector exists

This file is the **prediction** E13's second clause is judged against (plan
ruling A5). §4.6's `typescript/acceptance/census_deferred.mjs` cannot run at
T0 — the detector it walks with does not exist yet — so the three lists below
are read by hand, and E13 holds when the script, once written, prints exactly
these and the transform's 0.3.0→0.4.0 golden diff over the same roots changes
exactly these functions' wrappers and no other byte.

**The rule**, from design §4.2, applied to one function at a time:

> A function is **seal-deferred** when its own body — not a nested function,
> arrow, method or class — contains a `ReturnStatement` whose ancestors, up to
> the function, include a `TryStatement` with a `finallyBlock`, and the return
> sits inside that try's `tryBlock` or `catchClause`. (A return inside the
> `finallyBlock` itself is a return that no further finally of that try
> guards; it counts only if an OUTER try-with-finally encloses it — same
> test, one level up.)

**How each root was swept.** `grep -rn 'finally'` over the root, excluding
`node_modules`, over `*.ts`, `*.mjs` and `*.js`; then every hit read in
context. A try-with-finally cannot exist without the keyword, so a root with
no `finally` hit carries no seal-deferred function, and a root's hits are the
complete candidate set. The three roots are §4.6's: `typescript/probes`,
`corpus/typescript`, and the lens's `src/lib/diceQueue.ts`.

Each table's `line` is the function's own definition line.

## 1. `typescript/probes`

Two `finally` bodies in the root, and NEITHER function is seal-deferred.

| file | qualname | line |
|---|---|---|

N = 0

- `typescript/probes/src/swallow.probe.test.ts:117` — `shape12`'s `return
  'ok';` sits inside the `finallyBlock` itself (`try { throw … } finally {
  return 'ok' }`), and no outer try-with-finally encloses it, so the
  parenthesis of the rule excludes it. It is the shape the corpus's
  `finally_return` case is built from, and the same reading applies to both.
- `typescript/probes/nodetest/controls.mjs:79` — `main`'s try has a
  `finallyBlock` and its `tryBlock` contains no `return` at all (the function
  has none anywhere; it sets `process.exitCode` and falls off the end). No
  return, nothing to defer.

## 2. `corpus/typescript`

One function, this task's own. `grep` finds `finally` in exactly two files of
this root, and the second is excluded by the same clause as `shape12`.

| file | qualname | line |
|---|---|---|
| `corpus/typescript/focus_finally_return/finally.ts` | `settle` | 7 |

N = 1

- `corpus/typescript/focus_finally_return/finally.ts:7` — `settle`'s `return
  1` and `return 2` both sit in the `tryBlock` of a try whose `finallyBlock`
  is `{ cleanup = 1; note(cleanup); }`. Seal-deferred, and the case exists to
  pin what the seal does. `note` (line 18) has no `try` at all and is not
  deferred; it is the CALL the finally makes, not a function with the shape.
- `corpus/typescript/finally_return/ledger.ts:6` — **not counted.** `commit`
  is rung 2's case and its shape is a `return rows;` inside the
  `finallyBlock`, with no `catch` anywhere and no enclosing try. That is the
  rule's parenthesis exactly: a return in a finally that no further finally
  guards, and no OUTER try-with-finally one level up. Its wrapper must
  therefore be byte-identical after the seal, which is the part of E13's
  golden diff that says the rule discriminates rather than firing on every
  `finally` in the tree.
- No other file of this root contains the keyword `finally`, so no other
  function of it can carry the shape.

## 3. The lens — `src/lib/diceQueue.ts`

| file | qualname | line |
|---|---|---|

N = 0

`grep -n 'finally'` over the file exits 1: the file contains no `try` and no
`finally` at all, so **no function of `diceQueue.ts` returns from inside a
try-with-finally**. This is E13's third clause and H8′'s eighth: the lens
file's transform under this slice must be byte-identical to 0.3.0's, and the
census is what makes that a prediction rather than a hope.

## What E13 reads

- The three lists above, printed by `census_deferred.mjs` exactly: **0**,
  **1**, **0**.
- The transform golden diff 0.3.0→0.4.0 over `typescript/probes/src` and
  `corpus/typescript` changes exactly `settle`'s wrapper and no other byte.
