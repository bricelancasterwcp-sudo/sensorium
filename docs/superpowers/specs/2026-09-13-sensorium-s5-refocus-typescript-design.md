# S5, the refocus slice — `refocus` for TypeScript traces, and E15

**Date:** 2026-09-13 · **Status:** design, approved in conversation
(Brice, 2026-09-13: "refocus only, fold the `_MORE` removal, go") ·
**Design authority:** Claude · **Base:** main `5ab9861` (Python 0.13.0;
`sensorium-ts` 0.4.0; crates rt 0.5.0 / transform 0.5.0 / driver 0.6.0) ·
**Branch:** `docs/s5-refocus-ts-design` (this document and its plan), then
`feat/s5-refocus-ts` for the work.

Rung 4 (`docs/superpowers/specs/2026-09-11-sensorium-s5-rung4-focus-tier-design.md`)
gave TypeScript traces LINE rows and locals under a transform-time `--focus`
and named `refocus` its non-goal, "next slice, on these rows". The debts slice
(`docs/superpowers/specs/2026-09-12-sensorium-s5-rung4-debts-design.md`) paid
rung 4's list and carried Brice's scope ruling: debts first, then refocus for
TypeScript as its own slice. This is that slice. `sensorium refocus` answers on
a TypeScript trace by re-running the recorded harness invocation one flag
deeper, finding the pair in the store, and comparing it under the comparator
every language shares. The Rust slice that did the same
(`docs/superpowers/specs/2026-09-07-sensorium-rung4-refocus-design.md`, rulings
G1–G3, amendments B1–B3) is the precedent, and where JavaScript's harness is
not cargo this document says so and why.

## 0. Rulings this design rests on

Brice's, 2026-09-13, both about scope:

| # | Ruling | What it settles |
|---|---|---|
| S1 | **refocus only.** The C conversation (spec 2026-09-12 §9, the 44 design-level rows) is **dropped**, not on hold; so is the token-cost measurement (branch `feat/token-cost-measure`, local only, never pushed, 21 commits kept as a record). Nothing on `main` names either. | this slice ships one command on one recorder, and `docs/CARRIED-DEBT.md`'s cut records the two drops with their date |
| S2 | **fold the `_MORE` removal.** `js_inspect._MORE`, the alias kept "for one release (0.13.0)", is removed at the next Python minor — which is this one. | 0.14.0 removes it; the debts section's item is struck where it stands |

Claude's, each with the alternative it rejected:

