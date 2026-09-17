# E17 — sensorium as an MCP server, measured

## 1. Pre-registration (locked)

### 9. E17, pre-registered

Measured **once**, after the branch is complete and reviewed, on this
box, from a plain shell (not inside the session that wrote the code).
Work root `E17_DIR=/mnt/extra/sensorium-rung2/e17`; instrument
`tests/acceptance_e17/e17.py` with cells in `e17_cells.py`, assembled by
`assemble_e17.py` into `docs/superpowers/acceptance/<date>-sensorium-e17-
mcp.md`; rehearsed first under `e17-dry` on a two-case corpus subset so
every artifact path the reading step needs is checked to exist before the
run. Lens on every number: Python version, `sensorium 0.18.0`, the
official `mcp` client's version, Claude Code's version. Both readings
written here before the instrument exists; the point estimate decides; an
infrastructure kill (any cell over 10 min, the part over 45 min) is a
rerun from zero, never a splice.

| H | Claim | PASS | STOP |
|---|---|---|---|
| **H1 parity** | `run_corpus.py --via mcp --require-driver` over all cases. For every question on a **read-only** tool the harness also runs the CLI path and compares: stdout byte-identical, exit identical. `refocus` questions (they execute, and a rerun's text carries a fresh run id) are held to their expectations and exit only. | 0 failures; every read-only question byte-identical and exit-identical; skipped set equals Task 0's locked not-a-tool list exactly | any failure, any difference, any skip outside the list — named per question |
| **H2 conformance** | The official Python SDK client (dev extra `conformance`, pinned major) over stdio: (a) its default connect succeeds (discover, or initialize on fallback); (b) `list_tools` = 9 names without `--allow-run`, 11 with; (c) `call_tool("runs")` returns one text block whose first line matches `^exit [0-3]: ` and `structuredContent.exit` an int; (d) a hand-written minimal client: `initialize` with `2025-03-26` echoed, with `1900-01-01` answered `2025-11-25`, a `_meta` version `1900-01-01` answered `-32022` with the supported list. | all of a–d | any |
| **H3 the cap** | `tree` with `depth 50`, `limit 100000` on the largest trace (by event count, from `runs`) in a `cp -a` copy of `~/.sensorium/traces`. Instrument check first: the same call through the CLI exceeds 65536 bytes, else the cell measured nothing and STOPs as instrument. | text ≤ 65536 + marker; marker names `depth, limit, around`; head and tail both non-empty; audit `truncated: true` | any |
| **H4 the gate** | Without the flag: `tools/list` names exactly the nine; `tools/call record` is `-32602 Unknown tool: record`. With it: eleven; `record` of the `silent_swallow` corpus program from its directory answers `exit 0:`, a trace appears under `--store`, and `exceptions` on it through the wire satisfies that case's expectations. | all | any |
| **H5 liveness** | With the flag, `record` of `probes/sleeper.py` (sleeps 30 s). The client pings every 0.5 s during the call: every ping answered under 1 s (max recorded). Cancel at 5 s: the child's process group gone within 2 s (`os.killpg(pgid, 0)` raises), the next `tools/call` answered. Then `--run-timeout 3` on the same probe: header `no answer: timed out after 3 s…`, `isError: true`, group gone within 5 s of the call. | all | any |
| **H6 secrecy** | The `secret_in_env` case through the wire with its token in the server's environment: the token appears in no result text (the case's `expect_absent`), not in `mcp.jsonl`, not in the server's stderr transcript. **H6b:** a `grep` call whose pattern is `sk-e17-<33 random>` (minted, never committed): the audit line holds `<redacted>`, not the value; the child's stdout may hold it (the CLI echoes the pattern) and that is the CLI's documented behaviour, not this cell's. | 0 occurrences in the three places; H6b marker present, value absent from the audit | any occurrence |
| **H7 the deploy target** | One Claude Code session (`claude mcp add … --allow-run`, cwd a copy of `silent_swallow`), prompt: *record the tests and find the swallowed exception using the sensorium tools only*. Transcript kept. **n = 1, reported not gated**, tier stated (the model Claude Code ran that day). | the session used ≥ 3 sensorium tools and named the swallowing frame the case's `truth` names | reported either way; a STOP names what the model did instead |
| **latency** | 20 × `runs` through the wire vs 20 × `python -m sensorium runs` directly, same store, medians and the ratio. **Never gated.** | — | — |

