"""The driver's exit-2 refusal for a `--focus` that matches nothing.

This cannot be a corpus case. A corpus case records ONCE, with one argv, and
every question is asked of the trace that recording produced -- so a case
whose recording is refused has no trace to ask anything of, and
`run_corpus.py` reports it as `recording failed`, which is the shape of a
BROKEN case rather than a passing one. The refusal is nonetheless the
promise that keeps `--focus` honest (design §2.2: a value matching nothing
refuses *before any rewrite or compile*, so a typo'd focus can never be read
as an unfocused run that quietly recorded no locals), so it is pinned here
instead, against the same corpus crate the focused cases use.

Two facts, and the second is the one a substring assertion would lose:
the SENTENCE, and that **nothing was built** -- no target directory, no
trace store, no mirror. A driver that refused after rewriting would print the
same sentence.

Skipped BY NAME when there is no driver on the box, exactly as
`run_corpus.py` skips the cargo cases: the Python CI matrix has no Rust
toolchain, and "could not run" and "passed" are the two facts that must not
read alike.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from sensorium.driver import cargo_sensorium

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "corpus" / "rust" / "focus_let_chain"


def _scratch_target(tmp_path: Path) -> Path:
    """Where the control test's real build goes.

    Only the control needs this. The two refusal tests point at a fresh
    `tmp_path` subdirectory instead, because their assertion is that the
    directory never comes to exist -- and an assertion of non-existence
    against a path another test in the same file creates would pass or fail
    on test ORDER rather than on the driver's behaviour.

    A SUBDIRECTORY of `CARGO_TARGET_DIR` when the caller set one, so the
    build lands wherever the gate already puts its artifacts (off a
    near-full root disk, inside a CI runner's workspace) -- but never that
    directory ITSELF, because a focused build of this crate must not be able
    to reuse or poison the artifacts the corpus cases depend on. With no
    `CARGO_TARGET_DIR`, pytest's own `tmp_path`, which is cleaned up for us.

    No path in this file is specific to one machine: a test that names a
    mount point fails with `PermissionError` on a box that lacks it instead
    of skipping, which is the one failure mode the skip-by-name discipline
    exists to prevent.
    """
    base = os.environ.get("CARGO_TARGET_DIR")
    return Path(base) / "focus-refusal" if base else tmp_path / "target"


#: The same resolution `run_corpus.cargo_driver` and `refocus` use, because
#: it is now the same function. This module's skip and the corpus's skip
#: have to agree about whether a driver exists, or a box would run the gate
#: and skip its fence, or the other way round.
_driver = cargo_sensorium


requires_driver = pytest.mark.skipif(
    _driver() is None,
    reason="no cargo-sensorium (SENSORIUM_CARGO_SENSORIUM unset and none on "
           "PATH) -- the driver's refusal cannot be asked for")


@pytest.fixture
def crate(tmp_path):
    """The corpus crate, copied whole, exactly as the corpus harness copies
    it -- without `target` or `Cargo.lock`, so a local build lying around
    cannot make this run pass or fail."""
    wd = tmp_path / "focus_let_chain"
    shutil.copytree(CASE, wd, ignore=shutil.ignore_patterns(
        "__pycache__", "target", "Cargo.lock", ".sensorium"))
    return wd


def _run(crate: Path, focus: str, target: Path):
    return subprocess.run(
        [_driver(), "sensorium", "--focus", focus, "run"],
        cwd=crate, capture_output=True, text=True,
        env={**os.environ,
             "SENSORIUM_DIR": str(crate / ".sensorium"),
             "CARGO_TARGET_DIR": str(target),
             "PYTHONDONTWRITEBYTECODE": "1"})


@requires_driver
def test_a_focus_matching_nothing_refuses_with_the_closest_names(crate,
                                                                 tmp_path):
    target = tmp_path / "target"
    r = _run(crate, "no_such_fn", target)

    # Exit 2 is BAD_CALL, the rung-3 exit-status convention: the fault is in
    # the command, not in the recording -- which is what separates it from
    # the capability refusals (`watch` on a `line: false` trace) that exit 3.
    assert r.returncode == 2, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    out = r.stdout + r.stderr
    assert ("REFUSED: --focus no_such_fn matches no function in the "
            "workspace; nothing was built. Closest: ") in out
    # The suggestion is the half that makes the refusal usable rather than
    # merely correct, so it is asserted separately: the crate's own eligible
    # qualname must be among the names offered.
    closest = out.split("Closest: ", 1)[1].strip()
    assert "fill" in closest.split(", "), closest


@requires_driver
def test_the_refusal_builds_nothing(crate, tmp_path):
    """Design §2.2: the resolution happens BEFORE cargo is invoked. If the
    refusal came after a rewrite, the sentence would be identical and only
    the filesystem would know."""
    # A path pytest guarantees is fresh, so "it must not come to exist" is a
    # claim about the driver and about nothing else.
    target = tmp_path / "target"
    assert _run(crate, "no_such_fn", target).returncode == 2
    assert not target.exists(), "a refused focus built into the target dir"
    assert not (crate / ".sensorium").exists(), "a refused focus wrote a store"
    # The sharpest of the three: cargo writes `Cargo.lock` on ANY invocation,
    # even one that resolves dependencies and stops. Its absence says cargo
    # was never reached, which is stronger than "no artifacts were produced".
    assert not (crate / "Cargo.lock").exists(), "cargo was invoked after all"


@requires_driver
def test_a_focus_that_matches_is_not_refused(crate, tmp_path):
    """The control. Without it, a driver that refused EVERY `--focus` would
    pass both tests above.

    This is the only test here that really builds, so it is also the only one
    that leaves anything behind -- a shim copy and one artifact set, tens of
    megabytes (design amendment A8: every distinct focus gets its own). It is
    REMOVED rather than reused: the reuse would save a second on a rerun and
    cost a scratch directory that nothing on the box owns.
    """
    target = _scratch_target(tmp_path)
    target.mkdir(parents=True, exist_ok=True)
    try:
        r = _run(crate, "fill", target)
    finally:
        shutil.rmtree(target, ignore_errors=True)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    out = r.stdout + r.stderr
    assert "REFUSED" not in out
    # The driver's own echo of what it resolved, and the `run:` line that only
    # a completed recording prints: a build that produced nothing would have
    # the first without the second.
    assert "focus: fill" in out
    assert "run: " in r.stdout
