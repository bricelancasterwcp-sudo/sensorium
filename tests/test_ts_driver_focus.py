"""`sensorium ts run --focus`: what the driver settles BEFORE it runs anything.

A focus is the one flag whose mistakes are silent. A spec that matches
nothing records a whole program the caller did not ask for; a spec that
matches only a function the transform never instruments records nothing and
says the run was fine. So the driver resolves every spec against the root
first -- through the recorder's own resolver, which reuses the transform's
pass one, so the resolver and the transform cannot disagree -- and a bad
spec is a refusal at exit 2 with nothing minted and nothing spawned.

The harness here is `node --test`, as in `test_ts_driver.py`, whose fixtures
this module reuses: no vitest, one process tree, a real Node.
"""
import argparse
import json
import os
import shutil
from pathlib import Path

import pytest

from sensorium.ts import driver as driver_mod
from sensorium.ts import focus as focus_mod
from sensorium.ts import invocation
from sensorium.ts import pkg as pkg_mod
from tests.helpers import run_cli
from tests.test_ts_driver import SKIP, TEST, only_trace

pytestmark = pytest.mark.skipif(SKIP is not None, reason=SKIP or "")

#: `test_ts_driver.py`'s library, with one statement that is not the return.
#: A `return` is the frame's RETURN record and mints no statement row of its
#: own, so a function whose whole body is one would prove nothing about the
#: rows a focus is for. The test file beside it is unchanged: `add` still
#: adds.
LIB = """\
export function add(a: number, b: number): number {
  const sum = a + b;
  return sum;
}
"""

#: A function-like this recorder never instruments, and no eligible one in
#: the file: an ambient declaration is the shortest honest example.
DECL = """\
declare module 'legacy-dep' {
  export function legacy(a: number): number;
}
"""

#: A root with no function-like at all, for the refusal that has nothing to
#: suggest.
TYPES = "export type Pair = { a: number; b: number };\n"


@pytest.fixture
def project(tmp_path):
    """`test_ts_driver.py`'s `node --test` project: two files and the one
    dependency the loader hook resolves from the ROOT."""
    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "app", "type": "module"}\n')
    (root / "lib.ts").write_text(LIB)
    (root / "a.test.ts").write_text(TEST % 3)
    (root / "node_modules" / "typescript").symlink_to(
        pkg_mod.locate() / "node_modules" / "typescript")
    return root


def drive(project, sdir, *extra, env_extra=None):
    return run_cli(["ts", "run", *extra, "--", "node", "--test", "a.test.ts"],
                   cwd=project, sensorium_dir=sdir, env_extra=env_extra)


def spool_of(sdir: Path) -> Path:
    """The one spool directory this store holds, found without reading the
    driver's own report: a run whose conversion refused prints no
    `invocation:` line, and the directory is the fact under test."""
    spools = sorted((sdir / "spool").iterdir())
    assert len(spools) == 1, spools
    return spools[0]


def records(spool: Path) -> list[dict]:
    return [json.loads(line)
            for path in sorted(spool.glob("*.jsonl"))
            for line in path.read_text(encoding="utf-8").splitlines()
            if line != ""]


# -- a focus that resolves ---------------------------------------------------

