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

### 2026-09-15 — Part C's pre-registration (amendment, beside the locked text above)

- **Part C's cell is H4 in full**, on a COPY of this box's `~/.sensorium/traces` — the store §9 names, 273 traces when §9 was written; the copy's own count is recorded in §4 and H4 is read over every trace the copy holds. H1, H2, H3 and H6 were parts A's and B's (measured, DONE); H5 was part B's. Each is written into the results file as `dropped` with the part that owns it. §9's H4 row stands: PASS iff `redact --all --dry-run` on the copy reports every trace holding `CLAUDE_CODE_MESSAGING_TOKEN` plaintext, `redact --all` on the copy leaves `grep -c` of that token's value at 0 across every file, every trace still opens (`info` exit 0), and the count line matches the dry run; STOP on any residue, any trace that no longer opens, or dry-run ≠ real.
- **The token is not minted.** It is the value of `CLAUDE_CODE_MESSAGING_TOKEN` in the copy's own traces, read by the instrument from the first trace's `meta.env` through a read-only connection, held in memory, never printed and never written by the instrument anywhere but its own `grep` argument; the record cites its `sha256` first 8 hex. The rehearsal (`E16_DRY=1`) runs the same phases on a fabricated store of three synthetic traces carrying `dry-` + 4 characters in the same variable, one `str` RETURN, one output row and one `children` element, and never touches the live store's copy.
- **H4's reading, clause by clause:** (1) the dry run's stdout parsed line by line — `run <id>: env <n> redacted (<names>); values <n>; mode <a> -> <b>` — and the set of `<id>` whose `<names>` contains `CLAUDE_CODE_MESSAGING_TOKEN` must equal the set of `*.db` stems in the copy; (2) `grep -rc --binary-files=text -F <value>` over `store-c/` after the real run, per file, every count 0 (a `-wal`/`-shm` that no longer exists is 0 by absence; `redaction.key` and `invocations.jsonl` are in the sweep); (3) `sensorium info <id>` for every stem, exit 0 and the `redaction:` line containing `by retrofit`; (4) the two captured stdouts compared as bytes. The count-before phase is a PRECONDITION: every `*.db` in the copy must hold the value at least once before the run, else the copy is not the store §9 describes and the run refuses.
- **Reported, not gated:** the copy's trace count beside §9's 273; the summary line verbatim (it carries no path); every file's mode after (`stat -c %a`) and `traces/`'s; the number of `-wal`/`-shm` files before and after; the wall time of the dry run and the real run; `values` totals summed over the dry-run lines.
- **Locations** are the record's §4 pin table only: `E16C_DIR=/mnt/extra/sensorium-rung2/e16c`, the copy `$E16C_DIR/store-c`, transcripts `$E16C_DIR/c-transcripts/`, instrument output `$E16C_DIR/c-out/`, the rehearsal's own root `$E16C_DIR-dry`. Part A's and B's trees under `/mnt/extra/sensorium-rung2/e16` were freed 2026-09-15 (evidence archived) and are not read.
- **Versions expected:** the venv's `sensorium` reads **0.17.0** (`importlib.metadata`), and every retrofitted trace's `redaction.by` reads `retrofit`; the traces' own `recorder` strings are whatever they were and §4 records their distribution (§13(a): 251 `sensorium-rt`, 19 Python, 3 `sensorium-ts`).
- **Kill rules:** the copy 600 s, each `redact` run 900 s, the `info` sweep 900 s, each grep 300 s, the part 45 min; a kill is an infrastructure event, rerun from zero on a FRESH copy.

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

### measured 2026-09-14

Measured once, on this box, under `e16b.sh`. **Part B: DONE** — H1 (values) PASS  H5 (overhead) measured  H6 (`redaction.values`) PASS. The token was `sk-e16-` plus 33 characters, minted by the instrument, never printed and never committed: `sha256(token)[:8] = 7785be0f`. Every recording ran under a scrubbed environment of exactly `PATH`, `HOME`, `USER`, `LANG`, `TMPDIR`, `CARGO_TARGET_DIR`, `SENSORIUM_DIR`, `SENSORIUM_E16_TOKEN` — no other name reached a recorder, and the instrument refuses to start unless none of them fires rule v1, which is what makes H6's "exactly one name" a fact about the token. The two bench tables ran with the token OUT of the environment: H5 is a measurement of overhead, and a secret in a tree H1 does not sweep is a secret nobody checked. 85.3s wall clock.

