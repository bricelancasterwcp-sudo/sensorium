"""The seam between `refocus_world` and `refocus_threads`, pinned.

`refocus_world` reached this repository's 800-line ceiling with a fix still
to land in it, so the thread bookkeeping -- who started each thread, how
many the comparison saw, and the clauses that name the recorder's own --
moved to `refocus_threads`, the seam CARRIED-DEBT had already named.

That is a move, not an interface: `refocus_world.harness_threads` and the
rest still resolve, to the SAME function objects, because every caller and
every test that reaches for them is reaching for one command's internals and
there is still only one of each. `is` and not `==` for exactly that reason
-- a wrapper or a re-definition would satisfy equality and would be a second
implementation to keep in step.

Modelled on `tests/test_refocus_report_split.py`, which pins the same
property for `refocus_cmd`'s split; the line counts are here beside the
names because the split's whole purpose was the ceiling.
"""
import ast
from pathlib import Path

from sensorium.query import (refocus_cmd, refocus_report, refocus_threads,
                             refocus_world)

#: Relative to this file, never to a checkout path: the test has to be true
#: of the repository, not of one machine's copy of it.
SRC = Path(__file__).resolve().parents[1] / "src" / "sensorium" / "query"

#: The whole move set. The first four are CARRIED-DEBT's named seam;
#: `compared_threads` travels with them because it is `uncompared_threads`'
#: only helper and leaving it behind would make the new module import
#: `refocus_world` back.
MOVED = ("harness_threads", "harness_exclusion", "harness_note",
         "uncompared_threads", "compared_threads")

#: The two that `refocus_cmd` re-exports ONWARD, from `refocus_world`. A
#: chain of re-exports is still one object or it is not a move.
THROUGH_CMD = ("harness_note", "uncompared_threads")


def test_every_moved_name_is_one_object_reachable_through_both_modules():
    for name in MOVED:
        through_world = getattr(refocus_world, name)
        through_threads = getattr(refocus_threads, name)
        assert through_world is through_threads, name


def test_the_onward_re_exports_are_the_same_object_too():
    """`refocus_cmd` and `refocus_report` reach these through
    `refocus_world`, which now reaches them through `refocus_threads`. Two
    hops is still one object, and a test that only checked the first hop
    would pass over a second implementation reached by the second."""
    for name in THROUGH_CMD:
        assert getattr(refocus_cmd, name) is getattr(refocus_threads, name), \
            name
    for name in ("harness_note", "uncompared_threads"):
        assert getattr(refocus_report, name) is \
            getattr(refocus_threads, name), name


def test_the_names_that_weigh_the_facts_did_not_move():
    """`_licence_caveats` and `_verified_facts` stay where the evidence is
    weighed -- the seam is counting threads versus deciding what a count
    lets the licence claim, and a thread module that also weighed would put
    that judgement in two places."""
    for name in ("_licence_caveats", "_verified_facts", "_env_state",
                 "_source_state"):
        assert hasattr(refocus_world, name), name
        assert not hasattr(refocus_threads, name), name


def test_the_new_module_says_what_it_holds_and_why():
    doc = refocus_threads.__doc__
    assert doc is not None and doc.strip(), refocus_threads.__file__


def test_both_halves_are_under_the_ceiling_the_split_was_for():
    for name in ("refocus_world.py", "refocus_threads.py"):
        path = SRC / name
        n = len(path.read_text().splitlines())
        assert n <= 800, f"{name} is {n} lines"


def test_the_thread_half_does_not_import_the_world_back():
    """The re-export runs one way. An import back would be a cycle, and the
    names those bodies need have real homes of their own to come from.

    The IMPORTS and not the text: the docstring names `refocus_world` on
    purpose, to say where this file came from, and a check that banned the
    word would be pinning the prose rather than the dependency.
    """
    tree = ast.parse((SRC / "refocus_threads.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            assert "refocus_world" not in mod, node.lineno
            assert "refocus_cmd" not in mod, node.lineno
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert "refocus_world" not in alias.name, node.lineno
