# The TypeScript corpus

Forty-two cases recorded by the **TypeScript** recorder
(`sensorium ts run -- npx vitest run <case>`) and questioned through the same
Python CLI as the rest of the corpus. Ten of them are recorded one flag
deeper — `record: {focus: [...]}` in the case file becomes
`sensorium ts run --focus <spec> … --`, one `--focus` per entry, before the
`--` — and those are the ten that may ask a per-line question at all.
`record` is the ONLY key a vitest case shares with the Python recorder, it
may hold nothing but `focus`, and a `window` under it is refused by name:
`sensorium ts run` has no such flag, and a key that reached no recorder
would leave every question passing against a recording nobody asked for.

Unlike the Python and Rust corpora, a case here is **not** a self-contained
directory: a vitest run needs the project around it — the config vitest reads,
the `package.json` that names its version, and an installed `node_modules`. So
this directory is ONE vitest project, a case is a subdirectory of it, and
`corpus/run_corpus.py` copies the whole project into a disposable work dir per
case with `node_modules` symlinked to the real one. A case's `harness_args` are
the tokens after `vitest` — `["run", "<case>"]` — and the positional argument is
what selects that case's test files.

**A case name that is a PREFIX of another case name is a trap.** `vitest run
<pattern>` selects every test file whose path CONTAINS `<pattern>` as a
substring — it is not an exact match and not anchored to one directory — and
every case's directory sits in the SAME copied project, so a bare case name
that happens to prefix a sibling's pulls both into one recording. This is
exactly what `untraced_catcher` hits: its name is a literal prefix of
`untraced_catcher_rejection` and `untraced_catcher_later_failure`, so
`harness_args: ["run", "untraced_catcher"]` would record all three test files
as one, and whichever ran first would silently own `$RUN`. Its
`harness_args` is `["run", "untraced_catcher/"]` instead — the trailing
slash matches the directory boundary, which is not a substring of either
sibling's path — and that is the fix for the next prefix-named case, not a
new `$RUN2` situation to declare. The ten focus cases take the slash form as
a matter of course: none of their names is a prefix of any other today, and
the next `focus_*` case somebody adds may well make one of them one.

```
npm ci --prefix corpus/typescript             # once; the lock is committed
python corpus/run_corpus.py                   # skips these BY NAME with no Node
python corpus/run_corpus.py --only-dir typescript --require-driver
python corpus/run_corpus.py --only typescript/wrong_branch
```

`vitest`, `vite` and `typescript` are pinned EXACTLY (R18): the lens a
measurement was taken through is part of the measurement, and a corpus that
floated its harness version would change what it pins without anybody
editing it. With no `corpus/typescript/node_modules` and with Node below 24,
every case here is reported `skip … no corpus/typescript/node_modules (npm ci)
or node < 24` and counted in its own column of the summary — never as a pass.

`vitest.config.ts` is deliberately PLAIN — `include`, `environment`, nothing
else. The driver writes its own wrapper config, `mergeConfig`s this one into
it, and adds the plugin, the setup file and the runtime externalisation itself;
`mergeConfig` concatenates arrays, so a config that wired any of those here
would give a driven run two plugins, two setup files and two runtimes, which is
one spool with two BOOT records and a refusal.

## What each case pins

