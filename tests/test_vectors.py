"""Every vector under docs/trace-format/vectors builds, and every question
it asks of the CLI comes back as the contract says.

These are the trace-format contract's teeth: `docs/TRACE-FORMAT.md` states
what a trace must hold, and each vector is a trace built to that statement
and run through the real CLI in a subprocess. A second recorder's suite
reads the same JSON files, so a rule that both suites pass is a rule both
recorders keep.
"""
import shutil

import pytest

from corpus.run_corpus import check_question
from sensorium.store.db import TraceFormatError
from sensorium.store.reader import Trace
from tests.helpers import run_cli
from tests.vectors import build, load_all, sub

VECTORS = load_all()
_ASSERTING = ("expect_contains", "expect_line", "expect_count")


@pytest.mark.parametrize("vector", VECTORS, ids=[v["id"] for v in VECTORS])
def test_vector(vector, tmp_path):
    sdir = tmp_path / "sdir"
    run_ids = ["20260101-000000-aaaaaa",
               "20260101-000001-bbbbbb"][:vector.get("copies", 1)]
    path = build(vector, sdir, run_ids)
    if len(run_ids) == 2:
        shutil.copy(path, path.with_name(f"{run_ids[1]}.db"))
    assert vector["questions"], f"{vector['id']} asserts nothing"
    for q in vector["questions"]:
        cmd = [sub(a, run_ids) for a in q["command"]]
        r = run_cli(cmd, cwd=tmp_path, sensorium_dir=sdir)
        bad = check_question(q, r.stdout + r.stderr, r.returncode)
        assert not bad, f"{vector['id']}/{q['id']}: {bad}\n{r.stdout}{r.stderr}"


def test_every_vector_has_an_id_a_claim_and_at_least_one_question():
    assert VECTORS, "no vectors found"
    ids = [v["id"] for v in VECTORS]
    assert len(set(ids)) == len(ids), f"duplicate vector ids in {ids}"
    for v in VECTORS:
        assert v["id"] and v["asserts"] and v["questions"]


def test_every_question_says_what_it_asks_and_asserts_something():
    """A question with no assertion always passes, which is the one thing a
    conformance suite must not contain; a question with no `ask` leaves the
    next reader to reverse-engineer the claim from the substrings."""
    for v in VECTORS:
        for q in v["questions"]:
            where = f"{v['id']}/{q.get('id')}"
            assert q.get("id") and q.get("ask"), f"{where}: needs id and ask"
            assert isinstance(q.get("command"), list) and q["command"], where
            assert any(q.get(k) for k in _ASSERTING), (
                f"{where}: asserts nothing -- needs a non-empty "
                + " / ".join(_ASSERTING))


@pytest.mark.parametrize("vector", VECTORS, ids=[v["id"] for v in VECTORS])
def test_call_rows_carry_no_frame_id(vector, tmp_path):
    """The vectors write the rows the recorder writes: a frame-opening CALL
    has `frame_id` NULL (`tracer._on_call` passes None -- the frame does not
    exist yet), and the frame is found from the other end, through
    `frames.call_event_id`. A vector that set `frame_id` on a CALL would
    hand a second recorder a row shape the Python one never produces."""
    try:
        trace = Trace.open(build(vector, tmp_path / "sdir",
                                 ["20260101-000000-aaaaaa"]))
    except TraceFormatError:
        pytest.skip(f"{vector['id']} is refused at open, by design")
    for ev in trace.events(kind="CALL"):
        assert ev.frame_id is None, (
            f"{vector['id']}: e{ev.id} is a CALL carrying frame_id "
            f"{ev.frame_id}; the recorder writes NULL there")
    for f in trace.frames():
        found = trace.frame_containing(f.call_event_id)
        assert found is not None and found.id == f.id, (
            f"{vector['id']}: f{f.id} is not reachable from its own CALL "
            f"e{f.call_event_id}")
