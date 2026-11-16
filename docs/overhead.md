# Overhead: measured, never gated

The README's `## Overhead` section, **moved here 2026-09-16 (the MCP stdio
slice) so `README.md` stays under 800 lines**, wording and order unchanged.
The `docs/query.md` precedent of 2026-09-06. The README keeps three lines and
a link.

**Measured on this machine** (AMD Ryzen 7 9800X3D, Linux 7.0.0-28-generic,
CPython 3.14.4) with `python corpus/run_corpus.py --bench`:

    workload            tier      baseline  recorded       x    events  us/event
    call_dense          default     0.0092    1.2486   136.0    185428       6.7
    call_dense          focused     0.0088    1.7052   194.2    278140       6.1
    work_between_calls  default     0.1104    0.3146     2.9     24004       8.5
    work_between_calls  focused     0.1096    0.4473     4.1     48006       7.0
    async_call_dense    default     0.0314    0.3174    10.1     40004       7.1
    await_dense         default     0.0502    0.2347     4.7     40004       4.6
    await_dense         focused     0.0502    0.3714     7.4     60005       5.4

    recorder fixed cost: 0.036s on a program that does nothing (0.0074s -> 0.0432s)

**Derived parentage and task identity cost more in situ than on paper.** The
0.2.0 design note predicted about 0.05 µs/event for the pair; measured
against 0.1.0 on the same machine the same day, each side best-of-three in
its own fresh venv, `call_dense` went **6.0 → 6.5** µs/event (+8%) and
`work_between_calls` **8.3 → 8.4** (+1%), with the call-dense multiplier
moving **113× → 135×**, roughly half that per-event cost restated and half
the two builds' baselines differing by a millisecond. So the in-situ cost is
**0.1–0.5 µs/event** depending on call density, five to ten times the
prediction, recorded here as a finding rather than restated.
`async_call_dense` pays the task-identity path in full at 7.1 µs/event, about
0.4 µs above the synchronous call-dense case on this box, and registers no
focus target (its body only calls a one-line function), so it is reported for
the default tier alone; `await_dense` prices coroutine-body focus instead.

Two later arcs were measured the same way against the worktree immediately
before each, and neither moved a row past run-to-run noise. **Arc 2a's**
frame-and-suspension bookkeeping: **6.7/8.5/7.1** µs/event against 0.2.0's
**6.7/8.1/7.6**. **Plan 2b's** per-task fingerprint, whose cost falls only on
events inside a task, so the async rows are where movement would show and the
synchronous ones are the control: `call_dense` held at **6.7/6.1**
(default/focused), `async_call_dense` **7.2 → 7.1**, `await_dense`
**4.5 → 4.6** and **5.3 → 5.4**, `work_between_calls` **8.3 → 8.5** and
**6.8 → 7.0**, largest move **+0.2 µs/event**, the size of the run-to-run
noise reported elsewhere here. Both sets are deltas against a WORKTREE rather
than a release, which is why they are written here and nowhere else:
`CHANGELOG.md` records what shipped, not what did not move.

Two costs plan 2b adds that a per-event figure does not show. **Memory**: the
recorder holds one `Fingerprint` per asyncio task the run created, for the
lifetime of the process, measured here with `tracemalloc` at **220 bytes per
task** (the dict entry and the object together), so a program that creates a
million tasks over its life pays about 220 MB whether or not those tasks are
still alive. **Exit**: every task's fingerprint row is written at `uninstall`,
after the program has finished, in ONE transaction, measured at **4.6–5.4 µs
per task** on this box's ext4 (1,000 rows, best of five). It was one
transaction per row until 0.4.0's final wave, which cost 1.3–3.2 ms per task:
recording a 2,000-task program took 2.18 s of wall clock where it now takes
0.35 s, all of the difference being `fsync` charged to a process the user had
already watched finish.

An await-heavy program roughly **doubles its event count**, and that is a cost
the per-event figures above do not show: every suspension is one YIELD plus
one RESUME on the same frame, so `await_dense`'s 20,000 awaits are 40,004
events, 40,000 suspension rows and the four CALL/RETURN rows its two function
calls make. A program that never suspends records nothing new. That workload
is what prices suspension on its own: 4.6 µs/event by default (5.4 focused),
of which ~0.9 µs is the amortised 0.036 s boot from the fixed-cost row above,
so about 3.7 µs of real per-event work. Against the **~114 ns** the design
note measured for the bare `sys.monitoring` PY_YIELD/PY_RESUME callbacks, that
is roughly 32× the floor (40× on the 4.6 µs figure, boot included), the rest
being the trace write and the derived-state bookkeeping. `us/event` is the
figure that travels; the multiplier tracks how call-dense the program is.

