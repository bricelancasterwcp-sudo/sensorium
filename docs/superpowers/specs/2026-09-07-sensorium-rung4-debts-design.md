# Rung 4, slice 3 — the rung-4 debts

**Date:** 2026-09-07 · **Status:** design, approved in one message (Brice,
2026-09-07: "go") · **Design authority:** Claude — every ruling below is
Claude's, recorded here, none deferred · **Base:** main `24de001` (Python
0.8.4; driver 0.5.0 / transform 0.4.1 / rt 0.4.0) · **Branch:**
`feat/rung4-debts`

Slices 1 and 2 (PRs #19, #20) closed rung 4's features and left seven debts
with their fixes spelled out in `docs/CARRIED-DEBT.md`. This slice closes
them and measures the one that changes a printed verdict word.

## 0. Rulings (Claude, 2026-09-07)

| # | Debt | Ruling | Why · cost if wrong |
|---|---|---|---|
| R1 | the licence is WITHHELD on every `cargo test` pair by its untraced-thread clause | a non-main thread whose ROOT frame's site is a `#[test]`-marked fn is the **harness thread** (libtest's per-test thread); the licence excludes harness threads from its untraced-thread counts and names them; Python only | the manifest already marks test fns and `exceptions` already builds the lookup; Python traces carry no test marks so their path is unchanged by construction · cost: a `#[test]` fn that itself spawns nothing reads granted — which is the truth |
| R2 | a re-run whose test spawns an instrumented child yields two `refocus_of`-linked traces and a refusal naming the wrong cause | `find_pair` excludes a linked trace whose `ppid` equals another linked trace's `pid`; the parent is the pair; the excluded child run ids are printed on the pair line; `runs` still lists them | the answer is about the process the user recorded; the child stays visible · cost: a child that is itself the interesting process is not the pair — `runs` names it |
| R3 | one ~40 MB shim COPY per distinct focus | `install_shim` hard-links the driver, falling back to a copy on any error (cross-filesystem included); the key already hashes the driver's bytes, so a replaced driver changes the key | cargo keys the wrapper by path · cost: a hard link shares the inode with the driver, so `set_permissions` touches the driver too — it is already executable |
| R4 | `results.json` re-derivation policy | every raw and assembled results file carries `schema_version` (`"e9/1"`, `"e4/1"`, `"e4p/1"`); the renderer states once when the assembled schema is later than the raw's ("re-derived under X from a raw written under Y") | the entry slice's open item; cost: one string per file |
| R7 | housekeeping | `info` prints the unverifiable checks beside the licence lines; `driver.rs` splits into `invocation.rs` + `launch.rs`; the transform's census path populates sites and skip reasons so `fn_items` stops running the splicing transform | ceilings and cost · none |
| R6 | `--window`; refocus over multi-process invocations; an inference-variable opt-out; a per-site volume cap | **not funded** until a use asks; declared blind spots stand | — |

## 1. What ships

1. Python (`refocus_world.py`, `refocus_rust.py`, `info_cmd.py`, `vocab.py`): R1, R2, the `info` line. Python 0.8.5.
2. Driver (`rt_build.rs`, `driver.rs` → `invocation.rs`, `launch.rs`): R3, the split. `cargo-sensorium` 0.5.1.
3. Transform (`focus.rs`, `visit.rs`/`splice.rs`): `fn_items` via the census path. `sensorium-transform` 0.4.2.
4. Instruments: `schema_version` in the E9 and E4 runners/schemas/renderers; a new pass-2-only runner E4′.
5. A corpus case `refocus_child_run`; the E4′ record measured once; docs; CARRIED-DEBT strikes.

## 2. R1 — the harness thread

