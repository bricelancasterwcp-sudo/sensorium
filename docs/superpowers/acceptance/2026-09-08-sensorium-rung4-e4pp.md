# Rung-4 acceptance, the recorder's footprint and the licence word — E4″ (H1–H8)

The record of whether the recorder's own footprint is out of the licence's
way — the driver's `RUSTDOCFLAGS` fragment, a program thread mistaken for the
harness's, and the session variables of the shell a re-run was launched from —
and of what the harness-thread rule then does to the word `sensorium refocus`
prints beside a Rust pair's verdict. Measured by re-reading the same 61 kept
originals E4′ read, under a **different driver build**, plus two four-pair
control arms.

## 0. Provenance

**What E4′ found, why a second build is the subject, and where the rules
are written.** E4′ (`docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md`)
measured the harness-thread rule once over 61 kept originals and STOPPED on
H1 with `granted` = **0**: the licence's environment clause read the driver's
own `RUSTDOCFLAGS` fragment — `--extern sensorium_rt=…/sensorium/rt/<16
hex>/<unwind|abort>/libsensorium_rt.rlib` with its `-L dependency=…` — as a
change the world had made, so all 61 pairs were WITHHELD for a reason with
nothing to do with the rule under test (E4′ §5, whose ruling — not this
record's — is that E4″ must read an original recorded under a *different*
driver build). This slice's design —
`docs/superpowers/specs/2026-09-08-sensorium-rung4-footprint-design.md`,
committed **`0badf65`**, amended **`7de5565`** (amendment **A-§3**, which
supersedes §3 and rewrites §7's arms and H4–H6) — strips that fragment as the
recorder's own (R1), anchors the harness thread on a thread's FIRST root and
never on a `spawn@` name (R3), and exempts **session set 1** from withholding
(R4 as A-§3 rules it: a session set, not a bearing set). **E4″ is a second
pass over the same 61 originals** — kept, recorded by `cargo-sensorium`
**0.5.0**, never re-recorded — read this time by this slice's driver,
`cargo-sensorium` **0.5.2**, built by the preflight from the measurement
commit. The two builds differ by construction, and the rt hash the fragment
carries is a digest of the driver binary and the `sensorium-rt` sources, so
the fragment differs between the two sides: the one condition under which
E4′'s confound is visible, and one a dry run under a single build cannot
create. E4′ is not re-opened and no number in it is re-measured.

**§1 is byte-locked, and it is committed ALONE.** It is committed before
`strip_recorder_fragment` exists in `refocus_env.py`, before `SESSION_EXACT`
exists, before `harness_threads` has ever read a `spawn@` name, before
`rust/tests/acceptance_e4pp.py` exists, and while `cargo-sensorium` is still
**0.5.1** — so no value below was chosen after seeing an instrument behave.
Each of those five is checkable at this commit. The lock is
`awk '/^## 1/,/^## 2/' | sha256sum`; the runner refuses to start unless the
range is byte-identical to the commit that locked it, and refuses outright
while no lock sha is set. §1 references no footnote, so the extended lock
range and the `awk` range are the same bytes. §1.1's subject table lives in a
**sibling file** whose sha256 §1.1 prints, so the subject is locked too — by
digest rather than by range.

**A completed measurement is never re-rolled, and a miss is a STOP with its
number.** Measured once. The kill sentences are §1.4's.

## 1. Pre-registration

**The argv form, verbatim — pass 2 only.** This record does not re-record
anything. Pass 1 already happened: it is E4's, its 61 originals are kept, and
§1.3 copies them rather than re-running them. Every invocation this record
makes against the subject has one shape:

| arm | n | argv | launch environment |
|---|---|---|---|
| — | 0 | *(pass 1 is not run — the kept originals are the subject, copied per §1.3)* | — |
| A | 61 | `sensorium refocus <run> --focus <name>` | the guard's environment, unmodified |
| B | 4 | `sensorium refocus <run> --focus <name>` | the guard's environment **plus `E4PP_INPUT=1`** |
| C | 4 | `sensorium refocus <run> --focus <name>` | the guard's environment **plus `<the chosen session key>=<the launch stamp>`** (§1.3) |

`<run>` is the original run id of the subject row and `<name>` is that row's
test function, the bare qualname — the same `--focus` value E4 and E4′ used,
unique workspace-wide. The CLI re-invokes the driver itself: `sensorium
refocus` builds `[driver, "--refocus-of", <run>, "--focus", <name>,
*cargo_args]` and runs it from `workspace_root` under the fresh store (slice-2
design §2.3). Nothing parsed from the driver's stdout is load-bearing; the
pair is found by `refocus_of` in the store. Because pass 1 is not re-run, the
originals' bytes are E4's exactly, and any difference this record reads is
attributable to the reader and the driver, never to a fresh recording. Each
refocus rebuilds the matched unit under its focus against a FRESH
`CARGO_TARGET_DIR` (§1.3) — the shape E4′'s amendment A1 ruled a normal use
of the tool, and what makes the relocation rule and the fragment strip
load-bearing here rather than incidental.

### 1.1 The subject — the 61 kept originals, recorded under driver 0.5.0

The subject is E4′ §1.1's enumeration, unchanged and in E4′'s order: 61
`#[test]` functions across seven `--test` targets, 20 / 15 / 4 / 4 / 8 / 4 / 6
= **61**, each carrying the run id E4's pass 1 produced for it. Every one of
those originals was recorded by `cargo-sensorium` **0.5.0** and is read here
by **0.5.2**; no row is dropped and none is added, so N is 61 and a smaller N
is a refusal to start, never a result.

**The rows live in a sibling file**,
`docs/superpowers/acceptance/2026-09-08-sensorium-rung4-e4pp-rows.md`,
carrying `# | fn | file | original run id | expected licence` — §1.2's
partition spelled per row so the subject and its expectation are read
together. The sibling is part of this pre-registration and is locked by
digest:

> **sha256 of the rows file:**
> `e3bd5313231ce2d65c190b4e2ac11355033920a3e1a8a2a17e4a15cf17d50aa8`

`rust/tests/acceptance_e4pp_lock.py` carries the same digest as
`ROWS_SHA256`, the suite checks both this printed value and the file on disk
against it, and the runner refuses to start on a mismatch: a byte that moves
in the rows file after the lock is a **different subject**, not a correction.
The rows were generated from `rust/tests/acceptance_e4p_rows.ROWS` — the
constant E4′'s suite already derives from E4′'s locked §1.1 and asserts equal
row for row — and never retyped.

### 1.2 The expected licence partition, written first

**Copied verbatim from E4′ §1.2**, whose paragraphs and table are this
record's expectation unchanged: the subject is the same 61 originals and the
rule under test is the same rule. Two translations are named after the copy,
and E4′'s closing shim-census paragraph is **not** carried — E4″ has no
census endpoint, and an expectation with no endpoint to meet would be a
number in the room with nothing to fail.

**Granted 57 of 61. WITHHELD on exactly four**, named below with the count of
the program's own threads that keeps them withheld. Every one of the 61 pairs
reports **exactly 1 harness thread** — libtest's per-test thread — on each
side, and under R1 that thread is excluded from the untraced-thread count and
named as the recorder's own.

**Where the four names and their counts come from.** They are E4's measured
thread counts, not a guess made here: the archived raw record's
`raw_h4.per_test[*].licence_caveats` (the field E4's assembled record surfaces
as `licence_per_test[*].licence_caveats`) carries, for each of the 61, two
sentences of the form *"the original / the rerun started N thread(s) besides
the main one …"*. Read over the 61, N is **1** on 57 pairs, **2** on one, and
**5** on three; the original and the rerun agree on N for every pair. E4 §1.2
had derived the same numbers from the clone's source before anything ran, and
E4 §5.2 published the agreement. Subtracting the one harness thread gives the
program's own threads in the table's last column.

| pair(s) | harness threads (excluded) | the program's own threads | licence under R1 |
|---|---|---|---|
| the other **57** originals of §1.1, each | 1 | **0** | **granted** |
| `a_pager_can_be_shared_across_threads` | 1 | **1** | **WITHHELD** |
| `the_refusal_advises_a_window_that_actually_places` | 1 | **4** | **WITHHELD** |
| `the_advice_never_exceeds_the_window_the_agent_already_had` | 1 | **4** | **WITHHELD** |
| `the_journal_records_the_advice_alongside_the_refusal_arithmetic` | 1 | **4** | **WITHHELD** |

**Why exactly these four, from the source rather than from the counts.**
`a_pager_can_be_shared_across_threads` (`pager_obligation_test.rs:576`) spawns
exactly one thread at line 582 and joins it at 584 — E4 §1.2's named
thread-spawning test. The three `pager_refusal_advice_test` tests each call
`bloomery_daemon::test_support::serve_fake()`, which spawns `WORKER_COUNT = 4`
workers on one shared server — E4 §1.2's named hazard. The fourth test of that
file, `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess`,
drives the substrate directly with no server and spawns nothing, so it is one
of the 57 and is expected **granted**. No other test in the seven spawns a
thread.

**What each of the four must say.** The WITHHELD reason names the program's
own thread count (1, 4, 4, 4) **and** states that the harness thread was
excluded as the recorder's own. A WITHHELD whose reason names the raw count
(2, 5, 5, 5) instead — i.e. one that never subtracted — is not this partition
and is H1's STOP, because it means the rule did not fire even though the word
happens to be right.

**The rest of the expectation, so H2 and H3 have their numbers first.**
**MATCH 61 of 61** — the comparator is untouched by this slice, so E4's gate
must reproduce exactly. **Pair 1 of 1 on all 61**, with the excluded-child
list empty on every one. The four verified/unverifiable counts of E4's H4 are
expected unchanged in kind (source and environment verified for real; output
and children UNVERIFIABLE by construction), and they are **reported, never
gated and never summed**: this record changes the licence's thread arithmetic,
not what it can see.

**The two translations.** The paragraph above names E4′'s endpoint ids:
E4′'s H2 (the verdict) and H3 (the pair) are **this record's H3**, which
gates both; E4′'s H4 — the shim census — has no counterpart here. The four
verified/unverifiable counts named two paragraphs up are **E4's** H4, not
E4′'s: E4′ carried them over in kind, and so does this record, **reported and
unsummed** under §1.5.
Nothing about the partition itself is translated — 57, the four names,
1/4/4/4, and 1 harness thread on every pair are this record's numbers as they
were E4′'s. E4′ *measured* that partition and got `granted` = 0, all 61
withheld by the env clause; that reading is E4′'s result, it stands, it is
the confound this slice removes, and it is deliberately not carried into any
cell here as a prior. A second 0 is H1's STOP a second time and no third pass
is authorised by this document.

### 1.3 The instrument, the arms, and the launch guard

**The driver is built, never found.** `cargo-sensorium` **0.5.2**, built by
the preflight from **this branch's HEAD at measurement time** (the
measurement commit), with the commit, the `built_from` result and the
binary's sha256 recorded in §2 **before and after** — the pre-repair-binary
trap of the E6⁗ record is why the runner builds it rather than trusting a
path. The version token exists so §2 can name the driver by token as well as
by sha, because `driver_version` is what a trace carries; **it is an
expectation, not a gate**. Every version token that appears inside a sentence
this record checks is read from the trace's own `meta.recorder` and from the
driver's recorded version, never hard-coded here, and §2 records what each
actually was.

