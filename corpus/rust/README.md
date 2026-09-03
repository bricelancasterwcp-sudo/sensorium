# The Rust corpus

Thirteen cases recorded by the **Rust** recorder (`cargo sensorium …`) and
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
| `spawned_thread` | a worker spawned inside a test is a task named `<test> :: spawn@src/lib.rs:33`, comparable by that name | `tree`, `info`, `diff --task` |
| `aliasing` | an identity question this recorder cannot answer: `flow --object` REFUSES through `object_identity: false` (exit 2), and the values it does hold do not settle it | `flow --object`, `tree` |
| `stale_cache` | a per-line question this recorder cannot answer: `watch` REFUSES through `line: false` (exit 2) — while the same fault is still reachable through return values | `watch`, `grep` |

`corpus/rust/outcome_generic`, named in `rust/HONESTY.md` §1, is **rung 3's**
and is deliberately absent: this tier reads a generic `T` that is an `Err`
as `ok`, and the case that falsifies that limit arrives with the fix.

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
