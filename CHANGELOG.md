# Changelog

## 0.15.0 — 2026-09-13

**Secrets stop reaching disk in the first place.** Every recorder stored the
whole process environment in plaintext, at `0644`, so a trace of any program
launched from a developer's shell held whatever that shell was carrying —
`GITHUB_TOKEN`, `PGPASSWORD`, `OPENAI_API_KEY`, live. **Rule v1** replaces a
secret-*named* value with `<redacted>` at the WRITER, before anything reaches
disk, and keeps an HMAC-SHA256 of the plaintext under a per-store key so
`refocus` can still say whether it changed without being told what it changed
to; every file a recorder now creates is `0600` in a `0700` directory. This
is PART A: the environment and the file modes. Captured argument, local,
return and output values are still stored as the caps clipped them, and part
B redacts those. Python **0.15.0**, `sensorium-ts` **0.5.0**, `sensorium-rt`
**0.6.0**, `cargo-sensorium` **0.7.0**; `sensorium-transform` stays **0.5.0**,
`TRACE_FORMAT` stays **4**, the Rust spool wire stays **v3** and the
TypeScript wire **v1** — one optional meta key, no column and no record kind.

- **One rule, three implementations, one fixture.** A name is split on
  non-alphanumerics and on both camelCase boundaries and fires when any
  SEGMENT is in a 25-word set — segment-exact, never substring, so
  `MONKEY_PATCH` and `BYPASS_CACHE` do not fire and the fixture pins both
  directions. Two amendments came out of a census of 178 real environment
  names (`tests/fixtures/benign-env-names.txt`): `PWD` fires only inside a
  longer name (`MYSQL_PWD` yes, `PWD` and `OLDPWD` no) and `PGPASSWORD` fires
  by whole name, because segment-exact matching cannot see inside a compound
  word. `docs/trace-format/redaction-v1.json` holds every case and
  `tests/test_redact.py`, `rust/sensorium-rt/tests/redact.rs` and
  `typescript/test/redact.test.mjs` all read it: three implementations of one
  rule agree only on what all three are asked.
- **Three knobs, recorded in the trace.** `SENSORIUM_NO_REDACT` turns the
  rule off, `SENSORIUM_REDACT_NAMES` adds names, `SENSORIUM_REDACT_ALLOW`
  removes them and wins over `NAMES`. None of the three fires the rule — a
  knob that redacted itself would hide the terms of its own recording — and
  all three are written into `redaction` so a reader sees what the recording
  was made under (`tests/test_redact.py::test_env_honours_both_knobs`,
  `tests/test_record_redaction.py::test_names_and_allow_knobs`).
- **The key is published by content, never by an empty file** (ruling R15).
  32 bytes go into a private per-pid temporary, are written whole and
  fsynced, and only then is the finished file hard-linked at
  `<store>/redaction.key` at `0600`; a loser of the race reads the WINNER's
  file, and a filesystem without hard links falls back to an atomic rename.
  An `O_EXCL` open on the final name would be visible at 0 bytes for as long
  as the write takes. A store where the key cannot be read or created records
  `keyed: false` with `null` digests and still redacts — the fallback loses
  comparability and never loses safety
  (`tests/test_redact.py::test_a_created_key_is_published_whole_and_leaves_no_tmp`,
  `::test_a_loser_of_the_creation_race_reads_the_winners_key`,
  `tests/test_record_redaction.py::test_unreadable_key_records_unkeyed`).
- **The Rust and TypeScript runtimes never touch a key file.** Creating one
  means a directory, a temporary, a link and a race, and both are linked into
  somebody else's program: their DRIVER mints or reads the key and hands the
  hex over as `SENSORIUM_REDACT_KEY`, which every recorder DELETES from what
  it records rather than redacting — a digest of the key under the key is a
  pointless row. `rust/cargo-sensorium/tests/convert_e2e.rs::check_redaction`
  drives all four modules of that hop with one real invocation.
- **`info` says what was taken and never what it was.** The `env:` field has
  three forms — the bare hash, `(120 vars, 0 redacted)` for a MEASURED zero,
  and `(120 vars, 2 redacted: …)` with names only, first eight then `+N
  more` — and a new line under `caps:` has four: keyed (with the key's id,
  and a `key mode 0644 -- expected 0600` note when the store's own key is
  loose), UNKEYED, OFF, and `none -- recorded before redaction existed;
  plaintext throughout`, which is the one a reader most needs, because
  absence of the key is not absence of secrets. Vectors
  `v42-redaction-render` and `v42b-redaction-none`; `tests/test_info_redaction.py`.
- **`refocus` compares digests, and a check it cannot run never withholds.**
  Same key, both sides: the digests. One plaintext side: its HMAC under the
  store's key. Two keys, or no key: **unverifiable** — named on the env line,
  stamped in `refocus_licence_unverifiable`, and granted, because a check
  that could not run is not a finding against the pair (R19). A redacted
  session or harness variable keeps its exemption, since set membership is a
  judgement about the NAME (R21), and the `compared` count excludes the
  uncomparable, since a line that counts a check it did not run is lying by
  arithmetic (R22). Vector `v43-refocus-redacted-env`;
  `tests/test_refocus_redaction.py`.
