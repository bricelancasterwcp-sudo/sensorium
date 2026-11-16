# sensorium

Record one run of your program, then let a coding agent ask what actually happened: call trees, exceptions, and where a value came from, answered from the trace or refused.

## What Sensorium is

Sensorium records one run (every call, return, and exception, with captured values) into a SQLite trace, and answers debugging questions from that trace in plain text. Four recorders write [trace format 4](docs/TRACE-FORMAT.md). One command line, `sensorium`, reads all four.

- **Python**: `sensorium run -- <command>` uses PEP 669 (`sys.monitoring`). Python 3.12+, no runtime dependencies. A Python child (`subprocess`, `multiprocessing`, pytest-xdist) is recorded into that same run. `--no-children` or `SENSORIUM_NO_CHILDREN=1` records the parent only. A non-Python child is counted and not traced.
- **Rust**: `cargo sensorium test` or `cargo sensorium run`. Stable rustc, Linux. [rust/README.md](rust/README.md).
- **TypeScript**: `sensorium ts run [--focus <spec>]… -- vitest run …` or `-- node --test …`. Node 24, vitest 4.1. [typescript/README.md](typescript/README.md).
- **C**: `sensorium c run -- <cmd>` for a Linux x86-64 debug build (gcc or clang, `-O0` or `-Og`). [c/README.md](c/README.md).

A query refuses by name when a recorder lacks a capability.

Two commitments run through all of it. The instrument never answers from data it does not have: truncated captures are marked, sites a predicate could not be evaluated at are counted, a recording that died is labelled, and a rerun that was a different execution says so. Nothing here guesses. Every answer is a deterministic function of the recorded trace, and where the trace cannot settle a question the output says so instead of inferring. `refocus` is the one command that executes anything: it re-runs the program and says whether what came back was the same execution. The per-command limits are [docs/claims.md](docs/claims.md).

## Quickstart (Python 3.12+, uv)

    uv venv .venv && uv pip install -p .venv/bin/python "sensorium-trace @ git+https://github.com/bricelancasterwcp-sudo/sensorium" pytest
    .venv/bin/sensorium run -- pytest tests/test_something.py
    .venv/bin/sensorium exceptions last

Run these from your project root, in your project's own venv, so recordings import your dependencies.

## Connect your agent (MCP)

Use the absolute path to your project venv's `sensorium`. `--allow-run` lets the agent record and rerun; leave it off for read-only.

Cursor, `.cursor/mcp.json`, and Claude Desktop, `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sensorium": {
      "command": "/abs/path/to/project/.venv/bin/sensorium",
      "args": ["mcp", "--allow-run"]
    }
  }
}
```

VS Code, `.vscode/mcp.json`:

```json
{
  "servers": {
    "sensorium": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/sensorium",
      "args": ["mcp", "--allow-run"]
    }
  }
}
```

Claude Code:

    claude mcp add sensorium -- /abs/path/to/project/.venv/bin/sensorium mcp --allow-run

`sensorium mcp` serves the same store on stdio. Every query except `redact` is a tool. `record`, `refocus`, and `record_c` exist only with `--allow-run`. Tools, the result header, the cap, and the audit file: [docs/mcp.md](docs/mcp.md).

## How this differs from live debuggers and LLM tracing

