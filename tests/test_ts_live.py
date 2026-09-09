"""The driver against the real thing: `npx vitest run` over the probes.

This is the only test that puts the whole recorder together -- the wrapper
config in front of a consumer's own config, a real vitest, ten forked
containers, the conversion, and the reader. It is also the only one that can
tell us the wrapper text WORKS, as opposed to being spelled correctly.

Gated on `SENSORIUM_TS_LIVE=1` and skipped BY NAME otherwise, because it
needs `typescript/probes` installed (`npm ci`) and takes seconds rather than
milliseconds. Gated, not deleted: the assertion at its centre is the
recorder's own acceptance -- `check.mjs`, the probes' checker, passing every
one of its checks against spools the DRIVER produced, not against spools the
probe project wired for itself.

    SENSORIUM_TS_LIVE=1 .venv/bin/python -m pytest tests/test_ts_live.py
"""
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from sensorium.store.reader import Trace
from sensorium.ts import pkg as pkg_mod
from tests.helpers import run_cli

pytestmark = pytest.mark.skipif(
    os.environ.get("SENSORIUM_TS_LIVE") != "1",
    reason="live vitest run: set SENSORIUM_TS_LIVE=1 (needs npm ci in "
           "typescript/probes)")

PROBES = pkg_mod.locate() / "probes"
INVOCATION = re.compile(r"^invocation: (\S+)  traces: (\d+)  "
                        r"harness exit: (.+)$", re.MULTILINE)


def probe_files() -> list[Path]:
    return sorted(PROBES.glob("src/*.probe.test.*"))


def drive(store: Path, *extra: str):
    r = run_cli(["ts", "run", "--", "npx", "vitest", "run", *extra],
                cwd=PROBES, sensorium_dir=store)
    m = INVOCATION.search(r.stdout)
    assert m, r.stdout + r.stderr
    return r, m.group(1), m.group(3)


def traces(store: Path) -> list[Trace]:
    return [Trace.open(p) for p in sorted((store / "traces").glob("*.db"))]


@pytest.fixture(scope="module")
def driven(tmp_path_factory):
    """One driven `vitest run`, shared by every assertion about it."""
    store = tmp_path_factory.mktemp("live")
    r, invocation, ending = drive(store)
    return {"store": store, "result": r, "invocation": invocation,
            "ending": ending, "spool": store / "spool" / invocation}


# -- the acceptance ---------------------------------------------------------

def test_the_probes_checker_passes_against_the_drivers_own_spools(driven):
    """The same 77 checks the probe project asserts when it wires itself.
    Passing them through the driver is what says the wrapper config, the
    written setup file and the R16 external declaration reproduce the wiring
    the probes were written against -- and not merely something like it."""
    spool = driven["spool"]
    r = subprocess.run(
        ["node", "check.mjs", "vitest", str(spool), str(spool / "manifests")],
        cwd=PROBES, capture_output=True, text=True)
    report = json.loads(r.stdout)
    assert report["failures"] == []
    assert report["ok"] is True
    assert r.returncode == 0
    assert report["spools"] == len(probe_files())


def test_one_trace_per_probe_file(driven):
    """E0's finding, now the driver's: under vitest's default pool a
    container is one forked child per test file."""
    got = traces(driven["store"])
    assert len(got) == len(probe_files())
    assert {t.meta["test_file"] for t in got} == {
        f"src/{p.name}" for p in probe_files()}


def test_every_trace_carries_the_ending_the_driver_witnessed(driven):
    for trace in traces(driven["store"]):
        assert trace.meta["harness_exit"]["basis"] == "waited"
        assert trace.meta["invocation"] == driven["invocation"]
        assert trace.meta["exit_status_basis"] == "unwitnessed"


def test_the_harness_is_red_by_design_and_the_driver_says_so(driven):
    """Two probes make `vitest run` red on purpose. The driver reports
    vitest's own status and exits with it: a recorder that laundered a red
    run into its own 0 would be lying about the run it recorded."""
    assert driven["ending"] == "1 (waited)"
    assert driven["result"].returncode == 1


def test_runs_groups_the_invocation_and_lists_every_member(driven):
    r = run_cli(["runs"], cwd=PROBES, sensorium_dir=driven["store"])
    assert r.returncode == 0, r.stderr
    headers = [ln for ln in r.stdout.splitlines()
               if ln.startswith("invocation ")]
    members = [ln for ln in r.stdout.splitlines() if ln.startswith("  ")]
    assert len(headers) == 1
    assert driven["invocation"] in headers[0]
    assert len(members) == len(probe_files())


def test_the_wrapper_is_gone_from_the_consumers_tree(driven):
    assert not (PROBES / "node_modules" / ".sensorium").exists()


def test_the_spool_directory_holds_the_record_and_the_marker(driven):
    spool = driven["spool"]
    record = json.loads((spool / "invocation.json").read_text())
    assert record["harness"] == "vitest"
    assert record["argv"] == ["npx", "vitest", "run"]
    assert record["root"] == str(PROBES)
    assert record["vitest"] is not None
    assert record["wrapper"].endswith(f"{driven['invocation']}.config.mts")
    assert json.loads((spool / "ingested.json").read_text())["refused"] == []


# -- the threads pool -------------------------------------------------------

def test_a_threads_pool_records_every_container_it_ran(tmp_path):
    """Reported, not gated. Under `--pool=threads` vitest reuses worker
    threads, so a container can run more than one test file -- the branch
    that writes `test_files` instead of `test_file`. Whether it fires at all
    is a property of vitest's scheduling on the box, so what is asserted is
    the invariant either way: every container names what it ran."""
    r, _invocation, _ending = drive(tmp_path, "--pool=threads")
    got = traces(tmp_path)
    assert got, r.stdout
    named = [("test_files" if "test_files" in t.meta else "test_file")
             for t in got]
    assert all("test_file" in t.meta or "test_files" in t.meta for t in got)
    assert sum(len(t.meta.get("test_files", [t.meta.get("test_file")]))
               for t in got) == len(probe_files())
    print(f"threads pool: {len(got)} containers, "
          f"{named.count('test_files')} of them with test_files")