| cell | word | §9's rule | what was read |
|---|---|---|---|
| H1 (values) | **PASS** | every count 0 where 0 is required | 20 file(s) examined: every count 0 under the store, in every proc header and in the TypeScript spool, and exactly 3 occurrence(s) in the Rust spools; 762 further file(s) swept outside the four readings (not gated), none holding the token |
| H5 (overhead) | **measured** | n/a — an outlier ratio is a finding for CARRIED-DEBT, not a stop | 7 workload row(s); both tables parsed |
| H6 (`redaction.values`) | **PASS** | exact | 3 trace(s): python 5, rust 4, typescript 4, each redacting exactly SENSORIUM_E16_TOKEN |
| H1-env | dropped | -- | part A |
| H2 | dropped | -- | part A |
| H3 | dropped | -- | part A |
| H4 | dropped | -- | part C |
| H6-env | dropped | -- | part A |

#### Pins

| pin | path |
|---|---|
| work root | `E16_DIR=/mnt/extra/sensorium-rung2/e16` |
| store | `$E16_DIR/store-b` |
| transcripts | `$E16_DIR/b-transcripts/` |
| Python case copy | `$E16_DIR/py-case-b/` |
| crate copy | `$E16_DIR/rust-crate-b/` |
| vitest project copy | `$E16_DIR/ts-project-b/` |
| cargo target | `$E16_DIR/rust-target/` |
| instrument output | `$E16_DIR/b-out/` |
| baseline worktree (`7dd25d2`) | `$E16_DIR/baseline-7dd25d2/` |
| bench scratch store | `$E16_DIR/bench-b/` |
| driver (the committed transcripts' label) | `$DRIVER_DIR` — the release `cargo-sensorium`'s own directory, outside the work root |

#### The dry run

Before the measurement, with a `dry-` decoy that cannot match the content rule and the recordings capped at 60 s, each bench table at 300 s, the driver build at 1800 s and the baseline worktree at 600 s, into a work root of its own that was deleted afterwards. What it found, and what changed in the instrument between it and the run above:

- Three dry runs preceded the measurement, into a work root of their own -- its own store, cargo target directory, baseline worktree and case copies, all deleted afterwards -- with a `dry-` plus four decoy that cannot match the content rule, the recordings capped at 60 s, each bench table at 300 s and the benchmark at `reps=1`. Every phase completed, every artifact path the reader opens existed and parsed, and the assembler refused the dry raw record by name (`dry_run: true`), which is the refusal the dry run exists to exercise; a copy with the flag flipped rendered every section with `offenders()` empty.
- The decoy's census read the NAME rows alone and exactly as predicted -- Python 4, TypeScript 2, Rust 2 -- and its complement was visible in the same sweep: the Python trace held the decoy once (the `print` chunk), the Rust and TypeScript traces twice each (`copy` and the header value), and the Rust `.spool` files three times together. 4+1, 2+2 and 2+2 are §1's amendment's 5, 4 and 4, so every row it counts is where it says it is and the content rule is the only thing that can reach three of them.
- The TypeScript spool directory lives UNDER the store, so every file in it is in two of §1's four readings: the cell named one offender twice and reported 27 readings as 27 files examined where the sweep had looked at 20. Both the cell and §3's table now answer per FILE and name the readings each file belongs to.
- H5's command line was built from the `BENCH_REPS` constant and printed `reps=5` directly above evidence reading `best of 1 timed runs`. The reps are read off the run now, and the cell's own sentence no longer claims a number it cannot see.
- The `driver_version` expectation for the Rust trace was spelled `0.8.0` beside a read of `cargo-sensorium 0.8.0` -- a difference where there is none -- and an em dash in H1's prose rendered as two hyphens. Both corrected. From self-review beside them: a `versions` phase that left `None` crashed the renderer instead of dropping the block in words.
- A fourth dry run, after the task review: the sweep had held back the whole Rust spool tree from the `rust-target/` reading, so `<pid>.runner.json` and `invocation.json` were in no grep set; only the gated `.proc.json` and `.spool` files are held back now, the two land in the other-sweep table (both read 0 on the decoy), and `mint` became a precondition.
- Nothing else was altered in response to what the dry runs read. No prediction, no constant, no cell and no line of `sensorium` changed: `RULES`, `EXPECTED_VALUES`, `SPOOL_OCCURRENCES`, `DRY_NAME_ROWS` and the token's name went into the run exactly as §1's amendment fixed them.

#### Amendments, beside §1

- **R11, the Python probe's focus.** §1's part B block records the Python probe with `sensorium run --focus handle -- main.py`. A bare `--focus handle` names a MODULE: `FocusSpec` splits each entry on `:` into `module` and an optional `qualname` (`record/tracer_frames.py`), so `handle` alone matches only code whose module is called `handle` — nothing in `main.py` — and the recording would carry no LINE deltas at all, which is three of the five rows §1 counts. Corrected clause: **`sensorium run --focus main:handle -- main.py`**, which is how `corpus/secret_in_env/questions.yaml` spells the same focus for the corpus's own case. The Rust arm (`cargo sensorium --focus handle run`) and the TypeScript arm (`--focus handle`) are unchanged: neither recorder's focus spec is module-qualified.
- **The TypeScript project copy omits `corpus/typescript/secret_in_env`.** §1 records the TypeScript probe with `npx vitest run secret`, and vitest's positional filter is a SUBSTRING match over test file paths: the corpus's own `secret_in_env/secret_in_env.test.ts` matches it as surely as the probe's `e16_probe/secret.test.ts` does. Both would be recorded into one trace and that case's four planted rows counted into the probe's census of four. The disposable copy therefore leaves that one case directory out; the command, the probe and the predicted count are unchanged. (The probe is copied into a SUBDIRECTORY for the same reason it is copied at all: the corpus project's `vitest.config.ts` includes `*/**/*.test.ts`, which a file at the project root does not match.)

