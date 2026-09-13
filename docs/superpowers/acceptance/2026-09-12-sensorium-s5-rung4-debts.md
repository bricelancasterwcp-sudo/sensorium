# S5 rung 4's debts, funded — E12′, the finally seal, the Rust `unbound`, the closable list: acceptance (pre-registered)

**Status: PRE-REGISTERED.** §1 and §2 were written before any line of this
slice's code existed; §3, §4 and §5 are the measured half and are written
once the endpoints have run.

§1 of this file was written and committed on the feature branch
`feat/s5-rung4-debts` **before any line of this slice's code existed**: the
commit that carried it changed nothing under `src/`, `typescript/src/` or
`rust/`, and under `corpus/` only the three new case directories this
pre-registration is partly made of — `corpus/typescript/focus_finally_return`,
`corpus/typescript/focus_long_string` and `corpus/rust/focus_block_let`, each
committed RED, each with its failing run recorded in the ledger before the
code that turns it green was written. §1 is the locked contract — after a
number is read, no threshold moves, no arm is added and nothing is re-run; an
instrument defect found before a number is read is fixed and written into
§2.3 with its commit, and found after, it is a finding. §2 keeps this slice's
preflight pins. §3, §4 and §5 are written when the endpoints have run.

The two things this slice can be tempted to move after the fact are **the two
hand tables** — the H2′ function-like count and the seal-deferred census —
because they are the only parts of this pre-registration that a human's
reading of source decides rather than an instrument. They live in
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-h2-handcount.md` and `docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-census.md`, were written before
`typescript/acceptance/e12p_report.py` and `typescript/acceptance/census_deferred.mjs`
existed, and are pinned by sha256 as §1's last two lines; the lock test
recomputes both shas and refuses a table that has moved by a byte.

**What this slice reads, and what it does not re-run.** E12′ re-adjudicates
data that is already committed: rung 4's thirteen read transcripts under
`docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/` and
the store its trace hashes describe. The three numbers H2′, H4′ and H5′ are
rung 4's own, read once there; the question this slice asks is whether an
instrument without the four parser defects §4.4/§4.5 of that record names can
see them. Only H8′ records anything new, and it is run LAST.

The lock is enforced by `tests/test_acceptance_s5_debts_lock.py`, which
recomputes §1's own sha256 and, separately, compares each of §1's four
verbatim bodies against `git show <sha>:<source>` — so "verbatim" is a claim
a test holds, not one this prose makes.

## 1. Pre-registration

Four blocks, copied verbatim from the two documents that own them, and nine
sub-sections that write down what those blocks defer to this record. Nothing
in the four blocks is paraphrased, reordered or reworded; the only editorial
act is that each source section's own heading is carried as the `###`
sub-heading that introduces its body here — two of them (`### 3.3`, `### 3.4`)
are already `###` in their source and are carried unchanged, and the other two
are `##` there and appear as `###` below — so that this record keeps its own
§1–§5 numbering. The bodies are byte-for-byte the source sections, each read
to the next heading in its source, which is why the plan block below ends with
the horizontal rule that terminates it in the plan file: the rule is part of
the section's body, not a choice made here. The four are carried in the order
the plan block itself names them. Sources, at the commits named:

- `docs/superpowers/specs/2026-09-12-sensorium-s5-rung4-debts-design.md` at
  **`3ecbb65`** (this branch's design commit) — `### 3.3 The three readings,
  pre-registered`, `### 3.4 H8′ — the live confirmation`, and `## 8.
  Acceptance — pre-registered`, each whole
- `docs/superpowers/plans/2026-09-12-sensorium-s5-rung4-debts.md` at
  **`5c36baa`** (this branch's plan, at its single plan commit) — `## Pre-registration (…)`,
  whole, up to `### Task 0`

One box path appears inside §1, and only inside the verbatim §3.4 block: that
block's own words name the lens as the VTT frontend copy at
`/mnt/extra/sensorium-s5/vtt/frontend`. The block is carried byte-for-byte, so
the path is carried with it; editing it out would break the claim the lock
test holds. It is sanctioned here for that reason and for no other. Everywhere
else in this slice the lens is `<lens>` and the store is `<store>`, and §2's
pin tables are the only other place in this record where a box path is
written.

### 3.3 The three readings, pre-registered

Locked in the new record's §1 before `e12p_report.py` exists; each read ONCE;
a reading that does not match is a **STOP** recorded as a finding, no re-roll,
no second parser.

| Endpoint | Reads | Holds when |
|---|---|---|
| **H2′** | `node resolve.mjs` output in the record; `meta.functions_focused`, `meta.focus_matched` off the committed trace; a HAND count under the container rule written at T0 (the three named functions plus every function-like nested in them, read from `diceQueue.ts` at VTT `0091e97`) | hand count = resolver sites = `functions_focused` = **6**; `focus_matched` = **5**, and the one qualname two sites share is `buildDiceQueueEntry.<anonymous>`; the suite half exactly as §4.2 quotes it |
| **H4′** | the three committed `watch` transcripts | W1/W2/W3 all `SATISFIED`/exit 0; W2's HITs = **52**, of which **0** on a row whose `unbound` names `count` (the `while`'s completion rows — §1.2's clause as written) and **2** at line 72, both head rows (`m=[ … ]`, no `unbound`, `count=1`); W3's HITs = **15**, all at line 72 on rows carrying `m=null` and `unbound:count,sides` |
| **H5′** | the two committed `flow --value` transcripts + the trace's `code` table | S1 found (**9** sightings at `:74` in `parseDiceGroups`); S2 found (event `e10`, CALL, qualname `parseDiceGroups`, code-object line **68**); `elsewhere_not_gated` = **5** (1 + 4 RETURN rows); the transcripts' own `sightings:` totals **10** and **5** quoted beside; `unpredicted` = **0** |

The numbers are rung 4's, read once there, quoted here as the pre-registered
expectation of a parser that can see them. They are not re-measured; the
question is whether an instrument without the four defects reads them.

### 3.4 H8′ — the live confirmation

One run, last in the slice, on the lens (`/mnt/extra/sensorium-s5/vtt/frontend`,
VTT `0091e97`): the rung-1 manifest verified before and after (748 OK / 0
FAILED, else stop before start), then `sensorium ts run --focus <the three
specs> -- npx vitest run src/lib/diceQueue.test.ts` under this slice's driver
and recorder. Holds when: `node resolve.mjs` prints the same six sites;
`info` prints `focus matched: 5 … (6 functions)`; H3's nine LINE rows are
TEXT-equal to the record's §1.1 hand count (event ids may differ, the row text
may not); the suite line reads `26 passed (26)`; the marker grep and the
wrapper listing read clean. The focused file carries no return-inside-a-finally
shape (§4.6's census pins that), so this slice's transform of it must be
byte-identical to 0.3.0's: at T-last, `e6f5035`'s `transform.mjs` is run from
a temporary checkout over the same `diceQueue.ts` with the same three specs,
and the diff against this slice's output is empty. That empty diff is the
eighth clause.

### 8. Acceptance — pre-registered

Every endpoint below is written into the record's §1 and committed BEFORE the
instrument or the code it measures exists (T0), then read ONCE. A clause
that does not hold is a **STOP** recorded as a finding; nothing is re-run,
re-rolled or re-parsed. Instrument defects found after a number are findings,
and the number stands.

| Endpoint | Question | Clauses (all must hold) |
|---|---|---|
| **E12′ H2′/H4′/H5′** | does an instrument without the four defects read what rung 4's post-mortem read by hand? | §3.3's table, plus the hash preflight §3.1 |
| **H8′** | does this slice's recorder still produce the same rows on the same lens? | §3.4's eight clauses |
| **E13** | is a finally after a return recorded, and only where the shape exists? | `focus_finally_return` green with its RED run in the ledger; the census lists (§4.6) match the golden diff exactly; the lens file's list is empty; `HONESTY-COST.md`'s cited numbers are untouched (the seam and the seal change no unfocused wrapper) |
| **E14** | does Rust's row say what its block unbound, and does the fold honour it? | `focus_block_let` green; `v40` round-trips; the tag-3 refusal cases in `spool/tests.rs`; every existing Rust corpus case equal (no block-free fragment moved); `refocus_*` cases equal |
| **E6-TS′** | does the re-registered table hold? | `e6tsppp.py` over every TS case with an `exceptions` question: every row matches, `focus_catch_binding` included; the swallow set non-empty |
| **fences** | did anything else move? | `python corpus/run_corpus.py --require-driver` every case equal (all three languages); `.venv/bin/python -m pytest -q`; `cargo test --workspace`; `npm --prefix typescript test`; the probes; `tests/test_ceiling.py`; the E7 needle on TS output; `e_fences.py` legacy and branch — the legacy fence's `FENCED` set covers `rust/` whole, `exceptions.py`, `exceptions_rust.py` and the four `test_exceptions*` files; this slice edits `rust/` by design (§5) and NOTHING else in that set, so the record's §1 names `rust/` as the one fenced path expected to move and the fence's report must list only paths under it |

Baselines (suite counts, corpus case count, the ceiling census, `df`) are
taken at T0 and written into the record's §2, the ambient pins.

### Plan section "Pre-registration (Task 0 commits spec §8's table verbatim as the record's §1, plus this block)" — verbatim

The record's §1 carries, verbatim: spec §3.3's table (H2′/H4′/H5′), §3.4's eight clauses (H8′), §8's table (every endpoint), and this block. Read ONCE each; a clause that does not hold is a STOP recorded in §4 as a finding.

- **§1.1 The hashes.** The thirteen transcripts under `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/` listed by `git ls-files` with each file's sha256 (`sha256sum` format), and the store list `…-focus-tracehashes.txt` cited by its own sha256. Verified by `e12p_report.py` before any cell is read; a mismatch is exit 4 and no number.
- **§1.2 H2′'s hand count** — `…-h2-handcount.md`, sha-pinned as §1's last line (A4). Predicted N = 6; predicted `focus_matched` = 5 with the one shared qualname `buildDiceQueueEntry.<anonymous>`.
- **§1.3 H4′** — W2's HITs 52, of which 0 on a row whose `unbound` names `count` and 2 at line 72 (head rows: `m=[ … ]`, no `unbound`, `count=1`); W1 31 of 64; W3 15 at line 72 on rows carrying `m=null` and `unbound:count,sides`; verdict words and exits as §1.2 of the rung-4 record.
- **§1.4 H5′** — S1 found (9 sightings, `:74`, `parseDiceGroups`); S2 found (`e10`, CALL, `parseDiceGroups`, code-object line 68); `elsewhere_not_gated` 5; the transcripts' `sightings:` totals 10 and 5; `unpredicted` 0.
- **§1.5 E13** — `…-census.md` (A5), sha-pinned: the hand list of seal-deferred functions in the three roots; predicted lens list EMPTY; `census_deferred.mjs` must print it exactly; the transform golden diff 0.3.0→0.4.0 over `typescript/probes/src` and `corpus/typescript` changes exactly those functions' wrappers and no other byte (Task 11's diff); `corpus/typescript/focus_finally_return` green with its RED run logged in the ledger at T0.
- **§1.6 E14** — `corpus/rust/focus_block_let` green with its RED run logged; `v40` round-trips; the tag-3 refusals; every other Rust corpus case equal; `refocus_*` equal.
- **§1.7 E6-TS′** — every TS case with an `exceptions` question matches the table, `focus_catch_binding` at 0, the swallow set non-empty (rung 3's instrument `e6tsppp.py` + `e6ts.py`).
- **§1.8 Fences** — the corpus (`--require-driver`, all three languages), pytest, `cargo test --workspace`, `npm --prefix typescript test`, the probes, `tests/test_ceiling.py`, `e7_report.py` needle `sensorium run --focus` on TS output, `e_fences.py` legacy (expected movers: paths under `rust/` ONLY) and branch.
- **§1.9 H8′** — spec §3.4's eight clauses, run LAST.

---

### 1.1 The hashes

The thirteen transcripts of rung 4's reads, as `git ls-files` lists them, with
each file's sha256 in `sha256sum` format, and the store list cited by its own
sha256. `e12p_report.py` verifies every line of this list before any cell is
read; a mismatch is **exit 4 and no number**, because a reading of data this
record does not describe is not the reading §1 pre-registers. The list is
generated by command (`git ls-files <the reads directory> | xargs sha256sum`),
never typed.

```
a529100e614b19d27d6cf4690cf9d98252ec4f9bc6f4f39ec9538571336b4ecb  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/01-info-U1.txt
2d0c6d0bfa6ae082f52a536fc89289025780034f1fe9494effda16370c76e30a  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/02-info-F1.txt
4c225fa228ced9820a6479161cfb782505743f4ba806e9f7e50bc60f2a7e8356  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/03-watch-U1-at-parseDiceGroups-expr-groups-0.txt
431d519a8da09c1baf32bbd0095a49ef54fe79f030772becf8a7da14af0fb5a8  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/04-watch-F1-at-parseDiceGroups-expr-sides-20.txt
89b3dbdba26d7e35460dab1bda647a24cc3ee62867aa7d5e0bff31869a5a9a51  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/05-watch-F1-at-parseDiceGroups-expr-count-1.txt
66a807ed267062b8b867431d80874e16fe9a12f958e248b8a7a2ec67b02c1fc3  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/06-watch-F1-at-parseDiceGroups-expr-m-null.txt
6e89e7ef44c2282115d50ceb80998e258f2b4e1609544b24714d79ab7182f14e  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/07-flow-F1-value-20.txt
27fe68caa21fe631284554811a6b3fcda2344e7c3ae1925d2f821ddcf064933f  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/08-flow-F1-value-1d20.txt
55fd6dce91761ff5048f7a47890692d4674373b54b7ee380fa71ce1bba98d064  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/09-grep-F1-dice-kind-LINE.txt
7970409062cfd3400c01e8c6b7dd9f8237f98cd04912487cac8f3f80a2239442  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/10-flow-F1-object-e367-dice.txt
865decb56538c9aa15e995fc390a6db2a3bd43ccb26c74463502a22b124b7e18  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/11-grep-F1-parseDiceGroups-kind-CALL.txt
f89e64b666efc42b062cfd8a660af76929e452e2b25488f83c6a3f906f253c64  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/12-frame-F1-fn-parseDiceGroups.txt
702d39ad9a78e2834fe9acfe84a89b673bc0c6f578c1d8642d94aaa1631d7fa6  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-reads/13-tree-F1.txt
```

And the store list, which the copy of the rung-4 store is checked against
before any cell is read:

```
32a5612111e981b461061efd32f0d6d1d4dc1da561fc34ae6701f26b336deafc  docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus-tracehashes.txt
```

Twelve of that list's thirteen lines must verify against the store and the
thirteenth, `invocations.jsonl`, is checked as an APPEND — its first six lines
still hashing to what rung 4 listed — for the reason rung 4's own §2.1 gives:
the hash list was taken after the arms and before any read, so the reads
themselves appended to the journal. §2 records the reading taken at T0.

### 1.2 H2′'s hand count

The count is a table in its own file,
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-h2-handcount.md`,
pinned by sha256 as §1's second-to-last line (plan ruling A4). It lists every
function-like the three rung-4 specs select under `focus.mjs`'s container
rule, one row per site, `| n | qualname | line | kind | how selected |`, and
its last line is `N = 6`.

- **The count (the gate): N = 6.** The hand count, the site list `node
  resolve.mjs` printed in the rung-4 record's §4.2, and the committed trace's
  `meta.functions_focused` are all **6**; any disagreement between the three
  is a STOP with the three lists beside each other.
- **The set (the second reading):** `meta.focus_matched` = 5, and the one
  qualname two sites share is `buildDiceQueueEntry.<anonymous>` — the two
  default-parameter arrows of `buildDiceQueueEntry`, two functions with one
  spelling.
- **The suite half** holds exactly as the rung-4 record's §4.2 quotes it: F1
  and U1 both printing ` Test Files  1 passed (1)` and `      Tests  26 passed
  (26)`, both exiting 0, and `grep F1 parseDiceGroups --kind CALL` printing
  `parseDiceGroups(formula='1d20')` first.

### 1.3 H4′

Read off the three committed `watch` transcripts (`04-`, `05-`, `06-`), whose
verdict words and exits are the rung-4 record's §1.2: `SATISFIED` and exit `0`
three times.

| # | `--expr` | pre-registered reading |
|---|---|---|
| W1 | `sides == 20` | **31** HITs of **64** evaluable sites |
| W2 | `count == 1` | **52** HITs of **77** evaluable sites, of which **0** sit on a row whose `unbound` names `count` — the `while`'s completion rows, which is §1.2's clause as rung 4 wrote it — and **2** sit at line 72 and are HEAD rows (`m=[ … ]`, no `unbound`, `count=1`) |
| W3 | `m == null` | **15** HITs, all at line 72, all on rows carrying `m=null` and `unbound:count,sides` |

W2's clause is the one rung 4's instrument read too strongly (its §4.4): a
`line` alone cannot tell a `while`'s head row from its completion row, and the
row's own payload can. The re-registered reading classes a HIT by its payload
— a row carrying `unbound` is a completion row — which is the fix §3.2 names
and the reason this endpoint is worth re-reading at all.

### 1.4 H5′

Read off the two committed `flow --value` transcripts (`07-`, `08-`) and the
trace's `code` table.

- **S1 found:** **9** sightings of `20` as `sides` at `diceQueue.ts:74` inside
  `parseDiceGroups`.
- **S2 found:** event **`e10`**, a **CALL** row, qualname **`parseDiceGroups`**
  — the token before its `(` — and line **68**, the code object's own line,
  read from the trace because a printed CALL carries no `L<line>`.
- **`elsewhere_not_gated` = 5**: one row from the `--value 20` transcript and
  four `RETURN` rows from the `--value "'1d20'"` one, which the old parser
  could not all read because a `RETURN` arrow takes one space or two.
- The transcripts' own printed totals, quoted beside the cell: **`sightings:
  10`** and **`sightings: 5`**.
- **`unpredicted` = 0**: no third triple inside the gated population.

### 1.5 E13 — the finally seal

The census is a table in its own file,
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-census.md`,
pinned by sha256 as §1's last line (plan ruling A5): three tables in the order
probes / corpus / lens, each `| file | qualname | line |` and each ending
`N = <count>`, listing by hand every function whose own body returns from
inside a try-with-finally. The predicted counts are **0**, **1** and **0** —
the lens list is EMPTY, which is also H8′'s eighth clause.

E13 holds when all four hold:

1. `typescript/acceptance/census_deferred.mjs`, once it exists, prints exactly
   those three lists.
2. The transform golden diff 0.3.0→0.4.0 over `typescript/probes/src` and
   `corpus/typescript` changes exactly the wrappers of the functions the
   census named — one, `settle` — and no other byte.
3. `corpus/typescript/focus_finally_return` is green, its RED run at T0
   recorded in the ledger. The case's own questions are the endpoint: `watch
   --at settle --expr cleanup == 1` SATISFIED at **2** of the sites it could
   be evaluated at, with a HIT on `LINE settle L13  cleanup=1`; `frame --fn
   settle` carrying exactly **3** LINE rows, the RETURN following the
   finally's; and `tree` rendering `note()` as `settle`'s CHILD, two spaces
   deeper than `settle`.
4. `typescript/HONESTY-COST.md`'s cited numbers are untouched — the seam and
   the seal change no unfocused wrapper.

The three LINE rows of clause 3 are counted by hand from design §4.3 and
`docs/trace-format/TYPESCRIPT-KEYS.md`'s statement table, before the run: one
for `let cleanup = 0;` (L8), one for `cleanup = 1;` (L13) and one for
`note(cleanup);` (L14, an expression statement writing no identifier, so an
empty `deltas` row that says the line ran). Nothing else mints one — `return
1` and `return 2` never complete normally, the `if` at L10 diverges through
its body's return and its head binds nothing, and the `try` statement itself
never completes normally either, so the probe after it is never reached.

### 1.6 E14 — the Rust `unbound`

E14 holds when all five hold:

1. `corpus/rust/focus_block_let` is green, its RED run at T0 recorded in the
   ledger. Its questions are the endpoint: `frame --fn shape` carrying
   `unbound:x` on the plain block's row at `main.rs:16`, `unbound:first` on
   the `if let`'s at L20, `unbound:item` on the `for`'s at L23 and
   `unbound:n,big` on the `match`'s at L26 — the arm pattern's name first and
   the arm body's `let` second, which is source order (design §5.2); `watch
   --expr x == 2` SATISFIED at **2** of the sites it could be evaluated at,
   with `x` reported *not in scope* after the block; and `watch --expr x == 1`
   SATISFIED at **2 of the 4** sites the predicate could be evaluated at, both
   hits BEFORE the block — the shadow reading R4, which is the costly half and
   is pinned on purpose.
2. `docs/trace-format/vectors/v40-rust-line-unbound.json` round-trips.
3. The tag-3 refusal cases in `rust/sensorium-rt/tests` / `spool/tests.rs` hold
   — a name that is both a delta and an unbound in one record is a refusal
   naming the record and the name.
4. Every other Rust corpus case is equal: no block-free fragment moved.
5. Every `refocus_*` case is equal.

### 1.7 E6-TS′

`e6tsppp.py` over every TypeScript case with an `exceptions` question: every
row matches `e6ts.PRE_REGISTERED`, `focus_catch_binding` included at **0**
SWALLOWED, and the swallow set is non-empty.

`focus_catch_binding`'s row was added by rung 3's procedure in its OWN commit,
before the case's `exceptions` question exists (spec §6.2, plan ruling A7).
The hand adjudication, carried in that commit's message: `attempts` wraps
`parseKey(key)` in a `try` whose `catch (e)` at `retry.ts:17` bumps a counter
and drops the reason, so the answer carries **one HANDLED** at that clause,
**nothing swallowed**, and **no `ambiguous by reason:` line** — a verdict the
tool reaches with confidence grows no reason line. The case therefore takes no
row in `PRE_REGISTERED_REASON_LINE`, whose own rule is that a case absent from
it is not checked for one.

**Amendment, 2026-09-12 — the reason line is PINNED, not left unchecked**
(controller ruling P6, committed alone and adding a second sha, as the rung-4
design's §8 requires of a dated amendment inside §1). The paragraph above ends
"The case therefore takes no row in `PRE_REGISTERED_REASON_LINE`, whose own
rule is that a case absent from it is not checked for one." That sentence read
plan ruling A7's "one row" as the binding instruction. The SPEC binds: §6.2
writes the case's pre-registration as *"row: **0** SWALLOWED, reason line
`None`"*, and `None` in that table is a claim of its own — "no such line at
all" — not an absence. **The pre-registered claim is therefore BOTH: `e6ts.
PRE_REGISTERED["focus_catch_binding"] = 0` AND
`e6ts.PRE_REGISTERED_REASON_LINE["focus_catch_binding"] = None`**, the second
carried in its own commit on the same day and still before the case's
`exceptions` question exists. E6-TS′ now holds only if the answer prints no
`ambiguous by reason:` line at all, which is strictly more than the sentence
above asked for; the hand adjudication it rests on — one HANDLED at
`retry.ts:17`, nothing swallowed, no reason line — is unchanged, and this
amendment moves no other row, method or derivation of §1. `ORIGINAL_LOCK` in
`tests/test_acceptance_s5_debts_lock.py` carries the sha of §1 before this
paragraph and `BYTE_LOCK` the sha after it, so the amendment is a fact the
lock publishes rather than a claim this prose makes.

**§1.7 second amendment (2026-09-12, Task 8, ruling P16) — the SWALLOWED
count was misread from a sibling command's vocabulary** (committed alone
and adding a third sha to the pair above, as the rung-4 design's §8
requires of a dated amendment inside §1). Task 8, assigned to write
`focus_catch_binding`'s `exceptions` question, ran it and read: `dispositions:
swallowed 1` — not the **0** this section pre-registers. The hand
adjudication above read `retry.ts:17`'s `catch (e) { count += 1 }` in
`grep --kind HANDLED`'s vocabulary — a HANDLED event, traced with
confidence — and concluded "nothing swallowed" from that confidence.
`src/sensorium/query/exceptions_typescript.py`'s own rule (module
docstring, line 30-32) says otherwise: "``swallowed``   an absorbing
handler took it and the frame holding that handler then returned." The
clause neither rethrows nor logs (`how="catch"`, in `ABSORBING`, not
`ESCAPING`) and `attempts` returns normally once the loop ends — exactly
that rule, and the same shape as `silent_swallow`, already pinned at 1.
HANDLED is a fact about attribution, not about disposition, and the
earlier adjudication read one for the other.

The clause this section pre-registers — E6-TS′, `focus_catch_binding` at
**0** SWALLOWED — stands as it was written, before any code existed, and is
now expected to STOP at measurement for exactly that reason: the row it
pins is the wrong one, so a faithful measurement of the case cannot match
it. **E6-TS″** is the corrected clause this amendment pre-registers beside
it, not in place of it: `e6ts.PRE_REGISTERED["focus_catch_binding"] = 1`
and `e6ts.PRE_REGISTERED_REASON_LINE["focus_catch_binding"] = None`
(unchanged — a SWALLOWED verdict carries no `ambiguous by reason:` line
either), derived from the disposition rule quoted above rather than from a
hand read of a different command's output. Task 11 measures both clauses
once each and reports both: E6-TS′ as pre-registered, expected to STOP, and
E6-TS″ as the corrected clause this slice ships. This amendment still moves
no table row, method or derivation of §1 above it — the "swallow set is
non-empty" clause and the reason-line pin both hold under E6-TS″ exactly as
under E6-TS′. `BYTE_LOCK` in `tests/test_acceptance_s5_debts_lock.py` now
carries the sha of §1 after this paragraph too; `ORIGINAL_LOCK` is
unchanged — still the pre-registration commit, before either amendment.

### 1.8 Fences

Nothing else moved:

- `python corpus/run_corpus.py --require-driver` — every case equal, all three
  languages.
- `.venv/bin/python -m pytest -q`; `cargo test --workspace`; `npm --prefix
  typescript test`; `npm --prefix typescript/probes run probe`;
  `tests/test_ceiling.py`.
- `e7_report.py`'s needle grep at 0 over this slice's TypeScript output.
- `e_fences.py` legacy and branch. The legacy fence's `FENCED` set is, quoted
  from `typescript/acceptance/e_fences.py`:

```
FENCED = ("src/sensorium/query/exceptions_rust.py",
          "src/sensorium/query/exceptions.py",
          "rust/",
          "tests/test_exceptions_rust*.py",
          "tests/test_exceptions_invocation.py",
          "tests/test_exceptions.py",
          "tests/test_exceptions_synthetic.py")
```

  **`rust/` is the one fenced path expected to move**, because §5 funds the
  Rust `unbound` by design; the fence's report must list only paths under it,
  and a changed path anywhere else in that set is a STOP. Every other entry of
  the set is expected to show zero diff against the branch point.

### 1.9 H8′ — the live confirmation, run LAST

Spec §3.4's eight clauses, carried verbatim above and enumerated here in the
order they are checked. One run, last in the slice, on the lens.

| # | clause |
|---|---|
| 1 | the rung-1 manifest verifies before AND after the run — 748 OK / 0 FAILED, else stop before start |
| 2 | `node resolve.mjs` prints the same six sites |
| 3 | `info` prints `focus matched: 5 … (6 functions)` |
| 4 | H3's nine LINE rows are TEXT-equal to the rung-4 record's §1.1 hand count — event ids may differ, the row text may not |
| 5 | the suite line reads `26 passed (26)` |
| 6 | the marker grep reads clean |
| 7 | the wrapper listing reads clean |
| 8 | `e6f5035`'s `transform.mjs`, run from a temporary checkout over the same `diceQueue.ts` with the same three specs, diffs EMPTY against this slice's output — the focused file carries no return-inside-a-finally shape, which §1.5's census is what pins |

---

The two hand tables are the predictions E12′ H2′ and E13 are judged against.
Both were written at Task 0, before any of this slice's code existed, and are
pinned here by content: a table edited after a number is read is not a
prediction, so each file's sha256 is one of §1's last two lines and the lock
test recomputes both.

9d5b4651c63368bff3b31cd1580b579e7c844eabf82b1c2147fc94a1a022f7e0  docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-h2-handcount.md
d94ae930e6293ea6c65fd1777177a9b309b4cf6462e3ddfa6b57ae190535aa06  docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-census.md

## 2. Ambient pins (preflight, recorded before any of this slice's code exists)

Every value below is the output of the command beside it, run on this box on
2026-09-12 between 09:14 and 09:40 local time (`-05:00`) — the session that
opens this slice — before any file under `src/`, `typescript/src/` or `rust/`
was touched. The lens is the VTT frontend **copy** (VTT `0091e97`) that the
first row below pins, abbreviated `<lens>` throughout the rest of this slice's
files; the VTT working repository itself was neither read nor touched (the
rung-4 record spells its path here; this one does not, so that §2's rule below
holds without an exception), and the lens
was read here by `sha256sum -c` and by opening three functions of
`src/lib/diceQueue.ts`, all of which only read. The store rung 4 recorded
into, abbreviated `<store>`, is read-only for this slice: E12′ re-adjudicates
committed transcripts and hashes that store, and records nothing into it. The
build and log directory this slice writes into is abbreviated `<target>`, and
like the other two labels it is spelled out in exactly one place, the pin
table below.

Box paths are written **only in the pin tables of this section** — this table
and §2.1's, §2.1 being part of §2 — because a pin without its location is not
a pin, and the tables are the one place this record sanctions them. This prose
names the lens and the store by their labels alone, so every box path in §2 is
a table row. The rule that no box path is committed binds every other file
this slice produces, as it did at rung 1, slice 2, rung 2, rung 3 and rung 4.

| Item | Command | Value |
|---|---|---|
| `<lens>`, the label | `ls -d /mnt/extra/sensorium-s5/vtt/frontend` | exists — the VTT frontend **copy** at VTT `0091e97`, read-only for the whole slice. `<lens>` abbreviates this path throughout the rest of this slice's files |
| `<store>`, the label | `ls -d /mnt/extra/sensorium-s5/store-rung4ts` | exists — rung 4's store, the data E12′ re-reads. `<store>` abbreviates this path; this slice opens it read-only and writes nothing into it |
| node | `node --version` | `v24.16.0` |
| npm | `npm --version` | `11.13.0` |
| nproc | `nproc` | `16` |
| 1-minute load, at pin time | `date -Iseconds; cat /proc/loadavg` | `2026-09-12T09:33:40-05:00`, then `0.39 0.62 0.58 1/2566 513231` — 1-minute load **0.39** |
| free disk `/` | `df -h /` | `4.2G` available on `/dev/nvme0n1p2` (100% used, 915G total) — the refusal floor is 3 GB; nothing this slice writes goes to `/` |
| free disk `/mnt/extra` | `df -h /mnt/extra` | `85G` available on `/dev/nvme1n1p1` (82% used, 469G total) — the refusal floor is 8 GB, and H8′'s one run writes on this device |
| worktree | `git rev-parse --abbrev-ref HEAD` | `feat/s5-rung4-debts`, at `/mnt/extra/sensorium-rung2/s5-rung4-debts`, cut from `docs/s5-rung4-debts-design` at `5c36baa` |
| the branch point | `git rev-parse 5c36baa` | `5c36baa7ce7bd11ff6e49630d5f918e8a48f022a` — the plan's single plan commit. **T0** for this slice, and the base every fence diffs against |
| `git rev-parse HEAD` at pin time | `git rev-parse HEAD` | `997f16890b0dcce13591407e2ab692520827567b` — Task 0's first commit, the E6-TS row alone (three lines of `typescript/acceptance/e6ts.py`). Nothing under `src/`, `typescript/src/`, `rust/` or `corpus/` had moved when these pins were taken |
| worktree venv | `.venv/bin/python -V` | `Python 3.13.13` (editable install of this worktree) |
| sensorium, worktree venv | `.venv/bin/python -c "…version('sensorium')"` | `0.12.0` — becomes `0.13.0` at Task 12 |
| sensorium, global tool | `$(dirname $(readlink -f $(which sensorium)))/python -c "…version('sensorium')"` | `0.12.0` — the same version. The global tool is **never reinstalled from this worktree**; every instrument of this slice runs `.venv/bin/sensorium` |
| sensorium-ts | `node -e "console.log(require('./typescript/package.json').version)"` | `0.3.0` — becomes `0.4.0` when the seal lands |
| the Rust crates | `grep -m1 '^version' rust/{sensorium-rt,sensorium-transform,cargo-sensorium}/Cargo.toml` | `sensorium-rt 0.4.1` → `0.5.0` (§5.3); `sensorium-transform 0.4.4` → `0.5.0` (spec R6, §5.2: the rewriter that splices a block-like statement's `line_unbinding` call moves with the wire — this arrow was missing from the row when §2 was pinned, and is annotated here at Task 11 before any endpoint ran, on Task 6's note); `cargo-sensorium 0.5.3` → `0.6.0` (§5.4) |
| `<target>`, the label | `ls -d /mnt/extra/sensorium-rung2/s5-debts-target` | exists — the `CARGO_TARGET_DIR` every cargo build and every corpus run of this slice exports, and where the two baseline logs were written. `<target>` abbreviates this path throughout the rest of this slice's files |
| the driver every corpus run used | `SENSORIUM_CARGO_SENSORIUM` | `<target>/release/cargo-sensorium`, built from this worktree at `5c36baa`. The box's `PATH` driver is the installed `0.5.3` and is not reinstalled from here until after merge |

### 2.1 The lens, and rung 4's committed data

The lens is named by its own line, which is what every other file of this
slice quotes instead of a path.

| Item | Command | Value |
|---|---|---|
| the lens line | `cat typescript/acceptance/LENS.txt` | `VTT frontend at 0091e97 — vitest 4.1.9, vite 6.4.3, jsdom 29.1.1, node v24.16.0, 16 cores (powersave); snapshot taken under sensorium 0.8.7 / sensorium-ts 0.1.0 at 29c5059` — one line, the whole file |
| lens manifest, verified before the hand read | `cd <lens> && sha256sum -c /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | exit `0`, **748 OK, 0 FAILED** — the lens is byte-identical to the state rung 1 left it in and rungs 2, 3 and 4 read it in, so §1.2's hand count read the same source rung 4's arms recorded |
| the manifest file | `sha256sum /mnt/extra/sensorium-s5/manifest-rung1-before.txt` | `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`, **748** lines — the same sha the rung-4 record pins for it and for `manifest-after.txt` |
| the subject | `wc -l <lens>/src/lib/diceQueue.ts` | `212` lines; `parseDiceGroups` at 68, `forcedDiceFromSource` at 127, `buildDiceQueueEntry` at 194 — the three specs §1.2 counts under. `grep -n finally` over the file exits 1: no `try` and no `finally`, which is §1.5's third census list and H8′'s eighth clause |
| rung 4's reads | `git ls-files <the reads directory> \| wc -l` | **13** transcripts, whose sha256 list is §1.1 |
| rung 4's store, hashed | `cd <store> && sha256sum -c docs/…/2026-09-11-sensorium-s5-rung4-focus-tracehashes.txt` | **12 of 13 OK**, the thirteenth `invocations.jsonl` FAILED — exactly what the rung-4 record's §2.1 records and for the same reason: the hash list was taken before rung 4's own reads, which appended to the journal. E12′ checks that line as an APPEND |
| the store's hash list | `sha256sum <the trace-hash file>` | `32a5612111e981b461061efd32f0d6d1d4dc1da561fc34ae6701f26b336deafc` — the second fence of §1.1 |

### 2.2 The ceilings, the suites, and the counts this slice's endpoints move against

**The suites**, green at the branch point. The Python, Node and `tsc` numbers
are one background run from this worktree at `5c36baa`, logged to
`<target>/baseline-py-node.log`; `cargo test --workspace` is its sibling
`<target>/baseline-cargo.log`; the probes were run again at T0 by the command
named, because the log kept only that run's last lines.

| Item | Command | Value |
|---|---|---|
| Python | `.venv/bin/python -m pytest -q -p no:cacheprovider` | **4100 passed, 24 skipped**, 170.15s, exit 0 |
| Rust | `cargo test --workspace` from `rust/` | every crate `ok`: **190 passed, 0 failed, 23 ignored** over 13 test binaries, exit 0 |
| Node | `npm --prefix typescript test` | **pass 522, fail 0**, 0 cancelled, 0 skipped, 0 todo, exit 0 |
| TypeScript types | `npm --prefix typescript run check` | `tsc -p tsconfig.json`, no output, exit 0 |
| the probes | `SENSORIUM_TIER=call SENSORIUM_SPOOL=<tmp>/spool SENSORIUM_MANIFEST_DIR=<tmp>/manifest npm --prefix typescript/probes run probe` | `check.mjs` **`ok: true`**, **12** spools, **146** checks, **0** failures, `escape:count` 14, tally `files_transformed 14 / functions_focused 12 / parse_errors 0`, exit 0. vitest itself prints ` Test Files  1 failed | 11 passed (12)` — `never_settles.probe.test.ts > parks forever` is the probe that deliberately never settles, and the checker, not vitest's tally, is the gate |
| the corpus, at the branch point | `corpus/run_corpus.py`'s loader over `5c36baa` | **105** cases — 20 Python, 43 Rust, 42 TypeScript |
| the corpus, with this task's three | the same loader over the working tree | **108** cases — 20 Python, **44** Rust, **44** TypeScript. The three added are `corpus/typescript/focus_finally_return`, `corpus/typescript/focus_long_string` and `corpus/rust/focus_block_let`, all three RED at T0 |

**The ceilings** (`tests/test_ceiling.py`, 800 lines; `docs/superpowers/`
exempt), measured over the tracked set at the branch point:
`git ls-files -- '*.md' '*.py' '*.mjs' '*.ts' '*.rs' '*.sh' | grep -v
'^docs/superpowers/' | xargs wc -l | sort -rn | head -30`. The three new corpus
files add nothing near it (the largest is 20 lines).

| file | lines |
|---|---|
| `tests/test_corpus.py` | **800** — at the ceiling; the harness half moves to `tests/test_corpus_harness.py` (§7) |
| `README.md` | **799** — one line of headroom (§7) |
| `rust/tests/mechanics.sh` | 795 |
| `tests/test_runs_info.py` | 790 |
| `src/sensorium/query/flow_cmd.py` | 789 |
| `rust/tests/acceptance_e9_phases.py` | 788 |
| `rust/sensorium-transform/tests/golden.rs` | 788 — R8 puts this slice's goldens in a new `tests/unbound.rs` |
| `docs/TRACE-FORMAT.md` | 788 — one sentence to come (§4.3) |
| `typescript/HONESTY.md` | 786 — one line to come (§4.5) |
| `rust/sensorium-transform/tests/edges.rs` | 784 — R8 |
| `typescript/src/rt.mjs` | **783** — the seal adds ≈30 lines, so the capture seam comes first (§7) |
| `tests/test_ts_ingest_meta.py` | 781 |
| `rust/cargo-sensorium/src/convert/mod.rs` | 777 — §5.4 edits it |
| `tests/test_refocus_licence.py` | 772 |
| `rust/HONESTY-BLIND-SPOTS.md` | 772 — a new Rust entry to come (§5.5) |
| `typescript/probes/check.mjs` | 770 |
| `tests/test_flow_identity.py` | 770 |
| `src/sensorium/query/exceptions_cmd.py` | 770 |
| `src/sensorium/record/boot.py` | 768 |
| `rust/cargo-sensorium/tests/convert_meta.rs` | 758 |
| `tests/refocus_programs.py` | 755 |
| `rust/cargo-sensorium/src/mirror.rs` | 753 |
| `rust/sensorium-rt/src/spool.rs` | 752 — §5.3 edits it |
| `tests/test_capture.py` | 750 |
| `tests/test_refocus_rust.py` | 747 |
| `rust/tests/acceptance_e4.py` | 747 |
| `CHANGELOG-ARCHIVE.md` | 742 — cannot take another cut, hence volume 2 (R7, §7) |
| `src/sensorium/query/diff_cmd.py` | 740 |
| `typescript/src/transform.mjs` | 731 |
| total, over the census's own set | 182754 |

`CHANGELOG.md` and `docs/CARRIED-DEBT.md` are the two §7 names not in the top
thirty; both are appended to and both are measured before the append.

### 2.3 Instrument changes made before any endpoint ran

**One, plus the list of named changes the corpus fence is read modulo.** Every
instrument of this slice — `e12p_report.py`, `e12p_h8.py`, `e13_report.py`,
`e14_report.py`, `census_deferred.mjs` — is written after this
pre-registration is locked and before any endpoint reads a number; each change
decided in that window is appended here with the commit that carried it, as
rung 4's §2.3 did. A defect found AFTER a number is read is a finding in §4
and never an entry here.

| # | what changed | commit | why |
|---|---|---|---|
| 1 | **E13's clause 2 is gated on TWO inputs**, `transform-diff.json` AND `census.json`, not on the diff alone; `measured_claims` in `e12p_h8.py` now takes a tuple of input names as well as one name | this task's first commit | the clause's READING comes from the diff and its EXPECTATION from the census. Gated on the diff alone, a results directory with no `census.json` gave an empty expectation, scored a non-empty diff `False`, and counted that `False` in `n` — while `dropped` named the census as not written. One clause would have said both "not measured" and "did not hold", which is the exact defect the two reporters' `measured_claims` rule exists to prevent (Task 2's review minor, deferred here). The covering test is `test_e13_clause_two_is_omitted_when_the_census_was_not_written`; the one-input gate was restored as a mutant and the test failed on it (`3 == 2`) before the fix was kept |

**The named changes, declared before the fence was read.** §1.6's fourth and
fifth clauses and §1.8's first ("every case equal, all three languages") are
read against a corpus whose questions this slice deliberately re-pinned. The
corpus runner reports a case as EQUAL when its answers match its questions as
they stand, so a re-pinned question is not a difference the fence can see;
naming them here, before the run, is what keeps "equal" from meaning "equal to
whatever it says now". Twelve files, none of them a change to what is
RECORDED except where the column says so. These are earlier tasks' diffs, as
rung 4's §2.3 entry 3 was — what this entry carries is the decision to name
them before the reading.

| case / file | what moved | commit | why |
|---|---|---|---|
| `corpus/rust/{aliasing, focus_unfocused_refuses, stale_cache}` | the recorder token in three refusal sentences, `sensorium-rt 0.4.1` → `0.5.0` | `4fb4554` (`aliasing`'s comment refined at `6bd044d`) | all three refuse on a capability the wire's new delta tag cannot reach (`line: false` on an unfocused run, `object_identity: false` always), so the exit is still `3` and only the recorder's name in the sentence moved. Each carries its own dated comment saying so |
| `corpus/typescript/{object_identity, pass_vs_fail, silent_swallow, watch_refused}` | the recorder token in four expectations, `sensorium-ts 0.3.0` → `0.4.0` | `86dd55f` | the seal takes the TypeScript package to `0.4.0`, and a trace declares the recorder that recorded it. Two are refusal sentences, two are `info`/`run` lines; none is a claim about what was recorded |
| `corpus/rust/focus_loop_counter` | `SATISFIED at 3 of the 7` → `2 of the 6`, plus a new `i: not in scope at this site   [4 site(s)]` needle | `0255b5b` | the rule's own number. §5.2 makes a `for` statement's completion row unbind its head pattern, so `i` has left scope at `e11` and that site leaves the evaluable set, taking the third hit with it. The KIND of the answer — SATISFIED, first hit at `e9` — is unchanged, and the case now also pins the absence |
| `corpus/typescript/finally_return` | `harness_args: ["run", "finally_return"]` → `["run", "/finally_return"]` | `77af3c9` | ruling P11. vitest's filter is a substring, and Task 0's new `focus_finally_return/` directory matches `finally_return` too, so rung 2's case collected two test files in unstable pid order (~50 % flake, measured at Task 3). The leading `/` matches `…/finally_return/…` and not `…/focus_finally_return/…`. The case's own pins are untouched, and after this fix a recurrence of that failure is a **STOP**, not a flake |
| `corpus/typescript/focus_catch_binding` | question 2 now asks the `exceptions` question the E6-TS table is about, where it asked a `grep` one | `69cf474` | spec §6.2 / blind spot 37: the case's row in `e6ts.PRE_REGISTERED` is only a pre-registration if the case actually asks the question the table answers |
| `corpus/typescript/focus_async` | one `expect_contains` needle carrying event ids (`e4`/`e7`) split into two id-free needles plus an adjacency needle | `dd07e75` | a deferred minor: `e4`/`e7` were one recording's numbering and pinned nothing the question asks — any row inserted earlier renumbers both and fails a needle that is still true. The adjacency the id-bearing needle also carried is now pinned explicitly |
| `corpus/cases.py` | the refusal for an unknown key in a `program: vitest` case's `record` no longer attributes that key to the Python recorder | `dd07e75` | a deferred minor: a key that is not `focus` need not be Python's at all, and a refusal that says it is sends the reader to the wrong recorder's documentation |

Everything else under `corpus/` is an ADDITION this slice's endpoints are
about — `corpus/rust/focus_block_let`, `corpus/typescript/focus_finally_return`
and `corpus/typescript/focus_long_string`, the three cases §2.2's second row
counts. No other existing case's bytes moved.

## 3. Results

**Status: DONE-WITH-STOP.** Seven gated endpoints and the two fences, every
one read once, in the order Task 11 fixes: E12′ over rung 4's committed
transcripts, then E13, then E14, then E6-TS, then the fences and the suites,
then H8′ last and alone on the lens. **Six of the seven gated endpoints
PASS.** The seventh, **E6-TS′, STOPs** — and it STOPs against a clause §1.7's
own second amendment said three days' work in advance would not hold, because
the clause was pre-registered from the wrong command's vocabulary. So the word
this slice ships is `DONE-WITH-STOP` and not `DONE`, and §4.4 says exactly
what the reading showed and §5 says what the mistake was worth. Nothing was
re-run, no threshold moved and no focus was narrowed after a number was read.

The numbers below are
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts.results.json`,
assembled by `typescript/acceptance/assemble_s5debts.py`, **with three stated
exceptions**, each of which says so again where it is used:

* `cargo test --workspace`'s aggregate — 45 `test result` sections summing to
  804 passed / 0 failed / 24 ignored — is an `awk` sum over `<results>/logs/
  cargo.log`, which is a session artefact and is not committed. The cell holds
  cargo's exit status and the LAST three lines of that log, which are one
  section and not the total.
* the probes' `12 spools, 146 checks, 0 failures` is the checker's JSON at the
  end of `<results>/logs/npm-probes.log`, likewise not committed. The cell
  holds the exit status.
* **E6-TS′'s cell is not the assembler's; it was added to the results file BY
  HAND after assembly** (controller ruling P17), and it is labelled as such in
  the file itself. `assemble_s5debts.py` filters `gated` through its own
  `ORDER` list and builds `reported` from a fixed set of keys, so a cell added
  for E6-TS′ through the assembler would have been silently DROPPED rather
  than refused, and the assembler is not edited after a number is read — that
  seam is §5 item 8. But a reader of `…-debts.results.json` ALONE would then
  have met seven gated cells every one of which reads `value == n`, no
  adjudicated reading, and no word for the slice, and would have had no way to
  see the STOP this record's own first paragraph opens with. So the file was
  written into by hand, and every key added carries the stamp `after assembly,
  by hand, 2026-09-12 (ruling P17)`: `reported.adjudicated.E6TSp_original` —
  `value 0, n 1, verdict "STOP"`, with §1.7's first clause quoted as its
  `rule`, a `basis` that names the `E6TSp` cell's `focus_catch_binding` row
  (`swallowed_lines 1`, `tally_swallowed 1`) it was adjudicated from, and its
  own `added` — and the top-level `word: "DONE-WITH-STOP"` beside
  `recorded_by`, whose stamp is its sibling `word_added` because the word
  itself is the bare string a reader should be able to read straight off the
  file. **None of it is an instrument value**, and none of it touches one:
  `gated`, `verification` and `recorded_by` are byte-identical to what the
  assembler wrote, and the whole edit is additive. §3.4 and §4.4 remain where
  the adjudication is made and reasoned; the file now points at them.

Every cell is `{value, n, lens, dropped}` plus `recorder` / `recorder_rev` /
`recorder_basis`. The recorder is **`sensorium 0.12.0 / sensorium-ts 0.4.0` on
`feat/s5-rung4-debts` @ `d9e843d45fe8f7d0049637b059a2eedeb2c1fc28`** — this
task's own first commit, the pre-measurement instrument fix of §2.3, which is
the tree every endpoint below was read on. The Python version does not move
here: the bump to `0.13.0` is Task 12's, and a cell claiming it would name a
recorder that took no reading.

The assembler's three verifications all held before a number was published:
the hashed set (13 of 13 transcripts, 12 of 13 store entries plainly and
`invocations.jsonl` as an append); the reads were taken against THIS record
(sha `b095e2671136363406c21616d6118fbdd8a3816f9641f3fd99514c8126b9bbb0`); and
the QUESTIONS were read off rung 4's record (sha
`320bce35f44cf5f8688f49e95a647e5ce324daab1aa2fb906a9cae6e7f741e15`). The first
of those two shas is of this record FILE as it stood at assembly time — §1 and
§2 written, §3–§5 still the pre-registration's placeholder — so it is a
ONE-SHOT provenance check and not a standing one: writing these three sections
moves the file's sha and re-running the assembler against this record now
refuses. That is the guard doing its job and also its limit, stated here
rather than discovered by the next reader who runs it; rung 4's §3 records the
same thing about its own.

| # | endpoint | cell (`value` of `n`) | the rule | word |
|---|---|---|---|---|
| E12′ H2′ | can an instrument without the four defects read rung 4's hand count? | **5 of 5** — the hand count, `node resolve.mjs`'s site list and `meta.functions_focused` are all **6**; `meta.focus_matched` is **5**; the one qualname two sites share is `buildDiceQueueEntry.<anonymous>`; both arms print ` Test Files  1 passed (1)` / `      Tests  26 passed (26)` at exit 0; `grep --kind CALL` prints `parseDiceGroups(formula='1d20')` first | one number three ways, `focus_matched` one lower for the shared qualname, the suite half unmoved → else STOP | **PASS** |
| E12′ H4′ | does the re-registered `watch` reading hold? | **3 of 3** — W1 `31` of `64`, W2 `52` of `77` with **0** HITs on a row whose `unbound` names `count` and **2** at line 72 both head rows, W3 `15` all at line 72 carrying `m=null` and `unbound:count,sides`; all three SATISFIED at exit 0 | all three triples as §1.3 re-registers them, W2's clause read off `unbound` and not off a line number → else STOP | **PASS** |
| E12′ H5′ | does the new parser see the CALL the transcript prints? | **7 of 7** — S1 found, **9** sightings at `:74`; S2 found as event **`e10`**, a **CALL** row of `parseDiceGroups` at code-object line **68**; `elsewhere_not_gated` **5**; the transcripts' own `sightings:` **10** and **5**; `unpredicted` **0** | both sightings found, no third triple in the gated population, the ungated rows counted as §1.4 writes them → else STOP | **PASS** |
| H8′ | does this slice's recorder still produce the same rows on the same lens? | **8 of 8** — §1.9's eight clauses, every one held; one run, wall **2.4072 s**, 1-minute load **0.41** | all eight → PASS; any one is a STOP | **PASS** |
| E13 | is a finally after a return recorded, and only where the shape exists? | **4 of 4** — the census prints **0 / 1 / 0** exactly; the 0.3.0→0.4.0 diff over 102 files changes **one**, `settle`'s wrapper, three lines; `focus_finally_return` green; `HONESTY-COST.md`'s diff-stat empty | all four clauses of §1.5 → else STOP | **PASS** |
| E14 | does Rust's row say what its block unbound, and does the fold honour it? | **5 of 5** — `focus_block_let` green; `v40` round-trips; the three tag-3 refusal tests green; **43** other Rust cases equal; **5** `refocus_*` cases equal | all five clauses of §1.6 → else STOP | **PASS** |
| E6-TS″ | does the CORRECTED table hold? | **22 of 22** — every TypeScript case with an `exceptions` question matches `e6ts.PRE_REGISTERED`, `focus_catch_binding` at **1** SWALLOWED with no `ambiguous by reason:` line; the swallow set is **9** cases, non-empty | every row matches, the reason-line pins hold, the swallow set non-empty → else STOP | **PASS** |
| **E6-TS′** | does the table as §1.7 FIRST wrote it hold? | **0 of 1** — `focus_catch_binding` prints `dispositions: swallowed 1` and one `SWALLOWED -- caught by catch at e12 (attempts L17) in f2, which returned`; §1.7 pre-registers **0** | `focus_catch_binding` at 0 SWALLOWED → else STOP | **STOP** |

**Reported beside them, gating nothing** — the two fences and the eight suite
readings of §1.8:

| endpoint | cell | reading |
|---|---|---|
| E-legacy | **1 of 2** | `git diff 5c36baa..HEAD --stat` over the fenced paths names **47** changed files and **every one of them is under `rust/`** — §1.8's one expected mover, because §5 funds the Rust `unbound` by design. No fenced path outside `rust/` moved a byte. The fenced tests and the Rust key's tuple equality are green (`118 passed`) |
| E-branch | **1 of 1** | `tests/test_acceptance_scripts.py` green |

| suite | command | reading |
|---|---|---|
| corpus | `corpus/run_corpus.py --require-driver` | **108 cases, 229 questions, 0 failures, 0 error(s)**, exit 0, wall 50.49 s at a 1-minute load of 0.92 → 1.24 |
| pytest | `.venv/bin/python -m pytest -q -p no:cacheprovider` | **4228 passed, 24 skipped** in 156.92 s, exit 0 |
| cargo | `cargo test --workspace` from `rust/` | exit 0; **45** `test result: ok` sections summing to **804 passed, 0 failed, 24 ignored** (from the log named above, not from the cell) |
| node | `npm --prefix typescript test` | **pass 559, fail 0**, 0 cancelled / skipped / todo, exit 0 |
| probes | `npm --prefix typescript/probes run probe` | checker **`ok: true`**, **12** spools, **146** checks, **0** failures, `files_transformed 14 / functions_focused 12 / parse_errors 0`, exit 0 (vitest itself prints ` Test Files  1 failed \| 11 passed (12)` — `never_settles.probe.test.ts > parks forever` is the probe that deliberately never settles, and the checker is the gate) |
| tsc | `npm --prefix typescript run check` | no output, exit 0 |
| ceiling | `tests/test_ceiling.py` | **1001 passed**, exit 0 |
| E7 needle | `e7_report.py`, `E7_NEEDLES=rung2` | **0** occurrences of the nine needles over **43** lines of this slice's TypeScript output, exit 0; the ungated context counts (`python`, `rust`, `asyncio task`) are **0, 0, 0** |

### 3.1 E12′ — H2′, H4′ and H5′, off the committed transcripts

The preflight ran first and published its own evidence: **13 of 13**
transcripts hash to §1.1's list with no unlisted fourteenth; the store's hash
list is the sha §1.1 cites; **12** of its thirteen entries verify plainly, and
`invocations.jsonl` verifies as an APPEND — its first **6** lines still hashing
to `3a619cbb77356d191489828beaeb70f90cdc1a053e682cf29e1296a39df8221c`, the
value rung 4 listed. The journal stands at **19** lines, rung 4's six plus the
thirteen its own reads appended, which is the arithmetic §1.1 and the rung-4
record's §3 both describe. No cell was read until all of that held.

**H2′ — 5 of 5.** The hand count's six rows, the six sites `node resolve.mjs`
printed in the rung-4 record's §4.2, and the committed trace's
`meta.functions_focused` agree on **6**:

```
src/lib/diceQueue.ts:parseDiceGroups
src/lib/diceQueue.ts:forcedDiceFromSource
src/lib/diceQueue.ts:forcedDiceFromSource.<anonymous>
src/lib/diceQueue.ts:buildDiceQueueEntry
src/lib/diceQueue.ts:buildDiceQueueEntry.<anonymous>
src/lib/diceQueue.ts:buildDiceQueueEntry.<anonymous>
```

`meta.focus_matched` holds **5** — the two default-parameter arrows of
`buildDiceQueueEntry` (L197 `idFactory = () => crypto.randomUUID()`, L198
`now = () => Date.now()`) share the one qualname
`buildDiceQueueEntry.<anonymous>`, which is the shared spelling §1.2 names.
The suite half is byte-equal on both arms and `grep F1 parseDiceGroups --kind
CALL` prints `parseDiceGroups(formula='1d20')` first.

**H4′ — 3 of 3.** Every hit TOTAL is read off `watch`'s own `sites: … hits: …`
tally line and never by counting rows, because `--limit` caps what a
transcript prints; the CLASS questions are read off the printed rows, and the
cell's `note` says which is which.

| # | `--expr` | verdict / exit | tally | the class reading |
|---|---|---|---|---|
| W1 | `sides == 20` | `SATISFIED at 31 of the 64 site(s)…` / 0 | 165 sites, 64 evaluated, 31 hits, 101 not captured, 0 errors | — |
| W2 | `count == 1` | `SATISFIED at 52 of the 77 site(s)…` / 0 | 165 sites, 77 evaluated, 52 hits, 88 not captured, 0 errors | **0** of the 20 printed HITs sits on a row whose `unbound` names `count`; **2** sit at line 72 and both are HEAD rows — `m=[ '2d6', … ]   state: count=1` at `e32` and `e86`, neither carrying `unbound` |
| W3 | `m == null` | `SATISFIED at 15 of the 120 site(s)…` / 0 | 165 sites, 120 evaluated, 15 hits, 45 not captured, 0 errors | all **15** printed HITs are at line 72 and every one carries `m=null  unbound:count,sides` |

**H5′ — 7 of 7.** S1 is sighted **9** times, every one a LINE row
`e<id> LINE    parseDiceGroups L74  sides=20   [local sides]`. S2 is found —
one row, event **`e10`**, kind **CALL**, qualname **`parseDiceGroups`** (the
token before its `(`), code-object line **68**, read from the trace's
`code_objects` table because a printed CALL row carries no `L<line>`:

```
e10 CALL    parseDiceGroups(formula='1d20')   [arg formula]
```

`elsewhere_not_gated` is **5** — one row from the `--value 20` transcript and
four `RETURN` rows from the `--value "'1d20'"` one, all five in
`buildForcedNotation.<anonymous>`, which is outside the three gated qualnames.
The transcripts' own printed totals, quoted beside the cell, are `sightings:
10` and `sightings: 5`, and `unpredicted` is **0**.

### 3.2 E13 — the finally seal

**4 of 4.**

**Clause 1, the census.** `census_deferred.mjs` over the three roots printed
exactly §1.5's three lists — `typescript/probes` **0** deferred of 23 files
scanned, `corpus/typescript` **1** of 90, the lens's `src/lib/diceQueue.ts`
**0** of 1 — and the one row is
`corpus/typescript/focus_finally_return/finally.ts`, `settle`, line **7**,
which is the hand table's row triple for triple.

**Clause 2, the golden diff.** `transform_diff.mjs` ran `e6f5035`'s
`transform.mjs` against this tree's over `typescript/probes/src` and
`corpus/typescript`, both sides on the same bytes with the same options, from
the repository root so that each file is spelled as the census spells it.
**102 files compared, 1 changed**, and the changed file is the census's one,
its changed lines attributed to `settle` and to nothing else:

```
--- base/corpus/typescript/focus_finally_return/finally.ts
+++ head/corpus/typescript/focus_finally_return/finally.ts
@@ -7,13 +7,13 @@
 export function settle(flag: boolean): number {const __sf=__srt.call(__sfile,0);try{
   let cleanup = 0;
   try {
-    if (flag) return __srt.ret(__sf,(1));
-    return __srt.ret(__sf,(2));
+    if (flag) return __srt.pend(__sf,(1));
+    return __srt.pend(__sf,(2));
   } finally {
     cleanup = 1;
     note(cleanup);
   }
-;__srt.ret(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}}
+;__srt.pend(__sf,undefined)}catch(__se){__srt.thr(__sf,__se);throw __se}finally{__srt.seal(__sf)}}
 
 export function note(n: number): number {const __sf=__srt.call(__sfile,1);try{
   return __srt.ret(__sf,(n));
```

Three lines, 1279 → 1307 bytes. `note`, in the same file and two lines below
the changed wrapper, is untouched; so is
`corpus/typescript/finally_return/ledger.ts`'s `commit`, which the census
excluded by name and which is the part of this diff that shows the rule
DISCRIMINATES rather than firing on every `finally` in the tree.

**Clause 3, the case.** `corpus/typescript/focus_finally_return` is green —
3 questions, exit 0, inside the one corpus run — its RED run at T0 in the
ledger.

**Clause 4, the cost prose.** `git diff 5c36baa -- typescript/HONESTY-COST.md`
prints nothing at all: the seam and the seal changed no unfocused wrapper, so
none of that file's cited numbers moved.

### 3.3 E14 — the Rust `unbound`

**5 of 5**, all five clauses read off the artefacts of the one corpus run and
two commands of their own.

| clause | reading |
|---|---|
| 1 | `corpus/rust/focus_block_let` green — 3 questions, exit 0; its RED run at T0 in the ledger |
| 2 | `v40` round-trips: `pytest -q tests/test_vectors.py -k v40` selects `test_vector[v40-rust-line-unbound]` and `test_call_rows_carry_no_frame_id[v40-rust-line-unbound]`, **2 passed, 81 deselected**, exit 0 |
| 3 | the tag-3 refusals hold: `cargo test -p cargo-sensorium spool::` — **49 passed, 0 failed**, exit 0, with `a_tag_three_block_is_an_unbound_name_and_never_a_delta`, `a_duplicate_unbound_name_within_one_record_is_refused` and `deltas_and_unbound_names_ride_one_record_each_into_its_own_list` among them by name |
| 4 | every other Rust corpus case equal: **44** Rust cases in the run, **43** besides `focus_block_let`, **none** moved |
| 5 | every `refocus_*` case equal: **5** of them — `refocus_child_run`, `refocus_diverged`, `refocus_match`, `refocus_refused_many`, `refocus_spawned_test_fn` — **none** moved |

"Equal" here is the corpus runner's own word — a case whose answers match its
questions as those questions stand — and §2.3 names, before this reading was
taken, the twelve files whose questions this slice deliberately re-pinned.
Two of them are Rust cases inside clause 4's set: the three
`sensorium-rt 0.4.1 → 0.5.0` refusal sentences, and
`corpus/rust/focus_loop_counter`'s `3 of the 7` → `2 of the 6`, which is the
rule's own number and not a loosened pin.

**How `corpus.json` was keyed, because the shape has a corner the corpus has
now grown into.** `e14_report.py` reads one entry per case, keyed by name,
with `language` as a field. Fourteen case DIRECTORY names are now shared
across two languages (`aliasing`, `pass_vs_fail`, `focus_loop_counter` and
eleven more), so a file keyed by bare name alone would have let one language's
case overwrite the other's and read "every Rust case equal" over a set that
had quietly lost members. The input was therefore keyed by the runner's own
name with its language prefix stripped WHERE THAT IS UNAMBIGUOUS and kept
whole where it is not — 108 entries for 108 reported cases, 20 Python, 44
Rust, 44 TypeScript, and the cell's own `rust_cases` list is 44 long, which is
how a reader can check that nothing was lost. No instrument was changed for
this; it is a statement of how the operator's input was built. §5 carries it
as a finding about the shape.

### 3.4 E6-TS — the corrected table measured, the pre-registered one adjudicated

**E6-TS″ — 22 of 22.** `e6ts.py` recorded every TypeScript corpus case that
asks an `exceptions` question through the corpus's own driver and compared each
printed answer against `e6ts.PRE_REGISTERED` two independent ways — the count
of lines beginning `SWALLOWED --`, and the `swallowed` term of the parsed
`dispositions:` line. Twenty-two cases asked, twenty-two matched, `differences`
empty, `dropped` empty, wall 13.83 s. The swallow set is **9** cases and
therefore non-empty. Every case in `PRE_REGISTERED_REASON_LINE` printed the
line that table pins, `None` included.

`focus_catch_binding`'s row, whole, is the evidence both clauses are read off:

```
case                 focus_catch_binding
question             did-anything-record-the-catch-itself
command              exceptions 20260912-190450-7d551d          exit 0
tally line           dispositions: swallowed 1
swallowed lines      1        tally_swallowed     1
reason line          None     expected            None
lines                SWALLOWED -- caught by catch at e12 (attempts L17) in f2, which returned
expected             1        equal               true
```

**E6-TS′ — 0 of 1, STOP.** §1.7 as it was first written pre-registers that
same case at **0** SWALLOWED. The answer prints **1**, twice over, by two
derivations that agree. The clause does not hold. It is adjudicated here from
the evidence above and not from a second run, because there is only one run and
the two clauses are two readings of it. §4.4 says what this STOP is a finding
about.

### 3.5 The fences and the suites

Eight suite readings and two fences, each carrying its own exit status; every
one green, and the one non-zero-looking cell is E-legacy's, which §1.8 wrote
down in advance.

**The legacy fence is the one worth spelling out.** Its first claim — "the
fenced files show zero diff against the branch point" — reads **false**, and
§1.8 pre-registers exactly that: `rust/` is inside `FENCED` and §5 funds the
Rust `unbound` by design, so `rust/` is named as **the one fenced path
expected to move** and the rule the record actually gates on is that the
fence's report lists only paths under it. It does. **47** files changed, and
all 47 are under `rust/`: the three crates' `Cargo.toml`s and `Cargo.lock`, the
runtime's `line.rs` and its tests, the transform's `lines.rs` / `facts.rs`, the
converter's `spool/line.rs` and `spool/tests.rs`, ten new `focus_unbound_*`
golden pairs plus `focus_loop`'s re-pin, the new `tests/unbound.rs`, and the
Rust prose. Nothing in `src/sensorium/query/exceptions.py`,
`exceptions_rust.py` or any of the four `test_exceptions*` files moved a byte.

One mechanical note about how that was checked: `git diff --stat` ELIDES long
paths for display width, so twenty of the cell's forty-seven `diff_stat_lines`
read `.../tests/golden_focus/focus_unbound_*.rs`. The full names were read
with `git diff <branch point>..HEAD --name-only` over the same fenced path
list — the same two fixed commits, a name listing rather than a second
measurement, and the cell's value is untouched by it.

**The E7 needle ran LAST, after H8′, and over H8′'s output**, which is a
departure from the order the task brief lists it in and is stated here rather
than left to be noticed. §1.8 asks for the needle grep "over this slice's
TypeScript output", and the TypeScript output this slice PUBLISHES is H8′'s —
the `info` and `frame` transcripts now committed under
`…-debts-reads/`. Running the grep before H8′ would have had no such output to
read. The list is rung 2's nine, the list rung 4 read its own transcripts
under, so the two readings are comparable: **0** occurrences over 43 lines,
with the matching rule for each needle committed beside the transcripts as
`13-e7-needle-rules.txt`.

### 3.6 H8′ — the live confirmation, run last

One run on the lens, under this slice's driver and recorder, into a fresh
store of its own: `run 20260912-191050-0be0e9`, wall **2.4072 s**, taken at a
1-minute load of **0.41** through the same guard every arm of this slice's
family uses (under 4.0, up to 90 tries 20 s apart). `session.json` records
`preregistered_subject: true` — the subject, the three specs, the diffed
source and the framed function are §1.9's own words and no override was in
play. All nine steps exited 0.

| # | clause | reading |
|---|---|---|
| 1 | the manifest before AND after | **748 OK / 0 FAILED** both times, over a 748-line manifest. The lens is byte-identical after the run to what it was before it |
| 2 | `resolve.mjs` prints the same six sites | the six above, in the same order, exit 0 — equal to rung 4's list element for element |
| 3 | `info` prints `focus matched: 5 … (6 functions)` | `focus matched: 5 — …buildDiceQueueEntry, …buildDiceQueueEntry.<anonymous>, …forcedDiceFromSource, …forcedDiceFromSource.<anonymous>, …parseDiceGroups (6 function(s) focused by the transform)` |
| 4 | H3's nine LINE rows are TEXT-equal to the rung-4 record's §1.1 hand count | **9** read, **9** expected, every row equal on line, deltas and `unbound`. The activation is `f6 … [e10..e20]`, `args: formula='1d20'`, and its rows are L69 `groups=[]`, L70, L71 `m=undefined`, L72 `m=[ '1d20', … ]`, L73 `count=1`, L74 `sides=20`, L76, L75, L72 `m=null  unbound:count,sides` |
| 5 | the suite line | `      Tests  26 passed (26)`, run exit 0 |
| 6 | the marker grep | two cache directories searched by name (`node_modules/.vite`, `node_modules/.vite-temp`), **0** hits of `__srt` |
| 7 | the wrapper listing | `node_modules/.sensorium: absent` |
| 8 | the base transform's diff | 1 file compared, **0** changed, **0** diff bytes — `e6f5035`'s `transform.mjs` and this slice's emit byte-identical output for `diceQueue.ts` under the same three specs |

Two readings sit beside the eight and gate nothing. `info` reports `recorded:
CALL 117  RETURN 117  RAISE 0  HANDLED 0  YIELD 0  RESUME 0  LINE 295` over
**529** events — the same call tier and the same 295 LINE rows rung 4's F1
arm recorded, under a recorder two minor versions later. And the trace
declares `recorder: sensorium-ts 0.4.0` with `line=yes locals=yes`, which is
the tier this run asked for saying so in its own words.

The thirteen artefacts of this run are committed, redacted, under
`docs/superpowers/acceptance/2026-09-12-sensorium-s5-rung4-debts-reads/`. Four
labels replace box paths there — `<lens>`, `<h8 store>`, `<repo>` and
`<home>`, plus `<base checkout>` and `<results>` where the session names them.
The store is labelled `<h8 store>` and not `<store>` on purpose: §2's `<store>`
is rung 4's store, which E12′ read and this run never touched, and one label
for two directories is how a reader comes to believe a run wrote where it did
not.

## 4. Decisions

### 4.1 E12′ — an instrument without the four defects reads all three, PASS

The question this endpoint asks is narrow and worth restating before its
answer: rung 4 STOPped on H2, H4 and H5, and its own §4.4/§4.5 concluded that
two of those three STOPs were the INSTRUMENT's rather than the recorder's. It
listed four defects — a CALL row's name is the token before its `(`; a CALL
sighting's line lives in the code object and not in the printed row; a
`RETURN` arrow takes one space or two; and a `while`'s head row is told from
its completion row by the row's own `unbound` payload and never by its line
number. E12′ re-registered the readings those defects blocked, built a parser
without them, and read the SAME committed bytes.

**All three PASS.** The conclusion rung 4's post-mortem reached by hand is the
one an instrument reaches mechanically, and the reach of that is exactly this:
the four defects were the whole of the difference. Nothing about the recorder
moved, nothing was re-recorded, and no number in rung 4's own record is
revised by this — its H2/H4/H5 cells stay STOPped, because a cell records what
its instrument read on the day. What changes is that the next reader of
`docs/CARRIED-DEBT.md` can close three gaps rather than carry them.

**The reach of H4′'s W2 reading, stated plainly** (the one place in this
endpoint where the instrument cannot see the whole population). W2's
transcript prints **20** of its **52** HITs — `watch --limit` caps the rows and
the transcript says `... 32 more` in its own words. The hit TOTAL, 52, is read
off `watch`'s own tally line and is complete. The two CLASS readings — "0 on a
row whose `unbound` names `count`" and "2 at line 72, both head rows" — cover
**the 20 printed rows and no more**. The other 32 rest on the fold rule rather
than on inspection: a name popped on a row cannot be evaluated at that row, so
a HIT cannot sit on a completion row that unbinds the name its predicate
names. That is the rule the re-registration is built on, and it is why the
zero is a zero about a class and not a count of a sample. Rung 4's post-mortem
read the same truncated twenty by hand. The instrument's cell carries both
numbers (`printed_hits: 20`, `hits: 52`) and its `note` says which question
each answers, so the limit is visible in the JSON rather than in a footnote —
and the anti-vacuity control Task 2 added is what keeps the zero from being
the output of a dead parse: the same parser, on the same run's committed
`frame` transcript, must still read exactly one completion row
`(72, ["count","sides"])`, and it does.

One thing a reader comparing E12′ against rung 4 should know, because it makes
S2's cell weaker than it looks in isolation: in this trace a CALL event's
`events.line` EQUALS its code object's `firstlineno` — all 117 of them. So
`call_line_of` reading 68 for `e10` does not by itself distinguish a correct
reader from one that took the event's own line. What distinguishes them is the
assertion Task 2 added when the first mutant survived: `call_line_of(conn, 11)`
must also read **68**, where `e11` is a LINE event AT line 69 whose code object
is still `parseDiceGroups` at 68. The cell reads the code table, which is what
§1.4 asks for; the two sources would have agreed here anyway.

**Verdict: PASS** on each of H2′, H4′ and H5′, by the rule each carries.

### 4.2 E13 — the seal fires on the shape and on nothing else, PASS

Four clauses, all held, and the four are deliberately one question asked from
four sides: does the transform now defer a function's exit when — and only
when — the function returns THROUGH a `finally`?

The census answers the "only when" half twice. It found one deferred function
in three roots and 114 scanned files, and the hand table written before the
detector existed named that same one. Two functions in those roots have the
`finally` keyword and are NOT deferred —
`typescript/probes/src/swallow.probe.test.ts`'s `shape12` and
`corpus/typescript/finally_return/ledger.ts`'s `commit`, both of them returns
inside a `finallyBlock` that no further finally guards, which is the rule's
own parenthesis. The golden diff then answers it in bytes: 102 files compared,
one changed, three lines, `settle`'s wrapper and no other byte in the tree.
A rule that fired on the keyword would have moved three wrappers; a rule that
fired on nothing would have moved none.

The "when" half is the corpus case, green with the questions §1.5 fixed
before the code existed: `watch --at settle --expr cleanup == 1` SATISFIED at
2 of its evaluable sites with a HIT on `LINE settle L13  cleanup=1`, `frame
--fn settle` carrying exactly 3 LINE rows (`expect_count LINE: 3`) with
`args: flag=true` and `return: 1`, and `tree` rendering `note() -> 1` two
spaces deeper than `settle(flag=true)` — its CHILD, which under a recorder
that closed the frame at the `return` would have been its sibling. Those are the
case's own pins and the corpus checked them; this endpoint's clause is that
the case is green, and it is.

The fourth clause is the one that says the change was SURGICAL:
`typescript/HONESTY-COST.md` cites what the unfocused wrapper costs, and its
diff-stat against the branch point is empty. The seal changed the deferred
shape's wrapper and left every other function's alone, which is what makes the
cost prose still true rather than merely still committed.

**Verdict: PASS.**

### 4.3 E14 — a Rust row now says what its block unbound, PASS

Five clauses, all held. The centre of them is the corpus case, whose questions
were written at T0 from design §5.2 and committed RED: `frame --fn shape`
carrying `unbound:x` on the plain block's row, `unbound:first` on the `if
let`'s, `unbound:item` on the `for`'s and `unbound:n,big` on the `match`'s —
the arm pattern's name first and the arm body's `let` second, which is SOURCE
order and is the ruling (P7) this slice took and then had to correct once
(P13, §5). Around it: the wire vector round-trips; the converter refuses a
record that names one name as both a delta and an unbound, by name, in three
tests; and the other 43 Rust cases and all 5 `refocus_*` cases are equal.

The fourth clause is the one that carries the most weight and is the easiest
to read carelessly. "No block-free fragment moved" is a claim about the
transform's blast radius — the rule is supposed to touch statements that OWN a
scope and nothing else — and 43 unmoved cases is the evidence for it. It is
read off the same single corpus run as clause 1, which is deliberate: two runs
would have measured two populations. The cell refuses an EMPTY set for exactly
this reason, and the reading published is the set's size (43) and its members,
so a short set is visible rather than silently green — which is the hazard the
bare-name keying of §3.3 would have created and did not.

One existing case did move, in the predicted direction, and §2.3 names it
before the reading: `focus_loop_counter`'s `SATISFIED at 3 of the 7` became
`2 of the 6` because the `for` statement's own completion row now unbinds `i`,
so `e11` left the evaluable set and took the third hit with it. The verdict
word and the first hit are unchanged. That is the rule costing a reading, not
a pin loosened to fit an output.

**Verdict: PASS.**

### 4.4 E6-TS — the corrected clause holds, and the pre-registered one STOPs

**E6-TS″: PASS, 22 of 22.** Every TypeScript case that asks an `exceptions`
question prints the answer `e6ts.PRE_REGISTERED` pins, `focus_catch_binding`
included at **1** SWALLOWED and with no `ambiguous by reason:` line — the two
claims §1.7's second amendment pre-registered, both derived from
`exceptions_typescript.py`'s own documented disposition rule rather than from
a reading of an output. The swallow set is nine cases and non-empty, which is
the clause that keeps a table of zeroes from satisfying equality.

**E6-TS′: STOP, 0 of 1.** §1.7 as first written pre-registers
`focus_catch_binding` at **0** SWALLOWED. The case prints
`dispositions: swallowed 1` and one `SWALLOWED --` line. The clause does not
hold, and no instrument defect is available to blame: the two independent
derivations agree with each other, the case's own `expect_line` pins pass
through the corpus harness over this very output, and the same reading of the
same shape (`silent_swallow`) has been pinned at 1 since rung 2.

**What the STOP is a finding about — the pre-registration, not the tool.** The
hand adjudication behind the 0 read `retry.ts:17`'s `catch (e) { count += 1 }`
and concluded "one HANDLED at that clause, nothing swallowed". HANDLED is
`grep --kind HANDLED`'s vocabulary: it is a fact about ATTRIBUTION — this
handler is the one that took it, traced with confidence — and it says nothing
about DISPOSITION. `exceptions_typescript.py`'s module docstring, lines 30-32,
defines the disposition the command prints: *"``swallowed``   an absorbing
handler took it and the frame holding that handler then returned."* The clause
neither rethrows nor logs (`how="catch"`, in `ABSORBING`, not `ESCAPING`) and
`attempts` returns normally once its loop ends. That is the rule, exactly, and
the adjudication read one vocabulary for the other.

**Why the locked clause was not quietly corrected.** It could have been: §1.7
is a section of this record and the row in `e6ts.py` is three lines. Ruling
P16 refused that and the refusal is the point. The clause was pre-registered
before the case's `exceptions` question existed, which is what gives it any
force at all; editing it once the answer was known would have converted a
prediction into a description and left no trace that anyone had been wrong.
So §1.7 keeps its words, the lock publishes the amendment as a fact
(`ORIGINAL_LOCK` unchanged, `BYTE_LOCK` moved twice), E6-TS″ was pre-registered
BESIDE it — from the rule, before the instrument read the cell — and Task 11
measured both and reports both. The correction was derivable at T0 from a
docstring that has said so all along; what the observation supplied was not the
rule but the discovery that it had been misapplied.

**Verdict: E6-TS″ PASS; E6-TS′ STOP**, and the STOP is this slice's own,
reported against itself.

### 4.5 H8′ — the same rows, on the same lens, under a later recorder

Eight clauses, all held, on one run that took 2.4 seconds and left the lens
byte-identical (748 OK before, 748 OK after, no `__srt` in any vite cache, no
`node_modules/.sensorium` left behind).

The clause worth dwelling on is the fourth. Rung 4's H3 hand count is nine
rows written from the design and the statement table before `bindings.mjs`,
`probe.mjs`, the runtime's `line` or the converter's `_on_line` existed. This
run reproduces all nine, TEXT-equal — same lines in the same order (69, 70,
71, 72, 73, 74, 76, 75, 72), same delta names, same single `unbound:count,
sides` on the `while`'s completion row — under a recorder that has since
gained the finally seal, `positions.mjs`, a stricter `captures()` and a guarded
`resolve.survey`. The grain did not drift while the tier grew.

The eighth clause is the other half of E13's second: the focused file carries
no `try` and no `finally` at all, so the seal must be INVISIBLE on it, and
`e6f5035`'s transform and this slice's produce byte-identical output for
`diceQueue.ts` under the same three specs — 0 diff bytes. A change that fires
on a shape the lens does not have should change nothing about the lens, and
this is that sentence measured.

**Verdict: PASS.**

### 4.6 The fences and the suites — nothing else moved

**E-legacy, 1 of 2, and the reading HOLDS.** The cell's first claim is "zero
diff", and §1.8 pre-registers that this slice breaks it in exactly one place:
`rust/` is inside the fence and §5 funds the Rust `unbound` by design. The
rule the record gates on is the one §1.8 writes — the fence's report must list
only paths under `rust/` — and all 47 changed paths are. The `src/sensorium/
query/exceptions*.py` readers and the four `test_exceptions*` files are
byte-unchanged, and the fenced tests plus the Rust key's tuple equality are
green at 118 passed.

**E-branch, 1 of 1.** `tests/test_acceptance_scripts.py` green: the
instruments ran this branch's binary and only the assembler minted the lens
label.

**The suites.** The corpus is the fence with the most surface and it came back
`108 cases, 229 questions, 0 failures, 0 error(s)` on ONE run, at a 1-minute
load of 0.92 rising to 1.24 — well under the 4.0 the flake disposition of
rulings P10/P11 is written around, and no case failed, so no re-run was taken
and none was needed. That is worth recording because of what it replaces:
`corpus/typescript/finally_return` flaked roughly half the time between Tasks
0 and 4, and after Task 4's filter fix a recurrence would have been a STOP
rather than a flake. It did not recur.

pytest **4228 passed, 24 skipped** (the three Task-0 corpus cases that were
the plan-sanctioned RED for most of this slice are green and inside that
number); cargo 45 sections summing to **804 passed, 0 failed, 24 ignored**;
node **559 passed, 0 failed**; the probes' checker **ok: true** with 146
checks and 0 failures; `tsc` silent at exit 0; the ceiling green at 1001
passed. And the E7 needle over this slice's published TypeScript output: **0**
of nine, with `python`, `rust` and `asyncio task` all at 0 beside it.

**Verdict: reported.** None of these gates a number; each of them would have
stopped the slice had it moved.

## 5. What the slice ships

**`DONE-WITH-STOP`.**

One endpoint STOPped: **E6-TS′**, the clause §1.7 pre-registered before the
case it is about existed, against a case that prints `swallowed 1` where the
clause says 0. It is the only STOP, it is a finding about this slice's own
pre-registration rather than about the tool, and §4.4 gives it whole. Six
gated endpoints PASS, the two fences and eight suite readings are green, and
nothing was re-run.

**What is established.**

* **Rung 4's three STOPs were the instrument's, and now there is a
  measurement that says so.** E12′ read the same committed bytes with a parser
  free of the four defects rung 4's post-mortem named, and H2′, H4′ and H5′ all
  PASS — 6 sites three ways, three `watch` triples with W2's clause read off
  the row's `unbound` instead of its line number, and the CALL sighting the old
  parser printed but could not see, found at `e10` with its line taken from the
  code object. Three carried gaps close.
* **A TypeScript function that returns through a `finally` is recorded, and
  only that shape is touched.** E13: the census names one deferred function in
  114 files and the 0.3.0→0.4.0 golden diff moves exactly that function's
  wrapper — three lines, 102 files compared, one changed — while the two
  `finally`s the rule excludes keep byte-identical wrappers and
  `HONESTY-COST.md`'s cited numbers do not move.
* **A Rust block-like statement's row now says what went out of scope on
  it.** E14: `focus_block_let` green on four shapes (plain block, `if let`,
  `for` pattern, `match` arm) in source order, the wire vector round-tripping,
  three converter refusals for a name that is both a delta and an unbound, and
  43 other Rust cases unmoved.
* **The grain did not drift.** H8′, on the same lens under `sensorium-ts
  0.4.0`, reproduces rung 4's nine LINE rows TEXT-equal, the same six resolved
  sites, `focus matched: 5 … (6 functions)`, `26 passed (26)`, the same
  `CALL 117 RETURN 117 … LINE 295` over 529 events — and leaves the lens
  byte-identical, 748 OK before and after.
* **The E6-TS table can take a new case, by a procedure that is now written
  down** — and the first case to use it caught the procedure's own weak point
  (below).

**The gaps and the lessons, none of them papered over.**

1. **The pre-registration named the wrong disposition, and the slice reported
   it against itself (E6-TS′, STOP).** `focus_catch_binding` was
   hand-adjudicated in `grep --kind HANDLED`'s vocabulary — a HANDLED event,
   traced with confidence — and "nothing swallowed" was concluded from that
   confidence. `exceptions`'s own rule, in the reader's module docstring since
   long before this slice, says `swallowed` means an absorbing handler took it
   and the frame holding that handler then returned, which is precisely the
   shape. **The process lesson is about WHICH VOCABULARY a hand adjudication is
   written in**: the pre-registration of a command's output must be derived
   from that command's own documented rule, not from a sibling command's kinds,
   however closely the two seem to be about the same event. `e6ts.py`'s "how a
   new case asks an `exceptions` question" now says that in as many words, with
   the commit that got it wrong named. And the mechanism worked: the wrong
   clause was left standing, a corrected one was pre-registered beside it from
   the rule before any cell was read, and both were measured once and reported.
2. **A vitest filter is a substring, and a new directory can silently join an
   old case's run.** Task 0 added `corpus/typescript/focus_finally_return/`;
   rung 2's `finally_return` case filtered vitest with the bare string
   `finally_return`, which matches both directories, so that case recorded two
   test files in unstable pid order and failed about half the time. Found at
   Task 3 (as a ~50 % flake, after two earlier unreproduced 8-vs-7 sightings),
   diagnosed to its cause, fixed at Task 4 with the filter `"/finally_return"`,
   and re-classed by ruling P11 from "flake" to "a recurrence is a STOP". It
   did not recur in this measurement. The lesson is that an intermittent
   failure with an unknown cause is worth the hour it takes to find the cause
   BEFORE the measurement, because the disposition rule you can write
   afterwards is much weaker than the one you can write once you know.
3. **An `else if` is an expression, not a statement, and the first rule
   written for it was wrong (P13 corrects P7).** The Rust unbind rule was
   specified with the head-pattern order right (source order, P7) and the
   `else if` case wrong: an `else if` is the outer `if`'s `else_branch`
   EXPRESSION, so it never takes a completion row of its own and the outer
   statement's row is the only one that can unbind the chain's names.
   `unbound_of` now descends the chain while the branch is an `Expr::If`,
   collecting each link's condition bindings and its block's direct `let`s;
   the golden `focus_unbound_elseif` pins it, and a nested `if` that IS a
   statement still unbinds its own. Caught by review inside the slice, before
   any endpoint read a number.
4. **An abandoned generator's exit is `unread`, not `undefined` (A12/P12).** A
   seal-deferred generator whose consumer walks away — `.return()`, a `break`
   out of `for…of` — never ran the body to a value, and reporting `RETURN
   undefined` would have claimed the body produced one. The deferred generator
   wrapper now passes a flag to `seal`, and "nothing was pended with the flag
   set" is exactly the abandoned case, so it emits `RETURN {k: 'unread'}`. A
   body that falls off its end still pends `undefined` explicitly.
5. **A block-like EXPRESSION takes no completion row, so a whole family of
   Rust shapes is still not unbound** (Rust blind spot 33, opened by this
   slice and carried). `let y = { … }`, a `match` arm body, `let y = if … `
   and a function's tail expression all bind names that nothing pops, because
   the rule is attached to statements. `focus_unbound_tail`'s goldens falsify
   the tail case; the other three shapes are untested, and the entry says so.
   Blind spot 32 is its sibling: a block that shadows an outer binding pops the
   name, so the outer binding stops answering after the block — the shadow
   reading R4 that `focus_block_let`'s third question pins on purpose because
   it is the costly half of the rule.
6. **A gate nothing else runs is a gate nobody runs.** Task 2 added
   `typescript/acceptance/transform_diff.mjs` and did not run `npm --prefix
   typescript run check`; `typescript/tsconfig.json` covers
   `acceptance/**/*.mjs`, so eighteen `tsc` errors stood in that one file from
   the commit that added it until Task 3's implementer found them. No Python
   test type-checks an `.mjs`. Fixed by typing alone, after Task 2 had been
   reported complete, and named here because the failure mode — a file added
   under a checker nobody in that task ran — is the generic one.
7. **Two instrument-shaped things this measurement found, neither of which
   moved a number.** `e13_report.py`'s clause 2 was gated on
   `transform-diff.json` alone while its expectation derives from
   `census.json`, so a directory missing the census would have scored the
   clause False AND named it in `dropped` — one clause saying both "not
   measured" and "did not hold". Found in Task 2's review, fixed and committed
   BEFORE any endpoint ran, and recorded in §2.3 with its covering test and the
   mutant that failed without it. And `corpus.json`'s shape — one entry per
   case, keyed by name, with `language` as a field — cannot represent two cases
   of the same directory name in different languages, of which the corpus now
   has **fourteen**; keyed naively, "every other Rust corpus case is equal"
   would have read over a set that had lost members. §3.3 says exactly how the
   input was keyed instead. The reporter is unchanged; the shape's corner is
   the finding.
8. **The ASSEMBLER cannot carry a cell nobody wrote an instrument for, so a
   hand-adjudicated reading had to be written into its output by hand.**
   `assemble_s5debts.py` filters `gated` through a fixed `ORDER` and builds
   `reported` from a fixed set, so an added E6-TS′ key would have been dropped
   SILENTLY rather than refused — the worse of the two failures, and the reason
   the assembler was not edited after a number. The cost is that the file it
   wrote could not, on its own, show the one endpoint that STOPped: seven gated
   cells all reading `value == n`, nothing adjudicated, and no word for the
   slice. Ruling P17 closed that by hand — `reported.adjudicated.
   E6TSp_original` and a top-level `word`, both stamped `added … by hand …
   (ruling P17)`, both additive, neither an instrument value (§3's third
   exception). **The seam is real and stays open**: an assembler whose schema
   has no representation for "a reading a human made from an instrument's
   evidence" forces either a silent drop or a hand edit, and a later slice
   should give it one — a declared `adjudicated` section, written from a file
   the operator hands in like every other input, so that the provenance of a
   hand reading is checked by the same machinery as the rest.

**Carried debt for the next slice**, none of it measured here: blind spot 33's
three untested shapes (the value-block family); whether `--focus` should offer
a spelling that means "this function and not the function-likes nested in it"
(rung 4's question, untouched by this slice); `rust/HONESTY-BLIND-SPOTS.md`
standing at exactly **800** lines, the ceiling, so its NEXT entry must open a
volume (ruling P15) — and beside it `src/sensorium/query/flow_cmd.py` and
`README.md` at 799, `typescript/src/rt.mjs` at 798 and
`rust/sensorium-transform/src/lines/facts.rs` at 778; and the assembler seam of
item 8.

**What a reader can do with this that they could not before.** Ask a
TypeScript function that returns through a `finally` what it actually did —
and be shown the finally's own statements, in order, with the RETURN after
them rather than before. Ask a Rust frame what a block took away when it
ended, and be told the names by the row that ended it, so `watch` stops
answering with a value that no longer exists. And read rung 4's three STOPped
endpoints as what they were: a parser's four defects, now named, fixed, and
measured out of the way.
