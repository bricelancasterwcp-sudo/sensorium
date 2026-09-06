# The model recorder's honesty ledger

`sensorium-model` — **no version yet**: this ledger is written before the crate exists (S0,
2026-09-05), as `rust/HONESTY.md` was written before the transformer. The first release
that writes a format-5 trace stamps its version here and strikes this line.

Sensorium's founding rule is that **the instrument never answers from data it does not have**.
This is the third recorder's half of that rule. It records what a model *did* — the token it
chose, the distribution it chose from, the spans a scanner found — and it makes no claim about
*why*; every key that could be read as a why (`attention`, `routing`, `activations`) is declared
`false` until a recorder witnesses it, and one of them is declared unwitnessable under the
engine's default configuration.

**How to read a section.** Each one states a promise, says **what in the trace says it** — a
meta key, a column, or a line `sensorium info` prints — and names **what could falsify it**: a
vector under `docs/trace-format/vectors/pending/` (promoted in S1), a pre-registered endpoint of
the design spec §10, or a test by path that S1 must write. A promise with no falsifier is not a
promise; this document carries none.

---

## 1

**Promise.** A `tokens` row records a token the sampler actually chose. The recorder never
writes a token id it did not see returned from sampling — no speculative continuation, no
re-derivation from the completion text, no row for a candidate the sampler considered and
rejected.

**What says it.** `tokens.token` is the id `sampler.sample` returned for that position, written
to the row only after the call returns — never a value read back out of decoded `piece` text or
reconstructed from the prompt.

**Falsifier.** `tests/test_model_writer.py::test_row_per_sampled_token_only` (S1), which must
show the writer refuses to source a `tokens.token` value from anything but the sampler's return;
and E-noise's kill clause — a divergence at `p = 0` between two identical boots is not noise, it
is the daemon not decoding what it says it is, and the run stops.

## 2

**Promise.** `logprob` and `entropy` are computed over the **full** vocabulary or not written at
all — never a partial-vocabulary shortcut reported under the true names. When the full
log-softmax is too costly, `entropy` reads `false`, not an approximation dressed as a
measurement.

**What says it.** `capabilities.entropy` gates whether the key is trustworthy at all
(`caps.require`, exit 3, per TRACE-FORMAT §4); `meta.model.n_vocab` is the width the recorder
promises `logprob`/`entropy` were taken over, so a reader can check the log-softmax denominator
matches the model's own vocabulary size rather than a truncated one. And the fallback is visible
in the rows themselves: `tokens.logprob` and `tokens.entropy` are **NULL** — never `0.0`, which
would be `p = 1`, the most confident claim the column can make — exactly when
`capabilities.entropy` is false, both deriving from the same full-vocabulary log-softmax; and
`meta.topk_basis` then reads `"logit"` instead of its default `"logprob"`, so the surviving
`topk` values are not silently read as logprobs they are not (MODEL-TRACES §2/§3, design spec
§11 R13).

**Falsifier.** `tests/test_model_writer.py::test_entropy_matches_reference_softmax_over_n_vocab`
(S1), comparing the written `entropy` against an independent full-vocabulary softmax of the same
logits; and E-overhead's fallback clause (design spec §10, §7) — if the full log-softmax's cost
binds, the recorder must flip `entropy` to `false` and fall back to sampler-candidate `topk`,
never report a cheaper number under the `entropy` name.

## 3

**Promise.** `topk` is the true top-k of the same distribution the token was sampled from,
listed in descending logprob order, with ties broken by ascending token id — not an
approximate or reordered slice.

**What says it.** `tokens.topk` is the JSON array itself, capped at length `meta.topk`, which
names the `k` the recorder promised to record for every position in the trace.

**Falsifier.** `tests/test_model_writer.py::test_topk_is_sorted_prefix_of_full_distribution`
(S1), which must confirm `tokens.topk` is exactly the first `k` entries of the full distribution
sorted descending by logprob with id-order tiebreaking, never a resorted or partial candidate
list from the sampler's own working set.

## 4

**Promise.** A generation's fingerprint hashes token ids only. Measurement — `logprob`,
`entropy`, `topk`, `piece`, `ts_ns` — never enters the hash, so two boots that sampled identical
tokens fingerprint identical no matter what GPU floating-point noise did to the third decimal.

**What says it.** `meta.fingerprint_basis` is stamped `"per-generation"`, naming the rule; the
`task_fingerprints.hash` column is the rolling blake2b-16 built only from the `f"{token}\n"`
updates §6 of the contract describes.

