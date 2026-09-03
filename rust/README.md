# rust/ — the sensorium recorder for Rust

Record what a Rust program actually did; ask it the same questions.

`cargo sensorium test` wraps one `cargo test` invocation, instruments your
workspace's own crates at build time, and writes one sensorium trace per
process — the same SQLite format 4 the Python recorder writes, read by the same
`sensorium` command line. It exists for the same reason the Python side does:
reading logs is reading a diary, and this is watching the execution.

Three crates, all `0.1.0`, all `publish = false`:

| Crate | What it is |
|---|---|
| `sensorium-rt` | The runtime linked into every instrumented unit. Zero dependencies. Thread serials, the global sequence, the frame guard, the capture probe, the panic hook, `MAP_SHARED` spools. |
| `sensorium-transform` | The `syn` rewriter. Pure: source + tier config in, spliced source + a site manifest out. No I/O. |
| `cargo-sensorium` | One binary with four roles: the `cargo sensorium` driver, the workspace wrapper cargo calls per unit, the target runner, and the converter that turns spools and manifests into traces. |

**What v1 records** — tier `call`: calls and returns with an outcome and a
captured return value, panics, threads as tasks (libtest's per-test threads and
the ones your code spawns). Workspace crates only, Linux, stable rustc, no
nightly, no root, no hand annotation. What it does *not* see, and what says so
in the trace, is [`HONESTY.md`](HONESTY.md) — read that before you trust an
answer. The trace contract both recorders are written against is
[`../docs/TRACE-FORMAT.md`](../docs/TRACE-FORMAT.md).

## Build

    cd rust && cargo build --release

Build the driver `--release` for anything you intend to measure: it hashes
itself to key the per-version shim, and a debug binary makes that ~0.5 s of
fixed cost on every invocation against 0.025 s for a release one.

Set `CARGO_TARGET_DIR` if your root disk is small: an instrumented build keeps
its own artifact set alongside the plain one, which is what lets the two
coexist and what makes it cost disk.

## Install

    cargo install --path rust/cargo-sensorium      # from the repository root

That puts `cargo-sensorium` on `PATH`, which is what makes `cargo sensorium` a
cargo subcommand. Reading the traces needs the Python side too: `sensorium`
0.6.0+ reads these traces. An older reader opens them — they are format 4 and
carry every required key — but narrates them in Python's words, which is a
claim about provenance the trace does not carry.

## Record

    cargo sensorium test [--tier off|call] <cargo test args…>
    cargo sensorium run  [--tier off|call] <cargo run args…>

Everything after the tier flag is your cargo command line, unchanged: `-p`,
`--lib`, `--test NAME`, `--exact`, `-- --test-threads=1`, all of it. Cargo
stays the runner and the builder; sensorium only changes what gets compiled and
watches what comes out.

`--tier off` compiles exactly the same artifacts and gates emission at runtime,
so switching tiers rebuilds nothing.

Everything the tool writes inside your workspace lives under
`<target>/sensorium/` — the mirror it builds in, the per-unit manifests, and
the spool directory for the invocation. Your sources, your `Cargo.lock` and
your plain artifacts are untouched, and a plain `cargo test` afterwards is
still plain.

## What it prints

One line per trace it converted:

    run: <id>  pid: <pid>  exe: <basename>  events: <n>  threads: <k>  exit: <status|unwitnessed>

`exit:` is a status somebody waited for, or `unwitnessed` for a process the
runner did not start (a child a test spawned itself). It is never cargo's
status wearing this process's name — see `HONESTY.md` §5.

When one invocation produced more than one test binary you also get:

    WARN: this invocation produced N test binaries; a single-target selector (--lib, --test X, --bin X) makes one trace the answer

That is not an error. `diff`, `refocus` and every "was this the same
execution" question are per-process concepts, so a question about *one* binary
wants a run of one binary.

## Where traces go

`$SENSORIUM_DIR/traces/`, default `~/.sensorium/traces` — the same place the
Python recorder writes, so one `sensorium runs` lists both. A trace holds the
recorded process's environment, command line, source digests and captured
values in plaintext; treat one the way you would treat a core dump.

## Ask

    sensorium runs                                 # what have I recorded
    sensorium info last                            # what am I looking at
    sensorium tree last --depth 3                  # what actually ran
    sensorium frame last --fn compute              # one activation, in full
    sensorium grep last compute --kind RETURN      # every event that mentions it
    sensorium diff RUN_A RUN_B                     # where two runs part
    sensorium diff --ignore-moves RUN_A RUN_B      # …across a refactor that moved code

On a Rust trace, `info` adds the toolchain, the invocation and binary, the
per-unit counts (`instrumented`, `fell back`, `skipped`, spawn sites), the
child runs linked to this process, live threads at exit, and any `seq gaps` or
dropped records. `runs` groups a whole invocation under one header.

## What refuses, and why

Four commands refuse outright on a Rust trace in this version. Each prints why
and exits 2; none of them answers from a capability the recorder declared it
does not have.

| Command | Why |
|---|---|
| `exceptions` | The Rust disposition rules are rung 3; the Python rules would misread `Err` values as exceptions. Nothing is judged. |
| `refocus` | Rung 4 — `capabilities.refocus: false`. |
| `watch`, `flow` | Per-line state and locals are rung 4 — `capabilities.line: false`. |

## Not yet

`?` sites, sinks and `Err`-arm classification (rung 3, with the Rust
`exceptions` rules); locals and LINE capture under `--focus`, and `refocus` by
re-invocation (rung 4); program output under libtest; `async fn` bodies, which
are declared-and-skipped rather than given a frame that would be wrong;
object identity, which Rust does not have an equivalent of.

The design and its rungs are in
`../docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md`; what
rung 1 measured, including everything it could not do, is in
`../docs/superpowers/spikes/2026-09-02-rust-mechanics-spike.md`.

## Cost

Reported, never gated. Recording a bloomery test suite measured
indistinguishable from a plain run at the suite's own granularity, and about
+5 ns per site on call-dense code at `opt-level = 0` — two readings roughly
1900× apart in event density, and both true. `HONESTY.md` §10 states them
together, with the lens on each; the acceptance document carries the numbers
with their `n`.
