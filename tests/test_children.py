"""Python child processes land in the same run, under the spawning frame.

pytest-xdist is not a dependency. It starts workers with `sys.executable`,
which is the subprocess path covered here. multiprocessing is exercised on
fork and spawn, and on the interpreter's default (forkserver on 3.14+).
"""
import multiprocessing as mp

from sensorium.record.fingerprint import CAUSAL_KINDS
from sensorium.store.reader import Trace

from tests.helpers import record_script, run_cli


SUBPROCESS_CHILD = """
import subprocess
import sys

def child_work():
    return 7

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        child_work()
        return
    subprocess.run([sys.executable, sys.argv[0], "child"], check=True)

if __name__ == "__main__":
    main()
"""


def _mp_source(method: str) -> str:
    return f"""
import multiprocessing as mp

def child_work(n):
    return n + 1

def main():
    ctx = mp.get_context({method!r})
    proc = ctx.Process(target=child_work, args=(1,))
    proc.start()
    proc.join()
    if proc.exitcode != 0:
        raise SystemExit(proc.exitcode or 1)

if __name__ == "__main__":
    main()
"""


OPT_OUT = """
import subprocess
import sys

def child_work():
    return 1

def main():
    subprocess.run([sys.executable, sys.argv[0], "child"], check=True)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "child":
        child_work()
    else:
        main()
"""


NON_PYTHON = """
import subprocess

def main():
    subprocess.run(["/bin/true"], check=True)

if __name__ == "__main__":
    main()
"""


NO_SPAWN = """
def main():
    return 1

if __name__ == "__main__":
    main()
"""


def _open(trace):
    assert trace is not None
    return Trace.open(trace)


def _qualnames(trace):
    t = _open(trace)
    return {t.code(e.code_id).qualname for e in t.events(kind="CALL")
            if e.code_id is not None}


def _ancestors(trace, frame):
    t = trace
    seen = set()
    while frame is not None and frame.id not in seen:
        seen.add(frame.id)
        yield frame
        if frame.parent_id is None:
            break
        frame = t.frame(frame.parent_id)


def _linked(trace, child="child_work", parent="main"):
    """child's frame has `parent` somewhere above it, and is not a root."""
    t = _open(trace)
    frames = [f for f in t.frames()
              if t.code(f.code_id).qualname == child]
    assert frames, f"no frame named {child}"
    linked = False
    for frame in frames:
        names = [t.code(f.code_id).qualname for f in _ancestors(t, frame)]
        if parent in names and names[0] == child:
            # parent is an ancestor, not the child frame itself
            if names.index(parent) > 0:
                linked = True
                assert frame.parent_id is not None
    assert linked, "child frame is not under the spawning frame"
    main_tid = t.meta["main_thread_ident"]
    child_tids = set()
    for event in t.events(kind="CALL"):
        if event.code_id is None:
            continue
        if t.code(event.code_id).qualname == child:
            assert event.thread_id != main_tid
            child_tids.add(event.thread_id)
    fps = t.fingerprints()
    assert child_tids
    for tid in child_tids:
        assert tid in fps
    assert t.meta.get("child_record_errors") == 0
    assert t.meta.get("python_children", 0) >= 1
    # The parent's own fingerprint covers only the main thread. Child
    # events were merged onto other thread ids and must not be folded in.
    causal = [e for e in t.events()
              if e.thread_id == main_tid and e.task_id is None
              and e.kind in CAUSAL_KINDS]
    digest = t.fingerprints()[main_tid]
    assert digest[1] == len(causal)


def test_subprocess_child_links_to_the_callers_frame(tmp_path):
    run_id, trace, result = record_script(tmp_path, SUBPROCESS_CHILD)
    assert result.returncode == 0, result.stderr
    assert run_id
    assert "child_work" in _qualnames(trace)
    _linked(trace)


def test_multiprocessing_child_links_on_fork_and_spawn(tmp_path):
    methods = ["fork", "spawn"]
    default = mp.get_start_method()
    if default not in methods:
        methods.append(default)
    for method in methods:
        run_id, trace, result = record_script(
            tmp_path / method, _mp_source(method))
        assert result.returncode == 0, (method, result.stderr, result.stdout)
        assert run_id
        assert "child_work" in _qualnames(trace), method
        _linked(trace)


def test_opt_out_fork_does_not_inherit_the_parent_trace(tmp_path):
    """A forked child shares the parent's monitoring until it is detached.

    Without that, `--no-children` still records `child_work` into the
    parent file. Spawn never shares that file; fork does.
    """
    for method in ("fork", "spawn"):
        _, trace, result = record_script(
            tmp_path / method, _mp_source(method), extra=("--no-children",))
        assert result.returncode == 0, (method, result.stderr)
        names = _qualnames(trace)
        assert "main" in names
        assert "child_work" not in names, method


def test_opt_out_records_the_parent_but_not_the_child(tmp_path):
    run_id, trace, result = record_script(
        tmp_path / "flag", OPT_OUT, extra=("--no-children",))
    assert result.returncode == 0, result.stderr
    assert run_id
    names = _qualnames(trace)
    assert "main" in names
    assert "child_work" not in names

    run_id, trace, result = record_script(
        tmp_path / "env", OPT_OUT,
        env_extra={"SENSORIUM_NO_CHILDREN": "1"})
    assert result.returncode == 0, result.stderr
    assert run_id
    names = _qualnames(trace)
    assert "main" in names
    assert "child_work" not in names


def test_non_python_child_is_not_traced(tmp_path):
    run_id, trace, result = record_script(tmp_path, NON_PYTHON)
    assert result.returncode == 0, result.stderr
    assert run_id
    t = _open(trace)
    assert "child_work" not in _qualnames(trace)
    listed = t.meta.get("children") or []
    assert any("/bin/true" in part for cmd in listed for part in cmd)
    assert t.meta.get("non_python_children", 0) >= 1
    assert t.meta.get("python_children") == 0
    assert t.meta.get("child_record_errors") == 0


def test_no_spawn_fingerprint_matches_opt_out(tmp_path):
    # Same directory: the fingerprint hashes the source path, so two
    # working directories would differ even when the run did not.
    _, trace_on, on = record_script(tmp_path, NO_SPAWN)
    _, trace_off, off = record_script(
        tmp_path, NO_SPAWN, extra=("--no-children",))
    assert on.returncode == 0, on.stderr
    assert off.returncode == 0, off.stderr
    assert _open(trace_on).fingerprints() == _open(trace_off).fingerprints()


def test_run_help_mentions_no_children(tmp_path):
    result = run_cli(["run", "--help"], cwd=tmp_path, sensorium_dir=tmp_path)
    assert result.returncode == 0
    assert "--no-children" in result.stdout
    assert "SENSORIUM_NO_CHILDREN" in result.stdout


def test_a_corrupt_child_spool_is_counted_not_raised(tmp_path):
    from sensorium.record.boot import _LateWriteGuard
    from sensorium.record.children import merge_children
    from sensorium.store.writer import TraceWriter

    guard = _LateWriteGuard(TraceWriter(tmp_path / "parent.db"))
    spool = tmp_path / "spool"
    spool.mkdir()
    (spool / "9.db").write_bytes(b"this is not a sqlite database")
    stats = merge_children(guard, spool)
    assert stats["child_record_errors"] >= 1
    assert stats["python_children"] == 0
