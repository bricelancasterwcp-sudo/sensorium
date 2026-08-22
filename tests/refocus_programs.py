"""Program shapes and recording fixtures shared by the two `refocus` files.

Split out for the same reason as `programs.py`: each source string is one
program *shape*, and the shapes that matter to `refocus` are whole-program
properties -- whether control flow depends on state outside the process,
whether a worker thread can take a branch the main thread cannot see,
whether the recorder's own capture perturbs the program. None of them can be
expressed in a fragment.

`test_refocus.py` covers running, refusing, and the verdict;
`test_refocus_licence.py` covers what the verdict is allowed to claim.
"""
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from sensorium.store import db
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script, run_cli

# Deterministic. `accumulate`'s loop calls nothing, so editing its input list
# changes the printed value but NOT the causal stream -- which is exactly the
# shape the changed-source tests need.
LOOP = """
def helper(n):
    return n + 1

def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    print("sum:", accumulate([5, 10, 20]), helper(1))

if __name__ == "__main__":
    main()
"""

# Control flow decided by state OUTSIDE the process, so the rerun genuinely
# takes the other branch -- and does so deterministically, unlike a coin
# flip, which would make a DIVERGED test flaky in the direction of a false
# pass.
COUNTER = """
import pathlib

def bump():
    p = pathlib.Path("counter.txt")
    n = int(p.read_text()) if p.exists() else 0
    p.write_text(str(n + 1))
    return n

def first():
    return "first"

def again():
    return "again"

def main():
    print(first() if bump() == 0 else again())

if __name__ == "__main__":
    main()
"""

# Same causal shape both times; only the value that decides the exit status
# differs. A MATCH here is correct and yet the two runs ended differently.
EXIT_FROM_FILE = """
import pathlib
import sys

def attempt():
    p = pathlib.Path("n.txt")
    n = int(p.read_text()) if p.exists() else 0
    p.write_text(str(n + 1))
    return n

def main():
    sys.exit(attempt())

if __name__ == "__main__":
    main()
"""

READS_STDIN = """
def main():
    line = input()
    print("got", line)

if __name__ == "__main__":
    main()
"""

# Writes a marker, then blocks: lets a test kill the recorder at a known
# point and get a genuinely incomplete trace.
SLEEPER = """
import pathlib
import time

def spin():
    time.sleep(60)

def main():
    pathlib.Path("ready").write_text("1")
    spin()

if __name__ == "__main__":
    main()
"""

TWO_FILES = """
import lib

def main():
    print("n:", lib.compute(3))

if __name__ == "__main__":
    main()
"""

LIB = """
def helper(x):
    return x * 2

def compute(x):
    return helper(x) + 1
"""

# -- the three false MATCHes, as fixtures -----------------------------------
# Each one produced "verdict: MATCH" plus the full licence sentence before
# the licence was gated on every signal rather than on the source tree alone.

# 1. Input arrives through the environment. The comprehension is inlined
# (PEP 709), so the causal shape is genuinely identical either way -- MATCH
# is the right verdict about SHAPE and a lie about the run.
ENV_LIMIT = """
import os

def over(items, limit):
    return [x for x in items if x > limit]

def main():
    limit = int(os.environ.get("REFOCUS_TEST_LIMIT", "5"))
    print("over:", len(over([3, 7, 12], limit)))

if __name__ == "__main__":
    main()
"""

# 2. Only a WORKER thread takes the other branch. The main thread -- the one
# `compare()` looks at -- is byte-identical across the two runs.
THREAD_BRANCH = """
import pathlib
import threading

def choose():
    p = pathlib.Path("turn.txt")
    n = int(p.read_text()) if p.exists() else 0
    p.write_text(str(n + 1))
    return n

def alpha():
    return "A"

def beta():
    return "B"

def work(out):
    out.append(alpha() if choose() == 0 else beta())

def main():
    out = []
    t = threading.Thread(target=work, args=(out,))
    t.start()
    t.join()
    print(out)

if __name__ == "__main__":
    main()
"""

# 3. The instrument perturbs the program. `marker` is a local, never an
# argument, so the original (no focus) never captures it and never calls its
# __repr__; the refocused rerun captures every local on every LINE event and
# calls it repeatedly. Those calls run with `tls.in_hook` set, so the frames
# they create are suppressed from the trace -- the fingerprint is blind to
# the recorder's own footprint BY CONSTRUCTION and can never report this.
SIDE_EFFECT_REPR = """
COUNT = [0]

class Noisy:
    def __repr__(self):
        COUNT[0] += 1
        return "noisy"

def step():
    marker = Noisy()
    total = 0
    for i in range(4):
        total = total + i
    return total

def main():
    step()
    print("reprs:", COUNT[0])

if __name__ == "__main__":
    main()
"""

