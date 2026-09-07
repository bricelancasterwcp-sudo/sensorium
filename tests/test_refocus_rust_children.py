"""A re-run's own child process is not a second candidate for the pair.

Ruling R2 (design 2026-09-07 §0, §3), split into its own file because
`tests/test_refocus_rust.py` is at the 800-line ceiling and this rule is a
whole subject: the fixtures are that file's, imported unchanged.

THE SHAPE THIS FILE EXISTS FOR
------------------------------
A `cargo test` re-run whose test itself runs an instrumented program writes
TWO traces stamped `refocus_of` -- the runner's process and the child it
spawned -- because the driver stamps the link on every trace of the
invocation. Before R2 the pair lookup counted both, called it "more than
one candidate" and refused with the single-target sentence: advice to add a
selector, given to a caller whose selector was already single, about a
second trace that was never a candidate. The parent is the process the user
recorded and asked about; the child is excluded from the pair, NAMED where
the pair is named, stamped into the pair's trace, and still listed by
`sensorium runs`.

Every test here fixes `pid`/`ppid` explicitly, because the rule is a
relation between two traces and a fixture that left them unset would pass
for the wrong reason.
"""
import time

import pytest

from sensorium import paths
from sensorium.query import refocus_rust
from tests.refocus_rust_fixtures import (CHILD, CHILD_PID, GRANDCHILD,
                                         GRANDCHILD_PID, ORIG, PAIR,
                                         PARENT_PID, SECOND, SECOND_PID,
                                         _drive, _read_meta, original)


def _linked(tmp_path, monkeypatch, run, run_id, *, launched, pid=None,
            ppid=None):
    """One trace linked to `run` by `refocus_of`, recorded after `launched`.

    `pid`/`ppid` are written ONLY where the caller names one: the converter
    writes both on every trace it produces, and a test that wants the
    "recorded no process id" shape needs the key to be absent rather than
    zero.
    """
    ids = {k: v for k, v in (("pid", pid), ("ppid", ppid)) if v is not None}
    original(tmp_path, monkeypatch, run_id=run_id, refocus_of=run,
             start_ts=launched + 1, **ids)


# -- the lookup ------------------------------------------------------------
def test_the_childs_ppid_takes_it_out_of_the_pair_and_names_it(tmp_path,
                                                               monkeypatch):
    """The rule itself: `CHILD.ppid == PAIR.pid`, so the parent is the pair
    and the child is reported beside it rather than counted against it."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched,
            pid=PARENT_PID, ppid=1)
    _linked(tmp_path, monkeypatch, run, CHILD, launched=launched,
            pid=CHILD_PID, ppid=PARENT_PID)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [CHILD])


def test_a_second_process_of_the_invocation_is_still_a_candidate(tmp_path,
                                                                 monkeypatch):
    """The rule excludes CHILDREN, not "everything after the first".

    Two test binaries and one spawned child is three linked traces and two
    genuine candidates, which is still the refusal `refocus` owes -- with
    the count and the ids naming the two the reader has to choose between.
    """
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched,
            pid=PARENT_PID, ppid=1)
    _linked(tmp_path, monkeypatch, run, CHILD, launched=launched,
            pid=CHILD_PID, ppid=PARENT_PID)
    _linked(tmp_path, monkeypatch, run, SECOND, launched=launched,
            pid=SECOND_PID, ppid=1)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR, SECOND], [CHILD])


def test_a_grandchild_is_a_child_run_too(tmp_path, monkeypatch):
    """`ppid` is matched against EVERY candidate's pid, not against the
    first one: a child that spawns its own child leaves three linked traces
    and exactly one process nobody spawned."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched,
            pid=PARENT_PID, ppid=1)
    _linked(tmp_path, monkeypatch, run, CHILD, launched=launched,
            pid=CHILD_PID, ppid=PARENT_PID)
    _linked(tmp_path, monkeypatch, run, GRANDCHILD, launched=launched,
            pid=GRANDCHILD_PID, ppid=CHILD_PID)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [CHILD, GRANDCHILD])


def test_traces_that_record_no_process_ids_are_all_candidates(tmp_path,
                                                              monkeypatch):
    """None is not zero, and an unknown pid is not a pid to match against.

    Three traces of unknown parentage: one recorded a pid and no ppid, two
    recorded neither. Read as 0 they would be each other's children; let the
    unknown pid into the set to match on and the FIRST one's unknown parent
    finds it there -- two absences read as one relation. Either way the
    lookup returns fewer candidates than the re-run wrote, and a pair that
    is sitting in the store is refused.
    """
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched,
            pid=PARENT_PID)
    _linked(tmp_path, monkeypatch, run, CHILD, launched=launched)
    _linked(tmp_path, monkeypatch, run, SECOND, launched=launched)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR, CHILD, SECOND], [])


