# CARRIED-DEBT — volume 9

The S5 rung-3 section — naming the ambiguity — moved here **2026-09-12** (S5
rung 4's debts, funded) so [`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays
under 800 lines. It is the ninth numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file.

The move was measured before it was made, the way the ledger's own lesson
asks: this slice's section was drafted at **375** lines against a live file of
**591**, which would have taken it to **967**, so the oldest section was cut
rather than the ceiling discovered.

**The wording, the order and the strikes are unchanged**, with no exception:
nothing below was edited in the move, a resolved item is struck through here
exactly as it was in the live file, and nothing is deleted. Six of the seven
strikes below are rung 4's, made while this section was still the live file's
oldest; the seventh — rung 3's *new debts* entry on spec §4.3's whole-word
prose — is **this** slice's, made at its documentation task, and it travels
with the section. Each is dated where it stands. The house rule stated in
`docs/CARRIED-DEBT.md`'s header governs every volume, and a deferred item
below is still open unless it is struck.

## 2026-09-11 — S5 rung 3, naming the ambiguity (Python 0.11.0 / sensorium-ts 0.2.0)

The rung that names rung 2's own Gap 4: the seventeen blocks reading *"no
rule of this recorder reaches a verdict here"* now read a reason,
`untraced catcher`, predicted by a human from source before any of this
code existed. Twelve plan decisions (P1–P12) and thirteen controller
rulings, every one of them in the spec's §12. **The rung ships DONE** —
eight endpoints, each run once, no rule's failure word fired; the gate
that decides the word, `E6-TS‴`, read **0 false names of 20** printed
blocks against the seventeen-row hand read. Nothing was recorded this
rung — one re-read of the kept rung-2 invocation, hashed byte-for-byte
before and after.

### Settled — rung 2's own debts, closed here

Struck where they stand, above, with a dated pointer; restated in full
here because a reader who reaches this section first should not have to
scroll up to find what closed.

- **Gap 1** (the shape key's id mask) — closed: the TypeScript key holds
  the verdict's own words under a mask (`\b[ef]\d+\b`) that exempts
  nothing; the origin site enters only where the verdict names none of its
  own. `E-places` read **28 of 28** SWALLOWED blocks (record §3 row 7,
  §4.4).
- **Gap 2** (three instruments measuring the global binary) and **Gap 3**
  (E7″'s needle list unapplicable as written) — both closed at this
  rung's own Task 4, before Task 5 read a number: every acceptance script
  resolves `<repo root>/.venv/bin/sensorium`; the needle checker prints
  its matching rule into the transcript header (spec §4.3; record §3
  rows 4, 8).
- **Gap 4** (the modal AMBIGUOUS reason had no name) — closed: `untraced
  catcher`, in three variants, still AMBIGUOUS. **0 false names of 20**
  printed blocks; 17 of 17 hand-read rows named; `unnamed` after 0
  (record §3 row 5, §4.2). `HONESTY-BLIND-SPOTS.md` item 27 is
  **narrowed**, not struck — naming the shape is not the same as reading
  what the untraced code did with the failure, which stays unread.
- **The Gap-4 neighbour** (rule 4's absorbing conjunct read trace-global)
  — closed: it now reads within the unit's own window; a logged rethrow
  to the harness reads `PROPAGATED`
  (`corpus/typescript/logged_rethrow_to_harness`, record §4.5).
- **The callback-side bare-rethrow probe marker** — closed:
  `callback_bare_rethrow` added to `escape.probe.test.ts`; **E8‴** read
  **33 of 33** markers (record §3 row 3, §4.6).

### New debts this rung's measurement found

- ~~**`Shape.site`'s `key[1]` fallback is a fence, not a guarantee.**~~ —
  **closed 2026-09-12, S5 rung 4** (`exceptions_group.Shape.site` is a
  required field with no default, handed in by `group_units` from the same
  local the key function is given, so a shape whose site and key disagree
  cannot be built; every hand-built `Shape` in the suite passes it, which is
  the one line the rung-4 E-legacy fence reported, R12). The debt as it
  stood: `exceptions_group.Shape.__post_init__` still reads `self.key[1]`
  when no `site` is handed in — true of Rust's key and of every hand-built `Shape`
  a test constructs, but no longer true in general once a key's second
  component can be something other than a place. **Closing it** means
  making `site` a required argument once the Rust grouping fence lifts
  and every hand-built test passes it explicitly. *Cost if wrong:* a
  future renderer whose key puts something other than a place at index 1
  gets a wrong `site` silently.
- ~~**The store's own command journal, `invocations.jsonl`, sits outside
  the hashed trace set.**~~ — **closed 2026-09-12, S5 rung 4**: the
  pre-registration hashes it with the rest and names its expected delta in
  advance — the LENGTH of §1.5's list of read commands — and the assembler
  verified 12 of 13 hashes equal with the thirteenth appended and not
  rewritten, the journal grown by exactly 13 lines (record §3). The debt as
  it stood: The T5 re-read appended exactly one line to
  it — the read's own receipt, ruled NOT the forbidden write (record
  §4.1) — but §2.1's hash list covers only `traces/*.db` and the spool's
  `*.jsonl`, so a `sha256sum -c` returning all-OK says nothing about the
  journal either way. **Closing it** means the next rung either hashes
  `invocations.jsonl` too, with a pre-registered expected delta of one
  line per pre-registered command, or names it out of scope in the same
  sentence that names the hashed set. *Cost if wrong:* a read that
  silently also wrote a trace would pass this rung's own gate.
- ~~**A fenced pre-registration pattern that matches no file.**~~ —
  **closed 2026-09-12, S5 rung 4**: `e_fences.FENCED_TESTS` names the
  Python reader's real files (`tests/test_exceptions.py`,
  `tests/test_exceptions_synthetic.py`) beside one glob
  (`tests/test_exceptions_rust*.py`) and `tests/test_exceptions_invocation.py`,
  and `existing()` is hoisted above the `git diff` so the refusal precedes
  any measurement. The debt as it stood:
  `tests/test_exceptions_python*.py` (spec §7, §1's E-legacy clause)
  matches no file in this tree — the Python reader's own tests are
  `tests/test_exceptions.py` and `tests/test_exceptions_synthetic.py`.
  `e_fences.py` reports the miss in the cell's `dropped` rather than
  folding it into the gate (record §2.3, §4.7). **Closing it** means the
  next rung's pre-registration names the real files before it is locked.
  *Cost if wrong:* none measured; a fence reading intact for a pattern
  matching nothing is a fence over an empty set.
- **The hand read's uniform prediction leaves two of three variants
  unmeasured on the lens.** All seventeen rows predicted the `returned`
  variant; the `had not closed at the end of the recording` and `later
  unwound with <exc>` variants are pinned by
  `tests/test_exceptions_typescript_reasons.py` and the corpus case
  `untraced_catcher_later_failure` only, never by a hand-adjudicated row
  on somebody else's code. *Cost if wrong:* nothing measured; a future
  lens is the only way to learn whether either variant is common there.
- **`tests/test_acceptance_scripts.py` is 315 lines**, comfortably under
  the 800-line ceiling today, but it is the file every future E-branch
  instrument change grows. Watched, not acted on.
- ~~**Spec §4.3's prose and the shipped instrument disagree on which
  needles are whole-word.**~~ — **closed 2026-09-12, S5 rung 4's debts**:
  §4.3 carries the dated parenthesis this bullet asked for
  (`docs/superpowers/specs/2026-09-10-sensorium-s5-rung3-naming-ambiguity-design.md:248-251`,
  "2026-09-12: the locked transcript header and the shipped instrument
  bind … not this sentence"). The debt as it stood: §4.3 reads
  "whole-word for `Err` and `Rust disposition`"; the shipped rule and the
  locked transcript header are `oid`/`chain`/`Err` whole-word, `Rust
  disposition` substring (record §4.6). *Cost if wrong:* a reader of §4.3
  alone expects a stricter match than the tool makes.
- **The T0 hand read's row 1 calls the untraced catcher "a library
  `try`"** where it is a `.catch` chain on the promise TanStack Query's
  retryer returned. The locked table keeps the words it locked; the
  record's §3 states the correction in place rather than editing the
  table. *Cost if wrong:* none — the prediction the row supports
  (`useCompendiumQuery.queryFn`, `returned`) is the one the reader
  printed.
- **`Index.left_frame` is per-serial and outermost, so a window-2 rethrow
  that stayed inside traced code reads a window-1 root.** The frame the
  reason's sentence names is the outermost frame the SERIAL left, across
  every window that serial has; where a rethrow unwound no further than
  the frame its own predecessor left, `f<child>` is window 1's id rather
  than the rethrow's. This is rung-2 behaviour, untouched here, and the
  PARENT — and so the name the reason prints — is unaffected. Raised at
  T1's review and carried to T5's dispatch; no block on the lens showed
  the shape, so it is recorded rather than measured. *Cost if wrong:* a
  reader following `f<child>` out of a rethrow's block lands on a frame id
  from the wrong window.
- **Task 4's `lens.stamp()` wiring into the three legacy assemblers is
  verified by the slice-2 tooling test only.** `assemble.py`,
  `assemble_rung2.py` and `assemble_slice2.py` gained the call at T4; the
  Global Constraints freeze their results, so not one was re-run against a
  store this rung and the evidence is
  `tests/test_acceptance_s5_slice2_tooling.py` (16/16 green) plus one
  standalone interactive check — new code on old, frozen paths. *Cost if wrong:* a future re-run of an old
  assembler fails or mis-stamps, and this rung's measurement would not
  have caught it.
- ~~**`typescript/acceptance/e7_report.py` rewrites the transcript it is
  handed, in place**~~ — **closed 2026-09-12, S5 rung 4**: the needle-rule
  header is written to a SIBLING, `<transcript>.rules`, and the transcript
  itself is never written, so the reporter is idempotent and the sha256 the
  record pins cannot move under it. The debt as it stood: it prepended the
  header to the same file — it prepends the needle-rule header to the same file
  (`e7_report.py:123-124`), so a second run over one transcript prepends a
  second header, and rung 2's `e7.sh`, which reuses this reporter,
  inherits the write. **Ruled NOT fixed this rung:** an instrument defect
  found after its number is a finding, not a fix, and the transcript's
  sha256 is pinned in the record (§4.1). **Closing it** means guarding on
  a header already present, or writing the header to a sibling file.
  *Cost if wrong:* nothing measured — nobody ran it twice this rung; a
  later re-run mangles the transcript it exists to preserve.
- ~~**`CHANGELOG.md` sits at exactly 800 lines**~~ — **closed 2026-09-11,
  S5 rung 4's T0** (`b71b995`, `docs(changelog): cut 0.8.6 and 0.8.5 to the
  archive before the rung-4 entry`): cut before append, as this bullet
  prescribed, leaving 589 lines and room for a 109-line entry at 0.12.0
  without a second cut. The archive itself is now the constrained file — see
  rung 4's own list below. The debt as it stood: the ceiling
  `tests/test_ceiling.py` enforces, so the next release entry cannot be
  written until its oldest section is cut. The mechanism is this repo's
  own and is NOT this file's numbered volumes:
  [`CHANGELOG-ARCHIVE.md`](../CHANGELOG-ARCHIVE.md), one archive file, the
  oldest entries moved into it as a pure move in a commit that lands
  BEFORE the release entry is appended — the way `0.8.2`, `0.8.1` and
  `0.8.0` moved at rung 1. Cut before append. *Cost if wrong:* the release
  commit fails `test_ceiling.py`, and the entry gets trimmed to fit
  instead of the file being cut.

### Process lessons

- **A hand read predicts words, not a technique.** Row 1's "a library
  `try`" named the wrong syntax and still supported the right prediction,
  because the reason the reader prints does not depend on which untraced
  construct did the catching. A locked table is locked on its
  predictions; a wording slip in its own prose is a correction, not a
  re-open.
- **A pre-registered bracket string can describe a shape the printer
  cannot produce.** `[×3 …]` was read as a shape prediction (printed
  once, with a `×N` bracket) rather than a literal, and the arithmetic
  (130+1+1 = 132) is what the reading was checked against instead. The
  next rung's pre-registration pins brackets by their arithmetic, not by
  a quoted example.
