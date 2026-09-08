"""The seam between `refocus_cmd` and `refocus_report`, pinned.

`refocus_cmd` reached this repository's 800-line ceiling with a slice still
to land in it, so the printing half -- the stamp, the `threads:` line, the
attribution sentence and `report()` itself -- moved to `refocus_report`.
That is a move, not an interface: `refocus_cmd.report` and the rest still
resolve, to the SAME function objects, because every caller and every test
that reaches for them is reaching for one command's internals and there is
still only one of each. `is` and not `==` for exactly that reason -- a
wrapper or a re-definition would satisfy equality and would be a second
implementation to keep in step.

The line counts are here beside them because the split's whole purpose was
the ceiling: a check that says the seam holds while one side has crept back
over 800 lines has certified the wrong thing.
"""
import ast
from pathlib import Path

from sensorium.query import refocus_cmd, refocus_report

#: Relative to this file, never to a checkout path: the test has to be true
#: of the repository, not of one machine's copy of it.
SRC = Path(__file__).resolve().parents[1] / "src" / "sensorium" / "query"

#: The whole move set. `assess` and `final_verdict` are deliberately absent:
#: they decide, and the split's seam is between deciding and printing.
MOVED = ("_stamp", "_print_thread_line", "_diverged_why", "report")


def test_every_moved_name_is_one_object_reachable_through_both_modules():
    for name in MOVED:
        through_cmd = getattr(refocus_cmd, name)
        through_report = getattr(refocus_report, name)
        assert through_cmd is through_report, name


def test_the_names_that_decide_did_not_move():
    """`assess` and `final_verdict` stay where the verdict is decided --
    the seam is deciding versus printing, and a report module that also
    decided would put the verdict back in two places."""
    for name in ("assess", "final_verdict"):
        assert hasattr(refocus_cmd, name), name
        assert not hasattr(refocus_report, name), name


def test_the_new_module_says_what_it_holds_and_why():
    doc = refocus_report.__doc__
    assert doc is not None and doc.strip(), refocus_report.__file__


def test_both_halves_are_under_the_ceiling_the_split_was_for():
    for name in ("refocus_cmd.py", "refocus_report.py"):
        path = SRC / name
        n = len(path.read_text().splitlines())
        assert n <= 800, f"{name} is {n} lines"


def test_the_report_half_does_not_import_the_command_back():
    """The re-export runs one way. An import back would be a cycle, and the
    names those bodies need have real homes of their own to come from.

    The IMPORTS and not the text: the docstring names `refocus_cmd` on
    purpose, to say where this file came from, and a check that banned the
    word would be pinning the prose rather than the dependency.
    """
    tree = ast.parse((SRC / "refocus_report.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "refocus_cmd" not in (node.module or ""), node.lineno
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert "refocus_cmd" not in alias.name, node.lineno
