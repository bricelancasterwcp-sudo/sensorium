"""`redact_store.plan` -- what a trace already on disk BECOMES, decided in
memory and written by nobody (spec C14, plan P1).

Every trace on this box predates rule v1: 273 of them, each holding a live
`CLAUDE_CODE_MESSAGING_TOKEN` at 0644 (spec §13's measurement). Parts A and
B put the rule at the three recorders' writers, so nothing NEW leaks; this
is the other half -- the judgement `sensorium redact` makes about what is
already there. Task 3 adds `apply`, Task 4 the command; nothing here writes
a trace, so every assertion below is about a `Plan` object.

The three shapes are built synthetically (C15) rather than recorded: a
Python trace with a secret at every site the rule reaches, a Rust one and a
TypeScript one for the `k=v` env-hash formula and the `dbg` capture, plus
the committed format-1 fixture -- the shape of the 18 oldest traces in the
store, whose `events` table has no `task_id` column at all.

`_python` is imported by Tasks 3 and 4's suites; its signature and the event
ids it writes (`E_CALL` .. `E_RAISE`) are part of what this module publishes.
"""
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

from sensorium import redact, redact_store
from sensorium.redact_key import Key
from sensorium.store import db
from sensorium.store.writer import TraceWriter
from sensorium.ts.invocation import env_hash as _kv_env_hash
from tests import rust_traces, ts_traces
from tests.helpers import finalize_synthetic, rust_trace

#: One secret per pattern family the content rule knows, so a test can tell
#: which hand took a value: `TOKEN` and `ANT` are whole-match rows, `BEARER`
#: and `DSN` keep the sentence around the span.
TOKEN = "sk-live-0123456789abcdef0123"
BEARER = "Bearer abcdefghijklmnopqrstuvwxyz"
ANT = "sk-ant-abcdefghijklmnopqrstuvwxyz1234"
DSN = "postgres://u:pw@h/db"

#: A name rule v1 does NOT know: `MYCO` and `HANDLE` are segments of no
#: set, so only a caller's `SENSORIUM_REDACT_NAMES` can take it. That is
#: what makes the knobs argument load-bearing rather than decorative.
HANDLE_NAME, HANDLE = "MYCO_HANDLE", "handle-0123456789"

#: `API_KEY` fires the NAME rule (segments `API`, `KEY`); `HOME` fires
#: nothing and is what a test reads to see the env pass left it alone.
ENV = {"API_KEY": "api-key-0123456789", "HOME": "/tmp/u"}

#: The caller's knobs, as `redact_cmd` will build them: the rule on, no
#: list either way. `plan` never reads an environment of its own.
KNOBS = redact.Knobs(False, frozenset(), frozenset())

RUN = "20260101-000000-py0001"

#: `_python`'s event ids, in the order it writes them. `E_BENIGN` is the row
#: that must NEVER appear in a plan (P8): it holds nothing the rule takes.
E_CALL, E_BENIGN, E_LINE, E_RETURN, E_RAISE = 1, 2, 3, 4, 5
#: The frame `_python` leaves by throwing, and the one output row.
FR_UNWIND, OUT_ROW = 2, 1


def _json_hash(env: dict) -> str:
    """The Python recorder's `env_hash` (`record/boot.py:490`), spelled here
    independently of the module under test -- an assertion that called
    `env_hash_for` would agree with any formula it happened to use."""
    return hashlib.sha256(
        json.dumps(env, sort_keys=True).encode()).hexdigest()[:16]


def _key(tmp_path) -> Key:
    return Key.load_or_create(Path(tmp_path) / "sdir")


def _set_meta(path, **pairs) -> None:
    """Meta written straight onto a finished trace: the only way to state a
    shape `finalize_synthetic` writes last (`incomplete`), one it writes
    from a fixed table (`trace_format`), or one a later test amends."""
    conn = sqlite3.connect(path)
    with conn:
        for k, v in pairs.items():
            db.set_meta(conn, k, v)
    conn.close()


