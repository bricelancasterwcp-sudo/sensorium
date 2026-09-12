"""`flow` over an identity that is exact, and the gate that admits it.

Python's `--object` is a hedged claim and says so on every run: CPython
recycles addresses, so two sightings of one `(oid, type)` may be two
objects, and everything `flow` prints between them -- ADDRESS REUSED, NEW
OBJECT, spanned by, unwitnessed -- exists to corroborate a continuity the
trace cannot prove. A TypeScript serial is minted once per object from a
`WeakMap` and never reused, so there is nothing to corroborate: every
sighting IS the same object. Printing Python's caveats over it would
understate what this recording holds, and running the gap analysis would
print hedges about gaps that cannot exist.

The gate moves with it (ruling R13). A serial rides on EVERY capture this
recorder writes -- a RETURN value at the call tier, an argument and a
statement's delta under a focus -- so `flow --object` needs
`object_identity` and nothing else. `flow --value` still needs `line`: a
value that only lived in a local between call and return is not in a trace
that recorded no statement. The "no LINE events" note prints on an object
flow all the same, because what it says (a local was never captured) is
just as true there.
"""
import pytest

from sensorium import cli
from sensorium.exit import ANSWERED, BAD_CALL, UNSETTLED
from sensorium.query.dbg_dialects import INSPECT, RUST
from sensorium.query.flow_values import ObjTarget, matches
from tests.ts_traces import (TS_CAPABILITIES, TS_CAPABILITIES_0_1, call,
                             frame, line_ev, out, ret, task, ts_trace)

FILE = "/w/app/src/lib/settings.ts"
ROOT = "/w/app"
FOCUSED_CAPS = {**TS_CAPABILITIES, "line": True, "locals": True}


def dbg(text, **extra):
    return {"k": "dbg", "v": text, "trunc": False, **extra}


def obj(text, oid, type_="Object"):
    """A captured OBJECT: the inspect text, plus the identity the runtime
    minted for it (`oid`) and its constructor's name."""
    return dbg(text, oid=oid, type=type_)


def focused_trace(tmp_path, monkeypatch, **meta):
    """One focused activation that binds one object to two names, mutating
    it in between -- the shape `flow --object` is asked about."""
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "tune", 5]],
        frames=[frame(1, 1, 5)],
        events=[
            call(1000, 1, 5, task=1, args={"base": dbg("4")}),
            line_ev(2000, 1, 1, 6, {"cfg": obj("{ retries: 3 }", 7)}, task=1),
            line_ev(3000, 1, 1, 7, {"alias": obj("{ retries: 9 }", 7)},
                    task=1),
            line_ev(4000, 1, 1, 8, {"n": dbg("5")}, task=1),
            ret(5000, 1, 1, task=1),
        ],
        tasks=[task(1, "settings > tunes")],
        capabilities=FOCUSED_CAPS, root=ROOT,
        focus=["settings.ts:tune"],
        focus_matched=["src/lib/settings.ts:tune"], **meta)


def call_tier_trace(tmp_path, monkeypatch, **meta):
    """An UNFOCUSED container: no statement was instrumented, and the two
    RETURNs still carry the identity of the object they handed back."""
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "loadSettings", 12]],
        frames=[frame(1, 1, 2), frame(1, 3, 4)],
        events=[
            call(1000, 1, 12, task=1),
            ret(2000, 1, 1, task=1),
            call(3000, 1, 12, task=1),
            ret(4000, 2, 1, task=1),
        ],
        tasks=[task(1, "settings > shares")],
        root=ROOT, **meta)


def _with_returns(tmp_path, monkeypatch):
    """`call_tier_trace`, with the shared object on both RETURNs."""
    return ts_trace(
        tmp_path, monkeypatch,
        codes=[[FILE, "loadSettings", 12]],
        frames=[frame(1, 1, 2), frame(1, 3, 4)],
        events=[
            call(1000, 1, 12, task=1),
            {"ts": 2000, "thread": 1, "kind": "RETURN", "frame": 1,
             "code": 1, "line": None,
             "payload": {"value": obj("{ retries: 3 }", 4), "outcome": "ok"},
             "task": 1},
            call(3000, 1, 12, task=1),
            {"ts": 4000, "thread": 1, "kind": "RETURN", "frame": 2,
             "code": 1, "line": None,
             "payload": {"value": obj("{ retries: 3 }", 4), "outcome": "ok"},
             "task": 1},
        ],
        tasks=[task(1, "settings > shares")],
        root=ROOT)


# -- (a) an exact identity, said as one ------------------------------------
def test_two_sightings_of_one_serial_are_one_object(
        tmp_path, monkeypatch, capsys):
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--object", "e2:cfg"]) == ANSWERED
    text = out(capsys)
    assert f"flow of object #7 (Object) in {run_id}" in text
    assert ("  identity is a per-object serial minted once and never reused: "
            "every sighting is the same object") in text
    assert ("  captured-value lineage, not dataflow analysis: the trace "
            "records values, not the edges between them") in text
    assert "sightings: 2 event(s), 2 capture(s)" in text
    assert "continuity: exact (serial identity)" in text


