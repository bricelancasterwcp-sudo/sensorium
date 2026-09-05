# The Rust corpus

Twenty-nine cases recorded by the **Rust** recorder (`cargo sensorium …`) and
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

Fifteen cases added with the `?`/sink/arm probes and `exceptions` on a Rust
trace. Every one of them registers, in its `exceptions` question, both the
tally line WHOLE (`dispositions: ...`, printed tags only, in the fixed order
`swallowed, panicked, returned-to-harness, propagated, ambiguous`) and its
swallow set: as `expect_line` groups whose FIRST needle is `SWALLOWED`, or,
where the set is empty, as `expect_absent: ["SWALLOWED", "dispositions:
swallowed"]` -- the convention the Python `suspended_handler` case already
uses, and the one `tests/test_corpus.py` checks. An empty swallow set is a
claim like any other: nine of these fifteen exist to pin that nothing is
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
