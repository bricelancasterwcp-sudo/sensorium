# `rust/spike/` — throwaway

This code is evidence for `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`. It is:

- **never merged to main** — it lives only on the `spike/rust-mechanics` branch and, per Task 6 of the plan, is never cherry-picked; only the findings document, its `results.json` copy, and a spec amendment land on main.
- **not built by CI** — `nothing under rust/ is built by CI` (plan Task 6); CI stays Python-only.
- **not installed** — never `cargo install`ed, and never referenced from `pyproject.toml`.

See `docs/superpowers/plans/2026-09-02-sensorium-rung1-mechanics-spike.md` for the full plan, and `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` for the design this spike measures against.

## How to build

Task 1's members are `sensorium-rt` (the runtime) and `bench-caller` (the
micro-bench's instrumented caller, a separate package only so its optimisation
level can differ from the runtime's). Tasks 2 and 3 add `sensorium-transform`
and `cargo-sensorium`.

```
cd rust/spike/
cargo build --release
cargo test
cargo clippy --all-targets -- -D warnings
```

`sensorium-rt` is pinned to `opt-level = 3` in every profile (workspace
`Cargo.toml`), because that is the lens §1 pre-registers and what the rung-2
driver will do regardless of the target workspace's profile.

## The micro-bench (E1's `fib(30)` numbers)

```
cargo build && cargo build --release && cargo run --release --bin microbench
```

Both profiles must be built, because the bench reports **two lenses** and they
differ by enough to reverse a reading:

- `caller=dev(opt0) rt=opt3` — **E1's pre-registered lens**: instrumented code
  at opt-level 0 against a runtime at 3, where the MIR inliner is off and
  `enter` is a real cross-crate call.
- `caller=release(opt3) rt=opt3` — both optimised, the gate inlined.

`bench-caller` is its own package precisely so both exist: a cargo package
override applies to every *target* of a package, so a bench binary inside
`sensorium-rt` is opt-level 3 in the dev profile too and can only ever measure
the release lens.

Output is one `key=value` line per number with the lens on every line (`#`
lines are a human summary). Each arm runs in its own process three times
(`SENSORIUM_TIER` is read once per process) and the best is reported. Spool
directories go under `TMPDIR` (or `SENSORIUM_BENCH_DIR`) and are removed after
each run; the `call` arm writes about 129 MB per run before cleanup.

## How the measurement is run

Once Task 5 has landed:

```
python rust/spike/measure.py
```

This runs the pre-registered protocol (§1 of the findings document) against `/home/brice/workspace/bloomery` (read-only — see the plan's Global Constraints) and the probe workspace at `rust/spike/probes/ws/`, then writes results.

## Where results live

- Ledger (gitignored, raw logs included): `.superpowers/sdd/2026-09-02-sensorium-rung1-mechanics-spike/results.json`
- Committed copy beside the findings document: `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.results.json`
- Rendered tables: `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` §3 (Results), §4 (Decisions), §5 (Rung-2 gaps found)
