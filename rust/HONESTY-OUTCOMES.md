# The Rust recorder's honesty ledger — §1: what a frame's outcome means

Section 1 of [`rust/HONESTY.md`](HONESTY.md), **moved here 2026-09-05 (the
borrow repair) so that file stays under 800 lines**. The split
`docs/CARRIED-DEBT.md` named at rung 3's close — "the next split is now named:
**§1**" — is this one; the section is unchanged in wording and order, and
`§1` still names what it always named, one file away.

## 1. What a frame's outcome means

Every frame closes with exactly one outcome, carried in the RETURN event's
payload as `{"outcome": "ok" | "err" | "panic" | "none"}`.

- **`ok` / `err` are read from the value at the exit operand** — the tail
  expression, and every `return <e>` at closure depth 0, of a function whose
  return type is neither `()` nor `!`. `err` means that value was
  `Result::Err` *at the moment it crossed the function boundary*; `ok` means it
  was anything else, `Result::Ok` and non-`Result` values alike. This is a fact
  about the boundary, not about the body: an `Err` built and absorbed inside
  the function never shows as `err`, and an `Ok` that wraps a failure of some
  other kind is `ok`.
  **Amended 2026-09-05 (rung 3, design R1): an `err` outcome is now typed.**
  The exit probe knows `E`, so a RETURN record closing `err` carries
  `std::any::type_name::<E>()` beside the outcome, and the converter spends
  it on the origin RAISE it synthesises immediately before that RETURN
  (`how: exit`) — which is where a reader looks for the type, because the
  RETURN event itself carries no error-type key of its own
  (`docs/TRACE-FORMAT.md` §5). The outcome's *meaning* is unchanged; what is
  new is that an `Err` born by being **returned** now has an event to be
  reported at, instead of only a frame that closed. *Falsified by*
  `rust/sensorium-rt/tests/err_flow.rs`, `rust/cargo-sensorium/tests/convert.rs`
  and `docs/trace-format/vectors/v16-raise-handled-chain-serial-kind.json`.
- **A function with nothing to return** (`-> ()`, or no return type) has no
  exit operand to probe. Its frame closes `ok` with the recorded value `()`
  when it returned normally.
- **`panic` comes from the panic hook, and where it does not, the trace says
  so.** The guard reads `std::thread::panicking()` at *both* ends of its frame —
  once at `enter`, once when it drops — and closes `panic` only on a
  false-to-true transition across the frame (**amended 2026-09-03**; it used to
  read the exit alone). A panic that begins while the thread is already
  unwinding aborts the process, so a frame a `Drop` opened *during* someone
  else's unwind cannot have panicked itself: it closes on its own outcome, which
  for the usual `-> ()` `Drop` body is `ok`. Before the amendment such a frame
  read `panic` although it had returned, and the converter then attached the
  *outer* panic's message and serial to it. Falsifier:
  `rust/sensorium-rt/tests/outcomes.rs::a_frame_entered_during_an_unwind_did_not_itself_panic`
  (scenario `panic-truncated-before-spool`, whose `EntersOnDrop` local opens its
  thread's first spool from inside the unwind).
  The hook — installed on the process's first recording `enter`, chained to
  whatever was there — writes a PANIC record on that thread. The frame's
  `closed_by` is `"unwind"` and `unwind_exc` is
  `{"type": "panic", "msg", "serial", "loc"}` taken from the most recent PANIC
  record on the thread. `closed_by` is never the string `"panic"` — a reader
  renders that as a false ` (open)`.
  **A frame can still close `panic` with no PANIC record to take it from**, and
  it is not a lookup failure: the program installed its own hook *after* ours
  (ours is gone; the program's own output is unaffected either way), or the
  thread's spool had gone inert and could not accept the hook's record (§4)
  (reasoned from `emit_if_open` → `Spool::record` refusing on `broken`; not
  exercised by a test in this wave).
  Then the converter writes `unwind_exc` as `{"type": "panic"}` with `"msg"` set
  to `"<panic message not recorded: no PANIC record preceded this unwind>"`, and
  counts the frame in the meta key `panics_unrecorded`. So a reader sees
  `unwind` with a named absence, never a message the recorder guessed. The
  first case is not reachable in a libtest-shaped run, where the test function's
  own `enter` comes first. A thread that panicked before it had recorded
  anything still gets no PANIC record at all — the hook opens no spool, because
  a hook that could fail could print, and printing on an already-panicking
  thread aborts the process (§4) — but it now leaves no `panic`-closed frame
  either: the only frames it opens are opened during the unwind, and they
  return.
- **`none` means a *value-returning* function's frame closed with nothing
  probed at its own site** — the qualifier matters, because a `-> ()` function
  also stashes nothing and reads `ok` (above): the wire carries no per-site
  knowledge, and the manifest's `ret: unit` is what separates the two at
  conversion. The ordinary cases, all of them properties of the source, are: a
  `?` that propagated past the tail, a syntactically diverging operand
  (`return`/`break`/`continue`, a `loop` with no valued `break`, a call of
  `panic!`, `unreachable!`, `todo!`, `unimplemented!`, `std::process::exit`,
  `std::process::abort`), or a `-> !` function. `none` is not "no error"; it is
  "this trace does not know".
- **That list is not closed, and the mechanism can produce `none` too.** A
  frame's exit operand leaves its capture on a per-thread LIFO stack keyed by
  `(site, frame depth)`, and the frame's own guard takes it back — top of stack,
  both keys matching, or nothing. The key is what makes the ordinary case safe:
  a local (or a tail temporary) whose `Drop` calls instrumented code opens a
  whole frame *between* an exit operand and its guard, at the same site if the
  `Drop` re-enters the same function, and neither frame can take the other's
  value. What remains, stated rather than left to be found:
  **the stack holds 64 pending captures**, and a 65th is refused, so that frame
  closes `none` — 64 is the depth of a chain of `Drop`s that each call
  instrumented code, not of the call stack, so no measured workload comes near
  it; and a capture left by a frame whose CALL was never written (its spool had
  already failed, so `records_dropped` is non-zero) is taken by nobody. Neither
  is signalled beyond the `none` itself. A run whose `records_dropped` is zero
  has met neither.
- **A generic return type reads `ok` even when the value is an `Err`.** The
  capture probe's specialisation is resolved where the fragment sits — inside
  the generic function, where `T` is not known to be a `Result` — so a
  `fn f<T>() -> T` monomorphised to `Result<_, _>` and returning `Err` closes
  `ok`. The outcome is a property of the *static* type at the exit operand.

**Falsified by** `rust/sensorium-rt/tests/panics.rs` (the PANIC record's
location, message and non-string payload, and the wire order CALL, PANIC,
RETURN `panic` on one thread), `rust/sensorium-rt/tests/outcomes.rs` (one arm
per outcome, read off the spool bytes by a parser written from the wire
format, not from the writer — including the three arms that pin the stack: a
`Drop` that calls a `-> ()` unit fn while an `Err` is pending, a `Drop` that
re-enters the same site one level down, and a re-entered site whose own frame
leaves by `?` and so must not take the outer frame's capture),
`corpus/rust/panic` (`closed_by unwind`, `unwind_exc.type panic`), and
— for the generic case, which this rung does not fix —
`corpus/rust/outcome_generic`, **deferred to rung 3** and named here so the
limit has an address before it has a test.
