"""The driver against the real thing: `npx vitest run` over the probes.

This is the only test that puts the whole recorder together -- the wrapper
config in front of a consumer's own config, a real vitest, twelve forked
containers, the conversion, and the reader. It is also the only one that can
tell us the wrapper text WORKS, as opposed to being spelled correctly. Two
driven runs of the same suite: one plain, and one with a `--focus` per probe
function, which is the only place the resolver, the variable and the focused
transform are exercised together by a command line.

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


#: The functions `src/focus.probe.test.ts` exports, which is what the probe
#: project focuses when it wires itself. Mirrored here rather than imported,
#: because the driven reading of the flag is the point: these arrive on a
#: COMMAND LINE. `test_the_focus_list_is_the_one_the_probes_wire_themselves`
#: is what keeps the two copies the same list.
FOCUS_FUNCTIONS = ("letChain", "loopCounter", "blockScope", "bareGuard",
                   "doWhile", "forIn", "asyncRows", "catchBinding",
                   "destructure", "placeWrite", "nestedArrow")
FOCUS = [f"focus.probe.test.ts:{fn}" for fn in FOCUS_FUNCTIONS]


def drive(store: Path, *extra: str, focus: list[str] = ()):
    flags = [flag for spec in focus for flag in ("--focus", spec)]
    r = run_cli(["ts", "run", *flags, "--", "npx", "vitest", "run", *extra],
                cwd=PROBES, sensorium_dir=store)
    m = INVOCATION.search(r.stdout)
    assert m, r.stdout + r.stderr
    return r, m.group(1), m.group(3)


def traces(store: Path) -> list[Trace]:
    return [Trace.open(p) for p in sorted((store / "traces").glob("*.db"))]


def checked(spool: Path) -> dict:
    """`check.mjs` over one driven run's spools, as the probe project runs it
    over its own."""
    r = subprocess.run(
        ["node", "check.mjs", "vitest", str(spool), str(spool / "manifests")],
        cwd=PROBES, capture_output=True, text=True)
    report = json.loads(r.stdout or "{}")
    report["exit"] = r.returncode
    return report


@pytest.fixture(scope="module")
def driven(tmp_path_factory):
    """One driven `vitest run`, shared by every assertion about it."""
    store = tmp_path_factory.mktemp("live")
    r, invocation, ending = drive(store)
    return {"store": store, "result": r, "invocation": invocation,
            "ending": ending, "spool": store / "spool" / invocation}


@pytest.fixture(scope="module")
def driven_focus(tmp_path_factory):
    """The same run with a `--focus` per probe function on the command line.

    The second half of R20's contract: `checkFocus` asserts one thing when
    the recorder was focused and another when it was not, and only a run of
    each says both branches are real. This one is also the only place the
    RESOLVER meets a project it did not write -- eleven specs against the
    probes' own tree, before vitest starts.
    """
    store = tmp_path_factory.mktemp("live-focus")
    r, invocation, ending = drive(store, focus=FOCUS)
    return {"store": store, "result": r, "invocation": invocation,
            "ending": ending, "spool": store / "spool" / invocation}


# -- the acceptance ---------------------------------------------------------

def test_the_probes_checker_passes_against_the_drivers_own_spools(driven):
    """Every check the probe project asserts when it wires itself, in the
    checker's unfocused reading (103 of them at this rung). Passing them
    through the driver is what says the wrapper config, the written setup
    file and the R16 external declaration reproduce the wiring the probes
    were written against -- and not merely something like it."""
    report = checked(driven["spool"])
    assert report["failures"] == []
    assert report["ok"] is True
    assert report["exit"] == 0
    assert report["spools"] == len(probe_files())
    assert _detail(report, "focus:mode") == "unfocused"


def test_the_probes_checker_passes_its_focused_branch_against_the_driver(
        driven_focus):
    """R27. The focus tier, driven the way a consumer drives it: eleven
    `--focus` flags, resolved before the run, carried to every worker in one
    variable, and read back by the checker as the statement rows and the
    captured arguments its markers name. The unfocused run above is the
    control -- same probes, same driver, one flag apart."""
    report = checked(driven_focus["spool"])
    assert report["failures"] == []
    assert report["ok"] is True
    assert report["exit"] == 0
    assert report["spools"] == len(probe_files())
    assert _detail(report, "focus:mode") == "focused"
    assert _detail(report, "focus:caps")["line"] is True


def test_the_driven_focus_is_recorded_as_typed_and_as_resolved(driven_focus):
    """What the driver settled before the run, kept beside the spools: the
    eleven specs as they were typed, and every function they selected."""
    record = json.loads(
        (driven_focus["spool"] / "invocation.json").read_text())
    assert record["focus"] == FOCUS
    matched = record["focus_matched"]
    assert matched == sorted(matched)
    assert all(m.startswith("src/focus.probe.test.ts:") for m in matched)
    assert {f"src/focus.probe.test.ts:{fn}" for fn in FOCUS_FUNCTIONS} <= \
        set(matched)


def test_the_focus_list_is_the_one_the_probes_wire_themselves():
    """The probe project's config focuses the same functions with no driver
    at all. Two copies of one list is two ways to drift: a function added to
    the probe and to the config, and a driven run that never focuses it."""
    config = (PROBES / "vitest.config.ts").read_text()
    body = config.split("const FOCUS = [", 1)[1].split("]", 1)[0]
    assert re.findall(r"'([^']+)'", body) == list(FOCUS_FUNCTIONS)


def _detail(report: dict, check_id: str):
    """One check's detail out of a checker report, by id."""
    hits = [c for c in report["checks"] if c["id"] == check_id]
    assert len(hits) == 1, f"{check_id}: {hits}"
    return hits[0]["detail"]


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


