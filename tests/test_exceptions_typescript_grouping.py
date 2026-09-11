"""The TypeScript shape key is the CLASSIFIER'S parts, not its prose (§3.1).

WHY THE PROSE KEY BROKE, AND WHERE
----------------------------------
`exceptions_group` keyed a shape on `(tag, site, masked verdict, route)`,
and the masked verdict is the sentence the rules PRINT -- which names the
handler's frame. The mask turns `e412` into `e#` and `f204` into `f#`, but
it deliberately leaves `f16`, `f32`, `f64` and `f128` alone (R-G8: those are
Rust's float TYPE names, and masking them merged two verdicts naming
different types). On the rung-2 lens invocation that guard split one
place three ways: three throws absorbed by ONE `catch` in `useAiAssist`,
in frames 32, 128 and 174, printed as three blocks saying the same thing
about the same line. The reader's table had to put them back together by
hand, which is the work the grouper exists to have already done.

So the TypeScript renderer keys on `(disposition, reason, the site the
verdict is about, the verdict's own words under a mask that exempts
NOTHING, the route where the verdict names no site)`. The SENTENCE stays
because the components alone cannot tell a `→ swallowed` rethrow from a
`→ propagated` one, nor two propagations naming two different failing
tests. The ORIGIN enters only through `site_of`'s fallback, as rung 2's
key and R-G2 had it: a sink keyed on the places that reached it is the
split the hand-built table had to undo, and §3.2 says how a shape reports
what its key ignored -- `origins: N distinct`.

Rust keeps the masked-prose key verbatim
(design R3, decision P6): its nineteen fenced tests and two acceptance
records are the fence, and `test_the_rust_key_is_todays_tuple_verbatim`
below states it as a tuple equality so a rewrite of `_rust_key` fails here
rather than in a record nobody re-reads.

WHAT THE KEY STILL SEPARATES
----------------------------
Everything the old key separated: two sinks that print the
same words in different FILES stay two shapes (R-G12), and two dispositions
or two reasons at one site stay apart. The traces below are DATA
(`tests/ts_traces.py`), so each states one grouping question and nothing
else.
"""
from dataclasses import replace

from sensorium import cli, paths
from sensorium.exit import ANSWERED
from sensorium.query import exceptions_rust, exceptions_typescript
from sensorium.query.exceptions_cmd import Disposition
from sensorium.query.exceptions_group import (RUST, TYPESCRIPT, _masked,
                                              group_chains, group_units, mask,
                                              site_of, ts_mask, vary_lines)
from sensorium.store.reader import Trace
from tests.test_exceptions_invocation import CARGO
from tests.test_exceptions_invocation import INV as RUST_INV
from tests.test_exceptions_invocation import M1 as RUST_M1
from tests.test_exceptions_invocation import M2 as RUST_M2
from tests.test_exceptions_invocation import escaped_trace as rust_member
from tests.test_exceptions_rust_grouping import (escaped_trace,
                                                 repeat_sink_trace)
from tests.ts_traces import (FILE, call, frame, handled_ev, out, raise_ev,
                             ret, task, ts_exc, ts_trace)

#: The lens's own shape: one React hook catching what its render threw.
HOOK = "/w/app/src/hooks/useAiAssist.ts"

#: Two `loadConfig`s that print one site text and are two places.
APP = "/w/app/src/config.ts"
VENDOR = "/w/app/vendor/legacy-config.ts"
PARSE = "/w/app/src/parse.ts"


def _trace(run_id) -> Trace:
    return Trace.open(paths.find_trace(run_id))


