"""`exceptions` on a Rust trace: the four dispositions that make a CLAIM.

SWALLOWED is the accusation -- a written sink absorbed the chain and its
frame returned ok -- and E6 gates it, so its guards are here beside it:
a chain born in dependency code, the frame a panic actually unwound, the
frame the harness got it back from, and a chain still travelling when the
recording stopped. The shapes that end in "the trace cannot say" live in
`test_exceptions_rust_ambiguous.py`; the capability gate, the paging and
the tally live in `test_exceptions_rust_gate.py`.

Nothing here recomputes a terminal. A test that hand-wrote
`terminal: "swallowed_candidate"` and then asserted SWALLOWED would be
pinning this module's table, which is the point: the converter's own suite
pins that the machine writes the right terminal for a record stream, and
`tests/test_rust_convert.py` pins that the two halves meet on a real spool.
"""
import json
import sqlite3

from sensorium import cli, paths
from sensorium.exit import ANSWERED
from tests.rust_traces import (FILE, S1, SITE_FILE, call, err_flow, flow,
                               fn_site, frame, harness_trace, out,
                               panic_trace, ret, rust_trace, swallow_trace)


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
def swallow_trace(tmp_path, monkeypatch, **meta):
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
    run_id = swallow_trace(tmp_path, monkeypatch)
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
    assert ("born outside this thread's instrumented frames; absorbed at "
            "sink_let_underscore") in o, o
    assert "dispositions: swallowed 1" in o, o

# -- §2a: the holder unwound ------------------------------------------------
def panic_trace(tmp_path, monkeypatch, unwind_exc):
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
    run_id = panic_trace(tmp_path, monkeypatch, {
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
    run_id = panic_trace(tmp_path, monkeypatch, {
        "kind": "panic", "type": "panic", "serial": 0,
        "msg": "<panic message not recorded: no PANIC record preceded this "
               "unwind>"})
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "panicked -- the frame holding it unwound (f1, panic(" in o, o
    assert "panic message not recorded" in o, o

# -- §2a: THREAD_END on a `test: true` / `main: true` holder ----------------
def harness_trace(tmp_path, monkeypatch, *, test=True, main=False,
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
    run_id = harness_trace(tmp_path, monkeypatch)
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
    run_id = harness_trace(tmp_path, monkeypatch, test=False, main=True)
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
    run_id = harness_trace(tmp_path, monkeypatch, sites=[])
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
    run_id = harness_trace(
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
    # The reason names `live_threads`, the fact this trace actually carries.
    # "INCOMPLETE" is `info`'s word for a recording that never finalized --
    # a different fact, and `info` prints the two apart (vector v10).
    assert ("means the thread was still live when the recording ended "
            "(`live_threads`) or its frames were not all instrumented") in o, o
    assert "only possible on an INCOMPLETE recording" not in o, o
    assert ("hops: e4 deep L18 exit -> e6 mid L11 try -> e7 mid L9 exit "
            "-> e9 outer L7 try -> e10 outer L8 sink_ok") in o, o
    assert "dispositions: propagated 1" in o, o
    # a sink whose frame never returned is not evidence of a swallow
    assert "SWALLOWED" not in o, o

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

# -- the terminal is READ, never recomputed ---------------------------------
def test_dropping_the_terminal_from_the_trace_changes_the_verdict(
        tmp_path, monkeypatch, capsys):
    """The load-bearing claim of placement B: this module reads
    `chain.terminal` and derives nothing. Strip the key from the swallow
    trace's last event and the SWALLOWED verdict must disappear -- if it
    survives, some rule here is recomputing the machine's answer and the
    converter's terminal is decoration."""
    run_id = swallow_trace(tmp_path, monkeypatch)
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


def test_the_harness_frame_is_the_one_still_open_not_the_innermost_marked(
        tmp_path, monkeypatch, capsys):
    """Reviewer's adversarial, fix round 1. A `#[test] fn t()` calls the bin
    crate's `main()`, which is marked `main: true` and re-returns an `Err`
    from `inner`. §2a moves the holder OUT of `main` when `main` closes
    `err`, so at THREAD_END the chain sits in `t` -- and `t`, not `main`, is
    the frame whose mark this verdict is about.

    The last event is the synthesised `exit` RAISE inside `main`, so a walk
    that simply took the innermost MARKED ancestor stopped at `main` and
    named the bin crate's entry point for a chain the test harness got. The
    holder is the innermost ancestor that is still OPEN when the thread
    ends; `main` returned, `t` did not.
    """
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "t", 3], [FILE, "main", 20], [FILE, "inner", 40]],
        frames=[frame(1, 1, None, closed_by=None),
                frame(2, 2, 7, parent=1, depth=1),
                frame(3, 3, 5, parent=2, depth=2)],
        events=[
            call(1000, 1, 3),
            call(2000, 2, 20),
            call(3000, 3, 40),
            flow(4000, "RAISE", 3, 3, 42,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=1)),
            ret(5000, 3, 3, "err", "Err(Boom(7))"),
            flow(6000, "RAISE", 2, 2, 20,
                 err_flow("exit", "demo::Boom", "Boom(7)", S1, hop=2,
                          terminal="returned_to_harness")),
            ret(7000, 2, 2, "err", "Err(Boom(7))"),
        ],
        sites=[fn_site("t", SITE_FILE, 3, test=True),
               fn_site("main", SITE_FILE, 20, main=True),
               fn_site("inner", SITE_FILE, 40)],
        incomplete=True, live_threads=[1])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("returned to the harness -- it came to rest in f1 (t), which the "
            "manifest marks as a #[test] fn") in o, o
    assert "fn main" not in o, o
    assert "f2" not in o, o
    # the frame had not returned when the recording ended, and the verdict
    # must not claim a return it never saw
    assert "f1 had not returned when the recording ended" in o, o


