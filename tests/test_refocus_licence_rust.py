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
from functools import partial

import pytest

from sensorium import cli, paths
from sensorium.query import refocus_world
from sensorium.query.refocus_world import (UNVERIFIABLE_CHILDREN,
                                           UNVERIFIABLE_OUTPUT,
                                           _verified_facts, harness_threads,
                                           unverifiable_checks)
from sensorium.query.vocab import PYTHON, RUST
from sensorium.store.reader import Trace
from tests.helpers import finalize_synthetic, fn_site, rust_trace
from tests.programs import synthetic
from tests.refocus_programs import LOOP, drop_meta, rec, refocus, set_meta
from tests.refocus_rust_fixtures import (ORIG, PAIR, _drive, _drop_meta,
                                         _read_meta, libtest_original,
                                         original)
from tests.rust_traces import (FILE, HARNESS_SERIAL, MAIN_THREAD, SITE_FILE,
                               TEST_FN, WORKER_FN, call, frame,
                               rerunnable_trace, ret)


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


# -- libtest's per-test thread is the RECORDER'S, not the program's --------
#
# E4 (2026-09-07) ran the whole licence over 61 real `cargo test` pairs and
# got `licence: WITHHELD` on every one of them, always for the same reason:
# libtest runs each `#[test]` fn on a thread it spawns, so the untraced-
# thread clause has a thread to name on every trace this recorder can
# produce. A clause that cannot not fire is not a finding. R1 (design
# 2026-09-07 section 2) makes that thread the recorder's own -- the
# precedent being the recorder's own environment variables, which this same
# licence already excludes by name -- and the tests below are that rule and
# the two ways of getting it wrong: subtracting a thread the site table
# never marked, and reading a frame that is not the thread's root.

#: The exact clause of design section 2, as one harness thread renders it.
HARNESS_PHRASE = ("1 harness thread (libtest's per-test thread, excluded as "
                  "the recorder's own)")
#: Design section 2's granted line, character for character.
GRANTED_THREAD_LINE = ("no thread started besides the main one and "
                       + HARNESS_PHRASE)


def _libtest(tmp_path, monkeypatch, **kw):
    """The whole command over a `cargo test`-shaped pair, both sides built
    the same way -- which is what makes the verdict a MATCH and leaves the
    licence as the only thing under test."""
    return _drive(tmp_path, monkeypatch, pairs=[(PAIR, ORIG)],
                  program=partial(libtest_original, **kw))