These are measurements of one machine and four workloads, not a promise about
yours. The multiplier is not a property of sensorium: recording costs
**4–9 microseconds per event** here (4.6 on the per-suspension `await_dense`
case, 6.7 call-dense, up to 8.5 on `work_between_calls`) and how much that is
depends entirely on how often the traced program calls or suspends.
`call_dense` is naive recursive `fib`, close to the worst case that exists;
`work_between_calls` does real work inside each call, which is what ordinary
code looks like. Times are whole-command wall clock (best of three, after an
untimed warm-up), so every row includes interpreter startup and recorder
boot; the fixed cost is printed separately so it can be subtracted.

`--focus` costs one further event per executed line of the focused code, so
its price depends on what you point it at: at the hot recursive function
above it adds a third again, and pointed at a function whose body is a hot
inner loop it would cost far more.

TypeScript and Rust pay for call arguments on the default tier from
`sensorium-ts` 0.6.1 and `sensorium-rt` 0.7.1. Each argument is the same
capture a return already was: 200 bytes of `util.inspect` or `Debug` text.
Rust writes them into the CALL payload, which stops at 2048 bytes; a tail
that does not fit is dropped and the row says `unread: ["locals"]` beside
the arguments it kept. The closure that formats them is not called at
`--tier off`. `--focus` is unchanged: it is still one LINE event per
executed statement. `watch` still needs that tier. `flow --value` searches
returns and call arguments without it and warns that statement locals were
not recorded.
A `Debug` impl of a standard collection still walks every element before
the cap is applied (`rust/sensorium-rt`'s `probe.rs`); the bound is on what
is stored, not on that walk. No new multiplier was measured for this change.

**Caps, measured 2026-11-14** on this host (Linux 6.12.113+, 8 vCPU Intel
Xeon, CPython 3.13.5). The program is a loop that calls `leaf` 200,000
times; `leaf` returns `(n * 3) % 97`. Wall clock is best of three after one
untimed warmup, each rep in a fresh `SENSORIUM_DIR`. The before column is
the tree before this change. The after column is the default cap
(100,000 events, 8 MiB, 1,024 calls of one function).

    column     baseline   recorded      x    events        bytes  elided
    before       0.0179     6.4187  358.6    400004    52482048       0
    after        0.0178     0.4348   24.4      2052      315392  198976
    --no-cap     0.0178     6.4521  362.5    400004    52482048       0

The capped trace is marked truncated (`hit: ["max_calls"]`). `--no-cap` on
the same tree writes the same 400,004 events and the same 52,482,048 bytes
the uncapped recorder wrote before. Each `leaf(i)` payload differs, so
string interning does not shrink this file. A separate run of 5,000 calls
that all return the same 200-character string, recorded with `--no-cap`,
stores the first payload inline and 4,999 later copies as `#<id>`: the
trace is 1,167,360 bytes where storing every copy inline would be
2,296,906 (1,129,546 bytes kept out of the file).

Reading a trace back is a separate cost from recording one, and it is
reported here rather than gated, same as everything else in this section:
`info` on a 93k-event/44k-frame trace (`20260901-210520-7f8854`) took 54.4 s
before the reader fix (an unindexed `LEFT JOIN` scanning `frames` once per
`CALL` row) and takes 0.08 s after it, on this box.

**C recorder, measured 2026-11-15** on this host (Linux 6.12.113+, 8 vCPU,
gcc 14.2.0, CPython 3.13.5). `c/sample/fib.c` `fib(27)` is 635,622 calls
and prints 196418. Plain `-O0 -g` with a frame pointer and no inlining,
best of three: 0.0018 s. The same binary linked with the C runtime,
recording on, convert not included, best of three: 0.432 s. The spool
was 116,954,747 bytes. One `sensorium c run` of that binary took 31.5 s
wall. A separate convert of one spool took 84.7 s and wrote a
176,218,112 byte trace (1,271,244 events). Convert time moved between
those two samples. The converter is Python. Not a gate.
