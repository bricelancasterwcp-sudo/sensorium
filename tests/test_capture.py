import re

from sensorium import cli
from sensorium.record.capture import CAPS, capture_exc, capture_stats, capture_value
from tests.helpers import record_script


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
