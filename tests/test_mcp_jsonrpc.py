"""The envelope: one JSON-RPC message per line, in and out.

`jsonrpc.py` is the only code on the branch that touches the wire
bytes, so these tests assert about BYTES and about THREADS -- the two
things a framing layer can get wrong in a way no higher test would
notice. A response that parses but is spelled `{"jsonrpc": "2.0", ...}`
is still a wire change; two responses whose halves interleave are still
valid JSON objects, individually, in the wrong order on one line.

Nothing here spawns a process and nothing imports the server: the
parser is a pure function of a string and the writer is a pure function
of a stream. The end-to-end proof that a real client can read what
`Writer` writes lives in `tests/test_mcp_client.py`.

WHY `HalfWriter` AND NOT `io.StringIO`. `StringIO.write` is one atomic
C call: two threads writing whole lines to one StringIO produce whole
lines whether or not a lock is held, so a lock mutant would survive
that test forever. `HalfWriter` writes each string in two pieces with a
real sleep between them -- which is what any stream that can block
mid-write (a pipe, a full buffer) does to an unlocked writer.

PRE-REGISTERED MUTATIONS (task 5a, step 7), each with the test that
catches it:

* `json.dumps(..., separators=(", ", ": "))` (the module default) ->
  `test_a_result_is_one_compact_line_byte_for_byte`. The line still
  parses, and every test that went through `json.loads` would pass; the
  wire grew a space per key for every message the server will ever
  write.
* drop the `threading.Lock` around write + flush ->
  `test_two_threads_writing_at_once_never_split_a_line`. It is a race,
  so the mutant is run five times and the count is in the report.
* delete the array branch (fall through to the object path) ->
  `test_an_array_is_invalid_request_because_batching_is_gone`. The
  mutant lands in the not-a-dict branch and answers the right CODE with
  the wrong sentence: a client that sent a batch is told it forgot a
  `method`, and goes looking for a bug in a message that had one.
"""
from __future__ import annotations

import dataclasses
import io
import json
import threading
import time

import pytest

from sensorium.mcp.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    UNSUPPORTED_VERSION,
    Incoming,
    Writer,
    parse_line,
)

BATCHING = "Invalid Request: batching left the protocol in 2025-06-18"
NO_METHOD = "Invalid Request: no method"


class HalfWriter:
    """A stream that can be interrupted mid-write. See the module
    docstring for why the lock test cannot use `io.StringIO`."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.flushes = 0

    def write(self, s: str) -> int:
        half = len(s) // 2
        self.parts.append(s[:half])
        time.sleep(0.0005)
        self.parts.append(s[half:])
        return len(s)

    def flush(self) -> None:
        self.flushes += 1

    def text(self) -> str:
        return "".join(self.parts)


class Exploder:
    """A stream whose every write fails the way a gone client's does."""

    def __init__(self, exc: BaseException) -> None:
        self.exc = exc
        self.writes = 0

    def write(self, s: str) -> int:
        self.writes += 1
        raise self.exc

    def flush(self) -> None:
        pass


# --------------------------------------------------------------- codes

def test_the_codes_are_the_protocols_own_numbers():
    assert (PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS,
            INTERNAL_ERROR, UNSUPPORTED_VERSION) == (
        -32700, -32600, -32601, -32602, -32603, -32022)


# -------------------------------------------------------------- parsing

def test_a_request_parses_into_id_method_and_params():
    inc = parse_line(
        '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"a":1}}')
    assert isinstance(inc, Incoming)
    assert inc.id == 1
    assert inc.method == "tools/list"
    assert inc.params == {"a": 1}
    assert inc.notification is False


def test_a_message_with_no_id_key_is_a_notification():
    inc = parse_line('{"jsonrpc":"2.0","method":"notifications/initialized"}')
    assert inc.notification is True
    assert inc.id is None
    assert inc.params == {}


def test_an_explicit_null_id_is_a_request_and_not_a_notification():
    """`"id": null` is a key that is present: the server answers it (with
    a null id), rather than silently dropping a message a client is
    blocked on."""
    inc = parse_line('{"jsonrpc":"2.0","id":null,"method":"ping"}')
    assert inc.notification is False
    assert inc.id is None


def test_an_id_keeps_its_json_type():
    """P21. A string id stays a string and an int stays an int, all the
    way from this function to the `Writer` that echoes it."""
    assert parse_line('{"id":"abc","method":"ping"}').id == "abc"
    seven = parse_line('{"id":7,"method":"ping"}').id
    assert seven == 7 and isinstance(seven, int)


