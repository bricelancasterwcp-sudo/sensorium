"""The server's two lifecycles, its listing and its answers, end to end.

Every test here spawns the REAL `sensorium mcp` as a child and talks to
it through `corpus/mcp_client.py` over real pipes. Nothing is mocked and
nothing is called in-process except the one test that has to be (the
internal-error case, which needs a monkeypatched `command_argv`): the
whole point of this surface is that a model reaches it through a pipe,
and a server that answered correctly to an in-process harness and
wrongly to a pipe would pass a suite of unit tests.

WHAT EVERY TEST ASSERTS WITHOUT SAYING SO. `client.bad_lines == []`,
after `__exit__`, in every single test. A `print()` anywhere in the
server -- a leftover debug line, a library that writes to stdout at
import -- is a line no client can parse, and it would otherwise be
invisible: the responses it does not corrupt still arrive. The client
files blank lines there too, so even a bare `print()` is caught.

THE STORE IS RECORDED ONCE AND IS READ-ONLY. `recorded` is module
scoped: one `sensorium run` of `PROGRAM`, reused by every test that only
ASKS things. A test that records, cancels, or reads `mcp.jsonl` takes a
private copy with `own()` first -- `runs` counts what is in the store,
and a test that added a trace to the shared one would break whichever
test happened to run after it. `own()` also drops the audit file, so a
test that reads its LAST line reads a line it wrote itself.

`tests/test_mcp_server_process.py` holds the rest of this surface -- the
cancel, timeout, cap, EOF and SIGTERM cases, which are about processes
rather than about protocol -- because one file for both would be past
the repository's 800-line ceiling.

PRE-REGISTERED MUTATIONS (task 5, step 7), each with the test that
catches it:

* drop the `META_CAPS` check ->
  `test_a_modern_request_without_client_capabilities_is_32602_naming_
  the_key`.
* echo any offered version in `initialize` ->
  `test_legacy_handshake_echoes_a_legacy_version_and_answers_2025_11_25_
  to_an_unknown_one` (its `2026-07-28` row, P27).
* omit `resultType` on a modern `tools/call` ->
  `test_runs_through_the_wire_has_the_header_structured_exit_and_no_
  error`.
* answer a `Rejection` as `-32602` instead of an `isError` result ->
  `test_unknown_field_is_an_is_error_result_naming_the_fields_and_
  audited`.
* drop the worker's `try/except` ->
  `test_an_internal_error_is_32603_and_the_worker_survives`: the second
  request is never answered.
* compare cancel ids with `str()` -> `test_ids_keep_their_json_type`:
  the string `"7"` cancels the call whose id is the integer `7`.
* echo `str(id)` in `Writer.result` -> `test_ids_keep_their_json_type`:
  `wait(11)` never sees an answer filed under `"11"`.
* `print()` to stdout at boot -> every test's `bad_lines == []`.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import signal
import sys
import time

import pytest

from corpus.mcp_client import META_CAPS, META_VERSION, McpClient, McpError
from sensorium.mcp import server as mcp_server
from sensorium.mcp import tools
from sensorium.mcp.result import STDERR_LABEL
from tests.helpers import record_script

#: The nine a client is always offered, in the order it is shown them.
NINE = ("runs", "info", "tree", "frame", "grep", "exceptions", "flow",
        "watch", "diff")

#: One flat call tree, four hundred activations deep enough to be worth
#: capping (`tests/test_mcp_server_process.py` caps this same trace).
PROGRAM = """
def leaf(i):
    return i * 2


def main():
    total = 0
    for i in range(400):
        total += leaf(i)
    return total


