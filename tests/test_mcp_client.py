"""The client every other test, the corpus and E17 will talk through.

`corpus/mcp_client.py` is a test instrument, so it is tested the way an
instrument is: against a REAL process over REAL pipes, not against a
mock of one. The server it talks to here is a thirty-line echo script
the test writes into `tmp_path` -- it answers `server/discover` and
`initialize` minimally and echoes every request's `params` straight
back, which is what makes the `_meta` rules observable on the wire
rather than in the client's own bookkeeping. `tests/test_mcp_server.py`
(task 5b) points the same client at the real server.

Two things this file is deliberately strict about:

* THE `_meta` RULES. Modern stamps it, legacy does not, `meta=True`
  forces it, and a caller's own `_meta` is sent AS GIVEN. The last one
  is the only way the -32022 and P5 tests can craft a malformed `_meta`
  at all, so a client that "helpfully" merged its own keys in would
  make those tests unwritable.
* DEATH. A server that exits must fail every pending and every future
  call with `McpError(-32000, ...)` at once. A client that let the
  futures hang would turn every server bug into a 60-second timeout,
  and one that let `BrokenPipeError` out would make every such bug read
  as a client bug.

PRE-REGISTERED MUTATIONS (task 5a, step 7), each with the test that
catches it:

* merge a caller's `_meta` into the default block instead of sending it
  as given -> `test_a_caller_supplied_meta_is_sent_exactly_as_given`.
* drop the EOF path that fails every future (leave the reader thread to
  exit quietly) -> `test_a_dead_server_fails_every_wait_and_send_with_
  mcp_error`, which is bounded at 3 s and fails with `TimeoutError`
  rather than hanging.
"""
from __future__ import annotations

import json
import sys
import time

import pytest

from corpus.mcp_client import (
    META_CAPS,
    META_CLIENT,
    META_VERSION,
    CallResult,
    McpClient,
    McpError,
    split_text,
)
from sensorium.mcp.result import STDERR_LABEL

#: A server that speaks just enough of the protocol to echo. Every
#: request comes back as `result.echo`, which is the request's `params`
#: verbatim -- `_meta` included, or absent when the client sent none.
ECHO_SERVER = r'''
import json
import sys


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def log(msg):
    sys.stderr.write("sensorium mcp: " + msg + "\n")
    sys.stderr.flush()


log("handshake discover 2026-07-28")
log("child 4242 pgid 4243 tool record")
log("child 4244 pgid 4245 tool refocus")

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    mid, method = msg.get("id"), msg.get("method")
    params = msg.get("params")
    log("recv " + str(method))
    if mid is None:
        continue
    if method == "silent":
        continue
    if method == "garbage":
        sys.stdout.write("this line is not json\n")
        sys.stdout.flush()
        send({"jsonrpc": "2.0", "id": mid, "result": {"echo": params}})
    elif method == "boom":
        send({"jsonrpc": "2.0", "id": mid,
              "error": {"code": -32602, "message": "no such thing",
                        "data": {"fields": ["regex"]}}})
    elif method == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": (params or {}).get("protocolVersion"),
            "echo": params}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "tools": [{"name": "runs"}, {"name": "info"}], "echo": params}})
    elif method == "tools/call":
        args = (params or {}).get("arguments") or {}
        out = {"content": [{"type": "text", "text": args.get("text", "")}],
               "echo": params}
        if "exit" in args:
            out["structuredContent"] = {"exit": args["exit"]}
        if args.get("isError"):
            out["isError"] = True
        send({"jsonrpc": "2.0", "id": mid, "result": out})
    else:
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "resultType": "complete", "echo": params}})
'''

#: A server that is gone before the client's first request.
DEAD_SERVER = "import sys\nsys.exit(3)\n"


@pytest.fixture
def echo(tmp_path):
    script = tmp_path / "echo_server.py"
    script.write_text(ECHO_SERVER, encoding="utf-8")
    return [sys.executable, str(script)]


@pytest.fixture
def dead(tmp_path):
    script = tmp_path / "dead_server.py"
    script.write_text(DEAD_SERVER, encoding="utf-8")
    return [sys.executable, str(script)]


def body(*lines: str) -> str:
    return "".join(line + "\n" for line in lines)