def test_incoming_is_frozen():
    inc = parse_line('{"id":1,"method":"ping"}')
    with pytest.raises(dataclasses.FrozenInstanceError):
        inc.method = "tools/list"


def test_a_line_that_is_not_json_is_a_parse_error_with_no_id():
    assert parse_line('{"id":1,"method":') == (PARSE_ERROR, "Parse error",
                                               None)
    assert parse_line("\xff not json at all\n") == (PARSE_ERROR,
                                                    "Parse error", None)


def test_an_array_is_invalid_request_because_batching_is_gone():
    assert parse_line('[{"jsonrpc":"2.0","id":1,"method":"ping"}]') == (
        INVALID_REQUEST, BATCHING, None)
    assert parse_line("[]") == (INVALID_REQUEST, BATCHING, None)


def test_an_object_without_a_string_method_is_invalid_request_with_its_id():
    assert parse_line('{"jsonrpc":"2.0","id":4}') == (INVALID_REQUEST,
                                                      NO_METHOD, 4)
    assert parse_line('{"id":"x","method":5}') == (INVALID_REQUEST,
                                                   NO_METHOD, "x")
    assert parse_line('{"method":null}') == (INVALID_REQUEST, NO_METHOD, None)


def test_a_bare_json_scalar_is_invalid_request_with_no_id():
    assert parse_line("5") == (INVALID_REQUEST, NO_METHOD, None)
    assert parse_line('"ping"') == (INVALID_REQUEST, NO_METHOD, None)


def test_params_absent_or_null_is_an_empty_dict():
    assert parse_line('{"id":1,"method":"ping"}').params == {}
    assert parse_line('{"id":1,"method":"ping","params":null}').params == {}


def test_params_that_is_not_an_object_is_invalid_params_with_its_id():
    assert parse_line('{"id":1,"method":"ping","params":5}') == (
        INVALID_PARAMS, "params must be an object", 1)
    assert parse_line('{"id":"a","method":"ping","params":[1]}') == (
        INVALID_PARAMS, "params must be an object", "a")


def test_a_blank_line_is_nothing_at_all():
    """The reader skips these rather than answering -32700: a trailing
    newline on a client's last write is not a malformed message."""
    assert parse_line("") is None
    assert parse_line("\n") is None
    assert parse_line("   \t \r\n") is None


# -------------------------------------------------------------- writing

def test_a_result_is_one_compact_line_byte_for_byte():
    stream = io.StringIO()
    Writer(stream).result(1, {"a": 1})
    assert stream.getvalue() == '{"jsonrpc":"2.0","id":1,"result":{"a":1}}\n'


def test_an_error_is_one_compact_line_byte_for_byte():
    stream = io.StringIO()
    w = Writer(stream)
    w.error(1, INVALID_PARAMS, "params must be an object")
    w.error(None, PARSE_ERROR, "Parse error")
    w.error("x", UNSUPPORTED_VERSION, "Unsupported protocol version",
            {"supported": ["2026-07-28"], "requested": "1900-01-01"})
    assert stream.getvalue() == (
        '{"jsonrpc":"2.0","id":1,"error":{"code":-32602,'
        '"message":"params must be an object"}}\n'
        '{"jsonrpc":"2.0","id":null,"error":{"code":-32700,'
        '"message":"Parse error"}}\n'
        '{"jsonrpc":"2.0","id":"x","error":{"code":-32022,'
        '"message":"Unsupported protocol version","data":'
        '{"supported":["2026-07-28"],"requested":"1900-01-01"}}}\n')


def test_data_is_omitted_when_it_is_none_and_kept_when_it_is_falsey():
    stream = io.StringIO()
    Writer(stream).error(1, INTERNAL_ERROR, "Internal error", {})
    assert stream.getvalue() == (
        '{"jsonrpc":"2.0","id":1,"error":{"code":-32603,'
        '"message":"Internal error","data":{}}}\n')


def test_the_writer_echoes_an_id_with_its_json_type():
    """P21, the other half of it: `"abc"` comes back quoted and `7`
    comes back bare, so a client keyed on the JSON value finds them."""
    stream = io.StringIO()
    w = Writer(stream)
    w.result("abc", {})
    w.result(7, {})
    assert stream.getvalue() == ('{"jsonrpc":"2.0","id":"abc","result":{}}\n'
                                 '{"jsonrpc":"2.0","id":7,"result":{}}\n')


