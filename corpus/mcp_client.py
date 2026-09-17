"""A minimal MCP stdio client: the standard library and a subprocess.

`tests/test_mcp_server.py`, the corpus's `--via mcp` mode and the E17
instrument all talk to the server through this class. It exists because
the official SDK is correct by construction -- valid `_meta`, ids it
owns, never an unsupported version -- and those are the requests the
server's era rules must be tested with. Hence: A CALLER'S OWN `_meta`
IS SENT AS GIVEN, never merged.

On the wire (verified against the official Python SDK 2.2.0, task 5's
wire facts) `modern` is `server/discover` then `_meta` -- version,
`clientInfo`, empty capabilities -- on every request, ids minted from
1; `legacy` is `initialize`, `notifications/initialized` then no
`_meta` at all (the SDK sends `{}`; both read as legacy to a server
keyed off the version key's ABSENCE); `none` spawns and reads.
`STDERR_LABEL` is imported, never copied: a copy would go stale.

A CALL'S EXIT IS READ OFF THE HEADER LINE (R18), never off
`structuredContent`: this server sends none, and one that did would not
be believed over the text the model itself is reading.

Three threads -- the caller's writes, one resolving futures off stdout,
one that ALWAYS drains stderr (into `stderr_path`, else into memory)
because a pipe nobody reads fills up and blocks the server inside
`log()`. NOTHING THE SERVER WRITES IS DROPPED (R13): a line that is not
a JSON object -- blank lines included -- lands in `bad_lines`, and an
object with no id of its own (a `-32700` answered `"id": null`, a
notification) lands in `unaddressed`, which `wait(None)` drains oldest
first -- binning either hides a server that answers the wrong shape.
DEATH IS AN ANSWER: on EOF or a read error every pending and every
future call fails at once with `McpError(-32000, "server exited
(rc=<n>)")` -- hanging futures would turn a server crash into a
60-second timeout, and a `BrokenPipeError` would blame the caller.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from sensorium.mcp.result import STDERR_LABEL

#: 2026-07-28's per-request protocol fields, as a CLIENT writes them.
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CLIENT = "io.modelcontextprotocol/clientInfo"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"

#: The server's spawn line -- where a test learns the group to watch --
#: and `GONE`, which is not a protocol code: the client made that one up
#: to say "there is no server".
CHILD_LINE = re.compile(r"sensorium mcp: child (\d+) pgid (\d+) tool \S+")
LOG_PREFIX = "sensorium mcp: "
HANDSHAKE = LOG_PREFIX + "handshake "
GONE = -32000

#: The header form that reports a status (D19). Everything else -- a
#: `no answer:` line, or a first line that is neither -- is no exit.
EXIT_HEADER = re.compile(r"exit (-?\d+): ")


class McpError(Exception):
    """A JSON-RPC error response, or the server's absence."""
    def __init__(self, code: int, message: str, data: object = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.data = code, message, data


@dataclass
class CallResult:
    """One `tools/call` answer, split the way the corpus compares it."""
    raw: dict
    text: str
    header: str
    stdout: str
    stderr: str
    exit: int | None
    is_error: bool


def split_text(text: str) -> tuple[str, str, str]:
    """`(header, stdout, stderr)` out of a result's one text block.

    The header is the first line -- always, by D19. The rest splits at
    the FIRST line that is exactly `STDERR_LABEL`: that line is dropped,
    what precedes its start is stdout (so a stdout that ended in a
    newline keeps it), what follows its newline is stderr. A line that
    merely CONTAINS the label is stdout -- splitting on a substring
    would hand the caller half its stdout under the wrong name.
    """
    nl = text.find("\n")
    if nl < 0:
        return text, "", ""
    header, rest = text[:nl], text[nl + 1:]
    parts = rest.split("\n")            # "\n" only: `splitlines` also cuts
    for i, part in enumerate(parts):    # at \r and \f, which stdout may hold
        if part == STDERR_LABEL:
            out = "\n".join(parts[:i]) + "\n" if i else ""
            return header, out, "\n".join(parts[i + 1:])
    return header, rest, ""


class McpClient:
    """A server process and the conversation with it."""
    def __init__(self, argv: list[str], cwd=None, env: dict | None = None,
                 stderr_path=None, mode: str = "modern",
                 version: str = "2026-07-28",
                 client_name: str = "sensorium-corpus") -> None:
        self.argv, self.cwd, self.env, self.mode = list(argv), cwd, env, mode
        self.version, self.client_name = version, client_name
        self.stderr_path = None if stderr_path is None else Path(stderr_path)
        self.proc = self.pid = self.pgid = None
        self.bad_lines, self.unaddressed, self.stderr_lines = [], [], []
        self._threads, self._answers, self._dead = [], {}, None
        self._cond, self._next_id = threading.Condition(), 1

    def __enter__(self) -> "McpClient":
        self.proc = subprocess.Popen(
            self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
            start_new_session=True, env=self.env,
            cwd=None if self.cwd is None else str(self.cwd))
        self.pid = self.pgid = self.proc.pid      # start_new_session: leader
        self._threads = [threading.Thread(target=fn, daemon=True) for fn in
                         (self._read_stdout, self._drain_stderr)]
        for thread in self._threads:
            thread.start()
        try:
            if self.mode == "modern":
                self.discover()
            elif self.mode == "legacy":
                self.initialize(self.version)
                self.notify("notifications/initialized")
        except BaseException:            # a boot that fails leaks nothing
            self.__exit__()
            raise
        return self

    def __exit__(self, *exc) -> None:
        """EOF, the kill ladder, the threads, the pipes, in that order."""
        self.close_stdin()
        for sig, grace in ((None, 5), (signal.SIGTERM, 2),
                           (signal.SIGKILL, 2)):
            if sig is not None:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(self.pgid, sig)
            try:
                self.proc.wait(grace)
                break
            except subprocess.TimeoutExpired:
                continue
        for thread in self._threads:
            thread.join(5)
        for pipe in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            with contextlib.suppress(Exception):
                pipe.close()

    def close_stdin(self) -> None:
        """Only the server's stdin: the EOF tests need that alone."""
        with contextlib.suppress(OSError, ValueError):
            self.proc.stdin.close()      # a second close is a no-op

    def _read_stdout(self) -> None:
        try:
            for raw in self.proc.stdout:
                line = raw.strip()
                try:
                    obj = json.loads(line) if line else None
                except ValueError:
                    obj = None
                if not isinstance(obj, dict):
                    self.bad_lines.append(line)   # a blank line included
                    continue
                with self._cond:
                    if obj.get("id") is None:
                        self.unaddressed.append(obj)
                    else:
                        self._answers[obj["id"]] = obj
                    self._cond.notify_all()
        except Exception:                 # a read error is EOF with a cause
            pass
        finally:
            self._die()

    def _drain_stderr(self) -> None:
        handle = None
        try:
            if self.stderr_path is not None:
                handle = open(self.stderr_path, "w", encoding="utf-8",
                              buffering=1)
        except OSError as err:           # drain to memory rather than not
            self.stderr_lines.append(f"[no {self.stderr_path}: {err}]")
        keep = handle.write if handle is not None else (
            lambda line: self.stderr_lines.append(line.rstrip("\n")))
        try:
            for line in self.proc.stderr:
                keep(line)
        except Exception:
            pass
        finally:
            if handle is not None:
                handle.close()

    def _die(self) -> None:
        rc = self.proc.poll()            # the absence, published once
        with contextlib.suppress(subprocess.TimeoutExpired):
            rc = self.proc.wait(2) if rc is None else rc
        with self._cond:
            if self._dead is None:
                self._dead = (GONE, f"server exited (rc={rc})", None)
            self._cond.notify_all()

    def _line(self, msg: dict) -> None:
        with self._cond:
            if self._dead is not None:
                raise McpError(*self._dead)
        text = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
        try:
            self.proc.stdin.write(text + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError):
            self._die()                # EPIPE: the server is already gone
            with self._cond:
                raise McpError(*self._dead) from None

    def send(self, method: str, params: dict | None = None, *,
             meta: bool | None = None, id: object = None) -> object:
        """Write one request and return its id, without waiting."""
        out = dict(params) if params else {}
        want = (self.mode == "modern") if meta is None else meta
        if want and "_meta" not in out:
            out["_meta"] = {META_VERSION: self.version,
                            META_CLIENT: {"name": self.client_name,
                                          "version": "0"}, META_CAPS: {}}
        with self._cond:                 # two senders cannot mint one id
            id = self._next_id if id is None else id
            if isinstance(id, int) and not isinstance(id, bool):
                self._next_id = max(self._next_id, id + 1)
        self._line({"jsonrpc": "2.0", "id": id, "method": method,
                    "params": out})
        return id

    def notify(self, method: str, params: dict | None = None) -> None:
        msg = {"jsonrpc": "2.0", "method": method}
        self._line(msg if params is None else {**msg, "params": params})

    def wait(self, id: object, timeout: float = 60) -> dict:
        """The raw response for `id`: a result, an error, or death.

        `wait(None)` takes the oldest object the server wrote with no id
        of its own -- a `-32700` answered `"id": null`, a notification --
        in the order they arrived. This client never sends a null id, so
        the two queues cannot collide."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                if id is None and self.unaddressed:
                    return self.unaddressed.pop(0)
                if id is not None and id in self._answers:
                    return self._answers.pop(id)
                if self._dead is not None:
                    raise McpError(*self._dead)
                left = deadline - time.monotonic()
                if left <= 0:
                    raise TimeoutError(f"no answer to id {id!r} "
                                       f"in {timeout} s")
                self._cond.wait(left)

    def request(self, method: str, params: dict | None = None,
                timeout: float = 60, **kw) -> dict:
        answer = self.wait(self.send(method, params, **kw), timeout)
        err = answer.get("error")
        if err is not None:
            raise McpError(err.get("code"), err.get("message"),
                           err.get("data"))
        return answer.get("result")

    def discover(self) -> dict:
        return self.request("server/discover", meta=True)

    def initialize(self, version: str) -> dict:
        return self.request("initialize", meta=False, params={
            "protocolVersion": version, "capabilities": {},
            "clientInfo": {"name": self.client_name, "version": "0"}})

    def list_tools(self) -> list[dict]:
        return self.request("tools/list")["tools"]

    def call(self, name: str, arguments: dict,
             timeout: float = 600) -> CallResult:
        result = self.request("tools/call",
                              {"name": name, "arguments": arguments}, timeout)
        text = result["content"][0]["text"]
        header, out, err = split_text(text)
        status = EXIT_HEADER.match(header)
        return CallResult(
            raw=result, text=text, header=header, stdout=out, stderr=err,
            exit=int(status.group(1)) if status else None,
            is_error=bool(result.get("isError")))

    def cancel(self, id: object) -> None:
        self.notify("notifications/cancelled",
                    {"requestId": id, "reason": "test"})

    def ping(self) -> float:
        started = time.monotonic()
        self.request("ping")
        return time.monotonic() - started

    def _stderr(self) -> list[str]:
        if self.stderr_path is not None:
            with contextlib.suppress(OSError):
                return self.stderr_path.read_text("utf-8").splitlines()
        return list(self.stderr_lines)

    def child_pgids(self) -> list[int]:
        found = (CHILD_LINE.search(line) for line in self._stderr())
        return [int(m.group(2)) for m in found if m]

    def handshake_line(self) -> str | None:
        """The server's handshake log line, minus the `log()` prefix."""
        hit = [line for line in self._stderr() if HANDSHAKE in line]
        return hit[0].split(LOG_PREFIX, 1)[1] if hit else None