def _rewrite(path, p) -> None:
    """Task 3's `apply`, in the four statements this module needs: the
    plan's own rows, in place. No backup, no rename, no modes -- those are
    C7's mechanics and Task 3 tests them. What this is for is the GROUND a
    re-application stands on: a trace that has already been retrofitted."""
    conn = sqlite3.connect(path)
    with conn:
        for eid, payload in p.payloads.items():
            conn.execute("UPDATE events SET payload = ? WHERE id = ?",
                         (payload, eid))
        for fid, exc in p.unwinds.items():
            conn.execute("UPDATE frames SET unwind_exc = ? WHERE id = ?",
                         (exc, fid))
        for oid, data in p.outputs.items():
            conn.execute("UPDATE output SET data = ? WHERE id = ?",
                         (data, oid))
        for k, v in p.meta.items():
            db.set_meta(conn, k, v)
    conn.close()


def _dead_pid() -> int:
    """A pid this box provably does not have -- the spelling
    `tests/test_redact_key_sweep.py` uses. `PermissionError` means the pid
    is real but not ours to signal, so it is skipped, not accepted."""
    pid = 2**22 - 1
    while pid > 1:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except OSError:
            pass
        pid -= 1
    raise RuntimeError("no dead pid found below 2**22")


def _python(tmp_path, *, env, redaction=None, children=None, mode=0o644):
    """A Python-shaped trace with a secret at every site rule v1 reaches: a
    bound argument (`token`, by name), a map VALUE under a firing key
    (`authorization`, B8), a RETURN under a firing callee (`get_api_key`,
    B7), an exception message and an `unwind_exc` (content), and one output
    row. `E_BENIGN` holds none, which is what makes P8 checkable.

    Returned at 0644 with its sidecars -- the mode every trace in the store
    was measured at -- so `tightens` is true unless a test says otherwise.
    """
    path = Path(tmp_path) / "sdir" / "traces" / f"{RUN}.db"
    w = TraceWriter(path, batch=1)
    code = w.intern_code("prog.py", "get_api_key", 1)
    call = w.add_event(1, 1, "CALL", None, code, 1, {"args": {
        "token": {"k": "str", "v": TOKEN, "trunc": False},
        "n": {"k": "num", "v": 1}}})
    returning = w.open_frame(None, code, call, 0, 1)
    benign = w.add_event(2, 1, "CALL", None, code, 1,
                         {"args": {"n": {"k": "num", "v": 2}}})
    unwinding = w.open_frame(None, code, benign, 0, 1)
    w.add_event(3, 1, "LINE", returning, code, 2, {"deltas": {"headers": {
        "k": "map", "type": "dict", "len": 1, "trunc": False, "sample": [[
            {"k": "str", "v": "authorization", "trunc": False},
            {"k": "str", "v": BEARER, "trunc": False}]]}}})
    ret = w.add_event(4, 1, "RETURN", returning, code, None, {
        "value": {"k": "str", "v": "tok_plain_value", "trunc": False}})
    w.close_frame(returning, ret, "return")
    w.add_event(5, 1, "RAISE", unwinding, code, 3, {"exc": {
        "type": "ValueError", "msg": f"bad {DSN}", "serial": 1, "oid": 1}})
    w.close_frame(unwinding, None, "unwind",
                  {"type": "E", "msg": ANT, "serial": 2})
    w.add_output(ret, "stdout", f"token {TOKEN}\n")
    finalize_synthetic(w, env=dict(env), env_hash=_json_hash(env),
                       children=list(children or []),
                       **({"redaction": redaction} if redaction else {}))
    w.close()
    path.chmod(mode)
    return path


def _settled(tmp_path, key, **kw):
    """A `_python` trace with the retrofit ALREADY applied, and the plan
    that applied it: every capture carries `redacted`, the env holds
    markers, the stamp is on under the store's key."""
    path = _python(tmp_path, env=dict(ENV), **kw)
    first = redact_store.plan(path, key, KNOBS)
    _rewrite(path, first)
    return path, first


