import pytest

from sensorium import cli
from sensorium.query import fmt
from sensorium.store.reader import Trace
from tests.helpers import record_script
from tests.programs import CLEAN, record


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


def test_fmt_value_names_the_reads_a_hostile_object_refused():
    """The marker has to survive as far as the DISPLAY. `Sneaky[0]={}` for a
    container whose own `__len__` raised is the recorder inventing a size."""
    seq = {"k": "seq", "type": "Evil", "len": 3, "oid": 1,
           "unread": ["sample"]}
    assert fmt.fmt_value(seq) == "Evil[3]=[] <unread: sample>"
    m = {"k": "map", "type": "Sneaky", "len": None, "oid": 2, "sample": [],
         "unread": ["len"]}
    assert fmt.fmt_value(m) == "Sneaky[?]={} <unread: len>"
    nothing = {"k": "unread", "type": "Cloaked", "oid": 3,
               "unread": ["value"]}
    assert fmt.fmt_value(nothing) == "<unreadable Cloaked#3>"


def test_fmt_exc_does_not_quote_a_message_it_could_not_read():
    """...and still quotes an empty message that really was empty."""
    assert fmt.fmt_exc({"type": "Rude", "msg": "", "oid": 1,
                        "unread": ["msg"]}) \
        == "Rude(<message unreadable: __str__ raised>)"
    assert fmt.fmt_exc({"type": "ValueError", "msg": "", "oid": 1}) \
        == "ValueError('')"


def test_fmt_args_caps_at_limit():
    args = {f"a{i}": {"k": "num", "v": i} for i in range(6)}
    s = fmt.fmt_args(args)
    assert s.count("=") == 4 and s.endswith(", ...")


def test_parse_refs():
    assert fmt.parse_eref("e12") == 12 and fmt.parse_eref("12") == 12
    assert fmt.parse_fref("f5") == 5


def test_parse_refs_refuse_a_malformed_reference():
    """A typo in a ref is a user error, and `int()` answers it with a
    traceback -- a poor answer for a human and a confusing one for an agent
    parsing the output. It also has to stay a ValueError subclass so nothing
    that already guards these calls changes behaviour."""
    for bad in ("xyz", "e", "", "e4x", "-3", "e 4", "eef12"):
        with pytest.raises(fmt.RefError) as exc:
            fmt.parse_eref(bad)
        assert repr(bad) in str(exc.value) and "e<id>" in str(exc.value)
    assert issubclass(fmt.RefError, ValueError)

    with pytest.raises(fmt.RefError) as exc:
        fmt.parse_fref("f9x")
    assert "frame reference" in str(exc.value) and "f<id>" in str(exc.value)


REF_FLAGS = [
    (["grep", "RUN", "x", "--after", "xyz"], "event"),
    (["exceptions", "RUN", "--after", "xyz"], "event"),
    (["flow", "RUN", "--value", "1", "--after", "xyz"], "event"),
    (["tree", "RUN", "--around", "xyz"], "event"),
    (["tree", "RUN", "--root", "xyz"], "frame"),
    (["frame", "RUN", "xyz"], "frame"),
]


@pytest.mark.parametrize("argv,kind", REF_FLAGS)
def test_every_command_refuses_a_malformed_ref_cleanly(
        tmp_path, monkeypatch, capsys, argv, kind):
    """`parse_eref` is shared, so the hole was shared: three commands died
    with an uncaught ValueError on a typo. One fix, one clean refusal."""
    run_id = record(tmp_path, monkeypatch, CLEAN)
    argv = [run_id if a == "RUN" else a for a in argv]
    assert cli.main(argv) == 2
    err = capsys.readouterr().err
    assert "'xyz' is not a" in err and f"{kind} reference" in err
    assert "Traceback" not in err


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