# -- the config shape this recorder refuses ---------------------------------

PROJECTS_CONFIG = """\
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    projects: [
      { test: { name: 'alpha', include: ['alpha/*.test.ts'] } },
    ],
  },
});
"""

ALPHA_TEST = """\
import { expect, test } from 'vitest';

test('runs', () => {
  expect(1 + 1).toBe(2);
});
"""


def test_a_projects_config_is_refused_by_name_and_records_nothing(tmp_path):
    """R41, against a real vitest. A `test.projects` config makes vitest
    resolve a config PER PROJECT, and this wrapper merges onto one: the
    plugin never reaches the projects' pipelines, so the suite runs and
    nothing is recorded. Measured before the fix, that came back as the
    CONVERTER's sentence -- "no spools in <dir>: nothing was recorded, or
    the recorder wrote somewhere else" -- at the right exit status and
    naming neither the cause nor the fix.

    The project's `node_modules` is the probes' own, by symlink: the
    wrapper has to live under a `node_modules` for `vitest/config` to
    resolve, and the driver takes its directory back in a `finally`.
    """
    root = tmp_path / "ws"
    (root / "alpha").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "ws", "type": "module"}\n')
    (root / "vitest.config.ts").write_text(PROJECTS_CONFIG)
    (root / "alpha" / "a.test.ts").write_text(ALPHA_TEST)
    (root / "node_modules").symlink_to(PROBES / "node_modules")

    store = tmp_path / "store"
    r = run_cli(["ts", "run", "--", "npx", "vitest", "run"], cwd=root,
                sensorium_dir=store)
    assert r.returncode == 2, r.stdout + r.stderr
    assert ("error: vitest projects/workspaces are not supported by "
            "sensorium-ts 0.3.0") in r.stderr, r.stderr
    # Nothing was recorded, and nothing pretends to have been.
    assert not (store / "traces").exists()
    assert "run: " not in r.stdout
    # And the wrapper is gone from the tree it was written into.
    assert not (PROBES / "node_modules" / ".sensorium").exists()


# -- the `node --test` harness ----------------------------------------------

#: The explicit file list `npm run probe:nodetest` runs, in its order. Node's
#: own default test patterns are not relied on: they would sweep the ten
#: vitest probes under `src/` into the same run, and those need a vitest.
NODETEST_PROBES = [
    "nodetest/async.probe.test.ts", "nodetest/ext.probe.test.mts",
    "nodetest/ext.probe.test.mjs", "nodetest/ext.probe.test.cjs"]


def test_the_nodetest_probes_and_controls_pass_through_the_driver(tmp_path):
    """Spec section 4.5's four files and two controls, driven the way a
    consumer drives them rather than by the probe project's own script.

    One test file per extension: the `.ts` and the `.mts` are typed and are
    stripped by NODE, the `.mjs` has nothing to strip, and the `.cjs` is
    excluded and counted -- and the controls hold the other half of H1/H2,
    that a file Node refuses to load is refused identically with this
    recorder in front of it. `check.mjs` is the gate on the first four;
    `controls.mjs`'s exit status is the gate on the two.
    """
    store = tmp_path / "store"
    r = run_cli(["ts", "run", "--", "node", "--test", *NODETEST_PROBES],
                cwd=PROBES, sensorium_dir=store)
    assert r.returncode == 0, r.stdout + r.stderr
    m = INVOCATION.search(r.stdout)
    assert m, r.stdout + r.stderr
    spool = store / "spool" / m.group(1)

    check = subprocess.run(
        ["node", "check.mjs", "nodetest", str(spool), str(spool / "manifests")],
        cwd=PROBES, capture_output=True, text=True)
    report = json.loads(check.stdout or "{}")
    assert report.get("failures") == [], check.stdout + check.stderr
    assert report["ok"] is True
    assert check.returncode == 0

    controls = subprocess.run(
        ["node", "nodetest/controls.mjs"], cwd=PROBES, capture_output=True,
        text=True, env=dict(os.environ, SENSORIUM_TS_ROOT=str(PROBES),
                            SENSORIUM_TS_PKG=str(pkg_mod.locate())))
    assert controls.returncode == 0, controls.stdout + controls.stderr
