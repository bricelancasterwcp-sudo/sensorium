"""The MCP server: two threads, two eras, one way out.

TWO THREADS. The calling thread reads stdin and answers two things
itself: `ping`, because a liveness check queued behind a three-minute
`record` would report the server dead while it was working, and
`notifications/cancelled`, whose point is to reach a call the worker is
blocked inside. Everything else is queued on one `deque` behind one
`Condition` for one daemon worker -- serialised on purpose (D14): the
store is SQLite and a call is a child process, so the honest offer is
one question at a time.

THE ONE CRITICAL SECTION. The worker pops a request and publishes the
`Child` it will spawn -- `_inflight = (id, child)` -- without releasing
the Condition in between, and the reader reads `_inflight` under the
same lock: a cancel arriving in a gap between the two would find the
request in neither place and be lost. The child is published BEFORE it
is spawned for the same reason, which is why `Child.run` re-reads the
cancelled flag under its own lock after `Popen`. Everything but the
spawn is decided AND answered inside that section -- microseconds of
work, and a gap is the bug.

THE WORKER OWNS THE SESSION, so the era rules need no second lock for
state with exactly one writer, and the reader's two methods need no
session at all (`ping` is exempt from the era check; a cancel names an
id). No request takes the worker down either: an exception becomes one
stderr line and a `-32603` naming the class. Pipe errors are not among
them -- `Writer` swallows those into `closing`, because by then there
is nobody to tell.

TWO ERAS ON ONE PROCESS (spec §3, P5). A request whose `_meta` carries
`io.modelcontextprotocol/protocolVersion` is served statelessly under
2026-07-28's per-request model; one without that key is legacy and
needs `initialize` to have happened -- `initialize` and `ping` are the
only methods exempt from the check. The key's ABSENCE is what decides,
never its value: the SDK sends `"_meta": {}` on every legacy request,
and keying off emptiness would read those as modern.

ONE SHUTDOWN PATH. `serve()`'s `finally` -- reached by EOF, by the
`SystemExit` the SIGTERM handler raises, by `KeyboardInterrupt`, by a
broken pipe or by a bug -- ignores SIGTERM, marks the writer closing,
closes the queue, kills the in-flight child's group and joins the
worker. The handler does three things and none is the kill: one that
ran `Child.cancel()` would re-enter a kill already in its grace wait,
on the thread holding that child's lock, and hang. The join is not
tidiness -- a daemon thread mid-write at interpreter finalisation
prints a traceback onto the client's stdout.
"""
from __future__ import annotations

import collections
import importlib.metadata
import os
import signal
import sys
import threading
from dataclasses import dataclass

from sensorium import paths
from sensorium.mcp import audit, jsonrpc, result, tools
from sensorium.mcp.child import Child
from sensorium.mcp.jsonrpc import Incoming, Writer, parse_line
from sensorium.mcp.schema import Rejection
from sensorium.mcp.tools import Tool

#: Every revision this server answers, newest first: the per-request
#: era, then the three `initialize` ones. `STRUCTURED_LEGACY` is the
#: legacy pair that knows `Tool.title` (no result carries structured
#: content and no tool an output schema: R18, and `result.py` says why).
SUPPORTED = ("2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26")
LEGACY = SUPPORTED[1:]
LEGACY_LATEST = "2025-11-25"
STRUCTURED_LEGACY = ("2025-06-18", "2025-11-25")

#: 2026-07-28's per-request protocol fields, and the one we answer with.
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPS = "io.modelcontextprotocol/clientCapabilities"
META_SERVER = "io.modelcontextprotocol/serverInfo"

#: How long a listing may be cached, and by whom -- private: the tools
#: are THIS process's CLI over one developer's store. `COMPLETE` is the
#: only `resultType` we send: we never stream.
TTL_MS = 3600000
CACHE_SCOPE = "private"
COMPLETE = "complete"
NAME = "sensorium"

#: Spec §3.3 (D15, P29): what the model does not get from its prior,
#: sent with both handshakes, pinned under 800 characters by a test. The
#: last sentence is this deployment's, not the spec paragraph's.
INSTRUCTIONS = (
    "sensorium answers debugging questions from a recorded execution "
    "trace. Start with `runs`, then `info` on the run you mean; `last` is "
    "the newest trace and the default. Event ids eN and frame ids fN "
    "printed by one answer are valid arguments to the next. Every result "
    "begins with an exit line: 0 answered, 1 the trace says no or none, 2 "
    "fix the arguments and ask again, 3 the trace cannot settle it and "
    "only a new recording can. Never repeat a 3 on the same run; never "
    "re-record on a 2. Two plays: a wrong value or a swallowed error is "
    "`exceptions`, then `frame` on the guilty fN, then `tree` with "
    "`around` set to the parent's event id; a flaky or "
    "environment-dependent test is two recordings and `diff`. `record` "
    "and `refocus` execute your program and exist only under "
    "`--allow-run`.")