def test_a_focused_run_records_the_focus_it_was_given_and_what_it_matched(
        project, tmp_path):
    """`invocation.json` carries both lists: the specs AS TYPED, which is
    what a reader recognises, and the `rel:qualname` of every function they
    selected, which is what says whether the spec meant what its author
    thought. The harness ran, and the recorder in it emitted the statement
    rows a focus is for -- which is the whole plumbing in one assertion:
    the variable reached the child, the transform focused the function the
    resolver named, and the runtime wrote its rows."""
    sdir = tmp_path / "sdir"
    drive(project, sdir, "--focus", "lib.ts:add")
    spool = spool_of(sdir)

    record = json.loads((spool / "invocation.json").read_text())
    assert record["focus"] == ["lib.ts:add"]
    assert record["focus_matched"] == ["lib.ts:add"]
    # And read back through the contract the converter reads it through,
    # not only as the JSON this test wrote it as.
    read = invocation.read_invocation(spool)
    assert read.focus == ["lib.ts:add"]
    assert read.focus_matched == ["lib.ts:add"]

    ending = json.loads((spool / "harness.json").read_text())
    assert ending["status"] == 0, ending

    recs = records(spool)
    assert [r for r in recs if r["e"] == "LINE"], [r["e"] for r in recs]
    boot = recs[0]
    assert boot["e"] == "BOOT"
    assert boot["capabilities"]["line"] is True
    assert boot["capabilities"]["locals"] is True


def test_an_unfocused_run_writes_the_two_keys_empty(project, tmp_path):
    """The keys are always written, and empty is the honest value: a reader
    of a spool directory should not have to know which recorder version
    wrote it to know that nothing was focused."""
    sdir = tmp_path / "sdir"
    r = drive(project, sdir)
    assert r.returncode == 0, r.stdout + r.stderr
    record = json.loads((spool_of(sdir) / "invocation.json").read_text())
    assert record["focus"] == []
    assert record["focus_matched"] == []
    assert [rec for rec in records(spool_of(sdir)) if rec["e"] == "LINE"] == []


@pytest.mark.xfail(strict=True,
                   reason="the converter learns the LINE record at Task 6")
def test_the_trace_says_what_was_focused(project, tmp_path):
    """What the whole tier is for, and the one assertion this task cannot
    make yet: the converter has no rule for a LINE record until Task 6, so
    the focused container's spool is REFUSED (`no rule for a LINE record`)
    and no trace is written -- while `meta.focus` is Task 6's key besides.
    Left here, strict, so the task that teaches the converter cannot land
    without being told this passes now."""
    sdir = tmp_path / "sdir"
    r = drive(project, sdir, "--focus", "lib.ts:add")
    assert r.returncode == 0, r.stdout + r.stderr
    trace = only_trace(sdir)
    assert trace.meta["focus"] == ["lib.ts:add"]
    assert trace.meta["focus_matched"] == ["lib.ts:add"]
    assert trace.meta["capabilities"]["line"] is True
    assert trace.events(kind="LINE")


# -- a focus that does not ---------------------------------------------------

def test_a_spec_matching_nothing_is_refused_before_anything_is_minted(
        project, tmp_path):
    """The refusal names the spec, the root and the closest eligible names,
    and it happens before `new_run_id()`: no spool directory, no record, no
    harness -- a run nobody wanted is not half-recorded."""
    sdir = tmp_path / "sdir"
    r = drive(project, sdir, "--focus", "nope")
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stderr.strip() == (
        f"error: --focus nope matches no function under {project}; "
        "nothing was run. Closest: add")
    assert "Traceback" not in r.stderr
    assert not (sdir / "spool").exists()
    assert not (sdir / "traces").exists()


def test_a_refused_focus_mints_nothing_beside_the_runs_already_there(
        project, tmp_path):
    """The refusal above sees an empty store, where "nothing was minted" and
    "nothing exists" look alike. Here a run has already happened: what must
    not change is the COUNT of spool directories, nor the contents of the
    one that is there. (The command journal DOES gain a line -- it journals
    commands, and this one was typed.)"""
    sdir = tmp_path / "sdir"
    drive(project, sdir)
    before = {d: sorted(p.name for p in d.iterdir())
              for d in (sdir / "spool").iterdir()}

    r = drive(project, sdir, "--focus", "nope")
    assert r.returncode == 2
    assert {d: sorted(p.name for p in d.iterdir())
            for d in (sdir / "spool").iterdir()} == before


