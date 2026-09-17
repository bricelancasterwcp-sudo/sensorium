"""The official MCP SDK as the conformance oracle for `sensorium mcp`.

`tests/test_mcp_server.py` drives the server through
`corpus/mcp_client.py` -- our own client, written from our own reading
of the protocol. A misreading in that reading sits on BOTH sides of
those tests, so they cannot catch one. This file is the one client that
cannot share it: the official Python SDK (`mcp`, installed by the
`conformance` extra), which under a modern session hard-fails a
`tools/call` result without `resultType` and a `tools/list` without
`ttlMs`/`cacheScope`, reads `serverInfo` out of `_meta`, revalidates
`structuredContent` against the tool's own `outputSchema`, and probes
`server/discover` before it will fall back to `initialize`.

THE CONSTANTS BELOW ARE LITERALS ON PURPOSE. `SUPPORTED` and `NINE`
are spelled out, never imported from `sensorium.mcp.server`: an oracle
that imports the subject's own constants moves with the subject, and a
revision quietly dropped from the supported list would still "pass".
A FAILURE HERE IS A SERVER DEFECT OR A MISREAD SPEC -- never a reason
to soften a line. `pytest.importorskip("mcp")` is why this file skips
BY NAME wherever the extra is absent (every CI job but `conformance`
installs `.[dev]` alone), and E17's H2 floor is nine of these ten
passed and NONE skipped -- so a skip in the job that DOES install it
is an instrument failure rather than a pass.

THE SDK LETS SIX VARIABLES THROUGH -- `get_default_environment()` keeps
`HOME LOGNAME PATH SHELL TERM USER` and drops the rest -- so `params()`
passes `SENSORIUM_DIR` explicitly, with `PATH` and `HOME`, which the
recorder's own children need. Two tests still use the hand-written
client: they ask what a NON-conforming client is told, and the SDK
cannot send a malformed `_meta` -- correct by construction is the whole
reason it is the oracle everywhere else.
"""
from __future__ import annotations

import os
import re
import shutil
import sys

import pytest

mcp = pytest.importorskip("mcp")        # the `conformance` extra, by name

import anyio                                                # noqa: E402
from mcp import Client, MCPError, StdioServerParameters     # noqa: E402
from mcp.client.session import ClientSession                # noqa: E402
from mcp.client.stdio import stdio_client                   # noqa: E402

from corpus.mcp_client import META_CAPS, META_VERSION, McpClient  # noqa: E402
from tests.helpers import record_script                     # noqa: E402
from tests.mcp_programs import SLEEPER                       # noqa: E402

#: Every revision this server speaks, newest first: a `-32022`'s list.
SUPPORTED = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26"]

#: The tools offered without `--allow-run`, in the order they are shown.
NINE = ["runs", "info", "tree", "frame", "grep", "exceptions", "flow",
        "watch", "diff"]

#: ...and the two the flag adds, in the order the gate appends them.
ELEVEN = [*NINE, "refocus", "record"]

#: Enough for `runs` to have an answer; recorded once for the module.
PROGRAM = """
def main():
    return sum(i * 2 for i in range(50))

main()
"""


@pytest.fixture(scope="module")
def sdir(tmp_path_factory):
    """The read-only store: one real recording, made once. Never
    written to -- a test that records takes a private copy with `own()`
    first, because `runs` counts what is in the store and a test that
    added to it would change what the next test is told.
    """
    root = tmp_path_factory.mktemp("conformance-store")
    run_id, trace, r = record_script(root, PROGRAM)
    assert run_id and trace.exists(), r.stderr
    return root / "sdir"


def params(store, *flags, cwd=None, extra_env=None) -> StdioServerParameters:
    """A real `sensorium mcp` over `store`, as the SDK spawns it."""
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "sensorium", "mcp", *flags],
        env={"SENSORIUM_DIR": str(store), "PATH": os.environ["PATH"],
             "HOME": os.environ.get("HOME", ""), **(extra_env or {})},
        cwd=cwd)


def own(sdir, tmp_path):
    """A private copy of the store, for a test that records into it."""
    store = tmp_path / "sdir"
    shutil.copytree(sdir, store)
    return store