def test_nothing_is_hedged_about_a_gap_that_cannot_exist(
        tmp_path, monkeypatch, capsys):
    """Every line the address-based analysis prints is a claim about
    whether two sightings are one object. On a serial they are, so none of
    them may print -- and CPython's caveat may not either."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--object", "e2:cfg"]) == ANSWERED
    text = out(capsys)
    for absent in ("unwitnessed", "spanned by", "ADDRESS REUSED",
                   "NEW OBJECT", "memory address", "CPython",
                   "gap(s) spanned by a recorded binding"):
        assert absent not in text, absent


def test_the_mutation_is_the_two_renderings_of_the_one_object(
        tmp_path, monkeypatch, capsys):
    """What an exact identity buys: the object is the same and its inspect
    text is not, which is the mutation itself."""
    run_id = focused_trace(tmp_path, monkeypatch)
    cli.main(["flow", run_id, "--object", "e2:cfg"])
    text = out(capsys)
    assert "cfg={ retries: 3 }   [local cfg]" in text
    assert "alias={ retries: 9 }   [local alias]" in text


# -- (b) what has an identity, and what has none ---------------------------
def test_a_capture_with_no_serial_is_a_primitive_and_says_which_command(
        tmp_path, monkeypatch, capsys):
    """A number has no identity to follow, and the refusal names the
    command that does answer about it. The recorder puts a serial on an
    object and a function and on nothing else, so this is the whole of the
    "not an object" case."""
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--object", "e1:base"]) == BAD_CALL
    text = out(capsys)
    assert ("error: 'base' at e1 is a primitive (4) and has no identity to "
            "follow; use --value 4") in text


def test_a_return_value_carries_an_identity_at_the_call_tier(
        tmp_path, monkeypatch, capsys):
    """R13's reason, measured: this container instrumented no statement at
    all, and the object two activations handed back is still followable."""
    run_id = _with_returns(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--object",
                     "loadSettings:return"]) == ANSWERED
    text = out(capsys)
    assert "flow of object #4 (Object)" in text
    assert "sightings: 2 event(s), 2 capture(s)" in text
    assert "continuity: exact (serial identity)" in text
    # ...and the note that no local was ever captured still prints: it is
    # as true here as on a value flow, and a reader may be looking for a
    # sighting that only a focused run would hold.
    assert "this run recorded no LINE events" in text


# -- (c) the gate (ruling R13) ---------------------------------------------
def test_an_object_flow_needs_identity_and_not_line(
        tmp_path, monkeypatch, capsys):
    """The recording has no LINE row and declares none, and the question is
    answered anyway. Before R13 this refused at exit 3 -- a refusal about a
    capability the search does not read."""
    run_id = call_tier_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--object",
                     "loadSettings:return"]) != UNSETTLED
    assert "REFUSED" not in out(capsys)


def test_a_value_flow_still_needs_line(tmp_path, monkeypatch, capsys):
    """Unchanged, and for a reason the note above states: a value that only
    lived in a local between call and return is not in this trace."""
    run_id = call_tier_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--value", "5"]) == UNSETTLED
    assert ("REFUSED: flow needs line, which recorder sensorium-ts 0.3.0 "
            "declares it does not produce (capabilities.line: false); "
            "nothing was checked") in out(capsys)


def test_an_object_flow_on_a_recorder_with_no_identity_is_refused(
        tmp_path, monkeypatch, capsys):
    """The 0.1.x shape: no capture it wrote carries a serial, so there is
    no identity to follow and the refusal names the capability."""
    run_id = call_tier_trace(tmp_path, monkeypatch,
                             capabilities=TS_CAPABILITIES_0_1,
                             recorder="sensorium-ts 0.1.0")
    assert cli.main(["flow", run_id, "--object",
                     "loadSettings:return"]) == UNSETTLED
    assert ("REFUSED: flow --object needs object_identity, which recorder "
            "sensorium-ts 0.1.0 declares it does not produce") in out(capsys)


# -- (d) --value, in the dialect the trace names ---------------------------
def test_five_point_zero_sights_a_five_here_and_never_on_a_rust_trace():
    """JavaScript has one number type, so `5.0` IS `5` and a sighting is
    right. Rust prints `5.0` for the float and `5` for the integer, and
    `tests/test_query_rust_dbg.py` keeps that fence: one capture, two
    dialects, two answers, neither of them a guess."""
    cap = {"k": "dbg", "v": "5", "trunc": False}
    assert matches(cap, 5.0, INSPECT.write) is True
    assert matches(cap, 5, INSPECT.write) is True
    assert matches(cap, 5.0, RUST.write) is False
    assert matches(cap, 5.0) is False               # the default is Rust's


def test_flow_value_searches_the_traces_own_dialect(
        tmp_path, monkeypatch, capsys):
    run_id = focused_trace(tmp_path, monkeypatch)
    assert cli.main(["flow", run_id, "--value", "5.0"]) == ANSWERED
    text = out(capsys)
    assert "sightings: 1 event(s), 1 capture(s)" in text
    assert "[local n]" in text


def test_an_object_target_never_matches_a_rendering_without_a_serial():
    """A `dbg` text carries no identity of its own; only the two keys the
    runtime adds do. Matching on the TEXT would splice every object that
    renders the same way into one lineage -- the worst failure this command
    has, because the output looks exactly like a correct answer."""
    target = ObjTarget(7, "Object")
    assert matches(dbg("{ retries: 3 }"), target, INSPECT.write) is False
    assert matches(obj("{ retries: 3 }", 7), target, INSPECT.write) is True
    assert matches(obj("{ retries: 3 }", 8), target, INSPECT.write) is False
    assert matches(obj("{ retries: 3 }", 7, "Settings"), target,
                   INSPECT.write) is False
    # a truncated rendering is still that object: the identity is a key on
    # the capture, not something read out of the text
    clipped = {**obj("{ retries: 3 ", 7), "trunc": True}
    assert matches(clipped, target, INSPECT.write) is True