- **0600 and 0700, at creation and never by a later `chmod`** — a file
  created `0644` and tightened a moment later is readable for exactly the
  moment it is being filled with what it holds. The trace, the store root,
  `traces/`, `redaction.key`, the Rust spool directory and its
  `<pid>.proc.json` / `.spool` / `<pid>.runner.json`, and the TypeScript
  spool. The converter's own `traces/` was the last directory still made
  under the process umask and is now `perms::dir_all` like the rest (R26);
  `tests/test_record_redaction.py::test_created_files_are_0600_and_dirs_0700`
  and `convert_e2e.rs::check_modes` assert it, the second over a real
  invocation. An existing file or directory keeps the permissions its owner
  chose, and Windows treats every one of these numbers as advisory.

**Documented as it landed, not as it was designed.** `docs/redaction.md` is
new — the rule, the knobs, the key, what each command prints, and the honest
limits, including that a digest is an equality identity and not a commitment,
so a redacted low-entropy value is guessable by anyone holding the key file.
`README.md`, `docs/TRACE-FORMAT.md` (§2's permissions, §4's shared optional
set, §5's capture shape), `docs/query.md`, `docs/trace-format/TYPESCRIPT-KEYS.md`,
`rust/README.md`, `rust/HONESTY.md` and `typescript/README.md` are amended to
this state. Where the code and the design differ the code is what these
describe, and the differences are filed in the design's dated amendments.

## 0.14.0 — 2026-09-13

**`refocus` reads a TypeScript trace.** The command that re-runs a recording
one flag deeper and verifies that what came back is the same execution has
had a Rust branch since rung 4 and a Python one before that; it now has a
TypeScript one. The thing a vitest recording does differently is that an
invocation is a POOL — `npx vitest run` starts as many worker containers as
it likes and each records its own trace, while the reader asked about exactly
one of them — so this branch re-runs the WHOLE invocation, as typed, and then
says which of the traces that came back is the pair and what it is claiming
about the rest. Python **0.14.0**; `sensorium-ts` stays **0.4.0**,
`sensorium-rt` **0.5.0**, `sensorium-transform` **0.5.0** and
`cargo-sensorium` **0.6.0** — no recorder moves, `TRACE_FORMAT` stays **4**
and the wire stays **v1**.

- **The pair is found in the store, by test file, and never parsed.** The
  driver stamps `refocus_of` into every trace of the re-run invocation
  (`ts run --refocus-of`, lifted into each member's meta by the converter)
  and the lookup asks the STORE which traces carry it; the driver's `run:`
  lines go to the terminal and decide nothing. The rest are SIBLINGS —
  counted on the pair line, stamped as a count, never compared, and listed by
  `runs` under the new invocation with no verdict, which is exactly what they
  have. New meta: **`harness_cwd`** (the directory the command was typed in,
  which is a third directory beside the container's `cwd` and the plan's
  `root`), `refocus_of`, `refocus_siblings`, and `capabilities.refocus`.
- **Seven refusals, all of them BEFORE the re-run.** A suite costs minutes
  and has side effects of its own, so every condition that would make the
  answer meaningless is checked first and each exits 2: `--window` (this
  recorder has no per-activation gate), a `--tier off` original, no
  `harness_command`, no `harness_cwd`, a `harness_cwd` that is gone, a `root`
  that is gone, and a REUSED WORKER — a container that ran more than one test
  file, for which "which container of a re-run would be its pair" has no
  answer at all. The count in that seventh sentence is read from the trace's
  own task ROOT frames, not from a `test_files` key the converter never
  writes under `--no-isolate`.
- **The licence says what a TypeScript pair can and cannot check.** Source
  and environment run for real, and so does the exit check — `harness_exit`
  on both invocations and `exit_self_reported` on both containers — while
  `output`, `children` and `threads` are UNVERIFIABLE, keyed on the
  recorder's own `capabilities`. Those three are printed and stamped as
  checks that could not run and they do NOT withhold: a check that could not
  run is not a finding against the pair. The environment rule names the
  recorder's own `SENSORIUM_*` variables rather than counting them, and
  harness set 1 — vitest's per-worker `VITEST_POOL_ID` / `VITEST_WORKER_ID` —
  is counted and named beside session set 1 instead of withholding every
  licence a pooled harness could earn.
- **Three corpus cases and a vector.** `refocus_match` (MATCH, exit 0,
  `siblings in the re-run: 0`, the licence granted over exactly the points it
  names), `refocus_diverged` (DIVERGED, exit 1, the divergent causal step),
  `refocus_refused_reused_worker` (refusal 7, exit 2, and a store that still
  holds one invocation); `docs/trace-format/vectors/v41-typescript-refocus-
  link.json` pins the link and the sibling count in the format.

**The slice ships `DONE-WITH-STOP`.** E15 pre-registered twelve cells before
the instrument existed and read each once, over **31** members of one real
vitest invocation of somebody else's 372-container suite (record
`docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md`
§3–§5): **H1 PASS 0/31 · H2 PASS 31/31 · H3 PASS 31/31 · H4 PASS 24/24 ·
H5 PASS 8/8 · H6 STOP 3/4 · H7 STOP 0/1 · H7′ PASS 1/1 · H8 STOP 0/1 ·
H8′ PASS 1/1 · H9 reported · H10 PASS 11/11**. **None of the three STOPs is
about the tool.** H7 and H8 are this record's own pre-registration errors —
a `licence: WITHHELD` line asked for on a verdict that prints none, and a
control command missing a `required=True` argument — found while the
instrument was being read against the code it judges, pinned by a dated §1
amendment with corrected clauses **H7′** and **H8′** registered beside them,
**before `e15.sh` was launched once**. H6 is the survey's: its `flow --value
0.4` read predicted NOT FOUND on the premise that only the focused function
bears captures, and the value came back FOUND 115 times as the RETURN value
of a function the focus spec does not name. Each was measured as written,
reported against itself, and **not re-rolled**.

**What it costs, reported and gated by nothing** (H9). A refocus of one
container re-runs the whole recorded invocation, so the median wall from
launch to verdict is **41.693 s** (min 38.971, max 46.337) against vitest's
own near-flat ~24.6 s `Duration`, and each invocation adds ~425 MB of spool
and ~687 MB of trace. Every one of the 31 rows found its pair and counted
**371 siblings** — re-executed, stamped with the link, compared to nothing,
left `UNVERIFIED`. Blind spots **40–43** state the four bounds that follow:
the siblings, harness set 1, the reused worker a refocus refuses outright,
and the whole suite as the unit of cost.

**Two scope rulings, recorded here because nothing else on `main` names
them** (Brice, 2026-09-13). The **C conversation** — the 44 design-level rows
of the rung-4 debts design's §9 — is **dropped**, not on hold; and the
**token-cost measurement** is dropped with it, its branch
`feat/token-cost-measure` kept LOCAL at `7c0009b` (21 commits, never pushed)
as a record. Folded in with them: **`js_inspect._MORE`**, the alias of
`INSPECT_MORE` kept "for one release", is **removed** — the debts section
scheduled it for the next Python minor, and this is that minor.

`docs/query.md`, `docs/corpus.md`, `docs/trace-format/TYPESCRIPT-KEYS.md`,
`docs/trace-format/VECTORS.md`, the three READMEs, `typescript/HONESTY.md`
and the new `typescript/HONESTY-REFOCUS.md` are amended to this state; the
corpus stands at **111 cases, 236 questions**; the design's §9 carries the
plan's ten decisions (A1–A10), all twenty-three controller rulings (P0–P22)
and every in-place amendment they made; and `docs/CARRIED-DEBT.md` opens
this slice's section.

## 0.13.0 — 2026-09-12

**The debts rung 4 named, funded.** S5 rung 4 closed `DONE-WITH-STOP` with
three endpoints STOPped on its own instrument and a list of what it had left
undone; this slice pays that list. Two recorder gaps are closed for real — a
TypeScript function that returns through a `finally` now records the
finally's own statements, and a Rust block-like statement's LINE row now says
which names went out of scope on it — and rung 4's three STOPs are
re-adjudicated over its committed transcripts under a parser without the four
defects that produced them. Python **0.13.0**; **`sensorium-ts 0.4.0`** (the
RETURN row moves past a finally's rows, which is format-visible);
**`sensorium-rt 0.5.0`** and **`sensorium-transform 0.5.0`** (the wire
grammar gains a delta tag); **`cargo-sensorium 0.6.0`** (the converter reads
it). `TRACE_FORMAT` stays **4** and the wire stays **v1** — no header moves
and no record kind is added; a converter that predates tag 3 refuses a spool
carrying one by name, which is the honest reading of bytes it cannot
describe.

- **A RETURN now follows the rows of the `finally` it passed through.** The
  0.3.0 runtime's `ret` closed the frame before the program's own `finally`
  ran, so every statement that finally minted was dropped — blind spot **38**,
  declared at rung 4 and pinned there as an absence. `sensorium-ts 0.4.0`
  splits the exit in two: a `return` inside a try-with-finally renders
  `__srt.pend(__sf,(x))`, which records the value and leaves the frame open,
  and the wrapper's own `finally{__srt.seal(__sf)}` emits the RETURN after
  the finally's rows. The rule is **static and shape-scoped** — only a
  function whose own body carries a `return` lexically inside a `try` with a
  `finally` gets the deferred exit, nested closures excluded because they own
  their frames — so every other wrapper is byte-identical to 0.3.0's and no
  cost figure in `typescript/HONESTY-COST.md` moves. Measured: a census of
  114 files names **one** function with the shape, and the 0.3.0→0.4.0 golden
  diff over 102 files changes exactly that one function's wrapper, three
  lines. A `finally` the `try` reached by a `throw` is unchanged; it was
  already recorded in full.
- **An abandoned generator reads `unread`, not `undefined`.** A
  seal-deferred generator whose consumer walks away — `.return()`, a `break`
  out of `for…of` — never ran its body to a value, so `seal` emits
  `{k: 'unread'}` where nothing was pended (`f.pending ?? {k: 'unread'}`);
  only an abandoned generator reaches `seal` that way, because every other
  exit pends — a `return`, or the fallthrough close's `pend(__sf, undefined)`.
  A body that falls off its end still pends `undefined` explicitly, so the two
  cases are distinguishable in the record rather than merged into one claim
  the program did not make.
- **A Rust block-like statement's row says what it unbound.** Python has
  emitted `unbound` for `del` and the end of an `except … as e` since rung 3
  and TypeScript on every block-like statement's row since rung 4; Rust
  emitted none at all, so `watch`'s fold reported a `let` inside a block as
  in scope at every site after the block. `sensorium-rt 0.5.0` adds
  `line_unbinding(unit, site, deltas, unbound)` beside `line` — a second
  entry point, so every golden without a block is byte-identical — and the
  wire's existing delta tags gain **3**: a name with no value, written after
  the deltas, counted in the same `n` and under the same 2 KiB budget.
  `cargo-sensorium 0.6.0` reads it into `"unbound": [...]` on the row, and a
  name appearing as both a delta and an unbound in one record is refused by
  name, because a statement cannot write what it unbinds. The transform
  lists head-pattern bindings and the block's own direct `let`s in **source
  order**, and an `else if` chain is ONE statement — an `else if` is the
  outer `if`'s `else_branch` expression and takes no completion row of its
  own, so the outer statement's row unbinds the whole chain. A `let` with no
  initialiser is listed too: `unbound` means this name's scope ended here,
  which is true whether or not a probe ever bound it.
- **A shadowed name is popped, not re-read** (both recorders, stated at
  last). After `{ let x = 2; }` the outer `x` is alive, but a probe of it at
  block exit would read a name the statement did not write, so the block's
  row lists `x` as `unbound` and the fold reports it *not captured* until its
  next write — absence, never a stale value. It is the costly half of the
  rule and it now has an entry in both blind-spot lists with a falsifier
  each: `corpus/rust/focus_block_let`'s shadowed `x`, and a TypeScript unit
  test in `bindings.test.mjs`.
- **`info`'s `truncated values:` counts what inspect cut** (blind spot 36).
  A string cut at `util.inspect`'s 100 characters carries `trunc: false`, so
  the counter that read the flag alone under-reported. `js_inspect.is_clipped`
  now answers off the `… N more characters` tail as well as the flag, pinned
  by `corpus/typescript/focus_long_string`.
- **A new TypeScript corpus case can ask an `exceptions` question** (blind
  spot 37). `typescript/acceptance/e6ts.py`'s `PRE_REGISTERED` table is
  re-registered by rung 3's own procedure — the row lands in its own commit
  with its adjudication, before the case's question exists — and the
  procedure is written down in the instrument that enforces it.
  `focus_catch_binding` is the first case to use it, and it caught the
  procedure's weak point (below).
- **`watch`'s "not in scope" guidance is keyed by language.** It named `del`
  and `except E as e:` — two Python statements — on a Rust or a TypeScript
  trace. `vocab.Terms` gains `scope_exit_note`, with Python's two entries
  character for character what the command printed before the field existed.
- Seams and hygiene, each a pure move or a mechanical fix: `tests/test_corpus.py`
  (at exactly 800) splits its harness half to `tests/test_corpus_harness.py`;
  `rt.mjs`'s naming block (`UNNAMED`, `titleOf`, `nameProvider`, `ask`,
  `nameFor`) moves to `typescript/src/naming.mjs` with the export set
  unchanged; `lineOf` and `terminatorFor` move to `typescript/src/positions.mjs`,
  which removes the `transform.mjs ⇄ probe.mjs` import cycle — a test now
  asserts the import graph over `typescript/src/` is acyclic; `CHANGELOG-ARCHIVE-2.md`
  opens, on the numbered-volume rule this file's debt ledger already uses.
  `captures()` on an odd pairs list **throws** rather than dropping the
  trailing name; `resolve.survey` wraps `sitesOf` in a `try`, counts the
  throw as unparsable and names the file; `Resolution.wall` is persisted as
  `resolver_wall_s` in the invocation's manifest, so an instrument can time
  the resolver without timing itself; `tests/test_ts_honesty_prose.py` reads
  `HONESTY-COST.md`'s three acceptance paths structurally, the same way it
  reads the blind-spot lists. The named minors rung 4 left in the readers,
  the recorder, the tests and the prose are closed at their sites, and
  `docs/CARRIED-DEBT.md` says which seven are not and why.
- Three new corpus cases — `focus_finally_return`, `focus_long_string`,
  `focus_block_let` — and an `exceptions` question on `focus_catch_binding`
  bring the corpus to **108 cases, 229 questions**. One new vector,
  **`v40-rust-line-unbound`**: the tag-3 row and its `frame` and `watch`
  renderings. One corpus filter is corrected: rung 2's `finally_return` case
  filtered vitest with the bare string `finally_return`, which a new
  directory named `focus_finally_return` also matches, so the case recorded
  two test files in unstable order; the filter is `"/finally_return"` now.

**The slice ships `DONE-WITH-STOP`** — seven gated endpoints and two fences,
each read once, six of the seven PASS (record
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.md` §3–§5).
**E12′ closes rung 4's three STOPs**: over the same committed transcripts,
under a parser free of the four defects rung 4's post-mortem named, **H2′
5/5, H4′ 3/3 and H5′ 7/7** — six sites read three independent ways with
`focus_matched` one lower for the one qualname two anonymous arrows share;
all three `watch` triples, W2's clause read off the row's own `unbound`
rather than off a line number; and the CALL sighting the old parser printed
but could not see, found at `e10` with its line taken from the code object.
**E13 4/4**, **E14 5/5** and **H8′ 8/8**: on the same lens under
`sensorium-ts 0.4.0` the recorder reproduces rung 4's nine LINE rows
text-equal, the same six resolved sites, the same `CALL 117 RETURN 117 …
LINE 295` over 529 events, and leaves the lens byte-identical — 748 OK
before and after. The fences and the eight suite readings are green: 108
corpus cases / 229 questions / 0 failures, `pytest -q` **4228 passed, 24
skipped**, `cargo test --workspace` **804 passed**, `npm --prefix typescript
test` **559 passed**, the probes' **146** checks, and 0 of nine leak needles
over this slice's own transcripts.

