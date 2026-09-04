"""`tree` and `frame`: what actually ran, and one activation in full."""
import shutil
import sys

import pytest

from sensorium.exit import BAD_CALL, NEGATIVE
from sensorium import cli, paths
from sensorium.query import tree_cmd
from sensorium.store.writer import TraceWriter
from tests.helpers import record_inproc, record_script

SRC = """
def gold(total):
    return total * 0.80

def silver(total):
    return total * 0.95

def price(points, total):
    if points > 1000:
        return gold(total)
    return silver(total)

def main():
    for pts in (500, 1000, 1500):
        price(pts, 100.0)

if __name__ == "__main__":
    main()
"""

# Two functions, one qualname a substring of the other -- built for the
# `--fn` exact-first-then-substring rule (X9). See tests.programs.HELPERS,
# which this mirrors: kept local to this file rather than imported, since
# `_rec` takes a raw source string, not a run builder.
HELPERS_SRC = """
def helper(x):
    return x + 1

def helper_two(x):
    return x + 2

def main():
    helper(1)
    helper_two(2)

main()
"""

LOOP = """
def accumulate(ops):
    total = 0
    for op in ops:
        total = total + op
    return total

def main():
    accumulate([5, 10])

if __name__ == "__main__":
    main()
"""

# `del a` on line 5 unbinds a name with nothing else changing on the next
# line -- the shape that vanishes entirely if a renderer only looks at
# "deltas" and ignores the sibling "unbound" key.
UNBIND_SRC = """
def watched(n):
    a = n
    b = a + 1
    del a
    c = b + 1
    return c

def main():
    watched(1)

if __name__ == "__main__":
    main()
"""

# An uncaught exception: every frame it crosses is closed_by "unwind" with a
# captured unwind_exc, exercising tree/frame's exception-tail rendering
# against a real recorded trace rather than a hand-built fixture.
CRASH = """
def boom(n):
    return 1 / n

def main():
    boom(0)

if __name__ == "__main__":
    main()
"""


def _rec(tmp_path, monkeypatch, src=SRC, extra=()):
    run_id, trace, r = record_script(tmp_path, src, extra=extra)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def test_tree_shows_hierarchy_args_returns(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("silver(") == 2 and out.count("gold(") == 1
    assert "-> 95.0" in out
    # children indented under price
    price_line = next(ln for ln in out.splitlines() if "price(points=1000" in ln)
    child_line = out.splitlines()[out.splitlines().index(price_line) + 1]
    assert child_line.startswith(price_line[:len(price_line)
                                            - len(price_line.lstrip())] + "  ")


def test_tree_around_event(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    cli.main(["tree", run_id])
    first = capsys.readouterr().out
    silver_line = next(ln for ln in first.splitlines() if "silver(" in ln)
    eid = silver_line.split()[1]            # "e<id>" token of frame_line;
    # this is the CALL event id -- CALL events carry frame_id = NULL, so this
    # also exercises frame_containing's call_event_id fallback path.
    assert cli.main(["tree", run_id, "--around", eid]) == 0
    out = capsys.readouterr().out
    assert "silver(" in out and "main(" in out    # ancestors shown


def test_tree_around_missing_event_reports_and_exits_1(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id, "--around", "e999999"]) == 1
    assert "no frame contains e999999" in capsys.readouterr().out


def test_tree_rejects_a_nonpositive_limit(tmp_path, monkeypatch, capsys):
    """Consistency with grep/exceptions/flow/watch, which all refuse a
    zero-or-negative --limit rather than print a degenerate page."""
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id, "--limit", "0"]) == 2
    assert "--limit must be >= 1" in capsys.readouterr().out


def test_tree_rejects_a_negative_depth(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id, "--depth", "-1"]) == 2
    assert "--depth must be >= 0" in capsys.readouterr().out


def test_tree_root_missing_frame_reports_and_exits_1(
        tmp_path, monkeypatch, capsys):
    """A valid-syntax `--root` that names no frame must refuse, not print
    "no frames recorded" (which is false -- the trace has frames) at exit 0.
    Matches `--around` and `frame f<id>`, and keeps "no frames recorded" for a
    genuinely empty trace."""
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id, "--root", "f999999"]) == 1
    out = capsys.readouterr().out
    assert "no such frame" in out and "f999999" in out
    assert "no frames recorded" not in out


def test_tree_root_scopes_to_subtree_and_drops_ancestors(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    cli.main(["tree", run_id])
    first = capsys.readouterr().out
    price_line = next(ln for ln in first.splitlines()
                      if "price(points=500" in ln)
    fid = price_line.split()[0]              # "f<id>" token
    assert cli.main(["tree", run_id, "--root", fid]) == 0
    out = capsys.readouterr().out
    assert "price(points=500" in out
    assert "silver(" in out                   # its child is still shown
    assert "main(" not in out                 # but the ancestor is not


def test_tree_depth_limit_prunes_and_reports_how_much(
        tmp_path, monkeypatch, capsys):
    # The script's own module body is the true root (depth 0); main() is
    # depth 1, price() depth 2. --depth 1 keeps main but prunes price.
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["tree", run_id, "--depth", "1"]) == 0
    out = capsys.readouterr().out
    assert "main(" in out
    assert "price(" not in out                # depth 2, pruned
    assert "--depth 1" in out
    # exact, runnable command: the real run id and a real pruned frame id,
    # not a template like "fN"
    assert f"continue with: sensorium tree {run_id} --root f" in out
    hint_frame = out.strip().splitlines()[-1].rsplit("--root f", 1)[1]
    assert hint_frame.isdigit()


