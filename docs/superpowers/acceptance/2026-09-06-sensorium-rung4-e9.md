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
lock range and the `awk` range are the same bytes. §1 is not amended: there is
one sha and no dated note inside it.

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

## 2. Environment

(written by Task 8)

## 3. Results

(written by Task 8)

## 4. Verdicts

(written by Task 8)

## 5. Gaps

(written by Task 8)
