"""Where the C runtime lives, and the object file a link needs.

`locate` finds the directory that contains ``rt/sensorium_c_rt.c``.
`runtime_object` compiles it, once, with the flags the runtime was
measured with. The compiler wrapper is often the ``gcc`` on ``PATH``
while this runs, so the build below skips that shim and calls a real
``gcc``. A second copy of the object in one link is a duplicate symbol;
callers check for the path before adding it.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from sensorium import paths

_RUNTIME_C = Path("rt") / "sensorium_c_rt.c"
_RUNTIME_O = Path("rt") / "sensorium_c_rt.o"
_COMPILE = (
    "-O2", "-g", "-fno-omit-frame-pointer", "-fPIC",
    "-fno-instrument-functions",
    "-Wall", "-Wextra", "-Wno-frame-address", "-c",
)


class PackageError(Exception):
    """The runtime source is missing, or ``gcc`` could not compile it."""


def locate() -> Path:
    """Directory that contains ``rt/sensorium_c_rt.c``.

    An editable install lives in the repo, so walking from this file up
    to a directory that contains ``c/rt/sensorium_c_rt.c`` finds it. A
    wheel that cannot see the checkout is checked second, at
    ``sensorium/_c`` beside the installed package (the same shape as
    ``sensorium/_typescript``).
    """
    looked: list[str] = []
    here = Path(__file__).resolve().parent
    for directory in (here, *here.parents):
        candidate = directory / "c" / _RUNTIME_C
        looked.append(str(candidate))
        if candidate.is_file():
            return candidate.parent.parent
    wheel = _wheel_source()
    if wheel is not None:
        looked.append(str(wheel))
        if wheel.is_file():
            return wheel.parent.parent
    raise PackageError(
        "cannot find the C runtime rt/sensorium_c_rt.c. Looked for: "
        + "; ".join(looked))


def _wheel_source() -> Path | None:
    """``sensorium/_c/rt/sensorium_c_rt.c`` inside an installed package.

    ``None`` when this process has no importable ``sensorium`` package
    file to start from (the walk above is then the only place we looked).
    """
    try:
        import sensorium
    except ImportError:
        return None
    origin = getattr(sensorium, "__file__", None)
    if not origin:
        return None
    return Path(origin).resolve().parent / "_c" / _RUNTIME_C


def runtime_object() -> Path:
    """Compiled ``sensorium_c_rt.o``, rebuilding when it is older than the .c.

    The object is cached next to the source when that directory is
    writable, and otherwise under ``<trace root>/c-rt/``.
    """
    root = locate()
    src = root / _RUNTIME_C
    beside = root / _RUNTIME_O
    if _fresh(beside, src):
        return beside
    if _writable(beside.parent):
        try:
            _compile(src, beside)
            return beside
        except OSError:
            pass
    cache_dir = _cache_dir()
    cached = cache_dir / "sensorium_c_rt.o"
    if _fresh(cached, src):
        return cached
    _compile(src, cached)
    return cached


def _cache_dir() -> Path:
    """``<trace root>/c-rt``, created 0700 one level at a time.

    ``Path.mkdir(parents=True, mode=...)`` applies the mode only to the
    leaf, so a single call would leave the store root (where
    ``redaction.key`` lives) at the default. An existing directory is
    not chmod'ed.
    """
    root = paths.trace_root()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache = root / "c-rt"
    cache.mkdir(exist_ok=True, mode=0o700)
    return cache


def _fresh(obj: Path, src: Path) -> bool:
    if not obj.is_file():
        return False
    try:
        return obj.stat().st_mtime >= src.stat().st_mtime
    except OSError:
        return False


def _writable(directory: Path) -> bool:
    return os.access(directory, os.W_OK | os.X_OK)


def _compile(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
    cmd = [_real_gcc(), *_COMPILE, str(src), "-o", str(tmp)]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        raise PackageError(
            f"cannot run {cmd[0]} to compile {src}: {e.strerror}") from e
    if completed.returncode != 0:
        tmp.unlink(missing_ok=True)
        detail = (completed.stderr or completed.stdout or "").strip()
        raise PackageError(
            f"gcc failed to compile {src} (exit {completed.returncode})"
            + (f": {detail}" if detail else ""))
    try:
        os.replace(tmp, dest)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _real_gcc() -> str:
    """A ``gcc`` that is not this recorder's shim.

    During ``sensorium c run`` the shim directory is first on ``PATH``.
    Compiling the runtime with that ``gcc`` would re-enter the wrapper.
    """
    skipped = set()
    root = os.environ.get("SENSORIUM_C_ROOT")
    if root:
        skipped.add(os.path.abspath(os.path.join(root, "bin")))
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            directory = os.curdir
        if os.path.abspath(directory) in skipped:
            continue
        candidate = os.path.join(directory, "gcc")
        if _usable_gcc(candidate):
            return os.path.abspath(candidate)
    fallback = "/usr/bin/gcc"
    if _usable_gcc(fallback):
        return fallback
    raise PackageError(
        "gcc was not found on PATH; the C runtime cannot be built")


def _usable_gcc(path: str) -> bool:
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        return False
    return not _looks_like_wrapper(path)


def _looks_like_wrapper(path: str) -> bool:
    """True for the Python shims this driver writes, not for a real gcc."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
    except OSError:
        return False
    return b"sensorium.c.cc" in head or b"sensorium-cc" in head