**The reader** is this repository's `.venv` Python running `python -m
sensorium` at the branch HEAD §2 records. The rules it reads by are the
designs', not this document's: the verdict under slice-2 design §3.1, the
licence under slice-2 §3.2 as amended by this slice's **R1** (the fragment
strip), **R3** (the harness anchor) and **R4/A-§3** (session set 1), the pair
under slice-3's rule, and every refusal sentence under slice-2 §2.3.

**The kept store is never written.** For each of §1.1's 61 run ids the runner
copies the original out of the kept E4 store into a FRESH one with

```
sqlite3 <kept>/traces/<run>.db "VACUUM INTO '<fresh>/traces/<run>.db'"
```

— the **statement** is what is pre-registered; its executor is the `sqlite3`
CLI when one is on `PATH`, else Python's `sqlite3` module running the
identical SQL, and §2 records which and the SQLite library version. Each
copy's `meta.run_id` must equal `<run>` or the run refuses to start, before
any number. The copies are made **before arm A opens**, the fresh store holds
only those 61 files at that moment (§2 records the listing count), and the
`st_mtime` and size of every `.db` in the kept store are recorded before and
after the whole run — a single changed mtime is a STOP.

**Locations — the only box-local paths this record names.** Every one is
either FRESH for this run or READ-ONLY for its whole duration.

| what | value |
|---|---|
| trace store — FRESH, holding only the 61 copies when arm A opens | `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e4pp` |
| cargo target for every rebuild — FRESH and empty at the start | `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/bloomery-target-e4pp` |
| H8's corpus target — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e4pp-corpus` |
| the dry run's two siblings — FRESH, emptied before arm A opens | `/mnt/extra/sensorium-rung2/sensorium-dir/e4pp-dry`, `/mnt/extra/sensorium-rung2/bloomery-target-e4pp-dry` |
| the kept E4 store — READ-ONLY, source of the 61 copies (122 `.db`) | `/mnt/extra/sensorium-rung2/sensorium-dir/e4` |
| the clone under measurement — READ-ONLY, at E4's pin | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |

