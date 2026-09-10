"""What `sensorium ts ingest` turns a spool into: the events, the frames,
the fingerprints, and the records it deliberately turns into no row at all.

The fixtures and the machinery that drives them are `tests/ts_spools.py`,
which also carries the provenance of every case. The refusals, the meta keys
and this command's own surfaces are `tests/test_ts_ingest_meta.py`, and the
pool that runs the work is `tests/test_ts_ingest_pool.py`; the three are one
suite, split twice at the 800-line ceiling.
"""
import json

import pytest

from corpus.run_corpus import RUN_LINE, check_question
from sensorium.record.fingerprint import Fingerprint
from sensorium.store import db
from sensorium.store.db import TraceFormatError
from sensorium.store.reader import Trace
from tests.helpers import run_cli
from tests.ts_spools import (CASES, FIXTURES, REFUSING, copy_tree,
                             ingest_case, ingested, only_trace, open_run,
                             run_ids_in, sub)

__all__ = ["ingested"]      # a fixture, imported for pytest to find


def test_every_case_asks_at_least_one_question_with_an_assertion():
    """A `questions.json` that asks nothing pins nothing. This is the check
    that keeps a case from being added and then quietly asserting zero."""
    for case in CASES:
        questions = json.loads((FIXTURES / case / "questions.json").read_text())
        assert questions, f"{case}: questions.json is empty"
        for q in questions:
            asserts = (q.get("expect_contains") or q.get("expect_line")
                       or q.get("expect_count") or q.get("expect_absent")
                       or "expect_exit" in q)
            assert asserts, f"{case}/{q['id']}: asks nothing"


def test_no_committed_fixture_carries_a_path_off_this_box():
    """A recorded spool holds the absolute path of every file it saw. A
    fixture that kept one is pinned to the box it was recorded on, and
    `sanitize.py` exists to stop exactly that."""
    leaks = []
    for path in sorted(FIXTURES.rglob("*")):
        if path.suffix not in (".json", ".jsonl"):
            continue
        text = path.read_text()
        for needle in ("/home/", "/mnt/"):
            if needle in text:
                leaks.append(f"{path.relative_to(FIXTURES)}: {needle}")
    assert leaks == []


@pytest.mark.parametrize("case", CASES)
def test_case_converts_and_answers_every_question(case, ingested):
    spool, sdir, result = ingested[case]
    expected_exit = 2 if case in REFUSING else 0
    assert result.returncode == expected_exit, (
        f"{case}: exit {result.returncode}\n{result.stdout}{result.stderr}")

    ids = run_ids_in(result.stdout)
    assert ids, f"{case}: no `run:` line in:\n{result.stdout}"

    questions = json.loads((FIXTURES / case / "questions.json").read_text())
    for q in questions:
        subbed = sub(q, ids)
        r = run_cli(subbed["command"], cwd=spool.parent, sensorium_dir=sdir)
        bad = check_question(subbed, r.stdout + r.stderr, r.returncode)
        assert not bad, (
            f"{case}/{q['id']}: " + "; ".join(bad)
            + f"\n    ask: {q['ask']}"
            + f"\n    cmd: sensorium {' '.join(subbed['command'])}"
            + f"\n    got: {r.stdout}{r.stderr}")


@pytest.mark.parametrize("case", CASES)
def test_every_trace_opens_and_is_complete_or_says_it_is_not(case, ingested):
    """The contract's own refusal rule, run on every trace this converter
    writes: a trace that claims `incomplete = false` and lacks a required
    key is refused at open, so a converter that forgets one is caught here
    and nowhere later."""
    _spool, sdir, _result = ingested[case]
    dbs = sorted((sdir / "traces").glob("*.db"))
    assert dbs, f"{case}: no trace written"
    for path in dbs:
        try:
            trace = Trace.open(path)
        except TraceFormatError as e:
            pytest.fail(f"{case}: {path.name} refused at open: {e}")
        missing = db.missing_required(trace._c)
        assert missing == [], f"{case}: {path.name} lacks {missing}"
        if case != "killed-mid-file":
            assert trace.meta.get("incomplete") is False, (
                f"{case}: {path.name} did not finalize")


@pytest.mark.parametrize("case", CASES)
def test_the_run_line_is_the_one_the_corpus_reads(case, ingested):
    """P7's line, held to the regex `corpus/run_corpus.py` reads run ids
    with. The corpus learns what it just recorded from this string, so its
    shape is a contract between two programs."""
    _spool, _sdir, result = ingested[case]
    mine = run_ids_in(result.stdout)
    theirs = RUN_LINE.findall(result.stdout)
    assert mine == theirs, result.stdout