# -- fix round 1: `tree --around` computed `cut` from render_tree and never
# checked or printed it -- only the default (no --around) branch did. A
# reader asking "what's around this event" would see a complete-looking
# tree and have no way to know a subtree was withheld. Reproduced on SRC's
# price -> silver call: --around on price's own CALL event with --depth 0
# prunes silver's subtree entirely and (pre-fix) said nothing about it.
def test_tree_around_reports_truncation_with_runnable_command(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)     # SRC: price() calls silver()
    cli.main(["tree", run_id])
    first = capsys.readouterr().out
    price_line = next(ln for ln in first.splitlines()
                      if "price(points=500" in ln)
    eid = price_line.split()[1]              # price's own CALL event id

    assert cli.main(["tree", run_id, "--around", eid, "--depth", "0"]) == 0
    out = capsys.readouterr().out
    assert "price(points=500" in out
    assert "silver(" not in out               # silver's subtree is pruned
    assert "1 subtree(s) beyond --depth 0" in out
    # exact, runnable command -- a real run ref and a real frame id, not a
    # literal "fN" template
    assert f"continue with: sensorium tree {run_id} --root f" in out
    hint_frame = out.strip().splitlines()[-1].rsplit("--root f", 1)[1]
    assert hint_frame.isdigit()

    # and following that exact command actually reveals what was withheld
    assert cli.main(["tree", run_id, "--root", f"f{hint_frame}"]) == 0
    assert "silver(" in capsys.readouterr().out


