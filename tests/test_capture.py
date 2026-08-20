import re

from sensorium import cli
from sensorium.record.capture import CAPS, capture_exc, capture_stats, capture_value
from sensorium.store.writer import TraceWriter
from tests.helpers import record_inproc, record_script


def test_primitives_stored_natively():
    assert capture_value(42) == {"k": "num", "v": 42}
    assert capture_value(2.5) == {"k": "num", "v": 2.5}
    assert capture_value(True) == {"k": "bool", "v": True}
    assert capture_value(None) == {"k": "none"}
    assert capture_value("hi") == {"k": "str", "v": "hi"}


def test_long_string_truncated_and_marked():
    before = capture_stats["truncated"]
    v = capture_value("x" * 500)
    assert v["trunc"] is True and len(v["v"]) == CAPS["str"]
    assert capture_stats["truncated"] == before + 1


def test_large_list_keeps_len_and_capped_sample():
    v = capture_value(list(range(1000)))
    assert v["k"] == "seq" and v["len"] == 1000 and v["trunc"] is True
    assert len(v["sample"]) == CAPS["sample"]
    assert v["sample"][0] == {"k": "num", "v": 0}
    assert isinstance(v["oid"], int)


def test_dict_sample_pairs():
    v = capture_value({"a": 1, "b": 2})
    assert v["k"] == "map" and v["len"] == 2 and "trunc" not in v
    assert v["sample"][0] == [{"k": "str", "v": "a"}, {"k": "num", "v": 1}]


def test_object_has_oid_and_capped_repr():
    class Grid:
        def __repr__(self):
            return "<Grid " + "y" * 500 + ">"
    g = Grid()
    v = capture_value(g)
    assert v["k"] == "obj" and v["type"] == "Grid" and v["oid"] == id(g)
    assert len(v["repr"]) == CAPS["repr"] and v["trunc"] is True


def test_hostile_repr_is_guarded():
    class Bomb:
        def __repr__(self):
            raise RuntimeError("boom")
    v = capture_value(Bomb())
    assert v["k"] == "obj" and "repr-raised" in v["repr"] and v["trunc"] is True


def test_recursive_structure_stops_at_depth_cap():
    l: list = []
    l.append(l)
    v = capture_value(l)          # must not RecursionError
    assert v["k"] == "seq"


def test_capture_exc():
    e = ValueError("bad amount")
    assert capture_exc(e) == {"type": "ValueError", "msg": "bad amount",
                              "oid": id(e)}


# -- hostile dunders: every read here is a call INTO the observed program --
#
# `__repr__` was guarded from the start; its four neighbours were not, and
# each of them runs from inside a `sys.monitoring` callback, so an exception
# escaping one does not fail the capture -- it lands in the observed
# program's own frame and is then reported as that program's bug.
class Evil(list):
    def __iter__(self):
        raise ValueError("iter is mine")


class Sneaky(dict):
    def __len__(self):
        raise KeyError("len is mine")


class Secretive(dict):
    def items(self):
        raise KeyError("items are mine")


class Rude(Exception):
    def __str__(self):
        raise RuntimeError("str is mine")


def test_hostile_iter_is_guarded_and_the_length_still_stands():
    """The two reads fail independently: `len` succeeded, so it is reported,
    and the sample is ABSENT rather than an empty list that would read as an
    empty container."""
    before = capture_stats["truncated"]
    v = capture_value(Evil([1, 2, 3]))
    assert v["k"] == "seq" and v["len"] == 3
    assert v["unread"] == ["sample"] and "sample" not in v
    assert capture_stats["truncated"] == before + 1


def test_hostile_len_is_guarded_and_the_sample_still_stands():
    """`len` is None, never 0: a size that could not be read is not a size."""
    before = capture_stats["truncated"]
    v = capture_value(Sneaky(a=1))
    assert v["k"] == "map" and v["len"] is None and v["unread"] == ["len"]
    assert v["sample"] == [[{"k": "str", "v": "a"}, {"k": "num", "v": 1}]]
    assert capture_stats["truncated"] == before + 1


def test_hostile_items_is_guarded():
    v = capture_value(Secretive(a=1))
    assert v["k"] == "map" and v["len"] == 1
    assert v["unread"] == ["sample"] and "sample" not in v