def _rust(tmp_path, monkeypatch, env):
    """A `sensorium-rt` trace: `dbg` captures, and an `env_hash` under the
    sorted `k=v` formula both non-Python recorders use."""
    run = rust_trace(
        tmp_path, monkeypatch,
        codes=[("/w/demo/src/lib.rs", "secret", 1)],
        events=[rust_traces.call(1, 1, 1),
                rust_traces.line(2, 1, 1, 2,
                                 {"token": rust_traces.dbg(f'"{TOKEN}"')}),
                rust_traces.ret(3, 1, 1, "ok", '"tok"')],
        frames=[rust_traces.frame(1, 1, 3)],
        env=dict(env), env_hash=_kv_env_hash(env))
    return Path(tmp_path) / "sdir" / "traces" / f"{run}.db"


def _ts(tmp_path, monkeypatch, env):
    """A `sensorium-ts` trace: a focused CALL carrying `args`, whose
    `apiKey` binding fires the name rule."""
    run = ts_traces.ts_trace(
        tmp_path, monkeypatch,
        codes=[("/w/app/src/config.ts", "load", 1)],
        events=[ts_traces.call(1, 1, 1, args={
                    "apiKey": {"k": "str", "v": TOKEN, "trunc": False}}),
                ts_traces.ret(2, 1, 1)],
        frames=[ts_traces.frame(1, 1, 2)],
        env=dict(env), env_hash=_kv_env_hash(env))
    return Path(tmp_path) / "sdir" / "traces" / f"{run}.db"


# -- the whole judgement, on a trace that predates the rule ----------------

def test_a_pre_rule_python_trace_is_redacted_in_full(tmp_path):
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)

    p = redact_store.plan(path, key, KNOBS)

    assert (p.refused, p.skipped) == (None, None)
    assert (p.run, p.lang) == (RUN, "python")
    assert p.env_names == ("API_KEY",)
    assert p.meta["env"] == {"API_KEY": redact.REDACTED, "HOME": "/tmp/u"}
    assert p.meta["env_hash"] == _json_hash(p.meta["env"])
    assert p.meta["redaction"] == {
        "rule": "v1", "mode": "on", "keyed": True, "key_id": key.key_id,
        "env": {"API_KEY": key.digest(ENV["API_KEY"])},
        "names": [], "allow": [], "by": "retrofit", "values": 6}

    assert sorted(p.payloads) == [E_CALL, E_LINE, E_RETURN, E_RAISE]
    args = json.loads(p.payloads[E_CALL])["args"]
    assert args["token"]["v"] == redact.REDACTED
    assert args["token"]["redacted"] == {
        "by": "name", "digest": key.digest(TOKEN)}
    assert args["n"] == {"k": "num", "v": 1}
    pair = json.loads(p.payloads[E_LINE])["deltas"]["headers"]["sample"][0]
    assert pair[0]["v"] == "authorization"
    assert pair[1]["v"] == redact.REDACTED
    assert pair[1]["redacted"]["by"] == "name"
    value = json.loads(p.payloads[E_RETURN])["value"]
    assert value["v"] == redact.REDACTED
    assert value["redacted"]["by"] == "name"
    exc = json.loads(p.payloads[E_RAISE])["exc"]
    assert exc["msg"] == f"bad postgres://u:{redact.REDACTED}@h/db"
    assert exc["redacted"] == {"by": "content", "digest": None}

    assert list(p.unwinds) == [FR_UNWIND]
    assert json.loads(p.unwinds[FR_UNWIND])["msg"] == redact.REDACTED
    assert p.outputs == {OUT_ROW: f"token {redact.REDACTED}\n"}

    assert p.values == 6
    assert p.rewrites is True and p.changes is True
    assert p.mode_before == 0o644 and p.tightens is True