| Case | Planted truth | Commands |
|---|---|---|
| `double_call` | one order charged twice from one `submit`, found by the count and by that activation's four children in order | `grep`, `frame` |
| `wrong_branch` | the exactly-1000 order silently takes `silver`: three `price` activations, two silvers, and `gold` absent from the frame that should have had it | `tree`, `frame --nth 2` |
| `unit_mismatch` | grams priced as kilograms: `itemWeight -> 1800` and the next call returns `4504` with no children of its own | `grep`, `frame --nth 2` |
| `pass_vs_fail` | two test FILES of one invocation: compared straight they part at causal step 0 on the split itself, and `--ignore-moves` pairs the two test callbacks and finds the real parting at step 2, `gold` against `silver`. Also the exit rule — `unwitnessed` per container, `1 (waited)` for the harness | `diff`, `diff --ignore-moves`, `info`, `runs` |
| `nondeterministic` | a branch decided by a file outside the process: the second invocation is a DIFFERENT execution (DIVERGED at step 4), and nothing in the store claims the two runs are related | `diff`, `runs` |
| `async_interleaved` | two `test.concurrent` tests write one key; every row of each is in its own task, including the write after the `await` — and the naming cross-check DISAGREED once on a concurrent test and said so (`task names: mixed, 1 conflict(s)`) | `tree`, `frame` ×2, `info` |
| `object_identity` | an identity question this recorder now ANSWERS, and one it still refuses: two callers hold one object, `flow --object loadSettings:return` sights it three times under one serial (`continuity: exact (serial identity)`) with no focus recorded at all, the values it captured are byte-identical and settle nothing on their own, and `flow --value` still refuses through `line: false`. Named `object_refused` until S5 rung 4 gave every 0.3.0 trace an identity | `flow --object`, `tree`, `flow --value` |
| `watch_refused` | a per-line question this recorder cannot answer: `watch` REFUSES through `line: false` (exit 3) — while the same fault is still reachable through return values (`compute -> 200` inside `refresh -> 100`) | `watch`, `tree` |
| `silent_swallow` | a swallowed parse error: the RAISE and the HANDLED rows ARE recorded, `err_flow=yes` says they carry what a verdict needs, and `exceptions` calls it SWALLOWED at the `catch` whose frame returned a healthy-looking default | `exceptions`, `info`, `tree` |
| `each_naming` | three `test.each` rows named as vitest expands them (`squares 2/3/4`), `task names: vitest`, no `#k`; and the `beforeEach` hook's twelve events counted outside every test | `info` ×2, `tree` |
| `unhandled_rejection_in_info` | a rejection nobody receives: the test passes, the harness exits 0, and the container's own listener is the only thing that noticed — `unhandled rejections: 1`; and the verdict on it is UNCAUGHT, the one disposition taken from the process rather than from the rows | `info`, `tree`, `exceptions` |
| `suspended_at_end` | a test parked on a promise that never settles: `~ suspended at LNone at end of recording`, one RETURN fewer than CALLs, and no INCOMPLETE banner — a parked frame in a whole recording | `tree`, `info`, `frame` |
| `timer_callback_parentless` | a `setTimeout` callback that runs with the task's stack empty: `sweep` is a root of the test's task at depth 0, and it is NOT among the scheduling frame's three children | `tree`, `frame` ×2 |

## The swallow corpus

Fifteen more cases, one throw-flow shape each, added by S5 rung 2. Every one
registers the `exceptions` verdict line AND the `dispositions:` tally before
the E6-TS collector reads them, so the set of shapes this recorder calls
SWALLOWED is pinned case by case and not counted after the fact.

