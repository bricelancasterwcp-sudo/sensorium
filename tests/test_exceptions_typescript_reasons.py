"""The reason an AMBIGUOUS TypeScript verdict carries, and the table of them.

Rung 2 left seventeen blocks reading "no rule of this recorder reaches a
verdict here", and a reader who counts them cannot tell one shape from
another. Most of them are ONE footprint: a throw that unwound every traced
frame it was in while the frame ABOVE went on, with no handler row
anywhere -- `expect(() => parse('x')).toThrow()`, a rejection an assertion
took, an error boundary rendering a fallback. Untraced code caught it, and
naming that is not a claim about what the untraced code DID with it, which
is why the word stays AMBIGUOUS (design section 2.1).

So every ambiguous sentence this module prints now carries a REASON KEY,
the tally by reason prints under `dispositions:`, and this file is where
the keys and the table are pinned. `test_exceptions_typescript_window.py`
holds rule 4's window; the shapes and their sentences are in
`test_exceptions_typescript_ambiguous.py`, and the accusation in
`test_exceptions_typescript.py`.
"""
import ast
import inspect

from sensorium import cli, paths
from sensorium.exit import ANSWERED
from sensorium.query import exceptions_typescript as rules
from sensorium.query.exceptions_typescript import (REASON_ORDER, Index,
                                                   classify)
from sensorium.store.reader import Trace
from tests.ts_traces import (FILE, call, frame, handled_ev, out, raise_ev,
                             rejection, ret, task, ts_exc, ts_trace,
                             yield_ev)

BOOM = ts_exc("Error", "boom", 1)


def dispositions(run_id) -> list:
    """Every unit's Disposition, in origin order, read through the rules
    rather than off the page: a reason KEY is never printed, and a test
    that read it out of a sentence would be pinning the sentence twice."""
    trace = Trace.open(paths.find_trace(run_id))
    idx = Index(trace)
    return [classify(trace, u, idx) for u in idx.units]


def test_a_throw_caught_by_untraced_code_inside_a_traced_frame_is_named(
        tmp_path, monkeypatch, capsys):
    """`expect(() => parse('x')).toThrow()`: parse unwinds, the arrow unwinds,
    the test frame returns, no handler row anywhere."""
    exc = ts_exc("FormulaError", "Unknown function 'sqrt'", 9)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "formula > rejects sqrt", 30],
               [FILE, "<anonymous>", 37], [FILE, "parse", 80]],
        frames=[frame(1, 1, 6),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc),
                frame(3, 3, parent=2, depth=2, unwind_exc=exc)],
        events=[call(1000, 1, 30, task=1), call(2000, 2, 37, task=1),
                call(3000, 3, 80, task=1),
                raise_ev(4000, 3, 3, 86, exc, task=1),
                ret(6000, 1, 1, task=1)],
        tasks=[task(1, "formula > rejects sqrt")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside "
            "formula > rejects sqrt (config.ts): f2 unwound, its caller f1 "
            "returned; not followed") in o, o
    assert "dispositions: ambiguous 1" in o, o
    assert "ambiguous by reason: untraced catcher 1" in o, o
    assert "no rule of this recorder" not in o, o


