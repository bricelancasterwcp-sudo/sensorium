"""Format 4: the Python recorder declares itself, and the reader reads the
declaration instead of inferring age from absent keys."""
from sensorium.record import boot
from sensorium.store.reader import Trace
from tests.helpers import finalize_synthetic, record_script
from tests.programs import synthetic

PROG = "def main():\n    return 1\n\nif __name__ == '__main__':\n    main()\n"


def test_recorder_writes_recorder_lang_and_full_capabilities(tmp_path):
    run_id, trace, r = record_script(tmp_path, PROG)
    assert run_id, r.stderr
    m = Trace.open(trace).meta
    assert m["lang"] == "python"
    assert m["recorder"].startswith("sensorium ")
    assert m["capabilities"] == boot.CAPABILITIES
    assert all(m["capabilities"].values())
    assert m["trace_format"] == 4
    t = Trace.open(trace)
    assert t.lang == "python" and t.declares("threads") is True
    assert t.dropped_writes() == 0


def test_format3_fixture_reads_as_python_full_but_declares_nothing():
    from pathlib import Path
    t = Trace.open(Path(__file__).parent / "fixtures" / "format3_async.db")
    assert t.lang == "python"
    assert t.recorder.startswith("sensorium <=0.4.0")
    assert t.capabilities == boot.CAPABILITIES
    assert t.declares("threads") is None


def test_declares_false_reads_as_false(tmp_path, monkeypatch):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"threads": False, "children": False,
                                     "stdin": False})
    w.close()
    from sensorium import paths
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    assert t.lang == "rust" and t.declares("threads") is False
    assert t.declares("line") is False        # absent from the dict = not declared


def test_dropped_writes_reads_rust_records_dropped(tmp_path, monkeypatch):
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={}, records_dropped={"1": 0, "2": 3, "3": None})
    w.close()
    from sensorium import paths
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    assert t.dropped_writes() == 3
