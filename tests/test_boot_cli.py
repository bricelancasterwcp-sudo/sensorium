"""Booting a target under recording, run metadata, and the `run` command."""
import io
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from sensorium import paths
from sensorium.record import boot
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
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


# -- a thread that outlives the target ------------------------------------
def test_dropped_late_writes_reach_the_run_metadata(tmp_path):
    """The guard seals before finalization, so drops in that window land in
    the trace instead of being counted where nobody will ever see them."""
    w = TraceWriter(tmp_path / "t.db", batch=1)
    g = boot._LateWriteGuard(w)
    g.set_meta("incomplete", True)
    g.seal()                              # in-flight callbacks stop here
    assert g.add_event(1, 2, "CALL", None, 0, 1, None) == 0
    g.add_output(0, "stdout", "late")
    g.set_meta_final("late_writes", g.late_writes)
    g.set_meta_final("incomplete", False)
    g.close()
    m = Trace.open(tmp_path / "t.db").meta
    assert m["late_writes"] == 2 and m["incomplete"] is False


def test_recording_gaps_reports_both_kinds_of_loss():
    assert boot._recording_gaps([], 0) is None
    assert "still alive" in boot._recording_gaps(["w1"], 0)
    dropped = boot._recording_gaps([], 3)
    assert "3 trace write" in dropped and "dropped" in dropped
    both = boot._recording_gaps(["w1", "w2"], 3)
    assert "2 thread" in both and "3 trace write" in both


def test_late_writes_after_close_are_absorbed(tmp_path):
    """A write from a callback still in flight must not hit a closed db."""
    w = TraceWriter(tmp_path / "t.db", batch=1)     # every event flushes
    g = boot._LateWriteGuard(w)
    cid = g.intern_code("f.py", "f", 1)
    g.add_event(1, 2, "CALL", None, cid, 1, None)
    g.close()
    # What a monitoring callback still in flight goes on to write. Unguarded,
    # the first of these flushes and raises sqlite3.ProgrammingError from
    # inside the callback, killing the thread that was running traced code.
    assert g.add_event(2, 2, "CALL", None, cid, 2, None) == 0
    assert g.intern_code("f.py", "g", 2) == 0
    assert g.open_frame(None, 0, 0, 0, 2) == 0
    g.close_frame(0, 0, "return")
    g.add_output(0, "stdout", "late")
    g.write_fingerprint(2, "abc", 1)
    g.set_meta("incomplete", False)
    assert g.late_writes == 7
    t = Trace.open(tmp_path / "t.db")
    assert len(t.events()) == 1 and not t.output_chunks()


def test_daemon_thread_outliving_main_does_not_crash(sandbox):
    (sandbox / "prog.py").write_text(DAEMON)
    errors = []
    old_hook = threading.excepthook
    threading.excepthook = errors.append
    try:
        run_id, exit_status = boot.run_target(["prog.py"])
        for th in threading.enumerate():
            if th.name == "sensorium-daemon-test":
                th.join(10)
    finally:
        threading.excepthook = old_hook
    assert [a.exc_type.__name__ for a in errors] == []
    assert exit_status == 0
    assert (sandbox / "daemon-ran.txt").exists()   # it really did run late
    t = _trace_of(run_id)
    assert t.meta["incomplete"] is False
    quals = {t.code(e.code_id).qualname for e in t.events(kind="CALL")}
    assert "spin" in quals                         # the thread was recorded
    assert "worker" not in quals                  # recorded up to the close


def test_live_threads_at_teardown_are_reported(tmp_path):
    run_id, trace, r = record_script(tmp_path, DAEMON)
    assert r.returncode == 0
    assert "still alive" in r.stderr
    assert Trace.open(trace).meta["incomplete"] is False


def test_a_hostile_thread_name_does_not_crash_the_recorder(tmp_path):
    """A still-alive thread whose name's comparisons raise must not kill a
    program that finished cleanly, when the teardown sorts the live names."""
    run_id, trace, r = record_script(tmp_path, HOSTILE_THREAD_NAME)
    assert r.returncode == 0, r.stderr           # the program returned 0
    assert run_id is not None                    # the run was reported, not lost
    assert "main done" in r.stdout
    assert "still alive" in r.stderr             # the gap is still reported...
    assert "evil-worker" in r.stderr             # ...with the name normalised
    assert "Traceback" not in r.stderr


