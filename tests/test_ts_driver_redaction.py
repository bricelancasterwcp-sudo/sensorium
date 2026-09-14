"""The one thing the TypeScript harness cannot work out for itself about
rule v1: the store's key.

The runtime only ever PARSES `SENSORIUM_REDACT_KEY`. It never creates a key,
never writes one and never reads a key file -- creating one means a
directory, a temporary, a link and a race, and the runtime is linked into
somebody else's test suite. So the driver mints or reads
`<store>/redaction.key` and hands the hex down, exactly as
`cargo-sensorium` does for the Rust runtime, and one key file serves every
language recording into one store.

`tests/test_ts_driver.py` drives the rest of the command end to end; what is
here is the environment hop and the one predicate that keeps the key
variable out of a `refocus` comparison. Its own file because that module is
at 683 lines.
"""
from pathlib import Path

from sensorium import redact
from sensorium.query import refocus_rust, refocus_typescript
from sensorium.ts import driver as driver_mod
from sensorium.ts import harness as harness_mod


def _env(tmp_path: Path) -> dict:
    plan = harness_mod.recognise(["vitest", "run"], tmp_path)
    return driver_mod._env(tmp_path / "spool", "INV", plan, tmp_path / "pkg",
                           "call", [])


def test_the_harness_is_handed_the_stores_key(tmp_path, monkeypatch):
    sdir = tmp_path / "sdir"
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    env = _env(tmp_path)

    key = redact.Key.load(sdir)
    assert key.keyed, key.problem
    assert env[redact.KEY_VAR] == key.material.hex()
    assert len(env[redact.KEY_VAR]) == 64


def test_the_key_is_the_store_s_and_is_minted_once(tmp_path, monkeypatch):
    """A second invocation into one store hands over the SAME key: two
    recordings whose digests were taken under different keys cannot be
    compared, and `refocus` would report every redacted variable as
    unverifiable."""
    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert _env(tmp_path)[redact.KEY_VAR] == _env(tmp_path)[redact.KEY_VAR]


def test_a_store_that_cannot_be_keyed_hands_over_nothing(tmp_path,
                                                         monkeypatch):
    """An empty `redaction.key` is somebody else's file and is never written
    over, so this store stays unkeyed. The driver then sets NO variable
    rather than an empty one -- and POPS the one the launching shell was
    carrying, because a stale key inherited from another store would have
    the recorder write digests nothing in this store can verify.
    """
    sdir = tmp_path / "sdir"
    sdir.mkdir()
    (sdir / redact.KEY_FILE).write_bytes(b"")
    monkeypatch.setenv("SENSORIUM_DIR", str(sdir))
    monkeypatch.setenv(redact.KEY_VAR, "ab" * 32)

    assert redact.KEY_VAR not in _env(tmp_path)


def test_the_key_variable_is_the_recorders_own_in_both_languages():
    """`refocus` exempts the recorder's own bookkeeping from the environment
    comparison, and this variable is the recorder's twice over: it differs
    between two stores by construction, and it is deleted from every
    recorded environment, so a pair would compare a name that is on neither
    side. Both branches answer for it under one prefix; this is what says so
    when either prefix is narrowed.
    """
    assert refocus_typescript.is_recorder_key(redact.KEY_VAR)
    assert refocus_rust._is_recorder_key(redact.KEY_VAR)
