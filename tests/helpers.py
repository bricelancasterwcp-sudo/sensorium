"""Test helpers: in-process recording against real sys.monitoring."""
import importlib.util
import os
import re
import subprocess
import sys
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
    that survives the run (e.g. `tracer._tls.window_depth` must be 0).
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
