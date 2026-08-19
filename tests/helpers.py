"""Test helpers: in-process recording against real sys.monitoring."""
import importlib.util
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
