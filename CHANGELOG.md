# Changelog

## 0.8.0 — 2026-09-05

- **Rust err flow, and `sensorium exceptions` on a Rust trace.** The
  transformer probes every `?` on a `Result`, the four written sinks
  (`.ok()`, `.unwrap_or(..)`, `.unwrap_or_else(..)`, `.unwrap_or_default()`),
  `let _ = <value>`, and every `Err(..) =>` arm or `if let Err(..)` body —
  classified `arm_propagate` / `arm_handled` / `arm_ambiguous` by what its
  body does, with panicking arms deliberately unprobed. Closures holding a
  `?` get their own frame. The runtime writes wire-v3 RAISE/HANDLED records
  with the `Err`'s type and capped `Debug` text; the converter mints chain
  serials at conversion time in a namespace disjoint from panic serials; a
  Rust rule module behind the shared renderer prints five dispositions —
  `swallowed`, `panicked`, `returned-to-harness`, `propagated`, `ambiguous`.
  `rust/HONESTY.md` §11 is what each verdict may claim.
- **Measured, and the first measurement said STOP.** On the bloomery clone's
  `--lib` suite the rule printed 15 SWALLOWED lines and one was a false
  accusation — an `Err(e) =>` arm whose `format!` product is the value the
  function returns — so the pre-registered endpoint read STOP
  (`docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md`).
  The classifier was amended (a bound name in `format!`/`format_args!`/
  `write!`/`writeln!` now ESCAPES; only the logging family's bare arguments
  stay exempt), a new endpoint set was byte-locked, and the repair was
  re-measured: **0 false accusations of 14** on two selectors and under both
  readings of the endpoint
  (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md`).
- **A `?` the transformer cannot reach is declared, not lost**: `partial`
  rows (`macro-arg`, `async-block`, `struct-literal`) reach the trace as a
  meta key, and both `info` and `exceptions` print them.
- **New capability `err_flow`**, declared by `sensorium-rt` ≥ 0.3.0 and
  passed through untouched by the converter. `exceptions` on a Rust trace an
  older runtime wrote refuses by name at exit 3 — what it lacks is a record,
  not a rule. Python traces are untouched: `exceptions` output on a Python
  trace is byte-identical to 0.7.0.
- **Panic locations keep their promise, with a two-place clause**: lines never
  move, and a column shifts in exactly two places. Inside a wrapped `?`/sink/
  `let _` operand, by the wrap prefix's 6 bytes — **measured**, predicted
  before each run and met exactly at both tiers. And after an arm probe or
  closure guard spliced at a same-line `{`, by that probe's own byte length —
  **stated, unmeasured**: no check exercises it (`docs/CARRIED-DEBT.md`).
- **Trace format 4 gains** `exc.kind`, `how`, `chain` and a typed `err`
  RETURN (`docs/TRACE-FORMAT.md` §5), meta keys `partial`,
  `err_flow_records`, `err_flow_outside_frames`, `closure_frames`, and
  conformance vectors v16–v19. RAISE and HANDLED are causal kinds, so every
  Rust fingerprint moved; E3″ (0 DIVERGED of 19) and E5″ re-measured it.
- **`sensorium-rt`, `sensorium-transform` and `cargo-sensorium` → 0.3.0**
  (wire v3). A v2 spool still converts.
- **`watch --near` removed, as 0.7.0 promised.** The hidden deprecated alias
  is gone from the parser; `--misses` is the only spelling now, and passing
  `--near` is an unrecognized argument like any other unknown flag (exit 2).

## 0.7.0 — 2026-09-04

- **Exit-status convention**: every query command's exit status now names
  the caller's next action — `0` the question was answered affirmatively,
  `1` answered negatively (the trace says no, or none), `2` the call is
  wrong (edit the command and ask again), `3` the trace cannot settle it
  (change the recording and re-record). `run` is unchanged: it exits with
  the target's own status. See the README's "Exit statuses" section and
  every subcommand's `--help` epilog.
- **Contract change**: `diff` and `refocus`'s `REFUSED` verdict moves from
  exit 2 to exit **3** — a refusal after a comparison ran (or, for
  `refocus`, after the rerun happened) is "the recording can't settle it,"
  not "the call is wrong." `refocus`'s other gate — refusing before any
  rerun is attempted (INCOMPLETE original, stdin consumed, the target no
  longer resolves, the working directory gone, a per-thread-basis original
  that ran tasks, the trace records no command to re-run or no working
  directory to re-run from, `capabilities.refocus: false`) — stays exit 2,
  unchanged.
- **`watch --misses N`** replaces `--near N` as the flag that sets how many
  near-misses to show when nothing hit; `--near` is kept as a hidden,
  deprecated alias for this release only (prints a deprecation line on
  stderr) and will be removed in 0.8.0.
- **`--fn` is exact-first, then substring** in both `grep` and `frame`: a
  qualname that matches `--fn` exactly wins outright; only when nothing
  matches exactly does it fall back to substring, and a substring that
  matches more than one distinct qualname is refused (exit 2) with every
  candidate listed, rather than picked among.
- **Invocation log**: `sensorium` now appends one JSON line per invocation
  — `utc`, `argv`, `exit`, `error` — to `<trace root>/invocations.jsonl`,
  a sibling of `traces/` so no trace lookup ever sees it. Default on;
  disable for one process with `SENSORIUM_NO_INVOCATION_LOG=1`.
- **Rust toolchain pinned** to `1.96.0` via `rust/rust-toolchain.toml`; CI
  installs it with `rustup show` and the cache key carries the channel
  string, so a clippy/rustfmt version bump is now a deliberate commit.

## 0.6.0 — 2026-09-04

- Rust recorder rung 2 (recorder v1) and the rung-3 entry slice (spawn
  names across a file move) merged — PRs #10, #12.
