import sqlite3

from sensorium.store import db


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