def recv(client) -> list[str]:
    """The methods the echo server logged, in order. Read AFTER the
    context manager: the stderr drainer is a thread, and a line the
    server flushed is not a line the client has necessarily read yet."""
    return [ln.split("recv ", 1)[1] for ln in client.stderr_lines
            if "recv " in ln]


def eventually(fn, timeout: float = 5.0):
    """Poll a live server's stderr until it says what we are waiting
    for. The same shape task 5b needs for `child_pgids()` mid-call."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.02)
    return fn()


# ------------------------------------------------------------ split_text

def test_split_text_pulls_the_header_the_stdout_and_the_labelled_stderr():
    text = body("exit 0: ok", "out one", "out two", STDERR_LABEL, "err one")
    assert split_text(text) == ("exit 0: ok", "out one\nout two\n",
                                "err one\n")


def test_split_text_with_stdout_and_no_label_has_an_empty_stderr():
    text = body("exit 0: ok", "out one")
    assert split_text(text) == ("exit 0: ok", "out one\n", "")


def test_split_text_with_a_label_and_no_stdout_has_an_empty_stdout():
    text = body("exit 2: bad", STDERR_LABEL, "error: no trace matches")
    assert split_text(text) == ("exit 2: bad", "",
                                "error: no trace matches\n")


def test_split_text_with_neither_stream_is_the_header_alone():
    assert split_text("exit 1: no\n") == ("exit 1: no", "", "")
    assert split_text("exit 1: no") == ("exit 1: no", "", "")
    assert split_text("") == ("", "", "")


def test_the_label_only_splits_when_it_is_a_whole_line():
    """A trace's own output may print the label's characters. Splitting
    on a substring would hand the caller half its stdout as stderr."""
    inline = body("exit 0: ok", "a --- stderr --- b", "still stdout")
    assert split_text(inline) == ("exit 0: ok",
                                  "a --- stderr --- b\nstill stdout\n", "")
    longer = body("exit 0: ok", STDERR_LABEL + " and more")
    assert split_text(longer) == ("exit 0: ok",
                                  STDERR_LABEL + " and more\n", "")


def test_the_first_whole_label_line_is_the_one_that_splits():
    text = body("exit 0: ok", "a --- stderr --- b", STDERR_LABEL,
                "E1", STDERR_LABEL, "E2")
    header, out, err = split_text(text)
    assert out == "a --- stderr --- b\n"
    assert err == "E1\n" + STDERR_LABEL + "\nE2\n"


def test_a_stdout_without_its_trailing_newline_keeps_what_it_had():
    """`text_of` adds the newline the label needs; everything before the
    label's own line start belongs to stdout, byte for byte."""
    text = "exit 0: ok\nragged" + "\n" + STDERR_LABEL + "\nE\n"
    assert split_text(text) == ("exit 0: ok", "ragged\n", "E\n")


# ------------------------------------------------------------- the wire

def test_modern_mode_discovers_and_stamps_meta_on_every_request(echo):
    with McpClient(echo) as client:
        echoed = client.request("anything")["echo"]
        assert echoed["_meta"] == {
            META_VERSION: "2026-07-28",
            META_CLIENT: {"name": "sensorium-corpus", "version": "0"},
            META_CAPS: {},
        }
    assert recv(client) == ["server/discover", "anything"]


def test_legacy_mode_initializes_and_then_sends_no_meta(echo):
    with McpClient(echo, mode="legacy", version="2025-03-26") as client:
        assert client.request("anything")["echo"] == {}
    assert recv(client) == ["initialize", "notifications/initialized",
                            "anything"]


def test_meta_true_forces_the_block_a_legacy_client_would_not_send(echo):
    with McpClient(echo, mode="legacy", version="2025-03-26") as client:
        echoed = client.request("anything", meta=True)["echo"]
        assert echoed["_meta"][META_VERSION] == "2025-03-26"


def test_meta_false_drops_the_block_a_modern_client_would_send(echo):
    with McpClient(echo) as client:
        assert client.request("anything", meta=False)["echo"] == {}


def test_a_caller_supplied_meta_is_sent_exactly_as_given(echo):
    """The -32022 and P5 tests craft a deliberately wrong `_meta`; a
    client that merged its own keys into it would repair the very thing
    those tests are trying to send."""
    crafted = {META_VERSION: "1900-01-01"}
    with McpClient(echo) as client:
        echoed = client.request("anything", {"_meta": dict(crafted)})["echo"]
        assert echoed["_meta"] == crafted
        forced = client.request("anything", {"_meta": {}}, meta=True)["echo"]
        assert forced["_meta"] == {}


