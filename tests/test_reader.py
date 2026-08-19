from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter


def _fixture(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p)
    main = w.intern_code("/x/prog.py", "main", 1)
    add = w.intern_code("/x/prog.py", "add", 5)
    e1 = w.add_event(10, 7, "CALL", None, main, 1, {"args": {}})
    f1 = w.open_frame(None, main, e1, 0, 7)
    e2 = w.add_event(20, 7, "CALL", None, add, 5,
                     {"args": {"a": {"k": "num", "v": 2}}})
    f2 = w.open_frame(f1, add, e2, 1, 7)
    e3 = w.add_event(30, 7, "RETURN", f2, add, None,
                     {"value": {"k": "num", "v": 5}})
    w.close_frame(f2, e3, "return")
    e4 = w.add_event(40, 7, "RETURN", f1, main, None,
                     {"value": {"k": "none"}})
    w.close_frame(f1, e4, "return")
    w.set_meta("run_id", "r1")
    w.write_fingerprint(7, "aa", 4)
    w.close()
    return Trace.open(p), (e1, f1, e2, f2, e3, e4)


def test_meta_codes_events(tmp_path):
    t, (e1, f1, e2, f2, e3, e4) = _fixture(tmp_path)
    assert t.meta["run_id"] == "r1"
    assert {c.qualname for c in t.codes()} == {"main", "add"}
    assert [e.kind for e in t.events()] == ["CALL", "CALL", "RETURN", "RETURN"]
    assert t.event(e3).payload == {"value": {"k": "num", "v": 5}}
    assert len(t.events(kind="CALL")) == 2
    assert len(t.events(kind=("CALL", "RETURN"), after=e2)) == 2
    assert len(t.events(limit=3)) == 3


def test_frames_tree_navigation(tmp_path):
    t, (e1, f1, e2, f2, e3, e4) = _fixture(tmp_path)
    assert [f.id for f in t.roots()] == [f1]
    assert [f.id for f in t.children(f1)] == [f2]
    assert t.frame(f2).return_event_id == e3
    assert t.frame(f2).closed_by == "return"
    add_code = next(c for c in t.codes() if c.qualname == "add")
    assert [f.id for f in t.frames(code_id=add_code.id)] == [f2]
    assert [e.id for e in t.frame_events(f2)] == [e3]


def test_frame_containing_falls_back_to_call_event(tmp_path):
    t, (e1, f1, e2, f2, e3, e4) = _fixture(tmp_path)
    assert t.frame_containing(e2).id == f2   # CALL event: via call_event_id
    assert t.frame_containing(e3).id == f2   # RETURN event: via frame_id


def test_causal_stream_and_counts(tmp_path):
    t, ids = _fixture(tmp_path)
    assert t.main_thread_id() == 7
    stream = t.causal_stream()
    assert [(q, k) for _, q, k, _ in stream] == [
        ("main", "CALL"), ("add", "CALL"), ("add", "RETURN"),
        ("main", "RETURN")]
    assert t.counts() == {"CALL": 2, "RETURN": 2}
    assert t.fingerprints() == {7: ("aa", 4)}
