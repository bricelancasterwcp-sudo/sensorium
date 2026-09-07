# Rung-4 acceptance, the harness thread and the licence word — E4′ (H1–H6)

The record of whether the harness-thread rule of the rung-4 debts slice changes
the word `sensorium refocus` prints beside a Rust pair's verdict, and changes
nothing else — measured by re-running the same 61 `#[test]` functions E4
measured, from E4's own originals, under the repaired rule.

**The pre-registration this record measures** is §8 of the binding design
(`docs/superpowers/specs/2026-09-07-sensorium-rung4-debts-design.md`), whose
ruling R1 (§0, §2) is the thing under test:

> a non-main thread whose ROOT frame's site is a `#[test]`-marked fn is the
> **harness thread** (libtest's per-test thread); the licence excludes harness
> threads from its untraced-thread counts and names them; Python only

**What this record repairs, and where the debt was written.** E4 measured
`licences granted` = **0** on all 61 pairs and published the reason in its
§5.2: the untraced-thread clause fires on every `cargo test` trace because
libtest runs each test on a spawned thread. E4's own measured counts are the
subject of this record's prediction — **57** of the 61 pairs reported **1**
extra thread on each side, `a_pager_can_be_shared_across_threads` reported
**2**, and the **three** `pager_refusal_advice_test` server tests reported
**5** (E4 §5.2; the raw field is named in §1.2). E4 named the candidate fix and
deliberately did not apply it, calling it a ruling's to make. The ruling is
R1. This record measures what R1 does to those 61 pairs.

**E4 is not re-opened and no number in it is re-measured.** E4 stands exactly
as written — its 61 of 61 MATCH, its four H4 counts, its cost table, its
§5.2 through §5.7. This is a NEW pre-registration in a NEW document, measured
once, on the same subject under a changed rule, which is what E4's §5.6 said a
corrected endpoint requires.

**§1 is byte-locked, and it is committed ALONE.** It is committed before
`harness_threads` exists in `refocus_world.py`, before `find_pair` excludes a
child, before `install_shim` hard-links, before any results file carries
`schema_version`, and before `rust/tests/acceptance_e4p.py` exists — so no
value below was chosen after seeing an instrument behave. The lock is
`awk '/^## 1/,/^## 2/' | sha256sum`; the runner refuses to start unless the
range is byte-identical to the commit that locked it, and refuses outright
while no lock sha is set. §1 references no footnote, so the extended lock
range and the `awk` range are the same bytes.

**A completed measurement is never re-rolled, and a miss is a STOP with its
number.** Measured once.

## 1. Pre-registration

**The argv form, verbatim — pass 2 only.** This record does not re-record
anything. Pass 1 already happened: it is E4's, its 61 originals are kept, and
§1.3 copies them rather than re-running them. The only invocation this record
makes against the subject is:

| pass | argv |
|---|---|
| 1 | *(not run — E4's originals are the subject, copied per §1.3)* |
| 2 | `sensorium refocus <run> --focus <name>` |

`<run>` is the original run id of §1.1's row and `<name>` is that row's test
function, the bare qualname, which is the same `--focus` value E4 used and is
unique workspace-wide (E4 §1.1). The CLI re-invokes the driver itself:
`sensorium refocus` builds `[driver, "--refocus-of", <run>, "--focus", <name>,
*cargo_args]` and runs it from `workspace_root` under the fresh store (slice-2
design §2.3). Nothing parsed from the driver's stdout is load-bearing; the
pair is found by `refocus_of` in the store. Because pass 1 is not re-run, the
originals' bytes are E4's exactly, and any difference this record reads is
attributable to the reader and the driver, never to a fresh recording.

**Each refocus rebuilds the matched unit under its focus**, as E4's pass 2
did: 61 rebuilds against a FRESH `CARGO_TARGET_DIR` (§1.4), which is what
makes H4's shim census have 61 focused keys to count.

| id | question | endpoint (both readings pre-committed) |
|---|---|---|
| H1 | does the harness rule change the licence word as predicted? | **Gate:** `granted` = **57** and WITHHELD = **exactly the four named in §1.2**, by name, no other partition → **PASS**. Any other partition — a different count, a different set, or a granted line among the four — is a **STOP**: the rule or the `test`-mark lookup it reads is wrong, and the partition observed is the finding. Second reading, **REPORTED**: each of the four WITHHELD reasons names the program's own thread count *and* states the harness thread was excluded, and each of the 57 granted pairs' thread line carries the harness phrase of design §2; a WITHHELD whose reason does not name the exclusion, or a granted line that hides it, is a finding reported as one. |
| H2 | is the verdict untouched? | **Gate:** **MATCH 61 of 61** → **PASS**. The comparator is not changed by this slice, so any non-MATCH — DIVERGED or REFUSED, on any pair — is a **STOP**, with the pair's run ids and its divergent event recorded. Second reading: the printed verdict word and the exit `refocus` returns (MATCH 0 / DIVERGED 1 / REFUSED 3) agree on all 61; a disagreement between word and exit is itself a finding and is reported as one, never resolved in favour of either. |
| H3 | is the pair found? | **Gate:** **61 of 61 pairs of exactly one** → **PASS**. A pair count ≠ 1 on any original — zero, or more than one — is a **STOP**: the instrument or the pairing, not the subject. Second reading, **REPORTED**: the `child runs excluded from the pair` list (R2) is **empty on all 61** — E4 §1.1's greps found `Command::new` 0 hits over the seven files and `tests/common/*.rs`, so none of the 61 spawns a process and R2's exclusion has nothing to exclude here; a non-empty list is a finding, reported with the excluded ids. |
| H4 | does the shim link? | **Gate:** **61 focused keys**, and for every key the `st_ino` of its `cargo-sensorium` equals the driver's `st_ino` → **PASS**. A distinct inode where a link was possible — same `st_dev` as the driver, so the fallback was not forced by a filesystem boundary — is a **finding**, not a STOP, recorded with the count. Second reading, **REPORTED**: total bytes under the census path counted **once per inode**, beside the count of distinct inodes and the count of entries; the two numbers are printed separately and the byte total is never the sum of the per-entry sizes. |
| H5 | is `schema_version` present? | **Gate:** the E4′ raw record and the E4′ assembled record both carry `schema_version` = `e4p/1` → **PASS**; absent from either, or a different value, is a STOP of the instrument (not of the subject) under kill 4. Second reading, **REPORTED**: on a **dry assemble** — an assemble that writes nothing — the E9 and E4 renderers print their own `schema_version` fields (`e9/1`, `e4/1`); their committed `results.json` files are **not** re-derived and are not expected to carry the field (design §5's R-F15/R-G15 precedent), and that they predate it is stated, never repaired. |
| H6 | did nothing else move? | **Gate:** every corpus case equal, the new `refocus_child_run` case included; the whole Python suite green; `cargo test --workspace` green → **PASS**. Second reading: per-case equality of printed answers, and beside it each suite's exit status and its pass/skip counts. This runs against this repository, never the clone. |

### 1.1 The 61 originals — name, file, run id, in E4's order

The rows are E4's §1.1 enumeration in E4's order, each carrying the run id
E4's pass 1 produced for it, read from the E4 raw record's
`raw_pass1.runs[*]` (`index`, `name`, `target`, `run`; the lens row *E4 raw
record* names the file). The seven counts are 20 / 15 / 4 / 4 / 8 / 4 / 6 =
**61**, which is E4 §1.1's partition unchanged. All 61 run ids are distinct,
and every one names an existing `<run>.db` under the kept store (§1.4) —
checked when this section was written, before any instrument existed, and
re-checked by the runner before the loop opens; a missing or duplicated
original is a refusal to start, not a smaller N.

| # | fn (the `--focus` value) | file | original run id |
|---|---|---|---|
| 1 | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | `pager_codec_gate_test.rs` | `20260907-111144-33d30c` |
| 2 | `unknown_model_mutating_verbs_is_false` | `pager_codec_gate_test.rs` | `20260907-111145-e2c8e3` |
| 3 | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | `pager_codec_gate_test.rs` | `20260907-111146-8497d7` |
| 4 | `stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement` | `pager_codec_gate_test.rs` | `20260907-111147-b2146f` |
| 5 | `set_codec_gate_on_unknown_model_is_named` | `pager_codec_gate_test.rs` | `20260907-111148-085b7a` |
| 6 | `model_patch_codec_follows_the_attached_profiles_selection` | `pager_codec_gate_test.rs` | `20260907-111149-82548c` |
| 7 | `model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown` | `pager_codec_gate_test.rs` | `20260907-111150-ab143a` |
| 8 | `model_codec_from_profile_separates_a_measured_selection_from_the_default` | `pager_codec_gate_test.rs` | `20260907-111151-71f89b` |
| 9 | `agent_task_policy_resolves_through_the_agents_model` | `pager_codec_gate_test.rs` | `20260907-111152-b19140` |
| 10 | `agent_task_policy_is_none_for_an_unknown_agent` | `pager_codec_gate_test.rs` | `20260907-111153-2fe948` |
| 11 | `agent_task_policy_resolves_envelope_through_the_agents_model` | `pager_codec_gate_test.rs` | `20260907-111154-de3ee9` |
| 12 | `journal_codec_fixture_round_trips_through_replay` | `pager_codec_gate_test.rs` | `20260907-111155-67ca55` |
| 13 | `journal_codec_fixture_round_trips_a_refuse_class_row` | `pager_codec_gate_test.rs` | `20260907-111156-d0c398` |
| 14 | `unmeasured_model_has_null_done_trust_and_null_refusal_gate` | `pager_codec_gate_test.rs` | `20260907-111157-3a93a9` |
| 15 | `stored_gate_with_both_classes_clear_renders_done_trust_true` | `pager_codec_gate_test.rs` | `20260907-111159-54c3a7` |
| 16 | `stored_gate_with_one_class_failing_renders_done_trust_false` | `pager_codec_gate_test.rs` | `20260907-111200-990b34` |
| 17 | `set_refusal_gate_never_touches_mutating_verbs_or_codec_gate` | `pager_codec_gate_test.rs` | `20260907-111201-ab997d` |
| 18 | `set_refusal_gate_on_unknown_model_is_named` | `pager_codec_gate_test.rs` | `20260907-111202-764f03` |
| 19 | `journal_codec_verdict_mixed_round_trips_through_replay` | `pager_codec_gate_test.rs` | `20260907-111203-8bd7b0` |
| 20 | `journal_codec_verdict_round_trips_through_replay` | `pager_codec_gate_test.rs` | `20260907-111204-4e635f` |
| 21 | `residency_refusal_is_pre_checked_and_never_touches_the_substrate` | `pager_obligation_test.rs` | `20260907-111206-be9b6d` |
| 22 | `stale_image_digest_cold_starts_and_journals_degraded` | `pager_obligation_test.rs` | `20260907-111207-7997d1` |
| 23 | `corrupt_spilled_image_cold_starts_and_journals_degraded` | `pager_obligation_test.rs` | `20260907-111208-7b34da` |
| 24 | `suspend_resume_round_trips_the_kv_image_through_nvme` | `pager_obligation_test.rs` | `20260907-111209-cf57f2` |
| 25 | `unmeasured_vram_journals_degraded_once_and_caps_residency_at_one` | `pager_obligation_test.rs` | `20260907-111210-de710a` |
| 26 | `missing_stats_is_a_contract_violation_not_a_reply` | `pager_obligation_test.rs` | `20260907-111211-ac01ef` |
| 27 | `unload_model_pages_out_holders_and_journals` | `pager_obligation_test.rs` | `20260907-111212-f190d4` |
| 28 | `image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context` | `pager_obligation_test.rs` | `20260907-111213-53bd85` |
| 29 | `a_transient_restore_failure_keeps_the_image_for_the_retry` | `pager_obligation_test.rs` | `20260907-111214-83522d` |
| 30 | `an_aborted_eviction_is_journaled_not_left_orphaned` | `pager_obligation_test.rs` | `20260907-111216-997b0b` |
| 31 | `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` | `pager_obligation_test.rs` | `20260907-111217-bfe991` |
| 32 | `a_pager_can_be_shared_across_threads` | `pager_obligation_test.rs` | `20260907-111218-b37956` |
| 33 | `unknown_model_and_unknown_agent_are_named` | `pager_obligation_test.rs` | `20260907-111219-a4ad75` |
| 34 | `agent_ids_are_unique_and_status_is_a_snapshot` | `pager_obligation_test.rs` | `20260907-111220-6d9c78` |
| 35 | `a_model_with_no_admission_block_renders_none` | `pager_obligation_test.rs` | `20260907-111221-2070ee` |
| 36 | `the_refusal_advises_a_window_that_actually_places` | `pager_refusal_advice_test.rs` | `20260907-111222-5b7e4e` |
| 37 | `the_advice_never_exceeds_the_window_the_agent_already_had` | `pager_refusal_advice_test.rs` | `20260907-111224-baa1d5` |
| 38 | `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` | `pager_refusal_advice_test.rs` | `20260907-111225-5d21ce` |
| 39 | `the_journal_records_the_advice_alongside_the_refusal_arithmetic` | `pager_refusal_advice_test.rs` | `20260907-111226-12b15f` |
| 40 | `remove_agent_destroys_context_and_forgets_the_agent` | `pager_remove_agent_test.rs` | `20260907-111227-69395c` |
| 41 | `remove_agent_on_a_fresh_agent_is_not_an_error` | `pager_remove_agent_test.rs` | `20260907-111228-1b60c3` |
| 42 | `remove_agent_on_unknown_id_is_named` | `pager_remove_agent_test.rs` | `20260907-111229-7ecc9d` |
| 43 | `remove_agent_journals_the_removal_with_its_reason` | `pager_remove_agent_test.rs` | `20260907-111230-c3f27d` |
| 44 | `a_second_agents_reservation_not_just_its_kv_is_what_refuses_it` | `pager_reservation_test.rs` | `20260907-111232-be1ecb` |
| 45 | `the_global_overhead_margin_is_subtracted_from_placement_too` | `pager_reservation_test.rs` | `20260907-111233-d808f7` |
| 46 | `status_reports_reserved_bytes_and_both_overhead_terms` | `pager_reservation_test.rs` | `20260907-111234-77aca0` |
| 47 | `eviction_credits_the_whole_reservation_back` | `pager_reservation_test.rs` | `20260907-111235-5c41c0` |
| 48 | `a_vram_bound_window_is_placeable_item_7_regression` | `pager_reservation_test.rs` | `20260907-111236-78e563` |
| 49 | `a_sibling_blind_automatic_window_still_refuses_item_7_third_half` | `pager_reservation_test.rs` | `20260907-111237-889ce6` |
| 50 | `recurrent_state_is_charged_per_context_and_reported` | `pager_reservation_test.rs` | `20260907-111238-841017` |
| 51 | `recurrent_state_binds_the_vram_term_of_the_window_law` | `pager_reservation_test.rs` | `20260907-111240-16e1f6` |
| 52 | `eviction_under_pressure_saves_image_and_journals` | `pager_test.rs` | `20260907-111241-232c32` |
| 53 | `the_eviction_story_is_journaled_in_order_with_a_faithful_prompt` | `pager_test.rs` | `20260907-111242-246517` |
| 54 | `oversized_prompt_is_refused_with_arithmetic_never_truncated` | `pager_test.rs` | `20260907-111243-a3b48c` |
| 55 | `budget_exhaustion_refuses_before_the_call` | `pager_test.rs` | `20260907-111244-e71496` |
| 56 | `loading_a_model_charges_its_weights_against_the_budget` | `pager_weights_test.rs` | `20260907-111246-2e13b3` |
| 57 | `a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic` | `pager_weights_test.rs` | `20260907-111247-da8d66` |
| 58 | `unload_credits_the_weights_back` | `pager_weights_test.rs` | `20260907-111248-87cf0b` |
| 59 | `status_reports_loaded_weights` | `pager_weights_test.rs` | `20260907-111249-6b0bff` |
| 60 | `unmeasured_budget_refusal_detail_says_unmeasured_not_zero` | `pager_weights_test.rs` | `20260907-111250-092953` |
| 61 | `a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics` | `pager_weights_test.rs` | `20260907-111251-80be5a` |

**N stays 61 and nothing is excluded.** E4 §1.1 recorded `#[ignore]` 0 hits
and `#[should_panic]` 0 hits over the seven files, so no name above is skipped
by libtest and none is skipped here. This record adds no test and drops none:
the subject is E4's subject, and a row that could not be measured would be
published as a null with its reason rather than dropped from N.

### 1.2 The expected licence partition, written first

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

**The shim census expectation.** 61 focused keys under the census path, each
`cargo-sensorium` sharing the driver's inode, bytes counted once. On this box
the driver and the target sit on one filesystem, so the fallback-to-copy path
of R3 is not expected to be taken; if `st_dev` differs at measurement time,
§2 records it and H4's finding branch does not apply.

### 1.3 The fresh store — how the 61 originals get there

**The kept store is never written.** The 61 originals live in E4's kept store
(§1.4, `<kept>`), which holds 122 `.db` files — E4's 61 originals and its 61
refocused traces. This record reads them and copies each into a FRESH store
`<fresh>`; it never opens `<kept>` for writing, never runs the reader against
it, and never lets a refocus point at it.

**The copy, verbatim.** For each of §1.1's 61 run ids:

```
sqlite3 <kept>/traces/<run>.db "VACUUM INTO '<fresh>/traces/<run>.db'"
```

`VACUUM INTO` writes a checkpointed single-file copy: any WAL content is
folded into the destination, the destination is a complete database on its
own, and the source is opened read-only for the operation. The **statement is
what is pre-registered**; its executor is either the `sqlite3` CLI, when one
is on `PATH`, or Python's `sqlite3` module executing the identical SQL — §2
records which was used and the SQLite library version, because they are lens
facts and neither changes the bytes the statement produces.

**Proof the kept store was not written**: the `st_mtime` (and size) of every
one of `<kept>`'s `.db` files is recorded **before and after** the whole run,
and §2 states that the two lists are identical; a single changed mtime is a
STOP under kill 4 and is reported as one.

**Proof each copy is the original it claims to be**: after each copy, the
destination's `meta.run_id` is read and must equal `<run>`; a mismatch is a
refusal to start (before any number, so kill 3), never a silently renamed
file. The copies are made **before the loop opens**, and `<fresh>` holds
**only those 61 files** and nothing else at that moment — no refocused trace,
no earlier run, no leftover — which §2 records as a listing count.

**The target and the driver.** `CARGO_TARGET_DIR` is FRESH and empty at the
start (§1.4): each of the 61 refocuses rebuilds the matched unit under its own
focus, exactly as E4's pass 2 did, so the 61 rebuilds are real and H4 has 61
distinct focused keys to census. The driver is `cargo-sensorium` **built by
the runner from this branch's HEAD at measurement time**, with the commit, the
`built_from` result and the binary's sha256 recorded in §2 before and after —
the pre-repair-binary trap of the E6⁗ record is why the runner builds it
rather than trusting a path.

### 1.4 Lens, and the kill criteria

**Lens for every endpoint.** The reader is this repository's `.venv` Python
running `python -m sensorium` at the branch HEAD §2 records, and the rules it
reads by are the designs', not this document's: the verdict under slice-2
design §3.1 (per-task fingerprints over CALL, RETURN, RAISE and HANDLED; LINE
rows never enter the hash), the licence under slice-2 §3.2 **as amended by
this slice's §2 (R1)**, the pair under this slice's §3 (R2), the shim under §4
(R3), and every refusal sentence under slice-2 §2.3.

**Locations — the only box-local paths this record names.** Every path below
is either FRESH for this run or READ-ONLY for its whole duration; no other
absolute path appears anywhere in this record.

| what | value |
|---|---|
| trace store `<fresh>` — FRESH, holding only the 61 copies when the loop opens | `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e4p` |
| cargo target for the 61 refocuses — FRESH and empty at the start | `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/bloomery-target-e4p` |
| H6's corpus target — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e4p-corpus` |
| the kept E4 store `<kept>` — READ-ONLY, source of the 61 copies (122 `.db`) | `/mnt/extra/sensorium-rung2/sensorium-dir/e4` |
| the E4 raw record — READ-ONLY, source of §1.1's rows and §1.2's counts | `/mnt/extra/sensorium-rung2/sdd-archive/2026-09-07-sensorium-rung4-refocus/results-e4-raw.json` |
| the clone under measurement — READ-ONLY | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| the shim census | `<CARGO_TARGET_DIR>/sensorium/shim/*/cargo-sensorium` — entries, distinct inodes, and bytes once per inode, measured once at the end |

**The clone is read-only for the whole run**, and each refocus rebuilds inside
it: its HEAD, its porcelain and its `Cargo.lock` sha256 are recorded **before
and after**, and the lock is restored to the pin if a `cargo` invocation moved
it — §2 says whether it did and that it was restored. The runner never writes
into the clone by any other means, and every refocus runs with cwd = the
clone's workspace root, which is what `workspace_root` records and what the
re-run rule uses.

**`SENSORIUM_TIER` is not set by this record.** Each refocus replays the tier
recorded on its own original: E4's pass 1 ran with `SENSORIUM_TIER` unset, so
the flag is omitted and the driver's default `call` applies again. The focus
tier is a compile-time decision, so an original and its refocused pair still
differ only by the added `--focus`.

**The invocation audit log is NOT silenced**: `SENSORIUM_NO_INVOCATION_LOG` is
unset, so every reader invocation this record makes is itself logged into
`<fresh>`, and §2 records the row count at the end. The 61 copied originals
carry no such rows from E4, so the count is this record's own.

**`TMPDIR` is observed, with E4's reading.** With `TMPDIR` unset,
`std::env::temp_dir()` is `/tmp` and the clone's `fresh_dir` names are
`<temp_dir>/<fixed name>`. No endpoint in this record is derived from a
temporary path — there is no `watch` triple here — so `TMPDIR` binds nothing;
it is recorded in §2 as observed because it is part of the environment the
licence compares, and if it is set at measurement time §2 states so and states
that no prediction moved on it.

**Versions, and the rule for reading a version token.** The slice puts
`cargo-sensorium` at **0.5.1**, `sensorium-transform` at **0.4.2**,
`sensorium-rt` at **0.4.0** (unchanged) and Python `sensorium` at **0.8.5**
(**0.8.4** if the Python bump has not landed when the run happens — §2 records
which). Those are expectations, not gates. **Every version token that appears
inside a sentence this record checks is read from the trace's own
`meta.recorder` and from the driver's recorded version, never hard-coded
here**, and §2 records what each actually was; a sentence is compared with
§2's recorded token substituted. E4 §5.5 recorded that the installed
distribution metadata in this `.venv` is stale (`0.6.0`); §2 records both the
metadata token and the tree's, and states plainly that they differ if they do.

**The reading rule for the licence lines.** Source, environment and exit run
for real and are counted as verified or not verified. **Output and children
are UNVERIFIABLE by construction** on a Rust pair — `capabilities.output` and
`capabilities.children` are false, so there is nothing to compare — and are
**reported, never counted as verified** and never summed into a verified
total. A licence line that said "verified" for either would be the named bug
class and would be reported as a finding, not as a pass. **The thread line is
read the same way**: a harness thread that R1 excludes is *named* in the line
under the phrase design §2 fixes, never silently dropped, and a granted
licence whose line omits the excluded harness thread is H1's second-reading
finding even when the word is the predicted one.

**The pair rule.** A verdict is read only from a pair the store itself
identifies: exactly **one** trace whose `refocus_of == <run>`, whose recording
started **after** that invocation's launch timestamp, and which R2 has not
excluded as a child of another candidate. Zero or more than one is a REFUSED
by count, never a guess, and — per H3 — that is a STOP. The driver's `run:`
lines are recorded in the report and decide nothing.

**Every row above carries both its readings**, pre-committed here; where a
row's two readings disagree the disagreement is the finding and is reported as
one, never resolved silently in favour of the friendlier number. **Every
measurement is `{value, n, lens, dropped}`**: a `null` value with a reason is
the only not-measured, `0` is measured-and-zero, and no endpoint is ever
filled from an expectation — the predictions above are in the room, and a
headline that borrowed from one could not fail. Loads at every phase's start
are recorded. Nothing is gated on a wall.

**Kill criteria.**

1. **A partition other than §1.2's is a STOP** (H1): not 57 granted, or a
   WITHHELD set other than the four named there. The rule or its `test`-mark
   lookup is wrong, and the partition observed is the finding — not a retry
   under a narrower rule, not a re-run with the lookup adjusted.
2. **Any non-MATCH is a STOP** (H2): the comparator is not touched by this
   slice, so a DIVERGED or a REFUSED on any pair means something moved that
   this slice did not intend to move. Recorded with the pair's run ids.
3. **A pair count ≠ 1 is a STOP** (H3): the instrument or the pairing, not the
   subject.
4. **A `.FAILED` marker before any number has been read is infrastructure.**
   The run is archived, the fresh locations are emptied, **the 61 copies are
   re-made from `<kept>` by §1.3's statement**, and it is relaunched from
   zero.
5. **A `.FAILED` marker after any number has been read is a STOP.** The
   numbers already read stand.
6. **Measured once.** No endpoint is re-rolled and no completed measurement is
   re-run under a kinder command. A miss is recorded with its number.
7. **A reader at its ceiling is the record.** Where a reader's own limit
   (a page, a cap, a truncation) bounds what an endpoint can see, that is
   published as the endpoint's lens and the cell goes null with its reason
   rather than being filled from a smaller view.

**Bounds.** The loop runs detached (`setsid nohup`) with a pid file and a
`.DONE`/`.FAILED` marker carrying `exit=<n>`; nothing below is read before the
marker exists. **The whole loop is bounded at 1 h 15 min** and **each
`sensorium refocus` invocation at 1800 s**. A bound reached is a `.FAILED` and
is read under rules 4 and 5 above. E4 measured a flat ~7 s per refocus over
the same 61 and closed its pass-2 half well inside its own bound; the bound
here is that measurement's shape with room for the added rebuilds, and it is
not an expectation — nothing is gated on a wall.

**Reported without a gate**: H1's second reading (the wording of all 61
licence lines); H4's byte total, entry count and distinct-inode count; H5's
dry-assemble tokens; the per-refocus walls with the first focus distinguished
from the later ones and cargo's own build time inside each; the copied and
refocused trace sizes; the store's size and the disk free before and after;
the invocation-log row count; and the four verified/unverifiable licence
counts carried over from E4's H4 in kind.

## 2. Environment

*(written by Task 6)*

## 3. Results

*(written by Task 6)*

## 4. Verdicts

*(written by Task 6)*

## 5. Gaps

*(written by Task 6)*
