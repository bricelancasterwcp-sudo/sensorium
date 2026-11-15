"""Record Python child processes into the run that spawned them.

`subprocess` and `multiprocessing` (fork, and spawn via fork_exec) start a
new interpreter or a forked copy of this one. The child's calls never appear
in the parent trace: the parent only sees the spawn. This module follows a
child when the executable is Python, writes a side spool the parent does not
share, and merges that spool back under the frame that spawned it.

A child that is not Python is counted and left alone. `SENSORIUM_NO_CHILDREN`
and `--no-children` skip the whole thing. A failure inside a child, or while
merging one, is counted and does not fail the parent.

The side directory lives outside the working directory on purpose. The
tracer records every file under that directory, and a hook placed inside it
would record itself.
"""
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from sensorium.record.children_merge import (
    merge_one as _merge_one,
    process_alive as _process_alive,
    spool_status as _spool_status,
)

_OFF = {"1", "true", "yes", "on"}
_SELF = os.path.realpath(__file__)
_SUBPROCESS = os.path.realpath(subprocess.__file__)


class _State:
    def __init__(self) -> None:
        self.armed = False
        self.record = False
        self.tracer = None
        self.spool_dir: Path | None = None
        self.hook_dir: Path | None = None
        self.non_python = 0
        self.popen_orig = None
        self.fork_exec_orig = None
        self.fork_hook = False
        self.forked = False
        self.pending_frame: int | None = None
        self.flushed = False
        self.finish_registered = False
        self.leaked: list = []
        self.exit_orig = None
        self.spawn_orig = None
        self.execve_orig = None
        self.focus = ()
        self.include = ()
        self.exclude = ()
        self.window = None
        self.limits = None


_STATE = _State()
# os._exit must call whichever spool is current. A forkserver worker
# inherits the wrapper and then points the tracer at its own file; a
# closure captured in the forkserver would flush the server instead.
_EXECING: set[int] = set()
_PENDING: dict[int, int | None] = {}


def children_enabled(env=None) -> bool:
    """True unless the process asked not to follow children."""
    env = os.environ if env is None else env
    return str(env.get("SENSORIUM_NO_CHILDREN", "")).lower() not in _OFF


def arm_children(tracer, *, record=True, focus=(), include=(), exclude=(),
                 window=None, limits=None) -> Path | None:
    """Start following children for this run.

    Returns the spool directory, or None when this run is not recording
    children. The fork hook is installed either way: a forked interpreter
    otherwise keeps the parent's monitoring callbacks and writes the
    child's calls into the parent's trace file.
    """
    _STATE.tracer = tracer
    _STATE.focus = tuple(focus or ())
    _STATE.include = tuple(include or ())
    _STATE.exclude = tuple(exclude or ())
    _STATE.window = window
    _STATE.limits = limits
    _STATE.non_python = 0
    _STATE.flushed = False
    _STATE.armed = True
    _STATE.record = bool(record)
    _install_fork_hook()
    if not record:
        return None
    spool = Path(tempfile.mkdtemp(prefix="sensorium-children-"))
    os.chmod(spool, 0o700)
    hook = spool / "hook"
    hook.mkdir(mode=0o700)
    _write_hook(hook)
    _STATE.spool_dir = spool
    _STATE.hook_dir = hook
    _install_popen()
    _install_fork_exec()
    _install_spawn_exec()
    return spool


def disarm_children() -> None:
    """Stop following. The fork hook cannot be removed; the flag no-ops it."""
    _STATE.armed = False
    _STATE.record = False
    _STATE.tracer = None
    if _STATE.popen_orig is not None:
        subprocess.Popen.__init__ = _STATE.popen_orig
        _STATE.popen_orig = None
    if _STATE.fork_exec_orig is not None:
        try:
            import _posixsubprocess
            _posixsubprocess.fork_exec = _STATE.fork_exec_orig
        except Exception:
            pass
        _STATE.fork_exec_orig = None
    if _STATE.spawn_orig is not None:
        os.posix_spawn = _STATE.spawn_orig
        _STATE.spawn_orig = None
    if _STATE.execve_orig is not None:
        os.execve = _STATE.execve_orig
        _STATE.execve_orig = None


