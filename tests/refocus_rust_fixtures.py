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
from tests.rust_traces import rerunnable_trace

ORIG = "20260101-000000-rust01"
PAIR = "20260101-000100-pair01"
STALE = "20250101-000000-stale1"
# A trace written by a CONCURRENT refocus of a different original: linked,
# and recent, so only the identity of what it is linked TO excludes it.
OTHER = "20260101-000050-other1"
OTHER_ORIGINAL = "20250101-000000-orig02"


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


def refuse(capsys, run, *focus, window=None):
    """Run the command and return (exit code, stderr)."""
    code = refocus_cmd.run(args(run, *focus, window=window))
    return code, capsys.readouterr().err


class FakeDriver:
    """Stands in for `cargo-sensorium`: records how it was called, and
    optionally writes the traces the real driver would have written."""

    def __init__(self, tmp_path, monkeypatch, *, pairs=(), returncode=0,
                 stdout="run: x  pid: 1  exit: 0\n", build=None):
        self.tmp_path, self.monkeypatch = tmp_path, monkeypatch
        self.pairs, self.returncode, self.stdout = pairs, returncode, stdout
        # What the re-run "records". The default writes the same program the
        # original ran, which is the MATCH case; a test that wants DIVERGED
        # passes a builder for a different one.
        self.build = build or original
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        for rid, link in self.pairs:
            self.build(self.tmp_path, self.monkeypatch, run_id=rid,
                       refocus_of=link, start_ts=time.time())
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
           build=None, **meta):
    """Run the whole command against a fake driver; return (code, out, fake)."""
    run, root = original(tmp_path, monkeypatch, **meta)
    fake = FakeDriver(tmp_path, monkeypatch, pairs=pairs, build=build,
                      returncode=returncode)
    monkeypatch.setenv("SENSORIUM_CARGO_SENSORIUM", "/d/cargo-sensorium")
    monkeypatch.setattr(refocus_rust.subprocess, "run", fake)
    code = refocus_cmd.run(args(run, *focus))
    return run, root, code, fake