#: The refusals that are this module's own words.
_BAD_CALL_PARAMS = "tools/call needs a string name and an object arguments"
_NOT_INITIALIZED = ("not initialized: send initialize or server/discover "
                    "first, or carry _meta protocolVersion")
_NO_DISCOVER_META = "server/discover needs _meta protocolVersion"

#: What the worker pops when it is time to stop. Not `None`: a request
#: whose id is null is a real request and must not read alike.
_DONE = object()


@dataclass
class Options:
    """This process's policy (§6). `store` reaches the children as
    `SENSORIUM_DIR`, which `cmd.run` sets for us (D16, P9)."""

    allow_run: bool = False
    store: str | None = None
    max_output: int = 65536
    timeout: float = 60.0
    run_timeout: float = 600.0


@dataclass
class Session:
    """The legacy era's state, owned by the worker: what `initialize`
    settled on, and whether the modern probe was answered."""

    legacy_version: str | None = None
    discovered: bool = False


@dataclass(frozen=True)
class _Call:
    """A call decided inside the critical section -- so `child` can be
    published with the pop -- and run outside it."""

    tool: Tool
    arguments: dict
    child: Child
    modern: bool


def version() -> str:
    """This package's version, or `?` when it is not installed."""
    try:
        return importlib.metadata.version("sensorium")
    except importlib.metadata.PackageNotFoundError:
        return "?"


