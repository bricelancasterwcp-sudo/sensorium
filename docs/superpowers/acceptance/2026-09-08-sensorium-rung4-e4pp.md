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

Measured 2026-09-08T05:52:35-0500 → 2026-09-08T06:03:21-0500 by `rust/tests/acceptance_e4pp.py`, launched detached; the raw facts are `results-e4pp-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 is rendered from this document's `results.json`, which `acceptance_e4pp_schema.assemble_e4pp` derived from that raw file.

**Schema.** This record is `e4pp/1`: the raw record and this assembly were written under the same schema version.

**§1 byte-lock.** The runner refuses to start unless the locked range is byte-identical to the commit that locked it. Range awk '/^## 1/,/^## 2/' PLUS the definition of every footnote §1 references, checked at `2acdc21`: 28208 bytes, sha256 `5717507e8e0f4beb82a449df6312ac1427a276596fb1ee71e1cf106c7d547759` — identical: yes. The 61-row subject sibling is locked by DIGEST: `e3bd5313231ce2d65c190b4e2ac11355033920a3e1a8a2a17e4a15cf17d50aa8` — identical: yes. §1 has never been amended (amended: no).

| what | value |
|---|---|
| repo HEAD at the run | `3d1a723cdd80c4bf7dca8fc03c258dbeffe9c7b9` (branch `feat/rung4-footprint`); porcelain before / after empty / empty |
| the clone under measurement (READ-ONLY input) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; §1.3's pin `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; `Cargo.lock` back on the pin: yes |
| the KEPT E4 store (READ-ONLY input) | `/mnt/extra/sensorium-rung2/sensorium-dir/e4`, 122 `.db` file(s); unchanged across the whole run: yes |
| the copy | §1.3's `VACUUM INTO`, executed by ['python sqlite3 module'] (SQLite 3.46.1; `sqlite3` CLI on PATH: none) |
| the driver | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` sha256 `4b18cad4844cb288b0db47a2fab648f6b041f5df566806c828b9d203adfabcb1`, built by this run from HEAD `3d1a723cdd80c4bf7dca8fc03c258dbeffe9c7b9` (rebuilt: no); unchanged after: yes |
| the driver's version token | `cargo-sensorium 0.5.2` — read from the TRACE's own `meta.driver_version`, never from the instrument |
| the launch guard | `session_parity`: 61 original(s) over 77 compared key(s); differing OUTSIDE session set 1: none (a difference there is a refusal to launch). Session keys differing: ['CLAUDE_CODE_SESSION_ID'] — expected ['CLAUDE_CODE_SESSION_ID'], as expected: yes. A different set is REPORTED, never a STOP |
| the arms | B injects `E4PP_INPUT`; C injects `TERM_SESSION_ID`, chosen at preflight as the first of session set 1's fourteen exact names absent from both sides. Rows: ['unmeasured_model_is_fail_closed_read_only_and_status_shows_null', 'unknown_model_mutating_verbs_is_false', 'stored_keep_gate_enables_mutating_verbs_and_populates_status', 'a_pager_can_be_shared_across_threads'] |
| the fresh trace store | `/mnt/extra/sensorium-rung2/sensorium-dir/e4pp`; invocation log 69 row(s) |
| the fresh cargo target | `/mnt/extra/sensorium-rung2/bloomery-target-e4pp`; H8's corpus target `/mnt/extra/sensorium-rung2/bloomery-target-e4pp-corpus` (from an env var: no) |
| `TMPDIR` | None; `tempfile.gettempdir()` resolved to `/tmp` |
| no other `cargo` was running | `pgrep -x cargo` → rc 1, pids [] |
| `SENSORIUM_TIER` | NOT set by this record: each refocus replays the tier recorded on its own original, and E4's pass 1 ran with SENSORIUM_TIER unset, so the driver's default `call` applies again |
| the invocation audit log | NOT silenced: SENSORIUM_NO_INVOCATION_LOG is unset, so every reader invocation this record makes is logged into the FRESH store, and the row count is recorded at the end. The 61 copied originals carry no such rows from E4, so the count is this record's own |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25); cargo 1.96.0 (30a34c682 2026-05-25); Python 3.14.4; sensorium `0.8.5` in the installed distribution metadata |
| machine | 16 CPU(s), governor `powersave`, 1-minute load 0.74 at the start |
| disk | repo 6.12 → 6.12 GB free; artifact disk 30.24 → 7.61 GB free |
| ceilings | {'refocus_timeout': 1800, 'loop_budget_s': 5400, 'corpus_timeout': 7200, 'pytest_timeout': 3600, 'cargo_test_timeout': 7200} |
| logs | /home/brice/workspace/sensorium/.superpowers/sdd/2026-09-08-sensorium-rung4-footprint/acceptance-e4pp/logs |

**Load at each phase's start.** pass2 0.74; armB 1.65; armC 1.51; H2 1.39; H3 1.39; H4 1.39; H5 1.39; H6 1.39; H6 1.39; H7 1.19.

**The two dry runs, 2026-09-08, before any number of this record existed.** §1.3
makes a dry run that shows the strip clause fire a condition of the launch. The
**first** (`05:38:55` → `05:39:23`) came back `exit=9` with
`dry_check.showed_the_strip_on_differing_hashes` **empty** on 2 of 2 rows — an
**instrument** defect, not a reading: the strip-clause regex over-ran the
two-space join between the env line's clauses, so what it reported as the
stripped key carried the next clause's names too. §1.3's words make that a
refusal to launch and §1.4's rule 4 makes a `.FAILED` before any number
infrastructure, so it was fixed at the measurement commit `3d1a723` before a
single number was read; no byte of §1 moved and no expectation was edited. The
**second** (`05:51:34` → `05:52:02`) came back `exit=0`:
`showed_the_strip_on_differing_hashes` names **2 of 2** rows, `did_not_show_it`
is empty, and `arms_rehearsed` is **true** — arms B and C, two rows each,
`never_run` and `rows_without_a_pair` empty on both. Both were archived under
`acceptance-e4pp/dry-1/` and `dry-2/` and their `-dry` siblings emptied before
the real launch, as §1.3 requires.

**The rows sibling, and where the measured columns went.** §1.1 locks the 61-row
subject **by digest**, and `tests/test_acceptance_e4pp_lock.py` asserts it
against the printed value and the file both — so appending measured columns
there would have made a **different subject**, not a result. The locked file is
left byte-identical: `…-e4pp-rows.md` hashes to
`e3bd5313231ce2d65c190b4e2ac11355033920a3e1a8a2a17e4a15cf17d50aa8` **before this
write and after it**, the value §1.1 prints. The four measured columns — licence
word, program threads, verdict, pair count — are in a **second sibling**,
[`…-e4pp-rows-measured.md`](2026-09-08-sensorium-rung4-e4pp-rows-measured.md),
sha256 `7d7dc62b08788a39e9fe69843e4566b4538f91b67ce0e34e3d6c39cf65c92890`,
written after the measurement from `pairs.rows[*]` — `arm` `A` in `index` order
for the 61, `armB`/`armC` for the eight control rows — each row's `#`, name and
original run id checked equal to the locked file's before a measured column was
written beside it.

