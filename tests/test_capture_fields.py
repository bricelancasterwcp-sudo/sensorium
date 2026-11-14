"""Field summaries for objects that use `object.__repr__`.

A custom repr is already stored. These tests cover the summary added when
that repr would only have been `<Name object at 0x...>`: which names, how
far the summary goes, and that a hostile object cannot escape the callback.
"""
from sensorium.record.capture import (
    CAPS, FIELD_KEYS, FIELD_REPR, capture_stats, capture_value)


def test_a_custom_repr_is_stored_and_not_summarised():
    class Grid:
        def __init__(self):
            self.n = 1

        def __repr__(self):
            return "<Grid>"

    v = capture_value(Grid())
    assert v["repr"] == "<Grid>"
    assert "fields" not in v and "fields_trunc" not in v


def test_an_inherited_repr_is_custom_too():
    class Base:
        def __repr__(self):
            return "Base()"

    class Child(Base):
        def __init__(self):
            self.n = 1

    v = capture_value(Child())
    assert v["repr"] == "Base()" and "fields" not in v


def test_a_default_repr_object_summarises_dict_fields_in_insertion_order():
    class Item:
        def __init__(self):
            self.sku = "widget"
            self.qty = 2

    item = Item()
    v = capture_value(item)
    assert v["k"] == "obj" and v["oid"] == id(item)
    assert " object at 0x" in v["repr"] and v["repr"].endswith(">")
    assert list(v["fields"]) == ["sku", "qty"]
    assert v["fields"]["sku"] == {"k": "str", "v": "widget"}
    assert v["fields"]["qty"] == {"k": "num", "v": 2}
    assert "fields_trunc" not in v


def test_an_instance_with_no_fields_stores_no_fields_key():
    class Bare:
        pass

    v = capture_value(Bare())
    assert v["k"] == "obj" and "fields" not in v
    assert "fields_trunc" not in v


def test_slots_are_summarised_in_mro_order_after_the_dict():
    class Base:
        __slots__ = ("a",)

    class Child(Base):
        __slots__ = ("b", "label")

        def __init__(self):
            self.a = 1
            self.b = 2
            self.label = "n"

    v = capture_value(Child())
    assert list(v["fields"]) == ["b", "label", "a"]
    assert v["fields"]["a"] == {"k": "num", "v": 1}
    assert v["fields"]["label"] == {"k": "str", "v": "n"}


def test_a_single_slot_string_and_a_bare_underscore_are_handled():
    class One:
        __slots__ = "value"

        def __init__(self):
            self.value = 3

    class Skip:
        def __init__(self):
            self._ = "hidden"
            self.ok = 1

    assert list(capture_value(One()).get("fields")) == ["value"]
    assert list(capture_value(Skip())["fields"]) == ["ok"]


def test_field_summary_stops_at_eight_names():
    class Wide:
        def __init__(self):
            for i in range(FIELD_KEYS + 2):
                setattr(self, f"f{i}", i)

    before = capture_stats["truncated"]
    v = capture_value(Wide())
    assert list(v["fields"]) == [f"f{i}" for i in range(FIELD_KEYS)]
    assert v["fields_trunc"] is True
    assert "f8" not in v["fields"]
    assert capture_stats["truncated"] == before + 1


def test_a_field_string_clips_at_the_field_cap_once():
    class Item:
        def __init__(self):
            self.sku = "x" * (FIELD_REPR + 10)

    before = capture_stats["truncated"]
    v = capture_value(Item())
    sku = v["fields"]["sku"]
    assert sku["v"] == "x" * FIELD_REPR and sku["trunc"] is True
    assert len(sku["v"]) < CAPS["str"]
    assert capture_stats["truncated"] == before + 1


def test_a_field_container_keeps_its_length_and_no_sample():
    class Item:
        def __init__(self):
            self.rows = [1, 2, 3]

    rows = capture_value(Item())["fields"]["rows"]
    assert rows["k"] == "seq" and rows["len"] == 3 and rows["trunc"] is True
    assert "sample" not in rows


def test_a_nested_object_field_is_not_summarised_again():
    class Node:
        def __init__(self):
            self.self = self
            self.n = 1

    v = capture_value(Node())
    inner = v["fields"]["self"]
    assert inner["k"] == "obj" and "fields" not in inner
    assert v["fields"]["n"] == {"k": "num", "v": 1}


def test_a_list_of_plain_objects_summarises_each_element():
    class Item:
        def __init__(self, sku):
            self.sku = sku

    v = capture_value([Item("a")])
    elt = v["sample"][0]
    assert elt["fields"]["sku"] == {"k": "str", "v": "a"}


def test_a_failed_field_read_is_unread_and_not_none():
    """An unset slot is a read that failed, not a field holding None."""
    class Slot:
        __slots__ = ("a", "b")

        def __init__(self):
            self.b = 1

    v = capture_value(Slot())
    assert v["fields"]["a"] == {"k": "unread", "unread": ["value"]}
    assert v["fields"]["b"] == {"k": "num", "v": 1}


def test_a_hostile_dict_cannot_escape_the_summary():
    class Boom:
        @property
        def __dict__(self):
            raise RuntimeError("no dict")

    v = capture_value(Boom())
    assert v["k"] == "obj"
    assert "fields" not in v


def test_a_field_value_holds_no_live_str_subclass():
    class Live(str):
        def __eq__(self, other):
            raise ValueError("EMBEDDED-eq")

    class Item:
        def __init__(self):
            self.sku = Live("abc")

    sku = capture_value(Item())["fields"]["sku"]
    assert type(sku["v"]) is str and sku["v"] == "abc"


def test_none_in_a_field_is_not_an_unread_read():
    class Item:
        def __init__(self):
            self.sku = None

    assert capture_value(Item())["fields"]["sku"] == {"k": "none"}
