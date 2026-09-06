# Rung 4 slice 1 — the focus tier — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `cargo sensorium --focus <qualname> test|run` records one LINE event per completed statement of each focused Rust function, its `deltas` the bindings the statement wrote, so `watch` and `flow` answer on a Rust trace — measured once under a pre-registered E9 on the bloomery clone.

**Architecture:** The driver resolves each focus value against the workspace before building and refuses an unmatched one (exit 2). The wrapper hands the focus list to the transform through `SENSORIUM_FOCUS`; the transform marks matching functions and splices a `line` probe after every statement in them (new `SiteKind::Line` sites, one per statement). The runtime gains wire kind 6 and a `line(...)` entry point that captures each named delta through the existing Debug-or-unread ladder. The converter writes LINE rows in the Python payload shape, records `focus`/`focus_matched`, and declares `line`/`locals` true only when a LINE site exists. The Python query side learns the `::` prefix boundary and gives `dbg` captures a defined meaning. Everything else is unchanged; an unfocused build compiles byte-for-byte as today.

**Tech Stack:** Rust (`syn` source-rewrite transform, `sensorium-rt` spool, `cargo-sensorium` driver/converter, SQLite), Python 3.12+ (`sensorium` query CLI, pytest), the E6q-family acceptance runner pattern.

