# Changelog

## 0.8.3 — 2026-09-06

Rung 4, slice 1: **the focus tier** — LINE and locals for Rust, under a
compile-time `--focus`. Python **0.8.3**; the crates move together to
**`sensorium-rt 0.4.0`**, **`sensorium-transform 0.4.0`** and
**`cargo-sensorium 0.4.0`**. `TRACE_FORMAT` stays **4**: LINE rows and a
`focus` meta key already exist there and `focus_matched` is optional meta.

- **The driver takes `--focus <qualname>`, repeatable, and resolves it before
  it builds anything.** A container value selects its children on the `::`
  boundary, and resolution reads the workspace's sources through the
  TRANSFORM's own eligibility rule, so the driver can never accept a value
  the transform would then ignore. A value matching nothing is refused at exit
  **2** with up to three `Closest:` suggestions and nothing built; a value
  whose only matches are functions the transform skips is refused the same
  way, naming every one of them with its reason. A resolved focus prints one
  `focus: <qualname>` line per selection on stderr before cargo runs. The
  focus reaches cargo's fingerprint through the wrapper shim's PATH, so every
  distinct focus has its own `-C metadata`, its own mirror and its own unit
  manifests — which accumulate in the target directory, at roughly one ~40 MB
  shim copy and one artifact set per focus.
- **The transform splices one LINE probe after every statement of a focused
  function, at every block depth.** A parameters LINE comes first, even for a
  function taking none; an arm or loop pattern that BINDS mints a synthetic
  entry LINE once per entry or iteration, and one that binds nothing mints
  none; a bare-expression arm body is wrapped `{ probe; expr }`, so the arm
  entry exists there too while the expression stays a tail and takes no row.
  A statement that returns, breaks, continues, propagates with `?` or panics
  leaves no LINE — its exit is already the RETURN or RAISE row — and neither
  does a tail expression.
- **The runtime gains a wire kind, LINE (6), and a lazy entry point.**
  `line(unit, site, || [("x", probe_cap!(&x))])` evaluates its deltas only
  when the runtime is recording, so under `--tier off` no `Debug` impl runs
  for a delta; `probe_cap!` formats inside the runtime scope, which is what
  keeps the reentrancy promise true for LINE. A payload is capped at
  `LINE_PAYLOAD_MAX` (2048 bytes, nine fully capped eight-character-named
  deltas); beyond it the remaining deltas are dropped and `flags.bit0` says
  so, never a silently short record.
- **The converter writes LINE rows in the Python payload shape** —
  `deltas: {name: capture}` with `unread: ["locals"]` when a delta was
  dropped — decoding with a parser that mirrors the writer byte for byte: a
  malformed payload is a conversion refusal naming the record, never a
  guessed row, and so is a LINE whose thread has no open frame. `meta.focus`
  is **the invocation's own list**, handed over by the driver and never read
  back out of an accumulated manifest, and `meta.focus_matched` is the union
  over the manifests built under THIS invocation's focus (compared as a SET,
  so `--focus a --focus b` and `--focus b --focus a` are one build).
  `capabilities.line` and `capabilities.locals` are true exactly when some
  registered unit of the run carries a LINE site; `refocus` stays `false`.
- **`watch` and `flow` answer on a focused Rust trace.** The qualname prefix
  rule learns the `::` boundary beside Python's `.` — `--at Counter` selects
  `Counter::new` and never `Counters::new` — in one helper with no `lang`
  branch anywhere near it. And a `dbg` capture now has a defined meaning:
  it is Debug **text**, compared against a literal's Debug rendering
  (`5`, `2.5`, `true`, `None`, a string WITH its quotes), never matching when
  truncated, and `len()` over one is `NOTHING WAS CHECKED` at exit 3 rather
  than a comparison to nothing. `resolve` and `matches` are **inverses on the
  literal domain** — exponent floats, `inf`, `-inf`, `NaN` and `None`
  included — so `flow --value` cannot report a sighting that `watch --expr`
  then denies at the same site. `flow --object` on a Rust trace still refuses.