**The one STOP is this slice's own pre-registration, and it reported it
against itself.** **E6-TS′** pre-registered `focus_catch_binding` at **0**
SWALLOWED; the answer prints **1**, by two derivations that agree. The clause
was written in `grep --kind HANDLED`'s vocabulary — a HANDLED event, traced
with confidence — and "nothing swallowed" was concluded from that confidence,
where `exceptions`'s own documented rule says `swallowed` is exactly this
shape: an absorbing handler took it and the frame holding the handler then
returned. The lesson is about WHICH VOCABULARY a hand adjudication is written
in — a pre-registration of a command's output must derive from that command's
own documented rule, never from a sibling command's kinds. The mechanism
worked: the wrong clause was left standing, a corrected one (**E6-TS″**,
22/22 PASS) was pre-registered beside it from the rule before any cell was
read, and both were measured once and reported.

`docs/TRACE-FORMAT.md`, `docs/trace-format/VECTORS.md`, `docs/query.md`,
`docs/corpus.md`, both HONESTY sets (TypeScript blind spot **38** struck and
**39** added; Rust **32** and **33** added), `rust/HONESTY.md`, `rust/HONESTY-INDEX.md`,
`rust/HONESTY-REFOCUS.md`, `docs/trace-format/TYPESCRIPT-KEYS.md` and the
three READMEs are amended to this state; the design's §12 carries all
thirteen amendments and every controller ruling that changed a section's
reading. `docs/CARRIED-DEBT.md` closes rung 4's carried debts — three of them
by this slice's own measurement — and opens this slice's.