## 3. Results

The gate of each row, and both readings where §1 pre-committed two. A `null` is not-measured with its reason; `0` is a measured zero; a KILLED cell has no numeric reading at all. The per-pair tables are in `results.json`.

### H1 — does the harness rule change the licence word as predicted?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| licences GRANTED (the gate: 57) | 57 | 61 | the licence word `sensorium refocus` printed beside each of the 61 arm-A pairs, and the thread counts inside i… | none |
| the WITHHELD pairs and their program-thread counts | {'a_pager_can_be_shared_across_threads': 1, 'the_advice_never_exceeds_the_window_the_agent_already_had': 4, 'the_journal_records_the_advice_alongside_the_refusal_arithmetic': 4, 'the_refusal_advises_a_window_that_actually_places': 4} | 61 | the licence word `sensorium refocus` printed beside each of the 61 arm-A pairs, and the thread counts inside i… | none |
| granted lines that HIDE the exclusion (2nd reading) | [] | 61 | granted pairs whose thread line does NOT name the excluded harness thread (a finding even when the word is pre… | none |
| WITHHELD reasons that never subtracted (2nd reading) | [] | 61 | WITHHELD pairs whose reason names the RAW thread count -- the rule did not fire even though the word is right … | none |
| every pair reports exactly 1 harness thread | True | 61 | every pair reports exactly 1 harness thread (§1.2) | none |

Rule: granted = 57 AND the WITHHELD set is exactly §1.2's four, by name, with 1/4/4/4; any other partition is a STOP. Verdict: **PASS** (as predicted: yes).

Withheld only here: none; withheld missing: none; count mismatches: none. Harness phrase(s): ["libtest's per-test thread, excluded as the recorder's own"]. Pairs whose licence could not be read: none.

### H2 — is the recorder's fragment gone from the compare?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| pairs whose CHANGED list names `RUSTDOCFLAGS` (the gate: 0) | 0 | 61 | the `env:` line each of the 61 arm-A pairs printed: R1's strip clause, the CHANGED name list, and Task 5b's re… | none |
| pairs whose strip clause NAMES it (the gate: 61) | 61 | 61 | the `env:` line each of the 61 arm-A pairs printed: R1's strip clause, the CHANGED name list, and Task 5b's re… | none |
| the relocated key set (the gate: E4′'s four) | ['CARGO_BIN_EXE_bloomery-daemon', 'CARGO_BIN_EXE_flywheel-tool', 'CARGO_TARGET_DIR', 'LD_LIBRARY_PATH'] | 61 | the `env:` line each of the 61 arm-A pairs printed: R1's strip clause, the CHANGED name list, and Task 5b's re… | none |
| pairs whose two rt hashes DIFFER (2nd reading) | 61 | 61 | §1.5: the rt hash the recorder's fragment carries on each side, read from each trace's own recorded `RUSTDOCFL… | none |
| pairs whose rt hash could not be READ (2nd reading) | [] | 61 | §1.5: pairs whose rt hash could not be read on one side or both. Published BESIDE `hashes_differ` and the equa… | none |

Rule: `RUSTDOCFLAGS` in 0 of 61 changed lists, the strip clause naming it on 61 of 61, and E4′'s four relocated keys on 61 of 61. Verdict: **PASS** (as predicted: yes).

Expected relocated set: ['CARGO_BIN_EXE_bloomery-daemon', 'CARGO_BIN_EXE_flywheel-tool', 'CARGO_TARGET_DIR', 'LD_LIBRARY_PATH']; sets seen: [['CARGO_BIN_EXE_bloomery-daemon', 'CARGO_BIN_EXE_flywheel-tool', 'CARGO_TARGET_DIR', 'LD_LIBRARY_PATH']]; pairs matching: 61. Pairs naming `RUSTDOCFLAGS` as changed: none; pairs whose strip clause was silent: none. **Pairs whose two rt hashes were EQUAL — a strip that pair could not have tested:** none. Pairs whose rt hash could not be read on one side or both — counted as neither, because an unreadable run and a single-build run must not print the same number: {'value': [], 'n': 61, 'lens': "§1.5: pairs whose rt hash could not be read on one side or both. Published BESIDE `hashes_differ` and the equal list, because counted as 'not differing' an unreadable run and a single-build run would print the same number", 'dropped': []} (readable: 61).

### H3 — is the verdict untouched and the pair still found?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| MATCH verdicts (the gate: 61) | 61 | 61 | the verdict word `refocus` printed on each of the 61 arm-A pairs, read APART from the process exit; and the ST… | none |
| pairs of exactly one (the gate: 61) | 61 | 61 | the verdict word `refocus` printed on each of the 61 arm-A pairs, read APART from the process exit; and the ST… | none |
| word/exit disagreements (2nd reading) | [] | 61 | pairs where the printed word and the exit (MATCH 0 / DIVERGED 1 / REFUSED 3) disagree -- a finding, never reso… | none |
| pairs with a NON-empty R2 exclusion list (2nd reading) | 0 | 61 | pairs whose R2 exclusion list is NON-empty (expected empty on all 61) | none |

Rule: MATCH 61 of 61 and 61 pairs of exactly one. Verdict: **PASS** (as predicted: yes).

Non-MATCH: none. Pair counts other than 1: none. The pair is read from the STORE, by THAT invocation's launch timestamp, and the printed id is a cross-check beside it.

### H4 — do session differences stay outside the vote?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| the printed session set (the gate: the preflight's pin) | ['CLAUDE_CODE_SESSION_ID'] | 61 | the session clause each arm-A pair printed on its `env:` line (A-§3's `unchanged outside session set 1 (…)`), … | none |
| K (the gate: the pin's size) | 1 | 61 | the session clause each arm-A pair printed on its `env:` line (A-§3's `unchanged outside session set 1 (…)`), … | none |
| withholdings citing a session key (the gate: none) | [] | 61 | WITHHELD pairs whose CHANGED list names a key of session set 1 -- the whole of R4 is that such a key never wit… | none |

Rule: the printed session set equals `pins.session_keys_differing` by name and by size on 61 of 61, and no withholding cites a key of session set 1. Verdict: **PASS** (as predicted: yes).

The pin (recorded at preflight, before any refocus): ['CLAUDE_CODE_SESSION_ID'] (n 1); names matching on 61 pair(s), K on 61. Decided on K alone: no. Pairs with an EMPTY session set: 0.

The line on a granted pair: `env: unchanged outside session set 1 (104 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _; 1 session variable(s) differ: CLAUDE_CODE_SESSION_ID)  4 variable(s) differ only by the target directory: CARGO_BIN_EXE_bloomery-daemon, CARGO_BIN_EXE_flywheel-tool, CARGO_TARGET_DIR, LD_LIBRARY_PATH; treated as unchanged; the recorder's own fragment stripped before comparing: RUSTDOCFLAGS  the recorder's own, also not compared: CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER, RUSTC_WORKSPACE_WRAPPER, SENSORIUM_CARGO_SENSORIUM, SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_RT_DIR, SENSORIUM_SPOOL, SENSORIUM_TARGET, SENSORIUM_TIER, SENSORIUM_TOOL_HASH, SENSORIUM_WS`.

### H5 — does the licence still bite outside the set?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| arm B WITHHELD (the gate: 4) | 4 | 4 | arm B: the same four rows re-run with one key on no list added to the launch environment, read from each pair'… | none |
| caveats naming the key (the gate: 4) | 4 | 4 | arm B: the same four rows re-run with one key on no list added to the launch environment, read from each pair'… | none |
| the pager row's thread reason survived (2nd reading) | True | 1 | the pager row's one-program-thread reason, read beside the env caveat: a control that SILENCED the thread reas… | none |

Rule: arm B WITHHELD 4 of 4, each env caveat naming `E4PP_INPUT`; any granted line is a STOP. Verdict: **PASS** (as predicted: yes).

Key: `E4PP_INPUT`. Granted lines (any is a STOP): none; WITHHELD without the key named: none. Arm B's verdicts (REPORTED, never a gate): {'unmeasured_model_is_fail_closed_read_only_and_status_shows_null': 'MATCH', 'unknown_model_mutating_verbs_is_false': 'MATCH', 'stored_keep_gate_enables_mutating_verbs_and_populates_status': 'MATCH', 'a_pager_can_be_shared_across_threads': 'MATCH'}.

### H6 — is the session count exact, and the word unmoved?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| arm C's word equals arm A's (the gate: 4) | 4 | 4 | arm C: the same four rows re-run with the FIRST of session set 1's fourteen exact names absent from both sides… | none |
| the printed session set (the gate: the pin ∪ the key) | ['CLAUDE_CODE_SESSION_ID', 'TERM_SESSION_ID'] | 4 | arm C: the same four rows re-run with the FIRST of session set 1's fourteen exact names absent from both sides… | none |
| K (the gate: one greater) | 2 | 4 | arm C: the same four rows re-run with the FIRST of session set 1's fourteen exact names absent from both sides… | none |
| the injected key (2nd reading; DERIVED from the pin) | TERM_SESSION_ID | 1 | `pins.injected_session_key` -- chosen and recorded at PREFLIGHT and DERIVED here, never chosen a second time | none |

Rule: arm C's licence word equals arm A's on 4 of 4, and the session set is the pin ∪ the injected key with K exactly one greater. Verdict: **PASS** (as predicted: yes).

Expected set: ['CLAUDE_CODE_SESSION_ID', 'TERM_SESSION_ID'] (K 2); names matching on 4 pair(s), K on 4. Words that MOVED: none. The choice skipped ['DBUS_SESSION_BUS_ADDRESS', 'XDG_SESSION_ID'] — the FIRST of session set 1's fourteen exact names, in the order §1.3 prints, absent from BOTH the original's recorded environment and the runner's own.

### H7 — is the instrument honest?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| partition cells NULL on a printed licence (the gate: 0) | 0 | 69 | this record's OWN instrument, over every pair of every arm: the partition cells beside the licence word that p… | none |
| every count carries its source line | True | 69 | this record's OWN instrument, over every pair of every arm: the partition cells beside the licence word that p… | none |
| the verified/unverifiable counts (non-null) | source verified 61, env verified 61, exit verified 61, output unverifiable 61, children unverifiable 61, n 61 | 61 | the four verified/unverifiable counts, COUNTED over `raw_pass2.refocuses[*].licence` and never summed | none |
| the version probe | 0.8.5 | 1 | `/home/brice/workspace/sensorium/.venv/bin/python -c import importlib.metadata as m; print(m.version('sensoriu… | none |

Rule: 0 null partition cells on a printed licence, every count carrying its source line, non-null verified counts, and a version probe that is a token or null WITH its reason — a miss is a STOP of the INSTRUMENT. Verdict: **PASS** (as predicted: yes).

Null partition cells: none; counts with no source line: none. Probe reason: none. Every `dropped` list this run wrote: none. A miss here is a STOP of the instrument, not of the subject: §1.4's kill 2 distinguishes the two in the record.

### H8 — did nothing else move?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| corpus exit | 0 | 1 | this repository, never the clone: the corpus collector over every case WITH the driver (`--require-driver`), t… | none |
| `refocus_spawned_test_fn` present | False | 1 | the corpus collector's own `load_cases()` listing, asked whether it names `refocus_spawned_test_fn` | none |
| Python suite exit | 0 | 1 | this repository, never the clone: the corpus collector over every case WITH the driver (`--require-driver`), t… | none |
| `cargo test --workspace` exit | 0 | 1 | this repository, never the clone: the corpus collector over every case WITH the driver (`--require-driver`), t… | none |
| the Python suite's summary (reported) | 2256 passed, 4 skipped in 128.70s (0:02:08) | 1 | this repository, never the clone: the corpus collector over every case WITH the driver (`--require-driver`), t… | none |

Rule: corpus rc 0 with `--require-driver` and `refocus_spawned_test_fn` present, pytest rc 0, `cargo test --workspace` rc 0. Verdict: **STOP** (as predicted: no).

Corpus: 63 case(s), args ['--require-driver'], require_driver yes; failures none; errors none; skipped none. Rust result lines: ['test result: ok. 305 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.22s', 'test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.13s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.36s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.22s', 'test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.12s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s', 'test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s', 'test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.09s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.75s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.13s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.48s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 81 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.06s', 'test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 47 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.31s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.11s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.85s', 'test result: ok. 25 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 38 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.11s', 'test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 8 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.54s', 'test result: ok. 0 passed; 0 failed; 9 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 14 ignored; 0 measured; 0 filtered out; finished in 0.00s'].

### Reported without a gate

**The two tool hashes.** 61 pair(s) carried DIFFERENT rt hashes on their two sides; 0 carried equal ones; 0 could not be read at all. their DIFFERENCE is the proof the two builds are not the same build -- the one condition E4′ could not create; a pair whose two hashes were EQUAL is a pair whose strip was never tested, and a pair whose hash could not be READ is on neither list -- counted as 'not differing' an unreadable run and a single-build run would print the same number.

**K and its names.** Pin ['CLAUDE_CODE_SESSION_ID'] (n 1), expected ['CLAUDE_CODE_SESSION_ID'], as expected: yes; injected `TERM_SESSION_ID`. a differing set other than the expected one is REPORTED, never a STOP: the launch shell is the instrument's, not the subject's (§1.3's rule 3).

**Wall per arm.** A: first 8.375 s, later mean 6.667 s over 61; B: first 3.35 s, later mean 3.38 s over 4; C: first 3.363 s, later mean 3.448 s over 4. nothing is gated on a wall.

**The four verified/unverifiable counts, in kind and never summed.** source 61, environment 61, exit 61 verified; output 61, children 61 UNVERIFIABLE by construction, over n 61.

**The store.** 61 original(s) copied, 21770240 byte(s), by ['python sqlite3 module']; the fresh store held 61 file(s) when the loop opened and only the copies: yes; 130 trace(s) at the end. The KEPT store: 122 file(s) before, 122 after; identical: yes. The invocation log: 69 row(s) — this record's own.

**Arm B's verdicts.** {'unmeasured_model_is_fail_closed_read_only_and_status_shows_null': 'MATCH', 'unknown_model_mutating_verbs_is_false': 'MATCH', 'stored_keep_gate_enables_mutating_verbs_and_populates_status': 'MATCH', 'a_pager_can_be_shared_across_threads': 'MATCH'}. a variable the program actually READ would change the re-run's behaviour, so arm B's verdicts may not all be MATCH. That is a FINDING, not a gate.

**STOP.** H8 (kill 2): a miss with its number. Gate: corpus rc 0 with `--require-driver` and the spawned-test case present, pytest rc 0, `cargo test --workspace` rc 0. This is a STOP of the subject

## 4. Verdicts

**H1–H7 PASS, H8 STOP on an instrument cell.** The two questions this slice
asked — *does the harness-thread rule change the licence word as predicted*, and
*is the recorder's own fragment gone from the compare* — are answered **PASS at
n = 61**, under a driver build different from the originals': the rt hash the
fragment carries moved from `d9ce385a08c6646b` on every original to
`45773c80095d5b87` on every re-run (`reported.rt_hashes.by_pair`), the one
condition E4′ could not create, on all 61 pairs. The eighth row is `H8`: it
missed on a cell of this record's own reader while its three commands came back
green — under §1.4's kill 2 a **STOP with its number**, and under kill 6 not
something this record may repair into a PASS. The marker is `e4pp.FAILED`,
**`exit=7`**, `numbers_read` **true** since 05:52:44: under §1.4's rule 5 a
`.FAILED` after a number has been read is a STOP and **the numbers already read
stand**.

**H1 — PASS.** `endpoints.H1.headline` = **57** granted of 61 against
`H1.expected_granted_n` **57**, and `H1.withheld` is exactly §1.2's four by name
with their program-thread counts — `a_pager_can_be_shared_across_threads` **1**,
`the_refusal_advises_a_window_that_actually_places` **4**,
`the_advice_never_exceeds_the_window_the_agent_already_had` **4**,
`the_journal_records_the_advice_alongside_the_refusal_arithmetic` **4**.
`withheld_only_here`, `withheld_missing` and `withheld_count_mismatches` are all
empty and `withheld_set_as_predicted` is true, so the partition is not merely
the right size: it is the right four. **This is the number E4′ measured as 0** —
all 61 withheld by the env clause; that reading stands as E4′'s, and what moved
between the two records is the strip R1 ships, not the subject and not the rule.

**Second reading, REPORTED, and 61-wide.** `H1.hides_the_exclusion` is **empty**
over 61 (no granted line omits the excluded harness thread);
`H1.reasons_that_never_subtracted` is **empty** over 61 (no WITHHELD reason
names the raw 2/5/5/5); `H1.harness_threads_all_one` is **true** over 61;
`H1.sides_disagree` and `H1.unread` are empty; `H1.harness_phrases` holds one
spelling only, `libtest's per-test thread, excluded as the recorder's own`. Two
of those — `reasons_that_never_subtracted` and `sides_disagree` — E4′ could
publish over **4** pairs only, and its `harness_threads_all_one` came back
**false** over 61; here `H1.counts_source_by_name` reads `licence-clause` on
**61 of 61**, because R1's licence clause now speaks on a granted pair too — *no
thread started besides the main one and 1 harness thread (…)* — so every count
has a clause to come from and the aggregates cover the whole subject. E4′ gap 1,
closed and shown closed.

**H2 — PASS, and the strip was TESTED on every pair.**
`H2.rustdocflags_in_changed` = **0** of 61 with `rustdocflags_in_changed_pairs`
empty; `H2.strip_clause_named` = **61** of 61 with `strip_clause_missing` empty;
`H2.relocated_set` is E4′'s measured four — `CARGO_BIN_EXE_bloomery-daemon`,
`CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` — with
`relocated_sets_seen` holding that one set and `relocated_set_matches` **61**.
**Second reading:** `H2.hashes_differ` = **61** of 61,
`hashes_equal_so_the_strip_was_untested` **empty**, `H2.hashes_unread`
**empty**, `hashes_readable` **61**. A strip that fired on a pair whose two
hashes were equal is a strip nothing could have tested; there is no such pair.
**The reading's other half — the count of fragments removed per key per side —
was read and never published**: `raw_pass2.refocuses[*].original_rt_hash.fragments`
and `.rerun_rt_hash.fragments` are **1** on 61 of 61, `occurrences` **2** on both
sides, and the assembly lifts neither into `endpoints.H2` nor
`reported.rt_hashes` — findings gap 4.

**H3 — PASS.** `H3.headline` = **MATCH 61 of 61** with `non_match` empty, and
`H3.pairs_of_one` = **61** with `not_one` empty — the pair read from the store,
the printed id agreeing beside it. **Second reading:** `H3.word_and_exit_disagree`
**empty** (every `pairs.rows[*].exit` is 0) and `H3.excluded_children` = **0**
over 61. The comparator and the pairing are untouched and reproduced E4′'s
verdict on every pair.

**H4 — PASS.** `H4.session_names` = `['CLAUDE_CODE_SESSION_ID']` on **61 of
61**, equal to `pins.session_keys_differing` by name, and `H4.session_k` = **1**
= the pin's size on 61 of 61 (`session_names_match` 61, `session_k_match` 61).
`H4.withholding_cites_a_session_key` is **empty**: not one withholding cites a
key of session set 1, which is the whole of R4. **Second reading:**
`H4.pairs_with_an_empty_session_set` = **0**, so the launch shell did differ from
the originals' as §1.3's rule 3 expects; `H4.names_bounded` is empty and
`H4.decided_on_k_alone` **false** — K is 1, far under the 8-name cap, so kill 7's
reduced reading never applied and the by-name half was read in full.

**H5 — PASS, and the exemption did not eat the rule.** `H5.headline` = **4**
WITHHELD of 4 with `H5.granted` **empty**, and `H5.env_caveat_names_the_key` =
**4** of 4 with `env_caveat_missing_the_key` empty, each caveat naming `H5.key`
= `E4PP_INPUT`: a key on no list still withholds exactly as it did before
session set 1 existed, and one granted line would have been a STOP. **Second
reading:** `H5.thread_reason_kept` is **true** with `thread_reason_reason`
`null` — the pager row carries its one-program-thread reason *alongside* the env
caveat, so the control added a reason rather than silencing one.

**H6 — PASS, and the count is exact.** `H6.headline` = **4** of 4 pairs whose
licence word equals arm A's for the same row, `H6.word_moved` **empty** — three
granted and the pager row WITHHELD, matching arm A row for row.
`H6.session_names` = `['CLAUDE_CODE_SESSION_ID', 'TERM_SESSION_ID']` = the pin ∪
`pins.injected_session_key`, and `H6.session_k` = **2**, exactly one greater, on
4 of 4. **Second reading:** `H6.injected_key` is `TERM_SESSION_ID`, and
`H6.injected_key_choice` shows it *derived* rather than picked — the first of
session set 1's fourteen exact names absent from both sides, skipping
`DBUS_SESSION_BUS_ADDRESS` and `XDG_SESSION_ID`, present on both.

**H7 — PASS, and it is the instrument's own row.** `H7.headline` = **0** null
partition cells on a pair whose licence printed, over n **69** — every pair of
every arm, not only the 61; `H7.counts_carry_their_source_line` is **true** over
69 with `counts_without_a_source_line` empty; `H7.licence_verified_counts` is
**non-null** — source 61, environment 61 and exit 61 verified, output 61 and
children 61 UNVERIFIABLE by construction, over n 61, in kind and never summed;
and `H7.version_probe` is the token **`0.8.5`** with `version_probe_ok` true and
`version_probe_reason` `null`, never an empty string (E4′ gaps 2 and 7, closed
on this row). `H7.dropped_lists` is empty and so is `reported.dropped_lists`:
**no cell this run wrote carries a dropped reason**, so no endpoint is nulled
and none was read at a ceiling.

**H8 — STOP, and both readings are printed because they disagree.** Three of the
gate's four things held. `H8.corpus_rc` = **0** over `H8.corpus_cases` = **63**
cases, `corpus_failures`, `corpus_errors` and `corpus_skipped` all **empty**
under `H8.corpus_args` = `['--require-driver']` — the flag that turns a skipped
case into exit 1, so a green summary here is green over cases that ran through
the built driver. `H8.pytest_rc` = **0** (`H8.pytest_summary`: `2256 passed, 4
skipped in 128.70s (0:02:08)`) and `H8.cargo_rc` = **0** over 42 `test result:
ok.` lines. The fourth is `H8.spawned_test_fn_present` = **False**, and §1.4's
row names it, so the row is a **STOP** by its own words.

**What the False is, as evidence.** The case is present and it ran.
`raw_h8.case_listing.names` holds **63** names and one of them is
**`rust/refocus_spawned_test_fn`** — 43 of the 63 carry a `rust/` prefix, which
is how the collector names a Rust case — while `H8.spawned_test_fn`, the value
the reader looked for, is the **bare** `refocus_spawned_test_fn`.
`H8.spawned_test_fn_skipped` and `corpus_skipped` are both empty under
`--require-driver`, so the case was collected, run and equal. The cell is a
name-shape miss in this record's reader, not a case missing from the corpus —
but it is a **measured `False`**, and a record does not reinterpret one of its
own cells into a PASS after the fact.

**The label disagrees with the evidence**, and both stand: `stop` and the marker
read *"This is a STOP of the subject"* while the miss is the instrument's —
findings gap 2 carries it, and neither reading is resolved silently in favour of
the friendlier one.

### The ungated readings, §1.5's list

| what | measured | field |
|---|---|---|
| the two rt hashes | original `d9ce385a08c6646b`, re-run `45773c80095d5b87`, **differing on 61 of 61** | `reported.rt_hashes` |
| `driver_version` | **`cargo-sensorium 0.5.2`** on **69 of 69** rows, from the re-run trace's own `meta.driver_version`, and from the built driver, sha256 `4b18cad4844cb288b0db47a2fab648f6b041f5df566806c828b9d203adfabcb1`. The originals' **`0.5.0`** is §1.1's pre-registered fact carried from E4 — **no field of this record reads it** (§5) | `reported.driver_version`, `pairs.rows[*].driver_version_from_the_trace` |
| K and its names | pin `['CLAUDE_CODE_SESSION_ID']`, n **1**, `as_expected` true; injected `TERM_SESSION_ID`. A differing set is reported, never a STOP — the launch shell is the instrument's | `reported.session_set` |
| wall per arm | A first **8.375 s**, later mean **6.667 s**, max **7.514 s** over 61; B **3.35 / 3.38 / 3.4 s** over 4; C **3.363 / 3.448 / 3.641 s** over 4. The runner writes no total and this record quotes none. §1.5 also names the dry run's wall and the driver build's *separately*, and `walls_s` holds A/B/C alone: the build's is `pins.built_from.cargo_wall_s` **0.025 s** (`rebuilt: no`), cargo's own time inside each refocus is `raw_pass2.refocuses[*].cargo_finished_s`, and the dry run's stayed in its own archived results — read, not gathered where §1.5 points (findings gap 5) | `reported.walls_s`, `pins.built_from` |
| arm B's verdicts | **all four MATCH**. `E4PP_INPUT` is a name no code in the clone reads, so a moved verdict would have been a finding; none moved, reported as the reading it is | `reported.arm_b_verdicts` |
| the loop was whole, wrote nothing and dropped nothing | **69** invocations — A **61**, `armB` **4**, `armC` **4** — none killed, none skipped by the bound; **no** measurement cell carries a dropped reason; the kept store 122 files before and after, `differences` empty, `identical` **true** | `pairs.n`, `pairs.by_arm`, `reported.dropped_lists`, `H7.dropped_lists`, `reported.kept_store_unchanged` |

**The record's own reading of itself.** Seven endpoints of eight answered
exactly as pre-registered, including both the slice exists to answer; the eighth
is a miss in the reader, on a cell whose subject was green — the STOP real, the
finding the instrument's, and neither cancelling the other.

## 5. Gaps

### The ruling on this measurement (controller, 2026-09-08)

**The STOP STANDS as measured.** H8 is not re-rolled and no instrument change is
made after the measurement to make the cell come out differently — §1.4's kill
6, and E4′'s own precedent on the day its H1 STOPPED. The reader is wrong and
the record says so; a record does not become right by editing the reader that
wrote it. **The finding is the slice's result**, and the fix is ruled for the
NEXT slice, never applied here. H1 and H2 — the two endpoints this slice exists
for — PASS at n = 61; what missed is a cell of the row that watches the rest of
the workspace.

### Gaps, in a sibling so this record stays under its ceiling

The five instrument gaps with their one-line fixes, what this record does
**not** license (blind spot 28's mechanism included), and the three E4′ gaps
closed with their cells —
[`…-e4pp-findings.md`](2026-09-08-sensorium-rung4-e4pp-findings.md); the ungated
per-row readings — [`…-e4pp-rows-measured.md`](2026-09-08-sensorium-rung4-e4pp-rows-measured.md).

### What no `dropped` list says

`reported.dropped_lists` and `H7.dropped_lists` are empty and no cell carries a
`dropped` reason: the loop ran whole (69 of 69, none killed, none skipped, no
ceiling reached) and `H7.headline` counts **0** null partition cells over 69.
`H8.spawned_test_fn_present` is a **measured `False`**, not a missing one.

### Not in this record

E4 and E4′ are not re-opened and no number in either is re-measured; pass 1 was
not re-run, so nothing here claims anything about a fresh recording; the four
verified/unverifiable counts stay in kind and unsummed; nothing is gated on a
wall; §1 is never edited here.
