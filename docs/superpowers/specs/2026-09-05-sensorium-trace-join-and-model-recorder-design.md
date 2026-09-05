# Sensorium S0 — the cross-trace join and the model recorder's contract

## 0. Provenance and status

- **Slice:** S0 of the approved program (plan `~/.claude/plans/if-you-were-to-lexical-clover.md`,
  2026-09-05; memory `sensor-suite-transfer-program`). S0 is **docs and vectors only**: this
  spec, an amendment to `docs/TRACE-FORMAT.md`, and pending conformance vectors. No recorder
  code, no query code. S1 (the `sensorium-model` crate + bloomery seam) and S3 (program traces
  launched by the daemon) implement it.
- **Design authority:** Claude, delegated by Brice 2026-09-04 ("you have design authority").
  Rulings are in §11 with cost-if-wrong; Brice may overturn any at spec review.
- **Branch:** `feat/s0-trace-join` (worktree `/mnt/extra/sensorium-rung2/s0-trace-join`), off
  main `e307d90` (0.8.1 / crates 0.3.1). Ledger
  `.superpowers/sdd/2026-09-05-sensorium-s0-trace-contract/progress.md`.
- **Sibling rule (Brice, 2026-08-20):** a new recorder brings its own honesty ledger and its own
  verdict rules and never compromises the Python core. This spec adds a third recorder kind
  and touches the Python reader only where §6 says, each touch fenced by a vector.

## 1. Goal, scope, non-goals

**Goal.** Make it possible, in one file format and one CLI, to answer: *at the token where the
model emitted `Done`, what had the program under test actually done, which memory episode was
in the window, and how sure was the model?* That is three traces — the **harness** (the
bloomery daemon, recorded by `cargo-sensorium`), the **model** (tokens the daemon sampled,
recorded by the daemon itself), and the **program under test** (what a granted command ran,
recorded by the Python or Rust recorder) — joined on explicit anchors.