| Case | Planted truth | Commands |
|---|---|---|
| `logged_catch` | a `catch` whose only mention of its binding is a `console.error`: SWALLOWED, because log-and-continue is where the failure went and a log is not a return value | `exceptions` |
| `escaped_catch` | `return String(e)`: the same two rows as a swallow, a `catch_escaped` `how` word, and AMBIGUOUS — the line these rules refuse to cross | `exceptions` |
| `asserted_catch` | `expect((e as Error).message)`, the commonest `catch` any suite writes and the lens's dominant shape: AMBIGUOUS, never an accusation against a deliberate test | `exceptions` |
| `rethrow_hop` | one object through two clauses: two RAISE blocks and a `hops:` line drawing the journey — the origin RE-RAISED `→ swallowed`, the rethrow SWALLOWED at the clause that returned. The bare `throw e` is a traced EXIT, not an escape, which is what lets the swallow below it be named | `exceptions` |
| `translated` | `throw new Wrapped(String(e))`: two objects, two serials, two blocks — the original stops at the clause and the wrapper is judged on its own evidence. Re-pinned by S5 rung 3: the wrapper's own block now reads AMBIGUOUS, untraced catcher, instead of the old catch-all | `exceptions` |
| `callback_sink` | `await p.catch(() => {})`: SWALLOWED with no `throw` statement anywhere, the verdict naming the birth (`a reject()`) because there is no raise to pair the handler with | `exceptions` |
| `callback_handled` | `.catch((e) => { console.warn(e) })`: the `logged_catch` swallow written as a promise, and the `how` word is what says which | `exceptions` |
| `callback_escaped` | `.catch((e) => { seen.push(e) })`: the reason left the callback, so AMBIGUOUS | `exceptions` |
| `callback_opaque` | `.catch(noteFailure)`: the splice saw an identifier and not a body, so AMBIGUOUS — the handler really does drop it, and the recorder will not guess | `exceptions` |
| `await_rejection_caught` | `try { await f() } catch {}`: one identity carried across the suspension, the RAISE in one frame and the clause that swallowed it in another | `exceptions` |
| `test_failed` | the one direction that was never silent: PROPAGATED to the harness with the test named — a RED suite by design, and the control the other cases are read against | `exceptions` |
| `primitive_rethrow` | `throw 'boom'`, caught and thrown on: four rows, no identity between any two of them, AMBIGUOUS four times — the honest answer and not the useful one | `exceptions` |
| `finally_return` | a `return` inside a `finally` and no `catch` in the file at all: SWALLOWED by `sink_finally_return`, the swallow a search for `catch` never finds | `exceptions` |
| `dependency_throw` | `JSON.parse('{')` inside an empty `catch`: SWALLOWED, `born outside traced code` — a handler row with no raise, and no throw site invented for it | `exceptions` |
| `suspended_handler` | an absorbing clause whose frame then parks forever: AMBIGUOUS, still suspended — an absorbing clause is only HALF of a swallow. Also a red suite, by its own 200 ms timeout | `exceptions` |

## The named-ambiguity cases

Four more, added by S5 rung 3. None are SWALLOWED; all four are the shape
rung 2 could only fold into the catch-all, `AMBIGUOUS -- no rule of this
recorder reaches a verdict here`, now printed with the reason named and,
where there is one, a `hops:` line.

| Case | Planted truth | Commands |
|---|---|---|
| `untraced_catcher` | `expect(() => parse('sqrt(4)')).toThrow(FormulaError)`: the throw unwinds into vitest's own matcher, which is not traced code — AMBIGUOUS, untraced catcher, `its caller f1 returned; not followed` | `exceptions` |
| `untraced_catcher_rejection` | the same reason reached across a suspension: `await expect(fetchThing()).rejects.toThrow('offline')`, and the unwound frame is the rejecting function's own, with no wrapping arrow | `exceptions` |
| `untraced_catcher_later_failure` | the `toThrow` shape, then a second, unrelated `throw` out of the same test root: the first block reads the third variant, `later unwound with Error(…): a translation by untraced code, or a later failure, indistinguishable`, and the second raise is PROPAGATED to the harness on its own block. Red suite by design | `exceptions` |
| `logged_rethrow_to_harness` | `rethrow_hop`'s journey read to its other ending: `try { load() } catch (e) { console.error(e); throw e }` in the test body, and the rethrow leaves the test's own root frame — RE-RAISED `→ propagated` with its `hops:` line, then PROPAGATED to the harness. Red suite by design | `exceptions` |

## The focus cases

Ten more, added by S5 rung 4, and the only ten recorded under
`--focus`: one rule of the focus tier each, with the answer's exit status
and its distinctive lines pinned byte for byte. Under a focus a recording
declares `line: yes` and `locals: yes`, so `watch`, `frame`'s timeline and
`flow --value` mean something here that they refuse to mean in the
thirty-two cases above — and what the tier does NOT reach is pinned in the
same table, twice, rather than left to the absence of a case.