| # | Question | Ruling | Why |
|---|---|---|---|
| R1 | what is re-run? | **the whole recorded invocation** — the harness command as typed, from the recorded working directory, into the same store, with the original's focus plus the caller's | a narrowed re-run (the one test file appended as a filter) is a command nobody typed, and vitest's positional filter is a SUBSTRING match `corpus/typescript/README.md` already documents as a trap; refusing every multi-file invocation (Rust's rule) is honest and useless — the lens is 372 files |
| R2 | what is the unit of the verdict? | **one member trace**, the one the caller named. The verdict and the licence are the PAIR's; the re-run's other containers are counted, stamped with the link, and left `UNVERIFIED` | a verdict over 372 pairs is a different command with a different report shape (§7); a member's own question is what every language's `refocus` answers |
| R3 | how does the new trace learn the link? | **`--refocus-of <run>` on `sensorium ts run`**, written into `invocation.json` and lifted by the converter into every member's `meta.refocus_of` | the Rust ruling G3, for the Rust reason: the link is durable in the trace and read by `info`/`runs` the same way for both languages; nothing parsed from the driver's stdout is load-bearing |
| R4 | how is the pair found among the members? | **by `test_file`** where the original carries one; **by `argv`** where it carries neither `test_file` nor `test_files` (a `node --test` process, a `globalSetup` container); a **`test_files`** original (a reused worker that ran several files) **refuses before the re-run** | which container of a re-run would pair with a reused worker is the harness's scheduling, not a fact; the other two keys are the converter's own statement of what the container ran |
| R5 | where does the re-run happen? | **a subprocess of the same interpreter** — `python -m sensorium ts run …` — announced as `sensorium ts run …` with the interpreter named on a second line | the driver is this package, so no PATH question and no `SENSORIUM_CARGO_SENSORIUM` analogue; a process boundary keeps the driver's `chdir`, its exit and its stdio out of the command that is waiting on it, and makes the announced command the executed one |
| R6 | what tier does the re-run use? | **the original's**, read from its recorded `env.SENSORIUM_TIER` (absent → the driver's default, `call`); an original at **`off`** refuses before the re-run | the Rust rule, and `off` holds no causal stream — the comparator would REFUSE after a whole suite had run |
| R7 | which licence checks can a TypeScript pair run? | source and environment for real; **threads join output and children as UNVERIFIABLE**, keyed on `capabilities.threads: false` exactly as the two existing markers are keyed on theirs | today the thread block prints the declared-false witness gap as a CAVEAT, which withholds every TypeScript licence for a check that could not run — the named bug class, one check further along. Rust declares `threads: true` and Python declares everything, so neither reads differently |
| R8 | which environment variables are the tool's, on a TypeScript pair? | every **`SENSORIUM_*`** key is the recorder's own — excluded and NAMED on the line; **harness set 1** = `VITEST_POOL_ID`, `VITEST_WORKER_ID` — counted and named, never withholding, versioned in the printed line the way session set 1 is | a focused re-run mints a new `SENSORIUM_INVOCATION`, `SENSORIUM_SPOOL`, `SENSORIUM_MANIFEST_DIR` and `SENSORIUM_FOCUS` by definition; a worker's slot is the pool's bookkeeping. Nothing else is excluded: `VITEST`, `VITEST_MODE`, `TEST`, `NODE_ENV` are constants the harness sets and are compared like any other key |
| R9 | what is the exit check on a TypeScript pair? | **`harness_exit`** (status and signal, `basis: waited`) equal on both invocations, and **`exit_self_reported`** equal on both containers; `exit_status`, `null` on both sides, is **never read as agreement** | every vitest worker ends by SIGTERM from its pool, so the container's own ending says nothing about the run; what the driver waited for does |
| R10 | what does the new trace declare? | `capabilities.refocus: true` for **every** trace this driver converts; whether one PARTICULAR trace can be refocused is a refusal, not a capability | the Rust rule (design 2026-09-07 §2.2); a capability is a statement about the recorder |
| R11 | versions and format | Python **0.14.0**; `sensorium-ts` **0.4.0 unchanged** (no file under `typescript/src/` moves); `TRACE_FORMAT` **4 unchanged**, two OPTIONAL meta keys (`harness_cwd`, `refocus_of`), one vector (`v41`) | the link and the working directory are the driver's facts and the converter's keys; the runtime is untouched |
| R12 | seams | new modules for the branch, its tests and its honesty section; `README.md` (799) net-zero; `typescript/HONESTY.md` (794) takes a two-line pointer and gives two lines back | the ceiling census in `docs/CARRIED-DEBT.md` §2026-09-12 names each of these as a file whose next edit must take a seam |

## 1. What ships

1. **Driver** (`src/sensorium/ts/driver.py`, `cli.py`): `sensorium ts run
   --refocus-of <run-id> [--tier …] [--focus …]… -- <harness command>`;
   the value validated before anything is minted; `refocus_of` in
   `invocation.json`.
2. **Converter** (`src/sensorium/ts/build.py`, `invocation.py`): `harness_cwd`
   and `refocus_of` in meta; `capabilities.refocus: true`.
3. **Python**: a TypeScript branch of `sensorium refocus`
   (`src/sensorium/query/refocus_typescript.py`, new) — seven pre-rerun
   refusals, the subprocess re-run, the pair lookup by key, the unchanged
   comparator, the TypeScript licence (§3), the stamps.
4. **The shared licence code** learns one thing: threads can be unverifiable
   (`refocus_world.py`); the two helpers a second language needs
   (`_relicense`, the unverifiable stamp) move out of `refocus_rust.py` into
   `refocus_world.py` as pure moves.
5. **Vocabulary**: the TypeScript `no_rerun_note` and `refocus_blind_spots`
   rewritten (§3.5); `rerun_command` unchanged.
6. **Corpus**: three TypeScript cases (`refocus_match`, `refocus_diverged`,
   `refocus_refused_reused_worker`); Python tests on fixture traces; the
   E15 record and instrument; docs; the `_MORE` removal; versions.

## 2. The re-run path

### 2.1 Driver

