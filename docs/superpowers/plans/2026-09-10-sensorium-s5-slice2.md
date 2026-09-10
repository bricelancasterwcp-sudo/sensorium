# S5 slice 2 — E6″, the converter ladder, the `node --test` extensions: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn rung 1's two open numbers into verdicts under new pre-registrations — E6″ (the plain band) and E10′ (the converter ladder) — and close the four R46 residuals in the `node --test` hook, shipping Python **0.9.1** and `sensorium-ts` **0.1.1** with trace format 4 untouched.

**Architecture:** Three independent parts under one pre-registration. (1) A new E6 instrument (`e6pp.sh`) runs one guarded before/call/after session on the lens and derives its band from the before arm. (2) The converter's write path takes the Rust converter's own fix (`TraceWriter(durable=False)`: one transaction per trace, `synchronous=NORMAL`) and a streaming spool reader, each measured on the kept f08e89 spool set by a guarded instrument (`e10p.sh`) against a diagnosis taken on main's code first; a 372-pair `sensorium diff` equivalence gate holds the traces identical. (3) The loader hook returns Node's own reported format so Node strips and the hook erases nothing; the R45 refusal names the CommonJS exclusions.

**Tech Stack:** Python 3.12–3.14 (converter, driver, reader, instruments); Node v24.16.0 (the hook, probes); vitest 4.1.9 / vite 6.4.3 on the lens; sqlite3 (WAL); bash + `python3` for the acceptance instruments. No new dependency on either side.

**Spec:** `docs/superpowers/specs/2026-09-10-sensorium-s5-slice2-design.md` — §2 (E6″), §3 (E10′), §4 (the hook), §5 (decisions without work), §6 (testing), §7 (order), §8 (versions, ceilings), §9 (S1–S14), §10 (rulings), §11 (the pre-registration table). **Prior record:** `docs/superpowers/acceptance/2026-09-09-sensorium-s5-rung1.md` (§5 gaps 5, 6, 13). **Rigor:** `~/.claude/skills/rigorous-experiments/SKILL.md`. **Style:** as rung 1's plan — interfaces and invariants, verbatim text only where a fresh implementer would guess wrong (the writer's mode, the reader's shape, the hook's return, the refusal sentence, the instruments' sequence).

## Global Constraints

- **The lens is read-only except by Task 6.** `/mnt/extra/sensorium-s5/vtt/frontend` (VTT `0091e97`) is touched by nothing but `e6pp.sh`; `~/workspace/projects/vtt` is never read. Nothing measured writes to `/`.
- **Stores and copies:** `SENSORIUM_DIR=/mnt/extra/sensorium-s5/store-slice2` for every trace this slice records or converts; the spool copies at `/mnt/extra/sensorium-s5/e10-spool/` (Task 0). **No box path is ever committed**; results files are redacted by the assembler and refused if a path survives.
- **Pre-registration is committed before any code** (Task 0), and byte-locked: after a number is read no threshold moves, no arm is added, no run is re-rolled. An infrastructure kill may be re-run from zero with the reason recorded.
- **Every converter cell names its converter:** the instrument writes `converter_rev` (`git rev-parse HEAD` of the tree whose `sensorium` ran) and `converter_bin` into every JSON cell. Arm 0 runs main's converter (the tree at Task 0's commit); every later cell runs the worktree's own `.venv/bin/sensorium`.
- **Legacy output is byte-identical:** the suite counts pinned in Task 0 (pytest on 3.12/3.13/3.14, `npm --prefix typescript test`, corpus `--only-dir typescript --require-driver` and `--only-dir .`, live) are the regression fence for every task; no trace key, vector or vocabulary string moves.
- **Dependency policy:** none added, Python or Node. `typescript/` runtime dependency stays `magic-string` only.
- **The load guard** (1-minute load under 4.0, read from `/proc/loadavg`, up to 90 tries 20 s apart, the reading written beside every wall) precedes every timed repetition in Tasks 1–4 and every run in Task 6.
- **Ceilings:** no file over 800 lines (`tests/test_ceiling.py`; records exempt). `docs/TRACE-FORMAT.md` (799) is not opened. `README.md` (782) takes at most one sentence. `CHANGELOG.md` (756) cuts its oldest entry to `CHANGELOG-ARCHIVE.md` before the 0.9.1 entry is written. `docs/CARRIED-DEBT.md` (415) is measured before its section is appended.
- **Tests:** TDD per task; every new Python test mutation-checked (break the pinned line, watch it fail, restore) under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged; any harness that runs mutants in a loop uses `setsid` and kills by process group on timeout. Functions under 50 lines.
- **Commits:** conventional prefixes; the session's trailer lines. Branch `feat/s5-slice2` off `main` at `bbd0781` (the spec is on main), worktree `/mnt/extra/sensorium-rung2/s5-slice2`, venv `.venv` (3.13; `uv venv .venv --python 3.13 && uv pip install -p .venv/bin/python -e ".[dev]"`), `npm ci --prefix typescript && npm ci --prefix typescript/probes && npm ci --prefix corpus/typescript`. SDD ledger `<worktree>/.superpowers/sdd/2026-09-10-sensorium-s5-slice2/progress.md`, archived to `/mnt/extra/sensorium-rung2/sdd-archive/` before the worktree goes.
- **Gotchas carried:** `npm --prefix typescript run check`, never `npx tsc -p` from the root (R4); `pgrep -f`/`pkill -f` self-match — anchor `^[^ ]*node ` or find pids from spool names; `setsid nohup x &` changes the pid.

---

## Decisions this plan makes (each amends the spec non-silently in Task 7)

