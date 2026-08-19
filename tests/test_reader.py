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
    # this fixture never sets meta["main_thread_ident"]: the value above
    # comes from the event-id-1 fallback, which must say so of itself.
    assert t.main_thread_basis() == "inferred"
    stream = t.causal_stream()
    assert [(q, k) for _, q, k, _ in stream] == [
        ("main", "CALL"), ("add", "CALL"), ("add", "RETURN"),
        ("main", "RETURN")]
    assert t.counts() == {"CALL": 2, "RETURN": 2}
    assert t.fingerprints() == {7: ("aa", 4)}


def test_main_thread_id_prefers_recorded_ident_over_event_order(tmp_path):
    """A worker thread's first RECORDED event can land before the main
    thread's own first event -- under --focus/--window filtering, or
    ordinary scheduling jitter in a program that starts a worker early.
    meta["main_thread_ident"] must win regardless of which thread's event
    happened to get id 1."""
    p = tmp_path / "t.db"
    w = TraceWriter(p)
    worker_code = w.intern_code("/x/prog.py", "worker_fn", 1)
    main_code = w.intern_code("/x/prog.py", "main", 5)
    w.add_event(10, 999, "CALL", None, worker_code, 1, {"args": {}})  # id 1
    w.add_event(20, 7, "CALL", None, main_code, 5, {"args": {}})      # id 2
    w.set_meta("main_thread_ident", 7)
    w.close()

    t = Trace.open(p)
    assert t.main_thread_id() == 7
    assert t.main_thread_basis() == "recorded"
    # and the causal stream actually compared is the main thread's, not the
    # worker's that happened to log first
    assert [(q, k) for _, q, k, _ in t.causal_stream()] == [("main", "CALL")]


def test_main_thread_id_falls_back_and_flags_inference_on_legacy_traces(
        tmp_path):
    """No main_thread_ident key at all -- a trace recorded before that key
    existed. The event-id-1 heuristic runs, and here it produces exactly
    the false answer it can produce: it names the WORKER thread. That must
    be visible to callers via main_thread_basis(), not silently asserted as
    fact."""
    p = tmp_path / "t.db"
    w = TraceWriter(p)
    worker_code = w.intern_code("/x/prog.py", "worker_fn", 1)
    main_code = w.intern_code("/x/prog.py", "main", 5)
    w.add_event(10, 999, "CALL", None, worker_code, 1, {"args": {}})  # id 1
    w.add_event(20, 7, "CALL", None, main_code, 5, {"args": {}})      # id 2
    w.close()

    t = Trace.open(p)
    assert t.main_thread_id() == 999            # the wrong thread, by design
    assert t.main_thread_basis() == "inferred"


def test_main_thread_basis_is_none_with_no_events_and_no_recorded_key(
        tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p)
    w.close()
    t = Trace.open(p)
    assert t.main_thread_id() is None
    assert t.main_thread_basis() is None