- **Live debuggers over MCP** (DAP-based servers) make the agent step through a paused process, one breakpoint at a time. Sensorium records the whole run once, and the agent queries it afterward, as often as it likes, with stable event ids.
- **LLM tracing** (LangSmith, Langfuse and similar) records the model's prompts and tool calls. Sensorium records the program under test: its calls, returns, exceptions and values.
- **Not sensorium-mcp.** [andriyshevchenko/sensorium-mcp](https://github.com/andriyshevchenko/sensorium-mcp) is an unrelated Telegram and memory agent that shares the name.

## Install

Python 3.12+. The CLI command is `sensorium`.

From git, which works today:

    uv venv .venv && uv pip install -p .venv/bin/python "sensorium-trace @ git+https://github.com/bricelancasterwcp-sudo/sensorium"

From PyPI, once published: `uv pip install sensorium-trace`.

Dev checkout: `uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"`.

The import package stays `sensorium`. The name `sensorium` on PyPI and npm is an unrelated project. The publish name is `sensorium-trace`. npm package of the same name is the TypeScript recorder; it does not replace the CLI. Details: [docs/install.md](docs/install.md).

The recorder is `sys.monitoring` and nothing else, so on 3.11 it refuses to start. Witnessing a `multiprocessing` spawn needs the `_posixsubprocess.fork_exec` audit event, which arrived in 3.14. Below that, such a spawn is unwitnessed, and `refocus` says so by withholding the "no child process witnessed" line ([docs/claims.md](docs/claims.md)).

## Commands

    sensorium run -- pytest tests/test_fog.py
    sensorium runs
    sensorium info last
    sensorium tree last --depth 3
    sensorium frame last --fn compute
    sensorium grep last compute --kind RETURN
    sensorium exceptions last
    sensorium failures last
    sensorium flow last --value 1800
    sensorium flow last --object build_key:record
    sensorium diff RUN_A RUN_B
    sensorium refocus last --focus fog:compute
    sensorium redact --all --dry-run
    sensorium mcp --allow-run

Per-line state is opt-in: `sensorium run --focus fog:compute -- ...`, then `sensorium watch last --at fog:compute --expr '...'`. Asked without that `--focus`, `watch` reports `NOTHING WAS CHECKED` and prints the re-record command. It does not report zero hits.

Traces land in `~/.sensorium/traces` (or `$SENSORIUM_DIR/traces`), one SQLite file per run. Rust, TypeScript, and C write to the same directory, so one `runs` lists all four. A run reference is a full id, a unique prefix, or `last`. Events are `eN` and frames are `fN`, and those ids stay stable, so an answer from one command is an argument to the next. `--fn` matches a qualname exactly first, then as a substring, and refuses when more than one name matches. Asyncio frames, `--window`, and `flow --object`: [docs/use.md](docs/use.md).

## Rust, TypeScript, and C

- **Rust.** `rust/` ships `sensorium-rt` 0.7.3, `sensorium-transform` 0.5.2, and `cargo-sensorium` 0.8.4. `cargo install --path rust/cargo-sensorium`, then `cargo sensorium test` or `cargo sensorium run` from a workspace. Linux, stable rustc. Panics show up in `failures`. [rust/README.md](rust/README.md). What it does not see: [rust/HONESTY.md](rust/HONESTY.md).
- **TypeScript.** `typescript/` ships `sensorium-ts` 0.6.2. A trace reports `recorder: sensorium-ts`. Node 24. From a checkout, `npm ci --prefix typescript`, then `sensorium ts run -- vitest run …` or `sensorium ts run -- node --test …`. Package scripts, jest, a project with no `typescript` of its own, and a vitest `projects` or `workspace` config are refused by name. [typescript/README.md](typescript/README.md).
- **C.** `sensorium c run -- <cmd>` records a Linux x86-64 debug build (`-O0` or `-Og`, gcc or clang). Crashes are what `exceptions` reads. [c/README.md](c/README.md).

Recording follows code under the working directory the run started in, so `sensorium run -- pytest ...` traces your tests and your code, and not pytest's. `--focus module:qualname` adds line-level capture for the named code. `--window QUALNAME` limits that capture to what runs inside one function. The `fog.py` examples in [docs/use.md](docs/use.md) were run as typed.

## Exit statuses

The exit status is the caller's next action, not a health code:

| exit | meaning | examples |
|---|---|---|
| 0 | the question was answered affirmatively. The trace says yes | `grep` found a match; `refocus` MATCH; `watch` SATISFIED |
| 1 | the question was answered negatively. The trace says no, or none | `grep` `matches: 0`; `exceptions` `no exceptions recorded`; `refocus` DIVERGED |
| 2 | the call is wrong, edit the command and ask again | an ambiguous `--fn`; `--nth` out of range; a run reference that resolves to nothing; `refocus` refusing before any rerun was attempted |
| 3 | the trace cannot settle it, change the recording and re-record | `watch` `NOTHING WAS CHECKED`; `refocus` REFUSED after a rerun; `exceptions`' uncaught-without-RAISE arm; `exceptions` on a Rust trace whose recorder predates err flow (`recorder sensorium-rt 0.2.0 declares it does not produce (capabilities.err_flow: false)`) |

`run` exits with the target's own status. It never applies this table to itself.

Every invocation is appended to `<trace root>/invocations.jsonl` (default `~/.sensorium/invocations.jsonl`, or under `$SENSORIUM_DIR`) as one JSON line with `utc`, `argv`, `exit` and `error` (the exception class name or null) and nothing else: never the environment, never the working directory. Set `SENSORIUM_NO_INVOCATION_LOG` to any non-empty value other than `0` to turn it off for one process, `=0` leaves logging on. The same branch is [docs/agent.md](docs/agent.md).

## For agents

Install, record one run, query it, serve it over MCP: ten steps in [docs/agent.md](docs/agent.md). After install, prove the path with `.venv/bin/python -m pytest tests/test_agent_smoke.py -q`.

## What the answers claim

Sensorium reports; the agent reading it reasons. Nothing in an answer is inferred from data the trace does not hold.

- `diff` compares the shape of two runs, `(file, qualname, kind)`, not their values. A pure move reads DIVERGED unless `--ignore-moves` can pair the name uniquely.
- `refocus` re-runs, then issues MATCH, DIVERGED, or REFUSED. The licence lists only the checks that ran. A check that could not run withholds the licence. Exit 2 means nothing was re-run.
- `tree` derives parentage from the caller frame, not from "the last frame on this thread".
- `exceptions` claims SWALLOWED only when the recording establishes it. Anything short of that is `ambiguous`, with the reason printed.
- `watch` never reads zero hits as "the invariant held". A site it could not evaluate is counted.
- `flow` is lineage over captured values, not static dataflow.
- `info` labels an INCOMPLETE recording and does not print a `0` as proof that nothing happened.

The full wording is [docs/claims.md](docs/claims.md). `exceptions`, `watch`, `flow`, and Rust `refocus` in detail are [docs/query.md](docs/query.md).

## What a trace holds, and what it does not see

A trace holds the process environment (minus what rule v1 withheld), stdout and stderr, the command line, source digests, and captured values. It does not see children by an unlisted mechanism, non-Python threads, files the program read, code outside the run root, the clock, or the network. Treat a trace as a core dump. [docs/visibility.md](docs/visibility.md). Redaction: [docs/redaction.md](docs/redaction.md).

## Overhead

Recording overhead and read-back cost are [docs/overhead.md](docs/overhead.md).
Measured with `python corpus/run_corpus.py --bench`.
The headline: 2.9× on the corpus's typical workloads, up to 194× on the call-dense one under `--focus`. Record failing tests, never benchmarks.

## Corpus

    python corpus/run_corpus.py                          # verify against seeded bugs
    python corpus/run_corpus.py --show                   # print the questions and commands
    python corpus/run_corpus.py --bench                  # report recording overhead
    python corpus/run_corpus.py --require-driver         # a skipped Rust or TypeScript case is exit 1
    python corpus/run_corpus.py --via mcp --compare-cli  # every tool question through the MCP server, diffed against the CLI

Small programs with planted bugs, and questions registered before any output was looked at. **115 cases and 253 questions.** A case whose recorder is not built is reported skipped by name. `--bench` reports; it never gates. Case by case: [docs/corpus.md](docs/corpus.md).

## Not yet

What each slice deferred, and the ruling each deferral is waiting on, is [docs/CARRIED-DEBT.md](docs/CARRIED-DEBT.md).

## License

MIT, see [LICENSE](LICENSE). Copyright © 2026 Brice Lancaster.

Versions after the Proprietary interlude are again under MIT (matching releases through 0.14.0).

## Also

- [docs/agent.md](docs/agent.md), [docs/mcp.md](docs/mcp.md), [docs/query.md](docs/query.md), [docs/TRACE-FORMAT.md](docs/TRACE-FORMAT.md)
- [docs/install.md](docs/install.md), [docs/changelog/README.md](docs/changelog/README.md), [docs/planning/README.md](docs/planning/README.md)
- [ORIGIN.md](ORIGIN.md)