def test_both_reads_hostile_names_both():
    class Total(dict):
        def __len__(self):
            raise KeyError("len is mine")

        def items(self):
            raise KeyError("items are mine")
    v = capture_value(Total(a=1))
    assert v["len"] is None and "sample" not in v
    assert v["unread"] == ["len", "sample"]


def test_an_empty_container_records_an_empty_sample_not_a_missing_one():
    """`"sample": []` means "looked, and there was nothing there". `sample`
    ABSENT means "did not look" -- depth-capped, or a read that raised. The
    guard must not collapse the two into one shape."""
    v = capture_value([])
    assert v["k"] == "seq" and v["len"] == 0 and v["sample"] == []
    assert "unread" not in v and "trunc" not in v


def test_hostile_str_on_an_exception_is_guarded():
    """An exception whose `__str__` raises has no message the trace can
    quote. It gets "" plus an explicit unread marker -- never an empty
    message passed off as the message it was raised with."""
    e = Rude()
    cap = capture_exc(e, serial=7)
    assert cap == {"type": "Rude", "msg": "", "oid": id(e),
                   "unread": ["msg"], "serial": 7}


def test_hostile_class_property_cannot_escape_capture():
    """`isinstance` consults `__class__`, so the very first branch of a
    capture is already a call into user code."""
    class Cloaked:
        @property
        def __class__(self):
            raise ValueError("no isinstance for you")
    v = capture_value(Cloaked())
    assert v["k"] == "unread" and v["unread"] == ["value"]
    assert v["type"] == "Cloaked"


def test_hostile_type_name_cannot_escape_capture():
    class Meta(type):
        @property
        def __name__(cls):
            raise ValueError("no name for you")

    class Anonymous(metaclass=Meta):
        pass
    v = capture_value(Anonymous())
    assert v["k"] == "obj" and v["type"] == "?"


# -- a capture must never EMBED a live object ------------------------------
#
# Guarding the reads is not enough on its own: a capture that holds a `str`,
# `int` or `float` SUBCLASS instance has smuggled the observed program's
# dunders past every guard here, into a payload that outlives them. Two
# consumers then run that code on the recorder's own thread -- `_on_line`'s
# `prev.get(name) != cap` and `writer.add_event`'s json encoding -- with no
# guard at either site.
class _LiveStr(str):
    """Refuses every comparison, so an embedded instance shows up loudly."""
    def __eq__(self, other):
        raise ValueError("EMBEDDED-eq")

    def __ne__(self, other):
        raise ValueError("EMBEDDED-ne")

    def __hash__(self):
        return 0


def test_a_str_subclass_is_captured_as_its_exact_base_type():
    class Lying(_LiveStr):
        def __str__(self):
            return _LiveStr("not the real characters")
    v = capture_value(Lying("abc"))
    assert type(v["v"]) is str          # not the subclass...
    assert v["v"] == "abc"              # ...and the TRUE characters


def test_int_and_float_subclasses_are_captured_as_their_base_types():
    """`int()`/`float()` honour `__int__`/`__float__`, which can both lie
    about the value and hand back another subclass instance. The unbound
    base slots cannot be intercepted."""
    class LyingInt(int):
        def __int__(self):
            return LyingInt(99)

    class LyingFloat(float):
        def __float__(self):
            return LyingFloat(9.9)
    i = capture_value(LyingInt(7))
    assert type(i["v"]) is int and i["v"] == 7
    f = capture_value(LyingFloat(1.5))
    assert type(f["v"]) is float and f["v"] == 1.5


def test_plain_num_is_total_even_for_a_hostile_class_subclass():
    """`plain_num` must be total by construction like `plain_str`: a numeric
    subclass whose `__class__` property raises is dispatched by TYPE and read
    through the base slot, never returned live via the exception path. `_capture`
    guards this one step earlier today, but the function's own guarantee must
    not rest on that ordering -- "safe only because of the order things happen
    in" is exactly the argument this project has watched rot before."""
    from sensorium.record.capture import plain_num

    class HostileFloat(float):
        @property
        def __class__(self):
            raise RuntimeError("no class for you")

    h = HostileFloat(3.5)
    out = plain_num(h)
    assert type(out) is float and out == 3.5 and out is not h


def test_a_repr_returning_a_str_subclass_is_normalised():
    """`repr()` is free to return a subclass instance, so guarding the CALL
    to `__repr__` does not stop one reaching the payload."""
    class Sneaky:
        def __repr__(self):
            return _LiveStr("<Sneaky>")
    v = capture_value(Sneaky())
    assert type(v["repr"]) is str and v["repr"] == "<Sneaky>"