def test_a_child_whose_parent_is_not_in_the_store_is_a_candidate(tmp_path,
                                                                 monkeypatch):
    """A `ppid` is only a link when the process it names is one of these
    traces. Every re-run has a ppid -- the shell's, cargo's -- and reading
    any ppid as "this is somebody's child" would empty the pair."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched,
            pid=PARENT_PID, ppid=SECOND_PID)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [])


def test_a_trace_is_never_its_own_child(tmp_path, monkeypatch):
    """`another` candidate's pid, says the ruling. A trace whose recorder
    wrote its own pid into `ppid` is a corrupt record of one process, not a
    process that spawned itself: excluding it would leave the re-run with no
    candidate and REFUSE a pair that is sitting in the store."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched,
            pid=PARENT_PID, ppid=PARENT_PID)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR], [])


@pytest.mark.parametrize("pid, ppid", [(True, 1), ("4100", "4100"),
                                       (4100.0, 4100.0)])
def test_a_process_id_that_is_not_an_integer_is_not_read_at_all(
        tmp_path, monkeypatch, pid, ppid):
    """`True == 1` in Python, and a string or a float pid is a pid this
    reader did not understand. None of the three may be matched: an
    unreadable process identity makes a trace neither a parent nor a child,
    which leaves the pre-R2 behaviour (both are candidates) intact."""
    run, _ = original(tmp_path, monkeypatch)
    launched = time.time()
    _linked(tmp_path, monkeypatch, run, PAIR, launched=launched, pid=pid,
            ppid=1)
    _linked(tmp_path, monkeypatch, run, CHILD, launched=launched,
            pid=CHILD_PID, ppid=ppid)
    assert refocus_rust.find_pair(paths.traces_dir(), run, launched) == (
        [PAIR, CHILD], [])


# -- what the reader is told, and what the trace keeps ---------------------
def _drive_with_child(tmp_path, monkeypatch, *, extra=()):
    """The whole command against a re-run that wrote a parent and a child."""
    meta = {PAIR: {"pid": PARENT_PID, "ppid": 1},
            CHILD: {"pid": CHILD_PID, "ppid": PARENT_PID},
            SECOND: {"pid": SECOND_PID, "ppid": 1}}
    pairs = [(PAIR, ORIG), (CHILD, ORIG), *[(rid, ORIG) for rid in extra]]
    return _drive(tmp_path, monkeypatch, pairs=pairs, pair_meta=meta)


def test_the_pair_line_names_the_child_run_it_excluded(tmp_path, monkeypatch,
                                                       capsys):
    """The one place a reader learns that a trace was set aside. It rides on
    the line that names the pair, because "which trace is this verdict
    about" and "which trace is it not about" are one fact."""
    _run, _root, code, _fake = _drive_with_child(tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert code == 0
    assert f"run: {PAIR}   child runs excluded from the pair: {CHILD}" in out


def test_the_child_run_is_stamped_into_the_pairs_trace(tmp_path, monkeypatch,
                                                       capsys):
    """Printed AND stamped, for `_stamp_unverifiable`'s reason: a terminal
    scrolls, and the trace is what a later reader has."""
    _drive_with_child(tmp_path, monkeypatch)
    capsys.readouterr()
    assert _read_meta(PAIR, "refocus_children") == [CHILD]


def test_a_pair_with_no_child_run_stamps_an_empty_list_and_prints_none(
        tmp_path, monkeypatch, capsys):
    """The ordinary re-run, unchanged on stdout: no clause on the pair line.

    The stamp is written anyway -- `[]` says the child rule ran and found
    nothing, an ABSENT key says the trace predates the rule, and a reader of
    a key that only appears sometimes cannot tell those apart.
    """
    _run, _root, code, _fake = _drive(
        tmp_path, monkeypatch, pairs=[(PAIR, ORIG)],
        pair_meta={PAIR: {"pid": PARENT_PID, "ppid": 1}})
    out = capsys.readouterr().out
    assert code == 0
    assert f"run: {PAIR}\n" in out
    assert "child runs excluded from the pair" not in out
    assert _read_meta(PAIR, "refocus_children") == []


def test_two_candidates_and_a_child_refuse_by_the_candidates(
        tmp_path, monkeypatch, capsys):
    """The refusal after R2: the COUNT is of candidates, the ids named are
    the two the reader must choose between, and the child is named as
    excluded rather than left out of a sentence that would then describe
    two of the three traces the re-run actually wrote."""
    run, _root, code, _fake = _drive_with_child(tmp_path, monkeypatch,
                                                extra=[SECOND])
    out = capsys.readouterr().out
    assert code == 3
    assert (f"refocus verdict: REFUSED -- the re-run produced 2 traces "
            f"linked to {run} ({PAIR}, {SECOND}); refocus needs an "
            "invocation with a single-target selector (--lib, --test X, "
            "--bin X) so one trace is the answer; child runs excluded from "
            f"the pair: {CHILD}") in out
