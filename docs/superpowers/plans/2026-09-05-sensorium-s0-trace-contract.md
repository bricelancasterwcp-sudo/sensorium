# S0 — Trace contract (cross-trace join + model recorder) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the format-5 model-trace contract, the cross-trace join, and the `signature` reading as documentation and pending conformance vectors on `feat/s0-trace-join`, with no recorder or query code.

**Architecture:** The contract text lives in a new `docs/trace-format/MODEL-TRACES.md` (TRACE-FORMAT.md is at 752 of its 800-line ceiling and keeps only a format-5 row, one-line pointers, and the two rules that change for every recorder). Vectors that no builder can yet write go under `docs/trace-format/vectors/pending/`, which `tests/vectors.load_all` cannot see (`VECTORS.glob("v*.json")`, non-recursive). The model recorder's honesty ledger is written before its code, as the Rust one was.

**Tech Stack:** Markdown, JSON, SQLite DDL (documented, not executed), pytest only as a no-regression check (docs slice — every test that passes on `e307d90` must pass unchanged).

**Spec:** `docs/superpowers/specs/2026-09-05-sensorium-trace-join-and-model-recorder-design.md` (rulings R1–R10 in §11; §12 RULED 2026-09-05: `topk` 8, recorder off by default, `bless-noise` writes into A).

## Global Constraints

- **Docs only.** No file under `src/`, `rust/`, `tests/` is modified. `python3 -m pytest -q tests/test_vectors.py` must report the same count before and after every task (19 vectors on `e307d90`).
- **Branch discipline (Brice, 2026-09-05):** all work on `feat/s0-trace-join` in worktree `/mnt/extra/sensorium-rung2/s0-trace-join`; never touch `main` or `~/workspace/sensorium` (another session owns the Rust recorder there). Commits **by path** (`git add <files>`), never `git add -A`; verify each commit with `git show --stat HEAD` names only your files.
- `docs/TRACE-FORMAT.md` stays **≤ 800 lines** (`wc -l`).
- Every JSON fence in a new doc must parse. Where the spec writes `a | b` alternatives inside JSON, the doc gives **one concrete value** in the fence and lists the alternatives in a table beneath it.
- No placeholders: no "TBD/TODO", no falsifier left unnamed.
- Commit message trailer on every commit:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_011t9v9n3SV72XoTe6ipqDaD
  ```
  Commit with `git -c core.hooksPath=/dev/null commit -F -` and a quoted heredoc (backticks in `-m` get shell-substituted — a measured failure). **If you drive a shell from a heredoc yourself, use a unique terminator — a plan containing `EOF` inside its own code blocks truncated this file once.**

---

## File structure

| Path | Responsibility | Task |
|---|---|---|
| `docs/trace-format/MODEL-TRACES.md` (new) | The model-trace contract: vocabulary, meta, tables, capabilities, fingerprints/diff/noise band, the join, `signature`, command table | T1 |
| `docs/TRACE-FORMAT.md` (modify) | Format-5 row; pointers; `not-a-process-exit`; `join` as a shared optional key; model vocabulary column; the ts_ns cross-file rule; per-generation basis pointer | T2 |
| `docs/trace-format/vectors/pending/README.md` (new) + `m01`–`m10`, `p01` `.json` (new) | Pending conformance vectors, promoted to `vectors/` in S1 | T3 |
| `model/HONESTY.md` (new) | The model recorder's honesty ledger, promises with named falsifiers | T4 |
| `docs/CARRIED-DEBT.md` (modify, insert newest-first) | What S0 settled / deferred / lessons; then push + draft PR | T5 |

---

### Task 1: `docs/trace-format/MODEL-TRACES.md` — the contract text

**Files:**
- Create: `docs/trace-format/MODEL-TRACES.md`
- Read: the spec §2–§6 (source of every sentence), `docs/TRACE-FORMAT.md` §3–§7 (the style and the rules being extended), `docs/trace-format/VECTORS.md` lines 1–4 (the "moved out to keep under 800" header shape).

**Interfaces:**
- Consumes: spec sections §2 (vocabulary table), §3.2 (meta table), §3.3 (DDL + `spans.ref`), §3.4 (capabilities JSON), §3.5, §4.1–4.3, §5.1–5.4, §6 (command table).
- Produces: section anchors the other tasks point at, **exactly these headings**:
  `## 1. Subject and vocabulary`, `## 2. Meta`, `## 3. Tables`, `## 4. Capabilities`,
  `## 5. One trace per boot`, `## 6. Fingerprints and diff`, `## 7. The join`,
  `## 8. signature`, `## 9. Commands on a model trace`.

