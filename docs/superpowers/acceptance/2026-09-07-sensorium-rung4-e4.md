# Rung-4 acceptance, `refocus` on a Rust pair — E4 (H1–H7)

The record of whether `sensorium refocus` re-runs a recorded `cargo sensorium`
command under an added focus, finds the pair it produced, and issues the
comparator's verdict on it — measured on all 61 `#[test]` functions of the
seven `pager_*_test.rs` files of a workspace nobody wrote it for, one test at
a time under `--exact`.

**The pre-registration this record measures** is row E4 of the Rust recorder
design, written into that plan before the first line of the transformer
(`docs/superpowers/specs/2026-09-01-sensorium-rust-recorder-design.md`, §13,
line 1019):

> | E4 | `refocus` MATCH rate on the 7 `pager_*_test.rs` FakeSubstrate files, per test with `--exact`, expected-MATCH list written first | tier call → full | a MATCH on the expected list only; an unexpected DIVERGED is a finding | not measured (rung 4) |

The binding design for the mechanism under test is
`docs/superpowers/specs/2026-09-07-sensorium-rung4-refocus-design.md` (rulings
G1–G3; §2.3 defines the pre-rerun refusals, the re-run argv and the pair
lookup; §3.1 the verdict; §3.2 the licence and its two UNVERIFIABLE checks;
§4 this pre-registration in prose). The reading rules for a `dbg` capture and
for a LINE's `deltas` are slice 1's
(`docs/superpowers/specs/2026-09-06-sensorium-rung4-focus-tier-design.md`
§3.1/§3.2/§4.2). Nothing here amends either design, and nothing here re-runs
or re-classifies an earlier record: the rung-4 focus-tier acceptance
(`2026-09-06-sensorium-rung4-e9.md`), the rung-3 borrow-repair acceptance
(`2026-09-05-sensorium-rung3-e6q.md`) and the rung-4 entry-grain records stand
exactly as written and no number in them is re-measured.

**§1 is byte-locked, and it is committed ALONE.** It is committed before the
driver can parse a `--refocus-of`, before the converter can write a
`refocus_of` key, before Python has a Rust branch in `refocus`, and before
`rust/tests/acceptance_e4.py` exists — so no value below was chosen after
seeing an instrument behave. The lock is `awk '/^## 1/,/^## 2/' | sha256sum`;
the runner refuses to start unless the range is byte-identical to the commit
that locked it, and refuses outright while no lock sha is set. §1 references
no footnote, so the extended lock range and the `awk` range are the same
bytes.

**The subject is a workspace this project did not write.** The bloomery clone
at `e209ed9` (`e209ed9b00f7eef647fb31d0b0895a5ad3b90807`, porcelain empty when
§1 was written) is read-only for the whole run; its HEAD, porcelain and
`Cargo.lock` are recorded before and after. Every number §1 pre-registers
below — the 61 names and their lines, the expected-MATCH list, the three
`watch` triples — was hand-derived from that source at `e209ed9`, with the
derivation written beside it, before any instrument could produce a competing
number.

**A completed measurement is never re-rolled, and a miss is a STOP with its
number.** Measured once.

## 1. Pre-registration

**The two argv forms, verbatim.** Pass 1 records the original; pass 2 asks the
reader to re-run it under an added focus. `<file>` is one of the seven
`--test` targets and `<name>` is the test function's bare qualname:

| pass | argv |
|---|---|
| 1 | `cargo sensorium test -p bloomery-daemon --test <file> -- <name> --exact` |
| 2 | `sensorium refocus <run> --focus <name>` |

