# The Rust recorder's honesty ledger — §8: What this recorder cannot see

The numbered list of [`rust/HONESTY.md`](HONESTY.md) §8, **moved here
2026-09-05 (rung 3) so that file stays under 800 lines**. The section's own
framing paragraphs stay there; **the numbering is unchanged**, so item *n*
here is `rust/HONESTY.md` §8 item *n* — the spelling every code comment and
the ledger's index already use. Items 1–14 are rung 2's, verbatim except
item 2, which rung 3 narrowed to the recordings it is still true of. Items
15–26 are rung 3's own, from the design's R16 (`?`, sinks and `Err` arms:
`docs/superpowers/specs/2026-09-04-sensorium-rung3-err-flow-design.md`).

Each entry names **what declares it** — the field or line a reader meets
without knowing this document exists — and, where one exists, what could
falsify it. A bare `§n` below is a section of `rust/HONESTY.md`.

**What it does see, so the list below is bounded.** Every function item with a
body in a workspace crate gets a frame, except the skips items 5 and 6 declare;
every unit either instruments or says it fell back. Rung 1 measured 100.0% of
eligible function items on bloomery (2051/2051), and this rung re-measures it
as **E2′**, where a floor of 98% applies and *any* fell-back unit is a finding
that stops the rung until it is explained. *Falsified by* E2′ in
`docs/superpowers/acceptance/2026-09-02-sensorium-rung2-acceptance.md` and by
`rust/sensorium-transform/tests/census.rs`, which requires
`instrumented + async == eligible` over a real workspace's files.

