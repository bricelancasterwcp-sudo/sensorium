# S5 rung 4 — the focus tier: LINE, arguments and identity for TypeScript under `--focus`

*Design, 2026-09-11. Brainstormed with Brice: the slice ruled from a field of
four, approach 1 ruled from a field of three, seven sections approved in
turn. Design authority: Claude. Base: main `4ce2cda` (Python 0.11.0 /
sensorium-ts 0.2.0). Branch: `feat/s5-rung4`.*

## 0. Provenance

The TypeScript recorder's design
(`2026-09-09-sensorium-typescript-recorder-design.md`, §11) set a ladder:
recorder v1 (rung 1, DONE-WITH-STOP, then slice 2 closed the STOP), the
throw flow (rung 2, DONE), and next *"Tiers — `--focus <qualname>`:
argument capture and one LINE per completed statement with the bindings it
wrote (the Rust focus design, transferred), `watch`/`flow`; measured cost
per tier. Own design doc."* Rung 3 (naming the ambiguity, PR #32, main
`4ce2cda`) sat between, reader-side only. This is that tier's design, and by
count it is S5's fourth rung.

What it rests on:

- **The Rust focus design** (`2026-09-06-sensorium-rung4-focus-tier-design.md`,
  rulings F1–F3, amendments A1–A7). Its three rulings transfer: one slice
  for the tier and a later one for `refocus` (F1); the focus decided at
  transform time (F2); a LINE's `deltas` are the bindings the statement
  wrote (F3). Where JavaScript is not Rust, this document says so and why.
- **Two decisions of the recorder design** whose cost this rung pays: D12
  (*arguments unread in rung 1; an args tier arrives with `--focus`*) and
  D14 (*a `--focus` selector spelling is the tier's*).
- **What the readers already are.** `watch`, `flow` and `frame` read LINE
  rows and CALL `args` with no language branch; `caps.require` refuses on a
  declaration; `CAUSAL_KINDS` excludes LINE from the fingerprint. The
  TypeScript side mostly has to write the rows the readers already know.
- **The rung-3 debts** (`docs/CARRIED-DEBT.md`, the 2026-09-11 section):
  `Shape.site`'s fallback, the command journal outside the hashed set, a
  fence pattern matching no file, `e7_report.py`'s in-place rewrite,
  `CHANGELOG.md` at the ceiling. They are this rung's T0 (§6.3).
- **Measured, not assumed:** the `util.inspect` spellings §4.1 pins were
  read off node v24.16.0 under the recorder's own inspect options on
  2026-09-11, the way Rust's `Debug` spellings were read off rustc on
  2026-09-06.

## 1. Goal, scope, non-goals

**Goal.** An agent debugging the VTT frontend records one `vitest run`
under `--focus <function>` and asks what a local held at the statement that
wrote it, what a focused function was called with, whether a predicate held
at any recorded site, where a value was seen, and whether two captures are
one object — every answer a function of the trace, every refusal naming the
declaration it rests on.

**In scope.**

- `sensorium ts run --focus <spec>`, repeatable, both harnesses; resolution
  before the run; the environment plumbing; `focus` and `focus_matched` in
  the artifacts; `line` and `locals` declared true under a focus.
- The transform: one LINE probe after every statement of a focused
  function, `deltas` = the bindings the statement wrote, per-entry rows for
  guarded bodies, `unbound` on a block-like statement's row, `args` on the
  CALL of a focused function.
- The runtime and wire: `LINE` records, `a` on a focused CALL, `oid`/`type`
  on object captures; the converter's rows and meta.
- The readers: a second `dbg` dialect (`util.inspect`) behind the
  vocabulary; `null`/`undefined`/`true`/`false` as predicate constants; one
  site spelling for `--at` and `--focus`; per-language re-record guidance;
  `flow --object` on a serial identity.
- Ten corpus cases, two re-pins, vectors v35–v39, the acceptance record E12
  on the VTT lens, docs and versions, the rung-3 debts as T0, and the
  `debugging-typescript-with-sensorium` skill at the close.

**Non-goals.** `refocus` for TypeScript (next slice, on these rows);
`--window`; the browser substrate; a transform cache; probes inside `eval`
or `new Function`; place writes as deltas; identities for objects nested
inside another capture's text; any change to the Python or Rust recorders
beyond the shared readers' dialect seam.

## 2. The CLI and the pipeline (section 1, approved)

### 2.1 The flag and its spelling

`sensorium ts run [--tier off|call] [--focus <spec>]… [--jobs N] -- <harness
command>`. `--focus` is repeatable and parsed where `--tier` is, before the
`--`; a harness's own `--focus` after it is never stolen. A spec is
`<qualname>` or `<file>:<qualname>`.

- **The qualname is what `tree` prints** (recorder design §2.4, D14):
  `Fog.compute`, `outer.inner`, `refresh`, `default`. A value naming a
  container selects everything under it on a `.` boundary — equal, or a
  prefix ending at a `.` — so `--focus Fog` selects `Fog.compute` and
  `Fog.render`, and `--focus refresh` selects `refresh` and the arrows nested
  in it (`refresh.<anonymous>`). The container rule is the only way to name
  an anonymous function: `<anonymous>` carries no ordinal, and `<` is the
  shell's.
- **The file part narrows and is optional.** It is the root-relative path
  (`src/lib/cache.ts`), the basename (`cache.ts`) or the stem (`cache`).
  Qualnames are file-local, so a bare `--focus load` selects every `load`
  under the root — all of them, and `focus_matched` lists each — as a bare
  Rust qualname selects across a workspace. On the acceptance lens the most
  repeated stem is `types` (five files); the file part is what a reader
  reaches for there.
- **Notation.** `--focus` is the house flag on both other recorders and
  collides with nothing in grep, git, make or pytest. `file:symbol` is
  uvicorn's and Python's own spelling, and it is the reader's `--at` spelling
  (§4.3), so the recorder and the reader take one set of names. No globs, no
  regexes, no line numbers.

### 2.2 Resolution before the run

Before anything is minted, the driver runs the package's resolver —
`node <pkg>/src/resolve.mjs`, reading the root and the specs from the
environment — which walks the eligible files under the root with the
transform's own `classify` and `planSites` (pass one only; nothing is
spliced) and matches every spec with `focus.mjs`'s matcher. It prints one
JSON object: `{matched: [{rel, qualname, line, kind}], unmatched: [spec]}`.

Any unmatched spec refuses, exit 2, before a spool directory exists:

```
REFUSED: --focus <spec> matches no function under <root>; nothing was run. Closest: <up to 3>
```

Rust's sentence with the two words that are true here (*under `<root>`*,
*run*). `Closest:` lists up to three qualnames sharing the longest suffix
with the spec's qualname part, and is dropped only when the root holds no
eligible function at all. A spec whose only matches are functions the
transform excludes (an overload signature, a `declare`, a hoisted factory)
refuses with the exclusion named.

The resolver's wall on the lens (742 eligible files) is reported by E12 H7,
beside the run's.

### 2.3 Plumbing

- Driver → harness: `SENSORIUM_FOCUS`, the specs as typed joined by `\x1f`
  (a unit separator no identifier, string-literal property name or path can
  contain), set beside `SENSORIUM_TIER`. Absent or empty = no focus.
- Plugin and hook → transform: both read the variable once, split it, and
  pass `focus: string[]` in `transformSource`'s options beside `root`.
  `planSites` marks a function-like as focused after eligibility, with the
  same `focus.mjs` matcher the resolver used, against the file's `rel` and
  the site's qualname — so the resolver and the transform cannot disagree.
  The output stays a pure function of `(source, focus)`. There is no cache
  to key.
- Runtime: reads `SENSORIUM_FOCUS` at boot, like the tier, and declares
  `line: true, locals: true` in BOOT's `capabilities` when it is non-empty.
  A statement about what the recorder PRODUCES, not about what ran: a
  focused function that never ran leaves both true and zero LINE rows, and
  `focus_matched` is what says which functions were selected — Rust's
  semantics (design 2026-09-06 §2.4). The driver has already refused a
  focus that matched nothing, so non-empty means at least one match.
- `--tier off` with a focus: the probes are spliced and emit nothing. Not a
  measured arm.

### 2.4 What the artifacts say

- **Per-file manifest** (`tally.mjs`): `focused: [qualname…]`, the sites in
  this file the focus selected; absent when none. The tally gains
  `functions_focused`, the count across the invocation.
