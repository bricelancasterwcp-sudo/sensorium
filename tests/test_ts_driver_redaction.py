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
here is the environment hop, the one predicate that keeps the key variable
out of a `refocus` comparison, and the modes every path this driver creates
is created with. Its own file because that module is at 683 lines.
"""
from pathlib import Path

import pytest

from sensorium import redact
from sensorium.query import refocus_rust, refocus_typescript
from sensorium.ts import driver as driver_mod
from sensorium.ts import harness as harness_mod
from sensorium.ts import pkg as pkg_mod
from tests.helpers import run_cli
from tests.test_ts_driver import LIB, SKIP, TEST


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


# -- the modes, end to end --------------------------------------------------
@pytest.fixture
def project(tmp_path):
    """`test_ts_driver.py`'s `node --test` project: two files and the one
    dependency the loader hook resolves from the ROOT. Copied rather than
    imported, as `test_ts_driver_focus.py` copies it, so that a module whose
    other tests need no Node holds its own fixture."""
    root = tmp_path / "app"
    (root / "node_modules").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "app", "type": "module"}\n')
    (root / "lib.ts").write_text(LIB)
    (root / "a.test.ts").write_text(TEST % 3)
    (root / "node_modules" / "typescript").symlink_to(
        pkg_mod.locate() / "node_modules" / "typescript")
    return root


@pytest.mark.skipif(SKIP is not None, reason=SKIP or "")
def test_every_path_a_run_creates_under_the_spool_is_private(project,
                                                             tmp_path):
    """§5.5 is categorical: every file this recorder writes is 0600 and
    every directory 0700, AT CREATION.

    Measured otherwise by E16 part A (H2, ten paths at 0775/0664): the
    driver made its spool with a bare `mkdir(parents=True)` and wrote
    `invocation.json`, `harness.json`, `ingested.json` and the plugin's
    `manifests/*.json` with plain `write_text`/`writeFileSync`, so all of
    them landed at whatever the umask allowed -- 0775/0664 on that box.
    Only the files carrying a recorded ENVIRONMENT were private, and a
    record holding the user's argv and their project paths beside them is
    not a footnote.

    A sweep and not a list: the point is that no path under the spool
    escapes, and a test naming six files would say nothing about the
    seventh somebody adds. The named-presence check below is what stops an
    empty sweep from passing.
    """
    sdir = tmp_path / "sdir"
    r = run_cli(["ts", "run", "--", "node", "--test", "a.test.ts"],
                cwd=project, sensorium_dir=sdir)
    assert r.returncode == 0, r.stderr

    spool_root = sdir / "spool"
    spools = sorted(p for p in spool_root.iterdir() if p.is_dir())
    assert len(spools) == 1, spools
    spool = spools[0]

    wrong = {}
    for path in (spool_root, spool, *sorted(spool.rglob("*"))):
        want = 0o700 if path.is_dir() else 0o600
        mode = path.stat().st_mode & 0o7777
        if mode != want:
            wrong[str(path.relative_to(sdir))] = f"{mode:o}, want {want:o}"
    assert wrong == {}

    # What the sweep had to have walked. `manifests/` is the loader hook's,
    # written from inside the harness; the other three are the driver's own,
    # and the `.jsonl` is the runtime's spool.
    assert {"invocation.json", "harness.json", "ingested.json",
            "manifests"} <= {p.name for p in spool.iterdir()}
    assert any(p.suffix == ".jsonl" for p in spool.iterdir()), sorted(spool)
    assert sorted((spool / "manifests").iterdir())
