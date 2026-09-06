# Model traces (trace format 5)

> The contract for the third recorder kind, `sensorium-model` (S1 of the sensor-suite program).
> Kept out of `docs/TRACE-FORMAT.md` so that file stays under its 800-line ceiling; TRACE-FORMAT
> §1 names format 5 and points here. Design: `docs/superpowers/specs/2026-09-05-sensorium-trace-join-and-model-recorder-design.md`.
> **Status 2026-09-05: contract only.** No recorder writes this format yet; sensorium 0.8.1 refuses
> a format-5 file by TRACE-FORMAT §1's newer-format rule, which is the intended behavior until S1.

## 1. Subject and vocabulary

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

## 2. Meta

The required set is **unchanged** (`db.REQUIRED_META`). A model trace fills it thus:

| Key | Model recorder's value |
|---|---|
| `run_id` | Minted by the recorder in the standard shape, or supplied (validated by `paths.is_valid_run_id`). |
| `argv`, `cwd` | The daemon's own. |
| `env_hash` | Sorted `k=v` lines, as the Rust recorder does. Comparable only to other model traces. |
| `start_ts`, `end_ts` | Wall clock around the recording window (one boot, §5). |
| `exit_status` | **`null`**, with `exit_status_basis: "not-a-process-exit"`. A model trace does not end because a process ended; it ends because recording was closed. A reader prints `exit: n/a (model trace)`; §9 fences this so `null` never renders as a status. |
| `main_thread_ident` | Serial of the daemon thread that opened the trace. |
| `fingerprint_basis` | **`"per-generation"`** (§6). |
| `truncated_count` | Count of token pieces or span texts clipped by the caps. |
| `source_hashes` | `{}` — this run traced code from no files. The artifacts behavior derives from live in `model`. **`{}` is a measured empty, not an absence**; the key is present. |
| `recorder` | `"sensorium-model <version>"`. |
| `lang` | **`"model"`**. |
| `capabilities` | §4. |

New optional keys, all written by the model recorder, read with defaults:

