# E4″ — what the 61 rows measured

The measured companion to
[`…-e4pp-rows.md`](2026-09-08-sensorium-rung4-e4pp-rows.md), which is the
**locked subject** and is not edited: §1.1 prints its sha256, the runner
refuses to start unless the file on disk hashes to it, and
`tests/test_acceptance_e4pp_lock.py` asserts the same digest, so a measured
column appended there would be a different subject rather than a result.
The four measured columns live here instead, row for row and in the same
order, and the record's §2 gives both files' sha256.

Every column below is read from
`2026-09-08-sensorium-rung4-e4pp.results.json` at `pairs.rows[*]` — the
rows whose `arm` is `A` for the table of 61, in `index` order — and
nothing here is re-derived: `licence`, `program_threads`, `verdict`,
`pair_count`, `original` and `pair`. The `#`, the name and the original
run id are the locked file's own, and were checked equal row for row
before this table was written.

## Arm A — the 61 kept originals, re-read under driver `0.5.2`

| # | fn (the `--focus` value) | licence | program threads | verdict | pairs | original run id | the pair this run made |
|---|---|---|---|---|---|---|---|
| 1 | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | granted | 0 | MATCH | 1 | `20260907-111144-33d30c` | `20260908-055244-aceee8` |
| 2 | `unknown_model_mutating_verbs_is_false` | granted | 0 | MATCH | 1 | `20260907-111145-e2c8e3` | `20260908-055250-e8bd07` |
| 3 | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | granted | 0 | MATCH | 1 | `20260907-111146-8497d7` | `20260908-055257-711233` |
| 4 | `stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement` | granted | 0 | MATCH | 1 | `20260907-111147-b2146f` | `20260908-055303-08d8cd` |
| 5 | `set_codec_gate_on_unknown_model_is_named` | granted | 0 | MATCH | 1 | `20260907-111148-085b7a` | `20260908-055310-fe88a8` |
| 6 | `model_patch_codec_follows_the_attached_profiles_selection` | granted | 0 | MATCH | 1 | `20260907-111149-82548c` | `20260908-055316-16067e` |
| 7 | `model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown` | granted | 0 | MATCH | 1 | `20260907-111150-ab143a` | `20260908-055323-0ada3b` |
| 8 | `model_codec_from_profile_separates_a_measured_selection_from_the_default` | granted | 0 | MATCH | 1 | `20260907-111151-71f89b` | `20260908-055329-fedaeb` |
| 9 | `agent_task_policy_resolves_through_the_agents_model` | granted | 0 | MATCH | 1 | `20260907-111152-b19140` | `20260908-055335-4ce0f4` |
| 10 | `agent_task_policy_is_none_for_an_unknown_agent` | granted | 0 | MATCH | 1 | `20260907-111153-2fe948` | `20260908-055342-e5fc53` |
| 11 | `agent_task_policy_resolves_envelope_through_the_agents_model` | granted | 0 | MATCH | 1 | `20260907-111154-de3ee9` | `20260908-055348-23458e` |
| 12 | `journal_codec_fixture_round_trips_through_replay` | granted | 0 | MATCH | 1 | `20260907-111155-67ca55` | `20260908-055355-5054f1` |
| 13 | `journal_codec_fixture_round_trips_a_refuse_class_row` | granted | 0 | MATCH | 1 | `20260907-111156-d0c398` | `20260908-055401-dd6a17` |
| 14 | `unmeasured_model_has_null_done_trust_and_null_refusal_gate` | granted | 0 | MATCH | 1 | `20260907-111157-3a93a9` | `20260908-055408-29536c` |
| 15 | `stored_gate_with_both_classes_clear_renders_done_trust_true` | granted | 0 | MATCH | 1 | `20260907-111159-54c3a7` | `20260908-055415-272045` |
| 16 | `stored_gate_with_one_class_failing_renders_done_trust_false` | granted | 0 | MATCH | 1 | `20260907-111200-990b34` | `20260908-055421-46c3fa` |
| 17 | `set_refusal_gate_never_touches_mutating_verbs_or_codec_gate` | granted | 0 | MATCH | 1 | `20260907-111201-ab997d` | `20260908-055428-8983b0` |
| 18 | `set_refusal_gate_on_unknown_model_is_named` | granted | 0 | MATCH | 1 | `20260907-111202-764f03` | `20260908-055435-c4d4b1` |
| 19 | `journal_codec_verdict_mixed_round_trips_through_replay` | granted | 0 | MATCH | 1 | `20260907-111203-8bd7b0` | `20260908-055442-093b65` |
| 20 | `journal_codec_verdict_round_trips_through_replay` | granted | 0 | MATCH | 1 | `20260907-111204-4e635f` | `20260908-055448-1d88fd` |
| 21 | `residency_refusal_is_pre_checked_and_never_touches_the_substrate` | granted | 0 | MATCH | 1 | `20260907-111206-be9b6d` | `20260908-055455-483492` |
| 22 | `stale_image_digest_cold_starts_and_journals_degraded` | granted | 0 | MATCH | 1 | `20260907-111207-7997d1` | `20260908-055501-0425ce` |
| 23 | `corrupt_spilled_image_cold_starts_and_journals_degraded` | granted | 0 | MATCH | 1 | `20260907-111208-7b34da` | `20260908-055508-808265` |
| 24 | `suspend_resume_round_trips_the_kv_image_through_nvme` | granted | 0 | MATCH | 1 | `20260907-111209-cf57f2` | `20260908-055515-d6eca3` |
| 25 | `unmeasured_vram_journals_degraded_once_and_caps_residency_at_one` | granted | 0 | MATCH | 1 | `20260907-111210-de710a` | `20260908-055521-e8acfe` |
| 26 | `missing_stats_is_a_contract_violation_not_a_reply` | granted | 0 | MATCH | 1 | `20260907-111211-ac01ef` | `20260908-055528-1f246b` |
| 27 | `unload_model_pages_out_holders_and_journals` | granted | 0 | MATCH | 1 | `20260907-111212-f190d4` | `20260908-055535-0bef3b` |
| 28 | `image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context` | granted | 0 | MATCH | 1 | `20260907-111213-53bd85` | `20260908-055541-d49942` |
| 29 | `a_transient_restore_failure_keeps_the_image_for_the_retry` | granted | 0 | MATCH | 1 | `20260907-111214-83522d` | `20260908-055548-a58726` |
| 30 | `an_aborted_eviction_is_journaled_not_left_orphaned` | granted | 0 | MATCH | 1 | `20260907-111216-997b0b` | `20260908-055555-9c84fc` |
| 31 | `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` | granted | 0 | MATCH | 1 | `20260907-111217-bfe991` | `20260908-055601-754fce` |
| 32 | `a_pager_can_be_shared_across_threads` | WITHHELD | 1 | MATCH | 1 | `20260907-111218-b37956` | `20260908-055608-64b8f6` |
| 33 | `unknown_model_and_unknown_agent_are_named` | granted | 0 | MATCH | 1 | `20260907-111219-a4ad75` | `20260908-055615-8722ab` |
| 34 | `agent_ids_are_unique_and_status_is_a_snapshot` | granted | 0 | MATCH | 1 | `20260907-111220-6d9c78` | `20260908-055622-8491bb` |
| 35 | `a_model_with_no_admission_block_renders_none` | granted | 0 | MATCH | 1 | `20260907-111221-2070ee` | `20260908-055629-adea62` |
| 36 | `the_refusal_advises_a_window_that_actually_places` | WITHHELD | 4 | MATCH | 1 | `20260907-111222-5b7e4e` | `20260908-055635-65990a` |
| 37 | `the_advice_never_exceeds_the_window_the_agent_already_had` | WITHHELD | 4 | MATCH | 1 | `20260907-111224-baa1d5` | `20260908-055642-f2ce95` |
| 38 | `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` | granted | 0 | MATCH | 1 | `20260907-111225-5d21ce` | `20260908-055648-688dc0` |
| 39 | `the_journal_records_the_advice_alongside_the_refusal_arithmetic` | WITHHELD | 4 | MATCH | 1 | `20260907-111226-12b15f` | `20260908-055656-817370` |
| 40 | `remove_agent_destroys_context_and_forgets_the_agent` | granted | 0 | MATCH | 1 | `20260907-111227-69395c` | `20260908-055702-0fc9d4` |
| 41 | `remove_agent_on_a_fresh_agent_is_not_an_error` | granted | 0 | MATCH | 1 | `20260907-111228-1b60c3` | `20260908-055709-dafc45` |
| 42 | `remove_agent_on_unknown_id_is_named` | granted | 0 | MATCH | 1 | `20260907-111229-7ecc9d` | `20260908-055715-3ee056` |
| 43 | `remove_agent_journals_the_removal_with_its_reason` | granted | 0 | MATCH | 1 | `20260907-111230-c3f27d` | `20260908-055723-be3a6f` |
| 44 | `a_second_agents_reservation_not_just_its_kv_is_what_refuses_it` | granted | 0 | MATCH | 1 | `20260907-111232-be1ecb` | `20260908-055729-850ac1` |
| 45 | `the_global_overhead_margin_is_subtracted_from_placement_too` | granted | 0 | MATCH | 1 | `20260907-111233-d808f7` | `20260908-055736-953565` |
| 46 | `status_reports_reserved_bytes_and_both_overhead_terms` | granted | 0 | MATCH | 1 | `20260907-111234-77aca0` | `20260908-055743-874a9c` |
| 47 | `eviction_credits_the_whole_reservation_back` | granted | 0 | MATCH | 1 | `20260907-111235-5c41c0` | `20260908-055750-6e2696` |
| 48 | `a_vram_bound_window_is_placeable_item_7_regression` | granted | 0 | MATCH | 1 | `20260907-111236-78e563` | `20260908-055757-819410` |
| 49 | `a_sibling_blind_automatic_window_still_refuses_item_7_third_half` | granted | 0 | MATCH | 1 | `20260907-111237-889ce6` | `20260908-055803-95c5ea` |
| 50 | `recurrent_state_is_charged_per_context_and_reported` | granted | 0 | MATCH | 1 | `20260907-111238-841017` | `20260908-055810-0ed02a` |
| 51 | `recurrent_state_binds_the_vram_term_of_the_window_law` | granted | 0 | MATCH | 1 | `20260907-111240-16e1f6` | `20260908-055817-bee523` |
| 52 | `eviction_under_pressure_saves_image_and_journals` | granted | 0 | MATCH | 1 | `20260907-111241-232c32` | `20260908-055823-1fc0a6` |
| 53 | `the_eviction_story_is_journaled_in_order_with_a_faithful_prompt` | granted | 0 | MATCH | 1 | `20260907-111242-246517` | `20260908-055830-ac8749` |
| 54 | `oversized_prompt_is_refused_with_arithmetic_never_truncated` | granted | 0 | MATCH | 1 | `20260907-111243-a3b48c` | `20260908-055837-cfa47f` |
| 55 | `budget_exhaustion_refuses_before_the_call` | granted | 0 | MATCH | 1 | `20260907-111244-e71496` | `20260908-055844-c43c56` |
| 56 | `loading_a_model_charges_its_weights_against_the_budget` | granted | 0 | MATCH | 1 | `20260907-111246-2e13b3` | `20260908-055850-3a42bf` |
| 57 | `a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic` | granted | 0 | MATCH | 1 | `20260907-111247-da8d66` | `20260908-055857-6f0250` |
| 58 | `unload_credits_the_weights_back` | granted | 0 | MATCH | 1 | `20260907-111248-87cf0b` | `20260908-055904-28e03b` |
| 59 | `status_reports_loaded_weights` | granted | 0 | MATCH | 1 | `20260907-111249-6b0bff` | `20260908-055911-b6aa20` |
| 60 | `unmeasured_budget_refusal_detail_says_unmeasured_not_zero` | granted | 0 | MATCH | 1 | `20260907-111250-092953` | `20260908-055918-8838d4` |
| 61 | `a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics` | granted | 0 | MATCH | 1 | `20260907-111251-80be5a` | `20260908-055924-c2dc8b` |

