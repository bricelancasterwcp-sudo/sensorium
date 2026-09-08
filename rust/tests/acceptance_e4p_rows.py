#!/usr/bin/env python3
"""The 61 originals of E4′ §1.1, and §1.2's expected licence partition.

The one piece of DATA in this instrument: a transcription of the byte-locked
pre-registration, kept as a constant because a runner must not parse prose at
measurement time and because the LOCK is what makes a constant trustworthy.
`tests/test_acceptance_e4p.py` derives the same table out of the locked
document and asserts it equal, row for row and in order -- so a retyped digit
in a run id, or a name that drifted by one character, is caught in the suite
rather than by a refusal with a store already copied.

Every row is `(index, fn, target, run)`:

    index   §1.1's ordinal, 1..61, which is also the order the loop runs in
    fn      the `--focus` value: the bare qualname, unique workspace-wide
    target  the `--test` target the fn lives in, WITHOUT the `.rs`
    run     the original run id E4's pass 1 produced, which lives in the
            kept store and is copied into the fresh one by §1.3

Nothing here is ever a value an endpoint falls back to. §1.2's partition
below enters the record as a COMPARISON TARGET under its own name; a headline
that borrowed from it could not fail.
"""

from __future__ import annotations

#: §1.1's enumeration, in §1.1's order.
ROWS = (
    (1, "unmeasured_model_is_fail_closed_read_only_and_status_shows_null",
     "pager_codec_gate_test", "20260907-111144-33d30c"),
    (2, "unknown_model_mutating_verbs_is_false",
     "pager_codec_gate_test", "20260907-111145-e2c8e3"),
    (3, "stored_keep_gate_enables_mutating_verbs_and_populates_status",
     "pager_codec_gate_test", "20260907-111146-8497d7"),
    (4, "stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement",
     "pager_codec_gate_test", "20260907-111147-b2146f"),
    (5, "set_codec_gate_on_unknown_model_is_named",
     "pager_codec_gate_test", "20260907-111148-085b7a"),
    (6, "model_patch_codec_follows_the_attached_profiles_selection",
     "pager_codec_gate_test", "20260907-111149-82548c"),
    (7, "model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown",
     "pager_codec_gate_test", "20260907-111150-ab143a"),
    (8, "model_codec_from_profile_separates_a_measured_selection_from_the_default",
     "pager_codec_gate_test", "20260907-111151-71f89b"),
    (9, "agent_task_policy_resolves_through_the_agents_model",
     "pager_codec_gate_test", "20260907-111152-b19140"),
    (10, "agent_task_policy_is_none_for_an_unknown_agent",
     "pager_codec_gate_test", "20260907-111153-2fe948"),
    (11, "agent_task_policy_resolves_envelope_through_the_agents_model",
     "pager_codec_gate_test", "20260907-111154-de3ee9"),
    (12, "journal_codec_fixture_round_trips_through_replay",
     "pager_codec_gate_test", "20260907-111155-67ca55"),
    (13, "journal_codec_fixture_round_trips_a_refuse_class_row",
     "pager_codec_gate_test", "20260907-111156-d0c398"),
    (14, "unmeasured_model_has_null_done_trust_and_null_refusal_gate",
     "pager_codec_gate_test", "20260907-111157-3a93a9"),
    (15, "stored_gate_with_both_classes_clear_renders_done_trust_true",
     "pager_codec_gate_test", "20260907-111159-54c3a7"),
    (16, "stored_gate_with_one_class_failing_renders_done_trust_false",
     "pager_codec_gate_test", "20260907-111200-990b34"),
    (17, "set_refusal_gate_never_touches_mutating_verbs_or_codec_gate",
     "pager_codec_gate_test", "20260907-111201-ab997d"),
    (18, "set_refusal_gate_on_unknown_model_is_named",
     "pager_codec_gate_test", "20260907-111202-764f03"),
    (19, "journal_codec_verdict_mixed_round_trips_through_replay",
     "pager_codec_gate_test", "20260907-111203-8bd7b0"),
    (20, "journal_codec_verdict_round_trips_through_replay",
     "pager_codec_gate_test", "20260907-111204-4e635f"),
    (21, "residency_refusal_is_pre_checked_and_never_touches_the_substrate",
     "pager_obligation_test", "20260907-111206-be9b6d"),
    (22, "stale_image_digest_cold_starts_and_journals_degraded",
     "pager_obligation_test", "20260907-111207-7997d1"),
    (23, "corrupt_spilled_image_cold_starts_and_journals_degraded",
     "pager_obligation_test", "20260907-111208-7b34da"),
    (24, "suspend_resume_round_trips_the_kv_image_through_nvme",
     "pager_obligation_test", "20260907-111209-cf57f2"),
    (25, "unmeasured_vram_journals_degraded_once_and_caps_residency_at_one",
     "pager_obligation_test", "20260907-111210-de710a"),
    (26, "missing_stats_is_a_contract_violation_not_a_reply",
     "pager_obligation_test", "20260907-111211-ac01ef"),
    (27, "unload_model_pages_out_holders_and_journals",
     "pager_obligation_test", "20260907-111212-f190d4"),
    (28, "image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context",
     "pager_obligation_test", "20260907-111213-53bd85"),
    (29, "a_transient_restore_failure_keeps_the_image_for_the_retry",
     "pager_obligation_test", "20260907-111214-83522d"),
    (30, "an_aborted_eviction_is_journaled_not_left_orphaned",
     "pager_obligation_test", "20260907-111216-997b0b"),
    (31, "the_substrate_window_backstop_stays_a_refusal_across_the_boundary",
     "pager_obligation_test", "20260907-111217-bfe991"),
    (32, "a_pager_can_be_shared_across_threads",
     "pager_obligation_test", "20260907-111218-b37956"),
    (33, "unknown_model_and_unknown_agent_are_named",
     "pager_obligation_test", "20260907-111219-a4ad75"),
    (34, "agent_ids_are_unique_and_status_is_a_snapshot",
     "pager_obligation_test", "20260907-111220-6d9c78"),
    (35, "a_model_with_no_admission_block_renders_none",
     "pager_obligation_test", "20260907-111221-2070ee"),
    (36, "the_refusal_advises_a_window_that_actually_places",
     "pager_refusal_advice_test", "20260907-111222-5b7e4e"),
    (37, "the_advice_never_exceeds_the_window_the_agent_already_had",
     "pager_refusal_advice_test", "20260907-111224-baa1d5"),
    (38, "unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess",
     "pager_refusal_advice_test", "20260907-111225-5d21ce"),
    (39, "the_journal_records_the_advice_alongside_the_refusal_arithmetic",
     "pager_refusal_advice_test", "20260907-111226-12b15f"),
    (40, "remove_agent_destroys_context_and_forgets_the_agent",
     "pager_remove_agent_test", "20260907-111227-69395c"),
    (41, "remove_agent_on_a_fresh_agent_is_not_an_error",
     "pager_remove_agent_test", "20260907-111228-1b60c3"),
    (42, "remove_agent_on_unknown_id_is_named",
     "pager_remove_agent_test", "20260907-111229-7ecc9d"),
    (43, "remove_agent_journals_the_removal_with_its_reason",
     "pager_remove_agent_test", "20260907-111230-c3f27d"),
    (44, "a_second_agents_reservation_not_just_its_kv_is_what_refuses_it",
     "pager_reservation_test", "20260907-111232-be1ecb"),
    (45, "the_global_overhead_margin_is_subtracted_from_placement_too",
     "pager_reservation_test", "20260907-111233-d808f7"),
    (46, "status_reports_reserved_bytes_and_both_overhead_terms",
     "pager_reservation_test", "20260907-111234-77aca0"),
    (47, "eviction_credits_the_whole_reservation_back",
     "pager_reservation_test", "20260907-111235-5c41c0"),
    (48, "a_vram_bound_window_is_placeable_item_7_regression",
     "pager_reservation_test", "20260907-111236-78e563"),
    (49, "a_sibling_blind_automatic_window_still_refuses_item_7_third_half",
     "pager_reservation_test", "20260907-111237-889ce6"),
    (50, "recurrent_state_is_charged_per_context_and_reported",
     "pager_reservation_test", "20260907-111238-841017"),
    (51, "recurrent_state_binds_the_vram_term_of_the_window_law",
     "pager_reservation_test", "20260907-111240-16e1f6"),
    (52, "eviction_under_pressure_saves_image_and_journals",
     "pager_test", "20260907-111241-232c32"),
    (53, "the_eviction_story_is_journaled_in_order_with_a_faithful_prompt",
     "pager_test", "20260907-111242-246517"),
    (54, "oversized_prompt_is_refused_with_arithmetic_never_truncated",
     "pager_test", "20260907-111243-a3b48c"),
    (55, "budget_exhaustion_refuses_before_the_call",
     "pager_test", "20260907-111244-e71496"),
    (56, "loading_a_model_charges_its_weights_against_the_budget",
     "pager_weights_test", "20260907-111246-2e13b3"),
    (57, "a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic",
     "pager_weights_test", "20260907-111247-da8d66"),
    (58, "unload_credits_the_weights_back",
     "pager_weights_test", "20260907-111248-87cf0b"),
    (59, "status_reports_loaded_weights",
     "pager_weights_test", "20260907-111249-6b0bff"),
    (60, "unmeasured_budget_refusal_detail_says_unmeasured_not_zero",
     "pager_weights_test", "20260907-111250-092953"),
    (61, "a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics",
     "pager_weights_test", "20260907-111251-80be5a"),
)


