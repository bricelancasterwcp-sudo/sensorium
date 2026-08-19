import sqlite3
import threading

from sensorium.store.writer import TraceWriter


def test_roundtrip_events_frames_output(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=100)
    cid = w.intern_code("/x/prog.py", "add", 1)
    assert w.intern_code("/x/prog.py", "add", 1) == cid  # interned once
    e1 = w.add_event(10, 7, "CALL", None, cid, 1, {"args": {}})
    fid = w.open_frame(None, cid, e1, 0, 7)
    e2 = w.add_event(20, 7, "RETURN", fid, cid, None,
                     {"value": {"k": "num", "v": 5}})
    w.close_frame(fid, e2, "return")
    w.add_output(e2, "stdout", "hello\n")
    w.write_fingerprint(7, "abc123", 2)
    w.close()

    c = sqlite3.connect(p)
    assert c.execute("SELECT COUNT(*) FROM code_objects").fetchone()[0] == 1
    ev = c.execute("SELECT id, kind, frame_id FROM events ORDER BY id").fetchall()
    assert ev == [(e1, "CALL", None), (e2, "RETURN", fid)]
    fr = c.execute(
        "SELECT return_event_id, closed_by FROM frames WHERE id=?", (fid,)
    ).fetchone()
    assert fr == (e2, "return")
    assert c.execute("SELECT data FROM output").fetchone()[0] == "hello\n"
    assert c.execute("SELECT hash FROM fingerprints").fetchone()[0] == "abc123"


def test_event_ids_monotonic_and_last_event_id(tmp_path):
    w = TraceWriter(tmp_path / "t.db")
    cid = w.intern_code("/x.py", "f", 1)
    ids = [w.add_event(i, 1, "CALL", None, cid, 1, None) for i in range(5)]
    assert ids == [1, 2, 3, 4, 5] and w.last_event_id == 5
    w.close()


def test_concurrent_writers_get_unique_contiguous_ids(tmp_path):
    # The writer's central promise: safe to call from any thread, ids monotonic
    # across threads. The tracer flushes on whichever thread fills the batch,
    # so the sqlite connection must tolerate cross-thread use.
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=16)
    cid = w.intern_code("/x.py", "f", 1)
    n_threads, n_events = 8, 50
    start = threading.Barrier(n_threads)
    lock = threading.Lock()
    ids: list[int] = []
    errors: list[BaseException] = []

    def worker():
        try:
            start.wait()                 # genuinely concurrent, not staggered
            mine = [w.add_event(i, threading.get_ident(), "CALL", None, cid,
                                1, None) for i in range(n_events)]
            with lock:
                ids.extend(mine)
        except BaseException as e:       # noqa: BLE001 - surfaced by assert
            with lock:
                errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    w.close()

    total = n_threads * n_events
    assert errors == []
    assert len(ids) == total
    assert len(set(ids)) == total                       # no id handed out twice
    assert sorted(ids) == list(range(1, total + 1))     # contiguous, none lost

    c = sqlite3.connect(p)
    rows = [r[0] for r in c.execute("SELECT id FROM events ORDER BY id")]
    assert rows == list(range(1, total + 1))            # every row landed


def test_partial_trace_valid_without_close(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=2)          # tiny batch forces auto-flush
    cid = w.intern_code("/x.py", "f", 1)
    for i in range(5):
        w.add_event(i, 1, "CALL", None, cid, 1, None)
    # no close(): simulate a killed process; flushed batches must be readable
    c = sqlite3.connect(p)
    n = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert n >= 4                        # two full batches guaranteed flushed
