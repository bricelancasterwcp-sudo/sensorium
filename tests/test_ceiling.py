"""The repo-wide 800-line ceiling gate (design ruling R1, widened
2026-09-08 by the final fix wave, and again 2026-09-09 by ruling R43).

Covers code and living docs: every tracked `*.py`, `*.rs`, `*.sh`, `*.md`,
`*.mjs`, `*.ts` and `*.tsx` file -- which is to say `src/`, `tests/`,
`rust/` (crates and `rust/tests/`), `corpus/`, `docs/`, `typescript/` and
every markdown file at the repository root, all at once, by pattern rather
than by a hand-maintained list.

The three TypeScript patterns are R43: the gate shipped naming every
language in the repository except the one rung 1 added, so the recorder's
whole Node side sat outside the ceiling from its first commit. They walk
TRACKED files only, which is what keeps `typescript/node_modules` and
`package-lock.json` out of the enumeration without a single exclusion
rule -- neither is tracked.

`*.md` whole rather than `README.md`, `docs/*.md` and `rust/*.md`: the
named form was three patterns that happened to cover the markdown that
existed when it was written, and it silently missed `CHANGELOG.md` (798
lines, two from the ceiling), `ORIGIN.md` and `corpus/rust/README.md`. A
gate whose scope is a list of the files someone remembered is a gate that
grows a hole every time a document is added at a new path, so the scope is
the whole extension and `EXEMPT` is the only thing that carves it back.

Exempt, by name and only by name: `docs/superpowers/acceptance/`,
`docs/superpowers/plans/` and `docs/superpowers/specs/`. Those three hold
dated history -- some byte-locked -- and are never edited after the fact
except by appended amendments; a record growing past 800 lines as its
history accumulates is accepted, because a record is read by section, not
end to end the way a module is. Nothing else is exempt. `test_the_
exemption_list_is_exactly_these_three_record_directories` below pins the
list itself, so a fourth entry cannot be added silently to widen it.

This gate lands AFTER Tasks 1-4 split every file this branch pushed over
800 lines (`docs/superpowers/specs/2026-09-08-sensorium-debts-buttonup-
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

#: Passed straight to `git ls-files --`. A bare `*.md` reaches every tracked
#: markdown file at any depth (git's pathspec glob is not shell-anchored to
#: one directory level), so the enumeration is every living document in the
#: repository -- `EXEMPT` is what carves the record directories back out.
PATTERNS = ("*.py", "*.rs", "*.sh", "*.md", "*.mjs", "*.ts", "*.tsx")

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
    for prefix in ("src/", "tests/", "rust/", "corpus/", "docs/",
                   "typescript/"):
        assert any(p.startswith(prefix) for p in FILES), prefix


def test_the_widened_markdown_scope_reaches_the_repository_root():
    """What `*.md` buys over the three named patterns it replaced.

    Three were tracked, living markdown that no pattern named:
    `CHANGELOG.md` at 798 lines, two from the ceiling and rising with every
    release; `ORIGIN.md`; and `corpus/rust/README.md`. The fourth,
    `CHANGELOG-ARCHIVE.md`, is the volume the same wave cut out of the
    first, and it is covered from its first commit rather than from the
    day someone remembers to add a pattern for it. Naming the four here
    rather than trusting the glob is the check that the widening actually
    happened -- `PATTERNS` narrowed back to `README.md` would still pass
    every assertion above.
    """
    for relpath in ("CHANGELOG.md", "CHANGELOG-ARCHIVE.md", "ORIGIN.md",
                    "corpus/rust/README.md"):
        assert relpath in FILES, relpath


def test_the_typescript_scope_reaches_the_recorders_node_sources():
    """What `*.mjs`, `*.ts` and `*.tsx` buy (R43).

    The gate shipped covering `*.py`, `*.rs`, `*.sh` and `*.md`, which is
    every language in the repository EXCEPT the one rung 1 added: the
    recorder's whole Node side -- runtime, transform, plugin, loader hook
    and their tests -- was outside the ceiling from its first commit. Four
    files are named here rather than trusting the glob, one per shape the
    three patterns reach: a `.mjs` source, a `.mjs` test, a `.ts` golden
    and the one `.tsx` in the tree. `PATTERNS` narrowed back to the four
    it shipped with would still pass every assertion above.
    """
    for relpath in ("typescript/src/transform.mjs",
                    "typescript/test/rt.test.mjs",
                    "typescript/test/golden/yield.ts",
                    "typescript/test/golden/component.tsx"):
        assert relpath in FILES, relpath
