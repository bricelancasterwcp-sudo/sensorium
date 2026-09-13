# The corpus, case by case

The whole of the README's `## Corpus` section, **moved here 2026-09-09 (S5
rung 1, the TypeScript recorder) so [`../README.md`](../README.md) stays under
800 lines** — the `docs/query.md` precedent of 2026-09-06, taken the same way:
deliberately, before the gate names the file, rather than discovered at the
ceiling. The README stood at 798 with the TypeScript section and the thirteen
new cases in it, two lines from a ceiling `tests/test_ceiling.py` enforces.

**The wording and the order are unchanged**, with one addition named as one:
every paragraph below is byte for byte what the README carried, except the
last — the thirteen TypeScript cases — which is new text this slice wrote, and
which the shipped history (`603f879`) shows being written straight into this
file rather than into the README first. The README keeps the four commands, the
one-sentence claim the corpus makes, and a link here. The `--require-driver`
comment in the block below is the README's own wording of the day it was
written, when the only driver-backed cases were Rust's; the README's copy now
says "Rust or TypeScript".

    python corpus/run_corpus.py                   # verify against seeded bugs
    python corpus/run_corpus.py --show            # print the questions and commands
    python corpus/run_corpus.py --bench           # report recording overhead
    python corpus/run_corpus.py --require-driver  # a skipped Rust case is exit 1

Twenty small programs with deliberately planted bugs, and thirty-nine
questions registered **before** any output was looked at: the question in
plain language, the known ground truth, the exact invocation expected to
yield it, and why a `print()` cannot answer it. Ground truth is known
because the bugs were planted. This is the regression suite, and it
includes the honesty cases — a DIVERGED verdict, an under-claimed generator
swallow, a `watch` tally with fourteen unchecked sites, a task group that
answers which coroutine made the final write, a cancellation located at the
line a task was parked on, and arc 2's four: `abandoned_generator` (a
dropped generator's frame reads `~ abandoned`, never a fabricated `->`
return), `suspended_handler` (a handler frame still open when recording
stopped stays `ambiguous … never closed`, not a claimed swallow),
`window_across_suspension` (`--window` as ancestry survives a suspension —
another task's call parked in the middle is outside it, the windowed
frame's own call after it resumes is inside), and `async_handler` (`watch`
locals inside a focused coroutine, disambiguating two interleaved tasks a
print cannot tell apart). Plan 2b adds `async_refocus`: two tasks whose
start order flips between a recording and its rerun still MATCH, because
tasks are compared by content and the interleaving is not; re-recorded with
one task's content branching, the verdict is DIVERGED, naming that task.

Forty-three more cases live under `corpus/rust/`, recorded by the Rust
recorder instead. Fourteen of them are rungs 0–2's: seven ports of the cases
above (the same class of planted bug, asked differently, because that
recorder captures return values and not arguments), five that only Rust has
— a caught panic turned into an `Ok`, an `abort()` that leaves its frames
open and its exit `unwitnessed`, libtest under `--test-threads=1` against
`=4`, a worker thread named for the test that spawned it and the item the
spawn sits in, and a spawning function that moves to another file without
the worker's name changing — and two whose pinned answer is a REFUSAL, where
the question needs object identity or per-line events that recorder declares
it does not produce. Seventeen are rung 3's err-flow cases, each
registering both its `dispositions:` tally and its swallow set — ten of them
to pin that nothing is accused. Seven are rung 4's focus tier: six
recorded under a `--focus`, each pinning a LINE count DERIVED from the
design's rules before it was measured and at least one absence, and a seventh
recorded without one, so that the unfocused reading has a case whose name says
what it is. The last five are rung 4's refocus loop, where a recording is
re-run one flag deeper and compared against itself: a MATCH that answers the
per-line question the original could not, a DIVERGED where the program
branches on a file its own first run wrote, a refusal issued before anything
is rebuilt because the invocation was two test binaries, a re-run that spawns
a child of its own, and a test that spawns a thread onto another `#[test]`
fn — where the licence must count that thread as the program's and WITHHOLD,
rather than read its marked root as the recorder's own and grant. All
forty-three need a built
`cargo-sensorium` (`SENSORIUM_CARGO_SENSORIUM=<path>`, or one on `PATH`);
without it they are reported skipped BY NAME and counted apart from the
passes, never as them — and **`--require-driver`** turns such a skip into
exit 1, on the summary line and in `--json`, which is what CI's Rust corpus
step passes: a green summary over cases nobody ran is the dishonesty this
harness exists to refuse. `corpus/rust/README.md` is the case-by-case list.