`--refocus-of <run-id>` is parsed where `--tier` and `--focus` are — before
the `--`, so a harness's own flag after it is never stolen. The value is
checked FIRST among the driver's own refusals, before `check_node`, because it
is about the call and nothing else: one trailing `.db` is stripped so
`<id>.db` names `<id>`; a value `paths.is_valid_run_id` rejects (a separator,
`.`, `..`, empty) refuses with `--refocus-of <v> is not a run id; nothing was
run.`; a value naming no `<store>/traces/<id>.db` refuses with `--refocus-of
<id> names no trace in <store>; nothing was run.` Both exit 2 and mint
nothing. The value is recorded in `invocation.json` as `refocus_of` and
reaches every container of the invocation through the converter. The driver
changes in no other way: `recognise`, the wrapper, `_env`, the spawn and the
conversion are rung 4's.

### 2.2 Converter

Two optional meta keys, so `TRACE_FORMAT` stays 4:

| key | value | source | present |
|---|---|---|---|
| `harness_cwd` | the directory `sensorium ts run` was invoked from, absolute | `invocation.json`'s `cwd`, which every record since the driver's first version carries | unconditional for every spool converted by 0.14.0 or later — a re-ingest of an older spool directory gets it too |
| `refocus_of` | the original run id | `invocation.json`, when `--refocus-of` was given | absent otherwise |

`harness_cwd` is a different fact from `cwd`: `cwd` is the CONTAINER's, which
for a vitest worker is the root the pool started it in, and `root` is the
plan's; the harness command's relative arguments (`vitest run src/fog`) are
relative to neither — they are relative to where the person typed the
command, which is what a re-run has to reproduce. `capabilities.refocus` is
`true` for every trace this converter writes (R10). `info` prints
`harness cwd: <path>` on the line after the harness line when the key is
present, and prints `refocus-of:` through the block it already prints for
the Python and Rust keys (`info_cmd.py`, the `refocus_of` block); `runs`
flags the member row `refocus-of:<id>` through the generic path it already
has.

### 2.3 Python: the branch

Dispatch on `trace.lang == "typescript"` directly after the Rust dispatch
(`refocus_cmd.run`), after the two shared gates (`capabilities.refocus`,
`incomplete`) and before Python's own — for the Rust reason: the sentences a
TypeScript user meets arrive in the order this section fixes, not behind a
gate whose words name a fact about the Python recorder.

**Pre-rerun refusals** (exit 2, `BAD_CALL`, nothing launched), in this order.
Each is announced by `refocus_cmd._refuse` as `error: cannot refocus <run>:
<sentence>`; the sentences carry no prefix of their own (Rust amendment B3),
and every one ends `; nothing was re-run`. Each is followed by the
TypeScript `no_rerun_note` (§3.5), which names the command that can record
this project afresh.

| # | condition | sentence |
|---|---|---|
| 1 | `--window` given | `--window is not available for a TypeScript trace (the recorder has no per-activation gate); nothing was re-run` |
| 2 | recorded `env.SENSORIUM_TIER == "off"` | `run <id> was recorded at --tier off and holds no causal stream to compare against; nothing was re-run` |
| 3 | `harness_command` absent | `run <id> records no harness command to re-run (recorded by a driver before the key existed); nothing was re-run` |
| 4 | `harness_cwd` absent | `run <id> records no working directory to re-run from (recorded by sensorium ts 0.13.0 or earlier); nothing was re-run` |
| 5 | `harness_cwd` no longer a directory | `directory <path> no longer exists; nothing was re-run` |
| 6 | `root` no longer a directory | `project root <path> no longer exists; nothing was re-run` |
| 7 | `test_files` present (a reused worker) | `run <id> ran <n> test files in one container (a reused worker); which container of a re-run would be its pair is the harness's scheduling, not a fact; nothing was re-run` |

The seventh is the one Rust has no counterpart for and the one R4 is about.
A container that carries neither `test_file` nor `test_files` is NOT refused:
its argv is its key (§2.4).

**The re-run.** argv = `[sys.executable, "-m", "sensorium", "ts", "run",
"--refocus-of", <run>, "--tier", <tier>, "--focus", v1, "--focus", v2, …,
"--", *harness_command]` where `<tier>` is R6's and the focus list is the
original's `meta.focus` followed by the caller's `--focus` values in that
order, de-duplicated by `refocus_cmd._merged_focus` — never fewer than the
original's, so a refocus only ever captures MORE. cwd = `harness_cwd`.
Environment: the caller's, with `SENSORIUM_DIR` set to the original's store
resolved ABSOLUTE (the `_pin_trace_store` reason: a relative value would
follow the child into the project and write the new traces where the pair
lookup never looks), and nothing else set or stripped — the two traces'
recorded environments are what the licence compares afterwards. stdio is
INHERITED, all three streams: the harness's output is what a person waiting
on a suite is watching, and the driver's own `run:` lines print live with
it. Nothing is captured and nothing printed is parsed. No timeout, as for
the other two branches. The announced lines:

    refocus-of: <run>   cmd: sensorium ts run --refocus-of <run> --tier call --focus fill -- npx vitest run
    via: <interpreter> -m sensorium
    cwd: <harness_cwd>
    focus: fill   window: -
    source: …
    --- rerunning (the harness's own output follows; the driver's run: lines print with it) ---