# Two threads doing identical, deterministic work: every per-thread
# fingerprint matches, so the verdict is a genuine MATCH -- and the
# INTERLEAVING between them was still never compared.
TWO_WORKERS = """
import threading

def tally(n):
    total = 0
    for i in range(n):
        total = total + i
    return total

def work():
    tally(3)

def main():
    ts = [threading.Thread(target=work) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print("joined")

if __name__ == "__main__":
    main()
"""

# The same worker shape, run a different NUMBER of times. Both runs record
# the same SET of per-thread fingerprints; only the counts differ, which is
# why the comparison has to be a multiset.
THREAD_COUNT = """
import pathlib
import threading

def how_many():
    p = pathlib.Path("n.txt")
    n = int(p.read_text()) if p.exists() else 0
    p.write_text(str(n + 1))
    return 2 + n

def tally():
    return 1

def work():
    tally()

def main():
    ts = [threading.Thread(target=work) for _ in range(how_many())]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print("joined")

if __name__ == "__main__":
    main()
"""

# A subprocess is observed by the audit hook and never witnessed: whatever
# it did is outside every trace either run holds.
SPAWNS = """
import subprocess
import sys

def spawn():
    subprocess.run([sys.executable, "-c", "pass"])

def main():
    spawn()
    print("done")

if __name__ == "__main__":
    main()
"""

# `os.system` starts a shell without ever touching `subprocess`, so a hook
# that watches only `subprocess.Popen` records `children == []` for it.
SHELLS_OUT = """
import os

def shell():
    os.system("exit 0")

def main():
    shell()
    print("done")

if __name__ == "__main__":
    main()
"""

# Reached as `../tool.py` from a cwd it does not live under, this traces
# NOTHING: `_classify` only traces files below the run's root. Two runs that
# take visibly different branches then produce two empty causal streams,
# which compare equal.
OUTSIDE_ROOT = """
import pathlib

def main():
    p = pathlib.Path("marker.txt")
    if p.exists():
        print("SECOND-RUN")
    else:
        p.write_text("1")
        print("FIRST-RUN")

if __name__ == "__main__":
    main()
"""

# A worker whose body is entirely stdlib produces NO fingerprint row, so
# counting fingerprints reports a single-threaded run while a second thread
# is still doing file I/O.
UNTRACED_WORKER = """
import threading
import time

def start():
    t = threading.Thread(target=time.sleep, args=(30,), daemon=True,
                         name="untraced-worker")
    t.start()
    return t

def main():
    start()
    print("main done")

if __name__ == "__main__":
    main()
"""


# -- fixtures ---------------------------------------------------------------

def rec(tmp_path, src, extra=(), stdin_text=None):
    run_id, _trace, r = record_script(tmp_path, src, extra=extra,
                                      stdin_text=stdin_text)
    assert run_id, r.stderr + r.stdout
    return run_id, tmp_path / "sdir"