def hand(store, tmp_path, name, **kw) -> McpClient:
    """The hand-written client, for the two malformed-request tests."""
    return McpClient(
        [sys.executable, "-m", "sensorium", "mcp"], cwd=tmp_path,
        env={**os.environ, "SENSORIUM_DIR": str(store)},
        stderr_path=tmp_path / f"{name}.stderr", **kw)


# -- what the SDK makes of the server ---------------------------------------
def test_auto_connect_is_modern_and_names_the_server(sdir):
    """The default connect: `server/discover`, answered, no fallback.
    `mode="auto"` probes it and falls back to `initialize` only on a
    `-32601`, so a modern `protocol_version` is proof the probe was
    answered; `server_info` in this era exists ONLY in the result's
    `_meta`, there being no session to have carried it.
    """
    async def go():
        async with Client(params(sdir)) as client:
            return (client.protocol_version, client.server_info.name,
                    client.instructions)

    version, name, instructions = anyio.run(go)
    assert version == "2026-07-28"
    assert name == "sensorium"
    assert instructions.startswith("sensorium answers")


def test_list_tools_nine_then_eleven(sdir):
    """The gate from outside, plus the three fields a cache needs.
    `ttl_ms` and `cache_scope` fall back to SDK defaults (0 and
    `"private"`) when the server sends nothing, so the TTL is the
    assertion that carries: a forgotten field reads as 0 here.
    """
    async def go(*flags):
        async with Client(params(sdir, *flags)) as client:
            return await client.list_tools()

    closed = anyio.run(go)
    opened = anyio.run(go, "--allow-run")
    assert [t.name for t in closed.tools] == NINE
    assert [t.name for t in opened.tools] == ELEVEN
    assert closed.ttl_ms == 3600000
    assert closed.cache_scope == "private"
    assert closed.tools[0].annotations.read_only_hint is True


def test_call_runs_has_header_and_structured_exit(sdir):
    """One whole answer, revalidated by the SDK against our own
    schema: `call_tool` re-checks `structured_content` against the
    tool's declared `outputSchema` and raises when a tool that declares
    one returns none, so reaching the assertions below is itself part
    of what this test proves.
    """
    async def go():
        async with Client(params(sdir)) as client:
            return await client.call_tool("runs", {})

    result = anyio.run(go)
    assert re.match(r"^exit [0-3]: ", result.content[0].text.splitlines()[0])
    assert isinstance(result.structured_content["exit"], int)
    assert result.is_error is False


def test_legacy_mode_connects_at_2025_11_25(sdir):
    """`mode="legacy"` skips the probe and opens with `initialize`,
    offering `2025-11-25`; the era it lands in is the server's answer."""
    async def go():
        async with Client(params(sdir), mode="legacy") as client:
            return client.protocol_version

    assert anyio.run(go) == "2025-11-25"


def test_unknown_tool_raises_32602(sdir):
    """A name that is not in the table is a protocol error, not an
    `isError` result -- the SDK raises for the first and returns the
    second, and which one a model gets decides whether it retries."""
    async def go():
        async with Client(params(sdir)) as client:
            with pytest.raises(MCPError) as caught:
                await client.call_tool("nope", {})
            return caught.value

    error = anyio.run(go)
    assert error.code == -32602
    assert error.message == "Unknown tool: nope"


def test_read_timeout_cancels_and_the_server_survives(sdir, tmp_path):
    """The liveness claim, asked by the SDK's own cancel path. A
    `record` of a sleeper never ends on its own; the SDK abandons it at
    one second, writes `notifications/cancelled` for that id and raises
    `-32001`, and the server must stay in the conversation.
    `cache_mode="bypass"` is what makes the second call a wire round
    trip -- the default would be served from the listing the connect
    already cached, and this test would pass against a dead server.
    """
    store = own(sdir, tmp_path)
    (tmp_path / "sleeper.py").write_text(SLEEPER)

    async def go():
        async with Client(params(store, "--allow-run",
                                 cwd=str(tmp_path))) as client:
            with pytest.raises(MCPError) as caught:
                await client.call_tool(
                    "record",
                    {"command": ["sleeper.py"], "cwd": str(tmp_path)},
                    read_timeout_seconds=1)
            return caught.value, await client.list_tools(cache_mode="bypass")

    error, listing = anyio.run(go)
    assert error.code == -32001
    assert [t.name for t in listing.tools] == ELEVEN