**Spec:** `docs/superpowers/specs/2026-09-06-sensorium-rung4-focus-tier-design.md` (design authority: Claude; rulings F1–F3 and the three approved sections are binding; §7 is E9's pre-registration in prose, which Task 0 turns into the locked §1).

## Global Constraints

- **Branch** `feat/rung4-focus-tier` off main `9db30d0`, worked in the main checkout `~/workspace/sensorium`; never push `main`; the merge is Brice's. The S0 session owns `/mnt/extra/sensorium-rung2/s0-trace-join` and PR #17 — never touch either.
- **Versions**: `sensorium-rt` 0.3.0 → **0.4.0**, `sensorium-transform` 0.3.1 → **0.4.0**, `cargo-sensorium` 0.3.1 → **0.4.0**, Python `pyproject.toml` 0.8.2 → **0.8.3**; `TRACE_FORMAT` stays **4**. Crate bumps land in the task that first changes the crate; the Python bump in Task 9.
- **`docs/TRACE-FORMAT.md`** is PR #17's to restructure. This slice touches exactly two places (design §5): the `capabilities` prose for `line`/`locals` and one sentence in the `LINE` payload row. If #17 has merged, merge `main` into this branch before Task 9.
- **The pre-registration** (E9 §1) is committed ALONE (Task 0), byte-locked by `awk '/^## 1/,/^## 2/' <doc> | sha256sum`, and never edited afterwards; dated amendments only, both readings pre-committed; one measurement; a `.FAILED` before any number is infrastructure, after a number a STOP.
- **Box rules**: every cargo target under `/mnt/extra/sensorium-rung2/` (`CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target` for the workspace; a FRESH `bloomery-target-e9` for E9); one cargo at a time (`pgrep -a cargo` empty first); root disk ≈12 GB free — nothing large on it; `/mnt/extra/sensorium-rung2/bloomery` (e209ed9) is READ-ONLY; never `pkill -f`; long runs `setsid nohup … &` with a pid file and `.DONE`/`.FAILED` markers.
- **Repo hygiene**: no box-local path in a committed file except the acceptance record's lens/pin rows and this plan; every file ≤ 800 lines (`wc -l` at each commit; split before, not after); commits by explicit path (never `git add -A`, never `.superpowers/`); every commit ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01D5ALVP7MSxhfTzxp4TFDPn`; `docs/superpowers/specs/2026-09-02-query-cli-exit-status-finding.md` is Brice's — never modify.
- **Tests**: every new behaviour is pinned by a test that FAILS under a one-line mutation of the pinned line (report the mutant); Python runs with `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` after purging `__pycache__`; Rust with `cargo test -p <crate>` under the workspace target. None-vs-zero: an unmeasured value is `None` and named, never `0`.
- **Notation** (designing-notation-for-llms): every new spelling is one the model already knows (`--focus`, `LINE`, `deltas`, `REFUSED:` sentences in the existing shape); the exit codes follow the rung-3 convention (`BAD_CALL` = 2, `UNSETTLED` = 3).

---

## File map

| file | responsibility in this slice |
|---|---|
| `rust/sensorium-rt/src/spool.rs` | `KIND_LINE = 6`; the record grammar comment gains the LINE payload |
| `rust/sensorium-rt/src/line.rs` (new) | `write_line_payload`, the `line(...)` entry point, per-field caps, the dropped-deltas flag |
| `rust/sensorium-transform/src/focus.rs` (new) | `Focus::parse(&str)`, `Focus::matches(&self, qualname)`, `focus_hash` |
| `rust/sensorium-transform/src/lines.rs` (new) | the statement walk for focused fns: statement/arm/param probe fragments, `SiteKind::Line` sites |
| `rust/sensorium-transform/src/visit.rs` | `fn_item` consults the focus after `classify`; body walk delegates to `lines.rs` when focused |
| `rust/sensorium-transform/src/lib.rs` | `SiteKind::Line`; `transform`/`transform_file` gain `focus: &Focus` |
| `rust/cargo-sensorium/src/driver.rs` | `--focus` parsing into `DriverArgs`; `SENSORIUM_FOCUS`; resolution + refusal |
| `rust/cargo-sensorium/src/resolve.rs` (new) | the resolve-only workspace walk: `resolve_focus(ws_root, &Focus) -> Resolution` |
| `rust/cargo-sensorium/src/wrapper.rs`, `mirror.rs` | read `SENSORIUM_FOCUS`; stamp `tool_hash:focus_hash:source_hash` |
| `rust/cargo-sensorium/src/convert/spool/line.rs` (new) | `parse_line_payload` |
| `rust/cargo-sensorium/src/convert/frames.rs` | the `KIND_LINE` arm → `events` row |
| `rust/cargo-sensorium/src/convert/manifest.rs`, `meta.rs` | `Line` sites, per-unit focus record; `focus`, `focus_matched`, conditional `line`/`locals` |
| `src/sensorium/query/watch_cmd.py`, `expr.py`, `flow_cmd.py` | `::` prefix; `dbg` in `resolve`/`matches` |
| `corpus/rust/focus_*` (6) | the printing gate |
| `rust/tests/acceptance_e9.py` (+ `_phases.py`, `_schema.py`, `render_e9.py` as needed, each ≤ 800) | E9 runner |
| `docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md` (+ `.results.json`) | the record |
| `rust/HONESTY*.md`, `docs/TRACE-FORMAT.md`, `README.md`, `rust/README.md`, `CHANGELOG.md`, `docs/CARRIED-DEBT.md`, `pyproject.toml` | Task 9 |

---

### Task 0: E9 pre-registration — §1 committed alone and locked

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md` (header + `## 1. Pre-registration` only; `## 2. Environment` … `## 5.` are headings with `(written by Task 8)`)
- Read-only inputs: `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9` — `crates/bloomery-daemon/tests/pager_obligation_test.rs` (`missing_stats_is_a_contract_violation_not_a_reply`, lines ≈250–303) and `tests/pager_codec_gate_test.rs` (`pager_with_model`, lines ≈22–31); the kept `ws` store's `results-grain-raw.json` is NOT needed.

**Interfaces:**
- Produces: the §1 table H1–H7 exactly as design §7, with the values Task 0 fills in: `N` (H3), the three `watch` triples `(qualname, expr, predicted verdict, line)` (H4), the two `flow --value` sightings `(literal, name, line)` (H5), the two focus values (H2), the lens sentence, the environment pins (clone sha `e209ed9`, the Python venv, the driver = `rust-target/debug/cargo-sensorium` built from this branch's HEAD at measurement time, whose sha256 Task 8 records).
- The lock: the commit sha and `sha256sum` of `awk '/^## 1/,/^## 2/'` go into the ledger and into Task 7's `BYTE_LOCK`.

- [ ] **Step 1: Count N by the design's rule.** Read the focused test at `e209ed9`. Count, on its passing path: 1 (parameters LINE — a `#[test]` fn has none, so this LINE has empty deltas and still counts) + every statement at any block depth that completes normally (a `let`, an expression statement, an `assert!`/`assert_eq!` macro statement — each one) + one per arm/loop-body entry that binds a pattern, per iteration. Do NOT count the tail expression, statements inside closures, or statements after a diverging one. Record the count and the list of (line → 1) that produced it in the record's §1 as a table, so H3's diff can name lines.
- [ ] **Step 2: Choose H4/H5 values.** From the same function, three bindings whose Debug text is an integer or bool (an event count, a `status.is_ok()`-style bool, a `len()`), each with the exact `--expr` (e.g. `events == 2`), the predicted verdict (MATCH/NO-MATCH at that line) and the line. Two `flow --value` literals (integers) with the binding name and line where the sighting must appear, and the assertion "no other sighting of that literal in this function". Write the derivation (which source lines) beside each.
- [ ] **Step 3: Write §1.** Design §7's table verbatim with the values filled; the lens paragraph (design §4.2 governs `dbg` reads; §3.1/§3.2 govern N; `SENSORIUM_TIER` default `call`; the audit log not silenced); both readings per row; the kill criteria (H2 compile failure = STOP; `.FAILED` rule). No box path except in the lens rows (clone path, target dir, store dir).
- [ ] **Step 4: Commit ALONE** (`docs(rung4): E9 pre-registered — §1 alone, before the instrument`), then print and ledger `git rev-parse --short HEAD` and `awk '/^## 1/,/^## 2/' docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md | sha256sum`.

---

### Task 1: Runtime — wire kind LINE and the `line` entry point (`sensorium-rt` 0.4.0)

**Files:**
- Modify: `rust/sensorium-rt/src/spool.rs` (the record grammar doc comment at the top; the kind constants beside `KIND_HANDLED`), `rust/sensorium-rt/src/lib.rs` (`pub mod line;` + re-export), `rust/sensorium-rt/Cargo.toml` (0.4.0)
- Create: `rust/sensorium-rt/src/line.rs`
- Test: unit tests inside `line.rs` (`#[cfg(test)]`), following `exit.rs`'s payload tests

**Interfaces:**
- Consumes: `spool`'s record writer used by `exit.rs` (`RECORD_FIXED = 24`, kind written last with `Release`), `probe::{Capture, CAP}` and `spool::cap_utf8`, `thread::try_enter_runtime`/`RuntimeScope`, `STATE`/`STATE_CALL`.
- Produces: `pub const KIND_LINE: u8 = 6;` and
  `pub fn line(unit: &'static Unit, site: u32, deltas: &[(&str, Capture)])` — inert when `STATE != STATE_CALL` or inside `RuntimeScope`; otherwise writes ONE record of kind 6 whose payload is:
  ```
  u8  flags        bit0 = deltas dropped
  u16 n            deltas present (little-endian, as every u16 in the record)
  n × { u16 name_len, name UTF-8,
        u8 tag (0 no value | 1 debug text | 2 unread), u8 truncated,
        [u16 text_len, text UTF-8]   -- present iff tag == 1 }
  ```
  `pub fn probe_cap<T>(v: &T) -> Capture` — the existing `Probe`/`DebugCap` autoref ladder applied to ONE borrowed value (Debug text capped at `CAP`, else unread); a thin re-export, never a second ladder. Task 2's probe fragments call it.
  `pub(crate) fn write_line_payload(buf: &mut [u8; LINE_PAYLOAD_MAX], deltas: &[(&str, Capture)]) -> (u16 /*len*/, bool /*dropped*/)` — writes deltas in order, each text capped by `cap_utf8(.., CAP)`; when the next delta would exceed `LINE_PAYLOAD_MAX` (= the record's `u16` payload capacity used for RETURN, same constant family), it and every later one are dropped and `flags.bit0` is set. Names are never truncated: a name longer than the remaining space drops that delta whole.

- [ ] **Step 1: Failing tests** in `line.rs`: (z) `probe_cap(&5u8)` is `Debug` text `5`, `probe_cap(&NoDebug)` is unread; (a) two deltas `("x", debug "5"), ("buf", unread)` encode to the exact byte vector spelled out in the test (flags 0, n 2, `01 00 78` … — write the bytes); (b) a 300-byte Debug text is capped at 200 with `truncated = 1`; (c) forty 190-byte deltas set `flags.bit0` and `n` equals the number written; (d) `line` under `SENSORIUM_TIER=off` (set `STATE` directly in the test) writes nothing to the spool.
- [ ] **Step 2: Run** `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target cargo test -p sensorium-rt line::` — FAIL (module missing).
- [ ] **Step 3: Implement** `line.rs` per the interface; add `KIND_LINE` and the grammar comment; bump to 0.4.0; `cargo test -p sensorium-rt` green; mutation: flip `bit0` never set → test (c) red; restore.
- [ ] **Step 4: Commit** `feat(rt): wire kind LINE (6) and the line() entry point — one record per completed statement, deltas capped per field, a dropped delta stated (0.4.0)`.

---

### Task 2: Transform — focus matching and the statement walk (`sensorium-transform` 0.4.0)

**Files:**
- Create: `rust/sensorium-transform/src/focus.rs`, `rust/sensorium-transform/src/lines.rs`
- Modify: `rust/sensorium-transform/src/lib.rs` (`SiteKind::Line`; `transform`/`transform_file` gain `focus: &Focus`; `pub mod focus; mod lines;`), `rust/sensorium-transform/src/visit.rs` (`fn_item`: after `classify`, `let focused = focus.matches(&qualname)`; when focused, the body walk calls `lines::walk_body`), `rust/sensorium-transform/src/manifest.rs` (serialize `Line` sites with `line`), `rust/sensorium-transform/src/bin/*` (thread the focus from `SENSORIUM_FOCUS` if the binary is the wrapper's entry — check `rust/cargo-sensorium/src/wrapper.rs` first: the wrapper calls `transform_file` directly; then only the library signature changes here and Task 3 passes the value), `rust/sensorium-transform/Cargo.toml` (0.4.0)
- Test: the crate's existing test layout (`cargo test -p sensorium-transform`); golden-output tests over inline fixture sources

**Interfaces:**
- Consumes: `Ctx { scope, next_site, emit, .. }`, `Ctx::qualname`/`scope_path`, `Site { site, file, qualname, line, .. }`, `Kind`/`Splice`/`Ctx::push` (point splices at byte offsets), `arms::bound_names(pat, &mut Vec<String>)`, `MAX_SITE_INDEX`.
- Produces:
  - `pub struct Focus(Vec<String>)`; `Focus::parse(csv: &str) -> Focus` (split on `,`, trim, drop empties, de-dup, keep order); `Focus::is_empty()`; `Focus::matches(&self, qualname: &str) -> bool` = any value `v` with `qualname == v || qualname.starts_with(&format!("{v}::"))`; `pub fn focus_hash(&self) -> String` = first 16 hex of sha256 over the SORTED de-duplicated values joined by `\n`, `"0"` when empty.
  - `SiteKind::Line` (manifest: `kind: "line"`, `line` = the statement's first line, `qualname` = the enclosing fn's).
  - The unit manifest gains a top-level `focus: {"values": [..given order..], "matched": [..sorted qualnames of this unit's focused fns..]}` when the focus is non-empty, absent otherwise (`manifest.rs`); Task 4 reads it — the manifest is per unit and needs no env to survive.
  - `lines::walk_body(ctx: &mut Ctx, sig: &Signature, block: &Block, fn_qualname: &str)` which splices, in source order:
    1. the **parameters LINE** right after the body's opening `{`: `::sensorium_rt::line(&crate::__SENSORIUM_UNIT, <site>, &[("a", ::sensorium_rt::probe_cap(&a)), ...]);` — one entry per parameter identifier (patterns destructured via `bound_names`; `self` included when present; empty slice when there are none);
    2. after every `Stmt` at every block depth (walking `if`/`else`, `loop`/`while`/`for` bodies, `match` arm blocks, plain and `unsafe` blocks; NOT closures, NOT `async` blocks, NOT macro bodies): a probe whose deltas are the names the statement wrote — `Stmt::Local` → `bound_names(&local.pat)` (skip when the `let` has no initializer); `Stmt::Expr(Expr::Assign | Expr::AssignOp)` with a bare `Expr::Path` of one segment on the left → that identifier; everything else → an empty slice;
    3. for an arm or loop body that binds a pattern (`match` arm, `if let`, `while let`, `for`): a probe as the FIRST statement of that body with the pattern's `bound_names`, site line = the arm's/loop's line.
    A probe is a point splice INSERTED AFTER the statement's last byte (after `;` or the closing `}`), never wrapping the statement; the statement itself is not re-rendered. The probe's capture expression is `::sensorium_rt::probe_cap(&name)` — add that thin helper in Task 1's `line.rs` if `probe.rs` does not already export a one-argument `(&T) -> Capture` (check `Probe`/`DebugCap` first and REUSE the ladder; do not write a second Debug ladder).
  - `transform(source, file, unit_metadata, …, focus: &Focus)` and `transform_file(…, focus: &Focus)` — an empty focus must produce output BYTE-IDENTICAL to today's (test it against a fixture whose expected output was captured before this task).

- [ ] **Step 1: Failing tests** (golden strings; write the expected rewritten source in the test): (a) `Focus::matches`: `Counter` matches `Counter::new`, not `Counters::new`; `tests` matches `tests::a::b`; exact match; empty focus matches nothing; (b) a focused `fn fill() { let a = 1; let b = a + 1; println!("{b}"); }` yields three probes + the params LINE with the exact fragments; (c) `for i in 0..3 { total += i; }` yields the loop-body entry probe with `i` and a statement probe with `total`; (d) `match o { Some(n) => { let d = n * 2; } None => {} }` yields the arm-entry probe with `n` and the `let` probe with `d`, none for the empty arm; (e) a closure inside a focused fn gets NO probes; (f) an `async fn` named in the focus is skipped with the existing reason and gets none; (g) empty focus → output byte-identical to the pre-task golden; (h) `focus_hash` of `["b","a","a"]` equals that of `["a","b"]` and differs from `["a"]`; empty → `"0"`; (i) manifest JSON of a focused fn lists the `line` sites with the right lines.
- [ ] **Step 2: Run** `cargo test -p sensorium-transform` — FAIL.
- [ ] **Step 3: Implement**; keep `visit.rs` ≤ 800 (it is the reason `lines.rs` is a separate module); bump 0.4.0; green; mutations: boundary rule `"::"` → `":"` (a red), drop the arm-entry probe (d red), probe closures (e red).
- [ ] **Step 4: Commit** `feat(transform): compile-time focus — one LINE probe per completed statement of a focused fn, deltas = the bindings it wrote (0.4.0)`.

---

### Task 3: Driver — `--focus`, resolution before building, `SENSORIUM_FOCUS`, the focus hash in the mirror stamp (`cargo-sensorium` 0.4.0, part 1)

**Files:**
- Modify: `rust/cargo-sensorium/src/driver.rs` (`parse_args` → `DriverArgs.focus: Vec<String>`; refusal; `.env("SENSORIUM_FOCUS", csv)`), `rust/cargo-sensorium/src/wrapper.rs` (read `SENSORIUM_FOCUS`, `Focus::parse`, pass to `transform_file`), `rust/cargo-sensorium/src/mirror.rs:200` (`write_rewrite(.., tool_hash, focus_hash, r)`: `key = format!("{tool_hash}:{focus_hash}:{}", r.source_hash)`), `rust/cargo-sensorium/Cargo.toml` (0.4.0)
- Create: `rust/cargo-sensorium/src/resolve.rs`
- Test: unit tests in `resolve.rs` over a fixture workspace written to a temp dir; `parse_args` tests beside the existing `--tier` ones

**Interfaces:**
- Consumes: `sensorium_transform::{Focus, transform}` in census mode (`emit: false` — classification without splicing — see `Ctx.emit`) to enumerate eligible fn qualnames per file; `modtree.rs` for the workspace's file list.
- Produces: `pub struct Resolution { pub matched: Vec<String> /*sorted qualnames*/, pub unmatched: Vec<(String /*value*/, Vec<String> /*closest ≤3*/)>, pub skipped_only: Vec<(String, String /*reason*/)> }` and `pub fn resolve_focus(ws_root: &Path, focus: &Focus) -> Result<Resolution, String>`. Driver behaviour: with a non-empty focus, resolve first; any `unmatched` or `skipped_only` entry → print
  `REFUSED: --focus <value> matches no function in the workspace; nothing was built. Closest: <a>, <b>, <c>` (or `… matches only <qualname>, which the transform skips (<reason>); nothing was built.`) and exit 2 BEFORE cargo runs. "Closest" = the ≤3 eligible qualnames sharing the longest common suffix on `::` segments, then lexicographic. Otherwise set `SENSORIUM_FOCUS` (values comma-joined, given order) on the cargo child; the converter learns what matched from the unit manifests (Task 2), not from env.
- `--focus` parsing: repeatable `--focus <v>` and `--focus=<v>`, only before the first bare `--`, like `--tier`; `--focus` with an empty value → `BAD_CALL` 2 with `--focus needs a qualname`.

- [ ] **Step 1: Failing tests**: (a) `parse_args(["--focus","a::b","--focus=c","test","--","--focus","x"])` → focus `["a::b","c"]`, cargo args untouched after `--`; (b) `resolve_focus` over a temp workspace with `mod m { pub fn f() {} pub async fn g() {} } fn h() {}`: focus `m` → matched `["m::f"]`; focus `m::g` → `skipped_only [("m::g","async")]`; focus `zz` → unmatched with closest from the eligible set; (c) the mirror key contains the focus hash (a unit test on the key format, or the stamp file contents after `write_rewrite`).
- [ ] **Step 2: Run** `cargo test -p cargo-sensorium` — FAIL.
- [ ] **Step 3: Implement**; bump 0.4.0; green; mutations: boundary in the resolver (uses `Focus::matches`, so mutate the call), the `--` stop.
- [ ] **Step 4: Build the driver** (`cargo build -p cargo-sensorium` under the workspace target) and run, by hand, on `corpus/rust/silent_swallow` with `--focus no_such_fn run` (`CARGO_TARGET_DIR` a scratch under `/mnt/extra`): the sentence, exit 2, and `ls` shows no mirror written. Paste the output in the report.
- [ ] **Step 5: Commit** `feat(driver): --focus resolved before building — an unmatched value refuses with exit 2; SENSORIUM_FOCUS reaches the transform; the focus hash joins the mirror stamp (0.4.0)`.

---

### Task 4: Converter — LINE rows, `focus` meta, conditional capabilities (`cargo-sensorium` 0.4.0, part 2)

**Files:**
- Create: `rust/cargo-sensorium/src/convert/spool/line.rs` (`parse_line_payload`)
- Modify: `rust/cargo-sensorium/src/convert/spool/mod.rs` (`KIND_LINE = 6` mirror constant; `pub mod line`), `rust/cargo-sensorium/src/convert/frames.rs` (the `KIND_LINE` arm beside `KIND_RETURN`), `rust/cargo-sensorium/src/convert/manifest.rs` (`SiteKind::Line` deserialization; the per-unit `focus: {values, matched}` record Task 2 emits — the ONLY source: `meta.focus` = the `values` of any unit carrying the record (all units of one run carry the same list), `focus_matched` = the sorted union of the units' `matched`), `rust/cargo-sensorium/src/convert/meta.rs` (`build`: `focus` list and `focus_matched` when non-empty; capabilities: `line` and `locals` `true` iff any unit's manifest has ≥1 `line` site — computed from the manifests, never from the flag alone)
- Test: converter tests with a hand-built spool record (bytes from Task 1's test (a)) → the `events` row and payload JSON; meta tests for the three cases (no focus; focus with matched sites; focus given but zero `line` sites → `false`)

**Interfaces:**
- Consumes: Task 1's payload grammar; `parse_return_payload(label, payload, ..)`'s error style (a malformed payload is a conversion refusal naming the record, never a guessed row); `writer.insert_event(...)` as the RETURN arm calls it; `stacks[thread].last()` for the current frame.
- Produces: `pub fn parse_line_payload(label: &str, payload: &[u8]) -> Result<LinePayload, String>` with `pub struct LinePayload { pub dropped: bool, pub deltas: Vec<(String, Value /*the capture dict*/)> }` where the capture dict is exactly the RETURN value's shape: `{"k":"dbg","v":<text>,"trunc":<bool>}` for tag 1, `{"k":"unread"}` for tag 2, and tag 0 never occurs for a delta (a refusal if seen). The `events` row: kind `"LINE"`, `frame_id` = current frame, `code_id` = the fn's, `line` = the site's line, payload `{"deltas": {name: capture, ...}}` plus `"unread": ["locals"]` iff `dropped`. Meta: `focus: [..]`, `focus_matched: [..]`; `capabilities.line`/`locals` per the rule above.

- [ ] **Step 1: Failing tests** for the parser (round-trip of Task 1's bytes; a truncated buffer → `Err` naming the label), the row (a spool with CALL, LINE, RETURN → three rows; the LINE row's `frame_id` equals the CALL's frame; payload JSON exact), and meta (three cases).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement**; green; mutation: `dropped` ignored → the `unread` test red; capabilities computed from the flag instead of the sites → the zero-sites case red.
- [ ] **Step 4: Commit** `feat(convert): LINE rows from wire kind 6, focus and focus_matched in meta, line/locals true only where a LINE site exists`.

---

### Task 5: Query side — the `::` boundary and `dbg` captures (Python)

**Files:**
- Modify: `src/sensorium/query/watch_cmd.py:102-104` (`_qual_matches`), `src/sensorium/query/expr.py:160` (`resolve`), `src/sensorium/query/flow_cmd.py:236` (`matches`) and `:209` (`parse_literal`, only if `None` needs a Rust rendering), `corpus/rust/stale_cache/questions.yaml` (the refusal's version string 0.3.0 → 0.4.0 — a by-rule pin move, named in the commit)
- Test: `tests/test_watch_rust_dbg.py` (new; keep `tests/test_watch*.py`/`test_flow*.py` ≤ 800) using `tests/rust_traces.py`'s fixtures extended with LINE rows carrying `dbg` deltas

**Interfaces:**
- Produces:
  - `_qual_matches(qualname, spec)` = `qualname == spec or qualname.startswith(spec + ".") or qualname.startswith(spec + "::")`; the same helper is what `flow` uses for `--at`/qualname specs (grep for a second copy and unify, do not duplicate).
  - `resolve({"k":"dbg","v":t,"trunc":tr})`: `TRUNCATED` if `tr`; else `int(t)` when `t` matches `^-?\d+$`; `float(t)` when it parses as a float literal; `True`/`False` for `true`/`false`; the unquoted string when `t` is `"…"` with matching quotes (Rust Debug escapes → `codecs.decode(.., "unicode_escape")` on the inner text); otherwise `t` itself (a string). `len(name)` over a `dbg` value → the existing unevaluable-size marker (same path as an unread container length): the site is reported UNSETTLED, never compared.
  - `matches(cap, target)` for `k == "dbg"`: `False` when `trunc`; else `cap["v"] == debug_text(target)` where `debug_text(int|float)` = `repr` in Rust's decimal spelling (`5`, `2.5` — note Python's `repr(2.0)` is `2.0` and Rust's Debug of `2.0f64` is also `2.0`), bools `true`/`false`, `str` → `'"' + s + '"'` with `"`/`\` escaped, `None` → `None`.

- [ ] **Step 1: Failing tests**: (a) `_qual_matches("Counter::new","Counter")` True, `("Counters::new","Counter")` False, `("Pot.add","Pot")` still True; (b) `resolve` on the six `dbg` shapes (int, negative int, float, bool, quoted string with an escaped quote, arbitrary text) and the truncated case; (c) `matches` on `5`, `2.5`, `true`, `"A1"`, `None`, and a truncated `"A1"` → False; (d) an end-to-end `watch --at fill --expr b == 2` over a fixture Rust trace with LINE rows → MATCH at the pinned line, exit 0; `flow --value 2` → the sighting line; (e) `--expr len(s) > 1` over a `dbg` string → UNSETTLED wording for that site.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement**; green; mutations: drop the `"::"` clause (a red), compare `dbg` text to `str(target)` (c's `"A1"` case red), forget `trunc` (b/c red).
- [ ] **Step 4: Commit** `feat(query): watch/flow read Rust — a :: prefix boundary and a defined reading of dbg captures`.

---

### Task 6: Corpus — six focus cases

**Files:**
- Create: `corpus/rust/focus_let_chain/`, `focus_loop_counter/`, `focus_match_binding/`, `focus_moved_value/`, `focus_non_debug/`, `focus_unfocused_refuses/` — each `Cargo.toml` (no deps, no lock), `src/main.rs`, `questions.yaml` with `program: cargo`, `cargo_args: ["--focus", "<q>", "run"]` (the last one: `["run"]`)
- Modify: `corpus/rust/README.md` (the case list)
- Test: `tests/test_corpus.py` (the existing gate; run it with `SENSORIUM_CARGO_SENSORIUM=/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium`, `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/corpus-target`), plus one gate test for the driver's refusal: `tests/test_focus_refusal.py` invoking the driver on `corpus/rust/focus_let_chain` with `--focus no_such_fn run` → the exact sentence and exit 2 (skipped by name when no driver is on the box, exactly as `run_corpus.py` skips)

**Interfaces:** consumes Tasks 1–5 built into one driver (`cargo build -p cargo-sensorium` first; record its sha256 in the report).

Programs and pins (each `questions.yaml` pins byte-exact answers you obtain by RUNNING the tool once the program is written — the pin is what the tool prints, checked against the design's rules by reading, not the other way round; cite the rule per question in `why_logs_fail`/`truth`):

| case | `src/main.rs` shape | questions (ask → `expect_*`) |
|---|---|---|
| `focus_let_chain` | `fn fill() -> String { let a = 1; let b = a + 1; let s = format!("{b}"); s }` called from `main`; focus `fill` | `watch $RUN --at fill --expr b == 2` → MATCH at the `let b` line, exit 0; `frame`/`tree` show LINE rows count 4 (params + 3); `info` shows `focus: ["fill"]`, `capabilities.line: true` |
| `focus_loop_counter` | `fn sum() -> i32 { let mut total = 0; for i in 0..3 { total += i; } total }`; focus `sum` | `flow $RUN --value 3` → one sighting of `total` at the `total += i` line (third iteration); `watch --at sum --expr i == 2` MATCH; LINE count = 1 + 1 + 3×(1 entry + 1 stmt) |
| `focus_match_binding` | `fn pick(o: Option<i32>) -> i32 { match o { Some(n) => { let d = n * 2; d } None => 0 } }` + an `if let`; focus `pick` | `watch --at pick --expr n == 21` MATCH at the arm line; `--expr d == 42` MATCH; params LINE carries `o` as `dbg` `Some(21)` |
| `focus_moved_value` | `fn go() -> usize { let v = vec![1, 2]; let w = v; let n = w.len(); n }`; focus `go` | the build SUCCEEDS (the case exists to compile); `watch --at go --expr n == 2` MATCH; `flow --value 2` finds `n`, and the LINE rows for `v` and `w` carry `dbg` text `[1, 2]` |
| `focus_non_debug` | `struct Opaque(u8); fn make() -> u8 { let h = Opaque(7); h.0 }`; focus `make` | `frame $RUN --at make` (or the command that prints a LINE's deltas) shows `h: <unread>`; `watch --at make --expr h == 7` → UNSETTLED for that site (not-captured), exit 3 |
| `focus_unfocused_refuses` | the `stale_cache` program shape, `cargo_args: ["run"]` | `watch $RUN --at price_of --expr key == "A1"` → `REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 declares it does not produce (capabilities.line: false); nothing was checked`, exit 3; `info` shows no `focus` key |

- [ ] **Step 1: Write the six programs and empty `questions.yaml` skeletons**; run the corpus gate — the new cases FAIL on missing expectations.
- [ ] **Step 2: Run each program once under the built driver**, read the outputs against design §3.2/§4.2, and pin them; where a printed line contradicts the design, STOP and report (do not pin a wrong output).
- [ ] **Step 3: Gate**: `tests/test_corpus.py` all cases equal (existing ones unchanged — `stale_cache` only in the version string, Task 5); `tests/test_focus_refusal.py` green; mutation: change one pinned exit → red.
- [ ] **Step 4: Commit** `test(corpus): six focus cases — let chain, loop counter, match binding, moved value, non-Debug, unfocused refusal`.

---

### Task 7: E9 runner (instrument), locked to Task 0's §1

**Files:**
- Create: `rust/tests/acceptance_e9.py` (config, preflight, lock check, phases H1–H7, markers, `main`, `--assemble`, `--render`), splitting into `acceptance_e9_phases.py` / `acceptance_e9_schema.py` / `render_e9.py` if any file nears 800; reuse `acceptance_lib.py` (`Refused`, `step`, `plain_env`, markers) and `acceptance_rung3.byte_lock_check`
- Test: `tests/test_acceptance_e9.py` (box-free: lock facts with `BYTE_LOCK`, schema completeness, none-vs-zero, the killed-answer rule from the grain repair — an arm that timed out publishes nulls with a reason, the box-path scan over the instrument modules)

**Interfaces:**
- Consumes: env vars only — `SENSORIUM_DRIVER` (the built `cargo-sensorium`), `SENSORIUM_BLOOMERY` (the clone), `SENSORIUM_E9_TARGET` (FRESH `CARGO_TARGET_DIR`), `SENSORIUM_DIR` (FRESH), `SENSORIUM_RUST_TARGET` (for H7's `cargo test --workspace`); refuses when any is missing or the fresh ones are not empty.
- Produces: `BYTE_LOCK = "<Task 0's sha>"`; phases returning dicts with `{value, n, lens, dropped}` cells; the raw record `results-e9-raw.json` in the ledger; `docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.results.json` derived by `--assemble` (deterministic; `acceptance` from the raw record's `byte_lock.doc`, as the grain repair fixed); `section-2-3.md` by `--render`; markers `e9.DONE`/`e9.FAILED` carrying `exit=<n>`.
- Phase contracts (each runs the driver via `subprocess` with `plain_env()` + the needed `SENSORIUM_*`): H1 unfocused run of `-p bloomery-daemon --test pager_obligation_test` → `info` JSON's `capabilities.line`, `count(*) from events where kind='LINE'`, `watch` stdout+exit; H2 focused run with the two `--focus` values → the driver's resolution lines, cargo's test summary line for both runs (equal?), a compile failure → `.FAILED` after the H1 numbers (a STOP); H3 `count(*)` of LINE rows joined to the focused test's frame → compared to §1's N, with the per-line histogram for the diff; H4/H5 the pinned commands → verdict/lines vs §1; H6 wall times (`time.perf_counter` around each run; the focused rebuild's wall separately); H7 corpus gate + Python suite + `cargo test --workspace` result lines. Both readings per §1; a timed-out phase publishes nulls with the reason.

- [ ] **Step 1: Failing box-free tests**; **Step 2: implement**; `tests/test_acceptance_e9.py` green; mutation on the lock check and on the killed-answer rule; `wc -l` of every instrument file.
- [ ] **Step 3: Dry run in `--assemble`/`--render` mode over a hand-written raw record** (no driver): the schema is complete and the render matches the record's §2–§3 headings.
- [ ] **Step 4: Commit** `test(rung4): E9 runner — the focus tier measured against the bloomery clone, locked to <sha>`.

---

### Task 8: Measure E9 once; §2–§5 of the record

Exactly Task 5/Task 8 discipline of the entry slice: `pgrep -a cargo` empty; build the driver from HEAD (`cargo build -p cargo-sensorium`), record its sha256; write the launcher under `<ledger>/acceptance-e9/launch.sh` (pid file, the env vars, `exec` the runner); `setsid nohup bash launch.sh > logs/e9.log 2>&1 &`; poll `ps -p` + markers in a bounded loop (the focused rebuild of `bloomery-daemon`'s test target will take minutes — bound 60 min); read nothing before `e9.DONE`/`e9.FAILED`. `.FAILED` before H1's numbers = infrastructure (archive `failed-launch-<n>/`, empty BOTH fresh locations, relaunch from zero); after = STOP, no relaunch. Then re-run `--assemble` once and prove determinism; write §2 Environment, §3 numbers per H, §4 verdicts (both readings where the number selects one; a STOP written as a STOP), §5 findings; every prose number names its field; §1 sha unchanged before/after (report it). Commit the record + `.results.json` by explicit path.

---

### Task 9: Docs, HONESTY, versions, close-out

**Files:** `rust/HONESTY.md` (§9 "once per captured return **and once per captured delta**"; the new promise bullet per design §3.6 — if the file would pass 800, move a section to a sibling first, as HONESTY-OUTCOMES was), `rust/HONESTY-BLIND-SPOTS.md` (item 3 narrowed per design §3.3; the new declaring facts), `rust/HONESTY-INDEX.md` (the row), `docs/TRACE-FORMAT.md` (ONLY: the `line`/`locals` capability prose gains "for `lang = rust`, true only under a `--focus`"; the `LINE` row gains "for `lang = rust`, `deltas` are the bindings the statement wrote (design 2026-09-06 §3.2)"), `rust/README.md` (`--focus`, the "Not yet" list loses LINE/locals, keeps `refocus`/`--window`), `README.md` (`watch`/`flow` on Rust: one paragraph + the `dbg` reading rule), `CHANGELOG.md` (`## 0.8.3 — <date>` Python + a crates block 0.4.0, with E9's numbers in the record's words and its verdicts as recorded — a STOP stated as a STOP), `pyproject.toml` (0.8.3), `docs/CARRIED-DEBT.md` (new section: settled / deferred — `--window`, closure/async bodies, place writes, CALL args for Rust, volume cap, whatever §5 found — / process lessons), `docs/superpowers/specs/2026-09-02-sensorium-rung3-inbox.md` (rung-4 items: LINE/locals struck, refocus remains for slice 2).

- [ ] Grep `0\.3\.1`, `0\.3\.0`, `0\.8\.2` and account for every hit (Cargo.lock entries move with the crates; records and plans are history).
- [ ] Full gate: Python suite; corpus with the built driver; `cargo test --workspace`; `git status` clean; `wc -l` of every touched file; no box path in anything committed.
- [ ] PR body draft in the ledger (`pr-body.md`): summary, what changed, E9 as measured (verdicts as recorded), rulings for Brice if any, test plan, the two closing lines.
- [ ] Commits by explicit path: docs; version; CARRIED-DEBT + inbox.

### After Task 9 — final review, fix wave, PR

Whole-branch review (fable) on `9db30d0..HEAD` with the design, the record and the ledger's rulings; the classification rule: a `src/`, `rust/sensorium-*` or `cargo-sensorium` change after the measurement that can alter a recorded or printed line invalidates E9 → CARRIED-DEBT, not a fix; ONE fix wave (docs/tests/instrument only, with re-assembly proofs); scoped re-review; push; PR against `main` (merge main in first if PR #17 landed); CI green; merge is Brice's.

## Self-review

- **Spec coverage**: design §2.1–§2.4 → Tasks 2 (matching), 3 (flag, resolution, env, stamp), 4 (manifest, meta, capabilities); §3.1–§3.5 → Tasks 1, 2, 4; §3.6 → Task 9; §4.1–§4.3 → Task 5; §5 → Tasks 1–4 (crate bumps) + 9; §6 → Task 6; §7 → Tasks 0, 7, 8; §8 honoured by omission; §9 risks → H2's STOP rule, H6, TRACE-FORMAT prose.
- **Placeholders**: none — every expected string, byte layout, refusal sentence and test list is written; values Task 0 derives (N, triples) are named as its outputs.
- **Type consistency**: `Focus`/`Focus::matches`/`focus_hash` (Task 2) are what Task 3's resolver and mirror use; `KIND_LINE = 6` and the payload grammar (Task 1) are what Task 4's `parse_line_payload` mirrors; `LinePayload.deltas` values are the `{"k":"dbg"|"unread"}` dicts Task 5's `resolve`/`matches` read; `_qual_matches` is one helper; `BYTE_LOCK` (Task 7) is Task 0's sha.