def test_the_harness_thread_alone_no_longer_withholds_the_licence(
        tmp_path, monkeypatch, capsys):
    """A `#[test]` fn that spawns nothing ran no thread of its own, and the
    licence now says so -- naming the excluded harness thread rather than
    dropping it silently."""
    _run, _root, code, _fake = _libtest(tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert code == 0, out
    assert "licence: WITHHELD" not in out
    assert f"  - {GRANTED_THREAD_LINE}" in out
    assert _read_meta(PAIR, "refocus_licence") == "granted"
    assert GRANTED_THREAD_LINE in _read_meta(PAIR, "refocus_licence_verified")


def test_one_program_thread_still_withholds_and_names_the_exclusion(
        tmp_path, monkeypatch, capsys):
    """The rule subtracts the harness thread; it does not stop counting.
    One thread the test itself spawned withholds the licence, and the
    reason names ONE -- the program's own -- and says what the other was."""
    _libtest(tmp_path, monkeypatch, program_threads=1)
    out = capsys.readouterr().out
    assert "licence: WITHHELD" in out
    for label in ("the original", "the rerun"):
        assert (f"{label} started 1 thread(s) besides the main one and "
                f"{HARNESS_PHRASE}. A thread that ran no traced code") in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_four_program_threads_are_four_after_the_harness_is_excluded(
        tmp_path, monkeypatch, capsys):
    """E4's own hazard, in miniature: the three server tests report five
    threads and four of them are the program's. A count that came back 5
    here would be the raw number, and R1 would not have fired."""
    _libtest(tmp_path, monkeypatch, program_threads=4)
    out = capsys.readouterr().out
    assert (f"the original started 4 thread(s) besides the main one and "
            f"{HARNESS_PHRASE}.") in out
    assert "started 5 thread(s)" not in out


def test_an_unmarked_thread_is_never_excluded_from_the_count(
        tmp_path, monkeypatch, capsys):
    """The discriminating control. The same trace with the `#[test]` mark
    taken off the site: the thread is still there, still untraced, and the
    licence must still count it. A rule that subtracted one thread whatever
    the site table said would pass every test above and fail this one."""
    _libtest(tmp_path, monkeypatch, harness_marked=False)
    out = capsys.readouterr().out
    assert "licence: WITHHELD" in out
    assert ("the original started 1 thread(s) besides the main one. "
            "A thread that ran no traced code") in out
    assert "harness thread" not in out


def test_harness_threads_names_the_thread_whose_root_is_the_test_fn(
        tmp_path, monkeypatch):
    run, _root = libtest_original(tmp_path, monkeypatch, program_threads=2)
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert harness_threads(t) == {HARNESS_SERIAL}


def test_a_marked_frame_below_the_root_is_not_a_harness_thread(
        tmp_path, monkeypatch):
    """The rule reads the thread's ROOT frame, and it has to: a `#[test]`
    fn called from somewhere deeper says nothing about who started the
    thread it ran on. Here thread 2's root is `worker` -- an ordinary
    spawned thread -- with the marked fn one frame below it, and the
    licence must count that thread as the program's."""
    run = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, WORKER_FN, 60], [FILE, TEST_FN, 40]],
        frames=[frame(1, 1, 2),
                frame(1, 3, 6, thread=HARNESS_SERIAL),
                frame(2, 4, 5, parent=2, depth=1, thread=HARNESS_SERIAL)],
        events=[call(1000, 1, 60), ret(1100, 1, 1, "ok", "()"),
                call(2000, 1, 60, thread=HARNESS_SERIAL, task=HARNESS_SERIAL),
                call(2100, 2, 40, thread=HARNESS_SERIAL, task=HARNESS_SERIAL),
                ret(2200, 3, 2, "ok", "()", thread=HARNESS_SERIAL,
                    task=HARNESS_SERIAL),
                ret(2300, 2, 1, "ok", "()", thread=HARNESS_SERIAL,
                    task=HARNESS_SERIAL)],
        sites=[fn_site(WORKER_FN, SITE_FILE, 60),
               fn_site(TEST_FN, SITE_FILE, 40, test=True)],
        threads_with_rows=[MAIN_THREAD], threads_started=1, live_threads=[])
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert harness_threads(t) == set()
    assert any("started 1 thread(s) besides the main one. A thread"
               in c for c in refocus_world._licence_caveats(t, t))


# -- ...and a MARKED root is not proof the recorder started the thread -----
#
# Blind spot 28 (review 2026-09-07, design 2026-09-08 R3). The root anchor
# above is a BOUND, not soundness in both directions: `#[test] fn` is an
# ordinary fn to rustc and callable from anywhere, so
# `thread::spawn(|| a_test_fn())` puts a marked ROOT on a thread the PROGRAM
# started -- and the old rule subtracted it, `threads_started - harness`
# reached 0, and the licence was GRANTED over a program thread. The
# direction that claims MORE. Two facts the recording already carries close
# it: the runtime NAMES a workspace spawn at its site
# (`<parent> :: spawn@<qualname>#<k>`, `sensorium-rt/src/tasks.rs`), and a
# thread has exactly one FIRST root.


def test_a_thread_the_program_spawned_onto_a_marked_fn_is_the_program_s(
        tmp_path, monkeypatch, capsys):
    """The false grant, as a fixture. The spawned thread's root IS the
    `#[test]` fn -- the closure holds no `?`, so it opens no frame of its
    own -- and its mark is identical to the libtest thread's. What tells
    them apart is the task name the runtime minted at the spawn site, so
    only the libtest thread is subtracted and the licence is WITHHELD over
    the one thread the program really started."""
    run, _root, code, _fake = _libtest(tmp_path, monkeypatch,
                                       spawned_on_marked_fn=1)
    out = capsys.readouterr().out
    assert code == 0, out
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert harness_threads(t) == {HARNESS_SERIAL}
    assert "licence: WITHHELD" in out
    for label in ("the original", "the rerun"):
        assert (f"{label} started 1 thread(s) besides the main one and "
                f"{HARNESS_PHRASE}. A thread that ran no traced code") in out
    assert GRANTED_THREAD_LINE not in out
    assert _read_meta(PAIR, "refocus_licence") == "withheld"