The clone is read-only for the whole run and each refocus rebuilds inside it:
its HEAD, porcelain and `Cargo.lock` sha256 are recorded before and after,
and the lock is restored to the pin if a `cargo` invocation moved it.
`SENSORIUM_TIER` is not set — each refocus replays the tier recorded on its
own original, E4's default `call`. `SENSORIUM_NO_INVOCATION_LOG` is unset, so
every reader invocation is logged into the fresh store (§2 records the count).

**Session set 1, printed here so "the first key" is decidable.** The set is
A-§3's, in A-§3's order, and this order is what arm C's choice reads:

> `DBUS_SESSION_BUS_ADDRESS`, `XDG_SESSION_ID`, `TERM_SESSION_ID`,
> `WINDOWID`, `TMUX`, `TMUX_PANE`, `SSH_AGENT_PID`, `SSH_AUTH_SOCK`,
> `SSH_CLIENT`, `SSH_CONNECTION`, `SSH_TTY`, `INVOCATION_ID`,
> `JOURNAL_STREAM`, `SYSTEMD_EXEC_PID`; prefix `CLAUDE_CODE_`.

**Arm C's candidate list is the fourteen EXACT names above, in that order,
and nothing else.** The `CLAUDE_CODE_` prefix is never a candidate: a prefix
names no key, so "the first key absent from both sides" would not be
decidable over it, and a `CLAUDE_CODE_*` name invented by the runner would be
a key this box's agent session may create or destroy underneath the
measurement. The prefix stays in the set for the purpose it has — exempting
whatever `CLAUDE_CODE_*` keys the shells really carry, which on this box is
`CLAUDE_CODE_SESSION_ID` — and takes no part in arm C's choice.

