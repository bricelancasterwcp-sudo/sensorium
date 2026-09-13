# CARRIED-DEBT — volume 11

The 2026-09-12 section — S5 rung 4's debts, funded — moved here **2026-09-13**
(the refocus slice for TypeScript, in its documentation task) so
[`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays under 800 lines. It is the
eleventh numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file.

The move was measured before it was made, the way the ledger's own lesson
asks: the refocus slice's section was drafted at **346** lines against a live
file of **489**, which would have taken it to **836** — thirty-six over the
ceiling and fifty-six over this slice's own target. Content was not trimmed to
fit; the oldest section was cut, which is the rule.

**The wording, the order and the strikes are unchanged** — nothing was edited
BY the move, a resolved item is struck through here exactly as it was in the
live file, and nothing is deleted. **The refocus slice's one strike inside the
section travels with it**: the `js_inspect._MORE` clause of *Deferred by
ruling*, which said the alias would be removed at the next Python minor, is
struck below with a dated pointer, made after the move. The house rule stated
in `docs/CARRIED-DEBT.md`'s header governs every volume, and a deferred item
below is still open unless it is struck.

## 2026-09-12 — S5 rung 4's debts, funded (Python 0.13.0 / sensorium-ts 0.4.0 / rt 0.5.0 / transform 0.5.0 / driver 0.6.0)

The slice that pays rung 4's list: two recorder gaps closed for real — a
TypeScript RETURN that now follows the rows of the `finally` it passed
through, and a Rust block-like statement's row that now says which names went
out of scope on it — and rung 4's three STOPped endpoints re-adjudicated over
its own committed transcripts under a parser without the four defects that
produced them. Thirteen amendments (A1–A13) and eighteen controller rulings
(P0–P17); every one that changed a reading is in the spec's §12. **The slice
ships `DONE-WITH-STOP`** — seven gated endpoints and two fences, each read
once, six of the seven PASS. The one STOP, **E6-TS′**, is a finding about this
slice's own pre-registration and not about the tool: the clause was written in
the wrong command's vocabulary, was left standing rather than edited, and was
measured and reported against itself (record §3.4, §4.4, §5 item 1, at
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md`).

### Settled — rung 4's own debts, closed here

Struck where they stand, with a dated pointer — in
[`CARRIED-DEBT-ARCHIVE-10.md`](CARRIED-DEBT-ARCHIVE-10.md) since this file's
own ceiling cut the rung-4 section there, strikes and all. Restated in full
here, which is why that was safe: a reader who reaches this section first
should not have to follow a pointer to find what closed.

- **H2, H4 and H5 STOPped on the instrument, not on the recorder** (rung 4's
  *gaps* 1–3) — closed as ENDPOINTS: **E12′** re-registered all three over the
  thirteen committed transcripts, hash-verified before a cell was read, under
  `typescript/acceptance/e12p_report.py`, and all three PASS — **H2′ 5 of 5**,
  **H4′ 3 of 3**, **H5′ 7 of 7** (record §3.1, §4.1). Six sites read three
  independent ways with `focus_matched` one lower for the qualname two anonymous
  arrows share; W2's clause read off the row's own `unbound` and not off a line
  number; and the CALL sighting the old parser printed but could not see, found
  at `e10` with its line from the code object. `e12_report.py` is kept unedited,
  a locked record citing it by name. The DESIGN questions gaps 1 and 2 also
  raised are untouched and restated below under *Deferred by ruling*.
- **`e12_report.py`'s row parser drops a `RETURN` row** (rung 4's *gaps* 4) —
  closed: `e12p_report.py`'s row regex takes one space or two before `->`, so
  `elsewhere_not_gated` reads **5** where the transcripts print five.
