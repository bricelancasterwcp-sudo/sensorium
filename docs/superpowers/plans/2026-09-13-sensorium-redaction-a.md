# Secrets redaction, PR A — rule v1, the store key, env redaction, file modes, `info`/`refocus`, E16 part A: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every recorder stores a secret-named environment variable as `<redacted>` plus a keyed digest instead of its value, every file the recorders create is 0600 (directories 0700), the trace says what was withheld under which rule, `info` prints it and `refocus` still compares it — measured once as E16 part A.

**Architecture:** One pure rule module per language (`src/sensorium/redact.py`, `rust/sensorium-rt/src/redact.rs`, `typescript/src/redact.mjs`) holds the segment name rule, the knobs and the HMAC digest, all three pinned to one fixture. Each recorder redacts the environment at its single env-write site and writes the `redaction` meta beside it; the two converters pass it through and apply the same rule to a header from an older runtime. The query side reads the digest tables in `_env_diff` and prints the rule on `info`. The content rule, captured values and the retrofit are PR B and PR C, each with its own plan written from the same spec when this one merges.

**Tech Stack:** Python 3.13 (`src/sensorium/`), pytest; Rust 1.96 (`rust/`, `sensorium-rt` dependency-free, `cargo-sensorium`); Node ≥ 24 ESM `.mjs` under `typescript/`, `node --test`; the vector runner (`tests/test_vectors.py`); the acceptance-instrument pattern of `typescript/acceptance/e15.sh` + `tests/test_acceptance_e15_*.py`.

**Spec:** `docs/superpowers/specs/2026-09-13-sensorium-secrets-redaction-design.md` (branch `docs/secrets-redaction-design`, e29bfeb). The spec is the authority; this plan is its argument for PR A. Section numbers below (§n) are the spec's unless prefixed by a file name.

## Global Constraints