def test_non_ascii_goes_out_as_an_escape_and_decodes_back_to_itself():
    """`ensure_ascii=True` (C2): the wire is ASCII and what the client
    reads back is the string we sent, escape or no escape."""
    stream = io.StringIO()
    Writer(stream).result(1, {"text": "café ✓ 日本語"})
    line = stream.getvalue()
    assert line.isascii()
    assert json.loads(line)["result"]["text"] == "café ✓ 日本語"


def test_a_lone_surrogate_reaches_the_client_as_an_escape(tmp_path):
    """C2. A method name and a tool name are model-typed text, and a
    tokenizer that split an emoji hands us half a surrogate pair.
    Serialised with `ensure_ascii=False` that string cannot be encoded
    onto a UTF-8 stdout; the `UnicodeEncodeError` (a `ValueError`) was
    swallowed as if the pipe had gone, and the client waited on that id
    forever. Escaped, it is six ASCII characters and the answer goes."""
    stream = io.StringIO()
    w = Writer(stream)
    w.result(2, {"text": "Method not found: \ud800"})
    line = stream.getvalue()
    assert line == ('{"jsonrpc":"2.0","id":2,'
                    '"result":{"text":"Method not found: \\ud800"}}\n')
    assert line.isascii() and w.closing is False
    assert json.loads(line)["result"]["text"] == "Method not found: \ud800"
    # And it survives a real UTF-8 stream, which is what stdout is.
    handle = tmp_path / "wire.txt"
    handle.write_text(line, encoding="utf-8")
    assert json.loads(handle.read_text(encoding="utf-8"))["id"] == 2


def test_an_encoding_failure_on_an_OPEN_stream_is_raised_not_swallowed():
    """C2's other half: `closing` is for a client that has gone. A
    `ValueError` off a stream that is not closed is OUR bug and must
    reach the worker's `-32603`, as an unserialisable result does."""
    stream = Exploder(UnicodeEncodeError("utf-8", "\ud800", 0, 1, "surrogate"))
    w = Writer(stream)
    with pytest.raises(UnicodeEncodeError):
        w.result(1, {})
    assert w.closing is False
    with pytest.raises(ValueError):
        Writer(Exploder(ValueError("something else entirely"))).result(1, {})


def test_every_write_is_flushed_and_is_exactly_one_line():
    stream = HalfWriter()
    w = Writer(stream)
    w.result(1, {"a": 1})
    w.error(2, METHOD_NOT_FOUND, "Method not found: nope")
    assert stream.flushes == 2
    assert stream.text().count("\n") == 2
    assert stream.text().endswith("\n")


def test_two_threads_writing_at_once_never_split_a_line():
    stream = HalfWriter()
    w = Writer(stream)

    def run(base: int) -> None:
        for i in range(200):
            w.result(base + i, {"a": "x" * 16})

    threads = [threading.Thread(target=run, args=(base,))
               for base in (0, 1000)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    lines = stream.text().splitlines()
    assert len(lines) == 400
    assert sorted(json.loads(line)["id"] for line in lines) == sorted(
        list(range(200)) + list(range(1000, 1200)))


# -------------------------------------------------------------- closing

def test_a_broken_pipe_sets_closing_and_is_not_raised():
    stream = Exploder(BrokenPipeError(32, "Broken pipe"))
    w = Writer(stream)
    assert w.closing is False
    w.result(1, {})
    assert w.closing is True
    w.error(2, INTERNAL_ERROR, "Internal error")   # still never raises
    assert stream.writes == 2


def test_writing_to_a_closed_stream_sets_closing_and_is_not_raised():
    """The real one, not a mock: a closed `TextIOWrapper` raises
    `ValueError("I/O operation on closed file")`, which is what the
    server's stdout does when the client goes away mid-shutdown."""
    stream = io.StringIO()
    stream.close()
    w = Writer(stream)
    w.result(1, {})
    assert w.closing is True


def test_an_unserialisable_result_is_a_bug_and_is_raised():
    """`closing` is for a gone client, not for a server that built a
    result it cannot send: that one must reach the worker's `except`
    and be answered -32603 rather than vanishing."""
    stream = io.StringIO()
    with pytest.raises(TypeError):
        Writer(stream).result(1, {"o": object()})
    assert stream.getvalue() == ""
