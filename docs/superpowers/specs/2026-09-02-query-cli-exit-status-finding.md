# The query CLI's exit statuses conflate three next actions — finding, and a proposed slice

2026-09-02, against `main` @ `b9873dd` (v0.5.0). Found by two independent
design passes under the `designing-notation-for-llms` skill (a fresh agent
each, one blind and one with the skill; both named the exit channel first),
then verified here by reading every non-zero return site in
`src/sensorium/query/*.py` and `src/sensorium/cli.py`. Nothing in this
document is measured on model behaviour; every demand claim below is
**UNMEASURED** and says so, because the repository has no instrument that
could measure it yet (§4). This is a design finding with a proposed slice,
not a plan. It is orthogonal to the Rust-recorder rungs and should not take
a rung number.

## 1. The exit map as it is

An agent driving this CLI branches on the exit status before it reads
prose. Today the status answers "did it work" but not "what should I do
next", and the three next actions an agent actually has — *read the
answer*, *fix my call*, *change the recording* — are spread across the
three codes without regard to which is which.

| exit | sites | condition | the caller's next action |
|---:|---|---|---|
| 0 | every command's normal path | answered | read it |
| 0 | `watch_cmd.py:412 → :554` | **NOTHING WAS CHECKED** — the predicate could not be evaluated at any recorded site | **change the recording** (`--focus`) |
| 0 | `grep_cmd.py:98-101` | **no event matched** (`matches: 0`) | read it — but POSIX `grep` exits 1 here |
| 1 | `diff_cmd.py:791`, `refocus_cmd.py:636` | DIVERGED — the trace answers *no* | read the divergence, drill in |
| 1 | `tree_cmd.py:318, :348`; `frame_cmd.py:72`; `flow_cmd.py:755`; `watch_cmd.py:486` | `no such frame`, `no frame contains eN`, flow target not found, `--at` names no recorded code | **fix my call** (the reference is wrong for this trace) |
| 2 | `cli.py:75` | malformed or unknown run/event/frame ref; trace from a newer format | fix my call |
| 2 | `tree:296,300`, `flow:742`, `grep:75`, `exceptions:614`, `watch:498-503` | `--limit 0`, `--depth -1`, `--near 0`, bad `--expr` | fix my call |
| 2 | `flow_cmd.py:750`, `watch_cmd.py:509` | **REFUSED: <capability missing>** — the trace was recorded without LINE capture / object identity | **change the recording** |
| 2 | `refocus_cmd.py:281` | cannot refocus: no rerun attempted | fix my call, or record fresh |
| 2 | `refocus_cmd.py:601`, `diff_cmd.py:790` | REFUSED — no verdict could be issued | change the recording (or accept: no verdict exists) |

Three conflations, read off the table:

- **Exit 0 means both "answered" and "could not evaluate".** `watch`
  prints `verdict: NOTHING WAS CHECKED` and its own second line says
  `'hits: 0' here means 'could not evaluate', NOT 'the invariant held'`
  — and then exits 0, the same as SATISFIED. The prose is right and the
  channel an agent branches on contradicts it. Two tests pin this
  (`tests/test_watch_verdict.py:279`, `tests/test_format2_fixture.py:161`
  assert `== 0`).
- **Exit 2 means both "your call is wrong" and "this trace cannot settle
  it".** `--limit 0` and a `REFUSED: needs a --focus recording` land on
  the same status. One is fixed by editing the command; the other by
  re-recording. An agent that retries on 2 will retry the un-retryable.
- **Exit 1 means both "the answer is no" and "you named nothing".**
  DIVERGED is a verdict to read; `no such frame: f999` is a wrong
  reference to correct. `grep` with no match — the one case where the
  prior *expects* 1 — exits 0.

The README's verdict table (under "`refocus` — three verdicts") documents
0/1/2 for MATCH/DIVERGED/REFUSED and nothing else; the query commands have
no documented convention, so each one chose locally.

## 2. What the prior says the statuses should mean

The three tools the model knows best in this shape agree with each
other: `grep` 0 match / 1 no match / 2 trouble; `diff` 0 same / 1 differ
/ 2 trouble; `pytest` 0 pass / 1 failed / 2 interrupted / 4 usage error /
**5 no tests collected**. sensorium's `diff` and `refocus` already follow
the first two; the query commands do not, and nothing anywhere carries
pytest's fifth meaning — *the question was fine and the instrument had
nothing to check it against* — which is exactly `NOTHING WAS CHECKED` and
`REFUSED: <capability>`.

## 3. Proposed convention

| exit | meaning | covers |
|---:|---|---|
| 0 | answered, affirmatively | SATISFIED, MATCH, rows shown, a frame printed |
| 1 | answered, negatively — the trace says *no* or *none* | DIVERGED, `matches: 0`, not satisfied at N sites, `no such frame`, `no frame contains eN`, `--at` names nothing |
| 2 | the call is wrong — edit the command | malformed/ambiguous ref, `--limit 0`, bad `--expr`, newer format, cannot refocus (no rerun attempted) |
| **3** | **the trace cannot settle it — change the recording** | NOTHING WAS CHECKED, `REFUSED: needs --focus`, `REFUSED: needs object identity`, diff/refocus REFUSED, refocus UNVERIFIED |

