#!/usr/bin/env python3
"""E17's GATHERING layer: the wire work H3-H6 and the latency row need.

Split out of `e17.py` at that file's 500-line target, on the seam the plan
names: everything here TAKES a reading off a real server and returns it as
a dict keyed by the cell function's own parameter names, so `e17.py` reads
`e17_cells.h5(**gathered)` and the decision stays in one module. Nothing
here decides anything; nothing in `e17_cells.py` touches a socket.

A gather that cannot read what its cell needs RAISES. `Part.phase` records
the exception and returns `None`, and the cell then DROPS with a reason --
which is the honest answer for a hole, and is not the same answer as a
STOP. The one exception is H6's `/proc` check, which is reported as a
failed "question" so that H6's own STOP-AS-INSTRUMENT sentence carries it:
a server that turned out not to hold the token in its environment did not
measure secrecy, and that is a finding about the measurement.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import e17_cells                                                  # noqa: E402
from corpus.cases import load_cases                               # noqa: E402
from corpus.mcp_client import McpClient, McpError                 # noqa: E402
from corpus.run_corpus import check_question, sub_run_ids         # noqa: E402
from e17_run import median                                        # noqa: E402
from sensorium.mcp import schema, tools                           # noqa: E402

#: `runs`' own row: the id, and the `events:` column H3 picks the largest
#: trace by. `^\s*` because a vitest invocation indents its members.
RUNS_ROW = re.compile(r"^\s*(\d{8}-\d{6}-[0-9a-f]{6})\s+exit:\S+\s+"
                      r"events:(\d+)", re.M)
#: The `run: <id>` line a recording prints.
RECORDED = re.compile(r"^run: (\d{8}-\d{6}-[0-9a-f]{6})", re.M)

#: H3's call, as §9 spells it.
TREE_ARGS = {"depth": 50, "limit": 100000}
#: H5's: ping every half second, cancel at five.
PING_EVERY = 0.5
CANCEL_AT = 5.0
#: How often a process group is looked at while waiting for it to go.
POLL = 0.1
#: The latency row's sample, and the rehearsal's -- forty `runs` over a
#: 273-trace store is two and a half minutes, which is most of a dry run's
#: whole budget and tells a rehearsal nothing it does not learn from three.
REPS = 20
DRY_REPS = 3


def spawn(part, store: Path, cwd: Path, name: str, allow_run: bool = True,
          flags=(), extra: dict | None = None) -> McpClient:
    """One `sensorium mcp` over `store`, from `cwd`, with its stderr on
    disk under the transcripts (which is where H5 reads the child's pgid
    and H6 counts the token's bytes)."""
    argv = [part.python, "-m", "sensorium", "mcp"]
    if allow_run:
        argv.append("--allow-run")
    argv += ["--store", str(store), *[str(f) for f in flags]]
    part.transcripts.mkdir(parents=True, exist_ok=True)
    env = part.env({"SENSORIUM_DIR": str(store), **(extra or {})})
    # Created at 0600 BEFORE the client opens it: `open(path, "w")` keeps
    # an existing file's mode, and H6's transcript is the one the token
    # must be proved absent from -- a 0644 copy of it under the work root
    # is not the hazard the cell is about, but it is not hygiene either.
    stderr = part.transcripts / f"{name}.stderr"
    stderr.touch(mode=0o600, exist_ok=True)
    os.chmod(stderr, 0o600)
    return McpClient(argv, cwd=cwd, env=env, stderr_path=stderr)


def call_argv(client: McpClient, cmd, timeout: float):
    """One corpus question through the wire: the command word names the
    tool and the schema the server derives reads the rest back into
    arguments (P25), never a second table of field names kept here."""
    word = str(cmd[0])
    tool = tools.table(True)[word]
    args = schema.from_argv(tool.schema, [str(a) for a in cmd[1:]])
    return client.call(word, args, timeout=timeout)


def _alive(pgid: int) -> bool:
    """Whether the group is still there. A `PermissionError` means it IS
    -- somebody else's process exists -- and reading that as absence is
    how a liveness cell passes over a group it never looked at."""
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _wait_gone(pgid: int, deadline: float, since: float) -> float | None:
    """Seconds from `since` until `killpg(pgid, 0)` raises, or `None` if
    the group was still there at `deadline`."""
    while time.monotonic() < deadline:
        if not _alive(pgid):
            return time.monotonic() - since
        time.sleep(POLL)
    return None if _alive(pgid) else time.monotonic() - since


def _pgid(client: McpClient, until: float | None = None) -> int | None:
    """The child's process group, off the server's own stderr line.

    `until` is a deadline to poll to; without one the file is read ONCE.
    The stderr drain writes line-buffered, so the spawn line is there as
    soon as the child exists -- but not before it, which is why a caller
    inside the ping loop asks again each time round.
    """
    while True:
        found = client.child_pgids()
        if found:
            return found[-1]
        if until is None or time.monotonic() >= until:
            return None
        time.sleep(POLL)


def _last_audit(store: Path) -> dict | None:
    lines = _audit_lines(store)
    return json.loads(lines[-1]) if lines else None


def _audit_lines(store: Path) -> list[str] | None:
    """Every line of `<store>/mcp.jsonl`, or `None` when there is no such
    file. `None` and `[]` are different facts: a file that is not there
    was not read, and a file that is there and empty is a server that
    audited nothing -- a finding, not a hole."""
    path = store / "mcp.jsonl"
    if not path.is_file():
        return None
    return [ln for ln in path.read_text("utf-8").splitlines() if ln.strip()]


def _case(name: str):
    return next(c for c in load_cases() if c.name == name)


def _swap(value, old: str, new: str):
    """`old` -> `new` everywhere in a question, keys included: a question's
    `expect_count` is keyed by the substring being counted, and the token
    is exactly the sort of substring that appears there."""
    if isinstance(value, str):
        return value.replace(old, new)
    if isinstance(value, list):
        return [_swap(v, old, new) for v in value]
    if isinstance(value, dict):
        return {_swap(k, old, new): _swap(v, old, new)
                for k, v in value.items()}
    return value


# -- H3: the cap ------------------------------------------------------------
def h3(part) -> dict:
    """The largest trace in the copy, through the wire and through the CLI.

    The CLI reading FIRST and unconditionally: it is §9's instrument check
    (`the same argv writes more than 65536 bytes`), and a cap cell that
    never took it could pass on a trace small enough that the cap never
    fired.
    """
    env = part.env({"SENSORIUM_DIR": str(part.store)})
    listing = part._run([part.python, "-m", "sensorium", "runs"], part.work,
                        env, part.timers["cell"])
    part._keep("h3-runs", {**listing, "out": listing["out"][:8000]})
    rows = [(int(events), run) for run, events in
            RUNS_ROW.findall(listing["out"])]
    if not rows:
        raise RuntimeError("`runs` over the copy listed no trace: there is "
                           "nothing for the cap to be measured on")
    events, run = max(rows)
    argv = ["tree", run, "--depth", str(TREE_ARGS["depth"]),
            "--limit", str(TREE_ARGS["limit"])]
    cli = part._run([part.python, "-m", "sensorium", *argv], part.work, env,
                    part.timers["cell"])
    cli_bytes = len(cli["out"].encode("utf-8"))
    part._keep("h3-cli", {**cli, "out": cli["out"][:4000] +
                          f"\n[... {cli_bytes} bytes in all ...]"})
    with spawn(part, part.store, part.work, "h3-server",
               allow_run=False) as client:
        answer = client.call("tree", {"run": run, **TREE_ARGS},
                             timeout=part.timers["cell"])
    part._keep("h3-tree", answer.text)
    return {"text": answer.text, "cli_bytes": cli_bytes,
            "audit_last": _last_audit(part.store),
            "_run": run, "_events": events}


# -- H4: the gate -----------------------------------------------------------
def h4(part) -> dict:
    """`silent_swallow` copied, then both sides of the flag."""
    case, store = part.work / "h4" / "case", part.work / "h4" / "store"
    shutil.copytree(REPO / "corpus" / "silent_swallow", case)
    store.mkdir(parents=True)
    spec = _case("silent_swallow")
    with spawn(part, store, case, "h4-off", allow_run=False) as client:
        names_off = [t["name"] for t in client.list_tools()]
        try:
            client.call("record", {"command": [spec.program]}, timeout=60)
            err_off = None            # answered: the gate did not hold
        except McpError as refused:
            err_off = {"code": refused.code, "message": refused.message}
    with spawn(part, store, case, "h4-on") as client:
        names_on = [t["name"] for t in client.list_tools()]
        recorded = client.call("record", {"command": [spec.program]},
                               timeout=part.timers["cell"])
        part._keep("h4-record", recorded.text)
        listing = client.call("runs", {}, timeout=part.timers["cell"])
        part._keep("h4-runs", listing.text)
        found = RUNS_ROW.findall(listing.stdout)
        if not found:
            raise RuntimeError("`runs` through the wire listed no trace "
                               "after the recording: there is no id to ask "
                               "`exceptions` about")
        run = found[0][0]
        question = sub_run_ids(spec.questions[0], run, None)
        answer = call_argv(client, question["command"], part.timers["cell"])
        part._keep("h4-exceptions", answer.text)
        failures = check_question(question, answer.stdout + answer.stderr,
                                  answer.exit)
    return {"names_off": names_off, "err_off": err_off, "names_on": names_on,
            "record_header": recorded.header, "runs_text": listing.stdout,
            "exceptions_check": failures}


# -- H5: liveness -----------------------------------------------------------
def h5(part) -> dict:
    """Both arms of §9's H5, on two fresh stores under `$E17_DIR/h5/`."""
    root = part.work / "h5"
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve().parent / "probes" / "sleeper.py",
                 root / "sleeper.py")
    out = _h5_cancel(part, root)
    out.update(_h5_timeout(part, root))
    return out


