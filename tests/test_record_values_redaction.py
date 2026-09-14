"""The Python recorder under rule v1's VALUE half: what a recorded program's
own values become on the way to disk.

Every test records a real program through `sensorium run`, in a SUBPROCESS,
the way `test_record_redaction.py` records for the environment half: the rule
is applied at the writer, and a test that patched the state in THIS process
would be asserting against a stub rather than against what a user's trace
actually holds. `env_extra` plants the secret; the trace is read back from
the store the subprocess wrote.

The first program is the E16 probe's twin, and the five rows it plants are
the ones part B pre-registered (H6-values): a RETURN taken by the callee's
name, a LINE delta taken by its own name, a map value taken under its key
(B8), a CALL argument taken by its name, and a `print` chunk taken by the
CONTENT rule -- five operations, five counted in `redaction.values`.
"""
import json
from pathlib import Path

from sensorium import redact
from sensorium.store.reader import Trace
from tests.helpers import record_script

#: The planted secret: a name the rule fires on holding a value the CONTENT
#: rule would fire on too, so each row below states WHICH rule took it.
TOKEN_VAR = "MY_API_TOKEN"
TOKEN = "sk-test-" + "aB3" * 10 + "xy"

assert len(TOKEN) == len("sk-test-") + 32

#: The E16 Python probe's twin. `secret` is a firing qualname, `token` a
#: firing local and argument, `authorization` a firing map key; `handle` and
#: `send` fire on nothing, so the rows that move are only the ones named.
PROBE = f'''import os


def secret():
    return os.environ["{TOKEN_VAR}"]


def send(token):
    return None


def handle():
    token = secret()
    headers = {{"authorization": token}}
    send(token)
    print(token)
    return len(headers)


if __name__ == "__main__":
    handle()
'''


#: `record_script` writes `prog.py`, so the module is `prog`. A BARE
#: `--focus handle` would name a MODULE called `handle` (`FocusSpec` splits
#: on `:` and a bare entry is the module half) and focus nothing at all --
#: no LINE events, and two of the five rows below would simply not exist.
FOCUS = ("--focus", "prog:handle")


def _record(tmp_path, source, env_extra, extra=FOCUS):
    """(Trace, the store directory) for one recorded program."""
    run_id, trace, r = record_script(tmp_path, source, extra=extra,
                                     env_extra=env_extra)
    assert run_id is not None, f"run failed: {r.stdout}\n{r.stderr}"
    return Trace.open(trace), Path(tmp_path) / "sdir", Path(trace)


def _codes(trace) -> dict:
    return {c.qualname: c.id for c in trace.codes()}


def _deltas(trace, code_id) -> list[dict]:
    return [e.payload.get("deltas", {})
            for e in trace.events(kind="LINE", code_id=code_id)]


def _delta_of(trace, code_id, name):
    """The one recorded delta for `name`, and how many rows carried it."""
    rows = [d[name] for d in _deltas(trace, code_id) if name in d]
    return (rows[0] if rows else None), len(rows)


def test_the_five_rows_are_redacted_and_counted(tmp_path):
    trace, sdir, _ = _record(tmp_path, PROBE, {TOKEN_VAR: TOKEN})
    key = redact.Key.load(sdir)
    codes = _codes(trace)
    taken = {"by": "name", "digest": key.digest(TOKEN)}

    # 1. `secret`'s RETURN, by the callee's own name (B7).
    returns = trace.events(kind="RETURN", code_id=codes["secret"])
    assert len(returns) == 1
    assert returns[0].payload["value"] == {
        "k": "str", "v": redact.REDACTED, "redacted": taken}

    # 2. the `token` LINE delta in `handle`, by its own name.
    token_delta, rows = _delta_of(trace, codes["handle"], "token")
    assert rows == 1 and token_delta == {
        "k": "str", "v": redact.REDACTED, "redacted": taken}

    # 3. the `headers` delta's map value, under the key `authorization` (B8).
    headers, rows = _delta_of(trace, codes["handle"], "headers")
    assert rows == 1 and headers["k"] == "map" and headers["len"] == 1
    key_cap, value_cap = headers["sample"][0]
    assert key_cap["v"] == "authorization"      # the name is not the secret
    assert value_cap == {"k": "str", "v": redact.REDACTED, "redacted": taken}
    assert "redacted" not in headers            # the dict itself was kept

    # 4. `send`'s CALL argument, by its name.
    calls = trace.events(kind="CALL", code_id=codes["send"])
    assert len(calls) == 1
    assert calls[0].payload["args"]["token"] == {
        "k": "str", "v": redact.REDACTED, "redacted": taken}

    # 5. the `print` chunk, by the CONTENT rule -- no name is involved.
    chunks = [data for _, stream, data in trace.output_chunks()
              if stream == "stdout"]
    assert redact.REDACTED in chunks

    assert trace.meta["redaction"]["values"] == 5