**The launch guard, and what it may and may not refuse on.** Before any
refocus runs, the preflight compares the runner's own process environment
with **every** original's recorded one, after the recorder's exclusions, the
relocation rule and the fragment strip, and:

1. **Every key OUTSIDE session set 1 must match.** A difference there is a
   refusal to launch (before any number), because it is an uncontrolled
   instrument variable, not a subject property. The launcher satisfies this
   by **exporting** the three keys rule 3 names, exactly as E4′'s launcher
   did — never by exempting them.
2. **Every key INSIDE session set 1 that differs is recorded by name, BEFORE
   any refocus runs**, into `pins.session_keys_differing`. H4 and H6 compare
   the printed lines against **that recorded set**, by name and by count —
   never against a set read out of the same lines they are checking.
3. **The expected differing set on this box is exactly
   `CLAUDE_CODE_SESSION_ID`.** Measured 2026-09-08 (names only) against kept
   original `20260907-111144-33d30c` from this session's shell: after the
   recorder's exclusions, 73 keys equal, 0 added, 3 missing
   (`PYTHONDONTWRITEBYTECODE`, `SSL_CERT_DIR`, `SSL_CERT_FILE` — the previous
   launcher's own pins, which the E4″ launcher exports too), exactly **one**
   changed. **A different set is REPORTED, not a STOP**: the launch shell is
   the *instrument's*, not the subject's, and which session variables this
   box's shell happens to carry on the day is a fact about the launcher. What
   would be a STOP is a difference outside the set (rule 1) or a printed line
   that disagrees with the recorded set (H4).

**The arms.**

- **A — the subject.** All 61 rows of §1.1, `refocus <run> --focus <name>`,
  under the guard's environment unmodified. H1–H4 and H7 read arm A.
- **B — the control that must still bite.** Four rows, re-run with
  **`E4PP_INPUT=1`** added: a key on no list, standing in for something the
  program could have read. Expected **WITHHELD 4/4**, each env caveat naming
  `E4PP_INPUT`. If a key outside session set 1 no longer withholds, the
  licence stopped meaning anything and the slice's own exemption is what did
  it.
- **C — the control that must not bite.** The same four rows, re-run with the
  **FIRST of the fourteen exact names of session set 1, in the order printed
  above, that is absent from BOTH the original's recorded environment and the
  runner's own**, set to the launch stamp. The `CLAUDE_CODE_` prefix is not a
  candidate (above). The key is **chosen and recorded at preflight**
  (`pins.injected_session_key`), never chosen here, because which keys this
  box's shell exports is not knowable before the day. If no key of the list
  is absent from both sides, the preflight **REFUSES to launch** and says so:
  it never falls back to a key that is already present, and never reaches
  outside the set for one. Expected: the licence word equals arm A's on 4/4,
  and the session set on the line is the preflight's ∪ the chosen key, with
  K exactly one greater.

**The four rows of arms B and C**, named here so the arms are not a choice
made at run time: rows 1–3 of §1.1 —
`unmeasured_model_is_fail_closed_read_only_and_status_shows_null`,
`unknown_model_mutating_verbs_is_false`,
`stored_keep_gate_enables_mutating_verbs_and_populates_status`, all three
expected **granted** under arm A — and `a_pager_can_be_shared_across_threads`,
expected **WITHHELD** for its one program thread, so a control's env caveat is
read beside a thread reason that must survive it.

**The dry run, and what it must show.** Two pairs from the kept store (one
expected granted, and `a_pager_can_be_shared_across_threads`) into the `-dry`
siblings, before arm A. It must show **the strip clause firing on an original
whose rt hash differs from the re-run's** — a dry run under one build is not a
dry run of this instrument, which is precisely E4′'s lesson. A dry run that
does not show it has not checked the instrument: the launch does not happen,
and that is infrastructure, not a STOP.

**Every measurement is `{value, n, lens, dropped}`.** A `null` value with a
reason is the only not-measured; `0` is measured-and-zero; no endpoint is
ever filled from an expectation, so a headline that borrowed from one could
not fail. Loads at every phase's start are recorded. Nothing is gated on a
wall.

### 1.4 The endpoints and the kill criteria

Every row's gate is decidable from named fields of the record's own
`results.json` — `endpoints.<id>.<cell>`, each a `{value, n, lens, dropped}`
measurement — so a reader can check the verdict without re-reading the prose.
Both readings are pre-committed; where a row's two readings disagree, the
disagreement is the finding and is reported as one, never resolved silently
in favour of the friendlier number.

| id | question | endpoint (both readings pre-committed) |
|---|---|---|
| H1 | does the harness rule change the licence word as predicted? | **Gate:** `H1.headline` = **57** granted and `H1.withheld` = **exactly §1.2's four**, by name, each mapping to its program-thread count **1 / 4 / 4 / 4** → **PASS**. Any other partition — a different count, a different set, or a granted line among the four — is a **STOP**, and the partition observed is the finding. **Second reading, REPORTED:** `H1.reasons_that_never_subtracted` is empty (no WITHHELD reason names the raw 2/5/5/5), `H1.hides_the_exclusion` is empty (no granted line omits the excluded harness thread), and `H1.harness_threads_all_one` is true over 61 — read from the licence clause where it speaks and from the `threads:` line where it is silent, each count carrying the line it came from (H7). |
| H2 | is the recorder's fragment gone from the compare? | **Gate:** `H2.rustdocflags_in_changed` = **0 of 61** (`RUSTDOCFLAGS` appears in no pair's changed list), `H2.strip_clause_named` = **61 of 61** (the strip clause names `RUSTDOCFLAGS` on every pair), and `H2.relocated_set` on 61/61 is exactly E4′'s measured four — `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` → **PASS**; any other value on any of the three is a **STOP**. **Second reading, REPORTED:** the rt hash the fragment carries on each side (§1.5), and the count of fragments removed per key per side — a strip that fired on a pair whose two hashes were EQUAL would be a strip that could not have been tested, and is reported as one. |
| H3 | is the verdict untouched and the pair still found? | **Gate:** `H3.headline` = **MATCH 61 of 61** and `H3.pairs_of_one` = **61** → **PASS**. The comparator and the pairing are not changed by this slice, so a DIVERGED, a REFUSED, or a pair count ≠ 1 on any pair is a **STOP**, recorded with the pair's run ids. **Second reading, REPORTED:** `H3.word_and_exit_disagree` is empty (the printed verdict word and `refocus`'s exit — MATCH 0 / DIVERGED 1 / REFUSED 3 — agree on all 61), and `H3.excluded_children` = **0** on all 61; a disagreement between word and exit is itself a finding and is never resolved in favour of either. |
| H4 | do session differences stay outside the vote? | **Gate:** on **61 of 61**, `H4.session_names` equals `pins.session_keys_differing` by name and `H4.session_k` equals its size, and `H4.withholding_cites_a_session_key` is **empty** — no withholding reason cites a key of session set 1 → **PASS**; else **STOP**. **Second reading, REPORTED:** the exact line and fact wording on a granted pair, so a reader can see that A-§3's `env: unchanged outside session set 1 (…)` is what printed and that the caveat is `None`; and the count of pairs on which the session set was empty (which on this box it should not be, per §1.3's rule 3). **Lens, and the reading when it is bounded:** the names are read from the printed line, whose list is capped at 8 with a `+M more` tail. **If K > 8 on any pair**, `H4.session_names` goes **`null` with its reason** on that pair (kill 7) and H4 is decided **on K alone**: **PASS** only if `H4.session_k` equals `pins.session_keys_differing`'s size on 61 of 61 **and** `H4.withholding_cites_a_session_key` is empty; a K mismatch is a **STOP** exactly as a name mismatch would be. The reduced reading is published as the endpoint's lens and the record states plainly that the by-name half went unread — a bounded reading is never reported as the full one. On this box K is expected to be **1**, so this is a contingency, not the plan. |
| H5 | does the licence still bite outside the set? | **Gate:** arm B is **WITHHELD 4 of 4** (`H5.headline` = 4) and `H5.env_caveat_names_the_key` = **4 of 4**, each caveat naming `E4PP_INPUT` → **PASS**; **any granted line in arm B is a STOP** — the exemption ate the rule. **Second reading, REPORTED:** `H5.thread_reason_kept` — `a_pager_can_be_shared_across_threads` still carries its one-program-thread reason alongside the env caveat; a control that silenced the thread reason is a finding. |
| H6 | is the session count exact, and the word unmoved? | **Gate:** `H6.headline` = **4 of 4** pairs whose licence word equals arm A's for the same row; `H6.session_names` = `pins.session_keys_differing` ∪ {`pins.injected_session_key`} and `H6.session_k` = that set's size, on 4 of 4 → **PASS**; else **STOP**. **Second reading, REPORTED:** `H6.injected_key` — which key was chosen and why (the first of the printed order absent from both sides), and the two names the choice skipped over, so the rule is checkable rather than asserted. |
| H7 | is the instrument honest? | **Gate:** `H7.headline` = **0** — no partition cell is `None` on a pair whose licence printed; `H7.counts_carry_their_source_line` is true for every thread count (each says whether it came from the licence clause or the `threads:` line); `H7.licence_verified_counts` is **non-null**; and `H7.version_probe` is a version token **or** `null` with its reason, never an empty string → **PASS**; else **STOP of the instrument**, not of the subject. **Second reading, REPORTED:** the four verified/unverifiable counts in kind (source and environment verified for real; output and children UNVERIFIABLE by construction, reported and never summed), and every `dropped` list this run wrote. |
| H8 | did nothing else move? | **Gate:** `H8.corpus_rc` = 0 with every corpus case equal, run **WITH the driver** (`--require-driver`) and `H8.spawned_test_fn_present` true for `refocus_spawned_test_fn`; the whole Python suite green (`H8.pytest_rc` = 0); `cargo test --workspace` green (`H8.cargo_rc` = 0) → **PASS**; any red is a **STOP** (kill 2). Three commands, three return codes, each its own field — a summary line is prose and does not decide a gate. **Second reading, REPORTED:** `H8.pytest_summary` (the pass/skip counts), per-case equality of printed answers, and each suite's exit status beside its rc. This runs against **this repository**, never the clone. |
| reported | *(no gate)* | §1.5's list: wall per arm; arm B's verdicts; the two rt hashes; `driver_version` on both sides; K and its names. |