## 0.12.0 — 2026-09-12

**TypeScript records per statement, when it is asked to.** S5 rung 4 gives
`sensorium ts run` a focus tier. `--focus <spec>` is resolved against the
consumer's own AST with the consumer's own TypeScript **before anything is
spawned** — a spec that names nothing is refused at exit **2** with the
closest eligible qualnames, and a spec that names only functions this
recorder never instruments is refused with the reason and its count — and the
transform then splices a probe after every statement of the functions it
selected. One **LINE** row per completed statement, its `deltas` the bindings
that statement wrote and nothing else; a guarded body's head names as a
synthetic first row at each entry; the block-scoped names a block-like
statement declared listed `unbound` on that statement's own row; and the CALL
of a focused function carrying its `args` where an unfocused one still reads
`<unread: locals>`. Python **0.12.0** (the driver's `--focus` and its
resolver, the converter's `_on_line`, the inspect dialect, the `--at`
spellings, `flow --object` on a serial, the predicate constants);
**`sensorium-ts 0.3.0`**, bumped at the rung's second task before any of it
was measured. The Rust crates do not move. `TRACE_FORMAT` stays **4** and the
wire stays **v1** — a 0.2.x spool converts under 0.12.0 unchanged, and a
converter that predates the LINE record refuses one by name.

