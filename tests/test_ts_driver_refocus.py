"""`sensorium ts run --refocus-of <run>`: the link, and what refuses it.

The flag is what makes a re-run a re-run: `sensorium refocus` re-runs the
recorded harness command one flag deeper and passes this, and every trace
of the second invocation is then stamped with the first run's id. So the
value is checked FIRST among the driver's own refusals -- before the Node
version, before the package, before `recognise` -- because it is about the
CALL and nothing else, and a bad one must not cost a spawn (design 2.1).

The three refusals need no Node at all, which is the point of checking them
first, and they run everywhere. The end-to-end test records twice through
the real command line and is skipped BY NAME where `tests/test_ts_driver.py`
skips: a suite that quietly stopped exercising its driver would look
exactly like a suite that passes.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from sensorium.store.reader import Trace
from sensorium.ts import driver as driver_mod
from sensorium.ts import pkg as pkg_mod
from tests.helpers import run_cli

INVOCATION = re.compile(r"^invocation: (\S+)  traces: (\d+)  "
                        r"harness exit: (.+)$", re.MULTILINE)

ORIGINAL = "20260101-000000-abc123"

#: The `node --test` project of `tests/test_ts_driver.py`, by shape and not
#: by import: a fixture shared across two modules is a fixture neither can
#: change, and what this one needs is that the project RECORDS, twice.
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
    assert.equal(add(1, 2), 3);
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


# -- the link's own refusals -------------------------------------------------

def _args(**kw) -> argparse.Namespace:
    base = dict(command=["--", "node", "--test", "t/"], tier="call",
                focus=[], jobs=None, refocus_of=None)
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture
def nothing_spawns(tmp_path, monkeypatch):
    """The driver, standing in an empty directory, with a tripwire where the
    harness would be. Anything that reaches `_spawn` has got past a refusal
    this module says it must not get past, and says so by name."""
    sdir = tmp_path / "sdir"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))

    def _tripwire(*a, **kw):
        raise AssertionError("spawned")

    monkeypatch.setattr(driver_mod, "_spawn", _tripwire)
    return sdir


def test_a_link_that_is_not_a_run_id_is_refused_before_anything_runs(
        nothing_spawns, capsys):
    """`../x` is the shape `is_valid_run_id` exists for: it would flow into
    `traces_dir() / f"{v}.db"` and read outside the store."""
    assert driver_mod.run(_args(refocus_of="../x")) == 2
    err = capsys.readouterr().err
    assert ("error: --refocus-of ../x is not a run id; nothing was run."
            in err), err
    assert not (nothing_spawns / "spool").exists()


def test_a_link_naming_no_trace_is_refused_and_says_where_it_looked(
        nothing_spawns, capsys):
    """A run id that is well-formed and absent is the typo a person makes,
    and the store's path is the thing they need to see to fix it."""
    assert driver_mod.run(_args(refocus_of="20260101-000000-nope01")) == 2
    err = capsys.readouterr().err
    assert ("error: --refocus-of 20260101-000000-nope01 names no trace in "
            f"{nothing_spawns}; nothing was run." in err), err
    assert not (nothing_spawns / "spool").exists()


def test_a_db_suffix_names_the_trace_it_is_the_file_of(
        nothing_spawns, capsys):
    """`<id>.db` is what tab-completion in the store hands a person, so one
    trailing suffix is stripped rather than refused. What this test pins is
    that the value gets PAST the link check: whatever refuses next is the
    Node check, the package, `recognise` or the tripwire, and none of them
    is about `--refocus-of`."""
    (nothing_spawns / "traces").mkdir(parents=True)
    (nothing_spawns / "traces" / f"{ORIGINAL}.db").touch()
    try:
        code = driver_mod.run(_args(refocus_of=f"{ORIGINAL}.db"))
    except AssertionError as e:
        assert str(e) == "spawned"      # got all the way to the harness
        return
    err = capsys.readouterr().err
    assert code == 2, err
    assert "--refocus-of" not in err, err


def test_the_link_is_checked_before_the_node_version(nothing_spawns,
                                                     monkeypatch, capsys):
    """The order is the design's, so it is pinned as the order and not as a
    consequence: `check_node` is the driver's first refusal for every other
    call, and a call with a bad link never reaches it."""
    def _never(*a, **kw):
        raise AssertionError("check_node ran")

    monkeypatch.setattr(pkg_mod, "check_node", _never)
    assert driver_mod.run(_args(refocus_of="../x")) == 2
    assert "is not a run id" in capsys.readouterr().err


# -- the whole journey, twice ------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """A `node --test` project of two files, and the one dependency the
    loader hook resolves from the ROOT: the consumer's own TypeScript."""
    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "app", "type": "module"}\n')
    (root / "lib.ts").write_text(LIB)
    (root / "a.test.ts").write_text(TEST)
    (root / "node_modules" / "typescript").symlink_to(
        pkg_mod.locate() / "node_modules" / "typescript")
    return root


def _traces(sdir: Path) -> set[Path]:
    return set((sdir / "traces").glob("*.db"))


@pytest.mark.skipif(SKIP is not None, reason=SKIP or "")
def test_a_re_run_stamps_every_trace_with_the_run_it_re_runs(project,
                                                             tmp_path):
    """Two real recordings of one command, the second linked to the first.
    The link is written into `invocation.json` before the harness is spawned
    and reaches the trace through the converter, which is the whole path
    `sensorium refocus` depends on."""
    sdir = tmp_path / "sdir"
    first = run_cli(["ts", "run", "--", "node", "--test", "a.test.ts"],
                    cwd=project, sensorium_dir=sdir)
    assert first.returncode == 0, first.stdout + first.stderr
    original = Trace.open(next(iter(_traces(sdir))))
    original_id = original.meta["run_id"]
    assert "refocus_of" not in original.meta
    assert original.meta["harness_cwd"] == str(project)

    before = _traces(sdir)
    second = run_cli(["ts", "run", "--refocus-of", original_id, "--",
                      "node", "--test", "a.test.ts"],
                     cwd=project, sensorium_dir=sdir)
    assert second.returncode == 0, second.stdout + second.stderr
    m = INVOCATION.search(second.stdout)
    assert m, second.stdout

    record = json.loads(
        (sdir / "spool" / m.group(1) / "invocation.json").read_text())
    assert record["refocus_of"] == original_id
    new = _traces(sdir) - before
    assert len(new) == 1, sorted(p.name for p in new)
    meta = Trace.open(next(iter(new))).meta
    assert meta["refocus_of"] == original_id
    assert meta["harness_cwd"] == str(project)


@pytest.mark.skipif(SKIP is not None, reason=SKIP or "")
def test_a_re_run_of_a_trace_the_store_lost_is_refused(project, tmp_path):
    """Through the real command line, and not just the helper: the flag is
    parsed where `--tier` and `--focus` are, before the `--`, so the harness
    command after it is never what the check reads."""
    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "run", "--refocus-of", "20260101-000000-nope01", "--",
                 "node", "--test", "a.test.ts"],
                cwd=project, sensorium_dir=sdir)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "names no trace in" in r.stderr, r.stderr
    assert not (sdir / "spool").exists()
