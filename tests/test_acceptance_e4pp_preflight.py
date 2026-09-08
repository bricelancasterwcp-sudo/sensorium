"""E4″'s launch guard: what it may refuse on, and what it must only record.

§1.3's three rules, and they are not symmetrical.

1. Every key OUTSIDE session set 1 must match. A difference there is a
   refusal to launch, before any number, because it is an uncontrolled
   instrument variable rather than a subject property.
2. Every key INSIDE the set that differs is recorded BY NAME, before any
   refocus runs, into `pins.session_keys_differing`. H4 and H6 compare the
   printed lines against THAT recorded set -- never against a set read out
   of the same lines they are checking.
3. A different differing-set on the day is REPORTED, not a STOP: the launch
   shell is the instrument's, not the subject's.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4pp_preflight as pre                            # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402

BASE = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/someone",
    "PYTHONDONTWRITEBYTECODE": "1",
    "SSL_CERT_DIR": "/usr/lib/ssl/certs",
    "SSL_CERT_FILE": "/usr/lib/ssl/cert.pem",
    "CARGO_TARGET_DIR": "/build/target-a",
    "CLAUDE_CODE_SESSION_ID": "the-original-session",
    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
    "_": "/usr/bin/env",
    "PWD": "/somewhere",
}


def _store(tmp_path, envs) -> Path:
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


# ------------------------------------------------------------ rule 1

def test_an_identical_environment_PASSES_and_is_RECORDED(tmp_path):
    kept = _store(tmp_path, {"r-1": BASE, "r-2": BASE})
    rec = pre.session_parity(kept, _rows("r-1", "r-2"), environ=dict(BASE))
    assert rec["guard"] == "session_parity"
    assert rec["checked"] == 2
    assert rec["differing"] == []
    assert rec["session_differs"] == []
    assert "PYTHONDONTWRITEBYTECODE" in rec["compared_keys"]


@pytest.mark.parametrize("key, value", [
    ("SSL_CERT_DIR", "/etc/ssl/certs"),
    ("HOME", "/home/someone-else"),
    ("PYTHONDONTWRITEBYTECODE", ""),
])
def test_a_key_OUTSIDE_the_session_set_is_a_REFUSAL_naming_it(
        tmp_path, key, value):
    """Rule 1. The launcher satisfies this by EXPORTING the keys, never by
    exempting them."""
    kept = _store(tmp_path, {"r-1": BASE})
    with pytest.raises(Refused) as e:
        pre.session_parity(kept, _rows("r-1"),
                           environ=dict(BASE, **{key: value}))
    assert key in str(e.value)
    assert "session set 1" in str(e.value)


def test_EVERY_offending_key_is_named_in_ONE_refusal(tmp_path):
    """A refusal that named the first would cost one detached launch per
    key to discover the rest."""
    kept = _store(tmp_path, {"r-1": BASE})
    mine = dict(BASE, HOME="/elsewhere")
    mine.pop("SSL_CERT_FILE")
    mine["A_NEW_ONE"] = "1"
    with pytest.raises(Refused) as e:
        pre.session_parity(kept, _rows("r-1"), environ=mine)
    for key in ("HOME", "SSL_CERT_FILE", "A_NEW_ONE"):
        assert key in str(e.value)


# ------------------------------------------------------------ rule 2

@pytest.mark.parametrize("key", ["CLAUDE_CODE_SESSION_ID",
                                 "DBUS_SESSION_BUS_ADDRESS", "TMUX",
                                 "SSH_AUTH_SOCK"])
def test_a_SESSION_key_that_differs_is_ALLOWED_and_named(tmp_path, key):
    """Rule 2: recorded by name, before any refocus runs. `TMUX` is the
    ADDED case -- a re-run launched inside tmux carries a key the original
    never had, which is the same fact about the launcher as a changed
    value."""
    kept = _store(tmp_path, {"r-1": BASE})
    rec = pre.session_parity(kept, _rows("r-1"),
                             environ=dict(BASE, **{key: "moved"}))
    assert rec["session_differs"] == [key]
    assert rec["differing"] == []
    assert rec["session_detail"][key]["how"]


def test_a_session_key_MISSING_from_this_process_is_also_a_difference(
        tmp_path):
    """A SET is compared, not a subset: the licence would see the absence
    as a difference either way."""
    kept = _store(tmp_path, {"r-1": BASE})
    mine = dict(BASE)
    mine.pop("CLAUDE_CODE_SESSION_ID")
    rec = pre.session_parity(kept, _rows("r-1"), environ=mine)
    assert rec["session_differs"] == ["CLAUDE_CODE_SESSION_ID"]
    assert "MISSING" in rec["session_detail"]["CLAUDE_CODE_SESSION_ID"]["how"]


def test_the_differing_set_is_SORTED_and_deduplicated_over_the_originals(
        tmp_path):
    """One name per key however many originals carry it: H4 compares the
    printed set by NAME and by SIZE against this list."""
    kept = _store(tmp_path, {"r-1": BASE, "r-2": BASE, "r-3": BASE})
    rec = pre.session_parity(kept, _rows("r-1", "r-2", "r-3"),
                             environ=dict(BASE, TMUX="/tmp/s",
                                          CLAUDE_CODE_SESSION_ID="new"))
    assert rec["session_differs"] == ["CLAUDE_CODE_SESSION_ID", "TMUX"]
    assert rec["session_differs_n"] == 2


def test_a_DIFFERENT_differing_set_is_reported_and_never_a_stop(tmp_path):
    """Rule 3: which session variables this box's shell happens to carry on
    the day is a fact about the LAUNCHER. The guard names the expectation
    beside what it found and does not refuse."""
    kept = _store(tmp_path, {"r-1": BASE})
    rec = pre.session_parity(kept, _rows("r-1"),
                             environ=dict(BASE, SSH_TTY="/dev/pts/9"))
    assert rec["session_differs"] == ["SSH_TTY"]
    assert rec["expected_session_differs"] == ["CLAUDE_CODE_SESSION_ID"]
    assert rec["session_set_as_expected"] is False
    assert rec["reported_never_a_stop"]


# ----------------------------------------------- an unreadable original

def test_an_original_with_NO_recorded_environment_is_a_refusal(tmp_path):
    """Not a smaller N: an original the guard cannot read is one it cannot
    vouch for, and the guard's whole job is before the first number."""
    traces = tmp_path / "traces"
    traces.mkdir(parents=True)
    con = sqlite3.connect(traces / "r-1.db")
    con.execute("create table meta (key text primary key, value text)")
    con.execute("insert into meta values ('run_id', ?)", (json.dumps("r-1"),))
    con.commit()
    con.close()
    with pytest.raises(Refused) as e:
        pre.session_parity(tmp_path, _rows("r-1"), environ=dict(BASE))
    assert "r-1" in str(e.value)


