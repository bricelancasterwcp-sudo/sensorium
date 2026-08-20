from sensorium.record.fingerprint import CAUSAL_KINDS, Fingerprint


def _fp(seq):
    f = Fingerprint()
    for item in seq:
        f.update(*item)
    return f


def test_same_sequence_same_digest():
    seq = [("/a.py", "f", "CALL"), ("/a.py", "f", "RETURN")]
    assert _fp(seq).hexdigest() == _fp(seq).hexdigest()
    assert _fp(seq).count == 2


def test_order_matters():
    a = [("/a.py", "f", "CALL"), ("/a.py", "g", "CALL")]
    assert _fp(a).hexdigest() != _fp(list(reversed(a))).hexdigest()


def test_kind_matters():
    assert (_fp([("/a.py", "f", "CALL")]).hexdigest()
            != _fp([("/a.py", "f", "RETURN")]).hexdigest())


def test_no_separator_collision():
    # ("ab","c") must not hash equal to ("a","bc")
    assert (_fp([("ab", "c", "CALL")]).hexdigest()
            != _fp([("a", "bc", "CALL")]).hexdigest())


def test_line_not_a_causal_kind():
    assert "LINE" not in CAUSAL_KINDS