- **Seven new Rust corpus cases**, six recorded under a focus and one without,
  each pinning a LINE count DERIVED from the rules before it was measured and
  at least one absence: `focus_let_chain`, `focus_loop_counter`,
  `focus_match_binding`, `focus_arm_bare`, `focus_moved_value`,
  `focus_non_debug` and `focus_unfocused_refuses`. The driver's exit-2 refusal
  is not a case — a case records once, with one argv — so it is pinned by
  `tests/test_focus_refusal.py` and by the resolver's own unit tests.
- **E9, measured once, on a real workspace: six PASS and one REPORTED — all
  seven rows as pre-registered.** H1 the unfocused control (`line: false`,
  `locals: false`, **0** LINE rows, the pinned refusal at exit 3); H2 both
  focus values resolving to exactly one qualname with the focused runs' test
  counts and exit status equal to the unfocused ones; **H3 N = 26 with no
  line differing** — the LINE rows of one activation against a hand count
  locked before the transform could produce a competing number, `missing []`,
  `unexpected []`, `count_diffs []`; H4 all three `watch` triples as predicted
  on both readings; H5 both `flow --value` sightings found and no unpredicted
  one; **H6 reported without a gate and without a usable cost signal** —
  libtest read 0.00 s on all four binaries and every invocation wall is
  dominated by compilation, so neither reading isolates run-time overhead;
  H7 every corpus case equal, the Python suite green, `cargo test --workspace`
  green. The record is
  `docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md`; read §4 and
  §5 before quoting any of it, and §5.6 for what it does and does not license.
- **The record's lens was amended once, before any measurement, and carries
  both locks.** Both `flow --value` commands ran with `--limit 1000`, because
  every H5 number is read off the printed rows and the tool's default page is
  50 — a reader fix, not an endpoint change, committed alone at `ffaed19`
  after the original lock `a4264b5`. Its guard did not have to fire: neither
  page truncated, so H5 would have read the same under the unlimited
  spelling.
- **Versions: five pins move.** `sensorium-rt` 0.3.0 → **0.4.0** (the new wire
  kind), `sensorium-transform` 0.3.1 → **0.4.0** (focus, LINE splices,
  `SiteKind::Line`), `cargo-sensorium` 0.3.1 → **0.4.0** (`--focus`,
  resolution, LINE conversion, meta, capabilities), Python `sensorium`
  0.8.2 → **0.8.3**, and `TRACE_FORMAT` stays **4**. Traces recorded by an
  older runtime still read; the refusal sentence they carry moves with the
  recorder string, which is why `corpus/rust/stale_cache`'s pin changed in
  its version token and nothing else.
- **Two documents were split so neither passed 800 lines**, both deliberately
  and both with wording and order unchanged: `rust/HONESTY.md` §11 is now
  `rust/HONESTY-ERR-FLOW.md`, and the README's `exceptions`, `watch` and
  `flow` sections are now `docs/query.md`. Each keeps a pointer where it was.

## 0.8.2 — 2026-09-05

- **SWALLOWED has one definition, and it lives in `rust/HONESTY.md` §11.**
  Three records had restated the reading and the third let it decide 48 % of a
  headline, so the rule is written once and everything that cites it — design
  R15, the tool's own sentence, the next pre-registration's row — cites §11 by
  name and restates nothing. The definition adds what was only implied:
  **reading the error does not carry it out** (a match guard, a `&self`
  predicate that only steers control, a log line), and a guarded arm's
  disposition is its body's. `exceptions`' own detail sentence now says it —
  *"a bound error that is stored, returned or moved out of the arm is not a
  swallow; an arm that only reads it (a guard, a predicate), formats or logs
  it and continues is one"* — and a test asserts that sentence is a substring
  of §11.
