# E4′ — the 61 pairs, row by row

The per-pair table of `docs/superpowers/acceptance/2026-09-07-sensorium-rung4-e4p.md` §3, split into a sibling file so the record itself stays inside this
project's 800-line ceiling. Every value is read from the raw record
(`results-e4p-raw.json`, `raw_pass2.refocuses[*]`) and nothing here is
derived a second time.

Four columns are the same on all 61 and are stated once rather than
repeated: **verdict** MATCH, **exit** 0, **licence** WITHHELD, **env**
CHANGED. The relocated keys are the same four on all 61 —
`CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`,
`CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` — and the changed key is
`RUSTDOCFLAGS` on all 61; both are columns below all the same, because
"the same on every row" is a finding and a reader must be able to check
it rather than take it from a sentence.

`program threads` and `harness (licence)` are read from the licence's own
thread sentence and are `—` where that sentence is absent: R1 left those
57 pairs with no program thread, so `_licence_caveats` emitted no thread
clause at all. `harness (threads:)` is the same fact from the `threads:`
line, which every pair printed. See §4 of the record.

| # | test | original | re-run | verdict | exit | licence | program threads | harness (licence) | harness (`threads:`) | env | relocated keys | changed keys |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | `20260907-111144-33d30c` | `20260907-191909-0570e1` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 2 | `unknown_model_mutating_verbs_is_false` | `20260907-111145-e2c8e3` | `20260907-191915-de396e` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 3 | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | `20260907-111146-8497d7` | `20260907-191922-47adac` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 4 | `stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement` | `20260907-111147-b2146f` | `20260907-191929-e497e3` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 5 | `set_codec_gate_on_unknown_model_is_named` | `20260907-111148-085b7a` | `20260907-191935-49f17a` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 6 | `model_patch_codec_follows_the_attached_profiles_selection` | `20260907-111149-82548c` | `20260907-191942-54f7db` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 7 | `model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown` | `20260907-111150-ab143a` | `20260907-191948-38f766` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 8 | `model_codec_from_profile_separates_a_measured_selection_from_the_default` | `20260907-111151-71f89b` | `20260907-191955-6ee346` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 9 | `agent_task_policy_resolves_through_the_agents_model` | `20260907-111152-b19140` | `20260907-192002-7110d0` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 10 | `agent_task_policy_is_none_for_an_unknown_agent` | `20260907-111153-2fe948` | `20260907-192008-149017` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 11 | `agent_task_policy_resolves_envelope_through_the_agents_model` | `20260907-111154-de3ee9` | `20260907-192015-7be13f` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 12 | `journal_codec_fixture_round_trips_through_replay` | `20260907-111155-67ca55` | `20260907-192021-610f6f` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 13 | `journal_codec_fixture_round_trips_a_refuse_class_row` | `20260907-111156-d0c398` | `20260907-192028-cad337` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 14 | `unmeasured_model_has_null_done_trust_and_null_refusal_gate` | `20260907-111157-3a93a9` | `20260907-192035-776842` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 15 | `stored_gate_with_both_classes_clear_renders_done_trust_true` | `20260907-111159-54c3a7` | `20260907-192041-6a6e11` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 16 | `stored_gate_with_one_class_failing_renders_done_trust_false` | `20260907-111200-990b34` | `20260907-192048-237db1` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 17 | `set_refusal_gate_never_touches_mutating_verbs_or_codec_gate` | `20260907-111201-ab997d` | `20260907-192054-78c3ca` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 18 | `set_refusal_gate_on_unknown_model_is_named` | `20260907-111202-764f03` | `20260907-192102-79f30c` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 19 | `journal_codec_verdict_mixed_round_trips_through_replay` | `20260907-111203-8bd7b0` | `20260907-192108-4c8fff` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 20 | `journal_codec_verdict_round_trips_through_replay` | `20260907-111204-4e635f` | `20260907-192115-c10f10` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 21 | `residency_refusal_is_pre_checked_and_never_touches_the_substrate` | `20260907-111206-be9b6d` | `20260907-192122-b143e6` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 22 | `stale_image_digest_cold_starts_and_journals_degraded` | `20260907-111207-7997d1` | `20260907-192129-41bec5` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 23 | `corrupt_spilled_image_cold_starts_and_journals_degraded` | `20260907-111208-7b34da` | `20260907-192136-9c4766` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 24 | `suspend_resume_round_trips_the_kv_image_through_nvme` | `20260907-111209-cf57f2` | `20260907-192143-953cf3` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 25 | `unmeasured_vram_journals_degraded_once_and_caps_residency_at_one` | `20260907-111210-de710a` | `20260907-192150-0a487e` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 26 | `missing_stats_is_a_contract_violation_not_a_reply` | `20260907-111211-ac01ef` | `20260907-192157-fd75b7` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 27 | `unload_model_pages_out_holders_and_journals` | `20260907-111212-f190d4` | `20260907-192204-a87af9` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 28 | `image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context` | `20260907-111213-53bd85` | `20260907-192211-eceeb4` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 29 | `a_transient_restore_failure_keeps_the_image_for_the_retry` | `20260907-111214-83522d` | `20260907-192218-592b1e` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 30 | `an_aborted_eviction_is_journaled_not_left_orphaned` | `20260907-111216-997b0b` | `20260907-192225-a7bc34` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 31 | `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` | `20260907-111217-bfe991` | `20260907-192231-323a48` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 32 | `a_pager_can_be_shared_across_threads` | `20260907-111218-b37956` | `20260907-192238-8bc873` | MATCH | 0 | WITHHELD | 1 | 1 | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 33 | `unknown_model_and_unknown_agent_are_named` | `20260907-111219-a4ad75` | `20260907-192245-84924a` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 34 | `agent_ids_are_unique_and_status_is_a_snapshot` | `20260907-111220-6d9c78` | `20260907-192252-976b56` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 35 | `a_model_with_no_admission_block_renders_none` | `20260907-111221-2070ee` | `20260907-192259-a29cfb` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 36 | `the_refusal_advises_a_window_that_actually_places` | `20260907-111222-5b7e4e` | `20260907-192306-195599` | MATCH | 0 | WITHHELD | 4 | 1 | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 37 | `the_advice_never_exceeds_the_window_the_agent_already_had` | `20260907-111224-baa1d5` | `20260907-192312-5d9d6a` | MATCH | 0 | WITHHELD | 4 | 1 | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 38 | `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` | `20260907-111225-5d21ce` | `20260907-192319-8c75a2` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 39 | `the_journal_records_the_advice_alongside_the_refusal_arithmetic` | `20260907-111226-12b15f` | `20260907-192326-0b0638` | MATCH | 0 | WITHHELD | 4 | 1 | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 40 | `remove_agent_destroys_context_and_forgets_the_agent` | `20260907-111227-69395c` | `20260907-192333-285fa2` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 41 | `remove_agent_on_a_fresh_agent_is_not_an_error` | `20260907-111228-1b60c3` | `20260907-192339-9721de` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 42 | `remove_agent_on_unknown_id_is_named` | `20260907-111229-7ecc9d` | `20260907-192346-7d1876` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 43 | `remove_agent_journals_the_removal_with_its_reason` | `20260907-111230-c3f27d` | `20260907-192353-7eb4cf` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 44 | `a_second_agents_reservation_not_just_its_kv_is_what_refuses_it` | `20260907-111232-be1ecb` | `20260907-192359-c08101` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 45 | `the_global_overhead_margin_is_subtracted_from_placement_too` | `20260907-111233-d808f7` | `20260907-192406-3d59b8` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 46 | `status_reports_reserved_bytes_and_both_overhead_terms` | `20260907-111234-77aca0` | `20260907-192413-a0095a` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 47 | `eviction_credits_the_whole_reservation_back` | `20260907-111235-5c41c0` | `20260907-192420-6261b8` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 48 | `a_vram_bound_window_is_placeable_item_7_regression` | `20260907-111236-78e563` | `20260907-192427-04f8ff` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 49 | `a_sibling_blind_automatic_window_still_refuses_item_7_third_half` | `20260907-111237-889ce6` | `20260907-192434-07d470` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 50 | `recurrent_state_is_charged_per_context_and_reported` | `20260907-111238-841017` | `20260907-192441-aa8252` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 51 | `recurrent_state_binds_the_vram_term_of_the_window_law` | `20260907-111240-16e1f6` | `20260907-192447-3f54a4` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 52 | `eviction_under_pressure_saves_image_and_journals` | `20260907-111241-232c32` | `20260907-192454-502e68` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 53 | `the_eviction_story_is_journaled_in_order_with_a_faithful_prompt` | `20260907-111242-246517` | `20260907-192501-3f2e1b` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 54 | `oversized_prompt_is_refused_with_arithmetic_never_truncated` | `20260907-111243-a3b48c` | `20260907-192507-f1b53e` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 55 | `budget_exhaustion_refuses_before_the_call` | `20260907-111244-e71496` | `20260907-192514-3763e6` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 56 | `loading_a_model_charges_its_weights_against_the_budget` | `20260907-111246-2e13b3` | `20260907-192521-d6888f` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 57 | `a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic` | `20260907-111247-da8d66` | `20260907-192528-b9721c` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 58 | `unload_credits_the_weights_back` | `20260907-111248-87cf0b` | `20260907-192535-b652da` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 59 | `status_reports_loaded_weights` | `20260907-111249-6b0bff` | `20260907-192542-c7d4b5` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 60 | `unmeasured_budget_refusal_detail_says_unmeasured_not_zero` | `20260907-111250-092953` | `20260907-192549-5d5888` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |
| 61 | `a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics` | `20260907-111251-80be5a` | `20260907-192556-61f70c` | MATCH | 0 | WITHHELD | — | — | 1 | CHANGED | `CARGO_BIN_EXE_bloomery-daemon`, `CARGO_BIN_EXE_flywheel-tool`, `CARGO_TARGET_DIR`, `LD_LIBRARY_PATH` | `RUSTDOCFLAGS` |


## Reported without a gate (§1.4)

Moved here from §3 of the record for the same reason the table is here: the
record is at its 800-line ceiling. Every number is the raw record's.

**Walls.** First focus **8.705 s**; the later 60 mean **6.775 s**, max
**7.557 s**, min 6.523 s; 415.2 s over the loop against a 4500 s bound.
Nothing is gated on a wall.

**The copy.** 61 originals, **21 770 240 B**, by the Python `sqlite3` module
(SQLite 3.46.1); the fresh store held exactly 61 files when the loop opened,
only the copies.

**The four verified/unverifiable licence counts**, carried from E4's H4 in
kind and never summed — read **per row** from
`raw_pass2.refocuses[*].licence`, because the assembled record's
`reported.licence_verified_counts` is `null` (record §5 gap 7): `source`
**unchanged on 61**; `env` **CHANGED on 61**; `output` and `children`
**unverifiable by construction on 61**, reported and never counted as
verified.
