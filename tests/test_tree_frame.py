"""`tree` and `frame`: what actually ran, and one activation in full."""
from sensorium import cli, paths
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script

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
    assert "narrow with --root f" in out


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


def test_frame_children_section_lists_child_frames(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)     # SRC: price() calls silver/gold
    assert cli.main(["frame", run_id, "--fn", "price", "--nth", "1"]) == 0
    out = capsys.readouterr().out
    assert "children (1):" in out
    assert "silver(" in out


def test_frame_unknown_ref_is_exit_1(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch)
    assert cli.main(["frame", run_id, "--fn", "does_not_exist"]) == 1
    assert "no such frame" in capsys.readouterr().out
