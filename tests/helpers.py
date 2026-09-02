"""Test helpers: in-process recording against real sys.monitoring."""
import importlib.util
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from sensorium.record.tracer import FocusSpec, Tracer
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter


def load_module(path: Path):
    name = f"{path.stem}_{abs(hash(str(path))) % 10**6}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def record_inproc_full(tmp_path, source, focus=(), window=None, entry="main"):
    """Record `source` and return (Trace, exc | None, Tracer).

    The Tracer is handed back so tests can assert on recorder-internal state
    that survives the run (e.g. `tracer._tls.live` must be empty).
    """
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)   # tests pass tmp_path / "a"
    prog = tmp_path / "prog.py"
    prog.write_text(source)
    mod = load_module(prog)          # import BEFORE install: defs not traced
    writer = TraceWriter(tmp_path / "trace.db", batch=8)
    tracer = Tracer(writer, root=tmp_path, focus=FocusSpec(list(focus)),
                    window=window)
    err = None
    tracer.install()
    try:
        getattr(mod, entry)()
    except Exception as e:
        err = e
    finally:
        tracer.uninstall()
        writer.close()
    return Trace.open(tmp_path / "trace.db"), err, tracer


def record_inproc(tmp_path, source, focus=(), window=None, entry="main"):
    trace, err, _ = record_inproc_full(tmp_path, source, focus, window, entry)
    return trace, err


@contextmanager
def installed_tracer(tmp_path):
    """An installed Tracer with no recorded program.

    For asserting on recorder state that only exists *while* recording is
    live -- the retention table is cleared by `uninstall`, so a test that
    wants to see it must hold the tracer open itself. Exception bookkeeping
    runs for every exception in the process, traced or not, so the test can
    raise its own.
    """
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    writer = TraceWriter(tmp_path / "trace.db", batch=8)
    tracer = Tracer(writer, root=tmp_path, focus=FocusSpec([]))
    tracer.install()
    try:
        yield tracer
    finally:
        tracer.uninstall()
        writer.close()


def run_cli(args, cwd, sensorium_dir, stdin_text=None):
    """Run the real CLI in a subprocess, against a disposable trace store."""
    env = dict(os.environ, SENSORIUM_DIR=str(sensorium_dir))
    return subprocess.run(
        [sys.executable, "-m", "sensorium", *args],
        cwd=cwd, env=env, capture_output=True, text=True, input=stdin_text)


def record_script(tmp_path, source, extra=(), name="prog.py", argv=(),
                  stdin_text=None):
    """Record `source` via `sensorium run`; returns (run_id, trace, result)."""
    tmp_path = Path(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)   # tests pass tmp_path / "b"
    (tmp_path / name).write_text(source)
    sdir = tmp_path / "sdir"
    r = run_cli(["run", *extra, "--", name, *argv], cwd=tmp_path,
                sensorium_dir=sdir, stdin_text=stdin_text)
    m = re.search(r"^run: (\S+)$", r.stdout, re.M)
    run_id = m.group(1) if m else None
    trace = sdir / "traces" / f"{run_id}.db" if run_id else None
    return run_id, trace, r


# The newest format in which a trace may legitimately LACK a key format 4
# requires. A hand-built legacy shape -- no `cwd`, no `main_thread_ident`,
# no `fingerprint_basis` -- is not a format-4 trace, and a test must not
# make it claim to be one: format 4 refuses exactly that combination at
# open, and filling the key in would delete the very absence under test.
# Stamping the older format is how such a fixture says "this is what an
# older recorder left behind" without weakening the refusal.
LEGACY_FORMAT = 3

# Neutral values for every key a finalized format-4 trace must carry. A
# hand-built trace that sets `incomplete` False claims it finalized, and
# format 4 refuses that claim without these keys (db.REQUIRED_META).
FINAL_META = {
    "run_id": "synthetic", "argv": ["prog.py"], "cwd": "/tmp",
    "env_hash": "0" * 16, "start_ts": 0.0, "end_ts": 0.0, "exit_status": 0,
    "main_thread_ident": 1, "fingerprint_basis": "per-task",
    "truncated_count": 0, "source_hashes": {},
    "recorder": "sensorium (synthetic test trace)", "lang": "python",
    "capabilities": {"line": True, "locals": True, "return_value": True,
                     "tasks": True, "threads": True, "children": True,
                     "stdin": True, "output": True, "object_identity": True,
                     "refocus": True},
    "threads_started": 0, "live_threads": [], "children": [],
    "spawn_syscalls": 0, "audit_errors": 0, "stdin_consumed": False,
}


_WITNESS = {"threads": ("threads_started", "live_threads"),
            "children": ("children", "spawn_syscalls", "audit_errors"),
            "stdin": ("stdin_consumed",)}


def finalize_synthetic(w, **overrides) -> None:
    """Mark a hand-built trace finalized the way the recorder does: every
    required key present (existing values kept, `overrides` win), then
    `incomplete` False. Use in place of `w.set_meta("incomplete", False)`.

    Witness keys are written only for the capabilities the final dict
    declares TRUE -- a trace that declares `threads: false` must be able to
    have no `threads_started` at all, which is what the readers then print
    as a declaration. Pass a witness key explicitly to force it."""
    present = {k for (k,) in w._conn.execute("SELECT key FROM meta")}
    final = {**FINAL_META, **overrides}
    caps = final["capabilities"]
    skip = {k for cap, keys in _WITNESS.items() if not caps.get(cap)
            for k in keys if k not in overrides}
    for k, v in final.items():
        if k in skip:
            continue
        if k in overrides or k not in present:
            w.set_meta(k, v)
    w.set_meta("incomplete", False)