#### Versions

**Driver built by the run (R37):** `cargo build --release -p cargo-sensorium` in 0.151s before anything was recorded; `$DRIVER_DIR/cargo-sensorium`, 9737152 bytes, mtime 2026-09-14T16:46:30. cargo said: Finished `release` profile [optimized] target(s) in 0.10s

| version | read | §1 expected |
|---|---|---|
| `sensorium` (installed) | 0.16.0 | 0.16.0 |
| `recorder:` on the python trace | sensorium 0.16.0 | sensorium 0.16.0 |
| `recorder:` on the rust trace | sensorium-rt 0.7.0 | sensorium-rt 0.7.0 |
| `recorder:` on the typescript trace | sensorium-ts 0.6.0 | sensorium-ts 0.6.0 |
| `driver_version` on the python trace | (none recorded) | -- |
| `driver_version` on the rust trace | cargo-sensorium 0.8.0 | cargo-sensorium 0.8.0 |
| `driver_version` on the typescript trace | 0.16.0 | -- |
| `cargo` under the scrubbed environment | cargo 1.96.0 (30a34c682 2026-05-25) | -- |
| `node` under the scrubbed environment | v24.16.0 | -- |
| `vitest` under the scrubbed environment | vitest/4.1.9 linux-x64 node-v24.16.0 | -- |
| `python` in the `7dd25d2` worktree | Python 3.13.13 | -- |

#### H1 (values) — the token's bytes, per file

| file (under `$E16_DIR`) | set | occurrences | required |
|---|---|---|---|
| `store-b/invocations.jsonl` | every file under the store | 0 | 0 |
| `store-b/redaction.key` | every file under the store | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/4057260-0.jsonl` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/harness.json` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/ingested.json` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/invocation.json` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/manifests/_tally.json` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/manifests/e16_probe__secret.test.ts.json` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/spool/20260914-180856-2bbfe9/manifests/e16_probe__secret.ts.json` | every file under the store + TypeScript spool | 0 | 0 |
| `store-b/traces/20260914-180856-948ced.db` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180856-948ced.db-shm` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180856-948ced.db-wal` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180856-d41cc8.db` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180856-d41cc8.db-shm` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180856-d41cc8.db-wal` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180857-5e0231.db` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180857-5e0231.db-shm` | every file under the store | 0 | 0 |
| `store-b/traces/20260914-180857-5e0231.db-wal` | every file under the store | 0 | 0 |
| `rust-target/sensorium/spool/20260914-180856-fae745/4057202.proc.json` | Rust `<pid>.proc.json` | 0 | 0 |
| `rust-target/sensorium/spool/20260914-180856-fae745/4057202.1.spool` | Rust `.spool` | 3 | 3 together |