`source:` is `_source_state(meta)` before the re-run, as the other branches
do it: the TypeScript converter records `source_hashes` under ABSOLUTE paths
(`build.py`, `_on_file`), so they re-hash from any working directory and a
changed file is known before a suite is spent on it.

### 2.4 The pair

After the child exits, Python lists the store's traces LINKED to the
original: `meta.refocus_of == <run>` and `start_ts >= launched_at` (so an
EARLIER refocus of the same original is not mistaken for this one). Among
the linked, the CANDIDATES are those whose KEY equals the original's:

- the original carries `test_file` → a candidate carries the same
  `test_file`;
- the original carries neither `test_file` nor `test_files` → a candidate
  carries neither and its `argv` equals the original's.

Exactly one candidate → the pair. Zero → `verdict: REFUSED` after the re-run,
exit 3: `the re-run produced <n> trace(s) linked to <run> and none ran <key>
(harness exit <status>); see the harness's output above`. More than one →
REFUSED, exit 3, by count, naming them: two containers of one invocation
that both claim one test file is a fact about the harness this tool will
not guess through. The linked traces that are not the pair are its
**siblings**: counted on the pair line, stamped nowhere but by the driver's
own `refocus_of`, and listed by `runs` under the new invocation's header
with `verdict:UNVERIFIED`, which is what they are.

The pair line:

    run: <new>   invocation: <new invocation>   siblings in the re-run: 371 (not compared; UNVERIFIED)

`refocus_siblings` (the COUNT) is stamped into the pair's meta beside the
verdict, so `info` can say it after the terminal has scrolled; the ids are
not stamped, because the invocation id already names them and a list of 371
ids is not a thing a reader follows.

## 3. Verdict, licence, what prints

### 3.1 Verdict

`diff_cmd.compare(orig, new)` unchanged. A TypeScript pair compares under the
per-task basis: the main stream is what ran in no test, and every test is a
task named by its title (`task_name_basis: vitest`), compared as an
order-independent multiset of `(name, hash)` over CALL, RETURN, RAISE and
HANDLED. LINE rows never enter the hash, which is what lets a focused re-run
MATCH the unfocused run it came from (rung 4 §5, `CAUSAL_KINDS`). MATCH,
DIVERGED and REFUSED keep their meanings and exits (0 / 1 / 3). The stamps
are `refocus_report._stamp`'s, written into the NEW trace's meta through the
same `db.set_meta`.

### 3.2 Licence on a TypeScript pair

| check | TypeScript | reads |
|---|---|---|
| source | runs for real | `source_hashes` (the files the transform edited in that container, absolute) re-hashed now |
| environment | runs for real, under §3.3's two sets | `env` recorded in both traces — never this CLI's own environment |
| output | **UNVERIFIABLE** | `capabilities.output: false` — the existing marker |
| children | **UNVERIFIABLE** | `capabilities.children: false` — the existing marker |
| threads | **UNVERIFIABLE** (new, R7) | `capabilities.threads: false`: a worker thread or forked child of the program is its own trace, unlinked; the thread block's declared-false witness gap is no longer appended as a caveat when this marker is present |
| exit | runs for real (R9) | `harness_exit` on both invocations; `exit_self_reported` on both containers |

`refocus_world.unverifiable_checks` gains the third marker,
`UNVERIFIABLE_THREADS = "threads: unverifiable (not witnessed)"`, and the
`UNVERIFIABLE` tuple and `_SHORT_UNVERIFIABLE` map grow by one so `info`'s
replay names it. `_licence_caveats` skips the thread witness-gap sentence
when the marker is in the pair's unverifiable set, the way it already skips
the output cross-check and the children gap for theirs. An unverifiable check
is never counted as a verified one; the two counts print as two numbers and
are never summed. `refocus_rust._relicense` and `_stamp_unverifiable` become
`refocus_world.relicense` and `refocus_world.stamp_unverifiable` — pure
moves, the Rust branch importing them from there — because a second language
needs them and a sibling importing a sibling is a cycle waiting to happen.