def _h5_cancel(part, root: Path) -> dict:
    store = root / "store"
    store.mkdir(parents=True)
    with spawn(part, store, root, "h5-cancel") as client:
        rid = client.send("tools/call", {"name": "record",
                                         "arguments":
                                         {"command": ["sleeper.py"]}})
        sent, pings, pgid = time.monotonic(), [], None
        while time.monotonic() - sent < CANCEL_AT:
            time.sleep(PING_EVERY)
            pings.append(client.ping())
            pgid = pgid or _pgid(client)
        if pgid is None:
            raise RuntimeError("the server printed no `child … pgid …` line "
                               "for the record: there is no group to watch")
        alive_before = _alive(pgid)
        client.cancel(rid)
        cancelled = time.monotonic()
        gone = _wait_gone(pgid, cancelled + e17_cells.CANCEL_GRACE, cancelled)
        try:
            client.wait(rid, 3)
            seen = True
        except TimeoutError:
            seen = False
        listing = client.call("runs", {}, timeout=part.timers["cell"])
        part._keep("h5-runs", listing.text)
        rows = listing.stdout.splitlines()
    return {"pings_sent": len(pings), "ping_max": max(pings) if pings else None,
            "alive_before": alive_before, "group_gone_s": gone,
            "response_seen": seen,
            "runs_after": {"answered": True,
                           "traces": len(RUNS_ROW.findall(listing.stdout)),
                           "incomplete": sum("INCOMPLETE" in r for r in rows)}}