def merge_children(guard, spool_dir) -> dict:
    """Copy finished child spools into `guard`. Never raises.

    Incomplete spools are skipped. A resource-tracker process is still alive
    at finalize and must not count as a failed child. A spool that cannot be
    read is counted in `child_record_errors`.
    """
    stats = {
        "python_children": 0,
        "child_record_errors": 0,
        "non_python_children": _STATE.non_python,
    }
    directory = Path(spool_dir)
    try:
        if not directory.is_dir():
            return stats
        for err in directory.glob("*.err"):
            if err.is_file():
                stats["child_record_errors"] += 1
        for path in sorted(directory.glob("*.db")):
            try:
                done, pid = _spool_status(path)
            except Exception:
                stats["child_record_errors"] += 1
                continue
            # A live child (forkserver, resource tracker) has not finished
            # its spool. Skipping it is not a failed record.
            if not done and _process_alive(pid):
                continue
            if not done:
                stats["child_record_errors"] += 1
            try:
                if _merge_one(guard, path):
                    stats["python_children"] += 1
            except Exception:
                stats["child_record_errors"] += 1
    except Exception:
        stats["child_record_errors"] += 1
    finally:
        shutil.rmtree(directory, ignore_errors=True)
        _STATE.spool_dir = None
    return stats


def record_this_process() -> None:
    """Entry point for a spawned interpreter's sitecustomize.

    Forked children do not come through here: they already have a tracer,
    which `os.register_at_fork` points at a fresh spool.
    """
    if not children_enabled() or _STATE.flushed:
        return
    spool = os.environ.get("SENSORIUM_CHILD_SPOOL")
    if not spool:
        return
    try:
        _record_spawned(Path(spool))
    except Exception:
        _note_error(Path(spool), "start")


def _record_spawned(spool_dir: Path) -> None:
    from sensorium.limits import Limits
    from sensorium.record.tracer import FocusSpec, Tracer
    from sensorium.store.writer import TraceWriter

    _install_redact()
    cfg = _spawn_cfg()
    hook = os.environ.get("SENSORIUM_CHILD_HOOK")
    if hook:
        _STATE.hook_dir = Path(hook)
    path = spool_dir / f"{os.getpid()}.db"
    writer = TraceWriter(path)
    frame = _env_frame()
    writer.set_meta("parent_frame", frame)
    writer.set_meta("incomplete", True)
    root = Path(os.environ.get("SENSORIUM_CHILD_ROOT") or os.getcwd())
    lim = cfg.get("limits")
    limits = (Limits(int(lim[0]), int(lim[1]), int(lim[2]))
              if isinstance(lim, list) and len(lim) == 3 else None)
    tracer = Tracer(
        writer, root=root, focus=FocusSpec(list(cfg.get("focus") or ())),
        include=tuple(cfg.get("include") or ()),
        exclude=tuple(cfg.get("exclude") or ()),
        window=cfg.get("window"), limits=limits)
    tracer.install()
    _STATE.tracer = tracer
    _STATE.spool_dir = spool_dir
    _STATE.armed = True
    _STATE.record = True
    _STATE.flushed = False
    _STATE.focus = tuple(cfg.get("focus") or ())
    _STATE.include = tuple(cfg.get("include") or ())
    _STATE.exclude = tuple(cfg.get("exclude") or ())
    _STATE.window = cfg.get("window")
    _STATE.limits = limits
    # This process may itself fork (a forkserver). The hook is per
    # interpreter, and exec does not keep the parent's registration.
    _install_fork_hook()
    _install_popen()
    _install_fork_exec()
    _install_spawn_exec()
    _arm_finish()


