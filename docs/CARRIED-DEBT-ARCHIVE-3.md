# CARRIED-DEBT — volume 3

Rung 4's slice 3 section, **moved here 2026-09-08 (the queue buttoned up) so
[`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays under 800 lines**. It is the
third numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file. The move was named before it was needed — the queue slice
measured its own section against the live file and cut the oldest one rather
than discovering the ceiling at 800, which is the rule this ledger has now
kept four times. **The wording, the order and the strikes are unchanged**,
including the strikes the queue slice itself made in the section below: a
resolved item is struck through here exactly as it was there, never deleted,
and the house rule stated in `docs/CARRIED-DEBT.md`'s header governs every
volume. A deferred item below is still open unless it is struck.

## 2026-09-07 — rung 4 slice 3, the rung-4 debts (Python 0.8.5 / driver 0.5.1 / transform 0.4.2)

### Settled

- **The harness thread** — slice 2's first deferred item, struck above as taken
  at `11b7e8a` (with `d9115a5`, `2d38ff4`, `85d1860` and `b1a7771`) under
  **ruling R1**. A non-main thread whose ROOT frame's site the manifest marks
  `#[test]` is the recorder's own, subtracted from the licence's
  untraced-thread counts and NAMED wherever one of those counts is printed —
  joined to the count where the sentence counts what WAS compared, and set
  apart in a clause of its own on the line that counts what was not. Python
  traces carry no site marks, so their output is byte-identical by
  construction.
- **A child run is not the pair** — struck above as taken at `d4cccd9` (with
  the corpus case at `79cda14`) under **ruling R2**. The pair lookup excludes a
  linked trace whose `ppid` is another linked trace's `pid`, names the excluded
  ids on the pair line and in the >1-candidate refusal, and stamps them as
  `refocus_children`; `runs` still lists them.
- **A target directory that MOVED is not a world that changed** (Task 5b, at
  `1a76757` with `d43b7aa`). Not one of §0's seven: it was found in Task 5's
  dry run, ruled before any E4′ number was read, and recorded as the record's
  own amendment A1. Keys whose values differ ONLY by substituting the recorded
  `CARGO_TARGET_DIR` root for the current one — entry by entry down a
  `PATH`-like list, anchored at path boundaries on both sides — are named and
  treated as unchanged; nothing is excluded by name, and every other difference
  still withholds.
- **The shim is a hard link** — struck above as taken at `36d2fe9` (with
  `2b8b5fb` and `4edd5c7`) under **ruling R3**, `cargo-sensorium` **0.5.1**,
  with the unlink-first guard and `set_permissions` on the copy path alone, so
  the driver's own inode is never written.
- **`schema_version` in every results file** — struck above as taken at
  `e0f469c` under **ruling R4**, with the E9 and E4 files stated as predating
  the field rather than re-derived.
- **Housekeeping** — struck above as taken under **ruling R7**: `info`'s
  `licence unverifiable:` line at `11b7e8a`; `driver.rs` split to
  `invocation.rs` and `launch.rs` at `03a68d3` and `095be7e`; `fn_items`
  through the census path at `22fbe02` (with `ba3edb5`), `sensorium-transform`
  **0.4.2**.
- **A Rust screen says what its streams are in Rust's words** (`4ed802d`). The
  `threads:` line's scope parenthetical reads `(events outside any test or
  spawned thread)`; this converter writes one thread row and routes every other
  thread's events into `task_fingerprints`, so `asyncio` there named a runtime
  that never ran.
- **E4′, pre-registered §1-alone and byte-locked before the instrument
  existed** (`2991c3b`), amended once before any number was read (`d5efaab`,
  amendment A1 — the env clause and the launch environment) with the lock test
  following the amendment and carrying the original sha (`8954d3a`), and a
  preflight that refuses to launch unless this process's environment matches
  every original's recorded one under the licence's own exclusions
  (`10e2712`, `pins.env_parity`). The record carries its own numbers.

### Deferred, with rulings

- ~~**The env clause's tiered set is RULED and NOT BUILT.** The relocation rule
  above closes the target-directory case; a re-run launched **from another
  shell** still meets an unearnable licence, because session-identity variables
  differ there and every differing key that is not the recorder's own or shell
  bookkeeping withholds. *The ruling, so the next slice need not re-derive it*
  (E4′ §1.5, *carried, not built*): a named, versioned **positive set** of
  build-and-run-bearing variables — `PATH`, `HOME`, `USER`, `LOGNAME`, `LANG`,
  `LC_*`, `TZ`, `TMPDIR`, `CARGO*`, `RUST*`, `LD_*`, `DYLD_*`, `SSL_CERT_*`,
  `PYTHON*`, `DEBUGINFOD_URLS` — withholds; every other differing key is
  counted and NAMED but does not withhold. Not built before this measurement
  because fewer source changes before a measurement is the rule and E4′ does
  not need it: its runner pins the two certificate variables and refuses on any
  other difference instead.~~ — **Ruled DIFFERENTLY 2026-09-08** and built at `09aad49`,
  design amendment **A-§3**. A positive list of the variables that "bear" on a
  program is a guess dressed as a rule, and this repository's own suite held
  its falsifier: a test that records under `REFOCUS_TEST_LIMIT` and re-runs
  without it — a variable the program demonstrably READS, on no bearing list
  anyone would write — would have earned a full licence. What shipped is the
  mirror image: today's default stands, any differing key withholds, with ONE
  positive versioned exception, **session set 1**, the handles a shell,
  terminal, agent or login session hands a process. Measured by E4″ H4/H5/H6.
- ~~**`src/sensorium/query/refocus_cmd.py` is at 789 of 800.** The next change to
  that file splits it first. The natural seam is the report: `_print_thread_line`,
  `_diverged_why`, the verdict block and the blind-spot print are one screen's
  worth of printing sitting beside the re-run's control flow.~~ — **Taken 2026-09-08** at `b7c9a20`, before this
  slice changed a line of that file: `report`, `_print_thread_line`,
  `_diverged_why` and `_stamp` moved to `refocus_report.py`, leaving
  `refocus_cmd.py` at 605 lines and the new file at 207, with the re-export
  block so `refocus_cmd.<name>` still resolves for all four.
- ~~**`visit.rs` 773, `splice.rs` 762 and `lines.rs` 762**, all under
  `rust/sensorium-transform/src`, and `rust/HONESTY.md` at **794 of 800**
  after this slice's §13, its fix round and the fix wave's correction to §13's
  direction claim — the NEXT sentence added to that file splits it first, not
  the one after. The rule this file has kept twice applies: the next change to
  any of them splits it first rather than discovering the ceiling. For
  `visit.rs` the seam is the `Ctx` bookkeeping against the `Visit` impl; for
  `rust/HONESTY.md` it is the one the index already took — a section moves to a
  file it links.~~ — **Taken 2026-09-08**, each split before
  this slice edited any of them (ruling R5): `visit.rs` → `visit/walk.rs` at
  `853271a`, `splice.rs` → `assemble.rs` at `91df4a3`, `lines.rs` →
  `lines/facts.rs` at `b949129` (`sensorium-transform` **0.4.3**, goldens byte
  for byte), and `rust/HONESTY.md` §13 → `rust/HONESTY-REFOCUS.md` at
  `114c231` — the same commit that moved rung 4's slices 1 and 2 out of this
  file into archive volume 2. The split named before it was discovered, twice
  over.
- ~~**`cargo test --workspace` writes traces into the developer's real store.**
  Several driver tests record through the real pipeline without setting
  `SENSORIUM_DIR`, so a workspace test run leaves runs in `~/.sensorium/traces`
  and a later `sensorium last` can name one of them. *The fix*: every test that
  records sets `SENSORIUM_DIR` to its own temporary directory, the way
  `convert*.rs` already do. It is a test-only change and it was not made after
  the measurement.~~ — **Taken 2026-09-08** at `fe8da06` (ruling R6): the three
  `driver_smoke.rs` tests that ran the whole driver name a scratch
  `SENSORIUM_DIR`, and a new test pins the rule they rely on — with
  `SENSORIUM_DIR` set, `HOME` is not consulted at all.
- ~~**The corpus gate is the only gate that catches a changed CLI sentence, and a
  run without the driver reports the Rust cases as SKIPPED rather than
  failing.** That is correct for the Python CI matrix, which has no Rust
  toolchain — but it means a green local run proves nothing about a printed
  Rust line unless `SENSORIUM_CARGO_SENSORIUM` is set. Two fix rounds of this
  slice shipped with those cases skipped before the gate was run with the
  driver. *The fix, unbuilt*: make a skipped Rust case a non-zero exit under an
  explicit `--require-driver`, and use it wherever printed wording changed.~~ — **Taken 2026-09-08** at
  `fe8da06`: `corpus/run_corpus.py --require-driver` makes a skipped case exit
  1 and says so on the summary line and in `--json`; CI's Rust corpus step
  passes it. E4″ H8 ran the gate that way — 63 cases, rc 0, none skipped.
- **`tasks:` and "task stream" are the last asyncio nouns on a Rust screen.**
  `vocab.py` moved every language-bearing sentence to the recorder's own words;
  these two stayed, and they are the trace format's own word for the row —
  `tasks` is a table, and a Rust thread's stream really is a `task_fingerprints`
  row. *Ruled: left alone.* Renaming the printed noun without renaming the
  table would put two words on one fact, which is the failure `vocab.py` exists
  to prevent. If it moves, it moves in both places at once.
- **The zero-candidate refusal wording under a pid cycle.** `find_pair` reads a
  trace as a child when its `ppid` is ANOTHER linked trace's `pid`. Two traces
  each naming the other would leave no candidate at all, and the refusal would
  say the re-run produced no linked trace when it produced two. *Ruled: left as
  is.* The topology is impossible — a pid cycle is not a process tree — and a
  branch written for it could never be exercised, so it would be untested code
  standing where an honest refusal already stands.
- ~~**The fourth E4′ lock test checks table rows and a 200-character prefix, not
  a full line diff.** `test_the_amendment_ADDED_section_1_5_and_moved_no_earlier_row`
  compares every `|` row of §1 byte for byte at the two commits and then asserts
  the amended §1 starts with the first 200 characters of the original's
  pre-§1.5 text. A prose edit in §1.3 or §1.4 beyond that prefix, made in the
  same commit as the amendment, would pass. The rows are what the endpoints
  read, which is why the row check is the load-bearing one; a full diff of the
  pre-amendment range is the stronger check and was not written.~~ — **Taken 2026-09-08** at `32aab32`: the whole
  pre-amendment range is compared byte for byte, the `## 2` heading the
  extraction stops at is asserted as the tail, and the check was measured
  DISCRIMINATING — one byte moved at offset 900 passes the old rows-and-prefix
  test and fails this one.
