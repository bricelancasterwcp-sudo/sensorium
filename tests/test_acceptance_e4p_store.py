"""§1.3: how the 61 originals reach a fresh store, and the proof the kept one
was never written.

The statement is pre-registered verbatim -- `VACUUM INTO '<dst>'` -- and its
EXECUTOR is a lens fact: the `sqlite3` CLI where one is on `PATH`, or
Python's `sqlite3` module running the identical SQL. Neither changes the
bytes the statement produces, and §1.3 requires the record to say which ran.

The kept store is READ-ONLY for the whole run. Every test below is about one
of the two ways that can be false: a write through the copy itself, and a
write nobody notices because nothing was measured before and after.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "rust" / "tests"))

import acceptance_e4p_store as st                                  # noqa: E402
from acceptance_lib import Refused                                 # noqa: E402


def _trace(path: Path, run_id: str) -> Path:
    """A trace shaped the way the store writes one: a `meta` table whose
    values are `json.dumps`ed, which is what makes the run-id check real."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.execute("create table meta (key text primary key, value text)")
        con.execute("insert into meta values ('run_id', ?)",
                    (f'"{run_id}"',))
        con.execute("create table events (id integer primary key, k text)")
        con.executemany("insert into events (k) values (?)",
                        [("e",)] * 50)
        con.commit()
    finally:
        con.close()
    return path


# ------------------------------------------------------------- the statement

def test_the_statement_is_1_3s_verbatim():
    """The pre-registered SQL, spelled once. A copy made by `shutil` would
    carry an un-checkpointed WAL; a copy made by a different statement would
    not be the one §1.3 locked."""
    assert st.VACUUM_INTO == "VACUUM INTO '{dst}'"
    assert st.vacuum_sql(Path("/x/y.db")) == "VACUUM INTO '/x/y.db'"


@pytest.mark.parametrize("bad", ["/x/it's.db", "/x/a\nb.db", "/x/a\"b.db"])
def test_a_path_that_could_break_out_of_the_quotes_is_REFUSED(bad):
    """`VACUUM INTO` takes no parameter, so the destination is interpolated
    -- and a path that could close the quote is refused rather than escaped.
    Every path this record uses comes from an environment variable, so the
    check is on the one thing that is not this module's own."""
    with pytest.raises(Refused) as e:
        st.vacuum_sql(Path(bad))
    assert "quote" in str(e.value) or "newline" in str(e.value)


def test_the_engine_that_ran_it_is_RECORDED_not_assumed(tmp_path):
    """§1.3: "§2 records which was used and the SQLite library version,
    because they are lens facts". `sqlite3` is absent from this box, so the
    module executes the identical SQL itself -- and says so."""
    src = _trace(tmp_path / "kept" / "traces" / "r-1.db", "r-1")
    out = st.copy_one(src, tmp_path / "fresh" / "traces" / "r-1.db", "r-1")
    assert out["engine"] in ("sqlite3 CLI", "python sqlite3 module")
    assert out["sqlite_version"] == sqlite3.sqlite_version
    assert out["statement"] == st.vacuum_sql(
        tmp_path / "fresh" / "traces" / "r-1.db")
    assert out["copied"] is True


def test_the_copy_is_verified_by_its_OWN_run_id(tmp_path):
    """§1.3: "after each copy, the destination's `meta.run_id` is read and
    must equal `<run>`; a mismatch is a refusal to start ... never a
    silently renamed file"."""
    src = _trace(tmp_path / "kept" / "traces" / "r-1.db", "someone-else")
    with pytest.raises(Refused) as e:
        st.copy_one(src, tmp_path / "fresh" / "traces" / "r-1.db", "r-1")
    assert "someone-else" in str(e.value)


def test_a_missing_original_is_a_refusal_to_start_and_NOT_a_smaller_N(
        tmp_path):
    """§1.1: "a missing or duplicated original is a refusal to start, not a
    smaller N"."""
    with pytest.raises(Refused) as e:
        st.copy_one(tmp_path / "kept" / "traces" / "nope.db",
                    tmp_path / "fresh" / "traces" / "nope.db", "nope")
    assert "nope" in str(e.value)


def test_a_duplicate_run_id_in_the_table_is_REFUSED_before_anything_copies(
        tmp_path):
    rows = [(1, "a", "t", "r-1"), (2, "b", "t", "r-1")]
    with pytest.raises(Refused) as e:
        st.check_the_originals(tmp_path, rows)
    assert "duplicat" in str(e.value).lower()


