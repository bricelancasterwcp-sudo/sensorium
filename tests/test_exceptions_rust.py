"""`exceptions` on a Rust trace: one test per §2a row's VERDICT.

The chain machine lives in the converter (`rust/cargo-sensorium`'s
`convert/chains`) and writes one fact per chain -- `chain.terminal` on the
chain's last event. This module owns what that fact becomes when a person
asks: the five dispositions of design R8, and the wording each one earns.
So every test here states a recording as data (`tests.helpers.rust_trace`,
the same builder the conformance vectors use) and asserts on the rendered
answer, exactly as `tests/test_exceptions.py` does for the Python rules.

Nothing here recomputes a terminal. A test that hand-wrote
`terminal: "swallowed_candidate"` and then asserted SWALLOWED would be
pinning this module's table, which is the point: the converter's own suite
pins that the machine writes the right terminal for a record stream, and
`tests/test_rust_convert.py` pins that the two halves meet on a real spool.
"""
import json
import sqlite3

import pytest

from sensorium import cli, paths
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from tests.helpers import (RUST_CAPABILITIES, err_flow, fn_site,
                          rust_exc, rust_trace)

FILE = "/w/demo/src/lib.rs"
SITE_FILE = "demo/src/lib.rs"
S1 = 4294967296          # 1 << 32: the first chain serial on a thread
S2 = 4294967297


# -- vector-body shorthands -------------------------------------------------
def call(ts, code, line, thread=1):
    return {"ts": ts, "thread": thread, "kind": "CALL", "code": code,
            "line": line, "payload": {"args": {}, "unread": ["locals"]},
            "task": None}


def ret(ts, frame, code, outcome, value="()", thread=1):
    return {"ts": ts, "thread": thread, "kind": "RETURN", "frame": frame,
            "code": code, "line": None,
            "payload": {"outcome": outcome,
                        "value": {"k": "dbg", "v": value, "trunc": False}},
            "task": None}


def flow(ts, kind, frame, code, line, payload, thread=1):
    return {"ts": ts, "thread": thread, "kind": kind, "frame": frame,
            "code": code, "line": line, "payload": payload, "task": None}


def frame(code, call_ev, ret_ev=None, parent=None, depth=0, thread=1,
          closed_by="return", unwind_exc=None):
    fr = {"parent": parent, "code": code, "call": call_ev, "depth": depth,
          "thread": thread, "kind": "function"}
    if ret_ev is not None:
        fr["return"] = ret_ev
    if closed_by is not None and ret_ev is not None:
        fr["closed_by"] = closed_by
    if unwind_exc is not None:
        fr["closed_by"] = "unwind"
        fr["unwind_exc"] = unwind_exc
    return fr


def out(capsys):
    return capsys.readouterr().out