Forty-four more live under `corpus/typescript/`, recorded by the
TypeScript recorder (forty-two through rung 4; this slice, S5 rung 4's
debts, 2026-09-12, added the last two named below). Thirteen are rung 1's:
six ports of the cases above, two whose pinned answer is a REFUSAL, four
only this recorder has — `.each`
naming, an unhandled rejection in `info`, a frame suspended at end of
recording, and a timer callback with no traced caller — and
`silent_swallow`, whose parse error was pinned as a REFUSAL until rung 2
gave this recorder disposition rules and now pins the swallow it always was.
One of the two refusals has since become an answer: `object_refused` is
`object_identity` from S5 rung 4 on, because every trace from 0.3.0 on
carries a per-object serial and the aliasing it plants is now decided — three
sightings under one identity, `continuity: exact (serial identity)`, out of
a recording that focused nothing. Its third question still pins a refusal,
and `watch_refused` is still the whole of the other one.
They share one vitest project and need a `node`; without one they are
skipped BY NAME, and `--require-driver` turns such a skip into exit 1 there
too.

The other fifteen are rung 2's swallow corpus: one throw-flow shape each,
each registering both its verdict line and its `dispositions:` tally before
E6-TS's collector reads them, and nine of the seventeen shapes in the set
pinned to accuse NOTHING (before rung 3 — see below for the current totals).
Seven reach the accusation — `logged_catch` (a
`catch` whose only mention of its binding is a `console.error`, which is the
archetypal swallow and not an escape), `callback_sink` and
`callback_handled` (those two shapes reached through `.catch(fn)` instead,
born as rejections with no `throw` statement anywhere in the program),
`await_rejection_caught` (one identity carried across an `await`, the throw
in one frame and the clause that took it in another), `finally_return` (a
`return` inside a `finally`, which is the swallow a search for `catch` never
finds), `dependency_throw` (born inside `JSON.parse`, so there is a
handler row and no raise to pair it with) and `rethrow_hop` (one object
through two clauses: the origin RE-RAISED `→ swallowed` with its `hops:`
line, the rethrow SWALLOWED at the clause that returned — a bare `throw e`
is a traced EXIT and not an escape, which is what lets the swallow beneath
it be named). One leaves the traced world:
`test_failed`, the loud disposition the other sixteen were read against, at
the time. Seven pin what this recorder REFUSES to call a swallow — `escaped_catch` and
`asserted_catch`, where the binding or a rendering of it left the clause and
the second is the commonest `catch` any suite writes; `callback_escaped` and
`callback_opaque`, the same two readings of a rejection handler, the second
a function whose body the splice never saw; `translated`, two thrown objects
with two serials, judged apart; `primitive_rethrow`, a thrown string
whose four rows carry no identity between them; and `suspended_handler`, an
absorbing clause whose frame was still parked when the recording ended.
`unhandled_rejection_in_info` gains rung 2's question as well: UNCAUGHT, the
one disposition taken from the process rather than from the rows.

The last four are rung 3's named-ambiguity cases: still AMBIGUOUS or
PROPAGATED, none of them SWALLOWED, but now printing WHY a rung-2 reader
could only fold the shape into `no rule of this recorder reaches a verdict
here`. `untraced_catcher` and `untraced_catcher_rejection` are one footprint
on a synchronous `toThrow` and an awaited `.rejects.toThrow`: a traced frame
unwinds into vitest's own matcher and the matcher's caller returns, so the
reason line reads `untraced catcher`, `its caller … returned`.
`untraced_catcher_later_failure` reads the OTHER half of the same rule on a
red suite: the same untraced catcher, whose caller does not return but
unwinds again with a second, unrelated error — `later unwound with
Error(…)` — and that second raise is PROPAGATED to the harness on its own
block. `logged_rethrow_to_harness` is `rethrow_hop` read to its other
ending, also red: one object, two RAISE rows and a `hops:` line, but the
rethrow leaves the test's own root frame instead of hitting a `catch` that
returns, so the origin reads RE-RAISED `→ propagated` and the rethrow itself
is PROPAGATED to the harness — the `console.error` beside the `throw e`
changes nothing about where the object goes. `translated`'s own wrapper
raise, still one of the seven that refuse the swallow, is re-pinned the same
way: its AMBIGUOUS block now reads `untraced catcher` by name instead of the
catch-all rung 2 could only leave silent about.

