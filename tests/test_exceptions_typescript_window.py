"""Rule 4's absorbing conjunct, and the window it reads.

The conjunct exists so that a recording holding a handler row for a serial
never reads PROPAGATED -- "nothing traced took this" about a failure traced
code took is the false claim rule 4 has to refuse. What rung 2 got wrong is
WHICH handlers it read: `unit.absorbing` is every absorbing handler of the
serial anywhere in the trace, and for a RETHROWN serial that includes the
handler the rethrow itself came out of. `catch (e) { console.error(e);
throw e }` at a test root therefore declined rule 4 and printed a reason,
about a failure the harness demonstrably saw.

So rule 4 now reads the unit's OWN window (`unit.handled` filtered to the
absorbing set, design section 2.2). The escaping conjuncts stay
trace-global, and the two tests at the end of this file are the fence that
says so: an escaped object rethrown from anywhere is still never a swallow
and still never PROPAGATED.
"""
from sensorium import cli
from sensorium.exit import ANSWERED
from tests.ts_traces import (FILE, call, frame, handled_ev, out, raise_ev,
                             ret, task, ts_exc, ts_trace, yield_ev)


def test_a_logged_rethrow_out_of_the_test_root_propagates(
        tmp_path, monkeypatch, capsys):
    """`catch (e) { console.error(e); throw e }` in the test body: the
    absorbing handler's frame was closed by the rethrow itself, which is
    the rethrow's predecessor and not an unfinished handler."""
    exc = ts_exc("Error", "disk offline", 4)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "boot > falls back", 5], [FILE, "load", 20]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                raise_ev(3000, 2, 2, 22, exc, task=1),
                handled_ev(4000, 1, 1, 9, exc, "catch", task=1),
                raise_ev(5000, 1, 1, 10, exc, task=1)],
        tasks=[task(1, "boot > falls back")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "RE-RAISED -- raised again at e5 (boot > falls back L10) → propagated" in o, o
    assert 'PROPAGATED -- to the harness: test "boot > falls back" failed' in o, o
    assert "dispositions: re-raised 1, propagated 1" in o, o


def test_a_parked_callback_handler_in_this_window_still_declines_rule_4(
        tmp_path, monkeypatch, capsys):
    """The shape that motivated the conjunct (rung 2, Task 4's fix round):
    `.catch(async () => …)` still parked where the recording stops, over a
    throw that left a frame Node entered on an empty stack.

    This handler is in the unit's OWN window, so narrowing the conjunct to
    the window moves nothing about it: rule 4 still declines and the reason
    printed is still the suspension, byte for byte.
    """
    exc = ts_exc("Error", "tile 7 missing", 71, kind="rejection")
    run_id = ts_trace(
        tmp_path / "parked", monkeypatch,
        codes=[[FILE, "poll", 40], [FILE, "retry", 60]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 3, closed_by=None, kind="coroutine")],
        events=[call(1000, 1, 40), raise_ev(2000, 1, 1, 42, exc),
                call(3000, 2, 60),
                handled_ev(4000, 2, 2, 62, exc, "sink_empty_catch_callback"),
                yield_ev(5000, 2, 2)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- the handler's frame f2 is still suspended at the "
            "end of the recording") in o, o
    assert "PROPAGATED" not in o, o
    assert "SWALLOWED" not in o, o
    assert "dispositions: ambiguous 1" in o, o
    assert "ambiguous by reason: suspended 1" in o, o


def test_an_escaped_object_rethrown_later_still_reads_escaped(
        tmp_path, monkeypatch, capsys):
    """An earlier window's absorbing handler whose frame RETURNED, an
    escaping handler beside it, and a rethrow of the same object out of the
    test root a frame above.

    Narrowing the absorbing conjunct to the window takes the returned
    handler out of rule 4's reading -- and the escaping conjunct, which
    stays trace-global, is what still keeps this off PROPAGATED. The
    recording holds a row saying the error, or a rendering of it, left a
    handler; "nothing traced took this" would contradict it.
    """
    exc = ts_exc("Error", "boom", 1)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "boot > rethrows the stored error", 5],
               [FILE, "wrap", 20], [FILE, "read", 40]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 2, 7, parent=1, depth=1),
                frame(3, 3, parent=2, depth=2, unwind_exc=exc)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                call(3000, 3, 40, task=1),
                raise_ev(4000, 3, 3, 42, exc, task=1),
                handled_ev(5000, 2, 2, 22, exc, "sink_finally_return",
                           task=1),
                handled_ev(6000, 2, 2, 24, exc, "catch_escaped", task=1),
                ret(7000, 2, 2, task=1),
                raise_ev(8000, 1, 1, 9, exc, task=1)],
        tasks=[task(1, "boot > rethrows the stored error")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught at e6 (catch_escaped), and the error or a "
            "rendering of it left the handler; not followed") in o, o
    assert "PROPAGATED" not in o, o
    assert "SWALLOWED" not in o, o
    assert "dispositions: re-raised 1, ambiguous 1" in o, o
    assert "ambiguous by reason: escaped 1" in o, o