def test_an_unchanged_row_is_not_in_the_plan(tmp_path):
    """P8: equality is on the PARSED payload, and a row that decodes to what
    it already holds is never written -- which is what leaves a retrofitted
    trace byte-identical everywhere nothing was redacted."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)

    p = redact_store.plan(path, key, KNOBS)

    assert E_BENIGN not in p.payloads


def test_children_elements_take_the_content_rule(tmp_path):
    """R25: a spawned command line has positions, not bindings, so the span
    operation is the whole of the rule at that site."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV, children=[
        ["curl", "-H", f"Authorization: {BEARER}"]])

    p = redact_store.plan(path, key, KNOBS)

    assert p.meta["children"] == [
        ["curl", "-H", f"Authorization: Bearer {redact.REDACTED}"]]
    assert p.values == 7
    assert p.meta["redaction"]["values"] == 7


# -- the other two recorders ----------------------------------------------

def test_the_rust_env_hash_is_the_kv_formula_and_the_return_fires_by_qualname(
        tmp_path, monkeypatch):
    key = _key(tmp_path)
    env = {"API_KEY": "api-key-0123456789", "HOME": "/tmp/u"}
    path = _rust(tmp_path, monkeypatch, env)

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused is None and p.lang == "rust"
    assert p.meta["env_hash"] == _kv_env_hash(p.meta["env"])
    assert p.meta["env_hash"] != _json_hash(p.meta["env"])
    # P7: the callee's name comes from `code_objects.qualname`, and `secret`
    # fires -- nothing about the VALUE `"tok"` would have.
    value = json.loads(p.payloads[3])["value"]
    assert value["v"] == redact.REDACTED
    assert value["redacted"]["by"] == "name"
    assert json.loads(p.payloads[2])["deltas"]["token"]["v"] == redact.REDACTED


def test_the_typescript_shape_likewise(tmp_path, monkeypatch):
    key = _key(tmp_path)
    env = {"API_KEY": "api-key-0123456789", "HOME": "/tmp/u"}
    path = _ts(tmp_path, monkeypatch, env)

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused is None and p.lang == "typescript"
    assert p.meta["env_hash"] == _kv_env_hash(p.meta["env"])
    assert p.env_names == ("API_KEY",)
    api_key = json.loads(p.payloads[1])["args"]["apiKey"]
    assert api_key["v"] == redact.REDACTED
    assert api_key["redacted"]["by"] == "name"


# -- the refusals and the skip (C8, C9) ------------------------------------

def test_a_non_reproducing_env_hash_is_refused(tmp_path):
    """C3: a retrofit that cannot reproduce the OLD hash from the stored env
    cannot claim the new one is under the same formula."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    _set_meta(path, env_hash="0" * 16)

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused == "env_hash does not reproduce under the python formula"
    assert (p.meta, p.payloads, p.unwinds, p.outputs) == ({}, {}, {}, {})
    assert (p.env_names, p.values) == ((), 0)
    assert p.rewrites is False and p.changes is False


def test_an_incomplete_trace_is_skipped(tmp_path):
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    _set_meta(path, incomplete=True)

    p = redact_store.plan(path, key, KNOBS)

    assert p.skipped == "in flight (incomplete)"
    assert p.refused is None and p.lang == "python"
    assert p.changes is False


def test_a_newer_format_is_refused_with_open_traces_own_words(tmp_path):
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    _set_meta(path, trace_format=db.TRACE_FORMAT + 1)

    p = redact_store.plan(path, key, KNOBS)

    assert "newer than this sensorium reads" in p.refused
    assert p.refused.startswith("is trace format")
    assert str(path) not in p.refused      # the line names the file already


def test_a_file_that_is_not_a_database_is_refused(tmp_path):
    key = _key(tmp_path)
    path = Path(tmp_path) / "sdir" / "traces" / "20260101-000000-junk01.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not a database, just some bytes\n")

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused.startswith("not a database this sensorium can open: ")
    assert p.rewrites is False


def test_a_vanished_file_is_refused_not_raised(tmp_path):
    """A trace another process removed between the walk and the open. An
    `--all` pass has to lose that trace and not the ones after it."""
    key = _key(tmp_path)
    path = Path(tmp_path) / "sdir" / "traces" / "20260101-000000-gone01.db"
    path.parent.mkdir(parents=True, exist_ok=True)

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused.startswith("cannot open: ")
    assert p.rewrites is False and p.changes is False


def test_a_corrupt_meta_row_is_refused(tmp_path):
    """`db.all_meta` `json.loads`es every row; a truncated or hand-edited
    one is this trace's problem, not the walk's."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    conn = sqlite3.connect(path)
    with conn:
        conn.execute("UPDATE meta SET value = '{' WHERE key = 'cwd'")
    conn.close()

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused.startswith("meta is not JSON: ")
    assert (p.meta, p.values) == ({}, 0)