def test_an_exception_message_that_is_a_str_subclass_is_normalised():
    class Odd(Exception):
        def __str__(self):
            return _LiveStr("odd")
    cap = capture_exc(Odd())
    assert type(cap["msg"]) is str and cap["msg"] == "odd"


def test_a_type_name_that_is_a_str_subclass_is_normalised():
    class Meta(type):
        @property
        def __name__(cls):
            return _LiveStr("Named")

    class Odd(metaclass=Meta):
        pass
    v = capture_value(Odd())
    assert type(v["type"]) is str and v["type"] == "Named"


def assert_plain(node) -> None:
    """Nothing in this tree may be an instance of a type the program defined.

    The invariant the normalisation buys, checkable at any depth: keys are
    exact `str`, leaves are exact `str`/`int`/`float`/`bool`/`None`. A
    subclass instance anywhere here is a live object with live dunders that
    the recorder will later compare and json-encode, outside every guard.
    """
    if type(node) is dict:
        for k, v in node.items():
            assert type(k) is str, (k, type(k))
            assert_plain(v)
    elif type(node) is list:
        for x in node:
            assert_plain(x)
    else:
        assert type(node) in (str, int, float, bool, type(None)), \
            (node, type(node))


def test_a_capture_holds_no_live_object_anywhere_in_its_tree():
    """The property, over a nested container rather than one value."""
    class LiveInt(int):
        pass
    assert_plain(capture_value({_LiveStr("k"): [LiveInt(3),
                                                (_LiveStr("deep"),)]}))


# -- end to end: the recorder must not create the bug it then reports ------
HOSTILE = """
class Evil(list):
    def __iter__(self):
        raise ValueError("iter is mine")

class Sneaky(dict):
    def __len__(self):
        raise KeyError("len is mine")

class Rude(Exception):
    def __str__(self):
        raise RuntimeError("str is mine")

def consume(bag, book):
    return len(bag) + 100          # list's own __len__; `book` is untouched

def swallow():
    try:
        raise Rude()
    except Rude:
        return "handled"

def main():
    print("result", consume(Evil([1, 2, 3]), Sneaky(a=1)))
    print("swallowed", swallow())

main()
"""


def _line(out: str, prefix: str) -> str:
    """The one output line starting with `prefix`.

    Extracted rather than substring-matched against the whole output: five
    non-biting tests on this project shared exactly that shape, an assertion
    satisfied by a line other than the one it meant to check.
    """
    hits = [ln for ln in out.splitlines() if ln.startswith(prefix)]
    assert len(hits) == 1, f"{prefix!r} matched {len(hits)} lines in:\n{out}"
    return hits[0]


def test_a_hostile_program_still_runs_to_completion_under_recording(
        tmp_path, monkeypatch, capsys):
    """The whole point, end to end. This program runs clean standalone; it
    must run clean under `sensorium run` too, and `exceptions` must not
    report an exception the recorder itself created."""
    run_id, _trace, r = record_script(tmp_path, HOSTILE)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "result 103" in r.stdout and "swallowed handled" in r.stdout

    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    # The program raises exactly one exception, and handles it.
    assert _line(out, "dispositions:") == "dispositions: swallowed 1"
    assert not re.search(r"^uncaught:", out, re.M)
    # None of the three exceptions the unguarded recorder used to inject.
    for injected in ("iter is mine", "len is mine", "str is mine"):
        assert injected not in out
    # And the one real exception says what it could not read, rather than
    # reporting a Rude() raised with no message.
    assert "Rude(<message unreadable: __str__ raised>)" in out


# -- the three delayed injections: a live object smuggled into a payload ---
#
# Each of these programs runs clean standalone and, before the normalisation,
# died at exit 1 under `sensorium run` with the recorder's OWN exception
# reported as the program's uncaught bug at the program's own line.

# 1. `_on_line`'s `prev.get(name) != cap`. The capture EMBEDDED the instance,
#    dict comparison's identity shortcut hid it while one instance persisted,
#    and rebinding the name to a second instance ran `__eq__`. Needs --focus,
#    because LINE events are what compare captures.
HOSTILE_EQ = """
class EvilStr(str):
    def __eq__(self, other):
        raise ValueError("INJECTED-eq")
    def __hash__(self):
        return 0

def churn():
    x = EvilStr("a")
    x = EvilStr("b")
    return "ok"

def main():
    print("churn", churn())

main()
"""