@pytest.mark.parametrize("case", CASES)
def test_null_rules_hold_on_every_event_and_frame(case, ingested):
    """TRACE-FORMAT section 3: `frame_id` is NULL on every CALL, `code_id` is
    never NULL on a causal event, and `closed_by` is `return`, `unwind` or
    NULL and has no third value."""
    _spool, sdir, _result = ingested[case]
    for path in sorted((sdir / "traces").glob("*.db")):
        conn = Trace.open(path)._c
        for eid, kind, frame_id, code_id in conn.execute(
                "SELECT id, kind, frame_id, code_id FROM events"):
            where = f"{case}/{path.name}: e{eid} {kind}"
            if kind == "CALL":
                assert frame_id is None, f"{where} carries frame_id {frame_id}"
            if kind in ("CALL", "RETURN", "RAISE", "HANDLED"):
                assert code_id is not None, f"{where} carries no code_id"
        for fid, closed_by in conn.execute(
                "SELECT id, closed_by FROM frames"):
            assert closed_by in ("return", "unwind", None), (
                f"{case}/{path.name}: f{fid} closed_by {closed_by!r}")


def test_killed_mid_file_is_incomplete_and_refuses_a_verdict(ingested,
                                                             tmp_path):
    """A container `SIGKILL`ed mid-write loses its tail and its EXIT. The
    trace says so, `info` says so above everything else, and `diff` refuses
    to compare half a recording against a whole one (exit 3)."""
    _spool, sdir, result = ingested["killed-mid-file"]
    killed = run_ids_in(result.stdout)[0]
    cut = open_run(sdir, killed)
    assert cut.meta["incomplete"] is True
    assert "records_dropped" not in cut.meta, (
        "this recorder never counts what a killed process was about to write")

    r = run_cli(["info", killed], cwd=tmp_path, sensorium_dir=sdir)
    assert "INCOMPLETE" in r.stdout, r.stdout

    # The whole recording of the same program, converted into the same store,
    # so `diff` can be asked to compare the two.
    whole_spool, _, whole = ingest_case("async-chain", tmp_path / "whole")
    whole_id = run_ids_in(whole.stdout)[0]
    copy_tree(sdir / "traces", tmp_path / "both" / "traces")
    copy_tree(whole_spool.parent / "sdir" / "traces",
               tmp_path / "both" / "traces")
    d = run_cli(["diff", whole_id, killed], cwd=tmp_path,
                sensorium_dir=tmp_path / "both")
    assert d.returncode == 3, f"{d.stdout}{d.stderr}"
    assert "REFUSED" in d.stdout, d.stdout


def test_an_unhandled_rejection_is_meta_and_never_an_event(ingested):
    """Design D7: a causal event with no `code_id` is refused by the
    contract and a synthetic code object would put a site in the program
    that has none. So the rejection is a meta entry, and the trace carries
    no event without a code object at all."""
    _spool, sdir, _result = ingested["unhandled-rejection"]
    trace = only_trace(sdir)
    rejections = trace.meta["unhandled_rejections"]
    assert len(rejections) == 1, rejections
    assert rejections[0]["type"] == "Error"
    assert rejections[0]["msg"] == "e3"
    assert set(rejections[0]) == {"type", "msg", "serial"}
    (nulls,) = trace._c.execute(
        "SELECT COUNT(*) FROM events WHERE code_id IS NULL").fetchone()
    assert nulls == 0
    assert "UNHANDLED" not in {
        k for (k,) in trace._c.execute("SELECT DISTINCT kind FROM events")}


def test_a_throw_outside_every_frame_is_counted_and_written_as_no_event(
        ingested):
    """There is no frame to attach the event to, so none is written; the
    count is the only trace of it, read the way Rust's
    `err_flow_outside_frames` is."""
    _spool, sdir, _result = ingested["outside-frame-throw"]
    trace = only_trace(sdir)
    assert trace.meta["throw_flow_outside_frames"] == 1
    (raises,) = trace._c.execute(
        "SELECT COUNT(*) FROM events WHERE kind = 'RAISE'").fetchone()
    assert raises == 0


