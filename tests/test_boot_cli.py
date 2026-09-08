"""Booting a target under recording, run metadata, and the `run` command.

What happens at the EDGES of a run -- threads that outlive the target, two
runs in one process, target resolution, and the contract that nothing stored
may be a live object -- is `test_boot_cli_run.py`'s, split off at the
`# -- a thread that outlives the target` banner on 2026-09-08. The program
sources, the `sandbox` fixture and `_trace_of` below are read from both sides.
"""
import io
import json
import sys
from pathlib import Path

import pytest

from sensorium import paths
from sensorium.record import boot
from sensorium.store.reader import Trace
from tests.helpers import record_script, run_cli

HELLO = """
def greet(name):
    print(f"hello {name}")
    return name

def main():
    greet("world")

if __name__ == "__main__":
    main()
"""

EXITS = """
import sys
sys.exit(3)
"""

SPAWNS = """
import subprocess, sys
subprocess.run([sys.executable, "-c", "pass"])
print("spawned")
"""

SPAWNS_TWICE = """
import subprocess, sys
for _ in range(2):
    subprocess.run([sys.executable, "-c", "pass"])
"""

READS_STDIN = """
line = input()
print("got", line)
"""

NEXT_STDIN = """
import sys
next(sys.stdin)                    # skip the header: the standard idiom
print("rest:", sys.stdin.read().strip())
"""

ITER_STDIN = """
import sys
for line in sys.stdin:
    print("line:", line.strip())
"""

BINARY_STDIN = """
import sys
print("bytes:", len(sys.stdin.buffer.read()))
"""

SPAWNS_BYTES = """
import subprocess
subprocess.run(b"exit 0", shell=True)
print("done")
"""

# A live thread whose name is a str subclass hostile to the recorder: its
# __str__ returns self (so threading's own str(name) does not normalise it
# away) and its comparisons raise. Sorting the still-alive names at teardown
# must not run that __lt__ and kill a program that finished cleanly.
HOSTILE_THREAD_NAME = """
import threading, time

class Evil(str):
    def __str__(self): return self
    def __lt__(self, other): raise RuntimeError("no ordering for you")
    def __gt__(self, other): raise RuntimeError("no ordering for you")

def spin():
    while True:
        time.sleep(0.01)

def main():
    # two, so the teardown's sort actually compares the names
    for i in (1, 2):
        threading.Thread(target=spin, name=Evil(f"evil-worker-{i}"),
                         daemon=True).start()
    print("main done")

if __name__ == "__main__":
    main()
"""

# sys.exit() handed an object whose __class__ raises. isinstance(code, int)
# consults __class__ for a non-int, so computing the exit status must not run
# it and kill the program from inside the recorder's own SystemExit handler.
HOSTILE_EXIT_CODE = """
import sys

class Weird:
    @property
    def __class__(self):
        raise RuntimeError("no class for you")

if __name__ == "__main__":
    print("about to exit")
    sys.exit(Weird())
"""

# A daemon thread parked inside a monitoring callback (capture calls the
# argument's __repr__) when the target's main function returns: its trace
# writes land after the writer has closed.
DAEMON = """
import threading, time

READY = threading.Event()

class Slow:
    def __repr__(self):
        READY.set()
        time.sleep(0.5)
        return "slow"

def worker(obj):
    return 1

def spin():
    worker(Slow())
    with open("daemon-ran.txt", "w") as f:
        f.write("yes")

def main():
    threading.Thread(target=spin, name="sensorium-daemon-test",
                     daemon=True).start()
    READY.wait(5)

main()
"""

