"""`sensorium ts` -- the TypeScript recorder's own subcommands.

One subcommand today. `ingest` turns a directory of spools into traces; the
driver that produces such a directory lands beside it as `ts run`, and both
register here so a reader of `sensorium ts --help` sees the whole surface in
one place.

Every word printed by this file is about test files, containers and the
harness that ran them. Nothing here borrows a word from another recorder's
machinery: a reader who meets `asyncio` or `cargo` in a TypeScript command's
help has been told about something that is not there.
"""
import sys

from sensorium import exit as ex
from sensorium import paths
from sensorium.ts import ingest, invocation


def add_parser(sub) -> None:
    p = sub.add_parser("ts", help="record and read a TypeScript test run",
                       description="Record a TypeScript or JavaScript test "
                                   "run; read back what actually ran.")
    ts = p.add_subparsers(dest="ts_cmd", required=True)
    _add_ingest_parser(ts)


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


def _report(summaries, invocation_id: str) -> int:
    """One line per spool, then the invocation and what it converted to.

    A refused spool takes the place of its own `run:` line rather than being
    collected at the end, so the order on screen is the order on disk and a
    reader can see which container is missing from the count.
    """
    for summary in summaries:
        print(summary.line())
    converted = [s for s in summaries if s.refused is None]
    print(f"invocation: {invocation_id}  traces: {len(converted)}")
    return ex.ANSWERED if len(converted) == len(summaries) else ex.BAD_CALL