- **Identity is a serial now, not an address.** `dbg()` mints `oid` (a
  `WeakMap` serial, once per object, never reused) and `type` on every object
  or function it captures — a RETURN value at the call tier, an argument and a
  statement's delta under a focus — so `sensorium-ts 0.3.0` declares
  `capabilities.object_identity: **true**` unconditionally and `flow --object`
  is **exact**: no gap analysis, a `flow of object #64 (Array)` header and
  `continuity: exact (serial identity)`. `corpus/typescript/object_refused`
  became `corpus/typescript/object_identity`, a refusal turned into an answer.
- **One `dbg` kind, two dialects.** A TypeScript capture is `util.inspect`
  text and a Rust one is `Debug` text; `watch --expr` reads and `flow --value`
  writes each through its trace's own dialect, never through the other's.
  Every spelling was **generated**, not guessed: 41 measured rows in
  `typescript/test/fixtures/inspect-table.json`, four of which would have been
  wrong by hand — `5.0` prints `5` (JavaScript has one number type, the
  opposite of Rust's `2.0`), `-0` keeps its sign, `\v` prints `\x0B`, and a
  `${` in the text rules the backtick quote out. `null`, `undefined`, `true`
  and `false` are predicate constants in every language.
- **`--at` and `--focus` are one spelling.** The file half of a site may be
  the dotted module, the stem, the basename or the root-relative path, in
  every language, so every `--focus` spelling is an `--at` spelling; one
  fixture (`typescript/test/fixtures/site-spellings.json`) holds the JavaScript
  matcher and the Python one to the same ten rows. `info` prints
  `focus matched: <n> — …` beside the specs as they were typed, with
  `(<n> function(s) focused by the transform)` where the transform's own count
  differs — on a focused Rust trace too, because the line is gated on a meta
  key and never on a language.
- Ten new corpus cases — `focus_let_chain`, `focus_loop_counter`,
  `focus_block_scope`, `focus_destructure`, `focus_args`, `focus_async`,
  `focus_catch_binding`, `focus_place_write`, `focus_container`,
  `flow_value_inspect` — the only ten recorded under a focus, plus
  `object_identity`, bring `corpus/typescript/` to **42** and the whole corpus
  to **105 cases, 220 questions**. A vitest case declares its focus with the
  Python recorder's own key, `record: {focus: [...]}`. Five new vectors,
  `v35`–`v39`: the predicate constants, a TypeScript LINE and its args, the
  serial `flow --object`, the inspect dialect's two directions agreeing, and
  the site spellings as CLI questions.

**The rung ships `DONE-WITH-STOP`** — eight endpoints, each read once, three
of them STOPped (record
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md` §3–§5,
measured on 830 files of a real frontend). **H3 is the one the rung exists
for and it PASSed on the first reading**: the first `parseDiceGroups('1d20')`
activation carries **9** LINE rows, their lines **69, 70, 71, 72, 73, 74, 76,
75, 72**, every delta name and the one `unbound` list row for row against a
hand count written — and sha256-locked — before `bindings.mjs`, `probe.mjs`,
the runtime's `line` or the converter's `_on_line` existed. Empty diff. **H1**
4/4: an unfocused arm declares `line: false` / `locals: false`, writes zero
LINE rows, and `watch` refuses it at exit **3** in a sentence naming the
recorder the TRACE carries. **H6** 4/4: two sightings of one array across two
functions, one serial, `continuity: exact`, both `Array`. **H8** 6/6: 105
corpus cases and 220 questions equal, `pytest -q` 4090 passed / 33 skipped,
`cargo test --workspace` 773 passed, `npm --prefix typescript test` 521
passed, the probes' 146 checks green, and 0 of nine leak needles over 13
transcripts (the three suite totals are read from the session's own
uncommitted logs, not from a committed cell — the record's §4.8 names each
log; node's count is the reading's, and the rung's final review added one
test to it). **H7**, reported and gating nothing: ×**2.3816** on the median
wall of one 26-test file (0.7955 s → 1.8946 s, n=3 each, interleaved) for 295
extra LINE rows and the same call tier, plus **1.132 s** of resolution over
830 files, once per invocation.

**The three STOPs, and what each one is about.** **H2** is the
pre-registration's own under-derivation: three typed specs resolved to **six**
sites where §1 pre-committed three, because `focus.mjs`'s documented prefix
rule selects the function-likes nested inside a container — a `reduce` arrow
and two default-parameter arrows. The behaviour is the design's; the number
was a count of the functions a reader names, not of the ones a spec selects,
and `resolve.mjs` is where anyone finds that out before a run. Beside it,
`focus_matched` **5** against `functions_focused` **6**: two anonymous arrows
share one `<file>:<qualname>`, so a qualname is not an identity for an
anonymous function-like. **H4** and **H5** are the INSTRUMENT's, not the
recorder's: H4's cell tested "no HIT at line 72" where the pre-registration
predicted "no HIT at the `while`-COMPLETION row", and line 72 also carries a
head row; H5's row parser could not see a CALL sighting its own transcript
prints, because a printed CALL row's name carries its argument list and no
line at all. Both were found after their numbers were read, so both are
findings and the numbers stand — the next slice re-registers H2, H4 and H5
under fixed instruments, the way rung 1's E6′ became E6″. The lesson is about
the dry run: a rehearsal that does not exercise every SHAPE an endpoint can
meet verifies plumbing, not reading.

`docs/TRACE-FORMAT.md`, `docs/trace-format/TYPESCRIPT-KEYS.md`,
`typescript/HONESTY.md` (a new §11, *Under a focus*), `HONESTY-BLIND-SPOTS.md`
(items **28–37**), `docs/query.md` and both READMEs are amended to this state;
the design's §15 carries all fourteen plan decisions and every controller
ruling that amended a section, with what shipped and the cost if wrong,
including the two that changed the spec's own rules — **R23** (a `do…while` gets no head row, so §3.2's
guard list is narrowed) and **R29** (§2.2's `Closest:` clause gains the case
where only `<anonymous>` qualnames are eligible). `docs/CARRIED-DEBT.md` closes
five rung-3 debts and opens this rung's.

## 0.11.0 — 2026-09-11

**The catch-all gets a name.** S5 rung 3 closes rung 2's Gap 4: the
seventeen blocks reading *"no rule of this recorder reaches a verdict
here"* now read a reason, `untraced catcher`, in three variants — `its
caller f<n> returned; not followed`, `later unwound with <exc>: a
translation by untraced code, or a later failure, indistinguishable`, and
`had not closed at the end of the recording; not followed` — each
predicted by a human from source before this code existed. Rule 4's
absorbing conjunct is now window-scoped, not trace-global, so a logged
rethrow to the harness reads `PROPAGATED` where rung 2 read this same
catch-all (`corpus/typescript/logged_rethrow_to_harness`); a second tally
line prints only when non-empty — `ambiguous by reason: escaped 21,
untraced catcher 32` on the kept lens. Python **0.11.0** (the reason, the
window scope, the site-bearing TypeScript key — the verdict's own words
under a mask `\b[ef]\d+\b` that exempts nothing, closing Gap 1's borrowed
Rust float-type exclusion; the origin site enters only where the verdict
names none of its own); **`sensorium-ts` stays 0.2.0**, no runtime,
transform or wire change. `TRACE_FORMAT` stays **4**, wire **v1**; nothing
is recorded this rung — one re-read of the kept rung-2 invocation, hashed
before and after, against a pre-registration byte-locked first
(`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung3.md` §1).

Four new corpus cases and the `translated` re-pin bring
`corpus/typescript/` to **32**; one new probe marker,
`callback_bare_rethrow` (`.catch((e) => { throw e })` → `catch_callback`),
closes a rung-2 debt with no probe pin; every acceptance script resolves
`<repo root>/.venv/bin/sensorium` and refuses outside it, only `lens.py`
stamps the `lens` label, and the E7 checker prints its matching rule.

**All eight endpoints ran once, none fired its rule's failure word — the
rung ships DONE** (record §3, §5): **E6-TS‴** 0 false names over 20
blocks, 17 of 17 rows named, `unnamed` 0; **E6-TS′-fence** 0 differences
over 29 gated lines; **E-places** 28 of 28 SWALLOWED blocks; **E6-TS** 21
of 21 corpus cases; **E8‴** 33 of 33 markers; **E7‴** 0 over 9 needles;
**E-legacy**/**E-branch** intact. Left open, none a stop: a block can cover
origins from two rows sharing one parent frame; `[×3 …]` was unprintable,
its arithmetic conserved instead (`[×132 over 11 processes …]`,
130+1+1); and `tests/test_exceptions_python*.py` matched no file, the
fence holding on intent regardless. `HONESTY.md` §4 and blind spot 27 are
amended; `docs/query.md` gains the reason line; `CARRIED-DEBT.md` closes
Gap 1, Gap 4, the neighbour and the probe-marker debt, dated to this
record, and gains new debts.

## 0.10.0 — 2026-09-10

**`exceptions` answers on a TypeScript trace.** S5 rung 2 gives the throw-flow
rows rung 1 recorded a rule to be read by: the same five dispositions
`exceptions` has always printed — `swallowed`, `uncaught`, `re-raised`,
`propagated`, `ambiguous` — computed over JavaScript's own shapes, per trace
and across a whole `sensorium ts run` invocation. Python **0.10.0** (a third
rules module, the per-member invocation dispatch, four vectors, seventeen new
corpus cases); **`sensorium-ts 0.2.0`** (the escape rule, the rejection-callback
wrapper, the `finally` sink, `capabilities.err_flow: true`). The Rust crates do
not move. `TRACE_FORMAT` stays **4** and the wire stays **v1**: the BOOT record
gains `capabilities`, HANDLED gains `how`, and nothing else changes shape —
every Python and Rust `exceptions` output, every existing vector and every
Python and Rust corpus case is byte-identical, which is what the suites that
did not move are the evidence for.

Everything below is measured on one lens — the tabletop VTT frontend at
`0091e97`, **372 test files, 4,278 tests**, under vitest 4.1.9, vite 6.4.3,
jsdom 29.1.1, node v24.16.0, 16 cores — against a pre-registration byte-locked
before any of this code existed
(`docs/superpowers/acceptance/2026-09-10-sensorium-s5-rung2.md` §1). **Every
one of the nine endpoints ran, once, and not one fired its rule's failure
word.** No row reads PASS and neither does the rung, because no rule of this
pre-registration supplies that word: six name only a failure word, three name
none at all. **The rung ships DONE** — the DONE-WITH-STOP branch §1 spells out
is the one not taken.

- **The recorder classifies a catch binding where the syntax is, and says so
  in `how`** (`sensorium-ts 0.2.0`, spec §2.1–§2.5). A clause's word is decided
  at transform time from its own AST: **`catch`** when the body never mentions
  the binding or mentions it only as an argument of a `console.*` call
  (log-and-continue is the archetypal swallow), **`catch_escaped`** when it
  appears anywhere else, **`sink_empty_catch`** for an empty block. Rejection
  handlers get the same rule applied to their parameter —
  **`catch_callback`**, **`catch_callback_escaped`**,
  **`sink_empty_catch_callback`** (now for the `function` spelling too, closing
  blind spot 11), and **`catch_callback_opaque`** for a handler defined
  somewhere else, whose parameter's fate is not this splice's to say. A
  `finally` block that `return`s, `break`s or `continue`s discards an in-flight
  throw and records **`sink_finally_return`**, read from a one-slot mark per
  frame that carries the real serial (blind spot 3 closes). Nine `how` words in
  all, and the enumeration is the declaration: a shape outside it produced no
  record, and `typescript/HONESTY.md` §4 lists what still produces none.
- **A bare rethrow is a traced exit, not an escape** (`68015dd`, `43e1fbd`,
  spec §2.1's dated amendment). `throw e;` whose operand is the binding itself
  leaves the way it arrived and carries the same serial, so it does not count
  towards `catch_escaped`: `catch (e) { console.error(e); throw e }` reads
  `catch`, while `catch (e) { list.push(e); throw e }` and
  `catch (e) { throw new Wrapped(e) }` stay `catch_escaped`. The exclusion
  holds at closure depth 0 only, and applies to rejection callbacks by the same
  rule. It was found and fixed **before any endpoint was measured**: the
  literal reading barred every `throw e` hop from SWALLOWED and made §1's
  locked `rethrow_hop` count unreachable by construction (record §2.3).
- **The capability is the gate, and an old trace still refuses.**
  `capabilities.err_flow` is **true** on a 0.2.0 recording and the converter
  passes the BOOT record's own capabilities through untouched. A trace a 0.1.x
  runtime wrote declares `false` and is refused at exit **3** by the capability
  sentence — naming the recorder and saying nothing was checked — because what
  it lacks is a record and not a rule. Re-recording is the fix; the cost was
  pre-committed at rung 1, not discovered here. Vector
  `v32-err-flow-typescript-capability-refusal` pins that sentence, and the old
  language refusal is gone: `TYPESCRIPT.exceptions_refusal` is now `None`.
- **SWALLOWED is claimed only where the recording establishes it.** A HANDLED
  whose `how` is in the absorbing set, in a frame that later closed by
  `return`, with no later raise of the serial and **no** escaping handler for
  it anywhere. Everything else is `ambiguous` with its reason printed —
  an escaped or opaque handler, a handler frame still suspended, a primitive
  rethrow, a frame that unwound with a different serial. Nothing reaches
  SWALLOWED by falling through, and an UNWIND is never itself a verdict.
- **`sensorium exceptions <invocation-id>` answers for a whole TypeScript run**
  (spec §4). Every member trace is opened, dispatched on its own `lang`, and
  merged on a shape key the language module supplies, so one clause swallowing
  in 40 processes prints once with `[×N over N processes]` beside it. The
  grouper Rust has used since 0.8.2 is now generalised over a per-language
  renderer, and every Rust caller and test is byte-unchanged.
- **A swallow corpus that runs itself.** `corpus/typescript/` grows from
  thirteen cases to **28** — one shape per case, each with an `exceptions`
  question pinning the verdict line and the tally, and a `why_logs_fail` naming
  all three channels. `exceptions_refused` is renamed **`silent_swallow`**: the
  refusal it recorded is one no recorder produces any more, and it is a vector
  now.
- **What the endpoints read** (record §3). **E6-TS** — the corpus's verdicts,
  **17 of 17** equal to the locked table. **E6-TS′** — the gate that decides
  the shipping word: **0 false SWALLOWED of 30** hand-adjudicated shapes on a
  consumer's own suite, every line's adjudication written into
  `-e6tsp-adjudication.md` under a protocol fixed before any of them was read;
  the tally over that run is `swallowed 261, ambiguous 53` across 314 raises in
  53 of 372 processes. **E2″** — **287 spliced of 287** eligible sites
  (177 catch clauses, 108 `.catch`, 2 `.then`, 0 completing `finally`) over 741
  files, ratio **1.0000**, zero named exclusions needed. **E8″** — **32 of 32**
  probe markers. **E3-TS″** — **0/19** false DIVERGED over twenty recordings of
  one file. **E5″** — both harnesses green. **E7″** — **0** occurrences of nine
  Python/Rust leak needles over both transcripts. **E1‴** — `off/plain`
  **1.0608** and `call/plain` **1.1266** (n=5 per arm, interleaved, every load
  reading under 4.0), against rung 1's 1.0587 / 1.1324. **E10″** — the fresh
  372-spool set converts in **16.0715 s** (n=5), beside slice 2's 16.3859 s.
- **Four gaps, none of them an endpoint's rule** (record §5). **Gap 1** — the
  shape key's id mask carries Rust's float-type exclusion (`f32` and its
  siblings are Rust type names) onto TypeScript FRAME ids, so the lens's 30
  SWALLOWED shapes are **28 distinct places**; no verdict and no tally moves.
  **Gap 2** — `arms.sh`, `e3.sh` and `e7.sh` hard-coded the global `sensorium`,
  which is an editable install of `main`: three reused instruments were
  measuring the wrong binary, fixed before any of the three ran here. **Gap 3**
  — E7″'s needle list cannot be applied as written, because `Err` as a
  case-insensitive substring is matched by every `Error('…')` an answer prints;
  the three identifier needles are matched word-bounded and case-sensitively,
  fixed before the count was taken. **Gap 4** — on real code the modal
  AMBIGUOUS reason is the classifier's catch-all (**17** of 30 ambiguous
  shapes), and the shape behind it is an untraced catcher sitting *inside* a
  traced frame. The rules decline instead of guessing, which is what keeps the
  gate at 0.
- **Documents.** `typescript/HONESTY.md` §4 is rewritten against the shipped
  runtime and its blind-spot list restruck, with the list split to
  `typescript/HONESTY-BLIND-SPOTS.md`; `docs/query.md` gains the TypeScript
  paragraph under `exceptions`; `docs/CARRIED-DEBT.md` gains the rung's section
  after cutting rung 1's to [`docs/CARRIED-DEBT-ARCHIVE-6.md`](docs/CARRIED-DEBT-ARCHIVE-6.md),
  drafted and measured first the way the ledger's own lesson asks; this rung's
  design gains a §14 naming every place its own text moved and why.

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

**Earlier entries** — `0.9.1` and `0.9.0`, and `0.8.6`, `0.8.5`, `0.8.4`,
`0.8.3`, `0.8.2`, `0.8.1`, `0.8.0`, `0.7.0` and `0.6.0` below them — are in
the archive, which is **numbered volumes, each under 800 lines**, never one
growing file. [`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md) is volume 1 and
holds `0.8.6` down to `0.6.0`: `0.7.0`/`0.6.0` moved there 2026-09-08,
`0.8.2`/`0.8.1`/`0.8.0` 2026-09-09, `0.8.4`/`0.8.3` 2026-09-10 and
`0.8.6`/`0.8.5` 2026-09-11. [`CHANGELOG-ARCHIVE-2.md`](CHANGELOG-ARCHIVE-2.md)
is volume 2, opened 2026-09-12 for `0.9.1` and `0.9.0` because volume 1 had no
room left for a 271-line section. Every cut so this file stays under the
repo-wide 800-line ceiling `tests/test_ceiling.py` holds it to — and note that
a volume's number is its cut order, not its age: `0.9.1` and `0.9.0` are newer
than everything in volume 1. A count of moved entries in this sentence goes
stale at the next cut, which is why it names them rather than counting them.
Pure moves: same wording, same order, same dates.
