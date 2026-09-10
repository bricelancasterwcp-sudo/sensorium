"""`exceptions` on a TypeScript trace: the four rules that make a CLAIM.

SWALLOWED is the accusation -- an absorbing handler took the failure and
the frame holding it then returned -- and E6-TS gates it, so its guards are
here beside it: the logged catch, the `finally` sink, the two orphan
shapes, the rethrow that keeps the origin's block honest, the unhandled
rejection, and the two ways a failure leaves the traced world. The shapes
that end in "the trace cannot say" live in
`test_exceptions_typescript_ambiguous.py`.

The traces are DATA (`tests/ts_traces.py`), not recordings: what the
transform writes for a given source shape is pinned by the goldens and the
probes, and what these rules make of a given record stream is pinned here.
A test that hand-wrote a `how` and then asserted the verdict it implies is
pinning this module's table, which is the point -- `corpus/typescript` is
where the two halves are made to meet on a real recording.
"""
import ast
import re
from pathlib import Path

from sensorium import cli
from sensorium.exit import ANSWERED, NEGATIVE, UNSETTLED
from tests.helpers import run_cli
from tests.ts_spools import ingest_case, run_ids_in
from tests.ts_traces import (FILE, TS_CAPABILITIES_0_1, call, frame,
                             handled_ev, out, raise_ev, rejection, ret, task,
                             ts_exc, ts_trace, yield_ev)

PARSE_ERR = ts_exc("Error", "not a number: nine", 1)


def swallow_trace(tmp_path, monkeypatch, how="sink_empty_catch", **meta):
    """`loadConfig` calls `parse`, which throws; the `catch` clause absorbs
    it and `loadConfig` returns a default. The one shape reported as a
    swallow, and `corpus/typescript`'s first case."""
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "loadConfig", 15], [FILE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(2, 2, parent=1, depth=1, unwind_exc=PARSE_ERR)],
        events=[
            call(1000, 1, 15, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, PARSE_ERR, task=1),
            handled_ev(4000, 1, 1, 18, PARSE_ERR, how, task=1),
            ret(5000, 1, 1, "{ retries: 3 }", task=1),
        ],
        tasks=[task(1, "a config file is loaded")], **meta)


# -- rule 3: an absorbing handler, and the frame holding it returned --------
def test_an_empty_catch_in_a_frame_that_returned_is_the_one_swallow(
        tmp_path, monkeypatch, capsys):
    run_id = swallow_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (1):" in o, o
    # reported at the RAISE, with the thrown value's own type
    assert "e3 RAISE   parse raise Error('not a number: nine') L10" in o, o
    assert ("SWALLOWED -- caught by sink_empty_catch at e4 (loadConfig L18) "
            "in f1, which returned") in o, o
    assert "dispositions: swallowed 1" in o, o
    # nothing about a birth: this failure was thrown by traced code
    assert "born outside" not in o, o


def test_a_logged_catch_is_a_swallow_because_the_log_is_where_it_went(
        tmp_path, monkeypatch, capsys):
    """`catch (e) { console.error(e) }` -- the transform's `catch`. The
    failure never reached the caller, and the log is where it went (R2's
    logging family). The `how` is what says so; this module never reads a
    source line."""
    run_id = swallow_trace(tmp_path, monkeypatch, how="catch")
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- caught by catch at e4 (loadConfig L18) in f1, "
            "which returned") in o, o
    assert "dispositions: swallowed 1" in o, o