# 2. `writer.add_event`'s `json.dumps(..., default=repr)`. Reachable in
#    DEFAULT mode with no --focus at all, because it rides ordinary CALL
#    argument capture -- strictly broader than the first.
HOSTILE_SERIALISE = """
class Payload:
    def __repr__(self):
        raise ValueError("INJECTED-repr")

class SneakyStr(str):
    def __len__(self):
        return 10000                 # forces the clip...
    def __getitem__(self, k):
        return Payload()             # ...which then returns THIS

def take(s):
    return "ok"

def main():
    print("take", take(SneakyStr("abc")))

main()
"""

# 3. Found by the sweep, reported by nobody: `_Tee.write`'s `if s:` ran the
#    program's `__bool__`/`__len__` from inside its own `sys.stdout.write`,
#    and the instance was then held in the writer's buffer and bound into
#    sqlite from there.
HOSTILE_STREAM = """
import sys

class BoomLen(str):
    def __len__(self):
        raise ValueError("INJECTED-len")

def emit():
    sys.stdout.write(BoomLen("out\\n"))
    return "ok"

def main():
    print("emit", emit())

main()
"""


def _runs_clean(tmp_path, monkeypatch, capsys, src, expect, extra=()):
    """Record `src`, assert it completed, and that `exceptions` reports
    nothing the recorder injected."""
    run_id, _trace, r = record_script(tmp_path, src, extra=extra)
    assert r.returncode == 0, r.stdout + r.stderr
    assert expect in r.stdout, r.stdout
    assert "INJECTED" not in r.stderr, r.stderr

    monkeypatch.setenv("SENSORIUM_DIR", str(tmp_path / "sdir"))
    assert cli.main(["exceptions", run_id]) == 0
    out = capsys.readouterr().out
    assert "INJECTED" not in out, out
    assert not re.search(r"^uncaught:", out, re.M), out
    return run_id, out