Pass 1 is unfocused: no `--focus` and no `--tier`, so the driver's default
tier `call` applies and `capabilities.line` is false on the original. The bare
`--` separates the driver's own flags from cargo's, and `<name> --exact` is
libtest's, so exactly one test runs and the invocation produces exactly one
runner process. Under `--test <file>` the invocation is single-target, which
is what §2.3's `invocation_processes` refusal requires. The runner spells
`cargo sensorium` as the built binary invoked as `cargo-sensorium sensorium
…` (E9 §2's practice); the argv after the `sensorium` subcommand is the text
above, unchanged.

Pass 2's focus value is the test function's **bare qualname**. Every one of
the 61 is a top-level `fn` in an integration-test file — column 0, no
enclosing inline `mod`; the only `mod` in any of the seven is the bodiless
declaration `mod common;`, which pushes no scope over the items that follow
it — so `qualname` returns the bare item name
(`rust/sensorium-transform/src/visit.rs`, `qualname` returns `name.to_owned()`
when `self.scope.is_empty()`), with no `crate::` prefix, no crate name and no
file path. §1.1 records that all 61 names are unique workspace-wide as `fn`
definitions, so no `--focus` value below is ambiguous.

The CLI re-invokes the driver itself: `sensorium refocus` builds
`[driver, "--refocus-of", <run>, "--focus", <name>, *cargo_args]` and runs it
from `workspace_root` under the same store (design §2.3). Nothing parsed from
the driver's stdout is load-bearing; the pair is found by `refocus_of` in the
store.

| Id | Question | Operation | Endpoint (both readings pre-committed) | Source |
|---|---|---|---|---|
| H1 | does every original refocus without a pre-rerun refusal? | For each of the 61 originals, pass 2. Read the CLI's own exit and stdout: a pre-rerun refusal is exit **2** with a `REFUSED: …; nothing was re-run` sentence from design §2.3's table. | **0 of 61 pre-rerun refusals** — each original is a single-target invocation, so `invocation_processes == 1`, `workspace_root` is present and still exists, no `--window` is given and the driver is on the runner's `SENSORIUM_CARGO_SENSORIUM`. Second reading, on the count that can move independently: **61 of 61 invocations reached the driver**, i.e. 61 child launches observed, none short-circuited before launch. Any refusal is recorded with its verbatim sentence and its `run`. | Design §2.3's refusal table; the CLI's stdout and exit per test. |
| H2 | does every re-run complete? | The driver child's exit status and cargo's own outcome for each of the 61 pass-2 invocations. | **61 of 61 complete.** A **focused build failure is a STOP** (the compile-limitation class; the §3.3 guard is in this slice) — no fallback to an unfocused build, no retry under a narrower focus, no skipped test: the run stops and the pattern that failed is the finding. Second reading: beside the driver's exit, each re-run's libtest summary counts equal the original's (1 passed, 0 failed). | The driver child's exit and streamed stderr per test; each run's libtest summary. |
| H3 | MATCH on the expected list? | `diff_cmd.compare(orig, new)` through `refocus`, on the pair found by `refocus_of`. | **61 of 61 MATCH**, the expected-MATCH list of §1.2 — the gate. An unexpected **DIVERGED is a finding**, recorded with the divergent event (the E4 row's own reading), **not a STOP**. A **REFUSED after the rerun is a STOP** (the instrument or the pairing, not the subject). Second reading of the same answer: the verdict word `refocus` prints, and beside it the exit it returns (MATCH 0 / DIVERGED 1 / REFUSED 3); a disagreement between word and exit is itself a finding and is reported as one. §1.2 pre-registers three tests whose DIVERGED would be the hazard §1.2 names rather than a recorder finding; every other DIVERGED is the finding H3 means. | The store (the pair by `refocus_of`); the CLI's printed verdict and exit. |
| H4 | what does the licence say? | The licence block `refocus` prints after each verdict, and the `refocus_licence*` stamps in the NEW trace's meta. | **REPORTED, no gate.** Expected: source **verified 61 of 61** and environment **verified 61 of 61** (both run for real: `source_hashes` re-hashed now, `env` compared between the two traces); output and children **UNVERIFIABLE 61 of 61**, each printing its caveat (`output: unverifiable (not recorded)`, the same for children) — `capabilities.output` and `capabilities.children` are false on a Rust trace, and the honest reading is that the check could not run, never that it passed. Second reading, and the rule that binds it: an UNVERIFIABLE check is **never counted as verified** in any total this record prints; the verified count and the unverifiable count are printed as two separate numbers and never summed. | The CLI's licence block per test; `meta` stamps in each NEW trace. |
| H5 | does the loop close? | The three `watch` triples of §1.3, each on the NEW (refocused) trace named there. | **All three as predicted → PASS.** Each prediction is two pre-committed readings of one answer: the verdict class `watch` prints (`SATISFIED` / `not satisfied` / `NOTHING WAS CHECKED` / `error: no recorded code matches`) and the exit it returns (0 / 1 / 3). A disagreement between the two is itself a finding about `Verdict`/`STATUS`, reported as such and never resolved silently in favour of either. | §1.3, derived from the clone's source at `e209ed9` under slice-1 design §4.2. |
| H6 | what does it cost? | Per pass-2 invocation: the whole `refocus` wall, and cargo's own build time inside it. Then, at the end, a census of the shim directory under the fresh target. | **REPORTED, no gate.** First reading: the invocation wall per refocus, with **the first focus distinguished from the later ones** (the first pays for the rt build; the later ones pay for a fresh shim and the matched units). Second reading: cargo's own reported build time inside each. Beside them: the shim census — the count of entries under `<CARGO_TARGET_DIR>/sensorium/shim/*` and their total bytes, measured once at the end. | The runner's own timing per invocation; `<target>/sensorium/shim/*` (`rust/cargo-sensorium/src/rt_build.rs:207–211`). |
| H7 | did nothing else move? | This repository, not the clone: the corpus collector over every case (the three new Rust cases of design §3.4 included), the whole Python suite, and `cargo test --workspace`. | **Every corpus case equal**; Python suite green; Rust workspace green. Second reading: per-case equality of printed answers, and beside it each suite's exit status. | Parent §8 E6/E7, unchanged; design §3.4's three new cases. |

### 1.1 The 61 tests — the hand enumeration, file by file

Enumerated from the clone at `e209ed9`. Each row is one `#[test]` attribute
and the `fn` on the line after it; the line given is the `fn`'s own line, and
the file is under `crates/bloomery-daemon/tests/`. The seven counts are
20 / 15 / 4 / 4 / 8 / 4 / 6 = **61**.

**`pager_codec_gate_test.rs` — 20**

| line | fn |
|---|---|
| 65 | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` |
| 86 | `unknown_model_mutating_verbs_is_false` |
| 97 | `stored_keep_gate_enables_mutating_verbs_and_populates_status` |
| 117 | `stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement` |
| 132 | `set_codec_gate_on_unknown_model_is_named` |
| 156 | `model_patch_codec_follows_the_attached_profiles_selection` |
| 166 | `model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown` |
| 179 | `model_codec_from_profile_separates_a_measured_selection_from_the_default` |
| 215 | `agent_task_policy_resolves_through_the_agents_model` |
| 230 | `agent_task_policy_is_none_for_an_unknown_agent` |
| 240 | `agent_task_policy_resolves_envelope_through_the_agents_model` |
| 267 | `journal_codec_fixture_round_trips_through_replay` |
| 306 | `journal_codec_fixture_round_trips_a_refuse_class_row` |
| 381 | `unmeasured_model_has_null_done_trust_and_null_refusal_gate` |
| 398 | `stored_gate_with_both_classes_clear_renders_done_trust_true` |
| 422 | `stored_gate_with_one_class_failing_renders_done_trust_false` |
| 439 | `set_refusal_gate_never_touches_mutating_verbs_or_codec_gate` |
| 452 | `set_refusal_gate_on_unknown_model_is_named` |
| 466 | `journal_codec_verdict_mixed_round_trips_through_replay` |
| 503 | `journal_codec_verdict_round_trips_through_replay` |

**`pager_obligation_test.rs` — 15**

| line | fn |
|---|---|
| 58 | `residency_refusal_is_pre_checked_and_never_touches_the_substrate` |
| 120 | `stale_image_digest_cold_starts_and_journals_degraded` |
| 156 | `corrupt_spilled_image_cold_starts_and_journals_degraded` |
| 188 | `suspend_resume_round_trips_the_kv_image_through_nvme` |
| 223 | `unmeasured_vram_journals_degraded_once_and_caps_residency_at_one` |
| 250 | `missing_stats_is_a_contract_violation_not_a_reply` |
| 308 | `unload_model_pages_out_holders_and_journals` |
| 403 | `image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context` |
| 450 | `a_transient_restore_failure_keeps_the_image_for_the_retry` |
| 493 | `an_aborted_eviction_is_journaled_not_left_orphaned` |
| 537 | `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` |
| 576 | `a_pager_can_be_shared_across_threads` |
| 588 | `unknown_model_and_unknown_agent_are_named` |
| 604 | `agent_ids_are_unique_and_status_is_a_snapshot` |
| 633 | `a_model_with_no_admission_block_renders_none` |

**`pager_refusal_advice_test.rs` — 4**

| line | fn |
|---|---|
| 89 | `the_refusal_advises_a_window_that_actually_places` |
| 133 | `the_advice_never_exceeds_the_window_the_agent_already_had` |
| 163 | `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` |
| 222 | `the_journal_records_the_advice_alongside_the_refusal_arithmetic` |

**`pager_remove_agent_test.rs` — 4**

| line | fn |
|---|---|
| 15 | `remove_agent_destroys_context_and_forgets_the_agent` |
| 48 | `remove_agent_on_a_fresh_agent_is_not_an_error` |
| 60 | `remove_agent_on_unknown_id_is_named` |
| 73 | `remove_agent_journals_the_removal_with_its_reason` |

**`pager_reservation_test.rs` — 8**

| line | fn |
|---|---|
| 78 | `a_second_agents_reservation_not_just_its_kv_is_what_refuses_it` |
| 224 | `the_global_overhead_margin_is_subtracted_from_placement_too` |
| 281 | `status_reports_reserved_bytes_and_both_overhead_terms` |
| 320 | `eviction_credits_the_whole_reservation_back` |
| 367 | `a_vram_bound_window_is_placeable_item_7_regression` |
| 437 | `a_sibling_blind_automatic_window_still_refuses_item_7_third_half` |
| 560 | `recurrent_state_is_charged_per_context_and_reported` |
| 603 | `recurrent_state_binds_the_vram_term_of_the_window_law` |

**`pager_test.rs` — 4**

| line | fn |
|---|---|
| 39 | `eviction_under_pressure_saves_image_and_journals` |
| 73 | `the_eviction_story_is_journaled_in_order_with_a_faithful_prompt` |
| 159 | `oversized_prompt_is_refused_with_arithmetic_never_truncated` |
| 181 | `budget_exhaustion_refuses_before_the_call` |

**`pager_weights_test.rs` — 6**

| line | fn |
|---|---|
| 39 | `loading_a_model_charges_its_weights_against_the_budget` |
| 87 | `a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic` |
| 206 | `unload_credits_the_weights_back` |
| 259 | `status_reports_loaded_weights` |
| 289 | `unmeasured_budget_refusal_detail_says_unmeasured_not_zero` |
| 332 | `a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics` |

**`#[ignore]`: none, so nothing is excluded and N stays 61.** `grep -n
'#\[ignore\]'` over the seven files returns **0 lines**, and `#[should_panic]`
returns 0 as well. The check matters because libtest's `--exact <name>` does
**not** run an ignored test unless `--ignored` is also given: an ignored test
would be pre-registered here as EXCLUDED with its reason and N would drop by
one. There is no such test, so **N = 61** and every name above is measured.

**No test exits the process, spawns a child, or reads stdin — stated, not
assumed.** Over the seven files and `tests/common/*.rs`: `Command::new` **0
hits**; `std::process::exit` **0 hits**; `stdin` **0 hits**. The 28 hits of
`std::process` are all types and identifiers — `std::process::id()`,
`ExitStatus`, `Output` — never `exit`. Two behaviours the greps *did* find and
that §1.2 reads rather than hides: one spawned **thread** in
`pager_obligation_test.rs:582`, and a **TCP-served fixture** with four worker
threads used by three tests of `pager_refusal_advice_test.rs`.

### 1.2 The expected-MATCH list, written first

**The expected-MATCH list is all 61** — every name enumerated in §1.1, in
every one of the seven files. The gate for H3 is 61 of 61 MATCH.

**The thread-spawning test is on the list, named, with its reasoning.**
`a_pager_can_be_shared_across_threads` (`pager_obligation_test.rs:576`) spawns
exactly one thread (line 582, `std::thread::spawn(move ||
shared.lock().unwrap().status().agents.len())`) and joins it on line 584. A
spawned thread is a **task with its own fingerprint** under the per-task basis
(design §3.1), and the join is deterministic: one thread, one closure body,
one `status()` call, one `join()` whose value is asserted. So the task
multiset is the same on both sides and the pair MATCHes. It is named here so
that a DIVERGED on it reads against this reasoning rather than against a
guess.

**Why a value cannot move a verdict, which is what licenses "all".** The
fingerprint is a rolling blake2b-16 over `file \x1f qualname \x1f kind \n` per
causal event and **nothing else** —
`rust/cargo-sensorium/src/convert/fingerprint.rs:34–43`, whose four unit tests
pin it against the Python hashes. No argument, no return value, no local and
no LINE row enters the hash (design §3.1). A run-varying *value* — a
directory name, an ephemeral port, a pid — therefore cannot produce a
DIVERGED. Only a run-varying **sequence of calls** can.

**The survey, re-run for this record, with its counts.** Patterns over the
seven files (and, where noted, `tests/common/*.rs`):

| survey | pattern | hits in the seven | reading |
|---|---|---|---|
| clock | `SystemTime\|Instant\|now()\|elapsed(` | **0** | 6 hits exist in `tests/common/{drift,memory,refalsify}.rs`; none of the seven imports those modules — the `use common::…` lines are `common::pager` (six files), `common::pager_weights` (one), `common::http` (one) — so no test above calls them |
| randomness | `rand\|uuid\|random`, case-insensitive | **0** (and 0 in `tests/common/*.rs`) | no random identifier or value anywhere in the material |
| brace-delimited macro | `[A-Za-z_][A-Za-z_0-9]*!\s*\{` | **0** | the §3.3 guard's pattern does not occur at all, in tail position or anywhere else; the seven functions whose body ends in a block-like tail all end in a `match`, not a macro |
| inference-variable head | `let (mut )?x = (Vec::new\|HashMap::new\|HashSet::new\|BTreeMap::new\|Default::default\|None)` | **0** | the declared inference-variable limitation is not exercised |
| unascribed `.collect()` | `\.collect\(\)` | 4 hits → **0 unascribed** | all four are `let ids: Vec<String> = …` (`pager_refusal_advice_test.rs:93,137,226`; `pager_obligation_test.rs:609`), so the head type is written, not inferred |
| unascribed `.parse()`/`.into()`/`.try_into()` binding | `let x = ….(parse\|into\|try_into)()` | **0** | same |
| child process / stdin / exit | `Command::new`, `stdin`, `std::process::exit` | **0** each | §1.1 |

**Two survey facts the design's prose states more simply than the source
does, corrected here rather than silently.**

1. **`fresh_dir` is not one function.** Six of the seven files import
   `common::pager::fresh_dir` (`tests/common/pager.rs:65`), which is the
   fixed-name-and-remove form the design describes — `temp_dir().join(name)`
   with a name unique per test, so it reclaims its predecessor's directory
   and is safe under `--exact` one test at a time. **`pager_refusal_advice_test.rs`
   defines its own** `fresh_dir` at line 60, which suffixes with
   `std::process::id()` and a process-wide `AtomicU64` counter, so its
   directory name **differs between the two runs of a pair**. It is used by
   exactly one test, `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess`
   (line 164). Reading, pre-registered: the differing name **cannot** move the
   verdict, because the fingerprint hashes no values; that test stays on the
   expected-MATCH list. What the fact does bind is §1.3 — **no `watch` or
   `--value` prediction in this record is derived from that file**, and §1.3
   derives none.

2. **Three tests drive a real TCP server with four worker threads, and that is
   a named hazard.** `the_refusal_advises_a_window_that_actually_places` (89),
   `the_advice_never_exceeds_the_window_the_agent_already_had` (133) and
   `the_journal_records_the_advice_alongside_the_refusal_arithmetic` (222)
   each call `bloomery_daemon::test_support::serve_fake()` (lines 90, 134,
   223), which binds an ephemeral port and spawns `WORKER_COUNT = 4`
   (`crates/bloomery-daemon/src/http.rs:35`) worker threads that all pull
   requests off **one shared** `tiny_http` server
   (`crates/bloomery-daemon/src/http.rs:193–204`). Each test then drives about
   ten HTTP requests over the loopback. **Which worker services which request
   is the OS scheduler's decision, not the program's** — so the four worker
   tasks' per-task fingerprints depend on how the ten requests happened to
   split, and two runs can legitimately split them differently. The port and
   directory names cannot move a verdict (no value is hashed); the *split*
   can, because it changes each worker task's sequence of calls. The
   comparator softens this but does not remove it: `compare_tasks` compares
   tasks as an **order-independent multiset** of `(name, hash)`
   (`src/sensorium/query/diff_cmd.py`), so a split of (6, 4, 0, 0) matches
   another (6, 4, 0, 0) whichever worker got which, and only a different
   *partition* — (7, 3, 0, 0) against (6, 4, 0, 0) — diverges.

   **The reading, pre-committed.** These three stay on the expected-MATCH
   list, so the H3 gate remains **61 of 61**. A DIVERGED confined to exactly
   these three named tests is a **MISS of the gate that this section already
   accounts for**: it is recorded with its divergent event and its task
   multisets, and diagnosed as the subject's scheduler nondeterminism named
   here — **not** as a finding about the recorder, the comparator or the
   re-run path. A DIVERGED on **any other** test is the finding H3 means, with
   no prior explanation available to it. The fourth test of that file,
   `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` (163),
   drives `FakeSubstrate` directly with no server and carries no such hazard.

**No other exception is pre-registered.** With the two facts above stated, the
survey finds no clock, no randomness, no macro-tail, no inference-variable
head and no process boundary anywhere in the 61.

### 1.3 The three `watch` triples for H5

Each triple runs against a **NEW (refocused) trace** produced by pass 2, never
against an original — an original is unfocused and `watch` on it is a
capability refusal, which is E9's H1 and is not re-measured here. The `--at`
spec is the bare qualname in every case, with no `module:` prefix; §1.1
records that every name is unique workspace-wide.

W1 and W3 are E9's, taken from `2026-09-06-sensorium-rung4-e9.md` §1.2 with
their `--at`, `--expr` and source line unchanged, and run here on the NEW
trace of `missing_stats_is_a_contract_violation_not_a_reply` (design §4's H5).
W4 is this record's own, from a different file, derived below.

| # | NEW trace (the refocused run of) | `--at` | `--expr` | predicted class | exit | line |
|---|---|---|---|---|---|---|
| W1 | `missing_stats_is_a_contract_violation_not_a_reply` | `missing_stats_is_a_contract_violation_not_a_reply` | `dir == "/tmp/bloomery-pager-contract"` | **SATISFIED** | **0** | 251 |
| W3 | `missing_stats_is_a_contract_violation_not_a_reply` | `pager_with_model` | `dir == "/tmp/bloomery-pager-contract"` | **`error: no recorded code matches --at 'pager_with_model'`** | **1** | — |
| W4 | `remove_agent_on_unknown_id_is_named` | `remove_agent_on_unknown_id_is_named` | `dir == "/tmp/bloomery-pager-remove-unknown"` | **SATISFIED** | **0** | 61 |

**W1's derivation** is E9 §1.2's, unchanged, and E9's own H4 measured it
SATISFIED at exit 0. Line 251 of `pager_obligation_test.rs` is `let dir =
fresh_dir("bloomery-pager-contract");`; `common::pager::fresh_dir`
(`tests/common/pager.rs:65`) returns `std::env::temp_dir().join(name)`, and
with `TMPDIR` unset `temp_dir()` is `/tmp`, so `dir` is the `PathBuf`
`/tmp/bloomery-pager-contract`, whose `Debug` is the quoted string
`"/tmp/bloomery-pager-contract"` — 30 bytes, well inside the 200-byte cap, so
`trunc` is false. Slice-1 design §4.2 resolves a `dbg` capture to the literal
its text parses as and a quoted string to its unquoted value, so the
comparison is true at line 251's LINE and, through `watch`'s forward fold, at
every later site of the frame. Sites that cannot evaluate `dir` — the CALL row
(Rust CALL rows carry no args) and the parameters LINE at 250, which precedes
the binding — appear as a caveat above the verdict and change neither the
class nor the exit. Hits and not-captured counts are reported, not predicted.
**What this triple proves about *this* slice:** the refocused trace produced
by the re-run path carries LINE rows and their deltas, so the loop closes on a
trace the reader itself asked for.

**W3's derivation, and the one token that necessarily differs from E9's.** In
E9, W3 ran against F2 — the trace of the whole `pager_codec_gate_test` binary
— where `pager_with_model` is a real frame binding `dir` to a
`bloomery-codec-gate-…` path, so every evaluating site evaluated **false**:
`not satisfied`, exit 1. Here the design puts W3 on the NEW trace of
`missing_stats_is_a_contract_violation_not_a_reply`, and that trace records
**only** the `pager_obligation_test` binary running `--exact
missing_stats_is_a_contract_violation_not_a_reply`. `pager_with_model` is
defined in `pager_codec_gate_test.rs`, a **different test binary**, which this
invocation never builds into the run and never executes. So no recorded code
object matches `--at pager_with_model`, `watch` takes its `_no_match` branch
(`src/sensorium/query/watch_cmd.py:546–563, 594–595`), prints `error: no
recorded code matches --at 'pager_with_model'` followed by what the trace does
hold, and returns `NEGATIVE` = **1** (`src/sensorium/exit.py:12`).

Both readings are pre-committed, and they are deliberately split because they
do not both carry over from E9. **The exit is the gate: 1, byte-identical to
E9's W3.** **The printed class is reported, and it is `error: no recorded code
matches`, not E9's `not satisfied`** — the one token that necessarily differs,
because the subject is a single-test binary rather than a whole-file one. The
control's *role* is preserved exactly: the same literal that must be
SATISFIED in W1 must not be satisfiable here, and `watch` must say so by
refusing to find a frame rather than by inventing one. Pre-registering E9's
`not satisfied` verbatim would have been pre-registering a prediction
derivably false from the source, which this record does not do.

**W4's derivation** — the third triple, from a different file, chosen for
certainty. `remove_agent_on_unknown_id_is_named`
(`pager_remove_agent_test.rs:60`) is the whole test:

```
60  fn remove_agent_on_unknown_id_is_named() {
61      let dir = fresh_dir("bloomery-pager-remove-unknown");
62      let (mut p, _, _) = pager_in(&dir, 0, Some(10u64.pow(9)));
63      match p.remove_agent("nope", "test teardown") {
64          Err(PagerError::UnknownAgent(id)) => assert_eq!(id, "nope"),
65          other => panic!("expected UnknownAgent, got {other:?}"),
66      }
67  }
```

The file imports `fresh_dir` from `common::pager` (line 9), which is the
**fixed-name** form — not `pager_refusal_advice_test.rs`'s pid-suffixed one —
so line 61 binds `dir` to the `PathBuf` `/tmp/bloomery-pager-remove-unknown`
with `TMPDIR` unset, whose `Debug` is the quoted string
`"/tmp/bloomery-pager-remove-unknown"`: 36 bytes, inside the 200-byte cap, so
`trunc` is false and the capture is an untruncated `dbg`. This is the
**quoted-string branch** of slice-1 design §4.2 — the same branch E9's W1 and
W3 exercise and the same branch E9 measured — read on a file E9 never touched.
The comparison is true at line 61's LINE and at every later site of the frame
through the forward fold; the CALL row and the parameters LINE at 60 (the fn
takes no parameters, so its deltas are empty) cannot evaluate `dir` and appear
as a caveat that changes neither class nor exit. Predicted: **SATISFIED, exit
0.**

**Neither this file nor the obligation file binds an integer or a bool in the
focused frames, and §1 says so rather than pretending otherwise.**
`remove_agent_on_unknown_id_is_named` binds `dir` and `p` — a path and an
opaque struct. The integer and bool branches of §4.2 are pinned by the corpus
(`focus_let_chain`'s `b == 2`, `focus_loop_counter`'s `flow --value 3`) and by
design §3.4's new `refocus_match` case, which is the printing gate for them;
E4 is the re-run path's claim under a real workspace, and this workspace has
no integers in these frames to claim about. The unevaluable-`len` branch is
E9's W2 and is not re-measured here.

### 1.4 Lens, and the kill criteria

**Lens for every endpoint.** The reader is this repository's `.venv` Python
running `python -m sensorium` at the branch HEAD §2 records, and the rules it
reads by are the designs', not this document's: a `dbg` capture is read under
slice-1 §4.2, a LINE and its deltas under slice-1 §3.1/§3.2, the verdict under
this slice's §3.1 (per-task fingerprints over CALL, RETURN, RAISE and HANDLED;
LINE rows never enter the hash), the licence under §3.2, and every refusal
sentence under §2.3. The driver is `cargo-sensorium` **built by the runner
from this branch's HEAD at measurement time**, with the commit, the
`built_from` result and the binary's sha256 recorded in §2 before and after —
the pre-repair-binary trap of the E6⁗ record is why the runner builds it
rather than trusting a path.

**Versions, and the rule for reading a version token.** The slice puts
`cargo-sensorium` at **0.5.0**, `sensorium-transform` at **0.4.1**,
`sensorium-rt` at **0.4.0** (unchanged) and Python `sensorium` at **0.8.4**
(**0.8.3** if the Python bump has not landed when the run happens — §2 records
which). Those are expectations, not gates. **Every version token that appears
inside a sentence this record checks is read from the trace's own
`meta.recorder` (and the reader's own reported version), never hard-coded
here**, and §2 records what each actually was; a sentence is compared with
§2's recorded token substituted.

**Locations — the only box-local paths this record names, all fresh, all
under `/mnt/extra/sensorium-rung2/`.**

| what | value |
|---|---|
| trace store — FRESH and empty at the start | `SENSORIUM_DIR=/mnt/extra/sensorium-rung2/sensorium-dir/e4` |
| cargo target for the 61 pairs — FRESH | `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/bloomery-target-e4` |
| H7's corpus target — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e4-corpus` |
| the clone under measurement — READ-ONLY | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| the shim census | `<CARGO_TARGET_DIR>/sensorium/shim/*` — entry count and total bytes, measured once at the end |

Both fresh locations are named in §2 with their state at the start. The clone
is read-only for the whole run: HEAD, porcelain and `Cargo.lock` sha256 are
recorded **before and after** and the lock is restored to the pin if it moved
(a `cargo` invocation may touch it; §2 says whether it did and that it was
restored). The runner never writes into the clone by any other means, and pass
1 and pass 2 both run with cwd = the clone's workspace root, which is what
`workspace_root` records and what §2.3's re-run uses.

**`SENSORIUM_TIER` is left at its default `call`** for every pass-1 recording:
the coarse tier is not touched, and the focus tier is a compile-time decision,
so an original and its refocused pair differ only by the added `--focus`. Pass
2 inherits the original's recorded tier through §2.3's argv rule, which for an
unset `SENSORIUM_TIER` means the flag is omitted and the driver's default
`call` applies again.

**The invocation audit log is NOT silenced**: `SENSORIUM_NO_INVOCATION_LOG` is
unset, so every reader invocation this record makes is itself logged into the
store, and §2 records the row count at the end.

**`TMPDIR` is observed, and the reading is pre-registered.** With `TMPDIR`
unset, `std::env::temp_dir()` is `/tmp` and the `fresh_dir` names are
`<temp_dir>/<fixed name>`, which is what makes W1's and W4's literals
derivable at all. §2 records `TMPDIR` as observed; if it is set at measurement
time, W1 and W4 read against `<TMPDIR>/bloomery-pager-contract` and
`<TMPDIR>/bloomery-pager-remove-unknown` instead — the same predictions with
the prefix substituted — and §2 states which reading was taken. W3's
prediction does not depend on `TMPDIR` at all.

**The pair rule.** A pass-2 verdict is read only from a pair the store itself
identifies: exactly **one** trace whose `refocus_of == <run>` and whose
recording started **after** that invocation's launch timestamp. Zero or more
than one is a REFUSED by count, never a guess, and — per H3 — a REFUSED after
the rerun is a STOP. The driver's `run:` lines are recorded in the report and
decide nothing.

**The reading rule for the licence.** Source and environment run for real and
are counted as verified or not verified. Output and children are
**UNVERIFIABLE by construction** on a Rust pair — `capabilities.output` and
`capabilities.children` are false, so there is nothing to compare — and are
**reported, never counted as verified** and never summed into a verified
total. A licence line that said "verified" for either would be the named bug
class, and this record would report it as a finding rather than as a pass.

**Every row above carries both its readings**, pre-committed here; where a
row's two readings disagree the disagreement is the finding and is reported as
one, never resolved silently in favour of the friendlier number. **Every
measurement is `{value, n, lens, dropped}`**: a `null` value with a reason is
the only not-measured, `0` is measured-and-zero, and no endpoint is ever
filled from an expectation — the predictions above are in the room, and a
headline that borrowed from one could not fail. Loads at every phase's start
are recorded. Nothing is gated on a wall.

**Kill criteria.**

1. **A focused build failure is a STOP** (H2): the compile-limitation class.
   Not a fallback to an unfocused build, not a retry under a narrower focus,
   not a skipped test — the run stops, and the pattern that failed is the
   finding.
2. **A REFUSED after the rerun is a STOP** (H3): the instrument or the
   pairing, not the subject. A pre-rerun refusal is not this — it is H1's
   number, recorded with its verbatim sentence.
3. **A `.FAILED` marker before any number has been read is infrastructure.**
   The run is archived, the fresh locations are emptied, and it is relaunched
   from zero.
4. **A `.FAILED` marker after any number has been read is a STOP.** The
   numbers already read stand.
5. **Measured once.** No endpoint is re-rolled and no completed measurement is
   re-run under a kinder command. A miss is recorded with its number.
6. **A reader at its ceiling is the record.** Where a reader's own limit
   (a page, a cap, a truncation) bounds what an endpoint can see, that is
   published as the endpoint's lens and the cell goes null with its reason
   rather than being filled from a smaller view.

**Bounds.** The loop runs detached (`setsid nohup`) with a pid file and a
`.DONE`/`.FAILED` marker carrying `exit=<n>`; nothing below is read before the
marker exists. **The whole loop is bounded at 2 hours**, **each `cargo
sensorium` invocation at 1800 s**, and **each `sensorium refocus` invocation at
1800 s**. A bound reached is a `.FAILED` and is read under rules 3 and 4
above.

**Reported without a gate**: H4's four licence counts; H6's per-refocus walls
with the first focus distinguished from the later ones, cargo's own build time
inside each, and the shim census (count and bytes); the pass-1 and pass-2 trace
sizes; the store's size and the disk free before and after; the invocation-log
row count; and, for each of the three `watch` triples, the sites / evaluated /
hits / not-captured / errors counts beside the gated class and exit.

**Amended 2026-09-07, before the instrument exists — the lens, not the
endpoints (ruling R-H1, after Task 0's review).** (1) *Scope of the
survey.* §1.2's "no clock anywhere" reads over the seven test files and
`tests/common/*.rs`, not over the instrumented crate the 61 also record;
that crate has clock sites, and the one on every test's path
(`Pager::new`'s clock closure, read at `pager.rs:854`) stores a value and
branches on nothing, while the clock-branching scheduler lives in
`pager_timeshare_test.rs`, which is not one of the seven. No verdict can
move on it. (2) *A discriminator for the three-test hazard.* A DIVERGED on
`pager_refusal_advice_test`'s three server tests is read as the named
scheduler hazard only when both hold: the total causal event count over
the four worker tasks is the same in both traces (a different partition of
the same total) and the MAIN stream's fingerprint MATCHes; otherwise it is
H3's finding like any other. (3) The `.collect()` citations name the
ascription heads (93, 137, 226; 609); the tokens sit two lines later (95,
139, 228; 611). The 61 names, the expected-MATCH list, every endpoint and
every reading are unchanged; the runner carries both shas.

## 2. Environment

Measured 2026-09-07T11:11:36-0500 → 2026-09-07T11:23:04-0500 by `rust/tests/acceptance_e4.py`, launched detached; the raw facts it recorded are `results-e4-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-07-sensorium-rung4-e4.results.json`, which `acceptance_e4_schema.assemble_e4` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless the locked range is byte-identical to the commit that locked it — and refuses outright while no lock sha is set. The range is awk '/^## 1/,/^## 2/' PLUS the definition of every footnote §1 references (`footnotes_in_range` = none). Checked at `413f601`: 34583 bytes, sha256 `09d2f8da30f6e216fb07e97c27481d35d0c285e40c2bccb9295e0ef07863ff42` on both sides — identical: yes.

**Both locks.** §1 was committed ALONE at the ORIGINAL lock `8e7d837` (33378 bytes, sha256 `87abc779ea3acf867e07a0055d92de6281b4fd5571aaadb48998ac7d9afe18c4`), and was then amended once — after that lock and before the instrument existed (ruling R-H1) — to state the survey's scope, to give §1.2's three-test hazard a DISCRIMINATOR, and to correct the `.collect()` citation lines. Amended: yes (+1205 bytes). Both shas are recorded here, and no endpoint, method, derivation or table row moved: every `|` row of the locked range is byte-identical at the two commits (`tests/test_acceptance_e4.py`).

| Pin | Value |
|---|---|
| repo HEAD at the run | `3ac8ec7a251e93f905267647c1498eb59590ddd3` (branch `feat/rung4-refocus`) |
| the clone under measurement (READ-ONLY input) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; §1.4's pin `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; porcelain before / after empty / empty; HEAD after `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| the seven test files | `/mnt/extra/sensorium-rung2/bloomery/crates/bloomery-daemon/tests` — §1.1's 61 names re-derived from them in the preflight and compared row for row |
| the clone's `Cargo.lock` | sha256 `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` before, `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` after (moved: no); restored to the pin: yes |
| driver — BUILT by the runner from HEAD | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` (debug profile), `cargo build -p cargo-sensorium` exit 0 in 0.025 s from HEAD `3ac8ec7a251e93f905267647c1498eb59590ddd3`; rebuilt: no |
| driver sha256 | `54e6027817c241bc52260e66e21ac4bc384b6d135c4001a7adcb682d7f9acb0e` before, `54e6027817c241bc52260e66e21ac4bc384b6d135c4001a7adcb682d7f9acb0e` after — unchanged: yes |
| version tokens — READ FROM THE TRACE, never from the instrument | recorder `sensorium-rt 0.4.0`, driver `cargo-sensorium 0.5.0`, fingerprint basis `per-task` (from run `20260907-111144-33d30c`); reader sensorium 0.6.0 |
| trace store — FRESH and empty at the start | `/mnt/extra/sensorium-rung2/sensorium-dir/e4` |
| cargo target for the 61 pairs — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e4` |
| H7's corpus target — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e4-corpus` (named by `SENSORIUM_CORPUS_TARGET`: no) |
| Rust workspace target (H7's `cargo test --workspace`) | `/mnt/extra/sensorium-rung2/rust-target` |
| ceilings | 1800 s per `cargo sensorium`, 1800 s per `sensorium refocus`, 7200 s for the whole loop |
| `TMPDIR` as observed | None — TMPDIR was unset, so `std::env::temp_dir()` is `/tmp` and W1 and W4 read as §1.3 derives them |
| `SENSORIUM_TIER` | unset -- §1.4 leaves the coarse tier at its default `call` for every pass-1 recording, so an original and its refocused pair differ only by the added `--focus` |
| the invocation audit log | NOT silenced: SENSORIUM_NO_INVOCATION_LOG is unset, so every reader call this record makes appends a row to the store's `invocations.jsonl`, and the count is recorded at the end — rows in the store afterwards: 64 |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| repo porcelain before / after | empty / empty |
| 1-minute load at the start | 2.16 |
| disk free, repo filesystem, before / after | 7.15 GB / 7.1 GB |
| disk free, target filesystem, before / after | 85.61 GB / 59.52 GB |

**Log locations.** Every command's log is under `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-07-sensorium-rung4-refocus/acceptance-e4/logs`, one subdirectory per phase (`built-from`, `pass1`, `pass2`, `h5`, `h7`), one file per invocation.

1-minute load at each phase's start: pass1 2.15, pass2 2.62, H1 4.33, H2 4.33, H3 4.33, H4 4.33, H5 4.33, H6 4.33, H7 4.33.

**Preflight, by hand, before the launch.**

| check | value |
|---|---|
| `pgrep -a cargo` / `pgrep -a rustc` | both empty (exit 1) — nothing waited for, nothing killed |
| repo | `git status --porcelain` empty at `3ac8ec7a251e93f905267647c1498eb59590ddd3`, branch `feat/rung4-refocus` |
| the three FRESH locations | all three **absent** — the E4 target, the derived corpus target, the store; the runner made them |
| the clone | HEAD `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`, porcelain empty (0 lines), `Cargo.lock` sha256 `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` |
| disk | target filesystem 80 GB free (the runner refuses below 8); root/repo filesystem **6.7 GB** (floor 3) — the runner writes only under the target filesystem and the ledger, and the pager tests' `fresh_dir` under `/tmp` is small; after the run the root filesystem still read 6.7 GB free by `df -h` (7.15 → 7.1 GB by the runner's own finer reading) |
| `TMPDIR` | unset |
| driver sha256 BEFORE the runner's own in-place build | `54e6027817c241bc52260e66e21ac4bc384b6d135c4001a7adcb682d7f9acb0e`, and the same after the hand rebuild — `cargo build -p cargo-sensorium` finished in 0.10 s with nothing to compile, as expected from Tasks 3–5 touching no Rust |
| 1-minute load | 1.62 |
| reader | `.venv/bin/python` → Python 3.14.4 |
| §1 sha (`awk '/^## 1/,/^## 2/' \| sha256sum`) | `09d2f8da30f6e216fb07e97c27481d35d0c285e40c2bccb9295e0ef07863ff42` — the amended lock `413f601`'s, and the same value after every edit of this record |
| whole Python suite, WITHOUT the driver env | exit 0, **1590 passed, 12 skipped in 65.5 s** |

**The suite twice, and the driver once.** The pre-launch gate above ran under no `SENSORIUM_*` variable and read 1590/12; H7 runs the same suite with `SENSORIUM_CARGO_SENSORIUM` set and read **1601 passed, 1 skipped** — 1602 collected both times, the 11 tests that skip without a built driver running there. The runner built the driver from HEAD in place (`cargo build -p cargo-sensorium`, debug, exit 0 in 0.025 s, `rebuilt: false`) and its sha256 `54e6027817c2…cb0e` is the same by hand before the launch, in `built_from` before and after that build, and in `cleanup.driver_sha256_after` after H7's `cargo test --workspace`, which shares that target (`driver_unchanged: true`).

**The launcher, checked before use and unchanged.** Its exports are exactly the five keys the runner refuses without (`SENSORIUM_DRIVER`, `SENSORIUM_BLOOMERY`, `SENSORIUM_E4_TARGET`, `SENSORIUM_DIR`, `SENSORIUM_RUST_TARGET`) plus `SENSORIUM_CARGO_SENSORIUM`, which is how the CLI resolves the driver, and `PYTHONDONTWRITEBYTECODE`; it `unset TMPDIR`s, the reading §1.3 derives W1 and W4 from; and it does not set `SENSORIUM_CORPUS_TARGET`, so H7's corpus target is the derived `<E4 target>-corpus` (`corpus_target_from_env: false`). Nothing in it was changed.

**One launch, and it measured this record.** Launched once, detached, at 2026-09-07T11:11:36-0500 by `setsid nohup bash <ledger>/acceptance-e4/launch.sh`, stdout and stderr redirected to `<ledger>/acceptance-e4/logs/e4.log`, runner pid 3706918; it wrote `e4.DONE` carrying `exit=0` at 11:23:04 — **11 min 28 s**, against a 2-hour loop bound and a 2 h 45 min operator bound. It was polled with `ps -p` on the pid file and the two marker names in bounded 60 s loops (the marker appeared in the second bounded call), and **nothing was read before that marker existed**: not the log, not the raw record, not `results.json`, not the store. Nothing was killed, `pkill` was never used, and there is no `failed-launch-*` directory beside this record — §1.4's kills 3 and 4 were never exercised. `stop`, `refused` and `error` in `results.json` are all `null`, `bound_reached` is `null`, and all **36** `{value, n, lens, dropped}` cells carry a value: **0 nulls, 0 dropped reasons**.

**What this run wrote.** The store ended at 47 897 981 bytes over **122** traces (61 originals + 61 refocused) and **64** rows in `invocations.jsonl` — 61 refocuses plus H5's three `watch` calls, the audit log deliberately un-silenced (§1.4). The E4 target ended at 25 849 233 464 bytes and the corpus target at 757 136 422; the target filesystem went 85.61 → 59.52 GB free, the repo filesystem 7.15 → 7.10 GB. The clone's `Cargo.lock` did not move (`clone_cargo_lock_moved: false`, `clone_cargo_lock_back_on_the_pin: true`), its HEAD and porcelain are the pin's before and after, and `absent_after_the_run` is empty. §1.1's 61 names were re-derived from the clone's sources in the preflight and matched the locked table row for row **and in order**.

## 3. Results

The gate of each row, and both readings where §1 pre-committed two. A `null` is not-measured with its reason; `0` is a measured zero. All **36** measurement cells carry a value: 0 nulls, 0 dropped reasons. The seven `###` blocks the renderer emits are reflowed here into one table with the endpoint named per row; no cell, number, `n` or lens was changed or removed.

| Ep | Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|---|
| H1 | pre-rerun refusals (the gate: 0) | 0 | 61 | FIRST reading, and the gate: pre-rerun refusals, of the invocations made -- the gate is 0, because each origin… | none |
| H1 | invocations that reached the driver (2nd reading) | 61 | 61 | SECOND reading, on the count that can move independently: invocations whose driver child was LAUNCHED, read fr… | none |
| H1 | exit-2 answers carrying no §2.3 sentence | 0 | 61 | exit-2 answers carrying NO §2.3 sentence: the CLI refusing the CALL rather than the design's pre-rerun gate, w… | none |
| H2 | re-runs that completed (the gate: 61) | 61 | 61 | FIRST reading, and the gate: re-runs that COMPLETED, of the re-runs made; each re-run's own output: a libtest … | none |
| H2 | focused BUILD failures (§1's kill 1 — a STOP) | 0 | 61 | focused BUILD failures -- the child launched and no libtest summary was printed. §1's kill 1 makes any a STOP:… | none |
| H2 | re-runs whose libtest counts equal the original's (2nd reading) | 61 | 61 | SECOND reading: re-runs whose summed libtest passed/failed/ignored/measured/filtered counts equal the original… | none |
| H2 | pairs where a summary line could not be read | 0 | 61 | pairs where one side printed no summary at all, so `equal` is `None` rather than `False`: an unparsed outcome … | none |
| H3 | MATCH verdicts (THE GATE: 61 of 61) | 61 | 61 | THE GATE: MATCH verdicts, of the pairs compared; §1.2's expected-MATCH list is all 61; `diff_cmd.compare(orig,… | none |
| H3 | DIVERGED verdicts | 0 | 61 | DIVERGED verdicts, of the pairs -- a finding, not a STOP, recorded with its divergent event | none |
| H3 | … reading as §1.2's named hazard (§1.4's discriminator) | 0 | 61 | DIVERGED on one of §1.2's three server tests where §1.4's DISCRIMINATOR holds -- the total causal event count … | none |
| H3 | … reading as H3's finding | 0 | 61 | DIVERGED that §1.4's discriminator does NOT excuse: the finding H3 means, with no prior explanation available … | none |
| H3 | REFUSED after the rerun (§1's kill 2 — a STOP) | 0 | 61 | REFUSED AFTER the rerun -- §1's kill 2, a STOP: the instrument or the pairing, not the subject | none |
| H3 | verdict word and exit disagreeing (2nd reading) | 0 | 61 | SECOND reading: pairs where the printed verdict word and the returned exit (MATCH 0 / DIVERGED 1 / REFUSED 3) … | none |
| H4 | SOURCE verified | 61 | 61 | SOURCE verified: the original's `source_hashes` re-hashed now and unchanged by content, of the pairs; the lice… | none |
| H4 | ENVIRONMENT verified | 61 | 61 | ENVIRONMENT verified: the two traces' recorded `env` compared and unchanged (the recorder's own variables name… | none |
| H4 | EXIT verified | 61 | 61 | EXIT verified: the re-run ended the same way as the original, read off the printed `exit: rerun <a>   original… | none |
| H4 | OUTPUT — unverifiable (never counted as verified) | 61 | 61 | OUTPUT: `unverifiable (not recorded)` -- `capabilities.output` is false on a Rust trace, so the check could no… | none |
| H4 | CHILDREN — unverifiable (never counted as verified) | 61 | 61 | CHILDREN: `unverifiable (not witnessed)` -- `capabilities.children` is false, so the check could not run. REPO… | none |
| H4 | licences granted | 0 | 61 | licences GRANTED, of the pairs; a WITHHELD one lists its caveats and is counted separately | none |
| H4 | licence lines claiming an unverifiable check (gate: 0) | 0 | 61 | licence lines that CLAIM an unverifiable check as verified -- the named bug class; the gate is 0 and any is a … | none |
| H5 | triples as predicted ON THEIR OWN GATE | 3 | 3 | THE GATE: triples as §1.3 predicts them ON THEIR OWN GATE -- W1 and W4 on both readings, W3 on the exit; §1.3'… | none |
| H5 | verdict classes as predicted (1st reading) | 3 | 3 | FIRST reading: verdict classes as predicted (SATISFIED / SATISFIED / `error: no recorded code matches`) | none |
| H5 | exit statuses as predicted (2nd reading) | 3 | 3 | SECOND reading: exit statuses as predicted (0 / 0 / 1) | none |
| H5 | triples where class and exit disagree | 0 | 3 | triples where the class and the exit do not agree -- itself a finding about `Verdict`/`STATUS` | none |
| H6 | the FIRST focus's wall, s (1st reading) | 6.661 | 1 | REPORTED, NOT GATED. FIRST reading: the wall of the FIRST `sensorium refocus` invocation, seconds; the runner'… | none |
| H6 | later focuses' mean wall, s | 6.988 | 60 | the mean wall of the LATER focuses, seconds, of the later invocations | none |
| H6 | the slowest later focus, s | 7.467 | 60 | the slowest later focus, seconds | none |
| H6 | entries under `<target>/sensorium/shim/*` | 62 | None | entries under `<CARGO_TARGET_DIR>/sensorium/shim/*`, counted once at the end (`rt_build.rs:207-211`); `null` i… | none |
| H6 | bytes under `<target>/sensorium/shim/*` | 2506729440 | 62 | total bytes under the shim directory, of its entries | none |
| H7 | corpus questions whose answer is not the expectation | 0 | 135 | FIRST reading: corpus questions whose printed answer is not the case's registered expectation, of the question… | none |
| H7 | the collector's exit status (2nd reading) | 0 | 61 | SECOND reading: the collector's exit status, of the cases it ran -- 0 is every case equal | none |
| H7 | harness errors | 0 | 61 | harness errors -- a case that crashed the collector answered nothing and is not a pass | none |
| H7 | cases the collector SKIPPED (gate: 0) | 0 | 61 | cases the collector SKIPPED, of the cases -- `run_corpus` skips a cargo case when it can find no driver and st… | none |
| H7 | `pytest -q` exit status | 0 | None | `pytest -q` exit status -- 0 is green | none |
| H7 | the suite's summary line | 1601 passed, 1 skipped in 112.88s (0:01:52) | None | the suite's own summary line, recorded whole | none |
| H7 | `cargo test --workspace` exit status | 0 | 40 | `cargo test --workspace` exit status, of its `test result:` lines | none |

**Each endpoint's rule, verbatim from §1, and its own extras.**

* **H1** — does every original refocus without a pre-rerun refusal? 0 of 61 pre-rerun refusals; 61 of 61 invocations reached the driver. `refusals` [], `did_not_reach_the_driver` [].
* **H2** — does every re-run complete? 61 of 61 re-runs complete; a focused BUILD failure is a STOP. `failed_tests` [], `unequal_tests` [], and `build_failure_caveat` is `null` — the caveat that names what the build-failure class cannot tell apart renders only when there is a failure to disambiguate.
* **H3** — MATCH on the expected list? 61 of 61 MATCH (the gate); an unexpected DIVERGED is a finding, a REFUSED after the rerun is a STOP. `diverged_tests` [], `unclassified` [], `divergent_events` {}; the §1.4 discriminator was never asked (`reported.discriminator` is `{}`), because nothing diverged.
* **H4** — what does the licence say? REPORTED, no gate: source and environment verified 61 of 61; output and children UNVERIFIABLE 61 of 61, never summed with the verified counts. Withheld: 61; `no_licence_line` []. The endpoint's own reading, verbatim: *the verified counts and the unverifiable counts are two numbers and are never summed: a check that could not run is never counted as one that passed.*
* **H5** — does the loop close? All three triples as predicted on their own gates — W1 and W4 on both readings, W3 on the exit (§1.3).
* **H6** — what does it cost? Reported, not gated. Pass 1 total 74.741 s; pass 2 total 425.927 s.
* **H7** — did nothing else move? Every corpus case equal; the Python suite green; the Rust workspace green. Corpus 61 cases / 135 questions, failures none, skipped none; `cargo test --workspace` over 40 `test result: ok.` lines; phase walls corpus 60.251 s, pytest 113.213 s, cargo 11.864 s.

| # | NEW trace of | `--at` | gate | predicted | class | exit | sites / evaluated / hits / not-captured / errors |
|---|---|---|---|---|---|---|---|
| W1 | `missing_stats_is_a_contract_violation_not_a_reply` | `missing_stats_is_a_contract_violation_not_a_reply` | class and exit | SATISFIED / 0 | SATISFIED | 0 | 27 / 25 / 25 / 2 / 0 |
| W3 | `missing_stats_is_a_contract_violation_not_a_reply` | `pager_with_model` | exit | no recorded code matches / 1 | no recorded code matches | 1 | None / None / None / None / None |
| W4 | `remove_agent_on_unknown_id_is_named` | `remove_agent_on_unknown_id_is_named` | class and exit | SATISFIED / 0 | SATISFIED | 0 | 5 / 3 / 3 / 2 / 0 |

### The 61 pairs

Every row read the same four values, so they are stated once instead of
sixty-one times: **verdict MATCH, exit 0, licence WITHHELD, discriminator
class — (never asked: no DIVERGED).** What varies is the pair, two pairs
to a row:

| # | test | original → refocused | # | test | original → refocused |
|---|---|---|---|---|---|
| 1 | `unmeasured_model_is_fail_closed_read_only_and_status_shows_null` | 20260907-111144-33d30c → 20260907-111258-4a1b6e | 2 | `unknown_model_mutating_verbs_is_false` | 20260907-111145-e2c8e3 → 20260907-111305-1680c8 |
| 3 | `stored_keep_gate_enables_mutating_verbs_and_populates_status` | 20260907-111146-8497d7 → 20260907-111311-3650bc | 4 | `stored_demote_gate_disables_mutating_verbs_but_is_still_a_measurement` | 20260907-111147-b2146f → 20260907-111318-d003b8 |
| 5 | `set_codec_gate_on_unknown_model_is_named` | 20260907-111148-085b7a → 20260907-111325-c4e214 | 6 | `model_patch_codec_follows_the_attached_profiles_selection` | 20260907-111149-82548c → 20260907-111332-e74e68 |
| 7 | `model_patch_codec_defaults_search_replace_when_unprofiled_or_unknown` | 20260907-111150-ab143a → 20260907-111338-7ed788 | 8 | `model_codec_from_profile_separates_a_measured_selection_from_the_default` | 20260907-111151-71f89b → 20260907-111345-f7444d |
| 9 | `agent_task_policy_resolves_through_the_agents_model` | 20260907-111152-b19140 → 20260907-111352-facf7d | 10 | `agent_task_policy_is_none_for_an_unknown_agent` | 20260907-111153-2fe948 → 20260907-111359-8ad1b5 |
| 11 | `agent_task_policy_resolves_envelope_through_the_agents_model` | 20260907-111154-de3ee9 → 20260907-111406-da79b9 | 12 | `journal_codec_fixture_round_trips_through_replay` | 20260907-111155-67ca55 → 20260907-111413-c41a05 |
| 13 | `journal_codec_fixture_round_trips_a_refuse_class_row` | 20260907-111156-d0c398 → 20260907-111420-89cab5 | 14 | `unmeasured_model_has_null_done_trust_and_null_refusal_gate` | 20260907-111157-3a93a9 → 20260907-111426-6a5f5e |
| 15 | `stored_gate_with_both_classes_clear_renders_done_trust_true` | 20260907-111159-54c3a7 → 20260907-111433-23c569 | 16 | `stored_gate_with_one_class_failing_renders_done_trust_false` | 20260907-111200-990b34 → 20260907-111440-8be944 |
| 17 | `set_refusal_gate_never_touches_mutating_verbs_or_codec_gate` | 20260907-111201-ab997d → 20260907-111447-7b117b | 18 | `set_refusal_gate_on_unknown_model_is_named` | 20260907-111202-764f03 → 20260907-111454-73acd6 |
| 19 | `journal_codec_verdict_mixed_round_trips_through_replay` | 20260907-111203-8bd7b0 → 20260907-111501-971703 | 20 | `journal_codec_verdict_round_trips_through_replay` | 20260907-111204-4e635f → 20260907-111508-5c5ec7 |
| 21 | `residency_refusal_is_pre_checked_and_never_touches_the_substrate` | 20260907-111206-be9b6d → 20260907-111515-4bf631 | 22 | `stale_image_digest_cold_starts_and_journals_degraded` | 20260907-111207-7997d1 → 20260907-111523-db5e3f |
| 23 | `corrupt_spilled_image_cold_starts_and_journals_degraded` | 20260907-111208-7b34da → 20260907-111530-aedd49 | 24 | `suspend_resume_round_trips_the_kv_image_through_nvme` | 20260907-111209-cf57f2 → 20260907-111536-9f9e1c |
| 25 | `unmeasured_vram_journals_degraded_once_and_caps_residency_at_one` | 20260907-111210-de710a → 20260907-111543-93ab3e | 26 | `missing_stats_is_a_contract_violation_not_a_reply` | 20260907-111211-ac01ef → 20260907-111551-252cb2 |
| 27 | `unload_model_pages_out_holders_and_journals` | 20260907-111212-f190d4 → 20260907-111558-eaf88f | 28 | `image_rejected_for_size_mismatch_cold_starts_on_a_fresh_context` | 20260907-111213-53bd85 → 20260907-111605-c6b17c |
| 29 | `a_transient_restore_failure_keeps_the_image_for_the_retry` | 20260907-111214-83522d → 20260907-111612-124c85 | 30 | `an_aborted_eviction_is_journaled_not_left_orphaned` | 20260907-111216-997b0b → 20260907-111619-973316 |
| 31 | `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` | 20260907-111217-bfe991 → 20260907-111626-9a0554 | 32 | `a_pager_can_be_shared_across_threads` | 20260907-111218-b37956 → 20260907-111633-405705 |
| 33 | `unknown_model_and_unknown_agent_are_named` | 20260907-111219-a4ad75 → 20260907-111640-deb114 | 34 | `agent_ids_are_unique_and_status_is_a_snapshot` | 20260907-111220-6d9c78 → 20260907-111647-b6ebca |
| 35 | `a_model_with_no_admission_block_renders_none` | 20260907-111221-2070ee → 20260907-111655-5b98b7 | 36 | `the_refusal_advises_a_window_that_actually_places` | 20260907-111222-5b7e4e → 20260907-111702-ddc253 |
| 37 | `the_advice_never_exceeds_the_window_the_agent_already_had` | 20260907-111224-baa1d5 → 20260907-111709-f3795d | 38 | `unmeasured_vram_advises_nothing_rather_than_a_byte_derived_guess` | 20260907-111225-5d21ce → 20260907-111716-1d74ab |
| 39 | `the_journal_records_the_advice_alongside_the_refusal_arithmetic` | 20260907-111226-12b15f → 20260907-111723-e55b4b | 40 | `remove_agent_destroys_context_and_forgets_the_agent` | 20260907-111227-69395c → 20260907-111729-506e2e |
| 41 | `remove_agent_on_a_fresh_agent_is_not_an_error` | 20260907-111228-1b60c3 → 20260907-111736-87adfc | 42 | `remove_agent_on_unknown_id_is_named` | 20260907-111229-7ecc9d → 20260907-111743-9bca63 |
| 43 | `remove_agent_journals_the_removal_with_its_reason` | 20260907-111230-c3f27d → 20260907-111750-95e2f2 | 44 | `a_second_agents_reservation_not_just_its_kv_is_what_refuses_it` | 20260907-111232-be1ecb → 20260907-111757-de6846 |
| 45 | `the_global_overhead_margin_is_subtracted_from_placement_too` | 20260907-111233-d808f7 → 20260907-111804-09c12a | 46 | `status_reports_reserved_bytes_and_both_overhead_terms` | 20260907-111234-77aca0 → 20260907-111811-4402d8 |
| 47 | `eviction_credits_the_whole_reservation_back` | 20260907-111235-5c41c0 → 20260907-111818-1742d7 | 48 | `a_vram_bound_window_is_placeable_item_7_regression` | 20260907-111236-78e563 → 20260907-111825-76925e |
| 49 | `a_sibling_blind_automatic_window_still_refuses_item_7_third_half` | 20260907-111237-889ce6 → 20260907-111832-28f563 | 50 | `recurrent_state_is_charged_per_context_and_reported` | 20260907-111238-841017 → 20260907-111839-45cb50 |
| 51 | `recurrent_state_binds_the_vram_term_of_the_window_law` | 20260907-111240-16e1f6 → 20260907-111846-f1450b | 52 | `eviction_under_pressure_saves_image_and_journals` | 20260907-111241-232c32 → 20260907-111853-ea6978 |
| 53 | `the_eviction_story_is_journaled_in_order_with_a_faithful_prompt` | 20260907-111242-246517 → 20260907-111900-6d88f8 | 54 | `oversized_prompt_is_refused_with_arithmetic_never_truncated` | 20260907-111243-a3b48c → 20260907-111908-2c79af |
| 55 | `budget_exhaustion_refuses_before_the_call` | 20260907-111244-e71496 → 20260907-111915-c8c02c | 56 | `loading_a_model_charges_its_weights_against_the_budget` | 20260907-111246-2e13b3 → 20260907-111922-e37f70 |
| 57 | `a_second_models_weights_that_cannot_fit_are_refused_with_the_arithmetic` | 20260907-111247-da8d66 → 20260907-111930-32d059 | 58 | `unload_credits_the_weights_back` | 20260907-111248-87cf0b → 20260907-111937-51b522 |
| 59 | `status_reports_loaded_weights` | 20260907-111249-6b0bff → 20260907-111944-ef8db1 | 60 | `unmeasured_budget_refusal_detail_says_unmeasured_not_zero` | 20260907-111250-092953 → 20260907-111951-04c63e |
| 61 | `a_budget_smaller_than_already_loaded_weights_saturates_to_zero_free_and_never_panics` | 20260907-111251-80be5a → 20260907-111958-4083af | | | |

### Reported without a gate — §1.4

| what | value |
|---|---|
| the first focus | {'name': 'unmeasured_model_is_fail_closed_read_only_and_status_shows_null', 'wall_s': 6.661, 'cargo_finished_s': [3.47]} |
| later focuses, min / mean / max s | 6.571 / 6.988 / 7.467 |
| pass 1 total / pass 2 total, s | 74.741 / 425.927 |
| cargo's own build time reported for | 61 re-run(s) |
| shim census | 62 entries, 2506729440 bytes under `<CARGO_TARGET_DIR>/sensorium/shim` |
| invocation-log rows at the end | 64 |
| store bytes / traces recorded | 47897981 / 122 |
| E4 target bytes / corpus target bytes | 25849233464 / 757136422 |
| pass 1 measured / n | 61 / 61 |
| pass 2 measured / n | 61 / 61 |
| invocations killed at the ceiling | pass 1 [], pass 2 [] |
| invocations never run (the 2-hour bound) | pass 1 [], pass 2 [] |
| originals with more than one process | [] |
| pair-rule refusals | [] |

## 4. Verdicts

Written by hand against §1's rules, from `results.json` and the raw record and its logs in the gitignored plan ledger. One row per §1 endpoint, with the number that decided it and — where §1 pre-committed two readings — both. Launched ONCE, detached, 11:11:36 → 11:23:04 on 2026-09-07, and measured once: nothing was re-run, re-scoped or re-classified after a number was read, no `--focus` was narrowed, no unfocused fallback was taken, there is exactly one `e4.DONE` at `exit=0` and no `failed-launch-*` beside it, and §1 was not touched — its sha256 is `09d2f8da30f6e216fb07e97c27481d35d0c285e40c2bccb9295e0ef07863ff42` before and after (§2), at the amended lock `413f601`. **The assembly is deterministic.** The file committed HERE is a RE-assembly (`assembled.at` 11:25:30) of the same untouched raw record; the run's own is what `e4.log` records (`assembled.at` 11:23:04). Their leaf-path diff over **8770** leaf paths is exactly ONE path, `.assembled.at`; `section-2-3.md` re-rendered byte-identical; the raw record's md5 `5dc0bd83c408c1cd9b89ba775f6676f8` is unchanged before and after.

| Id | §1's rule, verbatim | What was measured (both readings) | Verdict |
|---|---|---|---|
| H1 | "**0 of 61 pre-rerun refusals** … Second reading … **61 of 61 invocations reached the driver**." | **0** pre-rerun refusals of 61 — no exit-2 answer carried a design §2.3 sentence, and `refusals` is empty. Second reading: **61 of 61** invocations reached the driver, counted from the `--- rerunning …` banner the CLI prints immediately before it launches the child, not from the exit. The third cell, exit-2 answers carrying no §2.3 sentence (the CLI refusing the CALL), is **0 of 61**. | **PASS** |
| H2 | "**61 of 61 complete.** A **focused build failure is a STOP** … Second reading: … each re-run's libtest summary counts equal the original's." | **61 of 61** re-runs completed, each printing a libtest `test result:` line; **0** focused build failures, so §1's kill 1 never fired and `build_failure_caveat` is `null`. Second reading: **61 of 61** re-runs' summed libtest passed/failed/ignored/measured/filtered counts equal the original's (`1 passed; 0 failed; 0 ignored; 0 measured; N filtered out` on both sides), with **0** pairs where a summary could not be read. | **PASS** |
| H3 | "**61 of 61 MATCH**, the expected-MATCH list of §1.2 — the gate. An unexpected **DIVERGED is a finding** … A **REFUSED after the rerun is a STOP**." | **61 of 61 MATCH** on the pair the store itself identified by `refocus_of` + launch timestamp (`pair_n` 1 on every row, `pair-rule refusals` []). **0** DIVERGED — so **0** reading as §1.2's named hazard and **0** reading as H3's finding — and **0** REFUSED, so kill 2 never fired. Second reading: the printed verdict word is `MATCH` on all 61 and the returned exit is `0` on all 61, with **0** word/exit disagreements. | **PASS** |
| H4 | "**REPORTED, no gate.** … source **verified 61 of 61** and environment **verified 61 of 61** … output and children **UNVERIFIABLE 61 of 61** … an UNVERIFIABLE check is **never counted as verified**." | Source **61 of 61** verified (`source: unchanged`, ~~85 files re-hashed by content~~ **corrected 2026-09-07, fix round 1 (§5.7): 85 files on 60 of the pairs and 80 on `the_substrate_window_backstop_stays_a_refusal_across_the_boundary`** — the 61 of 61 verified count is unaffected either way), environment **61 of 61** (`env: unchanged`, 104 variables compared, the recorder's own named and excluded), exit **61 of 61** (`exit: rerun 0   original 0`). Output **61 of 61 UNVERIFIABLE** and children **61 of 61 UNVERIFIABLE**, in their own cells, never summed with the verified counts; **0** licence lines claimed an unverifiable check as verified. The printed licence WORD was **WITHHELD on all 61** and `licences granted` is **0** — §5.2. | **REPORTED** (no gate) |
| H5 | "**All three as predicted → PASS.** Each prediction is two pre-committed readings … the verdict class … and the exit …" | **3 of 3** triples as predicted on their own gates. W1 `SATISFIED` / exit **0** (27 sites, 25 evaluated, 25 hits, 2 not-captured, 0 errors); W3 `error: no recorded code matches --at 'pager_with_model'` / exit **1**, gated on the exit alone with its class REPORTED (§1.3); W4 `SATISFIED` / exit **0** (5 / 3 / 3 / 2 / 0). Both readings agree on all three (`class_as_predicted` 3, `exit_as_predicted` 3), so **0** triples disagree and the `Verdict`/`STATUS` finding §1 reserved a place for has nothing to report. | **PASS** |
| H6 | "**REPORTED, no gate.** First reading: the invocation wall per refocus, with **the first focus distinguished from the later ones** … Second reading: cargo's own reported build time inside each." | First reading: the first focus **6.661 s**; the 60 later focuses min **6.571** / mean **6.988** / max **7.467 s**. Second reading: cargo's own `Finished … in <n>s` inside each re-run, reported for **61 of 61**, min 3.36 / mean 3.585 / max 3.85 s. Beside them the shim census: **62** entries, **2 506 729 440** bytes. §5.4 reads them. | **REPORTED** (no gate) |
| H7 | "**Every corpus case equal**; Python suite green; Rust workspace green." | The collector over **61** cases and **135** questions: **0** questions whose printed answer is not the registered one, **0** harness errors, **0** cases SKIPPED — so all `corpus/rust/*` cases ran, design §3.4's three new refocus cases included, and none was skipped for want of a driver. Second reading, each suite's exit status: collector **0**, `pytest -q` **0** (`1601 passed, 1 skipped in 112.88s`), `cargo test --workspace` **0** over **40** `test result: ok.` lines. | **PASS** |

**Overall: five PASS and two REPORTED — all seven as pre-registered, and the number the slice was built to produce came back whole: 61 of 61 MATCH, with no DIVERGED to classify.** Nothing was dropped, no invocation hit its 1800 s ceiling, the 2-hour loop bound was never approached (the loop closed in 8 min 22 s), no kill fired, and no endpoint fell back to an expectation. The one endpoint that did not land where §1 sketched it is H4's printed WORD — the counts §1 gates on are exactly as pre-registered, but the licence was WITHHELD on every pair (§5.2), which §1 neither predicted nor gates.

## 5. Gaps

### 5.1 What E4 measured about `refocus` on a Rust pair

**The gate came back whole: 61 of 61 MATCH, 0 DIVERGED, 0 REFUSED.** On a workspace nobody wrote `sensorium` for, `sensorium refocus <run> --focus <name>` took each of 61 recorded `cargo sensorium test … --exact` invocations, re-ran it under an added focus, found the pair the re-run produced through the store's own `refocus_of` link (never through the driver's printed `run:` line, which decided nothing), and issued the comparator's verdict on it — with the pass-2 exit status agreeing with the printed word on every one of the 61. No pre-rerun refusal fired, so §2.3's five refusal sentences are all consistent with a single-target invocation whose `workspace_root` still exists; and the focused re-build never failed, so §1's kill 1 — the compile-limitation class the §3.3 brace-macro guard exists for — had nothing to catch on this material, which §1.2's survey had already predicted by finding **0** brace-delimited macro tails in the seven files.

**The loop cost far less than §1's bound allowed.** The Task 5 report's §10.2 named wall-clock as the run's main risk: 61 originals plus 61 refocuses against one 2-hour deadline, with a cold dependency build feared at ~610 s from the E9 record's shape. Measured, the first pass-1 invocation compiled the clone's whole dependency tree in **5.58 s** of cargo's own reckoning (7.042 s wall), the remaining 60 originals cost 1.050–1.615 s each, and the whole loop closed in **8 min 22 s** of the 120 available. H7's three suites added 3 min 5 s outside the bound. Nothing was re-rolled and nothing was near a ceiling.

### 5.2 The licence was WITHHELD on all 61 — the surprise, and why it is honest

§1's H4 pre-registered four counts and got all four: source verified 61/61, environment verified 61/61, output UNVERIFIABLE 61/61, children UNVERIFIABLE 61/61 (and a fifth the instrument added, exit verified 61/61). What §1 did not predict is the **word** those counts appear under: `licences granted` is **0** and every one of the 61 printed `licence: WITHHELD -- this MATCH is about call shape, and these checks say it is not a statement about the run as a whole:`. The caveat is the same on every pair and it is not about source or environment at all — it is the untraced-thread clause: *"the original started N thread(s) besides the main one. A thread that ran no traced code has no fingerprint to compare, and the order the threads ran in was never compared for any of them"*, printed once for each side.

**That clause cannot not fire on a `cargo test` trace**, and the measured thread counts say exactly why, and say it in §1.2's own terms: **57** of the 61 pairs report **1** extra thread on each side — libtest's own per-test harness thread; **`a_pager_can_be_shared_across_threads`** reports **2**, the harness thread plus the one thread §1.2 names it for; and the **three** `pager_refusal_advice_test` server tests report **5**, the harness thread plus `serve_fake`'s `WORKER_COUNT = 4`. §1.2 derived those numbers from the source before anything ran; the licence's own counter re-derived them from two live traces each, and they agree on all 61. So the WITHHELD is not a defect and not a MISS of anything §1 gates: it is the licence declining to call a call-shape MATCH a statement about the whole run while a thread it could not fingerprint existed. The honest reading is that **on a Rust `cargo test` pair the licence is structurally never granted**, and the four counts — not the word — are what H4 reports. **The candidate fix, named here and deliberately not applied:** treat libtest's per-test thread as the recorder's own rather than the program's, so it does not raise the untraced-thread caveat — the precedent being the recorder's own environment variables, which the same licence already names and excludes (§4's H4 row). That is a design question about what "the program's threads" means on a test harness, and it is for a ruling (Brice, or a later slice), not for this record; Task 7 carries it to CARRIED-DEBT. Nothing in §2–§4 was changed on account of it.

### 5.3 The named hazard fired exactly once, and the comparator absorbed it

§1.2 named three `pager_refusal_advice_test` tests whose four `serve_fake` workers split ~ten loopback requests by the OS scheduler's choice, and pre-registered that only a different *partition* could diverge because `compare_tasks` matches tasks as an order-independent multiset of `(name, hash)`. **That is precisely what happened, on one pair of the three.** In `the_journal_records_the_advice_alongside_the_refusal_arithmetic` (pair 39 of §3's table: original `20260907-111226-12b15f`, refocused `20260907-111723-e55b4b`) the per-`task_id` assignment differs between the two runs — the original's workers carry (216, 205, 151, 233, 151) events by task id and the re-run's carry (216, 205, 233, 151, 151), the 233-event stream landing on a different worker — while the multiset of `(name, hash)` is identical and the total is 956 on both sides. The verdict is MATCH. Of the 61 pairs it is the **only** one whose per-task-id assignment moved at all; the other two server tests happened to split identically. §1.2's reasoning was therefore not merely unfalsified but exercised. **Where these numbers come from:** every count in this paragraph was read after the marker from each trace's `task_fingerprints` (`task_id`, `name`, `hash`, `n_events`) in the store, and from `fingerprints` for the MAIN stream — the same untouched traces the run itself compared, not a second measurement; no phase re-ran and no cell moved.

**One thing §1.4's discriminator cannot do on this subject, found by looking.** Its second condition is "the MAIN stream's fingerprint MATCHes". On every one of the 122 traces the MAIN stream (`fingerprints`, `thread_id` 1) carries **0 events** and the hash `cae66941d9efbd404e4d88758ea67670` — libtest runs each test on a spawned thread, which the converter records as a *task*, so nothing at all runs outside a task and the CLI prints `verdict: MATCH -- no causal event ran outside a task on either side, so the thread streams held nothing to compare`. Condition (2) is therefore true by construction here and would have discriminated nothing; had a DIVERGED occurred, the classification would have rested entirely on condition (1), the preserved worker total. The discriminator was never asked (`reported.discriminator` is `{}`), so no verdict in this record depends on it — but it is recorded as a limit of the amendment on `cargo test` material, not as a repair.

### 5.4 The cost — H6, and the instrument E9's residual asked for

E9's §5.5 item 3 left a residual: its cost reading carried no information because libtest reported `0.00 s` four times and every wall was dominated by compilation. E4 does not remove that — libtest still reports `0.0 s` on all 122 invocations — but it does what E9 could not: it separates the two halves at n = 61. **The refocus wall is almost entirely the focused rebuild.** Cargo's own `Finished … in <n>s` inside each re-run is min 3.36 / mean **3.585** / max 3.85 s against an invocation wall of min 6.571 / mean **6.988** / max 7.467 s — about 51 % of the wall is cargo's reported build, and the remainder is the shim keying, the recorder's spool and the conversion and comparison of two traces. The spread over 60 later focuses is 0.9 s, so the cost of a focus on this workspace is a flat ~7 s, not a distribution with a tail.

**§1.4's expectation that "the first pays for the rt build" is falsified, and harmlessly.** The first focus cost **6.661 s** — *faster* than the mean of the 60 that followed and only 0.09 s above the fastest. Pass 1 had already built the recorder runtime into the same fresh target, so by the time pass 2 opened there was no rt build left to pay for; what each refocus does pay for is its own shim key and the matched units. The **shim census** is the direct evidence: **62** entries under `<CARGO_TARGET_DIR>/sensorium/shim` totalling **2 506 729 440** bytes (~40.4 MB each) — one unfocused base key `d9ce385a08c6646b` from pass 1 and exactly **61** focused keys `d9ce385a08c6646b-<hash>`, one per focus, none reused. Around them the fresh E4 target reached **25.8 GB** and the traces are nearly the same size focused or not (originals 21 782 528 bytes total, refocused 22 171 648 — a 1.8 % mean increase), which is what a call-tier focus should cost in trace bytes.

### 5.5 What this run did not measure, and the residuals it leaves

* **One clone, one commit, 61 tests, seven single-target binaries.** A refocus of a multi-target invocation, of a workspace whose root has moved, of a run whose focus matches more than one qualname, and of a focused unit that fails to compile are all untested here — the last is what kill 1 exists for and it did not fire. Every pass-1 invocation produced exactly one process (`originals with more than one process` is `[]`), so §2.3's `invocation_processes` refusal is likewise unexercised, as are all five pre-rerun refusal sentences.
* **The reader version token is read from installed distribution metadata, and it is stale.** §2 records `sensorium 0.6.0`, which is what `importlib.metadata.version('sensorium')` reports in this `.venv`; the tree's `pyproject.toml` says **0.8.3** at this HEAD (§1.4 expected 0.8.4, or 0.8.3 if the Python bump had not landed — it had not). Nothing in E4 checks a sentence carrying that token, so no number moves on it; E9 recorded the same 0.6.0, so the venv's metadata has been stale across both records. Reported, not repaired.
* **H4's `verified_facts` is 0 on all 61 and is not a contradiction.** The licence's bulleted "verified against `<run>` on exactly these points" block only prints when the licence is GRANTED; with all 61 WITHHELD there are no such bullets to count. The verified counts H4 reports come from the printed `source:`, `env:` and `exit:` lines instead, which is why the instrument keeps them in separate fields — the alternative would have read 0 verified checks on a run where 183 checks ran and passed.
* **The suite's skip count still depends on one variable** — 1590/12 without `SENSORIUM_CARGO_SENSORIUM`, 1601/1 with it, both seen today (§2). E9 carried the same residual at 1426/12 against 1437/1; the delta is 11 tests in both records.

### 5.6 What this record licenses, and what it does not

It licenses `refocus`'s central claim **on this workspace**: given a recorded Rust invocation, `sensorium refocus <run> --focus <name>` re-runs it under the added focus, links the new trace to the old by `refocus_of`, finds that pair in the store by the link and the launch timestamp rather than by anything it printed, and returns the comparator's verdict with its exit — 61 of 61 MATCH, on all seven `pager_*_test.rs` files, at a flat ~7 s per pair; the licence beside each verdict verifies source and environment for real and refuses to call output or children verified when it cannot see them; and `watch` reads the resulting focused trace under slice-1 §4.2 on all three of §1.3's triples.

It does **not** license, and none of it is done here: a generalisation beyond one clone at one commit (§5.5); a claim that the licence can be granted on a Rust pair (§5.2 says the opposite is structural); a claim about the §1.4 discriminator's power, which was never asked and whose second condition has no subject on `cargo test` traces (§5.3); a cost claim beyond this workspace's flat ~7 s (§5.4); a second measurement — §1.4's kill 5 binds this record, and a corrected or extended endpoint is a NEW pre-registration in a NEW document, measured once; or re-opening an earlier record — the rung-4 focus-tier acceptance, the rung-3 borrow-repair acceptance and both rung-4 entry-grain records stand exactly as written.

### 5.7 Corrections of 2026-09-07, fix round 1 — every original sentence kept

Prose only. **No phase re-ran, no measurement was retaken, no verdict moved**: H1–H7 read exactly what §3 and §4 already published, H3 is still 61 of 61 MATCH with 0 DIVERGED, and §1 was not opened — its sha256 stays `09d2f8da30f6e216fb07e97c27481d35d0c285e40c2bccb9295e0ef07863ff42`.

**Struck in place with the correction beside it**, being a sentence that stated something wrong: §4's H4 cell said "85 files re-hashed by content" as though the count were uniform across the 61 pairs. The raw licence lines say **85 on 60 pairs and 80 on one**, `the_substrate_window_backstop_stays_a_refusal_across_the_boundary` — a smaller unit under test, not a smaller check. The endpoint is unaffected: H4's first reading is how many pairs verified source, which is 61 of 61 at either count.

**Edited in place, no strike**, being additions rather than corrections: §5.3 now names the two run ids of the pair whose task assignment moved and states that every count in it was read from `task_fingerprints` and `fingerprints` on the run's own untouched traces after the marker; and §5.2 now names the candidate fix for the structural WITHHELD and says explicitly that it is a ruling's to make and is not applied here.
