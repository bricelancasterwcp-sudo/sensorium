"""What a `refocus` licence may claim when a RECORDER'S OWN DECLARATION,
rather than a signal it found, decides the answer.

Split out of `tests/test_refocus_licence.py` at that file's 800-line ceiling,
along the seam the material has. Everything here turns on one question --
what may be said about a check the recorder declares it cannot run? -- and
the answer this slice fixed is the same on both sides of it:

* NEVER "verified". Two recordings that captured no output hold EQUAL
  output, and a difference check over them finds none, which reads as a
  passed cross-check. That is the bug class, and it is why the Rust pair
  gets `output: unverifiable (not recorded)` instead.
* NEVER a reason the licence was withheld either. A check that could not run
  is not a finding against the pair, so the two markers are printed and
  stamped beside the licence rather than inside its reasons.

The Python traces here are the same shape one step back: a witness key that
was never written, and a capability the interpreter could not provide.
"""
import pytest

from sensorium import paths
from sensorium.query import refocus_world
from sensorium.query.refocus_world import (UNVERIFIABLE_CHILDREN,
                                           UNVERIFIABLE_OUTPUT,
                                           _verified_facts,
                                           unverifiable_checks)
from sensorium.query.vocab import PYTHON, RUST
from sensorium.store.reader import Trace
from tests.refocus_programs import LOOP, drop_meta, rec, refocus, set_meta
from tests.refocus_rust_fixtures import ORIG, PAIR, _drive, _read_meta, original


# -- a Python recorder that could not run one of the checks ----------------

def test_refocus_omits_the_child_claim_when_spawns_are_unwitnessable(tmp_path):
    """A trace recorded where no audit event fires for a multiprocessing spawn
    (CPython < 3.14) cannot have its licence vouch `no child witnessed` -- that
    check could not run. Forced through meta so the rule holds on every
    interpreter, not only the ones that happen to lack the audit event."""
    run_id, sdir = rec(tmp_path, LOOP)
    set_meta(sdir / "traces" / f"{run_id}.db", spawn_witnessing=False)
    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: verified against" in r.stdout       # still granted...
    assert "no child process witnessed" not in r.stdout  # ...but not this claim
    # the categorical blind-spot block still states the gap on every verdict
    assert "any child process, by any mechanism" in r.stdout



def test_refocus_withholds_when_the_spawn_record_predates_the_check(tmp_path):
    """A trace recorded before spawn syscalls were counted would otherwise
    read as "no child process witnessed, by any mechanism sensorium watches"
    -- the strongest of the five verified facts, granted on a key that was
    never written. The thread bookkeeping already handles this shape; these
    must agree."""
    run_id, sdir = rec(tmp_path, LOOP)
    drop_meta(sdir / "traces" / f"{run_id}.db", "spawn_syscalls")

    r = refocus(sdir, run_id, "--focus", "prog:accumulate")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "refocus verdict: MATCH" in r.stdout
    assert "licence: WITHHELD" in r.stdout
    # `rec()` uses today's recorder, which declares `children` True at run
    # start -- `drop_meta` deletes the witness key afterward, so this is
    # the declared-True-but-missing state, not a genuine pre-declaration
    # trace: it must read as a contradiction on record, never "predates".
    assert ("declares children witnessed, but this trace carries no "
            "spawn-syscall record") in r.stdout
    assert "the recording did not finish, or the record was removed" in r.stdout
    assert "absence of the record is not a record of absence" in r.stdout
    assert "predates" not in r.stdout
    assert "licence: verified against" not in r.stdout


def test_licence_names_an_undeclared_output_capability_as_a_blind_spot(
        tmp_path, monkeypatch):
    # The sentence MOVED with rung 4 (design 2026-09-07 section 3.2) and is
    # now the marker `refocus_rust` prints and stamps, named once for the pair.
    from sensorium.query import refocus_world as rw
    from tests.helpers import finalize_synthetic
    from tests.programs import synthetic
    w = synthetic(tmp_path, monkeypatch)
    finalize_synthetic(w, lang="rust", recorder="sensorium-rt 0.0",
                       capabilities={"output": False, "threads": True},
                       threads_started=0, live_threads=[])
    w.write_fingerprint(1, "aa" * 16, 1)
    w.close()
    from sensorium import paths
    from sensorium.store.reader import Trace
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    caveats = rw._licence_caveats(t, t)
    assert caveats.count(rw.UNVERIFIABLE_OUTPUT) == 1  # the PAIR, not a side
    assert not any("cross-check did not run" in c for c in caveats)


