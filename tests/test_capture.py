from sensorium.record.capture import CAPS, capture_exc, capture_stats, capture_value


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
