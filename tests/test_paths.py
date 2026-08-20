import pytest

from sensorium import paths
from sensorium.store import db


def _mk(tmp_path, monkeypatch, names):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    for n in names:
        db.create_trace(paths.traces_dir() / f"{n}.db").close()


def test_find_by_unique_prefix(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch, ["20260818-1200-aaa111", "20260818-1300-bbb222"])
    assert paths.find_trace("20260818-13").name == "20260818-1300-bbb222.db"


def test_ambiguous_prefix_names_candidates(tmp_path, monkeypatch):
    _mk(tmp_path, monkeypatch, ["20260818-1200-aaa111", "20260818-1300-bbb222"])
    with pytest.raises(paths.TraceLookupError, match="ambiguous"):
        paths.find_trace("20260818")


def test_last_picks_newest(tmp_path, monkeypatch):
    import os, time
    _mk(tmp_path, monkeypatch, ["a-run", "b-run"])
    t = time.time()
    os.utime(paths.traces_dir() / "a-run.db", (t + 60, t + 60))
    assert paths.find_trace("last").name == "a-run.db"


def test_no_traces_is_clear_error(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path))
    with pytest.raises(paths.TraceLookupError, match="no traces"):
        paths.find_trace("last")


def test_run_ids_unique():
    assert paths.new_run_id() != paths.new_run_id()
