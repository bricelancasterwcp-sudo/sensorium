"""`sensorium-cc` and `sensorium c run`.

The wrapper exits 0 on `--version`, writes a `.scplan` for an `-O0`
hello, warns on stderr for `-O2`, and returns 2 for `-O2` when
`SENSORIUM_C_STRICT=1`. `sensorium c run` records a trace whose tree
contains `main`, and the program's stdout is both forwarded and stored.
make, cmake and meson go through the same command and skip by name
when that tool is not installed. clang fails the test only when
`SENSORIUM_C_REQUIRE_CLANG=1` and clang is absent; otherwise that part
skips by name.
"""
import os
import shutil
from pathlib import Path

import pytest

from sensorium.c.format import read_plan
from tests.c_helpers import SAMPLES, cc, gcc_or_skip, open_new_traces, run_c

HELLO = '#include <stdio.h>\nint main(void) {\n    printf("hello-from-c\\n");\n    return 0;\n}\n'


def _hello(directory: Path) -> Path:
    path = directory / "hello.c"
    path.write_text(HELLO)
    return path


def test_wrapper_version_returns_0(tmp_path):
    proc = cc(["--version"], tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_wrapper_o0_writes_a_plan(tmp_path):
    """An `-O0` link leaves `<image>.scplan` beside the binary, readable."""
    gcc_or_skip()
    _hello(tmp_path)
    binary = tmp_path / "hello"
    proc = cc(["-O0", "hello.c", "-o", str(binary)], tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    plan = Path(str(binary) + ".scplan")
    plans = list(tmp_path.rglob("*.scplan"))
    assert plan.is_file(), f"expected {plan}, found {plans}\n{proc.stderr}"
    funcs = read_plan(plan)
    assert funcs, funcs
    assert binary.is_file()


def test_wrapper_o2_warns_on_stderr(tmp_path):
    gcc_or_skip()
    _hello(tmp_path)
    proc = cc(["-O2", "hello.c", "-o", str(tmp_path / "hello")], tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    err = proc.stderr.lower()
    assert err.strip(), "expected a warning on stderr for -O2"
    assert ("o2" in err or "optim" in err or "debug" in err), proc.stderr


def test_strict_o2_returns_2(tmp_path):
    gcc_or_skip()
    _hello(tmp_path)
    proc = cc(["-O2", "hello.c", "-o", str(tmp_path / "hello")], tmp_path,
              env_extra={"SENSORIUM_C_STRICT": "1"})
    assert proc.returncode == 2, proc.stdout + proc.stderr


def test_strict_still_compiles_o0(tmp_path):
    """Strict refuses optimized builds. It does not refuse a debug build."""
    gcc_or_skip()
    _hello(tmp_path)
    proc = cc(["-O0", "hello.c", "-o", str(tmp_path / "hello")], tmp_path,
              env_extra={"SENSORIUM_C_STRICT": "1"})
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_exclude_file_list_is_not_passed_to_clang():
    """Clang 21 rejects ``-finstrument-functions-exclude-file-list``."""
    from sensorium.c.cc import _compile_args, instrument_flags

    gcc = instrument_flags("/usr/bin/gcc")
    clang = instrument_flags("/usr/bin/clang-21")
    assert any(flag.startswith("-finstrument-functions-exclude-file-list")
               for flag in gcc)
    assert "-finstrument-functions" in clang
    assert not any("exclude-file-list" in flag for flag in clang)
    built = _compile_args("/usr/bin/clang", [
        "-O0",
        "-finstrument-functions-exclude-file-list=/usr/include,/usr/lib",
        "hello.c",
    ])
    assert not any("exclude-file-list" in arg for arg in built)
    assert "-finstrument-functions" in built
    assert built[-1] != "hello.c"


def test_clang_o0_writes_a_plan(tmp_path):
    """`CMAKE_C_COMPILER_LAUNCHER` prefixes the real compiler, so argv is
    `sensorium-cc <clang> -O0 hello.c -o hello`."""
    clang = shutil.which("clang")
    require = os.environ.get("SENSORIUM_C_REQUIRE_CLANG") == "1"
    if clang is None:
        if require:
            pytest.fail("SENSORIUM_C_REQUIRE_CLANG=1 but clang is not on PATH")
        pytest.skip("clang is not on PATH")
    _hello(tmp_path)
    binary = tmp_path / "hello"
    proc = cc([clang, "-O0", "hello.c", "-o", str(binary)], tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    plan = Path(str(binary) + ".scplan")
    assert plan.is_file(), list(tmp_path.rglob("*.scplan"))
    assert read_plan(plan)


def test_run_records_hello_and_forwards_stdout(tmp_path):
    """`sensorium c run -- ./hello` records main, stores stdout, and prints it."""
    gcc_or_skip()
    _hello(tmp_path)
    sdir = tmp_path / "sdir"
    built = cc(["-O0", "hello.c", "-o", str(tmp_path / "hello")], tmp_path)
    assert built.returncode == 0, built.stdout + built.stderr
    before = {p.name for p in (sdir / "traces").glob("*.db")} if (sdir / "traces").is_dir() else set()
    # The wrapper test used this sdir too. Snapshot whatever is already there.
    proc = run_c(["c", "run", "--", "./hello"], tmp_path, sdir)
    assert "hello-from-c" in proc.stdout, proc.stdout + proc.stderr
    opened = open_new_traces(sdir, before)
    assert opened, proc.stdout + proc.stderr
    trace = opened[-1]
    text = "".join(data for _i, stream, data in trace.output_chunks()
                   if stream == "stdout")
    assert "hello-from-c" in text, trace.output_chunks()
    caps = trace.meta.get("capabilities") or {}
    assert caps.get("output") is True, caps
    shown = run_c(["tree", trace.path.stem], tmp_path, sdir)
    assert "main" in shown.stdout, shown.stdout + shown.stderr


def test_make_records_a_trace(tmp_path):
    """A temp Makefile that uses `$(CC)` is built by `sensorium c run -- make`."""
    gcc_or_skip()
    if shutil.which("make") is None:
        pytest.skip("make is not on PATH")
    proj = tmp_path / "proj"
    shutil.copytree(SAMPLES / "make", proj)
    sdir = tmp_path / "sdir"
    proc = run_c(["c", "run", "--", "make"], proj, sdir, timeout=90)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    opened = open_new_traces(sdir, set())
    assert opened, proc.stdout + proc.stderr
    names = [c.qualname for t in opened for c in t.codes()]
    assert any(name == "main" or name.endswith(".main") for name in names), names


def test_cmake_configure_and_build(tmp_path):
    if shutil.which("cmake") is None:
        pytest.skip("cmake is not on PATH")
    gcc_or_skip()
    proj = tmp_path / "proj"
    shutil.copytree(SAMPLES / "cmake", proj)
    sdir = tmp_path / "sdir"
    configured = run_c(["c", "run", "--", "cmake", "-S", ".", "-B", "build"],
                       proj, sdir, timeout=120)
    assert configured.returncode == 0, configured.stdout + configured.stderr
    built = run_c(["c", "run", "--", "cmake", "--build", "build"],
                  proj, sdir, timeout=120)
    assert built.returncode == 0, built.stdout + built.stderr
    hello = [p for p in proj.rglob("hello") if p.is_file() and os.access(p, os.X_OK)]
    plans = list(proj.rglob("*.scplan"))
    assert hello, "cmake --build did not produce an executable named hello"
    assert plans, f"no .scplan under {proj}"
    assert read_plan(plans[0]) is not None


def test_meson_setup_and_compile(tmp_path):
    if shutil.which("meson") is None or shutil.which("ninja") is None:
        pytest.skip("meson or ninja is not on PATH")
    gcc_or_skip()
    proj = tmp_path / "proj"
    shutil.copytree(SAMPLES / "meson", proj)
    sdir = tmp_path / "sdir"
    setup = run_c(["c", "run", "--", "meson", "setup", "build"],
                  proj, sdir, timeout=120)
    assert setup.returncode == 0, setup.stdout + setup.stderr
    built = run_c(["c", "run", "--", "meson", "compile", "-C", "build"],
                  proj, sdir, timeout=120)
    assert built.returncode == 0, built.stdout + built.stderr
    hello = [p for p in (proj / "build").rglob("hello") if p.is_file() and os.access(p, os.X_OK)]
    plans = list(proj.rglob("*.scplan"))
    assert hello, "meson compile did not produce hello"
    assert plans, f"no .scplan under {proj}"
    assert read_plan(plans[0]) is not None
