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
            "fingerprints"} <= names
    assert db.get_meta(conn, "trace_format") == 1


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