def test_only_the_first_root_of_a_thread_decides(
        tmp_path, monkeypatch, capsys):
    """A thread that runs `worker` to completion and then a `#[test]` fn has
    TWO root frames, and only the first one says how the thread began. The
    old rule read ANY root -- `for root in trace.roots()` -- so the second
    one excluded a thread the first had already accounted for."""
    run, _root, _code, _fake = _libtest(tmp_path, monkeypatch, two_roots=True)
    out = capsys.readouterr().out
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert harness_threads(t) == {HARNESS_SERIAL}
    assert "licence: WITHHELD" in out
    assert (f"the original started 1 thread(s) besides the main one and "
            f"{HARNESS_PHRASE}.") in out


def test_the_libtest_thread_is_still_the_harness_s_beside_a_spawned_one(
        tmp_path, monkeypatch):
    """Today's case, kept -- and the discrimination stated in the names the
    two threads actually carry. Both roots are the same marked fn; one task
    is named for the test libtest ran, the other for the spawn site inside
    it. A guard that skipped every task whose name MENTIONS a test fn would
    take the harness thread out too and pass every assertion above."""
    run, _root = libtest_original(tmp_path, monkeypatch,
                                  spawned_on_marked_fn=1)
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    spawned = HARNESS_SERIAL + 1
    assert t.task(HARNESS_SERIAL).name == TEST_FN
    assert t.task(spawned).name == f"{TEST_FN} :: spawn@{TEST_FN}#1"
    assert harness_threads(t) == {HARNESS_SERIAL}


def test_a_root_whose_site_the_manifest_never_wrote_is_counted(
        tmp_path, monkeypatch):
    """The `async` shape, pinned rather than coded for. An `async fn` test --
    `#[tokio::test]` and every other custom harness -- is classified `async`
    by the transform and skipped whole, so its site row is never written and
    the lookup finds NO mark. The thread stays the program's, which is the
    direction that claims less, and it is what the rule did before R1: this
    test is here so a later mark-lookup that defaulted a missing row to
    `test` could not slip through."""
    async_fn = "harness_tests::an_async_test"
    run = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "compute", 10], [FILE, async_fn, 80]],
        frames=[frame(1, 1, 2),
                frame(2, 3, 4, thread=HARNESS_SERIAL)],
        events=[call(1000, 1, 10), ret(1100, 1, 1, "ok", "5"),
                call(2000, 2, 80, thread=HARNESS_SERIAL, task=HARNESS_SERIAL),
                ret(2100, 2, 2, "ok", "()", thread=HARNESS_SERIAL,
                    task=HARNESS_SERIAL)],
        sites=[fn_site("compute", SITE_FILE, 10)],
        tasks=[(HARNESS_SERIAL, async_fn, HARNESS_SERIAL)],
        threads_with_rows=[MAIN_THREAD], threads_started=1, live_threads=[])
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert harness_threads(t) == set()
    assert any("started 1 thread(s) besides the main one. A thread"
               in c for c in refocus_world._licence_caveats(t, t))


def test_the_thread_note_and_info_partition_a_spawned_marked_thread_too(
        tmp_path, monkeypatch, capsys):
    """The three lines on the same screen agree about which thread is whose
    under the new anchor as well -- `diff`'s note here, `info`'s count
    below. One trace, one partition (fix round 1, above)."""
    run, _root, _code, _fake = _libtest(tmp_path, monkeypatch,
                                        spawned_on_marked_fn=1)
    assert ("recorded more than one thread: 1 started as OS threads "
            "(libtest's per-test threads and threads spawned by workspace "
            f"code) and {HARNESS_PHRASE}, 1 left a fingerprint"
            ) in capsys.readouterr().out
    assert cli.main(["info", run]) == 0
    assert f"threads started: 1 besides the main one and {HARNESS_PHRASE}" \
        in capsys.readouterr().out


