"""One tool call, one child process -- and nothing left running.

`Child` is the whole process layer the MCP server stands on: it spawns
the CLI as a child in its own session, bounds the wait, and guarantees
that the child AND everything the child spawned are gone before `run`
returns. Every test below therefore asserts about processes rather than
about strings -- what exit came back, which pids stopped existing, and
how long it took -- because a kill that "worked" but left a grandchild
holding a pipe is the failure this layer exists to prevent.

The sleepers live in `tests/mcp_programs.py`; every one of them writes
its pids down before it sleeps, and every test here waits for that file
rather than for a duration (see that module's docstring).

Nothing here imports `schema` or `tools`: `child.py` is the standard
library and a process, and a test that needed the tool table to spawn
one would be testing the wrong seam.

PRE-REGISTERED MUTATIONS (task 3, step 5), each with the test that
catches it:

* `start_new_session=False` ->
  `test_timeout_kills_the_group_and_reports_timed_out`. Without a new
  session the child joins the TEST RUNNER's process group, `killpg`
  signals pytest itself, and `sleep 30` survives.
* skip the SIGTERM step (straight to SIGKILL) ->
  `test_sigterm_is_tried_before_sigkill`. `term.txt` is never written,
  because SIGKILL cannot be handled.
* send SIGKILL only while the leader is still alive ->
  `test_a_grandchild_that_ignores_sigterm_is_killed_and_run_returns`.
  The leader exits 0 on SIGTERM, so the mutant never sends SIGKILL, the
  deaf grandchild keeps the pipes open, and `communicate` runs out its
  own timeout instead: `run` returns late and the grandchild is alive.
* publish `_proc` before taking the lock, or drop the `_cancelled`
  check after the spawn -> `test_cancel_before_the_spawn_still_kills`.
  The cancel that landed first is lost and `run` waits out its timeout.
* `stdin=None` -> `test_stdin_is_devnull`. The child inherits the
  driver's stdin and reads the bytes meant for the server.
* format the timeout with `{timeout}` instead of `{timeout:g}` ->
  `test_timeout_kills_the_group_and_reports_timed_out`'s `cause`
  clause, which reads `1 s` and not `1.0 s`.
"""
from __future__ import annotations

import contextlib
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from sensorium.mcp.child import Child
from tests import mcp_programs as progs

#: Long enough that a sleeper never ends on its own, short enough that a
#: lost cancel is a failing test rather than a hung suite.
PATIENCE = 30.0


def env_for(sdir) -> dict:
    """The environment the server hands a child: its own, plus the
    store the call is to read and write (D16)."""
    return dict(os.environ, SENSORIUM_DIR=str(sdir))


def wait_for(path: Path, timeout: float = 5.0) -> str:
    """The file's content once it is there and non-empty."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            text = path.read_text()
        except OSError:
            text = ""
        if text:
            return text
        time.sleep(0.02)
    raise AssertionError(f"{path.name} never appeared within {timeout} s")


def wait_for_pid(path: Path, timeout: float = 5.0) -> int:
    return int(wait_for(path, timeout).strip())


def pid_gone(pid: int, timeout: float = 3.0) -> bool:
    """True once nothing answers to `pid`. A grandchild is not this
    process's child, so once it dies init reaps it and `kill(pid, 0)`
    raises -- there is no zombie to mistake for a survivor."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.02)
    return False


def group_gone(pgid: int, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.02)
    return False


@contextlib.contextmanager
def running(child: Child):
    """`child.run()` on a second thread, with the outcome in a box.

    The `finally` cancels unconditionally: a test that fails its own
    assertion must still not leave a sleeper on the box, and `cancel` is
    idempotent, so the cost of the cleanup on a passing test is one
    signal to a process group that is already gone.
    """
    box: dict = {}
    thread = threading.Thread(target=lambda: box.update(out=child.run()),
                              daemon=True)
    thread.start()
    try:
        yield box, thread
    finally:
        child.cancel()
        thread.join(10.0)
        assert not thread.is_alive(), "run() never returned"


# -- the plain shapes -------------------------------------------------


def test_a_query_child_returns_its_exit_and_streams(tmp_path):
    """The whole happy path in one call: a real query, its real exit
    status, its real stdout. `runs` against an empty store is the
    cheapest query with something to say -- it answers NEGATIVE (1) and
    prints one line (`runs_cmd.run`)."""
    out = Child(["runs"], str(tmp_path), None, env_for(tmp_path / "sdir"),
                PATIENCE).run()

    assert out.exit == 1
    assert out.stdout.strip() == "no traces recorded"
    assert out.stderr == ""
    assert out.cause is None
    assert not out.timed_out and not out.cancelled
    assert out.pgid is not None
    assert 0 <= out.ms < 30000


