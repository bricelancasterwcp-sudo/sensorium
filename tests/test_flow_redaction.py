"""`flow` over a value the redaction rule took: no sighting, no lineage.

Two failures this closes, and they fail in opposite directions.

`--value '<redacted>'` is the FALSE SIGHTING. Every name-redacted capture
holds the same five characters, whatever the value behind it was, so a
literal search for that text would report every taken value in the run as a
sighting of one value -- and the screen would look exactly like a correct
answer, which is this command's worst failure mode. A taken capture is
therefore never a sighting of any literal: what it holds is the rule's
marker, not the program's value.

`--object e1:token` is the FALSE LINEAGE. A taken container keeps its `oid`
(its address is a fact about the program, not about the value), so the
resolver would happily mint a target from one and follow an address whose
occupant nobody recorded. It refuses instead, at BAD_CALL: the trace is
fine, the call has to change.

A CONTENT hit is neither. The recorder kept the text, the identity is
untouched, and both searches work on it exactly as they did before -- which
is the fence `test_a_content_hit_is_followed_exactly_as_before` holds.
"""
from sensorium.exit import BAD_CALL
from sensorium.query import flow_cmd
from sensorium.query.flow_values import ObjTarget, find_in_value, matches
from tests.flow_programs import open_trace
from tests.helpers import finalize_synthetic
from tests.programs import synthetic

RUN = "20260101-000000-abcdef"

#: What the writer leaves behind in the field it took (`redact.REDACTED`).
STORED = "<redacted>"

BY_NAME = {"by": "name", "digest": "0123456789abcdef"}
BY_CONTENT = {"by": "content", "digest": None}


def taken_str() -> dict:
    return {"k": "str", "v": STORED, "redacted": BY_NAME}


def taken_map(sample=None) -> dict:
    """A `map` the name rule took. The writer keeps `k`/`type`/`len`/`oid`
    and drops the sample (B4) -- `sample` is a parameter only so a test can
    state what the KEEP rule is protecting."""
    out = {"k": "map", "type": "dict", "len": 2, "oid": 7,
           "redacted": BY_NAME}
    if sample is not None:
        out["sample"] = sample
    return out


def trace_with(tmp_path, monkeypatch, args: dict):
    w = synthetic(tmp_path, monkeypatch)
    c = w.intern_code("/tmp/prog.py", "leak", 1)
    call = w.add_event(0, 1, "CALL", None, c, 1, {"args": args})
    fid = w.open_frame(None, c, call, 0, 1)
    ret = w.add_event(0, 1, "RETURN", fid, c, None, {"value": {"k": "none"}})
    w.close_frame(fid, ret, "return")
    finalize_synthetic(w, run_id=RUN)
    w.close()
    trace = open_trace(RUN)
    return trace, flow_cmd.Index(trace)


# -- the false sighting ----------------------------------------------------
def test_a_taken_capture_is_a_sighting_of_nothing():
    """The literal that would otherwise match. Asserted beside the SAME
    capture without the `redacted` object, so the test states that the
    marker object is what decides it -- not the text, which is identical."""
    assert matches(taken_str(), STORED) is False
    assert matches({"k": "str", "v": STORED}, STORED) is True


def test_a_taken_number_is_not_a_sighting_of_the_text_either():
    """A taken `num` holds the marker text in a numeric capture, which no
    literal should reach: `--value 0` must not sight it, and neither must
    `--value '<redacted>'`."""
    cap = {"k": "num", "v": STORED, "redacted": BY_NAME}
    assert matches(cap, STORED) is False
    assert matches(cap, 0) is False


def test_a_taken_container_is_not_a_sighting_of_its_own_address():
    """Its `oid` is kept on purpose, so an identity search reaches it --
    and must not: the address is real, the occupant was never recorded."""
    assert matches(taken_map(), ObjTarget(7, "dict")) is False


def test_nothing_inside_a_taken_container_is_reachable():
    """The writer drops the sample, so a taken container has no members to
    walk -- and the search reports that honestly rather than listing paths
    into a value it does not hold. The unredacted twin lists the member,
    which is what says the walk itself still works."""
    assert find_in_value(taken_map(), "hunter2", "arg cfg") == []
    plain = {"k": "map", "type": "dict", "len": 2, "oid": 7,
             "sample": [[{"k": "str", "v": "pw"},
                         {"k": "str", "v": "hunter2"}]]}
    assert find_in_value(plain, "hunter2", "arg cfg") == ["arg cfg.pw"]


def test_a_taken_container_that_still_carried_a_sample_lists_no_root():
    """Belt and braces on the KEEP rule: if a writer ever left a sample on
    a taken container, the container itself is still not a sighting -- the
    guard is on the capture, not on the absence of members."""
    sample = [[{"k": "str", "v": "pw"}, {"k": "str", "v": STORED}]]
    assert "" not in find_in_value(taken_map(sample), STORED)


# -- the false lineage -----------------------------------------------------
def test_following_a_taken_value_is_refused_by_name(tmp_path, monkeypatch):
    """BAD_CALL and not NEGATIVE: the trace holds the event and the name,
    so this is not the recording answering "no" -- it is a call that has to
    change. The sentence names the rule that took it, because "no identity
    to follow" alone would read as a recorder shortcoming."""
    trace, idx = trace_with(tmp_path, monkeypatch, {"token": taken_str()})
    target, ref, note, err = flow_cmd.resolve_object(trace, idx, "e1:token")
    assert target is None and ref is None and note is None
    assert err.status == BAD_CALL
    assert err.message == ("'token' at e1 is redacted (by name) and has no "
                           "identity or value to follow")


def test_a_taken_container_is_refused_before_its_kept_address(
        tmp_path, monkeypatch):
    """The ordering that matters: a taken `map` passes every later check --
    it is not a primitive and it carries both `oid` and `type` -- so a
    guard placed after them would let the resolver mint a target from it."""
    trace, idx = trace_with(tmp_path, monkeypatch, {"cfg": taken_map()})
    target, _ref, _note, err = flow_cmd.resolve_object(trace, idx, "e1:cfg")
    assert target is None
    assert err.status == BAD_CALL and "is redacted (by name)" in err.message


def test_a_content_hit_is_followed_exactly_as_before(tmp_path, monkeypatch):
    """The rule replaced a span in this object's `repr`. Its identity was
    never touched, so the lineage it has is the lineage it had."""
    obj = {"k": "obj", "type": "Cfg", "oid": 9,
           "repr": f"Cfg(pw='{STORED}')", "redacted": BY_CONTENT}
    trace, idx = trace_with(tmp_path, monkeypatch, {"cfg": obj})
    target, ref, _note, err = flow_cmd.resolve_object(trace, idx, "e1:cfg")
    assert err is None
    assert target == ObjTarget(9, "Cfg") and ref == "e1:cfg"


def test_a_content_hit_is_sighted_by_the_text_the_trace_holds():
    """`--value` over a partially redacted string still answers: the
    characters the recorder kept are the characters it compares."""
    url = f"postgres://u:{STORED}@h/db"
    assert matches({"k": "str", "v": url, "redacted": BY_CONTENT}, url)
