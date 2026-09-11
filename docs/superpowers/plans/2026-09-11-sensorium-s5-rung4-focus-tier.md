# S5 rung 4 — the focus tier for TypeScript: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sensorium ts run --focus <spec>` records one LINE per completed statement of a focused TypeScript function, its `deltas` the bindings the statement wrote, the CALL's arguments, and a never-recycled identity on every captured object — so `watch`, `flow --value`, `flow --object`, `frame` and `tree` answer on a TypeScript trace the way they answer on a Python one, measured on the VTT lens against a hand count locked before any code.

**Architecture:** The focus is decided at transform time (spec D1): the driver resolves every spec before the run through a Node resolver that reuses the transform's own first pass, refuses at exit 2, and hands the specs to the harness in one environment variable; the plugin and the loader hook pass them into `transformSource`, which marks matched sites and splices a probe after every statement of a focused function, per-entry rows for guarded bodies, `unbound` lists on block-like statements, and an args array on the CALL. Two pure analysis modules (`bindings.mjs`, `focus.mjs`) decide the names; the runtime writes `LINE` records and `oid`/`type` on object captures; the converter writes the rows the readers already know. On the Python side the readers gain a second `dbg` dialect behind the vocabulary, four predicate constants, one site spelling shared with `--focus`, a per-language re-record template, and a serial identity basis for `flow --object`.

**Tech Stack:** Node ≥ 24 ESM `.mjs` + JSDoc under `tsc --checkJs` (`typescript/`), `magic-string`, the consumer's own `typescript`; Python 3.13 (`src/sensorium/`), pytest; vitest 4.1.9 for the probes and the corpus; bash acceptance scripts; the VTT lens copy.