- [ ] **Step 1: Write the header** (mirror VECTORS.md's split note):

```markdown
# Model traces (trace format 5)

> The contract for the third recorder kind, `sensorium-model` (S1 of the sensor-suite program).
> Kept out of `docs/TRACE-FORMAT.md` so that file stays under its 800-line ceiling; TRACE-FORMAT
> §1 names format 5 and points here. Design: `docs/superpowers/specs/2026-09-05-sensorium-trace-join-and-model-recorder-design.md`.
> **Status 2026-09-05: contract only.** No recorder writes this format yet; sensorium 0.8.1 refuses
> a format-5 file by TRACE-FORMAT §1's newer-format rule, which is the intended behavior until S1.
```

- [ ] **Step 2: Write §1–§9** by transcribing the spec sections named in *Consumes*, with these edits and no others:
  1. Spec §3.2's meta table → §2 verbatim, plus one sentence after it: "The required set is `db.REQUIRED_META`, unchanged; format 5 adds no required key."
  2. Spec §3.3 DDL → §3 verbatim inside a ```sql fence; the `spans.ref` table follows it.
  3. Spec §3.4 capabilities JSON → §4 in a ```json fence **exactly as in the spec** (it is already valid JSON).
  4. Spec §5.2's `join` example → §7 as **one concrete value**: `"role": "model"`, `"gen": "g5-mixed/patch-07"`, `"pid": 41213`, `"anchor": {"clock": "monotonic", "process": 41213}`; the role alternatives go in a three-row table under the fence (`model` / `program` / `harness`, one line each on who writes it).
  5. Spec §5.4's `signature` example → §8 as one concrete value: `"outcome": "raised"`, `"exc": {"type": "TypeError", "kind": null}`, `"disposition": "PROPAGATED"`, `"fork": {"qualname": "unit_17.helper", "kind": "RAISE", "depth": 2}`, `"closed_by": "unwind"`; the alternatives for `outcome`/`disposition`/`closed_by` go in a table.
  6. Spec §6's command table → §9 verbatim, then one closing line: "None of these commands exists in 0.8.1; this table is what S1 implements and what `pending/m01–m10.json` pin."
  7. §5 (one trace per boot) closes with the RULED §12 facts as a dated line: "Ruled 2026-09-05: `topk` default 8; recording is off by default and enabled by daemon config; `bless-noise` writes `noise_band` into A."

- [ ] **Step 3: Verify the document**

Run (from the worktree):
```bash
F=docs/trace-format/MODEL-TRACES.md
grep -c '^## ' $F                      # expect 9
for h in "1. Subject and vocabulary" "2. Meta" "3. Tables" "4. Capabilities" "5. One trace per boot" "6. Fingerprints and diff" "7. The join" "8. signature" "9. Commands on a model trace"; do grep -q "^## $h" $F || echo "MISSING: $h"; done
grep -c 'CREATE TABLE tokens\|CREATE TABLE spans\|per-generation\|not-a-process-exit\|bless-noise\|signature-v1\|flash_attention' $F   # expect ≥ 7
python3 - <<'PYCHECK'
import re,json
s=open("docs/trace-format/MODEL-TRACES.md").read()
fences=re.findall(r"```json\n(.*?)```", s, re.S)
assert fences, "no json fences"
for f in fences: json.loads(f)
print(len(fences), "json fences parse")
PYCHECK
```
Expected: `9`, no `MISSING:` lines, count ≥ 7, `N json fences parse`.

- [ ] **Step 4: Commit** (by path; message: `docs(s0): MODEL-TRACES.md — the format-5 model-trace contract, the join, and signature` + trailer). Verify `git show --stat HEAD` lists exactly one file.

---

### Task 2: `docs/TRACE-FORMAT.md` — the amendments every recorder sees

**Files:**
- Modify: `docs/TRACE-FORMAT.md` — §1 table (~line 25–31), §3 after `### fingerprints, task_fingerprints` (~229–240), §4 `exit_status_basis` subsection (~270–289), §4 `### Optional keys, by writer` first paragraph (~400–406), §4 wording table (~467–474), §6 `ts_ns` bullet (~647), §7 last paragraph (~742–748).

**Interfaces:**
- Consumes: MODEL-TRACES.md heading anchors from Task 1.
- Produces: nothing programmatic; the pointers must name the T1 headings exactly.

- [ ] **Step 1: §1 — add the format-5 row** immediately after the `| 4 |` row:

```markdown
| 5 | **Model traces** (`lang: "model"`, recorder `sensorium-model`, S1 of the sensor-suite program): adds the `tokens` and `spans` tables, admits `fingerprint_basis: "per-generation"` and `exit_status_basis: "not-a-process-exit"`. Program recorders keep writing 4. Contract: [`trace-format/MODEL-TRACES.md`](trace-format/MODEL-TRACES.md). This sensorium (0.8.1) refuses a format-5 file by the newer-format rule below — the intended behavior until the S1 reader ships. |
```

- [ ] **Step 2: §3 — one pointer paragraph** after the `task_fingerprints` paragraph (before `## 4. Meta`):

```markdown
**Format 5 adds two tables**, `tokens` and `spans`, and reuses `tasks`/`task_fingerprints` for
generations; their DDL and NULL rules are in [MODEL-TRACES §3](trace-format/MODEL-TRACES.md#3-tables).
```

- [ ] **Step 3: §4 — the third exit basis.** After the sentence ending `nobody waited, so nothing about the ending is known.` add:

```markdown
A third basis exists from format 5: `exit_status_basis: "not-a-process-exit"` with
`exit_status: null`, written by a recorder whose trace ends because recording was closed and not
because a process ended (a model trace, MODEL-TRACES §2). The readers print `exit: n/a (model
trace)`; rendering that null as a status, or as `0`, is the same failure this key already stops.
```

- [ ] **Step 4: §4 — `join` joins the shared optional set.** In `### Optional keys, by writer`, replace `These six are the shared optional set; they are not Python-only.` with:

```markdown
These six, plus `join` — the cross-trace group and anchor object defined in
[MODEL-TRACES §7](trace-format/MODEL-TRACES.md#7-the-join), written by whichever recorder was
launched or written by a daemon session, copied verbatim from `SENSORIUM_JOIN` when that variable
holds a JSON object and omitted otherwise — are the shared optional set; they are not Python-only.
```

- [ ] **Step 5: §4 — the vocabulary table gains the model column.** Replace the six-row `| Term | Python | Rust |` table with:

```markdown
| Term | Python | Rust | model (format 5) |
|---|---|---|---|
| unit of work | `asyncio task` | `test or spawned thread` | `generation` |
| ...plural | `asyncio task(s)` | `tests or spawned threads` | `generations` |
| a nameless one | `(name unreadable)` — the name existed and `get_name()` raised | `(unnamed: spawned by dependency code)` — it never had one | `(unnamed: no fixture or goal id was supplied)` |
| where threads came from | `through Python's own threading/_thread` | `as OS threads (libtest's per-test threads and threads spawned by workspace code)` | n/a — a model trace declares `threads: false` |
| what ran the program | `python <meta.python>` | `toolchain: <meta.toolchain>` | `model: <meta.model.name> via <meta.model.engine>` |
| a runtime-minted name | `Task-N` is read as no name at all | none exist; every name is the program's | `gen-N` is read as no name at all |
```
and append one sentence after the table: "The model column is contract only until S1 lands it in `query/vocab.py`; `terms()` today falls back to the Python column for any third `lang`, which is the known limit the module's docstring states."