def hook_trace(tmp_path, monkeypatch, *, handlers=(32, 128, 174)):
    """`useAiAssist` catches at L56 what `renderPanel` threw at L12, once
    per entry of `handlers` -- and the entry is the id of the frame that
    caught it, which is the ONLY thing the three units differ in.

    The filler frames between them are open frames of the thrower's code
    that no event names: a real worker opens hundreds before the one that
    matters, and the ids this test is about are those ids.

    Event ids, per unit i (0-based): e(5i+1) CALL useAiAssist, e(5i+2) CALL
    renderPanel, e(5i+3) RAISE (the unit's ORIGIN), e(5i+4) HANDLED (the
    sink), e(5i+5) RETURN. So the origins are e3, e8, e13.
    """
    frames, events = [], []
    for i, fid in enumerate(handlers):
        while len(frames) < fid - 1:
            # Never closed and named by nothing: only its id is the point.
            frames.append(frame(2, 1))
        exc = ts_exc("Error", "assist unavailable", i + 1)
        base, ts = 5 * i, 1000 * (5 * i + 1)
        frames.append(frame(1, base + 1, base + 5))
        frames.append(frame(2, base + 2, parent=fid, depth=1,
                            unwind_exc=exc))
        events += [
            call(ts, 1, 40, task=1),
            call(ts + 100, 2, 8, task=1, caller=None),
            raise_ev(ts + 200, fid + 1, 2, 12, exc, task=1),
            handled_ev(ts + 300, fid, 1, 56, exc, "catch", task=1),
            ret(ts + 400, fid, 1, "null", task=1),
        ]
    return ts_trace(tmp_path, monkeypatch,
                    codes=[[HOOK, "useAiAssist", 40],
                           [HOOK, "renderPanel", 8]],
                    frames=frames, events=events,
                    tasks=[task(1, "the assist panel renders")])


def two_files_trace(tmp_path, monkeypatch):
    """Two `loadConfig`s, one per file, each sinking at L18 what the SAME
    `parse` threw: one printed site text, two places, two shapes (R-G12).

    Event ids: e1 CALL loadConfig (app), e2 CALL parse, e3 RAISE, e4
    HANDLED, e5 RETURN; e6-e10 the same in the vendored copy.
    """
    bad = [ts_exc("Error", "bad json", 1), ts_exc("Error", "bad json", 2)]
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[APP, "loadConfig", 15], [VENDOR, "loadConfig", 15],
               [PARSE, "parse", 8]],
        frames=[frame(1, 1, 5),
                frame(3, 2, parent=1, depth=1, unwind_exc=bad[0]),
                frame(2, 6, 10),
                frame(3, 7, parent=3, depth=1, unwind_exc=bad[1])],
        events=[
            call(1000, 1, 15, task=1),
            call(2000, 3, 8, task=1, caller=None),
            raise_ev(3000, 2, 3, 10, bad[0], task=1),
            handled_ev(4000, 1, 1, 18, bad[0], "catch", task=1),
            ret(5000, 1, 1, "{}", task=1),
            call(6000, 2, 15, task=1),
            call(7000, 3, 8, task=1, caller=None),
            raise_ev(8000, 4, 3, 10, bad[1], task=1),
            handled_ev(9000, 3, 2, 18, bad[1], "catch", task=1),
            ret(10000, 3, 2, "{}", task=1),
        ],
        tasks=[task(1, "a config file is loaded")])


def one_parent_trace(tmp_path, monkeypatch, *, second=9):
    """Two `Bomb` frames throw under ONE `renderWithBoundary`, and untraced
    code catches both: the untraced-catcher reason's site is the parent's
    code object (P3), and the two sentences differ only in the frame id
    they name -- so they are one shape once the mask has done its work.

    The second thrower's frame id is the caller's choice: `f9` masks under
    any reading, `f16` is one of the four `MASK` exempts as a Rust float
    type name, and this recorder's mask exempts nothing.

    Event ids: e1 CALL renderWithBoundary, e2 CALL Bomb, e3 RAISE, e4 CALL
    Bomb, e5 RAISE, e6 RETURN.
    """
    boom = [ts_exc("Error", "render failed", 1), ts_exc("Error",
                                                        "render failed", 2)]
    frames = [frame(1, 1, 6),
              frame(2, 2, parent=1, depth=1, unwind_exc=boom[0])]
    while len(frames) < second - 1:
        frames.append(frame(2, 1))
    frames.append(frame(2, 4, parent=1, depth=1, unwind_exc=boom[1]))
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "renderWithBoundary", 20], [FILE, "Bomb", 8]],
        frames=frames,
        events=[
            call(1000, 1, 20, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 12, boom[0], task=1),
            call(4000, 2, 8, task=1, caller=None),
            raise_ev(5000, second, 2, 12, boom[1], task=1),
            ret(6000, 1, 1, "null", task=1),
        ],
        tasks=[task(1, "the panel renders")])


