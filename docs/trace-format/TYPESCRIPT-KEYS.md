# TypeScript-only meta keys (TRACE-FORMAT §4)

> Split out of `docs/TRACE-FORMAT.md` on 2026-09-09 (S5 rung 1) to keep that file under its 800-line ceiling, the same way §8's vector table was in 2026-09-04. Section numbering in TRACE-FORMAT is unchanged; that file's §4 is a pointer here.

Written by `sensorium ts ingest`'s builder (`src/sensorium/ts/build.py`,
`_meta` / `_container_meta` / `_invocation_meta`) and read by `info`,
`runs` and `Trace`. **Every one is printed only when the trace carries the
key**, so a TypeScript trace from an older converter simply says less —
never a zero, never "predates". Nothing here is required: the required set
is §4's, and it is the same for every language.

The keys divide by who knew the fact. The **invocation** keys are the
driver's and are identical on every trace of one `sensorium ts run`; the
**container** keys are one process's own; the **recording** keys are what
the conversion counted.

## Invocation — the driver's, identical across the invocation's traces

| Key | Meaning, and what reads it |
|---|---|
| `invocation` | The id of the `sensorium ts run` invocation this container belongs to. `runs` groups every trace of one invocation under a header naming the harness command (§6). |
| `harness` | `"vitest"` or `"node-test"` — the KIND of harness the driver recognised and wired. Not a program name: `node-test` is not a command. Which header `runs` prints is decided by `meta.lang`, never by this key being present (R27a). |
| `harness_command` | **The tokens the user typed after `--`**, before the driver consumed `--root`/`--config` out of them and before it re-issued its own: `["npx", "vitest", "run", "src/fog"]`. This is the one list here that is a COMMAND, and it is what `runs`' header and `info`'s `harness:` line print, joined by spaces (R26). Absent from a trace whose converter predates the key; the readers then fall back to `harness` + `harness_args`, which reconstructs a command nobody typed. |
| `harness_args` | The arguments **after** the harness word with `--root`/`--config` taken out, because the driver re-issues those itself (`ts/harness.Plan`). Machinery, not a command: nothing prints it where `harness_command` is present. |
| `harness_exit` | `{status, signal, basis}` — what the driver **waited for**, `basis` always `"waited"`. `status` and `signal` are exclusive. `runs`' header: `exit:1 (waited)`; `info`: `harness: vitest run src/fog  exit: 1 (waited)`. Absent when the driver was killed before the harness returned, which is not a harness that ended at 0. |
| `vitest` | The harness version, when one was read. `info` prints it in the parenthesis beside the interpreter: `node v24.16.0 (vitest 4.1.9, jsdom)`. |
| `driver_version` | The `sensorium ts` driver's own version. |
| `root` | The invocation's root directory, absolute, written unconditionally (plan P9). Every `rel` in this trace is relative to it — the fingerprint's paths, `test_file`, every `focus_matched` entry — and a reader on another box can re-anchor none of them without it. It is what `watch --at rel:qualname` and `sites.spell_site` resolve a root-relative spelling against; a trace that carried no root would fall back to the basename, which is still an `--at` spelling and claims no path this recording cannot support. |
| `focus`, `focus_matched` | The `--focus` specs **as they were typed**, and the `<rel>:<qualname>` of every function they selected, deduplicated across specs (R30). Two different facts, which is why both are kept: `focus` is what its author will recognise, `focus_matched` is what says whether the spelling meant what they thought — a spec that selected one function where its author expected three is invisible on the `focus:` line alone. **Written only where there was a focus**: no key at all is a run nobody focused, which is every unfocused TypeScript run, and `info` prints the two differently (`focus: -` for the absent key, `none` for a recorded empty list). |
| `files_transformed`, `transform_excluded` | How many files the transform edited, and `{reason: count}` for the ones it refused. `info`: `files: 41 transformed; excluded: 3 (vitest-hoisted-factory x3)`. **By reason, never a bare count**: the reasons are the difference between "nothing happened in that file" and "nothing was watching it". The GRAIN follows the harness: vitest transforms once for the whole invocation, so every container of it carries the same numbers; `node --test` runs one child process per test file, so a trace carries what its own container transformed. Absent when nobody counted, never written as a zero. |
| `functions_focused` | How many function-likes THIS container's transform spliced statement probes into (R22), from the same tally as `files_transformed` and written on the same terms — only where somebody counted, never as an invented zero. It is not `len(focus_matched)` and is not meant to be: the matched list is the INVOCATION's, keyed on `<rel>:<qualname>`, and two anonymous function-likes on one container share one qualname. `info` folds the number away when the two agree and prints it when they differ — measured 5 against 6 on the rung-4 lens, where `buildDiceQueueEntry`'s two default-parameter arrows are one qualname and two instrumented functions. |

