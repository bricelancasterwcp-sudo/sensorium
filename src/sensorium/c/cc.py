"""``sensorium-cc``: the compiler wrapper and the ``gcc``/``cc``/``clang`` shim.

A build sees this process where it expected a compiler. Probe flags
(``--version``, ``-E``, and the rest of the list in ``_passthrough``) are
handed to the real compiler unchanged. A compile or a link gets the
instrument flags appended, so they win over a default earlier in the
command, and a link also gets the C runtime.

The real compiler is never this file and never a shim directory. The
wrapper is Python, so it is not instrumented.
"""
from __future__ import annotations

import inspect
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

from sensorium.c import pkg

#: Appended to every compile and every link. Last, so they override a
#: default of the opposite flag. Duplicate copies are harmless.
#: The exclude-file-list entry is gcc only. Clang 21 rejects it as an
#: unknown argument, so a clang compile does not receive it.
INSTRUMENT_FLAGS = [
    "-g",
    "-fno-omit-frame-pointer",
    "-fno-inline",
    "-fno-optimize-sibling-calls",
    "-finstrument-functions",
    "-finstrument-functions-exclude-file-list=/usr/include,/usr/lib",
]
_EXCLUDE_FILE_LIST = "-finstrument-functions-exclude-file-list"

_SHIM_NAMES = {"gcc", "cc", "clang"}
_COMPILER_BASENAME = re.compile(r"^(?:gcc|cc|clang|clang-\d+|.+-gcc)$")
_TAKES_ARG = {
    "-o", "-I", "-L", "-l", "-D", "-U", "-x", "-include", "-imacros",
    "-isystem", "-idirafter", "-iprefix", "-iwithprefix",
    "-iwithprefixbefore", "-isysroot", "-imultilib", "-MF", "-MT", "-MQ",
    "-Xlinker", "-Xpreprocessor", "-Xassembler", "-b", "-B", "-T", "-u",
    "-aux-info", "-include-directory",
}
_SCRIPT = os.path.realpath(__file__)


class CompilerError(Exception):
    """The real compiler could not be named or found."""


def instrument_flags(compiler: str) -> list[str]:
    """Instrument flags this compiler accepts.

    gcc keeps the exclude-file-list entry so inlines from ``/usr/include``
    and ``/usr/lib`` stay out of the trace. Clang has no such flag.
    """
    if _is_clang(compiler):
        return [flag for flag in INSTRUMENT_FLAGS if not _exclude_file_list(flag)]
    return list(INSTRUMENT_FLAGS)


def _compile_args(compiler: str, args: list[str]) -> list[str]:
    """``args`` plus instrument flags, without a flag this compiler rejects.

    ``CFLAGS`` may already carry the gcc exclude-file-list entry. Drop
    that token when the real compiler is clang, then append the flags
    this compiler accepts.
    """
    if _is_clang(compiler):
        args = [arg for arg in args if not _exclude_file_list(arg)]
    return [*args, *instrument_flags(compiler)]


def _exclude_file_list(arg: str) -> bool:
    return arg == _EXCLUDE_FILE_LIST or arg.startswith(_EXCLUDE_FILE_LIST + "=")


def _is_clang(compiler: str) -> bool:
    """True for clang, including a ``cc`` symlink whose target is clang."""
    names = [os.path.basename(compiler).lower()]
    try:
        linked = os.path.basename(os.path.realpath(compiler)).lower()
    except OSError:
        linked = ""
    if linked and linked not in names:
        names.append(linked)
    return any(name == "clang" or name.startswith("clang-") for name in names)


