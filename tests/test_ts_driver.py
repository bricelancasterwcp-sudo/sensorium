"""`sensorium ts run`, end to end, through the harness that needs no vitest.

`node --test` is the whole recorder in one process tree: the driver
recognises it, prepends `--import`, spawns it, waits, converts the spools
and hands back node's own status. So it is what this module drives -- a real
run of the real command line against a real Node, with nothing stubbed.

The vitest half of the same journey is `tests/test_ts_live.py`, which needs
a vitest install and is gated; what is checked HERE is everything that does
not: the order of operations, the exit status, the record beside the spools,
and the fact that a node run writes no wrapper into anybody's tree.

Skipped BY NAME, never silently, when this box has no Node 24 or the
package has never been installed: a suite that quietly stopped exercising
its driver would look exactly like a suite that passes.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from sensorium.store.reader import Trace
from sensorium.ts import driver as driver_mod
from sensorium.ts import harness as harness_mod
from sensorium.ts import pkg as pkg_mod
from tests.helpers import run_cli

INVOCATION = re.compile(r"^invocation: (\S+)  traces: (\d+)  "
                        r"harness exit: (.+)$", re.MULTILINE)

LIB = """\
export function add(a: number, b: number): number {
  return a + b;
}
"""

TEST = """\
import assert from 'node:assert/strict';
import { describe, test } from 'node:test';

import { add } from './lib.ts';

describe('arithmetic', () => {
  test('adds', () => {
    assert.equal(add(1, 2), %d);
  });
});
"""


def _why_skip() -> str | None:
    node = shutil.which("node")
    if node is None:
        return "no node on PATH"
    out = subprocess.run([node, "--version"], capture_output=True, text=True)
    major = int(out.stdout.strip().lstrip("v").split(".")[0])
    if major < pkg_mod.NODE_FLOOR:
        return f"node {out.stdout.strip()} is below the recorder's floor"
    if not (pkg_mod.locate() / "node_modules" / "magic-string").is_dir():
        return f"{pkg_mod.locate()} has never been installed (npm ci)"
    return None


SKIP = _why_skip()
pytestmark = pytest.mark.skipif(SKIP is not None, reason=SKIP or "")


@pytest.fixture
def project(tmp_path):
    """A `node --test` project of two files, and the one dependency the
    loader hook resolves from the ROOT: the consumer's own TypeScript."""
    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "app", "type": "module"}\n')
    (root / "lib.ts").write_text(LIB)
    (root / "a.test.ts").write_text(TEST % 3)
    (root / "node_modules" / "typescript").symlink_to(
        pkg_mod.locate() / "node_modules" / "typescript")
    return root


def drive(project, sdir, *, extra=()):
    r = run_cli(["ts", "run", *extra, "--", "node", "--test", "a.test.ts"],
                cwd=project, sensorium_dir=sdir)
    return r


def only_trace(sdir: Path) -> Trace:
    files = sorted((sdir / "traces").glob("*.db"))
    assert len(files) == 1, files
    return Trace.open(files[0])


# -- the whole journey ------------------------------------------------------

def test_a_node_test_run_records_one_trace_and_says_so(project, tmp_path):
    sdir = tmp_path / "sdir"
    r = drive(project, sdir)
    assert r.returncode == 0, r.stderr
    m = INVOCATION.search(r.stdout)
    assert m, r.stdout
    invocation, traces, ending = m.groups()
    assert traces == "1"
    assert ending == "0 (waited)"
    assert r.stdout.count("run: ") == 1

    trace = only_trace(sdir)
    assert trace.meta["invocation"] == invocation
    assert trace.meta["harness"] == "node-test"
    assert trace.meta["harness_args"] == ["--test", "a.test.ts"]
    # R26: the tokens as TYPED, which for this harness is the whole point.
    # `harness` is a kind and not a program -- `node-test --test a.test.ts`,
    # what the header used to build out of `harness` + `harness_args`, is a
    # command that does not exist.
    assert trace.meta["harness_command"] == ["node", "--test", "a.test.ts"]
    assert trace.meta["harness_exit"] == {"status": 0, "signal": None,
                                          "basis": "waited"}
    assert trace.meta["lang"] == "typescript"

    listing = run_cli(["runs"], cwd=project, sensorium_dir=sdir)
    assert (f"invocation {invocation}: node --test a.test.ts  exit:0 (waited)"
            in listing.stdout), listing.stdout
    assert "node-test" not in listing.stdout, listing.stdout


