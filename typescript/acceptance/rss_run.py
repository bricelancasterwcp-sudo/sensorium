"""Run one command, pass its status through, and report its tree's peak RSS.

`e10p.sh` needs two things GNU `time -v` would give: the peak resident size
of the heaviest process in the command's tree, and the command's own exit
status unchanged. This box has no GNU `time`, and its `uutils` wrappers have
crashed under measurement before, so the wrapper on the measurement path is
six lines of the standard library instead of a coreutils clone (plan P10).

`resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` is the maximum resident set
of any ONE waited-for descendant, in kilobytes on Linux -- the largest
worker's peak, which is what spec 3.6 asks for, and NOT the sum across
workers. A converter that runs sixteen workers of 100 MB reports 100 MB
here, not 1.6 GB; the record quotes it as the largest worker's peak.

    rss_run.py -- <cmd> [args...]

Two lines of this wrapper's own go to stdout after whatever the child wrote:

    maxrss_kb=<kilobytes>
    child_wall=<seconds>

`child_wall` is this wrapper's clock around `subprocess.run` and nothing
else. It is printed so that the interpreter start-up this wrapper adds to
the caller's timed region is a number in the log rather than an assumption
that it is small -- the record still quotes the caller's wall, which is the
whole timed region. The exit status is the child's, so a child killed by a
signal exits non-zero here too (Python's own wrapping of a negative status),
which is all `e10p.sh` needs to drop that repetition by name.
"""
import resource
import subprocess
import sys
import time

USAGE = "usage: rss_run.py -- <cmd> [args...]\n"


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "--":
        sys.stderr.write(USAGE)
        return 2
    start = time.monotonic()
    proc = subprocess.run(argv[1:])
    wall = time.monotonic() - start
    sys.stdout.flush()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(f"maxrss_kb={usage.ru_maxrss}")
    print(f"child_wall={wall!r}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