def _h5_timeout(part, root: Path) -> dict:
    store = root / "store-timeout"
    store.mkdir(parents=True)
    with spawn(part, store, root, "h5-timeout",
               flags=("--run-timeout", "3")) as client:
        sent = time.monotonic()
        try:
            answer = client.call("record", {"command": ["sleeper.py"]},
                                 timeout=e17_cells.TIMEOUT_ANSWER)
            header, is_error = answer.header, answer.is_error
            exit_, answered = answer.exit, time.monotonic() - sent
            part._keep("h5-timeout-result", answer.text)
        except TimeoutError:
            header, is_error, exit_, answered = (
                e17_cells.NO_TIMEOUT_RESULT, None, None, None)
        pgid = _pgid(client, time.monotonic() + 1)
        if pgid is None:
            raise RuntimeError("the timeout arm's server printed no "
                               "`child … pgid …` line: there is no group "
                               "to watch")
        gone = _wait_gone(pgid, sent + e17_cells.TIMEOUT_GONE, sent)
    return {"timeout_header": header, "timeout_is_error": is_error,
            "timeout_exit": exit_, "timeout_answered_s": answered,
            "timeout_group_gone_s": gone}


# -- H6: secrecy ------------------------------------------------------------
def h6(part, token: str) -> dict:
    """`secret_in_env` recorded under the minted token, then asked through
    a server whose own environment holds it."""
    spec = _case("secret_in_env")
    literal = spec.env["SENSORIUM_CORPUS_TOKEN"]
    case, store = part.work / "h6" / "case", part.work / "h6" / "store"
    shutil.copytree(REPO / "corpus" / "secret_in_env", case)
    store.mkdir(parents=True)
    block = {**spec.env, "SENSORIUM_CORPUS_TOKEN": token}
    argv = ["run"]
    for focus in spec.record.get("focus") or []:
        argv += ["--focus", focus]
    if spec.record.get("window"):
        argv += ["--window", spec.record["window"]]
    argv += ["--", spec.program, *[str(a) for a in spec.argv]]
    recorded = part._run([part.python, "-m", "sensorium", *argv], case,
                         part.env({**block, "SENSORIUM_DIR": str(store)}),
                         part.timers["cell"])
    part._keep("h6-record", {**recorded,
                             "out": _scrub(recorded["out"], token),
                             "err": _scrub(recorded["err"], token)})
    run = next(iter(RECORDED.findall(recorded["out"])), None)
    if run is None:
        raise RuntimeError(f"the recording printed no `run:` line "
                           f"(exit {recorded['rc']}): there is no trace to "
                           f"ask about")
    return _h6_ask(part, spec, case, store, token, literal, run)


