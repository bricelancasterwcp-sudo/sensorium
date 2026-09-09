"""`exceptions` over synthetic traces -- shapes CPython will not reproduce.

The other half of `test_exceptions`, split at that file's own
`# -- exceptions: synthetic traces for shapes CPython will not reproduce`
banner on 2026-09-08 to bring both halves under the 800-line ceiling, as
`test_exception_identity` was split off it before. Nothing here records a
real program: each trace is written by hand because the shape it carries --
a recycled address, a frame that never closed, an unwind with no captured
exception -- is one a real run cannot be made to produce on demand.
"""
import shlex

from sensorium.exit import UNSETTLED
from sensorium import cli
from tests.helpers import finalize_synthetic
from tests.programs import (LOOP_SAME_MESSAGE, RAISE_CAUGHT_UNTRACED, SWALLOW,
                            UNTRACED_LIB_SOURCE, exc_payload, record,
                            synthetic)


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
    finalize_synthetic(w)
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
    finalize_synthetic(w)
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
    finalize_synthetic(w)
    w.set_meta("exit_status", 1)
    w.set_meta("uncaught", other)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert f"e{raises[1]} carries the same identity" in out
    assert "raised from the same statement" in out
    assert "then raised again at e" not in out
    assert "re-raised" not in out.splitlines()[-1]


def test_exceptions_legacy_trace_still_reports_a_different_statement_reraise(
        tmp_path, monkeypatch, capsys):
    """The other half of the legacy heuristic: a repeat from a *different*
    statement is still reported outright, so an old trace does not lose every
    re-raise verdict it used to have."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    e = exc_payload("ValueError", "boom", 22)          # no serial
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": e})
    h = w.add_event(0, 1, "HANDLED", f, c, 4, {"exc": e})
    second = w.add_event(0, 1, "RAISE", f, c, 6, {"exc": e})   # other line
    w.close_frame(f, None, "unwind", e)
    finalize_synthetic(w)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "LEGACY TRACE" in out
    assert f"handled at e{h} risky L4, then raised again at e{second}" in out
    assert "same statement" not in out
    assert "re-raised 1" in out


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
    """With serials, two RAISE rows sharing an identity ARE one object, and
    the absence of a HANDLED row between them is reported as what it is: no
    record of what caught it, not a proof that nothing did."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    e = exc_payload("ValueError", "boom", 11, serial=3)
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": e})
    second = w.add_event(0, 1, "RAISE", f, c, 5, {"exc": e})
    w.close_frame(f, None, "unwind", e)
    finalize_synthetic(w)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert f"raised again at e{second}" in out
    assert "the trace cannot say what caught it" in out
    assert "dispositions: re-raised 1" in out
    assert "LEGACY TRACE" not in out


def test_exceptions_legacy_trace_hedges_a_repeat_with_no_handled_row(
        tmp_path, monkeypatch, capsys):
    """The same rows without serials. This is the shape that disproved round
    2's soundness argument, so on a legacy trace it must hedge and name the
    reason -- an untraced handler frees an exception without leaving a
    HANDLED row."""
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "risky", 1)
    e_call = w.add_event(0, 1, "CALL", None, c, 1, {"args": {}})
    f = w.open_frame(None, c, e_call, 0, 1)
    e = exc_payload("ValueError", "boom", 11)          # no serial
    w.add_event(0, 1, "RAISE", f, c, 3, {"exc": e})
    second = w.add_event(0, 1, "RAISE", f, c, 5, {"exc": e})
    w.close_frame(f, None, "unwind", e)
    finalize_synthetic(w)
    w.set_meta("exit_status", 0)
    w.set_meta("uncaught", None)
    w.close()

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == 0
    out = capsys.readouterr().out
    assert "LEGACY TRACE" in out
    assert "re-record" in out
    assert f"e{second} carries the same type/message/oid" in out
    # no verdict line may assert a re-raise (the phrase appears only inside
    # the hedge's own explanation of the two possibilities)
    verdicts = [ln for ln in out.splitlines() if ln.startswith("    ")
                and not ln.startswith("      ")]
    assert not any("raised again" in ln for ln in verdicts), verdicts
    assert "handler in untraced code" in out
    assert "dispositions: propagated 1, ambiguous 1" in out


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
    finalize_synthetic(w)                        # frame simply never closed
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
    finalize_synthetic(w)
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

    assert cli.main(["exceptions", "20260101-000000-abcdef"]) == UNSETTLED
    out = capsys.readouterr().out
    assert "no exceptions recorded" not in out
    assert "no RAISE events recorded" in out and "INCOMPLETE" in out
