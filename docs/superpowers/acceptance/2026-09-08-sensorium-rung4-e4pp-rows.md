# E4″ — the 61 originals, and the licence each is expected to get

The subject table of `2026-09-08-sensorium-rung4-e4pp.md` §1.1, held in a
sibling file so §1 stays short enough to read in one sitting. This file is
part of the pre-registration: §1.1 prints its **sha256**, the lock module
`rust/tests/acceptance_e4pp_lock.py` carries the same digest as
`ROWS_SHA256`, and the runner refuses to start unless the file on disk
hashes to it. A byte that moves here after the lock is a different subject,
not a correction.

The rows are E4′ §1.1's enumeration in E4′'s order, each carrying the run
id E4's pass 1 produced for it — generated from
`rust/tests/acceptance_e4p_rows.ROWS`, never retyped, because a digit
retyped inside a run id names a trace that does not exist and is found by a
refusal with a store already copied. The seven per-file counts are
20 / 15 / 4 / 4 / 8 / 4 / 6 = **61**.

The last column is §1.2's expected partition, written first and carried
here row by row so no reader has to hold four names in their head while
reading sixty-one: **57 granted**, and **WITHHELD** on exactly four — one
with a single program thread of its own, three with four each. The counts
in parentheses are the PROGRAM's own threads, the harness thread already
subtracted; a WITHHELD reason that names the raw count instead (2, 5, 5, 5)
is H1's STOP.

