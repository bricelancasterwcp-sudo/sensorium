# Rung 4, slice 1 — the focus tier: LINE and locals for Rust under `--focus`

**Date:** 2026-09-06 · **Status:** design, approved section by section in
conversation (Brice, 2026-09-06) · **Design authority:** Claude · **Base:**
main `9db30d0` (Python 0.8.2; crates transform 0.3.1 / driver 0.3.1 /
rt 0.3.0) · **Branch:** `feat/rung4-focus-tier`

Rung 4 proper was split in two by ruling (2026-09-06, "two slices, focus
tier first"). This document is slice 1. Slice 2 — `refocus` for
`lang = rust` and the pre-registered E4 (`refocus` MATCH rate on the
`pager_*_test.rs` files, design 2026-09-01 §11 row E4) — gets its own design
after this slice merges. Neither touches `docs/TRACE-FORMAT.md`'s format
number: format 5 belongs to the S0 trace-contract slice (PR #17).

## 0. The three rulings this design rests on

| # | Question | Ruling (Brice, 2026-09-06) | Why |
|---|---|---|---|
| F1 | one slice or two? | **two: focus tier, then refocus + E4** | the hard invention (a LINE event for Rust) gets its own lock; E4's pre-registered row stays intact for slice 2 |
| F2 | where is a Rust focus decided? | **at compile time** | the transform instruments unconditionally today and only the coarse tier is a runtime switch; a per-statement probe must borrow what it captures, and a moved binding cannot be borrowed, so *where probes go* is a static decision — made per focus, it confines borrow risk to focused functions and leaves the unfocused workspace byte-identical |
| F3 | what does a LINE's `deltas` hold? | **the bindings the statement wrote** | captured by shared borrow right after the write, before any later move; Python computes the same set dynamically by diffing; re-capturing all live bindings would need a move analysis at every statement |

Approach chosen over two others (recorded for the reader who asks "why not"):
debugger-backed locals (lldb/rr on DWARF — a second tool the honesty ledger
does not cover, an order of magnitude slower, no path through cargo's spawned
test binaries) and snapshot-and-diff (rejected by F3).

## 1. What ships

1. `cargo sensorium --focus <qualname> … test|run` — repeatable; the driver
   resolves each value against the workspace sources before building and
   refuses a value that matches nothing (exit 2, nothing built).
2. In every matched function the transform splices **one LINE probe after
   every statement**, minting a site per statement; the probe captures the
   bindings that statement wrote through the existing Debug-or-unread ladder
   (200-byte cap, reentrancy guard) and emits a new wire kind, LINE (6).
3. `cargo-sensorium` converts LINE records to `events` rows of kind `LINE`
   in the Python payload shape (`deltas`, optional `unread`), records `focus`
   and `focus_matched` in meta, and declares `capabilities.line` and
   `capabilities.locals` **true only when some unit of the run carries at
   least one LINE site**. `refocus` stays `false`.
4. `watch` and `flow` work on a focused Rust trace: the qualname prefix
   match learns the `::` boundary, and `dbg` captures gain a defined meaning
   for `--expr` and `--value` (§5).
5. Six Rust corpus cases, a pre-registered acceptance record (E9) on the
   bloomery clone, HONESTY amendments, versions: rt / transform / driver
   0.4.0, Python 0.8.3, `TRACE_FORMAT` unchanged at 4.

## 2. The CLI and the pipeline (section 1, approved)

### 2.1 The flag

`cargo sensorium [--tier off|call] [--focus <qualname>]… test|run [cargo
args] [-- binary args]`. Parsed where `--tier` is parsed
(`rust/cargo-sensorium/src/driver.rs` `parse_args`): only before the first
bare `--`, so a test binary's own `--focus` is never stolen. Repeatable;
`--focus=<v>` accepted like `--tier=`.

**Spelling.** The value is the qualname the trace already prints for Rust —
the file-local `::` path the transform computes as `scope_path()`
(`rust/sensorium-transform/src/visit.rs` `qualname`/`scope_path`):
`Counter::new`, `nested::nested_marker`, `tests::describe_describes`. A value
naming a container (`Counter`, `tests`, `nested::inner`) selects every
eligible function under it; "under" means equal, or a prefix ending at a
`::` boundary. No `crate::` prefix, no crate name, no globs, no file paths.
Python's recorder keeps its own `pkg.module[:qualname]` spelling; the two
commands are different and each takes what its own `tree` prints
(designing-notation: familiar spelling, collision test passed — the same
flag name, but on a different command, taking that command's own names).

### 2.2 Resolution before building

Before invoking cargo, the driver walks the workspace's `.rs` files with the
transform's visitor in a resolve-only mode (no splicing) and collects every
eligible function qualname per file. Each `--focus` value is matched against
that set. A value matching nothing refuses:

```
REFUSED: --focus <value> matches no function in the workspace; nothing was
built. Closest: <up to 3 qualnames sharing the longest suffix>
```

exit 2 (`BAD_CALL`, the rung-3 exit-status convention), before any rewrite
or compile. Values that match are recorded (the matched qualnames, sorted)
for the manifest and the trace's meta. Functions the transform would skip
anyway (`const fn`, `extern`, `async fn`) are not eligible and do not count
as a match; a value matching only skipped functions refuses with the skip
reason named.

### 2.3 Plumbing

- Driver → wrapper: a new env var `SENSORIUM_FOCUS` (values comma-joined,
  in the order given; qualnames cannot contain a comma) set on the cargo
  child beside `SENSORIUM_TIER`. Absent or empty = no focus.
- Wrapper → transform: `transform_file(…, focus: &[String])`; the transform
  marks a function as focused in `fn_item` after `classify` (so skipped
  kinds are never focused) using the §2.1 boundary rule against its own
  `qualname`.
- Mirror freshness: the per-file stamp
  (`rust/cargo-sensorium/src/mirror.rs` `write_rewrite`) becomes
  `"{tool_hash}:{focus_hash}:{source_hash}"`, `focus_hash` = first 16 hex of
  sha256 over the sorted, de-duplicated focus list, `"0"` when empty. A new
  focus therefore re-rewrites and recompiles only files whose stamp changes;
  a file with no matched function keeps its bytes — the transform's output
  is a pure function of (source, focus), and the rewrite is skipped when the
  key matches. **The unfocused build is unchanged**: same key shape modulo
  the `:0:` component, same splices.
- Runtime: `sensorium-rt` learns the LINE kind and one entry point (§3.4).
  `SENSORIUM_TIER=off` gates LINE like everything else. The runtime learns
  nothing about focus.

### 2.4 What the artifacts say

- Manifest (`rust/cargo-sensorium/src/convert/manifest.rs`): sites gain a
  kind `Line` with `line` = the statement's first line and `qualname` = the
  enclosing function's; a per-unit `focus` record `{values: […], matched:
  […]}`.
- Meta (`rust/cargo-sensorium/src/convert/meta.rs` `build`): `focus` (the
  list, as Python's `boot.py` writes `focus`) and `focus_matched` (sorted
  qualnames); both absent when no focus was given. Capabilities: `line` and
  `locals` are `true` iff at least one LINE site exists in any unit's
  manifest for the run; otherwise `false` exactly as today. This is the
  runtime's own statement, not the converter's guess — the same discipline
  as `err_flow`.

## 3. The probe and the payload (section 2, approved)

### 3.1 Where a probe goes

Every `syn::Stmt` in a focused function's body, at every block depth: the
body block, `if`/`else` blocks, `loop`/`while`/`for` bodies, `match` arm
blocks, plain `{ … }` blocks, `unsafe` blocks. One probe per statement,
spliced after the statement's terminating `;` (or after the closing brace of
a block-like statement), as a point splice through the existing
`Splice`/`Kind` machinery (`rust/sensorium-transform/src/splice.rs`). Its
site: `SiteKind::Line`, `line` = the statement's first line (`Span::start`).

The probe runs only when the statement **completes normally**. A statement
that `return`s, `break`s, `continue`s, propagates with `?` or panics leaves
no LINE of its own; its exit is already the RETURN or RAISE row. The tail
expression is not a statement and its value stays the RETURN's.

### 3.2 What a probe captures — the deltas

| statement | deltas |
|---|---|
| `let PAT = expr;` | every identifier `PAT` binds (reuse `arms.rs` `bound_names`, a `visit_pat_ident` walk that handles nested destructuring); `_`-prefixed names included |
| `let x;` (deferred) | none here; `x` at its first assignment |
| `x = e;`, `x += e;` … (LHS a bare local identifier) | `x` |
| `*p = e;`, `a.b = e;`, `v[i] = e;` | none — a **place write**, declared |
| `match`/`if let`/`while let` arm with bindings, `for PAT in …` | the pattern's bindings, as a synthetic first LINE inside the arm/loop body at the arm's/loop's line, once per entry/iteration |
| parameters, `self` included | once, as the function's first LINE at the `fn` line, before the first statement |
| expression statement with no write (`foo();`, `println!(…);`) | empty `deltas` — the row still says the line ran |

Each value is taken by **shared borrow immediately after the write**
(`&name`), inside the probe call, through `Probe(&name).debug_cap()` —
`rust/sensorium-rt/src/probe.rs`'s autoref ladder: `Debug` → text capped at
`CAP = 200` bytes by `CapWriter`, `catch_unwind` around `fmt`; not `Debug` →
`unread`. The borrow is a temporary that ends inside the probe statement.
**Borrow safety holds by construction**: the capture precedes any later
statement, so no move has happened yet, and the probe touches only the
names the statement itself wrote, so no live `&mut` to another binding is
crossed (safe Rust forbids writing `x` while a `&mut x` is live anyway).
The reentrancy guard (`thread.rs` `RuntimeScope`, HONESTY §9) makes any
instrumented call a `Debug` impl performs inert; the impl still runs.

### 3.3 What stays outside (declared)

- **Closure bodies**: call-level instrumentation only (existing
  `SiteKind::Closure`); their statements get no probes.
- **`async fn` bodies**: not focused; `classify` already skips them for the
  entry guard's `Drop`-across-`.await` reason, and a probe's borrow inside an
  `async` block would face the same lifetime questions.
- **Macro invocations**: one statement, empty deltas; expansions are not
  inspected. Bodies produced by macros are never rewritten (as today).
- **Place writes and `&mut` mutation** (§3.2): not deltas.
- **`const fn` / `extern`**: never instrumented (as today).

`rust/HONESTY-BLIND-SPOTS.md` item 3 ("Locals, and per-line state — rung
4") is **narrowed, not deleted**: to unfocused functions, closure and async
bodies, place writes and `&mut` mutation, with the new declaring facts
(`capabilities.line: true` only under a focus; `focus_matched` in meta).

### 3.4 The wire

`rust/sensorium-rt/src/spool.rs`: `KIND_LINE = 6`, same 24-byte fixed
record (`seq, ts_ns, site, kind, outcome_or_how = 0, payload_len`), kind
written last as today. Payload grammar:

```
u8  flags        bit0 = deltas dropped (record would exceed payload_len)
u16 n            deltas present
n × { u16 name_len, name UTF-8,
      u8 tag (0 no value, 1 debug text, 2 unread), u8 truncated,
      [u16 text_len, text UTF-8]   -- only when tag = 1 }
```

The value block is `exit.rs`'s RETURN block, repeated. Text is capped per
field by `cap_utf8` (char-boundary safe). When the next delta would not fit,
it and all later deltas are dropped and `flags.bit0` is set — a partial
record is stated, never silently short. New runtime entry point
`line(unit, site, deltas: &[(&str, Capture)])`, inert under
`SENSORIUM_TIER=off` and inside `RuntimeScope`, exactly like `ret`.

### 3.5 The row

`rust/cargo-sensorium/src/convert/frames.rs`, a `KIND_LINE` arm beside
`KIND_RETURN`: decode with a new `spool::parse_line_payload` (mirrors the
writer byte for byte; a malformed payload is a conversion refusal naming
the record, never a guessed row), then

```json
{"deltas": {"x": {"k": "dbg", "v": "5", "trunc": false},
            "buf": {"k": "unread"}},
 "unread": ["locals"]}        // only when flags.bit0
```

inserted with `writer.insert_event(ts, thread, "LINE", frame_id, code_id,
line, payload, task_id)` on the thread's current frame (`stacks[thread]
.last()`); no push/pop, no fingerprint change. The capture dict is the one a
Rust RETURN value already uses (`fmt.py` knows `dbg`).

### 3.6 HONESTY

- `rust/HONESTY.md` §9: "A `Debug` that mutates or logs will do so once per
  captured return" → "… once per captured return **and once per captured
  delta**". The promise stays: reentrancy keeps it from emitting,
  `catch_unwind` keeps its panic from escaping.
- New promise bullet (in the file that keeps recorder promises; if
  `rust/HONESTY.md` would pass 800 lines, a further split precedes it):
  *Under a focus, one LINE per completed statement of a focused function,
  its `deltas` the bindings that statement wrote and nothing else; a
  dropped delta is stated by `unread: ["locals"]`.* Falsifier: a focused
  function's statement count on a straight-line path ≠ its LINE count (E9
  H3); a delta naming a binding the statement did not write.
- `rust/HONESTY-INDEX.md` (or wherever §-rows are indexed): the new row.

## 4. Query side (section 3, approved)

### 4.1 Qualname prefix on a `::` boundary

`src/sensorium/query/watch_cmd.py` `_qual_matches(qualname, spec)`:
`qualname == spec or qualname.startswith(spec + ".") or
qualname.startswith(spec + "::")`. Same helper wherever `flow` matches a
`--at`/qualname spec. Nothing else in `watch`/`flow` branches on `lang`;
they stay capability dispatchers.

### 4.2 `dbg` captures have a meaning

Today `expr.resolve` and `flow_cmd.matches` do not know `{"k": "dbg"}` — a
Rust return value already resolves to *not captured*. Rule: **a `dbg`
capture is Debug text.**

- `flow --value <literal>`: a sighting iff the capture is untruncated and
  its text equals the literal's **Debug rendering**: integers and floats
  their decimal text (`5`, `2.5`), bools `true`/`false`, strings the
  literal **with quotes** (`"A1"` matches a `String`/`&str` whose Debug is
  `"A1"`), `None` matches the text `None`. A truncated `dbg` never matches
  (same reason a clipped `str` never does).
- `watch --expr`: `resolve` maps a `dbg` capture to the literal its text
  parses as — an integer, a float, `true`/`false`, or a quoted string (the
  unquoted value) — else to the raw text as a string; `trunc` → TRUNCATED.
  `len(name)` over a `dbg` value is unevaluable at that site (the existing
  unread-size path; UNSETTLED for that site, never a comparison to nothing).
- `flow --object` on a Rust trace stays REFUSED via `object_identity:
  false`; `constructions()`'s receiver logic is untouched (Rust CALL rows
  carry no args).

### 4.3 Refusals unchanged

An unfocused Rust trace declares `line: false`; `watch`/`flow` print the
existing sentence (`REFUSED: <cmd> needs line, which recorder sensorium-rt
0.4.0 declares it does not produce (capabilities.line: false); nothing was
checked`, exit 3). `corpus/rust/stale_cache`'s pin changes only in the
version string.

## 5. Versions and format

| what | from | to |
|---|---|---|
| `sensorium-rt` | 0.3.0 | **0.4.0** (new wire kind) |
| `sensorium-transform` | 0.3.1 | **0.4.0** (focus, LINE splices, `SiteKind::Line`) |
| `cargo-sensorium` | 0.3.1 | **0.4.0** (`--focus`, resolution, LINE conversion, meta, capabilities) |
| Python `sensorium` | 0.8.2 | **0.8.3** (`::` prefix, `dbg` rules, docs) |
| `TRACE_FORMAT` | 4 | **4** — LINE rows and `focus` already exist; `focus_matched` is optional meta; format 5 is PR #17's |

`rust/HONESTY.md`'s pin table gains the row; `docs/TRACE-FORMAT.md`
`capabilities` prose for `line`/`locals` names the Rust condition ("true
under a focus"); the `LINE` payload paragraph gains one sentence: for
`lang = rust`, `deltas` are the bindings the statement wrote (see this
design §3.2).

## 6. Corpus — six new Rust cases

`corpus/rust/<case>/` with `cargo_args: ["--focus", "<q>", "run"]` (the
runner forwards argv verbatim; no runner change). Questions pin `watch`,
`flow --value`, `frame`/`tree` where relevant, byte-exact, both the answer
and the exit.

| case | program | pins |
|---|---|---|
| `focus_let_chain` | `fn fill() { let a = 1; let b = a + 1; let s = format!("{b}"); … }` | one LINE per statement; `watch --at fill --expr b == 2` MATCH at the `let b` line; params LINE first |
| `focus_loop_counter` | a `for i in 0..3 { total += i; }` | `i` as the loop-body's synthetic first LINE per iteration; `total` deltas per assignment; `flow --value 3` finds `total` |
| `focus_match_binding` | `match opt { Some(n) => { let d = n * 2; … } None => … }` | arm bindings as the arm's first LINE; `if let` variant |
| `focus_moved_value` | `let v = vec![1]; let w = v; let n = w.len();` | `v` captured at its `let` (before the move), `w` at its own; nothing captured for `v` after the move; the build succeeds — the borrow-by-construction case |
| `focus_non_debug` | a `let h = NoDebug::new();` | `{"k": "unread"}` for `h`; `frame` renders `<unread>`; `watch --expr h == 1` UNSETTLED |
| `focus_unfocused_refuses` | the `stale_cache` shape without `--focus` | `capabilities.line: false`; `watch` REFUSED exit 3 with the 0.4.0 sentence; `info` shows no `focus` key |

The driver's exit-2 refusal for a focus that matches nothing (§2.2) is not
a corpus question — a case records once, with one argv — so it is pinned by
a driver unit test (the resolver over a fixture workspace) and by a Python
gate test that invokes `cargo-sensorium` on a corpus crate with `--focus
no_such_fn` and asserts the sentence and exit 2 (skipped by name when no
driver is on the box, as the corpus gate does).

## 7. Acceptance — E9, pre-registered

Record: `docs/superpowers/acceptance/2026-09-06-sensorium-rung4-e9.md`, §1
committed **alone** and byte-locked (`awk '/^## 1/,/^## 2/' | sha256sum`)
before the runner exists in full; the runner follows the E6q/grain pattern
(`rust/tests/acceptance_e9.py`: env-var locations only, phases as
functions, `.DONE`/`.FAILED` markers carrying `exit=<n>`, kept stores as
inputs). Subject: the bloomery clone at `e209ed9`
(`/mnt/extra/sensorium-rung2/bloomery`, read-only; a fresh
`CARGO_TARGET_DIR` under `/mnt/extra/sensorium-rung2/`, a fresh
`SENSORIUM_DIR`). Two focus targets, chosen and written into §1 by reading
the source at `e209ed9`: `pager_obligation_test.rs`'s
`missing_stats_is_a_contract_violation_not_a_reply` (≈15 `let` bindings
across two scripted runs) and `pager_codec_gate_test.rs`'s
`pager_with_model` helper.

| id | question | endpoint (both readings pre-committed) |
|---|---|---|
| H1 | does an unfocused run stay unfocused? | `cargo sensorium test -p bloomery-daemon --test pager_obligation_test` (no `--focus`): meta `capabilities.line = false`, LINE rows = 0, `watch --at <target> --expr events == 0` (a real binding of the target, so the sentence is the capability refusal and not a parse error) → the REFUSED sentence, exit 3 |
| H2 | does a focus resolve and build? | each target resolves to exactly one qualname (driver output); the focused run's cargo test outcome (pass/fail counts) equals H1's; **a compile failure of a focused unit = STOP** |
| H3 | one LINE per completed statement? | for the focused test's single activation, LINE rows = N, where N is hand-counted from the source and written in §1 under §3.1/§3.2: one for the parameters LINE, one per completed statement at any depth on the passing path, one per arm or loop-body entry that binds a pattern (each iteration counted); readings: equal → PASS; ≠ → STOP with the diff of lines |
| H4 | does `watch` answer? | three `(qualname, --expr)` triples with predicted verdict and line, written in §1 from the source (integer/bool bindings only); all three as predicted → PASS |
| H5 | does `flow --value` see it? | two `(literal, name, line)` sightings predicted in §1; both found and no unpredicted sighting of that literal in the focused function → PASS |
| H6 | what does it cost? | focused vs unfocused wall time of the test file, and the focused rebuild's `cargo` wall; **reported, not gated** |
| H7 | did nothing else move? | corpus: every case equal (the six new ones included); Python suite green; `cargo test --workspace` green |

Lens sentence: `flow`/`watch` on Rust `dbg` captures are read under §4.2;
the statement count N uses §3.1's definition. Measured once; a `.FAILED`
before any number is infrastructure (relaunch from zero, archived); after a
number it is a STOP. The corpus is the printing gate; E9 is the recorder's
claim under a real workspace.

## 8. Not in this slice

`refocus` for Rust and E4 (slice 2); `--window` (needs a per-activation
runtime check the Rust runtime lacks); probes in closure and async bodies;
place writes and `&mut` mutation as deltas; CALL args for Rust; `flow
--object` for Rust; any change to Python's recorder; any `TRACE_FORMAT`
move. The acknowledgment marker N8 and Python grouping N7 stay where the
rung-4 entry slice left them (CARRIED-DEBT).

## 9. Risks named

- **A focused unit fails to compile** on a pattern §3.2 did not foresee
  (a `let` with a by-move sub-pattern whose remainder is used in the same
  statement; `let` inside a `const` block). E9 H2 measures it; the corpus
  case `focus_moved_value` pins the common one. A failure is a STOP and a
  finding, not a silent fallback to unfocused.
- **Volume**: a loop of 10⁶ iterations in a focused function writes 10⁶
  LINE records per statement. Accepted for slice 1 (the focus is the
  budget); H6 reports the cost; a per-site cap is slice-2 material if E9
  shows a need.
- **`dbg` text semantics** (§4.2) are weaker than Python's typed captures;
  stated in TRACE-FORMAT so a reader knows `x == 5` compared text.

## 10. Dated amendments

Each entry is added, never edited into the sections above; the sections read
with the amendment applied. E9's locked §1 (a4264b5) is not touched by any
of them — its gate value 26 is the value these amendments make unambiguous.

- **A1 (2026-09-06, R-F4) — bare-expression arm bodies.** §3.1/§3.2: a
  `match` / `if let` arm whose body is a bare expression (no block) is
  spliced as `{ <arm-entry probe>; <expr> }` — two point splices, the way
  exit wraps already surround an expression — so the arm-entry LINE exists
  for it too. The expression is the wrapper's tail, not a statement: no
  statement LINE for it.
- **A2 (2026-09-06) — zero parameters.** §3.2, parameters row: a function
  with no parameters still mints its parameters LINE, with empty `deltas`
  ("the row says the function was entered"), so every focused activation
  has a first LINE.
- **A3 (2026-09-06) — arms without bindings.** §3.2: an arm or loop pattern
  that binds no identifier (`_`, `Err(_)`, a literal pattern) mints NO
  arm-entry LINE. Only patterns with bindings do.
- **A4 (2026-09-06, R-F5) — verdict words and H4's bindings.** §7: verdict
  words in a record are the tool's own (`watch`: SATISFIED / not satisfied /
  NOTHING WAS CHECKED, exits 0/1/3), never "MATCH". H4 prefers integer/bool
  bindings; where the named subjects bind none (they do not — 17 and 7
  bindings, all paths, strings and opaque structs), the triples use §4.2's
  quoted-string branch and the unevaluable-`len` branch, as E9 §1 does; the
  integer branch is pinned by the corpus (`focus_let_chain`,
  `focus_loop_counter`).
- **A5 (2026-09-06, after Task 1) — the probe is lazy, and formats inside
  the runtime scope.** §3.2/§3.4: `line` takes the deltas as a closure,
  `::sensorium_rt::line(&UNIT, site, || [("x", probe_cap!(&x)), …])`,
  evaluated only when the runtime is recording (`STATE == STATE_CALL` and not
  inside `RuntimeScope`), exactly as `ret` takes its capture closure — so
  under `--tier off` no `Debug` impl runs for a delta. `probe_cap!` is a
  macro (the autoref ladder specialises at the call site's type; a generic
  fn cannot carry it) and formats inside `thread::enter_runtime()`, which is
  what keeps the §3.2 reentrancy promise true for LINE. `LINE_PAYLOAD_MAX`
  is 2048 bytes (room for eight capped deltas with names), not RETURN's 325;
  the drop rule beyond it stands.
- **A6 (2026-09-06) — a LINE needs an open frame.** §3.1/§3.5: the
  parameters LINE is spliced AFTER the entry guard, so a LINE always falls
  inside its function's CALL; a LINE record whose thread has no open frame
  is a malformed stream and the converter refuses it naming the record,
  never attaching it to a guessed frame.