def test_mode_none_spawns_and_reads_without_any_handshake(echo):
    with McpClient(echo, mode="none") as client:
        assert client.request("anything")["echo"] == {}
        assert client.request("anything", meta=True)["echo"]["_meta"]
    assert recv(client) == ["anything", "anything"]


def test_ids_are_minted_from_one_and_keep_their_json_type(echo):
    with McpClient(echo, mode="none") as client:
        assert client.send("anything") == 1
        assert client.send("anything") == 2
        assert client.wait(1)["id"] == 1
        given = client.send("anything", id="abc")
        assert given == "abc"
        answer = client.wait("abc")
        assert answer["id"] == "abc" and isinstance(answer["id"], str)
        assert client.send("anything") == 3


def test_a_caller_supplied_int_id_moves_the_counter_past_itself(echo):
    with McpClient(echo, mode="none") as client:
        client.send("anything", id=41)
        assert client.send("anything") == 42


def test_bad_lines_collects_a_stdout_line_that_is_not_a_json_object(echo):
    with McpClient(echo, mode="none") as client:
        assert client.request("garbage")["echo"] == {}
    assert client.bad_lines == ["this line is not json"]


def test_an_error_response_raises_mcp_error_with_code_message_and_data(echo):
    with McpClient(echo, mode="none") as client:
        with pytest.raises(McpError) as caught:
            client.request("boom")
        assert caught.value.code == -32602
        assert caught.value.message == "no such thing"
        assert caught.value.data == {"fields": ["regex"]}
        raw = client.wait(client.send("boom"))
        assert raw["error"]["code"] == -32602     # wait never raises on one


def test_call_splits_the_text_and_reads_the_structured_exit(echo):
    text = body("exit 0: the trace answered affirmatively", "out",
                STDERR_LABEL, "warn")
    with McpClient(echo) as client:
        got = client.call("runs", {"text": text, "exit": 0})
    assert isinstance(got, CallResult)
    assert got.header == "exit 0: the trace answered affirmatively"
    assert (got.stdout, got.stderr) == ("out\n", "warn\n")
    assert got.text == text
    assert got.exit == 0 and got.is_error is False
    assert got.raw["echo"]["name"] == "runs"


def test_call_reports_is_error_and_a_missing_structured_exit(echo):
    with McpClient(echo) as client:
        got = client.call("info", {"text": "exit 2: bad\n", "isError": True})
    assert got.is_error is True
    assert got.exit is None
    assert got.header == "exit 2: bad"


def test_call_raises_mcp_error_on_a_protocol_error(echo):
    with McpClient(echo, mode="none") as client:
        client.send("boom", id="pre")             # not a call: just noise
        with pytest.raises(McpError):
            client.request("boom")


def test_list_tools_returns_the_tools_list(echo):
    with McpClient(echo) as client:
        assert [t["name"] for t in client.list_tools()] == ["runs", "info"]


def test_discover_and_initialize_return_their_results(echo):
    with McpClient(echo, mode="none") as client:
        assert client.discover()["resultType"] == "complete"
        assert client.discover()["echo"]["_meta"][META_VERSION] == \
            "2026-07-28"
        assert client.initialize("2025-06-18")["protocolVersion"] == \
            "2025-06-18"
        assert client.initialize("2025-06-18")["echo"].get("_meta") is None


def test_notify_and_cancel_carry_no_id(echo):
    with McpClient(echo, mode="none") as client:
        client.notify("notifications/initialized")
        client.cancel(7)
        client.request("anything")                # a fence: the two landed
    assert recv(client) == ["notifications/initialized",
                            "notifications/cancelled", "anything"]


def test_ping_returns_a_round_trip_in_seconds(echo):
    with McpClient(echo) as client:
        elapsed = client.ping()
    assert isinstance(elapsed, float)
    assert 0 < elapsed < 30


def test_child_pgids_and_handshake_line_read_the_servers_stderr(echo):
    """Both are read while the server is still up -- which is how task
    5b's cancel test reads them -- so both are polled."""
    with McpClient(echo) as client:
        assert eventually(client.child_pgids) == [4243, 4245]
        assert eventually(client.handshake_line) == \
            "handshake discover 2026-07-28"
    assert client.child_pgids() == [4243, 4245]


