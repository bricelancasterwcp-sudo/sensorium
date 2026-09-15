# CARRIED-DEBT — volume 13

The first 2026-09-14 section — secrets redaction, PR A: rule v1, the store
key, the recorded environment and the 0600 file modes — moved here
**2026-09-14** (PR B, in its final fix wave) so
[`docs/CARRIED-DEBT.md`](CARRIED-DEBT.md) stays under 800 lines. It is the
thirteenth numbered volume, on the rule
[`docs/CARRIED-DEBT-ARCHIVE-2.md`](CARRIED-DEBT-ARCHIVE-2.md) set when it was
cut: the archive is **numbered volumes, each kept under 800 lines**, never one
growing file.

The move was measured before it was made, the way the ledger's own lesson
asks: the fix wave that closes the whole-branch review added **25** lines to
the live file's newest section — the spawned-command-line finding, the T7
item Task 12's review found missing, and the three ★ priorities — against a
live file of **795**, which would have taken it to **820**, twenty over the
ceiling. The section moved here is **245** lines; the live file is **591**
after the cut, the append and the blank line that had separated the two
sections. Content was not trimmed to fit; the oldest section was cut, which
is the rule — one slice earlier than the live file's own note predicted it
would fire, because five lines of headroom is not a wave's worth.

**The wording, the order and the strikes are unchanged** — nothing was edited
BY the move, a resolved item is struck through here exactly as it was in the
live file, and nothing is deleted. The fix wave struck nothing inside this
section: it closed nothing PR A carried, so every deferred item below travels
open. The house rule stated in `docs/CARRIED-DEBT.md`'s header governs every
volume, and a deferred item below is still open unless it is struck.

## 2026-09-14 — secrets redaction, PR A (rule v1, the store key, env redaction, 0600 files)

The first of the design's three PRs
(`docs/superpowers/specs/2026-09-13-sensorium-secrets-redaction-design.md`):
the recorded environment stops reaching disk in plaintext, in all three
recorders, and the store grows a key. Eleven plan decisions (**A1–A11**) and
thirty-eight rulings (**R1–R38**) are in the design's **§13** with what each
costs if wrong, beside the fourteen places the shipped code differs from the
spec. **DONE** — E16 part A was measured **twice**: run 1 `DONE-WITH-STOP`
(H1 PASS, H2 STOP, H3 STOP, H6 PASS), run 2 from zero with a fresh token
after the fixes, all four **PASS**
(`docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` §2:
every measured reading in run 1 is byte-untouched; run 2 follows it). Values
are PR B's, the retrofit PR C's.

### Settled — closed here

- **The environment leak is closed in all three recorders.** A value whose
  NAME fires rule v1 is written as a marker, never plaintext: Python
  `61aec55`, the Rust runtime `ccfa88e`/`402a102`, the TypeScript runtime and
  its ingest `dc8ef45`. Measured: E16 **H1, 0 hits over 1033 files** in run 2
  (842 in run 1), raw bytes, before and after conversion.
- **Digests are keyed, and the key is published by CONTENT** (**R15**). A
  per-store `redaction.key`, 32 bytes at 0600: a writer builds
  `redaction.key.<pid>.tmp` whole, fsyncs, hard-links it at the name, and on
  `FileExistsError` reads the WINNER's material, so two recorders cannot take
  digests under two keys; a filesystem refusing `link` falls back to
  `os.replace` and re-reads. `ac11369`/`d6802af`, Rust `9a42c01`
  (`redaction_key.rs::load_or_create_mints_a_32_byte_key_at_0600_under_a_0700_root`),
  handed to both runtimes as hex in `SENSORIUM_REDACT_KEY`, which every
  recorder deletes from what it records. Only the drivers and the Python
  recorder mint one (**A5**).
- **Every file the recorders and drivers create under the store and the
  spool directories is 0600, every directory 0700** — including the **ten**
  paths E16 run 1 found at 0664/0775: the TypeScript driver's
  `spool/<inv>/` tree, its `manifests/` dir and four JSON records,
  `harness.json`, `ingested.json`, `invocation.json`, and
  `cargo-sensorium`'s own `invocation.json` (`6a719e4`). With them: the store
  root and `traces/` as a two-level idiom (**R4**, `61aec55`),
  `invocations.record`'s third creator (**R18**), the Rust converter's
  `traces/` (**R26**, `7963a64`), and `store/db.py:117`, the last
  default-mode creator inside the store (**R35**, `e36d5dd`). Mode applies at
  CREATION: an existing store's `spool/` and `manifests/` keep the modes they
  were made with, and nothing chmods.
