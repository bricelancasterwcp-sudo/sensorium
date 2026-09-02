"""Rename detection for `diff --ignore-moves`: pair a function that left one
file with the same-named function that appeared in another, and only when
that pairing is the only one possible."""
from sensorium.query.moves import Moves, detect_moves, hash_stream, project


class _T:
    """Just enough of Trace for detect_moves: `codes()`."""
    def __init__(self, keys):
        from sensorium.store.reader import Code
        self._codes = [Code(i + 1, f, q, 1) for i, (f, q) in enumerate(keys)]

    def codes(self):
        return list(self._codes)


def test_unique_move_is_paired_and_named():
    a = _T([("/w/main.py", "main"), ("/w/a.py", "helper")])
    b = _T([("/w/main.py", "main"), ("/w/b.py", "helper")])
    m = detect_moves(a, b)
    assert m.mapping == {("/w/a.py", "helper"): ("/w/b.py", "helper")}
    assert m.moved == [("helper", "/w/a.py", "/w/b.py")]
    assert m.added == [] and m.removed == [] and m.unpaired == []


def test_unchanged_code_is_not_in_the_mapping():
    a = _T([("/w/main.py", "main")])
    m = detect_moves(a, a)
    assert m == Moves({}, [], [], [], [], [])


def test_ambiguous_name_is_left_unpaired_on_both_sides():
    a = _T([("/w/a.py", "helper"), ("/w/c.py", "helper")])
    b = _T([("/w/b.py", "helper"), ("/w/d.py", "helper")])
    m = detect_moves(a, b)
    assert m.mapping == {}
    assert m.unpaired == ["helper"]
    assert m.removed == [("/w/a.py", "helper"), ("/w/c.py", "helper")]
    assert m.added == [("/w/b.py", "helper"), ("/w/d.py", "helper")]


def test_added_and_removed_are_reported_not_paired():
    a = _T([("/w/a.py", "old")])
    b = _T([("/w/a.py", "new")])
    m = detect_moves(a, b)
    assert m.mapping == {}
    assert m.removed == [("/w/a.py", "old")] and m.added == [("/w/a.py", "new")]


def test_project_rewrites_only_mapped_steps_and_keeps_kind_and_event_id():
    m = Moves({("/w/a.py", "helper"): ("/w/b.py", "helper")}, [], [], [], [], [])
    stream = [("/w/main.py", "main", "CALL", 1), ("/w/a.py", "helper", "CALL", 2),
              ("/w/a.py", "helper", "RETURN", 3)]
    assert project(stream, m) == [
        ("/w/main.py", "main", "CALL", 1), ("/w/b.py", "helper", "CALL", 2),
        ("/w/b.py", "helper", "RETURN", 3)]


def test_project_drops_a_one_sided_module_frame_and_keeps_two_sided_ones():
    m = Moves({}, [], [], [], [], [("B", "/w/new.py")])
    stream = [("/w/main.py", "<module>", "CALL", 1), ("/w/new.py", "<module>", "CALL", 2),
              ("/w/new.py", "helper", "CALL", 3), ("/w/new.py", "<module>", "RETURN", 4)]
    assert project(stream, m) == [("/w/main.py", "<module>", "CALL", 1),
                                  ("/w/new.py", "helper", "CALL", 3)]


def test_detect_moves_never_pairs_module_code_and_lists_one_sided_files():
    a = _T([("/w/main.py", "<module>"), ("/w/old.py", "<module>")])
    b = _T([("/w/main.py", "<module>"), ("/w/new.py", "<module>")])
    m = detect_moves(a, b)
    assert m.mapping == {} and m.added == [] and m.removed == [] and m.unpaired == []
    assert m.one_sided_modules == [("A", "/w/old.py"), ("B", "/w/new.py")]


def test_hash_stream_is_blake2b_over_file_qualname_kind():
    import hashlib
    h = hashlib.blake2b(digest_size=16)
    h.update(b"/w/a.py\x1fhelper\x1fCALL\n")
    assert hash_stream([("/w/a.py", "helper", "CALL", 7)]) == h.hexdigest()
    assert hash_stream([]) == hashlib.blake2b(digest_size=16).hexdigest()
