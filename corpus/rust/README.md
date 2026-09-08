# The Rust corpus

Forty-three cases recorded by the **Rust** recorder (`cargo sensorium …`) and
questioned through the same Python CLI as the rest of the corpus. Each case
directory is a self-contained, dependency-free crate plus its
`questions.yaml`; `corpus/run_corpus.py` copies one whole directory into a
disposable work dir per run, so there is no workspace here and no
`Cargo.lock` is checked in.

```
python corpus/run_corpus.py                    # skips these BY NAME with no driver
SENSORIUM_CARGO_SENSORIUM=<path to cargo-sensorium> \
  python corpus/run_corpus.py                  # records and asks them
python corpus/run_corpus.py --only rust/panic  # one case
```

`CARGO_TARGET_DIR` is inherited when set; one warm target directory across
the cases is the difference between seconds and minutes. With no driver on
`PATH` and no `SENSORIUM_CARGO_SENSORIUM`, every case here is reported
`skip … no cargo-sensorium` and counted in its own column of the summary —
never as a pass.

## What each case pins

| Case | Planted truth | Commands |
|---|---|---|
| `double_call` | one order charged twice from one `submit` activation | `grep`, `frame` |
| `near_miss` | the overrun guard's high-water mark is 99 against a threshold of 100, so `alert` never ran — and the recording is complete enough for that absence to mean something | `tree`, `info` |
| `nondeterministic` | a branch decided by a file outside the process: the second recording is a DIFFERENT execution (DIVERGED), and nothing in the store claims the two runs are related | `diff`, `runs` |
| `none_propagation` | a `None` born in `lookup`, passed through `display_name`, unwrapped two frames later — crash site ≠ fault site | `grep`, `frame` |
| `pass_vs_fail` | 1000 and 1001 points part at the first causal step, and the two command lines are named | `diff` |
| `unit_mismatch` | grams priced as kilograms: `item_weight -> 1800.0` and the next call returns `4504.0` | `grep`, `frame` |
| `wrong_branch` | the exactly-1000 order silently takes silver | `tree`, `frame` |
| `panic` | a caught panic turned into `Ok(0)`: the panicking frame `closed: unwind` with `unwound: panic('…')`, the `catch_unwind` frame `-> Ok(0)` | `tree`, `frame` ×2 |
| `abort` | one invocation, two processes: the parent's `child runs:` names the child, the child reads `exit: unwitnessed` and its aborting frames are left open | `info` ×2, `tree` |
| `libtest_threads` | `--test-threads=1` against `=4` is a MATCH carried entirely by the tasks, which are named after the tests | `diff`, `info` |
| `spawned_thread` | a worker spawned inside a test is a task named `<test> :: spawn@<enclosing qualname>#<k>`, comparable by that name | `tree`, `info`, `diff --task` |
| `spawn_across_move` | the spawning function moves to another file between two runs of one crate and the worker keeps its name: `diff --ignore-moves` MATCHes across the move, a plain `diff` DIVERGED on the file the CALL is keyed to | `tree`, `diff --ignore-moves`, `diff` |
| `aliasing` | an identity question this recorder cannot answer: `flow --object` REFUSES through `object_identity: false` (exit 3), and the values it does hold do not settle it | `flow --object`, `tree` |
| `stale_cache` | a per-line question this recorder cannot answer: `watch` REFUSES through `line: false` (exit 3) — while the same fault is still reachable through return values | `watch`, `grep` |

## The rung-3 cases: Err flow

Seventeen cases added with the `?`/sink/arm probes and `exceptions` on a Rust
trace. Every one of them registers, in its `exceptions` question, both the
tally line WHOLE (`dispositions: ...`, printed tags only, in the fixed order
`swallowed, panicked, returned-to-harness, propagated, ambiguous`) and its
swallow set: as `expect_line` groups whose FIRST needle is `SWALLOWED`, or,
where the set is empty, as `expect_absent: ["SWALLOWED", "dispositions:
swallowed"]` -- the convention the Python `suspended_handler` case already
uses, and the one `tests/test_corpus.py` checks. An empty swallow set is a
claim like any other: ten of these seventeen exist to pin that nothing is
accused.

