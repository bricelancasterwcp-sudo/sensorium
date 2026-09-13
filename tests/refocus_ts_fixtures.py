"""The traces, the fake driver and the store reads every TypeScript-
`refocus` test is written against.

`tests/refocus_rust_fixtures.py`'s shape for the third recorder, and split
out for its reason: the branch's own suite and the suites that borrow its
pairs (the licence tests, later in this slice) must describe ONE recording,
not two. Nothing here asserts anything; the suites that import it do.

The fake driver WRITES THE PAIR ITSELF, exactly as `sensorium ts run
--refocus-of` does: a second trace carrying `refocus_of` and a `start_ts`
after the launch. That is what makes the pair lookup a real lookup in these
tests and not a stub -- and what lets a test ask for a SIBLING (another
container of the same invocation, running another test file) by adding one
entry to a list.

The environments are two SLOTS of one pool, because that is what a re-run
of a vitest suite gets: the recorder's own `SENSORIUM_SPOOL` is fresh by
construction and `VITEST_POOL_ID` is whichever worker slot was free. A
fixture whose two sides carried identical environments would let a licence
that compares neither of those pass every test in the suite.
"""
import hashlib
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from sensorium import paths
from sensorium.query import refocus_cmd, refocus_typescript
from sensorium.store import db
from tests.ts_traces import call, frame, ret, task, ts_trace

ORIG = "20260101-000000-ts0001"
PAIR = "20260101-000100-pair01"
#: Another container of the re-run's OWN invocation: linked, recent, and
#: running a DIFFERENT test file, which is the only thing that keeps it out
#: of the pair (design 2026-09-13 section 2.4).
SIBLING = "20260101-000200-sibl01"
STALE = "20250101-000000-stale1"
#: A trace written by a CONCURRENT refocus of a different original: linked,
#: and recent, so only the identity of what it is linked TO excludes it.
OTHER = "20260101-000050-other1"
OTHER_ORIGINAL = "20250101-000000-orig02"

#: The container environment the ORIGINAL recorded. `SENSORIUM_*` is the
#: recorder's own (`is_recorder_key`), `VITEST_*` is the pool's slot
#: bookkeeping (harness set 1), and `HOME`/`PATH` are the world -- one of
#: each, so a test that changes one can only be reading the rule it names.
ORIG_ENV = {"SENSORIUM_TIER": "call", "SENSORIUM_SPOOL": "/s/1",
            "VITEST_POOL_ID": "1", "VITEST_WORKER_ID": "1",
            "HOME": "/h", "PATH": "/p"}
#: ...and what the re-run's container recorded: a fresh spool (the recorder
#: mints one per invocation) and another pool slot (the harness takes
#: whichever is free). Nothing about the world moved.
PAIR_ENV = {**ORIG_ENV, "SENSORIUM_SPOOL": "/s/2", "VITEST_POOL_ID": "2"}


def args(run, *focus, window=None):
    return SimpleNamespace(run=run, focus=list(focus), window=window)


def project(tmp_path):
    """A project root that exists, with the one file the trace's code
    objects name -- the shape `harness_cwd` and `root` point at, so
    `_source_state` has something to re-hash."""
    root = Path(tmp_path) / "app"
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "config.ts").write_text(
        "export function compute(): number {\n  return 5;\n}\n")
    return root


def ts_digest(root: Path, rel: str) -> dict:
    """`source_hashes` as the TYPESCRIPT converter writes it: an ABSOLUTE
    key (`build.py`'s `_on_file`) and the full 64-character sha256, so the
    digests re-hash from any working directory at all."""
    path = Path(root) / rel
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()}


def _one_call(tmp_path, monkeypatch, qualname, **meta):
    """One container, one test, one traced call -- as DATA."""
    root = project(tmp_path)
    src = str(root / "src" / "config.ts")
    meta.setdefault("harness_cwd", str(root))
    meta.setdefault("root", str(root))
    meta.setdefault("cwd", str(root))
    meta.setdefault("source_hashes", ts_digest(root, "src/config.ts"))
    meta.setdefault("env", dict(ORIG_ENV))
    # The invocation's own exit, waited for by the driver, and the
    # container's self-report -- the two R9 compares. Both sides of a pair
    # get these values, so a test that sees them differ is reading a
    # difference some other fixture put there.
    meta.setdefault("harness_exit",
                    {"status": 0, "signal": None, "basis": "waited"})
    meta.setdefault("exit_self_reported", {"code": None, "signal": "SIGTERM"})
    run_id = meta.pop("run_id", ORIG)
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[src, qualname, 1]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 1, task=1), ret(2000, 1, 1, task=1)],
        tasks=[task(1, "config > reads")],
        run_id=run_id, **meta), root


