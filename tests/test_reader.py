from pathlib import Path

from sensorium.store.reader import FrameState, Trace
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


def _two_task_trace(tmp_path):
    """Hand-built: one framed call, two unframed calls (one per task)."""
    w = TraceWriter(tmp_path / "t.db", batch=100)
    c_main = w.intern_code("/x/p.py", "main", 1)
    c_gen = w.intern_code("/x/p.py", "gen", 5)
    e1 = w.add_event(0, 1, "CALL", None, c_main, 1, {"args": {}})
    f1 = w.open_frame(None, c_main, e1, 0, 1)
    w.add_event(1, 1, "CALL", None, c_gen, 5,
                {"args": {}, "unframed": "generator", "parent_frame": f1},
                task_id=1)
    w.add_event(2, 1, "CALL", None, c_gen, 5,
                {"args": {}, "unframed": "generator"}, task_id=2)
    w.add_task(1, "Task-1", 1)
    w.add_task(2, None, 1)
    w.close()
    return Trace.open(tmp_path / "t.db"), c_main, c_gen, f1


def test_reader_exposes_format_tasks_and_task_ids(tmp_path):
    t, c_main, c_gen, _ = _two_task_trace(tmp_path)
    assert t.format >= 2       # task_id/tasks arrived at format 2; a live
                                # trace is always written at the current format
    assert t.parentage_basis() == "derived"
    assert [(k.id, k.name, k.thread_id) for k in t.tasks()] == [
        (1, "Task-1", 1), (2, None, 1)]
    assert t.task(2).name is None and t.task(9) is None
    evs = t.events(kind="CALL")
    assert [e.task_id for e in evs] == [None, 1, 2]


def test_unframed_calls_is_a_join_not_a_payload_key(tmp_path):
    """Spec D3: 'recorded but not framed' must be decidable from the frames
    table alone, so a v1 trace (no `unframed` key) gets the same answer."""
    t, c_main, c_gen, f1 = _two_task_trace(tmp_path)
    unf = t.unframed_calls()
    assert [e.code_id for e in unf] == [c_gen, c_gen]
    assert t.unframed_calls(code_id=c_main) == []
    assert t.call_counts() == {c_main: 1, c_gen: 2}


def _frame_with(tmp_path, closed_by, unwind_exc, tail_events, kind="coroutine"):
    """One frame of `kind`, closed as given, with `tail_events` =
    [(kind, line, payload), ...] appended in order after its CALL."""
    w = TraceWriter(tmp_path / "t.db", batch=100)
    c = w.intern_code("/x/p.py", "worker", 1)
    e1 = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f1 = w.open_frame(None, c, e1, 0, 1, kind=kind)
    for k, line, payload in tail_events:
        w.add_event(1, 1, k, f1, c, line, payload)
    if closed_by is not None:
        w.close_frame(f1, None, closed_by, unwind_exc)
    w.close()
    t = Trace.open(tmp_path / "t.db")
    return t, t.frame(f1)


CANCEL = {"type": "CancelledError", "msg": "", "oid": 1, "serial": 7}
GENEXIT = {"type": "GeneratorExit", "msg": "", "oid": 2, "serial": 8}
VALERR = {"type": "ValueError", "msg": "x", "oid": 3, "serial": 9}


def test_frame_kind_reads_function_on_old_traces_and_the_column_on_new(tmp_path):
    t, f = _frame_with(tmp_path, "return", None, [])
    assert f.kind == "coroutine"
    assert Trace.open(Path(__file__).parent / "fixtures" / "format2_async.db"
                      ).frames()[0].kind == "function"
    assert Trace.open(Path(__file__).parent / "fixtures" / "format1_async.db"
                      ).frames()[0].kind == "function"


def test_frame_state_derives_each_state_from_evidence(tmp_path):
    t, f = _frame_with(tmp_path / "a", "return", None,
                       [("YIELD", 29, {"awaiting": "Future"}), ("RESUME", 29, None)])
    assert t.frame_state(f).state == "returned"
    t, f = _frame_with(tmp_path / "b", "unwind", VALERR,
                       [("YIELD", 29, {"awaiting": "Future"}), ("RESUME", 29, None)])
    assert t.frame_state(f) == FrameState("raised", None, VALERR)
    t, f = _frame_with(tmp_path / "c", "unwind", CANCEL,
                       [("YIELD", 29, {"awaiting": "Future"}),
                        ("RESUME", 29, {"thrown": CANCEL})])
    assert t.frame_state(f) == FrameState("cancelled", 29, CANCEL)
    t, f = _frame_with(tmp_path / "d", "unwind", GENEXIT,
                       [("YIELD", 23, {"awaiting": "NoneType"}),
                        ("RESUME", 23, {"thrown": GENEXIT})], kind="generator")
    assert t.frame_state(f) == FrameState("abandoned", 23, GENEXIT)
    t, f = _frame_with(tmp_path / "e", "unwind", VALERR,
                       [("YIELD", 23, {"awaiting": "NoneType"}),
                        ("RESUME", 23, {"thrown": VALERR})], kind="generator")
    assert t.frame_state(f) == FrameState("thrown", 23, VALERR)
    t, f = _frame_with(tmp_path / "f", None, None,
                       [("YIELD", 29, {"awaiting": "Future"})])
    assert t.frame_state(f) == FrameState("suspended", 29, None)
    t, f = _frame_with(tmp_path / "g", None, None, [])
    assert t.frame_state(f) == FrameState("open", None, None)