def test_one_bad_spec_among_good_ones_refuses_the_whole_run(project,
                                                            tmp_path):
    """A partly-good focus is not a focus: recording `add` while silently
    dropping `nope` would answer a question nobody asked, and the caller
    would read the trace as though both had been recorded."""
    sdir = tmp_path / "sdir"
    r = drive(project, sdir, "--focus", "add", "--focus", "nope")
    assert r.returncode == 2, r.stdout + r.stderr
    assert len(r.stderr.strip().splitlines()) == 1, r.stderr
    assert r.stderr.strip().startswith("error: --focus nope matches no ")
    assert not (sdir / "spool").exists()


def test_every_bad_spec_gets_its_own_line(project, tmp_path):
    """One line per bad spec: a caller who mistyped twice is told twice,
    rather than being sent round the loop once per typo."""
    sdir = tmp_path / "sdir"
    r = drive(project, sdir, "--focus", "nope", "--focus", "alsonope")
    assert r.returncode == 2
    lines = r.stderr.strip().splitlines()
    assert len(lines) == 2, r.stderr
    assert lines[0].startswith("error: --focus nope matches no function")
    assert lines[1].startswith("error: --focus alsonope matches no function")


def test_a_spec_matching_only_an_uninstrumented_function_says_so(project,
                                                                 tmp_path):
    """The refusal a bare "matches no function" would be a lie for: the
    name IS in the tree, and the reason it cannot be recorded is a property
    of the recorder, not of the spelling."""
    (project / "decl.ts").write_text(DECL)
    sdir = tmp_path / "sdir"
    r = drive(project, sdir, "--focus", "legacy")
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stderr.strip() == (
        "error: --focus legacy matches only functions this recorder does "
        "not instrument (ambient x1); nothing was run.")
    assert not (sdir / "spool").exists()


