import sqlite3

import pytest

from sensorium.store import db


def test_open_refuses_a_trace_format_newer_than_understood(tmp_path):
    """`trace_format` was written and never read. A trace from a FUTURE
    sensorium (a higher format) must be refused, not queried as if its schema
    matched -- silently answering from a layout this version does not know."""
    path = tmp_path / "future.db"
    conn = db.create_trace(path)
    db.set_meta(conn, "trace_format", db.TRACE_FORMAT + 1)
    conn.commit()
    conn.close()
    with pytest.raises(db.TraceFormatError):
        db.open_trace(path)


def test_open_accepts_the_current_and_a_legacy_format(tmp_path):
    """The current format opens, and so does a trace recorded before the key
    existed at all (absent -> not newer)."""
    cur = tmp_path / "cur.db"
    db.create_trace(cur).close()
    db.open_trace(cur).close()                       # no raise
    legacy = tmp_path / "legacy.db"
    conn = db.create_trace(legacy)
    conn.execute("DELETE FROM meta WHERE key = 'trace_format'")
    conn.commit()
    conn.close()
    db.open_trace(legacy).close()                    # no raise


def test_create_trace_has_all_tables(tmp_path):
    conn = db.create_trace(tmp_path / "t.db")
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"meta", "code_objects", "frames", "events", "output",
            "fingerprints", "tasks", "task_fingerprints"} <= names
    assert db.get_meta(conn, "trace_format") == db.TRACE_FORMAT


def test_meta_roundtrip_preserves_types(tmp_path):
    conn = db.create_trace(tmp_path / "t.db")
    db.set_meta(conn, "argv", ["prog.py", "--x"])
    db.set_meta(conn, "incomplete", True)
    db.set_meta(conn, "exit_status", 3)
    conn.commit()
    assert db.get_meta(conn, "argv") == ["prog.py", "--x"]
    assert db.get_meta(conn, "incomplete") is True
    assert db.all_meta(conn)["exit_status"] == 3
    assert db.get_meta(conn, "missing", "d") == "d"


def test_open_trace_missing_file_raises(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        db.open_trace(tmp_path / "nope.db")


def test_format_2_has_task_id_and_tasks_table(tmp_path):
    """Spec D4: events gains a nullable task_id; a tasks table maps serial to
    display name once, not per event. Frames stayed unchanged at format 2;
    format 3 appends `kind` -- see
    test_format_3_adds_frame_kind_and_task_fingerprints -- so this only pins
    the format-2 columns as a PREFIX, not the whole row."""
    conn = db.create_trace(tmp_path / "t.db")
    assert db.get_meta(conn, "trace_format") >= 2
    ev_cols = [r[1] for r in conn.execute("PRAGMA table_info(events)")]
    assert ev_cols[-1] == "task_id"
    task_cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)")]
    assert task_cols == ["id", "name", "thread_id"]
    fr_cols = [r[1] for r in conn.execute("PRAGMA table_info(frames)")]
    assert fr_cols[:9] == ["id", "parent_id", "code_id", "call_event_id",
                       "return_event_id", "depth", "thread_id", "closed_by",
                       "unwind_exc"]


def test_format_3_adds_frame_kind_and_task_fingerprints(tmp_path):
    conn = db.create_trace(tmp_path / "t.db")
    assert db.get_meta(conn, "trace_format") >= 3
    fcols = [r[1] for r in conn.execute("PRAGMA table_info(frames)")]
    assert fcols[-1] == "kind"
    tcols = [r[1] for r in conn.execute("PRAGMA table_info(task_fingerprints)")]
    assert tcols == ["task_id", "name", "hash", "n_events"]


def _format4_finalized(path, **meta):
    conn = db.create_trace(path)
    base = {"run_id": "r", "argv": ["p.py"], "cwd": "/w", "env_hash": "0" * 16,
            "start_ts": 1.0, "end_ts": 2.0, "exit_status": 0,
            "main_thread_ident": 1, "fingerprint_basis": "per-task",
            "truncated_count": 0, "source_hashes": {}, "recorder": "x 1.0",
            "lang": "rust", "capabilities": {"threads": False, "children": False,
                                             "stdin": False},
            "incomplete": False}
    base.update(meta)
    for k, v in base.items():
        db.set_meta(conn, k, v)
    conn.commit()
    conn.close()


def test_format_is_4():
    assert db.TRACE_FORMAT == 4


def test_open_refuses_a_finalized_format4_trace_missing_a_required_key(tmp_path):
    """The choke point: a recorder that says it finalized and left out a
    key the readers default to zero must be refused, naming the key."""
    p = tmp_path / "t.db"
    _format4_finalized(p)
    db.open_trace(p).close()                       # complete: opens
    _format4_finalized(tmp_path / "u.db")
    c = db.open_trace(tmp_path / "u.db")
    c.execute("DELETE FROM meta WHERE key = 'truncated_count'")
    c.commit()
    c.close()
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(tmp_path / "u.db")
    assert "truncated_count" in str(e.value) and "x 1.0" in str(e.value)


def test_open_requires_witness_keys_only_for_declared_capabilities(tmp_path):
    p = tmp_path / "t.db"
    _format4_finalized(p, capabilities={"threads": True, "children": False,
                                        "stdin": False})
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(p)
    assert "threads_started" in str(e.value)
    q = tmp_path / "u.db"
    _format4_finalized(q, capabilities={"threads": True, "children": False,
                                        "stdin": False},
                       threads_started=0, live_threads=[])
    db.open_trace(q).close()


def test_open_does_not_refuse_an_unfinished_or_hand_built_trace(tmp_path):
    """`incomplete` True, or absent (a trace still being written, or a test
    fixture that never claimed to have finalized), opens as before."""
    p = tmp_path / "t.db"
    _format4_finalized(p, incomplete=True)
    c = db.open_trace(p)
    c.execute("DELETE FROM meta WHERE key = 'exit_status'")
    c.commit()
    c.close()
    db.open_trace(p).close()
    q = tmp_path / "bare.db"
    db.create_trace(q).close()
    db.open_trace(q).close()


def test_open_refuses_a_finalized_trace_whose_capabilities_are_not_a_dict(tmp_path):
    """A declaration this reader cannot act on is not a declaration. A list
    would raise AttributeError out of `open_trace` -- which the CLI does not
    catch -- and a null would pass, then be rendered downstream as the full
    Python capability set. Both are refused by name instead."""
    p = tmp_path / "list.db"
    _format4_finalized(p, capabilities=["threads", "stdin"])
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(p)
    assert "capabilities" in str(e.value)
    q = tmp_path / "null.db"
    _format4_finalized(q, capabilities=None)
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(q)
    assert "capabilities" in str(e.value)


def test_the_refusal_names_no_recorder_rather_than_the_word_none(tmp_path):
    """`recorder: null` must not print as "written by None"."""
    p = tmp_path / "t.db"
    _format4_finalized(p, recorder=None, capabilities=None)
    with pytest.raises(db.TraceFormatError) as e:
        db.open_trace(p)
    assert "written by an unnamed recorder" in str(e.value)