`refocus_world._licence_caveats` reads `meta.threads_started` / `live_threads` and the `fingerprints` rows. New: `harness_threads(trace) -> set[int]` = the serials of non-main threads whose root frame (`frames` row with `thread_id = serial`, `parent_id IS NULL`) has a `code_objects` `(qualname, file)` that `meta.sites` marks `test: true` (the same table `exceptions_rust._marks` builds). The untraced-thread counts subtract `len(harness_threads)`; the caveat line reads `no thread started besides the main one and 1 harness thread (libtest's per-test thread, excluded as the recorder's own)`; when program threads remain, the WITHHELD reason names their count and the harness exclusion. Python traces: `meta.sites` has no `test` marks → the set is empty → byte-identical output. `capabilities`, `TRACE_FORMAT`, the converter: unchanged. Blind spot 12's WITHHELD bullet is struck and corrected.

## 3. R2 — the child-run pair

`find_pair` reads `pid`/`ppid` from each candidate's meta (both recorded by the converter). Candidates whose `ppid` is another candidate's `pid` are children: excluded from the pair, listed as `child runs excluded from the pair: <ids>` on the pair line (stdout) and stamped as `refocus_children` on the new trace. One parent → the pair; still 0 or > 1 parents → REFUSED as today. `runs`/`info` unchanged.

## 4. R3 — the shim

`install_shim`: `fs::hard_link(exe, tmp).or_else(|_| fs::copy(exe, tmp).map(|_| ()))`, then the existing rename. Test: byte identity (existing) plus, on one filesystem, `metadata().ino()` equal between the driver and the shim; the fallback pinned by a temp-dir on a different filesystem when one exists (`/dev/shm` if mounted, else skipped by name).

## 5. R4 — `schema_version`

The runner writes `schema_version` into the raw record; `assemble_*` copies it and stamps its own `assembled.schema_version`; when they differ the renderer's §2 prints `re-derived under <assembled> from a raw written under <raw>`. Completeness tests include the field. E9 and E4 gain `"e9/1"` / `"e4/1"` (their committed results.json are NOT re-derived — R-F15/R-G15 precedent: a derivation is stated, not rewritten; CARRIED-DEBT notes the two files predate the field).

## 6. R7 — housekeeping

- `info`: after `licence verified:` lines, `licence unverifiable: output (not recorded), children (not witnessed)` when `refocus_licence_unverifiable` holds names; nothing when absent.
- `driver.rs` (791): `Invocation` + serde + `write_invocation` → `invocation.rs`; the cargo child's env/launch block → `launch.rs`; `go` orchestrates. Pure moves; behaviour byte-identical (the smoke tests pin it).
- `fn_items`: `Ctx` gains `record_sites: bool` (true in census-for-focus mode) gating the `sites`/`skipped` pushes independently of `emit`; `fn_items` runs `Ctx::new(..., emit=false, record_sites=true)` + `visit_file` and reads the `Ctx`; `census()`'s `Census` shape unchanged; a test that `fn_items` output equals the previous route's on every golden input.

## 7. Corpus — `refocus_child_run`

A `cargo run` program whose `main` spawns itself as an instrumented child (the `corpus/rust/abort` child-run shape) and waits; `cargo_args: ["run"]`. `refocus $RUN --focus main` → `verdict: MATCH`, exit 0, the pair line naming one excluded child run; `runs` shows two new traces linked by `refocus-of` (parent + child). Pins derived from §3 before recording.

## 8. E4′ — pre-registered

Record `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md`, §1 alone and byte-locked; runner `rust/tests/acceptance_e4p.py` (a sibling of E4's family, pass 2 only). Subject: the 61 originals of E4 (`raw_pass1.runs[*].run` in E4's archived raw record), copied into a FRESH store by `sqlite3 <src>.db "VACUUM INTO '<dst>.db'"` (a checkpointed single-file copy; the kept store is never written), a FRESH `CARGO_TARGET_DIR`; the driver built from this branch's HEAD; the clone at `e209ed9`, read-only.