def test_frame_state_cancelled_requires_the_serials_to_match(tmp_path):
    """A CancelledError thrown in and a DIFFERENT CancelledError raised
    inside are two objects; only the serial says which one unwound the
    frame. A type match alone would over-claim."""
    other = dict(CANCEL, serial=99)
    t, f = _frame_with(tmp_path, "unwind", other,
                       [("YIELD", 29, {"awaiting": "Future"}),
                        ("RESUME", 29, {"thrown": CANCEL})])
    assert t.frame_state(f).state == "raised"


def test_suspensions_returns_yield_and_resume_rows_in_order(tmp_path):
    """Two suspend/resume cycles, with a LINE row in between: suspensions()
    must return only the YIELD/RESUME rows, in id order, and must not drop
    the RESUME half (a kind=YIELD-only filter would look right on one
    cycle but silently lose every RESUME)."""
    t, f = _frame_with(tmp_path, "unwind", CANCEL,
                       [("YIELD", 29, {"awaiting": "Future"}),
                        ("RESUME", 29, None),
                        ("LINE", 30, {"deltas": {}}),
                        ("YIELD", 31, {"awaiting": "Task"}),
                        ("RESUME", 31, {"thrown": CANCEL})])
    assert [(e.kind, e.line) for e in t.suspensions(f.id)] == [
        ("YIELD", 29), ("RESUME", 29), ("YIELD", 31), ("RESUME", 31)]


import sqlite3
from pathlib import Path

from sensorium.store.reader import Trace

GEN_FIXTURE = Path(__file__).parent / "fixtures" / "format2_gen.db"


def _old_unframed_ids(path, code_id=None):
    """The LEFT JOIN this rewrite replaces, kept here as the oracle."""
    c = sqlite3.connect(path)
    q = ("SELECT e.id FROM events e LEFT JOIN frames f ON f.call_event_id = e.id "
         "WHERE e.kind = 'CALL' AND f.id IS NULL AND e.code_id IS NOT NULL")
    params = ()
    if code_id is not None:
        q += " AND e.code_id = ?"
        params = (code_id,)
    return [r[0] for r in c.execute(q + " ORDER BY e.id", params)]


def test_unframed_calls_returns_exactly_what_the_join_returned():
    t = Trace.open(GEN_FIXTURE)
    got = [e.id for e in t.unframed_calls()]
    assert got == _old_unframed_ids(GEN_FIXTURE)
    assert got, "the format-2 generator fixture must contain unframed calls"
    cid = t.event(got[0]).code_id
    assert ([e.id for e in t.unframed_calls(code_id=cid)]
            == _old_unframed_ids(GEN_FIXTURE, cid))


def test_unframed_calls_query_does_not_scan_frames_per_event():
    """The plan is the fact: a per-CALL scan of `frames` is quadratic and was
    measured at 54 s on a 93k-event trace."""
    t = Trace.open(GEN_FIXTURE)
    plan = " ".join(r[3] for r in t._c.execute(
        "EXPLAIN QUERY PLAN " + t._unframed_sql()))
    assert "LEFT-JOIN" not in plan


def test_children_and_roots_match_a_direct_query():
    t = Trace.open(GEN_FIXTURE)
    c = sqlite3.connect(GEN_FIXTURE)
    roots = [r[0] for r in c.execute(
        "SELECT id FROM frames WHERE parent_id IS NULL ORDER BY id")]
    assert [f.id for f in t.roots()] == roots
    for fid in roots[:3]:
        kids = [r[0] for r in c.execute(
            "SELECT id FROM frames WHERE parent_id = ? ORDER BY id", (fid,))]
        assert [f.id for f in t.children(fid)] == kids
    assert t.children(10**9) == []


def _meta_trace(tmp_path, name, meta):
    p = Path(tmp_path) / f"{name}.db"
    w = TraceWriter(p)
    for k, v in meta.items():
        w.set_meta(k, v)
    w.close()
    return Trace.open(p)


def test_dropped_writes_adds_the_witnessed_drops_to_the_inferred_gaps(
        tmp_path):
    """A Rust recorder loses trace writes two ways, and they are DISJOINT:
    `records_dropped` is what a writer knew it could not write (a failed
    mmap or ftruncate leaves the thread inert), `seq_gaps` is a hole in the
    process-global sequence the merge inferred -- a record minted and never
    found. Reading only one of them would let `diff` issue a verdict over a
    hole the trace itself declares (rust/HONESTY.md section 4)."""
    t = _meta_trace(tmp_path, "both", {"records_dropped": {"2": 3, "5": 4},
                                       "seq_gaps": 2})
    assert t.dropped_writes() == 9
    gaps_only = _meta_trace(tmp_path, "gaps", {"records_dropped": {},
                                               "seq_gaps": 2})
    assert gaps_only.dropped_writes() == 2
    dropped_only = _meta_trace(tmp_path, "dropped",
                               {"records_dropped": {"2": 3}})
    assert dropped_only.dropped_writes() == 3
    clean = _meta_trace(tmp_path, "clean", {"records_dropped": {},
                                            "seq_gaps": 0})
    assert clean.dropped_writes() == 0


def test_dropped_writes_prefers_late_writes_where_a_python_run_wrote_it(
        tmp_path):
    """`late_writes` is the Python recorder's own count and is not summed
    with anything: the two recorders' keys never appear on one trace, and
    a reader that added them would be adding one recording's number to
    another's."""
    t = _meta_trace(tmp_path, "py", {"late_writes": 3, "seq_gaps": 99})
    assert t.dropped_writes() == 3
    assert _meta_trace(tmp_path, "py0",
                       {"late_writes": 0}).dropped_writes() == 0