def test_a_node_test_container_has_no_test_file_to_name(project, tmp_path):
    """`test_file` comes from the vitest setup file, which `node --test`
    does not run. The key is ABSENT rather than empty: nobody told this
    container which file it was."""
    sdir = tmp_path / "sdir"
    drive(project, sdir)
    meta = only_trace(sdir).meta
    assert "test_file" not in meta and "test_files" not in meta


def test_tasks_are_named_lexically_because_no_harness_offered_a_name(
        project, tmp_path):
    sdir = tmp_path / "sdir"
    drive(project, sdir)
    trace = only_trace(sdir)
    assert [t.name for t in trace.tasks()] == ["arithmetic > adds"]
    assert trace.meta["task_name_basis"] == "title"


def test_the_recorded_program_is_the_one_that_ran(project, tmp_path):
    sdir = tmp_path / "sdir"
    drive(project, sdir)
    trace = only_trace(sdir)
    assert "add" in {c.qualname for c in trace.codes()}


def test_the_harness_status_is_the_drivers_status(project, tmp_path):
    """The whole point of the `run` verb: it never applies the query CLI's
    0/1/2/3 table to itself. A red test run exits 1 because node exited 1."""
    (project / "a.test.ts").write_text(TEST % 4)
    sdir = tmp_path / "sdir"
    r = drive(project, sdir)
    assert r.returncode == 1, r.stdout + r.stderr
    m = INVOCATION.search(r.stdout)
    assert m and m.group(3) == "1 (waited)"
    assert only_trace(sdir).meta["harness_exit"]["status"] == 1


def test_a_failing_harness_still_leaves_a_converted_recording(
        project, tmp_path):
    """The recording is the reason to be here. A run that went red is the
    run an agent most wants to read, so nothing about the conversion is
    conditional on the harness's status."""
    (project / "a.test.ts").write_text(TEST % 4)
    sdir = tmp_path / "sdir"
    drive(project, sdir)
    assert only_trace(sdir).meta["harness"] == "node-test"


# -- what is left on disk ---------------------------------------------------

def test_the_spool_directory_keeps_the_invocations_own_record(
        project, tmp_path):
    sdir = tmp_path / "sdir"
    r = drive(project, sdir)
    invocation = INVOCATION.search(r.stdout).group(1)
    spool = sdir / "spool" / invocation
    record = json.loads((spool / "invocation.json").read_text())
    assert record["harness"] == "node-test"
    assert record["argv"] == ["node", "--test", "a.test.ts"]
    assert record["command"] == ["node", "--test", "a.test.ts"]
    assert record["root"] == str(project)
    assert record["cwd"] == str(project)
    assert record["vitest"] is None
    assert record["wrapper"] == ""
    assert record["node"].startswith("v")
    assert len(record["env_hash"]) == 16

    ending = json.loads((spool / "harness.json").read_text())
    assert ending["status"] == 0 and ending["signal"] is None
    assert ending["basis"] == "waited"
    assert ending["wall_end_ts"] >= ending["wall_start_ts"]


def test_the_typed_command_keeps_the_flags_the_driver_consumes(tmp_path):
    """R26, the case a `node --test` run cannot show.

    For vitest the driver CONSUMES `--root` and `--config` out of the
    command so it can re-issue its own at the end, and `harness_args` and
    `stripped` are what is left over. A reader shown either has been shown
    a command with the user's own flags deleted from it -- silently, and
    with no way to tell from the output that anything was removed.
    `command` is the tokens before any of that happened, which is the only
    list here anyone typed.

    No harness is spawned: this drives the record-writing step alone, which
    is where the field is filled in.
    """
    (tmp_path / "sub").mkdir()
    (tmp_path / "mine.ts").write_text("export default {}\n")
    typed = ["npx", "vitest", "run", "src/fog", "--root", "sub",
             "-c", "mine.ts"]
    plan = harness_mod.recognise(list(typed), tmp_path)
    assert isinstance(plan, harness_mod.Plan), plan
    spool = tmp_path / "spool"
    spool.mkdir()
    driver_mod._write_record(spool, plan, "20260101-000000-abcdef",
                             "v24.0.0", pkg_mod.locate(), None)
    record = json.loads((spool / "invocation.json").read_text())
    assert record["command"] == typed
    # What the driver kept for its own machinery is a different list, and
    # neither half of it is a command.
    assert record["harness_args"] == ["run", "src/fog"]
    assert record["harness"] == "vitest"
    assert "--root" not in record["harness_args"]
    assert "--root" not in " ".join([record["harness"],
                                     *record["harness_args"]])


