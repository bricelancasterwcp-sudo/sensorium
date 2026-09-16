# CARRIED-DEBT — volume 14

The 2026-09-14 section — secrets redaction, PR B: captured values, the
content rule, wire v4 and the readers — moved here **2026-09-16** (PR C, at
its ledger task) so [`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays under 800
lines. It is the fourteenth numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file.

The move was measured before it was made, the way the ledger's own lesson
asks: PR C's section was drafted at **342** lines against a live file of
**591**, which would have taken it to **934** — a hundred and thirty-four
over the ceiling — so the oldest section was cut rather than the content
trimmed. The section moved here is **443** lines before the strike below and
**447** after it.

**The wording, the order and the strikes are unchanged**, but for the ONE
strike PR C made inside this volume as it moved: the *Deferred by ruling*
bullet **PR C — the retrofit** is struck where it stands and says what
settled it, because that bullet named this slice and this slice ran. Nothing
else was edited BY the move and nothing is deleted; every other deferred item
here is still open unless it is struck.

## 2026-09-14 — secrets redaction, PR B (captured values, the content rule, wire v4, the readers)

The second of the design's three PRs
(`docs/superpowers/specs/2026-09-13-sensorium-secrets-redaction-design.md`):
part A took the environment, this takes everything a recording CAPTURES —
arguments, locals, returns, exception messages, output chunks, and any
secret-shaped SPAN inside any text a recorder stores. Twenty-eight plan
decisions (**B1–B28**) and twenty-five rulings (**R1–R25**) are in the
design's **§13** with what each costs if wrong, beside the twenty places
the shipped code differs from the spec. **DONE** — E16 part B was measured
**once**, on 2026-09-14
(`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` §3):
H1-values **PASS**, H6-values **PASS**, H5 **measured and not gated**. The
retrofit of every trace already on disk is PR C's.

### Settled — closed here

- **Every captured value is judged at the WRITER, in all three recorders.**
  A value whose NAME fires rule v1 is stored as `<redacted>` with an HMAC of
  the text the trace would otherwise have held; a secret-shaped span inside
  any stored text is replaced where it stands, sentence intact. Python
  `2e92eaa`/`b246075`, the Rust runtime `422874d` and its converter
  `d47d371`/`7bbe6cc`, the TypeScript runtime and its ingest
  `f0df6cc`/`a5f4b50`. Measured: E16 **H1-values PASS** over 20 gated files
  — every count 0 under the store, in every Rust `<pid>.proc.json` and in
  the TypeScript spool, and the Rust `.spool` files exactly **3**
  occurrences, the content window §5.2 names — with **762** further files
  swept beside them (the build tree, the disposable copies, the transcripts,
  `TMPDIR`), none holding the token.
- **The content rule: nineteen patterns, three implementations, one
  fixture.** `src/sensorium/redact_content.py`,
  `rust/cargo-sensorium/src/convert/redact_content.rs` and
  `typescript/src/redact.mjs` all read
  `docs/trace-format/redaction-v1.json`'s `content` rows (**B20**:
  `{"pattern", "text", "after"}`, a negative row's `after` equal to its
  `text`). A **hit** means the text CHANGED, never that a pattern matched —
  the userinfo pattern matches the marker it put there itself, which is what
  makes re-conversion a fixed point and the `values` count honest.
  `06d325f`.
- **The Rust wire is v4, and the tag is `4`** (**B1**). On a LINE row tag 3
  has meant UNBOUND since wire v3, shipped in 0.13.0; §5.2 named 3 anyway,
  having been written a day after `line.rs` changed. Tag 4 carries the
  16-hex digest (empty when unkeyed), `truncated` 0, LINE rows only, over
  the CAPPED text (**B24**); a v2/v3 reader still refuses it as `not
  0..=3`. `422874d`, read by the converter at `d47d371`
  (`rust/sensorium-rt/tests/redact/line.rs`,
  `rust/cargo-sensorium/src/convert/spool/tests/line.rs`).
- **The readers name what they cannot do** (`01e4dac`, `1431a50`).
  `frame`/`tree`/`grep` print `token=<redacted #01234567>`,
  `dict[3]=<redacted>` for a container and `Cfg#7` unchanged for an object;
  a content hit prints as stored. `watch` renders
  `<redacted; no comparable value>`, ends a predicate that met only taken
  values at `NOTHING WAS CHECKED` and exit 3, and names the remedy
  (`SENSORIUM_REDACT_ALLOW=<name>`, **R13**) rather than only the diagnosis.
  `flow --object` refuses at exit 2 — the address is real and its occupant
  was never recorded (**B11**) — and `flow --value` never sights a marker,
  which would otherwise report every secret in the run as sightings of one
  value. Vector `v42-redaction-render`.
- **`redaction.values` is counted at the WRITE site** (**R10**, amending
  **B3**): `redact_values.count`/`count_capture` walk what is handed to
  `add_event`/`close_frame`, the tee counts a chunk whose text changed, and
  the two converters count as they build — so the number is a pure function
  of the trace's contents. A secret local re-captured at every line of a
  loop counts ONCE; one text written into two rows counts once (an `Err`
  return and the exit RAISE synthesised in front of it, under one digest,
  **R16**). A kind this rule has never heard of is withheld WHOLE with
  `digest: null`, pinned by an exhaustiveness test over `capture.py`'s kind
  literals: the failure direction of this control is a lost fact, never a
  kept secret. `b246075`.
- **`by` changes meaning, visibly** (**B2**). It reads `recorder` only where
  the RUNTIME did the value half too — Rust wire v4 or better with a
  `redaction` header whose mode is on, `sensorium-ts` 0.6.0 or better — and
  `converter` wherever a converter applied a half the runtime should have.
  `rust/cargo-sensorium/src/convert/redaction.rs`,
  `src/sensorium/ts/redaction.py`.
- **`KEY` fires only inside a longer name, as `PWD` does** (**B28**,
  **R6**), on the census's own evidence: **8 of the 17 firing bindings**
  Task 0's static census found across `corpus/**`, the vectors and the
  ts-spool fixtures were a bare `key` — a cache key, a dict key, a lookup
  key (`stale_cache` in two languages, Rust's `focus_unfocused_refuses`,
  TypeScript's `focus_async` and `focus_catch_binding`, vector `v36`) — so
  rule v1 as first written would have answered `NOTHING WAS CHECKED` to
  `watch --expr key == …` on every mapping-iterating function in the
  language, the §12 false-positive cost paid on the commonest local
  there is. Every compound spelling still fires (`api_key`, `apiKey`,
  `secret_key`, `build_key`, `KEY_FILE`), and `SENSORIUM_REDACT_NAMES=key`
  restores it per run. **Amended into v1 rather than minted as v2**: no
  trace under the earlier spelling exists outside this box and CI, and the
  identity rule binds from the first published release — §13 records the
  narrowing, which is security-relevant and was taken on design authority.
  `f7e0ef8`.
- **The content rule's pre-check folds case where its patterns do**
  (**R21**) — a LEAK found in prose, not in a test. **B18** put one
  alternation of literal prefixes in front of the twenty regexes so H5 would
  not measure them all on every string; `_TRIGGER` was case-SENSITIVE while
  `authorization-header` is `(?i)`, so `BEARER <token>` skipped the table
  and was stored in plaintext. Fixed in all three languages with two
  uppercase fixture rows pinning `test_every_positive_passes_the_trigger`.
  `ddb384e`.
- **Two values are never taken, under any name** (**R17**, **R19**): Rust's
  synthesised unit return `()` and a `dbg` text that is exactly `undefined`
  or `null`, on ANY site and in both hands. They say the program produced no
  value; a marker there would cost a reader that fact, hide no secret and
  publish a digest of a constant. Whole texts and nothing near them — a
  `NaN` is a value the program had. `7bbe6cc`, `a5f4b50`.
- **A SPAWNED process's command line stops reaching the trace in plaintext**
  — the final whole-branch review's finding, and the last path rule v1 did
  not reach that nothing in the slice had named. `meta.children` holds the
  argv of every child the recorded program starts and `info` prints each one
  back verbatim, so a `subprocess.run(["curl", "-H", f"Authorization: Bearer
  {tok}"])` put a live token into run metadata. Each element now takes the
  CONTENT rule at the audit sink, and an element that CHANGED counts into
  `values` at the write like any other (**R25**); an argv has positions
  rather than bindings, so there is no name to ask about and the name rule
  stays out. `ff8546e`,
  `tests/test_record_values_redaction.py::test_a_spawned_command_line_is_content_ruled_and_counted`
  (mutation: drop the rule at the sink and it fails on the plaintext token).
- **E16 part B, measured once, 85.3 s wall clock.** H1-values PASS and
  H6-values PASS (python **5**, rust **4**, typescript **4** — each trace
  redacting exactly `SENSORIUM_E16_TOKEN`, the counts derived by hand from
  the probe sources at **B15** and pre-registered). H5 measured and never
  gated (§9, `rust/HONESTY.md` §10), `recorded/baseline` at `7dd25d2`
  against HEAD, best-of-5 (**B17**):

  | workload | tier | at `7dd25d2` | at HEAD | HEAD over `7dd25d2` |
  |---|---|---|---|---|
  | async_call_dense | default | 14.88 | 17.31 | **1.16** |
  | await_dense | default | 6.89 | 7.26 | **1.05** |
  | await_dense | focused | 10.45 | 12.35 | **1.18** |
  | call_dense | default | 169.05 | 196.64 | **1.16** |
  | call_dense | focused | 238.67 | 286.91 | **1.20** |
  | work_between_calls | default | 2.83 | 3.36 | **1.19** |
  | work_between_calls | focused | 3.96 | 5.52 | **1.39** |

### Deferred by ruling

- **The H5 cost is real, and its levers are named, not taken.** Every one of
  the seven ratios is above 1: redaction costs 5–39% on top of the
  recorder's own overhead, worst where the recorder is cheapest
  (`work_between_calls focused`, 1.39) and mildest where it is dearest. The
  two costs are the content regex over every stored text and
  `redact.fires()` called **per local per line** from `redact_values`;
  **B18**'s pre-check is the mitigation already built, and the two levers
  left are a per-name memo for `fires()` (the names are `co_varnames`
  strings, interned and handed back on every call, so a memo keyed on the
  name pays once per name per process) and a cheaper trigger than one
  alternation.
  §9 says an outlier is a CARRIED-DEBT finding and never a stop, so it is
  recorded here rather than chased. *Cost if wrong:* a recording 20% slower
  than it needs to be, on a number that is reported and never gated.
- ~~**PR C — the retrofit.** `sensorium redact [--all] [--dry-run]`, and H4
  with it: every trace already on disk still holds plaintext values, and
  nothing in this PR reaches one. One hazard still travels from A — a stale
  `redaction.key.<pid>.tmp` from a killed writer is left on disk by **R15**'s
  publication and nothing sweeps it. *Cost if wrong:* every trace recorded
  before 0.15.0/0.16.0 stays as it is, which is what part C exists for.~~ —
  **settled 2026-09-16 by PR C**, which is the slice this bullet named: the
  command ships, the sweep with it, and E16 part C read **H4 PASS** over a
  copy of the store's 273 traces. The live store's own pass is a post-merge
  chore (**C18**). The settled statement is the live file's newest section.
- **`argv` is stored in plaintext.** Rule v1 reaches the environment and
  captured values; a token passed as a command-line argument is in
  `invocations.jsonl` and in the trace's own argv, untouched, and the name
  rule has no name to judge it by. Named in `docs/redaction.md`'s honest
  limits. *Cost if wrong:* a secret on a command line, which `ps` already
  publishes to every process on the box.
- **The output-chunk boundary.** The tee scans one `write()` at a time
  (**B5**): a token split across two writes is seen by neither scan and
  reaches the trace whole. Buffering one chunk to look across the seam would
  hold output back from a recording that may never finish. *Cost if wrong:*
  an unlucky `print` of a long secret, split by the interpreter's own
  buffering.
- **A Rust `?`-hop RAISE's message is content-ruled, not name-ruled**
  (Task 6's open edge, not ruled). The message on a `?`-hop is the probe's
  own read of the `Err`, not the RETURN text that **R16** withholds whole
  under a firing qualname, so it takes the content rule like any other text.
  Whether a hop through a firing function should withhold its message whole
  is the question **R16** answered for the exit RAISE and not for this one.
  *Cost if wrong:* a secret-shaped `Err` no content pattern knows, visible
  in one synthesised row.
- **The Rust spool holds content-plaintext under `<target>/sensorium/`
  between the runtime and the converter.** The runtime does the name half
  (it needs no regex, and the crate stays dependency-free); everything else
  is the converter's, so a token inside a `Debug` rendering or
  `get_token()`'s return is in the `.spool` file at 0600 until conversion —
  exactly the 3 occurrences H1 counted. Taken by `cargo clean`, named in
  `rust/README.md` and `rust/HONESTY.md` §14 rather than left to be
  discovered. Closing it puts a regex dependency in a dependency-free
  runtime, which §11 declined. *Cost if wrong:* a readable secret in a build
  tree that outlives the recording.
- **A spool ingested into a store that did not record it names two keys.**
  `key_id` on the trace is the RECORDER's, while the capture digests the
  converter took are under the INGESTING store's key. In practice the driver
  mints the store key it hands the runtime, so the two are one; a spool
  carried between stores is where they part. Documented as a limit.
  *Cost if wrong:* a digest nobody can reproduce from the `key_id` printed
  beside it.
- **`exceptions` groups on the message text, so two identically redacted
  messages are one group.** A content-rule consequence: two different
  secrets whose messages redact to the same text merge into one row with a
  count of 2. The grouping key would have to be the pre-redaction digest,
  which the trace does not hold for a content hit (§2.3: a partial cannot
  honestly carry a digest of the whole). *Cost if wrong:* an exception
  census that under-reports distinct failures by one row.
- **B8's map-key rule is Python-only.** A `map` sample pair whose KEY is a
  firing `str` has its VALUE withheld — which is what reaches a headers
  dict's `authorization` entry — in the Python recorder alone. Rust and
  TypeScript store a RENDERING of a struct or object rather than a
  decomposed map, so the content rule is their only reach into one, and
  E16's Rust and TypeScript header rows were counted as content hits for
  that reason. *Cost if wrong:* a headers dict whose value is on none of the
  nineteen patterns, plaintext in two of three languages.
- **Every older spool re-converted under this release now says
  `by: "converter"` where it said `recorder`** — a visible change to a
  published key (**B2**). `tests/fixtures/rust-spools/redacted-env/` is the
  in-tree instance, re-pinned at Task 6. It is the truth about whose hand
  took the capture digests, and the CHANGELOG says so, but a reader diffing
  two conversions of one spool across releases sees a meta key change with
  no wire change under it. *Cost if wrong:* one confused reader per
  re-conversion.
- **Outside this PR's promise, carried from A and still at default modes:**
  `<target>/sensorium/{manifests,mirror,cache,rt}` — the **mirror holds a
  copy of the user's source** — and `ts/wrapper.py`'s files inside the
  user's `node_modules`. PR B added no writer outside the store and the
  spools, and moved none of these. *Cost if wrong:* a world-readable copy of
  somebody's source under `target/`, unchanged from A.
- **Named as later slices by the design's §11, untouched:** `seal` mode, the
  MCP policy layer, scanner parity, allow-globs and Windows ACLs.

### Files near the ceiling

Measured at this slice's last commit against the 800-line gate
(`tests/test_ceiling.py`, `LIMIT = 800`, tracked `*.py *.rs *.sh *.md *.mjs
*.ts *.tsx` outside the three record directories); the next edit to each
takes a seam, not a paragraph:

- **`rust/HONESTY-BLIND-SPOTS.md` 800** — AT the gate, zero headroom. The
  next blind spot needs the file cut first, on the pattern `HONESTY.md`
  itself already took three times (`HONESTY-ERR-FLOW.md`,
  `HONESTY-OUTCOMES.md`, `HONESTY-REFOCUS.md`).
- **`CHANGELOG.md` 799** after 0.16.0 and the fix wave's limits clause — the
  **next** entry must move the
  oldest one to `CHANGELOG-ARCHIVE-2.md` (479) under a dated cut note
  BEFORE it is written, which is **R36**'s rule from A applied in advance
  rather than discovered.
- **`docs/query.md` 798**, **`docs/TRACE-FORMAT.md` 797**, **`README.md`
  796**, **`typescript/HONESTY.md` 796** — four documents with nine lines
  between them. **B25** is the pattern that kept TRACE-FORMAT net-zero this
  slice: the contract names the key, the reading lives one file away
  (`docs/redaction.md`). `docs/query-typescript.md` is query.md's named
  seam; `typescript/HONESTY-REDACTION.md` is the split
  `typescript/HONESTY.md` already took.
- **`rust/HONESTY.md` 780** after §14 — 20 lines; the index
  (`rust/HONESTY-INDEX.md`) is where a new row goes cheaply.
- **`typescript/src/rt.mjs` 788** — **B13**'s five splits cleared A's named
  seams (`redact_key.py`, `refocus_facts.py`, `flow_report.py`,
  `record/boot_io.py`, `convert/discover.rs`, `3af7850`…`c94157e`), and
  `typescript/src/capabilities.mjs` took rt.mjs's declaration block on top
  of them; what is left in rt.mjs is the recorder itself.
- **`src/sensorium/ts/build.py` 773**, **`rust/tests/mechanics.sh` 795**,
  **`rust/cargo-sensorium/src/convert/redaction.rs` 763** and
  **`convert/frames.rs` 743** — the four the value half grew most. The
  converter pair is the one to watch: `redaction.rs` gained the content and
  RETURN halves this slice.
- **`typescript/src/redact.mjs` 711**, **`src/sensorium/query/flow_cmd.py`
  724**, **`src/sensorium/record/boot.py` 726** (the audit sink's own rule,
  **R25**) and **`record/tracer.py` 698** — the write sites, with room.
- Clear after the splits, and named here so nobody re-splits them:
  `refocus_world.py` **657** (was 788), `redact.py` **304** (was 520).
- **This file 591** after TWO cuts — volume 12 when PR B's section was
  drafted, and volume 13 when the final fix wave's twenty-five lines would
  have taken the live file to **820**. The five lines of headroom the first
  cut left were not a wave's worth, so the rule at the top fired one slice
  earlier than this bullet predicted: the oldest section went to
  [`docs/CARRIED-DEBT-ARCHIVE-13.md`](CARRIED-DEBT-ARCHIVE-13.md) rather
  than the content being trimmed to fit, and both moves were measured before
  they were made. *Five lines of headroom is a file with none.*
- **What this list does NOT cover.** **Twelve** more tracked files sit
  between 770 and 800 and are not named above, because this slice touched
  none of them and none is its seam: `tests/test_flow_identity.py` 797,
  `tests/test_refocus_typescript.py` 794, `tests/test_runs_info.py` 790,
  `tests/test_ts_ingest_meta.py` 789, `rust/tests/acceptance_e9_phases.py`
  788, `rust/sensorium-transform/tests/golden.rs` 788, that crate's
  `tests/edges.rs` 784 and `src/lines/facts.rs` 778,
  `tests/test_refocus_licence.py` 772, `typescript/src/transform.mjs` 771,
  `typescript/probes/check.mjs` 770 and
  `src/sensorium/query/exceptions_cmd.py` 770. A hand-kept list is the thing
  `tests/test_ceiling.py`'s by-pattern enumeration exists to replace: the
  gate is the list, and this section is only what the next editor of these
  particular files needs to know before adding a paragraph.

### Deferred minors, per task

None of these blocks the merge; the final whole-branch review triaged them
and marked **★ next** on the three a next slice should take first, each
with the reason it leads. The rest of the list is flat on purpose — an order
nobody argued for would read as one somebody did.

- **T0 (census, pre-registration, lock):** the census's parameter regexes
  use `[^()]*`, so a nested paren in a default value or a fn-pointer type
  drops that parameter list silently (an under-report); the Rust
  `Some|Ok|Err(name)` pattern misses tuple patterns; the census does not
  cover `tests/` fixtures beyond `ts-spools`; `corpus/cases.py: key` is
  harness code the module docstring overclaims as "rendered";
  `test_the_record_carries_both_headings_inside_section_one` iterates three
  rows and still says "both".
- **T1 (the five splits):** six private helpers (`_write_key`, `_unlink`,
  `_NO_LINK`, `_ROOT_MODE`, `_MARK_ON_CALL`, `_MARK_ON_ACCESS`) are not
  re-exported by their old modules — no importer anywhere, so the
  constraint's purpose holds and its letter does not.
- **T2 (the content rule):** `Cargo.toml`'s `regex` comment is 3 lines, not
  the 1 the brief budgeted; no fixture row mixes two patterns in one text,
  and none exercises lowercase `bearer`; the `gh` trigger literal is broad
  (spec-shaped, noted at **B18**).
- **T3 (the Python recorder):** **R5** (an `unbound` row's NAME is never
  withheld) is asserted by no test since `test_flow.py`'s fixture rename; a
  map-key capture with `trunc` fires on the CLIPPED text; nested-container
  recursion is unpinned past one level;
  `test_an_exc_message_with_nothing_in_it_is_left_alone` uses a shape
  `capture_exc` never writes; `run_target` installs the redaction state
  without a matching `reset()`; a payload dropped by `w.seal()` is counted
  though the trace does not hold it (`late_writes` already reports such a
  run).
- **T4 (the readers):** **★ next** — the name-redaction predicate is spelled
  six times across four modules (`fmt`, `expr` ×2, `flow_values` ×2,
  `flow_cmd`) rather than once as `is_name_redacted(capture)`: six places to
  edit the day the marker's shape moves, and a fifth reader will spell it a
  seventh way. `digest[:8]` on a non-string digest raises; a taken
  container loses `unread_marker`; `_key_step` on a name-redacted map key is
  untested; `flow --value`'s footer counts taken captures as searched with
  no note; a lineage over an object later bound to a firing name silently
  loses that sighting.
- **T5 (the Rust runtime):** no redacted MULTIBYTE text case (both 300-byte
  cases are ASCII); empty-string and CAP-exact texts under a firing name are
  untested; `use std::borrow::Cow` sits outside the std import group;
  `LINE_PAYLOAD_MAX`'s "eight capped deltas" doc is now a floor.
- **T6 (the Rust converter):** the Rust fixture suite no longer exercises an
  unkeyed converter end to end (unit tests do); **B3**'s rule is stated in
  two comments; `tests/test_rust_convert.py` mints a fixed 0600 store key
  per fixture case (a harness change the reviewer accepted).
- **T7 (TypeScript):** **★ next** — no structural guard that `rt.mjs` has
  no bare `dbg(` outside `captures`/`ret`/`pend` (a `graph.test.mjs` source
  assertion would close it): a fourth call site added later would store a
  plaintext capture and no test in the suite would say so. A stale comment at
  `redact.test.mjs:416` still calls `dbg()`/`exc()` "the CONTENT half";
  `_values`'s docstring overstates **B9** (a previously content-marked text
  is never re-scanned). ~~`typescript/README.md:14` says "Eighteen
  modules"~~ — **settled in Task 9** (`f45424b`), which moved the count to
  "Nineteen modules and a version"; Task 7 had added `redact.mjs`'s row to
  the table below it and left the number behind.
- **T8 (the corpus cases):** **★ next** — a case's `env:` could clobber
  `SENSORIUM_DIR` or `PYTHONDONTWRITEBYTECODE` and there is no reserved-key
  guard: a case that names `SENSORIUM_*` would send the run at the
  developer's own store and write into it. The env-value refusal test does
  not assert the case is named; there is no test for a non-mapping `env:`.
- **T9 (docs, versions):** `rust/HONESTY-INDEX.md` row 5's falsifier is
  prose pointing at prose (`check_modes` falsifies only the 0600 clause);
  `typescript/HONESTY.md` has no `## 13.` stub, an index row only, as
  briefed.
- **T10 (the instrument):** no test pins the phase ORDER (grep before
  info); `e16b.sh` hard-codes `baseline-7dd25d2` instead of reading
  `BASELINE`; the baseline tree's own sensorium version is absent from §3's
  versions table (only the uv transcript shows 0.14.0); A's inherited
  preflight refusal still says "part A"; stale `bench-<label>` and copy
  directories are not refused by the launcher; an unreadable `other` file is
  not named in `why` when a non-zero one co-occurs, and the assembler
  coerces a `None` occurrence to 0, so an unreadable file renders as clean
  — neither moves the gate.
- **T11 (the measurement):** **Brice owed** — free `$E16_DIR` (part A's two
  runs and part B's `store-b`, the baseline worktree, the disposable copies
  and a 0600 plaintext token), and `git worktree remove` the
  `baseline-7dd25d2` tree (**R2**).

### Process lessons

- **A spec written a day after the wire it describes will name a number
  that is already taken.** §5.2 called the redacted-by-name LINE tag `3`;
  tag 3 had meant UNBOUND since wire v3 shipped in 0.13.0, one design
  document and one day earlier. Nothing in the spec's own review caught it,
  because a reviewer reads the spec against the spec. **B1** caught it by
  reading `line.rs` — the writer, not the document — before the first line
  of v4 was written. *A wire number is not a spec's to choose; it is the
  writer's to report.*
- **A rule nobody has run over a named list is a rule nobody has read**,
  again, and the second run of A's lesson found more than the first.
  **B27** made the census STATIC — every binding name in `corpus/**`, every
  `args`/`deltas` key in the vectors, every `a`/`d` key in the ts-spool
  fixtures, against a committed
  `tests/fixtures/corpus-firing-names.txt` — and it ran at Task 0, before
  any renderer existed. What it found was **B28**: half its firing bindings
  were a bare `key`, and rule v1 as written would have blinded `watch` on
  the commonest local in the language. The list is the finding, and a census
  that runs in seconds before the expensive thing is rigorous-experiments §1
  paying for itself twice in two PRs.
- **A stale binary on PATH called PR A's corpus green.** CI on `main` at
  `3e4e6b5` was RED on the `rust` job the moment this branch started: three
  corpus questions pin a refusal sentence carrying `sensorium-rt 0.5.0`, and
  a driver built from that tree prints 0.6.0. A's Task 9 corpus run had gone
  through the `~/.cargo/bin` `cargo-sensorium`, which embeds the runtime it
  was BUILT with — so the gate answered about a binary nobody had rebuilt.
  **R3** now makes every Rust corpus run in a plan use a driver built from
  that worktree, first on `PATH`; PR #41 fixed `main`, **R4** cherry-picked
  it here, and **R9** made the one hand-typed pin
  (`test_acceptance_e9_read`) read `RT_VERSION` out of `spool.rs` instead.
  *A version pinned in two places is pinned in neither.*
- **A pre-registration error found before launch is amended beside the
  locked text, never edited** — **R11**, and this is the S5 slice's **P16**
  applied a THIRD time, which is what makes it the repo's rule. §1's Python
  probe command read `sensorium run --focus handle -- main.py`; a bare
  `--focus handle` names a MODULE, so the recording would have carried no
  LINE deltas at all and three of the five rows H6 counts would never have
  existed. The corrected clause (`--focus main:handle`, the spelling the
  corpus's own case uses) sits beside the locked one with its date. The
  vitest copy's omission of `corpus/typescript/secret_in_env` is the second
  amendment, for the same reason: `vitest run secret` is a SUBSTRING filter
  and would have recorded two cases into one trace.
- **A count is a pure function of the trace's contents, or it is a guess.**
  The plan had `redaction.values` counted by the transforms as they applied
  the rule, with a roll-back when a payload was dropped. **R10** moved it to
  the WRITE site — `count(payload)` over what is handed to `add_event` — so
  the number witnesses the trace and not the attempt. The roll-back
  disappeared with it, and the one residual case (a payload dropped by
  `w.seal()`) is a known minor rather than a wrong number in a
  documented key.
- **A leak can be found through prose.** Task 9's reviewer read the
  pre-check's completeness claim — *every positive case carries a trigger*
  — against the code that implements it and found `_TRIGGER` case-sensitive
  where `authorization-header` is `(?i)`: `BEARER <token>` skipped the whole
  table and was stored in plaintext (**R21**). No test failed, because every
  fixture positive was lowercase. *Documentation review is security review
  when the document publishes a completeness claim.*
- **A sweep hole is found by review, before a once-only run.** Task 10's
  own review caught the instrument holding back the WHOLE Rust spool tree
  from the `rust-target/` sweep, so `<pid>.runner.json` and
  `invocation.json` were in no grep set at all — two files H1 would have
  reported on and did not look at. Only the gated `.proc.json` and `.spool`
  files are held back now. A fourth dry run confirmed it, and `mint` became
  a precondition (**R23**) in the same round. An instrument measured once
  has exactly one chance to be right about what it did not look at.
- **Two reviewers on two languages found the same carve-out.** **R17**
  (Rust's synthesised `()`) and **R19** (a `dbg` text of `undefined` or
  `null`) were raised independently, in Tasks 6 and 7, by reviewers who had
  not read each other's rounds; **R19 refined** made the rule symmetric
  across both hands and all three sites. The rule they share — *a value that
  says the program produced nothing hides nothing* — was in neither the spec
  nor the plan. Convergent findings from independent reviewers are the
  cheapest evidence a rule is missing, not a duplicate to close.
