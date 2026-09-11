"""`exceptions <invocation-id>` answers for a whole TypeScript invocation.

WHY THIS FILE IS SEPARATE FROM ITS RUST SIBLING
-----------------------------------------------
`tests/test_exceptions_invocation.py` is the Rust half and is the fence
this task was measured against: every one of its nineteen tests is
byte-unchanged, so a merge key or a header that moved for TypeScript's
sake fails there rather than here. It is also 696 lines, and the two halves
in one file would cross the 800-line ceiling (`tests/test_ceiling.py`).

WHAT THIS HALF PINS
-------------------
That the mode dispatches PER MEMBER on `meta.lang` -- one grouper, two
renderers -- and that everything it prints in this language is this
recorder's own words: `with throws` and not `with Err chains`, `N raises`
and not `N chains`, no panic line and no `partial` block, and an
INCOMPLETE member whose sentence says what a cut hides HERE (throws).

A vitest invocation really is many processes: the driver forks a worker per
test file, and every one of them writes its own trace. So the merge this
mode does for `cargo test --workspace` is the merge a lens run needs, and
the shape merged across two members below is the one E6-TS' reads at scale.
"""
import re

from sensorium import cli
from sensorium.exit import ANSWERED, BAD_CALL, NEGATIVE, UNSETTLED
from tests.helpers import rust_trace
from tests.rust_traces import FILE as RUST_FILE
from tests.rust_traces import call as rust_call
from tests.rust_traces import frame as rust_frame
from tests.rust_traces import ret as rust_ret
from tests.ts_traces import (FILE, TS_CAPABILITIES_0_1, call, frame,
                             handled_ev, out, raise_ev, rejection, ret,
                             task, ts_exc, ts_trace)

#: `TS_META`'s own invocation id: every member built below shares it,
#: which is what makes them one invocation without a keyword saying so.
INV = "20260101-000000-111111"
M1 = "20260101-000000-ts0001"
M2 = "20260101-000000-ts0002"

PARSE_ERR = ts_exc("Error", "not a number: nine", 1)


def swallow_member(tmp_path, monkeypatch, run_id, **meta):
    """One worker: `loadConfig` calls `parse`, which throws; the `catch`
    absorbs it and `loadConfig` returns a default.

    Event ids: e1 CALL loadConfig, e2 CALL parse, e3 RAISE, e4 HANDLED,
    e5 RETURN.
    """
    return ts_trace(
        tmp_path, monkeypatch, run_id=run_id,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=PARSE_ERR)],
        events=[
            call(1000, 1, 15, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, PARSE_ERR, task=1),
            handled_ev(4000, 1, 1, 18, PARSE_ERR, "catch", task=1),
            ret(5000, 1, 1, "{ retries: 3 }", task=1),
        ],
        tasks=[task(1, "a config file is loaded")], **meta)


def quiet_member(tmp_path, monkeypatch, run_id, **meta):
    """A worker whose test file threw nothing at all."""
    return ts_trace(
        tmp_path, monkeypatch, run_id=run_id,
        codes=[[FILE, "loadConfig", 15]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 15, task=1), ret(2000, 1, 1, "{}", task=1)],
        tasks=[task(1, "a config file is loaded")], **meta)


def escaped_member(tmp_path, monkeypatch, run_id, **meta):
    """One worker whose `catch` let the error or a rendering of it out --
    rule 5's `escaped` reason, and the commonest one in the lens.

    Event ids: e1 CALL loadConfig, e2 CALL parse, e3 RAISE, e4 HANDLED,
    e5 RETURN.
    """
    return ts_trace(
        tmp_path, monkeypatch, run_id=run_id,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=PARSE_ERR)],
        events=[
            call(1000, 1, 15, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, PARSE_ERR, task=1),
            handled_ev(4000, 1, 1, 18, PARSE_ERR, "catch_escaped", task=1),
            ret(5000, 1, 1, "{ retries: 3 }", task=1),
        ],
        tasks=[task(1, "a config file is loaded")], **meta)


def two_reasons_member(tmp_path, monkeypatch, run_id, **meta):
    """One worker carrying TWO ambiguities with different reasons: the
    escaped `catch` above, and a `Bomb` whose failure untraced code took.

    Event ids: e1-e5 the escaped unit; then e6 CALL renderWithBoundary,
    e7 CALL Bomb, e8 RAISE, e9 RETURN.
    """
    boom = ts_exc("Error", "render failed", 2)
    return ts_trace(
        tmp_path, monkeypatch, run_id=run_id,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8],
               [FILE, "renderWithBoundary", 20], [FILE, "Bomb", 30]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=PARSE_ERR),
                frame(3, 6, 9),
                frame(4, 7, parent=3, depth=1, unwind_exc=boom)],
        events=[
            call(1000, 1, 15, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, PARSE_ERR, task=1),
            handled_ev(4000, 1, 1, 18, PARSE_ERR, "catch_escaped", task=1),
            ret(5000, 1, 1, "{ retries: 3 }", task=1),
            call(6000, 3, 20, task=1),
            call(7000, 4, 30, task=1, caller=None),
            raise_ev(8000, 4, 4, 34, boom, task=1),
            ret(9000, 3, 3, "null", task=1),
        ],
        tasks=[task(1, "a config file is loaded")], **meta)


