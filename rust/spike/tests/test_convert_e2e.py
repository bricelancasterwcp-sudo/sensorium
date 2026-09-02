"""End-to-end tests for `rust/spike/convert.py` (THROWAWAY SPIKE CODE, Task 4).

Split out of `test_convert.py` (which keeps the wire-parser, k-way-merge,
frame-reconstruction and `convert_dir` meta tiers) purely to keep both files
under the project's 800-line cap -- there is no other reason for the split,
and both files import the same `convert` module the same way.

Builds the probe workspace through the real `cargo-sensorium` driver into a
temp `CARGO_TARGET_DIR` (a subdirectory of the probe workspace itself, so
`parent(--target)` is the actual workspace root -- the Controller ruling
`convert.py` relies on), converts through `convert.py`'s own CLI, then drives
the real `sensorium` CLI in a subprocess against a temp `SENSORIUM_DIR`.

Run: `.venv/bin/python -m pytest rust/spike/tests/test_convert_e2e.py -q`, or
`rust/spike/tests/` for both files together (from the repo root; the
directory's `conftest.py` puts `rust/spike` on `sys.path` so `import convert`
resolves).
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

import convert

REPO_ROOT = Path(__file__).resolve().parents[3]
SPIKE_DIR = REPO_ROOT / "rust" / "spike"
PROBE_WS = SPIKE_DIR / "probes" / "ws"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python"
SENSORIUM_BIN = REPO_ROOT / ".venv" / "bin" / "sensorium"
CONVERT_PY = SPIKE_DIR / "convert.py"
WORK_WORKS_FILE = PROBE_WS / "probe-app" / "src" / "lib.rs"

pytestmark_e2e = pytest.mark.skipif(
    not (SENSORIUM_BIN.exists() and PYTHON_BIN.exists()),
    reason="the project's own .venv is required for the end-to-end tests")


def _run_driver(driver_bin: Path, target: Path, cargo_args: list):
    env = dict(os.environ)
    env["CARGO_TARGET_DIR"] = str(target)
    env["SENSORIUM_SPIKE_ROOT"] = str(SPIKE_DIR)
    proc = subprocess.run([str(driver_bin), "sensorium", *cargo_args],
                          cwd=PROBE_WS, env=env, capture_output=True,
                          text=True, timeout=300, check=False)
    spool_dir = cargo_exit = None
    for line in proc.stderr.splitlines():
        if line.startswith("spool: "):
            spool_dir = Path(line[len("spool: "):])
        elif line.startswith("cargo exit: "):
            cargo_exit = int(line[len("cargo exit: "):])
    if spool_dir is None or cargo_exit is None:
        raise RuntimeError(
            f"driver did not report spool/exit; stderr:\n{proc.stderr}\n"
            f"stdout:\n{proc.stdout}")
    if cargo_exit != 0:
        raise RuntimeError(f"cargo exited {cargo_exit}:\n{proc.stderr}")
    return spool_dir, cargo_exit


def _convert(spool_dir: Path, target: Path, cargo_exit: int, cargo_args: list,
            home: Path) -> str:
    env = dict(os.environ)
    env["SENSORIUM_DIR"] = str(home)
    proc = subprocess.run(
        [str(PYTHON_BIN), str(CONVERT_PY), str(spool_dir), "--target",
        str(target), "--cargo-exit", str(cargo_exit), "--argv", *cargo_args],
        capture_output=True, text=True, env=env, timeout=120, check=True)
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("run: ")]
    assert len(lines) == 1, f"expected exactly one trace, got:\n{proc.stdout}"
    return lines[0].split()[1]


def _sensorium(home: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["SENSORIUM_DIR"] = str(home)
    return subprocess.run([str(SENSORIUM_BIN), *args], capture_output=True,
                          text=True, env=env, timeout=60, check=False)


@pytest.fixture(scope="module")
def driver_bin():
    subprocess.run(["cargo", "build", "--release", "-p", "cargo-sensorium"],
                   cwd=SPIKE_DIR, check=True, capture_output=True, text=True,
                   timeout=300)
    path = SPIKE_DIR / "target" / "release" / "cargo-sensorium"
    assert path.exists()
    return path


@pytest.fixture(scope="module")
def probe_target():
    d = Path(tempfile.mkdtemp(prefix="convert-e2e-target-", dir=PROBE_WS))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def probe_traces(driver_bin, probe_target, tmp_path_factory):
    """Builds the probe workspace's `probe-app` lib test binary THREE times
    -- twice unchanged, once with `work_works`'s body changed -- and
    converts each into its own trace under one shared `SENSORIUM_DIR`.
    Module-scoped: the cargo builds are the expensive part, and every test
    below only needs to read what this produced.
    """
    home = tmp_path_factory.mktemp("sensorium-home")
    cargo_args = ["test", "-p", "probe-app", "--lib"]

    spool1, exit1 = _run_driver(driver_bin, probe_target, cargo_args)
    run1 = _convert(spool1, probe_target, exit1, cargo_args, home)

    spool2, exit2 = _run_driver(driver_bin, probe_target, cargo_args)
    run2 = _convert(spool2, probe_target, exit2, cargo_args, home)

    original = WORK_WORKS_FILE.read_text(encoding="utf-8")
    assert "assert_eq!(work(2), 6);" in original, (
        "probe-app/src/lib.rs no longer matches this test's assumption "
        "about work_works' body -- update the sed pattern below")
    changed = original.replace("assert_eq!(work(2), 6);",
                               "assert_eq!(work(3), 8);")
    WORK_WORKS_FILE.write_text(changed, encoding="utf-8")
    try:
        spool3, exit3 = _run_driver(driver_bin, probe_target, cargo_args)
    finally:
        # Survive a failure the same way mechanics.sh does: restore before
        # anything else can observe the edited tree.
        WORK_WORKS_FILE.write_text(original, encoding="utf-8")
    run3 = _convert(spool3, probe_target, exit3, cargo_args, home)

    return {"home": home, "run1": run1, "run2": run2, "run3_changed": run3}


class TestEndToEnd:
    pytestmark = pytestmark_e2e

    def test_probe_source_tree_is_unmodified_after_the_fixture_runs(
            self, probe_traces):
        # Requesting `probe_traces` is load-bearing, not decoration: without
        # it pytest is free to run this test BEFORE the fixture's edit ever
        # happens (confirmed with `pytest --setup-show`), and an empty git
        # status before an edit proves nothing about whether the edit was
        # ever restored. Depending on the fixture forces this test to run
        # AFTER `probe-app/src/lib.rs` was edited and (should have been)
        # restored, so THIS is the check that would fail if the fixture's
        # restore were ever skipped -- see the same check mechanics.sh uses
        # for its own edit.
        result = subprocess.run(
            ["git", "status", "--porcelain", "--", str(WORK_WORKS_FILE)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True)
        assert result.stdout == ""

    def test_trace_opens_without_refusal(self, probe_traces):
        r = _sensorium(probe_traces["home"], "info", probe_traces["run1"])
        assert r.returncode == 0, r.stderr

    def test_info_shows_recorder_lang_and_capabilities(self, probe_traces):
        r = _sensorium(probe_traces["home"], "info", probe_traces["run1"])
        assert r.returncode == 0, r.stderr
        assert "recorder: sensorium-rt 0.0.0-spike  lang: rust" in r.stdout
        assert "capabilities:" in r.stdout
        for cap, value in convert.CAPABILITIES.items():
            assert f"{cap}={'yes' if value else 'no'}" in r.stdout

    def test_flow_refuses_because_line_is_undeclared(self, probe_traces):
        r = _sensorium(probe_traces["home"], "flow", probe_traces["run1"],
                       "--value", "1")
        assert r.returncode == 2
        assert "REFUSED" in r.stdout
        assert "capabilities.line: false" in r.stdout

    def test_tree_renders_frames_with_no_none_marker(self, probe_traces):
        r = _sensorium(probe_traces["home"], "tree", probe_traces["run1"])
        assert r.returncode == 0, r.stderr
        assert "[None]" not in r.stdout
        assert "tests::work_works" in r.stdout

    def test_grep_shows_the_unread_locals_marker_and_never_bare_args(
            self, probe_traces):
        """`query/fmt.py`'s CALL rendering (`fmt_event`, used by `grep`) is
        where `unread: ["locals"]` actually becomes visible text --
        `query/tree_cmd.py`'s `frame_line` never reads a CALL payload's
        `unread` key at all (only its `args`), so `tree` renders `work()`
        bare regardless of this payload; that is a fact about the real
        `sensorium` source this converter cannot change, confirmed by
        reading `tree_cmd.py` and by running both commands against the same
        trace. `grep` is the command this invariant is checkable through."""
        r = _sensorium(probe_traces["home"], "grep", probe_traces["run1"],
                       "CALL")
        assert r.returncode == 0, r.stderr
        call_lines = [ln for ln in r.stdout.splitlines() if " CALL " in ln]
        assert call_lines, r.stdout
        for line in call_lines:
            assert "<unread: locals>" in line, line

    def test_two_identical_runs_match_and_tasks_carry_the_verdict(
            self, probe_traces):
        r = _sensorium(probe_traces["home"], "diff", probe_traces["run1"],
                       probe_traces["run2"])
        assert r.returncode == 0, r.stdout + r.stderr
        assert ("MATCH -- no causal event ran outside a task on either "
               "side, so the thread streams held nothing to compare; the "
               "tasks below carry the whole verdict") in r.stdout
        assert "all matched" in r.stdout

    def test_a_changed_test_body_diverges_naming_the_task(self, probe_traces):
        r = _sensorium(probe_traces["home"], "diff", probe_traces["run1"],
                       probe_traces["run3_changed"])
        assert r.returncode == 1, r.stdout + r.stderr
        assert "DIVERGED" in r.stdout
        assert "tests::work_works" in r.stdout