def main(argv: list[str] | None = None) -> int:
    """Run the real compiler, with instrument flags unless this is a probe.

    ``argv`` is either a full ``sys.argv`` (program name first) or just the
    arguments after it, as in ``main(["--version"])``. ``None`` reads
    ``sys.argv``, which is what the console script and the shims do.
    """
    try:
        argv0, args = _invocation(argv)
        requested, args = _select_compiler(argv0, args)
        compiler = _resolve(requested, argv0)
    except CompilerError as e:
        print(f"sensorium-cc: error: {e}", file=sys.stderr)
        return 2
    args = _expand_responses(args)
    if _passthrough(args):
        return _invoke([compiler, *args])
    warnings = _warnings(args)
    for line in warnings:
        _emit(line)
    if warnings and _strict():
        return 2
    cmd = [compiler, *_compile_args(compiler, args)]
    linking = _links(args)
    if linking:
        try:
            runtime = pkg.runtime_object()
        except pkg.PackageError as e:
            print(f"sensorium-cc: error: {e}", file=sys.stderr)
            return 2
        if not _has_runtime(args, runtime):
            cmd.append(os.fspath(runtime))
        cmd.extend(["-ldl", "-pthread"])
    status = _invoke(cmd)
    if status == 0 and linking:
        plan_status = _after_link(args)
        if plan_status is not None:
            return plan_status
    return status


def _invocation(argv: list[str] | None) -> tuple[str, list[str]]:
    """``(argv0, args)``. Args-only lists get the running interpreter's argv0.

    A list whose first element is already a program (a shim named gcc, cc
    or clang, this file, or ``sensorium-cc``) is a full argv. Anything else,
    including ``["--version"]``, is the compiler's own arguments.
    """
    if argv is None:
        full = list(sys.argv)
    elif not argv or argv[0].startswith("-") or not _looks_like_program(argv[0]):
        full = [sys.argv[0], *argv]
    else:
        full = list(argv)
    if not full:
        return "", []
    return full[0], full[1:]


def _looks_like_program(token: str) -> bool:
    base = os.path.basename(token)
    if base in _SHIM_NAMES or base in {"sensorium-cc", "cc.py", "__main__.py"}:
        return True
    try:
        return os.path.isfile(token) and os.path.samefile(token, _SCRIPT)
    except OSError:
        return False


def _select_compiler(argv0: str, args: list[str]) -> tuple[str, list[str]]:
    """Which compiler the user asked for, and the args with that name removed.

    ``argv[1]`` wins when it is an executable or a compiler basename, which
    is how a launcher (``shim cc /usr/bin/gcc ...``) names the real tool.
    Otherwise a shim invoked as ``gcc``, ``cc`` or ``clang`` asks for that
    tool. Anything else uses ``$SENSORIUM_C_CC`` or ``cc``.
    """
    if args and _is_compiler_token(args[0]):
        return args[0], args[1:]
    base = os.path.basename(argv0) if argv0 else ""
    if base in _SHIM_NAMES:
        if _usable_real_compiler(argv0):
            return argv0, list(args)
        return base, list(args)
    env = os.environ.get("SENSORIUM_C_CC", "")
    if env:
        return env, list(args)
    return "cc", list(args)


def _is_compiler_token(token: str) -> bool:
    if not token or token.startswith("-"):
        return False
    if _COMPILER_BASENAME.match(os.path.basename(token)):
        return True
    return _usable_real_compiler(token) or (
        os.path.isfile(token) and os.access(token, os.X_OK)
        and not os.path.isabs(token) and not _looks_like_wrapper(token))


def _resolve(requested: str, argv0: str) -> str:
    """Absolute path of the real compiler, never this shim and never this file.

    An absolute real compiler is used as named. ``cc`` and ``gcc`` prefer
    ``$SENSORIUM_C_CC`` when that variable is an absolute compiler, which is
    how a shim named ``cc`` reaches the ``cc`` that was on ``PATH`` before
    the shim directory was prepended. The search skips the shim's directory
    and skips this script, so the wrapper cannot recurse.
    """
    base = os.path.basename(requested) if requested else "cc"
    env_cc = os.environ.get("SENSORIUM_C_CC", "")
    if os.path.isabs(requested) and _usable_real_compiler(requested):
        return os.path.abspath(requested)
    if base in {"cc", "gcc"} and _usable_real_compiler(env_cc):
        return os.path.abspath(env_cc)
    skip = _skip_dirs(argv0)
    for directory in _path_dirs():
        if os.path.abspath(directory) in skip:
            continue
        candidate = os.path.join(directory, base)
        if not _usable_real_compiler(candidate):
            continue
        if _is_this_script(candidate) or _same_file(candidate, argv0):
            continue
        return os.path.abspath(candidate)
    raise CompilerError(
        f"cannot find the real compiler {base!r} on PATH")