**Falsifier.** `m11-fingerprint-ignores-measurement` — two traces whose generations chose the
**identical token id at every position** while every recorded measurement about those tokens
(`logprob`, `entropy`, `topk`, `ts`) differs must fingerprint equal and read `MATCH`; a reading
of `DIVERGED` there means measurement entered the hash, which falsifies the "token ids only"
promise directly. `m05b-diff-within-noise-needs-blessed-band` is the second citation, for the
neighbouring case where the token ids themselves differ and the noise band is what decides.

## 5

**Promise.** A generation's `name` is the caller's own — the fixture or goal id supplied at the
call — or, when nothing was supplied, the recorder-minted `gen-N` read as **unnamed**. The
recorder never invents a name that looks caller-supplied.

**What says it.** `tasks.name` carries the value itself; a `gen-N` value (creation order) is the
signal that no caller name was given, exactly as `Task-N` marks an unnamed asyncio task.

**Falsifier.** `m03-gens-unnamed-pairs-by-order` — unnamed generations must pair with other
unnamed generations by creation order only, never by any invented similarity; a vector that
pairs a `gen-N` by content match instead of order falsifies the promise.

## 6

**Promise.** `spans` boundaries are the envelope scanner's judgement, not the model's — bloomery's
`<action …>…</action>` scanner finds byte offsets in the completion text, and the recorder maps
those offsets onto token positions. A boundary that lands inside a multi-byte token's bytes is
assigned to the token that completes it, and that assignment is declared, not hidden.

**What says it.** `meta.spans_basis` is stamped `"envelope-scanner"`, telling a reader a span
boundary is a scanner's finding, never a model-declared structure; `spans.ref.boundary_inside_token`
is `true` on exactly the spans where a scanner byte offset fell inside a multi-byte token's byte
range.

