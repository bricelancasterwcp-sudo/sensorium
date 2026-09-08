# rust/ — the sensorium recorder for Rust

Record what a Rust program actually did; ask it the same questions.

`cargo sensorium test` wraps one `cargo test` invocation, instruments your
workspace's own crates at build time, and writes one sensorium trace per
process — the same SQLite format 4 the Python recorder writes, read by the same
`sensorium` command line. It exists for the same reason the Python side does:
reading logs is reading a diary, and this is watching the execution.

Three crates, all `publish = false`: **`sensorium-rt 0.4.0`**,
**`sensorium-transform 0.4.1`** and **`cargo-sensorium 0.5.0`**. All three
were `0.4.0` at the focus tier of 2026-09-06 (a new wire kind, LINE, and the
`--focus` flag that mints it); on 2026-09-07 the refocus slice moved
`sensorium-transform` alone to `0.4.1` for the brace-delimited-macro-tail
guard (a `src` fix to what a focused build emits) and `cargo-sensorium` alone
to `0.5.0` for `--refocus-of` and the three invocation-scoped meta keys it
writes — neither the wire nor the runtime felt either change, which is why
`sensorium-rt` stayed at `0.4.0`.
Before that all three were `0.3.0` at the err-flow rung of 2026-09-05
(wire v3: RAISE/HANDLED records, a typed `err` RETURN, and the `err_flow`
capability); later that day the borrow repair moved `sensorium-transform` and
`cargo-sensorium` to `0.3.1` and left `sensorium-rt` at `0.3.0`, because
neither the wire nor the runtime changed. Before all that,
`sensorium-transform` and `cargo-sensorium` were `0.2.0` from the spawn-naming
change of 2026-09-03 and `sensorium-rt` was `0.1.0`:

| Crate | What it is |
|---|---|
| `sensorium-rt` | The runtime linked into every instrumented unit. Zero dependencies. Thread serials, the global sequence, the frame guard, the capture probe, the panic hook, `MAP_SHARED` spools. |
| `sensorium-transform` | The `syn` rewriter. Pure: source + tier config in, spliced source + a site manifest out. No I/O. |
| `cargo-sensorium` | One binary with four roles: the `cargo sensorium` driver, the workspace wrapper cargo calls per unit, the target runner, and the converter that turns spools and manifests into traces. |

`sensorium-rt`'s zero-dependency policy and `cargo-sensorium`'s own policy
against a `sha2` dependency each carry their own from-scratch, NIST-vector-pinned
SHA-256 (`env_hash` in the runtime, `tool_hash`/`source_hashes` in the driver) —
two ~200-line files kept in sync by the same test vectors, a duplication
D1 forces rather than an oversight (design spec §2.3, D1 in the rung-2 plan).

**What v1 records** — tier `call`: calls and returns with an outcome and a
captured return value, panics, threads as tasks (libtest's per-test threads and
the ones your code spawns), and — since 0.3.0 — **err flow**: a record at every
`?` on a `Result`, at the four written sinks, at `let _ = <value>` and at every
classified `Err` arm, which is what makes `sensorium exceptions` answer here
instead of refusing. Since 0.4.0, and only under a `--focus`, it also records
**one LINE per completed statement** of the named functions, carrying the
bindings that statement wrote — which is what makes `watch` and `flow` answer
here. Since `cargo-sensorium` 0.5.0 it also records `refocus_of`,
`workspace_root` and `invocation_processes`, which is what makes
`sensorium refocus` re-run a recorded invocation one flag deeper and compare
the pair instead of refusing. Workspace crates only, Linux, stable rustc, no
nightly, no root, no hand annotation. What it does *not* see, and what says so
in the trace, is [`HONESTY.md`](HONESTY.md) with
[`HONESTY-BLIND-SPOTS.md`](HONESTY-BLIND-SPOTS.md) and
[`HONESTY-ERR-FLOW.md`](HONESTY-ERR-FLOW.md) — read those before you
trust an answer. The trace contract both recorders are written against is
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
0.6.0+ reads these traces, **0.8.0+ is what `exceptions` needs**, and
**0.8.3+ is what `watch` and `flow` need on a focused trace** — the `::`
qualname boundary and the rules for reading a `dbg` capture are 0.8.3's — and
**0.8.4+ is what `refocus` needs on a Rust trace**, its re-run path being
0.8.4's, against a trace a 0.5.0 driver wrote. An
0.6.0/0.7.0 reader opens a 0.3.0 trace and answers every other question, but
its `exceptions` still refuses, because the Rust disposition rules are 0.8.0's.
A reader older than 0.6.0 opens them too — they are format 4 and carry every
required key — but narrates them in Python's words, which is a claim about
provenance the trace does not carry.