- **Base and branch.** `feat/redaction-a` off `docs/secrets-redaction-design` at the commit that carries this plan. Worktree `/mnt/extra/sensorium-rung2/redaction-a`; venv `.venv` (`uv venv -p 3.13 && uv pip install -p .venv/bin/python -e '.[dev]'`); `npm ci` in `typescript/`, `typescript/probes/`, `corpus/typescript/`; `CARGO_TARGET_DIR=/mnt/extra/sensorium-rung2/rust-target`. Ledger `.superpowers/sdd/2026-09-13-sensorium-redaction-a/`. Check `df -h /mnt/extra` first; below 20 GB free, stop and say so.
- **Plans state invariants and falsifiers; code is verbatim only where a fresh implementer would guess wrong** (the wire, the HMAC, the header JSON, the exact sentences). Every task's tests ARE in this plan; the implementation is described by interface and invariant. Implementers transcribe bugs faithfully — that is why.
- **No box path in a committed file** except the E16 record's pin table. `grep -rn "/mnt/\|/home/"` over the diff before every commit.
- **Pre-registration is committed alone and before any code** (Task 0) and byte-locked by `tests/test_acceptance_e16_lock.py`.
- **Legacy output is byte-identical where nothing was redacted:** every existing vector, every Python/Rust/TypeScript corpus case, `tests/test_refocus*.py` unchanged in outcome. A trace with no `redaction` key prints exactly what 0.14.0 printed, plus one `redaction: none …` line on `info` (§4.3, §6.1) — that line is the only permitted diff on old traces, and vector v42 pins it.
- **`TRACE_FORMAT` stays 4. The Rust spool wire stays v3 in PR A** (v4 is PR B's, with tag 3); the proc header JSON gains two siblings, which is additive.
- **Versions** (§10): Python **0.15.0**, `sensorium-ts` **0.5.0**, `sensorium-rt` **0.6.0**, `cargo-sensorium` **0.7.0**; transform untouched. Numbers land in Task 7 with the CHANGELOG's dated header in the same commit (`tests/test_release_tokens.py`'s dated form: `## 0.15.0 — YYYY-MM-DD`, the date of that commit). Recorded fixture facts (`tests/helpers.py:186`'s `sensorium-rt 0.4.0`, `tests/fixtures/ts-spools/*` versions) stay; pins that describe THIS converter's output move — find them by `grep -rn "sensorium-ts 0.4.0\|sensorium-rt 0.5.0\|cargo-sensorium 0.6.0" tests typescript/test rust` and judge each by its own docstring.
- **Ceilings** (`tests/test_ceiling.py`, 800): `record/boot.py` 768 — the env write shrinks to one call, so it stays under; `refocus_world.py` 710 — the redaction comparison goes in `refocus_env.py` (§10), `refocus_world.py` gains at most 25 lines; `rt.mjs` 798 — every new line goes in `redact.mjs`, `rt.mjs` may only SHRINK (the BOOT's env lines move out); `spool.rs` 752 — `redact_env` lives in `redact.rs`; `README.md` 796 — net-zero or shrink.
- **Tests:** TDD per task; every new predicate mutation-checked (break the line the test pins, the test must FAIL, restore) under `PYTHONDONTWRITEBYTECODE=1` with `__pycache__` purged before each run. Mutation results go in the task report as `mutant → test that failed`. Rust and JavaScript predicates are mutation-checked the same way by hand (edit, `cargo test -p sensorium-rt` / `npm --prefix typescript test`, restore).
- **Commits:** conventional prefixes; the session's trailer lines. By-path `git add`, never `-A`; `git show --stat` after every commit.
- **Gotchas carried:** `pkill -f`/`pgrep -f` self-match; helper scripts scrub `SENSORIUM_MANIFEST_DIR`, `SENSORIUM_SPOOL`, `SENSORIUM_FOCUS`, `SENSORIUM_INVOCATION` AND NOW `SENSORIUM_REDACT_KEY`, `SENSORIUM_NO_REDACT`, `SENSORIUM_REDACT_NAMES`, `SENSORIUM_REDACT_ALLOW`; `sensorium --version` is not a flag; a plan's line numbers move — locate by the quoted text; **the E7 needle** `sensorium run --focus` must not appear in any TypeScript sentence added here.

---

## File structure

| file | responsibility |
|---|---|
| `src/sensorium/redact.py` (new, Task 1) | `RULE`, `SEGMENTS`, `REDACTED`, `KEY_VAR`, `split`, `normalise`, `Knobs`, `fires`, `Key`, `env`, `meta`, `uncomparable` |
| `docs/trace-format/redaction-v1.json` (new, Task 1) | the shared fixture: `split`, `names`, `knobs` cases (PR B appends `content`) |
| `tests/test_redact.py` (new, Task 1) | the fixture-driven Python tests + the key + the census over `tests/fixtures/benign-env-names.txt` |
| `tests/fixtures/benign-env-names.txt` (new, Task 1) | ~200 real environment names, the census input, with the firing subset pre-listed at its top |
| `src/sensorium/record/boot.py` | `_write_run_meta` calls `redact.env`; `redaction` meta; key loaded before the program runs |
| `src/sensorium/store/db.py`, `src/sensorium/paths.py`, `src/sensorium/invocations.py`, `src/sensorium/ts/ingest.py` | 0600 / 0700 at creation |
| `tests/test_record_redaction.py` (new, Task 2) | env redaction end to end via `record_script`; the knobs; the modes |
| `rust/sensorium-rt/src/redact.rs` (new, Task 3), `spool.rs`, `lib.rs` | the rule, HMAC, `Key`, `redact_env`; header siblings; knob reads; modes |
| `rust/cargo-sensorium/src/redaction_key.rs` (new, Task 4), `launch.rs`, `runner.rs`, `convert/{mod,meta,sqlite}.rs`, `convert/spool/mod.rs` | key create-or-load; `SENSORIUM_REDACT_KEY`; `redaction` meta; older-header pass; modes |
| `typescript/src/redact.mjs` (new, Task 5), `rt.mjs`, `typescript/test/redact.test.mjs` (new) | the rule, HMAC, BOOT siblings, modes |
| `src/sensorium/ts/driver.py`, `build.py`, `tests/test_ts_ingest_redaction.py` (new) | key var; `redaction` meta; older-BOOT pass |
| `src/sensorium/query/info_cmd.py`, `refocus_env.py`, `refocus_world.py`, `refocus_licence.py`, `refocus_rust.py`, `refocus_typescript.py` | the two `info` lines; `RedactionPair`; the sixth list; `UNVERIFIABLE_ENV`; `is_recorder_key` |
| `tests/test_info_redaction.py`, `tests/test_refocus_redaction.py` (new, Task 6) | the lines and the three outcomes on meta-built pairs |
| `docs/trace-format/vectors/v42-redaction-render.json`, `v43-refocus-redacted-env.json`, `docs/trace-format/VECTORS.md` | the contract pins |
| `docs/TRACE-FORMAT.md`, `docs/trace-format/TYPESCRIPT-KEYS.md`, `rust/README.md`, `docs/redaction.md` (new), `README.md`, `CHANGELOG.md`, `docs/CARRIED-DEBT.md`, the spec's §13 | prose |
| `tests/acceptance_e16/e16a.sh`, `e16a.py`, `assemble_e16a.py` (new, Task 8), `tests/test_acceptance_e16_lock.py` (Task 0), `tests/test_acceptance_e16_cells.py` (Task 8) | the instrument and its tests |
| `docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md` | the record: §1 locked at Task 0, §2 part A appended at Task 8 |

## Decisions this plan makes (each amends the spec non-silently; Task 9 appends them to §13)

| # | decision | why |
|---|---|---|
| A1 | **E16 is measured in three parts, one per PR, each once**, on the cells that PR delivers (A: H1-env, H2, H3, H6-env; B: H1-values, H5, H6-values; C: H4). One record file, three dated sections, each byte-locked when written. §9's "after PR C" is amended. | a leak closed in PR A that is not verified until PR C lands is a leak nobody checked for weeks |
| A2 | **`_env_diff(was, now, redaction=None)`** keeps its positional pair and gains a keyword `RedactionPair \| None`; it returns a **six**-tuple, `uncomparable` last, `[]` when `redaction` is None. `_env_state(meta, env, now_meta=None)` builds the pair from `meta["redaction"]`, `now_meta["redaction"]` (None → the live plaintext side) and `Key.load(paths.trace_root())`. The five existing unpack sites (`refocus_world.py:385`, `tests/test_refocus_env.py:261,525`, `tests/test_refocus_world_threads.py:223`) take the sixth name. | one comparison function; the Python re-run's side IS plaintext (`refocus_cmd.py:608`), so the pair has to admit a side with no table |
| A3 | **The unverifiable marker is fixed text**, `UNVERIFIABLE_ENV = "env: unverifiable in part (redacted variables not comparable)"`, short form `env (redacted, not comparable)`, added to `UNVERIFIABLE`, `_SHORT_UNVERIFIABLE` and `unverifiable_checks(orig, new)` — which computes it from the two metas through `redact.uncomparable`. The NAMES ride the env line (`; 2 redacted variable(s) not comparable (different keys): A, B`) and the fact. | `relicense` filters caveats by exact string; names in the marker would defeat the filter |
| A4 | **The Rust converter takes the key as a parameter**: `convert_dir(spool_dir, key: &Key)`; the driver passes the one it created; `cargo sensorium convert` (standalone) builds it with `Key::load(&store_root()?)` and never creates. | conversion of an older header needs digests; a converter that minted keys would mint one per invocation on a read-only store |
| A5 | **Key creation lives in the drivers and the Python recorder, never in a runtime.** `cargo-sensorium/src/redaction_key.rs` reads 32 bytes from `/dev/urandom` (std only); the runtime only parses hex from `SENSORIUM_REDACT_KEY`. | §3; the rt is dependency-free and runs inside the user's binary |
| A6 | **The census input is a committed list of environment names**, `tests/fixtures/benign-env-names.txt`, harvested from this box's shell (`env \| cut -d= -f1 \| sort`) plus 40 common CI names, with the EXPECTED firing subset listed at its top under `# fires:`; the test asserts the rule fires on exactly that subset. The corpus runner's own environment is not a census input in PR A. | on CI the launching shell carries `GITHUB_TOKEN`, and the rule firing on it is correct, not a false positive; §8's census wants a controlled input |
| A7 | **`info`'s `env:` field, exactly:** `env:<hash>` when the trace has no `redaction` key or `mode` is `off`; `env:<hash> (<N> vars, <k> redacted: A, B, +M more)` when on, `_capped` semantics (8 names then `+M more`); `(<N> vars, 0 redacted)` when on and nothing fired. | §6.1 gave the shape; the zero case must read as a measured zero |
| A8 | **The `redaction:` line goes directly after `caps:`**, four forms verbatim (§6.1); `values redacted: N` appended only when the key is present (PR B on). | the line sits with the recording's other declared parameters |
| A9 | **Versions and the changelog land in Task 7, one commit**, `## 0.15.0 — <date>` dated. | `test_release_tokens`: a minor bump and its header travel together |
| A10 | **E16 part A records existing programs, no new probes:** `corpus/aliasing/main.py` under `sensorium run`, `corpus/rust/aliasing` under `cargo sensorium test`, `corpus/typescript/aliasing` under `sensorium ts run -- npx vitest run`, each with `SENSORIUM_E16_TOKEN` exported (`sk-e16-`+33). Value probes are PR B's. | PR A redacts the environment only; a probe that plants values would measure PR B's rule against PR A's code |
| A11 | **The fixture's schema is fixed now:** `{"split": [{"name", "segments"}], "names": [{"name", "knobs"?: {"names": [], "allow": []}, "fires": bool}], "content": []}`; PR B fills `content`. | three suites read one file; the shape cannot move under them |

## Pre-registration (Task 0 commits spec §9 verbatim as the record's §1, plus this block)

- **Part A's cells** are H1 restricted to the environment (the token is in no file under the store, the Python spool dir, the TypeScript spool dir, and in no Rust proc header; the Rust `.spool` files carry no environment at all), H2 in full, H3 in full, H6 restricted to `redaction.env` (exactly one name per trace: `SENSORIUM_E16_TOKEN`). H1-values, H5 are part B; H4 is part C. Both readings per §9's table stand.
- **The token** is `sk-e16-` + 33 characters from `[A-Za-z0-9]`, minted by `e16a.sh` into `$E16_DIR/token` at 0600, exported as `SENSORIUM_E16_TOKEN`, never printed by the instrument and never committed; the record cites its sha256 prefix only.
- **Locations** are the record's §2 pin table only: `E16_DIR=/mnt/extra/sensorium-rung2/e16`, store `$E16_DIR/store-a`, spools under it, transcripts `$E16_DIR/a-transcripts/`.
- **Versions expected:** `driver_version`/`recorder` read `sensorium 0.15.0`, `sensorium-rt 0.6.0`, `cargo-sensorium 0.7.0`, `sensorium-ts 0.5.0`; §2 records what they were.
- **H3's pair:** Python — `refocus <run> --focus main` on the aliasing recording; Rust — `refocus <run> --focus compute` (the case's focused fn; read `corpus/rust/aliasing/questions.yaml` for the name). First with the token unchanged (predict: licence held, `SENSORIUM_E16_TOKEN` counted among compared), then re-exported to a fresh value (predict: WITHHELD, the name in the changed list). TypeScript's refocus is exercised by v43 and `tests/test_refocus_redaction.py`, not live, because the TS pair's env clause runs the same code path — stated as a reading, not a gate.
- **Kill rules:** each recording 600 s, each refocus 900 s, the part 45 min; a kill is an infrastructure event, rerun from zero with a fresh token.

---

### Task 0: The record's §1 and the lock

**Files:** Create `docs/superpowers/acceptance/2026-09-13-sensorium-e16-redaction.md`, `tests/test_acceptance_e16_lock.py`.

- [ ] **Step 1: Write the record's §1.** Heading `# E16 — secrets redaction, measured` ; `## 1. Pre-registration (locked)` containing (a) the spec's `## 9. E16, pre-registered` section verbatim, heading carried as `### 9`, and (b) this plan's `## Pre-registration` block verbatim. Then `## 2. Part A` with the single line `Not yet measured.`
- [ ] **Step 2: Write the lock test.** On `tests/test_acceptance_e15_lock.py`'s pattern (read it): the test extracts block (a) from the record and asserts it equals the spec's §9 text read from `git show docs/secrets-redaction-design:docs/superpowers/specs/2026-09-13-sensorium-secrets-redaction-design.md` (fallback: the working-tree spec) sliced between `## 9. E16, pre-registered` and `## 10.`; and block (b) equals the plan's block sliced between `## Pre-registration` and the `---` that follows it. A second test pins that §2 begins with `Not yet measured.` OR with a `### measured` heading — never anything else.
- [ ] **Step 3: Run** `pytest tests/test_acceptance_e16_lock.py -q` → PASS. Mutate one character of block (a) in the record → FAIL → restore.
- [ ] **Step 4: Commit** `test(acceptance): E16 pre-registration locked` — by path, these two files only; `git show --stat` must list nothing under `src/`, `rust/`, `typescript/`.

### Task 1: The rule module, the fixture, the key

**Files:** Create `src/sensorium/redact.py`, `docs/trace-format/redaction-v1.json`, `tests/test_redact.py`, `tests/fixtures/benign-env-names.txt`.

**Interfaces (produces):**
```python
RULE = "v1"; REDACTED = "<redacted>"; KEY_VAR = "SENSORIUM_REDACT_KEY"
SEGMENTS: frozenset[str]          # §2.1's set, exactly
def split(name: str) -> list[str]  # uppercased segments (§2.1's two splits)
def normalise(name: str) -> str    # "".join(split(name)) — the NAMES/ALLOW comparison form
@dataclass(frozen=True)
class Knobs: off: bool; names: frozenset[str]; allow: frozenset[str]   # normalised
    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> "Knobs"
    def meta(self) -> dict          # {"names": sorted(...), "allow": sorted(...)}
def fires(name: str, knobs: Knobs) -> bool   # allow → False; names → True; any segment in SEGMENTS → True
class Key:
    path: Path; material: bytes | None
    @classmethod
    def load(cls, root: Path) -> "Key"            # never creates, never raises
    @classmethod
    def load_or_create(cls, root: Path) -> "Key"  # O_CREAT|O_EXCL 0o600, 32 bytes os.urandom; never raises
    @classmethod
    def from_hex(cls, text: str | None) -> "Key"
    keyed: bool; key_id: str | None               # sha256(material)[:8]
    def digest(self, text: str) -> str | None     # hmac-sha256(material, text.encode()).hexdigest()[:16]
    def mode_note(self) -> str | None             # "key mode 0644 -- expected 0600" or None
def env(environ: Mapping[str, str], key: Key, knobs: Knobs) -> tuple[dict[str, str], dict[str, str | None]]
def meta(key: Key, knobs: Knobs, table: dict[str, str | None], by: str = "recorder") -> dict
def uncomparable(was_meta: dict, now_meta: dict | None, key: Key) -> tuple[list[str], str | None]
```
Invariants: `env()` deletes `KEY_VAR` from the result, never redacts it, never lists it in the table; with `knobs.off` it returns `(dict(environ) minus KEY_VAR, {})`. `meta()` returns `{"rule": "v1", "mode": "off"}` when off, else `{"rule", "mode": "on", "keyed", "key_id", "env": table, "names", "allow", "by"}`. `uncomparable` returns the names on either side's `redaction.env` whose comparison §6.2's table calls unverifiable, and the reason word (`"unkeyed"` or `"different keys"`).

- [ ] **Step 1: Author the fixture** with the schema of A11. `split`: at least `apiKey→[API,KEY]`, `HTTPToken→[HTTP,TOKEN]`, `SSH_AUTH_SOCK→[SSH,AUTH,SOCK]`, `XAUTHORITY→[XAUTHORITY]`, `db.password→[DB,PASSWORD]`, `x→[X]`, `__init__→[INIT]`. `names`: every segment of §2.1 firing once (`API_KEY`, `accessToken`, `secret`, `DATABASE_DSN`, `passphrase`, `jwt`, `cookie_jar`, `private_key_path`, `bearer`, `SIGNATURE_V4`, `creds`, `authorization`, `oauth_token`, `MY_PASS`); the near-misses NOT firing (`KEYBOARD`, `KEYRING`, `authorId`, `OAUTH_URL`, `XAUTHORITY`, `PWD`, `OLDPWD`, `SESSION_MANAGER`, `PATH`, `MONKEY_PATCH`, `BYPASS_CACHE`, `PASSENGER_COUNT`); the knobs (`SENSORIUM_NO_REDACT`, `SENSORIUM_REDACT_NAMES`, `SENSORIUM_REDACT_ALLOW` not firing; `MYCO_DSN` firing anyway; `myco_thing` firing only with `knobs.names: ["MYCO_THING"]`; `API_KEY` NOT firing with `knobs.allow: ["api_key"]`; `<redacted>` not firing). `content: []`.
- [ ] **Step 2: Write `tests/test_redact.py`** — parametrised over the fixture: `test_split`, `test_fires`; then `test_env_replaces_value_and_tables_digest` (`{"API_KEY": "abc", "HOME": "/h", KEY_VAR: "00"*32}` under a key built from 32 `\x01` bytes → env `{"API_KEY": "<redacted>", "HOME": "/h"}`, table `{"API_KEY": <hmac of "abc">}`, and the digest equals `hmac.new(b"\x01"*32, b"abc", "sha256").hexdigest()[:16]` computed in the test); `test_env_off_keeps_plaintext_but_drops_key_var`; `test_key_load_or_create_is_0600_and_idempotent` (tmp root; `stat` mode `0o600`; second call returns identical material; `load` on an empty dir → `keyed False`, `key_id None`, `digest → None`); `test_key_id_is_sha256_prefix`; `test_meta_off_and_on_shapes`; `test_uncomparable_three_rows` (same key → `[]`; different key ids → names, `"different keys"`; `keyed False` side → `"unkeyed"`); `test_census_fires_on_exactly_the_listed_subset` (reads `benign-env-names.txt`, asserts `{n for n in names if fires(n, Knobs(False, frozenset(), frozenset()))} == expected_from_header`).
- [ ] **Step 3: Harvest the census file**: `env | cut -d= -f1 | sort -u` on this box plus `CI GITHUB_ACTIONS GITHUB_TOKEN GITHUB_SHA RUNNER_OS CARGO_HOME RUSTUP_HOME NODE_OPTIONS npm_config_cache VIRTUAL_ENV PYTHONPATH LANG LC_ALL TERM COLORTERM DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS SSH_AGENT_PID GPG_TTY EDITOR PAGER LESS MANPATH` and 15 more of your choosing; then compute the firing subset BY HAND from §2.1 (expect `CLAUDE_CODE_MESSAGING_TOKEN`, `SSH_AUTH_SOCK`, `GITHUB_TOKEN`, and whatever else the box's names contain) and write it under `# fires:` at the top — the test is the check of your hand.
- [ ] **Step 4: Run** → every test FAILS on import. **Step 5: Implement `redact.py`** to the interfaces above. The camelCase split, verbatim, because two implementers will spell it differently: `re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", name))`, then `re.split(r"[^A-Za-z0-9]+", …)`, drop empties, uppercase. **Step 6: Run** → PASS. Mutations: remove `PASS` from `SEGMENTS` → `MY_PASS` case fails; drop the `allow` check → `API_KEY`/allow case fails; hash with `sha256` instead of HMAC → `test_env_replaces…` fails; `0o644` in `load_or_create` → the mode test fails.
- [ ] **Step 7: Commit** `feat(redact): rule v1's name rule, the knobs, the store key — one fixture` (module, fixture, both test files).

### Task 2: The Python recorder redacts its environment; files are 0600

**Files:** Modify `src/sensorium/record/boot.py` (`_write_run_meta`, `run_target`), `src/sensorium/store/db.py:114-127`, `src/sensorium/paths.py:31-34`, `src/sensorium/invocations.py:60-64`, `src/sensorium/ts/ingest.py:168`. Create `tests/test_record_redaction.py`.

**Interfaces:** `_write_run_meta(w, run_id, argv, focus, include, exclude, window, refocus_of, *, key: redact.Key, knobs: redact.Knobs)`; `run_target` builds `key = redact.Key.load_or_create(paths.trace_root())` and `knobs = redact.Knobs.from_environ(os.environ)` BEFORE `resolve_target`.

- [ ] **Step 1: Tests** (each records via `tests.helpers.record_script` with `env_extra`; read `run_cli`'s signature — `record_script` may need an `env_extra` passthrough, add it if absent, defaulting to None):
  - `test_secret_named_variable_is_stored_redacted_with_digest`: `env_extra={"MY_API_KEY": "abc123", "PLAIN": "x"}` → meta `env["MY_API_KEY"] == "<redacted>"`, `env["PLAIN"] == "x"`, `redaction["env"]["MY_API_KEY"]` is 16 hex and equals `Key.load(sdir).digest("abc123")`, `redaction["mode"] == "on"`, `redaction["by"] == "recorder"`, `redaction["keyed"] is True`, `redaction["key_id"] == Key.load(sdir).key_id`.
  - `test_env_hash_is_over_the_stored_env`: `meta["env_hash"] == sha256(json.dumps(meta["env"], sort_keys=True).encode()).hexdigest()[:16]`.
  - `test_no_redact_knob_stores_plaintext_and_says_so`: `env_extra={"SENSORIUM_NO_REDACT": "1", "MY_API_KEY": "abc123"}` → `env["MY_API_KEY"] == "abc123"`, `redaction == {"rule": "v1", "mode": "off"}`; and with `"0"` → redacted.
  - `test_names_and_allow_knobs`: `SENSORIUM_REDACT_NAMES=MYCO_THING`, `SENSORIUM_REDACT_ALLOW=my_api_key` → `MYCO_THING` redacted, `MY_API_KEY` plaintext, `redaction["names"] == ["MYCOTHING"]`, `redaction["allow"] == ["MYAPIKEY"]`.
  - `test_key_var_is_dropped_not_recorded`: `env_extra={KEY_VAR: "00"*32}` → `KEY_VAR not in env`, not in the table.
  - `test_created_files_are_0600_and_dirs_0700`: after one recording, `stat` of `sdir/traces/<run>.db`, `sdir/redaction.key`, `sdir/invocations.jsonl` is `0o600`; `sdir/traces` and `sdir` are `0o700`; a `-wal`/`-shm` sidecar, if present, is `0o600`.
  - `test_unreadable_key_records_unkeyed` (`monkeypatch` `Key.load_or_create` to return `Key(path, None)` — or `chmod 000` the key file before recording under a non-root user) → `redaction["keyed"] is False`, every table value `None`, values still `<redacted>`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** `db.create_trace`: `os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))` before `sqlite3.connect` (a `FileExistsError` here is `run_target`'s already-refused case; let it raise). `paths.traces_dir`: `d.mkdir(parents=True, exist_ok=True, mode=0o700)` — and `trace_root()` itself when it is created by that call: pass `mode=0o700` (Python applies it to every level it creates). `invocations.record`: create with `os.open(..., 0o600)` when absent, then append. `ingest.py:168`: `0o600`. `_write_run_meta`: `env, table = redact.env(os.environ, key, knobs)`; `w.set_meta("env", env)`; `env_hash` over `env`; `w.set_meta("redaction", redact.meta(key, knobs, table))`.
- [ ] **Step 4: Run** the new file, then `pytest -q` whole → all PASS (existing tests that read `meta["env"]` for a plaintext value they planted: fix each by planting a non-firing name, and say so in the report). Mutations: `0o644` in `create_trace` → mode test fails; skip `KEY_VAR` deletion → key-var test fails; hash the plaintext env → `env_hash` test fails.
- [ ] **Step 5: Commit** `feat(record): the Python recorder redacts its environment; traces, key and store are 0600/0700`.

### Task 3: The Rust runtime redacts its environment; spools and headers are 0600

**Files:** Create `rust/sensorium-rt/src/redact.rs`; modify `rust/sensorium-rt/src/spool.rs` (`write_proc_header`, `sorted_env`, `Spool::open` at `:158`, the header tmp at `:497`, `RT_VERSION`), `lib.rs` (`ensure_dir` at `:232`, `mod redact;`), `rust/sensorium-rt/Cargo.toml` (0.6.0).

**Interfaces (produces):**
```rust
pub const RULE: &str = "v1"; pub const REDACTED: &str = "<redacted>"; pub const KEY_VAR: &str = "SENSORIUM_REDACT_KEY";
pub fn split(name: &str) -> Vec<String>;
pub struct Knobs { pub off: bool, pub names: Vec<String>, pub allow: Vec<String> }  // normalised, sorted
impl Knobs { pub fn from_env() -> Knobs; }
pub fn fires(name: &str, knobs: &Knobs) -> bool;
pub struct Key(Option<[u8; 32]>);
impl Key { pub fn from_hex(s: Option<&str>) -> Key; pub fn from_env() -> Key; pub fn keyed(&self) -> bool;
           pub fn key_id(&self) -> Option<String>; pub fn digest(&self, text: &str) -> Option<String>; }
pub fn hmac_sha256(key: &[u8], msg: &[u8]) -> [u8; 32];
pub type Table = Vec<(String, Option<String>)>;
pub fn redact_env(env: Vec<(String, String)>, key: &Key, knobs: &Knobs) -> (Vec<(String, String)>, Table);
pub fn redaction_json(key: &Key, knobs: &Knobs) -> String;   // {"rule":"v1","mode":..,"keyed":..,"key_id":..,"names":[..],"allow":[..]}
```
HMAC, verbatim (RFC 2104 over the crate's `sha256::Sha256`): block 64; key ≤ 64 bytes is zero-padded to 64; `inner = Sha256(k ⊕ 0x36 ‖ msg)`; `out = Sha256(k ⊕ 0x5c ‖ inner)`. The header gains, after `"env_hash"`: `,"env_redaction":{<name>:<"16hex"|null>,…},"redaction":<redaction_json>`; `env_hash` is computed over the REDACTED env with the existing formula.

- [ ] **Step 1: Tests** in `rust/sensorium-rt/tests/redact.rs` — an integration test, so it may read the fixture with `serde_json` under `[dev-dependencies]` (add `serde_json = "1"` there; a dev-dependency never reaches the rlib the driver compiles with its bare `rustc` line, so D1's zero-dependency promise holds). The fixture path is `concat!(env!("CARGO_MANIFEST_DIR"), "/../../docs/trace-format/redaction-v1.json")`. Cases: `split` and `fires` over the fixture; `hmac_sha256` against RFC 4231 test case 2 (`key = "Jefe"`, `msg = "what do ya want for nothing?"`, expect `5bdcc146bf60754e6a042426089575c75a003f089d2739839dec58b964ec3843`); `redact_env` replaces and tables; `KEY_VAR` dropped; `off` keeps plaintext; `key_id` = sha256 prefix.
  Runtime tests in `rust/sensorium-rt/tests/units.rs`'s style (read `tests/common/mod.rs` for the child helper): a child run with `SENSORIUM_REDACT_KEY=<64 hex>` and `MY_API_KEY=abc` in its env → the proc header's `env` has `"MY_API_KEY":"<redacted>"`, no `SENSORIUM_REDACT_KEY` key, `env_redaction.MY_API_KEY` equals the HMAC computed in the test, `redaction.keyed == true`; the spool file and the header are mode `0o600`, the spool dir `0o700` (`std::os::unix::fs::PermissionsExt`). Note `tests/common`'s child helper already scrubs `SENSORIUM_FOCUS`; it must scrub the four new variables too (Global Constraints).
- [ ] **Step 2: Run** `cargo test -p sensorium-rt` → FAIL. **Step 3: Implement.** `Spool::open`: `.mode(0o600)` on the `OpenOptions` (behind `#[cfg(unix)] use std::os::unix::fs::OpenOptionsExt`); header tmp: `OpenOptions::new().write(true).create(true).truncate(true).mode(0o600).open(&tmp)`; `ensure_dir`: `std::fs::DirBuilder::new().recursive(true).mode(0o700).create(dir)` (unix; plain `create_dir_all` elsewhere). `write_proc_header` reads `Knobs::from_env()` and `Key::from_env()` ONCE (a `OnceLock`), calls `redact_env(sorted_env(), …)`, writes the two siblings. `RT_VERSION = "sensorium-rt 0.6.0"`.
- [ ] **Step 4: Run** `cargo test -p sensorium-rt`, `cargo test -p sensorium-rt --features test-hooks`, `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings` → green. Mutations: swap `0x36`/`0x5c` → RFC case fails; `0o644` → mode test fails.
- [ ] **Step 5: Commit** `feat(rt): the runtime redacts its environment under rule v1; spools, headers and the dir are 0600/0700; 0.6.0`.

### Task 4: The Rust driver mints the key; the converter passes the redaction through

**Files:** Create `rust/cargo-sensorium/src/redaction_key.rs`; modify `launch.rs:60-80`, `runner.rs:124-135`, `convert/mod.rs` (`convert_dir`, `run`), `convert/spool/mod.rs` (`ProcHeader`), `convert/meta.rs` (`MetaInput`, `build`), `convert/sqlite.rs:92-99`, `driver.rs` (where `convert_dir` is called), `Cargo.toml` (0.7.0).

**Interfaces:** `redaction_key::load_or_create(root: &Path) -> sensorium_rt::redact::Key` (never fails: unreadable → `Key(None)`, and the driver prints one WARN line `sensorium: no redaction key at <path> (<error>); digests will be absent` to stderr); `redaction_key::to_hex(&Key) -> Option<String>`. `ProcHeader` gains `#[serde(default)] pub env_redaction: BTreeMap<String, Option<String>>` and `#[serde(default)] pub redaction: Option<serde_json::Value>`. `MetaInput` gains `pub redaction: serde_json::Value`; `build` emits `("redaction", m.redaction.clone())` right after `("env", …)`. `convert_dir(spool_dir: &Path, key: &Key)`.

Invariants: a header WITH `redaction` → meta `redaction` = header's object + `"env": env_redaction` + `"by": "recorder"`. A header WITHOUT (an rt ≤ 0.5.0) → the converter runs `sensorium_rt::redact::redact_env(header env, key, Knobs::default())`, writes the redacted env, recomputes `env_hash` with the Rust formula, meta `redaction` with `"by": "converter"`. `TraceWriter::create` pre-creates `tmp_path` at 0600 (`OpenOptions … .mode(0o600).create_new(true)`) before `Connection::open`. `runner::write_record`'s tmp is 0600 and the spool dir `DirBuilder` 0700. `launch.rs` adds `.env(KEY_VAR, hex)` only when keyed (an unkeyed driver sets nothing, and the runtime records unkeyed).

- [ ] **Step 1: Tests.** `convert/spool/tests.rs` pattern (read `header_v` and the JSON header fixtures there): a header JSON with `redaction`/`env_redaction` → passthrough asserted on the built meta; a header without → converter-applied with `by: "converter"` and `env.MY_API_KEY == "<redacted>"`; `env_hash` equals the sorted `k=v` sha256 prefix of the STORED env. `redaction_key` tests in its own `#[cfg(test)]`: creates 0600, idempotent, `load` of an absent file → unkeyed. `tests/test_rust_convert.py`'s fixture mechanism (JSON case → real binary): add `tests/fixtures/rust-spools/redacted-env/` whose proc header carries the two siblings and whose `case.json` asks `info` for `env:` naming `MY_API_KEY` and `redaction: rule v1, keyed` — this case runs only where the binary is built (the file says how it skips).
- [ ] **Step 2: Run** `cargo test -p cargo-sensorium` → FAIL. **Step 3: Implement** to the interfaces. **Step 4: Run** `cargo test --workspace`, fmt, clippy, `bash rust/tests/mechanics.sh` → green; `python -m pytest -q tests/test_rust_convert.py` with the release binary on PATH → green.
- [ ] **Step 5: Commit** `feat(driver): the key is minted per store and handed to the runtime; the converter carries redaction through and applies it to older headers; 0.7.0`.

### Task 5: The TypeScript runtime, driver and ingest

**Files:** Create `typescript/src/redact.mjs`, `typescript/test/redact.test.mjs`, `tests/test_ts_ingest_redaction.py`; modify `typescript/src/rt.mjs` (`boot()` at `:176-208`, the `SPOOL_DIR` mkdir, `flush`'s `appendFileSync`, `VERSION`), `typescript/package.json` (0.5.0), `src/sensorium/ts/driver.py` (`_harness_env`), `src/sensorium/ts/build.py` (`_meta`), `src/sensorium/query/refocus_typescript.py` (`is_recorder_key`), `src/sensorium/query/refocus_rust.py` (`is_recorder_key`).

**Interfaces (`redact.mjs`):** `export const RULE, REDACTED, KEY_VAR; export function split(name); export function normalise(name); export function knobsFromEnv(env) → {off, names, allow}; export function fires(name, knobs); export class Key { static fromHex(hex|undefined); keyed; keyId; digest(text) }; export function redactEnv(env, key, knobs) → {env, table}; export function redactionMeta(key, knobs)`. HMAC via `crypto.createHmac('sha256', material).update(text).digest('hex').slice(0, 16)`; `keyId` = `createHash('sha256')` over the material, 8 hex.

BOOT gains `envRedaction: table` and `redaction: redactionMeta(key, knobs)`; `env` is the redacted one with `KEY_VAR` deleted; `envHash: envHash(env)` over it. `fs.mkdirSync(SPOOL_DIR, {recursive: true, mode: 0o700})`; `fs.appendFileSync(spoolPath, text, {mode: 0o600})`. `driver._harness_env` sets `SENSORIUM_REDACT_KEY` to `Key.load_or_create(paths.trace_root())`'s hex when keyed. `build._meta` adds `"redaction"`: BOOT's `redaction` + `"env": boot.envRedaction` + `"by": "recorder"`; a BOOT without `redaction` (0.4.0 fixtures) → `redact.env(boot.env, Key.load(paths.trace_root()), Knobs(False, ∅, ∅))`, `env_hash` recomputed with the TS formula (sorted `k=v` join), `"by": "converter"`. Both `is_recorder_key`s return True for `KEY_VAR`.

- [ ] **Step 1: Tests.** `redact.test.mjs`: fixture-driven `split`/`fires` (read the JSON with `fs.readFileSync` + `JSON.parse`); HMAC against RFC 4231 case 2; `redactEnv` replaces/tables/drops `KEY_VAR`; `knobsFromEnv` reads the three knobs with the `"0"` rule. In `rt.focus.test.mjs`'s style (it spawns a child with a spool dir — read it), a child with `MY_API_KEY=abc` and a key → BOOT `env.MY_API_KEY === '<redacted>'`, `envRedaction.MY_API_KEY` equals the test's HMAC, no `SENSORIUM_REDACT_KEY` key, spool file mode `0o600`, dir `0o700`. `tests/test_ts_ingest_redaction.py`: ingest the existing fixture spool `tests/fixtures/ts-spools/async-chain` (a 0.4.0 BOOT, no `redaction`) under a tmp store → meta `redaction.by == "converter"`, `redaction.mode == "on"`, any firing name in that fixture's BOOT env (plant one by copying the fixture and editing its BOOT with `copy_tree` from `tests/ts_spools.py`) is `<redacted>`; a BOOT that carries `redaction` passes through with `by == "recorder"`; the ingested trace file is `0o600`. `tests/test_ts_driver_*`: `_harness_env` carries `SENSORIUM_REDACT_KEY` equal to the store key's hex (new file `tests/test_ts_driver_redaction.py`, `tests/test_ts_driver.py` is at 683 and not edited).
- [ ] **Step 2: Run** `npm --prefix typescript test`, `pytest tests/test_ts_ingest_redaction.py tests/test_ts_driver_redaction.py -q` → FAIL. **Step 3: Implement.** `rt.mjs` must not grow: move the BOOT's env lines into a `bootEnv()` in `redact.mjs` that returns `{env, envHash, envRedaction, redaction}`, and have `boot()` spread it. `VERSION` → `0.5.0` (find its definition; `grep -n "0.4.0" typescript/src/*.mjs typescript/package.json`).
- [ ] **Step 4: Run** all three suites → PASS; `wc -l typescript/src/rt.mjs` ≤ 798. Mutations: drop the `delete env[KEY_VAR]` → the child test fails; `mode: 0o644` → mode test fails.
- [ ] **Step 5: Commit** `feat(ts): the TypeScript runtime redacts its BOOT environment; the driver hands it the key; ingest carries redaction through and applies it to 0.4.0 spools; sensorium-ts 0.5.0`.

### Task 6: `info` prints the rule; `refocus` compares digests

**Files:** Modify `src/sensorium/query/info_cmd.py:193-212`, `refocus_env.py` (new `RedactionPair`, `compare_redacted`), `refocus_world.py` (`_env_diff`, `_env_state`, `UNVERIFIABLE_ENV`, `_SHORT_UNVERIFIABLE`, `unverifiable_checks`), `refocus_licence.py:113-133` (`env_of` passes `new.meta`), `refocus_cmd.py:533` (passes `now_meta=None`), the five unpack sites of A2. Create `tests/test_info_redaction.py`, `tests/test_refocus_redaction.py`, `docs/trace-format/vectors/v42-redaction-render.json`, `v43-refocus-redacted-env.json`; append two rows to `docs/trace-format/VECTORS.md`.

**Interfaces (`refocus_env.py`):**
```python
@dataclass(frozen=True)
class RedactionPair:
    was: dict[str, str | None]; was_key_id: str | None; was_keyed: bool
    now: dict[str, str | None] | None; now_key_id: str | None; now_keyed: bool   # now None → live plaintext side
    key: redact.Key
    @classmethod
    def of(cls, was_meta: dict, now_meta: dict | None, key: redact.Key) -> "RedactionPair | None"  # None when neither side carries redaction.env
    def compare(self, name: str, before: str | None, after: str | None) -> bool | None
        # True equal / False differs / None uncomparable, per §6.2's table
```
`_env_diff(was, now, redaction=None) -> (changed, relocated, stripped, session, harness, uncomparable)`: for a name where `redaction.compare` returns None → `uncomparable`; True → `continue`; False → the existing partition (relocation/session/harness/changed) is NOT consulted — a redacted value has no path to reroot — so it goes to `changed`. `_env_state(meta, env, now_meta=None)`: the env line gains, when `uncomparable`: `; {n} redacted variable(s) not comparable ({reason}): {_capped(names)}`; the fact carries the same clause; the caveat is unchanged (uncomparable never withholds). `unverifiable_checks(orig, new)` appends `UNVERIFIABLE_ENV` when `redact.uncomparable(orig.meta, new.meta, Key.load(paths.trace_root()))[0]` is non-empty.

`info`: A7's `env:` field and A8's `redaction:` line, verbatim from §6.1, with `key mode` appended in parentheses when `Key.load(...).mode_note()` is not None and the trace's `key_id` equals the store's.

- [ ] **Step 1: Tests.** `test_info_redaction.py` (build traces with `tests.vectors.build`-style meta or `TraceWriter` + `finalize_synthetic` from `tests.helpers`): the four `redaction:` lines and the three `env:` forms of A7 (on, on-with-zero, absent/off), `+M more` at nine names. `test_refocus_redaction.py` on meta-built Python pairs (`tests/refocus_programs.rec`/`new_run` — read them): (1) both sides `redaction.env {"T": d}` same key id → `_env_diff` puts `T` nowhere, line says `unchanged`; (2) digests differ → `T` in `changed`, line `CHANGED … T`; (3) original digest, `now` plaintext with the store key present and key ids equal → compared through the HMAC, equal → unchanged, different → changed; (4) key ids differ → `uncomparable == ["T"]`, line carries `1 redacted variable(s) not comparable (different keys): T`, caveat None; (5) original `keyed False` → reason `unkeyed`; (6) `unverifiable_checks` returns `UNVERIFIABLE_ENV` in case 4 and not in case 1; (7) `relicense` on a MATCH with only that caveat grants.
- [ ] **Step 2: Vectors.** `v42-redaction-render`: one Python trace, meta `redaction` on with `env {"SECRET_TOKEN": "0123456789abcdef"}`, env `{"SECRET_TOKEN": "<redacted>", "HOME": "/h"}`; questions: `info $RUN` `expect_contains` `env:` … `(2 vars, 1 redacted: SECRET_TOKEN)` and `redaction: rule v1, keyed (key `; `expect_absent`: the string `hunter2` (planted nowhere — the vector asserts the marker, and PR B extends it). A second copy-less question on a trace built with NO `redaction` key: `redaction: none -- recorded before redaction existed; plaintext throughout`. `v43-refocus-redacted-env`: two copies (`copies: 2`), the second with `refocus_of: $RUN` and stamped `refocus_licence_unverifiable` containing `UNVERIFIABLE_ENV`; `info $RUN2` shows `licence unverifiable: … env (redacted, not comparable)`. Rows in `VECTORS.md` in that table's voice.
- [ ] **Step 3: Run** → FAIL. **Step 4: Implement** to the interfaces. **Step 5: Run** `pytest -q` whole and `python corpus/run_corpus.py` → green; every legacy refocus test unchanged. Mutations: make `compare` return False for equal digests → case 1 fails; drop the `UNVERIFIABLE_ENV` append → case 6 fails; print the digest instead of the name in the `env:` field → the info test's `expect_absent` on the digest fails (add that assertion).
- [ ] **Step 6: Commit** `feat(query): info names what was redacted; refocus compares redacted variables by digest and names the ones it cannot`.

### Task 7: Contract, docs, versions

**Files:** `docs/TRACE-FORMAT.md` (§4 "Optional keys, by writer" first paragraph; §5's capture-shape paragraph — one sentence saying the `redacted` object arrives in PR B), `docs/trace-format/TYPESCRIPT-KEYS.md` (Container: `envRedaction`, `redaction`), `rust/README.md` ("Where traces go": the header's two siblings, the 0600 modes, the key), `docs/redaction.md` (new: §2–§4, §6 of the spec in user voice, with the honest limits and "not a secret scanner"), `README.md` ("What a trace file holds": the env bullet and the "no redaction pass" paragraph rewritten to what PR A makes true — and to say captured values are still plaintext until PR B; net-zero lines), `docs/query.md` (one pointer line — it is at 797: remove one blank line to make room), `CHANGELOG.md` (`## 0.15.0 — <date>`), `pyproject.toml` (0.15.0), `tests/test_release_tokens.py` (passes by construction).

- [ ] **Step 1:** Write the prose. Every sentence that makes a claim points at the test or vector that pins it (`v42`, `v43`, `tests/test_redact.py`, `tests/test_record_redaction.py`).
- [ ] **Step 2:** `pytest -q tests/test_release_tokens.py tests/test_ceiling.py` → PASS; `wc -l README.md` ≤ 796; `grep -rn "no redaction pass" README.md docs/TRACE-FORMAT.md` → 0 hits.
- [ ] **Step 3:** `uv pip install -p .venv/bin/python -e .` (the recorder id reads the installed version); `sensorium info last` on a fresh recording prints `recorder: sensorium 0.15.0`.
- [ ] **Step 4: Commit** `docs+chore: rule v1 in the contract, the README and docs/redaction.md; Python 0.15.0`.

### Task 8: E16 part A — instrument, dry run, measurement

**Files:** Create `tests/acceptance_e16/e16a.sh`, `tests/acceptance_e16/e16a.py`, `tests/acceptance_e16/assemble_e16a.py`, `tests/test_acceptance_e16_cells.py`; append §2 part A to the record.

**The instrument** (`e16a.sh`, on `typescript/acceptance/e15.sh`'s shape — read it for the launcher idioms): (1) preflight: versions (`sensorium info` on a throwaway recording; `cargo sensorium --version` if it has one, else the binary's `Cargo.toml`), `df`, the corpus `node_modules` present; (2) mint the token to `$E16_DIR/token` 0600; (3) `export SENSORIUM_DIR=$E16_DIR/store-a SENSORIUM_E16_TOKEN=$(cat token)`; (4) record the three A10 programs, transcripts to `$E16_DIR/a-transcripts/`; (5) H1-env: `grep -rc --binary-files=text -F "$TOKEN" $E16_DIR/store-a $E16_DIR/store-a/ts-spools <rust spool dir under CARGO_TARGET_DIR>/sensorium/spool` per file → a table `file, count`; (6) H2: `find $E16_DIR/store-a -exec stat -c '%a %n' {} +` and the Rust/TS spool dirs; (7) H3: the two refocus runs, then `export SENSORIUM_E16_TOKEN=sk-e16-<fresh>` and the two again; (8) H6-env: `sensorium info <run>` per trace, parse `redacted:` names; (9) `e16a.py` reads all of it and writes `results-a.json` `{cells: {H1: {...}, H2: …}, lens: {…}, versions: {…}}` with `None` for anything not measured and a `dropped` list; (10) `assemble_e16a.py` renders §2 part A: the pin table, the per-file grep table, the mode table, the two refocus transcript excerpts, the H6 names, the verdict word per cell FROM §9's rule, and the part's word.

- [ ] **Step 1: Cell tests** (`tests/test_acceptance_e16_cells.py`): each cell function on hand-built inputs — H1 passes on all-zero counts and STOPs on one non-zero naming the file; H2 STOPs on one `644`; H3 PASS/STOP on parsed refocus transcripts (reuse `rust/tests/acceptance_e4_read.py`'s licence parser — import it, it is Python); H6 exact set. `None` anywhere → the cell is `dropped`, never PASS. Verdict words come from a table copied from §9, not retyped.
- [ ] **Step 2: Dry run** with a 4-character decoy token and the kill rules at 60 s: every artifact path the reader opens exists (the dry-run checklist: *is the value in the FILE a later step reads?*); the dry run's outputs are deleted before the measurement.
- [ ] **Step 3: Measure once.** Run `e16a.sh`; assemble; append §2 part A to the record with the date measured; the lock test's second assertion now sees `### measured`. **A STOP on H1 is a missed path**: fix it in a named commit, delete `store-a`, mint a fresh token, re-run from zero, and the record's §2 says which run is the first PASS and what the first run found.
- [ ] **Step 4: Commit** `test(acceptance): E16 part A measured — <the per-cell words>` (instrument + record; no box path outside the pin table).

### Task 9: Ledger, debt, the spec's amendments, the PR

- [ ] **Step 1:** `docs/CARRIED-DEBT.md`: a `## 2026-09-XX — redaction PR A` section: settled (the env leak, the modes, the key), deferred with rulings (PR B: values, wire v4, content rule; PR C: retrofit; `seal`; the Rust spool window; Windows), process lessons (whatever the tasks taught — at least one is the census input decision A6).
- [ ] **Step 2:** The spec's §13: decisions A1–A11 in a table, dated; §9 footnoted for A1.
- [ ] **Step 3:** Full green: `pytest -q`, `python corpus/run_corpus.py`, `cargo test --workspace` + fmt + clippy + `mechanics.sh`, `npm --prefix typescript test`, `tests/test_ceiling.py`. `git show --stat` of every commit re-read for stray files.
- [ ] **Step 4:** Push `feat/redaction-a`; PR titled `feat: secrets redaction A — rule v1, the store key, env redaction, 0600 files (E16 part A)`, body = the record's part-A verdict table + the CHANGELOG entry + the CARRIED-DEBT section; base `main` (the docs branch's PR merges independently; retarget nothing). Merge is Brice's.

## Self-review (run before handing off)

- **Spec coverage, PR A's share:** §2.1 name rule → T1; §2.4 knobs → T1/T2/T3/T5; §2.5 fixture → T1 (+ Rust T3, TS T5 readers); §3 key → T1/T2/T4/T5; §4.1 env marker → T2/T3/T5; §4.3 meta → T2/T4/T5; §4.4 env_hash → T2/T3/T4/T5; §5.1–5.3 env halves → T2/T3/T5; §5.4 converters → T4/T5; §5.5 modes → T2/T3/T4/T5; §6.1 info → T6; §6.2 refocus → T6; §8 contract/vectors/census → T6/T7/T1; §9 E16 part A → T0/T8; §10 docs/versions → T7. Not PR A's: §2.2, §2.3's span operation, §4.2, §5's value halves, §6.3, §7 — named as B/C in T9's debt section.
- **Placeholders:** none intended; `<date>` is the commit date, filled at the task.
- **Type consistency:** `redact.Key.load` / `load_or_create` / `from_hex`; `RedactionPair.of` / `.compare`; `_env_diff` six-tuple; `UNVERIFIABLE_ENV`; Rust `Key::from_env` / `redact_env` / `redaction_json`; TS `Key.fromHex` / `redactEnv` / `redactionMeta` / `bootEnv` — used with these names throughout.
