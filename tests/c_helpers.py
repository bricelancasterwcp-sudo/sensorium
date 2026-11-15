"""Shared process helpers for the C recorder tests.

`SENSORIUM_DIR` is always a directory the test passes in. Nothing here
writes `~/.sensorium`. `run_c` is `tests.helpers.run_cli` plus a timeout,
so a stuck trampoline fails the test instead of hanging the suite.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

from sensorium.store.reader import Trace

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "c" / "sample"


class Recorded(NamedTuple):
    proc: subprocess.CompletedProcess
    trace: Trace
    sdir: Path
    work: Path


def _child_env(sdir, env_extra=None, env_drop=()):
    """Environment for a recorder subprocess.

    `PYTHONPATH` is made absolute before the child changes directory.
    A relative `src` entry would otherwise point at the temp work tree,
    and `python -m sensorium` would not import this checkout.
    """
    env = dict(os.environ)
    for key in env_drop:
        env.pop(key, None)
    if env_extra:
        env.update(env_extra)
    env["SENSORIUM_DIR"] = str(sdir)
    import sensorium
    src = str(Path(sensorium.__file__).resolve().parents[1])
    parts = []
    seen = set()
    for part in [src, *env.get("PYTHONPATH", "").split(os.pathsep)]:
        if not part or part in seen:
            continue
        path = Path(part)
        if not path.is_absolute():
            path = Path.cwd() / path
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        parts.append(key)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def run_c(args, cwd, sdir, env_extra=None, env_drop=(), timeout=60):
    """Run `python -m sensorium` with `SENSORIUM_DIR` pointed at `sdir`."""
    env = _child_env(sdir, env_extra, env_drop)
    Path(sdir).mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run(
            [sys.executable, "-m", "sensorium", *args],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = e.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        pytest.fail(f"timed out after {timeout}s: {args}\n{out}\n{err}")


def cc(args, cwd, argv0="sensorium-cc", env_extra=None, timeout=60):
    """Invoke `sensorium.c.cc:main` the way the console script does.

    `argv0` is the wrapper's own name. The CMake launcher form passes the
    real compiler as the first argument instead, and leaves `argv0` as
    `sensorium-cc`.
    """
    sdir = Path(cwd) / "sdir"
    sdir.mkdir(parents=True, exist_ok=True)
    env = _child_env(sdir, env_extra)
    # `python -c <script> <argv0> <args...>`: sys.argv[0] is `-c`, so the
    # wrapper's own name is passed as the next argument and then installed
    # as argv[0]. A shim named `clang` and a CMake launcher are different
    # tests; both go through this.
    script = (
        "import inspect, sys\n"
        "from sensorium.c.cc import main\n"
        "argv0 = sys.argv[1]\n"
        "args = sys.argv[2:]\n"
        "sys.argv = [argv0, *args]\n"
        "n = len(inspect.signature(main).parameters)\n"
        "rc = main(args) if n else main()\n"
        "raise SystemExit(0 if rc is None else rc)\n"
    )
    try:
        return subprocess.run(
            [sys.executable, "-c", script, argv0, *args],
            cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"sensorium-cc timed out: {args}\n{e.stdout}\n{e.stderr}")


def _trace_paths(sdir: Path) -> list[Path]:
    directory = Path(sdir) / "traces"
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.db"))


def open_new_traces(sdir: Path, before: set[str]) -> list[Trace]:
    opened = []
    for path in _trace_paths(sdir):
        if path.name in before:
            continue
        try:
            opened.append(Trace.open(path))
        except Exception as e:
            pytest.fail(f"could not open {path}: {type(e).__name__}: {e}")
    return opened


def _pick(opened: list[Trace], binary: str) -> Trace:
    named = []
    for trace in opened:
        argv = [str(a) for a in (trace.meta.get("argv") or [])]
        if any(a == f"./{binary}" or a.endswith("/" + binary) for a in argv):
            named.append(trace)
    pool = named or opened
    return max(pool, key=lambda t: len(t.events()))


def build_and_run(work, src, sdir, argv=(), link=(), binary="prog",
                  run_env=None, env_drop=(), timeout=60) -> Recorded:
    """Compile `src` with `sensorium c run -- gcc ...` and run the binary.

    The compile and the run are separate driver invocations. The returned
    trace is the one the run added, not a trace the compiler left behind.
    """
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    src = Path(src)
    dest = work / src.name
    if src.resolve() != dest.resolve():
        shutil.copy(src, dest)
    compiled = run_c(
        ["c", "run", "--", "gcc", "-O0", "-g", *link, src.name, "-o", binary],
        work, sdir, timeout=timeout)
    if compiled.returncode != 0:
        pytest.fail(
            f"compile failed ({compiled.returncode}):\n"
            f"{compiled.stdout}\n{compiled.stderr}")
    before = {p.name for p in _trace_paths(sdir)}
    proc = run_c(
        ["c", "run", "--", f"./{binary}", *argv],
        work, sdir, env_extra=run_env, env_drop=env_drop, timeout=timeout)
    opened = open_new_traces(sdir, before)
    if not opened:
        pytest.fail(
            f"no trace after running {binary} (exit {proc.returncode}):\n"
            f"{proc.stdout}\n{proc.stderr}")
    return Recorded(proc, _pick(opened, binary), Path(sdir), work)


def calls(trace: Trace, qual: str) -> list:
    out = []
    for event in trace.events("CALL"):
        if event.code_id is None:
            continue
        name = trace.code(event.code_id).qualname
        if name == qual or name.endswith("." + qual) or name.endswith("::" + qual):
            out.append(event)
    return out


def returns(trace: Trace, qual: str) -> list:
    out = []
    for event in trace.events("RETURN"):
        if event.code_id is None:
            continue
        name = trace.code(event.code_id).qualname
        if name == qual or name.endswith("." + qual) or name.endswith("::" + qual):
            out.append(event)
    return out


def gcc_or_skip() -> None:
    if shutil.which("gcc") is None:
        pytest.skip("gcc is not on PATH")
