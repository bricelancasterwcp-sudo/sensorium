import sqlite3

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