#: The seven `--test` targets, in first-appearance order.
TARGETS = tuple(dict.fromkeys(t for _i, _n, t, _r in ROWS))

#: N. §1.1: "N stays 61 and nothing is excluded" -- `#[ignore]` 0 hits and
#: `#[should_panic]` 0 hits over the seven files, so no name above is skipped
#: by libtest and none is skipped here.
GATE_N = len(ROWS)

#: The `--focus` values and the original run ids, spelled once each.
NAMES = tuple(n for _i, n, _t, _r in ROWS)
RUNS = tuple(r for _i, _n, _t, r in ROWS)

#: §1.2, written first: **granted 57 of 61**, WITHHELD on exactly four, each
#: keyed to the count of the PROGRAM's own threads that keeps it withheld.
#: The counts are E4's measured ones minus the one harness thread -- 2-1 and
#: 5-1 -- and a WITHHELD reason that named the raw count instead (2, 5, 5, 5)
#: is H1's STOP, because it would mean the rule never fired even though the
#: word happened to be right.
EXPECTED_WITHHELD = {
    "a_pager_can_be_shared_across_threads": 1,
    "the_refusal_advises_a_window_that_actually_places": 4,
    "the_advice_never_exceeds_the_window_the_agent_already_had": 4,
    "the_journal_records_the_advice_alongside_the_refusal_arithmetic": 4,
}