| Key | Meaning |
|---|---|
| `model` | `{name, engine, engine_build, weights_path, weights_sha256, adapters: [{name, sha256}], n_ctx, n_vocab, backend, sampler: {"kind": "greedy"}, flash_attention: bool}`. `weights_sha256` is the file digest actually read at boot, not a card value. `flash_attention` is here because §4's attention gap depends on it. |
| `topk` | The `k` recorded per token (default 8). |
| `noise_band` | Present only on a trace that was **blessed** as a diff baseline (§6): `{"basis": "two-identical-boots", "against": "<run_id>", "max_margin": f, "positions": n, "gens": n}`. |
| `join` | §7. |
| `spans_basis` | How action-span boundaries were found: `"envelope-scanner"` (bloomery's `<action …>…</action>` scanner, byte offsets mapped to tokens) — so a reader knows a span is a scanner's judgement, not a model's. |

The required set is `db.REQUIRED_META`, unchanged; format 5 adds no required key.

## 3. Tables

Verbatim additions to `db.SCHEMA` (format 5). Existing tables are present and, in a model
trace, `code_objects`, `frames`, `events`, `output` are **empty** and `tasks`/`task_fingerprints`
are **reused** for generations:

```sql
CREATE TABLE tokens (
  id INTEGER PRIMARY KEY,          -- causal order across the trace (§6)
  task_id INTEGER NOT NULL,        -- → tasks.id: the generation
  pos INTEGER NOT NULL,            -- 0-based position within the generation's completion
  token INTEGER NOT NULL,          -- the sampled token id
  piece TEXT,                      -- the token's bytes as text; NULL = not decodable alone
  logprob REAL NOT NULL,           -- log p(token) under the full softmax
  entropy REAL NOT NULL,           -- H of the full distribution at this position, nats
  topk TEXT NOT NULL,              -- JSON [[token_id, logprob], ...] length ≤ meta.topk, desc
  ts_ns INTEGER NOT NULL           -- monotonic ns; display and join anchor only (§7)
);
CREATE TABLE spans (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL,        -- → tasks.id
  kind TEXT NOT NULL,              -- 'prompt' | 'action' | 'answer' | 'stop'
  first_pos INTEGER,               -- NULL for 'prompt' (not sampled)
  last_pos INTEGER,                -- inclusive; NULL while open
  text TEXT,                       -- the span's text; capped, trunc flag in ref
  ref TEXT                         -- JSON, keys by kind (§3)
);
CREATE INDEX idx_tokens_task ON tokens(task_id, pos);
CREATE INDEX idx_spans_task ON spans(task_id);
```

- **`tasks`** — one row per generation: `name` = the caller-supplied fixture/goal id (§1; design spec §11 R3) or
  NULL when unreadable (never the case for this recorder: absent input yields `gen-N`, not NULL);
  `thread_id` = the daemon thread that ran the decode.
- **`task_fingerprints`** — one row per generation, zero-count included (a generation that hit
  EOG at token 0 is a fact with content: "asked, said nothing").
- **`fingerprints`** (per-thread) — one row per daemon thread that ran a decode, count 0, meaning
  "every causal event on this thread ran inside a generation". Kept for the same reason a
  program trace keeps its zero-count main-thread row.
- Rows a recorder cannot fill are **omitted or NULL by rule above, never zero**: `piece` NULL
  means the bytes are not a standalone UTF-8 sequence, not an empty piece.

### `spans.ref` by kind

| kind | ref keys |
|---|---|
| `prompt` | `{"bytes": n, "sha256": "…", "memory_stamp": {"kind": "injected"\|"silent"\|"off", "episode_id": …\|null}, "grant": {…}\|null, "trunc": bool}` — the stamp and grant are **copied from the daemon's journal row for this turn**, so the trace says what the prompt carried without a reader re-rendering it. |
| `action` | `{"verb": "read"\|"patch"\|"run"\|"find"\|"done"\|…, "attrs": {…}, "exec": {"run_id": "<program trace run_id>"\|null, "exit_status": n\|null, "exit_status_basis": "waited"\|"unwitnessed"\|"not-run"}}` — `exec.run_id` is the join to the program trace (§7); `not-run` means the action was refused or never executed. |
| `answer` | `{"trunc": bool}` — completion text outside any action block. |
| `stop` | `{"reason": "eog"\|"stop-string"\|"max-tokens"\|"window"\|"error", "detail": …}` |

## 4. Capabilities

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
- `tokens`, `topk`, `entropy`, `spans` gate the model commands (§9) through `caps.require`, exit 3.
- **Reserved for S4, declared false now:** `routing`, `activations`, `attention`. Their witness
  keys when true will be `routing_records`, `activation_layers`, `attention_basis`. The gap
  sentence for attention is fixed now: when `model.flash_attention` is true the recorder **cannot**
  witness attention weights (the softmax is fused), and the declaration must be `false` with
  `witness_gap: "flash_attention_on"` — the same shape as `spawn_witnessing`.

## 5. One trace per boot

**One trace per daemon boot** (R4). Generations accumulate as `tasks` rows across the boot's
lifetime; the trace is `incomplete = true` until the daemon closes recording at shutdown or on
an explicit `POST /sensorium/close`, then finalized. Why per boot: the acceptance endpoints
(design spec §10) compare *boots*, the daemon's drift watch is per boot, and a per-generation file would
make `diff`'s pairing a filesystem exercise. A `diff` therefore compares two boots' generation
multisets by name — which is precisely `compare_tasks`' existing shape.

Ruled 2026-09-05: `topk` default 8; recording is off by default and enabled by daemon config;
`bless-noise` writes `noise_band` into A.

## 6. Fingerprints and diff

### Causal order and the fingerprint

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
trace (**exit 2** — a different call would settle it, §9), and refuses (**exit 3** — a different
recording would) two model traces with unequal `topk` **only when** the within-noise reading of
§6 is asked for — token-id comparison needs no `topk` at all.

### The verdict, stepwise per generation

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
   - `MATCH (within noise)` — every divergence is *within noise* (§6) **and** a `noise_band`
     is cited; the output names the baseline it was read from.
   - `DIVERGED` — at least one divergence outside the band, or any divergence with no band
     available. The first such generation, by A's order, is the one printed in full.
   - `REFUSED` — either side `incomplete`, bases differ, a side has generations but no
     `task_fingerprints`, or (for the within-noise reading) `noise_band` absent or computed
     against a different `model.weights_sha256`.

Exit statuses follow the house convention (0 yes = MATCH incl. within-noise, 1 no = DIVERGED,
3 = REFUSED; 2 = a bad call, e.g. mixed subjects). `--strict` drops the noise reading entirely
and treats any divergence as DIVERGED — for callers that want the raw fact.

### The noise band, derived not chosen

Vulkan greedy decoding on this box is not bit-identical across launches (bloomery baselines:
prose differed on 5 of 52 fixtures across two identical boots). A within-noise verdict
therefore needs a **band measured from two identical boots of the same weights on the same
fixtures**, and nothing else:

- **`bless`**: `sensorium bless-noise <A> <B>` (new, §9) requires equal `model.weights_sha256`,
  equal adapters, equal fixture name sets; computes every divergence's margin under both
  sides; writes `noise_band = {max_margin, positions, gens, against: B}` **into A**. If A and B
  produced zero divergences the band is `{max_margin: 0.0, positions: 0, gens: 0}` — a measured
  zero, and any later divergence is outside it.
- **Within noise** at a divergence: both tokens appear in each other's top-k **and**
  `|margin| ≤ noise_band.max_margin` under both distributions.
- The band is **not** a tolerance a caller may widen. A caller who disagrees with it re-runs
  two identical boots and blesses again; the trace records which baseline said so.

## 7. The join

### What there is not

There is no dense causal sequence across processes: the daemon, the recorded program, and
`cargo-sensorium`'s converter each mint their own. Any design that pretends otherwise
("shared seq") would have to elect a coordinator that every recorder calls on every event, and
the Python recorder's overhead is already the one cost this project reports honestly. So the
join is **anchors and references**, and the reader says which of the three kinds it used.

### `meta.join` — the group and the role (R5)

Optional on every trace, written by whoever launched or wrote it:

```json
{"join": {"group": "<daemon session id>", "role": "model", "gen": "g5-mixed/patch-07",
          "pid": 41213, "anchor": {"clock": "monotonic", "process": 41213}}}
```

`gen` is the generation name for a `model` or `program` join and **null** for a `harness`
join (a whole-process trace is tied to no single generation).

| `role` | Who writes it |
|---|---|
| `model` | The model recorder itself, into its own trace, at finalize. |
| `program` | The program recorder (Python S3, or Rust), copying `SENSORIUM_JOIN` verbatim from the daemon-set child-process environment. |
| `harness` | `cargo-sensorium`, converting the bloomery daemon's own recording. |

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

### What the reader may say

A future `join` command (not S0; reserved) answers "what was true at token p of generation g":
it walks reference edges first, clock edges second, and prints the edge kind beside every
fact — `exec run 20260906-…-3 (by reference) exit 1 (waited)`; `harness frame
run_task → exec_run entered 41 ms before token 217 (by clock, same process)`. A trace with no
`join` key takes part in nothing and says so.

## 8. signature

The transfer research (crucible phase D draft, 2026-09-05) wants a **trace-derived signature**
of a failing unit as episode identity — mechanism-level, surface-free. Today that would be
scraped from `exceptions`/`frame` prose, which is exactly the kind of reading a later wording
change breaks. So the contract names a derived reading, `signature <run> [--json]`, computed by
the reader from any program trace (Python or Rust) and defined here so its meaning is fixed
before anyone stores one:

```json
{"basis": "signature-v1", "recorder": "sensorium 0.8.1", "lang": "python",
 "outcome": "raised",
 "exc": {"type": "TypeError", "kind": null},
 "disposition": "PROPAGATED",
 "fork": {"qualname": "unit_17.helper", "kind": "RAISE", "depth": 2},
 "closed_by": "unwind"}
```

| Field | Alternatives |
|---|---|
| `outcome` | `"raised"` \| `"returned"` \| `"unwound"` \| `"open"` |
| `exc` | the `{type, kind}` object when the run raised, **null** when `outcome` is `returned` or `open` |
| `disposition` | `"PROPAGATED"` \| `"SWALLOWED"` \| `"HANDLED"` \| `"AMBIGUOUS"` \| `null` |
| `fork` | the frame object when a raising or diverging frame exists, **null** when the run returned with no divergence from the reference (or no reference was given and nothing raised) |
| `closed_by` | `"unwind"` \| `"return"` \| `null` |

- **Identity, not description**: it hashes to a key by content (`blake2b-16` over the canonical
  JSON with `recorder` removed), and two units whose failing runs share a key are *signature
  siblings* whatever their source text says. The key is what S2's `sig` arm retrieves on.
- `fork` is the frame at which the run's causal stream first departs from a *reference* run when
  one is given (`--against <run>`), else the outermost frame that raised. `qualname` is
  **file-local** (TRACE-FORMAT §3 `code_objects.qualname`) so a unit renamed `unit_<id>` at
  composition keeps its signature.
- `exc.msg` is **excluded**: messages carry surface (values, names), and the whole point is to
  abstract over surface. A caller who wants the message reads `exceptions`.
- Implementation is S1's or S3's; the vector `p01-signature-canonical-json` (pending, design spec §9) pins
  the shape. **Nothing here changes the model-trace layout**; it is the program-trace half of the
  suite's join to a memory store.

## 9. Commands on a model trace

Familiar spellings; nothing novel (designing-notation §2). Exits per the 0/1/2/3 convention.

| Command | On a model trace |
|---|---|
| `runs` | Lists model traces under `session <group>: <model.name>` when `join.group` is present; otherwise in place. `exit: n/a (model trace)` in the row. |
| `info` | Prints `model: <name> via <engine> <build>`, weights sha (short), adapters, `n_ctx`, `sampler: greedy`, `topk`, generations count, tokens count, mean entropy, declared-not-witnessed line for routing/activations/attention with the flash-attention gap sentence when applicable, `noise_band` if blessed, `join` if present. |
| `gens <run>` | **New.** One line per generation: `g<id> <name> tokens:<n> stop:<reason> H̄:<mean entropy> minH:<min> at p<pos>` in causal order. Exit 0 with rows, 1 with none. |
| `tokens <run> --gen <name> [--from P --to Q] [--min-margin X]` | **New.** Token rows with piece, logprob, entropy, top-k. `--min-margin X` keeps positions where the top-1/top-2 gap ≤ X (the "swallowed uncertainty" view). `--gen` exact-first, then unique prefix, as `--fn` does. |
| `spans <run> --gen <name>` | **New.** The generation's prompt/action/answer/stop spans with refs; `action` prints `exec run <id> exit …` or `not run`. |
| `diff A B` | §6. Auto-dispatches on `lang == "model"` both sides; mixed → exit 2 `REFUSED: A is a model trace and B is a program trace; diff compares like with like`. |
| `bless-noise A B` | **New**, §6. |
| `tree`, `frame`, `grep`, `flow`, `watch`, `exceptions`, `refocus` | **Refuse with exit 2** and one sentence: `REFUSED: <cmd> reads program <frames|events|…>; this is a model trace (recorder <r>) -- use gens/tokens/spans`. `flow`/`watch` already refuse via `line: false` (exit 3); the model-trace sentence takes precedence because the fix is a different command, not a different recording. `exceptions` already refuses on an unknown lang; its wording is replaced by the same sentence on `lang == "model"`. |

`vocab.terms()` gains the `MODEL` column (§1). `exit_phrase` gains `n/a (model trace)` for
basis `not-a-process-exit`.

None of these commands exists in 0.8.1; this table is what S1 implements and what `pending/m01–m10.json` pin.