def original(tmp_path, monkeypatch, **meta):
    """The trace being refocused: re-runnable, in a project that exists."""
    return _one_call(tmp_path, monkeypatch, "compute", **meta)


def other_program(tmp_path, monkeypatch, **meta):
    """A recording of a DIFFERENT program -- another causal stream, so a
    pair built with it diverges on shape rather than on anything in the
    world. `build=` on the fake driver."""
    return _one_call(tmp_path, monkeypatch, "other", **meta)


def two_test_files(tmp_path, monkeypatch, *, second="src/b.test.ts", **meta):
    """A REUSED WORKER: one container, two tests, each rooted in its own
    file (ruling P3). `second` names the file the second test roots in --
    `src/helpers.ts` is the bound, a container whose second test's callbacks
    all root in a non-test helper.
    """
    root = project(tmp_path)
    first = str(root / "src" / "a.test.ts")
    other = str(root / second)
    meta.setdefault("harness_cwd", str(root))
    meta.setdefault("root", str(root))
    meta.setdefault("cwd", str(root))
    meta.setdefault("source_hashes", ts_digest(root, "src/config.ts"))
    meta.setdefault("env", dict(ORIG_ENV))
    meta.setdefault("test_file", "src/a.test.ts")
    meta.setdefault("tests_seen", 2)
    run_id = meta.pop("run_id", ORIG)
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[first, "asserts", 1], [other, "asserts", 1]],
        frames=[frame(1, 1, 2), frame(2, 3, 4)],
        events=[call(1000, 1, 1, task=1), ret(1100, 1, 1, task=1),
                call(2000, 2, 1, task=2), ret(2100, 2, 2, task=2)],
        tasks=[task(1, "a > asserts"), task(2, "b > asserts")],
        run_id=run_id, **meta), root


def refuse(capsys, run, *focus, window=None):
    """Run the command and return (exit code, stderr)."""
    code = refocus_cmd.run(args(run, *focus, window=window))
    return code, capsys.readouterr().err


class FakeDriver:
    """Stands in for `python -m sensorium ts run`: records how it was
    called, and writes the traces that invocation would have written.

    `pairs` is [(run id, meta overrides)]. Every entry is linked to `ORIG`
    and started NOW unless its overrides say otherwise, which is what makes
    "a stale link", "a link to another original" and "a sibling running
    another test file" one keyword each.
    """

    def __init__(self, tmp_path, monkeypatch, *, pairs=(), returncode=0,
                 build=None):
        self.tmp_path, self.monkeypatch = tmp_path, monkeypatch
        self.pairs, self.returncode = list(pairs), returncode
        # What the re-run "records". The default writes the same program the
        # original ran, which is the MATCH case; a test that wants DIVERGED
        # passes a builder for a different one.
        self.build = build or original
        self.calls = []

    def __call__(self, argv, **kw):
        self.calls.append((list(argv), kw))
        for rid, overrides in self.pairs:
            self.build(self.tmp_path, self.monkeypatch,
                       **{"run_id": rid, "refocus_of": ORIG,
                          "start_ts": time.time(), "env": dict(PAIR_ENV),
                          **overrides})
        # No `stdout=`: this branch captures nothing, so a CompletedProcess
        # carrying output would describe a call this code never makes.
        return subprocess.CompletedProcess(argv, self.returncode)


def _never(*a, **kw):                       # pragma: no cover - a tripwire
    raise AssertionError("the harness was launched by a refused call")


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


def _drive(tmp_path, monkeypatch, *, pairs=(), returncode=0,
           focus=("compute",), build=None, program=None, **meta):
    """Run the whole command against a fake driver; return
    (run id, root, exit code, fake).

    `program` builds BOTH sides -- one program other than the default,
    recorded twice, which is what a MATCH is; `build` overrides the RERUN's
    builder alone, which is how a test asks for a divergence.
    """
    make = program or original
    run, root = make(tmp_path, monkeypatch, **meta)
    fake = FakeDriver(tmp_path, monkeypatch, pairs=pairs,
                      build=build or make, returncode=returncode)
    monkeypatch.setattr(refocus_typescript.subprocess, "run", fake)
    code = refocus_cmd.run(args(run, *focus))
    return run, root, code, fake