| # | Question | Decision | Why | Cost if wrong |
|---|---|---|---|---|
| P1 | Where the plan lives | On the feature branch as its first commit, not a docs PR | The spec is merged; Brice asked for the plan next | the plan is reviewed in the slice's PR |
| P2 | Results file names | `<store>/results/e10p-<stage>-<cell>.json` (stages `arm0`, `a1`, `a3`, `a2`, `a4`, `final`; cells `big-j1`, `full-j1`, `full-j4`, `full-j16`, `file`), `e10p-eq.json`, `e6pp.json`, `pins.json`; assembled by a new `assemble_slice2.py` into `docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.results.json` | one file per cell, so a cell that was never measured is a missing file the assembler reports as `null` + `dropped` | none |
| P3 | The equivalence pairing key | `test_file` from each `run:` line's `file:` field — 372 distinct on this set (E0′) | the run ids differ by construction | a set with a repeated `test_file` refuses the gate by name rather than pairing wrong |
| P4 | `TraceWriter`'s new argument | `TraceWriter(path, batch=512, durable=True)`; `durable=False` sets `PRAGMA synchronous=NORMAL`, never commits before `close()`, and `close()` always commits | one argument, one meaning; the Python recorder is untouched by default | none |
| P5 | The reader's shape | `spool.read(path)` keeps its name and return type; `Spool.records` becomes an **iterator** that fills `Spool.exit` and `Spool.torn_tail` as it goes; BOOT is read eagerly from line 1 | every caller already treats `records` as a sequence to iterate once | a caller wanting a list writes `list(sp.records)` (one test does) |
| P6 | The R45 sentence's shape | per reason with counts (`commonjs x2, parse-error x1`), the ES-modules-only clause appended only when `commonjs` is among them | R27's precedent: one bare reason loses the split as soon as there are two | none |
| P7 | `check.mjs` nodetest mode takes the manifest dir | `node check.mjs nodetest <spool> <manifests>`; the `.cjs` check reads `_tally-<pid>.json` | the check needs the tally; the vitest mode already requires it | the npm script passes one more argument |
| P8 | `e6.sh` / `e10.sh` untouched | each gains ONE header comment line naming its successor; nothing else | the rung-1 record cites them by name (spec §5) | none |
| P9 | The new record's byte lock | `tests/test_acceptance_s5_slice2_lock.py` with `DOC` and `BYTE_LOCK`; it reuses `rust/tests/acceptance_rung3.byte_lock_check` if that helper slices this document's `## 1.`–`## 2.` range, else a 20-line local equivalent (`git show <sha>:<doc>`, the slice between `\n## 1.` and `\n## 2.`, sha256 against the working tree); skips BY NAME on a shallow clone | rung 1 checked its lock by hand; a test does it every run | none |
| P10 | RSS is measured by the instrument, not the product | `e10p.sh` runs each ingest through a 6-line Python wrapper that prints `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` after the subprocess returns (the largest descendant's peak, KB) | no GNU `time` dependency (memory: `uutils` wrappers have crashed on this box) | none |

## Pre-registration (Task 0 commits spec §2.2, §3.2, §3.4, §3.5, §4.5 and §11 verbatim as the record's §1, plus these pins)

- **The full-suite set:** `/mnt/extra/sensorium-s5/store-rung1/acceptance/spool/20260909-160038-f08e89/` — 372 `.jsonl`, 414,450,522 bytes — copied whole (`invocation.json`, `harness.json`, `manifests/` included, `ingested.json` removed from the copy) to `/mnt/extra/sensorium-s5/e10-spool/f08e89/`; `sha256sum` over every file in the copy written to `/mnt/extra/sensorium-s5/e10-spool/f08e89.sha256` and its own sha256 quoted in §2.
- **The one file:** `20260909-155657-4965c3/1478098-0.jsonl` (611,016 bytes) with its directory's three JSON siblings, to `/mnt/extra/sensorium-s5/e10-spool/one/`; pinned the same way.
- **The big-spool copy for cell 0a:** `/mnt/extra/sensorium-s5/e10-spool/big/` holding only `1491993-0.jsonl` (195,851,484 bytes, `src/lib/map/gridDetect.test.ts`) plus the set's `invocation.json`, `harness.json`, `manifests/`.
- **The reference wall:** 22.5925 s (E1′'s plain median). **The one-file bound:** 0.4002 s. **Job counts:** 1, 4, 16 (16 = `os.cpu_count()` here, the driver's default).
- **The rung-1 manifest:** `/mnt/extra/sensorium-s5/manifest-rung1-before.txt` (748 entries, file sha256 `eb4c5ddb203e3af25dd2f485fa5099ee9347656c305c6b7521edb4efa156c9a8`), verified once at T0 and again by `e6pp.sh` before and after its own runs.
- **Reported without a gate:** spec §3.6 — events/s per rung on the big spool, peak RSS before/after A3, 0b/0d, the call run's harness and driver walls, the fresh set's ingest.

## File structure

```
src/sensorium/store/writer.py       TraceWriter(durable=)            [modify, Task 2]
src/sensorium/ts/build.py           Builder(..., durable=False)      [modify, Task 2]
src/sensorium/ts/spool.py           streaming read()                 [modify, Task 3]
src/sensorium/ts/ingest.py          R45 refusal; A2 dispatch (cond.) [modify, Tasks 5, 3]
typescript/src/hook.mjs             Node's format, no strip          [modify, Task 5]
typescript/src/index.mjs, package.json   0.1.1                       [modify, Task 7]
typescript/test/hook.test.mjs       H1/H2 tests                      [modify, Task 5]
typescript/probes/nodetest/{ext.probe.test.mts, ext.probe.test.mjs, ext.probe.test.cjs}
typescript/probes/nodetest/controls/{enum.ts, jsx.tsx}, controls.mjs [create, Task 5]
typescript/probes/check.mjs, package.json, README.md                  [modify, Task 5]
typescript/acceptance/{e10p.sh, e10p_report.py, e10p_eq.sh, e10p_eq_report.py, rss_run.py}  [create, Tasks 1, 4]
typescript/acceptance/{e6pp.sh, e6pp_report.py, assemble_slice2.py}  [create, Task 6]
typescript/acceptance/assemble.py   arm_stats: loads filtered        [modify, Task 6]
typescript/acceptance/{e6.sh, e10.sh}   one header line each         [modify, Task 6 / 1]
tests/test_writer.py, tests/test_ts_ingest_meta.py, tests/test_ts_driver.py, tests/test_ts_live.py  [modify]
tests/test_acceptance_s5_slice2_lock.py                              [create, Task 0]
docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md (+ .results.json)  [create, Task 0; filled Tasks 1–6]
typescript/HONESTY.md, typescript/README.md, README.md, CHANGELOG.md, CHANGELOG-ARCHIVE.md, docs/CARRIED-DEBT.md, the rung-1 spec §11, this slice's spec (§14-style deltas)  [Task 7]
```

---

### Task 0: Branch, pre-registration, pins, the spool copies, the byte lock

**Files:**
- Create: `docs/superpowers/acceptance/2026-09-10-sensorium-s5-slice2.md` — §1 (the six spec sections named above, verbatim, each under a `###` carrying its source heading, with the source commit `bbd0781` stated), §2 ambient pins (filled), §3 results (every cell `not measured (slice 2 pending)`), §4 verdicts and §5 gaps (empty).
- Create: `tests/test_acceptance_s5_slice2_lock.py` (P9).
- Create: `/mnt/extra/sensorium-s5/e10-spool/{f08e89,one,big}/` and the two `.sha256` manifests (box side; the manifests' own sha256 go into §2).

**Invariants:**
- The pre-registration commit precedes every other commit on the branch; §1's bodies are byte-for-byte the spec's sections (a test in the lock file compares each to `git show bbd0781:docs/superpowers/specs/2026-09-10-sensorium-s5-slice2-design.md`).
- §2 records, each with its command: `node --version`, `npm --version`, the lens's vitest/vite/typescript/jsdom versions, `nproc`, the governor, `free -g`, `df -h` of `/` and `/mnt/extra`, `findmnt` of both, `/proc/loadavg` at pin time, `git rev-parse HEAD`, `python -c "import importlib.metadata as m; print(m.version('sensorium'))"` from the worktree venv AND from the global tool (both `0.9.0`), the rung-1 manifest verified (`sha256sum -c` → 748 OK / 0 FAILED), the three spool copies' byte counts and manifest sha256s, and the suite baselines: pytest counts on 3.12/3.13/3.14, `npm --prefix typescript test` (164), `npm --prefix typescript run check` rc 0, corpus `--only-dir typescript --require-driver` (13/35/0) and `--only-dir .` (20/39/0), `SENSORIUM_TS_LIVE=1 pytest tests/test_ts_live.py` (9).
- Preflight refuses under 8 GB free on `/mnt/extra` or 3 GB on `/`, or a 1-minute load above 4.0.
- The copies are made with `cp -r` and the manifest with `cd <copy> && find . -type f | sort | xargs sha256sum`; `f08e89/` holds exactly 372 `.jsonl`.

- [ ] **Step 1:** worktree + venv + npm installs as Global Constraints say; preflight; the three copies and their manifests; the rung-1 manifest verified.
- [ ] **Step 2:** write the record (§1 by `sed -n` over the spec's line ranges, then diffed against `git show`), §2 filled, §3 stubs.
- [ ] **Step 3:** commit §1+§2 ALONE: `docs(s5): pre-register slice 2 (E6″, E10′, the hook probes) before any code`; record the sha as `BYTE_LOCK` in the lock test; run it (PASS); commit the test: `test(acceptance): byte-lock S5 slice 2's §1 at <sha>`.

---

### Task 1: Arm 0 — the diagnosis on main's converter

**Files:**
- Create: `typescript/acceptance/e10p.sh <spool copy> <scratch> <label> <jobs> [n=3]`, `typescript/acceptance/e10p_report.py`, `typescript/acceptance/rss_run.py`.
- Modify: `typescript/acceptance/e10.sh` — one header line: `# Superseded by e10p.sh (E10′, slice 2); kept as E10's instrument.`
- Modify: the record §3 (cells 0a–0e filled with their predictions quoted).

**Interfaces:**
- `e10p.sh`: per repetition — wait for load; `cp -r <copy> <scratch>/<label>-copy-k`, `rm -f …/ingested.json`; fresh `<scratch>/<label>-store-k`; timed region = `python3 rss_run.py -- "$SENSORIUM_BIN" ts ingest --jobs <jobs> <copy-k>` with `SENSORIUM_DIR=<store-k>`; outside it, remove both. Writes one TSV line `k wall status traces load_1min maxrss_kb` per rep; `e10p_report.py` emits the record cell `{value: median wall, n, lens, dropped, label, jobs, spools, spool_bytes, walls, reps, min, max, loads, maxrss_kb (max over reps), converter_bin, converter_rev}`. `SENSORIUM_BIN` defaults to `sensorium`; `CONVERTER_REV` is required (the script refuses without it) and written verbatim.
- `rss_run.py -- <cmd…>`: `subprocess.run(cmd)`; then prints `maxrss_kb=<resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss>` on its own stdout line and exits with the child's status.
- Cells (all with the load guard): 0a `big/` jobs 1 n 3; 0b `f08e89/` jobs 1 n 3; 0c jobs 4 n 3; 0d jobs 16 n 3; 0e `one/` jobs 16 n 5. Converter = the **global tool** (main at `aaa8692`/`bbd0781`, converter code identical), `CONVERTER_REV=$(git -C ~/workspace/sensorium rev-parse HEAD)`.

**Invariants:** no code under `src/` changes in this task; every cell's JSON carries `converter_rev`; the record's §3 quotes each cell beside spec §3.2's prediction and states which of the two pre-stated readings the numbers support (contention vs. serial floor) — a reading, not a verdict.

- [ ] **Step 1:** write the three instrument files; dry-run `e10p.sh` on `tests/fixtures/ts-spools/async-chain` copied to `/mnt/extra` (n=1) and check the JSON shape.
- [ ] **Step 2:** the five cells, in order 0a, 0e, 0c, 0b, 0d (short ones first so a broken instrument is found cheaply).
- [ ] **Step 3:** §3 filled; commit: `test(acceptance): E10′ Arm 0 — the converter's cost on main's code, guarded`.

---

### Task 2: A1 — one transaction per trace, `synchronous=NORMAL`

**Files:**
- Modify: `src/sensorium/store/writer.py` (`TraceWriter.__init__`, `set_meta`, `write_fingerprint`, `write_task_fingerprints`, `_flush_locked`, `close`).
- Modify: `src/sensorium/ts/build.py:85-92` (`Builder.__init__` gains `durable: bool = False` and passes it).
- Test: `tests/test_writer.py`, `tests/test_ts_ingest_meta.py`.
- Modify: the record §3 (cells a1: 0a, 0d, 0e re-measured with the worktree's converter).

**Interfaces:**
- `TraceWriter(path, batch=512, durable=True)`. Verbatim, because the mode is easy to get subtly wrong:

```python
        self._durable = durable
        if not durable:
            # NORMAL under WAL: no fsync per commit. The file is renamed into
            # place only after close() commits, so there is no earlier
            # committed state a reader could be shown; synchronous below that
            # point buys speed, not correctness (the Rust converter's rule).
            self._conn.execute("PRAGMA synchronous=NORMAL")

    def _commit(self) -> None:
        """Every commit in this class goes through here. Durable: each batch
        is its own transaction, so a killed recorder leaves what it flushed.
        Non-durable: nothing commits before close() — one transaction."""
        if self._durable:
            self._conn.commit()
```
  Every `self._conn.commit()` in `set_meta`, `write_fingerprint`, `write_task_fingerprints` and `_flush_locked` becomes `self._commit()`; `close()` becomes `self._flush_locked(); self._conn.commit(); self._conn.close()` (a real commit, both modes).
- `Builder(spool, invocation, harness, tally, path, run_id, durable=False)` → `TraceWriter(path, durable=durable)`.

**Tests (write first, watch each fail):**
- `test_writer.py::test_a_non_durable_writer_commits_nothing_before_close`: `TraceWriter(p, batch=2, durable=False)`, 5 events; a SECOND `sqlite3.connect(p)` reads `COUNT(*) FROM events` == 0; after `close()` it reads 5. (The durable twin, `test_partial_trace_valid_without_close`, keeps passing unchanged.)
- `test_writer.py::test_a_non_durable_writer_runs_normal_under_wal`: `PRAGMA synchronous` → 1, `PRAGMA journal_mode` → `wal` on `w._conn`; and the durable default reads 2 (FULL).
- `test_writer.py::test_set_meta_and_fingerprints_ride_the_one_transaction`: non-durable; `set_meta`, `write_fingerprint`, `write_task_fingerprints` then a second connection sees none of the rows before `close()`.
- `test_ts_ingest_meta.py::test_a_trace_is_identical_whether_the_writer_was_durable`: `Builder` over `async-chain` twice (durable True/False, two paths, one `run_id`); for each table in `code_objects, frames, events, output, tasks, fingerprints, task_fingerprints` the `SELECT * ORDER BY rowid` rows are equal; `meta` equal.
- `test_the_incomplete_claim_is_written_before_anything_is_read` keeps passing: it reads through the builder's own connection, which sees its own transaction.

- [ ] **Step 1:** the four tests; run: 3 fail (`durable` unknown), the fourth fails on `durable`.
- [ ] **Step 2:** the writer change; the builder change; run the four + the whole writer/ingest suites: PASS.
- [ ] **Step 3:** mutation check: flip `_commit` to always commit → the first test fails; restore.
- [ ] **Step 4:** measure a1 cells 0a (n 3), 0d (n 3), 0e (n 5) with `SENSORIUM_BIN=<worktree>/.venv/bin/sensorium`, `CONVERTER_REV=$(git rev-parse HEAD)`; §3 filled against spec §3.3's A1 prediction.
- [ ] **Step 5:** commit: `perf(ingest): one transaction per trace, synchronous=NORMAL — the converter's writer is non-durable (A1)`; then `test(acceptance): E10′ A1 measured`.

---

### Task 3: A3 — the streaming spool reader (and A2/A4 only by the numbers)

**Files:**
- Modify: `src/sensorium/ts/spool.py` (`Spool`, `read`, `_lines` removed, `_parse` kept).
- Modify: `src/sensorium/ts/build.py:141` (unchanged loop; `self.spool.exit` read after it — already so).
- Test: `tests/test_ts_ingest_meta.py` (lines 250–292 re-pointed; two new tests).
- Modify: the record §3 (a3 cells 0a, 0d, 0e + `maxrss_kb` before/after).

**Interfaces (verbatim shape — the refusal semantics are the product):**

```python
@dataclass
class Spool:
    path: Path
    boot: dict
    records: Iterator[dict] = field(default_factory=lambda: iter(()))
    exit: dict | None = None
    torn_tail: bool = False


def read(path) -> Spool:
    """BOOT read now from line 1; every later record yielded by `records` as
    the file is walked, `exit`/`torn_tail` filled by the time it is done."""
    path = Path(path)
    try:
        fh = open(path, "rb")
    except OSError as e:
        raise SpoolError(f"{path} cannot be read as a spool: {e}") from None
    first = fh.readline()
    if not first.endswith(b"\n") or not first.strip():
        fh.close()
        raise SpoolError(f"no BOOT record in {path}: the spool does not say what wrote it")
    boot = _parse(path, 1, _decode(path, 1, first))
    if boot.get("e") != "BOOT":
        fh.close()
        raise SpoolError(f"no BOOT record in {path}: line 1 is a {boot['e']} record, and the spool does not say what wrote it")
    sp = Spool(path=path, boot=boot)
    sp.records = _stream(sp, fh)
    return sp


def _stream(sp: Spool, fh):
    lineno = 1
    with fh:
        for raw in fh:
            lineno += 1
            if not raw.endswith(b"\n"):
                sp.torn_tail = True          # the tail a SIGKILL cut; dropped
                return
            line = _decode(sp.path, lineno, raw)
            if not line.strip():
                continue
            rec = _parse(sp.path, lineno, line)
            if rec.get("e") == "BOOT":
                raise SpoolError(f"two BOOT records in {sp.path}: two runtime instances wrote one spool")
            if rec.get("e") == "EXIT":
                sp.exit = rec
            yield rec
```
  `_decode` raises `SpoolError` naming the line on `UnicodeDecodeError`. A second BOOT now surfaces inside `Builder.build()`; `convert()`'s `except BaseException` aborts and unlinks the reserved file, and `_worker` returns the refusal as a value — the same outcome as today, later.

**Tests:**
- `test_a_torn_final_line_is_dropped_and_not_refused`: `list(sp.records)` has 119 entries and `sp.torn_tail` is True **after** the list.
- `test_a_spool_with_no_boot_names_the_file`, `test_a_malformed_line_anywhere_else_is_a_refusal`, `test_a_line_that_is_not_a_record_is_refused`: the refusal now comes from `list(spool.read(...).records)` where it came from `read()`; each re-pointed, message text unchanged.
- New `test_a_boot_that_is_not_line_one_is_refused_naming_the_line`: a two-line file `{"e":"SEEN"…}\n{"e":"BOOT"…}` → `SpoolError` mentioning `line 1`.
- New `test_a_second_boot_met_late_leaves_no_trace_behind`: `ingest_case("duplicate-boot")` → exit 2, the refusal line names the file, and `<sdir>/traces/` holds no `.tmp` and only the good spool's `.db` (extends `test_two_boot_records_name_two_runtimes`).

- [ ] **Step 1:** re-point the four tests and add the two; run: the two new ones fail.
- [ ] **Step 2:** the reader; full suite PASS; mutation: make `_stream` skip `sp.exit = rec` → `test_a_container_that_saw_its_own_ending_says_so` fails; restore.
- [ ] **Step 3:** measure a3 cells 0a, 0d, 0e; §3 filled with `maxrss_kb` before (a1) and after.
- [ ] **Step 4 (conditional, spec §3.3):** only if a3's 0d median > 22.5925 s: A2 — in `ingest_dir`, `work` sorted by `p.stat().st_size` descending before `_map`, summaries re-sorted by `Summary.file` before return (test: a 3-spool dir with sizes S<M<L converts in order L, M, S — pinned by monkeypatching `_worker` to record order — and prints in name order); measure `a2`. Still above: A4 — `TraceWriter.add_event` accepts `payload: dict | str | None` (a `str` is already-serialised JSON, stored as is; test: the stored `payload` column equals the string); `build.py` uses module constants `CALL_PAYLOAD = json.dumps({"args": {}, "unread": ["locals"]}, separators=(",", ":"))` and its `caller: "untraced"` twin; measure `a4`. Each lever its own commit and cell; neither built if the bound is already met.
- [ ] **Step 5:** commit: `perf(ingest): the spool is streamed, not materialised (A3)`; `test(acceptance): E10′ A3 measured`.

---

### Task 4: The equivalence gate and E10′'s verdict cells

**Files:**
- Create: `typescript/acceptance/e10p_eq.sh <spool copy> <scratch> <bin-A> <rev-A> <bin-B> <rev-B>`, `typescript/acceptance/e10p_eq_report.py`.
- Modify: the record §3 (`E10′-eq`, `E10′-suite`, `E10′-file`), §4 (the three verdicts, and the ladder's reading).

**Interfaces:**
- `e10p_eq.sh`: two fresh copies, two fresh stores; `<bin-A> ts ingest <copy-A>` into store A (untimed), `<bin-B> ts ingest <copy-B>` into store B; each `run:` line parsed (`run: <id>  pid: <pid>  file: <f>  …`); pairs keyed by `file` — refuse if either side repeats a `file` or the key sets differ; for each pair `SENSORIUM_DIR=<store-B> <bin-B> diff <run-A-path> <run-B-path>` … **the reader takes run ids in one store**, so store A's `.db` files are hard-linked into store B's `traces/` under their own names first (`ln`, same filesystem), and `diff <idA> <idB>` runs there. Exit codes tallied: 0 MATCH, 1 DIVERGED, 3 REFUSED, anything else `other`. Row counts per table via `sqlite3 <db> "SELECT COUNT(*) FROM <t>"` for the seven tables; meta keys whose values differ collected per pair. Report cell: `{value: matches, n: pairs, dropped, diverged, refused, other, row_counts_equal_pairs, meta_keys_differing (a sorted set over all pairs), converter_a: {bin, rev}, converter_b: {bin, rev}}`.
- A = main's converter (`~/workspace/sensorium`'s global tool, rev `bbd0781`); B = the worktree at the tip after Task 3 (or Task 3's conditional levers).
- The verdict cells: `e10p.sh f08e89 … final 16 5` and `e10p.sh one … final-file 16 5` with the worktree's converter.

**Invariants:** the `diff` used for every pair is one binary (B's), so a difference cannot be the reader's; `meta_keys_differing` must be a subset of `{run_id}` — anything else is written into §5 and the gate STOPs; the verdict cells are the LAST timed cells and are not re-run.

- [ ] **Step 1:** the two files; dry run on `async-chain` + `each-names` copied together (2 pairs → 2 MATCH).
- [ ] **Step 2:** the real gate; then the two verdict cells; §3 and §4 filled: suite PASS/REPORTED, file PASS/STOP, eq PASS/STOP, each with its rule quoted (spec §3.4).
- [ ] **Step 3:** commit: `test(acceptance): E10′ — the equivalence gate and the verdict cells`.

---

### Task 5: The hook — Node strips, no JSX; the probes and controls; R45; R47

**Files:**
- Modify: `typescript/src/hook.mjs` (delete `strip`, `STRIP`, the `ts` handling that served only `strip`; the return); header comment rewritten.
- Modify: `typescript/test/hook.test.mjs`; `typescript/probes/check.mjs` (`runNodeTest`, `main`), `typescript/probes/package.json` (`probe:nodetest`), `typescript/probes/README.md`.
- Create: `typescript/probes/nodetest/ext.probe.test.mts`, `ext.probe.test.mjs`, `ext.probe.test.cjs`, `controls/enum.ts`, `controls/jsx.tsx`, `controls.mjs`.
- Modify: `src/sensorium/ts/ingest.py` (`ingest_dir`'s no-spools branch + `_no_spools()`), `tests/test_ts_ingest_meta.py`, `tests/test_ts_driver.py`, `tests/test_ts_live.py`, `docs/CARRIED-DEBT.md` (the `hook.mjs:98` citation → `hook.mjs` `load`).

**Interfaces:**
- The hook's ES-module return, verbatim:

```js
  const out = transformSource(code, file, { root: ROOT, ts, rtPath: RT_PATH });
  if (out === null) return loaded;
  tally.record(file, out, MANIFEST_DIR);
  if (MANIFEST_DIR) tally.write(MANIFEST_DIR, tally.containerTally());
  // Node's own format goes back with the edited source: `module-typescript`
  // is stripped by the stripper plain `node --test` already uses, `module`
  // is loaded as written. This hook erases nothing.
  const edited = out.code !== null ? out.code : code;
  return { format: loaded.format, source: edited, shortCircuit: true };
```
  `ts` stays `require`d from the root — the transform parses against it.
- `_no_spools(spool_dir) -> str` in `ingest.py`: reads every `manifests/_tally*.json` (via `_read_tally`); if at least one exists and every one has `files_transformed == 0` and a non-empty `excluded`, returns `no spools in {dir}: this run transformed 0 files and excluded {N} ({reason xN, …} across {k} tallies)` + (when `commonjs` is a reason) `; this recorder instruments ES modules only, so a CommonJS-only suite records nothing`; otherwise today's sentence. `ingest_dir` raises `IngestError(_no_spools(spool_dir))`.
- `probe:nodetest`: `node --import ../src/register.mjs --test nodetest/async.probe.test.ts nodetest/ext.probe.test.mts nodetest/ext.probe.test.mjs nodetest/ext.probe.test.cjs; node nodetest/controls.mjs; node check.mjs nodetest "$SENSORIUM_SPOOL" "$SENSORIUM_MANIFEST_DIR"`.
- `controls.mjs`: for each control, `spawnSync(node, [file])` and `spawnSync(node, ['--import', '../src/register.mjs', file], {env: {…, SENSORIUM_TS_ROOT: <probes>, SENSORIUM_TS_PKG: <pkg>, SENSORIUM_TIER: 'call', SENSORIUM_SPOOL: <tmp>}})`; extracts the first `ERR_[A-Z_]+` from stderr on each side; prints one JSON line per control `{control, plain, hooked, same}`; exit 1 if any `same` is false or either side exited 0.
- `runNodeTest(k, spools, manifestDir)`: `probes:present` now expects `nodetest/async.probe.test.ts`, `nodetest/ext.probe.test.mts`, `nodetest/ext.probe.test.mjs` and NOT a `.cjs` spool; `ext:mts:tasks` ≥ 1 task with `basis: "title"`; `ext:mjs:tasks` ≥ 1; `ext:cjs:tally` — the one `_tally-<pid>.json` whose pid is not any spool's pid reads `{files_transformed: 0, excluded: {commonjs: 1}}`.

**Tests (first):**
- `hook.test.mjs`: `a .mts under the root is instrumented and stripped by Node` (a `.mts` lib with a type annotation, imported from `main.mts`; stdout `2`; `called` has `helper`); `the hook erases nothing: a construct strip-only mode rejects fails as it fails plain` (an `enum` in `lib.ts`; `res.status` ≠ 0 and stderr contains `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`; and the same file run without the hook gives the same code); `a .tsx never reaches the hook` (`main.mjs` importing `./x.tsx` → stderr `ERR_UNKNOWN_FILE_EXTENSION`, no FILE record for it, tally does not count it).
- `test_ts_ingest_meta.py::test_a_directory_with_only_commonjs_tallies_and_no_spool_names_the_exclusions`: a spool dir with `invocation.json` and `manifests/_tally-1.json` = `{"files_transformed":0,"excluded":{"commonjs":2}}` → exit 2, stderr contains `excluded 2 (commonjs x2 across 1 tallies)` and `ES modules only`. And `..._with_a_transformed_file_keeps_the_old_sentence` (`files_transformed: 1`) → the old sentence.
- `test_ts_driver.py::test_a_commonjs_only_suite_is_refused_naming_the_exclusions`: a `cjs_project` minus `a.test.mjs`; `sensorium ts run -- node --test` → exit 2, stderr has the new sentence; plain `node --test` on it is green (the control).
- `test_ts_live.py::test_the_nodetest_probes_and_controls_pass_through_the_driver`: `sensorium ts run -- node --test <the four files>` from `PROBES`, then `node check.mjs nodetest <spool> <manifests>` → `ok`, and `node nodetest/controls.mjs` → exit 0.

- [ ] **Step 1:** hook tests + Python tests + the live test; run: fail as expected (`.mts` SyntaxError; enum passes under the old hook; the old sentence).
- [ ] **Step 2:** the hook; `npm --prefix typescript test`, `run check` PASS. The probes, controls, checker, npm script, README rows. R45. R47.
- [ ] **Step 3:** `SENSORIUM_TS_LIVE=1 pytest tests/test_ts_live.py tests/test_ts_driver.py`; corpus `--only-dir typescript --require-driver`; the H-probes row of §3 filled from `check.mjs`'s JSON and `controls.mjs`'s lines.
- [ ] **Step 4:** commits: `fix(hook): Node's own format goes back — the hook erases nothing, .mts loads (H1)`; `test(probes): one probe per extension and two controls under node --test (H2)`; `fix(ingest): a no-spool refusal names the CommonJS exclusions (R45)`; `docs(ledger): cite hook.mjs by function (R47)`.

---

### Task 6: E6″ — the instrument, the assembler, the session

**Files:**
- Create: `typescript/acceptance/e6pp.sh <lens dir> <manifest> <store dir> <out dir>`, `typescript/acceptance/e6pp_report.py`, `typescript/acceptance/assemble_slice2.py`.
- Modify: `typescript/acceptance/assemble.py` (`arm_stats`: `loads` collected in the same loop as `walls`, so a dropped run's load leaves with its wall); `typescript/acceptance/e6.sh` — one header line: `# Superseded by e6pp.sh (E6″, slice 2); kept as E6′'s instrument.`
- Modify: the record §2 (pins re-taken before the session), §3 (`E6″`), §4, §5.

**Interfaces:**
- `e6pp.sh`, in this order, refusing at any step that fails: (1) `cd <lens> && sha256sum -c <manifest>` → must be 748 OK / 0 FAILED, else refuse "the lens moved"; (2) before arm: 5 × [`wait_for_load` (copied from `arms.sh`), `npx vitest run` timed, one JSON line via `arm_line.py` with `ARM=before`]; (3) the call run: `SENSORIUM_DIR=<store> sensorium ts run -- npx vitest run`, its line with `ARM=call` (harness wall from `harness.json`, driver wall = the script's clock); (4) after arm: 5 × as (2) with `ARM=after`; (5) `sha256sum -c` again → `e6pp-manifest-after.txt`; the marker grep as `e6.sh` (searched list written); the wrapper listing. All lines to `<out>/e6pp.jsonl`.
- `e6pp_report.py`: reads the jsonl; `before`/`after` stats via `assemble.arm_stats(rows, arm, "wall")` (imported from the fixed assembler); `band = [median_before − (max_before − min_before), median_before + (max_before − min_before)]`; `in_band = band[0] <= median_after <= band[1]`; `usable` counts; the five clause booleans; emits the cell `{value: clauses held (0–5), n: 5, lens, dropped, manifest_before, manifest_after, before, after, band, in_band, call_run: {harness_wall, driver_wall, invocation}, markers, wrapper_dir, timing_clause: "held"|"STOP"|"STOP by instrument"}`.
- `assemble_slice2.py <results dir> <out> [PATH=LABEL]…`: `gated` = `E10′-0` (the five arm0 cells), `E10′-suite` (`e10p-final-full-j16.json`), `E10′-file` (`e10p-final-file.json`), `E10′-eq`, `E6″`, `H-probes`; `reported` = the a1/a3(/a2/a4) cells, RSS, 0b/0d, the call run's walls, the fresh set's ingest; the same redaction refusal as `assemble.py`.

**Tests:** `tests/test_acceptance_s5_slice2_tooling.py`: `arm_stats` drops a run's load with its wall (a 3-row table with one `ok: false` → `len(loads) == len(walls) == 2`); `e6pp_report`'s band arithmetic on a fixed five-wall table (median 22.5925, range 0.4085 → band `[22.184, 23.001]`); `in_band` false at 23.01; `STOP by instrument` when an arm has 3 usable walls; `assemble_slice2` refuses a surviving `/mnt/` string.

- [ ] **Step 1:** the tooling tests; run: fail; the assembler fix, the report, the assembler; PASS.
- [ ] **Step 2:** `e6pp.sh` dry run on `typescript/probes` with a 2-file manifest and n forced to 1 (an `E6PP_N` env, default 5, for dry runs only — recorded in the JSON).
- [ ] **Step 3:** the session on the lens (≈ 15 min with guard waits), run in the foreground under `setsid` with a pid file; nothing else running on the box; §2's loads re-taken before it starts.
- [ ] **Step 4:** §3/§4/§5 filled; the rung-1 spec's §11 gets its dated line; `assemble_slice2.py` writes the results file; commit: `test(acceptance): E6″ measured — <verdict>`.

---

### Task 7: Land it — documents, versions, the ledger

**Files:**
- Modify: `typescript/HONESTY.md` §7 (dated: Node strips, the hook erases nothing; `.tsx`/`.jsx` outside Node's scope under `node --test`; the R45 sentence), §9 (E6″ and E10′'s numbers, the STOP word where the record uses it); `typescript/README.md` (the `src/hook.mjs` row: "instruments a file under the root and hands it back in Node's own format; Node strips"); `README.md` (`sensorium-ts 0.1.0` → `0.1.1` on line 722 — one token, no new line); `CHANGELOG.md` (cut `## 0.8.4` to `CHANGELOG-ARCHIVE.md` with the archive's dated note, then the `## 0.9.1 — <date>` entry); `pyproject.toml` `0.9.1`; `typescript/package.json` + `typescript/src/index.mjs` `0.1.1`; `typescript/test/rt.test.mjs:63`, `src/sensorium/ts/wrapper.py:57`, `tests/test_ts_live.py:200`, `tests/test_ts_wrapper.py:84` (`sensorium-ts 0.1.1`); `docs/CARRIED-DEBT.md` (measure first; the slice's section: settled — E6″, E10′, H1–H4, the `loads` fix, the materialised-whole residual struck; deferred — A2/A4 if unbuilt, Arm B by ruling, anything §5 of the record raised); this slice's spec (a §12-style "what changed against this design" table if any decision above moved the text).
- Reinstall the three venvs (`uv pip install -p .venv/bin/python -e .` etc.) so `importlib.metadata` reads 0.9.1 (`test_release_tokens.py`).

**Invariants:** `test_release_tokens.py` green (the newest CHANGELOG header agrees with `pyproject`); `tests/test_ceiling.py` green; the three fixture-borne `0.1.0` strings (`tests/test_ts_ingest_meta.py:31`, `test_exceptions_rust_gate.py:268`, the fixtures' BOOT) are NOT changed — they are what those spools carry.

- [ ] **Step 1:** the cut, then the entry; versions; the four string sites; reinstall; full suite on 3.12/3.13/3.14 + npm + corpus + live.
- [ ] **Step 2:** HONESTY, READMEs, the ledger (line count before/after quoted in its own header sentence), the spec pointers.
- [ ] **Step 3:** commits: `chore(release): sensorium 0.9.1, sensorium-ts 0.1.1`; `docs: HONESTY, READMEs, CHANGELOG and the ledger for slice 2`.

---

### Task 8: Final review, one fix wave, the PR

- [ ] **Step 1:** superpowers:requesting-code-review over the whole branch (fable); Critical/Important fixed in ONE wave, each fix its own commit; minors parked in the ledger with a ruling.
- [ ] **Step 2:** the byte-lock test, the full suites, the corpus and the live suite once more on the tip; `git push -u origin feat/s5-slice2`; `gh pr create` with the verdicts as measured; CI green; merge is Brice's.
- [ ] **Step 3:** archive the SDD ledger to `/mnt/extra/sensorium-rung2/sdd-archive/2026-09-10-sensorium-s5-slice2/`; after the merge, `git worktree remove`, delete the branch local + remote, verify `origin/main` sync, reinstall the global tool (`uv tool install --reinstall --python 3.13 -e ~/workspace/sensorium`), and tell Brice `store-rung1`/`acceptance-rung1` may go (the copies under `e10-spool/` stay with the record).

---

## Self-review against the spec

- **§2 E6″** → Task 6 (session order 2.1, rule 2.2 including the <4-walls STOP-by-instrument, instrument 2.3 with `e6.sh` untouched, disposition 2.4 written into §4 by the outcome). **§3 E10′** → Task 0 (workload 3.1), Task 1 (Arm 0, 3.2), Tasks 2–3 (A1, A3; A2/A4 conditional, 3.3), Task 4 (rules 3.4, gate 3.5), §3.6 reported cells across Tasks 1–6, §3.7 recorded in the record's §4. **§4 the hook** → Task 5 (H1–H4, probes 4.5). **§5** → P8 and the ` > ` decision stated in Task 7's ledger section. **§6 testing** → each task's tests; mutation checks in Global Constraints. **§7 order** → Tasks 0–8 in that order. **§8** → Task 7. **§9/§10** → Task 7's ledger and the PR body.
- **Placeholders:** none — every instrument has its arguments and output shape, every test its assertion, every sentence its text.
- **Type consistency:** `TraceWriter(durable=)` / `Builder(durable=)` (Tasks 2, 3); `Spool.records: Iterator[dict]` (Task 3, `list(sp.records)` in tests); `_no_spools(spool_dir) -> str` (Task 5); `assemble.arm_stats(rows, arm, key)` reused by `e6pp_report.py` (Task 6); `e10p.sh <spool copy> <scratch> <label> <jobs> [n]` everywhere it is invoked (Tasks 1–4); `check.mjs nodetest <spool> <manifests>` (Task 5, P7).
