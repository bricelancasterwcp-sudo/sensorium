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

*(written by Task 6)*

## 3. Results

*(written by Task 6)*

## 4. Verdicts

*(written by Task 6)*

## 5. Gaps

*(written by Task 6)*