## Container — this one process's own

| Key | Meaning, and what reads it |
|---|---|
| `pid`, `ppid` | Process identity within the invocation. `info`: `container: pid 4242 …`. |
| `thread_id_os`, `is_main_thread` | Node's own `threadId`, and whether this container is the harness's main process or one of its workers. `info` prints `thread 0 (main)` / `thread 3 (worker)`. Worth a word because it says what the absent thread record means here: a worker's siblings are **other traces of this same invocation**, unlinked. |
| `node` | The Node version string, read off the container's own boot record. `info`'s interpreter line is `node <node>`, where a Python trace's is `python <version>`. |
| `wire` | The spool protocol version the runtime wrote. Read by the spool reader; nothing prints it. |
| `environment` | The vitest environment (`node`, `jsdom`, …) where exactly one was seen. In `info`'s interpreter parenthesis. |
| `test_file` / `test_files` | The root-relative path of the one test file this container ran, or the list where a reused worker ran several. `runs` prints `file: <path>` or `files: N` in place of a `cmd:` (§6); `info` prints the same beside the container line and keeps the whole argv on its `cmd:` line. **Carrying neither is a statement**: this container ran no test file (a `globalSetup`, any `node --test` process) and keeps its argv. |
| `exit_self_reported` | `{code, signal}` — what the container said about its **own** ending, from inside, on the way out. `info`: `container exit: self-reported code 1 (nobody waited)`. Absent where the container never got to observe its own ending, which is not the same fact as one that ended at 0. Distinct from `harness_exit` (waited, another process) and from `exit_status` (§4: always null / `unwitnessed` here, because the driver spawned the harness and not its workers). |

## Recording — what the conversion counted

| Key | Meaning, and what reads it |
|---|---|
| `tests_seen` | How many tests the **harness** registered, counted by the setup file. `info`: `tests: 11 as tasks, 11 seen by the harness`, and names the shortfall when they differ — a test the transform did not wrap ran and was recorded by nothing, so a bare task count would read as the whole file. **Present only where the counter ran**: the spool carries a `SEEN` or a `FILE_START`, or the invocation was vitest, whose setup file always runs. `node --test` runs no setup file, so its traces carry no key and `info` prints `tests: N as tasks` alone — never a zero nobody measured. |
| `task_name_basis` | Which rule named this trace's tasks: the provider's (`vitest`), the lexical `describe > title`, or `mixed`. Printed as `; task names: vitest`. |
| `task_name_conflicts` | Provider names that did not end with the string literal the transform passed; the task fell back to its lexical title and the disagreement was **counted rather than resolved**. Printed beside the basis it qualifies — alone it would name no rule to doubt. |
| `unhandled_rejections` | `[{type, msg, serial}]` from `process.on('unhandledRejection')` — a fact with no SITE, so it is here and never in `events` (§5). `info` prints the count, **including a zero on a complete trace**: the listener always ran, so that zero is measured. |
| `throw_flow_outside_frames` | RAISE/HANDLED records that fired with no open frame — a throw at module scope, a default-parameter expression that threw before its frame opened. There is no frame to attach an event to, so none was written; the count is the only trace of them. Printed when non-zero. |