def test_a_finally_that_completed_with_a_throw_in_flight_is_a_swallow(
        tmp_path, monkeypatch, capsys):
    """`try { … } finally { return x }` discards an in-flight throw, and
    `sink_finally_return` is the record of it. In the absorbing set: drop
    it and this test is the one that fails."""
    exc = ts_exc("Error", "disk full", 4)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "save", 30], [FILE, "write", 44]],
        frames=[frame(1, 1, 6),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[
            call(1000, 1, 30, task=1),
            call(2000, 2, 44, task=1, caller=None),
            raise_ev(3000, 2, 2, 46, exc, task=1),
            handled_ev(4000, 1, 1, 34, exc, "sink_finally_return", task=1),
            ret(5000, 1, 1, "true", task=1),
        ],
        tasks=[task(1, "a save completes")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- caught by sink_finally_return at e4 (save L34) in "
            "f1, which returned") in o, o
    assert "dispositions: swallowed 1" in o, o


def test_a_primitive_thrown_and_caught_in_one_frame_pairs_and_is_a_swallow(
        tmp_path, monkeypatch, capsys):
    """A thrown string carries a fresh serial on every record, so identity
    cannot pair these two rows -- §3.1's one admitted pairing does: the
    next HANDLED in the SAME frame carrying equal type and message, with no
    RAISE between. Anything wider is ambiguous, and the sibling suite holds
    those."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "guard", 12]],
        frames=[frame(1, 1, 4)],
        events=[
            call(1000, 1, 12, task=1),
            raise_ev(2000, 1, 1, 14, ts_exc("string", "boom", 8), task=1),
            handled_ev(3000, 1, 1, 15, ts_exc("string", "boom", 9),
                       "sink_empty_catch", task=1),
            ret(4000, 1, 1, "false", task=1),
        ],
        tasks=[task(1, "a guard swallows a string")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- caught by sink_empty_catch at e3 (guard L15) in "
            "f1, which returned") in o, o
    assert "primitive" not in o, o


# -- rule 3: the two orphans -----------------------------------------------
def test_a_handled_no_raise_minted_says_it_was_born_outside_traced_code(
        tmp_path, monkeypatch, capsys):
    """`try { JSON.parse(s) } catch {}` -- the throw happened in a library,
    so no RAISE carries its serial and the HANDLED is the first thing known
    of it. Still a swallow, and the detail says where it came from."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "readJson", 20]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 20, task=1),
            handled_ev(2000, 1, 1, 23,
                       ts_exc("SyntaxError", "Unexpected end of JSON input",
                              12), "sink_empty_catch", task=1),
            ret(3000, 1, 1, "null", task=1),
        ],
        tasks=[task(1, "a bad file is read")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- caught by sink_empty_catch at e2 (readJson L23) in "
            "f1, which returned") in o, o
    assert "born outside traced code, at readJson L23" in o, o
    assert "reject()" not in o, o


