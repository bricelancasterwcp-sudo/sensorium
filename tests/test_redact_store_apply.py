"""`redact_store.apply` -- the one writer, and what a kill leaves behind
(spec C7, C11; plan P1, P5).

Task 2's `plan()` is the whole judgement and writes nothing; this is the
mechanics that put it on disk. The shape is C7's, in order: a private copy
made with SQLite's own backup API into `.<run>.db.redact.<pid>.tmp`, the
rewrite in one transaction, a TRUNCATE checkpoint, an fsync, an
`os.replace`, the directory fsynced, and the ORIGINAL's `-wal`/`-shm`
unlinked last. Every step of that is there because a cheaper one loses
something, so every step below has a falsifier: a byte copy loses committed
WAL pages nobody has checkpointed yet, a rewrite in place leaves a killed
retrofit's trace half redacted, a result carrying its sidecars is a 0600
database beside two 0644 files holding the plaintext pages it just removed.

The traces are Task 2's `_python` builder -- a secret at every site rule v1
reaches, at 0644, which is the mode all 273 traces on this box were
measured at. The assertions read the RESULT, through `Trace.open` and
through raw SQL where the question is about bytes rather than values.
"""
import os
import sqlite3
from pathlib import Path

from sensorium import redact, redact_store
from sensorium.store.reader import Trace
from tests.test_redact_store_plan import (
    E_BENIGN, E_CALL, E_LINE, E_RAISE, E_RETURN, ENV, FR_UNWIND, KNOBS,
    RUN, TOKEN, _key, _python, _set_meta, _settled)

#: Every file `apply` may leave beside a trace it rewrote, as a suffix on
#: the database's own name. The result must have neither (C7).
SIDECARS = ("-wal", "-shm")


def _payload_text(path: Path, eid: int) -> str:
    """One event's payload as it is STORED, not as JSON parses it: the
    byte-identity question P8 answers is about the text in the column."""
    conn = sqlite3.connect(path)
    try:
        return conn.execute(
            "SELECT payload FROM events WHERE id = ?", (eid,)).fetchone()[0]
    finally:
        conn.close()


def _tmps(path: Path) -> list[Path]:
    """Every rewrite tmp beside `path`, whoever's pid is in the name."""
    return sorted(path.parent.glob(f".{path.stem}.db{redact_store.TMP_SUFFIX}"
                                   f".*.tmp"))


def _boom(*_a, **_kw):
    raise OSError("boom")


#: `apply`'s own fsync, captured before any test replaces it.
_REAL_FSYNC = redact_store._fsync


def _no_directory_fsync(path):
    """An `_fsync` that fails on the DIRECTORY and nowhere else: the last
    step of the rewrite, and the only place a failure can arrive after the
    original has already been replaced."""
    if Path(path).is_dir():
        raise OSError("boom")
    _REAL_FSYNC(path)


# -- the rewrite ------------------------------------------------------------

