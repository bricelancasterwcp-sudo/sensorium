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

**The queue-buttoned-up slice moved 2026-09-10** — that section is
[`docs/CARRIED-DEBT-ARCHIVE-5.md`](CARRIED-DEBT-ARCHIVE-5.md), wording, order
and strikes unchanged, so a deferred item there is still open unless it is
struck. Measured before it was made, the way the rule asks: this commit's
four residual rows (ruling R46) were drafted at **34** lines against a live
file of **785**, which would have taken it to **819**, over the ceiling, so
the oldest section was cut rather than the ceiling discovered. This file
keeps the newest section, and the next slice's section is appended here.

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

- ~~**E6″ — a NEW pre-registration, not a second look at E6′** (*ruling R32*).
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
  last thing that touched the lens.~~ — **Measured 2026-09-10, S5 slice 2:
  E6″ PASS on all five clauses**, all four commitments kept (record
  `docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md` §3.11, §4.3).
  Manifest **748 OK / 0 FAILED** before and after, ten of ten plain runs at
  `372 passed (372)` / `4278 passed (4278)` with nothing dropped, **0** markers
  over the 2 cache directories that exist, the wrapper **absent**, and the
  after arm's median **22.1136 s** inside the band **[21.9834, 22.3652]** —
  the before arm's own median **22.1743** ± its own range **0.1909**. The
  after arm is **0.0607 s faster**. What this closes is one session on one
  lens with one recorder; the record's §5 gaps 8 and 9 say what it does not.
- ~~**The E10 design question — a Node converter on `node:sqlite`, or a binary
  wire** (*ruling R33*). Full-suite `ingest` costs **45.5293 s** (n=3) against
  a plain wall of 22.5925 s — ×2.02, above E10's bound, which its own rule
  made design input and not a STOP. The commitment is to answer it the way the
  spike was answered: **pre-registered**, with the endpoint written before the
  instrument, and on both workloads — the full suite AND the one file a
  debugging loop actually pays for (**0.3638 s**, n=3), because a converter
  rewritten for the suite number could easily be no better on the one that
  matters. The second reading of the same effect is in the record's §5 gap 13:
  the call arm's driver wall climbed 45.0 → 70.3 s run to run while its
  harness wall never moved.~~ — **Answered 2026-09-10, S5 slice 2: the
  converter stays Python.** Pre-registered on both workloads as the commitment
  said, and both PASS on the slice's final converter: **E10′-suite 16.3859 s**
  (n=5) against the pinned **22.5925 s**, and **E10′-file 0.1648 s** (n=5)
  against **0.4002 s** — the one clause allowed to STOP the ladder, which did
  not fire. Two levers did it, `TraceWriter(durable=False)` and a streaming
  spool reader: **2.7913×** on the suite, **2.1990×** on the one file, and the
  heaviest worker's peak resident **2,269,696 kB → 290,948 kB** on the suite
  cell. **Arm B — a Node or Rust converter — was never built** and is not
  raised (Brice's ruling, spec §10.1). The second reading this bullet named is
  now a pair on record too: one call run's harness wall **25.2619 s** against
  a driver wall **38.8595 s** (record §3.11), below the lowest of rung 1's
  five.

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
- ~~**The recorder joins a describe chain with ` > ` and vitest's JSON reporter
  joins it with a space** (record §5 gap 10). E9's rule attaches no threshold
  to its 20-name sample, so this gates nothing; whether §3.4 should emit
  vitest's own `fullName` spelling is raised and unsettled.~~ — **Decided
  2026-09-10, S5 slice 2 (design §5, "Decisions recorded without work"): the
  join stays ` > `.** It is vitest's **own console spelling** for nested
  names — what the consumer reads in a failing test's header — and the
  space-joined `fullName` is the JSON reporter's spelling, not vitest's.
  E9's rule attaches nothing to it either way, so nothing was measured and
  no code moved; the question is answered, not still open. *(Struck
  2026-09-10 in the final fix wave: the row was decided by the slice that
  raised it and still read "raised and unsettled".)*

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
- *Task 5*: `_meta()` mutates builder state (`bases.pop`); ~~the spool is
  materialised whole (memory linear in spool size — what E10 measures)~~
  *(struck 2026-09-10, S5 slice 2: `spool.read` streams — BOOT from line 1,
  every later record yielded — and the heaviest worker's peak resident fell
  **2,273,996 → 280,408 kB**, 8.1096×, on the big-spool cell; record §3.8)*;
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

**Four residuals from the fix wave's re-review, parked whole** (*ruling
R46, 2026-09-10*). The re-review at `c1712c9` found all fourteen R37–R44
findings addressed and no Critical or Important breakage, with four
residuals left standing; R46 chose one docs-only commit over a second fix
wave, and this is that commit.