def rethrown_trace(tmp_path, monkeypatch):
    """One `boom` line, one `bubble` line, two throws -- and the two
    rethrows END differently: the first is absorbed by a `catch` in a
    `runCase` that returned, the second leaves a `runCase` that unwound.

    Every component of the two RE-RAISED units is equal (tag, no reason,
    the same origin site both as the site and as the origin); the last
    word of the sentence is the whole of the difference.

    Event ids: e1 CALL runCase, e2 CALL bubble, e3 CALL boom, e4 RAISE
    (origin), e5 RAISE (the rethrow), e6 HANDLED, e7 RETURN; then e8-e12
    the same without the handler or the return.
    """
    exc = [ts_exc("Error", "kaboom", 1), ts_exc("Error", "kaboom", 2)]
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "runCase", 20], [FILE, "bubble", 30],
               [FILE, "boom", 8]],
        frames=[frame(1, 1, 7),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc[0]),
                frame(3, 3, parent=2, depth=2, unwind_exc=exc[0]),
                frame(1, 8, parent=None, depth=0, unwind_exc=exc[1]),
                frame(2, 9, parent=4, depth=1, unwind_exc=exc[1]),
                frame(3, 10, parent=5, depth=2, unwind_exc=exc[1])],
        events=[
            call(1000, 1, 20, task=1),
            call(2000, 2, 30, task=1, caller=None),
            call(3000, 3, 8, task=1, caller=None),
            raise_ev(4000, 3, 3, 10, exc[0], task=1),
            raise_ev(5000, 2, 2, 34, exc[0], task=1),
            handled_ev(6000, 1, 1, 24, exc[0], "catch", task=1),
            ret(7000, 1, 1, "null", task=1),
            call(8000, 1, 20, task=1),
            call(9000, 2, 30, task=1, caller=None),
            call(10000, 3, 8, task=1, caller=None),
            raise_ev(11000, 6, 3, 10, exc[1], task=1),
            raise_ev(12000, 5, 2, 34, exc[1], task=1),
        ],
        tasks=[task(1, "a case runs")])


def two_tests_trace(tmp_path, monkeypatch):
    """The same `boom` line throws in two TESTS, and both failures reach
    the harness. One origin site, one disposition, no reason -- and two
    verdicts, because a PROPAGATED sentence names the test that failed.

    Event ids: e1 CALL runCase, e2 CALL boom, e3 RAISE; e4-e6 the same in
    the second test.
    """
    exc = [ts_exc("Error", "kaboom", 1), ts_exc("Error", "kaboom", 2)]
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "runCase", 20], [FILE, "boom", 8]],
        frames=[frame(1, 1, parent=None, depth=0, unwind_exc=exc[0]),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc[0]),
                frame(1, 4, parent=None, depth=0, unwind_exc=exc[1]),
                frame(2, 5, parent=3, depth=1, unwind_exc=exc[1])],
        events=[
            call(1000, 1, 20, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, exc[0], task=1),
            call(4000, 1, 20, task=2),
            call(5000, 2, 8, task=2, caller=None),
            raise_ev(6000, 4, 2, 10, exc[1], task=2),
        ],
        tasks=[task(1, "loads a config"), task(2, "rejects a bad config")])


def dispatch_trace(tmp_path, monkeypatch):
    """The `createHooks.dispatch` shape: ONE `catch` at one line absorbing
    throws from TWO different hooks. Same sink, same words, two origins --
    which the key ignores and `origins: 2 distinct` reports (§3.2).

    Event ids: e1 CALL dispatch, e2 CALL useA, e3 RAISE, e4 HANDLED,
    e5 CALL useB, e6 RAISE, e7 HANDLED, e8 RETURN.
    """
    exc = [ts_exc("Error", "hook failed", 1),
           ts_exc("Error", "hook failed", 2)]
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "createHooks.dispatch", 90], [FILE, "useA", 8],
               [FILE, "useB", 18]],
        frames=[frame(1, 1, 8),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc[0]),
                frame(3, 5, parent=1, depth=1, unwind_exc=exc[1])],
        events=[
            call(1000, 1, 90, task=1),
            call(2000, 2, 8, task=1, caller=None),
            raise_ev(3000, 2, 2, 10, exc[0], task=1),
            handled_ev(4000, 1, 1, 98, exc[0], "catch", task=1),
            call(5000, 3, 18, task=1, caller=None),
            raise_ev(6000, 3, 3, 20, exc[1], task=1),
            handled_ev(7000, 1, 1, 98, exc[1], "catch", task=1),
            ret(8000, 1, 1, "undefined", task=1),
        ],
        tasks=[task(1, "the hooks run")])