The Rust `.spool` files hold 3 occurrence(s) together, against the 3 §1's amendment predicts: the three rows the CONVERTER redacts (`copy`, the `Headers` `Debug` text and `secret`'s RETURN) are plaintext in the spool until it runs, and the fourth Rust row — the `token` parameter delta — is taken by the recorder before the spool is written.

Swept and listed, outside the four readings and gated by none of them — the disposable copies, the transcripts, the cargo build tree (the two Rust spool files §1's amendment does not name among them: `<pid>.runner.json` and `invocation.json`), the TMPDIR every recording ran under and this instrument's own output, by top directory:

| path (under `$E16_DIR`) | files swept | max occurrences |
|---|---|---|
| `b-out/` | 1 | 0 |
| `b-transcripts/` | 10 | 0 |
| `py-case-b/` | 1 | 0 |
| `rust-crate-b/` | 3 | 0 |
| `rust-target/` | 71 | 0 |
| `tmp/` | 526 | 0 |
| `ts-project-b/` | 150 | 0 |

#### H5 — the overhead, before and after

`python -c "from corpus._bench import bench; bench.report(reps=5)"`, in each tree, back to back on this box.

**At `7dd25d2`:**

```
workload            tier      baseline  recorded       x    events  us/event
call_dense          default     0.0087    1.4707   168.6    185428       7.9
call_dense          focused     0.0086    2.0526   238.2    278140       7.3
work_between_calls  default     0.1427    0.4040     2.8     24004      10.9
work_between_calls  focused     0.1436    0.5680     4.0     48006       8.8
async_call_dense    default     0.0264    0.3929    14.9     40004       9.2
async_call_dense    focused  n/a  (no focus target registered for this workload)
await_dense         default     0.0459    0.3164     6.9     40004       6.8
await_dense         focused     0.0455    0.4756    10.5     60005       7.2

recorder fixed cost: 0.080s on a program that does nothing (0.0073s -> 0.0868s).
  Every row above includes it, so a short program's multiplier is mostly this.
best of 5 timed runs after one untimed warm-up; python 3.13.13.
  Measurements of THIS machine and these workloads, not a promise about yours: the
  multiplier tracks how call-dense the program is, and us/event is the figure that travels.
```

**At HEAD (this branch):**

```
workload            tier      baseline  recorded       x    events  us/event
call_dense          default     0.0089    1.7501   197.0    185428       9.4
call_dense          focused     0.0086    2.4674   287.5    278140       8.8
work_between_calls  default     0.1415    0.4761     3.4     24004      13.9
work_between_calls  focused     0.1421    0.7837     5.5     48006      13.4
async_call_dense    default     0.0266    0.4605    17.3     40004      10.8
async_call_dense    focused  n/a  (no focus target registered for this workload)
await_dense         default     0.0457    0.3317     7.3     40004       7.1
await_dense         focused     0.0462    0.5708    12.4     60005       8.7

recorder fixed cost: 0.082s on a program that does nothing (0.0071s -> 0.0894s).
  Every row above includes it, so a short program's multiplier is mostly this.
best of 5 timed runs after one untimed warm-up; python 3.13.13.
  Measurements of THIS machine and these workloads, not a promise about yours: the
  multiplier tracks how call-dense the program is, and us/event is the figure that travels.
```

| workload | tier | recorded/baseline at `7dd25d2` | recorded/baseline at HEAD | HEAD over `7dd25d2` |
|---|---|---|---|---|
| async_call_dense | default | 14.88 | 17.31 | 1.16 |
| await_dense | default | 6.89 | 7.26 | 1.05 |
| await_dense | focused | 10.45 | 12.35 | 1.18 |
| call_dense | default | 169.05 | 196.64 | 1.16 |
| call_dense | focused | 238.67 | 286.91 | 1.20 |
| work_between_calls | default | 2.83 | 3.36 | 1.19 |
| work_between_calls | focused | 3.96 | 5.52 | 1.39 |

Never gated (§9, and rust/HONESTY.md §10: cost is reported, never gated). An outlier is a CARRIED-DEBT finding, not a stop.

#### H6 (`redaction.values`) — the census

| trace | arm | `values redacted:` | §1 expected | `redaction.env` names |
|---|---|---|---|---|
| `20260914-180856-948ced` | python | 5 | 5 | `SENSORIUM_E16_TOKEN` |
| `20260914-180856-d41cc8` | rust | 4 | 4 | `SENSORIUM_E16_TOKEN` |
| `20260914-180857-5e0231` | typescript | 4 | 4 | `SENSORIUM_E16_TOKEN` |

#### Phases

| phase | seconds |
|---|---|
| build-driver | 0.152 |
| preflight | 0.311 |
| baseline | 0.667 |
| mint | 0.0 |
| copies | 0.018 |
| record-python | 0.137 |
| record-rust | 0.648 |
| record-typescript | 0.67 |
| info | 0.142 |
| versions | 0.009 |
| grep-values | 0.276 |
| bench-baseline | 37.656 |
| bench-head | 44.6 |

## 4. Part C

### measured 2026-09-16

Measured once, on this box, under `e16c.sh`. **Part C: DONE** — H4 PASS. The subject was a COPY of `~/.sensorium/traces` and its `redaction.key`: 273 traces against §9's 273, copied into the work root and retrofitted there, so the live store was read and never written (the retrofit of it is a post-merge chore, C18). The token was NOT minted (P10) and it is not one value: the traces already held 4 distinct value(s) of `CLAUDE_CODE_MESSAGING_TOKEN` (the token rotated over the store's life), each read from its own trace's `meta.env` through a read-only connection and swept one at a time (R15, amended below), never printed and never written anywhere but `grep`'s own argument — `sha256(value)[:8]` = `41285dda` (254 trace(s)), `61e4ad5f` (11 trace(s)), `876f167c` (5 trace(s)), `426ae10d` (3 trace(s)). 28.8s wall clock.