def _usable_real_compiler(path: str) -> bool:
    if not path or not os.path.isabs(path):
        return False
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        return False
    if _is_this_script(path) or _looks_like_wrapper(path):
        return False
    return True


def _skip_dirs(argv0: str) -> set[str]:
    skipped = set()
    root = os.environ.get("SENSORIUM_C_ROOT")
    if root:
        skipped.add(os.path.abspath(os.path.join(root, "bin")))
    if argv0:
        base = os.path.basename(argv0)
        if base in _SHIM_NAMES or _looks_like_wrapper(argv0):
            skipped.add(os.path.dirname(os.path.abspath(argv0)))
    return skipped


def _path_dirs() -> list[str]:
    raw = os.environ.get("PATH", "")
    dirs = []
    for directory in raw.split(os.pathsep):
        dirs.append(directory or os.curdir)
    return dirs


def _looks_like_wrapper(path: str) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(400)
    except OSError:
        return False
    return b"sensorium.c.cc" in head or b"sensorium-cc" in head


def _is_this_script(path: str) -> bool:
    try:
        return os.path.realpath(path) == _SCRIPT
    except OSError:
        return False


def _same_file(path: str, other: str) -> bool:
    if not path or not other:
        return False
    try:
        return os.path.samefile(path, other)
    except OSError:
        return os.path.abspath(path) == os.path.abspath(other)


def _passthrough(args: list[str]) -> bool:
    """Probes and preprocess-only commands run the real compiler unchanged.

    ``-v`` is a probe only when it is the only argument. ``gcc -v file.c``
    is a verbose compile and is instrumented.
    """
    if args == ["-v"]:
        return True
    for arg in args:
        if arg in {"--version", "-dumpmachine", "-dumpversion", "-###",
                   "--help", "-E"}:
            return True
        if arg.startswith("-print-") or arg.startswith("--print-"):
            return True
    return False


def _links(args: list[str]) -> bool:
    """True when this command produces a final image (executable or shared).

    ``-c``, ``-S`` and ``-E`` do not link. A pure ``-M`` / ``-MM`` scan does
    not either (``-MD`` / ``-MMD`` still compile, and are not this case).
    ``-fsyntax-only`` produces no image. ``-shared`` still links.
    """
    if any(arg in {"-c", "-S", "-E", "-fsyntax-only"} for arg in args):
        return False
    if "-M" in args or "-MM" in args:
        return False
    return True


def _warnings(args: list[str]) -> list[str]:
    """One line per reason this build will not yield reliable values.

    The effective ``-O`` is the last ``-O*`` on the command. No ``-O`` at
    all is ``-O0``. ``-fcf-protection`` other than ``=none`` turns on CET;
    a shadow stack makes the return trampoline record nothing.
    """
    lines = []
    level = _opt_level(args)
    if level not in {"0", "g"}:
        subject = _subject(args)
        lines.append(
            f"sensorium-cc: warning: {subject}: built at -O{level}; "
            "argument and return values are reliable at -O0 or -Og")
    if _cet_on(args):
        lines.append(
            "sensorium-cc: warning: CET/cf-protection is on; a shadow "
            "stack disables return-value recording")
    return lines


def _opt_level(args: list[str]) -> str:
    level = "0"
    for arg in args:
        if not arg.startswith("-O"):
            continue
        suffix = arg[2:]
        # A bare ``-O`` is gcc's ``-O1``.
        level = "1" if suffix == "" else suffix
    return level


def _cet_on(args: list[str]) -> bool:
    chosen = None
    for arg in args:
        if arg == "-fcf-protection" or arg.startswith("-fcf-protection="):
            chosen = arg
    if chosen is None:
        return False
    return chosen != "-fcf-protection=none"