**57 granted, 4 WITHHELD, MATCH on 61, one pair on every row** — the
partition §1.2 wrote first, and `endpoints.H1.headline`,
`endpoints.H1.withheld`, `endpoints.H3.headline` and
`endpoints.H3.pairs_of_one` are the same four numbers counted over this
table. The program-thread column is **0** on the 57 and **1 / 4 / 4 / 4**
on the four, each read from the licence's own thread clause
(`pairs.rows[*].counts_source` is `licence-clause` on all 61); the one
harness thread every pair reports is excluded before this column and is
never in it.

## Arms B and C — the two four-pair controls

`pairs.rows[*]` with `arm` `armB` or `armC`. Arm B adds `E4PP_INPUT`, a
name no code in the clone reads; arm C adds `TERM_SESSION_ID`, a member of
session set 1 chosen at preflight. The licence column is the endpoint:
arm B must withhold on all four (the exemption did not eat the rule), and
arm C's word must equal arm A's for the same row (a session key never
moves it).

| arm | fn | licence | program threads | verdict | pairs | arm A's word for the same row |
|---|---|---|---|---|---|---|
| B | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | WITHHELD | 0 | MATCH | 1 | granted |
| B | `unknown_model_mutating_verbs_is_false` | WITHHELD | 0 | MATCH | 1 | granted |
| B | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | WITHHELD | 0 | MATCH | 1 | granted |
| B | `a_pager_can_be_shared_across_threads` | WITHHELD | 1 | MATCH | 1 | WITHHELD |
| C | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | granted | 0 | MATCH | 1 | granted |
| C | `unknown_model_mutating_verbs_is_false` | granted | 0 | MATCH | 1 | granted |
| C | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | granted | 0 | MATCH | 1 | granted |
| C | `a_pager_can_be_shared_across_threads` | WITHHELD | 1 | MATCH | 1 | WITHHELD |

Arm B: **WITHHELD 4 of 4**, each caveat naming `E4PP_INPUT`
(`endpoints.H5.env_caveat_names_the_key` = 4 of 4), and the pager row
keeps its one-program-thread reason beside the env caveat
(`endpoints.H5.thread_reason_kept` = true). Arm C: the word equals arm A's
on **4 of 4** (`endpoints.H6.headline`), with the printed session set
`['CLAUDE_CODE_SESSION_ID', 'TERM_SESSION_ID']` and K **2** on all four.
Arm B's verdicts are **reported, never gated**: all four came back MATCH
(`reported.arm_b_verdicts`), which is what a name nothing reads should do
and would have been a finding either way.
