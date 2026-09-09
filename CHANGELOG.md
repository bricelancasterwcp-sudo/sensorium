# Changelog

## 0.8.7 — 2026-09-08

**The queue, buttoned up.** No new capability: this slice pays the carried
debt four ledgers had accumulated — 116 open bullets at `f14d2f6` — and ships
the ledgers to prove it. Brice funded three of the four buckets: **A**, 54
mechanical rows whose fix was already written (47 taken whole, 3 in part, 4
declined with reasons); **B**, the 800-line ceiling; **D**, 5 rows closable
only by a dated note. **C**, 43 design-level or ruled-not-funded rows, is
untouched and is the next conversation. Python **0.8.7**; **`sensorium-rt
0.4.1`**, its first move since `0.4.0`, because the leaf crate now owns the
one `sha256`; **`sensorium-transform 0.4.4`** and **`cargo-sensorium 0.5.3`**,
which take it from there. `TRACE_FORMAT` stays **4**: nothing here writes a
new key into a trace.

- **One `sha256`, in the crate with zero dependencies** (row #13, ruling R3,
  `a0580d3`). The same ~300-line from-scratch implementation stood in all
  three crates, kept in sync by the same NIST vectors. `sensorium-rt` — the
  only crate the other two can both depend on — owns it as `pub mod sha256`
  and the copies are deleted. **The one observable consequence is a token.**
  `sensorium-rt`'s `RT_VERSION` is a literal by necessity (the bare `rustc`
  line that builds the runtime has no cargo environment, so `env!` will not
  compile) and a unit test holds it to the manifest, so the rt bump changes
  what every Rust trace declares: `recorder: sensorium-rt 0.4.1`. Three corpus
  expectations, one E9 cross-check and the living docs moved with it, each
  re-pinned **by value** — the sentence names the recorder, so loosening it
  would have deleted the check. Nothing the runtime records changed: no wire
  kind, no record shape, no capability. The sha256 vectors the consolidation
  dropped came back at `bde3a66`.
