"""The traces, the fake driver and the store reads every Rust-`refocus`
test is written against.

Split out when `tests/test_refocus_rust.py` and the licence tests that use
the same fixtures stopped fitting in one file -- the seam `tests/
refocus_programs.py` already follows for the Python side. Nothing here
asserts anything; the two suites that import it do.

The fake driver WRITES THE PAIR ITSELF, exactly as the real one does: a
second trace carrying `refocus_of` and a `start_ts` after the launch. That
is what makes the pair lookup a real lookup in these tests and not a stub.
"""
import hashlib
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from sensorium import paths
from sensorium.query import refocus_cmd, refocus_rust
from sensorium.store import db
from tests.rust_traces import libtest_trace, rerunnable_trace

ORIG = "20260101-000000-rust01"
PAIR = "20260101-000100-pair01"
STALE = "20250101-000000-stale1"
# A trace written by a CONCURRENT refocus of a different original: linked,
# and recent, so only the identity of what it is linked TO excludes it.
OTHER = "20260101-000050-other1"
OTHER_ORIGINAL = "20250101-000000-orig02"
# The re-run's OWN child process (design 2026-09-07 §3, ruling R2): a test
# that runs the driver spawns an instrumented child, so the invocation
# stamps `refocus_of` on TWO traces. The ids sort after `PAIR`, because
# `find_pair` returns name order and a test that pins an order needs one.
CHILD = "20260101-000200-child1"
SECOND = "20260101-000300-second1"
GRANDCHILD = "20260101-000400-grand01"
#: The pids those traces record. Distinct values, none of them 0 and none
#: of them equal to another's, so a test that passes can only be reading
#: the pid it was given.
PARENT_PID = 4100
CHILD_PID = 4101
GRANDCHILD_PID = 4102
SECOND_PID = 4200


def args(run, *focus, window=None):
    return SimpleNamespace(run=run, focus=list(focus), window=window)


def workspace(tmp_path):
    """A directory that exists, with one source file in it -- the shape a
    real workspace root has, so `_source_state` has something to re-hash."""
    root = tmp_path / "ws"
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "lib.rs").write_text("fn compute() -> u8 { 5 }\n")
    return root


def rust_digest(root: Path, rel: str) -> dict:
    """`source_hashes` as the RUST converter writes it: a workspace-relative
    key and the FULL 64-character sha256, which is the width Python's own
    recorder does not use."""
    return {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()}


def original(tmp_path, monkeypatch, **meta):
    """The trace being refocused: rerunnable, in a workspace that exists."""
    root = workspace(tmp_path)
    meta.setdefault("workspace_root", str(root))
    meta.setdefault("cwd", str(root))
    meta.setdefault("source_hashes", rust_digest(root, "src/lib.rs"))
    return rerunnable_trace(tmp_path, monkeypatch, **meta), root


def libtest_original(tmp_path, monkeypatch, *, program_threads=0,
                     silent_threads=0, harness_marked=True, task_rows=True,
                     **meta):
    """`original()`'s workspace, recorded the way `cargo test` records it.

    The same wrapper `original` is -- a workspace that exists, so the
    source re-hash has something to read -- around the trace that carries
    libtest's per-test thread. Pass it to `_drive(program=...)` through
    `functools.partial` to fix the thread counts on BOTH sides.
    """
    root = workspace(tmp_path)
    meta.setdefault("workspace_root", str(root))
    meta.setdefault("cwd", str(root))
    meta.setdefault("source_hashes", rust_digest(root, "src/lib.rs"))
    return libtest_trace(tmp_path, monkeypatch,
                         program_threads=program_threads,
                         silent_threads=silent_threads,
                         harness_marked=harness_marked,
                         task_rows=task_rows, **meta), root


def refuse(capsys, run, *focus, window=None):
    """Run the command and return (exit code, stderr)."""
    code = refocus_cmd.run(args(run, *focus, window=window))
    return code, capsys.readouterr().err


class FakeDriver:
    """Stands in for `cargo-sensorium`: records how it was called, and
    optionally writes the traces the real driver would have written."""

    def __init__(self, tmp_path, monkeypatch, *, pairs=(), returncode=0,
                 stdout="run: x  pid: 1  exit: 0\n", build=None,
                 pair_meta=None):
        self.tmp_path, self.monkeypatch = tmp_path, monkeypatch
        self.pairs, self.returncode, self.stdout = pairs, returncode, stdout
        # Extra meta per written trace, keyed by run id: `pid`/`ppid` for the
        # child-run rule, which needs the traces to differ in something other
        # than their names.
        self.pair_meta = dict(pair_meta or {})
        # What the re-run "records". The default writes the same program the
        # original ran, which is the MATCH case; a test that wants DIVERGED
        # passes a builder for a different one.
        self.build = build or original
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        for rid, link in self.pairs:
            self.build(self.tmp_path, self.monkeypatch, run_id=rid,
                       refocus_of=link, start_ts=time.time(),
                       **self.pair_meta.get(rid, {}))
        return subprocess.CompletedProcess(argv, self.returncode,
                                           stdout=self.stdout)


def _never(*a, **kw):                       # pragma: no cover - a tripwire
    raise AssertionError("the driver was launched by a refused call")


def _drop_meta(tmp_path, run_id, key):
    conn = db.open_trace(paths.traces_dir() / f"{run_id}.db")
    try:
        conn.execute("DELETE FROM meta WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()


def _read_meta(run_id, key, default=None):
    conn = db.open_trace(paths.traces_dir() / f"{run_id}.db")
    try:
        return db.get_meta(conn, key, default)
    finally:
        conn.close()


def _drive(tmp_path, monkeypatch, *, pairs=(), returncode=0, focus=("compute",),
           build=None, program=None, pair_meta=None, **meta):
    """Run the whole command against a fake driver; return (code, out, fake).

    `program` builds BOTH sides -- one program other than the default,
    recorded twice, which is what a MATCH is; `build` overrides the RERUN's
    builder alone, which is how a test asks for a divergence. Neither given
    is `original` on both, exactly as before.
    """
    make = program or original
    run, root = make(tmp_path, monkeypatch, **meta)
    fake = FakeDriver(tmp_path, monkeypatch, pairs=pairs, build=build or make,
                      returncode=returncode, pair_meta=pair_meta)
    monkeypatch.setenv("SENSORIUM_CARGO_SENSORIUM", "/d/cargo-sensorium")
    monkeypatch.setattr(refocus_rust.subprocess, "run", fake)
    code = refocus_cmd.run(args(run, *focus))
    return run, root, code, fake