class Server:
    """One conversation on one pair of pipes."""

    def __init__(self, options: Options, stdin, stdout, stderr,
                 table: dict[str, Tool] | None = None) -> None:
        self.options = options
        self._stdin, self._stderr = stdin, stderr
        self.writer = Writer(stdout)
        self.table = (tools.table(options.allow_run) if table is None
                      else table)     # P22: once, before any thread exists
        self.session = Session()
        self._cond = threading.Condition()
        self._queue: collections.deque = collections.deque()
        self._inflight: tuple[object, Child] | None = None

    # -- the reader thread --------------------------------------------------
    def serve(self) -> int:
        """Read stdin until it ends, then shut down. Always 0."""
        self.log(f"serving {len(self.table)} tools "
                 f"(allow_run={self.options.allow_run}) "
                 f"store={paths.trace_root()}")
        if audit.disabled():
            self.log("audit off (SENSORIUM_NO_INVOCATION_LOG)")
        worker = threading.Thread(target=self._work, daemon=True,
                                  name="sensorium-mcp-worker")
        worker.start()
        try:
            self._read()
        finally:
            self._shutdown(worker)
        return 0

    def log(self, msg: str) -> None:
        """The only writer of stderr; stdout is JSON-RPC and nothing
        else. A diagnostic is never a reason to lose a call."""
        try:
            self._stderr.write(f"sensorium mcp: {msg}\n")
            self._stderr.flush()
        except (BrokenPipeError, ValueError):
            pass

    def _read(self) -> None:
        for line in self._stdin:
            message = parse_line(line)
            if message is None:
                continue       # a blank line or a dropped notification
            if not isinstance(message, Incoming):
                code, text, id_ = message     # parse_line's own refusal
                self.writer.error(id_, code, text)
            elif message.notification:
                if message.method == "notifications/cancelled":
                    self._cancel(message.params)
            elif message.method == "ping":
                self.writer.result(
                    message.id, self._modern({"resultType": COMPLETE})
                    if _is_modern(message.params) else {})
            else:
                with self._cond:
                    self._queue.append(message)
                    self._cond.notify()

    def _cancel(self, params: dict) -> None:
        """P21: the id is compared as the JSON value it arrived as --
        `"7"` is not the call whose id is `7`. The kill runs here and
        may hold this thread for the child's grace period: accepted,
        since the only thing behind it is another cancel."""
        if "requestId" not in params:
            return
        wanted, queued = params["requestId"], None
        with self._cond:
            flying = self._inflight
            child = (flying[1] if flying is not None
                     and flying[0] == wanted else None)
            for index, waiting in enumerate(self._queue):
                if child is None and waiting is not _DONE \
                        and waiting.id == wanted:
                    queued = waiting
                    del self._queue[index]
                    break
        if child is not None:
            child.cancel()
        elif queued is not None:
            # Nothing was spawned, so there is no duration to report.
            audit.record_cancel(queued.params.get("name"),
                                _arguments(queued.params), True, None)

    def _shutdown(self, worker: threading.Thread) -> None:
        """The one way out, from EOF, SIGTERM, Ctrl-C or a bug."""
        _ignore_sigterm()      # a second SIGTERM must not unwind the kill
        self.writer.closing = True
        with self._cond:
            # One hold for both: apart, the worker could pop and publish
            # a new child between them, killed by nobody.
            flying = self._inflight
            self._queue.clear()         # whatever is left will not be served
            self._queue.append(_DONE)
            self._cond.notify()
        if flying is not None:
            flying[1].cancel()          # the full kill, on this thread
        worker.join(5.0)

    # -- the worker thread --------------------------------------------------
    def _work(self) -> None:
        while True:
            failure: Exception | None = None
            call: _Call | None = None
            with self._cond:
                while not self._queue:
                    self._cond.wait()
                message = self._queue.popleft()
                if message is _DONE:
                    return
                try:
                    call = self._plan(message)
                except Exception as exc:           # our bug, not theirs
                    failure = exc
                if call is not None:
                    self._inflight = (message.id, call.child)
            try:
                if call is not None:
                    self._run(message, call)
            except Exception as exc:
                failure = exc
            finally:
                with self._cond:
                    self._inflight = None
            if failure is not None:
                self.log(f"internal error on {message.method} id "
                         f"{message.id}: {type(failure).__name__}: {failure}")
                self.writer.error(message.id, jsonrpc.INTERNAL_ERROR,
                                  "Internal error",
                                  {"type": type(failure).__name__})

    def _plan(self, message: Incoming) -> _Call | None:
        """Answer `message`, or hand back the call left to run. `None`
        is "answered": what `writer.result` and `_fault` return."""
        params = message.params
        modern = _is_modern(params)
        if message.method == "initialize":
            return self.writer.result(message.id, self._initialize(params))
        if message.method == "server/discover" and not modern:
            return self._fault(message, jsonrpc.INVALID_PARAMS,
                               _NO_DISCOVER_META)
        if not self._era_ok(message, params, modern):
            return None
        structured = modern or self.session.legacy_version in STRUCTURED_LEGACY
        if message.method == "server/discover":
            return self.writer.result(message.id, self._discover(params))
        if message.method == "tools/list":
            return self.writer.result(message.id,
                                      self._listing(structured, modern))
        if message.method == "tools/call":
            return self._plan_call(message, modern)
        return self._fault(message, jsonrpc.METHOD_NOT_FOUND,
                           f"Method not found: {message.method}")

    def _fault(self, message: Incoming, code: int, text: str,
               data: object = None) -> None:
        self.writer.error(message.id, code, text, data)

    def _era_ok(self, message: Incoming, params: dict, modern: bool) -> bool:
        """P5. False means refused, with nothing left to do."""
        if not modern:
            if self.session.legacy_version is None:
                self._fault(message, jsonrpc.INVALID_PARAMS, _NOT_INITIALIZED)
                return False
            return True
        offered = _meta(params)[META_VERSION]
        if offered not in SUPPORTED:
            self._fault(message, jsonrpc.UNSUPPORTED_VERSION,
                        "Unsupported protocol version",
                        {"supported": list(SUPPORTED), "requested": offered})
            return False
        if META_CAPS not in _meta(params):
            self._fault(message, jsonrpc.INVALID_PARAMS,
                        f"missing _meta key {META_CAPS}")
            return False
        return True

    def _initialize(self, params: dict) -> dict:
        """P27: the offered version is echoed iff we speak it. Offering
        `2026-07-28` here is a confused client -- that revision has no
        `initialize` -- and is answered the newest legacy one, as an
        unknown date is: echoing anything offered would claim a revision
        we cannot speak."""
        offered = params.get("protocolVersion")
        answered = offered if offered in LEGACY else LEGACY_LATEST
        self.session.legacy_version = answered
        self.log(f"handshake initialize {offered} -> {answered}")
        return {"protocolVersion": answered,
                "capabilities": {"tools": {}},
                "serverInfo": self._info(),
                "instructions": INSTRUCTIONS}

    def _discover(self, params: dict) -> dict:
        self.session.discovered = True
        self.log(f"handshake discover {_meta(params)[META_VERSION]}")
        return {"resultType": COMPLETE,
                "supportedVersions": list(SUPPORTED),
                "capabilities": {"tools": {}},
                "instructions": INSTRUCTIONS,
                "ttlMs": TTL_MS, "cacheScope": CACHE_SCOPE,
                "_meta": {META_SERVER: self._info()}}

    def _listing(self, structured: bool, modern: bool) -> dict:
        """`cursor` is ignored: eleven tools is one page."""
        listed = {"tools": [tools.to_wire(tool, structured)
                            for tool in self.table.values()]}
        if not modern:
            return listed
        listed.update(resultType=COMPLETE, ttlMs=TTL_MS,
                      cacheScope=CACHE_SCOPE)
        return self._modern(listed)

    def _info(self) -> dict:
        return {"name": NAME, "version": version()}

    def _modern(self, answer: dict) -> dict:
        """P6: every per-request-era result says who wrote it. Only
        `_meta`: `resultType` is written by whoever built the result,
        because two hands on one key is how they disagree."""
        return {**answer, "_meta": {META_SERVER: self._info()}}

    # -- one tool call ------------------------------------------------------
    def _plan_call(self, message: Incoming, modern: bool) -> _Call | None:
        """Refuse the call, answer it, or hand back the child to run."""
        params = message.params
        name, given = params.get("name"), params.get("arguments")
        if not isinstance(name, str) or not (given is None
                                             or isinstance(given, dict)):
            # No tool was named, so there is nothing to audit under.
            return self._fault(message, jsonrpc.INVALID_PARAMS,
                               _BAD_CALL_PARAMS)
        arguments = _arguments(params)
        tool = self.table.get(name)
        if tool is None:
            text = f"Unknown tool: {name}"
            audit.record_rejection(name, jsonrpc.INVALID_PARAMS,
                                   "unknown_tool", text)
            return self._fault(message, jsonrpc.INVALID_PARAMS, text)
        try:
            argv, extras = tools.command_argv(tool, arguments)
        except Rejection as rejected:
            # P30: an argument the model can fix comes back as a RESULT
            # in the CLI's exit-2 words -- an error response is swallowed
            # by the client, field names and all.
            #
            # The audit runs BEFORE the write, as it does for an unknown
            # tool above: a failure here is then the request's only
            # answer (`_work`'s -32603), where after the write it was a
            # SECOND response for an id that already had its result.
            audit.record_rejection(tool.name, jsonrpc.INVALID_PARAMS,
                                   rejected.reason, rejected.message,
                                   rejected.fields)
            answer = result.rejection_result(rejected, modern)
            self.writer.result(message.id,
                               self._modern(answer) if modern else answer)
            return None
        return _Call(tool, arguments, Child(
            argv, cwd=extras.get("cwd"), python=extras.get("python"),
            env=dict(os.environ),
            timeout=(self.options.run_timeout if tool.executes
                     else self.options.timeout),
            log=self.log, name=tool.name), modern)

    def _run(self, message: Incoming, call: _Call) -> None:
        """Spawn, wait, answer -- the slow part, outside the lock. P20:
        a cancelled call is never answered, because the client has
        stopped waiting and may have reused the id."""
        outcome = call.child.run()
        with self._cond:
            self._inflight = None       # cleared before the answer is written
        if outcome.cancelled:
            audit.record_cancel(call.tool.name, call.arguments, False,
                                outcome.ms)
            return
        answer, truncated = result.call_result(
            call.tool, outcome, self.options.max_output, call.modern)
        shown = len(answer["content"][0]["text"].encode("utf-8"))
        self.writer.result(message.id, self._modern(answer) if call.modern
                           else answer)
        audit.record_call(call.tool.name, call.arguments, outcome, shown,
                          truncated)


