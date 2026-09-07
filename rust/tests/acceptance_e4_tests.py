"""§1.1's hand enumeration: the 61 tests, as the locked document counts them.

A module of its own because `acceptance_e4.py` reached the repository's
800-line ceiling, and because this is DATA -- the one thing in the instrument
that is a transcription of the pre-registration rather than a protocol or a
parser. Keeping it here makes the transcription reviewable on its own and
`tests/test_acceptance_e4.py`'s derivation of the same table from the
BYTE-LOCKED document a check on one file rather than on a runner.

The runner must not parse prose while measuring, so the table is a constant;
the lock is what makes the constant trustworthy, and the test derives §1.1's
rows from the committed document and asserts them equal, row for row and in
order.

One row runs past this repository's usual column: the name
`a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics`
is 84 characters. It is NOT split across two string literals -- an implicitly
concatenated identifier that joined wrong would be invisible in a table whose
whole job is to be exact, and `--focus` takes the name whole.
"""

from __future__ import annotations

#: §1.1's hand enumeration, in §1.1's order: (`--test` target, the `fn`'s own
#: line, the bare qualname `--focus` takes). Published as a COMPARISON TARGET
#: under its own name and re-derived from the clone's sources in the
#: preflight; a mismatch is a REFUSAL, not a measurement against a table that
#: no longer describes the subject.
#:
#: The constant is retyped here rather than parsed at run time (the runner
#: must not read prose while measuring), and the lock is what makes the
#: constant trustworthy: `tests/test_acceptance_e4.py` derives the same table
#: from the BYTE-LOCKED document and asserts it equal, row for row.
TESTS = (
    # pager_codec_gate_test.rs -- 20
    ("pager_codec_gate_test", 65,
     "unmeasured_model_is_fail_closed_read_only_and_status_shows_null"),
    ("pager_codec_gate_test", 86,
     "unknown_model_mutating_verbs_is_false"),
    ("pager_codec_gate_test", 97,
     "stored_keep_gate_enables_mutating_verbs_and_populates_status"),
    ("pager_codec_gate_test", 117,
     "stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement"),
    ("pager_codec_gate_test", 132,
     "set_codec_gate_on_unknown_model_is_named"),
    ("pager_codec_gate_test", 156,
     "model_patch_codec_follows_the_attached_profiles_selection"),
    ("pager_codec_gate_test", 166,
     "model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown"),
    ("pager_codec_gate_test", 179,
     "model_codec_from_profile_separates_a_measured_selection_from_the_default"),
    ("pager_codec_gate_test", 215,
     "agent_task_policy_resolves_through_the_agents_model"),
    ("pager_codec_gate_test", 230,
     "agent_task_policy_is_none_for_an_unknown_agent"),
    ("pager_codec_gate_test", 240,
     "agent_task_policy_resolves_envelope_through_the_agents_model"),
    ("pager_codec_gate_test", 267,
     "journal_codec_fixture_round_trips_through_replay"),
    ("pager_codec_gate_test", 306,
     "journal_codec_fixture_round_trips_a_refuse_class_row"),
    ("pager_codec_gate_test", 381,
     "unmeasured_model_has_null_done_trust_and_null_refusal_gate"),
    ("pager_codec_gate_test", 398,
     "stored_gate_with_both_classes_clear_renders_done_trust_true"),
    ("pager_codec_gate_test", 422,
     "stored_gate_with_one_class_failing_renders_done_trust_false"),
    ("pager_codec_gate_test", 439,
     "set_refusal_gate_never_touches_mutating_verbs_or_codec_gate"),
    ("pager_codec_gate_test", 452,
     "set_refusal_gate_on_unknown_model_is_named"),
    ("pager_codec_gate_test", 466,
     "journal_codec_verdict_mixed_round_trips_through_replay"),
    ("pager_codec_gate_test", 503,
     "journal_codec_verdict_round_trips_through_replay"),
    # pager_obligation_test.rs -- 15
    ("pager_obligation_test", 58,
     "residency_refusal_is_pre_checked_and_never_touches_the_substrate"),
    ("pager_obligation_test", 120,
     "stale_image_digest_cold_starts_and_journals_degraded"),
    ("pager_obligation_test", 156,
     "corrupt_spilled_image_cold_starts_and_journals_degraded"),
    ("pager_obligation_test", 188,
     "suspend_resume_round_trips_the_kv_image_through_nvme"),
    ("pager_obligation_test", 223,
     "unmeasured_vram_journals_degraded_once_and_caps_residency_at_one"),
    ("pager_obligation_test", 250,
     "missing_stats_is_a_contract_violation_not_a_reply"),
    ("pager_obligation_test", 308,
     "unload_model_pages_out_holders_and_journals"),
    ("pager_obligation_test", 403,
     "image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context"),
    ("pager_obligation_test", 450,
     "a_transient_restore_failure_keeps_the_image_for_the_retry"),
    ("pager_obligation_test", 493,
     "an_aborted_eviction_is_journaled_not_left_orphaned"),
    ("pager_obligation_test", 537,
     "the_substrate_window_backstop_stays_a_refusal_across_the_boundary"),
    ("pager_obligation_test", 576,
     "a_pager_can_be_shared_across_threads"),
    ("pager_obligation_test", 588,
     "unknown_model_and_unknown_agent_are_named"),
    ("pager_obligation_test", 604,
     "agent_ids_are_unique_and_status_is_a_snapshot"),
    ("pager_obligation_test", 633,
     "a_model_with_no_admission_block_renders_none"),
    # pager_refusal_advice_test.rs -- 4
    ("pager_refusal_advice_test", 89,
     "the_refusal_advises_a_window_that_actually_places"),
    ("pager_refusal_advice_test", 133,
     "the_advice_never_exceeds_the_window_the_agent_already_had"),
    ("pager_refusal_advice_test", 163,
     "unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess"),
    ("pager_refusal_advice_test", 222,
     "the_journal_records_the_advice_alongside_the_refusal_arithmetic"),
    # pager_remove_agent_test.rs -- 4
    ("pager_remove_agent_test", 15,
     "remove_agent_destroys_context_and_forgets_the_agent"),
    ("pager_remove_agent_test", 48,
     "remove_agent_on_a_fresh_agent_is_not_an_error"),
    ("pager_remove_agent_test", 60,
     "remove_agent_on_unknown_id_is_named"),
    ("pager_remove_agent_test", 73,
     "remove_agent_journals_the_removal_with_its_reason"),
    # pager_reservation_test.rs -- 8
    ("pager_reservation_test", 78,
     "a_second_agents_reservation_not_just_its_kv_is_what_refuses_it"),
    ("pager_reservation_test", 224,
     "the_global_overhead_margin_is_subtracted_from_placement_too"),
    ("pager_reservation_test", 281,
     "status_reports_reserved_bytes_and_both_overhead_terms"),
    ("pager_reservation_test", 320,
     "eviction_credits_the_whole_reservation_back"),
    ("pager_reservation_test", 367,
     "a_vram_bound_window_is_placeable_item_7_regression"),
    ("pager_reservation_test", 437,
     "a_sibling_blind_automatic_window_still_refuses_item_7_third_half"),
    ("pager_reservation_test", 560,
     "recurrent_state_is_charged_per_context_and_reported"),
    ("pager_reservation_test", 603,
     "recurrent_state_binds_the_vram_term_of_the_window_law"),
    # pager_test.rs -- 4
    ("pager_test", 39,
     "eviction_under_pressure_saves_image_and_journals"),
    ("pager_test", 73,
     "the_eviction_story_is_journaled_in_order_with_a_faithful_prompt"),
    ("pager_test", 159,
     "oversized_prompt_is_refused_with_arithmetic_never_truncated"),
    ("pager_test", 181,
     "budget_exhaustion_refuses_before_the_call"),
    # pager_weights_test.rs -- 6
    ("pager_weights_test", 39,
     "loading_a_model_charges_its_weights_against_the_budget"),
    ("pager_weights_test", 87,
     "a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic"),
    ("pager_weights_test", 206,
     "unload_credits_the_weights_back"),
    ("pager_weights_test", 259,
     "status_reports_loaded_weights"),
    ("pager_weights_test", 289,
     "unmeasured_budget_refusal_detail_says_unmeasured_not_zero"),
    ("pager_weights_test", 332,
     "a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics"),
)

#: The seven `--test` targets, in §1.1's order, derived from the table so the
#: two cannot drift.
TARGETS = tuple(dict.fromkeys(t for t, _ln, _n in TESTS))

#: §1.2's gate: the expected-MATCH list is ALL 61.
GATE_N = len(TESTS)

#: Where the seven files live in the clone (§1.1: "the file is under
#: `crates/bloomery-daemon/tests/`"). A repo-relative fragment, joined onto
#: `SENSORIUM_BLOOMERY`; not a location.
TESTS_SUBDIR = ("crates", "bloomery-daemon", "tests")