def test_a_keyed_trace_under_another_key_is_refused(tmp_path):
    """C5: a stamp that names one key has to be true of every digest under
    it, so two keys never meet in one trace."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV, redaction={
        "rule": "v1", "mode": "on", "keyed": True, "key_id": "deadbeef",
        "env": {"API_KEY": "aaaabbbbccccdddd"}, "names": [], "allow": [],
        "by": "recorder", "values": 1})

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused == (f"digests under key deadbeef, the store's is "
                         f"{key.key_id}; nothing rewritten")
    assert (p.meta, p.values) == ({}, 0)


# -- re-application (C5, P2, P4, P5, P6) -----------------------------------

def test_an_unkeyed_mode_on_trace_proceeds_and_becomes_keyed(tmp_path):
    """P6: a null digest loses comparability, never safety. The old nulls
    stay null, the new digest is the store's, and the stamp says keyed."""
    key = _key(tmp_path)
    env = {"API_KEY": redact.REDACTED, "DB_PASSWORD": "hunter2",
           "HOME": "/tmp/u"}
    path = _python(tmp_path, env=env, redaction={
        "rule": "v1", "mode": "on", "keyed": False, "key_id": None,
        "env": {"API_KEY": None}, "names": [], "allow": [],
        "by": "recorder", "values": 1})

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused is None
    assert p.env_names == ("DB_PASSWORD",)
    assert p.meta["redaction"]["env"] == {
        "API_KEY": None, "DB_PASSWORD": key.digest("hunter2")}
    assert p.meta["redaction"]["keyed"] is True
    assert p.meta["redaction"]["key_id"] == key.key_id


def test_a_mode_on_trace_with_nothing_new_is_not_rewritten(tmp_path):
    """P5: a second pass over a retrofitted trace finds nothing and writes
    nothing -- not even a stamp saying today's knobs."""
    key = _key(tmp_path)
    path, first = _settled(tmp_path, key)
    assert first.values == 6                   # the ground this stands on

    p = redact_store.plan(path, key, KNOBS)

    assert (p.meta, p.payloads, p.unwinds, p.outputs) == ({}, {}, {}, {})
    assert (p.env_names, p.values) == ((), 0)
    assert p.rewrites is False
    assert p.changes is True                   # still 0644: the mode alone