- [ ] **Step 6: §6 — the one cross-file exception for `ts_ns`.** After the bullet beginning `**`ts_ns` is monotonic**` add a bullet:

```markdown
- **`ts_ns` is comparable across two trace files in exactly one case:** both carry `join.anchor`
  with `clock == "monotonic"` and the same `process` — one process wrote both (a daemon's model
  trace and its `cargo-sensorium` harness trace). A reader that aligns them labels every such
  fact `by clock`, never `by order`, and refuses the alignment when either anchor is absent
  (MODEL-TRACES §7).
```

- [ ] **Step 7: §7 — the per-generation basis.** Append to the final paragraph of §7:

```markdown
Format 5 adds a third basis, `"per-generation"`: one row per generation, the digest over sampled
token ids only (MODEL-TRACES §6). `diff` never compares a per-generation trace with either program
basis; that refusal exits 2 (a different call), not 3.
```

- [ ] **Step 8: Verify**

```bash
wc -l docs/TRACE-FORMAT.md                                   # ≤ 800
grep -c 'MODEL-TRACES' docs/TRACE-FORMAT.md                  # expect ≥ 6
grep -n 'not-a-process-exit\|per-generation\|by clock\|gen-N' docs/TRACE-FORMAT.md | wc -l   # expect ≥ 5
grep -n '^| 5 |' docs/TRACE-FORMAT.md                        # one row
python3 -m pytest -q tests/test_vectors.py 2>&1 | tail -2    # same pass count as before the task
```