def test_the_main_thread_is_never_a_harness_thread(tmp_path, monkeypatch):
    """`cargo test -- --test-threads=1` runs the `#[test]` fn on the main
    thread itself, so a marked ROOT frame there is not evidence of a thread
    libtest spawned -- there is none. `threads_started` never counted the
    main thread, so subtracting for it would take one off a count it was
    never in and hide a thread the program really did start.

    Found by a surviving mutant: with the main-thread test taken out of
    `harness_threads`, every assertion above still passed."""
    run = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, TEST_FN, 40], [FILE, WORKER_FN, 60]],
        frames=[frame(1, 1, 2),
                frame(2, 3, 4, thread=HARNESS_SERIAL)],
        events=[call(1000, 1, 40), ret(1100, 1, 1, "ok", "()"),
                call(2000, 2, 60, thread=HARNESS_SERIAL, task=HARNESS_SERIAL),
                ret(2100, 2, 2, "ok", "()", thread=HARNESS_SERIAL,
                    task=HARNESS_SERIAL)],
        sites=[fn_site(TEST_FN, SITE_FILE, 40, test=True),
               fn_site(WORKER_FN, SITE_FILE, 60)],
        threads_with_rows=[MAIN_THREAD], threads_started=1, live_threads=[])
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert harness_threads(t) == set()
    caveats = refocus_world._licence_caveats(t, t)
    assert any("started 1 thread(s) besides the main one. A thread" in c
               for c in caveats)
    assert not any("harness thread" in c for c in caveats)


def test_a_python_trace_has_no_harness_thread_and_the_same_caveats(tmp_path):
    """Python traces carry no site table, so the lookup finds nothing and
    every Python caveat is the string it was before R1 -- which is what the
    legacy licence suite is the fence for."""
    run_id, sdir = rec(tmp_path, LOOP)
    t = Trace.open(sdir / "traces" / f"{run_id}.db")
    assert harness_threads(t) == set()
    assert not any("harness thread" in c
                   for c in refocus_world._licence_caveats(t, t))
    assert not any("harness thread" in f
                   for f in refocus_world._verified_facts(t, t, ""))


# -- `info` replays the checks that could not run (design section 6) -------

def test_info_replays_the_checks_the_licence_could_not_run(
        tmp_path, monkeypatch, capsys):
    """The stamp has been written since rung 4 slice 1 and nothing read it.
    A reader of `info` saw the `licence verified:` lines alone and was left
    to infer that everything else had been checked and failed."""
    run_id = rerunnable_trace(
        tmp_path, monkeypatch, refocus_of="20260101-000000-original",
        refocus_licence="granted", refocus_licence_verified=["exit unchanged"],
        refocus_licence_unverifiable=[UNVERIFIABLE_OUTPUT,
                                      UNVERIFIABLE_CHILDREN])
    assert cli.main(["info", run_id]) == 0
    out = capsys.readouterr().out
    assert ("  licence unverifiable: output (not recorded), "
            "children (not witnessed)") in out


def test_info_says_nothing_about_unverifiable_checks_when_none_are_stamped(
        tmp_path, monkeypatch, capsys):
    """Absence of a name is absence of the line. A Python pair runs both
    checks for real, and a line saying nothing was unverifiable would be a
    claim the key's absence does not make."""
    run_id = rerunnable_trace(
        tmp_path, monkeypatch, refocus_of="20260101-000000-original",
        refocus_licence="granted", refocus_licence_verified=["exit unchanged"])
    assert cli.main(["info", run_id]) == 0
    assert "licence unverifiable" not in capsys.readouterr().out


def test_info_says_nothing_when_the_unverifiable_stamp_is_empty(
        tmp_path, monkeypatch, capsys):
    """`refocus` stamps the key even when the list is empty, so the empty
    list must read exactly as the missing key does."""
    run_id = rerunnable_trace(
        tmp_path, monkeypatch, refocus_of="20260101-000000-original",
        refocus_licence="granted", refocus_licence_verified=["exit unchanged"],
        refocus_licence_unverifiable=[])
    assert cli.main(["info", run_id]) == 0
    assert "licence unverifiable" not in capsys.readouterr().out


