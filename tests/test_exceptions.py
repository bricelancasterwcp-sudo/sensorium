"""`exceptions`: every raise and what became of it.

Organised one test per program *shape*. The head of the trace is
byte-identical for behaviours that mean opposite things -- a genuine
swallow, a bare `raise` re-raise, and an exception merely crossing a
`finally` all produce RAISE + HANDLED with no later RAISE -- so a shape
is the smallest unit that can tell them apart. Every expectation here was
read off a real recorded trace before the classifier existed.
"""
import shlex

from sensorium import cli, paths
from sensorium.store.reader import Trace
from tests.programs import (
    BARE_RERAISE, CLEAN, CRASH, EXPLICIT_RERAISE, EXPLICIT_RERAISE_ESCAPES,
    FINALLY_PASSTHROUGH, GENERATOR_HANDLES, LOOP_SAME_MESSAGE,
    RAISE_CAUGHT_UNTRACED, RERAISE_CAUGHT_UNTRACED,
    RETRY_LOOP_REUSED_ADDRESS, RETRY_THEN_RAISE_LAST, STASH_AND_RERAISE,
    SWALLOW, SWALLOW_THEN_UNRELATED, TRANSLATED, UNTRACED_LIB,
    UNTRACED_LIB_SOURCE, exc_payload, record, synthetic)