- [ ] **Step 9: Commit** (by path; message: `docs(s0): TRACE-FORMAT — format 5 row, join as a shared optional key, not-a-process-exit, the ts_ns clock-anchor rule, per-generation basis` + trailer).

---

### Task 3: Pending conformance vectors `m01`–`m10`, `p01`

**Files:**
- Create: `docs/trace-format/vectors/pending/README.md`, `docs/trace-format/vectors/pending/m01-format5-refused-by-format4-reader.json` … `m10-zero-token-generation-row.json`, `p01-signature-canonical-json.json`.
- Read: `docs/trace-format/VECTORS.md` (the vector schema and the `$RUN`/`$RUN2` rule), `docs/trace-format/vectors/v04-main-thread-silent-tasks-carry.json` for shape.

**Interfaces:**
- Consumes: MODEL-TRACES §9 command names and refusal sentence; spec §9 table.
- Produces: JSON files S1's builder will load once `tests/vectors.py` learns `tokens`/`spans` and the `pending/` promotion happens. Two **new top-level keys** beyond VECTORS.md's schema: `"tokens"` and `"spans"` (lists of row objects with MODEL-TRACES §3 column names); `"tasks"` rows are `[id, name, thread]` as today. Two-trace vectors carry `meta2`/`tokens2`/`spans2` for the second trace (`$RUN2`).

- [ ] **Step 1: Write `pending/README.md`**

```markdown
# Pending vectors

Vectors whose rows no builder can write yet. `tests/vectors.load_all` globs `vectors/v*.json`
non-recursively, so nothing here runs. **Promotion rule:** a pending vector moves to `../` (and
is renamed `vNN-…`) in the same commit that teaches `tests/vectors.py` to build its rows; it may
not be promoted before it passes. Authored 2026-09-05 (S0); promotion is S1's first task.

Keys beyond VECTORS.md: `tokens` (rows: task, pos, token, piece, logprob, entropy, topk, ts),
`spans` (rows: task, kind, first_pos, last_pos, text, ref), and for two-trace vectors `meta2`
(`{"same_as": "meta", ...overrides}`), `tokens2`, `spans2`, `absent2` (the second trace is
deliberately missing). Question keys beyond VECTORS.md: `expect_absent` (substrings that must not
appear), `expect_col0` (a line that must start at column 0), `expect_same_key` (the printed
`"key"` equals the previous question's). `$RUN`/`$RUN2` substitute as in VECTORS.md.
```

- [ ] **Step 2: Write `m04-diff-first-divergence-and-margin.json`** (in full):

```json
{"id": "m04-diff-first-divergence-and-margin",
 "asserts": "diff on two model traces pairs generations by name, names the first divergent position with both pieces and both margins, and reports a token outside the other side's top-k as '> topk-floor' rather than as a number",
 "meta": {"trace_format": 5, "incomplete": false, "run_id": "$RUN", "lang": "model", "recorder": "sensorium-model 0.1.0",
          "fingerprint_basis": "per-generation", "exit_status": null, "exit_status_basis": "not-a-process-exit",
          "topk": 2, "main_thread_ident": 1, "truncated_count": 0, "source_hashes": {},
          "capabilities": {"line": false, "locals": false, "return_value": false, "tasks": true, "threads": false,
                           "children": false, "stdin": false, "output": false, "object_identity": false, "refocus": false,
                           "tokens": true, "topk": true, "entropy": true, "spans": true,
                           "routing": false, "activations": false, "attention": false},
          "model": {"name": "fixture-model", "engine": "llama.cpp", "engine_build": "b10200", "weights_path": "/w/m.gguf",
                    "weights_sha256": "00", "adapters": [], "n_ctx": 4096, "n_vocab": 8, "backend": "vulkan",
                    "sampler": {"kind": "greedy"}, "flash_attention": true}},
 "meta2": {"same_as": "meta", "run_id": "$RUN2"},
 "tasks": [[1, "fx/patch-01", 1]],
 "tokens": [{"task": 1, "pos": 0, "token": 3, "piece": "The", "logprob": -0.10, "entropy": 0.30, "topk": [[3, -0.10], [5, -2.40]], "ts": 1000},
            {"task": 1, "pos": 1, "token": 5, "piece": " fix", "logprob": -0.20, "entropy": 0.60, "topk": [[5, -0.20], [6, -1.70]], "ts": 2000}],
 "tokens2": [{"task": 1, "pos": 0, "token": 3, "piece": "The", "logprob": -0.10, "entropy": 0.30, "topk": [[3, -0.10], [5, -2.40]], "ts": 1000},
             {"task": 1, "pos": 1, "token": 7, "piece": " patch", "logprob": -0.90, "entropy": 1.10, "topk": [[7, -0.90], [5, -1.00]], "ts": 2000}],
 "spans": [], "spans2": [],
 "fingerprints": "compute",
 "questions": [{"id": "first-divergence-named",
                "ask": "Does diff name generation fx/patch-01, position 1, pieces ' fix' vs ' patch'?",
                "command": ["diff", "$RUN", "$RUN2"],
                "expect_exit": 1,
                "expect_line": [["fx/patch-01", "p1"], [" fix", " patch"]]},
               {"id": "margin-outside-topk-is-not-a-number",
                "ask": "Under A's distribution token 7 is outside top-2: is the margin printed as '> topk-floor' and under B's as 0.10?",
                "command": ["diff", "$RUN", "$RUN2"],
                "expect_exit": 1,
                "expect_line": [["margin", "> topk-floor"], ["margin", "0.10"]]}]}
```

