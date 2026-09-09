"""The seam between `tracer`, `tracer_frames` and `tracer_exc`, pinned.

`tracer.py` reached this repository's 800-line ceiling at 1193 lines, so it
was cut by responsibility: `tracer_frames` took which frames the recorder
decides to watch and the identities it mints for them, `tracer_exc` took how
many exception objects a thread remembers and the tables that remember them,
and `tracer` kept the audit surface -- what fires and what gets written.

That is a move, not an interface. `tracer.FocusSpec`, `tracer._RETAIN_MAX`
and the rest still resolve, to the SAME objects, because every caller reaching
for them is reaching for one recorder's internals and there is still only one
of each. `is` and not `==` for exactly that reason -- a wrapper or a
re-definition would satisfy equality and would be a second implementation to
keep in step.

Modelled on `tests/test_refocus_report_split.py`, which pins the same property
for `refocus_cmd`'s split; the line counts are here beside the names because
the split's whole purpose was the ceiling.
"""
import ast
from pathlib import Path

from sensorium.record import tracer, tracer_exc, tracer_frames

#: Relative to this file, never to a checkout path: the test has to be true
#: of the repository, not of one machine's copy of it.
SRC = Path(__file__).resolve().parents[1] / "src" / "sensorium" / "record"

#: Every name `tracer` re-exports, and the module that now defines it.
#: `FocusSpec`, `module_name_for`, `_RETAIN_MAX` and `_CONTROL_RETAIN_MAX` are
#: named by the design as the ones the tree already imports through `tracer`
#: (`boot.py`, `watch_cmd.py`, `tests/programs.py`, `tests/helpers.py`); the
#: other five are used by `tracer`'s own remaining half and are re-exported by
#: the same import.
MOVED = {
    "FocusSpec": tracer_frames,
    "WindowSpec": tracer_frames,
    "module_name_for": tracer_frames,
    "_FrameDecisions": tracer_frames,
    "_RETAIN_MAX": tracer_exc,
    "_CONTROL_RETAIN_MAX": tracer_exc,
    "_ExcRefs": tracer_exc,
    "_TLS": tracer_exc,
    "_is_control_flow": tracer_exc,
}


def test_every_moved_name_is_one_object_reachable_through_both_modules():
    for name, home in MOVED.items():
        through_tracer = getattr(tracer, name)
        through_home = getattr(home, name)
        assert through_tracer is through_home, name


def test_the_audit_surface_did_not_move():
    """`Tracer`, `locals_snapshot` and the two `sys.monitoring` handles stay
    where events are written. A frames module that also wrote events, or an
    exception module that owned the tool id, would put the audit surface in
    two places -- which is the thing the seam exists to keep in one."""
    for name in ("Tracer", "locals_snapshot", "M", "TOOL"):
        assert hasattr(tracer, name), name
        assert not hasattr(tracer_frames, name), name
        assert not hasattr(tracer_exc, name), name


def test_the_recorders_own_directory_is_NOT_re_exported():
    """`_SENSORIUM_DIR` is deliberately absent from `tracer`.

    Its only reader is `_classify`, which lives in `tracer_frames`, and
    `tests/test_tracer_serials.py` monkeypatches it to prove the recorder
    excludes its own code. Re-exporting the name would rebind only `tracer`'s
    copy: the guard would keep reading the real directory and that test would
    fail on a FULL EVENT LIST rather than loudly. Measured both ways at the
    split. So the absence is the fence, and this is it.
    """
    assert hasattr(tracer_frames, "_SENSORIUM_DIR")
    assert not hasattr(tracer, "_SENSORIUM_DIR")
    assert not hasattr(tracer_exc, "_SENSORIUM_DIR")


def test_each_new_module_says_what_it_holds_and_why():
    for mod in (tracer_frames, tracer_exc):
        assert mod.__doc__ is not None and mod.__doc__.strip(), mod.__file__


def test_all_three_files_are_under_the_ceiling_the_split_was_for():
    for name in ("tracer.py", "tracer_frames.py", "tracer_exc.py"):
        path = SRC / name
        n = len(path.read_text().splitlines())
        assert n <= 800, f"{name} is {n} lines"


def test_neither_half_imports_the_recorder_back():
    """The re-export runs one way. An import back would be a cycle, and the
    names those bodies need have real homes of their own to come from.

    The IMPORTS and not the text: both docstrings name `tracer.py` on purpose,
    to say where the file came from, and a check that banned the word would be
    pinning the prose rather than the dependency.
    """
    for name in ("tracer_frames.py", "tracer_exc.py"):
        tree = ast.parse((SRC / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.endswith("tracer"), f"{name}:{node.lineno}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.endswith("tracer"), \
                        f"{name}:{node.lineno}"