- **`exceptions` on a Rust trace prints one block per SHAPE, not one per
  chain.** Two chains are one shape when they share a disposition, the site
  the verdict is about (the sink for `swallowed`, the arm for an escaped
  `ambiguous`, the origin site — with its masked route — for every verdict
  that names no site) and the verdict text once event and frame ids are
  masked. The shape prints the FIRST chain's block byte-for-byte as before and
  appends to the verdict line, two spaces after it, a bracket of the members'
  ORIGIN ids: `[×2: e3, e7]`; eight ids show, then `… +K`. Where members
  differ in something the key does not look at, one line says so —
  `origins:`, `messages:`, `details vary`, `routes:`, each `(first shown)` or
  `(this one has none)` — so a merge is never silent. The `dispositions:`
  tally still counts CHAINS; `--limit` counts SHAPES and its continuation
  raises the limit
  (`... K more; continue with: sensorium exceptions <run> --limit N`, carrying
  `--after` when the reader gave one) because an event cursor over grouped
  output would re-show a partial group. A group of one is byte-identical to
  0.8.1.
- **The shape key carries the file.** The first measurement keyed the site on
  `qualname L<line>` alone, and two test files each holding a `sandbox` at L42
  merged across processes; the key is now the code object's `(file, line)`
  plus the qualname. The printed site text is unchanged, except that when ONE
  answer prints two shapes whose site text collides, each colliding verdict
  names its file — `(sandbox L42 in task_exec_run_test.rs)` — so answers that
  never collide look exactly as they did.
- **`sensorium exceptions <invocation-id>` answers for a whole
  `cargo sensorium test` invocation**, on the id `runs` already prints above
  the group. It opens every member trace, classifies each with the Rust rules
  and merges shapes across processes on the same key, the bracket naming the
  spread (`[×N over M processes: first e<id> in <run-id>, +K]`; a shape seen
  once carries `[in <run-id>]`). The header is
  `invocation <id>: cargo <args> -- 144 processes, 114 with Err chains, 30
  with none`; every INCOMPLETE member is named before any answer about chains;
  `partial` rows are the union with their process named and the tally is the
  members' sum. `--after` is refused here (exit **2**: an event id belongs to
  one process), and a member whose recorder declares `err_flow: false` refuses
  the whole answer, naming it.
- **Four pins moved BY RULE before the pre-registration was locked**, and the
  record lists them: `corpus/rust/err_stored/questions.yaml` and
  `corpus/rust/err_rendered_into_value/questions.yaml` (the tool's new
  sentence), `docs/trace-format/vectors/v18-exceptions-rust-ambiguous-merge.json`
  (the same sentence) and
  `docs/trace-format/vectors/v17-exceptions-rust-swallowed.json` (the new
  continuation note) — with `err_stored` moving twice, because its retry arm's
  two chains are one shape, so the bracket and `messages: 2 distinct (first
  shown)` are pinned where a second block used to be.
  `tests/test_exceptions_rust_gate.py`'s continuation-note pin moved with v17.
- **Measured twice, and neither record is rewritten.**
  The first
  (`docs/superpowers/acceptance/2026-09-05-sensorium-rung4-entry-grain.md`)
  read H1 PASS, H2 PASS, H3 PASS, **H4 STOP**, H5 PASS, H6 PASS: **4 site
  differences per arm**, the invocation view resolving to **89** and **96**
  distinct sites against the published E6⁗ record's 91 and 98, with 11 chains
  of 782 and 10 of 812 booked at a sibling test file while every count was
  conserved. That is the missing file in the key, and it was repaired under a
  NEW pre-registration rather than by re-rolling the record. The second
  (`…-rung4-entry-grain-repair.md`) read **0 site differences per arm** — 91
  and 98 sites against the record's 91 and 98, over **103** and **105** shapes
  — with the A run's answer and all 288 per-process answers byte-identical to
  the first measurement's, so only the two invocation views moved. **H4′'s
  verdict depends on the reading and the ruling is Brice's**: §1′ asked for
  "exactly 91 / 98 shapes, one per (file, line) site", a clause that was
  unsatisfiable as written — it was locked after the first measurement had
  already published 100 and 103 shapes, and adding a key component can only
  split. Under the gate reading (the site multiset, the instrument's committed
  rule) H4′ is a PASS; under the strict reading it is a STOP at 103 / 105.
  No number in either record turns on it. Read §4 and §5.2 of the repair
  record before quoting any of this.