- [ ] **Step 3: Write `m06-exit-status-not-a-process-exit.json`** (in full):

```json
{"id": "m06-exit-status-not-a-process-exit",
 "asserts": "a model trace's null exit_status with basis not-a-process-exit renders as 'exit: n/a (model trace)' and never as None or 0",
 "meta": {"trace_format": 5, "incomplete": false, "run_id": "$RUN", "lang": "model", "recorder": "sensorium-model 0.1.0",
          "fingerprint_basis": "per-generation", "exit_status": null, "exit_status_basis": "not-a-process-exit",
          "topk": 8, "main_thread_ident": 1, "truncated_count": 0, "source_hashes": {},
          "capabilities": {"line": false, "locals": false, "return_value": false, "tasks": true, "threads": false,
                           "children": false, "stdin": false, "output": false, "object_identity": false, "refocus": false,
                           "tokens": true, "topk": true, "entropy": true, "spans": true,
                           "routing": false, "activations": false, "attention": false},
          "model": {"name": "fixture-model", "engine": "llama.cpp", "engine_build": "b10200", "weights_path": "/w/m.gguf",
                    "weights_sha256": "00", "adapters": [], "n_ctx": 4096, "n_vocab": 8, "backend": "vulkan",
                    "sampler": {"kind": "greedy"}, "flash_attention": true}},
 "tasks": [[1, "fx/patch-01", 1]],
 "tokens": [{"task": 1, "pos": 0, "token": 3, "piece": "ok", "logprob": -0.05, "entropy": 0.10, "topk": [[3, -0.05]], "ts": 1000}],
 "spans": [{"task": 1, "kind": "stop", "first_pos": 0, "last_pos": 0, "text": null, "ref": {"reason": "eog"}}],
 "fingerprints": "compute",
 "questions": [{"id": "info-exit-na", "ask": "Does info print exit: n/a (model trace)?", "command": ["info", "$RUN"], "expect_exit": 0,
                "expect_line": [["exit:", "n/a (model trace)"]], "expect_absent": ["exit: None", "exit: 0"]},
               {"id": "runs-exit-na", "ask": "Does runs show exit:n/a for the row?", "command": ["runs"], "expect_exit": 0,
                "expect_line": [["$RUN", "exit:n/a"]]}]}
```

- [ ] **Step 4: Write the remaining nine vectors** using the `m06` meta block verbatim as the canonical model-trace meta (change only what the row says):

