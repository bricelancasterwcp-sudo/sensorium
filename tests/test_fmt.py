from sensorium.query import fmt
from sensorium.store.reader import Trace
from tests.helpers import record_script


def test_fmt_scalars():
    assert fmt.fmt_value({"k": "num", "v": 1800}) == "1800"
    assert fmt.fmt_value({"k": "str", "v": "hi"}) == "'hi'"
    assert fmt.fmt_value({"k": "str", "v": "xx", "trunc": True}) == "'xx'~"
    assert fmt.fmt_value({"k": "none"}) == "None"
    assert fmt.fmt_value({"k": "bool", "v": True}) == "True"
    assert fmt.fmt_value(None) == "?"


def test_fmt_containers_and_objects():
    v = {"k": "seq", "type": "list", "len": 3, "oid": 1,
         "sample": [{"k": "num", "v": 1}, {"k": "num", "v": 2},
                    {"k": "num", "v": 3}]}
    assert fmt.fmt_value(v) == "list[3]=[1, 2, 3]"
    v["trunc"] = True
    assert fmt.fmt_value(v).endswith(", ...]")
    o = {"k": "obj", "type": "Grid", "oid": 99, "repr": "<Grid>"}
    assert fmt.fmt_value(o) == "Grid#99"


def test_fmt_args_caps_at_limit():
    args = {f"a{i}": {"k": "num", "v": i} for i in range(6)}
    s = fmt.fmt_args(args)
    assert s.count("=") == 4 and s.endswith(", ...")


def test_parse_refs():
    assert fmt.parse_eref("e12") == 12 and fmt.parse_eref("12") == 12
    assert fmt.parse_fref("f5") == 5


def test_more_note():
    assert fmt.more_note(10, 10, "x") is None
    assert "7 more" in fmt.more_note(10, 3, "sensorium tree R --after e9")


# -- contract: a depth-capped container omits "sample" entirely, it is never
# an empty list under the key -- fmt_value must not KeyError on that shape.
def test_fmt_value_seq_with_no_sample_key_at_all():
    v = {"k": "seq", "type": "list", "len": 5, "oid": 3, "trunc": True}
    assert fmt.fmt_value(v) == "list[5]=[, ...]"


def test_fmt_value_map_with_no_sample_key_at_all():
    v = {"k": "map", "type": "dict", "len": 5, "oid": 4, "trunc": True}
    assert fmt.fmt_value(v) == "dict[5]={, ...}"


# -- contract: LINE payloads may carry a sibling "unbound" key (names that
# went out of scope this step) alongside "deltas", and may have EMPTY
# deltas with a non-empty "unbound". fmt_event must render it, not drop it.
class _FakeCode:
    qualname = "work"


class _FakeTrace:
    def code(self, cid):
        return _FakeCode()


class _FakeEvent:
    def __init__(self, payload):
        self.id = 81
        self.code_id = 1
        self.kind = "LINE"
        self.line = 4
        self.payload = payload


def test_fmt_event_line_renders_unbound_names():
    e = _FakeEvent({"deltas": {}, "unbound": ["e"]})
    out = fmt.fmt_event(_FakeTrace(), e)
    assert out == f"e81 {'LINE':<7} work L4  unbound:e"
    assert "unbound" in out


def test_fmt_event_line_renders_deltas_and_unbound_together():
    e = _FakeEvent({"deltas": {"total": {"k": "num", "v": 15}},
                     "unbound": ["e"]})
    out = fmt.fmt_event(_FakeTrace(), e)
    assert out == f"e81 {'LINE':<7} work L4  total=15  unbound:e"


def test_fmt_event_line_with_only_deltas_matches_dense_house_style():
    e = _FakeEvent({"deltas": {"total": {"k": "num", "v": 15}}})
    out = fmt.fmt_event(_FakeTrace(), e)
    assert out == f"e81 {'LINE':<7} work L4  total=15"


# -- fmt_event coverage against a REAL recorded trace, not a fake's idea of
# the format. The three tests above only ever construct kind="LINE" -- CALL,
# RETURN, RAISE and HANDLED had zero coverage, and every later query command
# (Tasks 10-15) renders events through this function. Pin all five branches
# here, against actual recorder output, so a regression in any of them is
# caught by the suite rather than by hand-checking against live traces.
_FIVE_KINDS_SRC = """
def work(n):
    total = n + 1
    try:
        [1, 2][n]
    except IndexError:
        pass
    return total

def main():
    work(5)

if __name__ == "__main__":
    main()
"""


def _first_of_kind(trace, kind, qualname):
    for e in trace.events(kind=kind):
        code = trace.code(e.code_id) if e.code_id is not None else None
        if code is not None and code.qualname == qualname:
            return e
    raise AssertionError(f"no {kind} event found for {qualname!r}")


def test_fmt_event_renders_all_five_kinds_from_a_real_trace(tmp_path):
    run_id, trace_path, r = record_script(
        tmp_path, _FIVE_KINDS_SRC, extra=["--focus", "prog:work"])
    assert run_id, r.stderr
    trace = Trace.open(trace_path)

    call = _first_of_kind(trace, "CALL", "work")
    assert fmt.fmt_event(trace, call) == f"e{call.id} {'CALL':<7} work(n=5)"

    ret = _first_of_kind(trace, "RETURN", "work")
    assert fmt.fmt_event(trace, ret) == f"e{ret.id} {'RETURN':<7} work -> 6"

    raised = _first_of_kind(trace, "RAISE", "work")
    assert fmt.fmt_event(trace, raised) == (
        f"e{raised.id} {'RAISE':<7} work raise "
        "IndexError('list index out of range') L5")

    handled = _first_of_kind(trace, "HANDLED", "work")
    assert fmt.fmt_event(trace, handled) == (
        f"e{handled.id} {'HANDLED':<7} work handled "
        "IndexError('list index out of range') L5")

    # under --focus prog:work, work's `total = n + 1` LINE fires just
    # before line 4 (the `try:`), carrying the delta produced by line 3.
    line = next(e for e in trace.events(kind="LINE") if e.line == 4)
    assert fmt.fmt_event(trace, line) == (
        f"e{line.id} {'LINE':<7} work L4  total=6")