# -- what a client the SDK cannot be is told --------------------------------
def test_hand_written_client_initialize_echo_fallback_and_32022(
        sdir, tmp_path):
    """The legacy echo rule and the modern refusal, in one test. The
    handshake is sent by hand (`mode="none"`, then `initialize` and
    `notifications/initialized`) rather than by `mode="legacy"`, which
    performs it at `__enter__` and discards the result: the answered
    `protocolVersion` is the assertion, so it must be in hand.
    """
    with hand(sdir, tmp_path, "echo", mode="none") as echo:
        echoed = echo.initialize("2025-03-26")
        echo.notify("notifications/initialized")
    with hand(sdir, tmp_path, "fallback", mode="none") as fallback:
        fell_back = fallback.initialize("1900-01-01")
        fallback.notify("notifications/initialized")
    with hand(sdir, tmp_path, "unsupported") as modern:
        answer = modern.wait(modern.send("tools/list", {"_meta": {
            META_VERSION: "1900-01-01", META_CAPS: {}}}), 60)

    assert echoed["protocolVersion"] == "2025-03-26"
    assert fell_back["protocolVersion"] == "2025-11-25"
    assert answer["error"]["code"] == -32022
    assert answer["error"]["data"]["supported"] == SUPPORTED
    assert answer["error"]["data"]["requested"] == "1900-01-01"


def test_a_modern_request_without_client_capabilities_is_32602(
        sdir, tmp_path):
    """Both of the per-request era's `_meta` keys are required, and the
    refusal names the missing one: the client that sent the request is
    the only thing that can add it."""
    with hand(sdir, tmp_path, "nocaps") as client:
        answer = client.wait(client.send("tools/list", {"_meta": {
            META_VERSION: "2026-07-28"}}), 60)

    assert answer["error"]["code"] == -32602
    assert answer["error"]["message"] == f"missing _meta key {META_CAPS}"


# -- the low-level session: the probe, and what the server said aloud -------
@pytest.fixture(scope="module")
def discover_refusal(sdir, tmp_path_factory):
    """`(the MCPError, the server's whole stderr transcript)`: one
    low-level session, module scoped so both tests below read the same
    run -- one is about the answer on stdout, the other about what went
    to stderr while it was answered, and two servers would make those
    two facts about two processes.
    """
    transcript = tmp_path_factory.mktemp("conformance-stderr") / "srv.stderr"

    async def go():
        with open(transcript, "w", encoding="utf-8") as errlog:
            async with stdio_client(params(sdir), errlog=errlog) as streams:
                read, write = streams
                async with ClientSession(read, write,
                                         read_timeout_seconds=30) as session:
                    with pytest.raises(MCPError) as caught:
                        await session.send_discover("1900-01-01")
                    return caught.value

    error = anyio.run(go)
    return error, transcript.read_text("utf-8").splitlines()


def test_sdk_send_discover_with_an_unsupported_version_is_32022(
        discover_refusal):
    """`server/discover` refuses an unknown version the same way every
    other modern request does. A `-32601` here instead would send a
    dual-era client off to `initialize` -- it would connect, in the
    wrong era, and never learn that the date it asked for was junk."""
    error, _ = discover_refusal
    assert error.code == -32022
    assert error.data["supported"] == SUPPORTED


def test_the_servers_stderr_holds_no_json(discover_refusal):
    """stdout is the protocol and stderr is the diagnostics, and one
    line in the wrong stream corrupts a session no client can recover.
    The transcript is checked non-empty first: the server logs at boot,
    so an empty file would mean this test proved nothing."""
    _, lines = discover_refusal
    assert lines, "the server logged nothing at all -- nothing was checked"
    assert [line for line in lines if line.startswith("{")] == []
