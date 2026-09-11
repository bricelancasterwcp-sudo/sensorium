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

So the TypeScript renderer keys on what the classifier DECIDED --
`(disposition, reason, the site the verdict is about, the origin's site)`
-- and reads no sentence at all. Rust keeps the masked-prose key verbatim
(design R3, decision P6): its nineteen fenced tests and two acceptance
records are the fence, and `test_the_rust_key_is_todays_tuple_verbatim`
below states it as a tuple equality so a rewrite of `_rust_key` fails here
rather than in a record nobody re-reads.

WHAT THE KEY STILL SEPARATES
----------------------------
Everything the old key separated except the prose: two sinks that print the
same words in different FILES stay two shapes (R-G12), and two dispositions
or two reasons at one site stay apart. The traces below are DATA
(`tests/ts_traces.py`), so each states one grouping question and nothing
else.
"""
from sensorium import cli, paths
from sensorium.exit import ANSWERED
from sensorium.query import exceptions_rust, exceptions_typescript
from sensorium.query.exceptions_group import (RUST, TYPESCRIPT, _masked,
                                              group_chains, group_units, mask,
                                              site_of)
from sensorium.store.reader import Trace
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


def one_parent_trace(tmp_path, monkeypatch):
    """Two `Bomb` frames throw under ONE `renderWithBoundary`, and untraced
    code catches both: the untraced-catcher reason's site is the parent's
    code object (P3), so the two are one shape.

    The throwers are f2 and f16 -- `f16` is a float type name the mask
    leaves alone, which is exactly what split them before.

    Event ids: e1 CALL renderWithBoundary, e2 CALL Bomb, e3 RAISE, e4 CALL
    Bomb, e5 RAISE, e6 RETURN.
    """
    boom = [ts_exc("Error", "render failed", 1), ts_exc("Error",
                                                        "render failed", 2)]
    frames = [frame(1, 1, 6),
              frame(2, 2, parent=1, depth=1, unwind_exc=boom[0])]
    while len(frames) < 15:
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
            raise_ev(5000, 16, 2, 12, boom[1], task=1),
            ret(6000, 1, 1, "null", task=1),
        ],
        tasks=[task(1, "the panel renders")])


# -- (a) the ids that defeated the mask -------------------------------------
def test_one_sink_in_three_frames_is_one_shape(tmp_path, monkeypatch, capsys):
    """Three throws, one `catch`, one line: ONE block counting three.

    What used to split them is stated here rather than described: the mask
    leaves `f32` and `f128` alone, so the three sentences were three
    different strings about one place.
    """
    assert mask("f32 f128 f174") == "f32 f128 f#"
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


def test_the_typescript_key_is_the_classifier_s_four_parts(
        tmp_path, monkeypatch):
    """`(disposition, reason, site, origin site)` -- no prose, no mask, no
    route (§3.1). Stated as a tuple so a fifth component or a reordering
    fails here."""
    run_id = hook_trace(tmp_path, monkeypatch)
    trace = _trace(run_id)
    idx = exceptions_typescript.Index(trace)
    keys = set()
    for unit in idx.units:
        d = exceptions_typescript.classify(trace, unit, idx)
        keys.add(TYPESCRIPT.key(trace, unit, d,
                                site_of(trace, unit, d, TYPESCRIPT),
                                _masked(TYPESCRIPT.hops_line(trace, unit))))
    assert keys == {("swallowed", None, (HOOK, 56, "useAiAssist"),
                     (HOOK, 12, "renderPanel"))}, keys


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


# -- (c) the untraced catcher groups on the parent --------------------------
def test_two_untraced_catcher_units_under_one_parent_are_one_shape(
        tmp_path, monkeypatch, capsys):
    """The reason's site is the parent's code object, so the shape is the
    PLACE the untraced catcher sits in -- and the tally by reason counts
    both units, from the grouper's own pass."""
    run_id = one_parent_trace(tmp_path, monkeypatch)
    assert cli.main(["exceptions", run_id]) == ANSWERED
    o = out(capsys)
    assert o.count("AMBIGUOUS --") == 1, o
    assert ("    AMBIGUOUS -- caught by untraced code inside "
            "renderWithBoundary (config.ts): f2 unwound, its caller f1 "
            "returned; not followed  [×2: e3, e5]") in o, o
    assert "dispositions: ambiguous 2" in o, o
    assert "ambiguous by reason: untraced catcher 2" in o, o


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
        hops = _masked(RUST.hops_line(trace, unit))
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