def test_a_mode_on_trace_gains_a_name_the_callers_knobs_add(tmp_path):
    """C5's other half: a name NOT in the table is digested now, under the
    store's key, and the previous stamp's count carries (P2).

    `MYCO_HANDLE` fires on nothing rule v1 knows, so the ONLY thing that can
    take it is the `names` list this caller passed -- which is what makes
    `_env_pass`'s `knobs` argument load-bearing rather than decorative.
    """
    key = _key(tmp_path)
    path, first = _settled(tmp_path, key)
    assert redact.fires(HANDLE_NAME, KNOBS) is False    # nothing else does
    env = {**first.meta["env"], HANDLE_NAME: HANDLE}
    _set_meta(path, env=env, env_hash=_json_hash(env),
              redaction={**first.meta["redaction"], "by": "recorder",
                         "values": 3})
    knobs = redact.Knobs.from_environ(
        {"SENSORIUM_REDACT_NAMES": "myco_handle"})

    p = redact_store.plan(path, key, knobs)

    assert p.env_names == (HANDLE_NAME,)
    assert p.values == 0
    assert p.meta["env"][HANDLE_NAME] == redact.REDACTED
    table = p.meta["redaction"]["env"]
    assert table[HANDLE_NAME] == key.digest(HANDLE)
    assert table["API_KEY"] == first.meta["redaction"]["env"]["API_KEY"]
    assert p.meta["redaction"]["values"] == 3
    assert p.meta["redaction"]["names"] == ["MYCOHANDLE"]
    assert p.meta["redaction"]["by"] == "retrofit"


def test_the_callers_allow_list_reaches_the_env_and_the_values(tmp_path):
    """§2.3: allow WINS, and the list the command was given has to reach
    BOTH sites that consume knobs -- `_env_pass`'s `redact.fires` and the
    state `rv.install` publishes for the value pass. `API_KEY` stays
    plaintext in the environment and the RETURN under `get_api_key` is left
    exactly as the recorder wrote it, so neither site can be hardcoded."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    knobs = redact.Knobs.from_environ(
        {"SENSORIUM_REDACT_ALLOW": "api_key,get_api_key"})

    p = redact_store.plan(path, key, knobs)

    assert p.env_names == ()
    assert "env" not in p.meta and "env_hash" not in p.meta
    assert p.meta["redaction"]["env"] == {}
    assert E_RETURN not in p.payloads
    assert p.values == 5                      # the other five still fired
    assert p.meta["redaction"]["allow"] == ["APIKEY", "GETAPIKEY"]


def test_off_knobs_are_ignored_and_the_stamp_is_on(tmp_path):
    """C4: `SENSORIUM_NO_REDACT` is a decision about a RECORDING; running
    `redact` is the decision here, so `mode` is always on.

    Left unforced this is not a no-op but a corruption: `redact.fires`
    ignores `off`, so the pass would take every firing value and digest it,
    and then `redact.meta` would stamp the two-key `mode: "off"` shape over
    an environment whose plaintext is gone -- the digests discarded, the
    trace claiming it was never redacted.
    """
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)

    p = redact_store.plan(path, key,
                          redact.Knobs(True, frozenset(), frozenset()))

    assert p.meta["redaction"]["mode"] == "on"
    assert p.meta["redaction"]["env"] == {
        "API_KEY": key.digest(ENV["API_KEY"])}
    assert p.meta["env"]["API_KEY"] == redact.REDACTED
    assert p.values == 6                      # the value pass ran too


def test_a_marker_value_outside_the_table_is_never_digested(tmp_path):
    """P4: a value that is literally the marker but whose name is in no
    table (a hand-edited trace, a converter from elsewhere) gains no
    digest -- a digest of `<redacted>` is a wrong digest."""
    key = _key(tmp_path)
    path = _python(tmp_path, env={"API_KEY": redact.REDACTED,
                                  "HOME": "/tmp/u"})

    p = redact_store.plan(path, key, KNOBS)

    assert p.env_names == ()
    assert "env" not in p.meta and "env_hash" not in p.meta
    assert p.meta["redaction"]["env"] == {}


def test_a_mode_off_trace_is_redacted_and_stamped_on(tmp_path):
    """§7 read as P5 reads it: running the command IS the decision, so a
    trace recorded under `SENSORIUM_NO_REDACT` is redacted and stamped on --
    and stamped on even when the pass finds nothing left to take."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV, redaction={"rule": "v1", "mode": "off"})

    p = redact_store.plan(path, key, KNOBS)

    assert p.values == 6 and p.env_names == ("API_KEY",)
    assert p.meta["redaction"]["mode"] == "on"
    assert p.meta["redaction"]["by"] == "retrofit"
    assert p.meta["redaction"]["values"] == 6

    _rewrite(path, p)
    _set_meta(path, redaction={"rule": "v1", "mode": "off"})

    again = redact_store.plan(path, key, KNOBS)

    assert again.values == 0
    assert list(again.meta) == ["redaction"]
    assert again.meta["redaction"]["mode"] == "on"
    assert again.rewrites is True


