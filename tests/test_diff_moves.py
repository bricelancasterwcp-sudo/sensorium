"""`diff --ignore-moves`: a function moved to another file is paired by
name; a planted behavioural change under the same move is still DIVERGED
(spec E5 -- if the planted change read MATCH the verifier would be void)."""
import re
import subprocess
import sys

from sensorium import cli

MAIN = """
from lib import helper, other

def main():
    helper(1)
    other(2)

if __name__ == "__main__":
    main()
"""
MAIN_SWAPPED = MAIN.replace("    helper(1)\n    other(2)", "    other(2)\n    helper(1)")
LIB_TOGETHER = "def helper(x):\n    return x + 1\n\ndef other(y):\n    return y * 2\n"
LIB_SPLIT = "from lib_helper import helper\n\ndef other(y):\n    return y * 2\n"
LIB_HELPER = "def helper(x):\n    return x + 1\n"


def _record(workdir, sdir, files):
    """Write `files` into ONE directory and record `main.py` there. Every
    version is recorded in the same directory on purpose: `file` is
    absolute, and a different directory would make every module's
    `<module>` and every function a "move" at once. Stale bytecode is
    ruled out explicitly (same directory, rewritten sources)."""
    import os
    for stale in workdir.glob("*.py"):
        stale.unlink()
    for fname, text in files:
        (workdir / fname).write_text(text)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, "-m", "sensorium", "run", "--", "main.py"],
                       cwd=workdir, env={**env, "SENSORIUM_DIR": str(sdir)},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return re.search(r"^run: (\S+)$", r.stdout, re.M).group(1)


def _three(tmp_path, monkeypatch):
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_TOGETHER)])
    moved = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_SPLIT),
                              ("lib_helper.py", LIB_HELPER)])
    swapped = _record(w, sdir, [("main.py", MAIN_SWAPPED), ("lib.py", LIB_SPLIT),
                                ("lib_helper.py", LIB_HELPER)])
    return before, moved, swapped


def _collect(capsys, args):
    rc = cli.main(args)
    return rc, capsys.readouterr().out


def _side(out, label):
    """The step `diff` named for one side of a divergence."""
    return re.search(rf"^  {label}:      (.*)$", out, re.M).group(1)


def test_plain_diff_calls_a_pure_move_diverged(tmp_path, monkeypatch, capsys):
    before, moved, _ = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", before, moved])
    assert rc == 1 and "verdict: DIVERGED" in out


def test_ignore_moves_pairs_the_move_and_says_so(tmp_path, monkeypatch, capsys):
    before, moved, _ = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, moved])
    assert rc == 0, out
    assert "verdict: MATCH modulo location" in out
    assert re.search(r"moved: helper\s+lib\.py -> lib_helper\.py", out)
    assert "key: (file, qualname, kind), with 1 code object(s) paired" in out
    assert "module frames not compared: 1 (files only in B: lib_helper.py" in out
    assert "values, timing, and LINE events were not compared" in out


def test_ignore_moves_still_catches_a_planted_swap(tmp_path, monkeypatch, capsys):
    """E5: the same move plus two call sites swapped must read DIVERGED and
    name the step; a MATCH here would mean the comparison compares nothing."""
    before, _, swapped = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, swapped])
    assert rc == 1, out
    assert "verdict: DIVERGED at causal step" in out
    # Named AT the swap: A still calls helper first, B now calls other.
    assert "helper" in _side(out, "A") and "other" in _side(out, "B")
    assert "moved: helper" in out          # the pairing is still reported
    # And named in the file A RECORDED it in. The comparison ran on the
    # projected key (B's file); printing that key told the reader to drill
    # into a file A never had -- at the one line the drill-in command names.
    a = _side(out, "A")
    assert re.search(r"\(/.*/lib\.py\) \(paired with lib_helper\.py\)$", a), a


MAIN_TAIL = """
from lib import helper, other

def main():
    helper(1)
    other(2)
    helper(3)

if __name__ == "__main__":
    main()
"""
MAIN_TAIL_SWAPPED = MAIN_TAIL.replace("    other(2)\n    helper(3)",
                                      "    helper(3)\n    other(2)")


def test_a_common_line_for_a_moved_function_names_the_recorded_file(
        tmp_path, monkeypatch, capsys):
    """The run-up above a divergence is A's stream, projected. A moved
    function in it was printed under B's file too -- the same false citation
    as the `A:` line, in the lines that give it its context."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN_TAIL), ("lib.py", LIB_TOGETHER)])
    after = _record(w, sdir, [("main.py", MAIN_TAIL_SWAPPED),
                              ("lib.py", LIB_SPLIT), ("lib_helper.py", LIB_HELPER)])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, after])
    assert rc == 1, out
    common = [l for l in out.splitlines() if l.startswith("  common  ")]
    moved = [l for l in common if " helper " in l]
    assert moved, out
    for line in moved:
        assert re.search(r"\(/.*/lib\.py\) \(paired with lib_helper\.py\)$",
                         line), line


def test_ignore_moves_of_a_trace_against_itself_is_a_plain_match(
        tmp_path, monkeypatch, capsys):
    """Nothing moved and no file is one-sided, so the projected streams ARE
    the recorded ones: "MATCH modulo location ... once 0 moved code
    object(s) are paired" hedged an exact agreement, over a bare `moves:`
    header that read as a list cut off."""
    before, _moved, _swapped = _three(tmp_path, monkeypatch)
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, before])
    assert rc == 0, out
    assert "verdict: MATCH -- identical causal streams" in out
    assert "MATCH modulo location" not in out
    assert "moves: none -- no code object was on one side only" in out


def test_ignore_moves_lists_added_and_removed_code(tmp_path, monkeypatch, capsys):
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_TOGETHER)])
    renamed = _record(w, sdir, [("main.py", MAIN.replace("other", "third")),
                                ("lib.py", LIB_TOGETHER.replace("other", "third"))])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, renamed])
    assert rc == 1
    assert "removed (only in A): lib.py:other" in out
    assert "added (only in B): lib.py:third" in out


def test_import_time_side_effects_in_a_new_module_still_diverge(tmp_path, monkeypatch, capsys):
    """Only the new module's own <module> steps are dropped; a call it makes
    at import time is a step A never took."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_TOGETHER)])
    noisy = _record(w, sdir, [("main.py", MAIN), ("lib.py", LIB_SPLIT),
                              ("lib_helper.py", LIB_HELPER + "\nhelper(0)\n")])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, noisy])
    assert rc == 1 and "verdict: DIVERGED at causal step" in out


