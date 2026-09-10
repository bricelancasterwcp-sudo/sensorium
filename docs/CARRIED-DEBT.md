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
"files near the ceiling" bullet, below) rather than discovered at 800; ~~the
rule above governs both files, and the next slice appends here~~ — **corrected
2026-09-08**: **three** files, not two. The paragraph below superseded this
sentence when volume 2 was cut and left it standing, which is how a reader
arriving at this line alone would have counted the archive wrong; the rule at
the top governs every volume, and the next slice appends to *this* file.

**Rung 4's slices 1 and 2 moved 2026-09-08** — the focus tier and the refocus
slice are [`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md),
wording, order and strikes unchanged, so a deferred item there is still open
unless it is struck. Volume 1 was itself at 594 lines when this file next
needed room, so the archive is **numbered volumes, each under 800 lines**, and
~~the rule at the top now governs three files rather than the two named
above~~ — **corrected 2026-09-08**: **four** files, the paragraph below having
superseded this sentence when volume 3 was cut, exactly as this paragraph
superseded the one above it. A count of volumes stated in a paragraph goes
stale every time a volume is cut; the rule at the top governs every volume,
whatever their number.
This file keeps the newest sections, and the next slice's section is appended
here.

**Rung 4's slice 3 moved 2026-09-08** — the rung-4 debts slice is
[`docs/CARRIED-DEBT-ARCHIVE-3.md`](CARRIED-DEBT-ARCHIVE-3.md), wording, order
and strikes unchanged (the queue slice's own strikes inside it included), so a
deferred item there is still open unless it is struck. ~~The rule at the top now
governs **four** files.~~ — a count in a paragraph, which the paragraph below
made stale exactly as this file's header has twice recorded happening; the rule
at the top governs every volume, whatever their number. The move was measured
before it was made: this slice's section would have taken the live file to 790
lines, and the ledger's own rule is to cut the oldest section rather than
discover the ceiling.

**Rung 4's slice 4 moved 2026-09-09** — the recorder's-footprint slice is
[`docs/CARRIED-DEBT-ARCHIVE-4.md`](CARRIED-DEBT-ARCHIVE-4.md), wording, order
and strikes unchanged, so a deferred item there is still open unless it is
struck. Measured before it was made, the way the rule asks: the S5 rung-1
section below was drafted at **270** lines against a live file of **676**, and
the oldest section was cut rather than the ceiling discovered. This file keeps
the newest sections, and the next slice's section is appended here.

## 2026-09-08 — the queue buttoned up (Python 0.8.7 / rt 0.4.1 / transform 0.4.4 / driver 0.5.3)

### Settled

- **The queue itself.** Four ledgers carried **116** open bullets at `f14d2f6`.
  Brice funded three buckets and left the fourth: **A** (54 mechanical rows
  whose fix was already written), **B** (7 rows about the 800-line ceiling),
  **D** (5 rows closable only by a dated note); **C** (43) is untouched and is
  the next conversation. Of A, **47 were taken whole**, 3 partly and 4 not at
  all, each named below. Every strike is in the section where the debt was
  raised — this file and all three archive volumes — and the rung-3 inbox,
  which is a spec, carries an appended dated line per item instead of a
  strike. **This file's own ceiling was measured before it was met**: the
  section you are reading would have taken it to 790 lines, so slice 3's
  section moved to [`docs/CARRIED-DEBT-ARCHIVE-3.md`](CARRIED-DEBT-ARCHIVE-3.md)
  first, wording, order and strikes unchanged, on the rule volume 2 set.
- **Thirteen files split before anything edited them, and four more the
  ceiling caught mid-slice** (rulings R2 and R9). `tests/programs.py` →
  `flow_programs.py` + `async_programs.py` (`b05046b`); `test_tree_frame.py` (`718a013`),
  `test_boot_cli.py` (`5ef40e5`), `test_exceptions.py` (`71d18b8`),
  `test_diff.py` (`d3823b4`), `test_tracer.py` (`4267251`),
  `test_refocus.py` (`f24745c`), `test_acceptance_e6q.py` (`1bd523d`, row
  #58), `rust/tests/acceptance_schema.py` (`91242c2`);
  `rust/cargo-sensorium/tests/convert.rs` (`4b98c3f`, row #56),
  `convert/chains/tests.rs` → `tests_terminals.rs` (`9bd2647`);
  `src/sensorium/record/tracer.py` 1193 → 672 + `tracer_frames.py` +
  `tracer_exc.py` (`e87996e`); `src/sensorium/query/refocus_world.py`
  (`f350b9c`, row #55). Four more went over 780 under this slice's own edits
  and were split at their banners under **R9** (`bb6b2c4` and the commits
  above; design amendment A2). Seventeen in all, every one a pure move,
  proved by `--color-moved=zebra` and equal collection counts, with the
  pointers seven documents carried repointed at `b6e2125`.
- **One sha256** (row #13, ruling R3) at `a0580d3`. `sensorium-rt` — the leaf
  with zero dependencies — owns it as `pub mod sha256` and the two copies are
  gone. **rt 0.4.1 / transform 0.4.4 / driver 0.5.3**, and the one observable
  consequence is a token: `RT_VERSION` is a literal held to the manifest by a
  unit test, so every Rust trace this runtime writes now says
  `recorder: sensorium-rt 0.4.1`. Three corpus expectations, one E9
  cross-check and the living docs moved with it, each re-pinned **by value**.
  The vectors the consolidation dropped came back at `bde3a66`.
- **The E4″ instrument's five gaps** (rows #1–#5, ruling R5) at `962cacd`,
  with a dated *Closed at* paragraph per gap in the record's findings sibling
  (`8c4dde1`) and the renderer's own absent-cell fix at `b0c3720`. No
  published number is re-derived and no `results.json` is re-assembled: every
  fix changes what the NEXT run publishes and is pinned by a unit test on
  synthetic records. Both schema tokens moved with the shapes their
  assemblers publish — **`e4pp/2`** and **`e9/2`**, raw and assembly together
  so a fresh run's two tokens agree; `e4/1` is untouched.
- **The instruments' own honesty** — `ENV_RECORDER_OWN` anchored on its clause
  rather than the line (#8, `04d0243`); the E4″ runner's seven minors (#9,
  `862ffa0`); the E4′ lock test diffing the whole pre-amendment range (#12,
  `32aab32`, measured discriminating on one moved byte); `line_rows_per_run`
  reading the census that counted it (#17, `3e1dac9`); one manifest reader for
  rung 2 and rung 3, the workaround deleted (#22, `05148e8`); the e6q runner's
  falsified expectation swept (#25, `a3b29b7`); `render_grain`'s three
  literals derived (#32) and the grain box-path scan walking the directory
  (#33, both `a3b29b7`, both measured discriminating); the grain reader's
  `RAISED_INV` regex BUILT from the line the tool prints (`aefb7ca`).
- **Eight printed sentences, each through the corpus gate WITH the driver**
  (ruling R6): the session clause in the withheld pair's fact (#6) and
  `is_relocation_note` → `is_env_rule_note` (#7) at `fc72550`; `focus: -` for
  an absent key and `focus: none` for a recorded empty one (#14, `36a6f5f`);
  the `HONESTY.md` citation the tool prints (#18), the born-outside claim
  qualified (#28), the invocation header's noun (#30) and the panics line's
  unit (#31) at `edc2bce` with `6490a14`; a typed lookup failure, a
  language-free `diff --task` help line, the `or "?"` fixture and "modulo
  location" on the all-in-tasks branch (#27, #36, #37, #51) at `0d685ad`; the
  MATCH that says it is not a statement about the schedule (#20) at `13475a2`
  with `245dee4`.
- **The corpus and the driver seam** — one driver resolution under
  `src/sensorium/` (#19), the `run:` line keyed and pinned (#21/#43), and
  `corpus/rust/abort` cleaning its core file (#45) at `a9a5ed1`; the spawned
  case recording deterministically and pinning its marked ROOT (#10) at
  `7d9dc9c`. 63 cases, 141 questions.
- **The crate-side rows** — `expr_attrs`' loud fallthrough (#16, `bb0bb29`);
  five private intra-doc links, so `RUSTDOCFLAGS="-D warnings" cargo doc`
  passes (#24, `059ac7b`); malformed-metadata fixtures (#38, `d836a77`); the
  `mint()` test that reddens and one run-id mix for both minters (#39/#42,
  `74d5fbb`); the panic path pinned by wire number and the orphan panic's
  serial (#40/#41, `852a0f5`); the WARN that counts test binaries apart from
  doctest processes (#46, `9c82fde`); `convert_perf` named for its bound (#47,
  `6abcc27`); goldens for fns nested in const, static and trait-const
  initialisers (#50/#52, `d17eb20`); the refused crate root on the wrapper
  path (#53, `017a4a1`); self-removing scratch directories (#54, `1530f68`);
  and the tid-mask justification written into the suite (#44 nit 2,
  `91f737d`).
- **A repo-wide ceiling gate** (ruling R1) at `e531200`: `tests/test_ceiling.py`
  holds every tracked `.py`/`.rs`/`.sh`, the README, `docs/*.md` and
  `rust/*.md` under 800 lines, and exempts the three record directories
  under `docs/superpowers/` **by name** — dated history, some byte-locked, amended by
  appended notes and never restructured. Both mutations were measured (the
  limit lowered: 37 files fail; a fourth exemption: the tuple check fails).
  That ruling closes two ledger rows without a line of code — the parent spec
  at 1458 (**#59**, struck) and the repair acceptance record at 795 (**#60**,
  which took a dated **continuation** rather than a strike: its README half
  was taken 2026-09-06 and only its record half closes here) — because
  neither is owed a split. `b498caa`'s message lists #60 among the struck
  rows; that message stands as written, and this is the correction.
  **A second message needs one.** `d261a52`'s body says "every file this
  commit's slice touched is under it" — under the gate. It was not true
  when it was written: the gate's patterns were `*.py`, `*.rs`, `*.sh`,
  `README.md`, `docs/*.md` and `rust/*.md`, and that commit also touched
  `CHANGELOG.md` and three files under `docs/superpowers/specs/`, none of
  which any pattern reached — the specs by the exemption, the changelog by
  omission. That message stands as written too, and this is its correction.
  The final fix wave then made the sentence true for the changelog by
  widening the gate to `*.md` whole; the three spec files stay exempt, which
  is R1's own ruling and not an oversight.
- **The stale root-disk driver deleted** (#15, ruling R7): 6 916 896 bytes, a
  2026-09-04 build of ours, untracked, on the near-full root disk while the
  box builds on the second one. Nothing to commit — the deletion is recorded
  here and struck where it was raised.
- **Two blind spots declared** in the ledger that is supposed to carry them:
  `rust/HONESTY-BLIND-SPOTS.md` **item 30**, the by-value hand-off that
  reaches a sink with no open chain (design R16 (v), the ledger half of #28),
  and **item 31**, a spawn in an expression position the container visitors
  skip (the A half of #49; rewriting those positions stays C). Both were
  named in an earlier ledger and in no blind-spot entry.
- **A design's stale example, corrected beside itself** (row **#34**, taken by
  this slice's ledger commit). `2026-09-05-sensorium-rung4-entry-grain-design.md`
  §5 still spelled the continuation note `... 1 more shape; continue with: …`,
  which ruling R-G7 replaced: `fmt.more_note` prints `... N more; continue
  with: <hint>` and carries no "shape" word. The stale text stays and the
  dated amendment sits beside it, which is how every other amendment in that
  document is made — a design two measurements were pre-registered against is
  evidence, not a description.
- **Five dated notes** (ruling R8), each struck where it was raised, because a
  note is the only thing that closes them: **#62** the golden comment naming
  `lines.rs`'s `statement_deltas` (moved to `lines/facts.rs` at `b949129`;
  golden bytes are not edited for a comment); **#63** the golden carrying the
  pre-repair sentence (design B1, 2026-09-05, superseded R2's "only two
  provable uses"); **#64** the two E6‴-era 31-element sets (the question no
  longer needs answering — E-flip settled the method and the repair has since
  been measured twice); **#65** `paging.rs:673`'s collapse (stands as read;
  the record's own §5.2 is the evidence); **#66** the grain records
  (both predate `schema_version`, and a later re-derivation is a NEW
  derivation).
- **What #66's note costs, measured rather than asserted.** Re-rendering both
  committed grain `results.json` with the base renderer and with this slice's
  gives **three** differing lines, all in §2, none in §3: in
  `…rung4-entry-grain.md`'s byte-lock paragraph the trailing
  `` (`original_lock` = None) `` clause is gone; in
  `…rung4-entry-grain-repair.md`'s first paragraph the raw file's name reads
  `results-grain-repair-raw.json` where the published text says
  `results-grain-raw.json`; and in that record's byte-lock paragraph the
  sentence "§1 was committed ALONE and never amended: there is no second sha
  (`original_lock` = 9bf64df)" is replaced by the amended-lock sentence
  carrying both shas and the amendment's byte count. **Two of the three are
  #32 removing a published falsehood** — the repair record's own §5.7 struck
  both by hand in its prose. The records are locked and are NOT edited.
- **Seven strikes for work that shipped in earlier slices** (X): the CI
  refusal gate (#67); `scenario.rs` split to `src/bin/scenario/` (#68); Task
  8's `[exit <cargo_exit>]` suffix (#69); `Report`/`TraceSummary` kept by
  decision (#70); the `--workspace` E6 arm with no `--lib`, closed by E6⁗-WS
  (#71); the design's §3/N6 examples (#72); and the four transform/driver
  files split at `91df4a3`, `853271a`, `b949129` and `03a68d3` (#73). None
  was open; each stood unstruck only because nothing came back to close it.
- **Three deviations and two amendments, dated in the design.** Task 1 landed
  three splits under names the seam map spells rather than the design's table
  (`test_exceptions_synthetic.py`, `test_tracer_serials.py`,
  `acceptance_schema_e5prime.py`), each because the design's name would send a
  reader to the wrong file; Task 6 split four files this slice's own edits
  took past 780 — two of them R9 names by path, two of them R9 reaches by
  its rule and not by its list. Both are appended to the design as A1 and A2,
  and the two-of-four correction as **A3** (the final fix wave).
  One deliberate non-re-export rides with
  them: `tracer.py`'s `_SENSORIUM_DIR` is **not** re-exported, so a test that
  patches it on the wrong module meets a loud `AttributeError` rather than a
  silently ineffective patch.

### Deferred, with rulings

- **The C list is untouched: 43 rows at the inventory, not funded this slice,
  and every one of them is the next conversation with Brice** — 44 as it
  stands, the final fix wave's review having added **C117** rather than
  ruling on it. They are restated in one line
  each below so the list can be read without opening three volumes; the
  numbers are the design's own (§2), and each row is still live where it was
  raised. **C74** `--window` for Rust (refused at exit 2). **C75** refocus
  over a multi-process invocation. **C76** the autoref ladder commits an open
  inference variable to `Debug`. **C77** no per-site volume cap — no measured
  cost to size one against. **C78** closure and `async fn` bodies get no
  probes. **C79** place writes and `&mut` mutation are not deltas. **C80**
  CALL rows carry no arguments on a Rust trace. **C81** `flow --object` on a
  Rust trace stays REFUSED. **C82** the cost residual needs a different
  instrument. **C83** Python traces print one block per raise (N7) — it needs
  the per-disposition site defined. **C84** the in-source acknowledgment
  marker (N8), decided and unbuilt. **C85** the rung-5 lever: record which env
  vars were READ; both recorders change. **C86** H4′'s verdict, gate reading
  against strict. **C87** `focus_matched` can carry a STALE unit's match.
  **C88** `tasks:`/"task stream", ruled left alone. **C89** the zero-candidate
  refusal under a pid cycle, ruled left as is. **C90** a key on one side only
  whose whole value was our fragment still withholds. **C91**
  `--bench --require-driver` is inert, ruled left as is. **C92** the two build
  caches on the second disk are Brice's to free. **C93** the composite-loop
  residual. **C94** the uppercase-initial heuristic. **C95** the suite's skip
  count depends on one variable. **C96** `last` is mtime-ordered. **C97** the
  digest floor is 16 hex characters. **C98** the discriminator's second
  condition has no subject on `cargo test` material. **C99** a `chain.holder`
  field on the wire. **C100** the nested-literal gap (blind spot 23 (a)).
  **C101** E2″'s numerator is `(file, line)`-deduped. **C102** three classes a
  reader may reasonably contest. **C103** four of the eleven flipped arms were
  never executed. **C104** two rows §1 asks for are ABSENT, not zero. **C105**
  the side-channel residual (blind spot 23 (d)). **C106** `.await`/`?`
  wrapping a dropped call is not recognised. **C107** an origin-keyed
  collision prints no file. **C108** the shape key reads masked prose.
  **C109** `.is_err()`/`.is_ok()` as OBSERVATION tags. **C110** an
  `.unwrap()`/`.expect()` probe, re-opened on the first target with panics.
  **C111** whether rustdoc joins the gate set (the repair half is taken).
  **C112** a 0-byte spool costs the whole invocation's conversion. **C113**
  rewriting spawns in expression positions (the declaration half is taken).
  **C114** no unit tests on the acceptance instruments. **C115**
  `refocus --window QUALNAME` reads as a size/range. **C116** the Python
  `live_threads` line's pre-existing asymmetry. **C117** (added by the final
  fix wave's review, so the list is 44) — `assess` (`refocus_cmd.py:495-504`)
  comments that a withheld licence's one exception is "about NAMES rather
  than about standing", but on the `not names` branch what is retained is
  the whole `N compared and unchanged…` sentence, and ruling R6 extended it
  to the session clause: the retained fact now carries standing as well as
  names. Either the comment is narrowed to what the branch keeps or the
  branch is narrowed to what the comment promises, and which of the two is a
  design question about what a withheld licence may still assert — the C
  conversation's, not a rewording.
- **Function lengths are C, not A** — **C48** by its inventory number, the
  one A row this slice re-bucketed (**ruling R4**): six converter functions
  of 88–274 lines (`frames::process`, `convert_one`, `wrapper::instrument`,
  `driver::go`, `convert_dir`, `write_proc_header`). Splitting the converter's
  core is behaviour-risk work with no failing test behind it, and it goes to
  the C conversation as a refactor needing its own review. It is the largest
  row this slice declined, and it is declined on purpose.
- ~~**Three A rows were not taken, and none of them is mechanical from here.**
  **#11**, the three residues of the splits, is now **four**: the two
  `refocus_cmd.py` "two files" re-export comments, a third the
  `refocus_world.py` split added at `f350b9c`, and `rust/HONESTY-REFOCUS.md`'s
  bare `---`. The comments are `src/`, which the ledger task may not touch.
  **#23**, three `chain.terminal` conformance vectors (`panicked`,
  `left_thread`, `handled_then_failed`), needs the vectors AND the reader's
  vector test in one commit — `docs/trace-format/vectors/` plus `tests/`.
  **#29**, the §11 sweep N1 left unfinished, is four items of which two are a
  vector and a test (`v18`'s prose assertion, `test_honesty_prose` pinning §11
  whole); taking only the `HONESTY-INDEX.md` row and the `JoinHandle` gloss
  would leave the row half-open with no gain. All three want one task with
  both file scopes.~~ — **Taken 2026-09-08 by the final fix wave**, which is
  the one task with both file scopes this bullet said they wanted. **#11**:
  the file count is gone from all eight sites of the re-export idiom
  (`refocus_cmd.py` ×2, `refocus_world.py`, `refocus_threads.py`,
  `diff_cmd.py`, `diff_notes.py`, `tracer.py`, `tracer_frames.py`) — the
  ruling was to drop the number rather than reconcile five different ones —
  and `rust/HONESTY-REFOCUS.md`'s bare `---` is dropped, the heading below it
  already saying what it silently marked. **#23**:
  `v20-exceptions-rust-panicked`, `v21-exceptions-rust-left-thread` and
  `v22-exceptions-rust-handled-then-failed`, built by `tests/vectors.py` from
  hand-written JSON like every vector before them and run by
  `tests/test_vectors.py` against the real CLI; each was mutated (its
  `terminal` set to a value the rules do not know) and each reddened.
  **#29**: the `HONESTY-INDEX.md` §11 row states the post-N1 definition, §11's
  `JoinHandle` bullet carries the per-thread gloss and points at blind spot
  25, `v18`'s `asserts` says that the sentence its question pins IS the
  ledger's own (`ESCAPED_DETAIL`, held to §11 by `tests/test_honesty_prose.py`)
  rather than a paraphrase of it, and that test now reads the SWALLOWED bullet
  instead of the whole section.
- **Partly taken, with what stands named.** **#26**: six of ten closed at
  `ae58c54`; the four that stand are crate code and crate unit tests — the
  side-effecting `visit_stmt` guard, no receiver-position dropped-call row,
  `close_frame` computing `preferred` on every outcome, no CALLEE-walk row.
  **#35**: two of six closed at `eba4db1`; the four that stand are
  `_at`/`_hops_line` as unnamed cross-module API, `group_chains` rendering
  before clipping, `resolve_invocation`'s unclosed `Trace` handles, and the
  Python-path pin asserting substrings rather than a whole answer — for the
  last, the two options are (a) a whole-answer golden, which is what N7's
  "byte-identical to 0.8.1" literally asks for and which reddens on any
  Python-side wording change, or (b) leave it and record that N7 is pinned by
  shape, not by bytes; (a) belongs in the same commit as the next Python-side
  wording change. **#44**: **one of eleven taken** — nit 2, the tid-mask
  justification, at `91f737d` — and **ten reported**, which is what the inbox
  marks item by item: two are **not present at HEAD** (the `SITE_*` consts;
  the `Fixed`/`CapWriter` duplication as stated), one is **obsolete** (the
  `"$RUN2" in str(spec)` scan, which now reads `q["command"]` with the comment
  the nit asked for), four are **out of the taking task's file scope** (the
  runner's pair-count naming, the `_sub` docstring, `gen.py`'s unused
  encoders, `trace._c` access from a Python helper), two are **more than a
  line** (two rt tests with no demonstrated mutation — and the review that
  filed it named neither test, so its subject is not decidable from the
  source; `mechanics.sh`'s dependency-proxy shape, which lands on top of a
  split that file still owes), and one — `cargo_driver()`'s caching — is
  **both** out of scope and more than a line. 1 + 10 = 11.
- **Two fences this slice states rather than pins.** The `expr_attrs`
  catch-all's `&[]` is a **documented known-surviving mutant**: no `syn`
  variant reaches the arm today, so no test can distinguish its return value
  from any other — the counter and the printed line are what make it
  observable at all. And `"spawn@" in name` is a **measured equivalent
  mutant**: no task name either recorder can mint distinguishes it from the
  shipped predicate, so the honest form left open is a unit test over a
  hand-built name, declared as an unreachable input.
- **The minors this slice's own reviews raised**, none blocking, each one line:
  `tests/test_acceptance_e9_read.py:221` hard-codes `sensorium-rt 0.4.1` and
  will need moving on every rt bump (a derivation from `spool.rs`'s
  `RT_VERSION` is the honest fix); `src/sensorium/capture.py:52` points at a
  `tracer.py` line number the split aged; `tracer.py`'s docstring states
  `_ExcRefs`' contract two files away; the renamed driver-rule test's
  docstring sits where the rename left it; ~~`refocus_threads.py`'s "four
  files" reads against the re-export idiom's "two files" (row #11's
  neighbourhood)~~ — **taken by the final fix wave**, which dropped the count
  from all eight sites of the idiom rather than reconciling them;
  the process-global `UNENUMERATED_EXPRS` counter is asserted by delta rather
  than by value; `#46`'s doctest exclusion is inline in `convert_dir` rather
  than factored; `pub(super) text` is unused across the chains seam; and
  `render_e4pp`'s walls table renders arms A/B/C only, while the record now
  also carries `dry`, `driver_build` and `cargo_s` — **and, added by the
  final fix wave's review, `render_e4pp.py:399-402` still prints an ABSENT
  wall as `None s`**: `(walls.get(a) or {}).get('first_focus')` is `None`
  when the arm recorded no wall, and the f-string renders it beside the
  unit, so a cell that was never measured reads like a measured zero-ish
  number. That is the same class the H8 fix removed from the presence
  reader this slice, one renderer along. Carried, not fixed: it is an
  instrument, no published number turns on it, and the honest repair is
  the same `null`-with-a-reason shape H8 now uses — next slice.
- ~~**The ceiling gate does not yet cover `CHANGELOG.md`** (**796** after this
  slice's entry). The gate's patterns are `*.py`, `*.rs`, `*.sh`, `README.md`,
  `docs/*.md` and `rust/*.md`, so a root-level changelog is outside them and
  the next release entry crosses 800 with nothing red. *The fix*: **the final
  fix wave widens it**, and the next `CHANGELOG.md` change moves the pre-0.8
  entries to a dated archive volume first — the same rule this ledger keeps
  for itself. Recorded rather than taken here because widening what the gate
  covers is a ruling, and Task 5's own docstring says a file the gate names is
  a split to take, never an exemption to add.~~ — **Taken 2026-09-08 by the
  final fix wave, both halves and in that order.** The archive came first: the
  `0.7.0` and `0.6.0` entries moved to `CHANGELOG-ARCHIVE.md` as a pure move
  under a dated volume header in `CARRIED-DEBT-ARCHIVE-2`'s shape, with a
  pointer line at the foot of `CHANGELOG.md`; `tests/test_release_tokens.py`
  reads the NEWEST header only and is unaffected, which was checked and not
  assumed. Then the gate widened to **`*.md` minus the three exemptions**
  rather than to three more named patterns — the class, not the three files
  that happened to be missing. The enumeration gains exactly
  `CHANGELOG.md`, `CHANGELOG-ARCHIVE.md`, `ORIGIN.md` and
  `corpus/rust/README.md`; **nothing it newly covers is over 800**, and
  `tests/test_ceiling.py` names the four so a narrowed `PATTERNS` reddens.
- **Files near the ceiling, named rather than split** (rulings R2/R9 — none of
  them was edited past 780 by this slice). **Re-measured 2026-09-08 by the
  final fix wave**, after the changelog cut and under the WIDENED patterns, so
  the list below is the gate's own scope and not the narrower one the earlier
  reading used:

  ```
  git ls-files -- '*.py' '*.rs' '*.sh' '*.md' \
    | grep -v -E '^docs/superpowers/(acceptance|plans|specs)/' \
    | xargs wc -l | awk '$1>=750 && $2!="total"' | sort -rn
  ```

  `rust/tests/mechanics.sh` **795** (row #57, and an E7 second-column check
  waits on the split); `tests/test_runs_info.py` **790** (seam: its
  `# -- Ruling 7` banner at `:476` → `test_runs_info_rust.py`);
  `rust/tests/acceptance_e9_phases.py` **788**;
  `rust/sensorium-transform/tests/golden.rs` **788**;
  `rust/sensorium-transform/tests/edges.rs` **784**; `CHANGELOG.md` **780** —
  new to this list, because it is new to the gate, and 780 is what it reads
  AFTER the pre-0.8 entries moved to `CHANGELOG-ARCHIVE.md` (it was 798, two
  lines from the ceiling, with nothing red);
  `rust/cargo-sensorium/src/convert/mod.rs` **777**;
  `tests/test_refocus_licence.py`
  **772**; `rust/HONESTY-BLIND-SPOTS.md` **772** after this slice's two items —
  the next item added to it splits it first, and the seam is the one the index
  already uses, a rung's items moving to a file it links;
  `tests/test_flow_identity.py` **770**; `src/sensorium/record/boot.py` **768**;
  `rust/cargo-sensorium/tests/convert_meta.rs` **758** (**no seam named yet** —
  the file carries no banner, and choosing one is the next toucher's call);
  `tests/refocus_programs.py` **755** (seam: its `# -- asyncio` banner at
  `:591`); `rust/cargo-sensorium/src/mirror.rs` **753** (seam: `mod tests` at
  `:329` → `mirror/tests.rs`, the house pattern); `rust/sensorium-rt/src/spool.rs`
  **752**; `docs/TRACE-FORMAT.md` **752** (seam: a numbered section moves to a
  file it links, as `rust/HONESTY.md` §1, §8, §11 and §13 did — §5's
  enumerations at `:476` are the largest); and `tests/test_capture.py` **750**,
  which the previous reading of this list omitted at exactly the floor it
  declares. Seventeen files, floor 750, and it is a measurement rather than a
  recollection — the command is above, so the next reader re-runs it instead of
  trusting this paragraph. `tests/test_ceiling.py` fails on any of them
  crossing 800, which is the difference between this list and the six that came
  before it.

### Process lessons

- **A ledger row's fix is not always inside its taker's file scope, and the
  ledger did not say so.** Four of `#44`'s eleven nits, four of `#26`'s ten,
  four of `#35`'s six and all of `#11`, `#23` and `#29` were declined for
  exactly one reason: the fix spans files the task owning the row may not
  touch. The rows were bucketed as "mechanical, fundable now" by reading the
  FIX, never the file list. A row's bucket should be a function of both.
- **A nit filed without naming its subject cannot be taken.** `#44`'s "two
  `sensorium-rt` tests with no single-line mutation demonstrated" names no
  test, and no reading of the source recovers which two the reviewer meant.
  It survived three slices as an open row that no one could have closed. A
  deferred minor names its subject or it is not a minor, it is a mood.
- **A pure refactor moved a token every trace carries.** Consolidating
  `sha256.rs` into the leaf crate is behaviour-free by construction — and
  `sensorium-rt`'s version literal is held to its manifest by a unit test, so
  the refactor bumped `RT_VERSION` and changed `recorder: sensorium-rt 0.4.1`
  in every Rust trace, three corpus expectations and an E9 cross-check with
  it. "No behaviour change" is a claim about the program; a version token is
  an observation about the recorder, and they are not the same claim.
- **The change one task makes to a printed sentence breaks a reader another
  task owns, and the suite stays green.** `#30` renamed the invocation
  header's noun; the grain runner's `RAISED_INV` regex reads that line, and
  its tests feed it SYNTHETIC text still carrying the old noun — so the break
  was latent and only a future grain RUN would have met it. The repair is the
  general rule: a reader that names another component's output BUILDS the
  expected line from that component, and never retypes it.
- **An instrument printed an absent cell as a value, in the fix round for a
  row about exactly that.** The renderer appended "The named case matched as
  `None`" over a record derived before the key existed — a measured-looking
  sentence about a measurement nobody made, which is `#1`'s own bug class one
  level up. Absent, matched and missed are three states, and a renderer that
  collapses the first two is the failure this slice spent a task removing.

## 2026-09-09 — S5 rung 1, the TypeScript recorder (Python 0.9.0 / sensorium-ts 0.1.0)

The first slice of a third recorder, and the first to ship **DONE-WITH-STOP**
on a clause of its own contamination endpoint. Forty-two controller rulings
(`rulings.md`, R1–R35 plus the lettered amendments) and eleven plan decisions
(P1–P11); every one of them is now a dated row in §14 of
`docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md`,
which is where a reader goes for what the design said before it moved.

### Settled

- **The recorder.** `sensorium-ts 0.1.0` — a transform whose edits never
  contain a newline (goldens assert `lines(out) == lines(in)` on every one), a
  runtime on `AsyncLocalStorage` importing `node:` builtins only, a vitest
  plugin, a `node --test` loader hook, a setup-file template the driver fills
  under `<root>/node_modules/.sensorium/` (P5) — with `sensorium ts run` and
  `sensorium ts ingest` in Python, so reading a trace needs no Node (D1, P10).
- **The reader's third vocabulary.** A `TYPESCRIPT` column in `vocab.py`, the
  unknown-`lang` refusal at one choke point in `db.open_trace` (P3),
  `info_typescript.py`, a `runs` header gated on `meta.lang` and not on a key
  (R27), the command as typed in `harness_command` (R26), the container's own
  exit kept as `exit_self_reported` beside an `exit_status` that stays
  `unwitnessed` (R21). Seven vectors `v23`–`v29`; thirteen corpus cases under
  one vitest project (P9); a `typescript` CI job pinned to the acceptance
  lens's own vitest 4.1.9 and vite 6.4.3 (R18).
- **Two reader defects this recorder was the first able to produce, fixed for
  all three languages** (R28, R28a). A NULL `line` printed `LNone` — a value
  that looks like a line and is not — in `tree`'s state tail, in `frame`'s
  timeline and in `fmt.fmt_event` for every event kind. Python and Rust output
  is byte-unchanged, because neither can produce a NULL-line event; this
  recorder's suspended frames and YIELD/RESUME rows can.
- **The acceptance, measured on somebody else's suite** and byte-locked before
  the code existed: twelve endpoints and two controls, ten PASS plus both
  controls, **E6′ a STOP**, **E10 REPORTED**. `docs/superpowers/acceptance/
  2026-09-09-sensorium-s5-rung1.md`; the doc pass amended two sentences of it
  in place (§4's endpoint count, which had read E10's REPORTED as a PASS; §5
  gap 8's quoted frames, which carried this box's worktree name), and touched
  neither §1, §2 nor §3.
- **The 800-line ceiling, paid four times before it was hit** (R20, R25,
  R35). `typescript/test/rt.test.mjs` split at 802 during Task 4 (**R20**);
  `docs/TRACE-FORMAT.md` given only what **R25** allowed — five additions that
  took it 752 → **799** in Task 7 — with the TypeScript meta-key table going
  to `docs/trace-format/TYPESCRIPT-KEYS.md` instead, and no further edit in
  the doc pass (**R35**); and in the doc pass itself two pure moves,
  `CHANGELOG.md`'s three oldest entries (`0.8.2`, `0.8.1`, `0.8.0`) to
  `CHANGELOG-ARCHIVE.md` and the README's `## Corpus` roll-call to
  `docs/corpus.md`. Four payments, four items — and a fifth, this file's own
  volume 4, narrated in the header above rather than here.
- **The versions.** Python `0.9.0` (declared, and the editable installs in all
  three venvs reinstalled with it, because `test_release_tokens.py` reads
  `importlib.metadata` and not only the file); `sensorium-ts` stays `0.1.0`,
  held to `src/index.mjs`'s `VERSION` by a unit test (R15), so a trace says
  `recorder: sensorium-ts 0.1.0`. `sensorium --help`'s top-level description
  stops saying "a Python program".
- **Nine deferred minors that were parked FOR this doc pass, taken here.** The
  record's endpoint count and its worktree-named frames (*Task 10*); the
  `#k`-scope sentence in `HONESTY.md` §2, which said "of one registration"
  where R17 rules per NAME (*Task 4, ruling R17*); the unsatisfiable "a 10 kB
  string is 200 bytes with `trunc`" cap example (*Task 3*); the four
  options-second shapes `canMoveOptions` used to refuse, now stated as refused
  by nothing (*Task 2, ruling R8c*); §7's `.d.ts`/`node_modules` exclusion
  wording (*ruling R7*); §7's `excluded:` example, now per reason with counts
  (*ruling R27*); the untraced-caller wording in the spec's §4 and the ledger
  (*ruling R29*); `stdin: false`, missing from the declared-absent list
  (*Task 1*); and the driver's empty-`node_modules` behaviour, documented in
  `typescript/README.md` (*Task 6*). *(A tenth self-healed: `typescript/
  README.md` described modules that did not exist when it was written, and
  they exist now — Task 1's note said it would.)*

### Deferred, with rulings

**The two next-slice commitments, written as commitments.**

- **E6″ — a NEW pre-registration, not a second look at E6′** (*ruling R32*).
  E6′ STOPped on its plain-band clause: a plain-after wall of **22.8678 s**
  against the plain arm's own min–max band **[22.3136, 22.7221]**, 0.1457 s
  (0.65%) above it, while its manifest, marker and wrapper clauses held
  exactly. The number stands as measured — nothing re-rolled, no band moved,
  no verdict renamed — and E6″ commits, before its instrument exists, to four
  things the record's §5 gaps 5 and 6 name: (a) `e6.sh` gains the **load
  guard** every timed arm of E1′ already had, reading `/proc/loadavg` before
  every run and writing the reading into the artifact; (b) the band is
  **derived, not chosen** — the plain arm's own median ± the spread the plain
  arm measured, rather than a five-run min–max, which is a range with no slack
  by construction; (c) the comparison is **medians over n=5** plain-after
  runs, not a single wall against a range; (d) the manifest is verified
  **after** its own plain run, not before it, so the instrument audits the
  last thing that touched the lens.
- **The E10 design question — a Node converter on `node:sqlite`, or a binary
  wire** (*ruling R33*). Full-suite `ingest` costs **45.5293 s** (n=3) against
  a plain wall of 22.5925 s — ×2.02, above E10's bound, which its own rule
  made design input and not a STOP. The commitment is to answer it the way the
  spike was answered: **pre-registered**, with the endpoint written before the
  instrument, and on both workloads — the full suite AND the one file a
  debugging loop actually pays for (**0.3638 s**, n=3), because a converter
  rewritten for the suite number could easily be no better on the one that
  matters. The second reading of the same effect is in the record's §5 gap 13:
  the call arm's driver wall climbed 45.0 → 70.3 s run to run while its
  harness wall never moved.

**A finding about the consumer, which the pre-registration committed to
reading as one.**

- **Eight of the lens's 372 test files record differently on two runs of the
  same suite** (2.2%), named in the acceptance record's §3.4. Spec §8 asked
  for the count without a gate and pre-committed to reading a non-zero as a
  fact about the consumer; the comparator refused nothing and mis-called
  nothing, and the file E3-TS recorded twenty times identically is not among
  them. Nothing is owed here by this recorder. It is carried because it is the
  first thing this tool has told somebody about their own suite that they did
  not ask it, and the next consumer-facing slice should decide whether that is
  a thing `sensorium runs` should offer to compute.

**Deferred by ruling — design-level, each waiting on a rung.**

- **Argument capture** (`locals: false`, D12) and **per-line state**
  (`line: false`) arrive with `--focus` in rung 3, measured. Every CALL carries
  `unread: ["locals"]` and `watch`/`flow` refuse at exit 3 meanwhile: a stated
  absence, not an empty list.
- **The `exceptions` disposition rules** are rung 2 (D15). RAISE and HANDLED
  rows exist and `capabilities.err_flow` is **false**, so `exceptions` refuses
  a 0.1.0 trace at exit 3 — and **will keep refusing it after rung 2 lands**,
  because what it lacks is a record and not a rule. Re-recording is the fix;
  the cost was pre-committed, not discovered.
- **`scheduled_by`** — which frame scheduled a continuation — is recorded by
  nothing (D5). Depth 0 inside the right task with `caller: "untraced"` is the
  whole of the claim.
- **The untraced-caller tag is a READER feature for all three languages**
  (*ruling R29*), not a TypeScript one: `caller: "untraced"` is on the wire
  here and on the Python wire, and the reader has never rendered either. A
  slice that adds it changes Python and Rust output too, which is why it is
  not folded into a TypeScript rung.
- **A transform cache keyed on source sha** is explicitly NOT rung-1 work:
  E1′'s `off/plain` **1.0587** is inside the 1.10 bound its rule set, so the
  cache stays §11 item 6 until a lens says otherwise.
- **jest** is refused by name (D10). A jest consumer is a future slice with
  its own spike; the refusal says so rather than guessing.
- **`.concurrent` naming cannot be cross-checked** (ledger blind spot 5).
  vitest's `expect` state is global, so a `.concurrent.each` name that is
  wrong is countable and not catchable. E9 measured `task_name_conflicts` **0**
  and tasks = `tests_seen` = 4,278, which is evidence about the shapes the
  check reaches and none at all about the one it does not.
- **The `describe`-chain / `.each` naming hazard under `node --test`**: an
  `async describe` callback registers after the lexical chain pops (P11), so
  those tasks lose their chain where no provider runs. `task_name_basis` says
  which rule named the trace's tasks.
- **The recorder joins a describe chain with ` > ` and vitest's JSON reporter
  joins it with a space** (record §5 gap 10). E9's rule attaches no threshold
  to its 20-name sample, so this gates nothing; whether §3.4 should emit
  vitest's own `fullName` spelling is raised and unsettled.

**Deferred blind spots — each now in `typescript/HONESTY.md` §10 with a
falsifier, none of them silent.**

- **A class static block is neither instrumented nor counted** (blind spot
  12) — the one in-scope thing the transform declines that produces no
  `excluded` entry. It should count as `static-block`; a later slice adds it.
- **`for await` and top-level `await` mint no YIELD/RESUME** (blind spot 10):
  measured **0** occurrences in the acceptance lens, so no endpoint could have
  caught it.
- **A `.catch(function () {})` is not a sink; only the arrow spelling is**
  (blind spot 11). Which shapes are sinks is rung 2's question.
- **A destructuring `catch ({ code })` records `type: "undefined"`** (blind
  spot 13) — what the recorder knows about the value, not a claim that the
  program caught `undefined`.
- **Two shipped declarations are unfalsifiable as they stand** (blind spot
  15). R16's `rt.mjs`-external declaration reads the same at vitest 4.1.9 with
  it and without it, so it is insurance and is named as such; and
  `meta.test_files` is written by the converter and exercised by **no run** —
  0 traces carry it, and a `--pool=threads` probe produced none either, so
  `runs`' `files: N` line is code no recording has printed.
- **One reader fallback is unreachable and would print Python's word**
  (blind spot 16): `tree`'s unframed-kind line falls back to the contract's
  `generator`/`coroutine` spelling. Every TypeScript call is framed, so
  nothing reaches it.

**Files near the ceiling** — named here rather than discovered at 800, which
is the rule that produced volume 4, the CHANGELOG's third cut and
`docs/corpus.md` in this same slice.

- **`docs/TRACE-FORMAT.md` is at 799 of 800**, having reached it on this
  branch: Task 7 (`63a6af4`, `1abf67c`) took it 752 → 799 with exactly the
  five additions *ruling R25* allowed — the `lang` value, the `exc.kind`/`how`
  enumerations, the `runs` header sentence, the vocabulary column and a
  pointer — while the TypeScript meta-key table went to
  `docs/trace-format/TYPESCRIPT-KEYS.md` instead of into it. The **doc pass**
  then edited it no further (*ruling R35*), which is the clause that says
  "not edited" and the only one that does. The next thing that document needs
  splits it first, at a section seam. Everything else this slice touched
  has room: `CHANGELOG.md` 756, `README.md` 749, `docs/CARRIED-DEBT.md` 782,
  `typescript/HONESTY.md` 627. The two files over 800 —
  `docs/superpowers/specs/2026-09-09-…-design.md` at 901 and the acceptance
  record at 854 — are in the two directories `tests/test_ceiling.py` exempts
  BY NAME as dated history, and are amended by appended notes, never
  restructured.

**Deferred minors, by the task that raised them.** Each is a one-line fix or a
fixture; none changes a claim a trace makes, and each names its subject so a
later slice can close it (the ledger's own lesson of 2026-09-08: a nit with no
subject is a mood).

- *Task 0*: the record's §1 preamble says only headings changed, but the plan
  section's heading lost its inner backticks; the task report says the tsconfig
  carries "nine options" where it carries 8 plus `include`.
- *Task 1*: `HONESTY.md`'s "above everything else" ordering clause is
  unsourced; its opening paraphrases the 2026-08-20 ruling ("refusals" for
  "`exceptions` rules"); spec §7 item 8's "consumer's config" clause is filed
  under ledger §7 rather than §8. *(The same task's `stdin: false` omission
  was **taken** in this doc pass.)*
- *Task 2*: the golden count guard is `>= 13` with 16 present — pin the exact
  name set; unused destructures in the byte-exact test; the `node_modules`
  check reads the root-relative path only; no golden pins the task-boundary
  and expression-bodied-callback shared-offset ordering (verified correct by
  review, unpinned by a test); ~~`transformSource`'s JSDoc lacks `@throws` for
  R10a~~ *(struck 2026-09-09, ruling R44: stale when it was written -- the tag
  is on `transformSource` in `typescript/src/transform.mjs` and names R10a;
  no line number here, so this row cannot go stale a second way)*; a one-line
  tsconfig reformat.
- *Task 3*: the `off` test pre-creates the spool directory, so it cannot tell
  "no file" from "empty dir"; `run()` yields `recs: []` on a spool count ≠ 1
  instead of asserting.
- *Task 4*: three checks in `probes/check.mjs` lack failure detail (:257,
  :380, :417); its argv is positional-by-subtraction; module-level plugin
  tally singletons; `probes/hooktmp-*` temp roots are created inside the repo.
- *Task 5*: `_meta()` mutates builder state (`bases.pop`); the spool is
  materialised whole (memory linear in spool size — what E10 measures);
  `sanitize.py`'s substitution order is undocumented; the questions guard
  accepts `expect_exit` alone; `Builder(...)` is constructed outside
  `convert()`'s cleanup try, so a constructor failure leaks the reserved tmp
  file (a pre-existing shape).
- *Task 6*: the D9 exit-2 mapping in `driver.run` has no test; the wrapper
  filename rule is spelled twice; `js_regexp` double-escapes an
  already-escaped rt path (POSIX-theoretical); `check_node` checks PATH's node
  and not the command's; `wrapper.remove` rmdirs an empty `node_modules` it
  did not create; a lazy import cycle between `driver` and `cli`; `_consume`
  swallows a valueless flag. *(The empty-`node_modules` behaviour was
  **documented** in `typescript/README.md` in this doc pass, as the task
  asked.)*
- *Task 7*: `info_cmd.run` is 215 lines — a pre-existing overage the
  TypeScript hook grew by six, whose split is its own slice because the output
  is byte-exact legacy; `_every_parser` reaches into argparse privates.
- *Task 8*: a stale `RUN_LINE` comment names two callers where there are now
  three; `NO_TS` respells the floor instead of interpolating `NODE_FLOOR`;
  `_report_json` takes `args` for one bool; the `node_modules` symlink writes
  `.sensorium/` into the live checkout during a recording (serial only);
  a task report quoted 3276 where the run reads 3278.
- *Task 10*: the split control gates on the exit code alone (the mechanism is
  stated verbatim in §3); `e0.py`'s docstring overstates its value;
  `assemble.py`'s `loads` list is not filtered the way `walls` is — a latent
  instrument misalignment, worth fixing before E6″ uses that assembler. The
  same task's third clause — the record's header still reading
  "pre-registration only" — is **closed by a dated note**, not carried: §3's
  opening paragraph supersedes the header in place and says why lines 1–97 are
  left byte-identical to `29c5059` instead of tidied.
- *`sensorium --version`*: still not a verb. The version came from installed
  metadata; the README does not claim one, so nothing is false — but a tool
  whose CHANGELOG names versions should probably answer for its own.

### Process lessons

- **A chunk MOVE carries the text between its ends.** R8a authorised
  relocating a test's callback to the end of the argument list; relocation in
  `magic-string` moves the intro and outro attached to that range, so an
  earlier splice inside the moved chunk travels with it and lands somewhere it
  does not belong. R8c withdrew the move and spliced **positionally** instead,
  which has the ordering guarantees the two-argument form already had — and
  the four shapes the move had to refuse became goldens that come out correct.
  A rewrite that reorders source text is a different kind of change from one
  that inserts into it, and should be reviewed as one.
- **A purely syntactic wrap rule needs a scope.** "Wrap the second argument of
  a `test`/`describe` call" is a rule about spelling, and ordinary source is
  full of that spelling — a local `describe(label, formula, value)` helper was
  being rewritten. Narrowing to inline callbacks fixed that hazard and made a
  new one (a real test file's `test('x', sharedFn)` got no task). The property
  that actually distinguishes them is **which file this is**, so R8 made the
  rule file-scoped, and R8b then had to exclude type-only imports from the
  test-file test. A syntactic rule with no scope is a rule about the wrong
  thing.
- **A guard keyed on node kind cannot cover an open set of splice
  interactions.** The reviewer's four refused shapes were each described as a
  kind (a multi-line options object, an options object holding a function, an
  awaited title, an expression-bodied callback) and `canMoveOptions` tested
  for exactly those. The property that matters is not the kind: it is **which
  insertions share an offset**, and how the splicer orders insertions at the
  same offset. Once the ordering was the rule (parents visited first, so the
  boundary insertions are outermost by construction), the enumeration of kinds
  was not needed at all and was deleted.
- **A pre-registered verdict vocabulary has no PARTIAL.** E6′'s rule is a flat
  conjunction of four clauses. Three held; one did not; the rule defines PASS
  and STOP and nothing between. Writing "PARTIAL" would have been inventing a
  verdict word after seeing the number — the same failure class as a needle
  aimed at a wording rather than at the thing. The STOP was taken, and where
  it landed (the one timing clause, not the three contamination clauses) was
  recorded as a fact about the STOP rather than as a reason to soften it.
- **An instrument that reads a load must write it.** `arms.sh` waited on
  `/proc/loadavg` before every timed run AND wrote each reading into the
  artifact, so "every run was under the refusal" is checkable. `e6.sh` did
  neither, and its one timed clause is where the rung's STOP fired — and the
  load at that moment is known only as an operator's by-hand reading at
  ~16:32, in no artifact, quoted in the record as exactly that and used as
  evidence for nothing (ruling R34). A number a reader cannot re-derive is not
  evidence, however true it is.
- **Measure the thing before sizing the cut.** R35 says cut the CHANGELOG
  before writing the entry, and the cut was taken first — but sized by
  guessing the entry's length. The file landed at **833** and a third entry
  had to follow. Cutting first was right; the missing step is drafting,
  measuring, then cutting. The README, measured the same way, went to 798 with
  two lines of headroom, and its `## Corpus` roll-call moved out for the same
  reason rather than being left at the edge.
- **A verdict count in prose drifts from the table above it.** The acceptance
  record's own §4 said "eleven of the twelve … PASS" while its table read
  REPORTED for E10 — a summary sentence written by hand over a table written
  from `results.json`. The table was right both times. A count in a summary is
  derived data and should be derived, or at minimum re-checked against the
  rows on the day the rows are final.