def _h6_ask(part, spec, case: Path, store: Path, token: str, literal: str,
            run: str) -> dict:
    checks, texts = [], []
    with spawn(part, store, case, "h6-server", extra={
            **spec.env, "SENSORIUM_CORPUS_TOKEN": token}) as client:
        checks.append(_proc_check(client.pid, token))
        for question in spec.questions:
            asked = _swap(sub_run_ids(question, run, None), literal, token)
            answer = call_argv(client, asked["command"], part.timers["cell"])
            texts.append(answer.text)
            part._keep(f"h6-{question['id']}", _scrub(answer.text, token))
            checks.append({"question": question["id"],
                           "failures": check_question(
                               asked, answer.stdout + answer.stderr,
                               answer.exit)})
        before = _audit_lines(store)
        counts = {"questions": len(spec.questions), "texts": len(texts),
                  "in_texts": sum(t.count(token) for t in texts),
                  "jsonl_lines": None if before is None else len(before),
                  "in_jsonl": None if before is None
                  else sum(ln.count(token) for ln in before)}
        grep = client.call("grep", {"run": run, "pattern": token},
                           timeout=part.timers["cell"])
        part._keep("h6b-grep", _scrub(grep.text, token))
        after = _audit_lines(store)
        h6b = {"pattern": (json.loads(after[-1]).get("arguments") or {}
                           ).get("pattern") if after else None,
               "in_jsonl": None if after is None
               else sum(ln.count(token) for ln in after)}
    transcript = part.transcripts / "h6-server.stderr"
    if transcript.is_file():
        text = transcript.read_text("utf-8")
        counts["stderr_bytes"] = len(text.encode("utf-8"))
        counts["in_stderr"] = text.count(token)
    else:
        counts["stderr_bytes"] = counts["in_stderr"] = None
    return {"checks": checks, "counts": counts, "h6b": h6b}


#: What `_proc_check` calls itself in `checks`. Counted apart from the
#: case's own questions in `e17_cells.h6`'s detail, so `checks_run` never
#: reads as one more question than the case has.
PROC_CHECK = "the server's own environment holds the token"


def _proc_check(pid: int, token: str) -> dict:
    """§9's precondition, read in memory and never written: the server's
    own `/proc/<pid>/environ` carries `NAME=<token>`. Reported as a
    question so that H6's STOP-AS-INSTRUMENT sentence carries it -- a
    server without the token in its environment measured no secrecy."""
    entry = f"SENSORIUM_CORPUS_TOKEN={token}".encode()
    try:
        held = entry in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
        why = [] if held else ["the entry is not in the server's environ"]
    except OSError as err:
        why = [f"/proc/{pid}/environ could not be read: {err}"]
    return {"question": PROC_CHECK, "failures": why}


def _scrub(text: str, token: str) -> str:
    """No committed or kept file carries the minted value (P10's rule for
    a minted secret), whatever the tool under test printed."""
    return (text or "").replace(token, "<token>")


# -- latency ----------------------------------------------------------------
def latency(part) -> dict:
    """§9's never-gated row: the same `runs` through both seams."""
    reps = DRY_REPS if part.dry else REPS
    env = part.env({"SENSORIUM_DIR": str(part.store)})
    wire, spawned = [], time.monotonic()
    with spawn(part, part.store, part.work, "latency-server",
               allow_run=False) as client:
        discover_ms = (time.monotonic() - spawned) * 1000
        for _ in range(reps):
            began = time.monotonic()
            client.call("runs", {}, timeout=part.timers["cell"])
            wire.append((time.monotonic() - began) * 1000)
    direct = []
    for _ in range(reps):
        began = time.monotonic()
        part._run([part.python, "-m", "sensorium", "runs"], part.work, env,
                  part.timers["cell"])
        direct.append((time.monotonic() - began) * 1000)
    part._keep("latency", json.dumps({"reps": reps, "wire_ms": wire,
                                      "cli_ms": direct,
                                      "discover_ms": discover_ms}, indent=2))
    return {"mcp_ms": median(wire), "cli_ms": median(direct),
            "discover_ms": discover_ms}