def test_apply_rewrites_only_the_planned_rows(tmp_path):
    """The plan names rows by id and `apply` writes those and no others: the
    four payloads the rule fired on carry their markers, and the benign CALL
    -- which the plan never mentions -- is byte-identical in the result."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    benign_before = _payload_text(path, E_BENIGN)

    p = redact_store.plan(path, key, KNOBS)
    redact_store.apply(p)

    t = Trace.open(path)
    try:
        assert t.event(E_CALL).payload["args"]["token"]["v"] == redact.REDACTED
        assert t.event(E_CALL).payload["args"]["token"]["redacted"] == {
            "by": "name", "digest": key.digest(TOKEN)}
        pair = t.event(E_LINE).payload["deltas"]["headers"]["sample"][0]
        assert pair[1]["v"] == redact.REDACTED
        assert t.event(E_RETURN).payload["value"]["v"] == redact.REDACTED
        assert redact.REDACTED in t.event(E_RAISE).payload["exc"]["msg"]
        assert t.frame(FR_UNWIND).unwind_exc["msg"] == redact.REDACTED
        assert t.output_chunks() == [
            (E_RETURN, "stdout", f"token {redact.REDACTED}\n")]
        meta = t.meta
        assert meta["redaction"]["by"] == "retrofit"
        assert meta["redaction"]["mode"] == "on"
        assert meta["env"]["API_KEY"] == redact.REDACTED
        assert meta["env_hash"] == p.meta["env_hash"]
    finally:
        t._c.close()

    assert _payload_text(path, E_BENIGN) == benign_before
    assert _tmps(path) == []


def test_the_result_is_0600_with_no_sidecars(tmp_path):
    """C7's last step and C11's mode. The `-wal`/`-shm` unlinked are the
    ORIGINAL's -- they belong to the inode `os.replace` displaced, and the
    plaintext pages they hold are exactly what the rewrite removed. A reader
    is holding this trace open, which is the only way they outlive the
    backup's own connection and so the only way to ask the question."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    reader = sqlite3.connect(path)
    try:
        reader.execute("SELECT count(*) FROM meta").fetchone()
        assert all((path.with_name(path.name + s)).exists() for s in SIDECARS)

        redact_store.apply(redact_store.plan(path, key, KNOBS))

        assert os.stat(path).st_mode & 0o777 == 0o600
        for suffix in SIDECARS:
            assert not (path.with_name(path.name + suffix)).exists()
        assert _tmps(path) == []
    finally:
        reader.close()


def test_uncheckpointed_wal_pages_reach_the_result(tmp_path):
    """C7's reason for the backup API over a byte copy: a row committed into
    the `-wal` and not yet checkpointed is in the DATABASE and not in the
    `.db` file. A reader holding the trace open is what keeps the close from
    checkpointing it, which is the state every live store is in."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    reader = sqlite3.connect(path)
    try:
        reader.execute("INSERT INTO output (after_event_id, stream, data) "
                       "VALUES (?, ?, ?)", (E_RETURN, "stdout", "benign\n"))
        reader.commit()

        redact_store.apply(redact_store.plan(path, key, KNOBS))

        after = Trace.open(path)
        try:
            assert [d for _e, _s, d in after.output_chunks()] == [
                f"token {redact.REDACTED}\n", "benign\n"]
        finally:
            after._c.close()
    finally:
        reader.close()


def test_a_failure_mid_rewrite_leaves_the_original_whole_and_no_tmp(
        tmp_path, monkeypatch):
    """C7's crash contract, forced at the last step that can fail: the
    original is untouched until the rename, so a retrofit that dies anywhere
    before it leaves a trace that still reads -- and the tmp it was building
    goes with it rather than becoming litter another run has to sweep."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    before = path.read_bytes()
    p = redact_store.plan(path, key, KNOBS)
    monkeypatch.setattr(os, "replace", _boom)

    try:
        redact_store.apply(p)
    except OSError as e:
        assert str(e) == "boom"
    else:
        raise AssertionError("apply swallowed the failure")

    assert path.read_bytes() == before
    assert os.stat(path).st_mode & 0o777 == 0o644
    assert _tmps(path) == []
    for suffix in SIDECARS:
        assert not (path.with_name(path.name + suffix)).exists()