def _redirect_fork_child(frame: int | None) -> None:
    """Point the inherited tracer at a new spool.

    The copied writer still holds the parent's SQLite connection. Closing it
    here would checkpoint the parent's database from the child. It is kept
    alive and unused instead: multiprocessing leaves via os._exit, which
    does not run that destructor. Calls that were already open belong to the
    parent, so their returns are dropped (`Tracer._fork_child`).
    """
    from sensorium.store.writer import TraceWriter

    tracer = _STATE.tracer
    spool = _STATE.spool_dir
    if tracer is None or spool is None:
        return
    _STATE.flushed = False
    _STATE.leaked.append(tracer.writer)
    _STATE.leaked.append(tracer)
    writer = TraceWriter(spool / f"{os.getpid()}.db")
    writer.set_meta("parent_frame", frame)
    writer.set_meta("incomplete", True)
    tracer.writer = writer
    # The copied budget still holds the parent's writer. Counting from
    # here keeps this child's calls on this spool, and a later report
    # reads this connection rather than the parent's.
    if getattr(tracer, "_budget", None) is not None:
        from sensorium.record.budget import Budget
        tracer._budget = Budget(tracer.limits, writer)
    tracer._fork_child = True
    tracer._tls.live.clear()
    with tracer._parked_lock:
        tracer._parked.clear()
    with tracer._fp_lock:
        tracer._fps.clear()
        tracer._task_fps.clear()
    _arm_finish()


def _flush_current() -> None:
    """Close this process's spool. Looks up the tracer at call time.

    A forkserver worker inherits the parent's os._exit wrapper. The wrapper
    has to flush the worker's writer, which was installed after the fork,
    not the server's writer the wrapper was first created beside.
    """
    if _STATE.flushed:
        return
    _STATE.flushed = True
    tracer = _STATE.tracer
    if tracer is None:
        return
    writer = tracer.writer
    try:
        tracer.uninstall()
        writer.set_meta("incomplete", False)
    except Exception:
        spool = _STATE.spool_dir
        if spool is not None:
            _note_error(spool, "flush")
        try:
            writer.set_meta("incomplete", True)
        except Exception:
            pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


def _arm_finish() -> None:
    _wrap_exit()
    if _STATE.finish_registered:
        return
    atexit.register(_flush_current)
    _STATE.finish_registered = True


def _silence_inherited() -> None:
    """Drop a forked tracer without writing through its connection.

    `Tracer.uninstall` stores fingerprints. On an opt-out fork that would
    write the child's calls into the parent's trace. Events are turned off
    and the writer is pinned so it is not closed onto the parent's file.
    """
    tracer = _STATE.tracer
    if tracer is not None:
        _STATE.leaked.append(tracer)
        writer = getattr(tracer, "writer", None)
        if writer is not None:
            _STATE.leaked.append(writer)
    try:
        mon = sys.monitoring
        tool = mon.PROFILER_ID
        mon.set_events(tool, 0)
        ev = mon.events
        for kind in (ev.PY_START, ev.PY_RETURN, ev.PY_UNWIND, ev.RAISE,
                     ev.RERAISE, ev.EXCEPTION_HANDLED, ev.LINE,
                     ev.PY_YIELD, ev.PY_RESUME, ev.PY_THROW):
            try:
                mon.register_callback(tool, kind, None)
            except Exception:
                pass
        try:
            mon.free_tool_id(tool)
        except Exception:
            pass
    except Exception:
        pass
    _STATE.tracer = None
    _STATE.record = False


def _install_redact() -> None:
    """Same key and knobs the parent recorded under. A spawned interpreter
    does not go through `run_target`, so nothing has installed the rule."""
    try:
        from sensorium import paths, redact
        from sensorium import redact_values as rv
        rv.install(redact.Key.load_or_create(paths.trace_root()),
                   redact.Knobs.from_environ(os.environ))
    except Exception:
        pass


def _spawn_cfg() -> dict:
    raw = os.environ.get("SENSORIUM_CHILD_CFG") or ""
    if not raw:
        return {}
    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return cfg if isinstance(cfg, dict) else {}