**Kill criteria.**

1. **A partition other than §1.2's is a STOP** (H1): not 57 granted, or a
   WITHHELD set other than the four named there, or a reason that never
   subtracted. Not a retry under a narrower rule, not a re-run with the
   lookup adjusted. The partition observed is the finding.
2. **A miss on H2, H3, H4, H5, H6 or H8 is a STOP with its number.** The
   strip, the anchor and the session set are what this slice ships; a control
   that does not discriminate is a result about the slice, not a reason to
   move the control. **H8's three commands are gates like any other**: a red
   corpus (`H8.corpus_rc` non-zero, a case unequal, or
   `refocus_spawned_test_fn` absent), a red Python suite (`H8.pytest_rc`
   non-zero) or a red `cargo test --workspace` (`H8.cargo_rc` non-zero) is a
   STOP, never a note appended to a passing record. **A miss on H7 is a STOP
   of the instrument**, distinguished in the record from a STOP of the
   subject. With kill 1 (H1), these eight cover every gated endpoint.
3. **A refusal to launch is not a measurement.** A guard failure outside
   session set 1, a missing or duplicated original, a `meta.run_id`
   mismatch, no eligible key for arm C, or a dry run that does not show the
   strip clause fire: the run does not start, nothing is read, and the
   record says which refusal it was.