- **Seventeen files split — thirteen before anything edited them, four
  after, which is what R9 asks for** (rulings R2/R9).
  Thirteen the design's seam map named — `tests/programs.py` (`b05046b`),
  `test_tree_frame.py` (`718a013`), `test_boot_cli.py` (`5ef40e5`),
  `test_exceptions.py` (`71d18b8`), `test_diff.py` (`d3823b4`),
  `test_tracer.py` (`4267251`), `test_refocus.py` (`f24745c`),
  `test_acceptance_e6q.py` (#58, `1bd523d`), `rust/tests/acceptance_schema.py`
  (`91242c2`), `rust/cargo-sensorium/tests/convert.rs` (#56, `4b98c3f`),
  `convert/chains/tests.rs` (`9bd2647`), `src/sensorium/record/tracer.py`
  1193 → 672 + two modules (`e87996e`), `src/sensorium/query/refocus_world.py`
  (#55, `f350b9c`) — and four more that this slice's own edits took past 780,
  split at their banners under R9 (`bb6b2c4` and the fix commits). Every one a
  pure move, proved by `--color-moved=zebra` and equal collection counts, with
  seven falsified pointers repointed at `b6e2125`.
- **A repo-wide ceiling gate** (ruling R1, `e531200`, widened in the final
  fix wave). `tests/test_ceiling.py` holds every tracked `*.py`, `*.rs`,
  `*.sh` and `*.md` under 800 lines and exempts the three record directories
  under
  `docs/superpowers/` **by name** — dated history, some byte-locked, amended
  by appended notes and never restructured. Both mutations were measured: the
  limit lowered to 700 names 37 files; a fourth exemption fails the test that
  pins the list. The ruling closes two ledger rows without code — the parent
  spec at 1458 (#59) and the repair acceptance record at 795 (#60) — because
  neither is owed a split. The wave widened the markdown half from three
  named patterns to `*.md` whole, which closes the class rather than the
  three files it happened to be missing: `CHANGELOG.md`, `ORIGIN.md` and
  `corpus/rust/README.md` join the enumeration, and this file's own pre-0.8
  entries move to `CHANGELOG-ARCHIVE.md` first — a pure move, off 798 lines
  and two from a ceiling nothing was checking. `docs/CARRIED-DEBT.md`'s
  near-ceiling list carries the measured number.
- **The E4″ instrument's five gaps, with the measurement closed** (rows #1–#5,
  ruling R5, `962cacd`, findings lines `8c4dde1`, renderer `b0c3720`): H8's
  presence reader matches the listing's last path segment as well as the whole
  name and records `null` with the listing command and its rc; the STOP's
  label is derived from what missed, with both sides printed when they
  disagree; `driver_version` is read from the copied original too; H2's
  fragment counts are published per side and per pair; and `walls_s` carries
  `driver_build`, `dry` and a per-arm cargo summary. No published number is
  re-derived and no `results.json` is re-assembled — every fix changes what
  the NEXT run publishes and is pinned by a unit test on synthetic records.
  **Both schema tokens moved with the shapes their assemblers publish:
  `e4pp/2` and `e9/2`**, raw and assembly together, so a fresh run's two
  tokens agree and only a genuine re-derivation of a closed record differs;
  `e4/1` is untouched.
- **The instruments' own honesty**: `ENV_RECORDER_OWN` anchored on its clause
  rather than the line's end (#8, `04d0243`); the E4″ runner's seven minors
  (#9, `862ffa0`); the E4′ lock test diffing the whole pre-amendment range
  (#12, `32aab32`, measured discriminating on a single moved byte);
  `line_rows_per_run` reading the census that counted it (#17, `3e1dac9`); one
  manifest reader for rung 2 and rung 3, its workaround deleted (#22,
  `05148e8`); the e6q runner's falsified expectation swept (#25),
  `render_grain`'s three literals derived (#32) and the grain box-path scan
  walking the directory (#33) — all three at `a3b29b7`, the last two measured
  discriminating; five runner-side review minors (#26, `ae58c54`); the fifth
  override named (#35, `eba4db1`); and the grain reader's `RAISED_INV` regex
  BUILT from the line the tool prints (`aefb7ca`).
- **Eight printed sentences, each through the corpus gate WITH the driver**
  (ruling R6): the session clause reaching the withheld pair's own record and
  `is_relocation_note` → `is_env_rule_note` (#6/#7, `fc72550`); `focus: -` for
  an absent key against `focus: none` for a recorded empty one (#14,
  `36a6f5f`); the printed `HONESTY.md` citation (#18), the born-outside claim
  qualified (#28), the invocation header's noun — `N swallowed shape(s)`,
  which is what N counts (#30) — and the panics line's unit (#31), at
  `edc2bce` with `6490a14`; a typed lookup failure — `cli.py:91` stamps
  `type(e).__name__`, so the invocation log's `error` value for a prefix
  miss now reads `NoSuchTrace` where it read `TraceLookupError`, the class
  actually raised, and no reader keys on it — a language-free `diff --task`
  help line, the `or "?"` fixture and "modulo location" on the
  all-in-tasks branch (#27/#36/#37/#51, `0d685ad`); and a MATCH that says it
  is not a statement about the schedule (#20, `13475a2` with `245dee4`).
- **The corpus and the driver seam**: one driver resolution under
  `src/sensorium/`, the `run:` line keyed and pinned, and `corpus/rust/abort`
  cleaning its core file (#19/#21/#43/#45, `a9a5ed1`); the spawned-test-fn
  case recording deterministically and pinning its marked ROOT (#10,
  `7d9dc9c`). 63 cases, 141 questions, none skipped.
- **The crate-side rows**: `expr_attrs`' loud fallthrough for a `syn` variant
  it does not enumerate (#16, `bb0bb29`, with the known-surviving mutant
  documented at `30fcb39`); five private intra-doc links, so
  `RUSTDOCFLAGS="-D warnings" cargo doc` passes (#24, `059ac7b`);
  malformed-metadata fixtures (#38, `d836a77`); a `mint()` test that reddens
  and one run-id mix for both minters (#39/#42, `74d5fbb`); the panic path
  pinned by wire number and the orphan panic's serial (#40/#41, `852a0f5`);
  the WARN that counts test binaries apart from doctest processes (#46,
  `9c82fde`); `convert_perf` named for the bound it asserts (#47, `6abcc27`);
  goldens for fns nested in const, static and trait-const initialisers
  (#50/#52, `d17eb20`); the refused crate root on the wrapper-binary path
  (#53, `017a4a1`); self-removing scratch directories (#54, `1530f68`); and
  the tid-mask justification written into the suite (#44 nit 2, `91f737d`).
- **The ledgers themselves** (`b498caa`). Every row struck where it was
  raised, across this file's live volume and three archives, with the rung-3
  inbox — a spec — taking appended dated lines instead of strikes. Five **D**
  rows closed by dated note (#62–#66, ruling R8), including the measured cost
  of #66: re-rendering the two committed grain `results.json` today differs
  from their published §2 in exactly three lines, two of which remove a
  falsehood the records struck by hand in prose. Seven **X** rows struck for
  work that shipped in earlier slices and was never marked (#67–#73). Two
  blind spots declared — `rust/HONESTY-BLIND-SPOTS.md` items **30** (design
  R16 (v), the ledger half of #28) and **31** (a spawn in an expression
  position the container visitors skip, #49's A half). The stale
  `rust/target/release/cargo-sensorium` deleted from the root disk (#15,
  ruling R7). The rung-4-entry grain design's §5 example, which still spelled
  a continuation note ruling R-G7 had replaced, corrected beside itself with a
  dated amendment (#34). Slice 3's section moved to a third archive volume,
  measured before the ceiling was met rather than after.
- **What was declined, and why** (all in `docs/CARRIED-DEBT.md`'s new
  section): the six converter functions of 88–274 lines are **C, not A**
  (ruling R4 — behaviour-risk work with no failing test behind it); and of
  #26, #35 and #44 the parts that stand are named individually. Rows #11,
  #23 and #29 were declined for wanting one task holding two file scopes at
  once, and the final fix wave — one task, both scopes — took all three:
  the re-export idiom's file counts dropped everywhere they were spelled,
  three `chain.terminal` conformance vectors (`v20`–`v22`, for `panicked`,
  `left_thread` and `handled_then_failed`), and the §11 sweep finished.
  The **C** list — the inventory's 43, plus **C117**, which the final fix
  wave's review added rather than ruled on — is restated in one line each so
  it can be read without opening four volumes.

## 0.8.6 — 2026-09-08

Rung 4, slice 4: **the recorder's footprint** — the three places this recorder
still showed up inside its own licence, removed, and the small debts slice 3
named with their fixes, paid. Python **0.8.6**; **`cargo-sensorium 0.5.2`**,
**`sensorium-transform 0.4.3`** for three pure splits (the goldens pin the
output byte for byte), **`sensorium-rt 0.4.0`** unchanged (neither the wire nor
the runtime moved). The driver's number carries no behaviour change, and that
is the point: E4″ identifies the driver that recorded a run by
`driver_version`, the token a trace carries, so a rebuilt tree needs a number
of its own. `TRACE_FORMAT` stays **4**: nothing here writes a new key into a
trace.

- **The recorder's own compiler flags are not a change the world made**
  (ruling R1). E4′ withheld the licence on all 61 pairs for one key:
  `RUSTDOCFLAGS` carries the driver's own `--extern sensorium_rt=…` and
  `-L dependency=…`, two tokens naming one directory under
  `<target>/sensorium/rt/<16 hex>/<unwind|abort>/`, whose hash moves with
  every driver build. `strip_recorder_fragment` removes
  every occurrence from BOTH sides before the compare; the remainder is
  compared exactly as it always was, and the backreference is the rule — two
  tokens that do not name one directory are not a shape this recorder writes
  and are left for the world's compare. A variable this tool compared less of
  is never silent: `; the recorder's own fragment stripped before comparing:
  RUSTDOCFLAGS` rides on the line and in the fact. Python traces cannot carry
  the fragment and their lines are byte for byte what they were.
- **Session set 1** (ruling R4, amended by A-§3 before any code). A re-run
  launched from another shell met a licence it could not earn: the handles a
  shell, terminal or agent session hands a process differ, and none of them is
  input to what a program computes. Fourteen exact names and one prefix,
  **positive and versioned**, are now named and never withhold —
  `env: unchanged outside session set 1 (<N> variables compared; …; <K>
  session variable(s) differ: <names>)` — while every other differing key
  withholds exactly as before. Not a *bearing* set: a list of the variables
  that "bear" on a program is a guess dressed as a rule, and the suite already
  held its falsifier in a test that records under `REFOCUS_TEST_LIMIT` and
  re-runs without it.
- **The harness rule anchors on the FIRST root, and never on a spawned
  thread** (ruling R3, `rust/HONESTY-BLIND-SPOTS.md` item 28). `#[test] fn` is
  an ordinary fn to rustc, so `thread::spawn(|| a_test_fn())` put a marked
  root on a thread the PROGRAM started, that thread was subtracted as the
  recorder's own, and the licence was granted over a thread nothing had
  compared — the direction that claims more. A spawn-named task
  (`spawn@<qualname>#<k>`) is now never the harness's whatever its root's
  mark, only the first root counts, and an `async` test fn carries no mark so
  its thread stays counted. `corpus/rust/refocus_spawned_test_fn` records the
  shape through the real driver.
- **Six files split before this slice edited any of them** (ruling R5).
  `docs/CARRIED-DEBT.md` → a second archive volume (archives are numbered
  volumes ≤ 800 lines); `rust/HONESTY.md` §13 → `rust/HONESTY-REFOCUS.md`;
  `refocus_cmd.py` → `refocus_report.py`; `visit.rs` → `visit/walk.rs`;
  `splice.rs` → `assemble.rs`; `lines.rs` → `lines/facts.rs`. Every one a pure
  move, tests and goldens green either side.
- **The recorder's tests leave no footprint either** (ruling R6). The three
  `driver_smoke.rs` tests that ran the whole driver named no store, so each
  run converted a trace into `~/.sensorium` — the store of whoever ran the
  suite. They name a scratch store now, and a new test pins the rule they
  rely on: with `SENSORIUM_DIR` set, `HOME` is not consulted at all.
  `corpus/run_corpus.py` gains **`--require-driver`**, which turns a skipped
  case into exit 1 and says so on the summary line and in `--json`; CI's rust
  corpus step passes it, because that job builds a driver precisely so those
  cases run and a green summary over cases nobody recorded is the dishonesty
  this harness exists to refuse. `tests/test_release_tokens.py` pins the three
  places this package's version lands — `pyproject`, the installed
  distribution's metadata, and this file's newest header — in both of the
  states that header legally has.
- **E4″ measured once, 2026-09-08 — H1–H7 PASS, H8 STOP on an instrument
  cell.** Pre-registered and §1 byte-locked before the instrument existed, then
  read once over the 61 kept originals of E4 under this slice's driver. The two
  questions the slice asked are answered **PASS at n = 61**: the harness-thread
  rule moved the licence word exactly as §1.2 predicted — **57 granted**,
  WITHHELD on the four thread-spawning tests with their program-thread counts
  **1 / 4 / 4 / 4** (E4′ read **0** granted, all 61 withheld by the confound R1
  removes) — and the recorder's fragment is gone from the compare:
  `RUSTDOCFLAGS` in **0 of 61** changed lists, the strip clause naming it on
  **61 of 61**, with the rt hash **differing on 61 of 61** pairs, so the strip
  was tested on every one under a driver build different from the originals'
  (`0.5.2` here, read from each re-run trace's own `meta.driver_version`; the
  kept store's `0.5.0` is **E4's** own §2 fact about those originals, carried
  into this record's §1.1 pre-registration — no field of E4″ reads it, and
  E4′ §2's `0.5.1` was the driver of E4′'s own re-runs).
  The verdict, the pair, session set 1 and both control
  arms held (H3–H6), and the instrument's own honesty row passed over all 69
  pairs (H7). **H8 STOPPED on this record's own reader**, not on the workspace:
  its three commands were green (corpus rc 0 over 63 cases with
  `--require-driver`, pytest rc 0, `cargo test --workspace` rc 0) and
  `corpus/rust/refocus_spawned_test_fn` did run, but the cell asking whether the
  case is present compared the bare name against a listing that spells Rust
  cases `rust/<name>` and so read a measured-looking `False`. The STOP stands as
  measured — kill 6 forbids an instrument change after the measurement — and the
  one-line fix is ruled for the next slice.

## 0.8.5 — 2026-09-07

Rung 4, slice 3: **the rung-4 debts** — the seven items slices 1 and 2 left in
`docs/CARRIED-DEBT.md` with their fixes spelled out, closed. Python **0.8.5**;
**`cargo-sensorium 0.5.1`** for the hard-linked shim and the `driver.rs` split,
**`sensorium-transform 0.4.2`** for a focus resolution that no longer splices,
**`sensorium-rt 0.4.0`** unchanged (neither the wire nor the runtime moved).
`TRACE_FORMAT` stays **4**: nothing here writes a new key into a trace but
`refocus_children`, which is optional meta.

- **The licence knows the recorder's own thread from the program's** (ruling
  R1). `cargo test` runs every `#[test]` function on a thread libtest spawns
  for it, so the untraced-thread caveat fired on all 61 pairs of E4 for that
  reason and no other — a clause that cannot not fire is not a finding. A
  non-main thread whose ROOT frame's site the manifest marks `#[test]` is now
  a **harness thread**, subtracted from the licence's untraced-thread counts
  and **named wherever one of those counts is printed**: `and 1 harness thread
  (libtest's per-test thread, excluded as the recorder's own)` where the clause
  joins a count, `; 1 harness thread (…) is not among these counts` on the
  `threads:` line, which counts what WAS compared. The root anchors it, which
  is a **bound** and not soundness in both directions — a mark below the root
  excludes nothing, but a thread the PROGRAM spawns whose first instrumented
  frame is itself a `#[test]`/`#[bench]` fn is read as harness and the licence
  can be **granted** over it, while an `async` test fn carries no mark so its
  harness thread stays counted (found by review 2026-09-07, not measured;
  `rust/HONESTY-BLIND-SPOTS.md` item 28) — and the set is empty on any trace
  with no site marks
  (every **Python** trace, byte-identical output) and empty unless the main
  thread is a RECORDED fact.
- **A child run is not the pair** (ruling R2). A re-run whose test spawns an
  instrumented program writes a second trace carrying `refocus_of`, and the
  pair lookup counted it: `refocus` refused "more than one" and advised a
  single-target selector at a caller whose selector was already single. A
  linked trace whose `ppid` is **another** linked trace's `pid` is now excluded
  from the pair, named on the pair line as `child runs excluded from the pair:
  <ids>`, stamped into the pair's trace as `refocus_children`, and still listed
  by `runs`. The >1-candidate refusal carries the same clause in the same
  words. `corpus/rust/refocus_child_run` records the shape through the real
  driver.
- **A target directory that MOVED is read as a relocation, not as a change the
  world made.** A refocus re-runs under whatever `CARGO_TARGET_DIR` the caller
  has, and cargo derives `CARGO_BIN_EXE_*`, `LD_LIBRARY_PATH` and
  `RUSTDOCFLAGS` from the root, so a re-run from a fresh target differed on all
  four and withheld the licence for it. Nothing is excluded **by name** — that
  would let a
  program really handed one extra directory on the loader's path earn a full
  licence. Each DIFFERING key is asked whether its difference disappears when
  the original's root is substituted for the re-run's, entry by entry down a
  `PATH`-like list and anchored at path boundaries on both sides; a key the
  rule explains is named (`N variable(s) differ only by the target directory:
  …; treated as unchanged`) on the env line and kept in the trace even where
  the licence is withheld for another reason. Anything else still withholds.
- **`info` says which checks could not run at all**, instead of printing the
  `licence verified:` lines alone and leaving a reader to infer that every
  other check ran and failed: `licence unverifiable: output (not recorded),
  children (not witnessed)`, and nothing where the stamp is absent. Its
  `threads started:` line takes the same harness partition as the licence, on
  the same screen.
- **A Rust screen says what its streams are in Rust's words.** The
  `threads:` line's scope parenthetical reads `(events outside any test or
  spawned thread)`: this converter writes one thread row — the main thread's —
  and routes every other thread's events into `task_fingerprints`, so `asyncio`
  there named a runtime that never ran.
- **The wrapper shim is a hard link, not a ~40 MB copy per focus** (ruling R3,
  `cargo-sensorium` **0.5.1**). E4 counted 62 shim entries under one target
  directory totalling 2 506 729 440 bytes, all of them the same binary.
  `install_shim` now links, falling back to a copy on any error — a
  `CARGO_TARGET_DIR` on another mount included — and names both failures when
  both fail. Sharing the driver's inode is safe because the key already hashes
  the driver's own bytes. Two guards ride with it: the leftover temporary is
  **unlinked first**, because a `tmp` left by a run that died between install
  and rename may itself be a link to the driver and `fs::copy` onto it would
  truncate the driver; and `set_permissions` runs on the **copy path only**, so
  nothing here ever writes the driver's inode. `du` over the shim tree now
  counts those bytes once, however many keys are present.
- **`fn_items` enumerates through the census path** (ruling R7,
  `sensorium-transform` **0.4.2**). Resolving `--focus` ran the whole splicing
  transform on every `.rs` file of the workspace — every offset computed, every
  fragment placed, every rewritten source assembled — and threw the string away
  to read two lists off it. It now runs the walk alone, under a named
  `census::Mode` (`Emitting` / `Census` / `Counting`) so the fourth combination
  of the two `bool`s it replaced is unspellable. One answer MOVED, deliberately:
  a file whose walk is clean but whose splicing half would fail answered `[]`
  under 0.4.1 and answers with its full row list now, so a `--focus` naming a
  function that is plainly in the file is no longer refused before cargo runs
  because some other file could not be spliced.
- **`driver.rs` splits** (ruling R7): the invocation record to `invocation.rs`,
  the cargo child's environment and launch to `launch.rs`. Behaviour-preserving
  moves; the cargo child's variables, values and order are unchanged (a 14-line
  `Ground` construction was added in `driver.rs`) and `driver_smoke.rs` is
  green.
- **Every raw and assembled acceptance results file carries `schema_version`**
  (ruling R4): `"e9/1"`, `"e4/1"`, `"e4p/1"`, with the renderer stating once
  when the assembled schema is later than the raw's. The E9 and E4
  `results.json` committed with their records are NOT re-derived — a derivation
  is stated, not rewritten — and `docs/CARRIED-DEBT.md` notes that those two
  files predate the field.
- **E4′ was measured once and STOPPED on H1**
  (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md`): the
  licence was granted on **0** of 61 pairs where §1.2 predicted 57 — not
  because R1 failed, since the harness exclusion fired and was **named on 61
  of 61** `threads:` lines and the four pairs §1.2 named report the
  program's own counts 1, 4, 4, 4 — but because the env clause withheld on a
  single key, `RUSTDOCFLAGS`, whose driver-injected `--extern
  sensorium_rt=<target>/sensorium/rt/<hash>/…` fragment carries a hash that
  moved with the driver build (0.5.0 recorded the originals, 0.5.1 re-ran
  them), so the clause read the recorder's own footprint as a change the
  world made; H2–H6 passed as pre-registered (MATCH 61 of 61, one pair on
  every pair, the shim at the driver's own single inode on all 61,
  `schema_version` present, and corpus, Python suite and `cargo test
  --workspace` green). The STOP stands: it is not re-rolled, no `src` change
  was made after it, and the ruled fix — strip that fragment as the
  recorder's own, then **E4″** over a subject with an original recorded under
  a different driver build — is carried in `docs/CARRIED-DEBT.md`.
- **Not funded** (ruling R6, until a use asks): `--window` on a Rust trace,
  refocus over a multi-process invocation, an inference-variable opt-out, and a
  per-site volume cap. The declared blind spots stand.

## 0.8.4 — 2026-09-07

Rung 4, slice 2: **`refocus` for Rust traces** — `sensorium refocus <run>
--focus <name>` re-runs the recorded `cargo sensorium` invocation one flag
deeper and issues the comparator's verdict on the pair, instead of refusing.
Python **0.8.4**; the crates move apart for the first time —
**`sensorium-rt 0.4.0`** unchanged (neither the wire nor the runtime moved),
**`sensorium-transform 0.4.1`** for the macro-tail guard, and
**`cargo-sensorium 0.5.0`** for `--refocus-of` and the three meta keys it
writes. `TRACE_FORMAT` stays **4**: all three keys are optional meta.

- **The brace-delimited-macro-tail guard, the one slice-1 debt that was a
  broken build** (ruling G1). `fn f() -> i32 { m! { 1 } }` — the shape of
  every `quote!`- or `html!`-terminated function — minted a LINE after the
  return value and produced a parse error, so the unit fell back whole. The
  `Stmt::Macro` arm now returns `None` when the macro is the block's tail,
  exactly as `Stmt::Expr(expr, None)` beside it already did. The compile-FAIL
  case is deleted and the shape is a compile-PASS golden through the
  real-rustc oracle under `-D warnings`; the golden carries the unit-fn half
  (`fn u() { m! { a } }`, one fewer LINE) that never failed to build and so
  had never been measured. `sensorium-transform` **0.4.1**;
  `rust/HONESTY-BLIND-SPOTS.md`'s bullet and `docs/CARRIED-DEBT.md`'s item are
  struck as taken.
- **The driver takes `--refocus-of <run id>`, and every run now records three
  invocation-scoped facts.** The flag is parsed where `--tier` and `--focus`
  are — only before the first bare `--`, at most once — and refuses twice
  before anything is rewritten or built: `REFUSED: --refocus-of <v> is not a
  run id; nothing was built.` for a path separator, `.`, `..`, an absolute
  path or an empty value (a trailing `.db` is stripped once), and
  `REFUSED: --refocus-of <id> names no trace in <store>; nothing was built.`
  for a value the current store does not hold. The shape check runs FIRST, on
  purpose: `--refocus-of ../traces/<a real run>` would otherwise stamp a link
  the store could never resolve. The converter writes `refocus_of`,
  `workspace_root` (the workspace the invocation ran in) and
  `invocation_processes` (the runner processes it produced — test binaries and
  doctests alike), and `capabilities.refocus` becomes **`true`** for every
  trace this driver converts: the recorder CAN be re-invoked, and whether one
  particular trace can be is a refusal, not a capability.
- **`refocus` has a Rust branch, and it re-runs the RECORDED command.** argv
  is `--refocus-of <run>` first and unconditional, then the ORIGINAL's
  recorded tier — never one the call asserts — then the original's
  `meta.focus` followed by the values this call added, then the original's own
  cargo argv; cwd is the recorded `workspace_root` and the store is the
  original's. So a refocus only ever captures MORE. **Five refusals come
  first**, each at exit 2 with `nothing was re-run` in it: `--window` (no
  per-activation runtime check exists on the Rust side); a run that is one of
  *n* processes of its invocation, naming the single-target selector that
  makes the count 1; no `workspace_root` recorded; a workspace since deleted;
  no `cargo-sensorium` to re-run with. **The pair is found in the STORE** by
  `refocus_of` plus the launch timestamp, never by parsing the driver's
  printed `run:` lines — zero candidates is `verdict: REFUSED` after the rerun
  at exit 3, more than one is REFUSED by count, and neither guesses. The
  comparator is unchanged: MATCH / DIVERGED / REFUSED keep their meanings and
  exits, the fingerprint is per task over CALL/RETURN/RAISE/HANDLED, and a
  LINE row never enters the hash — which is what lets a deeper re-run MATCH
  the run it came from.
- **The licence on a Rust pair says what it could not check.** Source,
  environment and exit status run for real; `output` and `children` are
  printed and stamped `unverifiable (not recorded)` / `unverifiable (not
  witnessed)` rather than compared, because `capabilities.output` and
  `capabilities.children` are false and comparing them would compare two empty
  sets and report agreement. **An unverifiable check is never counted as a
  verified one**, and the two counts are never summed. The blind-spot block
  after a Rust verdict is the Rust vocabulary's — output not recorded, threads
  from dependency code unnamed, and the line only a re-run can owe: the
  rebuild is its own cost, since `--focus` keys a fresh shim and rebuilds the
  matched units. `RUST.no_rerun_note`'s "arrives with rung 4" is retired and
  now names the command a reader may run instead.
- **Three Rust corpus cases, and they are the only cases whose QUESTIONS
  record.** The harness records each case once and a `refocus` question then
  launches the driver itself, through the gate's own driver environment:
  `refocus_match` (MATCH at exit 0, the licence GRANTED over four points, the
  pair in `runs`, and `watch last --at fill --expr b == 2` SATISFIED — the
  loop closed), `refocus_diverged` (a program that branches on a marker file
  its first run wrote: DIVERGED at causal step 1, exit 1) and
  `refocus_refused_many` (two test binaries: the single-target sentence at
  exit 2, and a store with no third trace in it).
- **Three pins moved with the capability, and each is a statement about a
  different recorder.** `tests/helpers.py`'s `RUST_CAPABILITIES` and
  `tests/test_runs_info.py`'s `RUST_CAPS` now read `refocus: True`, being the
  0.5.0 driver's traces; `docs/trace-format/vectors/v14-rust-refusals.json`
  keeps `refocus: false` and gains a sentence saying why it still holds — it
  describes a recording by `cargo-sensorium 0.4.0` or earlier, which is
  exactly what a current `refocus` refuses through — and its `no rerun was
  attempted` needle moves to the retired note's new text.
- **E4, measured once on a workspace nobody wrote this recorder for: five
  PASS and two REPORTED — all seven rows as pre-registered.** All 61 `#[test]`
  functions of the seven `pager_*_test.rs` files, one at a time under
  `--exact`, against an expected-MATCH list written and byte-locked first.
  H1 **0 of 61** pre-rerun refusals and 61 of 61 invocations reaching the
  driver; H2 **61 of 61** re-runs complete with libtest counts equal to the
  original's and **0** focused build failures; **H3 61 of 61 MATCH**, 0
  DIVERGED, 0 REFUSED, verdict word and exit agreeing on every one; H4
  REPORTED — source, environment and exit verified 61 of 61, output and
  children UNVERIFIABLE 61 of 61, and **0** licence lines claiming an
  unverifiable check as verified; H5 all three `watch` triples as predicted on
  both readings; H6 REPORTED; H7 every corpus case equal, the Python suite
  green, `cargo test --workspace` green. **The licence was WITHHELD on every
  one of the 61 pairs** — its untraced-thread clause cannot not fire on a
  `cargo test` trace, because libtest runs each test on a thread it spawns
  (counts 57×1, 1×2, 3×5). That is a finding about the licence's thread
  clause, not about the recorder; the candidate fix is named in the record and
  deliberately not applied, and is carried to `docs/CARRIED-DEBT.md` for a
  ruling. Recorded beside it: §1.4's expectation that "the first focus pays
  for the rt build" is falsified (first **6.661 s** against a later mean of
  **6.988 s**), and the pre-registered discriminator's MAIN condition has no
  subject here — every one of the 122 traces carries a 0-event MAIN stream.
  The named worker-pool hazard fired on exactly one pair and the comparator's
  order-independent multiset absorbed it into a MATCH. The record is
  `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4.md`, byte-locked
  at `8e7d837` and amended once before the instrument existed at `413f601`
  (both shas carried); read §4 and §5 before quoting any of it, and §5.6 for
  what it does and does not license.
- **What it cost, measured.** 61 focused rebuilds at a flat ~7 s each — about
  half of it cargo's own reported build — leaving **62** entries under
  `<target>/sensorium/shim` totalling **2 506 729 440** bytes (~2.5 GB), one
  unfocused base key from pass 1 and exactly 61 focused keys, none reused. The
  fresh E4 target reached **25.8 GB**. The per-focus shim COPY is now a
  measured debt rather than an estimated one, and the hard-link that would
  close it is `docs/CARRIED-DEBT.md`.
- **Versions: four pins accounted, three of them move.** `sensorium-rt` stays
  **0.4.0** — neither the wire nor the runtime changed — `sensorium-transform`
  0.4.0 → **0.4.1** (the macro-tail guard, a `src` fix to what a focused build
  emits), `cargo-sensorium` 0.4.0 → **0.5.0** (`--refocus-of`, the three meta
  keys, `capabilities.refocus`) and Python `sensorium` 0.8.3 → **0.8.4**. The
  fourth pin, `TRACE_FORMAT`, is accounted by staying **4**.

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
- **Versions: five pins accounted, four of them move; `TRACE_FORMAT` stays 4.**
  `sensorium-rt` 0.3.0 → **0.4.0** (the new wire kind), `sensorium-transform`
  0.3.1 → **0.4.0** (focus, LINE splices, `SiteKind::Line`), `cargo-sensorium`
  0.3.1 → **0.4.0** (`--focus`, resolution, LINE conversion, meta,
  capabilities) and Python `sensorium` 0.8.2 → **0.8.3** — four moves; the
  fifth pin, `TRACE_FORMAT`, is accounted by staying **4**. Traces recorded by an
  older runtime still read; the refusal sentence they carry moves with the
  recorder string, which is why `corpus/rust/stale_cache`'s pin changed in
  its version token and nothing else.
- **Two documents were split so neither passed 800 lines**, both deliberately
  and both with wording and order unchanged: `rust/HONESTY.md` §11 is now
  `rust/HONESTY-ERR-FLOW.md`, and the README's `exceptions`, `watch` and
  `flow` sections are now `docs/query.md`. Each keeps a pointer where it was.
