# Changelog

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