def test_stdin_is_devnull(tmp_path):
    """The server's stdin is the JSON-RPC stream, so a child that
    inherited it would eat the client's next request (spec S4.1).

    The check runs inside a driver process because the assertion is
    about INHERITANCE: pytest's own stdin is already closed or empty, so
    a child that inherited it would read `''` too and the test would
    pass on the mutant. `subprocess.run(input=...)` gives the driver a
    stdin that provably holds something, and the driver's Child must
    still hand its own child nothing.
    """
    progs.write(tmp_path, "reader.py", progs.READER)
    driver = progs.write(tmp_path, "driver.py", progs.STDIN_DRIVER)

    r = subprocess.run([sys.executable, str(driver), str(tmp_path)],
                       input="not empty\n", capture_output=True, text=True,
                       cwd=str(tmp_path), env=dict(os.environ), timeout=120)

    assert r.returncode == 0, r.stderr
    assert "exit=0" in r.stdout, r.stdout
    assert "''" in r.stdout, r.stdout
    assert "not empty" not in r.stdout, r.stdout


def test_env_and_cwd_reach_the_child(tmp_path):
    """`cwd` and `SENSORIUM_DIR` are process state, which is half the
    reason a call is a child at all (spec S4.1)."""
    sdir = tmp_path / "sdir"
    progs.write(tmp_path, "pwd.py", progs.PWD)

    out = Child(["run", "--", "pwd.py"], str(tmp_path), None, env_for(sdir),
                PATIENCE).run()

    assert out.exit == 0, out.stderr
    assert f"cwd={Path(tmp_path).resolve()}" in out.stdout
    assert f"store={sdir}" in out.stdout


def test_empty_strings_for_cwd_and_python_mean_absent(tmp_path):
    """R8. `record`'s `cwd` and `python` are strings in the wire schema,
    and a client may send `""` for either; JSON Schema calls that a
    valid string. `Popen(cwd="")` raises FileNotFoundError and
    `Popen([""])` is not an interpreter, so the empty string has to mean
    what its absence means before it reaches either."""
    out = Child(["runs"], "", "", env_for(tmp_path / "sdir"), PATIENCE).run()

    assert out.exit == 1
    assert out.stdout.strip() == "no traces recorded"
    assert out.cause is None


def test_spawn_failure_is_an_outcome_not_a_raise(tmp_path):
    """A `python` field naming nothing runnable is the client's mistake,
    and the server answers it like any other call (spec S4.3)."""
    out = Child(["runs"], str(tmp_path), "/nonexistent/python",
                env_for(tmp_path / "sdir"), PATIENCE).run()

    assert out.exit is None
    assert out.cause is not None and "No such file" in out.cause
    assert out.stdout == "" and out.stderr == ""
    assert out.pgid is None
    assert not out.timed_out and not out.cancelled


def test_the_spawn_log_line_has_the_one_format(tmp_path):
    """`child <pid> pgid <pgid> tool <name>` is the ONE line every
    reader parses -- the corpus client's `child_pgids()` reads the
    server's stderr for it, and Task 7's acceptance counts on it. It is
    written once, at the spawn, and the tool name is the server's, not
    argv's, when the two differ (`record` is the CLI's `run`)."""
    lines: list[str] = []
    out = Child(["runs"], str(tmp_path), None, env_for(tmp_path / "sdir"),
                PATIENCE, lines.append).run()

    assert len(lines) == 1
    assert re.fullmatch(r"child \d+ pgid \d+ tool \w+", lines[0]), lines[0]
    assert lines[0] == f"child {out.pgid} pgid {out.pgid} tool runs"

    named: list[str] = []
    Child(["runs"], str(tmp_path), None, env_for(tmp_path / "sdir"),
          PATIENCE, named.append, name="record").run()

    assert len(named) == 1
    assert named[0].endswith(" tool record"), named[0]


# -- the kills --------------------------------------------------------


def test_timeout_kills_the_group_and_reports_timed_out(tmp_path):
    """The timeout is the server's promise that a call ends. What it has
    to end is the GROUP: the recorder runs the target in its own
    process, and the target had spawned a `sleep 30` of its own."""
    progs.write(tmp_path, "sleeper.py", progs.SLEEPER_WITH_GRANDCHILD)
    child = Child(["run", "--", "sleeper.py"], str(tmp_path), None,
                  env_for(tmp_path / "sdir"), 1.0)

    out = child.run()

    grandchild = wait_for_pid(tmp_path / "grandchild.pid")
    assert out.timed_out
    assert out.exit is None
    assert out.cause == ("timed out after 1 s "
                         "(server flag --timeout / --run-timeout)")
    assert not out.cancelled
    assert out.ms < 4000
    assert pid_gone(grandchild), f"grandchild {grandchild} survived"
    assert group_gone(out.pgid)