- ~~**`typescript/src/hook.mjs` `load`** — under `node --test` a `.tsx`/`.jsx`
  file now fails to load at all: Node's own loader throws
  `ERR_UNKNOWN_FILE_EXTENSION` from `nextLoad` before this hook ever sees
  the file, where the pre-R37 hook had transpiled it with `jsx:
  react-jsx`. Such a file could not load under plain `node --test` either
  way, so no passing suite is broken by this. Queued: decide whether this
  hook should carry JSX at all, and test both extensions either way.~~ —
  **Decided and tested 2026-09-10, S5 slice 2 (spec §4.2, S12): no JSX in the
  hook.** `.tsx`/`.jsx` are outside **Node's own** scope under `node --test`,
  not an exclusion this recorder makes, and so not counted as one. The control
  `probes/nodetest/controls/jsx.tsx` pins it by measurement:
  `ERR_UNKNOWN_FILE_EXTENSION` on the hooked side and the plain side alike,
  `same: true` (record §3.10). A consumer who wants JSX under `node --test`
  needs a Node feature, not a recorder feature.
- ~~**`typescript/src/hook.mjs`** (pre-existing, not R37's doing) — an
  eligible `.mts` is transformed but never type-stripped: `STRIP` holds
  only `.ts`/`.tsx`, so Node throws a `SyntaxError` on the file's first
  type annotation. Likely fix: stop naming extensions and return Node's
  own reported format instead — `module-typescript`, which Node ≥ 23.6
  strips natively — measured on node v24.16.0 that `nextLoad` already
  reports exactly that for an ESM `.ts`. Queued with a test per
  extension.~~ — **Fixed 2026-09-10, S5 slice 2 (H1, `05e5338`), by exactly
  the likely fix this row named**: the hook stops naming extensions, returns
  Node's own reported format and erases nothing; Node strips. Tested per
  extension by four probe files under `node --test` — `.ts`, `.mts`, `.mjs`,
  `.cjs` — plus two controls, `check.mjs nodetest` reading **25 checks, 0
  failures** (record §3.10). The `.mts` probe records `M1 an .mts is stripped
  by Node and recorded`, which is the row this bullet said did not exist.
- **`src/sensorium/query/info_typescript.py:27-29`** — the module
  docstring said an older converter's trace "prints none of these
  lines"; after R38 the `tests:` line is gated on the trace's own TASK
  rows, not on any meta key, so it is not among the lines a keyless trace
  suppresses. Corrected in this commit.
- **`typescript/HONESTY.md:131-134`** and the spec's R17 row
  (`docs/superpowers/specs/2026-09-09-sensorium-typescript-recorder-design.md`)
  — "impossible under vitest's unique full names" was over-strong once
  R39 made `#k` per CONTAINER: a `threads`-pool worker can run several
  test files (`tests/test_ts_live.py` asserts the `test_files` case), so
  two of those files sharing one full title in the same container yield
  `name` and `name#2`. Corrected in this commit.

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

## 2026-09-10 — S5 slice 2 (Python 0.9.1 / sensorium-ts 0.1.1)

The slice that answers the two things rung 1 shipped open — E6′'s STOPped
timing clause and E10's design input — and fixes what the `node --test` path
was getting wrong. Ten plan decisions (P1–P10), and — read off the slice's
SDD ledger rather than counted by hand — **eleven** distinct controller
rulings, two of them stated twice (once in a task's risk table and again in
its bullet), one clause each:

1. the equivalence gate's side B stays the tip after Task 3; Task 5's R45
   edit touches only the zero-spool refusal and is not re-gated;
2. the global `sensorium` tool is not reinstalled from the worktree until
   Task 4's side A has converted, so Arm 0 and side A are not the new code;
3. `ingested.json` is dropped from all three spool copies (the marker makes
   `ingest` refuse and carries no measured data);
4. the timed region keeps `rss_run.py`'s ~16 ms start-up in **every** stage,
   so the bound stands as written and no threshold moves;
5. the 4.0 load guard admits repetitions on a jobs-16 cell's own decaying
   load — the pre-registered guard stands and the readings are in the JSON;
6. Task 3 absorbs two record minors and builds `TraceWriter.discard()`
   (rollback then close) behind `Builder.abort()`;
7. the streaming reader's UTF-8 refusal names the **line**, where the old
   reader named the file;
8. `sensorium diff` MATCH compares causal structure and row counts and not
   recorded values — so E10′-eq stands on its own pre-registered rule, and a
   NEW ungated check, E10′-eq-content, is pre-registered before it runs;
9. Task 7 adds `tests/test_ts_ingest_refusals.py` to CI's `typescript` job
   file list, for symmetry with the matrix jobs' bare `pytest -q`;
10. Task 6 re-runs `npm run probe:nodetest` once to capture `h-probes.json`
    for the assembler, the H-probes verdict staying Task 5's;
11. Task 7 absorbs three of Task 6's minors as edits and writes the rest
    into the record's §5 and this ledger.

Every one that moved the design's text is a dated row in §12 of
`docs/superpowers/specs/2026-09-10-sensorium-s5-slice2-design.md`, and the
`Ruling:` lines themselves are in
`.superpowers/sdd/2026-09-10-sensorium-s5-slice2/progress.md`. *(The count
read "Seven" until the final fix wave; this section's own process lesson is
that a summary count goes stale, so it is derived here and the list is what
a reader checks.)* Every
number below is copied from
`docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md`, whose §1 was
byte-locked before any of this code existed.

**Measured before it was written, the way the rule asks.** This section was
drafted at **250** lines against a live file of **452** — 415 at the
slice's start, plus **37** the strikes above added — which took it to
**703**, under the 800-line ceiling. Nothing was cut, and no volume
was opened. *(Re-measured 2026-09-10 after the task's review: the fix wave
added **19** lines here, so the section is **269** and the file **722**. A
line count stated in a paragraph goes stale the next time the paragraph's own
section is edited — this file's header has recorded that happening to three
volume counts — so the number is re-taken rather than left standing, and both
readings are kept. Re-measured a third time the same day, after the FINAL
review's fix wave struck the ` > ` row, enumerated the rulings above and
amended the version-token row: the section is **313** and the file **774**,
this sentence's own four lines included — writing the count moved the count,
which is the lesson in one line. Still under the 800-line ceiling.)*

### Settled

- **E6″ — PASS on all five clauses.** One guarded session on the lens (five
  plain runs, one call-tier recording, five plain runs, the manifest last):
  manifest **748 OK / 0 FAILED** before and after, ten of ten plain runs at
  `372 passed (372)` / `4278 passed (4278)` and **nothing dropped**, **0**
  `__srt` markers over the 2 cache directories that exist,
  `node_modules/.sensorium` **absent**, and the after arm's median
  **22.1136 s** inside the band **[21.9834, 22.3652]** — the before arm's own
  median **22.1743** ± its own range **0.1909**. The after arm is **0.0607 s
  faster** than the before arm. E6 is closed for this recorder on this lens,
  and the rung-1 spec's §11 carries the dated line saying so.
- **E10′ — PASS on all three gated clauses; the converter stays Python.**
  **E10′-suite 16.3859 s** (n=5) against the pinned **22.5925 s** wall,
  **E10′-file 0.1648 s** (n=5) against **0.4002 s**, and **E10′-eq 372 MATCH
  / 0 DIVERGED / 0 REFUSED** over the same set converted twice. Two levers,
  each its own commit with its cells measured before the next was written:
  `TraceWriter(durable=False)` (one transaction per trace,
  `synchronous=NORMAL`, committed in `close()`) and a **streaming spool
  reader** (BOOT from line 1, every later record yielded, `TraceWriter.
  discard()` behind `Builder.abort()`). End to end **2.7913×** on the suite
  and **2.1990×** on the one file, with the heaviest worker's peak resident
  down **2,269,696 → 290,948 kB** on the suite cell.
- **And the trace did not move.** Beside the gate, ungated and
  pre-registered *after* the gate was read so it could not touch its verdict:
  **E10′-eq-content**, every row of `events`, `frames`, `code_objects`,
  `tasks`, `fingerprints`, `task_fingerprints` and `output` compared column
  for column across all 372 pairs — **372 / 372 identical**, the only `meta`
  key differing on any pair being the minted `run_id`. The instrument was
  mutation-checked before it ran: a changed column, a deleted row and a
  changed `meta` value were each caught and named.
- **H1 — the loader hook returns Node's own format and erases nothing**
  (`05e5338`). It classified by extension and forced `format: 'module'`; it
  now asks `nextLoad` and takes the answer, so **Node** strips and the
  recorder splices. The `.mts` that was instrumented and never stripped now
  records.
- **H2 — one probe per extension, two controls, under `node --test`**
  (`761c935`). `.ts`, `.mts`, `.mjs`, `.cjs` and the controls `enum.ts` and
  `jsx.tsx`: `check.mjs nodetest` reads **25 checks, 0 failures**, and both
  controls fail **identically** hooked and plain
  (`ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`, `ERR_UNKNOWN_FILE_EXTENSION`,
  `same: true` twice). The controls discriminate, measured: against the
  pre-fix hook `enum.ts` **loaded** under the recorder and failed plain.
- **H3 / R45 — a run that recorded nothing says why when the tallies know**
  (`5af2def`). Where every tally reads `files_transformed: 0` and the
  exclusions are non-empty, the refusal names them by reason with counts
  (`commonjs x2, parse-error x1`), the ES-modules-only clause appended only
  when `commonjs` is among them (plan P6, R27's precedent). A partial suite
  keeps the old sentence: a real recording failure is not an exclusion.
- **H4 / R47 — `hook.mjs:98` became `hook.mjs` `load`** (`90d6380`). A line
  number in a ledger is a citation that goes stale on the next edit; H1 moved
  those lines in this same slice. No `hook.mjs:<line>` citation remains in
  any document this slice can edit.
- **The `loads` fix** (`ecdc631`, spec §2.3). `assemble.py`'s `arm_stats`
  zipped the arm's `loads` against its **kept** walls while `loads` held a
  row per attempt, so a dropped run would have misaligned every later
  reading. Rung 1 dropped no run, which is why the misalignment stayed
  latent; it is filtered now, before `e6pp` used the assembler.
- **The R45 sentence's ordering, and the refusal tests.** Reasons are
  rendered `sorted()` so the sentence is stable across dictionary order, and
  `tests/test_ts_ingest_refusals.py` is now named in CI's `typescript` job
  file list beside the rest of the recorder suite (the matrix jobs' bare
  `pytest -q` already ran it; the list is for symmetry).

### Deferred, with rulings

Each row is a decision that was made rather than a thing forgotten, with the
number or the ruling that made it and what it costs if it was wrong.

- **A2, largest-first dispatch — not built.** Spec §3.3 conditioned it on
  A1 + A3 leaving the suite cell above the bound; a3's 0d read **16.5088 s**,
  **6.0837 s** below the 22.5925 s bound. *Cost if wrong:* a converter faster
  than the verdict needed is not built, and the numbers say exactly how much
  headroom was left.
- **A4, the per-record Python cost — not built**, on the same condition and
  the same number. *Cost if wrong:* the same, plus the attribution question
  A3 raised (which share of its 1.25 s is decode, allocator or collector)
  stays unanswered.
- **Arm B — a Node or Rust converter — never built** (*Brice's ruling
  2026-09-10, spec §10.1*): Arm B stops at the report, a Node converter is a
  later slice. The suite clause PASSed, so nothing asked for it. *Cost if
  wrong:* none this slice can see; the ladder's rungs are on record for
  whoever raises it.
- **The non-durable writer's transient WAL is unmeasured at the job count
  the gate ran.** Measured once at `--jobs 1`: a **335,895,392-byte** `-wal`
  beside a **333,832,192-byte** database, so transient disk is ≈ **2×** per
  in-flight trace, and at the default job count it is the sum over the
  workers building at that moment. 63 GB were free and nothing came near the
  disk. *Cost if wrong:* this box has run at ~3 GB free on `/`, and a
  full-suite conversion there could fail on space in a way no cell here
  would predict.
- **`Builder`'s class docstring does not say the build is non-durable by
  default** (T2 M3). One sentence. *Cost if wrong:* a reader of the class
  learns the default from the constructor signature instead.
- **A `Spool` that is never iterated leaves its handle to the collector**
  (T3 M3) — a `ResourceWarning` under `-W error`, not a leak in any shipped
  path. *Cost if wrong:* a future caller that constructs and abandons spools
  in a loop holds file descriptors longer than it should.
- **`torn_tail` still has no production consumer** (T3 M7, pre-existing).
  The streaming reader fills it as it walks; nothing reads it. *Cost if
  wrong:* a truncated spool converts with the fact recorded and unreported.
- **`sensorium diff` exit 0 counts its leniencies as MATCH** (T4 M5):
  "MATCH modulo location" and "nothing to compare" are not separated from a
  plain MATCH by the gate's instrument. Closed in practice by
  E10′-eq-content's 372/372 — the rows are identical, so no pair could have
  been leniently matched — but the instrument still cannot tell them apart.
  *Cost if wrong:* a future gate on a set where the leniencies fire reads
  MATCH for something weaker.
- **`probes/check.mjs` collapses duplicate probe names and pins no spool
  count** (T5 M3). It asserted 3 spools here because the run produced 3.
  *Cost if wrong:* a probe file that silently stopped producing a spool could
  be masked by another with the same name.
- **No test discriminates the `sorted()` in R45's reason rendering** (T5 M2):
  a mutant that drops it survives on any single-reason fixture. *Cost if
  wrong:* the sentence's ordering becomes dictionary order and the refusal
  text varies run to run.
- **`e10p.sh` records a peak RSS of `0` silently** if the `maxrss_kb=` line
  fails to parse (`${maxrss:-0}`, T1 M3). Every repetition of every cell
  parsed, and each report says so. *Cost if wrong:* a future rung reads a
  zero as a measurement.
- **A dropped plain run STOPs E6″'s suite clause outright** (T6 M2), so the
  "fewer than four usable walls" STOP-by-instrument is nearly unreachable —
  the conjunction fails first. It is the conservative direction (an
  instrument that cannot manufacture a PASS), and it was not disclosed in the
  pre-registration. *Cost if wrong:* a future session reading the rule
  expects a graceful degradation it will not get.
- **The five E6″ clauses cannot see a failed call run** (T6 M3). The call run
  is the contamination *source* and deliberately outside the clause (record
  §5 gap 10); its greenness was checked by hand — call row ok, exit 0, 372
  spools. *Cost if wrong:* a session whose recording half-failed reads as a
  clean PASS unless someone looks.
- **The manifest's sha256 is recorded, not enforced** (T6 M4). `e6pp.sh`
  derives the expected OK count from the manifest's own `wc -l`, so it writes
  the manifest's sha into the cell to anchor *which* 748 — but nothing
  compares that sha to the pinned value automatically. *Cost if wrong:* a
  truncated or swapped manifest passes the count clause and the mismatch is
  visible only to a reader who checks the sha by eye.
- **`assemble_slice2` can emit `null` with an empty `dropped`** on two
  branches (T6 M5), where the file's own rule is that a missing cell is
  `null` **plus** a reason. *Cost if wrong:* a cell reads as absent with
  nothing saying why.
- **The band's width is a property of the session, not of the rule** (record
  §5 gap 8): ±0.1909 s here against the ±0.4085 s spec §2.2's worked example
  derives from E1′. A PASS here is a claim against a tighter yardstick, not a
  tighter claim, and sensitivity is not comparable across sessions. A session
  wanting stable sensitivity would pre-register a floor on the band's width —
  which §2.2 deliberately refused, a chosen width being the thing it refused.
  *Cost if wrong:* a later E6 whose control arm is noisier passes a clause this
  one would have failed, and the two PASSes get read as the same claim.
- **"Under 4.0" is not "idle"** (record §5 gap 9). Ten of the eleven guarded
  readings were above 3.0 and only the before arm's first run was cold
  (0.35). The asymmetry runs **against** a contamination finding — the arm on
  the quieter box is the slower one — but a guard that wanted the arms
  ambient-matched would wait for a *return* to a baseline, not for a ceiling.
  *Cost if wrong:* on a session where the asymmetry ran the other way, ambient
  load and not the recording would be the thing the band measured.
- **The instrument's timed region includes its own wrapper's start-up**
  (record §5 gap 1), now **8.3%** of the gated one-file cell (0.0137 s of
  0.1648 s). Both walls fall the same side of both bounds, so no verdict
  turns on it. *Cost if wrong:* a bound within 10% of the truth would be
  decided by an interpreter start-up; a later instrument should time the
  child alone or say which wall the rule reads.
- **The record's `### 3.6`–`### 3.11` shadow the spec's own §3.6/§3.7
  numbering** (T3 M4). Every citation that could be ambiguous is qualified
  "spec §3.x" in place; the headings themselves were not renumbered because
  §1 quotes the spec's and §1 is byte-locked. *Cost if wrong:* a reader
  follows "§3.7" to the wrong document.
- **Job-count independence of the converter's output is an inference, not a
  measurement** (T4 M8). Both sides of the equivalence gate ran at the
  default job count, so the 372 MATCH says nothing about whether `--jobs 1`
  and `--jobs 16` write the same trace. Nothing in the converter is
  job-count-dependent by construction. *Cost if wrong:* a dispatch change
  (A2, if it is ever built) could move output without this gate noticing.
- **Rung 1's results file was written by an assembler that no longer
  exists** (record §5 gap 11). The `loads` fix landed after that file was
  produced and it was **not** regenerated: nothing in it moves (rung 1
  dropped no run), and re-running it today would change a locked record's
  evidence rather than reproduce it. *Cost if wrong:* none measured; the
  provenance is the point and it is written down.
- **`assemble.py`'s `load()` leaks a filesystem path into an absent-file
  reason**, where every other field is redacted. No absent cell occurred, so
  no path shipped. *Cost if wrong:* one box path in a committed results file
  — which is exactly what `offenders()` exists to refuse.
- **`docs/TRACE-FORMAT.md`'s `capabilities.err_flow` sentence still names
  `sensorium-ts 0.1.0`**, and so does
  `corpus/typescript/exceptions_refused/questions.yaml:12` ("no TypeScript
  disposition rules exist in 0.1.0", in the case's `truth` prose) — **two**
  version tokens this slice left standing, not one. *(Amended 2026-09-10 in
  the final fix wave: this row claimed to be the only one.)* Both are true
  of 0.1.0 and still true of 0.1.1 — the same rung still owes the
  disposition rules, and `capabilities.err_flow` is false in both — and the
  corpus file is left alone because no test reads that prose, and
  `docs/TRACE-FORMAT.md` sits at **799** of 800 lines, which this slice
  pre-committed not to open (plan Global Constraints). *Cost if wrong:* a
  reader on 0.1.1 goes looking for a version statement that has not moved
  because it did not need to. The four others the first pass missed were
  taken 2026-09-10 rather than deferred, so this row — in its two places —
  is the whole of the deferral: `typescript/README.md`'s
  "Arguments are unread" and `typescript/HONESTY.md`'s `capabilities.err_flow`
  sentence are now **version-free** ("in this version"), because both describe
  the package as it is rather than a recording; and `typescript/README.md`'s
  "Not yet" clause and `typescript/HONESTY.md`'s "a trace this 0.1.0 runtime
  wrote" **keep `0.1.0` and name `0.1.1` beside it**, because both are about
  traces a 0.1.0 runtime actually wrote and both versions declare the same
  capability.
- **`task_name_basis` is spelled `lexical` in prose and `title` on the wire**
  (record §5 gap 6). Same fact, two spellings; the checker asserts the value
  the recorder writes. *Cost if wrong:* a reader goes looking for a third
  basis.

The per-task minors this slice did not fund are in the slice's SDD ledger
(`.superpowers/sdd/2026-09-10-sensorium-s5-slice2/progress.md`, each task's
"Minors deferred" line), archived with the worktree.

### Process lessons

- **Two instrument defects were found only by running the instrument, and
  both were found before the number was.** The first H-probes run STOPped on
  `ext:cjs:tally` with two orphan tallies instead of one: `controls.mjs` had
  spawned its hooked side with `SENSORIUM_MANIFEST_DIR` inherited, so a
  control's child wrote a tally into the run's own manifest directory and
  read as a second child that recorded nothing. Nothing about the recorder
  was wrong; an instrument that shares a directory with the run it measures
  is. It was fixed, the run repeated from zero, and the first run's only
  reading is the defect. The second was caught by mutation: `e6pp_report.py`
  had a test that compared the after arm's **wall** where the rule compares
  its **median**, and a mutant that swapped them survived until the mutation
  round found it — fifteen mutations, one real gap. An instrument gets the
  same evidence standard as the thing it measures, or the measurement is
  worth what the instrument's tests are worth.
- **A prediction can fail in the fast direction, and that is still a
  falsification.** Six of the ten per-cell predictions this ladder
  pre-registered did not hold as written, and **five of the six were faster
  than predicted** — A1's "0e unchanged" by a factor of 2.2004, A3's "wall
  within noise" by about 1.25 s on each large cell. The temptation each time
  is to read a happy number as a held prediction; the discipline is that the
  prediction said something specific and the cell said something else, so the
  prediction is falsified and the record says which way. What the misses
  bought is the diagnosis they forced: the one-file spool was
  commit-*dominated*, and a memory lever moved the wall as well as the bytes.
- **Check that two numbers are the same kind of number before naming their
  difference a finding.** Rung 1's E10 reading and this slice's Arm 0 both
  measure "full-suite ingest", and neither is comparable to E6″'s call run
  (n=1, unguarded within itself, over a set nothing pinned) — the record says
  so in three places rather than letting a reader subtract them. The same
  care named the wrapper's start-up as part of the timed region *before* a
  gated clause stood on it, and named the band's width as a session property
  *before* the band was read.
- **Draft, measure, then cut.** The previous CHANGELOG cut was sized by
  guessing at the entry's length and the file landed at 833. This one drafted
  the `0.9.1` entry first (**105** lines against a live file of **756**,
  which would have taken it to **862**), and only then cut — two entries
  rather than one, with the arithmetic for both written into the archive's
  own note. The same order was used for this section.