| file | rows | questions (command → expect_exit; expect_line pairs) |
|---|---|---|
| `m01-format5-refused-by-format4-reader.json` | m06 rows + top-level `"harness": {"reader_max_format": 4}` (the builder runs the question through a reader pinned at 4) | `["info","$RUN"]` → 2; `[["is trace format 5, newer than this sensorium reads (up to 4)", "upgrade sensorium"]]` |
| `m02-model-trace-program-commands-refuse.json` | m06 rows | four questions, one per command `tree`/`frame --fn x`/`grep --kind RETURN`/`exceptions`, each → 2 with `[["REFUSED:", "reads program"], ["this is a model trace", "use gens/tokens/spans"]]` |
| `m03-gens-unnamed-pairs-by-order.json` | two traces (`meta2`), `tasks` `[[1,"gen-1",1],[2,"gen-2",1]]` on both, identical tokens on gen-1, one differing token at pos 0 on gen-2 | `["diff","$RUN","$RUN2"]` → 1; `[["gen-2", "unnamed"], ["p0"]]`; `["gens","$RUN"]` → 0; `[["g1", "gen-1"], ["g2", "gen-2"]]` |
| `m05a/b/c-diff-within-noise-needs-blessed-band.json` (three files) | as m04 but B's pos-1 token 6 with both tokens in each other's top-2 and margins 0.05/0.07. **a**: no `noise_band` → 1 `[["DIVERGED"]]`. **b**: A's meta adds `"noise_band": {"basis":"two-identical-boots","against":"$RUN2","max_margin":0.10,"positions":1,"gens":1}` → 0 `[["MATCH (within noise)", "$RUN2"]]`. **c**: as b but A's `weights_sha256` `"01"` → 3 `[["REFUSED", "weights_sha256"]]` | as stated per file |
| `m07-spans-exec-ref-joins-program-trace.json` | `spans` `[{"task":1,"kind":"action","first_pos":0,"last_pos":0,"text":"<action verb=\"run\">python3 -m unittest</action>","ref":{"verb":"run","attrs":{},"exec":{"run_id":"$RUN2","exit_status":1,"exit_status_basis":"waited"}}}]`; `meta2` is a **format-4 Python** trace (`lang: python`, `recorder: "sensorium 0.8.1"`, `exit_status: 1`, the ordinary required set) | `["spans","$RUN","--gen","fx/patch-01"]` → 0; `[["exec run", "$RUN2"], ["exit 1 (waited)"]]`; second question with `"absent2": true` → 0; `[["exec run", "(trace not found)"]]` |
| `m08-join-group-in-runs.json` | m06 meta + `"join": {"group":"sess-20260905-01","role":"model","gen":null,"pid":41213,"anchor":{"clock":"monotonic","process":41213}}`; `meta2` a format-4 Python trace **without** `join` | `["runs"]` → 0; `[["session sess-20260905-01:", "fixture-model"], ["  $RUN"]]`, plus `"expect_col0": ["$RUN2"]` |
| `m09-attention-declared-unwitnessable-under-fa.json` | m06 meta (`flash_attention: true`) | `["info","$RUN"]` → 0; `[["attention", "not witnessed"], ["flash_attention_on"]]`; `expect_absent: ["attention: 0", "predates"]` |
| `m10-zero-token-generation-row.json` | `tasks` `[[1,"fx/empty",1]]`, `tokens: []`, `spans` one `stop` row `{"reason":"eog"}` with `first_pos: null, last_pos: null`; `meta2` identical | `["gens","$RUN"]` → 0; `[["g1", "fx/empty", "tokens:0", "stop:eog"]]`; `["diff","$RUN","$RUN2"]` → 0; `[["MATCH"]]` |
| `p01-signature-canonical-json.json` | a **format-4 Python** trace: `codes` `[["/w/unit_17.py","unit_17.helper",3],["/w/unit_17.py","unit_17.run",9]]`; `frames` run (depth 0, `closed_by: unwind`) → helper (depth 1, `closed_by: unwind`), both `unwind_exc: {"type":"TypeError","msg":"bad","oid":1}`; events CALL run, CALL helper, RAISE helper (exc same), no RETURN | `["signature","$RUN","--json"]` → 0; `[["\"basis\": \"signature-v1\""], ["\"outcome\": \"raised\""], ["\"qualname\": \"unit_17.helper\""], ["\"disposition\": \"PROPAGATED\""]]`; `expect_absent: ["\"msg\""]`; second question: same rows with both `codes[*][0]` = `/w/unit_18.py` → `"expect_same_key": true` |

- [ ] **Step 5: Verify**

```bash
ls docs/trace-format/vectors/pending/ | wc -l                # 14 (README + 13 files)
for f in docs/trace-format/vectors/pending/*.json; do python3 -c "import json; json.load(open('$f'))" || echo "BAD JSON: $f"; done
python3 -c "from tests.vectors import load_all; print(len(load_all()))"   # 19 — pending excluded
python3 -m pytest -q tests/test_vectors.py 2>&1 | tail -1
```

- [ ] **Step 6: Commit** (by path `docs/trace-format/vectors/pending/`; message: `docs(s0): pending conformance vectors m01–m10 + p01 for model traces and signature` + body `Not built: tests/vectors.load_all globs v*.json non-recursively. Promoted in S1 with the builder that can write tokens/spans rows.` + trailer).

---

### Task 4: `model/HONESTY.md` — the ledger before the recorder

**Files:**
- Create: `model/HONESTY.md`
- Read: `rust/HONESTY.md` lines 1–50 (header + "How to read a section" + "Provenance" shape), spec §8 (the ten promises), spec §10 (the endpoints that double as falsifiers).

**Interfaces:**
- Consumes: the ten promises of spec §8; vector ids from Task 3; endpoint names E-noise, E-noise′, E-adapter, E-mem, E-overhead.
- Produces: the falsifier names S1's plan must implement — **exact test/vector names below are obligations**; S1's plan references them verbatim.