| # | fn (the `--focus` value) | file | original run id | expected licence |
|---|---|---|---|---|
| 1 | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | `pager_codec_gate_test.rs` | `20260907-111144-33d30c` | granted |
| 2 | `unknown_model_mutating_verbs_is_false` | `pager_codec_gate_test.rs` | `20260907-111145-e2c8e3` | granted |
| 3 | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | `pager_codec_gate_test.rs` | `20260907-111146-8497d7` | granted |
| 4 | `stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement` | `pager_codec_gate_test.rs` | `20260907-111147-b2146f` | granted |
| 5 | `set_codec_gate_on_unknown_model_is_named` | `pager_codec_gate_test.rs` | `20260907-111148-085b7a` | granted |
| 6 | `model_patch_codec_follows_the_attached_profiles_selection` | `pager_codec_gate_test.rs` | `20260907-111149-82548c` | granted |
| 7 | `model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown` | `pager_codec_gate_test.rs` | `20260907-111150-ab143a` | granted |
| 8 | `model_codec_from_profile_separates_a_measured_selection_from_the_default` | `pager_codec_gate_test.rs` | `20260907-111151-71f89b` | granted |
| 9 | `agent_task_policy_resolves_through_the_agents_model` | `pager_codec_gate_test.rs` | `20260907-111152-b19140` | granted |
| 10 | `agent_task_policy_is_none_for_an_unknown_agent` | `pager_codec_gate_test.rs` | `20260907-111153-2fe948` | granted |
| 11 | `agent_task_policy_resolves_envelope_through_the_agents_model` | `pager_codec_gate_test.rs` | `20260907-111154-de3ee9` | granted |
| 12 | `journal_codec_fixture_round_trips_through_replay` | `pager_codec_gate_test.rs` | `20260907-111155-67ca55` | granted |
| 13 | `journal_codec_fixture_round_trips_a_refuse_class_row` | `pager_codec_gate_test.rs` | `20260907-111156-d0c398` | granted |
| 14 | `unmeasured_model_has_null_done_trust_and_null_refusal_gate` | `pager_codec_gate_test.rs` | `20260907-111157-3a93a9` | granted |
| 15 | `stored_gate_with_both_classes_clear_renders_done_trust_true` | `pager_codec_gate_test.rs` | `20260907-111159-54c3a7` | granted |
| 16 | `stored_gate_with_one_class_failing_renders_done_trust_false` | `pager_codec_gate_test.rs` | `20260907-111200-990b34` | granted |
| 17 | `set_refusal_gate_never_touches_mutating_verbs_or_codec_gate` | `pager_codec_gate_test.rs` | `20260907-111201-ab997d` | granted |
| 18 | `set_refusal_gate_on_unknown_model_is_named` | `pager_codec_gate_test.rs` | `20260907-111202-764f03` | granted |
| 19 | `journal_codec_verdict_mixed_round_trips_through_replay` | `pager_codec_gate_test.rs` | `20260907-111203-8bd7b0` | granted |
| 20 | `journal_codec_verdict_round_trips_through_replay` | `pager_codec_gate_test.rs` | `20260907-111204-4e635f` | granted |
| 21 | `residency_refusal_is_pre_checked_and_never_touches_the_substrate` | `pager_obligation_test.rs` | `20260907-111206-be9b6d` | granted |
| 22 | `stale_image_digest_cold_starts_and_journals_degraded` | `pager_obligation_test.rs` | `20260907-111207-7997d1` | granted |
| 23 | `corrupt_spilled_image_cold_starts_and_journals_degraded` | `pager_obligation_test.rs` | `20260907-111208-7b34da` | granted |
| 24 | `suspend_resume_round_trips_the_kv_image_through_nvme` | `pager_obligation_test.rs` | `20260907-111209-cf57f2` | granted |
| 25 | `unmeasured_vram_journals_degraded_once_and_caps_residency_at_one` | `pager_obligation_test.rs` | `20260907-111210-de710a` | granted |
| 26 | `missing_stats_is_a_contract_violation_not_a_reply` | `pager_obligation_test.rs` | `20260907-111211-ac01ef` | granted |
| 27 | `unload_model_pages_out_holders_and_journals` | `pager_obligation_test.rs` | `20260907-111212-f190d4` | granted |
| 28 | `image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context` | `pager_obligation_test.rs` | `20260907-111213-53bd85` | granted |
| 29 | `a_transient_restore_failure_keeps_the_image_for_the_retry` | `pager_obligation_test.rs` | `20260907-111214-83522d` | granted |
| 30 | `an_aborted_eviction_is_journaled_not_left_orphaned` | `pager_obligation_test.rs` | `20260907-111216-997b0b` | granted |
| 31 | `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` | `pager_obligation_test.rs` | `20260907-111217-bfe991` | granted |
| 32 | `a_pager_can_be_shared_across_threads` | `pager_obligation_test.rs` | `20260907-111218-b37956` | WITHHELD (1 program thread) |
| 33 | `unknown_model_and_unknown_agent_are_named` | `pager_obligation_test.rs` | `20260907-111219-a4ad75` | granted |
| 34 | `agent_ids_are_unique_and_status_is_a_snapshot` | `pager_obligation_test.rs` | `20260907-111220-6d9c78` | granted |
| 35 | `a_model_with_no_admission_block_renders_none` | `pager_obligation_test.rs` | `20260907-111221-2070ee` | granted |
| 36 | `the_refusal_advises_a_window_that_actually_places` | `pager_refusal_advice_test.rs` | `20260907-111222-5b7e4e` | WITHHELD (4 program threads) |
| 37 | `the_advice_never_exceeds_the_window_the_agent_already_had` | `pager_refusal_advice_test.rs` | `20260907-111224-baa1d5` | WITHHELD (4 program threads) |
| 38 | `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` | `pager_refusal_advice_test.rs` | `20260907-111225-5d21ce` | granted |
| 39 | `the_journal_records_the_advice_alongside_the_refusal_arithmetic` | `pager_refusal_advice_test.rs` | `20260907-111226-12b15f` | WITHHELD (4 program threads) |
| 40 | `remove_agent_destroys_context_and_forgets_the_agent` | `pager_remove_agent_test.rs` | `20260907-111227-69395c` | granted |
| 41 | `remove_agent_on_a_fresh_agent_is_not_an_error` | `pager_remove_agent_test.rs` | `20260907-111228-1b60c3` | granted |
| 42 | `remove_agent_on_unknown_id_is_named` | `pager_remove_agent_test.rs` | `20260907-111229-7ecc9d` | granted |
| 43 | `remove_agent_journals_the_removal_with_its_reason` | `pager_remove_agent_test.rs` | `20260907-111230-c3f27d` | granted |
| 44 | `a_second_agents_reservation_not_just_its_kv_is_what_refuses_it` | `pager_reservation_test.rs` | `20260907-111232-be1ecb` | granted |
| 45 | `the_global_overhead_margin_is_subtracted_from_placement_too` | `pager_reservation_test.rs` | `20260907-111233-d808f7` | granted |
| 46 | `status_reports_reserved_bytes_and_both_overhead_terms` | `pager_reservation_test.rs` | `20260907-111234-77aca0` | granted |
| 47 | `eviction_credits_the_whole_reservation_back` | `pager_reservation_test.rs` | `20260907-111235-5c41c0` | granted |
| 48 | `a_vram_bound_window_is_placeable_item_7_regression` | `pager_reservation_test.rs` | `20260907-111236-78e563` | granted |
| 49 | `a_sibling_blind_automatic_window_still_refuses_item_7_third_half` | `pager_reservation_test.rs` | `20260907-111237-889ce6` | granted |
| 50 | `recurrent_state_is_charged_per_context_and_reported` | `pager_reservation_test.rs` | `20260907-111238-841017` | granted |
| 51 | `recurrent_state_binds_the_vram_term_of_the_window_law` | `pager_reservation_test.rs` | `20260907-111240-16e1f6` | granted |
| 52 | `eviction_under_pressure_saves_image_and_journals` | `pager_test.rs` | `20260907-111241-232c32` | granted |
| 53 | `the_eviction_story_is_journaled_in_order_with_a_faithful_prompt` | `pager_test.rs` | `20260907-111242-246517` | granted |
| 54 | `oversized_prompt_is_refused_with_arithmetic_never_truncated` | `pager_test.rs` | `20260907-111243-a3b48c` | granted |
| 55 | `budget_exhaustion_refuses_before_the_call` | `pager_test.rs` | `20260907-111244-e71496` | granted |
| 56 | `loading_a_model_charges_its_weights_against_the_budget` | `pager_weights_test.rs` | `20260907-111246-2e13b3` | granted |
| 57 | `a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic` | `pager_weights_test.rs` | `20260907-111247-da8d66` | granted |
| 58 | `unload_credits_the_weights_back` | `pager_weights_test.rs` | `20260907-111248-87cf0b` | granted |
| 59 | `status_reports_loaded_weights` | `pager_weights_test.rs` | `20260907-111249-6b0bff` | granted |
| 60 | `unmeasured_budget_refusal_detail_says_unmeasured_not_zero` | `pager_weights_test.rs` | `20260907-111250-092953` | granted |
| 61 | `a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics` | `pager_weights_test.rs` | `20260907-111251-80be5a` | granted |

**61 rows, 57 granted, 4 WITHHELD.** All
61 run ids are distinct, and every one names an existing
`<run>.db` under the kept E4 store §1.3 reads (122 `.db` files, E4's 61
originals and its 61 refocused traces) — checked when this file was
written, before any E4″ instrument existed, and re-checked by the runner
before arm A opens; a missing or duplicated original is a refusal to
start, never a smaller N.
