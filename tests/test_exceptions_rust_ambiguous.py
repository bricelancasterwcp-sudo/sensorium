"""`exceptions` on a Rust trace: AMBIGUOUS, the default that must hold.

Every shape here is one a rule reaching for a verdict would get WRONG, and
each was named by the design as a false-SWALLOWED generator or a blind
spot: a frame that returned ok with nothing recorded absorbing what it
held, two different `Err`s sharing one window, an `Err(e) =>` arm that
bound the error and let the name escape, a sink whose frame then failed for
another reason, a chain that left a spawned thread into a `JoinHandle`, and
a terminal these rules were never taught. `"SWALLOWED" not in output` is
the assertion they share.

Split from `test_exceptions_rust.py` at the 800-line ceiling; the
accusations are there, the gate and paging in
`test_exceptions_rust_gate.py`.
"""
import pytest

from sensorium import cli
from sensorium.exit import ANSWERED
from tests.rust_traces import (FILE, S1, S2, SITE_FILE, call, err_flow, flow,
                               fn_site, frame, out, ret, rust_trace)


# -- §2a: the holder returned ok with no sink -------------------------------
def test_an_ok_close_with_no_sink_is_ambiguous_never_swallowed(
        tmp_path, monkeypatch, capsys):
    """R8's default. Nothing recorded absorbing the `Err`, so the trace
    cannot say what did -- and "nothing" is not the answer."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "outer", 30], [FILE, "inner", 12]],
        frames=[frame(1, 1, 5), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1,
                          terminal="ambiguous_escaped")),
            ret(4000, 2, 2, "err", "Err(Boom(7))"),
            ret(5000, 1, 1, "ok", "None"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert ("ambiguous -- the frame holding it returned ok with no sink "
            "recorded") in o, o
    assert "left the grammar this recorder watches" in o, o
    assert "dispositions: ambiguous 1" in o, o

# -- §2a: THREAD_END on a spawned thread's outermost frame ------------------
def test_a_chain_that_left_a_spawned_threads_outermost_frame_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "worker", 40], [FILE, "inner", 18]],
        frames=[frame(1, 1, 5, thread=2), frame(2, 2, 4, parent=1, depth=1,
                                                thread=2)],
        events=[
            call(1000, 1, 40, thread=2),
            call(2000, 2, 18, thread=2),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1),
                 thread=2),
            ret(4000, 2, 2, "err", "Err(Boom(7))", thread=2),
            flow(5000, "RAISE", 1, 1, 40,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=2,
                          terminal="left_thread"), thread=2),
        ],
        threads_started=1, live_threads=[])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert ("ambiguous -- it left its thread into a JoinHandle; whether it "
            "was ever read is not recorded") in o, o

# -- §2a: two different Errs in one window (Merged) -------------------------
def test_two_errs_in_one_window_are_both_ambiguous_and_neither_swallowed(
        tmp_path, monkeypatch, capsys):
    """The critic's false-SWALLOWED generator. A window holding two
    distinct `Err`s cannot be split, so no verdict is issued on either."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "outer", 30], [FILE, "inner", 12]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::First", "First", S1, hop=1,
                          terminal="merged")),
            ret(4000, 2, 2, "err", "Err(First)"),
            flow(5000, "RAISE", 1, 1, 33,
                 err_flow("try", "demo::Second", "Second", S2, hop=1,
                          terminal="merged")),
            ret(6000, 1, 1, "ok", "None"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert o.count("ambiguous -- it shared a frame's window with another, "
                   "different Err") == 2, o
    assert ("identity across hops is (type, Debug text) and a window holding "
            "two distinct Errs cannot be split, so a merged window is never "
            "reported as a swallow") in o, o
    assert "dispositions: ambiguous 2" in o, o
    assert "raised (2):" in o, o

# -- §2a refinement (ii): a sink'd chain whose holder then failed -----------
def test_a_sink_whose_frame_then_failed_is_ambiguous_not_swallowed(
        tmp_path, monkeypatch, capsys):
    """`let _ = cleanup(); work()?` -- HONESTY's named blind spot. The
    absorbed `Err` reads ambiguous, and the `Err` that left the frame is a
    chain of its own."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 4)],
        events=[
            call(1000, 1, 3),
            flow(2000, "HANDLED", 1, 1, 5,
                 err_flow("sink_let_underscore", "std::io::Error",
                          "NotFound", S1, hop=1, origin="outside",
                          terminal="handled_then_failed")),
            flow(3000, "RAISE", 1, 1, 3,
                 err_flow("exit", "demo::Boom", "Boom(7)", S2, hop=1,
                          terminal="returned_to_harness")),
            ret(4000, 1, 1, "err", "Err(Boom(7))"),
        ],
        sites=[fn_site("run", SITE_FILE, 3, test=True)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert ("ambiguous -- absorbed by sink_let_underscore at e2 (run L5) in "
            "f1, but f1 then failed anyway") in o, o
    assert "cleanup-then-fail blind spot" in o, o
    assert "dispositions: returned-to-harness 1, ambiguous 1" in o, o

# -- §2a: an `arm_ambiguous` HANDLED ----------------------------------------
def test_an_arm_that_bound_the_error_and_let_it_escape_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """`Err(e) => errors.push(e)` -- the critic's retry-loop shape."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "collect", 30], [FILE, "inner", 12]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1)),
            ret(4000, 2, 2, "err", "Err(Boom(7))"),
            flow(5000, "HANDLED", 1, 1, 33,
                 err_flow("arm_ambiguous", "demo::Boom", "Boom(7)", S1,
                          hop=1, terminal="ambiguous_escaped")),
            ret(6000, 1, 1, "ok", "None"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert ("ambiguous -- an Err(..) arm at e5 (collect L33) bound it to a "
            "name and let the name escape") in o, o
    assert "is not a swallow" in o, o

# -- R8's default: anything the table does not decide -----------------------
@pytest.mark.parametrize("terminal, phrase", [
    (None, "the recording records no ending for this chain"),
    ("teleported", "ends the chain with 'teleported', which these rules do "
                   "not know"),
])
def test_a_terminal_these_rules_do_not_decide_reads_ambiguous(
        tmp_path, monkeypatch, capsys, terminal, phrase):
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 3),
            flow(2000, "RAISE", 1, 1, 5,
                 err_flow("try", "demo::Boom", "Boom(7)", S1, hop=1,
                          terminal=terminal)),
            ret(3000, 1, 1, "ok", "None"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert phrase in o, o
    assert "dispositions: ambiguous 1" in o, o


def test_a_failed_frames_terminal_on_a_non_sink_event_names_no_sink(
        tmp_path, monkeypatch, capsys):
    """The `handled_then_failed` half of the same guard: the verdict names
    the site that absorbed the `Err` only where the chain's last event IS
    one. A `try` RAISE carrying that terminal -- a shape the §2a machine
    does not write -- keeps the disposition and drops the claim."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 3),
            flow(2000, "RAISE", 1, 1, 5,
                 err_flow("try", "demo::Boom", "Boom(7)", S1, hop=1,
                          terminal="handled_then_failed")),
            ret(3000, 1, 1, "err", "Err(Boom(7))"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("ambiguous -- absorbed at e2 (run L5) in f1, but f1 then failed "
            "anyway") in o, o
    assert "absorbed by" not in o, o
    assert "cleanup-then-fail blind spot" in o, o