- **`info` says what was redacted, in two lines** (`f542ce1`, **A7**/**A8**).
  `env:` has three forms — bare hash (no `redaction` key, or `mode: off`),
  `(N vars, 0 redacted)` for a MEASURED zero, `(N vars, k redacted: A, B, +M
  more)` capped at eight names; the `redaction:` line, straight after
  `caps:`, has four — `none`, `OFF (SENSORIUM_NO_REDACT)`, `rule v1, UNKEYED
  (…)` naming why (**R8**), and `rule v1, keyed (key <id>), by <writers>`,
  appending `(key mode 0644 -- expected 0600)` only when the loose key took
  these digests. `tests/test_info_redaction.py`, vectors `v42`, `v42b`.
- **`refocus` compares redacted variables by digest, and says when it
  cannot.** §6.2's table lives ONCE, in `redact.compare` (**R1**);
  `RedactionPair.compare` delegates. Two execution changes: a redacted name
  whose digests differ is still partitioned by NAME into the session and
  harness sets, so a cross-terminal re-run keeps the exemptions its plaintext
  twin had (**R21**, amending **A2** — without it every such re-run was
  withheld); and an UNCOMPARABLE name never withholds a licence, in the
  Python branch as in the other two, stamping `UNVERIFIABLE_ENV` beside the
  verdict (**R19**), while the `compared` count excludes it (**R22**).
  `2d954da`, `131a652`; `tests/test_refocus_redaction.py`, vector `v43`.
- **The recorder-key exclusion is an EXACT set in both branches, not a
  prefix** (**R31**, **R33**, **R34**) — E16 H3's finding and the reason run 1
  STOPped. `refocus_rust.RECORDER_KEYS` is the nine names
  `launch.rs`/`runner.rs`/`driver.rs` SET — `SENSORIUM_FOCUS`, `INVOCATION`,
  `RT_DIR`, `SPOOL`, `TARGET`, `TIER`, `TOOL_HASH`, `WS`, plus
  `SENSORIUM_REDACT_KEY`; `refocus_typescript.RECORDER_KEYS` the eight
  `ts/driver.py::_env` sets — `SENSORIUM_FOCUS`, `INVOCATION`,
  `MANIFEST_DIR`, `SPOOL`, `TIER`, `TS_PKG`, `TS_ROOT`, plus
  `SENSORIUM_REDACT_KEY`. The three user knobs (`NO_REDACT`, `REDACT_NAMES`,
  `REDACT_ALLOW`), `SENSORIUM_CARGO_SENSORIUM` and `SENSORIUM_INNER_RUNNER`
  are COMPARED like any user variable — a chained runner is a world change.
  Both are pinned by grepping those sources' SET-sites
  (`tests/test_refocus_{rust,typescript}_recorder_keys.py`). `1f60dd6`,
  `9d8f16a`.
- **Rule v1's name rule, as amended by R10:** `PWD` joins the segment set but
  fires only in a name of two or more segments (`MYSQL_PWD` fires, `PWD` and
  `OLDPWD` do not), and an EXACT set `{PGPASSWORD}` fires regardless of
  segments. `ac11369`, `7b97770`; one fixture,
  `docs/trace-format/redaction-v1.json`, read by `tests/test_redact.py`,
  `rust/sensorium-rt/tests/redact.rs` and `typescript/test/redact.test.mjs`,
  the split cross-checked against Python's over 9,331 names at Task 3.

### Deferred by ruling

- **PR B — captured values, wire v4, the content rule.** §4.2's `redacted`
  object on a capture and the `redaction.values` key **do not exist** here;
  `info` prints no `values redacted:` clause and `v42`'s `expect_absent` pins
  the absence. The content rule goes in its own `redact_content.py`, not into
  `redact.py`; v4 is built beside v3 with the v3 fixtures kept as the
  older-runtime path. *Cost if wrong:* a value-bearing leak H1-values has not
  looked for yet, which is what part B measures.
- **PR C — the retrofit.** `sensorium redact [--all] [--dry-run]`, and H4
  with it. One hazard travels to it: a stale `redaction.key.<pid>.tmp` from a
  killed writer is left on disk by **R15**'s publication and nothing sweeps
  it. *Cost if wrong:* a stray 0600 file of key material in the store root.
- **Outside this PR's promise, still at default modes:**
  `<target>/sensorium/{manifests,mirror,cache,rt}` — the **mirror holds a
  copy of the user's source** — and `ts/wrapper.py`'s files inside the user's
  `node_modules`. This PR promised the spool and the store; these are
  neither, and they were named at Task 8b rather than discovered. *Cost if
  wrong:* a world-readable copy of somebody's source under `target/`.
- **Named as later slices by the design's §11, untouched:** `seal` mode
  (reversible AES-GCM under this key — the key exists now, the mode wants its
  own threat model first), the MCP policy layer, scanner parity, allow-globs,
  Windows ACLs (modes are advisory there), and the Rust content window under
  `target/` (closing it puts a regex dependency in the dependency-free
  runtime).
- **Untested corners, named by reviewers, deliberately left:** the
  rename-fallback re-read in **R15** (forcing a `link` failure is hard; two
  processes both in the fallback can still end with different keys —
  inherent, accepted); the short-write loop in Python's key writer (the
  mutation claim does not reproduce — a monkeypatched `os.write` returning a
  short count is the falsifier); the driver's unkeyed stderr announce
  (`redaction_key.rs::announce`), which the docs state and nothing pins — a
  `#[test]` over an unreadable key path capturing stderr is the falsifier;
  `TraceWriter::create`'s `remove_file → create_new` ordering; and
  `launch.rs`'s unset-when-unkeyed direction. *Cost if wrong:* five
  behaviours described in prose and asserted by nothing.

### Files near the ceiling

Measured at this slice's last commit against the 800-line gate
(`tests/test_ceiling.py`); the next edit to each takes a seam, not a
paragraph:

- **`src/sensorium/query/refocus_world.py` 788** — S5 named the seam, this
  slice spent the headroom; the next change SPLITS.
- **`docs/query.md` 798** and **`docs/TRACE-FORMAT.md` 797** — two lines
  between them; `docs/query-typescript.md` is query.md's named seam.
- **`rust/cargo-sensorium/src/convert/mod.rs` 795** — split `Discovery` into
  `convert/discover.rs`.
- **`src/sensorium/record/boot.py` 784** — 16 lines of headroom; the
  `record/boot_meta.py` seam the plan already names.
- **`src/sensorium/redact.py` 520** — `redact_key.py` is where the key half
  goes when PR B adds the content rule.
- **`tests/acceptance_e16/e16a.py` 715** and **`assemble_e16a.py` 677** —
  part B's cells split first; `e16a_cells.py` (353) is the precedent.
- **`CHANGELOG.md` 660** after 0.15.0 — the 0.8.7 entry moved verbatim to
  `CHANGELOG-ARCHIVE-2.md` (479) under a dated cut note at **R36** to make
  the room.

### Deferred minors, per task

- **T0:** `SECTIONS.here_reader` never varies in
  `tests/test_acceptance_e16_lock.py` — dispatch without payoff.
- **T1 (`redact.py`):** the unreachable `was is None and now is None` branch
  in `compare` is untested; `Key.from_hex` sets a fake `path`; `uncomparable`
  returns ONE reason word for a mixed set (plan-mandated).
- **T2 (Python recorder):** `create_trace` fchmods a pre-existing file it
  then refuses (unreachable from the recorder), and its bare `OSError` raise
  on a chmod-hostile mount would read better as `TargetError`; no unit test
  scans the trace BYTES (E16 H1 does);
  `test_the_ts_ingest_reservation_is_0600…` reaches a private `_reserve`.
- **T3 (Rust runtime):** `.mode(0o600)` does not reach a pre-existing 0.5.0
  spool file in a reused dir with a recycled pid; `Knobs::from_env` is lossy
  where `Key::from_env` is strict.
- **T4 (driver):** `serde_json::Map` alphabetises the `redaction` object on
  the wire (**R2**'s order is source-level); a non-object `redaction` header
  value passes through verbatim; `SENSORIUM_DIR` and `HOME` both unset
  records silently unkeyed until after cargo (deliberate — never refuse a
  build).
- **T5 (TypeScript):** `ts/invocation.py::env_hash` encodes surrogateescape
  only; `rt.test.mjs:87` computes its expectation with `redactEnv` itself (a
  blind pin; the load-bearing ones are in `redact.test.mjs`); `envHash` has
  no importer; a truthy non-object `redaction` passes through.
- **T6 (query side):** the unrun-checks preamble ("the recorder declares it
  does not produce them") is untrue of the redaction marker but byte-pinned
  by two locked acceptance readers; `_env_state` loads the store key on every
  call; `v42b`'s `asserts` should say why it plants no digest; a non-dict
  `redaction` raises in `info_cmd`/`refocus_env`;
  `test_two_digests_that_differ_withhold…`'s docstring still says the
  partitions are never consulted, which **R21** made false.
- **T7 (docs):** `rust/README.md:263-267`'s Pin-1 citation clause lost its
  verb; "Where traces go" grew 15 lines against a one-sentence budget.
- **T8 (measurement):** `first_pass_block` hardcodes "run 1"; the launcher
  refuses when no binary exists (a fresh clone builds once by hand);
  `FIX_COMMITS` is hardcoded in the assembler; run 1's raw record predates
  the `driver_build` field, so it would re-render as "Versions: dropped" —
  §2-equals-render holds for run 2 only. **Brice owed:** free `$E16_DIR` (two
  runs and a 0600 plaintext token).

### Process lessons

- **The census's input is a committed list, and the list is the finding.**
  **A6** made `tests/fixtures/benign-env-names.txt` the input — this box's
  shell names plus 40 common CI names, the expected firing subset at its top
  — rather than the corpus runner's live environment, because on CI the
  launching shell carries `GITHUB_TOKEN` and the rule firing on it is
  correct, not a false positive. The fixed list is what let anyone notice
  that **`PGPASSWORD` and `MYSQL_PWD` never fired**: the two commonest
  database-password variables in the world, missed by a segment rule that
  read plausible. Amended at **R10** before Rust and TypeScript implemented
  it, for two fixture rows. A rule nobody has run over a named list is a rule
  nobody has read.
- **A repo-wide pytest gate is invisible to a cargo or npm command list.**
  Two live there — the 800-line ceiling and the no-box-path grep — and both
  cover `.rs` and `.mjs`. Task 3 shipped `spool.rs` at 804 lines, and Task 3
  again shipped a home-directory literal in `redact.rs`; `cargo test` caught
  neither, the next task's `pytest -q` caught both. Every task's verification
  list now names the WHOLE `pytest -q`, not its own language's runner.
- **A test that calls a store-touching function without `SENSORIUM_DIR`
  writes the DEVELOPER's real store.** `tests/test_ts_driver_focus.py` called
  `driver._env` unisolated, and a plain `pytest` run minted
  `~/.sensorium/redaction.key` on this box; the sweep that followed found a
  second such test, OLDER than this branch, appending to the real
  `invocations.jsonl`. The proof the fix holds is the whole suite under a
  scratch `HOME` leaving no `.sensorium` behind (`84a5925`) — isolation is a
  sweep, not a patched call site.
- **A partition is a judgement about the NAME, not the value.** The plan
  wrote that a redacted variable's change skips the session and harness
  exemptions because their rules "cannot be consulted without plaintext".
  Both sets are **lists of names**: `SSH_AUTH_SOCK` and `CLAUDE_CODE_*TOKEN`
  are session set 1 members that also fire rule v1, so the rule as written
  withheld a licence from every cross-terminal re-run. **R21** reads
  membership off the name and skips only RELOCATION, which genuinely needs
  the value. When a rule says *cannot be consulted*, check what it is
  consulted WITH.
- **A STOP the dry run already showed is a defect, not a re-roll.** Run 1's
  two STOPs — H2's ten modes, H3's prefix hole — were both visible in the dry
  runs that preceded it, and neither cell nor clause was touched before the
  measurement: run 1 was measured and recorded verbatim, the code was fixed
  (`6a719e4`, `1f60dd6`, `9d8f16a`, `e36d5dd`), and run 2 measured from zero
  beside it (**R30**), the record naming which run is the first PASS per
  cell. Softening either clause would have bought a clean table and lost the
  finding that a prefix exclusion silently grants a licence over a rotated
  secret.
- **The dry run of a re-measurement earns its keep by finding NEW failures.**
  **R37** added a driver-rebuild phase for run 2 — a warning comment is not a
  check, and a stale release binary re-measures old code silently (run 1's
  own finding). The dry run of that new phase caught it failing **OPEN**:
  `phase()` swallowed the precondition's `KeyError` and recorded a note where
  the run should have ended (`10bdc18`, then `CRITICAL_PHASES` pinned by
  `tests/test_acceptance_e16_phase.py` at `3bf855f`). A phase added between
  two readings is new code and gets the same dry run the first reading did.
- **A pre-registration error found before launch is amended beside the locked
  text, never edited.** Three here, all **R27**: decision A10 named
  `corpus/typescript/aliasing`, which does not exist (Task 8 records
  `async_interleaved`); the Rust arm's `--focus` had to name a function that
  exists in `corpus/rust/aliasing`; and §1's instrument path
  (`tests/acceptance/e16.sh`) is not where the instrument landed. Each was
  pinned by a dated amendment with the corrected clause beside the locked
  one. This is the S5 slice's **P16** applied a second time, which is what
  makes it the repo's rule rather than that slice's anecdote.
