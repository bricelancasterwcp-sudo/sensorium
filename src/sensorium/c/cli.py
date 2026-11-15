"""`sensorium c` -- record a C program or a C build.

One subcommand. `run` puts compiler shims on `PATH`, spawns the command
after `--`, and converts whatever that command spooled. The exit status
is the command's own, including `128 + n` when a signal ended it, because
a recorder whose status meant something else could not stand in front of
an existing build.
"""
from __future__ import annotations

import argparse


def add_parser(sub) -> None:
    p = sub.add_parser(
        "c",
        help="record a C program or a C build",
        description="Record a C program or a build (make, cmake, meson, or "
                    "a plain gcc/clang command) on Linux x86-64. Debug "
                    "builds (-O0 or -Og) are the ones whose arguments and "
                    "return values can be read back. The command's own "
                    "status is the exit status.")
    commands = p.add_subparsers(dest="c_cmd", required=True)
    _add_run_parser(commands)


def _add_run_parser(sub) -> None:
    p = sub.add_parser(
        "run",
        help="record a C program or a build",
        description="Record a C program or a build (make, cmake, meson, or "
                    "a plain gcc/clang command) on Linux x86-64. Debug "
                    "builds (-O0 or -Og) keep argument and return values; "
                    "other optimization levels still record calls. The "
                    "command after -- runs as typed. The command's own "
                    "status is the exit status. When the command dies on a "
                    "signal, that status is 128 plus the signal number, the "
                    "same one a shell reports.",
        epilog="exit: the command's own status, or 2 to fix the call")
    p.add_argument(
        "--strict", action="store_true",
        help="refuse to compile a translation unit whose effective -O is "
             "not -O0 or -Og")
    p.add_argument(
        "--no-retval", action="store_true",
        help="do not install the return trampoline "
             "(env SENSORIUM_C_NO_RETVAL=1)")
    p.add_argument(
        "command", nargs=argparse.REMAINDER,
        help="-- followed by the command to record: make, cmake, meson, "
             "or a plain gcc/clang command")
    p.set_defaults(func=run_run)


def run_run(args) -> int:
    # Imported here: the driver does not import this module, but keeping
    # the import late matches the other recorder and leaves `c --help`
    # free of the compiler wrapper.
    from sensorium.c import driver
    return driver.run(args)
