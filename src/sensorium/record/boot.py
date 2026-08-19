"""Resolve and execute a target program in-process under recording.

The target runs inside this interpreter, not a child: that is what makes its
frames visible to sys.monitoring at all. Everything here therefore has to put
the interpreter back the way it found it -- streams, argv, sys.path, the
monitoring tool id, the audit hook -- because `refocus` re-runs a program a
second time in the same process and must not inherit the first run's state.

Two orderings matter and are deliberate:

* The target is resolved *before* monitoring is installed, so import
  machinery, entry-point loading and runpy's own setup never land in the
  trace.
* The tracer is uninstalled *before* the writer closes, and every write goes
  through `_LateWriteGuard` so a callback a thread was already inside cannot
  write into a closed database.

A run that cannot record is a failed run: if monitoring will not install, or
the target cannot be resolved, nothing reports success. `incomplete` is
written true up front and cleared only after a clean finish, so a trace that
died mid-run says so.
"""
import hashlib
import importlib.metadata
import json
import os
import runpy
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

from sensorium import paths
from sensorium.record import capture
from sensorium.record.tracer import FocusSpec, Tracer
from sensorium.store.writer import TraceWriter


class TargetError(Exception):
    pass


# -- target resolution -----------------------------------------------------
def resolve_target(argv: list[str]):
    """Return a zero-argument callable that runs `argv`, or raise TargetError.

    Called before monitoring is installed, so nothing it imports is traced.
    """
    if not argv:
        raise TargetError("no target command given")
    cmd = argv[0]
    if cmd == "-m":
        return _module_target(argv)
    if cmd.endswith(".py"):
        return _script_target(argv)
    return _console_script_target(argv)


def _module_target(argv: list[str]):
    if len(argv) < 2:
        raise TargetError("-m requires a module name")
    mod, rest = argv[1], argv[2:]

    def run_module():
        sys.path.insert(0, os.getcwd())      # what `python -m` puts first
        sys.argv = [mod, *rest]
        runpy.run_module(mod, run_name="__main__", alter_sys=True)
    return run_module


def _script_target(argv: list[str]):
    p = Path(argv[0]).resolve()
    if not p.exists():
        raise TargetError(f"cannot resolve target: no such file: {argv[0]}")

    def run_file():
        sys.path.insert(0, str(p.parent))    # what `python script.py` does
        sys.argv = [str(p), *argv[1:]]
        runpy.run_path(str(p), run_name="__main__")
    return run_file


def _console_script_target(argv: list[str]):
    cmd = argv[0]
    for ep in importlib.metadata.entry_points(group="console_scripts",
                                              name=cmd):
        fn = ep.load()

        def run_script():
            sys.argv = list(argv)
            fn()
        return run_script
    raise TargetError(
        f"cannot resolve target {cmd!r}: not a .py file, -m module, "
        "or installed console script")


# -- stream interception ---------------------------------------------------
class _Tee:
    """Pass writes through to the real stream and into the trace.

    A delegating proxy rather than a TextIOBase subclass: programs reach for
    `sys.stdout.buffer`, `.fileno()`, `.encoding` and `.isatty()`, and a
    subclass would answer those for itself instead of for the stream the
    program actually has. Output written straight to the file descriptor
    (`os.write(1, ...)`, a child process) bypasses this and is not captured;
    the trace holds what went through the Python stream object.
    """

    def __init__(self, orig, name, writer) -> None:
        self._orig = orig
        self._name = name
        self._writer = writer

    def write(self, s):
        n = self._orig.write(s)
        if s:
            self._writer.add_output(self._writer.last_event_id, self._name, s)
        return n

    def writelines(self, lines) -> None:
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        self._orig.flush()

    def __getattr__(self, name):
        return getattr(self._orig, name)


_MARK_ON_CALL = ("read", "readline", "readlines", "readinto", "read1")
_MARK_ON_ACCESS = ("buffer", "detach")