def cut_member(tmp_path, monkeypatch, run_id, **meta):
    """A worker killed mid-file: one open frame and no close."""
    return ts_trace(
        tmp_path, monkeypatch, run_id=run_id,
        codes=[[FILE, "loadConfig", 15]],
        frames=[frame(1, 1)],
        events=[call(1000, 1, 15, task=1)],
        tasks=[task(1, "a config file is loaded")], incomplete=True, **meta)


# -- the answer -------------------------------------------------------------
def test_one_shape_merges_across_two_workers(tmp_path, monkeypatch, capsys):
    """Two workers ran the same file and sank the same throw at the same
    `catch`: ONE block, counting both, naming the process a reader can go
    and open -- and a header whose three counts are this recorder's."""
    swallow_member(tmp_path, monkeypatch, M1)
    swallow_member(tmp_path, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert (f"invocation {INV}: npx vitest run src/config  exit:1 (waited) "
            "-- 2 processes, 2 with throws, 0 with none") in o, o
    assert "raised (2 raises over 2 processes, 1 swallowed shape):" in o, o
    assert o.count("SWALLOWED --") == 1, o
    assert ("    SWALLOWED -- caught by catch at e4 (loadConfig L18) in f1, "
            f"which returned  [×2 over 2 processes: first e3 in {M1}, +1]"
            ) in o, o
    assert "dispositions: swallowed 2" in o, o
    # the two members agree in everything the key does not look at
    assert "origins:" not in o and "messages:" not in o, o
    # Rust's nouns and Rust's extra blocks belong to the other half. `Err`
    # as a WORD: the `Err` inside `Error(...)` is the program's own type
    # name and no claim of this command's (E7"'s own word-boundary rule).
    assert re.search(r"\bErr\b", o) is None, o
    assert "chains" not in o, o
    assert "panics:" not in o and "partial:" not in o, o


def test_a_shape_in_one_worker_still_names_its_process(
        tmp_path, monkeypatch, capsys):
    """Within one trace a group of one needs no bracket -- the process is
    the ref the reader typed. Here it is one of many, so it says which."""
    swallow_member(tmp_path, monkeypatch, M1)
    quiet_member(tmp_path, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert (f"invocation {INV}: npx vitest run src/config  exit:1 (waited) "
            "-- 2 processes, 1 with throws, 1 with none") in o, o
    assert "raised (1 raise over 1 process, 1 swallowed shape):" in o, o
    assert f"  [in {M1}]" in o, o
    assert "1 processes" not in o, o
    assert "dispositions: swallowed 1" in o, o


def test_an_incomplete_member_is_named_before_any_verdict(
        tmp_path, monkeypatch, capsys):
    """A worker that stopped mid-file is a gap in the whole answer, named
    ABOVE the blocks -- and what its cut hides is THROWS, because that is
    what this recorder writes."""
    swallow_member(tmp_path, monkeypatch, M1)
    cut_member(tmp_path, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    line = (f"INCOMPLETE: {M2} never finalized -- its throws after the cut "
            "are not below")
    assert line in o, o
    assert o.index(line) < o.index("raised ("), o
    assert "Err chains" not in o, o
    assert "dispositions: swallowed 1" in o, o


def test_silence_across_workers_is_a_gap_where_one_never_finalized(
        tmp_path, monkeypatch, capsys):
    """The empty answer splits the way it does in every other mode: 3 when
    a member stopped mid-flight, 1 when every recording is whole."""
    a = tmp_path / "a"
    quiet_member(a, monkeypatch, M1)
    cut_member(a, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == UNSETTLED
    o = out(capsys)
    assert "no exceptions recorded across 2 processes" in o, o
    assert f"INCOMPLETE: {M2} never finalized" in o, o

    b = tmp_path / "b"
    quiet_member(b, monkeypatch, M1)
    quiet_member(b, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == NEGATIVE
    o = out(capsys)
    assert "no exceptions recorded across 2 processes" in o, o
    assert "INCOMPLETE" not in o, o


def test_the_unhandled_rejections_are_summed_over_the_members(
        tmp_path, monkeypatch, capsys):
    """A rejection the process reported unhandled and no row carries has no
    site, so it opens no block (R1) -- it is counted in the header or it is
    said nowhere at all. Summed across members for the same reason the Rust
    half sums its panics: a merged answer that reported one member's is a
    number about the wrong thing.
    """
    swallow_member(tmp_path, monkeypatch, M1)
    quiet_member(tmp_path, monkeypatch, M2,
                 unhandled_rejections=[rejection("Error", "no route", 900),
                                       rejection("Error", "gone", 901)])
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert "unhandled rejections: 2" in o, o
    assert o.index("unhandled rejections: 2") < o.index("raised ("), o
    # the count is not a verdict: nothing was judged uncaught
    assert "dispositions: swallowed 1" in o, o


def test_the_reasons_are_summed_once_under_the_invocation_s_tally(
        tmp_path, monkeypatch, capsys):
    """`ambiguous by reason:` is a fact about the whole invocation, so it
    is summed over the members and printed ONCE, directly under the tally
    it explains, in the reason table's order (§2.3, P7).

    Three ambiguities over two workers: each member's own answer would say
    `escaped 1` and one would add `untraced catcher 1`. Here the reader
    sees the invocation's number, which is the one the record quotes.
    """
    escaped_member(tmp_path, monkeypatch, M1)
    two_reasons_member(tmp_path, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    lines = o.splitlines()
    assert "dispositions: ambiguous 3" in lines, o
    i = lines.index("dispositions: ambiguous 3")
    assert lines[i + 1] == ("ambiguous by reason: escaped 2, "
                            "untraced catcher 1"), o
    assert o.count("ambiguous by reason:") == 1, o


def test_an_invocation_with_nothing_ambiguous_prints_no_reason_line(
        tmp_path, monkeypatch, capsys):
    """A reason nothing wore is not a fact about this invocation, so the
    line is absent rather than empty -- which is also why a Rust answer,
    whose dispositions carry no reason at all, keeps the bytes two
    acceptance records quote."""
    swallow_member(tmp_path, monkeypatch, M1)
    swallow_member(tmp_path, monkeypatch, M2)
    assert cli.main(["exceptions", INV]) == ANSWERED
    o = out(capsys)
    assert "dispositions: swallowed 2" in o, o
    assert "ambiguous by reason:" not in o, o


# -- what this mode refuses -------------------------------------------------
def test_after_is_refused_here_too(tmp_path, monkeypatch, capsys):
    """An event id is minted per worker, and the ids of two workers are not
    one sequence to resume in. Paging is `--limit`, which counts shapes."""
    swallow_member(tmp_path, monkeypatch, M1)
    swallow_member(tmp_path, monkeypatch, M2)
    assert cli.main(["exceptions", INV, "--after", "e3"]) == BAD_CALL
    o = out(capsys)
    assert ("--after names an event of one process; this answer spans 2 "
            "processes -- page with --limit") in o, o
    assert "raised (" not in o and "dispositions:" not in o, o


def test_a_member_without_err_flow_refuses_the_whole(
        tmp_path, monkeypatch, capsys):
    """A merged count over a worker recorded by 0.1.x would be a number
    missing an unknown amount of the run. The whole answer is refused,
    naming the member to re-record."""
    swallow_member(tmp_path, monkeypatch, M1)
    quiet_member(tmp_path, monkeypatch, M2,
                 capabilities=TS_CAPABILITIES_0_1,
                 recorder="sensorium-ts 0.1.1")
    assert cli.main(["exceptions", INV]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions needs err_flow, which recorder "
            "sensorium-ts 0.1.1 declares it does not produce "
            "(capabilities.err_flow: false); nothing was checked "
            f"(member {M2})") in o, o
    assert "SWALLOWED" not in o and "raised (" not in o, o


def test_a_member_set_of_two_languages_is_refused_by_name(
        tmp_path, monkeypatch, capsys):
    """One invocation is one driver's, so this set cannot exist -- and the
    refusal is written rather than assumed, because the alternative to an
    impossible-case refusal is an impossible-case answer judged by one
    language's rules over another's records."""
    swallow_member(tmp_path, monkeypatch, M1)
    rust_trace(
        tmp_path, monkeypatch, run_id="20260101-000000-rs0001",
        invocation=INV, cargo_args=["test", "--workspace"],
        codes=[[RUST_FILE, "run", 3]],
        frames=[rust_frame(1, 1, 2)],
        events=[rust_call(1000, 1, 3), rust_ret(2000, 1, 1, "ok", "()")])
    assert cli.main(["exceptions", INV]) == UNSETTLED
    o = out(capsys)
    # members are read in file-name order, so the Rust worker is the first
    # and the TypeScript one is the member that cannot join it
    assert ("REFUSED: an invocation is one driver's; member "
            f"{M1} is typescript and 20260101-000000-rs0001 is rust") in o, o
    assert "SWALLOWED" not in o and "raised (" not in o, o