def test_a_caller_that_never_closed_says_that_rather_than_that_it_returned(
        tmp_path, monkeypatch, capsys):
    """The caller is still on the stack where the recording stops. It went
    on in the only sense the wire supports -- it did not unwind with this
    failure -- and saying "returned" about it would be a fact nobody
    recorded."""
    run_id = ts_trace(
        tmp_path / "open", monkeypatch,
        codes=[[FILE, "boot", 5], [FILE, "load", 20]],
        frames=[frame(1, 1),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                raise_ev(3000, 2, 2, 22, BOOM, task=1)],
        tasks=[task(1, "boot > loads")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside boot (config.ts): "
            "f2 unwound, its caller f1 had not closed at the end of the "
            "recording; not followed") in o, o
    assert "ambiguous by reason: untraced catcher 1" in o, o


def test_a_caller_that_later_unwound_with_another_failure_says_both_readings(
        tmp_path, monkeypatch, capsys):
    """The untraced code may have translated this failure into that one, or
    the caller may have failed later for its own reasons. Nothing on the
    wire tells them apart, so the sentence says so."""
    later = ts_exc("Error", "later", 2)
    run_id = ts_trace(
        tmp_path / "later", monkeypatch,
        codes=[[FILE, "render", 5], [FILE, "draw", 20]],
        frames=[frame(1, 1, unwind_exc=later),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                raise_ev(3000, 2, 2, 22, BOOM, task=1)],
        tasks=[task(1, "render > draws")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside render "
            "(config.ts): f2 unwound, its caller f1 later unwound with "
            "Error('later'): a translation by untraced code, or a later "
            "failure, indistinguishable") in o, o
    assert "ambiguous by reason: untraced catcher 1" in o, o


def test_a_rejection_reads_the_same_sentence_as_a_throw(
        tmp_path, monkeypatch, capsys):
    """`exc.kind` says how the failure was MINTED, and the footprint is
    about where it went: an `await` whose rejection no traced code took
    reads exactly as a `throw` that nothing traced took."""
    exc = ts_exc("Error", "tile 7 missing", 71, kind="rejection")
    run_id = ts_trace(
        tmp_path / "rejection", monkeypatch,
        codes=[[FILE, "fog > renders every tile", 5], [FILE, "poll", 40]],
        frames=[frame(1, 1, 4),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 40, task=1),
                raise_ev(3000, 2, 2, 42, exc, task=1),
                ret(4000, 1, 1, task=1)],
        tasks=[task(1, "fog > renders every tile")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside "
            "fog > renders every tile (config.ts): f2 unwound, its caller "
            "f1 returned; not followed") in o, o
    assert "ambiguous by reason: untraced catcher 1" in o, o


def test_a_handler_row_in_the_window_keeps_the_reason_out(
        tmp_path, monkeypatch, capsys):
    """The footprint is "no traced code took it". A handler row for this
    serial in this unit's own window says traced code DID, and then the
    sentence a reader needs is the one about that handler's frame -- not a
    claim about untraced code that the recording contradicts."""
    run_id = ts_trace(
        tmp_path / "handled", monkeypatch,
        codes=[[FILE, "boot", 5], [FILE, "wrap", 20], [FILE, "read", 40]],
        frames=[frame(1, 1, 6),
                frame(2, 2, parent=1, depth=1, closed_by=None),
                frame(3, 3, parent=2, depth=2, unwind_exc=BOOM)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                call(3000, 3, 40, task=1),
                raise_ev(4000, 3, 3, 42, BOOM, task=1),
                handled_ev(5000, 2, 2, 24, BOOM, "catch", task=1),
                ret(6000, 1, 1, task=1)],
        tasks=[task(1, "boot > reads")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- the handler's frame f2 had not closed at the end "
            "of the recording") in o, o
    assert "caught by untraced code" not in o, o
    assert "ambiguous by reason: suspended 1" in o, o


def test_an_unhandled_rejection_is_still_uncaught_and_never_the_reason(
        tmp_path, monkeypatch, capsys):
    """Rule 1 owns a rejection the process itself reported unhandled: the
    runtime SAW where it ended, and a reason saying untraced code caught it
    would contradict the one witness there is."""
    exc = ts_exc("Error", "tile 7 missing", 7, kind="rejection")
    run_id = ts_trace(
        tmp_path / "unhandled", monkeypatch,
        codes=[[FILE, "boot", 5], [FILE, "poll", 40]],
        frames=[frame(1, 1, 4),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 40, task=1),
                raise_ev(3000, 2, 2, 42, exc, task=1),
                ret(4000, 1, 1, task=1)],
        tasks=[task(1, "fog > renders every tile")],
        unhandled_rejections=[rejection("Error", "tile 7 missing", 7)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "UNCAUGHT -- unhandled rejection; raised at poll L42" in o, o
    assert "caught by untraced code" not in o, o
    assert "ambiguous by reason:" not in o, o


def test_the_frame_named_is_the_outermost_one_the_failure_left(
        tmp_path, monkeypatch, capsys):
    """One traced frame deep: the frame the throw left IS the frame it was
    raised in, and `f<child>` names that one. The parent is the caller,
    never the raise's own frame -- a reason whose two ids were the same
    would be saying the failure was caught where it was thrown."""
    run_id = ts_trace(
        tmp_path / "single", monkeypatch,
        codes=[[FILE, "config > rejects nine", 5], [FILE, "parse", 20]],
        frames=[frame(1, 1, 4),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                raise_ev(3000, 2, 2, 22, BOOM, task=1),
                ret(4000, 1, 1, task=1)],
        tasks=[task(1, "config > rejects nine")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("AMBIGUOUS -- caught by untraced code inside "
            "config > rejects nine (config.ts): f2 unwound, its caller f1 "
            "returned; not followed") in o, o


# -- the reason table -------------------------------------------------------
def _escaped(tmp_path, monkeypatch):
    """`catch (e) { return String(e) }`: the binding left the clause."""
    return ts_trace(
        tmp_path / "escaped", monkeypatch,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 15, task=1), call(2000, 2, 8, task=1),
                raise_ev(3000, 2, 2, 10, BOOM, task=1),
                handled_ev(4000, 1, 1, 18, BOOM, "catch_escaped", task=1),
                ret(5000, 1, 1, task=1)],
        tasks=[task(1, "config > loads")])


def _untraced_catcher(tmp_path, monkeypatch):
    """The footprint section 2.1 names."""
    return ts_trace(
        tmp_path / "untraced", monkeypatch,
        codes=[[FILE, "config > rejects nine", 5], [FILE, "parse", 20]],
        frames=[frame(1, 1, 4),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 5, task=1), call(2000, 2, 20, task=1),
                raise_ev(3000, 2, 2, 22, BOOM, task=1),
                ret(4000, 1, 1, task=1)],
        tasks=[task(1, "config > rejects nine")])


def _suspended(tmp_path, monkeypatch):
    """`.catch(async () => …)` still parked where the recording stops."""
    exc = ts_exc("Error", "tile 7 missing", 71, kind="rejection")
    return ts_trace(
        tmp_path / "suspended", monkeypatch,
        codes=[[FILE, "poll", 40], [FILE, "retry", 60]],
        frames=[frame(1, 1, unwind_exc=exc),
                frame(2, 3, closed_by=None, kind="coroutine")],
        events=[call(1000, 1, 40), raise_ev(2000, 1, 1, 42, exc),
                call(3000, 2, 60),
                handled_ev(4000, 2, 2, 62, exc, "sink_empty_catch_callback"),
                yield_ev(5000, 2, 2)])


def _translated(tmp_path, monkeypatch):
    """`catch (e) { throw new Wrapped(e) }`: the handler's frame left by
    throwing a DIFFERENT serial."""
    wrapped = ts_exc("ConfigError", "wrapped: boom", 9)
    return ts_trace(
        tmp_path / "translated", monkeypatch,
        codes=[[FILE, "wrap", 10], [FILE, "inner", 30]],
        frames=[frame(1, 1, unwind_exc=wrapped),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 10, task=1),
                call(2000, 2, 30, task=1, caller=None),
                raise_ev(3000, 2, 2, 32, BOOM, task=1),
                handled_ev(4000, 1, 1, 14, BOOM, "catch", task=1),
                raise_ev(5000, 1, 1, 15, wrapped, task=1)],
        tasks=[task(1, "a failure is translated")])


def _primitive(tmp_path, monkeypatch):
    """`throw 'nope'` twice: no row of either can be attached to the other."""
    first = ts_exc("string", "nope", 1)
    second = ts_exc("string", "nope", 2)
    return ts_trace(
        tmp_path / "primitive", monkeypatch,
        codes=[[FILE, "validate", 10]],
        frames=[frame(1, 1, unwind_exc=first),
                frame(1, 3, unwind_exc=second)],
        events=[call(1000, 1, 10, task=1),
                raise_ev(2000, 1, 1, 12, first, task=1),
                call(3000, 1, 10, task=1),
                raise_ev(4000, 2, 1, 12, second, task=1)],
        tasks=[task(1, "validate > refuses")])


def _orphan(tmp_path, monkeypatch):
    """A `.catch(fn)` row no RAISE minted, in a frame that then unwound
    with the very failure it took: no rule reaches a verdict, and the unit
    is still an orphan."""
    return ts_trace(
        tmp_path / "orphan", monkeypatch,
        codes=[[FILE, "then", 10]],
        frames=[frame(1, 1, unwind_exc=BOOM)],
        events=[call(1000, 1, 10, task=1),
                handled_ev(2000, 1, 1, 12, BOOM, "catch_callback", task=1)],
        tasks=[task(1, "a route is resolved")])


def _incomplete(tmp_path, monkeypatch):
    """The cut is the reason there is no evidence."""
    return ts_trace(
        tmp_path / "incomplete", monkeypatch,
        codes=[[FILE, "load", 10]],
        frames=[frame(1, 1, closed_by=None)],
        events=[call(1000, 1, 10, task=1),
                raise_ev(2000, 1, 1, 12, BOOM, task=1)],
        tasks=[task(1, "a load is cut short")], incomplete=True)


def _unnamed(tmp_path, monkeypatch):
    """A handler took it and its frame then left with the SAME failure:
    not a swallow, not a translation, not still open, and no untraced
    catcher above -- rule 5's catch-all, which is the number this rung is
    measured on."""
    return ts_trace(
        tmp_path / "unnamed", monkeypatch,
        codes=[[FILE, "wrap", 10], [FILE, "inner", 30]],
        frames=[frame(1, 1, unwind_exc=BOOM),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 10, task=1), call(2000, 2, 30, task=1),
                raise_ev(3000, 2, 2, 32, BOOM, task=1),
                handled_ev(4000, 1, 1, 14, BOOM, "catch", task=1)],
        tasks=[task(1, "a failure vanishes")])


#: One builder per reason, so the table below is driven rather than
#: asserted about: a key added to `REASON_ORDER` with no shape that
#: produces it fails here, and a shape whose key is not in `REASON_ORDER`
#: fails too.
REASON_SHAPES = (
    ("escaped", _escaped),
    ("untraced catcher", _untraced_catcher),
    ("suspended", _suspended),
    ("translated", _translated),
    ("primitive", _primitive),
    ("orphan", _orphan),
    ("incomplete", _incomplete),
    ("unnamed", _unnamed),
)


def _ambiguous_calls(module) -> list:
    """Every `Disposition("ambiguous", …)` the module's source contains.

    Read as SYNTAX, not as text: a regex over the source would pass the
    moment somebody reflowed an argument list, and what this has to
    establish is that no ambiguous verdict anywhere in the module is
    constructed without a reason.
    """
    tree = ast.parse(inspect.getsource(module))
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and getattr(n.func, "id", None) == "Disposition"
            and n.args and isinstance(n.args[0], ast.Constant)
            and n.args[0].value == "ambiguous"]


