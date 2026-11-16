# S5 rung 4 — the hand count: the LINE rows of `parseDiceGroups('1d20')`, counted before any rung-4 code exists

This table is the **prediction** E12 H3 is judged against. It was written at
Task 0, on a branch whose tip changed nothing under `src/`,
`typescript/src/`, `rust/` or `corpus/`: `typescript/src/bindings.mjs` and
`probe.mjs` do not exist, the runtime has no `line`, the converter has no
`_on_line`, and no LINE row has ever been written for a TypeScript program.
H3 STOPs on a count this table got wrong even where the transform is right,
and that is the design — a count derived after the rows have printed is not
a prediction.

**What is read.** `src/lib/diceQueue.ts` of the lens — *VTT frontend at
0091e97 — vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores
(powersave); snapshot taken under sensorium 0.8.7 / sensorium-ts 0.1.0 at
29c5059* (`typescript/acceptance/LENS.txt`, verbatim) — opened read-only at
`parseDiceGroups`, line 68, together with `src/lib/diceQueue.test.ts`. Every
line number below is a line of `src/lib/diceQueue.ts`. Nothing under the
lens was modified; the copy was verified byte-identical to rung 1's
748-entry manifest before and after this reading (record §2).

**The activation counted.** H3 reads the **first** activation of
`parseDiceGroups` in F1, which is `parseDiceGroups('1d20')` — the call at
`diceQueue.test.ts:16`, in `it('parses a single group')`, the first `it` of
the file's first `describe`. A `describe` callback only registers; the `it`
bodies run in file order, so no earlier call to this function exists in the
run. The module-level `const GROUP_RE = …` at line 65 is module code, never
a frame (§3.9), and mints nothing.

**The source, as it stands in the lens:**

```ts
68  export function parseDiceGroups(formula: string): Array<{ count: number; sides: number }> {
69    const groups: Array<{ count: number; sides: number }> = [];
70    GROUP_RE.lastIndex = 0;
71    let m: RegExpExecArray | null;
72    while ((m = GROUP_RE.exec(formula)) !== null) {
73      const count = m[1] ? parseInt(m[1], 10) : 1;
74      const sides = parseInt(m[2], 10);
75      if (Number.isFinite(count) && Number.isFinite(sides) && count > 0 && sides > 0) {
76        groups.push({ count, sides });
77      }
78    }
79    return groups;
80  }
```

with `GROUP_RE` = `/(\d*)d(\d+)(?:[a-z]{1,3}\d+)?/gi` (line 65).

**The rules applied**, all four of them, each named per row in the `rule`
column:

- **§3.1 (where a probe goes)** — one row per statement of a focused
  function's body at every block depth, and only when the statement
  **completes normally**. `return`, `throw`, `break` and `continue` mint no
  row of their own.
- **§3.2 (the deltas)** — the table of statement shapes: what a `const`/
  `let`/`var` binds, that `let x;` binds `undefined` and is a write, that a
  place write (`a.b = e`) yields none, that a guard which binds or assigns
  mints a synthetic first row inside the body at the head's line once per
  entry, that an expression statement writing nothing has empty `deltas`,
  and that a block-like statement completing has empty `deltas` plus
  `unbound`.
- **§3.4 (`unbound`)** — a block-like statement's row lists the
  block-scoped names its block declared, which just died; plan P4 restricts
  that to the block's **direct** declarations.
- **Plan P1** — (a) a guarded statement's OWN completion row carries its
  head's assignment targets as deltas, declarations excluded; (b) a `let x;`
  with no initialiser IS a row, with delta `x`.

**What mints nothing here**, stated so that the count is falsifiable in both
directions: the parameter `formula` (§3.3 — the CALL carries `args`, and
there is no parameters row, so N counts statements only); `return groups;`
at line 79 (§3.1); the failed second evaluation of the `while` head (§3.2 —
a guard that fails mints nothing); the function's own line 68 and the
closing braces at 77, 78 and 80.

## The table

| row | line | statement | deltas | unbound | rule |
|---|---|---|---|---|---|
| 1 | 69 | `const groups: Array<{ count: number; sides: number }> = [];` | groups | - | §3.2 `const PAT = e` |
| 2 | 70 | `GROUP_RE.lastIndex = 0;` | - | - | §3.2 place write (§3.9) |
| 3 | 71 | `let m: RegExpExecArray \| null;` | m | - | §3.2 `let x;` + plan P1(b) |
| 4 | 72 | `while ((m = GROUP_RE.exec(formula)) !== null)` — head row, entry 1 | m | - | §3.2 head row |
| 5 | 73 | `const count = m[1] ? parseInt(m[1], 10) : 1;` | count | - | §3.2 `const PAT = e` |
| 6 | 74 | `const sides = parseInt(m[2], 10);` | sides | - | §3.2 `const PAT = e` |
| 7 | 76 | `groups.push({ count, sides });` | - | - | §3.2 expression statement, no write |
| 8 | 75 | `if (Number.isFinite(count) && …) { … }` — the `if` completing | - | - | §3.2 block-like + §3.4 |
| 9 | 72 | `while ((m = GROUP_RE.exec(formula)) !== null) { … }` — the `while` completing | m | count, sides | plan P1(a) + §3.4 + plan P4 |

The one `|` of row 3's source text is escaped as `\|` because a markdown
table cell cannot hold a bare pipe; the statement in the lens reads
`let m: RegExpExecArray | null;`.

## Why each row is there, and why it is not more

