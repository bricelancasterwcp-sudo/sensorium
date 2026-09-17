"""JSON-RPC 2.0 over stdio: one message per line, each way.

The whole transport, and nothing above it. `parse_line` turns a line of
stdin into an `Incoming` or into the three values an error response
needs; `Writer` puts one compact line on stdout under one lock. What a
method MEANS, which era it belongs to and whether it may run a program
are the server's questions -- this module knows only the envelope, and
that is why it can be tested without a process.

WHAT THE PARSER REFUSES, AND WHY EACH GETS ITS OWN CODE. A line that is
not JSON is `-32700`: nothing about it can be trusted, not even its id,
so the response carries `null`. A JSON ARRAY is `-32600` and says so in
words -- batching left the protocol in 2025-06-18, and a client that
sends a batch is not making a typo, it is speaking a revision this
server does not implement; answering `-32700` would send it looking for
a syntax error that is not there. An object with no string `method` is
`-32600` too, but it keeps its id: the client is blocked on that id and
a `null` there would leave it waiting forever. `params` that is present
and not an object is `-32602`, because the envelope was fine and the
payload was not; absent or `null` is `{}`, which is what every caller
in this codebase reads next.

A BLANK LINE IS NOT A MESSAGE. `parse_line` returns `None` for one and
the reader skips it. A trailing newline on a client's last write is not
a malformed request, and answering `-32700` to one would put a line on
stdout that no client is waiting for.

IDS KEEP THEIR JSON TYPE (P21). `Incoming.id` is the parsed value --
`7` stays an int, `"7"` stays a string, and `Writer` echoes back what it
was handed. Normalising to `str` would let a `notifications/cancelled`
naming `"7"` cancel the call whose id is `7`, which is a different
request from a different client loop.

A WRITE IS NEVER A REASON TO DIE. When the client is gone, `write`
raises `BrokenPipeError`, and when our own stdout has been closed
underneath us it raises `ValueError("I/O operation on closed file")`.
Both set `closing` and are swallowed: by then there is nobody to tell,
and a server that raised out of its writer would abandon a live child
instead of running its shutdown. Everything else -- a result holding an
object `json` cannot serialise, say -- is OUR bug and is raised, so the
worker's `except` can answer `-32603` rather than lose the request.
`json.dumps` therefore runs outside the `try` and outside the lock.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass

#: The protocol's own numbers. `-32022` is 2026-07-28's
#: `UnsupportedProtocolVersionError`; the rest are JSON-RPC 2.0's.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
UNSUPPORTED_VERSION = -32022

#: Said in full so a client reading the message learns the revision it
#: is out of step with, not merely that we said no.
_BATCHING = "Invalid Request: batching left the protocol in 2025-06-18"
_NO_METHOD = "Invalid Request: no method"
_BAD_PARAMS = "params must be an object"


@dataclass(frozen=True)
class Incoming:
    """One well-formed message. `notification` is `"id" not in obj` --
    an explicit `"id": null` is a REQUEST whose id happens to be null,
    and it gets an answer; a message with no id key at all gets none."""

    id: object
    method: str
    params: dict
    notification: bool


def parse_line(line: str) -> Incoming | tuple[int, str, object] | None:
    """`Incoming`, or `(code, message, id)`, or `None` for a blank line.

    The tuple is exactly `Writer.error`'s first three arguments, so the
    reader loop never has to decide anything: it writes what it got.
    """
    if not line.strip():
        return None
    try:
        obj = json.loads(line)
    except ValueError:
        return PARSE_ERROR, "Parse error", None
    if isinstance(obj, list):
        return INVALID_REQUEST, _BATCHING, None
    if not isinstance(obj, dict):
        # A bare scalar: valid JSON, and no more a request than `[]` is.
        return INVALID_REQUEST, _NO_METHOD, None
    method = obj.get("method")
    if not isinstance(method, str):
        return INVALID_REQUEST, _NO_METHOD, obj.get("id")
    params = obj.get("params")
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        return INVALID_PARAMS, _BAD_PARAMS, obj.get("id")
    return Incoming(obj.get("id"), method, params, "id" not in obj)


class Writer:
    """Stdout, one JSON-RPC message per line, from any thread.

    The lock is not decoration: the reader thread answers `ping` and
    parse errors while the worker thread answers everything else, and
    two interleaved halves of two messages are two lines no client can
    parse. It covers the flush as well as the write -- a flush between
    somebody else's write and its own would ship a half line.
    """

    def __init__(self, stream) -> None:
        self._stream = stream
        self._lock = threading.Lock()
        self.closing = False

    def result(self, id: object, result: dict) -> None:
        self._write({"jsonrpc": "2.0", "id": id, "result": result})

    def error(self, id: object, code: int, message: str,
              data: object = None) -> None:
        err: dict = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        self._write({"jsonrpc": "2.0", "id": id, "error": err})

    def _write(self, obj: dict) -> None:
        line = json.dumps(obj, separators=(",", ":"),
                          ensure_ascii=False) + "\n"
        with self._lock:
            try:
                self._stream.write(line)
                self._stream.flush()
            except (BrokenPipeError, ValueError):
                self.closing = True
