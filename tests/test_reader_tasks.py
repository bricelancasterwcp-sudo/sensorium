"""The reader's view of task fingerprints and of the fingerprint basis."""
from collections import Counter
from pathlib import Path

from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter

OLD3 = Path(__file__).parent / "fixtures" / "format3_async.db"


def _build(tmp_path, basis):
    """A hand-built trace: main thread runs f, then task 1 (named 'w') runs
    g twice, task 2 (unnamed) runs g once; writer-level, no recorder."""
    w = TraceWriter(tmp_path / "t.db", batch=4)
    if basis is not None:
        w.set_meta("fingerprint_basis", basis)
    f = w.intern_code("/p/prog.py", "f", 1)
    g = w.intern_code("/p/prog.py", "g", 5)
    w.add_task(1, "w", 1)
    w.add_task(2, None, 1)
    w.add_event(0, 1, "CALL", None, f, 1, {"args": {}})
    w.add_event(1, 1, "CALL", None, g, 5, {"args": {}}, task_id=1)
    w.add_event(2, 1, "RETURN", None, g, None, {"value": None}, task_id=1)
    w.add_event(3, 1, "YIELD", None, g, 6, {"awaiting": "Future"}, task_id=1)
    w.add_event(4, 1, "CALL", None, g, 5, {"args": {}}, task_id=2)
    w.add_event(5, 1, "RETURN", None, g, None, {"value": None}, task_id=2)
    w.add_event(6, 1, "RETURN", None, f, None, {"value": None})
    w.write_fingerprint(1, "aa" * 16, 2)
    w.write_task_fingerprint(1, "bb" * 16, 2)
    w.write_task_fingerprint(2, "cc" * 16, 2)
    w.close()
    return Trace.open(tmp_path / "t.db")


def test_basis_defaults_to_per_thread_when_the_marker_is_absent(tmp_path):
    t = _build(tmp_path, None)
    assert t.fingerprint_basis == "per-thread"
    assert Trace.open(OLD3).fingerprint_basis == "per-thread"


def test_basis_reads_the_marker(tmp_path):
    assert _build(tmp_path, "per-task").fingerprint_basis == "per-task"


def test_task_fingerprints_carry_the_name_from_the_tasks_table(tmp_path):
    t = _build(tmp_path, "per-task")
    assert t.task_fingerprints() == {1: ("w", "bb" * 16, 2),
                                     2: (None, "cc" * 16, 2)}
    assert Trace.open(OLD3).task_fingerprints() == {}


def test_task_shapes_is_a_multiset_of_name_and_hash(tmp_path):
    t = _build(tmp_path, "per-task")
    assert t.task_shapes() == Counter({("w", "bb" * 16): 1,
                                       (None, "cc" * 16): 1})


def test_task_stream_is_the_tasks_causal_events_in_order(tmp_path):
    t = _build(tmp_path, "per-task")
    assert [s[:3] for s in t.task_stream(1)] == [
        ("/p/prog.py", "g", "CALL"), ("/p/prog.py", "g", "RETURN")]
    assert [s[3] for s in t.task_stream(1)] == [2, 3]      # event ids
    assert t.task_stream(99) == []


def test_causal_stream_narrows_to_no_task_events_under_the_per_task_basis(
        tmp_path):
    t = _build(tmp_path, "per-task")
    assert [s[:3] for s in t.causal_stream(1)] == [
        ("/p/prog.py", "f", "CALL"), ("/p/prog.py", "f", "RETURN")]


def test_causal_stream_keeps_every_event_under_the_per_thread_basis(tmp_path):
    t = _build(tmp_path, None)
    assert [s[1:3] for s in t.causal_stream(1)] == [
        ("f", "CALL"), ("g", "CALL"), ("g", "RETURN"), ("g", "CALL"),
        ("g", "RETURN"), ("f", "RETURN")]
