# The TypeScript corpus

Thirteen cases recorded by the **TypeScript** recorder
(`sensorium ts run -- npx vitest run <case>`) and questioned through the same
Python CLI as the rest of the corpus.

Unlike the Python and Rust corpora, a case here is **not** a self-contained
directory: a vitest run needs the project around it — the config vitest reads,
the `package.json` that names its version, and an installed `node_modules`. So
this directory is ONE vitest project, a case is a subdirectory of it, and
`corpus/run_corpus.py` copies the whole project into a disposable work dir per
case with `node_modules` symlinked to the real one. A case's `harness_args` are
the tokens after `vitest` — `["run", "<case>"]` — and the positional argument is
what selects that case's test files.

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
| `object_refused` | an identity question this recorder cannot answer: `flow --object` REFUSES through `object_identity: false` (exit 3), the values it does hold are byte-identical and settle nothing, and `flow --value` refuses again through `line: false` | `flow --object`, `tree`, `flow --value` |
| `watch_refused` | a per-line question this recorder cannot answer: `watch` REFUSES through `line: false` (exit 3) — while the same fault is still reachable through return values (`compute -> 200` inside `refresh -> 100`) | `watch`, `tree` |
| `exceptions_refused` | a swallowed parse error: the RAISE and the HANDLED rows ARE recorded, `err_flow=yes` says they carry what a verdict needs, and `exceptions` calls it SWALLOWED at the `catch` whose frame returned a healthy-looking default | `exceptions`, `info`, `tree` |
| `each_naming` | three `test.each` rows named as vitest expands them (`squares 2/3/4`), `task names: vitest`, no `#k`; and the `beforeEach` hook's twelve events counted outside every test | `info` ×2, `tree` |
| `unhandled_rejection_in_info` | a rejection nobody receives: the test passes, the harness exits 0, and the container's own listener is the only thing that noticed — `unhandled rejections: 1` | `info`, `tree` |
| `suspended_at_end` | a test parked on a promise that never settles: `~ suspended at LNone at end of recording`, one RETURN fewer than CALLs, and no INCOMPLETE banner — a parked frame in a whole recording | `tree`, `info`, `frame` |
| `timer_callback_parentless` | a `setTimeout` callback that runs with the task's stack empty: `sweep` is a root of the test's task at depth 0, and it is NOT among the scheduling frame's three children | `tree`, `frame` ×2 |

## Three things a case here must know

**Arguments are not recorded.** `capabilities.locals: false`, so every CALL
row reads `name() <unread: locals>` and `frame` prints `args: <unread:
locals>` — a stated absence, not an empty argument list. A port of a Python
case that identified an activation by its arguments identifies it here by its
position (`frame --nth 2`) or by what it returned. The planted bug is the same
class of bug; the question that finds it is not the same question.

**One invocation records one trace per test FILE**, and the `run:` lines come
in spool-name order, which is not the order vitest ran them in and is not
stable across runs. A question that uses `$RUN2` inside one invocation
(`pass_vs_fail`) may assert only what holds of either file — `expect_count`
and single-line groups whose needles do not depend on which side is A.

**A non-zero harness exit is not a recording failure.** `sensorium ts run`
returns the harness's own status, so `pass_vs_fail`, `suspended_at_end` and
`timer_callback_parentless` all exit 1 with a complete recording behind them.
What decides whether a case recorded is its `run:` lines.
