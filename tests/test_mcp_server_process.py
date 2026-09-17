"""The server as a PROCESS: cancel, timeout, the cap, EOF and SIGTERM.

The other half of `tests/test_mcp_server.py` (which holds the protocol
half and explains the fixtures both files share). What is asserted here
cannot be asserted about a protocol: that a cancelled call's process
GROUP is gone, that a second question is answered while a first one is
still running, that the server exits 0 on EOF with a child still alive
and kills it on the way out, and that a SIGTERM arriving DURING that
kill does not abort it.

EVERY SLEEPER IS WAITED FOR, NEVER TIMED. `tests/mcp_programs.py`'s
shapes all write `child.pid` before they sleep, and the tests here poll
for that file (or for the server's own `child <pid> pgid <pgid>` stderr
line) rather than sleeping a guessed interval: a test that cancelled on
a timer would half the time be measuring the kill of an interpreter
that had not yet reached the sleep.

A GROUP, NOT A PROCESS. `child.Child` spawns into a session of its own,
so the assertion after every kill is `os.killpg(pgid, 0)` raising
`ProcessLookupError` -- a leader-only kill leaves the recorded program
running and the leader's pid alone would not notice.

PRE-REGISTERED MUTATIONS (task 5, step 7), each with the test that
catches it:

* answer `ping` through the worker instead of inline on the reader ->
  `test_a_second_call_is_answered_after_a_cancelled_record`: a ping
  queued behind a three-second call waits three seconds, and the test
  bounds every round trip at one.
* publish `_inflight` only after the child has run ->
  `test_a_second_call_is_answered_after_a_cancelled_record`: the cancel
  at three seconds finds nothing in flight and the sleeper lives on
  (`group_gone` fails). Publishing it in a SECOND critical section
  instead -- microseconds after the pop -- is NOT caught here, and was
  measured rather than assumed: an immediate cancel reaches the reader
  before the worker has popped in six runs out of six, so
  `test_cancel_sent_immediately_after_the_call_still_kills` takes the
  queued path and never observes the gap. That gap is not observable
  from the wire at all; one critical section is a by-construction rule,
  and this is the honest bound on what these tests prove.
* send a response after a cancel ->
  `test_a_second_call_is_answered_after_a_cancelled_record`: its "no
  answer for that id" clause.
* make the SIGTERM handler call `Child.cancel()` -> NOT caught on its
  own, because the shutdown sets SIGTERM to `SIG_IGN` before it kills
  and the handler never runs. Take that `SIG_IGN` away and
  `test_sigterm_during_the_eof_grace_still_kills_the_group` fails both
  ways: with the cancelling handler the server deadlocks on the child's
  own lock and never exits (the test's `proc.wait(6)` raises), and with
  the plain handler the `SystemExit` unwinds the kill mid-grace and the
  group survives. Two rules, one test, and it holds each of them.
* `print()` to stdout at boot -> every test's `bad_lines == []`.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

import pytest

from corpus.mcp_client import McpClient
from sensorium.mcp import tools
from tests.helpers import record_script
from tests.mcp_programs import IGNORES_SIGTERM, SLEEPER, write

#: One flat call tree, four hundred activations: big enough that `tree`
#: has to be capped, small enough to record in a moment.
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


@pytest.fixture(scope="module")
def sdir(tmp_path_factory):
    """The read-only store: one real trace, recorded once. Every test
    here takes a private copy -- they all record, cancel or count."""
    root = tmp_path_factory.mktemp("mcp-store")
    run_id, trace, r = record_script(root, PROGRAM)
    assert run_id and trace.exists(), r.stderr
    return root / "sdir"


def spawn(store, tmp_path, *flags, name="server", env=None, **kw):
    """An `McpClient` on a real `sensorium mcp` over `store`."""
    return McpClient(
        [sys.executable, "-m", "sensorium", "mcp", *flags],
        cwd=tmp_path,
        env={**os.environ, "SENSORIUM_DIR": str(store)} if env is None
        else env,
        stderr_path=tmp_path / f"{name}.stderr", **kw)


def own(sdir, tmp_path):
    """A private copy of the store, with no audit file: a test that
    reads `mcp.jsonl` must read the lines IT caused."""
    store = tmp_path / "sdir"
    shutil.copytree(sdir, store)
    (store / "mcp.jsonl").unlink(missing_ok=True)
    return store


def audit_lines(store) -> list:
    return [json.loads(line) for line
            in (store / "mcp.jsonl").read_text().splitlines()]


def last_audit(store) -> dict:
    return audit_lines(store)[-1]


def one_cancel(store) -> dict:
    """The single cancel line in the audit file."""
    cancelled = [line for line in audit_lines(store) if line.get("cancelled")]
    assert len(cancelled) == 1, cancelled
    return cancelled[0]


def eventually(answer, timeout: float = 20.0, step: float = 0.02):
    """Poll `answer()` until it is truthy; return it, or None."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = answer()
        if value:
            return value
        time.sleep(step)
    return None