- **Rust's fold keeps a dead block-scoped `let` alive** — closed:
  `sensorium-rt 0.5.0` writes delta tag **3** through `line_unbinding`, the
  transform lists a block-like statement's head-pattern bindings and its direct
  `let`s in source order, and `cargo-sensorium 0.6.0` reads them onto the row
  as `unbound`. Pinned by `corpus/rust/focus_block_let`,
  `rust/sensorium-transform/tests/unbound.rs` and `v40-rust-line-unbound`.
- **`info`'s `truncated values:` misses an inspect-side cut** (blind spot 36)
  — closed: `js_inspect.is_clipped` answers off the `… N more characters` tail
  as well as the `trunc` flag, pinned by `corpus/typescript/focus_long_string`.
- **A new TypeScript corpus case cannot ask an `exceptions` question** (blind
  spot 37) — closed: `e6ts.py`'s `PRE_REGISTERED` table is re-registered by
  rung 3's procedure, `focus_catch_binding`'s row landed in its own commit with
  its adjudication, and the procedure is written down in the instrument that
  enforces it. The first case to use it found the procedure's own weak point —
  see *the gaps*, below.
- **A statement in a `finally` after a `return` mints no row** (blind spot 38,
  R42, the largest clause of rung 4's *Deferred minors*) — closed:
  `sensorium-ts 0.4.0`'s `pend`/`seal` pair defers the exit for the one shape
  that needs it, pinned by `typescript/test/rt.seal.test.mjs` and
  `corpus/typescript/focus_finally_return`; 38 is struck where it stands.
- **`tests/test_corpus.py` at exactly 800** — closed: the harness half moved
  to `tests/test_corpus_harness.py`, a pure move verified by the test-name set.
- **`CHANGELOG-ARCHIVE.md` at 742, unable to take another cut** — closed:
  `CHANGELOG-ARCHIVE-2.md` opened with a preamble in the archive's voice and a
  pointer from volume 1, so the 0.13.0 entry (151 lines onto 437) needed none.
- **Three more, each closed where it stood:** `typescript/HONESTY-COST.md` is
  read structurally by `tests/test_ts_honesty_prose.py` now, the way the
  blind-spot lists are; rung 3's spec §4.3 prose has the dated 2026-09-12
  parenthesis it asked for; and rung 4's *Deferred minors* paragraph is closed
  clause by clause at the sites it named, mostly at this slice's minors task,
  with its own closing sentence naming the eight it left, of which **seven**
  stay open — the converter fixture's `driver_version` was closed at Task 12
  by A8, and the count is corrected here rather than left to read stale.

### The gaps this slice's measurement found (record §5)

1. **The pre-registration named the wrong disposition, and the slice reported
   it against itself — E6-TS′, STOP.** `focus_catch_binding` was
   hand-adjudicated in `grep --kind HANDLED`'s vocabulary — a HANDLED event,
   traced with confidence — and *nothing swallowed* was concluded from that
   confidence. `exceptions`'s own documented rule says `swallowed` means an
   absorbing handler took it and the frame holding it then returned, which is
   precisely the shape; the answer prints **1** where the clause says **0**, by
   two derivations that agree. **Closed as far as this slice can close it**:
   `e6ts.py`'s procedure now says, in as many words, that a hand adjudication
   must derive from the command's own documented rule and never from a sibling
   command's kinds, and names the commit that got it wrong. **Left open:**
   nothing mechanical — the residue is the lesson. *Cost if wrong:* a
   pre-registration that reads confidently in the wrong vocabulary STOPs an
   endpoint that was never about the tool.
2. **The assembler has no representation for a reading a human made.**
   `assemble_s5debts.py` filters `gated` through a fixed `ORDER` and builds
   `reported` from a fixed key set, so an added E6-TS′ cell would have been
   **silently dropped** rather than refused — and the file it wrote could not,
   on its own, show the one endpoint that STOPped. Ruling
   **P17** closed that by hand: `reported.adjudicated.E6TSp_original` and a
   top-level `word`, stamped *added after assembly, by hand (ruling P17)*,
   additive, neither an instrument value. **Closing it** means a declared
   `adjudicated` section fed from a file the operator hands in like every other
   input, so a hand reading's provenance is checked by the same machinery as
   the rest. *Cost if wrong:* a results file that either drops the human
   reading in silence or carries it with no provenance.
3. **H4′'s W2 class clause was read over the rows `--limit` printed, not over
   every hit.** The tally says **52** hits; the transcript prints **20**, and
   *0 of the 20 printed HITs sits on a row whose `unbound` names `count`* is a
   statement about those twenty. The cell's `note` says which readings are the
   tally's and which the printed rows', and no TOTAL was counted by counting
   rows — that was defect 2 of the four. **Closing it** means a reading whose
   population is the whole hit set, which `watch` would have to offer. *Cost if
   wrong:* a class clause that holds over a printed prefix, stated as if it
   held over the set.
4. **`h4p` and `h5p` carry no `data_recorder` field where `h2p` does.** The
   instrument records per cell the recorder the DATA was written by, distinct
   from the one that READ it; two of the three E12′ cells lack it, so a reader
   of those two alone cannot see the transcripts are rung 4's. Instrument-side;
   it moved no number. **Closing it** means one field in `e12p_report.py`'s
   `h4p` and `h5p`. *Cost if wrong:* a cell that reads as if taken off this
   slice's own recording.

### Deferred by ruling

Each was ruled at execution, is in the spec's §12 or the ledger, and leaves
something a later slice may want.

- **The C pile, untouched by design** (spec §9, class **C** of the inventory —
  design-level questions, not mechanical debt). **A `--focus` spelling meaning
  *this function and not what it nests*, and identity for an anonymous
  function-like** (rung 4's *gaps* 1–2): one question from two sides — what
  `--focus` promises, and whether a qualname is an identity — which the refocus
  slice inherits as stated. **Blind spots 28–31** (a place write is a row with
  no delta; `this` is not read; a conditional assignment's row does not say
  whether the write happened; a `switch` discriminant's assignment is reported
  nowhere), **34** (`enum` / `namespace` names and a class `static {}` block
  reach no delta) and **35** (`undefined` and a BigInt are readable and
  unwritable at `flow --value`): each deferred by a ruling whose reason still
  holds — a snapshot-and-diff's cost at scope×statements, `this` as a
  pseudo-argument on demand, a row that never invents a write, the erased
  binders, and a value one command can read and the other cannot spell.
  **`info`'s `focus matched:` line has no length bound** (R31) and **prints on
  a focused Rust trace too** (R32), both accepted as shipped: a cap would hide
  the fact the line exists to show, and every `info` line is gated on the meta
  key it prints, never on `meta.lang`. And **the TypeScript skill lives outside
  this repository**, the arrangement Python's and Rust's have. *Cost if wrong:*
  a reader focusing three functions pays for six and is told five; the deltas
  under-report, in the direction that never invents; a watched name reads as
  never recorded and a search sights nothing; one unreadable line on a wide
  focus; a skill that drifts from the CLI it documents with nothing in this
  tree to catch it.
- **`rust/HONESTY-BLIND-SPOTS.md` stands at exactly 800 lines** — the ceiling,
  which `n <= LIMIT` still passes. Ruling **P15**: no split in this slice; the
  file's **next** entry must open a volume, on the `CARRIED-DEBT-ARCHIVE`
  precedent, and that split costs `rust/HONESTY-INDEX.md`'s *one home of §12*
  promise. *Cost if wrong:* a later slice writes an entry that cannot land
  until it pays a seam it did not plan for.
- **Four carried smalls in the readers, each with its reason and none measured
  away.** ~~`js_inspect._MORE`, the alias of `INSPECT_MORE` kept for one
  release, has zero consumers and is **removed at the next Python minor** —
  named here so the removal is scheduled, not discovered.~~ — **closed
  2026-09-13**: the next Python minor is **0.14.0** and the alias is gone
  (ruling **S2**), `tests/test_js_inspect.py` asserting the name's absence;
  [`CARRIED-DEBT.md`](CARRIED-DEBT.md) §2026-09-13 *Settled* restates it.
  `sites._anchor`'s cwd fallback is
  **closed by this dated note** (**A9**): it IS the documented Python-trace rule
  (`root` or `cwd`, else `None`), the comment the function carries says so, no
  trace in the corpus reaches it, and no code changed. `find_in_value`'s `path`
  **stays third** — a positional caller passes it, so the reorder is unsafe and
  `src/sensorium/query/flow_values.py` carries a comment saying why. And
  `flow_cmd`'s `v["oid"]` read **stays unguarded** below the new type guard,
  because the input that would reach it — a container capture carrying neither
  `oid` nor `type` — is dead today, which is also what `flow_cmd.py:565-574`'s
  refusal wording is about. *Cost if wrong:* one dead name for a release; a
  rootless trace anchored to the reader's cwd, which is what the rule says to
  do; one argument in an order a reader would not have chosen; a `KeyError`
  where a named refusal belongs, on an input nothing produces.
- **A block-like EXPRESSION takes no completion row, so a family of Rust
  shapes is still not unbound** (Rust blind spot **33**, opened by this slice).
  `let y = { … }`, a `match` arm body, `let y = if …` and a function's tail
  expression all bind names nothing pops, because the rule is attached to
  statements. `focus_unbound_tail`'s goldens falsify the tail case; the other
  three are untested and the entry says so. **Closing it** means a rule for
  expression position — a design question about where a row can be minted at
  all. *Cost if wrong:* `watch` reads a value block's name as still in scope.
- **The five rung-3 D items get their dated NOTE here** (spec §2, class **D** —
  closable only by a note, because nothing can be built for them), each with
  what would close it. (1) **Two of the three `untraced catcher` variants are
  unmeasured on a lens** — all seventeen rows predicted `returned`, the other
  two pinned by `tests/test_exceptions_typescript_reasons.py` and
  `corpus/typescript/untraced_catcher_later_failure` only, never by a hand
  adjudication on somebody else's code; *closed by* a future lens whose rows
  exercise them, and there is nothing to build. (2)
  **`tests/test_acceptance_scripts.py` is watched, not acted on** — 315 lines
  at rung 3 and the file every future E-branch instrument change grows;
  *closed by* the seam, when a slice's instrument work takes it past the gate.
  It did not this slice. (3) **The rung-3 T0 hand read's row 1 calls the
  untraced catcher "a library `try`"** where it is a `.catch` chain on the
  promise TanStack Query's retryer returned; *closed by* nothing — the locked
  table keeps its words and rung 3's §3 states the correction in place. (4)
  **`Index.left_frame` is per-serial and outermost**, so a window-2 rethrow
  that stayed inside traced code reads a window-1 root — rung-2 behaviour,
  untouched, and no lens has shown the shape; *closed by* a corpus case that
  pins it, deliberately not written, because a case for a shape nobody has met
  pins an invention rather than a fact. (5) **Rung 3's `lens.stamp()` wiring
  into `assemble.py`, `assemble_rung2.py` and `assemble_slice2.py` is verified
  by the slice-2 tooling test only** — new code on frozen paths, none of the
  three re-run against a store since; *closed by* a slice with honest cause to
  re-run one of them, and this slice's own assembler is a different file.
- **The `§n` convention clash in `rust/HONESTY-BLIND-SPOTS.md`.** Items 32 and
  33 cite design-spec sections as bare `§5.5` / `§5.2` where the file's own
  rule at `:27` reads a bare `§n` as `rust/HONESTY.md`'s. The attribution line
  was corrected to name §12; the two bodies were not. **Closing it** means
  settling the file's `§n` spelling once, in the volume split P15 already
  requires. *Cost if wrong:* a reader follows `§5.5` to *Exit status*.
- **Five carried smalls in the tests and the instruments.**
  `typescript/test/graph.test.mjs` reads STATIC imports only, so a relative
  dynamic `import('./x.mjs')` is invisible to it — one assertion per file would
  close it, and nothing in `src/` uses one today.
  `tests/test_ts_ingest_caps.py`'s counted prose is asserted by nothing, where
  `tests/test_ts_live.py` now derives its 103 and 146 from the file.
  `typescript/acceptance/e12p_h8.py`'s clause-1 regex raises `AttributeError` on
  a reworded §1.9 (`:304-306`) where clause 5 guards the same pattern at `:346`;
  the file has now taken its reading. `typescript/acceptance/e13_report.py` is
  **108** lines against ruling P2's "< 100", the pre-measurement instrument fix
  of record §2.3 having added to it — named rather than trimmed to fit, P2's
  figure being a size intent and not a gate. And
  `typescript/acceptance/transform_diff.mjs:142` symlinks `node_modules` into
  the base checkout and never removes it; the checkout is a session directory
  outside the tree, so nothing tracked is touched. *Cost if wrong:* a cycle
  reintroduced dynamically passes the test that exists to refuse it; a count
  that drifts silently; a rewritten record section crashes an instrument instead
  of refusing it; a stale symlink in a scratch checkout.
- **The two lock-test minors from Task 0.** `tests/test_acceptance_s5_debts_lock.py:391-392`
  asserts `locked_bytes == original_lock_bytes + amendment_bytes`, an identity
  that holds for any two inputs — its docstring and its commit message claim it
  catches a removing amendment, and it does not (the sibling row-identity test
  does); and the §1.7 amendment's dated marker is not pinned the way rung 3's
  precedent pins its `Amended <date>` string. **Closing them** means deleting
  the vacuous assertion or making it fall on a deletion, correcting the claim,
  and pinning the marker. *Cost if wrong:* a lock test that reads as stronger
  than it is — the same shape `rust/tests/acceptance_rung3.py:211-221` carries.
- **`ORIGINAL_COMMIT = 9b4c0fe` is a feature-branch commit**, so a SQUASH
  merge would make the amendment tests skip by name; sensorium merges are merge
  commits (`e6f5035` is the precedent) and the PR body says so too. *Cost if
  wrong:* the record's lock tests go quiet on `main` instead of failing.

### Files near the ceiling

The 800-line gate (`tests/test_ceiling.py`) covers every tracked `.py`, `.rs`,
`.sh`, `.md`, `.mjs`, `.ts` and `.tsx`. These are the ones this slice wrote in,
whose next edit must take a seam rather than a paragraph:

- **`rust/HONESTY-BLIND-SPOTS.md` 800** — at the gate exactly; its next entry
  opens a volume (P15).
- **`src/sensorium/query/flow_cmd.py` 799**, **`README.md` 799**,
  **`typescript/src/rt.mjs` 798**, **`typescript/HONESTY.md` 794**,
  **`rust/…/src/lines/facts.rs` 778**, **`rust/…/tests/golden.rs` 788** and
  **`rust/…/tests/edges.rs` 784** — the last two are why ruling **R8** sent this
  slice's Rust goldens to a new file, `tests/unbound.rs`. `README.md` took this
  slice's two new sentences **net-zero**, trimming the same sections.
- Other tracked files sit between 770 and 800 and are not listed: a hand-kept
  list of the files somebody remembered is the very thing `test_ceiling.py`'s
  pattern scope replaced. The census is one command:
  `git ls-files -- '*.md' '*.py' '*.mjs' '*.ts' '*.rs' '*.sh' | grep -v '^docs/superpowers/' | xargs wc -l | sort -rn | head -30`.
- **This file**, twice. Measured before it was written: the S5 rung-3 section
  was cut to [`CARRIED-DEBT-ARCHIVE-9.md`](CARRIED-DEBT-ARCHIVE-9.md); then
  this section's own review round would have taken the file to 804, so the
  rung-4 section went to
  [`CARRIED-DEBT-ARCHIVE-10.md`](CARRIED-DEBT-ARCHIVE-10.md). Both pure moves,
  both verified byte-identical, and neither paid for by trimming content.

### Deferred minors, per task

Small, named, and none measured away; the ledger holds every one and this
paragraph is the roll-up. The eleven already stated above under *Deferred by
ruling* — the two lock tests, `e13_report.py`, `e12p_h8.py`,
`transform_diff.mjs`, `graph.test.mjs`, `test_ts_ingest_caps.py`,
`flow_cmd.py`'s dead input, the `§n` clash, `_MORE`, `find_in_value` and
`sites._anchor` — are not repeated. **In the instruments:** `e12p_pre.py:51-52`
keeps an orphaned comment fragment; `rows_of2` (`e12p_report.py:111`) silently
drops a row-shaped line it cannot parse and counts no unparsed rows, which is
defect 3's own failure mode in shape;
`test_every_predicted_number_is_read_from_the_record` moves only N = 6 of about
fifteen predictions; the dry-run `e6tsp.json` of the procedure task was not
saved (the measurement re-ran it). **In the recorder:** `naming.mjs` exports
`UNNAMED` and `ask` with no importer (a plan-mandated surface) and its header
comment says `rt.nameProvider` is *the only way* where `setProvider` is an
ungated export; `positions.mjs` keeps a JSDoc-type reference to
`transform.mjs`'s `Splicer`, a type-level cycle only; `census_deferred.mjs:110`
calls `statSync` unguarded on a mistyped root, so an ENOENT escapes instead of
the script's exit-2 path; `transform.mjs:336-343`'s `isFocusedFrame` is a third
copy of the parent walk `enclosingFunction` now factors. **In Rust:**
`unbound_of`'s `_ => {}` and `is_block_like` are two lists kept in step by a
comment, so an eleventh statement variant would silently unbind nothing;
`line_unbinding_fragment` renders its list with a manual loop where
`common/mod.rs` uses map/join; `LinePayload`'s own doc (`line.rs:74-79`) never
names the second list; the tag-0 and unknown-tag refusals still say `delta`
(`:240,244`), a deliberate hold; `UNBOUND_MARKER = Value::Null` is a value-space
sentinel, documented; `tests/unbound.rs:24` cites a test by a stale name, and
the task's report and commit say eleven unit tests where there are ten. **In the
tests and fixtures:** `tests/test_corpus_harness.py` imports a collected test
module (`tests.test_corpus`, executed twice per session, harmless) where the
repo's precedent is a non-collected helper; `test_ts_honesty_prose.py:199`
silently continues on a TypeScript entry citing nothing path-shaped (zero such
entries today; the Rust half prints its uncited list, and the symmetric print
would close it); `focus_async`'s third-needle comment claims more than the
needle pins; the `is_clipped` fixture pair does not discriminate the module's
rule from a bare `INSPECT_MORE.search` (the guarantee is source-level — no `re`
in `build.py`) and `_base_truncated` assumes the replaced capture contributed 0,
unasserted; `v40:313`'s `expect_absent` duplicates `expect_count` and pins a
double space; `"/finally_return"` is the corpus's first leading-slash filter and
must **not** be normalised back. **In the prose:** ~~`typescript/README.md:34`
lists three `escape.mjs` exports where there are now four~~ — **closed at this
task's own fix round, commit `48e3cb7`**, which added `deferredExit(ts, fn)` to
that row, so the ledger carried it OPEN after it was shut;
`docs/query.md:291-292` has a subject-verb slip left by the *0.3.0 and later*
rewording; `rt.seal.test.mjs:226-250`'s fallthrough test body is hand-written,
so the file header's *every body generated from the real transform* is slightly
overstated; ragged reflow at `typescript/HONESTY.md:62-63` and `:557-558`; the
README's TypeScript `finally` sentence sits in the tier-generic intro, true but
vacuous at the call tier; the two CHANGELOG pointer notes are paragraphs rather
than the *one sentence* their brief asked for; rung 4's *Deferred minors*
paragraph was closed by one appended sentence rather than per-clause strikes,
which is readable and complete but not the file's usual form. **Five more from
the E6-TS procedure task:** ~~`docs/corpus.md:169` still leads
`focus_catch_binding`'s entry with *(HANDLED, …)*, the very vocabulary A13
corrects~~ — **closed 2026-09-12** in this slice's final fix round, where the
entry was made to read *(SWALLOWED, …)*; `e6ts.py`'s written procedure runs to
four sentences where its brief
asked three; and `typescript/HONESTY-BLIND-SPOTS.md` carries a 98-character line
at `:43`, a `--` at `:444` where the file uses an em dash, and a line break
inside inline code at `:454`. **In the record:** ~~§3.6 says *all nine steps
exited 0* against seven recorded statuses and two output files~~ and ~~§3's
*seven gated … six PASS* arithmetic wants the sentence that E6-TS″ is the
amendment's extra cell~~ — **both closed 2026-09-12** in this slice's final fix
round; the instrument-fix commit also touched `e12p_h8.py`, named in §2.3
and not in the dispatch wording; and two preflight readings of the same disk say
78 and 79 GB, taken in different minutes. **And four about task REPORTS rather
than about the tree**, kept so the roll-up is complete: a report called
`census_matches` "a scratch one-off" after it was committed; a RED count of "8
failed, 1 passed" was the `--test unbound` target's, not the workspace's; one
task took four commits where its brief asked for one; and the renamed
`bindings.test.mjs` case uses its own wording.

### Process lessons

- **A hand adjudication must be written in the vocabulary of the command it
  pre-registers.** E6-TS′ STOPped because `focus_catch_binding` was adjudicated
  in `grep --kind HANDLED`'s kinds and the clause was pre-registered against
  `exceptions`'s output. The two commands are about the same event and do not
  share a rule; the second's own documented rule was derivable on day one, and
  reading it was the whole of the fix.
- **A plan's line numbers move; locate by text.** Every task met at least one
  `file:line` shifted under an earlier task's edit — this one included, whose
  brief cited `README.md:550` for a token at `:547`. A brief citing a line
  number cites a guess about the tree at dispatch time; the text it quotes is
  the durable half.
- **`tsconfig` covers `acceptance/**/*.mjs`, and no Python test type-checks
  one.** Eighteen `tsc` errors stood in `transform_diff.mjs` from the commit
  that added it until a later task's implementer ran `npm run check`. A gate
  nothing else runs is a gate nobody runs.
- **A new corpus directory name can be a substring of an existing vitest
  filter.** `focus_finally_return/` silently joined rung 2's `finally_return`
  case, which filtered with the bare string, so that case recorded two test
  files in unstable pid order and failed about half the time. An intermittent
  failure with an unknown cause is worth the hour it takes to find the cause
  BEFORE the measurement: the disposition rule you can write afterwards is
  weaker than the one you can write once you know.
- **A count corrected inside a task can re-drift inside the same task.**
  `tests/test_ts_ingest_meta.py`'s "777" was corrected to 781 and the file was
  785 by the task's end. A number about a file belongs in an assertion its own
  length feeds, not in a sentence.
- **An instrument defect found before any number is a fix, recorded in §2.3;
  found after, it is a finding.** `e13_report.py`'s clause 2 was gated on the
  wrong input file, caught in review before any endpoint ran, then fixed,
  committed, covered by a test and written into §2.3 with the mutant that
  failed without it. The same defect an hour later would have been a finding
  and the number would have stood.
- **A ruling can be wrong mid-slice, and it is corrected by a numbered
  successor, never by an edit.** P13 corrects P7's `else if` clause and says so
  in its first line; P11 supersedes P10's mechanism and keeps its disposition.
  A ruling edited in place leaves a ledger that cannot show what was believed
  when the work was done.