class _StdinProxy:
    """Mark the run as having consumed stdin, so replay knows it is not pure.

    Only reads that go through the Python object are seen. An interactive
    `input()` on a real tty is served by the readline fast path against fd 0
    and does not touch this proxy; piped and redirected stdin, which is what
    a recorded run almost always has, does.

    Everything else about the stream must behave exactly as it would without
    the recorder -- an instrument that changes the program it observes is
    worse than no instrument.
    """

    def __init__(self, orig) -> None:
        self._orig = orig
        self.consumed = False

    def _marking(self, fn):
        def inner(*a, **k):
            self.consumed = True
            return fn(*a, **k)
        return inner

    def __getattr__(self, name):
        attr = getattr(self._orig, name)     # raises first: absent is not use
        if name in _MARK_ON_CALL:
            return self._marking(attr)
        if name in _MARK_ON_ACCESS:
            # Handing out the binary layer forfeits the ability to see the
            # read, so the access itself counts. Over-marking is the safe
            # direction: it costs a refused refocus, where a missed mark
            # costs a MATCH verdict on a run that was never repeatable.
            self.consumed = True
        return attr

    # Implicit special-method lookup goes to the type, not to __getattr__, so
    # every dunder a program might use on a stream is spelled out here. A
    # missing one is not a missed mark -- it is a TypeError in a program that
    # ran fine without the recorder.
    def __iter__(self):
        self.consumed = True
        return self               # a file is its own iterator; so is this

    def __next__(self):
        self.consumed = True
        return next(self._orig)

    def __enter__(self):
        self._orig.__enter__()
        return self               # never the raw stream: reads must stay seen

    def __exit__(self, *exc_info):
        return self._orig.__exit__(*exc_info)

    def __repr__(self) -> str:
        return repr(self._orig)   # the instrument does not announce itself


# -- writes from threads that outlive the target ---------------------------
class _LateWriteGuard:
    """Serialise every trace write against close.

    Uninstalling the tracer stops new callbacks, but a thread already inside
    one runs to completion and writes afterwards -- a daemon thread parked in
    a captured value's `__repr__` when the target's main function returns is
    the reachable case. Sealing under the same lock that guards each
    delegated write makes such a write either land before the close or be
    dropped and counted; it can never reach a closed sqlite connection.
    (Measured: with the writer's default batching a late write is merely
    buffered and lost, but any flush it triggers raises
    `sqlite3.ProgrammingError` from inside the monitoring callback and kills
    that thread.)

    Dropping is the only available answer -- the database has to close, and
    the thread may run forever -- so nothing is dropped quietly: `seal()`
    stops accepting writes while the connection is still open, which is what
    lets the drop count reach `late_writes` in the run metadata, and
    `run_target` reports both that count and the threads still alive.
    """

    def __init__(self, writer: TraceWriter) -> None:
        self._w = writer
        self._lock = threading.Lock()
        self._sealed = False
        self._closed = False
        self.late_writes = 0

    @property
    def last_event_id(self) -> int:
        return self._w.last_event_id

    def _call(self, name, *args, **kwargs):
        with self._lock:
            if self._sealed:
                self.late_writes += 1
                return 0
            return getattr(self._w, name)(*args, **kwargs)

    def intern_code(self, *a, **k):
        return self._call("intern_code", *a, **k)

    def add_event(self, *a, **k):
        return self._call("add_event", *a, **k)

    def open_frame(self, *a, **k):
        return self._call("open_frame", *a, **k)

    def close_frame(self, *a, **k):
        return self._call("close_frame", *a, **k)

    def add_output(self, *a, **k):
        return self._call("add_output", *a, **k)

    def set_meta(self, *a, **k):
        return self._call("set_meta", *a, **k)

    def write_fingerprint(self, *a, **k):
        return self._call("write_fingerprint", *a, **k)

    def seal(self) -> None:
        """Stop accepting writes; the connection stays open to finalize."""
        with self._lock:
            self._sealed = True

    def set_meta_final(self, key, value) -> None:
        """Write metadata after the seal: the finalizer is not a late write."""
        with self._lock:
            if not self._closed:
                self._w.set_meta(key, value)

    def interned_files(self) -> list[str]:
        """Deliberately not routed through `_call`: this is a read, and a
        sealed writer must still be able to answer it for the finalizer."""
        return self._w.interned_files()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._sealed = self._closed = True
            self._w.close()


