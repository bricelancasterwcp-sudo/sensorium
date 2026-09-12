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
files; `~/workspace/projects/vtt` was neither read nor touched, and the lens
was read here by `sha256sum -c` and by opening three functions of
`src/lib/diceQueue.ts`, all of which only read. The store rung 4 recorded
into, abbreviated `<store>`, is read-only for this slice: E12′ re-adjudicates
committed transcripts and hashes that store, and records nothing into it.

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
| the Rust crates | `grep -m1 '^version' rust/{sensorium-rt,sensorium-transform,cargo-sensorium}/Cargo.toml` | `sensorium-rt 0.4.1` → `0.5.0` (§5.3); `sensorium-transform 0.4.4`; `cargo-sensorium 0.5.3` → `0.6.0` (§5.4) |
| the driver every corpus run used | `SENSORIUM_CARGO_SENSORIUM` | `/mnt/extra/sensorium-rung2/s5-debts-target/release/cargo-sensorium`, built from this worktree at `5c36baa`. The box's `PATH` driver is the installed `0.5.3` and is not reinstalled from here until after merge |

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
`/mnt/extra/sensorium-rung2/s5-debts-target/baseline-py-node.log`; `cargo test
--workspace` is its sibling log; the probes were run again at T0 by the
command named, because the log kept only that run's last lines.

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

**None yet.** Every instrument of this slice — `e12p_report.py`,
`e12p_h8.py`, `e13_report.py`, `e14_report.py`, `census_deferred.mjs` — is
written after this pre-registration is locked and before any endpoint reads a
number; each change decided in that window is appended here with the commit
that carried it, as rung 4's §2.3 did. A defect found AFTER a number is read
is a finding in §4 and never an entry here.

## 3. Results

*Written when the endpoints have run.*

## 4. Decisions

*Written when the endpoints have run.*

## 5. What the slice ships

*Written when the endpoints have run.*