def group_gone(pgid: int, timeout: float) -> bool:
    """Whether the whole process group has left, within `timeout`."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)


def sleeping_record(client, tmp_path, source=SLEEPER):
    """Send a `record` of a sleeper and wait for its group to exist.

    Returns `(request id, pgid)`. The wait is on the server's own spawn
    line and then on the program's pid file, so by the time it returns
    the recorded program is really sleeping and a kill has something to
    reach.
    """
    write(tmp_path, "sleeper.py", source)
    request = client.send("tools/call", {
        "name": "record",
        "arguments": {"command": ["sleeper.py"], "cwd": str(tmp_path)}})
    pgid = eventually(lambda: (client.child_pgids() or [None])[-1])
    assert pgid, "the server logged no spawn"
    assert eventually(lambda: (tmp_path / "child.pid").exists()), \
        "the recorded program never reached its sleep"
    return request, pgid


# -- cancel -----------------------------------------------------------------
def test_a_second_call_is_answered_after_a_cancelled_record(sdir, tmp_path):
    """The whole liveness claim, in one conversation.

    A `record` that will never end on its own is started; the client
    pings four times a second THROUGH it and every round trip is under
    a second (a ping answered by the worker instead of inline would
    wait behind the call -- three seconds by the end); the call is
    cancelled at three seconds; its group dies; no response for it ever
    arrives (P20: a cancelled request is not answered); and the next
    question is answered, with the half-written trace listed as
    INCOMPLETE (P24) rather than hidden.
    """
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path, "--allow-run") as client:
        request, pgid = sleeping_record(client, tmp_path)
        pings = []
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            pings.append(client.ping())
            time.sleep(0.25)
        client.cancel(request)
        assert len(pings) >= 8, pings
        assert max(pings) < 1.0, pings
        assert group_gone(pgid, 2.0)
        with pytest.raises(TimeoutError):
            client.wait(request, 2.0)
        listed = client.call("runs", {})
    assert listed.exit == 0
    assert len(listed.stdout.strip().splitlines()) == 2
    assert "[INCOMPLETE]" in listed.stdout
    line = one_cancel(store)
    assert line["tool"] == "record"
    assert line["queued"] is False          # it had started: it was killed
    assert line["ms"] >= 3000               # ...after the three seconds
    assert client.bad_lines == []


def test_cancel_sent_immediately_after_the_call_still_kills(sdir, tmp_path):
    """The cancel that arrives in the seam.

    Written on the very next line, so it lands somewhere between the
    reader queueing the request and the child existing -- which is
    exactly the window the one critical section closes. Either it finds
    the request still queued (dropped, nothing spawned) or it finds the
    child (killed, spawned or not: `Child.run` re-reads the flag under
    its own lock after `Popen`). What must never happen is a cancel
    that falls between the two and leaves a sleeper running.
    """
    store = own(sdir, tmp_path)
    write(tmp_path, "sleeper.py", SLEEPER)
    with spawn(store, tmp_path, "--allow-run") as client:
        request = client.send("tools/call", {
            "name": "record",
            "arguments": {"command": ["sleeper.py"], "cwd": str(tmp_path)}})
        client.cancel(request)
        with pytest.raises(TimeoutError):
            client.wait(request, 3.0)
        for pgid in client.child_pgids():
            assert group_gone(pgid, 3.0), pgid
        assert client.request("ping")["resultType"] == "complete"
    line = one_cancel(store)
    assert line["tool"] == "record"
    assert client.bad_lines == []


# -- the two timeouts, and the cap ------------------------------------------
def test_run_timeout_gives_no_answer_is_error_and_kills_the_group(
        sdir, tmp_path):
    """A call that ran out of time has no exit status, so it says so:
    `no answer:` and the flag to raise, never an invented number. It is
    an error result (there is nothing to report), and the group it left
    behind is gone.

    The header is the whole of the machine-readable part (R18): there is
    no `structuredContent` to carry a null exit, and a client reads "no
    exit" off the first token -- `CallResult.exit` is `None` for exactly
    this header (`test_exit_is_read_from_the_header_not_from_structured_
    content`), which is what E17's H5 timeout arm reports.
    """
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path, "--allow-run", "--run-timeout", "1") as client:
        request, pgid = sleeping_record(client, tmp_path)
        answer = client.wait(request, 30)["result"]
        assert group_gone(pgid, 3.0)
    text = answer["content"][0]["text"]
    assert text.splitlines()[0] == (
        "no answer: timed out after 1 s "
        "(server flag --timeout / --run-timeout)")
    assert answer["isError"] is True
    assert "structuredContent" not in answer
    line = last_audit(store)
    assert line["timeout"] is True
    assert line["exit"] is None
    assert client.bad_lines == []


def test_the_cap_cuts_head_and_tail_and_audits_truncated(sdir, tmp_path):
    """D24: what comes back is the head AND the tail of the answer, with
    the server's own marker between them naming the fields THIS tool
    narrows by -- the model is told the cut was ours and how to ask for
    less. The header line is never counted against the cap."""
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path, "--max-output", "4096") as client:
        answer = client.call("tree", {"limit": 100000})
    narrowing = ", ".join(tools.narrowing_fields(tools.table(False)["tree"]))
    marker = re.compile(r"^\[\.\.\. [\d,]+ lines \([\d,]+ bytes\) omitted; "
                        rf"narrow with: {re.escape(narrowing)} \.\.\.\]$",
                        re.M)
    found = marker.search(answer.text)
    assert found, answer.text[:400]
    body = answer.text.split("\n", 1)[1]
    assert body.startswith("f1 e1 <module>() -> None\n")       # the head
    assert body.rstrip("\n").endswith("leaf(i=399) -> 798")    # ...and tail
    kept = body.replace(found.group(0) + "\n", "", 1)
    assert len(kept.encode("utf-8")) <= 4096
    line = last_audit(store)
    assert line["tool"] == "tree"
    assert line["truncated"] is True
    assert line["bytes"] == len(answer.text.encode("utf-8"))
    assert client.bad_lines == []


# -- the two ways the session ends ------------------------------------------
def test_eof_mid_record_exits_zero_within_five_seconds_and_kills_the_group(
        sdir, tmp_path):
    """The client went away mid-call. That is the end of the session,
    not an error: exit 0, and the program we started for it does not
    outlive us."""
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path, "--allow-run") as client:
        _request, pgid = sleeping_record(client, tmp_path)
        client.close_stdin()
        client.proc.wait(5)
        assert client.proc.returncode == 0
        assert group_gone(pgid, 3.0)
    assert client.bad_lines == []


def test_sigterm_mid_record_exits_zero_and_kills_the_group(sdir, tmp_path):
    """...and the same for the other way a session ends. One shutdown
    path, reached from both: the handler only asks for it."""
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path, "--allow-run") as client:
        _request, pgid = sleeping_record(client, tmp_path)
        client.proc.send_signal(signal.SIGTERM)
        client.proc.wait(6)
        assert client.proc.returncode == 0
        assert group_gone(pgid, 3.0)
    assert client.bad_lines == []


def test_sigterm_during_the_eof_grace_still_kills_the_group(sdir, tmp_path):
    """The case that decides where the kill may live.

    The recorded program ignores SIGTERM, so the kill spends its whole
    grace period waiting before the unconditional SIGKILL -- and a
    second SIGTERM arrives in the middle of it. The handler's three
    lines are why this still ends: it sets SIGTERM to SIG_IGN and asks
    for the shutdown that is already running. A handler that ran the
    kill itself would re-enter it on the one thread that holds that
    child's lock and hang here instead.
    """
    store = own(sdir, tmp_path)
    with spawn(store, tmp_path, "--allow-run") as client:
        _request, pgid = sleeping_record(client, tmp_path, IGNORES_SIGTERM)
        client.close_stdin()
        time.sleep(0.5)
        client.proc.send_signal(signal.SIGTERM)
        try:
            client.proc.wait(6)
        except subprocess.TimeoutExpired:      # never leave it running
            os.killpg(client.pgid, signal.SIGKILL)
            raise
        assert client.proc.returncode == 0
        assert group_gone(pgid, 3.0)
    assert client.bad_lines == []


# -- what the store is left holding -----------------------------------------
def test_every_call_lands_in_invocations_jsonl_and_the_server_exit_line_lands_in_the_store(  # noqa: E501 - the name is the assertion
        sdir, tmp_path):
    """P9: `--store` IS `SENSORIUM_DIR`, so the log the children write
    and the line the server writes on its own way out land in the store
    the caller named -- here with no `SENSORIUM_DIR` in the environment
    at all, which is the only way to prove the flag did it."""
    store = own(sdir, tmp_path)
    env = {k: v for k, v in os.environ.items() if k != "SENSORIUM_DIR"}
    with spawn(store, tmp_path, "--store", str(store), env=env) as client:
        assert client.call("runs", {}).exit == 0
    lines = [json.loads(line) for line
             in (store / "invocations.jsonl").read_text().splitlines()]
    argvs = [line["argv"] for line in lines]
    assert argvs.count(["runs"]) == 1
    served = [line for line in lines if line["argv"][:2] == ["mcp", "--store"]]
    assert len(served) == 1, argvs
    assert served[0]["exit"] == 0
    assert served[0]["error"] is None
    assert client.bad_lines == []


def test_the_audit_knob_silences_mcp_jsonl_and_logs_it_once(sdir, tmp_path):
    """D29: one word for "log nothing about my calls", honoured by both
    files -- and said once on stderr, so a reader of the log's absence
    is not left wondering whether the server was writing somewhere
    else."""
    store = own(sdir, tmp_path)
    env = {**os.environ, "SENSORIUM_DIR": str(store),
           "SENSORIUM_NO_INVOCATION_LOG": "1"}
    with spawn(store, tmp_path, env=env) as client:
        assert client.call("runs", {}).exit == 0
    assert not (store / "mcp.jsonl").exists()
    stderr = (tmp_path / "server.stderr").read_text("utf-8")
    assert stderr.count(
        "sensorium mcp: audit off (SENSORIUM_NO_INVOCATION_LOG)") == 1
    assert client.bad_lines == []
