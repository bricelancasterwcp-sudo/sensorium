# The Rust recorder's honesty ledger — §8: What this recorder cannot see

The numbered list of [`rust/HONESTY.md`](HONESTY.md) §8, **moved here
2026-09-05 (rung 3) so that file stays under 800 lines**. The section's own
framing paragraphs stay there; **the numbering is unchanged**, so item *n*
here is `rust/HONESTY.md` §8 item *n* — the spelling every code comment and
the ledger's index already use. Items 1–14 are rung 2's, verbatim except
three: item 2, which rung 3 narrowed to the recordings it is still true of;
item 3, which rung 4's focus tier narrowed 2026-09-06 to what a focus still
does not reach; and item 12, which rung 4's refocus slice narrowed 2026-09-07
to what a re-run does not compare and what its licence cannot check.
Items 15–26 are rung 3's own, from the design's R16 (`?`,
sinks and `Err` arms:
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
3. **Locals, and per-line state — what a `--focus` still does not reach.**
   **Narrowed 2026-09-06** (rung 4 slice 1, design §3.3), not struck: the
   focus tier gives one LINE per completed statement of a focused function,
   with the bindings that statement wrote (`rust/HONESTY.md` §12), and what is
   left is exactly this list.
   * **Every function no `--focus` named.** Nothing is captured between its
     entry and its exit, so a value that changed in place mid-frame — mutation
     through a long-lived `&mut` included — is invisible there, which is what
     this item said of every function before this rung.
   * **Closure bodies, `async fn` bodies and `async` blocks**, focused or not:
     the statement walk stops at them (call-level instrumentation only, and an
     `async fn` is skipped whole for item 5's reason).
   * **Macro bodies.** A macro invocation is ONE statement with empty
     `deltas`; the expansion is not inspected, so a binding written inside it
     mints nothing.
   * **Place writes and `&mut` mutation.** `*p = e`, `a.b = e`, `v[i] = e` and
     a mutating method call are not deltas (design §3.2): those statements
     mint a row with empty `deltas`, which says the line ran and nothing about
     what it changed.
   * **A `loop` a `break` leaves, nested inside a COMPOSITE statement**
     (`unsafe { loop { break; } }`, a `match` whose every arm is such a loop):
     the divergence walk calls it diverging and it loses its row. It costs a
     row and never a build.
   * **Statements under `#[cfg]` / `#[cfg_attr]`**, which are declined: the
     probe is spliced after the statement and would survive a `cfg` that
     stripped it, so the row would name a binding that was never built.
   * **A pattern name whose first character is uppercase** is read as a path
     pattern (`None`, a unit variant, a const) and mints no delta — `syn`
     cannot tell it from a binding, and resolution is rustc's job. The cost is
     a missed delta for a binding written against Rust's own naming
     convention.
   * ~~**A `let` whose head type is wholly unresolved** (`let x =
     Default::default();`, resolved by a later use) is design §9's named
     compile risk: the probe constrains nothing and the unit may fail to
     compile. E9 H2 measured **0** focused build failures over two units,
     which does not reach this shape — named, not measured.~~ **Struck and
     corrected 2026-09-06** (the whole-branch review's item 2, after E9): the
     mechanism named here is wrong, and wrong in the direction that matters. A
     probe on such a `let` does not *constrain nothing* — it constrains the
     variable to `Debug`, at the probe. The replacement is the next bullet;
     E9 H2's **0** build failures over two units still stands and still does
     not reach the shape.
   * **A `let` whose head type is an INFERENCE VARIABLE that a later statement
     resolves to a non-`Debug` type.** `let mut v = Vec::new();` followed by
     `v.push(Opaque)`; `let mut x = None;` followed by `x = Some(Opaque)`;
     `let x = Default::default();`; a `.collect()` whose collection type
     arrives later. **Measured mechanism**: the autoref ladder is resolved
     where the probe is spliced, and at that point the head type is an open
     inference variable, so the ladder COMMITS the variable to its `Debug`
     rung. The later resolution then has to satisfy `Debug` and does not:
     `error[E0277]: `Opaque` doesn't implement `Debug``, and the unit does not
     build. This is not "`Vec::new()` is unsupported" — `let mut v =
     Vec::new();` resolving to `Vec<u8>` compiles (compiled by hand at the fix wave; no case in the tree pins it), and so does a
     `Vec<T>` for a generic `T` with no `Debug` bound, because there the bound
     is unprovable rather than open and the ladder takes its fallback rung and
     records `unread` (compiled by hand at the fix wave; not pinned by a case). What breaks it is an OPEN variable that
     closes on a type without `Debug`.
     *Declared by* the whole unit falling back to the real tree and saying so
     on stderr — `sensorium: unit <crate> (<metadata>) fell back to the real
     tree: <rustc's first error>` (`fallback::announce`) — so the trace has no
     LINE row for anything in that unit and the build named the reason.
     *Falsified by* `rust/sensorium-transform/tests/focus_compile_fail/focus_infer_debug.rs`
     (the failure, in its error class) against
     `tests/golden_focus/focus_moved_value.in.rs` (the same `Vec::new()` shape
     resolving to a type that does implement `Debug`, compiled clean).
     The repair is a ruling, not an oversight: an opt-out spelling, or
     declining the delta on an initializer with no type witness, costs
     something either way, and both are `docs/CARRIED-DEBT.md`.
   * ~~**A brace-delimited MACRO in TAIL position** — `fn f() -> i32 { m! { 1 } }`,
     which is the shape of a `quote!`/`html!`-terminated function and so of
     proc-macro and markup crates. **Measured mechanism**: `syn` reads that
     tail as a `Stmt::Macro` whose `semi_token` is `None`, and `lines.rs`'s
     `statement_end` hands a brace-delimited macro the byte after its closing
     brace without asking whether it is the block's tail — so a LINE is minted
     after a macro that IS the return value. The tail takes the RETURN wrap as
     well, and the two together give `…, m! { 1 })::sensorium_rt::line(…)`,
     which rustc rejects as `expected one of `.`, `;`, `?`, `}`, or an
     operator, found `::``. Being a PARSE error it takes the file, so the unit
     fails to build under a focus.
     *Declared by* the same loud whole-unit fallback as the bullet above.
     *Falsified by* `rust/sensorium-transform/tests/focus_compile_fail/focus_macro_tail.rs`.
     The guard is one line — `lines.rs`'s `Stmt::Macro` arm returning `None`
     when `is_tail` — and it is NOT taken here: it is a `src` change after the
     measurement (R-F14), so it is `docs/CARRIED-DEBT.md` for Brice or slice
     2.~~ — **Struck as FIXED in `sensorium-transform` 0.4.1**, ruling G1 of
     slice 2 (design §3.3). The mechanism above was measured and is accurate
     for 0.4.0; the guard is the one line it named, and it is the same guard
     `Stmt::Expr(_, None)` already applied one arm above — a tail is not a
     statement whichever `syn` node spells it. The compile-fail case is deleted
     with the repair, and the shape is now a compile-PASS golden,
     `tests/golden_focus/focus_macro_tail.{in,out}.rs`: the value fn pins
     `ret(…, pick! { 1 })` with no `line(` after it, and
     `tests/oracle.rs::every_focus_golden_output_compiles_with_zero_diagnostics`
     hands those bytes to the real rustc under `-D warnings` and requires an
     empty stderr. The golden carries a UNIT fn (`shout! { a }`) as well,
     because that half of the shape was never loud: with no RETURN wrap to
     collide with, the extra LINE compiled and simply recorded a completed
     statement for what is the function's value — a wrong row rather than a
     lost build, and the only thing that would have said so is the row count
     the golden now pins. Two more functions there fix the guard's extent
     rather than its subject: `declared` is the NEGATIVE — a brace macro that
     is not a tail keeps its probe, so the arm cannot be widened to every brace
     macro without the suite saying so — and `looped` is a brace-macro tail of
     a NESTED block, a loop body's, which nothing claims as an operand (only a
     fn body's tail is one) and which therefore never failed to build either.
     It takes no probe for the plainer half of the reason, that a tail is not a
     statement, and its count is what says so: three LINE sites before the
     guard, two after.
   * **A focused function that was BUILT but never RAN** leaves
     `capabilities.line: true` with zero LINE rows (`--focus tests::x` under
     `cargo run`). That is honest under design §2.4 — the capability is a
     statement about what the recorder produces, not a promise that it did —
     and the two facts are scoped differently on purpose: `focus_matched` is
     about the BUILD (the manifests built under this invocation's focus),
     `capabilities.line` / `locals` about the RUN (its registered units).
   *Declared by* `capabilities.line` and `capabilities.locals`, which are
   `true` for `lang = rust` **only under a `--focus`**; by `meta.focus` (the
   invocation's own list) and `meta.focus_matched` (what this build matched),
   both printed by `info`; by the `"unread": ["locals"]` marker every CALL
   payload carries, which `tree` renders as `name() <unread: locals>` and
   `frame` as `args: <unread: locals>` — never `(none)`, which would read as
   "called with no arguments" — and which a LINE row carries too when a delta
   was dropped; by the driver's exit-2 refusals, which name a `--focus` value
   that matches nothing (`REFUSED: --focus <v> matches no function in the
   workspace; nothing was built.` with up to three `Closest:` suggestions) or
   that matches only functions the transform skips, each named with its
   reason, and build nothing; and, on an unfocused trace, by the unchanged
   refusal `watch` and `flow` print:
   `REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 declares it
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
12. **What a deeper re-run does not compare, and what its licence cannot
    check.** **Narrowed 2026-09-07** (rung 4 slice 2, design 2026-09-07), not
    struck: `refocus` re-invokes the recorder on a Rust trace and issues the
    comparator's verdict (`rust/HONESTY.md` §13), and what is left is exactly
    this list.
    * **The program's OUTPUT and its CHILDREN are never checked on a Rust
      pair.** `capabilities.output` and `capabilities.children` are `false`,
      so the two cross-checks the Python licence runs cannot run at all. They
      are printed and stamped `output: unverifiable (not recorded)` and
      `children: unverifiable (not witnessed)` and are **never counted as
      verified** — the alternative was comparing two empty sets and reporting
      agreement, which is the bug class the wording exists to refuse.
      *Declared by* those two lines and the `refocus_licence*` stamps.
      *Measured* at n = 61 by **E4 H4**
      (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md` §3/§4):
      both UNVERIFIABLE 61 of 61, and **0** licence lines claimed an
      unverifiable check as verified.
    * **A multi-process invocation is refused, not compared.** `cargo
      sensorium test --workspace` produces one trace per runner process (test
      binaries and doctests alike), and no single one of them is the answer to
      a question about the invocation. `refocus` refuses at exit **2** naming
      the count and the single-target selector, before anything is launched.
      *Declared by* `meta.invocation_processes` and that sentence; *pinned by*
      `corpus/rust/refocus_refused_many`. A refocus of such an invocation is
      untested because it does not exist — it is CARRIED-DEBT, not a gap in a
      shipped answer.
    * **The re-run's rebuild is its own cost, and the verdict says so.** A
      `--focus` keys a fresh wrapper shim and rebuilds the matched units, so a
      refocus is not a cheap replay: E4 measured a flat ~7 s per pair on its
      subject, of which about half is cargo's own reported build, and 61
      focused re-runs plus pass 1's own unfocused base key left **62** shim
      entries totalling **2 506 729 440** bytes — one base key and exactly 61
      focused keys, none reused (record §3, §5.4). Those bytes were **copies**,
      one per key, which is what `cargo-sensorium` 0.5.0 installed; from 0.5.1
      the shim is a hard link to the driver wherever the target directory
      shares its filesystem, so the per-key PATH cargo needs no longer costs a
      per-key binary (design 2026-09-07 ruling R3, at `36d2fe9`). The REBUILD
      is unchanged and is still the cost this bullet is about. *Declared by*
      the third blind-spot line the verdict prints
      (`vocab.RUST.refocus_blind_spots`).
    * **A per-thread fingerprint can partition differently under a scheduler
      split, and only the comparator's multiset absorbs it.** Where a test
      drives a worker pool over one queue, which worker serves which request
      is the OS scheduler's choice, so the same execution can distribute the
      same work across workers differently. `compare_tasks` matches tasks as
      an order-independent multiset of `(name, hash)`, so only a different
      PARTITION — not a different ORDER — could diverge. **Measured, and it
      fired**: on 1 of E4's 61 pairs the per-`task_id` assignment moved (the
      workers carried (216, 205, 151, 233, 151) events on one side and (216,
      205, 233, 151, 151) on the other), the multiset was identical, the total
      was 956 on both sides, and the verdict was MATCH (record §5.3). The
      **discriminator** E4 pre-registered for telling this hazard from a
      recorder finding is two conditions — the worker tasks' total event count
      preserved, AND the MAIN stream MATCHing — and its second condition has
      **no subject on `cargo test` material**: every one of E4's 122 traces
      carries a **0-event** MAIN stream, because libtest runs each test on a
      spawned thread the converter records as a *task*, so nothing runs
      outside a task at all. The discriminator was never asked (nothing
      diverged), so no verdict rests on it; it is recorded as a limit of the
      amendment, not as a repair.
    * ~~**The licence is structurally WITHHELD on every `cargo test` pair.**
      The untraced-thread clause fires on libtest's own per-test thread, so
      `licences granted` was **0** on all 61 of E4's pairs while every count
      the endpoint gates on was as pre-registered (thread counts 57×1, 1×2
      and 3×5; record §5.2). **This is a finding about the licence's thread
      clause, not about the recorder**, and the candidate fix — treat
      libtest's per-test thread as the recorder's own, as the licence already
      treats the recorder's own environment variables — is named there and
      deliberately **not applied**: it is a ruling's to make
      (`docs/CARRIED-DEBT.md`). A reader of a `cargo test` refocus should read
      the four printed counts, not the word.~~ — **taken 2026-09-07** at
      `11b7e8a` (with `d9115a5`), design 2026-09-07 ruling R1. The MEASURED
      reason the word never moved was libtest's per-test thread and nothing
      else, so that thread is now the **harness thread**: a non-main thread
      whose ROOT frame's site the manifest marks `#[test]`, subtracted from
      the licence's untraced-thread counts and NAMED on every line one of
      those counts appears on (`rust/HONESTY.md` §13). What remains a blind
      spot is what it always was and is one bullet down: the licence's thread
      clause reports what was not COMPARED, and a program thread of the test's
      own still withholds — which is the answer, not a gap.
    * ~~**A re-run whose test spawns a workspace CHILD is refused by count,
      and the sentence names the selector rather than the cause.** Every trace
      of the invocation carries `refocus_of`, a child process the test spawns
      included, while `meta.invocation_processes` counts only what cargo hands
      the runner — so the pre-rerun count is 1, the pair lookup finds 2, and
      the refusal asks for a single-target selector the caller already used.
      Two traces is not a pair, so the REFUSED verdict is right; what is wrong
      is the diagnosis. Derived from the code and the trace format, not
      measured — E4's subject spawns no child from a test. *Carried, with two
      candidate fixes and a ruling owed*, in `docs/CARRIED-DEBT.md`.~~ —
      **taken 2026-09-07** at `d4cccd9`, design 2026-09-07 ruling R2, which
      chose the first candidate: a linked trace whose `ppid` is another linked
      trace's `pid` is a child run, excluded from the pair and named on the
      pair line, so such a re-run is now ANSWERED about its parent rather than
      refused. `corpus/rust/refocus_child_run` records the shape through the
      real driver. What is still refused by count is more than one linked
      trace that is nobody's child, and that sentence now names the excluded
      children too.
    * **The licence still WITHHOLDS on a re-run launched from another shell.**
      The env clause compares every key that is neither the recorder's own nor
      shell bookkeeping, and a second shell differs in variables that bear on
      nothing the build or the run reads. A target directory that MOVED is now
      read as a relocation (`rust/HONESTY.md` §13), so cargo's four
      root-bearing variables no longer fire on their own — but a
      `SSL_CERT_DIR` present at one launch and absent at the next does.
      **Ruled and deliberately not built**: a named, versioned positive set of
      build-and-run-bearing variables withholds, and every other differing key
      is counted and NAMED without withholding (E4′ §1.5, *carried, not
      built*; the set is enumerated in `docs/CARRIED-DEBT.md`). Fewer source
      changes before a measurement is the rule, and E4′ does not need it: its
      runner refuses to launch unless its own process environment matches
      every original's recorded one under the same exclusions
      (`pins.env_parity`, instrument commit `10e2712`). *Declared by* the env
      line, which names every key it did not explain.
    * **`--window` is not available on a Rust trace at all** (refused at exit
      2): it needs a per-activation runtime check the Rust runtime does not
      have. *Declared by* that refusal sentence.
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
    row of `tests/test_exceptions_rust_ambiguous.py`
    (`test_a_sink_whose_frame_then_failed_is_ambiguous_not_swallowed`; the §2a
    rows split across two files at the 800-line ceiling).
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
22. **`Err(ref e) => note(e)` reads ESCAPED.** Exactly two shapes count as a
    provable shared borrow, and **since 2026-09-05 the first of them is
    narrower than it was** (the borrow repair, item 23 (c) below): a literal
    `&e` argument of a call at a DROPPED call site — the whole expression of a
    statement ending in `;`, a `let _ =` with a plain wildcard, or a logging
    macro's argument — and a `{}`/`{:?}` format argument of the logging
    family. A literal `&e` argument anywhere else ESCAPES too, which it did
    not before that date: `Err(e) => map_error(&e),` is a literal `&e`
    argument and reads `arm_ambiguous`. A binding reached any other way was
    already treated as escaping. **ESCAPED is an upper bound, deliberately**:
    it costs AMBIGUOUS verdicts on arms that in fact handled, and never a
    false SWALLOWED. *Falsified by* the golden `err_arm_escaped`, whose
    controls are the two provable shapes (its `&e` control is `note(&e);`, a
    dropped site); the `ref` binding itself is **untested by fixture**.
23. **What the escape test proves, and what it leaves.** Four residuals
    follow. They are **not the same kind of thing**, so they are stated apart
    rather than together. (a) and (b) are the macro rule: the test reads a
    macro's TOP-LEVEL arguments. (c) was the `&e` rule and is **repaired and
    measured**; (d) is what that repair leaves.
    (a) A value-format macro *nested* inside a logging macro's argument
    (`eprintln!("{}", keep(format!("{e}")))`) reads HANDLED and can therefore
    still reach SWALLOWED: a **false-accusation generator**, the same class
    the R2 amendment of 2026-09-05 was written for, one nesting level in. Its
    exposure on the bloomery clone was **measured zero**
    (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6ppp.md` §5.3) —
    a fact about that workspace, not a promise about any other — and it was
    recorded rather than repaired.
    (b) A whole-word literal `e` inside a NON-logging macro's string
    over-escapes, so an arm that handled reads AMBIGUOUS. That is the **safe
    direction**: it can never produce an accusation, only withhold a verdict.
    **Its exposure is measured nowhere** — no run counted it, and nothing here
    should be read as saying it is rare.
    (c) A `&e` handed to a FUNCTION was exempt **regardless of what the
    call's product does** — the exemption (design R2,
    `escape.rs::visit_expr_reference`) was a fact about the borrow and said
    nothing about the value the call returns, so
    `Err(e) => { let (status, value) = map_error(&e, ..);
    V1Result::json(status, value) }` read `arm_handled` and could reach
    SWALLOWED while the failure reached the caller as an HTTP error: a
    **false-accusation generator**, the R2 amendment's class one function call
    out rather than one macro nesting in. **Repaired 2026-09-05** (the borrow
    repair, design B1): the exemption now holds only where the borrowing
    call's product is provably dropped — an expression statement, a `let _ =`,
    or a logging macro's argument — and that arm reads `arm_ambiguous`.
    **Measured, and the control discriminated**
    (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`):
    **E6⁗-A PASS**, 0 false accusations of 14; **E6⁗-WS PASS**, 0 false of 782
    over 144 processes of `cargo sensorium test --workspace`; **E6⁗-WS0
    DISCRIMINATING** — the same command under the PRE-repair driver printed 30
    more lines, every one false, at 7 of the 11 arms the repair moved, where
    the repaired driver printed none; 4 of the 11 were never executed by any
    arm of that run (§5.5 there). *Falsified by* the `class_of` rows of
    `rust/sensorium-transform/src/arms.rs` (the dropped-site and escaping
    shapes of the borrow-repair design §2) and by
    `corpus/rust/err_borrowed_into_value`. **One more gap in the same
    direction, found after the numbers were read:** `log(&e).await;` and
    `note(&e)?;` are not matched by `walk_dropped_call` (they are
    `Expr::Await`/`Expr::Try` over the call, not the call), so both ESCAPE
    too — the safe direction, unmeasured, added 2026-09-05 to the
    borrow-repair design's §2.
    (d) **A callee that STORES a rendering through a side channel.** A `&e`
    handed to a call whose product is dropped — `self.record(&e);`, or a call
    that writes through a capture or a global — is exempt by (c)'s repaired
    rule, and the callee may keep what it was handed all the same, so the arm
    still reads `arm_handled` and can reach SWALLOWED. A syntactic rule cannot
    see it; closing it needs the inter-procedural analysis this recorder does
    not do (design B2). Today's reading is *pinned* by
    `a_dropped_call_that_stores_what_it_is_handed_is_still_handled_and_says_so`
    (`rust/sensorium-transform/src/arms.rs`), which documents the reading
    rather than falsifying the gap. Added 2026-09-05; design R16 (vii).
    (a), (b) and (d) are **untested by fixture**; (c) is measured, by the
    endpoints named in it.
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
