"""``sensorium c run``: shim the compilers, spawn, wait, convert.

The command after ``--`` is the user's, typed as they would type it. This
driver puts ``gcc``, ``cc`` and ``clang`` shims first on ``PATH``, points
``CC`` at the ``cc`` shim, and leaves the runtime off ``LDFLAGS`` (the
wrapper adds it once; a second copy is a duplicate symbol). The exit
status is the command's own, or ``128 + n`` when a signal ended it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from sensorium import paths
from sensorium.c import cc as cc_mod

SPOOL_DIR = "c-spool"
_SHIMS = ("gcc", "cc", "clang")


def run(args) -> int:
    command = list(getattr(args, "command", None) or [])
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("usage: sensorium c run [--strict] [--no-retval] -- "
              "<command> [args...]", file=sys.stderr)
        return 2
    strict = bool(getattr(args, "strict", False))
    no_retval = bool(getattr(args, "no_retval", False))
    inv_id = paths.new_run_id()
    spool = _make_spool(inv_id)
    bindir = spool / "bin"
    bindir.mkdir(mode=0o700)
    for name in _SHIMS:
        _write_shim(bindir / name)
    env = _env(bindir, spool, strict, no_retval)
    compiler_line = _compiler_version(env.get("SENSORIUM_C_CC", ""))
    started = time.time()
    side = {
        "invocation": inv_id,
        "driver_command": command,
        "cwd": os.getcwd(),
        "compiler": compiler_line,
        "start_ts": started,
        "no_retval": no_retval,
    }
    side_path = spool / "side.json"
    _write_json(side_path, side)
    try:
        proc = subprocess.Popen(
            command, env=env, stdin=None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        print(f"error: cannot start {command[0]}: {e.strerror}",
              file=sys.stderr)
        return 2
    threads = [
        threading.Thread(target=_pump,
                         args=(proc.stdout, spool / "stdout.bin",
                               _binary(sys.stdout)),
                         daemon=False),
        threading.Thread(target=_pump,
                         args=(proc.stderr, spool / "stderr.bin",
                               _binary(sys.stderr)),
                         daemon=False),
    ]
    for thread in threads:
        thread.start()
    side["root_pid"] = proc.pid
    _write_json(side_path, side)
    returncode = proc.wait()
    for thread in threads:
        thread.join()
    ended = time.time()
    if returncode < 0:
        harness = {"signal": -returncode, "basis": "waited"}
    else:
        harness = {"status": returncode, "basis": "waited"}
    side["end_ts"] = ended
    side["harness_exit"] = harness
    warnings = _read_warnings(spool / "build-warnings.txt")
    if warnings is not None:
        side["build_warnings"] = warnings
    _write_json(side_path, side)
    return _finish(spool, inv_id, returncode)


def _make_spool(inv_id: str) -> Path:
    """``<trace root>/c-spool/<invocation>``, each level mode 0700.

    One ``mkdir(parents=True, mode=0o700)`` would leave the store root,
    which holds ``redaction.key``, at the platform default. An existing
    directory is not chmod'ed.
    """
    root = paths.trace_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent = root / SPOOL_DIR
    parent.mkdir(exist_ok=True, mode=0o700)
    spool = parent / inv_id
    spool.mkdir(exist_ok=True, mode=0o700)
    return spool


def _write_shim(path: Path) -> None:
    """A Python script whose argv0 is ``gcc``, ``cc`` or ``clang``.

    The shebang is this interpreter. The body calls
    ``sensorium.c.cc.main``, so the wrapper sees the shim's argv0 and
    chooses the real compiler from that name.
    """
    exe = sys.executable or "/usr/bin/python3"
    text = (
        f"#!{exe}\n"
        "import sys\n"
        "from sensorium.c.cc import main\n"
        "sys.exit(main())\n"
    )
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _env(bindir: Path, spool: Path, strict: bool, no_retval: bool) -> dict:
    """The child's environment. The real ``cc`` is resolved first.

    ``SENSORIUM_C_CC`` is the previous ``CC`` when that value is an
    absolute path, otherwise the absolute ``cc`` found on the original
    ``PATH`` (before the shim directory is prepended). ``LDFLAGS`` is
    left alone: the wrapper links the runtime, and a second copy is a
    duplicate symbol.
    """
    original_path = os.environ.get("PATH", "")
    previous_cc = os.environ.get("CC", "")
    if os.path.isabs(previous_cc) and _real_compiler(previous_cc):
        real_cc = previous_cc
    else:
        real_cc = _which_cc(original_path)
    env = dict(os.environ)
    env["PATH"] = os.fspath(bindir) + os.pathsep + original_path
    env["CC"] = os.fspath(bindir / "cc")
    env["SENSORIUM_C_CC"] = real_cc
    env["SENSORIUM_C_ROOT"] = os.fspath(spool)
    if strict:
        env["SENSORIUM_C_STRICT"] = "1"
    else:
        env.pop("SENSORIUM_C_STRICT", None)
    if no_retval:
        env["SENSORIUM_C_NO_RETVAL"] = "1"
    else:
        env.pop("SENSORIUM_C_NO_RETVAL", None)
    flags = " ".join(cc_mod.INSTRUMENT_FLAGS)
    env["CFLAGS"] = _append_flags(env.get("CFLAGS", ""), flags)
    env["CMAKE_C_COMPILER_LAUNCHER"] = os.fspath(bindir / "cc")
    env["CMAKE_C_FLAGS"] = _append_flags(env.get("CMAKE_C_FLAGS", ""), flags)
    return env


def _append_flags(existing: str, flags: str) -> str:
    existing = existing.strip()
    if not existing:
        return flags
    return existing + " " + flags


def _which_cc(path: str) -> str:
    for directory in path.split(os.pathsep):
        if not directory:
            directory = os.curdir
        candidate = os.path.join(directory, "cc")
        if _real_compiler(candidate):
            return os.path.abspath(candidate)
    return "cc"


def _real_compiler(path: str) -> bool:
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        return False
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
    except OSError:
        return False
    return b"sensorium.c.cc" not in head and b"sensorium-cc" not in head


def _compiler_version(compiler: str) -> str:
    if not compiler:
        return "unknown"
    try:
        completed = subprocess.run(
            [compiler, "--version"], capture_output=True, text=True,
            timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    text = completed.stdout or completed.stderr or ""
    lines = text.splitlines()
    return lines[0] if lines else "unknown"


def _binary(stream):
    return getattr(stream, "buffer", stream)


def _pump(pipe, dest: Path, parent) -> None:
    """Copy a pipe to the parent stream and to ``dest`` as bytes arrive."""
    if pipe is None:
        return
    fd = os.open(dest, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        while True:
            block = pipe.read(1 << 16)
            if not block:
                break
            os.write(fd, block)
            if parent is None:
                continue
            try:
                parent.write(block)
                parent.flush()
            except Exception:
                parent = None
    finally:
        os.close(fd)
        pipe.close()


def _read_warnings(path: Path) -> list[str] | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return text.splitlines()


def _write_json(path: Path, payload: dict) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        os.write(fd, text.encode())
    finally:
        os.close(fd)
    os.replace(tmp, path)


def _finish(spool: Path, inv_id: str, returncode: int) -> int:
    shown = _shown_exit(returncode)
    status = 128 + (-returncode) if returncode < 0 else returncode
    if not _pid_dirs(spool):
        print(f"invocation: {inv_id}  traces: 0  exit: {shown}", flush=True)
        print("sensorium c: no instrumented process ran (the command did "
              "not start a binary linked with the C runtime)",
              file=sys.stderr)
        return status
    try:
        from sensorium.c.convert import convert_root
    except ImportError as e:
        return _convert_failed(e, returncode, shown)
    try:
        result = convert_root(spool)
    except Exception as e:
        return _convert_failed(e, returncode, shown)
    try:
        runs = _runs_from(result)
    except (TypeError, ValueError) as e:
        return _convert_failed(e, returncode, shown)
    for run_id, trace in runs:
        print(f"run: {run_id}", flush=True)
        print(f"trace: {trace}", flush=True)
    print(f"invocation: {inv_id}  traces: {len(runs)}  exit: {shown}",
          flush=True)
    return status


def _convert_failed(exc: BaseException, returncode: int, shown: str) -> int:
    """Exit 2. A failed command is reported as well, not replaced."""
    print(f"error: {exc}", file=sys.stderr)
    if returncode != 0:
        print(f"sensorium c: command exited with {shown}", file=sys.stderr)
    return 2


def _shown_exit(returncode: int) -> str:
    if returncode < 0:
        return f"signal {-returncode}"
    return str(returncode)


def _pid_dirs(spool: Path) -> list[Path]:
    """Immediate children whose names are process ids.

    ``bin`` and the driver's own files are not pid directories. Nothing
    in here means the command never started a binary linked with the
    runtime, which is not by itself a bad call.
    """
    found = []
    try:
        children = list(spool.iterdir())
    except OSError:
        return found
    for child in children:
        if child.is_dir() and child.name.isdigit():
            found.append(child)
    found.sort(key=lambda p: int(p.name))
    return found


def _runs_from(result) -> list[tuple[str, Path]]:
    """Run ids and trace paths from whatever ``convert_root`` returned.

    Accepted shapes: a list of run ids, a list of ``*.db`` paths, a list
    of ``(run_id, path)`` pairs, a list of objects or dicts with
    ``run_id`` and ``trace``, or a mapping of run id to path.
    """
    if result is None:
        return []
    if isinstance(result, dict):
        if "runs" in result and not any(
                key in result for key in ("run_id", "id", "trace")):
            return _runs_from(result["runs"])
        if "run_id" in result or "trace" in result or "id" in result:
            return [_one_run(result)]
        out = []
        for key, value in result.items():
            out.append(_one_run((key, value)))
        return out
    if isinstance(result, (str, Path)):
        return [_one_run(result)]
    out = []
    for item in result:
        out.append(_one_run(item))
    return out


def _one_run(item) -> tuple[str, Path]:
    if isinstance(item, tuple) and len(item) == 2:
        run_id, trace = item
        return str(run_id), Path(trace)
    if isinstance(item, (str, Path)):
        text = os.fspath(item)
        path = Path(text)
        if text.endswith(".db"):
            return path.stem, path
        return text, paths.traces_dir() / f"{text}.db"
    run_id = getattr(item, "run_id", None)
    trace = getattr(item, "trace", None)
    if trace is None:
        trace = getattr(item, "path", None)
    if isinstance(item, dict):
        run_id = item.get("run_id", item.get("id", run_id))
        trace = item.get("trace", item.get("path", trace))
    if run_id is None and trace is not None:
        run_id = Path(trace).stem
    if run_id is None:
        raise ValueError(f"convert_root returned {item!r}, which has no run id")
    if trace is None:
        trace = paths.traces_dir() / f"{run_id}.db"
    return str(run_id), Path(trace)