**Why the model trace exists (from the program's conclusions):** what blocks learning-while-
working is signal, credit assignment, routing trust and the gate. A token-grain record with a
`diff` that names the first divergent position is credit assignment at the model level and a
behavioral admission gate for adapters (E-adapter, §10). It records **behavior as fact**; it
does not claim to know why.

**In scope for S0**
1. The **join contract**: how a trace names the group it belongs to and the anchors another
   trace can be aligned on (§5).
2. The **model trace layout**: tables, meta, capabilities, refusals, vocabulary (§3).
3. **Fingerprints and `diff` for model traces**, including the noise band (§4).
4. The **query surface** a model trace earns, and what existing commands do on one (§6).
5. The honesty ledger skeleton `model/HONESTY.md` (§8) and the vectors that pin all of it (§9).
6. The pre-registered acceptance S1 must run (§10), written now so the thresholds are derived
   before the instrument exists.

**Non-goals (this slice and stated for S1 too)**
- Anything from the model's internals: expert routing, activations, attention. Those are **S4**,
  and they land as *probe* tables under their own capabilities (§3.4 reserves the names).
- Sampling other than greedy. bloomery decodes greedily (`api_v1.rs` refuses any other
  temperature as dishonest); a sampled decode changes what a fingerprint means and needs its
  own pre-registration.
- A shared causal sequence across processes. There is none; §5 says what there is instead.
- Recording the prompt's tokens with logprobs. The prompt is not sampled; its text is
  recorded as a span (§3.3), not as token rows.
- Redaction. A model trace holds prompts, which hold goals, transcripts and injected memory
  verbatim. Same rule as every trace: treat it like a core dump (TRACE-FORMAT §2).

## 2. The subject, and the words for it

A program trace's subject is *a process running code*; its unit of work is a task or a thread.
A model trace's subject is *a model being decoded*; its unit of work is a **generation** — one
call into the substrate that consumed a prompt and produced tokens until a stop. The reader's
vocabulary table (`query/vocab.py`) gains a third column so no sentence about a model trace
borrows a program's words:

| Term | Python | Rust | **model** |
|---|---|---|---|
| unit of work | `asyncio task` | `test or spawned thread` | `generation` |
| plural | `asyncio task(s)` | `tests or spawned threads` | `generations` |
| a nameless one | `(name unreadable)` | `(unnamed: spawned by dependency code)` | `(unnamed: no fixture or goal id was supplied)` |
| what ran the program | `python <v>` | `toolchain: <t>` | `model: <meta.model.name> via <meta.model.engine>` |
| a runtime-minted name | `Task-N` = no name | none | `gen-N` = no name |

Naming rule (**R3**): a generation's `name` is supplied by the caller — the G4/G5 fixture id or
the goal hash bloomery already mints — and is what `diff` pairs on. The recorder never invents
one; a generation whose caller supplied nothing gets `gen-N` (creation order) and is read as
**unnamed**, exactly as asyncio's `Task-N` is.

## 3. Layout: trace format 5

### 3.1 Why a new format number, and what it changes for whom

Format 4 changed no columns; format 5 **adds two tables** (`tokens`, `spans`) and admits new
values for two existing meta keys (`lang: "model"`, `fingerprint_basis: "per-generation"`). A
format-4 reader opening a model trace would find empty `frames`/`events` and print
`no frames recorded` — a confident wrong answer about a file it was not written for, which is
exactly what TRACE-FORMAT §1's newer-format refusal exists to prevent. So a model trace is
stamped **5** and older sensoriums refuse it by name.

**Program recorders keep writing 4.** The only thing they gain from this spec is the optional
`join` meta key (§5), and optional keys are "read with defaults, never refused" — no bump is
needed for them. A reader at 5 reads 1–5.

### 3.2 Meta

The required set is **unchanged** (`db.REQUIRED_META`). A model trace fills it thus:

| Key | Model recorder's value |
|---|---|
| `run_id` | Minted by the recorder in the standard shape, or supplied (validated by `paths.is_valid_run_id`). |
| `argv`, `cwd` | The daemon's own. |
| `env_hash` | Sorted `k=v` lines, as the Rust recorder does. Comparable only to other model traces. |
| `start_ts`, `end_ts` | Wall clock around the recording window (one boot, §3.5). |
| `exit_status` | **`null`**, with `exit_status_basis: "not-a-process-exit"`. A model trace does not end because a process ended; it ends because recording was closed. A reader prints `exit: n/a (model trace)`; §6 fences this so `null` never renders as a status. |
| `main_thread_ident` | Serial of the daemon thread that opened the trace. |
| `fingerprint_basis` | **`"per-generation"`** (§4). |
| `truncated_count` | Count of token pieces or span texts clipped by the caps. |
| `source_hashes` | `{}` — this run traced code from no files. The artifacts behavior derives from live in `model`. **`{}` is a measured empty, not an absence**; the key is present. |
| `recorder` | `"sensorium-model <version>"`. |
| `lang` | **`"model"`**. |
| `capabilities` | §3.4. |

New optional keys, all written by the model recorder, read with defaults:

| Key | Meaning |
|---|---|
| `model` | `{name, engine, engine_build, weights_path, weights_sha256, adapters: [{name, sha256}], n_ctx, n_vocab, backend, sampler: {"kind": "greedy"}, flash_attention: bool}`. `weights_sha256` is the file digest actually read at boot, not a card value. `flash_attention` is here because §3.4's attention gap depends on it. |
| `topk` | The `k` recorded per token (default 8). |
| `noise_band` | Present only on a trace that was **blessed** as a diff baseline (§4.3): `{"basis": "two-identical-boots", "against": "<run_id>", "max_margin": f, "positions": n, "gens": n}`. |
| `join` | §5. |
| `spans_basis` | How action-span boundaries were found: `"envelope-scanner"` (bloomery's `<action …>…</action>` scanner, byte offsets mapped to tokens) — so a reader knows a span is a scanner's judgement, not a model's. |

### 3.3 Tables

Verbatim additions to `db.SCHEMA` (format 5). Existing tables are present and, in a model
trace, `code_objects`, `frames`, `events`, `output` are **empty** and `tasks`/`task_fingerprints`
are **reused** for generations:

```sql
CREATE TABLE tokens (
  id INTEGER PRIMARY KEY,          -- causal order across the trace (§4.1)
  task_id INTEGER NOT NULL,        -- → tasks.id: the generation
  pos INTEGER NOT NULL,            -- 0-based position within the generation's completion
  token INTEGER NOT NULL,          -- the sampled token id
  piece TEXT,                      -- the token's bytes as text; NULL = not decodable alone
  logprob REAL NOT NULL,           -- log p(token) under the full softmax
  entropy REAL NOT NULL,           -- H of the full distribution at this position, nats
  topk TEXT NOT NULL,              -- JSON [[token_id, logprob], ...] length ≤ meta.topk, desc
  ts_ns INTEGER NOT NULL           -- monotonic ns; display and join anchor only (§5.3)
);
CREATE TABLE spans (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL,        -- → tasks.id
  kind TEXT NOT NULL,              -- 'prompt' | 'action' | 'answer' | 'stop'
  first_pos INTEGER,               -- NULL for 'prompt' (not sampled)
  last_pos INTEGER,                -- inclusive; NULL while open
  text TEXT,                       -- the span's text; capped, trunc flag in ref
  ref TEXT                         -- JSON, keys by kind (§3.3.1)
);
CREATE INDEX idx_tokens_task ON tokens(task_id, pos);
CREATE INDEX idx_spans_task ON spans(task_id);
```

- **`tasks`** — one row per generation: `name` = the caller-supplied fixture/goal id (§2, R3) or
  NULL when unreadable (never the case for this recorder: absent input yields `gen-N`, not NULL);
  `thread_id` = the daemon thread that ran the decode.
- **`task_fingerprints`** — one row per generation, zero-count included (a generation that hit
  EOG at token 0 is a fact with content: "asked, said nothing").
- **`fingerprints`** (per-thread) — one row per daemon thread that ran a decode, count 0, meaning
  "every causal event on this thread ran inside a generation". Kept for the same reason a
  program trace keeps its zero-count main-thread row.
- Rows a recorder cannot fill are **omitted or NULL by rule above, never zero**: `piece` NULL
  means the bytes are not a standalone UTF-8 sequence, not an empty piece.

#### 3.3.1 `spans.ref` by kind

| kind | ref keys |
|---|---|
| `prompt` | `{"bytes": n, "sha256": "…", "memory_stamp": {"kind": "injected"\|"silent"\|"off", "episode_id": …\|null}, "grant": {…}\|null, "trunc": bool}` — the stamp and grant are **copied from the daemon's journal row for this turn**, so the trace says what the prompt carried without a reader re-rendering it. |
| `action` | `{"verb": "read"\|"patch"\|"run"\|"find"\|"done"\|…, "attrs": {…}, "exec": {"run_id": "<program trace run_id>"\|null, "exit_status": n\|null, "exit_status_basis": "waited"\|"unwitnessed"\|"not-run"}}` — `exec.run_id` is the join to the program trace (§5.2); `not-run` means the action was refused or never executed. |
| `answer` | `{"trunc": bool}` — completion text outside any action block. |
| `stop` | `{"reason": "eog"\|"stop-string"\|"max-tokens"\|"window"\|"error", "detail": …}` |

### 3.4 Capabilities

The model recorder declares **every** key in `boot.CAPABILITIES` plus its own; a key omitted
from a declaration reads `False` (TRACE-FORMAT §4), so nothing is left to inference:

```json
{"line": false, "locals": false, "return_value": false, "tasks": true, "threads": false,
 "children": false, "stdin": false, "output": false, "object_identity": false, "refocus": false,
 "tokens": true, "topk": true, "entropy": true, "spans": true,
 "routing": false, "activations": false, "attention": false}
```

- `tasks: true` because generations are units of work with fingerprints.
- `output: false` — the generated text lives in `spans`, not in `output`; a reader that looked
  for program output must be told it was not recorded.
- `tokens`, `topk`, `entropy`, `spans` gate the model commands (§6) through `caps.require`, exit 3.
- **Reserved for S4, declared false now:** `routing`, `activations`, `attention`. Their witness
  keys when true will be `routing_records`, `activation_layers`, `attention_basis`. The gap
  sentence for attention is fixed now: when `model.flash_attention` is true the recorder **cannot**
  witness attention weights (the softmax is fused), and the declaration must be `false` with
  `witness_gap: "flash_attention_on"` — the same shape as `spawn_witnessing`.

### 3.5 What one trace covers

**One trace per daemon boot** (R4). Generations accumulate as `tasks` rows across the boot's
lifetime; the trace is `incomplete = true` until the daemon closes recording at shutdown or on
an explicit `POST /sensorium/close`, then finalized. Why per boot: the acceptance endpoints
(§10) compare *boots*, the daemon's drift watch is per boot, and a per-generation file would
make `diff`'s pairing a filesystem exercise. A `diff` therefore compares two boots' generation
multisets by name — which is precisely `compare_tasks`' existing shape.

## 4. Fingerprints and `diff` for model traces

### 4.1 Causal order and the fingerprint

`tokens.id` is the trace-wide causal order, dense, in the order the daemon sampled — across
generations and threads, as `events.id` is for a program. Within a generation `pos` is the
position.

A generation's fingerprint is the rolling blake2b-16 over **token ids only**:

```
h.update(f"{token}\n".encode())      # one update per sampled token; n_events = tokens
```

`logprob`, `entropy`, `topk`, `piece`, `ts_ns` are **excluded by construction**, for the same
reason `LINE` and values are excluded from a program's: they are measurement, not behavior,
and two boots that chose identical tokens must fingerprint identical whatever the GPU's
floating point did to the third decimal.

`fingerprint_basis = "per-generation"`. `diff` refuses to compare a model trace with a program
trace (**exit 2** — a different call would settle it, §6), and refuses (**exit 3** — a different
recording would) two model traces with unequal `topk` **only when** the within-noise reading of
§4.3 is asked for — token-id comparison needs no `topk` at all.

### 4.2 The verdict, stepwise per generation

`diff A B` on two model traces:

1. **Pair generations by name** (multiset of `(name, hash)` — `compare_tasks` unchanged; a
   `gen-N` name is unnamed and pairs only with another unnamed by order, as `Task-N` does).
2. For each pair with unequal hashes, find the **first position `p`** where `token` differs.
3. Report, per diverged generation: `p`, both tokens' pieces, and the **margin** at `p` — under
   A's distribution, `logprob_A(a_p) − logprob_A(b_p)` (read from A's `topk`; if `b_p` is not in
   A's top-k the margin is `> topk-floor` and reported as such, never as a number); and
   symmetrically under B.
4. Verdict:
   - `MATCH` — every paired generation's hash equal, and no unpaired named generation.
   - `MATCH (within noise)` — every divergence is *within noise* (§4.3) **and** a `noise_band`
     is cited; the output names the baseline it was read from.
   - `DIVERGED` — at least one divergence outside the band, or any divergence with no band
     available. The first such generation, by A's order, is the one printed in full.
   - `REFUSED` — either side `incomplete`, bases differ, a side has generations but no
     `task_fingerprints`, or (for the within-noise reading) `noise_band` absent or computed
     against a different `model.weights_sha256`.

Exit statuses follow the house convention (0 yes = MATCH incl. within-noise, 1 no = DIVERGED,
3 = REFUSED; 2 = a bad call, e.g. mixed subjects). `--strict` drops the noise reading entirely
and treats any divergence as DIVERGED — for callers that want the raw fact.

### 4.3 The noise band, derived not chosen

Vulkan greedy decoding on this box is not bit-identical across launches (bloomery baselines:
prose differed on 5 of 52 fixtures across two identical boots). A within-noise verdict
therefore needs a **band measured from two identical boots of the same weights on the same
fixtures**, and nothing else:

- **`bless`**: `sensorium bless-noise <A> <B>` (new, §6) requires equal `model.weights_sha256`,
  equal adapters, equal fixture name sets; computes every divergence's margin under both
  sides; writes `noise_band = {max_margin, positions, gens, against: B}` **into A**. If A and B
  produced zero divergences the band is `{max_margin: 0.0, positions: 0, gens: 0}` — a measured
  zero, and any later divergence is outside it.
- **Within noise** at a divergence: both tokens appear in each other's top-k **and**
  `|margin| ≤ noise_band.max_margin` under both distributions.
- The band is **not** a tolerance a caller may widen. A caller who disagrees with it re-runs
  two identical boots and blesses again; the trace records which baseline said so.

## 5. The join

### 5.1 What there is not

There is no dense causal sequence across processes: the daemon, the recorded program, and
`cargo-sensorium`'s converter each mint their own. Any design that pretends otherwise
("shared seq") would have to elect a coordinator that every recorder calls on every event, and
the Python recorder's overhead is already the one cost this project reports honestly. So the
join is **anchors and references**, and the reader says which of the three kinds it used.

### 5.2 `meta.join` — the group and the role (R5)

Optional on every trace, written by whoever launched or wrote it:

```json
"join": {"group": "<daemon session id>", "role": "model" | "program" | "harness",
         "gen": "<generation name>" | null, "pid": 12345,
         "anchor": {"clock": "monotonic", "process": 12345}}
```

- `group` is the daemon's session id (bloomery already mints one per boot); every trace that
  exists *because of* that boot carries it. `runs` groups traces by `join.group` the way it
  groups Rust traces by `invocation`, header `session <group>: <model.name>`.
- **model → program.** When a granted `run` executes under sensorium, the daemon passes
  `--run-id <group>-<gen>-<n>` (a single path component; `paths.is_valid_run_id` accepts it)
  and sets `SENSORIUM_JOIN='{"group": …, "role": "program", "gen": …}'` in the child's
  environment. The Python recorder (S3) copies that JSON into `meta.join` at boot, verbatim,
  or omits the key when the variable is absent or is not a JSON object (never partially). The
  model trace's `action` span carries `exec.run_id` = that run id. This edge is a **reference**:
  exact, no clock involved.
- **model ↔ harness.** Both are the same process. `join.anchor` says which clock and which
  process; two traces with equal `anchor.process` and `anchor.clock == "monotonic"` may have
  their `ts_ns` compared — **the only case where `ts_ns` is comparable across files**, and
  TRACE-FORMAT §3/§6 are amended to say so in those words. The harness trace's `pid` meta is
  what the Rust converter already writes; `anchor.process` on the model trace is the daemon's
  own pid. The reader labels every such alignment `by clock`, never `by order`.
- **program ↔ harness.** Through the model trace (the `action` span references the program
  run id, and the span's tokens have `ts_ns` on the daemon's clock). Two hops, both named.

### 5.3 What the reader may say

A future `join` command (not S0; reserved) answers "what was true at token p of generation g":
it walks reference edges first, clock edges second, and prints the edge kind beside every
fact — `exec run 20260906-…-3 (by reference) exit 1 (waited)`; `harness frame
run_task → exec_run entered 41 ms before token 217 (by clock, same process)`. A trace with no
`join` key takes part in nothing and says so.

### 5.4 What S2 needs from a program trace: a `signature`

The transfer research (crucible phase D draft, 2026-09-05) wants a **trace-derived signature**
of a failing unit as episode identity — mechanism-level, surface-free. Today that would be
scraped from `exceptions`/`frame` prose, which is exactly the kind of reading a later wording
change breaks. So the contract names a derived reading, `signature <run> [--json]`, computed by
the reader from any program trace (Python or Rust) and defined here so its meaning is fixed
before anyone stores one:

```json
{"basis": "signature-v1", "recorder": "sensorium 0.8.1", "lang": "python",
 "outcome": "raised" | "returned" | "unwound" | "open",
 "exc": {"type": "TypeError", "kind": null} | null,
 "disposition": "PROPAGATED" | "SWALLOWED" | "HANDLED" | "AMBIGUOUS" | null,
 "fork": {"qualname": "unit_17.helper", "kind": "RAISE", "depth": 2} | null,
 "closed_by": "unwind" | "return" | null}
```

- **Identity, not description**: it hashes to a key by content (`blake2b-16` over the canonical
  JSON with `recorder` removed), and two units whose failing runs share a key are *signature
  siblings* whatever their source text says. The key is what S2's `sig` arm retrieves on.
- `fork` is the frame at which the run's causal stream first departs from a *reference* run when
  one is given (`--against <run>`), else the outermost frame that raised. `qualname` is
  **file-local** (TRACE-FORMAT §3 `code_objects.qualname`) so a unit renamed `unit_<id>` at
  composition keeps its signature.
- `exc.msg` is **excluded**: messages carry surface (values, names), and the whole point is to
  abstract over surface. A caller who wants the message reads `exceptions`.
- Implementation is S1's or S3's; the vector `p01-signature-canonical-json` (pending, §9) pins
  the shape. **Nothing here changes the model-trace layout**; it is the program-trace half of the
  suite's join to a memory store.

## 6. Query-layer changes (fenced by vectors, §9)

Familiar spellings; nothing novel (designing-notation §2). Exits per the 0/1/2/3 convention.

| Command | On a model trace |
|---|---|
| `runs` | Lists model traces under `session <group>: <model.name>` when `join.group` is present; otherwise in place. `exit: n/a (model trace)` in the row. |
| `info` | Prints `model: <name> via <engine> <build>`, weights sha (short), adapters, `n_ctx`, `sampler: greedy`, `topk`, generations count, tokens count, mean entropy, declared-not-witnessed line for routing/activations/attention with the flash-attention gap sentence when applicable, `noise_band` if blessed, `join` if present. |
| `gens <run>` | **New.** One line per generation: `g<id> <name> tokens:<n> stop:<reason> H̄:<mean entropy> minH:<min> at p<pos>` in causal order. Exit 0 with rows, 1 with none. |
| `tokens <run> --gen <name> [--from P --to Q] [--min-margin X]` | **New.** Token rows with piece, logprob, entropy, top-k. `--min-margin X` keeps positions where the top-1/top-2 gap ≤ X (the "swallowed uncertainty" view). `--gen` exact-first, then unique prefix, as `--fn` does. |
| `spans <run> --gen <name>` | **New.** The generation's prompt/action/answer/stop spans with refs; `action` prints `exec run <id> exit …` or `not run`. |
| `diff A B` | §4.2. Auto-dispatches on `lang == "model"` both sides; mixed → exit 2 `REFUSED: A is a model trace and B is a program trace; diff compares like with like`. |
| `bless-noise A B` | **New**, §4.3. |
| `tree`, `frame`, `grep`, `flow`, `watch`, `exceptions`, `refocus` | **Refuse with exit 2** and one sentence: `REFUSED: <cmd> reads program <frames|events|…>; this is a model trace (recorder <r>) -- use gens/tokens/spans`. `flow`/`watch` already refuse via `line: false` (exit 3); the model-trace sentence takes precedence because the fix is a different command, not a different recording. `exceptions` already refuses on an unknown lang; its wording is replaced by the same sentence on `lang == "model"`. |

`vocab.terms()` gains the `MODEL` column (§2). `exit_phrase` gains `n/a (model trace)` for
basis `not-a-process-exit`.

## 7. The bloomery seam (what S1 will do; recorded here so the contract fits it)

- `bloomery-substrate::llama::generate_from` samples greedily per token from
  `sampler.sample(ctx, logits_idx)`. Before sampling, `ctx.candidates_ith(logits_idx)` yields
  every `(token, logit)`; `n_vocab` is on the model. logprob and entropy come from one
  log-softmax over the row; top-k from a partial sort. **Nothing touches the distribution** —
  the recorder reads, the sampler decides; the law-3 ruling (stop strings are termination, not
  constraint) extends to recording.
- Observation crosses the `Substrate` trait as data, not a callback: `Generated` gains
  `tokens: Option<Vec<TokenRecord>>`, `Some` only when the daemon asked for recording. The
  `sensorium-model` crate defines `TokenRecord`, the writer, and the finalize pass; bloomery
  depends on it; it depends on nothing of bloomery's.
- Span boundaries: bloomery's envelope scanner already finds `<action …>…</action>` by byte
  offset; the recorder maps byte offsets to token positions from cumulative `piece` lengths
  (a boundary inside a multi-byte token is assigned to the token that completes it, and the
  span's `ref.boundary_inside_token: true` says so).
- The memory stamp and grant for the turn are read from the journal row the task loop writes
  (`Event::MemoryStamp{episode_id, …}`), never re-derived from prompt text.
- E-overhead (§10) is the cost the recorder pays for a full-vocab log-softmax per token on the
  CPU while the GPU idles; if it binds, the fallback is `topk` from the sampler's candidate
  array and `entropy` declared **false** — never a cheaper approximation reported as entropy.

## 8. `model/HONESTY.md` — the promises (skeleton; S1 fills falsifiers)

1. A `tokens` row is a token the sampler chose; the recorder never writes a token it did not see
   chosen. 2. `logprob` and `entropy` are computed over the **full** vocabulary or not at all
   (declared `false`). 3. `topk` is the true top-k of the same distribution, descending, ties
   in token-id order. 4. A fingerprint hashes token ids only. 5. A generation's `name` is the
   caller's or `gen-N`; the recorder invents no name. 6. `spans` boundaries are the envelope
   scanner's judgement (`spans_basis`), not the model's. 7. `exec.run_id` is the id the daemon
   passed to the child, or null; it is never guessed from the filesystem. 8. `noise_band` is
   present only on a blessed trace and names the boot it was measured against. 9. Nothing in
   this trace says **why** the model did anything; `attention`, `routing`, `activations` are
   declared false until a recorder witnesses them, and attention under flash attention is
   declared unwitnessable, not unmeasured. 10. Cost is reported, never gated (E-overhead is
   published whichever way it reads).

## 9. Conformance vectors (authored in S0 under `docs/trace-format/vectors/pending/`, promoted in S1)

`tests/test_vectors.py` builds only `vectors/*.json`; **`pending/` is documentation until the
builder can write `tokens`/`spans` rows (S1 task 1)** — ruled so S0 stays code-free (R7).

| id | pins |
|---|---|
| `m01-format5-refused-by-format4-reader` | a format-5 file is refused by name, never read as empty frames |
| `m02-model-trace-program-commands-refuse` | `tree`/`frame`/`grep`/`exceptions` exit 2 with the one sentence |
| `m03-gens-unnamed-pairs-by-order` | `gen-N` is unnamed; pairs only with unnamed, by order |
| `m04-diff-first-divergence-and-margin` | `p`, pieces, both margins; a token outside top-k reports `> topk-floor`, not a number |
| `m05-diff-within-noise-needs-blessed-band` | same divergence: DIVERGED without `noise_band`, MATCH (within noise) with it, REFUSED when band's weights sha differs |
| `m06-exit-status-not-a-process-exit` | `exit: n/a (model trace)`; never `None`, never `0` |
| `m07-spans-exec-ref-joins-program-trace` | `spans` prints `exec run <id> exit 1 (waited)` read from the program trace when present, `exec run <id> (trace not found)` when absent |
| `m08-join-group-in-runs` | `runs` groups by `join.group`; a trace without `join` lists in place |
| `m09-attention-declared-unwitnessable-under-fa` | `info` prints the flash-attention gap sentence, not `0` and not "predates" |
| `m10-zero-token-generation-row` | a generation that produced 0 tokens has a `task_fingerprints` row with `n_events 0` |
| `p01-signature-canonical-json` | `signature --json` on a Python trace yields the §5.4 shape, `msg` absent, key stable under a file-local rename |

## 10. Pre-registered acceptance for S1 (thresholds derived here, before the instrument exists)

Fixture set: the frozen G5 `codec-tasks-v4-mixed` (16 + 16) plus the G4 set, memory **off**
(every frozen instrument runs memory-off — bloomery's standing rule). Model: the current
featured base at its recorded `weights_sha256`. Two identical boots = same binary, same
config, same fixtures, daemon restarted between.

| Endpoint | Reading | Pass | Kill |
|---|---|---|---|
| **E-noise** | `diff boot1 boot2` before any bless | count of diverged generations `d` and max margin `m` recorded; then `bless-noise` writes the band | — (this run *defines* the band; it cannot fail, it can only be recorded) | a divergence at `p = 0` or with either token outside the other's top-8 → instrument defect, STOP (the daemon is not decoding what it says it is) |
| **E-noise′** | third identical boot vs blessed boot1 | `MATCH (within noise)` | required | `DIVERGED` → the band does not generalise to a third boot; STOP and report |
| **E-adapter** | `fw-current` vs its base, same fixtures | DIVERGED on ≥ the fixtures whose G5 verdicts differ between the two (the *known* behavior change), `p` at or after the first post-prompt token; MATCH (within noise) on every fixture whose verdicts are equal on both | both halves | any DIVERGED on the base-vs-base control (a 4th boot) outside the band → instrument, STOP |
| **E-mem** | memory on vs off, same boot config | every divergence's `p` ≥ the `prompt` span's end (the injected stamp is in the prompt; the prefix is golden-tested byte-identical) | required | a divergence *before* the injection point → the recorder mis-mapped spans, STOP |
| **E-overhead** | decode tok/s, recorder on vs off, n = 5 boots each, same fixtures | ratio reported with both means; band = `[0.95, 1.00]` derived from `topk` extraction + one log-softmax over 150k floats per token at ≤ 1 ms against ≥ 10 ms/token decode | published either way | none — cost is reported, not gated (HONESTY §10); if `< 0.90` the entropy fallback of §7 becomes S1's first CARRIED-DEBT item |

Controls and rules: base-vs-base is the control arm for E-adapter; all readings computed by
`diff`, never by hand; every number quoted with `weights_sha256`, fixture set name, and boot
ids; an infra kill (daemon 503, OOM) is a clean rerun from zero, a completed reading is never
re-rolled.

## 11. Rulings (design authority; each with cost-if-wrong)

| # | Ruling | Alternatives rejected | Cost if wrong |
|---|---|---|---|
| R1 | Model traces use **new tables in the same format**, stamped format 5; generations reuse `tasks`/`task_fingerprints`. | (a) tokens as `events` rows — `causal_stream` requires `code_id`, and `tree`/`exceptions` would render a model as a program: a familiar-spelling/different-concept collision. (c) a separate format and tool — loses the contract, the vectors, and `diff`'s pairing machinery. | A reader change touches the Python core; fenced by m01–m10 and the legacy suite. If the reuse of `tasks` ever needs a generation-only column, format 6. |
| R2 | `lang: "model"`, third vocab column. | `subject` as a new key — a new axis when `lang` already keys every renderer's words and `exceptions`' dispatch, and the unknown-lang refusal already does the right thing. | If a fourth *program* language lands, `lang` still means "what the words are about"; no cost. |
| R3 | Generation names are caller-supplied; `gen-N` = unnamed. | Recorder-minted names from prompt hashes — would pair generations the caller considers different and hide fixture identity. | None beyond one line in HONESTY. |
| R4 | One trace per daemon boot. | Per generation — `diff` pairing becomes a filesystem exercise; per task — the drift watch is per boot. | A very long boot makes a large file; `POST /sensorium/close` rotates it. |
| R5 | Join = `meta.join` references + same-process clock anchor; no shared sequence. | Coordinator-minted global seq — every recorder pays a call per event. | If cross-process clock alignment is ever needed, `anchor.clock: "realtime"` is additive. |
| R6 | Fingerprint over token ids only; margins grade, never hash. | Hashing `(token, topk)` — GPU float noise would break every MATCH. | None; the margin rule is where measurement enters, explicitly. |
| R7 | S0 ships vectors as `pending/`, not built. | Building them needs writer support = code = S1. | Vectors are un-run prose for one slice; promoted first thing in S1. |
| R8 | `exit_status: null` + `exit_status_basis: "not-a-process-exit"`. | Writing the daemon's exit — the daemon has not exited when the trace is finalized. | One new basis word in `exit_phrase`; vector m06. |
| R9 | S4's probe capabilities named and declared false now, with the flash-attention gap sentence fixed. | Leave them out until S4 — an omitted key reads `false` anyway, but the *sentence* is what stops "attention wasn't measured" reading as "the model didn't attend". | None. |

## 12. Open for Brice (recommendation inline)

1. **`topk` default 8 vs 16.** 8 matches the G5 divergence pattern seen so far (two identical
   boots differ by prose choice, not by exotic tokens); 16 costs 2× row size for margins nobody
   has asked for. *Recommend 8*; a divergence outside top-8 is itself a finding (E-noise kill).
2. **Whether the model recorder is on by default in the featured daemon.** *Recommend off by
   default, on by config*; every frozen instrument's boot recipe stays byte-identical until a
   pre-registration turns it on.
3. **Whether `bless-noise` writes into the baseline trace or beside it.** Writing into A mutates
   a finalized trace's meta (additive key). *Recommend into A*, mirroring `refocus_*` stamps.

## 13. Order of work

S0 (this branch): T0 this spec + ledger → T1 TRACE-FORMAT §1 table row for 5, §3 tables, §4 new
optional keys + `not-a-process-exit`, §5 `lang: model`, §6 the ts_ns cross-file rule, §7
per-generation basis, pointer to this spec → T2 the §2 vocabulary column into TRACE-FORMAT §4's wording-note table (the `query/vocab.py` column itself lands in S1) → T3 `pending/m01–m10.json` → T4
`model/HONESTY.md` skeleton → T5 CARRIED-DEBT entry + PR. Then **writing-plans** for S1.
