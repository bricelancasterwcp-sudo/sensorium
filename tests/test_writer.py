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


def test_add_event_task_id_defaults_to_null_and_round_trips(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=100)
    cid = w.intern_code("/x/prog.py", "f", 1)
    e1 = w.add_event(10, 7, "CALL", None, cid, 1, {"args": {}})
    e2 = w.add_event(11, 7, "CALL", None, cid, 1, {"args": {}}, task_id=3)
    w.add_task(3, "task-A", 7)
    w.add_task(4, None, 7)                  # a task whose name was unreadable
    w.close()
    c = sqlite3.connect(p)
    rows = c.execute("SELECT id, task_id FROM events ORDER BY id").fetchall()
    assert rows == [(e1, None), (e2, 3)]
    tasks = c.execute("SELECT id, name, thread_id FROM tasks ORDER BY id").fetchall()
    assert tasks == [(3, "task-A", 7), (4, None, 7)]


def test_open_frame_records_the_kind_and_defaults_to_function(tmp_path):
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=100)
    cid = w.intern_code("/x/prog.py", "gen", 1)
    e1 = w.add_event(0, 1, "CALL", None, cid, 1, {"args": {}})
    f1 = w.open_frame(None, cid, e1, 0, 1)
    f2 = w.open_frame(None, cid, e1, 0, 1, kind="coroutine")
    w.close()
    c = sqlite3.connect(p)
    assert c.execute("SELECT id, kind FROM frames ORDER BY id").fetchall() == [
        (f1, "function"), (f2, "coroutine")]


class _CountingConn:
    """A connection that counts commits and forwards everything else.

    The row COUNT cannot see the difference between one transaction and one
    per task -- both write the same rows -- so the property under test is
    structural and has to be observed structurally.
    """

    def __init__(self, conn):
        self._conn = conn
        self.commits = 0

    def commit(self):
        self.commits += 1
        return self._conn.commit()

    def __getattr__(self, name):
        return getattr(self._conn, name)


def test_task_fingerprints_are_written_in_one_transaction(tmp_path):
    """`uninstall` writes one row per asyncio task, and a commit is an fsync.

    Per-row commits made exit cost scale with the task count (measured on
    this box's ext4: 1.3-3.2 ms per task, so recording a 2,000-task program
    spent 2.18 s of wall clock where it now spends 0.35 s -- all of it AFTER
    the program had finished). The rows are unchanged; what must not grow
    with the number of tasks is the number of transactions.
    """
    w = TraceWriter(tmp_path / "t.db", batch=512)
    for k in range(1, 201):
        w.add_task(k, f"task-{k}", 1)
    w._conn = _CountingConn(w._conn)
    w.write_task_fingerprints([(k, f"{k:032x}", k) for k in range(1, 201)])
    assert w._conn.commits == 1
    w.close()

    c = sqlite3.connect(tmp_path / "t.db")
    rows = c.execute("SELECT task_id, name, hash, n_events FROM "
                     "task_fingerprints ORDER BY task_id").fetchall()
    assert len(rows) == 200
    assert rows[0] == (1, "task-1", f"{1:032x}", 1)
    assert rows[-1] == (200, "task-200", f"{200:032x}", 200)


def test_write_task_fingerprint_still_writes_one_row(tmp_path):
    """The single-row entry point is kept (tests and any single-task caller
    use it) and must go through the same path, flush included."""
    w = TraceWriter(tmp_path / "t.db", batch=512)
    w.add_task(3, "task-A", 1)              # still in the write buffer
    w._conn = _CountingConn(w._conn)
    w.write_task_fingerprint(3, "abcdef", 7)
    assert w._conn.commits == 1
    w.close()
    c = sqlite3.connect(tmp_path / "t.db")
    assert c.execute("SELECT task_id, name, hash, n_events FROM "
                     "task_fingerprints").fetchall() == [(3, "task-A",
                                                          "abcdef", 7)]