def test_a_terminal_on_an_event_that_absorbs_nothing_names_no_sink(
        tmp_path, monkeypatch, capsys):
    """`SWALLOWED -- absorbed by <how>` reads the `how` off the chain's last
    event, which today is always the sink that took it. Nothing in the trace
    format REQUIRES that: a converter that put `swallowed_candidate` on a
    `try` RAISE -- a shape the §2a machine does not write -- would make this
    command name a `?` as the thing that swallowed an `Err`.

    The verdict still stands (the terminal is the converter's fact); only
    the claim about WHICH site absorbed it is dropped.
    """
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "run", 3]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 3),
            flow(2000, "RAISE", 1, 1, 5,
                 err_flow("try", "demo::Boom", "Boom(7)", S1, hop=1,
                          terminal="swallowed_candidate")),
            ret(3000, 1, 1, "ok", "None"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- absorbed at e2 (run L5) in f1, which returned ok"
            in o), o
    assert "absorbed by" not in o, o

def test_an_unbound_arm_says_what_it_read_in_the_recorders_own_terms(
        tmp_path, monkeypatch, capsys):
    """`corpus/rust/panic`'s shape, as data: `catch_unwind` hands an `Err`
    to an `Err(_) =>` arm, which absorbs it, and `attempt` returns ok.

    Two sentences here were Python's until fix round 2. The value renders
    `Err(<value not read: the arm binds no name>)` -- design R4's
    `err_site_unbound` records neither field, which has nothing to do with
    a `__str__` that raised. And the chain is chainless because no chain was
    open ON THIS THREAD, which is not the same claim as "born in dependency
    code" (R8, amended after Task 7's `join_handle`).
    """
    run_id = rust_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "attempt", 13]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 13),
            flow(2000, "HANDLED", 1, 1, 17,
                 err_flow("arm_handled", "Err", None, S1, hop=1,
                          origin="outside", terminal="swallowed_candidate",
                          unread=["type", "msg"])),
            ret(3000, 1, 1, "ok", "Ok(0)"),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("e2 HANDLED attempt handled "
            "Err(<value not read: the arm binds no name>) L17") in o, o
    assert "__str__" not in o and "message unreadable" not in o, o
    assert ("SWALLOWED -- absorbed by arm_handled at e2 (attempt L17) in f1, "
            "which returned ok") in o, o
    assert ("born outside this thread's instrumented frames; absorbed at "
            "arm_handled") in o, o