def test_no_plaintext_token_in_any_event_payload_or_output(tmp_path):
    """H1, at the unit grain: the value never reaches the file at all.

    Payloads and output rows are the reading part B pre-registered; the raw
    bytes are asserted beside them because a trace is a file a user hands to
    someone else, and "not in any payload we thought to walk" is a weaker
    claim than "not in the file".
    """
    trace, _, path = _record(tmp_path, PROBE, {TOKEN_VAR: TOKEN})
    for e in trace.events():
        assert TOKEN not in json.dumps(e.payload or {}), f"e{e.id} {e.kind}"
    for _, _, data in trace.output_chunks():
        assert TOKEN not in data
    assert TOKEN not in json.dumps(trace.meta)
    raw = TOKEN.encode()
    for p in (path, Path(f"{path}-wal")):
        if p.exists():
            assert raw not in p.read_bytes(), p.name


def test_the_digest_equals_the_store_keys_hmac_of_the_clipped_text(tmp_path):
    """§2.3: the digest is of what the trace would otherwise have held --
    the CLIPPED capture, not the value the program had. A digest over the
    whole 300 characters would be uncheckable by anyone reading the trace."""
    long_secret = "x" * 300
    source = ("def handle():\n"
              f"    api_key = {long_secret!r}\n"
              "    return len(api_key)\n"
              "\n"
              "handle()\n")
    trace, sdir, _ = _record(tmp_path, source, None)
    delta, rows = _delta_of(trace, _codes(trace)["handle"], "api_key")
    assert rows == 1
    assert delta == {"k": "str", "v": redact.REDACTED,
                     "redacted": {"by": "name",
                                  "digest": redact.Key.load(sdir).digest(
                                      long_secret[:200])}}
    assert "trunc" not in delta      # nothing was clipped: it was taken


def test_off_stores_plaintext_and_writes_no_values_key(tmp_path):
    """B26: the knob describes the whole recording. Nothing counts what did
    not happen, so `values` is absent rather than 0."""
    trace, _, _ = _record(tmp_path, PROBE,
                          {TOKEN_VAR: TOKEN, redact.OFF_VAR: "1"})
    assert trace.meta["redaction"] == {"rule": "v1", "mode": "off"}
    assert "values" not in trace.meta["redaction"]
    returns = trace.events(kind="RETURN", code_id=_codes(trace)["secret"])
    assert returns[0].payload["value"]["v"] == TOKEN
    assert TOKEN in [data for _, _, data in trace.output_chunks()]


def test_a_content_hit_in_an_exception_message_marks_the_exc(tmp_path):
    """An exception message is text the format holds (B21): the span goes,
    the sentence around it stays, and the `exc` object says which rule
    touched it."""
    source = ("def boom():\n"
              f"    raise ValueError('bad key {TOKEN}')\n"
              "\n"
              "def handle():\n"
              "    try:\n"
              "        boom()\n"
              "    except ValueError:\n"
              "        return 'caught'\n"
              "\n"
              "handle()\n")
    trace, _, _ = _record(tmp_path, source, None)
    raises = trace.events(kind="RAISE")
    assert raises, "the program raised nothing"
    exc = raises[0].payload["exc"]
    assert exc["msg"] == f"bad key {redact.REDACTED}"
    assert exc["redacted"] == {"by": "content", "digest": None}
    assert exc["type"] == "ValueError"      # the type was never a secret


