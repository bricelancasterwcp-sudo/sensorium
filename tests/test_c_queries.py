"""Queries over a C trace: exceptions, failures, info, runs, and MCP.

`assert_div` is UNCAUGHT and names the assertion. A clean `types.c` run
has no exceptions and no test functions. `longjmp_test` lists `test_one`
and not `test_two`. `info` says `compiler:` and `lang: c`, and does not
borrow Python's or cargo's words. `runs` groups the invocation under the
driver command. `record_c` is the MCP tool for `c run`.

`tests/test_ts_refusal.py` already refuses a cobol trace (v24). This file
only checks that `c` joined `KNOWN_LANGS` and cobol did not.
"""
import re
import shutil

import pytest

from sensorium.store.db import KNOWN_LANGS
from tests.c_helpers import SAMPLES, build_and_run, run_c

needs_gcc = pytest.mark.skipif(shutil.which("gcc") is None, reason="gcc is not on PATH")


@pytest.fixture(scope="module")
def recorded(tmp_path_factory):
    if shutil.which("gcc") is None:
        pytest.skip("gcc is not on PATH")
    root = tmp_path_factory.mktemp("queries")
    sdir = root / "sdir"
    assert_rec = build_and_run(root / "assert", SAMPLES / "assert_div.c", sdir,
                                binary="assert_div")
    jump_rec = build_and_run(root / "jump", SAMPLES / "longjmp_test.c", sdir,
                              binary="longjmp_test")
    thread_rec = build_and_run(root / "threads", SAMPLES / "threads.c", sdir,
                                link=("-pthread",), binary="threads")
    types_rec = build_and_run(root / "types", SAMPLES / "types.c", sdir,
                               binary="types")
    return {
        "sdir": sdir,
        "assert": assert_rec,
        "jump": jump_rec,
        "threads": thread_rec,
        "types": types_rec,
    }


def _q(args, recorded, key):
    rec = recorded[key]
    return run_c(args, rec.work, recorded["sdir"])


@needs_gcc
def test_exceptions_on_assert_is_uncaught(recorded):
    proc = _q(["exceptions", recorded["assert"].trace.path.stem], recorded, "assert")
    text = proc.stdout
    assert proc.returncode == 0, text + proc.stderr
    assert "UNCAUGHT" in text, text
    assert "divisor must be nonzero" in text, text
    assert "SWALLOWED" not in text, text


@needs_gcc
def test_exceptions_on_a_clean_run_says_none(recorded):
    proc = _q(["exceptions", recorded["types"].trace.path.stem], recorded, "types")
    text = proc.stdout
    assert proc.returncode == 1, text + proc.stderr
    assert "no exceptions recorded" in text, text


@needs_gcc
def test_failures_on_longjmp_lists_only_the_jump(recorded):
    proc = _q(["failures", recorded["jump"].trace.path.stem], recorded, "jump")
    text = proc.stdout
    assert proc.returncode == 0, text + proc.stderr
    assert "test_one" in text, text
    assert "test_two" not in text, text


@needs_gcc
def test_failures_on_types_says_no_test_functions(recorded):
    proc = _q(["failures", recorded["types"].trace.path.stem], recorded, "types")
    text = proc.stdout
    assert proc.returncode == 1, text + proc.stderr
    assert "no test functions recorded" in text, text


@needs_gcc
def test_info_names_the_compiler_and_lang_c(recorded):
    proc = _q(["info", recorded["types"].trace.path.stem], recorded, "types")
    text = proc.stdout
    assert proc.returncode == 0, text + proc.stderr
    assert "compiler:" in text, text
    assert re.search(r"lang: c\b", text), text
    assert "python ?" not in text, text
    assert "cargo" not in text, text


@needs_gcc
def test_runs_groups_the_driver_command(recorded):
    """The header is the command the driver ran, and it does not say cargo."""
    proc = run_c(["runs"], recorded["types"].work, recorded["sdir"])
    text = proc.stdout
    assert proc.returncode == 0, text + proc.stderr
    headers = [line for line in text.splitlines() if line.startswith("invocation ")]
    assert headers, text
    assert any("types" in line or "./types" in line for line in text.splitlines()), text
    assert "cargo" not in text, text


@needs_gcc
def test_tree_on_the_threads_crash_shows_both_workers(recorded):
    proc = _q(["tree", recorded["threads"].trace.path.stem], recorded, "threads")
    text = proc.stdout
    assert proc.returncode == 0, text + proc.stderr
    assert text.count("worker_fn") >= 2, text
    assert "SIGSEGV" in text, text


def test_c_is_a_known_language_and_cobol_is_not():
    """v24 and `tests/test_ts_refusal.py` already refuse a cobol trace at
    open. Adding C must not make that language readable."""
    assert "c" in KNOWN_LANGS
    assert "cobol" not in KNOWN_LANGS


def test_record_c_argv_is_c_run_strict():
    """`record_c` with `make test` and strict is the driver's argv, not cargo's."""
    from sensorium.mcp import tools
    table = tools.table(True)
    assert "record_c" in table, list(table)
    argv, _extras = tools.command_argv(
        table["record_c"], {"command": ["make", "test"], "strict": True})
    assert argv == ["c", "run", "--strict", "--", "make", "test"], argv