def test_each_rows_are_named_as_the_provider_named_them(ingested):
    """`test.each` expands a template into three rows and vitest names each
    one. A recorder that wrote the template three times would name three
    different tests the same."""
    _spool, sdir, _result = ingested["each-names"]
    trace = only_trace(sdir)
    names = [t.name for t in trace.tasks()]
    assert names == ["adds 1 + 2 = 3", "adds 2 + 3 = 5", "adds 4 + 5 = 9"]
    assert trace.meta["task_name_basis"] == "vitest"
    assert trace.meta["task_name_conflicts"] == 0
    # Every task owns a fingerprint row, zero-count included.
    assert len(trace.task_fingerprints()) == 3


def test_the_await_chain_nests_and_the_fanout_does_not(ingested, tmp_path):
    """E3 S1 and S2, read back off the trace. `a -> b -> c` are three frames
    each the child of the last; the two `p` frames of the fan-out are
    SIBLINGS under `fanout`, which is what popping a frame on YIELD buys."""
    _spool, sdir, result = ingested["async-chain"]
    run_id = run_ids_in(result.stdout)[0]
    trace = open_run(sdir, run_id)
    by_qual = {}
    for frame in trace.frames():
        by_qual.setdefault(trace.code(frame.code_id).qualname, []).append(frame)

    a, b, c = by_qual["a"][0], by_qual["b"][0], by_qual["c"][0]
    assert b.parent_id == a.id and c.parent_id == b.id
    assert a.depth + 1 == b.depth and b.depth + 1 == c.depth

    fanout = by_qual["fanout"][0]
    ps = [f for f in by_qual["p"] if f.parent_id == fanout.id]
    assert len(ps) == 2, by_qual["p"]
    assert ps[0].depth == ps[1].depth
    assert ps[0].id != ps[1].id

    # And the same fact through the real command line, which is where a
    # reader would meet it.
    r = run_cli(["tree", run_id, "--depth", "8"], cwd=tmp_path,
                sensorium_dir=sdir)
    assert r.returncode == 0, f"{r.stdout}{r.stderr}"
    assert "a()" in r.stdout and "fanout()" in r.stdout


def test_task_frame_kinds_are_the_contracts_enumeration(ingested):
    """`frames.kind` is never NULL from format 3 on, and the transform's
    four values are the contract's four."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    kinds = {k for (k,) in trace._c.execute("SELECT DISTINCT kind FROM frames")}
    assert kinds <= {"function", "coroutine", "generator", "async_generator"}
    assert None not in kinds
    assert "coroutine" in kinds


def test_a_generator_parks_on_whoever_is_pulling_it(ingested):
    """`await` and `yield` are two suspensions and the trace says which. A
    generator did not park on a promise, and saying it did would be a claim
    about machinery that never ran."""
    _spool, sdir, _result = ingested["generator-yield"]
    trace = only_trace(sdir)
    parked = {(e.payload or {}).get("awaiting")
              for e in trace.events(kind=("YIELD",))}
    assert parked == {"Promise", "consumer"}
    kinds = {k for (k,) in trace._c.execute("SELECT DISTINCT kind FROM frames")}
    assert "generator" in kinds


def test_the_four_ways_a_throw_is_handled_all_reach_the_trace(ingested):
    """`how` names what caught it: a `catch` clause, an empty one, an empty
    `.catch()` callback, or the `throw` that started it. Rung 2's rules read
    this key, so a converter that flattened it would leave them nothing to
    read."""
    _spool, sdir, _result = ingested["throw-flow"]
    trace = only_trace(sdir)
    hows = {(e.payload or {}).get("how")
            for e in trace.events(kind=("RAISE", "HANDLED"))}
    assert hows == {"throw", "catch", "sink_empty_catch",
                    "sink_empty_catch_callback"}
    kinds = {(e.payload or {})["exc"]["kind"]
             for e in trace.events(kind=("RAISE", "HANDLED"))}
    assert kinds == {"throw", "rejection"}
    for e in trace.events(kind=("RAISE", "HANDLED")):
        assert e.frame_id is not None
        assert e.code_id is not None
        assert e.line is not None
        assert set((e.payload or {})["exc"]) >= {"kind", "type", "msg",
                                                 "serial"}


def test_a_frame_that_left_by_throwing_says_so(ingested):
    """`closed_by` has no third value, and `unwind_exc` carries what left.
    An UNWIND writes no event: how a frame ended is evidence the reader
    derives from the frame row, not a row of its own."""
    _spool, sdir, result = ingested["unknown-frame"]
    trace = open_run(sdir, run_ids_in(result.stdout)[0])
    frames = trace.frames()
    assert len(frames) == 1
    assert frames[0].closed_by == "unwind"
    assert frames[0].return_event_id is None
    assert frames[0].unwind_exc["msg"] == "boom"
    kinds = [e.kind for e in trace.events()]
    assert kinds == ["CALL", "RAISE"], kinds


def test_a_call_with_no_caller_says_the_caller_was_untraced(ingested):
    """P4: a continuation that runs when its task's stack is empty opens a
    parentless frame, and the payload says who called it -- Node's own
    machinery -- rather than leaving a reader to read a root frame as a
    program entry point."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    roots, nested = 0, 0
    for e in trace.events(kind=("CALL",)):
        payload = e.payload or {}
        assert payload["args"] == {}
        assert payload["unread"] == ["locals"]
        if payload.get("caller") == "untraced":
            roots += 1
        else:
            assert "caller" not in payload
            nested += 1
    assert roots > 0 and nested > 0