# --------------------------------------------- the arm originals' env

def test_the_arm_originals_environments_are_MERGED_for_arm_Cs_choice(
        tmp_path):
    """Arm C runs FOUR rows, so "the original's recorded environment" is
    every one of the four: a key absent from the union is absent from each,
    which is the strict reading and the only one that holds for all four
    invocations."""
    kept = _store(tmp_path, {"r-1": dict(BASE, TMUX="/tmp/a"),
                             "r-2": dict(BASE, SSH_TTY="/dev/pts/1")})
    got = pre.arm_original_env(kept, _rows("r-1", "r-2"))
    assert got["read"] == ["r-1", "r-2"]
    assert "TMUX" in got["env"] and "SSH_TTY" in got["env"]
    assert got["unreadable"] == []


def test_NO_original_could_be_read_is_a_refusal_not_an_empty_environment(
        tmp_path):
    """An empty union would make EVERY candidate look absent, and arm C
    would inject a key the original already carried."""
    (tmp_path / "traces").mkdir(parents=True)
    with pytest.raises(Refused) as e:
        pre.arm_original_env(tmp_path, _rows("r-1"))
    assert "r-1" in str(e.value)


# ============ fix round 1: minor (f) — the refusal's two sentences ========

def test_an_UNREADABLE_original_alone_does_not_print_zero_keys_differ(
        tmp_path):
    """A guard that said "0 key(s) differ:" when the only fault was an
    original it could not read would send a reader hunting a key that does
    not exist."""
    traces = tmp_path / "traces"
    traces.mkdir(parents=True)
    con = sqlite3.connect(traces / "r-1.db")
    con.execute("create table meta (key text primary key, value text)")
    con.execute("insert into meta values ('run_id', ?)", (json.dumps("r-1"),))
    con.commit()
    con.close()
    with pytest.raises(Refused) as e:
        pre.session_parity(tmp_path, _rows("r-1"), environ=dict(BASE))
    text = str(e.value)
    assert "0 key(s) differ" not in text
    assert "could not be read out of the kept store" in text
    assert "r-1" in text


def test_a_REAL_key_difference_still_names_every_key(tmp_path):
    """The other branch, unchanged."""
    kept = _store(tmp_path, {"r-1": BASE})
    with pytest.raises(Refused) as e:
        pre.session_parity(kept, _rows("r-1"),
                           environ=dict(BASE, HOME="/elsewhere"))
    assert "1 key(s) differ" in str(e.value)
    assert "HOME" in str(e.value)