**Spec:** `docs/superpowers/specs/2026-09-11-sensorium-s5-rung4-focus-tier-design.md` (main `aea6b47`, PR #33). The spec is the authority; this plan is its argument. Section numbers below (§2.1, §3.2, §8 …) are the spec's unless they say "plan".

## Global Constraints

- **Recording is allowed this rung, into a FRESH store.** The lens is the VTT frontend copy at `0091e97` (`typescript/acceptance/LENS.txt`), read-only for the whole rung — nothing under it is edited, and `sha256sum -c` of its manifest brackets every session. The store is a directory under `/mnt/extra/sensorium-s5/` named for this rung (reached ONLY through `SENSORIUM_DIR`, named by the label `<store>` in every committed file). `store-rung2ts` is never opened. `~/workspace/projects/vtt` is never read.
- **No box path in a committed file.** `grep -rn "/mnt/\|/home/"` over every committed file must hit only the record's §2 pin table, which sanctions it in its own sentence; the assembler redacts with `PATH=LABEL` pairs as rung 3's did.
- **Pre-registration is committed alone and before any code** (Task 0) and byte-locked by `tests/test_acceptance_s5_rung4_lock.py`: the commit that carries the record's §1 changes nothing under `src/`, `typescript/src/`, `rust/` or `corpus/`. After a number is read no threshold moves, no arm is added, nothing is re-run. An instrument defect found before a number is read is fixed and written into the record's §2.3 with its commit; found after, it is a finding.
- **Verdict words come from the rule** (spec §8, §13): per endpoint `PASS` / `STOP` / `reported` exactly as its rule reads; the rung's word is `DONE` or `DONE-WITH-STOP`.
- **Legacy output is byte-identical:** every Python and Rust corpus case, every existing vector, the Python and Rust `watch`/`flow`/`frame`/`tree` outputs, `rust/`, the Rust `dbg` reader (`rust_debug.py`) — zero diff. The existing 32 TypeScript cases may move ONLY in the declaration block and in a `sensorium-ts 0.2.0` → `0.3.0` token; the collector names every moved line.
- **Wire stays 1, trace format 4.** `sensorium-ts` becomes **0.3.0** at Task 2 (every token: `typescript/package.json`, `package-lock.json` lines 3 and 9, `src/index.mjs`, `typescript/test/rt.test.mjs:67`, `src/sensorium/ts/wrapper.py:57`, `tests/test_ts_wrapper.py:84`, `tests/test_ts_live.py:200`, `tests/ts_traces.py:46`, vectors v30–v34's `recorder`, `corpus/typescript/{object_refused,pass_vs_fail,silent_swallow,watch_refused}/questions.yaml`). Python becomes **0.12.0** at Task 10 (`tests/test_release_tokens.py` binds `pyproject` to the CHANGELOG's newest header, so the CHANGELOG entry lands in the bump commit).
- **Ceilings** (`tests/test_ceiling.py`, 800; `docs/superpowers/{acceptance,plans,specs}/` exempt): `CHANGELOG.md` 800 → cut at Task 1 BEFORE anything else; `typescript/HONESTY.md` 799 → §9 moves at Task 1; `typescript/src/transform.mjs` 765 → the task-boundary code moves to `tasks.mjs` at Task 1 and the focus splices live in a NEW `probe.mjs`; `rt.mjs` 705 (+≈45); `flow_cmd.py` 742 (+≈30; if it would cross, the serial branch goes to `flow_values.py`); `tests/test_ts_ingest_meta.py` 777 → converter tests go to a NEW `tests/test_ts_ingest_focus.py`; `docs/TRACE-FORMAT.md` 781 → three sentences, nothing more; `docs/CARRIED-DEBT.md` 530, append.
- **Tests:** TDD per task; every new Python predicate and every new JS analysis mutation-checked (break the line the test pins, the test must FAIL, restore) under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged, mutant runs under `setsid` and killed by process group on timeout, the failing tests named in the task report. Never `npx tsc -p` from the root: `npm --prefix typescript run check`. Node tests: `npm --prefix typescript test`. The global `sensorium` tool is never reinstalled from this worktree; the branch's binary is `.venv/bin/sensorium`. `tests/test_ts_live.py` is gated on `SENSORIUM_TS_LIVE=1` and is run at Tasks 4, 6 and 8.
- **Commits:** conventional prefixes; the session's trailer lines. Branch `feat/s5-rung4` off `main` at `aea6b47`, worktree `/mnt/extra/sensorium-rung2/s5-rung4`, venv `.venv` 3.13 (editable, `[dev]`), `node_modules` installed in `typescript/`, `typescript/probes/`, `corpus/typescript/`.
- **Gotchas carried:** `pkill -f`/`pgrep -f` self-match; helper scripts scrub `SENSORIUM_MANIFEST_DIR`, `SENSORIUM_SPOOL` and now `SENSORIUM_FOCUS`; the corpus runner's `expect_line` is a substring match, so a collector compares whole printed lines itself; `test_ceiling.py` enumerates `git ls-files`, so suite counts move when files become tracked; never wrap a command in `timeout` on this box; vitest's `vi.mock` factories are never instrumented; a `magic-string` `prependRight` registered EARLIER renders to the RIGHT of one registered later at the same offset (the transform's whole closer discipline rests on it).

---

## File structure

| file | responsibility |
|---|---|
| `typescript/src/tasks.mjs` (new, Task 1) | the test-file rule and the task/suite boundary splice, moved whole out of `transform.mjs` |
| `typescript/src/bindings.mjs` (new) | pure: `boundNames`, `writesOf`, `headBindingsOf`, `headDeclaredOf`, `declaredIn`, `isStatementPosition`, `paramNames` |
| `typescript/src/focus.mjs` (new) | pure: `SEP`, `specsFromEnv`, `parseSpec`, `qualnameMatches`, `fileMatches`, `specMatches`, `closest` |
| `typescript/src/probe.mjs` (new) | the focus splices: `spliceFocused(ctx, node)` — statement probes, guard bodies, head rows |
| `typescript/src/transform.mjs` | `planSites` marks focused sites; `Splicer` gains `focused: Set<Node>`; `spliceFunction` emits the args array; exports `sitesOf` for the resolver; manifest `focused` |
| `typescript/src/resolve.mjs` (new) | the CLI the driver runs before the harness: root + specs in, JSON out |
| `typescript/src/rt.mjs`, `dbg.mjs` | `line`, `call`'s args array, `captures`; `oid`/`type` on object captures; `CAPABILITIES` from `SENSORIUM_FOCUS` |
| `typescript/src/vite.mjs`, `hook.mjs`, `tally.mjs` | `focus` from the environment into `transformSource`; `functions_focused` in the tally |
| `typescript/probes/src/focus.probe.test.ts`, `probes/check.mjs`, `probes/vitest.config.ts` | the probe, `checkFocus`, the DIRECT-mode focus list |
| `src/sensorium/ts/focus.py` (new) | `Resolution`, `resolve(root, package, specs)`, `refusals(res, root)`, `SEP` |
| `src/sensorium/ts/cli.py`, `driver.py`, `invocation.py`, `build.py` | `--focus`; the resolver call before the mint; `SENSORIUM_FOCUS`; `Invocation.focus`/`focus_matched`; `_on_line`, `args`, `root`, `focus`, `focus_matched` in meta |
| `src/sensorium/query/js_inspect.py` (new) | `read_inspect`, `inspect_text`, `js_number` |
| `src/sensorium/query/dbg_dialects.py` (new) | `Dialect`, `RUST`, `INSPECT`, `for_trace` |
| `src/sensorium/query/sites.py` (new) | `spell_site`, `site_matches`, `rerun_command` |
| `src/sensorium/query/expr.py`, `vocab.py`, `watch_cmd.py`, `flow_cmd.py`, `flow_values.py` | constants + `resolve(v, dialect)`; five fields per column; the dialect threaded; the serial basis |
| `typescript/test/{bindings,focus,probe,resolve}.test.mjs`, `test/golden/focus-*.ts`, `test/fixtures/{inspect-table.json,site-spellings.json,gen-inspect-table.mjs}` | the JS tests and the two shared fixtures |
| `tests/test_js_inspect.py`, `tests/test_ts_ingest_focus.py`, `tests/test_ts_driver_focus.py`, `tests/test_watch_typescript.py`, `tests/test_flow_serial.py`, `tests/fixtures/ts-spools/focus-lines/` | the Python tests and the recorded fixture |
| `docs/trace-format/vectors/v35–v39-*.json` + `VECTORS.md` rows | the contract's pins |
| `corpus/typescript/{focus_let_chain,…,flow_value_inspect,object_identity}/`, `corpus/cases.py`, `corpus/run_corpus.py` | the ten cases, the re-pins, the `record: {focus}` key |
| `typescript/acceptance/{e12.sh,e12_report.py,e12_h3.py,e12_cost.py,e12_h8.sh,assemble_rung4.py}`, `e_fences.py`, `e7_report.py` | the instruments |
| `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md` (+ `-handcount.md`, `-tracehashes.txt`, `.results.json`) | the record |
| `tests/test_acceptance_s5_rung4_lock.py` | the byte lock |
| `~/.claude/skills/debugging-typescript-with-sensorium/SKILL.md` (outside the repo) | the third sibling skill |

## Decisions this plan makes (each amends the spec non-silently in Task 10's §15)

| # | decision | why |
|---|---|---|
| P1 | **A guarded statement's own completion row carries its head's assignment targets as deltas** (declarations excluded — those are `unbound`). `while ((m = re.exec(s)) !== null)` reports `m` on each iteration's head row AND `m = null` on the while's row; `if ((x = f())) …` reports `x` on the if's row whichever branch ran. | Spec §3.2's per-entry rule alone leaves the guard's LAST write unreported: `m` is `null` after the loop and the fold would keep the last array. This closes that and the falsy-`if`-head blind spot the spec declared (§3.9's "a falsy `if` head's" is struck at Task 10). N does not change. |
| P2 | **A non-block body of a guard (`if (c) x = 1;`, `for (…) stmt;`, `else stmt;`) is wrapped in a block** `{…}` whenever the function is focused, so the body's probe and the head row sit inside the guard. | Appended after a bare body, a probe would run unconditionally — Rust's A1, transferred. |
| P3 | **The statement probe is registered with `prependRight(stmt.end, …)` BEFORE the statement's children are visited**, and carries `terminatorFor`'s `;` when the statement has none. | A descendant closer at the same offset (`await x` as a whole statement: the suspension's `),0))`) must render INSIDE the probe; magic-string renders earlier-registered `prependRight` content rightmost. |
| P4 | **`writesOf` excludes anything inside a nested function-like or class member body**; `declaredIn` lists a block's DIRECT `let`/`const`/`class`/function declarations, the catch binding and the loop head's declarations, never a nested block's (that block's own row lists those). | Rust §3.3 for closures; one row owns each name's death. |
| P5 | **The driver's refusal keeps the driver's one shape** — `error: --focus <spec> matches no function under <root>; nothing was run. Closest: a, b, c` on stderr, exit 2, one line per bad spec — not spec §2.2's `REFUSED:` prefix. | Every refusal `sensorium ts run` makes before spawning goes through `_refuse`; two shapes for one status would be the fault D8 exists to prevent. |
| P6 | **The probe project sets `process.env.SENSORIUM_FOCUS` in `vitest.config.ts`'s DIRECT branch** from a `FOCUS` list beside the plugin call; `checkFocus` asserts BOOT declares `line: true`. If a forked worker does not inherit it, the `probe` script exports it instead — either way the checker decides. | The plugin and the runtime read one variable (§2.3); the probes have no driver. |
| P7 | **`inspect_text` returns `None` for a string past 100 characters** (inspect's `maxStringLength`), so `flow --value` sights nothing; `read_inspect` reads the `'…'... N more characters` tail as TRUNCATED. | Spec §4.1 said the writer spells the tail and "therefore matches nothing" — but a capture under the 200-byte cap carries `trunc: false` and its text WOULD equal the spelled tail. A clipped rendering equals nothing, on both sides. |
| P8 | **`site_spelling` is `"module"` for Python AND Rust, `"rel"` for TypeScript**; `--at` accepts basename and root-relative path for every language (additive). | Rust's printed listing today is `module_name_for`'s dotted spelling and is quoted in a closed record; spec §4.3's "stem for Rust" would move it. |
| P9 | **TypeScript meta gains `root`** (the invocation's root, from `invocation.json`), a new TYPESCRIPT-KEYS row. | `rel:qualname` needs the root; nothing else in meta carries it. |
| P10 | **`resolve(v, dialect=None)` and `matches(cap, target, write=debug_text)` keep their old behaviour when the argument is absent**; only `watch_cmd` and `flow_cmd` pass a dialect. | Every existing caller and test keeps its call; a Python trace never carries a `dbg` capture. |
| P11 | **The predicate constants are excluded from `Expr.names`** so `watch` never reports `null` as NEVER RECORDED. | A constant is not a name the trace could witness. |
| P12 | **The `oid` counter and the exception `serial` counter are separate maps and separate counters.** | Two namespaces (`flow --object` vs `exceptions`); sharing them would let a thrown object's `serial` read as an identity in the other command. |
| P13 | **H1–H6 read the FIRST U run and the FIRST F run; H7's arms are three U and three F runs interleaved (U1 F1 U2 F2 U3 F3), all six into the store**, so the measured traces are cost-arm members and nothing is recorded twice for two purposes. | One recording per purpose would double the lens's wall for no extra fact. |
| P14 | **The recorded converter fixture `focus-lines` is cut from the focus probe's own spool**, sanitised by `tests/fixtures/ts-spools/sanitize.py`, with a hand-written `invocation.json` carrying `focus`/`focus_matched`. | The converter's tests must read a spool the RUNTIME wrote (rung 1's rule), and the probe is the one focused program that exists before the corpus does. |

## Pre-registration (Task 0 commits spec §8's table verbatim as the record's §1, plus this block)

- **The lens and the store:** the VTT frontend copy at `0091e97` (`LENS.txt`), manifest-checked before and after every session; a fresh store `<store>` (`SENSORIUM_DIR`), empty at T0, hashed at T9 — every `traces/*.db`, every `spool/<invocation>/*.jsonl`, AND `invocations.jsonl`, listed in `…-s5-rung4-tracehashes.txt` after the arms and before any read; the journal's pre-registered delta is exactly one line per read command in §1.5's list, checked by the assembler after the reads.
- **The subject:** `src/lib/diceQueue.test.ts`; U = `sensorium ts run -- npx vitest run src/lib/diceQueue.test.ts`; F = the same with `--focus diceQueue.ts:parseDiceGroups --focus diceQueue.ts:forcedDiceFromSource --focus diceQueue.ts:buildDiceQueueEntry`. Three U and three F runs, interleaved U1 F1 U2 F2 U3 F3 under the load guard (`e6pp.sh`'s: 1-minute load under 4.0, up to 90 tries 20 s apart); H1–H6 read U1 and F1 (plan P13).
- **§1.1, the hand count for H3:** the first activation of `parseDiceGroups` in F1 is `parseDiceGroups('1d20')` (the first `it` of the file's first `describe`; vitest runs a file's tests in order). Counted under spec §3.1–3.4 and plan P1: one row per completed statement at every depth, a head row per iteration whose guard binds or assigns, the while's own row after the loop, no row for `return`, the CALL carrying `args` instead of a parameters row. The table lists every row with its source line, its `deltas` names and its `unbound` names; **N is the gate**; the file's lines are read at T0 from the copy (function at line 68), never from this plan.
- **§1.2, three `watch` triples for H4** on F1, `--at parseDiceGroups`: W1 `sides == 20` → **SATISFIED, exit 0**; W2 `count == 1` → **SATISFIED, exit 0, and no HIT row at the `while` statement's line** (the `unbound` reading: `count` dies on that row); W3 `m == null` → **SATISFIED, exit 0** (plan P1: the while's row carries `m`'s last write). Hits and the not-captured tally are reported, not predicted.
- **§1.3, two `flow --value` sightings for H5** on F1 among the three functions' LINE deltas: `flow --value 20` sights `sides` at the `const sides` row of the `'1d20'` activation; `flow --value "'1d20'"` sights `formula` as `arg formula` on that activation's CALL. Both found → PASS; every other sighting reported.
- **§1.4, the identity for H6:** `e<id>` = the first LINE row of `forcedDiceFromSource` carrying `dice` in F1, found by `grep F1 dice --kind LINE` (a lookup, not a number); `flow --object e<id>:dice` → exactly two sightings, that row and `buildDiceQueueEntry`'s `const { dice, skippedCount }` row, one serial, both `type` `Array`, `continuity: exact (serial identity)`.
- **§1.5, the read commands** (the journal's expected delta): `info` ×2, `watch` ×3, `flow` ×3, `grep` ×2, `frame` ×1, `tree` ×1 — twelve lines; listed verbatim in §1.5 with their arguments.
- **H1:** U1 `capabilities.line = false`, `locals = false`; LINE rows 0 (a `SELECT count(*) FROM events WHERE kind='LINE'`); `watch U1 --at parseDiceGroups --expr groups == 0` prints `REFUSED: watch needs line, which recorder sensorium-ts 0.3.0 declares it does not produce (capabilities.line: false); nothing was checked`, exit 3.
- **H2:** the resolver names exactly `src/lib/diceQueue.ts:parseDiceGroups`, `…:forcedDiceFromSource`, `…:buildDiceQueueEntry`; F1's `Test Files`/`Tests` lines equal U1's; `grep F1 parseDiceGroups --kind CALL` prints `parseDiceGroups(formula='1d20')` first. A focused file that fails to load, or a moved count, is a STOP.
- **H7:** medians of the three U and three F walls; the resolver's wall from `e12.sh`'s own timing of `node resolve.mjs`; reported.
- **H8:** `python corpus/run_corpus.py --require-driver` every case equal; `.venv/bin/python -m pytest -q`; `cargo test --workspace`; `npm --prefix typescript test`; `npm --prefix typescript/probes run probe`; `e7_report.py` with `E7_NEEDLES=rung2` at 0 over every transcript of §1.5's reads.
- **Versions:** sensorium-ts 0.3.0, Python 0.12.0, wire 1, trace format 4.

---

### Task 0: The record's §1, the hand count, the triples, the lock

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-11-sensorium-s5-rung4-focus.md`, `…-s5-rung4-handcount.md`, `tests/test_acceptance_s5_rung4_lock.py`
- Read only: `/mnt/extra/sensorium-s5/vtt/frontend/src/lib/diceQueue.ts` (lines 68–82, 127–156, 194–212) and `diceQueue.test.ts`

**Interfaces:** Produces the record whose §1 Task 9 fills against; the hand-count table (`| row | line | statement | deltas | unbound |`) `e12_h3.py` parses; the twelve read commands `e12_report.py` runs verbatim.

- [ ] **Step 1: The hand count.** Open `diceQueue.ts` at line 68 in the copy. Write `…-handcount.md`: one row per LINE row of `parseDiceGroups('1d20')`, in execution order, with source line, statement text, `deltas` names, `unbound` names, and the rule that mints it (§3.1 statement / §3.2 head row / plan P1 completion deltas / §3.4 unbound). The while head assigns `m`; `GROUP_RE.exec('1d20')` matches once, then returns `null`; the `if` guard is true. State the total `N = <count>` as the table's last line and the count of rows carrying `unbound`. Beside it, the same table for the `'1d20'` activation's CALL (`args: formula`) — not a row, stated for H2's third reading.
- [ ] **Step 2: The record.** §1 = spec §8 verbatim (its `##` carried as `###`) + this plan's Pre-registration block verbatim (up to `### Task 0`), then §1.1–§1.5 as the block names them, sources at their commits (`aea6b47` for the spec; this plan's commit). §1's last line is the hand-count file's sha256. §2 pins: `LENS.txt`'s line; the store label; `wc -l` of every ceiling-relevant file (`transform.mjs` 765, `rt.mjs` 705, `flow_cmd.py` 742, `CHANGELOG.md` 800, `HONESTY.md` 799, `TRACE-FORMAT.md` 781, `test_ts_ingest_meta.py` 777); the version tokens (0.2.0 → 0.3.0 list from Global Constraints); the E7 needle list `rung2`. §3–§5 stubs reading `not measured (rung 4 pending)`. Commit: `docs(acceptance): S5 rung 4 record — pre-registration, hand count`. This commit touches nothing outside `docs/superpowers/acceptance/`.
- [ ] **Step 3: The lock test**, modelled line for line on `tests/test_acceptance_s5_rung3_lock.py`: `DOC`, `HANDCOUNT_REL`, `BYTE_LOCK = "<sha of Step 2>"`, `ORIGINAL_LOCK = None`, `_SPEC = "docs/superpowers/specs/2026-09-11-sensorium-s5-rung4-focus-tier-design.md"` and the plan path; the locked range `## 1.`–`## 2.`; verbatim checks of spec `## 8.` (`git show aea6b47:<spec>`) and of this plan's `## Pre-registration (…)` block; every endpoint id H1–H8 inside the range; §1's last line equals the hand-count file's sha256; a one-byte mutation refused; a hand-count table with the five columns. Run: `.venv/bin/python -m pytest -q tests/test_acceptance_s5_rung4_lock.py` → green. Commit: `test(acceptance): byte-lock the rung-4 pre-registration`.

---

### Task 1: Ceilings and the rung-3 debts

**Files:**
- Modify: `CHANGELOG.md`, `CHANGELOG-ARCHIVE.md`; `typescript/HONESTY.md`; create `typescript/HONESTY-COST.md`; `typescript/src/transform.mjs`; create `typescript/src/tasks.mjs`; `typescript/acceptance/e7_report.py:118-124`, `e_fences.py`; `src/sensorium/query/exceptions_group.py:265-290, 400-405`; `tests/test_exceptions_rust_grouping.py:696`
- Test: `tests/test_ceiling.py`, `typescript/test/transform.test.mjs` (goldens unchanged), `tests/test_acceptance_scripts.py`, `tests/test_exceptions_rust_grouping.py`

**Interfaces:** Produces `tasks.mjs` exporting `isTestFile(ts, sf, filePath)`, `spliceTaskBoundary(ctx, node)`; `e7_report.py` writing `<transcript>.rules`; `Shape(site=…)` required; `e_fences.py` refusing an empty pattern.

- [ ] **Step 1: CHANGELOG cut.** Move the `## 0.8.6` and `## 0.8.5` sections (lines 582–800) whole into `CHANGELOG-ARCHIVE.md` ABOVE `## 0.8.4`, with a dated preamble paragraph in the archive's own voice (the fourth cut; the file stood at 800, two entries moved so the next slice inherits room; entries byte for byte). `CHANGELOG.md` → 581 lines. Run `tests/test_ceiling.py` and `tests/test_release_tokens.py` → green. Commit: `docs(changelog): cut 0.8.6 and 0.8.5 to the archive before the rung-4 entry`.
- [ ] **Step 2: HONESTY §9 → `HONESTY-COST.md`.** Move lines 600–739 (`## 9. Cost` through the line before `## 10.`) into the new file with a header in the blind-spots file's voice; leave a `## 9. Cost` pointer paragraph (≤ 8 lines) in place; the index's three `| 9 |` rows stay. Commit: `docs(honesty): §9 Cost moves to HONESTY-COST.md for the rung-4 promises`.
- [ ] **Step 3: `transform.mjs` → `tasks.mjs`.** Move `TEST_FILE`, `HARNESS_MODULES`, `TASK_CALLEES`, `SUITE_CALLEES`, `isTypeOnlyImport`, `isTestFile`, `calleeChain`, `isLiteralTitle`, `spliceTaskBoundary` (lines 32–39, 172–257, 569–595) verbatim into `typescript/src/tasks.mjs`; `transform.mjs` imports the two it calls; `lineOf` stays in `transform.mjs` and is exported for `tasks.mjs`/`probe.mjs`. `npm --prefix typescript test` → every golden unchanged; `run check` clean. Commit: `refactor(transform): the test-file rule and the task boundary move to tasks.mjs`.
- [ ] **Step 4: The three debts.** (a) `e7_report.py`: `Path(str(transcript_path) + ".rules").write_text(rule_header)`; the transcript is never written; `tests/test_acceptance_scripts.py` gains `test_e7_report_never_rewrites_its_transcript` (run it twice over a temp transcript, bytes equal). (b) `Shape.site: tuple` required (no default), `__post_init__`'s `key[1]` fallback deleted; the test fixture at `test_exceptions_rust_grouping.py:696` passes `site=site`. (c) `e_fences.py`: `FENCED`/`FENCED_TESTS` name `tests/test_exceptions.py` and `tests/test_exceptions_synthetic.py` in place of the phantom pattern; `existing()` raises `SystemExit(2)` naming any pattern that matches no file; `PYTHON_READER_TESTS` and its "reported, not gated" branch are removed. Run the four test files → green. Commit: `fix(acceptance): the rung-3 debts — e7's sibling header, Shape.site required, real fence files`.

---

### Task 2: The runtime and the wire — `line`, the args array, identity, the declaration; version 0.3.0

**Files:**
- Modify: `typescript/src/rt.mjs`, `typescript/src/dbg.mjs`, `typescript/src/index.mjs`, `typescript/package.json`, `package-lock.json`, every token file in Global Constraints, `tests/ts_traces.py` (`TS_CAPABILITIES` gains `object_identity: True`; recorder `0.3.0`)
- Test: `typescript/test/rt.test.mjs` (or a new `rt.focus.test.mjs` if it would cross 780)

**Interfaces (verbatim):**
```js
// dbg.mjs — Captured gains two optional keys for object and function values
/** @typedef {{k: 'dbg', v: string, trunc: boolean, oid?: number, type?: string}|{k: 'unread'}} Captured */
/** @type {WeakMap<object, number>} */
const oids = new WeakMap();
let nextOid = 1;
/** @param {object} o @returns {number} minted once per object, never reused */
function oidOf(o) {
  let id = oids.get(o);
  if (id === undefined) { id = nextOid++; oids.set(o, id); }
  return id;
}
export function dbg(v) {
  if (v === undefined) return { k: 'dbg', v: 'undefined', trunc: false };
  let text;
  try { text = util.inspect(v, INSPECT); } catch { return { k: 'unread' }; }
  const { v: text_, trunc } = cap(text);
  /** @type {Captured} */
  const out = { k: 'dbg', v: text_, trunc };
  const t = typeof v;
  if (v !== null && (t === 'object' || t === 'function')) { out.oid = oidOf(v); out.type = typeOf(v); }
  return out;
}

// rt.mjs
const FOCUS = process.env.SENSORIUM_FOCUS ?? '';
const CAPABILITIES = FOCUS === ''
  ? { err_flow: true, object_identity: true }
  : { err_flow: true, object_identity: true, line: true, locals: true };

/** @param {unknown[]} pairs `[name, value, name, value, …]` @returns {Record<string, Captured>} */
function captures(pairs) {
  /** @type {Record<string, Captured>} */
  const out = {};
  for (let i = 0; i + 1 < pairs.length; i += 2) out[/** @type {string} */ (pairs[i])] = dbg(pairs[i + 1]);
  return out;
}
export function call(fileId, c, args) {   // `args` present only on a focused site
  if (!on) return null;
  … as today …
  /** @type {Record_} */
  const rec = { e: 'CALL', f: f.id, p: parent ? parent.id : null, file: fileId, c, t: t ? t.id : null };
  if (args !== undefined) rec.a = captures(args);
  emitTs(rec);
  return f;
}
/** One completed statement of a focused function. */
export function line(f, l, pairs, unbound) {
  if (!on || !f || !f.open) return;
  /** @type {Record_} */
  const rec = { e: 'LINE', f: f.id, t: taskId(f), l, d: captures(pairs) };
  if (unbound !== undefined && unbound.length > 0) rec.u = unbound;
  emitTs(rec);
}
```
The wire (`KEYS` in `rt.test.mjs`): `LINE: ['e', 'f', 't', 'l', 'd', 'ts']`, `OPTIONAL.LINE = ['u']`, `OPTIONAL.CALL = ['a']`.

- [ ] **Step 1: Failing tests (RED).** `line` writes `{e:'LINE', f, t, l, d, ts}` with `d` capturing each pair and `u` only when non-empty; `line` is inert at tier `off`, with `f` null, and after `ret` closed the frame; a LINE inside a frame that parked and resumed carries that frame's id; `call(file, 0, ['a', 1])` writes `a: {a: {k:'dbg', v:'1', trunc:false}}` and `call(file, 0)` writes no `a`; two captures of one object carry one `oid`, two objects two, a primitive none, `type` is the constructor name and `unread` for an object whose `constructor` getter throws; BOOT declares `{err_flow: true, object_identity: true}` with no focus and adds `line: true, locals: true` when the child is spawned with `SENSORIUM_FOCUS='x'`; `VERSION` is `'0.3.0'`. Run `npm --prefix typescript test` → the new tests FAIL.
- [ ] **Step 2: Implement** as above; bump every 0.2.0 token in Global Constraints (vectors and corpus questions included — the corpus is re-collected at Task 8, so only the token moves here); `tests/ts_traces.py` `TS_META["recorder"] = "sensorium-ts 0.3.0"`, `TS_CAPABILITIES["object_identity"] = True`. Run the Node tests, `run check`, and `.venv/bin/python -m pytest -q tests/test_ts_wrapper.py tests/test_vectors.py tests/test_exceptions_typescript*.py tests/test_vocab.py` → green (the Python suite's TS refusal sentences now read 0.3.0).
- [ ] **Step 3: Commit** `feat(rt): LINE records, the focused CALL's arguments, serial identity on captures; sensorium-ts 0.3.0`.

---

### Task 3: `bindings.mjs` and `focus.mjs` — the two pure analyses

**Files:**
- Create: `typescript/src/bindings.mjs`, `typescript/src/focus.mjs`, `typescript/test/bindings.test.mjs`, `typescript/test/focus.test.mjs`, `typescript/test/fixtures/site-spellings.json`

**Interfaces (verbatim signatures; JSDoc-typed against the consumer's `typescript`):**
```js
// bindings.mjs — no state; every function takes `ts` and a node
export function boundNames(ts, name)            // Identifier | BindingPattern → string[] (nested patterns, defaults, rest; `_`-prefixed included)
export function isStatementPosition(ts, node)   // parent is Block/CaseClause/DefaultClause, or node is a guard's then/else/statement
export function writesOf(ts, statement)         // string[] in source order, deduped — see the table
export function headBindingsOf(ts, statement)   // names the guard binds or assigns → the per-entry row
export function headDeclaredOf(ts, statement)   // the subset of headBindingsOf that are DECLARATIONS (let/const in a for head, a catch binding)
export function declaredIn(ts, statement)       // block-scoped names its DIRECT blocks declare + headDeclaredOf → `unbound`
export function paramNames(ts, fn)              // boundNames of every parameter, a `this` parameter skipped

// focus.mjs
export const SEP = '\x1f';                    // the unit separator, written as an escape so no editor strips it
export function specsFromEnv(value)             // '' → []; split on SEP, empties dropped
export function parseSpec(spec)                 // {file: string|null, qualname: string}; split at the FIRST ':'
export function qualnameMatches(qualname, want) // equal, or startsWith(want + '.')
export function fileMatches(rel, want)          // rel === want, or basename(rel) === want, or stem(basename) === want (stem strips the last extension)
export function specMatches(spec, rel, qualname)
export function closest(eligible, want, limit = 3)  // by shared trailing '.'-segments desc, then name asc; [] when eligible is empty
```
**`writesOf`'s table** (the statement's own expressions; a nested function-like, class member or arrow body is NEVER walked): `VariableStatement` → `boundNames` of every declaration plus assignment targets inside initialisers; `ExpressionStatement` → assignment targets in it; `ClassDeclaration` → its name; `IfStatement`/`WhileStatement`/`DoStatement`/`SwitchStatement` → targets in `expression`; `ForStatement` → targets in `initializer` (when an expression), `condition`, `incrementor`; `ForInStatement`/`ForOfStatement` → targets in `initializer` (when an expression) and in `expression`; `TryStatement`, `LabeledStatement`, `Block`, `FunctionDeclaration`, `EmptyStatement` → `[]`; then MINUS `headDeclaredOf(statement)` (plan P1). An **assignment target** is: the left of a `BinaryExpression` whose operator token is any `ts.SyntaxKind.*EqualsToken` (`=`, `+=`, `-=`, `*=`, `/=`, `%=`, `**=`, `<<=`, `>>=`, `>>>=`, `&=`, `|=`, `^=`, `&&=`, `||=`, `??=`) when it is an `Identifier`; the identifiers inside an `ArrayLiteralExpression`/`ObjectLiteralExpression` target (elements, `PropertyAssignment.initializer`, `ShorthandPropertyAssignment.name`, `SpreadAssignment`/`SpreadElement` expressions, a `BinaryExpression` default's left); the operand of a `++`/`--` prefix or postfix unary when it is an `Identifier`. A `PropertyAccessExpression`/`ElementAccessExpression` target contributes nothing.
**`headBindingsOf`:** `ForOf`/`ForIn` → `boundNames` of the initializer's declaration, or the assignment targets of the initializer expression; `For` → the same over `initializer`; `While`/`Do`/`If` → assignment targets in `expression`; `CatchClause` → `boundNames(variableDeclaration.name)`; `Switch` → `[]`.
**`declaredIn`:** for each DIRECT block of the statement (`thenStatement`/`elseStatement` when a Block, a loop's `statement` when a Block, `tryBlock`, `catchClause.block`, `finallyBlock`, every `CaseClause`/`DefaultClause`'s statements, a `LabeledStatement`'s statement delegated, a bare `Block` itself): the names of its direct `VariableStatement`s whose `declarationList.flags & (ts.NodeFlags.Let | ts.NodeFlags.Const)`, direct `ClassDeclaration` and `FunctionDeclaration` names; plus `headDeclaredOf(statement)`.

- [ ] **Step 1: Failing tests (RED)** in `bindings.test.mjs` on the `escape.test.mjs` pattern (parse a fragment, find the statement, ask): one test per row of spec §3.2's table and of the three lists above, including `let x;` → `['x']`, `const {a, b: [c] = [0], ...r} = o` → `['a','c','r']`, `a.b = 1` → `[]`, `x ||= 1` → `['x']`, `[a, b] = [b, a]` → `['a','b']`, `arr[i++] = 0` → `['i']`, `xs.map(y => (z = 1))` → `[]`, `for (let i = 0; i < n; i++) {}` → `writesOf` `[]` / `headBindingsOf` `['i']` / `declaredIn` `['i']`, `while ((m = re.exec(s)) !== null) { const c = 1 }` → `writesOf` `['m']` / `headBindingsOf` `['m']` / `declaredIn` `['c']`, `if ((x = f())) {}` → `writesOf` `['x']`, `try { const a = 1 } catch (e) { const b = 2 } finally { const c = 3 }` → `declaredIn` `['a','e','b','c']`, `if (c) { const y = 1; if (d) { const z = 2 } }` → `declaredIn` `['y']`, `switch (k) { case 1: { const q = 1 } }` → `declaredIn` `[]` (the inner bare block owns `q`), `isStatementPosition` true for a then-statement and false for a `return`'s expression. `focus.test.mjs`: the spelling fixture (below), `parseSpec('src/a.ts:Fog.run')`, `closest(['m.f','S.k','h'], 'wrong.f')` → `['m.f','S.k','h']` (Rust's own case), `closest([], 'x')` → `[]`, `specsFromEnv('')` → `[]`.
- [ ] **Step 2: The spelling fixture** `typescript/test/fixtures/site-spellings.json`: `{"rel": "src/lib/cache.ts", "qualname": "Fog.compute", "matching": ["Fog.compute", "Fog", "cache:Fog.compute", "cache.ts:Fog", "src/lib/cache.ts:Fog.compute"], "not_matching": ["Fogs", "compute", "lib:Fog", "src/cache.ts:Fog", "Fog.compute.x"]}` — read by `focus.test.mjs` here and by vector v39 / `tests/test_watch_typescript.py` at Task 7 (one table, two implementations).
- [ ] **Step 3: Implement; GREEN; mutation-check** each list (swap `Let|Const` for `Let`, drop the `++` arm, drop the nested-function stop): the named test must fail. `run check` clean. Commit: `feat(transform): bindings.mjs and focus.mjs — the names a statement writes, the names a spec selects`.

---

### Task 4: The transform under a focus — splices, goldens, the plugin and the hook, the probe

**Files:**
- Create: `typescript/src/probe.mjs`, `typescript/test/probe.test.mjs`, goldens `typescript/test/golden/focus-{let-chain,loop,block-scope,guard-bare-body,async,catch,destructure,nested,unfocused-sibling}.ts` + `.expected.ts`, `typescript/probes/src/focus.probe.test.ts`
- Modify: `typescript/src/transform.mjs` (`planSites`, `Splicer`, `splice`, `spliceFunction`, `transformSource`, new export `sitesOf`), `vite.mjs`, `hook.mjs`, `tally.mjs`, `typescript/probes/check.mjs`, `probes/vitest.config.ts`, `probes/README.md`, `typescript/test/transform.test.mjs` (the golden runner passes `focus` when a golden's first line is `// focus: <spec>[,<spec>]`)

**Interfaces (verbatim):**
```js
// transform.mjs
/** @typedef {{qualname: string, line: number, kind: FrameKind, focused: boolean}} Site */
/** @typedef {{file, rel, sha256, instrumented: Site[], focused: string[], excluded, diagnostics?}} Manifest */
export function transformSource(code, filePath, opts)   // opts gains `focus?: string[]` (default [])
export function sitesOf(code, filePath, opts)           // {rel, sites: Site[], excluded} | null — pass one only, no splice; the resolver's entry
// Splicer gains `focused: Set<Node>` (function-likes whose site is focused)
// splice()'s visitor, AFTER the existing else-if chain and before forEachChild:
//   if (isFocusedFrame(ctx, node)) spliceFocused(ctx, node);
// spliceFunction: `const __sf=__srt.call(__sfile,${index}${argsList})` where
//   argsList = focused ? `,[${paramNames(ts, node).flatMap((n) => [JSON.stringify(n), n]).join(',')}]` : ''

// probe.mjs
export function spliceFocused(ctx, node)   // dispatches: statement position → spliceStatement; guard → spliceGuard; catch clause → head row
```
**`spliceStatement(ctx, node)`** (a node in statement position that is not `return`/`throw`/`break`/`continue`/`FunctionDeclaration`/`EmptyStatement`):
```js
const line = lineOf(ctx.sf, node.getStart(ctx.sf));
const pairs = writesOf(ts, node).flatMap((n) => [JSON.stringify(n), n]).join(',');
const gone = declaredIn(ts, node);
const tail = gone.length > 0 ? `,${JSON.stringify(gone)}` : '';
ctx.s.prependRight(node.end, `${terminatorFor(ctx, node)}__srt.line(__sf,${line},[${pairs}]${tail});`);
```
registered BEFORE `forEachChild` (plan P3). **`spliceGuard(ctx, node)`** for `If`/`For`/`ForIn`/`ForOf`/`While`/`Do`/`Labeled`: `heads = headBindingsOf(ts, node)`; `headRow = heads.length ? \`__srt.line(__sf,${line},[${pairs(heads)}]);\` : ''`; for each body (`thenStatement`, `elseStatement`, `statement`): a `Block` → `appendLeft(block.getStart(sf) + 1, headRow)`; a non-block → `appendLeft(body.getStart(sf), '{' + headRow)` and `prependRight(body.end, '}')` registered before the body is visited (plan P2) — an `else if` body is an `IfStatement` and is wrapped like any other. A `CatchClause` with a binding → `appendLeft(block.getStart(sf) + 1, headRow)` AFTER `spliceCatch` registered its HANDLED (visit order in `splice`). A `SwitchStatement` gets no head row.
**Plugin and hook:** `const FOCUS = specsFromEnv(process.env.SENSORIUM_FOCUS ?? '')` read once at module load; `transformSource(code, file, { root, ts, rtPath, focus: FOCUS })`. **Tally:** `functions_focused += manifest.focused.length` on the first count of a file.

- [ ] **Step 1: Goldens (RED).** Each golden's first line `// focus: <spec>`; expected files hand-written from the splice forms above. `focus-let-chain.ts`: a function `fill()` with three `const`s and a return → three probes, the CALL `[]` args; `focus-loop.ts`: `for (const v of xs) { total += v }` → head row `["v",v]` after `{`, `total` probe, the for's row `[]` with `,["v"]`; `focus-block-scope.ts`: `if (c) { const y = 1; }` then a statement → the if's row `[],["y"]`; `focus-guard-bare-body.ts`: `if ((x = f())) x = 2;` → `if ((x = f())) {x = 2;__srt.line(…,["x",x]);}__srt.line(…,["x",x]);`, and `while ((m = re.exec(s)) !== null) count++;` → the head row inside a wrapping block, the while's row carrying `m`; `focus-async.ts`: `async function g() { const a = await p; const b = a + 1; }` → the probe after `const a = __srt.r(__sf,await __srt.y(__sf,(p),0));`; `focus-catch.ts`: `try { throw new Error('x') } catch (e) { count += 1 }` → HANDLED, then `__srt.line(__sf,L,["e",e]);`, the `count` probe, the try's row `[],["e"]`; `focus-destructure.ts`: `const { a, b: [c] = [0], ...r } = o; let x;` → `["a",a,"c",c,"r",r]` and `["x",x]`; `focus-nested.ts`: `function outer() { const f = (n) => { const m = n * 2; return m }; return f(1) }` under `// focus: outer` → both frames probed, the arrow's CALL carrying `["n",n]`; `focus-unfocused-sibling.ts`: two functions, one focused → the other's output byte-identical to today's. Every expected file parses under the consumer's TypeScript; line counts equal. Run → FAIL.
- [ ] **Step 2: Implement** `probe.mjs`, the `transform.mjs` changes, the plugin, the hook, the tally. GREEN. `probe.test.mjs` asserts what a golden cannot: a `return` inside a wrapped bare body mints no probe; a `ReturnStatement` in statement position mints none; a class declaration statement mints `["Foo",Foo]`; a `for (let i …)` completion row excludes `i` (plan P1 minus declared).
- [ ] **Step 3: The probe.** `typescript/probes/src/focus.probe.test.ts` (`// @vitest-environment node`): one exported function per §3.2 row — `letChain`, `loopCounter`, `blockScope`, `bareGuard`, `asyncRows`, `catchBinding`, `destructure`, `placeWrite`, `nestedArrow` — each called once by a `test`, each row's statement preceded by a marker `// LINE <fn> <name>=<inspect text>|- [unbound:<a,b>]` describing the LINE record on the NEXT line (`-` = empty deltas). `probes/vitest.config.ts` DIRECT branch: `const FOCUS = ['focus.probe.test.ts:letChain', …]; process.env.SENSORIUM_FOCUS = FOCUS.join('\x1f');` before `sensorium({…})` (plan P6). `check.mjs`: `VITEST_PROBES` gains the file; `checkFocus(k, s)`: `focus:caps` (BOOT `capabilities.line === true && locals === true`), `focus:args` (the CALL of `letChain` carries `a` with the marked argument), one `focus:<fn>:<line>` check per marker comparing `d[name].v` (or `Object.keys(d).length === 0` for `-`) and `u` (sorted) against the marker; `focus:count` = the marker count. README row. `SENSORIUM_TS_LIVE=1 .venv/bin/python -m pytest -q tests/test_ts_live.py` and `npm --prefix typescript/probes run probe` → every check passes.
- [ ] **Step 4: Commit** `feat(transform): the focus tier — LINE probes, head rows, unbound, the focused CALL's arguments; the probe`.

---

### Task 5: `resolve.mjs` and the driver

**Files:**
- Create: `typescript/src/resolve.mjs`, `typescript/test/resolve.test.mjs`, `src/sensorium/ts/focus.py`, `tests/test_ts_driver_focus.py`
- Modify: `src/sensorium/ts/cli.py` (`--focus`, `action="append"`, `default=[]`, `metavar="SPEC"`, help `"a function to record per statement: <qualname> or <file>:<qualname>, as tree prints it; repeatable"`), `driver.py`, `invocation.py`, `typescript/package.json` `exports` (`"./resolve"`)

**Interfaces (verbatim):**
```js
// resolve.mjs — `node resolve.mjs`; reads SENSORIUM_TS_ROOT, SENSORIUM_TS_PKG, SENSORIUM_FOCUS; prints one JSON line; exit 0 always
// (a missing variable or an unreadable root → one line on stderr, exit 2)
{"matched": [{"rel": "src/lib/cache.ts", "qualname": "refresh", "line": 12, "kind": "function"}],
 "unmatched": [{"spec": "refrsh", "closest": ["refresh", "refreshAll"]}],
 "excluded_only": [{"spec": "cache.ts:decl", "reasons": {"ambient": 1}}],
 "files_scanned": 42, "files_unparsable": 0}
```
Walks the root with `fs.readdirSync(dir, {withFileTypes: true})` recursively, skipping directories named `node_modules` and `.sensorium`; for every path `classify(file, root) === 'transform'`: `sitesOf(code, file, {root, ts})`; a file with a parse error counts in `files_unparsable`; matching by `specMatches(spec, rel, qualname)` over `sites` (eligible) and over the excluded function-likes (for `excluded_only`); `closest` over every eligible qualname for an unmatched spec.
```python
# ts/focus.py
SEP = "\x1f"

@dataclass(frozen=True)
class Resolution:
    matched: list[dict]
    unmatched: list[dict]
    excluded_only: list[dict]
    files_scanned: int
    files_unparsable: int
    wall: float
    @property
    def matched_specs(self) -> list[str]:
        return sorted(f"{m['rel']}:{m['qualname']}" for m in self.matched)

def resolve(root: Path, package: Path, specs: list[str], node: str = "node") -> Resolution:
    """subprocess.run([node, package/'src'/'resolve.mjs'], env=dict(os.environ, SENSORIUM_TS_ROOT=str(root),
    SENSORIUM_TS_PKG=str(package), SENSORIUM_FOCUS=SEP.join(specs)), cwd=root, capture_output=True, text=True);
    a non-zero exit raises PackageError naming the stderr; `wall` is the call's own wall clock."""

def refusals(res: Resolution, root: Path) -> list[str]:
    """One line per bad spec, in the order given:
    f"--focus {spec} matches no function under {root}; nothing was run." + (f" Closest: {', '.join(c)}" if c else "")
    f"--focus {spec} matches only functions this recorder does not instrument ({reasons}); nothing was run."
    where reasons is ", ".join(f"{k} x{n}" for k, n in sorted(item['reasons'].items()))."""
```
`driver.run`: after `check_root`, `res = focus_mod.resolve(plan.root, package, args.focus)` when `args.focus`; every refusal line printed as `error: <line>` on stderr, then `BAD_CALL` — BEFORE `paths.new_run_id()`; `_record(..., res)`; `Invocation` gains `focus: list[str] = field(default_factory=list)` and `focus_matched: list[str] = field(default_factory=list)` (last, defaulted; `from_json` tolerates absence); `_env` adds `SENSORIUM_FOCUS=SEP.join(args.focus)` when non-empty.

- [ ] **Step 1: Failing tests (RED).** `resolve.test.mjs` over a temp root under `probes/` (the `hook.test.mjs` recipe): three files, a spec matching one, a container spec matching two, a spec matching nothing with `closest`, a spec matching only an overload signature, a `.cjs` and a `node_modules` file ignored, a file with a syntax error counted. `tests/test_ts_driver_focus.py` on the `test_ts_driver.py` fixture project (`node --test`, no vitest): `--focus lib.ts:add` → the trace's `meta.focus == ["lib.ts:add"]`, `focus_matched == ["lib.ts:add"]`, `capabilities.line` true, LINE rows > 0, `invocation.json` carries both keys; `--focus nope` → stderr `error: --focus nope matches no function under <root>; nothing was run. Closest: add`, exit 2, no spool directory minted, nothing spawned (no `harness.json`; the directory count under `SENSORIUM_DIR/spool` unchanged); `--focus add --focus nope` prints one refusal line and exits 2; a package with no `resolve.mjs` is a named refusal.
- [ ] **Step 2: Implement; GREEN;** `tests/test_ts_driver.py::test_the_harness_is_told_the_six_things_it_cannot_work_out` becomes seven with `SENSORIUM_FOCUS` (present only when a focus was given — assert both). Commit: `feat(ts): --focus resolved before the run; the resolver; the invocation's focus keys`.

---

### Task 6: The converter — LINE rows, the CALL's args, the meta keys; the recorded fixture

**Files:**
- Modify: `src/sensorium/ts/build.py` (`_on_call`, new `_on_line`, `_invocation_meta`)
- Create: `tests/fixtures/ts-spools/focus-lines/{invocation.json,<pid>-0.jsonl,manifests/_tally.json,questions.json}`, `tests/test_ts_ingest_focus.py`; `tests/ts_spools.py` docstring gains the case's provenance line

**Interfaces (verbatim):**
```python
def _on_call(self, rec):
    code_id, rel, qualname, line, kind = self._code(rec)
    if "a" in rec:
        payload = {"args": rec["a"]}
        for v in rec["a"].values():
            self._trunc(v)
    else:
        payload = {"args": {}, "unread": ["locals"]}
    # … unchanged from here …

def _on_line(self, rec):
    frame = self._frame(rec, rec["f"])
    if frame.closed:
        raise ConversionError(f"{self.spool.path}: a LINE names frame {rec['f']}, which had already closed")
    payload = {"deltas": rec["d"]}
    if rec.get("u"):
        payload["unbound"] = list(rec["u"])
    for v in rec["d"].values():
        self._trunc(v)
    self.w.add_event(rec["ts"], THREAD, "LINE", frame.db_id, frame.code_id, rec["l"], payload, self._task(rec))
    self.events += 1          # no fingerprint update: LINE is not causal

# _invocation_meta gains, after driver_version:
meta["root"] = self.inv.root                       # plan P9
if self.inv.focus:
    meta["focus"] = list(self.inv.focus)
    meta["focus_matched"] = list(self.inv.focus_matched)
```

- [ ] **Step 1: The fixture (plan P14).** Record the probe (`npm --prefix typescript/probes run probe` with a fresh `SENSORIUM_SPOOL`), take the `focus.probe.test.ts` container's spool, sanitise it, hand-write `invocation.json` with `focus` = the config's `FOCUS` list and `focus_matched` its `rel:qualname` forms, and `questions.json` pinning: `frame $RUN --fn letChain` prints `args: n=1` and a `timeline:` with one `LINE` per marked row; `tree $RUN` prints `letChain(n=1) -> 3` and an unfocused sibling with `<unread: locals>`; `grep $RUN --kind LINE` count; `info $RUN` prints `focus: focus.probe.test.ts:letChain, …` and the declaration block with `line: true`; `watch $RUN --at letChain --expr b == 2` SATISFIED exit 0; `flow $RUN --value 2` sightings ≥ 1 (the `flow --object` question is added at Task 7).
- [ ] **Step 2: Failing tests (RED)** in `tests/test_ts_ingest_focus.py` (the `ts_spools` machinery): the case converts and answers every question; a LINE row's `line`, `payload.deltas`, `payload.unbound`; a CALL carrying `a` writes `args` without `unread`; `meta.root`, `meta.focus`, `meta.focus_matched`; the fingerprint of the focused task equals a fingerprint computed over its CALL/RETURN/RAISE/HANDLED rows alone; a hand-edited spool whose LINE names a closed frame is refused with the sentence above; `test_ts_ingest_caps.py` gains the four-key BOOT.
- [ ] **Step 3: Implement; GREEN;** commit `feat(ts): LINE rows, a focused CALL's args, root/focus/focus_matched in meta`.

---

### Task 7: The readers — dialects, constants, sites, the re-record template, serial identity; vectors v35–v39

**Files:**
- Create: `src/sensorium/query/js_inspect.py`, `dbg_dialects.py`, `sites.py`, `typescript/test/fixtures/inspect-table.json`, `typescript/test/fixtures/gen-inspect-table.mjs`, `tests/test_js_inspect.py`, `tests/test_watch_typescript.py`, `tests/test_flow_serial.py`, vectors `v35-predicate-constants.json`, `v36-typescript-line-and-args.json`, `v37-flow-object-serial.json`, `v38-inspect-dialect-agreement.json`, `v39-site-spellings.json`
- Modify: `expr.py`, `vocab.py`, `watch_cmd.py`, `flow_cmd.py`, `flow_values.py`, `docs/trace-format/VECTORS.md`, `tests/test_expr.py`, `tests/test_vocab.py`, `tests/ts_traces.py` (a `line_ev` builder)

**Interfaces (verbatim):**
```python
# js_inspect.py
def js_number(x) -> str:
    """ECMAScript Number::toString. NaN / Infinity / -Infinity / -0 by name; an integral value with abs < 1e21
    as its integer; else the shortest round-trip digits (Decimal(repr(abs(x))).as_tuple()) placed by
    n = exponent + len(digits), k = len(digits):
      k <= n <= 21   -> digits + '0' * (n - k)
      0 < n <= 21    -> digits[:n] + '.' + digits[n:]
      -6 < n <= 0    -> '0.' + '0' * (-n) + digits
      otherwise      -> digits[0] + ('.' + digits[1:] if k > 1 else '') + 'e' + ('+' if n - 1 >= 0 else '-') + str(abs(n - 1))
    with the sign put back in front."""

def inspect_text(target) -> str | None:
    """None -> 'null'; bool -> 'true'/'false'; int -> str(int); float -> js_number; str -> quoted (single quotes,
    else double when the text holds a single quote and no double, else backticks when it holds both and no
    backtick, else single with \\' escaped), with \\n \\t \\r \\b \\f \\v \\\\ and the chosen quote escaped and
    other control characters as \\xHH; a str past 100 characters -> None (plan P7); anything else -> None."""

def read_inspect(text: str):
    """'null' -> None; 'undefined' -> UNDEFINED; 'true'/'false' -> bool; 'NaN'/'Infinity'/'-Infinity' -> the floats;
    '-0' -> -0.0; r'-?\\d+n' -> int; r'-?\\d+' -> int; r'-?\\d+(\\.\\d+)?[eE][-+]?\\d+|-?\\d+\\.\\d+' -> float;
    a quoted text ending in "'... N more characters" -> TRUNCATED; a quoted text -> the string with JS escapes
    undone (\\n \\t \\r \\b \\f \\v \\0 \\\\ \\' \\" \\` \\xHH \\uHHHH \\u{H+}; an unknown escape kept as read);
    else _DbgText(text)."""

# dbg_dialects.py
Dialect = namedtuple("Dialect", "read write")
RUST = Dialect(read_debug, debug_text)
INSPECT = Dialect(read_inspect, inspect_text)
BY_NAME = {"rust": RUST, "inspect": INSPECT}
def for_trace(trace) -> Dialect:
    name = terms(trace).dbg_dialect
    return BY_NAME[name] if name else RUST

# expr.py
UNDEFINED = _Marker("<undefined>")
_CONSTANTS = {"null": None, "undefined": UNDEFINED, "true": True, "false": False}
def resolve(v: dict, dialect=None):
    # k == "dbg": read = dialect.read if dialect else read_debug; a TRUNCATED from read stays TRUNCATED;
    # a str from read wraps as _DbgText as today
# compile_expr: names -= _CONSTANTS.keys()          (plan P11)
# _eval Name branch: if node.id in _CONSTANTS: return _CONSTANTS[node.id]

# vocab.Terms — five fields, all three columns:
#   dbg_dialect: str | None      PYTHON None, RUST "rust", TYPESCRIPT "inspect"
#   site_spelling: str           PYTHON "module", RUST "module", TYPESCRIPT "rel"          (plan P8)
#   identity_basis: str          PYTHON "address", RUST "none", TYPESCRIPT "serial"
#   rerun_command: str           PYTHON "sensorium run{focus} -- {command}", TYPESCRIPT "sensorium ts run{focus} -- {command}", RUST "cargo sensorium{focus} {command}"
#   command_key: str             PYTHON "argv", TYPESCRIPT "harness_command", RUST "cargo_args"
# TYPESCRIPT.no_rerun_note = "no rerun was attempted; refocus is not yet this recorder's -- record again with `sensorium ts run --focus <file>:<qualname> -- <harness command>`"
# TYPESCRIPT.timeline_hint = "record again with `sensorium ts run --focus {mod}:{qualname} -- <harness command>`; per-statement capture is opt-in at record time"

# sites.py
def spell_site(trace, code) -> str:
    """"rel": f"{relative(code.file, meta['root'])}:{code.qualname}" when meta carries root, else the basename form;
    "module": today's f"{module_name_for(file, cwd) or stem}:{qualname}"."""
def site_matches(code, at: str, trace) -> bool:
    """watch_cmd's rule today, with the basename and the root-relative path added to the file set."""
def rerun_command(trace, codes) -> str:
    """specs = meta.focus + [spell_site(trace, c) for c in codes]; focus = ''.join(f' --focus {shlex.quote(s)}' for s in specs);
    command = ' '.join(shlex.quote(a) for a in (meta.get(terms.command_key) or [])); body = terms.rerun_command.format(focus=focus, command=command);
    return f'cd {shlex.quote(cwd)} && {body}' if cwd else body."""
```
`watch_cmd`: `refocus_cmd` and `site_matches` become one-line delegations to `sites.py` (Python output byte-identical — `test_watch.py` is the fence); `sites_for(..., dialect)`; `_bind(..., dialect)`; `_no_match` lists `spell_site`. `flow_cmd`: `Index(trace)` holds `self.dialect = for_trace(trace)`; `scan(events, target, write)`, `find_in_value(v, target, write)`; `matches(cap, target, write=debug_text)`: an `ObjTarget` matches when `(k in CONTAINER_KINDS or (k == "dbg" and "oid" in cap)) and oid/type equal`; `resolve_object`'s primitive refusal excludes a `dbg` with `oid`; `_header` on `--object`: `basis = terms(trace).identity_basis`; serial → the lines `"  identity is a per-object serial minted once and never reused: every sighting is the same object"` and `"  captured-value lineage, not dataflow analysis: the trace records values, not the edges between them"`; `run`: `all_gaps = gaps(...) if isinstance(target, ObjTarget) and basis == "address" else []`; the footer prints `continuity: exact (serial identity)` for an `ObjTarget` on a serial basis.

- [ ] **Step 1: The measured table.** `gen-inspect-table.mjs` writes `inspect-table.json`: `[{"literal": <JSON value, or {"bigint": "123"} / {"undefined": true} / {"nan": true} / {"inf": 1|-1} / {"negzero": true}>, "text": <util.inspect under the recorder's INSPECT>}, …]` for: the strings `abc`, `it's`, `it's "x"`, `a\nb\tc\\d`, `café`, the empty string, `x`×150; `undefined`, `null`, `true`, `false`; `5`, `-5`, `2.5`, `1e21`, `1e-7`, `-0`, `0.000001`, `123456789.123`, `1.5e300`, `5e-324`, `NaN`, `Infinity`, `-Infinity`; `123n`; `[1,2]`, `{}`, `{a:1,b:"x"}`, a function, a class, a `Map`, a `Date(0)`, a 12-element array. Run it once, commit the JSON (the measurement); `tests/test_js_inspect.py`: every row reads as §4.1 says (numbers to the literal, strings to the string, the 150-char row to TRUNCATED, the function to `_DbgText`); `read_inspect(inspect_text(L)) == L` for every literal `L` in the domain; `inspect_text(x) == row.text` for every scalar row; `js_number` on the twelve numbers above equals node's text.
- [ ] **Step 2: Failing tests (RED).** `test_expr.py`: `x == null`, `x == undefined`, `flag == true`, `compile_expr("x == null").names == {"x"}`, `UNDEFINED + 1` raises `EvalError`, `resolve({"k":"dbg","v":"null"}, INSPECT) is None`, `resolve({"k":"dbg","v":"'a'"}, INSPECT) == "a"`, `resolve({"k":"dbg","v":"\"a\""})` (no dialect) is Rust's reading. `test_vocab.py`: every column carries the five new fields; the completeness test enumerates `Terms.__dataclass_fields__`. `test_watch_typescript.py` (on `ts_traces.ts_trace` with LINE rows built by a new `line_ev(ts, frame, code, line, deltas, unbound=None)` in `ts_traces.py`, and `meta["root"] = "/w/app"`): `watch --at cache:refresh`, `--at cache.ts:refresh`, `--at src/lib/cache.ts:refresh` all match (the spelling fixture's rows), `--at lib:refresh` does not; a `const` inside a block is reported at no site after the row that lists it `unbound`; the no-match listing spells `src/lib/cache.ts:refresh`; the re-record guidance on a TS trace prints `cd /w/app && sensorium ts run --focus src/lib/cache.ts:refresh -- npx vitest run src/config` and on the Python fixture prints today's bytes. `test_flow_serial.py`: `flow --object e<N>:x` on a TS trace whose two LINE captures share `oid` 7 lists both, prints the serial header and `continuity: exact (serial identity)`, no gap line; `resolve_object` on a `dbg` with `oid` is an identity, without one a primitive refusal naming `--value`; `flow --value 5.0` sights `{"k":"dbg","v":"5"}` on a TS trace and not on a Rust one (`test_flow.py`'s Rust fence kept).
- [ ] **Step 3: The vectors** (the `v34` shape; meta from `ts_traces.TS_META` at 0.3.0 with `line`/`locals` true where rows exist): v35 — a Python-shaped trace whose `watch --expr x == null` is SATISFIED where `x` is `{"k":"none"}`; v36 — a TS trace with a focused CALL (`args`) and three LINE rows: `frame` prints `args: key='rate'` and the timeline, `tree` prints `refresh(key='rate') -> 100`; v37 — two LINE captures of one serial: `flow --object` two sightings, exact continuity; v38 — one capture `{"k":"dbg","v":"'A1'"}`: `watch --expr s == 'A1'` SATISFIED and `flow --value "'A1'"` one sighting (A11 in the second dialect); v39 — the spelling fixture's five matching `--at` forms each answer and the five non-matching each print the no-match listing. `VECTORS.md` rows. `tests/test_vectors.py` green.
- [ ] **Step 4: Implement; GREEN; mutation-check** `js_number`'s three placement branches, the `_CONSTANTS` exclusion from `names`, `matches`'s `oid` arm, `site_matches`'s basename arm. The focus-lines fixture's `questions.json` gains `flow --object letChain:return`. Commit: `feat(query): the inspect dialect, predicate constants, one site spelling, the re-record template, serial identity`.

---

### Task 8: The corpus

**Files:**
- Create: `corpus/typescript/{focus_let_chain,focus_loop_counter,focus_block_scope,focus_destructure,focus_args,focus_async,focus_catch_binding,focus_place_write,focus_container,flow_value_inspect}/` (each: a source file, a `<case>.test.ts`, `questions.yaml`); rename `object_refused` → `object_identity` (`git mv`)
- Modify: `corpus/cases.py` (`_validate_vitest` admits `record` when it holds only `focus: [str, …]`; `window` on a vitest case refused as the Python recorder's), `corpus/run_corpus.py` (`_record_vitest(wd, sdir, harness_args, focus=())` inserts `--focus f` before `"--"`; `_record_both` passes `case.record.get("focus") or []`), `corpus/typescript/watch_refused/questions.yaml` (0.3.0), `corpus/typescript/README.md`, `docs/corpus.md`

**One full case, `focus_block_scope`** (the shape every other follows):
```ts
// corpus/typescript/focus_block_scope/scope.ts
// Seeded bug: the discount is computed inside the `if` and the code after it
// reads a stale total. The question a fold without `unbound` gets WRONG is
// whether `discount` was still bound at the statement after the block.
export function total(items: number[], member: boolean): number {
  let sum = 0;
  for (const price of items) {
    sum += price;
  }
  if (member) {
    const discount = Math.round(sum * 0.1);
    sum -= discount;
  }
  const rounded = Math.round(sum);
  return rounded;
}
```
```yaml
program: vitest
harness_args: ["run", "focus_block_scope/"]
record: {focus: ["scope.ts:total"]}
questions:
  - id: is-discount-alive-after-its-block
    ask: >
      `discount` is declared inside the `if`. Is it reported at the statement after the block?
    truth: >
      No. The `if` statement's own LINE row lists `discount` as `unbound`, so `watch` evaluates
      `discount == 9` at the two sites inside the block (SATISFIED there) and reports the
      `const rounded` row and the CALL as sites where `discount` is not in scope — never as hits.
    why_logs_fail: >
      A `console.log(discount)` after the block is a compile error, which is the point: the
      trace has to say the name died, not merely stop mentioning it.
    command: ["watch", "$RUN", "--at", "total", "--expr", "discount == 9"]
    expect_exit: 0
    expect_contains:
      - "verdict: SATISFIED at 2 of the 2 site(s) the predicate could be evaluated at"
      - "discount: not in scope at this site"
    expect_line:
      - ["HIT", "LINE", "total L", "discount=9"]
```
Each case's `questions.yaml` pins, byte-exact, the lines named in spec §7's table; `focus_args` pins `tree` lines `total(items=[ 1, 2 ], member=true) -> 3` and `helper() <unread: locals> -> 1`; `focus_async` pins `~ YIELD` / `~ RESUME` between LINE rows in `frame`; `focus_place_write` pins a `LINE … L<n>` row with no `=` after the site (empty deltas); `focus_container` pins `info`'s `focus:` line; `flow_value_inspect` pins `flow --value 5.0` → `sightings: 1`, `flow --value "'A1'"` → one, a 150-character string → `sightings: 0`, `watch --expr x == null` SATISFIED; `object_identity` pins `flow --object loadSettings:return` → `sightings: 3 event(s)` (two returns and `tune`'s argument) and `continuity: exact (serial identity)`.

- [ ] **Step 1:** `cases.py` and `run_corpus.py` (RED in `tests/test_corpus.py`: a vitest case with `record: {focus: […]}` loads and records with the flags; `record: {window: …}` refused). GREEN.
- [ ] **Step 2:** The ten cases + the rename, each collected with `python corpus/run_corpus.py --only typescript/<case> --require-driver`; every existing TS case re-collected; the collector's diff against `aea6b47`'s pins shows only declaration-block and version lines, listed in the commit message. `docs/corpus.md` and the README tables. Commit: `test(corpus): ten focus cases, object_identity, the record key on a vitest case`.

---

### Task 9: Instruments, then E12 measured once

**Files:**
- Create: `typescript/acceptance/e12.sh`, `e12_report.py`, `e12_h3.py`, `e12_cost.py`, `e12_h8.sh`, `assemble_rung4.py`; `tests/test_acceptance_scripts.py` gains the new scripts to its census
- Modify: the record's §2.1–§2.3, §3, §4, §5; `…-s5-rung4-tracehashes.txt`; `.results.json`

**Interfaces:** `e12.sh <lens dir> <manifest> <store> <out dir>` runs the manifest check, then U1 F1 U2 F2 U3 F3 under the load guard through `"$SENSORIUM_BIN" ts run …` (each run's `run:` lines, wall, and the harness's `Test Files`/`Tests` lines into `<out>/arms.jsonl`), times `node resolve.mjs` once, checks the manifest again, and writes the hash list; `e12_report.py <store> <arms> <out>` runs the twelve read commands of §1.5 verbatim against U1/F1 (transcripts saved), writes cells H1, H2, H4, H5, H6; `e12_h3.py <store> <handcount.md> <out>` compares F1's first `parseDiceGroups` activation's LINE rows (line, delta names, unbound names, in order) to the table → cell H3 with the diff of lines; `e12_cost.py <arms> <out>` → H7 (medians, n, dropped); `e12_h8.sh <out>` runs the four suites, the corpus, the probes, and `e7_report.py` (`E7_NEEDLES=rung2`) over every saved transcript → H8; `assemble_rung4.py <out> <results> <recorder> <rev> [PATH=LABEL]…` verifies the hash list (`sha256sum -c`), the journal delta (exactly twelve new lines, one per §1.5 command), stamps strict, refuses a box path.

- [ ] **Step 1: Instruments written and dry-run on the probe project** (a two-file manifest, `E12_N=1`), every cell shape checked, `tests/test_acceptance_scripts.py` green. Commit: `test(acceptance): the rung-4 instruments`.
- [ ] **Step 2: Fences first** (`e_fences.py <aea6b47> <out>`), then ONE `e12.sh` session on the lens, then the reads, then H3, H7, H8, the assembler. Every endpoint once. A `.FAILED` before any number → fix, relaunch from zero, archive. After a number: a STOP stands.
- [ ] **Step 3: The record's §3–§5** from the cells (§3 one row per endpoint with the rule and the word; §4 decisions and what each reading showed; §5 what the rung ships and the gaps found). Commit: `test(acceptance): S5 rung 4 measured — <DONE|DONE-WITH-STOP>`.

---

### Task 10: Documents, versions, the ledger, the skill

**Files:**
- Modify: `pyproject.toml` (0.12.0), `CHANGELOG.md` (the 0.12.0 entry, drafted and measured BEFORE it is appended; a second cut only if it would cross 800), `docs/TRACE-FORMAT.md` (three sentences), `docs/trace-format/TYPESCRIPT-KEYS.md` (the focus reading in full; rows for `root`, `focus`, `focus_matched`; the inspect table; `unbound`; serial identity), `typescript/HONESTY.md` (§7 "declared absent" rewritten; new §11 *Under a focus* + identity; index rows), `typescript/HONESTY-BLIND-SPOTS.md` (28–34; the falsy-`if` item written as CLOSED by plan P1 in the same breath), `docs/query.md`, `docs/CARRIED-DEBT.md` (this rung's section: settled — the rung-3 items struck in place; deferred by ruling — P1–P14 and the Rust fold debt; process lessons), the spec's §15 (P1–P14 and every controller ruling, dated), `README.md` (one sentence at most)
- Create: `~/.claude/skills/debugging-typescript-with-sensorium/SKILL.md` (outside the repo; the Rust skill's shape: setup on this box, `sensorium ts run` and its `--focus` spelling, what is captured and what is not, the query playbook including the two killer plays, the exit table, gotchas — every command copied from a corpus case that pins it)

- [ ] **Step 1:** Docs and the ledger; `tests/test_ceiling.py`, `tests/test_release_tokens.py`, the full Python suite, the Node tests → green. Commit: `chore(release): sensorium 0.12.0` (pyproject + CHANGELOG together), then `docs: TRACE-FORMAT, TYPESCRIPT-KEYS, HONESTY, query.md, CARRIED-DEBT and the spec's §15 for rung 4`.
- [ ] **Step 2:** The skill file; verify every command in it against the corpus's `questions.yaml` commands by name. Not committed to this repo; noted in CARRIED-DEBT.

---

### Task 11: Final review, one fix wave, the PR

- [ ] Final whole-branch review on the most capable model over `aea6b47..HEAD`, "with fixes"; one fix wave; one scoped re-review; push; PR against `main` with the record's numbers and every ruling; CI; **merge is Brice's**; then archive the ledger to `/mnt/extra/sensorium-rung2/sdd-archive/2026-09-11-sensorium-s5-rung4-focus-tier/`, remove the worktree, delete the branch local and remote, verify origin sync, reinstall the global tool (0.12.0), and name the two owed rulings: freeing `store-rung2ts` and the rung-4 store's fate.

---

## Self-review against the spec

- **§2.1–2.4** → Tasks 3 (matcher), 5 (resolver, driver, plumbing, artifacts), 2 (the declaration from the environment), 4 (manifest `focused`, tally). The refusal's prefix is plan P5, recorded for §15.
- **§3.1–3.9** → Tasks 3 and 4 (every row of the deltas table is a golden and a bindings test; plan P1–P4 refine the head-row and guard-body rules and are recorded), Task 2 (wire, runtime), Task 6 (row, refusal, no fingerprint change), Task 10 (blind spots 28–34).
- **§4.1–4.5** → Task 7 (dialects, the measured table, constants, `sites.py`, the template, `flow` serial basis); plan P7, P8, P10, P11 recorded. `frame`/`tree` answer through the corpus (Task 8) and v36.
- **§5** → Task 2 (`oid`/`type`, P12), Task 7 (`flow --object`), Task 8 (`object_identity` case), Task 10 (the promise, the blind spot).
- **§6.1–6.4** → Tasks 1 (cuts, split, debts), 2 (0.3.0), 10 (0.12.0, every document). The journal rule is in the Pre-registration block and the assembler (Task 9).
- **§7** → Task 8, ten cases named as the spec names them.
- **§8/§13** → Task 0 (§1 locked alone; the hand count; the triples; the sightings; the identity lookup), Task 9 (instruments, one measurement). H2's third reading (args in `grep`) and P13's arm design are plan additions, recorded.
- **§9** → every task's RED/GREEN steps, the mutation checks, the live test at Tasks 4/6/8, the probes at Task 4.
- **§10** → this plan's order: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11; the spec's steps 1–2 became Tasks 2–4 and its step 5 Task 7.
- **Placeholder scan:** no TBD/TODO; every code step carries its form; every test step names its assertions.
- **Type consistency:** `line(f, l, pairs, unbound)` (Task 2) ↔ `__srt.line(__sf,${line},[…],[…])` (Task 4) ↔ `rec["l"]`, `rec["d"]`, `rec["u"]` (Task 6); `call(fileId, c, args)` ↔ `rec.a` ↔ `payload["args"]`; `Site.focused` ↔ `Manifest.focused` ↔ tally `functions_focused`; `specMatches(spec, rel, qualname)` used by `planSites` and `resolve.mjs`; `Resolution.matched_specs` ↔ `Invocation.focus_matched` ↔ `meta.focus_matched`; `Dialect.read/write` ↔ `resolve(v, dialect)` / `matches(cap, target, write)`; `terms(trace).site_spelling/identity_basis/rerun_command/command_key/dbg_dialect` named identically in `vocab.py`, `sites.py`, `flow_cmd.py`, `dbg_dialects.py`.
