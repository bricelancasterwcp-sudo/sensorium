"""`sensorium mcp`: the subcommand that starts the server.

Thin on purpose: the words the CLI prints about this server (P19), the
policy flags' validation, and the one variable the whole process tree
reads (P9). What the server DOES is `server.py`'s.

WHY THE IMPORTS ARE INSIDE `run` (D31). `mcp.tools` imports
`sensorium.cli` -- it reads `sensorium run`'s own parser to build
`record`'s schema (D7) -- and `cli` imports this module to register the
subcommand: at module level that is a cycle, inside the function it is
three imports that happen after both modules exist. It is also why
`mcp` is registered beside `ts` and not in `cli._QUERY_MODULES`, which
is walked at import time.

WHY A REFUSAL IS EXIT 2 AND ONE LINE. The caller is a launcher in an
MCP client's configuration, and what a launcher shows the user is
whatever the process said before it died. A cap of ten bytes would
answer every question with a truncation marker and a timeout of zero
would kill every call before it spawned: both are refusals to START, in
a CLI's words rather than JSON-RPC's -- there is no client yet. The
table is built here for the same reason: a command that has lost the
help text a tool description is made of must refuse before a thread
exists. `server.main` is then handed that one table.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: The three strings `sensorium --help` and `sensorium mcp --help`
#: print (P19). The description says what the surface IS: a reader who
#: has never seen MCP needs its shape in one sentence.
HELP = "serve the store to a model over the Model Context Protocol on stdio"
DESCRIPTION = ("One JSON-RPC message per line on stdin/stdout; every query "
               "command is a tool, and record and refocus are tools only "
               "under --allow-run. Diagnostics go to stderr.")
EPILOG = "exit: 0 at EOF or SIGTERM, 2 a refusal to start"

#: Below this a cap cannot hold a head, a tail and the marker between
#: them, so the answer would be all marker (see `result.cap`).
MIN_OUTPUT = 4096
DEFAULT_OUTPUT = 65536
DEFAULT_TIMEOUT = 60.0
DEFAULT_RUN_TIMEOUT = 600.0


def add_parser(sub) -> None:
    p = sub.add_parser("mcp", help=HELP, description=DESCRIPTION,
                       epilog=EPILOG)
    p.add_argument("--allow-run", action="store_true",
                   help="offer record and refocus, the two tools that "
                        "execute the recorded program; default off")
    p.add_argument("--store", default=None, metavar="DIR",
                   help="the trace store to serve, as SENSORIUM_DIR for "
                   "this server and every call it makes; default the "
                   "inherited store")
    p.add_argument("--max-output", type=int, default=DEFAULT_OUTPUT,
                   metavar="BYTES", help="cap one answer's body at this "
                   "many bytes, head and tail kept with a marker naming "
                   f"what was cut; minimum {MIN_OUTPUT}")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                   metavar="SECONDS", help="how long one query tool may "
                   "take before its process group is killed and the call "
                   "is answered no answer")
    p.add_argument("--run-timeout", type=float, default=DEFAULT_RUN_TIMEOUT,
                   metavar="SECONDS", help="the same bound for the two "
                   "tools that execute the recorded program, which are "
                   "expected to take longer")
    p.set_defaults(func=run)


def _refuse(what: str) -> int:
    print(f"sensorium mcp: {what}", file=sys.stderr)
    return 2


def run(args) -> int:
    from sensorium.mcp import schema, server, tools    # D31: the cycle
    if args.max_output < MIN_OUTPUT:
        return _refuse(f"--max-output {args.max_output} is below the "
                       f"{MIN_OUTPUT}-byte minimum")
    for flag, seconds in (("--timeout", args.timeout),
                          ("--run-timeout", args.run_timeout)):
        if seconds <= 0:
            return _refuse(f"{flag} {seconds:g} is not a positive "
                           "number of seconds")
    if args.store is not None:
        # P9, D16: one variable, set before the table is built and any
        # child is spawned -- `paths.trace_root` reads it on every call
        # and the children inherit it.
        os.environ["SENSORIUM_DIR"] = str(Path(args.store).resolve())
    try:
        table = tools.table(args.allow_run)
    except schema.SchemaError as blank:
        return _refuse(str(blank))
    return server.main(server.Options(
        allow_run=args.allow_run, store=args.store,
        max_output=args.max_output, timeout=args.timeout,
        run_timeout=args.run_timeout), table)