#: The other 57. Derived rather than retyped: two hand-written lists of the
#: same partition can disagree, and the one that disagrees silently is the
#: one a gate reads.
EXPECTED_GRANTED = tuple(n for n in NAMES if n not in EXPECTED_WITHHELD)

#: §1.2: "Every one of the 61 pairs reports exactly 1 harness thread --
#: libtest's per-test thread -- on each side".
EXPECTED_HARNESS_THREADS = 1

#: §1.2's remaining numbers, so H2 and H3 have theirs first as well.
EXPECTED_MATCH = GATE_N
EXPECTED_PAIRS_OF_ONE = GATE_N
#: H3's second reading: E4 §1.1's greps found `Command::new` 0 hits over the
#: seven files, so none of the 61 spawns a process and R2's exclusion has
#: nothing to exclude here.
EXPECTED_EXCLUDED_CHILDREN = 0
#: H4: 61 focused keys under the census path, one per rebuild.
EXPECTED_SHIM_KEYS = GATE_N

__all__ = ["ROWS", "TARGETS", "GATE_N", "NAMES", "RUNS",
           "EXPECTED_WITHHELD", "EXPECTED_GRANTED",
           "EXPECTED_HARNESS_THREADS", "EXPECTED_MATCH",
           "EXPECTED_PAIRS_OF_ONE", "EXPECTED_EXCLUDED_CHILDREN",
           "EXPECTED_SHIM_KEYS"]