def rec_in_git(tmp_path, src, uncommitted=None):
    """Record inside a real git repo with `prog.py` committed.

    `uncommitted` rewrites the file after the commit, so the recording is
    made while the file is ALREADY dirty. That is the state in which
    `git_dirty_hash` -- a hash of the porcelain path list -- stops being
    able to notice any further edit at all.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "prog.py").write_text(src)
    for cmd in (["init", "-q", "-b", "main"],
                ["add", "prog.py"],
                ["-c", "user.email=t@example.invalid", "-c", "user.name=t",
                 "-c", "commit.gpgsign=false", "commit", "-q", "-m", "p"]):
        subprocess.run(["git", *cmd], cwd=tmp_path, check=True,
                       capture_output=True)
    if uncommitted is not None:
        (tmp_path / "prog.py").write_text(uncommitted)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", "--", "prog.py"], cwd=tmp_path, sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr
    run_id = re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)
    assert Trace.open(sdir / "traces" / f"{run_id}.db").meta["git_sha"]
    return run_id, sdir


def record_killed(tmp_path, src):
    """A genuinely incomplete recording: SIGKILL the recorder mid-run."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "prog.py").write_text(src)
    sdir = tmp_path / "sdir"
    proc = subprocess.Popen(
        [sys.executable, "-m", "sensorium", "run", "--", "prog.py"],
        cwd=tmp_path, env=dict(os.environ, SENSORIUM_DIR=str(sdir)),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = tmp_path / "ready"
    deadline = time.monotonic() + 60
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert ready.exists(), "the recorded program never reached its marker"
    proc.kill()
    proc.wait(timeout=60)
    return sdir


def refocus(sdir, run_id, *extra, cwd=None, sensorium_dir=None):
    return run_cli(["refocus", run_id, *extra], cwd=cwd or sdir.parent,
                   sensorium_dir=sensorium_dir or sdir)


def new_run(out):
    m = re.search(r"^run: (\S+)$", out, re.M)
    assert m, f"no new run id in output:\n{out}"
    return m.group(1)


def trace(sdir, run_id):
    return Trace.open(sdir / "traces" / f"{run_id}.db")


def dbs(sdir):
    return sorted(p.name for p in (sdir / "traces").glob("*.db"))


def recorded_output(sdir, run_id):
    return "".join(d for _e, _s, d in trace(sdir, run_id).output_chunks())


def set_meta(path, **kv):
    conn = db.open_trace(path)
    for k, v in kv.items():
        db.set_meta(conn, k, v)
    conn.commit()
    conn.close()


def drop_meta(path, *keys):
    """Remove metadata keys from a real recording, to make it look like a
    trace from before that key existed. `db` has no delete -- legacy shapes
    are read-only history everywhere else in the codebase."""
    conn = db.open_trace(path)
    for key in keys:
        conn.execute("DELETE FROM meta WHERE key = ?", (key,))
    conn.commit()
    conn.close()


def synthetic(sdir, run_id, *, argv=("prog.py",), cwd=None, late_writes=0,
              main_thread_ident=1, fingerprint="aaaabbbbccccdddd", tasks=()):
    """A hand-built trace, for shapes the recorder cannot produce on demand:
    dropped late writes, a legacy trace with no recorded main thread, a
    trace with no per-thread fingerprint at all, and corrupt metadata that
    must be refused rather than crashed on.

    `fingerprint=None` omits the fingerprint row. Both sides of a comparison
    must use the same digest, or the whole-thread check will report them as
    diverged for a reason the test did not intend.

    `tasks` is a list of `(task_id, name, thread_id)` rows. No
    `fingerprint_basis` is written, so a trace built with tasks here is
    exactly the shape an older recorder left behind: tasks ran, and the
    thread fingerprint covers their events.
    """
    path = Path(sdir) / "traces" / f"{run_id}.db"
    w = TraceWriter(path)
    w.set_meta("run_id", run_id)
    if argv is not None:
        w.set_meta("argv", list(argv))
    if cwd is not None:
        w.set_meta("cwd", str(cwd))
    w.set_meta("incomplete", False)
    w.set_meta("late_writes", late_writes)
    w.set_meta("live_threads", [])
    w.set_meta("threads_started", 0)
    w.set_meta("audit_errors", 0)
    w.set_meta("spawn_syscalls", 0)
    if main_thread_ident is not None:
        w.set_meta("main_thread_ident", main_thread_ident)
    c = w.intern_code("/tmp/prog.py", "main", 1)
    w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    for task_id, name, thread_id in tasks:
        w.add_task(task_id, name, thread_id)
    if fingerprint is not None:
        w.write_fingerprint(1, fingerprint, 1)
    w.close()
    return path


# The worker that beat the `live_threads` check: its body is entirely stdlib
# (so no fingerprint row) AND it is joined before the run ends (so it is gone
# from live_threads too). It is doing real, differing file I/O the whole
# time. Only counting thread CREATION sees it.
JOINED_UNTRACED_WORKER = """
import pathlib
import shutil
import threading

def deliver():
    t = threading.Thread(target=shutil.copyfile,
                         args=("payload.txt", "delivered.txt"))
    t.start()
    t.join()

def main():
    deliver()
    print("delivered", pathlib.Path("delivered.txt").stat().st_size > 0)

if __name__ == "__main__":
    main()
"""


# Path six: `multiprocessing` with spawn/forkserver reaches the OS through
# `_posixsubprocess.fork_exec`, which `subprocess.Popen` also nests -- so it
# cannot join `children` without double-counting, and is counted separately.
MULTIPROCESSING_CHILD = """
import multiprocessing as mp
import pathlib

def copy_payload(src, dst):
    pathlib.Path(dst).write_text(pathlib.Path(src).read_text())

def deliver():
    ctx = mp.get_context("spawn")
    p = ctx.Process(target=copy_payload, args=("payload.txt", "delivered.txt"))
    p.start()
    p.join()

def main():
    deliver()
    print("child done")

if __name__ == "__main__":
    main()
"""

# Path seven: COLUMNS was on the volatile denylist, so a program that sizes
# its output by terminal width wrote 80 bytes in one run and 9000 in the
# other under a full licence.
READS_COLUMNS = """
import os

def width():
    return int(os.environ.get("COLUMNS", "80"))

def main():
    with open("out.txt", "w") as fh:
        fh.write("x" * width())
    print("wrote", width())

if __name__ == "__main__":
    main()
"""

# A worker started ONLY on the rerun: the two sides are asymmetric, which is
# what separates max() from min() when counting threads that left no
# fingerprint.
WORKER_ON_SECOND_RUN = """
import pathlib
import shutil
import threading

def maybe_worker():
    p = pathlib.Path("seen.txt")
    if p.exists():
        t = threading.Thread(target=shutil.copyfile,
                             args=("seen.txt", "copy.txt"))
        t.start()
        t.join()
    else:
        p.write_text("1")

def main():
    maybe_worker()
    print("done")

if __name__ == "__main__":
    main()
"""


# -- asyncio: what a task compares by, and what it does not -----------------

# Two named tasks whose START ORDER flips between the original and the
# rerun (a counter file decides, as in COUNTER), while each task does
# identical work. Refocus must say MATCH: tasks are compared by content,
# never by the order they interleaved in.
ASYNC_ORDER_FLIP = """
import asyncio
from pathlib import Path
COUNTER = Path("run_count.txt")

def step(n):
    return n

async def worker(name):
    step(1)
    await asyncio.sleep(0)
    step(2)

async def amain(order):
    names = ["A", "B"] if order else ["B", "A"]
    await asyncio.gather(*[asyncio.create_task(worker(n), name=f"task-{n}")
                           for n in names])

def main():
    n = int(COUNTER.read_text()) if COUNTER.exists() else 0
    COUNTER.write_text(str(n + 1))
    asyncio.run(amain(n % 2 == 0))

if __name__ == "__main__":
    main()
"""

# Same, but task-B takes another branch on the rerun -- and the start order
# is held fixed, so the only difference between the two runs is one task's
# CONTENT: DIVERGED, naming task-B and the first differing step.
ASYNC_CONTENT_FLIP = ASYNC_ORDER_FLIP.replace(
    "async def worker(name):\n    step(1)\n    await asyncio.sleep(0)\n"
    "    step(2)",
    "def other(n):\n    return -n\n\nasync def worker(name):\n    step(1)\n"
    "    await asyncio.sleep(0)\n    if name == 'B' and not FIRST[0]:\n"
    "        other(2)\n    else:\n        step(2)").replace(
    "COUNTER = Path(\"run_count.txt\")",
    "COUNTER = Path(\"run_count.txt\")\nFIRST = [True]").replace(
    "    asyncio.run(amain(n % 2 == 0))",
    "    FIRST[0] = n % 2 == 0\n    asyncio.run(amain(True))")

# The rerun spawns a third worker: DIVERGED with a task stream that has no
# counterpart on the original side at all.
ASYNC_COUNT_FLIP = ASYNC_ORDER_FLIP.replace(
    "    names = [\"A\", \"B\"] if order else [\"B\", \"A\"]",
    "    names = [\"A\", \"B\"] if order else [\"A\", \"B\", \"C\"]")

# A thread that ran traced code ONLY inside an asyncio task: `asyncio.run`
# is the thread target itself, so nothing outside the task ever runs on it.
# Under the per-task basis its thread row therefore counts zero events --
# the row exists because the thread was there, and without it `refocus`
# would describe this thread as one that "ran no traced code", which is the
# opposite of what happened (it ran all of it, inside a task).
ASYNC_IN_THREAD = """
import asyncio
import threading

def helper(n):
    return n + 1

async def worker():
    helper(1)
    await asyncio.sleep(0)
    return helper(2)

def main():
    t = threading.Thread(target=asyncio.run, args=(worker(),))
    t.start()
    t.join()
    print("joined")

if __name__ == "__main__":
    main()
"""
