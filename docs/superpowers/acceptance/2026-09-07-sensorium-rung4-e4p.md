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

### 1.5 Amendment A1 — dated 2026-09-07, before any E4′ number was read

**Found in preflight (Task 5's dry run and the controller's scan of the
61 originals' recorded environments), not in the measurement.** The
licence's ENV clause compares the original's recorded environment with the
re-run's, excluding only the recorder's own keys and shell bookkeeping.
§1.3 mandates a FRESH `CARGO_TARGET_DIR` for the re-run (H4's inode census
needs it), and four variables embed the target root — `CARGO_TARGET_DIR`,
`CARGO_BIN_EXE_*`, `LD_LIBRARY_PATH`, `RUSTDOCFLAGS` — so under the
instrument as pre-registered the env caveat fires on all 61 pairs and the
licence is WITHHELD on all 61 for a reason unrelated to R1: kill 5 (STOP)
on H1 with nothing learned. E4 read `env: unchanged` on every pair only
because both of its passes shared one target directory and one launcher
process; §1.2's prediction was derived from E4's thread counts alone.

**Ruling (design authority).** A re-run from another target directory is a
normal use of the tool; the env clause must not read the target root's
relocation as a change the world made — and must not blanket-exclude those
keys either. Source change at `1a76757` (+ `d43b7aa`): values that
differ ONLY by substituting the recorded `CARGO_TARGET_DIR` root for the
current one, entry by entry and anchored at path boundaries, are
normalised and NAMED on the env line (`N variable(s) differ only by the
target directory: …; treated as unchanged`); any other difference,
addition or removal still fires. Rejected: running as pre-registered
(burns the hour to demonstrate a known instrument confound); re-running
under the kept E4 target (mutates a kept artifact; muddles H4).

**Launch environment.** Outside the cargo/rust/loader/recorder keys, the
61 originals' recorded environments differ from this session's process
environment in exactly three variables: `PYTHONDONTWRITEBYTECODE` (the
launcher already sets it, as E4's did), `SSL_CERT_DIR` and `SSL_CERT_FILE`
(present at E4's launch, absent in this session's shell). The E4′ launcher
pins the latter two to the originals' recorded values (the system
certificate paths — not session identity, which is identical because E4
ran from this same session). The runner's preflight compares its own
process environment with every original's recorded one under the same
exclusions and REFUSES to launch on any difference; the check is recorded
(instrument commit `10e2712`, `pins.env_parity`).

**Carried, not built (ruled).** The clause still withholds on any re-run
launched from another shell, because session-identity variables differ
there. The design decided: a named, versioned positive set of
build-and-run-bearing variables (`PATH`, `HOME`, `USER`, `LOGNAME`,
`LANG`, `LC_*`, `TZ`, `TMPDIR`, `CARGO*`, `RUST*`, `LD_*`, `DYLD_*`,
`SSL_CERT_*`, `PYTHON*`, `DEBUGINFOD_URLS`) withholds; every other
differing key is counted and named but does not. Not built before this
measurement (fewer source changes before a measurement is the rule; it is
not needed for E4′). CARRIED-DEBT.

**What changes in §1.** Nothing in §1.1, in §1.2's expected partition
(57 granted / the four withheld by name / harness 1 on every pair), in the
H-table, or in the kill sentences. The lens gains two rows: the env line's
reading rule (the relocated keys are read from the printed list and
recorded per pair; a pair whose env line names ANY other differing key is a
caveat as before) and the launcher's two pinned certificate variables.

**Locks.** §1 sha before this amendment:
`82152208e2fa57f54c573dea8305be28097529fd2544e2be5caabd16e6bf3528`
(commit 2991c3b). §1 sha after this amendment: the amendment cannot carry its own
hash; it is recorded in §2 (by Task 6), in the ledger, and in this
commit's message. Both shas travel together from here.

## 2. Environment

Measured **`2026-09-07T19:19:00-05:00`** (= `2026-09-08T00:19:00Z`) →
**`19:29:37-05:00`** by `rust/tests/acceptance_e4p.py`, launched detached
through `acceptance-e4p/launch.sh`; the raw facts are `results-e4p-raw.json` in
the gitignored plan ledger, every command's log beside it. §3 and §4 are read
from `2026-09-07-sensorium-rung4-e4p.results.json`, which
`acceptance_e4p_schema.assemble_e4p` derived from it, and from the raw file
where the assembly carries no field.

**The wall is 637 s, derived here.** The runner writes **no total wall** — only
the driver build's, the 61 per-refocus, the per-copy and H6's three — so 637 s
is `finished − started` (`19:29:37 − 19:19:00`), computed in this sentence and
nowhere else; the four measured phases sum to 634.7 s beside it (415.2 + 64.883
+ 141.911 + 12.671). **Erratum:** the commit body of `f653567` says "601 s",
which traces to no artefact and is wrong by 36 s. A commit message on a shared
branch is immutable; this record corrects it.

**Schema.** This record is `e4p/1`: the raw record and this assembly were
written under the same schema version (H5).

**The run ended in a STOP.** `e4p.FAILED` carries `exit=7` and `numbers_read:
true` — set 19:19:09, nine seconds in, when row 1 came back with a verdict and
a licence. Under §1.4's rule 5 **by its words** that is a STOP: the numbers
read stand and nothing is re-rolled.

**§1 byte-lock, both locks.** The runner refuses to start unless the locked
range is byte-identical to the commit that locked it, and refuses outright with
no lock sha set. The range is `awk '/^## 1/,/^## 2/'` plus every footnote §1
references — `footnotes_in_range` is empty, so the two are the same bytes.

| lock | commit | bytes | sha256 |
|---|---|---|---|
| ORIGINAL — §1 as Task 0 committed it alone | `2991c3b` | 27 880 | `82152208e2fa57f54c573dea8305be28097529fd2544e2be5caabd16e6bf3528` |
| CURRENT — §1 as amendment A1 left it, what the run refused on | `d5efaab` | 31 724 | `04aa4b6b0cdf20ee67f21b7e5741819f3e324d150dc2bd1b3969b68b7a3e3967` |

Checked at `d5efaab`: identical on both sides — **yes**.
`amended_after_the_original_lock` = **true**, `amendment_bytes` = **+3 844**
(§1.5 alone; every `|` row of §1.1, §1.2 and the H-table is byte-identical at
the two commits, asserted by `tests/test_acceptance_e4p.py`).

**ERRATUM — §1's kill cross-references read one low.** Three sentences cite an
index their own words do not match, and **the words bind**:

| §1 line | the citation | what the words say | what the runner did |
|---|---|---|---|
| 78 (H5) | "a STOP … under kill 4" | a **STOP** — rule 5 | implements STOP |
| 248 (§1.3, a changed mtime) | "a STOP under kill 4" | a **STOP** — rule 5 | implements STOP |
| 252 (§1.3, a run-id mismatch) | "a refusal to start (before any number, so kill 3)" | **before any number** — rule 4, infrastructure | raises `Refused` before any copy |

The marker's headline reads **"H1 (kill 1)"**, and kill 1 — *a partition other
than §1.2's is a STOP* — IS the rule that fired, so that label is right by its
words even where §1's numbering elsewhere is not. §1 is never edited; the
erratum is filed here.

### The lens

| what | value |
|---|---|
| repo HEAD at the run | `8954d3a6a84e9267100f9e4cf38f07c6bf54e593` (branch `feat/rung4-debts`, porcelain empty before) |
| the clone under measurement (READ-ONLY) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` = §1.4's pin; porcelain empty before **and** after; HEAD unmoved |
| the clone's `Cargo.lock` | `c089018581c9bd62a0…` before and after — **moved: no**, back on the pin: yes |
| the KEPT E4 store (READ-ONLY input) | `/mnt/extra/sensorium-rung2/sensorium-dir/e4`, 122 `.db` |
| the FRESH trace store | `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e4p` — 61 copies when the loop opened, 122 `.db` at the end (61 originals + 61 re-runs); invocation log **not** silenced, **61** rows, this record's own |
| the FRESH cargo target | `SENSORIUM_E4P_TARGET=/mnt/extra/sensorium-rung2/bloomery-target-e4p`, 25 093 453 279 B after; H6's corpus target `…-e4p-corpus` (derived, not from an env var), 777 274 277 B |
| the driver | `…/rust-target/debug/cargo-sensorium`, sha256 `f8b3a0f32bd0fe1efc7d417faa004e5b900fa55dcd2693912d6180eebfa5e85a`, built by this run from HEAD `8954d3a` (`rebuilt: false` — already current), **unchanged after the run**. Its version token `cargo-sensorium 0.5.1` is read from **`meta.driver_version` of the trace** on **61 of 61** re-runs, never from the instrument |
| the other two versions | `sensorium-transform` `0.4.2`, **source `rust/Cargo.lock`** — not observed from the run, being carried neither in the trace nor by the driver binary. Python `sensorium`: tree token **not recorded** (empty — §5 gap 2); installed metadata `0.6.0`, the stale value E4 §5.5 already found |
| the copy | §1.3's statement `VACUUM INTO '<dst>'`, executed by the **Python `sqlite3` module** (no `sqlite3` CLI on `PATH`), SQLite **3.46.1** |
| the two preflight guards | environment parity with the 61 originals: **61 of 61 checked, none differ**, over 77 compared keys, excluding `^(CARGO\|RUST\|SENSORIUM\|LD_)` and `_`, `OLDPWD`, `PWD`, `SHLVL`. No other `cargo` was running: `pgrep -x cargo` → rc **1**, pids `[]` |
| `TMPDIR` | unset; `tempfile.gettempdir()` resolved to `/tmp`. No endpoint here is derived from a temporary path — there is no `watch` triple in this record — so it binds nothing |
| `SENSORIUM_TIER` | not set by this record; each refocus replays its original's tier (E4's pass 1 ran unset, so the driver's default `call` applied again). Toolchain: rustc 1.96.0 (ac68faa20 2026-05-25), cargo 1.96.0 (30a34c682 2026-05-25), Python 3.14.4 |
| machine, disk | 16 CPU, governor `powersave`, 1-minute load 1.26 at the start (pass2 1.26; H4/H5/H6 1.66); repo 5.43 → 5.42 GB free, artifact disk 56.0 → 33.39 GB free |
| ceilings, logs | 1800 s per refocus; 4500 s on the loop; corpus 7200 s, pytest 3600 s, cargo 7200 s — none reached. Logs under `acceptance-e4p/logs/` |

### The kept store was not written — and one lens note

The runner's proof (§1.3): every `.db`'s size and `st_mtime_ns` censused before
and after and compared **file by file** — 122 before, 122 after,
`kept_census_differences` **empty**, `kept_store_unchanged: true`.

Beside it, a check made after the run over the *sidecars*, which the census
does not cover: **zero `.db` and zero `.db-wal`** files are newer than the
19:19:00 launch and **exactly 61 `.db-shm`** are — precisely the 61 originals
§1.3 copied. That is what a read-only WAL open does: SQLite maps the
shared-memory index even under `mode=ro`, touching the `-shm` mtime while the
database and its WAL are untouched. A **lens note, not a violation** — no page
of any kept database changed, and §1.3's census is what says so.

## 3. Results

Every number below is the raw record's. The loop was **whole** — 61 of 61
invocations ran, none killed, none skipped by the bound — so no measurement
cell (`{value, n, lens, dropped}`) carries a `dropped` reason and none is
nulled. Nulls do exist *inside* two of them, and are gap 1's rather than the
loop's: `H1.withheld.value` is `null` for **57 of 61** names, as are those 57
pair rows' `program_threads`, `harness_threads`, `names_the_exclusion` and
`sides_agree`.

### The six endpoints

| id | measurement | gate | measured | verdict |
|---|---|---|---|---|
| H1 | licences **granted** / the WITHHELD set | 57 / §1.2's four | **0** / **all 61** | **STOP** |
| H2 | **MATCH** verdicts | 61 of 61 | **61** | **PASS** |
| H3 | pairs of exactly one | 61 of 61 | **61** | **PASS** |
| H4 | focused shim keys, every one the driver's inode | 61 | **61 / 61** | **PASS** |
| H5 | `schema_version` in raw and assembled | `e4p/1` both | **`e4p/1` both** | **PASS** |
| H6 | corpus, Python suite, `cargo test --workspace` | all green | **all green** | **PASS** |

### H1 — the partition

| | measured |
|---|---|
| granted | **0** of 61 (predicted 57) |
| WITHHELD | **61** of 61 |
| `withheld_missing` | **none** — §1.2's four are all in the withheld set |
| `withheld_only_here` | **57** — the pairs §1.2 predicted granted |
| `withheld_count_mismatches` | **none** |
| the four §1.2 pairs' program-thread counts | `a_pager_can_be_shared_across_threads` **1**; `the_refusal_advises_a_window_that_actually_places` **4**; `the_advice_never_exceeds_the_window_the_agent_already_had` **4**; `the_journal_records_the_advice_alongside_the_refusal_arithmetic` **4** — 1/4/4/4, exactly §1.2's prediction |
| granted lines that hide the exclusion | **none** (there were no granted lines) |
| WITHHELD reasons that never subtracted | **none of the 4** pairs whose reason WAS the thread clause; unevaluable on the other 57 (§5 gap 1) |
| pairs whose two sides disagree on the count | **none of the same 4**; `sides_agree` is `None` on the other 57 |
| pairs whose licence could not be read | **none** |
| harness phrase printed | one spelling only: `libtest's per-test thread, excluded as the recorder's own` |
| harness threads, two readings | the `threads:` line: **1 on 61 of 61**. The *licence* clause: 1 on the four, **absent on the other 57** (§5) |

### H2 / H3

MATCH on **61 of 61**; every exit **0**, word and exit agreeing on all 61
(`word_and_exit_disagree` empty). Pair count **1 on all 61** read from the
store, the CLI's printed id agreeing on all 61, and R2's excluded-child list
**empty on every pair** — §1.1's greps found `Command::new` 0 hits.

### H4 — the shim census

| | value |
|---|---|
| focused keys under `<target>/sensorium/shim` | **61** |
| entries holding a `cargo-sensorium` | **61** — every key |
| distinct inodes | **1** |
| bytes, counted **once per inode** | **40 508 024** |
| the driver's inode | **20256660**, `st_dev` 66308 |
| keys sharing that inode | **61 of 61**; `not_linked` empty |
| keys holding no binary | **none** |

The three numbers are printed separately and the byte total is never the sum of
the per-entry sizes: 61 hard links to one 40 MB binary hold 40 MB.

### H5 / H6

`schema_version` is `e4p/1` in the raw record, in the assembled one, and in
`assembled.schema_version`. On a **dry assemble** — nothing written — the E9
and E4 renderers each printed their own field (`e9/1`, `e4/1`); their committed
`results.json` **do not carry it** and are not re-derived, stated here rather
than repaired.

H6: corpus **rc 0**, 62 cases / 138 questions, no failures, errors or skips
(64.9 s); Python suite **rc 0**, `1862 passed, 2 skipped in 141.65s (0:02:21)`
— H6 exports `SENSORIUM_CARGO_SENSORIUM`, so the module skipped without a built
driver runs here; `cargo test --workspace` **rc 0**, 42 `test result: ok.`
lines (12.7 s); the driver's sha256 after H6 unchanged.
`refocus_child_run_present` reads **`null`** — the collector's JSON exposes no
list this reader could name a case in, and `null` is "could not be read that
way", never `false` (§5).

### Reported without a gate

§1.4's ungated list — the per-refocus walls, the copy's size and engine, the
four verified/unverifiable licence counts — is reported in full in
[`…-e4p-rows.md`](2026-09-07-sensorium-rung4-e4p-rows.md) beside the 61-row
table, so this record stays inside the 800-line ceiling.

### The 61 pairs

Row by row — name, original, re-run id, verdict, exit, licence, program
threads, both harness readings, env status, relocated and changed keys — in
[`…-e4p-rows.md`](2026-09-07-sensorium-rung4-e4p-rows.md), a sibling file so
this record stays inside the project's 800-line ceiling.

## 4. Verdicts

**H1 — STOP.** Granted **0** of 61 where §1.2 predicted 57. Under §1.4's kill 1
the partition observed is the finding, not a retry under a narrower rule.

**R1 worked, on every pair** — the first thing this record has to say, because
the STOP is not R1's:

* the harness exclusion is named on **61 of 61** `threads:` lines in one
  spelling — `1 harness thread (libtest's per-test thread, excluded as the
  recorder's own) is not among these counts`;
* the four pairs §1.2 named report the **program's own** counts **1, 4, 4, 4**
  — E4's raw 2, 5, 5, 5 minus the harness thread — so the subtraction fired
  and none reports the unsubtracted number;
* **no** granted line hid the exclusion (there were none to hide) and not one
  licence went unread — both 61-wide; and on **all four** pairs whose reason
  was the thread clause, no reason failed to subtract and the two sides
  agreed. Those last two are **4-wide, not 61** — the other 57 parsed no
  thread sentence, so they are unevaluable rather than clean (§5 gap 1).

Every second reading §1 pre-committed for H1 came back clean. The word did not
move for the reason §1.2 was about.

**What withheld all 61 was the ENV clause, on exactly one key.** The licence
caveat is identical on all 61 pairs:

> 1 environment variable(s) differ between the two runs (RUSTDOCFLAGS); a
> program that reads them got different input

and the env line on all 61 reads `CHANGED` with the four target-rooted
variables **relocated and named** — `CARGO_BIN_EXE_bloomery-daemon`,
`CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` — as A1
ruled: the 5b rule did its job on four keys and left a fifth.

### The cause, as evidence

`RUSTDOCFLAGS` as the two sides recorded it (pair 1; identical in shape on all
61 — the only place in this record a box path appears outside the lens table):

| side | value |
|---|---|
| original `20260907-111144-33d30c` | `--extern sensorium_rt=/mnt/extra/sensorium-rung2/bloomery-target-e4/sensorium/rt/d9ce385a08c6646b/unwind/libsensorium_rt.rlib -L dependency=/mnt/extra/sensorium-rung2/bloomery-target-e4/sensorium/rt/d9ce385a08c6646b/unwind` |
| re-run `20260907-191909-0570e1` | `--extern sensorium_rt=/mnt/extra/sensorium-rung2/bloomery-target-e4p/sensorium/rt/83d9294b8135c157/unwind/libsensorium_rt.rlib -L dependency=/mnt/extra/sensorium-rung2/bloomery-target-e4p/sensorium/rt/83d9294b8135c157/unwind` |

Two things moved and only one of them is the world's:

1. the target **root** — `bloomery-target-e4` → `bloomery-target-e4p` — which
   §1.4 mandates and which the 5b rule relocates correctly;
2. the **rt hash** — `d9ce385a08c6646b` → `83d9294b8135c157` — the
   **recorder's own**: the driver injects this whole fragment, the hash keys
   the `sensorium-rt` build, and it moved because the driver that recorded the
   originals was **0.5.0** and the one that re-ran them is **0.5.1**.

The hash is not a relocation, so `differs_only_by_root` correctly returns
false, the key falls into the changed list, and the env clause reports the
recorder's own footprint as a change the world made — the bug class R1 had just
closed one check along, reappearing next door.

**Why the dry run could not see it.** It recorded its two originals minutes
before refocusing them, under the same driver build and so the same rt hash;
the fragment relocated cleanly and the licence came back `granted`. The
confound needs an original recorded under a **different driver build**, which
only the kept E4 store had.

**H2 — PASS.** MATCH 61 of 61, the gate exactly: the comparator is untouched by
this slice and reproduced E4's verdict on every pair.

**H3 — PASS.** Pair 1 of 1 on all 61, read from the store and cross-checked
against the printed id; R2's excluded-child list empty on every pair.

**H4 — PASS, by the words** — 61 focused keys, **every** one holding a
`cargo-sensorium` at the driver's own inode. R3's fallback-to-copy was not
taken, no key was left without a binary, the finding branch does not apply.

**H5 — PASS** and **H6 — PASS**, on the numbers §3 prints: `e4p/1` in both
records with both renderers printing their own field on a dry assemble;
corpus, Python suite and `cargo test --workspace` all green, the driver's
sha256 unchanged after the workspace test that shares its target.

**The record's own reading of itself.** Five endpoints of six answered as
pre-registered; the sixth measured the env clause rather than the licence
word's dependence on R1, because the env clause withholds before the thread
clause is reached. H1's question is therefore **unanswered by this run** — the
finding, not a smaller version of the predicted one.

## 5. Gaps

### The ruling on this measurement (controller, 2026-09-07)

**The measurement STANDS as a STOP.** It is not re-rolled and no `src/` change
is made after it to make it come out differently — §1.4's kill 6, and the
reason a pre-registration is worth having. **The finding is the slice's
result.**

**Ruled for the next slice, not this one:** the driver-injected fragment of
`RUSTDOCFLAGS` — `--extern sensorium_rt=…/sensorium/rt/<hash>/…` with its `-L
dependency=…` — is **stripped before the compare as the recorder's own**, on
the precedent this licence sets twice already (the recorder's `SENSORIUM_*`
variables, and R1's harness thread). **Anything else in `RUSTDOCFLAGS` stays
the world's** and still withholds: the rule is about that fragment, never the
variable. Then **E4″** re-measures §1.2's question over a subject including an
original recorded under a **different driver build** — the one condition under
which this confound is visible. Also carried: the tiered build-and-run-bearing
set (5c).

### The instrument's own gaps, as this run exposed them

1. **The licence partition reads `None` on a pair withheld by the env clause.**
   It reads the thread arithmetic out of the licence's thread sentence, and on
   the 57 pairs with no program thread R1 left **no such sentence**
   (`_licence_caveats` emits one only above zero), so `program_threads` and
   `harness_threads` are `null`. Honest as far as it goes; the aggregates
   built on it are not. `phase_h1`'s `harness_threads_all_one` came back
   **false** over 61 pairs each of which reported one harness thread on its
   `threads:` line — the parser reads that line (`threads_harness`, 1 on
   61 of 61) but the aggregate never falls back to it. The same silent-`None`
   path empties `sides_disagree` and `reasons_that_never_subtracted`, which
   `phase_h1` appends to only on a `False`/truthy reading: both are
   observations over **4** pairs, printed 4-wide in §3 and §4. **Fix next
   slice:** take the harness reading from `threads:` when the licence clause
   is silent and record which line each count came from — both readings are
   already in the raw record, so no number here needs re-deriving.
2. **`sensorium_version` recorded as an empty string.** The preflight probes
   the tree's token with `import sensorium; print(sensorium.__version__)`;
   `sensorium` has no `__version__` and the helper captures **stdout only**, so
   an `AttributeError` on stderr became `""` in the lens. A failed probe must
   record `null` with its reason, never a blank that reads as measured. The
   installed-metadata token (`0.6.0`, stale) was recorded and is in §2.
3. **`refocus_child_run_present` is `null`.** `_case_present` looks for a list
   under `cases` / `case_names` / `names` and the collector exposes none, so
   the reader cannot name a case. `null` is honest and the field is reported,
   never gated — but H6's "the new `refocus_child_run` case included" is
   therefore **not** mechanically checked here.
4. **The renderer's §1 byte-lock sentence contradicts itself** — it prints
   "§1 was committed ALONE and has never been amended (amended: yes)", the
   clause hard-coded beside the read flag. §2 is hand-written for that reason.
5. **The fourth lock test checks the amendment's shape, not its content** —
   it compares every `|` row across the two commits and asserts §1.5 appeared;
   a prose change **outside** a table row still moves the sha (so the lock
   refuses) but the test's message would say "rows unchanged".
6. **The kept store's sidecars are outside the pre-registered census** — §1.3
   censuses `.db`; a read-only WAL open touches `.db-shm` (checked by hand, §2).
7. **`reported.licence_verified_counts` is permanently `null`** —
   `acceptance_e4p_schema` builds it from a **top-level** key the runner never
   writes; the data lives per row under `raw_pass2.refocuses[*].licence`. The
   four counts were read from there and are right, but a reader who opens the
   field the record names finds `null`. One key path to fix.

### What no `dropped` list says

No measurement cell carries a `dropped` reason and no endpoint is nulled: the
loop ran whole, nothing killed, no bound reached, every phase present. H1's
cells are measured values that failed their gate, not missing ones. The nulls
that do exist are gap 1's — 57 unparsed program-thread readings inside
`H1.withheld.value` and on 57 pair rows — and `H1.withheld.dropped` is empty
because the cell itself was measured.

### Not in this record

E4 is not re-opened and no number in it is re-measured; the four
verified/unverifiable counts stay reported and unsummed; nothing is gated on a
wall; §1 — §1.5 included — is never edited by this section.