def test_the_stderr_log_goes_to_the_file_when_a_path_is_given(echo,
                                                              tmp_path):
    path = tmp_path / "server.err"
    with McpClient(echo, stderr_path=path) as client:
        client.request("anything")
        assert client.stderr_lines == []
        assert eventually(client.child_pgids) == [4243, 4245]
    assert client.child_pgids() == [4243, 4245]
    assert client.handshake_line() == "handshake discover 2026-07-28"
    assert "recv anything" in path.read_text(encoding="utf-8")


def test_a_client_with_no_stderr_to_parse_answers_none_and_empty(echo,
                                                                 tmp_path):
    quiet = tmp_path / "quiet.py"
    quiet.write_text("import sys\nfor line in sys.stdin:\n    pass\n",
                     encoding="utf-8")
    with McpClient([sys.executable, str(quiet)], mode="none") as client:
        assert client.child_pgids() == []
        assert client.handshake_line() is None


def test_a_dead_server_fails_every_wait_and_send_with_mcp_error(dead):
    """Bounded on purpose: a client that lost the EOF path would sit in
    `wait` for the full timeout and fail with `TimeoutError`."""
    with McpClient(dead, mode="none") as client:
        with pytest.raises(McpError) as caught:
            client.wait(1, timeout=3)
        assert caught.value.code == -32000
        assert caught.value.message == "server exited (rc=3)"
        with pytest.raises(McpError):
            client.send("anything")
        with pytest.raises(McpError):
            client.request("anything", timeout=3)


def test_a_handshake_that_fails_leaves_no_process_behind(dead):
    """`__enter__` owns what it spawned: a server that dies before it
    can answer `server/discover` is reaped on the way out, not left for
    the interpreter to find at exit."""
    client = McpClient(dead)                  # modern: discover() fails
    with pytest.raises(McpError), client:
        pass                                  # pragma: no cover
    assert client.proc.poll() is not None
    assert client.proc.stdout.closed


def test_an_unanswered_request_times_out_without_killing_the_client(echo):
    with McpClient(echo, mode="none") as client:
        with pytest.raises(TimeoutError):
            client.request("silent", timeout=0.5)
        assert client.request("anything")["echo"] == {}


def test_close_stdin_ends_the_server_and_exit_leaves_nothing_running(echo):
    with McpClient(echo) as client:
        client.close_stdin()
        assert client.proc.wait(5) == 0
        assert client.pid == client.pgid == client.proc.pid
    assert client.proc.poll() is not None
    for pipe in (client.proc.stdin, client.proc.stdout, client.proc.stderr):
        assert pipe is None or pipe.closed


def test_exit_reaps_a_server_that_would_not_leave_on_its_own(tmp_path):
    """The kill ladder: this one ignores EOF and SIGTERM, so `__exit__`
    has to reach SIGKILL for the process to be gone."""
    stubborn = tmp_path / "stubborn.py"
    stubborn.write_text(
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "sys.stderr.write('up\\n'); sys.stderr.flush()\n"
        "time.sleep(120)\n", encoding="utf-8")
    client = McpClient([sys.executable, str(stubborn)], mode="none")
    with client:
        pass
    assert client.proc.poll() is not None


def test_the_wire_is_compact_json_one_message_per_line(echo, tmp_path):
    """What the server's `parse_line` will actually be handed."""
    seen = tmp_path / "seen.jsonl"
    recorder = tmp_path / "recorder.py"
    recorder.write_text(
        "import sys\n"
        "out = open(%r, 'w')\n"
        "for line in sys.stdin:\n"
        "    out.write(line)\n"
        "    out.flush()\n" % str(seen), encoding="utf-8")
    with McpClient([sys.executable, str(recorder)], mode="none") as client:
        client.send("tools/call", {"name": "runs", "arguments": {}},
                    meta=True)
        client.notify("notifications/cancelled", {"requestId": 1})
        client.close_stdin()
        client.proc.wait(5)
    lines = seen.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["method"] == "tools/call"
    assert json.loads(lines[1]) == {
        "jsonrpc": "2.0", "method": "notifications/cancelled",
        "params": {"requestId": 1}}
    assert " " not in lines[1]