def test_a_hostile_sys_exit_code_does_not_crash_the_recorder(tmp_path):
    """sys.exit() with an object whose __class__ raises must not crash the
    recorder computing the exit status; it takes the interpreter's own answer
    for a non-int code (exit 1)."""
    run_id, trace, r = record_script(tmp_path, HOSTILE_EXIT_CODE)
    assert run_id is not None, r.stderr          # the run was reported, not lost
    assert "about to exit" in r.stdout
    assert r.returncode == 1                     # non-int code -> 1, as CPython
    assert Trace.open(trace).meta["exit_status"] == 1
    assert "_exit_status_of" not in r.stderr     # not a recorder traceback


# -- two runs in one process (what `refocus` will do) ----------------------
def test_run_target_twice_in_one_process(sandbox):
    (sandbox / "one.py").write_text(SPAWNS)
    (sandbox / "two.py").write_text(SPAWNS_TWICE)
    id1, st1 = boot.run_target(["one.py"])
    id2, st2 = boot.run_target(["two.py"], refocus_of=id1)
    assert (st1, st2) == (0, 0)
    assert boot._audit_installs == 1        # one hook ever, not one per run
    assert boot._audit_sink is None         # disarmed between runs
    assert len(_trace_of(id1).meta["children"]) == 1
    assert len(_trace_of(id2).meta["children"]) == 2
    assert _trace_of(id2).meta["refocus_of"] == id1
    assert _trace_of(id1).meta["incomplete"] is False


def test_run_target_restores_interpreter_state(sandbox):
    (sandbox / "prog.py").write_text(HELLO)
    before = (list(sys.argv), list(sys.path),
              sys.stdin, sys.stdout, sys.stderr)
    boot.run_target(["prog.py", "extra-arg"])
    assert list(sys.argv) == before[0]
    assert list(sys.path) == before[1]
    assert (sys.stdin, sys.stdout, sys.stderr) == before[2:]


def test_main_thread_ident_records_the_thread_that_ran_the_target(sandbox):
    """`run_target` records the identity of the thread that actually ran the
    target -- not the interpreter's global main thread. The recorded value is
    the thread serial the Tracer mints for its constructing thread, which is the
    calling thread, so invoked from a worker it names that worker: it equals the
    serial every event of the run carries, and the process main thread (which
    touched nothing) has no serial and cannot be it."""
    (sandbox / "prog.py").write_text("def main():\n    pass\nmain()\n")
    result = {}

    def worker():
        result["run_id"], result["exit_status"] = boot.run_target(["prog.py"])

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    assert result["exit_status"] == 0
    trace = _trace_of(result["run_id"])
    event_tids = {e.thread_id for e in trace.events()}
    assert len(event_tids) == 1                   # the whole run ran on one thread
    assert trace.meta["main_thread_ident"] == next(iter(event_tids))
    assert trace.main_thread_basis() == "recorded"


# -- target resolution ----------------------------------------------------
def test_module_target_runs(tmp_path):
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(
        "def main():\n    print('from module')\nmain()\n")
    r = run_cli(["run", "--", "-m", "mypkg"], cwd=tmp_path,
                sensorium_dir=tmp_path / "sdir")
    assert r.returncode == 0 and "from module" in r.stdout


def test_console_script_target_resolves(tmp_path):
    assert callable(boot.resolve_target(["pytest", "--version"]))


def test_console_script_target_runs_the_entry_point(sandbox, monkeypatch):
    """The console-script mode must actually RUN the resolved entry point with
    the given argv and capture its output -- not merely resolve to a callable.
    A no-op `run_script` (never setting argv, never calling the entry) passed
    the resolve-only test above, so the whole run path was unexercised."""
    ran = {}

    def entry():
        ran["argv"] = list(sys.argv)
        print("entry point ran")

    class FakeEP:
        def load(self):
            return entry

    def fake_entry_points(*, group=None, name=None):
        if group == "console_scripts" and name == "mytool":
            return [FakeEP()]
        return []

    monkeypatch.setattr(boot.importlib.metadata, "entry_points",
                        fake_entry_points)

    run_id, status = boot.run_target(["mytool", "--flag", "v"])
    assert status == 0
    assert ran["argv"] == ["mytool", "--flag", "v"]   # argv reached the entry
    out = "".join(d for _e, _s, d in _trace_of(run_id).output_chunks())
    assert "entry point ran" in out                    # its output was captured


