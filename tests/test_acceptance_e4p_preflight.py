"""The E4′ preflight's env-parity guard.

WHY IT EXISTS
-------------
The licence compares the environment the ORIGINAL executed under with the
one the RE-RUN did, and both come from the recording process's own. Task 5b
taught the check to read a relocated `CARGO_TARGET_DIR` as the same world,
which covers the difference §1.4 introduces on purpose. It does NOT cover a
difference between the SHELL E4 was launched from and the shell E4′ is
launched from — and a scan of the 61 originals found three:
`PYTHONDONTWRITEBYTECODE`, `SSL_CERT_DIR`, `SSL_CERT_FILE`.

The launcher now exports all three. This guard is what makes that pinning
MECHANICAL rather than a line on a checklist: the runner compares its own
`os.environ` against every one of the 61 recorded environments and refuses
to start when they part company, before a single copy is made and long
before a number is read.

Excluded, and each for a reason the record already states somewhere else:
`^(CARGO|RUST|SENSORIUM|LD_)` are the recorder's own and the target root's
(they differ BY DESIGN — the fresh target of §1.4 — and `refocus_env` is
what judges them), and `_`, `OLDPWD`, `PWD`, `SHLVL` are the shell
bookkeeping `refocus_world._UNCOMPARED_ENV` already refuses to compare.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4p_preflight as pre                             # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

#: A recorded environment shaped like the kept originals': the shell's own
#: keys, the recorder's, and the ones cargo derives from the target root.
BASE = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/someone",
    "PYTHONDONTWRITEBYTECODE": "1",
    "SSL_CERT_DIR": "/usr/lib/ssl/certs",
    "SSL_CERT_FILE": "/usr/lib/ssl/cert.pem",
    "CARGO_TARGET_DIR": "/build/target-a",
    "RUSTUP_TOOLCHAIN": "stable",
    "SENSORIUM_DIR": "/store/a",
    "LD_LIBRARY_PATH": "/build/target-a/debug",
    "_": "/usr/bin/env",
    "PWD": "/somewhere",
    "OLDPWD": "/elsewhere",
    "SHLVL": "3",
}


def _store(tmp_path, envs) -> Path:
    """A kept store holding one trace per recorded environment."""
    traces = tmp_path / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    for run, env in envs.items():
        con = sqlite3.connect(traces / f"{run}.db")
        try:
            con.execute("create table meta (key text primary key, "
                        "value text)")
            con.execute("insert into meta values ('run_id', ?)",
                        (json.dumps(run),))
            con.execute("insert into meta values ('env', ?)",
                        (json.dumps(env),))
            con.commit()
        finally:
            con.close()
    return tmp_path


def _rows(*runs):
    return [(i, f"n{i}", "t", run) for i, run in enumerate(runs, 1)]


# ------------------------------------------------------------------ passes

def test_an_identical_environment_PASSES_and_is_recorded(tmp_path):
    """Recorded either way: "the 61 recorded environments and this process's
    agree" is a lens fact of the run, and a check whose passing leaves no
    trace cannot be audited afterwards."""
    kept = _store(tmp_path, {"r-1": BASE, "r-2": BASE})
    rec = pre.env_parity(kept, _rows("r-1", "r-2"), environ=dict(BASE))
    assert rec["checked"] == 2
    assert rec["differing"] == []
    assert rec["compared_keys"]
    assert "PYTHONDONTWRITEBYTECODE" in rec["compared_keys"]


@pytest.mark.parametrize("key, value", [
    ("CARGO_TARGET_DIR", "/build/target-b"),
    ("CARGO_BIN_EXE_app", "/build/target-b/debug/app"),
    ("RUSTUP_TOOLCHAIN", "nightly"),
    ("RUSTDOCFLAGS", "--extern x=/build/target-b/y"),
    ("SENSORIUM_DIR", "/store/b"),
    ("SENSORIUM_TIER", "line"),
    ("LD_LIBRARY_PATH", "/build/target-b/debug"),
])
def test_the_recorders_own_and_the_target_roots_keys_are_EXCLUDED(
        tmp_path, key, value):
    """These differ BY DESIGN — §1.4 gives the re-run a fresh target and the
    recorder mints its own variables per invocation — and `refocus_env` is
    what judges them, one check along. A guard that compared them would
    refuse every launch it was written to protect.

    This is also the test the exclusion regex is mutated against: drop it
    and every one of these false-fires.
    """
    kept = _store(tmp_path, {"r-1": BASE})
    rec = pre.env_parity(kept, _rows("r-1"), environ=dict(BASE, **{key: value}))
    assert rec["differing"] == []
    assert key not in rec["compared_keys"]


@pytest.mark.parametrize("key", ["_", "OLDPWD", "PWD", "SHLVL"])
def test_the_shells_own_bookkeeping_is_EXCLUDED(tmp_path, key):
    """`refocus_world._UNCOMPARED_ENV`'s names, for its reasons: `PWD` names
    the calling shell and `os.chdir` does not update it."""
    kept = _store(tmp_path, {"r-1": BASE})
    rec = pre.env_parity(kept, _rows("r-1"),
                         environ=dict(BASE, **{key: "moved"}))
    assert rec["differing"] == []
    assert key not in rec["compared_keys"]


# ---------------------------------------------------------------- refusals

def test_a_key_whose_VALUE_differs_is_a_refusal_naming_it(tmp_path):
    """The case the scan of the 61 actually found."""
    kept = _store(tmp_path, {"r-1": BASE})
    with pytest.raises(Refused) as e:
        pre.env_parity(kept, _rows("r-1"),
                       environ=dict(BASE, SSL_CERT_DIR="/etc/ssl/certs"))
    assert "SSL_CERT_DIR" in str(e.value)
    assert "r-1" in str(e.value)


def test_a_key_MISSING_from_this_process_is_a_refusal(tmp_path):
    """Recorded but not exported: the licence would report it as a change
    the world made on all 61."""
    environ = dict(BASE)
    del environ["PYTHONDONTWRITEBYTECODE"]
    kept = _store(tmp_path, {"r-1": BASE})
    with pytest.raises(Refused) as e:
        pre.env_parity(kept, _rows("r-1"), environ=environ)
    assert "PYTHONDONTWRITEBYTECODE" in str(e.value)


def test_a_key_ADDED_by_this_process_is_a_refusal_too(tmp_path):
    """A variable this shell carries and E4's did not is the same finding
    from the other side — the env check compares a SET, not a subset."""
    kept = _store(tmp_path, {"r-1": BASE})
    with pytest.raises(Refused) as e:
        pre.env_parity(kept, _rows("r-1"), environ=dict(BASE, CI="true"))
    assert "CI" in str(e.value)


def test_EVERY_offending_key_and_original_is_named_in_ONE_refusal(tmp_path):
    """One launch reports all of them. A refusal that named the first would
    cost one detached launch per key to discover the rest."""
    other = dict(BASE, SSL_CERT_FILE="/etc/ssl/cert.pem")
    kept = _store(tmp_path, {"r-1": BASE, "r-2": other})
    with pytest.raises(Refused) as e:
        pre.env_parity(kept, _rows("r-1", "r-2"),
                       environ=dict(BASE, SSL_CERT_DIR="/etc/ssl/certs"))
    message = str(e.value)
    assert "SSL_CERT_DIR" in message and "SSL_CERT_FILE" in message
    assert "r-1" in message and "r-2" in message


def test_an_original_that_records_NO_environment_is_a_refusal(tmp_path):
    """None-vs-empty at the guard: a trace with no `env` key cannot be shown
    to agree with anything, and passing it would be a check that skipped
    the row it could not read."""
    traces = tmp_path / "traces"
    traces.mkdir(parents=True)
    con = sqlite3.connect(traces / "r-1.db")
    con.execute("create table meta (key text primary key, value text)")
    con.execute("insert into meta values ('run_id', '\"r-1\"')")
    con.commit()
    con.close()
    with pytest.raises(Refused) as e:
        pre.env_parity(tmp_path, _rows("r-1"), environ=dict(BASE))
    assert "r-1" in str(e.value)
    assert "no recorded environment" in str(e.value)


def test_a_missing_original_is_a_refusal_rather_than_a_skipped_row(tmp_path):
    kept = _store(tmp_path, {"r-1": BASE})
    with pytest.raises(Refused) as e:
        pre.env_parity(kept, _rows("r-1", "r-2"), environ=dict(BASE))
    assert "r-2" in str(e.value)


# ----------------------------------------------------- the guard's placing

def test_the_guard_runs_BEFORE_any_copy_and_before_the_driver_build():
    """§1.4's rule 4 by its words: everything here is before any number, so
    a refusal is the INFRASTRUCTURE kill. It must also be before
    `copy_originals`, or a refused launch leaves 61 copies behind for the
    next one to trip over as a non-fresh store."""
    src = (REPO / "rust" / "tests" / "acceptance_e4p_preflight.py").read_text()
    body = src[src.index("def preflight("):]
    # `(parity or env_parity)(...)` — E4″ passes its own session-aware guard
    # through this parameter, and the ORDER is what this test is about.
    assert body.index("parity_rec = ") < body.index("build_driver(")
    assert body.index("cargo_running()") < body.index("build_driver(")
    runner = (REPO / "rust" / "tests" / "acceptance_e4p.py").read_text()
    main = runner[runner.index("def main(argv)"):]
    assert main.index("preflight(paths, cfg)") < main.index("copy_originals(")


def test_the_launcher_exports_every_key_the_scan_of_the_61_found():
    """The three the controller's scan found, pinned in the launcher so the
    guard passes for the right reason rather than being loosened."""
    launch = (REPO / ".superpowers" / "sdd"
              / "2026-09-07-sensorium-rung4-debts" / "acceptance-e4p"
              / "launch.sh")
    if not launch.is_file():
        pytest.skip("the launcher is ledger-local and not in this checkout")
    text = launch.read_text()
    for key in ("PYTHONDONTWRITEBYTECODE", "SSL_CERT_DIR", "SSL_CERT_FILE"):
        assert f"export {key}=" in text, key


# ------------------------------------------- gap 2: the version probe

def test_the_version_probe_reads_the_INSTALLED_distribution_token():
    """The token, from `importlib.metadata` — and a `reason` of `None`,
    because there was nothing to explain."""
    probe = pre.version_probe(REPO / ".venv" / "bin" / "python")
    assert probe["token"], probe
    assert probe["reason"] is None
    assert probe["rc"] == 0
    assert "importlib.metadata" in probe["command"]


def test_a_FAILED_probe_records_null_WITH_its_reason_and_never_a_blank():
    """E4′ §5's gap 2, closed. `out()` captured stdout only, so a probe
    that raised put an empty string in the lens where a reader saw a
    measured token. A failed probe is `null` and the reason is the
    interpreter's own last line."""
    probe = pre.version_probe(REPO / ".venv" / "bin" / "python",
                              "no_such_distribution_e4p")
    assert probe["token"] is None
    assert probe["token"] != ""
    assert probe["reason"]
    assert "no_such_distribution_e4p" in probe["reason"] or probe["rc"] != 0
    assert probe["rc"] != 0


def test_the_attribute_probe_is_the_same_shape_and_never_a_blank():
    """`sensorium` has no `__version__`, so this probe FAILS on this box —
    which is the point: it records `null` with the `AttributeError`, not
    the empty string E4′ published."""
    probe = pre.attribute_probe(REPO / ".venv" / "bin" / "python")
    assert set(probe) >= {"token", "reason", "rc", "command", "source"}
    assert probe["token"] is None or probe["token"] != ""
    if probe["token"] is None:
        assert probe["reason"]


def test_a_probe_that_prints_NOTHING_and_exits_zero_is_still_not_measured():
    """A blank stdout with rc 0 is the shape that made `""` look measured.
    It is `null` with a reason of its own."""
    probe = pre._probe(REPO / ".venv" / "bin" / "python", "pass", "nothing")
    assert probe["token"] is None
    assert probe["reason"]
    assert "printed nothing" in probe["reason"]
