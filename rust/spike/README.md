# `rust/spike/` — throwaway

## PARKED (2026-09-02) — measurement complete, code frozen

The rung-1 mechanics spike is **done**. E0, E1, E2, E7 and E8 all PASS; the
three decisions are compile-once-gate-at-runtime, one test binary (one process)
as the trace unit, and GO for rung 2 on mechanics.

**This branch — `spike/rust-mechanics` — is parked and is never merged.** It
exists so the numbers below can be re-derived, and for no other purpose. Do not
build rung 2 on it: rung 2 is a fresh implementation against the amended spec.

Where the work actually lands:

- **Branch `docs/rung1-spike-findings`** (off `main`) carries the evidence —
  the findings document, its `results.json`, and the plan — plus the dated
  amendments to `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md`
  (§0, §2.1–2.5, §3.2, §3.5, §3.7, §4, §6, §8's measured column, §11's rung-1
  DONE, §13's deltas table).
- **After that PR merges, every number this spike produced lives on `main`** in
  `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md` (§3 results, §4
  decisions, §5 the twenty rung-2 gaps) and its `.results.json` beside it. Read
  those, not this tree, for what was measured.

Nothing under `rust/` is built by CI, on either branch; CI stays Python-only.

---

This code is evidence for `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`. It is:

- **never merged to main** — it lives only on the `spike/rust-mechanics` branch and, per Task 6 of the plan, is never cherry-picked; only the findings document, its `results.json` copy, and a spec amendment land on main.
- **not built by CI** — `nothing under rust/ is built by CI` (plan Task 6); CI stays Python-only.
- **not installed** — never `cargo install`ed, and never referenced from `pyproject.toml`.

See `docs/superpowers/plans/2026-09-02-sensorium-rung1-mechanics-spike.md` for the full plan, and `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` for the design this spike measures against.

## How to build

Task 1's members are `sensorium-rt` (the runtime) and `bench-caller` (the
micro-bench's instrumented caller, a separate package only so its optimisation
level can differ from the runtime's). Task 2 adds `sensorium-transform` (the
call-tier source rewriter); Task 3 adds `cargo-sensorium`.

`sensorium-transform`'s property test walks `/home/brice/workspace/bloomery`
READ-ONLY (override with `SENSORIUM_SPIKE_BLOOMERY`, skipped if absent) and
prints E2's census numbers:

```
cargo test -p sensorium-transform --test bloomery -- --nocapture
```

```
cd rust/spike/
cargo build --release
cargo test
cargo clippy --all-targets -- -D warnings
```

`sensorium-rt` is pinned to `opt-level = 3` in every profile (workspace
`Cargo.toml`), because that is the lens §1 pre-registers and what the rung-2
driver will do regardless of the target workspace's profile.

## The wrapper, and the E7/E8 checks

`cargo-sensorium` is one binary with two lives (`src/main.rs` explains the
role split). Run it against a target workspace like this:

```
cd rust/spike/probes/ws/
../../target/debug/cargo-sensorium sensorium test [--tier off|call] [cargo test args]
```

It builds `sensorium-rt` at release in *this* workspace, installs a shim at
`<target>/sensorium/shim/<hash>/cargo-sensorium`, points
`RUSTC_WORKSPACE_WRAPPER` at it, and runs `cargo test` with the argv unchanged.
Everything it writes lives under `<target>/sensorium/`: `mirror/`, `manifests/`,
`cache/`, `spool/<invocation-id>/`.

E7 and E8 are checked end to end on the probe workspace (`probes/ws`, its own
workspace with its own `Cargo.lock` — see `probes/ws/README.md`):

```
rust/spike/tests/mechanics.sh
```

Twenty-one checks, one line each, non-zero exit on any failure. (It said
"fifteen" until 2026-09-02; Task 3's fix round added six, and the findings
document records the run as "21 checks passed, 0 failed, exit 0" — §3, E7.)

**Build the driver with `--release` for any measurement run.** The shim path is
the sha256 of the driver binary and the rt rlib, and a debug build of the driver
is 20 MB, so hashing it costs ~0.5 s of fixed setup on EVERY invocation
(measured: 0.52/0.50/0.59 s debug versus 0.03 s release, against ~0.005 s for a
bare no-op `cargo test --no-run`). That is a systematic offset on the
instrumented arms of E1 and on nothing else. It uses a fresh
target directory per run unless `SENSORIUM_MECHANICS_TARGET` says otherwise, and
`SENSORIUM_MECHANICS_KEEP=1` leaves the logs and the target behind.

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

## The converter (Task 4)

`convert.py` is a throwaway Python script -- never imported by `sensorium`
itself, never referenced from `pyproject.toml` -- that reads one
`cargo sensorium test` invocation's spool directory and writes one format-4
sensorium trace per process, so a real trace can be opened with the real
`sensorium` CLI before the Rust recorder rung 2 will build exists:

```
.venv/bin/python rust/spike/convert.py <spool-dir> --target <target-dir> \
    [--cargo-exit N] [--argv CARGO ARGS...]
```

`<spool-dir>` is `<target>/sensorium/spool/<invocation>/`; `<target>` is the
same `CARGO_TARGET_DIR` the driver built into, and its PARENT is taken as the
workspace root (manifest paths are workspace-relative). `--argv`, if given,
must be the LAST flag -- it swallows every token after it, dashes included,
and is recorded as meta `cargo_args`.

Tests: `.venv/bin/python -m pytest rust/spike/tests/ -q` (`test_convert.py`
for the wire-parser/merge/frame-reconstruction/meta tiers, `test_convert_e2e.py`
for the end-to-end tier -- split purely to keep both files under 800 lines; a
`conftest.py` beside them puts `rust/spike` on `sys.path`, and
`pyproject.toml`'s `testpaths = ["tests"]` already keeps the main suite from
collecting either). The end-to-end tier builds the release driver and the
probe workspace's `probe-app` lib tests into a temp `CARGO_TARGET_DIR` under
`probes/ws/` itself, converts through `convert.py`'s own CLI, and drives the
real `sensorium` CLI in a subprocess against a temp `SENSORIUM_DIR` -- see
`.superpowers/sdd/2026-09-02-sensorium-rung1-mechanics-spike/task-4-report.md`
for the mapping decisions and the mutation-check log.

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