def test_every_missing_original_is_named_in_ONE_refusal(tmp_path):
    """One launch reports all of them: a refusal that named the first would
    cost one full re-copy per missing file to discover the rest."""
    kept = tmp_path / "traces"
    kept.mkdir(parents=True)
    _trace(kept / "r-1.db", "r-1")
    rows = [(1, "a", "t", "r-1"), (2, "b", "t", "r-2"), (3, "c", "t", "r-3")]
    with pytest.raises(Refused) as e:
        st.check_the_originals(tmp_path, rows)
    assert "r-2" in str(e.value) and "r-3" in str(e.value)
    assert "r-1" not in str(e.value)


# ------------------------------------------------- the read-only proof

def test_the_kept_stores_mtimes_are_censused_before_and_after(tmp_path):
    """§1.3's proof: "the `st_mtime` (and size) of every one of `<kept>`'s
    `.db` files is recorded before and after the whole run, and §2 states
    that the two lists are identical"."""
    kept = tmp_path / "kept"
    _trace(kept / "traces" / "r-1.db", "r-1")
    _trace(kept / "traces" / "r-2.db", "r-2")
    before = st.store_census(kept)
    assert before["n"] == 2
    assert set(before["files"]) == {"r-1.db", "r-2.db"}
    after = st.store_census(kept)
    assert st.census_diff(before, after) == []


def test_a_SINGLE_changed_mtime_is_found_and_NAMED(tmp_path):
    """A STOP under §1.4's rule 5 (the kill whose WORDS are "a `.FAILED`
    after any number has been read is a STOP"; the locked text's index
    beside it is off by one and is corrected in §2, never here). The test
    that matters is that the diff can FIND one -- a census compared by count
    alone would call two stores with the same number of files identical."""
    kept = tmp_path / "kept"
    db = _trace(kept / "traces" / "r-1.db", "r-1")
    before = st.store_census(kept)
    import os
    stat = db.stat()
    os.utime(db, (stat.st_atime, stat.st_mtime + 100))
    diff = st.census_diff(before, st.store_census(kept))
    assert len(diff) == 1
    assert "r-1.db" in diff[0]


def test_a_file_that_APPEARS_in_the_kept_store_is_a_difference_too(tmp_path):
    kept = tmp_path / "kept"
    _trace(kept / "traces" / "r-1.db", "r-1")
    before = st.store_census(kept)
    _trace(kept / "traces" / "r-2.db", "r-2")
    diff = st.census_diff(before, st.store_census(kept))
    assert any("r-2.db" in d for d in diff)


def test_the_copy_opens_the_SOURCE_read_only(tmp_path):
    """Belt and braces over the census: the source connection is opened
    `mode=ro`, so a bug in this module cannot write the input it measures.
    Asserted by trying to write through the very connection it uses."""
    src = _trace(tmp_path / "kept" / "traces" / "r-1.db", "r-1")
    con = st.connect_ro(src)
    try:
        with pytest.raises(sqlite3.OperationalError):
            con.execute("insert into meta values ('x', '1')")
    finally:
        con.close()


# -------------------------------------------------- the fresh store's state

def test_the_fresh_store_holds_ONLY_the_copies_when_the_loop_opens(tmp_path):
    """§1.3: "`<fresh>` holds only those 61 files and nothing else at that
    moment -- no refocused trace, no earlier run, no leftover -- which §2
    records as a listing count"."""
    kept, fresh = tmp_path / "kept", tmp_path / "fresh"
    rows = []
    for i in (1, 2):
        _trace(kept / "traces" / f"r-{i}.db", f"r-{i}")
        rows.append((i, f"n{i}", "t", f"r-{i}"))
    out = st.copy_originals(kept, fresh, rows)
    assert out["copied"] == 2
    assert out["fresh_listing"] == ["r-1.db", "r-2.db"]
    assert out["fresh_holds_only_the_copies"] is True
    assert out["engines"] == [out["copies"][0]["engine"]]


def test_a_leftover_in_the_fresh_store_is_REPORTED_and_never_ignored(
        tmp_path):
    kept, fresh = tmp_path / "kept", tmp_path / "fresh"
    _trace(kept / "traces" / "r-1.db", "r-1")
    (fresh / "traces").mkdir(parents=True)
    (fresh / "traces" / "leftover.db").write_bytes(b"")
    out = st.copy_originals(kept, fresh, [(1, "n", "t", "r-1")])
    assert out["fresh_holds_only_the_copies"] is False
    assert "leftover.db" in out["fresh_listing"]
