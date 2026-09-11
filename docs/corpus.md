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

Thirty-two more live under `corpus/typescript/`, recorded by the
TypeScript recorder. Thirteen are rung 1's: six ports of the cases above,
two whose pinned answer is a REFUSAL, four only this recorder has — `.each`
naming, an unhandled rejection in `info`, a frame suspended at end of
recording, and a timer callback with no traced caller — and
`silent_swallow`, whose parse error was pinned as a REFUSAL until rung 2
gave this recorder disposition rules and now pins the swallow it always was.
They share one vitest project and need a `node`; without one they are
skipped BY NAME, and `--require-driver` turns such a skip into exit 1 there
too.

The other fifteen are rung 2's swallow corpus: one throw-flow shape each,
each registering both its verdict line and its `dispositions:` tally before
E6-TS's collector reads them, and nine of the seventeen shapes in the set
(before rung 3; thirteen of twenty-one now) pinned to accuse NOTHING. Seven
reach the accusation — `logged_catch` (a
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
`test_failed`, the loud disposition the other sixteen are read against.
Seven pin what this recorder REFUSES to call a swallow — `escaped_catch` and
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

`--bench` reports; it never gates. Overhead is a tracked fact about a machine
and a workload, not a pass/fail property of the tool.