def test_cancel_from_another_thread_kills_and_returns_cancelled(tmp_path):
    """The reader thread cancels while the worker thread is inside
    `run`; the kill happens on the CALLING thread and the worker's
    `communicate` returns because the pipes closed."""
    progs.write(tmp_path, "sleeper.py", progs.SLEEPER_WITH_GRANDCHILD)
    child = Child(["run", "--", "sleeper.py"], str(tmp_path), None,
                  env_for(tmp_path / "sdir"), PATIENCE)

    with running(child) as (box, thread):
        grandchild = wait_for_pid(tmp_path / "grandchild.pid")
        time.sleep(0.5)
        child.cancel()
        thread.join(5.0)
        assert not thread.is_alive()

    out = box["out"]
    assert out.cancelled
    assert out.exit is None
    assert out.cause == "cancelled"
    assert not out.timed_out
    assert pid_gone(grandchild), f"grandchild {grandchild} survived"
    assert group_gone(out.pgid)


def test_cancel_before_the_spawn_still_kills(tmp_path):
    """A cancel is never lost. The server publishes the in-flight call
    under the same lock the spawn takes, but a cancel can still land
    before `Popen` has returned -- so `run` re-reads the flag under that
    lock and kills the group it has just created.

    The sleeper never gets as far as its pid file here: SIGTERM reaches
    the child a few microseconds after `Popen`, while the interpreter is
    still booting. What the test can see is that the group is gone, that
    the outcome says `cancelled`, and that `run` came back at once
    instead of waiting out its timeout -- which is exactly what a lost
    cancel would do.
    """
    progs.write(tmp_path, "sleeper.py", progs.SLEEPER)
    child = Child(["run", "--", "sleeper.py"], str(tmp_path), None,
                  env_for(tmp_path / "sdir"), PATIENCE)
    child.cancel()

    with running(child) as (box, thread):
        thread.join(3.0)
        assert not thread.is_alive(), "the cancel was lost"

    out = box["out"]
    assert out.cancelled
    assert out.exit is None
    assert out.cause == "cancelled"
    assert group_gone(out.pgid)
    assert not (tmp_path / "child.pid").exists()


def test_sigterm_is_tried_before_sigkill(tmp_path):
    """SIGTERM first, so a child that wants to finish something can.
    `term.txt` can only have been written by a handler, and only SIGTERM
    can be handled."""
    progs.write(tmp_path, "sleeper.py", progs.TRAPS_SIGTERM)
    child = Child(["run", "--", "sleeper.py"], str(tmp_path), None,
                  env_for(tmp_path / "sdir"), PATIENCE)

    with running(child) as (box, thread):
        wait_for_pid(tmp_path / "child.pid")
        child.cancel()
        thread.join(5.0)
        assert not thread.is_alive()

    out = box["out"]
    assert (tmp_path / "term.txt").read_text() == "term"
    assert out.cancelled
    assert out.exit is None
    assert group_gone(out.pgid)


def test_a_grandchild_that_ignores_sigterm_is_killed_and_run_returns(tmp_path):
    """Why SIGKILL is unconditional. The leader exits 0 on SIGTERM, so a
    kill that asked "is the leader still alive?" would stop there -- and
    the grandchild that ignores SIGTERM would go on holding the pipes,
    with the read hanging until `communicate`'s own timeout. `run` comes
    back inside the grace plus a little, and nothing is left."""
    progs.write(tmp_path, "sleeper.py", progs.GRANDCHILD_IGNORES_SIGTERM)
    child = Child(["run", "--", "sleeper.py"], str(tmp_path), None,
                  env_for(tmp_path / "sdir"), PATIENCE)

    with running(child) as (box, thread):
        grandchild = wait_for_pid(tmp_path / "grandchild.pid")
        started = time.monotonic()
        child.cancel()
        thread.join(3.0)
        elapsed = time.monotonic() - started
        assert not thread.is_alive()

    assert elapsed < 3.0, f"run() took {elapsed:.2f} s to return"
    assert pid_gone(grandchild), f"grandchild {grandchild} survived"
    assert box["out"].cancelled
    assert group_gone(box["out"].pgid)