def test_a_rejection_no_raise_minted_says_it_was_born_outside_a_throw(
        tmp_path, monkeypatch, capsys):
    """`Promise.reject(v).catch(() => {})` -- a rejection is not a `throw`
    statement, so nothing raised it and `exc.kind` is what says which of
    the two births this was."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "prefetch", 50]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 50, task=1),
            handled_ev(2000, 1, 1, 52,
                       ts_exc("Error", "tile fetch failed", 14,
                              kind="rejection"),
                       "sink_empty_catch_callback", task=1),
            ret(3000, 1, 1, "undefined", task=1),
        ],
        tasks=[task(1, "a prefetch is best effort")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- caught by sink_empty_catch_callback at e2 "
            "(prefetch L52) in f1, which returned") in o, o
    assert "born outside a throw statement (a reject())" in o, o


# -- rule 2: every RAISE keeps its own block and its own tally entry --------
def test_a_rethrow_gives_the_origin_its_hops_and_judges_the_rethrow_on_its_own(
        tmp_path, monkeypatch, capsys):
    """`catch (e) { throw e }` under an outer empty catch. One object, two
    RAISE rows, two blocks: the origin points at what became of the last
    raise and lists the hops, and the rethrow carries the verdict."""
    exc = ts_exc("Error", "boom", 7)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "outer", 5], [FILE, "inner", 20]],
        frames=[frame(1, 1, 7),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc)],
        events=[
            call(1000, 1, 5, task=1),
            call(2000, 2, 20, task=1, caller=None),
            raise_ev(3000, 2, 2, 22, exc, task=1),
            handled_ev(4000, 2, 2, 24, exc, "catch", task=1),
            raise_ev(5000, 2, 2, 25, exc, task=1),
            handled_ev(6000, 1, 1, 7, exc, "sink_empty_catch", task=1),
            ret(7000, 1, 1, "undefined", task=1),
        ],
        tasks=[task(1, "a rethrow reaches the outer catch")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (2):" in o, o
    assert "RE-RAISED -- raised again at e5 (inner L25) → swallowed" in o, o
    assert "hops: e3 (inner L22) → e5 (inner L25)" in o, o
    assert ("SWALLOWED -- caught by sink_empty_catch at e6 (outer L7) in f1, "
            "which returned") in o, o
    # tallies count RAISE events, so they stay comparable line for line
    assert "dispositions: swallowed 1, re-raised 1" in o, o


# -- rule 1: the process itself reported it unhandled -----------------------
def test_a_serial_the_process_reported_unhandled_is_uncaught(
        tmp_path, monkeypatch, capsys):
    exc = ts_exc("Error", "socket hang up", 21, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "connect", 60]],
        frames=[frame(1, 1, unwind_exc=exc)],
        events=[
            call(1000, 1, 60, task=1),
            raise_ev(2000, 1, 1, 62, exc, task=1),
        ],
        tasks=[task(1, "a socket is opened")],
        unhandled_rejections=[rejection("Error", "socket hang up", 21)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "unhandled rejections: 1" in o, o
    assert ("UNCAUGHT -- unhandled rejection; raised at connect L62") in o, o
    assert "dispositions: uncaught 1" in o, o


def test_an_unhandled_rejection_with_no_raise_of_its_own_names_no_site(
        tmp_path, monkeypatch, capsys):
    """A `reject()` mints no RAISE, so the only row carrying its serial is
    a handler's -- and the verdict says the failure has no origin site here
    rather than borrowing the handler's (R1)."""
    exc = ts_exc("Error", "no route", 31, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "route", 70]],
        frames=[frame(1, 1, 3)],
        events=[
            call(1000, 1, 70, task=1),
            handled_ev(2000, 1, 1, 72, exc, "sink_empty_catch_callback",
                       task=1),
            ret(3000, 1, 1, "undefined", task=1),
        ],
        tasks=[task(1, "a route is resolved")],
        unhandled_rejections=[rejection("Error", "no route", 31)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("UNCAUGHT -- unhandled rejection; born outside traced code "
            "(a reject() or a library)") in o, o
    assert "SWALLOWED" not in o, o
    assert "dispositions: uncaught 1" in o, o


# -- rule 4: it left the traced world, and where it left says which --------
def test_a_failed_test_propagates_while_a_sink_beside_it_stays_a_swallow(
        tmp_path, monkeypatch, capsys):
    """Two failures in one recording, and rule 3 runs before rule 4.

    `main` is the test's own root frame -- parentless, `caller: untraced`,
    inside the task -- and it unwound, so the harness got the failure and
    the verdict names the test. `poll` is a callback frame Node entered on
    an empty stack with no test around it; it unwound too, and a
    `.catch(() => {})` in `install` absorbed what it threw. Swap rules 3
    and 4 and the swallow reads PROPAGATED: the swallow's throw ALSO left a
    parentless frame, and only the order says which fact decides.
    """
    fail = ts_exc("AssertionError", "expected 2 to be 3", 41)
    dropped = ts_exc("Error", "tile 7 missing", 42, kind="rejection")
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "main", 3], [FILE, "poll", 40], [FILE, "install", 55]],
        frames=[frame(1, 1, unwind_exc=fail),
                frame(2, 2, unwind_exc=dropped),
                frame(3, 4, 6)],
        events=[
            call(1000, 1, 3, task=1),
            call(2000, 2, 40),
            raise_ev(3000, 2, 2, 42, dropped),
            call(4000, 3, 55),
            handled_ev(5000, 3, 3, 57, dropped, "sink_empty_catch_callback"),
            ret(6000, 3, 3, "undefined"),
            raise_ev(7000, 1, 1, 12, fail, task=1),
        ],
        tasks=[task(1, "config > loads the defaults")])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ("SWALLOWED -- caught by sink_empty_catch_callback at e5 "
            "(install L57) in f3, which returned") in o, o
    assert ('PROPAGATED -- to the harness: test "config > loads the '
            'defaults" failed') in o, o
    assert "dispositions: swallowed 1, propagated 1" in o, o