def _meta(params: dict) -> dict:
    """`params["_meta"]`, or an empty one -- a `_meta` that is not an
    object carries no keys, which is what a legacy request looks like."""
    found = params.get("_meta")
    return found if isinstance(found, dict) else {}


def _is_modern(params: dict) -> bool:
    """P5: the era is the version KEY's presence, never its value."""
    return META_VERSION in _meta(params)


def _arguments(params: dict) -> dict:
    given = params.get("arguments")
    return given if isinstance(given, dict) else {}


def _ignore_sigterm() -> None:
    try:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    except ValueError:
        pass      # not the main thread: nobody installed a handler either


def main(options: Options, table: dict[str, Tool] | None = None) -> int:
    """Serve on this process's own stdio. Always 0, and says which 0:
    EOF, SIGTERM (which the handler turns into a `SystemExit` the reader
    loop unwinds through), or stdout closed under us. None is a failure,
    and `serve()`'s `finally` has killed whatever was running."""
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8")
    server = Server(options, sys.stdin, sys.stdout, sys.stderr, table)

    def _terminated(signum, frame):
        # Three lines, and no kill: the shutdown is one path and this is
        # only how it is asked for. See the module docstring.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        server.writer.closing = True
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _terminated)
    try:
        server.serve()
    except SystemExit as leaving:
        if leaving.code not in (0, None):
            raise
        server.log("exit 0 (sigterm)")
        return 0
    except BrokenPipeError:
        server.log("exit 0 (pipe)")
        return 0
    server.log("exit 0 (eof)")
    return 0