META_CONTRACT = {
    "run_id", "argv", "cwd", "env", "env_hash", "python", "git_sha",
    "git_dirty_hash", "focus", "include", "exclude", "window", "caps",
    "start_ts", "end_ts", "exit_status", "uncaught", "stdin_consumed",
    "children", "truncated_count", "incomplete", "late_writes",
    "main_thread_ident",
}


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """cwd and trace store pointed somewhere disposable, for in-proc runs."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _trace_of(run_id):
    return Trace.open(paths.traces_dir() / f"{run_id}.db")


# -- recording a real program ---------------------------------------------
def test_records_and_propagates_exit_zero(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO)
    assert r.returncode == 0 and run_id is not None
    assert f"trace: {trace}" in r.stdout
    t = Trace.open(trace)
    assert t.meta["exit_status"] == 0
    assert t.meta["incomplete"] is False
    assert t.meta["argv"] == ["prog.py"]
    quals = {t.code(e.code_id).qualname for e in t.events(kind="CALL")}
    assert {"main", "greet"} <= quals
    # uninstall() writes these, so they only survive if it runs before close
    assert t.fingerprints()
    # main_thread_ident must name the thread that actually ran the target's
    # top-level code, not merely hold some int.
    main_call = next(e for e in t.events(kind="CALL")
                     if t.code(e.code_id).qualname == "main")
    assert t.meta["main_thread_ident"] == main_call.thread_id
    assert Trace.open(trace).main_thread_basis() == "recorded"


def test_stdout_passthrough_and_captured(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO)
    assert "hello world" in r.stdout          # passed through to real stdout
    t = Trace.open(trace)
    data = "".join(d for _, s, d in t.output_chunks() if s == "stdout")
    assert "hello world" in data              # and interleaved in the trace


def test_sys_exit_code_propagated(tmp_path):
    run_id, trace, r = record_script(tmp_path, EXITS)
    assert r.returncode == 3
    assert Trace.open(trace).meta["exit_status"] == 3


def test_uncaught_exception_recorded_and_exit_1(tmp_path):
    src = "def main():\n    raise ValueError('bad')\nmain()\n"
    run_id, trace, r = record_script(tmp_path, src)
    assert r.returncode == 1
    m = Trace.open(trace).meta
    assert m["uncaught"]["type"] == "ValueError"
    assert m["incomplete"] is False
    assert "ValueError: bad" in r.stderr       # the user is told, loudly


def test_child_processes_listed_not_witnessed(tmp_path):
    run_id, trace, r = record_script(tmp_path, SPAWNS)
    assert len(Trace.open(trace).meta["children"]) == 1


def test_bytes_popen_command_is_decoded_not_stringified(tmp_path):
    run_id, trace, r = record_script(tmp_path, SPAWNS_BYTES)
    assert r.returncode == 0, r.stderr
    m = Trace.open(trace).meta
    assert m["children"] == [["/bin/sh", "-c", "exit 0"]]   # not "b'exit 0'"
    assert m["incomplete"] is False                         # finalization ran


def test_the_audit_hook_swallows_its_own_failures_but_counts_them(
        monkeypatch):
    """An audit hook that raises breaks the operation being audited, so this
    one may never propagate -- but swallowing silently is how a hook bug
    becomes an empty `children` list that reads as "no subprocess ran". The
    licence gate downstream trusts that list, so a failure has to leave a
    mark. Driven directly: the failure modes are in the hook's argument
    handling, which no program can be relied on to provoke."""
    class Unlistable:
        def __iter__(self):
            raise RuntimeError("this command cannot be enumerated")

    children, threads, errors = [], [], []
    monkeypatch.setattr(boot, "_audit_sink", children)
    monkeypatch.setattr(boot, "_audit_threads", threads)
    monkeypatch.setattr(boot, "_audit_errors", errors)

    boot._audit("subprocess.Popen", (None, Unlistable(), None, None))

    assert children == [], "a failed extraction must not record a bogus child"
    assert len(errors) == 1, "the failure was swallowed without a trace"

    # ...and the sound path still works, so the guard is not just off
    boot._audit("os.system", ("exit 0",))
    assert children == [["exit 0"]]
    assert len(errors) == 1

    # An index past the end of `args` means the event table is WRONG about
    # this event. Returning quietly there would leave `children == []`
    # reading as "no subprocess ran" -- the failure this counter exists for.
    boot._audit("subprocess.Popen", ())
    assert children == [["exit 0"]], "no child should have been invented"
    assert len(errors) == 2, "a wrong table entry must not be silent"


def test_the_audit_hook_counts_spawn_syscalls_apart_from_children(monkeypatch):
    """`subprocess.Popen` nests a spawn syscall, so the two cannot share a
    list without counting every subprocess twice. They are separate
    observations: either being non-empty means a child was witnessed."""
    children, threads, errors, spawns = [], [], [], []
    monkeypatch.setattr(boot, "_audit_sink", children)
    monkeypatch.setattr(boot, "_audit_threads", threads)
    monkeypatch.setattr(boot, "_audit_errors", errors)
    monkeypatch.setattr(boot, "_audit_spawns", spawns)

    boot._audit("subprocess.Popen", (None, ["/bin/true"], None, None))
    boot._audit("os.posix_spawn", ("/bin/true", ["/bin/true"], {}))
    assert children == [["/bin/true"]], "one Popen, one entry"
    assert len(spawns) == 1, "the syscall is counted on its own"

    # multiprocessing spawn/forkserver: the syscall and nothing else
    boot._audit("_posixsubprocess.fork_exec", (None,))
    assert children == [["/bin/true"]]
    assert len(spawns) == 2
    assert errors == []


def test_the_audit_hook_counts_threads_however_they_are_started(monkeypatch):
    """Both spellings of thread creation, measured rather than assumed:
    `threading.Thread.start()` raises `_thread.start_joinable_thread` and
    `_thread.start_new_thread` raises its own event."""
    children, threads, errors = [], [], []
    monkeypatch.setattr(boot, "_audit_sink", children)
    monkeypatch.setattr(boot, "_audit_threads", threads)
    monkeypatch.setattr(boot, "_audit_errors", errors)

    boot._audit("_thread.start_joinable_thread", (None,))
    boot._audit("_thread.start_new_thread", (None, (), {}))
    assert len(threads) == 2
    assert children == [] and errors == []


def test_every_recorded_child_command_is_json_serializable(tmp_path):
    """Whatever lands in `children` must survive db.set_meta's json.dumps:
    a TypeError there aborts _finalize_meta and takes the run down with it."""
    sink = []
    boot._audit_sink = sink
    try:
        for args in ((None, b"exit 0", None, None),          # bare bytes
                     (None, "exit 0", None, None),           # bare str
                     (None, [b"/bin/ls", b"-l"], None, None),
                     (None, ["/bin/ls", Path("/tmp")], None, None),
                     (None, [b"/bin/ls", 7], None, None),
                     (None, None, None, None)):
            boot._audit("subprocess.Popen", args)
    finally:
        boot._audit_sink = None
    assert json.loads(json.dumps(sink)) == sink
    assert all(isinstance(a, str) for entry in sink for a in entry)
    assert sink[0] == ["exit 0"] and sink[2] == ["/bin/ls", "-l"]


def test_stdin_consumption_flagged(tmp_path):
    run_id, trace, r = record_script(tmp_path, READS_STDIN, stdin_text="x\n")
    assert Trace.open(trace).meta["stdin_consumed"] is True
    run_id2, trace2, _ = record_script(tmp_path / "b", HELLO)
    assert Trace.open(trace2).meta["stdin_consumed"] is False


def test_next_on_stdin_behaves_as_it_does_unrecorded(tmp_path):
    """`next(sys.stdin)` must not become a TypeError under recording."""
    run_id, trace, r = record_script(tmp_path, NEXT_STDIN,
                                     stdin_text="head\nbody\n")
    assert r.returncode == 0, r.stderr
    assert "rest: body" in r.stdout
    assert Trace.open(trace).meta["stdin_consumed"] is True


def test_stdin_iteration_behaves_as_it_does_unrecorded(tmp_path):
    run_id, trace, r = record_script(tmp_path, ITER_STDIN, stdin_text="a\nb\n")
    assert r.returncode == 0, r.stderr
    assert "line: a" in r.stdout and "line: b" in r.stdout
    assert Trace.open(trace).meta["stdin_consumed"] is True


def test_binary_stdin_read_marks_consumed(tmp_path):
    """A false negative here lets Task 15 claim MATCH on an unrepeatable
    run, which is the tool asserting something it cannot support."""
    run_id, trace, r = record_script(tmp_path, BINARY_STDIN,
                                     stdin_text="abc\n")
    assert r.returncode == 0, r.stderr
    assert "bytes: 4" in r.stdout
    assert Trace.open(trace).meta["stdin_consumed"] is True


def test_stdin_proxy_marks_every_consuming_path():
    def text():
        return boot._StdinProxy(io.TextIOWrapper(io.BytesIO(b"a\nb\n")))

    for name, use in {
            "read": lambda f: f.read(),
            "readline": lambda f: f.readline(),
            "readlines": lambda f: f.readlines(),
            "iter": lambda f: next(iter(f)),
            "next": lambda f: next(f),
            "buffer": lambda f: f.buffer,
            "detach": lambda f: f.detach()}.items():
        p = text()
        use(p)
        assert p.consumed is True, name
    for name, use in {"read1": lambda f: f.read1(2),
                      "readinto": lambda f: f.readinto(bytearray(2))}.items():
        p = boot._StdinProxy(io.BytesIO(b"abc"))
        use(p)
        assert p.consumed is True, name
    p = text()
    with p as f:
        assert f is p          # not the raw stream, or reads go unmarked
        f.readline()
    assert p.consumed is True
    p = text()                 # control: inspection is not consumption
    assert (p.encoding, p.closed, p.isatty(), repr(p)) and p.consumed is False


def test_iterating_stdin_yields_the_same_lines_as_the_raw_stream():
    p = boot._StdinProxy(io.TextIOWrapper(io.BytesIO(b"a\nb\n")))
    assert iter(p) is p and list(p) == ["a\n", "b\n"]


# -- run metadata: the key names later tasks read -------------------------
def test_meta_key_contract(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO)
    m = Trace.open(trace).meta
    assert META_CONTRACT <= set(m)
    assert "refocus_of" not in m               # only present when set
    assert m["run_id"] == run_id
    assert Path(m["cwd"]).resolve() == tmp_path.resolve()
    assert m["python"] == sys.version.split()[0]
    assert m["focus"] == [] and m["include"] == [] and m["exclude"] == []
    assert m["window"] is None and m["uncaught"] is None
    assert m["caps"]["str"] > 0
    assert m["end_ts"] >= m["start_ts"]
    assert m["env"]["SENSORIUM_DIR"] == str(tmp_path / "sdir")
    assert len(m["env_hash"]) == 16
    assert m["truncated_count"] >= 0 and m["late_writes"] == 0


def test_refocus_of_recorded_when_given(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO,
                                     extra=["--refocus-of", "20260818-x"])
    assert Trace.open(trace).meta["refocus_of"] == "20260818-x"


def test_focus_option_reaches_the_tracer(tmp_path):
    run_id, trace, r = record_script(tmp_path, HELLO,
                                     extra=["--focus", "prog:greet"])
    t = Trace.open(trace)
    assert t.meta["focus"] == ["prog:greet"]
    assert t.events(kind="LINE")               # focus tier actually engaged


# -- honest failure -------------------------------------------------------
def test_unresolvable_target_is_clear_error(tmp_path):
    r = run_cli(["run", "--", "no-such-cmd-xyz"], cwd=tmp_path,
                sensorium_dir=tmp_path / "s")
    assert r.returncode == 2 and "cannot resolve" in r.stderr


def test_missing_script_is_clear_error(tmp_path):
    r = run_cli(["run", "--", "nope.py"], cwd=tmp_path,
                sensorium_dir=tmp_path / "s")
    assert r.returncode == 2 and "cannot resolve" in r.stderr


def test_run_id_may_not_escape_the_trace_store(tmp_path):
    """`--run-id` flows straight into `traces_dir() / f"{run_id}.db"`, whose
    parent is created with `parents=True`, so a `..` or `/` would write a trace
    outside the store. It must be refused, cleanly, and write nothing."""
    (tmp_path / "prog.py").write_text("print('hi')\n")
    r = run_cli(["run", "--run-id", "../../pwned", "--", "prog.py"],
                cwd=tmp_path, sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "invalid run id" in r.stderr
    assert "Traceback" not in r.stderr           # a clean refusal, not a crash
    # nothing was created anywhere the id tried to reach
    assert not (tmp_path.parent / "pwned.db").exists()
    assert not list(tmp_path.rglob("pwned.db"))


def test_run_id_rejects_an_absolute_path(tmp_path):
    (tmp_path / "prog.py").write_text("print('hi')\n")
    r = run_cli(["run", "--run-id", "/tmp/pwned", "--", "prog.py"],
                cwd=tmp_path, sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 2 and "invalid run id" in r.stderr


def test_run_id_collision_is_a_clean_error_not_a_traceback(tmp_path):
    """A --run-id that already names a trace must refuse cleanly, not crash
    with a raw `sqlite3.OperationalError: table meta already exists`."""
    (tmp_path / "prog.py").write_text("print('hi')\n")
    argv = ["run", "--run-id", "fixed1", "--", "prog.py"]
    r1 = run_cli(argv, cwd=tmp_path, sensorium_dir=tmp_path / "sdir")
    assert r1.returncode == 0, r1.stderr
    r2 = run_cli(argv, cwd=tmp_path, sensorium_dir=tmp_path / "sdir")
    assert r2.returncode == 2
    assert "already" in r2.stderr and "fixed1" in r2.stderr
    assert "Traceback" not in r2.stderr


def test_no_target_prints_usage(tmp_path):
    r = run_cli(["run"], cwd=tmp_path, sensorium_dir=tmp_path / "s")
    assert r.returncode == 2 and "usage: sensorium run" in r.stderr


def test_install_failure_is_loud_and_leaves_incomplete_trace(sandbox):
    (sandbox / "prog.py").write_text(HELLO)
    streams = (sys.stdin, sys.stdout, sys.stderr)
    tool = sys.monitoring.PROFILER_ID
    sys.monitoring.use_tool_id(tool, "another-profiler")
    try:
        with pytest.raises(RuntimeError, match="already in use"):
            boot.run_target(["prog.py"])
    finally:
        sys.monitoring.free_tool_id(tool)
    assert (sys.stdin, sys.stdout, sys.stderr) == streams
    dbs = list(paths.traces_dir().glob("*.db"))
    assert len(dbs) == 1
    assert Trace.open(dbs[0]).meta["incomplete"] is True  # no false success