def two_routes_trace(tmp_path, monkeypatch):
    """One `boom L10`, one `bubble L34`, two throws -- and one of them
    takes a longer way home, through `relay L50`.

    Both origin units are RE-RAISED, name the same rethrow site, end in
    the same word and share an origin: every component is equal and the
    ROUTE is the whole of the difference. A verdict that names no site is
    exactly where R-G2 puts the route into the key.

    Event ids: e1-e7 the short way (CALL runCase, CALL bubble, CALL boom,
    RAISE, RAISE, HANDLED, RETURN); e8-e16 the long one, with relay
    between runCase and bubble and a third RAISE.
    """
    exc = [ts_exc("Error", "kaboom", 1), ts_exc("Error", "kaboom", 2)]
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "runCase", 20], [FILE, "bubble", 30],
               [FILE, "boom", 8], [FILE, "relay", 44]],
        frames=[frame(1, 1, 7),
                frame(2, 2, parent=1, depth=1, unwind_exc=exc[0]),
                frame(3, 3, parent=2, depth=2, unwind_exc=exc[0]),
                frame(1, 8, 16),
                frame(4, 9, parent=4, depth=1, unwind_exc=exc[1]),
                frame(2, 10, parent=5, depth=2, unwind_exc=exc[1]),
                frame(3, 11, parent=6, depth=3, unwind_exc=exc[1])],
        events=[
            call(1000, 1, 20, task=1),
            call(2000, 2, 30, task=1, caller=None),
            call(3000, 3, 8, task=1, caller=None),
            raise_ev(4000, 3, 3, 10, exc[0], task=1),
            raise_ev(5000, 2, 2, 34, exc[0], task=1),
            handled_ev(6000, 1, 1, 24, exc[0], "catch", task=1),
            ret(7000, 1, 1, "null", task=1),
            call(8000, 1, 20, task=1),
            call(9000, 4, 44, task=1, caller=None),
            call(10000, 2, 30, task=1, caller=None),
            call(11000, 3, 8, task=1, caller=None),
            raise_ev(12000, 7, 3, 10, exc[1], task=1),
            raise_ev(13000, 6, 2, 34, exc[1], task=1),
            raise_ev(14000, 5, 4, 50, exc[1], task=1),
            handled_ev(15000, 4, 1, 24, exc[1], "catch", task=1),
            ret(16000, 4, 1, "null", task=1),
        ],
        tasks=[task(1, "a case runs")])


# -- (a) the ids that defeated the mask -------------------------------------
def test_one_sink_in_three_frames_is_one_shape(tmp_path, monkeypatch, capsys):
    """Three throws, one `catch`, one line: ONE block counting three.

    What used to split them is stated here rather than described: the mask
    leaves `f32` and `f128` alone, so the three sentences were three
    different strings about one place.
    """
    assert mask("f32 f128 f174") == "f32 f128 f#"
    assert ts_mask("f32 f128 f174") == "f# f# f#"
    run_id = hook_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert "raised (3):" in o, o
    assert o.count("SWALLOWED --") == 1, o
    assert ("    SWALLOWED -- caught by catch at e4 (useAiAssist L56) in "
            "f32, which returned  [×3: e3, e8, e13]") in o, o
    assert "dispositions: swallowed 3" in o, o
    # the key looked at the site and the origin, and those agree, so
    # nothing is flagged as varying either
    assert "origins:" not in o and "messages:" not in o, o