def test_git_info_reports_sha_and_dirty_hash(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True,
                       capture_output=True)
    assert boot.git_info(tmp_path) == {"git_sha": None, "git_dirty_hash": None}
    git("init", "-q")
    (tmp_path / "a.txt").write_text("one")
    git("add", "a.txt")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "one")
    clean = boot.git_info(tmp_path)
    assert len(clean["git_sha"]) == 40 and len(clean["git_dirty_hash"]) == 16
    (tmp_path / "a.txt").write_text("two")
    dirty = boot.git_info(tmp_path)
    assert dirty["git_sha"] == clean["git_sha"]
    assert dirty["git_dirty_hash"] != clean["git_dirty_hash"]


def test_target_argv_is_visible_to_the_program(tmp_path):
    src = "import sys\nprint('ARGV', sys.argv[1:])\n"
    run_id, trace, r = record_script(tmp_path, src, argv=["a", "b"])
    assert "ARGV ['a', 'b']" in r.stdout
    assert Trace.open(trace).meta["argv"] == ["prog.py", "a", "b"]


def test_cli_refuses_a_python_that_predates_sys_monitoring(
        monkeypatch, capsys):
    """The recorder is PEP 669 and nothing else, so on 3.11 there is no
    degraded mode to fall back to -- only a refusal that names the version
    it needs and the one it got. An ImportError deep in the tracer would be
    the same fact delivered as a bug report."""
    from sensorium import cli

    monkeypatch.setattr(sys, "version_info", (3, 11, 9, "final", 0))
    assert cli.main(["runs"]) == 2

    err = capsys.readouterr().err
    assert "3.12+" in err
    assert sys.version.split()[0] in err        # the version it actually got


# -- contract: nothing the recorder STORES may be a live object. `_Tee.write`
# takes whatever the program passed to `sys.stdout.write`, which may be a
# `str` subclass: `if s:` ran its `__bool__`/`__len__` from inside the
# program's own call, and the instance was then held in the writer's buffer
# until the next flush and bound into sqlite from there.
class _HostileStr(str):
    def __len__(self):
        raise ValueError("INJECTED-len")

    def __bool__(self):
        raise ValueError("INJECTED-bool")


class _CountingSink:
    def __init__(self) -> None:
        self.wrote = []

    def write(self, s):
        self.wrote.append(str.__str__(s))
        return 4


class _RecordingWriter:
    last_event_id = 0

    def __init__(self) -> None:
        self.rows = []

    def add_output(self, after_event_id, stream, data) -> None:
        self.rows.append(data)


def test_tee_stores_an_exact_str_and_never_the_program_s_own_object():
    sink, writer = _CountingSink(), _RecordingWriter()
    tee = boot._Tee(sink, "stdout", writer)

    assert tee.write(_HostileStr("out\n")) == 4     # no dunder escaped
    assert sink.wrote == ["out\n"]                  # the real stream still got it
    assert writer.rows == ["out\n"]
    assert type(writer.rows[0]) is str


def test_tee_still_skips_an_empty_write():
    """The emptiness test survives normalisation: an empty write is not a
    row, or every `print()` would store a spurious blank."""
    sink, writer = _CountingSink(), _RecordingWriter()
    boot._Tee(sink, "stdout", writer).write("")
    assert writer.rows == []


def test_audit_records_exact_strs_not_the_program_s_own_objects():
    """`children` is stored in run metadata and lives until the finalizer.
    `str()` honours a `__str__` override and can hand back another subclass
    instance, so the list would hold live objects with live dunders."""
    class Live(str):
        def __str__(self):
            return Live("lie")
    out = boot._as_text(Live("real"))
    assert type(out) is str and out == "lie"
    assert type(boot._as_text(b"bytes")) is str