def test_a_test_whose_title_was_not_a_string_still_names_the_harness(
        tmp_path, monkeypatch, capsys):
    """The harness got the failure whether or not the title could be read,
    so the verdict stands and the name is the one this language's column
    prints for a test with none -- never a blank, and never a guess."""
    exc = ts_exc("AssertionError", "expected 2 to be 3", 43)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "main", 3]],
        frames=[frame(1, 1, unwind_exc=exc)],
        events=[call(1000, 1, 3, task=1), raise_ev(2000, 1, 1, 12, exc,
                                                   task=1)],
        tasks=[task(1, None)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert ('PROPAGATED -- to the harness: test "(unnamed: title not a '
            'string)" failed') in o, o


def test_a_throw_out_of_a_parentless_frame_in_no_test_says_untraced(
        tmp_path, monkeypatch, capsys):
    """A timer callback outside any test: Node entered the frame, Node
    caught what left it, and neither is in this recording."""
    exc = ts_exc("Error", "timer failed", 51)
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "tick", 80]],
        frames=[frame(1, 1, unwind_exc=exc)],
        events=[call(1000, 1, 80), raise_ev(2000, 1, 1, 82, exc)])
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "PROPAGATED -- handler not in traced code" in o, o
    assert "dispositions: propagated 1" in o, o


# -- the capability gate ----------------------------------------------------
def test_a_recorder_that_declares_no_err_flow_refuses_before_any_rule_runs(
        tmp_path, monkeypatch, capsys):
    """A 0.1.x recording wrote these rows and declared no rule read them.
    What it is missing is a RECORD, so the refusal is the capability's --
    the rung-2 sentence naming absent RULES is retired with this module."""
    run_id = swallow_trace(tmp_path, monkeypatch,
                           recorder="sensorium-ts 0.1.0",
                           capabilities=TS_CAPABILITIES_0_1)
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert ("REFUSED: exceptions needs err_flow, which recorder sensorium-ts "
            "0.1.0 declares it does not produce (capabilities.err_flow: "
            "false); nothing was checked") in o, o
    assert "disposition rules" not in o, o
    for absent in ("raised (", "SWALLOWED", "no exceptions recorded"):
        assert absent not in o, o


def test_a_recorded_0_1_0_spool_refuses_with_the_capability_sentence(
        tmp_path):
    """The gate on a real fixture, ingested by the real converter: the ten
    `tests/fixtures/ts-spools` cases are 0.1.0 recordings whose BOOT
    carries no capabilities map at all, which reads `err_flow: false`."""
    spool, sdir, result = ingest_case("async-chain", tmp_path)
    run_id = run_ids_in(result.stdout)[0]
    r = run_cli(["exceptions", run_id], cwd=spool.parent, sensorium_dir=sdir)
    assert r.returncode == 3, f"{r.stdout}{r.stderr}"
    assert ("REFUSED: exceptions needs err_flow, which recorder sensorium-ts "
            "0.1.0 declares it does not produce (capabilities.err_flow: "
            "false); nothing was checked") in r.stdout, r.stdout


# -- the two empty answers --------------------------------------------------
def test_a_finalized_trace_with_no_throw_flow_answers_none(
        tmp_path, monkeypatch, capsys):
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "quiet", 5]],
        frames=[frame(1, 1, 2)],
        events=[call(1000, 1, 5, task=1), ret(2000, 1, 1, "1", task=1)],
        tasks=[task(1, "nothing throws")])
    assert cli.main(["exceptions", run_id]) == NEGATIVE
    assert "no exceptions recorded" in out(capsys)


def test_an_unfinalized_trace_with_no_throw_flow_says_where_it_ended(
        tmp_path, monkeypatch, capsys):
    """Silence on a recording that stopped mid-run is not "none": it is a
    gap, and only a complete recording closes it."""
    run_id = ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "quiet", 5]],
        frames=[frame(1, 1, closed_by=None)],
        events=[call(1000, 1, 5, task=1)],
        tasks=[task(1, "nothing throws yet")], incomplete=True)
    assert cli.main(["exceptions", run_id]) == UNSETTLED
    o = out(capsys)
    assert "INCOMPLETE: this recording never finalized" in o, o
    assert "no RAISE events recorded (see INCOMPLETE above)" in o, o