# -- §2a: a sink absorbed it and its frame returned ok ----------------------
def _swallow_trace(tmp_path, monkeypatch, **meta):
    """`load()` calls `read_config()`, which returns `Err`; `load` sinks it
    with `.ok()` and returns ok. The one shape reported as a swallow."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 30], [FILE, "read_config", 12]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 30),
            call(2000, 2, 12),
            flow(3000, "RAISE", 2, 2, 14,
                 err_flow("exit", "demo::ConfigError", 'Missing("port")', S1,
                          hop=1, loc=f"{SITE_FILE}:14")),
            ret(4000, 2, 2, "err", 'Err(Missing("port"))'),
            flow(5000, "HANDLED", 1, 1, 31,
                 err_flow("sink_ok", "demo::ConfigError", 'Missing("port")',
                          S1, hop=1, terminal="swallowed_candidate",
                          loc=f"{SITE_FILE}:31")),
            ret(6000, 1, 1, "ok", "None"),
        ],
        sites=[fn_site("load", SITE_FILE, 30), fn_site("read_config",
                                                       SITE_FILE, 12)],
        **meta)


def test_a_sink_then_an_ok_close_is_the_one_shape_reported_as_swallowed(
        tmp_path, monkeypatch, capsys):
    run_id = _swallow_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (1):" in o, o
    # reported at the ORIGIN, with the origin's own type
    assert ("e3 RAISE   read_config raise "
            "demo::ConfigError('Missing(\"port\")') L14") in o, o
    assert ("SWALLOWED -- absorbed by sink_ok at e5 (load L31) in f1, "
            "which returned ok") in o, o
    assert "hops: e3 read_config L14 exit -> e5 load L31 sink_ok" in o, o
    assert "dispositions: swallowed 1" in o, o
    # a workspace-born chain is never described as one from a dependency
    assert "born outside" not in o, o


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


# -- §2a: the holder unwound ------------------------------------------------
def _panic_trace(tmp_path, monkeypatch, unwind_exc):
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "inner", 18]],
        frames=[frame(1, 1, None, closed_by=None, unwind_exc=unwind_exc),
                frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1,
                          terminal="panicked")),
            ret(4000, 2, 2, "err", "Err(Boom(7))"),
        ])


def test_a_panic_on_the_holder_quotes_the_panic_and_claims_no_cause(
        tmp_path, monkeypatch, capsys):
    run_id = _panic_trace(tmp_path, monkeypatch, {
        "kind": "panic", "type": "panic",
        "msg": "called `Result::unwrap()` on an `Err` value: Boom(7)",
        "serial": 1, "loc": "demo/src/lib.rs:5:9"})
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("panicked -- the frame holding it unwound (f1, panic('called "
            "`Result::unwrap()` on an `Err` value: Boom(7)'))") in o, o
    # R8: never that the panic was BECAUSE of the Err
    assert ("f1 unwound while holding this Err, not that the Err caused "
            "the panic") in o, o
    assert "dispositions: panicked 1" in o, o


def test_a_panic_whose_message_was_not_recorded_says_so(
        tmp_path, monkeypatch, capsys):
    """HONESTY §1: a panic with no PANIC record carries serial 0 and a
    literal message saying why it cannot be quoted. The verdict repeats
    that rather than printing an empty pair of quotes."""
    run_id = _panic_trace(tmp_path, monkeypatch, {
        "kind": "panic", "type": "panic", "serial": 0,
        "msg": "<panic message not recorded: no PANIC record preceded this "
               "unwind>"})
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "panicked -- the frame holding it unwound (f1, panic(" in o, o
    assert "panic message not recorded" in o, o


# -- §2a: THREAD_END on a `test: true` / `main: true` holder ----------------
def _harness_trace(tmp_path, monkeypatch, *, test=True, main=False,
                   sites=None):
    """`#[test] fn run()` takes an `Err` by `?` and returns it."""
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "inner", 18]],
        frames=[frame(1, 1, 7, closed_by="return"),
                frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(9)", S1, hop=1)),
            ret(4000, 2, 2, "err", "Err(Boom(9))"),
            flow(5000, "RAISE", 1, 1, 6,
                 err_flow("try", "demo::Boom", "Boom(9)", S1, hop=2)),
            flow(6000, "RAISE", 1, 1, 3,
                 err_flow("exit", "demo::Boom", "Boom(9)", S1, hop=3,
                          terminal="returned_to_harness")),
            ret(7000, 1, 1, "err", "Err(Boom(9))"),
        ],
        sites=(sites if sites is not None else
               [fn_site("run", SITE_FILE, 3, test=test, main=main),
                fn_site("inner", SITE_FILE, 18)]))


def test_a_chain_a_test_fn_returned_went_back_to_the_harness(
        tmp_path, monkeypatch, capsys):
    run_id = _harness_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("returned to the harness -- it left f1 (run), which the "
            "manifest marks as a #[test] fn") in o, o
    assert "dispositions: returned-to-harness 1" in o, o
    # one chain, three hops, reported ONCE at its origin
    assert "raised (1):" in o, o
    assert ("hops: e3 inner L18 exit -> e5 run L6 try -> e6 run L3 exit"
            ) in o, o


def test_the_same_chain_out_of_fn_main_names_main_not_a_test(
        tmp_path, monkeypatch, capsys):
    run_id = _harness_trace(tmp_path, monkeypatch, test=False, main=True)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("returned to the harness -- it left f1 (run), which the "
            "manifest marks as the bin crate's fn main") in o, o
    assert "#[test]" not in o, o


def test_a_harness_return_the_site_table_cannot_name_still_says_so(
        tmp_path, monkeypatch, capsys):
    """The terminal is the converter's fact and stands on its own. Where
    the site table carries no row for the frame, the verdict keeps the
    disposition and drops the claim it cannot support."""
    run_id = _harness_trace(tmp_path, monkeypatch, sites=[])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("returned to the harness -- it left a frame the recording marks "
            "as a test or main entry point") in o, o
    assert "the site table carries no row" in o, o
    assert "dispositions: returned-to-harness 1" in o, o


def test_a_site_table_that_contradicts_itself_earns_no_mark(
        tmp_path, monkeypatch, capsys):
    """Two rows for one `(qualname, file)` disagreeing about which mark it
    carries is a table that cannot say, and picking whichever came first
    would print a claim about the program from a coin toss. The
    disposition -- the converter's fact -- still stands."""
    run_id = _harness_trace(
        tmp_path, monkeypatch,
        sites=[fn_site("run", SITE_FILE, 3, test=True),
               fn_site("run", SITE_FILE, 3, main=True, site=9),
               fn_site("inner", SITE_FILE, 18)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "#[test]" not in o and "fn main" not in o, o
    assert ("returned to the harness -- it left a frame the recording marks "
            "as a test or main entry point") in o, o


def test_a_marked_qualname_in_another_file_is_not_this_frames_mark(
        tmp_path, monkeypatch, capsys):
    """The site table's `file` is workspace-relative and a trace's
    `code_objects.file` is absolute, so the join is a path-SEGMENT suffix.
    Two files each defining `run`, one of them a `#[test]`: the unmarked
    one must not inherit the mark, or the command reports an ordinary
    helper as a test entry point."""
    other = "/w/demo/src/util.rs"
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[other, "run", 3], [FILE, "inner", 18]],
        frames=[frame(1, 1, 5), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(9)", S1, hop=1)),
            ret(4000, 2, 2, "err", "Err(Boom(9))"),
            flow(5000, "RAISE", 1, 1, 3,
                 err_flow("exit", "demo::Boom", "Boom(9)", S1, hop=2,
                          terminal="returned_to_harness")),
        ],
        sites=[fn_site("run", SITE_FILE, 3, test=True),
               fn_site("inner", SITE_FILE, 18)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "#[test]" not in o, o
    assert ("returned to the harness -- it left a frame the recording marks "
            "as a test or main entry point") in o, o


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
    assert "dispositions: ambiguous 2" in o, o
    assert "raised (2):" in o, o


# -- R8: a chain whose type changed on the way out --------------------------
def test_a_hop_that_changed_the_error_type_is_labelled_translated(
        tmp_path, monkeypatch, capsys):
    """One chain, two types: the head prints the ORIGIN's type and the hop
    trail names the type each hop carried, with the change labelled."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "inner", 18]],
        frames=[frame(1, 1, 6), frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1)),
            ret(4000, 2, 2, "err", "Err(Boom(7))"),
            flow(5000, "RAISE", 1, 1, 3,
                 err_flow("exit", "demo::AppError", "Config(Boom(7))", S1,
                          hop=2, translated=True,
                          terminal="returned_to_harness")),
            ret(6000, 1, 1, "err", "Err(Config(Boom(7)))"),
        ],
        sites=[fn_site("run", SITE_FILE, 3, test=True)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (1):" in o, o                # ONE chain, not two
    assert "inner raise demo::Boom('Boom(7)') L18" in o, o
    assert ("hops: e3 inner L18 exit -> e5 run L3 exit "
            "(translated to demo::AppError)") in o, o


# -- §2a: a HANDLED with no chain to continue -------------------------------
def test_a_chain_born_outside_instrumented_code_says_so_under_its_verdict(
        tmp_path, monkeypatch, capsys):
    """`let _ = fs::remove_file(p);` -- the `Err` was made where this
    recording could not see it, and the sink is the first thing known of
    it. Still SWALLOWED, and the detail says where it came from."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "cleanup", 50]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 50),
            flow(2000, "HANDLED", 1, 1, 52,
                 err_flow("sink_let_underscore", "std::io::Error",
                          'Os { code: 2, kind: NotFound }', S1, hop=1,
                          origin="outside", terminal="swallowed_candidate")),
            ret(3000, 1, 1, "ok", "()"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- absorbed by sink_let_underscore at e2 "
            "(cleanup L52) in f1, which returned ok") in o, o
    assert ("born outside instrumented code; absorbed at "
            "sink_let_underscore") in o, o
    assert "dispositions: swallowed 1" in o, o


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


# -- §2a: still open when the thread ended, on an unmarked frame ------------
def test_a_chain_still_open_when_the_thread_ended_is_propagated(
        tmp_path, monkeypatch, capsys):
    """R8's PROPAGATED, with the reason it is possible at all stated and
    every hop listed."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "outer", 5], [FILE, "mid", 9], [FILE, "deep", 18]],
        frames=[frame(1, 1, None, closed_by=None),
                frame(2, 2, 8, parent=1, depth=1),
                frame(3, 3, 5, parent=2, depth=2)],
        events=[
            call(1000, 1, 5),
            call(2000, 2, 9),
            call(3000, 3, 18),
            flow(4000, "RAISE", 3, 3, 18,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1)),
            ret(5000, 3, 3, "err", "Err(Boom(7))"),
            flow(6000, "RAISE", 2, 2, 11,
                 err_flow("try", "demo::Boom", "Boom(7)", S1, hop=2)),
            flow(7000, "RAISE", 2, 2, 9,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=3)),
            ret(8000, 2, 2, "err", "Err(Boom(7))"),
            flow(9000, "RAISE", 1, 1, 7,
                 err_flow("try", "demo::Boom", "Boom(7)", S1, hop=4)),
            # A sink fired and the frame holding the chain never closed, so
            # nothing says it was absorbed: an event that observes a chain
            # WITHOUT crossing a frame carries the hop it happened at, which
            # is why the hop count is read off the events and not counted
            # from them.
            flow(10000, "HANDLED", 1, 1, 8,
                 err_flow("sink_ok", "demo::Boom", "Boom(7)", S1, hop=4,
                          terminal="propagated")),
        ],
        incomplete=True, live_threads=[1])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "INCOMPLETE: this recording never finalized" in o, o
    # five events, four frames crossed
    assert "propagated -- 4 hops, and still open when the thread ended" in o, o
    assert ("only possible on an INCOMPLETE recording or a thread whose "
            "frames were not all instrumented") in o, o
    assert ("hops: e4 deep L18 exit -> e6 mid L11 try -> e7 mid L9 exit "
            "-> e9 outer L7 try -> e10 outer L8 sink_ok") in o, o
    assert "dispositions: propagated 1" in o, o
    # a sink whose frame never returned is not evidence of a swallow
    assert "SWALLOWED" not in o, o


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


# -- the five dispositions, the tally, and paging ---------------------------
def _five_dispositions(tmp_path, monkeypatch):
    """One trace holding every disposition, on five threads so each shape
    is minimal. The chains are laid out in REVERSE tally order, so a tally
    printed in encounter order would come out backwards."""
    unwind = {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1}
    return rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "escapes", 5], [FILE, "inner", 18], [FILE, "stuck", 9],
               [FILE, "run", 3], [FILE, "crash", 40], [FILE, "swallow", 60]],
        frames=[
            frame(1, 1, 5),                                   # f1 escapes
            frame(2, 2, 4, parent=1, depth=1),                # f2 inner
            frame(3, 6, None, closed_by=None, thread=2),      # f3 stuck
            frame(2, 7, 9, parent=3, depth=1, thread=2),      # f4 inner
            frame(4, 10, 15, thread=3),                       # f5 run
            frame(2, 11, 13, parent=5, depth=1, thread=3),    # f6 inner
            frame(5, 16, None, thread=4, unwind_exc=unwind),  # f7 crash
            frame(2, 17, 19, parent=7, depth=1, thread=4),    # f8 inner
            frame(6, 20, 22, thread=5),                       # f9 swallow
        ],
        events=[
            # thread 1 -- ambiguous (ok close, no sink)
            call(1000, 1, 5),
            call(1100, 2, 18),
            flow(1200, "RAISE", 2, 2, 18,
                 err_flow("exit", "demo::Boom", "A", S1, hop=1,
                          terminal="ambiguous_escaped")),
            ret(1300, 2, 2, "err", "Err(A)"),
            ret(1400, 1, 1, "ok", "None"),
            # thread 2 -- propagated (still open at the end)
            call(2000, 3, 9, thread=2),
            call(2100, 2, 18, thread=2),
            flow(2200, "RAISE", 4, 2, 18,
                 err_flow("exit", "demo::Boom", "B", S1, hop=1,
                          terminal="propagated"), thread=2),
            ret(2300, 4, 2, "err", "Err(B)", thread=2),
            # thread 3 -- returned to harness
            call(3000, 4, 3, thread=3),
            call(3100, 2, 18, thread=3),
            flow(3200, "RAISE", 6, 2, 18,
                 err_flow("exit", "demo::Boom", "C", S1, hop=1), thread=3),
            ret(3300, 6, 2, "err", "Err(C)", thread=3),
            flow(3400, "RAISE", 5, 4, 3,
                 err_flow("exit", "demo::Boom", "C", S1, hop=2,
                          terminal="returned_to_harness"), thread=3),
            ret(3500, 5, 4, "err", "Err(C)", thread=3),
            # thread 4 -- panicked
            call(4000, 5, 40, thread=4),
            call(4100, 2, 18, thread=4),
            flow(4200, "RAISE", 8, 2, 18,
                 err_flow("exit", "demo::Boom", "D", S1, hop=1,
                          terminal="panicked"), thread=4),
            ret(4300, 8, 2, "err", "Err(D)", thread=4),
            # thread 5 -- swallowed
            call(5000, 6, 60, thread=5),
            flow(5100, "HANDLED", 9, 6, 62,
                 err_flow("sink_ok", "demo::Boom", "E", S1, hop=1,
                          terminal="swallowed_candidate"), thread=5),
            ret(5200, 9, 6, "ok", "()", thread=5),
        ],
        sites=[fn_site("run", SITE_FILE, 3, test=True)],
        incomplete=True, live_threads=[2])


def test_the_tally_is_printed_in_the_pinned_order(
        tmp_path, monkeypatch, capsys):
    run_id = _five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("dispositions: swallowed 1, panicked 1, returned-to-harness 1, "
            "propagated 1, ambiguous 1") in o, o
    assert "raised (5):" in o, o


def test_limit_clips_the_rows_but_never_the_tally(
        tmp_path, monkeypatch, capsys):
    run_id = _five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id, "--limit", "2"]) == ANSWERED
    o = out(capsys)
    assert "e3 RAISE" in o and "e8 RAISE" in o, o
    assert "e12 RAISE" not in o and "e18 RAISE" not in o, o
    # every chain in scope is counted, printed or not
    assert ("dispositions: swallowed 1, panicked 1, returned-to-harness 1, "
            "propagated 1, ambiguous 1") in o, o
    assert ("... 3 more; continue with: sensorium exceptions "
            f"{run_id} --after e8 --limit 2") in o, o


def test_after_resumes_from_a_chains_origin_and_says_what_it_skipped(
        tmp_path, monkeypatch, capsys):
    run_id = _five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id, "--after", "e8"]) == ANSWERED
    o = out(capsys)
    assert ("raised (3 of 5; 2 earlier chain(s) skipped by --after e8):"
            in o), o
    assert "e3 RAISE" not in o and "e8 RAISE" not in o, o
    assert "dispositions: swallowed 1, panicked 1, returned-to-harness 1" in o
    assert "propagated" not in o, o


# -- the Index selects on exc.kind, never on a type spelled "panic" ---------
def test_an_err_type_spelled_panic_is_judged_and_a_panic_raise_is_not(
        tmp_path, monkeypatch, capsys):
    """R7: the Rust index selects by `exc.kind`. A workspace error type
    literally named `panic` is a chain; a panic RAISE is not one, and is
    named rather than silently dropped."""
    unwind = {"kind": "panic", "type": "panic", "msg": "boom", "serial": 1}
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3], [FILE, "weird", 18]],
        frames=[frame(1, 1, None, thread=1, unwind_exc=unwind),
                frame(2, 2, 4, parent=1, depth=1)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 18),
            flow(3000, "RAISE", 2, 2, 18,
                 err_flow("exit", "panic", "Deliberate", S1, hop=1,
                          terminal="panicked")),
            ret(4000, 2, 2, "err", "Err(Deliberate)"),
            {"ts": 5000, "thread": 1, "kind": "RAISE", "frame": 1, "code": 1,
             "line": 5,
             "payload": {"exc": rust_exc("panic", "boom", 1,
                                         loc="demo/src/lib.rs:5:9",
                                         kind="panic")},
             "task": None},
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (1):" in o, o           # the err, not the panic
    assert "weird raise panic('Deliberate') L18" in o, o
    assert "panicked -- the frame holding it unwound (f1, panic('boom'))" in o
    # the panic RAISE is not a chain, and the answer says it exists
    assert ("panics: 1 recorded -- this command judges Err flow; a panic is "
            "a frame's unwind, printed by `tree` and `frame`") in o, o


# -- R9: the capability gate, before any rule runs --------------------------
def test_a_rust_trace_whose_recorder_declares_no_err_flow_is_refused(
        tmp_path, monkeypatch, capsys):
    """A rung-2 recording holds no err-flow record, so what would have to
    change is the recording. Exit 3, the standard capability sentence, and
    nothing judged."""
    caps = {"line": False, "locals": False, "return_value": True,
            "tasks": True, "threads": True, "children": False,
            "stdin": False, "output": False, "object_identity": False,
            "refocus": False}
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")],
        recorder="sensorium-rt 0.2.0", capabilities=caps,
        run_id="20260101-000000-rung02")
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions needs err_flow, which recorder "
            "sensorium-rt 0.2.0 declares it does not produce "
            "(capabilities.err_flow: false); nothing was checked") in o, o
    assert "no exceptions recorded" not in o, o
    assert "raised (" not in o and "dispositions:" not in o, o
    # the retired rung-2 sentence must not come back for a Rust trace
    assert "needs the Rust disposition rules" not in o, o


def test_the_capability_gate_runs_before_any_rule_sees_a_chain(
        tmp_path, monkeypatch, capsys):
    """The same trace as the swallow case, with the declaration removed:
    a refusal, not a verdict computed from records the recorder disowns."""
    caps = dict(RUST_CAPABILITIES)
    caps.pop("err_flow")
    run_id = _swallow_trace(tmp_path, monkeypatch, capabilities=caps,
                            recorder="sensorium-rt 0.2.0")
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert "capabilities.err_flow: false" in o, o


# -- the empty answers ------------------------------------------------------
def test_a_finalized_rust_trace_with_no_err_chains_answers_none(
        tmp_path, monkeypatch, capsys):
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")])
    assert cli.main(["exceptions", run_id]) == NEGATIVE
    o = out(capsys)
    assert "no exceptions recorded" in o, o


def test_an_incomplete_rust_trace_with_no_err_chains_is_unsettled(
        tmp_path, monkeypatch, capsys):
    """`caps.none_status`: an empty answer on a recording that stopped
    mid-flight reports where the RECORDING ended, not what the program
    did."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, None, closed_by=None)],
        events=[call(1000, 1, 3)],
        incomplete=True, live_threads=[1])
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert "INCOMPLETE: this recording never finalized" in o, o
    assert "no exceptions recorded" in o, o


# -- R6: `?` sites the transformer could not reach --------------------------
def test_a_partial_fn_is_named_rather_than_guessed_about(
        tmp_path, monkeypatch, capsys):
    """Corpus `macro_arg_partial`: an `Err` at an unreachable `?` site is
    recorded by nothing, so `exceptions` says the site exists instead of
    letting its silence read as "nothing happened there"."""
    run_id = _swallow_trace(
        tmp_path, monkeypatch,
        partial=[{"file": SITE_FILE, "line": 21, "qualname": "load",
                  "kind": "try", "reason": "macro-arg"}])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("partial: 1 ?-site the transformer could not reach -- an Err "
            "raised at one is recorded by nothing and appears nowhere "
            "below") in o, o
    assert f"load {SITE_FILE}:21 (macro-arg)" in o, o


def test_a_trace_with_no_partial_key_says_nothing_about_partial_sites(
        tmp_path, monkeypatch, capsys):
    run_id = _swallow_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    assert "partial:" not in out(capsys)


# -- a third language keeps the lang-keyed refusal --------------------------
def test_a_language_with_no_rules_at_all_still_gets_the_lang_refusal(
        tmp_path, monkeypatch, capsys):
    """R9: only the `rust` branch of `_language_refusal` retires."""
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 3), ret(2000, 1, 1, "ok", "()")],
        lang="go", recorder="sensorium-go 0.1.0")
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions on a go trace needs the Rust disposition "
            "rules (rung 3); the Python rules would misread Err values as "
            "exceptions; nothing was judged") in o, o


# -- the terminal is READ, never recomputed ---------------------------------
def test_dropping_the_terminal_from_the_trace_changes_the_verdict(
        tmp_path, monkeypatch, capsys):
    """The load-bearing claim of placement B: this module reads
    `chain.terminal` and derives nothing. Strip the key from the swallow
    trace's last event and the SWALLOWED verdict must disappear -- if it
    survives, some rule here is recomputing the machine's answer and the
    converter's terminal is decoration."""
    run_id = _swallow_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    assert "SWALLOWED" in out(capsys)

    conn = sqlite3.connect(paths.traces_dir() / f"{run_id}.db")
    row = conn.execute("SELECT id, payload FROM events WHERE kind = 'HANDLED'"
                       ).fetchone()
    payload = json.loads(row[1])
    del payload["chain"]["terminal"]
    conn.execute("UPDATE events SET payload = ? WHERE id = ?",
                 (json.dumps(payload), row[0]))
    conn.commit()
    conn.close()

    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "SWALLOWED" not in o, o
    assert "the recording records no ending for this chain" in o, o