# -- exceptions: one test per program shape --------------------------------
def test_exceptions_flags_genuine_swallow(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 2          # carol,x7 and erin,??
    assert "ValueError" in out and "load_all" in out
    assert "returned normally" in out
    assert "swallowed 2" in out


def test_exceptions_reports_uncaught(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CRASH)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "uncaught: AttributeError" in out
    assert "SWALLOWED" not in out
    # pin the verdict, not merely the absence of the wrong one: a classifier
    # that fell through to some other branch would still satisfy the above
    assert "uncaught -- left the program (exit 1); not swallowed" in out
    assert "dispositions: uncaught 1" in out
    assert "raised at e" in out                  # header links to the RAISE


def test_exceptions_never_calls_a_bare_reraise_swallowed(
        tmp_path, monkeypatch, capsys):
    """RAISE + HANDLED + no later RAISE, and yet nothing was swallowed."""
    run_id = record(tmp_path, monkeypatch, BARE_RERAISE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    # not merely "not swallowed" -- the verdict has to be the right one
    assert "uncaught -- left the program (exit 1); not swallowed" in out
    assert "uncaught 1" in out
    assert "not a catch" in out                  # the HANDLED rows explained


def test_exceptions_never_calls_a_finally_passthrough_swallowed(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, FINALLY_PASSTHROUGH)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "uncaught: ValueError('boom')" in out
    # the shape that makes this hard: HANDLED rows really are present
    assert "HANDLED row(s)" in out


def test_exceptions_refuses_to_guess_when_the_handler_is_untraced(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, RERAISE_CAUGHT_UNTRACED,
                    extra=("--exclude", "lib.py"),
                    files=(("lib.py", UNTRACED_LIB_SOURCE),))
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "propagated (handler not in traced code)" in out


def test_exceptions_translation_and_unrelated_failure_read_the_same(
        tmp_path, monkeypatch, capsys):
    """Two programs, opposite behaviour, indistinguishable traces. The tool
    must report the same thing for both and claim neither."""
    a = record(tmp_path / "a", monkeypatch, TRANSLATED)
    assert cli.main(["exceptions", a]) == 0
    out_a = capsys.readouterr().out
    b = record(tmp_path / "b", monkeypatch, SWALLOW_THEN_UNRELATED)
    assert cli.main(["exceptions", b]) == 0
    out_b = capsys.readouterr().out

    for out in (out_a, out_b):
        # the ValueError: caught here, but the frame died of something else
        assert "unwound with RuntimeError" in out
        assert "cannot say" in out
        assert "ambiguous 1" in out
        # the RuntimeError: genuinely swallowed by main's `except: pass`
        assert out.count("SWALLOWED") == 1
        assert "swallowed 1" in out


def test_exceptions_attributes_an_untraced_library_raise_to_its_caller(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, UNTRACED_LIB)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "JSONDecodeError" in out
    assert out.count("SWALLOWED") == 1
    assert "parse L" in out                     # the traced frame that caught


def test_exceptions_reports_an_explicit_reraise_as_raised_again(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, EXPLICIT_RERAISE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "raised again at e" in out
    assert "re-raised 1" in out
    assert out.count("SWALLOWED") == 1          # main's `except: pass`


def test_exceptions_never_claims_a_reraise_for_a_reused_address(
        tmp_path, monkeypatch, capsys):
    """Fix round 2. A plain retry loop reuses one address for three separate
    ValueError('fail') objects, and the handler frame unwinds so rule 2
    cannot fire. Rule 3 used to report two of them as "then raised again at
    eN" -- asserting a re-raise that never happened."""
    run_id = record(tmp_path, monkeypatch, RETRY_LOOP_REUSED_ADDRESS)
    # the collision is the whole point: prove it happened, so this test can
    # never quietly pass by testing a shape that no longer collides
    trace = Trace.open(paths.find_trace(run_id))
    ids = [(e.payload["exc"]["type"], e.payload["exc"]["msg"],
            e.payload["exc"]["oid"]) for e in trace.events(kind="RAISE")]
    fails = [k for k in ids if k[0] == "ValueError"]
    assert len(fails) == 3, ids
    assert len(set(fails)) == 1, (
        "this shape no longer reproduces the natural oid collision it exists "
        f"to pin; got {fails}")

    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "then raised again at e" not in out
    assert "same statement" in out
    assert "reused address" in out
    assert "re-raised" not in out.splitlines()[-1]       # not in the tally


def test_exceptions_keeps_a_genuine_stored_reraise_confident(
        tmp_path, monkeypatch, capsys):
    """The other half of the fix: a re-raise from a *different* statement is
    still asserted outright. A classifier that hedged every repeated identity
    would be as useless as one that hedged none."""
    run_id = record(tmp_path, monkeypatch, RETRY_THEN_RAISE_LAST)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "then raised again at e" in out
    assert "re-raised 1" in out
    assert "same statement" not in out


def test_exceptions_never_calls_a_stored_and_reraised_exception_swallowed(
        tmp_path, monkeypatch, capsys):
    """A returning handler frame is the swallow signal, but `return e` hands
    the exception out of that frame. With a later RAISE of the same identity
    both readings are live -- address reuse, or stored and raised again --
    so neither may be asserted."""
    run_id = record(tmp_path, monkeypatch, STASH_AND_RERAISE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "never re-raised" not in out          # it demonstrably was
    assert "uncaught: ValueError('x')" in out
    # the verdict names both live readings and picks neither
    assert "returned normally, but a later RAISE" in out
    assert "raised again" in out
    assert "reused address" in out
    assert "cannot tell them apart" in out
    assert "dispositions: uncaught 1, ambiguous 1" in out


def test_exceptions_output_never_contradicts_its_own_uncaught_header(
        tmp_path, monkeypatch, capsys):
    """No verdict may claim an exception ended in traced code when the
    header says that same identity left the program."""
    for src in (STASH_AND_RERAISE, EXPLICIT_RERAISE_ESCAPES, BARE_RERAISE):
        d = tmp_path / str(abs(hash(src)) % 10 ** 6)
        run_id = record(d, monkeypatch, src)
        assert cli.main(["exceptions", run_id]) == 0
        out = capsys.readouterr().out
        assert out.splitlines()[0].startswith("uncaught: ")
        assert "SWALLOWED" not in out, src
        assert "never re-raised" not in out, src
        # and no `swallowed N` bucket in the tally either
        tally = next(ln for ln in out.splitlines()
                     if ln.startswith("dispositions: "))
        assert "swallowed" not in tally, src


def test_exceptions_uncaught_header_names_the_raise_that_escaped(
        tmp_path, monkeypatch, capsys):
    """Two RAISE rows share one identity; the header must point at the later
    one, which is the object that actually left the program."""
    run_id = record(tmp_path, monkeypatch, EXPLICIT_RERAISE_ESCAPES)
    assert cli.main(["exceptions", run_id]) == 0
    lines = capsys.readouterr().out.splitlines()
    rows = [ln for ln in lines if " RAISE " in ln]
    assert len(rows) == 2
    first, last = (r.strip().split()[0] for r in rows)
    assert lines[0].endswith(f"raised at {last}")
    assert f"raised at {first}" not in lines[0]


def test_exceptions_pairs_each_loop_raise_with_its_own_handler(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, LOOP_SAME_MESSAGE)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 3
    handlers = [ln.split("SWALLOWED at ")[1].split()[0]
                for ln in out.splitlines() if "SWALLOWED at " in ln]
    assert len(set(handlers)) == 3              # three distinct HANDLED rows


def test_exceptions_refuses_to_classify_a_frameless_handler(
        tmp_path, monkeypatch, capsys):
    """Generators open no frame, so there is no closed_by to read and no
    honest verdict to give -- saying so beats guessing."""
    run_id = record(tmp_path, monkeypatch, GENERATOR_HANDLES)
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "no frame recorded" in out
    assert "generator" in out


def test_exceptions_says_so_when_nothing_was_raised(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, CLEAN)
    assert cli.main(["exceptions", run_id]) == 0
    assert capsys.readouterr().out.strip() == "no exceptions recorded"


# -- exceptions: synthetic traces for shapes CPython will not reproduce ----
def test_exceptions_survives_a_recycled_oid(tmp_path, monkeypatch, capsys):
    """`oid` is `id(exc)` and CPython reuses addresses: measured live, a
    ValueError and the RuntimeError raised two lines later in the same frame
    shared an oid. Identity must therefore be (type, msg, oid) -- keyed on
    oid alone, the RuntimeError's handler would be credited to the
    ValueError and one of them would be mis-classified."""
    w = synthetic(tmp_path, monkeypatch)
    c_risky = w.intern_code("/tmp/prog.py", "risky", 1)
    c_main = w.intern_code("/tmp/prog.py", "main", 8)
    e_call_main = w.add_event(0, 1, "CALL", None, c_main, 8, {"args": {}})
    f_main = w.open_frame(None, c_main, e_call_main, 0, 1)
    e_call = w.add_event(0, 1, "CALL", None, c_risky, 1, {"args": {}})
    f_risky = w.open_frame(f_main, c_risky, e_call, 1, 1)
    val = exc_payload("ValueError", "boom", 999)
    run = exc_payload("RuntimeError", "later", 999)          # same address, new object
    e_raise_v = w.add_event(0, 1, "RAISE", f_risky, c_risky, 3, {"exc": val})
    e_hand_v = w.add_event(0, 1, "HANDLED", f_risky, c_risky, 4, {"exc": val})
    e_raise_r = w.add_event(0, 1, "RAISE", f_risky, c_risky, 6, {"exc": run})
    w.close_frame(f_risky, None, "unwind", run)
    e_hand_r = w.add_event(0, 1, "HANDLED", f_main, c_main, 11, {"exc": run})
    e_ret = w.add_event(0, 1, "RETURN", f_main, c_main, None, {"value": None})
    w.close_frame(f_main, e_ret, "return")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    # the ValueError was not re-raised as the RuntimeError, and was not
    # swallowed either -- exactly one thing is provable about it
    v_line = next(ln for ln in out.splitlines()
                  if f"e{e_raise_v} RAISE" in ln)
    v_verdict = out.splitlines()[out.splitlines().index(v_line) + 1]
    assert "unwound with RuntimeError" in v_verdict
    assert f"e{e_raise_r}" not in v_verdict     # not "raised again"
    # the RuntimeError is swallowed by main, credited to *its* handler
    assert f"SWALLOWED at e{e_hand_r}" in out
    assert f"SWALLOWED at e{e_hand_v}" not in out


def test_exceptions_pairs_repeats_that_share_type_message_and_oid(
        tmp_path, monkeypatch, capsys):
    """A loop whose exception address *is* reused: two raises with an
    identical (type, msg, oid). Each must be credited to its own handler,
    never a neighbour's.

    Fix round 1: the first raise now under-claims. Its handler frame returned,
    but a later RAISE carries its identity, and from the trace alone that is
    either address reuse (what actually happened here) or `return e`
    stored-and-re-raised. Under-claiming on the one is the price of never
    falsely accusing the other; the last raise, with nothing after it, is
    still reported as the swallow it is."""
    w = synthetic(tmp_path, monkeypatch)
    c_boom = w.intern_code("/tmp/prog.py", "boom", 1)
    c_main = w.intern_code("/tmp/prog.py", "main", 5)
    e_call_main = w.add_event(0, 1, "CALL", None, c_main, 5, {"args": {}})
    f_main = w.open_frame(None, c_main, e_call_main, 0, 1)
    exc = exc_payload("ValueError", "same message", 4242)
    handlers = []
    for _ in range(2):
        e_call = w.add_event(0, 1, "CALL", None, c_boom, 1, {"args": {}})
        f_boom = w.open_frame(f_main, c_boom, e_call, 1, 1)
        w.add_event(0, 1, "RAISE", f_boom, c_boom, 2, {"exc": exc})
        w.close_frame(f_boom, None, "unwind", exc)
        handlers.append(
            w.add_event(0, 1, "HANDLED", f_main, c_main, 8, {"exc": exc}))
    e_ret = w.add_event(0, 1, "RETURN", f_main, c_main, None, {"value": None})
    w.close_frame(f_main, e_ret, "return")
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "dispositions: swallowed 1, ambiguous 1" in out
    # each verdict cites its OWN handler -- the collision never lets one
    # raise be explained by the other's HANDLED row
    first, second = handlers
    assert f"handled at e{first} main L8 -- f1 returned normally" in out
    assert f"SWALLOWED at e{second}" in out
    assert f"SWALLOWED at e{first}" not in out


def test_exceptions_same_statement_test_is_the_statement_not_the_frame(
        tmp_path, monkeypatch, capsys):
    """A loop calling a helper that raises: two activations of *one* raise
    statement, so two different frames. The repetition test has to key on the
    source statement (code_id, line) -- keyed on frame_id these look like two
    different statements and the classifier asserts a re-raise that, with the
    address reused, never happened.

    Synthetic because the natural version of this shape does not collide:
    binding the exception across the call keeps each object alive past the
    next allocation. The classifier must not depend on that luck."""
    w = synthetic(tmp_path, monkeypatch)
    c_main = w.intern_code("/tmp/prog.py", "main", 5)
    c_boom = w.intern_code("/tmp/prog.py", "boom", 1)
    e_call_main = w.add_event(0, 1, "CALL", None, c_main, 5, {"args": {}})
    f_main = w.open_frame(None, c_main, e_call_main, 0, 1)
    e = exc_payload("ValueError", "fail", 555)
    raises, handles = [], []
    for _ in range(2):
        e_call = w.add_event(0, 1, "CALL", None, c_boom, 1, {"args": {}})
        f_boom = w.open_frame(f_main, c_boom, e_call, 1, 1)
        # same code object, same line -- one statement, two activations
        raises.append(
            w.add_event(0, 1, "RAISE", f_boom, c_boom, 2, {"exc": e}))
        w.close_frame(f_boom, None, "unwind", e)
        handles.append(
            w.add_event(0, 1, "HANDLED", f_main, c_main, 7, {"exc": e}))
    other = exc_payload("RuntimeError", "gave up", 777)
    w.add_event(0, 1, "RAISE", f_main, c_main, 9, {"exc": other})
    w.close_frame(f_main, None, "unwind", other)   # so rule 2 cannot fire
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 1)
    w.set_meta("uncaught", other)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert f"e{raises[1]} carries the same identity" in out
    assert "raised from the same statement" in out
    assert "then raised again at e" not in out
    assert "re-raised" not in out.splitlines()[-1]


def test_exceptions_will_not_conclude_from_an_incomplete_recording(
        tmp_path, monkeypatch, capsys):
    """No finalize pass means no `uncaught` and no `exit_status`; absence of
    an uncaught record is then not evidence of anything."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc_payload("ValueError", "x", 7)})
    w.set_meta("incomplete", True)              # never finalized
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "SWALLOWED" not in out
    assert "propagated (handler not in traced code)" not in out
    assert "cannot say" in out


def test_exceptions_limit_offers_an_exact_runnable_continuation(
        tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, LOOP_SAME_MESSAGE)
    assert cli.main(["exceptions", run_id, "--limit", "1"]) == 0
    out = capsys.readouterr().out
    assert out.count("SWALLOWED") == 1
    assert "2 more; continue with:" in out
    hint = out.strip().splitlines()[-1].split("continue with: ", 1)[1]
    assert "eN" not in hint
    assert cli.main(shlex.split(hint)[1:]) == 0
    rest = capsys.readouterr().out
    assert rest.count("SWALLOWED") == 1           # --limit 1 also carried
    assert "1 more; continue with:" in rest
    assert "skipped by --after" in rest
    assert "swallowed 2" in rest                  # tally counts all in scope


def test_exceptions_rejects_a_nonpositive_limit(tmp_path, monkeypatch, capsys):
    run_id = record(tmp_path, monkeypatch, SWALLOW)
    assert cli.main(["exceptions", run_id, "--limit", "0"]) == 2
    assert "--limit" in capsys.readouterr().out


# -- the remaining refusal branches ---------------------------------------
def test_exceptions_reports_no_handler_at_all_as_propagated(
        tmp_path, monkeypatch, capsys):
    """No `try` in traced code: the catch happens in the library frame, so
    there is no HANDLED row of any kind to reason from."""
    run_id = record(tmp_path, monkeypatch, RAISE_CAUGHT_UNTRACED,
                    extra=("--exclude", "lib.py"),
                    files=(("lib.py", UNTRACED_LIB_SOURCE),))
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "propagated (handler not in traced code)" in out
    assert "no HANDLED row for it anywhere" in out


def test_exceptions_reraise_with_no_handled_row_says_so(
        tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = exc_payload("ValueError", "boom", 11)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    second = w.add_event(0, 1, "RAISE", f, c, 5, {"exc": exc})
    w.close_frame(f, None, "unwind", exc)
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert f"raised again at e{second}" in out
    # this branch stays a flat assertion, and says why it is sound: an
    # exception still in flight is still referenced, so its address cannot
    # have been handed to a different object
    assert "never stopped propagating in between" in out
    assert "address cannot have been reused" in out
    assert "same statement" not in out
    # pin the tag too -- hedging this branch changes only the tally
    assert "dispositions: re-raised 1" in out


def test_exceptions_will_not_read_a_frame_that_never_closed(
        tmp_path, monkeypatch, capsys):
    """The process died with the handler's frame still on the stack: there
    is no closed_by, so there is no verdict."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = exc_payload("ValueError", "boom", 12)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": exc})
    w.set_meta("incomplete", False)              # frame simply never closed
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert f"f{f} never closed" in out
    assert "cannot say what it did with the exception" in out


def test_exceptions_will_not_read_an_unwind_with_no_captured_exception(
        tmp_path, monkeypatch, capsys):
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = exc_payload("ValueError", "boom", 13)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": exc})
    w.close_frame(f, None, "unwind", None)       # closed, but exc not captured
    w.set_meta("incomplete", False)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "SWALLOWED" not in out
    assert "unwound with no captured exception" in out


def test_exceptions_incomplete_run_will_not_claim_propagation(
        tmp_path, monkeypatch, capsys):
    """The cleanup-HANDLED shape that would read as `propagated` in a
    finished run proves nothing when the recording was cut short."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    exc = exc_payload("ValueError", "boom", 14)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": exc})
    w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": exc})
    w.close_frame(f, None, "unwind", exc)
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "INCOMPLETE" in out
    assert "propagated (handler not in traced code)" not in out
    assert "unresolved" in out
    assert "no finalize pass" in out


def test_exceptions_incomplete_run_with_no_raises_does_not_say_none(
        tmp_path, monkeypatch, capsys):
    """"no exceptions recorded" would be a claim the trace cannot support."""
    w = synthetic(tmp_path, monkeypatch)
    w.set_meta("incomplete", True)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "no exceptions recorded" not in out
    assert "no RAISE events recorded" in out and "INCOMPLETE" in out