def _strict() -> bool:
    """``SENSORIUM_C_STRICT`` set to anything other than empty or ``0``."""
    value = os.environ.get("SENSORIUM_C_STRICT")
    if value is None or value == "" or value == "0":
        return False
    return True


def _subject(args: list[str]) -> str:
    output = _explicit_output(args)
    if output:
        return output
    first = _first_input(args)
    if first:
        return first
    return "a.out"


def _explicit_output(args: list[str]) -> str | None:
    found = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-o" and i + 1 < len(args):
            found = args[i + 1]
            i += 2
            continue
        if arg.startswith("-o") and len(arg) > 2:
            found = arg[2:]
            i += 1
            continue
        i += 1
    return found


def _first_input(args: list[str]) -> str | None:
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _TAKES_ARG:
            i += 2
            continue
        if arg.startswith("-"):
            i += 1
            continue
        return arg
    return None


def _emit(line: str) -> None:
    """Print one warning, and append it to ``$SENSORIUM_C_ROOT`` when set.

    The file is created mode 0600. A failure to append is itself a warning
    and does not change the compiler's status.
    """
    print(line, file=sys.stderr)
    root = os.environ.get("SENSORIUM_C_ROOT")
    if not root:
        return
    path = os.path.join(root, "build-warnings.txt")
    try:
        fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    except OSError as e:
        print(f"sensorium-cc: warning: cannot append {path}: {e.strerror}",
              file=sys.stderr)
        return
    try:
        os.write(fd, (line + "\n").encode())
    finally:
        os.close(fd)


def _has_runtime(args: list[str], runtime: Path) -> bool:
    real = os.path.realpath(runtime)
    for arg in args:
        if arg == os.fspath(runtime) or arg == real:
            return True
        try:
            if os.path.isfile(arg) and os.path.realpath(arg) == real:
                return True
        except OSError:
            continue
    return False


class _PlanFallback(Exception):
    """A symbol plan was written because ``sensorium.c.plan`` is absent.

    Not a failed link: the image has a readable plan, with empty
    arguments. Strict mode still compiles ``-O0``. A planner that imports
    and then fails is a different error, and strict mode exits 2 for that.
    """


def _after_link(args: list[str]) -> int | None:
    """Write ``<output>.scplan``. ``None`` means keep the compiler's status.

    A planner that fails prints a warning and still returns the compiler's
    status: the program records calls with empty arguments.
    ``SENSORIUM_C_STRICT`` turns that failure into exit 2. ``-shared`` and
    a normal executable are the same case. Output ``-`` (the compiler
    wrote stdout) has no image to plan.
    """
    output = _explicit_output(args) or "a.out"
    if output == "-":
        _emit("sensorium-cc: warning: link wrote stdout; no capture plan")
        return 2 if _strict() else None
    try:
        _call_plan(output)
    except _PlanFallback:
        _emit(f"sensorium-cc: warning: {output}: sensorium.c.plan is not "
              "available; wrote a symbol plan and argument values will "
              "be empty")
        return None
    except Exception as e:
        detail = " ".join(str(e).split())
        _emit(f"sensorium-cc: warning: {output}: capture plan failed: "
              f"{detail}")
        if _strict():
            return 2
    return None