**Row 1, line 69.** §3.2's first shape: a `const` declaration writes every
identifier its pattern binds, here the single name `groups`. The statement
completes normally, so the probe spliced after its `;` runs. `groups` is
`[]`.

**Row 2, line 70.** `GROUP_RE.lastIndex = 0;` assigns to a **member
expression**, not to an identifier: §3.2's fourth shape makes it a place
write with no deltas, and §3.9 declares place writes outside the tier
altogether. The statement still completed, so the row exists with empty
`deltas` — the row says the line ran. It is also what makes row 4's match
start at index 0 whatever the previous activation left behind.

**Row 3, line 71.** §3.2's second shape and plan P1(b): JavaScript binds a
declared-but-uninitialised `let` to `undefined`, which is a write, so the
declaration is a row and `m` is its delta. (Rust's deferred `let` binds
nothing until assigned and mints no delta — the two languages differ here
and the contract's LINE row says which does which.) The type annotation is
erased before any probe exists and changes nothing. `m` is `undefined`.

**Row 4, line 72, the head row.** §3.2's fifth shape: a guarded body whose
head assigns mints a synthetic first row **inside the body at the head's
line**, once per entry, captured at entry. `GROUP_RE` is global (`/gi`) and
row 2 reset `lastIndex` to 0, so `GROUP_RE.exec('1d20')` matches at index 0;
the head's assignment writes that match array into `m`, `!== null` is TRUE,
and the body is entered. `deltas: m` — the match array, which `util.inspect`
renders `[ '1d20', '1', '20', index: 0, input: '1d20', groups: undefined ]`.
There is **exactly one** entry: see row 9.

**Row 5, line 73.** §3.2's first shape. `m[1]` is the `(\d*)` group, `'1'`,
which is truthy, so the conditional takes `parseInt('1', 10)`: `count` is
`1`. (The `: 1` branch — the one that would run for `'d20'` — is not this
activation's.)

**Row 6, line 74.** §3.2's first shape. `m[2]` is the `(\d+)` group, `'20'`:
`sides` is `20`. This row is §1.3's first `flow --value` sighting and §1.2's
W1 site.

**Row 7, line 76.** §3.2's sixth shape: an expression statement that writes
no identifier. `groups` is read and the array it names is mutated through a
method call; a method call is not an assignment to a name, so `deltas` is
empty and the row says the line ran. It runs because the `if` guard is true.

**Row 8, line 75, the `if` completing.** §3.2's seventh shape with §3.4.
The guard reads `Number.isFinite(1) && Number.isFinite(20) && 1 > 0 && 20 >
0` → **true**, so the block ran and the `if` completed normally; the probe
after its closing brace (line 77) runs. The head neither binds nor assigns,
so §3.2's fifth shape mints no head row for it and plan P1(a) adds no
delta. The block declares no block-scoped name **directly** (plan P4), so
`unbound` is empty and `"u"` is absent from the wire record (§3.6).

**Row 9, line 72, the `while` completing.** The head is evaluated a second
time with `lastIndex` at 4, past the end of `'1d20'`; `exec` returns `null`
(and resets `lastIndex` to 0), the test is false, and the loop ends. A
guard that fails mints no head row (§3.2), but the `while` **statement**
completed normally, so §3.2's seventh shape gives it a row. Plan P1(a):
that row carries the head's assignment targets as deltas, so `deltas: m`,
its last write, `null` — the write the per-entry rule alone would leave
unreported. §3.4 with plan P4: `unbound` is the body block's **direct**
block-scoped declarations, `count` and `sides`, both of which just died.
This is the row §1.2's W2 (no HIT, `count` is gone) and W3 (`m == null`)
read.

**Which line a block-like statement's row carries.** Rows 8 and 9 report
their statement's **first** line — 75 and 72 — not the line of the closing
brace the probe sits after. §3.1 fixes where the probe is spliced and does
not say which line the row carries; the Rust focus design this transfers
does (`2026-09-06-sensorium-rung4-focus-tier-design.md` §3.1: "`line` = the
statement's first line (`Span::start`)"), and §3.2's own head-row rule puts
a guard's synthetic row "at the head's line". A `while` whose head row read
72 and whose completion row read 78 would name two places for one
statement. So every row's `line` is its statement's first line, and lines
77, 78 and 80 carry no row at all.

## The CALL, which is not a row

Deliberately **not** the five-column table above: a CALL carries `args`, not
`deltas`/`unbound`, it is not a LINE row, and it is not counted in N (§3.3 —
"there is no parameters LINE: N is the statements"). It is written here
because H2's third reading is what this activation's CALL prints.

| record | line | call | args | reading |
|---|---|---|---|---|
| CALL | 68 | `parseDiceGroups('1d20')` | `formula` = `'1d20'` | `grep F1 parseDiceGroups --kind CALL` prints `parseDiceGroups(formula='1d20')` first |

`args` is captured at body entry, after defaults are applied; `parseDiceGroups`
has one parameter, no default, no destructuring and no rest, so the args map
has exactly one key. `formula` is also §1.3's second `flow --value`
sighting, as `arg formula`.

## What H3 reads

- **The count (the gate):** the first activation of `parseDiceGroups` in F1
  carries exactly **nine** LINE rows.
- **The rows' `line` values, in order (the second reading):** 69, 70, 71,
  72, 73, 74, 76, 75, 72.
- **Rows carrying `unbound`:** **1** — row 9 only, `count, sides`. Every
  other row's `"u"` is absent from the record (§3.6).
- **Rows with empty `deltas`:** 3 — rows 2, 7 and 8.

N = 9