def test_tree_zero_frames_says_so_instead_of_printing_nothing(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdef"
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    w.set_meta("run_id", run_id)
    w.close()
    assert cli.main(["tree", run_id]) == NEGATIVE
    out = capsys.readouterr().out
    assert out.strip() == "no frames recorded"


def test_tree_and_frame_mark_unwound_frame_with_real_exception(
        tmp_path, monkeypatch, capsys):
    run_id, _trace, r = record_script(tmp_path, CRASH)
    assert run_id, r.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    boom_line = next(ln for ln in out.splitlines() if "boom(" in ln)
    assert boom_line.endswith("!! ZeroDivisionError('division by zero')")
    fid = boom_line.split()[0]

    assert cli.main(["frame", run_id, fid]) == 0
    out2 = capsys.readouterr().out
    assert "closed: unwind" in out2
    assert "unwound: ZeroDivisionError('division by zero')" in out2


def test_frame_line_covers_open_and_unwind_without_exc_branches(
        tmp_path, monkeypatch, capsys):
    """A synthetic trace: `tree`/`frame` must never blow up or lie about a
    frame that never closed (process died mid-call) or one that unwound
    without a captured exception (defensive fallback)."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdef"
    w = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    w.set_meta("run_id", run_id)
    w.set_meta("argv", ["prog.py"])
    w.set_meta("cwd", str(tmp_path))
    w.set_meta("incomplete", True)

    cid_a = w.intern_code("/tmp/prog.py", "stuck", 1)
    cid_b = w.intern_code("/tmp/prog.py", "wedged", 5)

    eid_a = w.add_event(0, 1, "CALL", None, cid_a, 1, {"args": {}})
    fid_a = w.open_frame(None, cid_a, eid_a, 0, 1)
    w.close_frame(fid_a, return_event_id=None, closed_by="unwind",
                 unwind_exc=None)

    eid_b = w.add_event(0, 1, "CALL", None, cid_b, 5, {"args": {}})
    fid_b = w.open_frame(None, cid_b, eid_b, 0, 1)
    w.close()

    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    stuck_line = next(ln for ln in out.splitlines() if "stuck(" in ln)
    assert stuck_line.endswith("!! unwound")
    wedged_line = next(ln for ln in out.splitlines() if "wedged(" in ln)
    assert wedged_line.endswith("(open)")

    assert cli.main(["frame", run_id, f"f{fid_a}"]) == 0
    out_a = capsys.readouterr().out
    assert "closed: unwind" in out_a
    assert "unwound: ?" in out_a
    assert "children: (none)" in out_a

    assert cli.main(["frame", run_id, f"f{fid_b}"]) == 0
    out_b = capsys.readouterr().out
    assert "closed: open" in out_b
    assert "return:" not in out_b
    assert "unwound:" not in out_b


def test_frame_by_fn_with_timeline(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=LOOP,
                  extra=("--focus", "prog:accumulate"))
    assert cli.main(["frame", run_id, "--fn", "accumulate"]) == 0
    out = capsys.readouterr().out
    assert "args: ops=list[2]=[5, 10]" in out
    assert "timeline:" in out and "total=15" in out
    assert "return: 15" in out
    assert "children: (none)" in out


def test_frame_without_focus_says_refocus(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=LOOP)
    cli.main(["frame", run_id, "--fn", "accumulate"])
    out = capsys.readouterr().out
    assert "not captured" in out and "refocus" in out
    assert "refocus with --focus prog:accumulate" in out


def test_frame_timeline_renders_unbound_names(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=UNBIND_SRC,
                  extra=("--focus", "prog:watched"))
    assert cli.main(["frame", run_id, "--fn", "watched"]) == 0
    out = capsys.readouterr().out
    assert "unbound:a" in out


def test_frame_positional_ref_and_nth_distinguish_activations(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)     # SRC: silver() runs twice
    assert cli.main(["frame", run_id, "--fn", "silver", "--nth", "1"]) == 0
    fid1 = capsys.readouterr().out.splitlines()[0].split()[0]
    assert cli.main(["frame", run_id, "--fn", "silver", "--nth", "2"]) == 0
    out2 = capsys.readouterr().out
    fid2 = out2.splitlines()[0].split()[0]
    assert fid1 != fid2

    assert cli.main(["frame", run_id, fid2]) == 0
    assert capsys.readouterr().out == out2


# -- fix round 1: `--nth 0` silently returned matches[-1] (the wrong
# activation, no error at all); `--nth -5` against a single match raised an
# uncaught IndexError. Both must instead refuse loudly and name how many
# activations actually exist, never guess and never crash.
def test_frame_nth_zero_is_rejected_not_silently_wrapped(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)     # SRC: silver() runs twice
    assert cli.main(["frame", run_id, "--fn", "silver", "--nth", "0"]) == BAD_CALL
    out = capsys.readouterr().out
    assert "--nth 0" in out and "2 framed activation(s)" in out
    assert "1..2" in out


def test_frame_nth_negative_does_not_crash(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=LOOP)   # accumulate() runs once
    assert cli.main(["frame", run_id, "--fn", "accumulate", "--nth", "-5"]) == BAD_CALL
    out = capsys.readouterr().out
    assert "--nth -5" in out and "1 framed activation(s)" in out


def test_frame_nth_too_high_names_activation_count(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)     # SRC: silver() runs twice
    assert cli.main(["frame", run_id, "--fn", "silver", "--nth", "9"]) == BAD_CALL
    out = capsys.readouterr().out
    assert "--nth 9" in out and "2 framed activation(s)" in out


def test_frame_children_section_lists_child_frames(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)     # SRC: price() calls silver/gold
    assert cli.main(["frame", run_id, "--fn", "price", "--nth", "1"]) == 0
    out = capsys.readouterr().out
    assert "children (1):" in out
    assert "silver(" in out


def test_frame_children_name_a_generator_child_by_its_kind(
        tmp_path, monkeypatch, capsys):
    """GEN_SRC's `main` calls exactly one thing -- `rows`, a generator, which
    now opens a frame of its own and is a child like any other. The line
    still has to say WHICH kind of child: without the marker `rows` reads as
    a plain function that returned None, and the reason its return value is
    None (a generator exhausted, not a function that computed nothing) is
    lost."""
    run_id = _rec(tmp_path, monkeypatch, src=GEN_SRC)
    assert cli.main(["frame", run_id, "--fn", "main"]) == 0
    out = capsys.readouterr().out
    assert "children: (none)" not in out
    assert "children (1):" in out
    child = next(ln for ln in out.splitlines() if "rows(" in ln)
    assert "[generator]" in child and "unframed" not in child


def test_frame_children_list_every_kind_in_call_order(
        tmp_path, monkeypatch, capsys):
    """`mixed` calls a plain function, then a generator, then a plain one
    again. All three open frames now, and the list is ordered by when the
    calls happened -- grouping by kind, or by frame id, would report an
    execution order the trace does not hold."""
    src = """
def one():
    return 1

def gen():
    yield 2

def three():
    return 3

def mixed():
    one()
    list(gen())
    three()

def main():
    mixed()

if __name__ == "__main__":
    main()
"""
    run_id = _rec(tmp_path, monkeypatch, src=src)
    assert cli.main(["frame", run_id, "--fn", "mixed"]) == 0
    out = capsys.readouterr().out
    assert "children (3):" in out
    rows = out.split("children (3):\n")[1].splitlines()
    assert len(rows) == 3, rows
    assert "one(" in rows[0]
    assert "gen(" in rows[1] and "[generator]" in rows[1]
    assert "three(" in rows[2]


def test_frame_unknown_ref_is_exit_1(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["frame", run_id, "--fn", "does_not_exist"]) == 1
    assert "no such frame" in capsys.readouterr().out


def test_frame_fn_exact_beats_substring(tmp_path, monkeypatch, capsys):
    """X9: `helper` is a substring of `helper_two` too, but an exact
    qualname match must win outright -- resolving to `helper`, not an
    ambiguous reference between the two."""
    run_id = _rec(tmp_path, monkeypatch, src=HELPERS_SRC)
    assert cli.main(["frame", run_id, "--fn", "helper"]) == 0
    out = capsys.readouterr().out
    assert "helper" in out and "ambiguous" not in out
    assert ":helper_two" not in out and "[helper_two]" not in out


def test_frame_fn_substring_ambiguous_lists_candidates_and_exits_2(
        tmp_path, monkeypatch, capsys):
    """No code object is named exactly `help`, and it is a substring of
    BOTH `helper` and `helper_two`: the reference is ambiguous, which is the
    call being wrong (BAD_CALL), not a coin flip that silently picks one."""
    run_id = _rec(tmp_path, monkeypatch, src=HELPERS_SRC)
    assert cli.main(["frame", run_id, "--fn", "help"]) == BAD_CALL
    out = capsys.readouterr().out
    assert ("--fn 'help' is ambiguous: matches helper, helper_two; give "
            "the exact qualname") in out


def test_frame_well_formed_ref_to_a_frame_that_never_existed_is_refused(
        tmp_path, monkeypatch, capsys):
    """`f9999` parses fine and names nothing. The refusal has to come from
    the lookup, not from the parser, or a valid-looking reference falls
    through to a traceback."""
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["frame", run_id, "f9999"]) == 1
    out = capsys.readouterr().out
    assert "no such frame" in out and "f9999" in out


def test_frame_with_no_selector_at_all_says_what_to_give_it(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["frame", run_id]) == BAD_CALL
    out = capsys.readouterr().out
    assert "f<id>" in out and "--fn" in out


ASYNC_SRC = """
import asyncio

def step(task, n):
    return f"{task}:{n}"

async def worker(name):
    step(name, 1)
    await asyncio.sleep(0)
    return step(name, 2)

async def amain():
    a = asyncio.create_task(worker("A"), name="task-A")
    b = asyncio.create_task(worker("B"), name="task-B")
    return await asyncio.gather(a, b)

if __name__ == "__main__":
    asyncio.run(amain())
"""

GEN_SRC = """
def parse(s):
    return int(s)

def rows(items):
    for it in items:
        yield parse(it)

def main():
    return list(rows(["1", "2"]))

if __name__ == "__main__":
    main()
"""


def _section(out: str, header: str) -> list[str]:
    """Lines under `header` up to the next unindented line."""
    lines = out.splitlines()
    i = lines.index(header)
    body = []
    for ln in lines[i + 1:]:
        if ln and not ln.startswith(" "):
            break
        body.append(ln)
    return body


def test_tree_groups_by_task_with_coroutine_frames(tmp_path, monkeypatch,
                                                   capsys):
    """Each `worker` coroutine has a frame of its own now: the calls it made
    nest UNDER it rather than sitting beside it with a `<- worker` tag, and
    the line says it is a coroutine and what it returned."""
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    a = _section(out, "task t2: task-A")
    b = "\n".join(_section(out, "task t3: task-B"))
    worker = next(ln for ln in a if "worker(" in ln)
    assert worker.endswith("worker(name='A')  [coroutine] -> 'A:2'")
    steps = [ln for ln in a if "step(" in ln]
    assert len(steps) == 2 and "task='B'" not in "\n".join(a)
    indent = len(worker) - len(worker.lstrip())
    assert all(ln.startswith(" " * (indent + 2) + "f") for ln in steps)
    assert "task='A'" not in b and "worker(name='B')  [coroutine]" in b
    assert "<- worker" not in out                # nothing to re-parent now
    assert "[coroutine, unframed]" not in out
    # `step` is an ordinary function, and an ordinary call carries NO marker:
    # the whole line, end to end, is what it was before coroutines had
    # frames. "[function]" on every sync call would be noise on every line
    # of every trace this tool has ever rendered.
    one = "step(task='A', n=1)"
    step_ln = next(ln for ln in out.splitlines() if one in ln)
    assert "[" not in step_ln and step_ln.endswith(one + " -> 'A:1'")
    # <module> ran before the loop existed: not placed in any task.
    assert "<module>()" in "\n".join(_section(out, "no asyncio task"))
    assert "order between tasks is wall-clock" in out


def test_tree_says_nothing_about_unframed_calls_on_a_format3_trace(
        tmp_path, monkeypatch, capsys):
    """The footer is a caveat about a LIMITATION -- code this version could
    not frame. A format-3 trace has none, so printing "0 unframed call(s)"
    (or the caveat at all) would warn about a hole that is not there."""
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    from sensorium import paths
    from sensorium.store.reader import Trace
    assert Trace.open(paths.find_trace(run_id)).unframed_calls() == []
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert "unframed call(s) in this trace" not in out
    assert "unframed" not in out


def test_tree_renders_a_generator_call_under_the_frame_that_called_it(
        tmp_path, monkeypatch, capsys):
    """`rows` is a generator: it opens a frame under `main`, and the two
    `parse` calls it made nest under IT rather than being tagged with its
    name and hoisted a level. `list()` exhausts it, so it "returns" None --
    the tail says so, and the marker says why that None is not a bug."""
    run_id = _rec(tmp_path, monkeypatch, src=GEN_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    main_ln = next(ln for ln in lines if "main()" in ln)
    gen_ln = next(ln for ln in lines if "rows(" in ln)
    assert gen_ln.endswith("[generator] -> None")
    indent = len(main_ln) - len(main_ln.lstrip())
    assert gen_ln.startswith(" " * (indent + 2) + "f")      # child of main
    parse_lns = [ln for ln in lines if "parse(" in ln]
    assert len(parse_lns) == 2
    gindent = len(gen_ln) - len(gen_ln.lstrip())
    assert all(ln.startswith(" " * (gindent + 2) + "f") for ln in parse_lns)
    assert "<-" not in out                                   # no tags at all
    assert "no asyncio task" not in out            # no tasks: no groups
    assert "unframed" not in out


def test_tree_around_a_yield_resolves_to_the_frame_that_parked(
        tmp_path, monkeypatch, capsys):
    """A YIELD is an event of a real frame now. `--around` on one lands in
    that frame instead of refusing with "no frame contains it" -- which was
    the truthful answer while coroutines had no frames, and is a false one
    the moment they do."""
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    from sensorium import paths
    from sensorium.store.reader import Trace
    t = Trace.open(paths.find_trace(run_id))
    worker = next(c for c in t.codes() if c.qualname == "worker")
    f = t.frames(code_id=worker.id)[0]
    y = next(e for e in t.suspensions(f.id) if e.kind == "YIELD")
    assert cli.main(["tree", run_id, "--around", f"e{y.id}"]) == 0
    out = capsys.readouterr().out
    assert f"f{f.id} " in out and "worker(name='A')  [coroutine]" in out
    assert "unframed CALL" not in out and "no frame contains" not in out


def test_tree_depth_withholds_a_generator_frame_and_names_it(
        tmp_path, monkeypatch, capsys):
    """`--depth` prunes a generator's frame exactly as it prunes any other,
    and the note can now NAME it: `--root fN` reaches a coroutine or
    generator subtree, which is precisely what the unframed-call count was
    a stand-in for while they had no frames."""
    run_id = _rec(tmp_path, monkeypatch, src=GEN_SRC)
    assert cli.main(["tree", run_id, "--depth", "1"]) == 0
    out = capsys.readouterr().out
    assert "main()" in out and "rows(" not in out
    assert "1 subtree(s) beyond --depth 1" in out
    rows_fid = next(ln for ln in out.splitlines()
                    if "--root f" in ln).split("--root f")[1].strip()
    assert "unframed" not in out
    # The hint is copy-pasteable and lands ON the generator frame.
    assert cli.main(["tree", run_id, "--root", f"f{rows_fid}"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].endswith("[generator] -> None")


def test_tree_limit_is_one_budget_across_every_task_group(
        tmp_path, monkeypatch, capsys):
    """`--limit` is ONE budget across the whole page, not a fresh one per
    root -- with a per-item budget every task group would print its own
    `--limit` rows and the page would be as long as the trace. Every row it
    withholds is a frame now, so the note names one to continue from."""
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    for limit in (1, 3):
        assert cli.main(["tree", run_id, "--limit", str(limit)]) == 0
        out = capsys.readouterr().out
        # Task headers, the note and the footers are unindented; every row
        # that spends budget is indented under a header.
        rows = [ln for ln in out.splitlines() if ln.startswith(" ")]
        assert len(rows) == limit, (limit, rows)
        assert f"--limit {limit}" in out
        assert "subtree(s) beyond" in out and "--root f" in out
        assert "unframed" not in out
        # The whole-trace view knows the total: it never hedges.
        assert "at least" not in out


def test_tree_subtree_view_reports_its_own_cut_and_hedges_what_it_counts(
        tmp_path, monkeypatch, capsys):
    """A `--root` slice reports the subtrees IT withheld, and names one to
    continue from. Its unframed count is the one number it cannot verify --
    most of what it did not print lies outside the subtree and was withheld
    by nothing -- so that count alone is phrased as a lower bound.

    A format-3 trace has no unframed calls, and neither committed old-format
    fixture holds one whose caller had a frame, so nothing reachable
    end-to-end still exercises the hedge; it stays pinned here directly,
    because the wording still ships for traces recorded by 0.2.x."""
    run_id = _rec(tmp_path, monkeypatch, src=GEN_SRC)
    assert cli.main(["tree", run_id, "--root", "f2", "--depth", "0"]) == 0
    out = capsys.readouterr().out
    assert "main()" in out and "rows(" not in out
    assert "1 subtree(s) beyond --depth 0 or --limit 200" in out
    assert f"sensorium tree {run_id} --root f3" in out
    assert "unframed" not in out
    note = tree_cmd._truncation_note("r1", 0, 200, [], 1, unframed_exact=False)
    assert "at least 1 unframed call(s) withheld by --depth 0" in note


# `amain` awaits `inner` directly. Both are coroutines, and both have real
# frames now: `inner` is `amain`'s CHILD, so the tree nests it rather than
# rendering the two as siblings under one task header with a `<-` tag --
# which read as two unrelated coroutines linked by a note.
AWAIT_SRC = """
import asyncio

def leaf():
    return 1

async def inner():
    return leaf()

async def amain():
    return await inner()

if __name__ == "__main__":
    asyncio.run(amain())
"""


def test_tree_nests_an_awaited_coroutine_under_its_awaiter(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=AWAIT_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    inner_ln = next(ln for ln in out.splitlines() if "inner(" in ln)
    amain_ln = next(ln for ln in out.splitlines() if "amain(" in ln)
    assert amain_ln.endswith("amain()  [coroutine] -> 1")
    assert inner_ln.endswith("inner()  [coroutine] -> 1")
    ai = len(amain_ln) - len(amain_ln.lstrip())
    assert inner_ln.startswith(" " * (ai + 2) + "f")     # child, not sibling
    assert "<-" not in out            # parentage is structural now, not a tag


def test_tree_state_tails_name_cancelled_abandoned_thrown_and_suspended(
        tmp_path, monkeypatch, capsys):
    """A frame that never returned did not simply stay "(open)": the trace
    holds WHICH way it ended, and each way says so in its own words. One
    tail for all of them would tell a reader that a cancelled task, a
    generator dropped by the garbage collector and one still parked at a
    yield when recording stopped are the same event.

    The states are derived by `Trace.frame_state` (spec D2); this pins that
    `tree` renders each of them, and renders nothing for a frame that simply
    returned."""
    from tests.test_coroutine_frames import ABANDON, CANCEL, LOUD_THROW
    tail = '\nif __name__ == "__main__":\n    main()\n'

    run_id = _rec(tmp_path / "c", monkeypatch, src=CANCEL + tail)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    b = "\n".join(_section(out, "task t3: task-B"))
    worker = next(ln for ln in b.splitlines() if "worker(" in ln)
    assert worker.endswith(
        "worker()  [coroutine]  ~ cancelled "
        "(CancelledError thrown in at L10)"), out
    # task-A waited at the same gate and was let through: it just returned.
    a = "\n".join(_section(out, "task t2: task-A"))
    assert "worker()  [coroutine] -> 2" in a and "~" not in a

    run2 = _rec(tmp_path / "d", monkeypatch, src=ABANDON + tail)
    assert cli.main(["tree", run2]) == 0
    out2 = capsys.readouterr().out
    gens = [ln for ln in out2.splitlines() if "gen()" in ln]
    assert len(gens) == 2, out2
    assert gens[0].endswith(
        "gen()  [generator]  ~ abandoned (GeneratorExit thrown in at L6)")
    assert gens[1].endswith(
        "gen()  [generator]  ~ suspended at L6 at end of recording")
    assert "(open)" not in out2           # neither is merely "still running"

    # ...and an exception thrown INTO a parked frame is neither of those: it
    # did not raise on its own line, and the tail says where it was hit.
    run3 = _rec(tmp_path / "e", monkeypatch, src=LOUD_THROW + tail)
    assert cli.main(["tree", run3]) == 0
    out3 = capsys.readouterr().out
    gen_ln = next(ln for ln in out3.splitlines() if "gen()" in ln)
    assert gen_ln.endswith(
        "gen()  [generator]  ~ unwound by Loud thrown in at L10")


# `gen`'s frame is already parked at its first `yield` when recording starts,
# so it never opened a frame -- and when it resumes and calls `helper`, that
# call has a traced caller with no frame. On a format-1/2 trace the reason
# was "coroutines and generators open no frame in this version"; here it is
# the only reason left, and the tag has to say the true one.
PRE_STARTED = """
def helper():
    return 1

def gen():
    yield 0
    yield helper()

G = gen()
next(G)

def main():
    return next(G)
"""


def test_tree_tags_a_caller_whose_frame_started_before_recording(
        tmp_path, monkeypatch, capsys):
    trace, err = record_inproc(tmp_path / "r", PRE_STARTED)
    assert err is None
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    shutil.copy(tmp_path / "r" / "trace.db", paths.traces_dir() / "pre.db")
    assert cli.main(["tree", "pre"]) == 0
    out = capsys.readouterr().out
    helper_ln = next(ln for ln in out.splitlines() if "helper(" in ln)
    assert helper_ln.endswith("<- gen (no frame: started before recording)")
    assert "unframed" not in out


# `Evil.get_name()` raises, so the recorder mints the task identity but
# cannot read its name and stores NULL. NULL means "the name could not be
# read", never "the task had no name" -- the label must not claim the latter.
HOSTILE_TASK_SRC = """
import asyncio

class Evil(asyncio.Task):
    def get_name(self):
        raise RuntimeError("no name for you")

def leaf():
    return 1

async def inner():
    return leaf()

async def amain():
    loop = asyncio.get_running_loop()
    return await Evil(inner(), loop=loop)

def main():
    return asyncio.run(amain())

if __name__ == "__main__":
    main()
"""


def test_tree_says_a_task_name_was_unreadable_not_that_it_was_unnamed(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=HOSTILE_TASK_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert "(name unreadable)" in out
    assert "(unnamed)" not in out


# `cb` is handed to the loop with `call_soon`: it runs INSIDE a running
# event loop, on the loop thread, with `asyncio.current_task()` returning
# None -- so its events carry a NULL task_id exactly like `<module>`'s do.
# The group they share cannot be called "outside any event loop" without
# saying something false about half of it.
CALL_SOON_SRC = """
import asyncio

def leaf():
    return 1

def cb():
    leaf()

async def amain():
    loop = asyncio.get_running_loop()
    loop.call_soon(cb)
    await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(amain())
"""


def test_tree_null_task_group_does_not_claim_the_code_ran_outside_the_loop(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, src=CALL_SOON_SRC)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    group = "\n".join(_section(out, "no asyncio task"))
    assert "cb(" in group, out          # ran in the loop, and is in the group
    assert "<module>()" in group        # ran before it, and is in the same one
    assert "outside any event loop" not in out
    assert "outside" not in out


@pytest.mark.skipif(
    sys.version_info < (3, 14),
    reason="on 3.12/3.13 asyncio.Task.__init__ itself calls hash() on the "
           "new task to register it in the pure-Python _all_tasks WeakSet "
           "(_register_task), so constructing a hostile-__hash__ Task "
           "subclass raises before sensorium's tracer ever sees the task -- "
           "reproduces identically with no sensorium import at all. 3.14 "
           "does not register tasks that way, so this is a CPython version "
           "fact, not a sensorium defect; the tool's claim (a hostile task "
           "hash is counted, never crashes the program) is exercised on 3.14.")
def test_tree_null_task_group_admits_it_may_be_an_unreadable_identity(
        tmp_path, monkeypatch, capsys):
    """When the identity lookup RAISED, a NULL task_id means "could not
    tell", not "no task" -- and both readings are live in the same group.
    `info` already says how many lookups broke; the group label has to
    admit it too, or a reader takes the group at face value."""
    from tests.test_async import HOSTILE_HASH_TASK
    src = HOSTILE_HASH_TASK + '\nif __name__ == "__main__":\n    main()\n'
    run_id = _rec(tmp_path, monkeypatch, src=src)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert "lookup error(s), see info" in out
    header = next(ln for ln in out.splitlines()
                  if ln.startswith("no asyncio task"))
    assert "task identity unreadable" in header


def test_tree_subtree_views_omit_the_inter_task_ordering_footer(
        tmp_path, monkeypatch, capsys):
    """`--root` and `--around` show one frame's descendants. A line about the
    order BETWEEN tasks describes nothing the reader can see there, so only
    the parentage-basis caveat -- a property of the recording, not of the
    slice -- survives into a subtree view."""
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["tree", run_id, "--root", "f1"]) == 0
    assert "order between tasks" not in capsys.readouterr().out
    assert cli.main(["tree", run_id, "--around", "e1"]) == 0
    assert "order between tasks" not in capsys.readouterr().out


def test_frame_fn_opens_a_coroutine_and_still_refuses_an_unrecorded_name(
        tmp_path, monkeypatch, capsys):
    """`--fn worker` used to refuse: worker is a coroutine and had no frame.
    It has one now, so the refusal would be the false claim. The OTHER arm
    -- a name the trace never saw at all -- must keep refusing, or the two
    become indistinguishable in the opposite direction."""
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["frame", run_id, "--fn", "worker"]) == 0
    out = capsys.readouterr().out
    assert "not framed" not in out and "unframed" not in out
    assert out.splitlines()[0].startswith("f")
    assert "args: name='A'" in out
    assert cli.main(["frame", run_id, "--fn", "nope"]) == 1
    assert "no recorded activations of 'nope'" in capsys.readouterr().out


def test_frame_nth_ranges_over_coroutine_frames_too(
        tmp_path, monkeypatch, capsys):
    """One qualname, two code objects: a plain `worker` here and a coroutine
    `worker` in the imported module. All three activations are framed now,
    so `--nth` reaches every one of them and the refusal past the end counts
    all three -- reporting "1 framed activation(s)" while `grep` shows three
    CALLs is the denial `--fn` was already fixed for once."""
    (tmp_path / "b.py").write_text("async def worker():\n    return 1\n")
    src = """
import asyncio
import b

def worker():
    return 0

async def amain():
    await b.worker()
    await b.worker()

if __name__ == "__main__":
    worker()
    asyncio.run(amain())
"""
    run_id = _rec(tmp_path, monkeypatch, src=src)
    assert cli.main(["frame", run_id, "--fn", "worker", "--nth", "3"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("f")
    assert cli.main(["frame", run_id, "--fn", "worker", "--nth", "4"]) == BAD_CALL
    out = capsys.readouterr().out
    assert "3 framed activation(s)" in out
    assert "valid --nth is 1..3 over the framed ones" in out
    assert "unframed" not in out


def test_tree_marks_each_frame_with_its_own_kind_not_the_first(
        tmp_path, monkeypatch, capsys):
    """`shape` is a generator in one module and a coroutine in the other.
    The kind is a property of the FRAME, not of the qualname: labelling both
    with whichever kind the trace recorded first -- the shape the old
    unframed message was fixed for -- would call a coroutine a generator."""
    (tmp_path / "b.py").write_text("async def shape():\n    return 1\n")
    src = """
import asyncio
import b

def shape():
    yield 1

async def amain():
    await b.shape()

if __name__ == "__main__":
    list(shape())
    asyncio.run(amain())
"""
    run_id = _rec(tmp_path, monkeypatch, src=src)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    shapes = [ln for ln in out.splitlines() if "shape()" in ln]
    assert len(shapes) == 2, out
    assert sum("[generator]" in ln for ln in shapes) == 1
    assert sum("[coroutine]" in ln for ln in shapes) == 1


def test_frame_header_names_the_task(tmp_path, monkeypatch, capsys):
    # `step` is called BY the worker coroutine, whose frame is its parent:
    # depth 1, not the depth 0 it had while coroutines opened no frames.
    run_id = _rec(tmp_path, monkeypatch, src=ASYNC_SRC)
    assert cli.main(["frame", run_id, "--fn", "step", "--nth", "1"]) == 0
    head = capsys.readouterr().out.splitlines()[0]
    assert "task t2 (task-A)" in head and "depth 1" in head


def test_frame_header_is_byte_identical_for_a_sync_function(
        tmp_path, monkeypatch, capsys):
    """A plain function's frame carries no kind marker (kind == "function"
    prints nothing, exactly as it always has) and no `state:` segment --
    `frame_state` derives "returned" here, which is precisely the arm the
    contract excludes. The header must be the exact string arc 1 printed,
    unchanged by Task 7's addition."""
    run_id = _rec(tmp_path, monkeypatch)     # SRC: silver() runs twice
    assert cli.main(["frame", run_id, "--fn", "silver", "--nth", "1"]) == 0
    head = capsys.readouterr().out.splitlines()[0]
    # No kind marker: the qualname is followed directly by the event-range
    # bracket, with the same two spaces arc 1 always used -- nothing
    # inserted between them.
    assert "silver  [e" in head
    assert "state:" not in head
    assert head.endswith("closed: return")