## Throw flow

> Moved here on 2026-09-10 (S5 rung 2) from `docs/TRACE-FORMAT.md` §5, unchanged — that file stood at 799 of its 800 lines and this rung amends this section, so it moves whole before it is amended.
> That is R25's precedent, the same way §4's key table moved into this file in rung 1: one commit moves a section without changing a byte of it, another edits it in its new home.

A TypeScript `exc` is `{kind, type, msg, serial}` and **`kind` is written on every
one** — `"throw"` or `"rejection"` — because a kindless `exc` is read as Python's
(TRACE-FORMAT §5). `serial` is minted per thrown **object** through a `WeakMap`, so
`catch (e) { throw e }` is one exception with two RAISE rows; a thrown **primitive**
has none to hang it on and gets a fresh serial each time, stated rather than papered
over by merging on text. Vectors: `v25-exc-kind-throw-rejection`,
`v27-unhandled-rejection-in-meta`.

**`how`** names the shape that recorded the event, and the enumeration is the
declaration — a shape outside it produced no record: `throw` (the RAISE a `throw`
statement writes when it fires); `catch` (the binding never left the clause, or
left it only as a `console.*` argument); `catch_escaped` (the binding left the
clause other than through a `console.*` argument). A **bare rethrow** —
`throw e;` at closure depth 0, whose operand after any parentheses is the
binding itself — is a traced EXIT and not a mention, so it does not make a
clause `catch_escaped`, and, by the same rule read over a rejection handler's
parameter, does not make one `catch_callback_escaped` either
(`.catch((e) => { throw e })` is `catch_callback`, while
`.catch((e) => { seen.push(e); throw e })` and `.catch((e) => { throw wrap(e) })`
stay `catch_callback_escaped`); the RAISE it writes carries the same serial and
the rule module reads the pair as a hop (amended 2026-09-10, spec §2.1). Then
`sink_empty_catch` (an empty
`catch {}` block); `catch_callback` (an inline rejection handler whose parameter
never left its body, or left it only as a `console.*` argument);
`catch_callback_escaped` (an inline rejection handler whose parameter left its body
some other way); `catch_callback_opaque` (a handler defined elsewhere);
`sink_empty_catch_callback` (an inline rejection handler with an empty body); and
`sink_finally_return` (a `finally` that completes with a throw in flight, whose
`exc` is the marked throw's own, COMPLETE — `kind`, `type`, `msg` and `serial`
exactly as the RAISE (or the synthetic marking clause) wrote them, nothing unread:
the mark holds the whole `exc` object, not just its serial. Two shapes are
declared blind spots instead (P1): a `try` that already has its own `catch`
clause gets no synthetic marking clause (only a catch-less `try` gains one,
`transform.mjs`'s `spliceFinally`), so an awaited callee rejecting inside that
catch's body, then a completing `finally`, records nothing — a *synchronous*
`throw` inside that same body is a `raise` and marks as usual; and `thr` (a
callee's frame closing by throw) sets no mark of its own, so a throw a callee
unwound with reaches the caller's mark only through the caller's own synthetic
clause, never any other way). What is still recorded by nothing: a
`finally` with no completion statement; `.finally(fn)`, never a handler;
a `Promise.reject(v)`, whose handler's HANDLED carries no RAISE and reads *born
outside a throw statement*; a throw inside a promise executor with no open frame,
counted in `throw_flow_outside_frames`; and a throw in untraced code (`JSON.parse`,
a library), whose HANDLED likewise carries no RAISE and reads *born outside traced
code*.

`sensorium-ts` 0.2.0 declares `capabilities.err_flow: true` in its BOOT record, and
the converter carries that declaration into `meta` over the constant it otherwise
writes (`src/sensorium/ts/build.py`). What the declaration guarantees is the
recorder's own statement that these rows now carry what a disposition verdict
needs. Reading them by rule is `src/sensorium/query/exceptions_typescript.py`'s,
and the refusal is gated on this key rather than on `lang`: a 0.2.0 recording is
JUDGED — five words, `swallowed` the only accusation among them
(`v30-exceptions-typescript-swallowed`, `v31-exceptions-typescript-escaped-ambiguous`)
— and a 0.1.x one refuses at exit 3 with the capability sentence, because what
it lacks is the record (`v32-err-flow-typescript-capability-refusal`). The
lang-keyed sentence that named absent TypeScript rules is retired.

Two things go to `meta` and never to `events`, because §3 refuses a causal event
with no `code_id` and inventing a code object would put a site in the program that
has none: an unhandled rejection (`unhandled_rejections`, `[{type, msg, serial}]`)
and a RAISE/HANDLED with no open frame (`throw_flow_outside_frames`).

## Under a focus

> Added 2026-09-12 (S5 rung 4, `sensorium-ts 0.3.0`). `docs/TRACE-FORMAT.md`'s
> LINE and CALL rows point here for `lang = typescript`; the grain is the
> contract's and the three differences from Rust's are below.

`sensorium ts run --focus <spec>` is a **transform-time** decision, so the
capability follows the recording and not the call: a focused run declares
`capabilities.line: true` and `locals: true`, an unfocused one declares both
false and writes no LINE record at all, and `watch`, `flow --value` and
`frame`'s timeline refuse the second by the declaration rather than answering
from an absence. A spec is `<qualname>` or `<file>:<qualname>`; the qualname
part is a **prefix on a `.` boundary**, so `Fog` selects `Fog.compute` — and
selects every function-like nested inside it, which is what makes a count of
sites a property of the source rather than of the names typed.

### The LINE row

One row per statement of a focused function **that completed normally**, at
the statement's own FIRST line (R10 — the probe's line is
`lineOf(node.getStart())`, so a block-like statement's row reads where the
statement opens, not where it closes). `deltas` is `{name: capture}` for what
that statement wrote and nothing else; `unbound` is present only when there
IS such a name. Empty `deltas` is a real row and says the line ran; empty
`deltas` WITH an `unbound` list is the ordinary shape of a loop's last pass.

| statement | `deltas` |
|---|---|
| `const` / `let` / `var PAT = e;` | every identifier `PAT` binds — nested object and array patterns, defaults, rest elements |
| `let x;` | `x`. JavaScript binds it to `undefined`, which is a write; Rust's deferred `let` binds nothing until assigned, and the two contracts differ here on purpose |
| `x = e`, `x += e`, `x ??= e`, `x++`, `[a, b] = [b, a]`, `({a} = o)` — at any depth in the statement's own expressions | the identifier targets, in source order, once each. A `\|\|=` / `&&=` / `??=` may not write at all; the row reports the binding's value after the statement either way |
| `a.b = e`, `a[i] = e`, `delete a.b`, `a.b++` | **none** — a place write, declared (blind spot 28) |
| an expression statement that writes nothing (`foo();`, `await p;`) | empty — the row says the line ran |
| a block-like statement completing (`if`, `for`, `while`, `do`, `switch`, `try`, a bare block) | empty, plus `unbound`; and, from plan P1, the assignment targets of its own HEAD — `while ((m = re.exec(s)) !== null)` reports `m = null` on the `while`'s row, which is the value every later site reads |
| a nested function's statements | **none of this function's** — `writesOf` stops at a function-like or class-member body; those statements are the nested function's own rows when it is focused too (blind spot 33) |

### Head rows, and which statements mint none

A guard that BINDS OR ASSIGNS as it enters mints a **synthetic first row
inside the body, at the head's line**, once per entry or iteration: `if`,
`for`, `for…in`, `for…of` and `while` — the five with a body and a test that
runs before it. A bare body (`if (c) x = 1;`) is wrapped in a block first, so
the head row and the body's own probe sit inside the guard.

Five shapes mint no row where a reader might look for one. Three mint no
HEAD row:

* **an `else` branch** (R21) — a falsy test entered nothing, so there is no
  entry to report; what the head WROTE reaches the record on the `if`'s own
  completion row (P1).
* **a `do…while` body** (R23) — its test runs AFTER the body, so an entry row
  would publish the previous iteration's test value dressed as an entry; the
  test's writes reach the record on the `do`'s completion row.
* **a `switch`** — no body to enter, so no head row at all, and its
  discriminant's assignment is reported nowhere (declared, blind spot 31).

And two mint no row of any kind:

* **a guard's BLOCK body** (R24). Its completion IS the guard's, and
  `declaredIn` already reports its dead names there; a second row would
  report one completion twice and pop the same names twice. A BARE body is
  different: it is wrapped in a block and probed as the statement it is.
* **a `LabeledStatement`** (R15, R16): it is a label and not a step, and it is
  never wrapped either (wrapping a labeled loop turns `continue label` into a
  syntax error). Its body statement is probed as usual.

**Type-only statements mint none either** (R17): an `interface`, a `type`
alias and anything `declare`d are erased before the program runs, so a row
would name a line that never ran. An `enum` and a `class` are NOT erased —
they execute where they stand — and both keep their row. So do the
completions' absences: `return`, `throw`, `break` and `continue` never
complete normally, and each one's exit is already the RETURN, the UNWIND or
the enclosing statement's row.

### `unbound`

A block-like statement's row lists as `unbound` the block-scoped names its
inner blocks declared and that just died: `let`, `const`, `class`, a `catch`
binding, a `for` head's declarations, and a `using` / `await using`
declaration (R18). `var` is function-scoped and is never unbound. A
per-iteration name is a delta again at the next iteration's head row, so no
`unbound` is minted between iterations. This is the key `watch`'s fold reads:
`sites_for` folds `deltas` forward and pops `unbound` at the same site, so a
`const` inside an `if` is in scope at the sites inside that block and at none
after it. Python emits `unbound` for `del` and the end of an `except … as e`;
**Rust emits none, and its fold keeps a dead block-scoped `let` alive** — a
Rust debt named in `docs/CARRIED-DEBT.md` and not closed here.

### Arguments are on the CALL, not on a LINE

A focused function's CALL carries `args: {name: capture}` in the Python
shape, captured at body entry — after defaults are applied, so a default is
the value the body saw, and a destructured parameter yields the names it
binds. An unfocused function's CALL in the very same recording still carries
`{"args": {}, "unread": ["locals"]}`, so `tree` prints
`helper() <unread: locals>` beside `total(items=[ 1, 2 ], member=true)`.
There is therefore **no parameters row**, and N for a focused activation is
the statement count: Rust mints a parameters row because its CALL cannot
carry args, and this is the difference `docs/TRACE-FORMAT.md`'s LINE row
points here for.

### The capture dialect: `util.inspect`, read one way and written one way

A `dbg` capture on a TypeScript trace is what node's `util.inspect` printed
under the recorder's own options — the same text a RETURN value has always
carried, now on arguments and deltas too. `watch --expr` READS it
(`read_inspect`) and `flow --value` WRITES it (`inspect_text`), and both live
in `src/sensorium/query/js_inspect.py` over one table, because an escape
undone in one and re-applied differently in the other reports a sighting the
predicate at the same site then denies. Which dialect a trace speaks is asked
of the TRACE (`vocab.dbg_dialect`), never of the text.

Every spelling was **generated, not reasoned about**: 41 rows out of `dbg()`
itself under node v24.16.0, committed as
`typescript/test/fixtures/inspect-table.json` and regenerated by
`gen-inspect-table.mjs`. What a reader has to know to spell a literal:

* `5.0` is written and read as **`5`** — JavaScript has one number type. This
  is the exact opposite of the Rust dialect, where `2.0` prints `2.0`.
* `1e21` is `1e+21`, `1e-7` keeps its sign and drops the pad, `0.000001` is
  written out in full, and `-0` keeps its sign (`String(-0)` does not).
* An integer of magnitude **≥ 2^53** goes through the double JavaScript
  actually held (R34): `2**60` is written `1152921504606847000`, so a search
  for it sights every capture of that double and reads back as the value the
  program had.
* Strings choose their quote the way inspect does — `'`, then `"`, then a
  backtick — except that a **`${` in the text rules the backtick out**, so
  `it's "x" ${y}` is written `'it\'s "x" ${y}'`.
* node names `\n`, `\t`, `\r`, `\b` and `\f` and nothing else: every other
  control character, DEL and the C1 block are `\xHH` in UPPERCASE hex, so a
  vertical tab prints **`\x0B`**. U+2028 and U+00A0 are printable to node and
  are not escaped at all.
* `null`, `undefined`, `true` and `false` are **predicate constants** in every
  language (plan D9): `watch --expr 'm == null'` and `flow --value null`
  answer about a value, not about a missing name.
* A string past inspect's own **100-character** cap is the one place
  truncation cannot be read off the capture's `trunc` flag — inspect cut the
  string long before the 200-byte wire cap saw the rendering, so `trunc` is
  `false` and the only evidence is the `… N more characters` tail outside the
  closing quote. `read_inspect` reads that tail as TRUNCATED and
  `inspect_text` refuses to spell one (plan P7), so a prefix is never
  compared as a value. `info`'s `truncated values:` count does not include
  such a cut (blind spot 36).

### Identity is a serial

`dbg()` mints two more keys for a value of type `object` or `function`
(`null` excluded): **`oid`**, a `WeakMap` serial minted once per object and
never reused, and **`type`**, the constructor's name through the ladder
`exc()` uses (`unread` when the object lies). They ride on every capture the
recorder makes — a RETURN value at the call tier, and under a focus the args
and the deltas — so `sensorium-ts 0.3.0` declares
`capabilities.object_identity: true` **unconditionally**, focused or not, and
`flow --object` needs only that capability and NOT `line` (R13).

Because the identity is minted rather than observed, there is nothing to
corroborate: the header reads *identity is a per-object serial minted once
and never reused: every sighting is the same object*, the gap analysis does
not run, and the footer is `continuity: exact (serial identity)`. Python's
`oid` is an ADDRESS and keeps its hedged reading; which of the two a trace
holds is `vocab.identity_basis`, not the number's shape. The serial counter
is its own map and its own counter, separate from the exception `serial`
(plan P12), so a thrown object's serial can never read as an identity in the
other command. **Sightings are top-level captures only** — an object inside
another's inspect text has no serial of its own (blind spot 32).

### The `focus matched:` line

`info` prints one line after `focus:` when the trace carries
`focus_matched`, gated on the meta key and never on the language (R31, R32):

    focus: Fog, fog.ts:Fog
    focus matched: 2 — focus_container/fog.ts:Fog.compute, focus_container/fog.ts:Fog.render

`(<n> function(s) focused by the transform)` is appended when
`functions_focused` is present AND differs. A focused **Rust** trace carries
`focus_matched` too and gets the same line, because every `info` line in this
reader is gated on the key it prints and not on `meta.lang`.

## What is deliberately absent

`records_dropped` is **never written by this recorder**. A container killed
by `SIGKILL` did not get to count what it was about to write, and a number
the runtime cannot know is a number this recorder does not put in a trace:
the trace carries `incomplete: true` and the tail is declared unknowable
(`typescript/HONESTY.md` §5). There is also no `scheduled_by` on a
parentless frame: which frame **scheduled** a timer callback is a
relationship this recorder does not record, and depth 0 inside the right
task is the whole of what is claimed (§3 of the same file).
