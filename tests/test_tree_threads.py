"""`tree` groups an extra OS thread under the frame that started it.

A `threading.Thread` body is a root: its parent is the stdlib bootstrap on
the other thread, so without a heading it looks like a second entry point.
The heading is recorded, not guessed. A trace that never stored
`thread_starts` (older recordings, other languages) stays ungrouped, and a
single-threaded trace grows no heading.
"""
import re

from sensorium import cli, paths
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import record_script


MAIN_ONLY = """
def leaf(n):
    return n + 1

def main():
    return leaf(1)

main()
"""

THREAD_SRC = """
import threading

def leaf():
    return 1

def worker():
    return leaf()

def main():
    started = threading.Thread(target=worker, name="worker")
    started.start()
    started.join()

main()
"""

POOL_SRC = """
from concurrent.futures import ThreadPoolExecutor

def leaf():
    return 1

def work():
    return leaf()

def main():
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(work).result()

main()
"""


def _rec(tmp_path, monkeypatch, src):
    run_id, _trace, result = record_script(tmp_path, src)
    assert run_id, result.stderr
    assert result.returncode == 0, result.stderr
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    return run_id


def _headings(out: str) -> list[str]:
    return [ln for ln in out.splitlines() if ln.startswith("thread ")]


def _section(out: str, header: str) -> list[str]:
    lines = out.splitlines()
    i = lines.index(header)
    body = []
    for ln in lines[i + 1:]:
        if ln and not ln.startswith(" "):
            break
        body.append(ln)
    return body


def _open(run_id) -> Trace:
    return Trace.open(paths.find_trace(run_id))


def test_main_thread_only_has_no_thread_heading(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, MAIN_ONLY)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert "leaf(" in out and "main(" in out
    assert _headings(out) == []
    assert "starter not recorded" not in out
    assert "started by " not in out
    # The key is present and empty: absence of a heading is "one thread",
    # not "this trace predates the key".
    assert _open(run_id).meta["thread_starts"] == []


def test_thread_heading_names_the_start_caller(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, THREAD_SRC)
    trace = _open(run_id)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    headings = _headings(out)
    assert len(headings) == 1, out
    heading = headings[0]
    match = re.search(r"^thread worker  started by f(\d+) (\S+)$", heading)
    assert match, heading
    fid = int(match.group(1))
    assert match.group(2) == "main"
    code = trace.code(trace.frame(fid).code_id)
    assert code.qualname == "main"
    assert code.file.endswith("prog.py")
    assert "threading.py" not in code.file
    body = _section(out, heading)
    worker = next(ln for ln in body if "worker(" in ln)
    leaf = next(ln for ln in body if "leaf(" in ln)
    assert worker.startswith("  ")
    assert len(leaf) - len(leaf.lstrip()) > len(worker) - len(worker.lstrip())
    # The worker is not a second unheaded entry point.
    assert not any(ln.startswith("f") and "worker(" in ln for ln in out.splitlines())
    rows = trace.meta["thread_starts"]
    assert len(rows) == 1
    assert rows[0]["name"] == "worker"
    assert rows[0]["frame"] == fid
    wfid = int(worker.split()[0][1:])
    assert rows[0]["thread"] == trace.frame(wfid).thread_id
    assert rows[0]["thread"] != trace.main_thread_id()


def test_pool_heading_links_the_submit_caller(tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, POOL_SRC)
    trace = _open(run_id)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    headings = _headings(out)
    assert len(headings) == 1, out
    heading = headings[0]
    assert "ThreadPoolExecutor" in heading
    match = re.search(r"started by f(\d+) (\S+)", heading)
    assert match, heading
    fid = int(match.group(1))
    code = trace.code(trace.frame(fid).code_id)
    assert code.qualname == "main"
    norm = code.file.replace("\\", "/")
    assert "concurrent/futures" not in norm
    assert not norm.endswith("/threading.py")
    assert code.file.endswith("prog.py")
    body = _section(out, heading)
    assert any("work(" in ln for ln in body)
    assert any("leaf(" in ln for ln in body)
    rows = trace.meta["thread_starts"]
    assert len(rows) == 1
    assert rows[0]["frame"] == fid
    assert rows[0]["name"] and "ThreadPoolExecutor" in rows[0]["name"]
    work = next(ln for ln in body if "work(" in ln)
    wfid = int(work.split()[0][1:])
    assert rows[0]["thread"] == trace.frame(wfid).thread_id