def test_frame_header_shows_kind_and_derived_state_for_a_cancelled_frame(
        tmp_path, monkeypatch, capsys):
    """Task-B's `worker` never returned: it was cancelled while parked at
    `await GATE.wait()`. The header has to say WHICH kind of frame this is
    (a coroutine, not a plain function) and how `frame_state` (spec D2)
    derived it ended -- `closed: unwind` alone does not distinguish a
    cancellation from an ordinary raised exception. No --focus was set, so
    locals are not captured, but the YIELD/RESUME suspension rows are
    recorded regardless and must still show up under their own heading."""
    from tests.test_coroutine_frames import CANCEL
    tail = '\nif __name__ == "__main__":\n    main()\n'
    run_id = _rec(tmp_path, monkeypatch, src=CANCEL + tail)
    assert cli.main(["frame", run_id, "--fn", "worker", "--nth", "2"]) == 0
    out = capsys.readouterr().out
    head = out.splitlines()[0]
    assert "[coroutine]" in head
    assert "state: cancelled at L10" in head

    assert "timeline: not captured" in out       # locals genuinely weren't
    susp = _section(out, "timeline (suspensions only):")
    assert len(susp) == 2, susp
    assert all(ln.startswith("  ~ e") for ln in susp)
    yield_ln = next(ln for ln in susp if "YIELD" in ln)
    assert "L10" in yield_ln and "awaiting" in yield_ln
    resume_ln = next(ln for ln in susp if "RESUME" in ln)
    assert "L10" in resume_ln and "thrown" in resume_ln
    assert "CancelledError" in resume_ln

    # task-A waited at the same gate and was let through: it just returned.
    # A returned coroutine frame still shows the `[coroutine]` marker and a
    # `state: returned` segment, because the exclusion only applies to a
    # plain function's frame -- the kind alone (not the state) decides
    # whether a coroutine's header carries a `state:` segment at all.
    assert cli.main(["frame", run_id, "--fn", "worker", "--nth", "1"]) == 0
    head_a = capsys.readouterr().out.splitlines()[0]
    assert "[coroutine]" in head_a
    assert "state: returned" in head_a