def _note_error(spool: Path, what: str) -> None:
    try:
        spool.mkdir(parents=True, exist_ok=True)
        (spool / f"{os.getpid()}.err").write_text(what)
    except Exception:
        pass


def _env_frame() -> int | None:
    raw = os.environ.get("SENSORIUM_PARENT_FRAME", "")
    if raw.isdigit():
        return int(raw)
    return None


def _is_python(argv0) -> bool:
    if argv0 is None:
        return False
    try:
        text = os.fsdecode(argv0)
    except Exception:
        return False
    try:
        if os.path.realpath(text) == os.path.realpath(sys.executable):
            return True
    except OSError:
        pass
    base = os.path.basename(text).lower()
    if base.endswith(".exe"):
        base = base[:-4]
    if base in {"python", "python3"}:
        return True
    if base.startswith("python3."):
        rest = base[len("python3."):]
        if rest.isdigit():
            return True
    return False


def _machinery(filename: str) -> bool:
    try:
        real = os.path.realpath(filename)
    except OSError:
        real = filename
    if real in {_SELF, _SUBPROCESS}:
        return True
    norm = real.replace("\\", "/")
    return ("/multiprocessing/" in norm
            or "/concurrent/futures/" in norm
            or norm.endswith("/concurrent/futures.py"))


def _starter_frame(tracer) -> int | None:
    """The traced frame that asked for this child, or None.

    stdlib and this module sit between that frame and the spawn. A frame
    this run did not trace is not a parent the trace can name.
    """
    if tracer is None:
        return None
    tls = tracer._tls
    frame = sys._getframe()
    while frame is not None:
        if not _machinery(frame.f_code.co_filename):
            entry = tls.live.get(id(frame))
            if entry is not None and type(entry[0]) is int:
                return entry[0]
            return None
        frame = frame.f_back
    return None


def _cfg_blob() -> str:
    limits = _STATE.limits
    lim = None
    if limits is not None:
        lim = [int(limits.max_events), int(limits.max_bytes),
               int(limits.max_calls)]
    return json.dumps({
        "focus": list(_STATE.focus),
        "include": list(_STATE.include),
        "exclude": list(_STATE.exclude),
        "window": _STATE.window,
        "limits": lim,
    }, separators=(",", ":"))


def _child_env(base, frame: int | None) -> dict:
    env = dict(os.environ if base is None else base)
    # An explicit env would otherwise drop the store and the redaction
    # knobs the child has to read. Do not copy SENSORIUM_NO_CHILDREN:
    # a recorded parent records its grandchildren too.
    for key in ("SENSORIUM_DIR", "SENSORIUM_NO_REDACT",
                "SENSORIUM_REDACT_NAMES", "SENSORIUM_REDACT_ALLOW"):
        if key not in env and key in os.environ:
            env[key] = os.environ[key]
    hook = str(_STATE.hook_dir) if _STATE.hook_dir is not None else ""
    prev = env.get("PYTHONPATH", "")
    if hook and (not prev or not prev.startswith(hook)):
        env["PYTHONPATH"] = hook + (os.pathsep + prev if prev else "")
    if hook:
        env["SENSORIUM_CHILD_HOOK"] = hook
    if _STATE.spool_dir is not None:
        env["SENSORIUM_CHILD_SPOOL"] = str(_STATE.spool_dir)
    root = getattr(_STATE.tracer, "root", None) if _STATE.tracer else None
    env["SENSORIUM_CHILD_ROOT"] = str(root) if root else os.getcwd()
    env["SENSORIUM_CHILD_CFG"] = _cfg_blob()
    if frame is None:
        env.pop("SENSORIUM_PARENT_FRAME", None)
    else:
        env["SENSORIUM_PARENT_FRAME"] = str(frame)
    return env


def _as_env_list(env: dict) -> list:
    rows = []
    for key, value in env.items():
        if value is None:
            continue
        rows.append(os.fsencode(str(key)) + b"=" + os.fsencode(os.fsdecode(value)
                    if isinstance(value, bytes) else str(value)))
    return rows