def test_the_typescript_key_is_the_classifier_s_five_parts(
        tmp_path, monkeypatch):
    """`(disposition, reason, site, masked verdict, route)` -- the
    components AND the sentence, under a mask that exempts nothing, with
    the route present only where the verdict names no site (§3.1 as
    amended 2026-09-11, twice). Stated as a tuple so a dropped component,
    an added one or a reordering fails here rather than in a re-read.

    These three swallows NAME their sink, so the route is `None` and the
    origin is nowhere in the key -- which is what keeps a sink from being
    split by the places that reached it (§3.2)."""
    run_id = hook_trace(tmp_path, monkeypatch)
    trace = _trace(run_id)
    idx = exceptions_typescript.Index(trace)
    keys = set()
    for unit in idx.units:
        d = exceptions_typescript.classify(trace, unit, idx)
        keys.add(TYPESCRIPT.key(trace, unit, d,
                                site_of(trace, unit, d, TYPESCRIPT),
                                _masked(TYPESCRIPT.hops_line(trace, unit),
                                        TYPESCRIPT.mask)))
    assert keys == {("swallowed", None, (HOOK, 56, "useAiAssist"),
                     "SWALLOWED -- caught by catch at e# (useAiAssist L56) "
                     "in f#, which returned", None)}, keys


# -- (b) one site text, two places ------------------------------------------
def test_two_places_that_print_one_site_text_stay_two_shapes(
        tmp_path, monkeypatch, capsys):
    """The masked sentences are identical and the origins are one `parse`:
    the FILE is the whole of what tells these apart, and dropping the site
    from the key would merge them (R-G12)."""
    run_id = two_files_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("SWALLOWED --") == 2, o
    assert "[×" not in o, o
    assert ("SWALLOWED -- caught by catch at e4 (loadConfig L18 in "
            "config.ts) in f1, which returned") in o, o
    assert ("SWALLOWED -- caught by catch at e9 (loadConfig L18 in "
            "legacy-config.ts) in f3, which returned") in o, o
    assert "dispositions: swallowed 2" in o, o


# -- (c)/(i) the untraced catcher groups on the parent ----------------------
def test_two_untraced_catcher_units_under_one_parent_are_one_shape(
        tmp_path, monkeypatch, capsys):
    """The reason's site is the parent's code object, so the shape is the
    PLACE the untraced catcher sits in -- and the two sentences, which
    differ only in the frame id each names, mask to one string.

    Run twice, because the ids are the point: `f9` masks under any
    reading, and `f16` is one of the four `MASK` exempts as a Rust float
    type name. Both are frame ids on this wire and both must mask.
    """
    for i, (second, tmp) in enumerate([(9, tmp_path / "a"),
                                       (16, tmp_path / "b")]):
        run_id = one_parent_trace(tmp, monkeypatch, second=second)
        assert cli.main(["exceptions", run_id]) == ANSWERED
        o = out(capsys)
        assert o.count("AMBIGUOUS --") == 1, (second, o)
        assert ("    AMBIGUOUS -- caught by untraced code inside "
                "renderWithBoundary (config.ts): f2 unwound, its caller f1 "
                "returned; not followed  [×2: e3, e5]") in o, (second, o)
        assert "dispositions: ambiguous 2" in o, (second, o)
        assert "ambiguous by reason: untraced catcher 2" in o, (second, o)


# -- (g)/(h) what the sentence carries and no component does ----------------
def test_two_rethrows_from_one_origin_that_ended_differently_are_two_shapes(
        tmp_path, monkeypatch, capsys):
    """A RE-RAISED verdict points at what became of the LAST raise, and
    that word is not a component of the key: same tag, no reason, one
    origin site, one rethrow site. Merging them would print `→ swallowed`
    over a bracket counting a throw that reached the harness."""
    run_id = rethrown_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("RE-RAISED --") == 2, o
    assert ("RE-RAISED -- raised again at e5 (bubble L34) → swallowed"
            ) in o, o
    assert ("RE-RAISED -- raised again at e12 (bubble L34) → propagated"
            ) in o, o
    assert "[×" not in o, o
    assert "dispositions: swallowed 1, re-raised 2, propagated 1" in o, o


def test_two_propagations_from_one_origin_naming_two_tests_are_two_shapes(
        tmp_path, monkeypatch, capsys):
    """A PROPAGATED verdict names the test that failed and carries no site
    of its own, so every component of these two is equal. The test NAME is
    the whole of the difference, and it is the fact the reader came for."""
    run_id = two_tests_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("PROPAGATED --") == 2, o
    assert ('PROPAGATED -- to the harness: test "loads a config" failed'
            ) in o, o
    assert ('PROPAGATED -- to the harness: test "rejects a bad config" '
            'failed') in o, o
    assert "[×" not in o, o
    assert "dispositions: propagated 2" in o, o