| Case | Planted truth | Commands |
|---|---|---|
| `silent_swallow` | two settings dropped at two DIFFERENT sinks in one frame -- `.ok()` and `let _ =` -- while `load` returns a healthy-looking default config: exactly two swallows | `exceptions`, `tree` |
| `err_propagation` | one error, four frames, four `?`: reported ONCE at its origin with every hop named, and returned to the harness by a `#[test]` fn that libtest reports as a bare `Debug` string | `exceptions`, `tree` |
| `interleaved_chains` | two DIFFERENT errors in one frame's window: identity on this wire is (type, `Debug` text), so the window cannot be split and both read ambiguous -- **never** a swallow | `exceptions`, `tree` |
| `unwrap_panic` | `.unwrap()` on an `Err`: PANICKED, naming the frame that was HOLDING the error, and saying out loud that the trace does not claim the Err caused the panic | `exceptions`, `tree` |
| `err_arms` | three `Err(..) =>` arms over one failing step -- handled, panicking, propagating -- and three different dispositions, one each | `exceptions`, `tree` |
| `closure_try` | a `?` inside a closure returns from the CLOSURE's own frame, not from the function around it; the chain then crosses one more hop into a sink in the enclosing frame | `exceptions`, `tree` |
| `returned_to_harness` | a `#[test]` fn that returns `Err`: the verdict names the frame and the `#[test]` mark that makes it a harness return, and the sibling passing test contributes no chain | `exceptions`, `tree` |
| `macro_arg_partial` | a `?` inside a `format!` invocation's tokens cannot be wrapped, so the site is DECLARED (`info`'s `partial fns:` line and `exceptions`' `partial:` header) rather than leaving an answer that only looks complete | `exceptions`, `info` |
| `err_stored` | an `Err(e) =>` arm that pushes `e` into a Vec: bound and escaped, so ambiguous -- the retry-loop shape a swallow detector must not accuse | `exceptions`, `grep` |
| `logged_arm` | the other side of that line: an `Err(e) =>` arm that only BORROWS the error to print it and carries on is a swallow, because the failure reached stderr and nothing else | `exceptions`, `tree` |
| `err_rendered_into_value` | the third side of it: an `Err(e) =>` arm whose `format!` PRODUCT is the value the function returns carries the failure to every caller, so it is ambiguous -- the shape endpoint E6' STOPped on (`build_memory` at the bloomery clone's `memory.rs:131`) | `exceptions`, `tree` |
| `err_borrowed_into_value` | an `Err(e) =>` arm that hands `&e` to a helper and keeps the helper's product -- the failure travelled to the caller inside the reply, so the arm reads ambiguous and NEVER a swallow (the shape E6⁗ measured on bloomery's `api_v1.rs`) | `exceptions`, `tree` |
| `keep_first_error` | a frame holding two different errors that returns the FIRST: the exit hop follows the returned text (no `translated`), the first error is swallowed by `main`'s log-and-continue arm, the second reads ambiguous | `exceptions`, `tree` |
| `dependency_swallow` | `let _ = fs::remove_file(..)`: a swallow whose error was born outside THIS THREAD's instrumented frames, with no producing frame to name, and a verdict that says so | `exceptions`, `tree` |
| `cleanup_then_fail` | the named blind spot: a GENUINE swallow in a frame that then fails for another reason reads ambiguous, not a swallow, and names which blind spot it is | `exceptions`, `tree` |
| `join_handle` | one error, two verdicts: in the child it left the thread into a `JoinHandle` (ambiguous, and why), in the parent it reached a sink in a frame that returned ok (a swallow) | `exceptions`, `tree` |
| `outcome_generic` | `rust/HONESTY.md` §1's named limit: a generic `T` that is an `Err` reads `ok`, so the generic frame raises nothing and its chain has NO hop, while the concrete frame beside it does | `grep`, `exceptions` |

The capability refusal (`exceptions` on a recorder that declares
`err_flow: false`) is **not** a case here: there is no runtime hook for
recording a rung-2-shaped trace out of a rung-3 build, so it is pinned by
conformance vector `v19` on a synthetic trace instead.

`panic`, `none_propagation` and `abort` each gained an `exceptions` question
in the same wave. A caught panic absorbed by an `Err(_) =>` arm IS a swallow
and is reported as one; a run that died by panic with no `Result` in it
answers `no exceptions recorded` with status 1 while still declaring that a
panic was recorded; and the aborted child answers 1 rather than 3, because
abort() took the process and not the records.

## The rung-4 cases: the focus tier

Seven cases added with `cargo sensorium --focus <qualname>`, which splices one
LINE probe after every statement of the named functions and gives the trace
`capabilities.line: true`. Six of them record WITH a focus; the seventh
records without one and exists so that the unfocused reading has a case whose
name says what it is.

Each of the six focused cases pins a LINE COUNT derived from the design's
rules before it was measured -- one probe per completed statement (§3.1), the
statement's own written bindings as its deltas (§3.2), a parameters LINE even
for a function taking none (amendment A2), an entry LINE for a pattern that
binds and none for one that does not (A3) -- and each pins at least one
ABSENCE, because that is where a miscounted rule shows up.

