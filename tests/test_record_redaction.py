"""The Python recorder under rule v1: what reaches `meta`, and file modes.

Every test here records a real program through `sensorium run` in a
SUBPROCESS. The rule is applied at the writer, over the recorded process's
own environment, so `monkeypatch.setenv` in this process is not the
environment under test; and a test that patched `redact.Key.load_or_create`
would be asserting against a stub rather than against what a user's store
actually gets. `env_extra` plants the variables; the trace is read back
from the store the subprocess wrote.

Nothing here asserts on the SIZE of `redaction.env`. The recorded process
inherits the launching shell's environment, which on a developer box and on
CI carries names of its own that fire (`SSH_AUTH_SOCK`,
`CLAUDE_CODE_MESSAGING_TOKEN`, `GITHUB_TOKEN`), so an exact count would be
a test of whoever's shell ran it. Membership of the planted names is the
assertion, every time.

The last test is not about the recorder: it is the one file mode on the
Python side that no ingest test can see after the fact, and it is here
because this module is where the mode rule is stated.
"""
import hashlib
import json
import os
import re
import stat
from pathlib import Path

from sensorium import redact
from sensorium.store.reader import Trace
from sensorium.ts import ingest
from tests.helpers import record_script, run_cli

HELLO = "print('hi')\n"

#: A name whose segments are `MY`, `API`, `KEY` -- the rule fires -- beside
#: one whose single segment is in nothing, so each test states both halves
#: of the judgement: what was redacted AND what was left alone.
SECRET, PLAIN = "MY_API_KEY", "PLAIN"
VALUE = "abc123"


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def _record(tmp_path, env_extra) -> tuple[dict, Path]:
    """(the recorded trace's meta, the store it was written to)."""
    run_id, trace, r = record_script(tmp_path, HELLO, env_extra=env_extra)
    assert run_id is not None, f"run failed: {r.stdout}\n{r.stderr}"
    return Trace.open(trace).meta, Path(tmp_path) / "sdir"


def test_secret_named_variable_is_stored_redacted_with_digest(tmp_path):
    meta, sdir = _record(tmp_path, {SECRET: VALUE, PLAIN: "x"})
    env, redaction = meta["env"], meta["redaction"]
    assert env[SECRET] == redact.REDACTED
    assert env[PLAIN] == "x"

    key = redact.Key.load(sdir)
    digest = redaction["env"][SECRET]
    assert re.fullmatch(r"[0-9a-f]{16}", digest), digest
    assert digest == key.digest(VALUE)
    assert PLAIN not in redaction["env"]

    assert redaction["rule"] == "v1"
    assert redaction["mode"] == "on"
    assert redaction["by"] == "recorder"
    assert redaction["keyed"] is True
    assert redaction["key_id"] == key.key_id


def test_env_hash_is_over_the_stored_env(tmp_path):
    """The hash names what the trace HOLDS, not what the process had.

    Two runs with different secrets under one unchanged environment have to
    hash the same, or `env_hash` reports a world change that a reader can
    no longer see the evidence for.
    """
    meta, _ = _record(tmp_path, {SECRET: VALUE})
    assert meta["env"][SECRET] == redact.REDACTED
    assert meta["env_hash"] == hashlib.sha256(
        json.dumps(meta["env"], sort_keys=True).encode()).hexdigest()[:16]


def test_no_redact_knob_stores_plaintext_and_says_so(tmp_path):
    meta, _ = _record(tmp_path / "off",
                      {redact.OFF_VAR: "1", SECRET: VALUE})
    assert meta["env"][SECRET] == VALUE
    assert meta["redaction"] == {"rule": "v1", "mode": "off"}

    # `=0` is not "off" -- it reads like SENSORIUM_NO_INVOCATION_LOG.
    meta, _ = _record(tmp_path / "zero",
                      {redact.OFF_VAR: "0", SECRET: VALUE})
    assert meta["env"][SECRET] == redact.REDACTED
    assert meta["redaction"]["mode"] == "on"


