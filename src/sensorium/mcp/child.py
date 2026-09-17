"""One tool call, one child process -- in its own session, killed by group.

WHY A CHILD (spec S4.1). `sensorium run` executes the target IN the
recording process under `sys.monitoring`, so an in-process `record`
would import the client's program into the server; a query that raised
would take the server down with it; `cwd` and `SENSORIUM_DIR` are
process state, not arguments; and a timeout on an in-process call has no
clean kill. The cost is one interpreter start per call, which is
reported and never gated. The interpreter is `sys.executable` (or the
call's own `python`), never a `sensorium` found on PATH -- the
stale-driver lesson applies to the server's own interpreter too.

WHY STDIN IS /dev/null. The server's stdin IS the JSON-RPC stream. A
child that inherited it would read the client's next request and the
session would stall with neither side at fault, so `stdin` is
`DEVNULL` for every call without exception.

THE KILL ORDER, and why SIGKILL is unconditional. `start_new_session`
puts the child in a session and a process group of its own, whose id is
the child's pid, so one `killpg` reaches everything the call spawned --
never `pkill -f`, which self-matches and leaves the survivors. The
sequence is SIGTERM, then up to `GRACE` seconds of polling for the
GROUP to empty (the leader is reaped as we go: a zombie leader keeps its
group alive and would read as a survivor), then SIGKILL -- sent whether
or not anything answered. A leader that exited politely on SIGTERM can
leave a grandchild that ignored it holding the inherited pipes, and a
kill that asked "is the leader still alive?" would never send the signal
that ends it. `communicate(timeout=REAP)` then bounds the read either
way: a descendant that escaped the session with its own `setsid` can
still hold a pipe, and the timeout is how that returns instead of
hanging the worker thread forever.

CANCEL IS NEVER LOST. `run` spawns under the Child's one lock and, still
holding it, re-reads the cancelled flag and kills the group it has just
created. That closes the window the server cannot close from outside:
the reader thread can call `cancel` after the worker popped the request
but before `Popen` returned, and a cancel that only killed `_proc` would
find it `None` and do nothing. `cancel` takes the same lock, so the two
can happen in one order only, and it runs the kill on the CALLING thread
(`Popen.wait` is safe from a second thread): the worker's `communicate`
returns because the pipes closed, reads the flag, and reports
`cancelled` with no exit status at all.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

#: Seconds between SIGTERM and the unconditional SIGKILL.
GRACE = 2.0

#: How often the grace period asks whether the group has emptied.
POLL = 0.05

#: The bound on the final read: a pipe held from outside the session.
REAP = 2.0


@dataclass(frozen=True)
class Outcome:
    """What one call produced. `exit` is `Popen.returncode` (negative
    for a signal) and is None whenever no exit was PRODUCED -- a
    timeout, a cancel, a spawn that never happened -- which the server
    renders as `no answer` rather than as a status."""

    exit: int | None
    stdout: str
    stderr: str
    cause: str | None
    ms: int
    timed_out: bool = False
    cancelled: bool = False
    pgid: int | None = None


def _signal_group(pgid: int, sig: int) -> None:
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass                      # already gone: what the signal was for


def _shut(proc: subprocess.Popen) -> None:
    """Close what we will not finish reading, so the fds do not leak
    into the next call."""
    for pipe in (proc.stdout, proc.stderr):
        if pipe is not None:
            try:
                pipe.close()
            except OSError:
                pass


def _reap(proc: subprocess.Popen) -> tuple[str, str]:
    """Collect the child and its streams, without hanging on either.

    `Popen` keeps what each `communicate` read, so calling this again
    after `kill_group` has been through adds no wait -- the pipes are at
    EOF or closed -- and hands back the whole of it decoded."""
    try:
        out, err = proc.communicate(timeout=REAP)
    except subprocess.TimeoutExpired:
        _shut(proc)               # a descendant outside the session has it
    except (OSError, ValueError):
        pass                      # already closed by an earlier kill
    else:
        return out or "", err or ""
    return "", ""


def kill_group(proc: subprocess.Popen, grace: float = GRACE) -> None:
    """SIGTERM the child's group, wait `grace` for it to empty, SIGKILL
    it anyway, then reap. See the module docstring for why every step is
    where it is. `ProcessLookupError` at any step means "already gone"
    and is never an error."""
    if not hasattr(os, "killpg"):            # pragma: no cover - Windows
        proc.terminate()                     # advisory, untested here
        try:
            proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            proc.kill()
        _reap(proc)
        return
    pgid = proc.pid               # start_new_session: the child leads
    _signal_group(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        proc.poll()               # reap: a zombie leader holds the group
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            break                 # the whole group has gone
        time.sleep(POLL)
    _signal_group(pgid, signal.SIGKILL)
    _reap(proc)


class Child:
    """The CLI, as a child process, for exactly one call.

    `name` is the tool the server was asked for, which is not always
    `argv[0]` (`record` is the CLI's `run`); it appears in the one log
    line and nowhere else. `cwd` and `python` arrive from a JSON object
    where the empty string is a valid string, and an empty one means
    what an absent one means -- `Popen(cwd="")` raises and `[""]` is not
    an interpreter.
    """

    def __init__(self, argv: list[str], cwd: str | None, python: str | None,
                 env: dict, timeout: float, log=None,
                 name: str | None = None):
        self._argv = list(argv)
        self._cwd = cwd or None
        self._python = python or None
        self._env = env
        self._timeout = timeout
        self._log = log
        self._name = name or (self._argv[0] if self._argv else "?")
        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._cancelled = False

    def run(self) -> Outcome:
        started = time.monotonic()
        with self._lock:
            try:
                proc = subprocess.Popen(
                    [self._python or sys.executable, "-m", "sensorium",
                     *self._argv],
                    cwd=self._cwd, env=self._env,
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True, encoding="utf-8",
                    errors="replace", start_new_session=True)
            except OSError as err:
                return self._outcome(started, None, "", "", str(err))
            self._proc = proc
            if self._log is not None:
                self._log(f"child {proc.pid} pgid {proc.pid} "
                          f"tool {self._name}")
            if self._cancelled:
                kill_group(proc)  # a cancel that landed before the spawn
        timed_out, broke = False, None
        try:
            out, err = proc.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_group(proc)
            out, err = _reap(proc)
        except (OSError, ValueError) as exc:
            out, err, broke = "", "", str(exc)   # a cancel closed the pipes
        with self._lock:
            cancelled = self._cancelled
        if cancelled:
            return self._outcome(started, None, out, err, "cancelled",
                                 cancelled=True, pgid=proc.pid)
        if timed_out:
            cause = (f"timed out after {self._timeout:g} s "
                     f"(server flag --timeout / --run-timeout)")
            return self._outcome(started, None, out, err, cause,
                                 timed_out=True, pgid=proc.pid)
        return self._outcome(started, proc.returncode, out, err, broke,
                             pgid=proc.pid)

    def cancel(self) -> None:
        """Kill the call, from whichever thread noticed. Idempotent: a
        second cancel signals a group that is already gone."""
        with self._lock:
            self._cancelled = True
            if self._proc is not None:
                kill_group(self._proc)

    def _outcome(self, started: float, exit_: int | None, out: str, err: str,
                 cause: str | None, **flags) -> Outcome:
        return Outcome(exit=exit_, stdout=out, stderr=err, cause=cause,
                       ms=int((time.monotonic() - started) * 1000), **flags)