def _env_marked(env) -> bool:
    if not env:
        return False
    try:
        items = list(env)
    except Exception:
        return False
    for item in items:
        try:
            if isinstance(item, bytes):
                text = item.decode("utf-8", "replace")
            else:
                text = str(item)
        except Exception:
            continue
        if text.startswith("SENSORIUM_CHILD_SPOOL="):
            return True
    return False


def _popen_shell(args, kwargs) -> bool:
    if "shell" in kwargs:
        return bool(kwargs.get("shell"))
    # Popen(args, bufsize, executable, stdin, stdout, stderr, preexec_fn,
    # close_fds, shell, ...). shell is the 9th argument after args.
    if len(args) > 8:
        return bool(args[8])
    return False


def _popen_head(args, kwargs):
    executable = kwargs.get("executable")
    if executable is None and len(args) > 2 and "executable" not in kwargs:
        # Only trust a positional executable when the caller actually
        # passed that many arguments. Index 2 is executable.
        if len(args) > 2:
            executable = args[2]
    if executable:
        return executable
    argv = args[0] if args else kwargs.get("args")
    if isinstance(argv, (list, tuple)):
        return argv[0] if argv else None
    return argv


def _inject_popen(args, kwargs):
    if not (_STATE.armed and _STATE.record):
        return args, kwargs
    if _popen_shell(args, kwargs):
        _STATE.non_python += 1
        return args, kwargs
    head = _popen_head(args, kwargs)
    if head is None or not _is_python(head):
        if head is not None:
            _STATE.non_python += 1
        return args, kwargs
    frame = _starter_frame(_STATE.tracer)
    if "env" in kwargs:
        kwargs = dict(kwargs)
        kwargs["env"] = _child_env(kwargs.get("env"), frame)
        return args, kwargs
    if len(args) > 10:
        copied = list(args)
        copied[10] = _child_env(copied[10], frame)
        return tuple(copied), kwargs
    kwargs = dict(kwargs)
    kwargs["env"] = _child_env(None, frame)
    return args, kwargs


def _install_popen() -> None:
    if _STATE.popen_orig is not None:
        return
    orig = subprocess.Popen.__init__

    def _init(self, *args, **kwargs):
        try:
            args, kwargs = _inject_popen(args, kwargs)
        except Exception:
            pass
        return orig(self, *args, **kwargs)

    subprocess.Popen.__init__ = _init
    _STATE.popen_orig = orig


def _install_fork_exec() -> None:
    if _STATE.fork_exec_orig is not None:
        return
    try:
        import _posixsubprocess
    except ImportError:
        return
    orig = _posixsubprocess.fork_exec

    def _fork_exec(args, exe_list, *rest, **kwargs):
        # vfork does not run at-fork hooks. A real fork inside fork_exec
        # does, and that child is about to exec: it must not open a spool.
        ident = threading.get_ident()
        _EXECING.add(ident)
        try:
            if not (_STATE.armed and _STATE.record):
                return orig(args, exe_list, *rest, **kwargs)
            head = None
            if isinstance(exe_list, (list, tuple)) and exe_list:
                head = exe_list[0]
            elif isinstance(args, (list, tuple)) and args:
                head = args[0]
            if not _is_python(head):
                return orig(args, exe_list, *rest, **kwargs)
            # env is the 4th argument after executable_list: close_fds,
            # pass_fds, cwd, env. Replacing None is what the child sees.
            # Mutating os.environ races other threads and is restored too
            # late to be the only path.
            if len(rest) >= 4 and not _env_marked(rest[3]):
                frame = _starter_frame(_STATE.tracer)
                if frame is None:
                    frame = _env_frame()
                updated = list(rest)
                if updated[3] is None:
                    updated[3] = _as_env_list(_child_env(None, frame))
                return orig(args, exe_list, *updated, **kwargs)
            return orig(args, exe_list, *rest, **kwargs)
        finally:
            _EXECING.discard(ident)

    _posixsubprocess.fork_exec = _fork_exec
    _STATE.fork_exec_orig = orig