# -- the tally and the pages ------------------------------------------------
def five_dispositions(tmp_path, monkeypatch):
    """One trace holding every disposition, laid out so that the order they
    are ENCOUNTERED in is not the order they are tallied in: ambiguous
    first, the swallow second from last."""
    esc = ts_exc("Error", "kept", 61)
    left = ts_exc("Error", "timer failed", 62)
    hop = ts_exc("Error", "boom", 63)
    rej = ts_exc("Error", "no route", 64, kind="rejection")
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "escapes", 5], [FILE, "tick", 40], [FILE, "outer", 60],
               [FILE, "inner", 70], [FILE, "connect", 90]],
        frames=[frame(1, 1, 4),                                   # f1
                frame(2, 5, unwind_exc=left),                     # f2
                frame(3, 7, 13),                                  # f3
                frame(4, 8, parent=3, depth=1, unwind_exc=hop),   # f4
                frame(5, 14, unwind_exc=rej)],                    # f5
        events=[
            call(1000, 1, 5, task=1),                             # e1
            raise_ev(1100, 1, 1, 6, esc, task=1),                 # e2
            handled_ev(1200, 1, 1, 8, esc, "catch_escaped", task=1),
            ret(1300, 1, 1, "'kept'", task=1),                    # e4
            call(2000, 2, 40),                                    # e5
            raise_ev(2100, 2, 2, 42, left),                       # e6
            call(3000, 3, 60, task=2),                            # e7
            call(3100, 4, 70, task=2, caller=None),               # e8
            raise_ev(3200, 4, 4, 72, hop, task=2),                # e9
            handled_ev(3300, 4, 4, 74, hop, "catch", task=2),     # e10
            raise_ev(3400, 4, 4, 75, hop, task=2),                # e11
            handled_ev(3500, 3, 3, 62, hop, "sink_empty_catch", task=2),
            ret(3600, 3, 3, "undefined", task=2),                 # e13
            call(4000, 5, 90, task=3),                            # e14
            raise_ev(4100, 5, 5, 92, rej, task=3),                # e15
        ],
        tasks=[task(1, "a value escapes"), task(2, "a rethrow"),
               task(3, "a socket")],
        unhandled_rejections=[rejection("Error", "no route", 64)])


def test_the_tally_prints_in_the_fixed_order_and_not_in_encounter_order(
        tmp_path, monkeypatch, capsys):
    run_id = five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (5):" in o, o
    assert ("dispositions: swallowed 1, uncaught 1, re-raised 1, "
            "propagated 1, ambiguous 1") in o, o
    # encounter order is the reverse-ish of that, so a tally built by
    # first-seen would come out differently
    assert o.index("AMBIGUOUS") < o.index("PROPAGATED") < o.index("UNCAUGHT")


def test_limit_clips_the_page_without_clipping_the_tally(
        tmp_path, monkeypatch, capsys):
    run_id = five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id, "--limit", "2"]) == ANSWERED
    o = out(capsys)
    assert "raised (5):" in o, o
    assert o.count("e2 RAISE") == 1 and "e15 RAISE" not in o, o
    assert ("dispositions: swallowed 1, uncaught 1, re-raised 1, "
            "propagated 1, ambiguous 1") in o, o
    assert ("... 3 more; continue with: sensorium exceptions "
            f"{run_id} --after e6 --limit 2") in o, o


def test_after_skips_the_earlier_raises_and_says_how_many(
        tmp_path, monkeypatch, capsys):
    run_id = five_dispositions(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id, "--after", "e9"]) == ANSWERED
    o = out(capsys)
    assert ("raised (2 of 5; 3 earlier raise(s) skipped by --after e9):"
            in o), o
    assert "dispositions: swallowed 1, uncaught 1" in o, o


# -- the words this recorder does not speak ---------------------------------
#: Every needle E7" greps the transcript for, as WORDS: `Err` inside
#: `TypeError` is the program's own type name and no claim of this module's,
#: which is why the scan is a word-boundary one and not a substring one.
FOREIGN = ("oid", "chain", "Err", "asyncio", "coroutine", "Rust", "Python")

MODULE = (Path(__file__).resolve().parents[1] / "src" / "sensorium" /
          "query" / "exceptions_typescript.py")


def _docstrings(tree) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                ids.add(id(first.value))
    return ids


def test_no_other_language_s_word_can_reach_a_sentence_this_module_prints():
    """A static scan over every string literal the module can PRINT --
    docstrings excluded, because prose about why these rules are not
    Python's is exactly where those words belong, and a reader never sees
    it. E7" greps the transcript; this catches the same thing at the
    source, on shapes no test has built yet."""
    tree = ast.parse(MODULE.read_text())
    skip = _docstrings(tree)
    bad = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in skip):
            for word in FOREIGN:
                if re.search(rf"\b{word}\b", node.value):
                    bad.append((node.lineno, word, node.value[:60]))
    assert not bad, bad