The exit check is the branch's own two clauses, passed to `assess` in its
`world_caveats` / `world_verified` lists as the source and environment facts
are: `the two invocations' harnesses ended differently: exit 0 originally,
exit 1 on the rerun` withholds; `the two containers reported different
endings: SIGTERM originally, exit 1 on the rerun` withholds; when both agree
the verified fact reads `harness exit equal (0, waited); container endings
equal`. The shared clause over `exit_status` stays as it is and is silent
over `null == null`; the branch's `exit:` line prints the harness exits and
never `?`.

### 3.3 The environment's two sets

The recorded `env` of the original's container is compared against the
recorded `env` of the pair's — `refocus_rust._env_of`'s rule, which becomes
a shared helper taking the recorder-key predicate as an argument. On a
TypeScript pair:

- **the recorder's own** — every key starting `SENSORIUM_` — is taken OUT
  of the compare and NAMED: `; the recorder's own variables not compared:
  SENSORIUM_FOCUS, SENSORIUM_INVOCATION, SENSORIUM_MANIFEST_DIR,
  SENSORIUM_SPOOL, SENSORIUM_TIER, SENSORIUM_TS_PKG, SENSORIUM_TS_ROOT`.
  Compared, four of them fire on every refocus by construction and a check
  that always fires says nothing.
- **harness set 1** — `VITEST_POOL_ID`, `VITEST_WORKER_ID` — is the one
  enumerated exception of the harness's own: a member that differs is
  counted, named and never withholds, in the words session set 1 uses:
  `env: unchanged outside session set 1 and harness set 1 (<N> variables
  compared; …; 2 harness variable(s) differ: VITEST_POOL_ID,
  VITEST_WORKER_ID)`. The set lives beside `SESSION_SET` in
  `refocus_env.py`, versioned in the printed line so a key found to bear
  can leave with a date. A `node --test` process carries neither key and
  the clause is simply absent.
- everything else — the shell's, the session's, npm's `npm_*` keys from an
  `npx` launch, `NODE_ENV`, `VITEST`, `TEST` — compares exactly as it does
  on a Python or Rust pair, session set 1 included.

### 3.4 The verdict's own words

The categorical blind-spot block is `vocab.TYPESCRIPT`'s, printed on every
verdict; after it, this recorder's own lines (`refocus_blind_spots`), rewritten
for a recorder that CAN be re-run:

- `output not recorded (capabilities.output: false)`
- `the whole recorded invocation was re-run; its other containers were not compared and stay UNVERIFIED`
- `the harness's worker-slot variables (harness set 1) were not compared`
- `a worker thread or forked child of the program is its own trace, unlinked to this pair`

The line `arguments are not read in this version (capabilities.locals:
false)` is retired: it has been false on every focused trace since rung 4.
The E7 needle (`sensorium run --focus` must not appear on TypeScript output)
stands, and no new sentence contains that spelling.

### 3.5 The note when nothing was re-run

`vocab.TYPESCRIPT.no_rerun_note` becomes `no rerun was attempted;
`sensorium ts run --focus <file>:<qualname> -- <harness command>` will record
a fresh, UNVERIFIED invocation if that is what you want` — the Python and
Rust shape, naming the command that can record this project and never
`sensorium run`, which cannot. The words `refocus is not yet this recorder's`
are retired with the fact.

## 4. Corpus cases, tests, mutations

### 4.1 Three TypeScript corpus cases

Each is a real re-run inside the gate: the corpus runner records the case
once under `sensorium ts run`; a `refocus` question then re-invokes the
driver itself from the case's copied project, whose `harness_cwd` is that
copy and is still there when the question runs. The corpus project's
`node_modules` must be installed (`npm ci --prefix corpus/typescript`); the
plan's first task does it, since this box has none today.