main()
"""

#: What `server/discover` and `initialize` both advertise about us.
SERVER_INFO = {"name": "sensorium", "version": mcp_server.version()}


@pytest.fixture(scope="module")
def recorded(tmp_path_factory):
    """`(store, run id)`: one real trace, recorded once for the module."""
    root = tmp_path_factory.mktemp("mcp-store")
    run_id, trace, r = record_script(root, PROGRAM)
    assert run_id and trace.exists(), r.stderr
    return root / "sdir", run_id


@pytest.fixture(scope="module")
def sdir(recorded):
    return recorded[0]


@pytest.fixture(scope="module")
def run_id(recorded):
    return recorded[1]


@pytest.fixture
def keep_sigterm():
    """Restore this process's SIGTERM handler.

    The one in-process test runs `serve()`, whose shutdown sets SIGTERM
    to `SIG_IGN` -- correct in the server's own process and intolerable
    in pytest's, where it would outlive the test and leave the whole
    session undismissable.
    """
    previous = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, previous)


def spawn(store, tmp_path, *flags, name="server", env=None, **kw):
    """An `McpClient` on a real `sensorium mcp` over `store`."""
    return McpClient(
        [sys.executable, "-m", "sensorium", "mcp", *flags],
        cwd=tmp_path,
        env={**os.environ, "SENSORIUM_DIR": str(store)} if env is None
        else env,
        stderr_path=tmp_path / f"{name}.stderr", **kw)


def own(sdir, tmp_path):
    """A private copy of the read-only store, with no audit file.

    A test that reads `mcp.jsonl`'s last line must read a line IT wrote:
    the shared store accumulates one per call from every test that used
    it, and the copy would inherit whichever came last.
    """
    store = tmp_path / "sdir"
    shutil.copytree(sdir, store)
    (store / "mcp.jsonl").unlink(missing_ok=True)
    return store


def last_audit(store) -> dict:
    return json.loads((store / "mcp.jsonl").read_text().splitlines()[-1])


# -- the two handshakes -----------------------------------------------------
def test_modern_handshake_lists_nine_tools_with_cache_fields_and_server_info_in_meta(  # noqa: E501 - the name is the assertion
        sdir, tmp_path):
    """2026-07-28's whole opening: `server/discover`, then a listing.

    The cache fields and the `_meta` serverInfo are what the official
    SDK reads to learn who it is talking to without a session, so they
    are asserted on the listing as well as on the probe (P6).
    """
    with spawn(sdir, tmp_path) as client:
        found = client.discover()
        listed = client.request("tools/list")
    assert found["resultType"] == "complete"
    assert found["supportedVersions"] == list(mcp_server.SUPPORTED)
    assert found["capabilities"] == {"tools": {}}
    assert found["instructions"] == mcp_server.INSTRUCTIONS
    assert found["ttlMs"] == 3600000
    assert found["cacheScope"] == "private"
    assert found["_meta"] == {mcp_server.META_SERVER: SERVER_INFO}
    assert [t["name"] for t in listed["tools"]] == list(NINE)
    assert listed["resultType"] == "complete"
    assert listed["ttlMs"] == 3600000
    assert listed["cacheScope"] == "private"
    assert listed["_meta"] == {mcp_server.META_SERVER: SERVER_INFO}
    first = listed["tools"][0]
    assert first["title"] == "runs"                 # 2025-06-18 and later
    assert first["outputSchema"]["properties"]["exit"]
    assert client.handshake_line() == "handshake discover 2026-07-28"
    assert client.bad_lines == []


def test_legacy_handshake_echoes_a_legacy_version_and_answers_2025_11_25_to_an_unknown_one(  # noqa: E501 - the name is the assertion
        sdir, tmp_path):
    """P27: the offered version is echoed iff this server has it.

    `2026-07-28` is offered by nobody honest -- that revision has no
    `initialize` at all -- so a client that sends it is confused, and
    answering `2025-11-25` tells it which era this conversation is in.
    An unknown date is the same case. Echoing whatever was offered would
    have the server claim a revision it cannot speak.
    """
    for offered, answered in (("2025-03-26", "2025-03-26"),
                              ("1900-01-01", "2025-11-25"),
                              ("2026-07-28", "2025-11-25")):
        with spawn(sdir, tmp_path, name=offered, mode="none") as client:
            result = client.initialize(offered)
        assert result["protocolVersion"] == answered
        assert result["capabilities"] == {"tools": {}}
        assert result["serverInfo"] == SERVER_INFO
        assert result["instructions"] == mcp_server.INSTRUCTIONS
        assert "_meta" not in result        # the legacy era stamps nothing
        assert client.handshake_line() == (
            f"handshake initialize {offered} -> {answered}")
        assert client.bad_lines == []


def test_a_modern_request_with_an_unsupported_version_is_32022_with_the_supported_list(  # noqa: E501 - the name is the assertion
        sdir, tmp_path):
    """`-32022` is how a modern client learns which versions to retry
    with, and the stdio probe rules say it MUST come back from
    `server/discover` too -- a discover answered `-32601` would send a
    dual-era client off to `initialize` instead."""
    crafted = {"_meta": {META_VERSION: "1900-01-01", META_CAPS: {}}}
    with spawn(sdir, tmp_path) as client:
        for method in ("tools/list", "server/discover"):
            with pytest.raises(McpError) as caught:
                client.request(method, dict(crafted))
            assert caught.value.code == -32022
            assert caught.value.message == "Unsupported protocol version"
            assert caught.value.data == {
                "supported": list(mcp_server.SUPPORTED),
                "requested": "1900-01-01"}
    assert client.bad_lines == []


def test_a_modern_request_without_client_capabilities_is_32602_naming_the_key(
        sdir, tmp_path):
    """P5: the per-request model's two required keys are both required.

    The message names the key, because the client that sent the request
    is the only thing that can add it.
    """
    with spawn(sdir, tmp_path) as client:
        with pytest.raises(McpError) as caught:
            client.request("tools/list",
                           {"_meta": {META_VERSION: "2026-07-28"}})
    assert caught.value.code == -32602
    assert caught.value.message == f"missing _meta key {META_CAPS}"
    assert client.bad_lines == []


def test_a_legacy_request_before_initialize_is_32602_not_initialized(
        sdir, tmp_path):
    """A request in neither era gets told what both eras look like."""
    with spawn(sdir, tmp_path, mode="none") as client:
        with pytest.raises(McpError) as caught:
            client.request("tools/list")
    assert caught.value.code == -32602
    assert caught.value.message == (
        "not initialized: send initialize or server/discover first, or "
        "carry _meta protocolVersion")
    assert client.bad_lines == []


def test_ping_is_answered_before_any_handshake(sdir, tmp_path):
    """`ping` is the one method with no era and no state: it is how a
    client asks whether the process is alive, and a liveness check that
    needed a handshake first would be a liveness check of the
    handshake."""
    with spawn(sdir, tmp_path, mode="none") as client:
        assert client.request("ping") == {}
    assert client.bad_lines == []


def test_modern_ping_carries_result_type_and_server_info(sdir, tmp_path):
    """...and under the per-request model even the empty result is
    stamped (P6): every result this server writes says who wrote it."""
    with spawn(sdir, tmp_path) as client:
        assert client.request("ping") == {
            "resultType": "complete",
            "_meta": {mcp_server.META_SERVER: SERVER_INFO}}
    assert client.bad_lines == []


# -- answers ----------------------------------------------------------------
def test_runs_through_the_wire_has_the_header_structured_exit_and_no_error(
        sdir, tmp_path, run_id):
    """One whole call: the exit header first, the status as structured
    content, `isError` absent, and the modern stamps on the result."""
    with spawn(sdir, tmp_path) as client:
        answer = client.call("runs", {})
    assert answer.header == "exit 0: the trace answered affirmatively"
    assert run_id in answer.stdout
    assert answer.stderr == ""
    assert answer.raw["structuredContent"] == {"exit": 0}
    assert answer.is_error is False
    assert "isError" not in answer.raw
    assert answer.raw["resultType"] == "complete"
    assert answer.raw["_meta"] == {mcp_server.META_SERVER: SERVER_INFO}
    assert client.bad_lines == []


def test_2025_03_26_omits_structured_content_output_schema_and_title(
        sdir, tmp_path):
    """`title` and `outputSchema` arrived in 2025-06-18 and structured
    content with them, so the oldest revision we speak is sent the text
    and nothing else: an unknown key is a validation failure in some
    clients and noise in the rest."""
    with spawn(sdir, tmp_path, mode="legacy", version="2025-03-26") as client:
        listed = client.list_tools()
        answer = client.call("runs", {})
    assert [t["name"] for t in listed] == list(NINE)
    assert all("title" not in t and "outputSchema" not in t for t in listed)
    assert "structuredContent" not in answer.raw
    assert "resultType" not in answer.raw
    assert "_meta" not in answer.raw
    assert answer.header == "exit 0: the trace answered affirmatively"
    assert client.bad_lines == []


def test_unknown_tool_is_32602_unknown_tool_and_audited(sdir, tmp_path):
    """A name that is not in the table is a protocol error, not a tool
    answer -- and it is the one census line that says a model reached
    for something this server does not offer."""
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path) as client:
        with pytest.raises(McpError) as caught:
            client.call("nope", {})
    assert caught.value.code == -32602
    assert caught.value.message == "Unknown tool: nope"
    line = last_audit(store)
    assert line["tool"] == "nope"
    assert line["rejected"]["code"] == -32602
    assert line["rejected"]["reason"] == "unknown_tool"
    assert line["rejected"]["message"] == "Unknown tool: nope"
    assert client.bad_lines == []


def test_call_without_arguments_is_an_empty_call(sdir, tmp_path):
    """`arguments` is optional on the wire and `runs` needs none; a
    server that required the key would refuse the simplest call there
    is."""
    with spawn(sdir, tmp_path) as client:
        answer = client.wait(client.send("tools/call", {"name": "runs"}), 60)
    assert answer["result"]["structuredContent"] == {"exit": 0}
    assert client.bad_lines == []


def test_call_with_non_object_arguments_or_no_name_is_32602(sdir, tmp_path):
    """...but an `arguments` that is PRESENT and not an object is a
    malformed request, not an empty call: `params.get("arguments") or
    {}` alone would quietly accept `[]` and run the tool with nothing."""
    with spawn(sdir, tmp_path) as client:
        for params in ({"name": "runs", "arguments": []},
                       {"name": "runs", "arguments": "x"},
                       {"arguments": {}},
                       {"name": 5, "arguments": {}}):
            answer = client.wait(client.send("tools/call", params), 60)
            assert answer["error"]["code"] == -32602, params
            assert answer["error"]["message"] == (
                "tools/call needs a string name and an object arguments")
    assert client.bad_lines == []


def test_unknown_field_is_an_is_error_result_naming_the_fields_and_audited(
        sdir, tmp_path):
    """P30: a call the model can repair comes back as an `isError`
    RESULT, in the CLI's own exit-2 words, with the field named.

    A `-32602` here would be swallowed by the client's error handling
    and the model would never see which field was wrong -- which is the
    whole reason the field is named.
    """
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path) as client:
        answer = client.call("grep", {"regex": "x"})
    assert answer.is_error is True
    assert answer.text.startswith(
        "exit 2: the call is wrong -- fix the arguments and ask again\n"
        "unknown field 'regex' for grep; fields: ")
    assert answer.raw["structuredContent"] == {"exit": 2}
    assert answer.raw["resultType"] == "complete"
    line = last_audit(store)
    assert line["tool"] == "grep"
    assert line["rejected"]["reason"] == "unknown_fields"
    assert line["rejected"]["fields"] == ["regex"]
    assert client.bad_lines == []


def test_exit_two_from_the_cli_is_is_error_with_stderr_labelled(
        sdir, tmp_path):
    """The CLI's own refusals reach the model the same way: the exit
    header, and the stderr the command printed under its label (P4)."""
    with spawn(sdir, tmp_path) as client:
        answer = client.call("info", {"run": "zz-no-such"})
    assert answer.header == (
        "exit 2: the call is wrong -- fix the arguments and ask again")
    assert STDERR_LABEL in answer.text
    assert answer.stderr.strip() == "error: no trace matches 'zz-no-such'"
    assert answer.is_error is True
    assert answer.raw["structuredContent"] == {"exit": 2}
    assert client.bad_lines == []


def test_a_negative_answer_is_exit_one_and_not_an_error(sdir, tmp_path):
    """Exit 1 is the trace answering NO, and `frame` says so for a frame
    id it does not hold (`frame_cmd._resolve`: a reference the trace
    simply lacks is NEGATIVE, an unusable reference is BAD_CALL). A
    server that flagged 1 as an error would teach the model to repair a
    call that was right."""
    with spawn(sdir, tmp_path) as client:
        answer = client.call("frame", {"frame": "f999999"})
    assert answer.header == ("exit 1: the trace answered negatively -- no "
                             "match, no frame, no exception, none")
    assert answer.stdout.strip() == "no such frame: f999999 does not exist"
    assert answer.is_error is False
    assert "isError" not in answer.raw
    assert answer.raw["structuredContent"] == {"exit": 1}
    assert client.bad_lines == []


def test_run_defaults_to_last(sdir, tmp_path, run_id):
    """D5: a positional with a default is sent even when the call omits
    it, so `info` with no arguments is `info last` and not a usage
    error."""
    with spawn(sdir, tmp_path) as client:
        answer = client.call("info", {})
    assert answer.header == "exit 0: the trace answered affirmatively"
    assert run_id in answer.stdout
    assert client.bad_lines == []


def test_record_and_refocus_absent_without_the_flag_and_present_with_it(
        sdir, tmp_path):
    """The execution gate, from the outside: the same store, two
    servers, and the two tools that run a program exist only in the
    second. Then a real recording through the wire -- `record`'s header
    says whose exit status it is reporting, because `run`'s is the
    target's own and not the query contract's."""
    store = own(sdir, tmp_path)
    (tmp_path / "hello.py").write_text("value = 6 * 7\nprint(value)\n")
    with spawn(store, tmp_path, name="closed") as closed:
        assert [t["name"] for t in closed.list_tools()] == list(NINE)
    with spawn(store, tmp_path, "--allow-run", name="open") as opened:
        assert [t["name"] for t in opened.list_tools()] == [
            *NINE, "refocus", "record"]
        made = opened.call("record", {"command": ["hello.py"],
                                      "cwd": str(tmp_path)})
        listed = opened.call("runs", {})
    assert made.header == ("exit 0: the recorded command's own status "
                           "(2 and no trace when recording was refused)")
    assert "42" in made.stdout
    assert listed.exit == 0
    assert len(listed.stdout.strip().splitlines()) == 2
    assert closed.bad_lines == []
    assert opened.bad_lines == []


# -- the awkward cases ------------------------------------------------------
def test_an_internal_error_is_32603_and_the_worker_survives(
        sdir, tmp_path, monkeypatch, keep_sigterm):
    """A bug in the server is one request's problem, not the session's.

    The one in-process test: `command_argv` is made to raise, which no
    request from outside can provoke. `_Stdin` holds the reader open
    until both answers are on stdout -- `serve()`'s shutdown drops the
    queue, so a `StringIO` that ended the moment it was drained would
    race the worker for the second request and this test would be
    asserting about the shutdown instead of about the worker.
    """
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    table = tools.table(False)
    real = tools.command_argv
    seen = []

    def boom(tool, arguments):
        seen.append(tool.name)
        if len(seen) == 1:
            raise RuntimeError("the plan blew up")
        return real(tool, arguments)

    monkeypatch.setattr(tools, "command_argv", boom)
    out, err = io.StringIO(), io.StringIO()
    meta = {META_VERSION: "2026-07-28", META_CAPS: {}}
    lines = [json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "runs", "arguments": {},
                                    "_meta": meta}}) + "\n",
             json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list",
                         "params": {"_meta": meta}}) + "\n"]
    options = mcp_server.Options()
    server = mcp_server.Server(options, _Stdin(lines, out), out, err, table)
    assert server.serve() == 0
    answers = [json.loads(line) for line in out.getvalue().splitlines()]
    assert len(answers) == 2, out.getvalue()
    assert answers[0]["id"] == 1
    assert answers[0]["error"]["code"] == -32603
    assert answers[0]["error"]["message"] == "Internal error"
    assert answers[0]["error"]["data"] == {"type": "RuntimeError"}
    assert [t["name"] for t in answers[1]["result"]["tools"]] == list(NINE)
    assert "internal error on tools/call id 1: RuntimeError: " in err.getvalue()
    assert seen == ["runs"]


class _Stdin:
    """Two request lines, then EOF -- but not before both are answered.

    The reader thread IS the caller's thread, so this iterator is where
    the test waits: it yields the lines and then holds the loop open
    until `out` has as many lines as it gave, or ten seconds pass.
    """

    def __init__(self, lines, out, timeout: float = 10.0) -> None:
        self._lines, self._out, self._timeout = lines, out, timeout

    def __iter__(self):
        yield from self._lines
        deadline = time.monotonic() + self._timeout
        while (self._out.getvalue().count("\n") < len(self._lines)
               and time.monotonic() < deadline):
            time.sleep(0.01)


def test_time_to_discover_answer_under_two_seconds(sdir, tmp_path):
    """P22: the whole table is built before the first answer, so this
    measures the boot a client actually waits through -- `Popen` to the
    discover result, imports, eleven derived schemas and all."""
    started = time.monotonic()
    with spawn(sdir, tmp_path) as client:
        elapsed = time.monotonic() - started
    assert elapsed < 2.0, elapsed
    assert client.bad_lines == []


def test_ids_keep_their_json_type(sdir, tmp_path):
    """P21, both halves.

    An id comes back the JSON value it arrived as -- a client that keyed
    its futures by `"abc"` would never find an answer filed under
    something else. And a cancel naming the STRING `"7"` is not a cancel
    of the call whose id is the INTEGER `7`: those are two requests from
    two client loops, and `str()`-ing both before comparing would kill
    the wrong one.
    """
    with spawn(sdir, tmp_path) as client:
        text = client.wait(client.send("ping", id="abc"), 30)
        number = client.wait(client.send("ping", id=11), 30)
        call = client.send("tools/call",
                           {"name": "runs", "arguments": {}}, id=7)
        client.cancel("7")
        answer = client.wait(call, 60)
    assert text["id"] == "abc" and isinstance(text["id"], str)
    assert number["id"] == 11 and isinstance(number["id"], int)
    assert answer["id"] == 7 and isinstance(answer["id"], int)
    assert answer["result"]["structuredContent"] == {"exit": 0}
    assert client.bad_lines == []


def test_instructions_is_under_800_characters(sdir, tmp_path):
    """D15/P29: the paragraph a client puts in front of the model, whole
    and short enough to be worth sending on every handshake."""
    assert len(mcp_server.INSTRUCTIONS) < 800
    assert mcp_server.INSTRUCTIONS.startswith(
        "sensorium answers debugging questions from a recorded execution ")
    assert mcp_server.INSTRUCTIONS.endswith(
        "`record` and `refocus` execute your program and exist only under "
        "`--allow-run`.")


def test_a_non_utf8_byte_on_stdin_is_a_parse_error_not_a_death(
        sdir, tmp_path):
    """`main()` reconfigures stdin with `errors="replace"`, so a byte
    that is not UTF-8 is a line that is not JSON -- `-32700` with a null
    id, like any other garbage, and the session lives."""
    with spawn(sdir, tmp_path, mode="none") as client:
        client.proc.stdin.flush()
        client.proc.stdin.buffer.write(b"\xff\n")
        client.proc.stdin.buffer.flush()
        answer = client.wait(None, 10)
        assert answer["id"] is None
        assert answer["error"]["code"] == -32700
        assert answer["error"]["message"] == "Parse error"
        assert client.request("ping") == {}
    assert client.bad_lines == []