def test_audit_hook_absorbs_even_a_base_exception(monkeypatch):
    """The hook calls `isinstance`, `str()` and `__iter__` on the program's
    own objects, so a dunder may raise ANYTHING -- and an audit hook that
    raises breaks the operation being audited, which is the recorder killing
    what it observes. `except Exception` left that half open."""
    class Cloaked:
        @property
        def __class__(self):
            raise KeyboardInterrupt("not an Exception")

    children, threads, errors = [], [], []
    monkeypatch.setattr(boot, "_audit_sink", children)
    monkeypatch.setattr(boot, "_audit_threads", threads)
    monkeypatch.setattr(boot, "_audit_errors", errors)

    boot._audit("os.system", (Cloaked(),))     # must not propagate

    assert children == [], "a failed extraction must not record a bogus child"
    assert len(errors) == 1, "swallowed without a trace"


def test_stdin_proxy_does_not_compare_the_program_s_own_attribute_name():
    """`getattr(sys.stdin, name)` hands a `str` SUBCLASS straight through to
    `__getattr__`, so the proxy's two membership tests would run the
    program's `__eq__` -- inside the program's own call, where without the
    recorder no comparison happens at all."""
    class K(str):
        """Equal to its own characters, hostile to anything else -- so the
        interpreter's own attribute lookup succeeds (as it does without the
        recorder) and only the proxy's extra comparison raises."""
        def __eq__(self, other):
            if str.__eq__(self, other) is True:
                return True
            raise ValueError("INJECTED-attr-eq")

        def __hash__(self):
            return str.__hash__(self)

    plain = io.StringIO("payload")
    assert getattr(plain, K("readable"))() is True      # baseline: no raise

    proxy = boot._StdinProxy(io.StringIO("payload"))
    assert getattr(proxy, K("readable"))() is True      # must not raise either
    assert proxy.consumed is False                      # readable() is not a read

    assert getattr(proxy, K("read"))() == "payload"     # ...and marking still works
    assert proxy.consumed is True


def test_task_errors_meta_is_stamped_as_zero_on_a_clean_run(tmp_path):
    run_id, trace, r = record_script(tmp_path, "def main():\n    pass\nmain()\n")
    assert run_id, r.stderr
    from sensorium.store.reader import Trace
    assert Trace.open(trace).meta["task_errors"] == 0


# `worker()` binds a local (`y`) across a suspension. The original fixture
# only awaited and returned a literal, which emits no LINE deltas at all and
# would make `LINE count > 0` below prove nothing.
ASYNC_FOCUS_SCRIPT = """
import asyncio

def step(n):
    return n

async def worker():
    y = step(1)
    await asyncio.sleep(0)
    y = step(y + 1)
    return y

def main():
    return asyncio.run(worker())

if __name__ == "__main__":
    main()
"""


def test_run_with_focus_on_a_coroutine_records_lines_and_stamps_no_warning(tmp_path):
    run_id, trace, r = record_script(tmp_path, ASYNC_FOCUS_SCRIPT,
                                     extra=["--focus", "prog:worker"])
    assert run_id, r.stderr
    assert "matched only coroutine" not in r.stderr
    from sensorium.store.reader import Trace
    t = Trace.open(trace)
    assert "focus_unframed" not in t.meta
    assert t.counts().get("LINE", 0) > 0


def test_late_write_guard_classifies_every_public_writer_method():
    """_LateWriteGuard forwards writer methods BY HAND. When add_task was added
    to TraceWriter without a delegate, `sensorium run` killed every asyncio
    target with AttributeError (aec8d1e). This pins the classification: a new
    public TraceWriter method must be placed here on purpose -- delegated
    (write path, counted after seal) or listed as a deliberate non-delegate."""
    from sensorium.store.writer import TraceWriter
    from sensorium.record.boot import _LateWriteGuard
    public = {n for n, v in vars(TraceWriter).items()
              if callable(v) and not n.startswith("_")}
    delegated = {"intern_code", "add_event", "add_task", "open_frame",
                 "close_frame", "add_output", "set_meta", "write_fingerprint",
                 "write_task_fingerprint"}
    deliberate = {"interned_files",   # read passthrough, documented in the guard
                  "close",            # guard has its own close
                  "flush"}            # no caller on a guarded writer
    assert public == delegated | deliberate, (
        f"unclassified TraceWriter method(s): {sorted(public - delegated - deliberate)}")
    for name in delegated:
        assert callable(getattr(_LateWriteGuard, name)), name