| case | program | pins |
|---|---|---|
| `refocus_match` | one test file over a deterministic `fill()` in a `src/`-style module; `harness_args: ["run", "refocus_match/"]` | `refocus $RUN --focus fill` → `verdict: MATCH`, exit 0; the announced command with `--refocus-of $RUN`, `--tier call`, `--focus fill`; `siblings in the re-run: 0`; the licence line with `WITHHELD` absent; the three unverifiable markers named; `runs` → `refocus-of:$RUN` beside `verdict:MATCH(granted:N,see-info)` and two invocation headers; `info last` → `refocus-of: $RUN`, `verdict: MATCH`, `licence: granted`, `line=yes locals=yes`, `harness cwd:`; `watch last --at fill --expr b == 2` SATISFIED — the loop |
| `refocus_diverged` | the `nondeterministic` shape: a counter file outside the process decides the branch, so the re-run takes the other one | `refocus $RUN --focus main` → `verdict: DIVERGED`, exit 1, `at causal step N:` with both sides named |
| `refocus_refused_reused_worker` | two test files; `harness_args: ["run", "refocus_refused_reused_worker/", "--no-isolate", "--maxWorkers", "1"]` (vitest 4.1.9's spellings, checked on the lens's own binary), so ONE fork runs both files and the container carries `test_files` | `refocus $RUN --focus …` → refusal 7's sentence, exit 2; `runs` → exactly one invocation header, the store unchanged |

`docs/corpus.md` gains their entries; `corpus/typescript/README.md`'s count
moves from forty-two to forty-five and its focus-case count from ten to
thirteen (each of the three records under a focus of its own, so the new
trace can be asked a per-statement question).

### 4.2 Python tests on fixture traces

`tests/test_refocus_typescript.py` (new) on `tests/ts_traces.py` builders:
every pre-rerun refusal in §2.3's order; the key rule (test_file, argv,
`test_files` refused); the pair lookup with 0 / 1 / 2 candidates and with
siblings; the merged-focus order; the argv construction (tier from env,
default when absent); the recorder's own set named and never counted, harness
set 1 counted and never withholding, a key that merely resembles a member
still withholding, a session key beside a real change withholding and naming
both; the three unverifiable markers present and never "verified"; the exit
clauses on differing `harness_exit` and differing `exit_self_reported`; the
stamps (`refocus_of` link, `refocus_siblings`, the unverifiable list).
`tests/test_ts_ingest_refocus.py` (new — `test_ts_ingest_meta.py` is at 785):
`harness_cwd` and `refocus_of` lifted from `invocation.json`, `refocus_of`
absent when not given, `capabilities.refocus: true`, the driver flag's three
refusals and its `.db` strip. `tests/test_refocus_licence.py` and
`test_refocus_licence_rust.py` pin that a Python and a Rust pair print
exactly what they printed before this slice.

Every test file names its pre-registered mutations in a module docstring and
the plan's task runs them: the key rule reading `test_files` as a key; the
lookup ignoring `launched_at`; the recorder set letting a `SENSORIUM_` key
withhold; harness set 1 withholding; the thread marker missing from the
tuple; the exit clause reading `exit_status`; the sibling count off by the
pair; the driver accepting `../x`.

## 5. E15, pre-registered

Record `docs/superpowers/acceptance/2026-09-13-sensorium-e15-refocus-typescript.md`;
§1 committed alone and byte-locked before the instrument exists, on the
`tests/test_acceptance_s5_debts_lock.py` pattern (a content sha, recomputed
on the working tree, with the amendment discipline that file documents);
instrument `typescript/acceptance/e15.py` (the loop, detached with markers,
`.DONE`/`.FAILED` with `exit=<n>`, env-var locations only), `e15_report.py`
(the cells, both readings), `assemble_e15.py` (`lens.stamp`, provenance,
writes-then-exits-1 on a provenance failure, ruling P9 of the debts slice).
Subject: a throwaway copy of the lens (`copy_lens.sh`) at VTT `0091e97`,
`typescript/acceptance/LENS.txt`'s own words, `node_modules` symlinked; a
fresh `SENSORIUM_DIR`; the `sensorium` of this branch (`lens.sensorium_bin`),
whose editable install is refreshed at preflight so that `driver_version`
reads **0.14.0** on every trace the record cites — the driver reads its
version from package metadata, and a stale install would stamp the previous
release's number on this slice's data.

**The originals.** ONE unfocused recording of the whole suite: `sensorium ts
run -- npx vitest run` from the copy's root — the harness command as the
rung-1 arms typed it. Its member count is `U`; every later count is read
against it.