| Case | Planted truth | Commands |
|---|---|---|
| `focus_let_chain` | the straight-line shape: 4 rows for 3 statements, the fourth being the parameters LINE, and none for the tail expression whose value is the RETURN's | `watch`, `frame`, `info` |
| `focus_loop_counter` | three passes and one completion at the same source line: 9 rows, `i` bound three times by the loop's entry row, and the value 3 reached on the third pass and nowhere else | `flow`, `watch`, `frame` |
| `focus_match_binding` | an `if let` that binds and a `match` arm that binds each mint an entry row; `None` binds nothing and mints none; a `match` in tail position is not a statement; and the parameters row is the only place a Rust argument exists | `watch` ×2, `frame` |
| `focus_arm_bare` | amendment A1's shape: an arm whose body is a bare expression still mints its entry row, while the expression is the wrapping block's tail and mints none -- 2 rows, and three absences (the tail `match`, the arm's own expression, the untaken `None`). The shape E9 §5.1 settled and §5.5 item 2 recorded as unpinned | `watch`, `frame` |
| `focus_moved_value` | the borrow-by-construction proof: a focused function that moves a `Vec` still COMPILES, because a delta is captured right after its own write and never re-read; `[1, 2]` is not a sighting of `2` | `info`, `frame`, `flow`, `watch` |
| `focus_non_debug` | a binding whose type has no `Debug` is recorded as a NAME with `<unread>`, and `watch` answers NOTHING WAS CHECKED (exit 3) rather than "not satisfied" | `frame`, `watch` |
| `focus_unfocused_refuses` | the counterfactual: the same driver, one flag apart -- `line=no`, `LINE 0`, no `focus` key in the meta, and `watch` REFUSED at exit 3 | `watch`, `info` |

The driver's OTHER refusal -- `--focus` naming a function that does not exist,
which exits 2 with `Closest:` suggestions and builds nothing -- is not a case
here, because a corpus case records once and a refused recording leaves no
trace to question. It is pinned by `tests/test_focus_refusal.py`, which skips
by name when no driver is on the box exactly as these cases do.

## The rung-4 cases: the refocus loop

Five cases added with `sensorium refocus` on a Rust trace, which re-invokes
`cargo sensorium` under an added `--focus` and compares the pair. They are the
only cases here whose QUESTIONS record: the harness records the case once, and
a `refocus` question then launches the driver itself (the same
`SENSORIUM_CARGO_SENSORIUM` the recording used, passed through by
`run_corpus._cli` along with the case's `SENSORIUM_DIR`). A focused rebuild of
a one-file crate is seconds, and the re-run's cost is a blind spot the verdict
prints about itself.

The re-run's trace is a NEW run whose id no `questions.yaml` can spell, so the
questions after a refocus address it as `last` — the store's newest trace,
which the refocus just wrote — and read the PAIR through `runs`, where
`refocus-of:<original>` and the verdict ride together. **`last` is
mtime-ordered, not clock-ordered**, so it is unambiguous here only because a
case runs in a store of its own that holds exactly two traces, the second
written by the refocus under test; a case that refocused twice would need
`runs` to name which trace it means, and none of the five does.
`refocus_child_run` is the one whose store does NOT hold two traces — its
program records two processes and is recorded twice, so four — and it
therefore never says `last` at all: it names the original by `$RUN`, the
child of the original by `$RUN2`, and reads the pair and the excluded child
run through `runs`. `refocus_spawned_test_fn` says `last` no more than that
one does, for a different reason: what it asks for is the LICENCE, which the
refocus prints itself, so both its questions name the original by `$RUN`.

| Case | Planted truth | Commands |
|---|---|---|
| `refocus_match` | the loop closed: a run with no LINE row at all is re-run one flag deeper, MATCHes, and answers `b == 2` at the statement that wrote it — with the licence granted over exactly four points and `output`/`children` reported as checks that could NOT run rather than as two empty sets agreeing | `refocus`, `runs`, `info`, `watch` |
| `refocus_diverged` | a program that branches on a marker file its own first run wrote: the re-run cannot take the first run's path, so the verdict is DIVERGED at causal step 1 with `first_path` against `other`, exit 1, and the listing carries the divergence beside the link | `refocus`, `runs` |
| `refocus_refused_many` | `cargo test` on a crate with two integration tests is two processes, and refocus refuses BEFORE building anything — exit 2, the single-target sentence, and a store with no third trace in it | `refocus`, `runs` |
| `refocus_child_run` | a program that spawns itself: the re-run leaves TWO traces carrying `refocus_of`, and the one whose `ppid` is the other's `pid` is a child RUN rather than a second candidate — MATCH about the parent, the excluded child named on the pair line, and both re-run traces still listed, the unpaired one as `verdict:UNVERIFIED` | `info`, `refocus`, `runs` |
| `refocus_spawned_test_fn` | a test that spawns a thread onto another `#[test]` fn: the marked ROOT frame is not proof the recorder started that thread, so it counts as the program's (`1 besides the main one and 2 harness threads`) and the licence is WITHHELD — the rule that read the mark on any root subtracted all three, said `no thread started besides the main one`, and GRANTED | `info`, `refocus` |

## Two things a case here must know

**Arguments are not recorded.** At tier `call` the recorder captures return
values and outcomes, never locals or arguments — `tree` prints
`price() <unread: locals> -> 95.0`. So a port of a Python case that
identified an activation by its arguments identifies it here by its position
(`frame --nth 2`) or by what it returned. The planted bug is the same class
of bug; the question that finds it is not the same question.

**`info`'s `units:` line is partly a fact about the build tree.** The
`N instrumented` count is this process's own registered units, but the
`fell back` and `skipped` counts are read from every manifest in the build's
`CARGO_TARGET_DIR`, so a target directory shared with another crate that
fell back reports that crate's fallbacks here. Cases pin the instrumented
count and not the others.