# -- child processes -------------------------------------------------------
_audit_lock = threading.Lock()
_audit_sink: list | None = None    # the `children` list of the run in progress
_audit_installs = 0                # audit hooks added, ever, by this process


# Audit events that start another process, mapped to the positional argument
# carrying the command (None where the event carries no command at all).
#
# `subprocess.Popen` alone was not enough: `os.system` spawns a shell without
# ever touching `subprocess`, so a run that shelled out recorded
# `children == []` and was reported as having witnessed everything it did.
#
# The set is chosen from measurement, not from the audit-event list, because
# the events nest. Measured on this platform:
#
#   subprocess.run(...)     -> subprocess.Popen, os.posix_spawn
#   subprocess.run(shell=1) -> subprocess.Popen, os.posix_spawn
#   os.system(...)          -> os.system
#   os.spawnv(...)          -> os.fork
#   os.posix_spawn(...)     -> os.posix_spawn
#
# so `os.posix_spawn` is deliberately absent: it is how CPython implements
# `subprocess.Popen` here, and listening to both counts every subprocess
# twice. The cost is a known gap -- a DIRECT `os.posix_spawn` call is not
# noticed -- which is recorded here rather than papered over. `os.exec*` is
# absent for a different reason: it replaces this process rather than
# starting a child, so there is no run left to attach the note to.
_CHILD_EVENTS = {
    "subprocess.Popen": 1,     # (executable, args, cwd, env)
    "os.system": 0,            # (command,)
    "os.fork": None,           # no args; also how os.spawn* reaches the OS
}


def _audit(event, args) -> None:
    """Note child processes. One hook for the whole process, armed per run.

    `sys.addaudithook` cannot be removed, so a hook per run would accumulate:
    after `refocus` re-runs a program, the first run's hook would still be
    appending into a list nobody reads for every subprocess anything spawns
    for the rest of the process's life. One module-level hook, armed and
    disarmed around each run, has neither problem.
    """
    if event not in _CHILD_EVENTS:
        return
    try:
        sink = _audit_sink
        if sink is None:
            return
        index = _CHILD_EVENTS[event]
        if index is None:
            sink.append([f"<{event}>"])    # a child with no command to name
            return
        cmd = args[index] if len(args) > index else None
        if not cmd:
            return
        if isinstance(cmd, (str, bytes, os.PathLike)):
            cmd = [cmd]           # a bare command line, as Windows reports it
        sink.append([_as_text(a) for a in cmd][:8])
    except Exception:
        pass          # an audit hook that raises breaks the audited operation


def _as_text(arg) -> str:
    """Every recorded argument must be a str, or json.dumps kills the run.

    `Popen` takes bytes anywhere a str is allowed -- `Popen(b"...",
    shell=True)` reaches the hook as `['/bin/sh', '-c', b'...']` -- and
    `str(b"x")` would record the literal `"b'x'"`, so decode rather than
    stringify. `db.set_meta` json-encodes `children` inside the finalizer,
    which runs before the writer closes: an unserializable entry there aborts
    finalization, leaks the connection, and masks the program's exit status.
    """
    if isinstance(arg, bytes):
        return arg.decode("utf-8", "replace")
    return str(arg)


def _arm_audit(sink: list) -> None:
    global _audit_sink, _audit_installs
    with _audit_lock:
        if _audit_installs == 0:
            sys.addaudithook(_audit)
            _audit_installs += 1
        _audit_sink = sink


def _disarm_audit() -> None:
    global _audit_sink
    with _audit_lock:
        _audit_sink = None