**The selection, written first.** `find src -name '*.test.*' | LC_ALL=C
sort`, every twelfth file starting at index 0 — **31** of 372. For each, a
HAND survey classes it deterministic or names its source of divergence
(`Math.random`, a clock, a real timer, a network call, an order the program
does not fix), and names ONE focus spec: the first function, in source
order, of the first `src/` module the test file imports that
`resolve.mjs` selects; if the file imports none, the first function the
file itself defines. The list — file, class, reason where not
deterministic, focus spec, `node resolve.mjs`'s count for it — is §1's table
and is byte-locked. The expected-MATCH list is the deterministic rows. No
exception is invented for a file the survey cannot read; such a file is
listed as `unsurveyed` and its verdict is a reading, not a gate.

**Loop.** For each of the 31: `sensorium refocus <member> --focus <spec>`,
where `<member>` is the original's trace for that file — 31 whole-suite
re-runs. Then the two controls. Then the reads.

| id | question | endpoint (both readings pre-committed in §1) |
|---|---|---|
| H1 | does every original refocus without a pre-rerun refusal? | **0 of 31** refusals — each member carries `harness_command`, `harness_cwd`, one `test_file`, tier `call` |
| H2 | does every re-run complete? | **31 of 31** harness exits equal to `U`'s (status, signal, `waited`); a harness that ended differently is a **finding** carrying the exit, not a STOP |
| H3 | is the pair found, and how many siblings? | **31 of 31** exactly one candidate by `test_file`; linked count = `U`'s member count on **31 of 31**; a REFUSED after the re-run on the lookup is a **STOP** (the pairing) |
| H4 | MATCH on the expected list? | MATCH on every deterministic row; an unexpected DIVERGED is a **finding** recorded with the divergent event (E4's own reading); a REFUSED from the comparator is a **STOP** |
| H5 | what does the licence say? | reported per pair and summed: source verified **31 of 31**; environment verified **31 of 31** with the recorder's set NAMED on every line and harness set 1's count where it differs; output, children, threads UNVERIFIABLE **31 of 31**, each printed; harness exit equal **31 of 31**; **0** licence lines claiming an unverifiable check as verified; GRANTED on every MATCHed deterministic row (the expected-granted list is the expected-MATCH list — nothing in a per-file container's world is expected to move) |
| H6 | does the loop close? | three `watch --at <spec> --expr …` triples and one `flow --value` on three NEW traces named in §1, answering as predicted (verdict class and exit) |
| H7 | control B — a planted edit | `plant_edit.py` appends one failing test to one selected file in the copy; its refocus reads `source: CHANGED` naming the file and `licence: WITHHELD` with that reason, whatever the verdict; **1 of 1** |
| H8 | control C — a refusal | `refocus <member> --window 1` on one original: exit 2, the §2.3 sentence, and the store's trace count UNCHANGED before and after; **1 of 1** |
| H9 | what does it cost? | reported, no gate: per refocus the wall from launch to verdict, the harness's own `Duration`, the conversion's wall, the spool bytes and trace bytes the invocation added; the store and spool totals at the end |
| H10 | did nothing else move? | corpus every case equal, all three languages, `--require-driver`, the three new cases included; pytest; `cargo test --workspace`; `npm --prefix typescript test`; the probes; `tests/test_ceiling.py`; the E7 needle on the new output; `e_fences.py` legacy and branch, with the fence's report listing NO fenced path (this slice touches none: `rust/` is untouched, `exceptions*.py` untouched) |

**Kill rules.** As E4 and E12′: a `.FAILED` before any number is
infrastructure (archive, empty the fresh locations, relaunch from zero);
after a number it stands; measured once; nothing re-rolled; a reader at its
ceiling is the record. The loop runs detached, bounded at three hours, each
refocus at 900 s. **Disk**: each whole-suite invocation keeps its spool
directory under `<store>/spool/` (the driver's own behaviour, ~400 MB on the
lens) — 33 invocations is on the order of 13 GB, on a disk with 87 GB free;
the spools are kept until §3 is written and freed after, and the record
names the bytes. **Wall**: the lens's call-tier suite is ~24 s plus a
conversion measured at 16–45 s (rung 1), so ~45 minutes for the loop.

## 6. Docs, versions, seams, the two folds

- **Versions**: Python **0.14.0** (`pyproject.toml`, the driver's
  `driver_version` with it); `sensorium-ts` **0.4.0** unchanged; crates
  unchanged; `TRACE_FORMAT` 4.
- **`docs/trace-format/TYPESCRIPT-KEYS.md`**: rows for `harness_cwd` and
  `refocus_of`; **`v41-typescript-refocus-link.json`**: a TypeScript trace
  carrying both keys and the stamps, asserting what `info` and `runs` print
  (the v28 pattern, `docs/trace-format/VECTORS.md`'s entry).
- **`docs/query.md`**: `### `refocus` on a TypeScript trace — the recorded
  invocation, run again` after the Rust section — the seven refusals, the
  announced command, the pair, the two environment sets, the exit clause.
- **`README.md` (799)**: the TypeScript section's clause `refocus refuses at exit 2`
  clause becomes the sentence that it answers, with the pair rule in one
  phrase; **net-zero**, trimming the same section.
- **`typescript/README.md`**: the `refocus` row of "What refuses" becomes
  the pre-0.14.0 refusal only; "Not yet" loses refocus; a short `### refocus`
  under "Ask" names the pair rule and the sibling count.
- **`typescript/HONESTY.md` (794)**: §12 *Refocus* — the section after §11
  *Under a focus* — is written in a new file,
  **`typescript/HONESTY-REFOCUS.md`**, on `rust/HONESTY-REFOCUS.md`'s
  precedent — what a MATCH on a TypeScript pair may mean, the pair rule, the
  two sets, the three unverifiable checks, the *falsified by* lines naming
  E15 and the three cases; `HONESTY.md` takes a two-line pointer and gives
  two lines back.
- **`typescript/HONESTY-BLIND-SPOTS.md`**: entries **40–43** — the siblings
  are not compared; harness set 1 is not compared; a reused worker cannot be
  refocused; the whole suite is the unit of cost.
- **`vocab.py`**: §3.4 and §3.5.
- **The `_MORE` fold** (S2): `js_inspect._MORE` removed with its comment;
  no consumer exists (`tests/` and `src/` grep clean today); the
  CARRIED-DEBT item struck where it stands.
- **`docs/CARRIED-DEBT.md`**: a §2026-09-13 section — the two drops (S1),
  with the date and the branch kept; the `_MORE` strike; the retired
  vocabulary lines; what E15 found; this slice's own minors. The file is at
  489 and takes it.
- **`CHANGELOG.md`**: the 0.14.0 entry (the file is at 591).
- **The skill** `~/.claude/skills/debugging-typescript-with-sensorium` —
  outside this repository, the arrangement the other two have — gains the
  `refocus` step in the words `docs/query.md` uses.
- **Seams**: `refocus_typescript.py`, `test_refocus_typescript.py`,
  `test_ts_ingest_refocus.py`, `HONESTY-REFOCUS.md` (TypeScript) are new
  files by R12; `refocus_world.py` (625) takes the two moved helpers and the
  shared env helper and stays under the gate — the plan measures it at the
  task that moves them and opens `refocus_licence.py` if it does not.

## 7. Not in this slice

- **Refocus by invocation id** — every pair compared, a roll-up verdict and
  an exit for a mixed result: a different report shape, its own brainstorm,
  and the natural next step once this slice's pair rule has been measured.
- **A narrowing spelling** (`--only-this-file`): rejected by R1 for this
  slice; if a later slice wants it, it is a command the reader typed and
  must be announced as one.
- `--window`; the browser runtime (S5 rung 5, its own brainstorm); a
  transform cache; the C pile (dropped, S1); the deferred-by-ruling list of
  `docs/CARRIED-DEBT.md` §2026-09-12 except S2.

## 8. Risks named

- **The whole suite per refocus.** ~1 minute and ~400 MB of spool on the
  lens, per question. That is the honest cost of R1 and H9 reports it; the
  narrowing spelling is §7's, not a quiet default.
- **A file whose worker the pool retried**, or a vitest configuration that
  runs one file in two containers, would produce two candidates for one key:
  REFUSED by count, never a guess. No lens run has shown the shape.
- **`harness_cwd` on every trace of the lens store predates this slice**, so
  no trace recorded before 0.14.0 can be refocused: refusal 4 says so by
  version. E15 records its own originals.
- **Harness set 1 is a list**, and a list is only as honest as its last
  review: it holds two names, both the pool's slot bookkeeping, and the
  version number is in the printed line so the day a member is found to bear
  on a program it can leave with a date.
- **The threads marker changes a shared function.** Keyed on the
  capability, so a Rust pair (declares `true`) and a Python pair (declares
  everything) print byte for byte what they print today; the two existing
  licence test files hold that.

## 9. Dated amendments

None yet.