# -- the same pairing, on task streams -------------------------------------

ASYNC_MAIN = """
import asyncio
from lib import step, other

FLIP = {flip}

async def worker(name):
    step(1)
    await asyncio.sleep(0)
    if FLIP and name == "B":
        other(2)
    else:
        step(2)

async def amain():
    await asyncio.gather(*[asyncio.create_task(worker(n), name=f"task-{{n}}")
                           for n in ("A", "B")])

def main():
    asyncio.run(amain())

main()
"""
ASYNC_LIB_TOGETHER = "def step(n):\n    return n\n\ndef other(n):\n    return -n\n"
ASYNC_LIB_SPLIT = "from lib_step import step\n\ndef other(n):\n    return -n\n"
ASYNC_LIB_STEP = "def step(n):\n    return n\n"


def test_ignore_moves_finds_the_task_that_diverged_after_a_move(
        tmp_path, monkeypatch, capsys):
    """The task drill-in turns a HASH back into a task id, and under the
    flag the shapes are re-hashed at query time -- looking that hash up in
    the stored rows finds nothing at all (it raised StopIteration before
    `task_hashes` existed), so a real task divergence went unreported."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="False")),
                               ("lib.py", ASYNC_LIB_TOGETHER)])
    after = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="True")),
                              ("lib.py", ASYNC_LIB_SPLIT),
                              ("lib_step.py", ASYNC_LIB_STEP)])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, after])
    assert rc == 1, out
    assert "tasks: DIVERGED" in out
    assert "first difference inside task-B" in out
    assert "moved: step  lib.py -> lib_step.py" in out


def test_ignore_moves_matches_two_task_streams_across_a_move(
        tmp_path, monkeypatch, capsys):
    """The move alone must not make the tasks look different either: both
    sides are re-hashed the one way, so the paired streams still match."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="False")),
                               ("lib.py", ASYNC_LIB_TOGETHER)])
    after = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="False")),
                              ("lib.py", ASYNC_LIB_SPLIT),
                              ("lib_step.py", ASYNC_LIB_STEP)])
    rc, out = _collect(capsys, ["diff", "--ignore-moves", before, after])
    assert rc == 0, out
    assert "verdict: MATCH modulo location" in out
    assert "all matched" in out


def test_ignore_moves_on_one_task_matches_across_a_move(
        tmp_path, monkeypatch, capsys):
    """`--task` compares the PROJECTED streams too, so its MATCH must say
    "modulo location" and carry the key line -- claiming "the same sequence
    of (file, qualname, kind)" would describe a comparison that never ran."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="False")),
                               ("lib.py", ASYNC_LIB_TOGETHER)])
    after = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="False")),
                              ("lib.py", ASYNC_LIB_SPLIT),
                              ("lib_step.py", ASYNC_LIB_STEP)])
    rc, out = _collect(capsys, ["diff", "--task", "task-A", "--ignore-moves",
                                before, after])
    assert rc == 0, out
    assert "key: (file, qualname, kind), with 1 code object(s) paired" in out
    assert "verdict: MATCH modulo location" in out and "task task-A" in out
    assert "the same sequence of (file, qualname, kind)" not in out
    assert "moved: step  lib.py -> lib_step.py" in out


def test_ignore_moves_on_one_task_still_catches_a_changed_body(
        tmp_path, monkeypatch, capsys):
    """The same move with the task's own body changed: DIVERGED, at the
    changed call and not at the move."""
    w, sdir = tmp_path / "w", tmp_path / "sdir"
    w.mkdir()
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    before = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="False")),
                               ("lib.py", ASYNC_LIB_TOGETHER)])
    after = _record(w, sdir, [("main.py", ASYNC_MAIN.format(flip="True")),
                              ("lib.py", ASYNC_LIB_SPLIT),
                              ("lib_step.py", ASYNC_LIB_STEP)])
    rc, out = _collect(capsys, ["diff", "--task", "task-B", "--ignore-moves",
                                before, after])
    assert rc == 1, out
    assert "verdict: DIVERGED at causal step" in out
    assert "step" in _side(out, "A") and "other" in _side(out, "B")
    assert "moved: step  lib.py -> lib_step.py" in out