def test_frame_timeline_interleaves_suspension_rows_among_line_rows(
        tmp_path, monkeypatch, capsys):
    """A focused coroutine's timeline is ONE ordered list, not two
    disconnected views: LINE rows (locals, from --focus) and YIELD/RESUME
    rows (suspension points, captured regardless of --focus) share it, in
    event order. Only the suspension rows carry the `~ ` prefix, and they
    must land BETWEEN the LINE rows they actually fall between -- `before`
    is bound, then the coroutine suspends and resumes, then `after` is
    bound -- not gathered under a separate "suspensions only" heading just
    because --focus also captured locals for this frame."""
    from tests.test_coroutine_frames import SUSPEND_LOCALS
    tail = '\nif __name__ == "__main__":\n    main()\n'
    run_id = _rec(tmp_path, monkeypatch, src=SUSPEND_LOCALS + tail,
                  extra=("--focus", "prog:worker"))
    assert cli.main(["frame", run_id, "--fn", "worker"]) == 0
    out = capsys.readouterr().out
    assert "timeline (suspensions only):" not in out

    tl = _section(out, "timeline:")
    before_idx = next(i for i, ln in enumerate(tl) if "before=1" in ln)
    after_idx = next(i for i, ln in enumerate(tl) if "after=2" in ln)
    yield_idx = next(i for i, ln in enumerate(tl) if "YIELD" in ln)
    resume_idx = next(i for i, ln in enumerate(tl) if "RESUME" in ln)
    # LINE rows carry no `~ ` prefix; YIELD/RESUME rows do.
    assert not tl[before_idx].strip().startswith("~")
    assert not tl[after_idx].strip().startswith("~")
    assert tl[yield_idx].strip().startswith("~")
    assert tl[resume_idx].strip().startswith("~")
    # event order: bound `before`, suspended, resumed, bound `after` --
    # the suspension rows sit strictly between the two LINE rows, not
    # trailing after both or leading before both.
    assert before_idx < yield_idx < resume_idx < after_idx