Every 3 already prints the recording that would settle it (the caps
module's refusals do; `NOTHING WAS CHECKED` names the sites). The change
is to put the same fact on the channel the agent branches on. "Name both
ends" is the rule that found this: the diagnostic names the fix in prose
and withholds it from the status.

**Cost, stated:** two pinned tests move from `== 0` to `== 3`; the README
verdict table gains a row and the query commands gain a documented
convention; the `refocus`/`diff` REFUSED status changes 2 → 3, which is
the one documented contract this touches (v0.5.0 → 0.6.0, a note in the
changelog). Everything else is currently undocumented and unpinned.

**Falsifier, pre-committed:** on the corpus's honesty cases (`near_miss`,
`suspended_handler`, `silent_swallow`, `async_handler`), an agent shown
*only* the exit status should re-record more often on 3 than it does
today on the 0/2 cases that mean the same thing. If it does not, the
channel carried nothing and this ships as documentation only.

## 4. The instrument the repository lacks, and why it comes first

A compiler sees every rejected program; this CLI sees only invocations
that reached argparse, and a wrong-but-valid call exits 0 like a right
one. There is no record of what agents tried and were refused on, so
every demand claim in this document — and in any future flag proposal —
is UNMEASURED. The cheapest fix is one append, env-gated, in
`cli.main`: `(utc, argv, exit, error class or None)` to
`~/.sensorium/invocations.jsonl` (secrets are already the recorder's
problem, not this log's: argv only, never environment). Once the exit
split above exists, that log *is* the demand census: the flags agents
guess at, the refs they get wrong, the refusals they hit, in what
proportion. Ship it in the same slice, before any flag is added on
"agents would want this".

## 5. Collisions found on the way (§2's fifth row), for the same slice

| flag | means here | what the prior expects | note |
|---|---|---|---|
| `watch --near N` | how many near-misses to *show* | proximity to a location (`--near e40`) | rename candidate: `--misses N`; keep `--near` as a deprecated alias for one release |
| `refocus --window QUALNAME` | the qualname gate for LINE capture | a size or range (context window, time window) | house meaning with a prior-shaped spelling; rename candidate: `--lines-in QUALNAME`, or fold into `--focus`'s existing `module:qualname` form |
| `--fn NAME` | `grep`: qualname **substring**; `frame`: qualname **exact** (`frame_cmd.py:37`) | one meaning per spelling | make both exact, or both substring with exact-first resolution; either way document it once |
| `grep` exit 0 on no match | | POSIX `grep` exits 1 | covered by §3 |

`--around`, `--after`, `--context`, `--limit`, `--depth`, `--kind`,
`--at`, `--expr`, `--value`, `--object`, `--root`, `--nth`, `--task`
pass the collision test: the three tools the model knows best use each
the way sensorium does.

## 6. Ceremony noticed and deliberately NOT proposed yet

The run reference is a required positional on ten of the twelve
commands, and the caller skill's playbook types `last` in every example.
Defaulting it to `last` would remove one echoed constant per call — the
subtractive move the skill ranks first — but `find_trace` accepts any
prefix of a trace stem, so `sensorium grep foo` cannot tell a run prefix
from a pattern without a shape rule, and a wrong guess would answer
about the wrong trace silently. That is worse than the ceremony.
Recorded so nobody re-derives it; revisit only with the §4 census in
hand, which would say how often agents actually mistype the run.

## 7. Proposed slice, in order, invariants only

1. **Invocation log** (§4). Invariant: every `main()` return appends one
   record with the exit it returned; falsification: a mutant that logs
   before dispatch (exit unknown) fails the test that reads the exit
   back from the file.
2. **Exit-status convention** (§3). Invariants: `NOTHING WAS CHECKED`
   and every `require()` refusal return 3; `matches: 0` and every
   "names nothing" site return 1; argument validation and `RefError`
   stay 2; the README table and each subcommand's `--help` epilog state
   the four meanings in one sentence. Falsification per site: mutate
   the return, the pinned test fails. The two existing `== 0` assertions
   are rewritten, not deleted, with the reason in the commit.
3. **`grep` no-match → 1** (part of 2; listed because it is the one
   change that moves a *documented-by-prior* behaviour).
4. **Collision renames** (§5) with one-release deprecated aliases and a
   `--fn` semantics decision.
5. Re-read the invocation log after the next debugging arc and rank
   whatever it shows before proposing any new flag.

## 8. What is not claimed

- Nothing about how often agents hit any of these: unmeasured until §4.
- Nothing about the Rust-recorder arc; the proposed convention applies
  to whatever `sensorium` commands exist when it lands.
- The capability window: one binary serves every model tier, and the
  evidence behind the skill says ergonomic help matters least for the
  strongest caller. This slice is for the weakest caller that will
  drive the tool, and that is the one the tool was built for.
