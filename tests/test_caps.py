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
    declared = witness_gap(t, "threads", "thread", "UNUSED-LEGACY")
    assert "declares threads not witnessed" in declared and "predates" not in declared
    from pathlib import Path
    old = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    # `declares() is None` returns the caller's own legacy sentence
    # unchanged -- byte for byte, not reworded through this module.
    legacy = "predates the recorder's thread bookkeeping (site-specific)"
    assert witness_gap(old, "threads", "thread", legacy) == legacy


def test_witness_gap_names_a_declared_but_still_missing_witness_key(
        tmp_path, monkeypatch):
    """Today's Python recorder writes `capabilities` (all True) at run
    start (`boot.install()`) and `threads_started` only at the finalize
    pass (`set_meta_final`) -- every still-recording or killed-mid-record
    trace declares threads True with the key still absent. That state must
    never read as "predates" (the trace does not predate the declaration --
    it just hasn't finished), and must never assert
    `capabilities.threads: false`, which the trace's own dict denies."""
    from sensorium.record.boot import CAPABILITIES
    w = synthetic(tmp_path, monkeypatch)
    w.set_meta("recorder", "sensorium 9.9.9")
    w.set_meta("capabilities", dict(CAPABILITIES))
    w.close()
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    assert t.declares("threads") is True
    gap = witness_gap(t, "threads", "thread", "UNUSED-LEGACY")
    assert "declares threads witnessed" in gap
    assert "predates" not in gap
    assert "capabilities.threads: false" not in gap
    assert "recording did not finish, or the record was removed" in gap
    assert "absence of the record is not a record of absence" in gap
