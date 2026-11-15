"""Store cleanup: age, count, size, pins, and the newest run."""
import json
import os
import time

import pytest

from sensorium.limits import StorePolicy
from sensorium.store import db
from sensorium.store.gc import (
    GcError, apply, format_bytes, list_traces, load_pins, plan, save_pins)
from sensorium.store.reader import Trace
from tests.helpers import record_script, run_cli


def _trace(root, name, mtime, pad=0):
    directory = root / "traces"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.db"
    conn = db.create_trace(path)
    if pad:
        conn.execute("CREATE TABLE pad (body BLOB)")
        conn.execute("INSERT INTO pad VALUES (?)", (b"x" * pad,))
    conn.commit()
    conn.close()
    os.utime(path, (mtime, mtime))
    return path


def test_keep_count_leaves_the_newest(tmp_path):
    root = tmp_path / "store"
    _trace(root, "a", 1_000)
    _trace(root, "b", 2_000)
    _trace(root, "c", 3_000)
    chosen = plan(StorePolicy(keep=1), root=root)
    assert [item.run_id for item in chosen.victims] == ["a", "b"]
    apply(chosen)
    assert [item.run_id for item in list_traces(root)] == ["c"]
    Trace.open(root / "traces" / "c.db").path  # vacuum left it readable


def test_pin_and_newest_survive_age_and_size(tmp_path):
    root = tmp_path / "store"
    _trace(root, "old", 1_000, pad=4000)
    _trace(root, "mid", 2_000, pad=4000)
    newest = _trace(root, "new", 3_000, pad=4000)
    save_pins(["old"], root)
    chosen = plan(StorePolicy(older_than=1, max_bytes=1), root=root,
                  now=10_000)
    gone = {item.run_id for item in chosen.victims}
    assert gone == {"mid"}
    assert "old" in chosen.protected and "new" in chosen.protected
    apply(chosen, dry_run=True)
    assert newest.exists() and (root / "traces" / "old.db").exists()
    apply(chosen)
    left = {item.run_id for item in list_traces(root)}
    assert left == {"old", "new"}


def test_dry_run_prints_and_deletes_nothing(tmp_path):
    root = tmp_path / "store"
    _trace(root, "a", 1_000)
    _trace(root, "b", 2_000)
    result = run_cli(["gc", "--dry-run", "--keep", "1"], tmp_path, root)
    assert result.returncode == 0, result.stderr
    assert "would delete a" in result.stdout
    assert "dry-run:" in result.stdout
    assert (root / "traces" / "a.db").exists()


def test_gc_without_a_rule_exits_2(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "store"))
    result = run_cli(["gc"], tmp_path, tmp_path / "store")
    assert result.returncode == 2
    assert "needs" in result.stderr
    assert not (tmp_path / "store" / "traces").exists()


def test_corrupt_pins_refuse_to_delete(tmp_path):
    root = tmp_path / "store"
    _trace(root, "a", 1_000)
    _trace(root, "b", 2_000)
    (root / "pins.json").write_text("{")
    with pytest.raises(GcError):
        plan(StorePolicy(keep=1), root=root)
    assert (root / "traces" / "a.db").exists()


def test_pin_command_and_mode(tmp_path):
    root = tmp_path / "store"
    _trace(root, "only", time.time())
    pinned = run_cli(["pin", "only"], tmp_path, root)
    assert pinned.returncode == 0, pinned.stderr
    path = root / "pins.json"
    assert json.loads(path.read_text())["runs"] == ["only"]
    assert path.stat().st_mode & 0o777 == 0o600
    assert load_pins(root) == ["only"]
    assert run_cli(["unpin", "only"], tmp_path, root).returncode == 0
    assert load_pins(root) == []


def test_automatic_keep_does_not_change_the_program_status(tmp_path):
    first, first_path, one = record_script(
        tmp_path, "def main():\n    return 0\n",
        env_extra={"SENSORIUM_GC_KEEP": "1"})
    assert one.returncode == 0, one.stderr
    os.utime(first_path, (1_000, 1_000))
    second, _, two = record_script(
        tmp_path, "def main():\n    return 0\n",
        env_extra={"SENSORIUM_GC_KEEP": "1"})
    assert two.returncode == 0, two.stderr
    assert "gc deleted 1" in two.stderr
    names = sorted(p.stem for p in (tmp_path / "sdir" / "traces").glob("*.db"))
    assert names == [second]
    assert first not in names


def test_format_bytes_is_1024_based():
    assert format_bytes(512) == "512 B"
    assert format_bytes(2048) == "2.0 KiB"