| Case | Planted truth | Commands |
|---|---|---|
| `focus_let_chain` | a three-`const` chain whose tail returns the wrong link: one row per statement carrying what that statement wrote, NO row for the `return` (nothing at `fill L9`), and `watch` counting the CALL among its four sites — SATISFIED at the two it could evaluate, the other two reported as not in scope | `frame`, `watch` |
| `focus_loop_counter` | a `for…of` over `xs.slice(1)`: the head mints a row PER ENTRY (`v=2`, `v=3`), the body one per write, and the pass that ends the loop is the head's row again with `unbound:v`. `flow --value 3` sights the reading the loop saw, once; `flow --value 1` sights the dropped one nowhere, exit 1, with the searched scope printed beside the emptiness | `frame`, `flow` ×2 |
| `focus_block_scope` | a `const` inside an `if`, read after it: the `if` statement's own row carries `unbound:discount`, so `watch` hits at the two sites inside the block and reports the nine outside it as out of scope rather than as misses — the case whose Rust twin cannot exist | `watch`, `frame` |
| `focus_destructure` | `const { id, size: [first] = [0], ...rest }`: one statement, three names on one row, and `first=0` is the DEFAULT binding beside the `sizes` the payload actually carried, sitting unread in `rest`. `let note;` binds `undefined`, which is a value | `frame`, `watch` |
| `focus_args` | one run, two functions: the focused `total(items=[ 1, 2 ], member=true) -> 3` — a destructured, defaulted parameter printed as what BOUND — beside the unfocused `helper() <unread: locals> -> 1`, whose argument is not in this recording at all. What a focus buys and what it does not, in two lines of one tree | `tree`, `frame` |
| `focus_async` | a cache published before the value exists: rows on both sides of the `await` with `~ YIELD` and `~ RESUME` between them, the pre-await write immediately followed by the YIELD, and the reader that got the placeholder (`peek() … -> 0`) sitting between the two | `frame`, `tree` |
| `focus_catch_binding` | `catch (e) { count += 1 }`: a HANDLED row, then the catch clause's own entry row carrying `e=Error: bad key: oops`, then the `try` statement's row with `unbound:e` — twice, once per iteration, including the pass that threw nothing | `frame`, `grep` |
| `focus_place_write` | `state.x = 5`: a row at the line with NO delta after the site, and `flow --value 5` sighting nothing across the four captures searched. The blind spot as a present row and an absent value, said from both sides | `frame`, `flow` |
| `focus_container` | `--focus Fog` and `--focus fog.ts:Fog` in one recording select the same two methods and no more: `focus matched: 2 — …Fog.compute, …Fog.render`, with `info` printing the specs as they were TYPED beside what they resolved to | `info`, `tree` |
| `flow_value_inspect` | the inspect dialect's spellings: `flow --value 5.0` sights a JS `5`, `--value "'A1'"` sights a string, a 150-character value is rendered at `str=100` with `… 50 more characters` and a needle spelling it out sights nothing (exit 1), and `watch` answers `parsed == null` and `missing == undefined` as claims about values, not about absent names | `flow` ×3, `watch` ×2 |

## Three things a case here must know

**Arguments are recorded only under a focus.** Thirty-two of these cases
record no `--focus` at all, so `capabilities.locals: false` holds for them:
every CALL row reads `name() <unread: locals>` and `frame` prints `args:
<unread: locals>` — a stated absence, not an empty argument list. A port of a
Python case that identified an activation by its arguments identifies it here
by its position (`frame --nth 2`) or by what it returned. The planted bug is
the same class of bug; the question that finds it is not the same question.
The ten focus cases are the other side of that: a FOCUSED function's CALL
prints its arguments (`total(items=[ 1, 2 ], member=true)`), and an unfocused
one in the very same recording still reads `<unread: locals>`, which is what
`focus_args` exists to pin.

**One invocation records one trace per test FILE**, and the `run:` lines come
in spool-name order, which is not the order vitest ran them in and is not
stable across runs. A question that uses `$RUN2` inside one invocation
(`pass_vs_fail`) may assert only what holds of either file — `expect_count`
and single-line groups whose needles do not depend on which side is A.

**A non-zero harness exit is not a recording failure.** `sensorium ts run`
returns the harness's own status, so `pass_vs_fail`, `suspended_at_end`,
`timer_callback_parentless`, `test_failed`, `suspended_handler`,
`untraced_catcher_later_failure` and `logged_rethrow_to_harness` all exit 1
with a complete recording behind them — the last four by design: in three of
them (`test_failed`, `untraced_catcher_later_failure`,
`logged_rethrow_to_harness`) the planted failure reaches the harness, and in
the fourth (`suspended_handler`) the frame it is asked about is still parked
when the test's own timeout ends the run. What decides whether a case
recorded is its `run:` lines.
