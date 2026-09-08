# CARRIED-DEBT

Appended at every merge: *what this slice settled* → *deferred, with
rulings* → *process lessons*. Resolved items are struck through, never
deleted.

Started 2026-09-05, at rung 3's close. Earlier slices carried their debt in
the rung-3 inbox
(`docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` §3) and in the
gitignored plan ledgers; nothing there is restated here, and that document
stays the record for rungs 0–2.

**The earlier sections moved 2026-09-06** — rung 3, the borrow repair and the
rung-4 entry slice are
[`docs/CARRIED-DEBT-ARCHIVE.md`](CARRIED-DEBT-ARCHIVE.md), wording, order and
strikes unchanged, so a deferred item there is still open unless it is struck.
The split was named in this file before it was taken (the focus tier's own
"files near the ceiling" bullet, below) rather than discovered at 800; the rule
above governs both files, and the next slice appends here.

**Rung 4's slices 1 and 2 moved 2026-09-08** — the focus tier and the refocus
slice are [`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md),
wording, order and strikes unchanged, so a deferred item there is still open
unless it is struck. Volume 1 was itself at 594 lines when this file next
needed room, so the archive is **numbered volumes, each under 800 lines**, and
the rule at the top now governs three files rather than the two named above.
This file keeps the newest sections, and the next slice's section is appended
here.

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
- **The fourth E4′ lock test checks table rows and a 200-character prefix, not
  a full line diff.** `test_the_amendment_ADDED_section_1_5_and_moved_no_earlier_row`
  compares every `|` row of §1 byte for byte at the two commits and then asserts
  the amended §1 starts with the first 200 characters of the original's
  pre-§1.5 text. A prose edit in §1.3 or §1.4 beyond that prefix, made in the
  same commit as the amendment, would pass. The rows are what the endpoints
  read, which is why the row check is the load-bearing one; a full diff of the
  pre-amendment range is the stronger check and was not written.
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

## 2026-09-08 — rung 4 slice 4, the recorder's footprint (Python 0.8.6 / driver 0.5.2 / transform 0.4.3)

### Settled

- **The recorder's own compiler flags are not a change the world made** —
  slice 3's `RUSTDOCFLAGS` item, struck above as taken at `0810bee` (with
  `83d48ff`) under **ruling R1**. Every occurrence of the driver-injected
  `--extern sensorium_rt=… -L dependency=…` fragment, both tokens naming ONE
  directory, is removed from both sides before the compare; the remainder is
  the world's and is compared exactly as before; the key is named on the env
  line and in the stamped fact. A value in which nothing matched comes back
  byte for byte, so a variable this rule never touched cannot be widened by it.
- **Session set 1** — slice 3's tiered-set item, struck above as **ruled
  differently** and built at `09aad49` under **ruling R4 as amended by A-§3**.
  Fourteen exact names and one prefix, positive and versioned, are counted and
  named and never withhold; every other differing key withholds exactly as
  before. The set's number rides in the printed sentence so a key found to bear
  can leave it with a date.
- **The harness anchor is the FIRST root, and a spawn-named thread is never the
  harness's** — slice 3's false-grant item, struck above as taken at `b2f07e3`
  under **ruling R3**, and **measured before it shipped** by
  `corpus/rust/refocus_spawned_test_fn` through the real driver, where the
  previous rule printed `no thread started besides the main one and 3 harness
  threads` and granted.
- **Six files split before this slice edited any of them** — struck above under
  **ruling R5**: `docs/CARRIED-DEBT.md` → archive volume 2 and `rust/HONESTY.md`
  §13 → `rust/HONESTY-REFOCUS.md` at `114c231`; `refocus_cmd.py` →
  `refocus_report.py` at `b7c9a20`; `visit.rs` → `visit/walk.rs` at `853271a`;
  `splice.rs` → `assemble.rs` at `91df4a3`; `lines.rs` → `lines/facts.rs` at
  `b949129`. Every one a pure move, tests and goldens green either side.
- **R6's small items, all four** — struck above where slice 3 raised them, at
  `fe8da06`: the three `driver_smoke.rs` tests name a scratch `SENSORIUM_DIR`
  (with a test pinning that `HOME` is not consulted when it is set);
  `corpus/run_corpus.py --require-driver` makes a skipped case exit 1 and CI's
  Rust step passes it; `tests/test_release_tokens.py` pins the three places this
  package's version lands; and `harness_threads`' docstring says what is true
  rather than claiming soundness in both directions (`b2f07e3`).
- **The E4′ instrument gaps this slice could close** — struck above for the
  version probe, at `1fb001b`: the licence partition reads the threads line and
  records which line each count came from, the verified/unverifiable counts are
  built from the rows the runner actually writes, and a failed version probe
  records `null` **with its reason** instead of an empty string. E4″'s H7 read
  all three back: **0** null partition cells over 69 pairs, every count carrying
  its source line, non-null verified counts, and the token `0.8.5`.
- **E4″, pre-registered §1-alone and byte-locked before the instrument existed**
  (`b9abcbd`, `2acdc21`, with the lock at `eec532b` and re-anchored at
  `eaabd70`), the 61 rows locked by sha256 in a sibling, amended once before the
  measurement (`2b0eb5b`, **A-R8** — no build cache deleted by this slice), and
  **measured once** (`3ce75f2`, with the record's corrections at `6688292`):
  **H1–H7 PASS, H8 STOP on an instrument cell.** The two questions the slice
  exists for are answered at n = 61 — granted **57** with the four predicted
  withholdings at 1/4/4/4, and `RUSTDOCFLAGS` in **0 of 61** changed lists with
  the rt hash differing on 61 of 61 — under a driver build different from the
  originals', the one condition E4′ could not create.

### Deferred, with rulings

- **H8's presence reader compares a bare case name against a prefixed
  listing.** The corpus collector spells Rust cases `rust/<name>` and the reader
  asked for the bare `refocus_spawned_test_fn`, so it printed a measured-looking
  `False` where `null` **with its reason** was owed — the case was collected,
  ran through the built driver under `--require-driver` and came back equal. It
  is E4′ gap 3 one turn on: there the same reader returned `null` because no
  listing existed, and this slice gave it one. *Ruled*: the STOP stands as
  measured (kill 6 forbids an instrument change after the measurement), and the
  fix belongs to the next slice — match on the listing's last path segment as
  well as the whole name, and record `null` carrying the listing command and its
  rc when neither spelling is found. E4″ §5 and its findings sibling, gap 1.
- **R7's four are ruled NOT FUNDED**, in the design's own words: `--window`;
  refocus over multi-process invocations; an inference-variable opt-out; a
  per-site volume cap — not funded until a use asks, declared blind spots stand.
- **`{told}`, the session clause, is on the env LINE but not in the stamped FACT
  on a withheld pair** (`refocus_world._env_state`). That is what the plan
  mandated, and the cost is that `info` replays less than the screen said. *The
  fix, unbuilt*: carry the clause into the withheld pair's fact the way the
  relocation and strip clauses already are.
- **`is_relocation_note` is a two-rule predicate under a one-rule name**
  (`refocus_env.py`): it recognises the relocation clause and the strip clause
  both. *Ruled: left alone this slice* — renaming it touches every caller, and
  the docstring states both rules; the next change to that function renames it.
- **A key present on one side only, whose whole value was our fragment, still
  withholds.** The strip leaves an empty string on the side that had it and the
  key is absent on the other, so `_env_diff` sees a difference and — for a key
  outside session set 1 — partitions it as a change. Conservative, and the
  direction that claims less. Measured, so the bullet says which key it is
  about: `_env_diff({"FOO": <fragment>}, {})` gives changed `['FOO']`, while
  `_env_diff({"CLAUDE_CODE_X": <fragment>}, {})` gives changed `[]` and session
  `['CLAUDE_CODE_X']` — session membership is tested BEFORE the changed list, so
  a session key on one side only never withholds, which is R4 working as ruled
  and not a second conservatism.
- **`refocus_world.py` is at 777 of 800.** The next change to that file splits
  it first. The seam is the thread bookkeeping — `harness_threads`,
  `harness_exclusion`, `harness_note`, `uncompared_threads` → `refocus_threads.py`.
- **`ENV_RECORDER_OWN` (the instrument's env-line reader) is right only while
  the recorder's own clause is last on the line.** True by construction today —
  `refocus_rust._env_of` assembles it last — and nothing pins the invariant. *The
  fix, unbuilt*: assert the ordering where the line is built, or anchor the
  reader on the clause's own start instead of the line's end.
- **Instrument minors, all in the E4″ runner and none load-bearing on a
  verdict**: `bound_sentence` at a whole number of hours drops the "0 min";
  `_k_reason` renders a Python list repr into prose; no test drives a multi-key
  strip list; `_drops` has no `n != GATE_N` clause (the phase checks catch it);
  H7 gates over its own `censused` denominator; a dry run that kills a row after
  a number has been read exits 7; exit 9 has two documented shapes.
- **What the corpus case does not pin.** `corpus/rust/refocus_spawned_test_fn`
  pins the counts and the spawn name but not that the spawned thread's root is
  the MARKED fn — fixture (a) of `tests/test_refocus_licence_rust.py` does;
  `corpus/rust/README.md`'s `last` reason for that case covers its second
  question only; the `task(thread)` lookup's thread-serial == task-id invariant
  is unstated at `refocus_world.py` though `convert/sqlite.rs`'s `insert_task`
  guarantees it (`id` is the thread serial, never a rowid); and `"spawn@" in name` is an equivalent mutant of the spawn-name test that
  no case distinguishes.
- **`--bench --require-driver` is inert.** The flag catches cases that were
  skipped, not cases that vanished from the listing, and `--bench` reports
  rather than gating. *Ruled: left as is* — the flag's promise is about skips.
- **The golden pair `focus_deferred_init.{in,out}.rs:5` names `lines.rs`'s
  `statement_deltas`**, which now lives in `lines/facts.rs`. Golden bytes are
  not edited for a comment: they stay until that golden legitimately changes.
- **Three small residues of this slice's splits.** Task 1's dead-import trim
  narrowed the `refocus_cmd` namespace by seven names (no consumers, and the
  re-export block covers the four the report owns); the "two files" re-export
  comments now describe a shape three modules share; and
  `rust/HONESTY-REFOCUS.md` carries a bare `---` from the move — in
  `rust/HONESTY.md` it separated §13 from §14, and here it divides the moved
  body from this slice's amendments, a use it was not given on purpose.
- **The rung-5 lever, and the principled end of session set 1**: record which
  environment variables the program actually READ, and compare only those. It
  retires blind spot 29 rather than bounding it — the exemption today rests on a
  claim about intent that nothing in the trace checks — and it is the only fix
  that makes the licence's environment check say what a reader assumes it says.
  Not funded here; it needs a runtime change on both recorders.
- **Two build caches on the second disk are Brice's to free** (A-R8): the E4 and
  E4′ targets, 24 GB and 21 GB, kept through this slice because deleting is a
  destructive action and those are not the design authority's to take. This
  slice's own E4″ targets (~22 GB, the run's and the corpus's) are scratch once
  the record is merged. Build caches are reproducible; the records and the trace
  stores are the evidence, and none of them is touched.

### Process lessons

- **A pre-registration's `awk` range needs its next-section stub at lock
  time.** The E4″ lock byte-locks §1 by reading from the `## 1.` heading to the
  `## 2.` one, and §2 did not exist yet, so the range ran to the end of the file
  and the lock covered text §1 does not own. The stubs were written and the lock
  re-anchored before any number was read (`2acdc21`, `eaabd70`) — but the lesson
  is to write the stub in the same commit as the range.
- **Grep the suite for a design's falsifier before ruling it.** The first §3
  ruled a positive "bearing set" and the test that falsifies it was already in
  the repository, green, pinning a withheld licence over a variable the program
  reads. It cost one amendment before any code; it would have cost a shipped
  rule that grants over changed input.
- **Build parser tests from real lines, not from templates.** A dry run with
  `--dry-arms` caught the strip-clause regex over-running into the next clause,
  which the synthetic tests could not see, because the real env line joins its
  clauses with two spaces and the templates did not. The dry run is the cheapest
  place a real line is available before the measurement.
- **An instrument name must come from the producer, never be retyped.** H8's
  presence reader was handed a listing whose Rust entries carry a `rust/` prefix
  and asked for the bare name — the same class as the parser lesson above, one
  level up: a name compared against a producer's spelling that nobody read.
  Every reader that names another component's output takes the spelling from
  that component.
- **Child modules see their parent's privates.** The `visit.rs` split was
  planned with five `pub(super)` bumps and needed none: a `mod walk;` inside
  `visit.rs` can reach `Ctx`'s private fields and methods. Plan the visibility
  from the language's rule, not from the shape of the move.
- **One implementer at a time held, again.** Every commit of this slice was
  written by a single implementer in the one worktree, and no commit swept
  another's staged files — the failure mode two slices ago. It costs
  serialisation and it is worth it.