# -- the two checks a Rust pair can never run ------------------------------

def test_the_two_unverifiable_checks_are_printed_and_stamped(
        tmp_path, monkeypatch, capsys):
    """Design section 3.2: on a Rust pair the output and children checks
    cannot run, and the honest answer is to SAY so on both channels -- the
    terminal a person reads and the trace `info` replays."""
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert "checks that could not run on this pair" in out
    assert f"  - {UNVERIFIABLE_OUTPUT}" in out
    assert f"  - {UNVERIFIABLE_CHILDREN}" in out
    assert _read_meta(PAIR, "refocus_licence_unverifiable") == [
        UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN]


def test_the_unverifiable_checks_do_not_withhold_the_licence(
        tmp_path, monkeypatch, capsys):
    """A check that could not RUN is not a finding against the pair. The
    licence is granted, the two unrun checks are named beside it, and the
    stamped label and the printed line say the same thing."""
    run, _root, _code, _fake = _drive(tmp_path, monkeypatch,
                                      pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert "licence: WITHHELD" not in out
    assert f"licence: verified against {run} on exactly these points" in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"
    assert _read_meta(PAIR, "refocus_licence_reasons") == []
    verified = _read_meta(PAIR, "refocus_licence_verified")
    assert UNVERIFIABLE_OUTPUT not in verified
    assert UNVERIFIABLE_CHILDREN not in verified
    assert any("source file(s) unchanged by content" in f for f in verified)
    assert any("environment variable(s) compared and unchanged" in f
               for f in verified)


def test_a_real_caveat_still_withholds_the_licence_on_a_rust_pair(
        tmp_path, monkeypatch, capsys):
    """The removal above is of TWO named strings, not of the mechanism: a
    source file edited between the runs still withholds."""
    run, root, _code, _fake = _drive(tmp_path, monkeypatch,
                                     pairs=[(PAIR, ORIG)],
                                     source_hashes={"src/lib.rs": "0" * 64})
    out = capsys.readouterr().out
    assert "licence: WITHHELD" in out
    assert "source file(s) CHANGED between the two runs" in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"
    # ...and the unrun checks are still reported, on both channels.
    assert UNVERIFIABLE_OUTPUT not in _read_meta(PAIR,
                                                 "refocus_licence_reasons")
    assert _read_meta(PAIR, "refocus_licence_unverifiable") == [
        UNVERIFIABLE_OUTPUT, UNVERIFIABLE_CHILDREN]
    assert f"  - {UNVERIFIABLE_OUTPUT}" in out


def test_the_output_check_is_never_consulted_on_a_rust_pair(tmp_path,
                                                            monkeypatch,
                                                            capsys):
    """Two recordings that captured nothing hold EQUAL output, and the
    difference check duly finds none -- which reads as verified. It must
    not run at all; the marker is the answer."""

    def boom(a, b):                    # pragma: no cover - a tripwire
        raise AssertionError("the output check ran on a Rust pair")
    monkeypatch.setattr(refocus_world, "_output_difference", boom)
    _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)])
    out = capsys.readouterr().out
    assert UNVERIFIABLE_OUTPUT in out
    assert "the program's own captured" not in out


def test_verified_facts_never_list_output_or_children_on_a_rust_pair(
        tmp_path, monkeypatch):
    """The positive list is what a granted licence RESTS on. Neither the
    output cross-check nor the child witness may appear in it here."""
    run, _root = original(tmp_path, monkeypatch)
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    facts = _verified_facts(t, t, "")
    assert unverifiable_checks(t, t) == [UNVERIFIABLE_OUTPUT,
                                         UNVERIFIABLE_CHILDREN]
    assert not any("output" in f for f in facts)
    assert not any("child process" in f for f in facts)
    # The thread clause is the Rust one: a Python provenance claim about a
    # run no Python interpreter touched is the bug `vocab.py` exists for.
    assert any(RUST.thread_origin in f for f in facts)
    assert not any(PYTHON.thread_origin in f for f in facts)