def test_suspension_says_what_the_frame_parked_on(ingested):
    """P8. `await` parks on a promise; `yield` parks on whoever is pulling.
    Neither carries a line, because the wire carries none."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    awaiting = set()
    for e in trace.events(kind=("YIELD",)):
        awaiting.add((e.payload or {}).get("awaiting"))
        assert e.line is None
        assert e.frame_id is not None
    assert awaiting == {"Promise"}
    for e in trace.events(kind=("RESUME",)):
        assert e.payload == {}
        assert e.line is None


def test_the_thread_row_covers_what_ran_in_no_test(ingested):
    """Under the per-task basis a thread's row covers the causal events that
    ran in NO unit of work, and a zero-count row is a fact with content."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    rows = trace.fingerprints()
    assert list(rows) == [1], rows
    _digest, n_events = rows[1]
    # The setup file's own calls run outside every test.
    assert n_events > 0
    assert len(trace.task_fingerprints()) == len(trace.tasks()) == 6


def test_a_test_that_ran_nothing_still_owns_its_rows(ingested):
    """Every unit of work gets a `tasks` row and a `task_fingerprints` row,
    whatever state it was left in -- a zero-count row is a fact with content
    and is not the same fact as having no row, which every reader takes to
    mean the unit never existed."""
    _spool, sdir, _result = ingested["outside-frame-throw"]
    trace = only_trace(sdir)
    assert [t.name for t in trace.tasks()] == ["boom runs", "boom is skipped"]
    counts = {name: n for name, _h, n in trace.task_fingerprints().values()}
    assert counts == {"boom runs": 2, "boom is skipped": 0}


def test_a_thread_that_ran_only_tests_keeps_its_zero_count_row(ingested):
    """The same rule for the container's own row. Every causal event here
    ran inside a test, so the thread row counts nothing -- and it is still
    written, because "this container ran traced code, all of it inside
    tests" is not "this container ran nothing"."""
    _spool, sdir, _result = ingested["outside-frame-throw"]
    trace = only_trace(sdir)
    assert trace.fingerprints()[1][1] == 0


def test_the_fingerprint_hashes_the_root_relative_file(ingested):
    """TRACE-FORMAT section 7: `code_objects.file` is the ABSOLUTE path and
    the fingerprint hashes the ROOT-RELATIVE one. The two are deliberately
    different strings, and a converter that hashed the absolute path would
    produce digests that look fine, compare fine against themselves, and
    never pair with a Python or Rust trace of the same shape -- which no
    other test in this file would notice."""
    _spool, sdir, _result = ingested["async-chain"]
    trace = only_trace(sdir)
    root = json.loads(
        (FIXTURES / "async-chain" / "invocation.json").read_text())["root"]

    for task_id, (_name, digest, count) in trace.task_fingerprints().items():
        rebuilt = Fingerprint()
        for file, qualname, kind, _eid in trace.task_stream(task_id):
            rebuilt.update(_relative(file, root), qualname, kind)
        assert rebuilt.hexdigest() == digest, f"task {task_id}"
        assert rebuilt.count == count

    thread = Fingerprint()
    for file, qualname, kind, _eid in trace.causal_stream(1):
        thread.update(_relative(file, root), qualname, kind)
    digest, count = trace.fingerprints()[1]
    assert (thread.hexdigest(), thread.count) == (digest, count)


def _relative(path: str, root: str) -> str:
    return path[len(root) + 1:] if path.startswith(root + "/") else path
