"""What the recorder does at the edges of a run: threads that outlive the
target, two runs in one process, resolving what to record, and the contract
that nothing the recorder STORES may be a live object.

The other half of `test_boot_cli`, split at that file's own
`# -- a thread that outlives the target` banner on 2026-09-08 to bring both
halves under the 800-line ceiling. The program sources, the `sandbox` fixture
and `_trace_of` are the first file's -- imported, never copied, so one change
to what a shape records still lands in one place.
"""
import io
import subprocess
import sys
import threading

from sensorium.record import boot
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import FINAL_META, record_script, run_cli
from tests.test_boot_cli import (DAEMON, HELLO, HOSTILE_EXIT_CODE,
                                 HOSTILE_THREAD_NAME, SPAWNS, SPAWNS_TWICE,
                                 _trace_of)
# `sandbox` is a `@pytest.fixture` (`test_boot_cli.py:156`): importing it is
# what registers it in THIS module, and it is then named only as a test
# parameter -- so this one line, and only this one, is an unused import.
from tests.test_boot_cli import sandbox  # noqa: F401


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
    # Through the guard, not `finalize_synthetic`: after `seal()` the plain
    # `set_meta` path is absorbed, and a format-4 trace that says it
    # finalized must carry every required key (db.REQUIRED_META).
    for k, v in FINAL_META.items():
        g.set_meta_final(k, v)
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
                 "write_task_fingerprint", "write_task_fingerprints"}
    deliberate = {"interned_files",   # read passthrough, documented in the guard
                  "close",            # guard has its own close
                  "flush"}            # no caller on a guarded writer
    assert public == delegated | deliberate, (
        f"unclassified TraceWriter method(s): {sorted(public - delegated - deliberate)}")
    for name in delegated:
        assert callable(getattr(_LateWriteGuard, name)), name


def test_console_script_return_value_is_the_exit_status(sandbox, monkeypatch):
    """pip's console-script wrapper is `sys.exit(main())`, so a `main` that
    returns 2 exits 2. The recorder must report THAT status -- `runs`, `info`
    and refocus's "the two runs ended differently" all read it -- not the 0
    of a function that merely returned. Found by sweeping assay under the
    recorder: `assay cover` refusals (main -> 2) were recorded as exit 0 while
    `-m assay cover` recorded 2."""
    def entry():
        return 2

    class FakeEP:
        def load(self):
            return entry

    def fake_entry_points(*, group=None, name=None):
        if group == "console_scripts" and name == "mytool":
            return [FakeEP()]
        return []

    monkeypatch.setattr(boot.importlib.metadata, "entry_points",
                        fake_entry_points)
    run_id, status = boot.run_target(["mytool"])
    assert status == 2
    assert _trace_of(run_id).meta["exit_status"] == 2