def test_frame_prints_where_a_panic_fired_not_merely_that_one_did(
        tmp_path, monkeypatch, capsys):
    """A Rust `unwind_exc` carries the `loc` the panic fired at, which is
    NOT the frame's own line: the frame is where the unwind was observed,
    `loc` is where it began. Dropping it turns "this frame unwound HERE"
    into "this frame unwound", and the reader has nowhere to look."""
    from tests.vectors import build
    vector = {
        "id": "adhoc-panic-loc",
        "codes": [["/w/src/lib.rs", "boom", 1]],
        "frames": [{"parent": None, "code": 1, "call": 1, "depth": 0,
                    "thread": 1, "closed_by": "unwind", "kind": "function",
                    "unwind_exc": {"type": "panic", "msg": "kaboom",
                                   "serial": 1,
                                   "loc": "src/lib.rs:12:9"}}],
        "events": [{"ts": 1, "thread": 1, "kind": "CALL", "code": 1,
                    "line": 1, "payload": {"args": {}, "unread": ["locals"]},
                    "task": None}],
        "meta": {"trace_format": 4, "lang": "rust",
                 "recorder": "sensorium-rt 0.1.0"},
    }
    build(vector, tmp_path / "sdir", ["20260101-000000-panloc"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["frame", "20260101-000000-panloc", "--fn", "boom"]) == 0
    out = capsys.readouterr().out
    assert "unwound: panic('kaboom') at src/lib.rs:12:9" in out, out


def test_frame_prints_no_dangling_at_when_the_unwind_has_no_location(
        tmp_path, monkeypatch, capsys):
    """A panic the converter could not match to a PANIC record carries no
    `loc`. The line must then end at the exception -- a trailing ` at ` is
    a location the trace does not have, rendered as one it does."""
    from tests.vectors import build
    vector = {
        "id": "adhoc-panic-noloc",
        "codes": [["/w/src/lib.rs", "boom", 1]],
        "frames": [{"parent": None, "code": 1, "call": 1, "depth": 0,
                    "thread": 1, "closed_by": "unwind", "kind": "function",
                    "unwind_exc": {"type": "panic", "serial": 0,
                                   "msg": "<panic message not recorded: no "
                                          "PANIC record preceded this "
                                          "unwind>"}}],
        "events": [{"ts": 1, "thread": 1, "kind": "CALL", "code": 1,
                    "line": 1, "payload": {"args": {}, "unread": ["locals"]},
                    "task": None}],
        "meta": {"trace_format": 4, "lang": "rust",
                 "recorder": "sensorium-rt 0.1.0"},
    }
    build(vector, tmp_path / "sdir", ["20260101-000000-nopanl"])
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["frame", "20260101-000000-nopanl", "--fn", "boom"]) == 0
    out = capsys.readouterr().out
    assert "panic message not recorded" in out
    assert " at " not in out.split("unwound: ")[1], out