def test_root_on_main_does_not_preface_every_thread(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, THREAD_SRC)
    assert cli.main(["tree", run_id]) == 0
    full = capsys.readouterr().out
    module = next(ln for ln in full.splitlines() if "<module>(" in ln)
    assert cli.main(["tree", run_id, "--root", module.split()[0]]) == 0
    out = capsys.readouterr().out
    assert _headings(out) == []
    assert "worker(" not in out


def test_root_on_the_worker_notes_only_that_thread(
        tmp_path, monkeypatch, capsys):
    run_id = _rec(tmp_path, monkeypatch, THREAD_SRC)
    assert cli.main(["tree", run_id]) == 0
    full = capsys.readouterr().out
    heading = _headings(full)[0]
    body = _section(full, heading)
    worker = next(ln for ln in body if "worker(" in ln)
    assert cli.main(["tree", run_id, "--root", worker.split()[0]]) == 0
    out = capsys.readouterr().out
    headings = _headings(out)
    assert headings == [heading]
    assert out.splitlines()[0] == heading
    assert "leaf(" in out
    # The note is not the whole process: main's tree is not reprinted.
    assert "<module>(" not in out
    assert not any(ln.lstrip().startswith("f") and "main(" in ln
                   for ln in out.splitlines())


def _two_roots(tmp_path, monkeypatch, *, starts):
    """Two root frames on two threads. `starts` is the meta value, or None
    to leave the key off entirely."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    run_id = "20260101-000000-abcdef"
    writer = TraceWriter(paths.traces_dir() / f"{run_id}.db", batch=1)
    writer.set_meta("run_id", run_id)
    writer.set_meta("argv", ["prog.py"])
    writer.set_meta("main_thread_ident", 1)
    if starts is not None:
        writer.set_meta("thread_starts", starts)
    main = writer.intern_code("/tmp/prog.py", "main", 1)
    work = writer.intern_code("/tmp/prog.py", "worker", 5)
    call_m = writer.add_event(0, 1, "CALL", None, main, 1, {"args": {}})
    frame_m = writer.open_frame(None, main, call_m, 0, 1)
    ret_m = writer.add_event(1, 1, "RETURN", frame_m, main, 2, {"value": None})
    writer.close_frame(frame_m, return_event_id=ret_m)
    call_w = writer.add_event(2, 2, "CALL", None, work, 5, {"args": {}})
    frame_w = writer.open_frame(None, work, call_w, 0, 2)
    ret_w = writer.add_event(3, 2, "RETURN", frame_w, work, 6, {"value": None})
    writer.close_frame(frame_w, return_event_id=ret_w)
    writer.close()
    return run_id, frame_m


def test_missing_thread_starts_keeps_the_old_flat_tree(
        tmp_path, monkeypatch, capsys):
    run_id, _frame_m = _two_roots(tmp_path, monkeypatch, starts=None)
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert _headings(out) == []
    assert "starter not recorded" not in out
    assert "started by " not in out
    roots = [ln for ln in out.splitlines() if ln.startswith("f")]
    assert len(roots) == 2
    assert any("main(" in ln for ln in roots)
    assert any("worker(" in ln for ln in roots)


def test_unknown_starter_is_not_invented(tmp_path, monkeypatch, capsys):
    """A frame id the trace does not hold is not a link, and neither is null."""
    run_id, frame_m = _two_roots(
        tmp_path, monkeypatch,
        starts=[{"thread": 2, "name": "worker", "frame": None},
                {"thread": 9, "name": None, "frame": 999}])
    assert cli.main(["tree", run_id]) == 0
    out = capsys.readouterr().out
    assert _headings(out) == ["thread worker  starter not recorded"]
    assert "started by " not in out
    assert "f999" not in out
    assert "f0" not in out
    body = _section(out, "thread worker  starter not recorded")
    assert any(ln.lstrip().startswith("f") and "worker(" in ln for ln in body)
    # The recorded main frame stays unheaded, at column 0.
    main_line = next(ln for ln in out.splitlines() if "main(" in ln)
    assert main_line.startswith(f"f{frame_m} ")