Pinned ambient variables: `SENSORIUM_DIR` per cell as stated,
`SENSORIUM_NO_INVOCATION_LOG` unset, `PYTEST_ADDOPTS` unset, the venv's
own `python`, no `sensorium` on PATH ahead of it (asserted by the
instrument's preflight, which prints `which -a sensorium`). Every cell
writes its transcript under `$E17_DIR/<cell>/`; `None` for an unmeasured
value and a `dropped` list, never a zero that was not measured.

### The plan's pre-registration block

- **The subject** is the branch's own `sensorium mcp` at Python **0.18.0**, run by the worktree venv's absolute interpreter (`<venv>/bin/python -m sensorium mcp …`); the oracle for H2 is the official `mcp` Python SDK **2.2.x** installed in that venv from the `conformance` extra; H7's client is Claude Code **2.1.258** (or whatever `claude --version` prints on the day, recorded). Versions expected are asserted by the preflight and recorded in §2.
- **Locations** are the record's §2 pin table only: `E17_DIR=/mnt/extra/sensorium-rung2/e17`, the rehearsal root `E17_DIR-dry` (`E17_DRY=1`), the store copy `$E17_DIR/store` (a `cp -a` of `~/.sensorium/traces` and `redaction.key`; its traces are read for H3 and the latency cell and never written — the server's own `mcp.jsonl` and `invocations.jsonl` land beside them, which is P9's rule, not a write to a trace), fresh empty stores `$E17_DIR/h4/store`, `$E17_DIR/h5/store` and `$E17_DIR/h5/store-timeout`, `$E17_DIR/h6/store` for the cells that record, transcripts `$E17_DIR/<cell>/`, instrument output `$E17_DIR/out/`.
- **The not-a-tool list, locked:** exactly three questions, all in `corpus/redact_retrofit`: `what-would-the-retrofit-take`, `the-retrofit-rewrites-once`, `a-second-pass-finds-nothing`. H1 reads `via_cli` equal to this list and nothing else; no `ts` or `run` question exists in the corpus at `0385d80`.
- **H1's reading:** `.venv/bin/python corpus/run_corpus.py --via mcp --compare-cli --require-driver --json` from the worktree, the Rust driver built from the worktree first on PATH and `corpus/typescript` `npm ci`'d. PASS iff `cases` and `questions` equal the census locked at Task 0 (**115 cases / 253 questions** at `0385d80`, re-counted by the cells test from `load_cases()`), `failures == []`, `errors == []`, no `exit_reason`, `via_cli` equals the locked three, and `mcp_differences == []` (every read-only question's stdout byte-identical and exit identical; `refocus` questions are never re-run and are held to their own expectations and `expect_exit`). Any difference is named per question with the first differing line. The per-case server runs with `--max-output 1048576` so the cap is never what H1 measures.
- **H2's reading:** `.venv/bin/python -m pytest -q tests/test_mcp_conformance.py -rA`; PASS iff exit 0 and the summary counts ≥ 9 passed and 0 skipped (a skip means the extra is missing and the cell measured nothing → STOP as instrument). The tests are (a) `Client(server)` connects with `protocol_version == "2026-07-28"` and `server_info.name == "sensorium"`; (b) `list_tools` = 9 names without `--allow-run`, 11 with; (c) `call_tool("runs", {})` returns one text block whose first line matches `^exit [0-3]: ` and `structured_content["exit"]` an int; (d) `Client(server, mode="legacy")` connects with `protocol_version == "2025-11-25"`; (e) `call_tool("nope", {})` raises `MCPError` with `code == -32602` and message `Unknown tool: nope`; (f) `read_timeout_seconds=1` on a `record` of the sleeper raises `MCPError` `-32001` and the server then answers `list_tools(cache_mode="bypass")` on the same client (a wire round trip, never a cache hit); (g) the hand-written `corpus.mcp_client.McpClient`: `initialize` offering `2025-03-26` is echoed, offering `1900-01-01` is answered `2025-11-25`, and after a modern handshake a `tools/list` sent with `_meta` version `1900-01-01` (and `clientCapabilities: {}`) is `-32022` with `data.supported == ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"]`; (h) after a modern handshake a `tools/list` sent with `_meta` carrying the version but no `clientCapabilities` is `-32602` naming the key; (i) the server's stderr transcript holds no line starting with `{`; (j) the SDK's own `session.send_discover("1900-01-01")` raises `MCPError` `-32022` with the same `supported` list.
- **H3's reading:** the largest trace by event count in the copy (chosen by `runs`' `events:` column); `tree` with `depth 50`, `limit 100000` through the wire against `--store $E17_DIR/store`; instrument check first: the same argv through `<venv>/bin/python -m sensorium` writes more than 65536 bytes to stdout, else STOP as instrument. PASS iff, in UTF-8 bytes, the text after the header line with the marker line removed is ≤ 65536 (the header line and the marker are never counted), the header line is intact and starts `exit 0: `, the marker matches `^\[\.\.\. \d[\d,]* lines \(\d[\d,]* bytes\) omitted; narrow with: depth, limit, around \.\.\.\]$`, both the head and the tail are non-empty, and the last `mcp.jsonl` line has `"truncated": true`. The cells test derives that regex's `narrow with:` list from `tools.narrowing_fields(tools.table(True)["tree"])`, so the locked text and the code cannot drift apart unnoticed.
- **H4's reading:** without the flag: `tools/list` names == `{runs, info, tree, frame, grep, exceptions, flow, watch, diff}`, `tools/call record` → `-32602`, message `Unknown tool: record`. With the flag: names == the nine + `{record, refocus}`; `record` of `corpus/silent_swallow/main.py` from a copy of that case's directory answers a header `exit 0: the recorded command's own status …`, `runs` through the wire lists one trace, and `exceptions` on it satisfies that case's `what-was-dropped` question (`check_question` on the text minus header).
- **H5's reading:** with the flag and a fresh empty `--store $E17_DIR/h5/store`, `record` of `tests/acceptance_e17/probes/sleeper.py` (a script that sleeps 30 s and spawns one `sleep 30` child); the client pings every 0.5 s from the moment the call is sent: **at least 8 pings are sent before the cancel** (fewer is STOP as instrument) and every ping is answered in < 1.0 s (the maximum recorded); at t=5 s, having first observed `os.killpg(pgid, 0)` SUCCEED (the group was alive; a record that never spawned cannot pass by absence), the client sends `notifications/cancelled` for the call: within **2.0 s** `os.killpg(pgid, 0)` raises `ProcessLookupError` for the child's group (the pgid read from the server's stderr line `sensorium mcp: child <pid> pgid <pgid> tool record`, which the server prints for every spawn), no response for that id arrives within 3 s, and a following `tools/call runs` is answered listing the one incomplete trace. Then a second server with `--run-timeout 3` on a second fresh store: the same `record` answers within 6 s of the send a result with `isError: true`, header `no answer: timed out after 3 s (server flag --timeout / --run-timeout)`, `structuredContent.exit == null`, and the group is gone within **5 s of the send** (polled every 0.1 s). PASS iff all; STOP names the clause.
- **H6's reading:** `corpus/secret_in_env` copied and recorded as `run_corpus._record` would (`run --focus main:handle -- main.py`) with the case's `env:` block in which `SENSORIUM_CORPUS_TOKEN`'s value is REPLACED by a minted `sk-e17-<33 chars from [A-Za-z0-9]>` (written to `$E17_DIR/token` at 0600, never committed, never printed); then a server started with that same variable and value in ITS environment — verified before any question by reading `/proc/<server pid>/environ` and asserting the `NAME=<token>` entry is present (read and compared in memory, never written anywhere; absent → STOP as instrument); every question of the case asked through the wire and `check_question` run on `stdout + stderr` with the yaml's `tok_corpus_…` literal substituted by the minted value. PASS iff every question's expectations hold (else STOP as instrument, naming the question — the case's own `expect_absent` and marker rows are what prove the token was at the four value sites and was withheld), the counts were taken over exactly the case's question count of result texts, a `mcp.jsonl` with at least that many lines and a non-empty stderr transcript (a missing file is `dropped` with the reason, never a 0), AND the minted token's bytes occur 0 times in every result text, in `mcp.jsonl`, and in the server's stderr transcript. **H6b:** `grep` with `pattern` = the token: the last `mcp.jsonl` line's `arguments.pattern` is `<redacted>` and the token occurs 0 times in `mcp.jsonl`; the result text MAY hold it (the CLI echoes its argument) and that occurrence is excluded from H6's count by construction (H6 counts before H6b runs).
- **H7's reading (n = 1, reported):** `claude mcp add sensorium -- $E17_DIR/h7/serve.sh` at user scope, where `serve.sh` is `exec <venv>/bin/sensorium mcp --allow-run 2>>$E17_DIR/h7/server.stderr`; a fresh `claude` session in a copy of `corpus/silent_swallow` (a single `main.py`; the case has no tests) with the prompt in `tests/acceptance_e17/probes/h7-prompt.txt` (*Using only the sensorium MCP tools, record `main.py` and find the exception that was swallowed; name the function whose frame swallowed it.*); the controller saves the transcript to `$E17_DIR/h7/transcript.txt` and writes `$E17_DIR/h7/h7.json` = `{"tools_used": [...], "recorded_command": [...], "named_frame": <bool>, "model": "<id>", "claude_version": "<v>", "handshake": "<the server's stderr handshake line>"}` by reading the transcript and `server.stderr`; the word is `reported` either way and the row records whether ≥ 3 sensorium tools were used, what the model passed to `record`, whether the named frame is the case's truth, and which handshake the deploy target opened with.
- **Latency (measured, never gated):** 20 × `tools/call runs` through the wire against the copy vs 20 × `<venv>/bin/python -m sensorium runs` directly; medians in ms and the ratio; also the time from server spawn to the `server/discover` answer.
- **Kill rules:** H1's cell timer is **3 × the CLI-path corpus wall time measured at Task 10 Step 1, never below 10 min**, recorded in the pin table; every other cell 10 min; the part 45 min plus H1's timer; a kill is an infrastructure event, rerun from zero with a fresh token. **Pinned ambient variables:** `SENSORIUM_DIR` per cell as stated, `SENSORIUM_NO_INVOCATION_LOG`, `SENSORIUM_NO_REDACT`, `PYTEST_ADDOPTS` unset (the instrument builds a complete environment: `PATH=<venv>/bin:$E17_CARGO_BIN:$E17_NODE_BIN:/usr/local/bin:/usr/bin:/bin` where `e17.sh` exports `E17_CARGO_BIN=$(dirname "$(command -v cargo)")` and `E17_NODE_BIN=$(dirname "$(command -v node)")` and both are recorded in the pin table; `HOME`, `LANG`, `PYTHONDONTWRITEBYTECODE=1`, `SENSORIUM_CARGO_SENSORIUM` as Task 10 sets it, plus what a cell adds; the preflight asserts `node --version` ≥ 24 and `cargo --version` exit 0 on that PATH unless `E17_DRY`). **None-vs-zero:** an unread value is `None` and its cell `dropped` with a reason; `0` is a count that was taken.

### 2026-09-17 — amendments beside the locked text above (written before the instrument ran)

Written after H7's first run and before any cell was measured by the instrument; the two locked bodies above are unchanged. Each entry names its ruling in the slice's ledger.

- **R18 (design).** `structuredContent` and `outputSchema` leave the wire: a `tools/call` result is text only, the header line is the exit's machine-readable carrier (`^exit (-?\d+): ` or `^no answer: `), `isError` stays. Why: the deploy target passes the model ONLY a result's structured content when one is present and drops the text for every non-error result (measured in H7's first run, below). Readings that referred to `structuredContent` now read: **H2 (c)** asserts the header regex, `is_error is False` and `structured_content is None`; **H5**'s timeout arm asserts the header `no answer: timed out after 3 s (server flag --timeout / --run-timeout)` and `CallResult.exit is None` as the client parses it from that header (no `structuredContent.exit == null`); H1, H3, H4, H6 are unchanged (the client's `exit` is parsed from the header everywhere).
- **R17 (H7's store and mode).** `serve.sh` runs `sensorium mcp --allow-run --store $E17_DIR/h7/store`, a fresh store, so the deploy-target session never writes the live store; the session is print mode (`claude -p <prompt> --model opus --output-format stream-json --verbose --allowedTools "mcp__sensorium__*"`) from the case copy, and `h7.json` also records `sensorium_tool_calls`. The model is recorded, as the locked row requires.
- **H7 is measured on the R18 server.** The first run (07:55–07:57 CDT, Claude Code 2.1.258, `claude-opus-5`, before R18) is evidence, kept at `$E17_DIR/h7-before/` (transcript, server stderr, `h7.json`): 40 sensorium calls, `record` of `["main.py"]`, `load_all` named correctly — reached by exit-code probing because the client hid the text. Its handshake was `initialize 2025-11-25 -> 2025-11-25`: Claude Code opened LEGACY, contrary to the spec's §3.1 sentence, which the §13 amendment corrects.
- **T_cli** = 63 s (the CLI-path corpus with both drivers at 6dbbb95) → H1's timer is the 600 s floor; `E17_H1_TIMER=600`.
- **The pin table** writes `E17_CARGO_BIN` and `E17_NODE_BIN` with `~` in place of the home directory (R16), so only `E17_DIR=` lines carry a box path.
- **Fresh stores per cell:** H4 `$E17_DIR/h4/store`; H5 `$E17_DIR/h5/store` and `$E17_DIR/h5/store-timeout`; H6 `$E17_DIR/h6/store`; H7 `$E17_DIR/h7/store`. The copy at `$E17_DIR/store` is read by H3 and the latency cell only.

## 2. Measured

### measured 2026-09-17

Measured once, on this box, under `e17.sh`. **E17: DONE** — H1 parity PASS  H2 conformance PASS  H3 the cap PASS  H4 the gate PASS  H5 liveness PASS  H6 secrecy PASS  H7 the deploy target reported  latency measured. 273 traces in the copy. 251.2s wall clock.

| cell | word | §9's rule | what was read |
|---|---|---|---|
| H1 parity | **PASS** | 0 failures; every read-only question byte-identical and exit-identical; skipped set equals Task 0's locked not-a-tool list exactly | 0 failure(s); 0 harness error(s); no `exit_reason`; 0 case(s) skipped; 0 MCP/CLI difference(s) over the read-only questions; `via_cli` holds 3 question(s) against the locked 3; 115 cases / 253 questions, against the locked 115 / 253 |
| H2 conformance | **PASS** | all of a–d | pytest exited 0; 10 passed, against §1's floor of 9 |
| H3 the cap | **PASS** | text ≤ 65536 + marker; marker names `depth, limit, around`; head and tail both non-empty; audit `truncated: true` | the header line reads `exit 0: the trace answered affirmatively`; 1 line(s) match §1's marker regex, which names `depth, limit, around`; 65135 bytes after the header with the marker line removed, against the 65536-byte bound; the head is 306 line(s); the tail is 32 line(s); the last `mcp.jsonl` line says truncated = True |
| H4 the gate | **PASS** | all | 9 tools without the flag; `tools/call record` without the flag answered -32602 'Unknown tool: record', against -32602 'Unknown tool: record'; 11 tools with `--allow-run`; `record` answered `exit 0: the recorded command's own status (2 and no trace when recordi`; `runs` through the wire lists 1 trace(s): 20260917-092446-76f719; `exceptions` satisfies `what-was-dropped` |
| H5 liveness | **PASS** | all | 10 pings sent, the slowest answered in 0.8 ms (ceiling 1000 ms); the child's group was gone 0.10 s after the cancel; no response for the cancelled id arrived; the next `runs` answered=True, listing 1 trace(s), 1 INCOMPLETE; the timeout arm's header is `no answer: timed out after 3 s (server flag --timeout / --run-timeout)`; the timeout result's `isError` is True; the header's exit (`CallResult.exit`) is None; answered 3.05 s after the send (cap 6.0 s); the group was gone 3.06 s after the send (cap 5.0 s) |
| H6 secrecy | **PASS** | 0 occurrences in the three places; H6b marker present, value absent from the audit | 4 result text(s) counted, over the case's 4 question(s); `mcp.jsonl` holds 4 line(s), against the 4 calls made; the stderr transcript holds 430 byte(s); 0 occurrence(s) of the token in 0× the result texts, 0× `mcp.jsonl`, 0× the stderr transcript; H6b: the audit line's `arguments.pattern` is '<redacted>'; H6b: 0 occurrence(s) of the token in `mcp.jsonl` after the `grep` |
| H7 the deploy target | **reported** | — | 7 sensorium tool(s) used (Skill, ToolSearch, mcp__sensorium__record, mcp__sensorium__info, mcp__sensorium__exceptions, mcp__sensorium__frame, and 1 more), ≥ 3, over 5 sensorium call(s); `record` was passed ['main.py']; the frame the session named IS the case's `truth` frame `load_all`; the deploy target opened with `handshake initialize 2025-11-25 -> 2025-11-25`; model `claude-opus-5` under Claude Code 2.1.258 |
| latency | **measured** | — | median `runs` through the wire 3704.9 ms vs 3709.1 ms through the CLI, a ratio of 1.00×; server spawn to the `server/discover` answer 49.5 ms |

#### Pins

| pin | path |
|---|---|
| work root | `E17_DIR=/mnt/extra/sensorium-rung2/e17` |
| the copy (the subject) | `$E17_DIR/store/` |
| H4's store | `$E17_DIR/h4/store/` |
| H5's stores | `$E17_DIR/h5/store/, $E17_DIR/h5/store-timeout/` |
| H6's store | `$E17_DIR/h6/store/` |
| transcripts | `$E17_DIR/transcripts/` |
| instrument output | `$E17_DIR/out/` |
| copied out of (never written to) | `~/.sensorium` |
| E17_CARGO_BIN | `~/.cargo/bin` |
| E17_NODE_BIN | `~/.nvm/versions/node/v24.16.0/bin` |
| H1's cell timer | `600 s` |
| the part's cap | `3300 s` |

#### Versions

| version | read | §1 expected |
|---|---|---|
| `sensorium` (the venv the server ran from) | 0.18.0 | 0.18.0 |
| Python | 3.13.13 | — |
| `mcp` (H2's oracle, the official SDK) | 2.2.0 | 2.2.x |
| Claude Code (H7's client) | 2.1.258 (Claude Code) | — |

#### H1 — PASS

| clause | what was read | word |
|---|---|---|
| failures | 0 failure(s) | **PASS** |
| errors | 0 harness error(s) | **PASS** |
| exit_reason | no `exit_reason` | **PASS** |
| skipped | 0 case(s) skipped | **PASS** |
| differences | 0 MCP/CLI difference(s) over the read-only questions | **PASS** |
| via_cli | `via_cli` holds 3 question(s) against the locked 3 | **PASS** |
| census | 115 cases / 253 questions, against the locked 115 / 253 | **PASS** |

| reading | value |
|---|---|
| `census` | [115, 253] |
| `differences` | [] |
| `dry` | False |
| `via_cli` | ['redact_retrofit/what-would-the-retrofit-take', 'redact_retrofit/the-retrofit-rewrites-once', 'redact_retrofit/a-second-pass-finds-nothing'] |

#### H2 — PASS

| clause | what was read | word |
|---|---|---|
| exit | pytest exited 0 | **PASS** |
| passed | 10 passed, against §1's floor of 9 | **PASS** |

| reading | value |
|---|---|
| `passed` | 10 |
| `rc` | 0 |
| `skipped` | 0 |

#### H3 — PASS

| clause | what was read | word |
|---|---|---|
| header | the header line reads `exit 0: the trace answered affirmatively` | **PASS** |
| marker | 1 line(s) match §1's marker regex, which names `depth, limit, around` | **PASS** |
| bytes | 65135 bytes after the header with the marker line removed, against the 65536-byte bound | **PASS** |
| head | the head is 306 line(s) | **PASS** |
| tail | the tail is 32 line(s) | **PASS** |
| truncated | the last `mcp.jsonl` line says truncated = True | **PASS** |

| reading | value |
|---|---|
| `bytes` | 65135 |
| `cli_bytes` | 28514015 |
| `head_lines` | 306 |
| `header` | exit 0: the trace answered affirmatively |
| `tail_lines` | 32 |

#### H4 — PASS

| clause | what was read | word |
|---|---|---|
| nine | 9 tools without the flag | **PASS** |
| record-is-unknown | `tools/call record` without the flag answered -32602 'Unknown tool: record', against -32602 'Unknown tool: record' | **PASS** |
| eleven | 11 tools with `--allow-run` | **PASS** |
| record | `record` answered `exit 0: the recorded command's own status (2 and no trace when recordi` | **PASS** |
| runs | `runs` through the wire lists 1 trace(s): 20260917-092446-76f719 | **PASS** |
| exceptions | `exceptions` satisfies `what-was-dropped` | **PASS** |

| reading | value |
|---|---|
| `error_off` | {'code': -32602, 'message': 'Unknown tool: record'} |
| `names_off` | ['runs', 'info', 'tree', 'frame', 'grep', 'exceptions', 'flow', 'watch', 'diff'] |
| `names_on` | ['runs', 'info', 'tree', 'frame', 'grep', 'exceptions', 'flow', 'watch', 'diff', 'refocus', 'record'] |
| `record_header` | exit 0: the recorded command's own status (2 and no trace when recording was refused) |
| `traces` | ['20260917-092446-76f719'] |

#### H5 — PASS

| clause | what was read | word |
|---|---|---|
| pings | 10 pings sent, the slowest answered in 0.8 ms (ceiling 1000 ms) | **PASS** |
| group-gone | the child's group was gone 0.10 s after the cancel | **PASS** |
| no-response | no response for the cancelled id arrived | **PASS** |
| runs-after | the next `runs` answered=True, listing 1 trace(s), 1 INCOMPLETE | **PASS** |
| timeout-header | the timeout arm's header is `no answer: timed out after 3 s (server flag --timeout / --run-timeout)` | **PASS** |
| timeout-is-error | the timeout result's `isError` is True | **PASS** |
| timeout-exit | the header's exit (`CallResult.exit`) is None | **PASS** |
| timeout-answered | answered 3.05 s after the send (cap 6.0 s) | **PASS** |
| timeout-group-gone | the group was gone 3.06 s after the send (cap 5.0 s) | **PASS** |

| reading | value |
|---|---|
| `group_gone_s` | 0.1 |
| `ping_max` | 0.001 |
| `pings_sent` | 10 |
| `runs_after` | {'answered': True, 'incomplete': 1, 'traces': 1} |
| `timeout_answered_s` | 3.055 |
| `timeout_group_gone_s` | 3.055 |

#### H6 — PASS

| clause | what was read | word |
|---|---|---|
| texts | 4 result text(s) counted, over the case's 4 question(s) | **PASS** |
| audit-lines | `mcp.jsonl` holds 4 line(s), against the 4 calls made | **PASS** |
| stderr | the stderr transcript holds 430 byte(s) | **PASS** |
| occurrences | 0 occurrence(s) of the token in 0× the result texts, 0× `mcp.jsonl`, 0× the stderr transcript | **PASS** |
| h6b-marker | H6b: the audit line's `arguments.pattern` is '<redacted>' | **PASS** |
| h6b-absent | H6b: 0 occurrence(s) of the token in `mcp.jsonl` after the `grep` | **PASS** |

| reading | value |
|---|---|
| `checks_run` | 4 |
| `counts` | {'in_jsonl': 0, 'in_stderr': 0, 'in_texts': 0, 'jsonl_lines': 4, 'questions': 4, 'stderr_bytes': 430, 'texts': 4} |
| `h6b` | {'in_jsonl': 0, 'pattern': '<redacted>'} |
| `proc_check` | PASS |

#### H7 — reported

**No clause table (reported).** §9 gives this row no PASS/STOP column, so it has no clauses

| reading | value |
|---|---|
| `claude_version` | 2.1.258 |
| `handshake` | handshake initialize 2025-11-25 -> 2025-11-25 |
| `model` | claude-opus-5 |
| `named_frame` | True |
| `recorded_command` | ['main.py'] |
| `sensorium_tool_calls` | 5 |
| `tools_used` | ['Skill', 'ToolSearch', 'mcp__sensorium__record', 'mcp__sensorium__info', 'mcp__sensorium__exceptions', 'mcp__sensorium__frame', 'mcp__sensorium__tree'] |

#### Latency

| reading | value |
|---|---|
| median `runs` through the wire | 3704.907 ms |
| median `runs` through the CLI | 3709.077 ms |
| ratio | 0.999× |
| server spawn to the `server/discover` answer | 49.467 ms |

#### Phases

| phase | seconds | error |
|---|---|---|
| preflight | 0.404 | — |
| copy-store | 0.053 | — |
| h1-corpus | 81.25 | — |
| h2-conformance | 2.37 | — |
| h3-cap | 6.221 | — |
| h4-gate | 0.458 | — |
| h5-liveness | 11.373 | — |
| mint | 0.0 | — |
| h6-secrecy | 0.577 | — |
| h7-read | 0.0 | — |
| latency | 148.467 | — |
| versions | 0.059 | — |

#### Erratum (2026-09-17, the controller, same day, after reading the raw)

The H7 row's `what was read` says "7 sensorium tool(s) used (Skill, ToolSearch, …)": the cell counted every distinct tool NAME in `h7.json`'s `tools_used`, including Claude Code's own `Skill` and `ToolSearch`, which are not sensorium's. Read from the same file by hand: the distinct sensorium tools were **5** (`record`, `info`, `exceptions`, `tree`, `frame`), the `sensorium_tool_calls` field is **5**, and the locked "≥ 3" holds either way. The measured value (`h7.json`) is untouched; the cell's counting is a rendering defect carried to the next slice. The same run's handshake line — `initialize 2025-11-25 -> 2025-11-25` — records that Claude Code 2.1.258 opened with the LEGACY handshake, not `server/discover`.