- **Python traces are untouched** — byte-identical output, one block per raise,
  paging by event id. Grouping there waits on a definition of the site each
  Python disposition's verdict is about, and is a rung-4 inbox item.
- **Python 0.8.2. The crates do not move**: no Rust changed in this slice, so
  `sensorium-transform` and `cargo-sensorium` stay **0.3.1** and `sensorium-rt`
  stays **0.3.0**, and no trace needs re-recording.

## 0.8.1 — 2026-09-05

- **The `&e` exemption is now a rule about the borrowing call's product.** A
  shared borrow of an `Err` binding is a provable non-escape only where the
  borrowing call's product is dropped — the whole expression of a statement
  ending in `;`, a `let _ =` with a plain wildcard, or a logging macro's
  argument. Everywhere else the borrow ESCAPES, so
  `Err(e) => { let (status, value) = map_error(&e, ..);
  V1Result::json(status, value) }` reads `arm_ambiguous` where it read
  `arm_handled` and could print SWALLOWED while the failure reached the caller
  as an HTTP error. On the bloomery clone (`e209ed9`) the census moves arms
  handled (`arm_handled`) **65 → 54** and arms escaped (`arm_ambiguous`)
  **121 → 132** over the same **225** arm sites; arms propagate
  (`arm_propagate`) stays **39**. No splice fragment changed, so no line
  moved.
- **An `err` close hops the held chain whose text the RETURN carries.** A
  frame closing `err` while it held two chains minted the exit hop on the
  INNERMOST one whatever the text said, so a keep-first-error shape recorded
  the hop on the wrong chain and labelled it `translated`. The converter now
  runs the text-preferring search the RAISE and HANDLED rows already ran, with
  the innermost as the fallback. **Hop data only**: no disposition moved, and
  the wire is unchanged.
- **Two Rust corpus cases**, taking the Rust corpus to thirty-one:
  `err_borrowed_into_value` (an arm hands `&e` to a helper and keeps the
  helper's product — `dispositions: ambiguous 1`, never a swallow) and
  `keep_first_error` (a frame holding two different errors returns the FIRST:
  the exit hop follows the returned text with no `translated`, that first
  error is swallowed by `main`'s log-and-continue arm, and the second reads
  ambiguous).
- **Measured, and — for the first time in this line of records — the control
  discriminated**
  (`docs/superpowers/acceptance/2026-09-05-sensorium-rung3-e6q.md`).
  **E6⁗-A PASS**: 0 false accusations of 14 SWALLOWED lines on the clone's
  `-p bloomery-daemon --lib` suite, under both readings. **E6⁗-WS PASS**: 0
  false of 782 lines over all 144 processes of
  `cargo sensorium test --workspace`, resolving to 91 sink sites, under both
  readings. **E6⁗-WS0 DISCRIMINATING**: the same command under the pre-repair
  driver printed 812 lines — the same 782 plus 30 more, every one of the 30
  false, at 7 of the 11 arms the repair moved, where the repaired driver
  printed none. **E-flip PASS**: 11 changed manifest rows, every transition
  `arm_handled → arm_ambiguous`, and `11 == 65 − 54`. **E6-again′ PASS**: 0
  unequal sets over 20 corpus `exceptions` questions. **E7⁗ PASS**:
  `mechanics.sh` exit 0, 47 ok and 0 FAIL. **E0‴ PASS**: `info` 1.507 s and
  `diff` 1.500 s on the widest trace this project has recorded. Four of the
  eleven flipped arms were never executed by any arm of the run, and nothing
  in the record is evidence about them.
- **`sensorium-transform` and `cargo-sensorium` → 0.3.1** (the rule and the
  hop). **`sensorium-rt` stays 0.3.0**: no wire and no runtime change, and a
  trace recorded before this release needs no re-recording.

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