def test_the_conversion_marks_the_directory_it_converted(project, tmp_path):
    sdir = tmp_path / "sdir"
    r = drive(project, sdir)
    invocation = INVOCATION.search(r.stdout).group(1)
    marker = json.loads(
        (sdir / "spool" / invocation / "ingested.json").read_text())
    assert len(marker["run_ids"]) == 1 and marker["refused"] == []


def test_no_wrapper_is_written_for_a_node_test_run(project, tmp_path):
    """The wrapper is vitest's. A node run gets `--import` on its own
    command line and the consumer's tree is not written to at all."""
    before = sorted(str(p.relative_to(project)) for p in project.rglob("*"))
    drive(project, tmp_path / "sdir")
    after = sorted(str(p.relative_to(project)) for p in project.rglob("*"))
    assert after == before
    assert not (project / "node_modules" / ".sensorium").exists()


def test_the_control_arm_records_nothing_and_says_so(project, tmp_path):
    """`--tier off` is the arm that transforms everything and emits nothing,
    so its empty spool directory is the expected outcome. It reports zero
    traces and still hands back the harness's status -- a control arm that
    exited 2 could not be put opposite the recorded arm in a timing run."""
    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "run", "--tier", "off", "--", "node", "--test",
                 "a.test.ts"], cwd=project, sensorium_dir=sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert INVOCATION.search(r.stdout).group(2) == "0"
    assert "run: " not in r.stdout
    assert not (sdir / "traces").exists()


# -- the parts the happy path cannot reach ----------------------------------

def test_a_harness_killed_by_a_signal_is_recorded_and_reported_as_one(
        tmp_path):
    """A real death by signal, not a hand-built record: `subprocess` reports
    it as a NEGATIVE return code, which is the one shape a status-only
    reading would silently turn into an exit code nobody chose."""
    from sensorium.ts import driver
    ending = driver._spawn(["sh", "-c", "kill -TERM $$"], dict(os.environ),
                           tmp_path)
    assert (ending.status, ending.signal) == (None, "SIGTERM")
    assert ending.basis == "waited"
    assert driver._status(ending) == 143            # what a shell reports
    assert driver._ending(ending) == "signal SIGTERM (waited)"


def test_the_wrapper_is_removed_even_when_the_run_raises(
        tmp_path, monkeypatch):
    """The removal is in a `finally`, and this is the path that proves it:
    an exception nobody planned for, between writing the two files and
    reaching the conversion."""
    from sensorium.ts import driver

    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "node_modules" / ".package-lock.json").write_text("{}\n")
    monkeypatch.chdir(root)
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))

    def boom(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(driver, "_spawn", boom)
    args = argparse.Namespace(command=["--", "vitest", "run"], tier="call",
                              jobs=None)
    with pytest.raises(KeyboardInterrupt):
        driver.run(args)
    assert not (root / "node_modules" / ".sensorium").exists()
    # And the record of what was about to be spawned is still there: the
    # driver died, the invocation happened.
    spools = sorted((tmp_path / "sdir" / "spool").iterdir())
    assert len(spools) == 1
    assert (spools[0] / "invocation.json").is_file()
    assert not (spools[0] / "harness.json").exists()


def test_the_wrapper_goes_when_the_run_merely_finishes(tmp_path, monkeypatch):
    """The ordinary case, and the one an exception test cannot stand in for:
    a harness that returned normally must not leave the two files behind.

    It also pins what an EMPTY spool directory means at tier `call`: the
    recorder was wired into the run and recorded nothing, which is a call to
    fix and not a recording -- exit 2, with the directory named.
    """
    from sensorium.ts import driver
    from sensorium.ts.invocation import HarnessExit

    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "node_modules" / ".package-lock.json").write_text("{}\n")
    monkeypatch.chdir(root)
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    monkeypatch.setattr(driver, "_spawn",
                        lambda *a, **k: HarnessExit(0, None, 1.0, 2.0))
    args = argparse.Namespace(command=["--", "vitest", "run"], tier="call",
                              jobs=None)
    assert driver.run(args) == 2
    assert not (root / "node_modules" / ".sensorium").exists()