## Record

    cargo sensorium test [--tier off|call] [--focus <qualname>…] [--refocus-of <run id>] <cargo test args…>
    cargo sensorium run  [--tier off|call] [--focus <qualname>…] [--refocus-of <run id>] <cargo run args…>

Everything after the flags is your cargo command line, unchanged: `-p`,
`--lib`, `--test NAME`, `--exact`, `-- --test-threads=1`, all of it. Cargo
stays the runner and the builder; sensorium only changes what gets compiled and
watches what comes out.

`--tier off` compiles exactly the same artifacts and gates emission at runtime,
so switching tiers rebuilds nothing.

### `--focus`: per-line answers, for the functions you name

`--focus <qualname>` splices a probe after every statement of each function it
selects, so the trace carries one LINE event per completed statement with the
bindings that statement wrote. It is **repeatable**, it takes the file-local
qualname the recorder itself prints (`Counter::new`, `tests::fill`), and a
value that names a CONTAINER selects its children — `--focus Counter` selects
`Counter::new` and `Counter::add`, matching on the `::` boundary so
`--focus Counter` never quietly selects `Counters::new`.

Resolution happens **before anything is built**, against the workspace's own
sources and the transform's own eligibility rule. A value that matches
nothing is refused at exit **2** with nothing built and up to three
suggestions:

    REFUSED: --focus no_such_fn matches no function in the workspace; nothing was built. Closest: fill, …

A value whose only matches are functions the transform never instruments
(`async`, `const`, `extern`, macro-produced) is refused the same way, naming
every one of them with its reason — being told only the first would mean
meeting the same refusal again. A focus that resolves prints one line per
selected qualname on stderr before cargo runs, so a record of a run can quote
what the focus actually selected rather than what was typed:

    focus: fill

The tier is a **compile-time** decision, so it is the build that carries it:
a focused build declares `capabilities.line` and `capabilities.locals` true
and records `focus` and `focus_matched` in the trace's meta, and an unfocused
build of the same crate declares both false and carries no LINE row at all.
`sensorium info` prints both — `line=yes locals=yes`, and the `focus:` line —
so a later reader knows what was instrumented without having launched it.
What a focus still does not reach is `HONESTY-BLIND-SPOTS.md` item 3.

### `--refocus-of`: this run is a re-run of that one

`--refocus-of <run id>` records the new trace as a re-run of an existing one:
the id reaches every process of the invocation and the converter writes it as
`meta.refocus_of`, which is the link `sensorium refocus` finds the pair by and
the `refocus-of:<run>` `runs` prints. It is **not** a flag you normally type —
`sensorium refocus <run> --focus <name>` is what builds this argv and runs it
from the workspace the original recorded (see `../docs/query.md`) — but it is
what the driver takes, and it is documented here because the trace carries it.

At most once (`--refocus-of given twice`, exit **2**), and recognised only
before the first bare `--`, like `--tier` and `--focus`, so a test binary's own
argument of that spelling is left alone. **Two refusals, both before anything
is rewritten or built:**

    REFUSED: --refocus-of ../traces/20260101-000000-abcdef is not a run id; nothing was built.
    REFUSED: --refocus-of 20260101-000000-abcdef names no trace in /home/you/.sensorium; nothing was built.

