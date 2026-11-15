"""sensorium command-line interface.

Every `main()` return is appended to the invocation log (see
`sensorium.invocations`) after dispatch, including the version guard
below and the three exception classes caught around `args.func(args)`.
The one shape this never sees is any argparse exit: a parse failure and
`--help`/`--version` alike raise `SystemExit` straight out of
`argparse.parse_args`, before dispatch, so both escape `main()` without
a record -- do not wrap it.
"""
import argparse
import sys

from sensorium import invocations, paths
from sensorium.mcp import cmd as mcp_cmd
from sensorium.query import (diff_cmd, exceptions_cmd, failures_cmd, flow_cmd,
                             fmt, frame_cmd, grep_cmd, info_cmd, redact_cmd,
                             refocus_cmd, runs_cmd, tree_cmd, watch_cmd)
from sensorium.store import db
from sensorium.store.gc import add_parsers as add_gc_parsers
from sensorium.c import cli as c_cli
from sensorium.ts import cli as ts_cli

_QUERY_MODULES = [runs_cmd, info_cmd, tree_cmd, frame_cmd, grep_cmd,
                  exceptions_cmd, failures_cmd, flow_cmd, watch_cmd, diff_cmd,
                  refocus_cmd, redact_cmd]


def _add_run_parser(sub):
    p = sub.add_parser(
        "run", help="record one execution",
        description="Runs the command under the recorder from `cwd` and "
                    "writes one trace; only code under `cwd` is recorded; "
                    "the command is a .py file, a `-m` module or a console "
                    "script, never `python` itself.",
        epilog="exit: the target's own status")
    p.add_argument("--focus", action="append", default=[],
                   help="pkg.module or pkg.module:qualname; repeatable")
    p.add_argument("--include", action="append", default=[],
                   help="glob matched against each file's path relative "
                        "to the working directory; when given, only the "
                        "files it matches are recorded; repeatable")
    p.add_argument("--exclude", action="append", default=[],
                   help="glob matched against each file's path relative "
                        "to the working directory; a file it matches is "
                        "never recorded; repeatable")
    p.add_argument("--window", default=None,
                   help="limit --focus line capture to what runs inside this "
                        "function's activations; MODULE:QUALNAME scopes to one "
                        "function, a bare QUALNAME matches that name in any "
                        "module")
    p.add_argument("--max-events", default=None,
                   help="stop storing events after this many (0 is unlimited)")
    p.add_argument("--max-bytes", default=None,
                   help="stop storing events after the trace reaches this "
                        "size, for example 8M (0 is unlimited)")
    p.add_argument("--max-calls", default=None,
                   help="store at most this many calls of each function; "
                        "later calls are counted and marked elided "
                        "(0 is unlimited)")
    p.add_argument("--no-cap", action="store_true",
                   help="record without an event, size, or per-function cap")
    p.add_argument("--run-id", default=None, help=argparse.SUPPRESS)
    p.add_argument("--refocus-of", default=None, help=argparse.SUPPRESS)
    p.add_argument("target", nargs=argparse.REMAINDER)
    p.set_defaults(func=_run)


def _run(args) -> int:
    from sensorium.record import boot
    target = list(args.target)
    if target and target[0] == "--":
        target = target[1:]
    if not target:
        print("usage: sensorium run [options] -- <command> [args...]",
              file=sys.stderr)
        return 2
    from sensorium.limits import LimitsError, resolve
    try:
        limits = resolve(max_events=args.max_events, max_bytes=args.max_bytes,
                         max_calls=args.max_calls, no_cap=args.no_cap)
    except LimitsError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    try:
        run_id, exit_status = boot.run_target(
            target, focus=args.focus, include=args.include,
            exclude=args.exclude, window=args.window,
            run_id=args.run_id, refocus_of=args.refocus_of, limits=limits)
    except boot.TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"run: {run_id}")
    print(f"trace: {paths.traces_dir() / (run_id + '.db')}")
    return exit_status


def main(argv=None) -> int:
    # The argv the invocation log records: what this call received, never
    # the environment or the working directory.
    recorded_argv = list(argv) if argv is not None else list(sys.argv[1:])
    if sys.version_info < (3, 12):
        print("sensorium requires Python 3.12+ (sys.monitoring); running "
              f"under {sys.version.split()[0]}", file=sys.stderr)
        invocations.record(recorded_argv, 2, None)
        return 2
    parser = argparse.ArgumentParser(
        prog="sensorium",
        description="Record a program's execution; query what actually "
                    "happened. `sensorium run` records Python, `cargo "
                    "sensorium` records Rust, `sensorium ts run` records "
                    "TypeScript and `sensorium c run` records C; every "
                    "query below reads any of the four traces.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_run_parser(sub)
    ts_cli.add_parser(sub)
    c_cli.add_parser(sub)
    mcp_cmd.add_parser(sub)
    add_gc_parsers(sub)
    for mod in _QUERY_MODULES:
        mod.add_parser(sub)
    args = parser.parse_args(argv)
    error = None
    try:
        exit_status = args.func(args)
    except (paths.TraceLookupError, fmt.RefError, db.TraceFormatError) as e:
        # "the reference you gave does not name anything", or "this trace is
        # from a newer sensorium" -- user-facing conditions every query command
        # can hit, and never a reason to hand back a traceback.
        print(f"error: {e}", file=sys.stderr)
        exit_status = 2
        error = type(e).__name__
    invocations.record(recorded_argv, exit_status, error)
    return exit_status
