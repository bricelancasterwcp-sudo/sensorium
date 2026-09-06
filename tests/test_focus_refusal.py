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

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "corpus" / "rust" / "focus_let_chain"

#: A scratch target directory on the second disk, beside the corpus gate's
#: own. Never the shared `corpus-target`: this invocation must not be able to
#: reuse -- or poison -- artifacts the corpus cases depend on.
TARGET = Path("/mnt/extra/sensorium-rung2/corpus-target-refusal")


def _driver() -> str | None:
    """The same resolution order `run_corpus.cargo_driver` uses."""
    return (os.environ.get("SENSORIUM_CARGO_SENSORIUM")
            or shutil.which("cargo-sensorium"))


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
    target = tmp_path / "target"
    assert _run(crate, "no_such_fn", target).returncode == 2
    assert not target.exists(), "a refused focus built into the target dir"
    assert not (crate / ".sensorium").exists(), "a refused focus wrote a store"
    # The sharpest of the three: cargo writes `Cargo.lock` on ANY invocation,
    # even one that resolves dependencies and stops. Its absence says cargo
    # was never reached, which is stronger than "no artifacts were produced".
    assert not (crate / "Cargo.lock").exists(), "cargo was invoked after all"


@requires_driver
def test_a_focus_that_matches_is_not_refused(crate):
    """The control. Without it, a driver that refused EVERY `--focus` would
    pass both tests above."""
    TARGET.mkdir(parents=True, exist_ok=True)
    r = _run(crate, "fill", TARGET)
    assert r.returncode == 0, f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"
    out = r.stdout + r.stderr
    assert "REFUSED" not in out
    # The driver's own echo of what it resolved, and the `run:` line that only
    # a completed recording prints: a build that produced nothing would have
    # the first without the second.
    assert "focus: fill" in out
    assert "run: " in r.stdout