The first is the shape check — a path separator, `.`, `..`, an absolute path or
an empty value — and it runs before the store is consulted, because
`--refocus-of ../traces/<a real run>` would otherwise stamp a link the store
could never resolve (design 2026-09-07, amendment B2); a trailing `.db` is
stripped once, so `<id>.db` names `<id>`. The second is the existence check
against the current store, and it names the store ROOT — what `SENSORIUM_DIR`
was set to, which is what a person can act on — not the `traces` subdirectory
the file was looked for in
(`tests/refocus_of_gate.rs` pins both sentences through the binary).

Two more invocation-scoped meta keys ride along with it and are written on
every run, refocus or not: `workspace_root`, the workspace the invocation ran
in, and `invocation_processes`, the number of runner processes it produced —
test binaries and doctests alike. They are what `sensorium refocus` reads to
decide whether a re-run of this recording would be legitimate at all.
`TRACE_FORMAT` stays **4**: all three keys are optional meta.

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

The same goes for the spool directory the recording itself writes,
`<target>/sensorium/spool/<invocation>/`: each `<pid>.proc.json` there carries
the **full process environment** in plaintext, at whatever your umask gives it,
and the `.spool` files beside it hold the captured return values. Conversion
does not remove them. Treat that directory as a core dump too — it is inside
`target/`, so a `cargo clean` takes it, and it should not be uploaded as a
build artifact.

## Ask

    sensorium runs                                 # what have I recorded
    sensorium info last                            # what am I looking at
    sensorium tree last --depth 3                  # what actually ran
    sensorium frame last --fn compute              # one activation, in full
    sensorium grep last compute --kind RETURN      # every event that mentions it
    sensorium diff RUN_A RUN_B                     # where two runs part
    sensorium diff --ignore-moves RUN_A RUN_B      # …across a refactor that moved code

On a Rust trace, `info` adds the toolchain, the invocation and binary, the
per-unit counts (`instrumented`, `fell back`, `skipped`, spawn sites), any
`unreached files` a module walk could not reach, the `unit ceiling` line if
this process hit the 256-unit refusal, the child runs linked to this process,
live threads at exit, and any `seq gaps` or dropped records. `runs` groups a
whole invocation under one header.

## What refuses, and why

No command here answers from a capability the recorder declared it does not
have, and each refusal names the capability and the recorder. `watch` and
`flow` print why and exit **3** — change the recording, not the call — but
only on a trace recorded WITHOUT a `--focus`; on a focused one they answer.
`exceptions` answers from 0.3.0, and refuses on exactly one thing: a trace an
older runtime wrote, which carries no err-flow records to judge. `refocus`
answers from 0.5.0 and no longer refuses on the capability for traces that
driver converts; on a recording an OLDER driver made it still does, because
that trace declares `capabilities.refocus: false`. On a 0.5.0 trace the five
refusals are about this particular RUN instead, and each exits **2** with
`nothing was re-run` in it — see below.

| Command | Exit | Why |
|---|---|---|
| `exceptions` | 3, **only on a pre-0.3.0 trace** | `capabilities.err_flow: false` — the recorder produced no RAISE/HANDLED records, so there is nothing to judge. On a 0.3.0 trace it answers. |
| `refocus` | 2, **only on a pre-0.5.0 trace** | `capabilities.refocus: false` — recorded before the driver could be re-invoked, so nothing was re-run and the reader's next move is a different command. A trace a 0.5.0 driver converted declares `refocus: true` and is refused, if at all, by one of the five per-run sentences below. |
| `watch`, `flow` | 3, **only on an unfocused trace** | `capabilities.line: false` — no `--focus` was given, so no LINE record exists. On a focused trace they answer. |