1. **Dependency-crate internals.** Only workspace units are instrumented
   (cargo's workspace wrapper is the hook). A call into `serde` or `tokio`
   shows as the caller's frame and its return; the inside is not there.
   *Declared by* the meta key `instrumented_units` and `info`'s
   `units: N instrumented, …` line.
2. **`?` sites, sinks, and `Err` arms, on a recording made before
   `sensorium-rt 0.3.0`.** Rung 3 landed them (§11 there, and items 15–26 below say
   what err flow still cannot see), so this item is **narrowed 2026-09-05**
   rather than struck: it is exactly true of every trace an earlier runtime
   wrote, and those traces do not stop existing. On one of them no RAISE or
   HANDLED is recorded at a `?`; `.ok()`, `.unwrap_or*()`, `let _ =` and
   `Err(..) =>` arms are not classified; and everything the trace says about a
   `?` that propagated is `outcome: none` on the frame it left (§1).
   *Declared by* the absence of `capabilities.err_flow`, which reads `false`,
   and by the refusal `exceptions` prints against it —
   `REFUSED: exceptions needs err_flow, which recorder sensorium-rt 0.2.0
   declares it does not produce (capabilities.err_flow: false); nothing was
   checked` — exit 3. *Falsified by* `docs/trace-format/vectors/v19-err-flow-capability-refusal.json`
   and `tests/test_exceptions_rust_gate.py`.
3. **Locals, and per-line state — rung 4.** Nothing is captured between a
   function's entry and its exit, so a value that changed in place mid-frame,
   including mutation through a long-lived `&mut`, is invisible. *Declared by*
   `capabilities.line: false` and `capabilities.locals: false`; by the
   `"unread": ["locals"]` marker every CALL payload carries, which `tree`
   renders as `name() <unread: locals>` and `frame` as
   `args: <unread: locals>` — never `(none)`, which would read as "called with
   no arguments"; and by the refusal `watch` and `flow` print:
   `REFUSED: watch needs line, which recorder sensorium-rt 0.1.0 declares it
   does not produce (capabilities.line: false); nothing was checked`.
4. **What the program printed.** libtest owns the capture and the hook that
   would take it is unstable. *Declared by* `capabilities.output: false`: the
   `output` table is empty, and every reader prints the declaration instead of
   a zero.
5. **`async fn` bodies.** Skipped whole — an entry guard would live across
   every `.await`, and the guard is the sole emitter of a RETURN (§1) — so an
   async
   function gets no frame at all rather than a wrong one. *Declared by* the
   manifest's `skipped: [{reason: "async"}]`, carried into the meta key
   `skipped` and printed by `info` as `K skipped (<reasons>)`. bloomery has
   zero; a workspace with async functions gets one skip record each and no
   invented frames.
6. **`const fn`, `extern` functions, and function bodies inside
   `macro_rules!`.** Same declaration, reasons `const`, `extern`, `macro`.
   A `?` inside a macro argument is invisible to the parser for the same
   reason; that is rung 3's problem and rung 3's manifest field.
7. **A unit that fell back to the real tree.** Nothing in it is instrumented:
   no frames, no returns, no sites. The reasons are `rustc: <first error
   line>`, `lto`, `cross-target`, an absolute crate root, and
   `wrapper: <error>`. *Declared by* the unit manifest's `fell_back: true` and
   `fallback_reason`, the meta key `uninstrumented`, and `info`'s
   `M fell back (<reasons>)`. **Every** fallback path writes or patches a
   manifest — rung 1 had one that reported to the log channel only, and a
   coverage check reading manifests alone would have scored it as instrumented
   (findings §5.29). A fallback in a shared `tests/common/*.rs` uninstruments
   every test binary that includes it, and the manifests say which.
   **And a fallback is not always an escape.** A unit whose DEPENDENCIES are
   instrumented cannot be compiled plainly: their rmetas already reference
   `sensorium_rt`, so the passthrough rustc run needs the runtime as much as
   the instrumented one did. When such a unit falls back for a reason that is
   about the runtime's linkage, the plain compile fails with the same
   `E0463: can't find crate for <dependency>` and cargo's build fails —
   measured on the bloomery clone, 2026-09-03, on a fresh target with a wrapper
   that sent `--extern sensorium_rt=<rlib>` and no `-L dependency=<rt dir>`:
   `bloomery-daemon`'s lib unit was declared
   `fell_back: true, fallback_reason: "rustc: can't find crate for
   bloomery_core"` and the build then exited 101 anyway. The manifest is
   therefore the record of what the recorder did NOT instrument, never a
   promise that the build survived it.
   **The condition is the unit's own dependencies, not the fallback's reason.**
   A fallback replays the argv cargo built, with no `--extern` and no `-L` of
   ours, so *every* reason takes the same plain compile — including `lto` and
   `cross-target`, which are decided before instrumenting, and
   `wrapper: <error>`. A unit with instrumented dependencies therefore fails
   `E0463` on a `lto` fallback exactly as it does on a runtime-linkage one.
   "Recorded nothing, built fine" is what a fallback means **only when that
   unit's own dependencies are uninstrumented** — a leaf workspace crate, or
   one that depends only on registry crates. Which units those are is readable
   from the manifests: a fallen-back unit whose dependencies have manifests of
   their own is in the failing case.
   The linkage this rests on is the wrapper's `--extern sensorium_rt=<rlib>`
   **and** `-L dependency=<the rlib's own per-variant directory>` (plan
   decision D1 as amended): rustc resolves a dependency's own `sensorium_rt`
   through the search path, not the extern map.
8. **A module the module walk could not reach.** `#[cfg_attr(.., path = ..)]`
   is not evaluated — the walk resolves `mod` declarations and literal
   `#[path]`, and refuses to guess at a conditional one. *Declared by* the unit
   manifest's `unreached_files`, carried into the meta key of the same name
   over the units this process registered, and printed by `info` as
   `unreached files: N -- <paths>`. A file the walk never reached is a file
   whose functions have no sites at all, so the declaration has to travel with
   the trace: a limit whose declaration a reader cannot reach is half a
   declaration. bloomery has zero such files (findings §5.26).
   **Amended 2026-09-03** (rung-3 entry, Task-1 review B): `unreached_files`
   is not only the cfg-gated-path case above. A file the walk resolved but
   the wrapper could not READ, and a file the walk read but
   `sensorium-transform` REFUSED (an unparseable file, or one of the
   transformer's own synthesised errors — a spawn with no named item around
   it, a rewrite that would move a line, a wrapped spawn's ordinal
   disagreeing with source order) both land in `unreached_files` too, and
   only the last case carries a message: the wrapper prints `sensorium: unit
   <crate> (<metadata>): <rel>: <message>` on stderr and records `<message>`
   under the manifest key `unreached_reasons`, keyed by the same
   workspace-relative path. A file the wrapper cannot read gets no entry in
   `unreached_reasons` — `read` hands back an `Option`, so there is no
   message to quote, and inventing one would be worse than the silence.
   `fell_back` stays `false` for a refused file: this is one file's
   instrumentation lost, not the whole unit's, and every other file in the
   unit still is. The one exception is the crate root: if the file holding
   `__SENSORIUM_UNIT` is among the refused files, the whole unit ends up with
   no files instrumented at all (every guard would otherwise reference a
   static that does not exist) — still not `fell_back: true`; only
   `unreached_reasons` says why the unit came back empty. *Falsified by*
   (the refused CHILD-file half) `rust/cargo-sensorium/tests/wrapper_fallback.rs`'s
   `a_file_the_transformer_refused_names_its_reason_on_both_channels`, and (the
   refused CRATE-ROOT half, at the plan level) `wrapper.rs`'s unit test
   `a_unit_whose_crate_root_cannot_be_rewritten_is_left_wholly_alone`, which
   builds a unit whose root does not parse and asserts that `files`,
   `source_hashes` and `rewrites` are all cleared while
   `unreached_reasons["a/src/lib.rs"]` survives. What is untested as of
   2026-09-03 is narrower than "the crate-root half": the wrapper-BINARY path
   for a root refused by a SYNTHESISED error — the stderr line,
   `fell_back: false`, and the empty `files` as the driver writes them —
   has no fixture; rung-3 inbox.
9. **Why a return value was unread** (§2): a missing `Debug` impl and a
   panicking one read the same.
10. **A runner set in a workspace's `.cargo/config.toml`.** The driver sets
    `CARGO_TARGET_<HOST>_RUNNER` in the environment, which overrides the
    config file, and only an env-set `SENSORIUM_INNER_RUNNER` is chained. On
    such a workspace the recorded run is not the run the config describes —
    and **no field in the trace says so**. It is declared here, and in the
    acceptance document's §2 pins, which record that no config-file runner
    existed on the box or in the tree that was measured. *Falsified by* adding
    one to `rust/probes/ws/` and re-running `rust/tests/mechanics.sh`.
11. **Object identity.** There is no Rust `id()`: two `Vec`s with the same
    contents are one value to this trace. *Declared by*
    `capabilities.object_identity: false`; `flow --object` refuses.
12. **A deeper re-run.** `refocus` re-invokes the recorder and compares, and
    the Rust side of it is rung 4. *Declared by* `capabilities.refocus: false`;
    `refocus` refuses with the `caps.require` sentence, naming the capability
    and the recorder.
13. **Anything after the 256th instrumented unit in one process.** Unit ids
    run `0..=254`; the 256th distinct unit makes the runtime refuse to record
    rather than wrap the id and attribute events to the wrong unit, and every
    later `enter` in that process is inert. The refusal is **in the trace, not
    only on stderr**: the proc header's `refused` becomes that unit's metadata,
    the converter writes it as the meta key `units_refused`
    (`{"refused": bool, "at": <metadata or null>}`), and `info` prints
    `unit ceiling: recording REFUSED at unit <metadata> -- every later call in
    this process is unrecorded`. A trace past the ceiling is short **and says
    so**. The ceiling has never been approached (a workspace-wide bloomery
    build produced 108 units *in total*, findings §5.13), so the path is driven
    by a test and by nothing else yet. *Falsified by*
    `rust/sensorium-rt/tests/units.rs`.
14. **Everything the Python README's *What sensorium sees at all* rules out**,
    which is not language-specific: any file the program read or wrote, the
    environment beyond the variables a command names as compared, the clock,
    the network, and everything else the machine did. *Declared by*
    `source_hashes`, which is the whole of what the trace pins about the world
    outside the process — the source files the instrumented units were built
    from, and nothing else. Config, fixtures, databases and inputs move
    unseen.
15. **Absorbing shapes the grammar does not name.** `let … else`,
    `while let Err(..)`, `matches!(x, Err(_))`, `.err()`, an or-pattern arm
    (`Err(A) | Err(B) =>`), a let-chain (`if let Err(e) = x && c`), a *typed*
    `let _: T = e;`, and the closure of `.unwrap_or_else(|e| …)` that stores
    `e` are probed by nothing at all, so an `Err` that ends in one of them
    reads **AMBIGUOUS** — the designed default, never SWALLOWED.
    `.is_err()`/`.is_ok()` are on the same list by a *decision* rather than by
    omission: they take `&self` and observe rather than absorb, and a HANDLED
    there would report a predicate as a swallow (design R2's erratum of
    2026-09-04). *Declared by* the absence of any record at the site and by
    the AMBIGUOUS verdict `exceptions` prints for the chain. **Untested by
    fixture**: the design enumerates these shapes, and no golden pins that
    each one is left alone — a golden per shape is what would settle it.
16. **`.unwrap()` and `.expect()`.** Not probed; a panic on an `Err` is read
    from the panic hook instead, so the verdict is PANICKED and says "the
    frame holding it unwound", never that the panic was *because of* the
    `Err`. *Falsified by* `corpus/rust/unwrap_panic`.
17. **`?` on an `Option`.** The site is wrapped like any other, and the probe
    writes **nothing**: a `None` is not an error in this model, so no chain
    exists to report. *Falsified by*
    `rust/sensorium-transform/tests/errflow.rs::a_question_mark_on_an_option_is_wrapped_like_any_other`,
    the golden `try_option`, and `corpus/rust/none_propagation`.
18. **A real swallow inside a frame that then fails for another reason.**
    `let _ = cleanup(); work()?` absorbs the first `Err` and the frame closes
    `err`, so the chain ends `handled_then_failed` and reads **AMBIGUOUS**,
    not SWALLOWED. The absorption is real and the instrument declines to name
    it, because the frame did not go on as if the call had succeeded.
    *Falsified by* `corpus/rust/cleanup_then_fail` and the `handled_then_failed`
    row of `tests/test_exceptions_rust.py`.
19. **A generic `T` that is a `Result` only after monomorphisation** reads
    `ok`: the exit probe's ladder resolves on the pre-substitution type, so
    `Result`-ness gained at monomorphisation is invisible to it (§1).
    *Falsified by* `corpus/rust/outcome_generic`.
20. **Two `Err`s of one type with identical `Debug` text in one window are one
    chain.** There is no error identity on the wire; the chain machine follows
    `(holder frame, type, Debug text)`. A text the probe had to **truncate** is
    no identity at all — matching falls back to the type, which can only ever
    MERGE two chains, never split one. *Declared by* `exc.trunc` / `exc.type_trunc`
    and `docs/TRACE-FORMAT.md` §5. *Falsified by* `corpus/rust/interleaved_chains`
    and `docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json`.
21. **A conditional panic in an `Err` arm classifies the WHOLE arm PANIC.**
    `Err(e) => if c { panic!() } else { 0 }` gets no probe — the panic hook is
    the record, and a probe there would shift the panic's column, which E7″
    measures — so on the run where the arm does *not* panic its `Err` reads
    AMBIGUOUS. *Falsified by* (the unconditional half)
    `rust/sensorium-transform/tests/golden_errflow.rs::a_panic_arm_is_left_byte_for_byte_where_it_was`.
    The conditional half is **untested by fixture**.
22. **`Err(ref e) => note(e)` reads ESCAPED.** Only the literal `&e` argument
    and a `{}`/`{:?}` format argument of the logging family count as a
    provable shared borrow, so a binding reached any other way is treated as
    escaping. **ESCAPED is an upper bound, deliberately**: it costs AMBIGUOUS
    verdicts on arms that in fact handled, and never a false SWALLOWED.
    *Falsified by* the golden `err_arm_escaped`, whose controls are the two
    provable shapes; the `ref` binding itself is **untested by fixture**.
23. **The escape test reads a macro's TOP-LEVEL arguments.** Two residuals
    follow, both recorded rather than repaired in rung 3, and both measured to
    have **zero exposure** on the bloomery clone
    (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` §5.3):
    a value-format macro *nested* inside a logging macro's argument
    (`eprintln!("{}", keep(format!("{e}")))`) reads HANDLED and can therefore
    still reach SWALLOWED — the same class the R2 amendment of 2026-09-05 was
    written for, one nesting level in; and a whole-word literal `e` inside a
    NON-logging macro's string over-escapes, costing an AMBIGUOUS where the
    arm handled (the safe direction). **Untested by fixture**; the exposure
    check is a measurement on one workspace, not a promise about any other.
24. **`tracing`-style field syntax escapes unconditionally.** `err = ?e`,
    `error = %e` mention the bound name as a token, so every such arm reads
    `arm_ambiguous`: **no log-and-continue arm can read SWALLOWED on a
    workspace that logs that way**, and a low SWALLOWED count there is not
    evidence the classifier is right
    (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` §5.4).
    **Untested by fixture.**
25. **Records with no frame to attach to, and a chain machine that is
    per-thread.** Sinks and arms inside an `async {}` block ARE probed (only a
    `?` there is declared `partial`, reason `async-block`), and the future may
    poll on a thread with no open frame: such a record is **counted in the
    meta key `err_flow_outside_frames` and never written as an event**. A
    `const`/`static` initialiser gets no probe at all — `err_site` is not
    `const` — *falsified by*
    `rust/sensorium-transform/tests/edges.rs::a_const_context_gets_no_err_probe_and_a_closure_inside_one_does`.
    And the chain machine runs **per thread**: an `Err` born in an instrumented
    frame on ANOTHER thread is, to the thread that absorbs it, "born outside
    this thread's instrumented frames" — the wording says *this thread*
    because a cross-thread chain is unknowable to it by construction
    (amended 2026-09-04). *Falsified by* `corpus/rust/join_handle`.
26. **A probed operand whose type is a REFERENCE to a `Result`.**
    `let _ = f()` where `f` returns `&Result<T, E>` records nothing: the
    three-level autoref ladder resolves to its own fallback arm. That `Err`
    reads AMBIGUOUS **with no record and no `partial` row** — the one shape in
    this list whose absence nothing in the trace declares. Measured at the
    Task-1 review of 2026-09-04; **untested by fixture**.