def test_the_grouper_counts_the_reasons_it_already_classified(
        tmp_path, monkeypatch):
    """The tally by reason comes from `group_units`, which classifies every
    unit once; a second pass over the units to count them again is what
    Task 1 shipped as an interim and Task 2 removes."""
    run_id = one_parent_trace(tmp_path, monkeypatch)
    trace = _trace(run_id)
    idx = exceptions_typescript.Index(trace)
    shapes, tally, reasons = group_units(trace, idx.units, idx,
                                         exceptions_typescript.classify,
                                         TYPESCRIPT)
    assert len(shapes) == 1, shapes
    assert tally == {"ambiguous": 2}, tally
    assert reasons == {"untraced catcher": 2}, reasons


# -- (d) the Rust fence -----------------------------------------------------
def test_the_rust_key_is_todays_tuple_verbatim(tmp_path, monkeypatch):
    """`(tag, site, masked verdict, route)`, exactly as it was before the
    renderer had a `key` field at all (P6).

    Written as an equality against the literal rather than as prose: this
    is the one statement that keeps every Rust answer, vector, corpus case
    and acceptance record byte-identical, and a mutant that drops `mask`
    or the route clause has to fail a test that spells them out.
    """
    run_id = repeat_sink_trace(tmp_path, monkeypatch, repeats=2)
    trace = _trace(run_id)
    idx = exceptions_rust.Index(trace)
    seen = 0
    for unit in idx.chains:
        d = exceptions_rust.classify(trace, unit, idx)
        site = site_of(trace, unit, d, RUST)
        hops = _masked(RUST.hops_line(trace, unit), RUST.mask)
        assert RUST.key(trace, unit, d, site, hops) == (
            d.tag, site, mask(d.verdict), hops if d.site is None else None)
        # the masked verdict is not the verdict: a key that forgot to mask
        # would still satisfy the line above on a sentence carrying no id
        assert mask(d.verdict) != d.verdict, d.verdict
        seen += 1
    assert seen == 2, seen


def test_group_chains_still_returns_two_values(tmp_path, monkeypatch):
    """Every Rust caller unpacks two, and the third value is the
    invocation mode's alone (P5)."""
    run_id = repeat_sink_trace(tmp_path, monkeypatch, repeats=2)
    trace = _trace(run_id)
    idx = exceptions_rust.Index(trace)
    result = group_chains(trace, idx.chains, idx, exceptions_rust.classify)
    assert len(result) == 2, result
    shapes, tally = result
    assert len(shapes) == 1 and tally == {"swallowed": 2}, (shapes, tally)


def test_a_rust_ambiguous_chain_is_counted_under_no_reason(
        tmp_path, monkeypatch, capsys):
    """Rust dispositions carry no `reason` -- the field is TypeScript's --
    so the dict is empty even where the TAG is ambiguous, and no Rust
    answer grows a line. Counting by tag instead of by reason would print
    one, which is a byte moved in an answer two records quote."""
    run_id = escaped_trace(tmp_path, monkeypatch, origins=[2, 3])
    trace = _trace(run_id)
    idx = exceptions_rust.Index(trace)
    _shapes, tally, reasons = group_units(trace, idx.chains, idx,
                                          exceptions_rust.classify, RUST)
    assert tally.get("ambiguous") == 2, tally
    assert reasons == {}, reasons
    assert cli.main(["exceptions", run_id]) == ANSWERED
    assert "ambiguous by reason:" not in out(capsys)


# -- (j) one sink, two origins, and the line that says so -------------------
def test_one_sink_reached_from_two_origins_is_one_shape_that_says_so(
        tmp_path, monkeypatch, capsys):
    """The key holds the SINK, not the places that reached it.

    This is the `createHooks.dispatch L98` shape of the rung-2 lens, and
    two of its siblings (`useBuilderContent.<anonymous> L72` with three
    origins, `GuardedButton.<anonymous> L29` with two) read the same way.
    An unconditional origin component would split all three -- 32 printed
    places where the pre-registration locks 28 -- and §3.2 already says
    what a shape does with an origin its key ignored: it flags it.
    """
    run_id = dispatch_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("SWALLOWED --") == 1, o
    assert ("    SWALLOWED -- caught by catch at e4 (createHooks.dispatch "
            "L98) in f1, which returned  [×2: e3, e6]") in o, o
    assert "      origins: 2 distinct (first shown)" in o, o
    # one message, so the only thing flagged is the thing that differs
    assert "messages:" not in o, o
    assert "dispositions: swallowed 2" in o, o