def _rows(path, sql: str):
    """Read through a connection of its own, opened and closed here.

    A reader that stays open holds the snapshot it first read under WAL, so
    a second look through the same connection could report the writer's
    silence long after the writer stopped being silent. Opening per look
    makes "before close" and "after close" two independent readings.
    """
    c = sqlite3.connect(path)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_a_non_durable_writer_commits_nothing_before_close(tmp_path):
    """The converter's mode: one transaction per trace.

    `durable=False` is for a writer whose file is renamed into place only
    after `close()` -- nothing outside may see a row before then, because
    there is no reader to show it to and every commit before then is an
    fsync bought for nobody. The durable twin above
    (`test_partial_trace_valid_without_close`) pins the opposite promise for
    the recorder, and both must hold at once.
    """
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=2, durable=False)   # tiny batch forces flushes
    cid = w.intern_code("/x.py", "f", 1)
    for i in range(5):
        w.add_event(i, 1, "CALL", None, cid, 1, None)
    # Two batches have been flushed to the connection and neither committed.
    assert _rows(p, "SELECT COUNT(*) FROM events") == [(0,)]
    w.close()
    assert _rows(p, "SELECT COUNT(*) FROM events") == [(5,)]


def test_a_non_durable_writer_runs_normal_under_wal(tmp_path):
    """`synchronous=NORMAL` (1) under `journal_mode=WAL`, and only there.

    NORMAL under WAL is the mode that stops fsyncing every commit while
    keeping the database consistent against a process death; the durable
    default keeps FULL (2), because the recorder's partial trace is worth
    the fsyncs.
    """
    w = TraceWriter(tmp_path / "n.db", durable=False)
    assert w._conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    assert w._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    w.close()

    d = TraceWriter(tmp_path / "d.db")
    assert d._conn.execute("PRAGMA synchronous").fetchone()[0] == 2
    assert d._conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    d.close()


def test_set_meta_and_fingerprints_ride_the_one_transaction(tmp_path):
    """The finalize pass commits too, and in this mode it must not.

    `set_meta`, `write_fingerprint` and `write_task_fingerprints` each
    committed on their own -- about thirty-five fsyncs per converted trace
    on top of one per batch. In the non-durable mode they are writes inside
    the single transaction like any other, so nothing outside sees them
    until `close()`.
    """
    p = tmp_path / "t.db"
    w = TraceWriter(p, durable=False)
    w.set_meta("incomplete", True)
    w.add_task(3, "task-A", 1)
    w.write_fingerprint(1, "abc123", 2)
    w.write_task_fingerprints([(3, "def456", 1)])

    assert _rows(p, "SELECT COUNT(*) FROM meta WHERE key='incomplete'") == [(0,)]
    assert _rows(p, "SELECT COUNT(*) FROM fingerprints") == [(0,)]
    assert _rows(p, "SELECT COUNT(*) FROM task_fingerprints") == [(0,)]
    assert _rows(p, "SELECT COUNT(*) FROM tasks") == [(0,)]

    w.close()
    assert _rows(p, "SELECT value FROM meta WHERE key='incomplete'") == [("true",)]
    assert _rows(p, "SELECT thread_id, hash, n_events FROM fingerprints") == \
        [(1, "abc123", 2)]
    assert _rows(p, "SELECT task_id, name, hash, n_events FROM "
                    "task_fingerprints") == [(3, "task-A", "def456", 1)]


def test_a_discarded_writer_commits_nothing_at_all(tmp_path):
    """A trace nobody will finish is let go of, not committed.

    `close()` COMMITS -- and in the non-durable mode that commit is the
    whole trace, checkpointed out of the WAL into a file `ingest.convert`
    unlinks a moment later. `Builder.abort()` calls this instead: the
    transaction is rolled back and the connection closed, so nothing the
    writer buffered ever reaches the file.
    """
    p = tmp_path / "t.db"
    w = TraceWriter(p, batch=2, durable=False)   # tiny batch forces flushes
    cid = w.intern_code("/x.py", "f", 1)
    for i in range(5):
        w.add_event(i, 1, "CALL", None, cid, 1, None)
    w.discard()
    assert _rows(p, "SELECT COUNT(*) FROM events") == [(0,)]
