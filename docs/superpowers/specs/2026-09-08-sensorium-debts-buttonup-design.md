# The queue, buttoned up — sensorium's carried debts, funded (A, B, D)

**Date:** 2026-09-08 · **Status:** design, approved in one message (Brice, 2026-09-08: "let's button up sensorium's queue before we continue adding" → "a, b, d first. we will talk about c after") · **Design authority:** Claude — every ruling below is Claude's, recorded here · **Base:** main `f14d2f6` (Python 0.8.6; driver 0.5.2 / transform 0.4.3 / rt 0.4.0) · **Branch:** `feat/debts-buttonup`

Four ledgers carry 116 open bullets (this doc's §2 is the inventory, swept at `f14d2f6`). Brice funded three buckets: **A** mechanical debts whose fix is already written (54), **B** files over the 800-line ceiling (11 code/test files), **D** items closable only by a dated note (5). **C** (43 design-level or ruled-not-funded items) is untouched and is the next conversation. **X** (7) were fixed in earlier slices and never struck — they get their strikes.

This slice measures nothing: no `src/` behaviour under a pre-registration changes. Every printed-sentence change runs the corpus gate WITH the driver; every split is a pure move proved by `git diff --color-moved=zebra` and equal test-collection counts; every new fence is mutation-tested on a committed tree.

## 0. Rulings (Claude, 2026-09-08)

| # | Question | Ruling | Cost if wrong |
|---|---|---|---|
| R1 | What the 800-line ceiling covers | **Code and living docs**: `src/`, `tests/`, `rust/` (crates, `rust/tests/`), `corpus/`, and top-level docs (README, `docs/*.md`, `rust/HONESTY*.md`). **Exempt as records**: `docs/superpowers/{acceptance,plans,specs}/` — they are dated history (some byte-locked) and are never edited after the fact except by appended amendments. The parent spec at 1458 and the entry-grain record at 825 therefore stay. A repo-wide gate `tests/test_ceiling.py` enforces exactly this scope, landing AFTER the splits (it fails on 10 files today). | a record grows past readability — accepted; records are read by section |
| R2 | The eleven over-ceiling code/test files | split as PURE MOVES at the seams the map names (§3), one commit per file, `programs.py` first, `tracer.py` last; near-ceiling files get their seam NAMED in CARRIED-DEBT, not split, unless this slice's own edits push them over | none — moves are proved byte-identical |
| R3 | `sha256.rs` in three crates | **`sensorium-rt` owns it** (the leaf with zero dependencies); `sensorium-transform` and `cargo-sensorium` take it from `sensorium_rt::sha256` (a build-time dependency on the runtime crate is harmless — the driver already embeds rt's sources). rt 0.4.0 → **0.4.1** (a new `pub mod`); transform → **0.4.4**; driver → **0.5.3** | the runtime crate's public surface grows by one module |
| R4 | Function lengths (inventory #48: six converter fns of 88–274 lines) | **Not this slice.** Splitting the converter's core is behaviour-risk work with no failing test behind it; it goes to the C conversation as "refactor, needs its own review" | the <50-line checklist stays unmet for six fns |
| R5 | The E4″ runner fixes (inventory #1–#5, #8, #9) | funded as INSTRUMENT changes with the measurement CLOSED: they may not re-derive any published number; the E4″ results file is not re-assembled; each fix is pinned by a unit test on synthetic records (the instrument's own test files), and the record's findings sibling gets a dated "closed at <commit>" line per gap | none to the record |
| R6 | Printed sentences (#14 `focus: -`, #18, #20, #28, #30, #31, #36, #51 and any wording a fix touches) | the corpus gate WITH the driver after each; a Rust case's expectation is updated only to what the tool now prints, never loosened | a sentence nobody checked — the gate exists for this |
| R7 | The stale `rust/target/release/cargo-sensorium` on the root disk (#15) | deleted (an untracked 2026-09-04 build of ours; the box builds on the second disk) | none |
| R8 | D items | one dated note each, in the ledger or the record's findings sibling, never inside a byte-locked §1 | none |
| R9 | The `mechanics.sh` seam (795) and the three near-ceiling instrument files | named, not split, unless a fix in this slice grows them; `acceptance_e4p_read.py` (787) and `acceptance_e4pp_phases.py` (761) are checked after Task 6's edits and split at their `# ----` banners if over 780 | none |

## 1. What ships

- Python **0.8.7**: `refocus_threads.py` (from `refocus_world.py`), `tracer_frames.py` + `tracer_exc.py` (from `tracer.py`), the session clause in the withheld fact, `is_relocation_note` renamed, the wording fixes (§2 A), a typed dispatch exception, one vocab fixture, `flow_programs.py` and seven test-file splits, `tests/test_ceiling.py`.
- Crates: rt **0.4.1** (`pub mod sha256`), transform **0.4.4** (uses rt's sha256; `expr_attrs` loud fallthrough; two intra-doc links; goldens/fixtures #50/#52), driver **0.5.3** (uses rt's sha256; WARN excludes doctests; the spool temp-dir guard; `convert.rs` → `convert_runner.rs`; `chains/tests.rs` → `tests_terminals.rs`; fixtures #38–#41, #53; the `runid` helper dedupe #42).
- Instruments under `rust/tests/`: the five E4″ gaps, `ENV_RECORDER_OWN` anchored, the seven minors, the E4′ lock-test full diff, `render_grain` literals derived, the grain scan walking the directory, `read_manifests` fixed at source, `line_rows_per_run` nulls, the e6q runner's stale docs.
- Corpus: `refocus_spawned_test_fn` pins the marked root; `abort` cleans its core file; `run_corpus._run_ids` keyed unambiguously (#21/#43 together); three `chain.terminal` conformance vectors.
- Ledgers: X strikes; D notes; blind spot for the expression-position spawn (#49) and R16 (v) (#28); INDEX §11 row; the design-spec continuation note (#34); CARRIED-DEBT's section for this slice; CHANGELOG 0.8.7; `TRACE_FORMAT` stays 4.

## 2. The inventory (swept at `f14d2f6`; ledger keys: CD = `docs/CARRIED-DEBT.md`, A2 = `docs/CARRIED-DEBT-ARCHIVE-2.md`, A1 = `docs/CARRIED-DEBT-ARCHIVE.md`, F = the E4″ findings sibling, IN = the rung-3 inbox §3)

### A — mechanical, fundable now (54)

| # | ledger:line | title | fix as stated | files | verified | notes |
|---|---|---|---|---|---|---|
| 1 | CD:336-346, F:15-51 | **H8's presence reader compares a bare case name against a prefixed listing** | "match on the listing's last path segment as well as the whole name; record `null` with `case_listing.command` + `rc` otherwise" | `acceptance_e4pp_phases.py`, `_cells.py` | unit | with 2-5 |
| 2 | F:53-62 | **The STOP's label is fixed per endpoint, not derived from what failed** | "name the STOP by what the failing cell measures … print both when they disagree" | `acceptance_e4pp.py`, `_schema.py` | unit | with 1,3,4,5 |
| 3 | F:64-86 | **`driver_version` is read on one side, and §1.5 reads as though it were two** | "read `meta.driver_version` from the copied original too, beside the rt-hash pair" | `acceptance_e4pp_phases.py:294` | unit | §1.5 names `meta.recorder`; reader takes `driver_version` |
| 4 | F:88-101 | **H2's fragment count was read on both sides and published on neither** | "lift both counts into `H2` as a `{value,n,lens,dropped}` cell and into `reported.rt_hashes.by_pair[*]`" | `acceptance_e4pp_cells.py`, `_schema.py` | unit | already read |
| 5 | F:103-116 | **`reported.walls_s` holds three of the four walls §1.5 names** | "add `walls_s.driver_build`, `walls_s.dry` and a per-arm cargo-time summary" | `acceptance_e4pp_schema.py` | unit | no gate |
| 6 | CD:350-354 | **`{told}`, the session clause, is on the env LINE but not in the stamped FACT on a withheld pair** | "carry the clause into the withheld pair's fact the way relocation and strip already are" | `refocus_world.py:339-361` | unit + corpus+drv | same file as B1 — split first |
| 7 | CD:355-358 | **`is_relocation_note` is a two-rule predicate under a one-rule name** | "the next change to that function renames it" | `refocus_env.py:295`, `refocus_cmd.py:157,504` | grep | 2 callers |
| 8 | CD:372-376 | **`ENV_RECORDER_OWN` … is right only while the recorder's own clause is last on the line** | "assert the ordering where the line is built, or anchor the reader on the clause's own start" | `acceptance_e4p_read.py:116,420`; `refocus_rust._env_of` | unit | |
| 9 | CD:377-382 | **Instrument minors, all in the E4″ runner and none load-bearing on a verdict** | none named — all 7: `bound_sentence` whole hours; `_k_reason` list repr; no multi-key strip test; `_drops` lacks `n != GATE_N`; H7's `censused` denominator; dry-run exit 7; exit 9's two shapes | `acceptance_e4pp*.py` | unit | with 1-5 |
| 10 | CD:383-390 | **What the corpus case does not pin** | none named — 1 corpus assertion (marked root), 2 comments (README `last`; thread-serial == task-id), 1 mutant-killing case (`"spawn@" in name`) | `corpus/rust/refocus_spawned_test_fn`, its README, `refocus_world.py`, `convert/sqlite.rs` | corpus+drv + unit | |
| 11 | CD:397-403 | **Three small residues of this slice's splits** | none named — reword the two "two files" comments, caption or drop the bare rule | `refocus_cmd.py:162,169`; `rust/HONESTY-REFOCUS.md:181` | grep | all 3 at HEAD |
| 12 | CD:167-174 | **The fourth E4′ lock test checks table rows and a 200-character prefix, not a full line diff** | "a full diff of the pre-amendment range is the stronger check and was not written" | `tests/test_acceptance_e4p.py:115` | unit | |
| 13 | A2:182-185 | **`sha256.rs` now exists in THREE crates** | none named — one crate owns it, two depend | `sha256.rs` in `sensorium-rt` 212, `-transform` 311, `cargo-sensorium` 302 | suite (NIST vectors) | 3 copies at HEAD |
| 14 | A2:186-192 | **`info` renders an ABSENT `focus` as `focus: -`** | "Fixing the reader would let the literal pin be taken" | `info_cmd.py:176` | corpus+drv | printed line |
| 15 | A2:210-214 | **A stale `rust/target/release/cargo-sensorium` sits on the ROOT disk** | "Delete it or document it" | `rust/target/release/` (untracked) | ls | present, 2026-09-04 build |
| 16 | A2:243-247 | **`Expr::RawAddr` and any future `syn` variant in `expr_attrs`** | none named — exhaustive match, or a loud fallthrough | `lines/facts.rs:183-212` | unit | `RawAddr` now handled; the silent class stands |
| 17 | A2:264-269 | **`reported.line_rows_per_run` published four nulls** | none named — read the census's `line_events`, or drop it | `acceptance_e9*.py` | unit | record not rewritten |
| 18 | A2:274-288 | **`exceptions_rust.py` names `rust/HONESTY.md` at three sites, and after this slice's split one of them is PRINTED** | "the unprobed shapes are named by `HONESTY-ERR-FLOW.md` … and `HONESTY-BLIND-SPOTS.md` items 15–26" | `exceptions_rust.py:431,448,462` | corpus+drv | `:462` is printed; all 3 at HEAD |
| 19 | A2:518-525 | **One driver resolution, THREE copies of it** | "unifying them needs the shared helper to live under `src/sensorium/`" | `refocus_rust.py:122`, `run_corpus.py`, `test_focus_refusal.py` | suite (`…_resolutions_agree`) | |
| 20 | A2:537-545 | **The named hazard fired once and the comparator absorbed it** | "a MATCH does not say the two runs scheduled the same way" — no printed line states it | `refocus_report.py` | corpus+drv | printed |
| 21 | A1:114-116 | **`corpus/run_corpus.py::_run_ids` reads any stdout line starting `run: ` as a trace id** | "Key the id line unambiguously in a later slice" | `corpus/run_corpus.py:334` | unit | pairs with 43 |
| 22 | A1:144-146 | **Rung-2's `acceptance_lib.read_manifests` breaks on rung-3 manifests** | none named — fix at source, drop the workaround | `rust/tests/acceptance_lib.py` | unit | |
| 23 | A1:164-170, IN:203-206 | **Three `chain.terminal` values have no conformance vector** (`panicked`, `left_thread`, `handled_then_failed`) | none named — three vectors | `docs/trace-format/vectors/` | suite | both ledgers |
| 24 | A1:312-318 | **`RUSTDOCFLAGS="-D warnings" cargo doc -p sensorium-transform --no-deps` fails** on two pre-existing private-module intra-doc links | repair the two links (whether rustdoc joins the gate = C38) | `sensorium-transform/src/lib.rs` (`:435/:442`, drifted) | `cargo doc` | |
| 25 | A1:328-335 | **The acceptance runner's own docs still carry the falsified expectation** | "Sweep when that runner is next legitimately touched" | `acceptance_e6q.py:39,276`; `test_acceptance_e6q.py:308` | grep | B4: same file at 800 |
| 26 | A1:336-354 | **Review minors, deferred rather than repaired after the lock** | 10, one line each: side-effecting `visit_stmt` guard; no receiver-position dropped-call row; `close_frame` always computes `preferred`; `render_e6q.py` unreachable from `--doc`; base sha unchecked at cleanup; `ARM_A["selector"]` unpinned; "events's size"; no CALLEE-walk row; `phase_e6prime` step text; `arm_sites_distinct` null-with-no-reason | `arms.rs`, `chains/mod.rs`, `rust/tests/*.py` | unit + grep | |
| 27 | A1:487-490 | **`exceptions_cmd` dispatch sniffs an error MESSAGE** | none named — a typed exception, not a text test | `exceptions_cmd.py:671` | unit | at HEAD |
| 28 | A1:491-498 | **Rung-3 blind spot R16 (v) is in no ledger but this one** | none named — add it to the blind-spots ledger; qualify the printed "born outside this thread's instrumented frames" | `rust/HONESTY-BLIND-SPOTS.md`, `exceptions_rust.py` | corpus+drv | printed |
| 29 | A1:499-505 | **The §11 sweep N1 did not finish** | 4: INDEX §11 row pre-N1; §11's `JoinHandle` gloss + pointer to blind spot 25; `v18` asserts prose; `test_honesty_prose` pins §11 whole | `HONESTY-INDEX.md:44`, `HONESTY-ERR-FLOW.md`, `vectors/v18-*.json`, `test_honesty_prose.py` | unit | INDEX row still pre-N1 |
| 30 | A1:506-511 | **The invocation header's noun is wrong at both ends** | "it is free to fix now" | `exceptions_invocation.py:312` | corpus+drv | at HEAD |
| 31 | A1:512-516 | **Two residuals the repair recorded and did not touch** | none named — one word on the panics line; a fixture for `details vary` | `exceptions_rust.py:573`, `exceptions_group.py:275` | corpus+drv + unit | |
| 32 | A1:517-523 | **`rust/tests/render_grain.py` still carries the first document's literals** | none named — derive all three the way `name` already is | `render_grain.py` `:60`, `:75`, `:327` | unit | `name` now derived; 3 literals stand |
| 33 | A1:547-549 | **`tests/test_acceptance_grain.py`'s box-path scan does not list `rust/tests/acceptance_grain_repair.py`** | none named — walk the directory, as slice 1's scan does | `tests/test_acceptance_grain.py:350` | unit | 5-name hardcoded list |
| 34 | A1:550-554 | **Design §5's test line still spells the continuation note `... 1 more shape; continue with: …`** | "Amend at the next legitimate touch of that document" | rung-4-entry design spec | grep | |
| 35 | A1:555-562 | **Review minors, deferred rather than repaired** | 6, one line each: `_at`/`_hops_line` unnamed cross-module API; Python pin asserts substrings; `group_chains` renders before clipping; `resolve_invocation` leaks handles; `grain_config` a fifth override; runner restates `main` | `exceptions_*.py`, `rust/tests/*` | unit | |
| 36 | IN:238 | **`diff --task` help text is still Python-worded on a Rust trace** | no fix named — the recorder's own words (`vocab.py`) | `diff_cmd.py:698` | corpus+drv | at HEAD |
| 37 | IN:239 | **`vocab.interp_line`'s `or "?"` fallback branch has no fixture** | no fix named — one fixture | `vocab.py:134` | unit | at HEAD |
| 38 | IN:241-243 | **Malformed-meta robustness … no fixture exercises the error text** | no fix named — one fixture per hard-err | `cargo-sensorium/src/convert/` | unit | |
| 39 | IN:244-248 | **`mint()` isolating test** | no fix named — a test that reddens if `minted` is ignored | `runid.rs` | unit | a mutation survived once |
| 40 | IN:254-256 | **Panic-RETURN tag validation** | no fix named — pin tag/outcome writer-independently | `convert/` | unit | |
| 41 | IN:257-259 | **Panic serial numbering on outside-frame panics** | no fix named — pin the serial assignment | `convert/` | unit | |
| 42 | IN:260-261 | **`runid`/driver id-mix helper** duplication | "not yet factored out" | `runid.rs` + driver | unit | |
| 43 | IN:262-263 | **A byte-exact pin for the `run:` line's own format** | "Task 9's conformance fixtures may be the right place" | conformance fixtures | unit | pairs with 21 |
| 44 | IN:264-270, 271-279 | **Eleven rung-2 suite nits, one line each** | none named: `SITE_*` consts; tid-mask justification; `Fixed`/`CapWriter` duplication; two rt tests unmutated; `mechanics.sh` proxy shape; pair-count naming; `_sub` docstring; unused `gen.py` encoders; `trace._c` access; `cargo_driver()` uncached; `"$RUN2" in str(spec)` | `rust/**`, `tests/**` | unit | grouped; all 11 named |
| 45 | IN:280-282 | **Abort core files** — `corpus/rust/abort` leaves one under a permissive ulimit | no fix named — clean up in the case | `corpus/rust/abort` | corpus+drv | |
| 46 | IN:288-290 | **`convert/mod.rs:141-147`'s WARN counts runner records** — "N test binaries" overstates by the doctest count | no fix named — exclude doctest processes | `convert/mod.rs` | unit | |
| 47 | IN:291-294 | **`convert_perf.rs:57`'s test name promises "seconds not minutes"** | no fix named — rename to its bound | `convert_perf.rs:57` | grep | at HEAD |
| 48 | IN:295-298 | **Function lengths against the "under 50" constraint** | no fix named — split six (`frames::process` 274, `convert_one` 164, `wrapper::instrument` 112, `driver::go` 100, `convert_dir` 99, `write_proc_header` 88) | `convert/`, `wrapper.rs`, `driver.rs` | suite | largest A row; not a ceiling |
| 49 | IN:308-315 | **A spawn in an expression position the container visitors skip is neither rewritten nor declared** | declaring it is A; rewriting is C40 | `rust/HONESTY-BLIND-SPOTS.md` | grep | |
| 50 | IN:316-319 | **`visit_trait_item_const` … no golden or edge-case fixture reaches it** | no fix named — one fixture | `visit/walk.rs:118` | unit | path live |
| 51 | IN:320-327 | **`diff`'s verdict vocabulary** — "modulo location" missing on the all-in-tasks branch | "the wording should carry 'modulo location' there too" | `diff_cmd.py:567,676` | corpus+drv | printed sentence |
| 52 | IN:328-329 | **Golden for a fn nested inside a const/static initialiser (`X::h` prefix)** | no fix named — one golden | `sensorium-transform/tests/golden/` | unit | |
| 53 | IN:330-339 | **Fixture for a REFUSED crate-root file on the WRAPPER-BINARY path** | stderr line, `fell_back: false`, empty `files` | `wrapper_fallback.rs` | unit | plan level already tested |
| 54 | IN:343-347 | **The converter's `spool.rs` tests create a temp dir and never remove it** (3 sites) | "a scope guard would tidy all three" | path drifted: `sensorium-rt/src/spool.rs`, `tests/common/spool.rs` | unit | |

### B — over or at the 800-line ceiling (7)

| # | ledger:line | title | fix | files | verified | notes |
|---|---|---|---|---|---|---|
| 55 | CD:369-371 | **`refocus_world.py` is at 777 of 800** | seam: `harness_threads`, `harness_exclusion`, `harness_note`, `uncompared_threads` → `refocus_threads.py` | `src/sensorium/query/refocus_world.py` | wc 777 | blocks #6 |
| 56 | A2:193-195 | **`rust/cargo-sensorium/tests/convert.rs` is 833 lines**, over the ceiling, pre-existing since `089768d` | "the next legitimate touch splits it" | that file | wc **833 OVER** | |
| 57 | A1:117-125 | **`rust/tests/mechanics.sh` is at 795 of 800 lines** | "the next check added to it must split it first"; an E7 second-column check waits on the split | `rust/tests/mechanics.sh` | wc 795 | the E7 check is C |
| 58 | A1:319-321 | **`tests/test_acceptance_e6q.py` is at 800 of 800 lines** | "the next test added there must split the file first" | that file | wc **800 AT** | blocks #25 |
| 59 | A1:137-139 | **The parent spec is at 1 458 lines** | "Splitting a design spec's history is not a docs pass's call" | `specs/2026-09-01-…rust-recorder-design.md` | wc **1458 OVER** | |
| 60 | A1:532-546 | **Files at or near the ceiling** — the repair acceptance record at 795 | "the next paragraph added must split it first" | `…rung4-entry-grain-repair.md` | wc 795 | README half taken |
| 61 | A2:196-209 | **Files near the ceiling** | remaining: `rust/tests/acceptance_e9_phases.py` 788, `sensorium-transform/tests/edges.rs` 784 | those two | wc | other four = X7 |

### D — closable only by a dated NOTE (5)

| # | ledger:line | title | what the note must say, and where | files | verified | notes |
|---|---|---|---|---|---|---|
| 62 | CD:394-396 | **The golden pair `focus_deferred_init.{in,out}.rs:5` names `lines.rs`'s `statement_deltas`** | a dated ledger line: "`statement_deltas` moved to `lines/facts.rs` at `b949129`; the comment stays stale until the golden legitimately changes" | `golden_focus/focus_deferred_init.*` | grep | bytes not edited for a comment |
| 63 | A1:322-327 | **A golden fixture carries the PRE-repair sentence in a comment** ("the only two uses design R2 calls provable") | a dated line: design B1 (2026-09-05) superseded R2's "only two provable uses" | `golden/err_arm_escaped.in.rs:59-60` | grep | sweep at next re-derivation |
| 64 | A1:95-113 | **The reviewer's static list and the census's 31 are different sets** | a dated line: the two E6‴-era sets were enumerated, or the question no longer needs answering | ledger | — | E-flip settled the METHOD only |
| 65 | A1:280-288 | **Per-site adjudication is a reading of SOURCE, and R15's criterion is a property of EXECUTION** | a dated line: `paging.rs:673`'s collapse stands as read; §5.2's caveat is the evidence | e6q record | — | contestable reading |
| 66 | A1:460-467 | **The first record's `results.json` no longer re-assembles byte-identical** | a dated note in both grain records: "predates `schema_version`; a later re-derivation is a NEW derivation" | both grain `results.json` | grep — **neither carries it** | R4 covered `e9`/`e4`/`e4p` only |

### X — fixed or obsolete, never struck (7)

| # | ledger:line | title | closed by |
|---|---|---|---|
| 67 | A2:248-250| **The refusal gate is unverified on a real CI runner** | `ci.yml:130` runs `test_focus_refusal.py`, `:141` runs `run_corpus.py --require-driver`; #21/#22 merged green |
| 68 | IN:283-287| **`rust/sensorium-rt/src/bin/scenario.rs` sits at exactly 800 lines** | split to `src/bin/scenario/`; `scenario.rs` now 245 |
| 69 | IN:233-236| **Task 8's `[exit <cargo_exit>]` suffix** | the bullet records it as "tidied, dated" in the rung-2 plan |
| 70 | IN:249-253| **`Report`/`TraceSummary` unused** | by decision: `#[allow(dead_code)]` + comment, `convert/mod.rs:49` |
| 71 | IN:196-199| **A `--workspace` E6 slice with no `--lib`** | the borrow repair's E6⁗-WS: 0 false of 782 over 144 processes (A1:85-94) |
| 72 | A1:524-531| **The design's §3 and N6 examples show the pre-ship spelling** | the bullet records the dated in-place amendment as taken |
| 73 | A2:196-209 (part)| `splice.rs` 775→232, `visit.rs` 767→512, `lines.rs` 749→449, `driver.rs` 763→328 | `91df4a3`, `853271a`, `b949129`, `03a68d3` |


### C — design-level or ruled NOT FUNDED (43) — titles only; not this slice

| # | title |
|---|---|
| 74 | **`--window` for Rust** — NOT FUNDED (R6/R7); refused at exit 2 |
| 75 | **Refocus over a multi-process invocation** — NOT FUNDED |
| 76 | **The autoref ladder COMMITS an open inference variable to `Debug`** — NOT FUNDED |
| 77 | **No per-site volume cap** — NOT FUNDED; no cost to size against |
| 78 | **Closure bodies and `async fn` bodies get no probes** |
| 79 | **Place writes and `&mut` mutation are not deltas** |
| 80 | **CALL rows still carry no arguments on a Rust trace** |
| 81 | **`flow --object` on a Rust trace stays REFUSED** |
| 82 | **The cost residual needs a different instrument** |
| 83 | **Python traces still print one block per raise (N7)** — needs the per-disposition site defined |
| 84 | **The in-source acknowledgment marker (N8)** — decided, unbuilt |
| 85 | **The rung-5 lever** — record which env vars were READ; both recorders change |
| 86 | **H4′'s verdict is OPEN** — gate vs strict reading |
| 87 | **`focus_matched` can carry a STALE unit's match** — filter costs a read per manifest |
| 88 | **`tasks:`/"task stream", the last asyncio nouns on a Rust screen** — *ruled left alone* |
| 89 | **The zero-candidate refusal under a pid cycle** — *ruled left as is*; impossible topology |
| 90 | **A key on one side only whose whole value was our fragment still withholds** |
| 91 | **`--bench --require-driver` is inert** — *ruled left as is* |
| 92 | **Two build caches on the second disk are Brice's to free** (24+21 GB) |
| 93 | **The composite-loop residual** — duplicate the exit walk's recursion |
| 94 | **The uppercase-initial heuristic** — the alternative does not compile |
| 95 | **The suite's skip count depends on one variable** — 1428/12 vs 1437/1 |
| 96 | **`last` is mtime-ordered** — order by recorded start, or print an id |
| 97 | **The digest floor is 16 hex characters** |
| 98 | **The discriminator's second condition has no subject on `cargo test` material** |
| 99 | **A `chain.holder` field on the wire** |
| 100 | **The nested-literal gap** (blind spot 23 (a)) — zero measured exposure |
| 101 | **E2″'s numerator is `(file, line)`-deduped** |
| 102 | **Three classes a reader may reasonably contest** — settled by N8 or `--allow` |
| 103 | **Four of the eleven flipped arms were never executed** — asserted only |
| 104 | **Two rows §1 asks for are ABSENT, not zero** — needs a target-kind field |
| 105 | **The side-channel residual** (blind spot 23 (d)) — inter-procedural |
| 106 | **`.await`/`?` wrapping a dropped call is not recognized** |
| 107 | **An origin-keyed collision prints no file** |
| 108 | **The shape key still reads masked PROSE** |
| 109 | **`.is_err()`/`.is_ok()` as OBSERVATION tags** — no WORD for the guard |
| 110 | **An `.unwrap()`/`.expect()` probe** — re-open on the first target with panics in its tally |
| 111 | **Whether rustdoc joins the gate set** — ruling half of #24 |
| 112 | **A 0-byte spool costs the whole invocation's conversion** — ruling owed |
| 113 | **Rewriting spawns in expression positions** — rewrite half of #49 |
| 114 | **No unit tests on the acceptance instruments** |
| 115 | **`refocus --window QUALNAME` reads as a size/range** — blocked on #74 |
| 116 | **The Python `live_threads` line's pre-existing asymmetry** |

## 3. The splits (B), from the seam map

| File (lines) | Moves to | Seam | Notes |
|---|---|---|---|
| `tests/programs.py` 868 | `tests/flow_programs.py` (flow shapes `:774`) + the async block 523–663 | its own `# --` banners | 19 importers use `from tests.programs import …`; 3 importer edits; ~634 left |
| `tests/test_tree_frame.py` 1146 | `tests/test_tree_frame_gen.py` @483 | banner | `GEN_SRC` used above 388 → stays; `_rec` imported by the new file |
| `tests/test_boot_cli.py` 925 | `tests/test_boot_cli_run.py` @486 | banner | 8 names cross → imported from the first file |
| `tests/test_exceptions.py` 896 | `tests/test_exceptions_rust_shapes.py` @546 | banner | zero crossings |
| `tests/test_diff.py` 854 | `tests/test_diff_tasks.py` @486 | banner | |
| `tests/test_tracer.py` 817 | `tests/test_tracer_classify.py` @411 | banner | the `_SENSORIUM_DIR` monkeypatch repoints to `tracer_frames` with the tracer split |
| `tests/test_refocus.py` 809 | per the map's seam | banner | |
| `tests/test_acceptance_e6q.py` 800 | `tests/test_acceptance_e6q_record.py` @516 | banner | unblocks #25 |
| `rust/tests/acceptance_schema.py` 851 | `rust/tests/acceptance_schema_cells.py` @565 | banner | |
| `rust/cargo-sensorium/tests/convert.rs` 833 | `tests/convert_runner.rs` (G7+G8 568–707 + `OutputExt`) | cargo auto-discovers | helpers `FILE`/`Fixture`/`open`/`meta`/`context` duplicated (house pattern, `convert_meta.rs`); `count` not copied; no visibility bumps |
| `src/sensorium/record/tracer.py` 1193 | `tracer_frames.py` (~365: `_CO_*`/`_GENLIKE`, `_frame_kind`, `module_name_for`, `FocusSpec`, `WindowSpec`, the classification block 476–730) + `tracer_exc.py` (~205: `_is_control_flow`, retention constants, `_ExcRefs`, `_TLS`) | by responsibility | re-exports `FocusSpec`, `module_name_for`, `_RETAIN_MAX`, `_CONTROL_RETAIN_MAX`; `_CONTROL_FLOW_EXC` is dead → removed; **the one non-move edit**: `tests/test_tracer.py:752` patches `_SENSORIUM_DIR` on `tracer` — repoint to `tracer_frames` in the same commit |
| `src/sensorium/query/refocus_world.py` 777 | `refocus_threads.py` (`harness_threads`, `harness_exclusion`, `harness_note`, `uncompared_threads`) | CARRIED-DEBT's named seam | re-export block in the `refocus_cmd` idiom; done BEFORE #6's edit |
| `rust/cargo-sensorium/src/convert/chains/tests.rs` 771 | `tests_terminals.rs` | banner | the only Rust visibility bumps: eight helpers → `pub(super)` |

Named, not split (CARRIED-DEBT carries the seam): `rust/tests/mechanics.sh` 795, `acceptance_e9_phases.py` 788, `acceptance_e4p_read.py` 787, `edges.rs` 784, `test_refocus_licence.py` 772, `test_flow_identity.py` 769, `record/boot.py` 768, `golden.rs` 764, `test_runs_info.py` 763, `acceptance_e4pp_phases.py` 761.

## 4. Not in this slice

Every C row of §2 (43), including R6/R7's four, N7, N8, the rung-5 env-reads lever, H4′'s reading, the function-length refactor (R4), and the `last`-ordering and `--bench` items ruled left alone. They are the next conversation with Brice.

## Amendments

Appended, never edited in place; each names the section and the date.

**A1 — §3, the seam map's three new-file NAMES, 2026-09-08 (Task 1).** Three of
the nine Python/instrument splits landed under a different name from the one
§3's table spells, each because the table's name would send a reader to the
wrong file, and each matching the seam map's own spelling:

* `test_exceptions_rust_shapes.py` → **`tests/test_exceptions_synthetic.py`** —
  nothing in the moved 351 lines is Rust, and a genuinely Rust sibling
  (`tests/test_exceptions_rust_grouping.py`) sits next door.
* `test_tracer_classify.py` → **`tests/test_tracer_serials.py`** — "classify"
  names `Tracer._decide`/`_classify`, whose tests are ABOVE the seam and stay,
  and Task 3 lands `src/sensorium/record/tracer_frames.py` holding exactly that
  classification block.
* `acceptance_schema_cells.py` → **`rust/tests/acceptance_schema_e5prime.py`** —
  `_cells` means cell builders in that directory (`acceptance_e4pp_cells.py`
  and two siblings) and nothing moved is one; the file's two siblings are named
  for the document they assemble.

The design's other new-file names shipped unchanged. §3's table is the record
of what was planned; this note is what was taken.

**A2 — §3 and R9, four splits the map did not name, 2026-09-08 (Task 6).** R9
says the near-ceiling instrument files are split at their `# ----` banners if
this slice's own edits take them over 780. Four did, and were:
`rust/tests/acceptance_e4pp_phases.py` → `_phases2.py` (the H7 banner),
`rust/tests/acceptance_e4pp.py` → `acceptance_e4pp_kills.py` (the main banner),
`tests/test_acceptance_e4pp.py` → `tests/test_acceptance_e4pp_kills.py` (the
same seam), and `rust/tests/acceptance_e4p_read.py` →
`acceptance_e4p_trace.py` (its store banner). Every one a pure move with every
name imported back — R9 working as written, on files R9 named.