- **`invocation.json`**: `focus` (specs as typed) and `focus_matched`
  (sorted `rel:qualname` strings), from the resolver's output.
- **Meta**: `focus` and `focus_matched`, both absent when no focus was given,
  so `info`'s existing line prints `focus: -` as it does for an unfocused
  Rust trace; `focus: a, b` otherwise. `capabilities.line` and `.locals` come
  through BOOT's map over the converter's constant, the way `err_flow` does.

## 3. The probe and the payload (section 2, approved)

### 3.1 Where a probe goes

After every statement of a focused function's body at every block depth:
the body block, `if`/`else` blocks, loop bodies, `case` and `default`
clauses, `try`/`catch`/`finally` blocks, labeled and bare blocks. One point
splice after the statement — after its `;`, or after the closing brace of a
block-like statement — through the existing magic-string machinery, no
newline in any edit (recorder design §3). It runs only when the statement
**completes normally**: `return`, `throw`, `break` and `continue` mint no row
of their own, and their exit is already the RETURN, the UNWIND, or the
enclosing statement's row.

- An expression-bodied arrow has no statements; its value stays the RETURN's.
- A function declaration inside the body is hoisted and executes nowhere in
  particular: no row. A class declaration executes where it stands: a row,
  with the class name as its delta.
- A nested function's statements are probed only when it is itself under
  the focus prefix (§2.1), and then it is its own frame with its own rows.
  `--focus outer` therefore reaches the callbacks `outer` defines; `--focus
  outer.inner` reaches one of them.
- **Async and generator bodies are probed**, where Rust's are not (its
  entry guard's `Drop` across `.await`). A statement holding an `await`
  completes after the resume, and its probe runs then — after the `r(...)`
  the suspension rewrite already inserts — so `frame`'s timeline interleaves
  `~ YIELD` / `~ RESUME` with the rows.
- A `switch` discriminant that assigns (`switch (x = f())`) mints nothing
  (declared, §3.9).

### 3.2 What a probe captures — the deltas

Read off the statement's own AST at transform time by a new module,
`typescript/src/bindings.mjs` (the sibling of `escape.mjs`: pure, three
exports, no state): the names a statement *writes*, the names a guard
*binds*, and the block-scoped names a block-like statement *declares*.

| statement | deltas |
|---|---|
| `const`/`let`/`var PAT = e;` | every identifier `PAT` binds: nested object and array patterns, defaults, rest elements |
| `let x;` | `x` — JavaScript binds it to `undefined`, which is a write. Rust's deferred `let` binds nothing until assigned; the two differ and the contract says so |
| `x = e`, `x += e`, `x ??= e`, `x++`, `++x`, `[a, b] = [b, a]`, `({a} = o)`, at any depth in the statement's own expressions (a nested function body is not this statement's) | the identifier targets, in source order, once each. `\|\|=`, `&&=` and `??=` may not write; the row reports the binding's value after the statement either way, and the contract says so |
| `a.b = e`, `a[i] = e`, `delete a.b`, `a.b++` | none — a **place write**, declared (§3.9) |
| a guarded body whose head binds or assigns: `for (const x of xs)`, `for (const [k, v] of m)`, `for (const k in o)`, `for (let i = 0; …; i++)`, `while ((m = re.exec(s)) !== null)`, `do { … } while ((m = …))`, `if ((x = f()))`, `catch (e)`, `catch ({ code })` | the head's names, as a **synthetic first row inside the body at the head's line**, once per entry or iteration, captured at entry. A guard that fails mints nothing, and an `else` branch is not an entry: an `if ((x = f()))` whose test is falsy wrote `x` and reports it nowhere (declared, §3.9). A `for (let i …)` row carries `i`'s per-iteration value; its `i++` is the for's update clause, not a statement, and shows at the next iteration's row |
| an expression statement that writes nothing (`foo();`, `await p;`, `console.log(x);`) | empty `deltas` — the row says the line ran |
| a block-like statement completing (`if`, `for`, `while`, `do`, `switch`, `try`, a labeled or bare block) | empty `deltas`, plus **`unbound`** (§3.4) |

Two properties the count rests on: a statement's row exists exactly when the
statement completed normally, and a row's `deltas` are decided before the
run. So N for a straight-line path is derivable from the source by hand,
which is what E12 H3 pre-registers.

### 3.3 Arguments are not a LINE

The CALL of a focused function carries `args: {name: capture}` in the Python
shape, captured at body entry — after defaults are applied, so a default is
the value the body saw. A destructured parameter yields the names it binds,
a rest parameter its name; `this` is not a parameter and is not read; a
parameter shadowed before the body's first statement is still read at entry.
An unfocused function's CALL keeps `{"args": {}, "unread": ["locals"]}`
exactly as today, so `tree` prints `name() <unread: locals>` for it and
`refresh(key='rate')` for a focused one.

So a focused activation's first `watch` site is its CALL, as in Python, and
there is **no parameters LINE**: N is the statements. Rust minted a
parameters row (its A2) because its CALL could not carry args; the contract's
LINE row says which language does which.

### 3.4 `unbound` at block exit

A block-like statement's row lists as `unbound` the block-scoped names its
inner blocks declared — `let`, `const`, `class`, a `catch` binding, a `for`
head's declarations — which just died. `var` is function-scoped and is never
unbound. A per-iteration name (`for (const x …)`) is a delta again at the
next iteration's head row, so no `unbound` is needed between iterations.

This is the key `watch`'s fold needs: `sites_for` folds `deltas` forward and
pops `unbound` at the same site, so a `const y` inside an `if` is reported at
sites inside the block and at none after it. Python emits `unbound` for `del`
and the end of `except E as e:`; Rust emits none at all, and its fold keeps a
dead block-scoped `let` alive — a Rust debt this rung records in CARRIED-DEBT
and does not close.

### 3.5 Captures

Values are what `dbg.mjs` already produces for a RETURN: `util.inspect`
text under the 200-byte cap, `{k: "dbg", v, trunc}`, and `{k: "unread"}`
when inspection throws. Two keys are added for object and function values —
`oid` and `type` (§5). Reading a just-written local cannot throw (the
statement initialised it), so the probe passes an eager name/value array and
the runtime inspects only while recording. Getters and `inspect`
customisations run, as they do for a RETURN today (blind-spot footprint).

### 3.6 The wire

Wire stays **1**. Two additions:

```
{"e": "LINE", "f": <frame>, "t": <task|null>, "l": <line>,
 "d": {"<name>": <capture>, …}, "u": ["<name>", …]}   // "u" absent when empty
{"e": "CALL", …, "a": {"<name>": <capture>, …}}         // "a" on a focused CALL only
```

`ts` last, as on every stamped record. An older converter meets a LINE
record and refuses the spool by name ("no rule for a LINE record"), which is
the refusal it makes for any kind it does not know today.

### 3.7 The row

`_on_line` in `ts/build.py`: an `events` row of kind `LINE` on the open frame
(`frame_id`, the frame's `code_id`, `line` = `l`), payload `{"deltas": …}`
plus `"unbound": [...]` when present; no push, no pop, no fingerprint
update (`CAUSAL_KINDS` excludes LINE, so a focused and an unfocused run of
one file still read MATCH under `diff`, which is what `refocus` needs next
slice). A LINE naming a frame that has closed, or that no CALL opened, is a
conversion refusal naming the record — never a row on a guessed frame (Rust's
A6). `_on_call` writes `{"args": a}` without `unread` when the record carries
`a`.

### 3.8 The runtime surface the transform emits

```js
const __sf=__srt.call(__sfile,<idx>,["key",key,"n",n]);   // focused: an args array
__srt.line(__sf,<line>,["a",a,"b",b],["y"]);               // after a statement; ["y"] only when non-empty
__srt.line(__sf,<line>,[]);                                 // a statement that wrote nothing
```

`line` is inert when the tier is not `call`, when `f` is null, or when the
frame has closed. `call`'s third argument is optional and absent on every
unfocused site, so an unfocused file's output is byte-identical to 0.2.0's.

### 3.9 What stays outside, declared

Place writes and `delete`; `this`; a conditional assignment's write-or-not;
a `switch` discriminant's assignment and a falsy `if` head's;  statements in a nested function that is
not itself under the focus; `eval` and `new Function` bodies; module-level
code (never a frame); `with` (not in modules). Each is a numbered blind spot
(§6.4). Volume — a hot loop under focus writes one row per statement per
iteration — is accepted as Rust accepted it: the focus is the budget the
reader chose, and E12 H7 reports the cost.

## 4. The query side (section 3, approved)

### 4.1 One `dbg` kind, two dialects

A `dbg` capture is the recorder's own formatter's text. The readers parse it
as Rust's `Debug` (`query/rust_debug.py`, A11's read/write pair); the
TypeScript recorder writes `util.inspect`. So:

- `vocab.Terms` gains **`dbg_dialect`**: `"rust"` for Rust, `"inspect"` for
  TypeScript, `None` for Python (whose captures are typed, never `dbg`).
- A new module `query/dbg_dialects.py` maps the word to a read/write pair:
  `rust_debug.read_debug` / `debug_text` unchanged, and a new
  `query/js_inspect.py` with `read_inspect` / `inspect_text`.
- `expr.resolve(v, dialect)` and `flow_values.matches(cap, target, dialect)`
  take the pair; `watch` and `flow` pass what `terms(trace)` names. No
  `lang` branch in either command (design 2026-09-06 §4.1's discipline).

**The spellings, measured** (node v24.16.0; `depth: 2, maxArrayLength: 8,
maxStringLength: 100, breakLength: Infinity, compact: true`):

| value | text |
|---|---|
| `"abc"` / `"it's"` / both quotes | `'abc'` / `"it's"` / `` `it's "x"` `` |
| `"a\nb\tc\\d"`, `"café"` | `'a\nb\tc\\d'`, `'café'` |
| `undefined`, `null`, `true`, `false` | the bare words |
| `5`, `-5`, `2.5`, `1e21`, `1e-7`, `-0`, `NaN`, `Infinity`, `-Infinity` | `5`, `-5`, `2.5`, `1e+21`, `1e-7`, `-0`, `NaN`, `Infinity`, `-Infinity` |
| `123n` | `123n` |
| `[1, 2]`, `[]`, `{a: 1, b: "x"}`, `{}` | `[ 1, 2 ]`, `[]`, `{ a: 1, b: 'x' }`, `{}` |
| a function, a class, an instance | `[Function: foo]`, `[class Foo]`, `Foo { x: 1 }` |
| `Map`, `Set`, `Symbol`, a `Date`, a `RegExp` | `Map(1) { 'a' => 1 }`, `Set(1) { 1 }`, `Symbol(s)`, `1970-01-01T00:00:00.000Z`, `/a+/g` |
| a string past 100 characters | `'xxx…'... 50 more characters` |
| an array past 8 items | `[ 0, 1, 2, 3, 4, 5, 6, 7, ... 4 more items ]` |
| an `Error` | `Error: boom\n    at …` (its stack; the 200-byte cap cuts it) |

**Reading** (`read_inspect`): a text in `'…'`, `"…"` or `` `…` `` is the
string with JavaScript's escapes undone; a quoted text followed by
`... N more characters` reads **TRUNCATED** — a prefix, never compared, the
rule a clipped `str` already has; every numeric spelling above is a number
(`-0` is `-0.0`, `NaN`/`Infinity` the floats); `123n` is an `int`; `true`
and `false` are bools; `null` is `None`; `undefined` is a new marker
`UNDEFINED`, equal only to itself; anything else is the text as a `_DbgText`,
so `x == '[Function: foo]'` compares text as Rust's struct text does.

**Writing** (`inspect_text`, for `flow --value`): the inverse over the
literal domain — `None` → `null`, bools → `true`/`false`, a string → JS's
quote choice and escapes, a number → **JavaScript's `Number.prototype.
toString` rules** (shortest round-trip digits, exponent form beyond `1e21`
and below `1e-6`, an integral float printed as its integer). So `flow
--value 5.0` sights a `5`: in JavaScript `5.0` IS `5`, the opposite of Rust's
A12, and `docs/query.md` says so. A string that would exceed 100 characters
is written with inspect's own tail and therefore matches nothing, since the
capture is TRUNCATED on the other side.

**Pinned by generation.** A node fixture (`typescript/test/fixtures/
inspect-table.json`, regenerated by a script, committed) holds the measured
table; `tests/test_js_inspect.py` asserts `read_inspect(inspect_text(L)) == L`
for every literal `L` a command accepts and reads every row of the fixture
as the table says. A11's property, in the second dialect.

### 4.2 The predicate language

`expr.py` reads four names as constants: `null` → `None`, `undefined` →
`UNDEFINED`, `true`/`false` → bools. Language-neutral: `x == null` on a
Python trace compares with `None`, as `x == None` does. `UNDEFINED` in
arithmetic raises `EvalError` (not a number); `len(undefined)` is
`NO_LENGTH`. A program local spelled `null`, `undefined`, `true` or `false`
is shadowed by the constant — declared, and pinned by vector v35.

### 4.3 One site spelling for `--at` and `--focus`

`watch_cmd.site_matches` learns the file's basename and root-relative path
beside the stem and the dotted module, so every `--focus` spelling of §2.1
is an `--at` spelling: `refresh`, `cache:refresh`, `cache.ts:refresh`,
`src/lib/cache.ts:refresh`. The JS matcher and the Python one are two
implementations of one rule, pinned by one example table
(`typescript/test/fixtures/site-spellings.json`) that a JS test and vector
v39 both read.

Every printed site of a code object — `watch`'s no-match listing, the
re-record guidance, `flow`'s resolution note — spells it through a vocab
field **`site_spelling`** (`"module"` for Python, `"stem"` for Rust, `"rel"`
for TypeScript) and one helper, `query/sites.py:spell_site(trace, code)`.
Python and Rust output does not move.

### 4.4 What `watch` says when it cannot

`watch_cmd.refocus_cmd` — the *refocus and re-run:* guidance — becomes a
vocabulary template, **`rerun_command`**, instantiated with the trace's own
meta: for Python `cd {cwd} && sensorium run --focus {specs} -- {argv}` (what
it prints today); for TypeScript `cd {cwd} && sensorium ts run --focus
{specs} -- {command}` with `{command}` = `meta.harness_command` as typed and
each spec spelled `rel:qualname`; for Rust `cargo sensorium --focus {specs}
{cargo_args}` — which also closes a latent leak, since today a focused Rust
trace whose matched frames ran no LINE would be told `sensorium run --focus`.
The two `TYPESCRIPT` strings that name "S5 rung 3" (`no_rerun_note`,
`timeline_hint`) are rewritten: the timeline hint names the `ts run --focus`
command with the frame's own site; the no-rerun note says `refocus` is not
yet this recorder's and names the same command. The E7 needle
`sensorium run --focus` keeps guarding the Python spelling on TypeScript
output.

### 4.5 Readers that change by themselves

`frame` prints `args: key='rate'` and a timeline; `tree` prints
`refresh(key='rate') -> 100` for a focused frame and `<unread: locals>` for
the rest; `grep --kind LINE` lists rows; `info`'s declaration block flips
`line` and `locals` and prints `focus:`; `exceptions`, `diff` and `runs` are
untouched. Each is pinned by a corpus case, not by a code change.

## 5. Object identity (section 4, approved)

### 5.1 What the runtime mints

`dbg()` gains two keys for a value of type `object` or `function` (`null`
excluded): **`oid`**, a serial from a `WeakMap` minted once per object and
never reused — the same shape `serialOf` keeps for thrown objects, its own
map and counter — and **`type`**, the constructor's name through the ladder
`exc()` already uses (`unread` when the object lies). On every capture: a
RETURN value at the call tier, and under a focus the `args` and `deltas`. A
primitive carries neither. `sensorium-ts 0.3.0` therefore declares
**`object_identity: true` unconditionally**: an identity exists for every
object the recorder ever captures, focused or not.

### 5.2 What `flow --object` does with it

- `flow_values.matches(cap, ObjTarget)` accepts a `dbg` capture carrying
  `oid` and `type`, beside the container kinds; `resolve_object` stops
  calling such a value "a primitive … use `--value`".
- The header's caveat is CPython's, so it moves behind a vocab field
  **`identity_basis`**: `"address"` (Python, the existing `IDENTITY_CAVEAT`
  lines) or `"serial"` (TypeScript). On a serial basis the header reads
  *identity is a per-object serial minted once and never reused, so every
  sighting is the same object*; the gap analysis (address reused, new
  object, spanned by, unwitnessed) does not run, because there is nothing to
  corroborate; the continuity line reads `continuity: exact (serial
  identity)`.
- Rust stays `object_identity: false`, untouched (design 2026-09-06 §4.2).

Stated in `docs/query.md`: on a TypeScript trace `flow --object` is exact
identity, stronger than Python's, and an inspect text that changes between
two sightings of one serial is the mutation itself.

### 5.3 What it costs and what it declares

One `WeakMap` write per first capture of an object; two keys on the wire.
RETURN renderings do not move (`fmt_value` ignores the keys), so no corpus
answer changes except the declaration block and the recorder version in
refusal sentences, which 0.3.0 re-pins anyway. `corpus/typescript/
object_refused` becomes **`object_identity`**: the same planted aliasing
(`loadSettings` returning the shared defaults, `tune` mutating them), now
answered by `flow --object loadSettings:return` — both returns and the
downstream argument under one serial. HONESTY gains an identity promise and
one blind spot: **sightings are top-level captures only**; an object that
appears inside another's inspect text has no serial of its own, where
Python's `_walk` over samples finds nested identities.

## 6. Versions, ceilings, docs, and T0 (section 5, approved)

### 6.1 Versions

| what | from | to |
|---|---|---|
| `sensorium-ts` | 0.2.0 | **0.3.0** — LINE record, `a` on a focused CALL, `oid`/`type` on captures, `line`/`locals`/`object_identity` declarations, the resolver |
| Python `sensorium` | 0.11.0 | **0.12.0** — `ts run --focus`, resolution, LINE conversion and `args`, the inspect dialect, predicate constants, site spellings, serial identity, vocab fields |
| `TRACE_FORMAT` | 4 | **4** — LINE rows, `focus`, `focus_matched`, `oid` and `type` all exist in the contract; only their TypeScript reading is new |

Every refusal sentence that names `sensorium-ts 0.2.0` is re-pinned at
0.3.0 (`watch_refused`, the vectors that carry the version, HONESTY's pin
table).

### 6.2 Ceilings, and where the prose goes

- `docs/TRACE-FORMAT.md` is at 781/800. It gains one sentence on each of
  three rows — LINE (*for `lang = typescript` see TYPESCRIPT-KEYS*), CALL
  (`args` under a focus), the capabilities table (`line`/`locals` true under
  a focus; `object_identity` true for `sensorium-ts` ≥ 0.3.0, a serial never
  reused) — and nothing more. `docs/trace-format/TYPESCRIPT-KEYS.md` (129
  lines) holds the TypeScript reading in full: no parameters row, the deltas
  table, `unbound` at block exit, the inspect dialect and its table, serial
  identity, `focus`/`focus_matched`.
- `typescript/HONESTY.md` is at 799. Its §9 (Cost, ≈140 lines) moves whole to
  `typescript/HONESTY-COST.md` on the blind-spots precedent, in a commit
  before any promise is added; the new promises land in the room that makes.
- `CHANGELOG.md` is at exactly 800. The oldest sections move to
  `CHANGELOG-ARCHIVE.md` as a pure move, in a commit that lands BEFORE the
  release entry is appended — the file's own rule, the third cut.
- `typescript/src/transform.mjs` is at 765. The test-file and task-boundary
  code (`isTestFile`, `isTypeOnlyImport`, `calleeChain`, `isLiteralTitle`,
  `spliceTaskBoundary` and their constants) moves to `typescript/src/
  tasks.mjs` before a focus splice is written, as `escape.mjs` was carved out
  at rung 2. `rt.mjs` (705) takes `line` and the args branch of `call`
  (≈40 lines) and stays under; `flow_cmd.py` (742) takes the serial-basis
  branch (≈30 lines) and stays under — if it would not, the branch lives in
  `flow_values.py`; `watch_cmd.py` (633), `expr.py` (511),
  `vocab.py` (505), `build.py` (525) have room.

### 6.3 T0 — the rung-3 debts, closed or named before any new line

- **`e7_report.py`** writes its needle-rule header to a sibling file
  (`<transcript>.rules`) and leaves the transcript it was handed untouched,
  so a second run cannot prepend a second header over a pinned sha.
- **`Shape.site`** becomes a required argument of `exceptions_group.Shape`;
  every hand-built `Shape` in the tests passes it; the `key[1]` fallback is
  deleted.
- **The fence pattern.** `e_fences.py` names the real Python reader tests
  (`tests/test_exceptions.py`, `tests/test_exceptions_synthetic.py`) and
  refuses, at exit 2 with the pattern printed, any pattern that matches no
  file — a fence over an empty set is not a fence.
- **The journal.** The hashed set for E12's store names `traces/*.db`, the
  spool's `*.jsonl` AND `invocations.jsonl`, with a pre-registered expected
  delta on the journal of exactly one line per pre-registered read command,
  checked by the assembler.
- **Named, not closed** (stay in CARRIED-DEBT): `Index.left_frame`'s window
  reading; the two reason variants unmeasured on a lens; the `lens.stamp`
  wiring of the three legacy assemblers; `test_acceptance_scripts.py` (324
  lines) watched.

### 6.4 Contract and ledger amendments

- `typescript/HONESTY.md`: a new section, **§11 *Under a focus***, placed
  between §10 and the index, holding the promise — *Under a
  focus, one LINE per completed statement of a focused function, its
  `deltas` the bindings that statement wrote and nothing else, a guarded
  body's head names as its first row, the block-scoped names a block-like
  statement declared listed `unbound` on its row; the CALL of a focused
  function carries its arguments* — with falsifiers E12 H3/H4 and the corpus
  cases of §7; and the identity promise of §5.3. The §7 "declared absent"
  paragraph is rewritten: `locals` and `line` true under a focus,
  `object_identity` true.
- `typescript/HONESTY-BLIND-SPOTS.md`: items **28–34** — place writes and
  `delete`; `this`; a conditional assignment's write-or-not; a `switch`
  discriminant's assignment; a falsy `if` head's assignment; identities
  top-level only; a nested function outside the focus prefix is call-level
  only.
- `docs/CARRIED-DEBT.md`, this rung's section, *deferred*: the Rust
  fold-without-`unbound` debt (§3.4), named as Rust's, not closed here.
- `docs/query.md`: TypeScript notes under `watch` (`--at` spellings, the
  constants), `flow` (`--value 5.0` sights `5`; `--object` exact), and the
  re-record guidance.
- `docs/corpus.md` / `corpus/typescript/README.md`: the ten cases, the
  `record: {focus}` key on a vitest case.
- `docs/CARRIED-DEBT.md`: this rung's section at merge — settled, deferred
  by ruling, process lessons — with the rung-3 items struck where they stand.

## 7. The corpus (section 6, approved)

A vitest case gains the Python recorder's own key, `record: {focus: [...]}`
(`corpus/cases.py` admits it on `program: vitest`; still refused on cargo);
`run_corpus._record_vitest` turns each entry into `--focus <entry>` before
the `--`. Ten new cases under `corpus/typescript/`, one rule each, byte-exact
answers and exits:

| case | pins |
|---|---|
| `focus_let_chain` | a `const` chain: one row per statement and none for the tail; `watch --at fill --expr b == 2` SATISFIED at the row that wrote it, the CALL counted as a site; `frame`'s timeline |
| `focus_loop_counter` | `for (const v of xs) { total += v }`: the per-iteration head row carrying `v`, `total` per write, `flow --value 3`, and the loop statement's own row with `unbound: v` |
| `focus_block_scope` | a `const y` inside an `if`: `watch --expr y == 1` hits inside the block and not at the site after it — the case whose Rust twin cannot exist |
| `focus_destructure` | `const { a, b: [c] = [0] } = obj` binds `a` and `c`; a rest element; `let x;` binds `undefined` |
| `focus_args` | one run, two functions: the focused one's `tree` line prints its arguments (a destructured and a defaulted parameter included); the other keeps `<unread: locals>` |
| `focus_async` | an `async` function under focus: rows on both sides of an `await`, `~ YIELD` and `~ RESUME` between them in the timeline |
| `focus_catch_binding` | `catch (e) { count += 1 }`: HANDLED, then the catch block's entry row carrying `e`, then the try statement's row with `unbound: e` |
| `focus_place_write` | `state.x = 5` records a row with empty deltas: the blind spot pinned as a present row and an absent delta |
| `focus_container` | `--focus Fog` selects `Fog.compute` and `Fog.render`; `--focus fog.ts:Fog` the same; `info` prints `focus:` and what matched |
| `flow_value_inspect` | `flow --value 5.0` sights a `5`; `flow --value "'A1'"` sights `'A1'`; a string past 100 characters never matches; `watch --expr x == null` and `y == undefined` |

Re-pins: `watch_refused` stays the unfocused refusal at 0.3.0;
`object_refused` becomes `object_identity` (§5.3). The resolver's exit-2
refusal is not a corpus question — a case records once — and is pinned by
`tests/test_ts_driver.py` over a fixture project and by
`typescript/test/resolve.test.mjs`. Every existing TypeScript case is
re-collected under 0.3.0; only declaration blocks and version strings may
move, and the collector says which.

## 8. Acceptance — E12, pre-registered (section 7, approved)

Record: `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md`
(dated by the day §1 locks; a later lock day renames it and §15 says so).
**§1 is committed alone and byte-locked** (`awk '/^## 1/,/^## 2/' |
sha256sum`) before the transform can splice a probe, the runtime can write
one, or the driver can resolve a spec; the runner refuses to start unless
the range is byte-identical to the locking commit. A dated amendment inside
§1, if any, is committed alone and adds a second sha, as rung-4 E9 did.

**The lens** is the VTT frontend copy at `0091e97` already named by
`typescript/acceptance/LENS.txt`, read-only for the whole run. **The store**
is a fresh directory under `/mnt/extra/sensorium-s5/`, named by the rung
and reached by label from the runner's environment, never by path in a
committed file. **The subject** is one test file, `src/lib/diceQueue.test.ts`,
and three pure functions of `src/lib/diceQueue.ts` chosen by reading the
source: `parseDiceGroups` (line 68: a `while` head assigning `m`,
per-iteration consts, an `if` block), `forcedDiceFromSource` (line 127: early
returns, a nested `for…of`, `+=`) and `buildDiceQueueEntry` (line 194: a
destructuring `const`). **Two runs**: U, `sensorium ts run -- npx vitest run
src/lib/diceQueue.test.ts`; F, the same under `--focus diceQueue.ts:<each of
the three>`.

| id | question | endpoint, both readings pre-committed |
|---|---|---|
| H1 | does an unfocused run stay unfocused? | U: `capabilities.line = false` and `locals = false`; LINE rows = 0; `watch U --at parseDiceGroups --expr groups == 0` prints `REFUSED: watch needs line, which recorder sensorium-ts 0.3.0 declares it does not produce (capabilities.line: false); nothing was checked`, exit 3. Second reading: the version token is `trace.recorder` as §2 records it |
| H2 | does a focus resolve and run? | the resolver's output names exactly three sites, `src/lib/diceQueue.ts:<each>`; F's vitest pass/fail counts equal U's, beside each run's exit status. A focused file that fails to load, or a suite whose counts move, is a **STOP** — no fallback, no narrower focus |
| H3 | one LINE per completed statement? | the FIRST activation of `parseDiceGroups` in F carries **N** LINE rows, N hand-counted in §1.1 line by line under §3.1–3.4 of this design, head rows and `unbound` lists written beside each; **N = PASS**; any other count a STOP with the diff of lines. Second reading: the rows' `line` values equal §1.1's list in order |
| H4 | does `watch` answer? | three triples (`--at`, `--expr`, verdict word + exit) written in §1.2 from the source under §4.1–4.2, at least one over a head row's binding and one over an `unbound` name after its block; all three as predicted → PASS. A verdict/exit disagreement is a finding about `Verdict`/`STATUS`, reported |
| H5 | does `flow --value` see it? | two sightings (literal, name, line) predicted in §1.3 among the three functions' LINE deltas, both found and no unpredicted sighting there → PASS; sightings elsewhere in the trace (RETURN values, other files) reported beside, not gated |
| H6 | is identity exact? | `flow --object e<id>:dice`, where `e<id>` is the first LINE row of `forcedDiceFromSource` carrying `dice` in F — a lookup step written in §1.4 (`grep F dice --kind LINE`, first row of that qualname), not a number, since an event id cannot exist before the run; the endpoint is the count and the serial: exactly two sightings — that row and the destructuring row in `buildDiceQueueEntry` — one serial, `continuity: exact`; second reading: the two sightings' `type` both `Array` |
| H7 | what does it cost? | F against U, the test file's wall, n=3 each, interleaved, medians, under the slice-2 load guard (`e6pp.sh`'s); the resolver's wall beside it; **reported, not gated** |
| H8 | did nothing else move? | every corpus case equal (Python, Rust, TypeScript, the ten new ones included); the Python suite, `cargo test --workspace`, the Node tests and the probes green; E7's needle grep at 0 over every transcript this rung prints |

**Lens sentence.** Values are read under §4.1; N uses §3.1–3.4's
definitions; a site is a `watch` site under `watch_cmd`'s own CLAIM. Measured
once; a `.FAILED` before any number is infrastructure (relaunch from zero,
archived); after a number it is a STOP.

**Instruments** (`typescript/acceptance/`, rung 3's discipline): every script
sources `bin.sh` and resolves `<repo root>/.venv/bin/sensorium`; every cell is
`{value, lens, dropped}` through `lens.py`; `e_fences.py` names real files
(§6.3); the assembler `assemble_rung4.py` verifies the hashed set — `traces/
*.db`, spool `*.jsonl`, `invocations.jsonl` with its pre-registered delta —
after every read; the E7 reporter writes its header to a sibling file. The
store-rung2ts directory (6.2 GB) is not read by this rung and may be freed
once E12's §1 is locked — Brice's call, named in the ledger.

## 9. Testing story

- **Transform** (`typescript/test/transform.test.mjs`, `bindings.test.mjs`,
  new goldens under `test/golden/focus/`): every row of §3.2's table as a
  golden; the probe after a block-like statement; the per-entry row inside
  every guard form; `unbound` lists; a focused `async` body; nested
  functions under and outside the prefix; the args array with destructured,
  defaulted and rest parameters; an unfocused file byte-identical to 0.2.0's
  output (a golden that must not change). Every golden parses under the
  consumer's TypeScript after splicing (`sites.probe` precedent).
- **Matcher and resolver** (`focus.test.mjs`, `resolve.test.mjs`): the
  spelling table fixture; container selection; the refusal, `Closest:`, and
  the excluded-only refusal; the `\x1f` join.
- **Runtime** (`rt.test.mjs`): `line` inert off-tier / no frame / closed
  frame; a LINE inside a parked-and-resumed frame; `oid` stable across two
  captures of one object and distinct across two objects; a primitive
  carries none; `type` for a lying constructor.
- **Converter** (`tests/test_ts_ingest*.py`): `_on_line` rows; `args` on a
  focused CALL; the closed-frame refusal; `focus`/`focus_matched` meta;
  capabilities through BOOT.
- **Driver** (`tests/test_ts_driver.py`): `--focus` parsing before `--`;
  the resolver invoked before the mint; the refusal with nothing left
  behind; `invocation.json`'s two keys.
- **Readers**: `tests/test_js_inspect.py` (the generated table, the
  round-trip), `test_expr.py` (constants), `test_watch.py` (`--at`
  spellings, `unbound` fold on TS rows, the re-record template),
  `test_flow.py`/`test_flow_identity.py` (serial basis, `dbg`+`oid`
  matching, no gap analysis), `test_vocab.py` (the four new fields on all
  three columns, completeness).
- **Vectors** v35 (predicate constants), v36 (a TS LINE row and a focused
  CALL in `frame`/`tree`), v37 (serial identity in `flow --object`), v38 (the
  inspect dialect: `watch` and `flow` agree on one capture), v39 (site
  spellings). Every vector is mutation-tested before it counts.
- **Corpus**: §7, collected under 0.3.0; the collector compares whole lines.
- **Probes** (`typescript/probes/src/focus.probe.test.ts`): one marker per
  §3.2 row on real vitest, so a rule pinned by a golden is also seen to run.

## 10. Order of work

0. **T0** — §6.3's debts; `CHANGELOG.md` cut; HONESTY §9 → `HONESTY-COST.md`;
   `transform.mjs` → `tasks.mjs` split; E12 record §1 written and locked
   ALONE (the hand count, the triples, the sightings, the object spec, the
   hashed set) — before any of the below exists.
1. **Runtime and wire** (`sensorium-ts` 0.3.0 bumped here): `line`, the args
   branch of `call`, `oid`/`type`, the capability declaration from the
   environment.
2. **`bindings.mjs`, `focus.mjs`, the transform splices, goldens, probes.**
3. **`resolve.mjs`, the driver's `--focus`, plumbing, artifacts.**
4. **Converter**: rows, args, meta, capabilities.
5. **Readers**: `js_inspect.py`, `dbg_dialects.py`, vocab fields, `expr`
   constants, `site_matches` and `spell_site`, `rerun_command`, the serial
   basis in `flow`; vectors v35–v39.
6. **Corpus**: the ten cases, the two re-pins, the `record` key; every TS
   case re-collected.
7. **E12 measured** — every endpoint once; the record's §2–§5 written from
   the cells; STOPs stand where they fire.
8. **Docs and versions** (Python 0.12.0): TRACE-FORMAT's three sentences,
   TYPESCRIPT-KEYS, HONESTY and its blind spots, query.md, corpus docs,
   CARRIED-DEBT's section, CHANGELOG entry; the `debugging-typescript-with-
   sensorium` skill written from the corpus's own commands.
9. **Final review** (fable), one fix wave, PR. Merge is Brice's.

Subagent-driven, as rungs 2 and 3 were; the ledger under `.superpowers/sdd/`
in the worktree, archived to `/mnt/extra/sensorium-rung2/sdd-archive/` at
close.

## 11. Decisions, with what each costs if wrong

| # | decision | cost if wrong |
|---|---|---|
| D1 | focus decided at transform time (Rust F2) | a runtime switch would probe every function and move the call tier's cost; nothing here can be flipped without re-transforming, which every run does anyway |
| D2 | resolve before the run, refuse at exit 2 | the resolver parses every eligible file once per run (reported); the alternative wastes a 25-second run on a typo |
| D3 | deltas = bindings written, statically (Rust F3) | place writes invisible (declared); a snapshot-diff would see them at scope×statements cost and Python-spelled renderings |
| D4 | args on the CALL, no parameters LINE | N differs from Rust's by one row per activation; the contract says which language does which |
| D5 | `unbound` on the block-like statement's own row | no extra rows, so N stays the statement count; a name that dies with an unwinding frame needs no `unbound` because no later site reads it |
| D6 | per-entry rows for every guard form that binds or assigns, `if` included | one uniform rule; a `switch` discriminant is the declared exception |
| D7 | async and generator bodies probed | a probe after an `await` runs in the resumed continuation — the frame is back on its stack by then (`r` pushes before the probe); a LINE on a parked frame would be a converter refusal, which H3 would show |
| D8 | one `dbg` kind, two dialects through the vocabulary | a third recorder brings a third pair or reuses one; no reader gains a `lang` branch |
| D9 | `null`/`undefined`/`true`/`false` as predicate constants everywhere | a Python local named `null` is shadowed (declared, v35); the alternative is a language switch inside a language-neutral expression parser |
| D10 | serial identity, `object_identity: true` unconditionally | two keys per object capture on every RETURN; the payoff is an exact `flow --object` and one corpus refusal turned into an answer |
| D11 | the string cap stays inspect's 100 characters inside the 200-byte cap | a long string is TRUNCATED to `watch` and unmatchable to `flow`, as a clipped `str` is; raising it is a measured slice, not a default |
| D12 | wire stays 1 | an older converter refuses a LINE by name; a 0.2.x spool converts under 0.12.0 unchanged |

## 12. Rulings from Brice (this brainstorm, 2026-09-11)

- The next sensorium slice is the focus tier on TypeScript, chosen over a
  debts-only slice, refocus, and the browser substrate; the rung-3 debts
  fold in as T0.
- Approach 1 (Rust's design, JS-shaped) over Python's snapshot-and-diff and
  an arguments-only tier; object identity, the predicate constants and the
  skill ride along.
- Sections 1–7 of the brainstorm approved in turn, as §2–§8 record them.
- Owed at the close, Brice's: the merge; freeing `store-rung2ts` (6.2 GB).

## 13. The pre-registration, in one table

| id | gate value | rule |
|---|---|---|
| H1 | `line`/`locals` false, 0 LINE rows, the 0.3.0 refusal at exit 3 | all → PASS |
| H2 | three sites resolved; F's counts = U's | equal → PASS; a load failure or moved count → STOP |
| H3 | N rows on the first `parseDiceGroups` activation, N from §1.1 | equal → PASS; else STOP with the diff |
| H4 | three predicted (verdict, exit) pairs | 3/3 → PASS |
| H5 | two predicted sightings, no unpredicted one in the focused deltas | both → PASS |
| H6 | two sightings, one serial, `continuity: exact` | as predicted → PASS |
| H7 | F/U wall n=3 medians; resolver wall | reported |
| H8 | corpus equal, four suites green, needles 0 | all → PASS |

## 14. Risks named

- **A probe splice that breaks a shape §3.2 did not foresee** — a `for`
  head with a comma expression, a labeled block, an `export default` arrow,
  a `using` declaration. Caught by the goldens parsing under the consumer's
  compiler and by H2's STOP. A break is a finding, never a silent fallback
  to unfocused.
- **Volume** in a hot loop under focus: accepted; H7 reports it; a per-site
  cap is next-slice material if the number says so.
- **The JS number-to-string port** disagreeing with node on some float:
  caught by the generated round-trip fixture before any endpoint reads.
- **`unbound` on a statement an exception crossed**: the frame unwinds, so no
  later site reads the stale name; a throw caught inside the same frame lands
  on the `try` statement's own row, which lists the names. A caught throw
  inside a loop body whose `catch` is outside the loop ends the loop's
  statement, whose row lists the body's names. No shape leaves a dead name
  readable at a later site — H4's `unbound` triple is the measurement.
- **`this` unread** under focus surprises a method's reader: declared in
  the blind spots and in the skill; a later slice can capture it as a
  pseudo-argument if demand shows.

## 15. What changed against this design, and why

*Added 2026-09-12, at the rung's close. Nothing above is deleted; where a
sentence of this document was narrowed, replaced or falsified, this section
is the index to it. **§8's E12 table is carried verbatim into the record's
§1 and is byte-locked there** (`tests/test_acceptance_s5_rung4_lock.py`
recomputes the range's sha and the hand count's beside it) — no row below
touches it, and the one row that speaks to it (R37) is about what the
reading showed, never about what the pre-registration said.*

**P-rows** are the fourteen decisions the plan made before any code existed
(its own decisions table,
`../plans/2026-09-11-sensorium-s5-rung4-focus-tier.md`). **R-rows** are the
controller rulings made while shipping, in the order the ledger's `Ruling:`
lines carry them
(`.superpowers/sdd/2026-09-11-sensorium-s5-rung4-focus-tier/rulings-index.txt`).
Thirty-nine rulings were made; **six get no row here** and the reason is at
the end of this section, because a list that silently drops entries is a list
a reader cannot check.

### The plan's fourteen decisions

| # | What this document said, or left open | What rung 4 shipped, and why |
|---|---|---|
| P1 | §3.2's per-entry rule alone: a guard's head names arrive as a synthetic first row, and nothing says what the head wrote LAST | **Amended.** A guarded statement's own completion row also carries its head's ASSIGNMENT targets (declarations excluded — those are `unbound`), so `while ((m = re.exec(s)) !== null)` reports `m` on every entry row AND `m = null` on the `while`'s row. Without it the fold keeps the last matched array forever and every later site reads a value the program did not hold. It is also what **closes** §3.9's *"a falsy `if` head's"* declared gap: the `if`'s own row carries `x` whichever branch ran, so the shape is never numbered as a blind spot. N does not change. Measured as H3's row 9 (`m=null unbound:count,sides`). *Cost if wrong:* one delta per guard row. |
| P2 | §3.1 places a probe after each statement | **Amended.** A guard's non-block body (`if (c) x = 1;`, `for (…) stmt;`, `else stmt;`) is WRAPPED in a block whenever the function is focused, so the body's probe and the head row sit inside the guard. Appended after a bare body a probe would run unconditionally — Rust's A1, transferred. *Cost if wrong:* one synthetic block per bare body, invisible in the source map. |
| P3 | §3.1 says only that the probe follows the statement | **Amended.** The probe is registered with `prependRight(stmt.end, …)` **before** the statement's children are visited, and carries `terminatorFor`'s `;` when the statement has none: a descendant closer at the same offset — `await x` as a whole statement, whose suspension renders `),0))` — must land INSIDE the probe, and magic-string renders earlier-registered `prependRight` content rightmost. *Cost if wrong:* a syntax error the goldens catch under the consumer's own compiler. |
| P4 | §3.2 says "the names a statement writes" and §3.4 "the block-scoped names its inner blocks declared" | **Narrowed, deliberately.** `writesOf` excludes anything inside a nested function-like or class-member body, and `declaredIn` lists a block's DIRECT declarations only, never a nested block's. Rust §3.3's rule for closures; one row owns each name's death. The cost is blind spot 33. *Cost if wrong:* a nested arrow's writes would be attributed to the statement containing it. |
| P5 | §2.2's refusal is spelled `REFUSED: --focus <spec> matches no function under <root>; nothing was run. Closest: …` | **Amended.** The DRIVER's one refusal shape is kept — `error: --focus <spec> matches no function under <root>; nothing was run. Closest: a, b, c` on stderr at exit 2, one line per bad spec — not the `REFUSED:` prefix, which belongs to a capability refusal at exit 3. Every refusal `sensorium ts run` makes before spawning goes through `_refuse`; two shapes for one status would be the fault D8 exists to prevent. *Cost if wrong:* one prefix in a sentence no test of this rung reads twice. |
| P6 | §2.3: the plugin and the runtime read one variable | **Made concrete for the probes.** `typescript/probes/vitest.config.ts`'s DIRECT branch sets `process.env.SENSORIUM_FOCUS` from a `FOCUS` list beside the plugin call (eleven functions, the whole of `focus.probe.test.ts`'s exports), because the probe project has no driver to set it. **R25** records the consequence: `vite.mjs` reads the variable at plugin CONSTRUCTION, not at module load, which is why the assignment is a statement above `defineConfig` and is documented at `vite.mjs:19-25`. *Cost if wrong:* none — the hook reads at module load and both read once. |
| P7 | §4.1: a string over 100 characters "is written with inspect's own tail and therefore matches nothing" | **Corrected before it shipped.** A capture under the 200-byte wire cap carries `trunc: false`, so its text WOULD have equalled the spelled tail and a prefix would have been compared as a value. `inspect_text` returns **`None`** past 100 characters and `flow --value` sights nothing; `read_inspect` reads the `… N more characters` tail as TRUNCATED. A clipped rendering equals nothing, on both sides. The residue is blind spot 36. *Cost if wrong:* a prefix match reported as a sighting. |
| P8 | §4.3: `--at` prints the stem for Rust | **Not shipped as written.** `site_spelling` is `"module"` for Python AND Rust and `"rel"` for TypeScript; `--at` ACCEPTS the dotted module, the stem, the basename and the root-relative path in every language, which is additive and is what makes every `--focus` spelling an `--at` spelling. Rust's printed listing is `module_name_for`'s dotted spelling and is quoted in a CLOSED record; the design's `"stem"` would have moved those bytes for no gain. *Cost if wrong:* one column of one table. |
| P9 | §2.1's `rel:qualname` spelling, with nothing in meta to anchor it | **Added.** TypeScript meta gains **`root`**, the invocation's own, written unconditionally — a new TYPESCRIPT-KEYS row. Nothing else in meta carries it, and a reader on another box can re-anchor no `rel` without it. *Cost if wrong:* one always-present key. |
| P10 (with **R2**) | §4.1 gives `expr.resolve` and `flow_values.matches` a dialect | **Widened to a default.** `resolve(v, dialect=None)` and `matches(cap, target, write=debug_text)` keep their old behaviour when the argument is absent, and **R2** extends the same rule to `sites_for(trace, code_ids, wanted, dialect=None)` and `_bind(..., dialect=None)`. Only `watch_cmd` and `flow_cmd` pass a dialect; every existing caller and test keeps its call, and a caller that passes none reads Rust's table, which no Python trace ever reaches. *Cost if wrong:* one default per signature. |
| P11 | §4.2 adds four predicate constants | **Amended.** The constants are excluded from `Expr.names`, so `watch` never reports `null` as NEVER RECORDED. A constant is not a name the trace could have witnessed. *Cost if wrong:* one spurious warning per predicate. |
| P12 | §5.1: the `oid` serial is "the same shape `serialOf` keeps for thrown objects" | **Made explicit: two maps, two counters.** The `oid` counter and the exception `serial` counter are separate. They are two namespaces — `flow --object` against `exceptions` — and sharing them would let a thrown object's `serial` read as an identity in the other command. *Cost if wrong:* a cross-command collision with no error. |
| P13 | §8: H1–H6 read F and U; H7 is a cost arm | **Made one session.** H1–H6 read the FIRST U run and the FIRST F run; H7's arms are three of each, interleaved **U1 F1 U2 F2 U3 F3**, all six into the store — so the measured traces ARE cost-arm members and nothing is recorded twice for two purposes. *Cost if wrong:* one recording per purpose would double the lens's wall for no extra fact. |
| P14 | §9 requires the converter's tests to read a spool the RUNTIME wrote | **Made concrete.** The recorded converter fixture `focus-lines` is cut from the focus probe's own spool, sanitised by `tests/fixtures/ts-spools/sanitize.py`, with a hand-written `invocation.json` carrying `focus` / `focus_matched` — the probe being the one focused program that exists before the corpus does. *Cost if wrong:* a fixture nobody's runtime wrote. |

### The rulings that amended a section

| # | Section | What shipped, and why | Cost if wrong |
|---|---|---|---|
| R1 | §9 (the plan's T1 split) | `transform.mjs` exports **`terminatorFor`** beside `lineOf`; the plan named only `lineOf`, and `probe.mjs` consumes both. | one export |
| R6 | §8 (the record's §1.5) | §1.5 lists **thirteen** read commands, not twelve — the H1 `watch` refusal is a CLI read like the rest — and the journal's expected delta is the LENGTH of §1.5's list read from the record, never a literal. | one assembler constant |
| R8 | §8 (the record's §1.4) | H6's lookup names the first `dice` LINE row of `forcedDiceFromSource` **in the activation `buildDiceQueueEntry` called**; the seven earlier activations are the test's own. Made at T0, before any code existed — and measured right: the plain first-row reading would have picked `e101`, sighted once, and H6 would have STOPped on a correct recorder. | H6 reads the wrong row |
| R9 / R11 | §8, and the record's §2 | The one box path inside the locked §1 arrives inside this document's verbatim §8 block and is sanctioned by §1's intro; the fix was taken on the §2 side instead — every box path in §2's prose moved into §2's own pin table — so §1 was not reopened and the single lock sha stands. | one table grows by four rows |
| R10 | §3.1 | A block-like statement's row carries the statement's FIRST line (`lineOf(node.getStart())`), which is what makes the hand count's rows 8 and 9 read 75 and 72. | none |
| R12 | §8 (E-legacy) | `tests/test_exceptions_rust_grouping.py:697` — the `site=site` the plan's own `Shape.site` requirement forces — sits inside the fence glob, so E-legacy reads **1 of 2** with that line named in advance (§2.3 entry 2). The fence was not narrowed to make it pass. | one honest cell |
| R13 | §5.2 | `flow --object` requires `object_identity` and **not** `line`: an identity rides on every capture, so refusing through `line` would refuse a question the recording answers. `flow --value` keeps its `line` gate. | one gate, one corpus line |
| R14 / R36 | §5.3 | `corpus/typescript/object_refused` became **`object_identity`** as §5.3 says — but as the UNFOCUSED recording, with **three** sightings (two `loadSettings` returns and `tune`'s RETURN, where §5.3's table said `tune`'s argument). Accepted: it pins identity at the CALL tier, which is R13's point, and the case's third question still refuses through `line: false`. | one corpus case's prose |
| R15 / R16 | §3.2, §3.9 | A `LabeledStatement` is never wrapped (wrapping a labeled loop turns `continue label` into a syntax error) and mints **no row of its own**; its body statement is probed as usual. | one row per labeled statement in a future hand count |
| R17 | §3.2 | Type-only statements inside a focused body — `interface`, `type`, anything `declare`d — mint **no row**: they are erased before the program runs. An `enum` and a `class` DO, because they execute where they stand; a golden pins it. | an empty row per type alias |
| R18 | §3.4 | `using` and `await using` declarations are block-scoped, so `declaredIn` tests the `Let \| Const \| Using \| AwaitUsing` flags. Shipped in Task 3's fix round, `bindings.mjs` being that task's module. | a `using` binding kept alive by the fold |
| R19 | §3.2 | The heritage/computed-name walk applies to the `ClassDeclaration` **statement** form too — `class Foo extends (Base = f()) {}` reports `['Foo', 'Base']` — widening the brief's "ClassDeclaration → its name" by the same reasoning. | one line to revert |
| R20 / R27 | §9 (the probes) | `probes/check.mjs`'s `checkFocus` asserts BOTH contracts, keyed on the BOOT record's own declaration: `line: true` → every marker, `focus:args`, `focus:count`; `line: false` → zero LINE records in that file's container and no args on its CALLs, reported as `focus:mode unfocused`. A check that silently skipped would be a hole. **R27** adds a FOCUSED driver run of the probe project (eleven specs) beside the unfocused one, so both branches are exercised by a gated test. | one checker branch, one more vitest run |
| R21 | §3.2 | An `else` body is wrapped (P2) and gets **no head row** — §3.2's "an else branch is not an entry" — and the `if`'s own completion row carries the head's targets (P1). | one head row per else |
| R22 / R31 / R32 | §2.4, §4.5 | The transform's own count reaches meta as **`meta.functions_focused`** when the tally carries it, and `info` prints one line after `focus:` — `focus matched: <n> — …`, with `(<n> function(s) focused by the transform)` appended when the two differ. The line is gated on the meta KEY and never on `meta.lang`, so a focused **Rust** trace prints it too (R32), which is this reader's rule for every `info` line. This is the ruling the record's §4.2 says earned its place: without the parenthetical, `focus matched: 5` would have been the whole story and one instrumented function would have been invisible. | one optional meta key, one info line, one line on Rust traces |
| R23 | **§3.2's guard list** | A `DoStatement` gets **no head row**. Its test runs AFTER the body, so there is no entry the guard bound, and its test's writes reach the record on the `do`'s own completion row (P1). §3.2 lists `do { … } while ((m = …))` among the head-row guards; **that row is narrowed here** — a `do…while` is wrapped, never head-rowed. | one head row per do-loop iteration |
| R24 | §3.1 | A guard's BLOCK body mints no row of its own: the guard statement's completion row is minted at the same moment and `declaredIn` already reports the block's dead names there. A bare body is different — it is a statement inside a block the transform synthesised, and it keeps its row. | N gains one row per guarded block in a future hand count |
| R26 | §2.2 | `sitesOf` gains `excludedSites: {qualname, line, reason}[]`, so the resolver can say a spec *matches only functions this recorder does not instrument (`<reason>` x`<n>`)* rather than reporting it as a spelling mistake. The manifest shape is unchanged. | one field on an internal return value |
| R28 | §2.2 | The driver's refusal lines print the unmatched specs first, then the excluded-only specs, each group in the order the specs were given. Accepted as shipped. | a reader of two mixed bad specs sees them regrouped |
| R29 | **§2.2's `Closest:` clause** | Three Task-5 design calls: `<anonymous>` qualnames are never offered under `Closest:`, so **§2.2's "dropped only when the root holds no eligible function at all" gains a second case** — a root whose only eligible qualnames are anonymous offers no suggestions; an inherited `SENSORIUM_FOCUS` is cleared on an unfocused `ts run`; and `--focus ''` is refused by name. Beside them, §2.2's `files_scanned` counts **eligible** files, not every file walked. | none measured |
| R30 | §2.4 | `Resolution.matched_specs` returns `sorted(set(...))`: same-line anonymous twins share a qualname and would otherwise repeat `rel:<anonymous>` in `meta.focus_matched`. This is also why `focus_matched` (5) and `functions_focused` (6) differ on the lens. | a duplicated string in meta |
| R33 | §4.2 | `flow_values.parse_literal` accepts `null` → `None` and `true`/`false` → bools, so `flow --value null` sights a JavaScript `null` and a Rust `None` alike — the same words `expr.py`'s constants take. `undefined` stays unwritable and a BigInt is read but not written, both declared (blind spot 35). | three literal spellings |
| R34 | **§4.1's number rules** | The integral shortcut is gated at `\|x\| < 2**53`; above it the value goes through placement 1 over `Decimal(repr(m)).normalize()` digits, so `js_number` reproduces node at every magnitude, and `inspect_text`'s int arm sends an int of magnitude ≥ 2^53 through `js_number(float(n))` because JavaScript holds it as a double. Measured rows for `2**53`, `2**60` and `123456789012345680000` were added to the generated fixture. **§4.1's A11 domain claim is corrected by this row**: the round-trip domain is integers BELOW 2^53, and above it there is no distinct number to round-trip to. | two lines and three fixture rows |
| R35 | §8 (the record's §2.3) | Two re-pins of closed bytes are sanctioned and NAMED in the record's legacy cell rather than absorbed: `v23-lang-typescript-prose` (the brief mandates rewriting `timeline_hint`, which v23 pinned verbatim) and `object_refused`'s Q2/Q3 prose (sentences the sanctioned declaration flip made false; Task 8 rewrote the whole case). | two named diffs in the record |
| R37 | **§8's E12 reading** | The three STOPs stand as **findings** and nothing was re-run. **H2** is the pre-registration's own under-derivation: §2.1's container rule selects nested function-likes, and §8's subject paragraph predicted three sites by counting the functions a reader names. **H4** and **H5** are readings of `e12_report.py`, found after their numbers — a `while`'s head row and its completion row share a line, and a printed CALL row carries neither a bare qualname nor a line. The next slice re-registers H2, H4 and H5 under fixed instruments, on rung 1's E6′→E6″ precedent. | none — the record already says all of it |

### Two prose corrections to §4.1, and one to §4.1's table

Measured against node, not argued: node names `\n`, `\t`, `\r`, `\b` and
`\f` and **nothing else**, so a vertical tab is written **`\x0B`** in
uppercase hex and not `\v`, and every other control character, DEL and the
C1 block follow the same rule while U+2028 and U+00A0 are printable to node
and are not escaped at all. And inspect's quote ladder has an exception this
document's table does not show: a **`${`** anywhere in the text rules the
backtick out, so `it's "x" ${y}` is written `'it\'s "x" ${y}'` and not with
a backtick. Both came out of the generated fixture — 41 measured rows in
`typescript/test/fixtures/inspect-table.json` — which is what §4.1's
"pinned by generation" paragraph exists for: four of those rows would have
been guessed wrong.

### What the endpoints read, against what this document expected

§13's table held for five of eight and did not for three, and §3 of the
record is the reading. **H3 — the endpoint this design is about — PASSed on
its first reading**: N = 9, the lines 69, 70, 71, 72, 73, 74, 76, 75, 72,
every delta name and the one `unbound` list equal to a hand count written
before `bindings.mjs`, `probe.mjs`, the runtime's `line` or the converter's
`_on_line` existed, empty diff. **H1** 4/4 and **H6** 4/4 as written.
**H8** 6/6. **H7** reported: ×2.3816 on the median wall, the resolver 1.132 s
over **830** files (this document's §2.2 said 742 — a count of eligible files
that had moved on the lens; the measured number is the record's). **H2**,
**H4** and **H5** STOPped, R37 above.

### The six rulings with no row, and why

- **R3** (`rerun_command` returns `body.rstrip()`) changes no sentence of
  this document: it stops an empty command leaving a trailing space, and
  every real trace carries an argv, so the Python column's fenced bytes are
  unmoved.
- **R4** and **R5** are about WHEN a pin is re-touched, not about what the
  design says: at Task 2 the implementer re-pins any corpus line that moved
  only in the declaration block or the version token, and flips
  `object_identity` to true on vectors v30–v34 beside the 0.3.0 bump, so the
  corpus is green at every task and Task 8 re-collects everything.
- **R7** answers a review finding by pointing at §4.3 as written — the JS
  and Python spelling matchers are two implementations of one rule by
  design, pinned by one fixture — and amends nothing.
- **R38** corrects the RECORD's own §3 and §4.8 prose (which of H8's figures
  are cells and which are read from uncommitted suite logs, and §2.3 entry
  3's commit column), not this design.
- **R39** is about the GitHub repository description, which this document
  does not contain.