# -- R1's partition on the rest of the screen ------------------------------
#
# Fix round 1. The licence's own two sentences applied R1; three other lines
# on the SAME screen still counted threads without it -- `diff`'s thread
# note, `refocus`'s `threads:` line and `info`'s `threads started:` -- so a
# reader saw "1 started as OS threads" directly above "no thread started
# besides the main one and 1 harness thread". One trace, one screen, two
# partitions. And the `threads:` line was arithmetic across two populations:
# the Rust converter writes ONE `fingerprints` row and routes every other
# thread into `task_fingerprints`, so every non-main Rust thread was
# reported as "ran no traced code ... NOT compared" when its whole call
# shape HAD been compared as a task stream.

def test_the_thread_note_applies_the_licence_partition(
        tmp_path, monkeypatch, capsys):
    _libtest(tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert ("recorded more than one thread: 0 started as OS threads "
            "(libtest's per-test threads and threads spawned by workspace "
            f"code) and {HARNESS_PHRASE}, 1 left a fingerprint") in out
    assert "1 started as OS threads" not in out


def test_the_threads_line_names_the_harness_thread_it_does_not_count(
        tmp_path, monkeypatch, capsys):
    _libtest(tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert f"; {HARNESS_PHRASE} is not among these counts" in out


def test_a_thread_compared_as_a_task_stream_is_not_reported_uncompared(
        tmp_path, monkeypatch, capsys):
    """The arithmetic bug. Two spawned threads whose call shapes were both
    compared -- as task streams, which is where this converter puts them --
    must not be reported as threads that ran no traced code."""
    _libtest(tmp_path, monkeypatch, program_threads=2)
    out = capsys.readouterr().out
    assert "ran no traced code, left no fingerprint, and were NOT compared" \
        not in out


def test_a_thread_that_really_ran_nothing_is_still_reported_uncompared(
        tmp_path, monkeypatch, capsys):
    """...and the clause does not go away: two threads that started, ran no
    traced code and left no row of any kind are still named, and the count
    is the program's own -- the harness thread is not among them."""
    _libtest(tmp_path, monkeypatch, silent_threads=2)
    out = capsys.readouterr().out
    assert ("2 further thread(s) ran no traced code, left no fingerprint, "
            "and were NOT compared") in out
    assert f"; {HARNESS_PHRASE} is not among these counts" in out
    # ...and the licence, three lines below, counts the same two.
    assert (f"the original started 2 thread(s) besides the main one and "
            f"{HARNESS_PHRASE}.") in out


def test_info_applies_the_licence_partition_to_its_thread_count(
        tmp_path, monkeypatch, capsys):
    """`info` prints the licence lines on the same screen as this count."""
    run, _root = libtest_original(tmp_path, monkeypatch, program_threads=1)
    assert cli.main(["info", run]) == 0
    out = capsys.readouterr().out
    assert f"threads started: 1 besides the main one and {HARNESS_PHRASE}" \
        in out
    assert "threads started: 2 besides" not in out


def test_the_libtest_fixture_records_a_task_stream_per_thread(
        tmp_path, monkeypatch):
    """The fixture's fidelity claim, asserted rather than asserted about.
    `write_task_fingerprints` fills each name by `INSERT ... SELECT` from
    `tasks`, so a vector that declares no task rows silently writes no task
    fingerprints at all -- and every `task=` argument threaded through the
    events above would then change nothing observable."""
    run, _root = libtest_original(tmp_path, monkeypatch, program_threads=2)
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert set(t.fingerprints()) == {MAIN_THREAD}
    assert {task.id: task.thread_id for task in t.tasks()} == {2: 2, 3: 3,
                                                              4: 4}
    named = {tid: name for tid, (name, _h, _n) in t.task_fingerprints().items()}
    assert named == {2: TEST_FN, 3: "worker-0", 4: "worker-1"}


def test_an_inferred_main_thread_names_no_harness_thread(
        tmp_path, monkeypatch):
    """`main_thread_id()` never says "I do not know": it falls back to the
    thread of whichever event got id 1. On that basis a misidentified main
    could take a thread out of a count it was never in -- the defect the
    `--test-threads=1` test above exists for, arrived at from the other
    side. The rule wants the main thread as a RECORDED fact and refuses to
    guess when it is not one.

    The trace is INCOMPLETE, which is the state the store lets the key be
    missing in (`db.missing_required` exempts a recording that never
    finalized): a `cargo test` run that died mid-recording is exactly a
    trace `refocus` and `diff` will still be handed."""
    run, _root = libtest_original(tmp_path, monkeypatch, program_threads=1,
                                  incomplete=True)
    _drop_meta(tmp_path, run, "main_thread_ident")
    t = Trace.open(paths.traces_dir() / f"{run}.db")
    assert t.main_thread_basis() == "inferred"
    assert harness_threads(t) == set()


def test_a_harness_thread_whose_stream_was_not_compared_is_still_excluded(
        tmp_path, monkeypatch, capsys):
    """The other half of the subtraction. A recording that ended before its
    task rows were written has a harness thread nothing compared -- and it
    is STILL the recorder's own, so it must not appear as a program thread
    that ran no traced code. Found by a surviving mutant: with the
    not-already-compared harness term dropped, every other assertion here
    still passed."""
    _libtest(tmp_path, monkeypatch, task_rows=False)
    out = capsys.readouterr().out
    assert "ran no traced code, left no fingerprint, and were NOT compared" \
        not in out
    assert f"; {HARNESS_PHRASE} is not among these counts" in out


def test_an_asyncio_task_is_not_counted_as_a_thread(tmp_path, monkeypatch):
    """`compared_threads` follows a task row back to its thread through the
    `tasks` table rather than reading the task id as one. In Python many
    tasks share a thread, so reading them as threads would mark a worker
    that ran no traced code as compared and quietly drop the honesty
    clause. Found by a surviving mutant (`{task.id: task.id}`), which no
    Rust fixture can catch: there the two ARE equal by construction."""
    w = synthetic(tmp_path, monkeypatch)
    w.add_task(7, "fetch", 1)          # one asyncio task, on the main thread
    w.write_task_fingerprints([(7, "aa" * 16, 3)])
    w.write_fingerprint(1, "bb" * 16, 2)
    finalize_synthetic(w, threads_started=1, live_threads=[])
    w.close()
    t = Trace.open(paths.traces_dir() / "20260101-000000-abcdef.db")
    assert refocus_world.compared_threads(t) == {1}
    # One thread started besides the main one, and nothing compared it.
    assert refocus_world.uncompared_threads(t) == 1


# -- the scope phrase, in the recorder's own words -------------------------

def test_a_rust_screen_never_describes_its_streams_as_asyncio_tasks(
        tmp_path, monkeypatch, capsys):
    """Rung 1's bug, one renderer further in. The scope phrase is gated on
    the per-task basis AND on the run having task rows -- both true of every
    `cargo test` trace -- so the moment the fixture carried the task rows the
    converter really writes, three lines began saying `asyncio` about a run
    no interpreter touched. `info` already said it in Rust's words (it reads
    `Terms.task_noun`); these three did not, and `info_cmd` says in its own
    comment that the two commands must not describe one trace differently."""
    _libtest(tmp_path, monkeypatch)
    out = capsys.readouterr().out
    assert "asyncio" not in out
    assert ("threads: 1 recorded fingerprint(s) compared (events outside any "
            "test or spawned thread), all matching") in out
    assert ("refocus verdict: MATCH -- every recorded thread produced the "
            "identical CALL/RETURN/RAISE/HANDLED sequence outside its test "
            "and spawned threads, and every task stream matched by content"
            ) in out
    assert ("  - identical call shape across 1 compared fingerprint(s), "
            "holding 2 causal event(s) outside any test or spawned thread"
            ) in out


def test_refocus_and_info_scope_one_rust_trace_with_the_same_words(
        tmp_path, monkeypatch, capsys):
    """One trace, two commands, one answer -- the invariant `info_cmd`
    states beside the gate both of them read."""
    run, _root = libtest_original(tmp_path, monkeypatch)
    assert cli.main(["info", run]) == 0
    out = capsys.readouterr().out
    assert "asyncio" not in out
    assert "causal events outside any test or spawned thread)" in out