The unfocused refusal, in full — the sentence
`corpus/rust/focus_unfocused_refuses` pins byte for byte:

    REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 declares it does not produce (capabilities.line: false); nothing was checked

## Not yet

`--window` (a per-activation runtime check the Rust runtime lacks, so a
`refocus --window` is refused by name at exit 2); a refocus of a multi-process
invocation, which is refused rather than compared; program output under
libtest; probes in closure and `async` bodies; place writes (`*p = e`,
`a.b = e`) and `&mut` mutation as deltas; arguments on a CALL row;
`flow --object`, since object identity is not a thing Rust has an equivalent
of. `?` sites, sinks and `Err`-arm classification **shipped in rung 3**
(0.3.0) — what they still cannot see is `HONESTY-ERR-FLOW.md` §11 and
`HONESTY-BLIND-SPOTS.md` items 15–26. LINE and locals under a `--focus`
**shipped in rung 4 slice 1** (0.4.0) — what they still cannot see is
`HONESTY.md` §12 and `HONESTY-BLIND-SPOTS.md` item 3, narrowed to exactly
that. `refocus` by re-invocation **shipped in rung 4 slice 2**
(`cargo-sensorium` 0.5.0), measured as **E4** over 61 tests of a real
workspace — what it still does not compare is `HONESTY.md` §13 and
`HONESTY-BLIND-SPOTS.md` item 12, narrowed the same way.

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

**What err flow added, reported the same way.** On the rung-3 acceptance run
(`../docs/superpowers/acceptance/2026-09-04-sensorium-rung3-acceptance.md`,
*reported without a gate*) the clone's `-p bloomery-daemon --lib` suite ran
**0.063 s plain against 0.132 s recorded**, medians of n=5 alternating arms
with the load recorded per arm — a difference of 0.069 s on a near-vacuous
workload, which is the honest way to read it rather than as a ratio. The
records themselves are cheap and rare: **13 RAISE and 17 HANDLED events in
1 424** on that trace, at 405.573 bytes per record over a 577 536-byte file.
A RAISE or HANDLED costs more bytes than a CALL — it carries a type name and
the `Err`'s capped `Debug` text, ≈ 60–350 bytes against a CALL's 24 — and
there is no type-intern table, which was a decision for simplicity with this
number as its check.

**What a focus costs, reported the same way — and what E9 could not measure.**
A focus is part of the build's cache key: the wrapper shim's path carries the
focus hash, so every distinct focus gets its own `-C metadata`, its own mirror
and its own unit manifests, and those **accumulate in the target directory**
across invocations. The shim itself stopped being a per-focus COPY in
`cargo-sensorium` **0.5.1**: it is a **hard link** to the driver wherever the
target directory shares the driver's filesystem, and a copy only where it
cannot be — another mount, or any other error, both named in one message if the
copy fails too. Sharing the driver's inode is safe because the key already
hashes the driver's own bytes, so a replaced driver takes a different key and
no live shim is ever written through. One consequence for anyone sizing the
directory: `du` over `<target>/sensorium/shim` counts those bytes **once**
however many focused keys are present, and a per-entry sum would report a
number the disk never held. Budget one artifact set per distinct focus — that
is the part that still accumulates — and expect a focused build after an
unfocused one to compile rather than to be `Fresh`. The runtime cost of the probes themselves
is **not measured**: on the rung-4 acceptance run
(`../docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md`, endpoint
**H6**, whose verdict is **REPORTED** with no gate) libtest reported
**0.00 s** for all four binaries — too fast to time at its resolution — and
the four invocation walls (U1 **6.693 s**, F1 **6.690 s**, U2 **1.448 s**,
F2 **6.587 s**) are each dominated by compilation, so *"neither isolates
run-time overhead"* (record §5.3). A cost claim needs a subject whose test
binary takes long enough to time and an instrument that separates compile from
run; this repository has neither yet, and says so rather than quoting a wall
as an overhead.