def _call_plan(output: str) -> None:
    dest = output + ".scplan"
    try:
        from sensorium.c.plan import write_image_plan
    except ImportError as e:
        _write_symbol_plan(output)
        raise _PlanFallback(str(e)) from e
    try:
        params = [
            p for p in inspect.signature(write_image_plan).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
    except (TypeError, ValueError):
        params = []
    if len(params) >= 2:
        write_image_plan(output, dest)
    else:
        try:
            write_image_plan(output, dest)
        except TypeError:
            write_image_plan(output)
    if not os.path.isfile(dest):
        raise OSError(f"capture plan was not written to {dest}")


def _write_symbol_plan(image: str) -> None:
    """Plan from the ELF symbol table when the DWARF planner is not there.

    Addresses are ``st_value``, which for a linked image is the
    unrelocated address the runtime adds the load bias to. Parameters are
    empty: without DWARF the slot is not known, and the value is unread.
    """
    from sensorium.c.format import RET_INT, FuncPlan, write_plan

    addrs = _elf_func_addrs(image)
    if not addrs:
        raise OSError(f"{image}: no function symbols to plan")
    write_plan(image + ".scplan",
               [FuncPlan(addr, RET_INT, 1, 8, ()) for addr in addrs])


def _elf_func_addrs(path: str) -> list[int]:
    """Defined ``STT_FUNC`` values in an ELF64 little-endian image."""
    import struct

    data = Path(path).read_bytes()
    if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise OSError(f"{path}: not a little-endian ELF64 file")
    e_shoff = struct.unpack_from("<Q", data, 40)[0]
    e_shentsize = struct.unpack_from("<H", data, 58)[0]
    e_shnum = struct.unpack_from("<H", data, 60)[0]
    if e_shentsize < 64 or e_shnum == 0:
        raise OSError(f"{path}: no section headers")
    sym_off = None
    for index in range(e_shnum):
        off = e_shoff + index * e_shentsize
        if off + 64 > len(data):
            break
        sh_type = struct.unpack_from("<I", data, off + 4)[0]
        if sh_type == 2:  # SHT_SYMTAB
            sym_off = off
            break
    if sym_off is None:
        for index in range(e_shnum):
            off = e_shoff + index * e_shentsize
            sh_type = struct.unpack_from("<I", data, off + 4)[0]
            if sh_type == 11:  # SHT_DYNSYM
                sym_off = off
                break
    if sym_off is None:
        raise OSError(f"{path}: no symbol table")
    sh_offset = struct.unpack_from("<Q", data, sym_off + 24)[0]
    sh_size = struct.unpack_from("<Q", data, sym_off + 32)[0]
    sh_entsize = struct.unpack_from("<Q", data, sym_off + 56)[0] or 24
    addrs: list[int] = []
    seen: set[int] = set()
    end = min(len(data), sh_offset + sh_size)
    cursor = sh_offset
    while cursor + 24 <= end:
        st_info = data[cursor + 4]
        st_shndx = struct.unpack_from("<H", data, cursor + 6)[0]
        st_value = struct.unpack_from("<Q", data, cursor + 8)[0]
        if (st_info & 0xF) == 2 and st_shndx != 0 and st_value not in seen:
            if st_value != 0:
                seen.add(st_value)
                addrs.append(st_value)
        cursor += sh_entsize
    return addrs


def _invoke(cmd: list[str]) -> int:
    try:
        completed = subprocess.run(cmd)
    except OSError as e:
        print(f"sensorium-cc: error: cannot run {cmd[0]}: {e.strerror}",
              file=sys.stderr)
        return 2
    code = completed.returncode
    if code < 0:
        return 128 + (-code)
    return code


def _expand_responses(args: list[str], depth: int = 0,
                      seen: set[str] | None = None) -> list[str]:
    """Splice ``@file`` arguments the way gcc does, one file at a time.

    A missing file is left for the real compiler to diagnose. Cycles and
    a deep nest are left unexpanded rather than followed forever.
    """
    if depth > 8:
        return list(args)
    if seen is None:
        seen = set()
    out: list[str] = []
    for arg in args:
        if not (arg.startswith("@") and len(arg) > 1):
            out.append(arg)
            continue
        path = arg[1:]
        if not os.path.isfile(path):
            out.append(arg)
            continue
        real = os.path.realpath(path)
        if real in seen:
            out.append(arg)
            continue
        seen.add(real)
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            parts = shlex.split(text, posix=True)
        except (OSError, ValueError):
            out.append(arg)
            continue
        out.extend(_expand_responses(parts, depth + 1, seen))
    return out


if __name__ == "__main__":
    sys.exit(main())