**Loop.** For each of the 61 (E4 §1.1's order): `sensorium refocus <orig> --focus <name>` under the new rule.

**Expected, written first.** Licence **granted 57 of 61**; **WITHHELD on exactly four**: `a_pager_can_be_shared_across_threads` (1 program thread) and the three `pager_refusal_advice_test` server tests (4 worker threads each), each reason naming the program's own threads AND the excluded harness thread; MATCH 61 of 61 (the comparator is untouched); every pair found (pair 1 of 1); the shim census: 61 focused keys whose inode equals the driver's when on one filesystem (this box: the driver and the target share one filesystem), bytes counted once.

| id | question | endpoint (both readings pre-committed) |
|---|---|---|
| H1 | does the harness rule change the licence word as predicted? | granted = 57 and withheld = the named four → PASS; any other partition → STOP (the rule or its lookup is wrong); each withheld reason names the harness exclusion → reported |
| H2 | is the verdict untouched? | MATCH 61 of 61 → PASS; ≠ → STOP |
| H3 | is the pair found? | 61 of 61 pairs of exactly one → PASS |
| H4 | does the shim link? | 61 focused keys; inode equality with the driver for every key on one filesystem → PASS; a copy where a link was possible → finding; bytes reported |
| H5 | schema_version present? | raw and assembled carry `e4p/1`; the E4 and E9 renderers print their fields on a dry assemble → PASS |
| H6 | nothing else moved? | corpus (incl. `refocus_child_run`) equal; Python suite green; `cargo test --workspace` green → PASS |

Kill rules as E4's (a `.FAILED` before any number is infrastructure; after, a STOP; once; bound 1 h; 1800 s per refocus).

## 9. Not in this slice

R6's four items; any change to the comparator; `TRACE_FORMAT`; PR #17's files (TRACE-FORMAT touched in exactly one place only if a sentence about the licence exists there — check; else not at all).

## Amendments

Appended, never edited in place: a design that reads as though it had always
said what the implementation found is a design nobody can be held to. Each
entry names the section it amends and the date it was made.

**A-§2 — the environment clause has a relocation rule, and a carried tier
(2026-09-07, before any E4′ number was read).** §2 ruled on the harness thread
and left the licence's env clause alone. Task 5's dry run showed a second
clause that cannot not fire: §8 mandates a FRESH `CARGO_TARGET_DIR` for the
re-run (H4's inode census needs one), and cargo hands the test binary four
variables that embed the root — `CARGO_TARGET_DIR`, `CARGO_BIN_EXE_*`,
`LD_LIBRARY_PATH`, `RUSTDOCFLAGS` — so under the instrument as pre-registered
the licence would have been WITHHELD on all 61 pairs for a reason unrelated to
R1, and H1 would have STOPPED with nothing learned. **Ruled**: a re-run from
another target directory is a normal use of the tool, and the clause must not
read the root's RELOCATION as a change the world made — and must not
blanket-exclude those four keys either, because a program really handed one
extra directory on the loader's path would then earn a full licence. Each
DIFFERING key is asked whether its difference disappears when the original's
root is substituted for the re-run's, compared entry by entry down a
`PATH`-like list and anchored at path boundaries on both sides; a key the rule
explains is NAMED on the env line and kept as a fact in the trace, and every
other difference withholds as before. Shipped in `refocus_env.py` (a module of
its own: `refocus_world.py` was the file nearest the ceiling) at `1a76757` with
`d43b7aa`. **Carried, not built**: a re-run launched from another SHELL still
meets an unearnable licence, because session-identity variables differ there.
The ruled design is a named, versioned positive set of build-and-run-bearing
variables that withholds, with every other differing key counted and named but
not withholding; it is not built before the measurement (fewer source changes
before a measurement is the rule, and E4′ does not need it), and it is in
`docs/CARRIED-DEBT.md` with its enumeration. What E4′ does instead is a launch
guard: the runner compares its own process environment with every original's
recorded one under the licence's exclusions and REFUSES to launch on any
difference (`10e2712`, `pins.env_parity`).

**A-§3 — the >1-candidate refusal names the child runs (2026-09-07).** §3 said
the excluded child ids are printed on the pair line and that "still 0 or > 1
parents → REFUSED as today". As implemented, the refusal is not as today: the
same `children_note` sentence is appended to it. The count and the ids in that
sentence stay the CANDIDATES' — they are what the reader has to choose between,
and naming a child among them would send someone after a selector for a process
cargo never started — but a bare count would otherwise describe two of the
three traces the re-run really wrote. One sentence, used in both places, so a
reader told about an excluded trace twice is not left working out whether they
are one fact.

**A-§4 — the shim install unlinks first, and chmods only the copy
(2026-09-07).** §4 gave the install as
`fs::hard_link(exe, tmp).or_else(|_| fs::copy(exe, tmp).map(|_| ()))` then the
existing rename. Two corrections, both found in review:

1. **The leftover temporary must be unlinked BEFORE either call.** `hard_link`
   refuses an existing destination, which alone would cost only a needless
   copy — but a `tmp` left behind by a run that died between install and rename
   may ITSELF be a link to the driver, and `fs::copy` truncates what it opens.
   The install would then destroy the driver it was installing. Unlink first,
   and a clear that fails for anything but `NotFound` STOPS the install, because
   the name is still there and the copy would open exactly the survivor the
   unlink was meant to destroy.
2. **`set_permissions` belongs to the copy path alone**, so **R3's conceded
   cost is void.** The ruling's "cost if wrong" column accepted that a hard link
   shares the driver's inode and a chmod would therefore touch the driver too,
   on the grounds that it is already executable. It buys nothing: on the link
   path the shim IS the driver and already carries the driver's mode, and only
   `fs::copy` creates a destination whose mode has to be stated. Nothing in this
   recorder writes the driver's inode, which is a stronger promise than the one
   §0 was willing to pay for.

**A-§6 — `fn_items` through the census path has a THIRD declared difference,
and the walk's purpose is a named enum (2026-09-07).** §6 asked for a test that
`fn_items` output equals the previous route's on every golden input, and
`tests/fn_census.rs` is that differential. One class of input it structurally
cannot cover, and no widening of its corpora would: **a file whose walk is
clean but whose SPLICING half would fail** answered `[]` under 0.4.1 and
answers with its full row list now. The splicing half is everything the walk
does not run — `splice::assemble`, `check_line_count`, `check_spawn_ordinals`,
the `MAX_SITE_INDEX` guard, and `wrap_operand`'s three refusals — and every
condition there is a construction bug in the crate or a file with more than
16.7 million sites, so no real tree holds one. The class is reached through the
one lever a caller can pull (`first_site` past the wire's 24-bit field) and
pinned by name, rather than only described. It is also the BETTER answer for
focus resolution: a `--focus` naming a function plainly in the file used to be
refused before cargo ran because some other file in the workspace could not be
spliced, and the splice failure now surfaces where it belongs, as a loud
transform error during the build naming the file and the offset. Second, §6's
`Ctx` gains a named `census::Mode` (`Emitting` / `Census` / `Counting`) rather
than the `record_sites: bool` beside `emit`: the three call sites wanted
`true, true` / `false, false` / `false, true`, and transposing the last to
`true, false` compiles silently and turns the resolver's census into a full
emitting walk that records no rows — a defect reachable by a typo, which
`clippy::fn_params_excessive_bools` does not fire on at two. Three named modes
make the fourth combination unspellable.

**A-§8 — the bound and the copy's executor (2026-09-07).** §8 gave the kill
rules "as E4's ... bound 1 h". The record's §1.4 sets the whole loop at
**1 h 15 min** with each `sensorium refocus` at 1800 s; E4 closed its pass-2
half well inside its own bound, and the extra quarter hour is for the 61 fresh
focused rebuilds this pass makes. The pre-registered copy statement
`VACUUM INTO` is unchanged, and §1.3 already allows either executor — the
`sqlite3` CLI when one is on `PATH`, or Python's `sqlite3` module running the
identical SQL. On this box **no `sqlite3` CLI is installed**, so the Python
module is what runs it, and §2 records that fact and the SQLite library version
as lens facts. Neither executor changes the bytes the statement produces.
