"""sensorium command-line interface."""
import argparse
import sys

from sensorium import paths
from sensorium.query import (exceptions_cmd, flow_cmd, frame_cmd, grep_cmd,
                             info_cmd, runs_cmd, tree_cmd)

_QUERY_MODULES = [runs_cmd, info_cmd, tree_cmd, frame_cmd, grep_cmd,
                  exceptions_cmd, flow_cmd]


def _add_run_parser(sub):
    p = sub.add_parser("run", help="record one execution")
    p.add_argument("--focus", action="append", default=[],
                   help="pkg.module or pkg.module:qualname; repeatable")
    p.add_argument("--include", action="append", default=[])
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--window", default=None)
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
    try:
        run_id, exit_status = boot.run_target(
            target, focus=args.focus, include=args.include,
            exclude=args.exclude, window=args.window,
            run_id=args.run_id, refocus_of=args.refocus_of)
    except boot.TargetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"run: {run_id}")
    print(f"trace: {paths.traces_dir() / (run_id + '.db')}")
    return exit_status


def main(argv=None) -> int:
    if sys.version_info < (3, 12):
        print("sensorium requires Python 3.12+ (sys.monitoring); running "
              f"under {sys.version.split()[0]}", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(
        prog="sensorium",
        description="Record a Python program's execution; "
                    "query what actually happened.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_run_parser(sub)
    for mod in _QUERY_MODULES:
        mod.add_parser(sub)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except paths.TraceLookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