4. **A `.FAILED` marker before any number has been read is
   infrastructure.** The run is archived, the fresh locations are emptied,
   the 61 copies are re-made by §1.3's statement, and it is relaunched from
   zero.
5. **A `.FAILED` marker after any number has been read is a STOP.** The
   numbers already read stand.
6. **Measured once, and nothing moves afterwards.** No endpoint is re-rolled
   and no completed measurement is re-run under a kinder command; and **no
   `src/`, crate, corpus or instrument change is made after the
   measurement** to make it come out differently. A miss is recorded with
   its number.
7. **A reader at its ceiling is the record.** Where a reader's own limit (a
   page, a cap, a truncation, the 8-name cap on a printed list) bounds what
   an endpoint can see, that is published as the endpoint's lens and the
   cell goes `null` with its reason rather than being filled from a smaller
   view.

**Bounds.** The loop runs detached (`setsid nohup`) with a pid file and a
`.DONE`/`.FAILED` marker carrying `exit=<n>`; nothing is read before the
marker exists. **The whole loop is bounded at 1 h 30 min** and **each
`sensorium refocus` invocation at 1800 s**. A bound reached is a `.FAILED`
and is read under rules 4 and 5. E4 and E4′ each measured a flat ~7 s per
refocus over the same 61; the bound is that shape with room for 69 rebuilds
rather than 61, and it is not an expectation — nothing is gated on a wall.