def test_a_failing_directory_fsync_after_the_rename_still_removes_the_old_sidecars(
        tmp_path, monkeypatch):
    """The window the crash contract does not cover on its own: the rename
    has already happened, so there is no tmp left to clean up, and the
    displaced inode's `-wal` is sitting beside a redacted database holding
    the plaintext pages it just removed. SQLite recovers that log over the
    new file -- which is how a retrofit can appear to have done nothing --
    so the unlink is in a `finally` and runs whether the fsync raised or
    not. A Ctrl-C during an `--all` pass over 273 traces takes the same
    path; only a signal that ends the process outright can leave them."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    reader = sqlite3.connect(path)
    try:
        reader.execute("SELECT count(*) FROM meta").fetchone()
        p = redact_store.plan(path, key, KNOBS)
        assert all((path.with_name(path.name + s)).exists() for s in SIDECARS)
        monkeypatch.setattr(redact_store, "_fsync", _no_directory_fsync)

        try:
            redact_store.apply(p)
        except OSError as e:
            assert str(e) == "boom"
        else:
            raise AssertionError("apply swallowed the failure")

        for suffix in SIDECARS:
            assert not (path.with_name(path.name + suffix)).exists()
        assert _tmps(path) == []
        after = Trace.open(path)                   # the rewrite still landed
        try:
            assert after.meta["redaction"]["by"] == "retrofit"
            assert after.event(E_CALL).payload["args"]["token"]["v"] == (
                redact.REDACTED)
        finally:
            after._c.close()
    finally:
        reader.close()


# -- the mode-only path (C11) ----------------------------------------------

def test_mode_only_plans_chmod_in_place(tmp_path):
    """A trace with nothing left to redact but sitting at 0644 is CHANGED:
    `apply` tightens it and its sidecars where they are. Nothing is copied,
    nothing is renamed, and the database's bytes do not move -- there is no
    rewrite to carry, and a backup round trip would rewrite a file to say
    what it already says."""
    key = _key(tmp_path)
    path, _first = _settled(tmp_path, key)

    p = redact_store.plan(path, key, KNOBS)

    assert (p.rewrites, p.tightens, p.changes) == (False, True, True)
    before = path.read_bytes()
    sidecars = [path.with_name(path.name + s) for s in SIDECARS]
    for sidecar in sidecars:
        sidecar.write_bytes(b"")
        sidecar.chmod(0o644)

    redact_store.apply(p)

    assert os.stat(path).st_mode & 0o777 == 0o600
    for sidecar in sidecars:
        assert sidecar.exists()                    # in place, not unlinked
        assert os.stat(sidecar).st_mode & 0o777 == 0o600
    assert path.read_bytes() == before
    assert _tmps(path) == []


# -- idempotence and the plans that name nothing ---------------------------

def test_a_second_plan_over_the_result_finds_nothing(tmp_path):
    """P5, over the real writer rather than Task 2's test rewrite: a trace
    the command has retrofitted is settled. Nothing to redact, nothing to
    tighten, so the second run would print `nothing to redact` and touch
    the file no further."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    redact_store.apply(redact_store.plan(path, key, KNOBS))

    again = redact_store.plan(path, key, KNOBS)

    assert (again.refused, again.skipped) == (None, None)
    assert again.rewrites is False
    assert again.tightens is False
    assert again.changes is False
    assert (again.env_names, again.values) == ((), 0)


def test_apply_on_a_refused_or_skipped_plan_touches_nothing(tmp_path):
    """A plan that refuses or skips names no rows, and `apply` must not read
    its mode either: a trace another `redact` is rewriting (C7) and one the
    Python recorder still holds open (C8) are both cases where this process
    knows less about the file than somebody else does."""
    key = _key(tmp_path)
    path = _python(tmp_path, env=ENV)
    held = path.parent / (f".{RUN}.db{redact_store.TMP_SUFFIX}"
                          f".{os.getpid()}.tmp")
    held.write_bytes(b"")
    before = path.read_bytes()

    refusal = redact_store.plan(path, key, KNOBS)
    assert refusal.refused is not None
    redact_store.apply(refusal)

    assert path.read_bytes() == before
    assert os.stat(path).st_mode & 0o777 == 0o644
    assert held.exists()                       # not swept by the writer
    held.unlink()

    _set_meta(path, incomplete=True)
    in_flight = redact_store.plan(path, key, KNOBS)
    assert in_flight.skipped is not None
    marked = path.read_bytes()

    redact_store.apply(in_flight)

    assert path.read_bytes() == marked
    assert os.stat(path).st_mode & 0o777 == 0o644
    assert _tmps(path) == []


def test_the_tmp_name_carries_the_pid(tmp_path):
    """C7's name, which `live_tmp` globs and `redact_key.sweep_stale`'s
    sibling rule reads: a dotfile, so no `*.db` walk sees it, and the pid of
    whoever is building it, so a killed run's litter can be told from a
    live run's workspace."""
    path = Path(tmp_path) / f"{RUN}.db"

    tmp = redact_store.tmp_path_for(path)

    assert tmp.parent == path.parent
    assert tmp.name == f".{RUN}.db.redact.{os.getpid()}.tmp"
    assert redact_store.live_tmp(path) is None    # nothing there to glob yet
