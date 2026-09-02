"""Capability declarations, read one way by every command."""
from sensorium import paths
from sensorium.query.caps import require, witness_gap
from sensorium.store.reader import Trace
from tests.helpers import finalize_synthetic
from tests.programs import synthetic

CAPS_NONE = {"line": False, "locals": False, "threads": False, "children": False,
             "stdin": False, "output": False, "object_identity": False}


def _rust(tmp_path, monkeypatch, **caps):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={**CAPS_NONE, **caps})
    w.close()
    return Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")


def test_require_passes_a_declared_capability_and_a_pre_format4_python_trace(
        tmp_path, monkeypatch):
    t = _rust(tmp_path, monkeypatch, line=True)
    assert require(t, "line", "flow") is None
    from pathlib import Path
    old = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    assert require(old, "object_identity", "flow --object") is None


def test_require_refuses_an_undeclared_capability_naming_the_recorder(
        tmp_path, monkeypatch):
    t = _rust(tmp_path, monkeypatch)
    msg = require(t, "line", "flow")
    assert msg and "sensorium-rt 0.0" in msg and "capabilities.line: false" in msg
    assert "nothing was checked" in msg


def test_witness_gap_distinguishes_predates_from_declared(tmp_path, monkeypatch):
    t = _rust(tmp_path, monkeypatch)
    declared = witness_gap(t, "threads", "thread")
    assert "declares threads not witnessed" in declared and "predates" not in declared
    from pathlib import Path
    old = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    assert "predates" in witness_gap(old, "threads", "thread")