def test_the_harness_is_told_the_six_things_it_cannot_work_out(tmp_path):
    """The runtime reads its spool directory, its tier and its invocation
    from the environment; the loader hook reads the root and the package;
    the plugin reads the manifest directory. None of the six can be guessed
    from inside the harness."""
    from sensorium.ts import driver, harness as harness_mod

    plan = harness_mod.recognise(["vitest", "run"], tmp_path)
    env = driver._env(tmp_path / "spool", "INV", plan, tmp_path / "pkg",
                      "call")
    # Everything the driver ADDED to its own environment, and nothing else:
    # the harness inherits the caller's environment unchanged otherwise.
    assert {k: v for k, v in env.items() if os.environ.get(k) != v} == {
        "SENSORIUM_SPOOL": str(tmp_path / "spool"),
        "SENSORIUM_TIER": "call",
        "SENSORIUM_TS_ROOT": str(tmp_path),
        "SENSORIUM_TS_PKG": str(tmp_path / "pkg"),
        "SENSORIUM_INVOCATION": "INV",
        "SENSORIUM_MANIFEST_DIR": str(tmp_path / "spool" / "manifests")}
    assert env["PATH"] == os.environ["PATH"]


# -- the refusals -----------------------------------------------------------

def test_a_package_script_is_refused_at_exit_two_with_one_line(
        project, tmp_path):
    r = run_cli(["ts", "run", "--", "npm", "test"], cwd=project,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2
    assert "sensorium ts run -- vitest run" in r.stderr
    assert "Traceback" not in r.stderr
    assert len(r.stderr.strip().splitlines()) == 1


def test_jest_is_refused_at_exit_two(project, tmp_path):
    r = run_cli(["ts", "run", "--", "jest"], cwd=project,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2
    assert r.stderr.strip() == (
        "error: jest is not supported: not measured, and the consumer does "
        "not run it")


def test_a_refused_command_spawns_nothing_and_records_nothing(
        project, tmp_path):
    sdir = tmp_path / "sdir"
    run_cli(["ts", "run", "--", "mocha"], cwd=project, sensorium_dir=sdir)
    assert not (sdir / "spool").exists()
    assert not (sdir / "traces").exists()


def test_an_empty_command_is_refused(project, tmp_path):
    r = run_cli(["ts", "run", "--"], cwd=project,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2
    assert "vitest" in r.stderr and "node --test" in r.stderr


def test_a_node_below_the_floor_is_refused_before_anything_is_spawned(
        project, tmp_path):
    """The floor is a measurement, not a preference (D2). The refusal names
    it, and it happens first: a run that got as far as writing a spool
    directory would leave one behind for a harness that never started."""
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "node").write_text("#!/bin/sh\necho v22.14.0\n")
    (fake / "node").chmod(0o755)
    r = run_cli(["ts", "run", "--", "node", "--test", "a.test.ts"],
                cwd=project, sensorium_dir=tmp_path / "sdir",
                env_extra={"PATH": f"{fake}{os.pathsep}{os.environ['PATH']}"})
    assert r.returncode == 2
    assert "24" in r.stderr and "v22.14.0" in r.stderr
    assert not (tmp_path / "sdir" / "spool").exists()


def test_an_uninstalled_package_is_refused_naming_the_install(
        project, tmp_path):
    empty = tmp_path / "not-installed"
    (empty / "src").mkdir(parents=True)
    r = run_cli(["ts", "run", "--", "node", "--test", "a.test.ts"],
                cwd=project, sensorium_dir=tmp_path / "sdir",
                env_extra={"SENSORIUM_TS_PKG": str(empty)})
    assert r.returncode == 2
    assert f"npm ci --prefix {empty}" in r.stderr