| cell | word | §9's rule | what was read |
|---|---|---|---|
| H4 | **PASS** | all | 273 traces, every one named in the dry run; 0 occurrences in 275 files after; 273/273 info exit 0, by retrofit; stdouts identical |
| H1-env | dropped | -- | part A |
| H1-values | dropped | -- | part B |
| H2 | dropped | -- | part A |
| H3 | dropped | -- | part A |
| H5 | dropped | -- | part B |
| H6-env | dropped | -- | part A |
| H6-values | dropped | -- | part B |

#### Pins

| pin | path |
|---|---|
| work root | `E16C_DIR=/mnt/extra/sensorium-rung2/e16c` |
| the copy (the subject) | `$E16C_DIR/store-c/` |
| transcripts | `$E16C_DIR/c-transcripts/` |
| instrument output | `$E16C_DIR/c-out/` |
| copied out of (never written to) | `~/.sensorium` |

#### The dry run

Before the measurement, on a FABRICATED store of three synthetic traces carrying a `dry-` decoy that no content pattern matches (P11), with each `redact` pass capped at 90 s, the `info` sweep at 90 s, each grep at 30 s and the part at 270 s (a tenth of the measurement's 2700 s), into a work root of its own that was deleted afterwards. What it found, and what changed in the instrument between it and the run above:

- e16a._run merges stderr into stdout, so clause 4 could never have matched under part A's runner; part C added _run_split, which keeps the streams apart and compares stdout as bytes.
- The traces/ directory clause prints in BOTH passes (P3), so --all's directory tightening does not break dry/real byte-identity; confirmed on the rehearsal, not assumed.
- The first fabricated store carried no -wal/-shm (TraceWriter.close checkpoints), so the sidecar arithmetic was rehearsed at zero on both sides and a suffix bug went unseen; the second rehearsal holds a reader open so the store carries sidecars, and counts by name: 3+3 before, 0 after.
- The before and after file counts are not one-for-one: the before sweep counts the sidecars apply later unlinks, and the after sweep counts the invocations.jsonl the command wrote into the copy; the Before and after table says so.
- R15 (pre-launch amendment, beside the locked block): the live store holds FOUR distinct CLAUDE_CODE_MESSAGING_TOKEN values (the token rotated: 254/11/5/3 of 273 traces), so the instrument sweeps every distinct value found in the copy -- each trace must hold its own value before, every value must read 0 in every file after -- and the record cites each value's sha8 and the count, never a value; the second rehearsal swept two decoy values.

#### Amendments, beside §1

- **R15, the token is a SET of values, not one.** §1's amendment pre-registers the token as "the value of `CLAUDE_CODE_MESSAGING_TOKEN` in the copy's own traces, read by the instrument from the first trace's `meta.env`", and makes it a precondition that "every `*.db` in the copy must hold the value at least once before the run". Measured read-only before the run, this box's store holds FOUR distinct values of that variable across its 273 traces (254 / 11 / 5 / 3 — the token rotated over the store's life), and the first `*.db` in sorted order carries the one held by 11. Read literally, the precondition therefore refuses 262 of 273 traces for a reason that has nothing to do with the retrofit. Corrected clause: **the instrument reads every trace's own value, sweeps the DISTINCT set one value at a time, and requires each trace to hold ITS OWN value at least once before the run; clause 2 requires every one of the values to read 0 in every file after it.** That is strictly stronger than the pre-registered single-value reading — it makes clause 2 a claim about all 273 traces instead of 11 — and it cannot pass where the pre-registered one would. The record cites each value's `sha256[:8]` with the number of traces holding it; no value is ever printed.

#### Versions

| version | read | §1 expected |
|---|---|---|
| `sensorium` (the venv the command ran from) | 0.17.0 | 0.17.0 |
| `recorder:` on 19 trace(s) | (none recorded — a Python trace) | -- |
| `recorder:` on 76 trace(s) | sensorium-rt 0.1.0 | -- |
| `recorder:` on 81 trace(s) | sensorium-rt 0.3.0 | -- |
| `recorder:` on 94 trace(s) | sensorium-rt 0.4.0 | -- |
| `recorder:` on 3 trace(s) | sensorium-ts 0.4.0 | -- |

#### H4 — the four clauses

| # | the clause | what was read | word |
|---|---|---|---|
| 1 | every `*.db` in the copy has a dry-run line naming CLAUDE_CODE_MESSAGING_TOKEN | 273 traces, every one named in the dry run | **PASS** |
| 2 | every `grep -rc` count over the copy is 0 after the real run | 0 occurrences in 275 files after | **PASS** |
| 3 | `sensorium info` exits 0 on every trace and reads `by retrofit` | 273/273 info exit 0, by retrofit | **PASS** |
| 4 | the dry run's stdout is the real run's, byte for byte | stdouts identical | **PASS** |

#### The count line

| pass | exit | seconds | the summary line |
|---|---|---|---|
| `--dry-run` | 0 | 6.619 | `redacted 273 of 273 traces (0 already clean, 0 skipped, 0 refused); spools under target/ and the TypeScript spool dirs are not reached; traces/ mode 775 -> 700` |
| real | 0 | 7.982 | `redacted 273 of 273 traces (0 already clean, 0 skipped, 0 refused); spools under target/ and the TypeScript spool dirs are not reached; traces/ mode 775 -> 700` |

The two stdouts were byte-identical: `sha256(dry) = f73437dcc1f03e5e`, `sha256(real) = f73437dcc1f03e5e`. `--dry-run` said on stderr: `dry run: nothing was written`.

#### Before and after

| reading | before | after |
|---|---|---|
| traces in the copy (`*.db`), against §9's 273 | 273 | -- |
| traces whose environment held `CLAUDE_CODE_MESSAGING_TOKEN` | 273 | -- |
| distinct values of it, each swept on its own (R15) | 4 | 4 |
| files holding any of those values' bytes | 273 | 0 |
| occurrences of them, summed | 273 | -- |
| files whose count could not be read | -- | 0 |
| files swept | 820 | 275 |
| `-wal` files | 273 | 0 |
| `-shm` files | 273 | 0 |
| files at mode 0600 | -- | 275 of 275 |
| `traces/` mode | -- | 700 |
| occurrences of `41285dda` after | -- | 0 |
| occurrences of `426ae10d` after | -- | 0 |
| occurrences of `61e4ad5f` after | -- | 0 |
| occurrences of `876f167c` after | -- | 0 |

The two file counts are not one-for-one: the sweep before the pass counted the `-wal`/`-shm` sidecars that `apply` then unlinked with the inode it replaced (C7), and the sweep after it counts the `invocations.jsonl` the command wrote into the copy as it ran. Both sweeps are the same function over the same root, so every file present at the time is in the count.

#### Phases

| phase | seconds |
|---|---|
| preflight | 0.128 |
| copy | 0.155 |
| count-before | 0.142 |
| dry-run | 6.62 |
| real | 7.983 |
| compare | 0.0 |
| grep-after | 0.139 |
| info | 13.584 |
| modes | 0.006 |
