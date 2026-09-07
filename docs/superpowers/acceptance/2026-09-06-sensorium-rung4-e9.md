# Rung-4 acceptance, the focus tier — E9 (H1–H7)

The record of whether `cargo sensorium --focus` puts one LINE event on every
completed statement of a focused Rust function, carrying the bindings that
statement wrote and nothing else, on a workspace nobody wrote it for.

The binding design is
`docs/superpowers/specs/2026-09-06-sensorium-rung4-focus-tier-design.md`
(rulings F1–F3; §3.1/§3.2 define what a LINE is and what its `deltas` hold;
§4.2 defines how a `dbg` capture reads; §5 the versions; §7 this
pre-registration). Nothing here amends that design, and nothing here re-runs
or re-classifies an earlier record: the rung-3 borrow-repair acceptance
(`2026-09-05-sensorium-rung3-e6q.md`) and the rung-4 entry-grain records
(`2026-09-05-sensorium-rung4-entry-grain.md` and its repair) stand exactly as
written and no number in them is re-measured.

**§1 is byte-locked, and it is committed ALONE.** It is committed before the
transform can splice a LINE, before the runtime can write one, before the
driver can resolve a `--focus`, and before `rust/tests/acceptance_e9.py`
exists — so no value below was chosen after seeing an instrument behave. The
lock is `awk '/^## 1/,/^## 2/' | sha256sum`; the runner refuses to start
unless the range is byte-identical to the commit that locked it, and refuses
outright while no lock sha is set. §1 references no footnote, so the extended
lock range and the `awk` range are the same bytes. ~~§1 is not amended: there is one sha and no dated note inside it.~~ **Corrected
2026-09-06, before any measurement: §1 IS amended — one dated note in §1.4's
lens (the reader's `--limit 1000`), committed alone at `ffaed19`; the runner
carries both shas (original `a4264b5`, amended `ffaed19`) and no table row
moved.**

**The subject is a workspace this project did not write.** The bloomery clone
at `e209ed9` is read-only for the whole run; its HEAD and porcelain are
recorded before and after. Two focus values were chosen by reading that source
at `e209ed9`, and every number §1 pre-registers below — the statement count,
the three `watch` triples, the two `flow` sightings — was hand-derived from
that source, with the derivation written beside it, before any instrument
could produce a competing number.

**A completed measurement is never re-rolled, and a miss is a STOP with its
number.** Measured once.

## 1. Pre-registration

**The two focus values, as `--focus` spells them.** The value is the qualname
the transform computes (`rust/sensorium-transform/src/visit.rs` `qualname` /
`scope_path`): the file-local `::` path, which for an item whose scope stack
is empty is the bare item name (`qualname` returns `name.to_owned()` when
`self.scope.is_empty()`). Both functions sit at file top level — column 0, no
enclosing inline `mod`; the only `mod` in either file is the bodiless
declaration `mod common;` (`pager_obligation_test.rs:8`,
`pager_codec_gate_test.rs:9`), which pushes no scope over the items that
follow it. So both spell as bare names, with no `crate::` prefix, no crate
name, no file path:

| # | focus value | file at `e209ed9` | line | uniqueness |
|---|---|---|---|---|
| A | `missing_stats_is_a_contract_violation_not_a_reply` | `crates/bloomery-daemon/tests/pager_obligation_test.rs` | 250 | the only `fn` of that name in the workspace |
| B | `pager_with_model` | `crates/bloomery-daemon/tests/pager_codec_gate_test.rs` | 22 | the only `fn` of that name in the workspace |

A is a `#[test]` fn taking no parameters; B is a plain helper taking one
(`dir: &Path`) and called twenty times from its own file. Neither is `async`,
`const` or `extern`, and neither body is macro-produced, so both are eligible
under §3.3.

**Four runs, named here so every row can say which one it reads.** All four
are `cargo sensorium … test` on the clone, from the same target and into the
same store:

| run | command |
|---|---|
| U1 | `cargo sensorium test -p bloomery-daemon --test pager_obligation_test` |
| F1 | `cargo sensorium --focus missing_stats_is_a_contract_violation_not_a_reply test -p bloomery-daemon --test pager_obligation_test` |
| U2 | `cargo sensorium test -p bloomery-daemon --test pager_codec_gate_test` |
| F2 | `cargo sensorium --focus pager_with_model test -p bloomery-daemon --test pager_codec_gate_test` |

| Id | Question | Method | Endpoint (both readings pre-committed) | Derivation |
|---|---|---|---|---|
| H1 | does an unfocused run stay unfocused? | U1; then `info <run>`, a count of `LINE` rows over the whole trace, and `watch <run> --at missing_stats_is_a_contract_violation_not_a_reply --expr events == 0` (`events` is a real binding of the target — line 282 — so what comes back is the capability refusal and not a parse error). | meta `capabilities.line = false` **and** `capabilities.locals = false`; **LINE rows = 0**; `watch` prints `REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 declares it does not produce (capabilities.line: false); nothing was checked` and exits **3**. Second reading, on the one token that can move: the version in that sentence is `trace.recorder`, which §2 records from the trace itself; design §5 moves `sensorium-rt` 0.3.0 → 0.4.0, so the gate is the sentence with §2's recorded token substituted, and `0.4.0` is what it is expected to be. | Design §4.3, and `corpus/rust/stale_cache/questions.yaml`, which pins the same sentence at 0.3.0 today. |
| H2 | does a focus resolve and build? | The driver's own resolution output for F1's and F2's `--focus` value, read before cargo is invoked; then F1's cargo test outcome against U1's, and F2's against U2's. | Each value **resolves to exactly one qualname**; F1's pass/fail/ignored counts equal U1's and F2's equal U2's. Second reading of "resolved to that one": the set of distinct qualnames carrying LINE rows in F1's trace is exactly `{missing_stats_is_a_contract_violation_not_a_reply}` and in F2's exactly `{pager_with_model}`. Second reading of "equal outcome": the libtest summary counts, and beside them each run's process exit status. **A compile failure of a focused unit is a STOP** — no fallback to unfocused, no retry under a narrower focus. | Design §2.2 and §9's first risk. |
| H3 | one LINE per completed statement? | F1's trace: the LINE rows of the single activation of focus value A (the test runs once, in one frame). | **LINE rows = N = 26**, the hand count of §1.1, whose per-line table is here so a difference can name lines. Readings: **26 = PASS (the gate)**; **25** or **27** are the two alternatives §1.1 names, each a MISS of the gate that the record diagnoses as the §3.1/§3.2 under-specification named there — recorded with the diff of lines and obliging a §3.2 amendment and a corpus pin before merge, not read as a recorder defect. **Any other count is a STOP**, with the diff of lines. | §1.1, derived from the source at `e209ed9` under design §3.1/§3.2. |
| H4 | does `watch` answer? | The three triples of §1.2, each on the run named there. | **All three as predicted → PASS.** Each prediction is two pre-committed readings of one answer: the verdict class `watch` prints (`SATISFIED` / `not satisfied` / `NOTHING WAS CHECKED`) and the exit status it returns (0 / 1 / 3). A disagreement between the two is itself a finding about `Verdict`/`STATUS`, reported as such and not silently resolved in favour of either. | §1.2, derived from the source under design §4.2. |
| H5 | does `flow --value` see it? | The two sightings of §1.3, on F1. | **Both found, and no unpredicted sighting of that literal among focus value A's LINE deltas → PASS.** First reading (the gate): sightings restricted to A's LINE deltas. Second reading (reported, not gated): every sighting of that literal anywhere in the trace — the unfocused `common::pager` helpers are still instrumented at the call tier and their RETURN values carry the same texts. | §1.3, derived from the source under design §4.2. |
| H6 | what does it cost? | F1 against U1 and F2 against U2: the wall of the test binary, and the wall of the whole `cargo sensorium` invocation including the focused rebuild. | **Reported, not gated**, under both readings (libtest's own reported time, and the invocation wall). | Design §9's volume risk; the rung-2 addendum's plain/call lens. |
| H7 | did nothing else move? | This repository, not the clone: the corpus collector over every case (the six new Rust cases of design §6 included), the whole Python suite, and `cargo test --workspace`. | **Every corpus case equal**; Python suite green; Rust workspace green. Second reading: per-case equality of printed answers, and beside it each suite's exit status. | Parent §8 E6/E7, unchanged. |

### 1.1 N for H3 — the hand count, line by line

Counted from `crates/bloomery-daemon/tests/pager_obligation_test.rs` at
`e209ed9`, lines 249–303, under design §3.1 (one probe per statement at every
block depth, only where the statement completes normally; the tail expression
is not a statement) and §3.2 (the parameters LINE, and an arm's or loop
body's binding LINE once per entry).

| source line | what it is | + |
|---|---|---|
| 250 | `fn missing_stats_is_a_contract_violation_not_a_reply() {` — the parameters LINE. The fn takes none, so its `deltas` are empty; §3.2 still gives it a row. | 1 |
| 251 | `let dir = fresh_dir("bloomery-pager-contract");` | 1 |
| 252 | `let (mut p, jpath, _) = pager_in(&dir, 0, Some(10u64.pow(9)));` — one statement; `deltas` `p`, `jpath` (the bare `_` binds no identifier) | 1 |
| 253 | `let gguf = write_gguf(&dir, "fake.gguf", b"weights");` | 1 |
| 254 | `p.register_model("qwen", &gguf, meta(1000), None).unwrap();` — expression statement, empty `deltas` | 1 |
| 255 | `let a = p.create_agent("qwen", 50, None, 10_000).unwrap();` | 1 |
| 257 | `match p.infer(&a.id, "hi", 16, None) { … }` — a block-like expression statement (no `;`; lines 257–261), empty `deltas`; its probe goes after the closing brace | 1 |
| 259 | `Err(PagerError::Substrate(msg)) => …` — the arm taken on the passing path; its binding LINE for `msg` (§3.2) | 1 |
| 263 | `let dir2 = fresh_dir("bloomery-pager-contract2");` | 1 |
| 264 | `let jpath2 = dir2.join("j.jsonl");` | 1 |
| 265 | `let journal = Journal::open(&jpath2).unwrap();` | 1 |
| 266 | `let images = ImageStore::new(&dir2.join("img")).unwrap();` | 1 |
| 267 | `let mut fake = FakeSubstrate::new();` | 1 |
| 268 | `fake.script_reply(Reply { … });` — one statement, lines 268–273, empty `deltas` | 1 |
| 274 | `let mut p2 = Pager::new(fake, journal, images, Box::new(\|\| Some(10u64.pow(9))));` — one statement; the closure is not focused (§3.3) | 1 |
| 275 | `let gguf2 = write_gguf(&dir2, "fake.gguf", b"weights");` | 1 |
| 276 | `p2.register_model("qwen", &gguf2, meta(1000), None).unwrap();` | 1 |
| 277 | `let a2 = p2.create_agent("qwen", 50, None, 10_000).unwrap();` | 1 |
| 278 | `match p2.infer(&a2.id, "hi", 16, None) { … }` — block-like statement, lines 278–281, empty `deltas`. The arm taken (line 279, `Err(PagerError::Contract(_)) => {}`) binds **no** identifier — `_` is a wildcard, not a name — so §3.2 mints no binding LINE, and its body is an empty block with zero statements. | 1 |
| 282 | `let events = replay(&jpath2).unwrap();` | 1 |
| 283 | `assert!(events.iter().any(\|e\| matches!(…)));` — macro statement, lines 283–284, empty `deltas`; the closure body is not focused | 1 |
| 286 | `let status = p2.status();` | 1 |
| 287 | `assert_eq!(status.agents[0].budget_spent, 0);` — macro statement, empty `deltas` | 1 |
| 292 | `let failed = replay(&jpath).unwrap();` | 1 |
| 293 | `assert!(…, "a failed call still journals …: {failed:?}");` — macro statement, lines 293–299 | 1 |
| 300 | `assert!(!failed.iter().any(\|e\| matches!(e, Event::InferCompleted { .. })));` — macro statement, lines 300–302, terminated by the `;` on line 302; the body therefore has **no** tail expression | 1 |
| **N** | | **26** |

**Deliberately not counted, named here so a diff of lines can be read against
a rule rather than against a guess:**

- Line 260 (`other => panic!(…)`) and line 280 (the same) — the arms **not**
  taken. The passing path is decided from the source and is not a judgment:
  at 257 the pager is built by `pager_in(&dir, 0, …)`, i.e. with **zero**
  scripted replies, so `FakeSubstrate::infer` returns
  `SubstrateError::Infer("script exhausted")`
  (`crates/bloomery-substrate/src/fake.rs:165`), which is the `Substrate` arm
  the comment on line 258 names and the arm the `assert!` on 259 checks; at
  278 the reply scripted on 268–273 has `prompt_tokens: None`, which is the
  `Contract` arm. Either `other` arm would `panic!`, and this test passes in
  the clone's suite, so neither runs.
- Line 279's arm body `{}` — an empty block, zero statements.
- The closure bodies at 274, 283, 296 and 302 — §3.3, call-level only.
- The bodies of `fresh_dir`, `pager_in`, `write_gguf` and `meta`
  (`crates/bloomery-daemon/tests/common/pager.rs`) — helpers are not focus
  values, and only a focus value's own body is probed.
- No tail expression exists to exclude: the body's last statement (line 300)
  is `;`-terminated.

**The three readings, and which one is the gate.** The one place where the
design's rules do not settle the count by themselves is line 259: its arm body
is a bare expression (`=> assert!(…)`), not a block, and §3.2 places an arm's
binding LINE "inside the arm/loop body". Design §6's `focus_match_binding`
corpus case exercises only **block** arm bodies, so the non-block case is
genuinely open in the design as written.

| reading | N | what it would mean |
|---|---|---|
| **A — the gate** | **26** | §3.2 read as written: an arm that binds a pattern gets its binding LINE whether or not its body is a block; the arm's bare expression becomes the wrapping block's tail and is therefore not a statement (§3.1). |
| B | 25 | the transform will not wrap a non-block arm body, so line 259 mints no row. |
| C | 27 | the transform wraps the arm body as a block *and* makes its expression a statement inside it, so line 259 mints both a binding LINE and a statement LINE. |

26 is the gate. A measured 25 or 27 is a MISS of the gate that this section
already accounts for: it is recorded with the diff of lines, read as the
§3.1/§3.2 under-specification named above, and obliges §3.2 to state which
reading ships and a corpus case to pin it, before merge. Any count outside
{25, 26, 27} is a **STOP**.

### 1.2 The three `watch` triples for H4

The `--at` spec is the bare qualname in every case — `--at
missing_stats_is_a_contract_violation_not_a_reply` and `--at
pager_with_model` — with no `module:` prefix. Both names are unique in the
workspace, so the bare spec is an exact qualname match; design §4.1's
`::`-boundary prefix rule is not exercised here and is pinned by the corpus
instead.

| # | run | qualname | `--expr` | predicted verdict | exit | line |
|---|---|---|---|---|---|---|
| W1 | F1 | `missing_stats_is_a_contract_violation_not_a_reply` | `dir == "/tmp/bloomery-pager-contract"` | **SATISFIED** | **0** | 251 |
| W2 | F1 | `missing_stats_is_a_contract_violation_not_a_reply` | `len(events) == 0` | **NOTHING WAS CHECKED** | **3** | 282 |
| W3 | F2 | `pager_with_model` | `dir == "/tmp/bloomery-pager-contract"` | **not satisfied** | **1** | 22 |

**W1's derivation.** Line 251 is `let dir = fresh_dir("bloomery-pager-contract");`.
`fresh_dir` (`tests/common/pager.rs:65–70`) returns
`std::env::temp_dir().join(name)`, and with `TMPDIR` unset `temp_dir()` is
`/tmp`, so `dir` is the `PathBuf` `/tmp/bloomery-pager-contract`. `PathBuf`'s
`Debug` is the quoted string `"/tmp/bloomery-pager-contract"` — 30 bytes, well
inside the 200-byte cap, so `trunc` is false. Design §4.2 resolves a `dbg`
capture to the literal its text parses as, and a quoted string to its unquoted
value; the comparison is therefore true at line 251's LINE and, through
`watch`'s forward fold, at every later site of the frame. Hits are reported,
not predicted. Sites that cannot evaluate `dir` (the CALL row — Rust CALL rows
carry no args — and the parameters LINE at 250, which precedes the binding)
appear as a caveat above the verdict and change neither the class nor the exit.

**W2's derivation.** Line 282 is `let events = replay(&jpath2).unwrap();`,
binding `Vec<Event>`; `Event` derives `Debug`
(`crates/bloomery-core/src/journal.rs:8`), so the capture is `dbg`. Design
§4.2: "`len(name)` over a `dbg` value is unevaluable at that site". Before
line 282 `events` is out of scope; from 282 on it is a `dbg`. So **no** site
evaluates, `watch` takes its `evaluated == 0` branch, and the verdict is
`NOTHING WAS CHECKED` at exit 3 (`Says.NOTHING_CHECKED` → `UNSETTLED`).
`events` is recorded somewhere in the trace, so it is not a never-recorded
ghost and the ghost line does not fire. This triple is the one that tests
§4.2's unevaluable path, and its prediction does not depend on how long
`Vec<Event>`'s `Debug` runs or on whether the capture truncates.

**W3's derivation, and why it is the control for W1.** `pager_with_model(dir:
&Path)` binds `dir` on its parameters LINE at line 22; `&Path`'s `Debug` is
the quoted path, short and untruncated. Its twenty callers, all in
`pager_codec_gate_test.rs`, pass `fresh_dir("bloomery-codec-gate-…")` or
`fresh_dir("bloomery-refusal-gate-…")` (lines 66, 87, 98, 118, 133, 157, 167,
180, 216, 231, 241, 268, 307, 382, 399, 423, 440, 453, 467, 504) — not one of
them is `bloomery-pager-contract` — and F2 records only the
`pager_codec_gate_test` binary, which does not contain focus value A at all.
So every site that evaluates evaluates to **false**, and at least one site
evaluates. The same literal that must HIT in W1 must MISS here: if `--at`
scoping or the parameters LINE were wrong, W1 and W3 could not both come back
as predicted.

**Neither focus value binds an integer or a bool, and §1 says so rather than
pretending otherwise.** Design §7's H4 asks for "integer/bool bindings only".
Read at `e209ed9`, focus value A binds `dir`, `p`, `jpath`, `gguf`, `a`,
`msg`, `dir2`, `jpath2`, `journal`, `images`, `fake`, `p2`, `gguf2`, `a2`,
`events`, `status`, `failed`, and focus value B binds `dir`, `jpath`,
`journal`, `images`, `fake`, `p`, `gguf` — paths, strings and opaque structs,
and **no integer and no bool anywhere in either**. The triples above therefore
exercise the other two branches design §4.2 defines — the quoted-string branch
(W1, W3) and the unevaluable-`len` branch (W2) — and this is a stated reading,
not a substitution made quietly. The integer branch of §4.2 is pinned by the
corpus instead (`focus_let_chain`'s `b == 2`, `focus_loop_counter`'s
`flow --value 3`), which is the printing gate for it; E9 is the recorder's
claim under a real workspace, and this workspace has no integers to claim
about.

### 1.3 The two `flow --value` sightings for H5

Both on F1, both `flow <run> --value <literal>`. `parse_literal` leaves each
string a string (neither is quoted, neither is numeric), and design §4.2 makes
a `dbg` capture a sighting when it is untruncated and its text equals the
literal's **Debug rendering** — for a string, the literal *with* quotes.

| # | literal | binding | line |
|---|---|---|---|
| S1 | `/tmp/bloomery-pager-contract` | `dir` | 251 |
| S2 | `/tmp/bloomery-pager-contract2/j.jsonl` | `jpath2` | 264 |

**S1's derivation** is W1's: line 251, `fresh_dir("bloomery-pager-contract")`
over `temp_dir()` = `/tmp`, whose `PathBuf` `Debug` is
`"/tmp/bloomery-pager-contract"`.

**S2's derivation**: line 263 `let dir2 = fresh_dir("bloomery-pager-contract2");`
and line 264 `let jpath2 = dir2.join("j.jsonl");`, so `jpath2` is the `PathBuf`
`/tmp/bloomery-pager-contract2/j.jsonl` and its `Debug` is that path quoted.

**No other sighting of either literal among focus value A's LINE deltas.**
`--value` is equality, never a prefix test, and A's other path-valued bindings
are all distinct texts: `jpath` = `/tmp/bloomery-pager-contract/j.jsonl` (252),
`gguf` = `/tmp/bloomery-pager-contract/fake.gguf` (253), `dir2` =
`/tmp/bloomery-pager-contract2` (263), `gguf2` =
`/tmp/bloomery-pager-contract2/fake.gguf` (275). Note in particular that
`dir2`'s text differs from S1's by the trailing `2`, which equality separates
and a prefix test would not. A's remaining bindings cannot render as either
text: `journal` (`Journal`) and `images` (`ImageStore`) derive no `Debug` at
`e209ed9` and capture as `{"k": "unread"}`; `p`, `p2`, `fake`, `a`, `a2`,
`events`, `status` and `failed` are structs, enums and vectors whose `Debug`
carries type names and braces; and `msg` is the substrate's error text
(`"script exhausted"`, `crates/bloomery-substrate/src/fake.rs:165`), not a
path.

**Sightings outside A's LINE deltas are expected, and are reported rather than
gated** (H5's second reading). `fresh_dir` and `pager_in` are not focused but
are still instrumented at the call tier, so their RETURN values carry the same
texts; the gate is the sighting set restricted to focus value A's LINE deltas,
and the whole-trace set is printed beside it.

### 1.4 Lens, and the kill criteria

**Lens for every endpoint.** The reader is this repository's `.venv` Python
running `python -m sensorium` at the branch HEAD §2 records (Python and
`sensorium` versions in §2), and the rules it reads by are the design's, not
this document's: a `dbg` capture is read under **§4.2** (Debug text; a
truncated `dbg` never matches a `--value`; `len()` over a `dbg` is unevaluable
at that site, UNSETTLED rather than a comparison to nothing), and N is defined
by **§3.1/§3.2** (one probe per statement that completes normally, at every
block depth; the parameters LINE; an arm's or loop body's binding LINE once
per entry; no tail expression, no closure body, no helper body). The driver is
`cargo-sensorium` **built by the runner from this branch's HEAD at measurement
time**, with the commit, the `built_from` result and the binary's sha256
recorded in §2 before and after — the pre-repair-binary trap of the E6⁗ record
is why the runner builds it rather than trusting the path. Design §5 puts
`sensorium-rt`, `sensorium-transform` and `cargo-sensorium` at **0.4.0** and
Python `sensorium` at **0.8.3**; §2 records what each actually is, and every
version token inside a pinned sentence (H1's refusal) is read against §2's
recorded value rather than against that expectation. `SENSORIUM_TIER` is left
at its **default `call`** for all four runs — the coarse tier is not touched,
and the focus tier is a compile-time decision (ruling F2), so U1/U2 and F1/F2
differ only by the `--focus` flags. The invocation audit log is **not
silenced**: `SENSORIUM_NO_INVOCATION_LOG` is unset, so every reader invocation
this record makes is itself logged into the store, and §2 says so. The store
is a **new, empty `SENSORIUM_DIR`** and the target a **fresh
`CARGO_TARGET_DIR`**, both under `/mnt/extra/sensorium-rung2/` and both named
in §2 with their state at the start; H7's corpus target is fresh too. The
clone `/mnt/extra/sensorium-rung2/bloomery` is **read-only** and pinned at
`e209ed9` (`e209ed9b00f7eef647fb31d0b0895a5ad3b90807`), with HEAD, porcelain
and `Cargo.lock` recorded before and after and restored to the pin. **`TMPDIR`
is expected unset**, which is what makes `std::env::temp_dir()` `/tmp` and W1,
W3, S1 and S2 derivable at all; §2 records `TMPDIR` as observed, and if it is
set at measurement time those four values read against `<TMPDIR>/…` instead —
the same predictions with the prefix substituted, and §2 states which reading
was taken. **Every row above carries both its readings**, pre-committed here;
where a row's two readings disagree the disagreement is the finding and is
reported as one, never resolved silently in favour of the friendlier number.
Loads at every phase's start are recorded. Nothing is gated on a wall.

**Every measurement is `{value, n, lens, dropped}`**: a `null` value with a
reason is the only not-measured, `0` is measured-and-zero, and no endpoint is
ever filled from an expectation — the predictions above are in the room, and a
headline that borrowed from one could not fail.

**Kill criteria.**

1. **A compile failure of a focused unit is a STOP** (H2; design §9's first
   risk). Not a fallback to an unfocused build, not a retry under a narrower
   focus, not a skipped unit: the run stops, and the pattern that failed is
   the finding.
2. **A `.FAILED` marker before any number has been read is infrastructure.**
   The run is archived and relaunched from zero.
3. **A `.FAILED` marker after any number has been read is a STOP.**
4. **H3 outside {25, 26, 27} is a STOP** with the diff of lines (§1.1); 25 or
   27 is a MISS of the gate under the alternative readings §1.1 names.
5. **Measured once.** No endpoint is re-rolled and no completed measurement is
   re-run under a kinder command. A miss is recorded with its number.

The run is launched detached (`setsid nohup`) with a pid file and a
`.DONE`/`.FAILED` marker carrying `exit=<n>`; nothing below is read before the
marker exists.

**Reported without a gate**: H6's four walls and the focused rebuild's cargo
wall; the LINE-row totals of F1 and F2 and the per-site row counts; the number
of `deltas` that came back `{"k": "unread"}` and the number that came back
truncated, per run (an honesty count — `journal`, `images`, `p`, `p2` and
`fake` are expected among the first); whether `flags.bit0` (a dropped delta,
`unread: ["locals"]`) was ever set; W1's and W3's hit and not-captured counts;
the whole-trace sighting sets of S1 and S2 beside the gated ones; the store's
size and the disk free before and after.

**Amended 2026-09-06, before any measurement — the reader, not the endpoint.**
The instrument at commit `e2fc083` passes `--limit 1000` to the two
`flow --value` commands of §1.3, so the H5 gate is computed over every
sighting the trace holds rather than over the tool's default printed page of
50, and it publishes the H5 cells as null with a reason if that page still
truncates. The commands' literals, runs, predictions and both readings are
unchanged. Recorded under the rule the entry slice set (its R-G13): a reader
fix after the lock and before a number is a dated lens amendment, and the
runner carries both shas — the original lock `a4264b5` and this one.

## 2. Environment

Measured 2026-09-06T18:59:05-0500 → 2026-09-06T19:02:38-0500 by `rust/tests/acceptance_e9.py`, launched detached; the raw facts it recorded are `results-e9-raw.json` in the gitignored plan ledger, with every command's log beside it. §3 below is rendered from `2026-09-06-sensorium-rung4-e9.results.json`, which `acceptance_e9_schema.assemble_e9` derived from that raw file.

**§1 byte-lock.** The runner refuses to start unless the locked range is byte-identical to the commit that locked it — and refuses outright while no lock sha is set. The range is awk '/^## 1/,/^## 2/' PLUS the definition of every footnote §1 references — here §1 references no footnote (`footnotes_in_range` = none), so the extended range and `awk '/^## 1/,/^## 2/'` are the same bytes. Checked at `ffaed19`: 24095 bytes, sha256 `473f86203189bede2b56b19068770dbedba34f012b2c4a7f79012593d8960163` on both sides — identical: yes.

**Both locks.** §1 was committed ALONE at the ORIGINAL lock `a4264b5` (23424 bytes, sha256 `15f0537587f55ec949a60c86543e6c4e1f7a0929cc57eb4a15320424185b67a5`), and its §1.4 LENS was then amended — after that lock and before any number was read — to name the reader the instrument runs. Amended: yes (+671 bytes). Both shas are recorded here, and no endpoint, method, derivation or table row moved: every `|` row of the locked range is byte-identical at the two commits (`tests/test_acceptance_e9.py`).

| Pin | Value |
|---|---|
| repo HEAD at the run | `5e943833cf358da67536a7b96dc91b7d096f145f` (branch `feat/rung4-focus-tier`) |
| the clone under measurement (READ-ONLY input) | `/mnt/extra/sensorium-rung2/bloomery` at `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; §1.4's pin `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`; porcelain before / after empty / empty; HEAD after `e209ed9b00f7eef647fb31d0b0895a5ad3b90807` |
| the clone's `Cargo.lock` | sha256 `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` before, `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` after (moved: no); restored to the pin: yes |
| driver — BUILT by the runner from HEAD | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium` (debug profile), `cargo build -p cargo-sensorium` exit 0 in 0.059 s from HEAD `5e943833cf358da67536a7b96dc91b7d096f145f`; rebuilt: no |
| driver sha256 | `cf0c3f7fe4250e193f469794e6b95f33db2e358bf5efa7aa2f685015dfaad930` before, `cf0c3f7fe4250e193f469794e6b95f33db2e358bf5efa7aa2f685015dfaad930` after — unchanged: yes |
| trace store — FRESH and empty at the start | `/mnt/extra/sensorium-rung2/sensorium-dir/e9` |
| cargo target for the four runs — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e9` |
| H7's corpus target — FRESH | `/mnt/extra/sensorium-rung2/bloomery-target-e9-corpus` (named by `SENSORIUM_CORPUS_TARGET`: no) |
| Rust workspace target (H7's `cargo test --workspace`) | `/mnt/extra/sensorium-rung2/rust-target` |
| `TMPDIR` as observed | None — TMPDIR was unset, so `std::env::temp_dir()` is `/tmp` and W1/W3/S1/S2 read as §1.2 and §1.3 derive them |
| `SENSORIUM_TIER` | unset -- §1.4 leaves the coarse tier at its default `call` for all four runs, so U1/U2 and F1/F2 differ only by `--focus` |
| the invocation audit log | NOT silenced: SENSORIUM_NO_INVOCATION_LOG is unset, so every reader call this record makes appends a row to the store's `invocations.jsonl`, and the count is recorded at the end — rows in the store afterwards: 7 |
| toolchain | rustc 1.96.0 (ac68faa20 2026-05-25) / cargo 1.96.0 (30a34c682 2026-05-25) |
| reader | Python 3.14.4, sensorium 0.6.0 |
| machine | 16 cpus, governor `powersave` |
| repo porcelain before / after | empty / empty |
| 1-minute load at the start | 1.03 |
| disk free, repo filesystem, before / after | 12.73 GB / 12.73 GB |
| disk free, target filesystem, before / after | 92.12 GB / 90.12 GB |

**Log locations.** Every command's log is under `/home/brice/workspace/sensorium/.superpowers/sdd/2026-09-06-sensorium-rung4-focus-tier/acceptance-e9/logs`, one subdirectory per phase (`built-from`, `record-u1`, `record-f1`, `record-u2`, `record-f2`, `h1`, `h4`, `h5`, `h7`).

1-minute load at each phase's start: records 1.03, H1 1.22, H2 1.22, H3 1.22, H4 1.22, H5 1.22, H6 1.22, H7 1.22.

**The four runs.**

| run | command | exit | trace | libtest | wall | focus resolved |
|---|---|---|---|---|---|---|
| U1 | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium sensorium test -p bloomery-daemon --test pager_obligation_test` | 0 | `20260906-185911-1ba726` (942080 bytes) | 0.0 s | 6.693 s | — |
| F1 | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium sensorium --focus missing_stats_is_a_contract_violation_not_a_reply test -p bloomery-daemon --test pager_obligation_test` | 0 | `20260906-185918-bbfa7c` (958464 bytes) | 0.0 s | 6.69 s | ['missing_stats_is_a_contract_violation_not_a_reply'] |
| U2 | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium sensorium test -p bloomery-daemon --test pager_codec_gate_test` | 0 | `20260906-185920-580f4e` (507904 bytes) | 0.0 s | 1.448 s | — |
| F2 | `/mnt/extra/sensorium-rung2/rust-target/debug/cargo-sensorium sensorium --focus pager_with_model test -p bloomery-daemon --test pager_codec_gate_test` | 0 | `20260906-185926-fbede9` (520192 bytes) | 0.0 s | 6.587 s | ['pager_with_model'] |


**One launch, and it measured this record.** Launched once, detached, at
2026-09-06T18:59:05-0500 by `setsid nohup bash <ledger>/acceptance-e9/launch.sh`, stdout and
stderr redirected to `<ledger>/acceptance-e9/logs/e9.log`, runner pid 2069504; it wrote
`e9.DONE` carrying `exit=0` at 19:02:38 — **3 min 33 s**. It was polled with `ps -p` on the
pid file and the two marker names in a bounded 30 s loop (bound 90 min; the marker appeared
at poll 5), and **nothing was read before that marker existed**: not the log, not the raw
record, not `results.json`, not the store. Nothing was killed, `pkill` was never used, and
there is no `failed-launch-*` directory beside this record — §1.4's kill 2 was never
exercised. `stop`, `refused` and `error` in `results.json` are all `null`, and all **34**
`{value, n, lens, dropped}` cells carry a value: **0 nulls, 0 dropped reasons**.

**The launcher, checked before use and unchanged.** Its five `export`s are exactly the five
keys the runner refuses without (`SENSORIUM_DRIVER`, `SENSORIUM_BLOOMERY`,
`SENSORIUM_E9_TARGET`, `SENSORIUM_DIR`, `SENSORIUM_RUST_TARGET`); it `unset TMPDIR`s, the
reading §1.2 and §1.3 derive from; and it does not set `SENSORIUM_CORPUS_TARGET`, so H7's
corpus target is the derived `<E9 target>-corpus` (`corpus_target_from_env: false`).

**Preflight, by hand, before the launch.**

| check | value |
|---|---|
| `pgrep -a cargo` / `pgrep -a rustc` | both empty — nothing waited for, nothing killed |
| repo | `git status --porcelain` empty at `5e943833cf358da67536a7b96dc91b7d096f145f`, branch `feat/rung4-focus-tier` |
| the three FRESH locations | all three **absent** — the E9 target, the derived corpus target, the store; the runner made them |
| the clone | HEAD `e209ed9b00f7eef647fb31d0b0895a5ad3b90807`, porcelain empty, `Cargo.lock` sha256 `c089018581c9bd62a0d1d0d11effd8c042b4587ead0578f0351856e67beb9fca` |
| disk | target filesystem 86 GB free (the runner refuses below 8); repo filesystem 12 GB, and nothing large was written to it |
| `TMPDIR` | unset |
| driver sha256 BEFORE the runner's own in-place build | `cf0c3f7fe4250e193f469794e6b95f33db2e358bf5efa7aa2f685015dfaad930` |
| 1-minute load | 0.58 |
| reader | `.venv/bin/python` → Python 3.14.4 |
| §1 sha (`awk '/^## 1/,/^## 2/' \| sha256sum`) | `473f86203189bede2b56b19068770dbedba34f012b2c4a7f79012593d8960163` — the amended lock `ffaed19`'s |
| whole Python suite, WITHOUT the driver env | exit 0, **1426 passed, 12 skipped in 63.5 s** |

**The suite twice, and the driver once.** The pre-launch gate above ran under no
`SENSORIUM_*` variable and read 1426/12; H7 runs the same suite with
`SENSORIUM_CARGO_SENSORIUM` set and read **1437 passed, 1 skipped** — 1438 collected both
times, the 11 tests that skip without a built driver running there. The runner built the
driver from HEAD in place (`cargo build -p cargo-sensorium`, debug, exit 0 in 0.059 s,
`rebuilt: false`) and its sha256 `cf0c3f7fe425…d930` is the same by hand before the launch,
in `built_from` before and after that build, and in `cleanup.driver_sha256_after` after
H7's `cargo test --workspace`, which shares that target
(`cleanup.driver_unchanged: true`).

**What this run wrote, and one ledger tidy.** The store ended at 2 995 448 bytes over
**4** traces and **7** rows in `invocations.jsonl` — one per reader call (H1's `info`
and `watch`, H4's three, H5's two), the audit log deliberately un-silenced (§1.4). The
E9 target ended at 1 613 203 557 bytes and the corpus target at 657 035 678; the target
filesystem went 92.12 → 90.12 GB free, the repo filesystem 12.73 → 12.73 GB. The clone's
`Cargo.lock` did not move (`clone_cargo_lock_moved: false`,
`clone_cargo_lock_back_on_the_pin: true`). Before the launch, two log subdirectories left
by Task 7's dry runs (`logs/prep`, `logs/built-from`) were moved to
`acceptance-e9/pre-task-8-logs/` so every file under `logs/` is this run's; no measurement
code, no location the runner reads and no document was touched.

## 3. Results

The gate of each row, and both readings where §1 pre-committed two. A `null` is not-measured with its reason; `0` is a measured zero.

### H1 — does an unfocused run stay unfocused?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| LINE rows over the whole U1 trace (the gate: 0) | 0 | None | LINE rows over the whole U1 trace -- the gate is 0; U1 -- `cargo sensorium test -p bloomery-daemon --test page… | none |
| meta `capabilities.line` | False | None | the trace's own meta `capabilities.line`, read from the converted trace and not from the printed row | none |
| meta `capabilities.locals` | False | None | the trace's own meta `capabilities.locals` | none |
| the class `watch` printed | REFUSED | 1 | the class `watch` printed, of the verdict sentences found (more than one is itself a defect and leaves the cla… | none |
| the exit `watch` returned | 3 | None | the exit status `watch` returned -- 3 is UNSETTLED, `record again with what it lacks` | none |
| the refusal sentence, with §2's recorded token (2nd reading) | True | None | SECOND reading: the pinned refusal sentence with the version token taken from the trace's own `recorder` meta … | none |

Rule: `capabilities.line` and `capabilities.locals` both false; LINE rows 0; the pinned refusal at exit 3.  
Recorder as the trace declares it: `sensorium-rt 0.4.0`.  
Expected sentence: `REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 declares it does not produce (capabilities.line: false); nothing was checked`.  
Printed sentence: `REFUSED: watch needs line, which recorder sensorium-rt 0.4.0 declares it does not produce (capabilities.line: false); nothing was checked`.  
Command: `sensorium watch 20260906-185911-1ba726 --at missing_stats_is_a_contract_violation_not_a_reply --expr events == 0`; the count is `select count(*) from events where kind = 'LINE'`.


### H2 — does a focus resolve and build?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| focus values resolving to exactly one qualname (the gate) | 2 | 2 | FIRST reading: `--focus` values that resolved to exactly one qualname, of the values given; the driver's own `… | none |
| pairs whose libtest counts are equal (1st reading) | 2 | 2 | FIRST reading of `equal outcome`: pairs whose summed libtest pass/fail/ignored/measured/filtered counts are eq… | none |
| focused traces whose LINE qualname set is exactly the value (2nd reading) | 2 | 2 | SECOND reading of `resolved to that one`: focused traces whose set of distinct qualnames carrying LINE rows is… | none |
| pairs whose process exit status is equal (2nd reading) | 2 | 2 | SECOND reading of `equal outcome`: pairs whose `cargo sensorium` process exit status is equal, of the pairs | none |
| focused runs that did not complete (§1's kill 1) | 0 | 2 | focused runs that did not complete -- §1's kill 1 makes any a STOP: no unfocused fallback, no narrower focus, … | none |

Rule: both values resolve to exactly one qualname; F1's counts equal U1's and F2's equal U2's; a focused compile failure is a STOP.

| run | `--focus` value | the driver's `focus:` lines |
|---|---|---|
| F1 | `missing_stats_is_a_contract_violation_not_a_reply` | ['missing_stats_is_a_contract_violation_not_a_reply'] |
| F2 | `pager_with_model` | ['pager_with_model'] |

| pair | focused summary | unfocused summary |
|---|---|---|
| F1/U1 | ['test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s'] | ['test result: ok. 15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s'] |
| F2/U2 | ['test result: ok. 20 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s'] | ['test result: ok. 20 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s'] |


### H3 — one LINE per completed statement?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| N — the LINE rows of A's activation (the gate: 26) | 26 | 26 | N: the LINE rows of focus value A's activation, of §1.1's hand count; the gate is 26, 25 and 27 are the two re… | none |
| N equals the gate | True | 26 | N equals §1.1's reading A, the gate | none |
| lines differing from §1.1's table (2nd reading) | 0 | 26 | SECOND reading: missing + unexpected + count-differing lines against §1.1's per-line table, of its 26 rows -- … | none |
| activations of the focus value | 1 | None | frames whose code object is focus value A -- §1 derives N from ONE activation, so anything but 1 changes what … | none |
| the frame join and the code join agree | True | None | the frame join and the code-object join count the same rows; a disagreement is a finding about attribution, no… | none |
| N is inside {25, 26, 27} | True | 3 | N is inside {25, 26, 27}; outside it is §1's kill 4, a STOP | none |

Rule: N = 26 (the gate); 25 or 27 is a MISS §1.1 accounts for; anything else is a STOP.

Missing lines: `[]`; unexpected: `[]`; count differences: `[]`.

| source line | LINE rows |
|---|---|
| 250 | 1 |
| 251 | 1 |
| 252 | 1 |
| 253 | 1 |
| 254 | 1 |
| 255 | 1 |
| 257 | 1 |
| 259 | 1 |
| 263 | 1 |
| 264 | 1 |
| 265 | 1 |
| 266 | 1 |
| 267 | 1 |
| 268 | 1 |
| 274 | 1 |
| 275 | 1 |
| 276 | 1 |
| 277 | 1 |
| 278 | 1 |
| 282 | 1 |
| 283 | 1 |
| 286 | 1 |
| 287 | 1 |
| 292 | 1 |
| 293 | 1 |
| 300 | 1 |


### H4 — does `watch` answer?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| triples as predicted on BOTH readings (the gate) | 3 | 3 | triples whose verdict class AND exit status are both as §1.2 predicts, of the three; §1.2's three triples, eac… | none |
| verdict classes as predicted (1st reading) | 3 | 3 | FIRST reading: verdict classes as predicted (SATISFIED / NOTHING WAS CHECKED / not satisfied) | none |
| exit statuses as predicted (2nd reading) | 3 | 3 | SECOND reading: exit statuses as predicted (0 / 3 / 1) | none |
| triples where the two readings disagree | 0 | 3 | triples where the class and the exit do not agree -- itself a finding about `Verdict`/`STATUS` | none |

Rule: all three triples as predicted, on both readings.

| # | run | `--expr` | predicted | class | exit |
|---|---|---|---|---|---|
| W1 | F1 | `dir == "/tmp/bloomery-pager-contract"` | SATISFIED / 0 | SATISFIED | 0 |
| W2 | F1 | `len(events) == 0` | NOTHING WAS CHECKED / 3 | NOTHING WAS CHECKED | 3 |
| W3 | F2 | `dir == "/tmp/bloomery-pager-contract"` | not satisfied / 1 | not satisfied | 1 |

§1.4's ungated bucket counts, from `watch`'s own counts line:

| # | sites | evaluated | hits | not-captured | errors |
|---|---|---|---|---|---|
| W1 | 27 | 25 | 25 | 2 | 0 |
| W2 | 27 | 0 | 0 | 27 | 0 |
| W3 | 180 | 160 | 0 | 20 | 0 |


### H5 — does `flow --value` see it?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| sightings found at the predicted line (the gate) | 2 | 2 | FIRST reading (the gate): sightings found among focus value A's LINE deltas at the line §1.3 derives, of the t… | none |
| unpredicted sightings among A's LINE deltas | 0 | 2 | sightings of the literal among A's LINE deltas at any OTHER line -- the gate is 0, and `--value` is equality, … | none |
| every printed sighting row, per literal (2nd reading) | {'S1': 2, 'S2': 1} | 2 | SECOND reading (reported, not gated): every sighting of the literal ANYWHERE in the trace, per literal, gated … | none |

Rule: both sightings found among A's LINE deltas, and no unpredicted one there.  
Every printed page held the whole sighting set.

| # | literal | sighting events | rows printed (`--limit`) | gated to A's LINE deltas | at the predicted line |
|---|---|---|---|---|---|
| S1 | `/tmp/bloomery-pager-contract` | 2 | 2 (1000) | 1 | yes |
| S2 | `/tmp/bloomery-pager-contract2/j.jsonl` | 1 | 1 (1000) | 1 | yes |


### H6 — what does it cost?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| the slowest invocation wall, s | 6.693 | 4 | REPORTED, NOT GATED: the slowest of the four invocation walls, seconds, of the runs timed; F1 against U1 and F… | none |
| libtest's own reported time, s (1st reading) | {'U1': 0.0, 'F1': 0.0, 'U2': 0.0, 'F2': 0.0} | 4 | FIRST reading: libtest's own reported time per run, seconds (null for a run whose summary line carried none) | none |
| the whole invocation's wall, s (2nd reading) | {'U1': 6.693, 'F1': 6.69, 'U2': 1.448, 'F2': 6.587} | 4 | SECOND reading: the wall of each whole `cargo sensorium` invocation, seconds | none |

Rule: reported, not gated.

| pair | libtest focused / unfocused | invocation focused / unfocused |
|---|---|---|
| F1/U1 | 0.0 s / 0.0 s | 6.69 s / 6.693 s |
| F2/U2 | 0.0 s / 0.0 s | 6.587 s / 1.448 s |


### H7 — did nothing else move?

| Measurement | Value | n | Lens (abridged; the full lens is in `results.json`) | Dropped |
|---|---|---|---|---|
| corpus questions whose answer is not the registered one (the gate) | 0 | 125 | FIRST reading: corpus questions whose printed answer is not the case's registered expectation, of the question… | none |
| the collector's exit status (2nd reading) | 0 | 57 | SECOND reading: the collector's exit status, of the cases it ran -- 0 is every case equal | none |
| cases that crashed the collector | 0 | 57 | harness errors -- a case that crashed the collector answered nothing and is not a pass | none |
| cases the collector SKIPPED (gate: 0) | 0 | 57 | cases the collector SKIPPED, of the cases -- `run_corpus` skips a cargo case when it can find no driver and st… | none |
| `pytest -q` exit status | 0 | None | `pytest -q` exit status -- 0 is green | none |
| the suite's summary line | 1437 passed, 1 skipped in 125.03s (0:02:05) | None | the suite's own summary line, recorded whole | none |
| `cargo test --workspace` exit status | 0 | 39 | `cargo test --workspace` exit status, of its `test result:` lines | none |

Rule: every corpus case equal; the Python suite green; the Rust workspace green.  
Corpus: 57 cases, 125 questions, failures `[]`, skipped `[]`.  
Rust: `['test result: ok. 278 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.14s', 'test result: ok. 18 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.29s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.23s', 'test result: ok. 13 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.73s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 2.38s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 81 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.05s', 'test result: ok. 17 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 6 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 44 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 35 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.11s', 'test result: ok. 12 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.03s', 'test result: ok. 22 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.02s', 'test result: ok. 38 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.01s', 'test result: ok. 11 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.10s', 'test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 1.59s', 'test result: ok. 0 passed; 0 failed; 9 ignored; 0 measured; 0 filtered out; finished in 0.00s', 'test result: ok. 0 passed; 0 failed; 14 ignored; 0 measured; 0 filtered out; finished in 0.00s']`.


### Reported without a gate — §1.4's honesty counts

| run | LINE rows | LINE deltas | `{"k": "unread"}` | truncated | rows with `unread: ["locals"]` (`flags.bit0`) | recorder's `truncated_count` |
|---|---|---|---|---|---|---|
| U1 | 0 | 0 | 0 | 0 | 0 (bit0 ever set: no) | 20 |
| F1 | 26 | 17 | 5 | 3 | 0 (bit0 ever set: no) | 23 |
| U2 | 0 | 0 | 0 | 0 | 0 (bit0 ever set: no) | 24 |
| F2 | 160 | 140 | 80 | 0 | 0 (bit0 ever set: no) | 24 |

§1.4's honesty count, reported without a gate; `journal`, `images`, `p`, `p2` and `fake` are expected among the unread

Unread delta names, per run: `{'F1': {'fake': 1, 'images': 1, 'journal': 1, 'p': 1, 'p2': 1}, 'F2': {'fake': 20, 'images': 20, 'journal': 20, 'p': 20}}`.

## 4. Verdicts

Written by hand against §1's rules, from `results.json` and the raw record and its logs
in the gitignored plan ledger. One row per §1 endpoint, with the number that decided it
and — where §1 pre-committed two readings — both. Launched ONCE, detached, 18:59:05 →
19:02:38 on 2026-09-06, and measured once: nothing was re-run, re-scoped or
re-classified after a number was read, no `--focus` was narrowed, no unfocused fallback
was taken, there is exactly one `e9.DONE` at `exit=0` and no `failed-launch-*` beside
it, and §1 was not touched — its sha256 is
`473f86203189bede2b56b19068770dbedba34f012b2c4a7f79012593d8960163` before and after
(§2), at the amended lock `ffaed19`. **The assembly is deterministic**: `--assemble`
re-run once after `.DONE` gave a `results.json` whose JSON leaf-path diff against the
committed one has exactly **one** changed path, `assembled.at`, and a byte-identical
`section-2-3.md`, with the raw record's md5 `99b29dca3a93bb2002f90aa301ca0c14` before
and after.

| Id | §1's rule, verbatim | What was measured (both readings) | Verdict |
|---|---|---|---|
| H1 | "meta `capabilities.line = false` **and** `capabilities.locals = false`; **LINE rows = 0**; `watch` prints `REFUSED: watch needs line, …` and exits **3**." | U1's trace meta declares `line: false` and `locals: false`; **0** LINE rows over the whole trace (`select count(*) from events where kind = 'LINE'`); `watch --at missing_stats_… --expr events == 0` printed class **REFUSED** and returned exit **3**. Second reading (the one token that can move): the recorder the trace itself declares is `sensorium-rt 0.4.0`, and the printed sentence is **byte-equal** to the pinned one with that token substituted (`refusal_equal: true`). | **PASS** |
| H2 | "Each value **resolves to exactly one qualname**; F1's pass/fail/ignored counts equal U1's and F2's equal U2's. … **A compile failure of a focused unit is a STOP**." | **2 of 2** values resolved to exactly one qualname, read from the driver's own `focus:` lines on stderr before cargo ran; **2 of 2** pairs have equal libtest counts (`15 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out` for F1/U1, `20 passed; …` for F2/U2). Second readings: the set of distinct qualnames carrying LINE rows is exactly `{missing_stats_is_a_contract_violation_not_a_reply}` in F1 and exactly `{pager_with_model}` in F2 (**2 of 2**), and **2 of 2** pairs have equal process exit status (0 and 0). **0** focused runs failed to complete — `focused_build_failures` is 0 of 2, so kill 1 did not fire. | **PASS** |
| H3 | "**LINE rows = N = 26** … **26 = PASS (the gate)**; 25 or 27 … a MISS … **Any other count is a STOP**." | **N = 26**, over **1** activation of focus value A, from the frame join `events → frames → code_objects`. Second reading: **0** line differences against §1.1's 26-row table — `missing []`, `unexpected []`, `count_diffs []`, every one of the 26 lines carrying exactly one LINE row. The code-object join gives the identical histogram (`joins_agree: true`); N is inside {25, 26, 27}, so kill 4 did not fire. | **PASS** |
| H4 | "**All three as predicted → PASS.** Each prediction is two pre-committed readings … the verdict class … and the exit status … (0 / 1 / 3)." | **3 of 3** triples as predicted on BOTH readings. W1 `SATISFIED` / exit **0**; W2 `NOTHING WAS CHECKED` / exit **3**; W3 `not satisfied` / exit **1** — each the class §1.2 named and each the exit beside it. **0** triples where the two readings disagree, so the `Verdict`/`STATUS` finding §1 reserved a place for has nothing to report. | **PASS** |
| H5 | "**Both found, and no unpredicted sighting of that literal among focus value A's LINE deltas → PASS.**" | **2 of 2** sightings found among focus value A's LINE deltas at the line §1.3 derives — S1 at 251, S2 at 264 — and **0** unpredicted sightings of either literal at any other line of A's LINE deltas. Second reading (reported, not gated): every sighting anywhere in the trace is `{S1: 2, S2: 1}`; neither printed page truncated (`--limit 1000`, 2 and 1 rows printed, `page_truncated: false` on both), so the gate was computed over the whole sighting set. | **PASS** |
| H6 | "**Reported, not gated**, under both readings." | First reading (libtest's own reported time): **0.00 s** on all four runs — the binaries are too fast for libtest's resolution, so the pair deltas are 0.0 s and 0.0 s. Second reading (the whole invocation's wall, focused rebuild included): U1 **6.693 s**, F1 **6.690 s**, U2 **1.448 s**, F2 **6.587 s** — F1/U1 −0.003 s, F2/U2 **+5.139 s**. §5.3 reads them. | **REPORTED** (no gate) |
| H7 | "**Every corpus case equal**; Python suite green; Rust workspace green." | The collector over **57** cases and **125** questions: **0** questions whose printed answer is not the registered one, **0** harness errors, **0** cases SKIPPED — so all 37 `corpus/rust/*` cases ran, the six `focus_*` cases of design §6 included, and none was skipped for want of a driver. Second reading, each suite's exit status: collector **0**, `pytest -q` **0** (`1437 passed, 1 skipped in 125.03s`), `cargo test --workspace` **0** over **39** `test result: ok.` lines. | **PASS** |

**Overall: six PASS and one REPORTED — all seven as pre-registered, and the one number
the whole slice was built to produce came back exactly.** H3 read **N = 26** with a
per-line diff of zero: not merely the right total, but the right total on the right 26
lines (§5.1). Nothing was dropped, no reader hit its 120 s ceiling, no kill fired, and no
endpoint fell back to an expectation.

## 5. Gaps

### 5.1 The one line §1.1 said the design does not settle — and what measurement said

§1.1 named line 259 as the single line the design's rules do not decide by themselves:
its arm body is a bare expression (`=> assert!(…)`), not a block, and design §3.2 places
an arm's binding LINE "inside the arm/loop body". It pre-registered three readings —
**A** (26, the gate: the binding LINE is minted whether or not the body is a block, and
the bare expression becomes the wrapping block's tail and so is not a statement), **B**
(25), **C** (27) — with 25 and 27 accounted misses and anything else a STOP.

**Measured N = 26 with a zero per-line diff.** `endpoints.H3.headline.value` is 26 over
`n = 26`; `line_differences` is 0; `reported.line_histogram` gives each of §1.1's 26
lines exactly one row and no row at any other line, and
`reported.line_histogram_via_code_id` — the independent code-object join — is the
identical mapping (`joins_agree: true`), over `activations: 1`. **Reading A holds; B and
C are both falsified here**: line 259 minted its binding LINE and did not mint a second,
statement row. §3.2 therefore needs no amendment to say which reading ships, and §1.1's
"obliging a §3.2 amendment and a corpus pin before merge" is not triggered — but the
non-block arm body is now measured and still unpinned (§5.5 item 2). **Which** 26
matters as much as how many: the arms not taken (260, 280), the empty arm body at 279,
the four closure bodies and the four helper bodies all minted nothing, and there is no
tail expression to exclude — written down as a rule before the transform could produce a
competing number.

### 5.2 The three `watch` triples and the two `flow` sightings

**All three triples came back on both readings** (`endpoints.H4`: `headline` 3,
`class_as_predicted` 3, `exit_as_predicted` 3, `readings_disagree` 0). What makes the
trio load-bearing is that W1 and W3 are the same literal on two runs: W1 must HIT on F1
and W3 must MISS on F2, and both did, so `--at` scoping and the parameters LINE are
right in one measurement rather than separately. W2 exercised design §4.2's
unevaluable-`len` path and returned `NOTHING WAS CHECKED` at exit 3 — the `evaluated ==
0` branch — without depending on how long the value's `Debug` runs. **The bucket counts
§3 prints land where §1.2's derivation said** (`reported.watch_bucket_counts`, ungated):
W1's 2 not-captured of 27 sites are exactly the pair §1.2 predicted as a caveat — the CALL
row, which in Rust carries no args, and the parameters LINE at 250, which precedes the
binding — and W3's 20 of 180 are the CALL rows of B's 20 activations.

**Both sightings found, neither page truncated** (2 and 1 rows against `--limit 1000`,
`page_truncated: false`), with **0** unpredicted sightings among A's LINE deltas. §1.3
expected sightings outside those deltas, "the unfocused `common::pager` helpers … still
instrumented at the call tier"; that is true of **one** of the two literals. S1's
whole-trace set is 2 — its LINE row plus `fresh_dir`'s RETURN carrying the same text — while
**S2's is 1**: `jpath2` is built at 264 by a `PathBuf::join` on an already-bound value, a
std method no instrumented helper returns. The clause is reported, not a gate, so nothing
turns on it; the asymmetry is a fact about what the call tier sees.

### 5.3 Reported without a gate — §1.4's honesty counts, and the cost

* **The capability flip is per build.** U1 and U2 declare `line: false, locals: false`
  and carry **0** LINE rows; F1 and F2 declare both `true` and carry **26** and **160**.
  Ruling F2 made the tier a compile-time decision; the unfocused runs are the control.
* **F2's 160 LINE rows are 20 activations of 8.** §1 gates only A's single activation, so
  160 is nobody's prediction: 8 rows per call of `pager_with_model` over the 20 calls §1.2
  counted in that file, with W3's 180 sites (20 × (1 CALL + 8 LINE)) agreeing. The tier
  re-probes a function on every activation, not once per function.
* **The unread deltas are exactly the five names §1.4 expected, and no others**
  (`reported.unread_and_truncated_captures.per_run`). F1: 17 LINE deltas, **5** `{"k":
  "unread"}` — `fake`, `images`, `journal`, `p`, `p2`, one each — and **3** truncated:
  `events`, `failed`, `status`. F2: 140 deltas, **80** unread (the same names bar `p2`,
  20 each), **0** truncated. `flags.bit0` was **never set** in any run, and none of the
  three truncated names is either `flow` literal or either `watch` binding, so no gate
  was decided by a value that was cut. Against capture totals 1934 / 1951 / 499 / 639, the
  focus added 17 captures and 3 truncations to U1's trace, 140 captures and none to U2's.
* **The cost, and what it is a cost of.** libtest reported **0.00 s** for all four
  binaries — too fast to time at its resolution, so H6's first reading is a floor. The
  invocation walls are U1 **6.693 s**, F1 **6.690 s**, U2 **1.448 s**, F2 **6.587 s**:
  F1/U1 **−0.003 s** because U1 paid for the cold build F1 reused, F2/U2 **+5.139 s**
  because F2 rebuilt the test target under a focus. **Neither isolates run-time overhead**
  — every wall is dominated by compilation, and §1 gates nothing on a wall.
* **The whole measurement took 3 min 33 s**, of which H7 is 3 min 12 s (collector 54.9 s,
  `pytest` 125.0 s, `cargo test --workspace` 11 s) and the four runs together 21.4 s. The
  90-minute poll bound was budgeted for a cold build of a large dependency tree; this one
  is **83** locked packages with no async runtime (counted from the clone's `Cargo.lock` at
  the pin, not a `results.json` field), so E9's cost is dominated by **this** repository's
  suites, not by the subject.

### 5.4 What this run did not measure, and the one deviation

* **One clone, one commit, two functions, one test binary each.** A focus value inside an
  inline `mod`, an `async` or macro-produced body, a value matching more than one qualname,
  and a focused unit that fails to compile are all untested — the last is what §1's kill 1
  exists for, and it did not fire. **No integer or bool binding was watched** (§1.2 says so
  and why; that branch of design §4.2 is pinned by the corpus), and **no second activation
  of focus value A**, so whether a second mints the same 26 is what F2's 20 activations
  suggest and what nothing here proves for A.
* **The clone was read, not written** — HEAD, porcelain and `Cargo.lock` sha256 are the
  pin's before and after, and the lock did not move at all. **One launch**: pid 2069504,
  one `e9.DONE` at `exit=0`, no `failed-launch-*` and no partial record, so §1.4's
  kill-2 relaunch rule was never exercised — said here rather than left to be inferred
  from an absence.
* **One deviation from §1's spelled commands, already inside the lens.** Both `flow
  --value` commands ran with `--limit 1000`, because every H5 number is read off the
  printed rows and the tool's default page is 50. §1.4 carries the dated amendment for
  it — *"Amended 2026-09-06, before any measurement — the reader, not the endpoint"* —
  committed alone at `ffaed19` after the original lock `a4264b5` and before any number was
  read, both shas in the record (`amended_after_the_original_lock: true`, +671 bytes, no
  `|` row moved). Its guard did not have to fire: neither page truncated, so H5 would have
  read the same under §1.3's unlimited spelling.

### 5.5 Residuals found by this run, recorded and not repaired

1. **`reported.line_rows_per_run` published four nulls.** It reads `meta.counts`, a key
   the Rust trace's `meta` does not carry (format 4 has `truncated_count` but no
   `counts`; the `recorded: CALL … LINE …` line `info` prints is computed by the
   reader). The number §1.4 asks for under *"the LINE-row totals of F1 and F2"* **is**
   in the record — the census's `line_events`, 0 / 26 / 0 / 160, which §3's ungated
   table prints — so this is a duplicate field shaped for the Python recorder, not a
   missing number. It is reported, not a measurement cell, so the "no null without a
   reason" rule does not reach it: that is the residual.
2. **The non-block arm body is measured but not pinned.** §5.1 settles line 259 in favour
   of reading A here; design §6's `focus_match_binding` exercises block arm bodies only,
   so nothing would catch a regression. This task writes documents, not cases.
3. **H6's first reading carries no information at this size.** libtest reported `0.00s`
   four times; any future claim about the tier's run-time cost needs a subject whose
   test binary takes long enough to time.
4. **The suite's skip count still depends on one variable** — 1426/12 without
   `SENSORIUM_CARGO_SENSORIUM`, 1437/1 with it, both seen today (§2). The entry slice's
   repair record carried the same residual at 1293/9 against 1301/1; the delta is now 11
   tests rather than 8.

### 5.6 What this record licenses, and what it does not

It licenses the focus tier's central claim **on this workspace**: under `cargo sensorium
--focus`, a focused Rust function receives one LINE event per completed statement at
every block depth, on exactly the lines design §3.1 and §3.2 predict and on no others —
26 of 26, zero differences — carrying the bindings that statement wrote; an unfocused
build of the same crate stays unfocused (0 LINE rows, `line: false`); a focus resolves
to exactly one qualname and changes neither the test outcome nor the exit status; and
`watch` and `flow --value` read the resulting `dbg` captures under design §4.2 as §1.2
and §1.3 derived them, including the unevaluable-`len` path and the same-literal
HIT/MISS control.

It does **not** license, and none of it is done here: a generalisation beyond one clone at
one commit (§5.4); a cost claim (§5.3, §5.5 item 3); a second measurement — §1.4's kill 5
binds this record, and a corrected or extended endpoint is a NEW pre-registration in a NEW
document, measured once; or re-opening an earlier record — the rung-3 borrow-repair
acceptance and both rung-4 entry-grain records stand as written.