def test_a_rebound_hostile_eq_does_not_reach_the_delta_comparison(
        tmp_path, monkeypatch, capsys):
    run_id, _out = _runs_clean(tmp_path, monkeypatch, capsys, HOSTILE_EQ,
                               "churn ok", extra=("--focus", "prog:churn"))
    # The deltas were still recorded, with the TRUE characters: the fix
    # normalises the capture, it does not stop capturing.
    assert cli.main(["grep", run_id, "churn"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert any(ln.endswith("x='a'") for ln in lines), lines
    assert any(ln.endswith("x='b'") for ln in lines), lines


def test_a_hostile_getitem_does_not_reach_the_payload_encoder(
        tmp_path, monkeypatch, capsys):
    """Default mode: no --focus, so this rides CALL argument capture."""
    run_id, _out = _runs_clean(tmp_path, monkeypatch, capsys,
                               HOSTILE_SERIALISE, "take ok")
    # ...and what was recorded is the string's TRUE characters, not the
    # 10000 its __len__ claimed nor what its __getitem__ handed back.
    assert cli.main(["grep", run_id, "take"]) == 0
    assert "take(s='abc')" in capsys.readouterr().out


def test_a_hostile_len_on_a_written_string_does_not_reach_the_tee(
        tmp_path, monkeypatch, capsys):
    _runs_clean(tmp_path, monkeypatch, capsys, HOSTILE_STREAM, "emit ok")


# -- the invariant, over a REAL recording ----------------------------------
LIVE_OBJECTS = """
class S(str):
    def __eq__(self, other): raise ValueError("INJECTED-eq")
    def __ne__(self, other): raise ValueError("INJECTED-ne")
    def __hash__(self): return 0

class N(int):
    def __int__(self): return N(999)

class F(float):
    def __repr__(self): raise ValueError("INJECTED-repr")

class Odd(Exception):
    def __str__(self): return S("odd")

def handle(tag, size, ratio, bag):
    label = tag
    label = S("second")
    total = size
    try:
        raise Odd()
    except Odd:
        pass
    return {"tag": label, "n": total}

class KeyS(str):
    def __lt__(self, other): raise ValueError("INJECTED-key-lt")
    def __hash__(self): return str.__hash__(self)

def keys_too():
    class C:
        ns = locals()
        ns[KeyS("hk1")] = 1
        ns[KeyS("hk2")] = 2
        z = 3
        del ns[KeyS("hk1")], ns[KeyS("hk2")]
    return C.z

def main():
    keys_too()
    return handle(S("first"), N(3), F(1.5), [S("in"), N(4), {S("k"): F(2.5)}])
"""


def test_no_recorded_payload_holds_a_live_object(tmp_path, monkeypatch):
    """End to end, structurally. Every payload the recorder hands the writer
    is walked, over a real recording of a program whose every value is a
    hostile subclass -- arguments, a return value, per-line deltas and an
    exception message all at once -- plus a class body that puts `str`
    SUBCLASSES where NAMES should be, so the walk covers payload keys and
    not only payload values. This is the invariant `_on_line`'s comparison
    and `add_event`'s json encoding both silently depend on.
    """
    seen = []
    real = TraceWriter.add_event

    def spy(self, ts, tid, kind, fid, cid, line, payload):
        seen.append(payload)
        return real(self, ts, tid, kind, fid, cid, line, payload)

    monkeypatch.setattr(TraceWriter, "add_event", spy)
    _trace, err = record_inproc(tmp_path, LIVE_OBJECTS, focus=("prog",))

    assert err is None, err
    kinds = {p and tuple(sorted(p))[0] for p in seen}
    assert len(seen) > 6, seen                 # args, deltas, exc, return
    assert {"args", "deltas", "exc", "value"} & kinds, kinds
    for payload in seen:
        assert_plain(payload)


# 4. `_exc_event`'s `type(exc).__name__ in _CONTROL_FLOW_EXC`. A metaclass
#    property makes that attribute raise, from a hook, on every RAISE.
HOSTILE_EXC_NAME = """
class Meta(type):
    @property
    def __name__(cls):
        raise ValueError("INJECTED-name")

class Nameless(Exception, metaclass=Meta):
    pass

def risky():
    try:
        raise Nameless()
    except Nameless:
        return "handled"

def rethrow():
    try:
        try:
            raise Nameless()
        except Nameless:
            raise                # bare re-raise: RERAISE, a second hook
    except Nameless:
        return "rethrown"

def main():
    print("risky", risky(), rethrow())

main()
"""


def test_a_hostile_exception_type_name_does_not_reach_the_hook(
        tmp_path, monkeypatch, capsys):
    """`_exc_event` reads the exception's type name on every RAISE to skip
    control-flow exceptions. It goes through `type_name`, which cannot raise
    and returns an exact `str`; "?" is not a control-flow name, so the
    exception is still RECORDED rather than silently dropped.

    `_on_reraise` is a second hook reading the same attribute, reached only
    by a bare `raise` or the implicit re-raise ending a `finally` -- which
    is why the program does both a plain catch and a re-raise.
    """
    _run_id, out = _runs_clean(tmp_path, monkeypatch, capsys,
                               HOSTILE_EXC_NAME, "risky handled rethrown")
    assert _line(out, "dispositions:").startswith("dispositions: swallowed ")


# 5. The payload KEYS, not its values. `_on_line` took names straight from
#    `frame.f_locals.items()`, so a `str` subclass sitting where a name
#    should be got hashed, compared and SORTED by the recorder. Two of them
#    going out of scope on one line reach `sorted(gone)`.
HOSTILE_KEYS = """
class K(str):
    def __lt__(self, other):
        raise ValueError("INJECTED-key-lt")
    def __gt__(self, other):
        raise ValueError("INJECTED-key-gt")
    def __hash__(self):
        return str.__hash__(self)

def build():
    class C:
        ns = locals()
        ns[K("hk1")] = 1
        ns[K("hk2")] = 2
        c = 3
        del ns[K("hk1")], ns[K("hk2")]     # both gone at the SAME step
        d = 4
    return "ok"

def main():
    print("built", build())

main()
"""

# 6. `frame.f_locals` may BE a mapping the program supplied: `exec(code,
#    globals, mapping)` hands the frame an arbitrary object, so `.items()`
#    is an overridable method the recorder calls from a hook.
HOSTILE_LOCALS_MAPPING = """
class HostileMap(dict):
    def items(self):
        raise ValueError("INJECTED-items")
    def __contains__(self, k):
        raise ValueError("INJECTED-contains")

SRC = "q = 1\\nw = q + 1\\n"

def run_exec():
    ns = HostileMap()
    exec(compile(SRC, __file__, "exec"), {}, ns)
    return "ok"

def main():
    print("exec", run_exec())

main()
"""


def test_hostile_local_names_never_reach_the_recorder_s_own_sort(
        tmp_path, monkeypatch, capsys):
    """`sorted(gone)`, `prev.get(name)` and `prev.keys() - cur.keys()` all
    ran the program's code when a name was a `str` subclass. Pre-fix this
    exited 1 and `exceptions` reported the recorder's own ValueError as an
    uncaught bug at `c = 3`, a line that never raised."""
    run_id, _out = _runs_clean(tmp_path, monkeypatch, capsys, HOSTILE_KEYS,
                               "built ok", extra=("--focus", "prog"))
    # The names were still RECORDED -- normalised, not dropped.
    assert cli.main(["grep", run_id, "hk1"]) == 0
    assert "hk1" in capsys.readouterr().out


def test_a_locals_mapping_the_program_supplied_cannot_kill_the_run(
        tmp_path, monkeypatch, capsys):
    """`exec(code, globals, mapping)`: `f_locals` IS the program's object,
    so `.items()` is its method. The read is guarded, and the site is
    recorded as unreadable rather than skipped -- an absent LINE event would
    read as "nothing changed here"."""
    run_id, _out = _runs_clean(tmp_path, monkeypatch, capsys,
                               HOSTILE_LOCALS_MAPPING, "exec ok",
                               extra=("--focus", "prog"))
    assert cli.main(["grep", run_id, ""]) == 0
    rows = capsys.readouterr().out.splitlines()
    unread = [r for r in rows if "<unread: locals>" in r]
    # The exec'd frame's own CALL and both of its LINE sites: recorded, and
    # each one saying it could not read the locals.
    assert sum(r.split()[1] == "CALL" for r in unread) == 1, unread
    assert sum(r.split()[1] == "LINE" for r in unread) == 2, unread
    # ...and the frames whose locals ARE readable carry no such marker.
    assert any("run_exec" in r and "<unread: locals>" not in r for r in rows)


def test_a_line_whose_locals_could_not_be_read_says_so(tmp_path):
    """The marker has to survive to the display: empty deltas alone read as
    "nothing changed", which is the opposite of what the event says."""
    from sensorium.query.fmt import _fmt_line_tail
    assert _fmt_line_tail({"deltas": {}, "unread": ["locals"]}) \
        == "  <unread: locals>"
    assert _fmt_line_tail({"deltas": {}}) == ""


# 7. A step whose locals could not be read establishes NOTHING. It must not
#    be treated as a step where every name vanished, or the next readable
#    step reports names as newly changed that never changed at all.
FLAKY_LOCALS_MAPPING = """
class Flaky(dict):
    calls = 0
    def items(self):
        Flaky.calls += 1
        if Flaky.calls == 4:            # the CALL, then L1, L2, and THIS
            raise ValueError("INJECTED-items-once")
        return dict.items(self)

SRC = "a = 1\\nb = 2\\nc = 3\\nd = 4\\n"

def run_exec():
    exec(compile(SRC, __file__, "exec"), {}, Flaky())
    return "ok"

def main():
    print("flaky", run_exec())

main()
"""


def test_an_unreadable_step_does_not_make_the_next_one_over_report(
        tmp_path, monkeypatch, capsys):
    """`prev` is deliberately left in place when a step cannot be read.
    Clearing it would make every name look newly bound at the next readable
    line -- a confident claim about a line where nothing of the sort
    happened, built on a step the recorder never saw."""
    run_id, _out = _runs_clean(tmp_path, monkeypatch, capsys,
                               FLAKY_LOCALS_MAPPING, "flaky ok",
                               extra=("--focus", "prog"))
    assert cli.main(["grep", run_id, ""]) == 0
    rows = capsys.readouterr().out.splitlines()
    unread = [r for r in rows if "LINE" in r and "<unread: locals>" in r]
    assert len(unread) == 1, rows            # exactly one step went unread

    # The step after it reports only what changed since the last step that
    # WAS read -- `b` and `c` -- and not `a`, which was already reported.
    after = rows[rows.index(unread[0]) + 1]
    assert "b=2" in after and "c=3" in after, after
    assert "a=1" not in after, after