def test_values_is_additive_on_a_previous_stamp(tmp_path):
    """P2: `values` is the sum of the hands' counts. A content hit leaves
    text and not a marker, so what a trace HOLDS cannot be recounted."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV, redaction={
        "rule": "v1", "mode": "on", "keyed": True, "key_id": key.key_id,
        "env": {}, "names": [], "allow": [], "by": "recorder", "values": 5})

    p = redact_store.plan(path, key, KNOBS)

    assert p.values == 6
    assert p.meta["redaction"]["values"] == 11


# -- the old shapes, and the tmp -------------------------------------------

def test_the_format_one_fixture_is_planned(tmp_path):
    """The 18 oldest traces in the store are format 1: no `lang`, no
    `recorder`, and no `events.task_id` column for a query to name."""
    key = _key(tmp_path)
    path = Path(tmp_path) / "sdir" / "traces" / "20260821-090431-646201.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(__file__).parent / "fixtures" / "format1_async.db",
                path)
    conn = sqlite3.connect(path)
    env = {**db.get_meta(conn, "env"), "SECRET_TOKEN": "s3cr3t-value"}
    conn.close()
    _set_meta(path, env=env, env_hash=_json_hash(env))

    p = redact_store.plan(path, key, KNOBS)

    assert p.refused is None and p.skipped is None
    assert p.lang == "python"
    assert p.env_names == ("SECRET_TOKEN",)
    assert p.meta["env"]["SECRET_TOKEN"] == redact.REDACTED
    assert p.meta["env_hash"] == _json_hash(p.meta["env"])


def test_a_live_tmp_refuses_and_a_dead_one_is_swept(tmp_path):
    """C7: a killed retrofit leaves the original whole and a tmp. One whose
    writer is alive holds the trace; one whose writer is gone is litter."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    mine = os.getpid()
    live = path.parent / f".{RUN}.db{redact_store.TMP_SUFFIX}.{mine}.tmp"
    live.write_bytes(b"")

    assert redact_store.live_tmp(path) == (
        f"another redact is rewriting it (pid {mine})")
    refusal = redact_store.plan(path, key, KNOBS)
    assert refusal.refused == f"another redact is rewriting it (pid {mine})"
    assert (refusal.meta, refusal.values) == ({}, 0)
    live.unlink()

    gone = _dead_pid()
    dead = path.parent / f".{RUN}.db{redact_store.TMP_SUFFIX}.{gone}.tmp"
    dead.write_bytes(b"")

    assert redact_store.live_tmp(path) is None
    assert not dead.exists()
    assert redact_store.plan(path, key, KNOBS).refused is None


def test_no_redact_in_the_environment_changes_nothing_here(tmp_path,
                                                           monkeypatch):
    """C4: the knobs are the CALLER's argument. `SENSORIUM_NO_REDACT` is
    ignored -- running the command is the decision -- and `plan` reads no
    environment of its own, so neither knob variable reaches it either."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    monkeypatch.setenv("SENSORIUM_NO_REDACT", "1")
    monkeypatch.setenv("SENSORIUM_REDACT_ALLOW", "API_KEY")

    p = redact_store.plan(path, key, KNOBS)

    assert p.values == 6
    assert p.env_names == ("API_KEY",)
    assert p.meta["redaction"]["mode"] == "on"
    assert p.meta["redaction"]["allow"] == []