# -- run metadata ----------------------------------------------------------
def git_info(cwd: Path) -> dict:
    """Repository context for the run. NOT a change detector.

    `git_dirty_hash` hashes the OUTPUT of `git status --porcelain`, which is
    a list of paths and their status letters -- not file contents. A file
    that is already dirty when a run is recorded can then be edited
    arbitrarily, including the program being executed, and this hash does not
    move; nor does it see gitignored or out-of-repo files. It answers "which
    paths were dirty", and nothing that needs "did the code change" may be
    built on it. `source_hashes` below is the check with that meaning.
    """
    def _git(*args):
        r = subprocess.run(["git", *args], cwd=cwd,
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    sha = _git("rev-parse", "HEAD")
    if sha is None:
        return {"git_sha": None, "git_dirty_hash": None}
    status = _git("status", "--porcelain") or ""
    return {"git_sha": sha,
            "git_dirty_hash": hashlib.sha256(status.encode()).hexdigest()[:16]}


def hash_file(path: str) -> str | None:
    """sha256 of a file's bytes, or None if it cannot be read now."""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return None


def _source_hashes(files) -> dict:
    """Content digests for every file this run executed traced code from.

    This is what makes "the source is unchanged" a claim the tool has
    actually verified. Its limit is precise and worth knowing: it covers the
    files the ORIGINAL run interned code from, plus the entry target. Code
    that was never traced -- stdlib, site-packages, anything `--include` /
    `--exclude` filtered out -- is not in the map and its changes are
    invisible here.
    """
    return {f: hash_file(f) for f in sorted(files)}


def _write_run_meta(w, run_id, argv, focus, include, exclude, window,
                    refocus_of) -> None:
    env = dict(os.environ)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", list(argv))
    w.set_meta("cwd", str(Path.cwd()))
    w.set_meta("env", env)
    w.set_meta("env_hash", hashlib.sha256(
        json.dumps(env, sort_keys=True).encode()).hexdigest()[:16])
    w.set_meta("python", sys.version.split()[0])
    for k, v in git_info(Path.cwd()).items():
        w.set_meta(k, v)
    # `target()` (below) runs synchronously on whichever thread called
    # `run_target` -- deliberately `threading.get_ident()`, NOT
    # `threading.main_thread().ident`. For the ordinary `sensorium run` CLI
    # path the two are identical (__main__ -> cli.main -> _run ->
    # run_target never crosses a thread boundary), but they are not the
    # same question: `main_thread().ident` names the interpreter's global
    # main thread regardless of who is asking, while `get_ident()` names
    # the thread that is actually about to execute the target's top-level
    # code. A hypothetical future caller that invokes `run_target` from a
    # worker thread would have `main_thread().ident` point at a thread that
    # may hold none of this run's events at all -- a worse lie than the
    # event-id-1 heuristic this key exists to replace. `get_ident()` is
    # correct under both calling conventions. `Trace.main_thread_id()`
    # prefers this key when present.
    w.set_meta("main_thread_ident", threading.get_ident())
    w.set_meta("focus", list(focus))
    w.set_meta("include", list(include))
    w.set_meta("exclude", list(exclude))
    w.set_meta("window", window)
    w.set_meta("caps", capture.CAPS)
    w.set_meta("start_ts", time.time())
    w.set_meta("incomplete", True)      # cleared only after a clean finish
    if refocus_of:
        w.set_meta("refocus_of", refocus_of)


def _finalize_meta(w, *, exit_status, uncaught, stdin_consumed, children,
                   truncated_count, live_threads, entry) -> None:
    """Close out the run. Runs after `w.seal()`, hence `set_meta_final`."""
    w.set_meta_final("uncaught", uncaught)
    w.set_meta_final("stdin_consumed", stdin_consumed)
    w.set_meta_final("children", children)
    w.set_meta_final("truncated_count", truncated_count)
    # Threads still running when recording stopped. Already computed for the
    # stderr gap warning; stored because a thread that ran only stdlib code
    # produces NO fingerprint row, so counting fingerprints alone reports a
    # single-threaded run while a second thread is doing file I/O.
    w.set_meta_final("live_threads", live_threads)
    files = set(w.interned_files())
    if entry:
        files.add(entry)       # the target itself, even if it traced nothing
    w.set_meta_final("source_hashes", _source_hashes(files))
    w.set_meta_final("exit_status", exit_status)
    w.set_meta_final("end_ts", time.time())
    w.set_meta_final("late_writes", w.late_writes)   # read as late as possible
    w.set_meta_final("incomplete", False)


# -- running ---------------------------------------------------------------
def _exit_status_of(exc: SystemExit) -> int:
    code = exc.code
    if code is None:
        return 0
    if isinstance(code, int):
        return int(code)
    print(code, file=sys.stderr)        # what the interpreter itself does
    return 1


def _live_thread_names() -> list[str]:
    return [t.name for t in threading.enumerate()
            if t is not threading.current_thread() and t.is_alive()]


def _recording_gaps(live: list[str], dropped: int) -> str | None:
    """Say what the trace does not contain. Silence would be the failure."""
    parts = []
    if live:
        names = ", ".join(sorted(live)[:4])
        parts.append(f"{len(live)} thread(s) still alive when recording "
                     f"stopped ({names}); anything they run after this point "
                     "is not in the trace")
    if dropped:
        parts.append(f"{dropped} trace write(s) arrived after the recorder "
                     "stopped accepting them and were dropped")
    if not parts:
        return None
    return "sensorium: " + "; ".join(parts) + "."


def run_target(argv, *, focus=(), include=(), exclude=(), window=None,
               run_id=None, refocus_of=None):
    """Record one execution of `argv`. Returns (run_id, exit_status)."""
    run_id = run_id or paths.new_run_id()
    target = resolve_target(list(argv))   # resolve before hooks: never traced
    # Resolved here, before the program can chdir underneath us.
    entry = (str(Path(argv[0]).resolve())
             if argv and str(argv[0]).endswith(".py") else None)
    w = _LateWriteGuard(TraceWriter(paths.traces_dir() / f"{run_id}.db"))
    _write_run_meta(w, run_id, argv, focus, include, exclude, window,
                    refocus_of)
    truncated_before = capture.capture_stats["truncated"]
    tracer = Tracer(w, root=Path.cwd(), focus=FocusSpec(list(focus)),
                    include=include, exclude=exclude, window=window)
    try:
        tracer.install()
    except BaseException:
        w.set_meta("end_ts", time.time())
        w.close()          # a trace still marked incomplete, and a loud raise
        raise

    children: list[list[str]] = []
    _arm_audit(children)
    saved = (sys.stdin, sys.stdout, sys.stderr, sys.argv, list(sys.path))
    stdin_proxy = _StdinProxy(sys.stdin)
    sys.stdin = stdin_proxy
    sys.stdout = _Tee(saved[1], "stdout", w)
    sys.stderr = _Tee(saved[2], "stderr", w)
    exit_status, uncaught = 0, None
    try:
        target()
    except SystemExit as e:
        exit_status = _exit_status_of(e)
    except BaseException as e:
        exit_status = 1
        # Ask the tracer for this object's serial before uninstalling it, so
        # the uncaught record names the exact RAISE row that produced it
        # rather than being matched back by a recyclable address.
        uncaught = capture.capture_exc(e, tracer.serial_of(e))
        traceback.print_exception(e)   # tee'd: the trace holds what was shown
    finally:
        tracer.uninstall()             # stop callbacks before closing the db
        _disarm_audit()
        sys.stdin, sys.stdout, sys.stderr, sys.argv = saved[:4]
        sys.path[:] = saved[4]
        w.seal()                       # in-flight callbacks stop writing here
        live = _live_thread_names()
        try:
            _finalize_meta(
                w, exit_status=exit_status, uncaught=uncaught,
                stdin_consumed=stdin_proxy.consumed, children=children,
                truncated_count=(capture.capture_stats["truncated"]
                                 - truncated_before),
                live_threads=live, entry=entry)
        finally:
            w.close()                  # never skipped: no leaked connection
            gaps = _recording_gaps(live, w.late_writes)
            if gaps:
                print(gaps, file=sys.stderr)
    return run_id, exit_status