def test_names_and_allow_knobs(tmp_path):
    meta, _ = _record(tmp_path, {redact.NAMES_VAR: "MYCO_THING",
                                 redact.ALLOW_VAR: "my_api_key",
                                 "MYCO_THING": "t", SECRET: VALUE})
    env, redaction = meta["env"], meta["redaction"]
    assert env["MYCO_THING"] == redact.REDACTED
    assert env[SECRET] == VALUE
    assert SECRET not in redaction["env"]
    # Recorded, so a reader sees what the recording was made under.
    assert redaction["names"] == ["MYCOTHING"]
    assert redaction["allow"] == ["MYAPIKEY"]


def test_key_var_is_dropped_not_recorded(tmp_path):
    meta, _ = _record(tmp_path, {redact.KEY_VAR: "00" * 32, PLAIN: "x"})
    assert redact.KEY_VAR not in meta["env"]
    assert redact.KEY_VAR not in meta["redaction"]["env"]
    assert meta["env"][PLAIN] == "x"        # the run did carry an env


def test_created_files_are_0600_and_dirs_0700(tmp_path):
    """A store sensorium creates from nothing, end to end.

    `run_cli` rather than `record_script`, and a store two levels down that
    does not exist yet, because the modes under test are the ones sensorium
    itself applies -- a directory a test made first would be asserting on
    the test's umask.
    """
    (tmp_path / "prog.py").write_text(HELLO)
    store = tmp_path / "fresh" / "store"
    # `=0` is the invocation log's "keep logging": the log is on by default,
    # but a shell that had disabled it would otherwise make this test's
    # `invocations.jsonl` assertion fail for a reason unrelated to modes.
    r = run_cli(["run", "--", "prog.py"], cwd=tmp_path, sensorium_dir=store,
                env_extra={"SENSORIUM_NO_INVOCATION_LOG": "0"})
    m = re.search(r"^run: (\S+)$", r.stdout, re.M)
    assert m is not None, f"run failed: {r.stdout}\n{r.stderr}"
    trace = store / "traces" / f"{m.group(1)}.db"

    assert _mode(store) == 0o700
    assert _mode(store / "traces") == 0o700
    assert _mode(trace) == 0o600
    assert _mode(store / redact.KEY_FILE) == 0o600
    assert _mode(store / "invocations.jsonl") == 0o600
    # sqlite's unix VFS gives a sidecar the database file's mode; both are
    # normally gone by the time the connection closes, so this binds only
    # when one survived.
    for sidecar in (Path(f"{trace}-wal"), Path(f"{trace}-shm")):
        if sidecar.exists():
            assert _mode(sidecar) == 0o600, sidecar.name


def test_unreadable_key_records_unkeyed(tmp_path):
    """No key is a lost COMPARISON, never a lost redaction.

    The key is planted as a 0-byte file rather than patched: the recorder
    runs in another process, where this one's monkeypatches do not reach,
    and `load_or_create` never writes over a `redaction.key` that is
    already there, whatever it says.
    """
    sdir = tmp_path / "sdir"
    sdir.mkdir(parents=True)
    (sdir / redact.KEY_FILE).write_bytes(b"")

    meta, _ = _record(tmp_path, {SECRET: VALUE})
    redaction = meta["redaction"]
    assert redaction["keyed"] is False
    assert redaction["key_id"] is None
    assert redaction["env"][SECRET] is None
    assert set(redaction["env"].values()) == {None}
    assert meta["env"][SECRET] == redact.REDACTED
    assert redact.Key.load(sdir).problem is not None


# -- the one mode an ingest test cannot see -------------------------------

def test_the_ts_ingest_reservation_is_0600_while_it_is_reserved(tmp_path):
    """`ts/ingest._reserve` creates the trace file before sqlite ever does.

    `db.create_trace` fchmods whatever file it is handed, so a converted
    trace is 0600 whichever mode the reservation used -- which leaves the
    reservation's own constant pinned by nothing an ingest test can read
    after the conversion has finished. The window it governs is real: the
    file sits reserved from here until the builder opens it, and a spool's
    converted environment goes into it. So it is read while the file is
    still only reserved, which is the only moment the constant is visible.
    """
    traces = tmp_path / "traces"
    traces.mkdir(parents=True)
    _run_id, reserved = ingest._reserve(traces, 1700000000.0)
    assert _mode(reserved) == 0o600