The last ten are rung 4's focus cases; two more from this debts slice join
them below, for twelve of the forty-four recorded under `sensorium ts run
--focus`. A vitest case declares that the
way a Python case does — `record: {focus: [...]}`, one `--focus <spec>` per
entry before the `--` — and `record` is the ONE key the two recorders share:
a `window` under it is refused by name, because `sensorium ts run` has no
such flag and a dropped key is a case whose questions all still pass. Under
a focus the recording declares `line=yes` and `locals=yes` on `info`'s
capabilities line, so these ten
pin what that tier says and, twice over, what it still does not:
`focus_let_chain` (one row per statement and none for the `return`, the CALL
counted among `watch`'s sites), `focus_loop_counter` (a row per loop entry, a
row per write, the exit pass carrying `unbound:v`, and a `flow --value` that
sights the dropped reading nowhere while printing the scope it searched),
`focus_block_scope` (the `if`'s own row saying its `const` died — the case
whose Rust twin cannot exist), `focus_destructure` (three names on one row,
one of them a silent default; `let x;` binds `undefined`), `focus_args` (a
focused CALL printing a destructured, defaulted parameter as what BOUND,
beside an unfocused `helper() <unread: locals>` in the same tree),
`focus_async` (rows on both sides of an `await` with `~ YIELD` and
`~ RESUME` between them, and the reader that took the placeholder sitting in
the gap), `focus_catch_binding` (SWALLOWED, the clause's entry row carrying
`e`, then the `try`'s own row with `unbound:e`), `focus_place_write`
(`state.x = 5` as a present row with an absent delta, and the 5 followable
nowhere), `focus_container` (two spellings of one class name selecting the
same two methods, with `info` printing the specs as typed beside what they
matched) and `flow_value_inspect` (the inspect dialect's own spellings: a
`5.0` needle finding a JS `5`, a quoted string, a 150-character value cut at
`str=100` and matching nothing, and `null` and `undefined` as claims about
values rather than about absent names).

This debts slice (2026-09-12) added two more under the same flag:
`focus_finally_return` (a `try` whose `finally` defers BOTH returns inside
its `tryBlock`, so two of `settle`'s three LINE rows — `cleanup = 1;` at L13
and `note(cleanup);` at L14 — run AFTER the `return` chose its value, inside
the `finally`, which is the case's point, and `watch --expr cleanup == 1`
reads SATISFIED at 2 of the 3 evaluable sites) and `focus_long_string` (the
inspect dialect's own length cap: a 100-character string renders whole, a
101-character one truncates to `... 1 more character` with the tail as the
only evidence a value was cut — blind spot 36 — and a `flow --value` of the
truncated literal sights nothing at all, exiting 1). Neither asks an
`exceptions` question.

`focus_catch_binding`, one of rung 4's own ten, is the one that gained an
`exceptions` question this slice: a new case cannot ask one against a table
locked before it existed, so its row is re-registered by hand, in a commit
of its own, BEFORE the question is written — the same discipline rung 3
used for its four named-ambiguity cases, and
`typescript/acceptance/e6ts.py`'s own docstring now says so under `HOW A
NEW CASE ASKS AN exceptions QUESTION`. The row must be read in the
vocabulary of the command it pre-registers: `focus_catch_binding`'s first
hand adjudication read a HANDLED event (attribution) as an accusation
(disposition) and pre-registered 0 SWALLOWED, corrected to 1 once the
question was written and run showed `dispositions: swallowed 1` — a plain
`catch` that only bumps a counter is the swallow `silent_swallow` already
named.

The current totals: twenty-two of the forty-four TypeScript cases carry an
`exceptions` verdict and a `dispositions:` tally (the seventeen above plus
rung 3's four plus `focus_catch_binding`), thirteen of them pinned to accuse
NOTHING (the nine above plus all four of rung 3's) and NINE now accuse
something — the eight above plus `focus_catch_binding`, this debts slice's
own correction (ruling P16): none of rung 3's four are SWALLOWED, but the
one of rung 4's ten that now asks an `exceptions` question is, once its row
reads the answer in that command's own vocabulary rather than a sibling
command's. Three leave the traced world with a PROPAGATED block, not one:
`test_failed`, `untraced_catcher_later_failure`'s second raise and
`logged_rethrow_to_harness`'s rethrow. The other nineteen are what is read
against them now, not sixteen.

`--bench` reports; it never gates. Overhead is a tracked fact about a machine
and a workload, not a pass/fail property of the tool.
