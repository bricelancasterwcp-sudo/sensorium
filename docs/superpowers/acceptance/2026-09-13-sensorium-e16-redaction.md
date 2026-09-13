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

## 2. Part A

Not yet measured.
