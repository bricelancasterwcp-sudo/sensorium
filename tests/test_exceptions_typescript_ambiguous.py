"""`exceptions` on a TypeScript trace: every shape that ends in "the trace
cannot say", and the reason each one prints.

AMBIGUOUS is the default (R8), and every one of these is a place a rule
COULD have reached SWALLOWED by falling through -- an escaped binding, a
handler defined elsewhere, a handler frame that never finished, a handler
frame that then failed for its own reasons, a primitive with no identity,
a recording that stopped mid-run. Each has its own sentence, because
"ambiguous" with no reason is a verdict a reader cannot act on.

The accusation and its guards are in `test_exceptions_typescript.py`.
"""
from sensorium import cli
from sensorium.exit import ANSWERED
from tests.ts_traces import (FILE, call, frame, handled_ev, out, raise_ev,
                             ret, task, ts_exc, ts_trace, yield_ev)

BOOM = ts_exc("Error", "boom", 1)


def escape_trace(tmp_path, monkeypatch, how):
    """`loadConfig` catches what `parse` threw and lets it -- or a
    rendering of it -- out of the clause: `return String(e)`,
    `expect(e.message)`, `seen.push(e)`, `.catch(handler)`. The frame
    RETURNED, which is the swallow's other half, and the escape is what
    keeps it from being one."""
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[
            call(1000, 1, 15, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, BOOM, task=1),
            handled_ev(4000, 1, 1, 18, BOOM, how, task=1),
            ret(5000, 1, 1, "'Error: boom'", task=1),
        ],
        tasks=[task(1, "a config file is loaded")])


def test_a_catch_whose_binding_escaped_is_never_a_swallow(
        tmp_path, monkeypatch, capsys):
    """The rung-3 STOP, transferred: `catch (e) { return String(e) }` read
    SWALLOWED while the rendering reached every caller. The frame returned
    and the failure still left it, so the verdict says so and follows it no
    further."""
    run_id = escape_trace(tmp_path, monkeypatch, "catch_escaped")
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught at e4 (catch_escaped), and the error or a "
            "rendering of it left the handler; not followed") in o, o
    assert "SWALLOWED" not in o, o
    assert "dispositions: ambiguous 1" in o, o


def test_a_handler_defined_elsewhere_is_opaque_and_never_accused(
        tmp_path, monkeypatch, capsys):
    """`.catch(handler)` -- whether the named function swallows is not the
    splice's to say (R4), so it is not this module's either."""
    run_id = escape_trace(tmp_path, monkeypatch, "catch_callback_opaque")
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught at e4 (catch_callback_opaque), and the "
            "error or a rendering of it left the handler; not followed"
            ) in o, o
    assert "SWALLOWED" not in o, o


def test_an_absorbing_handler_beside_an_escaping_one_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """R8's conjunction: one rejection reached two handlers -- an empty
    `.catch(() => {})` on the promise and a `catch (e) { seen.push(e) }`
    around the await. The absorbing one alone would read SWALLOWED; with
    an escaping one anywhere for the same serial, it does not.

    Drop the escaping half of rule 3 and this is the test that fails.
    """
    exc = ts_exc("Error", "tile 7 missing", 5, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "prefetch", 20], [FILE, "render", 40]],
        frames=[frame(1, 1, 3), frame(2, 4, 6)],
        events=[
            call(1000, 1, 20, task=1),
            handled_ev(2000, 1, 1, 22, exc, "sink_empty_catch_callback",
                       task=1),
            ret(3000, 1, 1, "undefined", task=1),
            call(4000, 2, 40, task=1, caller=None),
            handled_ev(5000, 2, 2, 44, exc, "catch_escaped", task=1),
            ret(6000, 2, 2, "'failed'", task=1),
        ],
        tasks=[task(1, "a tile is prefetched")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught at e5 (catch_escaped), and the error or a "
            "rendering of it left the handler; not followed") in o, o
    assert "SWALLOWED" not in o, o