- [ ] **Step 1: Write the header:**

```markdown
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
```

- [ ] **Step 2: Write the ten sections**, `## 1` … `## 10`, one per spec-§8 promise, each with exactly three labelled paragraphs — **Promise**, **What says it**, **Falsifier** — from this table:

| § | Promise (spec §8) | What says it | Falsifier |
|---|---|---|---|
| 1 | a `tokens` row is a sampled token | `tokens.token` = the id `sampler.sample` returned, written after sampling | `tests/test_model_writer.py::test_row_per_sampled_token_only` (S1); E-noise's kill (a divergence at p=0) |
| 2 | logprob/entropy over the full vocabulary or declared false | `capabilities.entropy`, `meta.model.n_vocab` | `tests/test_model_writer.py::test_entropy_matches_reference_softmax_over_n_vocab` (S1); E-overhead's fallback clause |
| 3 | `topk` is the true top-k, descending, ties by id | `tokens.topk`, `meta.topk` | `tests/test_model_writer.py::test_topk_is_sorted_prefix_of_full_distribution` (S1) |
| 4 | fingerprint over token ids only | `fingerprint_basis: per-generation`, `task_fingerprints.hash` | `m05b` (identical ids, different logprobs → equal hash) |
| 5 | names are the caller's; `gen-N` is unnamed | `tasks.name` | `m03-gens-unnamed-pairs-by-order` |
| 6 | spans are the scanner's judgement | `meta.spans_basis`, `spans.ref.boundary_inside_token` | `tests/test_model_spans.py::test_boundary_inside_multibyte_token_is_flagged` (S1); E-mem |
| 7 | `exec.run_id` is the id passed to the child or null | `spans.ref.exec.run_id`, `SENSORIUM_JOIN` | `m07-spans-exec-ref-joins-program-trace`; `tests/test_join_env.py::test_join_copied_verbatim_or_omitted` (S3) |
| 8 | `noise_band` only on a blessed trace, naming its baseline | `meta.noise_band.against` | `m05c` (REFUSED when weights differ); E-noise′ |
| 9 | nothing says why; attention under FA declared unwitnessable | `capabilities.attention: false`, `witness_gap: flash_attention_on` | `m09-attention-declared-unwitnessable-under-fa` |
| 10 | cost reported, never gated | E-overhead published either way | the acceptance record carries the ratio whichever way it reads: `docs/superpowers/acceptance/<S1 date>-model-recorder.md` §E-overhead |

- [ ] **Step 3: Write the index** as the last section, `## Index: promise → falsifier`, a two-column table of the ten rows, matching rust/HONESTY.md's closing section.

- [ ] **Step 4: Verify**

```bash
grep -c '^## ' model/HONESTY.md                 # 11 (ten promises + index)
grep -c '^\*\*Falsifier' model/HONESTY.md        # 10
grep -c 'TBD\|TODO' model/HONESTY.md             # 0
grep -o 'm0[0-9][a-z0-9-]*\|p01[a-z0-9-]*' model/HONESTY.md | sort -u | while read v; do ls docs/trace-format/vectors/pending/ | grep -q "^$v" || echo "names a vector that does not exist: $v"; done
```

- [ ] **Step 5: Commit** (by path; message: `docs(s0): model/HONESTY.md — the model recorder's promises, each with a named falsifier, before any code` + trailer).

---

### Task 5: CARRIED-DEBT, push, draft PR

**Files:**
- Modify: `docs/CARRIED-DEBT.md` — insert a new dated section **above** `## 2026-09-05 — rung 3, Err flow` (newest first).

- [ ] **Step 1: Insert the section**