def test_every_other_place_an_exception_is_stored_is_marked_too(tmp_path):
    """The rule reaches every `capture_exc` the recorder writes, not only the
    RAISE row: the frame it unwound, and the run's `uncaught` record.

    The traceback still reaches the real stderr as the program wrote it --
    an instrument that changed what a program SHOWS would be a worse
    instrument -- so the tee's own copy is where the rule applies.
    """
    source = ("def boom():\n"
              f"    raise ValueError('bad key {TOKEN}')\n"
              "\n"
              "boom()\n")
    trace, _, _ = _record(tmp_path, source, None)
    marked = f"bad key {redact.REDACTED}"

    unwound = [f for f in trace.frames() if f.unwind_exc]
    assert unwound, "the fixture must actually unwind a frame"
    assert unwound[0].unwind_exc["msg"] == marked
    assert unwound[0].unwind_exc["redacted"] == {"by": "content",
                                                 "digest": None}
    assert trace.meta["uncaught"]["msg"] == marked
    assert trace.meta["uncaught"]["redacted"]["by"] == "content"
    for _, _, data in trace.output_chunks():
        assert TOKEN not in data            # the tee'd traceback, redacted


def test_an_exception_thrown_into_a_suspended_frame_is_marked(tmp_path):
    """`g.throw(...)` is recorded on the generator's RESUME row, which is the
    fourth and last place a captured exception reaches the trace."""
    source = ("def gen():\n"
              "    try:\n"
              "        yield 1\n"
              "    except ValueError:\n"
              "        yield 2\n"
              "\n"
              "def handle():\n"
              "    g = gen()\n"
              "    next(g)\n"
              f"    return g.throw(ValueError('bad key {TOKEN}'))\n"
              "\n"
              "handle()\n")
    trace, _, _ = _record(tmp_path, source, None)
    # The dropped generator is finalised with a GeneratorExit thrown into
    # it, which is a second `thrown` row and not the one under test.
    thrown = [e.payload["thrown"] for e in trace.events(kind="RESUME")
              if e.payload.get("thrown", {}).get("type") == "ValueError"]
    assert len(thrown) == 1
    assert thrown[0]["msg"] == f"bad key {redact.REDACTED}"
    assert thrown[0]["redacted"] == {"by": "content", "digest": None}


def test_a_secret_local_in_a_loop_is_counted_once_not_once_per_line(tmp_path):
    """`values` counts what the TRACE HOLDS, never how often the rule ran.

    Every local in scope is re-captured at every line, so a secret bound
    before a loop meets the rule on each of the loop's lines while the trace
    stores it exactly once. A count of operations would put 9 on this trace
    and tell a reader to look for 9 rows.
    """
    source = ("def handle():\n"
              "    api_key = 'x'\n"
              "    total = 0\n"
              "    for i in range(5):\n"
              "        total += i\n"
              "    return total\n"
              "\n"
              "handle()\n")
    trace, _, _ = _record(tmp_path, source, None)
    _, rows = _delta_of(trace, _codes(trace)["handle"], "api_key")
    assert rows == 1
    assert trace.meta["redaction"]["values"] == 1


def test_a_value_that_does_not_change_across_lines_is_one_delta(tmp_path):
    """The digest is an equality identity (§2.3), so two sightings of one
    unchanged secret are one delta -- as they were before the rule. A digest
    that carried anything per-sighting would turn every line into a change."""
    source = ("def handle():\n"
              "    api_key = 'same-value'\n"
              "    api_key = 'same-value'\n"
              "    return api_key\n"
              "\n"
              "handle()\n")
    trace, _, _ = _record(tmp_path, source, None)
    delta, rows = _delta_of(trace, _codes(trace)["handle"], "api_key")
    assert rows == 1
    assert delta["redacted"]["by"] == "name"