def test_a_handler_frame_still_suspended_at_the_end_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """`catch { await retry() }` parked at the end of the recording: the
    clause absorbed the failure and the frame has not returned, so what it
    does next is not on the wire. Rule 3 needs a frame that RETURNED."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 10], [FILE, "fetch", 30]],
        frames=[frame(1, 1, closed_by=None, kind="coroutine"),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[
            call(1000, 1, 10, task=1),
            call(2000, 2, 30, task=1, caller=None),
            raise_ev(3000, 2, 2, 32, BOOM, task=1),
            handled_ev(4000, 1, 1, 14, BOOM, "catch", task=1),
            yield_ev(5000, 1, 1, task=1),
        ],
        tasks=[task(1, "a load retries")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- the handler's frame f1 is still suspended at the "
            "end of the recording") in o, o
    assert "SWALLOWED" not in o, o


def test_a_handler_frame_that_never_closed_at_all_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """The same rule with no suspension recorded: the frame is simply open
    where the recording stops, and "which returned" would be an invention."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 10], [FILE, "fetch", 30]],
        frames=[frame(1, 1, closed_by=None),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[
            call(1000, 1, 10, task=1),
            call(2000, 2, 30, task=1, caller=None),
            raise_ev(3000, 2, 2, 32, BOOM, task=1),
            handled_ev(4000, 1, 1, 14, BOOM, "catch", task=1),
        ],
        tasks=[task(1, "a load hangs")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- the handler's frame f1 had not closed at the end "
            "of the recording") in o, o
    assert "SWALLOWED" not in o, o


def test_a_parked_callback_handler_beats_the_frame_the_throw_unwound(
        tmp_path, monkeypatch, capsys):
    """`.catch(async () => …)` still parked where the recording stops, over
    a throw that left a frame Node entered on an empty stack.

    Both facts are on the wire and only one of them is a verdict. The
    frame below unwinding says where the failure WENT; the handler row says
    traced code TOOK it, and its frame has not finished. Rule 4 would have
    said "handler not in traced code" about a recording that holds the
    handler -- so rule 4 declines while any absorbing handler for the
    serial is still open (design section 3.3's conjunct), and the reason
    printed is the suspension.
    """
    exc = ts_exc("Error", "tile 7 missing", 71, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "poll", 40], [FILE, "retry", 60]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 3, closed_by=None, kind="coroutine")],
        events=[
            call(1000, 1, 40),
            raise_ev(2000, 1, 1, 42, exc),
            call(3000, 2, 60),
            handled_ev(4000, 2, 2, 62, exc, "sink_empty_catch_callback"),
            yield_ev(5000, 2, 2),
        ])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- the handler's frame f2 is still suspended at the "
            "end of the recording") in o, o
    assert "SWALLOWED" not in o, o
    assert "PROPAGATED" not in o, o
    assert "dispositions: ambiguous 1" in o, o


def test_a_handler_still_open_beats_the_test_root_the_throw_unwound(
        tmp_path, monkeypatch, capsys):
    """The same conjunct where the frame that unwound is the TEST's own
    root: without it the verdict reads `to the harness: test "..." failed`
    about a failure a handler in this recording took, which is the same
    false claim wearing the harness's name.
    """
    exc = ts_exc("Error", "tile 7 missing", 72, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "main", 3], [FILE, "retry", 60]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 3, closed_by=None)],
        events=[
            call(1000, 1, 3, task=1),
            raise_ev(2000, 1, 1, 12, exc, task=1),
            call(3000, 2, 60, task=1),
            handled_ev(4000, 2, 2, 62, exc, "catch_callback", task=1),
        ],
        tasks=[task(1, "fog > renders every tile")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- the handler's frame f2 had not closed at the end "
            "of the recording") in o, o
    assert "SWALLOWED" not in o, o
    assert "PROPAGATED" not in o, o
    assert "dispositions: ambiguous 1" in o, o


