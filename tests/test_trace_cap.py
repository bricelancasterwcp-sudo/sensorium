"""A per-function cap keeps the call-tree skeleton and the failing frame."""
import json
import sqlite3

from sensorium.store import payloads
from sensorium.store.reader import Trace
from sensorium.store.writer import TraceWriter
from tests.helpers import record_inproc, record_script, run_cli

LEAF = """
def leaf(i):
    return i

def main():
    for i in range(20):
        leaf(i)

if __name__ == "__main__":
    main()
"""

RAISES = """
def leaf(i):
    if i == 19:
        raise RuntimeError("boom")
    return i

def main():
    for i in range(20):
        leaf(i)
"""


def _calls(trace, qual):
    return [e for e in trace.events(kind="CALL")
            if trace.code(e.code_id).qualname == qual]


def test_per_function_cap_counts_the_calls_it_drops(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("SENSORIUM_MAX_CALLS", "3")
    monkeypatch.setenv("SENSORIUM_MAX_EVENTS", "0")
    monkeypatch.setenv("SENSORIUM_MAX_BYTES", "0")
    trace, err = record_inproc(tmp_path, LEAF)
    assert err is None
    assert len(_calls(trace, "leaf")) == 3
    assert trace.meta["trace_truncated"] is True
    limits = trace.meta["trace_limits"]
    assert limits["hit"] == ["max_calls"]
    assert limits["calls_elided"] == 17
    assert limits["max_calls"] == 3
    row = trace.meta["elisions"]
    assert row[0]["qualname"] == "leaf"
    assert row[0]["elided"] == 17
    assert row[0]["kept"] == 3


def test_a_failure_past_the_cap_is_still_in_the_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "store"))
    monkeypatch.setenv("SENSORIUM_MAX_CALLS", "3")
    monkeypatch.setenv("SENSORIUM_MAX_EVENTS", "0")
    monkeypatch.setenv("SENSORIUM_MAX_BYTES", "0")
    trace, err = record_inproc(tmp_path, RAISES)
    assert isinstance(err, RuntimeError)
    assert len(_calls(trace, "leaf")) == 4
    raises = [e for e in trace.events(kind="RAISE")
              if trace.code(e.code_id).qualname == "leaf"]
    assert raises and raises[0].payload["exc"]["type"] == "RuntimeError"
    assert trace.meta["trace_limits"]["calls_elided"] == 16
    assert trace.meta["trace_limits"]["failures_kept"] == 1


def test_queries_say_the_trace_was_truncated(tmp_path):
    run_id, _path, r = record_script(
        tmp_path, LEAF, extra=["--max-calls", "3", "--max-events", "0",
                               "--max-bytes", "0"])
    assert r.returncode == 0, r.stderr
    store = tmp_path / "sdir"
    info = run_cli(["info", run_id], tmp_path, store)
    assert info.returncode == 0, info.stderr
    assert "TRUNCATED:" in info.stdout
    assert "elided 17 calls of leaf" in info.stdout
    assert "truncated values:" in info.stdout
    listed = run_cli(["runs"], tmp_path, store)
    assert "TRUNCATED" in listed.stdout
    tree = run_cli(["tree", run_id], tmp_path, store)
    assert "elided 17 calls of leaf" in tree.stdout
    exc = run_cli(["exceptions", run_id], tmp_path, store)
    assert exc.returncode == 3, exc.stdout
    assert "no RAISE events recorded (see TRUNCATED above)" in exc.stdout


def test_no_cap_keeps_every_call(tmp_path):
    run_id, path, r = record_script(
        tmp_path, LEAF, extra=["--no-cap"],
        env_extra={"SENSORIUM_MAX_CALLS": "3"})
    assert r.returncode == 0, r.stderr
    trace = Trace.open(path)
    assert "trace_truncated" not in trace.meta
    assert len(_calls(trace, "leaf")) == 20
    assert run_id


def test_repeated_long_payload_roundtrips_and_redact_drops_it(tmp_path):
    path = tmp_path / "t.db"
    writer = TraceWriter(path, batch=2)
    body = "n" * 200
    payload = {"args": {"note": body}}
    code = writer.intern_code("f.py", "f", 1)
    writer.add_event(1, 1, "CALL", None, code, 1, payload)
    writer.add_event(2, 1, "CALL", None, code, 1, payload)
    writer.close()
    conn = sqlite3.connect(path)
    raw = [row[0] for row in conn.execute(
        "SELECT payload FROM events ORDER BY id")]
    assert raw[0].startswith("{")
    assert raw[1].startswith("#")
    strings = payloads.load_strings(conn)
    assert payloads.decode(raw[0], strings) == payloads.decode(raw[1], strings)
    conn.execute("UPDATE events SET payload = ?", ('{"args":{}}',))
    payloads.drop_unreferenced(conn)
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM strings").fetchone()[0] == 0
    conn.close()
    trace = Trace.open(path)
    assert [e.payload for e in trace.events()] == [{"args": {}}, {"args": {}}]
    assert json.loads(raw[0])["args"]["note"] == body
