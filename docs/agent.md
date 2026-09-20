# Sensorium for agents

Record one run, then ask what it did. Answers come only from that trace;
when the trace cannot settle a question the tool refuses instead of
guessing. Full honesty: [README](../README.md). This page is the path.

Python 3.12+; install is from this repository (not PyPI). Use the
venv's `sensorium`, never a stale binary on `PATH`.

## Steps

1. Install into a venv from the repo root:

       uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"

2. Prefix every command with `.venv/bin/` (or `source .venv/bin/activate`).
   `record` via MCP spawns this same interpreter; a global `sensorium` will
   not import the program's dependencies.

3. Record an in-repo program from the repo root. Only code under `cwd`
   is traced:

       SENSORIUM_DIR=$PWD/.sensorium .venv/bin/sensorium run -- corpus/silent_swallow/main.py

4. Query the newest trace (`last`). Event ids `eN` and frame ids `fN` in
   one answer are arguments to the next:

       SENSORIUM_DIR=$PWD/.sensorium .venv/bin/sensorium exceptions last
       SENSORIUM_DIR=$PWD/.sensorium .venv/bin/sensorium tree last --depth 2
       SENSORIUM_DIR=$PWD/.sensorium .venv/bin/sensorium frame last --fn load_all

5. Branch on the process exit before rereading prose: **0** the trace
   said yes, **1** it said no or none, **2** fix the call, **3** change
   the recording and re-record. Never retry a 3 on the same run; never
   re-record on a 2.

6. Serve that store over MCP (stdio, no extra dependency):

       .venv/bin/sensorium mcp --allow-run --store $PWD/.sensorium

   `--allow-run` is what offers `record` and `refocus`. Without it those
   two are not tools. `--store` is `SENSORIUM_DIR` for the server and
   every child.

7. Register any MCP client with that absolute binary on stdio. The
   minimum args are `["mcp", "--allow-run"]`; add `--store` when the
   client should not inherit the launcher's `SENSORIUM_DIR`:

       {
         "command": "<venv>/bin/sensorium",
         "args": ["mcp", "--allow-run", "--store", "<repo>/.sensorium"]
       }

   Claude Code: `claude mcp add sensorium -- <venv>/bin/sensorium mcp --allow-run --store <repo>/.sensorium`.
   Start the server from an environment you are willing to record under:
   every call inherits it; there is no `env` field.

8. Through MCP, `record` takes `command` as an **argv array**, never a
   shell string and never `python` itself:
   `{"command": ["corpus/silent_swallow/main.py"], "cwd": "<repo>"}`.
   Query tools default `run` to `last`. `redact` is not a tool.

9. Every MCP result's first line is `exit N:` (or `no answer:`). `isError`
   is set on exit 2 or on no exit — repair the call. 1 and 3 are answers
   about the trace. Tools, the cap, the audit file: [mcp.md](mcp.md).

10. Prove the path after install:

        .venv/bin/python -m pytest tests/test_agent_smoke.py -q

    That records `corpus/silent_swallow/main.py` through the CLI and
    through MCP, asks `exceptions` both ways, and never writes
    `~/.sensorium`.