def test_a_handler_frame_that_later_unwound_with_another_failure_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """`catch (e) { throw new Wrapped(e) }`: the clause absorbed one
    failure and the frame left by throwing a different one. A translation
    or a later failure -- the recording cannot tell them apart -- and the
    wrapper's own raise is judged on its own."""
    wrapped = ts_exc("ConfigError", "wrapped: boom", 9)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "wrap", 10], [FILE, "inner", 30]],
        frames=[frame(1, 1, unwind_exc=wrapped),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[
            call(1000, 1, 10, task=1),
            call(2000, 2, 30, task=1, caller=None),
            raise_ev(3000, 2, 2, 32, BOOM, task=1),
            handled_ev(4000, 1, 1, 14, BOOM, "catch", task=1),
            raise_ev(5000, 1, 1, 15, wrapped, task=1),
        ],
        tasks=[task(1, "a failure is translated")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- handler's frame f1 later unwound with "
            "ConfigError('wrapped: boom'): a translation or a later "
            "failure, indistinguishable") in o, o
    assert "SWALLOWED" not in o, o
    # the wrapper is its own raise, and it left the test's root frame
    assert ('PROPAGATED -- to the harness: test "a failure is translated" '
            'failed') in o, o
    assert "dispositions: propagated 1, ambiguous 1" in o, o


def test_a_rethrown_primitive_has_no_identity_and_every_row_of_it_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """`catch (e) { throw e }` on a thrown string. Every record carries a
    fresh serial, so the two raises cannot be linked and the outer catch's
    row cannot be attached to either -- and none of the three is called a
    swallow on the strength of matching text (R11)."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "outer", 5], [FILE, "guard", 20]],
        frames=[frame(1, 1, 7),
                frame(2, 2, parent=1, depth=1,
                      unwind_exc=ts_exc("string", "boom", 3))],
        events=[
            call(1000, 1, 5, task=1),
            call(2000, 2, 20, task=1, caller=None),
            raise_ev(3000, 2, 2, 22, ts_exc("string", "boom", 1), task=1),
            handled_ev(4000, 2, 2, 23, ts_exc("string", "boom", 2), "catch",
                       task=1),
            raise_ev(5000, 2, 2, 24, ts_exc("string", "boom", 3), task=1),
            handled_ev(6000, 1, 1, 7, ts_exc("string", "boom", 4),
                       "sink_empty_catch", task=1),
            ret(7000, 1, 1, "undefined", task=1),
        ],
        tasks=[task(1, "a string is rethrown")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("AMBIGUOUS -- a primitive carries no identity: two "
                   "records with this text may be one throw rethrown or "
                   "two throws; not followed") == 3, o
    assert "SWALLOWED" not in o, o
    assert "dispositions: ambiguous 3" in o, o


def test_an_orphan_handler_that_let_the_error_escape_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """A rejection born outside a `throw` statement whose handler bound it
    and let it out: neither where it came from nor where it went is on the
    wire, and the verdict claims neither."""
    exc = ts_exc("Error", "no route", 11, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "route", 40]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 40, task=1),
            handled_ev(2000, 1, 1, 42, exc, "catch_callback_escaped",
                       task=1),
            ret(3000, 1, 1, "null", task=1),
        ],
        tasks=[task(1, "a route is resolved")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught at e2 (catch_callback_escaped), and the "
            "error or a rendering of it left the handler; not followed"
            ) in o, o
    assert "SWALLOWED" not in o, o


def test_a_recording_that_never_finalized_says_that_instead_of_guessing(
        tmp_path, monkeypatch, capsys):
    """The cut is the reason there is no evidence, and naming it is the
    difference between "nothing handled this" and "the recording stopped
    before anything could"."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "load", 10]],
        frames=[frame(1, 1, closed_by=None)],
        events=[call(1000, 1, 10, task=1),
                raise_ev(2000, 1, 1, 12, BOOM, task=1)],
        tasks=[task(1, "a load is cut short")], incomplete=True)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "INCOMPLETE: this recording never finalized" in o, o
    assert "AMBIGUOUS -- this recording never finalized (INCOMPLETE)" in o, o
    assert "dispositions: ambiguous 1" in o, o


def test_a_failure_that_left_an_inner_frame_names_the_untraced_catcher(
        tmp_path, monkeypatch, capsys):
    """A failure that left an inner frame and never appeared again: the
    caller closed normally, nothing recorded handling it, and the frame it
    left is not one the harness owns. Falling through to a swallow here is
    exactly what these rules refuse to do.

    RE-PINNED by rung 3: this recording IS the untraced-catcher footprint
    (design §2.1) -- `outer` went on after `inner` unwound, and no handler
    row for the serial exists anywhere -- so the sentence now names the
    footprint instead of the rule table's silence. The verdict word is
    unchanged and so is the refusal below it: naming where a failure was
    caught claims nothing about what the catcher did with it. The
    catch-all it used to print is still reachable and is driven in
    `tests/test_exceptions_typescript_reasons.py`.
    """
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "outer", 5], [FILE, "inner", 20]],
        frames=[frame(1, 1, 4),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[
            call(1000, 1, 5, task=1),
            call(2000, 2, 20, task=1, caller=None),
            raise_ev(3000, 2, 2, 22, BOOM, task=1),
            ret(4000, 1, 1, "undefined", task=1),
        ],
        tasks=[task(1, "an inner failure vanishes")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside outer "
            "(config.ts): f2 unwound, its caller f1 returned; not followed"
            ) in o, o
    assert "ambiguous by reason: untraced catcher 1" in o, o
    assert "SWALLOWED" not in o, o