```markdown
## 2026-09-05 — S0, trace contract for the sensor-suite program (docs only; no version moves)

### Settled
- Trace format 5 defined for model traces (`docs/trace-format/MODEL-TRACES.md`): `tokens` + `spans`
  tables, generations as `tasks` rows, `lang: "model"`, `fingerprint_basis: "per-generation"`,
  `exit_status_basis: "not-a-process-exit"`. Program recorders stay on 4.
- The cross-trace join: `meta.join` (shared optional key), references over clocks, the one
  same-process `ts_ns` exception (TRACE-FORMAT §6).
- `signature` reading for program traces (MODEL-TRACES §8) — requested by crucible phase D.
- Design spec rulings R1–R10; Brice ruled §12 as recommended (topk 8, recorder off by default,
  `bless-noise` writes into A). Ledger: `.superpowers/sdd/2026-09-05-sensorium-s0-trace-contract/`.

### Deferred, awaiting S1 (each named where it lands)
- `query/vocab.py` model column; `exit_phrase` `n/a (model trace)`; `Trace` format-5 reader;
  `gens`/`tokens`/`spans`/`bless-noise`/`signature` commands; program-command refusals on a model
  trace (exit 2) — all pinned by `vectors/pending/m01–m10, p01`, promoted with the builder.
- `tests/vectors.py` must learn `tokens`/`spans` rows, two-trace vectors (`meta2`/`tokens2`), a
  pinned-reader harness (`m01`), `expect_absent`, `expect_col0`, `expect_same_key` — record each
  in VECTORS.md at promotion.
- README's three "trace format 4" sentences (lines ~345/387/578) stay true for program traces;
  add the format-5 sentence when the recorder ships, not before.
- `SENSORIUM_JOIN` → `meta.join` copy in `record/boot.py` (S3), with `tests/test_join_env.py`.

### Process lessons
- A docs-only slice still needs a pytest run per task: `test_vectors.py`'s count is the fence that
  `pending/` stayed invisible.
- The S2 fork's reading of GATE-B/C found seven plan-level corrections before any pre-registration
  was written; brief a fresh reader on the findings docs before locking anything.
- Design authority used for R1–R10 with cost-if-wrong recorded; Brice reviewed the spec, not each
  ruling — the ledger is what makes that reviewable later.
- A plan that quotes shell heredocs must be written with a unique outer terminator; `EOF` inside
  a code block truncated this plan's first write and ran its tail as shell (harmless, caught by
  `git log`/`git status` before anything else).
```

- [ ] **Step 2: Verify and commit**

```bash
grep -n '^## 2026-09-05 — S0' docs/CARRIED-DEBT.md          # present, above the rung-3 section
python3 -m pytest -q tests/test_vectors.py 2>&1 | tail -1
```
Commit by path (`docs/CARRIED-DEBT.md`; message: `docs(s0): CARRIED-DEBT — what the trace-contract slice settled and what S1/S3 owe` + trailer).

- [ ] **Step 3: Push the branch and open a DRAFT PR (not to be merged — Brice's ruling)**

```bash
git push -u origin feat/s0-trace-join
gh pr create --draft --base main --head feat/s0-trace-join \
  --title "docs(s0): trace contract — format 5 model traces, cross-trace join, signature" \
  --body "$(cat docs/superpowers/plans/2026-09-05-sensorium-s0-trace-contract.md | sed -n '/^## PR body/,/^## END PR body/p' | sed '1d;$d')"
git fetch origin && git status -sb | head -1                # no ahead/behind
```

## PR body
S0 of the sensor-suite program (docs + pending vectors only; no code, no version moves).

**Do not merge yet** — Brice ruled 2026-09-05 that this program's sensorium work stays off `main` while another session works the Rust recorder there. Merge is Brice's.

- Spec: `docs/superpowers/specs/2026-09-05-sensorium-trace-join-and-model-recorder-design.md` (R1–R10; §12 ruled)
- Contract: `docs/trace-format/MODEL-TRACES.md`; TRACE-FORMAT amendments (format-5 row, `join`, `not-a-process-exit`, ts_ns clock-anchor rule, per-generation basis)
- Pending vectors `m01–m10`, `p01` (promoted in S1)
- `model/HONESTY.md` written before the recorder
- CARRIED-DEBT entry

`pytest tests/test_vectors.py`: unchanged count (19) — `pending/` is invisible to the loader.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_011t9v9n3SV72XoTe6ipqDaD
## END PR body

---

## Self-review (done at authoring)

- **Spec coverage:** §2→T1§1+T2 step 5; §3.1→T2 step 1; §3.2–3.5→T1§2–5; §4→T1§6+T2 step 7; §5→T1§7+T2 steps 4/6; §5.4→T1§8+p01; §6→T1§9+m02; §8→T4; §9→T3; §10→T4 falsifiers reference E-*; §11/§12→T5 CARRIED-DEBT. Spec §7 (bloomery seam) is S1's — deliberately no task.
- **Placeholders:** none; every falsifier and vector is named.
- **Consistency:** exit codes — mixed subjects 2 (T2 step 7, m02), REFUSED recording 3 (m05c), DIVERGED 1 (m04, m05a), MATCH 0 (m10, m05b) — match spec §4.2/§6. Heading anchors used by T2 match T1's *Produces* list. m05 is three files (a/b/c) because one vector cannot vary `meta` per question; T3 step 5's count (14) and T4's falsifiers (`m05b`, `m05c`) agree.
