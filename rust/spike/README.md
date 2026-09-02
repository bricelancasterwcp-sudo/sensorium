# `rust/spike/` — throwaway

This code is evidence for `docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`. It is:

- **never merged to main** — it lives only on the `spike/rust-mechanics` branch and, per Task 6 of the plan, is never cherry-picked; only the findings document, its `results.json` copy, and a spec amendment land on main.
- **not built by CI** — `nothing under rust/ is built by CI` (plan Task 6); CI stays Python-only.
- **not installed** — never `cargo install`ed, and never referenced from `pyproject.toml`.

See `docs/superpowers/plans/2026-09-02-sensorium-rung1-mechanics-spike.md` for the full plan, and `docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md` for the design this spike measures against.

## How to build

Once Tasks 1–3 have landed on this branch (`sensorium-rt`, `sensorium-transform`, `cargo-sensorium`):

```
cd rust/spike/
cargo build --release
```

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
