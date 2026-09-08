"""`tree` and `frame` over generator, coroutine and task activations.

The other half of `test_tree_frame`, split at the `ASYNC_SRC` seam on
2026-09-08 to bring both halves under the 800-line ceiling. Everything here
needs a frame that suspends -- a generator parked at a yield, a coroutine
awaiting, a task the loop owns -- which is what separates it from the sync
`tree`/`frame` surface the first file covers. The recording helper and
`GEN_SRC` are the first file's, imported and never copied.
"""
import shutil
import sys

import pytest

from sensorium.exit import BAD_CALL
from sensorium import cli, paths
from sensorium.query import tree_cmd
from tests.helpers import record_inproc
from tests.test_tree_frame import GEN_SRC, _rec


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
