"""The repo-wide 800-line ceiling gate (design ruling R1).

Covers code and living docs: every tracked `*.py`, `*.rs`, `*.sh` file,
plus `README.md`, `docs/*.md` and `rust/*.md` -- which is to say `src/`,
`tests/`, `rust/` (crates and `rust/tests/`), `corpus/`, and the
repository's top-level documentation, all at once, by pattern rather than
by a hand-maintained list.

Exempt, by name and only by name: `docs/superpowers/acceptance/`,
`docs/superpowers/plans/` and `docs/superpowers/specs/`. Those three hold
dated history -- some byte-locked -- and are never edited after the fact
except by appended amendments; a record growing past 800 lines as its
history accumulates is accepted, because a record is read by section, not
end to end the way a module is. Nothing else is exempt. `test_the_
exemption_list_is_exactly_these_three_record_directories` below pins the
list itself, so a fourth entry cannot be added silently to widen it.

This gate lands AFTER Tasks 1-4 split every file this branch pushed over
800 lines (`docs/superpowers/sdd/2026-09-08-sensorium-debts-buttonup-
design.md` R2) -- it is the check that those splits actually cleared the
ceiling, not the mechanism that clears it. A file this gate names is a
Task 1-4 miss: the fix is to split that file at its seam, the same way the
eleven others were split, never to widen `EXEMPT` to cover it.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: The ceiling itself. Lower this to see the gate name files -- that is
#: the mutation check for this module, not a way to tighten the gate.
LIMIT = 800

#: Passed straight to `git ls-files --`. `docs/*.md` and `rust/*.md` reach
#: every markdown file under those trees (git's pathspec glob is not
#: shell-anchored to one directory level), so this already covers nested
#: docs -- `EXEMPT` is what carves the record directories back out.
PATTERNS = ("*.py", "*.rs", "*.sh", "README.md", "docs/*.md", "rust/*.md")

#: The record directories (R1): dated history, some byte-locked, never
#: edited after the fact except by appended amendments. Exactly these
#: three -- see the test below that pins this tuple.
EXEMPT = (
    "docs/superpowers/acceptance/",
    "docs/superpowers/plans/",
    "docs/superpowers/specs/",
)


def _tracked_files() -> tuple[str, ...]:
    """The enumeration this gate checks: git's own tracked-file list,
    filtered by `EXEMPT`. Skips rather than passing silently when `git`
    cannot answer -- an empty enumeration from a broken `git` would
    otherwise report as a full, passing gate."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--", *PATTERNS],
            cwd=REPO, capture_output=True, text=True,
        )
    except FileNotFoundError:
        pytest.skip("git is not available on this machine",
                     allow_module_level=True)
    if proc.returncode != 0:
        pytest.skip(f"{REPO} is not a git repository: {proc.stderr.strip()}",
                     allow_module_level=True)
    paths = [p for p in proc.stdout.splitlines() if p]
    return tuple(p for p in paths if not p.startswith(EXEMPT))


FILES = _tracked_files()


@pytest.mark.parametrize("relpath", FILES, ids=FILES)
def test_every_covered_file_is_under_the_ceiling(relpath):
    n = len((REPO / relpath).read_text().splitlines())
    assert n <= LIMIT, f"{relpath} is {n} lines (limit {LIMIT})"


def test_the_exemption_list_is_exactly_these_three_record_directories():
    """A future record directory does not become exempt by editing this
    tuple in passing -- widening it is a deliberate, reviewable change to
    the assertion below, not a side effect of some other fix."""
    assert EXEMPT == (
        "docs/superpowers/acceptance/",
        "docs/superpowers/plans/",
        "docs/superpowers/specs/",
    )
    for prefix in EXEMPT:
        assert (REPO / prefix).is_dir(), prefix


def test_the_enumeration_is_not_empty_and_spans_every_covered_directory():
    """A gate over an empty set is not a gate: it would pass forever, for
    the same reason a test with no assertions passes forever."""
    assert FILES, "the gate enumerated no files"
    for prefix in ("src/", "tests/", "rust/", "corpus/", "docs/"):
        assert any(p.startswith(prefix) for p in FILES), prefix