### 1.5 What this record publishes beyond the table

Reported without a gate, so a reader gets the facts the endpoints stand on
rather than only the verdicts:

- **The two tool hashes.** The rt hash the recorder's fragment carries on
  each side — the original's, written by `cargo-sensorium` 0.5.0, and the
  re-run's, written by 0.5.2 — recorded per pair. Their **difference** is the
  proof that the two builds are not the same build, the one condition E4′
  could not create and the whole reason E4″ exists; if they are equal on any
  pair, H2's second reading says so and that pair's strip was never tested.
- **`driver_version` on both sides**, read from each trace's own
  `meta.recorder` and from the built driver's recorded version, never from
  the tokens §1.3 expects. §2 states plainly if either differs.
- **K and its names** — the session set's size and members, per pair and per
  arm, beside `pins.session_keys_differing` and `pins.injected_session_key`.
- **Wall per arm** (A, B, C and the dry run), the first focus distinguished
  from the later ones with cargo's own build time inside each, and the driver
  build's wall separately.
- **Arm B's verdicts.** A variable the program actually READ would change the
  re-run's behaviour, so arm B's verdicts may not all be MATCH. That is a
  **finding, not a gate**: `E4PP_INPUT` is a name no code in the clone reads,
  and if a verdict moves anyway the record says which pair and leaves it.
- **The four verified/unverifiable licence counts**, carried from E4's H4 in
  kind and never summed into a verified total.
- **The store and disk facts**: copied and refocused trace sizes, the fresh
  store's size, disk free before and after, and the invocation-log row count
  (this record's own — the 61 copies carry none from E4).
- **The lens for every one of the above**, named with it. A number quoted
  without its instrument is not a property of the subject.

## 2. Environment

*(written by Task 8)*

## 3. Results

*(written by Task 8)*

## 4. Verdicts

*(written by Task 8)*

## 5. Gaps

*(written by Task 8)*