# -- (k) the route joins where the verdict names no site (R-G2) -------------
def test_two_rethrows_that_travelled_differently_are_two_shapes(
        tmp_path, monkeypatch, capsys):
    """A RE-RAISED verdict names no site of its own, so the unit's ORIGIN
    is what it is keyed by -- and there the recorded journey is the
    information the reader came for, which is R-G2's rule and now
    TypeScript's too. These two share an origin, a rethrow site and a
    last word; one of them went through `relay L50` and the other did
    not."""
    run_id = two_routes_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("RE-RAISED --") == 3, o
    # no bracket on either: the line ends where the verdict does
    assert ("    RE-RAISED -- raised again at e5 (bubble L34) → swallowed\n"
            ) in o, o
    assert ("    RE-RAISED -- raised again at e13 (bubble L34) → swallowed\n"
            ) in o, o
    assert "      hops: e4 (boom L10) → e5 (bubble L34)\n" in o, o
    assert ("      hops: e12 (boom L10) → e13 (bubble L34) → "
            "e14 (relay L50)\n") in o, o
    assert "dispositions: swallowed 2, re-raised 3" in o, o


# -- (l) the vary sets mask by the language's own rule ----------------------
def test_the_vary_sets_mask_with_the_language_s_own_mask(
        tmp_path, monkeypatch):
    """`Shape.hops` and `Shape.details` are compared under `render.mask`,
    not under whichever mask this module imported first.

    NO TypeScript sentence carries a frame id in its ROUTE or its DETAIL
    today: the hops line names event ids only, and the two details this
    recorder writes name none. So the renderer and the classifier here are
    stubs standing in for the first sentence that does -- what is fenced is
    the CALL SITE. Masked by Rust's rule, two routes differing only in
    `f32` and `f33` are two shapes, because `f32` is one of the four
    spellings `MASK` spares for Rust's float types; masked by this
    language's, they are one, and nothing is reported as varying.
    """
    run_id = two_tests_trace(tmp_path, monkeypatch)
    trace = _trace(run_id)
    idx = exceptions_typescript.Index(trace)
    frames = {u.origin.id: 32 + i for i, u in enumerate(idx.units)}
    assert sorted(frames.values()) == [32, 33], frames

    def hops_line(_trace_, unit):
        return ("hops: e1 (boom L10) → e2 (drain L7) in "
                f"f{frames[unit.origin.id]}")

    def classify(_trace_, unit, _idx_):
        return Disposition(
            "ambiguous", "AMBIGUOUS -- one sentence",
            f"the handler's frame f{frames[unit.origin.id]} had not closed",
            reason="suspended")

    render = replace(TYPESCRIPT, hops_line=hops_line)
    shapes, tally, reasons = group_units(trace, idx.units, idx, classify,
                                         render)
    assert len(shapes) == 1, [s.key for s in shapes]
    assert vary_lines(shapes[0]) == [], vary_lines(shapes[0])
    assert tally == {"ambiguous": 2} and reasons == {"suspended": 2}


# -- (M3) a Rust invocation grows no reason line ----------------------------
def test_a_rust_invocation_with_ambiguities_prints_no_reason_line(
        tmp_path, monkeypatch, capsys):
    """The whole way through, not just at the grouper: two Rust members,
    two ambiguous chains, and no `ambiguous by reason:` line -- because a
    Rust disposition carries no reason and the summed dict stays empty.
    The Rust half of the invocation suite is the byte fence; this is the
    one sentence of it about a line only TypeScript can print."""
    rust_member(tmp_path, monkeypatch, fn="alpha", line=18, run_id=RUST_M1,
                invocation=RUST_INV, cargo_args=CARGO)
    rust_member(tmp_path, monkeypatch, fn="beta", line=28, run_id=RUST_M2,
                invocation=RUST_INV, cargo_args=CARGO)
    assert cli.main(["exceptions", RUST_INV]) == ANSWERED
    o = out(capsys)
    assert "dispositions: ambiguous 2" in o, o
    assert "ambiguous by reason:" not in o, o