def _install_spawn_exec() -> None:
    """posix_spawn and execve snapshot the environment before the audit
    hook runs, so the hook cannot add variables. Inject before the call.
    """
    if _STATE.spawn_orig is None and hasattr(os, "posix_spawn"):
        orig_spawn = os.posix_spawn

        def _posix_spawn(path, argv, env, *args, **kwargs):
            try:
                if (_STATE.armed and _STATE.record
                        and _is_python(path or (argv[0] if argv else None))):
                    env = _child_env(env, _starter_frame(_STATE.tracer))
            except Exception:
                pass
            return orig_spawn(path, argv, env, *args, **kwargs)

        os.posix_spawn = _posix_spawn
        _STATE.spawn_orig = orig_spawn
    if _STATE.execve_orig is None:
        orig_exec = os.execve

        def _execve(path, argv, env):
            try:
                if _STATE.armed and _STATE.record and _is_python(path):
                    env = _child_env(env, _starter_frame(_STATE.tracer))
            except Exception:
                pass
            return orig_exec(path, argv, env)

        os.execve = _execve
        _STATE.execve_orig = orig_exec


def _install_fork_hook() -> None:
    if _STATE.fork_hook:
        return
    if not hasattr(os, "register_at_fork"):
        return

    def _before() -> None:
        ident = threading.get_ident()
        if ident in _EXECING or not _STATE.armed:
            return
        if not _STATE.record:
            _PENDING[ident] = None
            return
        # A forkserver worker's stack is stdlib, so the user frame is the
        # one this process was spawned under, carried in the environment.
        frame = _starter_frame(_STATE.tracer)
        if frame is None:
            frame = _env_frame()
        _PENDING[ident] = frame

    def _after_child() -> None:
        ident = threading.get_ident()
        if ident in _EXECING or not _STATE.armed:
            return
        frame = _PENDING.pop(ident, None)
        if not _STATE.record:
            _silence_inherited()
            return
        if frame is None:
            frame = _env_frame()
        try:
            _redirect_fork_child(frame)
        except Exception:
            if _STATE.spool_dir is not None:
                _note_error(_STATE.spool_dir, "fork")

    def _after_parent() -> None:
        _PENDING.pop(threading.get_ident(), None)

    os.register_at_fork(before=_before, after_in_child=_after_child,
                        after_in_parent=_after_parent)
    _STATE.fork_hook = True


def _wrap_exit() -> None:
    if _STATE.exit_orig is not None:
        return
    orig = os._exit

    def _exit(code=0):
        try:
            _flush_current()
        except Exception:
            pass
        orig(code)

    os._exit = _exit
    _STATE.exit_orig = orig


def _write_hook(hook: Path) -> None:
    # Chain any sitecustomize already on the path, then record. The hook
    # directory is outside the traced tree, so this file is not a frame.
    hook.joinpath("sitecustomize.py").write_text(
        "import os, sys\n"
        "_here = os.path.dirname(os.path.abspath(__file__))\n"
        "def _chain():\n"
        "    try:\n"
        "        import importlib.util\n"
        "        for entry in list(sys.path):\n"
        "            if os.path.abspath(entry) == _here:\n"
        "                continue\n"
        "            cand = os.path.join(entry, 'sitecustomize.py')\n"
        "            if not os.path.isfile(cand):\n"
        "                continue\n"
        "            spec = importlib.util.spec_from_file_location(\n"
        "                '_sensorium_user_sitecustomize', cand)\n"
        "            if spec is None or spec.loader is None:\n"
        "                continue\n"
        "            mod = importlib.util.module_from_spec(spec)\n"
        "            spec.loader.exec_module(mod)\n"
        "            return\n"
        "    except Exception:\n"
        "        pass\n"
        "_chain()\n"
        "try:\n"
        "    if os.environ.get('SENSORIUM_CHILD_SPOOL'):\n"
        "        from sensorium.record.children import record_this_process\n"
        "        record_this_process()\n"
        "except Exception:\n"
        "    pass\n"
    )
