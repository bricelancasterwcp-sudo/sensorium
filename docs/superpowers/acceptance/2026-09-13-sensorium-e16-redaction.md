# E16 — secrets redaction, measured

## 1. Pre-registration (locked)

### 9. E16, pre-registered

Measured once, after PR C, on this box, against the three probe programs
the plan adds under `probes/redaction/{python,rust,typescript}`; each
carries `SENSORIUM_E16_TOKEN` in the environment and receives the same
string as an argument, a local, a return value, a header dict value and
(Python) a `print`. The value is `sk-e16-` followed by 33 random characters
(40 in all), minted by the instrument and never committed: the prefix puts
it inside the content rule's `sk-` pattern, so the cases that carry no
firing name — the header dict in Rust's `Debug` text, Python's `print` —
are reached by content, and a token that only the name rule could see
would measure the name rule twice and the content rule never. The instrument is `tests/acceptance/e16.sh`, dry-run
first on a 4-character decoy to check every artifact path it reads exists.
Both readings are committed here.

| H | Claim | PASS | STOP |
|---|---|---|---|
| H1 | The token's bytes appear in **no file under the store** (`*.db`, `*.db-wal`, `*.db-shm`, `invocations.jsonl`, `redaction.key`) and in no Python or TypeScript spool for any of the three recorders. In the Rust spool it may appear only inside a `dbg` text (content) or a RETURN value block, **never** in a LINE tag-3 block, the proc header's `env`, or any file after conversion. Checked with `grep -c` over raw bytes, per file, before and after conversion. | every count 0 where 0 is required | any non-zero: a missed path. Named, fixed, and the whole of E16 re-measured from zero with a fresh token — an acceptance test of correctness is re-run after a fix, and the record says which run is the first PASS |
| H2 | Every file the three runs created under the store and the spool dirs is 0600; every directory 0700; `redaction.key` 0600. `stat -c %a`, listed per file. | all | any other mode |
| H3 | `refocus` on the Python and Rust probes, token unchanged: licence held, env line names the redacted variable among the compared. Then the token changed between the recording and the re-run (the instrument re-exports it): licence WITHHELD naming `SENSORIUM_E16_TOKEN` as a difference. | both | either the wrong way |
| H4 | `sensorium redact --all --dry-run` on a **copy** of this box's `~/.sensorium/traces` (273 traces) reports every trace holding `CLAUDE_CODE_MESSAGING_TOKEN` plaintext; `sensorium redact --all` on the copy leaves `grep -c <that token's value>` at 0 across every file, every trace still opens (`info` exit 0), and the count line matches the dry run. | all | any residue, any trace that no longer opens, or dry-run ≠ real |
| H5 | Overhead: `corpus/_bench` before PR A and after PR C, same box, n=5 each, the existing harness. Reported as the two medians and the ratio. **Never gated** (rust/HONESTY.md §10: cost is reported, never gated). | n/a | n/a — an outlier ratio is a finding for CARRIED-DEBT, not a stop |
| H6 | The census (§8) on the three probes' traces equals the planted count (env 1, values: Python 5, TypeScript 4, Rust 4 — the Rust probe has no output row and the TypeScript probe no print row) exactly. | exact | any other number: an over- or under-firing rule |

Record: `docs/superpowers/acceptance/<date measured>-sensorium-e16-redaction.md`,
with the per-file grep table, the mode table, the two refocus transcripts,
the dry-run/real pair, the bench numbers and their lens.

### The plan's pre-registration block

- **Part A's cells** are H1 restricted to the environment (the token is in no file under the store, the Python spool dir, the TypeScript spool dir, and in no Rust proc header; the Rust `.spool` files carry no environment at all), H2 in full, H3 in full, H6 restricted to `redaction.env` (exactly one name per trace: `SENSORIUM_E16_TOKEN`). H1-values, H5 are part B; H4 is part C. Both readings per §9's table stand.
- **The token** is `sk-e16-` + 33 characters from `[A-Za-z0-9]`, minted by `e16a.sh` into `$E16_DIR/token` at 0600, exported as `SENSORIUM_E16_TOKEN`, never printed by the instrument and never committed; the record cites its sha256 prefix only.
- **Locations** are the record's §2 pin table only: `E16_DIR=/mnt/extra/sensorium-rung2/e16`, store `$E16_DIR/store-a`, spools under it, transcripts `$E16_DIR/a-transcripts/`.
- **Versions expected:** `driver_version`/`recorder` read `sensorium 0.15.0`, `sensorium-rt 0.6.0`, `cargo-sensorium 0.7.0`, `sensorium-ts 0.5.0`; §2 records what they were.
- **H3's pair:** Python — `refocus <run> --focus main` on the aliasing recording; Rust — `refocus <run> --focus compute` (the case's focused fn; read `corpus/rust/aliasing/questions.yaml` for the name). First with the token unchanged (predict: licence held, `SENSORIUM_E16_TOKEN` counted among compared), then re-exported to a fresh value (predict: WITHHELD, the name in the changed list). TypeScript's refocus is exercised by v43 and `tests/test_refocus_redaction.py`, not live, because the TS pair's env clause runs the same code path — stated as a reading, not a gate.
- **Kill rules:** each recording 600 s, each refocus 900 s, the part 45 min; a kill is an infrastructure event, rerun from zero with a fresh token.

### 2026-09-14 — Part B's pre-registration (amendment, beside the locked text above)

- **Part B's cells** are H1 restricted to VALUES (the token planted as an argument, a local, a return value, a header-dict value and, in Python, a `print`, under `SENSORIUM_E16_TOKEN` as in part A), H5 in full, and H6 restricted to `redaction.values` and the census. H2, H3, H1-env and H6-env were part A's (measured, DONE at run 2); H4 is part C's. Both readings per §9's table stand.
- **The token** is `sk-e16-` + 33 characters from `[A-Za-z0-9]`, minted by `e16b.sh` into `$E16_DIR/token` at 0600, exported as `SENSORIUM_E16_TOKEN`, never printed by the instrument and never committed; the record cites its sha256 prefix only. The dry run's decoy is `dry-` + 4 characters, which no content pattern matches, so a dry run exercises the plumbing and the NAME rows and never the content rule.
- **The three probes** are `tests/acceptance_e16/probes/python/main.py` (`sensorium run --focus handle -- main.py`), `tests/acceptance_e16/probes/rust/` (`cargo sensorium run --focus handle`) and `tests/acceptance_e16/probes/typescript/secret.ts` + `secret.test.ts` copied into a copy of `corpus/typescript` (`sensorium ts run --focus handle -- npx vitest run secret`). Each reads the token from the environment in a function named `secret`, passes it to a focused function named `handle` that binds it to a local, puts it in a header dict under the key `authorization`, and (Python only) prints it alone as one `print` argument.
- **H6-values' planted counts, per row.** Python **5**: `secret`'s RETURN by name (the qualname segment `SECRET`); the `token` LINE delta in `handle` by name; the `headers` delta's map value under the key `authorization` by name; the CALL argument `token` of `send(token)` by name; the `print` chunk holding the token alone, by content. TypeScript **4**: the CALL argument `token` of `handle(token)` by name; the `copy` delta by content; the `headers` delta by content (the inspect text holds the token); `secret`'s RETURN by name. Rust **4**: the parameters row's `token` delta of `handle` by name (tag 4); the `copy` delta by content (converter); the `headers` delta's `Debug` text by content (converter); `secret`'s RETURN by name (converter). `redaction.env` on every trace is exactly `{SENSORIUM_E16_TOKEN}`.
- **H1-values' reading:** every file under the store 0 (`*.db`, `*.db-wal`, `*.db-shm`, `invocations.jsonl`, `redaction.key`, everything under `spool/`); every Rust `<pid>.proc.json` 0; the Rust `.spool` files together exactly **3** occurrences (B16); the TypeScript spool directory 0. Counted as occurrences with `grep -a -o -F "$TOKEN" | wc -l` per file. PASS iff all four hold.
- **H5's reading:** `python -c "from corpus._bench import bench; bench.report(reps=5)"` run twice, in a worktree at `7dd25d2` under its own `.venv` and in this branch's worktree under its `.venv`, each against a scratch `SENSORIUM_DIR` under `$E16_DIR`, same box, back to back. Reported: both tables verbatim, and per workload row the `recorded/baseline` ratio at 7dd25d2, the same at HEAD, and HEAD's over 7dd25d2's. Never gated (§9). An outlier is a CARRIED-DEBT finding.
- **Locations** are the record's §3 pin table only: `E16_DIR=/mnt/extra/sensorium-rung2/e16`, store `$E16_DIR/store-b`, spools under it, the baseline worktree `$E16_DIR/baseline-7dd25d2`, transcripts `$E16_DIR/b-transcripts/`. Part A's `store-a`/`store-a2` trees are not read.
- **Versions expected:** `recorder` reads `sensorium 0.16.0`, `sensorium-rt 0.7.0`, `sensorium-ts 0.6.0`; `driver_version` `cargo-sensorium 0.8.0`; §3 records what they were.
- **Kill rules:** the driver rebuild 1800 s, the baseline worktree build 600 s, each recording 600 s, each bench table 1200 s, the part 60 min; a kill is an infrastructure event, rerun from zero with a fresh token.

## 2. Part A

### measured 2026-09-14

Measured once, on this box, under `e16a.sh`. **Part A: DONE-WITH-STOP** — H1 PASS  H2 STOP  H3 STOP  H6 PASS. The token was `sk-e16-` plus 33 characters, minted by the instrument, never printed and never committed: `sha256(token)[:8] = b3d91fd1`, and the value H3 re-exported `5d755067`. Every recording and every refocus ran under a scrubbed environment of exactly `PATH`, `HOME`, `USER`, `LANG`, `TMPDIR`, `CARGO_TARGET_DIR`, `SENSORIUM_DIR`, `SENSORIUM_E16_TOKEN` — no other name reached a recorder, and the instrument refuses to start unless none of them fires rule v1, which is what makes H6's "exactly one name" a fact about the token. 1.9s wall clock.

| cell | word | §9's rule | what was read |
|---|---|---|---|
| H1 (environment) | **PASS** | every count 0 where 0 is required | 842 file(s) examined, every count 0 |
| H2 | **STOP** | any other mode | 10 path(s) carry another mode: 775 store-a/spool (want 700), 775 store-a/spool/20260914-001904-f6b424 (want 700), 775 store-a/spool/20260914-001904-f6b424/manifests (want 700), 664 store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__async_interleaved.test.ts.json (want 600), 664 store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__store.ts.json (want 600), 664 store-a/spool/20260914-001904-f6b424/manifests/_tally.json (want 600), 664 store-a/spool/20260914-001904-f6b424/harness.json (want 600), 664 store-a/spool/20260914-001904-f6b424/ingested.json (want 600), 664 store-a/spool/20260914-001904-f6b424/invocation.json (want 600), 664 rust-target/sensorium/spool/20260914-001904-424fc9/invocation.json (want 600) |
| H3 | **STOP** | either the wrong way | 2 of 4 pair(s) read the other way: rust-unchanged: predicted a granted licence with SENSORIUM_E16_TOKEN among the compared; read licence granted, env unchanged, token named on the env line: True, token in the recorded environment: True; rust-changed: predicted WITHHELD with SENSORIUM_E16_TOKEN in the changed list; read licence granted, env unchanged, token in the changed list: False |
| H6 (`redaction.env`) | **PASS** | exact | 3 trace(s), each redacting exactly SENSORIUM_E16_TOKEN |
| H1-values | dropped | -- | part B |
| H4 | dropped | -- | part C |
| H5 | dropped | -- | part B |
| H6-values | dropped | -- | part B |

#### Pins

| pin | path |
|---|---|
| work root | `E16_DIR=/mnt/extra/sensorium-rung2/e16` |
| store | `$E16_DIR/store-a` |
| transcripts | `$E16_DIR/a-transcripts/` |
| Python case copy | `$E16_DIR/py-case/` |
| crate copy | `$E16_DIR/rust-crate/` |
| vitest project copy | `$E16_DIR/ts-project/` |
| cargo target | `$E16_DIR/rust-target/` |
| instrument output | `$E16_DIR/a-out/` |
| driver (the committed transcripts' label) | `$DRIVER_DIR` — the release `cargo-sensorium`'s own directory, outside the work root |

#### The dry run

Written by hand. Run 1 was measured before the instrument carried a
`dry_run_findings` field; that field is what renders this section for a later
run, and this paragraph is what it would have said.

Two dry runs preceded the measurement, into a work root of their own — its
own store, cargo target directory and case copies, all deleted afterwards —
with a `dry-` plus four decoy that cannot match the content rule part B will
measure, and every timer at 60 s. What they found, and what changed in the
instrument between them and the run above:

- Reading `driver_version` out of each trace opens a read-only sqlite
  connection, which cannot checkpoint a WAL and so leaves `.db-wal`/`.db-shm`
  beside the trace — and it ran AFTER the grep sweep, so those six files were
  never looked at. The `versions` phase moved ahead of `grep`, and the sweep
  went from 836 files to 842.
- Two rendered wordings were wrong about their own subject: H1's summary rows
  said "no recorder's own" of trees that include the driver's, and H2's
  out-of-scope caption did not say it lists top directories only. Both
  corrected.
- The assembler refused the dry raw record by name (`dry_run: true`), which
  is the refusal the dry run exists to exercise; a copy with the flag flipped
  rendered every section, so every artifact path the reader opens existed and
  parsed.
- The Rust arm is 0.38 s, not minutes: `cargo-sensorium` runs the target
  under a shim rather than linking `sensorium-rt` into the crate, so there is
  no cold build. R29's optional 1200 s Rust timer was not taken, and the dry
  run's 60 s timers were not raised.

**Both STOPs above were already visible in the dry run, and nothing was
altered in response.** No prediction, no constant, no cell and no line of
`sensorium` changed between seeing them and measuring: `PREDICTIONS`, `RULES`
and the token's name went into the run exactly as §1 fixed them, and the two
fixes to the tool were made after the measurement, in their own commits.
Changing a prediction after seeing the answer is not an amendment. The dry
runs' outputs were deleted before the measurement, and the launcher refuses a
work root that already holds a `store-a`.

#### What the STOPs point at

- **H2.** All ten paths are made by callers that do not go through the 0700/0600 helpers. `sensorium.ts.driver` creates `<trace root>/spool/<invocation>/` with a bare `mkdir(parents=True, exist_ok=True)` and writes `invocation.json`, `harness.json`, `ingested.json` and `manifests/*.json` with plain `write_text`; `cargo-sensorium`'s `invocation::write_invocation` writes its own `invocation.json` with `std::fs::write`. Each lands 0666/0777-under-the-umask — 0664/0775 on this box — instead of 0600/0700. What DOES hold: every file that carries a recorded environment is 0600 — the TypeScript `<pid>-<n>.jsonl`, the Rust `.spool`, `.proc.json` and `.runner.json` — and the store itself is 0600/0700 throughout, `redaction.key` included. §5.5's claim is categorical, so a file beside the spool that holds argv and config paths at 0664 is a STOP and not a footnote.
- **H3.** Both failing readings are the Rust pair, and both have one cause: `refocus_rust._is_recorder_key` treats EVERY `SENSORIUM_`-prefixed name as the recorder's own bookkeeping and removes it before `refocus_licence.env_of` compares anything. The pre-registered variable is `SENSORIUM_E16_TOKEN`, which is inside that prefix, so on a Rust pair it is never compared: the unchanged pair grants the licence while naming the token on the not-compared list, and the changed pair grants it as well — a rotated secret the Rust licence cannot see. The Python pair read exactly as §1 predicted in both directions, so what failed is the Rust branch's exclusion rule and not rule v1's environment redaction. Two things to rule on, not one: (1) the prefix is wider than the six variables its docstring justifies and silently swallows any `SENSORIUM_`-named variable a user's program actually reads; (2) §1 chose a token name inside that prefix, and no part of the pre-registration noticed — this measurement is where it surfaced.

#### Amendments, beside §1

- **R27, the Rust focus.** §1's block names `--focus compute` "(the case's focused fn; read `corpus/rust/aliasing/questions.yaml` for the name)". That crate has no `compute`; its seeded-bug function is `derive_sandbox`. Corrected clause: **`--focus derive_sandbox`**, in both arms — `corpus/aliasing/main.py` carries a `derive_sandbox` too, so §1's Python `--focus main` is amended the same way and the two arms focus the same function.
- **R27, the TypeScript case.** Decision A10 names `corpus/typescript/aliasing`, which does not exist. Corrected clause: **`corpus/typescript/async_interleaved`**, recorded with `sensorium ts run -- npx vitest run async_interleaved`.
- **The TypeScript spool's location.** The plan's instrument sketch puts it at `store-a/ts-spools`; `sensorium.ts.driver` writes it to `<trace root>/spool/<invocation>/`. The sweep is recursive over the whole work root, so the directory is covered wherever it is, and the tables name it as it actually is.
- **"among the compared" (H3).** §1 predicts the env line "names the redacted variable among the compared". `refocus_world._env_state` never names a compared variable — it counts them and names only what was excluded. Reading applied, stated before the run: the variable is among the compared when the trace recorded it (H6) **and** the env line names it on no exclusion list. The prediction itself is unchanged.
- **The instrument's path.** §1's spec block names the instrument `tests/acceptance/e16.sh`. It is `tests/acceptance_e16/e16a.sh`, with `e16a.py`, `e16a_cells.py` and `assemble_e16a.py` beside it — which is what §1's own plan block already says, the two halves of §1 having been written at different times. Corrected clause: **`tests/acceptance_e16/e16a.sh`**.
- **The grep sweep is wider than §1's.** §1 sweeps the store and the spool directories; this one sweeps everything under the work root except the token file, and for the refocus value as well as the recording one. Wider in the only direction that can find a leak; the gate is still §1's — the recording token, every count 0.

#### Versions

| version | read | §1 expected |
|---|---|---|
| `sensorium` (installed) | 0.15.0 | 0.15.0 |
| `recorder:` on the python trace | sensorium 0.15.0 | sensorium 0.15.0 |
| `recorder:` on the rust trace | sensorium-rt 0.6.0 | sensorium-rt 0.6.0 |
| `recorder:` on the typescript trace | sensorium-ts 0.5.0 | sensorium-ts 0.5.0 |
| `driver_version` on the python trace | (none recorded) | -- |
| `driver_version` on the rust trace | cargo-sensorium 0.7.0 | -- |
| `driver_version` on the typescript trace | 0.15.0 | -- |
| `cargo` under the scrubbed environment | cargo 1.96.0 (30a34c682 2026-05-25) | -- |
| `node` under the scrubbed environment | v24.16.0 | -- |
| `vitest` under the scrubbed environment | vitest/4.1.9 linux-x64 node-v24.16.0 | -- |

#### H1 (environment) — the token's bytes, per file

| file (under `$E16_DIR`) | count, recording token | count, refocus token |
|---|---|---|
| `rust-target/sensorium/spool/20260914-001904-369969/1516676.1.spool` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-369969/1516676.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-369969/1516676.runner.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-369969/invocation.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/1516468.1.spool` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/1516468.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/1516468.runner.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/invocation.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001905-3a131b/1516719.1.spool` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001905-3a131b/1516719.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001905-3a131b/1516719.runner.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-001905-3a131b/invocation.json` | 0 | 0 |
| `store-a/invocations.jsonl` | 0 | 0 |
| `store-a/redaction.key` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/1516515-0.jsonl` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/harness.json` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/ingested.json` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/invocation.json` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/manifests/_tally.json` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__async_interleaved.test.ts.json` | 0 | 0 |
| `store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__store.ts.json` | 0 | 0 |
| `store-a/traces/20260914-001903-871933.db` | 0 | 0 |
| `store-a/traces/20260914-001903-871933.db-shm` | 0 | 0 |
| `store-a/traces/20260914-001903-871933.db-wal` | 0 | 0 |
| `store-a/traces/20260914-001904-03554b.db` | 0 | 0 |
| `store-a/traces/20260914-001904-03554b.db-shm` | 0 | 0 |
| `store-a/traces/20260914-001904-03554b.db-wal` | 0 | 0 |
| `store-a/traces/20260914-001904-aa30cb.db` | 0 | 0 |
| `store-a/traces/20260914-001904-aa30cb.db-shm` | 0 | 0 |
| `store-a/traces/20260914-001904-aa30cb.db-wal` | 0 | 0 |
| `store-a/traces/20260914-001904-f7adae.db` | 0 | 0 |
| `store-a/traces/20260914-001905-04f53e.db` | 0 | 0 |
| `store-a/traces/20260914-001905-28af2f.db` | 0 | 0 |
| `store-a/traces/20260914-001905-bb6ecd.db` | 0 | 0 |
| `a-transcripts/` — 10 further file(s) swept, summarised | max 0 | max 0 |
| `py-case/` — 2 further file(s) swept, summarised | max 0 | max 0 |
| `rust-crate/` — 4 further file(s) swept, summarised | max 0 | max 0 |
| `rust-target/` — 118 further file(s) swept, summarised | max 0 | max 0 |
| `tmp/` — 526 further file(s) swept, summarised | max 0 | max 0 |
| `ts-project/` — 148 further file(s) swept, summarised | max 0 | max 0 |
| `a-out/` — the instrument's own output, 1 file(s), swept but outside §1's scope | max 0 | -- |

#### H2 — the modes

| path (under `$E16_DIR`) | mode | wanted |
|---|---|---|
| `rust-target/sensorium/spool`/ | 700 | 700 |
| `rust-target/sensorium/spool/20260914-001904-424fc9`/ | 700 | 700 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/1516468.1.spool` | 600 | 600 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/1516468.proc.json` | 600 | 600 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/1516468.runner.json` | 600 | 600 |
| `rust-target/sensorium/spool/20260914-001904-424fc9/invocation.json` | 664 | 600  ← **STOP** |
| `store-a`/ | 700 | 700 |
| `store-a/invocations.jsonl` | 600 | 600 |
| `store-a/redaction.key` | 600 | 600 |
| `store-a/spool`/ | 775 | 700  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424`/ | 775 | 700  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/1516515-0.jsonl` | 600 | 600 |
| `store-a/spool/20260914-001904-f6b424/harness.json` | 664 | 600  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/ingested.json` | 664 | 600  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/invocation.json` | 664 | 600  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/manifests`/ | 775 | 700  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/manifests/_tally.json` | 664 | 600  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__async_interleaved.test.ts.json` | 664 | 600  ← **STOP** |
| `store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__store.ts.json` | 664 | 600  ← **STOP** |
| `store-a/traces`/ | 700 | 700 |
| `store-a/traces/20260914-001903-871933.db` | 600 | 600 |
| `store-a/traces/20260914-001904-03554b.db` | 600 | 600 |
| `store-a/traces/20260914-001904-aa30cb.db` | 600 | 600 |

This table and H1's cover different sets, and deliberately: the mode sweep is taken straight after the three recordings and before any query, so it describes what the RECORDERS left — a reader that opens a WAL database creates `-shm`/`-wal` beside it, and those are files the runs did not make. H1's sweep runs last, over everything present at the end, so it also covers the four refocus re-runs' spools and traces, which is why it lists more paths than this.

Swept and listed, outside this cell's scope — the instrument's own directories, and the driver's shared build-support trees under the cargo target directory (their top directories; §1's H2 is a claim about the store and the spools):

| path (under `$E16_DIR`) | mode |
|---|---|
| `.` | 775 |
| `a-out` | 775 |
| `a-transcripts` | 775 |
| `py-case` | 775 |
| `rust-crate` | 775 |
| `rust-target` | 775 |
| `rust-target/sensorium` | 775 |
| `rust-target/sensorium/cache` | 775 |
| `rust-target/sensorium/manifests` | 775 |
| `rust-target/sensorium/mirror` | 775 |
| `rust-target/sensorium/rt` | 775 |
| `rust-target/sensorium/shim` | 775 |
| `ts-project` | 775 |

#### H3 — the four refocus readings

**python-unchanged** — predicted granted, as predicted. Exit 0, 0.108s.

```
env: unchanged (7 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _)
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: verified against 20260914-001903-871933 on exactly these points, and no others:
```

**rust-unchanged** — predicted granted, **the other way**. Exit 0, 0.18s.

```
env: unchanged (32 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _)  the recorder's own fragment stripped before comparing: RUSTDOCFLAGS  the recorder's own, also not compared: CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER, RUSTC_WORKSPACE_WRAPPER, SENSORIUM_E16_TOKEN, SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_RT_DIR, SENSORIUM_SPOOL, SENSORIUM_TARGET, SENSORIUM_TIER, SENSORIUM_TOOL_HASH, SENSORIUM_WS
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: verified against 20260914-001904-03554b on exactly these points, and no others:
```

> predicted a granted licence with SENSORIUM_E16_TOKEN among the compared; read licence granted, env unchanged, token named on the env line: True, token in the recorded environment: True

**python-changed** — predicted WITHHELD, as predicted. Exit 0, 0.097s.

```
env: CHANGED since the original run -- 1 variable(s) differ: SENSORIUM_E16_TOKEN   (names only)
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: WITHHELD -- this MATCH is about call shape, and these checks say it is not a statement about the run as a whole:
```

**rust-changed** — predicted WITHHELD, **the other way**. Exit 0, 0.111s.

```
env: unchanged (32 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _)  the recorder's own fragment stripped before comparing: RUSTDOCFLAGS  the recorder's own, also not compared: CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER, RUSTC_WORKSPACE_WRAPPER, SENSORIUM_E16_TOKEN, SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_RT_DIR, SENSORIUM_SPOOL, SENSORIUM_TARGET, SENSORIUM_TIER, SENSORIUM_TOOL_HASH, SENSORIUM_WS
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: verified against 20260914-001904-03554b on exactly these points, and no others:
```

> predicted WITHHELD with SENSORIUM_E16_TOKEN in the changed list; read licence granted, env unchanged, token in the changed list: False


#### H6 (`redaction.env`) — the names

| trace | arm | vars stored | `redaction.env` names |
|---|---|---|---|
| `20260914-001903-871933` | python | 8 | `SENSORIUM_E16_TOKEN` |
| `20260914-001904-03554b` | rust | 44 | `SENSORIUM_E16_TOKEN` |
| `20260914-001904-aa30cb` | typescript | 50 | `SENSORIUM_E16_TOKEN` |

#### Phases

| phase | seconds |
|---|---|
| preflight | 0.218 |
| mint | 0.0 |
| copies | 0.004 |
| record-python | 0.097 |
| record-rust | 0.384 |
| record-typescript | 0.507 |
| modes | 0.015 |
| info-pre | 0.141 |
| refocus | 0.497 |
| versions | 0.009 |
| grep | 0.028 |

### measured 2026-09-14 — run 2, after the H2 and H3 fixes

Measured once, on this box, under `e16a.sh`. **Part A: DONE** — H1 PASS  H2 PASS  H3 PASS  H6 PASS. The token was `sk-e16-` plus 33 characters, minted by the instrument, never printed and never committed: `sha256(token)[:8] = a4badc8d`, and the value H3 re-exported `496d48cd`. Every recording and every refocus ran under a scrubbed environment of exactly `PATH`, `HOME`, `USER`, `LANG`, `TMPDIR`, `CARGO_TARGET_DIR`, `SENSORIUM_DIR`, `SENSORIUM_E16_TOKEN` — no other name reached a recorder, and the instrument refuses to start unless none of them fires rule v1, which is what makes H6's "exactly one name" a fact about the token. 1.9s wall clock.

| cell | word | §9's rule | what was read |
|---|---|---|---|
| H1 (environment) | **PASS** | every count 0 where 0 is required | 1033 file(s) examined, every count 0 |
| H2 | **PASS** | all | 23 path(s) in scope, every file 600 and directory 700 |
| H3 | **PASS** | both | all 4 pair(s) read as predicted |
| H6 (`redaction.env`) | **PASS** | exact | 3 trace(s), each redacting exactly SENSORIUM_E16_TOKEN |
| H1-values | dropped | -- | part B |
| H4 | dropped | -- | part C |
| H5 | dropped | -- | part B |
| H6-values | dropped | -- | part B |

#### Pins

| pin | path |
|---|---|
| work root | `E16_DIR=/mnt/extra/sensorium-rung2/e16` |
| store | `$E16_DIR/store-a2` |
| transcripts | `$E16_DIR/a2-transcripts/` |
| Python case copy | `$E16_DIR/py-case-a2/` |
| crate copy | `$E16_DIR/rust-crate-a2/` |
| vitest project copy | `$E16_DIR/ts-project-a2/` |
| cargo target | `$E16_DIR/rust-target/` |
| instrument output | `$E16_DIR/a2-out/` |
| driver (the committed transcripts' label) | `$DRIVER_DIR` — the release `cargo-sensorium`'s own directory, outside the work root |

#### Against run 1 — which run is the first PASS

- **H1 (environment)** passed in run 1 and reads **PASS** here.
- **H2 — this run is the first PASS.** The run before it read STOP: 10 path(s) carry another mode: 775 store-a/spool (want 700), 775 store-a/spool/20260914-001904-f6b424 (want 700), 775 store-a/spool/20260914-001904-f6b424/manifests (want 700), 664 store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__async_interleaved.test.ts.json (want 600), 664 store-a/spool/20260914-001904-f6b424/manifests/async_interleaved__store.ts.json (want 600), 664 store-a/spool/20260914-001904-f6b424/manifests/_tally.json (want 600), 664 store-a/spool/20260914-001904-f6b424/harness.json (want 600), 664 store-a/spool/20260914-001904-f6b424/ingested.json (want 600), 664 store-a/spool/20260914-001904-f6b424/invocation.json (want 600), 664 rust-target/sensorium/spool/20260914-001904-424fc9/invocation.json (want 600). Fixed by `6a719e4` (the TypeScript driver's spool, manifests and records, and the Rust invocation record, 0700/0600) and `e36d5dd` (`db.py`'s traces creator). This run reads: 23 path(s) in scope, every file 600 and directory 700.
- **H3 — this run is the first PASS.** The run before it read STOP: 2 of 4 pair(s) read the other way: rust-unchanged: predicted a granted licence with SENSORIUM_E16_TOKEN among the compared; read licence granted, env unchanged, token named on the env line: True, token in the recorded environment: True; rust-changed: predicted WITHHELD with SENSORIUM_E16_TOKEN in the changed list; read licence granted, env unchanged, token in the changed list: False. Fixed by `1f60dd6` and `9d8f16a` (the refocus branches' recorder keys are exact sets of what each driver SETS, not a `SENSORIUM_` prefix). This run reads: all 4 pair(s) read as predicted.
- **H6 (`redaction.env`)** passed in run 1 and reads **PASS** here.

#### The dry run

Before the measurement, with a `dry-` decoy that cannot match the content rule and every timer at 60 s, into a work root of its own that was deleted afterwards. What it found, and what changed in the instrument between it and the run above:

- `build-driver` raised `KeyError: 'build'` — the new phase asked for a timer `TIMERS` did not have — and `phase()` swallowed it into the phase's `error` field, so the run went on to record with the unrebuilt binary and reported `DONE`. A rebuild that is not a refusal is not a rebuild. Fixed before the measurement in `10bdc18`: the timer table gained `build`, and `phase(..., critical=True)` turns any exception in a PRECONDITION phase — `build-driver` and `preflight` — into a refusal that ends the run. A measurement phase still leaves `None` and drops its cell.
- Rendering the dry run's raw record showed two prose defects, both fixed in the same commit: a cell's `why` is a table clause with no full stop and swallowed the sentence after it when run into §2's prose, and cargo's own `Finished \`release\` profile` line carries backticks that ended the code span around it early.
- Everything the reader opens existed and parsed: `driver_build` stamped with the binary's labelled path, mtime, size and cargo's `Finished` line; `h2_roots` naming `store-a2` and `rust-target/sensorium/spool`, both `ok`; `arm` on every H6 row; all ten transcripts written; and the section rendered whole from a copy of the dry raw with the flag flipped, `offenders()` empty.
- The dry run's own outputs, its store and its cargo target were deleted before the measurement, together with run 1's `rust-target` — the launcher now refuses a work root whose `rust-target/sensorium/spool` holds an earlier run's spools, because they would be swept as if this run's recorders had made them.
- One launch of the measurement was discarded UNREAD before this one: it was started without `E16_DRY_FINDINGS`, so it would have carried no dry-run reading at all. Its store, out directory, transcripts, copies and token were deleted without its log or results being opened, and this run was made from zero with a freshly minted token.

#### Amendments, beside §1

- **R27, the Rust focus.** §1's block names `--focus compute` "(the case's focused fn; read `corpus/rust/aliasing/questions.yaml` for the name)". That crate has no `compute`; its seeded-bug function is `derive_sandbox`. Corrected clause: **`--focus derive_sandbox`**, in both arms — `corpus/aliasing/main.py` carries a `derive_sandbox` too, so §1's Python `--focus main` is amended the same way and the two arms focus the same function.
- **R27, the TypeScript case.** Decision A10 names `corpus/typescript/aliasing`, which does not exist. Corrected clause: **`corpus/typescript/async_interleaved`**, recorded with `sensorium ts run -- npx vitest run async_interleaved`.
- **The TypeScript spool's location.** The plan's instrument sketch puts it at `store-a/ts-spools`; `sensorium.ts.driver` writes it to `<trace root>/spool/<invocation>/`. The sweep is recursive over the whole work root, so the directory is covered wherever it is, and the tables name it as it actually is.
- **"among the compared" (H3).** §1 predicts the env line "names the redacted variable among the compared". `refocus_world._env_state` never names a compared variable — it counts them and names only what was excluded. Reading applied, stated before the run: the variable is among the compared when the trace recorded it (H6) **and** the env line names it on no exclusion list. The prediction itself is unchanged.
- **The instrument's path.** §1's spec block names the instrument `tests/acceptance/e16.sh`. It is `tests/acceptance_e16/e16a.sh`, with `e16a.py`, `e16a_cells.py` and `assemble_e16a.py` beside it — which is what §1's own plan block already says, the two halves of §1 having been written at different times. Corrected clause: **`tests/acceptance_e16/e16a.sh`**.
- **The grep sweep is wider than §1's.** §1 sweeps the store and the spool directories; this one sweeps everything under the work root except the token file, and for the refocus value as well as the recording one. Wider in the only direction that can find a leak; the gate is still §1's — the recording token, every count 0.

#### Versions

**Driver built by the run (R37):** `cargo build --release -p cargo-sensorium` in 0.03s before anything was recorded; `$DRIVER_DIR/cargo-sensorium`, 7219552 bytes, mtime 2026-09-14T01:02:58. cargo said: Finished `release` profile [optimized] target(s) in 0.01s

| version | read | §1 expected |
|---|---|---|
| `sensorium` (installed) | 0.15.0 | 0.15.0 |
| `recorder:` on the python trace | sensorium 0.15.0 | sensorium 0.15.0 |
| `recorder:` on the rust trace | sensorium-rt 0.6.0 | sensorium-rt 0.6.0 |
| `recorder:` on the typescript trace | sensorium-ts 0.5.0 | sensorium-ts 0.5.0 |
| `driver_version` on the python trace | (none recorded) | -- |
| `driver_version` on the rust trace | cargo-sensorium 0.7.0 | -- |
| `driver_version` on the typescript trace | 0.15.0 | -- |
| `cargo` under the scrubbed environment | cargo 1.96.0 (30a34c682 2026-05-25) | -- |
| `node` under the scrubbed environment | v24.16.0 | -- |
| `vitest` under the scrubbed environment | vitest/4.1.9 linux-x64 node-v24.16.0 | -- |

#### H1 (environment) — the token's bytes, per file

| file (under `$E16_DIR`) | count, recording token | count, refocus token |
|---|---|---|
| `rust-target/sensorium/spool/20260914-013409-6e9bda/1725510.1.spool` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/1725510.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/1725510.runner.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/invocation.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-07f558/1725732.1.spool` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-07f558/1725732.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-07f558/1725732.runner.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-07f558/invocation.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-6c53ac/1725800.1.spool` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-6c53ac/1725800.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-6c53ac/1725800.runner.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-013410-6c53ac/invocation.json` | 0 | 0 |
| `store-a2/invocations.jsonl` | 0 | 0 |
| `store-a2/redaction.key` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/1725556-0.jsonl` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/harness.json` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/ingested.json` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/invocation.json` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/manifests/_tally.json` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/manifests/async_interleaved__async_interleaved.test.ts.json` | 0 | 0 |
| `store-a2/spool/20260914-013409-bda173/manifests/async_interleaved__store.ts.json` | 0 | 0 |
| `store-a2/traces/20260914-013409-b4033a.db` | 0 | 0 |
| `store-a2/traces/20260914-013409-b4033a.db-shm` | 0 | 0 |
| `store-a2/traces/20260914-013409-b4033a.db-wal` | 0 | 0 |
| `store-a2/traces/20260914-013409-bdc9a0.db` | 0 | 0 |
| `store-a2/traces/20260914-013409-bdc9a0.db-shm` | 0 | 0 |
| `store-a2/traces/20260914-013409-bdc9a0.db-wal` | 0 | 0 |
| `store-a2/traces/20260914-013410-511dc8.db` | 0 | 0 |
| `store-a2/traces/20260914-013410-6dca36.db` | 0 | 0 |
| `store-a2/traces/20260914-013410-b5779c.db` | 0 | 0 |
| `store-a2/traces/20260914-013410-b5779c.db-shm` | 0 | 0 |
| `store-a2/traces/20260914-013410-b5779c.db-wal` | 0 | 0 |
| `store-a2/traces/20260914-013410-d4459c.db` | 0 | 0 |
| `store-a2/traces/20260914-013410-fad347.db` | 0 | 0 |
| `a-out/` — 4 further file(s) swept, summarised | max 0 | max 0 |
| `a-transcripts/` — 10 further file(s) swept, summarised | max 0 | max 0 |
| `a2-transcripts/` — 11 further file(s) swept, summarised | max 0 | max 0 |
| `py-case/` — 2 further file(s) swept, summarised | max 0 | max 0 |
| `py-case-a2/` — 2 further file(s) swept, summarised | max 0 | max 0 |
| `rust-crate/` — 4 further file(s) swept, summarised | max 0 | max 0 |
| `rust-crate-a2/` — 4 further file(s) swept, summarised | max 0 | max 0 |
| `rust-target/` — 118 further file(s) swept, summarised | max 0 | max 0 |
| `store-a/` — 22 further file(s) swept, summarised | max 0 | max 0 |
| `tmp/` — 526 further file(s) swept, summarised | max 0 | max 0 |
| `ts-project/` — 148 further file(s) swept, summarised | max 0 | max 0 |
| `ts-project-a2/` — 148 further file(s) swept, summarised | max 0 | max 0 |
| `a2-out/` — the instrument's own output, 1 file(s), swept but outside §1's scope | max 0 | -- |

#### H2 — the modes

| path (under `$E16_DIR`) | mode | wanted |
|---|---|---|
| `rust-target/sensorium/spool`/ | 700 | 700 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda`/ | 700 | 700 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/1725510.1.spool` | 600 | 600 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/1725510.proc.json` | 600 | 600 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/1725510.runner.json` | 600 | 600 |
| `rust-target/sensorium/spool/20260914-013409-6e9bda/invocation.json` | 600 | 600 |
| `store-a2`/ | 700 | 700 |
| `store-a2/invocations.jsonl` | 600 | 600 |
| `store-a2/redaction.key` | 600 | 600 |
| `store-a2/spool`/ | 700 | 700 |
| `store-a2/spool/20260914-013409-bda173`/ | 700 | 700 |
| `store-a2/spool/20260914-013409-bda173/1725556-0.jsonl` | 600 | 600 |
| `store-a2/spool/20260914-013409-bda173/harness.json` | 600 | 600 |
| `store-a2/spool/20260914-013409-bda173/ingested.json` | 600 | 600 |
| `store-a2/spool/20260914-013409-bda173/invocation.json` | 600 | 600 |
| `store-a2/spool/20260914-013409-bda173/manifests`/ | 700 | 700 |
| `store-a2/spool/20260914-013409-bda173/manifests/_tally.json` | 600 | 600 |
| `store-a2/spool/20260914-013409-bda173/manifests/async_interleaved__async_interleaved.test.ts.json` | 600 | 600 |
| `store-a2/spool/20260914-013409-bda173/manifests/async_interleaved__store.ts.json` | 600 | 600 |
| `store-a2/traces`/ | 700 | 700 |
| `store-a2/traces/20260914-013409-b4033a.db` | 600 | 600 |
| `store-a2/traces/20260914-013409-bdc9a0.db` | 600 | 600 |
| `store-a2/traces/20260914-013410-b5779c.db` | 600 | 600 |

This table and H1's cover different sets, and deliberately: the mode sweep is taken straight after the three recordings and before any query, so it describes what the RECORDERS left — a reader that opens a WAL database creates `-shm`/`-wal` beside it, and those are files the runs did not make. H1's sweep runs last, over everything present at the end, so it also covers the four refocus re-runs' spools and traces, which is why it lists more paths than this.

Swept and listed, outside this cell's scope — the instrument's own directories, and the driver's shared build-support trees under the cargo target directory (their top directories; §1's H2 is a claim about the store and the spools):

| path (under `$E16_DIR`) | mode |
|---|---|
| `.` | 775 |
| `a2-out` | 775 |
| `a2-transcripts` | 775 |
| `py-case-a2` | 775 |
| `rust-crate-a2` | 775 |
| `rust-target` | 775 |
| `rust-target/sensorium` | 775 |
| `rust-target/sensorium/cache` | 775 |
| `rust-target/sensorium/manifests` | 775 |
| `rust-target/sensorium/mirror` | 775 |
| `rust-target/sensorium/rt` | 775 |
| `rust-target/sensorium/shim` | 775 |
| `ts-project-a2` | 775 |

#### H3 — the four refocus readings

**python-unchanged** — predicted granted, as predicted. Exit 0, 0.097s.

```
env: unchanged (7 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _)
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: verified against 20260914-013409-bdc9a0 on exactly these points, and no others:
```

**rust-unchanged** — predicted granted, as predicted. Exit 0, 0.182s.

```
env: unchanged (33 variables compared; not compared: OLDPWD, PWD, SENSORIUM_DIR, SHLVL, _)  the recorder's own fragment stripped before comparing: RUSTDOCFLAGS  the recorder's own, also not compared: CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER, RUSTC_WORKSPACE_WRAPPER, SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_RT_DIR, SENSORIUM_SPOOL, SENSORIUM_TARGET, SENSORIUM_TIER, SENSORIUM_TOOL_HASH, SENSORIUM_WS
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: verified against 20260914-013409-b4033a on exactly these points, and no others:
```

**python-changed** — predicted WITHHELD, as predicted. Exit 0, 0.097s.

```
env: CHANGED since the original run -- 1 variable(s) differ: SENSORIUM_E16_TOKEN   (names only)
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: WITHHELD -- this MATCH is about call shape, and these checks say it is not a statement about the run as a whole:
```

**rust-changed** — predicted WITHHELD, as predicted. Exit 0, 0.111s.

```
env: CHANGED since the original run -- 1 variable(s) differ: SENSORIUM_E16_TOKEN   (names only)  the recorder's own fragment stripped before comparing: RUSTDOCFLAGS  the recorder's own, also not compared: CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_RUNNER, RUSTC_WORKSPACE_WRAPPER, SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_RT_DIR, SENSORIUM_SPOOL, SENSORIUM_TARGET, SENSORIUM_TIER, SENSORIUM_TOOL_HASH, SENSORIUM_WS
refocus verdict: MATCH -- every recorded thread produced the identical CALL/RETURN/RAISE/HANDLED sequence
licence: WITHHELD -- this MATCH is about call shape, and these checks say it is not a statement about the run as a whole:
```


#### H6 (`redaction.env`) — the names

| trace | arm | vars stored | `redaction.env` names |
|---|---|---|---|
| `20260914-013409-bdc9a0` | python | 8 | `SENSORIUM_E16_TOKEN` |
| `20260914-013409-b4033a` | rust | 44 | `SENSORIUM_E16_TOKEN` |
| `20260914-013410-b5779c` | typescript | 50 | `SENSORIUM_E16_TOKEN` |

#### Phases

| phase | seconds |
|---|---|
| build-driver | 0.031 |
| preflight | 0.218 |
| mint | 0.0 |
| copies | 0.004 |
| record-python | 0.096 |
| record-rust | 0.372 |
| record-typescript | 0.497 |
| modes | 0.015 |
| info-pre | 0.139 |
| refocus | 0.488 |
| versions | 0.009 |
| grep | 0.033 |

## 3. Part B

Not yet measured.
