"""The release tokens: the version, spelled the same in every place it lands.

Three places carry this package's number and they drift silently. `pyproject`
declares it; the installed distribution reports it (`importlib.metadata`, the
token a trace's own version probe reads); the CHANGELOG's newest header names
it. Nothing in the suite noticed when one of them moved without the others --
a slice could ship a CHANGELOG entry for a version the package never became,
and the only signal would be a reader eventually squinting at two numbers.

The rule has TWO legal states, so the test never lies mid-slice:

* `## X.Y.Z (unreleased)` -- the entry is being written for a version
  `pyproject` has not been bumped to yet. The only number that can legally be
  is the next patch above the declared one: a slice that means to ship a minor
  or a major bumps `pyproject` in the same commit it writes that header.
* `## X.Y.Z — YYYY-MM-DD` -- the release happened, so the CHANGELOG's number
  and the declared one are the same fact, and the date is a real date.

The shape rules live in functions here rather than inline in one assertion, so
each of them can be shown to REFUSE the thing it is for -- a rule that has
only ever been run against a repo that already satisfies it has not been
tested at all.
"""
import re
import tomllib
from datetime import date
from importlib.metadata import version as installed_version
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

#: `## 0.8.5 — 2026-09-07`: an entry that shipped. The dash is an em dash,
#: as every entry in the file uses.
DATED = re.compile(
    r"^## (?P<version>\d+\.\d+\.\d+) — (?P<date>\d{4}-\d{2}-\d{2})$")
#: `## 0.8.6 (unreleased)`: an entry whose slice is still open.
UNRELEASED = re.compile(r"^## (?P<version>\d+\.\d+\.\d+) \(unreleased\)$")


def declared_version(pyproject_text: str) -> str:
    """The version `pyproject.toml` declares."""
    return tomllib.loads(pyproject_text)["project"]["version"]


def newest_header(changelog_text: str) -> str:
    """The first `## ` line: the CHANGELOG is newest-first."""
    for line in changelog_text.splitlines():
        if line.startswith("## "):
            return line
    raise AssertionError("the CHANGELOG has no `## ` header at all")


def next_patch(version: str) -> str:
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


def check_newest_header(header: str, declared: str) -> None:
    """Raise `AssertionError` unless `header` is legal for `declared`."""
    dated = DATED.match(header)
    if dated:
        assert dated["version"] == declared, (
            f"the CHANGELOG's newest entry is dated {dated['version']} but "
            f"pyproject declares {declared}: a released entry names the "
            "version the package IS")
        try:
            date.fromisoformat(dated["date"])
        except ValueError as e:
            raise AssertionError(f"{header!r}: {e}") from None
        return
    unreleased = UNRELEASED.match(header)
    assert unreleased, (
        f"the CHANGELOG's newest header is neither `## X.Y.Z (unreleased)` "
        f"nor `## X.Y.Z — YYYY-MM-DD`: {header!r}")
    assert unreleased["version"] == next_patch(declared), (
        f"the CHANGELOG's unreleased entry is {unreleased['version']} but "
        f"pyproject declares {declared}: an unreleased entry names the next "
        f"patch ({next_patch(declared)}), and a slice shipping a bigger jump "
        "bumps pyproject in the same commit")


# -- the repository itself ---------------------------------------------------
def test_the_installed_distribution_reports_the_declared_version():
    """`importlib.metadata` is the token the E4-family version probe reads.

    An editable install keeps its own metadata, so this also catches the
    ordinary mistake of bumping `pyproject` and never reinstalling: the
    package would report the old number to anything that asked.
    """
    declared = declared_version((ROOT / "pyproject.toml").read_text())
    assert installed_version("sensorium") == declared


def test_the_newest_changelog_header_agrees_with_pyproject():
    declared = declared_version((ROOT / "pyproject.toml").read_text())
    header = newest_header((ROOT / "CHANGELOG.md").read_text())
    check_newest_header(header, declared)


def test_the_changelog_is_newest_first_and_the_header_is_line_three():
    """Where the header is, so `newest_header` reads the entry it means to."""
    lines = (ROOT / "CHANGELOG.md").read_text().splitlines()
    assert lines[0] == "# Changelog"
    assert lines[2].startswith("## ")


# -- the rules refuse what they are for --------------------------------------
def test_an_unreleased_header_may_name_the_next_patch():
    check_newest_header("## 0.8.6 (unreleased)", "0.8.5")


@pytest.mark.parametrize("header", [
    "## 0.8.5 (unreleased)",   # the version already declared
    "## 0.8.7 (unreleased)",   # a patch skipped
    "## 0.9.0 (unreleased)",   # a minor, with pyproject not bumped for it
    "## 1.0.0 (unreleased)",
])
def test_an_unreleased_header_that_is_not_the_next_patch_is_refused(header):
    with pytest.raises(AssertionError, match="names the next patch"):
        check_newest_header(header, "0.8.5")


def test_a_dated_header_may_name_the_declared_version():
    check_newest_header("## 0.8.5 — 2026-09-07", "0.8.5")


def test_the_state_this_entry_reaches_on_release_day_is_legal():
    """The same header, dated, once `pyproject` has been bumped with it.

    Both states are green by construction, which is the whole point: the
    test cannot be the reason a slice puts off writing its entry.
    """
    check_newest_header("## 0.8.6 (unreleased)", "0.8.5")
    check_newest_header("## 0.8.6 — 2026-09-08", "0.8.6")


def test_a_dated_header_that_names_another_version_is_refused():
    with pytest.raises(AssertionError, match="names the version the package"):
        check_newest_header("## 0.8.6 — 2026-09-08", "0.8.5")


def test_a_dated_header_whose_date_is_not_a_date_is_refused():
    with pytest.raises(AssertionError, match="month must be in 1..12"):
        check_newest_header("## 0.8.5 — 2026-13-01", "0.8.5")


@pytest.mark.parametrize("header", [
    "## 0.8.6",                    # no state at all
    "## 0.8.5 - 2026-09-07",       # a hyphen where the file uses an em dash
    "## 0.8.5 — 2026-9-7",         # a date the file's shape would not print
    "## 0.8.6 (draft)",
    "## v0.8.6 (unreleased)",
    "## 0.8.6 (unreleased) — 2026-09-08",
])
def test_a_header_of_neither_shape_is_refused(header):
    with pytest.raises(AssertionError, match="is neither"):
        check_newest_header(header, "0.8.5")


def test_the_newest_header_is_the_first_one_not_the_last():
    """Newest-first: a rule that read the LAST header would pin 0.1.0."""
    text = "# Changelog\n\n## 0.8.6 (unreleased)\n\nx\n\n## 0.8.5 — 2026-09-07\n"
    assert newest_header(text) == "## 0.8.6 (unreleased)"


def test_a_changelog_with_no_header_is_refused():
    with pytest.raises(AssertionError, match="no `## ` header"):
        newest_header("# Changelog\n\nnothing here yet\n")


@pytest.mark.parametrize("version, expected", [
    ("0.8.5", "0.8.6"), ("0.8.9", "0.8.10"), ("1.0.0", "1.0.1"),
])
def test_next_patch_bumps_the_last_component(version, expected):
    assert next_patch(version) == expected