def test_every_reason_the_module_prints_has_a_key(tmp_path, monkeypatch):
    """Each branch of rule 5, driven by a hand-built trace, and the source
    walked for an ambiguous verdict nobody tagged.

    Two halves because neither alone is enough: driving the branches proves
    the keys that exist are the ones `REASON_ORDER` names, and walking the
    source proves the next branch somebody writes cannot print an untagged
    reason that the tally would then silently drop.
    """
    for key, build in REASON_SHAPES:
        run_id = build(tmp_path, monkeypatch)
        ds = [d for d in dispositions(run_id) if d.tag == "ambiguous"]
        assert ds, key
        for d in ds:
            assert d.reason in REASON_ORDER, (key, d)
        assert key in {d.reason for d in ds}, (key, [d.reason for d in ds])

    keys: set = set()
    for call_node in _ambiguous_calls(rules):
        kw = next((k for k in call_node.keywords if k.arg == "reason"), None)
        assert kw is not None, ast.unparse(call_node)
        # Every string under the keyword, because one construction carries
        # two keys: the catch-all is `orphan` or `unnamed` by P2.
        keys |= {n.value for n in ast.walk(kw.value)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert keys == set(REASON_ORDER), sorted(keys)


def test_the_reason_line_is_absent_where_nothing_is_ambiguous(
        tmp_path, monkeypatch, capsys):
    """A tally of nothing is noise. The `dispositions:` line is rung 2's,
    byte for byte, and the reason line only exists where there is a reason
    to print."""
    run_id = ts_trace(
        tmp_path / "swallow", monkeypatch,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=BOOM)],
        events=[call(1000, 1, 15, task=1), call(2000, 2, 8, task=1),
                raise_ev(3000, 2, 2, 10, BOOM, task=1),
                handled_ev(4000, 1, 1, 18, BOOM, "catch", task=1),
                ret(5000, 1, 1, task=1)],
        tasks=[task(1, "config > loads")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "dispositions: swallowed 1" in o, o
    assert "ambiguous by reason:" not in o, o


#: The line the trace below must print, and the two lines it must not.
#: `REASON_ORDER` is `escaped, untraced catcher, suspended, …`; the units
#: are built so that INSERTION order (origin order: suspended, escaped,
#: untraced catcher) and ALPHABETICAL order (escaped, suspended, untraced
#: catcher) both differ from it and from each other. Without a third unit
#: all three orders agree, and `for r in sorted(reasons)` or `for r in
#: reasons` would print a passing answer.
IN_TABLE_ORDER = "ambiguous by reason: escaped 1, untraced catcher 1, suspended 1"
IN_ALPHABETICAL_ORDER = (
    "ambiguous by reason: escaped 1, suspended 1, untraced catcher 1")
IN_INSERTION_ORDER = (
    "ambiguous by reason: suspended 1, escaped 1, untraced catcher 1")


def test_the_keys_print_in_the_tables_order_with_the_zeros_left_out(
        tmp_path, monkeypatch, capsys):
    """One suspended unit, one escaped unit and one untraced-catcher unit:
    three keys in `REASON_ORDER`, and none of the five that counted nothing.

    §2.3 fixes the ORDER so two answers are comparable key by key, which is
    a claim only three keys can fence: the line is pinned whole, and the
    two orders a plausible mutation would produce are pinned absent.
    """
    pending = ts_exc("Error", "tile 7 missing", 3, kind="rejection")
    other = ts_exc("Error", "no such tile", 2)
    run_id = ts_trace(
        tmp_path / "three", monkeypatch,
        codes=[[FILE, "poll", 40], [FILE, "retry", 60],
               [FILE, "loadConfig", 15], [FILE, "parse", 8],
               [FILE, "boot", 30], [FILE, "read", 40]],
        frames=[frame(1, 1, unwind_exc=pending),
                frame(2, 3, closed_by=None, kind="coroutine"),
                frame(3, 6, 10),
                frame(4, 7, parent=3, depth=1, unwind_exc=BOOM),
                frame(5, 11, 14),
                frame(6, 12, parent=5, depth=1, unwind_exc=other)],
        events=[call(1000, 1, 40, task=1),
                raise_ev(2000, 1, 1, 42, pending, task=1),
                call(3000, 2, 60, task=1),
                handled_ev(4000, 2, 2, 62, pending,
                           "sink_empty_catch_callback", task=1),
                yield_ev(5000, 2, 2, task=1),
                call(6000, 3, 15, task=1), call(7000, 4, 8, task=1),
                raise_ev(8000, 4, 4, 10, BOOM, task=1),
                handled_ev(9000, 3, 3, 18, BOOM, "catch_escaped", task=1),
                ret(10000, 3, 3, task=1),
                call(11000, 5, 30, task=1), call(12000, 6, 40, task=1),
                raise_ev(13000, 6, 6, 42, other, task=1),
                ret(14000, 5, 5, task=1)],
        tasks=[task(1, "config > loads")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "dispositions: ambiguous 3" in o, o
    # A WHOLE line, so a fourth key appended to it is a failure too.
    assert IN_TABLE_ORDER in o.splitlines(), o
    assert IN_ALPHABETICAL_ORDER not in o, o
    assert IN_INSERTION_ORDER not in o, o