def test_a_root_with_nothing_eligible_is_offered_nothing(tmp_path):
    """`Closest:` is dropped rather than printed empty. A root this
    recorder can instrument nothing in is a different problem from a
    mistyped name, and a suggestion list of nothing says neither."""
    root = tmp_path / "bare"
    (root / "node_modules").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "bare", "type": "module"}\n')
    (root / "types.ts").write_text(TYPES)
    (root / "node_modules" / "typescript").symlink_to(
        pkg_mod.locate() / "node_modules" / "typescript")
    r = run_cli(["ts", "run", "--focus", "gone", "--", "node", "--test",
                 "types.test.ts"], cwd=root, sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stderr.strip() == (
        f"error: --focus gone matches no function under {root}; "
        "nothing was run.")


def test_an_empty_spec_is_refused_rather_than_dropped(project, tmp_path):
    """An empty qualname is a prefix of every name there is. Dropped, the
    flag did nothing and said nothing; honoured, it focuses the whole
    program. So it is neither, and the refusal says what a spec is."""
    sdir = tmp_path / "sdir"
    r = drive(project, sdir, "--focus", "add", "--focus", "")
    assert r.returncode == 2, r.stdout + r.stderr
    assert r.stderr.strip() == (
        "error: --focus was given nothing to name: a spec is a <qualname> "
        "or a <file>:<qualname>")
    assert not (sdir / "spool").exists()


def test_a_package_that_cannot_resolve_a_focus_is_refused_by_name(project,
                                                                  tmp_path):
    """The package's own refusal shape (`pkg.check`'s), for the file this
    flag needs: a recorder that fell back to "no matches" would blame the
    caller's spelling for its own missing script."""
    fake = tmp_path / "fakepkg"
    (fake / "node_modules" / "magic-string").mkdir(parents=True)
    r = drive(project, tmp_path / "sdir", "--focus", "add",
              env_extra={pkg_mod.ENV_VAR: str(fake)})
    assert r.returncode == 2, r.stdout + r.stderr
    assert len(r.stderr.strip().splitlines()) == 1, r.stderr
    assert "resolve.mjs" in r.stderr
    assert str(fake) in r.stderr


# -- the pieces, without a run -----------------------------------------------

def test_the_resolution_names_every_matched_function_once_and_sorted():
    res = focus_mod.Resolution(
        matched=[{"rel": "src/b.ts", "qualname": "g", "line": 2,
                  "kind": "function"},
                 {"rel": "src/a.ts", "qualname": "f", "line": 1,
                  "kind": "coroutine"}],
        unmatched=[], excluded_only=[], files_scanned=2, files_unparsable=0,
        wall=0.0)
    assert res.matched_specs == ["src/a.ts:f", "src/b.ts:g"]


def test_the_refusal_lines_are_one_per_bad_spec():
    res = focus_mod.Resolution(
        matched=[], unmatched=[{"spec": "refrsh", "closest": ["refresh"]},
                               {"spec": "gone", "closest": []}],
        excluded_only=[{"spec": "decl",
                        "reasons": {"ambient": 2, "abstract": 1}}],
        files_scanned=1, files_unparsable=0, wall=0.0)
    assert focus_mod.refusals(res, Path("/w")) == [
        "--focus refrsh matches no function under /w; nothing was run. "
        "Closest: refresh",
        "--focus gone matches no function under /w; nothing was run.",
        "--focus decl matches only functions this recorder does not "
        "instrument (abstract x1, ambient x2); nothing was run.",
    ]


def test_the_resolver_is_run_with_the_root_and_the_specs_in_its_environment(
        project, tmp_path):
    """The one call the driver makes, made directly: the specs go as typed,
    joined by the separator, and the answer counts the files it walked."""
    res = focus_mod.resolve(project, pkg_mod.locate(),
                            ["lib.ts:add", "a.test.ts:add"])
    assert res.matched_specs == ["lib.ts:add"]
    assert res.unmatched == [{"spec": "a.test.ts:add", "closest": ["add"]}]
    assert res.files_scanned == 2 and res.files_unparsable == 0
    assert res.wall > 0


def test_a_resolver_that_fails_is_a_package_error_naming_its_stderr(tmp_path):
    fake = tmp_path / "fakepkg"
    fake.mkdir()
    with pytest.raises(pkg_mod.PackageError) as e:
        focus_mod.resolve(tmp_path, fake, ["add"])
    assert "resolve.mjs" in str(e.value)


def test_a_focus_in_the_callers_shell_is_not_this_runs_focus(tmp_path,
                                                             monkeypatch):
    """`SENSORIUM_FOCUS` is the recorder's own variable, and the driver is
    the one that sets it. Inherited, it would focus a run whose own record
    says `focus: []` -- statement rows nobody asked for, and a record beside
    them denying they were asked for. (Which variable goes where is
    `test_ts_driver.py`'s seven-things test; this is the override alone.)"""
    from sensorium.ts import harness as harness_mod

    monkeypatch.setenv("SENSORIUM_FOCUS", "left over from a shell")
    plan = harness_mod.recognise(["vitest", "run"], tmp_path)
    assert "SENSORIUM_FOCUS" not in driver_mod._env(
        tmp_path / "spool", "INV", plan, tmp_path / "pkg", "call", [])
    assert driver_mod._env(tmp_path / "spool", "INV", plan,
                           tmp_path / "pkg", "call",
                           ["f"])["SENSORIUM_FOCUS"] == "f"


def test_a_run_with_no_focus_flag_resolves_nothing(project, tmp_path,
                                                   monkeypatch):
    """The resolver is a Node process per invocation: an unfocused run must
    not pay for it, and must not need it to exist."""
    calls = []
    monkeypatch.setattr(focus_mod, "resolve",
                        lambda *a, **k: calls.append(a))
    monkeypatch.chdir(project)
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    args = argparse.Namespace(command=["--", "node", "--test", "a.test.ts"],
                              tier="call", jobs=None, focus=[])
    assert driver_mod.run(args) == 0
    assert calls == []