**Falsifier.** `tests/test_model_spans.py::test_boundary_inside_multibyte_token_is_flagged` (S1),
which must show a boundary landing inside a multi-byte token's bytes sets `boundary_inside_token:
true` rather than silently rounding to the nearest token edge; and E-mem as restated 2026-09-05
(design spec §10, §11 R18): every memory-on `prompt` span must carry
`memory_stamp.kind: "injected"` with the journal's own `episode_id` and every memory-off one
`"off"`, and the sha256 of the prompt bytes *before* the injection point must be equal across the
two arms — a stamp that disagrees with the journal, or a prefix that does not hash equal, is the
recorder mis-reading what it mapped. The endpoint's earlier wording — every divergence at or
after the `prompt` span's end — is withdrawn: `pos` counts sampled tokens only and a `prompt`
span has none, so nothing could ever have failed it, and a falsifier that cannot fail is not
one.

## 7

**Promise.** `exec.run_id` on an `action` span is the run id the daemon actually passed to the
child process, or `null` when no child ran under this action — never a value guessed or
reconstructed from the filesystem.

**What says it.** `spans.ref.exec.run_id` is the join field itself; `SENSORIUM_JOIN`,
copied verbatim by the program recorder into its own `meta.join`, is the independent trail that
lets a reader confirm the id the model trace cites is the id the child process actually received,
not a guess. The exit beside that id has **two sources and the reader names both**:
`ref.exec.exit_status`/`exit_status_basis` is the daemon's own witness — what the daemon saw, or
`unwitnessed`, or `not run` — and the referenced program trace's `meta.exit_status` is what that
file says; `spans` prints them as two labeled facts and merges them never, so a cached ref never
speaks for a file nobody opened and a missing file never erases what the daemon did see
(MODEL-TRACES §9, design spec §11 R17).

**Falsifier.** `m07a-spans-exec-ref-joins-program-trace` — with the daemon's witness
`unwitnessed` and the referenced program trace present, `spans` must print **two labeled facts**,
`daemon saw: unwitnessed` and `program trace: exit 1 (waited)`, never one merged line; a vector
where the two are collapsed, or where the printed exit is synthesized rather than read from the
program trace, falsifies the promise. `m07b-spans-exec-ref-trace-not-found` — with the daemon's
witness `exit 1 (waited)` and no program trace, the two facts are `daemon saw exit 1 (waited)`
and `program trace: (trace not found)`: the daemon's witness survives the missing file, and the
cached ref never stands in for it. And `tests/test_join_env.py::test_join_copied_verbatim_or_omitted` (S3),
which must show the program recorder copies `SENSORIUM_JOIN` verbatim or omits the key entirely
on a missing or non-JSON value, never a partial copy.

## 8

**Promise.** `noise_band` appears only on a trace that was blessed as a diff baseline, and it
names the exact boot it was measured against — never a tolerance a caller can widen, and never
carried onto a trace whose weights don't match the baseline.

**What says it.** `meta.noise_band.against` is the run id of the boot the band was measured
against; the band's presence at all is the signal that this trace, and only this trace, may be
read within-noise against that named baseline. Beside it, `meta.noise_band.weights_sha256` and
`meta.noise_band.adapters` are what the band was measured **under**, and they are what
applicability is decided on: a band applies only while they equal both sides' `model`, and
differ → `REFUSED` (MODEL-TRACES §6, design spec §11 R14). The promise is therefore readable
from A alone — no one has to open the baseline trace, and deleting it takes nothing away.

**Falsifier.** `m05c-diff-within-noise-needs-blessed-band` — a `diff` between two model traces
whose `model.weights_sha256` differ must read `REFUSED`, never `MATCH (within noise)`, even if a
`noise_band` is present on one side; and E-noise′ (design spec §10) — a third identical boot
diffed against the blessed boot1 must read `MATCH (within noise)`, and a `DIVERGED` reading there
falsifies the band's claim to generalize beyond the two boots it was measured from.

## 9

**Promise.** Nothing in a model trace says **why** the model produced what it produced.
`attention`, `routing`, and `activations` are declared `false` until a recorder witnesses them,
and attention specifically is declared **unwitnessable** — not merely unmeasured — whenever the
engine ran with flash attention on, because the fused kernel never materializes the weights to
read.

**What says it.** `capabilities.attention: false` (alongside `routing: false`,
`activations: false`) is the declaration itself; `witness_gap: "flash_attention_on"` is the
sentence that distinguishes "cannot be witnessed under this configuration" from "wasn't
measured this time," the same shape `spawn_witnessing` uses on the Rust side.

**Falsifier.** `m09-attention-declared-unwitnessable-under-fa` — `sensorium info` on a trace
recorded with flash attention on must print the flash-attention gap sentence naming
`witness_gap: flash_attention_on`, never a bare `0` and never wording that reads as "predates
this feature"; either substitution falsifies the promise that the gap is declared as
unwitnessable, not unmeasured.

## 10

**Promise.** The recorder's own cost is reported, whichever way it reads, and never gates
whether recording happens. A high overhead ratio is a fact to publish, not a threshold that
silently disables the recorder.

**What says it.** E-overhead (design spec §10) is published either way by design — there is no
meta key or column that hides a bad ratio, because the promise is about what the acceptance
record does, not about a value inside the trace file itself.

**Falsifier.** the acceptance record carries the ratio whichever way it reads:
`docs/superpowers/acceptance/<S1 date>-model-recorder.md` §E-overhead — an acceptance record
that omits the ratio, or omits it specifically because it fell below the `[0.95, 1.00]` band,
falsifies the "never gated" half of the promise.

---

## Index: promise → falsifier

| § | Promise | Falsifier |
|---|---|---|
| 1 | a `tokens` row is a sampled token | `tests/test_model_writer.py::test_row_per_sampled_token_only` (S1); E-noise's kill (a divergence at p=0) |
| 2 | logprob/entropy over the full vocabulary or declared false (NULL under the fallback, `topk_basis: "logit"`) | `tests/test_model_writer.py::test_entropy_matches_reference_softmax_over_n_vocab` (S1); E-overhead's fallback clause |
| 3 | `topk` is the true top-k, descending, ties by id | `tests/test_model_writer.py::test_topk_is_sorted_prefix_of_full_distribution` (S1) |
| 4 | fingerprint over token ids only | `m11-fingerprint-ignores-measurement` (identical ids at every position, different logprob/entropy/topk/ts → equal hash, `MATCH`); `m05b-diff-within-noise-needs-blessed-band` |
| 5 | names are the caller's; `gen-N` is unnamed | `m03-gens-unnamed-pairs-by-order` |
| 6 | spans are the scanner's judgement | `tests/test_model_spans.py::test_boundary_inside_multibyte_token_is_flagged` (S1); E-mem as restated (stamp agrees with the journal, pre-injection prefix hashes equal) |
| 7 | `exec.run_id` is the id passed to the child or null; the daemon's witness and the program trace's exit are two labeled facts | `m07a-spans-exec-ref-joins-program-trace` (daemon unwitnessed, trace exit 1) and `m07b-spans-exec-ref-trace-not-found` (daemon saw exit 1, trace not found); `tests/test_join_env.py::test_join_copied_verbatim_or_omitted` (S3) |
| 8 | `noise_band` only on a blessed trace, naming its baseline | `m05c-diff-within-noise-needs-blessed-band` (REFUSED when weights differ); E-noise′ |
| 9 | nothing says why; attention under FA declared unwitnessable | `m09-attention-declared-unwitnessable-under-fa` |
| 10 | cost reported, never gated | E-overhead published either way; the acceptance record carries the ratio whichever way it reads: `docs/superpowers/acceptance/<S1 date>-model-recorder.md` §E-overhead |
