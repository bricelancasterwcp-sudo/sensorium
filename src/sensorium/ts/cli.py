"""`sensorium ts` -- the TypeScript recorder's own subcommands.

Two subcommands. `run` records a test run: it recognises the harness, wires
it, spawns the command as typed, waits, and converts what the run spooled.
`ingest` is the second half of that on its own, over a spool directory a run
already left behind -- deterministic and re-runnable, so a driver killed
between the harness's exit and the conversion leaves nothing that cannot be
finished by hand.

Every word printed by this file is about test files, containers and the
harness that ran them. Nothing here borrows a word from another recorder's
machinery: a reader who meets `asyncio` or `cargo` in a TypeScript command's
help has been told about something that is not there.
"""
import argparse
import sys

from sensorium import exit as ex
from sensorium import paths
from sensorium.ts import ingest, invocation


def add_parser(sub) -> None:
    p = sub.add_parser("ts", help="record and read a TypeScript test run",
                       description="Record a TypeScript or JavaScript test "
                                   "run under vitest or node --test; read "
                                   "back what actually ran.")
    ts = p.add_subparsers(dest="ts_cmd", required=True)
    _add_run_parser(ts)
    _add_ingest_parser(ts)


def _add_run_parser(sub) -> None:
    p = sub.add_parser(
        "run", help="record a test run under vitest or node --test",
        description="Record one test run. Give the harness command after "
                    "`--`, exactly as you would type it; the recorder wires "
                    "itself in and takes the wiring out again when the run "
                    "ends.",
        epilog="exit: the harness's own status, or 2 to fix the call")
    p.add_argument("--tier", choices=("off", "call"), default="call",
                   help="what the recorder emits: `call` records calls, "
                        "returns and awaits; `off` records nothing (the "
                        "control arm -- the same code still runs)")
    p.add_argument("--focus", action="append", default=[], metavar="SPEC",
                   help="a function to record per statement: <qualname> or "
                        "<file>:<qualname>, as tree prints it; repeatable")
    p.add_argument("--jobs", type=int, default=None, metavar="N",
                   help="how many spools to convert at once (default: one "
                        "per core)")
    p.add_argument("command", nargs=argparse.REMAINDER,
                   help="-- followed by the harness command: vitest run …, "
                        "npx vitest run …, node --test …")
    p.set_defaults(func=run_run)


def run_run(args) -> int:
    if args.jobs is not None and args.jobs < 1:
        print(f"--jobs must be >= 1 (got {args.jobs})", file=sys.stderr)
        return ex.BAD_CALL
    # Imported here and not above: the driver imports this module back for
    # its own reporting, and one of the two has to be the late one.
    from sensorium.ts import driver
    return driver.run(args)


def _add_ingest_parser(sub) -> None:
    p = sub.add_parser(
        "ingest", help="turn a recorded spool directory into traces",
        description="Convert every spool a recorded run left behind -- one "
                    "per container -- into one trace each.",
        epilog="exit: 0 every spool converted, 2 fix the call or the "
               "directory")
    p.add_argument("spool_dir",
                   help="the directory the run wrote its spools into")
    p.add_argument("--jobs", type=int, default=None, metavar="N",
                   help="how many spools to convert at once (default: one "
                        "per core)")
    p.set_defaults(func=run_ingest)


def run_ingest(args) -> int:
    if args.jobs is not None and args.jobs < 1:
        print(f"--jobs must be >= 1 (got {args.jobs})", file=sys.stderr)
        return ex.BAD_CALL
    try:
        summaries = ingest.ingest_dir(args.spool_dir, paths.trace_root(),
                                      jobs=args.jobs)
        # Read back rather than passed down: `ingest_dir` returns what
        # happened to the SPOOLS, and the invocation is a property of the
        # directory, not of any of them.
        invocation_id = invocation.read_invocation(args.spool_dir).invocation
    except (ingest.IngestError, invocation.InvocationError) as e:
        print(f"error: {e}", file=sys.stderr)
        return ex.BAD_CALL
    return _report(summaries, invocation_id)


def _report(summaries, invocation_id: str, harness: str | None = None) -> int:
    """One line per spool, then the invocation and what it converted to.

    A refused spool takes the place of its own `run:` line rather than being
    collected at the end, so the order on screen is the order on disk and a
    reader can see which container is missing from the count.

    `harness` is the ending the driver WITNESSED, and only a driver has one:
    an ingest of a directory read the same fact out of a file, which is a
    different claim, and the line does not make it.
    """
    for summary in summaries:
        print(summary.line())
    converted = [s for s in summaries if s.refused is None]
    tail = "" if harness is None else f"  harness exit: {harness}"
    print(f"invocation: {invocation_id}  traces: {len(converted)}{tail}")
    return ex.ANSWERED if len(converted) == len(summaries) else ex.BAD_CALL