- ~~**`RUSTDOCFLAGS` carries the recorder's own footprint, and the env clause
  reads it as the world's.** E4′'s H1 STOPPED on it: the driver injects
  `--extern sensorium_rt=<target>/sensorium/rt/<hash>/…` with its
  `-L dependency=…`, the 5b rule relocates the target root inside it correctly,
  and the `<hash>` — which keys the `sensorium-rt` build — moved anyway,
  because the originals were recorded by driver **0.5.0** and re-run by
  **0.5.1**. `differs_only_by_root` is right to return false; the key falls
  into the changed list and withholds. *The ruling, from the record's §5*: the
  driver-injected fragment is **stripped before the compare as the recorder's
  own**, on the precedent this licence already sets twice (the `SENSORIUM_*`
  variables, and R1's harness thread); **anything else in `RUSTDOCFLAGS` stays
  the world's** and still withholds — the rule is about that fragment, never
  the variable. Then **E4″** re-measures §1.2's question over a subject that
  includes an original recorded under a different driver build, the one
  condition under which the confound is visible. Not applied in this slice:
  kill 6 forbids a `src` change after the measurement to make it come out
  differently.~~ — **Taken 2026-09-08** at `0810bee` (with `83d48ff`)
  under **ruling R1**, and **measured by E4″ H2**: `RUSTDOCFLAGS` in **0 of
  61** changed lists, the strip clause naming it on **61 of 61**, and the rt
  hash differing on **61 of 61** pairs, so no pair's strip went untested.
- **R6's four items are ruled NOT FUNDED**, in the design's own words: *`--window`;
  refocus over multi-process invocations; an inference-variable opt-out; a
  per-site volume cap — **not funded** until a use asks; declared blind spots
  stand.* Each of the four still has its own bullet above, unstruck, because
  nothing shipped and the refusal or the bound is still what a reader meets.
- ~~**Half of the version-token fix is taken; the probe half is not.** The
  process lesson below assigns two fixes to Task 7b. The **install refresh is
  taken**: `pyproject.toml` moved to 0.8.5 and the editable install was
  refreshed in the same task, so the distribution metadata
  `importlib.metadata.version('sensorium')` reads `0.8.5` and no longer the
  stale `0.6.0` three records paid for. The **probe half is deferred**: E4′'s
  preflight still runs `import sensorium; print(sensorium.__version__)` against
  a package that has no `__version__` and still captures stdout only, so a
  failed probe still records `""` rather than `null` with its reason. It was
  not changed here because the measurement is closed and its instrument is not
  edited after the fact — the same reason kill 6 gives for `src`. *The fix,
  unchanged*: record `null` and the reason, and probe a token the package
  actually exposes.~~ — **Taken
  2026-09-08** at `1fb001b`: the E4-family preflight probes
  `importlib.metadata.version('sensorium')`, captures both streams, and records
  `null` **with its reason** where the probe fails. E4″ H7 read the token
  `0.8.5` with `version_probe_ok` true and the reason `null`, and its own gate
  forbids the empty string.
- ~~**R1's harness rule is ROOT-MARK-ANCHORED, and the bound has a false-grant
  end.** A thread the PROGRAM spawns whose first instrumented frame is itself
  a `#[test]`/`#[bench]` fn is read as the harness's and subtracted, so the
  licence can be GRANTED over a program thread; an `async` test fn carries no
  mark, so its thread stays counted and the licence withholds — the safe end.
  Found by review 2026-09-07, **not measured**; E4′'s 61 pairs cannot reach
  it; stated in full as `rust/HONESTY-BLIND-SPOTS.md` item 28. *The ruling*: a
  task named `spawn@<site>` is never harness whatever its root's mark, and
  only the FIRST root's mark counts — **measured before it ships**. Not built
  here (kill 6), which also leaves the docstring's own overclaim standing.~~ — **Taken 2026-09-08** at `b2f07e3` under **ruling R3**: a
  spawn-named task is never the harness's whatever its root's mark, only the
  FIRST root decides, and the docstring was rewritten with it. **Measured
  before it shipped** by `corpus/rust/refocus_spawned_test_fn` through the real
  driver, where the old rule granted; blind spot 28 carries the dated closure.
- ~~**No test pins that the release tokens agree.** Nothing asserts that
  `pyproject.toml`'s version, `importlib.metadata.version('sensorium')` and
  the newest `CHANGELOG.md` header are one token, or that the header carries a
  date rather than `(unreleased)`; the token has gone stale silently three
  times (E9, E4, E4′ each recorded `0.6.0`). *Ruled: a small
  `tests/test_release_tokens.py` next slice*, not in a docs-only fix wave.~~ — **Taken 2026-09-08** at
  `fe8da06`: `tests/test_release_tokens.py` pins `pyproject.toml`, the installed
  distribution's metadata and the newest `CHANGELOG.md` header as one token, in
  both of the states that header legally has, and each shape rule is shown
  refusing what it is for.

### Process lessons

- **Mutation-test on a COMMITTED tree.** A mutation run over an uncommitted
  working tree cannot be undone by `git checkout`, and a same-length mutation
  restored within the same second leaves CPython running the mutant's stale
  bytecode. Both are avoidable by mutating from a commit and purging
  `__pycache__`; this slice's two surviving mutants (`85d1860`) were found that
  way.
- **Every Python change to a printed sentence runs the corpus gate WITH the
  driver.** The Python suite pins the words a fixture reaches; the corpus is
  the only gate that puts the real driver behind them, and it skips silently
  enough that two fix rounds went by with the Rust cases unrun. A printed line
  changed without that gate is a line nobody checked.
- **A preflight DRY RUN before a measurement found two instrument confounds
  that no amount of re-reading the pre-registration would have.** §1.2's
  expected licence partition had been derived from the prior run's thread
  counts alone; a fresh `CARGO_TARGET_DIR` (mandated by the same document for
  H4's inode census) would have withheld the licence on all 61 pairs for a
  reason unrelated to R1, and the launch shell's own variables would have done
  it again. Both were ruled and recorded as amendment A1 **before any number
  was read**. The lesson is the order: run the instrument's first pair, read
  what it printed, and amend the lens then — not after the loop closes, when an
  amendment is indistinguishable from a rationalisation.
- **A record's version token comes from installed metadata, and this one was
  stale twice over.** E4′'s §2 recorded the installed distribution token as
  `0.6.0` while `pyproject.toml` said 0.8.4 — the same editable-install
  staleness E9 and E4 already paid for, now on a third record. Worse, the
  preflight's tree-side probe ran `import sensorium; print(sensorium.__version__)`
  against a package that has no `__version__` and captured **stdout only**, so
  the `AttributeError` on stderr became `""` in the lens: a failed probe
  recorded as a blank that reads as measured. Both stand — records are not
  rewritten, and no endpoint gates on either token. **The fix belongs to 7b**:
  refresh the install after the version bump, and a probe that fails records
  `null` with its reason — the install half is taken; see *Half of the
  version-token fix is taken* above.
