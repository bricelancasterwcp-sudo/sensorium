"""The programs the child tests write into `tmp_path` and record.

`child.py` is a process layer, so what it has to prove is about
processes: that a target which sleeps is killed rather than waited for,
that a grandchild it spawned dies with it, that SIGTERM is tried before
SIGKILL, that a descendant deaf to SIGTERM still lets `run` return.
None of that can be asserted against a program that merely computes a
value, so every shape here is a real program the recorder runs.

Two rules hold for all of them.

Every sleeper writes its pid files BEFORE it sleeps, and the tests wait
for the file rather than for a duration: a test that cancelled on a
timer would half the time be asserting about an interpreter still
booting, and the kill it measured would be the kill of a process that
had not yet reached the sleep.

`sensorium run` records the target IN the recorder's own process, so a
sleeper's own pid is also the child's pid and the process group's
leader -- a test can read that one from `Outcome.pgid`. The grandchild's
pid is the one nothing but the program itself can tell a test, which is
why the shapes that spawn one write it down.
"""
from pathlib import Path

#: A target that only sleeps. Used where the test needs a child that
#: will not end on its own and has nothing else to say.
SLEEPER = """
import os, time
from pathlib import Path

Path("child.pid").write_text(str(os.getpid()))
time.sleep(30)
"""

#: ...and the same with a grandchild the kill must reach. `sleep` dies
#: on SIGTERM like the leader, so this shape asks only whether the
#: signal went to the GROUP -- a leader-only kill leaves `sleep 30`
#: running and the test's `os.kill(pid, 0)` still answers.
SLEEPER_WITH_GRANDCHILD = """
import os, subprocess, time
from pathlib import Path

kid = subprocess.Popen(["sleep", "30"])
Path("grandchild.pid").write_text(str(kid.pid))
Path("child.pid").write_text(str(os.getpid()))
time.sleep(30)
"""

#: A sleeper that HANDLES SIGTERM: it leaves a word behind and exits 0.
#: The word is the only evidence that the kill sequence tried SIGTERM at
#: all -- a straight SIGKILL leaves the file unwritten, because SIGKILL
#: cannot be handled.
TRAPS_SIGTERM = """
import os, signal, sys, time
from pathlib import Path

def _term(signum, frame):
    Path("term.txt").write_text("term")
    sys.exit(0)

signal.signal(signal.SIGTERM, _term)
Path("child.pid").write_text(str(os.getpid()))
time.sleep(30)
"""

#: A sleeper that IGNORES SIGTERM, so only the unconditional SIGKILL
#: ends it. Written for the server's EOF-grace test (Task 5), and kept
#: here so every sleeper shape lives in one module.
IGNORES_SIGTERM = """
import os, signal, time
from pathlib import Path

signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path("child.pid").write_text(str(os.getpid()))
time.sleep(30)
"""

#: The hard shape: the LEADER exits 0 on SIGTERM and its grandchild
#: ignores the signal, holding the inherited stdout and stderr pipes
#: open. A kill sequence that sends SIGKILL only while the leader is
#: alive never sends it at all here, and the read of those pipes hangs
#: until `communicate`'s own timeout.
#:
#: The grandchild writes its OWN pid file, after installing SIG_IGN: a
#: pid written by the parent right after `Popen` would let a test cancel
#: during the window in which the grandchild still dies on SIGTERM like
#: anything else, and the shape under test would evaporate.
GRANDCHILD_IGNORES_SIGTERM = """
import os, signal, subprocess, sys, time
from pathlib import Path

DEAF = ("import os, signal, sys, time;"
        "from pathlib import Path;"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN);"
        "Path(sys.argv[1]).write_text(str(os.getpid()));"
        "time.sleep(30)")

def _term(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, _term)
subprocess.Popen([sys.executable, "-c", DEAF, "grandchild.pid"])
Path("child.pid").write_text(str(os.getpid()))
time.sleep(30)
"""

#: The line `TALKING_SLEEPER` prints before it sleeps.
SAID = "the child said this before it slept"

#: A sleeper that SPEAKS FIRST. Everything it says is written and
#: flushed before the pid file exists, so by the time a test cancels the
#: bytes are in the pipe waiting to be read -- and whether the outcome
#: still carries them is the whole question about who reads the pipes
#: (R9: a cancel that reaped could take them into a buffer nobody reads,
#: or split them with the worker).
TALKING_SLEEPER = f"""
import os, sys, time
from pathlib import Path

print({SAID!r})
sys.stdout.flush()
Path("child.pid").write_text(str(os.getpid()))
time.sleep(30)
"""

#: Says what the child's stdin held. `''` is the whole assertion.
READER = """
import sys

print(repr(sys.stdin.read()))
"""

#: Says where the child ran and which store it was pointed at.
PWD = """
import os

print("cwd=" + os.getcwd())
print("store=" + str(os.environ.get("SENSORIUM_DIR")))
"""

#: The stdin test's driver, which is the test itself moved into a
#: process whose stdin provably holds something: `subprocess.run` writes
#: "not empty" into THIS program's stdin and never reads it, so a child
#: that inherited stdin would read the client's bytes. Run from the
#: directory it is passed; prints what the child said.
STDIN_DRIVER = """
import os, sys
from pathlib import Path

from sensorium.mcp.child import Child

root = Path(sys.argv[1])
env = dict(os.environ, SENSORIUM_DIR=str(root / "sdir"))
outcome = Child(["run", "--", "reader.py"], str(root), None, env, 60).run()
sys.stdout.write("exit=%r\\n" % (outcome.exit,))
sys.stdout.write(outcome.stdout)
sys.stdout.write(outcome.stderr)
"""


def write(tmp_path, name: str, source: str) -> Path:
    """Write one program into `tmp_path`, and hand back its path.

    The leading newline every constant above opens with is stripped, so
    a traceback out of a recorded program names the line the source
    reads on.
    """
    path = Path(tmp_path) / name
    path.write_text(source.lstrip("\n"))
    return path
